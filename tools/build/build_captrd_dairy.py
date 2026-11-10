"""DG AGRI's dairy data for CAPTRD's expert supports (captrd/expert_support.gms l. 365-760), as CSV.

Sources (the project lead's CAPRI installation, docs/EXTERNAL_SOURCES.md, capri_sources/dat_local/baseline):
  dairy_targets_agri.gms   the tables p_cowMilkProd, p_DcowMilkProd, p_milkDeliveries, p_nrCows, p_dairyCowYield
                           (ms_agri x year, 1990-2025: DG AGRI's 2015 market outlook, "data received from Sophie
                           Helaine"), the mapping ms_agri_TO_MS and %lst_daitar% (the last year with entries, set in
                           captrd.gms l. 261: 2020)
  recent_mlk_yld.gdx       p_recentMlkYld(region, year | "y"): recent milk yields and their annual change, converted to
                           Parquet by tools/build/convert_capri_gdx.py (capri_sources/dat_parquet/baseline/recent_mlk_yld)
Output: capri_data/pipeline/captrd/dat/dairy_<table>.csv (ms_agri, year, value), dairy_ms_agri_to_ms.csv
(ms_agri, region), p_recentmlkyld.csv (region, year, value).

    python tools/build/build_captrd_dairy.py
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
import gams_text as GT                                    # noqa: E402
from paths import SOURCES                                 # noqa: E402

OUT = ROOT / "capri_data" / "pipeline" / "captrd" / "dat"
SRC = SOURCES / "dat_local" / "baseline" / "dairy_targets_agri.gms"
MLK = SOURCES / "dat_parquet" / "baseline" / "recent_mlk_yld" / "p_recentMlkYld.parquet"
TABLES = ["p_cowMilkProd", "p_DcowMilkProd", "p_milkDeliveries", "p_nrCows", "p_dairyCowYield"]


def _write(name, header, rows):
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / f"{name}.csv", "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
    print(f"{name}.csv: {len(rows)} records")


def main() -> None:
    text = GT.read_text(SRC)
    for t in TABLES:
        recs = GT.table_records(text, t, 1, str(SRC))
        _write(f"dairy_{t.lower()}", ["ms_agri", "year", "value"], [(k.upper(), y, repr(float(v))) for k, y, v in recs])
    body = text[re.search(r"set\s+ms_agri_TO_MS\s*\(", text, flags=re.I).start():]
    body = body[body.index("/") + 1:]
    body = body[:body.index("/")]
    pairs = re.findall(r"^\s*(\w+)\s*\.\s*(\w+)", body, flags=re.M)
    _write("dairy_ms_agri_to_ms", ["ms_agri", "region"], [(a.upper(), b.upper()) for a, b in pairs])
    import pandas as pd
    d = pd.read_parquet(MLK)
    if d["special"].fillna("").ne("").any():
        raise ValueError(f"{MLK}: special values")
    _write("p_recentmlkyld", ["region", "year", "value"],
           [(r.upper(), y.upper(), repr(float(v))) for r, y, v in zip(d.d1, d.d2, d.value)])


if __name__ == "__main__":
    main()
