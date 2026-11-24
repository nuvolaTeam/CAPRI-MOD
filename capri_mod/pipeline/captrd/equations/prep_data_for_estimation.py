r"""CAPTRD's statements of captrd/prep_data_for_estimation.gms (CAPRI star 3.0): the series' pre-statistics nObs, nW,
wAve and wVar, as named functions (the file's other statements join them in the refactor's C5.13).

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). The functions take numpy arrays over the series (rows) and the ex-post years,
as capri_mod/pipeline/captrd/step1.py (prestats) passes them, and keep the port's numpy operations, so the statistics
are unchanged.
"""
from __future__ import annotations

import numpy as np


def p_data_nObs_nW(obs, w):
    r"""p_data(., "nObs" / "nW"): the number of observations and their summed weights p_trend. Returns (nObs, nW).

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 209-210):

           p_data(Rest,S_ColsEst,S_RowsEst,"nObs")  = SUM(ExpostT $ p_data(Rest,S_ColsEst,S_RowsEst,ExpostT), 1.);
           p_data(Rest,S_ColsEst,S_RowsEst,"nW")    = SUM(ExpostT $ p_data(Rest,S_ColsEst,S_RowsEst,ExpostT), p_trend(ExpostT));

    Departures from CAPRI: the BASM and the INHA / DOMM exclusions (l. 215-227) are the caller's: it passes nObs and nW where they change them
    (step1.prestats)."""
    return obs.sum(axis=1).astype(float), (obs * w).sum(axis=1)


def p_data_WAve(x, w, nw):
    r"""p_data(., "WAve"): the weighted mean over all ex-post years (zeros add nothing), where nW is nonzero.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 233-234):

           p_data(Rest,S_ColsEst,S_RowsEst,"WAve") $ p_data(Rest,S_ColsEst,S_RowsEst,"nW") =
               SUM(ExpostT, p_data(Rest,S_ColsEst,S_RowsEst,ExpostT)*p_trend(ExpostT))/p_data(Rest,S_ColsEst,S_RowsEst,"nW");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (step1.prestats)."""
    return np.where(nw != 0.0, (x * w).sum(axis=1) / np.where(nw != 0.0, nw, 1.0), 0.0)


def p_data_wVar(x, obs, w, n, nw, wave):
    r"""p_data(., "wVar"): the weighted variance over the observations over nW - 1, where nObs > 2; at most 1E-20 in
    size set to 0.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 241-246):

           p_data(Rest,S_ColsEst,S_RowsEst,"wVar") $ (p_data(Rest,S_ColsEst,S_RowsEst,"nObs") GT 2)
        *pw120411      = SUM(ExpostT, SQR(p_data(Rest,S_ColsEst,S_RowsEst,ExpostT)-p_data(Rest,S_ColsEst,S_RowsEst,"wAve"))*p_trend(ExpostT) )
              = SUM(ExpostT $ p_data(Rest,S_ColsEst,S_RowsEst,ExpostT),
                          SQR(p_data(Rest,S_ColsEst,S_RowsEst,ExpostT)-p_data(Rest,S_ColsEst,S_RowsEst,"wAve"))*p_trend(ExpostT) )
              / (p_data(Rest,S_ColsEst,S_RowsEst,"nW")-1);
           p_data(Rest,S_ColsEst,S_RowsEst,"wVar") $ (ABS(p_data(Rest,S_ColsEst,S_RowsEst,"wVar")) LE 1.E-20) = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (step1.prestats)."""
    dev = np.where(obs, (x - wave[:, None]) ** 2 * w, 0.0).sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        wvar = np.where(n > 2, dev / (nw - 1.0), 0.0)
    return np.where(np.abs(wvar) <= 1e-20, 0.0, wvar)
