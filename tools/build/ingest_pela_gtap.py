"""
Ingest CAPRI's PELA elasticities (the GTAP Armington parameters until 30 October 2026, see below).

PELA
----
`dat/estnlp/results.gdx`, symbol PELA, dimensioned region x crop x crop x year.
The third index is the crop whose price the response is measured against, so the
diagonal is own-price and the rest are genuine cross-price elasticities.

Two findings on inspection:

1. The model's existing supply_elasticities_regional.csv reproduces the 2005
   own-price slice EXACTLY -- 0.0% median deviation across 107 regions and 13
   crops. So that file was correctly derived; it was simply truncated. PELA
   covers 228 regions, more than double.

2. 480,473 of the 522,985 records are cross-price and entirely unused. The
   supply module currently derives its Q off-diagonals from a heuristic or from
   the group-level p_pmpQuadPact; these are the activity-level estimates.

Vintage: PELA runs 1986-2005 and stops twelve years before the base year. The
2005 slice is used because it is the most recent available and because it is
what the existing file already used. This is a real limitation, not a choice
worth hiding: supply elasticities are structural enough that a twelve-year gap
is defensible, but it should be stated.

GTAP
----
Until 30 October 2026 it also wrote the GTAP Armington elasticities (esubd, esubm of dat/arm/GTP57_134.gdx) per model
commodity through a GTAP-sector concordance to sources/estnlp/gtap_armington.csv. Nothing read that file (the
model's Armington terms come from tools/build/build_bilateral_market.py, armington_rho.csv) and it was removed with
that part of this tool, the project lead's decision (KNOWN_ISSUES K103).

Usage
-----
    python tools/build/ingest_pela_gtap.py --dump-dir /path/to/dumps
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
PELA_REC = re.compile(
    r"^'([A-Z]{2}[A-Z0-9]{6})'\.'([A-Z0-9]+)'\.'([A-Z0-9]+)'\.'(\d{4})'\s+([-\d.Ee+]+)")

PELA_YEAR = "2005"

def parse_pela(path: Path, year: str) -> pd.DataFrame:
    rows = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = PELA_REC.match(line)
            if m and m.group(4) == year:
                rows.append((m.group(1), m.group(2), m.group(3), float(m.group(5))))
    return pd.DataFrame(rows, columns=["region", "crop", "wrt", "value"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", required=True, type=Path)
    ap.add_argument("--data-dir", type=Path, default=Path("capri_data"))
    args = ap.parse_args()

    out = args.data_dir / "sources" / "estnlp"
    out.mkdir(parents=True, exist_ok=True)

    # the model's regions are CAPRI's regional units (shared/regional_units.csv): each CAPRI code is its own region
    # (until 27 October 2026 mapped through shared/nuts_crosswalk.json, which left 21 regions unmatched)
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
    from _model_regions import UNITS
    rev = {u: u for u in UNITS}

    # ---- PELA ---------------------------------------------------------
    pela = parse_pela(args.dump_dir / "estnlp_PELA.txt", PELA_YEAR)
    pela["model_region"] = pela.region.map(rev)
    pela = pela.dropna(subset=["model_region"])
    pela["crop"] = pela.crop.replace({"MAIZ": "CORN"})
    pela["wrt"] = pela.wrt.replace({"MAIZ": "CORN"})

    own = pela[pela.crop == pela.wrt].pivot_table(
        index="model_region", columns="crop", values="value", aggfunc="mean")
    cross = pela[pela.crop != pela.wrt][
        ["model_region", "crop", "wrt", "value"]]

    own.to_csv(out / "pela_own_price.csv")
    # (the cross-price records were also written to pela_cross_by_region.json for the supply module's legacy cross
    # terms; that path and the file were removed on 29 October 2026: KNOWN_ISSUES K105)
    print(f"PELA {PELA_YEAR}: {len(pela):,} records reaching "
          f"{pela.model_region.nunique()} model regions")
    print(f"  own-price   : {own.shape[0]} regions x {own.shape[1]} crops")
    print(f"  cross-price : {len(cross):,} records "
          f"({100*(cross.value < 0).mean():.0f}% negative, i.e. substitutes)")
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()
