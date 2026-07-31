"""
Scenario validation framework for CAPRI-Python.

Purpose: test whether the model RESPONDS to shocks the way economic theory
(and CAPRI) would predict — not just whether it reproduces the base.

Three families of test:
  1. Supply-response elasticities   — does a price rise raise the right activity
                                       by the right amount (vs the PELA target)?
  2. Cross-price substitution       — does a crop price rise pull land from
                                       competing crops?
  3. Market/trade shocks            — do world price shocks and tariff changes
                                       move prices and trade in the right direction?

For each test we report: the model's response, the economically-expected sign,
the calibrated target where one exists, and a PASS/CHECK/FAIL verdict.

This is a behavioural check. Where real CAPRI scenario outputs are available they
should be dropped into REFERENCE below to turn CHECK verdicts into quantitative
PASS/FAIL against CAPRI itself.
"""
import sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "/home/claude")
import pandas as pd
import numpy as np
from capri_python.model import CAPRIModel


# ---------------------------------------------------------------------------
# Reference values from real CAPRI (fill in when CAPRI scenario outputs exist)
# ---------------------------------------------------------------------------
# Own-price supply elasticities CAPRI reports (from PELA / literature)
CAPRI_SUPPLY_ELAS = {
    "SWHE": (0.3, 1.8),   # (low, high) plausible range across regions
    "BARL": (0.3, 1.6),
    "CORN": (0.3, 1.8),
    "RAPE": (0.3, 1.7),
}
# Placeholder for real CAPRI scenario deltas — e.g. {"WTO_LIB": {"BEEF": -0.08}}
CAPRI_SCENARIO_DELTAS = {}


def measure_supply_elasticity(model, region, activity, shocks=(0.10, 0.20)):
    """Directly perturb the supply module's price signal and measure response."""
    base = model.supply_module.run(price_signals=None, regions=[region])
    q0 = base[region].activities.get(activity, 0.0)
    if q0 <= 0:
        return None
    elasticities = []
    for shk in shocks:
        sig = pd.Series(0.0, index=model.data["world_prices"].index)
        if activity in sig.index:
            sig[activity] = shk
        s = model.supply_module.run(price_signals=sig, regions=[region])
        q1 = s[region].activities.get(activity, 0.0)
        e = ((q1 - q0) / q0) / shk
        elasticities.append(e)
    return float(np.mean(elasticities))


def test_supply_elasticities(model, regions):
    print("\n" + "=" * 70)
    print("TEST 1 — Own-price supply elasticities (supply module)")
    print("=" * 70)
    print(f"{'region':7s} {'act':5s} {'implied':>8s} {'CAPRI range':>13s} {'verdict':>8s}")
    rows = []
    for region in regions:
        for act in ["SWHE", "BARL", "CORN", "RAPE"]:
            e = measure_supply_elasticity(model, region, act)
            if e is None:
                continue
            lo, hi = CAPRI_SUPPLY_ELAS.get(act, (0.1, 2.5))
            verdict = "PASS" if lo * 0.7 <= e <= hi * 1.3 else "CHECK"
            print(f"{region:7s} {act:5s} {e:8.2f} {f'{lo}-{hi}':>13s} {verdict:>8s}")
            rows.append({"region": region, "activity": act,
                         "implied_elas": round(e, 3), "verdict": verdict})
    return rows


def test_cross_price(model, region):
    """Shock ONE crop's price signal and check competing crops fall (land competition)."""
    print("\n" + "=" * 70)
    print("TEST 2 — Cross-price substitution (land competition)")
    print("=" * 70)
    base = model.supply_module.run(price_signals=None, regions=[region])
    b = base[region].activities
    sig = pd.Series(0.0, index=model.data["world_prices"].index)
    sig["SWHE"] = 0.25  # +25% wheat price only
    s = model.supply_module.run(price_signals=sig, regions=[region])
    a = s[region].activities
    print(f"Region {region}: +25% wheat price only")
    print(f"{'act':6s} {'base':>8s} {'shock':>8s} {'change':>8s} {'expected':>10s}")
    rows = []
    for act in ["SWHE", "BARL", "CORN", "RAPE", "POTA"]:
        q0 = b.get(act, 0.0); q1 = a.get(act, 0.0)
        if q0 <= 0:
            continue
        ch = (q1 - q0) / q0 * 100
        exp = "up" if act == "SWHE" else "down"
        ok = (ch > 0) if act == "SWHE" else (ch <= 0.5)
        rows.append({"activity": act, "change_pct": round(ch, 2),
                     "expected": exp, "ok": ok})
        print(f"{act:6s} {q0:8.1f} {q1:8.1f} {ch:+7.1f}% {exp:>10s} {'OK' if ok else 'CHECK'}")
    return rows


def test_market_shock(model, regions):
    """World price shock: does it propagate and move quantities sensibly?"""
    print("\n" + "=" * 70)
    print("TEST 3 — Market shock propagation (+30% world wheat)")
    print("=" * 70)
    base = model.run(scenario="BASELINE", max_outer_iter=3, market_max_iter=80,
                     regions=regions, run_environmental=False, run_feed=False)
    shock = model.run(scenario="BASELINE", world_price_shock={"SWHE": 0.30},
                      max_outer_iter=3, market_max_iter=80, regions=regions,
                      run_environmental=False, run_feed=False)
    wp0, wp1 = base["market"].world_prices, shock["market"].world_prices

    def wheat_supply(res):
        return sum(r.activities.get("SWHE", 0.0) for r in res["supply"].values())

    w0, w1 = wheat_supply(base), wheat_supply(shock)
    dq = (w1 - w0) / w0 * 100 if w0 else 0
    print(f"World wheat price: {wp0.get('SWHE',0):.0f} -> {wp1.get('SWHE',0):.0f}")
    print(f"EU wheat supply:   {w0:.0f} -> {w1:.0f}  ({dq:+.1f}%)")
    print("Expected: higher price -> higher supply (positive response).")
    verdict = "PASS" if dq > 0 else "FAIL"
    print(f"Verdict: {verdict}")
    return {"price_change_pct": 30, "supply_change_pct": round(dq, 2),
            "verdict": verdict}


if __name__ == "__main__":
    model = CAPRIModel(data_dir="/home/claude/capri_data", verbose=False)
    test_regions = list(model.data["areas"].index[:5])

    r1 = test_supply_elasticities(model, test_regions[:2])
    r2 = test_cross_price(model, test_regions[0])
    r3 = test_market_shock(model, test_regions)

    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    n_elas_pass = sum(1 for r in r1 if r["verdict"] == "PASS")
    n_cross_ok = sum(1 for r in r2 if r["ok"])
    print(f"  Supply elasticities in CAPRI range: {n_elas_pass}/{len(r1)}")
    print(f"  Cross-price responses correct sign: {n_cross_ok}/{len(r2)}")
    print(f"  Market shock propagation:           {r3['verdict']}")
