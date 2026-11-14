"""G3.3, the solver battery: the market system's methods (capri_mod/market/market_g3.py) against the fixed point on a
set of supply shocks from the market solved at CAPRI's base supply rows.

For each shock (the supply models' rows scaled, below): the fixed point solves it from the solved base (its time and
iterations, and its equilibrium); the lifted system is built once at the base's state, and each method solves it from
the same start: "newton" (Newton at CAPRI's slope), "continuation" (Newton at market.g3_slope_steps then CAPRI's), "ipopt",
"auto" (the default chain). A method may carry variants after a colon, joined by +: dogleg or linesearch
(market.g3_newton_step), a linear solver (market.g3_linear_solver for Newton: pardiso, mumps, ma28; for ipopt
market.g3_ipopt_linear_solver: mumps, ma27, ma57, ma77, ma86, ma97), e.g. newton:dogleg+ma28, ipopt:ma57. Reported per
method: converged or not, time, and the largest relative difference of the
bilateral prices from the fixed point's equilibrium. The linear solver is market.g3_linear_solver (--set to change).

    python tools/check/g3_solver_battery.py [--shocks NAME,...] [--methods M[:VARIANT],...] [--set key=value ...]
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

CEREALS = ("SWHE", "DWHE", "RYEM", "BARL", "OATS", "MAIZ", "OCER")
ANIMALS = ("BEEF", "PORK", "SGMT", "POUM", "EGGS", "MILK")
SHOCKS = {
    "wheat+5": {"SWHE": 1.05},
    "wheat-20": {"SWHE": 0.80},
    "milk+10": {"MILK": 1.10},
    "beef-10": {"BEEF": 0.90},
    "cereals-10": {c: 0.90 for c in CEREALS},
    "pork-15": {"PORK": 0.85},
    "f2f-like": {**{c: 0.90 for c in CEREALS}, **{c: 0.90 for c in ANIMALS}},
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shocks", default=",".join(SHOCKS))
    ap.add_argument("--methods", default="newton,continuation,ipopt,auto")
    ap.add_argument("--set", action="append", default=[])
    a = ap.parse_args()
    from capri_mod.data.loaders import load_all_data
    from capri_mod.market.market_module import MarketModule
    from capri_mod.market.market_g3 import build, solve
    from capri_mod.settings import override
    sets = {}
    for kv in a.set:
        k, v = kv.split("=", 1)
        sets[k] = v
    with override(sets):
        mm = MarketModule(load_all_data(ROOT / "capri_data"))
        exo = mm.capri_base_supply_rows()
        assert mm.solve(exogenous_supply=exo).converged
        base = pickle.dumps(mm)
        for name in a.shocks.split(","):
            exo2 = exo.copy()
            for c, f in SHOCKS[name].items():
                if c in exo2.columns:
                    exo2[c] = exo2[c] * f
            m_fp = pickle.loads(base)
            t0 = time.time()
            e = m_fp.solve(exogenous_supply=exo2)
            t_fp = time.time() - t0
            r_fp = m_fp.sv.bilat_last_r
            m = pickle.loads(base)
            ctx = build(m, m.sv.bilat_last_r.copy(), exo2, None)
            lay = ctx["lay"]
            cols = list(m.par.bilat)
            ref = np.concatenate([r_fp[c].reindex(list(m.par.bilat[c].regions)).to_numpy(dtype=float) for c in cols])
            nr = len(ref)
            print(f"{name}: fixed point {'converged' if e.converged else 'NOT converged'} in {e.iterations} "
                  f"iterations, {t_fp:.1f} s; system built in {ctx['built']:.1f} s", flush=True)
            for spec in a.methods.split(","):
                meth, _, var = spec.partition(":")
                extra = {}
                for v in filter(None, var.split("+")):
                    if v in ("linesearch", "dogleg"):
                        extra["market.g3_newton_step"] = v
                    elif meth == "ipopt":
                        extra["market.g3_ipopt_linear_solver"] = v
                    else:
                        extra["market.g3_linear_solver"] = v
                t0 = time.time()
                with override(extra):
                    xs, ok, msg = solve(ctx, meth)
                t = time.time() - t0
                d = float(np.max(np.abs(xs[:nr] - ref) / np.maximum(np.abs(ref), 1e-3)))
                print(f"   {spec:20s} {'ok ' if ok else 'FAIL'} {t:7.1f} s  prices within {d:.1e}  ({msg})",
                      flush=True)
            del lay


if __name__ == "__main__":
    main()
