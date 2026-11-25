"""Farm income by region, as CAPRI's reports compute it (reports/welfare.gms ProfitAgr over the activities' MGVA),
with the policy module's CAP payments reported beside it (capri_mod/income/income_module.py)."""
from .income_module import IncomeDistributionModule, IncomeResult

__all__ = ["IncomeDistributionModule", "IncomeResult"]
