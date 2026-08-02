"""
CAPRI Policy Module
===================
Handles Common Agricultural Policy instruments and other trade policies.

CAP pillars implemented:
  Pillar I (direct payments):
    - Basic Income Support for Sustainability (BISS / former BPS)
    - Complementary Redistributive Income Support (CRIS)
    - Coupled support (for specific sectors)
    - Eco-schemes
    - Young farmers supplement

  Pillar II (rural development):
    - Agri-Environment-Climate Schemes (AECS)
    - Areas of Natural Constraint (ANC) payments
    - Organic farming support
    - Investment support

  Market measures:
    - Tariff Rate Quotas (TRQs)
    - Export subsidies (now mostly eliminated under WTO)
    - Intervention buying / public storage
    - Private storage aid

Reference: EU Regulation 2021/2115 (CAP Strategic Plans)
           CAPRI Policy Module documentation (Britz & Witzke 2012, Ch. 3)
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


# ---------------------------------------------------------------------------
# ENUMS AND CONSTANTS
# ---------------------------------------------------------------------------


# Non-Tariff Measure Ad Valorem Equivalents (%) for EU imports
# Source: CAPRI GAMS arm/def_ntm.gms, based on Arita et al. (2015)
NTM_AVE_PCT = {
    "EU_USA_beef": {
        "applied_rate": 70.0,
        "AVE": 23.0
    },
    "EU_USA_poum": {
        "applied_rate": 21.0,
        "AVE": 102.0
    },
    "EU_USA_pork": {
        "applied_rate": 25.0,
        "AVE": 81.0
    }
}


class PaymentType(Enum):
    BISS       = "biss"       # Basic Income Support for Sustainability
    CRIS       = "cris"       # Complementary Redistributive Income Support
    COUPLED    = "coupled"    # Voluntary Coupled Support
    ECO_SCHEME = "eco_scheme" # Eco-schemes (Pillar I greening successor)
    YOUNG      = "young"      # Young farmers
    ANC        = "anc"        # Areas of Natural Constraint (Pillar II)
    AECS       = "aecs"       # Agri-Environment-Climate (Pillar II)
    ORGANIC    = "organic"    # Organic farming support


class TRQStatus(Enum):
    CLOSED  = "closed"    # TRQ not used (import price > world + tariff)
    PARTIAL = "partial"   # TRQ partially filled
    FULL    = "full"      # TRQ fully utilised (in-quota rate binds)


# ---------------------------------------------------------------------------
# DATA STRUCTURES
# ---------------------------------------------------------------------------

@dataclass
class TRQ:
    """Tariff Rate Quota specification."""
    commodity: str
    importer: str
    quota_volume: float        # 1000 t per year
    in_quota_tariff: float     # ad valorem % within quota
    out_quota_tariff: float    # ad valorem % over quota
    current_fill: float = 0.0  # 1000 t used
    status: TRQStatus = TRQStatus.CLOSED

    @property
    def effective_tariff(self) -> float:
        """Effective tariff rate given current fill level."""
        if self.current_fill < self.quota_volume * 0.999:
            return self.in_quota_tariff
        return self.out_quota_tariff

    def update_fill(self, import_demand: float) -> float:
        """
        Fill TRQ given import demand. Returns effective tariff paid.
        Returns: actual imports allowed under TRQ mechanism.
        """
        if import_demand <= self.quota_volume:
            self.current_fill = import_demand
            self.status = TRQStatus.PARTIAL
            return self.in_quota_tariff
        else:
            self.current_fill = self.quota_volume
            self.status = TRQStatus.FULL
            # Out-of-quota imports face higher tariff
            return self.out_quota_tariff


@dataclass
class DirectPaymentScheme:
    """CAP direct payment configuration for a member state."""
    country: str
    payment_type: PaymentType
    rate_per_ha: float          # EUR/ha
    eligible_land: float        # 1000 ha eligible
    conditionality: Dict[str, float] = field(default_factory=dict)
    # conditionality: {requirement: compliance_rate}
    # e.g. {"crop_rotation": 0.95, "soil_cover": 0.98}

    @property
    def total_budget(self) -> float:
        """Total annual budget (EUR million)."""
        return self.rate_per_ha * self.eligible_land / 1000.0

    def effective_rate(self) -> float:
        """Rate after conditionality deductions."""
        compliance = np.prod(list(self.conditionality.values())) if self.conditionality else 1.0
        return self.rate_per_ha * compliance


@dataclass
class EcoScheme:
    """
    Eco-scheme specification (CAP 2023-2027).

    Eco-schemes are voluntary Pillar I payments for climate/environment
    practices, replacing the former 'greening' requirements.
    """
    name: str
    practice: str               # e.g. "cover_crops", "reduced_inputs", "wetland"
    payment_rate: float         # EUR/ha additional payment
    adoption_rate: float        # % of eligible area that adopts
    eligible_activities: List[str] = field(default_factory=list)
    # Environmental benefit coefficients
    n_reduction: float = 0.0    # kg N/ha reduction vs. baseline
    ghg_reduction: float = 0.0  # t CO2eq/ha reduction
    biodiversity: float = 0.0   # index 0-1


@dataclass
class PolicyScenario:
    """
    Complete CAP / trade policy scenario specification.

    Used to parameterize the supply and market modules for
    counterfactual analysis.
    """
    name: str
    description: str = ""

    # Pillar I changes (relative to baseline)
    biss_rate_change: float = 0.0          # EUR/ha change in BISS rate
    coupled_support: Dict[str, float] = field(default_factory=dict)
    # {commodity: EUR/head or EUR/ha}
    eco_scheme_budget_pct: float = 0.25    # % of Pillar I for eco-schemes

    # Pillar II changes
    aecs_rate_change: float = 0.0
    organic_rate_change: float = 0.0
    anc_rate_change: float = 0.0

    # Trade measures
    tariff_changes: Dict[str, Dict[str, float]] = field(default_factory=dict)
    # {region: {commodity: delta_pct}}
    trq_volume_changes: Dict[str, float] = field(default_factory=dict)
    # {commodity: delta_1000t}

    # Environmental constraints
    nitrate_limit_change: float = 0.0     # delta kg N/ha (negative = tighter)
    set_aside_requirement: float = 0.0    # % arable land mandatory set-aside

    # Production quotas (dairy, sugar — historically important)
    milk_quota: Optional[float] = None    # 1000 t (None = no quota)
    sugar_quota: Optional[float] = None


# ---------------------------------------------------------------------------
# TRQ HANDLER
# ---------------------------------------------------------------------------

class TRQHandler:
    """
    Handles Tariff Rate Quota mechanisms for the market module.

    TRQs create a two-tier tariff structure:
      - In-quota: lower tariff, limited volume
      - Out-of-quota: higher (MFN) tariff, unlimited volume

    The equilibrium depends on whether the quota is filled:
      - Underfilled: domestic price = world price × (1 + in-quota tariff)
      - Filled: domestic price = world price × (1 + in-quota tariff) + rent
      - Overfilled (import > quota): both tiers face their respective tariffs
    """

    # Key EU TRQs (WTO schedules + bilateral FTAs)
    EU_TRQS = [
        # commodity, importer, quota(1000t), in-quota%, out-quota%
        ("BEEF",  "EU27", 300,  0.0,  65.0),
        ("PORK",  "EU27", 150,  0.0,  20.0),
        ("POUL",  "EU27", 250,  0.0,  35.0),
        ("BUTR",  "EU27", 80,  17.0,  82.0),
        ("CHES",  "EU27", 200,  5.0,  40.0),
        ("SUGR",  "EU27", 1200, 0.0,  35.0),
        ("SWHE",  "EU27", 500,  0.0,   0.0),
        ("BARL",  "EU27", 300,  0.0,   0.0),
        ("CORN",  "EU27", 2000, 0.0,   0.0),
        ("WINE",  "EU27", 800,  0.0,  32.0),
        ("SHGM",  "EU27", 200, 10.0,  52.0),
    ]

    def __init__(self, custom_trqs: Optional[List[TRQ]] = None):
        self.trqs: List[TRQ] = []

        # Load default EU TRQs
        for comm, imp, vol, in_t, out_t in self.EU_TRQS:
            self.trqs.append(TRQ(
                commodity=comm, importer=imp,
                quota_volume=vol,
                in_quota_tariff=in_t,
                out_quota_tariff=out_t,
            ))

        if custom_trqs:
            self.trqs.extend(custom_trqs)

        # Index for fast lookup
        self._index: Dict[Tuple[str,str], TRQ] = {
            (t.commodity, t.importer): t for t in self.trqs
        }

    def get_effective_tariff(
        self,
        commodity: str,
        importer: str,
        import_volume: float,
        base_tariff: float,
    ) -> float:
        """
        Return effective tariff given import volume and TRQ status.

        If no TRQ exists, returns base_tariff.
        """
        key = (commodity, importer)
        if key not in self._index:
            return base_tariff

        trq = self._index[key]
        return trq.update_fill(import_volume)

    def get_trq_rents(self) -> pd.DataFrame:
        """
        Compute TRQ rents (EUR million) = in-quota tariff × filled volume × price.
        These are quota rents, accruing to licence holders.
        """
        rows = []
        for trq in self.trqs:
            if trq.status != TRQStatus.CLOSED and trq.current_fill > 0:
                # Rent ≈ (out_quota - in_quota) tariff rate × filled volume × world price proxy
                rent_rate = (trq.out_quota_tariff - trq.in_quota_tariff) / 100.0
                rent = rent_rate * 200 * trq.current_fill / 1000   # EUR million
                rows.append({
                    "commodity": trq.commodity,
                    "importer": trq.importer,
                    "fill_rate": trq.current_fill / max(trq.quota_volume, 1),
                    "status": trq.status.value,
                    "rent_EUR_million": max(0, rent),
                })
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    def apply_trq_scenario(self, volume_changes: Dict[str, float]):
        """Modify TRQ volumes for scenario analysis."""
        for comm, delta in volume_changes.items():
            for trq in self.trqs:
                if trq.commodity == comm:
                    trq.quota_volume = max(0, trq.quota_volume + delta)


# ---------------------------------------------------------------------------
# DIRECT PAYMENTS ENGINE
# ---------------------------------------------------------------------------

class DirectPaymentsEngine:
    """
    Computes CAP direct payments and their distributional effects.

    Based on CAP Strategic Plans 2023-2027 structure.
    """

    # National envelopes (EUR million/year) — approximate 2023-2027 values
    NATIONAL_ENVELOPES = {
        "FR": 7000, "DE": 5900, "IT": 3600, "ES": 4800, "PL": 3360,
        "RO": 1930, "HU": 1340, "BG": 812,  "CZ": 859,  "NL": 729,
        "BE": 481,  "DK": 881,  "SE": 720,  "FI": 524,  "AT": 693,
        "EL": 1900, "PT": 608,  "IE": 1185, "SK": 398,  "HR": 343,
        "SI": 137,  "LT": 410,  "LV": 302,  "EE": 199,  "LU": 33,
        "CY": 51,   "MT": 5,    "NO": 0,
    }

    def __init__(self, scenario: Optional[PolicyScenario] = None):
        self.scenario = scenario or PolicyScenario(name="baseline")

    def compute_payments_by_region(
        self,
        cap_data: pd.DataFrame,   # [region × {BPS, ANC, AES, ORGANIC, COUPLED}]
        land_data: pd.DataFrame,  # [region × land_type]
    ) -> pd.DataFrame:
        """
        Compute total CAP payments per region (EUR/ha and total EUR 1000).

        Returns DataFrame with payment components by region.
        """
        from capri_mod.data.definitions import REGION_TO_COUNTRY

        results = []
        for region in cap_data.index:
            country = REGION_TO_COUNTRY.get(region, "XX")
            uaa = land_data.loc[region, ["ARABLE", "PERMANENT", "GRASSLAND"]].sum() \
                  if region in land_data.index else 100.0

            # BISS (formerly BPS)
            biss_rate = cap_data.at[region, "BPS"] if "BPS" in cap_data.columns else 200.0
            biss_rate += self.scenario.biss_rate_change
            biss_total = biss_rate * uaa / 1000   # EUR 1000

            # ANC (Pillar II)
            anc_rate = cap_data.at[region, "ANC"] if "ANC" in cap_data.columns else 0.0
            anc_rate += self.scenario.anc_rate_change
            anc_total = anc_rate * uaa * 0.30 / 1000  # ~30% of land is ANC-eligible

            # AECS (Pillar II agri-environment)
            aecs_rate = cap_data.at[region, "AES"] if "AES" in cap_data.columns else 0.0
            aecs_rate += self.scenario.aecs_rate_change
            aecs_total = aecs_rate * uaa * 0.20 / 1000  # ~20% of land in AECS

            # Organic
            org_rate = cap_data.at[region, "ORGANIC"] if "ORGANIC" in cap_data.columns else 0.0
            org_rate += self.scenario.organic_rate_change
            organic_total = org_rate * uaa * 0.08 / 1000  # ~8% organic

            # Eco-scheme (25% of Pillar I in 2023-2027 CAP)
            eco_total = biss_total * self.scenario.eco_scheme_budget_pct

            results.append({
                "region": region,
                "country": country,
                "UAA_1000ha": uaa,
                "BISS_EUR_ha": biss_rate,
                "BISS_total": biss_total,
                "eco_scheme": eco_total,
                "ANC_total": anc_total,
                "AECS_total": aecs_total,
                "organic_total": organic_total,
                "total_payments": biss_total + eco_total + anc_total + aecs_total + organic_total,
            })

        return pd.DataFrame(results).set_index("region")

    def compute_national_budgets(
        self,
        regional_payments: pd.DataFrame,
    ) -> pd.DataFrame:
        """Aggregate regional payments to national level and compare to envelopes."""
        from capri_mod.data.definitions import REGION_TO_COUNTRY

        regional_payments = regional_payments.copy()
        regional_payments["country"] = [
            REGION_TO_COUNTRY.get(r, r) for r in regional_payments.index
        ]
        national = regional_payments.groupby("country")["total_payments"].sum()
        envelope = pd.Series(self.NATIONAL_ENVELOPES)

        budget = pd.DataFrame({
            "simulated_EUR_million": national / 1000,
            "envelope_EUR_million": envelope,
        }).dropna()
        budget["utilisation_pct"] = (
            budget["simulated_EUR_million"] / budget["envelope_EUR_million"] * 100
        ).clip(0, 150)

        return budget


# ---------------------------------------------------------------------------
# INTERVENTION / PUBLIC STORAGE
# ---------------------------------------------------------------------------

class InterventionSystem:
    """
    Public intervention buying and storage for cereals and dairy.

    Intervention price sets a price floor:
      If market price < intervention price → public buying starts
      If market price > intervention price → stocks released

    Reference: EU Reg. 1308/2013, Art. 7-14 (CMO Regulation)
    """

    INTERVENTION_PRICES = {
        "SWHE": 101.31,   # EUR/t (official EU intervention price)
        "BARL": 101.31,
        "CORN": 101.31,
        "BUTR": 2217.5,
        "SKIM": 1698.0,
        "BEEF": 2224.0,
    }

    def __init__(self):
        self.stocks: Dict[str, float] = {k: 0.0 for k in self.INTERVENTION_PRICES}

    def apply_intervention(
        self,
        market_prices: pd.Series,
        production: pd.Series,
        consumption: pd.Series,
    ) -> Dict[str, float]:
        """
        Check intervention thresholds and adjust stocks.

        Returns dict of {commodity: stock_change_1000t}.
        """
        stock_changes = {}

        for comm, int_price in self.INTERVENTION_PRICES.items():
            mkt_price = market_prices.get(comm, int_price * 1.1)
            surplus = production.get(comm, 0) - consumption.get(comm, 0)

            if mkt_price < int_price and surplus > 0:
                # Buy into intervention
                buying = min(surplus, surplus * 0.5)  # buy up to 50% of surplus
                self.stocks[comm] += buying
                stock_changes[comm] = buying
            elif mkt_price > int_price * 1.05 and self.stocks.get(comm, 0) > 0:
                # Release from stocks
                release = min(self.stocks[comm], abs(surplus) * 0.3)
                self.stocks[comm] -= release
                stock_changes[comm] = -release
            else:
                stock_changes[comm] = 0.0

        return stock_changes

    def get_stock_summary(self) -> pd.Series:
        return pd.Series(self.stocks)


# ---------------------------------------------------------------------------
# POLICY MODULE COORDINATOR
# ---------------------------------------------------------------------------

class PolicyModule:
    """
    Coordinates all CAP and trade policy instruments.

    Called at the start of each scenario run to:
      1. Compute payment rates → feed to supply module (net revenues)
      2. Compute tariffs / TRQ status → feed to market module
      3. Track compliance costs and environmental conditionality
    """

    def __init__(
        self,
        data: dict,
        scenario: Optional[PolicyScenario] = None,
    ):
        self.data     = data
        self.scenario = scenario or PolicyScenario(name="baseline")

        self.payments   = DirectPaymentsEngine(self.scenario)
        self.trq_handler = TRQHandler()
        self.intervention = InterventionSystem()

    def apply_scenario(self, scenario: PolicyScenario):
        """Switch to a new policy scenario."""
        self.scenario = scenario
        self.payments = DirectPaymentsEngine(scenario)

        if scenario.trq_volume_changes:
            self.trq_handler.apply_trq_scenario(scenario.trq_volume_changes)

    def get_payment_rates_by_region(self) -> pd.DataFrame:
        """Compute and return regional payment rates for supply module."""
        return self.payments.compute_payments_by_region(
            cap_data=self.data["cap_payments"],
            land_data=self.data["land"],
        )

    def get_effective_tariffs(
        self,
        import_volumes: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Return effective tariff matrix [region × commodity] accounting for TRQs.
        """
        base_tariffs = self.data["tariffs"].copy()

        # Apply scenario tariff changes
        for region, changes in self.scenario.tariff_changes.items():
            for comm, delta in changes.items():
                if region in base_tariffs.index and comm in base_tariffs.columns:
                    base_tariffs.at[region, comm] = max(
                        0, base_tariffs.at[region, comm] + delta
                    )

        # Apply TRQ adjustments if import volumes known
        if import_volumes is not None:
            for comm in base_tariffs.columns:
                for region in base_tariffs.index:
                    vol = import_volumes.at[region, comm] if (
                        region in import_volumes.index and comm in import_volumes.columns
                    ) else 0.0
                    base_tariff = base_tariffs.at[region, comm]
                    effective = self.trq_handler.get_effective_tariff(
                        comm, region, vol, base_tariff
                    )
                    base_tariffs.at[region, comm] = effective

        return base_tariffs

    def get_supply_policy_adders(self) -> pd.Series:
        """
        Return per-activity policy payment to add to net revenues (EUR/ha or EUR/head).
        Includes BISS, eco-schemes, coupled support.
        """
        regional_payments = self.get_payment_rates_by_region()
        avg_biss = regional_payments["BISS_EUR_ha"].mean()

        from capri_mod.data.definitions import CROPS, ANIMALS, ALL_ACTIVITIES
        adders = pd.Series(0.0, index=ALL_ACTIVITIES)

        # BISS applied to all eligible crops (not SETA, not permanent for simplicity)
        eligible_crops = [c for c in CROPS if c not in ("SETA",)]
        for crop in eligible_crops:
            adders[crop] = avg_biss

        # Coupled support (voluntary, sector-specific)
        for comm, rate in self.scenario.coupled_support.items():
            if comm in adders.index:
                adders[comm] += rate

        return adders

    def summarise_policy(self) -> Dict:
        """Print policy scenario summary."""
        regional = self.get_payment_rates_by_region()
        national = self.payments.compute_national_budgets(regional)

        return {
            "scenario_name": self.scenario.name,
            "total_EU_budget_EUR_billion": regional["total_payments"].sum() / 1e6,
            "avg_BISS_EUR_ha": regional["BISS_EUR_ha"].mean(),
            "national_budgets": national,
            "active_TRQs": len(self.trq_handler.trqs),
            "intervention_stocks": self.intervention.get_stock_summary().to_dict(),
        }
