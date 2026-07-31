"""
Ingest world prices and bilateral trade flows from the capmod base-year result.

Source
------
`output/results/capmod/res_0_1717cap_after_2014_cal_from_data_caldefaulta.gdx`,
symbol dataOut. The name decodes as res_<NTSLVL>_<BAS><SIM><scenario>...: BAS=17
and SIM=17, so this is the 2017 base year calibrated from data rather than a
projection. Every other file in that directory is a 2020-2050 projection or a
single-member-state slice.

Structure
---------
    dataOut(importer, exporter, item, commodity, year)

with the items that matter here:

    ImportQ    bilateral import quantity
    ImportP    bilateral import price
    Fob        free-on-board price at the exporter
    TCost      transport cost
    TaAppl     applied tariff

`World` appears in the exporter slot as the aggregate over all origins.

This finally puts trade flows at the base year. The model has been carrying a
2021 matrix inside a 2017 base year, and the alternative found earlier
(dat/global/trade_flows_ori.gdx) was raw FAO data ending in 2005, which would
have been worse. This is CAPRI's own calibrated matrix at exactly the right year.

On world prices
---------------
There is no single world price in dataOut. `Fob` is dimensioned by importer,
because it is the free-on-board price that importer faces on its own import
bundle -- barley is 281.0 for Norway and 132.5 for the UK in the same year, which
reflects different origins, not a contradiction.

A single reference price therefore has to be constructed, and the choice is a
judgement rather than a lookup. The import-quantity-weighted mean across
importers is used here: it answers "what did a tonne of this commodity cost on
the world market in 2017", which is what the model's world_prices.csv means.
The unweighted mean is also reported so the two can be compared.

Usage
-----
    python tools/ingest_capmod_market.py --dump /path/to/_symbols_base1717.txt
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

RECORD = re.compile(
    r"^'([^']+)'\.'([^']+)'\.'(ImportQ|ImportP|Fob|TCost|TaAppl)'"
    r"\.'([A-Z0-9]+)'\.'(\d{4})'\s+([-\d.Ee+]+)")

YEAR = "2017"
WORLD = "World"


def parse(path: Path) -> pd.DataFrame:
    rows = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = RECORD.match(line)
            if m and m.group(5) == YEAR:
                rows.append((m.group(1), m.group(2), m.group(3),
                             m.group(4), float(m.group(6))))
    return pd.DataFrame(
        rows, columns=["importer", "exporter", "item", "commodity", "value"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", required=True, type=Path)
    ap.add_argument("--data-dir", type=Path, default=Path("capri_data"))
    args = ap.parse_args()

    print(f"parsing {args.dump.name}...")
    df = parse(args.dump)
    print(f"  {len(df):,} records for {YEAR}, "
          f"{df.importer.nunique()} importers, {df.commodity.nunique()} commodities")

    out = args.data_dir / "sources" / "capmod"
    out.mkdir(parents=True, exist_ok=True)

    # ---- bilateral trade, excluding the World aggregate -----------------
    bil = df[(df.item == "ImportQ") & (df.exporter != WORLD)]
    bil[["importer", "exporter", "commodity", "value"]].to_csv(
        out / "capmod_trade_flows_2017.csv", index=False)
    print(f"\nbilateral trade : {len(bil):,} flows, "
          f"{bil.importer.nunique()} importers x {bil.exporter.nunique()} exporters")

    # ---- world reference price -----------------------------------------
    fob = df[(df.item == "Fob") & (df.exporter == WORLD)]
    qty = df[(df.item == "ImportQ") & (df.exporter == WORLD)]
    merged = fob.merge(qty, on=["importer", "commodity"],
                       suffixes=("_p", "_q"))
    merged = merged[(merged.value_p > 0) & (merged.value_q > 0)]

    weighted = merged.groupby("commodity").apply(
        lambda g: np.average(g.value_p, weights=g.value_q), include_groups=False)
    unweighted = merged.groupby("commodity").value_p.mean()
    prices = pd.DataFrame({"world_price_eur_t": weighted.round(2),
                           "unweighted_mean": unweighted.round(2),
                           "n_importers": merged.groupby("commodity").size()})
    prices.to_csv(out / "capmod_world_prices_2017.csv")
    print(f"world prices    : {len(prices)} commodities")

    # ---- comparison with the incumbent ----------------------------------
    cur_path = args.data_dir / "2017/market/world_prices.csv"
    if cur_path.exists():
        cur = pd.read_csv(cur_path, index_col=0)
        col = cur.columns[0]
        common = [c for c in prices.index if c in cur.index]
        cmp_ = pd.DataFrame({
            "model": cur.loc[common, col],
            "capmod": prices.loc[common, "world_price_eur_t"]})
        cmp_["dev_pct"] = ((cmp_.model - cmp_.capmod).abs()
                           / cmp_.capmod * 100).round(1)
        print(f"\nagainst the current world_prices.csv, {len(common)} commodities:")
        print(f"  median |deviation| : {cmp_.dev_pct.median():.1f}%")
        print(cmp_.sort_values("dev_pct", ascending=False).head(10).to_string())

    (args.data_dir / "validation" / "capmod_market_extraction.json").write_text(
        json.dumps({
            "source": "res_0_1717cap_after_2014_cal_from_data_caldefaulta.gdx",
            "year": YEAR,
            "trade_flows": int(len(bil)),
            "world_prices": int(len(prices)),
            "note": ("Fob is dimensioned by importer, so a single world price is "
                     "constructed as the import-weighted mean. The unweighted "
                     "mean is retained alongside it for comparison."),
        }, indent=1))
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()
