#!/usr/bin/env python3
"""Check the model against the validated regression anchors.

Run this after ANY change to ``capri_data`` or to the supply, market, policy or
environmental modules — and especially before and after a base-year re-base.

What it is for
--------------
It tells you **which validation broke**, not merely that a number moved. Each
anchor names the external reference it was checked against, so a failure points
at a source you can go and re-read rather than a bare delta.

Why it exists
-------------
Eleven real defects were found in a single working session, and every one was
surfaced by an *external* reference rather than an internal consistency check.
Several had been silently wrong for the life of the project. Internal checks
only see what they are pointed at: the permanent-crop collapse sat invisible
behind a base-fidelity measure that only looked at annual crops, which is why
olives now have an anchor of their own.

Exit codes
----------
0 = all checked anchors within tolerance
1 = at least one anchor breached

Usage
-----
    python tools/check_regression.py [--data-dir capri_data] [--update]

``--update`` rewrites the anchors to the current values. Use it only when a
change is *intended* and has been explained — it is how a re-base is accepted,
not a way to silence a failure.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

# run from anywhere: put the repo root on the path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

ANCHORS = _ROOT / "capri_data" / "validation" / "REGRESSION_ANCHORS.json"


def measure(data_dir: str) -> dict:
    """Recompute the cheap anchors. Loose anchors are skipped by default."""
    import numpy as np
    import pandas as pd
    from capri_mod.data.loaders import load_all_data
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities
    from capri_mod.market.market_module import MarketModule
    from capri_mod.policy.policy_module import PolicyModule, PolicyScenario
    from capri_mod.environmental.environmental_module import EnvironmentalModule
    from capri_mod.data.definitions import MARKET_COMMODITIES

    d = load_all_data(data_dir)
    sm = SupplyModule(d, calibrate_supply_elasticities(d["areas"]))
    res = sm.run(price_signals=None)

    out = {"n_regions": len(res),
           "n_converged": int(sum(1 for v in res.values() if v.converged))}

    errs, olv = [], []
    for reg in d["areas"].index:
        model = sm._models.get(reg)
        if model is None:
            continue
        solved = model.solve(price_shock=None)
        for a in ("SWHE", "BARL", "RAPE", "MAIZ", "SUGB", "POTA"):
            base = model._base_levels().get(a, 0)
            if base >= 2:
                errs.append(abs(solved.activities.get(a, 0) - base) / base)
        ob = model._base_levels().get("OLIV", 0)
        if ob >= 2:
            olv.append(abs(solved.activities.get("OLIV", 0) - ob) / ob)
    out["base_fidelity_pct"] = round(float(np.mean(errs)) * 100, 2)
    out["olive_base_fidelity_pct"] = round(float(np.mean(olv)) * 100, 2)

    em = EnvironmentalModule(d)
    surplus = []
    for reg in list(d["areas"].index[:30]):
        if reg not in res or reg not in d["yields"].index:
            continue
        acts = res[reg].activities
        nb = em.compute_nitrogen_balance(acts, d["yields"].loc[reg], reg)
        area = sum(float(acts.get(c, 0.0)) for c in d["areas"].columns)
        if area > 0:
            surplus.append(nb["n_surplus"] / area)
    out["n_surplus_median_kg_ha"] = round(float(np.median(surplus)), 1)

    mm = MarketModule(d)
    imb = []
    for c in ("SWHE", "RAPE", "SOYA", "BEEF"):
        p = mm.base_production[c].sum()
        q = mm.base_consumption[c].sum()
        if p > 0:
            imb.append(abs(q - p) / p * 100)
    out["max_world_imbalance_pct"] = round(float(max(imb)), 3)

    exo = pd.DataFrame(0.0, index=["EU27"], columns=MARKET_COMMODITIES)
    for c in MARKET_COMMODITIES:
        if c in mm.base_production.columns:
            exo.at["EU27", c] = mm.base_production.at["EU27", c]
    eq = mm.solve(exogenous_supply=exo, max_iter=150, tolerance=0.01)
    ref = {"SWHE": 148, "BARL": 145, "CORN": 148, "RAPE": 213, "SOYA": 103,
           "BEEF": 3692, "PORK": 1613, "POUL": 1405, "MILK": 319,
           "BUTR": 3782, "CHES": 4815, "SKIM": 1429}
    out["price_reproduction_within_15pct"] = int(sum(
        1 for c, r in ref.items()
        if abs((eq.world_prices.get(c, 0) - r) / r) <= 0.15))

    pm = PolicyModule(d, PolicyScenario(name="BASELINE"))
    out["eu_cap_budget_bn_eur"] = round(
        float(pm.summarise_policy()["total_EU_budget_EUR_billion"]), 1)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="capri_data")
    ap.add_argument("--update", action="store_true",
                    help="accept current values as the new anchors")
    args = ap.parse_args()

    fixture = json.loads(ANCHORS.read_text())
    current = measure(args.data_dir)

    failures, checked, skipped = [], 0, []
    for name, spec in fixture["anchors"].items():
        if name not in current:
            skipped.append(name)
            continue
        checked += 1
        got, want, tol = current[name], spec["value"], spec["tolerance"]
        if abs(got - want) > tol:
            failures.append((name, want, got, tol, spec["reference"]))

    print(f"Regression check — base year {fixture['base_year']}")
    print(f"  {checked} anchors checked, {len(skipped)} skipped "
          f"(expensive: {', '.join(skipped) or 'none'})\n")

    for name, spec in fixture["anchors"].items():
        if name in skipped:
            continue
        got, want = current[name], spec["value"]
        mark = "FAIL" if any(f[0] == name for f in failures) else "ok  "
        print(f"  [{mark}] {name}: {got}  (anchor {want} +/- {spec['tolerance']})")

    if failures:
        print("\nBREACHED — each names the reference that validated it:\n")
        for name, want, got, tol, refr in failures:
            print(f"  {name}: {want} -> {got} (tolerance {tol})")
            print(f"      validated against: {refr}\n")
        print("Explain each breach before accepting the change. If the new value "
              "is correct and understood, re-run with --update.")

    if args.update:
        for name, val in current.items():
            if name in fixture["anchors"]:
                fixture["anchors"][name]["value"] = val
        ANCHORS.write_text(json.dumps(fixture, indent=1))
        print(f"\nAnchors updated to current values in {ANCHORS}.")
        return 0

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
