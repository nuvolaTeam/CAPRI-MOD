"""The supply models' state objects and the guard on moved names (refactor stage 3, capri_mod/supply/state.py)."""
from __future__ import annotations

import ast
import copy
import pickle
from pathlib import Path

import pytest

from capri_mod.supply import state as S
from capri_mod.supply.supply_module import RegionalSupplyModel, SupplyModule

ROOT = Path(__file__).resolve().parents[2]


def test_state_objects_are_created_on_first_use_and_absent_fields_stay_absent():
    """The objects exist on a model built without __init__ (as tests' stubs are); a field never set is absent, so a
    getattr default applies as it did for an attribute never set (plan Q1: slot classes)."""
    m = RegionalSupplyModel.__new__(RegionalSupplyModel)
    for kind, cls in (("par", S.RegionalParameters), ("sv", S.RegionalSolveState), ("ev", S.RegionalEvalState),
                      ("seen", S.RegionalSeen), ("res", S.RegionalResults)):
        assert isinstance(getattr(m, kind), cls)
        assert getattr(m, kind) is getattr(m, kind)
    sm = SupplyModule.__new__(SupplyModule)
    assert isinstance(sm.par, S.ModuleParameters) and isinstance(sm.sv, S.ModuleSolveState)
    with pytest.raises(AttributeError):
        sm.ev                                   # the supply module has no per-solve working state
    assert getattr(m, "no_such_attribute", "default") == "default"


def test_a_moved_name_raises_on_read_and_write(monkeypatch):
    """A moved name raises RuntimeError on the model, so neither a read with a getattr default nor a write to the old
    name can go unnoticed (as the market's MOVED)."""
    monkeypatch.setitem(S.MOVED_REGIONAL, "_old_field", "sv.old_field")
    m = RegionalSupplyModel.__new__(RegionalSupplyModel)
    with pytest.raises(RuntimeError, match="sv.old_field"):
        getattr(m, "_old_field", None)
    with pytest.raises(RuntimeError, match="sv.old_field"):
        m._old_field = 1
    monkeypatch.setitem(S.MOVED_MODULE, "_old_module_field", "par.old")
    sm = SupplyModule.__new__(SupplyModule)
    with pytest.raises(RuntimeError, match="par.old"):
        hasattr(sm, "_old_module_field")


def test_models_with_state_objects_pickle_and_copy():
    """The workers pickle the regional models back, and the Hessian deep-copies state: both keep the objects."""
    m = RegionalSupplyModel.__new__(RegionalSupplyModel)
    m.some_attribute = {"a": 1.0}
    m.par, m.sv                                 # created
    for m2 in (pickle.loads(pickle.dumps(m)), copy.deepcopy(m), copy.copy(m)):
        assert m2.some_attribute == {"a": 1.0}
        assert isinstance(m2.par, S.RegionalParameters) and isinstance(m2.sv, S.RegionalSolveState)


def _string_uses(names):
    """Where a moved name is used as a string in capri_mod or tools: in getattr/setattr/hasattr/delattr calls, in
    subscripts and .get/.pop/.setdefault on a __dict__, and in tuples of names (SOLVE_STATE and the like). The runtime
    guard does not see these."""
    found = []
    for base in (ROOT / "capri_mod", ROOT / "tools"):
        for f in base.rglob("*.py"):
            if "tests" in f.parts:
                continue
            try:
                tree = ast.parse(f.read_text())
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in names:
                    found.append(f"{f.relative_to(ROOT)}:{node.lineno}: {node.value}")
    return found


def test_no_moved_name_is_used_as_a_string():
    """Refactor stage 3: after a move no code reaches the old name through a string (getattr(obj, "_x"),
    obj.__dict__["_x"], a tuple of names), which the runtime guard cannot catch."""
    names = set(S.MOVED_REGIONAL) | set(S.MOVED_MODULE)
    found = _string_uses(names) if names else []
    assert not found, "\n".join(found)
