"""
Extract real per-activity variable costs (TOIN) from CAPRI's capreg DATA2 cube.

CAPRI stores 'TOIN' = "Total intermediate input" in EUR/ha per region and
activity (confirmed in CAPRI GAMS: `TOIN  Total intermdiate input`, and declared
as 'Euro/ha'). CAPRI itself uses it as the cost term:

    Gross Value Added = TOOU (revenue) - TOIN (cost)

which is exactly what CAPRI-Python's `variable_costs.csv` needs.

Why this matters
----------------
The previous `variable_costs.csv` was a crop-GROUP approximation: every arable
crop in a region shared one number (e.g. DE11: wheat = barley = maize = 443.91).
TOIN is genuinely crop- and region-specific (DE11: wheat 743, barley 730,
potato 4501, sugar beet 1461 EUR/ha).

Usage
-----
1. In GAMS Studio, dump DATA2 for each member state you want:

     execute 'gdxdump <path>\\capreg\\res_17DE.gdx symb=DATA2 output=<path>\\DE_data2.txt';

   (repeat per country: DE, FR, IT, ES, PL, ... — use a distinct output name each
   time, or the file gets overwritten.)

2. Run this script over the dumps:

     python extract_variable_costs.py DE_data2.txt FR_data2.txt ... -o variable_costs.csv

3. Drop the result into capri_data/<year>/supply/variable_costs.csv

Notes
-----
* Region codes in DATA2 are padded (DE110000). NUTS-2 = first 4 characters;
  the national aggregate ends in '000000' and is skipped.
* Missing values are genuine (e.g. grain maize is not grown in much of northern
  Germany) — they are left blank rather than zero-filled, and reported.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

LINE = re.compile(
    r"'([A-Z0-9]+)'\.'([A-Z0-9]+)'\.'TOIN'\.'Y'\s+([-\d.eE+]+)"
)

# CAPRI activity code -> CAPRI-Python activity code, where they differ.
# Codes not listed here are used as-is (most already match).
CAPRI_TO_MODEL = {
    "MAIZ": "CORN",   # grain maize
    "PIGF": "PIGF",   # pig fattening (model also has PIGS = breeding sows)
    "SHGF": "SHGP",   # sheep & goats (fattening) -> model's sheep/goat activity
    "POUF": "BROI",   # poultry fattening -> broilers
    "HENS": "LAYS",   # laying hens
}

# Model activities with no direct CAPRI TOIN column; left blank (documented).
# These either do not exist in the extracted country (e.g. CITR, OLIV, COTT in
# Germany) or are model aggregates without a single CAPRI counterpart.


def nuts2(code: str) -> str | None:
    """CAPRI region code -> NUTS-2 code, or None for national/other aggregates."""
    if code.endswith("000000"):          # national aggregate, e.g. DE000000
        return None
    if len(code) >= 4 and code.endswith("0000"):   # DE110000 -> DE11
        return code[:4]
    return None


def parse_dump(path: Path) -> dict[str, dict[str, float]]:
    """Read one DATA2 dump, return {nuts2_region: {activity: EUR/ha}}."""
    out: dict[str, dict[str, float]] = defaultdict(dict)
    with open(path, encoding="latin-1") as fh:
        for line in fh:
            if "'TOIN'" not in line:
                continue
            m = LINE.match(line)
            if not m:
                continue
            region, activity, value = m.group(1), m.group(2), m.group(3)
            reg = nuts2(region)
            if reg is None:
                continue
            try:
                v = float(value)
            except ValueError:
                continue
            if v > 0:                     # TOIN should be positive; skip eps/zero
                out[reg][activity] = v
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dumps", nargs="+", help="DATA2 dump .txt files (one per country)")
    ap.add_argument("-o", "--out", default="variable_costs.csv")
    ap.add_argument("--activities", default=None,
                    help="optional comma-separated list of activities to keep")
    args = ap.parse_args(argv)

    combined: dict[str, dict[str, float]] = {}
    for d in args.dumps:
        p = Path(d)
        if not p.exists():
            print(f"  ! missing: {p}")
            continue
        got = parse_dump(p)
        combined.update(got)
        print(f"  {p.name}: {len(got)} NUTS-2 regions")

    if not combined:
        print("No TOIN data found. Check the dumps contain symb=DATA2.")
        return 1

    df = pd.DataFrame(combined).T.sort_index()

    # rename CAPRI codes to the model's activity codes
    df = df.rename(columns=CAPRI_TO_MODEL)
    df = df.loc[:, ~df.columns.duplicated()]

    if args.activities:
        keep = [a.strip() for a in args.activities.split(",")]
        df = df[[c for c in keep if c in df.columns]]
    df.index.name = "region"

    df.to_csv(args.out, float_format="%.2f")

    total = df.shape[0] * df.shape[1]
    filled = int(df.notna().sum().sum())
    print(f"\nWrote {args.out}")
    print(f"  {df.shape[0]} regions x {df.shape[1]} activities")
    print(f"  coverage: {filled}/{total} cells ({100*filled/total:.0f}%)")
    print("  (gaps are genuine — an activity absent from a region — not errors)")
    print("\nUnits: EUR/ha (CAPRI 'TOIN' = total intermediate input)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
