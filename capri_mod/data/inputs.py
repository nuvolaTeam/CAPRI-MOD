"""The run's data adapter: the code that reads the model's input files (refactor stages 3b and 4b,
docs/design/ARCHITECTURE_REFACTOR.md, layer "data adapters"; the market has its own, capri_mod/market/inputs.py).

Every input is located in the data directory and base year of the run:
    <data_dir>/<base_year>/<area>/<file>   area: supply, abatement, environment, feed, policy, market
    <data_dir>/shared/<file>                cross-vintage mappings
    <data_dir>/sources/<sub>/<file>         CAPRI exports read as inputs
Before 30 October 2026 the supply, environment, fertiliser and water code read a fixed capri_data/2017 path next to
the package (and the PMP elasticity table a path relative to the working directory), so another data directory or
base year was ignored.

The run's inputs are set once (use: SupplyModule sets them from the model's data directory and base year); the tables
the code keeps at module or class level are cached on the inputs object (cached), so a run on another data directory
or base year reads its own files. capri_mod/supply/inputs.py is the supply package's name for it.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Optional

import pandas as pd

from capri_mod.tableio import read_input

REPO_DATA = Path(__file__).resolve().parents[2] / "capri_data"
AREAS = ("supply", "abatement", "environment", "feed", "policy", "market")


class RunInputs:
    """Paths and readers of the model's inputs for one data directory and base year."""

    def __init__(self, data_dir: Optional[Path] = None, base_year: Optional[str] = None):
        self.root = Path(data_dir) if data_dir else REPO_DATA
        self.base_year = str(base_year) if base_year is not None else default_base_year()
        self.cache: dict = {}

    # -- locations -----------------------------------------------------------------------------------------------
    def path(self, name: str, where: str) -> Path:
        """where: an area of the base year (AREAS, with a subfolder: "abatement/ammonia"), "shared",
        "scenarios/<folder>" (a scenario group's or reference's data, refactor stage 5) or "root" (the data
        directory itself). Not "sources/<sub>": the model reads no file under capri_data/sources (refused since
        3 November 2026; the builders read it)."""
        if where == "root":
            return self.root / name
        if where.startswith("sources/") or where == "sources":
            raise ValueError(f"{where!r}: the model reads no file under capri_data/sources (the builders' extracts of CAPRI's material, capri_data/sources/README.md); a builder writes what the model needs as an input (3 November 2026)")
        if where == "shared" or where.startswith("scenarios/"):
            return self.root / where / name
        if where.split("/")[0] in AREAS:
            return self.root / self.base_year / where / name
        raise ValueError(f"unknown input location {where!r}")

    def exists(self, name: str, where: str) -> bool:
        return self.path(name, where).exists()

    # -- readers -------------------------------------------------------------------------------------------------
    def csv(self, name: str, where: str, required: bool = True, **read_kw) -> Optional[pd.DataFrame]:
        """The table as pandas reads it with read_kw; None for a missing input that is not required."""
        p = self.path(name, where)
        if not p.exists():
            if required:
                raise FileNotFoundError(f"input {p} is missing")
            return None
        return read_input(p, **read_kw)

    def json(self, name: str, where: str, required: bool = True) -> Any:
        p = self.path(name, where)
        if not p.exists():
            if required:
                raise FileNotFoundError(f"input {p} is missing")
            return None
        with open(p) as fh:
            return json.load(fh)

    def rows(self, name: str, where: str, required: bool = True) -> Optional[list]:
        """The rows of a CSV as dicts of strings (csv.DictReader), None for a missing input that is not required."""
        return self.rows_at(self.path(name, where), required)

    def rows_at(self, p: Path, required: bool = True) -> Optional[list]:
        """rows of a CSV at a path this object located (path, resolve)."""
        import csv
        p = Path(p)
        if not p.exists():
            if required:
                raise FileNotFoundError(f"input {p} is missing")
            return None
        with open(p, newline="") as fh:
            return list(csv.DictReader(fh))

    def resolve(self, name: str) -> Optional[Path]:
        """The location capri_mod.data.loaders.resolve_data_file gives a file of its catalogue (shared, the base year's
        category folder, or the data directory itself)."""
        from capri_mod.data.loaders import resolve_data_file
        return resolve_data_file(self.root, name, base_year=self.base_year)

    def need(self, path: Path) -> Path:
        """path, which must exist (a missing input stops the run, naming the file)."""
        if path is None or not Path(path).exists():
            raise FileNotFoundError(f"input {path} is missing")
        return Path(path)

    def read(self, path: Path, **read_kw) -> pd.DataFrame:
        """A table at a path this object located (path, resolve)."""
        return read_input(path, **read_kw)

    def parameters(self) -> dict:
        """The model's parameters, {(name, key): value}, from <data_dir>/shared/model_parameters.csv (capri_mod.params;
        refactor stage 3, N1: read through the run's inputs, not from a path next to the package)."""
        def _load(s):
            import csv
            tab = {}
            with open(s.need(s.path("model_parameters.csv", "shared")), newline="") as f:
                for r in csv.DictReader(f):
                    k = (r["name"], r.get("key") or "")
                    if k in tab:
                        raise ValueError(f"model_parameters.csv: duplicate {k}")
                    tab[k] = float(r["value"])
            return tab
        return self.cached("model_parameters", _load)

    def cached(self, key: str, load: Callable[["RunInputs"], Any]) -> Any:
        """load(self), computed once per inputs object."""
        if key not in self.cache:
            self.cache[key] = load(self)
        return self.cache[key]


_CURRENT: Optional[RunInputs] = None


def default_base_year() -> str:
    """The settings' base year (run.base_year), the default of every reader without one (KNOWN_ISSUES K52f, 2 November
    2026: the base year is a parameter of the run, no reader fixes 2017)."""
    from capri_mod.settings import current as _settings
    return str(_settings().get("run.base_year"))


def base_year() -> str:
    """The run's base year (the current inputs')."""
    return current().base_year


def market_year(data) -> int:
    """The year of CAPRI's market data a data set is calibrated to: data["market_year"] (the projection layer sets it),
    else the data's base year, else the run's."""
    d = data if isinstance(data, dict) else {}
    return int(d.get("market_year") or d.get("base_year") or base_year())


def check_base_year(data_dir, base_year) -> None:
    """Stop where the data directory has no folder for the base year, naming the years it has (a missing file in it
    stops the run where it is read, naming the file)."""
    root = Path(data_dir) if data_dir else REPO_DATA
    if not (root / str(base_year)).is_dir():
        have = sorted(p.name for p in root.iterdir() if p.is_dir() and p.name.isdigit()) if root.is_dir() else []
        raise FileNotFoundError(f"base year {base_year}: no data folder {root / str(base_year)} "
                                f"(base years with data in {root}: {', '.join(have) or 'none'})")


def use(inputs: RunInputs) -> RunInputs:
    """Make inputs the run's inputs (SupplyModule sets it when built)."""
    global _CURRENT
    _CURRENT = inputs
    return inputs


def current() -> RunInputs:
    """The run's inputs; the repository's data and base year 2017 when no SupplyModule has set them."""
    global _CURRENT
    if _CURRENT is None:
        _CURRENT = RunInputs()
    return _CURRENT
