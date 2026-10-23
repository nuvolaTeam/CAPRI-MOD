"""Where a run spends its time and how the market solve behaves in each outer iteration.

python tools/check/trace_market.py OUT.pkl [run_f2f_2030.py options]

Wraps MarketModule.solve and MarketModule._solve_bilateral and SupplyModule.solve_all (whichever exist) with timers,
runs tools/run/run_f2f_2030.py unchanged, and prints per outer iteration: supply time, market time, bilateral market
steps, converged flag and final residual. A diagnostic only - the run itself is not changed.
"""
import runpy
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from capri_mod.market.market_module import MarketModule  # noqa: E402
from capri_mod.supply import supply_module as sm  # noqa: E402

LOG = []
_t = {"supply": 0.0}


def _wrap(cls, name, tag):
    f = getattr(cls, name, None)
    if f is None:
        return

    def g(self, *a, **k):
        t0 = time.time()
        out = f(self, *a, **k)
        dt = time.time() - t0
        rec = {"tag": tag, "s": dt}
        if tag == "bilateral":
            rec.update(steps=out[6], conv=bool(out[5]), err=float(getattr(self, "_bilat_err", float("nan"))),
                       worst=max(getattr(self, "_bilat_errs", {"-": 0}).items(), key=lambda kv: kv[1])[0])
        LOG.append(rec)
        return out
    setattr(cls, name, g)


_wrap(MarketModule, "solve", "market")
_wrap(MarketModule, "_solve_bilateral", "bilateral")
for nm in ("solve_all", "solve_regions", "run"):
    if hasattr(sm.SupplyModule, nm):
        _wrap(sm.SupplyModule, nm, "supply")
        break

sys.argv = [str(ROOT / "tools" / "run" / "run_f2f_2030.py")] + sys.argv[1:]
t_start = time.time()
try:
    runpy.run_path(sys.argv[0], run_name="__main__")
finally:
    print("\n== trace ==")
    tot = {}
    for r in LOG:
        tot[r["tag"]] = tot.get(r["tag"], 0.0) + r["s"]
        if r["tag"] == "bilateral":
            print(f"  market: {r['s']:6.1f} s  steps {r['steps']:3d}  converged {r['conv']}  max rel resid {r['err']:.1e} ({r['worst']})")
        elif r["tag"] == "supply":
            print(f"  supply: {r['s']:6.1f} s")
    print("totals:", {k: round(v, 1) for k, v in tot.items()}, "wall", round(time.time() - t_start, 1))
