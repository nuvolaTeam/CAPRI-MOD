"""Compare two run pickles of tools/run/run_f2f_2030.py value by value (the refactor gate: a move must reproduce
the reference run). Floats compared with a relative tolerance (default 1e-10); reports every differing path.

    python tools/check/compare_pickles_exact.py REF.pkl NEW.pkl [--rtol 1e-10] [--ignore meta.time_s,...]
"""
from __future__ import annotations

import argparse
import math
import pickle
import sys

import numpy as np
import pandas as pd


def walk(a, b, path, out, rtol, ignore):
    if path in ignore:
        return
    if isinstance(a, (pd.DataFrame, pd.Series)):
        if not isinstance(b, type(a)) or a.shape != b.shape:
            out.append((path, "shape/type", type(b).__name__)); return
        if isinstance(a, pd.DataFrame) and (list(a.columns) != list(b.columns) or list(a.index) != list(b.index)):
            out.append((path, "labels", "")); return
        if isinstance(a, pd.Series) and list(a.index) != list(b.index):
            out.append((path, "labels", "")); return
        walk(a.to_numpy(), b.to_numpy(), path, out, rtol, ignore); return
    if isinstance(a, np.ndarray):
        if not isinstance(b, np.ndarray) or a.shape != b.shape:
            out.append((path, "shape", "")); return
        if a.dtype.kind in "fc" or b.dtype.kind in "fc":
            try:
                x, y = a.astype(float), b.astype(float)
            except (TypeError, ValueError):
                if not (a == b).all(): out.append((path, "values", ""))
                return
            ok = np.isclose(x, y, rtol=rtol, atol=1e-12, equal_nan=True)
            if not ok.all():
                i = np.argwhere(~ok)[0]
                out.append((path, f"{int((~ok).sum())} values", f"first at {tuple(i)}: {x[tuple(i)]!r} vs {y[tuple(i)]!r}"))
        elif not np.array_equal(a, b):
            out.append((path, "values", ""))
        return
    if isinstance(a, dict):
        if not isinstance(b, dict):
            out.append((path, "type", type(b).__name__)); return
        for k in set(a) | set(b):
            if k not in a or k not in b:
                out.append((f"{path}.{k}", "missing in " + ("new" if k in a else "ref"), "")); continue
            walk(a[k], b[k], f"{path}.{k}", out, rtol, ignore)
        return
    if isinstance(a, (list, tuple)):
        if not isinstance(b, (list, tuple)) or len(a) != len(b):
            out.append((path, "length", "")); return
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, f"{path}[{i}]", out, rtol, ignore)
        return
    if isinstance(a, float) or isinstance(b, float):
        try:
            fa, fb = float(a), float(b)
        except (TypeError, ValueError):
            out.append((path, "type", "")); return
        if not (math.isclose(fa, fb, rel_tol=rtol, abs_tol=1e-12) or (math.isnan(fa) and math.isnan(fb))):
            out.append((path, "value", f"{fa!r} vs {fb!r}"))
        return
    if hasattr(a, "__dict__") and not isinstance(a, type):
        walk(vars(a), vars(b) if hasattr(b, "__dict__") else b, path, out, rtol, ignore); return
    try:
        if a != b:
            out.append((path, "value", f"{a!r:.80} vs {b!r:.80}"))
    except Exception:
        out.append((path, "uncomparable", ""))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ref"); ap.add_argument("new")
    ap.add_argument("--rtol", type=float, default=1e-10)
    ap.add_argument("--ignore", default="")
    a = ap.parse_args()
    ref, new = pickle.load(open(a.ref, "rb")), pickle.load(open(a.new, "rb"))
    ignore = {"$" + ("." + p if p else "") for p in a.ignore.split(",") if p}
    out = []
    walk(ref, new, "$", out, a.rtol, ignore)
    for p, what, detail in out[:60]:
        print(f"{p}: {what} {detail}")
    print(f"{len(out)} differences" if out else "identical within rtol")
    return 1 if out else 0


if __name__ == "__main__":
    sys.exit(main())
