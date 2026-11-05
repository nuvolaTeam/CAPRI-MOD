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
    """Where a moved name appears as a string constant in capri_mod or tools (outside the tests and state.py): the
    form of getattr/setattr/hasattr names, __dict__ keys and tuples of names (SOLVE_STATE and the like), which the
    runtime guard does not see. Any string equal to the name counts."""
    found = []
    for base in (ROOT / "capri_mod", ROOT / "tools"):
        for f in base.rglob("*.py"):
            if "tests" in f.parts or f == ROOT / "capri_mod" / "supply" / "state.py":    # where MOVED is declared
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
    # a public input moved under its own name (feed_rations -> seen.feed_rations, S9) is not searched: its new field
    # and the supply module's own attribute of that name are read by the same string; the runtime guard covers it
    names = {k for k, v in (*S.MOVED_REGIONAL.items(), *S.MOVED_MODULE.items()) if v.rpartition(".")[2] != k}
    found = _string_uses(names) if names else []
    assert not found, "\n".join(found)


def test_the_emission_tax_is_taken_back_once_on_the_same_net_revenues():
    """Refactor stage 3, S7 (plan section 4.2): _apply_ghg_tax's undo record (ev.ghg_applied) acts only on the net
    revenues object it was added to (ev.ghg_nr_obj, an identity check): applied twice on the same object the tax is
    there once; on a rebuilt object nothing is taken back."""
    import pandas as pd
    m = RegionalSupplyModel.__new__(RegionalSupplyModel)
    m.seen.ghg_tax, m.seen.ghg_coef = 2.0, {"act": {"SWHE": 1.5, "DCOW": 3.0}}
    m.net_revenues = pd.Series({"SWHE": 100.0, "DCOW": 50.0})
    m._apply_ghg_tax()
    m._apply_ghg_tax()
    assert m.net_revenues.to_dict() == {"SWHE": 97.0, "DCOW": 44.0}
    assert m.ev.ghg_nr_obj is m.net_revenues and m.ev.ghg_applied == {"SWHE": 3.0, "DCOW": 6.0}
    m.net_revenues = pd.Series({"SWHE": 100.0, "DCOW": 50.0})     # rebuilt: a new object, nothing to take back
    m._apply_ghg_tax()
    assert m.net_revenues.to_dict() == {"SWHE": 97.0, "DCOW": 44.0}
