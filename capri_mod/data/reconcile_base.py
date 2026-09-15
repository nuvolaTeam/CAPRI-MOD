"""Base-year reconciliation — reproducing CAPRI's `coco`/`capreg` step.

Why this exists
---------------
CAPRI's value is not its numbers but that they are *internally consistent*:
`coco` and `capreg` solve a Highest Posterior Density problem, minimising
squared deviations from raw statistical sources subject to accounting
identities. Everything downstream — PMP calibration, market balancing, the
nutrient accounts — assumes that has already happened.

This module does the same job on raw data, so a base year can be built from
public statistics rather than a CAPRI GDX. It is the difference between "we
depend on CAPRI's data" and "we can reproduce CAPRI's reconciliation".

The method
----------
Weighted least squares projection onto the identity set, the same family
`projection/reconcile.py` already uses for the forward projection: find the
nearest feasible point to the raw data, weighting by magnitude so large entries
absorb more of the correction, and holding entries non-negative.

What is deliberately NOT done
-----------------------------
The land identity is **not** enforced as an equality. It measurably does not
hold in this data: only 64 of 248 regions have a cropped-area-to-land ratio
within 10% of 1.0, with outliers at 426x and 14x. GRAS is both a land type and
an activity, and city-states measure the two on different bases. Forcing an
equality there would not reconcile the data, it would rewrite it — which is
exactly what an early version of the projection reconciler did, adjusting 248
regions by a 122% mean before the null test caught it.

Instead the land relation is treated as a *bound* (see
``SupplyModel._build_constraints``), and reconciliation targets the identities
that genuinely hold.

Validation
----------
The archive carries three vintages of the same 248x29 area matrix: raw Eurostat,
COCO-reconciled, and CAPRI final. That gives a real test — reconcile the Eurostat
matrix and measure how much of the distance to CAPRI's own result is recovered.
See ``tools/validate_reconciliation.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Sequence

import numpy as np
import pandas as pd


@dataclass
class ReconciliationResult:
    """Reconciled data plus an account of what moved and why."""

    areas: pd.DataFrame
    adjustments: pd.DataFrame          # reconciled - raw
    diagnostics: Dict = field(default_factory=dict)

    def summary(self) -> str:
        adj = self.adjustments.abs()
        tot = float(self.areas.sum().sum())
        moved = float(adj.sum().sum())
        return (f"reconciled {self.areas.shape[0]} regions x "
                f"{self.areas.shape[1]} activities; "
                f"{moved:,.0f} kha moved ({moved / tot * 100:.1f}% of total)")


def _project_to_total(raw: np.ndarray, total: float,
                      weights: Optional[np.ndarray] = None) -> np.ndarray:
    """Nearest non-negative vector to ``raw`` summing to ``total``.

    Weighted least squares with one equality constraint, solved in closed form,
    then clipped at zero and re-solved on the free set. Proportional weighting
    by default, so large entries absorb more of the correction — the same
    principle as CAPRI weighting deviations by magnitude.
    """
    x = np.asarray(raw, dtype=float).copy()
    if x.size == 0:
        return x
    if weights is None:
        weights = np.maximum(np.abs(x), 1e-6)
    w = np.asarray(weights, dtype=float).copy()

    free = np.ones_like(x, dtype=bool)
    for _ in range(x.size + 1):
        gap = total - x[~free].sum()
        wf = w[free]
        if wf.sum() <= 0:
            break
        adj = x.copy()
        adj[free] = x[free] + wf / wf.sum() * (gap - x[free].sum())
        neg = adj < 0
        if not neg.any() or not (neg & free).any():
            x = np.maximum(adj, 0.0)
            break
        x[neg & free] = 0.0
        free = free & ~neg
        if not free.any():
            break
    return np.maximum(x, 0.0)


def reconcile_areas(
    raw_areas: pd.DataFrame,
    regional_totals: Optional[pd.Series] = None,
    national_totals: Optional[pd.DataFrame] = None,
    region_to_country=None,
) -> ReconciliationResult:
    """Reconcile a raw region x activity area matrix.

    Two identities are enforced, both of which genuinely hold in agricultural
    statistics:

    1. **Regional totals** — each region's activities sum to its reported total
       cropped area, where such a total is given.
    2. **National consistency** — regional areas sum to the national figure per
       activity, which is the identity national statistics actually publish and
       regional breakdowns routinely violate.

    Neither forces the land bound, for the reason given in the module docstring.

    Parameters
    ----------
    raw_areas : region x activity, the unreconciled source
    regional_totals : optional per-region total cropped area
    national_totals : optional country x activity national areas
    region_to_country : callable mapping a region code to a country code;
        defaults to the first two characters (NUTS convention)
    """
    if region_to_country is None:
        def region_to_country(reg):  # noqa: E306
            return str(reg)[:2]

    out = raw_areas.copy().astype(float)
    diag: Dict = {"identities": []}

    # --- 2. national consistency, applied first because it is the identity
    # national statistics publish and regional detail is the weaker source ---
    if national_totals is not None:
        diag["identities"].append("national_totals")
        n_adj = 0
        for country in national_totals.index:
            members = [r for r in out.index
                       if region_to_country(r) == country]
            if not members:
                continue
            for act in out.columns:
                if act not in national_totals.columns:
                    continue
                target = float(national_totals.at[country, act])
                if not np.isfinite(target) or target < 0:
                    continue
                col = out.loc[members, act].to_numpy(dtype=float)
                if col.sum() <= 0 and target <= 0:
                    continue
                out.loc[members, act] = _project_to_total(col, target)
                n_adj += 1
        diag["national_cells_adjusted"] = n_adj

    # --- 1. regional totals ---
    if regional_totals is not None:
        diag["identities"].append("regional_totals")
        n_adj = 0
        for reg in out.index:
            if reg not in regional_totals.index:
                continue
            target = float(regional_totals[reg])
            if not np.isfinite(target) or target <= 0:
                continue
            row = out.loc[reg].to_numpy(dtype=float)
            out.loc[reg] = _project_to_total(row, target)
            n_adj += 1
        diag["regional_rows_adjusted"] = n_adj

    adjustments = out - raw_areas.astype(float)
    diag["total_moved_kha"] = float(adjustments.abs().sum().sum())
    return ReconciliationResult(areas=out, adjustments=adjustments,
                                diagnostics=diag)


def null_check(raw_areas: pd.DataFrame, **kwargs) -> float:
    """Reconciling already-consistent data must change nothing.

    Returns the maximum absolute change. This is the gate that catches a
    reconciler which rewrites rather than reconciles — the failure mode that
    hit the projection reconciler, where 248 regions moved by a 122% mean
    before anyone noticed.
    """
    totals = raw_areas.sum(axis=1)
    res = reconcile_areas(raw_areas, regional_totals=totals, **kwargs)
    return float((res.areas - raw_areas).abs().to_numpy().max())
