"""The environmental module's parameters and state, by kind (refactor stage 4, second half;
docs/design/ENV_COUPLING_STATE_INVENTORY.md).

EnvironmentalModule holds what it keeps between calls in declared objects, as the supply's models do
(capri_mod/supply/state.py):
- ``par``: memos of the base data, built on first use (the inner fertiliser model, the row caches, the unit balances);
- ``ev``: one region's evaluation (compute_indicators), passed between its blocks;
- ``seen``: what the caller sets on the module before an evaluation (the manure-trade switch);
- ``res``: the last evaluation's results kept for a reader.

It has no ``sv``: nothing is carried from one iteration to the next (the memos are keyed on their inputs).

E0 adds the objects empty and the guard; the fields move in E2-E3, each commit a pure move checked against the
mini-EU run. A moved name is listed in MOVED_ENV: reading or writing it on the module raises RuntimeError (not
AttributeError, so a getattr default cannot hide it). Reads and writes through ``__dict__`` and names held in strings
are not seen by the guard; capri_mod/tests/test_env_coupling_state.py scans the code for them.
"""
from __future__ import annotations

from capri_mod.statekit import _Slots, _StateMixin


class EnvParameters(_Slots):
    """Memos of the base data, built on first use."""
    __slots__ = (
        "mloss_cache",        # manure N lost in housing and storage, by region and animal
        "nexc_cache",         # manure N per head, by (region, animal)
        "mn2o_cache",         # manure N2O factors, by (region, animal)
        "mn2o_tech_cache",    # the technologies' N2O effects and base shares, by region
        "mn2o_tech_tab",      # manure_n2o_tech.csv
        "amm_tm",             # CAPRI's ammonia sub-activities (ammonia_tech_model.csv), loaded by _manure_n2o_tech
        "nh3_fac_cache",      # NH3 factors, by region
        "sub_cache",          # manure substitution terms, by region (dropped when the manure-trade switch changes)
        "row_cache",          # one region's row of a data table, by (table, region)
        "need_base_cache",    # the base crop need weights, by region
        "res_av_cache",       # residue availability, by region
        "unit_nb_memo",       # unit N balances, by (region, activity, yields, intensity, trade)
        "inner_fert",         # the inner fertiliser model (InnerFertDist), also reached from the supply's blocks
        "min_n2o_cache",      # mineral N2O-N per N, by region
        "p_ratio_base",       # the manure P applied ratio at the first call, by CAPRI region
    )


class EnvEvalState(_Slots):
    """One region's evaluation, passed between the blocks."""
    __slots__ = (
        "nitrate_share_now",  # the nitrate shares of the region's rations
        "supp_ch4",           # the feed supplements' enteric CH4 factor, by region (kept for every region seen)
        "feed_dm_now",        # feed dry matter per animal of the region
        "region_now",         # the region being evaluated
        "nh3_saved_last",     # NH3-N kept by the ammonia options
        "n_kept_last",        # manure N kept by the options
        "nitrate_nh3_extra",  # NH3 of the nitrate supplement's extra N
        "fert_dist_now",      # the region's fertiliser distribution rows
    )


class EnvSeen(_Slots):
    """What the caller set before the evaluation."""
    __slots__ = (
        "manure_trade_on",    # the run's manure trade switch (set_manure_trade; read with the default True)
    )


class EnvResults(_Slots):
    """The last evaluation's results kept for a reader."""
    __slots__ = (
        "last_fert_dist",     # the run's fertiliser distribution table (the model's results["fert_dist"])
    )


_REMOVED = "removed (refactor stage 4 E1, 2 November 2026: written, never read)"

MOVED_ENV: dict = {
    "_leaching_last": _REMOVED,
    # E2 (par), E3 (ev, seen, res)
    "_mloss_cache": "par.mloss_cache",
    "_nexc_cache": "par.nexc_cache",
    "_mn2o_cache": "par.mn2o_cache",
    "_mn2o_tech_cache": "par.mn2o_tech_cache",
    "_mn2o_tech_tab": "par.mn2o_tech_tab",
    "_amm_tm": "par.amm_tm",
    "_nh3_fac_cache": "par.nh3_fac_cache",
    "_sub_cache": "par.sub_cache",
    "_row_cache": "par.row_cache",
    "_need_base_cache": "par.need_base_cache",
    "_res_av_cache": "par.res_av_cache",
    "_unit_nb_memo": "par.unit_nb_memo",
    "_inner_fert": "par.inner_fert",
    "_min_n2o_cache": "par.min_n2o_cache",
    "_p_ratio_base": "par.p_ratio_base",
    "_nitrate_share_now": "ev.nitrate_share_now",
    "_supp_ch4": "ev.supp_ch4",
    "_feed_dm_now": "ev.feed_dm_now",
    "_region_now": "ev.region_now",
    "_nh3_saved_last": "ev.nh3_saved_last",
    "_n_kept_last": "ev.n_kept_last",
    "_nitrate_nh3_extra": "ev.nitrate_nh3_extra",
    "_fert_dist_now": "ev.fert_dist_now",
    "manure_trade_on": "seen.manure_trade_on",
    "last_fert_dist": "res.last_fert_dist",
}


class EnvStateMixin(_StateMixin):
    """EnvironmentalModule's par, ev, seen and res (no state between iterations)."""
    _MOVED = MOVED_ENV
    _KINDS = {"par": EnvParameters, "ev": EnvEvalState, "seen": EnvSeen, "res": EnvResults}
