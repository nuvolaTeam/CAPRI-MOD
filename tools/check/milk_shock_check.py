"""Derived demand for EU raw milk in the market model (K13 diagnosis).

python tools/check/milk_shock_check.py

Runs the 2030 baseline, puts the market in scenario mode with no shock (emission tax 0), then solves the market
alone with EU raw milk delivered cut by 5% and 10% and everything else at the baseline: the change in the EU raw milk
price (dairy block) and in the dairy product prices. October 2026: -5% -> +26%, -10% -> +55% (butter +32%, whey +24%,
cheese +17%): a derived demand elasticity of about -0.2 with CAPRI's own dairy block (p_hessNQDairy, which reproduces
p_ElasDair exactly), food demand (p_ElasDem) and Armington parameters.
"""
import sys, os, pickle, warnings
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2])); warnings.simplefilter("ignore")
from capri_mod.model import CAPRIModel
from capri_mod.market.market_module import MarketModule
CAP = {}
_s = MarketModule.solve
def solve(self, exogenous_supply=None, *a, **k):
    CAP["exo"] = None if exogenous_supply is None else exogenous_supply.copy()
    CAP["seen"] = self.seen.eu_price_seen
    return _s(self, exogenous_supply, *a, **k)
MarketModule.solve = solve
m = CAPRIModel(data_dir=str(__import__("pathlib").Path(__file__).resolve().parents[2] / "capri_data"), verbose=False)
b = m.run(scenario="BASELINE", max_outer_iter=25)
from capri_mod.scenarios.scenarios import carbon_tax_scenario
m.run(custom_scenario=carbon_tax_scenario(0.0), max_outer_iter=2)   # market in scenario mode, no shock
mm = m.market_module
exo = CAP["exo"]; base = mm.solve(exogenous_supply=exo)
P0 = base.domestic_prices.loc["EU27"]; W0 = base.world_prices
res = {}
for f in (0.95, 0.90):
    e2 = exo.copy(); e2["MILK"] = e2["MILK"] * f
    mm.seen.eu_price_seen = CAP["seen"]
    eq = mm.solve(exogenous_supply=e2)
    P = eq.domestic_prices.loc["EU27"]; dl = mm.ev.dairy_last
    res[f] = {c: round(100 * (P[c] / P0[c] - 1), 1) for c in ["BUTR", "SKIM", "CHES", "WHEY", "FRMI", "CREM"]}
    res[f]["MILK(dairy)"] = round(100 * (dl["price_ratio"]["MILK"] - 1), 1)
    res[f]["converged"] = eq.converged
    print("milk x", f, res[f], flush=True)
