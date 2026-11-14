"""G3.3 trial: IPOPT on the assembled market system in its lifted form (capri_mod/market/market_system_ad.py,
lifted=True: the Armington ratios, supply and use as unknowns with their defining equations, as CAPRI's m_globMarket),
from the state a captured solve started from, against the default solve's equilibrium.

A zero objective with the system as equality constraints (IPOPT as a feasibility solver, as CONOPT in CAPRI's market
model); the empty region-commodity balances out and their prices held at the start (G3_SYSTEM.md, G3.2e); the exact
Jacobian from CasADi; the Lagrangian's Hessian exact or limited-memory (option). Each equation scaled by its block's
scale (g3_market_system._scales). Reports IPOPT's status, iterations and time, the largest scaled residual, and each
unknown block's largest relative difference from the default solve's equilibrium.

    python tools/check/g3_ipopt_trial.py runs/capture/market_011.pkl [exact|lbfgs|newton] [ipopt.option=value ...]

newton: CasADi's rootfinder (Newton's method with the exact sparse Jacobian, CSparse) on the same square system instead
of IPOPT.
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
from replay_market import load_module  # noqa: E402
from capri_mod.settings import override  # noqa: E402
from capri_mod.market.market_system_ad import market_system, market_x0  # noqa: E402
from g3_market_system import _scales  # noqa: E402


def main() -> None:
    p = Path(sys.argv[1])
    hess = sys.argv[2] if len(sys.argv) > 2 else "lbfgs"
    rec = pickle.load(open(p, "rb"))
    exo = rec["args"]["exogenous_supply"]
    with override(rec["settings"].replace({"diagnostics.capture_market_dir": ""})):
        mm_d = load_module(rec["module"], p.parent / "blobs")
        t0 = time.time()
        assert mm_d.solve(**rec["args"]).converged
        t_def = time.time() - t0
        mm_d._bilateral_eval(mm_d.sv.bilat_last_r.copy(), exo, None)
        fn_d, lay_d, _, _ = market_system(mm_d, exo, lifted=True)
        x_def = market_x0(mm_d, lay_d)
        mm = load_module(rec["module"], p.parent / "blobs")
        fs, ls, _, _ = market_system(mm, exo)                 # the substituted form: which balances are empty
        t0 = time.time()
        fn, lay, x, F = market_system(mm, exo, lifted=True)
        t_build = time.time() - t0
        x0 = market_x0(mm, lay)
    sp = fs.jac_sparsity(0, 0)
    er = np.nonzero(np.diff(np.asarray(sp.T.colind())) == 0)[0]
    sc = _scales(mm, lay)
    keep = np.setdiff1d(np.arange(lay["n_F"]), er)
    g = F[keep.tolist()] / ca.DM(sc[keep])
    lbx, ubx = -np.inf * np.ones(lay["n_x"]), np.inf * np.ones(lay["n_x"])
    lbx[er], ubx[er] = x0[er], x0[er]
    if hess == "newton":
        free = np.setdiff1d(np.arange(lay["n_x"]), er)
        z, pz = ca.SX.sym("z", len(free)), ca.SX.sym("p", len(er))
        xf = ca.SX.zeros(lay["n_x"])
        for k, i in enumerate(free):
            xf[int(i)] = z[k]
        for k, i in enumerate(er):
            xf[int(i)] = pz[k]
        gz = ca.substitute(g, x, xf)
        t0 = time.time()
        rf = ca.rootfinder("g3n", "newton", {"x": z, "p": pz, "g": gz},
                           {"linear_solver": "csparse", "abstol": 1e-10, "max_iter": 50, "error_on_fail": False,
                            "print_iteration": True})
        t_setup = time.time() - t0
        t0 = time.time()
        zs = np.asarray(rf(x0[free], x0[er]), float).ravel()
        t_sol = time.time() - t0
        xs = x0.copy()
        xs[free] = zs
        res = np.abs(np.asarray(fn(xs)[0], float).ravel()[keep]) / sc[keep]
        st = rf.stats()
        print(f"default solve {t_def:.1f} s; lifted system {lay['n_x']} unknowns, built in {t_build:.1f} s; Newton set "
              f"up in {t_setup:.1f} s, {st.get('return_status')} in {st.get('iter_count')} iterations, {t_sol:.1f} s; "
              f"largest scaled residual {res.max():.2e}")
        _report(lay, xs, x_def)
        return
    opts = {"ipopt.print_level": 5, "print_time": False, "ipopt.tol": 1e-10, "ipopt.constr_viol_tol": 1e-10,
            "ipopt.max_iter": 200, "ipopt.linear_solver": "mumps"}
    if hess == "lbfgs":
        opts["ipopt.hessian_approximation"] = "limited-memory"
    for a in sys.argv[3:]:
        k, v = a.split("=", 1)
        try:
            v = int(v)
        except ValueError:
            try:
                v = float(v)
            except ValueError:
                pass
        opts[k] = v
    t0 = time.time()
    solver = ca.nlpsol("g3", "ipopt", {"x": x, "f": ca.SX(0.0), "g": g}, opts)
    t_setup = time.time() - t0
    t0 = time.time()
    sol = solver(x0=x0, lbx=lbx, ubx=ubx, lbg=0.0, ubg=0.0)
    t_sol = time.time() - t0
    st = solver.stats()
    xs = np.asarray(sol["x"], float).ravel()
    res = np.abs(np.asarray(sol["g"], float).ravel())
    print(f"default solve {t_def:.1f} s; lifted system {lay['n_x']} unknowns, built in {t_build:.1f} s; IPOPT set up "
          f"in {t_setup:.1f} s, {st['return_status']} in {st['iter_count']} iterations, {t_sol:.1f} s; largest scaled "
          f"residual {res.max():.2e} (start {np.max(np.abs(np.asarray(fn(x0)[0], float).ravel()[keep]) / sc[keep]):.2e})")
    tw = {k[7:]: round(float(v), 2) for k, v in st.items() if k.startswith("t_wall_") and float(v) > 0.01}
    print(f"  wall time by part (s): {tw}")
    _report(lay, xs, x_def)


def _report(lay, xs, x_def) -> None:
    rel = np.abs(xs - x_def) / np.maximum(np.abs(x_def), 1e-3)
    o, groups = 0, {}
    for name, n in lay["x"]:
        gname = name.split("_")[0] if name.startswith(("r_", "sB_", "sW_")) else name
        groups.setdefault(gname, []).append((o, n))
        o += n
    for gname, sl in groups.items():
        idx = np.concatenate([np.arange(a, a + n) for a, n in sl])
        print(f"  {gname}: largest difference from the default solve's {np.max(rel[idx]) if len(idx) else 0:.2e}")


if __name__ == "__main__":
    main()
