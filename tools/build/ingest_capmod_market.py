"""
Count the bilateral trade flows of the capmod base-year result (validation/capmod_market_extraction.json, not kept in
git). Until 30 October 2026 it wrote them to sources/capmod/capmod_trade_flows_2017.csv.xz; nothing read that file
(the model's bilateral trade comes from tools/build/build_bilateral_market.py) and it was removed, the project lead's
decision (KNOWN_ISSUES K103).

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
There is no single world price in dataOut: `Fob` is dimensioned by importer. Until 29 October 2026 this tool built
an import-quantity-weighted reference price from it (capmod_world_prices_2017.csv); nothing read that file (the
model's world prices are CAPRI's FAO_agg PMRK) and it was removed (KNOWN_ISSUES K103).

Usage
-----
    python tools/build/ingest_capmod_market.py --dump /path/to/_symbols_base1717.txt
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
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

    # ---- bilateral trade, excluding the World aggregate: counted for the summary only (written to
    # sources/capmod/capmod_trade_flows_2017.csv.xz until 30 October 2026; nothing read it - the model's trade comes
    # from tools/build/build_bilateral_market.py - and the file was removed, the project lead's decision: K103)
    bil = df[(df.item == "ImportQ") & (df.exporter != WORLD)]
    print(f"\nbilateral trade : {len(bil):,} flows, "
          f"{bil.importer.nunique()} importers x {bil.exporter.nunique()} exporters")

    # (an import-weighted world reference price from Fob was written to capmod_world_prices_2017.csv until 29 October
    # 2026; nothing read it - the model's world prices are CAPRI's FAO_agg PMRK, tools/build/build_world_prices.py -
    # and it was removed: KNOWN_ISSUES K103)

    (args.data_dir / "validation" / "capmod_market_extraction.json").write_text(
        json.dumps({
            "source": "res_0_1717cap_after_2014_cal_from_data_caldefaulta.gdx",
            "year": YEAR,
            "trade_flows": int(len(bil)),
        }, indent=1))
    print(f"\nwritten to {args.data_dir / 'validation' / 'capmod_market_extraction.json'}")


if __name__ == "__main__":
    main()
