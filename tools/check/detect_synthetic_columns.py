"""
Audit tool — flag data columns that were generated rather than extracted.

Synthetic fallbacks in this project were produced as `constant * lognormal(sigma)`
with sigma around 0.10. That leaves a signature no real agricultural series has:
a coefficient of variation pinned near sigma across every region. Real regional
yields, costs and herd sizes scatter far wider (CV 0.2-0.5) because agronomy and
farm structure differ across Europe.

This is how `yields.csv` was caught claiming REAL_CAPRI in the sourcing registry
while 16 of its 40 columns were generated. Run it against the whole data tree
after any extraction or merge; the result is cross-checked against each file's
provenance (capri_data/schema/01_provenance.sql).

Usage
-----
    python tools/check/detect_synthetic_columns.py [data_dir]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
# CV window that catches constant * lognormal(0.10). Widened slightly on each
# side so a sigma of 0.08 or 0.12 does not slip through.
CV_LOW, CV_HIGH = 0.07, 0.13
MIN_ROWS = 30


def audit(data_dir: Path) -> pd.DataFrame:
    rows = []
    for path in sorted(data_dir.rglob("*.csv")):
        try:
            df = _read_csv(path, index_col=0)
        except Exception:
            continue
        num = df.select_dtypes("number")
        if num.shape[0] < MIN_ROWS or num.shape[1] < 2:
            continue
        for col in num.columns:
            v = num[col].replace(0, np.nan).dropna()
            if len(v) < MIN_ROWS or v.mean() <= 0:
                continue
            cv = v.std() / v.mean()
            # Two distinct synthetic signatures:
            #   constant * lognormal(0.10)  -> CV pinned near 0.10
            #   flat placeholder constant   -> CV exactly 0
            # The second was missed by the original CV window and is what let
            # COTT/OFIB/OFOD/SETA through in base_areas.csv.
            kind = None
            if float(v.std()) < 1e-9:
                kind = "CONSTANT_PLACEHOLDER"
            elif CV_LOW < cv < CV_HIGH:
                kind = "LOGNORMAL_FALLBACK"
            if kind:
                rows.append({
                    "file": str(path.relative_to(data_dir)),
                    "column": col,
                    "kind": kind,
                    "cv": round(float(cv), 4),
                    "mean": round(float(v.mean()), 5),
                    "n": len(v),
                })
    return pd.DataFrame(rows)


def main() -> None:
    data_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "capri_data")
    flagged = audit(data_dir)

    if flagged.empty:
        print("No synthetic fingerprints found.")
        return

    n_const = int((flagged["kind"] == "CONSTANT_PLACEHOLDER").sum())
    n_logn = len(flagged) - n_const
    print(f"{len(flagged)} synthetic column(s): {n_const} constant placeholder(s), "
          f"{n_logn} lognormal fallback(s) (CV in [{CV_LOW}, {CV_HIGH}]):\n")
    print(flagged.to_string(index=False))

    # Cross-check against the provenance (capri_data/schema/01_provenance.sql): a flagged column inside a file whose
    # origin is CAPRI or its publication is the failure mode that matters (no file may hold generated values).
    prov_path = data_dir / "schema" / "01_provenance.sql"
    if not prov_path.exists():
        return
    import duckdb
    con = duckdb.connect()
    con.execute(prov_path.read_text(encoding="utf-8"))
    nature = dict(con.execute("SELECT file, nature FROM provenance").fetchall())
    conflicts = []
    for _, r in flagged.iterrows():
        rel = "capri_data/" + str(r["file"])          # audit() gives the path relative to data_dir
        n = nature.get(rel, "")
        if n in ("capri", "capri-publication", "mixed"):
            conflicts.append(f'{r["file"]}:{r["column"]} in a file of origin {n}')
    print()
    if conflicts:
        print(f"{len(conflicts)} flagged columns in files built from CAPRI's data (a column constant across regions, or of "
              "narrow spread, can be CAPRI's own value: each is a column to look at, not a finding):")
        for c in conflicts:
            print(f"  {c}")
    else:
        print("No provenance conflicts.")


if __name__ == "__main__":
    main()
