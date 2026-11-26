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
                    so GROF and UVAG as CAPRI's; a fodder crop's at CAPRI's UVAG(FODDO), the fed fodder's value x (1 -
                    p_onFarmShare), in fresh matter, CAPRI's unit: IncomeDistributionModule.crop_fodder_output, K213); the
                    residues' nutrients MANN, MANP, MANK in quantity at the member state's unit value
                    (IncomeDistributionModule.crop_residue_nutrients, CAPRI's PACT_TO_O; their secondary revenue SREV:
                    KNOWN_ISSUES K212). The straw (STRA) at zero, as CAPRI's 2030 (K211).
           inputs:  at the 2030 market year CAPRI's directly yield-dependent inputs item by item (crop_inputs_2030.csv,
                    x TF_I, in the model's money; their sum is DATA_TOIN_Y's first term), the 2030 NPK need per nutrient
                    in quantity at its unit value (NITF, PHOF, POTF; capri_mod/fert/npk.py); at the base year the
                    margin's input cost in one item (TOIN_lin: variable_costs.csv, CAPRI's 2017 TOIN, not item by item).
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
                    difference (a fodder crop's at UVAG(FODDO), as the crop's), INPO, PLAP, the fertiliser (FERT, the margin's fertiliser cost basis, as I1 books it)
                    and the other inputs (OTHER_I), the residues' nutrients' difference; its premium difference in
                    PRME.
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
    "MGVA", "AGGT" (I1's MGVA), "DIFF" (MGVA - AGGT), "DIFF_act" {activity: EUR million}, "by_act" (DataFrame side,
    item, activity, EAAG: the items by the activity holding them, the technology mix's with its crop, None the
    region's), "other_o" and "young" (_other_output_parts: the animals' OTHER_O by CAPRI output, the young animals'
    heads), "products_t" (_animal_products_t: the animals' market products in 1000 t), and the accounts at producer and basic prices, "purchases", "EAAP", "EAAB" (eaap_eaab, income I2b); a member
    state's are income/eaa_ms.py's (I2c)}."""
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
    by_act = {}        # (side, item, activity or None) -> EUR million: the item's value by the activity that holds it

    def add(a, side, item, per_unit, L, kg=None, uv=None, owner=None):
        if not per_unit or not L:
            return
        k_ = (side, item, a if a is not None else owner)
        by_act[k_] = by_act.get(k_, 0.0) + float(per_unit) * float(L) / 1000.0
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
    npk_uv = _crop_npk_unit_values(region) if npk else {}
    feed_t = getattr(res, "feed_t", None) or {}
    feed_p = getattr(res, "feed_price", None) or {}
    feed_lin = getattr(res, "feed_lin", None) or {}
    ic = getattr(data, "livestock_input_cost", None)
    fo, fom = IDM.crop_residue_nutrients(m)
    fod = IDM.crop_fodder_output(region, m)
    for a, L in lev.items():
        if L <= 0:
            continue
        # a fodder crop's output at CAPRI's UVAG(FODDO), the fed fodder's value on the part not lost (K213)
        f_ = IDM.fodder_output_ratio(fod[a]) if a in fod else 1.0
        for it, kg, uv, v in oi.get(a, ()):
            add(a, "O", it, v * f_, L, *_fodder_q(fod.get(a), v * f_, kg, uv, f_))
        # the solve's changes of the net revenue after its first computation, by item (SupplyModule._nr_item)
        for side, it, v, kg, uv in nri.get(a, ()):
            add(a, side, it, v, L, kg if kg else None, uv)
        if a in CROPS:
            # the residues' nutrients (MANN, MANP, MANK) in quantity at the member state's unit value
            for it, (q, uv) in (fo.get(a) or {}).items():
                add(a, "O", it, float(q) * float(uv) / 1000.0, L, kg=float(q), uv=float(uv))
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
                    # in quantity (the need, kg per ha) at the nutrient's unit value where it has one (income I2c)
                    u_ = npk_uv.get(n)
                    add(a, "I", n, v, L, *((v * 1000.0 / u_, u_) if u_ else ()))
            else:
                c0 = float(data.variable_costs.get(a, 0.0))
                add(a, "I", "TOIN_lin", c0 if np.isfinite(c0) else 0.0, L)
        elif a in getattr(m, "OTHER_ANIMALS", ()):
            # the other animals: their inputs per unit in one item (TOIN_lin: variable_costs.csv, CAPRI's TOIN of OANI)
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
        f_ = IDM.fodder_output_ratio(fod[a]) if a in fod else 1.0         # a fodder crop's at UVAG(FODDO) (K213)
        add(None, "O", it, v * f_, z, *_fodder_q(fod.get(a), v * f_, kg, uv, f_), owner=a)
        for i, v in pa["I"].items():
            add(None, "I", i, v, z, owner=a)
        for it, q in (fom.get(a) or {}).items():
            uv = float(fo[a][it][1])
            add(None, "O", it, float(q) * uv / 1000.0, z, kg=float(q), uv=uv, owner=a)
    # the mitigation options at the region (EUR 1000; register DEP-54)
    for side, k in (("I", "mitiI"), ("O", "mitiO")):
        add(None, side, k, float(ip.get(k, 0.0) or 0.0), 1.0)
    other_o, young = _other_output_parts(region, m, lev, by_act)
    products_t = _animal_products_t(region, getattr(supply_module, "data", None), lev)
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
    out = {"items": items, "TOOU": O_tot, "TOIN": I_tot, "PRME": prme, "MGVA": mg, "AGGT": float(ip["MGVA"]) / 1000.0,
           "DIFF": mg - float(ip["MGVA"]) / 1000.0, "DIFF_act": diff_act,
           # the items' values by the activity holding them (the technology mix's with its crop; None: the region's),
           # for a member state's accounts at producer and basic prices (income I2c, capri_mod/income/eaa_ms.py)
           "by_act": pd.DataFrame([{"side": k[0], "item": k[1], "activity": k[2], "EAAG": v} for k, v in by_act.items()],
                                  columns=["side", "item", "activity", "EAAG"]),
           "other_o": other_o, "young": young, "products_t": products_t}
    out.update(eaap_eaab(region, res, m, lev, int(sim) if sim else None))
    return out


#: the model's nutrients -> CAPRI's mineral fertilisers (FNUT)
FNUT_OF = {"N": "NITF", "P": "PHOF", "K": "POTF"}


def eaap_eaab(region, res, m, lev, sim=None) -> dict:
    """CAPRI's accounts at producer and basic prices of a region at its solution (income I2b; reports/sol_simy.gms
    l. 2547-2562), EUR million: {"purchases": DataFrame (item NITF | PHOF | POTF, NETF kt, UVAP and UVAB EUR per t,
    EAAP, EAAB), "EAAP": {TOOU, TOIN, GVAP, PRME, MGVA}, "EAAB": {TOOU, TOIN, GVAB}}.

    A regional unit's NETF is the mineral fertilisers' purchases at the solution alone (l. 309: the products' net trade
    is a member state's balance, l. 1966-1970), so its EAAP and EAAB hold the purchases and the premiums, as CAPRI's
    NUTS 2 rows (DE110000 at the 2030 reference: EAAP NITF = 29.758 kt x 1,110.35 EUR/t = 33.04, TOIN 58.64):
      NETF      DATA_NETF_FNUT, the regional NLP's purchases (SupplyResult.fert_npk, t; supply/capri_regional_nlp.py)
      UVAP, UVAB  the member state's base year unit values (fnut_unit_values_2017.csv, tools/build/
                build_fnut_unit_values.py) at the simulation year by inflation (DATA_UVAP_IO_SIMY, DATA_UVAB_IO_SIMY;
                p_inflationFactor the money deflator of the year, capri_mod/data/inputs.py money_deflator, CAPRI's
                p_infl^(SIMY - BAS)), over the money deflator: the model's 2017 money
      PRME      DATA_EAAP_PRMDE over the activities' premiums x levels and the technology mix's premium difference on the
                area moved (as income I1's PRME)
    Departures from CAPRI: EAAP's PRMD (the declared premiums, DATA(MPACT, PRMD) = the sum over the schemes of
    p_premPaym's PRMD, policy/prmcut.gms l. 321-322) is not reported: the model's activities carry their paid premium
    (PRME) only, the declared ones being in the premium module (capri_mod/policy); it does not enter MGVA (l. 2562).
    Empty where the solve has no fertilisation block (outside CAPRI's EU data)."""
    from capri_mod.coupling.equations.inflation_and_trend_interpolation import DATA_UVAB_IO_SIMY, DATA_UVAP_IO_SIMY
    from capri_mod.coupling.equations.sol_simy import (DATA_EAAB_GVAB, DATA_EAAB_IO, DATA_EAAP_GVAP, DATA_EAAP_IO,
                                                       DATA_EAAP_MGVA, DATA_EAAP_PRMDE, DATA_GEAAC_TOIN,
                                                       DATA_GEAAC_TOOU, DATA_NETF_FNUT)
    from capri_mod.data.definitions import capri_ms
    from capri_mod.data.inputs import money_deflator
    from capri_mod.supply import inputs as _inputs
    npk = getattr(res, "fert_npk", None) or getattr(getattr(m, "res", None), "last_npk", None) or {}
    if not npk:
        return {}
    inp = _inputs.current()

    def load(i):
        t = i.csv("fnut_unit_values_2017.csv", "environment")
        return {(str(a), str(b)): (float(c), float(d)) for a, b, c, d in zip(t.ms, t.fnut, t.uvap_eur_t, t.uvab_eur_t)}
    uv = inp.cached("income_fnut_unit_values", load)
    defl = money_deflator(sim) if sim else 1.0
    ms = capri_ms(region)
    rows = []
    for nut, rec in npk.items():
        f = FNUT_OF.get(nut)
        if f is None or (ms, f) not in uv:
            continue
        netf = DATA_NETF_FNUT(-float(rec.get("purchase", 0.0) or 0.0) / 1000.0)          # t -> kt
        uvp = DATA_UVAP_IO_SIMY(uv[(ms, f)][0], defl) / defl
        uvb = DATA_UVAB_IO_SIMY(uv[(ms, f)][1], defl) / defl
        rows.append({"item": f, "NETF": netf, "UVAP": uvp, "EAAP": DATA_EAAP_IO(netf, uvp), "UVAB": uvb,
                     "EAAB": DATA_EAAB_IO(netf, uvb)})
    if not rows:
        return {}
    pur = pd.DataFrame(rows, columns=["item", "NETF", "UVAP", "EAAP", "UVAB", "EAAB"]).sort_values("item",
                                                                                                  ignore_index=True)
    pr = getattr(m, "premiums", None)
    mz = dict(getattr(res, "technology_mix", None) or {})
    tm = getattr(getattr(m, "data", None), "techn_mix", None)
    prs = [float(pr.get(a, 0.0)) if pr is not None else 0.0 for a in lev]
    lvs = [float(lev[a]) for a in lev]
    for a, z in mz.items():
        if tm is not None and a in tm.index and pr is not None:
            prs.append(float(tm.at[a, "prem_diff_share"]) * float(pr.get(a, 0.0)))
            lvs.append(float(z))
    prme = DATA_EAAP_PRMDE(prs, lvs)
    p_tou, p_tin = DATA_GEAAC_TOOU([]), DATA_GEAAC_TOIN(pur.EAAP)
    b_tou, b_tin = DATA_GEAAC_TOOU([]), DATA_GEAAC_TOIN(pur.EAAB)
    gvap = DATA_EAAP_GVAP(p_tou, p_tin)
    return {"purchases": pur,
            "EAAP": {"TOOU": p_tou, "TOIN": p_tin, "GVAP": gvap, "PRME": prme, "MGVA": DATA_EAAP_MGVA(gvap, prme)},
            "EAAB": {"TOOU": b_tou, "TOIN": b_tin, "GVAB": DATA_EAAB_GVAB(b_tou, b_tin)}}


def _fodder_q(rec, value, kg, uv, f_) -> tuple:
    """(kg per unit, EUR per t) of a crop's output item: a fodder crop's (rec: IncomeDistributionModule.
    crop_fodder_output's) in fresh matter at UVAG(FODDO) = PSHW x (1 - p_onFarmShare), CAPRI's unit (the grassland's
    margin holds dry matter); another crop's as the margin's (kg None: the value form)."""
    if rec is not None:
        from capri_mod.coupling.equations.sol_simy import DATA_UVAG_FODDO
        u_ = DATA_UVAG_FODDO(rec[2], rec[3])
        if u_ > 0:
            return float(value) * 1000.0 / u_, u_
    return (kg if kg else None), (uv * f_ if uv is not None else uv)


def _animal_products_t(region, data, lev) -> pd.DataFrame:
    """The animals' market products in quantity at the levels, for a member state's accounts at basic prices (income
    I2c): DataFrame activity, item (CAPRI's output), GROF (1000 t): the run's outputs per head (data
    "livestock_output_by_product_coef", t; CAPRI's 2030 at the 2030 market year, projection_module
    SUPBAL_outputsPerHead_Y) x level. Empty without the table."""
    t = data.get("livestock_output_by_product_coef") if hasattr(data, "get") else None
    rows = []
    if isinstance(t, pd.DataFrame) and region in t.index:
        for c, v in t.loc[region].items():
            a, it = str(c).split(".", 1)
            if pd.notna(v) and float(v) > 0 and lev.get(a, 0.0) > 0:
                rows.append({"activity": a, "item": it, "GROF": float(v) * lev[a]})
    return pd.DataFrame(rows, columns=["activity", "item", "GROF"])


def _crop_npk_unit_values(region) -> dict:
    """{NITF, PHOF, POTF: EUR per t}: the region's NPK unit values of _crop_npk_parts (capri_mod/fert/npk.py), the
    ones it has."""
    from capri_mod.fert.npk import NPKData, NUTRIENTS
    D = NPKData.get()
    cr = D.capri_region(region)
    code = {"N": "NITF", "P": "PHOF", "K": "POTF"}
    out = {}
    for n in NUTRIENTS:
        r_ = D.region(cr, n)
        if r_ is not None and r_.uvag_eur_t == r_.uvag_eur_t and float(r_.uvag_eur_t) > 0:
            out[code.get(n, n)] = float(r_.uvag_eur_t)
    return out


#: the farm balances' young animals per category of the young-animal tables -> CAPRI's outputs (OYANI)
def _young_codes():
    from capri_mod.projection.prices import YOUNG_PRODUCTS
    return {g: "/".join(v) for g, v in YOUNG_PRODUCTS.items()}


def _other_output_parts(region, m, lev, by_act):
    """An animal's other outputs (OTHER_O: its output value per head less its market products', SupplyModule.
    _output_items) by CAPRI output, for a member state's accounts at producer prices (income I2c), EUR million:
    (DataFrame activity, item, EAAG; DataFrame item, iyani, GROF, USE: the young animals' heads, 1000).

      MANN, MANP, MANK  the manure per head (capri_mod/fert/npk.py manure_coef_table, kg) x level x the member state's
                        unit value (ms_unit_values_2017.csv, CAPRI's UVAG at "BAS", tools/build/build_ms_farm_balance.py)
      COMF, SGMF        the milk for feeding per head (the fodder balances' producers, t; FEED_TO_O) x its value
      the young animals the rest, over the categories the activity produces (the young-animal tables, SupplyModule
                        young_animal_table) by their value per head x coefficient; CAPRI's OYANI (projection/prices.py
                        YOUNG_PRODUCTS; the pooled tables' categories as "YBUL/YHEI", "YCAM/YCAF"); an activity that
                        produces none keeps the rest as OTHER_O.
    The young animals' heads produced (GROF) and used (USE, CAPRI's IYANI of O_TO_YANI) at the levels: the
    categories' coefficients x level, the cattle member splits' columns not apart."""
    from capri_mod.data.definitions import capri_ms, capri_pairs
    from capri_mod.fert.npk import manure_coef_table
    from capri_mod.supply import inputs as _inputs
    cols_o, cols_y = ["activity", "item", "EAAG"], ["item", "iyani", "GROF", "USE"]
    oth = {k[2]: v for k, v in by_act.items() if k[0] == "O" and k[1] == "OTHER_O" and k[2] is not None}
    yc = m._young_animal_coefs() if hasattr(m, "_young_animal_coefs") else {}
    codes = _young_codes()
    o2i = {o: i for o, i in capri_pairs("O_TO_YANI")}
    young = []
    for g, rec in yc.items():
        if g not in codes:
            continue
        pr = sum(float(v) * lev.get(a, 0.0) for a, v in (rec.get("produce") or {}).items())
        us = sum(float(v) * lev.get(a, 0.0) for a, v in (rec.get("use") or {}).items())
        young.append({"item": codes[g], "iyani": "/".join(o2i.get(o, "") for o in codes[g].split("/")),
                      "GROF": pr, "USE": us})
    young = pd.DataFrame(young, columns=cols_y)
    if not oth:
        return pd.DataFrame(columns=cols_o), young
    inp = _inputs.current()

    def load(i):
        t = i.csv("ms_unit_values_2017.csv", "supply")
        return {(str(a), str(b)): float(c) for a, b, c in zip(t.ms, t["item"], t.uvag) if c == c}
    uv = inp.cached("income_ms_unit_values", load)
    ms = capri_ms(region)
    man = {it: manure_coef_table(n) for it, n in (("MANN", "N"), ("MANP", "P"), ("MANK", "K"))}
    f2o = {f: o for f, o in capri_pairs("FEED_TO_O") if o in ("COMF", "SGMF")}
    fb = getattr(getattr(m, "data", None), "fodder_balance", None) or {}
    rows = []
    for a, V in oth.items():
        L = lev.get(a, 0.0)
        parts = {}
        for it, t in man.items():
            if L > 0 and region in t.index and a in t.columns and pd.notna(t.at[region, a]) and (ms, it) in uv:
                parts[it] = float(t.at[region, a]) * L * uv[(ms, it)] / 1e6          # kg x 1000 heads x EUR/t
        for f, rec in fb.items():
            p_ = (rec or {}).get("producers") or {}
            if L > 0 and f in f2o and a in p_:
                parts[f2o[f]] = parts.get(f2o[f], 0.0) + float(p_[a]) * L * float(rec["value_eur_t"]) / 1000.0
        w = {codes[g]: float((r_.get("produce") or {}).get(a, 0.0)) * float(r_.get("value_eur_head", 0.0) or 0.0)
             for g, r_ in yc.items() if g in codes and (r_.get("produce") or {}).get(a)}
        rest = float(V) - sum(parts.values())
        if sum(w.values()) > 0:
            for it, v in w.items():
                parts[it] = parts.get(it, 0.0) + rest * v / sum(w.values())
        else:
            parts["OTHER_O"] = rest
        rows += [{"activity": a, "item": it, "EAAG": v} for it, v in parts.items()]
    return pd.DataFrame(rows, columns=cols_o), young


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
