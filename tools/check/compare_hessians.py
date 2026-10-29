"""Compare two market supply Hessians (the Parquet files of .cache/market_supply_hessian: ms, x, y, dq): entry by entry
and for symmetry of the EU sum (CAPRI's p_hessNQSupp is used as measured; the price responses of a convex supply side
are symmetric in theory, so the asymmetry is a measure of the measurement's noise).

    python tools/check/compare_hessians.py A.parquet B.parquet [--top 15]
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd


def eu(t):
    return t.groupby(["x", "y"]).dq.sum().unstack(fill_value=0.0)


def asym(h):
    c = sorted(set(h.index) & set(h.columns))
    m = h.loc[c, c].to_numpy()
    d = np.abs(m - m.T)
    s = np.maximum(np.abs(m), np.abs(m.T))
    return float(np.median(d[s > 1e-6] / s[s > 1e-6])) if (s > 1e-6).any() else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--top", type=int, default=15)
    o = ap.parse_args()
    A, B = pd.read_parquet(o.a), pd.read_parquet(o.b)
    m = A.merge(B, on=["ms", "x", "y"], how="outer", suffixes=("_a", "_b")).fillna(0.0)
    m["d"] = (m.dq_a - m.dq_b).abs()
    m["rel"] = m.d / m[["dq_a", "dq_b"]].abs().max(axis=1).clip(lower=1e-9)
    big = m[m[["dq_a", "dq_b"]].abs().max(axis=1) > 1e-3]
    print(f"entries {len(A)} / {len(B)}; equal {int((m.d == 0).sum())}; of the entries above 1e-3: relative difference "
          f"median {big.rel.median():.3g}, 90% {big.rel.quantile(0.9):.3g}, max {big.rel.max():.3g}")
    ea, eb = eu(A), eu(B)
    print(f"EU sum: median asymmetry |H - H'| / |H|: A {asym(ea):.3g}, B {asym(eb):.3g}")
    diag = [(x, float(ea.at[x, x]) if x in ea.index and x in ea.columns else 0.0,
             float(eb.at[x, x]) if x in eb.index and x in eb.columns else 0.0) for x in sorted(set(ea.index) | set(eb.index))]
    print("EU own-price responses (A, B):", ", ".join(f"{x} {a:.4g}/{b:.4g}" for x, a, b in diag if max(abs(a), abs(b)) > 1e-3))
    print(m.sort_values("d", ascending=False).head(o.top)[["ms", "x", "y", "dq_a", "dq_b"]].to_string(index=False))


if __name__ == "__main__":
    main()
