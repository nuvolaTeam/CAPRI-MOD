"""CAPTRD Step 1: the trend line x_t = a + b * t^c of every series, and its statistics.

Ported from CAPRI star 3.0:
  - captrd.gms l. 203, 271: the trend variable p_trend(t) = ORD(t)/10 over YEARS = %FirstYear%..%lastSimulationYear%;
  - prep_data_for_estimation.gms l. 205-247: nObs, nW, wAve, wVar (pre-statistics over the ex-post years ExPostT);
  - estimate_trends.gms (whole file): weighted least squares with weights t on the transformed regressor t^c, for a
    grid of 30 values of c in [0.02, 1.2], keeping the c with the smallest weighted error sum of squares;
  - define_stats_and_supports.gms l. 47-49: the trend value Step1(t) = a + b * t^c for the years YearsEst;
  - define_stats_and_supports.gms l. 118-132: the error variance wVarErr;
  - define_stats_and_supports.gms l. 177-179: wR2 = max(0, 1 - wVarErr/wVar), the term dropped where wVar = 0.
The statements' arithmetic is in capri_mod/pipeline/captrd/equations (estimate_trends.py, define_stats_and_supports.py,
prep_data_for_estimation.py), named functions quoting their GAMS.

Conventions of the GAMS code kept here:
  - which values are observations (setting captrd.zeros_as_missing; CAPRI-ERROR-FIX, register FIX-8):
      true  - CAPRI's convention (CAPTRD_MAP.md section 9, point 1): a zero is a missing observation; every count and
              sum runs over the ex-post years with a nonzero value (NaN is read as 0, so also missing);
      false - the default: NaN is a missing observation and a recorded zero is an observation (value 0). CAPREG's
              series as GAMS writes them carry no zeros (GAMS stores none), so on them the two agree; they differ
              once the data layer passes true zeros (docs/dev/CAPTRD_MOD.md section 6);
  - a GAMS parameter that is not assigned is 0: the formulas below assign 0 where the GAMS code assigns nothing.

The domain conditions on the number of observations n (estimate_trends.gms l. 76-123):
  - n > 4: the 30 grid points of c;
  - n = 3 or 4: c = 1 at the first grid point only;
  - n = 1 or 2: the regressor sums are not assigned, so b = 0 and a is the weighted mean;
  - for n <= 4 the other 29 grid points are set to zero (l. 160) and, as coded, still enter the minimum of l. 166
    (setting captrd.short_series_grid_as_coded; see fit()).

The inputs are arrays over series (rows) and ex-post years (columns); preparing the series (which series, which
years, the BASM exclusion of prep_data_for_estimation.gms l. 214-218) is the caller's task.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

import numpy as np

from capri_mod.pipeline.captrd.equations import define_stats_and_supports as DS
from capri_mod.pipeline.captrd.equations import estimate_trends as ET
from capri_mod.pipeline.captrd.equations import prep_data_for_estimation as PD
from capri_mod.settings import current as _settings


def trend_variable(years: Iterable[int], first_year: Optional[int] = None) -> np.ndarray:
    """p_trend(t) = ORD(t)/10 with ORD counted from %FirstYear% (captrd.gms l. 203, 271)."""
    fy = int(_settings().get("captrd.first_year") if first_year is None else first_year)
    t = np.asarray(list(years), dtype=int)
    if (t < fy).any():
        raise ValueError(f"years before %FirstYear% {fy}: {sorted(set(t[t < fy].tolist()))}")
    return (t - fy + 1) / 10.0


def c_grid(c_min: Optional[float] = None, c_max: Optional[float] = None, n: Optional[int] = None) -> np.ndarray:
    """The grid on c (estimate_trends.gms l. 80-82): c_k = c_min + (k-1)(c_max-c_min)/(n-1), k = 1..n."""
    s = _settings()
    c_min = float(s.get("captrd.c_min") if c_min is None else c_min)
    c_max = float(s.get("captrd.c_max") if c_max is None else c_max)
    n = int(s.get("captrd.c_grid_points") if n is None else n)
    k = np.arange(n, dtype=float)
    return c_min + k * (c_max - c_min) / (n - 1)


def zeros_missing(zeros_as_missing: Optional[bool] = None) -> bool:
    """The setting captrd.zeros_as_missing unless given."""
    return bool(_settings().get("captrd.zeros_as_missing")) if zeros_as_missing is None else bool(zeros_as_missing)


def observed(x, zeros_as_missing: Optional[bool] = None):
    """(values, mask): the values with NaN read as 0, and which of them are observations (module docstring)."""
    a = np.array(x, dtype=float, copy=True)
    if a.ndim == 1:
        a = a[None, :]
    miss = np.isnan(a)
    obs = ~miss & (a != 0.0) if zeros_missing(zeros_as_missing) else ~miss
    a[miss] = 0.0
    return a, obs


@dataclass
class PreStats:
    """prep_data_for_estimation.gms l. 205-247 (before the BASM exclusion of l. 214-218, which is the caller's)."""
    nobs: np.ndarray
    nw: np.ndarray
    wave: np.ndarray
    wvar: np.ndarray


def prestats(x, w, nobs: Optional[np.ndarray] = None, nw: Optional[np.ndarray] = None,
             zeros_as_missing: Optional[bool] = None) -> PreStats:
    """nObs, nW, wAve and wVar of each series.

    x: (series, ex-post years); w: p_trend of those years. nobs / nw may be passed when the caller has changed them
    (CAPRI zeroes both where BASM is zero, l. 214-218, and for INHA.LEVL and DOMM of young animals, l. 221-227). The
    lines cited here are prep_data_for_estimation.gms's.
    """
    x, obs = observed(x, zeros_as_missing)
    w = np.asarray(w, dtype=float)
    n0, nw0 = PD.p_data_nObs_nW(obs, w) if (nobs is None or nw is None) else (None, None)   # l. 209-210
    n = n0 if nobs is None else np.asarray(nobs, dtype=float)
    nW = nw0 if nw is None else np.asarray(nw, dtype=float)
    wave = PD.p_data_WAve(x, w, nW)                                       # l. 233-234 (zeros add nothing)
    wvar = PD.p_data_wVar(x, obs, w, n, nW, wave)                         # l. 241-246
    return PreStats(n, nW, wave, wvar)


@dataclass
class Fit:
    a: np.ndarray        # p_aTrend
    b: np.ndarray        # p_bTrend
    c: np.ndarray        # p_cTrend
    wess: np.ndarray     # p_trendRes(..., "cOpt", "wESS")
    k_opt: np.ndarray    # p_trendRes(..., "cOpt", "ordOpt") - 1 (0-based); -1 where nObs = 0


def fit(x, w, nobs, grid: Optional[np.ndarray] = None, as_coded: Optional[bool] = None,
        zeros_as_missing: Optional[bool] = None) -> Fit:
    """estimate_trends.gms: WLS of x on (1, t^c) with weights t for each c of the grid, then the c of least wESS.

    as_coded (setting captrd.short_series_grid_as_coded):
      True  - CAPRI's code: for nObs <= 4 the minimum (l. 166) runs over all 30 grid points, 29 of them zeroed at
              l. 160, so the minimum is 0 and, unless the first point fits exactly (wESS = 0), the optimum is the
              second point, whose a, b and c are 0 (l. 168-185);
      False - the minimum over the first grid point only, the intent stated at l. 158. CAPRI-ERROR-FIX, the
              default: CAPRI's own output (results_1770.gdx) has Step1 = 0 for 92 of its 93 series with 2-4
              observations (tests/test_captrd_step1.py::test_parity_with_captrd_step1).
    """
    x, obs = observed(x, zeros_as_missing)
    w = np.asarray(w, dtype=float)
    n = np.asarray(nobs, dtype=float)
    if grid is None:
        grid = c_grid()
    if as_coded is None:
        as_coded = bool(_settings().get("captrd.short_series_grid_as_coded"))
    if x.shape[0] > _CHUNK:                    # memory: the grid arrays are series x grid x years
        parts = [_fit_block(x[i:i + _CHUNK], obs[i:i + _CHUNK], w, n[i:i + _CHUNK], grid, as_coded)
                 for i in range(0, x.shape[0], _CHUNK)]
        return Fit(*(np.concatenate([getattr(p, k) for p in parts]) for k in ("a", "b", "c", "wess", "k_opt")))
    return _fit_block(x, obs, w, n, grid, as_coded)


_CHUNK = 4000


def _fit_block(x, obs, w, n, grid, as_coded) -> Fit:
    """estimate_trends.gms l. 80-183 for a block of series; the statements' arithmetic in
    capri_mod/pipeline/captrd/equations/estimate_trends.py."""
    cpar = ET.p_trendRes_cPar(n, grid)                                                 # l. 80-85
    trddep, onedep, onetrd, oneone, trdtrd = ET.p_trendRes_sums(x, obs, w, n, cpar)    # l. 94-123
    slope, const = ET.p_trendRes_slope_const(trddep, onedep, onetrd, oneone, trdtrd)  # l. 128-142
    wess = ET.p_trendRes_wESS(x, obs, w, n, cpar, slope, const)                       # l. 146-155
    ET.p_trendRes_short_zero(n, (cpar, slope, const, wess))                           # l. 160
    wmin, k_opt = ET.p_trendRes_cOpt_wESS_ordOpt(wess, n, as_coded)                   # l. 166-171
    a, b, c = ET.p_trendRes_cOpt(n, cpar, slope, const, k_opt)                        # l. 173-183
    has = n != 0
    return Fit(a, b, c, np.where(has, wmin, 0.0), np.where(has, k_opt, -1))


def step1_values(f: Fit, nobs, t_est) -> np.ndarray:
    """define_stats_and_supports.gms l. 47-49: Step1(t) = a + b * t^c for the years YearsEst, where nObs > 0."""
    return DS.p_result_Step1(f.a, f.b, f.c, nobs, t_est)


def error_variance(x, w, f: Fit, pre: PreStats, zeros_as_missing: Optional[bool] = None) -> np.ndarray:
    """define_stats_and_supports.gms l. 118-132.

    nObs > 2: sum over the observations of (x - a - b t^c)^2 * t, divided by nW - 1;
    nObs in {1, 2}: 0.25 * wAve^2 (the fall-back of l. 127-132).
    """
    x, obs = observed(x, zeros_as_missing)
    w = np.asarray(w, dtype=float)
    return DS.p_data_wVarErr(x, obs, w, f.a, f.b, f.c, pre.nobs, pre.nw, pre.wave)


def r_squared(wvarerr: np.ndarray, pre: PreStats) -> np.ndarray:
    """define_stats_and_supports.gms l. 177-179: max(0, 1 - (wVarErr/wVar) $ wVar), where nObs > 0.

    GAMS binds the $ to the ratio: where wVar = 0 (constant series, nObs <= 2) wR2 is 1.
    """
    return DS.p_data_wR2(wvarerr, pre.wvar, pre.nobs)


@dataclass
class Step1Result:
    pre: PreStats
    fit: Fit
    wvarerr: np.ndarray
    wr2: np.ndarray
    step1: np.ndarray           # (series, years_est)
    years_est: np.ndarray


def run(x, expost_years: Sequence[int], years_est: Sequence[int], nobs=None, nw=None,
        first_year: Optional[int] = None, as_coded: Optional[bool] = None,
        zeros_as_missing: Optional[bool] = None) -> Step1Result:
    """Step 1 for a block of series: pre-statistics, trend fit, Step1 values, error variance and R2.

    x: (series, len(expost_years)) the values of the ex-post years ExPostT: NaN missing; 0 missing where
    zeros_as_missing (setting captrd.zeros_as_missing, CAPRI's convention), else an observation.
    years_est: the years YearsEst (captrd.gms l. 806-810) at which the trend line is evaluated.
    nobs / nw: the caller's nObs / nW where CAPRI changes them after counting (prep_data_for_estimation.gms
    l. 214-227); by default counted from x.
    """
    w = trend_variable(expost_years, first_year)
    zm = zeros_missing(zeros_as_missing)
    pre = prestats(x, w, nobs, nw, zeros_as_missing=zm)
    f = fit(x, w, pre.nobs, as_coded=as_coded, zeros_as_missing=zm)
    te = trend_variable(years_est, first_year)
    s1 = step1_values(f, pre.nobs, te)
    ve = error_variance(x, w, f, pre, zeros_as_missing=zm)
    return Step1Result(pre, f, ve, r_squared(ve, pre), s1, np.asarray(list(years_est)))
