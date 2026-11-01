"""CAPRI's 2030 market balance per EU member state (Data_CAL of data_market_1730defaulta), for the market with the EU
as CAPRI's two trade blocks (docs/archive/MARKET_STRUCTURE_PLAN.md step 3).

CAPRI clears the EU market per trade block, A_EU_WEST and A_EU_EAST (gams/aggregation/defaultA.agg), with the member
states as behavioural regions inside. The market's EU-level data that have no member-state detail of their own (feed
share of use, biofuel share of use, residual feed output and its parents' use, crushing share of seed use, dairy
food and feed use) are split between the blocks with this table: per member state and CAPRI product, production
PROD, human consumption HCON, feed FEED, processing PROC, biofuel processing BIOF at CAPRI's 2030 calibration point.
Data with member-state detail (feed bulks, dairy blocks, biofuel feedstocks, GL demand, supply models) need no split.

Output: capri_data/2017/market/eu_ms_balance_2030.csv  ms, block, product, commodity, prod_kt, hcon_kt, feed_kt,
        proc_kt, biof_kt   (commodity: the model's market commodity, empty where it has none)

    python tools/build/build_eu_ms_balance.py
"""
from __future__ import annotations
import re, sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
DATA = Path("/mnt/user-data/uploads/data_market_1730defaulta.csv")
OUT = ROOT / "capri_data" / "2017" / "market" / "eu_ms_balance_2030.csv"
ITEMS = ("PROD", "HCON", "FEED", "PROC", "BIOF")


def main() -> None:
    sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
    import build_bilateral_market as BM
    g2m = {g: m for m, gs in BM.MODEL.items() for g in gs}
    bm = _read_csv(ROOT / "capri_data" / "shared" / "eu_market_blocks.csv")
    blocks = bm.set_index("ms")["block"].to_dict()                      # CAPRI's member states of the two blocks
    pat = re.compile(r"^'([A-Z]{2}000000)'\.'(" + "|".join(ITEMS) + r")'\.'([A-Za-z]+)'\.'CAL'\s+([-\d.Ee+]+)")
    v = defaultdict(lambda: defaultdict(float))
    for line in open(DATA, encoding="latin-1"):
        m = pat.match(line)
        if m and m.group(1) in blocks:
            v[(m.group(1), m.group(3))][m.group(2)] = float(m.group(4))
    rows = [dict(ms=ms, block=blocks[ms], product=p, commodity=g2m.get(p, ""),
                 **{f"{i.lower()}_kt": d.get(i, 0.0) for i in ITEMS}) for (ms, p), d in sorted(v.items())]
    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False)
    t = df.groupby("block")[["prod_kt", "hcon_kt", "feed_kt", "proc_kt", "biof_kt"]].sum()
    print(f"wrote {OUT.relative_to(ROOT)}: {len(df)} rows, {df.ms.nunique()} member states")
    print(df[df["product"].isin(["WHEA", "MILK", "PORK"])].groupby(["product", "block"])[["prod_kt", "hcon_kt", "feed_kt"]].sum().round(0))


if __name__ == "__main__":
    main()
