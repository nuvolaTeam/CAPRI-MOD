r"""CAPTRD's statements of captrd/national_supports.gms (CAPRI star 3.0, included by expert_support.gms l. 779;
%aglinkTightLink% off, %useAgriInfo% on, %lst_daitar% 2020): the national expert supports, as named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). capri_mod/pipeline/captrd/national_supports.py (supports) holds the loops over
the regions, the positions and the years, the conditions and the order, and calls them; the arithmetic is the port's,
so the supports are unchanged. trust_nat is p_trustNat (l. 205, 7.01).
"""
from __future__ import annotations


def p_ExpertSupprt_PercentChange_dairy(absolute, basm):
    r"""p_ExpertSupprt(runr, expertdairy_map, EXANTET, "PercentChange"): the dairy absolutes' change from BASM in
    percent.

    CAPRI's GAMS (captrd/national_supports.gms l. 31-34):

          p_ExpertSupprt(runr,cols,rows,EXANTET,"PercentChange") $ (  P_Result(runr,cols,rows,ExanteT,"BASM")
                                                                   $ p_ExpertSupprt(runr,cols,rows,EXANTET,"absolute")
                                                                   $ expertdairy_map(cols,rows) )
              = (p_ExpertSupprt(runr,cols,rows,EXANTET,"absolute")/P_Result(runr,cols,rows,ExanteT,"BASM"))*100.-100.;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return absolute / basm * 100. - 100.


def p_ExpertSupprt_MILK_from_MAPR(value):
    r"""p_ExpertSupprt(runr, "PRCM" / "DOMM", "MILK", EXANTET, "PercentChange" / "Trustlevl"): MAPR.MILK's.

    CAPRI's GAMS (captrd/national_supports.gms l. 37-39):

          p_ExpertSupprt(runr,cols,"MILK",EXANTET,"PercentChange") $ ( p_ExpertSupprt(runr,"MAPR","MILK",EXANTET,"PercentChange")
                                                                     $ (sameas(cols,"PRCM") or sameas(cols,"DOMM")))
              = p_ExpertSupprt(runr,"MAPR","MILK",EXANTET,"PercentChange");

    CAPRI's GAMS (captrd/national_supports.gms l. 40-43):

          p_ExpertSupprt(runr,cols,"MILK",exanteT,"Trustlevl") $ ( p_ExpertSupprt(runr,cols,"MILK",EXANTET,"PercentChange")
                                                                 $ (sameas(cols,"PRCM") or sameas(cols,"DOMM"))
                                                                 $ p_ExpertSupprt(runr,"MAPR","MILK",EXANTET,"PercentChange"))
             = p_ExpertSupprt(runr,"MAPR","MILK",exanteT,"Trustlevl");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return value


def p_natExpert_NECP(value):
    r"""p_natExpert(nuts0, xpCols, "LEV1", simyy) of the columns mapped to COLS: NECP's herds (p_fromNECP).

    CAPRI's GAMS (captrd/national_supports.gms l. 150-150):

        p_natExpert(nuts0,xpCols,"LEV1",simyy) $ sum(Expert_to_cols(xpCOLS,COLS),1) = p_fromNECP(NUTS0,xpCols,simyy);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return value


def p_NatExpert_AVGDAT(value):
    r"""p_NatExpert(MS, ., ., years / basYrsM) without one: time_avg.gms's interpolation p_AVGDAT (the needed years but
    BASYRSM; BASYRSM where observations lie before and after BAS and beyond the last ex-post year).

    CAPRI's GAMS (captrd/national_supports.gms l. 168-169):

             p_NatExpert(MS,xpCOLS,xpROWS,years) $ (  (NOT p_NatExpert(MS,xpCOLS,xpROWS,years) ) $ (not basYrsM(years)) $ neededYears(years))
               = p_AVGDAT(MS,xpCOLS,xpROWS,years);

    CAPRI's GAMS (captrd/national_supports.gms l. 171-175):

             p_NatExpert(MS,xpCOLS,xpROWS,basYrsM) $ ( sum(expostT $ (p_NatExpert(MS,xpCOLS,xpROWS,expostT) $ (ordT(expostT) LE ordT("BAS"))),1)
                                                     $ sum(expostT $ (p_NatExpert(MS,xpCOLS,xpROWS,expostT) $ (ordT(expostT) GT ordT("BAS"))),1)
                                                     $ sum(years $ (p_NatExpert(MS,xpCOLS,xpROWS,years) $ (ordT(years) GT ordT("lst_expost"))),1)
                                                     $ (not p_NatExpert(MS,xpCOLS,xpROWS,basYrsM)))
               = p_AVGDAT(MS,xpCOLS,xpROWS,basYrsM);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return value


def p_NatExpert_from_pdata(mapped, nat_both, mapped_both):
    r"""p_NatExpert(MS, ., ., basYrsM) without observations on both sides of BAS: p_data mapped to the series times
    the national source's sum over p_data's over the ex-post years where both have values.

    mapped: p_data of the year mapped (Expert_to_cols, Expert_to_rows); nat_both, mapped_both: the two over those
    years, in order.

    CAPRI's GAMS (captrd/national_supports.gms l. 179-193):

             p_NatExpert(MS,xpCOLS,xpROWS,basYrsM) $ ( (not ( sum(expostT $ (p_NatExpert(MS,xpCOLS,xpROWS,expostT) $ (ordT(expostT) LE ordT("BAS"))),1))
                                                            $ sum(expostT $ (p_NatExpert(MS,xpCOLS,xpROWS,expostT) $ (ordT(expostT) GT ordT("BAS"))),1))
                                                     $ sum(expostT $ ( p_NatExpert(MS,xpCOLS,xpROWS,expostT)
                                                                     $ SUM((Expert_to_cols(xpCOLS,COLS),Expert_to_rows(xpRows,rows)),
                                                                       P_Result(MS,Cols,Rows,expostT,"p_data"))), 1)
                                                     $ sum(years $ (p_NatExpert(MS,xpCOLS,xpROWS,years) $ (ordT(years) GT ordT("lst_expost"))),1)
                                                     $ (not p_NatExpert(MS,xpCOLS,xpROWS,basYrsM)))
              = SUM((Expert_to_cols(xpCOLS,COLS),Expert_to_rows(xpRows,rows)),                P_Result(MS,Cols,Rows,basYrsM,"p_data"))
              * sum(expostT $ ( p_NatExpert(MS,xpCOLS,xpROWS,expostT)
                              $ SUM((Expert_to_cols(xpCOLS,COLS),Expert_to_rows(xpRows,rows)),
                                P_Result(MS,Cols,Rows,expostT,"p_data"))),                    p_NatExpert(MS,xpCOLS,xpROWS,expostT))
              / sum(expostT $ ( p_NatExpert(MS,xpCOLS,xpROWS,expostT)
                              $ SUM((Expert_to_cols(xpCOLS,COLS),Expert_to_rows(xpRows,rows)),
                                P_Result(MS,Cols,Rows,expostT,"p_data"))), SUM((Expert_to_cols(xpCOLS,COLS),Expert_to_rows(xpRows,rows)),
                                                                                              P_Result(MS,Cols,Rows,expostT,"p_data")));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return mapped * sum(nat_both) / sum(mapped_both)


def p_NatExpert_BAS(values):
    r"""p_NatExpert(MSest, ., ., "20%BAS%") where every BASYRSM has a value: their mean.

    CAPRI's GAMS (captrd/national_supports.gms l. 197-198):

          p_NatExpert(MSest,xpCOLS,xpROWS,"20%BAS%") $ (SUM(BASYRSM $ p_NatExpert(MSest,xpCOLS,xpROWS,BASYRSM),1.) EQ CARD(BASYRSM))
              = SUM(BASYRSM, p_NatExpert(MSest,xpCOLS,xpROWS,BASYRSM))/CARD(BASYRSM);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return sum(values) / len(values)


def p_ExpertSupprt_Trustlevl_nat(trust_nat):
    r"""p_ExpertSupprt(MSest, cols, rows, exanteT, "Trustlevl") of the positions with a national source and no expert
    support yet: p_trustNat.

    CAPRI's GAMS (captrd/national_supports.gms l. 209-215):

          p_ExpertSupprt(MSest,cols,rows,exanteT,"Trustlevl")
                                     $ (  sum((Expert_to_cols(xpCOLS,COLS),Expert_to_rows(xpROWS,ROWS)),
                                                                                p_natExpert(MSest,xpCOLS,xpROWS,exanteT)
                                                                              * p_natExpert(MSest,xpCOLS,xpROWS,"20%BAS%"))
                                        $ (NOT(   p_ExpertSupprt(MSest,cols,rows,exanteT,"Absolute")
                                               OR p_ExpertSupprt(MSest,cols,rows,exanteT,"PercentChange"))))
              = p_trustNat;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return trust_nat


def p_ExpertSupprt_Trustlevl_CACT_HERD():
    r"""p_ExpertSupprt(MSest, CACT, "HERD", exanteT, "Trustlevl"): removed (crops have no herds).

    CAPRI's GAMS (captrd/national_supports.gms l. 216-216):

          p_ExpertSupprt(MSest,CACT,"HERD",exanteT,"Trustlevl") =0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return 0.0


def p_ExpertSupprt_PercentChange_nat(sources):
    r"""p_ExpertSupprt(MSest, cols, rows, exanteT, "PercentChange") with p_trustNat: the national sources' change from
    their base mean in percent (a tiny growth where unchanged, so the change is not zero).

    sources: (the year's, the base mean's) of the national sources mapped to the position, in the caller's order.

    CAPRI's GAMS (captrd/national_supports.gms l. 218-228):

          p_ExpertSupprt(MSest,cols,rows,exanteT,"PercentChange")
                                     $ (p_ExpertSupprt(MSest,cols,rows,exanteT,"Trustlevl") EQ p_trustNat)
              = sum((Expert_to_cols(xpCOLS,COLS),Expert_to_rows(xpROWS,ROWS))
                         $ ( p_natExpert(MSest,xpCOLS,xpROWS,"20%BAS%") $ p_natExpert(MSest,xpCOLS,xpROWS,exanteT)),
                    p_natExpert(MSest,xpCOLS,xpROWS,exanteT)
        *            ensure a tiny but nonzero growth if otherwise percentChange would be empty (case of sheep in FI000000)
                    +1.e-6 * p_natExpert(MSest,xpCOLS,xpROWS,"20%BAS%")
                           $ (p_natExpert(MSest,xpCOLS,xpROWS,"20%BAS%") eq p_natExpert(MSest,xpCOLS,xpROWS,exanteT)))
              / sum((Expert_to_cols(xpCOLS,COLS),Expert_to_rows(xpROWS,ROWS))
                         $ ( p_natExpert(MSest,xpCOLS,xpROWS,"20%BAS%") $ p_natExpert(MSest,xpCOLS,xpROWS,exanteT)),
                    p_natExpert(MSest,xpCOLS,xpROWS,"20%BAS%"))*100.-100.;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    num = sum(n + 1.e-6 * b * (b == n) for n, b in sources)
    den = sum(b for n, b in sources)
    return num / den * 100. - 100.


def p_ExpertSupprt_Trustlevl_CACT_yield():
    r"""p_ExpertSupprt(MS, CACT, rows, exanteT, "Trustlevl") of the yields whose GROF has p_trustNat.

    CAPRI's GAMS (captrd/national_supports.gms l. 232-235):

          p_ExpertSupprt(MS,CACT,rows,exanteT,"Trustlevl")
                                    $ (  (p_ExpertSupprt(MS,"GROF",rows,exanteT,"Trustlevl") EQ p_trustNat)
                                       $ PACT_TO_Y(CACT,rows))
              = 3.01;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return 3.01


def p_ExpertSupprt_Absolute_CACT(support):
    r"""p_ExpertSupprt(MS, CACT, rows, exanteT, "Absolute") of those yields: the support.

    CAPRI's GAMS (captrd/national_supports.gms l. 237-239):

          p_ExpertSupprt(MS,CACT,rows,exanteT,"Absolute")
                                    $ (p_ExpertSupprt(MS,CACT,rows,exanteT,"Trustlevl") EQ 3.01)
              = P_Result(MS,CACT,rows,ExanteT,"Support");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return support


def p_ExpertSupprt_Percentchange_lambs(shgm):
    r"""p_ExpertSupprt(MS, "GROF", "YLAM" / "ILAM", ExanteT, "Percentchange") where SHGM.LEVL has p_trustNat: its
    change.

    CAPRI's GAMS (captrd/national_supports.gms l. 244-247):

          p_ExpertSupprt(MS,"GROF",rows,ExanteT,"Percentchange")
                                     $ (  (p_ExpertSupprt(MS,"SHGM","LEVL",exanteT,"Trustlevl") EQ p_trustNat)
                                       $ (SAMEAS(rows,"YLAM") or SAMEAS(rows,"ILAM")))
               = p_ExpertSupprt(MS,"SHGM","LEVL",ExanteT,"Percentchange");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return shgm


def p_ExpertSupprt_TRustlevl_nat_less(trust_nat):
    r"""p_ExpertSupprt(MS, ., ., ExanteT, "TRustlevl"): p_trustNat - 1 for the young lambs, and for the herds and levels
    without disaggregate national data.

    CAPRI's GAMS (captrd/national_supports.gms l. 249-253):

          p_ExpertSupprt(MS,"GROF",rows,ExanteT,"TRustlevl")
                                    $ (   (SAMEAS(rows,"YLAM") or SAMEAS(rows,"ILAM"))
                                       $ (p_ExpertSupprt(MS,"SHGM","LEVL",exanteT,"Trustlevl") EQ p_trustNat)
                                       $ p_ExpertSupprt(MS,"GROF",rows,ExanteT,"Percentchange")   )
               = p_trustNat-1;

    CAPRI's GAMS (captrd/national_supports.gms l. 259-264):

          p_ExpertSupprt(MS,cols,rows,exanteT,"Trustlevl")
                                     $  (  p_ExpertSupprt(MS,cols,rows,exanteT,"PercentChange")
                                         $ (p_ExpertSupprt(MS,cols,rows,exanteT,"Trustlevl") EQ p_trustNat)
                                         $ (not sum(Expert_to_cols(xpDisAgg,COLS),p_NatExpert(MS,xpDisAgg,"LEV1",exanteT)))
                                         $ (SAMEAS(rows,"LEVL") or SAMEAS(rows,"HERD"))  )
              = p_trustNat-1;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return trust_nat - 1


def p_ExpertSupprt_dairy_PercentChange_removed():
    r"""p_ExpertSupprt(NUTS0_and_2, expertdairy_map, exanteT, "PercentChange") with an Absolute (up to 2020; after 2020
    in absDairyRunr): removed.

    CAPRI's GAMS (captrd/national_supports.gms l. 1538-1542):

          p_ExpertSupprt(NUTS0_and_2,S_ColsEst,S_RowsEst,exanteT,"PercentChange")
                  $ ( p_ExpertSupprt(NUTS0_and_2,S_ColsEst,S_RowsEst,exanteT,"Absolute")
                    $ expertdairy_map(S_ColsEst,S_RowsEst)
                    $ (calyea(exanteT) le calyea("2020")))
              = 0;

    CAPRI's GAMS (captrd/national_supports.gms l. 1553-1557):

          p_ExpertSupprt(NUTS0_and_2,S_ColsEst,S_RowsEst,exanteT,"PercentChange")
                  $ ( p_ExpertSupprt(NUTS0_and_2,S_ColsEst,S_RowsEst,exanteT,"Absolute")
                    $ expertdairy_map(S_ColsEst,S_RowsEst) $ absDairyRunr(NUTS0_and_2)
                    $ (calyea(exanteT) gt calyea("2020")))
              = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return 0.0


def p_ExpertSupprt_dairy_Absolute(percent, basm):
    r"""p_ExpertSupprt(NUTS0_and_2, expertdairy_map, exanteT, "Absolute") after 2020 in absDairyRunr: from the
    PercentChange.

    CAPRI's GAMS (captrd/national_supports.gms l. 1545-1550):

          p_ExpertSupprt(NUTS0_and_2,S_ColsEst,S_RowsEst,exanteT,"Absolute")
                  $ ( p_ExpertSupprt(NUTS0_and_2,S_ColsEst,S_RowsEst,exanteT,"PercentChange")
                    $ expertdairy_map(S_ColsEst,S_RowsEst) $ absDairyRunr(NUTS0_and_2)
                    $ (calyea(exanteT) gt calyea("2020")))
              = (100 + p_ExpertSupprt(NUTS0_and_2,S_ColsEst,S_RowsEst,exanteT,"PercentChange"))/100
              * P_Result(NUTS0_and_2,S_ColsEst,S_RowsEst,ExanteT,"BASM");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return (100 + percent) / 100 * basm


def p_ExpertSupprt_dairy_absolute_removed():
    r"""p_ExpertSupprt(runr, expertdairy_map, EXANTET, "absolute") with a PercentChange: removed.

    CAPRI's GAMS (captrd/national_supports.gms l. 1560-1563):

          p_ExpertSupprt(runr,cols,rows,EXANTET,"absolute")
                  $ ( p_ExpertSupprt(runr,cols,rows,EXANTET,"PercentChange")
                    $ expertdairy_map(cols,rows) )
              = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return 0.0


def p_ExpertSupprt_PercentChange_blend(percent, percent_daitar, a, b):
    r"""p_ExpertSupprt(country, ., ., exante, "PercentChange") after %lst_daitar% of the dairy positions: the year's
    change weighted a, %lst_daitar%'s weighted b (AT .5/.5; BL400000's herds .8/.8, the rest 1/0; EL .7/.3; UK .8/.2;
    CY's yields .7/.3; MT .2/.8; SI .6/.4; SK .6/.4, its cows' yields .9/.1; CZ .3/.7).

    CAPRI's GAMS (captrd/national_supports.gms l. 276-282):

          p_ExpertSupprt("AT000000",Cols,rows,exanteT,"PercentChange")
                                     $ ( p_ExpertSupprt("AT000000",Cols,rows,exanteT,"PercentChange")
                                       $ p_ExpertSupprt("AT000000",Cols,rows,"%lst_daitar%","PercentChange")
                                       $ (ORDT(ExanteT) GT ORDT("%lst_daitar%"))
                                       $ expertdairy_map(cols,rows) )
              =    p_ExpertSupprt("AT000000",Cols,rows,exanteT,"PercentChange") *.5
                 + p_ExpertSupprt("AT000000",Cols,rows,"%lst_daitar%","PercentChange") *.5;

    CAPRI's GAMS (captrd/national_supports.gms l. 365-371):

          p_ExpertSupprt("BL400000",Cols,rows,exanteT,"PercentChange")
                                     $ ( p_ExpertSupprt("BL400000",Cols,rows,exanteT,"PercentChange")
                                       $ p_ExpertSupprt("BL400000",Cols,rows,"%lst_daitar%","PercentChange")
                                       $ (ORDT(ExanteT) GT ORDT("%lst_daitar%"))
                                       $ expertdairy_map(cols,rows) )
              =    p_ExpertSupprt("BL400000",Cols,rows,exanteT,"PercentChange")         *(1 - .2 $ herdLevl(rows))
                 + p_ExpertSupprt("BL400000",Cols,rows,"%lst_daitar%","PercentChange") *(0 + .8 $ herdLevl(rows));

    CAPRI's GAMS (captrd/national_supports.gms l. 539-545):

          p_ExpertSupprt("EL000000",Cols,rows,exante,"PercentChange")
                                     $ ( p_ExpertSupprt("EL000000",Cols,rows,exante,"PercentChange")
                                       $ p_ExpertSupprt("EL000000",Cols,rows,"%lst_daitar%","PercentChange")
                                       $ (ORDT(ExAnte) GT ORDT("%lst_daitar%"))
                                       $ expertdairy_map(cols,rows) )
              =    p_ExpertSupprt("EL000000",Cols,rows,exante,"PercentChange") *.7
                 + p_ExpertSupprt("EL000000",Cols,rows,"%lst_daitar%","PercentChange") *.3;

    CAPRI's GAMS (captrd/national_supports.gms l. 870-876):

          p_ExpertSupprt("UK000000",Cols,rows,exante,"PercentChange")
                                     $ ( p_ExpertSupprt("UK000000",Cols,rows,exante,"PercentChange")
                                       $ p_ExpertSupprt("UK000000",Cols,rows,"%lst_daitar%","PercentChange")
                                       $ (ORDT(ExAnte) GT ORDT("%lst_daitar%"))
                                       $ expertdairy_map(cols,rows) )
              =    p_ExpertSupprt("UK000000",Cols,rows,exante,"PercentChange") *.8
                 + p_ExpertSupprt("UK000000",Cols,rows,"%lst_daitar%","PercentChange") *.2;

    CAPRI's GAMS (captrd/national_supports.gms l. 923-928):

          p_ExpertSupprt("CY000000",dcow,"comi",exante,"PercentChange")
                                     $ ( p_ExpertSupprt("CY000000",dcow,"comi",exante,"PercentChange")
                                       $ p_ExpertSupprt("CY000000",dcow,"comi","%lst_daitar%","PercentChange")
                                       $ (ORDT(ExAnte) GT ORDT("%lst_daitar%")))
              =    p_ExpertSupprt("CY000000",dcow,"comi",exante,"PercentChange") *.7
                 + p_ExpertSupprt("CY000000",dcow,"comi","%lst_daitar%","PercentChange") *.3;

    CAPRI's GAMS (captrd/national_supports.gms l. 1196-1202):

          p_ExpertSupprt("MT000000",Cols,rows,exante,"PercentChange")
                                     $ ( p_ExpertSupprt("MT000000",Cols,rows,exante,"PercentChange")
                                       $ p_ExpertSupprt("MT000000",Cols,rows,"%lst_daitar%","PercentChange")
                                       $ (ORDT(ExAnte) GT ORDT("%lst_daitar%"))
                                       $ expertdairy_map(cols,rows) )
              =    p_ExpertSupprt("MT000000",Cols,rows,exante,"PercentChange") *.2
                 + p_ExpertSupprt("MT000000",Cols,rows,"%lst_daitar%","PercentChange") *.8;

    CAPRI's GAMS (captrd/national_supports.gms l. 1298-1304):

          p_ExpertSupprt("SI000000",Cols,rows,exante,"PercentChange")
                                     $ ( p_ExpertSupprt("SI000000",Cols,rows,exante,"PercentChange")
                                       $ p_ExpertSupprt("SI000000",Cols,rows,"%lst_daitar%","PercentChange")
                                       $ (ORDT(ExAnte) GT ORDT("%lst_daitar%"))
                                       $ expertdairy_map(cols,rows) )
              =    p_ExpertSupprt("SI000000",Cols,rows,exante,"PercentChange") *.6
                 + p_ExpertSupprt("SI000000",Cols,rows,"%lst_daitar%","PercentChange") *.4;

    CAPRI's GAMS (captrd/national_supports.gms l. 1334-1340):

          p_ExpertSupprt("SK000000",Cols,rows,exante,"PercentChange")
                                     $ ( p_ExpertSupprt("SK000000",Cols,rows,exante,"PercentChange")
                                       $ p_ExpertSupprt("SK000000",Cols,rows,"%lst_daitar%","PercentChange")
                                       $ (ORDT(ExAnte) GT ORDT("%lst_daitar%"))
                                       $ expertdairy_map(cols,rows) )
              =    p_ExpertSupprt("SK000000",Cols,rows,exante,"PercentChange") *(.6+.3 $ (P_t_ActAgg(cols,"DCOW") $ sameas(rows,"comi")))
                 + p_ExpertSupprt("SK000000",Cols,rows,"%lst_daitar%","PercentChange") *(.4-.3 $ (P_t_ActAgg(cols,"DCOW") $ sameas(rows,"comi")));

    CAPRI's GAMS (captrd/national_supports.gms l. 1382-1388):

          p_ExpertSupprt("CZ000000",Cols,rows,exante,"PercentChange")
                                     $ ( p_ExpertSupprt("CZ000000",Cols,rows,exante,"PercentChange")
                                       $ p_ExpertSupprt("CZ000000",Cols,rows,"%lst_daitar%","PercentChange")
                                       $ (ORDT(ExAnte) GT ORDT("%lst_daitar%"))
                                       $ expertdairy_map(cols,rows) )
              =    p_ExpertSupprt("CZ000000",Cols,rows,exante,"PercentChange") *.3
                 + p_ExpertSupprt("CZ000000",Cols,rows,"%lst_daitar%","PercentChange") *.7;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return percent * a + percent_daitar * b


def p_ExpertSupprt_Absolute_Support(support):
    r"""p_ExpertSupprt(country, ., ., ., "Absolute"): the support (AT's fattening pigs, BL's and CY's pork, EL's sheep
    milk yield, IT's set-aside, KO's hens, the small ruminants of SI, CZ, NO and TUR, NO's cow yields, TUR's
    poultry).

    CAPRI's GAMS (captrd/national_supports.gms l. 287-290):

          p_ExpertSupprt("AT000000","PIGF",rows,exAnteT,"Absolute")
                                     $ ( P_Result("AT000000","PIGF",rows,ExAnteT,"Support") $ (herdLevl(rows) or sameas(rows,"DAYS"))
                                       $ (calyea(exanteT) gt calyea("2020")))
              = P_Result("AT000000","PIGF",rows,ExAnteT,"Support");

    CAPRI's GAMS (captrd/national_supports.gms l. 330-333):

          p_ExpertSupprt("BL000000","GROF","PORK",exAnteT,"Absolute")
                                     $ ( P_Result("BL000000","GROF","PORK",ExAnteT,"Support")
                                       $ (calyea(exanteT) gt calyea("2020")))
              = P_Result("BL000000","GROF","PORK",ExAnteT,"Support");

    CAPRI's GAMS (captrd/national_supports.gms l. 584-587):

          p_ExpertSupprt("EL000000","SHGM","SGMI",exanteT,"Absolute")
                                     $ ( P_Result("EL000000","SHGM","SGMI",ExanteT,"Support")
                                       $ (ORDT(ExAnteT) GT OrdT("2020")))
              = P_Result("EL000000","SHGM","SGMI",ExanteT,"Support");

    CAPRI's GAMS (captrd/national_supports.gms l. 730-732):

          p_ExpertSupprt("IT000000","VSET","LEVL",ExAnte,"Absolute")
                                     $ (   (ORDT(ExAnte) GT OrdT("2010")))
              =  P_Result("IT000000","VSET","LEVL",ExAnte,"Support")  ;

    CAPRI's GAMS (captrd/national_supports.gms l. 934-937):

          p_ExpertSupprt("CY000000","GROF","PORK",exAnteT,"Absolute")
                                     $ ( P_Result("CY000000","GROF","PORK",ExAnteT,"Support")
                                       $ (calyea(exanteT) gt calyea("2020")))
              = P_Result("CY000000","GROF","PORK",ExAnteT,"Support");

    CAPRI's GAMS (captrd/national_supports.gms l. 1006-1008):

          p_ExpertSupprt("KO000000","hens",herdLevl,exanteT,"Absolute")
                   $( P_Result("KO000000","hens",herdLevl,ExanteT,"Support") $(ORDT(ExAnteT) GE ORDT("2020")) $(ORDT(ExAnteT) LE ORDT("2030")))
             = P_Result("KO000000","hens",herdLevl,ExanteT,"Support");

    CAPRI's GAMS (captrd/national_supports.gms l. 1271-1276):

          p_ExpertSupprt("SI000000",cols,herdLevl,exanteT,"Absolute")
                                     $ ( P_Result("SI000000",cols,herdLevl,ExanteT,"Support")
                                       $ (not p_ExpertSupprt("SI000000",cols,herdLevl,ExanteT,"absolute"))
                                       $  (P_T_ActAgg(COLS,"SHGT") or sameas(cols,"POUF") or sameas(cols,"hens"))
                                       $ P_Result("SI000000",cols,herdLevl,ExanteT,"BASM"))
              = P_Result("SI000000",cols,herdLevl,ExanteT,"Support");

    CAPRI's GAMS (captrd/national_supports.gms l. 1393-1398):

          p_ExpertSupprt("CZ000000",cols,herdLevl,exanteT,"Absolute")
                                     $ ( P_Result("CZ000000",cols,herdLevl,ExanteT,"Support")
                                       $ (not p_ExpertSupprt("CZ000000",cols,herdLevl,ExanteT,"absolute"))
                                       $  (P_T_ActAgg(COLS,"SHGT") )
                                       $ P_Result("CZ000000",cols,herdLevl,ExanteT,"BASM"))
              = P_Result("CZ000000",cols,herdLevl,ExanteT,"Support");

    CAPRI's GAMS (captrd/national_supports.gms l. 1436-1437):

          p_ExpertSupprt("NO000000",dcow,"COMI",ExAnteT,"Absolute") $ (ORDT(ExAnteT) ge OrdT("2020"))
              = P_Result("NO000000",dcow,"COMI",ExAnteT,"Support");

    CAPRI's GAMS (captrd/national_supports.gms l. 1457-1462):

          p_ExpertSupprt("NO000000",cols,herdLevl,exanteT,"Absolute")
                                     $ ( P_Result("NO000000",cols,herdLevl,ExanteT,"Support")
                                       $ (not p_ExpertSupprt("NO000000",cols,herdLevl,ExanteT,"absolute"))
                                       $  (P_T_ActAgg(COLS,"SHGT") )
                                       $ P_Result("NO000000",cols,herdLevl,ExanteT,"BASM"))
              = P_Result("NO000000",cols,herdLevl,ExanteT,"Support");

    CAPRI's GAMS (captrd/national_supports.gms l. 1488-1489):

          p_ExpertSupprt("TUR",cols,"POUM",ExAnteT,"Absolute") $ ((ORDT(ExAnteT) gt OrdT("2020")) $ P_T_ActAgg(COLS,"POUL"))
              = P_Result("TUR",cols,"POUM",ExAnteT,"Support");

    CAPRI's GAMS (captrd/national_supports.gms l. 1496-1501):

          p_ExpertSupprt("TUR",cols,herdLevl,exanteT,"Absolute")
                                     $ ( P_Result("TUR",cols,herdLevl,ExanteT,"Support")
                                       $ (not p_ExpertSupprt("TUR",cols,herdLevl,ExanteT,"absolute"))
                                       $  (P_T_ActAgg(COLS,"SHGT") )
                                       $ P_Result("TUR",cols,herdLevl,ExanteT,"BASM"))
              = P_Result("TUR",cols,herdLevl,ExanteT,"Support");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return support


def p_ExpertSupprt_Absolute_base(value):
    r"""p_ExpertSupprt(country, ., ., exanteT, "Absolute"): BAST (IR's pork, IT's pork balance, SI's suckler cows) or
    BASM (SE's and SI's pork production).

    CAPRI's GAMS (captrd/national_supports.gms l. 633-635):

          p_ExpertSupprt("IR000000","GROF","PORK",EXANTET,"absolute") $ ( P_DATA("IR000000","GROF","PORK","BAST")
                                                                          $ (Ordt(ExAnteT) gt Ordt("2020")))
              = P_DATA("IR000000","GROF","PORK","BAST");

    CAPRI's GAMS (captrd/national_supports.gms l. 668-671):

          p_ExpertSupprt("IT000000",mrkKeyPos,"PORK",EXANTET,"absolute") $ ( P_DATA("IT000000",mrkKeyPos,"PORK","BAST")
                                                                           $ (Ordt(ExAnteT) gt Ordt("2020")))
        *        No increase to limit growth of slaughter weights
               = P_DATA("IT000000",mrkKeyPos,"PORK","BAST");

    CAPRI's GAMS (captrd/national_supports.gms l. 854-858):

          p_ExpertSupprt("SE000000","GROF","PORK",exanteT,"Absolute")
                                     $ ( P_Result("SE000000","GROF","PORK",ExanteT,"BASM")
                                       $ (ORDT(ExAnteT) GT ORDT("2020"))
                                       $ (not p_ExpertSupprt("SE000000","GROF","PORK",ExanteT,"absolute")))
              = P_Result("SE000000","GROF","PORK",ExanteT,"BASM");

    CAPRI's GAMS (captrd/national_supports.gms l. 1307-1309):

          p_ExpertSupprt("SI000000","SCOW",herdLevl,EXANTET,"absolute")
              $ (P_DATA("SI000000","SCOW",herdLevl,"BAST") $ (Ordt(ExAnteT) gt Ordt("2020")))
              = P_DATA("SI000000","SCOW",herdLevl,"BAST");

    CAPRI's GAMS (captrd/national_supports.gms l. 1316-1320):

          p_ExpertSupprt("SI000000","GROF","PORK",exanteT,"Absolute")
                                     $ ( P_Result("SI000000","GROF","PORK",ExanteT,"BASM")
                                       $ (ORDT(ExAnteT) GT ORDT("2020"))
                                       $ (not p_ExpertSupprt("SI000000","GROF","PORK",ExanteT,"absolute")))
              = P_Result("SI000000","GROF","PORK",ExanteT,"BASM");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return value


def p_ExpertSupprt_trustlevl_rule(trust, plus=0.0):
    r"""p_ExpertSupprt(country, ., ., ., "trustlevl") of the countries' rules: the rule's trust level, a constant or
    p_trustNat plus a few.

    trust: the constant or p_trustNat; plus: what CAPRI adds to p_trustNat.

    CAPRI's GAMS (captrd/national_supports.gms l. 298-301):

          p_ExpertSupprt("AT000000","PIGF",rows,exAnteT,"trustlevl")
                                     $   (   p_ExpertSupprt("AT000000","PIGF",rows,exAnteT,"Absolute") $ herdLevl(rows)
                                         $ (not p_ExpertSupprt("AT000000","PIGF",rows,exAnteT,"trustlevl")))
              = 9.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 303-306):

          p_ExpertSupprt("AT000000","PIGF",rows,exAnteT,"trustlevl")
                                     $   (   p_ExpertSupprt("AT000000","PIGF",rows,exAnteT,"Absolute") $  (sameas(rows,"PORK")  or sameas(rows,"DAYS"))
                                         $ (not p_ExpertSupprt("AT000000","PIGF",rows,exAnteT,"trustlevl")))
              = 9.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 323-325):

          p_ExpertSupprt("BL000000",DCOW,"COMI",exanteT,"trustlevl") $ ( p_ExpertSupprt("BL000000",DCOW,"COMI",exanteT,"Absolute")
                                                                  $ (ORDT(ExAnteT) eq ORDT("2020")))
             = 10.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 335-338):

          p_ExpertSupprt("BL000000","GROF","PORK",exAnteT,"trustlevl")
                                     $   (   p_ExpertSupprt("BL000000","GROF","PORK",exAnteT,"Absolute")
                                         $ (not p_ExpertSupprt("BL000000","GROF","PORK",exAnteT,"trustlevl")))
              = 8.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 384-386):

          p_ExpertSupprt("BL400000",cols,rows,exante,"trustlevl")
                                     $   p_ExpertSupprt("BL400000",cols,rows,exante,"PercentChange")
              = 10.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 425-426):

          p_ExpertSupprt("DE000000","INDM","MAIF",exanteT,"trustLevl") $ p_ExpertSupprt("DE000000","INDM","MAIF",exanteT,"Absolute")
              = 10.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 440-441):

          p_ExpertSupprt(NT2est,"INDM","MAIF",exanteT,"trustLevl") $ p_ExpertSupprt(NT2est,"INDM","MAIF",exanteT,"Absolute")
              = 5.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 450-453):

          p_ExpertSupprt("DE000000",DCOW,herdLevl,exanteT,"trustlevl")
                                     $ ( p_ExpertSupprt("DE000000",DCOW,herdLevl,exanteT,"PercentChange")
                                       $ (ORDT(ExanteT) GT ORDT("2020")))
              =    p_trustNat;

    CAPRI's GAMS (captrd/national_supports.gms l. 461-464):

          p_ExpertSupprt("DE000000",cols,"COMI",exanteT,"trustlevl")
                                       $ ((ORDT(ExanteT) GT ORDT("2020"))
                                       $ expertdairy_map(cols,"COMI") $ (not P_T_ActAgg(cols,"DCOW")) )
               = p_trustNat;

    CAPRI's GAMS (captrd/national_supports.gms l. 467-468):

          p_ExpertSupprt("DE000000","SHGM",herdLevl,exanteT,"Trustlevl") $  p_ExpertSupprt("DE000000","SHGM",herdLevl,exanteT,"Percentchange")
            = p_trustNat +2;

    CAPRI's GAMS (captrd/national_supports.gms l. 511-514):

          p_ExpertSupprt("DK000000",DCOW,herdLevl,exante,"trustlevl")
                                     $ ( p_ExpertSupprt("DK000000",DCOW,herdLevl,exante,"PercentChange")
                                       $ (ORDT(ExAnte) GT ORDT("2020")))
              =    p_trustNat;

    CAPRI's GAMS (captrd/national_supports.gms l. 522-525):

          p_ExpertSupprt("DK000000",cols,"COMI",exante,"trustlevl")
                                       $ ( (ORDT(ExAnte) GT ORDT("2020"))
                                         $ expertdairy_map(cols,"COMI") $ (not P_T_ActAgg(cols,"DCOW")) )
               = p_trustNat;

    CAPRI's GAMS (captrd/national_supports.gms l. 589-591):

          p_ExpertSupprt("EL000000","SHGM","SGMI",exanteT,"trustlevl")
                                     $   p_ExpertSupprt("EL000000","SHGM","SGMI",exanteT,"Absolute")
              = 9.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 603-606):

          p_ExpertSupprt("ES000000",DCOW,herdLevl,exante,"trustlevl")
                                     $ ( p_ExpertSupprt("ES000000",DCOW,herdLevl,exante,"PercentChange")
                                       $ (ORDT(ExAnte) GT ORDT("2020")))
              =    p_trustNat;

    CAPRI's GAMS (captrd/national_supports.gms l. 614-617):

          p_ExpertSupprt("ES000000",cols,"COMI",exante,"trustlevl")
                                       $ ( (ORDT(ExAnte) GT ORDT("2020"))
                                         $ expertdairy_map(cols,"COMI") $ (not P_T_ActAgg(cols,"DCOW")) )
               = p_trustNat;

    CAPRI's GAMS (captrd/national_supports.gms l. 625-626):

          p_ExpertSupprt("FI000000","PIGF",herdLevl,exanteT,"Trustlevl") $  p_ExpertSupprt("FI000000","PIGF",herdLevl,exanteT,"Percentchange")
            = p_trustNat +2;

    CAPRI's GAMS (captrd/national_supports.gms l. 637-637):

          p_ExpertSupprt("IR000000","GROF","PORK",exanteT,"Trustlevl") $  p_ExpertSupprt("IR000000","GROF","PORK",exanteT,"absolute") = 3.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 640-642):

          p_ExpertSupprt("IR000000",cols,herdLevl,exanteT,"Trustlevl")
            $  (p_ExpertSupprt("IR000000",cols,herdLevl,exanteT,"Percentchange") $ P_T_ActAgg(COLS,"POUL"))
            = p_trustNat +2;

    CAPRI's GAMS (captrd/national_supports.gms l. 654-657):

          p_ExpertSupprt("IT000000","GROF",rows,ExAnte,"TRustlevl")
                                     $ (  (SAMEAS(rows,"PORK") or SAMEAS(rows,"YPIG") or SAMEAS(rows,"IPIG"))
                                        $ p_ExpertSupprt("IT000000","GROF","PORK",ExAnte,"Percentchange")   )
              = 2;

    CAPRI's GAMS (captrd/national_supports.gms l. 666-666):

          p_ExpertSupprt("IT000000","PIGF",herdLevl,exanteT,"Trustlevl") $  p_ExpertSupprt("IT000000","PIGF",herdLevl,exanteT,"absolute") = 9.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 673-673):

          p_ExpertSupprt("IT000000",mrkKeyPos,"PORK",exanteT,"Trustlevl") $  p_ExpertSupprt("IT000000",mrkKeyPos,"PORK",exanteT,"absolute") = 9.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 681-681):

          p_ExpertSupprt("IT000000","SCOW",herdLevl,exanteT,"Trustlevl") $  p_ExpertSupprt("IT000000","SCOW",herdLevl,exanteT,"absolute") = 9.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 721-723):

          p_ExpertSupprt("IT000000",DCOW,rows,exanteT,"trustlevl") $ ( p_ExpertSupprt("IT000000",DCOW,rows,exanteT,"Absolute")
                                                                  $ (ORDT(ExAnteT) eq ORDT("2025")) $ (herdLevl(rows) or sameas(rows,"comi")))
             = 10.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 733-735):

          p_ExpertSupprt("IT000000","VSET","LEVL",ExAnte,"TRustlevl")
                                     $  (    p_ExpertSupprt("IT000000","VSET","LEVL",ExAnte,"Absolute"))
              = 2.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 748-751):

          p_ExpertSupprt("NL000000",DCOW,herdLevl,exante,"trustlevl")
                                     $ ( p_ExpertSupprt("NL000000",DCOW,herdLevl,exante,"PercentChange")
                                       $ (ORDT(ExAnte) GT ORDT("2020")))
              =    p_trustNat+2;

    CAPRI's GAMS (captrd/national_supports.gms l. 759-762):

          p_ExpertSupprt("NL000000",cols,"COMI",exante,"trustlevl")
                                       $ ( (ORDT(ExAnte) GT ORDT("2020"))
                                         $ expertdairy_map(cols,"COMI") $ (not P_T_ActAgg(cols,"DCOW")) )
               = p_trustNat;

    CAPRI's GAMS (captrd/national_supports.gms l. 773-775):

          p_ExpertSupprt("NL000000","PIGF","DAYS",exante,"trustlevl")
                                     $   p_ExpertSupprt("NL000000","PIGF","DAYS",exante,"PercentChange")
              = 8.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 794-796):

          p_ExpertSupprt("PT000000",CowsAct,"LEVL",exante,"Trustlevl")
                                     $      p_ExpertSupprt("PT000000",CowsAct,"LEVL",exante,"PercentChange")
              = 6;

    CAPRI's GAMS (captrd/national_supports.gms l. 802-803):

          p_ExpertSupprt("PT000000","PIGF","PORK",ExAnte,"Trustlevl")
               = 10;

    CAPRI's GAMS (captrd/national_supports.gms l. 813-814):

          p_ExpertSupprt("PT000000","SOWS","YPIG",ExAnte,"Trustlevl")
               = 2;

    CAPRI's GAMS (captrd/national_supports.gms l. 842-844):

          p_ExpertSupprt("PT000000","GROF",OIYANI,ExAnte,"TRustlevl")
                                     $ p_ExpertSupprt("PT000000","GROF",OIYANI,ExAnte,"Percentchange")
              = 3;

    CAPRI's GAMS (captrd/national_supports.gms l. 860-862):

          p_ExpertSupprt("SE000000","GROF","PORK",exanteT,"trustlevl")
                                     $   (  p_ExpertSupprt("SE000000","GROF","PORK",exanteT,"Absolute"))
              = 8.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 883-884):

          p_ExpertSupprt("BG000000","PIGF",herdLevl,exanteT,"Trustlevl") $  p_ExpertSupprt("BG000000","PIGF",herdLevl,exanteT,"Percentchange")
            = p_trustNat +1;

    CAPRI's GAMS (captrd/national_supports.gms l. 910-912):

          p_ExpertSupprt("CY000000",dcow,herdLevl,exAnteT,"trustlevl")
                                     $   p_ExpertSupprt("CY000000",dcow,herdLevl,exAnteT,"PercentChange")
              = 8.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 939-942):

          p_ExpertSupprt("CY000000","GROF","PORK",exAnteT,"trustlevl")
                                     $   (   p_ExpertSupprt("CY000000","GROF","PORK",exAnteT,"Absolute")
                                         $ (not p_ExpertSupprt("CY000000","GROF","PORK",exAnteT,"trustlevl")))
              = 8.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 981-984):

          p_ExpertSupprt("CS000000",cols,rows,exante,"trustlevl")
                                     $ (  p_ExpertSupprt("CS000000",cols,rows,exante,"absolute")
                                       $  expertdairy_map(cols,rows) )
              = 9.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 997-998):

          p_ExpertSupprt("BA000000","pouf",HerdLevl,exanteT,"trustLevl") $ p_ExpertSupprt("BA000000","pouf",HerdLevl,exanteT,"Absolute")
             = 8.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 1010-1011):

          p_ExpertSupprt("KO000000","hens",herdLevl,exanteT,"Trustlevl")
                   $  p_ExpertSupprt("KO000000","hens",herdLevl,exanteT,"Absolute") = 8.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 1035-1037):

          p_ExpertSupprt("EE000000",DCOW,"COMI",exanteT,"trustlevl") $ ( p_ExpertSupprt("EE000000",DCOW,"COMI",exanteT,"Absolute")
                                                                  $ (ORDT(ExAnteT) eq ORDT("2020")))
             = 10.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 1055-1058):

          p_ExpertSupprt("EE000000",DCOW,herdLevl,exante,"trustlevl")
                                     $ ( p_ExpertSupprt("EE000000",DCOW,herdLevl,exante,"PercentChange")
                                       $ (ORDT(ExAnte) GT ORDT("2020")))
              =    p_trustNat;

    CAPRI's GAMS (captrd/national_supports.gms l. 1066-1069):

          p_ExpertSupprt("EE000000",cols,"COMI",exante,"trustlevl")
                                       $ ( (ORDT(ExAnte) GT ORDT("2020"))
                                         $ expertdairy_map(cols,"COMI") $ (not P_T_ActAgg(cols,"DCOW")) )
               = p_trustNat;

    CAPRI's GAMS (captrd/national_supports.gms l. 1080-1083):

          p_ExpertSupprt("EE000000",mrkKeyPos,rows,exante,"trustlevl")
                                       $ ( (ORDT(ExAnte) GT ORDT("2020"))
                                         $ (sameas(rows,"SGMT") or sameas(rows,"SGMI")))
               = p_trustNat;

    CAPRI's GAMS (captrd/national_supports.gms l. 1093-1094):

          p_ExpertSupprt("HR000000","PIGF",herdLevl,exanteT,"Trustlevl") $  p_ExpertSupprt("HR000000","PIGF",herdLevl,exanteT,"Percentchange")
            = p_trustNat +1;

    CAPRI's GAMS (captrd/national_supports.gms l. 1106-1109):

          p_ExpertSupprt("HR000000",DCOW,herdLevl,exante,"trustlevl")
                                     $ ( p_ExpertSupprt("HR000000",DCOW,herdLevl,exante,"PercentChange")
                                       $ (ORDT(ExAnte) GT ORDT("2020")))
              =    p_trustNat;

    CAPRI's GAMS (captrd/national_supports.gms l. 1117-1120):

          p_ExpertSupprt("HR000000",cols,"COMI",exante,"trustlevl")
                                       $ ( (ORDT(ExAnte) GT ORDT("2020"))
                                         $ expertdairy_map(cols,"COMI") $ (not P_T_ActAgg(cols,"DCOW")) )
               = p_trustNat;

    CAPRI's GAMS (captrd/national_supports.gms l. 1133-1136):

          p_ExpertSupprt("LV000000",DCOW,herdLevl,exante,"trustlevl")
                                     $ ( p_ExpertSupprt("LV000000",DCOW,herdLevl,exante,"PercentChange")
                                       $ (ORDT(ExAnte) GT ORDT("2020")))
              =    p_trustNat;

    CAPRI's GAMS (captrd/national_supports.gms l. 1144-1147):

          p_ExpertSupprt("LV000000",cols,"COMI",exante,"trustlevl")
                                       $ ( (ORDT(ExAnte) GT ORDT("2020"))
                                         $ expertdairy_map(cols,"COMI") $ (not P_T_ActAgg(cols,"DCOW")) )
               = p_trustNat;

    CAPRI's GAMS (captrd/national_supports.gms l. 1158-1161):

          p_ExpertSupprt("LV000000",mrkKeyPos,rows,exante,"trustlevl")
                                       $ ( (ORDT(ExAnte) GT ORDT("2020"))
                                         $ (sameas(rows,"SGMT") or sameas(rows,"SGMI")))
               = p_trustNat;

    CAPRI's GAMS (captrd/national_supports.gms l. 1174-1177):

          p_ExpertSupprt("LT000000",DCOW,herdLevl,exante,"trustlevl")
                                     $ ( p_ExpertSupprt("LT000000",DCOW,herdLevl,exante,"PercentChange")
                                       $ (ORDT(ExAnte) GT ORDT("2020")))
              =    p_trustNat;

    CAPRI's GAMS (captrd/national_supports.gms l. 1185-1188):

          p_ExpertSupprt("LT000000",cols,"COMI",exante,"trustlevl")
                                       $ ( (ORDT(ExAnte) GT ORDT("2020"))
                                         $ expertdairy_map(cols,"COMI") $ (not P_T_ActAgg(cols,"DCOW")) )
               = p_trustNat;

    CAPRI's GAMS (captrd/national_supports.gms l. 1212-1214):

          p_ExpertSupprt("MT000000","GROF","SGMT",exAnteT,"trustlevl")
                                     $   p_ExpertSupprt("MT000000","GROF","SGMT",exAnteT,"PercentChange")
              = 7.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 1221-1222):

          p_ExpertSupprt("PL000000","PIGF",herdLevl,exanteT,"Trustlevl") $  p_ExpertSupprt("PL000000","PIGF",herdLevl,exanteT,"Percentchange")
            = p_trustNat +1;

    CAPRI's GAMS (captrd/national_supports.gms l. 1236-1239):

          p_ExpertSupprt("RO000000",DCOW,herdLevl,exante,"trustlevl")
                                     $ ( p_ExpertSupprt("RO000000",DCOW,herdLevl,exante,"PercentChange")
                                       $ (ORDT(ExAnte) GT ORDT("2020")))
              =    p_trustNat;

    CAPRI's GAMS (captrd/national_supports.gms l. 1247-1250):

          p_ExpertSupprt("RO000000",cols,"COMI",exante,"trustlevl")
                                       $ ( (ORDT(ExAnte) GT ORDT("2020"))
                                         $ expertdairy_map(cols,"COMI") $ (not P_T_ActAgg(cols,"DCOW")) )
               = p_trustNat;

    CAPRI's GAMS (captrd/national_supports.gms l. 1255-1256):

          p_ExpertSupprt("RO000000","PIGF",herdLevl,exanteT,"Trustlevl") $  p_ExpertSupprt("RO000000","PIGF",herdLevl,exanteT,"Percentchange")
            = p_trustNat +2;

    CAPRI's GAMS (captrd/national_supports.gms l. 1263-1263):

          p_ExpertSupprt("RO000000","MAIF","LEVL",exanteT,"Trustlevl") $  p_ExpertSupprt("RO000000","MAIF","LEVL",exanteT,"PercentChange") = .5;

    CAPRI's GAMS (captrd/national_supports.gms l. 1278-1281):

          p_ExpertSupprt("SI000000",cols,herdLevl,exanteT,"trustlevl")
                                     $   (  p_ExpertSupprt("SI000000",cols,herdLevl,exanteT,"Absolute")
                                         $  (P_T_ActAgg(COLS,"SHGT") or sameas(cols,"POUF") or sameas(cols,"hens")))
              = 9.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 1311-1311):

          p_ExpertSupprt("SI000000","SCOW",herdLevl,exanteT,"Trustlevl") $  p_ExpertSupprt("SI000000","SCOW",herdLevl,exanteT,"absolute") = 9.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 1322-1324):

          p_ExpertSupprt("SI000000","GROF","PORK",exanteT,"trustlevl")
                                     $   (  p_ExpertSupprt("SI000000","GROF","PORK",exanteT,"Absolute"))
              = 8.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 1357-1359):

          p_ExpertSupprt("SK000000",DCOW,"COMI",exanteT,"trustlevl") $ ( p_ExpertSupprt("SK000000",DCOW,"COMI",exanteT,"Absolute")
                                                                  $ (ORDT(ExAnteT) eq ORDT("2020")))
             = 10.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 1368-1371):

          p_ExpertSupprt("SK000000",mrkKeyPos,rows,exante,"trustlevl")
                                       $ ( (ORDT(ExAnte) GT ORDT("2020"))
                                         $ (sameas(rows,"SGMT") or sameas(rows,"SGMI")))
               = p_trustNat;

    CAPRI's GAMS (captrd/national_supports.gms l. 1400-1402):

          p_ExpertSupprt("CZ000000",cols,herdLevl,exanteT,"trustlevl")
                                     $   (p_ExpertSupprt("CZ000000",cols,herdLevl,exanteT,"Absolute") $ P_T_ActAgg(COLS,"SHGT"))
              = 10.01;

    CAPRI's GAMS (captrd/national_supports.gms l. 1429-1432):

          p_ExpertSupprt("NO000000",cols,"COMI",ExAnteT,"TRustlevl")
              $ ( p_ExpertSupprt("NO000000",cols,"COMI",ExAnteT,"Absolute")
                $ (ORDT(ExAnteT) gt OrdT("2020")) $ expertdairy_map(cols,"COMI"))
              = p_trustNat+1;

    CAPRI's GAMS (captrd/national_supports.gms l. 1439-1440):

          p_ExpertSupprt("NO000000",dcow,"COMI",ExAnteT,"TRustlevl")
              = p_trustNat-2;

    CAPRI's GAMS (captrd/national_supports.gms l. 1450-1453):

          p_ExpertSupprt("NO000000",mrkKeyPos,rows,ExAnteT,"TRustlevl")
              $ ( p_ExpertSupprt("NO000000",mrkKeyPos,rows,ExAnteT,"Absolute") $ (ORDT(ExAnteT) gt OrdT("2020"))
                $ (sameas(rows,"PORK") or sameas(rows,"EGGS") or sameas(rows,"POUM") ))
              = p_trustNat;

    CAPRI's GAMS (captrd/national_supports.gms l. 1464-1466):

          p_ExpertSupprt("NO000000",cols,herdLevl,exanteT,"trustlevl")
                                     $   (p_ExpertSupprt("NO000000",cols,herdLevl,exanteT,"Absolute") $ P_T_ActAgg(COLS,"SHGT"))
              = p_trustNat;

    CAPRI's GAMS (captrd/national_supports.gms l. 1491-1492):

          p_ExpertSupprt("TUR",cols,"POUM",ExAnteT,"TRustlevl") $ ((ORDT(ExAnteT) gt OrdT("2020")) $ P_T_ActAgg(COLS,"POUL"))
              = p_trustNat+3;

    CAPRI's GAMS (captrd/national_supports.gms l. 1503-1505):

          p_ExpertSupprt("TUR",cols,herdLevl,exanteT,"trustlevl")
                                     $   (p_ExpertSupprt("TUR",cols,herdLevl,exanteT,"Absolute") $ P_T_ActAgg(COLS,"SHGT"))
              = p_trustNat;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return trust + plus


def p_result_expert_bound(factor, absolute):
    r"""p_result(country, ., ., exanteT, "expertLo" / "expertUp"): the factor (.99 / 1.01) times the Absolute.

    CAPRI's GAMS (captrd/national_supports.gms l. 316-318):

          p_result("BL000000",DCOW,"COMI",exanteT,"expertLo") $ ( p_ExpertSupprt("BL000000",DCOW,"COMI",exanteT,"Absolute")
                                                                  $ (ORDT(ExAnteT) eq ORDT("2020")))
             = .99 * p_ExpertSupprt("BL000000",DCOW,"COMI",exanteT,"Absolute");

    CAPRI's GAMS (captrd/national_supports.gms l. 319-321):

          p_result("BL000000",DCOW,"COMI",exanteT,"expertUp") $ ( p_ExpertSupprt("BL000000",DCOW,"COMI",exanteT,"Absolute")
                                                                  $ (ORDT(ExAnteT) eq ORDT("2020")))
             = 1.01* p_ExpertSupprt("BL000000",DCOW,"COMI",exanteT,"Absolute");

    CAPRI's GAMS (captrd/national_supports.gms l. 779-781):

          p_result("NL000000",DCOW,herdLEVL,exanteT,"expertLo") $ ( p_ExpertSupprt("NL000000",DCOW,herdLEVL,exanteT,"Absolute")
                                                                  $ (ORDT(ExAnteT) eq ORDT("2020")))
             = .99 * p_ExpertSupprt("NL000000",DCOW,herdLEVL,exanteT,"Absolute");

    CAPRI's GAMS (captrd/national_supports.gms l. 782-784):

          p_result("NL000000",DCOW,herdLEVL,exanteT,"expertUp") $ ( p_ExpertSupprt("NL000000",DCOW,herdLEVL,exanteT,"Absolute")
                                                                  $ (ORDT(ExAnteT) eq ORDT("2020")))
             = 1.01* p_ExpertSupprt("NL000000",DCOW,herdLEVL,exanteT,"Absolute");

    CAPRI's GAMS (captrd/national_supports.gms l. 1028-1030):

          p_result("EE000000",DCOW,"COMI",exanteT,"expertLo") $ ( p_ExpertSupprt("EE000000",DCOW,"COMI",exanteT,"Absolute")
                                                                  $ (ORDT(ExAnteT) eq ORDT("2020")))
             = .99 * p_ExpertSupprt("EE000000",DCOW,"COMI",exanteT,"Absolute");

    CAPRI's GAMS (captrd/national_supports.gms l. 1031-1033):

          p_result("EE000000",DCOW,"COMI",exanteT,"expertUp") $ ( p_ExpertSupprt("EE000000",DCOW,"COMI",exanteT,"Absolute")
                                                                  $ (ORDT(ExAnteT) eq ORDT("2020")))
             = 1.01* p_ExpertSupprt("EE000000",DCOW,"COMI",exanteT,"Absolute");

    CAPRI's GAMS (captrd/national_supports.gms l. 1039-1041):

          p_result("EE000000",DCOW,herdLEVL,exanteT,"expertLo") $ ( p_ExpertSupprt("EE000000",DCOW,herdLEVL,exanteT,"Absolute")
                                                                  $ (ORDT(ExAnteT) eq ORDT("2020")))
             = .99 * p_ExpertSupprt("EE000000",DCOW,herdLEVL,exanteT,"Absolute");

    CAPRI's GAMS (captrd/national_supports.gms l. 1042-1044):

          p_result("EE000000",DCOW,herdLEVL,exanteT,"expertUp") $ ( p_ExpertSupprt("EE000000",DCOW,herdLEVL,exanteT,"Absolute")
                                                                  $ (ORDT(ExAnteT) eq ORDT("2020")))
             = 1.01* p_ExpertSupprt("EE000000",DCOW,herdLEVL,exanteT,"Absolute");

    CAPRI's GAMS (captrd/national_supports.gms l. 1285-1288):

          p_result("SI000000",cols,herdlevl,exanteT,"expertLo") $ ( p_ExpertSupprt("SI000000",cols,herdlevl,exanteT,"Absolute")
                                                                  $  (P_T_ActAgg(COLS,"SHGT") )
                                                                  $ (ORDT(ExAnteT) ge ORDT("2050")))
             = .99 * p_ExpertSupprt("SI000000",cols,herdlevl,exanteT,"Absolute");

    CAPRI's GAMS (captrd/national_supports.gms l. 1289-1292):

          p_result("SI000000",cols,herdlevl,exanteT,"expertUp") $ ( p_ExpertSupprt("SI000000",cols,herdlevl,exanteT,"Absolute")
                                                                  $  (P_T_ActAgg(COLS,"SHGT") )
                                                                  $ (ORDT(ExAnteT) ge ORDT("2050")))
             = 1.01* p_ExpertSupprt("SI000000",cols,herdlevl,exanteT,"Absolute");

    CAPRI's GAMS (captrd/national_supports.gms l. 1350-1352):

          p_result("SK000000",DCOW,"COMI",exanteT,"expertLo") $ ( p_ExpertSupprt("SK000000",DCOW,"COMI",exanteT,"Absolute")
                                                                  $ (ORDT(ExAnteT) eq ORDT("2020")))
             = .99 * p_ExpertSupprt("SK000000",DCOW,"COMI",exanteT,"Absolute");

    CAPRI's GAMS (captrd/national_supports.gms l. 1353-1355):

          p_result("SK000000",DCOW,"COMI",exanteT,"expertUp") $ ( p_ExpertSupprt("SK000000",DCOW,"COMI",exanteT,"Absolute")
                                                                  $ (ORDT(ExAnteT) eq ORDT("2020")))
             = 1.01* p_ExpertSupprt("SK000000",DCOW,"COMI",exanteT,"Absolute");

    CAPRI's GAMS (captrd/national_supports.gms l. 1406-1409):

          p_result("CZ000000",cols,herdlevl,exanteT,"expertLo") $ ( p_ExpertSupprt("CZ000000",cols,herdlevl,exanteT,"Absolute")
                                                                  $  (P_T_ActAgg(COLS,"SHGT") )
                                                                  $ (ORDT(ExAnteT) eq ORDT("2030")))
             = .99 * p_ExpertSupprt("CZ000000",cols,herdlevl,exanteT,"Absolute");

    CAPRI's GAMS (captrd/national_supports.gms l. 1410-1413):

          p_result("CZ000000",cols,herdlevl,exanteT,"expertUp") $ ( p_ExpertSupprt("CZ000000",cols,herdlevl,exanteT,"Absolute")
                                                                  $  (P_T_ActAgg(COLS,"SHGT") )
                                                                  $ (ORDT(ExAnteT) eq ORDT("2030")))
             = 1.01* p_ExpertSupprt("CZ000000",cols,herdlevl,exanteT,"Absolute");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return factor * absolute


def p_result_expert_bound_percent(factor, percent, basm):
    r"""p_result(country, ., ., exanteT, "expertLo" / "expertUp"): the factor (.99 / 1.01, .95 / 1.05, .9 / 1.1) times
    the PercentChange's level.

    CAPRI's GAMS (captrd/national_supports.gms l. 388-393):

          p_result("BL400000",cols,rows,exanteT,"expertLo") $ (  p_ExpertSupprt("BL400000",cols,rows,exanteT,"PercentChange")
                                                                  $ P_Result("BL400000",cols,rows,ExAnteT,"BASM")
                                                                  $ (P_T_ActAgg(cols,"DCOW") )
                                                                  $ expertdairy_map(Cols,Rows))
             = .99* (1+p_ExpertSupprt("BL400000",cols,rows,exanteT,"PercentChange")/100)
             * P_Result("BL400000",cols,rows,ExAnteT,"BASM");

    CAPRI's GAMS (captrd/national_supports.gms l. 395-400):

          p_result("BL400000",cols,rows,exanteT,"expertUp") $ (  p_ExpertSupprt("BL400000",cols,rows,exanteT,"PercentChange")
                                                                  $ P_Result("BL400000",cols,rows,ExAnteT,"BASM")
                                                                  $ (P_T_ActAgg(cols,"DCOW") )
                                                                  $ expertdairy_map(Cols,Rows))
             = 1.01* (1+p_ExpertSupprt("BL400000",cols,rows,exanteT,"PercentChange")/100)
             * P_Result("BL400000",cols,rows,ExAnteT,"BASM");

    CAPRI's GAMS (captrd/national_supports.gms l. 685-687):

          p_result("IT000000",DCOW,herdLEVL,exanteT,"expertLo") $ p_ExpertSupprt("IT000000",DCOW,herdLEVL,exanteT,"PercentChange")
             = .95 * (1+p_ExpertSupprt("IT000000",DCOW,herdLEVL,exanteT,"PercentChange")/100)
             * P_Result("IT000000",DCOW,herdLEVL,ExAnteT,"BASM");

    CAPRI's GAMS (captrd/national_supports.gms l. 688-690):

          p_result("IT000000",DCOW,herdLEVL,exanteT,"expertUp") $ p_ExpertSupprt("IT000000",DCOW,herdLEVL,exanteT,"PercentChange")
             = 1.05 * (1+p_ExpertSupprt("IT000000",DCOW,herdLEVL,exanteT,"PercentChange")/100)
             * P_Result("IT000000",DCOW,herdLEVL,ExAnteT,"BASM");

    CAPRI's GAMS (captrd/national_supports.gms l. 693-697):

          p_result("IT000000",mrkKeyPos,"COMI",exanteT,"expertLo") $ (  p_ExpertSupprt("IT000000",mrkKeyPos,"COMI",exanteT,"PercentChange")
                                                                  $ P_Result("IT000000",mrkKeyPos,"COMI",ExAnteT,"BASM")
                                                                  $ expertdairy_map(MrkKeyPos,"COMI"))
             = .9* (1+p_ExpertSupprt("IT000000",mrkKeyPos,"COMI",exanteT,"PercentChange")/100)
             * P_Result("IT000000",mrkKeyPos,"COMI",ExAnteT,"BASM");

    CAPRI's GAMS (captrd/national_supports.gms l. 699-703):

          p_result("IT000000",mrkKeyPos,"COMI",exanteT,"expertUp") $ (  p_ExpertSupprt("IT000000",mrkKeyPos,"COMI",exanteT,"PercentChange")
                                                                  $ P_Result("IT000000",mrkKeyPos,"COMI",ExAnteT,"BASM")
                                                                  $ expertdairy_map(MrkKeyPos,"COMI"))
             = 1.1* (1+p_ExpertSupprt("IT000000",mrkKeyPos,"COMI",exanteT,"PercentChange")/100)
             * P_Result("IT000000",mrkKeyPos,"COMI",ExAnteT,"BASM");

    CAPRI's GAMS (captrd/national_supports.gms l. 712-715):

          p_result("IT000000",DCOW,rows,exanteT,"expertLo") $ ( p_ExpertSupprt("IT000000",DCOW,rows,exanteT,"PercentChange")
                                                                  $ (ORDT(ExAnteT) eq ORDT("2025")) $ (herdLevl(rows) or sameas(rows,"comi")))
             = .99 * (1+p_ExpertSupprt("IT000000",DCOW,rows,exanteT,"PercentChange")/100)
             * P_Result("IT000000",DCOW,rows,ExAnteT,"BASM");

    CAPRI's GAMS (captrd/national_supports.gms l. 716-719):

          p_result("IT000000",DCOW,rows,exanteT,"expertUp") $ ( p_ExpertSupprt("IT000000",DCOW,rows,exanteT,"PercentChange")
                                                                  $ (ORDT(ExAnteT) eq ORDT("2025")) $ (herdLevl(rows) or sameas(rows,"comi")))
             = 1.01 * (1+p_ExpertSupprt("IT000000",DCOW,rows,exanteT,"PercentChange")/100)
             * P_Result("IT000000",DCOW,rows,ExAnteT,"BASM");

    CAPRI's GAMS (captrd/national_supports.gms l. 915-917):

          p_result("CY000000",DCOW,herdLEVL,exanteT,"expertLo") $ p_ExpertSupprt("CY000000",DCOW,herdLEVL,exanteT,"PercentChange")
             = .95 * (1+p_ExpertSupprt("CY000000",DCOW,herdLEVL,exanteT,"PercentChange")/100)
             * P_Result("CY000000",DCOW,herdLEVL,ExAnteT,"BASM");

    CAPRI's GAMS (captrd/national_supports.gms l. 918-920):

          p_result("CY000000",DCOW,herdLEVL,exanteT,"expertUp") $ p_ExpertSupprt("CY000000",DCOW,herdLEVL,exanteT,"PercentChange")
             = 1.05 * (1+p_ExpertSupprt("CY000000",DCOW,herdLEVL,exanteT,"PercentChange")/100)
             * P_Result("CY000000",DCOW,herdLEVL,ExAnteT,"BASM");

    CAPRI's GAMS (captrd/national_supports.gms l. 1343-1344):

          p_result("SK000000",DCOW,herdLEVL,exanteT,"expertLo") $ p_ExpertSupprt("SK000000",DCOW,herdLEVL,exanteT,"PercentChange")
             = .95 * (1+p_ExpertSupprt("SK000000",DCOW,herdLEVL,exanteT,"PercentChange")/100)* p_data("SK000000",DCOW,herdLEVL,"BASM");

    CAPRI's GAMS (captrd/national_supports.gms l. 1345-1346):

          p_result("SK000000",DCOW,herdLEVL,exanteT,"expertUp") $ p_ExpertSupprt("SK000000",DCOW,herdLEVL,exanteT,"PercentChange")
             = 1.05* (1+p_ExpertSupprt("SK000000",DCOW,herdLEVL,exAnteT,"PercentChange")/100)* p_data("SK000000",DCOW,herdLEVL,"BASM");

    Departures from CAPRI: the port multiplies the factor by (1 + PercentChange / 100) x BASM, CAPRI the factor by (1 + PercentChange / 100)
    first (the last digit may differ); the domain condition and the loops in the caller (national_supports.supports)."""
    return factor * ((1 + percent / 100) * basm)


def p_result_expertLo_BL4(support, basm):
    r"""p_result("BL400000", mAact, "LEVL", exanteT, "expertLo") without one: 95% of the support, at least a tenth of
    BASM.

    CAPRI's GAMS (captrd/national_supports.gms l. 405-408):

          p_result("BL400000",mAact,"LEVL",exanteT,"expertLo") $ (  P_Result("BL400000",mAact,"LEVL",ExAnteT,"Support")
                                                                  $ (not p_result("BL400000",mAact,"LEVL",exanteT,"expertLo"))
                                                                  $ P_Result("BL400000",mAact,"LEVL",ExAnteT,"BASM"))
             = .95 * max(P_Result("BL400000",mAact,"LEVL",ExAnteT,"Support"),0.1*P_Result("BL400000",mAact,"LEVL",ExAnteT,"BASM"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return .95 * max(support, .1 * basm)


def p_result_expertUp_BL4(support, lo):
    r"""p_result("BL400000", mAact, "LEVL", exanteT, "expertUp") without one: 105% of the support, at least the lower
    bound.

    CAPRI's GAMS (captrd/national_supports.gms l. 410-413):

          p_result("BL400000",mAact,"LEVL",exanteT,"expertUp") $ (  P_Result("BL400000",mAact,"LEVL",ExAnteT,"Support")
                                                                  $ (not p_result("BL400000",mAact,"LEVL",exanteT,"expertUp"))
                                                                  $ P_Result("BL400000",mAact,"LEVL",ExAnteT,"BASM"))
             = 1.05 * max(P_Result("BL400000",mAact,"LEVL",ExAnteT,"Support"),p_result("BL400000",mAact,"LEVL",exanteT,"expertLo"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return 1.05 * max(support, lo)


def p_ExpertSupprt_PercentChange_natDCOW(nat, nat_bas):
    r"""p_ExpertSupprt(country, DCOW, herdLevl, exante, "PercentChange") after 2020: the national source's dairy cows
    (RO: all cattle) from its base mean.

    CAPRI's GAMS (captrd/national_supports.gms l. 445-448):

          p_ExpertSupprt("DE000000",DCOW,herdLevl,exanteT,"PercentChange")
                                     $ ( p_natExpert("DE000000","DCOW","LEV1","20%BAS%")
                                       $ (ORDT(ExanteT) GT ORDT("2020")))
              =  p_natExpert("DE000000","DCOW","LEV1",exanteT) / p_natExpert("DE000000","DCOW","LEV1","20%BAS%")*100-100;

    CAPRI's GAMS (captrd/national_supports.gms l. 506-509):

          p_ExpertSupprt("DK000000",DCOW,herdLevl,exante,"PercentChange")
                                     $ ( p_natExpert("DK000000","DCOW","LEV1","20%BAS%")
                                       $ (ORDT(ExAnte) GT ORDT("2020")))
              =  p_natExpert("DK000000","DCOW","LEV1",exante) / p_natExpert("DK000000","DCOW","LEV1","20%BAS%")*100-100;

    CAPRI's GAMS (captrd/national_supports.gms l. 598-601):

          p_ExpertSupprt("ES000000",DCOW,herdLevl,exante,"PercentChange")
                                     $ ( p_natExpert("ES000000","DCOW","LEV1","20%BAS%")
                                       $ (ORDT(ExAnte) GT ORDT("2020")))
              =  p_natExpert("ES000000","DCOW","LEV1",exante) / p_natExpert("ES000000","DCOW","LEV1","20%BAS%")*100-100;

    CAPRI's GAMS (captrd/national_supports.gms l. 743-746):

          p_ExpertSupprt("NL000000",DCOW,herdLevl,exante,"PercentChange")
                                     $ ( p_natExpert("NL000000","DCOW","LEV1","20%BAS%")
                                       $ (ORDT(ExAnte) GT ORDT("2020")))
              =  p_natExpert("NL000000","DCOW","LEV1",exante) / p_natExpert("NL000000","DCOW","LEV1","20%BAS%")*100-100;

    CAPRI's GAMS (captrd/national_supports.gms l. 1050-1053):

          p_ExpertSupprt("EE000000",DCOW,herdLevl,exante,"PercentChange")
                                     $ ( p_natExpert("EE000000","DCOW","LEV1","20%BAS%")
                                       $ (ORDT(ExAnte) GT ORDT("2020")))
              =  p_natExpert("EE000000","DCOW","LEV1",exante) / p_natExpert("EE000000","DCOW","LEV1","20%BAS%")*100-100;

    CAPRI's GAMS (captrd/national_supports.gms l. 1101-1104):

          p_ExpertSupprt("HR000000",DCOW,herdLevl,exante,"PercentChange")
                                     $ ( p_natExpert("HR000000","DCOW","LEV1","20%BAS%")
                                       $ (ORDT(ExAnte) GT ORDT("2020")))
              =  p_natExpert("HR000000","DCOW","LEV1",exante) / p_natExpert("HR000000","DCOW","LEV1","20%BAS%")*100-100;

    CAPRI's GAMS (captrd/national_supports.gms l. 1128-1131):

          p_ExpertSupprt("LV000000",DCOW,herdLevl,exante,"PercentChange")
                                     $ ( p_natExpert("LV000000","DCOW","LEV1","20%BAS%")
                                       $ (ORDT(ExAnte) GT ORDT("2020")))
              =  p_natExpert("LV000000","DCOW","LEV1",exante) / p_natExpert("LV000000","DCOW","LEV1","20%BAS%")*100-100;

    CAPRI's GAMS (captrd/national_supports.gms l. 1169-1172):

          p_ExpertSupprt("LT000000",DCOW,herdLevl,exante,"PercentChange")
                                     $ ( p_natExpert("LT000000","DCOW","LEV1","20%BAS%")
                                       $ (ORDT(ExAnte) GT ORDT("2020")))
              =  p_natExpert("LT000000","DCOW","LEV1",exante) / p_natExpert("LT000000","DCOW","LEV1","20%BAS%")*100-100;

    CAPRI's GAMS (captrd/national_supports.gms l. 1231-1234):

          p_ExpertSupprt("RO000000",DCOW,herdLevl,exante,"PercentChange")
                                     $ ( p_natExpert("RO000000","CATT","LEV1","20%BAS%")
                                       $ (ORDT(ExAnte) GT ORDT("2020")))
              =  p_natExpert("RO000000","CATT","LEV1",exante) / p_natExpert("RO000000","CATT","LEV1","20%BAS%")*100-100;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return nat / nat_bas * 100 - 100


def p_ExpertSupprt_PercentChange_natCOMI(dcoh_levl_percent, dcoh_comi, dcoh_comi_basm):
    r"""p_ExpertSupprt(country, cols, "COMI", exante, "PercentChange") of the milk positions but the cows' after 2020:
    the new herd times the absolute dairy yield, from BASM.

    CAPRI's GAMS (captrd/national_supports.gms l. 455-459):

          p_ExpertSupprt("DE000000",cols,"COMI",exanteT,"PercentChange")
                                       $ ( (ORDT(ExanteT) GT ORDT("2020"))
                                         $ expertdairy_map(cols,"COMI") $ (not P_T_ActAgg(cols,"DCOW")) )
              = (100+p_ExpertSupprt("DE000000","DCOH","LEVL",exanteT,"PercentChange"))/100
              * p_ExpertSupprt("DE000000","DCOH","COMI",exanteT,"Absolute")/P_Result("DE000000","DCOH","COMI",ExanteT,"BASM")*100-100;

    CAPRI's GAMS (captrd/national_supports.gms l. 516-520):

          p_ExpertSupprt("DK000000",cols,"COMI",exante,"PercentChange")
                                       $ ((ORDT(ExAnte) GT ORDT("2020"))
                                         $ expertdairy_map(cols,"COMI") $ (not P_T_ActAgg(cols,"DCOW")) )
              = (100+p_ExpertSupprt("DK000000","DCOH","LEVL",exante,"PercentChange"))/100
              * p_ExpertSupprt("DK000000","DCOH","COMI",exante,"Absolute")/P_Result("DK000000","DCOH","COMI",Exante,"BASM")*100-100;

    CAPRI's GAMS (captrd/national_supports.gms l. 608-612):

          p_ExpertSupprt("ES000000",cols,"COMI",exante,"PercentChange")
                                       $ ( (ORDT(ExAnte) GT ORDT("2020"))
                                         $ expertdairy_map(cols,"COMI") $ (not P_T_ActAgg(cols,"DCOW")) )
              = (100+p_ExpertSupprt("ES000000","DCOH","LEVL",exante,"PercentChange"))/100
              * p_ExpertSupprt("ES000000","DCOH","COMI",exante,"Absolute")/P_Result("ES000000","DCOH","COMI",Exante,"BASM")*100-100;

    CAPRI's GAMS (captrd/national_supports.gms l. 753-757):

          p_ExpertSupprt("NL000000",cols,"COMI",exante,"PercentChange")
                                       $ ( (ORDT(ExAnte) GT ORDT("2020"))
                                         $ expertdairy_map(cols,"COMI") $ (not P_T_ActAgg(cols,"DCOW")) )
              = (100+p_ExpertSupprt("NL000000","DCOH","LEVL",exante,"PercentChange"))/100
              * p_ExpertSupprt("NL000000","DCOH","COMI",exante,"Absolute")/P_Result("NL000000","DCOH","COMI",Exante,"BASM")*100-100;

    CAPRI's GAMS (captrd/national_supports.gms l. 1060-1064):

          p_ExpertSupprt("EE000000",cols,"COMI",exante,"PercentChange")
                                       $ ( (ORDT(ExAnte) GT ORDT("2020"))
                                         $ expertdairy_map(cols,"COMI") $ (not P_T_ActAgg(cols,"DCOW")) )
              = (100+p_ExpertSupprt("EE000000","DCOH","LEVL",exante,"PercentChange"))/100
              * p_ExpertSupprt("EE000000","DCOH","COMI",exante,"Absolute")/P_Result("EE000000","DCOH","COMI",Exante,"BASM")*100-100;

    CAPRI's GAMS (captrd/national_supports.gms l. 1111-1115):

          p_ExpertSupprt("HR000000",cols,"COMI",exante,"PercentChange")
                                       $ ( (ORDT(ExAnte) GT ORDT("2020"))
                                         $ expertdairy_map(cols,"COMI") $ (not P_T_ActAgg(cols,"DCOW")) )
              = (100+p_ExpertSupprt("HR000000","DCOH","LEVL",exante,"PercentChange"))/100
              * p_ExpertSupprt("HR000000","DCOH","COMI",exante,"Absolute")/P_Result("HR000000","DCOH","COMI",Exante,"BASM")*100-100;

    CAPRI's GAMS (captrd/national_supports.gms l. 1138-1142):

          p_ExpertSupprt("LV000000",cols,"COMI",exante,"PercentChange")
                                       $ ( (ORDT(ExAnte) GT ORDT("2020"))
                                         $ expertdairy_map(cols,"COMI") $ (not P_T_ActAgg(cols,"DCOW")) )
              = (100+p_ExpertSupprt("LV000000","DCOH","LEVL",exante,"PercentChange"))/100
              * p_ExpertSupprt("LV000000","DCOH","COMI",exante,"Absolute")/P_Result("LV000000","DCOH","COMI",Exante,"BASM")*100-100;

    CAPRI's GAMS (captrd/national_supports.gms l. 1179-1183):

          p_ExpertSupprt("LT000000",cols,"COMI",exante,"PercentChange")
                                       $ ( (ORDT(ExAnte) GT ORDT("2020"))
                                         $ expertdairy_map(cols,"COMI") $ (not P_T_ActAgg(cols,"DCOW")) )
              = (100+p_ExpertSupprt("LT000000","DCOH","LEVL",exante,"PercentChange"))/100
              * p_ExpertSupprt("LT000000","DCOH","COMI",exante,"Absolute")/P_Result("LT000000","DCOH","COMI",Exante,"BASM")*100-100;

    CAPRI's GAMS (captrd/national_supports.gms l. 1241-1245):

          p_ExpertSupprt("RO000000",cols,"COMI",exante,"PercentChange")
                                       $ ( (ORDT(ExAnte) GT ORDT("2020"))
                                         $ expertdairy_map(cols,"COMI") $ (not P_T_ActAgg(cols,"DCOW")) )
              = (100+p_ExpertSupprt("RO000000","DCOH","LEVL",exante,"PercentChange"))/100
              * p_ExpertSupprt("RO000000","DCOH","COMI",exante,"Absolute")/P_Result("RO000000","DCOH","COMI",Exante,"BASM")*100-100;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return (100 + dcoh_levl_percent) / 100 * dcoh_comi / dcoh_comi_basm * 100 - 100


def p_ExpertSupprt_Absolute_SHGM(basm, shgm_percent):
    r"""p_ExpertSupprt(country, mrkKeyPos, SGMT / SGMI, exante, "Absolute"): BASM moved with SHGM's level (EE, LV).

    CAPRI's GAMS (captrd/national_supports.gms l. 1074-1078):

          p_ExpertSupprt("EE000000",mrkKeyPos,rows,exante,"Absolute")
                                       $ ( (ORDT(ExAnte) GT ORDT("2020"))
                                         $ (sameas(rows,"SGMT") or sameas(rows,"SGMI")))
              = P_Result("EE000000",mrkKeyPos,rows,Exante,"BASM")
              *(1+p_ExpertSupprt("EE000000","SHGM","LEVL",exante,"PercentChange")/100);

    CAPRI's GAMS (captrd/national_supports.gms l. 1152-1156):

          p_ExpertSupprt("LV000000",mrkKeyPos,rows,exante,"Absolute")
                                       $ ( (ORDT(ExAnte) GT ORDT("2020"))
                                         $ (sameas(rows,"SGMT") or sameas(rows,"SGMI")))
              = P_Result("LV000000",mrkKeyPos,rows,Exante,"BASM")
              *(1+p_ExpertSupprt("LV000000","SHGM","LEVL",exante,"PercentChange")/100);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return basm * (1 + shgm_percent / 100)


def p_ExpertSupprt_PercentChange_copy(percent):
    r"""p_ExpertSupprt(country, ., ., ., "PercentChange") taken over: IT's pork from the fattening pigs, PT's young pigs
    and young cattle from the sows and the growing cattle, SK's sheep and goat milk from SHGM.

    CAPRI's GAMS (captrd/national_supports.gms l. 651-653):

          p_ExpertSupprt("IT000000","GROF",rows,ExAnte,"Percentchange")
                                     $ (SAMEAS(rows,"PORK") or SAMEAS(rows,"YPIG") or SAMEAS(rows,"IPIG"))
              = p_ExpertSupprt("IT000000","PIGF","LEVL",ExAnte,"Percentchange");

    CAPRI's GAMS (captrd/national_supports.gms l. 816-817):

          p_ExpertSupprt("PT000000","GROF","YPIG",ExAnte,"Percentchange")
               = p_ExpertSupprt("PT000000","SOWS","YPIG",ExAnte,"Percentchange");

    CAPRI's GAMS (captrd/national_supports.gms l. 818-819):

          p_ExpertSupprt("PT000000","GROF","IPIG",ExAnte,"Percentchange")
               = p_ExpertSupprt("PT000000","SOWS","YPIG",ExAnte,"Percentchange");

    CAPRI's GAMS (captrd/national_supports.gms l. 834-835):

          p_ExpertSupprt("PT000000","GROF","YCOW",exante,"PercentChange")
              = p_ExpertSupprt("PT000000","GROF","ICOW",exante,"PercentChange");

    CAPRI's GAMS (captrd/national_supports.gms l. 836-837):

          p_ExpertSupprt("PT000000","GROF","ICAM",exante,"PercentChange")
              = p_ExpertSupprt("PT000000","GROF","YCAM",exante,"PercentChange");

    CAPRI's GAMS (captrd/national_supports.gms l. 838-839):

          p_ExpertSupprt("PT000000","GROF","ICAF",exante,"PercentChange")
              = p_ExpertSupprt("PT000000","GROF","YCAF",exante,"PercentChange");

    CAPRI's GAMS (captrd/national_supports.gms l. 1363-1366):

          p_ExpertSupprt("SK000000",mrkKeyPos,rows,exante,"PercentChange")
                                       $ ( (ORDT(ExAnte) GT ORDT("2020"))
                                         $ (sameas(rows,"SGMT") or sameas(rows,"SGMI")))
              = p_ExpertSupprt("SK000000","SHGM","LEVL",exante,"PercentChange");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return percent


def p_ExpertSupprt_AT_PIGF_PORK(support, bast):
    r"""p_ExpertSupprt("AT000000", "PIGF", "PORK", exAnteT, "Absolute"): 10% the support, 90% BAST.

    CAPRI's GAMS (captrd/national_supports.gms l. 292-296):

          p_ExpertSupprt("AT000000","PIGF",rows,exAnteT,"Absolute")
                                     $ ( P_Result("AT000000","PIGF",rows,ExAnteT,"Support") $ (sameas(rows,"PORK"))
                                       $ (calyea(exanteT) gt calyea("2020")))
              = .1*P_Result("AT000000","PIGF",rows,ExAnteT,"Support")
              + .9*P_Result("AT000000","PIGF",rows,ExAnteT,"BAST");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return .1 * support + .9 * bast


def p_ExpertSupprt_BL4_herds():
    r"""p_ExpertSupprt("BL400000", dcow, herdlevl, exanteT, "PercentChange") after 2020: constant.

    CAPRI's GAMS (captrd/national_supports.gms l. 374-376):

          p_ExpertSupprt("BL400000",dcow,herdlevl,exanteT,"PercentChange")
                                       $ (ORDT(ExanteT) GT ORDT("2020"))
              =  .01;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return .01


def p_ExpertSupprt_BL4_GROF_COMI(comi, levl):
    r"""p_ExpertSupprt("BL400000", "GROF", "COMI", EXANTET, "PercentChange") after %lst_daitar%: the cows' yield's and
    herd's changes added.

    CAPRI's GAMS (captrd/national_supports.gms l. 379-381):

          p_ExpertSupprt("BL400000","GROF","COMI",EXANTET,"PercentChange") $ (OrdT(exAnteT) gt OrdT("%lst_daitar%"))
              = p_ExpertSupprt("BL400000","DCOH","COMI",exanteT,"PercentChange")
              + p_ExpertSupprt("BL400000","DCOH","LEVL",exanteT,"PercentChange");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return comi + levl


def p_ExpertSupprt_DE_INDM_MAIF(pdata):
    r"""p_ExpertSupprt("DE000000", "INDM", "MAIF", exanteT, "Absolute") after the last ex-post year: its p_data.

    CAPRI's GAMS (captrd/national_supports.gms l. 421-423):

          p_ExpertSupprt("DE000000","INDM","MAIF",exanteT,"Absolute") $ ( sum(lst_exPostT,P_Result("DE000000","INDM","MAIF",Lst_ExpostT,"p_data"))
                                                                       $ (ORDT(ExanteT) GT OrdT("lst_exPostT")))
              = sum(lst_exPostT,P_Result("DE000000","INDM","MAIF",Lst_ExpostT,"p_data"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return pdata


def p_ExpertSupprt_NT2_INDM_MAIF(de_pdata, de_absolute, nt2, total):
    r"""p_ExpertSupprt(NT2est, "INDM", "MAIF", exanteT, "Absolute") of Germany's NUTS 2 regions: Germany's (p_data,
    else Absolute) by the regions' shares of the last ex-post year.

    CAPRI's GAMS (captrd/national_supports.gms l. 431-439):

          p_ExpertSupprt(NT2est,"INDM","MAIF",exanteT,"Absolute")
                    $ ( (ORDT(ExanteT) GT OrdT("Lst_Expost"))
                      $ map_rr("DE000000",NT2est)
                      $ sum((lst_exPost,NT2) $ map_rr("DE000000",NT2),P_Result(NT2,"INDM","MAIF",Lst_Expost,"p_data")))
              = ( P_Result("DE000000","INDM","MAIF",exanteT,"p_data")
                + p_ExpertSupprt("DE000000","INDM","MAIF",exanteT,"Absolute") $ (NOT P_Result("DE000000","INDM","MAIF",exanteT,"p_data")))
              * sum(lst_exPost,P_Result(NT2est,"INDM","MAIF",Lst_Expost,"p_data"))
              / sum((lst_exPost,NT2) $ map_rr("DE000000",NT2),P_Result(NT2,"INDM","MAIF",Lst_Expost,"p_data"))
              ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return (de_pdata or de_absolute) * nt2 / total


def p_ExpertSupprt_EL_COMI(absolute):
    r"""p_ExpertSupprt("EL000000", DCOW, "COMI", 2020, "Absolute"): 10% lower.

    CAPRI's GAMS (captrd/national_supports.gms l. 531-534):

          p_ExpertSupprt("EL000000",DCOW,"COMI",exante,"Absolute")
                                     $ ( p_ExpertSupprt("EL000000",DCOW,"COMI",exante,"Absolute")
                                       $ (ORDT(ExAnte) EQ ORDT("2020")))
              =    p_ExpertSupprt("EL000000",DCOW,"COMI",exante,"Absolute") *.9;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return absolute * .9


def p_ExpertSupprt_EL_floor(support, bast):
    r"""p_ExpertSupprt("EL000000", "PIGF" .LEVL / "GROF" .YPIG .IPIG, ExAnte, "Absolute"): the support, at least 20% of
    BAST.

    CAPRI's GAMS (captrd/national_supports.gms l. 549-552):

          p_ExpertSupprt("EL000000","PIGF","LEVL",ExAnte,"Absolute")
                                     $ (   (ORDT(ExAnte) GT OrdT("2030")))
              =  max(P_Result("EL000000","PIGF","LEVL",ExAnte,"Support"),
                     0.2*P_Result("EL000000","PIGF","LEVL",ExAnte,"BAST"));

    CAPRI's GAMS (captrd/national_supports.gms l. 569-573):

          p_ExpertSupprt("EL000000","GROF",rows,ExAnte,"Absolute")
                                     $ ( p_ExpertSupprt("EL000000","PIGF","LEVL",ExAnte,"Absolute")
                                     $ (SAMEAS(rows,"YPIG") or SAMEAS(rows,"IPIG")))
               = max(P_Result("EL000000","GROF",rows,ExAnte,"Support") ,
                     .2*P_Result("EL000000","GROF",rows,ExAnte,"BAST") );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return max(support, .2 * bast)


def p_ExpertSupprt_EL_PIGF_HERD(levl, days):
    r"""p_ExpertSupprt("EL000000", "PIGF", "HERD", ExAnte, "Absolute"): the level times the days over 365.

    CAPRI's GAMS (captrd/national_supports.gms l. 556-560):

          p_ExpertSupprt("EL000000","PIGF","HERD",ExAnte,"Absolute")
                                     $ ( p_ExpertSupprt("EL000000","PIGF","LEVL",ExAnte,"Absolute")
                                       $ P_Result("EL000000","PIGF","DAYS",ExAnte,"Support") )
              =  p_ExpertSupprt("EL000000","PIGF","LEVL",ExAnte,"Absolute")
              *  P_Result("EL000000","PIGF","DAYS",ExAnte,"Support")/365;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return levl * days / 365.0


def p_ExpertSupprt_EL_TRustlevl(year, lst_exante):
    r"""p_ExpertSupprt("EL000000", "PIGF" / "GROF", ., ExAnte, "TRustlevl") after 2030: from 1 down to .1 by the last
    ex-ante year.

    CAPRI's GAMS (captrd/national_supports.gms l. 563-566):

          p_ExpertSupprt("EL000000","PIGF",herdLevl,ExAnte,"TRustlevl")
                                     $  (    p_ExpertSupprt("EL000000","PIGF",herdLevl,ExAnte,"Absolute")
                                     $    (ORDT(ExAnte) GT OrdT("2030")))
              = 1. + (ORDT(ExAnte) - ORDT("2030"))* (.1-1)/(OrdT('lst_exAnte')- ORDT("2030")) ;

    CAPRI's GAMS (captrd/national_supports.gms l. 575-579):

          p_ExpertSupprt("EL000000","GROF",rows,ExAnte,"TRustlevl")
                                     $ (  (SAMEAS(rows,"YPIG") or SAMEAS(rows,"IPIG"))
                                     $   p_ExpertSupprt("EL000000","GROF",rows,ExAnte,"Absolute")
                                     $    (ORDT(ExAnte) GT OrdT("2030")))
               = 1 + (ORDT(ExAnte) - ORDT("2030"))* (.1-1)/(OrdT('lst_exAnte')- ORDT("2030"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return 1. + (year - 2030) * (.1 - 1) / (lst_exante - 2030)


def p_ExpertSupprt_IT_PIGF(bast, n):
    r"""p_ExpertSupprt("IT000000", "PIGF", herdLevl, EXANTET, "Absolute") after 2020: BAST growing 0.25% a year over
    n = ORDT(exanteT) - ORDT("BAST").

    CAPRI's GAMS (captrd/national_supports.gms l. 663-664):

          p_ExpertSupprt("IT000000","PIGF",herdLevl,EXANTET,"absolute") $ (P_DATA("IT000000","PIGF",herdLevl,"BAST") $ (Ordt(ExAnteT) gt Ordt("2020")))
              = P_DATA("IT000000","PIGF",herdLevl,"BAST")*1.0025**(ORDT(exanteT)-ORDT("BAST"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return bast * 1.0025 ** n


def p_ExpertSupprt_IT_SCOW(basm, n):
    r"""p_ExpertSupprt("IT000000", "SCOW", herdLevl, EXANTET, "Absolute") after 2020: BASM falling 1.5% a year over
    n = ORDT(exanteT) - ORDT("BAS").

    CAPRI's GAMS (captrd/national_supports.gms l. 677-679):

          p_ExpertSupprt("IT000000","SCOW",herdLevl,EXANTET,"absolute")
              $ (P_DATA("IT000000","SCOW",herdLevl,"BASM") $ (Ordt(ExAnteT) gt Ordt("2020")))
              = P_DATA("IT000000","SCOW",herdLevl,"BASM")*(1-.015)**(ORDT(exanteT)-ORDT("BAS"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return basm * (1 - .015) ** n


def p_ExpertSupprt_IT_2025(percent_2020, percent_2030):
    r"""p_ExpertSupprt("IT000000", DCOW, rows, 2025, "percentChange"): the mean of 2020's and 2030's, 1% lower.

    CAPRI's GAMS (captrd/national_supports.gms l. 707-710):

          p_ExpertSupprt("IT000000",DCOW,rows,exanteT,"percentChange")
             $ (   p_ExpertSupprt("IT000000",DCOW,rows,"2020","percentChange") $ p_ExpertSupprt("IT000000",DCOW,rows,"2030","percentChange")
               $   (Ordt(ExAnteT) eq Ordt("2025")) $ (herdLevl(rows) or sameas(rows,"comi")))
             =  (p_ExpertSupprt("IT000000",DCOW,rows,"2020","percentChange")+p_ExpertSupprt("IT000000",DCOW,rows,"2030","percentChange"))/2*.99;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return (percent_2020 + percent_2030) / 2 * .99


def p_ExpertSupprt_PercentChange_support(support, basm):
    r"""p_ExpertSupprt(country, ., ., ., "PercentChange"): the support's change from BASM (NL's fattening days, MT's
    sheep and goat meat).

    CAPRI's GAMS (captrd/national_supports.gms l. 767-771):

          p_ExpertSupprt("NL000000","PIGF","DAYS",exante,"PercentChange")
                                     $ ( P_Result("NL000000","PIGF","DAYS",ExAnte,"Support")
                                       $ P_Result("NL000000","PIGF","DAYS",ExAnte,"BASM")
                                       $ (ORDT(ExAnte) GT ORDT("2010")))
              = P_Result("NL000000","PIGF","DAYS",ExAnte,"Support")/P_Result("NL000000","PIGF","DAYS",ExAnte,"BASM")*100-100;

    CAPRI's GAMS (captrd/national_supports.gms l. 1207-1210):

          p_ExpertSupprt("MT000000","GROF","SGMT",exAnteT,"PercentChange")
                                     $ ( P_Result("MT000000","GROF","SGMT",ExAnteT,"Support")
                                       $ P_Result("MT000000","GROF","SGMT",ExAnteT,"BASM"))
              = P_Result("MT000000","GROF","SGMT",ExAnteT,"Support")/P_Result("MT000000","GROF","SGMT",ExAnteT,"BASM")*100-100;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return support / basm * 100 - 100


def p_ExpertSupprt_PT_PIGF_PORK(n):
    r"""p_ExpertSupprt("PT000000", "PIGF", "PORK", ExAnte, "Percentchange"): falling 0.2% a year over
    n = Ordt(ExAnte) - Ordt("BAS").

    CAPRI's GAMS (captrd/national_supports.gms l. 800-801):

          p_ExpertSupprt("PT000000","PIGF","PORK",ExAnte,"Percentchange")
               = ((1.- 0.002)**(Ordt(ExAnte)-Ordt("BAS")))*100.-100.  ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return ((1. - 0.002) ** n) * 100. - 100.


def p_ExpertSupprt_PT_SOWS_YPIG(support, basm, year, base, lst_exante):
    r"""p_ExpertSupprt("PT000000", "SOWS", "YPIG", ExAnte, "Percentchange"): the support's change, at most 20% by the
    last ex-ante year.

    CAPRI's GAMS (captrd/national_supports.gms l. 808-811):

          p_ExpertSupprt("PT000000","SOWS","YPIG",ExAnte,"Percentchange")
               = MIN(P_Result("PT000000","SOWS","YPIG",exante,"Support")/P_Result("PT000000","SOWS","YPIG",exante,"BASM"),
                     1.+0.2*(MAX(OrdT("BAS")+1,OrdT(ExAnte))-OrdT("BAS"))/(OrdT("lst_exAnte")-OrdT("BAS")))
               * 100.-100.  ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return min(support / basm, 1. + 0.2 * (max(base + 1, year) - base) / (lst_exante - base)) * 100. - 100.


def p_ExpertSupprt_PT_GROF_cows(cows):
    r"""p_ExpertSupprt("PT000000", "GROF", ICOW / YCAM / YCAF, exante, "PercentChange"): the cows' level changes
    weighted by their BASM levels.

    cows: (PercentChange, BASM) of CowsAct's levels, in order.

    CAPRI's GAMS (captrd/national_supports.gms l. 823-832):

          p_ExpertSupprt("PT000000","GROF",rows,exante,"PercentChange")
                                    $ (   (   SAMEAS(ROWS,"ICOW")
                                           or SAMEAS(ROWS,"YCAM")
                                           or SAMEAS(ROWS,"YCAF"))
                                        $ SUM(CowsAct, P_Result("PT000000",CowsAct,"LEVL",exante,"BASM")
                                                       *P_Result("PT000000",CowsAct,ROWS,exante,"BASM"))  )

              = SUM(CowsAct, p_ExpertSupprt("PT000000",CowsAct,"LEVL",exante,"PercentChange")
                         *   P_Result("PT000000",CowsAct,"LEVL",exante,"BASM"))
              / SUM(CowsAct, P_Result("PT000000",CowsAct,"LEVL",exante,"BASM"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return sum(p * b for p, b in cows) / sum(b for p, b in cows)


def p_ExpertSupprt_CY_PercentChange(absolute, absolute_2020, basm):
    r"""p_ExpertSupprt("CY000000", dcow, herdLevl, exAnteT, "PercentChange") after 2020: the absolute's change plus 90%
    of 2020's.

    CAPRI's GAMS (captrd/national_supports.gms l. 892-900):

          p_ExpertSupprt("CY000000",dcow,herdLevl,exAnteT,"PercentChange")
                                     $ ( P_Result("CY000000",dcow,herdLevl,ExAnteT,"Support")
                                       $ P_Result("CY000000",dcow,herdLevl,ExAnteT,"BASM")
                                       $ (ORDT(exanteT) gt ORDT("2020")))
        *       Absolute supports derived from dairy targets and neglecting recent surge, are converted into percent format:
              = p_ExpertSupprt("CY000000",dcow,herdLevl,ExAnteT,"absolute")/P_Result("CY000000",dcow,herdLevl,ExAnteT,"BASM")*100-100
        *       Correct the series of projections upward according to the recent increase in dcow population (40% in 2012->19).
        *       THe 2020 value is based on Agriprod data and we assume that 90% of this increase is permanent:
              + (p_ExpertSupprt("CY000000",dcow,herdLevl,"2020","absolute")/P_Result("CY000000",dcow,herdLevl,ExAnteT,"BASM")*100-100)*.9 ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return absolute / basm * 100 - 100 + (absolute_2020 / basm * 100 - 100) * .9


def p_ExpertSupprt_CY_absolute_removed():
    r"""p_ExpertSupprt("CY000000", dcow, herdLevl, exAnteT, "absolute") with that PercentChange: removed.

    CAPRI's GAMS (captrd/national_supports.gms l. 905-908):

          p_ExpertSupprt("CY000000",dcow,herdLevl,exAnteT,"absolute")
                                    $ (p_ExpertSupprt("CY000000",dcow,herdLevl,exAnteT,"PercentChange")
                                       $ (ORDT(exanteT) gt ORDT("2020")))
              = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return 0.0


def P_Result_support_CS(support, bas, bast, year, base_year, bast_year, lst_exante):
    r"""P_Result("CS000000", DCOW, HerdLevl, ExAnteT, "support"): at least 90% a year of BAS (and of BAST, the
    smaller), and at least a linear decline to 20% of them by Lst_exAnte (expert_support.gms l. 794-807's formula).

    CAPRI's GAMS (captrd/national_supports.gms l. 952-966):

         P_Result("CS000000",DCOW,HerdLevl,ExAnteT,"support")
               = max( P_Result("CS000000",DCOW,HerdLevl,ExAnteT,"support"),
                     (P_DATA("CS000000",DCOW,herdLevl,"BAS") *.9**(OrdT(ExanteT)-OrdT("BAS")))
                      $ (not P_DATA("CS000000",DCOW,herdLevl,"BAST")),
                     min( P_DATA("CS000000",DCOW,herdLevl,"BAST")*.9**(OrdT(ExanteT)-OrdT("BAST")),
                          P_DATA("CS000000",DCOW,herdLevl,"BAS")*.9**(OrdT(ExanteT)-OrdT("BAS")))
                      $ (    P_DATA("CS000000",DCOW,herdLevl,"BAST")),
                    (P_DATA("CS000000",DCOW,herdLevl,"BAS") *(1-.8*(OrdT(ExanteT)-OrdT("BAS"))
                                                           /(OrdT("Lst_exAnte")-OrdT("BAS"))))
                      $ (not P_DATA("CS000000",DCOW,herdLevl,"BAST")) ,
                     min( P_DATA("CS000000",DCOW,herdLevl,"BAST") *(1- .8*(OrdT(ExanteT)-OrdT("BAST"))
                                                                  /(OrdT("Lst_exAnte")-OrdT("BAST"))),
                          P_DATA("CS000000",DCOW,herdLevl,"BAS")  *(1-.8*(OrdT(ExanteT)-OrdT("BAS"))
                                                                 /(OrdT("Lst_exAnte")-OrdT("BAS"))))
                      $      P_DATA("CS000000",DCOW,herdLevl,"BAST"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    if bast:
        f1 = min(bast * .9 ** (year - bast_year), bas * .9 ** (year - base_year))
        f2 = min(bast * (1 - .8 * (year - bast_year) / (lst_exante - bast_year)),
                 bas * (1 - .8 * (year - base_year) / (lst_exante - base_year)))
    else:
        f1 = bas * .9 ** (year - base_year)
        f2 = bas * (1 - .8 * (year - base_year) / (lst_exante - base_year))
    return max(support, f1, f2)


def p_ExpertSupprt_CS_Absolute(support, basm, year, lst_exante):
    r"""p_ExpertSupprt("CS000000", expertdairy_map, exanteT, "Absolute") after 2040: the support moved back towards
    BASM, by up to 30% at the last ex-ante year.

    CAPRI's GAMS (captrd/national_supports.gms l. 971-979):

          p_ExpertSupprt("CS000000",cols,rows,exanteT,"Absolute")
                                     $ ( P_Result("CS000000",cols,rows,ExanteT,"Support")
                                       $ P_Result("CS000000",cols,rows,ExanteT,"BASM")
                                       $ (OrdT(ExAnteT) gt OrdT("2040"))
                                       $ expertdairy_map(cols,rows) )
              = P_Result("CS000000",cols,rows,ExanteT,"Support")
              - (P_Result("CS000000",cols,rows,ExanteT,"Support")-P_Result("CS000000",cols,rows,ExanteT,"BASM"))
              * .3*((MAX(OrdT("2030")+1,OrdT(ExAnteT))-OrdT("2030"))
                   /(OrdT("lst_exAnte")-OrdT("2030")));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return support - (support - basm) * .3 * ((max(2031, year) - 2030) / (lst_exante - 2030))


def p_ExpertSupprt_BA_POUF(support, n, from_2020):
    r"""p_ExpertSupprt("BA000000", "pouf", HerdLevl, exanteT, "Absolute"): the support falling 1% a year over
    n = OrdT(ExanteT) - OrdT("BAST"), from 2020.

    CAPRI's GAMS (captrd/national_supports.gms l. 992-995):

          p_ExpertSupprt("BA000000","pouf",HerdLevl,exanteT,"Absolute")
                         =  P_Result("BA000000","pouf",HerdLevl,ExAnteT,"support")
        *mok lower pouf level/herd for years from 2020 onward
                      * (0.99**(OrdT(ExanteT)-OrdT("BAST")))  $ (ORDT(ExAnteT) GE ORDT("2020"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return support * (0.99 ** n) * from_2020


def p_ExpertSupprt_EE_COMI(absolute):
    r"""p_ExpertSupprt("EE000000", DCOW, "COMI", 2020, "Absolute"): 5% higher.

    CAPRI's GAMS (captrd/national_supports.gms l. 1021-1024):

          p_ExpertSupprt("EE000000",DCOW,"COMI",exante,"Absolute")
                                     $ ( p_ExpertSupprt("EE000000",DCOW,"COMI",exante,"Absolute")
                                       $ (ORDT(ExAnte) EQ ORDT("2020")))
              =    p_ExpertSupprt("EE000000",DCOW,"COMI",exante,"Absolute") *1.05;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return absolute * 1.05


def p_ExpertSupprt_RO_MAIF(bast, basm):
    r"""p_ExpertSupprt("RO000000", "MAIF", "LEVL", EXANTET, "PercentChange"): BAST's change from BASM.

    CAPRI's GAMS (captrd/national_supports.gms l. 1260-1261):

          p_ExpertSupprt("RO000000","MAIF","LEVL",EXANTET,"PercentChange") $ P_DATA("RO000000","MAIF","LEVL","BASM")
                                            = (P_DATA("RO000000","MAIF","LEVL","BAST")/P_DATA("RO000000","MAIF","LEVL","BASM")-1.)*100;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return (bast / basm - 1.) * 100


def p_ExpertSupprt_NO_COMI(dgagri1, dgagri1_lst, basm, year, lst, base):
    r"""p_ExpertSupprt("NO000000", cols, "COMI", ExAnteT, "Absolute") of the milk positions but the cows' after 2020:
    DGAgri1, after %lst_dgagri% plus its last value times its change from BASM extrapolated.

    CAPRI's GAMS (captrd/national_supports.gms l. 1421-1427):

          p_ExpertSupprt("NO000000",cols,"COMI",ExAnteT,"Absolute") $ ((ORDT(ExAnteT) gt OrdT("2020")) $ expertdairy_map(cols,"COMI") $ (not P_T_ActAgg(cols,"DCOW")))
              = P_Result("NO000000",cols,"COMI",ExAnteT,"DGAgri1")
              + P_Result("NO000000",cols,"COMI","%lst_dgagri%","DGAgri1")
             *[(P_Result("NO000000",cols,"COMI","%lst_dgagri%","DGAgri1")
               /P_Result("NO000000",cols,"COMI","%lst_dgagri%","BASM"))**((OrdT(exAnteT)-OrdT("%lst_dgagri%"))
                                                                         /(OrdT("%lst_dgagri%")-OrdT("BAS")))]
              $ (OrdT(exAnteT) gt OrdT("%lst_dgagri%"));

    Departures from CAPRI: the port adds the term only where %lst_dgagri%'s DGAgri1 is nonzero (it is zero otherwise); the domain condition
    and the loops in the caller (national_supports.supports)."""
    v = dgagri1
    if year > lst and dgagri1_lst:
        v += dgagri1_lst * ((dgagri1_lst / basm) ** ((year - lst) / (lst - base)))
    return v


def p_ExpertSupprt_NO_mrkKeyPos(dgagri1, dgagri1_lst, after):
    r"""p_ExpertSupprt("NO000000", mrkKeyPos, PORK / EGGS / POUM, ExAnteT, "Absolute"): DGAgri1, after %lst_dgagri% plus
    its last value.

    CAPRI's GAMS (captrd/national_supports.gms l. 1444-1448):

          p_ExpertSupprt("NO000000",mrkKeyPos,rows,ExAnteT,"Absolute")
              $ ( (ORDT(ExAnteT) gt OrdT("2020"))
                $ (sameas(rows,"PORK") or sameas(rows,"EGGS") or sameas(rows,"POUM") ))
              = P_Result("NO000000",mrkKeyPos,rows,ExAnteT,"DGAgri1")
              + P_Result("NO000000",mrkKeyPos,rows,"%lst_dgagri%","DGAgri1") $ (OrdT(exAnteT) gt OrdT("%lst_dgagri%"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return dgagri1 + dgagri1_lst * after


def p_ExpertSupprt_TUR(dgagri1, dgagri1_lst, basm, year, lst, base):
    r"""p_ExpertSupprt("TUR", mrkKeyPos, POUM / SGMT, ExAnteT, "Absolute") after 2020: DGAgri1, after %lst_dgagri% plus
    its last value extrapolated linearly from BASM.

    CAPRI's GAMS (captrd/national_supports.gms l. 1473-1479):

          p_ExpertSupprt("TUR",mrkKeyPos,rows,ExAnteT,"Absolute") $ ((ORDT(ExAnteT) gt OrdT("2020")) $ (sameas(rows,"POUM") or sameas(rows,"SGMT") ) )
              = P_Result("TUR",mrkKeyPos,rows,ExAnteT,"DGAgri1")
              +[P_Result("TUR",mrkKeyPos,rows,"%lst_dgagri%","DGAgri1")
               +(OrdT(exAnteT)-OrdT("%lst_dgagri%"))
               *(P_Result("TUR",mrkKeyPos,rows,"%lst_dgagri%","DGAgri1")-P_Result("TUR",mrkKeyPos,rows,"%lst_dgagri%","BASM"))
                /(OrdT("%lst_dgagri%")-OrdT("BAS"))]
              $ (OrdT(exAnteT) gt OrdT("%lst_dgagri%"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (national_supports.supports)."""
    return dgagri1 + (dgagri1_lst + (year - lst) * (dgagri1_lst - basm) / (lst - base)) * (year > lst)
