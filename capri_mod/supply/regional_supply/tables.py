r"""The supply's data structures and the tables read once per run (moved from capri_mod/supply/supply_module.py as they
were, 26 November 2026): CAPRI's fixed activities, the input tables' readers, RegionData, SupplyResult, the land-use and
fertiliser side tables.
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

#: the class, set by regional_model.py where it is defined (an import here would be circular)
RegionalSupplyModel = None




# ---------------------------------------------------------------------------
# DATA STRUCTURES
# ---------------------------------------------------------------------------

#: CAPRI's fixed production activities, held at their data level (supply/prep_sim.gms l. 250: v_actLevl.FX for FACT;
#: sets.gms l. 2317 FACT = MFCACT + OANI, l. 131 MFCACT = OOIL, OIND, FallGr, NURS, FLOW, OCRO, NECR). NURS, FLOW and
#: OCRO were endogenous here until 23 October 2026 (found by the proxy audit: they had no CAPRI elasticity)
FIXED_ACTIVITIES = tuple(a for a, r in ACTIVITY_CLASSES.items() if r["fixed"] == "1")   # model_activity_classes.csv


def _n_techn(activity: str) -> int:
    """CAPRI's LEVL technologies of an activity (T1 and T2 at half the level each, or T alone; model_activity_classes.csv
    technologies, checked against sim_ini_21730's p_technFact by build_code_lists): the activity bounds are per
    technology in CAPRI (set_supply_bounds.gms), the model's are their sums."""
    return int(ACTIVITY_CLASSES[activity]["technologies"])


#: an activity whose level at the calibration point is at most this (1000 ha / 1000 head) has no level: CAPRI has no
#: variable for it (v_actLevl exists where p_technFact(..,"LEVL",..) is set); the bounds hold it at zero
#: (setting supply.absent_activities_fixed) and the rules that refer to it (CAP greening) leave it out
# (the level: the setting supply.absent_level)

# CAPRI's p_OverFertMarkUp and p_fertEffCor (envind/ghgMiti.gms) and the supply's other parameters are read where they
# are used, through the run's inputs (param(): <data_dir>/codes/model_parameters.csv)


def overfert_factor(region: str):
    """CAPRI's over-fertilisation factor x = v_cropNutNeedMultFact(ru, NITF, "T") for a model
    region (capri_data/baselines/capri_greendeal_ref/1730/environment/crop_nut_need_mult_fact_2030.csv, built by
    tools/build/build_overfert_factors.py from CAPRI's priFertDist results). Every unit of the model has one
    (CAPRI's limits on the fertiliser technologies, Tot_MitFert_ and the regional maximum shares, need it): a missing
    file or region is an error (K74, 29 October 2026; before, the limits were dropped with a warning, a fallback no
    unit of the model reached)."""
    def load(inp):
        f = inp.path("crop_nut_need_mult_fact_2030.csv", "environment")
        if not f.exists():
            raise FileNotFoundError(f"CAPRI's over-fertilisation factors missing: {f} (tools/build/build_overfert_factors.py)")
        return {str(r.region): float(r.x) for r in inp.csv(f.name, "environment").itertuples(index=False)}
    x = _inputs.current().cached("overfert", load).get(region)
    if x is None:
        raise KeyError(f"{region}: no CAPRI over-fertilisation factor in crop_nut_need_mult_fact_2030.csv")
    return x






def fert_option_table() -> dict:
    """{model region: [row]} of CAPRI's fertiliser options (fert_options_jul15.csv)."""
    def load(inp):
        out = {}
        for r in inp.csv("fert_options_jul15.csv", "abatement").itertuples(index=False):
            out.setdefault(r.region, []).append(r)
        return out
    return _inputs.current().cached("fert_options", load)


def manure_trade_terms(region: str, fout: str) -> Optional[dict]:
    """CAPRI's manure trade terms of a region and nutrient (FOUT MANN, MANP, MANK) at the calibration point, in the
    model's units (manure_pool_market_2030.csv; tools/build/build_manure_pool_market.py): gross exports and imports
    e0, i0 (t), the sell and buy cost slopes (EUR 1000 per t per t) and the opening costs of the direction the region
    does not trade (EUR 1000 per t). None for a region without CAPRI's pool terms."""
    def load(inp):
        t = inp.csv("manure_pool_market_2030.csv", "environment", float_precision="round_trip")
        return {(str(r.region), str(r.fout)): {"e0": 1000.0 * float(r.base_export_kt),
                                               "i0": 1000.0 * float(r.base_import_kt),
                                               "sell_slope": float(r.sell_slope), "buy_slope": float(r.buy_slope),
                                               "open_export": float(r.open_export),
                                               "open_import": float(r.open_import)}
                for r in t.itertuples(index=False)}
    return _inputs.current().cached("manure_trade_terms", load).get((region, fout))


def _spec_fingerprint(spec, **extra) -> str:
    """A digest of a regional NLP's calibration problem (every array, number and label of the spec, and the base
    point): two calibrations of equal digests solve the same problem."""
    import hashlib
    h = hashlib.sha1()

    def feed(o):
        if isinstance(o, np.ndarray):
            a = np.ascontiguousarray(o)
            h.update(str((a.dtype.str, a.shape)).encode()); h.update(a.tobytes())
        elif isinstance(o, (pd.Series, pd.DataFrame)):
            feed(o.to_numpy()); feed(list(map(str, o.index)))
            if isinstance(o, pd.DataFrame):
                feed(list(map(str, o.columns)))
        elif isinstance(o, dict):
            h.update(b"{")
            for k in sorted(o, key=repr):
                h.update(repr(k).encode()); feed(o[k])
            h.update(b"}")
        elif isinstance(o, (list, tuple, set, frozenset)):
            h.update(b"[")
            for x in (sorted(o, key=repr) if isinstance(o, (set, frozenset)) else o):
                feed(x)
            h.update(b"]")
        elif isinstance(o, (float, np.floating)):
            h.update(np.float64(o).tobytes())
        else:
            h.update(repr(o).encode())
    feed(spec); feed(extra)
    return h.hexdigest()


def young_animal_table(year=None) -> dict:
    """CAPRI's young-animal coefficients per model region (calves, young cattle, cows, piglets, lambs): per sex as
    CAPRI's balances (young_animals_by_sex_<year>.csv) with the cattle member splits (the default since
    17 November 2026, K65), or pooled across the sexes (young_animals_<year>.csv) with
    RegionalSupplyModel.use_cattle_member_splits off (capri_mod/data/nested_tables.py). year: the data set's
    calibration year, by default the run's (RunInputs.market_year, set by SupplyModule; the base year where unset): the
    base year's tables (tools/build/build_young_animals.py) or, at the 2030 market year, CAPRI's 2030 coefficients in
    the baseline's folder (tools/build/build_young_animals_2030.py; CAPRI's INPANI_ takes the simulation year's
    DATA(.., "Y"), KNOWN_ISSUES K178). A year without its tables is an error (no fall back to the base year's)."""
    by_sex = bool(getattr(RegionalSupplyModel, "use_cattle_member_splits", False))
    by = _inputs.base_year()                                          # the base year's tables (K52f)
    yr = year if year is not None else getattr(_inputs.current(), "market_year", None)
    yr = str(yr) if yr is not None else str(by)
    name = f"young_animals_by_sex_{yr}.csv" if by_sex else f"young_animals_{yr}.csv"

    def load(inp):
        from capri_mod.data.nested_tables import read_young_animals
        return read_young_animals(inp.path(name, "supply"))
    return _inputs.current().cached(name, load)


def active_technologies():
    """CAPRI's active mitigation technologies of the Green Deal reference (activeTech,
    capri_data/2017/abatement/active_technologies.csv, tools/build/build_active_technologies.py). A missing file is an
    error (K74, 29 October 2026; before, every option with data was made available with a warning)."""
    def load(inp):
        f = inp.path("active_technologies.csv", "abatement")
        if not f.exists():
            raise FileNotFoundError(f"CAPRI's active mitigation technologies missing: {f} "
                                    "(tools/build/build_active_technologies.py)")
        return set(inp.csv(f.name, "abatement")["technology"].str.upper())
    return _inputs.current().cached("active_technologies", load) or None


def fert_efficiency_cap(region: str):
    """Largest total efficiency gain E = sum share x NMIN CAPRI allows (Tot_MitFert_):
    1 + E <= max(x + 0.1, 1). None when x is unknown."""
    x = overfert_factor(region)
    return None if x is None else max(x + param("OVERFERT_MARKUP"), 1.0) - 1.0


def _csv_dict(name: str, where: str, col: str) -> Dict[str, float]:
    """{key: value} of one column of an input CSV of the run (first column the key), NaN rows left out."""
    def load(inp):
        s = inp.csv(name, where, index_col=0)[col].dropna()
        return {str(k): float(v) for k, v in s.items()}
    return _inputs.current().cached(f"{where}/{name}:{col}", load)


class _InputColumn:
    """A class attribute holding one column of an input CSV of the run (_csv_dict), read when first used (it was read
    at import from the fixed capri_data/2017 path until 30 October 2026)."""

    def __init__(self, name: str, where: str, col: str):
        self.name, self.where, self.col = name, where, col

    def __get__(self, obj, owner=None) -> Dict[str, float]:
        return _csv_dict(self.name, self.where, self.col)


@dataclass
class RegionData:
    """All input data for a single NUTS-2 regional model."""
    region_id: str

    # Activity levels (ha / heads) — base year
    base_areas: pd.Series        # crops: ha, animals: heads (1000)
    base_animals: pd.Series

    # Prices and costs
    producer_prices: pd.Series   # EUR/t
    variable_costs: pd.Series    # EUR/ha or EUR/head
    yields: pd.Series            # t/ha or t/head

    # Land constraints (1000 ha)
    land: pd.Series              # indexed by land type

    # Nutrient coefficients (kg/ha or kg/head)
    nutrient_coefs: pd.DataFrame

    # CAP payments (EUR/ha)
    cap_payments: pd.Series
    cap_premium: Optional[pd.Series] = None   # CAPRI PRME, per activity

    # Optional: exogenous yield trend multipliers for projections
    yield_trend: Optional[pd.Series] = None

    # Optional: marketed final-product output per head for livestock, in kt per
    # 1000 head, built from CAPRI's COMI/BEEF/PORK/POUM/EGGS/SGMT/SGMI items by
    # tools/build/build_livestock_output_coef.py. Used for gross_output in place of
    # YILD, which for breeding and suckler activities is not a marketed product.
    livestock_output_coef: Optional[pd.Series] = None

    #: Market revenue per head for livestock, EUR/head, from CAPRI's MREV.
    #: Used instead of price x YILD, which for breeding and suckler activities
    #: values a quantity that is not a marketed product.
    livestock_revenue_coef: Optional[pd.Series] = None
    #: value of final products per head (no young animals), CAPRI quantities x UVAG; used where
    #: CAPRI's MREV counts young-animal sales (sows: MREV = piglets)
    livestock_product_value_coef: Optional[pd.Series] = None
    livestock_product_value_by_market_coef: Optional[pd.Series] = None
    #: CAPRI's transmission of a market's producer price change to the outputs' unit values (arm/set_prices.gms: the
    #: absolute change; K169): {(activity, commodity): PPRI0 / UVAG0} of the region's member state, the factor on the
    #: market's relative change; 1 where absent (price_transmission_2030.csv; at the 2030 market year)
    price_transmission: Optional[dict] = None
    #: young-animal value factors {good: factor} (CAPRI's 2030 prices in the projected baseline)
    young_value_factor: Optional[dict] = None
    #: CAPRI's dairy split DCOL/DCOH (share_low, d<item>_rel, q_low, q_high), the port of CAPRI's two dairy activities
    dairy_intensity: Optional[pd.Series] = None
    #: CAPRI's bull and heifer splits {animal: Series} (BULL/BULH, HEIL/HEIH), the port of CAPRI's bull and heifer splits
    cattle_intensity: Optional[dict] = None
    genetics_effects: Optional[dict] = None
    #: CAPRI's histosols: organic-soil shares, emission factors, fallowing cost terms
    histosol: Optional[pd.Series] = None
    #: CAPRI's atmospheric deposition per ha, p_nitrBalance(AtmDep) (kg N/ha, n_deposition_regional.csv): the MANN of
    #: the idled histosols in the residue pool and the N surplus (K184)
    n_deposition_kg_ha: Optional[float] = None
    #: CAPRI's crop technologies T1/T2: per crop with both, the T1 - T2 differences and CAPRI's 2030 technology
    #: block in the mix columns' variables (techn_mix_2030.csv, pmp_capri_2030_mix.csv); with CAPRI's 2030 PMP terms only
    techn_mix: Optional[pd.DataFrame] = None
    #: CAPRI's pesticide module (supply.pest_disagg "agg5"): {"cells": DataFrame (activity, item, technology) of the
    #: calibrated cells, "no_damage_fac": {(activity, technology): NoDamageFac}} (pesticide_par_2030.csv); None off
    pesticides: Optional[dict] = None
    #: CAPRI's input costs the Green Deal targets change (build_plant_protection_cost.py): plap, inpo, fert, eful
    #: (EUR/ha by crop) and inpo_toin_share (animals)
    input_costs_ha: Optional[pd.DataFrame] = None
    #: CAPRI's two valuations of each crop's plant protection at its 2030 reference (EUR/ha in CAPRI's 2030 money):
    #: plap_uvap_eur_ha (its Green Deal step's p_linObjeCont, DATA(PLAP) x the member state's UVAP(PLAP)) and
    #: plantp_cost_eur_ha (its reference's and PMP calibration's, the pesticide module's Plantp_cost);
    #: plant_protection_capri_step_2030.csv, at the 2030 market year only (the comparison switches
    #: supply.greendeal_plap_crop_level_capri_step and supply.greendeal_plap_mix_capri_step, DEP-51)
    plap_capri_step: Optional[pd.DataFrame] = None
    #: CAPRI's simulation-year input coefficients of 2030 (input_coefs_2030.csv, CAPRI's 2030 money; the 2030 market
    #: year only): the crops' PLAP, INPO and top-up bases and yield-dependent parts at the member state's UVAP, the
    #: animals' INPO yield factor (register DEP-21)
    input_coefs_2030: Optional[pd.DataFrame] = None
    #: the crops' yield-dependent inputs of 2030 item by item (crop_inputs_2030.csv: activity x item, EUR per ha before
    #: TF_I, CAPRI's 2030 money; the 2030 market year only; the EAA by item, income I2)
    crop_inputs_2030: Optional[pd.DataFrame] = None
    #: the simulation year (the projection's market year; None: the base year)
    sim_year: Optional[int] = None
    #: CAPRI's catch crops (catc_share_2030, catc_cost_eur_ha, biofix_t_n_ha) and winter cover shares by crop
    cover_crops: Optional[pd.Series] = None
    winter_cover_share: Optional[pd.DataFrame] = None
    livestock_cost_coef: Optional[pd.Series] = None
    #: the animals' input costs per model head by item (livestock_input_cost.csv, register DEP-13 step 3: the inputs of
    #: IobjCont, YOUNG, FEED; at the 2030 market year the year's inputs, projection_module.p_linObjeCont_animals_Y),
    #: animal x item, EUR per head
    livestock_input_cost: Optional[pd.DataFrame] = None
    livestock_output_value_coef: Optional[pd.Series] = None
    livestock_premium_coef: Optional[pd.Series] = None     # CAPRI PRME per model head
    capri_level_ratio: Optional[pd.Series] = None          # model herd units per CAPRI LEVL unit (activity bounds)
    livestock_feed_coef: Optional[pd.Series] = None
    fodder_balance: Optional[dict] = None
    land_market: Optional[dict] = None
    #: CAPRI's land rents (EUR/ha) by land type, {"ARAC", "FRUN", "GRAS"}, at the market year's calibration point
    land_rents: Optional[dict] = None
    #: CAPRI's 2030 PMP matrix of the crops, {(act_i, act_j): g} (K61); Q_ij = g / sqrt(x_i x_j) at the base levels
    pmp_capri: Optional[dict] = None
    #: activities with a level but no CAPRI calibration (no CAPRI PMP term and no CAPRI elasticity): held at their
    #: level, as CAPRI holds activities it does not calibrate (23 October 2026: before, literature elasticities)
    uncalibrated: Optional[frozenset] = None

    #: CAPRI's organic yield gaps by macro-region and product group.
    organic_yield_gap: Optional[pd.DataFrame] = None
    #: CAPRI's maps to them (inputs/load_organic_yieldgap.gms): member state -> PESETA macro-region (ms2peseta) and
    #: model crop -> product group (pact2yieldGap), organic_yield_gap_regions.csv / _groups.csv
    organic_yield_gap_regions: Optional[dict] = None
    organic_yield_gap_groups: Optional[dict] = None

    #: CAPRI's Green Deal targets for this region's member state: extra
    #: landscape land (points of UAA) and organic conversion (points of arable,
    #: grassland and permanent-crop area).
    landscape_target_pp: Optional[float] = None
    organic_targets_pp: Optional[pd.Series] = None
    #: {CAPRI crop group (NGRP): its organic target class} (organic_ngrp_class.csv)
    organic_ngrp_class: Optional[dict] = None
    #: the Green Deal group's slack on the fertiliser priors' partial derivative (fert_partial_slack.csv): the region's
    #: listed crop groups ("" alone: the tiny-prior rule only); None outside CAPRI's list
    fert_partial_slack: Optional[list] = None


@dataclass
class SupplyResult:
    """Output of a regional supply module solve."""
    region_id: str
    activities: pd.Series          # optimal activity levels (1000 ha / heads)
    gross_output: pd.Series        # 1000 t
    #: EUR 1000: the activities' margins x levels at the solve; the regional solve sets it to the region's income in
    #: CAPRI's form, income["MGVA"] (capri_mod/income/income_module.py income_parts)
    gross_margin: float
    shadow_prices: Dict[str, float] = field(default_factory=dict)
    nutrient_balance: pd.Series = None
    ghg_emissions: pd.Series = None
    converged: bool = True
    solver_message: str = ""
    #: CAPRI's obligatory set-aside ISET (1000 ha; SETA_, supply/land.py _obligatory_set_aside): 0 without rates
    iset: float = 0.0
    #: run.verbosity "solver": each IPOPT solve of the region's model, its log, size and status (runlog.supply_solves)
    solver_log: list = field(default_factory=list)
    #: the fodder balances' duals as the NLP returns them, not clipped at 0 (EUR/t; CAPRI's PSHW, the dual of SUPBAL_
    #: for the fodder, reports/sol_simy.gms l. 737-757): the fodder's scenario value, CAPRI's UVAG(FODDO, SIM)
    #: (IncomeDistributionModule.feed_by_animal; the product accounts of income I2); not in the region's income, where
    #: it is an internal flow
    fodder_duals: Dict[str, float] = field(default_factory=dict)
    #: the region's income at the solution in CAPRI's form (income I1, EUR 1000: MGVA, PRME, FEED, mitiI, mitiO,
    #: mitiPmp, the options' parts, MGVA per activity; IncomeDistributionModule.income_parts), set by the regional solve
    income: Dict = field(default_factory=dict)
    #: the region's gross account by item at the solution (income I2, EUR million: items, TOOU, TOIN, PRME, MGVA, AGGT,
    #: DIFF; capri_mod/income/eaa.py eaag_items), set by the regional solve; None where it could not be computed
    eaa: Optional[Dict] = None




def _luc_of(model, land_types):
    """CAPRI's land-use change transitions (capri_mod.environmental.luc) of the region at its solved land types,
    moved from the base land types of the land market; None outside CAPRI's LUC data."""
    try:
        from capri_mod.environmental.luc import LUCModel
        from capri_mod.fert.inner_fert_dist import InnerFertDist
        env_ = getattr(model.seen, "env_for_surplus", None)
        inner = getattr(env_.par, "inner_fert", None) if env_ is not None else None
        if inner is None:
            inner = InnerFertDist()
        cr = model.data.region_id              # the model's regions are CAPRI's units
        lm = getattr(model.data, "land_market", None) or {}
        L0 = lm.get("base_kha") or {}
        d = {t: float(land_types.get(t, L0.get(t, 0.0))) - float(L0.get(t, 0.0)) for t in LAND_MARKET_TYPES
             if t in (land_types or {})}
        return LUCModel.get().solve(cr, d) if cr else None
    except Exception as _exc:
        import warnings as _w
        _w.warn(f"LUC model failed for {model.data.region_id}: {_exc!r}")
        return None


def _mineral_n_for_accounts(model):
    """Mineral N of the region's solution for the environmental accounts: the purchases of the NLP form's
    fertilisation block (CAPRI's v_netPutQuant(NITF)), else the mineral-N allocation column (or None)."""
    npk = getattr(model.res, "last_npk", None) or {}
    if "N" in npk:
        return float(npk["N"]["purchase"])
    return getattr(model.res, "last_mineral_n", None)


def _merge_relief(model) -> dict:
    """N relief per activity unit for the accounts: ammonia technologies + inhibitors on manure."""
    out = dict(getattr(model.ev, "animal_n_relief", None) or {})
    for a, v in (getattr(model.ev, "manure_ni_relief", None) or {}).items():
        out[a] = out.get(a, 0.0) + float(v)
    return out




def fert_side_table():
    """{(model region, technology, item): CAPRI's literature-review side effect} (p_litRevFertTechs;
    capri_data/2017/abatement/fert_side_effects.csv, tools/build/build_fert_side_effects.py)."""
    def load(inp):
        tab = inp.csv("fert_side_effects.csv", "abatement")
        return {(r.region, r.technology, r.item): float(r.value) for r in tab.itertuples()}
    return _inputs.current().cached("fert_side_effects", load)


def fert_side_value(region: str, tech: str, item: str):
    """CAPRI's literature-review side effect (p_litRevFertTechs) for a model region, or None."""
    return fert_side_table().get((region, tech, item))
