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
    __slots__ = ()


class EnvEvalState(_Slots):
    """One region's evaluation, passed between the blocks."""
    __slots__ = ()


class EnvSeen(_Slots):
    """What the caller set before the evaluation."""
    __slots__ = ()


class EnvResults(_Slots):
    """The last evaluation's results kept for a reader."""
    __slots__ = ()


_REMOVED = "removed (refactor stage 4 E1, 2 November 2026: written, never read)"

MOVED_ENV: dict = {
    "_leaching_last": _REMOVED,
}


class EnvStateMixin(_StateMixin):
    """EnvironmentalModule's par, ev, seen and res (no state between iterations)."""
    _MOVED = MOVED_ENV
    _KINDS = {"par": EnvParameters, "ev": EnvEvalState, "seen": EnvSeen, "res": EnvResults}
