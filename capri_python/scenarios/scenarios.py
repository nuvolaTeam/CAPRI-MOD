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

from capri_python.policy.policy_module import PolicyScenario


# ---------------------------------------------------------------------------
# PRE-BUILT SCENARIOS
# ---------------------------------------------------------------------------

def baseline_scenario() -> PolicyScenario:
    """Reference baseline scenario (no policy change)."""
    return PolicyScenario(
        name="BASELINE",
        description="Calibrated baseline — no policy change from base year.",
    )


def farm_to_fork_scenario() -> PolicyScenario:
    """
    EU Farm-to-Fork Strategy (F2F) scenario.

    Key targets:
      - 25% organic farming by 2030
      - 50% reduction in pesticide use
      - 20% reduction in fertilizer use
      - 10% reduction in antibiotic use
    """
    return PolicyScenario(
        name="FARM_TO_FORK",
        description="EU Farm-to-Fork Strategy 2030 targets.",
        organic_rate_change=150.0,       # +EUR 150/ha organic premium
        aecs_rate_change=30.0,           # boost agri-environment payments
        eco_scheme_budget_pct=0.30,      # 30% of Pillar I to eco-schemes
        nitrate_limit_change=-30.0,      # stricter N limit (kg/ha)
    )


def cap_reform_2030_scenario() -> PolicyScenario:
    """
    Hypothetical CAP reform 2028-2033:
    - Flat rate BISS convergence to 200 EUR/ha EU-wide
    - 30% Pillar II ring-fencing for environment
    - Strong eco-scheme conditionality
    """
    return PolicyScenario(
        name="CAP_REFORM_2030",
        description="Convergence to flat-rate BISS and stronger greening.",
        biss_rate_change=-30.0,          # cut for high-payment regions
        eco_scheme_budget_pct=0.35,
        aecs_rate_change=20.0,
        set_aside_requirement=0.04,      # 4% mandatory set-aside
    )


def wto_liberalisation_scenario() -> PolicyScenario:
    """
    WTO trade liberalisation:
    - 50% reduction in EU import tariffs
    - TRQ expansion
    """
    return PolicyScenario(
        name="WTO_LIBERALISATION",
        description="50% reduction in EU agricultural tariffs + TRQ expansion.",
        tariff_changes={
            "EU27": {comm: -50.0 for comm in [
                "BEEF","PORK","POUL","BUTR","CHES","SUGR","WINE","SHGM"
            ]}
        },
        trq_volume_changes={
            "BEEF": 150.0, "PORK": 80.0, "POUL": 100.0,
            "BUTR": 40.0,  "CHES": 100.0,
        },
    )


def climate_policy_scenario(carbon_price_eur: float = 100.0) -> PolicyScenario:
    """
    Carbon pricing scenario:
    - Carbon price on agricultural emissions
    - Increased incentives for carbon sequestration
    """
    return PolicyScenario(
        name=f"CARBON_PRICE_{int(carbon_price_eur)}",
        description=f"Agricultural carbon price at {carbon_price_eur} EUR/t CO2-eq.",
        # Carbon price translates to reduced payments for high-emission activities
        # and increased payments for sequestration
        aecs_rate_change=carbon_price_eur * 0.3,  # proxy for carbon farming payments
        nitrate_limit_change=-20.0,
        eco_scheme_budget_pct=0.30,
    )


def ukraine_war_trade_shock() -> PolicyScenario:
    """
    Trade shock scenario: disruption of Ukrainian grain exports.
    Models world price increases for cereals and oilseeds.
    """
    return PolicyScenario(
        name="UKRAINE_TRADE_SHOCK",
        description="Disruption to Black Sea grain and oilseed exports.",
        # World price shocks applied externally to market module
        # Policy response: relaxation of set-aside, suspension of eco-scheme
        set_aside_requirement=-0.04,    # remove set-aside requirement
        eco_scheme_budget_pct=0.15,     # reduce eco-scheme to free up production
        nitrate_limit_change=20.0,      # loosen N constraint temporarily
    )


# ---------------------------------------------------------------------------
# SCENARIO REGISTRY
# ---------------------------------------------------------------------------

SCENARIO_REGISTRY = {
    "BASELINE":          baseline_scenario,
    "FARM_TO_FORK":      farm_to_fork_scenario,
    "CAP_REFORM_2030":   cap_reform_2030_scenario,
    "WTO_LIB":           wto_liberalisation_scenario,
    "UKRAINE_SHOCK":     ukraine_war_trade_shock,
}




def cap_2023_2027_scenario() -> PolicyScenario:
    """
    CAP Strategic Plans 2023-2027 baseline.
    Source: gams/scen/base_scenarios/CAP_2023_2027.gms
    """
    return PolicyScenario(
        name="CAP_2023_2027",
        description="CAP Strategic Plans 2023-2027: 25% eco-schemes, GAECs conditionality.",
        eco_scheme_budget_pct=0.25,      # mandatory 25% Pillar I to eco-schemes
        set_aside_requirement=0.04,       # 4% non-productive areas (GAEC 8)
        aecs_rate_change=10.0,
    )


def flat_rate_bps_scenario() -> PolicyScenario:
    """
    Full flat-rate BPS convergence.
    Source: gams/scen/Premiums/bps_full_flat_rate.gms
    BPS converges to uniform EUR/ha rate by 2019.
    """
    return PolicyScenario(
        name="FLAT_RATE_BPS",
        description="Full flat-rate BISS convergence by 2019 (Fischler reform extension).",
        biss_rate_change=0.0,            # total budget neutral, redistributed
        eco_scheme_budget_pct=0.25,
    )


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


def wto_falconer_scenario() -> PolicyScenario:
    """
    WTO Falconer tiered tariff cut formula.
    Source: gams/scen/trade_policies/WTO/falconer.gms
    Tiered cuts: 0-20% → 50% cut; 20-50% → 57%; 50-75% → 64%; >75% → 70%
    """
    return PolicyScenario(
        name="WTO_FALCONER",
        description="WTO Falconer tiered tariff reduction formula (2008 draft modalities).",
        tariff_changes={
            "EU27": {
                "BEEF": -46, "PORK": -35, "POUL": -35,
                "BUTR": -46, "CHES": -38, "SUGR": -46,
                "SHGM": -46, "WINE": -35,
            }
        },
        trq_volume_changes={"BEEF": 200.0, "PORK": 100.0, "BUTR": 50.0},
    )


def n_limits_scenario() -> PolicyScenario:
    """
    Tighter nitrogen limits scenario.
    Source: gams/scen/NLimits/sur_nlimits.gms
    Minimum N surplus limits enforced per NUTS-2 region.
    """
    return PolicyScenario(
        name="N_LIMITS_TIGHTER",
        description="Tighter N application limits (-20 kg N/ha) to reduce N surplus.",
        nitrate_limit_change=-20.0,
        aecs_rate_change=20.0,    # compensatory AECS payments
    )


def carbon_tax_scenario(carbon_price: float = 100.0) -> PolicyScenario:
    """
    Agricultural carbon tax.
    Source: gams/scen/ghg_emission_abatement/carbon_tax_eu_agri.gms
    """
    return PolicyScenario(
        name=f"CARBON_TAX_{int(carbon_price)}",
        description=f"Agricultural carbon tax at EUR {carbon_price}/t CO2-eq.",
        aecs_rate_change=carbon_price * 0.30,
        nitrate_limit_change=-15.0,
        eco_scheme_budget_pct=0.30,
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


# ---------------------------------------------------------------------------
# WORLD PRICE SHOCKS (passed to market module)
# ---------------------------------------------------------------------------

WORLD_PRICE_SHOCKS: Dict[str, Dict[str, float]] = {
    "UKRAINE_TRADE_SHOCK": {
        "SWHE": 0.40,   # +40% wheat
        "CORN": 0.35,   # +35% maize
        "SUNF": 0.80,   # +80% sunflower
        "RAPE": 0.30,   # +30% rapeseed
        "SOYA": 0.15,
        "BARL": 0.30,
    },
    "ENERGY_CRISIS": {
        "SWHE": 0.20, "CORN": 0.18, "RAPE": 0.25,
        "PORK": 0.15, "POUL": 0.12,
    },
    "DROUGHT_2022": {
        "SUGB": -0.15, "CORN": -0.10, "RAPE": -0.08,
    },
}

SCENARIO_REGISTRY.update({
    "CAP_2023_2027":    cap_2023_2027_scenario,
    "FLAT_RATE_BPS":    flat_rate_bps_scenario,
    "SET_ASIDE_10PCT":  set_aside_10_scenario,
    "WTO_FALCONER":     wto_falconer_scenario,
    "N_LIMITS_TIGHTER": n_limits_scenario,
    "CARBON_TAX_100":   lambda: carbon_tax_scenario(100.0),
    "CARBON_TAX_50":    lambda: carbon_tax_scenario(50.0),
})

WORLD_PRICE_SHOCKS.update({
    "OIL_PRICE_SHOCK_50PCT": {
        "SWHE": 0.20, "CORN": 0.18, "RAPE": 0.25,
        "PORK": 0.15, "POUL": 0.12, "BARL": 0.15,
    },
    "WTO_DOHA_LIBERALISATION": {
        "BEEF": -0.08, "PORK": -0.05, "POUL": -0.06,
        "BUTR": -0.12, "CHES": -0.07, "SUGR": -0.10,
    },
})
