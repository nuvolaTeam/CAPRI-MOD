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
