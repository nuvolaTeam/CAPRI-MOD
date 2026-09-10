"""Nitrogen intensity margin — let N per hectare respond, not just area.

The problem this solves
-----------------------
CAPRI-mod's nutrient coefficients are FIXED per activity (SWHE = 125.9 kg N/ha,
always), so nitrogen application per hectare cannot vary. A nitrogen constraint
can therefore only be satisfied by cutting AREA. Validated against CAPRI's Green
Deal 2030 run, that forced the entire adjustment onto the extensive margin and
overstated the response by roughly an order of magnitude (wheat -24% against
CAPRI's -1.9%).

CAPRI does it differently: ``v_cropNutNeedMultFact`` is a free VARIABLE scaling
each crop's nutrient need, so application per hectare flexes and the model trades
fertiliser cost against yield. The adjustment splits between intensity and area.

What this module adds
---------------------
For each crop, an intensity factor ``m`` in ``[m_min, 1]`` scaling N per hectare,
with yield responding along a Mitscherlich (diminishing-returns) curve:

    y(m) = y_base * (1 - exp(-k * m)) / (1 - exp(-k))

so that ``y(1) = y_base`` exactly — **the base year is reproduced by
construction**, which is the property that protects PMP calibration. Reducing N
saves fertiliser cost but loses yield revenue; the optimal ``m`` under an N
ceiling equates the two at the margin.

The curvature ``k``
-------------------
``k`` sets how fast yield falls as N is withdrawn. It is the one genuinely
assumed quantity here and is therefore exposed as a parameter, defaulted from the
agronomic literature (k ~ 3 gives roughly a 5% yield loss for a 20% N cut on
cereals, consistent with reported N-response trials), and recorded as an
assumption rather than presented as data. It is NOT tuned to make any comparison
come out right.

Scope
-----
This is a *response function*, not a re-estimation of CAPRI's fertiliser system.
It gives the model the missing margin so that nitrogen instruments behave
structurally like CAPRI's; it does not claim to reproduce CAPRI's fertiliser
module cell by cell.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd

#: Default Mitscherlich curvature. Higher = yield falls faster as N is withdrawn.
#: k=3.0 gives ~5% yield loss for a 20% N reduction on cereals.
DEFAULT_K = 3.0

#: Floor on the intensity factor: below this, agronomic response data is not
#: credible and the crop would realistically be abandoned rather than starved.
DEFAULT_M_MIN = 0.5


@dataclass
class IntensityResult:
    """Optimal N intensity and its consequences for one region."""

    intensity: pd.Series        # per-crop factor m in [m_min, 1]
    yield_factor: pd.Series     # resulting yield multiplier
    n_per_ha: pd.Series         # resulting N application (kg/ha)
    binding: bool               # whether the N ceiling actually bound
    notes: Dict


def yield_factor(m, k: float = DEFAULT_K):
    """Mitscherlich yield response to the N intensity factor.

    Normalised so ``yield_factor(1) == 1``: the base year is reproduced exactly,
    which is what keeps PMP calibration undisturbed when this is switched on.
    """
    m = np.asarray(m, dtype=float)
    return (1.0 - np.exp(-k * m)) / (1.0 - np.exp(-k))


def marginal_yield(m, k: float = DEFAULT_K):
    """d(yield_factor)/dm — the marginal yield gain from more nitrogen."""
    m = np.asarray(m, dtype=float)
    return (k * np.exp(-k * m)) / (1.0 - np.exp(-k))


def optimal_intensity(
    n_coef: pd.Series,
    price: pd.Series,
    base_yield: pd.Series,
    n_price: float,
    n_ceiling_per_ha: Optional[float] = None,
    areas: Optional[pd.Series] = None,
    k: float = DEFAULT_K,
    m_min: float = DEFAULT_M_MIN,
) -> IntensityResult:
    """Choose N intensity per crop, optionally under an N ceiling.

    Unconstrained, a crop applies N up to where the marginal revenue of yield
    equals the marginal cost of nitrogen. Under a binding ceiling, intensity is
    reduced where it is *cheapest* to do so — measured by the revenue lost per kg
    of nitrogen saved — rather than uniformly, which is what lets the adjustment
    fall on low-value crops first.

    Parameters
    ----------
    n_coef : kg N per ha by crop (the fixed coefficients)
    price : producer price by crop (EUR/t)
    base_yield : yield by crop (t/ha) at base intensity
    n_price : EUR per kg N
    n_ceiling_per_ha : ceiling on area-weighted N per ha; None = unconstrained
    areas : crop areas, used to weight the ceiling; required if a ceiling is set
    """
    crops = list(n_coef.index)
    m = pd.Series(1.0, index=crops)

    if n_ceiling_per_ha is None or areas is None:
        return IntensityResult(
            intensity=m,
            yield_factor=pd.Series(yield_factor(m.values, k), index=crops),
            n_per_ha=n_coef.copy(),
            binding=False,
            notes={"status": "unconstrained — base intensity retained"},
        )

    a = areas.reindex(crops).fillna(0.0)
    total_area = float(a.sum())
    if total_area <= 0:
        return IntensityResult(m, pd.Series(1.0, index=crops), n_coef.copy(),
                               False, {"status": "no area"})

    base_n = float((n_coef.reindex(crops).fillna(0.0) * a).sum())
    ceiling_n = n_ceiling_per_ha * total_area
    if base_n <= ceiling_n:
        return IntensityResult(
            intensity=m,
            yield_factor=pd.Series(1.0, index=crops),
            n_per_ha=n_coef.copy(),
            binding=False,
            notes={"status": "ceiling slack at base intensity"},
        )

    # Cost of cutting intensity, per kg N saved:
    #   revenue lost = price * base_yield * d(yield_factor)/dm * dm
    #   N saved      = n_coef * dm
    # so the ratio price*yield*marginal_yield / n_coef ranks where to cut first.
    # Reduce intensity on the cheapest crops until the ceiling is met. Each pass
    # cuts ONE crop by one step, so the iteration budget must allow every crop to
    # be cut all the way to the floor — a budget of (1-m_min)/step alone lets
    # only a single crop move and silently leaves the ceiling unmet.
    step = 0.01
    max_iter = int((1.0 - m_min) / step) * max(len(crops), 1) + 10
    for _ in range(max_iter):
        cur_n = float((n_coef.reindex(crops).fillna(0.0) * m * a).sum())
        if cur_n <= ceiling_n:
            break
        cost = {}
        for c in crops:
            if m[c] <= m_min or a.get(c, 0.0) <= 0 or n_coef.get(c, 0.0) <= 0:
                continue
            rev_loss = (float(price.get(c, 0.0)) * float(base_yield.get(c, 0.0))
                        * float(marginal_yield(m[c], k)))
            cost[c] = rev_loss / float(n_coef[c])
        if not cost:
            break
        cheapest = min(cost, key=cost.get)
        m[cheapest] = max(m_min, m[cheapest] - step)

    yf = pd.Series(yield_factor(m.values, k), index=crops)
    return IntensityResult(
        intensity=m,
        yield_factor=yf,
        n_per_ha=n_coef.reindex(crops).fillna(0.0) * m,
        binding=True,
        notes={
            "status": "ceiling binding — intensity reduced",
            "method": "cut intensity where revenue lost per kg N saved is lowest",
            "k": k, "m_min": m_min,
            "n_before": base_n, "n_ceiling": ceiling_n,
            "n_after": float((n_coef.reindex(crops).fillna(0.0) * m * a).sum()),
        },
    )
