"""
CAPRI-faithful handling of regional PMP supply elasticities.

This module ports four pieces of CAPRI logic that the Python calibrator either
approximated or omitted, and adds an explicit provenance record so that no
region x activity can silently inherit a default again.

Sources in the CAPRI GAMS tree:
  gams/supply/pmp_terms/impose_upper_bound_on_elasticity.gms  (dampening, share term)
  gams/sets.gms:2918                                          (EPRD_TO_GRP)

The four pieces
---------------
1. Dampening. CAPRI does not truncate high elasticities. Above p_elasHigh = 4.5
   it inflates the PMP quadratic slope so the effective elasticity becomes
   min(8, sqrt(e) + 4.5 - sqrt(4.5)); the source comment gives 10 -> 5.6,
   20 -> 7.0, 40 -> 8. The Python code used min(e, ELAS_HIGH / dampen) = 2.25,
   which both truncates legitimate values in (2.25, 4.5] and over-dampens
   everything above 4.5.

2. Share term. CAPRI scales the curvature of crop activities by
   1 - 0.2 * sqrt(LEVL_activity / arable_total), so a crop occupying a large
   share of the region's arable land gets a flatter response. Non-crop
   activities take 1.0.

3. Crop-to-group mapping (EPRD_TO_GRP), needed to attach the cross-group PMP
   terms. Taken verbatim from gams/sets.gms; the variant in gams/capdis/sets.gms
   uses a different group set and must not be used here.

4. Provenance. Every region x activity elasticity is recorded as REGIONAL_CAPRI, PMP_CAPRI,
   CAPRI_COUNTRY (member state's calibrated value), CAPRI_CAL_PRODUCT (livestock: the product's
   calibrated elasticity) or NO_CAPRI_VALUE, and written out for audit.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
from capri_mod.params import param, param_table
from capri_mod.data.definitions import MS_CODE
from capri_mod.csvio import read_csv

# --- 1. dampening ----------------------------------------------------------

ELAS_HIGH = param("ELAS_HIGH")      # p_elasHigh
ELAS_CAP = param("ELAS_CAP")        # MIN(8, ...)


def dampen_elasticity(eps):
    """CAPRI's heuristic upper bound. Values at or below ELAS_HIGH pass through."""
    e = np.asarray(eps, dtype=float)
    damped = np.minimum(ELAS_CAP, np.sqrt(np.maximum(e, 0.0))
                        + ELAS_HIGH - np.sqrt(ELAS_HIGH))
    return np.where(e > ELAS_HIGH, damped, e)


# --- 2. share term ---------------------------------------------------------

SHARE_COEF = param("SHARE_COEF")


def share_term(activity_levels: pd.Series, arable_total: float,
               crop_activities: set) -> pd.Series:
    """1 - 0.2*sqrt(share of arable) for crops, 1.0 otherwise."""
    out = pd.Series(1.0, index=activity_levels.index, dtype=float)
    if arable_total and arable_total > 0:
        for a in activity_levels.index:
            if a in crop_activities:
                share = max(float(activity_levels.get(a, 0.0)), 0.0) / arable_total
                out[a] = max(1.0 - SHARE_COEF * np.sqrt(min(share, 1.0)), 0.1)
    return out


# --- 3. crop -> PMP group (gams/sets.gms:2918) -----------------------------

EPRD_TO_GRP: Dict[str, str] = {
    "SWHE": "CERE", "DWHE": "CERE", "RYEM": "CERE", "BARL": "CERE", "OATS": "CERE",
    "MAIZ": "CER2", "CORN": "CER2", "OCER": "CER2", "PARI": "CER2",
    "RAPE": "OILS", "SUNF": "OILS", "SOYA": "OILS",
    "PULS": "OARA", "POTA": "OARA", "SUGB": "OARA",
    "MAIF": "FARA", "ROOF": "FARA", "OFAR": "FARA",
    "OFOD": "FARA",          # the model's OFOD is CAPRI's OFAR (other fodder on arable land)
}

# Activities on arable land, used for the share term denominator. Permanent
# crops, grassland and livestock are excluded.
ARABLE_ACTIVITIES = set(EPRD_TO_GRP) | {"SETA", "OFOD", "TEXT", "TOBA"}


# --- 4a. synthetic-anchor guard --------------------------------------------

def detect_synthetic_base_activities(base_areas: pd.DataFrame,
                                     min_regions: int = 30) -> set:
    """
    Activities whose base level is a constant placeholder across all regions.

    A real elasticity calibrated around a fake base level produces a real-looking
    but meaningless response: PMP curvature scales as 1/(eps * x0), so a small
    invented x0 combined with a large genuine eps makes the activity explode under
    any shock. In this dataset COTT, OFIB, OFOD and SETA are flat constants
    (1.0, 2.0, 3.0, 5.0 kha in every region), and OFOD carries a real CAPRI
    elasticity of 4.27 against a default of 0.12 — a 35x jump on a fictional
    anchor, which drove a +128% acreage response in the shock test.

    Note that the lognormal fingerprint detector cannot see these: it looks for
    a coefficient of variation near 0.10, and these columns have a CV of exactly
    zero.
    """
    synthetic = set()
    for col in base_areas.columns:
        v = base_areas[col].replace(0, np.nan).dropna()
        if len(v) >= min_regions and float(v.std()) < 1e-9:
            synthetic.add(col)
    return synthetic


# --- 4b. provenance-tracked elasticity table --------------------------------

#: Elasticity source files, resolved through the loaders' base-year-aware
#: lookup rather than a hard-coded "2017/..." path. Baking the year in here
#: meant re-basing the model to another year silently fell back to the
#: literature defaults, because these two paths would no longer exist.
REGIONAL_FILE = "supply_elasticities_regional.csv"
PMP_ELAS_FILE = "pmp_own_price_elasticities.csv"
COUNTRY_ELAS_FILE = "capri_own_price_elasticities.csv"
#: the country file's CAPRI codes -> model activities (animal products and young animals are not activities)
COUNTRY_ELAS_ALIASES = {"MAIZ": "CORN", "TWIN": "WINE"}
CROSSWALK = "shared/nuts_crosswalk.json"

# CAPRI names grain maize MAIZ; the model calls it CORN. Fodder on arable land OFAR is the model's OFOD (OFAR + ROOF;
# CAPRI's sources carry OFAR only): without the alias the 14 Mha of other fodder stayed on the literature default
# 0.12 against CAPRI's median 1.05 (K32).
ACTIVITY_ALIASES = {"MAIZ": "CORN", "OFAR": "OFOD"}
LIVESTOCK_ELAS_FILE = "sources/arm/capri_supply_elas_market_1717.csv"
LIVESTOCK_PRODUCT = {"DCOW": "MILK", "BCOW": "BEEF", "BULL": "BEEF", "HFRS": "BEEF", "CALV": "BEEF",
                     "PIGS": "PORK", "PIGF": "PORK", "LAYS": "EGGS", "BROI": "POUM", "SHGM": "MILK", "SHGF": "SGMT"}
LIVESTOCK_MS = MS_CODE
YOUNG_ELAS_FILE = "sources/arm/capri_supply_elas_young_1720.csv"
#: young animals produced by each cattle activity (CAPRI YCAM/YCAF, YBUL/YHEI, YCOW)
LIVESTOCK_YOUNG = {"DCOW": ("YCAM", "YCAF"), "BCOW": ("YCAM", "YCAF"), "CALV": ("YBUL", "YHEI"), "HFRS": ("YCOW",),
                   "PIGS": ("YPIG",)}   # sows: piglets


def build_elasticity_table(
    data_dir: Path,
    regions,
    activities,
    defaults: pd.Series,
    base_areas: Optional[pd.DataFrame] = None,
    base_year: str = "2017",
) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Return (elasticities, provenance, summary).

    Precedence, highest first:
      REGIONAL_CAPRI    supply_elasticities_regional.csv, already bounded at 4.5
      PMP_CAPRI         pmp_own_price_elasticities.csv, raw, needs dampening
      CAPRI_COUNTRY     crops neither regional source has anywhere: the member state's p_ElasSupp ("CAL")
      CAPRI_CAL_PRODUCT livestock: the product's calibrated p_elasSupp, with the young animals' share
      NO_CAPRI_VALUE     none of the above: no value (NaN); the activity is held at its level unless CAPRI's PMP
                         terms cover it (no literature defaults since 23 October 2026)

    Both CAPRI sources are per region x activity. The second is keyed by CAPRI
    8-character region codes and is resolved through the NUTS crosswalk, which is
    why it reaches regions the first one misses.
    """
    data_dir = Path(data_dir)
    apply_dampening = True        # CAPRI's dampening (impose_upper_bound_on_elasticity.gms)
    # (The runtime guard against activities anchored on a constant placeholder base, detect_synthetic_base_activities,
    # blocked none since the synthetic data was replaced and was removed from here on 23 October 2026; the function
    # stays as a data check, test_capri.py.)
    # no literature defaults (23 October 2026): a cell without a CAPRI value stays NaN, provenance NO_CAPRI_VALUE
    eps = pd.DataFrame(
        np.tile(defaults.reindex(activities).values.astype(float), (len(regions), 1)),
        index=regions, columns=activities, dtype=float)
    prov = pd.DataFrame("NO_CAPRI_VALUE", index=regions, columns=activities)

    # --- lower-precedence source first, so the better one overwrites it ---
    from capri_mod.data.loaders import resolve_data_file
    pmp_path = resolve_data_file(data_dir, PMP_ELAS_FILE, base_year=base_year)
    cw_path = data_dir / CROSSWALK
    n_pmp = 0
    if pmp_path.exists() and cw_path.exists():
        # model region -> CAPRI region: the shared map (tools/build/build_region_map.py: the NUTS correspondence with its
        # fixes, splits and merges), else the crosswalk; a region with neither, or whose CAPRI region has no row,
        # takes its member state's national row (K32: the crosswalk alone reached 140 of 248 regions, so 13 Mha of
        # arable crops in recoded regions - Denmark, Berlin, Saxony, Poland's renamed regions, Finland's - and every
        # national-row region stayed on the literature defaults)
        cw = json.loads(cw_path.read_text())["resolved"]      # model -> CAPRI
        to8 = dict(cw)
        rm = data_dir / "shared" / "region_capri_map.csv"
        if rm.exists():
            for _r in read_csv(rm, dtype=str).fillna("").itertuples(index=False):
                if _r.capri_region:
                    to8[_r.region] = _r.capri_region
        df = read_csv(pmp_path)
        df["activity"] = df["crop"].replace(ACTIVITY_ALIASES)
        df = df[df.activity.isin(set(activities))]
        vals = df["own_price_elas"].values
        if apply_dampening:
            vals = dampen_elasticity(vals)
        val = {(c8, a): float(v) for c8, a, v in zip(df.region, df.activity, vals) if np.isfinite(v) and v > 0}
        for r in regions:
            own = to8.get(r)
            nat = LIVESTOCK_MS.get(str(r)[:2], str(r)[:2]) + "000000"
            for a in set(df.activity):
                if a not in eps.columns:
                    continue
                v = val.get((own, a)) if own else None
                if v is None:
                    v = val.get((nat, a))
                if v is not None:
                    eps.at[r, a] = v
                    prov.at[r, a] = "PMP_CAPRI"
                    n_pmp += 1

    # --- higher-precedence source ---
    reg_path = resolve_data_file(data_dir, REGIONAL_FILE, base_year=base_year)
    n_reg = 0
    if reg_path.exists():
        rdf = read_csv(reg_path, index_col=0)
        rdf = rdf.rename(columns=ACTIVITY_ALIASES)
        common_r = [r for r in rdf.index if r in set(regions)]
        common_a = [c for c in rdf.columns if c in set(activities)]
        for r in common_r:
            for a in common_a:
                v = rdf.at[r, a]
                if pd.notna(v) and v > 0:
                    # This source is already bounded at 4.5 upstream; dampening
                    # it again would be double-counting.
                    eps.at[r, a] = float(v)
                    prov.at[r, a] = "REGIONAL_CAPRI"
                    n_reg += 1

    # --- crops neither regional source has: the member state's calibrated own-price supply elasticity (K30) ---
    # CAPRI's p_ElasSupp ("CAL", results/arm supply_elas_*; capri_own_price_elasticities.csv, 26 country groups).
    # Before October 2026 these crops (permanent crops, vegetables, tobacco, textile crops, table olives) took one
    # EU-wide value each, hand-entered from Spain and Italy (tobacco 0.213 against CAPRI's 0.44 in every member
    # state). Only for activities with no value from the two regional sources anywhere: where those sources miss a
    # region for an arable crop the default stays (registered in docs/KNOWN_ISSUES.md K30). Dampened as the PMP
    # source (values at or below the threshold pass unchanged); a crop the member state does not have keeps the default.
    n_cty = 0
    try:
        from capri_mod.data.loaders import resolve_data_file as _rdf
        cty_path = _rdf(data_dir, COUNTRY_ELAS_FILE, base_year=base_year)
    except Exception:
        cty_path = None
    if cty_path is not None and Path(cty_path).exists():
        cdf = read_csv(cty_path, index_col=0).rename(columns=COUNTRY_ELAS_ALIASES)
        covered = {a for a in prov.columns if prov[a].isin(["PMP_CAPRI", "REGIONAL_CAPRI"]).any()}
        cols_ = [c for c in cdf.columns if c in set(activities) and c not in covered]
        for r in regions:
            cc = LIVESTOCK_MS.get(str(r)[:2], str(r)[:2])
            if cc not in cdf.index:
                continue
            for a in cols_:
                v = cdf.at[cc, a]
                if pd.notna(v) and v > 0:
                    eps.at[r, a] = float(dampen_elasticity([float(v)])[0]) if apply_dampening else float(v)
                    prov.at[r, a] = "CAPRI_COUNTRY"
                    n_cty += 1

    # --- livestock: CAPRI's calibrated supply elasticities of the animal products ---
    # (results/arm/elas_2_1717*: p_elasSupp(MS, product, product, "CAL"), the elasticities
    # CAPRI's supply models are calibrated to reproduce; sources/arm/
    # capri_supply_elas_market_1717.csv). Each animal activity takes its product's
    # own-price value for its member state: dairy cows - milk; suckler cows, bulls, heifers,
    # calves - beef; pigs - pork; hens - eggs; broilers - poultry meat; sheep and goats for
    # fattening (SHGF) - sheep and goat meat; for milk (SHGM) - raw milk (CAPRI's MILK market holds cow
    # and sheep-goat milk; p_elasSupp has no separate SGMI). Replaces the literature priors (0.10-0.25; CAPRI 0.47-0.82).
    n_lsk = 0
    lsk_path = data_dir / LIVESTOCK_ELAS_FILE
    if lsk_path.exists():
        ldf = read_csv(lsk_path)
        ldf = ldf[(ldf["prod"] == ldf["wrt"]) & ldf["prod"].isin(set(LIVESTOCK_PRODUCT.values()))]
        ms_val = {(r, p_): float(v) for r, p_, v in zip(ldf.region, ldf["prod"], ldf.value)}
        # Young animals (calves, young cattle, cows) are part of the cattle activities' output
        # (CAPRI's TOOU minus its market revenue MREV); CAPRI calibrates to their supply
        # elasticities as well. Each activity's elasticity is the value-weighted mean of its
        # final product's and its young animals' (suckler cows: 89% calves in Duesseldorf).
        yel = {}
        ypath = data_dir / YOUNG_ELAS_FILE
        if ypath.exists():
            for r_, i_, v_ in read_csv(ypath).itertuples(index=False):
                yel[(r_, i_)] = float(v_)
        sup = data_dir / base_year / "supply"
        try:
            mrev = read_csv(sup / "livestock_revenue_coef.csv", index_col=0)
            toou = read_csv(sup / "livestock_output_value_coef.csv", index_col=0)
            # the product share is the value of final products (no young animals) in total output:
            # CAPRI's MREV is young-animal sales for sows, raised calves and replacement heifers
            try:
                _pv = read_csv(sup / "livestock_product_value_coef.csv", index_col=0)
                for _a in _pv.columns:
                    if _a in mrev.columns:
                        mrev[_a] = _pv[_a].reindex(mrev.index)
            except Exception:
                pass
        except Exception:
            mrev = toou = None
        for r in regions:
            ms = LIVESTOCK_MS.get(str(r)[:2], str(r)[:2]) + "000000"
            for a, prod_ in LIVESTOCK_PRODUCT.items():
                if a not in eps.columns:
                    continue
                v = ms_val.get((ms, prod_))
                if v is None or not np.isfinite(v) or v <= 0:
                    continue
                young = [yel.get((ms, i_)) for i_ in LIVESTOCK_YOUNG.get(a, ())]
                young = [y_ for y_ in young if y_ is not None and y_ > 0]
                if young and mrev is not None and r in mrev.index and r in toou.index \
                        and a in mrev.columns and a in toou.columns:
                    m_, t_ = float(mrev.at[r, a]), float(toou.at[r, a])
                    if np.isfinite(m_) and np.isfinite(t_) and t_ > 0 and 0 <= m_ <= t_:
                        sy = 1.0 - m_ / t_
                        v = (1.0 - sy) * v + sy * float(np.mean(young))
                eps.at[r, a] = v
                prov.at[r, a] = "CAPRI_CAL_PRODUCT"
                n_lsk += 1

    total = eps.size
    counts = prov.stack().value_counts().to_dict()
    summary = {
        "regions": len(regions),
        "activities": len(activities),
        "cells": int(total),
        "by_provenance": {k: int(v) for k, v in counts.items()},
        "pct_real": round(100 * (total - counts.get("NO_CAPRI_VALUE", 0)) / total, 1),
        "regions_with_any_real": int((prov != "NO_CAPRI_VALUE").any(axis=1).sum()),
        "activities_with_any_real": int((prov != "NO_CAPRI_VALUE").any(axis=0).sum()),
        "dampening_applied": bool(apply_dampening),
        "cells_from_pmp_file": n_pmp,
        "cells_from_country_file": n_cty,
        "cells_from_regional_file": n_reg,
        "cells_from_livestock_products": n_lsk,
    }
    return eps, prov, summary


def asymmetry_report(eps: pd.DataFrame, prov: pd.DataFrame) -> dict:
    """
    Quantify the covered/uncovered elasticity gap.

    Real CAPRI estimates exist only for arable crops. If those are raised while
    permanent crops, grass and livestock keep literature defaults, the arable
    block absorbs a disproportionate share of any adjustment. This is a property
    of the data coverage, not a bug, but it must be visible.
    """
    real = prov != "NO_CAPRI_VALUE"
    covered = eps.where(real).stack()
    uncovered = eps.where(~real).stack()
    ratio = (covered.median() / uncovered.median()) if len(uncovered) else float("nan")
    per_act = {}
    for a in eps.columns:
        m = real[a]
        if m.any():
            per_act[a] = {
                "real_median": round(float(eps.loc[m, a].median()), 3),
                "default": round(float(eps.loc[~m, a].median()), 3) if (~m).any() else None,
                "regions_real": int(m.sum()),
            }
    return {
        "covered_median": round(float(covered.median()), 3) if len(covered) else None,
        "uncovered_median": round(float(uncovered.median()), 3) if len(uncovered) else None,
        "asymmetry_ratio": round(float(ratio), 2),
        "interpretation": (
            "Activities with real CAPRI elasticities respond this many times more "
            "strongly to price than those left on literature defaults. A ratio far "
            "from 1 means scenario adjustment concentrates in the covered block."),
        "per_activity": per_act,
    }
