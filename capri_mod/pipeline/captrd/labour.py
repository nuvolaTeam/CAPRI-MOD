"""CAPTRD's bounds on agricultural labour from the farm holders' age lines and the activities' minimum labour
(baseline/labour_ageline.gms, CAPRI star 3.0; included at captrd.gms l. 902, after the household labour LABH and before
the policy data).

Age lines (AGELINE(region, age, year), dat/baseline/ageline.gdx: holders by age in the farm structure surveys, for the
NUTS 1 regions of SRNUTS1): each country's holders of working age (25-65) give annual change rates between survey
years (l. 37-58), filled forward over the years (l. 62-63), and their product from the base year to each ex-ante year
is the expected change of labour (l. 69). Its bounds across the countries (l. 75-89):
    MIN_CHANGE = max(the smallest expected change of any country with one - 0.05, own - 0.1, 0)
    MAX_CHANGE = min(the largest expected change of any country + 0.05, own + 0.1, 1)   (own term where it has one)
Minimum labour (l. 92-180): each activity's minimum requirement p_minLabourPerAct (h per unit, 2008), per country
MIN(minimum, 0.75 minimum + 0.25 the country's own LABT), less 0.5% a year from the base year; the country's total at
its base levels against its base labour GROF LABT gives EXPT_fromAct, x 0.9 the lower and x 1.5 the upper bound. The
bounds CAPTRD keeps (l. 199-205): MINS LABO = max(MIN from the age lines, MIN from the activities), MAXS LABO =
max(MAX from the age lines, MAX from the activities), per ex-ante year.

MS is CAPTRD's MS set (sets_captrd.gms: RMSSUP, every country), whatever countries a run prepares: the bounds of the age
lines are across all of them.

Data: capri_data/pipeline/captrd/dat/ageline.csv and p_minlabourperact.csv (tools/build/build_captrd_dat.py), the set
SRNUTS1 (tools/build/build_captrd_sets.py).
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Optional

import pandas as pd

from capri_mod.csvio import read_csv
from capri_mod.pipeline.captrd.prepare import CaptrdSets, DAT_DIR

W_AGE = {str(a) for a in range(25, 66)}                      # l. 32: SET W_AGE /25*65/
#: l. 42-58: (survey year, next survey year) of each annual change rate
PERIODS = [(1993, 1995), (1995, 1997), (1997, 2000), (2000, 2003), (2003, 2012), (2012, 2015)]
TECH_PROGRESS = 0.995                                        # l. 159: 0.5% less minimum requirement a year


def read_labour_dat(path: Path = DAT_DIR) -> Dict:
    ag = read_csv(path / "ageline.csv", keep_default_na=False, dtype={"region": str, "age": str, "year": str})
    ml = read_csv(path / "p_minlabourperact.csv", keep_default_na=False)
    return {"ageline": ag, "min_labour": dict(zip(ml.act, ml.value))}


def ageline_bounds(ageline: pd.DataFrame, sets: CaptrdSets, years: Iterable[int], exante: Iterable[int],
                   base_year: int) -> Dict[str, Dict[tuple, float]]:
    """l. 34-89: {"expt", "min", "max"} per (MS, ex-ante year), for every country of CAPTRD's MS set."""
    yrs = sorted(int(y) for y in years)
    yset = {str(y) for y in yrs}
    a = ageline[ageline["region"].isin(sets.srnuts1) & ageline["age"].isin(W_AGE) & ageline["year"].isin(yset)]
    grof_n1 = a.groupby(["region", "year"])["value"].sum()                 # l. 34
    ms = list(sets.ms)
    grof: Dict[tuple, float] = {}
    for (r, y), v in grof_n1.items():                                       # l. 36: the country's NUTS 1 regions
        for m in ms:
            if (m, r) in sets.map_rr:
                grof[(m, int(y))] = grof.get((m, int(y)), 0.0) + float(v)
    change: Dict[tuple, float] = {}
    for m in ms:
        for y0, y1 in PERIODS:                                              # l. 42-58
            g0 = grof.get((m, y0), 0.0)
            if g0:
                change[(m, y0)] = (grof.get((m, y1), 0.0) / g0) ** (1.0 / (y1 - y0))
        prev = 0.0
        for y in yrs:                                                       # l. 62-63: sequential (LOOP)
            if not change.get((m, y), 0.0) and prev:
                change[(m, y)] = prev
            prev = change.get((m, y), 0.0)
    exa = sorted(int(y) for y in exante)
    expt = {(m, e): _prod(change.get((m, y), 0.0) for y in yrs if base_year <= y < e) for m in ms for e in exa}
    mn: Dict[tuple, float] = {}
    mx: Dict[tuple, float] = {}
    for e in exa:
        have = [expt[(m, e)] for m in ms if expt[(m, e)]]
        smax = max(expt[(m, e)] for m in ms)
        for m in ms:
            x = expt[(m, e)]
            # l. 75-77; SMIN over an empty set is +INF in GAMS, so no country with data gives MIN_CHANGE = +INF
            mn[(m, e)] = max(min(have) - 0.05, x - 0.1, 0.0) if have else float("inf")
            mx[(m, e)] = min(smax + 0.05, x + 0.1, 1.0) if x else min(smax + 0.05, 1.0)   # l. 81-89
    return {"expt": expt, "min": mn, "max": mx}


def _prod(xs) -> float:
    v = 1.0
    for x in xs:
        v *= x
    return v


def labour_bounds(p: pd.DataFrame, ms: str, sets: CaptrdSets, bounds: Dict[str, Dict[tuple, float]],
                  min_labour: Dict[str, float], exante: Iterable[int], years: Iterable[int],
                  base_year: int) -> pd.DataFrame:
    """l. 152-205 for the country ms: p_data(ms, "MAXS"/"MINS", "LABO", ex-ante year), assigned (a zero deletes)."""
    basm = p[(p["region"] == ms) & (p["t"] == "BASM")]
    labt = basm[basm["row"] == "LABT"].set_index("col")["value"].astype(float)
    levl = basm[basm["row"] == "LEVL"].set_index("col")["value"].astype(float)
    req_b = {}
    for a in sorted(sets.mpact):                                            # l. 155-157
        mv = float(min_labour.get(a, 0.0))
        req_b[a] = min(mv, 0.75 * mv + 0.25 * float(labt.get(a, 0.0)))
    grof_b = float(labt.get("GROF", 0.0))                                   # l. 166
    yrs = sorted(int(y) for y in years)
    rows = []
    for e in sorted(int(y) for y in exante):
        f = TECH_PROGRESS ** sum(1 for y in yrs if base_year <= y < e)      # l. 159: PROD over the YEARS between
        req = sum(req_b[a] * f * float(levl.get(a, 0.0)) * 0.001 for a in req_b)   # l. 169
        mn_act = req / grof_b * 0.9 if grof_b else 0.0                      # l. 175-176
        mx_act = req / grof_b * 1.5 if grof_b else 0.0
        mn = max(bounds["min"].get((ms, e), 0.0), mn_act)                   # l. 199-200
        mx = max(bounds["max"].get((ms, e), 0.0), mx_act)
        rows += [(ms, "MAXS", "LABO", str(e), mx), (ms, "MINS", "LABO", str(e), mn)]
    new = pd.DataFrame(rows, columns=["region", "col", "row", "t", "value"])
    keep = ~((p["region"] == ms) & p["col"].isin(["MAXS", "MINS"]) & (p["row"] == "LABO") & p["t"].isin(set(new["t"])))
    new = new[new["value"] != 0]
    for c in p.columns:
        if c not in new.columns:
            new[c] = 0 if c == "eps" else None
    return pd.concat([p[keep], new[p.columns]], ignore_index=True)


def apply(p: pd.DataFrame, sets: CaptrdSets, ms: Iterable[str], years: Iterable[int], exante: Iterable[int],
          base_year: int, dat: Optional[Dict] = None, bounds: Optional[Dict] = None) -> pd.DataFrame:
    """labour_ageline.gms on one country's p_data (bounds: ageline_bounds of the run, computed once)."""
    dat = read_labour_dat() if dat is None else dat
    if bounds is None:
        bounds = ageline_bounds(dat["ageline"], sets, years, exante, base_year)
    for m in ms:
        if m in set(p["region"]):
            p = labour_bounds(p, m, sets, bounds, dat["min_labour"], exante, years, base_year)
    return p
