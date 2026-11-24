r"""CAPTRD's statements of captrd/adjust_to_biof_supports.gms (CAPRI star 3.0, with %use_KWS_supports% off; included by
define_stats_and_supports.gms l. 589-598 on "support" and define_EU_supports.gms l. 387 on "DGAgri1"): the feedstocks'
supports scaled so that the experts' biofuel demand changes end up in their production, as named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). capri_mod/pipeline/captrd/final_supports.py (biof_adjust) holds the loops over
the member states, the feedstocks and the ex-ante year, the conditions and the "series" copy, and calls them; the
arithmetic is the port's, so the supports are unchanged. n is OrdT(ExAnte) - OrdT("BAS"), the years since the base
year, of the lower limits' yearly decline .98**n.
"""
from __future__ import annotations


def MSest(biof_experts):
    r"""MSest: the member state's Expert BIOF of a feedstock in the year above 2E-13.

    biof_experts: Expert BIOF of the feedstocks bioStock. Returns True where the member state is adjusted.

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 20-20):

            MSest(MS)     = NO;

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 21-21):

            MSest(MS)  $ SUM((biostock) $  (P_Result(MS,"BIOF",bioStock,exAnte,"Expert") GT 2E-13),1) = YES;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.biof_adjust)."""
    return any(v > 2e-13 for v in biof_experts)


def P_PrdAdj_bioStock(grof, mapr, impt):
    r"""P_PrdAdj(MSest, bioStock): the share of a biofuel change met by production, 0.8 x production (GROF, else MAPR)
    against 0.2 x imports, at BASM of %lst_dgagri%.

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 27-36):

            P_PrdAdj(MSest,biostock)$  (  P_Result(MSest,"GROF",biostock,"%lst_dgagri%","BASM")
                                       +  P_Result(MSest,"MAPR",biostock,"%lst_dgagri%","BASM")
                                       +  P_Result(MSest,"IMPT",biostock,"%lst_dgagri%","BASM"))
                                    =  0.8 * (  P_Result(MSest,"GROF",biostock,"%lst_dgagri%","BASM")
                                             +  P_Result(MSest,"MAPR",biostock,"%lst_dgagri%","BASM")
                                             $ (not P_Result(MSest,"GROF",biostock,"%lst_dgagri%","BASM")))
                                    /( 0.8 * (  P_Result(MSest,"GROF",biostock,"%lst_dgagri%","BASM")
                                             +  P_Result(MSest,"MAPR",biostock,"%lst_dgagri%","BASM")
                                             $ (not P_Result(MSest,"GROF",biostock,"%lst_dgagri%","BASM")))
                                     + 0.2 * P_Result(MSest,"IMPT",biostock,"%lst_dgagri%","BASM"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.biof_adjust)."""
    prd = 0.8 * (grof + (mapr if not grof else 0.0))
    return prd / (prd + 0.2 * impt)


def P_LowLim_bioStock():
    r"""P_LowLim(MSest, bioStock): the feedstocks' lower limit, a share of BASM.

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 37-37):

            P_LowLim(MSest,biostock)=0.9;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.biof_adjust)."""
    return 0.9


def P_PrdAdj_oils(grof, impt):
    r"""P_PrdAdj(MSest, O) of the seeds of the oil feedstocks: 0.9 x GROF against 0.1 x IMPT, at BASM.

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 38-43):

            P_PrdAdj(MSest,O) $ ( SUM(PRCD(bioStockOilP,O),1.)
                                $ ( P_Result(MSest,"GROF",O,"%lst_dgagri%","BASM")
                                  + P_Result(MSest,"IMPT",O,"%lst_dgagri%","BASM")))
                                    =  0.9 * P_Result(MSest,"GROF",O,"%lst_dgagri%","BASM")
                                    /( 0.9 * P_Result(MSest,"GROF",O,"%lst_dgagri%","BASM")
                                     + 0.1 * P_Result(MSest,"IMPT",O,"%lst_dgagri%","BASM")) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.biof_adjust)."""
    return 0.9 * grof / (0.9 * grof + 0.1 * impt)


def P_LowLim_oils():
    r"""P_LowLim(MSest, O) of the seeds of the oil feedstocks.

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 44-44):

            P_LowLim(MSest,O) $ SUM(PRCD(bioStockOilP,O),1.) =0.8;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.biof_adjust)."""
    return 0.8


def P_PrdAdj_sugar():
    r"""P_PrdAdj(MSest, "SUGB" / "SUGA"): sugar's changes met by production in full.

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 45-45):

            P_PrdAdj(MSest,"SUGB")=1.0;

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 46-46):

            P_PrdAdj(MSest,"SUGA")=1.0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.biof_adjust)."""
    return 1.0


def P_LowLim_SUGB():
    r"""P_LowLim(MSest, "SUGB").

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 47-47):

            P_LowLim(MSest,"SUGB")=0.5;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.biof_adjust)."""
    return 0.5


def P_UppLim_oseeds():
    r"""P_UppLim(MSest, oseeds): the oilseeds' upper limit as an annual change factor.

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 49-49):

            P_UppLim(MSest,oseeds)=1.2;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.biof_adjust)."""
    return 1.2


def P_Result_series(value):
    r"""P_Result(MSest, S_colsEst, S_rowsEst, exAnte, "series"): the supports before the adjustment.

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 56-56):

            P_Result(MSest,S_colsEst,S_rowsEst,exAnte,"series") = P_Result(MSest,S_colsEst,S_rowsEst,exAnte,%1) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.biof_adjust)."""
    return value


def P_Result_GROF_MAPR_bioStock(value, basm, lowlim, n, biof_expert, biof, prdadj):
    r"""P_Result(MSest, "GROF" / "MAPR", bioStock, exAnte): the support plus the expert's BIOF change times P_PrdAdj, at
    least BASM x P_LowLim x .98**n.

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 61-66):

            P_Result(MSest,"GROF",bioStock,exAnte,%1) $ P_Result(MSest,"GROF",bioStock,exAnte,%1)
               =  MAX(P_Result(MSest,"GROF",bioStock,exAnte,"BASM")*P_lowLim(MSest,bioStock)* .98**(OrdT(ExAnte)-OrdT("BAS")),
                      P_Result(MSest,"GROF",bioStock,exAnte,%1)
                    + (  P_Result(MSest,"BIOF",bioStock,exAnte,"Expert")
                       - P_Result(MSest,"BIOF",bioStock,exAnte,%1)) * P_PrdAdj(MSest,bioStock)
                      );

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 68-73):

            P_Result(MSest,"MAPR",bioStock,exAnte,%1) $ P_Result(MSest,"MAPR",bioStock,exAnte,%1)
               =  MAX(P_Result(MSest,"MAPR",bioStock,exAnte,"BASM")*P_lowLim(MSest,bioStock)* .98**(OrdT(ExAnte)-OrdT("BAS")),
                      P_Result(MSest,"MAPR",bioStock,exAnte,%1)
                    + (  P_Result(MSest,"BIOF",bioStock,exAnte,"Expert")
                       - P_Result(MSest,"BIOF",bioStock,exAnte,%1)) * P_PrdAdj(MSest,bioStock)
                      );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.biof_adjust)."""
    return max(basm * lowlim * 0.98 ** n, value + (biof_expert - biof) * prdadj)


def P_Result_Fst_exAnte(value, basm):
    r"""P_Result(MSest, "GROF" / "MAPR", bioStock, Fst_exAnte): at most 30% above BASM.

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 78-81):

            P_Result(MSest,COLS,bioStock,Fst_exAnte,%1) $ (  (SAMEAS(COLS,"GROF") or SAMEAS(COLS,"MAPR"))
                                                                  $ P_Result(MSest,COLS,bioStock,Fst_exAnte,%1) )
               = Min(P_Result(MSest,COLS,bioStock,Fst_exAnte,%1) ,
                     P_Result(MSest,COLS,bioStock,Fst_exAnte,"BASM")*1.3);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.biof_adjust)."""
    return min(value, basm * 1.3)


def P_Result_DOMM_bioStock(value, basm, lowlim, biof_expert, biof):
    r"""P_Result(MSest, "DOMM", bioStock, exAnte): the BIOF change passed on in full, at least BASM x P_LowLim.

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 86-91):

            P_Result(MSest,"DOMM",bioStock,exAnte,%1) $ P_Result(MSest,"DOMM",bioStock,exAnte,%1)
               =  MAX(P_Result(MSest,"DOMM",bioStock,exAnte,"BASM")*P_lowLim(MSest,bioStock),
                      P_Result(MSest,"DOMM",bioStock,exAnte,%1)
                    + (  P_Result(MSest,"BIOF",bioStock,exAnte,"Expert")
                       - P_Result(MSest,"BIOF",bioStock,exAnte,%1))
                      );

    Departures from CAPRI: the port adds the expert's BIOF to the value, then subtracts the support's (CAPRI subtracts first, the last digit may
    differ); the domain condition and the loops over the sets in the caller (final_supports.biof_adjust)."""
    return max(basm * lowlim, value + biof_expert - biof)


def P_Result_PRCM_Oseeds(value, basm, lowlim, n, oils):
    r"""P_Result(MSest, "PRCM", Oseeds, exAnte): the oils' MAPR change over their processing yields added, at least BASM
    x P_LowLim x .98**n.

    oils: (MAPR, its "series", Proc_Yields) of the seed's biodiesel oils, in the caller's order.

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 96-105):

            P_Result(MSest,"PRCM",Oseeds,exAnte,%1) $ (  SUM(SED_TO_OIL(Oseeds,biostock) $ BIO_PRCD("BIOD",biostock),
                                                                       P_Result(MSest,"MAPR",biostock,ExAnte,%1))
                                                              $ P_Result(MSest,"PRCM",Oseeds,exAnte,%1))

               =  MAX(P_Result(MSest,"PRCM",Oseeds,exAnte,"BASM")*P_lowLim(MSest,Oseeds)* .98**(OrdT(ExAnte)-OrdT("BAS")),
                      P_Result(MSest,"PRCM",Oseeds,exAnte,%1)
                    + SUM(SED_TO_OIL(Oseeds,biostock) $ BIO_PRCD("BIOD",biostock),
                                                (  P_Result(MSest,"MAPR",biostock,exAnte,%1)
                                                 - P_Result(MSest,"MAPR",biostock,exAnte,"series"))
                                               /Proc_Yields(biostock))                                              ) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.biof_adjust)."""
    return max(basm * lowlim * 0.98 ** n, value + sum((m - s) / p for m, s, p in oils))


def P_Result_GROF_Oseeds(value, bast, basm, upplim, n_bast, n, lowlim, prcm, series, prdadj):
    r"""P_Result(MSest, "GROF", Oseeds, exAnte): the PRCM change times P_PrdAdj added, at least BASM x P_LowLim x .98**n,
    at most BAST (else BASM) x P_UppLim to the power of the years since BAST (else BAS).

    n_bast: OrdT(ExAnte) - OrdT("BAST").

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 109-122):

            P_Result(MSest,"GROF",Oseeds,exAnte,%1) $ (  SUM(SED_TO_OIL(Oseeds,biostock),BIO_PRCD("BIOD",biostock))
                                                              $ P_Result(MSest,"PRCM",Oseeds,exAnte,%1)
                                                              $ P_Result(MSest,"GROF",Oseeds,exAnte,%1)
                                                              $ P_Result(MSest,"GROF",Oseeds,exAnte,"BASM"))

               =  MIN( (P_Result(MSest,"GROF",Oseeds,exAnte,"BAST")
                      + P_Result(MSest,"GROF",Oseeds,exAnte,"BASM")
                      $ (not P_Result(MSest,"GROF",Oseeds,exAnte,"BAST")))
                      * P_uppLim(MSest,Oseeds)**(OrdT(Exante)-OrdT("BAST") $ (    P_Result(MSest,"GROF",Oseeds,exAnte,"BAST"))
                                                             -OrdT("BAS")  $ (not P_Result(MSest,"GROF",Oseeds,exAnte,"BAST"))),
                      MAX(P_Result(MSest,"GROF",Oseeds,exAnte,"BASM")*P_lowLim(MSest,Oseeds)* .98**(OrdT(ExAnte)-OrdT("BAS")),
                             P_Result(MSest,"GROF",Oseeds,exAnte,%1)
                        + (  P_Result(MSest,"PRCM",Oseeds,exAnte,%1)
                           - P_Result(MSest,"PRCM",Oseeds,exAnte,"series")) * P_PrdAdj(MSest,Oseeds)                          ));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.biof_adjust)."""
    base, k = (bast, n_bast) if bast else (basm, n)
    return min(base * upplim ** k, max(basm * lowlim * 0.98 ** n, value + (prcm - series) * prdadj))


def P_Result_DOMM_Oseeds(value, prcm, series):
    r"""P_Result(MSest, "DOMM", Oseeds, exAnte): the PRCM change passed on in full, not below zero.

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 127-131):

            P_Result(MSest,"DOMM",Oseeds,exAnte,%1) $ (  SUM(SED_TO_OIL(Oseeds,biostock),BIO_PRCD("BIOD",biostock))
                                                              $ p_Result(MSest,"DOMM",Oseeds,exAnte,%1))
               = Max(0,     P_Result(MSest,"DOMM",Oseeds,exAnte,%1)
                       + (  P_Result(MSest,"PRCM",Oseeds,exAnte,%1)
                          - P_Result(MSest,"PRCM",Oseeds,exAnte,"series")));

    Departures from CAPRI: the port adds PRCM to the value, then subtracts its "series" (CAPRI subtracts first, the last digit may differ);
    the domain condition and the loops over the sets in the caller (final_supports.biof_adjust)."""
    return max(0.0, value + prcm - series)


def P_Result_MAPR_SECO(value, basm, lowlims, n, changes, yld):
    r"""P_Result(MSest, "MAPR", SECO, exAnte): the cake's support plus its oilseeds' PRCM change x Proc_Yields(SECO), at
    least BASM x the sum of its oils' P_LowLim x .98**n.

    lowlims: P_LowLim of the oils of the cake; changes: (PRCM, its "series") of their seeds, in the caller's order.

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 136-144):

            P_Result(MSest,"MAPR",SECO,exAnte,%1)
               $  SUM((OIL_TO_CAK(biostock,SECO),SED_TO_OIL(Oseeds,biostock),BIO_PRCD("BIOD",biostock)),
                             P_Result(MSest,"PRCM",Oseeds,exAnte,%1))
               =  MAX(P_Result(MSest,"MAPR",SECO,exAnte,"BASM")*SUM(OIL_TO_CAK(biostock,SECO),P_lowLim(MSest,bioStock))
                                                               *.98**(OrdT(ExAnte)-OrdT("BAS")),
                      P_Result(MSest,"MAPR",seco,exAnte,%1)
                     +SUM((OIL_TO_CAK(biostock,SECO),SED_TO_OIL(Oseeds,biostock),BIO_PRCD("BIOD",biostock)),
                             P_Result(MSest,"PRCM",Oseeds,exAnte,%1)
                           - P_Result(MSest,"PRCM",Oseeds,exAnte,"series")) * Proc_Yields(SECO)) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.biof_adjust)."""
    return max(basm * sum(lowlims) * 0.98 ** n, value + sum(p - s for p, s in changes) * yld)


def P_Result_LEVL_GRCU(value, grof, series):
    r"""P_Result(MSest, GRCU, "LEVL", exAnte): the level times its outputs' GROF over their "series" (the change from
    the area, not the yield).

    grof, series: GROF and its "series" of the crop's outputs, in the caller's order.

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 149-156):

            P_Result(MSest,GRCU,"LEVL",exAnte,%1) $ ( (SUM(PACT_TO_Y(GRCU,CROPO),P_Result(MSest,"GROF",CROPO,exAnte,%1)
                                                                                -P_Result(MSest,"GROF",CROPO,exAnte,"BASM")
                                                                                *P_lowLim(MSest,CROPO)* .98**(OrdT(ExAnte)-OrdT("BAS"))) GT 1E-13)
                                                    $ P_Result(MSest,GRCU,"LEVL",exAnte,%1)
                                                    $ SUM(PACT_TO_Y(GRCU,CROPO),P_Result(MSest,"GROF",CROPO,exAnte,"series")))
              =   P_Result(MSest,GRCU,"LEVL",ExAnte,%1)
                  * SUM(PACT_TO_Y(GRCU,CROPO), P_Result(MSest,"GROF",CROPO,exAnte,%1)
                                             / P_Result(MSest,"GROF",CROPO,exAnte,"series") );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.biof_adjust)."""
    return value * sum(a / b for a, b in zip(grof, series))


def P_Result_MAPR_SUGA(value, quts, indm, biof_expert):
    r"""P_Result(MSest, "MAPR", "SUGA", exAnte) with a quota: at least the quota plus INDM plus the expert's BIOF
    (ethanol beets on top of the quota).

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 162-172):

            P_Result(MSest,"MAPR","SUGA",exAnte,%1) $ ( (p_result(MSest,"QUTS","SUGA",exAnte,"p_data") gt eps)
                                                      $ P_Result(MSest,"MAPR","SUGA",ExAnte,%1)
                                                      $ p_data(MSest,"MAPR","SUGA","nObs")
                                                      $ (P_Result(MSest,"BIOF","SUGA",exAnte,"Expert") gt 1E-13)
                                                      )

               =  MAX(  P_Result(MSest,"MAPR","SUGA",exAnte,%1),
                        p_result(MSest,"QUTS","SUGA",exAnte,"p_data")
                      + P_Result(MSest,"INDM","SUGA",exAnte,%1)
                      + P_Result(MSest,"BIOF","SUGA",exAnte,"Expert")
                      );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.biof_adjust)."""
    return max(value, quts + indm + biof_expert)


def P_Result_BIOF_SUGA_Expert():
    r"""P_Result(MSest, "BIOF", "SUGA", exAnte, "Expert") without MAPR.SUGA observations: removed.

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 175-175):

            P_Result(MSest,"BIOF","SUGA",exAnte,"Expert") $ (not p_data(MSest,"MAPR","SUGA","nObs")) = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.biof_adjust)."""
    return 0.0


def P_Result_PRCM_SUGB(value, basm, lowlim, n, mapr, series, prcy):
    r"""P_Result(MSest, "PRCM", "SUGB", exAnte): the sugar's MAPR change over its yield PRCY (between .12 and .19)
    added, at least BASM x P_LowLim x .98**n.

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 179-186):

            P_Result(MSest,"PRCM","SUGB",exAnte,%1) $ (  P_Result(MSest,"PRCM","SUGB",exAnte,%1)
                                                           $ P_Result(MSest,"MAPR","SUGA",ExAnte,%1))

               =  MAX(P_Result(MSest,"PRCM","SUGB",exAnte,"BASM")*P_lowLim(MSest,"SUGB")* .98**(OrdT(ExAnte)-OrdT("BAS")),
                         P_Result(MSest,"PRCM","SUGB",exAnte,%1)
                    + (  P_Result(MSest,"MAPR","SUGA",exAnte,%1)
                       - P_Result(MSest,"MAPR","SUGA",exAnte,"series"))
                    / MAX(.12,MIN(.19,p_result(MSest,"PRCY","SUGA",ExAnte,"support"))) );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.biof_adjust)."""
    return max(basm * lowlim * 0.98 ** n, value + (mapr - series) / max(0.12, min(0.19, prcy)))


def P_Result_GROF_SUGB(value, basm, lowlim, n, prcm, series, prdadj):
    r"""P_Result(MSest, "GROF", "SUGB", exAnte): the PRCM change times P_PrdAdj added, at least BASM x P_LowLim x
    .98**n.

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 191-197):

            P_Result(MSest,"GROF","SUGB",exAnte,%1) $ (    P_Result(MSest,"GROF","SUGB",exAnte,%1)
                                                           and P_Result(MSest,"PRCM","SUGB",exAnte,%1))

               =  MAX(P_Result(MSest,"GROF","SUGB",exAnte,"BASM")*P_lowLim(MSest,"SUGB")* .98**(OrdT(ExAnte)-OrdT("BAS")),
                         P_Result(MSest,"GROF","SUGB",exAnte,%1)
                    + (  P_Result(MSest,"PRCM","SUGB",exAnte,%1)
                       - P_Result(MSest,"PRCM","SUGB",exAnte,"series")) * P_PrdAdj(MSest,"SUGB")                          );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.biof_adjust)."""
    return max(basm * lowlim * 0.98 ** n, value + (prcm - series) * prdadj)


def P_Result_ShiftSugbPos(basm, grof, basm_grof):
    r"""P_Result(MSest, ShiftSugbPos, "SUGB", exAnte): BASM scaled with GROF.

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 202-207):

            P_Result(MSest,ShiftSugbPos,"SUGB",exAnte,%1) $ (    P_Result(MSest,"GROF","SUGB",exAnte,%1)
                                                                 $   P_Result(MSest,"GROF","SUGB",exAnte,"BASM"))

               =  p_result(MSest,ShiftSugbPos,"SUGB",ExAnte,"BASM")
               *  P_Result(MSest,"GROF","SUGB",exAnte,%1)
               /  p_result(MSest,"GROF","SUGB",ExAnte,"BASM") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.biof_adjust)."""
    return basm * grof / basm_grof


def P_Result_LOSM_SUGB(bas, grof, bas_grof):
    r"""P_Result(MSest, "LOSM", "SUGB", exAnte): p_data's BAS scaled with GROF.

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 212-216):

            P_Result(MSest,"LOSM","SUGB",exAnte,%1) $ (    P_Result(MSest,"GROF","SUGB",exAnte,%1)
                                                                 $   p_data(MSest,"GROF","SUGB","BAS"))
               =  p_data(MSest,"LOSM","SUGB","BAS")
               *  P_Result(MSest,"GROF","SUGB",exAnte,%1)
               /  p_data(MSest,"GROF","SUGB","BAS");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.biof_adjust)."""
    return bas * grof / bas_grof


def P_Result_DOMM_SUGB(value, dompos, series):
    r"""P_Result(MSest, "DOMM", "SUGB", exAnte): the domestic positions' change passed on in full, at least 20% of the
    value.

    dompos, series: the DomPos' supports and their "series", in the caller's order.

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 221-225):

            P_Result(MSest,"DOMM","SUGB",exAnte,%1) $  P_Result(MSest,"DOMM","SUGB",exAnte,%1)
               = Max(0.2*P_Result(MSest,"DOMM","SUGB",exAnte,%1),
                         P_Result(MSest,"DOMM","SUGB",exAnte,%1)
                    + (  SUM(DomPos, P_Result(MSest,DomPos,"SUGB",exAnte,%1))
                       - SUM(DomPos, P_Result(MSest,DomPos,"SUGB",exAnte,"Series"))));

    Departures from CAPRI: the port adds the positions' sum to the value, then subtracts the "series"' (CAPRI subtracts first, the last digit
    may differ); the domain condition in the caller (final_supports.biof_adjust)."""
    return max(0.2 * value, value + sum(dompos) - sum(series))


def P_Result_LEVL_SUGB(value, grof, series):
    r"""P_Result(MSest, "SUGB", "LEVL", exAnte): the level times GROF over its "series".

    CAPRI's GAMS (captrd/adjust_to_biof_supports.gms l. 230-234):

            P_Result(MSest,"SUGB","LEVL",exAnte,%1) $ (    P_Result(MSest,"SUGB","LEVL",exAnte,%1)
                                                            $  P_Result(MSest,"GROF","SUGB",exAnte,"series") )
              =   P_Result(MSest,"SUGB","LEVL",ExAnte,%1)
                  * P_Result(MSest,"GROF","SUGB",exAnte,%1)
                  / P_Result(MSest,"GROF","SUGB",exAnte,"series") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.biof_adjust)."""
    return value * grof / series
