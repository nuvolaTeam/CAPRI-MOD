"""Farm-income distribution — regional income and its concentration.

What it computes
----------------
For each region, agricultural income as CAPRI's reports compute it (reports/welfare.gms, ProfitAgr): the sum over
activities of the market gross value added including premiums, MGVA = TOOU + PRME - TOIN (capinv.gms), times the
activity level:

    farm income     = sum_a (revenue_a - input cost_a + premium_a) x level_a   [EUR 1000]
    public support  = sum_a premium_a x level_a          (CAPRI's PRME: the premiums attached to the activities)
    market income   = farm income - public support

Fodder is an internal flow: the supply module values it in the fodder balance rows, not in the activities' net
revenues, so it is neither a revenue of the fodder crops nor a cost of the animals here, as in CAPRI's sum, where the
fodder's output value and the animals' fodder cost cancel.

From the regional vector it derives the distributional measures CAP debates turn
on: the share of income that comes from public support (the "support
dependency"), income per hectare, and the concentration of both income and
payments across regions (a Gini coefficient and top-decile share).

Until 27 October 2026 the module added the policy module's CAP payments (DirectPaymentsEngine, pillars 1 and 2) to
the sum of the net revenues, which already hold CAPRI's premiums: the premiums were counted twice. It also left
grassland out, for a fresh-matter yield artefact that no longer exists. The policy module's payments are now reported
beside the income (cap_payments_policy), not added to it.

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

    def _income_parts(self, region, res, supply_module):
        """(farm income, premiums) in EUR 1000: sum over activities of net revenue x level and of premium x level.
        Net revenues are per ha or per head in EUR; levels in 1000 ha or 1000 heads."""
        acts = getattr(res, "activities", None)
        m = getattr(supply_module, "_models", {}).get(region)
        if m is None or acts is None:
            raise ValueError(f"{region}: no solved supply model (run the supply module for the region first)")
        nr, pr = m.net_revenues, getattr(m, "premiums", None)
        if pr is None:
            raise ValueError(f"{region}: the supply model carries no premiums")
        lev = {a: float(acts.get(a, 0.0)) for a in nr.index}
        return (float(sum(float(nr[a]) * lev[a] for a in nr.index)),
                float(sum(float(pr.get(a, 0.0)) * lev[a] for a in nr.index)))

    def compute(self,
                supply_results: Dict,
                supply_module,
                cap_payments_by_region: Optional[pd.DataFrame] = None) -> IncomeResult:
        """Regional farm income (CAPRI's ProfitAgr form) and its distribution.

        Parameters
        ----------
        supply_results : dict[region -> SupplyResult]
            Each carries ``activities`` (solved levels).
        supply_module : SupplyModule
            The module that solved them: its regional models carry the net revenues and premiums per activity.
        cap_payments_by_region : DataFrame, optional
            ``DirectPaymentsEngine.compute_payments_by_region``: its ``total_payments`` (EUR 1000) are reported beside
            the income for comparison (cap_payments_policy), not added to it; its ``UAA_1000ha`` is the area for the
            per-hectare measures. Without it the area is the region's solved crop area.
        """
        rows = []
        for region, res in supply_results.items():
            income, support = self._income_parts(region, res, supply_module)
            acts = res.activities
            if cap_payments_by_region is not None and region in cap_payments_by_region.index:
                pol = float(cap_payments_by_region.at[region, "total_payments"])
                uaa = float(cap_payments_by_region.at[region, "UAA_1000ha"])
            else:
                pol = np.nan
                uaa = float(sum(float(acts.get(c, 0.0)) for c in self.data["areas"].columns))
            rows.append({
                "region": region,
                "market_income": income - support,
                "public_support": support,
                "farm_income": income,
                "cap_payments_policy": pol,
                "UAA_1000ha": uaa,
                "support_share": (support / income) if income > 0 else np.nan,
                "income_per_ha": (income / uaa) if uaa and uaa > 0 else np.nan,
            })
        df = pd.DataFrame(rows).set_index("region")

        total_income = df["farm_income"].sum()           # (until 27 October 2026 regions with a loss counted as 0)
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
