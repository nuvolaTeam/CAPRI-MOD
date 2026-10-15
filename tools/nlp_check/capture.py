"""Capture the regional conic problems of a converged run for the NLP check.

python tools/nlp_check/capture.py OUTDIR [run_f2f_2030.py options...]
Runs tools/run_f2f_2030.py with a hook: for the regions in NLP_REGIONS (default IE05,NL22,FRH0,DE94,BE21), the last
call of solve_regional_conic that carries CAPRI's technologies (the scenario's final solve) is saved with its inputs,
its solution and the ammonia data of the region (OUTDIR/<region>.pkl).
"""
import os
import pickle
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
REGS = set(os.environ.get("NLP_REGIONS", "IE05,NL22,FRH0,DE94,BE21").split(","))

from capri_mod.supply import feed_conic as fc            # noqa: E402
from capri_mod.supply import supply_module as sm          # noqa: E402

_orig_solve = fc.solve_regional_conic
_orig_fcs = sm.RegionalSupplyModel._feed_conic_solve
_CUR = {}


def solve_hook(*a, **k):
    out = _orig_solve(*a, **k)
    m = _CUR.get("model")
    if m is not None and (k.get("techs") or k.get("fert") or k.get("mni")):
        ctx = m._amm_context()
        amm = None
        if ctx is not None:
            techs, man_d, nh3, sub = ctx
            amm = {"subs": techs, "man_d": dict(man_d), "nh3": dict(nh3), "sub": sub,
                   "sc": {a_: m._amm_scale(subs, float(man_d.get(a_, 0.0) or 0.0), float(nh3.get(a_, 0.0) or 0.0))
                          for a_, subs in techs.items() if float(man_d.get(a_, 0.0) or 0.0) > 0
                          and float(nh3.get(a_, 0.0) or 0.0) > 0},
                   "last": dict(getattr(m, "_amm_last", None) or {})}
        _CUR["saved"] = dict(args=a, kwargs=k, out=out, amm=amm, region=m.data.region_id,
                             tax=float(getattr(m, "ghg_tax", 0.0) or 0.0))
    return out


def fcs_hook(self, *a, **k):
    if self.data.region_id not in REGS:
        return _orig_fcs(self, *a, **k)
    _CUR.clear(); _CUR["model"] = self
    try:
        return _orig_fcs(self, *a, **k)
    finally:
        if "saved" in _CUR:
            pickle.dump(_CUR["saved"], open(OUT / f"{self.data.region_id}.pkl", "wb"))
        _CUR.clear()


if os.environ.get("NLP_SUBSET"):
    # diagnostics only: solve just these regions (the market does not converge on a handful of regions)
    from capri_mod.projection import projection_module as _pm
    _run = _pm.ProjectionModule.run

    def _run_subset(self, *a, **k):
        k.setdefault("regions", os.environ["NLP_SUBSET"].split(","))
        return _run(self, *a, **k)
    _pm.ProjectionModule.run = _run_subset
fc.solve_regional_conic = solve_hook
sm.RegionalSupplyModel._feed_conic_solve = fcs_hook
sys.argv = ["run_f2f_2030.py"] + sys.argv[2:]
runpy.run_path(str(ROOT / "tools" / "run_f2f_2030.py"), run_name="__main__")
