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
from capri_mod.supply import inputs as _inputs


def _load(inp):
    rates = inp.csv("cap14_coupled_rates.csv", "policy")
    ceil = inp.csv("cap14_coupled_ceilings.csv", "policy")
    psg = inp.csv("capri/PSG_TO_A.csv", "codes")
    groups = defaultdict(list)
    for g, a in zip(psg["psgroup"], psg["pact"]):
        groups[str(g).upper()].append(str(a))
    return {"rates": rates, "ceilings": ceil, "groups": dict(groups)}


def data():
    """The coupled schemes' rates and ceilings (capri_data/<base year>/policy/cap14_coupled_*.csv) and CAPRI's premium
    groups (codes/capri/PSG_TO_A.csv), read once per run."""
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


def coupled_premiums(units, levels: dict, year: int, d=None):
    """The coupled schemes' declared premiums (PRMD per unit of the activity) at the given units, their weights (1)
    and ceilings, for premium_cut.premiums: (prmd {(unit, activity, scheme): EUR}, weight, ceilings {(region,
    scheme): {"CEILVAL": million EUR}}). An activity gets a rate where the unit has a level of it (policy.gms's
    p_dataCopy LEVL condition); the sum over its groups where it is in several."""
    d = data() if d is None else d
    units = list(units)
    prmd, ceilings = {}, {}
    for (r, s), item in coupled_premium_data(year, d).items():
        below = [u for u in units if u == r] or [u for u in units if capri_ms(u) == r and r != u]
        if not below:
            continue
        if "CEILVAL" in item:
            ceilings[(r, s)] = {"CEILVAL": item["CEILVAL"]}
        for g, rate in item["rates"].items():
            for a in d["groups"].get(g, []):
                for u in below:
                    if levels.get((u, a), 0.0) > 0.0:
                        prmd[(u, a, s)] = prmd.get((u, a, s), 0.0) + rate
    return prmd, {k: 1.0 for k in prmd}, ceilings
