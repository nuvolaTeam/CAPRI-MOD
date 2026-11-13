"""CAPTRD's animal requirement functions (captrd/prep_requirement_estimation.gms, captrd/define_stats_and_supports.gms
l. 86-93; CAPRI star 3.0).

CAPTRD does not project the animals' energy, protein, fibre and dry-matter requirements (REQST: ENNE, CRPR, FILG, FICT,
FISM, FISF) with their own trends. It estimates a linear relation between each requirement and the animal's main
output coefficient (its yield, PACT_TO_Y) and projects the requirement from the projected yield:

estimate (prep_requirement_estimation.gms), on one country's prepared p_data (after statistics.statistics, whose feed
input coefficients it reads):
  1  per country (MS) and animal (MAACT) x requirement, ordinary least squares over the ex-post years ExPost in which
     the requirement is observed (l. 17-39): y = the requirement, x = the sum of the animal's yields (PACT_TO_Y);
       Slope = max(0, Sxy / Sxx) where nObs and Sxx are nonzero, Const = mean(y) - mean(x) Slope where nObs;
     the sums of x run over the years with a requirement, the sum of y over every ExPost year (a missing y adds 0)
  2  copied from the country to its regions (Rest: the country and its NUTS 2 regions; CAPTRD's farm types are not
     ported) (l. 44-49): Slope where the region's LEVL has a BASM, Const where its LEVL has observations (nObs), and the
     requirement's BASM = Const + Slope x the yields' BASM where LEVL has a BASM
  3  scaled to the base-year feed (l. 61-71): the factor = sum over the feeds with a base-year input coefficient of
     coefficient x the country's content of the requirement in that feed (p_data(MS, REQST, FEED, "BASM")) / the
     requirement's BASM, where LEVL has observations and the BASM is nonzero, else 0; Const and Slope multiplied by
     it, and the requirement's BASM recomputed (Const + Slope x yields' BASM, in every region, animal and requirement:
     0 where the factor is 0). The base-year requirement therefore equals the energy, protein, ... the base-year ration
     supplies.
step1 (define_stats_and_supports.gms l. 86-93): the requirement's Step1 in each ex-ante year, where the requirement
     has observations (the statistics' nObs) = (Const + Slope x the sum of the yields' Step1) x 0.998^(t - 2000), a
     0.2% efficiency gain a year ("exclusively based on WB's assumptions (so far)", l. 91).

Which values are observations follows step1.observed (setting captrd.zeros_as_missing): the count of the requirement's
years and the years whose yields enter Sx, Sxx and Sxy are its observed years.

As coded, kept: the requirements of a region whose LEVL has no observations lose their coefficients and their BASM at
step 3 (the factor is 0); Const and Slope are copied to a region under different conditions (LEVL nObs, LEVL BASM).
"""
from __future__ import annotations

from typing import Dict, Iterable, Optional, Set, Tuple

import numpy as np
import pandas as pd

from capri_mod.pipeline.captrd.prepare import CaptrdSets
from capri_mod.pipeline.captrd.step1 import observed, zeros_missing

KEYS = ["region", "col", "row"]
#: define_stats_and_supports.gms l. 91-92: 0.2% less requirement per unit of output a year, counted from 2000
EFFICIENCY = 0.998
EFFICIENCY_FROM = 2000


def _yields(sets: CaptrdSets) -> Dict[str, Set[str]]:
    out: Dict[str, Set[str]] = {}
    for a, o in sets.pact_to_y:
        if a in sets.maact:
            out.setdefault(a, set()).add(o)
    return out


def coefficients(p: pd.DataFrame, sets: CaptrdSets, expost: Iterable[int],
                 zeros_as_missing: Optional[bool] = None) -> pd.DataFrame:
    """Const, Slope and the requirement's BASM per (region, animal, requirement) after steps 1-3 (module docstring),
    indexed by KEYS, with the scaling factor ("scale"), the country regression's nObs ("nObs_reg") and Const and Slope
    before the scaling ("Const0", "Slope0"). Sums run over sorted members, so the results do not depend on Python's
    hash order."""
    zm = zeros_missing(zeros_as_missing)
    ex = [str(int(y)) for y in expost]
    reqst = set(sets.reqst)
    ys = _yields(sets)
    ms_set = set(sets.ms)
    ms_of = {r: m for m, r in sets.map_rr if m in ms_set}
    sub = p[p["col"].isin(sets.maact) | p["col"].isin(reqst)]
    wide = sub.pivot_table(index=KEYS, columns="t", values="value", aggfunc="first")
    for c in ex + ["BASM", "nObs"]:
        if c not in wide.columns:
            wide[c] = np.nan
    regions = sorted({r for r in wide.index.get_level_values("region") if r in sets.rest})

    def val(r, c, row, t):
        try:
            v = wide.at[(r, c, row), t]
        except KeyError:
            return 0.0
        return 0.0 if pd.isna(v) else float(v)

    rows = []
    # 1: the country regression
    reg: Dict[Tuple[str, str, str], Tuple[float, float, float]] = {}
    for m in [r for r in regions if r in ms_set]:
        for a, outs in ys.items():
            xk = [(m, a, o) for o in sorted(outs) if (m, a, o) in wide.index]
            X = sum((wide.loc[k, ex].to_numpy(float) for k in xk), np.zeros(len(ex)))
            X = np.nan_to_num(X)
            for q in reqst:
                k = (m, a, q)
                if k not in wide.index:
                    continue
                y, obs = observed(wide.loc[k, ex].to_numpy(float)[None, :], zm)
                y, obs = y[0], obs[0]
                n = float(obs.sum())
                if not n:
                    continue
                sx, sxx = float(X[obs].sum()), float((X[obs] ** 2).sum())
                sy, sxy = float(y.sum()), float((y[obs] * X[obs]).sum())
                x1 = sxy - sx * sy / n
                x2 = sxx - sx * sx / n
                slope = max(0.0, x1 / x2) if x2 else 0.0
                reg[k] = (sy / n - sx / n * slope, slope, n)
    # 2: copied to the regions, requirement BASM; 3: scaled to the base-year feed
    for r in regions:
        m = ms_of.get(r)
        for a, outs in ys.items():
            lv_basm = val(r, a, "LEVL", "BASM")
            lv_nobs = val(r, a, "LEVL", "nObs")
            y_basm = sum(val(r, a, o, "BASM") for o in sorted(outs))
            for q in reqst:
                c0, s0, n0 = reg.get((r, a, q), (0.0, 0.0, 0.0)) if r in ms_set else (0.0, 0.0, 0.0)
                cm, sm, _ = reg.get((m, a, q), (0.0, 0.0, 0.0))
                slope = sm if lv_basm else s0
                const = cm if lv_nobs else c0
                basm = const + slope * y_basm if lv_basm else val(r, a, q, "BASM")
                scale = 0.0
                if lv_nobs and basm:
                    num = 0.0
                    for f in sorted(sets.feed):
                        fb = val(r, a, f, "BASM")
                        if fb:
                            num += fb * val(m, q, f, "BASM")
                    scale = num / basm
                rows.append((r, a, q, const * scale, slope * scale, (const + slope * y_basm) * scale, scale, n0,
                             const, slope))
    out = pd.DataFrame(rows, columns=KEYS + ["Const", "Slope", "BASM", "scale", "nObs_reg", "Const0", "Slope0"]
                       ).set_index(KEYS)
    return out


def estimate(p: pd.DataFrame, sets: CaptrdSets, expost: Iterable[int],
             zeros_as_missing: Optional[bool] = None) -> pd.DataFrame:
    """p_data with the positions Const and Slope of the requirements added and the requirements' BASM replaced
    (prep_requirement_estimation.gms; module docstring)."""
    co = coefficients(p, sets, expost, zeros_as_missing)
    keys = pd.MultiIndex.from_frame(p[KEYS])
    req = keys.isin(co.index)
    drop = req & p["t"].isin(["Const", "Slope", "BASM"]).to_numpy()
    rest = p[~drop]
    long = co[["Const", "Slope", "BASM"]].reset_index().melt(id_vars=KEYS, var_name="t", value_name="value")
    long = long[long["value"] != 0.0]
    for c in p.columns:
        if c not in long.columns:
            long[c] = 0 if c == "eps" else None
    return pd.concat([rest, long[p.columns]], ignore_index=True)


def step1(co: pd.DataFrame, nobs: pd.Series, yield_step1: pd.DataFrame, sets: CaptrdSets) -> pd.DataFrame:
    """The requirements' Step1 (define_stats_and_supports.gms l. 86-93): co with Const and Slope (coefficients),
    nobs the statistics' nObs per series, yield_step1 the yields' Step1 (index KEYS, the ex-ante years as columns).
    Returns the requirements' Step1 with the same columns, where nObs is nonzero."""
    ys = _yields(sets)
    years = list(yield_step1.columns)
    eff = np.array([EFFICIENCY ** (int(t) - EFFICIENCY_FROM) for t in years])
    out = {}
    for (r, a, q), c in co[["Const", "Slope"]].iterrows():
        if not nobs.get((r, a, q), 0.0):
            continue
        x = np.zeros(len(years))
        for o in sorted(ys.get(a, ())):
            if (r, a, o) in yield_step1.index:
                x = x + np.nan_to_num(yield_step1.loc[(r, a, o)].to_numpy(float))
        out[(r, a, q)] = (c["Const"] + c["Slope"] * x) * eff
    res = pd.DataFrame.from_dict(out, orient="index", columns=years)
    res.index = pd.MultiIndex.from_tuples(res.index, names=KEYS) if len(res) else pd.MultiIndex.from_tuples([], names=KEYS)
    return res
