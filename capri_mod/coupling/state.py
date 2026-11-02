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
    __slots__ = ()


class ModelSolveState(_Slots):
    """State carried from one outer iteration (or run) to the next."""
    __slots__ = ()


class ModelEvalState(_Slots):
    """One outer iteration's working values."""
    __slots__ = ()


class ModelSeen(_Slots):
    """What the coupling recorded from the modules' last solve."""
    __slots__ = ()


class ModelResults(_Slots):
    """Results and diagnostics of the run."""
    __slots__ = ()


_REMOVED = "removed (refactor stage 4 E1, 2 November 2026: written, never read)"

MOVED_MODEL: dict = {
    "endotech": _REMOVED,
    "_ration_prev": _REMOVED,
    "_yani_trace": _REMOVED,
    "_pool_trace": _REMOVED,
    "_pool_flows": _REMOVED,
    "_pool_solver": _REMOVED,
}


class ModelStateMixin(_StateMixin):
    """CAPRIModel's par, sv, ev, seen and res."""
    _MOVED = MOVED_MODEL
    _KINDS = {"par": ModelParameters, "sv": ModelSolveState, "ev": ModelEvalState, "seen": ModelSeen,
              "res": ModelResults}
