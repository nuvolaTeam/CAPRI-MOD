"""CAPRI's national producer prices (MPRI) per member state and activity: the regional prices' fallback where a region
has no price of its own (capri_mod/data/loaders.py _national_capri_prices; KNOWN_ISSUES K101).

    capri_data/sources/capreg/capreg_national_prices.csv   capri_country, <activity>...

MPRI of the national row '<MS>000000' of each 2017 dump (res_17<MS>.txt, 'Y' column), every activity with a price, under
CAPRI's code; and under the model's code where it differs (build_capri_base.CROP_MAP, the crop's first CAPRI activity:
CORN = MAIZ, WINE = TWIN, OFOD = OFAR), the code the model's price table uses. Rows: CAPRI's two-letter country codes,
sorted; columns sorted.

Until 29 October 2026 the file had no builder: the same values, without MAIZ and OAR1 and without the CORN column
(so CORN had no national fallback; the 17 regions without a regional maize price grow none), with two columns for
CAPRI's TEXT under the old fibre codes COTT and OFIB, which no table reads.

    python tools/build/build_capreg_national_prices.py [dump dir, default /home/claude/work/capreg]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
import build_capri_base as B  # noqa: E402

OUT = ROOT / "capri_data" / "sources" / "capreg" / "capreg_national_prices.csv"
REC = re.compile(r"^'([A-Z]{2})000000'\.'([A-Z0-9]+)'\.'MPRI'\.'Y'\s+([^,\s]+)")


def main(dump_dir: Path) -> None:
    rows: dict = {}
    for f in sorted(dump_dir.glob("res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = REC.match(line)
            if m:
                rows.setdefault(m.group(1), {})[m.group(2)] = B._num(m.group(3))
    df = pd.DataFrame.from_dict(rows, orient="index")
    for model, acts in B.CROP_MAP.items():
        if model not in df.columns and acts[0] in df.columns:
            df[model] = df[acts[0]]
    df = df.sort_index().reindex(sorted(df.columns), axis=1)
    df.index.name = "capri_country"
    df.to_csv(OUT)
    print(f"{OUT.name}: {df.shape[0]} countries x {df.shape[1]} activities")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/home/claude/work/capreg"))
