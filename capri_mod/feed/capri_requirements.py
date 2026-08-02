"""
Real CAPRI feed requirements, replacing the hardcoded constants in feed_module.

Background
----------
`feed_module.py` carried 56 hardcoded numbers for live weights, production days
and fattening days. Two of them were materially wrong:

    PRODUCTION_DAYS   model   CAPRI median   range
    BULL                365            151   14-360
    PIGF                180            129   76-220

Bulls at 365 days rather than 151 overstates annual feed intake per animal by
roughly 2.4x, which propagates into livestock gross margins and the whole
nitrogen balance. Dairy cows, hens and sows are genuinely 365 and were correct.

The real values come from capreg's DATA2, items:

    ENNE  net energy requirement
    CRPR  crude protein requirement
    DRMN  dry matter intake, minimum
    DRMX  dry matter intake, maximum
    DAYS  production days per year

Note that reqrel_17*.gdx does NOT hold these. Its `p_animReqCorrFac1` is a set
of correction factors -- roughly +/-10% adjustments applied to ENNE and CRPR --
not the requirements themselves.

Coverage is 192 of 248 regions. Uncovered regions keep the literature defaults,
and the source of every value is recorded rather than silently blended.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

REQ_FILE = "sources/capreg/capreg_feed_requirements.csv"

# CAPRI activity name -> model activity name.
CAPRI_TO_MODEL = {
    "DCOW": "DCOW", "DCOL": "DCOW", "DCOH": "DCOW",
    "BULL": "BULL", "BULF": "BULL", "BULH": "BULL",
    "SCOW": "BCOW",
    "HEIF": "HFRS", "HEIR": "HFRS", "HEIH": "HFRS", "HEIL": "HFRS",
    "CAFF": "CALV", "CAFR": "CALV", "CAMF": "CALV", "CAMR": "CALV",
    "SHGF": "SHGP", "SHGM": "SHGP",
    "SOWS": "PIGS",
    "PIGF": "PIGF",
    "HENS": "LAYS",
    "POUF": "BROI",
}


def load_requirements(data_dir: Path) -> pd.DataFrame:
    """Wide frame indexed by (region, model activity), columns = requirement items."""
    path = Path(data_dir) / REQ_FILE
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    df["model_activity"] = df["activity"].map(CAPRI_TO_MODEL)
    df = df.dropna(subset=["model_activity"])
    # Several CAPRI activities map to one model activity (four heifer classes to
    # HFRS, for instance). Average rather than take the last, since the classes
    # are genuine subdivisions of the same herd.
    return df.pivot_table(index=["model_region", "model_activity"],
                          columns="item", values="value", aggfunc="mean")


def production_days(data_dir: Path, defaults: Dict[str, float]
                    ) -> Tuple[pd.DataFrame, dict]:
    """
    Region x activity production days, real where CAPRI has them.

    Returns the table and a provenance summary. Values outside 1-366 are
    rejected as parse errors rather than silently used.
    """
    req = load_requirements(data_dir)
    if req.empty or "DAYS" not in req.columns:
        return pd.DataFrame(), {"status": "unavailable"}

    days = req["DAYS"].unstack()
    days = days.where((days >= 1) & (days <= 366))

    n_real = int(days.notna().sum().sum())
    summary = {
        "regions": int(days.shape[0]),
        "activities": int(days.shape[1]),
        "real_cells": n_real,
        "median_by_activity": {a: round(float(days[a].median()), 1)
                               for a in days.columns if days[a].notna().any()},
        "defaults_differing": {
            a: {"default": defaults.get(a),
                "capri_median": round(float(days[a].median()), 1)}
            for a in days.columns
            if a in defaults and days[a].notna().any()
            and abs(days[a].median() - defaults[a]) / max(defaults[a], 1) > 0.05},
    }
    return days, summary


def nutrient_requirements(data_dir: Path) -> pd.DataFrame:
    """
    Net energy (ENNE) and crude protein (CRPR) requirements per head per year.

    These are what the feed module's own energy and protein balances should be
    solved against, in place of values derived from assumed live weights.
    """
    req = load_requirements(data_dir)
    if req.empty:
        return pd.DataFrame()
    keep = [c for c in ("ENNE", "CRPR", "DRMN", "DRMX") if c in req.columns]
    return req[keep]
