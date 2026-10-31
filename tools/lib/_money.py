"""CAPRI's money of a simulation year in the model's money (KNOWN_ISSUES K108, 31 October 2026).

The model works in 2017 money: its 2030 prices and premiums are CAPRI's 2030 ones over CAPRI's general inflation
p_infl^(2030 - 2017) (tools/build/build_price_trajectory_2030.py; capri_data/trajectories/capri_price_ratios_2030.csv,
column deflator: the median over the inputs of UVAG 2030 / UVAG 2017 per member state, 1.019^13 = 1.2772 in every one).
CAPRI's own terms of its 2030 calibration and results (PMP terms, land rents, unit values, mitigation costs and cost
savings) are in its 2030 money; a builder that hands one of them to the model divides it by deflator(2030), the same
number the prices take, so that every term of a 2030 run is in one money.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BASE_YEAR = 2017


@lru_cache(maxsize=None)
def deflator(year: int) -> float:
    """CAPRI's money of `year` per unit of the model's (2017) money: 1 for the base year, else the deflator of
    capri_price_ratios_<year>.csv (one value: CAPRI's p_infl is one index for every member state; an error if not)."""
    if int(year) == BASE_YEAR:
        return 1.0
    p = ROOT / "capri_data" / "trajectories" / f"capri_price_ratios_{int(year)}.csv"
    d = pd.read_csv(p, float_precision="round_trip")["deflator"].astype(float)
    if d.empty or (d.max() - d.min()) > 1e-12 * d.max():
        raise ValueError(f"{p.name}: the deflator is not one value ({d.min()} to {d.max()})")
    return float(d.iloc[0])
