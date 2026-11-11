"""The inputs of CAPTRD's supports from Eurostat's recent production statistics (captrd/agriprod_supports.gms, included by
captrd/expert_support.gms l. 771), as CSV.

Sources (the project lead's CAPRI installation, docs/EXTERNAL_SOURCES.md):
  gams/captrd/agriprod_supports.gms  its sets (read by tools/lib/gams_sets.py, %BaseYear% 2017 as the reference run)
  gams/feed/feed_decl.gms            the table p_reqfcnlim (l. 284: limits of days and daily growth)
  dat/coco/Agri_Prod.gdx             p_AgriProd (Eurostat's agriprod tables), converted to Parquet by
                                     tools/build/convert_capri_gdx.py (dat_parquet/coco/Agri_Prod); kept: the records of
                                     the file's domains (msAgriprod, agriprod, itemAgriProd: GAMS's execute_load drops the
                                     others) and of the years from 2010 (the file reads %BaseYear% - 1 to 2020)
Output: capri_data/pipeline/captrd/sets/agriprod/<set>.csv (d0, d1), capri_data/pipeline/captrd/dat/agriprod_p_agriprod.csv,
agriprod_p_reqfcnlim.csv.

    python tools/build/build_captrd_agriprod.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
import gams_sets as G                                      # noqa: E402
import gams_text as GT                                     # noqa: E402
from paths import SOURCES                                  # noqa: E402

GAMS = SOURCES / "course_capri_git" / "gams"
PARQ = SOURCES / "dat_parquet" / "coco" / "Agri_Prod" / "p_AgriProd.parquet"
OUT_SETS = ROOT / "capri_data" / "pipeline" / "captrd" / "sets" / "agriprod"
OUT_DAT = ROOT / "capri_data" / "pipeline" / "captrd" / "dat"
SETS = ["shepGoatOri", "agriprodOri", "agriprodCalc", "agriprod", "agriprod1", "agriprod2", "shepGoat", "agriProdAact",
        "agriProdCact", "agriProdMlk", "cols_TO_agriprod", "MSagriprod", "MSagriprod_map", "itemAgriProd", "mlkAgriProd",
        "agriprod_to_item", "facyr", "fac"]
#: the first year kept of p_AgriProd
FIRST_YEAR = 2010


def _write(path: Path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
    print(f"{path.relative_to(ROOT)}: {len(rows)} records")


def main() -> None:
    import pandas as pd
    gs = G.read(GAMS / "captrd" / "agriprod_supports.gms", GAMS, {"BaseYear": "2017", "BAS": "17"})
    for n in SETS:
        m = gs.get(n)
        _write(OUT_SETS / f"{n.lower()}.csv", [f"d{i}" for i in range(len(m[0]))], m)
    t = GT.read_text(GAMS / "feed" / "feed_decl.gms")
    _write(OUT_DAT / "agriprod_p_reqfcnlim.csv", ["act", "row", "bound", "value"],
           [(a, r, b, repr(float(v))) for a, r, b, v in GT.table_records(t, "p_reqfcnlim", 2, "feed_decl.gms")])
    d = pd.read_parquet(PARQ)
    if d["special"].fillna("").ne("").any():
        raise ValueError(f"{PARQ}: special values")
    dom = [{x[0].upper() for x in gs.get(n)} for n in ("MSagriprod", "agriprod", "itemAgriProd")]
    keep = (d.d1.str.upper().isin(dom[0]) & d.d2.str.upper().isin(dom[1]) & d.d3.str.upper().isin(dom[2])
            & (pd.to_numeric(d.d4, errors="coerce") >= FIRST_YEAR))
    d = d[keep]
    _write(OUT_DAT / "agriprod_p_agriprod.csv", ["ms_agriprod", "agriprod", "item", "year", "value"],
           [(a.upper(), b.upper(), c.upper(), int(y), repr(float(v))) for a, b, c, y, v in
            zip(d.d1, d.d2, d.d3, d.d4, d.value)])


if __name__ == "__main__":
    main()
