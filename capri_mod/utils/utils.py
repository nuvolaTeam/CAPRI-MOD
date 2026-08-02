"""
CAPRI Utility Functions
=======================
Calibration, convergence checking, and reporting tools.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, List
import json
from pathlib import Path


# ---------------------------------------------------------------------------
# CALIBRATION UTILITIES
# ---------------------------------------------------------------------------

def calibrate_supply_elasticities(
    base_areas: pd.DataFrame,
    price_history: Optional[pd.DataFrame] = None,
    default_eps: float = 0.25,
) -> pd.Series:
    """
    Estimate supply price elasticities from price-area time series,
    or return calibrated defaults from CAPRI literature.

    If price history is provided: OLS log-log regression
      ln(A_it) = α_i + ε_i × ln(P_it) + u_it

    Reference: Jansson, T. (2007). Econometric specification of
               constrained optimisation models. Agr. Econ. 36(3).
    """
    from capri_mod.data.definitions import ALL_ACTIVITIES

    if price_history is not None and len(price_history) >= 5:
        elasticities = {}
        for activity in ALL_ACTIVITIES:
            if activity not in base_areas.columns or activity not in price_history.columns:
                elasticities[activity] = default_eps
                continue
            # Panel OLS (simplified: pooled across regions)
            areas_vec  = base_areas[activity].values.flatten()
            prices_vec = price_history[activity].values.flatten()

            valid = (areas_vec > 0) & (prices_vec > 0)
            if valid.sum() < 5:
                elasticities[activity] = default_eps
                continue

            log_a = np.log(areas_vec[valid])
            log_p = np.log(prices_vec[valid])
            # OLS: ε = Cov(ln A, ln P) / Var(ln P)
            eps = np.cov(log_a, log_p)[0, 1] / np.var(log_p)
            elasticities[activity] = float(np.clip(eps, 0.05, 1.5))
        return pd.Series(elasticities)

    # Literature-based defaults (CAPRI calibration values)
    elasticities = {
        "SWHE": 0.30, "DWHE": 0.25, "RYEM": 0.20, "BARL": 0.30,
        "OATS": 0.20, "CORN": 0.35, "OCER": 0.20, "POTA": 0.15,
        "SUGB": 0.10, "SUNF": 0.35, "RAPE": 0.35, "SOYA": 0.40,
        "OOIL": 0.25, "PULS": 0.25, "TOMA": 0.20, "OVEG": 0.18,
        "APPL": 0.12, "OFRU": 0.12, "CITR": 0.12, "TAGR": 0.15,
        "WINE": 0.10, "OLIV": 0.08, "TOBA": 0.08, "COTT": 0.20,
        "OFIB": 0.15, "GRAS": 0.05, "MAIF": 0.20, "OFOD": 0.12,
        "SETA": 0.00,
        "DCOW": 0.15, "BCOW": 0.12, "BULL": 0.18, "HFRS": 0.15,
        "CALV": 0.10, "SHGP": 0.12, "PIGS": 0.20, "PIGF": 0.22,
        "LAYS": 0.18, "BROI": 0.25, "OANIИ": 0.18,
    }
    return pd.Series(elasticities)


def calibrate_demand_elasticities(
    demand_history: Optional[pd.DataFrame] = None,
) -> pd.Series:
    """
    Demand price elasticities from literature or regression.

    Reference: OECD (2009). Methods to analyse agricultural
               commodity price volatility. Chapter 3.
    """
    # Literature-based (CAPRI Witzke & Noleppa, 2010)
    elasticities = {
        "SWHE": -0.15, "DWHE": -0.15, "BARL": -0.20, "CORN": -0.18,
        "OCER": -0.20, "RAPE": -0.22, "SUNF": -0.22, "SOYA": -0.20,
        "SUGR": -0.12, "POTA": -0.25, "PULS": -0.18,
        "TOMA": -0.30, "OVEG": -0.28, "APPL": -0.30, "OFRU": -0.28,
        "CITR": -0.25, "WINE": -0.35, "OLIV": -0.30,
        "MILK": -0.12, "BUTR": -0.18, "SKIM": -0.15, "CHES": -0.22,
        "WHEY": -0.10, "BEEF": -0.40, "PORK": -0.35, "POUL": -0.30,
        "SHGM": -0.35, "EGGS": -0.20, "FATS": -0.18,
    }
    return pd.Series(elasticities)


# ---------------------------------------------------------------------------
# CONVERGENCE CHECKING
# ---------------------------------------------------------------------------

class ConvergenceTracker:
    """
    Track and report convergence of the supply-market iteration loop.

    CAPRI uses a tatonnement-style outer loop:
      1. Market module provides prices → Supply module
      2. Supply module provides quantities → Market module
      3. Repeat until prices and quantities converge
    """

    def __init__(self, tolerance: float = 0.001, max_iter: int = 50):
        self.tolerance  = tolerance
        self.max_iter   = max_iter
        self.history: List[Dict] = []

    def record(self, iteration: int, prices: pd.Series, quantities: pd.Series):
        self.history.append({
            "iteration": iteration,
            "prices": prices.copy(),
            "quantities": quantities.copy(),
        })

    def check_convergence(self) -> bool:
        """
        Check if last two iterations are within tolerance.
        """
        if len(self.history) < 2:
            return False

        prev = self.history[-2]
        curr = self.history[-1]

        price_change = (
            (curr["prices"] - prev["prices"]).abs() /
            prev["prices"].clip(lower=1.0)
        ).max()

        qty_change = (
            (curr["quantities"] - prev["quantities"]).abs() /
            prev["quantities"].clip(lower=1.0)
        ).max()

        return bool(max(price_change, qty_change) < self.tolerance)

    def summary(self) -> pd.DataFrame:
        """Return convergence history as DataFrame."""
        rows = []
        for i in range(1, len(self.history)):
            prev = self.history[i-1]
            curr = self.history[i]
            price_change = (
                (curr["prices"] - prev["prices"]).abs() /
                prev["prices"].clip(lower=1.0)
            ).max()
            rows.append({
                "iteration": curr["iteration"],
                "max_price_change": price_change,
            })
        return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# REPORTING
# ---------------------------------------------------------------------------

class ResultsReporter:
    """Format and export CAPRI results."""

    def __init__(self, results: Dict):
        self.results = results

    def supply_summary(self, by_country: bool = True) -> pd.DataFrame:
        """Aggregate supply results."""
        from capri_mod.data.definitions import REGION_TO_COUNTRY

        supply_results = self.results.get("supply", {})
        if not supply_results:
            return pd.DataFrame()

        rows = []
        for region, res in supply_results.items():
            country = REGION_TO_COUNTRY.get(region, region) if by_country else region
            row = {"region" if not by_country else "country": country}
            row.update(res.gross_output.to_dict())
            row["gross_margin_EUR_1000"] = res.gross_margin
            rows.append(row)

        df = pd.DataFrame(rows)
        key = "country" if by_country else "region"
        if by_country and key in df.columns:
            df = df.groupby(key).sum(numeric_only=True)
        return df

    def market_summary(self) -> pd.DataFrame:
        """Market module equilibrium summary."""
        market_eq = self.results.get("market")
        if market_eq is None:
            return pd.DataFrame()

        return pd.DataFrame({
            "world_price_EUR_t": market_eq.world_prices,
            "excess_demand_1000t": market_eq.excess_demand,
        })

    def welfare_summary(self) -> pd.DataFrame:
        """Welfare effects by trade region (EUR billion)."""
        market_eq = self.results.get("market")
        if market_eq is None:
            return pd.DataFrame()
        return market_eq.welfare

    def environmental_summary(self, aggregate: bool = True) -> pd.DataFrame:
        """Environmental indicators, optionally aggregated to EU total."""
        env_df = self.results.get("environmental")
        if env_df is None or env_df.empty:
            return pd.DataFrame()

        if aggregate:
            numeric = env_df.select_dtypes(include=[np.number])
            total = numeric.sum()
            return total.to_frame("EU_total")

        return env_df

    def print_summary(self):
        """Print a concise results summary to stdout."""
        print("\n" + "=" * 60)
        print("CAPRI-Python: Results Summary")
        print("=" * 60)

        # Market prices
        market_eq = self.results.get("market")
        if market_eq:
            key_comms = ["SWHE","CORN","RAPE","BEEF","PORK","MILK"]
            print("\n[Market Module] Equilibrium World Prices (EUR/t):")
            for c in key_comms:
                p = market_eq.world_prices.get(c, np.nan)
                print(f"  {c:8s}: {p:8.1f}")

            print(f"\n  Iterations: {market_eq.iterations}")
            print(f"  Converged:  {market_eq.converged}")

        # Supply
        supply_res = self.results.get("supply", {})
        if supply_res:
            n = len(supply_res)
            n_ok = sum(1 for r in supply_res.values() if r.converged)
            total_gm = sum(r.gross_margin for r in supply_res.values()) / 1e6
            print(f"\n[Supply Module] {n} regions solved ({n_ok} converged)")
            print(f"  Total EU farm gross margin: EUR {total_gm:.1f} billion")

        # Environmental
        env_df = self.results.get("environmental")
        if env_df is not None and not env_df.empty:
            total_ghg = env_df["ghg_total"].sum() / 1000  # Mt CO2-eq
            total_n_surplus = env_df["n_surplus"].sum()
            print(f"\n[Environmental Module]")
            print(f"  Total GHG: {total_ghg:.1f} Mt CO2-eq")
            print(f"  Total N surplus: {total_n_surplus:.0f} kt N")

        print("=" * 60 + "\n")

    def to_excel(self, path: str):
        """Export all results to Excel workbook."""
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            # Supply
            supply_df = self.supply_summary(by_country=True)
            if not supply_df.empty:
                supply_df.to_excel(writer, sheet_name="Supply_by_Country")

            # Market
            market_df = self.market_summary()
            if not market_df.empty:
                market_df.to_excel(writer, sheet_name="Market_Prices")

            # Welfare
            welfare_df = self.welfare_summary()
            if not welfare_df.empty:
                welfare_df.to_excel(writer, sheet_name="Welfare")

            # Environmental
            env_df = self.results.get("environmental")
            if env_df is not None and not env_df.empty:
                env_df.to_excel(writer, sheet_name="Environmental")

        print(f"Results exported to: {path}")

    def to_csv_folder(self, folder: str):
        """Export each result table as a separate CSV."""
        out = Path(folder)
        out.mkdir(parents=True, exist_ok=True)

        supply_df = self.supply_summary(by_country=True)
        if not supply_df.empty:
            supply_df.to_csv(out / "supply_by_country.csv")

        market_df = self.market_summary()
        if not market_df.empty:
            market_df.to_csv(out / "market_prices.csv")

        welfare_df = self.welfare_summary()
        if not welfare_df.empty:
            welfare_df.to_csv(out / "welfare.csv")

        env_df = self.results.get("environmental")
        if env_df is not None and not env_df.empty:
            env_df.to_csv(out / "environmental.csv")

        print(f"Results saved to: {folder}/")
