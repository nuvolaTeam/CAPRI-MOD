"""Replay market solves written by a run with diagnostics.capture_market_dir (G3.1, claude/g3_plan.md).

Each file holds the market module as it was before one solve (MarketModule._solve_captured; its attributes stored
once each by content in <folder>/blobs), the solve's arguments,
the run's settings and the equilibrium the run got. The replay unpickles the module, solves again with the same
arguments under the same settings and compares the equilibrium and the module's warm-start state with the run's, bit
for bit (pandas equals, numpy array_equal; NaN equal to NaN). Exit code 1 if any file differs.

    python tools/check/replay_market.py runs/capture [--files market_000.pkl,market_003.pkl]
"""
from __future__ import annotations

import argparse
import dataclasses
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def same(a, b) -> bool:
    """Bitwise equality of the result objects (frames, series, arrays, dicts, scalars; NaN equal to NaN)."""
    if isinstance(a, (pd.DataFrame, pd.Series)):
        return isinstance(b, type(a)) and a.equals(b) and list(a.index) == list(b.index)
    if isinstance(a, np.ndarray):
        return isinstance(b, np.ndarray) and a.shape == b.shape and np.array_equal(a, b, equal_nan=a.dtype.kind == "f")
    if isinstance(a, dict):
        return isinstance(b, dict) and a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        return isinstance(b, type(a)) and len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, float) and isinstance(b, float) and np.isnan(a) and np.isnan(b):
        return True
    if dataclasses.is_dataclass(a) and not isinstance(a, type):
        return type(a) is type(b) and all(same(getattr(a, f.name), getattr(b, f.name)) for f in dataclasses.fields(a))
    try:
        return bool(a == b)
    except Exception:
        return False


def differences(a, b) -> list:
    """The equilibrium's fields (or the state's attributes) that differ."""
    if dataclasses.is_dataclass(a):
        return [f.name for f in dataclasses.fields(a) if not same(getattr(a, f.name), getattr(b, f.name))]
    names = [k for k in getattr(type(a), "__slots__", ())] or list(vars(a))
    return [k for k in names if not same(getattr(a, k, None), getattr(b, k, None))]


def load_module(data: bytes, blobs: Path):
    """The market module of a capture: its pickle with the attributes stored by content in blobs/ (persistent ids)."""
    import io
    loaded = {}

    class _U(pickle.Unpickler):
        def persistent_load(self, pid):
            if pid not in loaded:
                loaded[pid] = pickle.loads((blobs / f"{pid}.pkl").read_bytes())
            return loaded[pid]
    return _U(io.BytesIO(data)).load()


def replay(path: Path) -> list:
    from capri_mod.settings import override
    with open(path, "rb") as fh:
        rec = pickle.load(fh)
    mm = load_module(rec["module"], path.parent / "blobs")
    with override(rec["settings"].replace({"diagnostics.capture_market_dir": ""})):
        eq = mm.solve(**rec["args"])
    return ([f"result.{k}" for k in differences(rec["result"], eq)]
            + [f"sv.{k}" for k in differences(rec["sv_after"], mm.sv)])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--files", default="", help="comma-separated file names (default: all market_*.pkl)")
    a = ap.parse_args()
    files = ([a.folder / f for f in a.files.split(",")] if a.files else sorted(a.folder.glob("market_*.pkl")))
    bad = 0
    for f in files:
        d = replay(f)
        bad += bool(d)
        print(f"{f.name}: {'identical' if not d else 'differs in ' + ', '.join(d)}")
    print(f"{len(files) - bad} of {len(files)} solves replayed bit for bit")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
