r"""CAPRI's economic accounts for agriculture of a region at its solution, item by item (income I2): the gross account EAAG
by output and input, its totals and its modified gross value added, against the activity-based income AGGT (income
I1). CAPRI's report (reports/sol_simy.gms, star 3.0) takes each activity's outputs and inputs at the solution (l.
377-390: the year's coefficients, weighted with the crops' technologies), sums them over the activities (GROF, l.
685-687), values them (EAAG = GROF x UVAG, l. 2549), totals them (TOOU, TOIN, MGVA, l. 2557-2566) and computes the
difference to AGGT (l. 2600-2615, a tolerance of EUR 1000; its assertion is commented out). The statements are in
coupling/equations/sol_simy.py.

What the model holds per activity at the solution, by item (EUR per ha or head, the model's money; levels in 1000 ha or
heads):
  crops    outputs: the product, its yield x the solve's price (SupplyModule._output_items: a quantity and a unit value,
                    so GROF and UVAG as CAPRI's). Not valued: the straw (STRA), which CAPRI's crops sell at its unit
                    value (their secondary revenue SREV; KNOWN_ISSUES K207, register DEP-54).
           inputs:  at the 2030 market year CAPRI's directly yield-dependent inputs item by item (crop_inputs_2030.csv,
                    x TF_I, in the model's money; their sum is DATA_TOIN_Y's first term), the 2030 NPK need per nutrient
                    at its unit value (NITF, PHOF, POTF; capri_mod/fert/npk.py); at the base year the margin's input
                    cost in one item (TOIN_lin: variable_costs.csv, CAPRI's 2017 TOIN, not item by item).
  animals  outputs: the market products' values per head with the solve's price changes and the rest of the output value
                    (the young animals and the other outputs, OTHER_O: one item; SupplyModule._output_items).
           inputs:  the input cost table's items per head (livestock_input_cost: ELEC, EGAS, INPO, IPHA, REPB, REPM and
                    the young animals bought, YOUNG; at the 2030 market year CAPRI's 2030 items but YOUNG and FEED), for
                    a herd fed in the regional model its solved ration by feed (SupplyResult.feed_t x feed_price, with
                    GROF in 1000 t and UVAG in EUR per t) in place of the table's FEED.
  the solve's changes  of the net revenues after their first computation, by item (SupplyModule._nr_item, ev.nr_items):
                    the crops' yields' changes (the price response, the pesticide loss, the organic yield gap) on their
                    product, the Green Deal's input changes on PLAP and INPO, the yield-dependent inputs' update on PLAP,
                    INPO and OTHER_I, the organic land's fertiliser saving on FERT, the young animals' price changes on
                    OTHER_O and YOUNG, the options' costs charged on the margins (outside the regional NLP) on mitiI.
  the technology mix  on the area moved to T1 (z), the terms of T1 less T2 (ev.mix_parts): the product's output
                    difference, INPO, PLAP, the fertiliser (FERT, the margin's fertiliser cost basis, as I1 books it)
                    and the other inputs (OTHER_I); its premium difference in PRME.
  region   the mitigation options' cost (mitiI, an input) and revenue (mitiO, an output) at the region (register DEP-54).
Where the model holds an item's value per unit and not its quantity and unit value apart, GROF is the value (EUR million)
and UVAG 1000 (DATA_EAAG_IO's departure). PRME as I1's. DIFF = EAAG's MGVA - AGGT's, by activity too (DIFF_act): what the
items above do not hold of I1's margins (the net revenues' other changes within the solve).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def eaag_items(region, res, supply_module, ip=None) -> dict:
    """The region's gross account at its solution (module docstring), EUR million: {"items": DataFrame (item, side "O"
    or "I", GROF: 1000 t or, value-only items, EUR million; UVAG: EUR per t or 1000; EAAG), "TOOU", "TOIN", "PRME",
    "MGVA", "AGGT" (I1's MGVA), "DIFF" (MGVA - AGGT), "DIFF_act" {activity: EUR million}}."""
    from capri_mod.coupling.equations.sol_simy import (DATA_EAAG_IO, DATA_EAAG_MGVA, DATA_GEAAC_TOIN, DATA_GEAAC_TOOU,
                                                       DATA_GROF_IO)
    from capri_mod.data.definitions import ANIMALS, CROPS
    from capri_mod.data.inputs import money_deflator
    from capri_mod.income.income_module import IncomeDistributionModule as IDM
    m = getattr(supply_module, "_models", {}).get(region)
    acts = getattr(res, "activities", None)
    if m is None or acts is None:
        raise ValueError(f"{region}: no solved supply model")
    ip = ip if ip is not None else (getattr(res, "income", None)
                                    or IDM(getattr(supply_module, "data", None)).income_parts(region, res, supply_module))
    oi = getattr(m, "output_items", None) or {}
    rows = {}          # (side, item) -> {"q": [(kg or EUR per unit, level)], "uv": EUR per t or None}
    own = {}           # activity -> outputs - inputs per unit, EUR

    def add(a, side, item, per_unit, L, kg=None, uv=None):
        if not per_unit or not L:
            return
        r_ = rows.setdefault((side, item), {"q": [], "uv": uv if kg is not None else None, "qform": kg is not None})
        if r_["qform"] and kg is not None and abs(float(uv) - float(r_["uv"])) <= 1e-9 * max(1.0, abs(float(uv))):
            r_["q"].append((float(kg), float(L)))
        else:
            # a value-only part of an item that has a quantity elsewhere, or a part at another unit value (a fodder's
            # value differs by herd): the item takes the value form
            if r_["qform"]:
                r_["q"] = [(k_ * float(r_["uv"]) / 1000.0, l_) for k_, l_ in r_["q"]]
                r_["qform"], r_["uv"] = False, None
            r_["q"].append((float(per_unit), float(L)))
        if a is not None:
            own[a] = own.get(a, 0.0) + (float(per_unit) if side == "O" else -float(per_unit))

    lev = {a: float(acts.get(a, 0.0) or 0.0) for a in m.net_revenues.index}
    data = m.data
    toin = IDM.crop_toin_y(region, m)
    sim = getattr(data, "sim_year", None)
    ci = getattr(data, "crop_inputs_2030", None)
    tf = float(m._greendeal_tech_progress()) if toin else 1.0
    defl = money_deflator(int(sim)) if sim else 1.0
    nri = dict(getattr(getattr(m, "ev", None), "nr_items", None) or {})
    npk = _crop_npk_parts(region, m, toin)
    feed_t = getattr(res, "feed_t", None) or {}
    feed_p = getattr(res, "feed_price", None) or {}
    feed_lin = getattr(res, "feed_lin", None) or {}
    ic = getattr(data, "livestock_input_cost", None)
    for a, L in lev.items():
        if L <= 0:
            continue
        for it, kg, uv, v in oi.get(a, ()):
            add(a, "O", it, v, L, kg if kg else None, uv)
        # the solve's changes of the net revenue after its first computation, by item (SupplyModule._nr_item)
        for side, it, v, kg, uv in nri.get(a, ()):
            add(a, side, it, v, L, kg if kg else None, uv)
        if a in CROPS:
            if a in toin:
                # CAPRI's TOIN at the year's coefficients (DATA_TOIN_Y): the yield-dependent inputs item by item where
                # the builder has them (else one item, IY), the NPK need per nutrient
                if ci is not None and a in ci.index:
                    for i, v in ci.loc[a].items():
                        if pd.notna(v) and float(v):
                            add(a, "I", i, float(v) * tf / defl, L)
                else:
                    add(a, "I", "IY", float(toin[a][1]) - sum(npk.get(a, {}).values()), L)
                for n, v in npk.get(a, {}).items():
                    add(a, "I", n, v, L)
            else:
                c0 = float(data.variable_costs.get(a, 0.0))
                add(a, "I", "TOIN_lin", c0 if np.isfinite(c0) else 0.0, L)
        elif a in ANIMALS:
            fed = a in feed_lin
            if ic is not None and a in ic.index:
                for i, v in ic.loc[a].items():
                    if pd.notna(v) and not (i == "FEED" and fed):
                        add(a, "I", i, float(v), L)
            if fed:
                for f, t in (feed_t.get(a) or {}).items():
                    p_ = float((feed_p.get(a) or {}).get(f, 0.0))
                    # t and EUR per kg: per head kg = t / L (L in 1000 heads), EUR per t = 1000 x EUR per kg
                    add(a, "I", f, float(t) * p_ / L, L, kg=float(t) / L, uv=1000.0 * p_)
    # the technology mix on the area moved to T1 (z, 1000 ha): T1 - T2 per ha by item; its premium difference is in PRME
    mz = dict(getattr(res, "technology_mix", None) or {})
    mp = dict(getattr(getattr(m, "ev", None), "mix_parts", None) or {})
    for a, z in mz.items():
        pa = mp.get(a)
        if pa is None or not z:
            continue
        it, kg, uv, v = pa["O"]
        add(None, "O", it, v, z, kg if kg else None, uv)
        for i, v in pa["I"].items():
            add(None, "I", i, v, z)
    # the mitigation options at the region (EUR 1000; register DEP-54)
    for side, k in (("I", "mitiI"), ("O", "mitiO")):
        add(None, side, k, float(ip.get(k, 0.0) or 0.0), 1.0)
    out = []
    for (side, item), r_ in rows.items():
        g = DATA_GROF_IO([k_ for k_, _ in r_["q"]], [l_ for _, l_ in r_["q"]])
        uv = float(r_["uv"]) if r_["qform"] else 1000.0
        out.append({"item": item, "side": side, "GROF": g, "UVAG": uv, "EAAG": DATA_EAAG_IO(g, uv)})
    items = pd.DataFrame(out, columns=["item", "side", "GROF", "UVAG", "EAAG"]).sort_values(["side", "item"],
                                                                                         ignore_index=True)
    O_tot = DATA_GEAAC_TOOU(items.loc[items.side == "O", "EAAG"])
    I_tot = DATA_GEAAC_TOIN(items.loc[items.side == "I", "EAAG"])
    prme = float(ip["PRME"]) / 1000.0
    mg = DATA_EAAG_MGVA(O_tot, I_tot, prme)
    pr = getattr(m, "premiums", None)
    mga = ip.get("MGVA_act") or {}
    diff_act = {a: (own.get(a, 0.0) + float(pr.get(a, 0.0) if pr is not None else 0.0) - float(v)) * lev[a] / 1000.0
                for a, v in mga.items()}
    return {"items": items, "TOOU": O_tot, "TOIN": I_tot, "PRME": prme, "MGVA": mg, "AGGT": float(ip["MGVA"]) / 1000.0,
            "DIFF": mg - float(ip["MGVA"]) / 1000.0, "DIFF_act": diff_act}


def _crop_npk_parts(region, m, toin) -> dict:
    """{crop: {NITF, PHOF, POTF: EUR per ha}}, CAPRI's 2030 NPK need per nutrient at its unit value (capri_mod/fert/npk.py)
    for the crops crop_toin_y covers; their sum is IncomeDistributionModule.crop_npk_y."""
    if not toin:
        return {}
    from capri_mod.coupling.equations.calc_inc_indic import DATA_TOIN_Y
    from capri_mod.fert.npk import NPKData, NUTRIENTS
    D = NPKData.get()
    cr = D.capri_region(region)
    code = {"N": "NITF", "P": "PHOF", "K": "POTF"}
    uv = {}
    for n in NUTRIENTS:
        r_ = D.region(cr, n)
        uv[n] = float(r_.uvag_eur_t) if r_.uvag_eur_t == r_.uvag_eur_t else 0.0
    return {a: {code.get(n, n): DATA_TOIN_Y(0.0, 1.0, [D.crop_coef(cr, n, a, "need_kg_ha")], [uv[n]]) for n in NUTRIENTS}
            for a in toin}
