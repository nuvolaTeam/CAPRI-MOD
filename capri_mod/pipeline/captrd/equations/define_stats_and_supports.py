r"""CAPTRD's statements of captrd/define_stats_and_supports.gms (CAPRI star 3.0): the trend lines' values and
statistics of Step 1, the supports from them, the COCO nowcasts' expert supports and the storage of the expert supports,
as named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). The callers hold the loops, the conditions and the order, and call them:
capri_mod/pipeline/captrd/step1.py (l. 47-179), supports.py (supports, uvag_from_dgagri1: l. 195-356),
coco_supports.py (l. 406-456), expert_support.py (expert, sugb_trade, trust: l. 490-645), dairy_supports.py
(hcom_expert: l. 511-519) and final_supports.py (overwrite, mcact_scale, wvarerr, domm_wvarerr: l. 604-663). The
functions of step1.py and supports.py take numpy arrays over the series (and the years), as those callers pass them,
and keep their numpy operations; the others take values. The arithmetic is the port's, so the results are unchanged.
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
    caller (step1, supports, final_supports, expert_support, dairy_supports, coco_supports)."""
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
    caller (step1, supports, final_supports, expert_support, dairy_supports, coco_supports)."""
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
    caller (step1, supports, final_supports, expert_support, dairy_supports, coco_supports)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(wvar != 0.0, wvarerr / np.where(wvar != 0.0, wvar, 1.0), 0.0)
    return np.where(nobs != 0, np.maximum(0.0, 1.0 - ratio), 0.0)


def p_result_NTRD_Support(base, wr2, step1):
    r"""p_result(Rest, "NTRD", S_RowsEst, ExAnte, "Support") of a series with observations: the base (BAST, else BASM)
    and Step1 weighted by wR2 (no floor: net trade may be negative).

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 195-199):

           p_result(Rest,"NTRD",S_RowsEst,ExAnte,"Support") $ P_Data(Rest,"NTRD",S_RowsEst,"nObs")
            = (  p_data(Rest,"NTRD",S_RowsEst,"BAST")
               + p_data(Rest,"NTRD",S_RowsEst,"BASM") $ (NOT p_data(Rest,"NTRD",S_RowsEst,"BAST")))
                                                             * (1.-p_data(Rest,"NTRD",S_RowsEst,"wR2"))
            + p_result(Rest,"NTRD",S_RowsEst,Exante,"STEP1") * p_data(Rest,"NTRD",S_RowsEst,"wR2");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (supports.supports)."""
    return base * (1.0 - wr2) + step1 * wr2


def p_result_Support(base, wr2, step1, cssp_negative):
    r"""p_result(Rest, S_ColsEst, S_RowsEst, ExAnte, "Support") of the other series with observations: the base and
    Step1 weighted by wR2, at least 0.1% of the base (the whole base for CSSP with a negative BASM).

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 203-212):

           p_result(Rest,S_ColsEst,S_RowsEst,ExAnte,"Support")
             $ (P_Data(Rest,S_ColsEst,S_RowsEst,"nObs") $ (NOT SAMEAS(S_ColsEst,"NTRD")))
             = MAX(( P_Data(Rest,S_ColsEst,S_RowsEst,"BAST")
                    +P_Data(Rest,S_ColsEst,S_RowsEst,"BASM") $ (NOT p_data(Rest,S_ColsEst,S_RowsEst,"BAST")))
                   *(0.001+0.999 $ (SAMEAS(S_ColsEst,"CSSP") and (P_Data(Rest,S_ColsEst,S_RowsEst,"BASM") LT 0))),

                   ( P_Data(Rest,S_ColsEst,S_RowsEst,"BAST")
                    +P_Data(Rest,S_ColsEst,S_RowsEst,"BASM") $ (NOT p_data(Rest,S_ColsEst,S_RowsEst,"BAST")))
                                                                     * (1.-P_Data(Rest,S_ColsEst,S_RowsEst,"wR2"))
                 + p_result(Rest,S_ColsEst,S_RowsEst,Exante,"STEP1") *P_Data(Rest,S_ColsEst,S_RowsEst,"wR2"));

    Departures from CAPRI: the port writes 1.0 for CAPRI's 0.001 + 0.999; the domain condition and the loops in the caller (supports.supports)."""
    floor = base * np.where(cssp_negative, 1.0, 0.001)
    return np.maximum(floor, base * (1.0 - wr2) + step1 * wr2)


def p_result_Support_MCACT_yield(base, bsy, wr2, step1):
    r"""p_result(Rest, MCACT, O, ExAnte, "Support") of the crops' yields: the best three yields BSY and Step1 weighted by
    the square root of wR2, at least 0.1% of the base.

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 217-221):

           p_result(Rest,MCACT,O,ExAnte,"Support") $ (PACT_TO_Y(MCACT,O) $ p_data(Rest,MCACT,O,"nObs"))
              = MAX((P_Data(Rest,MCACT,O,"BAST")
                    +P_Data(Rest,MCACT,O,"BASM") $ (NOT P_Data(Rest,MCACT,O,"BAST")))*0.001,
                  P_Data(Rest,MCACT,O,"BSY")            * (1.-SQRT(p_data(Rest,MCACT,O,"wR2")))
                + p_result(Rest,MCACT,O,Exante,"STEP1") *     SQRT(p_data(Rest,MCACT,O,"wR2"))   );

    Departures from CAPRI: the port takes the root of wR2 clipped at zero (wR2 is not negative: MAX(0., ...), l. 177); the domain condition and
    the loops in the caller (supports.supports)."""
    sq = np.sqrt(np.clip(wr2, 0.0, None))
    return np.maximum(base * 0.001, bsy * (1.0 - sq) + step1 * sq)


def p_result_Support_yield(support, base, dt):
    r"""p_result(Rest, ., ., ExAnte, "Support") of the yields (PACT_TO_Y): within 2.5% a year of the base, dt the years
    since BAST (else BAS).

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 226-238):

           p_result(Rest,S_ColsEst,S_RowsEst,ExAnte,"Support")
              $ (PACT_TO_Y(S_ColsEst,S_RowsEst) $ p_data(Rest,S_ColsEst,S_RowsEst,"nObs"))
              = MAX(MIN(p_result(Rest,S_ColsEst,S_RowsEst,ExAnte,"Support"),
                (P_Data(Rest,S_ColsEst,S_RowsEst,"BAST")
                +P_Data(Rest,S_ColsEst,S_RowsEst,"BASM") $ (NOT P_Data(Rest,S_ColsEst,S_RowsEst,"BAST")))
                *1.025
                **(OrdT(Exante)-OrdT("BAST") $ (    P_DATA(Rest,S_ColsEst,S_RowsEst,"BAST"))
                               -OrdT("BAS")  $ (NOT P_DATA(Rest,S_ColsEst,S_RowsEst,"BAST")))),
                (P_Data(Rest,S_ColsEst,S_RowsEst,"BAST")
                +P_Data(Rest,S_ColsEst,S_RowsEst,"BASM") $ (NOT P_Data(Rest,S_ColsEst,S_RowsEst,"BAST")))
                *0.975
                **(OrdT(Exante)-OrdT("BAST") $ (    P_DATA(Rest,S_ColsEst,S_RowsEst,"BAST"))
                               -OrdT("BAS")  $ (NOT P_DATA(Rest,S_ColsEst,S_RowsEst,"BAST"))));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (supports.supports)."""
    return np.maximum(np.minimum(support, base * 1.025 ** dt), base * 0.975 ** dt)


def p_result_Support_NoYieldDrop(support, base):
    r"""p_result(Rest, NoYieldDrop, ., ExAnte, "Support") of their yields: not below the base.

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 242-246):

           p_result(Rest,NoYieldDrop,S_RowsEst,ExAnte,"Support")
              $ (PACT_TO_Y(NoYieldDrop,S_RowsEst) $ p_data(Rest,NoYieldDrop,S_RowsEst,"nObs"))
              = MAX(p_result(Rest,NoYieldDrop,S_RowsEst,ExAnte,"Support"),
                    (P_Data(Rest,NoYieldDrop,S_RowsEst,"BAST")
                    +P_Data(Rest,NoYieldDrop,S_RowsEst,"BASM") $ (NOT P_Data(Rest,NoYieldDrop,S_RowsEst,"BAST"))));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (supports.supports)."""
    return np.maximum(support, base)


def p_result_Support_SLGW(support, basm, d0):
    r"""p_result(Rest, BreedAct, "SLGW", ExAnte, "Support"): within 0.2% a year of BASM (p_useBAST is 0), d0 the years
    since BAS.

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 254-266):

           p_result(Rest,BreedAct,"SLGW",ExAnte,"Support")
              $ p_data(Rest,BreedAct,"SLGW","nObs")
              = MAX(MIN(p_result(Rest,BreedAct,"SLGW",ExAnte,"Support"),
                (P_Data(Rest,BreedAct,"SLGW","BAST")*p_useBAST
                +P_Data(Rest,BreedAct,"SLGW","BASM") $ (NOT P_Data(Rest,BreedAct,"SLGW","BAST")*p_useBAST))
                *1.002
                **(OrdT(Exante)-OrdT("BAST") $ (    P_DATA(Rest,BreedAct,"SLGW","BAST")*p_useBAST)
                               -OrdT("BAS")  $ (NOT P_DATA(Rest,BreedAct,"SLGW","BAST")*p_useBAST))),
                (P_Data(Rest,BreedAct,"SLGW","BAST")*p_useBAST
                +P_Data(Rest,BreedAct,"SLGW","BASM") $ (NOT P_Data(Rest,BreedAct,"SLGW","BAST")*p_useBAST))
                *0.998
                **(OrdT(Exante)-OrdT("BAST") $ (    P_DATA(Rest,BreedAct,"SLGW","BAST")*p_useBAST)
                               -OrdT("BAS")  $ (NOT P_DATA(Rest,BreedAct,"SLGW","BAST")*p_useBAST)));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (supports.supports)."""
    return np.maximum(np.minimum(support, basm * 1.002 ** d0), basm * 0.998 ** d0)


def p_result_Support_UAAR(support, base, n):
    r"""p_result(Rest, "UAAR", "LEVL", ExAnte, "Support"): at most the base, at least the base x 0.998^n,
    n = OrdT(Exante) - OrdT("BAST").

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 272-281):

           p_result(Rest,"UAAR","LEVL",ExAnte,"Support")
              $ (  (  p_data(Rest,"UAAR","LEVL","BAST")
                    + p_data(Rest,"UAAR","LEVL","BASM") $ (NOT p_data(Rest,"UAAR","LEVL","BAST") ))
                 $ p_result(Rest,"UAAR","LEVL",ExAnte,"Support"))
              = MAX(MIN(  p_data(Rest,"UAAR","LEVL","BAST")
                        + p_data(Rest,"UAAR","LEVL","BASM") $ (NOT p_data(Rest,"UAAR","LEVL","BAST") ),
                          p_result(Rest,"UAAR","LEVL",ExAnte,"Support")),
                    (   p_data(Rest,"UAAR","LEVL","BAST")
                      + p_data(Rest,"UAAR","LEVL","BASM") $ (NOT p_data(Rest,"UAAR","LEVL","BAST") ))
                    * (0.998**(OrdT(Exante)-OrdT("BAST")-OrdT("BAS") $ (NOT OrdT("BAST"))) ));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (supports.supports)."""
    return np.maximum(np.minimum(base, support), base * 0.998 ** n)


def p_result_Support_GRSACT(support, basm):
    r"""p_result(Rest, GRSACT, "LEVL", ExAnte, "Support"): grassland at least 90% of BASM (no nObs condition).

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 285-286):

           p_result(Rest,GRSACT,"LEVL",ExAnte,"Support") = MAX(p_data(Rest,GRSACT,"LEVL","BASM")*0.9,
                                                               p_result(Rest,GRSACT,"LEVL",ExAnte,"Support") );

    Departures from CAPRI: a series without a support counts as 0 (the port's NaN); the loops in the caller (supports.supports)."""
    return np.maximum(basm * 0.9, np.nan_to_num(support))


def p_result_Support_reqfcnlim_lo(support, lo):
    r"""p_result(Rest, ., DAYS / DAILY, ExAnte, "Support") where the activity's level has observations: at least 99% of
    the requirement function's lower limit.

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 290-291):

           p_result(Rest,s_ColsEst,s_RowsEst,ExAnte,"Support") $ (p_reqfcnlim(s_ColsEst,s_RowsEst,"lo") $ p_data(Rest,s_ColsEst,"LEVL","nObs"))
             = MAX(p_result(Rest,s_ColsEst,s_RowsEst,ExAnte,"Support"),0.99*p_reqfcnlim(s_ColsEst,s_RowsEst,"lo"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (supports.supports)."""
    return np.maximum(np.nan_to_num(support), 0.99 * lo)


def p_result_Support_reqfcnlim_up(support, up):
    r"""p_result(Rest, ., DAYS / DAILY, ExAnte, "Support"): at most 101% of the upper limit.

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 292-293):

           p_result(Rest,s_ColsEst,s_RowsEst,ExAnte,"Support") $ (p_reqfcnlim(s_ColsEst,s_RowsEst,"up") $ p_data(Rest,s_ColsEst,"LEVL","nObs"))
             = MIN(p_result(Rest,s_ColsEst,s_RowsEst,ExAnte,"Support"),1.01*p_reqfcnlim(s_ColsEst,s_RowsEst,"up"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (supports.supports)."""
    return np.minimum(support, 1.01 * up)


def p_result_Support_reqfcnlim_new(lo, up):
    r"""p_result(Rest, ., DAYS / DAILY, ExAnte, "Support") of a series without observations of its own, where the
    activity's level has them: 99% of the lower limit, at most 101% of the upper one (up None: none).

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 290-291):

           p_result(Rest,s_ColsEst,s_RowsEst,ExAnte,"Support") $ (p_reqfcnlim(s_ColsEst,s_RowsEst,"lo") $ p_data(Rest,s_ColsEst,"LEVL","nObs"))
             = MAX(p_result(Rest,s_ColsEst,s_RowsEst,ExAnte,"Support"),0.99*p_reqfcnlim(s_ColsEst,s_RowsEst,"lo"));

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 292-293):

           p_result(Rest,s_ColsEst,s_RowsEst,ExAnte,"Support") $ (p_reqfcnlim(s_ColsEst,s_RowsEst,"up") $ p_data(Rest,s_ColsEst,"LEVL","nObs"))
             = MIN(p_result(Rest,s_ColsEst,s_RowsEst,ExAnte,"Support"),1.01*p_reqfcnlim(s_ColsEst,s_RowsEst,"up"));

    Departures from CAPRI: the port gives the series its support directly (CAPRI's max with a zero support, then the upper limit); the domain
    condition in the caller (supports.supports)."""
    return 0.99 * lo if up is None else min(0.99 * lo, 1.01 * up)


def p_result_Support_feed(basm):
    r"""p_result(Rest, MPACT, Feed, ExAnte, "Support") of the feed input coefficients, and of GROF of the feed
    aggregates without variance: BASM.

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 298-299):

           p_result(Rest,MPACT,Feed,ExAnte,"Support") $ p_data(Rest,MPACT,Feed,"nObs")
              = p_data(Rest,MPACT,Feed,"BASM");

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 314-315):

           p_result(Rest,"GROF",Feed,ExAnte,"Support") $ (p_data(Rest,"GROF",Feed,"nObs") $ (NOT p_data(Rest,"GROF",Feed,"wVar")))
              = p_data(Rest,"GROF",Feed,"BASM");

    Departures from CAPRI: the member states' 0.1 x BASM where the region has none (l. 301-302) is not ported: the regional rows need the member
    states' values; the domain condition in the caller (supports.supports)."""
    return basm


def p_result_Support_ReqsT():
    r"""p_result(Rest, MPACT, ReqsT, ExAnte, "Support") of the requirement scalers with a function: 1.

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 318-319):

           p_result(Rest,MPACT,ReqsT,ExAnte,"Support")
              $ (p_data(Rest,MPACT,ReqsT,"Const")  + p_data(Rest,MPACT,ReqsT,"Slope"))  = 1.;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (supports.supports)."""
    return 1.0


def p_result_wVarErr(wave, wvarerr, no_floor, floor_squared):
    r"""p_result(Rest, S_ColsEst, S_RowsEst, exAnte, "wVarErr") of the series with observations: the error variance, at
    least 5% of |wAve| but for the requirements and feed.

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 327-329):

           p_result(Rest,S_ColsEst,S_RowsEst,exAnte,"wVarErr") $ p_data(Rest,S_ColsEst,S_RowsEst,"nObs")
              = MAX(ABS(p_data(Rest,S_ColsEst,S_RowsEst,"wAve"))*0.05 $ ( (NOT SUM(SAMEAS(S_RowsEst,ReqST),1)) and (NOT SUM(SAMEAS(S_RowsEst,Feed),1))),
                     p_data(Rest,S_ColsEst,S_RowsEst,"wVarErr"));

    Departures from CAPRI: with floor_squared (setting captrd.variance_floor_squared, CAPRI-ERROR-FIX) the floor is (0.05 |wAve|)^2, a variance,
    where CAPRI takes 0.05 |wAve|, a level; the domain condition in the caller (supports.supports)."""
    floor = np.abs(wave) * 0.05
    if floor_squared:
        floor = floor * floor
    return np.where(no_floor, wvarerr, np.maximum(floor, wvarerr))


def p_result_UVAG_Support(dgagri1):
    r"""p_result(MS, "UVAG", S_RowsEst, exAnte, "Support") with DG AGRI's scaled price: DGAgri1.

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 355-356):

           p_result(MS,"UVAG",S_RowsEst,exAnte,"Support") $ p_result(MS,"UVAG",S_RowsEst,exAnte,"DGAgri1")
             = p_result(MS,"UVAG",S_RowsEst,exAnte,"DGAgri1");

    Departures from CAPRI: its wVarErr (l. 358-365) is the estimation's, not ported; the domain condition in the caller (supports.uvag_from_dgagri1)."""
    return dgagri1


def p_cocoSupport_Absolute(pdata):
    r"""p_cocoSupport(Rest, ., ., ExAnteD, "Absolute"): the nowcast year's data, where the column takes COCO's data (or
    the row is raw milk), the row does, and the series has observations or is a biofuel position.

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 406-419):

           p_cocoSupport(Rest,S_ColsEst,S_RowsEst,ExAnteD,"Absolute")
        *        no reason to exclude p_data for colsNoCoco if data are really coming from capreg, not coco,
             $[( ((not colsNoCoco(S_ColsEst)) or ( (ordT(exanteD) LE ordT("Lst_Expost"))
        *                                        ... and do not deviate extremely from BAS:
                                                $ p_dataPositionIsOk("closeToBas",Rest,S_ColsEst,S_RowsEst,ExAnteD) )
        *        also no reason to exclude COMI/SGMI because they are not steered by poslo_+posup_
                 or MLKO(S_RowsEst))
        *        ... but no exceptions for set.REQST (handled by regression on yields):
               $ (not rowsNoCoco(S_RowsEst))
        *        do not introduce expert supports from coco without Nobs (say because BAS was empty)
                $ (   p_data(Rest,S_ColsEst,S_RowsEst,"nObs")
                   or bioColsCoco(s_colsest) or bioRowsCoco(s_rowsest))
                ) $ p_result(Rest,S_ColsEst,S_RowsEst,exAnteD,"P_Data")]
             = p_result(Rest,S_ColsEst,S_RowsEst,exAnteD,"P_Data") ;

    Departures from CAPRI: the flag closeToBas (l. 395-403) assigns itself and is never set; the port drops it; the domain condition in the
    caller (coco_supports.coco_supports)."""
    return pdata


def p_cocoSupport_TrustLevl():
    r"""p_cocoSupport(Rest, ., ., exAnteD, "TrustLevl") of a nowcast.

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 437-439):

           p_cocoSupport(Rest,S_ColsEst,S_RowsEst,exAnteD,"TrustLevl")
               $ p_cocoSupport(Rest,S_ColsEst,S_RowsEst,ExAnteD,"Absolute")
              = 7 ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco_supports.coco_supports)."""
    return 7.0


def p_cocoSupport_TrustLevl_derived():
    r"""p_cocoSupport(Rest, ., ., exAnteD, "TrustLevl") of the positions only derived from COCO's data (EAAG, TOOU).

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 444-447):

           p_cocoSupport(Rest,S_ColsEst,S_RowsEst,exAnteD,"TrustLevl")
             $(  p_cocoSupport(Rest,S_ColsEst,S_RowsEst,ExAnteD,"Absolute")
               $ (onlyDerivedCocoCols(S_ColsEst) or onlyDerivedCocoRows(S_RowsEst)) )
              = .5 ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco_supports.coco_supports)."""
    return 0.5


def p_cocoSupport_TrustLevl_levl_yield():
    r"""p_cocoSupport(Rest, ., "LEVL" / yields, exAnteD, "TrustLevl"): the activity levels and the yields.

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 449-451):

           p_cocoSupport(Rest,S_ColsEst,"LEVL",exAnteD,"TrustLevl")
             $( p_cocoSupport(Rest,S_ColsEst,"LEVL",ExAnteD,"Absolute"))
              = 10 ;

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 453-456):

           p_cocoSupport(Rest,S_ColsEst,S_RowsEst,exAnteD,"TrustLevl")
              $(  p_cocoSupport(Rest,S_ColsEst,S_RowsEst,ExAnteD,"Absolute")
               $ (PACT_TO_Y(S_ColsEst,S_RowsEst)) )
              = 10 ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco_supports.coco_supports)."""
    return 10.0


def p_result_coco(absolute):
    r"""p_result(rest, ., ., ExAnteD, "coco"): the nowcast, where the column takes COCO's data or the year is ex post
    (or the row is raw milk), and the row does.

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 530-537):

           p_result(rest,S_ColsEst,S_RowsEst,ExAnteD,"coco")
        *        no reason to exclude p_data for colsNoCoco if data are really coming from capreg, not coco:
             $(  ((not colsNoCoco(S_ColsEst)) or (ordT(exanteD) LE ordT("Lst_Expost"))
                 or MLKO(S_RowsEst))
        *        ... but no exceptions for set.REQST (handled by regression on yields):
               $ (not rowsNoCoco(S_RowsEst))
               $ p_result(rest,S_ColsEst,S_RowsEst,exAnteD,"P_Data"))
             = p_cocoSupport(rest,S_ColsEst,S_RowsEst,ExAnteD,"Absolute") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco_supports.coco_supports)."""
    return absolute


def p_result_Expert_rmAggSup(absolute):
    r"""p_result(rmAggSup, S_ColsEst, S_RowsEst, exAnte, "Expert"): the Absolute.

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 490-492):

           p_result(rmAggSup,S_ColsEst,S_RowsEst,exAnte,"Expert")
             $ p_ExpertSupprt(rmAggSup,S_ColsEst,S_RowsEst,exAnte,"Absolute")
               = p_ExpertSupprt(rmAggSup,S_ColsEst,S_RowsEst,exAnte,"Absolute") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_support.expert)."""
    return absolute


def p_result_Expert(absolute, percent, basm):
    r"""p_result(Rest, S_ColsEst, S_RowsEst, exAnte, "Expert"): the Absolute, else (1 + PercentChange / 100) x BASM.

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 494-507):

           p_result(Rest,S_ColsEst,S_RowsEst,exAnte,"Expert")
             $ (p_ExpertSupprt(Rest,S_ColsEst,S_RowsEst,exAnte,"Absolute")
             or p_ExpertSupprt(Rest,S_ColsEst,S_RowsEst,exAnte,"PercentChange"))
             =
        *       -- absolute number is given

                  p_ExpertSupprt(Rest,S_ColsEst,S_RowsEst,exAnte,"Absolute")
                  $ p_ExpertSupprt(Rest,S_ColsEst,S_RowsEst,exAnte,"Absolute")

        *       -- percentage change against base year is given

               + (1+p_ExpertSupprt(Rest,S_ColsEst,S_RowsEst,exAnte,"PercentChange")/100)
                  * p_data(Rest,S_ColsEst,S_RowsEst,"BASM")
                  $ p_ExpertSupprt(Rest,S_ColsEst,S_RowsEst,exAnte,"PercentChange");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_support.expert)."""
    return (absolute if absolute else 0.0) + ((1 + percent / 100) * basm if percent else 0.0)


def P_Result_HCOM_COMI_expert(share, grof_expert, grof_support):
    r"""P_Result(rEst, "HCOM", "COMI", exanteT, "expert"): the share of direct sales times GROF.COMI's expert support
    (its trend support where it has none).

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 511-514):

           P_Result(rEst,"HCOM","COMI",exanteT,"expert") $ P_Result(rEst,"share","COMI",exanteT,"support1")
              =  P_Result(rEst,"share","COMI",exanteT,"support1")
              *( P_Result(rEst,"GROF","COMI",exanteT,"expert")
               + P_Result(rEst,"GROF","COMI",exanteT,"support") $ (not P_Result(rEst,"GROF","COMI",exanteT,"expert")));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.hcom_expert)."""
    return share * (grof_expert or grof_support)


def p_ExpertSupprt_HCOM_COMI_TrustLevl(share):
    r"""p_ExpertSupprt(Rest, "HCOM", "COMI", exAnteT, "TrustLevl"): 5 where the share is above 0.0001, else 1 (every
    region and ex-ante year: GAMS assigns it without a condition).

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 517-519):

           p_ExpertSupprt(Rest,"HCOM","COMI",exAnteT,"TrustLevl")
            = 5  $ (P_Result(rEst,"share","COMI",exanteT,"support1") gt .0001)
            + 1  $ (P_Result(rEst,"share","COMI",exanteT,"support1") le .0001);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.hcom_expert)."""
    return 5.0 if share > .0001 else 1.0


def p_result_Support_Expert(expert):
    r"""p_result(Rest, S_ColsEst, S_RowsEst, exAnte, "Support") with an Expert: the Expert.

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 604-606):

           p_result(Rest,S_ColsEst,S_RowsEst,exAnte,"Support")
             $ p_result(Rest,S_ColsEst,S_RowsEst,exAnte,"Expert")
             = p_result(Rest,S_ColsEst,S_RowsEst,exAnte,"Expert");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (final_supports.overwrite)."""
    return expert


def p_result_MCACT_LEVL_Support(levl, uaar, total):
    r"""p_result(Rest, MCACT, "LEVL", ExAnte, "Support") above 1E-12: the crop areas scaled to close 67% of their gap
    to UAAR.

    total: the areas' supports summed.

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 618-622):

            p_result(Rest,MCACT,"LEVL",ExAnte,"Support") $ ( (p_result(Rest,MCACT,"LEVL",ExAnte,"Support") GT 1.E-12)
                                                            $ p_result(Rest,"UAAR","LEVL",ExAnte,"Support"))
              =  p_result(Rest,MCACT,"LEVL",Exante,"Support")
              *  (0.67*p_result(Rest,"UAAR","LEVL",ExAnte,"Support")+0.33*SUM(MCACT1, p_result(Rest,MCACT1,"LEVL",ExAnte,"Support")))
              /  SUM(MCACT1, p_result(Rest,MCACT1,"LEVL",ExAnte,"Support"));

    Departures from CAPRI: the port writes 1 - 0.67 for CAPRI's 0.33 and multiplies the area by the factor (CAPRI multiplies, then divides; the
    last digit may differ); the domain condition and the loops in the caller (final_supports.mcact_scale)."""
    return levl * ((0.67 * uaar + (1 - 0.67) * total) / total)


def P_Result_SUGB_trade(bast, basm):
    r"""P_Result(MS, tradeEst, "SUGB", ExAnte, "support" / "expert"): the sugar beet trade at BAST, else BASM.

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 631-633):

            P_Result(MS,tradeEst,"SUGB",ExAnte,respos) $ (SAMEAS(respos,"support") or SAMEAS(respos,"expert"))
                =   P_Result(MS,tradeEst,"SUGB",ExAnte,"BAST") + P_Result(MS,tradeEst,"SUGB",ExAnte,"BASM")
                                                             $ (NOT P_Result(MS,tradeEst,"SUGB",ExAnte,"BAST"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_support.sugb_trade)."""
    return bast or basm


def p_result_TrustLevl(coco, expert):
    r"""p_result(Rest, S_ColsEst, S_RowsEst, exAnte, "TrustLevl") with an Expert: COCO's trust level, else the expert
    support's, else 10.

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 637-645):

           p_result(Rest,S_ColsEst,S_RowsEst,exAnte,"TrustLevl")
           $ p_result(Rest,S_ColsEst,S_RowsEst,exAnte,"Expert")
             = p_cocoSupport(Rest,S_ColsEst,S_RowsEst,ExAnte,"TrustLevl")
             + p_ExpertSupprt(Rest,S_ColsEst,S_RowsEst,exAnte,"TrustLevl")
             $ (NOT p_cocoSupport(Rest,S_ColsEst,S_RowsEst,ExAnte,"TrustLevl") )
             + 10
             $ (NOT (  p_cocoSupport(Rest,S_ColsEst,S_RowsEst,ExAnte,"TrustLevl")
                    or p_ExpertSupprt(Rest,S_ColsEst,S_RowsEst,exAnte,"TrustLevl")))
             ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_support.trust)."""
    return coco or expert or 10.0


def p_result_wVarErr_TrustLevl(expert, trust):
    r"""p_result(Rest, S_ColsEst, S_RowsEst, exAnte, "wVarErr") with a trust level: (max(0.1, |Expert|) x 0.05 / 3 x 10 /
    TrustLevl)^2.

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 647-650):

           p_result(Rest,S_ColsEst,S_RowsEst,exAnte,"wVarErr")
             $ p_result(Rest,S_ColsEst,S_RowsEst,ExAnte,"TrustLevl")
             = SQR(MAX(.1,abs(p_result(Rest,S_ColsEst,S_RowsEst,ExAnte,"Expert"))) * 0.05 / 3 *
                         (10/p_result(Rest,S_ColsEst,S_RowsEst,exAnte,"TrustLevl")));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (final_supports.wvarerr)."""
    return (max(0.1, abs(expert)) * 0.05 / 3.0 * (10.0 / trust)) ** 2


def p_result_wVarErr_DOMPOS(wvarerr, support):
    r"""p_result(MS, DOMPOS, ., exAnte, "wVarErr") of the domestic use components with a support but no external one,
    where DOMM has one: x 10, between those of trust levels 1 and 1E-4.

    CAPRI's GAMS (captrd/define_stats_and_supports.gms l. 655-663):

           p_result(MS,s_ColsEst,S_RowsEst,exAnte,"wVarErr") $ (   P_Result(MS,s_ColsEst,s_rowsEst,exAnte,"Support")
                                                                $  (NOT SUM(external $ P_Result(MS,s_ColsEst,s_rowsEst,ExAnte,external),1))
                                                                $  SUM(external $ P_Result(MS,"DOMM",s_rowsEst,ExAnte,external),1)
                                                                $  DOMPOS(s_ColsEst)    )
             = MIN(MAX(p_result(MS,s_ColsEst,S_RowsEst,exAnte,"wVarErr") * 10,
        *              implied trustlevel should be small (lower than 1) ...
                       SQR(p_result(MS,s_ColsEst,S_RowsEst,ExAnte,"support") * 0.05 / 3 * (10/1))),
        *          ... but larger than 1.E-4
                   SQR(p_result(MS,s_ColsEst,S_RowsEst,ExAnte,"support") * 0.05 / 3 * (10/1.E-4))) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (final_supports.domm_wvarerr)."""
    return min(max(wvarerr * 10.0, (support * 0.05 / 3.0 * (10.0 / 1.0)) ** 2),
               (support * 0.05 / 3.0 * (10.0 / 1.E-4)) ** 2)
