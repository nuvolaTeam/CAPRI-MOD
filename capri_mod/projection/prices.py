"""CAPRI's 2030 prices and premiums in the projected baseline, in 2017 money.

CAPRI's 2030 reference (the one JRC121368's Farm-to-Fork scenarios start from) is in current
prices: every non-agricultural input moves by one index (2030/2017 = 1.277, every member
state), agricultural outputs by their own projected prices, and CAP payments are nominal. The
model works in 2017 money, so its 2030 baseline takes each product's CAPRI price ratio over
that index (tools/build/build_price_trajectory_2030.py -> capri_data/trajectories/):

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
from typing import Dict

import pandas as pd
from capri_mod.data.definitions import MS_CODE
from capri_mod.tableio import read_input

#: crop products whose CAPRI price is applied (model price-table code -> CAPRI product)
CROP_PRODUCT = {c: c for c in (
    "SWHE", "DWHE", "RYEM", "BARL", "OATS", "OCER", "PARI", "RAPE", "SUNF", "SOYA", "OOIL", "PULS",
    "POTA", "SUGB", "TOMA", "OVEG", "APPL", "OFRU", "CITR", "TAGR", "TWIN", "OLIV", "TABO", "TOBA", "TEXT",
    "NURS", "FLOW", "OCRO", "OIND")}
CROP_PRODUCT.update({"CORN": "MAIZ", "MAIZ": "MAIZ", "WINE": "TWIN"})
#: fodder crops of the fodder balance -> CAPRI product (unit value = fodder shadow price)
FODDER_PRODUCT = {"GRAS": "GRAS", "MAIF": "MAIF", "OFOD": "OFAR", "ROOF": "ROOF"}
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
    eu = pr[pr["ms"] != "NO"].groupby("product")["real_ratio"].median().to_dict()
    cap = read_input(traj_dir / "capri_cap_premium_2030.csv", index_col=0)
    lsk = read_input(traj_dir / "capri_livestock_premium_ratio_2030.csv", index_col=0)
    return ratio, eu, cap, lsk


def apply_capri_prices_2030(data: Dict, traj_dir: Path, young_table: Dict, feed_cereal_mix: Dict,
                            cake_index=None) -> Dict:
    """Put CAPRI's 2030 prices (2017 money) into a projected data dict, in place. Returns a summary."""
    ratio, eu, cap30, lsk = load_price_tables(traj_dir)
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
                prod = FODDER_PRODUCT.get(rec.get("crop"))
                f = r(reg, prod) if prod else None
                if f and "value_eur_t" in rec:
                    rec["value_eur_t"] = float(rec["value_eur_t"]) * f
                    n_f += 1; fr.append(f)
        summary["fodder_values"] = n_f
        if fr:
            summary["fodder_value_ratio_median"] = float(pd.Series(fr).median())

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
            for act, c in g.get("produce", {}).items():
                d_yo[(reg, act)] = d_yo.get((reg, act), 0.0) + c * v0 * (f - 1.0)
            for act, c in g.get("use", {}).items():
                d_yi[(reg, act)] = d_yi.get((reg, act), 0.0) + c * v0 * (f - 1.0)
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

    # --- purchased feed bulks in the rations (Sprint 9p): CAPRI's 2030 bulk prices are its feedBlkPrice_ CES indices of
    # the member state's feed products at their 2030 prices; the rations were priced at 2017 bulk prices, so the 2030
    # baseline's ration choice used 2017 relative prices of purchased feed against fodder (whose 2030 values are
    # CAPRI's). Index per (member state, bulk): sum_i s_i r_i^(1-rho) ^ (1/(1-rho)), s_i the value shares of
    # tools/build/build_feed_bulks.py, r_i CAPRI's 2030/2017 real price ratio; products without a CAPRI unit value
    # (by-products, dairy products, fish meal, oils, sugar) at 1 (REGISTERED).
    data["ration_bulk_price"] = ration_bulk_price_index(r)
    summary["ration_bulk_price"] = {k: round(v, 3) for k, v in sorted(data["ration_bulk_price"].items())
                                    if k[0] in ("DE000000", "FR000000")}

    # --- premiums
    cp = data.get("cap_premium")
    if isinstance(cp, pd.DataFrame):
        new = cap30.reindex(index=cp.index, columns=cp.columns)
        crops = [c for c in cp.columns if c in CROP_PRODUCT or c in ("GRAS", "MAIF", "OFAR", "ROOF", "FODD",
                                                                      "SETF", "VSET", "FRUN", "ARAC", "ANNC")]
        for c in crops:
            cp[c] = new[c].combine_first(cp[c])
        summary["crop_premium_cells"] = int(new[crops].notna().sum().sum())
    lp = data.get("livestock_premium_coef")
    if isinstance(lp, pd.DataFrame):
        f = lsk.reindex(index=lp.index, columns=lp.columns).fillna(1.0)
        data["livestock_premium_coef"] = lp * f
    summary["young_regions"] = len(yfac)
    return summary


#: CAPRI feed products -> price-ratio products (the ratio table's codes)
_BULK_PRODUCT = {"WHEA": "SWHE", "RICE": "PARI"}


def ration_bulk_price_index(ratio_fn) -> Dict:
    """{(member state, bulk): CAPRI's 2030/2017 real price index of the feed bulk} (feedBlkPrice_ CES, rho of the
    bulk) from capri_data/2017/market/feed_bulks_eu.csv and CAPRI's product price ratios."""
    import numpy as np
    f = Path(__file__).resolve().parents[2] / "capri_data" / "2017" / "market" / "feed_bulks_eu.csv"
    if not f.exists():
        return {}
    t = read_input(f, keep_default_na=False)
    out = {}
    for (ms, b), g in t.groupby(["ms", "bulk"], sort=True):
        v = g["feed_kt"].astype(float).values * g["arm1p"].astype(float).values
        if not (v.sum() > 0):
            continue
        s_ = v / v.sum()
        rho = float(g["rho"].iloc[0])
        reg = ms[:2]
        rr = []
        for prod in g["product"].astype(str):
            x = ratio_fn(reg, _BULK_PRODUCT.get(prod, prod))
            rr.append(float(x) if x else 1.0)
        rr = np.maximum(np.array(rr), 1e-6)
        out[(ms, b)] = float((s_ * rr ** (1.0 - rho)).sum()) ** (1.0 / (1.0 - rho))
    return out
