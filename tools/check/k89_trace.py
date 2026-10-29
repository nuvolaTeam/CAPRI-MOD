"""KNOWN_ISSUES K89: where the regional solves that fail come from.

Runs the mini-EU Farm-to-Fork run (tools/run/run_mini_eu.py's units) in one process with every regional IPOPT solve
(CapriRegionalNLP.solve) recorded: the regional unit (RegionalSupplyModel.rid), the outer step (baseline or scenario,
iteration), the chain of supply-module functions and lines that asked for it (which fallback, check or start), the
start (warm or cold), IPOPT's status, iterations and seconds, and the objective. Diagnostic only: the run is the usual
one, nothing is changed.

    CAPRI_WORKERS=1 python tools/check/k89_trace.py OUT.jsonl [--scenario f2f|greendeal2030]
    python tools/check/k89_trace.py OUT.jsonl --summary

One process (CAPRI_WORKERS=1): forked workers would take their records with them.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
GOOD = ("Solve_Succeeded", "Solved_To_Acceptable_Level")


def _caller():
    """The regional unit and the supply module's call chain above this solve."""
    f = sys._getframe(2)
    chain, rid = [], None
    while f is not None:
        code = f.f_code
        if code.co_filename.endswith(os.path.join("supply", "supply_module.py")):
            chain.append(f"{code.co_name}:{f.f_lineno}")
            s = f.f_locals.get("self")
            if rid is None and s is not None and hasattr(s, "rid"):
                rid = s.rid
        f = f.f_back
    return rid, chain[:6]


def run(out, scenario):
    from capri_mod.supply import capri_regional_nlp as C
    sys.path.insert(0, str(ROOT / "tools" / "run"))
    import run_f2f_2030
    from run_mini_eu import UNITS

    orig = C.CapriRegionalNLP.solve
    fh = open(out, "w")

    def probe(self, x0, max_iter=None, tol=1e-8, print_level=0, lam=None):
        rid, chain = _caller()
        t0 = time.perf_counter()
        r = orig(self, x0, max_iter=max_iter, tol=tol, print_level=print_level, lam=lam)
        fh.write(json.dumps({"rid": rid, "chain": chain, "warm": r["warm"], "status": r["status"],
                             "iter": r["iterations"], "s": round(time.perf_counter() - t0, 4),
                             "f": r["f"], "max_iter": max_iter, "n_x": int(self.X.shape[0])}) + "\n")
        fh.flush()
        return r

    C.CapriRegionalNLP.solve = probe
    sys.argv = ["run_f2f_2030.py", str(Path(out).with_suffix(".pkl")), "--scenario", scenario,
                "--regions", ",".join(UNITS)]
    try:
        run_f2f_2030.main()
    finally:
        C.CapriRegionalNLP.solve = orig
        fh.close()


def summary(out):
    recs = [json.loads(line) for line in open(out)]
    fail = [r for r in recs if r["status"] not in GOOD]
    t_all, t_fail = sum(r["s"] for r in recs), sum(r["s"] for r in fail)
    print(f"{len(recs)} regional solves, {t_all:.1f} s; failed {len(fail)}, {t_fail:.1f} s "
          f"({100 * t_fail / max(t_all, 1e-9):.0f}%)")
    by = collections.defaultdict(lambda: [0, 0.0, collections.Counter()])
    for r in fail:
        k = (r["rid"], " < ".join(r["chain"][:3]), "warm" if r["warm"] else "cold")
        by[k][0] += 1
        by[k][1] += r["s"]
        by[k][2][r["status"]] += 1
    print("failed solves by unit, call chain (innermost first) and start:")
    for (rid, ch, w), (n, s, st) in sorted(by.items(), key=lambda kv: -kv[1][1]):
        print(f"  {rid} {w:4s} {n:3d} solves {s:7.1f} s  {dict(st)}  {ch}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--scenario", default="f2f")
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    if not a.summary:
        if os.environ.get("CAPRI_WORKERS", "") != "1":
            raise SystemExit("run with CAPRI_WORKERS=1 (one process)")
        run(a.out, a.scenario)
    summary(a.out)


if __name__ == "__main__":
    main()
