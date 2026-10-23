"""Compare the built-in QP solver with Clarabel on full model runs.

Runs the full-EU baseline and Farm-to-Fork (2017 base) once with
the setting supply.qp_solver = "builtin" and once with "clarabel", EACH IN ITS OWN PROCESS
(two model instances in one process are not bit-reproducible: a known small
leak of state, ~5e-6 relative), then compares every region's activity levels,
the market prices and the environmental totals, and reports run times.

The regional problems are strictly convex with unique optima, so the two solvers
must agree to solver tolerance. Requires `pip install clarabel`.

Usage:  python tools/check/compare_qp_solvers.py            (from the capri-mod folder)
Output: printed summary and capri_data/validation/qp_solver_comparison.csv
"""
import json, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHILD = r'''
import sys, json, time, warnings
warnings.simplefilter("ignore")
sys.path.insert(0, {root!r})
import capri_mod.supply.qp_solver as QPS
from capri_mod.model import CAPRIModel
from capri_mod.policy.greendeal import greendeal_scenario
from capri_mod import settings as _S
_S.activate(_S.current().replace({{"supply.qp_solver": {backend!r}}}))
m = CAPRIModel(data_dir={data!r}, verbose=False)
t = time.time(); b = m.run(scenario="BASELINE"); s = m.run(custom_scenario=greendeal_scenario())
out = {{"time": time.time() - t, "backend_used": _S.current().get("supply.qp_solver"),
       "act": {{r: {{k: float(v) for k, v in res.activities.items()}} for r, res in s["supply"].items()}},
       "prices": {{k: float(v) for k, v in s["market"].world_prices.items()}} if hasattr(s["market"], "world_prices") else {{}},
       "env": {{c: float(s["environmental"][c].sum()) for c in ("n_surplus", "nh3_total", "ghg_enteric") if c in s["environmental"]}},
       "converged": bool(s["metadata"].get("outer_converged")), "iterations": s["metadata"].get("n_outer_iterations")}}
json.dump(out, open({path!r}, "w"))
'''


def run(backend):
    path = tempfile.mktemp(suffix=f"_{backend}.json")
    code = CHILD.format(root=str(ROOT), data=str(ROOT / "capri_data"), backend=backend, path=path)
    subprocess.run([sys.executable, "-c", code], check=True)
    return json.load(open(path))


def main():
    try:
        import clarabel  # noqa: F401
    except ImportError:
        print("Clarabel is not installed: pip install clarabel"); return 1
    res = {b: run(b) for b in ("builtin", "clarabel")}
    a, c = res["builtin"], res["clarabel"]
    rows, worst = [], (0.0, None)
    for r in a["act"]:
        for k, v in a["act"][r].items():
            w = c["act"].get(r, {}).get(k)
            if w is None:
                continue
            d = abs(v - w) / max(1.0, abs(v))
            rows.append((r, k, v, w, d))
            if d > worst[0]:
                worst = (d, (r, k, v, w))
    import csv
    _out = Path(__file__).resolve().parents[2] / "capri_data" / "validation" / "qp_solver_comparison.csv"
    with open(_out, "w", newline="") as f:
        wr = csv.writer(f); wr.writerow(["region", "activity", "builtin", "clarabel", "rel_diff"]); wr.writerows(rows)
    dp = max((abs(a["prices"][k] - c["prices"].get(k, a["prices"][k])) / max(1e-9, abs(a["prices"][k])) for k in a["prices"]), default=0.0)
    print(f"run time: builtin {a['time']:.0f} s | clarabel {c['time']:.0f} s")
    print(f"converged: builtin {a['converged']} ({a['iterations']} it.) | clarabel {c['converged']} ({c['iterations']} it.)")
    print(f"activity levels: {len(rows)} compared, largest relative difference {worst[0]:.2e} at {worst[1]}")
    print(f"world prices: largest relative difference {dp:.2e}")
    for k in a["env"]:
        print(f"{k}: builtin {a['env'][k]:.1f} | clarabel {c['env'].get(k, float('nan')):.1f}")
    print(f"details: {_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
