"""CAPTRD Step 1: the trend line x_t = a + b * t^c of every series, and its statistics.

Ported from CAPRI star 3.0:
  - captrd.gms l. 203, 271: the trend variable p_trend(t) = ORD(t)/10 over YEARS = %FirstYear%..%lastSimulationYear%;
  - prep_data_for_estimation.gms l. 205-247: nObs, nW, wAve, wVar (pre-statistics over the ex-post years ExPostT);
  - estimate_trends.gms (whole file): weighted least squares with weights t on the transformed regressor t^c, for a
    grid of 30 values of c in [0.02, 1.2], keeping the c with the smallest weighted error sum of squares;
  - define_stats_and_supports.gms l. 44-49: the trend value Step1(t) = a + b * t^c for the years YearsEst;
  - define_stats_and_supports.gms l. 113-132: the error variance wVarErr;
  - define_stats_and_supports.gms l. 177-179: wR2 = max(0, 1 - wVarErr/wVar), the term dropped where wVar = 0.

Conventions of the GAMS code kept here:
  - which values are observations (setting captrd.zeros_as_missing; CAPRI-ERROR-FIX, register FIX-8):
      true  - CAPRI's convention (CAPTRD_MAP.md section 9, point 1): a zero is a missing observation; every count and
              sum runs over the ex-post years with a nonzero value (NaN is read as 0, so also missing);
      false - the default: NaN is a missing observation and a recorded zero is an observation (value 0). CAPREG's
              series as GAMS writes them carry no zeros (GAMS stores none), so on them the two agree; they differ
              once the data layer passes true zeros (docs/design/CAPTRD_MOD.md section 6);
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
from typing import Iterable, Mapping, Optional, Sequence

import numpy as np

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
    (CAPRI zeroes both where BASM is zero, l. 214-218, and for INHA.LEVL and DOMM of young animals, l. 221-227).
    """
    x, obs = observed(x, zeros_as_missing)
    w = np.asarray(w, dtype=float)
    n = obs.sum(axis=1).astype(float) if nobs is None else np.asarray(nobs, dtype=float)
    nW = (obs * w).sum(axis=1) if nw is None else np.asarray(nw, dtype=float)
    # l. 233-234: wAve $ nW = sum over all ExPostT of x*t / nW (zeros add nothing)
    wave = np.where(nW != 0.0, (x * w).sum(axis=1) / np.where(nW != 0.0, nW, 1.0), 0.0)
    # l. 241-246: wVar $ (nObs > 2) over the observations, divided by nW - 1; |wVar| <= 1E-20 -> 0
    dev = np.where(obs, (x - wave[:, None]) ** 2 * w, 0.0).sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        wvar = np.where(n > 2, dev / (nW - 1.0), 0.0)
    wvar = np.where(np.abs(wvar) <= 1e-20, 0.0, wvar)
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
    S, K = x.shape[0], len(grid)
    long_ = n > 4
    mid = (n > 2) & (n <= 4)
    some = n >= 1

    # l. 80-85: cPar; unassigned (0) for nObs <= 2 and for grid points 2..30 when nObs is 3 or 4
    cpar = np.zeros((S, K))
    cpar[long_, :] = grid[None, :]
    cpar[mid, 0] = 1.0

    wk = w[None, None, :]                     # (1, 1, T)
    ck = cpar[:, :, None]                     # (S, K, 1)
    xo = x[:, None, :]                        # (S, 1, T)
    ob = obs[:, None, :]
    t_c = wk ** ck                            # t^c
    t_c1 = t_c * wk                           # t^(c+1)
    # l. 94-123
    gt2 = (n > 2)[:, None]
    trddep = np.where(gt2, (t_c1 * xo).sum(axis=2), 0.0)
    onedep = np.where(some, (w[None, :] * x).sum(axis=1), 0.0)[:, None] * np.ones((1, K))
    onetrd = np.where(gt2, np.where(ob, t_c1, 0.0).sum(axis=2), 0.0)
    oneone = np.where(some, np.where(obs, w[None, :], 0.0).sum(axis=1), 0.0)[:, None] * np.ones((1, K))
    trdtrd = np.where(some[:, None], np.where(ob, wk ** (2.0 * ck + 1.0), 0.0).sum(axis=2), 0.0)
    # l. 128-142: assigned only where oneone*trdtrd > onetrd^2
    lhs, rhs = oneone * trdtrd, onetrd ** 2
    ok = lhs > rhs
    den = np.where(ok, lhs - rhs, 1.0)
    slope = np.where(ok, (trddep * oneone - onedep * onetrd) / den, 0.0)
    const = np.where(ok, (onedep * trdtrd - trddep * onetrd) / den, 0.0)
    # l. 146-155: wESS $ nObs over the observations
    resid = xo - const[:, :, None] - slope[:, :, None] * t_c
    wess = np.where((n != 0)[:, None], np.where(ob, resid ** 2 * wk, 0.0).sum(axis=2), 0.0)
    # l. 160: grid points 2..30 set to zero for nObs <= 4
    short = (n <= 4)
    for arr in (cpar, slope, const, wess):
        arr[short, 1:] = 0.0

    if as_coded:
        cand = wess
    else:
        cand = np.where(short[:, None] & (np.arange(K)[None, :] > 0), np.inf, wess)
    wmin = cand.min(axis=1)
    # l. 168-171: the first grid point with wESS equal to the minimum
    k_opt = np.argmax(cand == wmin[:, None], axis=1)
    rows = np.arange(S)
    has = n != 0
    a = np.where(has, const[rows, k_opt], 0.0)                     # l. 177-179 ($ nObs)
    b = np.where(n > 2, slope[rows, k_opt], 0.0)                  # l. 173-175 ($ nObs > 2)
    c = np.where(n > 2, cpar[rows, k_opt], 0.0)                   # l. 181-183 ($ nObs > 2)
    return Fit(a, b, c, np.where(has, wmin, 0.0), np.where(has, k_opt, -1))


def step1_values(f: Fit, nobs, t_est) -> np.ndarray:
    """define_stats_and_supports.gms l. 44-49: Step1(t) = a + b * t^c for the years YearsEst, where nObs > 0."""
    t = np.asarray(t_est, dtype=float)[None, :]
    v = f.a[:, None] + f.b[:, None] * t ** f.c[:, None]
    return np.where((np.asarray(nobs) != 0)[:, None], v, 0.0)


def error_variance(x, w, f: Fit, pre: PreStats, zeros_as_missing: Optional[bool] = None) -> np.ndarray:
    """define_stats_and_supports.gms l. 113-132.

    nObs > 2: sum over the observations of (x - a - b t^c)^2 * t, divided by nW - 1;
    nObs in {1, 2}: 0.25 * wAve^2 (the fall-back of l. 127-132).
    """
    x, obs = observed(x, zeros_as_missing)
    w = np.asarray(w, dtype=float)
    r = x - f.a[:, None] - f.b[:, None] * w[None, :] ** f.c[:, None]
    ess = np.where(obs, r ** 2 * w[None, :], 0.0).sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        v = np.where(pre.nobs > 2, ess / (pre.nw - 1.0), 0.0)
    return np.where((pre.nobs == 1) | (pre.nobs == 2), 0.25 * pre.wave ** 2, v)


def r_squared(wvarerr: np.ndarray, pre: PreStats) -> np.ndarray:
    """define_stats_and_supports.gms l. 177-179: max(0, 1 - (wVarErr/wVar) $ wVar), where nObs > 0.

    GAMS binds the $ to the ratio: where wVar = 0 (constant series, nObs <= 2) wR2 is 1.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(pre.wvar != 0.0, wvarerr / np.where(pre.wvar != 0.0, pre.wvar, 1.0), 0.0)
    return np.where(pre.nobs != 0, np.maximum(0.0, 1.0 - ratio), 0.0)


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
