"""The model's parameters, from one file: capri_data/shared/model_parameters.csv.

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

import csv
from pathlib import Path
from typing import Dict, Optional

FILE = Path(__file__).resolve().parents[1] / "capri_data" / "shared" / "model_parameters.csv"
_TAB: Optional[Dict[tuple, float]] = None


def _load() -> Dict[tuple, float]:
    global _TAB
    if _TAB is None:
        tab = {}
        with open(FILE, newline="") as f:
            for r in csv.DictReader(f):
                k = (r["name"], r.get("key") or "")
                if k in tab:
                    raise ValueError(f"model_parameters.csv: duplicate {k}")
                tab[k] = float(r["value"])
        _TAB = tab
    return _TAB


def param(name: str) -> float:
    """A scalar parameter; raises if it is not in the file."""
    try:
        return _load()[(name, "")]
    except KeyError:
        raise KeyError(f"parameter {name!r} is not in {FILE.name}") from None


def param_table(name: str) -> Dict[str, float]:
    """A keyed parameter as {key: value}; raises if it is not in the file."""
    out = {k: v for (n, k), v in _load().items() if n == name and k}
    if not out:
        raise KeyError(f"parameter table {name!r} is not in {FILE.name}")
    return out


def names() -> set:
    return {n for n, _ in _load()}
