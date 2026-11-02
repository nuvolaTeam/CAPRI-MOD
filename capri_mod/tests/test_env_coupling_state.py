"""The environment's and the coupling's state objects and the guard on moved names (refactor stage 4, second half;
capri_mod/environmental/state.py, capri_mod/coupling/state.py; docs/design/ENV_COUPLING_STATE_INVENTORY.md)."""
from __future__ import annotations

import ast
import copy
import pickle
from pathlib import Path

import pytest

from capri_mod.coupling import state as C
from capri_mod.environmental import state as E
from capri_mod.environmental.environmental_module import EnvironmentalModule
from capri_mod.model import CAPRIModel

ROOT = Path(__file__).resolve().parents[2]
#: moved names another class still uses for its own field: SupplyModule's own inner fertiliser model (supply_module.py)
#: and the regional models' NLP_STATE entry "_nlp_tol_trace" (a name the regional models never hold, so the Hessian's
#: restore never finds it; CAPRIModel's own field moved to res.nlp_tol_trace)
SHARED_NAMES = {"_inner_fert", "_nlp_tol_trace"}
STATE_FILES = {ROOT / "capri_mod" / "environmental" / "state.py", ROOT / "capri_mod" / "coupling" / "state.py"}


def test_state_objects_are_created_on_first_use():
    """The objects exist on instances built without __init__ (as tests' stubs are); the environment has no sv."""
    m = CAPRIModel.__new__(CAPRIModel)
    for kind, cls in (("par", C.ModelParameters), ("sv", C.ModelSolveState), ("ev", C.ModelEvalState),
                      ("seen", C.ModelSeen), ("res", C.ModelResults)):
        assert isinstance(getattr(m, kind), cls) and getattr(m, kind) is getattr(m, kind)
    e = EnvironmentalModule.__new__(EnvironmentalModule)
    for kind, cls in (("par", E.EnvParameters), ("ev", E.EnvEvalState), ("seen", E.EnvSeen), ("res", E.EnvResults)):
        assert isinstance(getattr(e, kind), cls)
    with pytest.raises(AttributeError):
        e.sv
    assert getattr(m, "no_such_attribute", "default") == "default"


def test_a_moved_name_raises_on_read_and_write(monkeypatch):
    """A moved name raises RuntimeError, so a getattr default cannot hide it (the Hessian's cache key reads coupling
    fields with defaults: hessian.py)."""
    monkeypatch.setitem(C.MOVED_MODEL, "_old_field", "sv.old_field")
    m = CAPRIModel.__new__(CAPRIModel)
    with pytest.raises(RuntimeError, match="sv.old_field"):
        getattr(m, "_old_field", None)
    with pytest.raises(RuntimeError, match="sv.old_field"):
        m._old_field = 1
    monkeypatch.setitem(E.MOVED_ENV, "_old_env", "par.old")
    e = EnvironmentalModule.__new__(EnvironmentalModule)
    with pytest.raises(RuntimeError, match="par.old"):
        hasattr(e, "_old_env")


def test_instances_with_state_objects_pickle_and_copy():
    """The environment crosses the workers' fork and the tests deep-copy the model: both keep the objects."""
    for cls, kinds in ((CAPRIModel, ("par", "sv")), (EnvironmentalModule, ("par", "ev"))):
        o = cls.__new__(cls)
        o.some_attribute = {"a": 1.0}
        for k in kinds:
            getattr(o, k)
        for o2 in (pickle.loads(pickle.dumps(o)), copy.deepcopy(o), copy.copy(o)):
            assert o2.some_attribute == {"a": 1.0}
            for k in kinds:
                assert type(getattr(o2, k)) is type(getattr(o, k))


def test_no_moved_name_is_used_as_a_string():
    """After a move no code reaches the old name through a string (getattr(obj, "_x"), obj.__dict__["_x"], the
    manure pools' _POOL_STATE, the run script's reads), which the runtime guard cannot catch."""
    # a public name other objects share is not searched: "endotech" is also the scenario's field and the run's keyword
    # (the model's write-only copy was removed, E1); the runtime guard covers the model's
    names = {k for k, v in (*E.MOVED_ENV.items(), *C.MOVED_MODEL.items())
             if v.rpartition(".")[2] != k and k.startswith("_")} - SHARED_NAMES
    found = []
    for base in (ROOT / "capri_mod", ROOT / "tools"):
        for f in base.rglob("*.py"):
            if "tests" in f.parts or f in STATE_FILES:
                continue
            try:
                tree = ast.parse(f.read_text())
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in names:
                    found.append(f"{f.relative_to(ROOT)}:{node.lineno}: {node.value}")
    assert not found, "\n".join(found)
