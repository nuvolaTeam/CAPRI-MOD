"""CAPRI's CAP 2014-2020 premiums of the simulation year, for the premium cut (P2; policy/prmcut.gms,
capri_mod/policy/premium_cut.py). So far the coupled support: the voluntary coupled support (VCS) and the
crop-specific cotton payment.

The year's premium data are each scheme's rates per premium group and its ceiling of the last year that has them
(policy/def_policy.gms l. 54-64 fills a year from the previous edited one; for the coupled schemes this runs after
CAP_2013_2020_vcs.gms's own fill from the base year, so a scheme written for 2015 only, Poland's flax, reaches 2030
here, though not the BPS ceiling's deduction, K136). policy.gms then gives each activity of a group the group's rate,
per level (the coupled schemes' application type, CAP_2013_2020_vcs.gms), at the units of the region the rate is
written for (a member state's to all its units; a unit's, BL400000's, to itself).
"""
from __future__ import annotations

from collections import defaultdict

from capri_mod.data.definitions import capri_ms
from capri_mod.policy.premium_cut import EPS
from capri_mod.supply import entitlements as _entl
from capri_mod.supply import inputs as _inputs


def _load(inp):
    rates = inp.csv("cap14_coupled_rates.csv", "policy")
    ceil = inp.csv("cap14_coupled_ceilings.csv", "policy")
    psg = inp.csv("capri/PSG_TO_A.csv", "codes")
    groups = defaultdict(list)
    for g, a in zip(psg["psgroup"], psg["pact"]):
        groups[str(g).upper()].append(str(a))
    # the groups the chain redefines at run time (mtr_until2013.gms): their crops become the union of other groups'
    edits = inp.csv("premium_group_edits.csv", "policy", keep_default_na=False)
    domain = {d: set(inp.csv(f"capri/{d}.csv", "codes", keep_default_na=False).code) for d in set(edits["domain"])}
    for g, part in edits.groupby("group"):
        dom = set().union(*(domain[d] for d in part["domain"]))
        crops = {a for f in part["from_group"] for a in groups.get(f, []) if a in dom}
        groups[g] = sorted({a for a in groups.get(g, []) if a not in dom} | crops)
    dg = inp.csv("cndp_decoupled_groups.csv", "policy", keep_default_na=False)
    return {"rates": rates, "ceilings": ceil, "groups": dict(groups),
            "dcndp_groups": [(str(s), str(g).upper()) for s, g in zip(dg.scheme, dg.group)]}


def data():
    """The coupled schemes' rates and ceilings (capri_data/<base year>/policy/cap14_coupled_*.csv) and CAPRI's premium
    groups (codes/capri/PSG_TO_A.csv, with the chain's run-time redefinitions, policy/premium_group_edits.csv), read
    once per run."""
    return _inputs.current().cached("cap14_premiums", _load)


def _last(years_values, year: int):
    ys = [y for y in years_values if y <= year]
    return years_values[max(ys)] if ys else None


def coupled_premium_data(year: int, d=None) -> dict:
    """{(region, scheme): {"rates": {group: EUR per unit}, "CEILVAL": million EUR}} of the simulation year: each item
    of the last year that has it (def_policy.gms)."""
    d = data() if d is None else d
    out = defaultdict(lambda: {"rates": {}})
    for (r, s, g), grp in d["rates"].groupby(["region", "scheme", "group"]):
        v = _last(dict(zip(grp.year.astype(int), grp.rate.astype(float))), year)
        if v is not None:
            out[(r, s)]["rates"][str(g).upper()] = v
    for (r, s), grp in d["ceilings"].groupby(["region", "scheme"]):
        v = _last(dict(zip(grp.year.astype(int), grp.ceiling_meur.astype(float))), year)
        if v is not None:
            out[(r, s)]["CEILVAL"] = v
    return dict(out)


def entitlement_weights(inp=None) -> dict:
    """{(region, activity, scheme): p_EntlWght1, EPS where CAPRI writes EPS} (policy/premium_entitlement_weights.csv):
    the restart file's weights, live in the chain until CAP_2014_2020.gms l. 77 kills them (rd_logic.gms's rate
    scaling, the base-year pass of calc_mtr_top.gms), not in the year's policy.gms."""
    inp = inp or _inputs.current()

    def _load(i):
        w = i.csv("premium_entitlement_weights.csv", "policy", keep_default_na=False)
        return {(r, a, s): (EPS if int(e) else float(v))
                for r, a, s, v, e in zip(w.region, w.activity, w.scheme, w.weight, w.eps)}
    return inp.cached("premium_entitlement_weights", _load)


def coupled_declarations(year: int, d=None, levels: dict = None):
    """The coupled schemes' declarations of the year for declared.declared_premiums: {(region, scheme): {"rates":
    {group: EUR per unit}, "APPTYPE": "perLevl" where the region has a ceiling (CAP_2013_2020_vcs.gms l. 49,
    _cscs.gms l. 47, _CNDP.gms l. 86-94)}} and their ceilings {(region, scheme): {"CEILVAL": million EUR}}. With the
    levels {(unit, activity): level}, the decoupled complementary national payments' rates too: the scheme's ceiling
    over the member state's level of its group's activities (CAP_2013_2020_CNDP.gms l. 63-66, computed with each data
    year's ceiling before the years are filled, so the last one's)."""
    d = data() if d is None else d
    decl, ceilings = {}, {}
    item_data = coupled_premium_data(year, d)
    if levels is not None:
        ms_level = defaultdict(float)
        for (u, a), v in levels.items():
            ms_level[(capri_ms(u), a)] += v
        for s, g in d["dcndp_groups"]:
            for (r, s2), item in item_data.items():
                if s2 != s or not item.get("CEILVAL"):
                    continue
                tot = sum(ms_level.get((r, a), 0.0) for a in d["groups"].get(g, []))
                if tot:
                    item["rates"][g] = item["CEILVAL"] * 1000.0 / tot
    for (r, s), item in item_data.items():
        decl[(r, s)] = {"rates": dict(item["rates"])}
        if "CEILVAL" in item:
            ceilings[(r, s)] = {"CEILVAL": item["CEILVAL"]}
            if item["CEILVAL"]:
                decl[(r, s)]["APPTYPE"] = "perLevl"
    return decl, ceilings


def area_declarations(year: int):
    """The CAP 2014-2020 area schemes' declarations of the year: the greening, young-farmer, redistributive,
    natural-constraint payments and the SAPS (CAP_2014_2020.gms l. 309-357): the rate per premium group (PGSAPS, 1000
    EUR per ha) in each member state, per level where the member state has a ceiling of the scheme (the year's, from
    capri_mod/supply/entitlements.py, K136), and those ceilings. The BPS of the member states with the basic payment
    scheme (dp_bps) has a rate per region from implement_bps.gms's convergence: P2c."""
    ent = _entl.data()
    rates = {item[len("area_rate_"):]: v for item, v in ent["settings"].items() if item.startswith("area_rate_")}
    decl, ceilings = {}, {}
    for ms, c in _entl.ms_ceilings(year, ent).items():
        for g, by_scheme in rates.items():
            for s, rate in by_scheme.items():
                decl.setdefault((ms, s), {"rates": {}})["rates"][g] = rate
                v = c.get(s, 0.0)
                if v > 0.0:
                    decl[(ms, s)]["APPTYPE"] = "perLevl"
                    ceilings[(ms, s)] = {"CEILVAL": v}
    return decl, ceilings


def _declared(units, levels, decl):
    """policy.gms for the year: no entitlement weights (CAP_2014_2020.gms l. 77 kills p_entlWght1 after the
    base-year pass that writes policyIUV.gdx, and no later file of the chain sets one), so each is 1."""
    from capri_mod.policy.declared import PolicyRegions, declared_premiums
    regions = PolicyRegions.from_codes(units)
    out = declared_premiums(decl, data()["groups"], regions, levels)
    units = set(units)
    prmd = {k: v for k, v in out["prmd"].items() if k[0] in units and v}
    return prmd, {k: out["weight"][k] for k in prmd}


def coupled_premiums(units, levels: dict, year: int, d=None):
    """The coupled schemes' declared premiums (PRMD per unit of the activity) at the given units, their entitlement
    weights and ceilings, for premium_cut.premiums: (prmd {(unit, activity, scheme): EUR}, weight, ceilings {(region,
    scheme): {"CEILVAL": million EUR}}), through policy.gms (declared.py)."""
    decl, ceilings = coupled_declarations(year, d, levels)
    prmd, weight = _declared(units, levels, decl)
    return prmd, weight, ceilings


def area_premiums(units, levels: dict, year: int):
    """The CAP 2014-2020 area schemes' declared premiums at the given units (area_declarations through policy.gms),
    their entitlement weights and the member states' ceilings, for premium_cut.premiums."""
    decl, ceilings = area_declarations(year)
    prmd, weight = _declared(units, levels, decl)
    return prmd, weight, ceilings
