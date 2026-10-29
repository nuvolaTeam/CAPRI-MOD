"""The run settings of capri-mod: one authoritative value per setting (agreed 23 October 2026).

Every switch, tolerance, iteration limit and algorithm choice of a run lives in ``defaults.toml`` (next to this file),
grouped by section (run, outer_loop, supply, fertiliser, market, young_animals, environment, projection, endotech,
diagnostics), each key commented with what it does and CAPRI's equivalent; where capri-mod departs from CAPRI the
comment says so (DEPARTURE). Sourced economic parameters stay in capri_data/shared/model_parameters.csv
(capri_mod.params), CAPRI's structure in mapping CSVs, scenarios in scenario definitions.

Use:
    from capri_mod import settings
    s = settings.load(["my_run.toml"], overrides={"supply.pmp_source": "recipe"})
    settings.activate(s)                     # the process-wide settings every module reads
    with settings.override({"market.eu_blocks": True}):
        model.run(...)                       # temporarily changed, restored on exit
    settings.current().get("outer_loop.outer_tolerance")
    s.save("run.settings.toml")              # the effective settings of a run

In the code a setting is read through a ``setting("section.key")`` class attribute (a descriptor), so classes keep
their attribute names (``RegionalSupplyModel.use_land_market``) but the value always comes from the active settings:
there is no second default to drift apart (getattr fallbacks, class duplicates) and nothing to carry to a projected
model by hand. Assigning to such an attribute is an error: change the settings instead.

Validation: an override or a user file may only name keys that exist in defaults.toml, with a value of the same type
(int accepted where a float is expected); anything else stops with the key named.
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Union

DEFAULTS_FILE = Path(__file__).resolve().parent / "defaults.toml"

__all__ = ["Settings", "load", "defaults", "current", "activate", "override", "setting", "SettingsError"]


class SettingsError(ValueError):
    """An unknown key or a value of the wrong type in a settings file or override."""


def _type_ok(default: Any, value: Any) -> bool:
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(default, int):
        return isinstance(value, int) and not isinstance(value, bool)
    if isinstance(default, float):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if isinstance(default, str):
        return isinstance(value, str)
    if isinstance(default, list):
        return isinstance(value, list)
    if isinstance(default, dict):
        return isinstance(value, dict)
    return True


class Settings:
    """An immutable set of settings: {"section.key": value}."""

    __slots__ = ("_flat", "_sources", "_key")

    def __init__(self, flat: Mapping[str, Any], sources: Iterable[str] = ()):
        self._flat = {k: copy.deepcopy(v) for k, v in flat.items()}
        self._sources = tuple(sources)
        self._key = None

    def get(self, key: str) -> Any:
        try:
            v = self._flat[key]
        except KeyError:
            raise SettingsError(f"unknown setting {key!r} (not in {DEFAULTS_FILE.name})") from None
        return copy.deepcopy(v) if isinstance(v, (list, dict)) else v

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def __contains__(self, key: str) -> bool:
        return key in self._flat

    def section(self, name: str) -> Dict[str, Any]:
        p = name + "."
        return {k[len(p):]: self.get(k) for k in self._flat if k.startswith(p)}

    def items(self):
        return ((k, self.get(k)) for k in self._flat)

    @property
    def sources(self):
        return self._sources

    def replace(self, overrides: Mapping[str, Any], source: str = "override") -> "Settings":
        """A copy with the overrides applied (validated against the defaults)."""
        base = _defaults_flat()
        new = dict(self._flat)
        for k, v in _flatten_overrides(overrides).items():
            if k not in base:
                raise SettingsError(f"{source}: unknown setting {k!r} (not in {DEFAULTS_FILE.name})")
            if not _type_ok(base[k], v):
                raise SettingsError(f"{source}: setting {k!r} must be {type(base[k]).__name__}, got {v!r}")
            new[k] = float(v) if isinstance(base[k], float) and isinstance(v, int) else v
        return Settings(new, self._sources + (source,))

    def diff(self, other: Optional["Settings"] = None) -> Dict[str, Any]:
        """{key: value} where this differs from `other` (default: the defaults)."""
        o = other._flat if other is not None else _defaults_flat()
        return {k: v for k, v in self._flat.items() if o.get(k) != v}

    def key(self) -> str:
        """A short hash of every value: equal settings, equal key (for caches)."""
        if self._key is None:
            blob = json.dumps(self._flat, sort_keys=True, default=str).encode()
            self._key = hashlib.sha1(blob).hexdigest()[:16]
        return self._key

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for k, v in self._flat.items():
            sec, name = k.split(".", 1)
            out.setdefault(sec, {})[name] = copy.deepcopy(v)
        return out

    def to_toml(self) -> str:
        lines = [f"# capri-mod effective settings; sources: {', '.join(self._sources) or 'defaults'}",
                 f"# changed from the defaults: {', '.join(sorted(self.diff())) or 'none'}"]
        for sec, kv in self.to_dict().items():
            lines.append(f"\n[{sec}]")
            for k, v in kv.items():
                lines.append(f"{k} = {_toml_value(v)}")
        return "\n".join(lines) + "\n"

    def save(self, path: Union[str, Path]) -> Path:
        p = Path(path)
        p.write_text(self.to_toml())
        return p

    def __eq__(self, other):
        return isinstance(other, Settings) and self._flat == other._flat

    def __hash__(self):
        return hash(self.key())

    def __repr__(self):
        d = self.diff()
        return f"Settings({len(self._flat)} keys, {len(d)} changed: {sorted(d)[:6]}{'...' if len(d) > 6 else ''})"

    def __getstate__(self):
        return {"flat": self._flat, "sources": self._sources}

    def __setstate__(self, st):
        self._flat, self._sources, self._key = st["flat"], st["sources"], None


def _toml_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, list):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k} = {_toml_value(x)}" for k, x in v.items()) + " }"
    raise SettingsError(f"cannot write {v!r} as TOML")


def _flatten_overrides(d: Mapping) -> Dict[str, Any]:
    """Accepts {"section.key": v} and {"section": {"key": v}}."""
    out = {}
    for k, v in d.items():
        if "." in k:
            out[k] = v
        elif isinstance(v, Mapping):
            for k2, v2 in v.items():
                out[f"{k}.{k2}"] = v2
        else:
            raise SettingsError(f"setting {k!r}: give it as 'section.key'")
    return out


_DEFAULTS_FLAT: Optional[Dict[str, Any]] = None


def _defaults_flat() -> Dict[str, Any]:
    global _DEFAULTS_FLAT
    if _DEFAULTS_FLAT is None:
        with open(DEFAULTS_FILE, "rb") as f:
            raw = tomllib.load(f)
        flat = {}
        for sec, kv in raw.items():
            if not isinstance(kv, Mapping):
                raise SettingsError(f"{DEFAULTS_FILE.name}: {sec!r} is not a section")
            for k, v in kv.items():
                flat[f"{sec}.{k}"] = v
        _DEFAULTS_FLAT = flat
    return _DEFAULTS_FLAT


def defaults() -> Settings:
    return Settings(_defaults_flat(), ("defaults",))


def load(files: Iterable[Union[str, Path]] = (), overrides: Optional[Mapping[str, Any]] = None) -> Settings:
    """The defaults, then each TOML file in order, then the overrides; every key validated."""
    s = defaults()
    for f in files:
        p = Path(f)
        with open(p, "rb") as fh:
            raw = tomllib.load(fh)
        s = s.replace(raw, source=str(p))
    if overrides:
        s = s.replace(overrides, source="overrides")
    return s


_ACTIVE: Optional[Settings] = None


def current() -> Settings:
    """The process-wide active settings (the defaults until something is activated)."""
    global _ACTIVE
    if _ACTIVE is None:
        _ACTIVE = defaults()
    return _ACTIVE


def activate(s: Settings) -> Settings:
    """Make `s` the active settings; returns the previous ones."""
    global _ACTIVE
    if not isinstance(s, Settings):
        raise SettingsError(f"activate() needs a Settings, got {type(s).__name__}")
    prev = current()
    _ACTIVE = s
    return prev


@contextlib.contextmanager
def override(overrides: Union[Mapping[str, Any], Settings]):
    """Temporarily change the active settings (tests, sensitivity runs); restored on exit."""
    prev = current()
    new = overrides if isinstance(overrides, Settings) else prev.replace(overrides)
    activate(new)
    try:
        yield new
    finally:
        activate(prev)


class setting:
    """Class attribute reading one setting from the active settings.

        class RegionalSupplyModel:
            use_land_market = setting("supply.use_land_market")

    `convert` maps the stored value to the one the code expects (e.g. "auto" -> None). With `run_state=True` an
    instance may hold its own value for the run in hand (CAPRI's scenario settings that a scenario may set, e.g. the
    manure trade: the setting is the default, the scenario's value holds for its run and its baseline);
    ``del obj.attr`` returns the instance to the setting."""

    __slots__ = ("key", "convert", "name", "owner", "run_state")

    def __init__(self, key: str, convert=None, run_state: bool = False):
        self.key = key
        self.convert = convert
        self.name = None
        self.owner = None
        self.run_state = run_state

    def __set_name__(self, owner, name):
        self.name, self.owner = name, owner.__name__

    def __get__(self, obj, objtype=None):
        if obj is not None and self.run_state and self.name in obj.__dict__:
            return obj.__dict__[self.name]
        v = current().get(self.key)
        return self.convert(v) if self.convert is not None else v

    def __set__(self, obj, value):
        if self.run_state:
            obj.__dict__[self.name] = value
            return
        raise AttributeError(f"{self.owner}.{self.name} is the setting {self.key!r}: change it with "
                             f"capri_mod.settings.override({{{self.key!r}: ...}}) or a settings file")

    def __delete__(self, obj):
        obj.__dict__.pop(self.name, None)


def auto_none(v):
    """'auto' -> None (the code's own rule decides), else the value."""
    return None if v == "auto" else v


def tri_state(v):
    """'capri' / 'auto' -> None (CAPRI's rule), 'on' -> True, 'off' -> False."""
    return {"on": True, "off": False}.get(v, None)
