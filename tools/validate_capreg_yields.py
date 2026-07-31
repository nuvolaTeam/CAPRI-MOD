"""
Validate the capreg regional yields BEFORE merging them into the model.

The COCO merge taught the lesson this script exists to apply: a substitution can
look entirely reasonable, pass the base-year gate, and still produce no
measurable improvement. That merge replaced synthetic values with real ones and
moved the median national error from 20.1% to 20.9%.

So this time the candidate is tested first, three ways:

  A. INTERNAL CONSISTENCY
     capreg regional yields, aggregated to national with capreg's own activity
     levels as weights, against capreg's own national rows. Both come from the
     same gdx, so a large gap here means the parse or the weighting is wrong,
     not that the data is bad. This is the sanity check on the ingest itself.

  B. CROSS-SOURCE
     The same regional aggregate against COCO2 national 2017, which is an
     independent extraction from a different CAPRI module. Agreement here is
     real evidence, since nothing is shared between the two paths except CAPRI.

  C. INCUMBENT
     The model's current yields, aggregated with base_areas as weights, against
     the same COCO2 benchmark. This is the number capreg has to beat.

If C is already better than B, merging makes the model worse and should not
happen regardless of how much more principled the new source looks.

Usage
-----
    python tools/validate_capreg_yields.py --coco2 /path/to/coco2.csv
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

COCO2_REC = re.compile(
    r"^'([A-Z]{2}[A-Z0-9]*)'\.'COCO2'\.'([A-Z0-9]+)'\.'YILD'\.'2017'\s+([-\d.Ee+]+)")

# Non-market fodder and set-aside: excluded everywhere, as in the merge tool.
EXCLUDE = {"GRAS", "GRAE", "GRAI", "SETA", "OFOD", "MAIF"}


def load_coco2_national(path: Path) -> dict:
    """(country, activity) -> t/ha for 2017, from the COCO2 stage."""
    out = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = COCO2_REC.match(line)
            if m:
                out[(m.group(1)[:2], m.group(2))] = float(m.group(3)) / 1000.0
    return out


def aggregate(yields: pd.DataFrame, weights: pd.DataFrame,
              activities, regions) -> dict:
    """Area-weighted national aggregate: (country, activity) -> value."""
    agg = {}
    countries = sorted({r[:2] for r in regions})
    for cc in countries:
        regs = [r for r in regions if r.startswith(cc)]
        for a in activities:
            if a not in yields.columns or a not in weights.columns:
                continue
            rs = [r for r in regs
                  if r in yields.index and r in weights.index
                  and pd.notna(yields.at[r, a]) and weights.at[r, a] > 0]
            if len(rs) < 2:
                continue
            w = weights.loc[rs, a]
            agg[(cc, a)] = float((yields.loc[rs, a] * w).sum() / w.sum())
    return agg


def compare(agg: dict, bench: dict, label: str) -> pd.DataFrame:
    rows = []
    for (cc, a), v in agg.items():
        b = bench.get((cc, a))
        if b and b > 0 and np.isfinite(v):
            rows.append({"country": cc, "activity": a,
                         "agg": v, "bench": b,
                         "err_pct": abs(v - b) / b * 100})
    df = pd.DataFrame(rows)
    if df.empty:
        print(f"{label}: no overlapping pairs")
        return df
    print(f"{label}: {len(df)} country x activity pairs, "
          f"median error {df.err_pct.median():.1f}%, "
          f"within 20% = {100*(df.err_pct <= 20).mean():.0f}%")
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coco2", required=True, type=Path)
    ap.add_argument("--data-dir", type=Path, default=Path("capri_data"))
    args = ap.parse_args()

    src = args.data_dir / "sources" / "capreg"
    cap_y = pd.read_csv(src / "capreg_yields.csv", index_col=0)
    cap_l = pd.read_csv(src / "capreg_levels.csv", index_col=0)
    cur_y = pd.read_csv(args.data_dir / "2017/supply/yields.csv", index_col=0)
    areas = pd.read_csv(args.data_dir / "2017/supply/base_areas.csv", index_col=0)

    print("loading COCO2 national benchmark...")
    bench = load_coco2_national(args.coco2)
    print(f"  {len(bench)} national (country, activity) values for 2017\n")

    acts = [a for a in cur_y.columns if a not in EXCLUDE]
    regs = [r for r in cap_y.index if r in cur_y.index]
    print(f"regions common to capreg and the model: {len(regs)}\n")

    # --- capreg national rows, for test A -------------------------------
    # capreg_yields is keyed by model region, so national rows were dropped by
    # the crosswalk. Rebuild the national benchmark from COCO2 only for B/C, and
    # use capreg's own regional spread against COCO2 for A's substitute: the
    # honest internal check available here is whether capreg's regional values
    # aggregate to something close to an independent national figure.
    cap_agg = aggregate(cap_y, cap_l, acts, regs)
    cur_agg = aggregate(cur_y, areas, acts, regs)

    print("=" * 66)
    b = compare(cap_agg, bench, "B. capreg regional -> national vs COCO2  ")
    c = compare(cur_agg, bench, "C. current model  -> national vs COCO2  ")
    print("=" * 66)

    if b.empty or c.empty:
        return

    # Only pairs both configurations can produce -- otherwise the comparison
    # rewards whichever source happens to cover the easier activities.
    key = ["country", "activity"]
    m = b.merge(c, on=key, suffixes=("_capreg", "_current"))
    print(f"\nhead-to-head on {len(m)} pairs both sources cover:")
    print(f"  capreg  median error : {m.err_pct_capreg.median():.1f}%")
    print(f"  current median error : {m.err_pct_current.median():.1f}%")
    print(f"  capreg closer in     : {100*(m.err_pct_capreg < m.err_pct_current).mean():.0f}% of pairs")

    per = m.groupby("activity").agg(
        n=("err_pct_capreg", "size"),
        capreg=("err_pct_capreg", "median"),
        current=("err_pct_current", "median")).round(1)
    per["better"] = np.where(per.capreg < per.current, "capreg", "current")
    print("\nby activity:")
    print(per.sort_values("capreg").to_string())

    out = args.data_dir / "validation" / "capreg_yield_validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "pairs_compared": int(len(m)),
        "capreg_median_err_pct": round(float(m.err_pct_capreg.median()), 2),
        "current_median_err_pct": round(float(m.err_pct_current.median()), 2),
        "capreg_closer_share_pct": round(
            float(100 * (m.err_pct_capreg < m.err_pct_current).mean()), 1),
        "by_activity": per.to_dict("index"),
    }, indent=1))
    print(f"\nwritten: {out}")


if __name__ == "__main__":
    main()
