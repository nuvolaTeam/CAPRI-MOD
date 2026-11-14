"""G3.2d: the use side in CasADi (capri_mod/market/use_ad.py) against the default solve's use at its solutions.

Each capture (G3.1) is replayed; the market is evaluated once more at the solve's final prices (`_bilateral_eval`,
which leaves its inputs in the module's state); the use function, built at the module's calibration state, is
evaluated at those inputs and compared with the evaluation's use, cell by cell (relative to max(|use|, 1 kt)).

    python tools/check/g3_use_residuals.py runs/capture [--files market_000.pkl,...]
"""
from __future__ import annotations

import argparse
import pickle
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "check"))


def check(path: Path) -> dict:
    from replay_market import load_module
    from capri_mod.settings import override
    from capri_mod.market.use_ad import use_function, use_inputs
    with open(path, "rb") as fh:
        rec = pickle.load(fh)
    mm = load_module(rec["module"], path.parent / "blobs")
    args = rec["args"]
    with override(rec["settings"].replace({"diagnostics.capture_market_dir": ""})):
        mm.solve(**args)
        r = mm.sv.bilat_last_r.copy()
        _, D1, _, _, _ = mm._bilateral_eval(r, args.get("exogenous_supply"), args.get("trade_scenario"))
        t0 = time.time()
        f, lay = use_function(mm)
        built = time.time() - t0
        D = np.asarray(f(*use_inputs(mm, lay)), float)
    ref = D1.reindex(index=list(mm.regions), columns=list(mm.commodities)).to_numpy(dtype=float)
    d = np.abs(D - ref) / np.maximum(np.abs(ref), 1.0)
    k = np.unravel_index(int(np.argmax(d)), d.shape)
    n_bad = int((d > 1e-12).sum())
    return {"largest": float(d[k]), "at": (list(mm.regions)[k[0]], list(mm.commodities)[k[1]]),
            "cells": d.size, "above_1e-12": n_bad, "built_s": round(built, 1),
            "worst": sorted(((float(d[i, j]), mm.regions[i], mm.commodities[j], float(ref[i, j]), float(D[i, j]))
                             for i, j in zip(*np.nonzero(d > 1e-12))), reverse=True)[:8]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--files", default="")
    a = ap.parse_args()
    files = ([a.folder / f for f in a.files.split(",")] if a.files else sorted(a.folder.glob("market_*.pkl")))
    for f in files:
        o = check(f)
        print(f"{f.name}: use over {o['cells']} cells, largest relative difference {o['largest']:.2e} at {o['at']}, "
              f"{o['above_1e-12']} cells above 1e-12 (function built in {o['built_s']} s)", flush=True)
        for w in o["worst"]:
            print("   ", w, flush=True)


if __name__ == "__main__":
    main()
