"""
CAPRI Scenario Management
=========================
Defines baseline and counterfactual scenarios for policy analysis.

The scenario framework follows CAPRI conventions:
  - BASELINE: Calibrated to observed data (base year)
  - COUNTERFACTUAL: Policy/exogenous change relative to baseline

Common scenario types:
  1. CAP reform (payment rates, greening, decoupling)
  2. Trade shock (world price change, new trade agreements)
  3. Climate policy (carbon price, land use regulations)
  4. Farm-to-Fork / Green Deal targets
  5. Technology (yield trends, efficiency)
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List
import pandas as pd
import numpy as np

from capri_mod.policy.policy_module import PolicyScenario


# ---------------------------------------------------------------------------
# PRE-BUILT SCENARIOS
# ---------------------------------------------------------------------------
# Removed 20 October 2026 (KNOWN_ISSUES K52a, the user's decision): FARM_TO_FORK (a payment-rate proxy, not
# CAPRI's Farm-to-Fork: use capri_mod.policy.greendeal.farm_to_fork_scenario()), FLAT_RATE_BPS (identical to the
# baseline), UKRAINE_SHOCK and WORLD_PRICE_SHOCKS (shock values without a source, never applied by run(); pass
# world_price_shock= to run() instead).
# Removed 23 October 2026 (the settings inventory; the project lead's decision: no presets without a CAPRI source):
# CAP_REFORM_2030 ("hypothetical"), WTO_LIB (no source), CAP_2023_2027, N_LIMITS_TIGHTER and WTO_FALCONER (their
# cited CAPRI files do not hold these numbers), GREEN_DEAL_F2F (a partial proxy superseded by
# capri_mod.policy.greendeal.farm_to_fork_scenario / greendeal_scenario). SET_ASIDE_10PCT is CAPRI's
# scen/set_aside/set_aside_10.gms (SETR 10).

def baseline_scenario() -> PolicyScenario:
    """Reference baseline scenario (no policy change)."""
    return PolicyScenario(
        name="BASELINE",
        description="Calibrated baseline — no policy change from base year.",
    )


def climate_policy_scenario(carbon_price_eur: float = 100.0) -> PolicyScenario:
    """Carbon pricing: CAPRI's emission tax in the supply models (see carbon_tax_scenario)."""
    return carbon_tax_scenario(carbon_price_eur)


# ---------------------------------------------------------------------------
# SCENARIO REGISTRY
# ---------------------------------------------------------------------------

SCENARIO_REGISTRY = {
    "BASELINE":          baseline_scenario,
}




def set_aside_10_scenario() -> PolicyScenario:
    """
    10% mandatory set-aside on arable land.
    Source: gams/scen/set_aside/set_aside_10.gms
    """
    return PolicyScenario(
        name="SET_ASIDE_10PCT",
        description="10% mandatory set-aside on all arable land.",
        set_aside_requirement=0.10,
    )


def carbon_tax_scenario(carbon_price: float = 100.0) -> PolicyScenario:
    """CAPRI's emission tax (pol_input/ecampa/carbtax50_endotech_set12.gms: %ghgTax% on, p_carbonTax(ru, "GGWP") =
    p_ghgEmisTax on the EU regions): EUR per t CO2-eq on agricultural emissions inside the supply models, with the
    mitigation options endogenous (capri_mod/supply/ghg_tax.py). The tax is the scenario's only shock, as in CAPRI's
    file (the earlier version stood in for it with agri-environment payments, a nitrate limit and an eco-scheme
    budget: retired, Sprint 9i)."""
    return PolicyScenario(
        name=f"CARBON_TAX_{int(carbon_price)}",
        description=f"CAPRI emission tax at EUR {carbon_price}/t CO2-eq on EU agricultural emissions (ghgTax).",
        carbon_tax=float(carbon_price),
    )


def get_scenario(name: str, **kwargs) -> PolicyScenario:
    """Retrieve a named scenario, optionally with custom parameters."""
    if name not in SCENARIO_REGISTRY:
        available = list(SCENARIO_REGISTRY.keys())
        raise ValueError(f"Unknown scenario '{name}'. Available: {available}")
    return SCENARIO_REGISTRY[name](**kwargs)


def list_scenarios() -> List[str]:
    """Return list of all available scenario names."""
    return list(SCENARIO_REGISTRY.keys())


SCENARIO_REGISTRY.update({
    "SET_ASIDE_10PCT":  set_aside_10_scenario,
    "CARBON_TAX_100":   lambda: carbon_tax_scenario(100.0),
    "CARBON_TAX_50":    lambda: carbon_tax_scenario(50.0),
})
