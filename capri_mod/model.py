"""
CAPRI-mod: Main Model Coordinator
=====================================
Top-level class that orchestrates the supply-market iteration loop,
connecting all modules:

  PolicyModule → SupplyModule → MarketModule → EnvironmentalModule
       ↑_______________(price feedback)_____________________|

The iterative loop follows CAPRI's original GAMS implementation:
  1. Policy module computes CAP payment rates (tariff changes act in the market's import prices)
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
from capri_mod.supply import state as _sst   # the supply's state objects
from capri_mod.data.inputs import market_year as _mkt_year   # the market year, else the base year (K52f)
from capri_mod.market.market_module import MarketModule
from capri_mod.policy.policy_module import PolicyModule, PolicyScenario
from capri_mod.environmental.environmental_module import EnvironmentalModule
from capri_mod.utils.utils import (
    calibrate_supply_elasticities, ConvergenceTracker, ResultsReporter
)
from capri_mod.scenarios.scenarios import get_scenario, list_scenarios
from capri_mod.params import param, param_table
from capri_mod.settings import setting, tri_state, current as _settings
from capri_mod.data.definitions import MS_CODE, capri_ms, REGION_TO_COUNTRY, EU_MS_BLOCK, sup_noneu, is_eu as _is_eu
from capri_mod.data.definitions import PRICE_FOLLOWS_EU, PRICE_FOLLOWS_ALL, PRICE_FOLLOWS_SHARE, CAPRI_FEED_TRD
from capri_mod.market.equations.set_prices import DATA_UVAG_DWHE
from capri_mod.tableio import read_input
from capri_mod.policy.premium_response import merge as _merge_premium_factors   # the iterations' premium cut
from capri_mod import runlog as _runlog


#: Nitrates Directive ceiling on organic N application (kg N per ha of UAA)


from capri_mod.coupling import (  # noqa: E402  (the blocks)
    HessianBlock, FeedBlock, YoungAnimalBlock, PriceStepBlock, ManureBlock, BridgeBlock, ReportingBlock,
)


from capri_mod.coupling.state import ModelStateMixin  # par, sv, ev, seen, res
from capri_mod import statekit as _cst   # the state objects' helpers
from capri_mod import statekit as _cst   # the state objects' helpers

from capri_mod.coupling.run_scenario import (  # noqa: E402,F401  the parts (moved as they were)
    RunScenarioBlock)
from capri_mod.coupling.result_tables import (  # noqa: E402,F401  the parts (moved as they were)
    _luc_table, _npk_table, _set_aside_table, _labour_table, ResultTablesBlock)


class CAPRIModel(RunScenarioBlock, ResultTablesBlock, ModelStateMixin, HessianBlock, FeedBlock, YoungAnimalBlock,
                 PriceStepBlock, ManureBlock, BridgeBlock, ReportingBlock):
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
    #: CAPRI's baseline calibration in projected years (the projection layer at CAPRI's reference): largest remaining drift of a regional activity
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
        # The base year is a parameter of the run (KNOWN_ISSUES K52f, 2 November 2026): every reader takes it from
        # the run's inputs. A base year without a data folder stops here, naming the years that have one (2030 runs
        # go through the projection layer, ProjectionModule, on the base year's data).
        if base_year is None:
            base_year = str(_settings().get("run.base_year"))
        base_year = str(base_year)
        if data is None:
            from capri_mod.data.inputs import check_base_year as _check_by
            _check_by(data_dir, base_year)
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

        # The run's supply regions: the EU's units and those of the run's supply-model countries outside the EU
        # (definitions.sup_noneu, the setting run.supply_countries_outside_eu; CAPRI's per-country switches). The data
        # may hold units of other countries; they are left out, as CAPRI leaves out a country switched off.
        _sel = sup_noneu()
        _all = [str(r) for r in self.data["areas"].index]
        _miss = [m for m in _sel if not any(capri_ms(r) == m for r in _all)]
        if _miss:
            raise ValueError(f"run.supply_countries_outside_eu: no regional data for {_miss} (capri_data areas)")
        if not regions:
            _keep = [r for r in _all if _is_eu(r) or capri_ms(r) in _sel]
            if len(_keep) < len(_all):
                regions = _keep
                self.regions = regions

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
        if getattr(self.par, "endotech_key", None) == k:
            return
        self.supply_module.set_mitigation_scope(settings)
        tab = scale_genetics(self.data.get("genetics_effects_unit"), settings)
        self.data["genetics_effects"] = tab
        self.supply_module.set_genetics_effects(tab, k)
        self.par.endotech_key = k

    def _ghg_coefficients(self, key) -> dict:
        """{region: coefficients} of CAPRI's emission tax at the baseline solution of this run's settings
        (capri_mod/supply/ghg_tax.ghg_coefficients), cached per baseline."""
        from capri_mod.supply.ghg_tax import ghg_coefficients
        cache = getattr(self.par, "ghg_coef_cache", None)
        if cache is None:
            cache = self.par.ghg_coef_cache = {}
        if key in cache:
            return cache[key]
        base = (getattr(self.par, "base_supply_cache", None) or {}).get(key) or {}
        rats = getattr(self.supply_module.seen, "feed_rations", None) or {}
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
        self.supply_module.seen.manure_trade_on = bool(_mt)
        if getattr(self.supply_module.par, "env_for_surplus", None) is not None:
            self.supply_module.par.env_for_surplus.set_manure_trade(bool(_mt))
        try:
            return self._run_scenario(pol_scenario, scenario, world_price_shock, custom_scenario, max_outer_iter,
                                      outer_tolerance, market_max_iter, run_environmental, run_biofuel,
                                      carbon_price, biofuel_output_scale, regions, endotech, _mt, _bm)
        finally:
            del self.use_manure_market                         # back to the setting
            del self.market_module.biofuel_markets



    # ------------------------------------------------------------------
    # SCENARIO COMPARISON
    # ------------------------------------------------------------------
    #: print a timed line per stage and outer iteration (wall clock, time since progress_t0); run scripts switch it on
    progress = False
    progress_t0: Optional[float] = None

    def _progress(self, msg: str) -> None:
        """The model's own timed line: the run log's level "detailed" (capri_mod/runlog.py)."""
        if not self.progress:
            return
        _runlog.current().detail(msg)


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


    #: CAPRI's tradable feed bulks (global/fromimpact/sets.gms FEED_TRD), priced by the market (feedBlkPrice_), in
    #: CAPRI's order (capri_data/codes/capri/FEED_TRD.csv; before 2 November 2026 FMIL stood before FOTH)
    FEED_BULKS = CAPRI_FEED_TRD

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


# the blocks' methods see this module's names (capri_mod/coupling/__init__.py)
from capri_mod import coupling as _blocks  # noqa: E402
_blocks.inject(globals())
