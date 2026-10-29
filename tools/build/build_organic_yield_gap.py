"""CAPRI's organic-to-conventional yield gaps per PESETA macro-region and product group (KNOWN_ISSUES K101).

    capri_data/2017/policy/organic_yield_gap.csv   peseta_region, cereals, fruits, grass, maize, milk, nonfruit_perm,
                                                    oilseeds, vegetables, wheat   (percent difference)

From CAPRI's dat/pesticides/yield_effects_ppp.xlsx, sheet yld_gap ("yield gaps organic to conventional: FADN estimates
by JRC used in SUPREMA project"): the macro-region codes in column C, the product groups in the header row, empty
cells where the workbook has none. Until 29 October 2026 the file had no builder and held the values rounded to 3
decimals; the values are now the workbook's.

    python tools/build/build_organic_yield_gap.py [--xlsx FILE]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
XLSX = Path("/mnt/user-data/uploads/yield_effects_ppp.xlsx")
OUT = ROOT / "capri_data" / "2017" / "policy" / "organic_yield_gap.csv"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xlsx", type=Path, default=XLSX)
    a = ap.parse_args()
    import openpyxl
    ws = openpyxl.load_workbook(a.xlsx, data_only=True, read_only=True)["yld_gap"]
    rows = [r for r in ws.iter_rows(values_only=True)]
    hi = next(i for i, r in enumerate(rows) if r and "cereals" in r)
    head = rows[hi]
    c0 = head.index("cereals")
    groups = [h for h in head[c0:] if h]
    data = {}
    for r in rows[hi + 1:]:
        code = r[c0 - 1] if len(r) >= c0 else None
        if not code:
            continue
        data[str(code)] = [float(v) if v is not None else float("nan") for v in r[c0:c0 + len(groups)]]
    df = pd.DataFrame.from_dict(data, orient="index", columns=groups)
    df.index.name = "peseta_region"
    df.to_csv(OUT)
    print(f"{OUT.name}: {len(df)} macro-regions x {len(groups)} product groups from {a.xlsx.name}")


if __name__ == "__main__":
    main()
