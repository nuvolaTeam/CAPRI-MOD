"""CAPRI's Norwegian premiums (policy/norw_pol.gms, star 3.0; P2): the seven tables of payment rates, national rates
(NO000000, EUR per ha, head or t) and regional factors (the NUTS 2 units), each payment group by year.

  p_norwPremPact_E(region, year, scheme, activity)   DPNOR1-DPNOR5: per activity unit (APPTYPE noDirPay)
  p_norwPremOutput_E(region, year, scheme, output)   DPNOR6-DPNOR7: per t of output (APPTYPE noPriceSup)

Every cell as written, 0 included (GAMS stores no record for a cell written 0; capri_mod/policy/norway.py applies
that). Output: capri_data/2017/policy/norway_premiums.csv (kind "pact" / "output", region, year, scheme, code, value).

Usage: python tools/build/build_norway_premiums.py [--gams CAPRI's gams folder]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tools" / "build")]
from capri_mod.external_paths import SOURCES  # noqa: E402
from build_cap14_entitlements import gams_table  # noqa: E402

NORW_POL = Path("policy") / "norw_pol.gms"
OUT = ROOT / "capri_data" / "2017" / "policy" / "norway_premiums.csv"
TABLES = {"p_norwPremPact_E": "pact", "p_norwPremOutput_E": "output"}


def tables(text: str):
    """(kind, {(row, column): value}) of every TABLE statement of the file, in order (the file declares each name
    several times, one table per payment group)."""
    starts = [m.start() for m in re.finditer(r"^\s*table\s+", text, re.I | re.M)]
    for i, s in enumerate(starts):
        seg = text[s:starts[i + 1] if i + 1 < len(starts) else len(text)]
        name = re.match(r"\s*table\s+(\w+)", seg, re.I).group(1)
        if name not in TABLES:
            raise SystemExit(f"{NORW_POL}: unexpected table {name}")
        yield TABLES[name], gams_table(seg, name)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gams", type=Path, default=SOURCES / "gams", help="CAPRI's gams folder (star 3.0)")
    a = ap.parse_args()
    text = (a.gams / NORW_POL).read_text(errors="ignore")
    rows, seen = [], set()
    for kind, tab in tables(text):
        for (row, col), v in tab.items():
            r, y, s = row.split(".")
            k = (kind, r, int(y), s, col)
            if k in seen:
                raise SystemExit(f"{NORW_POL}: {k} written twice")
            seen.add(k)
            rows.append((kind, r, int(y), s, col, v))
    df = pd.DataFrame(rows, columns=["kind", "region", "year", "scheme", "code", "value"])
    df = df.sort_values(["kind", "scheme", "region", "year", "code"]).reset_index(drop=True)
    df.to_csv(OUT, index=False, float_format="%.10g")
    print(f"{OUT.relative_to(ROOT)}: {len(df)} cells, schemes {sorted(df.scheme.unique())}, years "
          f"{df.year.min()}-{df.year.max()}, regions {sorted(df.region.unique())}")


if __name__ == "__main__":
    main()
