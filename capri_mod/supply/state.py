"""The supply models' parameters and state, by kind (refactor stage 3, second half; docs/design/STAGE3B_PLAN.md).

Each regional model (RegionalSupplyModel) and the supply module (SupplyModule) will hold what they keep between
calls in a few declared objects instead of loose attributes:
- ``par``: parameters, built once per base (calibration, memos of the base);
- ``sv``: state carried from one solve or outer iteration to the next (warm starts, linearisation points);
- ``ev``: the working values of one solve, passed between the blocks;
- ``seen``: what the caller sets on the model before a solve (prices, rations, switches of the run);
- ``res``: the last solve's results and diagnostics.

They are slot classes, not dataclasses with None defaults (the project lead's decision of 2 November 2026, plan Q1):
a field that was never set is absent, as an attribute that was never set is today, so the code's
``getattr(obj, name, default)`` reads keep their behaviour when they move (``getattr(obj.sv, name, default)``).

S0c added the objects empty and the guard; the fields move into them block by block (S2 onward), each commit a pure
move checked against the mini-EU run. A moved name is listed in MOVED_REGIONAL / MOVED_MODULE:
reading or writing it on the model raises RuntimeError (not AttributeError, so a getattr default cannot hide it), as
the market's MOVED (capri_mod/market/state.py). Reads and writes through ``__dict__`` and names held in strings are
not seen by the guard; capri_mod/tests/test_supply_state.py scans the code for them.

CAPRI's counterpart: GAMS declares its parameters (p_*) and variables (v_*) apart; the supply model's state between
solves is the variables' levels CONOPT starts from.
"""
from __future__ import annotations


from capri_mod.statekit import (  # noqa: F401  (re-exported: the kit moved to capri_mod/statekit.py, stage 4)
    _Slots, _StateMixin, setdefault, discard, pop, _split, get_path_or, setdefault_path, has_path, get_path, set_path,
    del_path,
)


class RegionalParameters(_Slots):
    """A regional model's parameters, built once per base."""
    __slots__ = (
        "nlp_cal",            # the NLP's calibration (CAPRI's PMP terms in the NLP form) for the current settings
        "nlp_base_alloc",     # the fertiliser allocation at the calibration point (nlp_cal's base_alloc)
        "nlp_cal_store",      # the calibrations by settings key, so a switch of settings and back keeps both
        "npk_dual_bound",     # the fertiliser distribution's dual bound where it was widened for the region
        # livestock (S4): the split columns' linear terms, calibrated from the duals of the first solves, and the
        # calibrations still pending
        "cattle_cz",          # the cattle splits' terms by split
        "cattle_pending",     # the cattle splits whose terms wait for the duals
        "dairy_cz",           # the low-yield dairy split's term
        "dairy_pending",      # the dairy split's column and requirement waiting for the duals
        "genet_cz",           # the genetics options' terms, for the current genetics settings
        "genet_cz_store",     # genet_cz by genetics settings key
        "genet_key",          # the genetics settings key genet_cz belongs to
        "genet_pending",      # the genetics options whose terms wait for the duals
        "genet_rows_memo",    # the genetics options' rows (a memo)
        # fertilisation (S5): memos of the base and CAPRI's priors recalibrated at the first solve
        "ef_lea_cache",       # the leaching emission factor (a memo)
        "ef_min_n2o_cache",   # mineral fertiliser's N2O per kg N, CO2 equivalent (a memo)
        "min_n2o_parts_cache",  # its parts (a memo)
        "npk_kappa",          # the fertiliser distribution's kappa by nutrient (a memo)
        "npk_prior_override", # CAPRI's priors where the calibration recalibrated them
        "npk_prior_recalibrated",  # the nutrients whose priors were recalibrated
        # abatement (S7): the histosol fallowing's terms, calibrated from the duals
        "hist_cal",           # the terms by histosol class
        "hist_pending",       # the classes whose terms wait for the duals
        # core and policy (S8)
        "base_cal_shift",     # the linear terms' shift from SupplyModule.calibrate_to_base
        "base_levels_cache",  # the base levels (a memo keyed on the base data's identity)
        "input_cost_memo",    # the input costs (a memo)
        "oyg_memo",           # the organic yield gaps (a memo)
    )


class RegionalSolveState(_Slots):
    """A regional model's state carried from one solve to the next."""
    __slots__ = (
        "nlp_prev",           # the last solution (graph key, x, shape, multipliers): the next solve's warm start
        "nlp_prev_f",         # its objective: the warm check's reference
        "nlp_y",              # its activity levels: the jump check's reference
        "nlp_cols",           # the columns of nlp_y
        "nlp_relax_keep",     # the mineral-cap exemption kept from the first solve of a problem (its fingerprint)
        "kkt_base",           # the base solve's KKT records by graph key (the Hessian's KKT mode)
        "wc_solved",          # the winter cover share chosen by the last solve (None where not endogenous)
        # fertilisation (S5)
        "n_relax_sticky",     # the N-target relaxation kept from one solve to the next (in SOLVE_STATE)
        # abatement (S7)
        "amm_last",           # the ammonia options' linearisation point, from the previous solve
    )


class RegionalEvalState(_Slots):
    """A regional model's working values within one solve."""
    __slots__ = (
        "last_duals",         # the NLP's duals of the solve's rows (feed, land, ...), read by the calibrations after it
        "last_req_duals",     # the requirement rows' duals, read by the split calibrations after the NLP
        "nlp_accept_last",    # set around the last attempt: IPOPT's last point is kept (as CAPRI)
        "nlp_failed",         # why the NLP form failed in this solve (None where it did not)
        "nlp_fb_last",        # how the last fallback ended (False, or "n_target")
        "nlp_n_target_cause", # the tiered N target was the cause of a failure
        "nlp_try_n_relax",    # set around a call: the N-target relaxation may be tried
        # livestock (S4): the split columns of this solve's problem
        "cattle_cols",        # the cattle splits' columns
        "dairy_col",          # the low-yield dairy split's column
        "dairy_req_extra",    # the splits' extra requirement entries by animal
        "genet_cols",         # the genetics options' columns
        # fertilisation (S5)
        "n_intensity",        # the mineral N intensity factors of the solve, by crop and the manure credit
        "nlp_mine_small",     # the fertiliser groups too small for the mineral-N row
        # land (S6): the land market's layout in the augmented problem and the manure pools
        "alloc_cols",         # the mineral-N allocation columns (0 or 1)
        "alloc_m0",           # the allocation's start
        "alloc_row",          # the allocation's row
        "aug_labels",         # one label per row of the augmented problem
        "cover_dbf_nb",       # the catch crops' N-balance term on the allocation row
        "land_rent_rows",     # the land rent rows by label
        "land_types_used",    # the land types of the problem
        "need_row",           # the feed need row
        "nrow_land",          # the land rows of the N row (columns, base land, target)
        "pool_avail",         # the manure available to the pool
        "pool_cols",          # the manure pool's export and import columns (N)
        "pool_cols_pk",       # idem for P and K
        # abatement (S7): the ammonia and inhibitor accounts of the solve, the catch-crop requirement, histosols, the
        # emission tax's undo record
        "amm_cost",           # the ammonia options' cost by animal
        "animal_n_relief",    # the manure N the ammonia options keep, by animal (the N row's relief)
        "cover",              # the catch-crop requirement and increment (1000 ha)
        "ghg_applied",        # the emission tax added to the net revenues, by activity (its undo record)
        "ghg_nr_obj",         # the net revenues object the tax was added to (an identity check, never a copy)
        "hist_cols",          # the histosol fallowing's columns
        "mix_cols",           # {crop: column} of the technology mix columns (S1)
        "mix_dnr",            # {crop: net revenue T1 - T2 per ha} of this solve (S1)
        "mix_n_min",          # {crop: mineral N input T1 - T2 per ha} of the N_balance row (S1)
        "manure_ni_nh3",      # NH3 of the manure inhibitors, by activity
        "manure_ni_relief",   # the manure N the inhibitors keep, by activity
        "nlp_nip",            # the manure inhibitors' parameters
        # core and policy (S8): the solve's arguments, the problem's rows, the scenario's per-solve terms
        "fall_floor",         # the landscape (fallow) floor
        "mineral_cap",        # the mineral fertiliser caps of this solve
        "mineral_row",        # the mineral-N row's terms
        "nbal_price",         # the N-balance price of this solve
        "price_shock_now",    # the price shock of this solve (the Hessian's)
        "row_labels",         # one label per row of the problem
        "surplus_row",        # the N-surplus row of this solve
        "yields_solve0",      # the yields at the start of the solve (restored at its end)
        "greendeal_inputs",   # the Green Deal's input reductions of this solve
        "greendeal_crop_delta",   # {crop: (plant protection, other inputs)} cost changes of this solve, EUR/ha
        "organic_conv",       # the organic conversion shares by crop
        "yield_price_factor", # the yields' price factors
    )


class RegionalSeen(_Slots):
    """What the supply module and the coupling set on a regional model before its solve (S9; read with a getattr
    default where it may be unset, as the attributes were: yani_price_ratio and manure_ctx had class defaults None)."""
    __slots__ = (
        "ration_state",       # the feed block's ration state of the region
        "manure_pool_price",  # the manure pool's N price of the member state
        "manure_pool_price_pk",  # its P and K prices
        "yani_price_ratio",   # the young-animal price ratios {good: price / base price}
        "feed_rations",       # the rations by animal
        "feed_prices",        # the feed prices
        "feed_bulk_ratio",    # the bulk feeds' price ratios
        "ghg_tax",            # the emission tax (EUR per t CO2-eq; 0 outside the EU)
        "ghg_coef",           # the emission coefficients of the region
        "env_for_surplus",    # the supply module's shared EnvironmentalModule (removed before pickling, re-attached)
        "manure_ctx",         # CAPRI's crop nutrient balance terms (Sprint 9k; None outside the EU)
        "fert_techs_all",     # CAPRI's fertiliser options (NLP form)
        "nlp_cal_check",      # set by CAPRIModel at a baseline: check the NLP calibration at the next solve
        "fallow_in_all_rmssup",  # CAPRI's %fallowInAllRmssup%: histosol fallowing outside the EU (endotech settings)
        "wintercov_in_all_rmssup",  # CAPRI's %winterCovInAllRmssup%: the winter cover outside the EU (endotech settings)
    )


class RegionalResults(_Slots):
    """A regional model's last solve: results and diagnostics."""
    __slots__ = (
        "cover_solved",       # the winter cover chosen in the NLP form (the supply result's cover_crops)
        "fd_model",           # the fertiliser distribution's flows and areas (the supply result's fert_dist_model)
        "fert_inside_factor", # the fertiliser accounts' factors inside the NLP
        "kkt_ipopt",          # IPOPT solves in the Hessian's KKT mode (a counter)
        "last_feed_dm",       # the feed used, dry matter
        "last_feed_t",        # the feed used, tonnes
        "last_npk",           # the fertiliser outputs by nutrient
        "n_solves",           # solves of the region (a counter)
        "nlp_fallback_log",   # the NLP form's fallbacks of the run (metadata nlp_fallback)
        "nlp_jump",           # the jump check's record (outer history's jump_check)
        "nlp_nonoptimal",     # IPOPT's status where its last point was kept (non-optimal, as CAPRI)
        "nlp_ok",             # the last solve was CAPRI's form, accepted
        "nlp_path",           # the starts tried and the last one's IPOPT iterations
        "nlp_rc",             # the activities' reduced costs
        "nlp_relaxed",        # the mineral-cap exemption applied
        "nlp_status",         # IPOPT's status
        "yani_dnet",          # the solution's response to the young-animal prices (K65)
        # livestock (S4): the split columns' levels in the last solution
        "last_cattle_z",
        "last_dairy_z",
        "last_genet_z",
        # fertilisation (S5)
        "fert_tech_shares",   # the fertiliser technologies' shares
        "n_target_relaxed",   # the solve ended at JRC121368's relaxed N target
        # land (S6): the manure pools, read by the manure market (coupling/manure.py)
        "manure_supply0",     # the region's manure N supply at the start
        "manure_supply0_pk",  # idem for P and K
        "pool_manure_vec",    # the manure N by column
        "pool_manure_vec_pk", # idem for P and K
        # abatement (S7)
        "animal_n_kept",      # the manure N kept by the ammonia options, by animal
        "animal_nh3_saved",   # the NH3 they save, by animal
        "manure_tech_shares", # the manure technologies' shares
        # core (S8)
        "land_solution",      # the land types' levels
        "last_aug",           # the augmented problem the land-market solve used (Q, c, A, b, y)
        "last_hist_fallow",   # the histosol fallowing by class
        "last_mix_z",         # {crop: z} of the technology mix columns, 1000 ha moved from T2 to T1 (S1)
        "last_manure_trade",  # the manure trade (N)
        "last_manure_trade_pk",  # idem for P and K
        "last_mineral_n",     # the mineral N bought
        "last_plain",         # the plain problem (no land market), as last_aug
    )


class ModuleParameters(_Slots):
    """The supply module's parameters, built once per base."""
    __slots__ = (
        # S10a; the per-region caches returned by the workers (_PAR_CACHES) are merged into the parent's
        "balance_cache",      # the N-balance coefficients by region
        "env_for_surplus",    # the EnvironmentalModule shared with the regional models (seen.env_for_surplus)
        "jrc_capped_cache",   # JRC121368's capped regions (popped by CAPRIModel every outer iteration)
        "mcap_cache",         # the mineral caps by region
        "mctx_cache",         # CAPRI's crop nutrient balance terms by region
        "genetics_key",       # the settings key of the genomics calibration
    )


class ModuleSolveState(_Slots):
    """The supply module's state carried between regional passes."""
    __slots__ = (
        # S10a; the N-balance price state is per region and returned by the workers (_PAR_STATE)
        "base_cal_prev",      # the base calibration's previous round
        "base_cal_round",     # its rounds across the baseline's iterations
        "base_cal_stalled",   # the regions where it stalled
        "nbal_bracket",       # the N-balance price bracket by region
        "nbal_prev",          # the previous N-balance prices by region
        "nbal_state",         # the N-balance price by region
    )


class ModuleSeen(_Slots):
    """What the model (CAPRIModel) and the coupling set on the supply module (S10b), passed on to each regional
    model's seen before its solve."""
    __slots__ = (
        "feed_prices",        # the feed prices by region (also set by the supply module's base rations)
        "feed_rations",       # the rations by region (idem)
        "feed_bulk_ratio",    # the bulk feeds' price ratios {(member state, bulk): ratio}
        "ghg_tax",            # the emission tax (EUR per t CO2-eq)
        "ghg_coef",           # the emission coefficients by region
        "manure_pool_price",  # the manure pools' N prices by member state
        "manure_pool_price_pk",  # their P and K prices
        "manure_trade_on",    # manure trade between regions (read with the default True)
        "yani_price_ratio",   # the young-animal price ratios, EU
        "yani_price_ratio_ms",  # idem by member state
        "yani_price_ratio_m",   # idem by market region (the coupling's own storage)
        "milk_price_dev_ms",  # the member states' milk price deviations
        "price_dev_ms",       # the member states' price deviations
        "ration_state",       # the feed block's ration state by region
        "hess_probe",         # the Hessian's skip probe mode ("record", "compare", "verify" or None)
        "hess_shock",         # the shock being measured
        "hess_base_res",      # the base re-solve's results by region
    )


class ModuleResults(_Slots):
    """The supply module's last pass: results and diagnostics."""
    __slots__ = (
        # S10a
        "hess_fp",            # the Hessian's skip probe: the regions' first-solve digests (set and popped by it)
        "hess_verify",        # idem, verify mode
        "max_nbal_region",    # the region of the largest N-balance price update
        "max_nbal_update",    # the largest N-balance price update of the pass
        "worker_failures",    # the regions a worker failed on
    )


_REMOVED = "removed (refactor stage 3 S1, 2 November 2026: written, never read)"
#: the regional models' former attribute names, with where each now lives ("sv.nlp_prev", or "removed (...)")
MOVED_REGIONAL: dict = {
    "_last_land": _REMOVED,
    "_last_aug_A": _REMOVED,
    "_last_aug_b": _REMOVED,
    "_mineral_row_m": _REMOVED,
    "_fert_inside_weight": _REMOVED,
    "_nlp_abatement": _REMOVED,
    "_npk_cov": _REMOVED,
    "_nlp_group_caps": _REMOVED,
    "_manure_ni_share": _REMOVED,
    "_last_feed": _REMOVED,
    "_nlp_times": _REMOVED,
    "_last_aug_cols": "removed (refactor stage 3 S1, 2 November 2026: read with a default, never written)",
    # S2: the NLP block's carried state and calibration
    "_nlp_prev": "sv.nlp_prev",
    "_nlp_prev_f": "sv.nlp_prev_f",
    "_nlp_y": "sv.nlp_y",
    "_nlp_cols": "sv.nlp_cols",
    "_nlp_relax_keep": "sv.nlp_relax_keep",
    "_kkt_base": "sv.kkt_base",
    "_wc_solved": "sv.wc_solved",
    "_nlp_cal": "par.nlp_cal",
    "_nlp_base_alloc": "par.nlp_base_alloc",
    "_nlp_cal_store": "par.nlp_cal_store",
    "_npk_dual_bound": "par.npk_dual_bound",
    # S3: the NLP block's working state and results
    "_last_duals": "ev.last_duals",
    "_last_req_duals": "ev.last_req_duals",
    "_nlp_accept_last": "ev.nlp_accept_last",
    "_nlp_failed": "ev.nlp_failed",
    "_nlp_fb_last": "ev.nlp_fb_last",
    "_nlp_n_target_cause": "ev.nlp_n_target_cause",
    "_nlp_try_n_relax": "ev.nlp_try_n_relax",
    "_cover_solved": "res.cover_solved",
    "_fd_model": "res.fd_model",
    "_fert_inside_factor": "res.fert_inside_factor",
    "_kkt_ipopt": "res.kkt_ipopt",
    "_last_feed_dm": "res.last_feed_dm",
    "_last_feed_t": "res.last_feed_t",
    "_last_npk": "res.last_npk",
    "_n_solves": "res.n_solves",
    "_nlp_fallback_log": "res.nlp_fallback_log",
    "_nlp_jump": "res.nlp_jump",
    "_nlp_nonoptimal": "res.nlp_nonoptimal",
    "_nlp_ok": "res.nlp_ok",
    "_nlp_path": "res.nlp_path",
    "_nlp_rc": "res.nlp_rc",
    "_nlp_relaxed": "res.nlp_relaxed",
    "_nlp_status": "res.nlp_status",
    "_yani_dnet": "res.yani_dnet",
    # S4: livestock and feed
    "_cattle_cz": "par.cattle_cz",
    "_cattle_pending": "par.cattle_pending",
    "_dairy_cz": "par.dairy_cz",
    "_dairy_pending": "par.dairy_pending",
    "_genet_cz": "par.genet_cz",
    "_genet_cz_store": "par.genet_cz_store",
    "_genet_key": "par.genet_key",
    "_genet_pending": "par.genet_pending",
    "_genet_rows_memo": "par.genet_rows_memo",
    "_cattle_cols": "ev.cattle_cols",
    "_dairy_col": "ev.dairy_col",
    "_dairy_req_extra": "ev.dairy_req_extra",
    "_genet_cols": "ev.genet_cols",
    "_last_cattle_z": "res.last_cattle_z",
    "_last_dairy_z": "res.last_dairy_z",
    "_last_genet_z": "res.last_genet_z",
    # S5: fertilisation
    "_ef_lea_cache": "par.ef_lea_cache",
    "_ef_min_n2o_cache": "par.ef_min_n2o_cache",
    "_min_n2o_parts_cache": "par.min_n2o_parts_cache",
    "_npk_kappa": "par.npk_kappa",
    "_npk_prior_override": "par.npk_prior_override",
    "_npk_prior_recalibrated": "par.npk_prior_recalibrated",
    "_n_relax_sticky": "sv.n_relax_sticky",
    "_n_intensity": "ev.n_intensity",
    "_nlp_mine_small": "ev.nlp_mine_small",
    "_fert_tech_shares": "res.fert_tech_shares",
    "_n_target_relaxed": "res.n_target_relaxed",
    # S6: land
    "_alloc_cols": "ev.alloc_cols",
    "_alloc_m0": "ev.alloc_m0",
    "_alloc_row": "ev.alloc_row",
    "_aug_labels": "ev.aug_labels",
    "_cover_dbf_nb": "ev.cover_dbf_nb",
    "_land_rent_rows": "ev.land_rent_rows",
    "_land_types_used": "ev.land_types_used",
    "_need_row": "ev.need_row",
    "_nrow_land": "ev.nrow_land",
    "_pool_avail": "ev.pool_avail",
    "_pool_cols": "ev.pool_cols",
    "_pool_cols_pk": "ev.pool_cols_pk",
    "_manure_supply0": "res.manure_supply0",
    "_manure_supply0_pk": "res.manure_supply0_pk",
    "_pool_manure_vec": "res.pool_manure_vec",
    "_pool_manure_vec_pk": "res.pool_manure_vec_pk",
    # S7: abatement
    "_hist_cal": "par.hist_cal",
    "_hist_pending": "par.hist_pending",
    "_amm_last": "sv.amm_last",
    "_amm_cost": "ev.amm_cost",
    "_animal_n_relief": "ev.animal_n_relief",
    "_cover": "ev.cover",
    "_ghg_applied": "ev.ghg_applied",
    "_ghg_nr_obj": "ev.ghg_nr_obj",
    "_hist_cols": "ev.hist_cols",
    "_manure_ni_nh3": "ev.manure_ni_nh3",
    "_manure_ni_relief": "ev.manure_ni_relief",
    "_nlp_nip": "ev.nlp_nip",
    "_animal_n_kept": "res.animal_n_kept",
    "_animal_nh3_saved": "res.animal_nh3_saved",
    "_manure_tech_shares": "res.manure_tech_shares",
    # S8: core and policy (net_revenues, premiums, f, Q and balance_shortfall stay on the model, plan Q8)
    "_base_cal_shift": "par.base_cal_shift",
    "_base_levels_cache": "par.base_levels_cache",
    "_input_cost_memo": "par.input_cost_memo",
    "_oyg_memo": "par.oyg_memo",
    "_fall_floor": "ev.fall_floor",
    "_mineral_cap": "ev.mineral_cap",
    "_mineral_row": "ev.mineral_row",
    "_nbal_price": "ev.nbal_price",
    "_price_shock_now": "ev.price_shock_now",
    "_row_labels": "ev.row_labels",
    "_surplus_row": "ev.surplus_row",
    "_yields_solve0": "ev.yields_solve0",
    "_greendeal_inputs": "ev.greendeal_inputs",
    "_organic_conv": "ev.organic_conv",
    "_yield_price_factor": "ev.yield_price_factor",
    "_land_solution": "res.land_solution",
    "_last_aug": "res.last_aug",
    "_last_hist_fallow": "res.last_hist_fallow",
    "_last_manure_trade": "res.last_manure_trade",
    "_last_manure_trade_pk": "res.last_manure_trade_pk",
    "_last_mineral_n": "res.last_mineral_n",
    "_last_plain": "res.last_plain",
    # S9: the regional models' inputs
    "ration_state": "seen.ration_state",
    "manure_pool_price": "seen.manure_pool_price",
    "manure_pool_price_pk": "seen.manure_pool_price_pk",
    "yani_price_ratio": "seen.yani_price_ratio",
    "feed_rations": "seen.feed_rations",
    "feed_prices": "seen.feed_prices",
    "feed_bulk_ratio": "seen.feed_bulk_ratio",
    "ghg_tax": "seen.ghg_tax",
    "ghg_coef": "seen.ghg_coef",
    "_env_for_surplus": "seen.env_for_surplus",
    "_manure_ctx": "seen.manure_ctx",
    "_fert_techs_all": "seen.fert_techs_all",
    "_nlp_cal_check": "seen.nlp_cal_check",
}
#: the supply module's former attribute names
MOVED_MODULE: dict = {
    "_base_cal_drift": _REMOVED,
    # S10a: the supply module's parameters, carried state and results
    "_balance_cache": "par.balance_cache",
    "_env_for_surplus": "par.env_for_surplus",
    "_jrc_capped_cache": "par.jrc_capped_cache",
    "_mcap_cache": "par.mcap_cache",
    "_mctx_cache": "par.mctx_cache",
    "genetics_key": "par.genetics_key",
    "_base_cal_prev": "sv.base_cal_prev",
    "_base_cal_round": "sv.base_cal_round",
    "_base_cal_stalled": "sv.base_cal_stalled",
    "_nbal_bracket": "sv.nbal_bracket",
    "_nbal_prev": "sv.nbal_prev",
    "_nbal_state": "sv.nbal_state",
    "_hess_fp": "res.hess_fp",
    "_hess_verify": "res.hess_verify",
    "max_nbal_region": "res.max_nbal_region",
    "max_nbal_update": "res.max_nbal_update",
    "worker_failures": "res.worker_failures",
    # S10b: what CAPRIModel and the coupling set on the supply module
    "feed_prices": "seen.feed_prices",
    "feed_rations": "seen.feed_rations",
    "feed_bulk_ratio": "seen.feed_bulk_ratio",
    "ghg_tax": "seen.ghg_tax",
    "ghg_coef": "seen.ghg_coef",
    "manure_pool_price": "seen.manure_pool_price",
    "manure_pool_price_pk": "seen.manure_pool_price_pk",
    "manure_trade_on": "seen.manure_trade_on",
    "yani_price_ratio": "seen.yani_price_ratio",
    "yani_price_ratio_ms": "seen.yani_price_ratio_ms",
    "yani_price_ratio_m": "seen.yani_price_ratio_m",
    "milk_price_dev_ms": "seen.milk_price_dev_ms",
    "price_dev_ms": "seen.price_dev_ms",
    "ration_state": "seen.ration_state",
    "_hess_probe": "seen.hess_probe",
    "_hess_shock": "seen.hess_shock",
    "_hess_base_res": "seen.hess_base_res",
}


class RegionalStateMixin(_StateMixin):
    """RegionalSupplyModel's par, sv, ev, seen and res."""
    _MOVED = MOVED_REGIONAL
    _KINDS = {"par": RegionalParameters, "sv": RegionalSolveState, "ev": RegionalEvalState, "seen": RegionalSeen,
              "res": RegionalResults}


class ModuleStateMixin(_StateMixin):
    """SupplyModule's par, sv, seen and res (it has no per-solve working state of its own)."""
    _MOVED = MOVED_MODULE
    _KINDS = {"par": ModuleParameters, "sv": ModuleSolveState, "seen": ModuleSeen, "res": ModuleResults}
