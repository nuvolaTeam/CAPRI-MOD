"""
Audit tool — flag data columns that were generated rather than extracted.

Synthetic fallbacks in this project were produced as `constant * lognormal(sigma)`
with sigma around 0.10. That leaves a signature no real agricultural series has:
a coefficient of variation pinned near sigma across every region. Real regional
yields, costs and herd sizes scatter far wider (CV 0.2-0.5) because agronomy and
farm structure differ across Europe.

This is how `yields.csv` was caught claiming REAL_CAPRI in the sourcing registry
while 16 of its 40 columns were generated. Run it against the whole data tree
after any extraction or merge, and cross-check the result against the registry.

Usage
-----
    python tools/detect_synthetic_columns.py [data_dir]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# CV window that catches constant * lognormal(0.10). Widened slightly on each
# side so a sigma of 0.08 or 0.12 does not slip through.
CV_LOW, CV_HIGH = 0.07, 0.13
MIN_ROWS = 30


def audit(data_dir: Path) -> pd.DataFrame:
    rows = []
    for path in sorted(data_dir.rglob("*.csv")):
        try:
            df = pd.read_csv(path, index_col=0)
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

    # Cross-check against the sourcing registry: a flagged column inside a file
    # the registry calls REAL is the failure mode that matters.
    reg_path = data_dir / "DATA_SOURCING_REGISTRY.json"
    if not reg_path.exists():
        return
    datasets = json.loads(reg_path.read_text(encoding="utf-8"))["datasets"]
    conflicts = []
    for _, r in flagged.iterrows():
        entry = datasets.get(Path(r["file"]).name)
        if not entry:
            continue
        nature = entry.get("nature", "")
        if nature.startswith("REAL"):
            conflicts.append(f'{r["file"]}:{r["column"]} labelled {nature}')
        elif nature == "MIXED_BY_COLUMN":
            declared = entry.get("column_nature", {}).get("SYNTHETIC_FALLBACK", [])
            if r["column"] not in declared:
                conflicts.append(
                    f'{r["file"]}:{r["column"]} not declared synthetic')
    print()
    if conflicts:
        print("REGISTRY CONFLICTS — flagged but labelled real:")
        for c in conflicts:
            print(f"  {c}")
    else:
        print("No registry conflicts: every flagged column is declared synthetic.")


if __name__ == "__main__":
    main()
