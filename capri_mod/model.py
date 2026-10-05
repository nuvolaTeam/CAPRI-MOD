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
import warnings
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

    #: CAPRI's land market, on by default as in CAPRI (p_landIsFixedinScenario
    #: = 0 in supply/def_supply_model_par.gms): land-type areas are variables
    #: with CAPRI's land-market costs (docs/LAND_USE_FLEXIBILITY.md). Set False
    #: to hold land fixed.
    use_land_market = True
    #: permanent-grassland decline allowed under the Green Deal (CAPRI default 0)
    grassland_allowance = 0.0
    #: EU feed ration chosen at current feed prices (capri_mod/feed/ration.py),
    #: on by default as in CAPRI, where rations are always endogenous in the
    #: supply models. Set False for fixed rations per head.
    use_ration = True

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
            from capri_mod.abatement.capri_mitigation import CapriAbatement as _CA
            self.capri_abatement = _CA.from_data_dir(
                data_dir or Path(__file__).parent.parent / "capri_data")
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

    #: Relaxation on the supply price signal between outer iterations.
    PRICE_SIGNAL_RELAXATION = 0.5

    def run(
        self,
        scenario: str = "BASELINE",
        world_price_shock: Optional[Dict[str, float]] = None,
        custom_scenario: Optional[PolicyScenario] = None,
        max_outer_iter: int = 25,
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
        self._run_carbon_price = float(carbon_price or 0.0) or None
        self.policy_module.apply_scenario(pol_scenario)

        # EU Armington premium needs the EU's BASE supply and demand at this
        # model's own levels, for the same region set. A baseline run records
        # them at convergence; a scenario run uses them, running a baseline
        # first if none is cached. In a baseline run the premium stays off,
        # so the baseline is exactly what it was.
        _key = tuple(sorted(regions or list(self.data["areas"].index)))
        _is_base = (custom_scenario is None and str(scenario).upper() == "BASELINE")
        _cache = getattr(self, "_eu_base_cache", {})
        self._eu_base_cache = _cache
        _mm = self.market_module
        if _is_base:
            _mm._eu_base_supply = None
            _mm._eu_base_demand = None
            # Recalibrate at THIS run's first market solve. The calibration used
            # to freeze at the first solve an instance ever performed, so a model
            # whose first run was price-shocked or on a region subset carried a
            # calibration taken at the wrong point into every later run - results
            # depended on the instance's history (a null-trajectory projection,
            # built on a fresh instance, then differed from the base by 0.06%).
            _mm._demand_cal_frozen = None
            # ...and restore the market's PRISTINE base tables: EU rows of
            # commodities without farm-model supply are not re-aligned per run
            # and carried an earlier run's values (a model with a full-region
            # run in its history had different EU oil and cake consumption
            # than a fresh one; with crushing this reached farm results).
            if getattr(_mm, "_base_production0", None) is not None:
                _mm.base_production = _mm._base_production0.copy()
                _mm.base_consumption = _mm._base_consumption0.copy()
                _mm._dom0_cache = None          # base domestic prices for the feed terms
                _mm._eu_aligned_use = None      # re-recorded by this run's alignment
        else:
            if _key not in _cache:
                _saved = self.verbose
                self.verbose = False
                self.run(scenario="BASELINE", regions=regions,
                         max_outer_iter=max_outer_iter)
                self.verbose = _saved
                self.policy_module.apply_scenario(pol_scenario)
            self.market_module.set_eu_base(*_cache[_key][:2])
            # reuse the calibration of the baseline for the same region set
            if len(_cache[_key]) > 2:
                _cal, _bp, _bc = _cache[_key][2:]
                _mm._demand_cal_frozen = _cal.copy()
                _mm.base_production.loc["EU27"] = _bp
                _mm.base_consumption.loc["EU27"] = _bc

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

        # Market base world prices for THIS run. A shocked run used to overwrite
        # them and nothing restored them, so every later run on the same model
        # silently inherited the shock (a baseline after a +20% wheat-price run
        # gave DE11 wheat 111.2 instead of 91.2). Each run now starts from the
        # true base and applies only its own shock.
        _mm = self.market_module
        if getattr(_mm, "_world_prices_base0", None) is None:
            _mm._world_prices_base0 = _mm.world_prices_base.copy()
        _wpb = _mm._world_prices_base0.copy()
        if world_price_shock:
            for comm, shock in world_price_shock.items():
                if comm in _wpb.index:
                    _wpb[comm] *= (1 + shock)
        _mm.world_prices_base = _wpb

        # ---- Outer iteration loop ----
        tracker = ConvergenceTracker(
            tolerance=outer_tolerance, max_iter=max_outer_iter
        )

        # Initial price signal = world prices
        price_signal = pd.Series(0.0, index=self.data["world_prices"].index)
        supply_results = None
        market_eq = None

        outer_converged = False
        for outer_iter in range(max_outer_iter):
            if self.verbose:
                print(f"  Outer iteration {outer_iter + 1}/{max_outer_iter}")

            # --- Step 1: Supply module ---
            if self.verbose:
                print("    [Supply] Solving regional models...")
            self.supply_module.use_land_market = getattr(self, "use_land_market", False)
            self.supply_module.grassland_allowance = getattr(self, "grassland_allowance", 0.0)
            if getattr(self, "use_ration", False):
                self._update_rations(price_signal if outer_iter > 0 else None)
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
            # the EU price (relative to base) at which this iteration's supply was
            # produced, so the market can anticipate the supply response
            self.market_module._eu_price_seen = (1.0 + price_signal).reindex(
                self.market_module.commodities).fillna(1.0)
            # FEED DEMAND FOLLOWS HERDS: EU feed use of each feed cereal from
            # this iteration's herds x the feed table, relative to base.
            self._set_feed_demand(supply_results)
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
            # Farmers respond to the EU price, not the world price. The EU price
            # is the world price times the fixed tariff wedge times the Armington
            # premium, so relative to base it moves by (world/world_base) x
            # premium. With no premium this is exactly the old world-price signal.
            _prem = getattr(self.market_module, "eu_premium", None)
            _prem = (_prem.reindex(new_prices.index).fillna(1.0)
                     if _prem is not None else 1.0)
            _target = (new_prices / base_prices.clip(lower=1.0)) * _prem - 1.0
            # Damped update. With the Armington premium the EU price responds
            # to EU supply, so supply and price feed back on each other; taking
            # the new signal in full made the outer loop oscillate (a cobweb:
            # the maximum price change grew 0.19 -> 0.33 between iterations).
            # Relaxation changes the path to the equilibrium, not the
            # equilibrium itself, so a converged result is unaffected.
            price_signal = price_signal + self.PRICE_SIGNAL_RELAXATION * (
                _target.reindex(price_signal.index).fillna(0.0) - price_signal)

            # Aggregate quantities for convergence
            agg_qty = eu_supply_market.sum() if eu_supply_market is not None \
                      else pd.Series(dtype=float)

            tracker.record(outer_iter, new_prices, agg_qty)
            if self.verbose:
                try:
                    _dv = (new_prices / base_prices.clip(lower=1.0) - 1.0)
                    _pr = getattr(self.market_module, 'eu_premium', None)
                    _prev = getattr(self, '_trace_prev_prem', None)
                    _top = ''
                    if _pr is not None and _prev is not None:
                        _d = (_pr - _prev.reindex(_pr.index).fillna(1.0)).abs().sort_values(ascending=False).head(3)
                        _top = ' | premium swing: ' + ', '.join(f'{k} {float(_pr[k]):.3f} ({v:+.3f})' for k, v in _d.items())
                    self._trace_prev_prem = _pr.copy() if _pr is not None else None
                    _lu = float(getattr(self.supply_module, 'max_land_update', 0.0) or 0.0)
                    print(f'  [outer {outer_iter + 1}] world max {_dv.abs().idxmax()} {float(_dv.abs().max()):.4f} | land update {_lu:.5f}{_top}', flush=True)
                except Exception:
                    pass

            # Damped steps are small by design, so small successive price
            # changes alone could signal a false convergence. Also require the
            # signal to have reached the target it is being relaxed toward.
            _gap = float((_target.reindex(price_signal.index).fillna(0.0)
                          - price_signal).abs().max())
            # land supply converges with prices: do not stop while it moves
            _land = float(getattr(self.supply_module, "max_land_update", 0.0) or 0.0)
            if outer_iter > 0 and tracker.check_convergence() and _gap < 0.005 and _land < 1e-3:
                outer_converged = True
                if self.verbose:
                    print(f"  ✓ Outer loop converged at iteration {outer_iter + 1}")
                break
        else:
            # A non-converged run is NOT a quiet event. Suppressing the price
            # feedback changes scenario results materially -- running a
            # Farm-to-Fork comparison at max_outer_iter=1 overstated the cereal
            # decline by 4 percentage points (-22.6% against -18.5% converged),
            # and that unconverged figure was published before anyone noticed.
            # The old code printed this only when verbose=True, so a
            # verbose=False comparison failed silently. It now always warns and
            # is recorded in metadata as outer_converged.
            outer_converged = False
            warnings.warn(
                f"Outer supply-market loop did NOT converge in {max_outer_iter} "
                "iterations. Price feedback is incomplete, so scenario results "
                "will overstate quantity responses. Do not compare an "
                "unconverged run against external references -- raise "
                "max_outer_iter or check metadata['outer_converged'].",
                RuntimeWarning, stacklevel=2)
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
                print("  [Abatement] CAPRI mitigation portfolio (primary) + EcAMPA measures (literature comparison)...")
            try:
                abatement_result = self._run_abatement(supply_results, env_df)
            except Exception as e:
                if self.verbose:
                    print(f"  [Abatement] skipped: {e}")

        # --- Policy summary ---
        policy_summary = self.policy_module.summarise_policy()

        t_elapsed = time.time() - t_start

        if _is_base and market_eq is not None:
            try:
                self._eu_base_cache[_key] = (
                    market_eq.production.loc["EU27"].copy(),
                    market_eq.consumption.loc["EU27"].copy(),
                    self.market_module._demand_cal_frozen.copy(),
                    self.market_module.base_production.loc["EU27"].copy(),
                    self.market_module.base_consumption.loc["EU27"].copy())
            except Exception:
                pass

        results = {
            "scenario": pol_scenario.name,
            "supply": supply_results,
            "market": market_eq,
            "environmental": env_df,
            "feed": feed_df,
            "biofuel": biofuel_result,
            "abatement": abatement_result,
            # CAPRI's own mitigation portfolio: full potential and, when a
            # carbon price is set, abatement at that price (tonnes CO2e)
            "abatement_capri": getattr(self, "_capri_abatement_result", None),
            "policy_summary": policy_summary,
            "convergence": tracker.summary(),
            "metadata": {
                "n_regions": len(supply_results) if supply_results else 0,
                "n_outer_iterations": outer_iter + 1,
                "market_converged": market_eq.converged if market_eq else False,
                # False means the supply-market price feedback is incomplete;
                # such a run must not be compared against external references.
                "outer_converged": outer_converged,
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
        self._abatement_inputs = []
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
            self._abatement_inputs.append(
                (region, ghg, self.env_module.enteric_ch4_by_animal(acts)))
            for k, v in ghg.items():
                sources[k] = sources.get(k, 0.0) + v
            for a, v in self.env_module.enteric_ch4_by_animal(acts).items():
                enteric[a] = enteric.get(a, 0.0) + v
        # CAPRI's own mitigation portfolio, per member state: reductions at
        # full technical potential and, if a carbon price is set, at that price.
        self._capri_abatement_result = None
        ca = getattr(self, "capri_abatement", None)
        if ca is not None:
            full, at_price = {}, {}
            price = getattr(self, "_run_carbon_price", None)
            herd = sum(float(v) for v in enteric.values()) or 1.0
            e_unit = {"CH4ENT": 1.7, "CH4MAN": sources.get("CH4_MAN", 0.0) / max(herd, 1.0),
                      "N2OSYN": 0.001}
            for region, ghg, ent in self._abatement_inputs:
                for k, v in ca.abate(ghg, region[:2], None, ent).items():
                    full[k] = full.get(k, 0.0) + v
                if price:
                    for k, v in ca.abate(ghg, region[:2], price, ent).items():
                        at_price[k] = at_price.get(k, 0.0) + v
            self._capri_abatement_result = {
                "emissions_by_source": dict(sources),
                "full_potential": full, "carbon_price": price,
                "at_carbon_price": at_price if price else None}
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

    #: feed cereals whose EU demand is split into a feed part that follows
    #: herd sizes and a remainder that keeps its own-price response
    FEED_DEMAND_COMMODITIES = ("SWHE", "BARL", "CORN", "OCER")

    def _feed_shares(self) -> dict:
        """Each feed cereal's feed share of EU domestic use, CAPRI 2030 balance
        (FEDM / (HCOM + FEDM + INDM + BIOF + LOSM)); other cereals include rye
        and oats, which have no market of their own here."""
        cached = getattr(self, "_feed_shares_cache", None)
        if cached is not None:
            return cached
        out = {}
        try:
            import json
            from pathlib import Path
            f = Path(getattr(self, "data_dir", None) or Path(__file__).resolve().parents[1] / "capri_data") \
                / "validation" / "capri_eu27_market_balance_2030_ref.json"
            if not f.exists():
                f = Path(__file__).resolve().parents[1] / "capri_data" / "validation" / "capri_eu27_market_balance_2030_ref.json"
            p = json.load(open(f))["products"]
            groups = {"SWHE": ("SWHE",), "BARL": ("BARL",), "CORN": ("MAIZ",), "OCER": ("OCER", "RYEM", "OATS")}
            for c, src in groups.items():
                fed = sum(float(p[x].get("FEDM", 0.0)) for x in src if x in p)
                use = sum(float(p[x].get(k, 0.0)) for x in src if x in p
                          for k in ("HCOM", "FEDM", "INDM", "BIOF", "LOSM"))
                if use > 0 and fed > 0:
                    out[c] = min(0.9, fed / use)
        except Exception:
            out = {}
        self._feed_shares_cache = out
        return out

    def _update_rations(self, price_signal) -> None:
        """Solve every EU region-animal ration at the current feed prices and hand
        the result to the supply module (feed costs, fodder balance) and to the
        market's feed demand. Cereals: CAPRI-weighted cereal price index; protein:
        cake price index; fodder and feeds without a market at base value
        (REGISTERED - fodder priced at its base value, not yet the balance dual)."""
        from capri_mod.feed.ration import RationModel
        from capri_mod.supply.supply_module import RegionalSupplyModel as _R
        rm = getattr(self, "_ration_model", None)
        if rm is None:
            rm = RationModel(self.data_dir if hasattr(self, "data_dir") else None)
            self._ration_model = rm
        sig = price_signal if price_signal is not None else {}
        g = (lambda c: float(sig.get(c, 0.0)) if hasattr(sig, "get") else 0.0)
        mix = _R.FEED_CEREAL_MIX; wsum = sum(mix.values())
        ci = 1.0 + sum(w * g(c) for c, w in mix.items()) / wsum
        cw, _p = _R._cake_index(); cs = sum(cw.values()) or 1.0
        pi = 1.0 + sum(w * g(c) for c, w in cw.items()) / cs
        state = {}
        # DAMPED like the price signal: each ration moves halfway from its
        # previous value toward the new optimum. Undamped rations reacted at once
        # to damped prices and the outer loop oscillated (Farm-to-Fork with the
        # ration on exceeded the 25-iteration cap). A convex combination of
        # feasible rations is feasible (linear, price-independent constraints),
        # and the fixed point is unchanged.
        prev = getattr(self, "_ration_prev", None)
        if price_signal is None or prev is None:
            prev = {}
        alpha = getattr(self, "ration_damping", 0.5)
        newprev = {}
        for (reg, act), r in rm.rations.items():
            p = rm.price_vector((reg, act), ci, pi)
            x, ok = r.solve(p)
            if not ok:
                x = r.x0
            xp = prev.get((reg, act))
            if xp is not None:
                x = xp + alpha * (x - xp)
            newprev[(reg, act)] = x
            state.setdefault(reg, {})[act] = {"x": dict(zip(r.feeds, x)),
                                              "dcost": r.cost(x, p) - r.cost(r.x0, r.p0)}
        self.supply_module.ration_state = state
        self._ration_state = state
        self._ration_prev = newprev

    def _cake_feed_shares(self) -> dict:
        """Feed share of EU domestic use per cake, CAPRI 2017 base (FAO_agg BAS)."""
        cached = getattr(self, "_cake_shares_cache", None)
        if cached is not None:
            return cached
        out = {}
        try:
            import json
            from pathlib import Path
            f = Path(__file__).resolve().parents[1] / "capri_data" / "2017" / "market" / "capri_oilseed_products_baseline.json"
            b = json.load(open(f))["balances"]
            for c in ("RAPC", "SUNC", "SOYC"):
                r = b.get(f"EU27|{c}", {})
                if r.get("consumption", 0) > 0:
                    out[c] = min(1.0, float(r.get("feed", 0.0)) / float(r["consumption"]))
        except Exception:
            out = {}
        self._cake_shares_cache = out
        return out

    def _set_feed_demand(self, supply_results) -> None:
        """Pass EU feed use (current and base) to the market.

        The market module never referred to animals: feed demand was a fixed
        part of each cereal's demand curve, so when herds shrank the market did
        not see the feed they no longer ate (Farm-to-Fork: pigs -15%, cereal
        prices +13% against CAPRI's +8%). Feed use = sum over regions and
        animals of heads x feed requirement (t/head, feed_requirements.csv);
        base use from each regional model's own base levels, so the base year
        cannot move. Broilers are counted per census place (4.35 birds a year).
        """
        mm = self.market_module
        try:
            fr = self.data.get("feed_requirements")
            if fr is None:
                fr = self.data.get("feed_req")
            if fr is None or not len(fr) or not supply_results:
                mm._feed_use = None
                return
            from capri_mod.data.definitions import ANIMALS
            mult = {"BROI": getattr(type(self.supply_module), "BROILER_BIRDS_PER_PLACE", 1.0)}
            cur = {c: 0.0 for c in self.FEED_DEMAND_COMMODITIES}
            prot = [0.0, 0.0]                       # protein-rich feed: now, base
            base = {c: 0.0 for c in self.FEED_DEMAND_COMMODITIES}
            for region, res in supply_results.items():
                mo = getattr(self.supply_module, "_models", {}).get(region)
                b0 = mo._base_levels() if mo is not None else None
                fc = getattr(mo.data, "livestock_feed_coef", None) if mo is not None else None
                for a in ANIMALS:
                    x = float(res.activities.get(a, 0.0))
                    x0 = float(b0.get(a, 0.0)) if b0 is not None else x
                    q = float(fc.get(f"{a}_cereals", float("nan"))) if fc is not None else float("nan")
                    qp = float(fc.get(f"{a}_protein", float("nan"))) if fc is not None else float("nan")
                    # with the EU ration wired in: current cereals and protein
                    # feed per head from the ration; base from the base ration
                    _rr = ((getattr(self, "_ration_state", None) or {}).get(region) or {}).get(a)
                    _r0 = getattr(self, "_ration_model", None)
                    if _rr and _r0 is not None and (region, a) in _r0.rations:
                        _rb = _r0.rations[(region, a)]
                        xb = dict(zip(_rb.feeds, _rb.x0))
                        if "FCER" in xb:
                            cur["OCER"] += x * _rr["x"].get("FCER", 0.0) / 1000.0
                            base["OCER"] += x0 * xb["FCER"] / 1000.0
                        if "FPRO" in xb:
                            prot[0] += x * _rr["x"].get("FPRO", 0.0) / 1000.0
                            prot[1] += x0 * xb["FPRO"] / 1000.0
                        continue
                    if qp == qp:                    # protein-rich feed, t per head
                        prot[0] += x * qp
                        prot[1] += x0 * qp
                    if q == q:                      # CAPRI total / our herd, t per head
                        cur["OCER"] += x * q
                        base["OCER"] += x0 * q
                        continue
                    if a not in fr.index:
                        continue
                    k = mult.get(a, 1.0)
                    for c in self.FEED_DEMAND_COMMODITIES:
                        if c in fr.columns:
                            q = float(fr.at[a, c]) * k
                            cur[c] += x * q
                            base[c] += x0 * q
            # The feed table files CAPRI's per-animal CEREAL AGGREGATE mostly
            # under OCER (183.5 of 189 Mt), so per-commodity sums would put the
            # whole herd effect on the small other-cereals market. Use ONE herd-
            # driven index - total cereal feed now vs base - and each cereal's
            # feed share of domestic use from CAPRI's 2030 market balance.
            F, F0 = sum(cur.values()), sum(base.values())
            shares = self._feed_shares()
            mm._feed_use = ({c: (F / F0, sh) for c, sh in shares.items()}
                            if F0 > 0 and shares else None)
            # CAKES follow protein-rich feed (crushing Stage 3): each cake's EU
            # feed share of domestic use from CAPRI's 2017 base (FAO_agg BAS).
            if prot[1] > 0:
                cs = self._cake_feed_shares()
                if cs:
                    mm._feed_use = dict(mm._feed_use or {})
                    for c, sh in cs.items():
                        mm._feed_use[c] = (prot[0] / prot[1], sh)
        except Exception:
            mm._feed_use = None

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
            # paddy rice is a market commodity; without this entry the model's
            # own rice production never reached the rice market
            "PARI": "PARI",
        }
        # LIVESTOCK (milk is handled by the dairy block below). The meat markets
        # meat, milk and egg supply never moved with the herds: under
        # Farm-to-Fork pig supply fell ~10% while the pork price changed by
        # exactly 0.0% (CAPRI: +43%). Each product is the sum of the
        # activities producing it, from their marketed gross output.
        # The model's own animal codes (definitions.ANIMALS): BCOW suckler cows,
        # HFRS heifers, PIGF a second pig activity, SHGP sheep and goats. An
        # earlier version of this map used HEIF/SCOW/SOWS/SHEP/GOAT, which do not
        # exist here, so beef came from bulls and calves only, pork from one pig
        # activity of two, and sheep and goat meat got nothing.
        livestock_maps = {
            "BEEF": ("BULL", "BCOW", "HFRS", "CALV"),
            "PORK": ("PIGS", "PIGF"),
            "POUL": ("BROI",),
            "EGGS": ("LAYS",),
            "SHGM": ("SHGP",),
        }
        # (Oil and cake supply now comes from crushing inside the market.)
        for mcomm, acts in livestock_maps.items():
            present = [a for a in acts if a in supply_agg.columns]
            if present and mcomm in market_supply.columns:
                market_supply[mcomm] = supply_agg[present].sum(axis=1)

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
        # The market commodities RAPE and SUNF are the SEEDS: they carry seed
        # world prices, and EU demand for them is calibrated to FAO seed use,
        # crushing included (CAPRI's 2030 reference: rapeseed production 22.4
        # Mt, of which 27.6 Mt processed with imports). The seed quantity used to
        # be multiplied by the OIL extraction yield (0.42) and passed to the seed
        # market, so the market saw EU rapeseed at 7.4 Mt and sunflower at 4.1
        # instead of ~19 and ~10. Percentage changes survived the constant
        # factor, which is why it went unnoticed; the EU's weight in world
        # oilseed markets did not.
        if "RAPE" in supply_agg.columns:
            market_supply["RAPE"] = supply_agg["RAPE"]
        if "SUNF" in supply_agg.columns:
            market_supply["SUNF"] = supply_agg["SUNF"]
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
        # (An older meat-and-eggs block stood here. Its codes were right, but it
        # scaled each product by an arbitrary "market slot" factor (pork x
        # 0.00004116),
        # so near-zero values reached the market, which then kept its own fixed
        # base: meat prices never moved with the herds in any scenario. It also
        # silently overwrote the livestock mapping above. Removed; dairy, which
        # maps correctly, is kept as it was.)

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
