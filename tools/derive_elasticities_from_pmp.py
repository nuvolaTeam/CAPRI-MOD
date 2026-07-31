"""
Derive supply elasticities for the activities PELA does not cover, using
CAPRI's own PMP terms and CAPRI's own relation between them.

The problem
-----------
PELA covers 15 arable crops. Permanent crops, vegetables and tobacco fall back
to EU-wide literature defaults around 0.15, against a CAPRI arable median of
1.43. That gap -- an asymmetry ratio of 9.56 -- means a price shock puts 90% of
its reallocation into arable land, which is a property of data coverage rather
than of agronomy, and it distorts every scenario the model runs.

The relation
------------
From gams/supply/pmp_terms/impose_upper_bound_on_elasticity.gms, CAPRI computes
the elasticity implied by its own PMP parameters as

    elas = revenue / (LEVL * shareTerm * (pmpQuadTechn + pmpQuadPact))

Every term on the right is now available from a GDX read:

    revenue        yield x producer price, both from DATA2
    LEVL           base activity level, from DATA2
    shareTerm      1 - 0.2*sqrt(share of arable), already implemented
    pmpQuadTechn   from pmppar, 30 activities x 192 regions
    pmpQuadPact    from pmppar, group level

So the elasticities for the uncovered activities are not missing -- they are
implicit in parameters we already hold, and this inverts CAPRI's formula to
recover them.

Why this is not circular
------------------------
The supply module runs the relation the other way: it takes an elasticity and
constructs Q. Here the direction is Q -> elasticity, using CAPRI's estimated Q
rather than the model's constructed one. The result is what CAPRI's calibration
implies about supply response, which is exactly the quantity the literature
defaults were standing in for.

The derived values are sanity-checked against PELA on the 15 activities where
both exist. If the derivation cannot reproduce PELA where PELA is known, it
should not be trusted where PELA is unknown.

Usage
-----
    python tools/derive_elasticities_from_pmp.py [--write]
"""
from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

D = Path("capri_data")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=D)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    dd = args.data_dir

    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from capri_python.supply.capri_pmp import (
        share_term, ARABLE_ACTIVITIES, EPRD_TO_GRP, dampen_elasticity)

    qt = pd.read_csv(dd / "sources/capreg/pmp_quad_techn.csv")
    qp = pd.read_csv(dd / "sources/capreg/pmp_quad_pact.csv")
    yields = pd.read_csv(dd / "2017/supply/yields.csv", index_col=0)
    areas = pd.read_csv(dd / "2017/supply/base_areas.csv", index_col=0)
    prices = pd.read_csv(dd / "sources/capreg/capreg_producer_prices.csv", index_col=0)
    pela = pd.read_csv(dd / "2017/supply/supply_elasticities_regional.csv", index_col=0)

    # Livestock revenue lives in different frames than crops: the "level" is the
    # herd size, the yield is output per head from the raw capreg extract, and
    # both are keyed by animal activity rather than crop. Loaded here so the
    # derivation can treat livestock on the same footing as crops.
    herds = pd.read_csv(dd / "sources/capreg/capreg_herds.csv", index_col=0)
    ls_yields = pd.read_csv(dd / "sources/capreg/capreg_yields.csv", index_col=0)
    LIVESTOCK = {"DCOL", "DCOH", "BULL", "BULH", "SCOW", "HEIR", "HEIL", "HEIH",
                 "PIGF", "SOWS", "HENS", "POUF", "SHGF", "SHGM", "CAFF", "CAFR",
                 "CAMF", "CAMR"}

    techn = qt.pivot_table(index="model_region", columns="activity",
                           values="value", aggfunc="last")
    # group diagonal, i.e. the own-group term that adds to pmpQuadTechn
    pact_diag = qp[qp.group1 == qp.group2].pivot_table(
        index="model_region", columns="group1", values="value", aggfunc="last")

    rows = []
    for region in techn.index:
        if region not in areas.index or region not in yields.index:
            continue
        levels = areas.loc[region]
        arable_total = float(levels.reindex(
            [a for a in ARABLE_ACTIVITIES if a in levels.index]).fillna(0.0).sum())
        st = share_term(levels, arable_total, ARABLE_ACTIVITIES)

        for act in techn.columns:
            q_t = techn.at[region, act]
            if not np.isfinite(q_t) or q_t <= 0:
                continue

            is_livestock = act in LIVESTOCK

            # price: regional CAPRI where available (same for both)
            price = np.nan
            if region in prices.index and act in prices.columns:
                price = prices.at[region, act]
            if not np.isfinite(price) or price <= 0:
                continue

            if is_livestock:
                # level = herd size, yield = output per head from capreg
                if act not in herds.columns or region not in herds.index:
                    continue
                levl = herds.at[region, act]
                if act not in ls_yields.columns or region not in ls_yields.index:
                    continue
                yld = ls_yields.at[region, act]
            else:
                if act not in areas.columns or areas.at[region, act] <= 0:
                    continue
                if act not in yields.columns:
                    continue
                levl = areas.at[region, act]
                yld = yields.at[region, act]

            if not np.isfinite(yld) or yld <= 0 or not np.isfinite(levl) or levl <= 0:
                continue

            revenue = yld * price     # EUR per unit of activity (per ha or per head)
            grp = EPRD_TO_GRP.get(act)
            q_p = 0.0
            if grp and region in pact_diag.index and grp in pact_diag.columns:
                v = pact_diag.at[region, grp]
                if np.isfinite(v):
                    q_p = float(v)

            denom = levl * float(st.get(act, 1.0)) * (q_t + q_p)
            if denom <= 0:
                continue
            rows.append((region, act, revenue / denom))

    df = pd.DataFrame(rows, columns=["region", "activity", "elas"])
    df = df[np.isfinite(df.elas) & (df.elas > 0)]
    wide = df.pivot_table(index="region", columns="activity", values="elas")
    print(f"derived: {wide.shape[0]} regions x {wide.shape[1]} activities, "
          f"{int(wide.notna().sum().sum()):,} values")

    # ---- validation against PELA where both exist -----------------------
    both = [a for a in wide.columns if a in pela.columns]
    regs = [r for r in wide.index if r in pela.index]
    checks = []
    for a in both:
        x = wide.loc[regs, a]
        y = pela.loc[regs, a]
        m = x.notna() & y.notna() & (y > 0)
        if m.sum() >= 20:
            ratio = (x[m] / y[m]).median()
            corr = x[m].corr(y[m])
            checks.append((a, int(m.sum()), round(float(ratio), 2),
                           round(float(corr), 2)))
    chk = pd.DataFrame(checks, columns=["activity", "n", "median_ratio", "corr"])
    print("\nvalidation against PELA where both exist "
          "(ratio near 1 and positive correlation = the derivation works):")
    print(chk.to_string(index=False))
    if len(chk):
        print(f"\n  median ratio across activities : {chk.median_ratio.median():.2f}")
        print(f"  median correlation             : {chk['corr'].median():.2f}")

    new_only = [a for a in wide.columns if a not in pela.columns]
    print(f"\nactivities PELA does not cover, now derivable: {len(new_only)}")
    summary = wide[new_only].median().round(2).sort_values(ascending=False)
    print(summary.to_string())

    out = dd / "sources" / "capreg" / "derived_elasticities_from_pmp.csv"
    wide.to_csv(out)
    print(f"\nwritten: {out}")

    if not args.write:
        print("\n[not merged] pass --write to extend "
              "supply_elasticities_regional.csv with the uncovered activities")
        return

    merged = pela.copy()
    added = 0
    for a in new_only:
        if a not in merged.columns:
            merged[a] = np.nan
        for r in wide.index:
            if r in merged.index and np.isfinite(wide.at[r, a]):
                merged.at[r, a] = float(dampen_elasticity([wide.at[r, a]])[0])
                added += 1
    merged.to_csv(dd / "2017/supply/supply_elasticities_regional.csv")
    print(f"\nmerged {added:,} derived values for {len(new_only)} activities")


if __name__ == "__main__":
    main()
