"""Shadow trial: CAPRI's original NLP solved with IPOPT next to every regional conic solve of a full run.

python tools/check/nlp_check/shadow.py OUT.csv   (writes OUT.<pid>.csv per worker process) [run_f2f_2030.py options]

Every call of solve_regional_conic during the run is also written in CAPRI's form (tools/check/nlp_check/nlp.py RegionNLP:
exact ammonia loss cascade, one regional share per fertiliser technology, inhibitor share x manure N; feeding in total
form, since CAPRI's per-head form fails in IPOPT from most starts - docs/archive/NLP_CHECK.md) and solved with IPOPT, warm
started as CAPRI does: from the region's previous NLP solution when the problem has the same shape, else from the
calibrated base point (herds, base rations, base option shares). The run itself follows the conic model unchanged.

Env: NLP_SHADOW_FEED=perhead for CAPRI's literal feeding; NLP_SHADOW_REGIONS=IE05,NL22 to limit the regions.

One row per solve: region, call number, conic status and time, NLP build and solve time, IPOPT status and
iterations, constraint violation, objective gap (NLP optimum - conic point in CAPRI's form, relative), largest
activity difference (relative, activities > 1 unit) and the N price both ways.
"""
import csv
import os
import runpy
import sys
import time
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check", "check/nlp_check")]
OUT = Path(sys.argv[1])
FEED = os.environ.get("NLP_SHADOW_FEED", "total")
REGS = set(filter(None, os.environ.get("NLP_SHADOW_REGIONS", "").split(",")))

from capri_mod.supply import feed_conic as fc            # noqa: E402
from capri_mod.supply import supply_module as sm          # noqa: E402
from nlp import RegionNLP                                 # noqa: E402

_orig_solve = fc.solve_regional_conic
_orig_fcs = sm.RegionalSupplyModel._feed_conic_solve
_CUR = {}
_PREV = {}          # region -> (shape, x) of the last NLP solution
_N = {}
FIELDS = ["region", "call", "techs", "conic_status", "conic_s", "nlp_build_s", "nlp_solve_s", "ipopt_status",
          "ipopt_iter", "start", "violation", "obj_gap_rel", "max_act_diff_rel", "act_worst", "nprice_conic",
          "nprice_nlp"]
_FH = {}


def _writer():
    """one file per process (the run's workers are forked): OUT.<pid>.csv; merge them afterwards"""
    pid = os.getpid()
    if pid not in _FH:
        f = open(OUT.with_suffix(f".{pid}.csv"), "w", newline="")
        w = csv.writer(f); w.writerow(FIELDS)
        _FH[pid] = (f, w)
    return _FH[pid]


def _amm(m):
    ctx = m._amm_context()
    if ctx is None:
        return None
    techs, man_d, nh3, sub = ctx
    return {"subs": techs, "man_d": dict(man_d), "nh3": dict(nh3), "sub": sub,
            "sc": {a_: m._amm_scale(subs, float(man_d.get(a_, 0.0) or 0.0), float(nh3.get(a_, 0.0) or 0.0))
                   for a_, subs in techs.items() if float(man_d.get(a_, 0.0) or 0.0) > 0
                   and float(nh3.get(a_, 0.0) or 0.0) > 0}}


def _base_point(P, cap):
    n0, nf, nt, nphi, nm = P.sizes
    x = np.zeros(n0 + nf + nt + nphi + nm + P.n_t)
    x[:n0] = np.maximum(np.asarray(cap["kwargs"]["x_base"], float)[:n0], 0.0) / P.sc[:n0]
    x[n0:n0 + nf] = 1.0
    x[n0 + nf:n0 + nf + nt] = [t["s0"] for t in P.techs]
    if P.n_t:
        x[len(x) - P.n_t:] = 1.0
    return x


def solve_hook(*a, **k):
    t0 = time.time()
    out = _orig_solve(*a, **k)
    t_conic = time.time() - t0
    m = _CUR.get("model")
    if m is None:
        return out
    reg = m.data.region_id
    _N[reg] = _N.get(reg, 0) + 1
    row = {"region": reg, "call": _N[reg], "techs": int(bool(k.get("techs") or k.get("fert") or k.get("mni"))),
           "conic_status": out[3].get("status"), "conic_s": round(t_conic, 4)}
    try:
        cap = dict(args=a, kwargs=k, out=out, amm=_amm(m) if k.get("techs") else None)
        t1 = time.time()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            P = RegionNLP(cap, uniform_fert=True, cascade="exact", feed=FEED)
        row["nlp_build_s"] = round(time.time() - t1, 4)
        shape = (P.sizes, P.n_t, tuple(P.acts))
        prev = _PREV.get(reg)
        if prev is not None and prev[0] == shape:
            x0, row["start"] = prev[1], "previous"
        else:
            x0, row["start"] = _base_point(P, cap), "base"
        t2 = time.time()
        x, f, lam, st, it = P.solve(np.clip(x0, P.lbx, P.ubx))
        row["nlp_solve_s"] = round(time.time() - t2, 4)
        row["ipopt_status"], row["ipopt_iter"] = st, it
        v, _ = P.violation(x)
        row["violation"] = f"{v:.2e}"
        ok = st in ("Solve_Succeeded", "Solved_To_Acceptable_Level")
        if ok:
            _PREV[reg] = (shape, x)
        if out[3].get("status") in ("Solved", "AlmostSolved", "Solved (IPOPT polish)"):
            xc = P.from_conic()
            fc_obj = float(P.f_obj(xc))
            row["obj_gap_rel"] = f"{(f - fc_obj) / max(abs(fc_obj), 1.0):+.2e}"
            yb = np.asarray(P.f_y(x)).ravel(); yc = np.asarray(P.f_y(xc)).ravel()
            dd = [(abs(yb[i] - yc[i]) / max(abs(yc[i]), 1.0), P.acts[i]) for i in range(len(P.acts))
                  if max(abs(yc[i]), abs(yb[i])) > 1.0]
            if dd:
                worst = max(dd)
                row["max_act_diff_rel"], row["act_worst"] = f"{worst[0]:.2e}", worst[1]
            if P.n_row is not None and P.n_row in P.row_index:
                row["nprice_conic"] = f"{float(out[2][P.n_row]):.3f}"
                row["nprice_nlp"] = f"{float(lam[P.row_index[P.n_row]]):.3f}"
    except Exception as exc:                               # a failed shadow solve is a finding, not a crash
        row["ipopt_status"] = f"error: {exc!r}"[:120]
    f_, w_ = _writer(); w_.writerow([row.get(f, "") for f in FIELDS]); f_.flush()
    return out


def fcs_hook(self, *a, **k):
    if REGS and self.data.region_id not in REGS:
        return _orig_fcs(self, *a, **k)
    _CUR["model"] = self
    try:
        return _orig_fcs(self, *a, **k)
    finally:
        _CUR.clear()


fc.solve_regional_conic = solve_hook
sm.RegionalSupplyModel._feed_conic_solve = fcs_hook
sys.argv = ["run_f2f_2030.py"] + sys.argv[2:]
runpy.run_path(str(ROOT / "tools" / "run" / "run_f2f_2030.py"), run_name="__main__")
