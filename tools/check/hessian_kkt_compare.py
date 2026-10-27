"""Hessian option 4, feasibility check: the regional models' response to each market price from their optimality
conditions (CapriRegionalNLP.response: one factorisation at the base optimum) against re-solving the region (CAPRI's
calibrate_supply.gms re-solves; model._market_supply_hessian).

For a subset run's baseline, at the state the market supply Hessian starts from, per region and shocked price:
  - the shocked problem is built but not solved, and compared with the base problem part by part: the response from
    the optimality conditions is exact to first order only where the shock changes the objective's linear terms (c)
    and nothing else (not the feed prices, rows, bounds or curvature);
  - the re-solve: the region solved at the shocked price from the base state (as the Hessian measurement does);
  - the response: dy = response(base optimum, delta c) for the columns.
Prints per region: shocks that reach it, of these the ones that change c only, and the agreement of dy (KKT) with the
re-solved change of the activity levels (relative to the change's size). Differences are expected where the region's
solve has loops around the NLP (N price, manure pools, land market rents) or where the price changes more than c.

    python tools/check/hessian_kkt_compare.py [--regions DE110000,ES610000,...]
"""
from __future__ import annotations

import argparse
import copy
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


class _Stop(BaseException):
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regions", default="DE110000,ES610000,IR010000,NL220000,NO080000")
    ap.add_argument("--products", default="", help="comma-separated subset of the shocked prices (default: all)")
    a = ap.parse_args()
    regs = a.regions.split(",")
    os.environ.setdefault("CAPRI_WORKERS", "1")
    from capri_mod.model import CAPRIModel
    from capri_mod.supply import capri_regional_nlp as crn
    from capri_mod.supply.supply_module import RegionalSupplyModel

    captured = {}
    orig_fp = crn.problem_fingerprint
    last_solve = {}
    orig_solve = crn.CapriRegionalNLP.solve

    def fp_spy(spec, kw, opts):
        if "x_start" in kw:                                  # the early probe: before the build
            captured["spec"] = spec
        return orig_fp(spec, kw, opts)

    def solve_spy(self, x0, **kw):
        r = orig_solve(self, x0, **kw)
        last_solve["nlp"], last_solve["res"] = self, r
        return r

    crn.problem_fingerprint = fp_spy
    crn.CapriRegionalNLP.solve = solve_spy
    report = []

    def compare(self, price_signal, supply_results, regions):
        sm = self.supply_module
        pol = dict(getattr(self, "_last_spol", {}) or {})
        sig0 = price_signal.copy()
        keys = lambda mo: [k for k in mo.__dict__ if (k.startswith("_nlp") and k != "_nlp_times")
                           or k in RegionalSupplyModel.SOLVE_STATE]
        snap = {r: {k: copy.deepcopy(mo.__dict__[k]) for k in keys(mo)} for r, mo in sm._models.items()}
        par = {n: copy.deepcopy(sm.__dict__.get(n)) for n in sm._PAR_STATE}

        def restore():
            for r, mo in sm._models.items():
                for k in [k for k in keys(mo) if k not in snap[r]]:
                    del mo.__dict__[k]
                mo.__dict__.update({k: copy.deepcopy(v) for k, v in snap[r].items()})
            for n, v in par.items():
                sm.__dict__.pop(n, None) if v is None else sm.__dict__.__setitem__(n, copy.deepcopy(v))

        def solve(sig, r):
            sm.feed_bulk_ratio = self.feed_bulk_price_ratios(sig)
            restore()
            return sm.run(price_signals=sig, policy_scenario=pol, regions=[r], verbose=False)[r]

        def build_only(sig, r):
            sm.feed_bulk_ratio = self.feed_bulk_price_ratios(sig)
            restore()
            captured.pop("spec", None)

            def stop(_fp):
                raise _Stop()
            crn.SOLVE_PROBE = stop
            try:
                sm.run(price_signals=sig, policy_scenario=pol, regions=[r], verbose=False)
            except _Stop:
                pass
            finally:
                crn.SOLVE_PROBE = None
            return captured.get("spec")

        prods = [p for p in sig0.index if not a.products or p in a.products.split(",")]
        dr_of = {p: self.MARKET_SUPPLY_SHOCK * (1.0 + float(sig0.get(p, 0.0))) for p in prods}
        for r in regions:
            base_spec = build_only(sig0, r)
            last_solve.clear()
            res0 = solve(sig0, r)
            nlp0, opt0 = last_solve.get("nlp"), last_solve.get("res")
            if base_spec is None or nlp0 is None:
                print(f"{r}: no NLP solve captured")
                continue
            acts = list(base_spec["acts"])
            y0 = np.array([float(res0.activities.get(x, 0.0)) for x in acts])
            reach = conly = 0
            errs, worst = [], (0.0, None)
            for p in prods:
                sig = sig0.copy()
                sig[p] = float(sig0.get(p, 0.0)) + dr_of[p]
                if p == "SUGR" and "SUGB" in sig.index:
                    sig["SUGB"] = sig["SUGR"]
                if p == "SWHE" and "DWHE" in sig.index:
                    sig["DWHE"] = sig["SWHE"]
                spec = build_only(sig, r)
                if spec is None:
                    continue
                diff = [k for k in set(spec) | set(base_spec)
                        if crn.problem_fingerprint(spec.get(k), {}, {}) != crn.problem_fingerprint(base_spec.get(k), {}, {})]
                if not diff:
                    continue
                reach += 1
                if diff != ["c"]:
                    continue
                conly += 1
                dc = np.asarray(spec["c"], float) - np.asarray(base_spec["c"], float)
                dy = nlp0.response(opt0, dc[:, None])[:, 0]
                y1 = np.array([float(solve(sig, r).activities.get(x, 0.0)) for x in acts])
                d_res = y1 - y0
                scale = max(float(np.abs(d_res).max()), 1e-9)
                e = float(np.abs(dy[:len(acts)] - d_res).max()) / scale
                errs.append(e)
                if e > worst[0]:
                    j = int(np.argmax(np.abs(dy[:len(acts)] - d_res)))
                    worst = (e, f"{p}: {acts[j]} kkt {dy[j]:.4g} re-solve {d_res[j]:.4g}")
            restore()
            line = (f"{r}: shocks reaching it {reach}/{len(prods)}, c only {conly}; KKT vs re-solve, max |difference| "
                    f"relative to the largest change: median {np.median(errs) if errs else float('nan'):.3g}, "
                    f"max {max(errs) if errs else float('nan'):.3g} ({worst[1]})")
            print(line, flush=True)
            report.append(line)
        return orig(self, price_signal, supply_results, regions)

    orig = CAPRIModel._market_supply_hessian
    CAPRIModel._market_supply_hessian = compare
    from capri_mod.settings import override
    with override({"market.hessian_skip_unchanged": True}):
        m = CAPRIModel(data_dir=str(ROOT / "capri_data"), verbose=False)
        m.run(scenario="BASELINE", regions=regs, max_outer_iter=2)
    print("\n".join(report))


if __name__ == "__main__":
    main()
