"""Regional own-price supply elasticities of the 15 arable crops: CAPRI's PELA with CAPRI's upper-bound rule.

Input: capri_data/sources/estnlp/pela_own_price.csv, the own-price slice (2005) of PELA in CAPRI's supply estimation
results (dat/estnlp/results.gdx, symbol PELA, region x crop x crop x year), by model region; written by
tools/build/ingest_pela_gtap.py from a gdxdump of that file.
Rule: CAPRI's heuristic bound on high elasticities (gams/supply/pmp_terms/impose_upper_bound_on_elasticity.gms,
capri_mod.supply.capri_pmp.dampen_elasticity): values above 4.5 become min(8, sqrt(e) + 4.5 - sqrt(4.5)); the rest
pass through.
Output: capri_data/2017/supply/supply_elasticities_regional.csv (model regions x crops; empty where PELA has none).

    python tools/build/build_supply_elasticities_regional.py [--check]

--check compares with the file in place and writes nothing (exit 1 on a difference).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "capri_data" / "sources" / "estnlp" / "pela_own_price.csv"
OUT = ROOT / "capri_data" / "2017" / "supply" / "supply_elasticities_regional.csv"


def build() -> pd.DataFrame:
    sys.path.insert(0, str(ROOT))
    from capri_mod.supply.capri_pmp import dampen_elasticity
    pela = pd.read_csv(SRC, index_col=0)
    out = pd.DataFrame(dampen_elasticity(pela.values), index=pela.index, columns=pela.columns)
    out = out.where(pela.notna())
    out.index.name = "model_region"
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    new = build()
    if a.check:
        cur = pd.read_csv(OUT, index_col=0)
        same = (cur.shape == new.shape and list(cur.columns) == list(new.columns) and list(cur.index) == list(new.index)
                and bool(np.allclose(cur.values, new.values, rtol=1e-12, atol=0.0, equal_nan=True)))
        print("supply_elasticities_regional.csv:", "reproduced" if same else "DIFFERS")
        return 0 if same else 1
    new.to_csv(OUT, lineterminator="\n")
    print(f"written {OUT.relative_to(ROOT)}: {new.shape[0]} regions x {new.shape[1]} crops, "
          f"{int((new > 4.5).sum().sum())} values above 4.5 after the bound")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
