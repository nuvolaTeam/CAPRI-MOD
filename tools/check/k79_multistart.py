"""K79: does a region's regional problem have more than one local optimum, and which one is lower?

A run with the environment variable CAPRI_NLP_DUMP=DIR writes, at every regional solve, the region's NLP (its spec, the
start columns and the column labels) to DIR/<region>.pkl; the file left at the end of a run is the region's problem at
the run's last iteration. This tool solves that problem with IPOPT from the run's own start and from the activity
levels other runs ended at (their act_regional), and prints each start's status, objective and the activities that
differ. The lowest objective is the better local optimum of that problem (the regional model minimises).

    CAPRI_NLP_DUMP=DUMP_DIR python tools/run/run_f2f_2030.py OUT.pkl      (the run whose last problem is taken)
    python tools/check/k79_multistart.py DUMP_DIR FR820000 r194_f2f_gate9.pkl r196_f2f_gate10.pkl [--tol 1e-10]

Diagnostic only: the run's results are not changed by the dump.
"""
from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dump_dir", type=Path)
    ap.add_argument("region")
    ap.add_argument("runs", nargs="*", type=Path, help="run pickles whose scenario levels are tried as starts")
    ap.add_argument("--tol", type=float, default=1e-10)
    ap.add_argument("--show", type=float, default=0.5, help="print activities differing by more than this (1000 ha/head)")
    a = ap.parse_args()
    from capri_mod.supply.capri_regional_nlp import CapriRegionalNLP
    d = pickle.load(open(a.dump_dir / f"{a.region}.pkl", "rb"))
    nlp = CapriRegionalNLP(d["spec"])
    cols = list(d["cols"])
    y0 = np.asarray(d["x_start"], float)
    starts = [("dump start", nlp.start(y0))]
    for p in a.runs:
        lev = pickle.load(open(p, "rb"))["act_regional"][1].get(a.region) or {}
        y = y0.copy()
        n = 0
        for j, c in enumerate(cols[:len(y)]):
            if c in lev:
                y[j] = float(lev[c]); n += 1
        starts.append((f"{p.name} ({n} levels)", nlp.start(y)))
    out = []
    for name, xs in starts:
        res = nlp.solve(xs, tol=a.tol)
        yv = np.asarray(nlp.outputs(res)[0], float)
        out.append((name, res["status"], float(res["f"]), int(res["iterations"] or 0), yv))
        print(f"{name:40s} {res['status']:28s} f = {float(res['f']):.10g}  ({int(res['iterations'] or 0)} iterations)")
    best = min(out, key=lambda t: t[2])
    print(f"lowest objective: {best[0]}")
    ref = out[0][4]
    for name, _, f, _, yv in out[1:]:
        diff = [(c, ref[j], yv[j]) for j, c in enumerate(cols[:len(yv)]) if abs(yv[j] - ref[j]) > a.show]
        print(f"{name}: f - f(dump start) = {f - out[0][2]:+.6g}; levels differing: "
              + ", ".join(f"{c} {u:.2f} -> {v:.2f}" for c, u, v in diff[:20]))


if __name__ == "__main__":
    main()
