r"""CAPTRD's statements of captrd/define_stats_and_supports.gms (CAPRI star 3.0): the trend lines' values and
statistics of Step 1, as named functions (the supports' statements of the file join them in the refactor's C5.12).

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). The functions take numpy arrays over the series (rows) and the years, as
capri_mod/pipeline/captrd/step1.py passes them, and keep the port's numpy operations, so the results are unchanged.
"""
from __future__ import annotations

import numpy as np


def p_result_Step1(a, b, c, nobs, t_est):
    r"""p_result(., YearsEst, "Step1"): the trend line's value a + b t^c at the years YearsEst, where nObs > 0.

    a, b, c: the trend's coefficients; nobs: nObs; t_est: p_trend of the years. Returns (series x years).

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 47-49):

           p_result(Rest,S_ColsEst,S_RowsEst,YearsEst,"Step1") $ p_data(Rest,S_ColsEst,S_RowsEst,"nObs")
              = p_aTrend(Rest,S_ColsEst,S_RowsEst)
                + p_bTrend(Rest,S_ColsEst,S_RowsEst) * p_trend(YearsEst)**p_cTrend(Rest,S_ColsEst,S_RowsEst);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (step1)."""
    t = np.asarray(t_est, dtype=float)[None, :]
    v = a[:, None] + b[:, None] * t ** c[:, None]
    return np.where((np.asarray(nobs) != 0)[:, None], v, 0.0)


def p_data_wVarErr(x, obs, w, a, b, c, nobs, nw, wave):
    r"""p_data(., "wVarErr"): the error variance, the weighted squared residuals over the observations over nW - 1
    where nObs > 2; 0.25 x wAve^2 where nObs is 1 or 2.

    x: the values (NaN read as 0); obs: the observations; w: p_trend of the ex-post years; a, b, c: the trend's
    coefficients; nobs, nw, wave: nObs, nW, wAve.

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 118-123):

           p_data(Rest,S_ColsEst,S_RowsEst,"wVarErr") $ (p_data(Rest,S_ColsEst,S_RowsEst,"nObs") GT 2)
              = SUM(exPostT $ p_data(Rest,S_ColsEst,S_RowsEst,exPostT),
                SQR(p_data(Rest,S_ColsEst,S_RowsEst,exPostT)
                - p_aTrend(Rest,S_ColsEst,S_RowsEst)
                - p_bTrend(Rest,S_ColsEst,S_RowsEst) * p_trend(exPostT)**p_cTrend(Rest,S_ColsEst,S_RowsEst))
                 * p_Trend(exPostT) ) / (p_data(Rest,S_ColsEst,S_RowsEst,"nW")-1);

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 129-132):

           p_data(Rest,S_ColsEst,S_RowsEst,"wVarErr")
              $ ((p_data(Rest,S_ColsEst,S_RowsEst,"nObs") eq 1)
                 or (p_data(Rest,S_ColsEst,S_RowsEst,"nObs") eq 2))
              = SQR(p_data(Rest,S_ColsEst,S_RowsEst,"wAve")) * 0.25;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (step1)."""
    r = x - a[:, None] - b[:, None] * w[None, :] ** c[:, None]
    ess = np.where(obs, r ** 2 * w[None, :], 0.0).sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        v = np.where(nobs > 2, ess / (nw - 1.0), 0.0)
    return np.where((nobs == 1) | (nobs == 2), 0.25 * wave ** 2, v)


def p_data_wR2(wvarerr, wvar, nobs):
    r"""p_data(., "wR2"): max(0, 1 - (wVarErr / wVar) $ wVar), where nObs > 0 (GAMS binds the $ to the ratio: where
    wVar = 0, constant series, wR2 is 1).

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 177-179):

           p_data(Rest,S_ColsEst,S_RowsEst,"wR2") $ p_data(Rest,S_ColsEst,S_RowsEst,"nObs")
              = MAX(0.,1. - (p_data(Rest,S_ColsEst,S_RowsEst,"wVarErr")/
                p_data(Rest,S_ColsEst,S_RowsEst,"wVar")) $ p_data(Rest,S_ColsEst,S_RowsEst,"wVar"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (step1)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(wvar != 0.0, wvarerr / np.where(wvar != 0.0, wvar, 1.0), 0.0)
    return np.where(nobs != 0, np.maximum(0.0, 1.0 - ratio), 0.0)
