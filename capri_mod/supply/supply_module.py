"""
CAPRI Supply Module
===================
Regional non-linear programming (NLP) models for ~280 EU NUTS-2 regions.

Mathematical structure follows CAPRI exactly:
  max  π = p'x - c(x)
       s.t.
       Ax ≤ b          (land, feed, nutrient constraints)
       x ≥ 0

where:
  x   = activity levels (ha for crops, heads for animals)
  p   = activity net revenues (producer price × yield - variable cost + CAP payment)
  c(x)= quadratic cost function: c(x) = ½ x'Qx + f'x
  A   = constraint matrix
  b   = constraint RHS

The quadratic cost matrix Q is calibrated using Positive Mathematical
Programming (PMP, Howitt 1995) extended with CAPRI's cross-commodity
calibration (Britz & Witzke 2008).

Reference: Britz, W. & Witzke, H.P. (2012). CAPRI Model Documentation 2012.
           University of Bonn. Chapter 4 (Supply Module).
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple
import multiprocessing
import os
import warnings
from pathlib import Path

from capri_mod.supply.capri_pmp import (
    share_term, ARABLE_ACTIVITIES,
)
from capri_mod.params import param, param_table
from capri_mod.units import M_N2O, M_N2O_N
from capri_mod.settings import setting, tri_state, current as _settings
from capri_mod.data.definitions import (
    CROPS, ANIMALS, ALL_ACTIVITIES, FEED_ITEMS, NUTRIENTS, ACTIVITY_CLASSES, CROPS_ON_LAND, LAND_MARKET_TYPES, CATTLE_SPLITS,
)
from capri_mod.data.definitions import MS_CODE, capri_ms, IdentityMap, is_eu
from capri_mod.tableio import read_input
from capri_mod.supply import inputs as _inputs
from capri_mod.market.equations.set_prices import DATA_UVAG_Y
from capri_mod.supply.equations.greendeal.landscape import DATA_FALL_FLOOR
from capri_mod.supply.equations.greendeal.surptot import data_SURTOT_MAXS
from capri_mod.supply.equations.set_supply_bounds import v_actLevl_up_FALL
from capri_mod.supply.equations.ghgmiti import (
    p_ghgMiti_othImpact_EmiCalmin, p_ghgMiti_pmpParsqr, p_ghgMiti_pmpParsqr_saving, p_ghgMiti_relSubs)



from capri_mod.supply.state import ModuleStateMixin, RegionalStateMixin  # noqa: E402,F401
from capri_mod.supply import state as _st  # noqa: E402
from capri_mod.supply.regional_supply.tables import (  # noqa: E402,F401  the parts (moved as they were)
    FIXED_ACTIVITIES, _n_techn, overfert_factor, fert_option_table, manure_trade_terms, _spec_fingerprint,
    young_animal_table, active_technologies, fert_efficiency_cap, _csv_dict, _InputColumn, RegionData,
    SupplyResult, _luc_of, _mineral_n_for_accounts, _merge_relief, fert_side_table, fert_side_value)
from capri_mod.supply.regional_supply.pmp_calibrator import (  # noqa: E402,F401  the parts (moved as they were)
    saving_slope, PMPCalibrator)
from capri_mod.supply.regional_supply.regional_model import (  # noqa: E402,F401  the parts (moved as they were)
    RegionalSupplyModel)
from capri_mod.supply.regional_supply.net_revenues import (  # noqa: E402,F401  the parts (moved as they were)
    NetRevenuesBlock)
from capri_mod.supply.regional_supply.constraints import (  # noqa: E402,F401  the parts (moved as they were)
    ConstraintsBlock)
from capri_mod.supply.regional_supply.solve import (  # noqa: E402,F401  the parts (moved as they were)
    SolveBlock)
from capri_mod.supply.regional_supply.region_build import (  # noqa: E402,F401  the parts (moved as they were)
    _region_nutrients, _region_prices, _region_costs, _capri_ms_targets, _landscape_pp, RegionBuildBlock)
from capri_mod.supply.regional_supply.n_balances import (  # noqa: E402,F401  the parts (moved as they were)
    NBalancesBlock)
from capri_mod.supply.regional_supply.region_loop import (  # noqa: E402,F401  the parts (moved as they were)
    _PAR_CTX, _kill_pool_workers, _InputsUnchanged, _par_solve_region, RegionLoopBlock)


class SupplyModule(RegionBuildBlock, NBalancesBlock, RegionLoopBlock, ModuleStateMixin):
    """
    Manages and runs all regional supply models in parallel.

    In the iterative supply-market loop, this module receives
    market prices from the MarketModule and returns aggregate
    supply quantities.
    """

    #: "recipe": capri-mod's own terms computed with CAPRI's recipe (tools/build/build_pmp_recipe.py) for the market year (2017
    #: or 2030); at 2030 with CAPRI's 2030 feed slopes and land-type terms (their own calibrations are not ported).
    #: the PMP terms at the 2030 market year: "capri2030" (CAPRI's own terms of its 2030 baseline calibration, K61:
    #: crops' p_pmpQuadTechn and p_pmpQuadPact, animals' herd terms, feed-PMP slopes, land-type terms; the default since
    #: 22 October 2026, the project lead's decision); at 2017 CAPRI's recipe at CAPRI's 2017 point. "elasticity"
    #: (calibrated per activity from CAPRI's supply elasticities) was removed on 28 October 2026 (the supply audit's finding S13, ARCHITECTURE_REFACTOR.md section 5.2).
    pmp_source = setting("supply.pmp_source")
    #: which of CAPRI's 2030 terms "capri2030" uses: the crops' matrix, the animals' herd terms, the feed-PMP slopes,
    #: the land market's land-type terms (all by default; subsets for diagnosis, run script --pmp-parts)
    pmp_capri_parts = setting("supply.pmp_capri_parts", tuple)
    #: CAPRI's land market, the grassland allowance, the JRC121368 capped regions override (settings supply.*)
    use_land_market = setting("supply.use_land_market")
    grassland_allowance = setting("supply.grassland_allowance")
    jrc_capped_override = setting("supply.jrc_capped_override")

    #: JRC121368 sect. 4.3.4: the nine regions with the highest baseline gross
    #: nitrogen balance (high animal numbers) had their reduction target set to
    #: the EU average cut, 36%, because the tiered target was infeasible there (the parameters JRC_CAPPED_N_REGIONS,
    #: JRC_CAPPED_CUT, read where used).

    def _jrc_capped_regions(self, cs) -> set:
        """The nine regions with the highest CAPRI baseline N surplus per ha."""
        got = getattr(self.par, "jrc_capped_cache", None)
        if got is None:
            try:
                col = cs["surplus_kg_n_per_ha"].dropna()
                got = set(col.sort_values(ascending=False).index[: int(param("JRC_CAPPED_N_REGIONS"))])
            except Exception:
                got = set()
            # sensitivity only (tools/run/run_f2f_2030.py --capped-regions): the report does not
            # name the nine regions; '+A,B' adds to them, 'A,B' replaces them
            ov = str(getattr(self, "jrc_capped_override", "") or "")
            if ov:
                extra = {x.strip() for x in ov.lstrip("+").split(",") if x.strip()}
                got = (got | extra) if ov.startswith("+") else extra
            self.par.jrc_capped_cache = got
        return got
    def __init__(self, data: dict, supply_elasticities: Optional[pd.Series] = None,
                 inputs: Optional["_inputs.SupplyInputs"] = None):
        """CAPRI's regional elasticity estimates, with provenance tracking. inputs: the run's data directory and base
        year (capri_mod/supply/inputs.py; the repository's data and 2017 by default), made the supply code's inputs."""
        self.data = data
        self.inputs = _inputs.use(inputs if inputs is not None else _inputs.SupplyInputs())
        # the calibration year of the data set (2030 for a projected one): the young-animal coefficients of that year
        # (young_animal_table, K178)
        self.inputs.market_year = _inputs.market_year(data)
        self.regions = list(data["areas"].index)

        if supply_elasticities is None:
            # no literature defaults (23 October 2026): CAPRI's own values come from build_elasticity_table below
            supply_elasticities = pd.Series(float("nan"), index=list(ALL_ACTIVITIES))
        self.supply_elasticities = supply_elasticities

        # Region x activity elasticities with explicit provenance.
        #
        # Two CAPRI sources are merged: supply_elasticities_regional.csv (already
        # bounded upstream at 4.5) takes precedence over pmp_own_price_elasticities.csv
        # (raw, keyed by CAPRI region codes, dampened on load). The latter is
        # resolved through the NUTS crosswalk, which is why it reaches regions the
        # former misses. Everything not covered falls back to the EU-wide literature
        # defaults, and every cell is recorded so no default is silent.
        from capri_mod.supply.capri_pmp import build_elasticity_table
        self.elasticity_provenance = pd.DataFrame()
        self.elasticity_summary: dict = {}
        eps_tab, prov, summary = build_elasticity_table(
            self.inputs.root, self.regions, ALL_ACTIVITIES, self.supply_elasticities,
            base_areas=data.get("areas"), base_year=self.inputs.base_year, inputs=self.inputs)
        self.regional_elasticities = eps_tab
        self.elasticity_provenance = prov
        self.elasticity_summary = summary

        self._models: Dict[str, RegionalSupplyModel] = {}

    def set_mitigation_scope(self, settings) -> None:
        """CAPRI's switches that extend an EU mitigation option to every supply region (capri_mod/policy/endotech.py):
        %fallowInAllRmssup% for histosol fallowing (no_histosols.gms rmssup_histo), %winterCovInAllRmssup% for the
        winter cover (cover_crops.gms); and %ghgTechAmmEndog%, the animals' ammonia options as choices (1) or at their
        initial shares (0; set_miti_bounds.gms l. 209-211)."""
        fal, wc = float(settings["fallowInAllRmssup"]) > 0, float(settings["winterCovInAllRmssup"]) > 0
        amm = float(settings.get("ghgTechAmmEndog", 0.0)) > 0
        # kept for the regional models built later (_get_or_build_model): a run's first call comes before its
        # models exist, and they then took the global settings' values (found 21 November 2026: the Farm-to-Fork
        # run's ammonia options at their initial shares, its ghgTechAmmEndog 1 not applied; KNOWN_ISSUES K192)
        self.par.mitigation_scope = (fal, wc, amm)
        for m in self._models.values():
            self._set_mitigation_scope_of(m)

    def _set_mitigation_scope_of(self, m) -> None:
        """The run's endotech switches (set_mitigation_scope) on one regional model; nothing before they are set."""
        scope = getattr(self.par, "mitigation_scope", None)
        if scope is None:
            return
        m.seen.fallow_in_all_rmssup, m.seen.wintercov_in_all_rmssup, m.seen.amm_endog = scope

    def set_genetics_effects(self, table: Optional[dict], settings_key: tuple) -> None:
        """Cattle genomics at the run's technology settings (capri_mod/policy/endotech.py). Each regional model
        keeps its genomics calibration (the linear cost terms taken from the base duals) per settings, so a
        scenario compared with the baseline of the same settings uses the calibration of that baseline."""
        self.data["genetics_effects"] = table
        self.par.genetics_key = settings_key
        for region, m in self._models.items():
            store = _st.setdefault(m.par, "genet_cz_store", {})
            old = getattr(m.par, "genet_key", None)
            if old == settings_key:
                continue
            if old is not None:
                store[old] = getattr(m.par, "genet_cz", None)
                # the NLP form's calibration (CAPRI's: the base a first-order point of the model it is simulated with)
                # belongs to the settings too: the genomics columns differ with them. Kept per settings and restored,
                # so a baseline after a run at other settings uses its own calibration, not the other one (found
                # 20 October 2026: after an ghgTechMYld 0.2 run, IE04's default baseline adopted genet_eff for the
                # whole herd)
                cal_store = _st.setdefault(m.par, "nlp_cal_store", {})
                cal_store[old] = (getattr(m.par, "nlp_cal", None), getattr(m.par, "nlp_base_alloc", None))
                m.par.nlp_cal, m.par.nlp_base_alloc = cal_store.get(settings_key, (None, None))
            m.data.genetics_effects = (table or {}).get(region)
            m.par.genet_cz = store.get(settings_key)
            m.par.genet_pending = None
            m.res.last_genet_z = {}
            m.par.genet_key = settings_key


    def aggregate_supply(
        self,
        results: Dict[str, SupplyResult],
        by_country: bool = False,
    ) -> pd.DataFrame:
        """
        Aggregate gross outputs across all regions (1000 t).

        Returns DataFrame [region × activity] or [country × activity].
        """
        from capri_mod.data.definitions import REGION_TO_COUNTRY

        rows = {}
        for region, res in results.items():
            key = REGION_TO_COUNTRY.get(region, region) if by_country else region
            if key not in rows:
                rows[key] = res.gross_output.copy()
            else:
                rows[key] = rows[key].add(res.gross_output, fill_value=0)

        return pd.DataFrame(rows).T

    def aggregate_farm_income(
        self,
        results: Dict[str, SupplyResult],
    ) -> pd.Series:
        """Total gross margin (EUR 1000) by region."""
        return pd.Series({r: res.gross_margin for r, res in results.items()})


# the parts that name SupplyModule in their code (its activities' price sources) get it here, where it is defined:
# an import there would be circular
from capri_mod.supply.regional_supply import net_revenues as _p_nr, regional_model as _p_rm  # noqa: E402
_p_nr.SupplyModule = SupplyModule
_p_rm.SupplyModule = SupplyModule


# the refactor's split into block mixins: the mixin modules' methods see this module's names (capri_mod/utils/mixins.py)
from capri_mod.utils.mixins import inject_names as _inject_names  # noqa: E402
_inject_names(globals(), ["capri_mod.supply." + _m for _m in ("livestock", "fertilisation", "abatement", "policy",
                                                              "land", "nlp", "techn_mix")]
              # and this module's parts (26 November 2026), whose code came from here
              + ["capri_mod.supply.regional_supply." + _m for _m in ("tables", "pmp_calibrator", "regional_model",
                                                                     "net_revenues", "constraints", "solve",
                                                                     "region_build", "n_balances", "region_loop")])
