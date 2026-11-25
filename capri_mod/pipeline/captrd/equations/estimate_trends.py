r"""CAPTRD's statements of captrd/estimate_trends.gms (CAPRI star 3.0): the trend lines x_t = a + b t^c of Step 1,
weighted least squares on (1, t^c) with weights t for a grid of c, keeping the c of the least weighted error sum of
squares, as named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). The functions take numpy arrays over the series (rows), the grid points and
the ex-post years, as capri_mod/pipeline/captrd/step1.py (_fit_block) passes them, and keep the port's numpy operations,
so the trends are unchanged.
"""
from __future__ import annotations

import numpy as np


def p_trendRes_cPar(n, grid):
    r"""p_trendRes(., cValues, "cPar"): the grid of c for the series with more than four observations; c = 1 at the
    first grid point for three or four; unassigned (0) otherwise.

    n: nObs of each series; grid: the grid's values. Returns cPar (series x grid points).

    CAPRI's GAMS (captrd/estimate_trends.gms l. 80-85):

          p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"cPar") $ (p_data(Rest,s_colsEst,s_rowsEst,"nObs") GT 4)
        *   reducing the number of grid points increases speed but decreases accuracy (last Ci should be equal here and in declarations):
             = p_cMin + (p_ordCPar(CValues)-p_ordCPar("C1"))*(p_cMax - p_cMin) / (p_ordCPar("C30")-p_ordCPar("C1"));
          p_trendRes(Rest,s_colsEst,s_rowsEst,"c1","cPar") $ (  (p_data(Rest,s_colsEst,s_rowsEst,"nObs") GT 2)
                                                              $ (p_data(Rest,s_colsEst,s_rowsEst,"nObs") LE 4))
             = 1.0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (step1._fit_block)."""
    cpar = np.zeros((n.shape[0], len(grid)))
    cpar[n > 4, :] = grid[None, :]
    cpar[(n > 2) & (n <= 4), 0] = 1.0
    return cpar


def p_trendRes_sums(x, obs, w, n, cpar):
    r"""p_trendRes(., cValues, "trddep" / "onedep" / "onetrd" / "oneone" / "trdtrd"): the regression's sums of cross
    products over the ex-post years (onedep and oneone where nObs >= 1, the others where nObs > 2; the observations'
    years only where CAPRI conditions on p_data).

    x: the values (NaN read as 0); obs: the observations; w: p_trend of the years; n: nObs; cpar: p_trendRes_cPar.
    Returns (trddep, onedep, onetrd, oneone, trdtrd), series x grid points.

    CAPRI's GAMS (captrd/estimate_trends.gms l. 94-123):

          p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"trddep") $ (p_data(Rest,s_colsEst,s_rowsEst,"nObs") GT 2)
        *    = Sum(ExPostT,   p_trend(ExPostT)**p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"cPar")*SQRT(p_trend(ExPostT))
        *                   * p_data(Rest,s_colsEst,s_rowsEst,ExPostT)*SQRT(p_trend(ExPostT)));
             = Sum(ExPostT,   p_trend(ExPostT)**(p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"cPar")+1)
                            * p_data(Rest,s_colsEst,s_rowsEst,ExPostT));
        *
          p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"onedep") $ (p_data(Rest,s_colsEst,s_rowsEst,"nObs") GE 1)
        *    = Sum(ExPostT,   1.*SQRT(p_trend(ExPostT))
        *                   * p_data(Rest,s_colsEst,s_rowsEst,ExPostT)*SQRT(p_trend(ExPostT)));
             = Sum(ExPostT,   p_trend(ExPostT)
                            * p_data(Rest,s_colsEst,s_rowsEst,ExPostT));
        *
          p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"onetrd") $ (p_data(Rest,s_colsEst,s_rowsEst,"nObs") GT 2)
        *    = Sum(ExPostT $ p_data(Rest,s_colsEst,s_rowsEst,ExPostT),
        *                     1.*SQRT(p_trend(ExPostT))
        *                   * p_trend(ExPostT)**p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"cPar")*SQRT(p_trend(ExPostT)));
             = Sum(ExPostT $ p_data(Rest,s_colsEst,s_rowsEst,ExPostT),
                             p_trend(ExPostT)**(p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"cPar")+1));
        *
          p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"oneone") $ (p_data(Rest,s_colsEst,s_rowsEst,"nObs") GE 1)
        *    = Sum(ExPostT $ p_data(Rest,s_colsEst,s_rowsEst,ExPostT),
        *                    SQR(1.*SQRT(p_trend(ExPostT))));
             = Sum(ExPostT $ p_data(Rest,s_colsEst,s_rowsEst,ExPostT),
                             p_trend(ExPostT));
        *
          p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"trdtrd") $ (p_data(Rest,s_colsEst,s_rowsEst,"nObs") GE 1)
        *    = Sum(ExPostT $ p_data(Rest,s_colsEst,s_rowsEst,ExPostT),
        *                    SQR(p_trend(ExPostT)**p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"cPar")*SQRT(p_trend(ExPostT))));
             = Sum(ExPostT $ p_data(Rest,s_colsEst,s_rowsEst,ExPostT),
                             p_trend(ExPostT)**(2.*p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"cPar")+1));

    Departures from CAPRI: the port's t^(c+1) is t^c x t (CAPRI's power, may differ in the last digit); the conditions in the arrays' masks, as the
    port had them (step1._fit_block)."""
    K = cpar.shape[1]
    some = n >= 1
    wk = w[None, None, :]                     # (1, 1, T)
    ck = cpar[:, :, None]                     # (S, K, 1)
    xo = x[:, None, :]                        # (S, 1, T)
    ob = obs[:, None, :]
    t_c = wk ** ck                            # t^c
    t_c1 = t_c * wk                           # t^(c+1)
    gt2 = (n > 2)[:, None]
    trddep = np.where(gt2, (t_c1 * xo).sum(axis=2), 0.0)
    onedep = np.where(some, (w[None, :] * x).sum(axis=1), 0.0)[:, None] * np.ones((1, K))
    onetrd = np.where(gt2, np.where(ob, t_c1, 0.0).sum(axis=2), 0.0)
    oneone = np.where(some, np.where(obs, w[None, :], 0.0).sum(axis=1), 0.0)[:, None] * np.ones((1, K))
    trdtrd = np.where(some[:, None], np.where(ob, wk ** (2.0 * ck + 1.0), 0.0).sum(axis=2), 0.0)
    return trddep, onedep, onetrd, oneone, trdtrd


def p_trendRes_slope_const(trddep, onedep, onetrd, oneone, trdtrd):
    r"""p_trendRes(., cValues, "slope" / "const"): the least squares' coefficients, where oneone x trdtrd > onetrd^2
    (0 elsewhere). Returns (slope, const).

    CAPRI's GAMS (captrd/estimate_trends.gms l. 128-142):

          p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"slope")
             $ (   (p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"oneone")*p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"trdtrd"))
                GT  SQR(p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"onetrd")))
             = (  p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"trddep")*p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"oneone")
                - p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"onedep")*p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"onetrd") )
             / (  p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"oneone")*p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"trdtrd")
                - SQR(p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"onetrd")));
        *
          p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"const")
             $ (   (p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"oneone")*p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"trdtrd"))
                GT  SQR(p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"onetrd")))
             = (  p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"onedep")*p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"trdtrd")
                - p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"trddep")*p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"onetrd") )
             / (  p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"oneone")*p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"trdtrd")
                - SQR(p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"onetrd")));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (step1._fit_block)."""
    lhs, rhs = oneone * trdtrd, onetrd ** 2
    ok = lhs > rhs
    den = np.where(ok, lhs - rhs, 1.0)
    slope = np.where(ok, (trddep * oneone - onedep * onetrd) / den, 0.0)
    const = np.where(ok, (onedep * trdtrd - trddep * onetrd) / den, 0.0)
    return slope, const


def p_trendRes_wESS(x, obs, w, n, cpar, slope, const):
    r"""p_trendRes(., cValues, "wESS"): the weighted error sum of squares over the observations, where nObs > 0.

    CAPRI's GAMS (captrd/estimate_trends.gms l. 146-155):

          p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"wESS") $ p_data(Rest,s_colsEst,s_rowsEst,"nObs")
        *    = Sum(ExPostT, SQR(  p_data(Rest,s_colsEst,s_rowsEst,ExPostT)*SQRT(p_trend(ExPostT))
        *                       - p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"const")*SQRT(p_trend(ExPostT))
        *                       - p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"slope")*p_trend(ExPostT)**p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"cPar")
        *                                                                             *SQRT(p_trend(ExPostT))));
             = Sum(ExPostT $ p_data(Rest,s_colsEst,s_rowsEst,ExPostT),
                          SQR( p_data(Rest,s_colsEst,s_rowsEst,ExPostT)
                              - p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"const")
                              - p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"slope")*p_trend(ExPostT)**p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"cPar"))
                        * p_trend(ExPostT) );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (step1._fit_block)."""
    wk = w[None, None, :]
    t_c = wk ** cpar[:, :, None]
    resid = x[:, None, :] - const[:, :, None] - slope[:, :, None] * t_c
    return np.where((n != 0)[:, None], np.where(obs[:, None, :], resid ** 2 * wk, 0.0).sum(axis=2), 0.0)


def p_trendRes_short_zero(n, arrays):
    r"""p_trendRes(., cValues, res) of the grid points 2..30 of the series with at most four observations: zero (the
    arrays, cPar, slope, const and wESS, set in place).

    CAPRI's GAMS (captrd/estimate_trends.gms l. 160-160):

          p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,res) $ ((NOT SAMEAS(CValues,"c1")) $ (p_data(Rest,s_colsEst,s_rowsEst,"nObs") LE 4)) = 0.;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (step1._fit_block)."""
    short = (n <= 4)
    for arr in arrays:
        arr[short, 1:] = 0.0


def p_trendRes_cOpt_wESS_ordOpt(wess, n, as_coded):
    r"""p_trendRes(., "cOpt", "wESS" / "ordOpt"): the least wESS and the first grid point with it.

    as_coded (setting captrd.short_series_grid_as_coded): True, CAPRI's code, the minimum over all 30 grid points,
    29 of them zeroed for nObs <= 4; False (the default, CAPRI-ERROR-FIX) the first grid point only for those.
    Returns (the minimum, the 0-based point).

    CAPRI's GAMS (captrd/estimate_trends.gms l. 166-171):

          p_trendRes(Rest,s_colsEst,s_rowsEst,"cOpt","wESS") $ p_data(Rest,s_colsEst,s_rowsEst,"nObs")
             = SMIN(cValues, p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"wESS"));
        *
        *     If there are several cValues with exactly equal and optimal wESS, pick (only) the first one:
          p_trendRes(Rest,s_colsEst,s_rowsEst,"cOpt","ordOpt") $ p_data(Rest,s_colsEst,s_rowsEst,"nObs")
             = SMIN(CValues $ (p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"wESS") eq p_trendRes(Rest,s_colsEst,s_rowsEst,"cOpt","wESS")),p_ordCPar(CValues));

    Departures from CAPRI: for nObs <= 4 the minimum over the first grid point only by default (the intent stated at l. 158; CAPRI-ERROR-FIX,
    setting captrd.short_series_grid_as_coded); the domain in the caller (step1._fit_block)."""
    K = wess.shape[1]
    short = (n <= 4)
    if as_coded:
        cand = wess
    else:
        cand = np.where(short[:, None] & (np.arange(K)[None, :] > 0), np.inf, wess)
    wmin = cand.min(axis=1)
    return wmin, np.argmax(cand == wmin[:, None], axis=1)


def p_trendRes_cOpt(n, cpar, slope, const, k_opt):
    r"""p_trendRes(., "cOpt", "Slope" / "Const" / "Cpar"): the coefficients of the optimal grid point (a where nObs > 0,
    b and c where nObs > 2). Returns (a, b, c).

    CAPRI's GAMS (captrd/estimate_trends.gms l. 173-183):

          p_trendRes(Rest,s_colsEst,s_rowsEst,"cOpt","Slope") $ (p_data(Rest,s_colsEst,s_rowsEst,"nObs") GT 2)
             = SUM(cValues $ (p_ordCPar(cValues) eq p_trendRes(Rest,s_colsEst,s_rowsEst,"cOpt","ordOpt")),
               p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"Slope"));
        *
          p_trendRes(Rest,s_colsEst,s_rowsEst,"cOpt","Const") $ p_data(Rest,s_colsEst,s_rowsEst,"nObs")
             = SUM(cValues $ (p_ordCPar(cValues) eq p_trendRes(Rest,s_colsEst,s_rowsEst,"cOpt","ordOpt")),
               p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"Const"));
        *
          p_trendRes(Rest,s_colsEst,s_rowsEst,"cOpt","Cpar") $ (p_data(Rest,s_colsEst,s_rowsEst,"nObs") GT 2)
             = SUM(cValues $ (p_ordCPar(cValues) eq p_trendRes(Rest,s_colsEst,s_rowsEst,"cOpt","ordOpt")),
               p_trendRes(Rest,s_colsEst,s_rowsEst,cValues,"Cpar"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (step1._fit_block)."""
    rows = np.arange(n.shape[0])
    a = np.where(n != 0, const[rows, k_opt], 0.0)
    b = np.where(n > 2, slope[rows, k_opt], 0.0)
    c = np.where(n > 2, cpar[rows, k_opt], 0.0)
    return a, b, c
