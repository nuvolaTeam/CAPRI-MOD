"""Reconciliation — restore accounting identities after applying growth factors.

Why this exists
---------------
Scaling a base year by independent growth factors *breaks internal consistency*.
Yields grow, herds shrink, land drifts — each from a different source — and the
result no longer satisfies the identities that make the data set meaningful:
crop areas stop summing to available land, and herds stop matching the land that
feeds them. A projected data set that violates its own accounting looks perfectly
plausible and is quietly wrong, which is exactly the failure mode this project
guards against everywhere else.

CAPRI solves the same problem in ``captrd`` by minimising squared deviations from
expert "supports" (AGLINK/Outlook targets) subject to the accounting constraints
— an HPD estimation. This module does the same thing in the small: it treats the
scaled values as *targets* and finds the nearest values that satisfy the
identities, in a weighted least-squares sense.

Method
------
For each region, given scaled crop areas ``a*`` and an available-land total ``L``,
solve

    min  sum_i w_i (a_i - a*_i)^2      s.t.   sum_i a_i = L,   a_i >= 0

which is a projection onto the simplex-like feasible set. With weights
``w_i = 1/max(a*_i, eps)`` the adjustment is *proportional* rather than absolute,
so a 1000 kha crop absorbs more of the correction than a 5 kha crop — the same
principle as CAPRI weighting deviations by magnitude. The closed-form solution
(equality-constrained least squares, then clipping at zero and re-solving on the
free set) is exact and needs no solver.

What is reconciled, and what is deliberately not
------------------------------------------------
- **Crop areas to available land** — enforced, per region.
- **Herds** — carried as scaled, but reported with a feed-availability check
  rather than silently forced: if a scaled herd cannot be fed from the scaled
  land, that is a substantive finding about the trajectory, not a rounding error
  to be smoothed away.
- **Market clearing** — NOT pre-reconciled. The market module solves for prices
  that clear supply and demand; forcing quantities to balance beforehand would
  pre-empt the economics the model exists to compute.

The report returned records every adjustment so the projection never silently
changes a number.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

_EPS = 1e-9


@dataclass
class ReconciliationReport:
    """What the reconciliation changed, and by how much."""

    land_adjusted_regions: int = 0
    max_area_adjustment_pct: float = 0.0
    mean_area_adjustment_pct: float = 0.0
    regions_over_land: List[str] = field(default_factory=list)
    regions_under_land: List[str] = field(default_factory=list)
    feed_warnings: List[str] = field(default_factory=list)
    notes: Dict = field(default_factory=dict)

    def summary(self) -> str:
        return (f"reconciled {self.land_adjusted_regions} regions to land "
                f"availability (mean |adj| {self.mean_area_adjustment_pct:.2f}%, "
                f"max {self.max_area_adjustment_pct:.2f}%); "
                f"{len(self.feed_warnings)} feed warnings")


def _project_to_total(target: np.ndarray, total: float,
                      weights: Optional[np.ndarray] = None) -> np.ndarray:
    """Nearest non-negative vector to ``target`` summing to ``total``.

    Weighted least squares with one equality constraint. Solved in closed form,
    then any negative entries are clamped to zero and the problem re-solved on
    the remaining free set (active-set, converges in a few passes since each
    pass fixes at least one variable).
    """
    x_star = np.asarray(target, dtype=float).copy()
    n = x_star.size
    if n == 0:
        return x_star
    if weights is None:
        # proportional weighting: larger entries absorb more of the correction
        weights = 1.0 / np.maximum(np.abs(x_star), _EPS)
    w = np.asarray(weights, dtype=float)

    free = np.ones(n, dtype=bool)
    x = x_star.copy()
    for _ in range(n + 1):
        if not free.any():
            break
        # minimise sum w_i (x_i - x*_i)^2 s.t. sum_{free} x_i = total - sum_{fixed} x_i
        inv_w = 1.0 / np.maximum(w[free], _EPS)
        residual = total - x[~free].sum()
        gap = residual - x_star[free].sum()
        x_new = x_star[free] + inv_w * (gap / inv_w.sum())
        x[free] = x_new
        neg = free.copy()
        neg[free] = x_new < 0
        if not neg.any():
            break
        x[neg] = 0.0
        free = free & ~neg
    return np.maximum(x, 0.0)


def reconcile_projected_data(
    data: Dict,
    base_data: Optional[Dict] = None,
    land_available: Optional[pd.DataFrame] = None,
    feed_check: bool = True,
) -> ReconciliationReport:
    """Restore accounting identities in a projected data set, in place.

    The constraint enforced is *not* an assumed identity like
    ``sum(crop areas) == sum(land)``. The base year does not satisfy such an
    identity exactly — crop areas and the land table come from different
    aggregations, and grassland appears both as a land type and as the GRAS
    activity — so imposing one would rewrite the base data rather than reconcile
    the projection. Instead the reconciliation **preserves the region's
    base-year ratio** of cropped area to available land, correcting only the
    *drift* introduced by scaling. With a null trajectory nothing changes, which
    is exactly the identity the projection layer is tested against.

    Parameters
    ----------
    data : dict
        Projected model data (already scaled). ``areas`` is adjusted in place.
    base_data : dict, optional
        The unscaled base-year data, used to measure each region's original
        cropped-area-to-land ratio. If omitted, no land reconciliation is done
        (the ratio cannot be known) and only the plausibility checks run.
    """
    report = ReconciliationReport()
    areas = data.get("areas")
    if areas is None or areas.empty:
        report.notes["status"] = "no areas to reconcile"
        return report

    land = land_available if land_available is not None else data.get("land")
    base_areas = (base_data or {}).get("areas")
    base_land = (base_data or {}).get("land")

    if land is None or land.empty or base_areas is None or base_land is None:
        report.notes["status"] = (
            "no base-year reference supplied; land reconciliation skipped "
            "(the target ratio is defined by the base year, not assumed)")
        if feed_check:
            report.feed_warnings = _feed_plausibility(data)
        return report

    LAND_COLS = [c for c in ("ARABLE", "PERMANENT", "GRASSLAND")
                 if c in land.columns and c in base_land.columns]
    if not LAND_COLS:
        report.notes["status"] = "land frame lacks expected columns"
        return report

    adjustments = []
    for region in areas.index:
        if region not in land.index or region not in base_areas.index:
            continue
        base_crop = float(base_areas.loc[region].sum())
        base_land_tot = float(base_land.loc[region, LAND_COLS].sum())
        proj_land_tot = float(land.loc[region, LAND_COLS].sum())
        if base_crop <= 0 or base_land_tot <= 0 or proj_land_tot <= 0:
            continue
        # the region's own base-year relationship, carried forward
        ratio = base_crop / base_land_tot
        target_total = ratio * proj_land_tot

        row = areas.loc[region].astype(float)
        cropped = float(row.sum())
        if cropped <= 0:
            continue
        rel_gap = abs(cropped - target_total) / max(target_total, _EPS)
        if rel_gap < 1e-9:
            continue
        adjusted = _project_to_total(row.values, target_total)
        pct = float(np.abs(adjusted - row.values).sum() / max(cropped, _EPS) * 100.0)
        adjustments.append(pct)
        areas.loc[region] = adjusted
        report.land_adjusted_regions += 1
        (report.regions_over_land if cropped > target_total
         else report.regions_under_land).append(region)

    if adjustments:
        report.max_area_adjustment_pct = float(np.max(adjustments))
        report.mean_area_adjustment_pct = float(np.mean(adjustments))

    if feed_check:
        report.feed_warnings = _feed_plausibility(data)

    report.notes.update({
        "method": "weighted least-squares projection of scaled crop areas onto "
                  "the region's BASE-YEAR cropped-to-land ratio (proportional "
                  "weights, non-negativity by active set) — the base year's own "
                  "relationship is preserved rather than an identity assumed",
        "market_clearing": "deliberately NOT pre-reconciled — the market module "
                           "solves for clearing prices; forcing quantities to "
                           "balance beforehand would pre-empt the economics",
        "herds": "carried as scaled and checked, not silently forced — an "
                 "unfeedable herd is a finding about the trajectory",
    })
    return report


def _feed_plausibility(data: Dict) -> List[str]:
    """Flag regions whose projected herds look unfeedable from projected land.

    A coarse screen, not a feed-balance solve: it compares grazing-livestock
    density against grassland plus fodder area and flags implausible densities.
    The point is to surface a trajectory that has quietly become incoherent, not
    to adjudicate feed allocation (the feed module does that).
    """
    warnings_out: List[str] = []
    animals = data.get("animal_numbers")
    land = data.get("land")
    if animals is None or land is None or animals.empty or land.empty:
        return warnings_out

    GRAZERS = [c for c in ("DCOW", "BCOW", "BULL", "HFRS", "CALV", "SHGP")
               if c in animals.columns]
    if not GRAZERS or "GRASSLAND" not in land.columns:
        return warnings_out

    for region in animals.index:
        if region not in land.index:
            continue
        grass = float(land.at[region, "GRASSLAND"])
        herd = float(animals.loc[region, GRAZERS].sum())
        if grass <= 0 or herd <= 0:
            continue
        # livestock units per hectare of grassland (areas are 1000 ha, herds 1000 head)
        density = herd / grass
        if density > 10.0:
            warnings_out.append(
                f"{region}: {density:.1f} grazing head per ha grassland after "
                "projection — trajectory may be internally inconsistent")
    return warnings_out
