r"""CAPRI's farm profit and domestic support by market product per member state (reports/welfare.gms l. 441-468,
714-749, star 3.0; the statements in capri_mod/market/equations/welfare.py): the farms' ProfitAgr by the main
product of their activities and the budget's support PSEs by product, the rows XX1 of CAPRI's welfare table (the
market's products, INPE for the activities and outputs outside them, LAND for the rents).

CAPRI, per member state with supply models (RMSSUP):
  ProfitAgr(XX1)   sum over the activities of PACT_TO_XX(a, XX1) of MGVA_a x LEVL_a x 0.001 (l. 448-449); INPE adds the
                   outputs less the inputs no activity holds (l. 454-456); LAND the rents with a minus sign (l. 460);
  PSEs(XX1)        - the premiums paid to the product's outputs (FEOP over CAP_TO_TRD) and the market's support wedges
                   (l. 716-740); INPE - the FEOGA outlays of the outputs outside the market's products (l. 745-746).
The sets are CAPRI's as its run built them (sim_ini_21730: capri_data/codes/capri/PACT_TO_XX.csv, CAP_TO_TRD.csv).

The model, per member state of the run's units (all of a member state's units in a full-EU run), EUR million in its
2017 money:
  - a model activity's MGVA (income I1, SupplyResult.income MGVA_act, EUR per ha or head) x its level goes to the
    product of its CAPRI members (CAPRI_MEMBERS; all members of a model activity have the same product in CAPRI's
    PACT_TO_XX, checked), the technology mix's MGVA on the area moved (MGVA_mix x technology_mix) with its crop;
  - INPE adds the mitigation options' revenue less their cost, which the model books at the region (register DEP-54);
  - LAND is the regions' rents (the welfare table's RENT, coupling/reporting.py DATA_ProfitLandUse);
  - PSEs take the premium outlays per product (income I4, capri_mod/income/feoga.py feop_by_product): the market's
    support wedges, export subsidies and intervention are 0 for the EU at CAPRI's 2030 reference.
The products' rows add up to the member state's ProfitAgr (MGVA - RENT) and its - PRME. Register DEP-58.
"""
from __future__ import annotations

from collections import defaultdict

import pandas as pd


def pact_to_xx() -> dict:
    """{model activity: its market product XX1} through its CAPRI members' PACT_TO_XX (capri_data/codes/capri/
    PACT_TO_XX.csv); a model activity whose members have different products is an error."""
    from capri_mod.data.definitions import CAPRI_MEMBERS, capri_pairs
    p2x = defaultdict(set)
    for a, x in capri_pairs("PACT_TO_XX"):
        p2x[a].add(x)
    out = {}
    for a, ms in CAPRI_MEMBERS.items():
        xs = set().union(*(p2x.get(m, set()) for m in ms))
        if len(xs) > 1:
            raise ValueError(f"{a}: its CAPRI members {ms} have several market products {sorted(xs)} in PACT_TO_XX")
        if xs:
            out[a] = next(iter(xs))
    return out


def cap_to_trd() -> dict:
    """{CAPRI output: its market product} (capri_data/codes/capri/CAP_TO_TRD.csv)."""
    from capri_mod.data.definitions import capri_pairs
    return {o: x for o, x in capri_pairs("CAP_TO_TRD")}


def welfare_by_product(supply_results, feop=None, rents=None) -> pd.DataFrame:
    """ProfitAgr and PSEs per member state and product XX1 (module docstring), EUR million: rows (member state,
    product), columns ProfitAgr, PSEs. feop: feop_by_product's table (None: no PSEs); rents: {region: RENT, EUR
    million} (the welfare table's; None: no LAND row). Empty without the regions' income."""
    from capri_mod.data.definitions import capri_ms
    from capri_mod.market.equations.welfare import (p_welfareRes_ProfitAgr, p_welfareRes_ProfitAgr_INPE,
                                                    p_welfareRes_ProfitAgr_LAND, p_welfareRes_PSEs_INPE,
                                                    p_welfareRes_PSEs_XX1)
    xx = pact_to_xx()
    parts = defaultdict(lambda: ([], []))            # (ms, product) -> (MGVA per unit, level)
    miti = defaultdict(lambda: [0.0, 0.0])           # ms -> [mitiO, mitiI], EUR million
    rent = defaultdict(float)
    for reg, res in supply_results.items():
        ip = getattr(res, "income", None)
        acts = getattr(res, "activities", None)
        if not ip or acts is None:
            continue
        ms = capri_ms(reg)
        for a, v in (ip.get("MGVA_act") or {}).items():
            k = (ms, xx.get(a, "INPE"))
            parts[k][0].append(float(v))
            parts[k][1].append(float(acts.get(a, 0.0) or 0.0) * 0.001)      # 1000 ha or heads x 0.001: EUR million
        for a, z in (getattr(res, "technology_mix", None) or {}).items():
            if a in (ip.get("MGVA_mix") or {}):
                k = (ms, xx.get(a, "INPE"))
                parts[k][0].append(float(ip["MGVA_mix"][a]))
                parts[k][1].append(float(z) * 0.001)
        miti[ms][0] += float(ip.get("mitiO", 0.0) or 0.0) * 0.001
        miti[ms][1] += float(ip.get("mitiI", 0.0) or 0.0) * 0.001
        if rents is not None and reg in rents:
            rent[ms] += float(rents[reg])
    rows = defaultdict(dict)
    for (ms, x), (m_, l_) in parts.items():
        rows[(ms, x)]["ProfitAgr"] = p_welfareRes_ProfitAgr(m_, l_)
    for ms, (mo, mi) in miti.items():
        rows[(ms, "INPE")]["ProfitAgr"] = p_welfareRes_ProfitAgr_INPE(rows[(ms, "INPE")].get("ProfitAgr", 0.0),
                                                                      [mo], [mi])
        if rents is not None:
            rows[(ms, "LAND")]["ProfitAgr"] = p_welfareRes_ProfitAgr_LAND(rent[ms])
    if feop is not None and len(feop):
        c2t = cap_to_trd()
        fx, fi = defaultdict(list), defaultdict(list)
        for (ms, o), v in feop["FEOP"].items():
            if o in c2t:
                fx[(ms, c2t[o])].append(float(v))
            else:
                fi[ms].append(float(v))
        for k, v in fx.items():
            rows[k]["PSEs"] = p_welfareRes_PSEs_XX1(v)
        for ms, v in fi.items():
            rows[(ms, "INPE")]["PSEs"] = p_welfareRes_PSEs_INPE(v)
    out = pd.DataFrame.from_dict(rows, orient="index", columns=["ProfitAgr", "PSEs"])
    if len(out):
        out.index = pd.MultiIndex.from_tuples(out.index, names=["member_state", "product"])
        out = out.sort_index()
    return out
