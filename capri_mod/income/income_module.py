"""Farm-income distribution — regional income and its concentration.

What it computes
----------------
For each region, agricultural income is split into two transparent parts:

    market income   = supply gross margin (revenue - variable cost)   [EUR 1000]
    public support  = total CAP payments (BISS, eco-scheme, ANC, ...)  [EUR 1000]
    farm income     = market income + public support

From the regional vector it derives the distributional measures CAP debates turn
on: the share of income that comes from public support (the "support
dependency"), income per hectare, and the concentration of both income and
payments across regions (a Gini coefficient and top-decile share).

Why this is a faithful, buildable module
----------------------------------------
It is an *accounting* layer over quantities the model already computes and
validates — supply gross margins and policy CAP payments — not a new economic
estimation. It introduces no unvalidated data. It deliberately reports
distribution *across regions* (which the model resolves), and does NOT claim
distribution across farms or farm sizes: that needs farm-structure (FADN) data
the model does not carry, and inventing it would be exactly the kind of
plausible-but-unfounded detail this project avoids. The regional distribution is
the honest, data-backed statement.

Interpretation guidance
-----------------------
Like the rest of CAPRI-mod, this is comparative-static: it reports the income
distribution *at the base year, or under a policy increment relative to it*. A
scenario's value is the *change* in the distribution (e.g. "capping BISS raises
the support share in region X, lowers concentration by Y"), read against the
base, not an absolute forecast of farm incomes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np
import pandas as pd


@dataclass
class IncomeResult:
    """Regional farm income and its distribution."""

    by_region: pd.DataFrame          # region x {market_income, support, income, ...}
    support_share_eu: float          # EU-wide share of income from CAP support
    income_gini: float               # concentration of farm income across regions
    payment_gini: float              # concentration of CAP payments across regions
    income_per_ha_eu: float          # EU average farm income per hectare
    top_decile_income_share: float   # income share of the top 10% of regions
    notes: Dict = field(default_factory=dict)


def _gini(values: np.ndarray) -> float:
    """Gini coefficient of a non-negative vector (0 = equal, 1 = concentrated).

    Standard mean-absolute-difference formulation. Negative entries (a region
    with a market loss before support) are floored at zero for the concentration
    measure, since a Gini is defined on non-negative masses; the raw incomes are
    still reported per region in ``by_region``.
    """
    v = np.sort(np.clip(np.asarray(values, dtype=float), 0, None))
    n = v.size
    if n == 0 or v.sum() == 0:
        return 0.0
    cum = np.cumsum(v)
    # Gini = (2 * sum(i * v_i) / (n * sum(v))) - (n + 1) / n
    idx = np.arange(1, n + 1)
    return float((2.0 * np.sum(idx * v) / (n * cum[-1])) - (n + 1.0) / n)


class IncomeDistributionModule:
    """Compute farm income by region and its distribution.

    Parameters
    ----------
    data : dict
        The model data dict (for land areas, used for per-hectare measures).
    """

    def __init__(self, data: dict):
        self.data = data

    def _market_income(self, region, res, supply_module) -> float:
        """Clean market income (EUR 1000) = sum(net_revenue_per_unit x level).

        Uses the supply module's per-region net revenues and the solved activity
        levels. Falls back to the SupplyResult's gross_margin only if no supply
        module is provided (noting that value is the PMP objective, not a clean
        income figure).

        Grassland (GRAS) is excluded: it is on-farm fodder consumed by livestock,
        not a marketed output, and its "net revenue" carries a fresh-matter
        yield-unit artifact (yield ~18000 kg/ha) that would otherwise dominate the
        total. Excluding it both matches the economics (grass income is realised
        through the livestock it feeds, already counted) and avoids the artifact.
        """
        EXCLUDE = {"GRAS"}
        acts = getattr(res, "activities", None)
        if supply_module is not None and acts is not None:
            m = getattr(supply_module, "_models", {}).get(region)
            if m is not None:
                nr = m.net_revenues
                return float(sum(
                    float(nr.get(a, 0.0)) * float(acts.get(a, 0.0))
                    for a in getattr(m, "acts", nr.index) if a not in EXCLUDE))
        return float(getattr(res, "gross_margin", 0.0) or 0.0)

    def compute(self,
                supply_results: Dict,
                cap_payments_by_region: pd.DataFrame,
                supply_module=None) -> IncomeResult:
        """Combine supply gross margins with CAP payments into regional income.

        Parameters
        ----------
        supply_results : dict[region -> SupplyResult]
            Each carries ``activities`` and ``gross_output``.
        cap_payments_by_region : DataFrame
            Output of ``DirectPaymentsEngine.compute_payments_by_region`` — must
            carry ``total_payments`` (EUR 1000) and ``UAA_1000ha``.
        supply_module : SupplyModule, optional
            If given, market income is computed cleanly as
            sum(net_revenue_per_unit x activity_level) per region, in EUR 1000.
            This is preferred over ``SupplyResult.gross_margin``, which is the
            PMP *objective value* (it includes the calibrated quadratic cost term
            and is not a directly interpretable income figure).
        """
        rows = []
        for region, res in supply_results.items():
            market = self._market_income(region, res, supply_module)
            if region in cap_payments_by_region.index:
                support = float(cap_payments_by_region.at[region, "total_payments"])
                uaa = float(cap_payments_by_region.at[region, "UAA_1000ha"])
            else:
                support, uaa = 0.0, np.nan
            income = market + support
            rows.append({
                "region": region,
                "market_income": market,
                "public_support": support,
                "farm_income": income,
                "UAA_1000ha": uaa,
                "support_share": (support / income) if income > 0 else np.nan,
                "income_per_ha": (income / uaa) if uaa and uaa > 0 else np.nan,
            })
        df = pd.DataFrame(rows).set_index("region")

        total_income = df["farm_income"].clip(lower=0).sum()
        total_support = df["public_support"].sum()
        support_share_eu = (total_support / total_income) if total_income > 0 else np.nan

        income_gini = _gini(df["farm_income"].values)
        payment_gini = _gini(df["public_support"].values)

        total_uaa = df["UAA_1000ha"].sum(skipna=True)
        income_per_ha_eu = (total_income / total_uaa) if total_uaa > 0 else np.nan

        # top-decile share of farm income across regions
        inc = df["farm_income"].clip(lower=0).sort_values(ascending=False)
        n_top = max(1, int(round(0.10 * len(inc))))
        top_decile_share = (inc.iloc[:n_top].sum() / inc.sum()) if inc.sum() > 0 else np.nan

        return IncomeResult(
            by_region=df,
            support_share_eu=float(support_share_eu),
            income_gini=float(income_gini),
            payment_gini=float(payment_gini),
            income_per_ha_eu=float(income_per_ha_eu),
            top_decile_income_share=float(top_decile_share),
            notes={
                "n_regions": int(len(df)),
                "scope": "distribution ACROSS REGIONS; not across farms/farm-sizes "
                         "(needs FADN farm-structure data the model does not carry)",
                "interpretation": "comparative-static — read the CHANGE in the "
                                  "distribution under a policy increment against the "
                                  "base, not as an absolute income forecast",
            },
        )
