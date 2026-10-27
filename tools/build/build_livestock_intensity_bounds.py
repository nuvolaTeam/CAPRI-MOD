"""CAPRI's low- and high-intensity dairy yields per model region (t milk per head), the bounds of the supply module's
livestock intensity margin under a nitrate limit (SupplyModel._apply_intensity_margin, capri_mod/supply/intensity.py).

  DCOW_low = YILD of DCOL / 1000,  DCOW_high = YILD of DCOH / 1000      (CAPRI 2017 results, res_17<MS>.txt)

Each region takes its own CAPRI row (the model's regions are CAPRI's units), else its member state's. The file was
supplied without a builder until 27 October 2026 (docs/design/REGIONAL_UNITS_INVENTORY.md).

Output: capri_data/2017/supply/livestock_intensity_bounds.csv
    python tools/build/build_livestock_intensity_bounds.py [--dump-dir /home/claude/work/capreg]
"""
from __future__ import annotations

import argparse
import importlib.util
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ROW = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'(DCOL|DCOH)'\.'YILD'\.'Y'\s+(-?\d[\d.]*(?:[Ee][+\-]?\d+)?)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", type=Path, default=Path("/home/claude/work/capreg"))
    a = ap.parse_args()
    y = defaultdict(dict)
    for p in sorted(a.dump_dir.glob("res_17*.txt")):
        for line in open(p, errors="ignore"):
            m = ROW.match(line)
            if m:
                y[m.group(1)][m.group(2)] = float(m.group(3))
    sp = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(sp); sp.loader.exec_module(mr)
    rows, nat = [], 0
    for reg in mr.model_regions():
        src = reg if {"DCOL", "DCOH"} <= set(y.get(reg, {})) else mr.national_code(reg)
        d = y.get(src, {})
        if d.get("DCOL", 0.0) > 0 and d.get("DCOH", 0.0) > 0:
            rows.append({"model_region": reg, "DCOW_low": d["DCOL"] / 1000.0, "DCOW_high": d["DCOH"] / 1000.0})
            nat += src != reg
    out = ROOT / "capri_data" / "2017" / "supply" / "livestock_intensity_bounds.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"wrote {out.name}: {len(rows)} regions ({nat} from the member state's row)")


if __name__ == "__main__":
    main()
