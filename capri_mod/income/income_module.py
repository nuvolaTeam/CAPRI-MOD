"""Farm income by region, as CAPRI's reports compute it.

What it computes
----------------
For each region, agricultural income as CAPRI's reports compute it (reports/welfare.gms, ProfitAgr): the sum over
activities of the market gross value added including premiums, MGVA = TOOU + PRME - TOIN (capinv.gms), times the
activity level:

    farm income     = sum_a (revenue_a - input cost_a + premium_a) x level_a   [EUR 1000]
    public support  = sum_a premium_a x level_a          (CAPRI's PRME: the premiums attached to the activities)
    market income   = farm income - public support

The policy module's CAP payments (DirectPaymentsEngine, pillars 1 and 2) are reported beside the income
(cap_payments_policy), not added to it: the premiums are in the net revenues already (until 27 October 2026 they were
counted twice).

A scenario's income here is at the activities' base unit margins (KNOWN_ISSUES K205): the solved ration, the fodder's
scenario value and the mitigation options' items are not in it yet (to be fixed by CAPRI's activity income,
reports/calc_inc_indic.gms).

Removed on 24 November 2026 (the project lead: follow CAPRI where a decision was pending): the distribution measures
across regions (the support share, income per hectare, a Gini coefficient of income and of payments, the top decile's
share). CAPRI's reports have no such measures; they were CAPRI-MOD's own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np
import pandas as pd


@dataclass
class IncomeResult:
    """Regional farm income."""

    by_region: pd.DataFrame          # region x {market_income, public_support, farm_income, cap_payments_policy}
    notes: Dict = field(default_factory=dict)


class IncomeDistributionModule:
    """Compute farm income by region (CAPRI's ProfitAgr form). The name is the module's since its start; the
    distribution measures it was named after were removed on 24 November 2026 (module docstring).

    Parameters
    ----------
    data : dict
        The model data dict.
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
        # CAPRI's crop technologies: the net revenue and premium of T1 less T2 on the area moved to T1 (z); the
        # premium difference is prem_diff_share x the crop's premium (supply/techn_mix.py)
        mz = dict(getattr(res, "technology_mix", None) or {})
        dnr = dict(getattr(getattr(m, "ev", None), "mix_dnr", None) or {})
        tm = getattr(getattr(m, "data", None), "techn_mix", None)
        inc_z = sum(float(dnr.get(a, 0.0)) * z for a, z in mz.items())
        prem_z = sum(float(tm.at[a, "prem_diff_share"]) * float(pr.get(a, 0.0)) * z
                     for a, z in mz.items() if tm is not None and a in tm.index)
        # CAPRI's ProfitAgr (reports/welfare.gms l. 448-449: market/equations/welfare.py p_welfareRes_ProfitAgr)
        from capri_mod.market.equations.welfare import p_welfareRes_ProfitAgr
        return (p_welfareRes_ProfitAgr([float(nr[a]) for a in nr.index], [lev[a] for a in nr.index]) + inc_z,
                float(sum(float(pr.get(a, 0.0)) * lev[a] for a in nr.index)) + prem_z)

    def compute(self,
                supply_results: Dict,
                supply_module,
                cap_payments_by_region: Optional[pd.DataFrame] = None) -> IncomeResult:
        """Regional farm income (CAPRI's ProfitAgr form).

        Parameters
        ----------
        supply_results : dict[region -> SupplyResult]
            Each carries ``activities`` (solved levels).
        supply_module : SupplyModule
            The module that solved them: its regional models carry the net revenues and premiums per activity.
        cap_payments_by_region : DataFrame, optional
            ``DirectPaymentsEngine.compute_payments_by_region``: its ``total_payments`` (EUR 1000) are reported beside
            the income for comparison (cap_payments_policy), not added to it.
        """
        rows = []
        for region, res in supply_results.items():
            income, support = self._income_parts(region, res, supply_module)
            pol = (float(cap_payments_by_region.at[region, "total_payments"])
                   if cap_payments_by_region is not None and region in cap_payments_by_region.index else np.nan)
            rows.append({
                "region": region,
                "market_income": income - support,
                "public_support": support,
                "farm_income": income,
                "cap_payments_policy": pol,
            })
        df = pd.DataFrame(rows).set_index("region")
        return IncomeResult(by_region=df, notes={"n_regions": int(len(df))})
