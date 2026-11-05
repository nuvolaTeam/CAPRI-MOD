"""The model's parameters, from one file: <data_dir>/shared/model_parameters.csv (capri_data's for the repository).

Every constant the model's economics or accounting rests on - CAPRI's parameters, the IPCC factors as CAPRI uses
them, JRC121368's assumptions, the few model settings that are not CAPRI data - is a row there, with its unit, kind
(capri, ipcc, jrc121368, legal, literature, model_setting) and source. Numerical tolerances (solver iterations,
convergence tolerances) stay in the code: they are not economics. A test checks that the file and the code agree
(no row unused, no parameter missing).

    from capri_mod.params import param, param_table
    OVERFERT_MARKUP = param("OVERFERT_MARKUP")
    FIBRE_FACTOR = param_table("FIBRE_FACTOR")          # {key: value}
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

#: the repository's file (the run's is <data_dir>/shared/model_parameters.csv, through capri_mod.data.inputs)
FILE = Path(__file__).resolve().parents[1] / "capri_data" / "shared" / "model_parameters.csv"


def _load() -> Dict[tuple, float]:
    """The run's parameters: the file of the data directory the run's inputs follow (capri_mod.data.inputs.current();
    the repository's data until a model sets them). A name read at import (a module constant) takes the repository's
    file; the supply's parameters are read where they are used (refactor stage 3, N1)."""
    from capri_mod.data import inputs as _inputs
    return _inputs.current().parameters()


def param(name: str) -> float:
    """A scalar parameter; raises if it is not in the file."""
    try:
        return _load()[(name, "")]
    except KeyError:
        raise KeyError(f"parameter {name!r} is not in the run's {FILE.name}") from None


def param_table(name: str) -> Dict[str, float]:
    """A keyed parameter as {key: value}; raises if it is not in the file."""
    out = {k: v for (n, k), v in _load().items() if n == name and k}
    if not out:
        raise KeyError(f"parameter table {name!r} is not in the run's {FILE.name}")
    return out


def names() -> set:
    return {n for n, _ in _load()}
