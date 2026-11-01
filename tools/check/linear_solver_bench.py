"""IPOPT's linear solvers compared on the model's own regional problems (supply.nlp_linear_solver, 29 October 2026).

The mini-EU run (tools/run/run_mini_eu.py's 20 units) runs as usual with MUMPS in one process; every regional IPOPT solve
(CapriRegionalNLP.solve) is repeated with each solver given, from the same start (x0 and, for a warm start, the same
multipliers) with the same options, and both are recorded: wall time of the IPOPT call, the part of it spent in
CasADi's function evaluations (objective, constraints, derivatives), iterations, status and objective. The run's
path follows MUMPS, so every pair is the same problem. SPRAL is bundled with CasADi; HSL solvers need their library (supply.nlp_hsllib; obtained
under HSL's licence and kept outside the repository).

    CAPRI_WORKERS=1 python tools/check/linear_solver_bench.py OUT.jsonl --solvers spral
    CAPRI_WORKERS=1 python tools/check/linear_solver_bench.py OUT.jsonl --solvers ma27 --hsllib /path/libhsl.so
    python tools/check/linear_solver_bench.py OUT.jsonl --summary

One process (CAPRI_WORKERS=1): forked workers would take their records with them.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

#: CasADi's per-function timing keys of an nlpsol's stats (the callbacks IPOPT makes)
CALLBACKS = ("nlp_f", "nlp_g", "nlp_grad", "nlp_grad_f", "nlp_jac_g", "nlp_hess_l")


def _callback_seconds(st):
    return float(sum(float(st.get(f"t_wall_{k}", 0.0) or 0.0) for k in CALLBACKS))


def run(out, solvers, hsllib):
    from capri_mod import settings as S
    from capri_mod.supply import capri_regional_nlp as C
    sys.path.insert(0, str(ROOT / "tools" / "run"))
    import run_f2f_2030
    from run_mini_eu import UNITS

    orig = C.CapriRegionalNLP.solve
    fh = open(out, "w")
    n = [0]

    def probe(self, x0, max_iter=None, tol=1e-8, print_level=0, lam=None):
        t0 = time.perf_counter()
        r = orig(self, x0, max_iter=max_iter, tol=tol, print_level=print_level, lam=lam)
        wall = time.perf_counter() - t0
        keep = (self._solver, self.build_s, self.solve_s)
        st = self._solver.stats()
        rec = {"i": n[0], "n_x": int(self.X.shape[0]), "n_g": int(self.g.shape[0]), "warm": r["warm"],
               "mumps": {"wall": wall, "solve": self.solve_s, "build": self.build_s, "callbacks": _callback_seconds(st),
                         "iter": r["iterations"], "status": r["status"], "f": r["f"]}}
        for ls in solvers:
            with S.override({"supply.nlp_linear_solver": ls, "supply.nlp_hsllib": hsllib}):
                t1 = time.perf_counter()
                r2 = orig(self, x0, max_iter=max_iter, tol=tol, print_level=print_level, lam=lam)
                w2 = time.perf_counter() - t1
                st2 = self._solver.stats()
                rec[ls] = {"wall": w2, "solve": self.solve_s, "build": self.build_s,
                           "callbacks": _callback_seconds(st2), "iter": r2["iterations"], "status": r2["status"],
                           "f": r2["f"], "dx": float(abs(r2["x"] - r["x"]).max()) if len(r["x"]) else 0.0}
        self._solver, self.build_s, self.solve_s = keep
        fh.write(json.dumps(rec) + "\n")
        n[0] += 1
        return r

    C.CapriRegionalNLP.solve = probe
    sys.argv = ["run_f2f_2030.py", str(Path(out).with_suffix(".pkl")), "--scenario", "f2f",
                "--regions", ",".join(UNITS)]
    try:
        run_f2f_2030.main()
    finally:
        C.CapriRegionalNLP.solve = orig
        fh.close()


def summary(out):
    import numpy as np
    recs = [json.loads(line) for line in open(out)]
    solvers = [k for k in recs[0] if k not in ("i", "n_x", "n_g", "warm", "mumps")]
    print(f"{len(recs)} regional solves ({sum(r['warm'] for r in recs)} warm-started); "
          f"columns {min(r['n_x'] for r in recs)}-{max(r['n_x'] for r in recs)}, "
          f"rows {min(r['n_g'] for r in recs)}-{max(r['n_g'] for r in recs)}")
    for ls in ["mumps"] + solvers:
        sol = np.array([r[ls]["solve"] for r in recs])
        cb = np.array([r[ls]["callbacks"] for r in recs])
        it = np.array([r[ls]["iter"] or 0 for r in recs])
        ok = sum(r[ls]["status"] in ("Solve_Succeeded", "Solved_To_Acceptable_Level") for r in recs)
        print(f"{ls:6s} IPOPT time {sol.sum():8.1f} s (function evaluations {cb.sum():7.1f} s, the rest "
              f"{sol.sum() - cb.sum():7.1f} s: IPOPT's own work, the linear solver in it); iterations {it.sum()}; "
              f"solved {ok}/{len(recs)}")
    for ls in solvers:
        df = np.array([abs(r[ls]["f"] - r["mumps"]["f"]) / max(1.0, abs(r["mumps"]["f"])) for r in recs])
        dx = np.array([r[ls]["dx"] for r in recs])
        st = sum(r[ls]["status"] != r["mumps"]["status"] for r in recs)
        better = sum(r[ls]["f"] < r["mumps"]["f"] - 1e-6 * max(1.0, abs(r["mumps"]["f"])) for r in recs)
        worse = sum(r[ls]["f"] > r["mumps"]["f"] + 1e-6 * max(1.0, abs(r["mumps"]["f"])) for r in recs)
        print(f"{ls} against mumps: objective relative difference median {np.median(df):.1e}, max {df.max():.1e}; "
              f"lower by > 1e-6: {better}, higher: {worse}; largest column difference {dx.max():.3g}; "
              f"status differs in {st}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--solvers", default="ma27")
    ap.add_argument("--hsllib", default="")
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    if a.summary:
        summary(a.out)
        return
    if os.environ.get("CAPRI_WORKERS", "") != "1":
        raise SystemExit("run with CAPRI_WORKERS=1 (one process)")
    run(a.out, [s.strip() for s in a.solvers.split(",") if s.strip()], a.hsllib)
    summary(a.out)


if __name__ == "__main__":
    main()
