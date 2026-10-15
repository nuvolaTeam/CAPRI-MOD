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

    # Load your own data directory (CAPRI data, capri_data)
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
from capri_mod.params import param, param_table


#: Nitrates Directive ceiling on organic N application (kg N per ha of UAA)


class CAPRIModel:
    """
    CAPRI-mod: Common Agricultural Policy Regionalised Impact Model.

    Partial equilibrium model for ex-ante policy impact assessment.

    Parameters
    ----------
    data_dir : path to directory containing CSV data files
               (from Eurostat, FADN, FAOSTAT, COMTRADE).
               Required: the model runs on CAPRI data only.
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
    #: CAPRI's manure trade (GUI "New Manure Trade Module", manureTradeNew; docs/MANURE_MARKET.md). ON by default
    #: as in CAPRI star 3.0's GUI (capri_gui_definition.xml: New_Manure_Trade_fromGUI = true). A scenario sets its
    #: own (PolicyScenario.manure_trade): JRC121368's Farm-to-Fork kept all manure in its region (p. 24), so
    #: farm_to_fork_scenario() turns it off; the setting holds for the scenario and its baseline.
    use_manure_market = True
    #: CAPRI's baseline calibration in projected years (Sprint 9p): largest remaining drift of a regional activity
    #: from its projected level, relative, for the baseline to count as converged
    BASE_CAL_TOL = 0.002
    calibrate_baseline = True
    #: CAPRI's endogenous biofuel markets (GUI "Endogenous bio-fuel markets", BIOF_M; docs/BIOFUEL_MARKET.md). ON
    #: by default as in CAPRI star 3.0's GUI (capri_gui_definition.xml BIOF_M = true). A scenario may set its own
    #: (PolicyScenario.biofuel_markets); the setting holds for the scenario and its baseline.
    biofuel_markets = True
    #: Convergence tolerance of the manure market: each country pool must clear
    #: to within this share of its manure supply (realised net exports vs net
    #: shipments) before the outer loop may stop. 0.03 = 3%: in a six-country
    #: Farm-to-Fork test results were already stable at that level (pigs and
    #: cattle unchanged to 0.1 point), while 1% needed about twice the
    #: iterations. Only used when use_manure_market is on.
    manure_pool_tolerance = 0.03
    #: nitrogen-surplus target per hectare of CURRENT farmland, as CAPRI
    #: (supply_model.gms e_SURTOTHa); False keeps base farmland. ON by default with land_no_slack
    surplus_per_current_ha = True
    #: outer-iteration cap used when the manure market is on. The pool loop
    #: contracts by a near-constant ~3.5% per iteration (regional schedules
    #: shift with the prices); on the full EU the worst pool reached 5.1% after
    #: 40 iterations, so 3% needs about 55.
    manure_max_outer_iter = 60
    #: CAPRI's ammonia technologies adopted inside the supply model under the
    #: nitrogen shadow price (docs/MITIGATION_IN_SUPPLY.md). ON by default: CAPRI's
    #: Farm-to-Fork run had them active (JRC121368 Table 17); with them, 2030
    #: Farm-to-Fork ammonia falls 34.4% (CAPRI 33%) and pigs 14.4% (CAPRI 14.5%)
    use_manure_techs = True
    #: CAPRI's young-animal markets (arm/market_model.gms yaniMarket_): calves, young cattle
    #: and replacement cows traded EU-wide at prices that keep the EU net balance of each at
    #: its baseline level (CAPRI fixes young-animal net trade); docs/YOUNG_ANIMALS.md
    use_young_animal_market = True
    #: CAPRI's land balances without slack (LandBalNoSlak_): no idle farmland. ON by default since
    #: October 2026 (with surplus_per_current_ha, "CAPRI's land rules"), once the grassland row
    #: became CAPRI's grassland balance: Farm-to-Fork 2030 gap to JRC121368 5.81 -> 4.85, EU
    #: farmland -1.9% -> +1.8% (JRC121368 Figure 5: +3%); docs/COUPLING_SPRINTS.md, Sprint 8
    land_no_slack = True
    #: nitrate as a feed-ration ingredient (CAPRI envind/line_nitr.gms): replaces
    #: protein, cuts enteric CH4 (10 x share of DM), adds N excretion; off until validated
    use_nitrate = False
    #: quadratic-program solver for the regional supply models and feed rations:
    #: "clarabel" (interior point, leading; the built-in chain stays as fallback when
    #: Clarabel is missing or does not solve) or "builtin" (active set + exact
    #: least-distance solver; kept for comparison). tools/compare_qp_solvers.py, full
    #: EU baseline + Farm-to-Fork, October 2026: world prices agree to 5e-5, N surplus,
    #: NH3 and enteric CH4 to 2e-5, 11,160 activity levels to a median 5e-6 (largest
    #: 3.4% on a 0.9 kha activity, within the outer-loop tolerance); same run time.
    #: The regional models with feeding inside are conic and always solved by Clarabel.
    qp_solver = "clarabel"
    #: price home-grown fodder in the rations at its fodder-balance shadow price
    #: (CAPRI) instead of its base value. OFF: the first 2030 Farm-to-Fork run with
    #: it did not converge (feedback ration <-> fodder dual, needs damping)
    fodder_at_shadow_price = False
    #: feeding inside the regional supply models, as CAPRI (docs/FEED_IN_SUPPLY.md)
    use_feed_in_supply = True
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

    def _apply_endotech(self, settings: Dict[str, float]) -> None:
        """Set the run's endogenous-technology settings: cattle genomics re-scaled (tools/
        build_genetics_effects.py writes it per unit of ghgTechMYld / ghgTechFEff)."""
        from capri_mod.policy.endotech import key as _et_key, scale_genetics
        k = _et_key(settings)
        if getattr(self, "_endotech_key", None) == k:
            return
        tab = scale_genetics(self.data.get("genetics_effects_unit"), settings)
        self.data["genetics_effects"] = tab
        self.supply_module.set_genetics_effects(tab, k)
        self.endotech = dict(settings)
        self._endotech_key = k

    def _ghg_coefficients(self, key) -> dict:
        """{region: coefficients} of CAPRI's emission tax at the baseline solution of this run's settings
        (capri_mod/supply/ghg_tax.ghg_coefficients), cached per baseline."""
        from capri_mod.supply.ghg_tax import ghg_coefficients
        cache = getattr(self, "_ghg_coef_cache", None)
        if cache is None:
            cache = self._ghg_coef_cache = {}
        if key in cache:
            return cache[key]
        base = (getattr(self, "_base_supply_cache", None) or {}).get(key) or {}
        rats = getattr(self.supply_module, "feed_rations", None) or {}
        out = {}
        for region, res in base.items():
            if region.startswith("NO"):                      # CAPRI: EU regions only (msNoEU)
                continue
            try:
                out[region] = ghg_coefficients(self.env_module, region, res, rats.get(region))
            except Exception as exc:                         # pragma: no cover
                import warnings as _w
                _w.warn(f"emission tax coefficients failed for {region}: {exc!r}")
        cache[key] = out
        return out

    # ------------------------------------------------------------------
    # MAIN RUN METHOD
    # ------------------------------------------------------------------

    #: Relaxation on the supply price signal between outer iterations.
    PRICE_SIGNAL_RELAXATION = param("PRICE_SIGNAL_RELAXATION")

    def run(
        self,
        scenario: str = "BASELINE",
        world_price_shock: Optional[Dict[str, float]] = None,
        custom_scenario: Optional[PolicyScenario] = None,
        max_outer_iter: int = 25,
        outer_tolerance: float = 0.005,
        market_max_iter: int = 150,
        run_environmental: bool = True,
        run_biofuel: bool = False,
        carbon_price: float = 0.0,
        biofuel_output_scale: Optional[Dict[str, float]] = None,
        regions: Optional[List[str]] = None,
        endotech: Optional[Dict[str, float]] = None,
        manure_trade: Optional[bool] = None,
        biofuel_markets: Optional[bool] = None,
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
        run_biofuel       : report the EU biofuel block (feedstock demand is always in the market)
        biofuel_output_scale : EU biofuel output relative to CAPRI's 2030 reference, per biofuel
                            ({"BIOE": x, "BIOD": y}); CAPRI fixes it in scenario runs without
                            endogenous biofuel markets, so a mandate scenario sets it
        regions           : region subset (default: all)
        endotech          : CAPRI endogenous-technology settings (capri_mod/policy/endotech.py), on top of
                            the scenario's own; they hold for this run and for the baseline it is compared
                            with, as in CAPRI's scenario configuration
        manure_trade      : CAPRI's manure trade between regions (default: the model's, on as star 3.0's GUI)
        biofuel_markets   : CAPRI's endogenous biofuel markets, BIOF_M (default: the model's, on as star 3.0's
                            GUI); both are scenario settings that hold for the run and its baseline

        Returns
        -------
        dict with keys: supply, market, environmental, policy_summary, metadata
        """
        # Get scenario
        if custom_scenario is not None:
            pol_scenario = custom_scenario
        else:
            pol_scenario = get_scenario(scenario)
        # CAPRI's manure trade: the scenario's setting (or the call's), else the model's default; it holds for
        # this run and the baseline it is compared with, and the model's default is restored afterwards
        _mt_default = bool(getattr(self, "use_manure_market", True))
        _mt = manure_trade if manure_trade is not None else getattr(pol_scenario, "manure_trade", None)
        _mt = _mt_default if _mt is None else bool(_mt)
        self.use_manure_market = _mt
        # CAPRI's endogenous biofuel markets (BIOF_M): the same rule
        _bm_default = bool(getattr(self, "biofuel_markets", True))
        _bm = biofuel_markets if biofuel_markets is not None else getattr(pol_scenario, "biofuel_markets", None)
        _bm = _bm_default if _bm is None else bool(_bm)
        self.market_module.biofuel_markets = _bm
        # the base manure trade between regions (CAPRI's 2030 reference) counts only where the run trades manure
        self.env_module.set_manure_trade(bool(_mt))
        self.supply_module.manure_trade_on = bool(_mt)
        if getattr(self.supply_module, "_env_for_surplus", None) is not None:
            self.supply_module._env_for_surplus.set_manure_trade(bool(_mt))
        try:
            return self._run_scenario(pol_scenario, scenario, world_price_shock, custom_scenario, max_outer_iter,
                                      outer_tolerance, market_max_iter, run_environmental, run_biofuel,
                                      carbon_price, biofuel_output_scale, regions, endotech, _mt, _bm)
        finally:
            self.use_manure_market = _mt_default
            self.market_module.biofuel_markets = _bm_default

    def _run_scenario(self, pol_scenario, scenario, world_price_shock, custom_scenario, max_outer_iter,
                      outer_tolerance, market_max_iter, run_environmental, run_biofuel,
                      carbon_price, biofuel_output_scale, regions, endotech, _mt, _bm=True) -> Dict:
        # the manure pools need more outer iterations than the default allows; an explicitly short run
        # (a test, a diagnostic) keeps its own limit
        if getattr(self, "use_manure_market", False) and int(max_outer_iter) >= 25:
            max_outer_iter = max(int(max_outer_iter), int(getattr(self, "manure_max_outer_iter", 60)))
        t_start = time.time()

        if self.verbose:
            print(f"Running scenario: {pol_scenario.name}")
            print(f"  {pol_scenario.description}")

        self.market_module.biofuel_output_scale = {"BIOE": 1.0, "BIOD": 1.0, **(biofuel_output_scale or {})}
        # CAPRI's biofuel mandate scenario (scen/bio_fuels/change_biof_mandate.gms): a policy shock of the
        # scenario, not of its baseline
        _bmand = getattr(pol_scenario, "biofuel_mandate", None)
        self.market_module.biofuel_mandate = float(_bmand) if _bmand is not None else 1.0

        # CAPRI's endogenous-technology settings: scenario configuration, the same in the baseline
        from capri_mod.policy.endotech import effective as _et_eff, key as _et_key
        _endotech = _et_eff(getattr(pol_scenario, "endotech", None), endotech)
        self._apply_endotech(_endotech)

        # Apply policy scenario
        self.policy_module.apply_scenario(pol_scenario)

        # EU Armington premium needs the EU's BASE supply and demand at this
        # model's own levels, for the same region set. A baseline run records
        # them at convergence; a scenario run uses them, running a baseline
        # first if none is cached. In a baseline run the premium stays off,
        # so the baseline is exactly what it was.
        _key = (tuple(sorted(regions or list(self.data["areas"].index))), _et_key(_endotech), bool(_mt), bool(_bm))
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
                         max_outer_iter=max_outer_iter, endotech=_endotech, manure_trade=bool(_mt),
                         biofuel_markets=bool(_bm))
                self.use_manure_market = bool(_mt)
                self.market_module.biofuel_markets = bool(_bm)
                self.verbose = _saved
                self.policy_module.apply_scenario(pol_scenario)
            self.market_module.set_eu_base(*_cache[_key][:2])
            # reuse the calibration of the baseline for the same region set
            if len(_cache[_key]) > 2:
                _cal, _bp, _bc = _cache[_key][2:5]
                _mm._demand_cal_frozen = _cal.copy()
                _mm.base_production.loc["EU27"] = _bp
                _mm.base_consumption.loc["EU27"] = _bc
                if len(_cache[_key]) > 5 and _cache[_key][5][0] is not None:
                    _bs, _bpa, _bca, _cov, _eau = _cache[_key][5]
                    _mm._bilat = _bs
                    for _sc in (_bs or {}).values():
                        if getattr(_sc, "trq_row", None) is not None and _sc.trq_offset is not None:
                            _sc.trq_offset = _sc.trq_offset * 0.0
                    _mm.base_production = _bpa.copy()
                    _mm.base_consumption = _bca.copy()
                    _mm._crush_q0_override = dict(_cov)
                    _mm._eu_aligned_use = dict(_eau)
                    _mm._crush_cache = None
                    _mm._bilat_local_el = None
                    _mm._bilat_last_r = None

        # CAPRI's emission tax (ghgTax; pol_input/ecampa/carbtax50_endotech_*.gms, supply_model.gms objective): a
        # policy shock of the scenario, EUR per t CO2-eq on the EU regions' emissions; each column's emission per
        # unit at this baseline's solution (capri_mod/supply/ghg_tax.py). carbon_price: the same, given at run time.
        _tax = float(getattr(pol_scenario, "carbon_tax", 0.0) or 0.0) or float(carbon_price or 0.0)
        self.supply_module.ghg_tax = 0.0
        self.supply_module.ghg_coef = None
        if _tax > 0 and not _is_base:
            self.supply_module.ghg_coef = self._ghg_coefficients(_key)
            self.supply_module.ghg_tax = _tax

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

        # ---- Young-animal markets: prices start at base every run; active in a scenario
        # run when the baseline of the same region set has recorded its net balances ----
        self.supply_module.yani_price_ratio = None
        self._yani_imbalance = 0.0
        self._yani_trace = []
        _yani_ref = (getattr(self, "_yani_ref", {}) or {}).get(_key)
        _yani_on = bool(getattr(self, "use_young_animal_market", False)) and not _is_base and bool(_yani_ref)
        if _yani_on:
            self.supply_module.yani_price_ratio = {g: 1.0 for g in _yani_ref}

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
            self.supply_module.jrc_capped_override = getattr(self, "jrc_capped_override", "")
            self.supply_module.__dict__.pop("_jrc_capped_cache", None)
            self.supply_module.grassland_allowance = getattr(self, "grassland_allowance", 0.0)
            if outer_iter == 0:
                from capri_mod.supply.supply_module import RegionalSupplyModel as _RSM
                _on = bool(getattr(self, "use_manure_market", False))
                _RSM.use_fert_allocation = False      # substitution already in the balance
                _RSM.use_manure_pool = _on
                _RSM.surplus_per_current_ha = bool(getattr(self, "surplus_per_current_ha", False))
                _RSM.use_manure_techs = bool(getattr(self, "use_manure_techs", False))
                _RSM.use_feed_in_supply = bool(getattr(self, "use_feed_in_supply", False))
                _RSM.land_no_slack = bool(getattr(self, "land_no_slack", False))
                import capri_mod.supply.qp_solver as _QPS
                _QPS.BACKEND = str(getattr(self, "qp_solver", "clarabel"))
                self.supply_module.manure_pool_price = {}     # fresh pools every run
                self._pool_state = None
                self._pool_accel = None
                self._pool_trace = []
                self._pool_imbalance = 0.0
            if getattr(self, "use_ration", False):
                self._update_rations(price_signal if outer_iter > 0 else None)
            else:
                # CAPRI's feed bulk prices for the feed costs per head (feedBlkPrice_)
                self.supply_module.feed_bulk_ratio = self.feed_bulk_price_ratios(price_signal if outer_iter > 0 else None)
            # CAPRI's raw milk price per member state (dairy block per RMS): the regional models get their member
            # state's milk price signal (relaxed like every price signal, below) as a departure from the EU's
            _ms_sig = getattr(self, "_milk_ms_signal", None) or {}
            self.supply_module.milk_price_dev_ms = (
                {ms: float(v) - float(price_signal.get("MILK", 0.0)) for ms, v in _ms_sig.items()}
                if outer_iter > 0 else {})
            supply_results = self.supply_module.run(
                price_signals=price_signal if outer_iter > 0 else None,
                policy_scenario={
                    "adders": policy_adders.to_dict(),
                    # premium factors by region and activity (a CAPRI premium experiment)
                    "premium_factor_regional": dict(
                        getattr(pol_scenario, "premium_factor_regional", None) or {}),
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
                    "surplus_rule": str(getattr(pol_scenario, "surplus_rule", "star3") or "star3"),
                    "surplus_cut": float(getattr(pol_scenario, "surplus_cut", 0.5) or 0.5),
                    # CAPRI's mineral fertiliser reduction (mineRedu): "20" UAA-wide, "NNcrp" by crop group
                    "mineral_redu": str(getattr(pol_scenario, "mineral_redu", "00") or "00"),
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
            self._last_supply_results = supply_results   # fodder shadow prices for the rations
            # CAPRI's baseline calibration (CAPMOD calibrates its supply models so that the simulation year's baseline
            # reproduces the projected levels): in the baseline of a projected year, the regional models' linear terms
            # are corrected until their solution is the projection's levels (Sprint 9p); the scenario then starts
            # from that calibrated baseline, as CAPRI's do
            self._calib_drift = 0.0
            if (_is_base and bool(getattr(self, "calibrate_baseline", True)) and isinstance(self.data, dict)
                    and self.data.get("market_year") and self.data.get("calibrate_baseline", True)):
                self._calib_drift = self.supply_module.calibrate_to_base(supply_results, reset=(outer_iter == 0))
                self._calib_trace = getattr(self, "_calib_trace", []) if outer_iter else []
                self._calib_trace.append(round(float(self._calib_drift), 5))
            if _yani_on:
                self._update_young_animal_prices(supply_results, _yani_ref)
            if str(scenario).upper() == "BASELINE" and custom_scenario is None:
                # reference fodder shadow prices = this baseline's own (ratio exactly 1 at base)
                self._fodder_dual_base = {_r: {k: float(v) for k, v in (getattr(_x, "shadow_prices", {}) or {}).items()
                                                 if str(k).startswith("fodder_") and not str(k).endswith("_band")}
                                          for _r, _x in supply_results.items()}

            # Aggregate EU supply for market module
            eu_supply_agg = self.supply_module.aggregate_supply(
                supply_results, by_country=True
            )

            # Map to market commodities (simplified bridge); livestock by CAPRI final product
            self._ls_by_country = self._livestock_products_by_country(supply_results)
            eu_supply_market = self._bridge_supply_to_market(eu_supply_agg)

            # --- Step 2: Market module ---
            if self.verbose:
                print("    [Market] Solving spatial equilibrium...")
            # the EU price (relative to base) at which this iteration's supply was
            # produced, so the market can anticipate the supply response
            self.market_module._eu_price_seen = (1.0 + price_signal).reindex(
                self.market_module.commodities).fillna(1.0)
            # premium damping state belongs to one run (CAPRIModel.run resets it on its first iteration)
            if outer_iter == 0:
                self.market_module._prem_prev, self.market_module._prem_w, self.market_module._prem_d = None, None, None
            # FEED DEMAND FOLLOWS HERDS: EU feed use of each feed cereal from
            # this iteration's herds x the feed table, relative to base.
            self._set_feed_demand(supply_results)
            if getattr(self, "use_manure_market", False):
                self._update_manure_pools()
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
            # CAPRI arm/set_prices.gms: the sugar beet price follows the sugar price
            # (UVAG(SUGB) x v_prodPrice(SUGA) / PPRI(SUGA)); beet has no market of its own
            if "SUGR" in _target.index:
                _target["SUGB"] = float(_target["SUGR"])
            # durum wheat is part of CAPRI's wheat market (WHEA)
            if "SWHE" in _target.index:
                _target["DWHE"] = float(_target["SWHE"])
            # Damped update. With the Armington premium the EU price responds
            # to EU supply, so supply and price feed back on each other; taking
            # the new signal in full made the outer loop oscillate (a cobweb:
            # the maximum price change grew 0.19 -> 0.33 between iterations).
            # Relaxation changes the path to the equilibrium, not the
            # equilibrium itself, so a converged result is unaffected.
            # Per-commodity adaptive step: where the gap to the target changes sign between
            # iterations (a cobweb around the fixed point - eggs under Farm-to-Fork, whose
            # supply jumps as hens leave regions at a high nitrogen price), that commodity's
            # step is halved (floor 0.1); otherwise it recovers toward the default. Like the
            # relaxation itself this changes the path, not the equilibrium.
            _g = _target.reindex(price_signal.index).fillna(0.0) - price_signal
            _w = getattr(self, "_relax_w", None)
            _gprev = getattr(self, "_relax_gprev", None)
            if _w is None or outer_iter == 0:
                _w = pd.Series(self.PRICE_SIGNAL_RELAXATION, index=price_signal.index)
            elif _gprev is not None:
                _flip = (_g * _gprev.reindex(_g.index).fillna(0.0)) < 0
                _w = _w.where(~_flip, (_w * 0.5).clip(lower=0.1))
                _w = _w.where(_flip, (_w * 1.25).clip(upper=self.PRICE_SIGNAL_RELAXATION))
            self._relax_w, self._relax_gprev = _w, _g
            price_signal = price_signal + _w * _g
            # member-state raw milk prices (dairy block per RMS): target = the member state's milk price relative to
            # the EU's, applied to the EU target; relaxed with the same adaptive step, per member state
            _dl = getattr(self.market_module, "_dairy_last", None) if self.market_module._dairy_params() else None
            _ms_gap = _ms_small_gap = 0.0
            if _dl and _dl.get("ms_price_ratio") and "MILK" in _target.index:
                _eu = float(_dl["price_ratio"]["MILK"]) or 1.0
                _sig = getattr(self, "_milk_ms_signal", None) or {}
                _mw = getattr(self, "_milk_ms_w", None) or {}
                _mg = getattr(self, "_milk_ms_gprev", None) or {}
                if outer_iter == 0:
                    _sig, _mw, _mg = {}, {}, {}
                for _ms, _v in _dl["ms_price_ratio"].items():
                    _t = (float(_v["MILK"]) / _eu) * (1.0 + float(_target["MILK"])) - 1.0
                    _s0 = _sig.get(_ms, float(price_signal.get("MILK", 0.0)) - float(_w.get("MILK", 0.0)) * float(_g.get("MILK", 0.0)))
                    _gg = _t - _s0
                    _ww = _mw.get(_ms, self.PRICE_SIGNAL_RELAXATION)
                    if _ms in _mg:
                        # floor 0.02 (prices 0.1): a member state's dairies set its milk price alone, and in a small
                        # one under a binding N target (Cyprus) milk price and herd fed back on each other in a
                        # cobweb at the 0.1 floor
                        _ww = max(0.02, _ww * 0.5) if _gg * _mg[_ms] < 0 else min(self.PRICE_SIGNAL_RELAXATION, _ww * 1.25)
                    _sig[_ms] = _s0 + _ww * _gg
                    _mw[_ms], _mg[_ms] = _ww, _gg
                    # convergence on the member states with at least 1% of EU milk: in Cyprus (0.2%) the herd's
                    # response to the milk price is discontinuous under its binding N target (the regional N price
                    # loop), and its milk price circles within a band without settling; it is reported, not held
                    _sh = float((self.market_module._dairy_params().get("ms", {}).get(_ms) or {}).get("Q0", [0])[
                        (self.market_module._dairy_params().get("ms", {}).get(_ms) or {}).get("iM", 0)]) if _ms in \
                        self.market_module._dairy_params().get("ms", {}) else 0.0
                    _tot = float(self.market_module._dairy_params()["Q0"][self.market_module._dairy_params()["iM"]])
                    if abs(_gg) > _ms_gap and _sh >= 0.01 * _tot:
                        self._milk_ms_worst = (_ms, _s0, _t, _ww, float(_v["milk_delivered"]))
                    if _sh >= 0.01 * _tot:
                        _ms_gap = max(_ms_gap, abs(_gg))
                    else:
                        _ms_small_gap = max(_ms_small_gap, abs(_gg))
                self._milk_ms_signal, self._milk_ms_w, self._milk_ms_gprev = _sig, _mw, _mg
            self._milk_ms_small_gap = _ms_small_gap

            # Aggregate quantities for convergence
            agg_qty = eu_supply_market.sum() if eu_supply_market is not None \
                      else pd.Series(dtype=float)

            tracker.record(outer_iter, new_prices, agg_qty)
            if self.verbose or getattr(self, "trace_outer", False):
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
                    _yv = float(getattr(self, '_yani_imbalance', 0.0) or 0.0)
                    _gp = (_target.reindex(price_signal.index).fillna(0.0) - price_signal).abs()
                    _lr = getattr(self.supply_module, 'max_land_region', None) if _lu > 1e-3 else None
                    print(f'  [outer {outer_iter + 1}] world max {_dv.abs().idxmax()} {float(_dv.abs().max()):.4f} | land update {_lu:.5f}'
                          f'{" (%s, %s)" % _lr if _lr else ""} | milk MS gap {_ms_gap:.4f}'
                          f'{" %s s %.3f t %.3f w %.2f q %.3f" % getattr(self, "_milk_ms_worst") if _ms_gap > 0.005 and getattr(self, "_milk_ms_worst", None) else ""}'
                          f' | gap {_gp.idxmax()} {float(_gp.max()):.4f} | yani {_yv:.4f}'
                          f'{" | pool %.4f %s eu %.4f" % (float(getattr(self, "_pool_imbalance", 0.0) or 0.0), getattr(self, "_pool_worst_key", "") + ("" if str(getattr(self, "_pool_solver_status", "Solved")).endswith("Solved") else " [" + str(getattr(self, "_pool_solver_status", "")) + "]"), float(getattr(self, "_pool_eu_unaccounted", 0.0) or 0.0)) if getattr(self, "use_manure_market", False) else ""}{" | base cal %.4f" % float(getattr(self, "_calib_drift", 0.0) or 0.0) if getattr(self, "_calib_drift", 0.0) else ""}{_top}', flush=True)
                except Exception:
                    pass

            # Damped steps are small by design, so small successive price
            # changes alone could signal a false convergence. Also require the
            # signal to have reached the target it is being relaxed toward.
            _gap = float((_target.reindex(price_signal.index).fillna(0.0)
                          - price_signal).abs().max())
            _gap = max(_gap, _ms_gap)
            # land supply converges with prices: do not stop while it moves
            _land = float(getattr(self.supply_module, "max_land_update", 0.0) or 0.0)
            _pool = float(getattr(self, "_pool_imbalance", 0.0) or 0.0)
            _pool_tol = float(getattr(self, "manure_pool_tolerance", 0.03))
            _yani = float(getattr(self, "_yani_imbalance", 0.0) or 0.0)
            _cal = float(getattr(self, "_calib_drift", 0.0) or 0.0)
            if (outer_iter > 0 and tracker.check_convergence() and _gap < 0.005 and _land < 1e-3
                    and _pool < _pool_tol and _yani < self.YANI_TOL and _cal < self.BASE_CAL_TOL):
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

        # --- Step 4: Feed ---
        # Feeding is chosen inside the regional supply models (CAPRI's REQSE_/REQSN_, feed bulks priced by the
        # market): the run reports each region's feed use per animal and bulk (t). The former post-solve feed
        # module (requirement functions and a feed balance after the solve) is retired (Sprint 9i).
        feed_df = ({r: dict(getattr(res, "feed_t", None) or {}) for r, res in supply_results.items()}
                   if supply_results else None)

        # --- Step 5: Biofuel block (inside the market since crushing stage 4) ---
        biofuel_result = None
        if run_biofuel and market_eq is not None:
            from capri_mod.biofuel import from_market
            biofuel_result = from_market(getattr(market_eq, "biofuel", None),
                                         self.market_module.biofuel_output_scale)

        # --- Step 6: Abatement ---
        # CAPRI's mitigation options are inside the supply models (ammonia, fertiliser, breeding, low-N feed,
        # supplements, cover crops, histosols) and an emission tax acts there too (ghgTax); the run's emissions
        # are the environmental accounts. The former post-solve abatement reports (EcAMPA measures at full
        # uptake, CAPRI's mitigation portfolio applied after the solve, a net-revenue MACC) are retired (Sprint 9i).
        abatement_result = ({"carbon_tax": float(getattr(self.supply_module, "ghg_tax", 0.0) or 0.0)}
                            if float(getattr(self.supply_module, "ghg_tax", 0.0) or 0.0) > 0 else None)

        # --- Policy summary ---
        policy_summary = self.policy_module.summarise_policy()

        t_elapsed = time.time() - t_start

        if _is_base and supply_results:
            # young-animal net balances of this baseline: the scenario keeps them (CAPRI)
            self._yani_ref = getattr(self, "_yani_ref", {}) or {}
            self._yani_ref[_key] = self._young_animal_balance(supply_results)[0]
            # the baseline's solution, for the emission tax's coefficients (CAPRI's emissions at the reference)
            self._base_supply_cache = getattr(self, "_base_supply_cache", {}) or {}
            self._base_supply_cache[_key] = dict(supply_results)
            (getattr(self, "_ghg_coef_cache", None) or {}).pop(_key, None)
        if _is_base and market_eq is not None:
            try:
                self._eu_base_cache[_key] = (
                    market_eq.production.loc["EU27"].copy(),
                    market_eq.consumption.loc["EU27"].copy(),
                    self.market_module._demand_cal_frozen.copy(),
                    self.market_module.base_production.loc["EU27"].copy(),
                    self.market_module.base_consumption.loc["EU27"].copy(),
                    # bilateral market: calibrated systems and full base tables of this baseline
                    (getattr(self.market_module, "_bilat", None),
                     self.market_module.base_production.copy(), self.market_module.base_consumption.copy(),
                     dict(getattr(self.market_module, "_crush_q0_override", None) or {}),
                     dict(getattr(self.market_module, "_eu_aligned_use", None) or {})))
            except Exception:
                pass

        results = {
            "scenario": pol_scenario.name,
            "supply": supply_results,
            "market": market_eq,
            "environmental": env_df,
            "feed": feed_df,
            "biofuel": biofuel_result,
            # CAPRI's inner fertiliser distribution model: N to each crop group per region (kg N/ha by source)
            "fert_dist": (getattr(self.env_module, "last_fert_dist", None) if env_df is not None else None),
            "abatement": abatement_result,
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
                "young_animal_prices": dict(self.supply_module.yani_price_ratio or {}),
                "young_animal_imbalance": float(getattr(self, "_yani_imbalance", 0.0) or 0.0),
                # member states below 1% of EU milk whose milk price has not settled (gap of the price signal)
                "milk_small_ms_gap": float(getattr(self, "_milk_ms_small_gap", 0.0) or 0.0),
            },
        }

        if self.verbose:
            reporter = ResultsReporter(results)
            reporter.print_summary()
            print(f"  Run completed in {t_elapsed:.1f}s")

        return results

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
    #: model NUTS prefix -> CAPRI member-state code where they differ (Belgium and Luxembourg are one CAPRI
    #: member state, BL; Ireland IR; Greece EL in both)
    _MS_CODE = {"BE": "BL", "LU": "BL", "IE": "IR", "GR": "EL"}

    @classmethod
    def member_state_of(cls, region: str) -> str:
        """CAPRI member-state code (e.g. DE000000) of a model region."""
        return cls._MS_CODE.get(region[:2], region[:2]) + "000000"

    def feed_bulk_price_ratios(self, price_signal) -> dict:
        """{(member state, bulk): price relative to the base} of CAPRI's feed bulks (feedBlkPrice_) at the EU
        price changes of the price signal (MarketModule.feed_bulk_price_ratio)."""
        mm = self.market_module
        sig = price_signal if price_signal is not None else {}
        ratio = {c: 1.0 + float(sig.get(c, 0.0)) for c in mm.commodities} if hasattr(sig, "get") else {}
        return {k: mm.feed_bulk_price_ratio(k[0], k[1], ratio)
                for k in (mm._feed_bulk_params().get("bulks") or {})}

    def _update_rations(self, price_signal) -> None:
        """Solve every EU region-animal ration at the current feed prices and hand
        the result to the supply module (feed costs, fodder balance) and to the
        market's feed demand. Cereals and protein-rich feed: the member state's CAPRI bulk price indices
        (feedBlkPrice_); fodder at its balance shadow price; feeds without a market at base value."""
        from capri_mod.feed.ration import RationModel
        rm = getattr(self, "_ration_model", None)
        if rm is None:
            # the ration model's own nitrate ingredient (an early approximation) is superseded by CAPRI's
            # supplement options in the supply model (envind/line_nitr.gms, Sprint 9g): never both
            _supp_in = bool(getattr(self, "use_feed_in_supply", False)) and any(
                o_ == "Nitr_Tot" for v_ in ((self.data.get("genetics_effects") if isinstance(self.data, dict) else None)
                                           or {}).values() for (_a, o_) in v_)
            RationModel.use_nitrate = bool(getattr(self, "use_nitrate", False)) and not _supp_in
            rm = RationModel(self.data_dir if hasattr(self, "data_dir") else None,
                             scale=(self.data.get("ration_scale") if isinstance(self.data, dict) else None),
                             price_scale=(self.data.get("ration_bulk_price") if isinstance(self.data, dict) else None),
                             factor=(self.data.get("ration_factor") if isinstance(self.data, dict) else None))
            self._ration_model = rm
        sig = price_signal if price_signal is not None else {}
        g = (lambda c: float(sig.get(c, 0.0)) if hasattr(sig, "get") else 0.0)
        # FEED BULK PRICES per member state (CAPRI feedBlkPrice_): the CES price index of the member state's
        # cereals (FCER) and protein-rich feed (FPRO, with cakes, DDGS, pulses, oils, milling by-products)
        bix = self.feed_bulk_price_ratios(price_signal)
        self.supply_module.feed_bulk_ratio = bix
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
        # FODDER VALUED AT ITS BALANCE SHADOW PRICE, as CAPRI: home-grown fodder
        # in the ration was priced at its base value, so dearer cereals pushed
        # rations to maize as if land were no scarcer. Each fodder's price is
        # scaled by (current fodder-balance dual / its base value) from the last
        # regional solve - exactly 1 at base.
        _fb = (self.data.get("fodder_balance") if isinstance(self.data, dict) else None) or {}
        _last = getattr(self, "_last_supply_results", None) or {}
        _fratio = {}
        for _reg, _res in (_last.items() if (price_signal is not None and getattr(self, "fodder_at_shadow_price", False)) else []):
            _sp = getattr(_res, "shadow_prices", {}) or {}
            for _feed, _rec in (_fb.get(_reg) or {}).items():
                _ref = (getattr(self, "_fodder_dual_base", None) or {}).get(_reg, {})
                _v0 = float(_ref.get("fodder_" + _feed, 0.0) or _rec.get("value_eur_t", 0.0) or 0.0)
                _mu = _sp.get("fodder_" + _feed)
                if _v0 > 0 and _mu is not None:
                    _fratio[(_reg, _feed)] = max(0.0, float(_mu)) / _v0
        # DAMPED and BOUNDED like the rations: halfway from the previous ratio each
        # iteration (same fixed point; undamped, ration <-> fodder dual chased each
        # other and Farm-to-Fork did not converge), kept within [0.2, 5] since a
        # balance flipping between binding and slack makes its dual jump to 0
        _fprev = getattr(self, "_fodder_ratio_prev", None) or {}
        if price_signal is None:
            _fprev = {}
        for _k, _q in list(_fratio.items()):
            _q = min(5.0, max(0.2, _q))
            _qp = _fprev.get(_k, 1.0)
            _fratio[_k] = _qp + 0.5 * (_q - _qp)
        self._fodder_ratio_prev = dict(_fratio)
        for (reg, act), r in rm.rations.items():
            _ms = self.member_state_of(reg)
            p = rm.price_vector((reg, act), bulk_ratio={b_: x_ for (m_, b_), x_ in bix.items() if m_ == _ms})
            if _fratio:
                for _i, _f in enumerate(r.feeds):
                    _q = _fratio.get((reg, _f))
                    if _q is not None:
                        p[_i] = p[_i] * _q
            x, ok = r.solve(p)
            if not ok:
                x = r.x0
            xp = prev.get((reg, act))
            if xp is not None:
                x = xp + alpha * (x - xp)
            newprev[(reg, act)] = x
            xd = dict(zip(r.feeds, x))
            _dmi = float(r.dm @ x)
            _nk = float(xd.get("NITR", 0.0))
            state.setdefault(reg, {})[act] = {"x": xd,
                                              "dcost": r.cost(x, p) - r.cost(r.x0, r.p0),
                                              "nitr_kg": _nk,
                                              "nitr_share": (_nk / _dmi) if _dmi > 0 else 0.0}
        self.supply_module.ration_state = state
        # rations and CURRENT feed prices for feeding inside the supply model
        # the per-region rations dicts are built ONCE per ration model and reused, so the
        # feed-in-supply block cache (keyed on the dict's identity) hits; only prices change
        if getattr(self, "_feed_rations_for", None) is not rm:
            _fr = {}
            for (reg, act), r in rm.rations.items():
                _fr.setdefault(reg, {})[act] = r
            self._feed_rations_stable = _fr
            self._feed_rations_for = rm
        _fp = {}
        for (reg, act), r in rm.rations.items():
            _ms = self.member_state_of(reg)
            _fp.setdefault(reg, {})[act] = rm.price_vector((reg, act), bulk_ratio={b_: x_ for (m_, b_), x_ in bix.items()
                                                                                    if m_ == _ms})
        self.supply_module.feed_rations = self._feed_rations_stable
        self.supply_module.feed_prices = _fp
        self._ration_state = state
        self._ration_prev = newprev

    POOL_OF_PREFIX = {"BE": "BL", "LU": "BL", "IE": "IR"}

    #: young-animal markets: largest EU imbalance (share of production) accepted at convergence
    YANI_TOL = 0.005
    #: damping of the Newton step for young-animal prices
    YANI_RELAXATION = param("YANI_RELAXATION")

    def _young_animal_balance(self, supply_results):
        """EU net balance (production - use, 1000 head) and production of each young-animal
        good, from the regional results and CAPRI's coefficients."""
        from capri_mod.supply.supply_module import young_animal_table
        tab = young_animal_table()
        net, prod = {}, {}
        for reg, res in (supply_results or {}).items():
            rec = tab.get(reg) or {}
            x = getattr(res, "activities", None)
            if x is None:
                continue
            # bulls and heifers at the low-intensity activity turn over more animals per stall, each
            # bought as a young animal (Sprint 7c): z stalls x use per head x (low - high) / average
            cz = getattr(res, "cattle_shift", None) or {}
            ct = (self.data.get("cattle_intensity") or {}).get(reg) or {}
            for g, r in rec.items():
                p_ = sum(float(c) * float(x.get(a, 0.0) or 0.0) for a, c in r.get("produce", {}).items())
                u_ = sum(float(c) * float(x.get(a, 0.0) or 0.0) for a, c in r.get("use", {}).items())
                u_ += sum(float(c) * float(cz.get(a, 0.0)) * float(ct[a]["dyoung_rel"])
                          for a, c in r.get("use", {}).items() if a in cz and a in ct)
                net[g] = net.get(g, 0.0) + p_ - u_
                prod[g] = prod.get(g, 0.0) + p_
        return net, prod

    def _update_young_animal_prices(self, supply_results, ref) -> None:
        """Clear CAPRI's young-animal markets (arm/market_model.gms yaniMarket_): the EU net
        balance of each good stays at its baseline level (young animals are not traded with
        third countries) and the prices adjust. As CAPRI's market model, the supply response
        is approximated from the supply models' PMP terms - here dx = Q^-1 dc per region (the
        normalised-quadratic approximation, CAPRI p_hessNQSupp) - and the approximation is
        renewed every outer iteration; a damped Newton step on the price ratios."""
        from capri_mod.supply.supply_module import young_animal_table
        tab = young_animal_table()
        goods = sorted(ref)
        gi = {g: i for i, g in enumerate(goods)}
        net, prod = self._young_animal_balance(supply_results)
        J = np.zeros((len(goods), len(goods)))
        sm = self.supply_module
        for reg, res in (supply_results or {}).items():
            rec = tab.get(reg)
            model = getattr(sm, "_models", {}).get(reg)
            if not rec or model is None or getattr(model, "Q", None) is None:
                continue
            acts = list(model.acts)
            Qi = getattr(model, "_Q_inv", None)
            if Qi is None or Qi.shape[0] != len(acts):
                Qi = np.linalg.pinv(np.asarray(model.Q, float))
                model._Q_inv = Qi
            N = np.zeros((len(acts), len(goods))); v = np.zeros(len(goods))
            for g, r in rec.items():
                if g not in gi:
                    continue
                v[gi[g]] = float(r.get("value_eur_head", 0.0) or 0.0) * float(
                    ((self.data.get("young_animal_value_factor") or {}).get(reg) or {}).get(g, 1.0))
                for a, c in r.get("produce", {}).items():
                    if a in acts:
                        N[acts.index(a), gi[g]] += float(c)
                for a, c in r.get("use", {}).items():
                    if a in acts:
                        N[acts.index(a), gi[g]] -= float(c)
            J += N.T @ Qi @ (N * v)
        gap = np.array([net.get(g, 0.0) - ref[g] for g in goods])
        scale = np.array([max(prod.get(g, 0.0), 1.0) for g in goods])
        self._yani_imbalance = float(np.max(np.abs(gap) / scale))
        try:
            d = np.linalg.solve(J, -gap)
        except np.linalg.LinAlgError:
            d = np.linalg.lstsq(J, -gap, rcond=None)[0]
        ratio = sm.yani_price_ratio or {g: 1.0 for g in goods}
        for g in goods:
            step = float(np.clip(self.YANI_RELAXATION * d[gi[g]], -0.3, 0.3))
            ratio[g] = float(np.clip(ratio.get(g, 1.0) + step, 0.2, 5.0))
        sm.yani_price_ratio = ratio
        self._yani_trace.append({"ratio": dict(ratio), "imbalance": self._yani_imbalance})
        if self.verbose:
            print("    [Young animals] imbalance %.4f | price ratios %s" % (
                self._yani_imbalance, {g: round(r_, 3) for g, r_ in ratio.items()}))

    def _update_manure_pools(self) -> None:
        """Clear CAPRI's CONNECTED manure pools on the regions' EXACT schedules.

        Each region's solve gives threshold prices for trading, from the
        reduced costs of its trade variables at the solution:
          exports e(p) = clip((th_e - p)/s, 0, manure produced),
                   th_e = p_now + s e_now - rc_e
          imports i(p) = max(0, (p - th_i)/s),  th_i = p_now - s i_now + rc_i
        (s = CAPRI's trade-cost slope). Pool k's net export z_k(p) is their sum
        - piecewise linear WITH the kinks where regions start or stop trading
        (local slopes ignored them and the search stalled: plan vs realised
        4.0, then 2.3 x supply). The connected equilibrium is the dual of the
        Takayama-Judge problem:
            min_p  sum_k Phi_k(p_k)   s.t.  p_k - p_l <= c_kl  (CAPRI arbitrage)
        with Phi_k = integral of z_k (convex, closed form, slope -z_k).
        """
        import json as _json
        from pathlib import Path as _P
        from scipy.optimize import nnls as _nnls, minimize as _min
        sm = self.supply_module
        pools = dict(getattr(sm, "manure_pool_price", None) or {})
        cost = getattr(self, "_pool_cost_cache", None)
        if cost is None:
            f = _P(__file__).resolve().parents[1] / "capri_data" / "2017" / "environment" / "manure_pool_costs.json"
            cost = {}
            if f.exists():
                for k, v in _json.load(open(f))["pairs"].items():
                    a, b = k.split("|"); cost[(a, b)] = v["eur_per_t_n"] / 1000.0
            self._pool_cost_cache = cost
        sched, es, sup = {}, {}, {}
        for reg, mo in getattr(sm, "_models", {}).items():
            pc = getattr(mo, "_pool_cols", []) or []
            aug = getattr(mo, "_last_aug", None)
            s0 = float(getattr(mo, "_manure_supply0", 0.0) or 0.0)
            if len(pc) != 2 or aug is None or s0 <= 0:
                continue
            Q, c, A, b, y = aug
            if max(pc) >= len(y):          # stored problem predates the market columns
                continue
            # row duals: the conic solve's own multipliers when the region was solved with feeding
            # inside (its feed block is not in the stored QP, so duals recovered from the QP's
            # KKT conditions were wrong there and the pools stopped clearing); else recovered by
            # NNLS from the active rows of the stored QP
            zc = getattr(mo, "_last_conic_duals", None)
            if zc is not None and len(zc) == A.shape[0]:
                lam = np.maximum(np.asarray(zc, float), 0.0)
            else:
                act = [r for r in range(A.shape[0]) if A[r] @ y >= b[r] - 1e-6 * max(1.0, abs(float(b[r])))]
                bnd = [q for q in range(len(y)) if y[q] <= 1e-9]
                M = np.hstack([A[act].T if act else np.zeros((len(y), 0)), -np.eye(len(y))[:, bnd]])
                gvec = -(Q @ y + c)
                if M.shape[1]:
                    sc = np.maximum(np.abs(M).max(axis=0), 1e-12)
                    mu, _r = _nnls(M / sc, gvec, maxiter=60 * M.shape[1]); mu = mu / sc
                    lam = np.zeros(A.shape[0]); lam[act] = mu[:len(act)]
                else:
                    lam = np.zeros(A.shape[0])
            je, ji = pc
            sl = float(Q[je, je])
            # the pool price the region was solved at (its export column's cost also carries the emission tax,
            # which belongs to the threshold, not to the price)
            pnow = float(getattr(mo, "manure_pool_price", 0.0) or 0.0)
            rce = max(0.0, float(c[je] + Q[je] @ y + A[:, je] @ lam))
            rci = max(0.0, float(c[ji] + Q[ji] @ y + A[:, ji] @ lam))
            # QUASI-NEWTON correction: regions respond less than 1/s per unit of
            # price, because their own N shadow price moves as they trade. Each
            # pool's response factor kappa (realised / planned, Broyden-type)
            # scales the schedules: slope s / kappa, re-anchored at the current
            # trade and price.
            k_ = self.POOL_OF_PREFIX.get(reg[:2], reg[:2])
            kap = float(((getattr(self, "_pool_state", None) or {}).get("_kappa") or {}).get(k_, 1.0))
            sl = sl / max(kap, 1e-3)
            th_e = pnow + sl * float(y[je]) - rce
            th_i = pnow - sl * float(y[ji]) + rci
            # export cap = manure produced at the current solution (a first draft
            # read the LAST row as the cap, but the land rows follow it, so the
            # cap came from the grassland row and exports vanished)
            ev = getattr(mo, "_pool_manure_vec", None)
            emax = float(ev @ y[:len(ev)]) if ev is not None else 0.0
            k = self.POOL_OF_PREFIX.get(reg[:2], reg[:2])
            sched.setdefault(k, []).append((th_e, th_i, sl, max(emax, 0.0)))
            es[k] = es.get(k, 0.0) + float(y[je]) - float(y[ji])
            sup[k] = sup.get(k, 0.0) + s0
        keys = sorted(sched)
        if not keys:
            self._pool_imbalance = 0.0
            return
        hist = getattr(self, "_pool_state", None) or {}
        plan = hist.get("_plan")
        # Broyden-type update of each pool's response factor: realised change in
        # net exports over the change the previous plan expected
        kappa = dict(hist.get("_kappa") or {})
        es_prev = hist.get("_es") or {}
        if plan and es_prev:
            for k in es:
                planned = float(plan.get(k, 0.0)) - float(es_prev.get(k, 0.0))
                realised = float(es[k]) - float(es_prev.get(k, 0.0))
                if abs(planned) > 0.002 * max(sup.get(k, 0.0), 1.0):
                    kappa[k] = float(np.clip(kappa.get(k, 1.0) * realised / planned, 0.05, 1.5))
        hist["_kappa"] = kappa
        self._pool_state = hist
        _ratios = {k: (abs(es[k] - plan.get(k, 0.0)) if plan else abs(es[k])) / sup[k] for k in keys}
        worst = max(_ratios.values())
        self._pool_worst_key = max(_ratios, key=_ratios.get)
        # ---- PRIMAL spatial equilibrium on the exact schedules (shipment side),
        # solved with the model's own exact QP solver (the dual price problem
        # with SLSQP failed on the kinks and kept stale prices).
        from capri_mod.supply.qp_solver import solve_qp_ldp, solve_qp
        reg_list = [(k, te, ti, sl, em) for k in keys for (te, ti, sl, em) in sched[k]]
        arcs = [(a, b_, cc) for (a, b_), cc in cost.items() if a in sched and b_ in sched]
        nr, na = len(reg_list), len(arcs)
        nv = 2 * nr + na                                  # e_r, i_r, T_arc
        Qp = np.zeros((nv, nv)); cp_ = np.zeros(nv)
        min_sl = min(r_[3] for r_ in reg_list) if reg_list else 1.0
        for q, (k, te, ti, sl, em) in enumerate(reg_list):
            Qp[q, q] = sl; cp_[q] = -te                   # exporters' benefit (negated)
            Qp[nr + q, nr + q] = sl; cp_[nr + q] = ti     # importers' cost
        for t, (a, b_, cc) in enumerate(arcs):
            Qp[2 * nr + t, 2 * nr + t] = 1e-3 * min_sl; cp_[2 * nr + t] = cc   # scaled ridge
        rows, rhs, eqs, eqb = [], [], [], []
        for q, (k, te, ti, sl, em) in enumerate(reg_list):
            r_ = np.zeros(nv); r_[q] = 1.0; rows.append(r_); rhs.append(max(em, 0.0))    # e <= manure produced
        for k in keys:
            bal = np.zeros(nv)
            for q, rec in enumerate(reg_list):
                if rec[0] == k:
                    bal[q] = 1.0; bal[nr + q] = -1.0
            for t, (a, b_, cc) in enumerate(arcs):
                if a == k: bal[2 * nr + t] -= 1.0
                if b_ == k: bal[2 * nr + t] += 1.0
            eqs.append(bal); eqb.append(0.0)                 # pool balance as a TRUE equality
        Ap, bp = np.array(rows), np.array(rhs)
        # Interior point (Newton): Clarabel when installed, else the built-in
        # primal-dual method (capri_mod/supply/convex_qp.py). The active-set loop
        # failed on the full EU (iteration limit; the balance written as two tight
        # inequalities made its KKT systems singular).
        from capri_mod.supply.convex_qp import solve_convex_qp
        # Scaled: objective by its largest coefficient (prices reach hundreds of EUR/kg N under
        # CAPRI's land rules, slopes differ by orders of magnitude after the kappa correction).
        # Clarabel's AlmostSolved (reduced accuracy) is accepted - the pool test below checks
        # the realised clearing anyway; a failed solve keeps the old prices and is reported.
        _sc = max(float(np.abs(cp_).max()), float(np.abs(Qp).max()), 1e-9)
        sol, ok, _info = solve_convex_qp(Qp / _sc, cp_ / _sc, Ap, bp, np.array(eqs), np.array(eqb), tol=1e-8, max_iter=300)
        if not ok and "AlmostSolved" in str(_info.get("status", "")):
            ok = True
        if _info.get("y") is not None:
            _info["y"] = np.asarray(_info["y"], float) * _sc
        self._pool_solver = _info
        self._pool_solver_status = str(_info.get("status", "?"))
        pnew = {}
        if ok:
            # POOL PRICE = shadow price of the pool's balance equation. For an
            # exporting region the optimality condition is s e - th_e + y_k = 0,
            # so y_k = th_e - s e: the price definition itself, available for
            # EVERY pool. (Taken from actively trading regions only, a pool
            # whose regions did not trade kept a stale price and never cleared
            # - Malta, Cyprus, Lithuania, Latvia on the full EU.)
            yv = _info.get("y")
            for j, k in enumerate(keys):
                if yv is not None and j < len(yv):
                    pnew[k] = float(yv[j])
                else:
                    pnew[k] = float(pools.get(k, 0.0))
            ship = {k: 0.0 for k in keys}
            for t, (a, b_, cc) in enumerate(arcs):
                ship[a] += sol[2 * nr + t]; ship[b_] -= sol[2 * nr + t]
            self._pool_flows = {(a, b_): float(sol[2 * nr + t]) for t, (a, b_, cc) in enumerate(arcs) if sol[2 * nr + t] > 1e-3}
            self._pool_state = {"_plan": ship, "_kappa": kappa, "_es": dict(es)}
        else:
            pnew = {k: float(pools.get(k, 0.0)) for k in keys}
        # CLEARING test on the REALISED regional trade: net exports of each pool
        # must equal its planned net shipments (zero for a closed pool)
        plan_now = (hist.get("_plan") or {}) if isinstance(hist, dict) else {}
        worst = max(abs(es[k] - plan_now.get(k, 0.0)) / sup[k] for k in keys)
        if not ok:
            worst = max(worst, 1.0)
        # ADAPTIVE DAMPING of the move to the new equilibrium prices (exact for
        # the current regional schedules; the schedules shift as regions respond).
        # A fixed half step near the solution was stable but slow (full EU: worst
        # pool 5.1% -> 4.3% over 12 iterations). Now: full steps while the gap
        # keeps falling (x1.25 per fall, capped at 1), halved (min 0.25) when it
        # rises.
        acc = getattr(self, "_pool_accel", None) or {}
        om = float(acc.get("_omega", 1.0))
        prev_gap = acc.get("_gap")
        cur_gap = float(max(worst, abs(sum(es.values())) / max(sum(sup.values()), 1e-9)))
        if prev_gap is not None:
            om = min(1.0, om * 1.25) if cur_gap < prev_gap else max(0.25, om * 0.5)
        acc["_omega"], acc["_gap"] = om, cur_gap
        for k in list(pnew):
            p_old = None
            for reg_ in getattr(sm, "_models", {}):
                if self.POOL_OF_PREFIX.get(reg_[:2], reg_[:2]) == k and reg_[:2] in pools:
                    p_old = float(pools[reg_[:2]]); break
            if p_old is not None:
                pnew[k] = p_old + om * (pnew[k] - p_old)
        self._pool_accel = acc
        out = {}
        for reg in getattr(sm, "_models", {}):
            k = self.POOL_OF_PREFIX.get(reg[:2], reg[:2])
            if k in pnew:
                out[reg[:2]] = pnew[k]
        sm.manure_pool_price = out
        # EU-WIDE conservation: realised net exports into all pools should sum
        # to zero; on the full EU it lagged the per-pool measure (200 kt N
        # unaccounted at iteration 6 while every pool was within ~6%)
        eu_unacc = abs(sum(es.values())) / max(sum(sup.values()), 1e-9)
        self._pool_eu_unaccounted = float(eu_unacc)
        self._pool_imbalance = float(max(worst, eu_unacc))
        self._pool_trace = getattr(self, "_pool_trace", []) + [(float(worst), float(eu_unacc))]

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
                mm._feed_bulk_index = None
                return
            from capri_mod.data.definitions import ANIMALS
            mult = {"BROI": getattr(type(self.supply_module), "BROILER_BIRDS_PER_PLACE", 1.0)}
            # feed bulks per member state (CAPRI v_feedBlk): cereals FCER and protein-rich feed FPRO, now and base
            blk = {}
            fmil = [0.0, 0.0]                       # feed from milk products (FMIL): now, base
            for region, res in supply_results.items():
                ms = self.member_state_of(region)
                bc = blk.setdefault((ms, "FCER"), [0.0, 0.0])
                bpr = blk.setdefault((ms, "FPRO"), [0.0, 0.0])
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
                        # feeding inside the supply model: the region's own feed totals (t)
                        _ft = (getattr(res, "feed_t", None) or {}).get(a)
                        # every tradable bulk of CAPRI (FEED_TRD: FCER, FPRO, FENE, FOTH, FMIL; Sprint 9h adds the
                        # last three per member state)
                        for _b in self.FEED_BULKS:
                            if _b in xb:
                                _acc = blk.setdefault((ms, _b), [0.0, 0.0])
                                _acc[0] += (_ft.get(_b, 0.0) if _ft is not None else x * _rr["x"].get(_b, 0.0)) / 1000.0
                                _acc[1] += x0 * xb[_b] / 1000.0
                        if "FMIL" in xb:              # feed from milk products (calves; CAPRI FMIL)
                            fmil[0] += (_ft.get("FMIL", 0.0) if _ft is not None else x * _rr["x"].get("FMIL", 0.0)) / 1000.0
                            fmil[1] += x0 * xb["FMIL"] / 1000.0
                        continue
                    if qp == qp:                    # protein-rich feed, t per head
                        bpr[0] += x * qp
                        bpr[1] += x0 * qp
                    if q == q:                      # CAPRI total / our herd, t per head
                        bc[0] += x * q
                        bc[1] += x0 * q
                        continue
                    if a not in fr.index:
                        continue
                    k = mult.get(a, 1.0)
                    for c in ("SWHE", "BARL", "CORN", "OCER"):
                        if c in fr.columns:
                            q = float(fr.at[a, c]) * k
                            bc[0] += x * q
                            bc[1] += x0 * q
            # CAPRI's market splits each member state's bulks into products (feedShareEqu_,
            # MarketModule.eu_feed_use); the market gets each bulk's change against the base
            mm._feed_bulk_index = {k: (v[0] / v[1] if v[1] > 0 else 1.0) for k, v in blk.items()}
            # DAIRY PRODUCTS FED (dairy Stage 3): the FMIL block follows the calves' milk feed, as CAPRI's
            # feed block FMIL (SMIP, WMIO, CASE, WHEP, BUTT, CREM, COCM, CHES, FRMI) follows the supply models
            mm._fmil_index = (fmil[0] / fmil[1]) if fmil[1] > 0 else 1.0
        except Exception:
            mm._feed_bulk_index = None

    #: CAPRI's tradable feed bulks (global/fromimpact/sets.gms FEED_TRD), priced by the market (feedBlkPrice_)
    FEED_BULKS = ("FCER", "FPRO", "FENE", "FOTH", "FMIL")

    #: CAPRI final product -> market commodity (tools/build_livestock_products.py)
    LIVESTOCK_PRODUCT_MARKET = {"COMI": "MILK", "SGMI": "MILK", "BEEF": "BEEF", "PORK": "PORK",
                                "POUM": "POUL", "EGGS": "EGGS", "SGMT": "SHGM"}

    def _livestock_products_by_country(self, supply_results):
        """Livestock market supply by country (1000 t): each region's animal output split into CAPRI's
        final products at the region's own product composition (livestock_output_by_product_coef) -
        dairy cows into milk and cull-cow beef, sheep and goats into meat and milk, laying hens into eggs
        and poultry meat. The split is the base composition per head; output itself follows the herd and
        the intensity splits (gross_output)."""
        coef = self.data.get("livestock_output_by_product_coef") if isinstance(self.data, dict) else None
        if coef is None or not supply_results:
            return None
        from collections import defaultdict as _dd
        from capri_mod.data.definitions import REGION_TO_COUNTRY
        cols = {}
        for c in coef.columns:
            a, p = c.split(".", 1)
            if p in self.LIVESTOCK_PRODUCT_MARKET:
                cols.setdefault(a, []).append((c, self.LIVESTOCK_PRODUCT_MARKET[p]))
        rows = _dd(lambda: _dd(float))
        for r, res in supply_results.items():
            go = getattr(res, "gross_output", None)
            if go is None or r not in coef.index:
                continue
            key = REGION_TO_COUNTRY.get(r, r)
            for a, parts in cols.items():
                g = float(go.get(a, 0.0)) if a in go.index else 0.0
                if not g == g or g == 0.0:
                    continue
                v = [(float(coef.at[r, c]) if pd.notna(coef.at[r, c]) else 0.0, m) for c, m in parts]
                tot = sum(x for x, _ in v)
                if tot > 0:
                    for x, m in v:
                        rows[key][m] += g * x / tot
        return pd.DataFrame({k: dict(v) for k, v in rows.items()}).T.fillna(0.0) if rows else None

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
            "BARL": "BARL",
            "CORN": "CORN", "OCER": "OCER", "RAPE": "RAPE",
            "SUNF": "SUNF", "SOYA": "SOYA",
            "POTA": "POTA", "PULS": "PULS",
            "TOMA": "TOMA", "OVEG": "OVEG", "APPL": "APPL",
            "OFRU": "OFRU", "CITR": "CITR", "WINE": "WINE",
            # (wheat, olives and paddy rice are bridged below, as CAPRI's wheat, olive oil and milled rice)
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
        _lsc = getattr(self, "_ls_by_country", None)
        for mcomm, acts in livestock_maps.items():
            present = [a for a in acts if a in supply_agg.columns]
            if _lsc is not None and mcomm in _lsc.columns and mcomm in market_supply.columns:
                market_supply[mcomm] = _lsc[mcomm].reindex(market_supply.index).fillna(0.0)
            elif present and mcomm in market_supply.columns:
                market_supply[mcomm] = supply_agg[present].sum(axis=1)

        for act, mcomm in direct_maps.items():
            if act in supply_agg.columns and mcomm in market_supply.columns:
                market_supply[mcomm] = supply_agg[act]
        # wheat: CAPRI's market product is wheat (WHEA = soft + durum); durum's price follows it
        if "SWHE" in market_supply.columns:
            market_supply["SWHE"] = sum(supply_agg[a] for a in ("SWHE", "DWHE") if a in supply_agg.columns)
        # olives and paddy rice reach the market as CAPRI's olive oil and milled rice (processing_yields.csv)
        for act, mc in (("OLIV", "OLIV"), ("PARI", "PARI")):
            if act in supply_agg.columns and mc in market_supply.columns:
                market_supply[mc] = supply_agg[act] * pd.Series(
                    {r: self._processing_yield(r, act) for r in supply_agg.index}).reindex(supply_agg.index)
        # the other-cereals market carries rye and oats (CAPRI's RYEM and OATS; their supply never reached
        # a market and their price signal already came from OCER)
        if "OCER" in market_supply.columns:
            market_supply["OCER"] = sum(supply_agg[a] for a in ("OCER", "RYEM", "OATS") if a in supply_agg.columns)

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

        # Sugar beet -> white sugar in the member state (CAPRI: MAPR(SUGA) = PRCY x PRCM(SUGB), 96% of the EU
        # harvest processed): sugar per tonne of beet harvested from CAPRI's 2030 reference, per member state
        # (tools/build_sugar_processing.py). Beet has no market of its own; its price follows the sugar price.
        if "SUGB" in supply_agg.columns and "SUGR" in market_supply.columns:
            market_supply["SUGR"] = supply_agg["SUGB"] * pd.Series(
                {r: self._sugar_per_beet(r) for r in supply_agg.index}).reindex(supply_agg.index)

        # Dairy: DCOW gross output -> milk tonnes via a calibrated factor, then
        # split into products with real FAO ratios. DCOW gross_output is already
        # a (per-animal, non-tonne) unit, so a single calibrated factor maps it
        # to base milk production; re-multiplying by a raw milk yield here would
        # double-convert (it inflated milk ~1.3x and all dairy products with it).
        if "DCOW" in supply_agg.columns:
            # raw milk = cow milk COMI + sheep and goat milk SGMI by CAPRI's product split of each
            # animal's output (livestock_output_by_product_coef); the old route took dairy-cow output
            # x 0.9575 and left sheep and goat milk in the sheep-meat market
            milk = (_lsc["MILK"].reindex(market_supply.index).fillna(0.0)
                    if _lsc is not None and "MILK" in _lsc.columns else supply_agg["DCOW"] * 0.9575)
            if "MILK" in market_supply.columns:
                market_supply["MILK"] = milk
            # dairy products at CAPRI's own member-state yields of its 2030 reference (output less
            # processing, per tonne of raw milk produced: dairy_processing.csv), replacing FAO EU-average
            # ratios (cheese 0.0456 against CAPRI's 0.068). With the dairy block on, the market replaces
            # these by the block's output.
            for mc, ck in (("BUTR", "BUTT"), ("SKIM", "SMIP"), ("CHES", "CHES"), ("WHEY", "WHEP"), ("FRMI", "FRMI"),
                           ("CREM", "CREM"), ("COCM", "COCM"), ("WMIO", "WMIO"), ("CASE", "CASE")):
                if mc in market_supply.columns:
                    market_supply[mc] = milk * pd.Series(
                        {r: self._dairy_yield(r, ck) for r in market_supply.index}).reindex(market_supply.index)

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

    #: model country code -> CAPRI member state (BE and LU are CAPRI's BL)
    _CAPRI_MS = {"IE": "IR", "GR": "EL", "BE": "BL", "LU": "BL"}

    def _dairy_yield(self, region: str, product: str) -> float:
        """A dairy product's output less processing per tonne of raw milk (cow + sheep and goat) in the
        region's member state, CAPRI 2030 reference (dairy_processing.csv); EU ratio where CAPRI has no
        dairy data for the member state."""
        tab = getattr(self, "_dairy_yield_cache", None)
        if tab is None:
            from pathlib import Path
            from capri_mod.data.loaders import resolve_data_file
            base = Path(getattr(self, "data_dir", None) or Path(__file__).resolve().parents[1] / "capri_data")
            f = resolve_data_file(base, "dairy_processing.csv")
            dp = pd.read_csv(f)
            net = (dp["q_kt"].fillna(0.0) - dp["proc_kt"].fillna(0.0))
            dp = dp.assign(net=net)
            raw = dp[dp["item"].isin(["COMI", "SGMI"])].groupby("ms")["q_kt"].sum()
            tab = {}
            for k in ("BUTT", "SMIP", "CHES", "WHEP", "FRMI", "CREM", "COCM", "WMIO", "CASE"):
                q = dp[dp["item"] == k].set_index("ms")["net"]
                tab.update({(ms, k): float(q.get(ms, 0.0)) / float(raw[ms]) for ms in raw.index if raw[ms] > 0})
                tab[("_EU", k)] = float(q.sum()) / float(raw.sum())
            self._dairy_yield_cache = tab
        ms = self._CAPRI_MS.get(str(region)[:2], str(region)[:2]) + "000000"
        return tab.get((ms, product), tab[("_EU", product)])

    def _processing_yield(self, region: str, raw: str) -> float:
        """CAPRI's olive oil per tonne of olives (member state) and milled rice per tonne of paddy (EU),
        2030 reference (processing_yields.csv)."""
        tab = getattr(self, "_proc_yield_cache", None)
        if tab is None:
            from pathlib import Path
            from capri_mod.data.loaders import resolve_data_file
            base = Path(getattr(self, "data_dir", None) or Path(__file__).resolve().parents[1] / "capri_data")
            f = resolve_data_file(base, "processing_yields.csv")
            py = pd.read_csv(f)
            tab = {(r["ms"], r["raw"]): float(r["yield"]) for _, r in py.iterrows()}
            self._proc_yield_cache = tab
        if raw == "PARI":
            return tab[("_EU", "PARI")]
        ms = self._CAPRI_MS.get(str(region)[:2], str(region)[:2]) + "000000"
        return tab.get((ms, raw), tab[("_EU", raw)])

    def _sugar_per_beet(self, region: str) -> float:
        """White sugar per tonne of sugar beet harvested in the region's member state (CAPRI 2030 reference:
        MAPR(SUGA) / GROF(SUGB)); member states without beet in CAPRI take the EU ratio."""
        tab = getattr(self, "_sugar_rate_cache", None)
        if tab is None:
            sp = self.data.get("sugar_processing")
            tab = {}
            if sp is not None and len(sp):
                eu = sp[~sp.index.isin(["UK000000", "AL000000", "BA000000", "CS000000", "MK000000", "ME000000",
                                        "KO000000", "TUR", "NO000000", "CH000000"])]
                tab = {ms: float(r["sugar_per_beet"]) for ms, r in sp.iterrows()}
                tab["_EU"] = float(eu["sugar_mapr_kt"].sum() / eu["beet_grof_kt"].sum())
            self._sugar_rate_cache = tab
        ms = self._CAPRI_MS.get(str(region)[:2], str(region)[:2]) + "000000"
        if ms in tab:
            return tab[ms]
        if "_EU" in tab:
            return tab["_EU"]
        raise RuntimeError("sugar_processing.csv missing: run tools/build_sugar_processing.py")

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
