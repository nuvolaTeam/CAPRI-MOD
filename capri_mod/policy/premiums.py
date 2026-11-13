"""CAPRI's premiums of the simulation year, all ported schemes together (P2): the declared premiums of policy.gms
(declared.py) fixed at the year's trend data, cut by prmcut.gms (premium_cut.py) at any levels.

The schemes, each from its port:
  coupled    VCS, the crop-specific cotton payment, the complementary national payments (cap14_premiums.py)
  area       greening, young farmers, redistributive, natural constraints, SAPS (cap14_premiums.py)
  BPS        dp_bps per unit: the 2030 rate (bps.py) on the key of the 2004-2013 regime (mtr.py); its ceilings the
             unit's entitlements (CEILLEV) and its share of the member state's BPS ceiling before the convergence
             (CEILVAL), implement_bps.gms l. 147-160, 315
  RD         the rural development schemes (rd.py)
  Nordic aid Finland's and Sweden's national aid (nordic_aid.py)
  DPIRSCOW   Ireland's suckler cow welfare payment (mtr_until2013.gms l. 351-352, carried to the year)
CAP_2014_2020.gms l. 77 kills the entitlement weights before the year's policy.gms: every weight is 1 there except
the slaughtered share of the schemes per slaughtered head (policy.gms). Not ported: Norway's payments (norw_pol.gms)
and the non-CAP payments (DPNONCAP, paid outside the EU in 2030).

The year's data (yields, young animals, historical yields) are sim_ini_21730's DATA "Y" (mtr_base_data.csv).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from capri_mod.data.definitions import capri_ms
from capri_mod.policy import bps as _bps
from capri_mod.policy import cap14_premiums as _c14
from capri_mod.policy import mtr as _mtr
from capri_mod.policy import nordic_aid as _noa
from capri_mod.policy import rd as _rd
from capri_mod.policy.declared import PolicyRegions, declared_premiums
from capri_mod.policy.premium_cut import EPS, CeilingRegions, premiums


def year_data(units, d=None):
    """{"yields", "hist", "slaughter"} of the units and their member states at the simulation year (DATA "Y")."""
    d = d or _mtr.data()
    base = _mtr._base(d)
    regions = set(units) | {capri_ms(u) for u in units}
    out = {"yields": {}, "hist": {}, "slaughter": {}}
    for (r, a, i, c), v in base.items():
        if r not in regions or c != "Y":
            continue
        if i == "YILD":
            out["yields"][(r, a)] = v
        elif i == "SLGT":
            out["slaughter"][(r, a)] = v
        elif i == "HSTY":
            out["hist"][(r, a)] = v
    return out


def bps_declarations(units, levels: dict, year: int, base_year: int):
    """dp_bps's declarations and ceilings per unit: ({(unit, "dp_bps"): {"rates": {"PGSAPS": EUR/ha}, "APPTYPE":
    "perLevl"}}, {(unit, "dp_bps"): {"CEILLEV": entitlements, "CEILVAL": million EUR}})."""
    key = _mtr.mtr_key(units, levels, year, base_year)
    rates, ceil = _bps.bps_rates(units, levels, key, year, detail=True)
    decl = {(u, "dp_bps"): {"rates": {"PGSAPS": r}, "APPTYPE": "perLevl"} for u, r in rates.items()}
    return decl, ceil


@dataclass
class YearPremiums:
    """The declared premiums of the year for a set of units, per member state: prmd {(region, activity, scheme)},
    weight {(unit, activity, scheme)}, ceilings {(region, scheme)}, and the regions of each member state."""
    prmd: dict = field(default_factory=dict)
    weight: dict = field(default_factory=dict)
    ceilings: dict = field(default_factory=dict)
    regions: dict = field(default_factory=dict)       # member state -> CeilingRegions

    def cut(self, levels: dict) -> dict:
        """prmcut.gms at the levels {(unit, activity): level}: {(unit, activity, scheme): PRME}."""
        out = {}
        for ms, cr in self.regions.items():
            us = set(cr.member_states[ms])
            lev = {k: v for k, v in levels.items() if k[0] in us}
            pr = {k: v for k, v in self.prmd.items() if k[0] in us}
            w = {k: self.weight[k] for k in pr}
            c = {k: v for k, v in self.ceilings.items() if k[0] == ms or k[0] in us or k[0] in cr.nuts1}
            out.update(premiums(lev, pr, w, c, cr)["prme"])
        return out


def year_premiums(units, levels: dict, year: int, base_year: int, schemes=None) -> YearPremiums:
    """The year's declared premiums of all ported schemes (or of the named groups: coupled, area, bps, rd, nordic,
    irscow) at the units, policy.gms run at the year's trend levels {(unit, activity): level}."""
    schemes = set(schemes or ("coupled", "area", "bps", "rd", "nordic", "irscow"))
    groups = _c14.data()["groups"]
    yd = year_data(units)
    lu = {str(a): float(v) for a, v in zip(_mtr.data()["lu"].activity, _mtr.data()["lu"].value)}
    by_ms = defaultdict(list)
    for u in units:
        by_ms[capri_ms(u)].append(u)
    out = YearPremiums()
    decl, ceil = {}, {}
    if "coupled" in schemes:
        d, c = _c14.coupled_declarations(year, None, levels)
        decl.update(d)
        ceil.update(c)
    if "area" in schemes:
        d, c = _c14.area_declarations(year)
        decl.update(d)
        ceil.update(c)
    if "rd" in schemes:
        r = _rd.rd_declarations(levels, year, groups, base_weights=_c14.entitlement_weights())
        decl.update(r["declarations"])
        ceil.update(r["ceilings"])
    if "nordic" in schemes:
        d, c = _noa.nordic_declarations(year)
        decl.update(d)
        ceil.update(c)
    if "irscow" in schemes:
        P = _mtr.mtr_series(year, base_year)
        Y = _mtr.declarations_of_year(P, year)
        d, c = _mtr.policy_inputs(Y, {"DPIRSCOW"})
        decl.update(d)
        ceil.update(c)
    if "bps" in schemes:
        d, c = bps_declarations(units, levels, year, base_year)
        decl.update(d)
        ceil.update(c)
    for ms, us in by_ms.items():
        regions = PolicyRegions.from_codes(us)
        lev = {k: v for k, v in levels.items() if k[0] in set(us)}
        dp = declared_premiums(decl, groups, regions, lev, yields=yd["yields"], hist_yields=yd["hist"],
                               slaughter=yd["slaughter"], lu_units=lu)
        u_set = set(us)
        for k, v in dp["prmd"].items():
            if k[0] in u_set and v:
                out.prmd[k] = v
                out.weight[k] = dp["weight"][k]
        nuts1 = {r: [u for u in us if u in regions.members.get(r, [])] for r in regions.nuts1
                 if r != ms and r not in u_set and any(u in regions.members.get(r, []) for u in us)}
        out.regions[ms] = CeilingRegions(member_states={ms: us}, nuts1=nuts1)
    out.ceilings = ceil
    return out


def trend_levels(inp=None) -> dict:
    """{(unit, activity): the 2030 trend level} the year's chain runs at (CAPRI's DATA TRD, cap14_entitlement_levels.csv)."""
    from capri_mod.supply import inputs as _inputs
    inp = inp or _inputs.current()
    lev = inp.csv("cap14_entitlement_levels.csv", "policy", keep_default_na=False)
    return {(str(r), str(a)): float(v) for r, a, v in zip(lev.region, lev.activity, lev.trd_kha)}


def eu_units(levels: dict, inp=None):
    """The EU's regional units of the levels (the member states the ported schemes cover: not Norway, the UK and the
    non-EU regions)."""
    from capri_mod.supply import inputs as _inputs
    inp = inp or _inputs.current()
    ru = set(str(u) for u in inp.csv("regional_units.csv", "codes", keep_default_na=False).region)
    eu = set(_mtr._ms_members(_mtr.data(), "EU028000"))
    return sorted(u for u in {u for u, _ in levels} & ru if capri_ms(u) in eu and capri_ms(u) != "UK000000")


def prme_table(year: int, base_year: int, levels: dict = None, units=None) -> dict:
    """{(region, activity): PRME} the premium per activity unit over all ported schemes at the levels (the trend
    levels by default), for the units and their member states (the units' level-weighted average, as
    aggreg_ppepay.gms aggregates PRME)."""
    levels = levels if levels is not None else trend_levels()
    units = units if units is not None else eu_units(levels)
    yp = year_premiums(units, levels, year, base_year)
    out = defaultdict(float)
    for (u, a, s), v in yp.cut(levels).items():
        if v and v != EPS:
            out[(u, a)] += v
    num, den = defaultdict(float), defaultdict(float)
    for u in units:
        m = capri_ms(u)
        for (r, a), L in levels.items():
            if r == u and L > 0:
                num[(m, a)] += out.get((u, a), 0.0) * L
                den[(m, a)] += L
    for k, L in den.items():
        if L > 0 and num[k]:
            out[k] = num[k] / L
    return dict(out)
