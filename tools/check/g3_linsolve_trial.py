"""G3.3, the solver question: the linear algebra of the lifted market system, and Newton's method on it, at a captured
solve (G3.1).

The system is the lifted form of capri_mod/market/market_system_ad.py, square once the empty balances are out and
their prices held (G3_SYSTEM.md, G3.2e); each equation divided by its largest derivative at the start, as
market_ipopt.py does.

    python tools/check/g3_linsolve_trial.py CAPTURE factor
        the square Jacobian at the start factorised and solved by each available sparse direct solver: SciPy's SuperLU
        (COLAMD ordering), Intel MKL's PARDISO (pypardiso), CasADi's MUMPS and CSparse; time and residual of the solve
    python tools/check/g3_linsolve_trial.py CAPTURE newton SOLVER
        Newton's method with that solver (superlu, pardiso, mumps), a backtracking line search on the largest scaled
        residual, from the state the solve started from; iterations, time, and the solution against the default solve's
"""
from __future__ import annotations

import pickle
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "check"))
import casadi as ca  # noqa: E402
import scipy.sparse as sps  # noqa: E402
import scipy.sparse.linalg as spla  # noqa: E402
from replay_market import load_module  # noqa: E402
from capri_mod.settings import override  # noqa: E402
from capri_mod.market.market_system_ad import market_system, market_x0  # noqa: E402


def _system(path: Path):
    rec = pickle.load(open(path, "rb"))
    exo = rec["args"]["exogenous_supply"]
    with override(rec["settings"].replace({"diagnostics.capture_market_dir": ""})):
        mm_d = load_module(rec["module"], path.parent / "blobs")
        t0 = time.time()
        mm_d.solve(**rec["args"])
        t_def = time.time() - t0
        mm_d._bilateral_eval(mm_d.sv.bilat_last_r.copy(), exo, None)
        fd, ld, _, _ = market_system(mm_d, exo, lifted=True)
        x_def = market_x0(mm_d, ld)
        mm = load_module(rec["module"], path.parent / "blobs")
        fs, _, _, _ = market_system(mm, exo)
        fn, lay, x, F = market_system(mm, exo, lifted=True)
        x0 = market_x0(mm, lay)
    sp = fs.jac_sparsity(0, 0)
    empty = np.nonzero(np.diff(np.asarray(sp.T.colind())) == 0)[0]
    keep = np.setdiff1d(np.arange(lay["n_F"]), empty)
    fF = ca.Function("F", [x], [F])
    fJ = ca.Function("J", [x], [ca.jacobian(F, x)])
    J0 = abs(fJ(x0).sparse().tocsr())
    sc = np.maximum(np.asarray(J0.max(axis=1).todense()).ravel(), 1e-12)
    return dict(fF=fF, fJ=fJ, x0=x0, keep=keep, sc=sc, lay=lay, x_def=x_def, t_def=t_def)


def _jac(s, v):
    J = s["fJ"](v).sparse().tocsr()[s["keep"], :][:, s["keep"]]
    return sps.diags(1.0 / s["sc"][s["keep"]]) @ J


def _res(s, v):
    return np.asarray(s["fF"](v), float).ravel()[s["keep"]] / s["sc"][s["keep"]]


def _solver(name):
    if name == "superlu":
        return lambda A, b: spla.splu(A.tocsc(), permc_spec="COLAMD").solve(b)
    if name == "pardiso":
        import pypardiso
        return lambda A, b: pypardiso.spsolve(A.tocsr(), b)
    if name in ("mumps", "csparse"):
        def f(A, b, _n=name):
            A = A.tocsc()
            M = ca.DM(ca.Sparsity(A.shape[0], A.shape[1], A.indptr.tolist(), A.indices.tolist()), A.data)
            ls = ca.Linsol("ls", _n, M.sparsity())
            ls.sfact(M)
            ls.nfact(M)
            return np.asarray(ls.solve(M, ca.DM(b)), float).ravel()
        return f
    raise ValueError(name)


def factor(path: Path) -> None:
    s = _system(path)
    A = _jac(s, s["x0"])
    b = -_res(s, s["x0"])
    print(f"square Jacobian {A.shape[0]} x {A.shape[1]}, {A.nnz} non-zeros; the default solve {s['t_def']:.1f} s")
    for name in ("superlu", "pardiso", "mumps", "csparse"):
        try:
            f = _solver(name)
            t0 = time.time()
            dx = f(A, b)
            t = time.time() - t0
            print(f"  {name}: {t:.2f} s, residual of the linear solve {np.max(np.abs(A @ dx - b)):.1e}", flush=True)
        except Exception as e:  # report and go on
            print(f"  {name}: {type(e).__name__} {str(e)[:120]}", flush=True)


def newton(path: Path, name: str) -> None:
    s = _system(path)
    f = _solver(name)
    keep = s["keep"]
    x = s["x0"].copy()
    t_all = time.time()
    t_lin = 0.0
    for it in range(60):
        r = _res(s, x)
        nk = float(np.max(np.abs(r)))
        if nk < 1e-10:
            break
        A = _jac(s, x)
        t0 = time.time()
        dx = f(A, -r)
        t_lin += time.time() - t0
        t = 1.0
        while True:
            xt = x.copy()
            xt[keep] += t * dx
            if float(np.max(np.abs(_res(s, xt)))) < nk or t < 1e-6:
                break
            t *= 0.5
        x = xt
        print(f"  step {it}: residual {nk:.2e}, step length {t:g}", flush=True)
    t_all = time.time() - t_all
    rel = np.abs(x - s["x_def"]) / np.maximum(np.abs(s["x_def"]), 1e-3)
    nb = sum(n for nm, n in s["lay"]["x"] if nm.startswith("r_"))
    print(f"Newton with {name}: {it} steps to {float(np.max(np.abs(_res(s, x)))):.1e}, {t_all:.1f} s ({t_lin:.1f} s in "
          f"the linear solves); the default solve {s['t_def']:.1f} s; prices within {float(rel[:nb].max()):.1e} of its")


if __name__ == "__main__":
    p = Path(sys.argv[1])
    if sys.argv[2] == "factor":
        factor(p)
    else:
        newton(p, sys.argv[3])
