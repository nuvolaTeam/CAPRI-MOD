"""CAPTRD's bounds on agricultural labour from the farm holders' age lines and the activities' minimum labour
(baseline/labour_ageline.gms, CAPRI star 3.0; included at captrd.gms l. 902, after the household labour LABH and before
the policy data).

Age lines (AGELINE(region, age, year), dat/baseline/ageline.gdx: holders by age in the farm structure surveys, for the
NUTS 1 regions of SRNUTS1): each country's holders of working age (25-65) give annual change rates between survey
years (l. 39-55), filled forward over the years (l. 59-60), and their product from the base year to each ex-ante year
is the expected change of labour (l. 66). Its bounds across the countries (l. 74-87):
    MIN_CHANGE = max(the smallest expected change of any country with one - 0.05, own - 0.1, 0)
    MAX_CHANGE = min(the largest expected change of any country + 0.05, own + 0.1, 1)   (own term where it has one)
Minimum labour (l. 92-189): each activity's minimum requirement p_minLabourPerAct (h per unit, 2008), per country
MIN(minimum, 0.75 minimum + 0.25 the country's own LABT), less 0.5% a year from the base year; the country's total at
its base levels against its base labour GROF LABT gives EXPT_fromAct, x 0.9 the lower and x 1.5 the upper bound. The
bounds CAPTRD keeps (l. 198-205): MINS LABO = max(MIN from the age lines, MIN from the activities), MAXS LABO =
max(MAX from the age lines, MAX from the activities), per ex-ante year. Each statement's arithmetic is a named function
in capri_mod/pipeline/captrd/equations/labour_ageline.py.

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
from capri_mod.pipeline.captrd.equations import labour_ageline as LA
from capri_mod.pipeline.captrd.prepare import CaptrdSets, DAT_DIR

W_AGE = {str(a) for a in range(25, 66)}                      # l. 31: SET W_AGE /25*65/
#: l. 39-55: (survey year, next survey year) of each annual change rate
PERIODS = [(1993, 1995), (1995, 1997), (1997, 2000), (2000, 2003), (2003, 2012), (2012, 2015)]


def read_labour_dat(path: Path = DAT_DIR) -> Dict:
    ag = read_csv(path / "ageline.csv", keep_default_na=False, dtype={"region": str, "age": str, "year": str})
    ml = read_csv(path / "p_minlabourperact.csv", keep_default_na=False)
    return {"ageline": ag, "min_labour": dict(zip(ml.act, ml.value))}


def ageline_bounds(ageline: pd.DataFrame, sets: CaptrdSets, years: Iterable[int], exante: Iterable[int],
                   base_year: int) -> Dict[str, Dict[tuple, float]]:
    """l. 33-87: {"expt", "min", "max"} per (MS, ex-ante year), for every country of CAPTRD's MS set; the statements'
    arithmetic in capri_mod/pipeline/captrd/equations/labour_ageline.py."""
    yrs = sorted(int(y) for y in years)
    yset = {str(y) for y in yrs}
    a = ageline[ageline["region"].isin(sets.srnuts1) & ageline["age"].isin(W_AGE) & ageline["year"].isin(yset)]
    grof_n1 = LA.AGELINE_GROF_SRNUTS1(a)                                   # l. 33
    ms = list(sets.ms)
    regional: Dict[tuple, list] = {}
    for (r, y), v in grof_n1.items():                                       # l. 35: the country's NUTS 1 regions
        for m in ms:
            if (m, r) in sets.map_rr:
                regional.setdefault((m, int(y)), []).append(v)
    grof = {k: LA.AGELINE_GROF_MS(v) for k, v in regional.items()}
    change: Dict[tuple, float] = {}
    for m in ms:
        for y0, y1 in PERIODS:                                              # l. 39-55
            g0 = grof.get((m, y0), 0.0)
            if g0:
                change[(m, y0)] = LA.AGELINE_ANUAL_CHANGE(g0, grof.get((m, y1), 0.0), y1 - y0)
        prev = 0.0
        for y in yrs:                                                       # l. 59-60: sequential (LOOP)
            if not change.get((m, y), 0.0) and prev:
                change[(m, y)] = LA.AGELINE_ANUAL_CHANGE_fill(prev)
            prev = change.get((m, y), 0.0)
    exa = sorted(int(y) for y in exante)
    expt = {(m, e): LA.AGELINE_EXPT_CHANGE([change.get((m, y), 0.0) for y in yrs if base_year <= y < e])
            for m in ms for e in exa}                                       # l. 66
    mn: Dict[tuple, float] = {}
    mx: Dict[tuple, float] = {}
    for e in exa:
        have = [expt[(m, e)] for m in ms if expt[(m, e)]]
        smax = max(expt[(m, e)] for m in ms)
        for m in ms:
            mn[(m, e)] = LA.AGELINE_MIN_CHANGE(expt[(m, e)], have)          # l. 74-76
            mx[(m, e)] = LA.AGELINE_MAX_CHANGE(expt[(m, e)], smax)          # l. 80-87
    return {"expt": expt, "min": mn, "max": mx}


def labour_bounds(p: pd.DataFrame, ms: str, sets: CaptrdSets, bounds: Dict[str, Dict[tuple, float]],
                  min_labour: Dict[str, float], exante: Iterable[int], years: Iterable[int],
                  base_year: int) -> pd.DataFrame:
    """l. 156-205 for the country ms: p_data(ms, "MAXS"/"MINS", "LABO", ex-ante year), assigned (a zero deletes); the
    statements' arithmetic in capri_mod/pipeline/captrd/equations/labour_ageline.py."""
    basm = p[(p["region"] == ms) & (p["t"] == "BASM")]
    labt = basm[basm["row"] == "LABT"].set_index("col")["value"].astype(float)
    levl = basm[basm["row"] == "LEVL"].set_index("col")["value"].astype(float)
    req_b = {}
    for a in sorted(sets.mpact):                                            # l. 175
        req_b[a] = LA.p_labourPerAct_MinRequirement_BASM(float(min_labour.get(a, 0.0)), float(labt.get(a, 0.0)))
    grof_b = float(labt.get("GROF", 0.0))                                   # l. 180
    yrs = sorted(int(y) for y in years)
    rows = []
    for e in sorted(int(y) for y in exante):
        n = sum(1 for y in yrs if base_year <= y < e)                       # l. 177: PROD over the YEARS between
        req = LA.p_labourPerAct_GROF_MinRequirement(
            [(LA.p_labourPerAct_MinRequirement(req_b[a], n), float(levl.get(a, 0.0))) for a in req_b])   # l. 183
        mn_act, mx_act = LA.p_labourPerAct_fromAct(req, grof_b)            # l. 186-189
        mn = LA.p_labourPerAct_CHANGE(bounds["min"].get((ms, e), 0.0), mn_act)   # l. 198, 205
        mx = LA.p_labourPerAct_CHANGE(bounds["max"].get((ms, e), 0.0), mx_act)   # l. 199, 204
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
