"""
Fix 2 — replace synthetic yields with CAPRI's own COCO yields where a region
match is certain.

Background
----------
`capri_data/2017/supply/yields.csv` is labelled REAL_CAPRI in the sourcing
registry, but 16 of its 40 activity columns carry a synthetic fingerprint:
a constant multiplied by lognormal noise at sigma = 0.10 (coefficient of
variation 0.089-0.101 across all 248 regions, where real regional yields
scatter at 0.2-0.5).

CAPRI's real crop yields were already in the repository, unused, at
`capri_data/sources/coco/coco_yields.csv`. They looked incompatible because
COCO keys regions with CAPRI's 8-character codes (DE110000) while the model
uses NUTS2 (DE11). The crosswalk is simply NUTS2 + "0000", validated against
the authoritative code list in <capri>/gams/capreg/regio_sets.gms.

Safety
------
Following the point-3 procedure, this touches ONE input (yields) and only
where the substitution is defensible:

  1. Region match must be certain — the NUTS2 code must appear in
     regio_sets.gms. Regions on the old NUTS2 classification (FR, IT, parts
     of DE and EL) are left untouched pending a proper crosswalk.
  2. Non-market activities (GRAS, MAIF, OFOD, SETA) are excluded — they are
     valued at on-farm opportunity cost, not market price, so the margin
     guard does not apply to them.
  3. Margin guard — a cell is only accepted if the CAP-adjusted gross margin
     stays above the validator's _ARTIFACT_LOSS threshold. A substitution
     that would push a previously-healthy crop into implausible loss is
     rejected and the original value kept.
  4. Zero and missing COCO values are never written.

Usage
-----
    python tools/merge_coco_yields.py --capri-gams /path/to/capri/gams [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

# Non-marketed fodder activities: excluded from substitution and from the
# margin guard, matching validate_data._NON_MARKET.
NON_MARKET = {"GRAS", "MAIF", "OFOD", "SETA"}

# Matches validate_data._ARTIFACT_LOSS: a CAP-adjusted loss worse than this
# (EUR/ha) is not real economics, it is a data error.
ARTIFACT_LOSS = -1000.0

DATA = Path("capri_data")
YIELDS = DATA / "2017" / "supply" / "yields.csv"
COCO = DATA / "sources" / "coco" / "coco_yields.csv"
COSTS = DATA / "2017" / "supply" / "variable_costs.csv"
AREAS = DATA / "2017" / "supply" / "base_areas.csv"
PRICES = DATA / "2017" / "market" / "producer_prices.csv"
PAYMENTS = DATA / "2017" / "policy" / "cap_payments.csv"


def load_capri_region_codes(gams_root: Path) -> set[str]:
    """Authoritative CAPRI 8-character region codes from regio_sets.gms."""
    path = gams_root / "capreg" / "regio_sets.gms"
    if not path.exists():
        raise SystemExit(f"regio_sets.gms not found under {gams_root}")
    text = path.read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r"\b([A-Z]{2}[A-Z0-9]{6})\b", text))


def build_crosswalk(nuts2_codes, capri_codes: set[str],
                    crosswalk_file: Path | None = None) -> dict[str, str]:
    """NUTS2 -> CAPRI code, only where the CAPRI code is attested.

    The direct rule is NUTS2 + "0000". Regions on an older classification
    (FR24 -> FRB0, GR11 -> EL51) need Eurostat's correspondence chain; pass a
    crosswalk built by tools/build_nuts_crosswalk.py to pick those up too.
    """
    cw = {r: f"{r}0000" for r in nuts2_codes if f"{r}0000" in capri_codes}
    if crosswalk_file and crosswalk_file.exists():
        extra = json.loads(crosswalk_file.read_text())["resolved"]
        for region, capri in extra.items():
            if region in nuts2_codes and capri in capri_codes:
                cw.setdefault(region, capri)
    return cw


def cap_adjusted_margin(yield_t_ha, price_eur_t, cost_eur_ha, payment_eur_ha):
    return yield_t_ha * price_eur_t - cost_eur_ha + payment_eur_ha


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--capri-gams", required=True, type=Path,
                    help="path to the CAPRI gams/ directory")
    ap.add_argument("--crosswalk", type=Path,
                    default=Path("capri_data/shared/nuts_crosswalk.json"),
                    help="optional NUTS crosswalk from build_nuts_crosswalk.py")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    y = pd.read_csv(YIELDS, index_col=0)
    coco = pd.read_csv(COCO, index_col=0)
    costs = pd.read_csv(COSTS, index_col=0)
    areas = pd.read_csv(AREAS, index_col=0)
    prices_df = pd.read_csv(PRICES, index_col=0)
    price = prices_df[prices_df.columns[0]]

    try:
        pay = pd.read_csv(PAYMENTS, index_col=0)
        pay_per_ha = pay.sum(axis=1) if pay.shape[1] > 1 else pay[pay.columns[0]]
    except Exception:
        pay_per_ha = pd.Series(0.0, index=y.index)

    capri_codes = load_capri_region_codes(args.capri_gams)
    cw = build_crosswalk(y.index, capri_codes, args.crosswalk)
    print(f"CAPRI region codes in regio_sets.gms : {len(capri_codes)}")
    print(f"model regions                        : {len(y.index)}")
    print(f"certain crosswalk matches            : {len(cw)}")

    unmatched = [r for r in y.index if r not in cw]
    by_country = pd.Series([r[:2] for r in unmatched]).value_counts()
    print(f"unmatched (old NUTS2 classification) : {len(unmatched)} "
          f"-> {by_country.to_dict()}")

    crops = [c for c in y.columns
             if c in coco.columns and c not in NON_MARKET]
    print(f"substitutable crop columns           : {len(crops)}\n")

    new = y.copy()
    applied, rejected_margin, skipped_zero = 0, 0, 0
    deviations = []
    rejects = []

    for reg, capri_reg in cw.items():
        if capri_reg not in coco.index:
            continue
        for crop in crops:
            old_val = y.at[reg, crop]
            new_val = coco.at[capri_reg, crop]

            if not np.isfinite(new_val) or new_val <= 0:
                skipped_zero += 1
                continue
            # Crop not grown here: nothing to guard, nothing worth changing.
            if crop not in areas.columns or areas.at[reg, crop] <= 0:
                continue
            if crop not in costs.columns or crop not in price.index:
                continue

            c_ha = costs.at[reg, crop]
            p_t = price.at[crop]
            sub = pay_per_ha.get(reg, 0.0)

            m_old = cap_adjusted_margin(old_val, p_t, c_ha, sub)
            m_new = cap_adjusted_margin(new_val, p_t, c_ha, sub)

            # Reject only substitutions that newly create an implausible loss.
            if m_new < ARTIFACT_LOSS <= m_old:
                rejected_margin += 1
                rejects.append({"region": reg, "crop": crop,
                                "margin_before": round(m_old, 1),
                                "margin_after": round(m_new, 1)})
                continue

            if old_val > 0:
                deviations.append({"region": reg, "crop": crop,
                                   "old": old_val, "new": new_val,
                                   "dev_pct": 100 * (old_val - new_val) / new_val})
            new.at[reg, crop] = new_val
            applied += 1

    print(f"cells applied        : {applied}")
    print(f"rejected by margin   : {rejected_margin}")
    print(f"skipped (zero/NaN)   : {skipped_zero}")

    if deviations:
        dev = pd.DataFrame(deviations)
        med = dev.groupby("crop")["dev_pct"].apply(
            lambda s: s.abs().median()).sort_values(ascending=False)
        print("\nmedian |deviation| of the synthetic values that were replaced:")
        print(med.round(1).to_string())

    if args.dry_run:
        print("\n[dry run] nothing written")
        return

    backup = YIELDS.with_suffix(".csv.pre_coco_merge")
    if not backup.exists():
        shutil.copy(YIELDS, backup)
    new.to_csv(YIELDS)

    report = {
        "crosswalk_rule": 'NUTS2 + "0000", validated against regio_sets.gms',
        "regions_matched": len(cw),
        "regions_unmatched": len(unmatched),
        "unmatched_by_country": by_country.to_dict(),
        "cells_applied": applied,
        "cells_rejected_by_margin": rejected_margin,
        "rejects": rejects[:50],
    }
    out = DATA / "validation" / "coco_yield_merge_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(f"\nwritten: {YIELDS}\nbackup : {backup}\nreport : {out}")


if __name__ == "__main__":
    main()
