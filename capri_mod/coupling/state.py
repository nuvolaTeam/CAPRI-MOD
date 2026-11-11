"""The coupling's parameters and state, by kind (refactor stage 4, second half;
docs/design/ENV_COUPLING_STATE_INVENTORY.md).

CAPRIModel (capri_mod/model.py with the mixins of capri_mod/coupling) holds what it keeps between calls in declared
objects, as the market's and the supply's modules do (capri_mod/market/state.py, capri_mod/supply/state.py):
- ``par``: parameters and caches built once per base, baseline or run;
- ``sv``: state carried from one outer iteration (or run) to the next: the price step, the departures' histories,
  the milk and young-animal markets, the manure pools, the Hessian's pending flag, the traces;
- ``ev``: one outer iteration's working values, passed between the coupling's methods;
- ``seen``: what the coupling recorded from the modules' last solve and reads later;
- ``res``: results and diagnostics read by the stop test, the run's metadata, the trace, the run script or the tests.

The run's settings (the descriptors of CAPRIModel, ``use_manure_market``) and ``verbose`` stay on the model, as the
supply's class-level settings stayed.

E0 adds the objects empty and the guard; the fields move in E4-E7, each commit a pure move checked against the
mini-EU run. A moved name is listed in MOVED_MODEL: reading or writing it on the model raises RuntimeError (not
AttributeError, so a getattr default cannot hide it; the Hessian's cache key reads three of these fields with
defaults). Reads and writes through ``__dict__`` and names held in strings (the manure pools' _POOL_STATE, the run
script's reads) are not seen by the guard; capri_mod/tests/test_env_coupling_state.py scans the code for them.
"""
from __future__ import annotations

from capri_mod.statekit import _Slots, _StateMixin


class ModelParameters(_Slots):
    """Parameters and caches built once per base, baseline or run."""
    __slots__ = (
        "eu_base_cache",  # per baseline key: the EU base tables and demand calibration (references kept, not copied)
        "yani_ref",           # the young-animal net balances of each baseline key
        "base_supply_cache",  # the baseline's supply results per key (the emission tax coefficients)
        "ghg_coef_cache",     # the emission tax coefficients per baseline key
        "hessian_key",        # the baseline key the market's supply Hessian belongs to
        "endotech_key",       # the key of the applied endotech settings (in the Hessian's cache key)
        "dairy_yield_cache",  # dairy products per t raw milk by member state
        "proc_yield_cache",   # olive oil and milled rice yields
        "prod_grof_cache",    # CAPRI's marketed over gross production per member state and product (S7, grofNEprod)
        "sugar_rate_cache",   # sugar per t beet by member state
        "pool_cost_cache",    # the manure pools' trade costs
        "pool_es_cache",      # the "capri" pool market's excess-supply slopes and calibration duals by region and FOUT
        "ration_model",       # CAPRI's ration model
        "feed_rations_stable",  # rations by region, built once per ration model (its identity keys the feed cache)
        "feed_rations_for",   # the ration model feed_rations_stable was built for (identity)
        "excluded_units",     # the EU units outside a run on a subset (K83)
        "excluded_sup_base",  # the base output of the non-EU supply-model units outside a subset run (S7)
        "base_start",         # per baseline key: the baseline's price signal, block departures and market ratios (S7)
    )


class ModelSolveState(_Slots):
    """State carried from one outer iteration (or run) to the next."""
    __slots__ = (
        "relax_w",            # the price step's adaptive step per product
        "relax_gprev",        # the previous gaps per product
        "capri_target_hist",  # CAPRI's price forecast: the last targets
        "capri_blockdev_hist", # the same for the trade blocks' departures
        "capri_special_hist", # the same for capri_step_special
        "capri_sup_hist",     # the same for Norway
        "capri_sup_full",     # Norway's full price history
        "capri_yani_hist",    # the young animals' price history
        "milk_ms_full",       # the member states' milk price history (reset per member state at iteration 0)
        "eu_dev",             # the trade blocks' price departures
        "sup_dev",            # Norway's price departures
        "special_ms_dev",     # the special smoothing's departures by member state
        "sup_w",              # Norway's adaptive steps
        "sup_gprev",          # Norway's previous steps
        "milk_ms_signal",     # the member states' milk price signals
        "milk_ms_w",          # their adaptive steps
        "milk_ms_gprev",      # their previous gaps
        "milk_ms_hist",       # their forecast histories
        "yani_w",             # the young animals' adaptive steps
        "yani_gprev",         # their previous gaps
        "capri_stop",         # CAPRI's stop rule (accumulates the steps)
        "trace_prev_prem",    # the trace's last premium
        "trace_go_prev",      # the trace's last gross output
        "trace_nlp_prev",     # the trace's last NLP levels
        "trace_nlp_t",        # the trace's last time
        # the manure pools (E6)
        "pool_state",         # the N manure market's plan, kappa and net exports
        "pool_accel",         # the manure market's damping
        "pool_pk",            # the P and K markets' copies of the pool state, by path (coupling/manure.py _POOL_STATE)
    )


class ModelEvalState(_Slots):
    """One outer iteration's working values."""
    __slots__ = (
        "outer_iter_now",     # the outer iteration
        "ls_by_country",      # livestock products by country (the bridge's input; the Hessian overwrites it)
        "unmarketed_supply",  # gross output the market does not take (no marketed production in CAPRI; S7, grofNEprod)
        "blockdev_target_now", # the trade blocks' target departures of the iteration
        "hessian_at_scenario", # set around a scenario's Hessian measurement (in its cache key)
        "yani_np",            # the young animals' (net, production) of the iteration
        "ration_state",       # the ration state of the iteration
    )


class ModelSeen(_Slots):
    """What the coupling recorded from the modules' last solve."""
    __slots__ = (
        "last_spol",          # the policy of the last supply call (the Hessian re-solves with it)
        "last_supply_results", # the last supply results (the next iteration's ration state)
    )


class ModelResults(_Slots):
    """Results and diagnostics of the run."""
    __slots__ = (
        "calib_drift",        # the base calibration's drift
        "calib_trace",        # its trace (the metadata's base_calibration_drift)
        "capri_stop_verdict", # CAPRI's stop rule's verdict
        "capri_drift",        # its drift
        "eu_dev_gap",         # the trade blocks' departure gap
        "sup_dev_gap",        # Norway's departure gap
        "sup_dev_worst",      # its worst product
        "sup_dev_gap_all",    # its gaps by product
        "milk_ms_worst",      # the member states' worst milk gap
        "milk_ms_small_gap",  # their small gaps (metadata)
        "nlp_tol_trace",      # the regional solves' tolerance by iteration
        "outer_history",      # the outer iterations' record
        "yani_imbalance",     # the young-animal markets' imbalance
        "yani_detail",        # their detail by market
        "pool_imbalance",     # the manure markets' worst imbalance
        "pool_worst_key",     # its region and market
        "pool_gaps",          # the gaps by nutrient market
        "pool_solver_status", # the last pool clearing's solver status
        "pool_eu_unaccounted", # the EU manure not accounted for
        "market_supply_hessian_info", # the market supply Hessian's record (source, file, time)
        "market_supply_hessian_log", # its records of the run
    )


_REMOVED = "removed (refactor stage 4 E1, 2 November 2026: written, never read)"

MOVED_MODEL: dict = {
    "endotech": _REMOVED,
    "_ration_prev": _REMOVED,
    "_yani_trace": _REMOVED,
    "_pool_trace": _REMOVED,
    "_pool_flows": _REMOVED,
    "_pool_solver": _REMOVED,
    # E4 (par), E5 (sv without the manure pools)
    "_eu_base_cache": "par.eu_base_cache",
    "_yani_ref": "par.yani_ref",
    "_base_supply_cache": "par.base_supply_cache",
    "_ghg_coef_cache": "par.ghg_coef_cache",
    "_hessian_key": "par.hessian_key",
    "_endotech_key": "par.endotech_key",
    "_dairy_yield_cache": "par.dairy_yield_cache",
    "_proc_yield_cache": "par.proc_yield_cache",
    "_sugar_rate_cache": "par.sugar_rate_cache",
    "_pool_cost_cache": "par.pool_cost_cache",
    "_ration_model": "par.ration_model",
    "_feed_rations_stable": "par.feed_rations_stable",
    "_feed_rations_for": "par.feed_rations_for",
    "_excluded_units": "par.excluded_units",
    "_hessian_pending": "removed (S7, 8 November 2026: the Hessian is measured at the baseline's start)",
    "_relax_w": "sv.relax_w",
    "_relax_gprev": "sv.relax_gprev",
    "_capri_target_hist": "sv.capri_target_hist",
    "_capri_blockdev_hist": "sv.capri_blockdev_hist",
    "_capri_special_hist": "sv.capri_special_hist",
    "_capri_sup_hist": "sv.capri_sup_hist",
    "_capri_sup_full": "sv.capri_sup_full",
    "_capri_yani_hist": "sv.capri_yani_hist",
    "_milk_ms_full": "sv.milk_ms_full",
    "_eu_dev": "sv.eu_dev",
    "_sup_dev": "sv.sup_dev",
    "_special_ms_dev": "sv.special_ms_dev",
    "_sup_w": "sv.sup_w",
    "_sup_gprev": "sv.sup_gprev",
    "_milk_ms_signal": "sv.milk_ms_signal",
    "_milk_ms_w": "sv.milk_ms_w",
    "_milk_ms_gprev": "sv.milk_ms_gprev",
    "_milk_ms_hist": "sv.milk_ms_hist",
    "_yani_w": "sv.yani_w",
    "_yani_gprev": "sv.yani_gprev",
    "_capri_stop": "sv.capri_stop",
    "_trace_prev_prem": "sv.trace_prev_prem",
    "_trace_go_prev": "sv.trace_go_prev",
    "_trace_nlp_prev": "sv.trace_nlp_prev",
    "_trace_nlp_t": "sv.trace_nlp_t",
    # E6 (the manure pools), E7 (seen, ev, res)
    "_pool_state": "sv.pool_state",
    "_pool_accel": "sv.pool_accel",
    "_pool_pk": "sv.pool_pk",
    "_last_spol": "seen.last_spol",
    "_last_supply_results": "seen.last_supply_results",
    "_outer_iter_now": "ev.outer_iter_now",
    "_ls_by_country": "ev.ls_by_country",
    "_blockdev_target_now": "ev.blockdev_target_now",
    "_hessian_at_scenario": "ev.hessian_at_scenario",
    "_yani_np": "ev.yani_np",
    "_ration_state": "ev.ration_state",
    "_calib_drift": "res.calib_drift",
    "_calib_trace": "res.calib_trace",
    "_capri_stop_verdict": "res.capri_stop_verdict",
    "_capri_drift": "res.capri_drift",
    "_eu_dev_gap": "res.eu_dev_gap",
    "_sup_dev_gap": "res.sup_dev_gap",
    "_sup_dev_worst": "res.sup_dev_worst",
    "_sup_dev_gap_all": "res.sup_dev_gap_all",
    "_milk_ms_worst": "res.milk_ms_worst",
    "_milk_ms_small_gap": "res.milk_ms_small_gap",
    "_nlp_tol_trace": "res.nlp_tol_trace",
    "_outer_history": "res.outer_history",
    "_yani_imbalance": "res.yani_imbalance",
    "_yani_detail": "res.yani_detail",
    "_pool_imbalance": "res.pool_imbalance",
    "_pool_worst_key": "res.pool_worst_key",
    "_pool_gaps": "res.pool_gaps",
    "_pool_solver_status": "res.pool_solver_status",
    "_pool_eu_unaccounted": "res.pool_eu_unaccounted",
    "market_supply_hessian_info": "res.market_supply_hessian_info",
    "market_supply_hessian_log": "res.market_supply_hessian_log",
}


class ModelStateMixin(_StateMixin):
    """CAPRIModel's par, sv, ev, seen and res."""
    _MOVED = MOVED_MODEL
    _KINDS = {"par": ModelParameters, "sv": ModelSolveState, "ev": ModelEvalState, "seen": ModelSeen,
              "res": ModelResults}
