"""The state objects' kit (refactor stages 3 and 4): the slot base class, the mixin that gives a model its par, sv,
ev, seen and res objects with the guard on moved names, and the helpers that read and write a field or a "kind.field"
path. Written for the supply (capri_mod/supply/state.py, STAGE3B_PLAN.md) and shared since stage 4's second half with
the environment (capri_mod/environmental/state.py) and the coupling (capri_mod/coupling/state.py); the supply's module
re-exports every name, so its importers are unchanged.
"""
from __future__ import annotations


class _Slots:
    """A slot class: the fields a subclass declares in __slots__, absent until set."""
    __slots__ = ()

    def __repr__(self):
        set_ = {k: getattr(self, k) for k in self.__slots__ if hasattr(self, k)}
        return f"{type(self).__name__}({', '.join(sorted(set_))})"


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


def get_path_or(model, path, default=None):
    """The entry's value, or default where the model does not hold it (dict.get for an entry of a state list)."""
    return get_path(model, path) if has_path(model, path) else default


def setdefault_path(model, path, default):
    """dict.setdefault for an entry of a state list: its value if held (None included), else default, set."""
    if has_path(model, path):
        return get_path(model, path)
    set_path(model, path, default)
    return default


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
            raise RuntimeError(f"{type(self).__name__}.{name} is now {moved[name]} (refactor stages 3-4)")
        raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")

    def __setattr__(self, name, value):
        moved = type(self)._MOVED
        if name in moved:
            raise RuntimeError(f"{type(self).__name__}.{name} is now {moved[name]} (refactor stages 3-4)")
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
