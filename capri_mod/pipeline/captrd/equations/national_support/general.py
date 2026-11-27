r"""CAPTRD's national expert supports of all countries: the percentage changes, trust levels and absolute supports
(moved from capri_mod/pipeline/captrd/equations/national_supports.py as they were, 26 November 2026).
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
