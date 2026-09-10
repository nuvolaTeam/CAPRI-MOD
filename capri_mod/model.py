"""
CAPRI-mod: Main Model Coordinator
=====================================
Top-level class that orchestrates the supply-market iteration loop,
connecting all modules:

  PolicyModule → SupplyModule → MarketModule → EnvironmentalModule
       ↑_______________(price feedback)_____________________|

The iterative loop follows CAPRI's original GAMS implementation:
  1. Policy module computes CAP payment rates + tariffs
  2. Supply module solves all ~280 regional NLPs given prices + payments
  3. Market module receives EU supply, clears world markets
  4. Market prices fed back to supply module
  5. Iterate until convergence (prices, quantities stable)
  6. Environmental module computes indicators on final allocation

Usage
-----
    from capri_mod import CAPRIModel

    # Load your own data directory (or use synthetic data)
    model = CAPRIModel(data_dir="path/to/your/data")

    # Run baseline
    baseline = model.run(scenario="BASELINE")

    # Run a policy counterfactual
    f2f = model.run(scenario="FARM_TO_FORK")

    # Compare
    model.compare(baseline, f2f)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List
import time

from capri_mod.data.loaders import load_all_data
from capri_mod.supply.supply_module import SupplyModule
from capri_mod.market.market_module import MarketModule
from capri_mod.policy.policy_module import PolicyModule, PolicyScenario
from capri_mod.environmental.environmental_module import EnvironmentalModule
from capri_mod.utils.utils import (
    calibrate_supply_elasticities, ConvergenceTracker, ResultsReporter
)
from capri_mod.scenarios.scenarios import get_scenario, list_scenarios


#: Nitrates Directive ceiling on organic N application (kg N per ha of UAA)
NITRATES_DIRECTIVE_N_LIMIT = 170.0


class CAPRIModel:
    """
    CAPRI-mod: Common Agricultural Policy Regionalised Impact Model.

    Partial equilibrium model for ex-ante policy impact assessment.

    Parameters
    ----------
    data_dir : path to directory containing CSV data files
               (from Eurostat, FADN, FAOSTAT, COMTRADE).
               If None, synthetic baseline data is used.
    regions   : subset of NUTS-2 regions to run (default: all ~280)
    verbose   : print progress messages
    """

    def __init__(
        self,
        data_dir: Optional[str] = None,
        regions: Optional[List[str]] = None,
        verbose: bool = True,
        base_year: str = "2017",
        data: Optional[Dict] = None,
    ):
        """
        Parameters
        ----------
        data : dict, optional
            A prepared data dict to use instead of loading from disk. The
            projection layer passes a *projected* data set here so that the
            supply and market modules (and the PMP calibration) are built from
            it — swapping the dict on an existing model would leave the modules
            calibrated on the base year and silently return base-year results.
        """
        self.verbose   = verbose
        self.data_dir  = Path(data_dir) if data_dir else None
        self.regions   = regions
        self.base_year = base_year

        if verbose:
            print("CAPRI-mod: Initialising model...")

        # Load all data (base_year selects the capri_data/<year>/ folder),
        # unless a prepared data set was supplied.
        self.data = data if data is not None else load_all_data(
            self.data_dir, base_year=base_year)

        # If region subset specified, filter data
        if regions:
            self._filter_regions(regions)

        # Calibrate supply elasticities
        self.supply_elasticities = calibrate_supply_elasticities(self.data["areas"])

        # Initialise modules
        self.supply_module = SupplyModule(self.data, self.supply_elasticities)
        self.market_module = MarketModule(self.data)
        self.policy_module = PolicyModule(self.data)
        self.env_module    = EnvironmentalModule(self.data)
        try:
            from capri_mod.feed.feed_module import FeedModule
            self.feed_module = FeedModule(self.data)
        except Exception:
            self.feed_module = None
        try:
            from capri_mod.biofuel.biofuel_module import BiofuelModule
            self.biofuel_module = BiofuelModule(self.data)
        except Exception:
            self.biofuel_module = None
        # Technological abatement (EcAMPA measures) — loaded if the measure file
        # is present; the economic MACC module is constructed on demand in run()
        # since it needs the calibrated supply module.
        try:
            from capri_mod.abatement import TechnologicalAbatement
            self.tech_abatement = TechnologicalAbatement.from_data_dir(
                data_dir, base_year=getattr(self, "base_year", "2017"))
        except Exception:
            self.tech_abatement = None

        if verbose:
            n_regions = len(self.data["areas"])
            print(f"  Regions: {n_regions} NUTS-2 regions")
            print(f"  Commodities: {len(self.data['areas'].columns)} crop activities")
            print(f"  Trade regions: {len(self.data['trade_flows'].index.get_level_values(0).unique())}")
            print("  Model ready.\n")

    def _filter_regions(self, regions: List[str]):
        """Filter all data to specified region subset."""
        for key in ["areas", "animal_numbers", "yields", "land",
                    "cap_payments"]:
            df = self.data.get(key)
            if df is not None and hasattr(df, "index"):
                valid = [r for r in regions if r in df.index]
                self.data[key] = df.loc[valid]

    # ------------------------------------------------------------------
    # MAIN RUN METHOD
    # ------------------------------------------------------------------

    def run(
        self,
        scenario: str = "BASELINE",
        world_price_shock: Optional[Dict[str, float]] = None,
        custom_scenario: Optional[PolicyScenario] = None,
        max_outer_iter: int = 15,
        outer_tolerance: float = 0.005,
        market_max_iter: int = 150,
        run_environmental: bool = True,
        run_feed: bool = False,
        run_biofuel: bool = False,
        run_abatement: bool = False,
        carbon_price: float = 0.0,
        biofuel_mandate: float = 0.065,
        regions: Optional[List[str]] = None,
    ) -> Dict:
        """
        Run a full CAPRI simulation.

        Parameters
        ----------
        scenario          : scenario name (see list_scenarios())
        world_price_shock : {commodity: relative_change} applied to world prices
        custom_scenario   : custom PolicyScenario object (overrides 'scenario')
        max_outer_iter    : max iterations of supply-market loop
        outer_tolerance   : convergence tolerance for outer loop
        market_max_iter   : max iterations inside market module solver
        run_environmental : also compute environmental indicators
        regions           : region subset (default: all)

        Returns
        -------
        dict with keys: supply, market, environmental, policy_summary, metadata
        """
        t_start = time.time()

        # Get scenario
        if custom_scenario is not None:
            pol_scenario = custom_scenario
        else:
            pol_scenario = get_scenario(scenario)

        if self.verbose:
            print(f"Running scenario: {pol_scenario.name}")
            print(f"  {pol_scenario.description}")

        # Apply policy scenario
        self.policy_module.apply_scenario(pol_scenario)

        # Get policy adders (CAP payments → supply module net revenues)
        # CAP support enters the supply model as a DELTA from the baseline
        # policy, not as an absolute level.
        #
        # The calibrated net revenue already contains cap_premium (SWHE base
        # 490.1 of which 322.1 is CAP). get_supply_policy_adders() returns the
        # ABSOLUTE payment (332.2), and the solve ADDS it to cap_premium — so
        # every scenario run through the model was double-counting CAP support
        # and inflating wheat supply ~29% against a no-policy solve. That
        # distortion sat in the BASELINE too, so scenario-vs-baseline
        # comparisons were measuring the double-count rather than the policy.
        #
        # Differencing against the baseline policy leaves the calibrated base
        # untouched (a BASELINE run gets a zero delta) while a scenario gets
        # exactly its own change: a -100 EUR/ha BISS cut yields -125.0 on wheat.
        from capri_mod.policy.policy_module import PolicyModule as _PM, \
            PolicyScenario as _PS
        _baseline_adders = _PM(self.data, _PS(name="BASELINE")) \
            .get_supply_policy_adders()
        policy_adders = (self.policy_module.get_supply_policy_adders()
                         - _baseline_adders)
        effective_tariffs = self.policy_module.get_effective_tariffs()

        # Trade scenario for market module
        trade_scenario = None
        if pol_scenario.tariff_changes:
            trade_scenario = {"tariff_change": {
                comm: delta
                for region_changes in pol_scenario.tariff_changes.values()
                for comm, delta in region_changes.items()
            }}

        # World price shock
        world_prices_current = self.data["world_prices"].copy()
        if world_price_shock:
            for comm, shock in world_price_shock.items():
                if comm in world_prices_current.index:
                    world_prices_current[comm] *= (1 + shock)

        # Override market module base prices if shocked
        if world_price_shock:
            self.market_module.world_prices_base = world_prices_current

        # ---- Outer iteration loop ----
        tracker = ConvergenceTracker(
            tolerance=outer_tolerance, max_iter=max_outer_iter
        )

        # Initial price signal = world prices
        price_signal = pd.Series(0.0, index=self.data["world_prices"].index)
        supply_results = None
        market_eq = None

        for outer_iter in range(max_outer_iter):
            if self.verbose:
                print(f"  Outer iteration {outer_iter + 1}/{max_outer_iter}")

            # --- Step 1: Supply module ---
            if self.verbose:
                print("    [Supply] Solving regional models...")
            supply_results = self.supply_module.run(
                price_signals=price_signal if outer_iter > 0 else None,
                policy_scenario={
                    "adders": policy_adders.to_dict(),
                    # mandatory non-productive share (CAP GAEC 8 / F2F landscape
                    # elements); binds the arable land constraint in the solve
                    "set_aside_requirement": float(
                        getattr(pol_scenario, "set_aside_requirement", 0.0) or 0.0),
                    # Nitrogen ceiling, as a DELTA in kg N/ha of UAA applied to
                    # each region's OWN observed base-year N intensity.
                    #
                    # It is deliberately not anchored to the 170 kg N/ha Nitrates
                    # Directive figure: that limit applies to ORGANIC (manure) N,
                    # whereas the constraint here acts on TOTAL N from the
                    # nutrient coefficients, which legitimately exceeds it (FR10
                    # sits at 178 kg N/ha in the base year). Anchoring to 170
                    # made the constraint bind on the BASE YEAR itself, so a
                    # -30 kg/ha scenario collapsed wheat by 75% against CAPRI's
                    # -1.9% — a ~60x over-response traced to this error.
                    #
                    # Anchoring to observed intensity means an unchanged scenario
                    # is slack by construction and a delta tightens from where
                    # each region actually is.
                    # Farm-to-Fork organic AREA target (share of UAA); adjusts
                    # average I/O coefficients in proportion to the share, as
                    # CAPRI does in organic_io.gms.
                    # Farm-to-Fork nutrient-surplus target: CAPRI's tiered GNB
                    # rule, resolved per region inside the solve because the
                    # target depends on each region's own surplus.
                    "nutrient_surplus_target": bool(
                        getattr(pol_scenario, "nutrient_surplus_target", False)),
                    # Farm-to-Fork pesticide target: only the yield-loss
                    # channel is represented (no plant-protection cost exists in
                    # this model's aggregate variable costs).
                    "pesticide_reduction": float(
                        getattr(pol_scenario, "pesticide_reduction", 0.0) or 0.0),
                    "organic_area_target": float(
                        getattr(pol_scenario, "organic_area_target", 0.0) or 0.0),
                    "nitrate_limit_delta": (
                        float(getattr(pol_scenario, "nitrate_limit_change", 0.0) or 0.0)
                        or None),
                },
                regions=regions or list(self.data["areas"].index),
                verbose=self.verbose,
            )

            # Aggregate EU supply for market module
            eu_supply_agg = self.supply_module.aggregate_supply(
                supply_results, by_country=True
            )

            # Map to market commodities (simplified bridge)
            eu_supply_market = self._bridge_supply_to_market(eu_supply_agg)

            # --- Step 2: Market module ---
            if self.verbose:
                print("    [Market] Solving spatial equilibrium...")
            market_eq = self.market_module.solve(
                exogenous_supply=eu_supply_market,
                trade_scenario=trade_scenario,
                max_iter=market_max_iter,
                verbose=self.verbose,
            )

            # --- Convergence check ---
            # Price signal for next supply iteration = relative deviation from base
            new_prices = market_eq.world_prices
            base_prices = self.data["world_prices"]
            price_signal = (new_prices - base_prices) / base_prices.clip(lower=1.0)

            # Aggregate quantities for convergence
            agg_qty = eu_supply_market.sum() if eu_supply_market is not None \
                      else pd.Series(dtype=float)

            tracker.record(outer_iter, new_prices, agg_qty)

            if outer_iter > 0 and tracker.check_convergence():
                if self.verbose:
                    print(f"  ✓ Outer loop converged at iteration {outer_iter + 1}")
                break
        else:
            if self.verbose:
                print(f"  ⚠ Outer loop did not fully converge in {max_outer_iter} iterations")

        # --- Step 3: Environmental module ---
        env_df = None
        if run_environmental and supply_results:
            if self.verbose:
                print("  [Environmental] Computing indicators...")
            env_df = self.env_module.run_all_regions(
                supply_results, verbose=self.verbose
            )

        # --- Step 4: Feed module ---
        feed_df = None
        if run_feed and supply_results and self.feed_module is not None:
            if self.verbose:
                print("  [Feed] Balancing feed demand vs availability...")
            try:
                feed_df = self.feed_module.run_all_regions(
                    supply_results, verbose=self.verbose
                )
            except Exception as e:
                if self.verbose:
                    print(f"  [Feed] skipped: {e}")

        # --- Step 5: Biofuel module ---
        biofuel_result = None
        if run_biofuel and self.biofuel_module is not None:
            if self.verbose:
                print("  [Biofuel] Computing mandate-driven feedstock demand...")
            try:
                biofuel_result = self.biofuel_module.run(mandate_share=biofuel_mandate)
            except Exception as e:
                if self.verbose:
                    print(f"  [Biofuel] skipped: {e}")

        # --- Step 6: Abatement module ---
        # Technological abatement applies EcAMPA measures to the computed
        # emissions; the economic response to a carbon price is available via the
        # standalone AbatementModule (a full MACC sweep is expensive, so it is
        # not run inline — see docs). Here we report technological abatement of
        # the run's emissions, activity-resolved for enteric CH4.
        abatement_result = None
        if run_abatement and run_environmental and env_df is not None \
                and self.tech_abatement is not None:
            if self.verbose:
                print("  [Abatement] Applying EcAMPA technological measures...")
            try:
                abatement_result = self._run_abatement(supply_results, env_df)
            except Exception as e:
                if self.verbose:
                    print(f"  [Abatement] skipped: {e}")

        # --- Policy summary ---
        policy_summary = self.policy_module.summarise_policy()

        t_elapsed = time.time() - t_start

        results = {
            "scenario": pol_scenario.name,
            "supply": supply_results,
            "market": market_eq,
            "environmental": env_df,
            "feed": feed_df,
            "biofuel": biofuel_result,
            "abatement": abatement_result,
            "policy_summary": policy_summary,
            "convergence": tracker.summary(),
            "metadata": {
                "n_regions": len(supply_results) if supply_results else 0,
                "n_outer_iterations": outer_iter + 1,
                "market_converged": market_eq.converged if market_eq else False,
                "elapsed_seconds": round(t_elapsed, 1),
            },
        }

        if self.verbose:
            reporter = ResultsReporter(results)
            reporter.print_summary()
            print(f"  Run completed in {t_elapsed:.1f}s")

        return results

    def _run_abatement(self, supply_results, env_df):
        """Apply EcAMPA technological measures to the run's emissions.

        Aggregates per-source GHG emissions across all regions — including
        per-animal enteric CH4 so feed measures are activity-resolved — and
        applies the technological measures at full uptake. Returns the
        TechnicalAbatementResult, which reports abatement per measure with EcAMPA
        page citations. The economic (carbon-price) MACC is a separate, expensive
        sweep and is not run inline; use capri_mod.abatement.AbatementModule for
        it.
        """
        import pandas as pd
        # aggregate emissions by source and enteric by animal across regions
        sources = {}
        enteric = {}
        for region, res in supply_results.items():
            acts = res.activities if hasattr(res, "activities") else res
            if not isinstance(acts, pd.Series):
                acts = pd.Series(acts)
            # add herd numbers so enteric is computed (supply activities are
            # crops; animal numbers live in the data layer). Drop any animal
            # codes already present in acts to avoid duplicate index labels.
            if "animal_numbers" in self.data and region in self.data["animal_numbers"].index:
                herds = self.data["animal_numbers"].loc[region]
                herds = herds[[a for a in herds.index if a not in acts.index]]
                acts = pd.concat([acts, herds])
            ghg = self.env_module.compute_ghg(acts, region)
            for k, v in ghg.items():
                sources[k] = sources.get(k, 0.0) + v
            for a, v in self.env_module.enteric_ch4_by_animal(acts).items():
                enteric[a] = enteric.get(a, 0.0) + v
        return self.tech_abatement.apply(
            sources, uptake_scale=1.0, enteric_by_animal=enteric)

    # ------------------------------------------------------------------
    # SCENARIO COMPARISON
    # ------------------------------------------------------------------
    def compare(
        self,
        baseline_results: Dict,
        scenario_results: Dict,
        output_path: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Compare two scenario results, computing absolute and relative differences.

        Returns a DataFrame of key indicator changes.
        """
        diffs = {}

        # Market prices
        if baseline_results.get("market") and scenario_results.get("market"):
            b_prices = baseline_results["market"].world_prices
            s_prices = scenario_results["market"].world_prices
            for comm in b_prices.index:
                bp = b_prices.get(comm, np.nan)
                sp = s_prices.get(comm, np.nan)
                if bp and not np.isnan(bp) and bp > 0:
                    diffs[f"price_{comm}_pct"] = 100 * (sp - bp) / bp

        # EU farm income
        b_supply = baseline_results.get("supply", {})
        s_supply = scenario_results.get("supply", {})
        if b_supply and s_supply:
            b_income = sum(r.gross_margin for r in b_supply.values()) / 1e6
            s_income = sum(r.gross_margin for r in s_supply.values()) / 1e6
            diffs["farm_income_EUR_billion_change"] = s_income - b_income
            diffs["farm_income_pct_change"] = 100 * (s_income - b_income) / max(b_income, 1)

        # Welfare
        b_mkt = baseline_results.get("market")
        s_mkt = scenario_results.get("market")
        if b_mkt and s_mkt and hasattr(b_mkt, "welfare") and hasattr(s_mkt, "welfare"):
            b_w = b_mkt.welfare["total_welfare"].sum()
            s_w = s_mkt.welfare["total_welfare"].sum()
            diffs["welfare_EUR_billion_change"] = s_w - b_w

        # Environmental
        b_env = baseline_results.get("environmental")
        s_env = scenario_results.get("environmental")
        if b_env is not None and s_env is not None and not b_env.empty and not s_env.empty:
            for col in ["ghg_total", "n_surplus", "nh3_total"]:
                if col in b_env.columns and col in s_env.columns:
                    b_val = b_env[col].sum()
                    s_val = s_env[col].sum()
                    diffs[f"{col}_pct_change"] = 100 * (s_val - b_val) / max(b_val, 1)

        comparison = pd.Series(diffs, name=f"{baseline_results['scenario']} → {scenario_results['scenario']}")

        if self.verbose:
            print("\n=== Scenario Comparison ===")
            print(f"  {baseline_results['scenario']} → {scenario_results['scenario']}")
            for key, val in diffs.items():
                print(f"  {key:45s}: {val:+.2f}")
            print()

        if output_path:
            comparison.to_csv(output_path)
            print(f"Comparison saved to: {output_path}")

        return comparison

    # ------------------------------------------------------------------
    # BRIDGE: Supply → Market commodities
    # ------------------------------------------------------------------

    def _bridge_supply_to_market(
        self,
        supply_agg: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Map supply module activity gross outputs (crops/animals) to
        market module commodity definitions.

        Some activities produce multiple commodities (e.g. oilseeds → oil + meal).
        Animals produce meat, milk, eggs.
        """
        from capri_mod.data.definitions import MARKET_COMMODITIES

        market_supply = pd.DataFrame(0.0,
                                      index=supply_agg.index,
                                      columns=MARKET_COMMODITIES)

        # Direct mappings (activity → market commodity)
        direct_maps = {
            "SWHE": "SWHE", "DWHE": "DWHE", "BARL": "BARL",
            "CORN": "CORN", "OCER": "OCER", "RAPE": "RAPE",
            "SUNF": "SUNF", "SOYA": "SOYA", "OOIL": "OOIL",
            "SUGB": "SUGB", "POTA": "POTA", "PULS": "PULS",
            "TOMA": "TOMA", "OVEG": "OVEG", "APPL": "APPL",
            "OFRU": "OFRU", "CITR": "CITR", "WINE": "WINE",
            "OLIV": "OLIV",
        }

        for act, mcomm in direct_maps.items():
            if act in supply_agg.columns and mcomm in market_supply.columns:
                market_supply[mcomm] = supply_agg[act]

        # Processing splits from FAO Commodity Balances (real EU crush yields
        # and dairy product ratios). Loaded once and cached on the model.
        splits = getattr(self, "_processing_splits", None)
        if splits is None:
            splits = {}
            try:
                import json
                from pathlib import Path
                from capri_mod.data.loaders import resolve_data_file
                base = Path(self.data_dir) if getattr(self, "data_dir", None) \
                    else Path(__file__).parent.parent / "capri_data"
                f = resolve_data_file(base, "fao_processing_splits.json",
                                      base_year=getattr(self, "base_year", "2017"))
                if f is not None and f.exists():
                    splits = json.load(open(f))
            except Exception:
                splits = {}
            self._processing_splits = splits
        eu = splits.get("_EU_AVG", {})

        # Oilseeds → oil + meal, using real crush yields where the oil/meal
        # commodities exist; otherwise keep seed-equivalent supply.
        rape_oil = eu.get("rape_oil_yield", 0.42)
        sun_oil  = eu.get("sun_oil_yield", 0.42)
        soya_oil = eu.get("soya_oil_yield", 0.18)
        if "RAPE" in supply_agg.columns:
            market_supply["RAPE"] = supply_agg["RAPE"] * rape_oil
        if "SUNF" in supply_agg.columns:
            market_supply["SUNF"] = supply_agg["SUNF"] * sun_oil
        if "SOYA" in supply_agg.columns:
            market_supply["SOYA"] = supply_agg["SOYA"]

        # Sugar beet → white sugar (~13.5% extraction rate)
        if "SUGB" in supply_agg.columns:
            market_supply["SUGB"] = supply_agg["SUGB"]
            if "SUGR" in market_supply.columns:
                market_supply["SUGR"] = supply_agg["SUGB"] * 0.135

        # Dairy: DCOW gross output -> milk tonnes via a calibrated factor, then
        # split into products with real FAO ratios. DCOW gross_output is already
        # a (per-animal, non-tonne) unit, so a single calibrated factor maps it
        # to base milk production; re-multiplying by a raw milk yield here would
        # double-convert (it inflated milk ~1.3x and all dairy products with it).
        if "DCOW" in supply_agg.columns:
            milk = supply_agg["DCOW"] * 0.9575  # calibrated to EU27 market slot
            if "MILK" in market_supply.columns:
                market_supply["MILK"] = milk
            if "BUTR" in market_supply.columns:
                market_supply["BUTR"] = milk * eu.get("milk_to_butter", 0.0116)
            if "SKIM" in market_supply.columns:
                # SKIM commodity is skim-milk POWDER, not skimmed liquid milk.
                market_supply["SKIM"] = milk * 0.013
            if "CHES" in market_supply.columns:
                market_supply["CHES"] = milk * eu.get("milk_to_cheese", 0.0456)

        # Beef: from cattle activities. Head counts must be converted to carcass
        # tonnage — previously heads were equated directly to BEEF tonnes, which
        # inflated EU beef supply ~300x and drove market non-convergence. The
        # per-head factor is calibrated so the bridge reproduces base production
        # (EU average carcass yield over the whole cattle herd, incl. cows/calves).
        beef_acts = ["BULL", "BCOW", "HFRS", "CALV"]
        beef_total = sum(
            supply_agg[a] for a in beef_acts if a in supply_agg.columns
        )
        if "BEEF" in market_supply.columns:
            market_supply["BEEF"] = beef_total * 0.00034961  # calibrated to EU27 market slot

        # Pork
        pig_acts = ["PIGS", "PIGF"]
        pork_total = sum(
            supply_agg[a] for a in pig_acts if a in supply_agg.columns
        )
        if "PORK" in market_supply.columns:
            market_supply["PORK"] = pork_total * 0.00004116  # calibrated to EU27 market slot

        # Poultry — heads to carcass tonnage (calibrated to base production)
        poul_acts = ["BROI", "OANI"]
        poul_total = sum(
            supply_agg[a] for a in poul_acts if a in supply_agg.columns
        )
        if "POUL" in market_supply.columns:
            market_supply["POUL"] = poul_total * 0.00004633  # calibrated to EU27 market slot

        # Sheep and goat meat — heads to carcass tonnage
        if "SHGP" in supply_agg.columns and "SHGM" in market_supply.columns:
            market_supply["SHGM"] = supply_agg["SHGP"] * 0.00063104  # calibrated to EU27 market slot

        # Eggs — layers to egg tonnage (t eggs / layer / yr)
        if "LAYS" in supply_agg.columns and "EGGS" in market_supply.columns:
            market_supply["EGGS"] = supply_agg["LAYS"] * 0.00000836  # calibrated to EU27 market slot

        return market_supply

    # ------------------------------------------------------------------
    # CONVENIENCE
    # ------------------------------------------------------------------

    @staticmethod
    def list_scenarios() -> List[str]:
        """List all available built-in scenarios."""
        return list_scenarios()

    def get_reporter(self, results: Dict) -> ResultsReporter:
        """Get a ResultsReporter for exporting results."""
        return ResultsReporter(results)
