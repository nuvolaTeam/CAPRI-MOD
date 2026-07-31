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

4. Provenance. Every region x activity elasticity is recorded as REGIONAL_CAPRI,
   NATIONAL_CAPRI or LITERATURE_DEFAULT, and written out for audit.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

# --- 1. dampening ----------------------------------------------------------

ELAS_HIGH = 4.5      # p_elasHigh
ELAS_CAP = 8.0       # MIN(8, ...)


def dampen_elasticity(eps):
    """CAPRI's heuristic upper bound. Values at or below ELAS_HIGH pass through."""
    e = np.asarray(eps, dtype=float)
    damped = np.minimum(ELAS_CAP, np.sqrt(np.maximum(e, 0.0))
                        + ELAS_HIGH - np.sqrt(ELAS_HIGH))
    return np.where(e > ELAS_HIGH, damped, e)


# --- 2. share term ---------------------------------------------------------

SHARE_COEF = 0.2


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
}

# Activities on arable land, used for the share term denominator. Permanent
# crops, grassland and livestock are excluded.
ARABLE_ACTIVITIES = set(EPRD_TO_GRP) | {"SETA", "OFOD", "COTT", "OFIB", "TOBA"}


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

REGIONAL_FILE = "2017/supply/supply_elasticities_regional.csv"
PMP_ELAS_FILE = "2017/supply/pmp_own_price_elasticities.csv"
CROSSWALK = "shared/nuts_crosswalk.json"

# CAPRI names grain maize MAIZ; the model calls it CORN.
ACTIVITY_ALIASES = {"MAIZ": "CORN"}


def build_elasticity_table(
    data_dir: Path,
    regions,
    activities,
    defaults: pd.Series,
    apply_dampening: bool = True,
    base_areas: Optional[pd.DataFrame] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Return (elasticities, provenance, summary).

    Precedence, highest first:
      REGIONAL_CAPRI    supply_elasticities_regional.csv, already bounded at 4.5
      PMP_CAPRI         pmp_own_price_elasticities.csv, raw, needs dampening
      LITERATURE_DEFAULT the EU-wide per-activity defaults

    Both CAPRI sources are per region x activity. The second is keyed by CAPRI
    8-character region codes and is resolved through the NUTS crosswalk, which is
    why it reaches regions the first one misses.
    """
    data_dir = Path(data_dir)
    # Activities anchored on a synthetic constant base level are held at their
    # literature default: a real elasticity on a fake anchor is worse than a
    # conservative one, because it looks legitimate.
    blocked = (detect_synthetic_base_activities(base_areas)
               if base_areas is not None else set())
    eps = pd.DataFrame(
        np.tile(defaults.reindex(activities).fillna(0.25).values, (len(regions), 1)),
        index=regions, columns=activities, dtype=float)
    prov = pd.DataFrame("LITERATURE_DEFAULT", index=regions, columns=activities)

    # --- lower-precedence source first, so the better one overwrites it ---
    pmp_path = data_dir / PMP_ELAS_FILE
    cw_path = data_dir / CROSSWALK
    n_pmp = 0
    if pmp_path.exists() and cw_path.exists():
        cw = json.loads(cw_path.read_text())["resolved"]      # model -> CAPRI
        rev = {v: k for k, v in cw.items()}
        df = pd.read_csv(pmp_path)
        df["model_region"] = df["region"].map(rev)
        df["activity"] = df["crop"].replace(ACTIVITY_ALIASES)
        df = df.dropna(subset=["model_region"])
        df = df[df.model_region.isin(set(regions)) & df.activity.isin(set(activities))]
        vals = df["own_price_elas"].values
        if apply_dampening:
            vals = dampen_elasticity(vals)
        for r, a, v in zip(df.model_region, df.activity, vals):
            if a in blocked:
                continue
            if np.isfinite(v) and v > 0:
                eps.at[r, a] = float(v)
                prov.at[r, a] = "PMP_CAPRI"
                n_pmp += 1

    # --- higher-precedence source ---
    reg_path = data_dir / REGIONAL_FILE
    n_reg = 0
    if reg_path.exists():
        rdf = pd.read_csv(reg_path, index_col=0)
        rdf = rdf.rename(columns=ACTIVITY_ALIASES)
        common_r = [r for r in rdf.index if r in set(regions)]
        common_a = [c for c in rdf.columns if c in set(activities)]
        for r in common_r:
            for a in common_a:
                if a in blocked:
                    continue
                v = rdf.at[r, a]
                if pd.notna(v) and v > 0:
                    # This source is already bounded at 4.5 upstream; dampening
                    # it again would be double-counting.
                    eps.at[r, a] = float(v)
                    prov.at[r, a] = "REGIONAL_CAPRI"
                    n_reg += 1

    total = eps.size
    counts = prov.stack().value_counts().to_dict()
    summary = {
        "regions": len(regions),
        "activities": len(activities),
        "cells": int(total),
        "by_provenance": {k: int(v) for k, v in counts.items()},
        "pct_real": round(100 * (total - counts.get("LITERATURE_DEFAULT", 0)) / total, 1),
        "regions_with_any_real": int((prov != "LITERATURE_DEFAULT").any(axis=1).sum()),
        "activities_with_any_real": int((prov != "LITERATURE_DEFAULT").any(axis=0).sum()),
        "dampening_applied": bool(apply_dampening),
        "cells_from_pmp_file": n_pmp,
        "cells_from_regional_file": n_reg,
        "activities_blocked_synthetic_base": sorted(blocked),
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
    real = prov != "LITERATURE_DEFAULT"
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
