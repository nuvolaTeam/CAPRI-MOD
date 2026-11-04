"""Symbols of CAPRI's dat folder (capri_sources/dat, its GDX files as Parquet, one file per symbol), extracted to CSV with
every record (4 November 2026).

  dat/envind/fao_peatland.gdx  P(FAOregions) "Share of peatland in arable land" (FAO), read by envind/lulucf_carbon_decl.gms
      l. 695-697 as p_PEATSH: the organic-soil fallback of the Western Balkans and Turkey (prep_lulucf_carbon.gms l. 255-256)
      -> capri_data/sources/capri_dat/envind/fao_peatland_P.csv  (fao_code, value)

    python tools/build/extract_capri_dat.py [capri_sources/dat]
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from paths import SOURCES  # noqa: E402

OUT = ROOT / "capri_data" / "sources" / "capri_dat"
#: (Parquet file under dat, output under capri_data/sources/capri_dat, the output's columns)
SYMBOLS = (("envind/fao_peatland/P.parquet", "envind/fao_peatland_P.csv", ["fao_code", "value"]),)


def main(src: Path) -> None:
    for rel, out, cols in SYMBOLS:
        df = pd.read_parquet(src / rel)
        dims, val = list(df.columns[:-1]), df.columns[-1]
        if len(dims) != len(cols) - 1 or val != "value":
            raise ValueError(f"{rel}: columns {list(df.columns)}, expected {len(cols) - 1} dimensions and 'value'")
        dest = OUT / out
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(cols)
            w.writerows([*(str(r[d]) for d in dims), repr(float(r[val]))] for r in df.to_dict("records"))
        print(f"{dest.relative_to(ROOT)}: {len(df)} records")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else SOURCES / "dat")
