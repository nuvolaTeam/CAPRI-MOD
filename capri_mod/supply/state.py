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

This step (S0c) adds the objects empty and the guard; the fields move into them block by block in the following
commits, each a pure move checked against the mini-EU run. A moved name is listed in MOVED_REGIONAL / MOVED_MODULE:
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
    __slots__ = ()


class RegionalSolveState(_Slots):
    """A regional model's state carried from one solve to the next."""
    __slots__ = ()


class RegionalEvalState(_Slots):
    """A regional model's working values within one solve."""
    __slots__ = ()


class RegionalSeen(_Slots):
    """What the supply module and the coupling set on a regional model before its solve."""
    __slots__ = ()


class RegionalResults(_Slots):
    """A regional model's last solve: results and diagnostics."""
    __slots__ = ()


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
}
#: the supply module's former attribute names
MOVED_MODULE: dict = {
    "_base_cal_drift": _REMOVED,
}


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
