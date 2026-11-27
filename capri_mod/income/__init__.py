"""Farm income by region, as CAPRI's reports compute it (reports/welfare.gms ProfitAgr over the activities' MGVA),
with the policy module's CAP payments reported beside it (capri_mod/income/income_module.py); CAPRI's gross account
by item at the regional solution (eaa.py, income I2) and its premium outlays per product (feoga.py, income I4)."""
from .income_module import IncomeDistributionModule, IncomeResult

__all__ = ["IncomeDistributionModule", "IncomeResult"]
