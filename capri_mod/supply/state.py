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


class _Slots:
    """A slot class: the fields a subclass declares in __slots__, absent until set."""
    __slots__ = ()

    def __repr__(self):
        set_ = {k: getattr(self, k) for k in self.__slots__ if hasattr(self, k)}
        return f"{type(self).__name__}({', '.join(sorted(set_))})"


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
        "grass_cz",           # the grass split's term
        "grass_pending_col",  # the grass split's column waiting for the duals
        # fertilisation (S5): memos of the base and CAPRI's priors recalibrated at the first solve
        "ef_lea_cache",       # the leaching emission factor (a memo)
        "ef_min_n2o_cache",   # mineral fertiliser's N2O per kg N, CO2 equivalent (a memo)
        "min_n2o_parts_cache",  # its parts (a memo)
        "npk_kappa",          # the fertiliser distribution's kappa by nutrient (a memo)
        "npk_prior_override", # CAPRI's priors where the calibration recalibrated them
        "npk_prior_recalibrated",  # the nutrients whose priors were recalibrated
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
        "n_relax_sticky",     # the N-target relaxation kept from one solve to the next (not restored by the Hessian)
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
        "grass_col",          # the grass split's column
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
    )


class RegionalSeen(_Slots):
    """What the supply module and the coupling set on a regional model before its solve."""
    __slots__ = ()


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
    )


class ModuleParameters(_Slots):
    """The supply module's parameters, built once per base."""
    __slots__ = ()


class ModuleSolveState(_Slots):
    """The supply module's state carried between regional passes."""
    __slots__ = ()


class ModuleSeen(_Slots):
    """What the model (CAPRIModel) sets on the supply module."""
    __slots__ = ()


class ModuleResults(_Slots):
    """The supply module's last pass: results and diagnostics."""
    __slots__ = ()


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
    "_grass_cz": "par.grass_cz",
    "_grass_pending_col": "par.grass_pending_col",
    "_cattle_cols": "ev.cattle_cols",
    "_dairy_col": "ev.dairy_col",
    "_dairy_req_extra": "ev.dairy_req_extra",
    "_genet_cols": "ev.genet_cols",
    "_grass_col": "ev.grass_col",
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
}
#: the supply module's former attribute names
MOVED_MODULE: dict = {
    "_base_cal_drift": _REMOVED,
}


def setdefault(obj, name, default):
    """dict.setdefault for a field of a state object: the field's value if set (None included), else default, set."""
    try:
        return getattr(obj, name)
    except AttributeError:
        setattr(obj, name, default)
        return default


def discard(obj, name):
    """Unset a field of a state object if it is set (dict.pop(name, None) for a field)."""
    try:
        delattr(obj, name)
    except AttributeError:
        pass


def pop(obj, name, default=None):
    """dict.pop(name, default) for a field of a state object: its value, unset, or default if it was not set."""
    try:
        v = getattr(obj, name)
    except AttributeError:
        return default
    delattr(obj, name)
    return v


def _split(path):
    kind, dot, name = path.partition(".")
    return (kind, name) if dot else (None, path)


def has_path(model, path):
    """Whether the model holds the entry of a state list (RegionalSupplyModel.NLP_STATE, SOLVE_STATE): an attribute
    name (in the instance's __dict__ only, as the Hessian's restore always took them) or "kind.field" (a field set in
    the model's state object; an object not yet created holds nothing)."""
    kind, name = _split(path)
    if kind is None:
        return name in model.__dict__
    obj = model.__dict__.get("_" + kind)
    return obj is not None and hasattr(obj, name)


def get_path(model, path):
    kind, name = _split(path)
    return model.__dict__[name] if kind is None else getattr(model.__dict__["_" + kind], name)


def set_path(model, path, value):
    kind, name = _split(path)
    if kind is None:
        model.__dict__[name] = value
    else:
        setattr(getattr(model, kind), name, value)


def del_path(model, path):
    """Remove the entry if the model holds it."""
    kind, name = _split(path)
    if kind is None:
        model.__dict__.pop(name, None)
    else:
        obj = model.__dict__.get("_" + kind)
        if obj is not None:
            discard(obj, name)


class _StateMixin:
    """The objects, created on first use (also on models built without __init__, as tests' stubs are), and the guard
    on the moved names."""
    _MOVED: dict = {}
    _KINDS: dict = {}

    def __getattr__(self, name):
        # only reached for names the instance and its class do not have
        moved = type(self)._MOVED
        if name in moved:
            raise RuntimeError(f"{type(self).__name__}.{name} is now {moved[name]} (refactor stage 3)")
        raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")

    def __setattr__(self, name, value):
        moved = type(self)._MOVED
        if name in moved:
            raise RuntimeError(f"{type(self).__name__}.{name} is now {moved[name]} (refactor stage 3)")
        object.__setattr__(self, name, value)

    def _state(self, kind):
        st = self.__dict__.get("_" + kind)
        if st is None:
            cls = type(self)._KINDS.get(kind)
            if cls is None:
                raise AttributeError(f"{type(self).__name__!r} object has no attribute {kind!r}")
            st = self.__dict__["_" + kind] = cls()
        return st

    @property
    def par(self):
        return self._state("par")

    @property
    def sv(self):
        return self._state("sv")

    @property
    def ev(self):
        return self._state("ev")

    @property
    def seen(self):
        return self._state("seen")

    @property
    def res(self):
        return self._state("res")


class RegionalStateMixin(_StateMixin):
    """RegionalSupplyModel's par, sv, ev, seen and res."""
    _MOVED = MOVED_REGIONAL
    _KINDS = {"par": RegionalParameters, "sv": RegionalSolveState, "ev": RegionalEvalState, "seen": RegionalSeen,
              "res": RegionalResults}


class ModuleStateMixin(_StateMixin):
    """SupplyModule's par, sv, seen and res (it has no per-solve working state of its own)."""
    _MOVED = MOVED_MODULE
    _KINDS = {"par": ModuleParameters, "sv": ModuleSolveState, "seen": ModuleSeen, "res": ModuleResults}
