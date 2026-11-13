"""CAPRI's endogenous entitlement limit (KNOWN_ISSUES K136): the CAP 2014-2020 ceilings of the simulation year
(scen/base_scenarios/CAP_2014_2020.gms) and the limit and cut of policy/def_endCut.gms, which supply_model.gms's
sumEntl_ and overShotEntl_ put in the regional model (l. 1885-1892; objective l. 4768):

    sumEntl = sum over the crop activities (MCACT) of their levels
    overshoot >= sumEntl - Limit,  overshoot >= 0
    objective - overshoot x Cut

Limit is the sum of the region's trend levels (DATA "LEVL" "TRD"), Cut the member state's ceilings of the cut
schemes (dp_bps or DPBPS_SAPS, DPYOUNG, DPFIRHA, DPNATCO: dpEndCut) x 1000 / the sum of its regions' limits, EUR per
ha: a hectare beyond the trend area earns no area payment.

The ceilings, as CAPRI's chain computes them (data: tools/build/build_cap14_entitlements.py):
  1. the national ceiling of Regulation 1307/2013 Annex II, each BPS year without a value taking the year before's
     (CAP_2014_2020.gms l. 133-141);
  2. less the transfer to pillar 2: in the years with a transfer (up to the simulation year) the national ceiling x
     the percentage, the other years taking the year before's amount (cap_2013_2020_transfers.gms); the transfer from
     pillar 2 is zero, since del_policy.gms has deleted the pillar-2 ceilings it is a share of;
  3. the greening share (30%) and the young-farmer, redistributive and natural-constraint shares of that ceiling;
     the BPS ceiling the rest, after the coupled support (VCS, cotton) of the member state's regions (l. 300-355);
     the coupled ceilings from the base year on take the year before's where they have none (CAP_2013_2020_vcs.gms,
     CAP_2013_2020_cscs.gms);
  4. a simulation year after the BPS years takes each scheme's ceiling of the last year that has one
     (policy/def_policy.gms l. 54-64): BPS and greening from the last BPS year, the shares' payments from the last
     year of their tables (2020). The BPS ceiling of the years after 2020 is therefore not reduced by those payments,
     as in CAPRI (checked: the 2030 ceilings of every member state equal those of CAPRI's reference dataOut).
"""
from __future__ import annotations

from collections import defaultdict

from capri_mod.data.definitions import CAPRI_MEMBERS, capri_ms
from capri_mod.supply import inputs as _inputs

#: the shares' payment schemes of the national ceiling (cap14_ceiling_shares.csv)
SHARE_SCHEMES = ("DPYOUNG", "DPFIRHA", "DPNATCO")
#: CAPRI's crop activities of the idled histosols (MCACT), by the model's histosol class (HISTOSOL_CLASSES)
HISTOSOL_CODES = {"crop": "IHISCR", "grass": "IHISGR"}


def _load(inp):
    nat = inp.csv("cap14_national_ceilings.csv", "policy")
    shares = inp.csv("cap14_ceiling_shares.csv", "policy")
    transfers = inp.csv("cap14_pillar_transfers.csv", "policy")
    coupled = inp.csv("cap14_coupled_ceilings.csv", "policy")
    st = inp.csv("cap14_settings.csv", "policy", keep_default_na=False)
    lev = inp.csv("cap14_entitlement_levels.csv", "policy", keep_default_na=False)
    settings = defaultdict(dict)
    for r in st.itertuples(index=False):
        settings[r.item][r.key] = float(r.value)
    # the crops' trend levels (CAPRI's MCACT; the file holds all production activities' for the RD chain)
    mcact = set(inp.csv("capri/MCACT.csv", "codes", keep_default_na=False).code)
    levels = defaultdict(dict)
    for r in lev.itertuples(index=False):
        if r.activity in mcact:
            levels[r.region][r.activity] = float(r.trd_kha)
    deducted = {str(c).strip().lower() for f in ("PSDPAY_vcs", "PSDPAY_cscs")
                for c in inp.csv(f"capri/{f}.csv", "codes", keep_default_na=False).code}
    return {"nat": nat, "shares": shares, "transfers": transfers, "coupled": coupled, "deducted": deducted,
            "settings": dict(settings),
            "levels": dict(levels)}


def data():
    """The run's CAP 2014-2020 inputs (capri_data/<base year>/policy/cap14_*.csv), read once per run."""
    return _inputs.current().cached("cap14_entitlements", _load)


def _filled(values: dict, years, keep=()) -> dict:
    """values {year: v} with each year of `years` (ascending) that has none taking the year before's, as GAMS's
    loop(y, p(y) $ (not p(y)) = p(y-1)); a present zero (a cell written EPS) is a value. The years in `keep` before
    the loop keep their values."""
    out = {y: v for y, v in values.items() if y in set(keep)}
    for y in years:
        if y in values:
            out[y] = values[y]
        elif y - 1 in out:
            out[y] = out[y - 1]
    return out


def ms_ceilings(year: int, d=None) -> dict:
    """{member state: {scheme: ceiling, million EUR}} of the simulation year: DPGREEN, the BPS ceiling (dp_bps, or
    DPBPS_SAPS in the single-area-payment member states) and the shares' schemes, CAPRI's chain (module docstring)."""
    d = data() if d is None else d
    st = d["settings"]
    bps_years = list(range(int(st["bps_years"]["first"]), int(st["bps_years"]["last"]) + 1))
    green = float(st["greening_share"]["MS"])
    saps = set(st.get("saps", {}))
    base = int(_inputs.base_year())

    # 1. Annex II, filled over the BPS years
    nat = {ms: _filled(dict(zip(g.year.astype(int), g.ceiling_meur.astype(float))), bps_years)
           for ms, g in d["nat"].groupby("ms")}

    # 2. the transfer to pillar 2 in its years (those of the table, up to the simulation year): the national ceiling
    #    x the percentage, a later year without a transfer taking the year before's amount
    tr = d["transfers"]
    t_years = sorted(y for y in set(tr.year.astype(int)) if y <= year)
    after = {}
    for ms, n in nat.items():
        rel = dict(zip(tr.year[tr.ms == ms].astype(int), tr.pct[tr.ms == ms].astype(float)))
        a = {y: n.get(y, 0.0) * rel[y] / 100.0 for y in t_years if y in rel}
        a = _filled(a, range(min(t_years, default=year), year + 1))
        after[ms] = {y: max(0.0, v - a.get(y, 0.0)) for y, v in n.items()}

    # 3. the coupled support of the member state's regions (map_rr: Luxembourg's in Belgium's), each scheme's
    #    ceiling from the base year on taking the year before's where it has none
    #    (the schemes of psdpay_vcs and psdpay_cscs: the complementary national payments in the same file are national
    #    money, not taken out, CAP_2014_2020.gms l. 178)
    cp = defaultdict(lambda: defaultdict(float))
    for (reg, _scheme), g in d["coupled"].groupby(["region", "scheme"]):
        if str(_scheme).strip().lower() not in d["deducted"]:
            continue
        v = dict(zip(g.year.astype(int), g.ceiling_meur.astype(float)))
        for y, x in _filled(v, range(base, year + 1), keep=[y for y in v if y < base]).items():
            cp[capri_ms(reg)][y] += x

    sh = defaultdict(dict)
    for r in d["shares"].itertuples(index=False):
        sh[(r.ms, r.scheme)][int(r.year)] = float(r.pct)

    out = {}
    for ms, n in after.items():
        per_year = defaultdict(dict)
        for y in bps_years:
            c = n.get(y, 0.0)
            per_year[y]["DPGREEN"] = green * c
            for s in SHARE_SCHEMES:
                per_year[y][s] = sh[(ms, s)].get(y, 0.0) / 100.0 * c
            rest = c - cp[ms].get(y, 0.0) - per_year[y]["DPGREEN"] - sum(per_year[y][s] for s in SHARE_SCHEMES)
            per_year[y]["DPBPS_SAPS" if ms in saps else "dp_bps"] = rest
        if year in per_year:
            out[ms] = {s: v for s, v in per_year[year].items() if v != 0.0}
            continue
        # 4. after the BPS years: each scheme's value of the last year that has one
        last = {}
        for y in sorted(per_year):
            for s, v in per_year[y].items():
                if v != 0.0 and y < year:
                    last[s] = v
        out[ms] = last
    return out


def ms_cuts(year: int, d=None) -> dict:
    """{member state: Cut, EUR per ha}: the member state's ceilings of the cut schemes (dpEndCut, those with a ceiling:
    PSDPAY_cutEndog) x 1000 / the sum of its regions' limits (p_entlLimit(MS, .., "cut")). The schemes share the
    limit, so their overshoots are equal and the region's objective loses overshoot x the sum of their cuts."""
    d = data() if d is None else d
    cut_schemes = {s.lower() for s in d["settings"].get("cut_scheme", {})}
    limits = defaultdict(float)
    for r, v in d["levels"].items():
        limits[capri_ms(r)] += sum(v.values())
    out = {}
    for ms, ceil in ms_ceilings(year, d).items():
        total = sum(v for s, v in ceil.items() if s.lower() in cut_schemes)
        if total > 0.0 and limits.get(ms, 0.0) > 0.0:
            out[ms] = total * 1000.0 / limits[ms]
    return out


def region_limit(region: str, acts, year: int):
    """CAPRI's entitlement limit of a regional unit in the model's columns: (Cut EUR/ha, limit kha, columns), the
    columns the model activities that are CAPRI crop activities (MCACT, through their CAPRI codes). The limit is the
    sum of those activities' trend levels: CAPRI's crop activities the model does not have (NECR, ISET, GSET, TSET,
    FallGr) are held at their trend levels, which leave both sides of sumEntl_ (the idled histosols, iHisCr and
    iHisGr, the caller adds as its histosol columns). None where the member state has no cut."""
    inp = _inputs.current()
    lev = data()["levels"].get(region)
    cut = inp.cached(f"cap14_cuts_{year}", lambda _i: ms_cuts(year)).get(capri_ms(region))
    if not lev or cut is None:
        return None
    cols, limit = [], 0.0
    for j, a in enumerate(acts):
        codes = [c for c in CAPRI_MEMBERS.get(a, (a,)) if c in lev]
        if codes:
            cols.append(j)
            limit += sum(lev[c] for c in codes)
    return cut, limit, cols
