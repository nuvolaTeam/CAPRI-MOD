"""CAPRI's Nordic aid (policy/nordicaid.gms, P2c): the national aid to northern Finland and Sweden granted on their
accession (regulation 142), as CAPRI declares it for 1995 and def_policy.gms carries it to the simulation year.

A CAPRI region's rate of a scheme for a premium group is the sum over the Nordic aid regions of its share in each
(p_nordicAidRegionShare) times the region's amount per livestock unit, ton of milk or hectare (tables 2.5 and 2.9 of
the evaluation CAPRI's file cites); the ceilings are the member states' (tables 2.6 and 2.10, million EUR). The
application type is set where the region has a ceiling or a rate of the scheme: per level for the crops' schemes,
per livestock unit for the animals', per yield for milk (policy.gms then multiplies by the livestock units or the
milk yield / 1000).
"""
from __future__ import annotations

from collections import defaultdict

from capri_mod.supply import inputs as _inputs


def _load(inp):
    def csv(name):
        return inp.csv(name, "policy", keep_default_na=False)

    return {"rates": csv("nordic_aid_rates.csv"), "ceilings": csv("nordic_aid_ceilings.csv"),
            "shares": csv("nordic_aid_region_shares.csv"), "schemes": csv("nordic_aid_schemes.csv")}


def data(inp=None) -> dict:
    """The Nordic aid tables (capri_data/<base year>/policy/nordic_aid_*.csv, build_nordic_aid.py), read once per run."""
    inp = inp or _inputs.current()
    return inp.cached("nordic_aid", _load)


def nordic_declarations(year: int, d: dict = None):
    """The Nordic aid's declarations of the year: ({(region, scheme): {"rates": {group: EUR}, "APPTYPE": type}},
    {(member state, scheme): {"CEILVAL": million EUR}}); empty before the year the file declares (1995)."""
    d = d or data()
    apptype = dict(zip(d["schemes"].scheme, d["schemes"].apptype))
    first = int(d["schemes"].year.min()) if len(d["schemes"]) else None
    if first is None or year < first:
        return {}, {}
    share = defaultdict(dict)
    for r, n, v in zip(d["shares"].region, d["shares"].nordic_region, d["shares"].share):
        share[str(r)][str(n)] = float(v)
    rate = defaultdict(float)
    for s, g, n, v in zip(d["rates"].scheme, d["rates"].group, d["rates"].nordic_region, d["rates"].rate):
        rate[(str(s), str(g), str(n))] += float(v)
    decl = {}
    for r, by_n in share.items():
        for (s, g, n), v in rate.items():
            if n in by_n:
                x = decl.setdefault((r, s), {"rates": {}})
                x["rates"][g] = x["rates"].get(g, 0.0) + by_n[n] * v
    ceilings = {(str(m), str(s)): {"CEILVAL": float(v)}
                for s, m, v in zip(d["ceilings"].scheme, d["ceilings"].ms, d["ceilings"].ceiling_meur)}
    for (m, s) in ceilings:
        decl.setdefault((m, s), {"rates": {}})
    for (r, s), x in decl.items():
        if (r, s) in ceilings or any(x["rates"].values()):
            x["APPTYPE"] = apptype[s]
    return decl, ceilings
