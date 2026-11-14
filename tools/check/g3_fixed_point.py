"""G3.2d: is the default solve's equilibrium a fixed point of ONE evaluation of the market's functions?

The default solve evaluates the whole model response (supply, use, the market's own blocks) at the price ratios r
(`_bilateral_eval`); some blocks read state the previous evaluation left (the land / FEDE rounds' milk price, the
young-animal / raw milk rounds, the warm starts). In G3 every block is a function of the system's unknowns only. This
check replays each captured solve (G3.1), then evaluates the market twice more at the solve's final r and compares:
  - the two fresh evaluations with each other (any difference: the evaluation depends on the state the previous one
    left, a lag that is not spent at the equilibrium);
  - the fresh evaluation's supply and use with the solve's own (the rows of the market regions; the EU aggregate rows
    the solve adds afterwards are not compared);
  - the fresh evaluation's balance residuals relative to the market's scale (S0 + D0) as the solve's test.
Reported per solve: the largest relative difference of supply and of use for each comparison (relative to
max(|value|, 1 kt)), where, and the largest balance residual.

    python tools/check/g3_fixed_point.py runs/capture [--files market_000.pkl,...]
"""
from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "check"))


def _largest(a: pd.DataFrame, b: pd.DataFrame):
    """The largest relative difference between two frames over their common cells (scale max(|b|, 1 kt))."""
    rows = [x for x in a.index if x in b.index]
    cols = [c for c in a.columns if c in b.columns]
    A = a.reindex(index=rows, columns=cols).fillna(0.0).to_numpy(dtype=float)
    B = b.reindex(index=rows, columns=cols).fillna(0.0).to_numpy(dtype=float)
    d = np.abs(A - B) / np.maximum(np.abs(B), 1.0)
    if not d.size:
        return 0.0, None
    k = np.unravel_index(int(np.argmax(d)), d.shape)
    return float(d[k]), (rows[k[0]], cols[k[1]])


def check(path: Path) -> dict:
    from replay_market import load_module
    from capri_mod.settings import override
    with open(path, "rb") as fh:
        rec = pickle.load(fh)
    mm = load_module(rec["module"], path.parent / "blobs")
    args = rec["args"]
    with override(rec["settings"].replace({"diagnostics.capture_market_dir": ""})):
        eq = mm.solve(**args)
        r = mm.sv.bilat_last_r.copy()
        exo, ts = args.get("exogenous_supply"), args.get("trade_scenario")
        S1, D1, _, F1, _ = mm._bilateral_eval(r, exo, ts)
        S2, D2, _, F2, _ = mm._bilateral_eval(r, exo, ts)
    out = {"repeat_S": _largest(S2, S1), "repeat_D": _largest(D2, D1),
           "solve_S": _largest(S1, eq.production), "solve_D": _largest(D1, eq.consumption)}
    worst = (0.0, None)
    for c, sc in (mm.par.bilat or {}).items():
        f = np.abs(np.asarray(F1[c], float)) / np.maximum(sc.S0 + sc.D0, 1.0)
        if f.size and float(f.max()) > worst[0]:
            worst = (float(f.max()), (list(sc.regions)[int(np.argmax(f))], c))
    out["balance"] = worst
    out["converged"] = bool(eq.converged)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--files", default="")
    a = ap.parse_args()
    files = ([a.folder / f for f in a.files.split(",")] if a.files else sorted(a.folder.glob("market_*.pkl")))
    for f in files:
        o = check(f)
        print(f"{f.name}: repeat S {o['repeat_S'][0]:.2e} {o['repeat_S'][1]}, D {o['repeat_D'][0]:.2e} "
              f"{o['repeat_D'][1]}; against the solve S {o['solve_S'][0]:.2e} {o['solve_S'][1]}, D "
              f"{o['solve_D'][0]:.2e} {o['solve_D'][1]}; balance {o['balance'][0]:.2e} {o['balance'][1]}; "
              f"converged {o['converged']}", flush=True)


if __name__ == "__main__":
    main()
