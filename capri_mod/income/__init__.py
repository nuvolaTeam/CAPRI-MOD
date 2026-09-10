"""Farm-income distribution module.

Computes agricultural income by region and its distribution, combining market
gross margin (from the supply module) with CAP payments (from the policy module).
Answers the distributional questions CAP analysis turns on: how income is spread
across regions, and how much of it comes from public support rather than the
market.
"""
from .income_module import IncomeDistributionModule, IncomeResult

__all__ = ["IncomeDistributionModule", "IncomeResult"]
