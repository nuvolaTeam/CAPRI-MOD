"""SPRAL's OpenMP threads on the model's own regional problems (supply.nlp_ipopt_library, supply.nlp_omp_threads;
register BEYOND-11; 31 October 2026).

The mini-EU Farm-to-Fork run (tools/run/run_mini_eu.py's 20 units) runs in one process with the IPOPT library given
(IPOPT with SPRAL in OpenMP, tools/solvers/build_ipopt_spral_omp.py) and SPRAL on the run's threads; every regional IPOPT
solve (CapriRegionalNLP.solve) is repeated with each thread count given, from the same start (x0 and, for a warm start,
the same multipliers) with the same options, and both are recorded: wall time of the IPOPT call, the part of it spent
in CasADi's function evaluations, iterations, status and objective. The run's path follows the run's thread count, so
every pair is the same problem. The comparison with MUMPS is tools/check/linear_solver_bench.py's (CasADi's IPOPT:
MUMPS and SPRAL on one thread), which cannot run in this process (this library has no MUMPS).

    CAPRI_WORKERS=1 python tools/check/omp_threads_bench.py OUT.jsonl --library PATH/libipopt.so.3 --threads 2
    python tools/check/omp_threads_bench.py OUT.jsonl --summary

One process (CAPRI_WORKERS=1): forked workers would take their records with them. A speed-up needs cores free for the
threads: on a machine with as many cores as workers there are none.
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


def run(out, library, threads):
    from capri_mod import settings as S
    from capri_mod.supply import capri_regional_nlp as C
    from capri_mod.supply import ipopt_library as IL
    sys.path.insert(0, str(ROOT / "tools" / "run"))
    import run_f2f_2030
    from run_mini_eu import UNITS

    orig = C.CapriRegionalNLP.solve
    fh = open(out, "w")
    n = [0]

    def probe(self, x0, max_iter=None, tol=1e-8, print_level=0, lam=None):
        t_run = IL.threads()
        t0 = time.perf_counter()
        r = orig(self, x0, max_iter=max_iter, tol=tol, print_level=print_level, lam=lam)
        wall = time.perf_counter() - t0
        keep = (self._solver, self.build_s, self.solve_s)
        st = self._solver.stats()
        rec = {"i": n[0], "n_x": int(self.X.shape[0]), "n_g": int(self.g.shape[0]), "warm": r["warm"],
               "base": t_run,
               str(t_run): {"wall": wall, "solve": self.solve_s, "callbacks": _callback_seconds(st),
                            "iter": r["iterations"], "status": r["status"], "f": r["f"]}}
        for t in threads:
            IL.set_threads(t)
            t1 = time.perf_counter()
            r2 = orig(self, x0, max_iter=max_iter, tol=tol, print_level=print_level, lam=lam)
            w2 = time.perf_counter() - t1
            st2 = self._solver.stats()
            rec[str(t)] = {"wall": w2, "solve": self.solve_s, "callbacks": _callback_seconds(st2),
                           "iter": r2["iterations"], "status": r2["status"], "f": r2["f"],
                           "dx": float(abs(r2["x"] - r["x"]).max()) if len(r["x"]) else 0.0}
        IL.set_threads(t_run)
        self._solver, self.build_s, self.solve_s = keep
        fh.write(json.dumps(rec) + "\n")
        n[0] += 1
        return r

    C.CapriRegionalNLP.solve = probe
    sys.argv = ["run_f2f_2030.py", str(Path(out).with_suffix(".pkl")), "--scenario", "f2f",
                "--regions", ",".join(UNITS), "--set", f"supply.nlp_ipopt_library={json.dumps(str(library))}",
                "--set", 'supply.nlp_linear_solver="spral"']
    try:
        run_f2f_2030.main()
    finally:
        C.CapriRegionalNLP.solve = orig
        fh.close()


def summary(out):
    import numpy as np
    recs = [json.loads(line) for line in open(out)]
    base = str(recs[0]["base"])
    others = [k for k in recs[0] if k not in ("i", "n_x", "n_g", "warm", "base", base)]
    print(f"{len(recs)} regional solves ({sum(r['warm'] for r in recs)} warm-started); "
          f"columns {min(r['n_x'] for r in recs)}-{max(r['n_x'] for r in recs)}, "
          f"rows {min(r['n_g'] for r in recs)}-{max(r['n_g'] for r in recs)}")
    for k in [base] + others:
        sol = np.array([r[k]["solve"] for r in recs])
        cb = np.array([r[k]["callbacks"] for r in recs])
        it = np.array([r[k]["iter"] or 0 for r in recs])
        ok = sum(r[k]["status"] in ("Solve_Succeeded", "Solved_To_Acceptable_Level") for r in recs)
        print(f"{k} thread(s): IPOPT time {sol.sum():8.1f} s (function evaluations {cb.sum():7.1f} s, the rest "
              f"{sol.sum() - cb.sum():7.1f} s: IPOPT's own work, the linear solver in it); iterations {it.sum()}; "
              f"solved {ok}/{len(recs)}")
    for k in others:
        ratio = np.array([r[k]["solve"] / r[base]["solve"] for r in recs if r[base]["solve"] > 0])
        df = np.array([abs(r[k]["f"] - r[base]["f"]) / max(1.0, abs(r[base]["f"])) for r in recs])
        st = sum(r[k]["status"] != r[base]["status"] for r in recs)
        print(f"{k} against {base} thread(s): time per solve median ratio {np.median(ratio):.2f}; objective relative "
              f"difference median {np.median(df):.1e}, max {df.max():.1e}; largest column difference "
              f"{max(r[k]['dx'] for r in recs):.3g}; status differs in {st}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--library", default="")
    ap.add_argument("--threads", default="2", help="thread counts to repeat each solve with, e.g. 2 or 2,4")
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    if a.summary:
        summary(a.out)
        return
    if os.environ.get("CAPRI_WORKERS", "") != "1":
        raise SystemExit("run with CAPRI_WORKERS=1 (one process)")
    if not a.library:
        raise SystemExit("--library: the IPOPT library with SPRAL in OpenMP")
    run(a.out, a.library, [int(t) for t in a.threads.split(",") if t.strip()])
    summary(a.out)


if __name__ == "__main__":
    main()
