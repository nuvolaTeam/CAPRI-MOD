r"""CAPTRD's statements of captrd/define_eu_supports.gms (CAPRI star 3.0, captrd.gms l. 1064-1072, between Solve1 and
Solve2 of the ex-ante loop; %aglinkTightLink% off): DG AGRI's information brought into the member states' supports,
as named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). capri_mod/pipeline/captrd/eu_supports.py (eu_supports, _set_extrap) holds the
loops over the member states, the EU aggregates, the positions and the ex-ante year, the conditions and the order, and
calls them; the arithmetic is the port's, so the supports are unchanged. mn and mx are p_exTrapMinMax("min") and
("max") (captrd.gms l. 336-337).
"""
from __future__ import annotations

import math


def ordT_StartpointExtrap(years):
    r"""ordT("StartpointExtrap"): the mean of the ordinals of Fst_exAnte and Sec_exAnte.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 67-68):

               ordT("StartpointExtrap") = SUM(years $ (Fst_exAnte(Years) or Sec_exAnte(Years)),ordT(years))
                                        / SUM(years $ (Fst_exAnte(Years) or Sec_exAnte(Years)),1);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return sum(years) / len(years)


def P_Result_StartpointExtrap_Step3(values):
    r"""P_Result(MS, ., ., "StartpointExtrap", "Step3") of a position with DGAgri1 at %lst_dgagri%: Step3's mean over
    Fst_exAnte and Sec_exAnte.

    values: Step3 of the years, in order (all of them, the zeros included).

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 72-81):

               P_Result(MS,S_ColsEst,S_RowsEst,"StartpointExtrap","Step3")
                         $ ( SUM(Lst_DGAgri, P_Result(MS,S_ColsEst,S_RowsEst,Lst_DGAgri,"DGAgri1")
        *          -- Special case PRCI (for HFCS) has been entered as an expert support => no DG agri support on MS level
                                           + SUM(MS_TO_RMSAGG(MS,CurEuropAgg),P_Result(CurEuropAgg,"PRCI","MAIZ",Lst_DGAgri,"DGAgri1"))
                                           $ (sameas(S_ColsEst,"PRCI") or sameas(S_ColsEst,"INDM")) $ sameas(S_RowsEst,"MAIZ"))
                           $ SUM(years $ (Fst_exAnte(Years) or Sec_exAnte(Years)),
                                               P_Result(MS,S_ColsEst,S_RowsEst,years,"Step3")))
               = SUM(years $ (Fst_exAnte(Years) or Sec_exAnte(Years)),
                                               P_Result(MS,S_ColsEst,S_RowsEst,years,"Step3"))
               / SUM(years $ (Fst_exAnte(Years) or Sec_exAnte(Years)),1);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return sum(values) / len(values)


def P_Result_BAS_Extrap(step3_lst, step3_start, n):
    r"""P_Result(MS, ., ., "BAS", "Extrap"): Step3's yearly growth rate from the start point to %lst_dgagri%, over
    n = OrdT("%lst_dgagri%") - OrdT("StartpointExtrap") years.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 149-156):

               P_Result(MS,S_ColsEst,S_RowsEst,"BAS","Extrap")
                       $ (    (NOT SAMEAS(S_COlsEst,"NTRD"))
                          and (P_Result(MS,S_ColsEst,S_RowsEst,"StartpointExtrap","Step3") GT 1.E-4)
                          and (P_Result(MS,S_ColsEst,S_RowsEst,"%lst_dgagri%","Step3") GT 1.E-4))

               =  ( ( P_Result(MS,S_ColsEst,S_RowsEst,"%lst_dgagri%","Step3")
                    /P_Result(MS,S_ColsEst,S_RowsEst,"StartpointExtrap","Step3"))
                   **(1/(OrdT("%lst_dgagri%") - OrdT("StartpointExtrap"))))-1;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return (step3_lst / step3_start) ** (1. / n) - 1.


def P_Result_BSY_Extrap(bas, mn, mx):
    r"""P_Result(MS, ., ., "BSY", "Extrap"): the logistic's slope matching the growth rate at %lst_dgagri%.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 161-165):

               P_Result(MS,S_ColsEst,S_RowsEst,"BSY","Extrap")
                       $ P_Result(MS,S_ColsEst,S_RowsEst,"BAS","Extrap")
               = P_Result(MS,S_ColsEst,S_RowsEst,"BAS","Extrap")
               / (1-p_exTrapMinMax("min"))
               / (1-(1-p_exTrapMinMax("min"))/(p_exTrapMinMax("max")-p_exTrapMinMax("min")));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return bas / (1 - mn) / (1 - (1 - mn) / (mx - mn))


def P_Result_DGAgri1_Extrap(step3_lst, bsy, n, mn, mx):
    r"""P_Result(MS, ., ., ExAnte, "DGAgri1") beyond %lst_dgagri%: Step3 of %lst_dgagri% times the logistic between mn
    and mx of BSY x n (n = OrdT(exAnte) - OrdT("%lst_dgagri%")), 1 without a slope.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 170-184):

               P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"DGAgri1")
        *                    Note1: Checking for the last DGAgri supports covers the case that StartpointExtrap may be zero (BIOF)
        *                    Note2: lst_dgAgri support at MS level may stem from the section "Disaggregate supports from DG-AGRI..."
        *                           (possibly assigned in that run through the exante loop when Exante=lst_dgagri)
                         $ SUM(Lst_DGAgri, P_Result(MS,S_ColsEst,S_RowsEst,Lst_DGAgri,"DGAgri1")
        *                    - Special case PRCI (for HFCS) has been entered as an expert support => no DG agri support on MS level
                                         + SUM(MS_TO_RMSAGG(MS,CurEuropAgg),P_Result(CurEuropAgg,"PRCI","MAIZ",Lst_DGAgri,"DGAgri1"))
                                         $ (sameas(S_ColsEst,"PRCI") or sameas(S_ColsEst,"INDM")) $ sameas(S_RowsEst,"MAIZ"))
               = P_Result(MS,S_ColsEst,S_RowsEst,"%lst_dgagri%","Step3")
               * ((  p_exTrapMinMax("min")
                   +(p_exTrapMinMax("max")-p_exTrapMinMax("min"))
                   *SIGMOID(P_Result(MS,S_ColsEst,S_RowsEst,"BSY","Extrap")*(OrdT(exAnte)-OrdT("%lst_dgagri%"))))
                            $ P_Result(MS,S_ColsEst,S_RowsEst,"BSY","Extrap")
        *                   in case that the growth rate could not be calculated: use no change
                + 1.        $ (NOT P_Result(MS,S_ColsEst,S_RowsEst,"BSY","Extrap")));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    f = (mn + (mx - mn) * _sigmoid(bsy * n)) if bsy else 1.
    return step3_lst * f


def P_Result_Extrap(dgagri1):
    r"""P_Result(MS, S_ColsEst, S_RowsEst, ExAnte, "Extrap"): DGAgri1 (beyond %lst_dgagri%; again after the long-run
    merge from %lst_dgagri%).

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 189-189):

               P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"Extrap") = P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"DGAgri1");

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 331-332):

                   P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"Extrap") $      (ORDT(ExAnte) GE ORDT("%lst_dgagri%"))
                      = P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"DGAgri1");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return dgagri1


def P_Result_rmAggSup_Step2(members):
    r"""P_Result(rmAggSup, ., ., ExAnte, "Step2"): the members' Step2 summed (of the market balances and levels with an
    aggregate's DGAgri1, over the members without their own; NTRD.DDGS and GROF.FPRO over all).

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 214-217):

            P_Result(rmAggSup,MrkBalee,S_RowsEst,ExAnte,"Step2")
              $ P_Result(rmAggSup,MrkBalee,S_RowsEst,Exante,"DGAgri1")
              = SUM(MS_TO_RMSAGG(MS,rmAggSup) $ (NOT P_Result(MS,MrkBalee,S_RowsEst,ExAnte,"DGAgri1")),
                      P_Result(MS,MrkBalee,S_RowsEst,ExAnte,"Step2"));

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 220-223):

            P_Result(rmAggSup,S_ColsEst,"LEVL",ExAnte,"Step2")
              $ P_Result(rmAggSup,S_ColsEst,"LEVL",ExAnte,"DGAgri1")
              = SUM(MS_TO_RMSAGG(MS,rmAggSup) $ (NOT P_Result(MS,S_ColsEst,"LEVL",ExAnte,"DGAgri1")),
                      P_Result(MS,S_ColsEst,"LEVL",ExAnte,"Step2"));

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 540-541):

            P_Result(rmAggSup,"NTRD","DDGS",ExAnte,"Step2")
              = SUM(MS_TO_RMSAGG(MS,rmAggSup), p_result(MS,"NTRD","DDGS",ExAnte,"Step2"));

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 542-543):

            P_Result(rmAGGSup,"GROF","FPRO",ExAnte,"Step2")
              = SUM(MS_TO_RMSAGG(MS,rmAggSup), p_result(MS,"GROF","FPRO",ExAnte,"Step2"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return sum(members)


def P_Result_DGAgri1_from_rmAggSup(step2, aggregates):
    r"""P_Result(MS, ., ., ExAnte, "DGAgri1") without one: the member's Step2 times its aggregates' DGAgri1 over their
    Step2.

    aggregates: (DGAgri1, Step2) of the member's aggregates with a Step2, in the caller's order.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 238-245):

            P_Result(MS,MrkBalee,S_RowsEst,ExAnte,"DGAgri1")
              $(not P_Result(MS,MrkBalee,S_RowsEst,ExAnte,"DGAgri1"))
              = P_Result(MS,MrkBalee,S_RowsEst,ExAnte,"Step2")
              * SUM(MS_TO_RMSAGG(MS,rmAggSup) $ (P_Result(rmAggSup,MrkBalee,S_RowsEst,ExAnte,"Step2") gt eps),
        *           -- recalculated in scale_DGAGRi_baseline without those MS where MS level information is given:
                    P_Result(rmAggSup,MrkBalee,S_RowsEst,Exante,"DGAgri1")
        *           -- calculated above without those MS where MS level information is given from DGAgri
                   /P_Result(rmAggSup,MrkBalee,S_RowsEst,Exante,"Step2")) ;

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 248-255):

            P_Result(MS,S_ColsEst,"LEVL",ExAnte,"DGAgri1")
              $(not P_Result(MS,S_ColsEst,"LEVL",ExAnte,"DGAgri1"))
              = P_Result(MS,S_ColsEst,"LEVL",ExAnte,"Step2")
              * SUM(MS_TO_RMSAGG(MS,rmAggSup) $ P_Result(rmAggSup,S_ColsEst,"LEVL",ExAnte,"Step2"),
        *           -- recalculated in scale_DGAGRi_baseline without those MS where MS level information is given:
                    P_Result(rmAggSup,S_ColsEst,"LEVL",Exante,"DGAgri1")
        *           -- calculated above without those MS where MS level information is given from DGAgri
                   /P_Result(rmAggSup,S_ColsEst,"LEVL",Exante,"Step2")) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return step2 * sum(d / s for d, s in aggregates)


def P_Result_DGAgri1_HERD(levl):
    r"""P_Result(MS, AACTwith365days, "HERD", ExAnte, "DGAgri1") without one: the level.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 259-262):

            P_Result(MS,S_ColsEst,"HERD",ExAnte,"DGAgri1") $ ( (NOT P_Result(MS,S_ColsEst,"HERD",ExAnte,"DGAgri1"))
                                                              $ P_Result(MS,S_ColsEst,"LEVL",ExAnte,"DGAgri1")
                                                              $ AACTwith365days(s_COLSest))
              = P_Result(MS,S_ColsEst,"LEVL",ExAnte,"DGAgri1");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return levl


def P_Result_Longrun1(longrun, dgagri1, year, phase_in, long_exp, long_wgt):
    r"""P_Result(MS, ., ., ExAnte, "Longrun1") beyond %phaseInYr% with Longrun and DGAgri1: Longrun weighted from 0 at
    %phaseInYr% to p_longWgt in 2050 with the exponent p_longExp, DGAgri1 the rest.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 275-285):

                   P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"Longrun1") $ (     (ORDT(ExAnte) GT ORDT("%phaseInYr%"))
                                                                         and P_Result(MS,S_ColsEst,S_RowsEst,Exante,"Longrun")
                                                                         and P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"DGAgri1"))
                      =    P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"Longrun")
        *                  Weight for Longrun increases from 0 to p_longWgt as 2050 is approached
                        *    ((min(ORDT("2050"),ORDT(ExAnte))-ORDT("%phaseInYr%"))/(ORDT("2050")-ORDT("%phaseInYr%")))**p_longExp*p_longWgt

                        +  P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"DGAgri1")
        *                  Weight for extrapolated DGAgri1 decreases from 1 to (1-p_longWgt) as 2050 is approached
                        * [1-((min(ORDT("2050"),ORDT(ExAnte))-ORDT("%phaseInYr%"))/(ORDT("2050")-ORDT("%phaseInYr%")))**p_longExp*p_longWgt]
                   ;

    Departures from CAPRI: the port computes the weight once, CAPRI writes it twice; the domain condition and the loops in the caller 
    (eu_supports.eu_supports)."""
    wt = ((min(2050, year) - phase_in) / (2050 - phase_in)) ** long_exp * long_wgt
    return longrun * wt + dgagri1 * (1 - wt)


def P_Result_Longrun1_DOMM(longrun1_domm, dgagri1, dgagri1_domm):
    r"""P_Result(MS, DOMM, ., ExAnte, "Longrun1") of the domestic use components without one: DOMM's Longrun1 split as
    DGAgri1.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 291-298):

                   P_Result(MS,DOMM,S_RowsEst,ExAnte,"Longrun1") $ (     (ORDT(ExAnte) GT ORDT("%phaseInYr%"))
                                                                   $ P_Result(MS,"DOMM",S_RowsEst,ExAnte,"Longrun1")
                                                                   $ P_Result(MS,"DOMM",S_RowsEst,ExAnte,"DGAgri1")
                                                                   $ P_Result(MS,DOMM,S_RowsEst,ExAnte,"DGAgri1")
                                                                   $ (not P_Result(MS,DOMM,S_RowsEst,ExAnte,"Longrun1")))
                      = P_Result(MS,"DOMM",S_RowsEst,ExAnte,"Longrun1")
                      * P_Result(MS,DOMM,S_RowsEst,ExAnte,"DGAgri1")
                      / P_Result(MS,"DOMM",S_RowsEst,ExAnte,"DGAgri1");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return longrun1_domm * dgagri1 / dgagri1_domm


def P_Result_Longrun1_group(members):
    r"""P_Result(MS, "CERE" / "OILS", "LEVL" / ., ExAnte, "Longrun1") beyond %lst_dgagri%: the group's crops' (rows')
    Longrun1 summed.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 303-305):

                   P_Result(MS,GRPC,"LEVL",ExAnte,"Longrun1") $ (     (ORDT(ExAnte) GT ORDT("%lst_dgagri%"))
                                                                 and (SAMEAS(GRPC,"CERE") or  SAMEAS(GRPC,"OILS")))
                      = SUM(CROPC_TO_G(cact,GRPC), P_Result(MS,cact,"LEVL",ExAnte,"Longrun1"));

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 307-309):

                   P_Result(MS,MrkBaleE,GRPR,ExAnte,"Longrun1") $ (     (ORDT(ExAnte) GT ORDT("%lst_dgagri%"))
                                                                 and (SAMEAS(GRPR,"CERE") or  SAMEAS(GRPR,"OILS")))
                      = SUM(ROWS_TO_G(S_RowsEst,GRPR), P_Result(MS,MrkBaleE,S_RowsEst,ExAnte,"Longrun1"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return sum(members)


def P_Result_Longrun1_COMI(step3_before, n, longrun1):
    r"""P_Result(MS, DCOW, "COMI", ExAnte, "Longrun1") beyond %lst_dgagri%: at least the year before's Step3 (if ex
    ante) grown by 0.25% a year over its n years.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 314-318):

                   P_Result(MS,DCOW,"COMI",ExAnte,"Longrun1") $ ( (ORDT(ExAnte) GT ORDT("%lst_dgagri%")) $ P_Result(MS,DCOW,"COMI",ExAnte,"Longrun1"))
                      = max(sum(Before(exAnte,Years) $ (ordt(years) gt OrdT("Lst_exPostT")),P_Result(MS,DCOW,"COMI",years, "Step3")
                                                                                            *(1+.0025)**(ordt(exante)-ordt(years))),
                            P_Result(MS,DCOW,"COMI",ExAnte,"Longrun1"))
                  ;

    Departures from CAPRI: without a year before (or one ex post) the port passes 0 for its Step3, as CAPRI's empty sum; the domain condition
    and the loops in the caller (eu_supports.eu_supports)."""
    return max(step3_before * (1 + 0.0025) ** n, longrun1)


def P_Result_DGAgri1_Longrun1(longrun1):
    r"""P_Result(MS, S_ColsEst, S_RowsEst, ExAnte, "DGAgri1") beyond %phaseInYr% with Longrun1: Longrun1.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 335-341):

                   P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"DGAgri1") $  ( (ORDT(ExAnte) GT ORDT("%phaseInYr%"))
        *                                                                Two options:
        *                                                                1) Copy without condition prevents mixing of Longrun1 and DGAgri1 (possibly set = 0)
        *                                                                2) Copy with condition accepts mixing and avoids loss of (extrapolated) information
        *                                                                   Case 2 triggers a lower trust level in about line 932 below (no factor 1.5)
                                                                         $ P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"Longrun1"))
                      = P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"Longrun1");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return longrun1


def P_Result_UAAR_DGAgri1(base, dgagri1, n):
    r"""P_Result(Rest, "UAAR", "LEVL", ExAnte, "DGAgri1"): within [base x 0.998^n, base], base BAST (else BASM),
    n = OrdT(Exante) - OrdT("BAST").

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 355-364):

            P_Result(Rest,"UAAR","LEVL",ExAnte,"DGAgri1")
              $ (    (  P_DATA(REST,"UAAR","LEVL","BAST")
                      + P_DATA(REST,"UAAR","LEVL","BASM") $ (NOT P_DATA(REST,"UAAR","LEVL","BAST") ))
                 and P_Result(Rest,"UAAR","LEVL",ExAnte,"DGAgri1"))
              = MAX(MIN(  P_DATA(REST,"UAAR","LEVL","BAST")
                        + P_DATA(REST,"UAAR","LEVL","BASM") $ (NOT P_DATA(REST,"UAAR","LEVL","BAST") ),
                          P_Result(Rest,"UAAR","LEVL",ExAnte,"DGAgri1")),
                    (   P_DATA(REST,"UAAR","LEVL","BAST")
                      + P_DATA(REST,"UAAR","LEVL","BASM") $ (NOT P_DATA(REST,"UAAR","LEVL","BAST") ))
                    * (0.998**(OrdT(Exante)-OrdT("BAST")-OrdT("BAS") $ (NOT OrdT("BAST"))) ));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return max(min(base, dgagri1), base * 0.998 ** n)


def P_Result_rmAggSup_DGAgri1(value, members):
    r"""P_Result(rmAggSup, ., ., ExAnte, "DGAgri1"): plus the DGAgri1 of its members with their own DGAgri (for
    display).

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 368-371):

            P_Result(rmAggSup,MrkBalee,S_RowsEst,ExAnte,"DGAgri1")
             = P_Result(rmAggSup,MrkBalee,S_RowsEst,ExAnte,"DGAgri1")
               + sum(MS_TO_RMSAGG(MS,rmAggSup) $(P_Result(MS,MrkBalee,S_RowsEst,ExAnte,"DGAgri")),
                 P_Result(MS,MrkBalee,S_RowsEst,ExAnte,"DGAgri1")) ;

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 373-376):

            P_Result(rmAggSup,S_ColsEst,"LEVL",ExAnte,"DGAgri1")
              = P_Result(rmAggSup,S_ColsEst,"LEVL",ExAnte,"DGAgri1")
                + sum(MS_TO_RMSAGG(MS,rmAggSup) $(P_Result(MS,S_ColsEst,"LEVL",ExAnte,"DGAgri")),
                  P_Result(MS,S_ColsEst,"LEVL",ExAnte,"DGAgri1")) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return value + sum(members)


def P_Result_Support_DGAgri1(dgagri1):
    r"""P_Result(MS, ., ., ExAnte, "Support") without an expert: DGAgri1 (market balances but NTRD, PRCI, LEVL, HERD,
    prices, TOOU, yields).

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 400-403):

            P_Result(MS,MrkBalee,S_RowsEst,ExAnte,"Support")
              $ (    (NOT (P_Result(MS,MrkBalee,S_RowsEst,ExAnte,"Expert") or SAMEAS(MrkBalee,"NTRD")))
                 and P_Result(MS,MrkBalee,S_RowsEst,Exante,"DGAgri1"))
              =  P_Result(MS,MrkBalee,S_RowsEst,Exante,"DGAgri1") ;

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 406-409):

            P_Result(MS,"PRCI",S_RowsEst,ExAnte,"Support")
              $ (    (NOT P_Result(MS,"PRCI",S_RowsEst,ExAnte,"Expert"))
                 and P_Result(MS,"PRCI",S_RowsEst,Exante,"DGAgri1"))
              =  P_Result(MS,"PRCI",S_RowsEst,Exante,"DGAgri1") ;

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 473-476):

            P_Result(MS,S_ColsEst,"LEVL",ExAnte,"Support")
              $ (    (NOT (P_Result(MS,S_ColsEst,"LEVL",ExAnte,"Expert")))
                 and P_Result(MS,S_ColsEst,"LEVL",Exante,"DGAgri1"))
              =  P_Result(MS,S_ColsEst,"LEVL",Exante,"DGAgri1") ;

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 478-481):

            P_Result(MS,S_ColsEst,"HERD",ExAnte,"Support")
              $ (    (NOT (P_Result(MS,S_ColsEst,"HERD",ExAnte,"Expert")))
                 and P_Result(MS,S_ColsEst,"HERD",Exante,"DGAgri1"))
              =  P_Result(MS,S_ColsEst,"HERD",Exante,"DGAgri1") ;

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 485-487):

            P_Result(MS,PRIC,S_RowsEst,exAnte,"Support") $ (    P_Result(MS,PRIC,S_RowsEst,exAnte,"DgAgri1")
                                                            and (NOT P_Result(MS,PRIC,S_RowsEst,ExAnte,"Expert")))
              = P_Result(MS,PRIC,S_RowsEst,exAnte,"DgAgri1");

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 491-493):

            P_Result(MS,S_ColsEst,"TOOU",exAnte,"Support") $ (    P_Result(MS,S_ColsEst,"TOOU",exAnte,"DgAgri1")
                                                              and (NOT P_Result(MS,S_ColsEst,"TOOU",ExAnte,"Expert")))
              = P_Result(MS,S_ColsEst,"TOOU",exAnte,"DgAgri1");

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 497-500):

            P_Result(MS,S_ColsEst,S_RowsEst,exAnte,"Support") $ (     P_Result(MS,S_ColsEst,S_RowsEst,exAnte,"DgAgri1")
                                                                 and (NOT P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"Expert"))
                                                                 AND PACT_TO_Y(S_ColsEst,S_RowsEst))
              = P_Result(MS,S_ColsEst,S_RowsEst,exAnte,"DgAgri1");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return dgagri1


def P_Result_EAAG_Support():
    r"""P_Result(MS, "EAAG", ., exAnte, "Support") with DG AGRI's price and production, or with an expert price and a
    quota: removed.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 505-508):

            P_Result(MS,"EAAG",S_RowsEst,exAnte,"Support") $ (    P_Result(MS,"UVAG",S_RowsEst,exAnte,"DgAgri1")
                                                              AND P_Result(MS,"GROF",S_RowsEst,exAnte,"DgAgri1")
                                                              and (NOT P_Result(MS,"EAAG",S_RowsEst,ExAnte,"Expert")))
             = 0;

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 613-617):

            P_Result(MS,"EAAG",S_RowsEst,exAnte,"Support") $ (    P_Result(MS,"UVAG",S_RowsEst,exAnte,"Expert")
                                                              AND (   sum(PRCD(SECOD,S_RowsEst) $ S_RowsEst(SECOD),
                                                                          P_RESULT(MS,"QUTS",SECOD,exAnte,"p_data"))
                                                                   OR P_RESULT(MS,"QUTS",S_RowsEst,exAnte,"p_data")))
            = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return 0.0


def P_Result_NTRD_Support(grof, mapr, domm, dompos, domm_dgagri1, dompos_external):
    r"""P_Result(MS, "NTRD", ., ExAnte, "Support"): production (GROF, else MAPR) less DOMM where DOMM has DGAgri1 but no
    component an external one, else less the components' supports.

    dompos: the DOMPOS' supports; dompos_external: their (DGAgri1, Expert), in the caller's order.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 518-536):

            P_Result(MS,"NTRD",S_RowsEst,ExAnte,"Support")
        *            -- Kicks out COMI, for example:
              $ (    (P_Result(MS,"IMPT",S_RowsEst,ExAnte,"Support") or P_Result(MS,"EXPT",S_RowsEst,ExAnte,"Support"))
                 and (P_Result(MS,"GROF",S_RowsEst,ExAnte,"Support") or P_Result(MS,"MAPR",S_RowsEst,ExAnte,"Support")))
            =  P_Result(MS,"GROF",S_RowsEst,ExAnte,"Support")
             + P_Result(MS,"MAPR",S_RowsEst,ExAnte,"Support") $ (NOT P_Result(MS,"GROF",S_RowsEst,ExAnte,"Support"))
             - P_Result(MS,"DOMM",S_RowsEst,ExAnte,"Support")
        *            -- If there are DGAgri supports for total demand but no DGAgri (or Expert) info
        *               for DOMPOS define NTRD as Prd-DOMM. Otherwise the default trend supports
        *               for DOMPOS may dominate the DGAgri info on DOMM indirectly via the support for NTRD
                     $ (     P_Result(MS,"DOMM",S_RowsEst,ExAnte,"DGAgri1")
                        and  (NOT SUM(DOMPOS,   P_Result(MS,DOMPOS,S_RowsEst,ExAnte,"DGagri1")
                                              + P_Result(MS,DOMPOS,S_RowsEst,ExAnte,"Expert")  )))
             - SUM(DOMPOS, P_Result(MS,DOMPOS,S_RowsEst,ExAnte,"Support"))
        *            -- If there are no DGAgri supports for total demand or if there is more precise info
        *               use the DOMPOS assigned above or already assigned in define_stats_and_supports
                     $ (     (NOT  P_Result(MS,"DOMM",S_RowsEst,ExAnte,"DGAgri1"))
                        or   SUM(DOMPOS,   P_Result(MS,DOMPOS,S_RowsEst,ExAnte,"DGagri1")
                                         + P_Result(MS,DOMPOS,S_RowsEst,ExAnte,"Expert")   ));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    ext_dom = sum(d + e for d, e in dompos_external)
    v = grof + (mapr if not grof else 0.0)
    if domm_dgagri1 and not ext_dom:
        v -= domm
    if (not domm_dgagri1) or ext_dom:
        v -= sum(dompos)
    return v


def P_Result_NTRD_DDGS_Support(ntrd, aggregates_ntrd, fpro, aggregates_fpro):
    r"""P_Result(MS, "NTRD", "DDGS", ExAnte, "Support"): Step2's less 90% of its aggregates' net exports, spread by its
    share of their GROF.FPRO.

    aggregates_ntrd: the aggregates' NTRD.DDGS Step2; aggregates_fpro: their GROF.FPRO Step2 summed.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 545-551):

            P_Result(MS,"NTRD","DDGS",ExAnte,"Support")
              $ SUM(MS_TO_RMSAGG(MS,rmAggSup), P_Result(rmAggSup,"GROF","FPRO",ExAnte,"Step2"))
            =  P_Result(MS,"NTRD","DDGS",ExAnte,"Step2")
        *        Reduce aggregated Step2 net exports of DDGS by 90%, as most of DDGS will end up in EU rather than in rest of the world
            -  0.9 * SUM(MS_TO_RMSAGG(MS,rmAggSup), P_Result(rmAggSup,"NTRD","DDGS",ExAnte,"Step2"))
        *        Shares of FPRO consumption are indicative of capacity to digest DDGS
                   * P_Result(MS,"GROF","FPRO",ExAnte,"Step2") / SUM(MS_TO_RMSAGG(MS,rmAggSup), P_Result(rmAggSup,"GROF","FPRO",ExAnte,"Step2"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return ntrd - 0.9 * sum(aggregates_ntrd) * fpro / aggregates_fpro


def P_Result_FEDM_DDGS_Support(fedm1, ntrd, ntrd1):
    r"""P_Result(MS, "FEDM", "DDGS", ExAnte, "Support"): Support1's less the NTRD correction, at least 0.1.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 553-555):

            P_Result(MS,"FEDM","DDGS",ExAnte,"Support") $ P_Result(MS,"FEDM","DDGS",ExAnte,"Support1")
              = P_Result(MS,"FEDM","DDGS",ExAnte,"Support1")
              - MIN(P_Result(MS,"FEDM","DDGS",ExAnte,"Support1")-.1,(P_Result(MS,"NTRD","DDGS",ExAnte,"Support")-P_Result(MS,"NTRD","DDGS",ExAnte,"Support1")));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return fedm1 - min(fedm1 - .1, ntrd - ntrd1)


def P_Result_DOMM_DDGS_Support(fedm):
    r"""P_Result(MS, "DOMM", "DDGS", ExAnte, "Support"): FEDM's.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 557-558):

            P_Result(MS,"DOMM","DDGS",ExAnte,"Support") $ P_Result(MS,"FEDM","DDGS",ExAnte,"Support")
              = P_Result(MS,"FEDM","DDGS",ExAnte,"Support");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return fedm


def P_Result_trade_series(value):
    r"""P_Result(MS, "IMPT" / "EXPT", S_RowsEst, ExAnte, "series"): the supports before the correction.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 565-565):

            P_Result(MS,"IMPT",S_RowsEst,ExAnte,"series") = P_Result(MS,"IMPT",S_RowsEst,ExAnte,"Support");

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 566-566):

            P_Result(MS,"EXPT",S_RowsEst,ExAnte,"series") = P_Result(MS,"EXPT",S_RowsEst,ExAnte,"Support");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return value


def P_Result_NTRD_series(expt, impt):
    r"""P_Result(MS, "NTRD", S_RowsEst, ExAnte, "series"): the old implied NTRD, EXPT - IMPT.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 567-569):

            P_Result(MS,"NTRD",S_RowsEst,ExAnte,"series")
              $ (P_Result(MS,"IMPT",S_RowsEst,ExAnte,"series") or P_Result(MS,"EXPT",S_RowsEst,ExAnte,"series"))
              = (P_Result(MS,"EXPT",S_RowsEst,ExAnte,"series")-P_Result(MS,"IMPT",S_RowsEst,ExAnte,"series") );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return expt - impt


def P_Result_IMPT_Support(impt, expt, ntrd, ntrd_series):
    r"""P_Result(MS, "IMPT", S_RowsEst, ExAnte, "Support"): the NTRD change relative to gross trade subtracted from the
    old import support.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 572-577):

            P_Result(MS,"IMPT",S_RowsEst,ExAnte,"Support") $ ((   P_Result(MS,"EXPT",S_RowsEst,ExAnte,"series")
                                                                + P_Result(MS,"IMPT",S_RowsEst,ExAnte,"series")) GT 1.E-6)
             = P_Result(MS,"IMPT",S_RowsEst,ExAnte,"series")
        *           -- Change relative to total gross trade is substracted from old import support
             * (1. -(P_Result(MS,"NTRD",S_RowsEst,ExAnte,"Support") - P_Result(MS,"NTRD",S_RowsEst,ExAnte,"series") )
                   /(P_Result(MS,"EXPT",S_RowsEst,ExAnte,"series") + P_Result(MS,"IMPT",S_RowsEst,ExAnte,"series") ) );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return impt * (1. - (ntrd - ntrd_series) / (expt + impt))


def P_Result_EXPT_Support(impt, expt, ntrd, ntrd_series):
    r"""P_Result(MS, "EXPT", S_RowsEst, ExAnte, "Support"): the NTRD change relative to gross trade added to the old
    export support.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 580-585):

            P_Result(MS,"EXPT",S_RowsEst,ExAnte,"Support") $ ((   P_Result(MS,"EXPT",S_RowsEst,ExAnte,"series")
                                                                + P_Result(MS,"IMPT",S_RowsEst,ExAnte,"series")) GT 1.E-6)
             = P_Result(MS,"EXPT",S_RowsEst,ExAnte,"series")
        *        -- Change relative to total gross trade is added to old export support
             * (1. +(P_Result(MS,"NTRD",S_RowsEst,ExAnte,"Support") - P_Result(MS,"NTRD",S_RowsEst,ExAnte,"series") )
                   /(P_Result(MS,"EXPT",S_RowsEst,ExAnte,"series") + P_Result(MS,"IMPT",S_RowsEst,ExAnte,"series") ) );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return expt * (1. + (ntrd - ntrd_series) / (expt + impt))


def P_Result_trade_series_reset():
    r"""P_Result(MS, "IMPT" / "EXPT", S_RowsEst, ExAnte, "series"): emptied before the estimates.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 587-588):

            P_Result(MS,"IMPT",S_RowsEst,ExAnte,"series") = 0;
            P_Result(MS,"EXPT",S_RowsEst,ExAnte,"series") = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return 0.0


def P_Result_IMPT_series(impt_basm, impt, expt):
    r"""P_Result(MS, "IMPT", S_RowsEst, ExAnte, "series") with an old NTRD: at least 1E-6 BASM, increased by any
    negative exports.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 591-593):

            P_Result(MS,"IMPT",S_RowsEst,ExAnte,"series") $  P_Result(MS,"NTRD",S_RowsEst,ExAnte,"series")
             = MAX(1.E-6*P_Result(MS,"IMPT",S_RowsEst,ExAnte,"BASM"),P_Result(MS,"IMPT",S_RowsEst,ExAnte,"Support"))
             + MAX(0.,-P_Result(MS,"EXPT",S_RowsEst,ExAnte,"Support"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return max(1.E-6 * impt_basm, impt) + max(0., -expt)


def P_Result_EXPT_series(expt_basm, expt, impt):
    r"""P_Result(MS, "EXPT", S_RowsEst, ExAnte, "series") with an old NTRD: at least 1E-6 BASM, increased by any
    negative imports.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 596-598):

            P_Result(MS,"EXPT",S_RowsEst,ExAnte,"series") $  P_Result(MS,"NTRD",S_RowsEst,ExAnte,"series")
             = MAX(1.E-6*P_Result(MS,"EXPT",S_RowsEst,ExAnte,"BASM"),P_Result(MS,"EXPT",S_RowsEst,ExAnte,"Support"))
             + MAX(0.,-P_Result(MS,"IMPT",S_RowsEst,ExAnte,"Support"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return max(1.E-6 * expt_basm, expt) + max(0., -impt)


def P_Result_trade_Support(series):
    r"""P_Result(MS, "IMPT" / "EXPT", S_RowsEst, ExAnte, "Support"): the estimates.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 600-601):

            P_Result(MS,"IMPT",S_RowsEst,ExAnte,"Support") =  P_Result(MS,"IMPT",S_RowsEst,ExAnte,"series");
            P_Result(MS,"EXPT",S_RowsEst,ExAnte,"Support") =  P_Result(MS,"EXPT",S_RowsEst,ExAnte,"series");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return series


def P_Result_tradeEst_SUGB(expert):
    r"""P_Result(MS, tradeEst, "SUGB", ExAnte, "support"): the sugar beet trade's expert support.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 608-608):

            P_Result(MS,tradeEst,"SUGB",ExAnte,"support") = P_Result(MS,tradeEst,"SUGB",ExAnte,"expert") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return expert


def P_Result_MCACT_LEVL_Support(levl, uaar, total):
    r"""P_Result(MS, MCACT, "LEVL", ExAnte, "Support"): the crop areas scaled to close 67% of their gap to UAAR.

    total: the areas' supports summed.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 624-629):

            P_Result(MS,S_ColsEst,"LEVL",ExAnte,"Support") $ (    SUM(SAMEAS(MCACT,S_ColsEst),
                                                                       P_Result(MS,MCACT,"LEVL",ExAnte,"Support"))
                                                              and P_Result(MS,"UAAR","LEVL",ExAnte,"Support"))
              =  P_Result(MS,S_ColsEst,"LEVL",Exante,"Support")
              *  (0.67*P_Result(MS,"UAAR","LEVL",ExAnte,"Support")+0.33*SUM(MCACT, P_Result(MS,MCACT,"LEVL",ExAnte,"Support")))
              / SUM(MCACT, P_Result(MS,MCACT,"LEVL",ExAnte,"Support"));

    Departures from CAPRI: the port writes 1 - 0.67 for CAPRI's 0.33 (the last digit may differ); the domain condition and the loops in the
    caller (eu_supports.eu_supports)."""
    return levl * (0.67 * uaar + (1 - 0.67) * total) / total


def P_Result_GROF_young(levl1, yield1, levl2, yield2):
    r"""P_Result(MS, "GROF", "IPIG" / "ICHI" / "ILAM", ExAnte, "Support") without an external one: the young animals of
    the breeding and fattening activities (SOWS and PIGF, HENS and POUF, SHGM and SHGF) in 1000 heads.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 641-646):

            P_Result(MS,"GROF","IPIG",ExAnte,"Support")
              $ (    (SUM(External, P_Result(MS,"GROF","IPIG",ExAnte,External)) EQ 0.)
                 and (     SUM(External, P_Result(MS,"SOWS","LEVL",ExAnte,External))
                      or   SUM(External, P_Result(MS,"PIGF","LEVL",ExAnte,External))) )
              = (P_Result(MS,"SOWS","LEVL",ExAnte,"Support")*P_Result(MS,"SOWS","IPIG",ExAnte,"Support")
              +  P_Result(MS,"PIGF","LEVL",ExAnte,"Support")*P_Result(MS,"PIGF","IPIG",ExAnte,"Support"))/1000.;

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 657-662):

            P_Result(MS,"GROF","ICHI",ExAnte,"Support")
              $ (    (SUM(External, P_Result(MS,"GROF","ICHI",ExAnte,External)) EQ 0.)
                 and (     SUM(External, P_Result(MS,"HENS","LEVL",ExAnte,External))
                      or   SUM(External, P_Result(MS,"POUF","LEVL",ExAnte,External))) )
              = (P_Result(MS,"HENS","LEVL",ExAnte,"Support")*P_Result(MS,"HENS","ICHI",ExAnte,"Support")
              +  P_Result(MS,"POUF","LEVL",ExAnte,"Support")*P_Result(MS,"POUF","ICHI",ExAnte,"Support"))/1000.;

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 673-678):

            P_Result(MS,"GROF","ILAM",ExAnte,"Support")
              $ (    (SUM(External, P_Result(MS,"GROF","ILAM",ExAnte,External)) EQ 0.)
                 and (     SUM(External, P_Result(MS,"SHGM","LEVL",ExAnte,External))
                      or   SUM(External, P_Result(MS,"SHGF","LEVL",ExAnte,External))) )
              = (P_Result(MS,"SHGM","LEVL",ExAnte,"Support")*P_Result(MS,"SHGM","ILAM",ExAnte,"Support")
              +  P_Result(MS,"SHGF","LEVL",ExAnte,"Support")*P_Result(MS,"SHGF","ILAM",ExAnte,"Support"))/1000.;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return (levl1 * yield1 + levl2 * yield2) / 1000.


def P_Result_GROF_young_Y(young):
    r"""P_Result(MS, "GROF", "YPIG" / "YCHI" / "YLAM", ExAnte, "Support") without an external one: the IPIG / ICHI /
    ILAM support.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 648-652):

            P_Result(MS,"GROF","YPIG",ExAnte,"Support")
              $ (    (SUM(External, P_Result(MS,"GROF","YPIG",ExAnte,External)) EQ 0.)
                 and (     SUM(External, P_Result(MS,"SOWS","LEVL",ExAnte,External))
                      or   SUM(External, P_Result(MS,"PIGF","LEVL",ExAnte,External))) )
              = P_Result(MS,"GROF","IPIG",ExAnte,"Support");

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 664-668):

            P_Result(MS,"GROF","YCHI",ExAnte,"Support")
              $ (    (SUM(External, P_Result(MS,"GROF","YCHI",ExAnte,External)) EQ 0.)
                 and (     SUM(External, P_Result(MS,"HENS","LEVL",ExAnte,External))
                      or   SUM(External, P_Result(MS,"POUF","LEVL",ExAnte,External))) )
              = P_Result(MS,"GROF","ICHI",ExAnte,"Support");

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 680-684):

            P_Result(MS,"GROF","YLAM",ExAnte,"Support")
              $ (    (SUM(External, P_Result(MS,"GROF","YLAM",ExAnte,External)) EQ 0.)
                 and (     SUM(External, P_Result(MS,"SHGM","LEVL",ExAnte,External))
                      or   SUM(External, P_Result(MS,"SHGF","LEVL",ExAnte,External))) )
              = P_Result(MS,"GROF","ILAM",ExAnte,"Support");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return young


def p_result_MrkBalee_nonneg(support):
    r"""p_result(MS, MrkBalee, s_rowsEst, exante, "Support") but NTRD: not below zero.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 710-711):

            p_result(MS,MrkBalee,s_rowsEst,exante,"Support") $ (NOT SAMEAS(MrkBaleE,"NTRD"))
              = max(0,p_result(MS,MrkBalee,s_rowsEst,exante,"Support"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return max(0., support)


def P_Result_TrustLevl_DGAgri(position, meat, sgmi):
    r"""P_Result(MS, ., ., ExAnte, "TrustLevl") of a support from the member's own DG AGRI outlook: 5, +1 for GROF,
    MAPR, DOMM and HCOM, +2 for the meats, -2 for SGMI.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 719-731):

            P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"TrustLevl") $ (     P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"DGAgri")
                                                                 and  (   P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"DGAgri1")
                                                                       EQ P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"Support")))
                                     = 5
                                     + 1  $ (SAMEAS(S_ColsEst,"GROF") OR SAMEAS(S_ColsEst,"MAPR") OR SAMEAS(S_ColsEst,"DOMM")
        *                                   also for HCOM after deletion of competing support for INHA (about line 538) has been removed
                                             or SAMEAS(S_ColsEst,"HCOM") )
        *                            For meats often no supplementing LEVL information from DGAgri:
                                     + 2 $ R_T_OAGG("MEAS",S_RowsEst)
        *                            SGMI is usually far less important than SGMT and should not dominate the results
                                     - 2 $ (SAMEAS(s_rowsest,"sgmi") )
        $ifi %aglinkTightLink%==on   + 2
                                     ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return 5. + 1. * position + 2. * meat - 2. * sgmi


def P_Result_TrustLevl_rmAggSup(position, sgmi):
    r"""P_Result(MS, ., ., ExAnte, "TrustLevl") of a support from the aggregate's outlook only: 3, +1 for GROF, MAPR
    and DOMM, -2 for SGMI.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 735-749):

            P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"TrustLevl") $  (    (NOT P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"DGAgri"))
                                                                    and P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"DGAgri1")
        *                                                           avoids modification of expert trustlevels
        *                                                           which might be identical to DG Agri by chance (UAAR.LEVL):
                                                                    and (NOT P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"Expert"))
                                                                    and (   P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"DGAgri1")
                                                                         EQ P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"Support")))
                                     = 3
                                     + 1  $ (SAMEAS(S_ColsEst,"GROF") OR SAMEAS(S_ColsEst,"MAPR") OR SAMEAS(S_ColsEst,"DOMM"))
        *pw210419 Deactivate emphasis on meats as they interfere with calory targets:
        *                             + 2 $ R_T_OAGG("MEAS",S_RowsEst)
        *                            SGMI is usually far less important than SGMT and should not dominate the results
                                     - 2 $ (SAMEAS(s_rowsest,"sgmi") )
        $ifi %aglinkTightLink%==on   + 3
                                     ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return 3. + 1. * position - 2. * sgmi


def P_Result_TrustLevl_trade():
    r"""P_Result(MS, ., ., ExAnte, "TrustLevl") of IMPT, EXPT, NTRD and the levels with DGAgri1, without an expert.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 752-761):

            P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"TrustLevl") $ (   P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"DGAgri1")
                                                                   $  (NOT P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"Expert"))
                                                                   $  (   sameas(S_ColsEst,"IMPT") or sameas(S_ColsEst,"EXPT")
                                                                       or sameas(S_ColsEst,"NTRD") or sameas(S_RowsEst,"LEVL") )
                                                                   )
                                     = 5
        $ifi %aglinkTightLink%==on   + 2
        *                                    To account for DGAgri1 LEVL/HERD that was only inferred from Grof:
        $ifi %aglinkTightLink%==on   - 5 $  ((NOT PACT_TO_IO(S_ColsEst,"ICOW")) $ PACT_TO_IO(S_ColsEst,"FCER") )
                                     ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return 5.


def P_Result_TrustLevl_groups():
    r"""P_Result(MS, "CERE" / "OILS", "LEVL", ExAnte, "TrustLevl") with DGAgri1, without an expert.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 767-770):

            P_Result(MS,S_ColsEst,"LEVL",ExAnte,"TrustLevl") $  (     P_Result(MS,S_ColsEst,"LEVL",ExAnte,"DGAgri1")
                                                                    $ (NOT P_Result(MS,S_ColsEst,"LEVL",ExAnte,"Expert"))
                                                                    $ (sameas(S_ColsEst,"CERE") or sameas(S_ColsEst,"OILS") ))
                = 1;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return 1.


def P_Result_TrustLevl_MAACT(extrap, herd_from_levl, no_icow):
    r"""P_Result(MS, MAACT, "LEVL", ExAnte, "TrustLevl") of a support from DGAgri1: 5, less 3 (+1.5 where HERD is the
    level) where extrapolated, less 2 for the activities not using young cows.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 774-785):

            P_Result(MS,MAACT,"LEVL",ExAnte,"TrustLevl") $  (     P_Result(MS,MAACT,"LEVL",ExAnte,"DGAgri1")
                                                                    and (   P_Result(MS,MAACT,"LEVL",ExAnte,"DGAgri1")
                                                                         EQ P_Result(MS,MAACT,"LEVL",ExAnte,"Support")))

                                     = 5 -( 3
        *                    Avoid double counting of extrapolated information that was copied from LEVL to HERD above
                      +1.5 $ (P_Result(MS,MAACT,"HERD",ExAnte,"DGAgri1") EQ P_Result(MS,MAACT,"LEVL",ExAnte,"DGAgri1")))
                    $ (P_Result(MS,MAACT,"LEVL",ExAnte,"DGAgri1") EQ P_Result(MS,MAACT,"LEVL",ExAnte,"Extrap"))
        $ifi %aglinkTightLink%==on   + 2
        *                                    To account for DGAgri1 LEVL/HERD that was only inferred from Grof:
                                     - 2 $  (NOT PACT_TO_IO(MAACT,"ICOW"))
                    ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return 5. - (3. + 1.5 * herd_from_levl) * extrap - 2. * no_icow


def P_Result_TrustLevl_quota(trust):
    r"""P_Result(MS, "EXPE" / "GROF", ., exAnte, "TrustLevl") with an expert price and a quota, or with a quota on a
    product (from 2006): a fifth.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 791-793):

            P_Result(MS,"EXPE",S_RowsEst,exAnte,"TrustLevl") $ (    P_Result(MS,"UVAG",S_RowsEst,exAnte,"Expert")
                                                                AND P_result(MS,"QUTS",S_RowsEst,exAnte,"p_data"))
            = P_Result(MS,"EXPE",S_RowsEst,exAnte,"TrustLevl") / 5.;

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 809-816):

            P_Result(MS,"GROF",S_RowsEst,ExAnte,"TrustLevl") $ ( SUM(PRCD(SECOD,S_RowsEst) $ S_RowsEst(SECOD),
                                                                         P_RESULT(MS,"QUTS",SECOD,exAnte,"p_data"))
        *                                                       Probably this should only apply to DG Agri supports:
                                                                and  (    P_Result(MS,"GROF",S_RowsEst,ExAnte,"DGAgri1")
                                                                      EQ  P_Result(MS,"GROF",S_RowsEst,ExAnte,"Support"))
                                                                and  P_Result(MS,"GROF",S_RowsEst,ExAnte,"DGAgri1")
                                                                AND (calyea(exAnte) ge calyea("2006")) )
            = P_Result(MS,"GROF",S_RowsEst,ExAnte,"TrustLevl") / 5.;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return trust / 5.


def P_Result_TrustLevl_yield(comi):
    r"""P_Result(MS, ., ., exAnte, "TrustLevl") of a yield (PACT_TO_Y) from DGAgri1: 3, the milk yields 3 + 4.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 798-803):

            P_Result(MS,S_ColsEst,S_RowsEst,exAnte,"TrustLevl") $ (    (  P_Result(MS,S_ColsEst,S_RowsEst,exAnte,"DgAgri1")
                                                                       EQ P_Result(MS,S_ColsEst,S_RowsEst,exAnte,"Support"))
                                                                   and P_Result(MS,S_ColsEst,S_RowsEst,exAnte,"Support")
                                                                   and PACT_TO_Y(S_ColsEst,S_RowsEst))
        *              COMI is very stable => extrapolation (stored on "DGagri1" at this point) is quite reliable
                = 3. + 4 $ SAMEAS(S_RowsEst,"COMI");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return 3. + 4. * comi


def P_Result_TrustLevl_Longrun1(trust, year, lst_dgagri):
    r"""P_Result(MS, ., ., ExAnte, "TrustLevl") beyond %lst_dgagri% of a DGAgri1 with Longrun1, without an expert:
    raised by up to 80% by 2050, at most 10.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 829-835):

            P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"TrustLevl") $ (    P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"DGAgri1")
                                                                   $   P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"longrun1")
                                                                   $  (NOT P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"Expert"))
                                                                   $  (OrdT(exAnte) GT OrdT("%lst_dgagri%")))
                                                             = MIN(10.,P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"TrustLevl")
                                                                      *(1 + .8 * ((min(ORDT("2050"),ORDT(ExAnte))-ORDT("%lst_dgagri%"))
                                                                                 /(ORDT("2050")-ORDT("%lst_dgagri%"))))) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return min(10., trust * (1 + .8 * ((min(2050, year) - lst_dgagri) / (2050 - lst_dgagri))))


def P_Result_TrustLevl_UVAG():
    r"""P_Result(MS, "UVAG", ., exAnte, "TrustLevl") of DG AGRI's own price.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 847-850):

            P_Result(MS,"UVAG",S_RowsEst,exAnte,"TrustLevl") $ (    P_Result(MS,"UVAG",S_RowsEst,exAnte,"DgAgri")
                                                               and (   P_Result(MS,"UVAG",S_RowsEst,exAnte,"DgAgri1")
                                                                    EQ P_Result(MS,"UVAG",S_RowsEst,exAnte,"Support")))
                = 3.;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return 3.


def P_Result_TrustLevl_UVAG_agg():
    r"""P_Result(MS, "UVAG", ., exAnte, "TrustLevl") of the aggregate's price.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 853-857):

            P_Result(MS,"UVAG",S_RowsEst,ExAnte,"TrustLevl") $  (   (NOT  P_Result(MS,"UVAG",S_RowsEst,exAnte,"DgAgri"))
                                                                and P_Result(MS,"UVAG",S_RowsEst,exAnte,"DgAgri1")
                                                                and (   P_Result(MS,"UVAG",S_RowsEst,exAnte,"DgAgri1")
                                                                     EQ P_Result(MS,"UVAG",S_RowsEst,exAnte,"Support")))
                = .5;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return .5


def P_Result_TrustLevl_UVAD():
    r"""P_Result(MS, "UVAD", ., exAnte, "TrustLevl") of a support from DGAgri1.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 862-864):

            P_Result(MS,"UVAD",S_RowsEst,exAnte,"TrustLevl") $ (  P_Result(MS,"UVAD",S_RowsEst,exAnte,"DgAgri1")
                                                               EQ P_Result(MS,"UVAD",S_RowsEst,exAnte,"Support"))
                = .3;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return .3


def P_Result_DGAgri_removed():
    r"""P_Result(MS, ., ., ExAnte, "DGAgri" / "DGAgri1") beyond %lst_dgagri%, and DGAgri1 where neither the member nor
    its EU part has DGAgri: removed.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 869-871):

            P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"DGAgri")   $  (    P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"DGAgri1")
                                                                   $  (OrdT(exAnte) GT OrdT("%lst_dgagri%")))
                                                             =  0;

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 873-875):

            P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"DGAgri1") $  (     P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"DGAgri1")
                                                                   $   (OrdT(exAnte) GT OrdT("%lst_dgagri%")))
                                                             = 0;

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 877-881):

            P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"DGAgri1") $  (     P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"DGAgri1")
                                                                   $   (NOT (  P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"DGAgri")
                                                                            or SUM(MS_TO_RMSAGG(MS,EUparts),
                                                                               P_Result(EUparts,S_ColsEst,S_RowsEst,ExAnte,"DGAgri")))))
                                                             = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return 0.0


def P_Result_wVarErr(support, trust):
    r"""P_Result(MS, ., ., exAnte, "wVarErr") without an expert, with a trust level: (max(0.1, |support|) x 0.05 / 3 x
    10 / TrustLevl)^2.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 883-886):

           P_Result(MS,S_ColsEst,S_RowsEst,exAnte,"wVarErr") $ (   (Not P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"Expert"))
                                                               and P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"TrustLevl"))
             = SQR(max(.1,abs(P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"Support")))
                  * 0.05 / 3 * (10/  P_Result(MS,S_ColsEst,S_RowsEst,exAnte,"TrustLevl")));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return (max(0.1, abs(support)) * 0.05 / 3.0 * (10.0 / trust)) ** 2


def P_Result_wVarErr_trade(wvarerr):
    r"""P_Result(MS, "IMPT" / "EXPT", ., ExAnte, "wVarErr") with an NTRD support: the standard deviation x 5.

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 891-892):

            P_Result(MS,"IMPT",S_RowsEst,ExAnte,"wVarErr") $ P_Result(MS,"NTRD",S_RowsEst,ExAnte,"Support")
                = P_Result(MS,"IMPT",S_RowsEst,ExAnte,"wVarErr") * SQR(5);

    CAPRI's GAMS (captrd/define_eu_supports.gms l. 894-895):

            P_Result(MS,"EXPT",S_RowsEst,ExAnte,"wVarErr") $ P_Result(MS,"NTRD",S_RowsEst,ExAnte,"Support")
                = P_Result(MS,"EXPT",S_RowsEst,ExAnte,"wVarErr") * SQR(5);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (eu_supports.eu_supports)."""
    return wvarerr * 5. ** 2


def _sigmoid(x):
    """GAMS's SIGMOID(x) = 1 / (1 + exp(-x))."""
    return 1. / (1. + math.exp(-x))
