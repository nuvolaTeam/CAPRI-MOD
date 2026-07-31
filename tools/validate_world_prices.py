"""
Validate world prices against verified EU producer prices.

The problem
-----------
Nothing inside the model can validate world_prices.csv: the market-module test
compares solved prices against reference values that are the file itself. The
divergence report shows the model and CAPRI's capmod result disagreeing on eight
commodities in inconsistent directions, with neither demonstrably right.

The independent check
---------------------
EU producer prices are now a verified GDX read (DATA2 MPRI, 192 regions), and
they are independent of world_prices.csv -- nothing in the supply chain that
produced them touches it. Arbitrage constrains the two:

  * for a commodity the EU imports heavily, the domestic price cannot sit far
    below the landed cost of imports, so
        producer / world  >~ 1, and roughly (world + transport + tariff) / world

  * for a commodity the EU is self-sufficient in or exports, the domestic price
    is free to sit above the world price by the extent of protection, but a
    domestic price far BELOW the world price makes no sense: producers would
    export instead

So a producer/world ratio well under 1 is the diagnostic. It says the world
price is implausibly high relative to what EU farmers actually receive.

capmod supplies the extra-EU import share per commodity, so each case can be
judged against the right expectation rather than a single blanket rule.

This does not prove which source is right. It identifies which of the two
implies a producer/world relationship that cannot hold.

Usage
-----
    python tools/validate_world_prices.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

CODE_MAP = {"SWHE": "WHEA", "CORN": "MAIZ", "POUL": "POUM",
            "BUTR": "BUTT", "SKIM": "SMIP"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=Path("capri_data"))
    args = ap.parse_args()
    dd = args.data_dir

    model_wp = pd.read_csv(dd / "2017/market/world_prices.csv", index_col=0)
    wcol = model_wp.columns[0]
    capri = pd.read_csv(dd / "sources/capmod/capmod_world_reference_2017.csv",
                        index_col=0)
    prod = pd.read_csv(dd / "sources/capreg/capreg_producer_prices.csv", index_col=0)
    areas = pd.read_csv(dd / "2017/supply/base_areas.csv", index_col=0)

    # EU producer price: median across regions where the activity is grown.
    eu_price = {}
    for c in prod.columns:
        if c in areas.columns:
            regs = [r for r in prod.index
                    if r in areas.index and areas.at[r, c] > 0
                    and pd.notna(prod.at[r, c]) and prod.at[r, c] > 0]
        else:
            regs = [r for r in prod.index
                    if pd.notna(prod.at[r, c]) and prod.at[r, c] > 0]
        if len(regs) >= 10:
            eu_price[c] = float(prod.loc[regs, c].median())

    # extra-EU import share, for the expectation
    share = {}
    tf = dd / "shared" / "trade_flows_2017.csv"
    if tf.exists():
        flows = pd.read_csv(tf, index_col=[0, 1])
        for c in flows.columns:
            rows = [(e, i) for (e, i) in flows.index if i == "EU27"]
            tot = float(flows.loc[rows, c].sum()) if rows else 0.0
            if tot > 0:
                intra = (float(flows.at[("EU27", "EU27"), c])
                         if ("EU27", "EU27") in flows.index else 0.0)
                share[c] = 100 * (tot - intra) / tot

    rows = []
    for c in model_wp.index:
        if c not in eu_price:
            continue
        k = CODE_MAP.get(c, c)
        cw = capri.at[k, "Fob"] if (k in capri.index and "Fob" in capri.columns) else np.nan
        mw = float(model_wp.at[c, wcol])
        if not (mw > 0):
            continue
        rows.append({
            "commodity": c,
            "eu_producer": round(eu_price[c], 1),
            "model_world": round(mw, 1),
            "capri_world": round(float(cw), 1) if pd.notna(cw) else None,
            "ratio_model": round(eu_price[c] / mw, 2),
            "ratio_capri": (round(eu_price[c] / float(cw), 2)
                            if pd.notna(cw) and cw > 0 else None),
            "extra_eu_pct": round(share.get(c, np.nan), 1) if c in share else None,
        })
    df = pd.DataFrame(rows).set_index("commodity")

    print("EU producer price divided by world price.")
    print("A ratio well below 1 means the world price is implausibly high:")
    print("EU farmers would export rather than accept the domestic price.\n")
    print(df.to_string())

    def verdict(r):
        m, c = r.ratio_model, r.ratio_capri
        if c is None or pd.isna(c):
            return ""
        # implausible = domestic more than 20% below world
        bad_m, bad_c = m < 0.8, c < 0.8
        if bad_m and not bad_c:
            return "CAPRI more plausible"
        if bad_c and not bad_m:
            return "model more plausible"
        if bad_m and bad_c:
            return "both implausible"
        return ""

    df["verdict"] = df.apply(verdict, axis=1)
    flagged = df[df.verdict != ""]
    if len(flagged):
        print("\n" + "=" * 70)
        print("COMMODITIES WHERE THE RATIO SETTLES IT")
        print("=" * 70)
        print(flagged[["eu_producer", "model_world", "capri_world",
                       "ratio_model", "ratio_capri", "verdict"]].to_string())

    out = dd / "validation" / "world_price_arbitrage_check.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out)
    print(f"\nwritten: {out}")


if __name__ == "__main__":
    main()
