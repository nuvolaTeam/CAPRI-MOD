"""Rebuild the input files that several builders patch in place, running those builders in their order (K70).

Two files are written by more than one builder, each owning some cells:

  capri_data/2017/supply/yields.csv
      1 build_crop_economics_2017.py   crop columns (CAPRI 2017 YILD, LEVL-weighted)
      3 build_animal_yields.py         animal columns (CAPRI YILD per model head)
  capri_data/2017/market/producer_prices.csv
      2 build_eu_producer_prices.py    crop rows (CAPRI's production-weighted EU price; reads yields.csv, and the
                                       regional prices that step 1 writes to sources/capreg/capreg_producer_prices.csv)
      livestock rows: no builder (the SHGM/SHGF rows came from build_shg_split.py's one-time split)
  (armington_params.csv, written by build_dairy_trade_params.py and build_feed_byproducts.py until 29 October
  2026: removed with its last column, eps, which acted on no result; KNOWN_ISSUES K72)

The base files these patch (areas, herds, the rest of yields.csv) come from build_capri_base.py, which is not rerun
here. Inputs: CAPRI's 2017 result dumps (--dump-dir, res_17*.txt) and CAPRI's market exports (--uploads:
data_market_1730defaulta.csv).

    python tools/build/build_patched_inputs.py [--dump-dir DIR] [--uploads DIR] [--check]

--check runs the chain on a copy of the repository (without capri_reference) and reports whether the two files,
and the other files the steps write, come out as they are in place (CSV values within 1e-9); nothing in the repository is changed.
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _read_csv(*a, **k):
    """pandas.read_csv with floats parsed to the last digit (KNOWN_ISSUES K82)."""
    import pandas as pd
    k.setdefault("float_precision", "round_trip")
    return pd.read_csv(*a, **k)

ROOT = Path(__file__).resolve().parents[2]

STEPS = (
    ["build_crop_economics_2017.py", "{dump}"],
    ["build_eu_producer_prices.py"],
    ["build_animal_yields.py"],
)
TARGETS = ("capri_data/2017/supply/yields.csv", "capri_data/2017/market/producer_prices.csv")


def same(p: Path, q: Path) -> bool:
    """Equal files; CSV tables equal within 1e-9 relative (the builders' float formatting differs in the last digit)."""
    if filecmp.cmp(p, q, shallow=False):
        return True
    if p.suffix != ".csv":
        return False
    import numpy as np
    import pandas as pd
    try:
        a, b = _read_csv(p), _read_csv(q)
    except Exception:
        return False
    if list(a.columns) != list(b.columns) or a.shape != b.shape:
        return False
    for c in a.columns:
        x, y = a[c], b[c]
        if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y):
            if not np.allclose(x.to_numpy(float), y.to_numpy(float), rtol=1e-9, atol=0.0, equal_nan=True):
                return False
        elif not x.astype(str).equals(y.astype(str)):
            return False
    return True


def run(root: Path, dump: str, up: str) -> bool:
    ok = True
    for cmd in STEPS:
        args = [c.format(dump=dump, up=up) for c in cmd]
        r = subprocess.run([sys.executable, str(root / "tools" / "build" / args[0])] + args[1:], cwd=root,
                           capture_output=True, text=True)
        tail = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
        print(f"{args[0]:32s} {'FAILED' if r.returncode else 'ok':6s} {tail[:120]}")
        if r.returncode:
            print(r.stderr.strip()[-800:])
            ok = False
            break
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", default="/home/claude/work/capreg")
    ap.add_argument("--uploads", default="/mnt/user-data/uploads")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if not a.check:
        return 0 if run(ROOT, a.dump_dir, a.uploads) else 1
    with tempfile.TemporaryDirectory() as td:
        cp = Path(td) / "repo"
        skip = shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".pytest_cache")

        def _ignore(d, names):
            out = set(skip(d, names))
            if Path(d) == ROOT:
                out |= {"capri_reference", "build"} & set(names)
            if Path(d) == ROOT / "capri_data" / "pipeline":
                out |= {"store"} & set(names)
            return out
        shutil.copytree(ROOT, cp, symlinks=False, ignore=_ignore)
        if not run(cp, a.dump_dir, a.uploads):
            return 1
        diff = []
        for p in sorted((cp / "capri_data").rglob("*")):
            if p.is_file():
                q = ROOT / p.relative_to(cp)
                if not q.exists() or not same(p, q):
                    diff.append(str(p.relative_to(cp)))
        for t in TARGETS:
            print(f"{t}: {'DIFFERS' if t in diff else 'reproduced'}")
        others = [d for d in diff if d not in TARGETS]
        print(f"other files that differ: {others if others else 'none'}")
        return 1 if diff else 0


if __name__ == "__main__":
    raise SystemExit(main())
