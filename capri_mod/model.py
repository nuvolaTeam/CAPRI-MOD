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

    # Run a policy counterfactual (CAPRI's Farm-to-Fork)
    from capri_mod.policy.greendeal import farm_to_fork_scenario
    f2f = model.run(custom_scenario=farm_to_fork_scenario())

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
from capri_mod.settings import setting, tri_state, current as _settings
from capri_mod.data.definitions import MS_CODE, capri_ms, REGION_TO_COUNTRY, EU_MS_BLOCK, SUP_NONEU, is_eu as _is_eu
from capri_mod.tableio import read_input


#: Nitrates Directive ceiling on organic N application (kg N per ha of UAA)


from capri_mod.coupling import (  # noqa: E402  (refactor stage 4a: the blocks)
    HessianBlock, FeedBlock, YoungAnimalBlock, PriceStepBlock, ManureBlock, BridgeBlock, ReportingBlock,
)


class CAPRIModel(HessianBlock, FeedBlock, YoungAnimalBlock, PriceStepBlock, ManureBlock, BridgeBlock, ReportingBlock):
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
    use_land_market = setting("supply.use_land_market")
    #: permanent-grassland decline allowed under the Green Deal (CAPRI default 0)
    grassland_allowance = setting("supply.grassland_allowance")
    #: CAPRI's manure trade (GUI "New Manure Trade Module", manureTradeNew; docs/MANURE_MARKET.md). ON by default
    #: as in CAPRI star 3.0's GUI (capri_gui_definition.xml: New_Manure_Trade_fromGUI = true). A scenario sets its
    #: own (PolicyScenario.manure_trade): JRC121368's Farm-to-Fork kept all manure in its region (p. 24), so
    #: farm_to_fork_scenario() turns it off; the setting holds for the scenario and its baseline.
    use_manure_market = setting("run.manure_trade", run_state=True)
    #: CAPRI's baseline calibration in projected years (Sprint 9p): largest remaining drift of a regional activity
    #: from its projected level, relative, for the baseline to count as converged
    BASE_CAL_TOL = setting("projection.base_cal_tol")
    #: CAPRI's market supply functions calibrated to the supply models at the baseline (supply/calibrate_supply.gms;
    #: model._market_supply_hessian), young-animal rows and columns included. ON since 24 October 2026 (CAPRI's
    #: setting; KNOWN_ISSUES K75): with it the young-animal markets clear inside the market with the products
    #: (CAPRI's yaniMarket_), which removes the slow beef / calf price mode of the update between solves. The
    #: Hessian is measured once per baseline (Farm-to-Fork 2030: 50 shocks, 49 min on 2 cores) and cached on disk.
    #: False: the market keeps its own-price anticipation of the EU supply response
    market_supply_nq = setting("market.market_supply_nq")
    #: CAPRI's endogenous biofuel markets (GUI "Endogenous bio-fuel markets", BIOF_M; docs/BIOFUEL_MARKET.md). ON
    #: by default as in CAPRI star 3.0's GUI (capri_gui_definition.xml BIOF_M = true). A scenario may set its own
    #: (PolicyScenario.biofuel_markets); the setting holds for the scenario and its baseline.
    biofuel_markets = setting("market.biofuel_markets")
    #: Convergence tolerance of the manure market: each country pool must clear
    #: to within this share of its manure supply (realised net exports vs net
    #: shipments) before the outer loop may stop. 0.03 = 3%: in a six-country
    #: Farm-to-Fork test results were already stable at that level (pigs and
    #: cattle unchanged to 0.1 point), while 1% needed about twice the
    #: iterations. Only used when use_manure_market is on.
    manure_pool_tolerance = setting("outer_loop.manure_pool_tol")
    #: outer-iteration cap used when the manure market is on. The pool loop
    #: contracts by a near-constant ~3.5% per iteration (regional schedules
    #: shift with the prices); on the full EU the worst pool reached 5.1% after
    #: 40 iterations, so 3% needs about 55.
    manure_max_outer_iter = setting("outer_loop.manure_max_outer_iter")
    #: CAPRI's young-animal markets (arm/market_model.gms yaniMarket_): calves, young cattle and replacement cows
    #: cleared inside the market model with the products, through the market's supply functions (with
    #: market.market_supply_nq; without it, and with the EU trade blocks, between market solves: K75);
    #: docs/YOUNG_ANIMALS.md. CAPRI's manure techniques, land balances without slack (LandBalNoSlak_) and N target
    #: per current hectare (e_SURTOTHa) are always on in the regional models (switches removed 27 October 2026)
    #: IPOPT's tolerance in the regional models (one tolerance throughout the outer loop)
    nlp_tol_final = setting("outer_loop.nlp_tol_final")

    def __init__(
        self,
        data_dir: Optional[str] = None,
        regions: Optional[List[str]] = None,
        verbose: Optional[bool] = None,
        base_year: Optional[str] = None,
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
        # Only the 2017 base exists, and several modules read capri_data/2017 directly (KNOWN_ISSUES K52f):
        # another year would mix vintages silently, so it is refused.
        if base_year is None:
            base_year = str(_settings().get("run.base_year"))
        if str(base_year) != "2017":
            raise ValueError(f"base_year {base_year!r}: only the 2017 base exists (capri_data/2017); "
                             "2030 runs go through the projection layer (ProjectionModule)")
        self.verbose   = bool(_settings().get("diagnostics.verbose")) if verbose is None else bool(verbose)
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
        from capri_mod.supply.inputs import SupplyInputs
        self.supply_module = SupplyModule(self.data, self.supply_elasticities,
                                          inputs=SupplyInputs(self.data_dir, base_year))
        from capri_mod.market.inputs import MarketInputs
        self.market_module = MarketModule(self.data, inputs=MarketInputs(self.data_dir, base_year))
        self.policy_module = PolicyModule(self.data)
        self.env_module    = EnvironmentalModule(self.data)
        if verbose:
            n_regions = len(self.data["areas"])
            print(f"  Regions: {n_regions} NUTS-2 regions")
            print(f"  Commodities: {len(self.data['areas'].columns)} crop activities")
            print(f"  Trade regions: {len(self.market_module.regions)}")
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
            if not _is_eu(region):                           # CAPRI: EU regions only (msNoEU)
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
    PRICE_SIGNAL_RELAXATION = setting("outer_loop.price_relaxation")

    def run(
        self,
        scenario: str = "BASELINE",
        world_price_shock: Optional[Dict[str, float]] = None,
        custom_scenario: Optional[PolicyScenario] = None,
        max_outer_iter: Optional[int] = None,
        outer_tolerance: Optional[float] = None,
        market_max_iter: Optional[int] = None,
        run_environmental: Optional[bool] = None,
        run_biofuel: Optional[bool] = None,
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
        market_max_iter   : Newton rounds of the bilateral market solve (default 100; 60 before 21 October 2026, when
                            the last rounds of some solves stopped at relative residuals of 2e-7 to 1e-6)
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
        # the run's settings (capri_mod/settings): arguments left None take them
        _st = _settings()
        if max_outer_iter is None:
            max_outer_iter = int(_st.get("outer_loop.max_outer_iter"))
        if market_max_iter is None:
            market_max_iter = int(_st.get("market.max_iter"))
        if run_environmental is None:
            run_environmental = bool(_st.get("run.run_environmental"))
        if run_biofuel is None:
            run_biofuel = bool(_st.get("run.report_biofuel"))
        # Get scenario
        if custom_scenario is not None:
            pol_scenario = custom_scenario
        else:
            pol_scenario = get_scenario(scenario)
        # CAPRI's manure trade: the scenario's setting (or the call's), else the model's default; it holds for
        # this run and the baseline it is compared with, and the model's default is restored afterwards
        self.__dict__.pop("use_manure_market", None)          # the setting, not an earlier run's value
        _mt_default = bool(_settings().get("run.manure_trade"))
        _mt = manure_trade if manure_trade is not None else getattr(pol_scenario, "manure_trade", None)
        _mt = _mt_default if _mt is None else bool(_mt)
        self.use_manure_market = _mt
        # CAPRI's endogenous biofuel markets (BIOF_M): the same rule
        _bm_default = bool(_settings().get("market.biofuel_markets"))
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
            del self.use_manure_market                         # back to the setting
            del self.market_module.biofuel_markets


    def _run_scenario(self, pol_scenario, scenario, world_price_shock, custom_scenario, max_outer_iter,
                      outer_tolerance, market_max_iter, run_environmental, run_biofuel,
                      carbon_price, biofuel_output_scale, regions, endotech, _mt, _bm=True) -> Dict:
        # the market supply Hessian of the baseline that has just run, if this run is a scenario on it: measured now,
        # from the state the baseline left, before this run changes anything (_measure_pending_hessian); any other
        # run drops it (a scenario on another baseline runs that baseline again, below)
        _pend = self.__dict__.pop("_hessian_pending", None)
        if (_pend is not None and not (custom_scenario is None and str(scenario).upper() == "BASELINE"
                                       and not world_price_shock)):
            from capri_mod.policy.endotech import effective as _et_eff0, key as _et_key0
            _k0 = (tuple(sorted(regions or list(self.data["areas"].index))),
                   _et_key0(_et_eff0(getattr(pol_scenario, "endotech", None), endotech)), bool(_mt), bool(_bm))
            if _pend["key"] == _k0:
                self._measure_pending_hessian(_pend)
        if outer_tolerance is None:
            outer_tolerance = float(_settings().get("outer_loop.outer_tolerance"))
        # the manure pools need more outer iterations than the default allows; an explicitly short run
        # (a test, a diagnostic) keeps its own limit
        if self.use_manure_market and int(max_outer_iter) >= int(_settings().get("outer_loop.manure_extend_min_iter")):
            max_outer_iter = max(int(max_outer_iter), int(self.manure_max_outer_iter))
        t_start = time.time()

        if self.verbose:
            print(f"Running scenario: {pol_scenario.name}")
            print(f"  {pol_scenario.description}")

        self.market_module.biofuel_output_scale = {"BIOE": 1.0, "BIOD": 1.0, **(biofuel_output_scale or {})}
        # CAPRI's biofuel mandate scenario (scen/bio_fuels/change_biof_mandate.gms): a policy shock of the
        # scenario, not of its baseline
        _bmand = getattr(pol_scenario, "biofuel_mandate", None)
        self.market_module.biofuel_mandate = float(_bmand) if _bmand is not None else 1.0
        # CAPRI's negProdPriceAllowed(rms, "MILK") of the scenario file (PolicyScenario.negative_milk_price)
        self.market_module.negative_milk_price = bool(getattr(pol_scenario, "negative_milk_price", False))
        self.market_module._milk_floor_hits = {}

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
        for _m in (getattr(self.supply_module, "_models", None) or {}).values():
            _m._nlp_fallback_log = []          # the NLP form's fallbacks of this run (metadata["nlp_fallback"])
        _key = (tuple(sorted(regions or list(self.data["areas"].index))), _et_key(_endotech), bool(_mt), bool(_bm))
        # A world-price shock makes the run a scenario against the unshocked baseline, also
        # under scenario="BASELINE" (it used to replace the cached baseline; KNOWN_ISSUES K52c).
        _is_base = (custom_scenario is None and str(scenario).upper() == "BASELINE" and not world_price_shock)
        _cache = getattr(self, "_eu_base_cache", {})
        self._eu_base_cache = _cache
        _mm = self.market_module
        if _is_base:
            _mm.seen.eu_base_supply = None
            # a baseline's market runs without a market supply Hessian (the one of an earlier baseline belonged to
            # another solution, possibly another region set); its own is measured when a scenario needs it
            _mm.par.supply_hessian = None
            self._hessian_key = None
            # Recalibrate at THIS run's first market solve. The calibration used
            # to freeze at the first solve an instance ever performed, so a model
            # whose first run was price-shocked or on a region subset carried a
            # calibration taken at the wrong point into every later run - results
            # depended on the instance's history (a null-trajectory projection,
            # built on a fresh instance, then differed from the base by 0.06%).
            _mm.par.demand_cal_frozen = None
            # ...and restore the market's PRISTINE base tables: EU rows of
            # commodities without farm-model supply are not re-aligned per run
            # and carried an earlier run's values (a model with a full-region
            # run in its history had different EU oil and cake consumption
            # than a fresh one; with crushing this reached farm results).
            if _mm.par.base_production0 is not None:
                _mm.par.base_production = _mm.par.base_production0.copy()
                _mm.par.base_consumption = _mm.par.base_consumption0.copy()
                _mm._dom0_cache = None          # base domestic prices for the feed terms
                _mm.par.eu_aligned_use = None      # re-recorded by this run's alignment
        else:
            _need_h = bool(getattr(self, "market_supply_nq", True))
            if _key not in _cache or (_need_h and getattr(self, "_hessian_key", None) != _key):
                # (a baseline in the cache whose Hessian is not at hand: another run came after it, so the models'
                # state is not the baseline's; the baseline is run again and its Hessian measured from it)
                _saved = self.verbose
                self.verbose = False
                self.run(scenario="BASELINE", regions=regions,
                         max_outer_iter=max_outer_iter, endotech=_endotech, manure_trade=bool(_mt),
                         biofuel_markets=bool(_bm))
                self.use_manure_market = bool(_mt)
                self.market_module.biofuel_markets = bool(_bm)
                self.verbose = _saved
                _pend = self.__dict__.pop("_hessian_pending", None)
                if _pend is not None:
                    self._measure_pending_hessian(_pend)
                self.policy_module.apply_scenario(pol_scenario)
                for _m in (getattr(self.supply_module, "_models", None) or {}).values():
                    _m._nlp_fallback_log = []  # the baseline's fallbacks are in the baseline's own metadata
            self.market_module.set_eu_base(*_cache[_key][:2])
            # reuse the calibration of the baseline for the same region set
            if len(_cache[_key]) > 2:
                _cal, _bp, _bc = _cache[_key][2:5]
                _mm.par.demand_cal_frozen = _cal.copy()
                _mm.par.base_production.loc[list(_mm.EU)] = _bp
                _mm.par.base_consumption.loc[list(_mm.EU)] = _bc
                if len(_cache[_key]) > 5 and _cache[_key][5][0] is not None:
                    _bs, _bpa, _bca, _cov, _eau = _cache[_key][5]
                    _mm.par.bilat = _bs
                    for _sc in (_bs or {}).values():
                        if getattr(_sc, "trq_row", None) is not None and _sc.trq_offset is not None:
                            _sc.trq_offset = _sc.trq_offset * 0.0
                    _mm.par.base_production = _bpa.copy()
                    _mm.par.base_consumption = _bca.copy()
                    _mm.par.crush_q0_override = dict(_cov)
                    import copy as _cp
                    _mm.par.eu_aligned_use = _cp.deepcopy(_eau)
                    _mm._crush_cache = None
                    _mm.sv.bilat_local_el = None
                    _mm.sv.bilat_last_r = None
                if len(_cache[_key]) > 6:
                    _mm.par.sup_milk0 = dict(_cache[_key][6])

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
        # exactly its own change: a -100 EUR/ha BISS cut yields -100 on wheat (until 23 October 2026 -125: an
        # eco-scheme share of 25% was added on top of Pillar I, which already contains it).
        from capri_mod.policy.policy_module import PolicyModule as _PM, \
            PolicyScenario as _PS
        _baseline_adders = _PM(self.data, _PS(name="BASELINE")) \
            .get_supply_policy_adders()
        policy_adders = (self.policy_module.get_supply_policy_adders()
                         - _baseline_adders)
        effective_tariffs = self.policy_module.get_effective_tariffs()

        # Trade scenario for market module
        trade_scenario = None
        # EU tariff-rate quota volumes (CAPRI's bilateral TRQs; KNOWN_ISSUES K52b): the scenario's change, none in
        # a baseline run; a commodity without an EU quota in CAPRI's data is refused rather than ignored
        _trq = {} if _is_base else dict(getattr(pol_scenario, "trq_volume_changes", None) or {})
        if _trq:
            _have = set(self.market_module.trq_commodities())
            _bad = sorted(c for c in _trq if c not in _have)
            if _bad:
                raise ValueError(f"trq_volume_changes for {_bad}: no EU tariff-rate quota in CAPRI's data "
                                 f"(quotas exist for {sorted(_have)})")
        self.market_module.trq_volume_changes = _trq
        if pol_scenario.tariff_changes:
            # {importing region: {commodity: points of ad valorem tariff}} (until 24 October 2026 the region was dropped
            # and every change landed on the EU's imports: audit M10)
            trade_scenario = {"tariff_change": {reg: dict(ch) for reg, ch in pol_scenario.tariff_changes.items()}}

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
        self.supply_module.yani_price_ratio_ms = None
        self.supply_module.yani_price_ratio_m = None
        self._yani_imbalance = 0.0
        self._yani_trace = []
        self._yani_w, self._yani_gprev = {}, {}
        self.market_module.seen.yani_state = None
        _yani_ref = (getattr(self, "_yani_ref", {}) or {}).get(_key)
        _yani_on = not _is_base and bool(_yani_ref)
        if _yani_on:
            self.supply_module.yani_price_ratio = {g: 1.0 for (_mr, g) in _yani_ref}

        # ---- Outer iteration loop ----
        tracker = ConvergenceTracker(
            tolerance=outer_tolerance, max_iter=max_outer_iter
        )

        # Initial price signal = world prices
        price_signal = pd.Series(0.0, index=self.data["world_prices"].index)
        supply_results = None
        market_eq = None

        outer_converged = False
        # IPOPT's tolerance in the regional models (outer_loop.nlp_tol_final)
        from capri_mod.supply.supply_module import RegionalSupplyModel as _RSMt
        _tol_tight = float(self.nlp_tol_final)
        self._nlp_tol_trace = []
        _lab = "baseline" if _is_base else str(getattr(pol_scenario, "name", scenario))
        self._progress(f"{_lab}: start (at most {max_outer_iter} iterations)")
        for outer_iter in range(max_outer_iter):
            self._outer_iter_now = outer_iter
            _t_it0 = time.time()
            if outer_iter == 0:
                # CAPRI's price forecast and stop rule start afresh every run (outer_loop.price_update, stop_rule)
                self._capri_yani_hist = {}
                self._capri_stop = None
            if self.verbose:
                print(f"  Outer iteration {outer_iter + 1}/{max_outer_iter}")
            _RSMt.nlp_tol = _tol_tight
            self._nlp_tol_trace.append(_RSMt.nlp_tol)

            # --- Step 1: Supply module ---
            if self.verbose:
                print("    [Supply] Solving regional models...")
            self.supply_module.__dict__.pop("_jrc_capped_cache", None)
            if outer_iter == 0:
                from capri_mod.supply.supply_module import RegionalSupplyModel as _RSM
                _on = bool(getattr(self, "use_manure_market", False))
                _RSM.use_fert_allocation = False      # substitution already in the balance
                _RSM.use_manure_pool = _on
                self.supply_module.manure_pool_price = {}     # fresh pools every run
                if _is_base:
                    # CAPRI calibrates its supply models in the baseline it simulates with (the base a first-order
                    # point of that model): each regional model checks at its first solve that its calibration was
                    # made on the same calibration problem, else calibrates again (found 26 October 2026: a
                    # calibration left by a supply module run on its own, without the model's rations and manure
                    # pools, was reused by DE11's mineral cap test)
                    for _m in self.supply_module._models.values():
                        _m._nlp_cal_check = True
                self._pool_state = None
                self._pool_accel = None
                self._pool_trace = []
                self._pool_imbalance = 0.0
            self._update_rations(price_signal if outer_iter > 0 else None)
            # CAPRI's raw milk price per member state (dairy block per RMS): the regional models get their member
            # state's milk price signal (relaxed like every price signal, below) as a departure from the EU's
            _ms_sig = getattr(self, "_milk_ms_signal", None) or {}
            self.supply_module.milk_price_dev_ms = (
                {ms: float(v) - float(price_signal.get("MILK", 0.0)) for ms, v in _ms_sig.items()}
                if outer_iter > 0 else {})
            # the milk price level each member state's models see, for the market's raw milk response (audit M5)
            _dpm = self.market_module._dairy_params() or {}
            _sm_ = float(price_signal.get("MILK", 0.0)) if price_signal is not None else 0.0
            self.market_module.seen.milk_seen_ms = {
                ms: 1.0 + _sm_ + float((self.supply_module.milk_price_dev_ms or {}).get(ms, 0.0))
                for ms in (_dpm.get("ms") or {})} if _dpm else None
            # CAPRI's two EU trade blocks (MarketModule.eu_blocks): each member state's models get their block's
            # prices, as the EU signal plus the block's departure from the EU average (relaxed like the signal)
            if outer_iter == 0:
                self._eu_dev = None
                self._sup_dev = None
            _dev = getattr(self, "_eu_dev", None) or {}
            _bmap = self.market_module._ms_block_map() if getattr(self.market_module, "eu_blocks", False) else {}
            self.supply_module.price_dev_ms = ({ms: _dev[rg] for ms, rg in _bmap.items() if rg in _dev}
                                               if (outer_iter > 0 and _dev) else {})
            # Norway (CAPRI market region NO000000 with supply models; KNOWN_ISSUES K56): its supply models get its own
            # market's prices, as the EU signal plus Norway's departure from it (relaxed like the signal)
            _sdev = getattr(self, "_sup_dev", None) or {}
            if outer_iter > 0 and _sdev:
                _smap = getattr(self.market_module, "SUP_NONEU_MS", {}) or {}
                self.supply_module.price_dev_ms = {**self.supply_module.price_dev_ms,
                                                   **{_smap[rg]: d for rg, d in _sdev.items() if rg in _smap}}
            # CAPRI's slower smoothing for a member state's problem products (outer_loop.capri_step_special)
            _sdm = getattr(self, "_special_ms_dev", None) or {}
            if outer_iter > 0 and _sdm:
                _pdm = dict(self.supply_module.price_dev_ms or {})
                for _ms_s, _d_s in _sdm.items():
                    _base_s = _pdm.get(_ms_s)
                    _base_s = (pd.Series(0.0, index=price_signal.index) if _base_s is None
                               else _base_s.reindex(price_signal.index).fillna(0.0))
                    _pdm[_ms_s] = _base_s.add(pd.Series(_d_s).reindex(price_signal.index).fillna(0.0))
                self.supply_module.price_dev_ms = _pdm
            elif outer_iter == 0:
                self._special_ms_dev = {}
            _spol = {
                    "adders": policy_adders.to_dict(),
                    # premium factors by region and activity (a CAPRI premium experiment)
                    "premium_factor_regional": self.policy_module.get_premium_factors_regional(),
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
                    "surplus_cut": float(pol_scenario.surplus_cut),
                    # CAPRI's mineral fertiliser reduction (mineRedu): "20" UAA-wide, "NNcrp" by crop group
                    "mineral_redu": str(getattr(pol_scenario, "mineral_redu", "00") or "00"),
                    # yield effect of the pesticide target: "jrc121368" (10% at a 50% cut) or "star3" (none)
                    "pesticide_rule": str(getattr(pol_scenario, "pesticide_rule", "jrc121368") or "jrc121368"),
                    # Farm-to-Fork pesticide target (CAPRI conventional_io.gms): plant-protection and other-input
                    # changes, catch crops and, under the jrc121368 rule, a yield loss
                    "pesticide_reduction": float(
                        getattr(pol_scenario, "pesticide_reduction", 0.0) or 0.0),
                    "organic_area_target": float(
                        getattr(pol_scenario, "organic_area_target", 0.0) or 0.0),
                }
            supply_results = self.supply_module.run(
                price_signals=price_signal if outer_iter > 0 else None,
                policy_scenario=_spol,
                regions=regions or list(self.data["areas"].index),
                verbose=self.verbose,
            )
            self._last_spol = _spol
            self._last_supply_results = supply_results   # fodder shadow prices for the rations
            _t_sup = time.time()
            # CAPRI's baseline calibration (CAPMOD calibrates its supply models so that the simulation year's baseline
            # reproduces the projected levels): in the baseline of a projected year, the regional models' linear terms
            # are corrected until their solution is the projection's levels (Sprint 9p); the scenario then starts
            # from that calibrated baseline, as CAPRI's do
            self._calib_drift = 0.0
            if (_is_base and isinstance(self.data, dict) and self.data.get("market_year")
                    and self.data.get("calibrate_baseline", True)):
                self._calib_drift = self.supply_module.calibrate_to_base(supply_results, reset=(outer_iter == 0))
                self._calib_trace = getattr(self, "_calib_trace", []) if outer_iter else []
                self._calib_trace.append(round(float(self._calib_drift), 5))
            # the market supply Hessian measured again at the scenario's state (market.hessian_scenario_iter; the
            # user's choice 2(b), 25 October 2026, K75): the baseline's responses can differ from the scenario's (the
            # calf market of the Farm-to-Fork runs responded with 0-10% of the baseline's own response). CAPRI
            # measures it once per baseline (DEPARTURE)
            _hk = int(_settings().get("market.hessian_scenario_iter") or 0)
            if (not _is_base and _hk > 0 and outer_iter + 1 == _hk and bool(getattr(self, "market_supply_nq", True))
                    and self.market_module.par.supply_hessian):
                try:
                    self._hessian_at_scenario = True
                    self.market_module.par.supply_hessian = self._market_supply_hessian(price_signal, supply_results,
                                                                                    regions)
                    self.market_supply_hessian_info = dict(self.market_supply_hessian_info, at_iteration=outer_iter + 1)
                    self.market_supply_hessian_log[-1] = dict(self.market_supply_hessian_info)
                except Exception as _exc:
                    warnings.warn(f"scenario market supply Hessian not measured ({_exc!r}); the baseline's kept",
                                  RuntimeWarning, stacklevel=2)
                    self.market_supply_hessian_info = dict(self.market_supply_hessian_info or {},
                                                           scenario_error=repr(_exc), at_iteration=outer_iter + 1)
                finally:
                    self._hessian_at_scenario = False
            _yani_mkt = _yani_on and self._yani_in_market_now()
            if _yani_on and not _yani_mkt:
                self._update_young_animal_prices(supply_results, _yani_ref)
            elif _yani_mkt:
                # CAPRI's yaniMarket_: the young-animal markets clear inside the market, with the products (the market's
                # supply functions, recalibrated to this solution); the prices come back after the market solve
                self._young_animal_state_to_market(supply_results, _yani_ref)
            else:
                self.market_module.seen.yani_state = None

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
            self.market_module.seen.eu_price_seen = (1.0 + price_signal).reindex(
                self.market_module.commodities).fillna(1.0)
            if getattr(self.market_module, "eu_blocks", False):
                _dv = getattr(self, "_eu_dev", None) or {}
                _cm = self.market_module.commodities
                self.market_module.seen.eu_price_seen = pd.DataFrame(
                    {rg: (1.0 + price_signal + _dv.get(rg, 0.0)).reindex(_cm).fillna(1.0)
                     for rg in self.market_module.EU}).T
            # Norway's supply models saw Norway's prices (K56)
            _sdv = getattr(self, "_sup_dev", None) or {}
            self.market_module.seen.sup_price_seen = {
                rg: (1.0 + price_signal + (_sdv[rg].reindex(price_signal.index).fillna(0.0) if rg in _sdv else 0.0)
                     ).reindex(self.market_module.commodities).fillna(1.0)
                for rg in getattr(self.market_module, "SUP", ())}
            # FEED DEMAND FOLLOWS HERDS: EU feed use of each feed cereal from
            # this iteration's herds x the feed table, relative to base.
            self._set_feed_demand(supply_results)
            if getattr(self, "use_manure_market", False):
                self._update_manure_pools()
            _t_mk0 = time.time()
            market_eq = self.market_module.solve(
                exogenous_supply=eu_supply_market,
                trade_scenario=trade_scenario,
                max_iter=market_max_iter,
                verbose=self.verbose,
            )
            _t_mk1 = time.time()
            if _yani_mkt:
                self._young_animal_prices_from_market(_yani_ref)

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
                _st_ = _settings()
                _w = _w.where(~_flip, (_w * _st_.get("outer_loop.relax_step_down")).clip(lower=_st_.get("outer_loop.relax_floor")))
                _w = _w.where(_flip, (_w * _st_.get("outer_loop.relax_step_up")).clip(upper=self.PRICE_SIGNAL_RELAXATION))
            self._relax_w, self._relax_gprev = _w, _g
            if self._capri_price_update():
                # CAPRI's price forecast on the market's prices of the last steps (outer_loop.price_update)
                _th = (getattr(self, "_capri_target_hist", None) or []) if outer_iter > 0 else []
                _th = (_th + [_target.reindex(price_signal.index).fillna(0.0)])[-4:]
                self._capri_target_hist = _th
                _ps_new = self._capri_forecast(_th, outer_iter)
                _w = pd.Series(1.0, index=price_signal.index)          # the step the blocks and Norway take below
                _g = _ps_new - price_signal
                self._relax_w = _w
                price_signal = _ps_new
            else:
                price_signal = price_signal + _w * _g
            # EU trade blocks: each block's target departure from the EU target, relaxed with the same step
            self._eu_dev_gap = 0.0
            _mmk = self.market_module
            if getattr(_mmk, "eu_blocks", False) and getattr(_mmk, "eu_premium_reg", None) is not None:
                _wr = new_prices / base_prices.clip(lower=1.0)
                _dev0 = getattr(self, "_eu_dev", None) or {}
                _newdev = {}
                for _rg in _mmk.EU:
                    _tr = _wr * _mmk.eu_premium_reg.loc[_rg].reindex(new_prices.index).fillna(1.0) - 1.0
                    if "SUGR" in _tr.index:
                        _tr["SUGB"] = float(_tr["SUGR"])
                    if "SWHE" in _tr.index:
                        _tr["DWHE"] = float(_tr["SWHE"])
                    _dt = (_tr - _target).reindex(price_signal.index).fillna(0.0)
                    for _c in ("MILK", "DCOW"):                 # raw milk: priced per member state (dairy blocks)
                        if _c in _dt.index:
                            _dt[_c] = 0.0
                    self.__dict__.setdefault("_blockdev_target_now", {})[_rg] = _dt
                    _d0 = _dev0.get(_rg)
                    _d0 = pd.Series(0.0, index=price_signal.index) if _d0 is None else _d0.reindex(price_signal.index).fillna(0.0)
                    if self._capri_price_update():
                        _bh = (getattr(self, "_capri_blockdev_hist", None) or {}) if outer_iter > 0 else {}
                        _bh[_rg] = ((_bh.get(_rg) or []) + [_dt])[-4:]
                        self._capri_blockdev_hist = _bh
                        _newdev[_rg] = self._capri_forecast(_bh[_rg], outer_iter)
                    else:
                        _newdev[_rg] = _d0 + _w * (_dt - _d0)
                    self._eu_dev_gap = max(self._eu_dev_gap, float((_dt - _d0).abs().max()))
                self._eu_dev = _newdev
            # CAPRI's slower smoothing for problem products of a member state (outer_loop.capri_step_special;
            # define_stepWeights.gms, price_forecast.gms l. 384-386): CAPRI smooths the price it passes to that member
            # state's supply models (DATA(MS, "UVAG", product, "Y")); here the member state's models get the smoothed
            # price as a departure from the price the others in its market see (applied with price_dev_ms next
            # iteration). The member state's market price each step: the EU target plus its block's departure
            self._special_ms_dev = {}
            _spm = {k_: v_ for k_, v_ in self._capri_step_special().items() if k_[1] != "MILK" and _is_eu(k_[0])}
            if _spm and self._capri_price_update():
                _hs = (getattr(self, "_capri_special_hist", None) or {}) if outer_iter > 0 else {}
                _bmap_s = (self.market_module._ms_block_map()
                           if getattr(self.market_module, "eu_blocks", False) else {})
                _bdt = getattr(self, "_blockdev_target_now", None) or {}
                _edv = getattr(self, "_eu_dev", None) or {}
                for (_ms_s, _p_s), _srt in _spm.items():
                    if _p_s not in price_signal.index:
                        raise ValueError(f"outer_loop.capri_step_special: {_p_s!r} has no price signal")
                    _rg_s = _bmap_s.get(_ms_s)
                    _tg = float(_target.get(_p_s, 0.0)) + (float(_bdt[_rg_s].get(_p_s, 0.0)) if _rg_s in _bdt else 0.0)
                    _hs[(_ms_s, _p_s)] = (_hs.get((_ms_s, _p_s)) or []) + [_tg]
                    _seen = float(price_signal[_p_s]) + (float(_edv[_rg_s].get(_p_s, 0.0)) if _rg_s in _edv else 0.0)
                    _d_s = float(self._capri_special_forecast(_hs[(_ms_s, _p_s)], _srt)) - _seen
                    _dd = self._special_ms_dev.setdefault(_ms_s, {})
                    _dd[_p_s] = _d_s
                    for _a_s, _c_s in (("SUGB", "SUGR"), ("DWHE", "SWHE")):   # beet follows sugar, durum wheat
                        if _p_s == _c_s and _a_s in price_signal.index:
                            _dd[_a_s] = _d_s
                self._capri_special_hist = _hs
            # NORWAY (CAPRI RMSSUP outside the EU, its own market region NOR; K56): its supply models see its own market's
            # producer prices (raw milk: its dairy block's), relaxed as a price level of their own, as the member states'
            # milk prices above. A departure from the EU signal relaxed toward a departure from the EU target (the first
            # form) dragged Norway's prices along with every move of the EU signal: on a subset run the EU's other-cereal
            # and oat targets crept up 0.003 per iteration, and Norway's cereals lagged 1-2% behind their own,
            # nearly flat, prices for ten iterations. The level is passed on as a departure from the new EU signal.
            self._sup_dev_gap = 0.0
            _spr = getattr(_mmk, "sup_price_ratio", None)
            if _spr is not None and len(_spr):
                _sd0 = getattr(self, "_sup_dev", None) or {}
                _nsd = {}
                _ps_old = price_signal - _w * _g                 # the EU signal this iteration's supply models saw
                _wn_all = getattr(self, "_sup_w", None)
                if _wn_all is None or outer_iter == 0:
                    _wn_all = {}; self._sup_gprev = {}
                for _rg in _spr.index:
                    _tn = (_spr.loc[_rg].astype(float) - 1.0).reindex(price_signal.index)
                    if "SUGR" in _tn.index and "SUGB" in _tn.index:
                        _tn["SUGB"] = float(_tn["SUGR"])
                    if "SWHE" in _tn.index and "DWHE" in _tn.index:
                        _tn["DWHE"] = float(_tn["SWHE"])
                    if "MILK" in _tn.index and "DCOW" in _tn.index:
                        _tn["DCOW"] = float(_tn["MILK"])
                    _d0 = _sd0.get(_rg)
                    _d0 = pd.Series(0.0, index=price_signal.index) if _d0 is None else _d0.reindex(price_signal.index).fillna(0.0)
                    _s0 = _ps_old + _d0                          # the price level Norway's models saw
                    _has = _tn.notna()                           # no market price of its own: the EU signal
                    _step = (_tn - _s0).where(_has, 0.0)
                    # adaptive step per product, as the EU signal's: halved when the step's direction flips (floor
                    # 0.1), recovering otherwise
                    _wn = _wn_all.get(_rg)
                    _gp_ = self._sup_gprev.get(_rg)
                    if _wn is None:
                        _wn = pd.Series(self.PRICE_SIGNAL_RELAXATION, index=price_signal.index)
                    elif _gp_ is not None:
                        _fl = (_step * _gp_.reindex(_step.index).fillna(0.0)) < 0
                        _wn = _wn.reindex(_step.index).fillna(self.PRICE_SIGNAL_RELAXATION)
                        _stn = _settings()                     # the EU signal's adaptive step, same settings
                        _wn = _wn.where(~_fl, (_wn * _stn.get("outer_loop.relax_step_down"))
                                        .clip(lower=_stn.get("outer_loop.relax_floor")))
                        _wn = _wn.where(_fl, (_wn * _stn.get("outer_loop.relax_step_up"))
                                        .clip(upper=self.PRICE_SIGNAL_RELAXATION))
                    _wn_all[_rg] = _wn
                    self._sup_gprev[_rg] = _step
                    _s1 = _s0 + _wn.reindex(_step.index).fillna(self.PRICE_SIGNAL_RELAXATION) * _step
                    if self._capri_price_update():
                        # CAPRI's price forecast on Norway's market prices (where it has none: the EU signal)
                        _nh = (getattr(self, "_capri_sup_hist", None) or {}) if outer_iter > 0 else {}
                        _nh[_rg] = ((_nh.get(_rg) or []) + [_tn.where(_has, price_signal)])[-4:]
                        self._capri_sup_hist = _nh
                        _s1 = self._capri_forecast(_nh[_rg], outer_iter).where(_has, price_signal)
                        # CAPRI's slower smoothing for problem products (outer_loop.capri_step_special, NO000000)
                        _nf = (getattr(self, "_capri_sup_full", None) or {}) if outer_iter > 0 else {}
                        _nf[_rg] = (_nf.get(_rg) or []) + [_tn.where(_has, price_signal)]
                        self._capri_sup_full = _nf
                        _ms_rg = (getattr(_mmk, "SUP_NONEU_MS", {}) or {}).get(_rg)
                        for (_rg_s, _p_s), _srt in self._capri_step_special().items():
                            if _rg_s == _ms_rg and _p_s in _s1.index and bool(_has.get(_p_s, False)):
                                _s1[_p_s] = float(self._capri_special_forecast([float(x_[_p_s]) for x_ in _nf[_rg]], _srt))
                    _nsd[_rg] = (_s1 - price_signal).where(_has, 0.0)
                    # the gap over the products the region produces, CAPRI's filter (SUP_GAP_MIN_PROD, 5 kt at base):
                    # Norway's producer prices of products it does not produce (maize, wine, olive oil, tobacco) swung
                    # by 13-75% between iterations (r54, r56, r58), its other cereals (about 2.6 kt) by 1-5% (r62)
                    _bp = _mmk.par.base_production.loc[_rg] if _rg in _mmk.par.base_production.index else None
                    _own = [c_ for c_ in _step.index if _bp is not None and c_ in _bp.index
                            and float(_bp[c_]) > self.SUP_GAP_MIN_PROD]
                    _own += [a_ for a_, c_ in (("SUGB", "SUGR"), ("DWHE", "SWHE"), ("DCOW", "MILK")) if c_ in _own]
                    _gs = _step.reindex(_own).abs() if _own else _step.abs()
                    if len(_gs) and float(_gs.max()) > self._sup_dev_gap:
                        self._sup_dev_gap = float(_gs.max()); self._sup_dev_worst = (_rg, str(_gs.idxmax()))
                    _ga = _step.abs()
                    self._sup_dev_gap_all = (float(_ga.max()), str(_ga.idxmax())) if len(_ga) else (0.0, "")
                self._sup_w = _wn_all
                self._sup_dev = _nsd
            # member-state raw milk prices (dairy block per RMS): target = the member state's milk price relative to
            # the EU's, applied to the EU target; relaxed with the same adaptive step, per member state
            _dl = self.market_module.ev.dairy_last if self.market_module._dairy_params() else None
            _ms_gap = _ms_small_gap = 0.0
            if _dl and _dl.get("ms_price_ratio") and "MILK" in _target.index:
                _eu = float(_dl["price_ratio"]["MILK"]) or 1.0
                _sig = getattr(self, "_milk_ms_signal", None) or {}
                _mw = getattr(self, "_milk_ms_w", None) or {}
                _mg = getattr(self, "_milk_ms_gprev", None) or {}
                _mh = getattr(self, "_milk_ms_hist", None) or {}
                if outer_iter == 0:
                    _sig, _mw, _mg, _mh = {}, {}, {}, {}
                for _ms, _v in _dl["ms_price_ratio"].items():
                    _t = (float(_v["MILK"]) / _eu) * (1.0 + float(_target["MILK"])) - 1.0
                    _s0 = _sig.get(_ms, float(price_signal.get("MILK", 0.0)) - float(_w.get("MILK", 0.0)) * float(_g.get("MILK", 0.0)))
                    _gg = _t - _s0
                    _ww = _mw.get(_ms, self.PRICE_SIGNAL_RELAXATION)
                    if _ms in _mg:
                        # floor 0.02 (prices 0.1): a member state's dairies set its milk price alone, and in a small
                        # one under a binding N target (Cyprus) milk price and herd fed back on each other in a
                        # cobweb at the 0.1 floor
                        _st_ = _settings()
                        _ww = (max(_st_.get("outer_loop.milk_ms_relax_floor"), _ww * _st_.get("outer_loop.relax_step_down"))
                               if _gg * _mg[_ms] < 0
                               else min(self.PRICE_SIGNAL_RELAXATION, _ww * _st_.get("outer_loop.relax_step_up")))
                    if self._capri_price_update():
                        # CAPRI's price forecast (capmod/define_stepWeights.gms, price_forecast.gms): the price passed on
                        # is the weighted average of the prices simulated in the last iterations, 0.55 / 0.30 / 0.15
                        # (0.4 / 0.3 / 0.2 / 0.1 from the 20th iteration), normalised over those available. A member
                        # state's dairy block is a thin market: with the adaptive step its milk price could cycle
                        # between two states (Portugal, Green Deal 2030, 21 October 2026: gap 0.005 / 0.03 alternating).
                        # Tried as the default in a full Green Deal 2030 run (r73, 21 October 2026): Spain's milk
                        # signal swung between +0.32 and -0.21 and its gap was still 0.34 at the 9th iteration (0.03 at
                        # the 6th with the adaptive step, r71). The weights average past market prices that themselves
                        # swing with the herd (a cobweb the weights do not damp); the adaptive step halves its weight
                        # on every reversal (KNOWN_ISSUES K62). Since the K75 fix CAPRI's forecast is the default
                        # for every price (outer_loop.price_update "capri")
                        _h = (_mh.get(_ms) or []) + [_t]
                        _mh[_ms] = _h[-4:]
                        _st_ = _settings()
                        _wts = tuple(_st_.get("outer_loop.capri_step_weights")
                                     if outer_iter + 1 < int(_st_.get("outer_loop.capri_step_weights_late_from"))
                                     else _st_.get("outer_loop.capri_step_weights_late"))
                        _use = list(reversed(_h))[:len(_wts)]
                        _sig[_ms] = sum(w_ * v_ for w_, v_ in zip(_wts, _use)) / sum(_wts[:len(_use)])
                        # CAPRI's slower smoothing for problem products (outer_loop.capri_step_special, the member
                        # state's MILK): over every step and the baseline
                        _mf = self.__dict__.setdefault("_milk_ms_full", {})
                        if outer_iter == 0:
                            _mf.pop(_ms, None)
                        _mf[_ms] = (_mf.get(_ms) or []) + [_t]
                        _srt = self._capri_step_special().get((_ms, "MILK"))
                        if _srt:
                            _sig[_ms] = float(self._capri_special_forecast(_mf[_ms], _srt))
                    else:
                        _sig[_ms] = _s0 + _ww * _gg
                    _mw[_ms], _mg[_ms] = _ww, _gg
                    # convergence on the member states with at least 1% of EU milk: in Cyprus (0.2%) the herd's
                    # response to the milk price is discontinuous under its binding N target (the regional N price
                    # loop), and its milk price circles within a band without settling; it is reported, not held
                    _sh = float((self.market_module._dairy_params().get("ms", {}).get(_ms) or {}).get("Q0", [0])[
                        (self.market_module._dairy_params().get("ms", {}).get(_ms) or {}).get("iM", 0)]) if _ms in \
                        self.market_module._dairy_params().get("ms", {}) else 0.0
                    _tot = float(self.market_module._dairy_params()["Q0"][self.market_module._dairy_params()["iM"]])
                    _mms = float(_settings().get("outer_loop.milk_ms_min_share"))
                    if abs(_gg) > _ms_gap and _sh >= _mms * _tot:
                        self._milk_ms_worst = (_ms, _s0, _t, _ww, float(_v["milk_delivered"]))
                    if _sh >= _mms * _tot:
                        _ms_gap = max(_ms_gap, abs(_gg))
                    else:
                        _ms_small_gap = max(_ms_small_gap, abs(_gg))
                self._milk_ms_signal, self._milk_ms_w, self._milk_ms_gprev = _sig, _mw, _mg
                self._milk_ms_hist = _mh
            self._milk_ms_small_gap = _ms_small_gap

            # Aggregate quantities for convergence
            agg_qty = eu_supply_market.sum() if eu_supply_market is not None \
                      else pd.Series(dtype=float)

            tracker.record(outer_iter, new_prices, agg_qty)
            try:
                # diagnostics: the outer loop's state per iteration (signals, targets, young-animal prices, member
                # states' milk, EU herds), kept in the results as outer_history (KNOWN_ISSUES K75)
                _hist = getattr(self, "_outer_history", None)
                if outer_iter == 0 or _hist is None:
                    _hist = []
                _sr_ = supply_results or {}
                _herd = {a_: float(sum(float(getattr(x_, "activities", pd.Series(dtype=float)).get(a_, 0.0))
                                       for r_, x_ in _sr_.items() if _is_eu(r_)))
                         for a_ in ("DCOW", "BCOW", "BULL", "HFRS", "CALV", "PIGF", "PIGS", "BROI", "LAYS", "SHGM", "SHGF")}
                _dlh = self.market_module.ev.dairy_last or {}
                _hist.append({"it": outer_iter + 1,
                              "signal": price_signal.astype(float).to_dict(),
                              "target": _target.astype(float).to_dict(),
                              "yani_ratio": {k_: dict(v_) for k_, v_ in (getattr(self.supply_module, "yani_price_ratio_m", None) or {}).items()},
                              "yani_imbalance": float(getattr(self, "_yani_imbalance", 0.0) or 0.0),
                              "milk_ms_signal": dict(getattr(self, "_milk_ms_signal", None) or {}),
                              "yani_state": __import__("copy").deepcopy(self.market_module.seen.yani_state),
                              "yani_market": __import__("copy").deepcopy(self.market_module.ev.yani_market_now),
                              "milk_ms": {k_: {kk: float(vv) for kk, vv in v_.items()} for k_, v_ in (_dlh.get("ms_price_ratio") or {}).items()},
                              "herd": _herd,
                              "herd_regional": {r_: {a_: round(float(getattr(x_, "activities", pd.Series(dtype=float)).get(a_, 0.0)), 4)
                                                     for a_ in ("BCOW", "DCOW", "CALV", "BULL", "HFRS", "GRAS", "MAIF", "OFOD")}
                                                for r_, x_ in _sr_.items()}})
                # the regions whose jump check acted at this iteration (supply.nlp_jump_check, K79): the largest move, the
                # starts solved, the one kept and the objectives
                _hist[-1]["jump_check"] = {r_: dict(m_._nlp_jump) for r_, m_ in
                                           (getattr(self.supply_module, "_models", None) or {}).items()
                                           if getattr(m_, "_nlp_jump", None)}
                if _settings().get("diagnostics.record_regional_levels"):
                    # every region's activity levels at this iteration, unrounded (K79: the rows CAPRI's stop rule
                    # flags, traced to regions and activities)
                    _hist[-1]["act_regional"] = {r_: {str(a_): float(v_) for a_, v_ in
                                                      getattr(x_, "activities", pd.Series(dtype=float)).items()}
                                                 for r_, x_ in _sr_.items()}
                    # each region's solve: the starts tried / IPOPT's iterations of the last, its objective, its
                    # relaxation (K79: a region jumping between two states)
                    _hist[-1]["nlp_regional"] = {
                        r_: {"path": getattr(m_, "_nlp_path", None), "f": getattr(m_, "_nlp_prev_f", None),
                             "relaxed": getattr(m_, "_nlp_relaxed", None)}
                        for r_, m_ in (getattr(self.supply_module, "_models", None) or {}).items()}
                self._outer_history = _hist
            except Exception as _e:
                warnings.warn(f"outer history not recorded: {_e!r}")
            if self.verbose or _settings().get("diagnostics.trace_outer"):
                try:
                    _dv = (new_prices / base_prices.clip(lower=1.0) - 1.0)
                    _pr = getattr(self.market_module, 'eu_premium', None)
                    _prev = getattr(self, '_trace_prev_prem', None)
                    _top = ''
                    if _pr is not None and _prev is not None:
                        _d = (_pr - _prev.reindex(_pr.index).fillna(1.0)).abs().sort_values(ascending=False).head(3)
                        _top = ' | premium swing: ' + ', '.join(f'{k} {float(_pr[k]):.3f} ({v:+.3f})' for k, v in _d.items())
                    self._trace_prev_prem = _pr.copy() if _pr is not None else None
                    _lu = float(getattr(self.supply_module, 'max_nbal_update', 0.0) or 0.0)
                    _yv = float(getattr(self, '_yani_imbalance', 0.0) or 0.0)
                    _gp = (_target.reindex(price_signal.index).fillna(0.0) - price_signal).abs()
                    _lr = getattr(self.supply_module, 'max_nbal_region', None) if _lu > 1e-3 else None
                    print(f'  [outer {outer_iter + 1}] world max {_dv.abs().idxmax()} {float(_dv.abs().max()):.4f} | N price update {_lu:.5f}'
                          f'{" (%s, %s)" % _lr if _lr else ""} | milk MS gap {_ms_gap:.4f}'
                          f'{" %s s %.3f t %.3f w %.2f q %.3f" % getattr(self, "_milk_ms_worst") if _ms_gap > 0.005 and getattr(self, "_milk_ms_worst", None) else ""}'
                          f' | gap {_gp.idxmax()} {float(_gp.max()):.4f} | yani {_yv:.4f}'
                          f' | NOR gap {float(getattr(self, "_sup_dev_gap", 0.0) or 0.0):.4f} {getattr(self, "_sup_dev_worst", ("", ""))[1]} (all {getattr(self, "_sup_dev_gap_all", (0.0, ""))[0]:.4f} {getattr(self, "_sup_dev_gap_all", (0.0, ""))[1]})'
                          f'{" | pool %.4f %s eu %.4f" % (float(getattr(self, "_pool_imbalance", 0.0) or 0.0), getattr(self, "_pool_worst_key", "") + ("" if str(getattr(self, "_pool_solver_status", "Solved")).endswith("Solved") else " [" + str(getattr(self, "_pool_solver_status", "")) + "]"), float(getattr(self, "_pool_eu_unaccounted", 0.0) or 0.0)) if getattr(self, "use_manure_market", False) else ""}{" | base cal %.4f" % float(getattr(self, "_calib_drift", 0.0) or 0.0) if getattr(self, "_calib_drift", 0.0) else ""}{_top}', flush=True)
                except Exception:
                    pass
                try:
                    # the commodity holding the largest signal gap: EU supply, world ratio, EU premium and the
                    # market's EU balance (diagnostics only)
                    _gc = str(_gp.idxmax())
                    _mc = {"SUGB": "SUGR", "DWHE": "SWHE"}.get(_gc, _gc)
                    _bal = ""
                    if market_eq is not None and _mc in market_eq.production.columns:
                        _eu_ = [r for r in self.market_module.EU if r in market_eq.production.index]
                        _bal = (f" | market EU prod {float(market_eq.production.loc[_eu_, _mc].sum()):.1f}"
                                f" cons {float(market_eq.consumption.loc[_eu_, _mc].sum()):.1f}"
                                f" netexp {float(market_eq.net_exports.loc[_eu_, _mc].sum()):.1f}"
                                f" | BIOE EU cons {float(market_eq.consumption.loc[_eu_, 'BIOE'].sum()) if 'BIOE' in market_eq.consumption.columns else float('nan'):.1f}"
                                f" | excess {float(market_eq.excess_demand.get(_mc, float('nan'))):.3g} conv {market_eq.converged}")
                    # the regions whose gross output of the gap's activity changed most since the last iteration
                    _sr = getattr(self, "_last_supply_results", None) or {}
                    _go = {r_: float(getattr(x_, "gross_output", pd.Series(dtype=float)).get(_gc, 0.0)) for r_, x_ in _sr.items()}
                    _lv = {r_: float(x_.activities.get(_gc, 0.0)) for r_, x_ in _sr.items()}
                    _gprev = getattr(self, "_trace_go_prev", None) or {}
                    if _gprev:
                        _dd = sorted(((abs(_go[r_] - _gprev.get(r_, 0.0)), r_) for r_ in _go), reverse=True)[:5]
                        print(f'    [gap {_gc} output] EU {sum(_go.values()):.1f} (prev {sum(_gprev.values()):.1f}) | '
                              + ', '.join(f'{r_} {_gprev.get(r_, 0.0):.1f}->{_go[r_]:.1f} (lvl {_lv.get(r_, float("nan")):.2f})'
                                          for _, r_ in _dd), flush=True)
                    self._trace_go_prev = _go
                    print(f'    [gap {_gc}->{_mc}] EU supply {float(agg_qty.get(_mc, float("nan"))):.1f}'
                          f' (beet {float(agg_qty.get("SUGB", float("nan"))):.1f}) | world ratio {float((_dv + 1.0).get(_mc, float("nan"))):.4f}'
                          f' | premium {float(_pr.get(_mc, float("nan"))) if _pr is not None else float("nan"):.4f}'
                          f' | signal {float(price_signal.get(_gc, float("nan"))):.4f} target {float(_target.get(_gc, float("nan"))):.4f}{_bal}', flush=True)
                except Exception as _e:
                    print(f'    [gap trace failed: {_e}]', flush=True)
                try:
                    self._trace_nlp_regions()
                except Exception:
                    pass

            # Damped steps are small by design, so small successive price
            # changes alone could signal a false convergence. Also require the
            # signal to have reached the target it is being relaxed toward.
            _gap = float((_target.reindex(price_signal.index).fillna(0.0)
                          - price_signal).abs().max())
            # Norway out of the test from CAPRI's 15th iteration on (SUP_GAP_LAST_ITER)
            _sup_gap_t = (float(getattr(self, "_sup_dev_gap", 0.0) or 0.0)
                          if outer_iter + 1 < self.SUP_GAP_LAST_ITER else 0.0)
            _gap = max(_gap, _ms_gap, float(getattr(self, "_eu_dev_gap", 0.0) or 0.0), _sup_gap_t)
            # each region's nitrogen-balance price settles with prices: do not stop while it moves
            _nbal = float(getattr(self.supply_module, "max_nbal_update", 0.0) or 0.0)
            _pool = float(getattr(self, "_pool_imbalance", 0.0) or 0.0)
            _pool_tol = float(self.manure_pool_tolerance)
            _yani = float(getattr(self, "_yani_imbalance", 0.0) or 0.0)
            _cal = float(getattr(self, "_calib_drift", 0.0) or 0.0)
            # CAPRI's stop rule, every iteration (recorded; it decides with outer_loop.stop_rule = "capri")
            try:
                _cv = self._capri_stop_step(supply_results, market_eq)
            except Exception as _exc:
                warnings.warn(f"CAPRI's stop rule not evaluated ({_exc!r})", RuntimeWarning, stacklevel=2)
                _cv = None
            self._capri_stop_verdict = _cv
            try:
                # the convergence tests of this iteration, for the outer history (K75)
                if getattr(self, "_outer_history", None):
                    self._outer_history[-1]["conv"] = {
                        "tracker": bool(tracker.check_convergence()), "last_change": float(tracker.last_change()),
                        "gap": _gap, "ms_gap": float(_ms_gap), "nbal": _nbal, "pool": _pool, "yani": _yani, "cal": _cal,
                        "capri": ({k_: _cv[k_] for k_ in ("max", "cur", "count", "go_on", "top")} if _cv else None)}
            except Exception:
                pass
            _own_ok = (outer_iter > 0 and tracker.check_convergence() and _gap < self.SUPPLY_GAP_TOL
                       and _nbal < self.NBAL_UPDATE_TOL and _pool < _pool_tol and _yani < self.YANI_TOL
                       and _cal < self.BASE_CAL_TOL)
            if str(_settings().get("outer_loop.stop_rule")) == "capri":
                # CAPRI's rule decides on prices and quantities (capmod.gms l. 1369); this model's price and supply-gap
                # tests are still recorded above. The model's inner balances (each region's N-balance price, the
                # manure pools, the young-animal markets, the base calibration) must have settled as well: CAPRI
                # solves them inside each step's simultaneous system, so a CAPRI step always has them closed
                _own_ok = bool(_cv is not None and outer_iter > 0 and not _cv["go_on"]
                               and _nbal < self.NBAL_UPDATE_TOL and _pool < _pool_tol and _yani < self.YANI_TOL
                               and _cal < self.BASE_CAL_TOL)
            _t_it1 = time.time()
            self._progress(
                f"{_lab} iteration {outer_iter + 1}: supply models {_t_sup - _t_it0:.0f} s, between "
                f"{_t_mk0 - _t_sup:.0f} s, market {_t_mk1 - _t_mk0:.0f} s, stop tests {_t_it1 - _t_mk1:.0f} s; "
                f"iteration {_t_it1 - _t_it0:.0f} s"
                + (f" | CAPRI: {_cv['count']} rows above 0.05%, largest {_cv['max']:.3f}%"
                   + (f" ({_cv['top'][0][0]} {_cv['top'][0][1]})" if _cv.get('top') else "") if _cv else "")
                + f" | N-balance price {_nbal:.2e}, pools {_pool:.2e}, young animals {_yani:.2e}, calibration {_cal:.2e}"
                + (" -> stop" if _own_ok else ""))
            if _own_ok:
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
        # Not CAPRI's (a report, the project lead's decision): items still moving one way when the loop ended
        # (outer_loop.drift_report_steps; CapriStopRule.drift)
        self._capri_drift = []
        _nd = int(_settings().get("outer_loop.drift_report_steps") or 0)
        if _nd > 0 and getattr(self, "_capri_stop", None) is not None:
            self._capri_drift = self._capri_stop.drift(_nd)
            if self._capri_drift:
                _top = "; ".join(f"{e['row']} {e['where']} ({e['kind']}) {e['changes'][-1]:+.3f}%"
                                 + (f", about {e['to_come']:.2f}% to come" if e["to_come"] is not None else ", not shrinking")
                                 for e in self._capri_drift[:5])
                self._progress(f"{_lab}: {len(self._capri_drift)} item(s) still moving one way for {_nd} iterations "
                               f"at the end: {_top}")
                if outer_converged:
                    warnings.warn(f"{_lab}: the loop stopped with {len(self._capri_drift)} item(s) still moving one way "
                                  f"for {_nd} iterations ({_top}); CAPRI's rule allows it (two rows or fewer above "
                                  "0.05%), their results are not at their equilibrium yet: metadata capri_stop drift",
                                  RuntimeWarning, stacklevel=2)
        _RSMt.nlp_tol = _tol_tight                # later solves outside the loop at the tight tolerance

        # CAPRI's market supply functions calibrated to the supply models (supply/calibrate_supply.gms:193-508): at the
        # converged baseline each product's price is raised by 1% in every regional model, and the member states'
        # responses form the Hessian of the market's normalised-quadratic supply (dQ / d relative price). The scenario
        # keeps it (CAPRI loads it in simulations, arm/market1.gms:505-674); the market moves the function through the
        # supply models' latest output every iteration (arm/simu_calibration_to_supply.gms:360-368).
        # Measured when a scenario needs it (28 October 2026, the project lead's decision), as CAPRI's calibrate_supply
        # is a task of its own after the baseline: the baseline records what the measurement needs, and the next run, if
        # it is a scenario on this baseline, measures it (or reads it from the cache) before it changes anything. A
        # baseline run alone (tests that check a baseline) does not measure it.
        if _is_base and supply_results and bool(getattr(self, "market_supply_nq", True)) and market_eq is not None:
            self._hessian_pending = {"key": _key, "price_signal": price_signal.copy(), "supply_results": supply_results,
                                     "regions": regions}

        if getattr(self.market_module, "_milk_floor_hits", None):
            warnings.warn(f"raw milk price held just above zero in {sorted(self.market_module._milk_floor_hits)} "
                          "(negative milk prices not allowed in this scenario, CAPRI's negProdPriceAllowed): their milk "
                          "markets do not clear", RuntimeWarning, stacklevel=2)

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
                    self.market_module.par.demand_cal_frozen.copy(),
                    self.market_module.par.base_production.loc[list(self.market_module.EU)].copy(),
                    self.market_module.par.base_consumption.loc[list(self.market_module.EU)].copy(),
                    # bilateral market: calibrated systems and full base tables of this baseline
                    (self.market_module.par.bilat,
                     self.market_module.par.base_production.copy(), self.market_module.par.base_consumption.copy(),
                     dict(self.market_module.par.crush_q0_override or {}),
                     __import__("copy").deepcopy(self.market_module.par.eu_aligned_use or {})),
                    # Norway's base raw milk delivery (its dairy block's reference; K56)
                    dict(self.market_module.par.sup_milk0 or {}))
            except Exception as _exc:
                warnings.warn(f"baseline market state not cached ({_exc!r}); scenarios will re-run the baseline")

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
            # CAPRI's land-use change transitions per region (1000 ha per year for changes; capri_mod/environmental/luc.py)
            "luc": _luc_table(supply_results),
            # CAPRI's labour accounts (million hours; GROF LABT = sum LABT x LEVL / 1000) and its set-aside split
            # VSET / FALL with their premiums (tools/build/build_labour_setaside.py)
            "set_aside": _set_aside_table(supply_results, self.data, self._pmp_suffix()),
            "labour": None,
            # the NLP form's mineral N, P2O5, K2O purchases and flows per region and crop group (t)
            "fert_npk": _npk_table(supply_results),
            "policy_summary": policy_summary,
            "convergence": tracker.summary(),
            "outer_history": list(getattr(self, "_outer_history", None) or []),
            "metadata": {
                "n_regions": len(supply_results) if supply_results else 0,
                "n_outer_iterations": outer_iter + 1,
                "market_converged": market_eq.converged if market_eq else False,
                # False means the supply-market price feedback is incomplete;
                # such a run must not be compared against external references.
                "outer_converged": outer_converged,
                # member states whose raw milk price was held just above zero (negative milk prices not allowed by
                # the scenario, CAPRI's negProdPriceAllowed): the price ratio the dairy block would have given
                "milk_price_floor": dict(getattr(self.market_module, "_milk_floor_hits", None) or {}),
                # CAPRI's stop rule at the last iteration (outer_loop.stop_rule; capri_mod/utils/capri_stop.py)
                "capri_stop": ({**{k_: v_ for k_, v_ in (getattr(self, "_capri_stop_verdict", None) or {}).items() if k_ != "rows"},
                                "drift": list(getattr(self, "_capri_drift", None) or [])}
                               if getattr(self, "_capri_stop_verdict", None) else None),
                # Norway's last price gap (its own products > 5 kt; out of the convergence test from iteration 15,
                # as CAPRI's) and the product, reported as it is
                "nor_price_gap": (float(getattr(self, "_sup_dev_gap", 0.0) or 0.0),
                                  str((getattr(self, "_sup_dev_worst", None) or ("", ""))[1])),
                "nlp_tol_by_iteration": list(getattr(self, "_nlp_tol_trace", []) or []),
                # market calibration bounds that bound at this run's calibration (PROXY_AUDIT S185, S192)
                "market_calibration_bound_hits": dict(getattr(self.market_module, "calibration_bound_hits", None) or {}),
                "elapsed_seconds": round(t_elapsed, 1),
                # the baseline's drift from its calibration point by outer iteration (CAPRI's baseline reproduction)
                "base_calibration_drift": list(getattr(self, "_calib_trace", []) or []),
                "young_animal_prices": dict(self.supply_module.yani_price_ratio or {}),
                "young_animal_imbalance": float(getattr(self, "_yani_imbalance", 0.0) or 0.0),
                "young_animal_markets": dict(getattr(self, "_yani_detail", None) or {}),
                "pmp_source": str(getattr(self.supply_module, "pmp_source", "capri2030")),
                "pmp_capri_parts": list(getattr(self.supply_module, "pmp_capri_parts", ())),
                # regions whose NLP solve took a fallback in this run (JRC121368's relaxed N target, IPOPT's last
                # point kept as CAPRI keeps a non-optimal solve), each with IPOPT's status (supply_module._nlp_solve)
                # the jump check per outer iteration (supply.nlp_jump_check, K79): the regions checked and those whose
                # solution it replaced with another start's lower objective
                "nlp_jump_check": [{"it": e_.get("it"), "checked": sorted(e_["jump_check"]),
                                    "switched": sorted(r_ for r_, v_ in e_["jump_check"].items()
                                                       if str(v_.get("kept", "")).startswith("jump:"))}
                                   for e_ in (getattr(self, "_outer_history", None) or []) if e_.get("jump_check")],
                "nlp_fallback": {r_: list(m_._nlp_fallback_log) for r_, m_ in self.supply_module._models.items()
                                 if getattr(m_, "_nlp_fallback_log", None)},
                # regions whose NLP form needed the Green Deal's mineral caps relaxed (supply_module._capri_nlp_solve)
                "nlp_relaxed": {r_: m_._nlp_relaxed for r_, m_ in self.supply_module._models.items()
                                if getattr(m_, "_nlp_relaxed", None)},
                # member states below 1% of EU milk whose milk price has not settled (gap of the price signal)
                "milk_small_ms_gap": float(getattr(self, "_milk_ms_small_gap", 0.0) or 0.0),
            },
        }

        if self.verbose:
            reporter = ResultsReporter(results)
            reporter.print_summary()
            print(f"  Run completed in {t_elapsed:.1f}s")

        results["labour"] = _labour_table(supply_results, self.data, results.get("set_aside"))
        results["welfare_supply"] = self._welfare_supply(supply_results)
        return results


    # ------------------------------------------------------------------
    # SCENARIO COMPARISON
    # ------------------------------------------------------------------
    #: print a timed line per stage and outer iteration (wall clock, time since progress_t0); run scripts switch it on
    progress = False
    progress_t0: Optional[float] = None

    def _progress(self, msg: str) -> None:
        if not self.progress:
            return
        now = time.time()
        t0 = self.progress_t0 if self.progress_t0 is not None else now
        el = int(now - t0)
        print(f"[{time.strftime('%H:%M:%S')} +{el // 3600}:{el % 3600 // 60:02d}:{el % 60:02d}] {msg}", flush=True)


    # ------------------------------------------------------------------
    # BRIDGE: Supply → Market commodities
    # ------------------------------------------------------------------

    #: feed cereals whose EU demand is split into a feed part that follows
    #: herd sizes and a remainder that keeps its own-price response
    #: model NUTS prefix -> CAPRI member-state code where they differ (Belgium and Luxembourg are one CAPRI
    #: member state, BL; Ireland IR; Greece EL in both)
    _MS_CODE = MS_CODE

    @classmethod
    def member_state_of(cls, region: str) -> str:
        """CAPRI member-state code (e.g. DE000000) of a model region."""
        return capri_ms(region)

    #: CAPRI's market supply Hessian (calibrate_supply.gms): price shock per product
    MARKET_SUPPLY_SHOCK = setting("market.nq_price_shock")
    #: products whose price the supply models see only as a feed cost (CAPRI's feed-bulk columns)
    MARKET_SUPPLY_FEED_COLS = ("RAPC", "SUNC", "SOYC", "FENI", "FPRI", "DDGS")


    POOL_OF_PREFIX = MS_CODE

    #: young-animal markets: largest EU imbalance (share of production) accepted at convergence
    YANI_TOL = setting("young_animals.tol")
    #: outer loop: largest supply gap and land update at convergence (model_parameters.csv)
    SUPPLY_GAP_TOL = setting("outer_loop.supply_gap_tol")
    NBAL_UPDATE_TOL = setting("outer_loop.nbal_update_tol")
    #: Norway in the outer loop's convergence test, as CAPRI's (capmod/price_forecast.gms): a price change counts only
    #: where production exceeds 10 x p_minAbsProdIterChg (0.5 kt, capmod.gms l. 384), i.e. 5 kt; and Norway's changes
    #: are set to zero from the 15th iteration on ("Norway reacts very sensitive and seems to jump around",
    #: p_iterChg("NO000000",ROWS,STEP) $ (ORD(step) ge 15) = 0). Its prices are still relaxed and reported after that.
    SUP_GAP_MIN_PROD = setting("outer_loop.sup_gap_min_prod")
    SUP_GAP_LAST_ITER = setting("outer_loop.norway_gap_last_iter")
    #: damping of the Newton step for young-animal prices
    YANI_RELAXATION = setting("young_animals.relaxation")
    #: the young-animal price update takes each region's response from its solved NLP where the region has it (K65,
    #: SupplyModel.yani_exact_response); else from the PMP terms Q^-1. None (default): on with the cattle member
    #: splits (the per-sex markets need it), off without them, where the PMP terms' response converges (r86) and the
    #: validated runs stay reproducible; True / False force it
    use_yani_exact = setting("young_animals.use_exact", tri_state)


    #: young-animal price ratios: a numeric guard only. CAPRI bounds young-animal prices at +-10 x (|level| + 10) x
    #: its limit factor, negative prices allowed, and widens a bound that binds (arm/set_start_val.gms:536-580,
    #: arm/widen_bounds.gms:418-484); the earlier bounds 0.2 and 5 x base bound the Green Deal run's lamb and calf
    #: prices and left their markets open (K37)
    YANI_RATIO_BOUNDS = setting("young_animals.ratio_bounds", tuple)


    #: CAPRI's tradable feed bulks (global/fromimpact/sets.gms FEED_TRD), priced by the market (feedBlkPrice_)
    FEED_BULKS = ("FCER", "FPRO", "FENE", "FOTH", "FMIL")

    #: CAPRI final product -> market commodity (tools/build/build_livestock_products.py)
    LIVESTOCK_PRODUCT_MARKET = {"COMI": "MILK", "SGMI": "MILK", "BEEF": "BEEF", "PORK": "PORK",
                                "POUM": "POUL", "EGGS": "EGGS", "SGMT": "SGMT"}


    #: model country code -> CAPRI member state (BE and LU are CAPRI's BL)
    _CAPRI_MS = MS_CODE


    # ------------------------------------------------------------------
    # CONVENIENCE
    # ------------------------------------------------------------------

    @staticmethod
    def list_scenarios() -> List[str]:
        """List all available built-in scenarios."""
        return list_scenarios()

    def _pmp_suffix(self) -> str:
        """The PMP terms' column suffix of the set-aside split's weights: the 2030 terms at the 2030 market year
        (CAPRI's or the recipe's, as SupplyModule.pmp_source; CAPRI's for the elasticity calibration), else the base
        year's."""
        from capri_mod.supply.supply_module import SupplyModule
        if int(self.data.get("market_year", 2017) or 2017) != 2030:
            return ""
        return "_recipe2030" if str(getattr(SupplyModule, "pmp_source", "")) == "recipe" else "_capri2030"


def _luc_table(supply_results):
    """Region x transition (1000 ha per year for changes, remaining in full) from the regional results, or None."""
    import pandas as pd
    rows = {r: (getattr(res, "luc", None) or {}).get("transitions") for r, res in (supply_results or {}).items()}
    rows = {r: v for r, v in rows.items() if v}
    return pd.DataFrame.from_dict(rows, orient="index") if rows else None


def _npk_table(supply_results):
    """Long table of the NLP form's fertilisation block per region: nutrient, crop group, source, t; purchases as
    group "TOTAL", source "PURCHASE". None without the NLP form."""
    import pandas as pd
    rows = []
    for r, res in (supply_results or {}).items():
        for nut, o in (getattr(res, "fert_npk", None) or {}).items():
            rows.append(dict(region=r, nutrient=nut, ngrp="TOTAL", source="PURCHASE", t=float(o["purchase"])))
            for (g, s_), v in o.get("flows", {}).items():
                rows.append(dict(region=r, nutrient=nut, ngrp=g, source=s_, t=float(v)))
    return pd.DataFrame(rows) if rows else None


def _set_aside_table(supply_results, data, wsfx=""):
    """CAPRI's two set-aside activities in the model's SETA, per region (1000 ha; premiums million EUR): VSET = s X0 +
    w (X - X0), FALL = X - VSET (tools/build/build_labour_setaside.py: s CAPRI's VSET share at the calibration year, w the
    share of a common change CAPRI's PMP terms give VSET; X0 the region's base SETA). None without the data."""
    import pandas as pd
    sa, ar = data.get("set_aside_split"), data.get("areas")
    if sa is None or ar is None or "SETA" not in getattr(ar, "columns", []):
        return None
    yr = int(data.get("market_year", 2017) or 2017)
    vt = "_2030" if yr == 2030 else ""
    rows = {}
    for r, res in (supply_results or {}).items():
        if r not in sa.index or r not in ar.index:
            continue
        x = getattr(res, "activities", None)
        if x is None or "SETA" not in x.index:
            continue
        X, X0 = float(x["SETA"]), float(ar.at[r, "SETA"])
        row = sa.loc[r]
        s_ = row.get("share_vset" + vt)
        s_ = float(row.get("share_vset")) if s_ is None or s_ != s_ else float(s_)
        w = row.get("w_vset" + wsfx)
        w = float(row.get("w_vset", 0.5)) if w is None or w != w else float(w)
        v = min(max(s_ * X0 + w * (X - X0), 0.0), X) if X > 0 else 0.0
        f_ = X - v
        pv, pf = (float(row.get(k + vt, row.get(k, 0.0)) or 0.0) for k in ("prem_vset", "prem_fall"))
        lv, lf = (float(row.get(k + vt, row.get(k, 0.0)) or 0.0) for k in ("labt_vset", "labt_fall"))
        rows[r] = {"SETA": X, "VSET": v, "FALL": f_, "prem_VSET": v * pv / 1000.0, "prem_FALL": f_ * pf / 1000.0,
                   "labt_VSET": v * lv / 1000.0, "labt_FALL": f_ * lf / 1000.0}
    return pd.DataFrame.from_dict(rows, orient="index") if rows else None


def _labour_table(supply_results, data, set_aside=None):
    """CAPRI's labour accounts per region (million hours): total LABT, family LABF, paid LABP, as CAPRI's GROF =
    sum over activities of the level x labour per unit / 1000 (tools/build/build_labour_setaside.py; the 2030 coefficients
    at the 2030 market year). The set-aside's total labour from its VSET / FALL split where available. None without
    the data."""
    import pandas as pd
    lc = data.get("labour_coef")
    if lc is None:
        return None
    yr = int(data.get("market_year", 2017) or 2017)
    vt = "_2030" if yr == 2030 else ""
    if not isinstance(lc.index, pd.MultiIndex):
        lc = lc.reset_index().set_index(["region", "activity"]) if "activity" in lc.columns else lc
    rows = {}
    for r, res in (supply_results or {}).items():
        x = getattr(res, "activities", None)
        if x is None:
            continue
        tot = {"LABT": 0.0, "LABF": 0.0, "LABP": 0.0}
        for a, lev in x.items():
            if (r, a) not in lc.index or not (lev == lev):
                continue
            row = lc.loc[(r, a)]
            for it in tot:
                c = row.get(it.lower() + vt)
                c = row.get(it.lower()) if c is None or c != c else c
                if c is not None and c == c:
                    tot[it] += float(lev) * float(c) / 1000.0
        if set_aside is not None and r in set_aside.index and (r, "SETA") in lc.index:
            row = lc.loc[(r, "SETA")]
            c = row.get("labt" + vt)
            c = row.get("labt") if c is None or c != c else c
            if c is not None and c == c:
                tot["LABT"] += (float(set_aside.at[r, "labt_VSET"]) + float(set_aside.at[r, "labt_FALL"])
                                - float(x["SETA"]) * float(c) / 1000.0)
        rows[r] = tot
    return pd.DataFrame.from_dict(rows, orient="index") if rows else None


# refactor stage 4a: the blocks' methods see this module's names (capri_mod/coupling/__init__.py)
from capri_mod import coupling as _blocks  # noqa: E402
_blocks.inject(globals())
