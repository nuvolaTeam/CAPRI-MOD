"""
Point 5 diagnostic — where does scenario adjustment land?

Real CAPRI elasticity estimates exist only for arable crops. Wiring them in
raises the responsiveness of that block while permanent crops, grassland and
livestock stay on literature defaults. The concern is that a half-covered model
concentrates all scenario adjustment in the covered activities, which a
base-year gate cannot detect because the base year is unshocked by construction.

This runs a price shock under both configurations and reports where the acreage
actually moves.

Usage
-----
    python tools/scenario_elasticity_check.py [--shock 0.20] [--regions 40]
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from capri_mod.data.loaders import load_all_data
from capri_mod.data.definitions import ALL_ACTIVITIES
from capri_mod.supply.supply_module import SupplyModule
from capri_mod.supply.capri_pmp import (
    build_elasticity_table, asymmetry_report, EPRD_TO_GRP,
)
from capri_mod.utils.utils import calibrate_supply_elasticities

SHOCKED = ["SWHE", "DWHE", "BARL", "RYEM", "OATS", "CORN", "OCER"]


def run(data, defaults, regions, shock, use_capri):
    sm = SupplyModule(data, defaults, use_capri_elasticities=use_capri)
    sig = pd.Series(0.0, index=ALL_ACTIVITIES)
    sig[[c for c in SHOCKED if c in sig.index]] = shock
    out = {}
    for r in regions:
        try:
            res = sm.run(price_signals=sig, regions=[r])[r]
            out[r] = pd.Series(res.activities)
        except Exception:
            continue
    return pd.DataFrame(out).T, sm


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shock", type=float, default=0.20)
    ap.add_argument("--regions", type=int, default=40)
    ap.add_argument("--out", type=Path,
                    default=Path("capri_data/validation/elasticity_wiring_report.json"))
    args = ap.parse_args()

    data = load_all_data("capri_data")
    defaults = calibrate_supply_elasticities(data["areas"])
    regions = list(data["areas"].index[:args.regions])

    eps, prov, summary = build_elasticity_table(
        Path("capri_data"), list(data["areas"].index), ALL_ACTIVITIES, defaults,
        base_areas=data["areas"])
    asym = asymmetry_report(eps, prov)

    print(f"provenance : {summary['by_provenance']}")
    print(f"coverage   : {summary['pct_real']}% of cells, "
          f"{summary['regions_with_any_real']} regions, "
          f"{summary['activities_with_any_real']} activities")
    print(f"asymmetry  : covered median {asym['covered_median']} vs "
          f"uncovered {asym['uncovered_median']} -> ratio {asym['asymmetry_ratio']}\n")

    print(f"running +{args.shock:.0%} cereal price shock on {len(regions)} regions...")
    new, sm_new = run(data, defaults, regions, args.shock, True)
    old, _ = run(data, defaults, regions, args.shock, False)
    base = data["areas"].reindex(new.index)

    covered = [a for a in ALL_ACTIVITIES
               if a in EPRD_TO_GRP or a in {"CORN", "MAIF"}]
    common = [c for c in new.columns if c in old.columns and c in base.columns]
    cov = [c for c in common if c in covered]
    unc = [c for c in common if c not in covered]

    rows = []
    for label, df in (("legacy", old), ("capri", new)):
        d = (df[common] - base[common]).abs()
        tot = d.sum().sum()
        rows.append({
            "config": label,
            "total_abs_reallocation_kha": round(float(tot), 1),
            "share_in_covered_arable_pct": round(100 * float(d[cov].sum().sum()) / tot, 1)
            if tot else None,
            "share_in_uncovered_pct": round(100 * float(d[unc].sum().sum()) / tot, 1)
            if tot else None,
        })
    cmp = pd.DataFrame(rows)
    print("\n" + cmp.to_string(index=False))

    resp = {}
    for c in common:
        b = base[c].replace(0, np.nan)
        resp[c] = {
            "legacy_pct": round(float(((old[c] - base[c]) / b * 100).median()), 2),
            "capri_pct": round(float(((new[c] - base[c]) / b * 100).median()), 2),
            "covered": c in cov,
        }
    r = pd.DataFrame(resp).T.sort_values("capri_pct", ascending=False)
    print("\nmedian acreage response to the shock (%):")
    print(r.head(12).to_string())

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "shock": args.shock, "shocked_activities": SHOCKED,
        "regions_tested": len(regions),
        "elasticity_summary": summary,
        "asymmetry": asym,
        "reallocation": cmp.to_dict("records"),
        "response_by_activity": resp,
    }, indent=1))
    print(f"\nwritten: {args.out}")


if __name__ == "__main__":
    main()
