r"""CAPTRD's statements of captrd/prep_data_for_estimation.gms (CAPRI star 3.0): the data's preparation for the
estimation (the sugar prices, the series CAPTRD does not use, the aggregates, the slaughter weights, the unit values,
the market balances) and the series' statistics (nObs, nW, wAve, wVar, BAS, the feed coefficients, BSY), as named
functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). The callers hold the loops, the conditions and the order, and call them:
capri_mod/pipeline/captrd/prepare.py (prep_for_estimation and its helpers, l. 34-203: pandas Series over (region,
year), as its Wide holds p_data), statistics.py (statistics, l. 215-317: numpy arrays over the series, or values) and
step1.py (prestats, l. 209-246). The functions keep the callers' pandas and numpy operations, so the results are
unchanged.
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
    caller (prepare.prep_for_estimation, statistics.statistics, step1.prestats)."""
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
    caller (prepare.prep_for_estimation, statistics.statistics, step1.prestats)."""
    dev = np.where(obs, (x - wave[:, None]) ** 2 * w, 0.0).sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        wvar = np.where(n > 2, dev / (nw - 1.0), 0.0)
    return np.where(np.abs(wvar) <= 1e-20, 0.0, wvar)


def P_DATA_PADM_SUGA_expost():
    r"""P_DATA(MS, "PADM", "SUGA", ExpostT) with a sugar quota: the administrative price.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 34-34):

           P_DATA(MS,"PADM","SUGA",ExpostT) $ P_DATA(MS,"QUTS","SUGA",ExpostT)= 631;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (prepare.prep_for_estimation)."""
    return 631.0


def P_DATA_PADM_SUGA_2008():
    r"""P_DATA(MS, "PADM", "SUGA", "2008") with a quota.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 35-35):

           P_DATA(MS,"PADM","SUGA","2008") $ P_DATA(MS,"QUTS","SUGA","2008")= 541.5;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (prepare.prep_for_estimation)."""
    return 541.5


def P_DATA_PADM_SUGA_2009():
    r"""P_DATA(MS, "PADM", "SUGA", ExpostT) with a quota from 2009.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 36-36):

           P_DATA(MS,"PADM","SUGA",ExpostT) $ (P_DATA(MS,"QUTS","SUGA",ExpostT) and (ORDT(ExpostT) GE ORDT("2009"))) = 404.4;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (prepare.prep_for_estimation)."""
    return 404.4


def p_data_UVAG_SUGA(padm, uvag_before, padm_before):
    r"""p_data(MS, "UVAG", "SUGA", YEARS) without one (a loop over the ex-post years): the year's PADM plus the year
    before's margin of the price over PADM.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 38-42):

           LOOP(years $ expostT(years),
               p_data(MS,"UVAG","SUGA",YEARS) $ (    (NOT p_data(MS,"UVAG","SUGA",YEARS))
                                                 $ p_data(MS,"UVAG","SUGA",YEARS-1)
                                                 $ p_data(MS,"PADM","SUGA",YEARS-1))
               = p_data(MS,"PADM","SUGA",YEARS) + (p_data(MS,"UVAG","SUGA",YEARS-1) - p_data(MS,"PADM","SUGA",YEARS-1));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (prepare.prep_for_estimation)."""
    return padm + (uvag_before - padm_before)


def p_data_BASM_weighted(value, weight):
    r"""p_data(MS, "UVAG", "SUGA", "BASM"): the base years' price weighted by MAPR.SUGA. Returns (the weighted mean,
    the weights' sum) per region (0 where the weights sum to 0).

    value, weight: pandas Series over (region, year), the weight 0 outside BASYRSM.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 45-47):

           p_data(MS,"UVAG","SUGA","BASM") $ SUM(BASYRSM, p_data(MS,"MAPR","SUGA",BASYRSM))
               = SUM(BASYRSM, p_data(MS,"UVAG","SUGA",BASYRSM)*p_data(MS,"MAPR","SUGA",BASYRSM))
               / SUM(BASYRSM, p_data(MS,"MAPR","SUGA",BASYRSM));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (prepare._basm_weighted)."""
    num = (value * weight).groupby(level="region").sum()
    den = weight.groupby(level="region").sum()
    return (num / den.where(den != 0, 1.0)).where(den != 0, 0.0), den


def p_data_removed():
    r"""p_data(Rest, ., ., YEARS) of the series CAPTRD does not use: removed (MAPR of the outputs with GROF, CATT, UAAR,
    the manure rows, the nutrients but INCE, LOSF.ICOW, the feed rows but GROF, the market balances of products and
    secondary products without production or imports around the base year, PRCY without MAPR; the base years'
    ILAM and YLAM and SHGM.SLGW flagged as outliers).

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 52-52):

           p_data(Rest,"MAPR",O,YEARS) $ p_data(Rest,"GROF",O,YEARS) = 0;

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 53-53):

           p_data(Rest,COLS,"CATT",YEARS) = 0;

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 55-55):

           p_data(Rest,"UAAR",ROWS,YEARS) = 0;

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 56-56):

           p_data(Rest,COLS,FOUT,YEARS)   = 0;

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 58-58):

           p_data(Rest,NCNC,ROWS,YEARS_BASM) $ (not sameas(rows,"INCE")) = 0;

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 61-61):

           p_data(Rest,"LOSF","ICOW",YEARS) = 0;

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 65-65):

           p_data(Rest,MrkBalee,FEED,YEARS) $ (NOT SAMEAS(MrkBalee,"GROF")) = 0;

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 66-66):

           p_data(Rest,MrkBale,O,YEARS)     $ (SUM(BASYRS5, p_data(Rest,"GROF",O,BASYRS5) + p_data(REST,"IMPT",O,BASYRS5)) EQ 0.)       = 0;

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 67-67):

           p_data(Rest,MrkBale,SECO,YEARS)  $ (SUM(BASYRS5, p_data(Rest,"MAPR",SECO,BASYRS5) + p_data(REST,"IMPT",SECO,BASYRS5)) EQ 0.) = 0;

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 68-68):

           p_data(Rest,"PRCY",SECO,YEARS)  $ (NOT p_data(Rest,"MAPR",SECO,YEARS)) = 0;

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 141-142):

           p_data(Rest,cols,rows,BASYRSM)
               $ (  (sameas(rows,"ILAM") or sameas(rows,"YLAM")) $ (p_data(Rest,"SHGM","SLGW",BASYRSM) eq -999)) = 0;

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 143-143):

           p_data(Rest,"SHGM","SLGW",BASYRSM) $ (p_data(Rest,"SHGM","SLGW",BASYRSM) eq -999) = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (prepare.prep_for_estimation)."""
    return 0.0


def p_data_group_sum(members, zero):
    r"""p_data(Rest, ., ., YEARS_BASM) of an aggregate: its members summed (UAAR from the crops, the crop groups' levels,
    the product groups' market balances, INHA of CERE and MEAS, EXPE.LEVL).

    members: pandas Series over (region, year), in the caller's order; zero: the Series to sum from.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 86-86):

           p_data(Rest,"UAAR","LEVL",ExpostT) = SUM(MCACT, p_data(Rest,MCACT,"LEVL",ExpostT));

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 90-91):

           p_data(Rest,GRPC,"LEVL","BASM")
            = SUM(CROPC_TO_G(CACT,GRPC), p_data(Rest,CACT,"LEVL","BASM"));

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 93-94):

           p_data(Rest,GRPC,"LEVL",ExpostT)
            = SUM(CROPC_TO_G(CACT,GRPC), p_data(Rest,CACT,"LEVL",ExpostT));

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 157-158):

           p_data(MS,MrkBaleE,GRPR,YEARS_BASM)
            = SUM(ROWS_TO_G(ROWS,GRPR),  p_data(MS,MrkBaleE,Rows,YEARS_BASM));

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 186-187):

           p_data(MS,"INHA",grpr,YEARS_BASM) $ (sameas(grpr,"CERE") or sameas(grpr,"MEAS"))
              = sum(rows_to_g(rows,grpr),p_data(MS,"INHA",ROWS,YEARS_BASM));

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 197-198):

           p_data(MS,"EXPE","LEVL",YEARS_BASM)
              = SUM(Rows $ ( NOT (SAMEAS(Rows,"LEVL") or GRPR(ROWS))), p_data(MS,"EXPE",Rows,YEARS_BASM));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (prepare.prep_for_estimation)."""
    return sum(members, zero)


def p_data_SLGW(meat, yani):
    r"""p_data(Rest, breedAct, "SLGW", expostT): the meat of the female breeding animals over their young animals, in
    kg.

    meat, yani: the outputs' and the young animals' sums, pandas Series over (region, year).

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 98-102):

           p_data(Rest,breedAct,"SLGW",expostT) $ ( SUM(PACT_TO_I(breedAct,IYANI),p_data(Rest,breedAct,IYANI,expostT))
                                                  $ p_data(Rest,breedAct,"LEVL",expostT)  )

            = SUM(PACT_TO_O(breedAct,MEAT) ,p_data(Rest,breedAct,MEAT,expostT))
            / SUM(PACT_TO_I(breedAct,IYANI),p_data(Rest,breedAct,IYANI,expostT))*1000;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (prepare.prep_for_estimation)."""
    return (meat / yani.where(yani != 0, 1.0)) * 1000.0


def p_data_SLGW_BASM(total, count):
    r"""p_data(Rest, breedAct, "SLGW", "BASM"): the mean of the nonzero BASYRSM values (0 without one).

    total, count: the values' sum and number per region.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 104-106):

           p_data(Rest,breedAct,"SLGW","BASM") $ SUM(BASYRSM $ p_data(Rest,breedAct,"SLGW",BASYRSM),1)
               = SUM(BASYRSM, p_data(Rest,breedAct,"SLGW",BASYRSM))
               / SUM(BASYRSM $ p_data(Rest,breedAct,"SLGW",BASYRSM),1);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (prepare._basm_mean)."""
    return (total / count.where(count != 0, 1.0)).where(count != 0, 0.0)


def p_data_SHGM_SLGW_mean(total, count, any_):
    r"""p_data(Rest, "SHGM", "SLGW", "mean"): the mean over the ex-post years with a value.

    total, count, any_: per region (as pandas Series over (region, year)) the values' sum, their number and whether
    there is one.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 111-112):

           p_data(Rest,"SHGM","SLGW","mean") $ SUM(ExpostT $ p_data(Rest,"SHGM","SLGW",ExpostT),1)
               = SUM(ExpostT, p_data(Rest,"SHGM","SLGW",ExpostT))/SUM(ExpostT $ p_data(Rest,"SHGM","SLGW",ExpostT),1);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (prepare.prep_for_estimation)."""
    return (total / count.where(count != 0, 1.0)).where(any_, 0.0)


def p_data_SHGM_SLGW_low(mean):
    r"""p_data(Rest, "SHGM", "SLGW", BASYRSM) below 15% of the mean: the mean.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 119-122):

           p_data(Rest,"SHGM","SLGW",BASYRSM)
               $  ((p_data(Rest,"SHGM","SLGW","mean") gt 0)
        	   $  (p_data(Rest,"SHGM","SLGW",BASYRSM) lt (.15*p_data(Rest,"SHGM","SLGW","mean"))))
        	   = p_data(Rest,"SHGM","SLGW","mean");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (prepare.prep_for_estimation)."""
    return mean


def p_data_SHGM_BASM(total, count):
    r"""p_data(Rest, "SHGM" .SLGW / ., ILAM / YLAM, "BASM") where a base year is flagged as an outlier: the mean over
    the base years not flagged.

    total, count: per region (as pandas Series over (region, year)) the values' sum over those years and their
    number.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 129-132):

           p_data(Rest,"SHGM","SLGW","BASM")
               $ ( sum(basyrsm $ (p_data(Rest,"SHGM","SLGW",BASYRSM) eq -999),1) $ p_data(Rest,"SHGM","SLGW","BASM"))
               = sum(basyrsm $ (p_data(Rest,"SHGM","SLGW",BASYRSM) ne -999),p_data(Rest,"SHGM","SLGW",BASYRSM))
               / sum(basyrsm $ (p_data(Rest,"SHGM","SLGW",BASYRSM) ne -999),1);

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 134-139):

           p_data(Rest,cols,rows,"BASM")
              $ ( sum(basyrsm $ (p_data(Rest,"SHGM","SLGW",BASYRSM) eq -999),1)
                 $ (sameas(rows,"ILAM") or sameas(rows,"YLAM"))
                 $ p_data(Rest,"SHGM","SLGW","BASM"))
               = sum(basyrsm $ (p_data(Rest,"SHGM","SLGW",BASYRSM) ne -999),p_data(Rest,cols,rows,BASYRSM))
               / sum(basyrsm $ (p_data(Rest,"SHGM","SLGW",BASYRSM) ne -999),1);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (prepare._shgm_basm)."""
    return total / count.where(count != 0, 1.0)


def p_data_UVAG(eaag, grof):
    r"""p_data(Rest, "UVAG", ., YEARS_BASM) with GROF and EAAG (and of the product groups): the unit value, EAAG over
    GROF in EUR/t.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 149-150):

           p_data(Rest,"UVAG",S_RowsEst,YEARS_BASM) $ (p_data(Rest,"GROF",S_RowsEst,YEARS_BASM) $ p_data(Rest,"EAAG",S_RowsEst,YEARS_BASM))
                = p_data(Rest,"EAAG",S_RowsEst,YEARS_BASM)/p_data(Rest,"GROF",S_RowsEst,YEARS_BASM) * 1000.;

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 169-170):

           p_data(Rest,"UVAG",GRPR   ,YEARS_BASM) $ p_data(Rest,"GROF",GRPR,YEARS_BASM)
             = p_data(Rest,"EAAG",GRPR,YEARS_BASM)/p_data(Rest,"GROF",GRPR,YEARS_BASM) * 1000;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (prepare.prep_for_estimation)."""
    return eaag / grof.where(grof != 0, 1.0) * 1000.0


def p_data_EAAG(uvag, grof):
    r"""p_data(Rest, "EAAG", S_RowsEst, YEARS_BASM): the unit value times GROF.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 152-153):

           p_data(Rest,"EAAG",S_RowsEst,YEARS_BASM)
              = p_data(Rest,"UVAG",S_RowsEst,YEARS_BASM) * p_data(Rest,"GROF",S_RowsEst,YEARS_BASM) * 0.001;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (prepare.prep_for_estimation)."""
    return uvag * grof * 0.001


def p_data_DOMM(dompos, zero):
    r"""p_data(MS, "DOMM", ROWS, YEARS_BASM): the domestic uses of at least 1E-12 summed (where they and DOMM are
    given, or DOMM is negative but for the young animals' rows).

    dompos: the DOMPOS' pandas Series over (region, year), in the caller's order.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 161-167):

           p_data(MS,"DOMM",ROWS,YEARS_BASM)  $ (   ( SUM(DOMPOS $ (p_data(MS,DOMPOS,ROWS,YEARS_BASM) GE 1.E-12), p_data(MS,DOMPOS,ROWS,YEARS_BASM))
                                                    $ p_data(MS,"DOMM",ROWS,YEARS_BASM))
        *                                       also remove DOMM<0 stemming from negative STCM that have been deleted
                                                or  ((p_data(MS,"DOMM",ROWS,YEARS_BASM) lt 0) $ (not OYANI_ROWS(rows))))
        *                    prevent  unplanned assignment of 1.E-14
        *                    and thus fixation to zero in fix_est:
             = SUM(DOMPOS $ (p_data(MS,DOMPOS,ROWS,YEARS_BASM) GE 1.E-12), p_data(MS,DOMPOS,ROWS,YEARS_BASM));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (prepare.prep_for_estimation)."""
    return sum((v.where(v >= 1e-12, 0.0) for v in dompos), zero)


def p_data_UVAD(expe, hcom):
    r"""p_data(MS, "UVAD", GRPR, YEARS_BASM): the consumer price, EXPE over HCOM in EUR/t.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 172-173):

           p_data(MS,"UVAD",GRPR   ,YEARS_BASM) $ p_data(MS,"HCOM",GRPR,YEARS_BASM)
             = p_data(MS,"EXPE",GRPR,YEARS_BASM)/p_data(MS,"HCOM",GRPR,YEARS_BASM) * 1000;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (prepare.prep_for_estimation)."""
    return expe / hcom.where(hcom != 0, 1.0) * 1000.0


def p_data_TOOU(outputs, zero):
    r"""p_data(MS, MPACT, "TOOU", YEARS_BASM): the activity's outputs valued at their unit values, in 1000 EUR.

    outputs: (the output per unit, its UVAG) pandas Series, in the caller's order.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 175-176):

           p_data(MS,MPACT,"TOOU",YEARS_BASM)  =
              SUM(PACT_TO_O(MPACT,S_RowsEst), p_data(MS,MPACT,S_RowsEst,YEARS_BASM) * p_data(MS,"UVAG",S_RowsEst,YEARS_BASM)) * 0.001;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (prepare.prep_for_estimation)."""
    return sum((a * u for a, u in outputs), zero) * 0.001


def p_data_NTRD(expt, impt):
    r"""p_data(MS, "NTRD", S_RowsEst, YEARS_BASM): exports less imports.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 178-180):

           p_data(MS,"NTRD",S_RowsEst,YEARS_BASM) =
                 p_data(MS,"EXPT",S_RowsEst,YEARS_BASM)
               - p_data(MS,"IMPT",S_RowsEst,YEARS_BASM);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (prepare.prep_for_estimation)."""
    return expt - impt


def p_data_foodSh(value):
    r"""p_data(MS, "foodSh", "cere" / "meas", YEARS_BASM): soft wheat's, beef's.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 188-188):

           p_data(MS,"foodSh","cere",YEARS_BASM) = p_data(MS,"foodSh","swhe",YEARS_BASM);

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 189-189):

           p_data(MS,"foodSh","meas",YEARS_BASM) = p_data(MS,"foodSh","beef",YEARS_BASM);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (prepare.prep_for_estimation)."""
    return value


def p_data_CSSP(uvad, uvag):
    r"""p_data(MS, "CSSP", ROWS, YEARS_BASM): the consumer subsidy equivalent, UVAD less UVAG.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 191-192):

           p_data(MS,"CSSP",ROWS,YEARS_BASM) $ (p_data(MS,"UVAD",ROWS,YEARS_BASM) $ p_data(MS,"UVAG",ROWS,YEARS_BASM))
              = p_data(MS,"UVAD",ROWS,YEARS_BASM) - p_data(MS,"UVAG",ROWS,YEARS_BASM);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (prepare.prep_for_estimation)."""
    return uvad - uvag


def p_data_EXPE(uvad, hcom, inha):
    r"""p_data(MS, "EXPE", ROWS, YEARS_BASM): the expenditure per head.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 194-195):

           p_data(MS,"EXPE",ROWS,YEARS_BASM) $ ( p_data(MS,"HCOM",ROWS,YEARS_BASM) $ p_data(MS,"INHA","LEVL",YEARS_BASM))
              = p_data(MS,"UVAD",ROWS,YEARS_BASM)*p_data(MS,"HCOM",ROWS,YEARS_BASM)/p_data(MS,"INHA","LEVL",YEARS_BASM);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (prepare.prep_for_estimation)."""
    return uvad * hcom / inha.where(inha != 0, 1.0)


def p_data_LU(animals, uaar, zero):
    r"""p_data(Rest, "LU", "LEVL", YEARS_BASM) with UAAR: the livestock units per hectare.

    animals: (the animal activity's level, its p_LUUnits) of MAACT, in the caller's order.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 202-203):

           p_data(Rest,"LU","LEVL",YEARS_BASM) $ p_data(REST,"UAAR","LEVL",YEARS_BASM)
              = SUM(MAACT $ p_data(REST,MAACT,"LEVL",YEARS_BASM), p_data(REST,MAACT,"LEVL",YEARS_BASM) * p_LUUnits(MAACT))/p_data(REST,"UAAR","LEVL",YEARS_BASM);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (prepare.prep_for_estimation)."""
    return sum((v * float(u) for v, u in animals), zero) / uaar.where(uaar != 0, 1.0)


def p_data_nObs_excluded(value, excluded):
    r"""p_data(Rest, ., ., "nObs" / "nW"): 0 where the series has no BASM (and is no biofuel COCO position), for
    INHA.LEVL and for DOMM of the young animals.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 215-216):

           p_data(Rest,S_ColsEst,S_RowsEst,"nObs") $ (NOT (   p_data(Rest,S_ColsEst,S_RowsEst,"BASM")
                                                           or bioColsCoco(s_colsest) or bioRowsCoco(s_rowsest) )) =0;

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 217-218):

           p_data(Rest,S_ColsEst,S_RowsEst,"nW")   $ (NOT (   p_data(Rest,S_ColsEst,S_RowsEst,"BASM")
                                                           or bioColsCoco(s_colsest) or bioRowsCoco(s_rowsest) )) =0;

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 221-221):

           p_data(Rest,"INHA","LEVL","nObs") = 0;

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 222-222):

           p_data(Rest,"INHA","LEVL","nW") = 0;

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 226-226):

           p_data(Rest,"DOMM",OYANI,"nObs") = 0;

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 227-227):

           p_data(Rest,"DOMM",OYANI,"nW") = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (statistics.statistics)."""
    return np.where(excluded, 0.0, value)


def p_data_BAS(total, count, nobs):
    r"""p_data(Rest, ., ., "BAS") of a series with observations: the number of BASYRS5 years with a value, then their
    sum over it (the mean of the observed base years).

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 255-256):

           p_data(Rest,S_ColsEst,S_RowsEst,"BAS") $ p_data(Rest,S_ColsEst,S_RowsEst,"nObs")
              = SUM(BASYRS5 $ p_data(Rest,S_ColsEst,S_RowsEst,BASYRS5), 1.);

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 258-259):

           p_data(Rest,S_ColsEst,S_RowsEst,"BAS") $  p_data(Rest,S_ColsEst,S_RowsEst,"BAS")
             = SUM(BASYRS5, p_data(Rest,S_ColsEst,S_RowsEst,BASYRS5))/p_data(Rest,S_ColsEst,S_RowsEst,"BAS");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (statistics.statistics)."""
    return np.where((nobs != 0) & (count > 0), total / np.maximum(count, 1), 0.0)


def p_data_BAS_PACT_TO_IO(values, levels):
    r"""p_data(Rest, MPACT, ., "BAS") of an activity's inputs and outputs where its level has a BAS: the base years'
    values weighted by its levels (GAMS: a zero level sum divides by zero; the port gives NaN).

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 263-264):

           p_data(Rest,MPACT,S_RowsEst,"BAS") $ ( S_ColsEst(MPACT) $  p_data(Rest,MPACT,"LEVL","BAS") $ PACT_TO_IO(MPACT,S_RowsEst)) =
             SUM(BASYRS5, p_data(Rest,MPACT,S_RowsEst,BASYRS5)*p_data(Rest,MPACT,"LEVL",BASYRS5))/SUM(BASYRS5, p_data(Rest,MPACT,"LEVL",BASYRS5));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (statistics.statistics)."""
    den = levels.sum()
    return float((values * levels).sum() / den) if den else np.nan


def p_data_feed_removed():
    r"""p_data(Rest, MAACT, FEED, "BASM") at most 1E-4, or where the country has none: removed.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 275-275):

           p_data(Rest,MAACT,FEED,"BASM")     $ (p_data(REST,MAACT,Feed,"BASM") LE 1.E-4)               = 0;

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 276-276):

           p_data(Rest,MAACT,FEED,"BASM")     $ (NOT SUM(MAP_RR(MS,Rest),         p_data(MS,MAACT,Feed,"BASM")))     = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (statistics.statistics)."""
    return 0.0


def p_data_feed_nObs():
    r"""p_data(Rest, MAACT, FEED, "nObs") where the country has the coefficient and the animal is estimated, and GROF's
    of a feed row where some animal has nObs: 1.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 279-279):

           p_data(Rest,MAACT,FEED,"nObs") $ (SUM(MAP_RR(MS,Rest), p_data(MS,MAACT,Feed,"BASM"))  $ p_data(Rest,MAACT,"LEVL","nObs")) = 1;

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 295-296):

           p_data(Rest,"GROF",FEED,"nObs") $ ( (NOT p_data(Rest,"GROF",FEED,"nObs")) $ SUM(MAACT, p_data(Rest,MAACT,FEED,"nObs")))
              = 1;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (statistics.statistics)."""
    return 1.0


def p_data_feed_BAS(basm):
    r"""p_data(Rest, MAACT .FEED / "GROF" .FEED, "BAS"): BASM (where the country has the coefficient; GROF's where it has
    none).

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 280-280):

           p_data(Rest,MAACT,FEED,"BAS")  $ SUM(MAP_RR(MS,Rest), p_data(MS,MAACT,Feed,"BASM")) = p_data(Rest,MAACT,Feed,"BASM");

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 297-298):

           p_data(Rest,"GROF",FEED,"BAS")  $ ( (NOT p_data(Rest,"GROF",FEED,"BAS"))  $ SUM(MAACT, p_data(Rest,MAACT,FEED,"nObs")))
              = p_data(Rest,"GROF",FEED,"BASM");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (statistics.statistics)."""
    return basm


def p_data_feed_small(ms_basm):
    r"""p_data(Rest, MAACT, FEED, "BAS" / "BASM") with nObs and none of its own: 0.1% of the country's BASM.

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 281-282):

           p_data(Rest,MAACT,FEED,"BAS")  $ (p_data(Rest,MAACT,FEED,"nObs") $ (NOT p_data(Rest,MAACT,FEED,"BAS")))
              = SUM(MAP_RR(MS,Rest), p_data(MS,MAACT,Feed,"BASM")) * 0.001;

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 283-284):

           p_data(Rest,MAACT,FEED,"BASM") $ (p_data(Rest,MAACT,FEED,"nObs") $ (NOT p_data(Rest,MAACT,FEED,"BASM")))
              = SUM(MAP_RR(MS,Rest), p_data(MS,MAACT,Feed,"BASM")) * 0.001;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (statistics.statistics)."""
    return ms_basm * 0.001


def p_data_BSY(yields, bas):
    r"""p_data(Rest, MPACT, ., "BSY") of the yields where the activity has a level BAS: the mean of the three highest
    distinct yields over EIGHTLST (GAMS's "1", "2", "3"), at least BAS; none without a first.

    yields: numpy array over EIGHTLST (CAPRI: a missing year as 0, as SMAX runs over the set; with
    captrd.zeros_as_missing false the caller passes the observed years only).

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 305-306):

           p_data(Rest,MPACT,S_RowsEst,"1") $ ( S_ColsEst(MPACT) $ p_data(Rest,MPACT,"LEVL","BAS") $ PACT_TO_Y(MPACT,S_RowsEst))
             =  SMAX(EIGHTLST, p_data(Rest,MPACT,S_RowsEst,EIGHTLST));

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 308-309):

           p_data(Rest,MPACT,S_RowsEst,"2") $ ( S_ColsEst(MPACT) $ p_data(Rest,MPACT,"LEVL","BAS") $ PACT_TO_Y(MPACT,S_RowsEst))
            =  SMAX(EIGHTLST $ (p_data(Rest,MPACT,S_RowsEst,EIGHTLST) ne p_data(Rest,MPACT,S_RowsEst,"1")), p_data(Rest,MPACT,S_RowsEst,EIGHTLST));

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 311-314):

           p_data(Rest,MPACT,S_RowsEst,"3") $ ( S_ColsEst(MPACT) $ p_data(Rest,MPACT,"LEVL","BAS") $ PACT_TO_Y(MPACT,S_RowsEst))
            =  SMAX(EIGHTLST $ (   (p_data(Rest,MPACT,S_RowsEst,EIGHTLST) ne p_data(Rest,MPACT,S_RowsEst,"1"))
                                 $ (p_data(Rest,MPACT,S_RowsEst,EIGHTLST) ne p_data(Rest,MPACT,S_RowsEst,"2"))),
                                                     p_data(Rest,MPACT,S_RowsEst,EIGHTLST));

    CAPRI's GAMS (captrd/prep_data_for_estimation.gms l. 316-317):

           p_data(Rest,MPACT,S_RowsEst,"BSY") $ (p_data(Rest,MPACT,S_RowsEst,"1") $ PACT_TO_Y(MPACT,S_RowsEst))
             = MAX( (p_data(Rest,MPACT,S_RowsEst,"1")+p_data(Rest,MPACT,S_RowsEst,"2")+p_data(Rest,MPACT,S_RowsEst,"3"))/3,p_data(Rest,MPACT,S_RowsEst,"BAS"));

    Departures from CAPRI: the helpers "1", "2", "3" (and their removal, l. 319-321) are locals; the domain condition in the caller
    (statistics.statistics)."""
    first = _gmax(yields)
    if not first:
        return 0.0
    second = _gmax(yields[yields != first])
    third = _gmax(yields[(yields != first) & (yields != second)])
    return max((first + second + third) / 3.0, bas)


def _gmax(values):
    """GAMS SMAX: -INF over an empty set."""
    return float(values.max()) if values.size else -np.inf
