"""CAPRI's 2030 prices and premiums in the projected baseline, in 2017 money.

CAPRI's 2030 reference (the one JRC121368's Farm-to-Fork scenarios start from) is in current
prices: every non-agricultural input moves by one index (2030/2017 = 1.277, every member
state), agricultural outputs by their own projected prices, and CAP payments are nominal. The
model works in 2017 money, so its 2030 baseline takes each product's CAPRI price ratio over
that index (tools/build/build_price_trajectory_2030.py -> capri_data/baselines/capri_greendeal_ref/1730/trajectories/):

- crop producer prices (regional and EU), by member state and product;
- fodder (grass, silage maize, other fodder, fodder roots) is not marketed: its value is the shadow
  price of CAPRI's fodder balance, which CAPRI reports as its unit value. The base value of the
  model's fodder balance (the dual its PMP calibration makes optimal) takes CAPRI's 2030/2017 ratio
  of that value (grass 0.43 in France: more grass per animal in 2030);
- livestock: final-product values per head by product and market (milk, beef, pork, poultry,
  eggs, sheep meat; sheep and goat milk in the product total), young animals sold and bought
  (calves, young cattle, heifers, piglets) in total output and total inputs per head and as the
  base value of the young-animal markets, and purchased feed cereals and oilcakes in total inputs;
- premiums: crop premiums per hectare are CAPRI's 2030 PRME per region in 2017 money; animal
  premiums per head scale by CAPRI's 2030/2017 ratio (2017 activity levels as weights).

Input costs stay at 2017 values: CAPRI moves them with the deflator only, so in 2017 money they
do not change. Purchased protein feed follows CAPRI's 2030 oilcake producer prices (market baseline).
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import pandas as pd
from capri_mod.data.definitions import MS_CODE, is_eu
from capri_mod.tableio import read_input

#: crop products whose CAPRI price is applied (model price-table code -> CAPRI product)
CROP_PRODUCT = {c: c for c in (
    "SWHE", "DWHE", "RYEM", "BARL", "OATS", "OCER", "PARI", "RAPE", "SUNF", "SOYA", "OOIL", "PULS",
    "POTA", "SUGB", "TOMA", "OVEG", "APPL", "OFRU", "CITR", "TAGR", "TWIN", "OLIV", "TABO", "TOBA", "TEXT",
    "NURS", "FLOW", "OCRO", "OIND")}
CROP_PRODUCT.update({"CORN": "MAIZ", "MAIZ": "MAIZ", "WINE": "TWIN"})
#: fodder crops of the fodder balance -> CAPRI product (unit value = fodder shadow price)
FODDER_PRODUCT = {"GRAE": "GRAS", "GRAI": "GRAS", "MAIF": "MAIF", "OFAR": "OFAR", "ROOF": "ROOF"}   # CAPRI's products
#: livestock markets -> CAPRI product
MARKET_PRODUCT = {"MILK": "COMI", "BEEF": "BEEF", "PORK": "PORK", "POUL": "POUM", "EGGS": "EGGS",
                  "SGMT": "SGMT"}
#: young-animal goods -> CAPRI products (value = mean of their unit values, as in the builder)
YOUNG_PRODUCTS = {"calves_m": ("YCAM",), "calves_f": ("YCAF",), "young_m": ("YBUL",), "young_f": ("YHEI",),
                  "calves": ("YCAM", "YCAF"), "young": ("YBUL", "YHEI"), "cows": ("YCOW",),
                  "piglets": ("YPIG",)}
#: feed cereals priced in livestock costs (the supply module's FEED_CEREAL_MIX)
FEED_CEREAL_PRODUCT = {"SWHE": "SWHE", "BARL": "BARL", "CORN": "MAIZ", "RYEM": "RYEM", "OATS": "OATS", "OCER": "OCER"}
_CTRY = MS_CODE


def _ms(region: str) -> str:
    return _CTRY.get(str(region)[:2], str(region)[:2])


def load_price_tables(traj_dir: Path):
    pr = read_input(traj_dir / "capri_price_ratios_2030.csv")
    ratio = {(r.ms, r.product): float(r.real_ratio) for r in pr.itertuples()}
    eu = pr[pr["ms"].map(is_eu)].groupby("product")["real_ratio"].median().to_dict()
    cap = read_input(traj_dir / "capri_cap_premium_2030.csv", index_col=0)
    lsk = read_input(traj_dir / "capri_livestock_premium_ratio_2030.csv", index_col=0)
    lsk30 = read_input(traj_dir / "capri_livestock_premium_2030.csv", index_col=0)
    return ratio, eu, cap, lsk, lsk30


def apply_capri_prices_2030(data: Dict, traj_dir: Path, young_table: Dict, feed_cereal_mix: Dict,
                            cake_index=None, young_table_base: Optional[Dict] = None) -> Dict:
    """Put CAPRI's 2030 prices (2017 money) into a projected data dict, in place. Returns a summary. young_table: the
    young-animal coefficients of the year (2030: CAPRI's, KNOWN_ISSUES K178); young_table_base: the base year's, whose
    young animals the base year's total output and inputs per head hold (None: the year's table, the change of the
    value alone)."""
    ratio, eu, cap30, lsk, lsk30 = load_price_tables(traj_dir)
    r = lambda reg, prod: ratio.get((_ms(reg), prod), eu.get(prod))
    summary = {}

    # --- crop prices, regional and EU
    pr = data.get("producer_prices_regional")
    if isinstance(pr, pd.DataFrame):
        n = 0
        for col in pr.columns:
            prod = CROP_PRODUCT.get(col)
            if prod is None:
                continue
            f = pr.index.map(lambda reg: r(reg, prod) or 1.0)
            pr[col] = pr[col] * pd.Series(f, index=pr.index)
            n += 1
        summary["regional_crop_prices"] = n
    pe = data.get("producer_prices")
    p0 = pe.copy() if isinstance(pe, pd.Series) else None
    if isinstance(pe, pd.Series):
        for act in pe.index:
            prod = CROP_PRODUCT.get(act)
            if prod and prod in eu:
                pe[act] = pe[act] * eu[prod]

    # --- fodder: base value of the fodder balance (CAPRI's fodder unit value)
    fb = data.get("fodder_balance")
    if isinstance(fb, dict):
        n_f, fr = 0, []
        for reg, feeds in fb.items():
            for feed, rec in (feeds or {}).items():
                prod = next((FODDER_PRODUCT[c] for c in (rec.get("crops") or {}) if c in FODDER_PRODUCT), None)
                f = r(reg, prod) if prod else None
                if f and "value_eur_t" in rec:
                    rec["value_eur_t"] = float(rec["value_eur_t"]) * f
                    n_f += 1; fr.append(f)
        summary["fodder_values"] = n_f
        if fr:
            summary["fodder_value_ratio_median"] = float(pd.Series(fr).median())
        # CAPRI's own 2030 value where its reference has it (KNOWN_ISSUES K161, the project lead's decision of 16
        # November 2026): the region's UVAG of the fed fodder, the dual of CAPRI's SUPBAL_ per t fed, in 2017 money
        # (tools/build/build_fodder_value_2030.py, the baseline layer's feed folder); it replaces the 2017 value scaled
        # above (the highest 2017 ration price of the region's animals x the member state's 2030/2017 UVAG ratio)
        # read from the same baseline layer as the price ratios (traj_dir = <baseline>/<BAS><SIM>/trajectories)
        _fvp = Path(traj_dir).parent / "feed" / "fodder_value_2030.csv"
        fv = read_input(_fvp) if _fvp.exists() else None
        if fv is not None:
            v30 = {(t.region, t.fodder): float(t.value_eur_t) for t in fv.itertuples(index=False)}
            n_30 = 0
            for reg, feeds in fb.items():
                for feed, rec in (feeds or {}).items():
                    v = v30.get((reg, feed))
                    if v is not None and v > 0:
                        rec["value_eur_t"] = v
                        n_30 += 1
            summary["fodder_values_capri_2030"] = n_30
        # CAPRI's milk for feeding (COMF, SGMF): non-tradable outputs of the cows and the milk sheep and goats, fed to
        # the calves and the sheep and goats as FCOM and FSGM, in SUPBAL_ with CAPRI's losses (use <= output; supply/
        # supply_model.gms l. 4551-4611, FEDUSE_ l. 789-803, supply/prep_sim.gms l. 222-223), valued at the balance's
        # dual, CAPRI's 2030 UVAG in 2017 money (tools/build/build_milk_for_feeding_2030.py; KNOWN_ISSUES K189). The
        # users are the animals whose ration feeds the milk (livestock.py _fodder_rows)
        _mfp = Path(traj_dir).parent / "feed" / "milk_for_feeding_2030.csv"
        mf = read_input(_mfp) if _mfp.exists() else None
        if mf is not None:
            n_m = 0
            for (reg, feed), g in mf.groupby(["region", "feed"]):
                if reg not in fb:
                    continue
                fb[reg] = fb[reg] if fb[reg] is not None else {}
                fb[reg][feed] = {"crops": {}, "producers": dict(zip(g.animal, g.output_t_head.astype(float))),
                                 "use_t_head": {}, "value_eur_t": float(g.value_eur_t.iloc[0]), "losses": True}
                n_m += 1
            summary["milk_for_feeding_balances"] = n_m
        # the rations price each fodder at its balance's base value (CAPRI: the fodder's price in the feeding problem
        # is the dual of its SUPBAL_, one per region): the projected value, EUR per kg as the ration data
        # (feed/ration.py, ration_model_for). Until 16 November 2026 the rations kept the 2017 value (ES41 grass 20.15
        # EUR/t), and the balance's dual at the 2030 base followed it (20.8 against CAPRI's UVAG 11.28)
        data["ration_fodder_price"] = {(reg, feed): float(rec["value_eur_t"]) / 1000.0
                                       for reg, feeds in fb.items() for feed, rec in (feeds or {}).items()
                                       if float(rec.get("value_eur_t", 0.0) or 0.0) > 0}
        summary["ration_fodder_prices"] = len(data["ration_fodder_price"])

    # --- livestock: final products by market
    bym = data.get("livestock_product_value_by_market_coef")
    tot = data.get("livestock_product_value_coef")
    toou = data.get("livestock_output_value_coef")
    toin = data.get("livestock_cost_coef")
    d_out = {}
    if isinstance(bym, pd.DataFrame):
        for col in bym.columns:
            act, mkt = col.split(".", 1)
            prod = MARKET_PRODUCT.get(mkt)
            if mkt == "MILK" and act in ("SHGM", "SHGF"):
                prod = "SGMI"                 # sheep and goat milk: its own CAPRI price (SGMI), not cow milk's
            if prod is None:
                continue
            f = pd.Series([r(reg, prod) or 1.0 for reg in bym.index], index=bym.index)
            old = bym[col].fillna(0.0)
            bym[col] = bym[col] * f
            delta = bym[col].fillna(0.0) - old
            d_out[act] = d_out.get(act, 0.0) + delta
        # (sheep and goat milk is the market column SHGM.MILK, valued at SGMI above; a second term here, written
        # before that column existed, added the same milk value change again: K26)
        if isinstance(tot, pd.DataFrame):
            for act, dlt in d_out.items():
                if act in tot.columns:
                    tot[act] = tot[act] + dlt.reindex(tot.index).fillna(0.0)
    summary["product_value_change_median"] = {a: float(v.median()) for a, v in d_out.items()}

    # --- young animals: value factors, and their change in total output / inputs per head
    yfac, d_yo, d_yi = {}, {}, {}
    for reg, rec in (young_table or {}).items():
        for good, g in rec.items():
            prods = YOUNG_PRODUCTS.get(good)
            if not prods:
                continue
            vals = [r(reg, p) for p in prods if r(reg, p)]
            if not vals:
                continue
            f = sum(vals) / len(vals)
            yfac.setdefault(reg, {})[good] = f
            v0 = float(g.get("value_eur_head", 0.0))
            # the year's young animals at the year's value less the base year's at the base value (the base year's
            # TOOU / TOIN hold those): c x v0 x f - c0 x v0, c0 = c without the base year's table
            g0 = ((young_table_base or {}).get(reg) or {}).get(good) if young_table_base is not None else g
            g0 = g0 or {"produce": {}, "use": {}}
            for side, dd in (("produce", d_yo), ("use", d_yi)):
                c1, c0 = g.get(side, {}), g0.get(side, {})
                for act in set(c1) | set(c0):
                    dd[(reg, act)] = dd.get((reg, act), 0.0) + (float(c1.get(act, 0.0)) * f - float(c0.get(act, 0.0))) * v0
    data["young_animal_value_factor"] = yfac

    # --- purchased feed cereals in total inputs (EU 2017 prices, member-state price ratios)
    fc = data.get("livestock_feed_coef")
    d_feed = {}
    if isinstance(fc, pd.DataFrame) and p0 is not None:
        wsum = sum(feed_cereal_mix.values())
        for col in fc.columns:
            if not col.endswith("_cereals"):
                continue
            act = col[: -len("_cereals")]
            for reg in fc.index:
                q = fc.at[reg, col]
                if pd.isna(q) or q <= 0:
                    continue
                dc = sum(float(q) * (w / wsum) * float(p0.get(feed, 0.0)) * ((r(reg, FEED_CEREAL_PRODUCT[feed]) or 1.0) - 1.0)
                         for feed, w in feed_cereal_mix.items())
                d_feed[(reg, act)] = dc
        # protein-rich feed: the oilcake price index of the supply module (EU feed use weights,
        # 2017 prices), at the member state's 2030 oilcake prices
        w_, p_ = cake_index or ({}, {})
        ws = sum(w_.values())
        if ws > 0:
            for col in fc.columns:
                if not col.endswith("_protein"):
                    continue
                act = col[: -len("_protein")]
                for reg in fc.index:
                    q = fc.at[reg, col]
                    if pd.isna(q) or q <= 0:
                        continue
                    dc = sum(float(q) * (w_[c] / ws) * p_[c] * ((r(reg, c) or 1.0) - 1.0) for c in w_)
                    d_feed[(reg, act)] = d_feed.get((reg, act), 0.0) + dc

    def _add(frame, per_act=None, per_cell=()):
        if not isinstance(frame, pd.DataFrame):
            return
        for act, dlt in (per_act or {}).items():
            if act in frame.columns:
                frame[act] = frame[act] + dlt.reindex(frame.index).fillna(0.0)
        for dct in per_cell:
            for (reg, act), v in dct.items():
                if reg in frame.index and act in frame.columns and pd.notna(frame.at[reg, act]):
                    frame.at[reg, act] = float(frame.at[reg, act]) + v

    _add(toou, d_out, (d_yo,))          # total output: final products and young animals sold
    _add(toin, None, (d_yi, d_feed))    # total inputs: young animals and feed cereals bought
    # the same changes in TOIN's parts of the input cost table (CAPRI's objective form, register DEP-13 step 3): the
    # young animals bought and the feeds, which the regional NLP takes out of the herd's linear term
    ic = data.get("livestock_input_cost")
    if isinstance(ic, dict):
        for item, dd in (("YOUNG", d_yi), ("FEED", d_feed)):
            for (reg, act), v in dd.items():
                f = ic.get(reg)
                if f is not None and act in f.index and item in f.columns and pd.notna(f.at[act, item]):
                    f.at[act, item] = float(f.at[act, item]) + v

    # --- purchased feed bulks in the rations (the projection layer at CAPRI's reference): the rations hold the bulks'
    # 2017 prices (the member state's UVAG, feed_ration_2017.csv); the 2030 baseline takes CAPRI's 2030 UVAG of each
    # bulk over the deflator (ration_bulk_price_index; register DEP-14)
    data["ration_bulk_price"] = ration_bulk_price_index(ratio)
    summary["ration_bulk_price"] = {k: round(v, 3) for k, v in sorted(data["ration_bulk_price"].items())
                                    if k[0] in ("DE000000", "FR000000")}

    # --- premiums
    cp = data.get("cap_premium")
    if isinstance(cp, pd.DataFrame):
        new = cap30.reindex(index=cp.index, columns=cp.columns)
        crops = [c for c in cp.columns if c in CROP_PRODUCT or c in ("GRAS", "GRAE", "GRAI", "MAIF", "OFAR",
                                                                      "ROOF", "FODD", "SETF", "VSET", "FALL", "FRUN",
                                                                      "ARAC", "ANNC")]
        for c in crops:
            cp[c] = new[c].combine_first(cp[c])
        summary["crop_premium_cells"] = int(new[crops].notna().sum().sum())
    # --- the animals' premiums per head: the 2017 coefficient x CAPRI's 2030/2017 ratio; where the 2017 coefficient is
    # empty or zero (CAPRI's 2017 data pay the animals none: Croatia's and Sweden's, Greece's SHGF) CAPRI's 2030 premium
    # per model head itself (KNOWN_ISSUES K210)
    lp = data.get("livestock_premium_coef")
    if isinstance(lp, pd.DataFrame):
        f = lsk.reindex(index=lp.index, columns=lp.columns).fillna(1.0)
        new = lp * f
        a30 = lsk30.reindex(index=lp.index, columns=lp.columns)
        fill = (lp.isna() | (lp == 0)) & a30.notna()
        data["livestock_premium_coef"] = new.mask(fill, a30)
        summary["livestock_premium_2030_cells"] = int(fill.sum().sum())
    summary["young_regions"] = len(yfac)
    return summary


#: CAPRI's purchased feed bulks, in its supply models' objective at the member state's unit value (sets.gms OM_OBJE
#: l. 5135-5136)
FEED_BULKS = ("FCER", "FPRO", "FENE", "FMIL", "FOTH")


def ration_bulk_price_index(ratio: Dict) -> Dict:
    r"""{(member state, bulk): the purchased feed bulk's 2030 price over its 2017 price, in the model's money}.

    CAPRI's supply model prices the bulks at the member state's unit value (supply/supply_model.gms l. 4641-4643, LINEAR_):

          SUM(  RUNR_OMOBJE(RUNR,OM_OBJE),
                v_netPutQuant(RUNR,OM_OBJE) * ( SUM(R_RAGG(RUNR,MSACT), (%data%(MSACT,"UVAG",OM_OBJE,"Y") ...

    and its 2030 baseline holds that unit value at the trend's, the base year's where the trend has none
    (capmod/load_base_data_and_trends.gms l. 693):

          DATA(RS,"UVAG",FEED,"TRD")   $ (NOT DATA(RS,"UVAG",FEED,"TRD")) = DATA(RS,"UVAG",FEED,"Y");

    The index is CAPRI's 2030 UVAG of the bulk (its 2030 reference) over its 2017 UVAG (CAPREG's, the rations' 2017
    price) over CAPRI's inflation: the price-ratio table's rows of the bulks (tools/build/build_price_trajectory_2030.py).
    In every EU member state CAPRI's 2030 UVAG is its 2017 one (no bulk price in the trend), so the index is
    1 / 1.2772 = 0.783; Norway's trend has the bulks' prices. A bulk without a row keeps its 2017 price (the rations'
    default factor 1). The scenarios move it from there: coupling/feed.py, CAPRI's arm/set_prices.gms. In our view
    CAPRI's 2030 bulk prices are an artefact of its trend step (the bulks' ingredients' prices rise, theirs do not),
    followed as CAPRI's form (docs/DEPARTURES_FROM_CAPRI.md, KNOWN_ISSUES K197)."""
    out = {}
    for (ms2, prod), x in ratio.items():
        if prod in FEED_BULKS and x:
            out[("TUR" if ms2 == "TU" else f"{ms2}000000", prod)] = float(x)
    return out
