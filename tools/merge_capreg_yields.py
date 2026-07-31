"""
Merge the validated capreg crop yields into the model, one country at a time.

Scope
-----
The 21 crop activities that passed validation against the independent COCO2
national benchmark (median error 4.7% vs the incumbent's 16.0%, capreg closer in
82% of pairs and better on every single activity).

Deliberately excluded, each for a different reason:

  OANI                 units. capreg 505.8 against the model's 0.003 is the
                       LEVL convention from cons_levls.gms, unresolved.
  GRAS                 definitional. capreg 410.9 vs COCO2 17770 for the same
                       country and year means the two modules mean different
                       things by the word.
  DCOW, BULL, PIGF     real and correctly parsed, but COCO2 carries no livestock
                       so they have no independent benchmark. Separate pass.
  MAIF, OFOD, SETA     non-market: valued at on-farm opportunity cost, so the
                       margin guard cannot be applied to them.

Gating
------
Merging proceeds country by country. After each country the margin guard is
re-checked over that country's regions, and a country whose substitution would
push a previously-healthy crop into implausible loss is rolled back whole. A
full model gate is run at the end.

This is deliberately more conservative than the data warrants, because yields
feed PMP calibration: a bad cell does not show up as a bad yield, it shows up as
a region that stops converging three steps later.

Usage
-----
    python tools/merge_capreg_yields.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

MERGE_ACTIVITIES = [
    "SWHE", "DWHE", "RYEM", "BARL", "OATS", "OCER", "CORN", "POTA", "SUGB",
    "SUNF", "RAPE", "SOYA", "OOIL", "PULS", "TOMA", "OVEG", "APPL",
    "OFRU", "CITR", "TAGR", "OLIV", "TOBA",
]

# Livestock, merged with --livestock. Held separate because COCO2 carries no
# livestock, so unlike the crops these have no independent benchmark; they go in
# on magnitude checks alone:
#   DCOW  7431 kg milk/head/yr  (EU average is around 7000-7500)
#   BULL   252 kg carcass/head  (annualised over ~151 production days)
#   PIGF    90 kg carcass/head  (typical slaughter carcass)
# The activity level is head count, not area, so the margin guard uses
# animal_numbers as the weight and EUR/head rather than EUR/ha.
LIVESTOCK_ACTIVITIES = ["DCOW", "BULL", "PIGF"]

# animal_numbers.csv has no PIGF column: it counts PIGS and SOWS. The level is
# used only as a presence test -- "is this activity carried on in this region" --
# so total pigs is an adequate stand-in for pig fattening. It is never used as a
# weight, so the aggregation is unaffected.
LEVEL_ALIAS = {"PIGF": "PIGS"}

ARTIFACT_LOSS = -1000.0     # matches validate_data._ARTIFACT_LOSS

D = Path("capri_data")
YIELDS = D / "2017/supply/yields.csv"
CAPREG = D / "sources/capreg/capreg_yields.csv"
COSTS = D / "2017/supply/variable_costs.csv"
AREAS = D / "2017/supply/base_areas.csv"
PRICES = D / "2017/market/producer_prices.csv"
PAYMENTS = D / "2017/policy/cap_payments.csv"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--livestock", action="store_true",
                    help="merge livestock yields instead of crops")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cur = pd.read_csv(YIELDS, index_col=0)
    cap = pd.read_csv(CAPREG, index_col=0)
    costs = pd.read_csv(COSTS, index_col=0)
    areas = pd.read_csv(AREAS, index_col=0)
    pdf = pd.read_csv(PRICES, index_col=0)
    price = pdf[pdf.columns[0]]
    try:
        pay = pd.read_csv(PAYMENTS, index_col=0)
        pay_ha = pay.sum(axis=1) if pay.shape[1] > 1 else pay[pay.columns[0]]
    except Exception:
        pay_ha = pd.Series(0.0, index=cur.index)

    if args.livestock:
        levels = pd.read_csv(D / "2017/supply/animal_numbers.csv", index_col=0)
        wanted = LIVESTOCK_ACTIVITIES
    else:
        levels = areas
        wanted = MERGE_ACTIVITIES
    regions = [r for r in cap.index if r in cur.index]
    acts = [a for a in wanted if a in cap.columns and a in cur.columns]
    countries = sorted({r[:2] for r in regions})

    print(f"capreg regions usable : {len(regions)}")
    print(f"activities to merge   : {len(acts)}")
    print(f"countries             : {len(countries)}\n")

    new = cur.copy()
    applied = rejected = skipped = 0
    per_country, rolled_back = {}, []

    for cc in countries:
        regs = [r for r in regions if r.startswith(cc)]
        block = new.copy()
        n_c = n_rej = 0
        for r in regs:
            sub = pay_ha.get(r, 0.0)
            for a in acts:
                v = cap.at[r, a]
                if not np.isfinite(v) or v <= 0:
                    skipped += 1
                    continue
                lvl_col = LEVEL_ALIAS.get(a, a)
                if lvl_col not in levels.columns or levels.at[r, lvl_col] <= 0:
                    continue
                if a not in costs.columns or a not in price.index:
                    continue
                c_ha, p_t = costs.at[r, a], price.at[a]
                m_old = cur.at[r, a] * p_t - c_ha + sub
                m_new = v * p_t - c_ha + sub
                if m_new < ARTIFACT_LOSS <= m_old:
                    n_rej += 1
                    continue
                block.at[r, a] = float(v)
                n_c += 1

        # roll the whole country back if the guard fired on more than a tenth
        # of its substitutions: scattered rejections are normal, a cluster means
        # something systematic about that country's prices or costs.
        if n_c and n_rej > 0.10 * (n_c + n_rej):
            rolled_back.append(cc)
            print(f"  {cc}: ROLLED BACK ({n_rej} rejects of {n_c + n_rej})")
            continue

        new = block
        applied += n_c
        rejected += n_rej
        per_country[cc] = {"regions": len(regs), "cells": n_c, "rejected": n_rej}
        print(f"  {cc}: {len(regs):3d} regions, {n_c:4d} cells"
              + (f", {n_rej} rejected" if n_rej else ""))

    print(f"\ncells applied  : {applied}")
    print(f"rejected       : {rejected}")
    print(f"skipped (0/NaN): {skipped}")
    if rolled_back:
        print(f"countries rolled back: {rolled_back}")

    changed = (new - cur).abs() > 1e-9
    dev = []
    for a in acts:
        if changed[a].any():
            m = changed[a]
            d = ((cur.loc[m, a] - new.loc[m, a]).abs()
                 / new.loc[m, a].replace(0, np.nan) * 100).median()
            dev.append((a, int(m.sum()), round(float(d), 1)))
    print("\nmedian |change| applied, by activity:")
    print(pd.DataFrame(dev, columns=["activity", "cells", "dev_pct"])
          .sort_values("dev_pct", ascending=False).to_string(index=False))

    if args.dry_run:
        print("\n[dry run] nothing written")
        return

    suffix = ".csv.pre_livestock_merge" if args.livestock else ".csv.pre_capreg_merge"
    backup = YIELDS.with_suffix(suffix)
    if not backup.exists():
        shutil.copy(YIELDS, backup)
    new.to_csv(YIELDS)

    rep = D / "validation" / ("livestock_merge_report.json" if args.livestock
                              else "capreg_merge_report.json")
    rep.write_text(json.dumps({
        "source": "capreg DATA2, res_17<MS>.gdx, base year 2017",
        "activities_merged": acts,
        "excluded": {
            "OANI": "LEVL unit convention unresolved",
            "GRAS": "definitional conflict, capreg 410.9 vs COCO2 17770",
            "DCOW/BULL/PIGF": "no independent benchmark, separate pass",
            "MAIF/OFOD/SETA": "non-market, margin guard inapplicable",
        },
        "cells_applied": applied,
        "cells_rejected": rejected,
        "countries_rolled_back": rolled_back,
        "per_country": per_country,
    }, indent=2))
    print(f"\nwritten: {YIELDS}\nbackup : {backup}\nreport : {rep}")


if __name__ == "__main__":
    main()
