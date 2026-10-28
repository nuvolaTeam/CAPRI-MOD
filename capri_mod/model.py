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
from capri_mod.data.definitions import MS_CODE, capri_ms, REGION_TO_COUNTRY
from capri_mod.csvio import read_csv


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
        self.supply_module = SupplyModule(self.data, self.supply_elasticities)
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

    def _trace_nlp_regions(self, top=4):
        """Outer-loop trace of the NLP form: the regions whose activity levels moved most since the last outer
        iteration (max over the columns of |dy| / max(|y|, 1% of the region's largest column)), with the starts IPOPT
        used (warm / prev / start, then a relaxation) and its iterations, and the counts of each path."""
        import numpy as _np
        prev = getattr(self, "_trace_nlp_prev", None) or {}
        cur, rows, paths = {}, [], {}
        for r_, m_ in (self.supply_module._models or {}).items():
            y_ = getattr(m_, "_nlp_y", None)
            if y_ is None:
                continue
            cur[r_] = y_
            p_ = getattr(m_, "_nlp_path", None) or ("?", 0)
            paths[p_[0]] = paths.get(p_[0], 0) + 1
            y0 = prev.get(r_)
            if y0 is not None and len(y0) == len(y_):
                # relative to the column's level, at least 1% of the region's largest column
                d_ = _np.abs(y_ - y0) / _np.maximum(_np.abs(y0), max(0.01 * float(_np.max(_np.abs(y0))), 1e-6))
                j_ = int(_np.argmax(d_))
                rows.append((float(d_[j_]), r_, j_, p_))
        self._trace_nlp_prev = cur
        import time as _t
        _now = _t.time()
        _dt = _now - getattr(self, "_trace_nlp_t", _now)
        self._trace_nlp_t = _now
        if not cur:
            return
        rows.sort(reverse=True)
        cols = lambda r_, j_: (list(getattr(self.supply_module._models[r_], "_nlp_cols", None) or [])[j_:j_ + 1] or [j_])[0]
        print(f"    [nlp] {_dt:.0f} s | paths " + ", ".join(f"{k} {v}" for k, v in sorted(paths.items()))
              + (" | moved " + "; ".join(f"{r_} {cols(r_, j_)} {d:.3f} ({p_[0]}, {p_[1]} it)" for d, r_, j_, p_ in rows[:top])
                 if rows else ""), flush=True)

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
            _mm._eu_base_supply = None
            _mm._eu_base_demand = None
            # a baseline's market runs without a market supply Hessian (the one of an earlier baseline belonged to
            # another solution, possibly another region set); its own is measured when a scenario needs it
            _mm.supply_hessian = None
            self._hessian_key = None
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
                _mm._demand_cal_frozen = _cal.copy()
                _mm.base_production.loc[list(_mm.EU)] = _bp
                _mm.base_consumption.loc[list(_mm.EU)] = _bc
                if len(_cache[_key]) > 5 and _cache[_key][5][0] is not None:
                    _bs, _bpa, _bca, _cov, _eau = _cache[_key][5]
                    _mm._bilat = _bs
                    for _sc in (_bs or {}).values():
                        if getattr(_sc, "trq_row", None) is not None and _sc.trq_offset is not None:
                            _sc.trq_offset = _sc.trq_offset * 0.0
                    _mm.base_production = _bpa.copy()
                    _mm.base_consumption = _bca.copy()
                    _mm._crush_q0_override = dict(_cov)
                    import copy as _cp
                    _mm._eu_aligned_use = _cp.deepcopy(_eau)
                    _mm._crush_cache = None
                    _mm._bilat_local_el = None
                    _mm._bilat_last_r = None
                if len(_cache[_key]) > 6:
                    _mm._sup_milk0 = dict(_cache[_key][6])

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
        self.market_module._yani_state = None
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
            self.market_module._milk_seen_ms = {
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
                    and getattr(self.market_module, "supply_hessian", None)):
                try:
                    self._hessian_at_scenario = True
                    self.market_module.supply_hessian = self._market_supply_hessian(price_signal, supply_results,
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
                self.market_module._yani_state = None

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
            if getattr(self.market_module, "eu_blocks", False):
                _dv = getattr(self, "_eu_dev", None) or {}
                _cm = self.market_module.commodities
                self.market_module._eu_price_seen = pd.DataFrame(
                    {rg: (1.0 + price_signal + _dv.get(rg, 0.0)).reindex(_cm).fillna(1.0)
                     for rg in self.market_module.EU}).T
            # Norway's supply models saw Norway's prices (K56)
            _sdv = getattr(self, "_sup_dev", None) or {}
            self.market_module._sup_price_seen = {
                rg: (1.0 + price_signal + (_sdv[rg].reindex(price_signal.index).fillna(0.0) if rg in _sdv else 0.0)
                     ).reindex(self.market_module.commodities).fillna(1.0)
                for rg in getattr(self.market_module, "SUP", ())}
            # premium damping state belongs to one run (CAPRIModel.run resets it on its first iteration)
            if outer_iter == 0:
                self.market_module._prem_prev, self.market_module._prem_w, self.market_module._prem_d = None, None, None
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
            _spm = {k_: v_ for k_, v_ in self._capri_step_special().items() if k_[1] != "MILK" and k_[0] != "NO000000"}
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
                        _wn = _wn.where(~_fl, (_wn * 0.5).clip(lower=0.1))
                        _wn = _wn.where(_fl, (_wn * 1.25).clip(upper=self.PRICE_SIGNAL_RELAXATION))
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
                    _bp = _mmk.base_production.loc[_rg] if _rg in _mmk.base_production.index else None
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
            _dl = getattr(self.market_module, "_dairy_last", None) if self.market_module._dairy_params() else None
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
                                       for r_, x_ in _sr_.items() if r_[:2] not in ("NO",)))
                         for a_ in ("DCOW", "BCOW", "BULL", "HFRS", "CALV", "PIGF", "PIGS", "BROI", "LAYS", "SHGM", "SHGF")}
                _dlh = getattr(self.market_module, "_dairy_last", None) or {}
                _hist.append({"it": outer_iter + 1,
                              "signal": price_signal.astype(float).to_dict(),
                              "target": _target.astype(float).to_dict(),
                              "yani_ratio": {k_: dict(v_) for k_, v_ in (getattr(self.supply_module, "yani_price_ratio_m", None) or {}).items()},
                              "yani_imbalance": float(getattr(self, "_yani_imbalance", 0.0) or 0.0),
                              "milk_ms_signal": dict(getattr(self, "_milk_ms_signal", None) or {}),
                              "yani_state": __import__("copy").deepcopy(getattr(self.market_module, "_yani_state", None)),
                              "yani_market": __import__("copy").deepcopy(getattr(self.market_module, "_yani_market_now", None)),
                              "milk_ms": {k_: {kk: float(vv) for kk, vv in v_.items()} for k_, v_ in (_dlh.get("ms_price_ratio") or {}).items()},
                              "herd": _herd,
                              "herd_regional": {r_: {a_: round(float(getattr(x_, "activities", pd.Series(dtype=float)).get(a_, 0.0)), 4)
                                                     for a_ in ("BCOW", "DCOW", "CALV", "BULL", "HFRS", "GRAS", "MAIF", "OFOD")}
                                                for r_, x_ in _sr_.items()}})
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
                    self.market_module._demand_cal_frozen.copy(),
                    self.market_module.base_production.loc[list(self.market_module.EU)].copy(),
                    self.market_module.base_consumption.loc[list(self.market_module.EU)].copy(),
                    # bilateral market: calibrated systems and full base tables of this baseline
                    (getattr(self.market_module, "_bilat", None),
                     self.market_module.base_production.copy(), self.market_module.base_consumption.copy(),
                     dict(getattr(self.market_module, "_crush_q0_override", None) or {}),
                     __import__("copy").deepcopy(getattr(self.market_module, "_eu_aligned_use", None) or {})),
                    # Norway's base raw milk delivery (its dairy block's reference; K56)
                    dict(getattr(self.market_module, "_sup_milk0", None) or {}))
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
                "capri_stop": ({k_: v_ for k_, v_ in (getattr(self, "_capri_stop_verdict", None) or {}).items() if k_ != "rows"}
                               or None),
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

    def _welfare_supply(self, supply_results) -> Optional[pd.DataFrame]:
        """The welfare components CAPRI takes from the supply models for the regions that have them (RMSSUP: the EU,
        Norway; reports/welfare.gms l. 360-380, 690-700, 800-806), per supply-model region, EUR million (levels):
          MGVA      market gross value added including premiums, sum over activities of (revenue - input cost +
                    premium) x level (CAPRI EAAG MGVA; capri_mod/income)
          RENT      the land rents: each land type's area x its rent at the solution, the dual of its land row
                    (EUR/ha; CAPRI's UAAR x d_area, reports/sol_simy.gms l. 181)
          ProfitAgr      the farms' profit, MGVA - RENT, and ProfitLandUse the land owners', RENT: CAPRI's accounts
                    with its land market (welfare.gms supremaMrk), as in CAPRI's 2030 reference run (EU27: MGVA
                    302,113 - rents 58,994 = ProfitAgr 243,119; capri_data/sources/capri_res/ref2030_welfare.csv)
          PSEs      the budget's cost of the premiums, minus the premiums paid (CAPRI -FEOP, -FEOG of the products
                    without a market)
        The market's agents' components are in results["market"].welfare. A failure here does not stop the run:
        it is warned and the table is None."""
        if not supply_results:
            return None
        try:
            from capri_mod.income.income_module import IncomeDistributionModule
            im = IncomeDistributionModule(self.data)
            rows = {}
            rlab = {"arable_land": "ARAC", "grassland": "GRAS", "permanent_land": "FRUN"}
            for reg, res in supply_results.items():
                inc, prem = im._income_parts(reg, res, self.supply_module)
                sp = getattr(res, "shadow_prices", None) or {}
                lt = getattr(res, "land_types", None) or {}
                # EUR/ha x 1000 ha = EUR 1000
                rent = sum((float(sp.get(lab, 0.0)) - float(sp.get(lab + "_lo", 0.0))) * float(lt.get(t, 0.0))
                           for lab, t in rlab.items())
                rows[reg] = {"MGVA": inc / 1000.0, "RENT": rent / 1000.0, "ProfitAgr": (inc - rent) / 1000.0,
                             "ProfitLandUse": rent / 1000.0, "PSEs": -prem / 1000.0}
            return pd.DataFrame.from_dict(rows, orient="index")
        except Exception as exc:
            warnings.warn(f"welfare: the supply models' components could not be computed ({exc!r})")
            return None

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
            # CAPRI's welfare (reports/welfare.gms), world totals: the market's agents (market/welfare.py) and, for
            # the regions with supply models, the farms' MGVA and the premiums' budget cost (_welfare_supply)
            tot = 0.0
            for comp in list(getattr(s_mkt.welfare, "columns", [])):
                if comp in b_mkt.welfare.columns and comp != "Welfare":
                    d_ = float(s_mkt.welfare[comp].sum() - b_mkt.welfare[comp].sum())
                    diffs[f"welfare_{comp}_EUR_million_change"] = d_
                    tot += d_
            b_ws, s_ws = baseline_results.get("welfare_supply"), scenario_results.get("welfare_supply")
            if b_ws is not None and s_ws is not None:
                for comp, lab in (("ProfitAgr", "ProfitAgr_supply_models"), ("ProfitLandUse", "ProfitLandUse"),
                                  ("PSEs", "PSEs")):
                    d_ = float(s_ws[comp].sum() - b_ws[comp].sum())
                    diffs[f"welfare_{lab}_EUR_million_change"] = d_
                    tot += d_
                diffs["welfare_EUR_million_change"] = tot

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
    _MS_CODE = MS_CODE

    @classmethod
    def member_state_of(cls, region: str) -> str:
        """CAPRI member-state code (e.g. DE000000) of a model region."""
        return capri_ms(region)

    #: CAPRI's market supply Hessian (calibrate_supply.gms): price shock per product
    MARKET_SUPPLY_SHOCK = setting("market.nq_price_shock")
    #: products whose price the supply models see only as a feed cost (CAPRI's feed-bulk columns)
    MARKET_SUPPLY_FEED_COLS = ("RAPC", "SUNC", "SOYC", "FENI", "FPRI", "DDGS")

    def _measure_pending_hessian(self, pend) -> None:
        """The market supply Hessian of the baseline that has just run (recorded in _hessian_pending), measured from the
        state the baseline left: called at the start of the scenario run that needs it, before the scenario changes
        anything (or right after the baseline the scenario ran for itself)."""
        from capri_mod.supply.supply_module import RegionalSupplyModel as _RSMh
        _RSMh.nlp_tol = float(self.nlp_tol_final)          # the baseline's solves after its loop
        try:
            self._progress("market supply Hessian of the baseline ...")
            _t_h = time.time()
            self.market_module.supply_hessian = self._market_supply_hessian(pend["price_signal"], pend["supply_results"],
                                                                            pend["regions"])
            self._hessian_key = pend["key"]
            self._progress(f"market supply Hessian of the baseline: {time.time() - _t_h:.0f} s")
        except Exception as _exc:
            warnings.warn(f"market supply Hessian not built ({_exc!r}); the market keeps its own-price "
                          "anticipation", RuntimeWarning, stacklevel=2)
            self.market_module.supply_hessian = None
            self._hessian_key = pend["key"]
            # recorded, so a run without CAPRI's market supply function shows it in its metadata (r131)
            self.market_supply_hessian_info = {"source": "failed", "error": repr(_exc)}

    def _market_supply_hessian(self, price_signal, supply_results, regions):
        """CAPRI's calibration of the market's supply functions to the supply models (supply/calibrate_supply.gms:
        193-508), on this baseline: per product y, the supply models' price of y is raised by 1% (sugar beet with sugar,
        durum with wheat, as the price signal moves them), every regional model re-solved, outputs bridged to the market
        products per member state; H[ms][x, y] = (Q_x(shocked) - Q_x(base)) / (change of y's price relative to base).
        The base is re-solved at the end, so the models leave as they came. Cached on disk by the base solution and
        settings (CAPRI stores it per baseline, supply_elas_*.gdx). Returns {"eu": DataFrame x by y, "ms": {ms: DataFrame}}."""
        import hashlib
        from pathlib import Path as _P
        regs = regions or list(self.data["areas"].index)
        sm = self.supply_module
        pol = dict(getattr(self, "_last_spol", {}) or {})
        sig0 = price_signal.copy()

        # young animals (CAPRI xxOmYani in p_hessNQSupp, calibrate_supply.gms l. 437-458): their net balance per country
        # is a row ("YANI:<good>") and their price a column, shocked as the products' are
        from capri_mod.supply.supply_module import young_animal_table as _yat
        yani_goods = sorted({g for rec in _yat().values() for g in rec})

        def bridged(res):
            self._ls_by_country = self._livestock_products_by_country(res)
            q_ = self._bridge_supply_to_market(sm.aggregate_supply(res, by_country=True)).fillna(0.0)
            if yani_goods:
                yn = self._young_animal_net_by_country(res)
                for g in yani_goods:
                    q_["YANI:" + g] = pd.Series({cc: v.get(g, 0.0) for cc, v in yn.items()}).reindex(q_.index).fillna(0.0)
            return q_
        q0 = bridged(supply_results)
        skip = bool(_settings().get("market.hessian_skip_unchanged"))
        cols_y = [c for c in sig0.index if c in q0.columns and float(q0[c].clip(lower=0).sum()) > 1e-6]
        cols_y += [c for c in self.MARKET_SUPPLY_FEED_COLS if c in sig0.index and c not in cols_y]
        cols_y += ["YANI:" + g for g in yani_goods]
        key_src = (repr((sorted(regs), [round(float(v), 3) for v in q0.sum(axis=0).values], list(q0.columns),
                        [round(float(v), 6) for v in sig0.values], self.MARKET_SUPPLY_SHOCK,
                        bool(getattr(self, "use_manure_market", False)), str(getattr(self, "_endotech_key", "")),
                        # the regional models' calibration (K58): a Hessian measured before the ridge fit is stale
                        "nlp",               # the supply form, when there were two (keeps the cached Hessians' keys)
                        str(getattr(self.supply_module, "pmp_source", "capri2030")),
                        tuple(getattr(self.supply_module, "pmp_capri_parts", ())), __import__(
                            "capri_mod.supply.capri_regional_nlp", fromlist=["CAL_RIDGE"]).CAL_RIDGE,
                        tuple(yani_goods),
                        # 28 October 2026 (audit S13): activities of a calibrated part without a positive own PMP term
                        # are held at their level; their price response changes, their base level does not, so the
                        # base totals above would not tell a Hessian measured before from one measured after
                        "held-without-own-term",
                        # the supply models' rules that change their price response (24 October 2026: S6-S10)
                        # (the rules whose switches were removed 27 October 2026 keep their values' place, so the
                        # cached Hessians' keys stay valid)
                        tuple(str(_settings().get(k_)) if k_ else v_ for k_, v_ in (
                            ("", "capri"), ("", "True"),        # need per ha from yield as CAPRI; yield-dependent inputs
                            ("", "True"), ("supply.cap_greening", ""), ("supply.fert_slope_with_saving", ""),
                            ("", "True"), ("", "True"),         # fertiliser options' cost on purchases; catch crops
                            # 26 October 2026 (K75): the NLP form without the lagged fodder band rows
                            ("", "True"))),     # the fodder band rows, removed 27 October 2026
                        # the measurement: every shock from the baseline's state (24 October 2026)
                        "shocks-from-base")
                        # differences to the base re-solved from the same state, regions a shock does not reach not
                        # re-solved (27 October 2026, market.hessian_skip_unchanged; off: the key as before)
                        + (("base-resolved-skip-unchanged", "full-solve-state") if skip else ()))
                   # at a scenario's state (market.hessian_scenario_iter): its young-animal and member-state milk
                   # prices too (a baseline's key is unchanged)
                   + (repr((sorted((getattr(sm, "yani_price_ratio", None) or {}).items()),
                            sorted((k_, sorted(v_.items())) for k_, v_ in (getattr(sm, "yani_price_ratio_ms", None) or {}).items()),
                            sorted((getattr(sm, "milk_price_dev_ms", None) or {}).items())))
                      if getattr(self, "_hessian_at_scenario", False) else ""))
        key = hashlib.sha1(key_src.encode()).hexdigest()[:16]
        cdir = _P(__file__).resolve().parents[1] / ".cache" / "market_supply_hessian"
        # Parquet (binary doubles, exact by construction). The Hessians cached as CSV before 27 October 2026 were
        # converted (read to the last digit, K82, and checked equal) and are no longer read
        cfile = cdir / f"{key}.parquet"
        if cfile.exists():
            t = pd.read_parquet(cfile)
            ms_h = {ms: g.pivot(index="x", columns="y", values="dq").fillna(0.0) for ms, g in t.groupby("ms")}
            eu, sup, blocks = self._split_hessian(ms_h)
            self.market_supply_hessian_info = {"source": "cache", "file": str(cfile), "products": len(eu.columns)}
            self.__dict__.setdefault("market_supply_hessian_log", []).append(dict(self.market_supply_hessian_info))
            return {"eu": eu, "ms": ms_h, "sup": sup, "blocks": blocks}
        import time as _t
        import copy as _cp
        t0 = _t.time()
        fb0 = getattr(sm, "feed_bulk_ratio", None)
        rows = []
        # every shock starts from the baseline's solution, and the models leave as they came: the regional NLPs' warm
        # starts and path state (_nlp_*) and the N-price loop's state are restored before each shock and after the
        # base re-solve. Chained warm starts let IPOPT end the base re-solve at another stationary point of the
        # non-convex problem (DE11, 24 October 2026: 12 kt off the baseline, and the next baseline from that state
        # 2% less wheat), so the scenario started from a state the baseline never had
        # the regional models' state: the warm-start fields (_nlp*) and everything else a solve leaves for the next one
        # (RegionalSupplyModel.SOLVE_STATE: the ammonia options' linearisation point, rations, splits, last solutions).
        # Until 27 October 2026 only the _nlp* fields were saved: each shock started from the state the previous shock
        # left (the ammonia options' point differed at 1e-36, rations and splits possibly more)
        def _state_key(mo_, k_):
            if not skip:                                   # the measurement as before (cached Hessians keep their keys)
                return k_.startswith("_nlp")
            return (k_.startswith("_nlp") and k_ != "_nlp_times") or k_ in getattr(type(mo_), "SOLVE_STATE", ())

        def _snapshot():
            _c = _cp.deepcopy if skip else _cp.copy
            mods = {r_: {k_: _c(v_) for k_, v_ in mo_.__dict__.items() if _state_key(mo_, k_)}
                    for r_, mo_ in sm._models.items()}
            return mods, {n_: _cp.deepcopy(sm.__dict__.get(n_)) for n_ in getattr(sm, "_PAR_STATE", ())}

        def _restore(snap):
            mods, par = snap
            for r_, d_ in mods.items():
                mo_ = sm._models.get(r_)
                if mo_ is None:
                    continue
                for k_ in [k_ for k_ in mo_.__dict__ if _state_key(mo_, k_) and k_ not in d_]:
                    del mo_.__dict__[k_]
                mo_.__dict__.update({k_: (_cp.deepcopy if skip else _cp.copy)(v_) for k_, v_ in d_.items()})
            for n_, v_ in par.items():
                if v_ is None:
                    sm.__dict__.pop(n_, None)
                else:
                    sm.__dict__[n_] = _cp.deepcopy(v_)
        _snap0 = _snapshot()
        yr0 = (getattr(sm, "yani_price_ratio", None), getattr(sm, "yani_price_ratio_ms", None),
               getattr(sm, "yani_price_ratio_m", None))
        q_ref, n_skipped, n_solved = q0, 0, 0
        verify = skip and __import__("os").environ.get("CAPRI_HESSIAN_SKIP_VERIFY", "") == "1"
        if skip:
            # the base re-solved from the baseline's state first, each region's first solve fingerprinted: a shock
            # whose first solve in a region has the same inputs (the region does not see the shocked price) would
            # repeat this base solve exactly, so the region is not re-solved and its base result is taken. The
            # differences are taken to this re-solved base: the shocks start from the same state, so a region a shock
            # does not reach contributes exactly 0 (before, the re-solve's departure from the baseline's own solution,
            # up to 0.04 kt in r161, entered every column)
            sm.feed_bulk_ratio = fb0 if fb0 is not None else self.feed_bulk_price_ratios(sig0)
            _restore(_snap0)
            sm._hess_fp, sm._hess_verify = {}, {}
            sm._hess_probe = "record"
            try:
                res_b = sm.run(price_signals=sig0, policy_scenario=pol, regions=regs, verbose=False)
            finally:
                sm._hess_probe = None
            q_ref = bridged(res_b)
            sm._hess_base_res = res_b
        try:
            _t_h0 = time.time()
            for _k_y, y in enumerate(cols_y):
                if _k_y and _k_y % 5 == 0:
                    self._progress(f"  market supply Hessian: {_k_y}/{len(cols_y)} price shocks, "
                                   f"{time.time() - _t_h0:.0f} s; {n_skipped} of {n_solved} regional solves skipped")
                sig = sig0.copy()
                if y.startswith("YANI:"):
                    # a young animal's price raised by the shock in every regional model (EU and Norway), the products'
                    # prices at the base
                    # (relative to its current price: 1 at a baseline, the scenario's at a scenario's state; Norway's models
                    # their own market's)
                    g_ = y[5:]
                    eu0 = {g: 1.0 for g in yani_goods}
                    eu0.update({g: float(v) for g, v in (yr0[0] or {}).items()})
                    dr = self.MARKET_SUPPLY_SHOCK * eu0.get(g_, 1.0)
                    sm.yani_price_ratio = {**eu0, g_: eu0.get(g_, 1.0) + dr}
                    if yr0[1]:
                        sm.yani_price_ratio_ms = {ms_: {**dict(d_), g_: float(dict(d_).get(g_, 1.0)) * (1.0 + self.MARKET_SUPPLY_SHOCK)}
                                                  for ms_, d_ in yr0[1].items()}
                        dr_ms = {ms_: self.MARKET_SUPPLY_SHOCK * float(dict(d_).get(g_, 1.0)) for ms_, d_ in yr0[1].items()}
                    else:
                        sm.yani_price_ratio_ms, dr_ms = None, {}
                    sm.yani_price_ratio_m = yr0[2]
                else:
                    dr = self.MARKET_SUPPLY_SHOCK * (1.0 + float(sig0.get(y, 0.0)))
                    sig[y] = float(sig0.get(y, 0.0)) + dr
                    if y == "SUGR" and "SUGB" in sig.index:
                        sig["SUGB"] = sig["SUGR"]
                    if y == "SWHE" and "DWHE" in sig.index:
                        sig["DWHE"] = sig["SWHE"]
                    sm.yani_price_ratio, sm.yani_price_ratio_ms, sm.yani_price_ratio_m = yr0
                    dr_ms = {}
                sm.feed_bulk_ratio = self.feed_bulk_price_ratios(sig)
                _restore(_snap0)
                if skip:
                    sm._hess_probe, sm._hess_shock = ("verify" if verify else "compare"), y
                try:
                    res = sm.run(price_signals=sig, policy_scenario=pol, regions=regs, verbose=False)
                finally:
                    sm._hess_probe = None
                n_skipped += sum(1 for r_ in res.values() if getattr(r_, "hess_unchanged", False))
                n_solved += len(res)
                # the price change each country's models saw (Norway's young-animal prices are its own market's)
                div = pd.Series([float(dr_ms.get(capri_ms(str(cc)), dr)) for cc in q0.index], index=q0.index)
                dq = (bridged(res) - q_ref).reindex(index=q0.index, columns=q0.columns).fillna(0.0).div(div, axis=0)
                for ms in dq.index:
                    for x in dq.columns:
                        v = float(dq.at[ms, x])
                        if abs(v) > 1e-9:
                            rows.append((ms, x, y, v))
        finally:
            sm._hess_probe = None
            sm.__dict__.pop("_hess_base_res", None)
        # back to the base: the regional models' warm starts and states as the baseline left them
        sm.yani_price_ratio, sm.yani_price_ratio_ms, sm.yani_price_ratio_m = yr0
        sm.feed_bulk_ratio = fb0 if fb0 is not None else self.feed_bulk_price_ratios(sig0)
        _restore(_snap0)
        if skip:
            dev = float((q_ref - q0).abs().max().max())          # the base re-solved first
        else:
            res = sm.run(price_signals=sig0, policy_scenario=pol, regions=regs, verbose=False)
            dev = float((bridged(res) - q0).abs().max().max())
        _restore(_snap0)
        bad = sorted(k_ for k_, v_ in (getattr(sm, "_hess_verify", None) or {}).items() if not v_)
        n_ver = len(getattr(sm, "_hess_verify", None) or {})
        sm.__dict__.pop("_hess_fp", None)
        sm.__dict__.pop("_hess_verify", None)
        self._ls_by_country = self._livestock_products_by_country(supply_results)
        t = pd.DataFrame(rows, columns=["ms", "x", "y", "dq"])
        cdir.mkdir(parents=True, exist_ok=True)
        # written whole, then renamed: another process (parallel test workers, two runs) reads a complete file or none
        import os as _os
        _tmp = cdir / f"{key}.{_os.getpid()}.tmp"
        t.to_parquet(_tmp, index=False)
        _os.replace(_tmp, cfile)
        ms_h = {ms: g.pivot(index="x", columns="y", values="dq").fillna(0.0) for ms, g in t.groupby("ms")}
        eu, sup, blocks = self._split_hessian(ms_h)
        self.market_supply_hessian_info = {"source": "computed", "file": str(cfile), "products": len(cols_y),
                                           "seconds": round(_t.time() - t0, 1), "base_resolve_max_dev_kt": dev}
        if skip:
            self.market_supply_hessian_info.update(regions_skipped=n_skipped, regions_shocked=n_solved)
            if verify:
                # CAPRI_HESSIAN_SKIP_VERIFY=1: the regions that would have been skipped were solved; their results must
                # equal the base re-solve's (else the fingerprint misses an input of the regional solve)
                self.market_supply_hessian_info.update(verified=n_ver, verify_mismatch=bad[:20])
                if bad:
                    warnings.warn(f"market supply Hessian: {len(bad)} region solves with the base's inputs gave "
                                  f"another result, e.g. {bad[:5]}", RuntimeWarning)
        self.__dict__.setdefault("market_supply_hessian_log", []).append(dict(self.market_supply_hessian_info))
        return {"eu": eu, "ms": ms_h, "sup": sup, "blocks": blocks}

    def _split_hessian(self, ms_h):
        """The market supply Hessian per country summed for the EU, and kept per non-EU market region with supply
        models (Norway: its own market supply function, K56). Norway's shocks are the same products' prices (one
        shock per product for all models; the cross terms between Norway's and the EU's prices do not arise, as each
        market region's supply depends only on the prices its own models see)."""
        mm = self.market_module
        sup_of = getattr(mm, "sup_region_of_country", lambda c: None)
        eu = self._sum_frames([h for cc, h in ms_h.items() if sup_of(cc) is None])
        sup = {}
        for cc, h in ms_h.items():
            rg = sup_of(cc)
            if rg is not None:
                sup[rg] = h if rg not in sup else sup[rg].add(h, fill_value=0.0)
        # CAPRI's two EU trade blocks: each block's member states, summed (each member state's models see its own
        # block's prices, so the measured response is to that block's price)
        blocks = {}
        if getattr(mm, "eu_blocks", False):
            bmap = mm._ms_block_map()
            for cc, h in ms_h.items():
                if sup_of(cc) is not None:
                    continue
                b_ = bmap.get(cc) or bmap.get(capri_ms(cc))
                if b_ is None:
                    raise ValueError(f"member state {cc} has no EU trade block (eu_market_blocks.csv)")
                blocks[b_] = h if b_ not in blocks else blocks[b_].add(h, fill_value=0.0)
        return eu, sup, blocks

    @staticmethod
    def _sum_frames(frames):
        out = None
        for f_ in frames:
            out = f_.copy() if out is None else out.add(f_, fill_value=0.0)
        return out.fillna(0.0) if out is not None else pd.DataFrame()

    def feed_bulk_price_ratios(self, price_signal) -> dict:
        """{(member state, bulk): price relative to the base} of CAPRI's feed bulks (feedBlkPrice_) at the EU
        price changes of the price signal (MarketModule.feed_bulk_price_ratio)."""
        mm = self.market_module
        sig = price_signal if price_signal is not None else {}
        ratio = {c: 1.0 + float(sig.get(c, 0.0)) for c in mm.commodities} if hasattr(sig, "get") else {}
        # EU trade blocks: the member state's block prices (EU signal + the block's departure)
        _dev = (getattr(self, "_eu_dev", None) or {}) if (getattr(mm, "eu_blocks", False) and price_signal is not None) else {}
        rr = {rg: {c: v + float(d.get(c, 0.0)) for c, v in ratio.items()} for rg, d in _dev.items()}
        _fb = mm._feed_bulk_params()
        out = {k: mm.feed_bulk_price_ratio(k[0], k[1], rr.get(mm.eu_region_of_ms(k[0]), ratio))
               for k in (_fb.get("bulks") or {})}
        # Norway's supply models: its own bulks at its own market's prices (the EU signal plus Norway's departure;
        # K56)
        _sd = (getattr(self, "_sup_dev", None) or {}) if price_signal is not None else {}
        _ms_reg = {v: k for k, v in (getattr(mm, "SUP_NONEU_MS", {}) or {}).items()}
        for k in (_fb.get("bulks_sup") or {}):
            d_ = _sd.get(_ms_reg.get(k[0]))
            rs = {c: v + float(d_.get(c, 0.0)) for c, v in ratio.items()} if d_ is not None else ratio
            out[k] = mm.feed_bulk_price_ratio(k[0], k[1], rs)
        return out

    def _update_rations(self, price_signal) -> None:
        """CAPRI's rations and the current feed prices for the feeding block inside the regional models (the ration is
        chosen there), and the ration state (feed per head of the last regional solution) for the market's feed
        index. Cereals and protein-rich feed: the member state's CAPRI bulk price indices (feedBlkPrice_); home-grown
        fodder through its balance; feeds without a market at base value."""
        from capri_mod.feed.ration import ration_model_for, rations_by_region, feed_prices_by_region
        rm = getattr(self, "_ration_model", None)
        if rm is None:
            rm = ration_model_for(self.data, self.data_dir if hasattr(self, "data_dir") else None,
                                  getattr(self.supply_module, "pmp_source", "capri2030"),
                                  getattr(self.supply_module, "pmp_capri_parts", ()))
            self._ration_model = rm
        # FEED BULK PRICES per member state (CAPRI feedBlkPrice_): the CES price index of the member state's
        # cereals (FCER) and protein-rich feed (FPRO, with cakes, DDGS, pulses, oils, milling by-products)
        bix = self.feed_bulk_price_ratios(price_signal)
        self.supply_module.feed_bulk_ratio = bix
        state = {}
        newprev = {}
        _last = getattr(self, "_last_supply_results", None) or {}
        # FEEDING INSIDE THE SUPPLY MODELS (CAPRI: v_feedInpCoeff is chosen only there, together with herds and
        # fodder): no ration is chosen outside them. The ration state is the feed per head of each region's last
        # regional solution (base ration before the first), kept for what reads it: the market's feed index where a
        # region returned no feed.
        for (reg, act), r in rm.rations.items():
            _res = _last.get(reg) if (price_signal is not None and hasattr(_last, "get")) else None
            _ft = (getattr(_res, "feed_t", None) or {}).get(act) if _res is not None else None
            _acts = getattr(_res, "activities", None) if _res is not None else None
            _h = float(_acts.get(act, 0.0)) if _acts is not None else 0.0
            if _ft and _h > 0:
                x = np.array([float(_ft.get(f_, 0.0)) / _h for f_ in r.feeds])
            else:
                x = np.array(r.x0, dtype=float)
            newprev[(reg, act)] = x
            state.setdefault(reg, {})[act] = {"x": dict(zip(r.feeds, x)), "dcost": 0.0,
                                              "nitr_kg": 0.0, "nitr_share": 0.0}
        self.supply_module.ration_state = state
        # rations and CURRENT feed prices for feeding inside the supply model
        # the per-region rations dicts are built ONCE per ration model and reused, so the
        # feed-in-supply block cache (keyed on the dict's identity) hits; only prices change
        if getattr(self, "_feed_rations_for", None) is not rm:
            self._feed_rations_stable = rations_by_region(rm)
            self._feed_rations_for = rm
        _fp = feed_prices_by_region(rm, bix)
        self.supply_module.feed_rations = self._feed_rations_stable
        self.supply_module.feed_prices = _fp
        self._ration_state = state
        self._ration_prev = newprev

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

    def _yani_market_region(self, reg: str) -> str:
        """The young-animal market of a supply region: CAPRI clears young animals per market region (yaniMarket_ per
        RM): the EU (one region) or its trade block; Norway its own (NOR, K56)."""
        mm = self.market_module
        return (mm.sup_region_of_country(reg) if hasattr(mm, "sup_region_of_country") else None) \
            or mm.eu_region_of_country(reg) or mm.EU[0]

    def _young_animal_net_by_country(self, supply_results) -> dict:
        """{country: {good: net balance (production - use, 1000 head)}} - _young_animal_balance per country (CAPRI's
        p_hessNQSupp rows for xxOmYani are per member state, calibrate_supply.gms)."""
        out = {}
        for reg, res in (supply_results or {}).items():
            net, _ = self._young_animal_balance({reg: res})
            cc = REGION_TO_COUNTRY.get(reg, reg)              # the country keys of aggregate_supply(by_country=True)
            d = out.setdefault(cc, {})
            for (_mr, g), v in net.items():
                d[g] = d.get(g, 0.0) + float(v)
        return out

    def _young_animal_balance(self, supply_results):
        """Net balance (production - use, 1000 head) and production of each young-animal good per young-animal market
        (EU27, or each EU trade block), {(market, good): value}, from the regional results and CAPRI's
        coefficients."""
        from capri_mod.supply.supply_module import young_animal_table
        tab = young_animal_table()
        net, prod = {}, {}
        for reg, res in (supply_results or {}).items():
            rec = tab.get(reg) or {}
            x = getattr(res, "activities", None)
            if x is None:
                continue
            mr = self._yani_market_region(reg)
            # bulls and heifers at the low-intensity activity turn over more animals per stall, each
            # bought as a young animal (Sprint 7c): z stalls x use per head x (low - high) / average
            cz = getattr(res, "cattle_shift", None) or {}
            ct = (self.data.get("cattle_intensity") or {}).get(reg) or {}
            from capri_mod.supply.supply_module import RegionalSupplyModel as _RSM0
            _member_splits = bool(getattr(_RSM0, "use_cattle_member_splits", False))
            for g, r in rec.items():
                p_ = sum(float(c) * float(x.get(a, 0.0) or 0.0) for a, c in r.get("produce", {}).items())
                u_ = sum(float(c) * float(x.get(a, 0.0) or 0.0) for a, c in r.get("use", {}).items())
                # every split of a cattle animal (key "BULL", "HFRS:rep", "CALV:male", ...): z stalls x use / production
                # per head x (a - b) / average; the intensity pairs' young bought as before (dyoung_rel)
                if not _member_splits:
                    # the intensity pairs alone (Sprint 7c), as in the validated runs r86 / r87
                    u_ += sum(float(c) * float(cz.get(a, 0.0)) * float(ct[a]["dyoung_rel"])
                              for a, c in r.get("use", {}).items() if a in cz and a in ct)
                    net[(mr, g)] = net.get((mr, g), 0.0) + p_ - u_
                    prod[(mr, g)] = prod.get((mr, g), 0.0) + p_
                    continue
                for k_, z_ in cz.items():
                    a_ = k_.split(":")[0]
                    if not z_ or k_ not in ct:
                        continue
                    cu = r.get("use", {}).get(a_)
                    if cu:
                        du = ct[k_].get(f"duse_{g}_rel")
                        du = float(ct[k_]["dyoung_rel"]) if du is None or du != du else float(du)
                        u_ += float(cu) * float(z_) * du
                    cp_ = r.get("produce", {}).get(a_) if _member_splits else None
                    dp = ct[k_].get(f"dprod_{g}_rel")
                    if cp_ and dp is not None and dp == dp:
                        p_ += float(cp_) * float(z_) * float(dp)
                net[(mr, g)] = net.get((mr, g), 0.0) + p_ - u_
                prod[(mr, g)] = prod.get((mr, g), 0.0) + p_
        return net, prod

    #: young-animal price ratios: a numeric guard only. CAPRI bounds young-animal prices at +-10 x (|level| + 10) x
    #: its limit factor, negative prices allowed, and widens a bound that binds (arm/set_start_val.gms:536-580,
    #: arm/widen_bounds.gms:418-484); the earlier bounds 0.2 and 5 x base bound the Green Deal run's lamb and calf
    #: prices and left their markets open (K37)
    YANI_RATIO_BOUNDS = setting("young_animals.ratio_bounds", tuple)

    def _update_young_animal_prices(self, supply_results, ref) -> None:
        """Clear CAPRI's young-animal markets (arm/market_model.gms yaniMarket_ per market region): the net balance
        of each good in each young-animal market (the EU, or each EU trade block) stays at its baseline level (young
        animals are not traded with third countries nor, in CAPRI, between the trade blocks) and the prices adjust.
        As CAPRI's market model, the supply response is approximated from the supply models' PMP terms - here
        dx = Q^-1 dc per region (the normalised-quadratic approximation, CAPRI p_hessNQSupp) - and the approximation
        is renewed every outer iteration; a damped Newton step on the price ratios, per market."""
        from capri_mod.supply.supply_module import young_animal_table
        tab = young_animal_table()
        net, prod = self._young_animal_balance(supply_results)
        sm = self.supply_module
        markets = sorted({mr for (mr, _g) in ref})
        ratio_m = dict(getattr(sm, "yani_price_ratio_m", None) or {})
        worst = 0.0
        lo, hi = self.YANI_RATIO_BOUNDS
        for mr in markets:
            goods = sorted(g for (m_, g) in ref if m_ == mr)
            gi = {g: i for i, g in enumerate(goods)}
            J = np.zeros((len(goods), len(goods)))
            n_exact = 0
            for reg, res in (supply_results or {}).items():
                rec = tab.get(reg)
                model = getattr(sm, "_models", {}).get(reg)
                if not rec or self._yani_market_region(reg) != mr:
                    continue
                # the region's response from its solved NLP, constraints included (K65; SupplyModel._yani_response)
                ex = getattr(res, "yani_dnet", None)
                _ue = getattr(self, "use_yani_exact", None)
                if _ue is None:
                    from capri_mod.supply.supply_module import RegionalSupplyModel as _RSMe
                    _ue = bool(getattr(_RSMe, "use_cattle_member_splits", False))
                if ex is not None and _ue:
                    eg = {g: i for i, g in enumerate(ex["goods"])}
                    if all(g in eg for g in goods if g in rec):
                        dn = np.asarray(ex["dnet"], float)
                        for g2 in goods:
                            for g1 in goods:
                                if g2 in eg and g1 in eg:
                                    J[gi[g2], gi[g1]] += dn[eg[g2], eg[g1]]
                        n_exact += 1
                        continue
                if model is None or getattr(model, "Q", None) is None:
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
                # the cattle splits (CAPRI's replacement heifers and calves with their own levels, per sex): their
                # response to the young-animal prices, z = H^-1 dc, with their own young-animal coefficients - without
                # it the per-sex markets saw only the animals' fixed mixes (male and female calves bought in fixed
                # proportion: a singular direction) and the prices of the two sexes ran apart (r89: x 8 and -1)
                ct = (self.data.get("cattle_intensity") or {}).get(reg) or {}
                from capri_mod.supply.supply_module import RegionalSupplyModel as _RSM1
                zk = [k for k in (getattr(res, "cattle_shift", None) or {}) if k in ct] \
                    if getattr(_RSM1, "use_cattle_member_splits", False) else []
                if zk:
                    from capri_mod.supply.supply_module import RegionalSupplyModel as _RSM
                    zk, Hz = _RSM.cattle_split_hessian(ct, zk)
                    if zk:
                        Nz = np.zeros((len(zk), len(goods)))
                        for i_, k_ in enumerate(zk):
                            a_ = k_.split(":")[0]
                            for g, r in rec.items():
                                if g not in gi:
                                    continue
                                cp_ = float(r.get("produce", {}).get(a_, 0.0) or 0.0)
                                cu_ = float(r.get("use", {}).get(a_, 0.0) or 0.0)
                                dp_ = ct[k_].get(f"dprod_{g}_rel")
                                du_ = ct[k_].get(f"duse_{g}_rel")
                                du_ = float(ct[k_]["dyoung_rel"]) if (du_ is None or du_ != du_) else float(du_)
                                dp_ = 0.0 if (dp_ is None or dp_ != dp_) else float(dp_)
                                Nz[i_, gi[g]] = cp_ * dp_ - cu_ * du_
                        J += Nz.T @ np.linalg.pinv(Hz) @ (Nz * v)
            gap = np.array([net.get((mr, g), 0.0) - ref[(mr, g)] for g in goods])
            # the imbalance relative to the market's production, or to a tenth of the good's production over all
            # young-animal markets where the market is smaller (Norway's: about 1% of the EU's calves, where solver
            # noise of 2 thousand heads was 0.8% and kept the outer loop from settling; REGISTERED tolerance choice)
            _tot = {g: sum(float(v_) for (m_, g_), v_ in prod.items() if g_ == g) for g in goods}
            _sms = float(_settings().get("young_animals.small_market_scale"))
            scale = np.array([max(prod.get((mr, g), 0.0), _sms * _tot[g], 1.0) for g in goods])
            worst = max(worst, float(np.max(np.abs(gap) / scale)) if len(goods) else 0.0)
            ratio = dict(ratio_m.get(mr) or {g: 1.0 for g in goods})
            try:
                d = np.linalg.solve(J, -gap)
            except np.linalg.LinAlgError:
                d = np.linalg.lstsq(J, -gap, rcond=None)[0]
            for g in goods:
                # the step is limited to 30% of the current price or of the base price, whichever is larger (d is the
                # change of the ratio; a limit relative to the current price alone could never cross zero)
                lim = float(_settings().get("young_animals.max_step")) * max(abs(ratio.get(g, 1.0)), 1.0)
                step = float(np.clip(self.YANI_RELAXATION * d[gi[g]], -lim, lim))
                ratio[g] = float(np.clip(ratio.get(g, 1.0) + step, lo, hi))
            ratio_m[mr] = ratio
        self._yani_imbalance = worst
        self._publish_young_animal_prices(ratio_m, ref, net, prod, markets)

    def _yani_in_market_now(self) -> bool:
        """The young-animal markets are cleared inside the market (CAPRI's yaniMarket_ with the market's supply
        functions): with CAPRI's market supply functions (market.market_supply_nq) built and one EU market (the trade
        blocks keep the price update between solves)."""
        mm = self.market_module
        hs = getattr(mm, "supply_hessian", None) or {}
        h_eu = hs.get("eu")
        return (bool(getattr(self, "market_supply_nq", False))
                and not getattr(mm, "eu_blocks", False) and h_eu is not None and len(h_eu)
                and any(str(x).startswith("YANI:") for x in h_eu.index))

    def _young_animal_state_to_market(self, supply_results, ref) -> None:
        """The supply models' young-animal state for the market's clearing (CAPRI simu_calibration_to_supply.gms
        l. 166-175, 360-368: the market's young-animal net supply recalibrated to the supply models' latest solution):
        per market, each good's net balance now, its reference (the baseline's) and the price ratio those models saw;
        also the imbalance reported by the outer loop (net - reference over the market's production)."""
        net, prod = self._young_animal_balance(supply_results)
        ratio_m = dict(getattr(self.supply_module, "yani_price_ratio_m", None) or {})
        _tot = {}
        for (m_, g_), v_ in prod.items():
            _tot[g_] = _tot.get(g_, 0.0) + float(v_)
        _sms = float(_settings().get("young_animals.small_market_scale"))
        st, worst = {}, 0.0
        for mr in sorted({mr for (mr, _g) in ref}):
            goods = sorted(g for (m_, g) in ref if m_ == mr)
            for g in goods:
                sc_ = max(prod.get((mr, g), 0.0), _sms * _tot.get(g, 0.0), 1.0)
                worst = max(worst, abs(net.get((mr, g), 0.0) - ref[(mr, g)]) / sc_)
            st[mr] = {"goods": goods, "net": {g: float(net.get((mr, g), 0.0)) for g in goods},
                      "ref": {g: float(ref[(mr, g)]) for g in goods},
                      "seen": {g: float((ratio_m.get(mr) or {}).get(g, 1.0)) for g in goods},
                      "bounds": tuple(self.YANI_RATIO_BOUNDS)}
        self._yani_imbalance = worst
        self._yani_np = (net, prod)
        self.market_module._yani_state = st
        self.market_module._yani_market_now = {}

    def _capri_stop_step(self, supply_results, market_eq) -> Optional[dict]:
        """One step of CAPRI's stop rule (capri_mod.utils.capri_stop.CapriStopRule; capmod/price_forecast.gms): the
        step's production, feed use and market prices per member state. Items, as CAPRI's where the model has them:
        - production: the supply models' output bridged to the market's products per member state (kt), CAPRI's
          grof of the outputs at member-state level;
        - feed: the traded feed bulks (FCER, FPRO, FENE, FMIL, FOTH; CAPRI's FEED rows without straw and the
          non-traded fodder FODDIS, which it sets to zero) per member state, kt;
        - prices: the market's solution of the step (CAPRI's UVAG before the price forecast): the domestic prices of
          the member state's market region (EU27 or its trade block; Norway's own), EUR/t; raw milk per member state:
          the EU's raw milk price x its dairy block's price relative to the EU's (the member states' own base milk
          price levels are not at hand: they matter only for the aggregate's weights and the EUR 0.05 filter); young
          animals as the market's price ratios (no price level at hand, so CAPRI's EUR 0.05 filter is not applied to
          them; they are out of the step's maximum as in CAPRI). Departures: one price per market region for every
          member state in it, where CAPRI has each member state's price; the aggregates are CAPRI's trade blocks EU_West and EU_East
          (capri_data/shared/eu_market_blocks.csv) - EU015000 and WBA, also in CAPRI's REGAGGU, are not used.
        Returns the step's verdict, or None when the items cannot be formed."""
        from capri_mod.data.definitions import capri_ms
        from capri_mod.utils.capri_stop import CapriStopRule
        if not supply_results:
            return None
        if getattr(self, "_capri_stop", None) is None:
            blocks = read_csv(Path(getattr(self, "data_dir", None) or Path(__file__).resolve().parents[1] / "capri_data") / "shared" / "eu_market_blocks.csv")
            aggs = {b: list(g["ms"]) for b, g in blocks.groupby("block")}
            self._capri_stop = CapriStopRule(aggs, yani_rows=(), no_abs_price_rows=())
        rule = self._capri_stop
        # production per member state (kt)
        q = self._bridge_supply_to_market(self.supply_module.aggregate_supply(supply_results, by_country=True)).fillna(0.0)
        prod = {}
        for cc, row in q.iterrows():
            d = prod.setdefault(capri_ms(cc), {})
            for c, v in row.items():
                if float(v) > 0:
                    d[str(c)] = d.get(str(c), 0.0) + float(v)
        # feed use per member state (kt): the traded feed bulks
        traded = ("FCER", "FPRO", "FENE", "FMIL", "FOTH")
        feed = {}
        for r_, res in supply_results.items():
            ft = getattr(res, "feed_t", None) or {}
            d = feed.setdefault(capri_ms(r_), {})
            for _a, bulks in ft.items():
                for b_, t_ in (bulks or {}).items():
                    if b_ in traded:
                        d[b_] = d.get(b_, 0.0) + float(t_) / 1000.0
        # the market's prices per member state (EUR/t, young animals as ratios): its domestic prices of the step
        # (the member state's trade block, or Norway's market), raw milk per member state from its dairy block
        dp = getattr(market_eq, "domestic_prices", None) if market_eq is not None else None
        if dp is None or not len(dp):
            return None
        _mmk = self.market_module
        bmap = _mmk._ms_block_map() if getattr(_mmk, "eu_blocks", False) else {}
        _smap = getattr(_mmk, "SUP_NONEU_MS", {}) or {}
        ms_reg = {capri_ms(v): k for k, v in _smap.items()}            # Norway's market region
        eu_reg = [r_ for r_ in _mmk.EU if r_ in dp.index]
        price = {}
        for ms in prod:
            rg = ms_reg.get(ms) or bmap.get(ms) or (eu_reg[0] if len(eu_reg) == 1 else None)
            if rg is None or rg not in dp.index:
                continue
            price[ms] = {str(c): float(v) for c, v in dp.loc[rg].items() if v == v and float(v) > 0}
        _dl = getattr(_mmk, "_dairy_last", None) or {}
        _eu = float((_dl.get("price_ratio") or {}).get("MILK", 0.0) or 0.0)
        if _eu > 0:
            for ms, v in (_dl.get("ms_price_ratio") or {}).items():
                if ms in price and "MILK" in price[ms]:
                    price[ms]["MILK"] = price[ms]["MILK"] * float(v["MILK"]) / _eu
        ya = getattr(self.market_module, "_yani_market_now", None) or {}
        yrows = set()
        for mr, d in ya.items():
            for g, rt in d.items():
                yrows.add("YANI:" + g)
                for ms in price:
                    if (mr == "NOR") == ms.startswith("NO"):
                        price[ms]["YANI:" + g] = float(rt)
        rule.yani_rows |= yrows
        rule.no_abs_price_rows |= yrows
        return rule.record(prod, feed, price)

    @staticmethod
    def _capri_price_update() -> bool:
        """outer_loop.price_update = "capri": every price passed to the supply models is CAPRI's price forecast
        (capmod/define_stepWeights.gms, price_forecast.gms l. 376-397) instead of the adaptive step."""
        return str(_settings().get("outer_loop.price_update")) == "capri"

    @staticmethod
    def _capri_forecast(hist, outer_iter):
        """CAPRI's price forecast: the weighted average of the market's prices of the last steps, newest last in
        hist; 0.55 / 0.30 / 0.15, from the 20th step 0.4 / 0.3 / 0.2 / 0.1 (define_stepWeights.gms), normalised over
        the steps available. Works on floats and on pandas Series alike."""
        st = _settings()
        w = tuple(st.get("outer_loop.capri_step_weights")
                  if outer_iter + 1 < int(st.get("outer_loop.capri_step_weights_late_from"))
                  else st.get("outer_loop.capri_step_weights_late"))
        use = list(reversed(hist))[:len(w)]
        tot = sum(w[:len(use)])
        out = None
        for w_, v_ in zip(w, use):
            out = w_ * v_ if out is None else out + w_ * v_
        return out / tot

    @staticmethod
    def _capri_special_forecast(hist, srt):
        """CAPRI's slower smoothing for a problem product (define_stepWeights.gms l. 41-50, price_forecast.gms
        l. 384-386): at step k the weight of step j is max(0, 1 - srt (k + 1 - j)) for j = 0 (TRD, the baseline: signal
        0) to k, normalised; hist holds the market's prices of steps 1..k, newest last (floats or Series)."""
        k = len(hist)
        vals = [0.0 * hist[0]] + list(hist)
        w = [max(0.0, 1.0 - float(srt) * (k + 1 - j)) for j in range(k + 1)]
        tot = sum(w)
        out = None
        for w_, v_ in zip(w, vals):
            out = w_ * v_ if out is None else out + w_ * v_
        return out / tot

    @staticmethod
    def _capri_step_special() -> dict:
        """outer_loop.capri_step_special as {(member state, product): srt}, as CAPRI's p_stepWgtSpecial(ms, product,
        "srt")."""
        out = {}
        for e in (_settings().get("outer_loop.capri_step_special") or []):
            rg, pr, srt = str(e[0]), str(e[1]), float(e[2])
            if not (0.0 < srt < 1.0):
                raise ValueError(f"outer_loop.capri_step_special {e!r}: srt in (0, 1)")
            if not (len(rg) == 8 and rg.endswith("000000")):
                raise ValueError(f"outer_loop.capri_step_special {e!r}: a member state as CAPRI (e.g. MT000000)")
            out[(rg, pr)] = srt
        return out

    def _young_animal_prices_from_market(self, ref) -> None:
        """The young-animal prices the market cleared, passed to the supply models with the same adaptive step as the
        products' prices (CAPRI passes every market price on through its price forecast, define_stepWeights.gms)."""
        now = getattr(self.market_module, "_yani_market_now", None) or {}
        if not now:
            return
        ratio_m = {k: dict(v) for k, v in (getattr(self.supply_module, "yani_price_ratio_m", None) or {}).items()}
        w_ = getattr(self, "_yani_w", None) or {}
        gp_ = getattr(self, "_yani_gprev", None) or {}
        _st = _settings()
        for mr, d in now.items():
            cur = ratio_m.setdefault(mr, {})
            for g, r_t in d.items():
                r0 = float(cur.get(g, 1.0))
                gap = float(r_t) - r0
                w = float(w_.get((mr, g), self.PRICE_SIGNAL_RELAXATION))
                if (mr, g) in gp_:
                    w = (max(_st.get("outer_loop.relax_floor"), w * _st.get("outer_loop.relax_step_down"))
                         if gap * gp_[(mr, g)] < 0 else min(self.PRICE_SIGNAL_RELAXATION, w * _st.get("outer_loop.relax_step_up")))
                w_[(mr, g)], gp_[(mr, g)] = w, gap
                if self._capri_price_update():
                    # CAPRI's price forecast on the young-animal prices the market cleared
                    yh = self.__dict__.setdefault("_capri_yani_hist", {})
                    yh[(mr, g)] = ((yh.get((mr, g)) or []) + [float(r_t)])[-4:]
                    cur[g] = float(self._capri_forecast(yh[(mr, g)], int(getattr(self, "_outer_iter_now", 0))))
                else:
                    cur[g] = r0 + w * gap
        self._yani_w, self._yani_gprev = w_, gp_
        net, prod = getattr(self, "_yani_np", ({}, {}))
        self._publish_young_animal_prices(ratio_m, ref, net, prod, sorted({mr for (mr, _g) in ref}))

    def _publish_young_animal_prices(self, ratio_m, ref, net, prod, markets) -> None:
        """Hand the young-animal prices of each market ({market: {good: ratio}}) to the supply models: per member
        state where markets are per trade block or Norway's, and the EU's production-weighted average otherwise."""
        sm = self.supply_module
        sm.yani_price_ratio_m = ratio_m
        # each member state's models see their market's prices; the EU average (production-weighted) for reporting
        bmap = self.market_module._ms_block_map() if getattr(self.market_module, "eu_blocks", False) else {}
        sm.yani_price_ratio_ms = {ms: ratio_m[rg] for ms, rg in bmap.items() if rg in ratio_m} if bmap else None
        # Norway's models: Norway's young-animal market (CAPRI yaniMarket_ per RM; K56)
        _smap = getattr(self.market_module, "SUP_NONEU_MS", {}) or {}
        _sms = {_smap[rg]: ratio_m[rg] for rg in _smap if rg in ratio_m}
        if _sms:
            sm.yani_price_ratio_ms = {**(sm.yani_price_ratio_ms or {}), **_sms}
        ratio = {}
        eu_markets = [m_ for m_ in markets if m_ not in _smap]
        for g in sorted({g for (_m, g) in ref}):
            # the EU's young-animal prices (its regions without a member-state entry above): EU markets only
            w = [(max(prod.get((m_, g), 0.0), 0.0), ratio_m.get(m_, {}).get(g, 1.0)) for m_ in eu_markets]
            if not w:
                continue
            ws = sum(x for x, _ in w)
            ratio[g] = sum(x * r_ for x, r_ in w) / ws if ws > 0 else float(np.mean([r_ for _, r_ in w]))
        sm.yani_price_ratio = ratio
        self._yani_detail = {f"{mr}|{g}": (round(float(ratio_m.get(mr, {}).get(g, 1.0)), 4),
                                            round(float(net.get((mr, g), 0.0) - ref[(mr, g)]), 2),
                                            round(float(prod.get((mr, g), 0.0)), 2))
                             for (mr, g) in ref}
        self._yani_trace.append({"ratio": dict(ratio), "imbalance": self._yani_imbalance, "markets": self._yani_detail})
        if self.verbose or getattr(self, "trace_outer", False):
            print("    [Young animals] imbalance %.4f | (ratio, net - ref, production) %s" % (
                self._yani_imbalance, self._yani_detail), flush=True)

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
        4.0, then 2.3 x supply). The connected equilibrium is solved as the PRIMAL
        Takayama-Judge problem on these schedules (shipments between pools at CAPRI's
        trade costs c_kl, each pool's exports and imports on its schedule; a convex QP
        solved with the model's own solver). The dual price problem
        (min_p sum_k Phi_k(p_k) s.t. p_k - p_l <= c_kl) was solved with SLSQP before and
        failed on the schedules' kinks.
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
            # row duals: the regional NLP's own multipliers (its feed block is not in the stored
            # problem, so duals recovered from the stored problem's KKT conditions were wrong and the
            # pools stopped clearing); else recovered by NNLS from the active rows of the stored problem
            zc = getattr(mo, "_last_duals", None)
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
            rc_ = getattr(mo, "_nlp_rc", None)
            if rc_ is not None and max(je, ji) < len(rc_):
                # the NLP form: IPOPT's own reduced costs (the fertilisation block is not in the stored A rows)
                rce, rci = max(0.0, float(rc_[je])), max(0.0, float(rc_[ji]))
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
                if abs(planned) > _settings().get("outer_loop.manure_pool_min_plan") * max(sup.get(k, 0.0), 1.0):
                    _klo, _khi = _settings().get("outer_loop.manure_pool_kappa_bounds")
                    kappa[k] = float(np.clip(kappa.get(k, 1.0) * realised / planned, _klo, _khi))
        hist["_kappa"] = kappa
        self._pool_state = hist
        _ratios = {k: (abs(es[k] - plan.get(k, 0.0)) if plan else abs(es[k])) / sup[k] for k in keys}
        worst = max(_ratios.values())
        self._pool_worst_key = max(_ratios, key=_ratios.get)
        # ---- PRIMAL spatial equilibrium on the exact schedules (shipment side),
        # solved with the model's own exact QP solver (the dual price problem
        # with SLSQP failed on the kinks and kept stale prices).
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
        # Interior point (Clarabel, capri_mod/supply/convex_qp.py). An active-set loop
        # failed on the full EU (iteration limit; the balance written as two tight
        # inequalities made its KKT systems singular).
        from capri_mod.supply.convex_qp import solve_convex_qp
        # Scaled: objective by its largest coefficient (prices reach hundreds of EUR/kg N under
        # CAPRI's land rules, slopes differ by orders of magnitude after the kappa correction).
        # Clarabel's AlmostSolved (reduced accuracy) is accepted - the pool test below checks
        # the realised clearing anyway; a failed solve keeps the old prices and is reported.
        _sc = max(float(np.abs(cp_).max()), float(np.abs(Qp).max()), 1e-9)
        sol, ok, _info = solve_convex_qp(Qp / _sc, cp_ / _sc, Ap, bp, np.array(eqs), np.array(eqb),
                                         tol=float(_settings().get("outer_loop.manure_pool_qp_tol")))
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
            _st_ = _settings()
            om = (min(1.0, om * _st_.get("outer_loop.manure_pool_omega_up")) if cur_gap < prev_gap
                  else max(_st_.get("outer_loop.manure_pool_omega_min"), om * _st_.get("outer_loop.manure_pool_omega_down")))
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
            fmil = [0.0, 0.0]                       # feed from milk products (FMIL): now, base (the EU's)
            fmil_sup = {}                           # the same for Norway's dairy block (own market region, K56)
            _sup_of = getattr(mm, "sup_region_of_country", lambda c: None)
            for region, res in supply_results.items():
                ms = self.member_state_of(region)
                _srg = _sup_of(region)
                _fm = fmil if _srg is None else fmil_sup.setdefault(_srg, [0.0, 0.0])
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
                            _fm[0] += (_ft.get("FMIL", 0.0) if _ft is not None else x * _rr["x"].get("FMIL", 0.0)) / 1000.0
                            _fm[1] += x0 * xb["FMIL"] / 1000.0
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
                    for c in ("SWHE", "BARL", "CORN", "RYEM", "OATS", "OCER"):
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
            mm._fmil_index_sup = {rg: (v[0] / v[1] if v[1] > 0 else 1.0) for rg, v in fmil_sup.items()}
        except Exception:
            mm._feed_bulk_index = None

    #: CAPRI's tradable feed bulks (global/fromimpact/sets.gms FEED_TRD), priced by the market (feedBlkPrice_)
    FEED_BULKS = ("FCER", "FPRO", "FENE", "FOTH", "FMIL")

    #: CAPRI final product -> market commodity (tools/build/build_livestock_products.py)
    LIVESTOCK_PRODUCT_MARKET = {"COMI": "MILK", "SGMI": "MILK", "BEEF": "BEEF", "PORK": "PORK",
                                "POUM": "POUL", "EGGS": "EGGS", "SGMT": "SGMT"}

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
            "CORN": "CORN", "OCER": "OCER", "RYEM": "RYEM", "OATS": "OATS", "RAPE": "RAPE",
            "SUNF": "SUNF", "SOYA": "SOYA",
            "POTA": "POTA", "PULS": "PULS",
            "TOMA": "TOMA", "OVEG": "OVEG", "APPL": "APPL",
            "OFRU": "OFRU", "CITR": "CITR", "TAGR": "TAGR", "TOBA": "TOBA", "TABO": "TABO", "TEXT": "TEXT", "WINE": "WINE",
            # (wheat, olives and paddy rice are bridged below, as CAPRI's wheat, olive oil and milled rice)
        }
        # LIVESTOCK (milk is handled by the dairy block below). The meat markets
        # meat, milk and egg supply never moved with the herds: under
        # Farm-to-Fork pig supply fell ~10% while the pork price changed by
        # exactly 0.0% (CAPRI: +43%). Each product is the sum of the
        # activities producing it, from their marketed gross output.
        # The model's own animal codes (definitions.ANIMALS): BCOW suckler cows,
        # HFRS heifers, PIGF a second pig activity, SHGM / SHGF sheep and goats. An
        # earlier version of this map used HEIF/SCOW/SOWS/SHEP/GOAT, which do not
        # exist here, so beef came from bulls and calves only, pork from one pig
        # activity of two, and sheep and goat meat got nothing.
        livestock_maps = {
            "BEEF": ("BULL", "BCOW", "HFRS", "CALV"),
            "PORK": ("PIGS", "PIGF"),
            "POUL": ("BROI",),
            "EGGS": ("LAYS",),
            "SGMT": ("SHGM", "SHGF"),
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
        # rye (RYEM) and oats (OATS) are markets of their own, as in CAPRI (arm/arm_sets.gms CERE_DEF)

        # Oilseeds: the seeds go to the seed markets; oil and cake come from crushing in the market.
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
        # (tools/build/build_sugar_processing.py). Beet has no market of its own; its price follows the sugar price.
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
            # x 0.9575 and left sheep and goat milk in the sheep-meat market (that stand-in, never reached, removed
            # 23 October 2026: without the product split the run stops)
            if _lsc is None or "MILK" not in _lsc.columns:
                raise ValueError("raw milk needs CAPRI's product split of the animals' output "
                                 "(livestock_output_by_product_coef.csv)")
            milk = _lsc["MILK"].reindex(market_supply.index).fillna(0.0)
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
    _CAPRI_MS = MS_CODE

    def _dairy_yield(self, region: str, product: str) -> float:
        """A dairy product's output less processing per tonne of raw milk (cow + sheep and goat) in the
        region's member state, CAPRI 2030 reference (dairy_processing.csv; Norway: dairy_world_processing.csv, per
        tonne of raw milk delivered); EU ratio where CAPRI has no dairy data for the member state."""
        tab = getattr(self, "_dairy_yield_cache", None)
        if tab is None:
            from pathlib import Path
            from capri_mod.data.loaders import resolve_data_file
            base = Path(getattr(self, "data_dir", None) or Path(__file__).resolve().parents[1] / "capri_data")
            f = resolve_data_file(base, "dairy_processing.csv")
            dp = read_csv(f)
            net = (dp["q_kt"].fillna(0.0) - dp["proc_kt"].fillna(0.0))
            dp = dp.assign(net=net)
            raw = dp[dp["item"].isin(["COMI", "SGMI"])].groupby("ms")["q_kt"].sum()
            tab = {}
            for k in ("BUTT", "SMIP", "CHES", "WHEP", "FRMI", "CREM", "COCM", "WMIO", "CASE"):
                q = dp[dp["item"] == k].set_index("ms")["net"]
                tab.update({(ms, k): float(q.get(ms, 0.0)) / float(raw[ms]) for ms in raw.index if raw[ms] > 0})
                tab[("_EU", k)] = float(q.sum()) / float(raw.sum())
            # Norway's dairies (its own market region since K56: CAPRI's NO000000 block, dairy_world_processing.csv):
            # output less processing per tonne of raw milk delivered (MILK), CAPRI 2030 reference
            fw = resolve_data_file(base, "dairy_world_processing.csv")
            if fw.exists():
                wp_ = read_csv(fw)
                for ms in ("NO000000",):
                    g = wp_[wp_["rms"] == ms].set_index("item")
                    if "MILK" in g.index and float(g.at["MILK", "q_kt"]) > 0:
                        for k in ("BUTT", "SMIP", "CHES", "WHEP", "FRMI", "CREM", "COCM", "WMIO", "CASE"):
                            if k in g.index:
                                tab[(ms, k)] = float(g.at[k, "q_kt"] - (g.at[k, "proc_kt"] if pd.notna(g.at[k, "proc_kt"])
                                                                       else 0.0)) / float(g.at["MILK", "q_kt"])
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
            py = read_csv(f)
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
        raise RuntimeError("sugar_processing.csv missing: run tools/build/build_sugar_processing.py")

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

    def get_reporter(self, results: Dict) -> ResultsReporter:
        """Get a ResultsReporter for exporting results."""
        return ResultsReporter(results)


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
