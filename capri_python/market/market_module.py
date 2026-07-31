"""
CAPRI Market Module
===================
Global spatial multi-commodity partial equilibrium model.

Implements the Armington (1969) assumption:
  - Goods from different origins are imperfect substitutes
  - Bilateral trade flows determined by price differentials and tariffs
  - Market clearing: excess supply = excess demand at equilibrium prices

Mathematical structure:
  For each commodity k and trade region r:
    Demand:     QD_r  = QD0_r × (PD_r / PD0_r)^η_k
    Supply:     QS_r  = QS0_r × (PS_r / PS0_r)^ε_k
    Armington:  import share_rj = (P_rj / Σ P_rj)^(-σ) / Σ(P_rj / Σ P_rj)^(-σ)
    Trade:      TRD_rj = M_r × share_rj
    Market clr: Σ_r QS_r = Σ_r QD_r  (spatial)

The system is solved as a mixed complementarity problem (MCP),
approximated here by Newton iteration on excess demand.

Reference: CAPRI Manual Chapter 5 (Market Module), Britz 2008.
           Armington, P.S. (1969). A theory of demand for products
           distinguished by place of production. IMF Staff Papers 16(1).
"""

import numpy as np
import pandas as pd
from scipy.optimize import fsolve
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple

from capri_python.data.definitions import (
    MARKET_COMMODITIES, ALL_TRADE_REGIONS,
)


# ---------------------------------------------------------------------------
# DATA STRUCTURES
# ---------------------------------------------------------------------------

@dataclass
class MarketEquilibrium:
    """Results of a market module solve."""
    world_prices: pd.Series          # EUR/t, CIF
    domestic_prices: pd.DataFrame    # [region × commodity], EUR/t
    production: pd.DataFrame         # [region × commodity], 1000 t
    consumption: pd.DataFrame        # [region × commodity], 1000 t
    trade_flows: pd.DataFrame        # MultiIndex (exp, imp) × commodity
    net_exports: pd.DataFrame        # [region × commodity]
    welfare: pd.DataFrame            # [region × {consumer, producer, budget}]
    excess_demand: pd.Series         # residual per commodity (should ≈ 0)
    converged: bool = True
    iterations: int = 0


# ---------------------------------------------------------------------------
# ARMINGTON DEMAND SYSTEM
# ---------------------------------------------------------------------------

class ArmingtonDemand:
    """
    CES/Armington demand aggregator for a single trade region and commodity.

    Computes import demand allocation across origins given prices.

    The CES aggregator:
        Q_total = [Σ_j δ_j × q_j^((σ-1)/σ)]^(σ/(σ-1))
    implies:
        q_j / q_k = (δ_j / δ_k) × (p_k / p_j)^σ    (Armington demand)
    """

    def __init__(self, sigma: float, base_shares: pd.Series, base_price: float):
        """
        Parameters
        ----------
        sigma      : Armington substitution elasticity
        base_shares: baseline import shares by origin (sums to 1)
        base_price : baseline aggregate import price index
        """
        self.sigma       = sigma
        self.base_shares = base_shares / base_shares.sum()
        self.base_price  = base_price
        # CES share parameters δ_j (calibrated to base shares)
        # At base: δ_j ∝ s_j (share) when prices equal
        self.delta = self.base_shares.copy()

    def price_index(self, prices_by_origin: pd.Series) -> float:
        """
        CES price index (Armington composite price).
        P = [Σ_j δ_j × p_j^(1-σ)]^(1/(1-σ))
        """
        p = prices_by_origin.reindex(self.delta.index).fillna(
            prices_by_origin.mean()
        ).values
        d = self.delta.values
        s = self.sigma

        if s == 1.0:
            # Cobb-Douglas case
            return float(np.prod(p ** d))
        else:
            exponent = 1 - s
            val = (d * p ** exponent).sum()
            if val <= 0:
                return float(prices_by_origin.mean())
            return float(val ** (1.0 / exponent))

    def import_shares(self, prices_by_origin: pd.Series) -> pd.Series:
        """
        Armington import shares: s_j = δ_j × (P/p_j)^σ
        """
        P = self.price_index(prices_by_origin)
        p = prices_by_origin.reindex(self.delta.index).fillna(
            prices_by_origin.mean()
        )
        shares = self.delta * (P / p.clip(lower=0.01)) ** self.sigma
        shares = shares / shares.sum()   # normalise to sum to 1
        return shares

    def import_quantities(
        self,
        total_imports: float,
        prices_by_origin: pd.Series,
    ) -> pd.Series:
        """Allocate total import quantity across origins."""
        shares = self.import_shares(prices_by_origin)
        return shares * total_imports


# ---------------------------------------------------------------------------
# MARKET MODULE
# ---------------------------------------------------------------------------

class MarketModule:
    """
    Global agricultural market model.

    Solves for world prices that clear markets in all commodities
    simultaneously, given supply quantities from the supply module
    and demand functions.

    Convergence algorithm:
      Tatonnement / Newton iterations on excess demand:
        P_{t+1} = P_t × (1 + α × ED_t / QS_t)
      until max|ED| < tolerance.
    """

    def __init__(self, data: dict):
        self.data       = data
        self.commodities = MARKET_COMMODITIES
        self.regions    = ALL_TRADE_REGIONS
        self.n_comm     = len(self.commodities)
        self.n_reg      = len(self.regions)

        # Base data
        self.world_prices_base = data["world_prices"].reindex(
            self.commodities).fillna(200.0)
        self.tariffs       = data["tariffs"]
        self.trade_flows_base = data["trade_flows"]
        self.armington     = data["armington"]
        self._demand_cal   = None  # set by _calibrate_demand_to_supply at solve time

        # Calibrate Armington aggregators
        self._build_armington_systems()

        # Compute baseline consumption and production
        self._calibrate_baseline()

    def _build_armington_systems(self):
        """Build Armington demand aggregators for each (region, commodity)."""
        self.armington_systems: Dict[Tuple[str,str], ArmingtonDemand] = {}

        for comm in self.commodities:
            sigma = self.armington.at[comm, "sigma"] if comm in self.armington.index else 3.0

            for importer in self.regions:
                # Base import shares from trade flows
                flows = self.trade_flows_base
                total_imports = 0.0
                shares_dict = {}

                for exporter in self.regions:
                    if exporter == importer:
                        continue
                    if (exporter, importer) in flows.index and comm in flows.columns:
                        val = flows.at[(exporter, importer), comm]
                        if val > 0:
                            shares_dict[exporter] = val
                            total_imports += val

                if total_imports < 1.0:
                    # Tiny importer — allocate uniformly across major exporters
                    major = [r for r in self.regions if r != importer][:5]
                    shares_dict = {r: 1.0 for r in major}

                base_shares = pd.Series(shares_dict)
                base_price = self.world_prices_base.get(comm, 200.0)

                self.armington_systems[(importer, comm)] = ArmingtonDemand(
                    sigma=sigma,
                    base_shares=base_shares,
                    base_price=base_price,
                )

    def _calibrate_baseline(self):
        """
        Calibrate baseline production and consumption.

        Uses FAOSTAT-approximate world totals allocated across trade regions
        via fixed production shares. Consumption = Production + NetImports,
        ensuring markets balance at baseline world prices.
        """
        flows = self.trade_flows_base
        comms = self.commodities
        regions = self.regions

        self.base_production  = pd.DataFrame(0.0, index=regions, columns=comms)
        self.base_consumption = pd.DataFrame(0.0, index=regions, columns=comms)

        # FAOSTAT-approximate world production totals (1000 t, ~2012 baseline)
        world_prod_ref = {
            "SWHE": 780000, "DWHE": 40000,  "BARL": 155000, "CORN": 1150000,
            "OCER": 80000,  "RAPE": 72000,  "SUNF": 55000,  "SOYA": 370000,
            "OOIL": 20000,  "SUGB": 1900000,"SUGR": 180000, "POTA": 370000,
            "PULS": 88000,  "TOMA": 180000, "OVEG": 900000, "APPL": 85000,
            "OFRU": 220000, "CITR": 145000, "WINE": 70000,  "OLIV": 20000,
            "MILK": 900000, "BUTR": 11000,  "SKIM": 8000,   "CHES": 22000,
            "WHEY": 15000,  "BEEF": 70000,  "PORK": 120000, "POUL": 130000,
            "SHGM": 15000,  "EGGS": 80000,  "FATS": 25000,  "OFOD_M": 50000,
        }

        # Production shares by trade region (must sum to ~1.0)
        prod_share_base = {
            "EU27": 0.18, "USA": 0.12, "CHN": 0.22, "IND": 0.11,
            "BRA":  0.09, "RUS": 0.06, "IDN": 0.04, "JPN": 0.02,
            "MEX":  0.02, "ARG": 0.05, "AUS": 0.03, "NZL": 0.01,
            "CAN":  0.03, "TUR": 0.02, "KOR": 0.01, "THA": 0.02,
            "VNM":  0.01, "PAK": 0.02, "BGD": 0.01, "NGA": 0.02,
            "ZAF":  0.01, "ETH": 0.01, "EGY": 0.01, "MAR": 0.01,
            "DZA":  0.005,"SAU": 0.005,"IRN": 0.01, "ROW": 0.07,
        }
        # Normalise so shares sum to 1 across known regions
        total_share = sum(prod_share_base.get(r, 0.005) for r in regions)
        prod_share  = {r: prod_share_base.get(r, 0.005) / total_share for r in regions}

        rng = np.random.default_rng(123)

        # Real production for NON-EU trade regions only (CAPRI FAO_agg SUA).
        # Real bilateral trade flows are now used for the net-trade identity.
        # EU27 base is left synthetic because its supply is overridden by the
        # supply module at solve time; injecting real EU27 levels unbalances
        # the base (supply-module output != SUA consumption at base price).
        real_world = {}
        try:
            import json as _json
            from pathlib import Path as _P
            from capri_python.data.loaders import resolve_data_file
            _b = _P(__file__).parent.parent.parent / "capri_data"
            f = resolve_data_file(_b, "fao_market_baseline.json")
            if f.exists():
                raw = _json.load(open(f))
                for key, rec in raw.items():
                    r, c = key.split("|")
                    if r != "EU27" and rec.get("production", 0) > 0:
                        real_world[(r, c)] = rec["production"]
        except Exception:
            real_world = {}

        for comm in comms:
            w_prod = world_prod_ref.get(comm, 10000)

            # Pre-compute net trade per region from baseline flows
            net_exports = {r: 0.0 for r in regions}
            for exporter in regions:
                for importer in regions:
                    if exporter == importer:
                        continue
                    key = (exporter, importer)
                    if key in flows.index and comm in flows.columns:
                        v = float(flows.at[key, comm])
                        net_exports[exporter] += v
                        net_exports[importer] -= v

            for region in regions:
                ps   = prod_share[region]
                noise = float(rng.uniform(0.92, 1.08))
                prod  = max(1.0, w_prod * ps * noise)
                # Override rest-of-world production with real SUA level if known
                if (region, comm) in real_world:
                    prod = max(1.0, real_world[(region, comm)])
                # Consumption = Production - NetExports (trade identity)
                cons  = max(1.0, prod - net_exports.get(region, 0.0))

                self.base_production.at[region, comm]  = prod
                self.base_consumption.at[region, comm] = cons

    # ------------------------------------------------------------------
    # Domestic prices
    # ------------------------------------------------------------------

    def domestic_prices(
        self,
        world_prices: pd.Series,
        trade_scenario: Optional[Dict] = None,
    ) -> pd.DataFrame:
        """
        Compute domestic (wedge) prices from world prices + tariffs.
        p_domestic = p_world × (1 + tariff/100) × exchange_rate

        Returns DataFrame [region × commodity].
        """
        tariffs = self.tariffs.copy()
        if trade_scenario and "tariff_change" in trade_scenario:
            for comm, change in trade_scenario["tariff_change"].items():
                if comm in tariffs.columns:
                    tariffs[comm] = (tariffs[comm] + change).clip(lower=0)

        prices = pd.DataFrame(index=self.regions, columns=self.commodities, dtype=float)
        for comm in self.commodities:
            wp = world_prices.get(comm, 200.0)
            for region in self.regions:
                tariff = tariffs.at[region, comm] if (
                    region in tariffs.index and comm in tariffs.columns
                ) else 0.0
                prices.at[region, comm] = wp * (1 + tariff / 100.0)

        return prices

    # ------------------------------------------------------------------
    # Supply and demand responses
    # ------------------------------------------------------------------

    def supply_response(
        self,
        world_prices: pd.Series,
        exogenous_supply: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Supply quantities by region and commodity (1000 t).
        If exogenous_supply is given (from supply module), use it for EU27.
        Otherwise, apply supply elasticity to price signal.
        """
        if exogenous_supply is not None:
            # Only override the EU27 row with the supply-module output; keep
            # all other trade regions (USA, BRA, CHN, ROW, ...) at their
            # calibrated base production. Otherwise global supply collapses to
            # the EU subset and excess demand explodes.
            supply = self.base_production.copy()
            for comm in exogenous_supply.columns:
                if comm not in supply.columns:
                    continue
                eu_val = exogenous_supply[comm].sum()
                if eu_val > 0 and "EU27" in supply.index:
                    supply.at["EU27", comm] = eu_val
        else:
            supply = self.base_production.copy()

        # Own-price supply elasticities from CAPRI's calibrated market model
        # (elas1717 p_elasSupp, EU medians). These replace the crop-oriented
        # Armington eps column, which stood in a blanket 0.15-0.25 for every
        # commodity -- including livestock, where CAPRI's real values are
        # 0.55-0.76. Commodities not in the file keep the eps fallback.
        real_supply = getattr(self, "_real_supply_elas", None)
        if real_supply is None:
            real_supply = {}
            try:
                from capri_python.data.loaders import resolve_data_file
                import json as _json
                _b = resolve_data_file("capri_data", "sources/arm")
                _f = resolve_data_file(_b, "supply_elas_eu_all.json")
                real_supply = _json.loads(open(_f).read())
            except Exception:
                real_supply = {}
            self._real_supply_elas = real_supply

        eps = self.armington["eps"] if "eps" in self.armington.columns else pd.Series(0.25, index=self.commodities)

        for comm in self.commodities:
            wp0 = self.world_prices_base.get(comm, 200.0)
            wp1 = world_prices.get(comm, 200.0)
            price_ratio = wp1 / max(wp0, 0.01)
            # real CAPRI elasticity first, eps fallback second
            if comm in real_supply:
                el = float(real_supply[comm])
            else:
                el = eps.get(comm, 0.25) if hasattr(eps, 'get') else 0.25

            for region in self.regions:
                # Price transmission: supply responds to world price signal
                base = supply.at[region, comm] if (
                    region in supply.index and comm in supply.columns
                ) else self.base_production.at[region, comm]
                supply.at[region, comm] = max(0, base * (price_ratio ** el))

        return supply

    def demand_response(
        self,
        domestic_prices: pd.DataFrame,
        world_prices: pd.Series,
    ) -> pd.DataFrame:
        """
        Consumption quantities by region and commodity (1000 t).

        Faithful to CAPRI's Generalised Leontief demand structure in that
        quantity responds to own price AND to per-capita income (Engel effect):
            QD = QD0 × (P/P0)^eta × (Y/Y0)^income_elas
        where the income term is the demand-side counterpart of the GL
        expenditure function's dependence on income per capita. Cross-price
        effects are captured through the Armington layer.
        """
        demand = pd.DataFrame(index=self.regions, columns=self.commodities, dtype=float)

        # Per-capita income proxy from GDP index (relative to base = 100)
        income_ratio = getattr(self, "_income_ratio", None)
        if income_ratio is None:
            income_ratio = 1.0

        # Real CAPRI demand elasticities (fao_agg p_demandElas), EU-average
        # own-price, mapped to model commodity codes. Overrides the generic eta.
        real_dem = getattr(self, "_real_demand_elas", None)
        if real_dem is None:
            real_dem = {}
            try:
                import json as _json
                from pathlib import Path as _P
                _b2 = _P(__file__).parent.parent.parent / "capri_data"
                from capri_python.data.loaders import resolve_data_file
                f = resolve_data_file(_b2, "fao_demand_own_elas_eu.json")
                if f.exists():
                    raw = _json.load(open(f))
                    cmap = {"WHEA":"SWHE","BARL":"BARL","MAIZ":"CORN","BEEF":"BEEF",
                            "PORK":"PORK","POUM":"POUL","MILK":"MILK","BUTT":"BUTR",
                            "CHES":"CHES","SMIP":"SKIM","SOYA":"SOYA","SUGA":"SUGR"}
                    for sua, mc in cmap.items():
                        if sua in raw:
                            real_dem[mc] = raw[sua]
            except Exception:
                real_dem = {}
            self._real_demand_elas = real_dem

        for comm in self.commodities:
            eta = real_dem.get(comm)
            if eta is None:
                eta = self.armington.at[comm, "eta"] if comm in self.armington.index else -0.25
            # Income elasticity: staples inelastic, livestock/processed higher
            inc_elas = self._income_elasticity(comm)
            wp0 = self.world_prices_base.get(comm, 200.0)
            cal = self._demand_cal_factor(comm)

            for region in self.regions:
                pd_r = domestic_prices.at[region, comm] if (
                    region in domestic_prices.index and comm in domestic_prices.columns
                ) else world_prices.get(comm, 200.0)
                price_ratio = pd_r / max(wp0, 0.01)

                base = self.base_consumption.at[region, comm] if (
                    region in self.base_consumption.index
                ) else 100.0
                demand.at[region, comm] = max(
                    0, cal * base * (price_ratio ** eta) * (income_ratio ** inc_elas)
                )

        return demand

    @staticmethod
    def _income_elasticity(comm: str) -> float:
        """Engel income elasticities by commodity group (CAPRI-style):
        staples low/negative, livestock and processed goods higher."""
        staples = {"SWHE", "DWHE", "BARL", "CORN", "OCER", "POTA", "PULS"}
        livestock = {"BEEF", "PORK", "POUL", "SHGM", "EGGS", "MILK", "BUTR",
                     "CHES", "SKIM", "WMLK", "CREM"}
        if comm in staples:
            return 0.1
        if comm in livestock:
            return 0.5
        return 0.3

    def compute_trade_flows(
        self,
        supply: pd.DataFrame,
        demand: pd.DataFrame,
        world_prices: pd.Series,
        domestic_prices: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Compute bilateral trade flows using Armington allocation.

        For each importing region r:
          Total imports M_r = max(0, QD_r - QS_r)
          Flow from j to r: TRD_{jr} = M_r × share_{jr}(prices)
        """
        flows_idx = pd.MultiIndex.from_product(
            [self.regions, self.regions], names=["exporter", "importer"]
        )
        flows = pd.DataFrame(0.0, index=flows_idx, columns=self.commodities)

        for comm in self.commodities:
            for importer in self.regions:
                sup = supply.at[importer, comm] if importer in supply.index else 0.0
                dem = demand.at[importer, comm] if importer in demand.index else 0.0
                total_imports = max(0.0, dem - sup)

                if total_imports < 0.001:
                    continue

                # Price of goods from each exporting origin (CIF basis)
                prices_by_origin = pd.Series({
                    exp: world_prices.get(comm, 200.0) * 1.05  # +5% transport
                    for exp in self.regions if exp != importer
                })

                arm_sys = self.armington_systems.get((importer, comm))
                if arm_sys is None:
                    # Uniform allocation
                    exporters = [r for r in self.regions if r != importer]
                    for exp in exporters:
                        flows.at[(exp, importer), comm] = total_imports / len(exporters)
                else:
                    alloc = arm_sys.import_quantities(total_imports, prices_by_origin)
                    for exp, qty in alloc.items():
                        if (exp, importer) in flows.index:
                            flows.at[(exp, importer), comm] = qty

        return flows

    # ------------------------------------------------------------------
    # Excess demand and market clearing
    # ------------------------------------------------------------------

    def excess_demand(
        self,
        world_prices: pd.Series,
        exogenous_supply: Optional[pd.DataFrame] = None,
        trade_scenario: Optional[Dict] = None,
    ) -> pd.Series:
        """
        Compute global excess demand for each commodity at given prices.
        ED_k = Σ_r QD_r(p) - Σ_r QS_r(p)
        At equilibrium: ED_k = 0 ∀ k.
        """
        dom_prices = self.domestic_prices(world_prices, trade_scenario)
        supply = self.supply_response(world_prices, exogenous_supply)
        demand = self.demand_response(dom_prices, world_prices)

        ed = {}
        for comm in self.commodities:
            total_supply = supply[comm].sum() if comm in supply.columns else 0.0
            total_demand = demand[comm].sum() if comm in demand.columns else 0.0
            ed[comm] = total_demand - total_supply

        return pd.Series(ed)

    def _calibrate_demand_to_supply(
        self,
        exogenous_supply: Optional[pd.DataFrame],
        prices: pd.Series,
        trade_scenario: Optional[Dict],
    ) -> None:
        """
        Calibrate the demand base so the base period is a market equilibrium.

        At base prices, compute world supply (including the supply-module
        override for EU27) and world demand. For each commodity, rescale the
        per-region base consumption by supply/demand so that total demand
        equals total supply at the base price. Cross-price and income terms
        in demand_response then operate as deviations around this calibrated
        base, so the solved base-period prices reproduce the reference levels.

        The scaling is stored (self._demand_cal) and applied inside
        demand_response, leaving the raw base_consumption untouched.
        """
        dom_prices = self.domestic_prices(prices, trade_scenario)
        supply = self.supply_response(prices, exogenous_supply)
        # Demand at base without any calibration factor (reset first)
        self._demand_cal = pd.Series(1.0, index=self.commodities)
        demand = self.demand_response(dom_prices, prices)

        total_supply = supply.sum(axis=0)
        total_demand = demand.sum(axis=0)

        cal = pd.Series(1.0, index=self.commodities)
        for comm in self.commodities:
            d = float(total_demand.get(comm, 0.0))
            s = float(total_supply.get(comm, 0.0))
            if d > 1.0 and s > 1.0:
                # factor that brings demand onto supply at base price
                cal[comm] = s / d
        # Clip to a sane range so a bad base datum can't distort things wildly
        self._demand_cal = cal.clip(lower=0.2, upper=5.0)

    def _demand_cal_factor(self, comm: str) -> float:
        cal = getattr(self, "_demand_cal", None)
        if cal is not None and comm in cal.index:
            return float(cal[comm])
        return 1.0

    # ------------------------------------------------------------------
    # Main solver (tatonnement / Newton)
    # ------------------------------------------------------------------

    def solve(
        self,
        exogenous_supply: Optional[pd.DataFrame] = None,
        trade_scenario: Optional[Dict] = None,
        policy_scenario: Optional[Dict] = None,
        max_iter: int = 200,
        tolerance: float = 0.010,
        step_size: float = 0.06,
        verbose: bool = False,
    ) -> MarketEquilibrium:
        """
        Solve for market equilibrium prices.

        Uses tatonnement (excess demand proportional price adjustment):
          P_{t+1} = P_t × exp(α × ED_t / QS_t)

        Convergence criterion: max|ED_k / QS_k| < tolerance

        Parameters
        ----------
        exogenous_supply : supply from supply module [region × commodity]
        trade_scenario   : {"tariff_change": {commodity: delta_pct}}
        policy_scenario  : additional policy instruments (export subsidies etc.)
        max_iter         : maximum iterations
        tolerance        : convergence threshold (relative excess demand)
        step_size        : tatonnement step (α)
        verbose          : print iteration progress
        """
        prices = self.world_prices_base.copy().astype(float)
        converged = False
        iteration = 0

        # --- Market calibration (CAPRI-style cal_market step) ---
        # Calibrate the demand base so the BASE period is an equilibrium -- but do
        # this only ONCE, against base supply, then freeze it. The previous code
        # recalibrated demand to match whatever supply was passed on every solve,
        # so a scenario supply cut was instantly matched by an equal demand cut
        # and no price ever moved (a 30% beef supply cut produced 0% price change).
        # Freezing the calibration at base means scenario supply changes create
        # genuine excess demand and the tatonnement moves prices, as a market
        # model must.
        if getattr(self, "_demand_cal_frozen", None) is None:
            base_supply = pd.DataFrame(0.0, index=["EU27"], columns=self.commodities)
            for comm in self.commodities:
                if comm in getattr(self, "base_production", pd.DataFrame()).columns:
                    base_supply.at["EU27", comm] = self.base_production.at["EU27", comm]
            self._calibrate_demand_to_supply(base_supply, prices, trade_scenario)
            self._demand_cal_frozen = self._demand_cal.copy()
        else:
            self._demand_cal = self._demand_cal_frozen.copy()

        for iteration in range(max_iter):
            dom_prices = self.domestic_prices(prices, trade_scenario)
            supply = self.supply_response(prices, exogenous_supply)
            demand = self.demand_response(dom_prices, prices)

            total_supply = supply.sum(axis=0)
            total_demand = demand.sum(axis=0)
            ed = total_demand - total_supply

            # Relative excess demand
            rel_ed = ed / total_supply.clip(lower=1.0)
            max_rel = rel_ed.abs().max()

            if verbose and iteration % 20 == 0:
                print(f"  Market iter {iteration:3d}: max|rel_ED| = {max_rel:.6f}")

            if max_rel < tolerance:
                converged = True
                break

            # Tatonnement price update: raise prices where demand > supply
            prices = prices * np.exp(step_size * rel_ed.clip(-0.3, 0.3))
            # Price floor: 50% of base price (no collapse to zero)
            price_floor = self.world_prices_base * 0.5
            prices = prices.clip(lower=price_floor)

        if verbose:
            status = "CONVERGED" if converged else "NOT CONVERGED"
            print(f"  Market module: {status} after {iteration+1} iterations")

        # Final equilibrium quantities
        dom_prices = self.domestic_prices(prices, trade_scenario)
        supply_final = self.supply_response(prices, exogenous_supply)
        demand_final = self.demand_response(dom_prices, prices)
        flows_final  = self.compute_trade_flows(
            supply_final, demand_final, prices, dom_prices
        )

        net_exports = supply_final.subtract(demand_final, fill_value=0)
        excess_dem  = demand_final.sum() - supply_final.sum()

        # Welfare decomposition (consumer surplus + producer surplus + budget)
        welfare = self._compute_welfare(
            supply_final, demand_final, prices, dom_prices, trade_scenario
        )

        return MarketEquilibrium(
            world_prices=prices,
            domestic_prices=dom_prices,
            production=supply_final,
            consumption=demand_final,
            trade_flows=flows_final,
            net_exports=net_exports,
            welfare=welfare,
            excess_demand=excess_dem,
            converged=converged,
            iterations=iteration + 1,
        )

    # ------------------------------------------------------------------
    # Welfare
    # ------------------------------------------------------------------

    def _compute_welfare(
        self,
        supply: pd.DataFrame,
        demand: pd.DataFrame,
        world_prices: pd.Series,
        domestic_prices: pd.DataFrame,
        trade_scenario: Optional[Dict] = None,
    ) -> pd.DataFrame:
        """
        Compute welfare effects (EUR million) by region.

        CS change ≈ -ΔP × QD0 - ½ΔP × ΔQD  (consumer surplus)
        PS change ≈  ΔP × QS0 + ½ΔP × ΔQS  (producer surplus)
        Budget     = tariff revenue           (government budget)
        """
        welfare_rows = []

        for region in self.regions:
            cs, ps, budget = 0.0, 0.0, 0.0

            for comm in self.commodities:
                wp0 = self.world_prices_base.get(comm, 200.0)
                wp1 = world_prices.get(comm, 200.0)
                dp0 = wp0  # baseline domestic ≈ world (no tariff change)
                dp1 = domestic_prices.at[region, comm] if (
                    region in domestic_prices.index and comm in domestic_prices.columns
                ) else wp1

                qd0 = self.base_consumption.at[region, comm] if (
                    region in self.base_consumption.index
                ) else 0.0
                qd1 = demand.at[region, comm] if region in demand.index else 0.0
                qs0 = self.base_production.at[region, comm] if (
                    region in self.base_production.index
                ) else 0.0
                qs1 = supply.at[region, comm] if region in supply.index else 0.0

                delta_p_cons = dp1 - dp0
                delta_p_prod = wp1 - wp0

                # Consumer surplus (negative when price rises)
                cs += -(delta_p_cons * qd0 + 0.5 * delta_p_cons * (qd1 - qd0))

                # Producer surplus
                ps +=  (delta_p_prod * qs0 + 0.5 * delta_p_prod * (qs1 - qs0))

                # Budget / tariff revenue
                tariff = self.tariffs.at[region, comm] if (
                    region in self.tariffs.index and comm in self.tariffs.columns
                ) else 0.0
                imports = max(0.0, qd1 - qs1)
                budget += (tariff / 100.0) * wp1 * imports

            welfare_rows.append({
                "region": region,
                "consumer_surplus": cs / 1e3,   # EUR billion
                "producer_surplus": ps / 1e3,
                "budget_effect":    budget / 1e3,
                "total_welfare":   (cs + ps + budget) / 1e3,
            })

        return pd.DataFrame(welfare_rows).set_index("region")
