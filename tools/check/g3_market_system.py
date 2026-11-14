"""G3.2e: the assembled market system F(x) = 0 (capri_mod/market/market_system_ad.py) at the default solve's solutions,
and its structure.

Each capture (G3.1) is replayed and the market evaluated once more at the solve's final prices (`_bilateral_eval`);
the system is built and evaluated at that evaluation's unknowns. Reported: the system's size; per equation block the
largest residual relative to its scale (balances: S0 + D0, the default solve's test; quotas: as they are; young
animals: their net supply; dairy blocks: their base raw milk; FeedBal_: the energy fed at calibration; land: the
calibration land); the pooled balances; the system's supply and use against the evaluation's; and the Jacobian's
structure (non-zeros, structural rank, the Dulmage-Mendelsohn blocks' sizes from CasADi's btf).

    python tools/check/g3_market_system.py runs/capture [--files market_000.pkl,...] [--structure]
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


def _scales(mm, lay) -> np.ndarray:
    """Each equation's scale (capri_mod/market/market_g3.py, the solver's own)."""
    from capri_mod.market.market_g3 import _scales as scales
    return scales(mm, lay)


def _count(names) -> dict:
    """{block name: count} of equation or unknown names "block[k]"."""
    out: dict = {}
    for n in names:
        b = n.split("[")[0]
        out[b] = out.get(b, 0) + 1
    return out


def check(path: Path, structure: bool) -> dict:
    import casadi as ca
    from replay_market import load_module
    from capri_mod.settings import override
    from capri_mod.market.market_system_ad import market_system, market_x0
    with open(path, "rb") as fh:
        rec = pickle.load(fh)
    mm = load_module(rec["module"], path.parent / "blobs")
    args = rec["args"]
    with override(rec["settings"].replace({"diagnostics.capture_market_dir": ""})):
        mm.solve(**args)
        r = mm.sv.bilat_last_r.copy()
        S1, D1, _, _, _ = mm._bilateral_eval(r, args.get("exogenous_supply"), args.get("trade_scenario"))
        mm._apply_feed_byproduct_supply(S1)
        t0 = time.time()
        fn, lay, x, F = market_system(mm, args.get("exogenous_supply"), args.get("trade_scenario"))
        built = time.time() - t0
        x0 = market_x0(mm, lay)
        Fv, pooled, S, D = (np.asarray(v, float) for v in fn(x0))
    sc_ = _scales(mm, lay)
    rel = np.abs(Fv.ravel()) / sc_
    blocks, o = {}, 0
    for name, n in lay["eqs"]:
        blocks[name] = (n, float(rel[o:o + n].max()) if n else 0.0)
        o += n
    refS = S1.reindex(index=lay["regions"], columns=lay["cols"]).to_numpy(dtype=float)
    refD = D1.reindex(index=lay["regions"], columns=lay["cols"]).to_numpy(dtype=float)
    dS = float((np.abs(S - refS) / np.maximum(np.abs(refS), 1.0)).max())
    dD = float((np.abs(D - refD) / np.maximum(np.abs(refD), 1.0)).max())
    out = {"n_x": lay["n_x"], "n_F": lay["n_F"], "blocks": blocks, "pooled": pooled.ravel().tolist(), "dS": dS,
           "dD": dD, "built": round(built, 1)}
    if structure:
        t0 = time.time()
        sp = fn.jac_sparsity(0, 0)              # the pattern by seeding, without the symbolic Jacobian
        out["nnz"] = int(sp.nnz())
        nb, rowperm, colperm, rowblock, colblock, crb, ccb = sp.btf()
        sizes = np.diff(np.asarray(rowblock))
        out["btf"] = {"blocks": int(nb), "largest": int(sizes.max()) if len(sizes) else 0,
                      "sizes_top": sorted(sizes.tolist(), reverse=True)[:8], "coarse_rows": list(crb),
                      "coarse_cols": list(ccb)}
        out["sprank"] = int(ca.sprank(sp))
        # which equations and unknowns: the empty rows and columns, and the coarse blocks (CasADi's btf works on the
        # transposed pattern: rows crow[0]:crow[2] over columns ccol[0]:ccol[1] are the over-determined part, rows
        # crow[2]:crow[3] over ccol[1]:ccol[2] the square part, rows crow[3]:crow[4] over ccol[2]:ccol[4] the
        # under-determined part)
        rn = [f"{n}[{k}]" for n, m in lay["eqs"] for k in range(m)]
        cn = [f"{n}[{k}]" for n, m in lay["x"] for k in range(m)]
        rows_nnz = np.diff(np.asarray(sp.T.colind()))
        cols_nnz = np.diff(np.asarray(sp.colind()))
        out["empty_rows"] = _count([rn[i] for i in np.nonzero(rows_nnz == 0)[0]])
        out["empty_cols"] = _count([cn[j] for j in np.nonzero(cols_nnz == 0)[0]])
        er, ec = set(np.nonzero(rows_nnz == 0)[0].tolist()), set(np.nonzero(cols_nnz == 0)[0].tolist())
        # the balances and the price ratios are in the same order (commodity, region): the same cells?
        out["empty_same_cells"] = er == ec
        regs = lay["regions"]
        cn_cell = [f"{n[2:]}:{regs[k]}" if n.startswith("r_") else f"{n}[{k}]" for n, m in lay["x"] for k in range(m)]
        out["empty_rows_only"] = sorted(cn_cell[i] for i in er - ec)      # bal and r share the (commodity, region) order
        out["empty_cols_only"] = sorted(cn_cell[j] for j in ec - er)
        keep_r = [i for i in range(sp.size1()) if i not in er]
        keep_c = [j for j in range(sp.size2()) if j not in ec]
        sub = sp.sub(keep_r, keep_c, False)[0]
        out["sprank_without_empty"] = (int(ca.sprank(sub)), len(keep_r), len(keep_c))
        # and with the prices of the empty balances fixed too (their columns out): the square system G3 solves
        keep_c2 = [j for j in keep_c if j not in er]
        sub2 = sp.sub(keep_r, keep_c2, False)[0]
        out["sprank_square"] = (int(ca.sprank(sub2)), len(keep_r), len(keep_c2))
        nb2, _, _, rb2, _, _, _ = sub2.btf()
        out["btf_square"] = sorted(np.diff(np.asarray(rb2)).tolist(), reverse=True)[:6]
        rp, cp = list(rowperm), list(colperm)
        out["over_rows"] = _count([rn[rp[i]] for i in range(crb[0], crb[2])])
        out["under_cols"] = _count([cn[cp[j]] for j in range(ccb[2], ccb[4])])
        out["structure_s"] = round(time.time() - t0, 1)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--files", default="")
    ap.add_argument("--structure", action="store_true")
    a = ap.parse_args()
    files = ([a.folder / f for f in a.files.split(",")] if a.files else sorted(a.folder.glob("market_*.pkl")))
    for f in files:
        o = check(f, a.structure)
        print(f"{f.name}: {o['n_x']} unknowns, {o['n_F']} equations (built in {o['built']} s); "
              + "; ".join(f"{k} {n}: {v:.2e}" for k, (n, v) in o["blocks"].items())
              + f"; pooled {o['pooled']}; supply vs the evaluation {o['dS']:.2e}, use {o['dD']:.2e}", flush=True)
        if "nnz" in o:
            print(f"   Jacobian: {o['nnz']} non-zeros, structural rank {o['sprank']}, btf {o['btf']} "
                  f"({o['structure_s']} s)", flush=True)
            print(f"   empty equations {o['empty_rows']}; empty unknowns {o['empty_cols']}; the same cells "
                  f"{o['empty_same_cells']}; without them: structural rank, rows, columns {o['sprank_without_empty']}",
                  flush=True)
            print(f"   square system (empty balances out, their prices fixed): structural rank, rows, columns "
                  f"{o['sprank_square']}, its btf blocks {o['btf_square']}", flush=True)
            print(f"   empty balance whose price enters elsewhere {o['empty_rows_only']}; empty price whose balance is "
                  f"not {o['empty_cols_only']}", flush=True)
            print(f"   over-determined equations {o['over_rows']}", flush=True)
            print(f"   under-determined unknowns {o['under_cols']}", flush=True)


if __name__ == "__main__":
    main()
