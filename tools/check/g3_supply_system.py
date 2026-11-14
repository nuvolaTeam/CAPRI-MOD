"""G3.2c/e: the supply side as one CasADi function with its blocks' equations (capri_mod/market/supply_system_ad.py)
at the default solve's solutions.

Each capture (G3.1) is replayed; the market is evaluated once more at the solve's final prices (`_bilateral_eval`);
the supply system, built at the module's calibration state and the solve's supply-model output, is evaluated at that
evaluation's unknowns (its Armington ratios, r, the young-animal prices, the dairy blocks' unknowns, FEDE, the rents):
its supply is compared with the evaluation's, cell by cell (relative to max(|q|, 1 kt); the EU's residual feeds left
out, set after the use side), and its block equations' residuals reported (relative to the block's scale: the
young-animal goods' net supply, the dairy blocks' base raw milk).

    python tools/check/g3_supply_system.py runs/capture [--files market_000.pkl,...]
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
    from capri_mod.market.supply_system_ad import supply_inputs, supply_system
    with open(path, "rb") as fh:
        rec = pickle.load(fh)
    mm = load_module(rec["module"], path.parent / "blobs")
    args = rec["args"]
    with override(rec["settings"].replace({"diagnostics.capture_market_dir": ""})):
        mm.solve(**args)
        r = mm.sv.bilat_last_r.copy()
        S1, _, PAr, _, _ = mm._bilateral_eval(r, args.get("exogenous_supply"), args.get("trade_scenario"))
        t0 = time.time()
        f, lay = supply_system(mm, args.get("exogenous_supply"))
        built = time.time() - t0
        PA = PAr.reindex(index=lay["regions"], columns=lay["cols"]).fillna(1.0).to_numpy(dtype=float)
        out = f(*supply_inputs(mm, lay, PA))
        byp = set()
        for reg in mm.EU:
            byp |= {(reg, p) for p in mm.eu_feed_byproduct_output(reg)}
    S = np.asarray(out[0], float)
    ref = S1.reindex(index=lay["regions"], columns=lay["cols"]).to_numpy(dtype=float)
    d = np.abs(S - ref) / np.maximum(np.abs(ref), 1.0)
    for i, rg in enumerate(lay["regions"]):
        for j, c in enumerate(lay["cols"]):
            if (rg, c) in byp:
                d[i, j] = 0.0
    k = np.unravel_index(int(np.argmax(d)), d.shape)
    ry = np.asarray(out[1], float).ravel()
    st = mm.seen.yani_state or {}
    ysc = np.array([max(abs(float(st[reg]["net"][g])), 1.0) for reg, goods in lay["ylay"] for g in goods])
    dp = mm._dairy_params() or {}
    eE = np.asarray(out[2], float).ravel()
    sE = np.repeat([max(float(dp["ms"][m]["Q0"][dp["ms"][m]["iM"]]), 1.0) for m in lay["ms"]], 3) if lay["ms"] else 1.0
    wp = mm._dairy_world_params() or {}
    eW = np.asarray(out[3], float).ravel()
    sW = np.repeat([max(float(wp[r]["Q0"][wp[r]["iM"]]), 1.0) for r in lay["wl"]], 3) if lay["wl"] else 1.0
    worst = sorted(((float(d[i, j]), lay["regions"][i], lay["cols"][j], float(ref[i, j]), float(S[i, j]))
                    for i, j in zip(*np.nonzero(d > 1e-9))), reverse=True)[:8]
    return {"largest": float(d[k]), "at": (lay["regions"][k[0]], lay["cols"][k[1]]), "cells": d.size,
            "above": int((d > 1e-9).sum()), "built": round(built, 1), "worst": worst,
            "yani": float(np.max(np.abs(ry) / ysc)) if ry.size else 0.0, "n_yani": ry.size,
            "dairy_eu": float(np.max(np.abs(eE) / sE)) if eE.size else 0.0, "n_eu": eE.size,
            "dairy_w": float(np.max(np.abs(eW) / sW)) if eW.size else 0.0, "n_w": eW.size,
            "milk_path": lay["milk_path"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--files", default="")
    a = ap.parse_args()
    files = ([a.folder / f for f in a.files.split(",")] if a.files else sorted(a.folder.glob("market_*.pkl")))
    for f in files:
        o = check(f)
        print(f"{f.name}: supply over {o['cells']} cells, largest relative difference {o['largest']:.2e} at {o['at']}, "
              f"{o['above']} cells above 1e-9; residuals: young animals {o['yani']:.2e} ({o['n_yani']}), EU dairy "
              f"{o['dairy_eu']:.2e} ({o['n_eu']}), other dairy {o['dairy_w']:.2e} ({o['n_w']}); milk path "
              f"{o['milk_path']}; built in {o['built']} s", flush=True)
        for w in o["worst"]:
            print("   ", w, flush=True)


if __name__ == "__main__":
    main()
