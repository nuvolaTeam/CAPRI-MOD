"""G3.3, first trial: Newton's method on the assembled market system (capri_mod/market/market_system_ad.py), from the
state a captured solve started from (the previous solve's equilibrium), against the default solve's equilibrium.

The Jacobian by forward differences over the unknowns of the square system (the empty balances out, their prices held;
G3_SYSTEM.md, G3.2e): CasADi's symbolic Jacobian of the substituted system did not fit in memory (it is 32% dense).
A damped Newton step with a backtracking line search on the largest scaled residual ("max", default) or its 2-norm
("l2"). Reports each step's residual and the equation where it is largest, then each unknown block's largest relative
difference from the default solve's equilibrium.

    python tools/check/g3_newton_trial.py runs/capture/market_011.pkl [max|l2]
"""
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

p = Path(sys.argv[1])
MERIT = sys.argv[2] if len(sys.argv) > 2 else "max"
rec = pickle.load(open(p, "rb"))
with override(rec["settings"].replace({"diagnostics.capture_market_dir": ""})):
    # the default solve, from a copy of the module as it was captured
    mm_d = load_module(rec["module"], p.parent / "blobs")
    t0 = time.time(); eq = mm_d.solve(**rec["args"]); t_def = time.time() - t0
    S1, D1, _, _, _ = mm_d._bilateral_eval(mm_d.sv.bilat_last_r.copy(), rec["args"]["exogenous_supply"], None)
    fn_d, lay_d, _, _ = market_system(mm_d, rec["args"]["exogenous_supply"])
    x_def = market_x0(mm_d, lay_d)
    # the system at the module as captured, before its solve: the start is its state (the previous solve's)
    mm = load_module(rec["module"], p.parent / "blobs")
    t0 = time.time()
    fn, lay, x, F = market_system(mm, rec["args"]["exogenous_supply"])
    t_build = time.time() - t0
    assert lay["x"] == lay_d["x"], "layouts differ"
    x0 = market_x0(mm, lay)
sc = _scales(mm, lay)
t0 = time.time(); F0 = np.asarray(fn(x0)[0], float).ravel(); t_F = time.time() - t0
print(f"default solve {t_def:.1f} s, converged {eq.converged}; system built in {t_build:.1f} s, F in {t_F*1000:.0f} ms; "
      f"start residual {np.max(np.abs(F0)/sc):.2e}")
sp = fn.jac_sparsity(0, 0)
er = set(np.nonzero(np.diff(np.asarray(sp.T.colind())) == 0)[0].tolist())
keep = np.array([i for i in range(sp.size1()) if i not in er])
fF = ca.Function("F", [x], [F])
def Fnum(v):
    return np.asarray(fF(v), float).ravel()
def jac_fd(v, F0):
    """Forward differences over the kept columns (the symbolic Jacobian does not fit in memory here)."""
    J = np.zeros((len(keep), len(keep)))
    for k, j in enumerate(keep):
        h = 1e-7 * max(abs(v[j]), 1e-2)
        w = v.copy(); w[j] += h
        J[:, k] = (Fnum(w)[keep] - F0[keep]) / h
    return J
xk = x0.copy()
for it in range(30):
    Fk = Fnum(xk)
    nk = np.max(np.abs(Fk[keep]) / sc[keep])
    wq = int(np.argmax(np.abs(Fk[keep]) / sc[keep]))
    eqn = [f"{n}[{k}]" for n, m in lay["eqs"] for k in range(m)][keep[wq]]
    print(f"  Newton {it}: residual {nk:.3e} ({eqn}), l2 {np.linalg.norm(Fk[keep] / sc[keep]):.3e}", flush=True)
    if nk < 1e-10:
        break
    t0 = time.time()
    Jk = jac_fd(xk, Fk)
    dx = np.linalg.solve(Jk, -Fk[keep])
    tj = time.time() - t0
    t = 1.0
    while True:
        xt = xk.copy(); xt[keep] += t * dx
        Ft = Fnum(xt)
        if (MERIT == "max" and np.max(np.abs(Ft[keep]) / sc[keep]) < nk) or \
           (MERIT == "l2" and np.linalg.norm(Ft[keep] / sc[keep]) < np.linalg.norm(Fk[keep] / sc[keep])) or t < 1e-4:
            break
        t *= 0.5
    xk = xt
    print(f"     step {t:g}, Jacobian + solve {tj:.1f} s", flush=True)
rel = np.abs(xk - x_def) / np.maximum(np.abs(x_def), 1e-3)
o = 0
groups = {}
for name, n in lay["x"]:
    g = name.split("_")[0] if name.startswith(("r_", "sB_", "sW_")) else name
    groups.setdefault(g, []).append((o, n)); o += n
for g, sl in groups.items():
    idx = np.concatenate([np.arange(a, a + n) for a, n in sl]) if sl else np.zeros(0, int)
    print(f"  {g}: largest difference from the default solve's {np.max(rel[idx]) if len(idx) else 0:.2e}")
