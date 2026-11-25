r"""CAPTRD's statements of captrd/expert_support.gms (CAPRI star 3.0; %useAgriInfo% on, %correctdairyaglink% on,
%lst_daitar% 2020): its own expert rules, DG AGRI's dairy data and the end of the expert supports, as named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). The callers hold the loops over the regions, the positions and the years,
the conditions and the order, and call them: capri_mod/pipeline/captrd/expert_rules.py (rules, l. 53-338),
dairy_supports.py (dairy, l. 365-757) and expert_support.py (herd_floor, toou, l. 794-834). The arithmetic is the
port's, so the supports are unchanged.
"""
from __future__ import annotations

import math


def p_ExpertSupprt_NTRD_FRMI():
    r"""p_ExpertSupprt(MS, "NTRD", "FRMI", exAnte, "ABSOLUTE").

    CAPRI's GAMS (captrd/expert_support.gms l. 53-53):

        p_ExpertSupprt(MS,"NTRD","FRMI",exAnte,"ABSOLUTE")  = 0.1;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_rules.rules)."""
    return 0.1


def p_ExpertSupprt_NTRD_FRMI_trustlevl():
    r"""p_ExpertSupprt(MS, "NTRD", "FRMI", exAnte, "trustlevl").

    CAPRI's GAMS (captrd/expert_support.gms l. 54-54):

        p_ExpertSupprt(MS,"NTRD","FRMI",exAnte,"trustlevl") = 10.;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_rules.rules)."""
    return 10.0


def p_ExpertSupprt_uvag_suga():
    r"""p_ExpertSupprt(ms, "uvag", "suga", years, "absolute") of the EU's member states from 2009: white sugar's
    price.

    CAPRI's GAMS (captrd/expert_support.gms l. 70-71):

         p_ExpertSupprt(ms,"uvag","suga",years,"absolute")   $ (exAnte(years) and (calyea(years) ge calyea("2009")))
                                                            = 404.4;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_rules.rules)."""
    return 404.4


def p_ExpertSupprt_uvag_sugb(prcy_mola):
    r"""p_ExpertSupprt(ms, "uvag", "sugb", years, "absolute") from 2009: the beet price plus the molasses' value at
    half its price.

    CAPRI's GAMS (captrd/expert_support.gms l. 83-84):

         p_ExpertSupprt(ms,"uvag","sugb",years,"absolute")   $ (exAnte(years) and (calyea(years) ge calyea("2009")))
                                                            = 26.29 + 75.94 * p_result(ms,"PRCY","MOLA",years,"support") * 0.5;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_rules.rules)."""
    return 26.29 + 75.94 * prcy_mola * 0.5


def p_ExpertSupprt_uvag_trustlevl():
    r"""p_ExpertSupprt(ms, "uvag", "suga" / "sugb", years, "trustlevl") from 2009.

    CAPRI's GAMS (captrd/expert_support.gms l. 72-73):

         p_ExpertSupprt(ms,"uvag","suga",years,"trustlevl")  $ (exAnte(years) and (calyea(years) ge calyea("2009")))
                                                            = 10;

    CAPRI's GAMS (captrd/expert_support.gms l. 85-86):

         p_ExpertSupprt(ms,"uvag","sugb",years,"trustLevl")  $ (exAnte(years) and (calyea(years) ge calyea("2009")))
                                                            = 10;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_rules.rules)."""
    return 10.0


def p_ExpertSupprt_sugar_balance(basm):
    r"""p_ExpertSupprt(ms, IMPT / FEDM / LOSM / EXPT .SUGB, FEDM / LOSM .SUGA, exante, "absolute"): BASM, where the
    demand (production for EXPT) has one.

    CAPRI's GAMS (captrd/expert_support.gms l. 90-90):

         p_ExpertSupprt(ms,"impt","sugb",exante,"absolute") $ p_result(MS,"domm","sugb",exAnte,"BASM") = p_result(MS,"impt","sugb",exAnte,"BASM");

    CAPRI's GAMS (captrd/expert_support.gms l. 91-91):

         p_ExpertSupprt(ms,"fedm","sugb",exante,"absolute") $ p_result(MS,"domm","sugb",exAnte,"BASM") = p_result(MS,"fedm","sugb",exAnte,"BASM");

    CAPRI's GAMS (captrd/expert_support.gms l. 92-92):

         p_ExpertSupprt(ms,"losm","sugb",exante,"absolute") $ p_result(MS,"domm","sugb",exAnte,"BASM") = p_result(MS,"losm","sugb",exAnte,"BASM");

    CAPRI's GAMS (captrd/expert_support.gms l. 93-93):

         p_ExpertSupprt(ms,"expt","sugb",exante,"absolute") $ p_result(MS,"grof","sugb",exAnte,"BASM") = p_result(MS,"expt","sugb",exAnte,"BASM");

    CAPRI's GAMS (captrd/expert_support.gms l. 94-94):

         p_ExpertSupprt(ms,"fedm","suga",exante,"absolute") $ p_result(MS,"domm","suga",exAnte,"BASM") = p_result(MS,"fedm","suga",exAnte,"BASM");

    CAPRI's GAMS (captrd/expert_support.gms l. 95-95):

         p_ExpertSupprt(ms,"losm","suga",exante,"absolute") $ p_result(MS,"domm","suga",exAnte,"BASM") = p_result(MS,"losm","suga",exAnte,"BASM");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_rules.rules)."""
    return basm


def p_ExpertSupprt_sugar_balance_trustLevl():
    r"""p_ExpertSupprt(ms, ., "sugb" / "suga", ExAnte, "trustLevl") of the sugar balance positions.

    CAPRI's GAMS (captrd/expert_support.gms l. 97-97):

         p_ExpertSupprt(ms,"IMPT","sugb",ExAnte,"trustLevl") $ p_ExpertSupprt(ms,"IMPT","sugb",exante,"absolute") = 8;

    CAPRI's GAMS (captrd/expert_support.gms l. 98-98):

         p_ExpertSupprt(ms,"FEDM","sugb",ExAnte,"trustLevl") $ p_ExpertSupprt(ms,"FEDM","sugb",exante,"absolute") = 8;

    CAPRI's GAMS (captrd/expert_support.gms l. 99-99):

         p_ExpertSupprt(ms,"LOSM","sugb",ExAnte,"trustLevl") $ p_ExpertSupprt(ms,"LOSM","sugb",exante,"absolute") = 8;

    CAPRI's GAMS (captrd/expert_support.gms l. 100-100):

         p_ExpertSupprt(ms,"EXPT","sugb",ExAnte,"trustLevl") $ p_ExpertSupprt(ms,"EXPT","sugb",exante,"absolute") = 8;

    CAPRI's GAMS (captrd/expert_support.gms l. 101-101):

         p_ExpertSupprt(ms,"FEDM","suga",ExAnte,"trustLevl") $ p_ExpertSupprt(ms,"FEDM","suga",exante,"absolute") = 8;

    CAPRI's GAMS (captrd/expert_support.gms l. 102-102):

         p_ExpertSupprt(ms,"LOSM","suga",ExAnte,"trustLevl") $ p_ExpertSupprt(ms,"LOSM","suga",exante,"absolute") = 8;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_rules.rules)."""
    return 8.0


def p_nutrientEU_mean(values):
    r"""p_nutrientEU(MS, ncnc, "mean00" / "mean10"): the mean over the three years around 2000 (2010) with a value.

    values: the three years' values, in order.

    CAPRI's GAMS (captrd/expert_support.gms l. 164-165):

          p_nutrientEU(MS,ncnc,"mean00")   = sum(simyy $ (abs(OrdT(simyy)-OrdT("2000")) le 1),p_nutrientEU(MS,ncnc,simyy) )
                                           / sum(simyy $ ((abs(OrdT(simyy)-OrdT("2000")) le 1) $ p_nutrientEU(MS,ncnc,simyy)),1);

    CAPRI's GAMS (captrd/expert_support.gms l. 168-169):

          p_nutrientEU(MS,ncnc,"mean10")   = sum(simyy $ (abs(OrdT(simyy)-OrdT("2010")) le 1),p_nutrientEU(MS,ncnc,simyy) )
                                           / sum(simyy $ ((abs(OrdT(simyy)-OrdT("2010")) le 1) $ p_nutrientEU(MS,ncnc,simyy)),1);

    Departures from CAPRI: GAMS divides by zero where no year has a value (UNDF), the port gives 0; the loops in the caller 
    (expert_rules.rules)."""
    k = sum(1 for v in values if v)
    return sum(values) / k if k else 0.0


def p_nutrientEU_EU(values, n_ms):
    r"""p_nutrientEU("EU", ncnc, "mean00" / "mean10"): the member states' means summed over card(ms).

    CAPRI's GAMS (captrd/expert_support.gms l. 166-166):

          p_nutrientEU("EU",ncnc,"mean00") = sum(ms,p_nutrientEU(MS,ncnc,"mean00"))/card(ms);

    CAPRI's GAMS (captrd/expert_support.gms l. 170-170):

          p_nutrientEU("EU",ncnc,"mean10") = sum(ms,p_nutrientEU(MS,ncnc,"mean10"))/card(ms);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_rules.rules)."""
    return sum(values) / n_ms


def p_nutrientEU_increase(mean10, mean00):
    r"""p_nutrientEU(rmall, ncnc, "increase"): the yearly increase from 2000 to 2010.

    CAPRI's GAMS (captrd/expert_support.gms l. 172-173):

          p_nutrientEU(rmall,ncnc,"increase") $ p_nutrientEU(rmall,ncnc,"mean00")
          = (p_nutrientEU(rmall,ncnc,"mean10")-p_nutrientEU(rmall,ncnc,"mean00"))/10;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_rules.rules)."""
    return (mean10 - mean00) / 10


def p_ExpertSupprt_INCE(basm, increase, year, bas_year, eu_mean10):
    r"""p_ExpertSupprt(MS, NCNC, "INCE", ExAnte, "Absolute"): BASM plus the EU's yearly increase, declining linearly
    to half by 2050, larger below the EU mean (convergence factor 4).

    CAPRI's GAMS (captrd/expert_support.gms l. 175-189):

          p_ExpertSupprt(MS,NCNC,"INCE",ExAnte,"Absolute") $ (  P_Result(MS,NCNC,"INCE",ExAnte,"BASM") )
        *
             = P_Result(MS,NCNC,"INCE",ExAnte,"BASM")
             + p_nutrientEU("EU",NCNC,"increase") * (min(ordT("2050"),ordT(ExAnte))-ordT("BAS"))
        *      Modification #1 assumes that annual increase declines to zero towards 2050. As we assume linear growth and
        *      linear decline of this annual growth, the average growth may be computed as an unweighted average of the initial
        *      growth and the final growth in some selected year, acknowledging the decline of growth by 100% towards 2050:
        *      avgIncrease = [p_nutrientEU("EU",increase)+p_nutrientEU("EU",increase)*(1-1*(ordT(ExAnte)-ordT("BAS"))/(ordT("2050")-ordT("BAS"))]/2
        *                  = p_nutrientEU("EU",increase)*[.5 + .5*(1-1*(ordT(ExAnte)-ordT("BAS"))/(ordT("2050")-ordT("BAS"))]
        *                  = p_nutrientEU("EU",increase)*[1 -0.5*(ordT(ExAnte)-ordT("BAS"))/(ordT("2050")-ordT("BAS"))] =>
             * (1 -0.5*(min(ordT("2050"),ordT(ExAnte))-ordT("BAS"))/(ordT("2050")-ordT("BAS")))
        *      Modification #2 assumes convergence of diets with a convergence factor of 4 => an MS with more than 25% above the EU avg
        *      would not grow at all anymore
             * (1+ 4 * (p_nutrientEU("EU",NCNC,"mean10")-P_Result(MS,NCNC,"INCE",ExAnte,"BASM"))
                      / p_nutrientEU("EU",NCNC,"mean10"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_rules.rules)."""
    t = min(2050, year) - bas_year
    return basm + increase * t * (1 - 0.5 * t / (2050 - bas_year)) * (1 + 4.0 * (eu_mean10 - basm) / eu_mean10)


def p_ExpertSupprt_INCE_trustLevl(fat):
    r"""p_ExpertSupprt(MS, NCNC, "INCE", ExAnte, "trustLevl"): 10, fat 7.

    CAPRI's GAMS (captrd/expert_support.gms l. 191-192):

          p_ExpertSupprt(MS,NCNC,"INCE",ExAnte,"trustLevl") $ p_ExpertSupprt(MS,NCNC,"INCE",ExAnte,"Absolute")
             = 10 - 3 $ sameas(NCNC,"N_FAT");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_rules.rules)."""
    return 7.0 if fat else 10.0


def P_Result_PRCI_MAIZ_DGAgri1(hcom_suga, coef_suga, hcos, s1com, coef_maiz):
    r"""P_Result(RMall, "PRCI", "MAIZ", ExAnte, "DGAgri1"): the maize processed to isoglucose, from DG AGRI's sugar
    consumption, HFCS's share of sweeteners (HCOS) and its self-sufficiency (S1COM).

    CAPRI's GAMS (captrd/expert_support.gms l. 208-217):

          P_Result(RMall,"PRCI","MAIZ",ExAnte,"DGAgri1") $ (sum(sameas(ms,RMall),1) or sum(sameas(curEuropAgg,RMall),1))
        *     => sugar in HFCS units
             = P_Result(RMall,"HCOM","SUGA",ExAnte,"DGAgri1")*p_coefHFCS('SUGA')
        *     => HFCS consumed
             * P_Result(RMall,"HCOS","HFCS",ExAnte,"DGAgri")/(1-P_Result(RMall,"HCOS","HFCS",ExAnte,"DGAgri"))
        *     => HFCS produced follows from self sufficiency ratio in Aglink
             * P_Result(RMall,"S1COM","HFCS",ExAnte,"DGAgri")
        *     => MAIZ needed
             / p_coefHFCS('MAIZ')
             ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_rules.rules)."""
    return hcom_suga * coef_suga * hcos / (1 - hcos) * s1com / coef_maiz


def p_coefHFCS_PROD():
    r"""p_coefHFCS('PROD'): the share of isoglucose allocated by maize production (the rest by sugar consumption).

    CAPRI's GAMS (captrd/expert_support.gms l. 222-222):

          p_coefHFCS('PROD') = .5;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_rules.rules)."""
    return .5


def p_ExpertSupprt_PRCI_MAIZ(aggregates, prod, grof, peers_grof, hcom, peers_hcom):
    r"""p_ExpertSupprt(MS, "PRCI", "MAIZ", ExAnte, "Absolute"): the aggregates' DGAgri1 shared by maize production and
    sugar consumption (BAST, else BASM).

    aggregates: the PRCI.MAIZ DGAgri1 of the member state's aggregates; peers_grof, peers_hcom: GROF.MAIZ and
    HCOM.SUGA of the member states of those aggregates (every aggregate's, as coded), in the caller's order.

    CAPRI's GAMS (captrd/expert_support.gms l. 224-235):

          p_ExpertSupprt(MS,"PRCI","MAIZ",ExAnte,"Absolute") $ ((  P_Result(MS,"GROF","MAIZ",ExAnte,"BAST")
                                                                 or P_Result(MS,"HCOM","SUGA",ExAnte,"BAST"))
                                                               $ sum(MS_TO_RMSAGG(MS,CurEuropAgg),1))

             = SUM(MS_TO_RMSAGG(MS,CurEuropAgg),P_Result(CurEuropAgg,"PRCI","MAIZ",ExAnte,"DGAgri1"))
             * (  p_coefHFCS('PROD')
                * P_Result(MS,"GROF","MAIZ",ExAnte,"BAST")
                / sum(MS_TO_RMSAGG(MS1,CurEuropAgg) $ MS_TO_RMSAGG(MS,CurEuropAgg),P_Result(MS1,"GROF","MAIZ",ExAnte,"BAST"))
               + (1-p_coefHFCS('PROD'))
                * P_Result(MS,"HCOM","SUGA",ExAnte,"BAST")
                / sum(MS_TO_RMSAGG(MS1,CurEuropAgg) $ MS_TO_RMSAGG(MS,CurEuropAgg),P_Result(MS1,"HCOM","SUGA",ExAnte,"BAST")))
              ;

    CAPRI's GAMS (captrd/expert_support.gms l. 237-248):

          p_ExpertSupprt(MS,"PRCI","MAIZ",ExAnte,"Absolute") $ (  (not p_ExpertSupprt(MS,"PRCI","MAIZ",ExAnte,"Absolute") )
                                                               $  (  P_Result(MS,"GROF","MAIZ",ExAnte,"BASM")
                                                                  or P_Result(MS,"HCOM","SUGA",ExAnte,"BASM"))
                                                               $ sum(MS_TO_RMSAGG(MS,CurEuropAgg),1))
             = SUM(MS_TO_RMSAGG(MS,CurEuropAgg),P_Result(CurEuropAgg,"PRCI","MAIZ",ExAnte,"DGAgri1"))
             * (  p_coefHFCS('PROD')
                * P_Result(MS,"GROF","MAIZ",ExAnte,"BASM")
                / sum(MS_TO_RMSAGG(MS1,CurEuropAgg) $ MS_TO_RMSAGG(MS,CurEuropAgg),P_Result(MS1,"GROF","MAIZ",ExAnte,"BASM"))
               + (1-p_coefHFCS('PROD'))
                * P_Result(MS,"HCOM","SUGA",ExAnte,"BASM")
                / sum(MS_TO_RMSAGG(MS1,CurEuropAgg) $ MS_TO_RMSAGG(MS,CurEuropAgg),P_Result(MS1,"HCOM","SUGA",ExAnte,"BASM")))
              ;

    Departures from CAPRI: GAMS divides by zero where the peers' sum is zero (UNDF), the port takes the share as 0; the domain condition and
    the loops in the caller (expert_rules.rules)."""
    tot = sum(aggregates)
    dg, ds = sum(peers_grof), sum(peers_hcom)
    return tot * (prod * (grof / dg if dg else 0.0) + (1 - prod) * (hcom / ds if ds else 0.0))


def p_ExpertSupprt_PRCI_MAIZ_trustLevl():
    r"""p_ExpertSupprt(MS, "PRCI", "MAIZ", ExAnte, "trustLevl").

    CAPRI's GAMS (captrd/expert_support.gms l. 250-251):

          p_ExpertSupprt(MS,"PRCI","MAIZ",ExAnte,"trustLevl") $ p_ExpertSupprt(MS,"PRCI","MAIZ",ExAnte,"Absolute")
              = 9.;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_rules.rules)."""
    return 9.0


def p_ExpertSupprt_INDM_MAIZ(prci):
    r"""p_ExpertSupprt(MS, "INDM", "MAIZ", ExAnte, "Absolute") without a support: 1.05 x PRCI.MAIZ.

    CAPRI's GAMS (captrd/expert_support.gms l. 258-260):

          p_ExpertSupprt(MS,"INDM","MAIZ",ExAnte,"Absolute") $ (  p_ExpertSupprt(MS,"PRCI","MAIZ",ExAnte,"Absolute")
                                                               $  (not P_Result(MS,"INDM","MAIZ",ExAnte,"support")))
            = 1.05* p_ExpertSupprt(MS,"PRCI","MAIZ",ExAnte,"Absolute");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_rules.rules)."""
    return 1.05 * prci


def p_ExpertSupprt_INDM_MAIZ_trustLevl():
    r"""p_ExpertSupprt(MS, "INDM", "MAIZ", ExAnte, "trustLevl").

    CAPRI's GAMS (captrd/expert_support.gms l. 265-266):

          p_ExpertSupprt(MS,"INDM","MAIZ",ExAnte,"trustLevl") $ p_ExpertSupprt(MS,"INDM","MAIZ",ExAnte,"Absolute")
              = 5.;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_rules.rules)."""
    return 5.0


def p_ExpertSupprt_from_Support(support):
    r"""p_ExpertSupprt(MS, "UAAR" .LEVL / breedAct .SLGW / "SHGM" .SGMI, ExAnte, "Absolute") without one: the
    support.

    CAPRI's GAMS (captrd/expert_support.gms l. 310-312):

          p_ExpertSupprt(MS,"UAAR","LEVL",ExAnte,"Absolute")
                                    $  (NOT   p_ExpertSupprt(MS,"UAAR","LEVL",ExAnte,"Absolute"))
               = P_Result(MS,"UAAR","LEVL",ExAnte,"Support") ;

    CAPRI's GAMS (captrd/expert_support.gms l. 319-321):

          p_ExpertSupprt(MS,breedAct,"SLGW",ExAnte,"Absolute")
                                    $  (NOT   p_ExpertSupprt(MS,breedAct,"SLGW",ExAnte,"Absolute"))
              = P_Result(MS,breedAct,"SLGW",ExAnte,"Support") ;

    CAPRI's GAMS (captrd/expert_support.gms l. 332-334):

          p_ExpertSupprt(MS,"SHGM","SGMI",ExAnte,"Absolute")
                                    $  (NOT   p_ExpertSupprt(MS,"SHGM","SGMI",ExAnte,"Absolute"))
              = P_Result(MS,"SHGM","SGMI",ExAnte,"Support") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_rules.rules)."""
    return support


def p_ExpertSupprt_UAAR_TRustlevl():
    r"""p_ExpertSupprt(MS, "UAAR", "LEVL", ExAnte, "TRustlevl") without one.

    CAPRI's GAMS (captrd/expert_support.gms l. 314-316):

          p_ExpertSupprt(MS,"UAAR","LEVL",ExAnte,"TRustlevl") $  (  p_ExpertSupprt(MS,"UAAR","LEVL",ExAnte,"Absolute")
                                                                  $ (NOT p_ExpertSupprt(MS,"UAAR","LEVL",ExAnte,"TRustlevl")))
               = 10;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_rules.rules)."""
    return 10.0


def p_ExpertSupprt_SLGW_TRustlevl():
    r"""p_ExpertSupprt(MS, breedAct, "SLGW", ExAnte, "TRustlevl") without one.

    CAPRI's GAMS (captrd/expert_support.gms l. 323-325):

          p_ExpertSupprt(MS,breedAct,"SLGW",ExAnte,"TRustlevl") $  (  p_ExpertSupprt(MS,breedAct,"SLGW",ExAnte,"Absolute")
                                                                  $ (NOT p_ExpertSupprt(MS,breedAct,"SLGW",ExAnte,"TRustlevl")))
              = 8;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_rules.rules)."""
    return 8.0


def p_ExpertSupprt_SGMI_TRustlevl():
    r"""p_ExpertSupprt(MS, "SHGM", "SGMI", ExAnte, "TRustlevl") without one.

    CAPRI's GAMS (captrd/expert_support.gms l. 336-338):

          p_ExpertSupprt(MS,"SHGM","SGMI",ExAnte,"TRustlevl") $  (  p_ExpertSupprt(MS,"SHGM","SGMI",ExAnte,"Absolute")
                                                                  $ (NOT p_ExpertSupprt(MS,"SHGM","SGMI",ExAnte,"TRustlevl")))
              = 5;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_rules.rules)."""
    return 5.0


def p_dairy_BASM(values):
    r"""p_nrCows / p_CowMilkProd / p_milkDeliveries / p_dairyCowYield(ms_agri, "BASM"): the mean over the years around
    BAS (yrbas).

    CAPRI's GAMS (captrd/expert_support.gms l. 387-387):

          p_nrCows(ms_agri,"BASM") = sum(yrbas,p_nrCows(ms_agri,yrbas))/card(yrbas);

    CAPRI's GAMS (captrd/expert_support.gms l. 396-396):

          p_CowMilkProd(ms_agri,"BASM") = sum(yrbas,p_CowMilkProd(ms_agri,yrbas))/card(yrbas);

    CAPRI's GAMS (captrd/expert_support.gms l. 414-414):

          p_milkDeliveries(ms_agri,"BASM") = sum(yrbas,p_milkDeliveries(ms_agri,yrbas))/card(yrbas);

    CAPRI's GAMS (captrd/expert_support.gms l. 425-425):

          p_dairyCowYield(ms_agri,"BASM") = sum(yrbas,p_dairyCowYield(ms_agri,yrbas))/card(yrbas);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return sum(values) / len(values)


def p_dairyCowYield_PL(milk, cows):
    r"""p_dairyCowYield("PL", simyy): Poland's yield, cow milk over cows in kg.

    CAPRI's GAMS (captrd/expert_support.gms l. 424-424):

          p_dairyCowYield("PL",simyy) $ p_nrCows("PL",simyy)  = p_CowMilkProd("PL",simyy) / p_nrCows("PL",simyy) * 1000 ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return milk / cows * 1000.0


def p_ExpertSupprt_dairy(changes, basm):
    r"""p_ExpertSupprt(runr, ., ., EXANTET1, "absolute") up to %lst_daitar%: the DG AGRI table's change from its BASM
    times BASM (dairy herds from p_nrCows; GROF, DOMM, EAAG .COMI from p_CowMilkProd; PRCM.COMI from
    p_milkDeliveries; the cows' yields from p_dairyCowYield).

    changes: (the table's value of the year, its BASM) of the region's ms_agri, in the caller's order.

    CAPRI's GAMS (captrd/expert_support.gms l. 388-393):

          p_ExpertSupprt(runr,DCOW,rows,EXANTET1,"absolute") $ (  P_Result(runr,DCOW,rows,"%lastSimulationYear%","BASM")
                                                               $ (sameas(rows,"LEVL") or sameas(rows,"HERD"))
                                                               $ (ORDT(ExanteT1) LE ORDT("%lst_daitar%")))

              = sum(ms_agri_TO_MS(ms_agri, Runr), p_nrCows(ms_agri,exanteT1) / p_nrCows(ms_agri,"BASM"))
              * P_Result(runr,DCOW,rows,"%lastSimulationYear%","BASM");

    CAPRI's GAMS (captrd/expert_support.gms l. 397-402):

          p_ExpertSupprt(runr,cols,"COMI",EXANTET1,"absolute") $ (  P_Result(runr,cols,"COMI","%lastSimulationYear%","BASM")
                                                               $ (sameas(cols,"GROF") or sameas(cols,"DOMM") or sameas(cols,"EAAG"))
                                                               $ (ORDT(ExanteT1) LE ORDT("%lst_daitar%")))

              = sum(ms_agri_TO_MS(ms_agri, Runr), p_CowMilkProd(ms_agri,exanteT1)/ p_CowMilkProd(ms_agri,"BASM"))
              * P_Result(runr,cols,"COMI","%lastSimulationYear%","BASM");

    CAPRI's GAMS (captrd/expert_support.gms l. 415-420):

          p_ExpertSupprt(runr,cols,"COMI",EXANTET1,"absolute") $ (  P_Result(runr,cols,"COMI","%lastSimulationYear%","BASM")
                                                               $ (sameas(cols,"PRCM") )
                                                               $ (ORDT(ExanteT1) LE ORDT("%lst_daitar%")))

              = sum(ms_agri_TO_MS(ms_agri, Runr), p_milkDeliveries(ms_agri,exanteT1)/ p_milkDeliveries(ms_agri,"BASM"))
              * P_Result(runr,cols,"COMI","%lastSimulationYear%","BASM");

    CAPRI's GAMS (captrd/expert_support.gms l. 426-430):

          p_ExpertSupprt(runr,dcow,"COMI",EXANTET1,"absolute") $ ( P_Result(runr,dcow,"COMI","%lastSimulationYear%","BASM")
                                                                 $ (ORDT(ExanteT1) LE ORDT("%lst_daitar%")))

              = sum(ms_agri_TO_MS(ms_agri, Runr), p_dairyCowYield(ms_agri,exanteT1)/ p_dairyCowYield(ms_agri,"BASM"))
              * P_Result(runr,dcow,"COMI","%lastSimulationYear%","BASM");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return sum(v / b for v, b in changes) * basm


def p_ExpertSupprt_EAAG_COMI(eaag, uvag, uvag_daitar, uvag_basm):
    r"""p_ExpertSupprt(runr, "EAAG", "COMI", EXANTET1, "absolute"): scaled by the price support (of %lst_daitar% where
    the year has none) over its BASM.

    CAPRI's GAMS (captrd/expert_support.gms l. 406-411):

          p_ExpertSupprt(runr,"EAAG","COMI",EXANTET1,"absolute") $ (  P_Result(runr,"UVAG","COMI","%lastSimulationYear%","BASM")
                                                                    $  p_ExpertSupprt(runr,"EAAG","COMI",EXANTET1,"absolute"))
              = p_ExpertSupprt(runr,"EAAG","COMI",EXANTET1,"absolute")
              * ( P_Result(runr,"UVAG","COMI",ExanteT1,"support")
                + P_Result(runr,"UVAG","COMI","%lst_daitar%","support") $ (not P_Result(runr,"UVAG","COMI",ExanteT1,"support")))
              / P_Result(runr,"UVAG","COMI","%lastSimulationYear%","BASM");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return eaag * (uvag or uvag_daitar) / uvag_basm


def p_exTrapMinMax():
    r"""p_exTrapMinMax("min") and ("max"): the logistic's range. Returns (min, max).

    CAPRI's GAMS (captrd/expert_support.gms l. 439-440):

          p_exTrapMinMax("min") = 0.75;
          p_exTrapMinMax("max") = 2-p_exTrapMinMax("min") ;

    CAPRI's GAMS (captrd/expert_support.gms l. 600-601):

          p_exTrapMinMax("min") = 0.75;
          p_exTrapMinMax("max") = 2-p_exTrapMinMax("min") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    mn = 0.75
    return mn, 2 - mn


def P_expertSupprt_grate(first, last, n):
    r"""P_expertSupprt(RUNR, ., ., "grate", "absolute"): the yearly growth rate from 2015 to %lst_daitar% (n years).

    CAPRI's GAMS (captrd/expert_support.gms l. 443-450):

          P_expertSupprt(RUNR,S_ColsEst,S_RowsEst,"grate","absolute")
                       $ ( (P_expertSupprt(RUNR,S_ColsEst,S_RowsEst,"2015","absolute") GT 1.E-4)
                         $ (P_expertSupprt(RUNR,S_ColsEst,S_RowsEst,"%lst_daitar%","absolute") GT 1.E-4)
                         $ (OrdT("Lst_exAnte") gt ORDT("%lst_daitar%"))
                         $ expertdairy_map(S_ColsEst,S_RowsEst))

              = ((P_expertSupprt(RUNR,S_ColsEst,S_RowsEst,"%lst_daitar%","absolute")
                 /P_expertSupprt(RUNR,S_ColsEst,S_RowsEst,"2015","absolute"))**(1/(OrdT("%lst_daitar%") - OrdT("2015"))))-1;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return (last / first) ** (1 / n) - 1


def P_expertSupprt_grate_yield(grate, cows_comi, comi, ir_mt):
    r"""P_expertSupprt(RUNR, DCOW, ., "grate", "absolute"): shifted by the distance of the region's mean cow yield
    from 8000 kg, up for the yields, down for the herds (not in Ireland and Malta).

    cows_comi: the dairy cows' COMI absolutes of %lst_daitar%; comi: the row is COMI; ir_mt: the region is
    IR000000 or MT000000.

    CAPRI's GAMS (captrd/expert_support.gms l. 456-471):

          P_expertSupprt(RUNR,S_ColsEst,S_RowsEst,"grate","absolute")
                 $ (  P_T_ActAgg(s_colsEst,"DCOW")
                   $ (P_expertSupprt(RUNR,S_ColsEst,S_RowsEst,"%lst_daitar%","absolute") GT 1.E-4)
                   $ (OrdT("Lst_exAnte") gt ORDT("%lst_daitar%"))
                   $ expertdairy_map(S_ColsEst,S_RowsEst))
                 = P_expertSupprt(RUNR,S_ColsEst,S_RowsEst,"grate","absolute")
        *            relative deviation of reference yield from regional yield...
                 + ( 8000 - 0.5*sum(P_T_ActAgg(cols,"DCOW"),P_expertSupprt(RUNR,Cols,"COMI","%lst_daitar%","absolute"))) / 8000
        *            ... is used to increase or decrease the expected milk yield growth...
                 * (.01 $ sameas(S_RowsEst,"COMI")
        *            ... or with opposite sign the expected decline of herds
                   -.01 $ ( (sameas(S_RowsEst,"LEVL") or sameas(S_RowsEst,"HERD"))
        *            ad hoc deactivation of downward effect to acknowledge Food Harvest 2020 or special case MT
        *            Note: 8000>yld(lst_daitar)=>HERD declines faster
                          $ (not sameas(runr,"IR000000")) $ (not sameas(runr,"MT000000")) )
                    );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    yld = 0.5 * sum(cows_comi)
    k = 0.01 if comi else (-0.01 if not ir_mt else 0.0)
    return grate + (8000.0 - yld) / 8000.0 * k


def P_expertSupprt_grate_recent(grate, recent):
    r"""P_expertSupprt(RUNR, DCOW, "COMI", "grate", "absolute"): 30% from the recent yield growth (p_recentMlkYld
    "y").

    CAPRI's GAMS (captrd/expert_support.gms l. 480-486):

          P_expertSupprt(RUNR,S_ColsEst,"COMI","grate","absolute")
                 $ (  P_T_ActAgg(s_colsEst,"DCOW")
                   $ (P_expertSupprt(RUNR,S_ColsEst,"COMI","%lst_daitar%","absolute") GT 1.E-4)
                   $ (OrdT("Lst_exAnte") gt ORDT("%lst_daitar%")))
        *                    The DG agri info is outdated but it was a careful assessment rather than just a recent snap shot => wgt>0.5
                 = (1-0.3)* P_expertSupprt(RUNR,S_ColsEst,"COMI","grate","absolute")
                 +    0.3 * p_recentMlkYld(runr,"y") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return (1 - 0.3) * grate + 0.3 * recent


def P_expertSupprt_grate_EUSubAgg(grates, levels):
    r"""P_expertSupprt(curEUSUbAgg, DCOW, ., "grate", "absolute"): the members' growth rates weighted by their BASM
    levels.

    CAPRI's GAMS (captrd/expert_support.gms l. 494-501):

          P_expertSupprt(curEUSUbAgg,S_ColsEst,S_RowsEst,"grate","absolute")
                 $ (  P_T_ActAgg(s_colsEst,"DCOW") $ (sameas(s_rowsEst,"LEVL") or sameas(s_rowsEst,"COMI") )
                   $ SUM(MS_TO_RMSAGG(ms,CurEuropAgg), P_Result(ms,S_ColsEst,"LEVL","%lastSimulationYear%","BASM"))
                   $ (OrdT("Lst_exAnte") gt ORDT("%lst_daitar%")))

             = SUM(MS_TO_RMSAGG(ms,CurEuropAgg), P_expertSupprt(ms,S_ColsEst,S_RowsEst,"grate","absolute")
                                                 * P_Result(ms,S_ColsEst,"LEVL","%lastSimulationYear%","BASM"))
             / SUM(MS_TO_RMSAGG(ms,CurEuropAgg), P_Result(ms,S_ColsEst,"LEVL","%lastSimulationYear%","BASM"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return sum(g * v for g, v in zip(grates, levels)) / sum(levels)


def P_Result_grate_DGAgri(first, last, n):
    r"""P_Result(rmall, DCOW, ., "grate", "DGAgri"): Aglink's yearly growth rate from 2015 to %lst_dgagri% (n years).

    CAPRI's GAMS (captrd/expert_support.gms l. 505-512):

          P_Result(rmall,S_ColsEst,S_RowsEst,"grate","DGAgri")
                 $ (  P_T_ActAgg(s_colsEst,"DCOW") $ (sameas(s_rowsEst,"LEVL") or sameas(s_rowsEst,"COMI") )
                   $ P_Result(rmall,S_ColsEst,S_RowsEst,"2015","DGAgri")
                   $ (sum(sameas(ms,RMall),1) or sum(sameas(curEuSubAgg,RMall),1))
                   $ (OrdT("Lst_exAnte") gt ORDT("%lst_daitar%")))

                 = ( P_Result(rmall,S_ColsEst,S_RowsEst,"%lst_dgagri%","DGAgri")
                   / P_Result(rmall,S_ColsEst,S_RowsEst,"2015","DGAgri"))**(1/(ordt("%lst_dgagri%")-ordt("2015")))-1;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return (last / first) ** (1 / n) - 1


def P_expertSupprt_grate_DGAgri(dgagri):
    r"""P_expertSupprt(runr, DCOW, ., "grate", "absolute") with Aglink's own: Aglink's.

    CAPRI's GAMS (captrd/expert_support.gms l. 516-520):

          P_expertSupprt(runr,S_ColsEst,S_RowsEst,"grate","absolute")
                  $ ( P_Result(runr,S_ColsEst,S_RowsEst,"grate","DGAgri")
                    $ (P_T_ActAgg(s_colsEst,"DCOW") $ (sameas(s_rowsEst,"LEVL") or sameas(s_rowsEst,"COMI") ))
                    $ (OrdT("Lst_exAnte") gt ORDT("%lst_daitar%")))
             = P_Result(runr,S_ColsEst,S_RowsEst,"grate","DGAgri");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return dgagri


def P_expertSupprt_grate_scaled(grate, ratios):
    r"""P_expertSupprt(runr, DCOW, ., "grate", "absolute"): times its EU parts' Aglink growth rate over their members'
    mean.

    ratios: (Aglink's, the members' mean) of the region's EU parts, in the caller's order.

    CAPRI's GAMS (captrd/expert_support.gms l. 523-529):

          P_expertSupprt(runr,S_ColsEst,S_RowsEst,"grate","absolute")
                  $ ( SUM((map_rr(ms,runr),MS_TO_RMSAGG(ms,CurEuSubAgg)),P_expertSupprt(curEUSUbAgg,S_ColsEst,S_RowsEst,"grate","absolute"))
                    $ (P_T_ActAgg(s_colsEst,"DCOW") $ (sameas(s_rowsEst,"LEVL") or sameas(s_rowsEst,"COMI") ))
                    $ (OrdT("Lst_exAnte") gt ORDT("%lst_daitar%")))
             = P_expertSupprt(runr,S_ColsEst,S_RowsEst,"grate","absolute")
             * SUM((map_rr(ms,runr),MS_TO_RMSAGG(ms,CurEuSubAgg)),P_Result(CurEuSubAgg,S_ColsEst,S_RowsEst,"grate","DGAgri")
                                                / P_expertSupprt(curEUSUbAgg,S_ColsEst,S_RowsEst,"grate","absolute"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return grate * sum(d / e for d, e in ratios)


def P_expertSupprt_EUSubAgg(dgagri):
    r"""P_expertSupprt(curEUSUbAgg, DCOW .LEVL / .COMI, GROF.COMI, yearsCur, "absolute"): Aglink's.

    CAPRI's GAMS (captrd/expert_support.gms l. 533-537):

          P_expertSupprt(curEUSUbAgg,S_ColsEst,S_RowsEst,yearsCur,"absolute")
                 $ (  P_T_ActAgg(s_colsEst,"DCOW") $ (sameas(s_rowsEst,"LEVL") or sameas(s_rowsEst,"COMI") )
                   $ (OrdT("Lst_exAnte") gt ORDT("%lst_daitar%")))

             = P_Result(curEuSubAgg,S_ColsEst,S_RowsEst,yearsCur,"DGAgri");

    CAPRI's GAMS (captrd/expert_support.gms l. 539-543):

          P_expertSupprt(curEUSUbAgg,S_ColsEst,S_RowsEst,yearsCur,"absolute")
                 $ (  sameas(s_colsEst,"GROF") $ sameas(s_rowsEst,"COMI")
                   $ (OrdT("Lst_exAnte") gt ORDT("%lst_daitar%")))

             = P_Result(curEuSubAgg,S_ColsEst,S_RowsEst,yearsCur,"DGAgri");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return dgagri


def p_maxmin_IR():
    r"""p_maxmin("IR000000", expertdairy_map).

    CAPRI's GAMS (captrd/expert_support.gms l. 551-551):

          p_maxmin("IR000000",cols,rows) $ expertdairy_map(cols,rows) = 0.2;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return 0.2


def p_maxmin_BL4():
    r"""p_maxmin("BL400000", expertdairy_map).

    CAPRI's GAMS (captrd/expert_support.gms l. 553-553):

          p_maxmin("BL400000",cols,rows) $ expertdairy_map(cols,rows) = -0.2;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return -0.2


def p_maxmin_EU13_comi(ee):
    r"""p_maxmin(ms, ., "comi") of EU013000's members (Estonia 0).

    CAPRI's GAMS (captrd/expert_support.gms l. 557-557):

          p_maxmin(ms,cols,"comi") $ (expertdairy_map(cols,"comi") $ MS_TO_RMSAGG(ms,"EU013000")) = -0.1 $ (not sameas(ms,"EE000000"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return -0.1 if not ee else 0.0


def p_maxmin_EU13_levl():
    r"""p_maxmin(ms, ., "levl") of EU013000's members.

    CAPRI's GAMS (captrd/expert_support.gms l. 559-559):

          p_maxmin(ms,cols,"levl") $ (expertdairy_map(cols,"levl") $ MS_TO_RMSAGG(ms,"EU013000")) = 0.1;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return 0.1


def p_maxmin_EU14_comi():
    r"""p_maxmin(ms, ., "comi") of EU014000's members.

    CAPRI's GAMS (captrd/expert_support.gms l. 561-561):

          p_maxmin(ms,cols,"comi") $ (expertdairy_map(cols,"comi") $ MS_TO_RMSAGG(ms,"EU014000")) = 0.1 ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return 0.1


def p_maxmin_EU14_levl():
    r"""p_maxmin(ms, ., "levl") of EU014000's members.

    CAPRI's GAMS (captrd/expert_support.gms l. 563-563):

          p_maxmin(ms,cols,"levl") $ (expertdairy_map(cols,"levl") $ MS_TO_RMSAGG(ms,"EU014000")) = -0.2;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return -0.2


def p_maxmin_DK_levl():
    r"""p_maxmin("DK000000", ., "levl").

    CAPRI's GAMS (captrd/expert_support.gms l. 565-565):

          p_maxmin(ms,cols,"levl") $ (expertdairy_map(cols,"levl") $ sameas(ms,"DK000000")) = 0.1;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return 0.1


def P_expertSupprt_gpar(grate, dcow, maxmin, mn, mx):
    r"""P_expertSupprt(RUNR, ., ., "gpar", "absolute"): the logistic's slope matching the growth rate, its range
    widened for the dairy cows (0.1 lower, 0.2 wider) and narrowed by p_maxmin.

    CAPRI's GAMS (captrd/expert_support.gms l. 568-580):

          P_expertSupprt(RUNR,S_ColsEst,S_RowsEst,"gpar","absolute")
                       $ P_expertSupprt(RUNR,S_ColsEst,S_RowsEst,"grate","absolute")
               = P_expertSupprt(RUNR,S_ColsEst,S_RowsEst,"grate","absolute")
               /    (1-p_exTrapMinMax("min")+.1 $ P_T_ActAgg(s_colsEst,"DCOW")
                                            -p_maxmin(runr,S_ColsEst,S_RowsEst))
               / (1-(1-p_exTrapMinMax("min")+.1 $ P_T_ActAgg(s_colsEst,"DCOW")
                                            -p_maxmin(runr,S_ColsEst,S_RowsEst))
        *           Note: Default from dairy is max-min = 1.2-.8 = .4
        *                 For COMI we have effectively max-min = 1.2-.8 +.2 = .6 (to permit higher yield growth)
        *                 For COMI in IR we have max-min = 1.2-.8 +.2 -.2 = .4 (smaller corridor in Ireland)
                   /(p_exTrapMinMax("max")-p_exTrapMinMax("min")+.2 $ P_T_ActAgg(s_colsEst,"DCOW")
                                                                -2*p_maxmin(runr,S_ColsEst,S_RowsEst)
                    ));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    lo = 1 - mn + (0.1 if dcow else 0.0) - maxmin
    span = mx - mn + (0.2 if dcow else 0.0) - 2 * maxmin
    return grate / lo / (1 - lo / span)


def P_expertSupprt_extrap(base, gpar, n, dcow, maxmin, mn, mx):
    r"""P_expertSupprt(RUNR, ., ., ExAnteT, "absolute") after %lst_daitar%: %lst_daitar%'s times the logistic of
    gpar x n (n = OrdT(exAnteT) - OrdT("%lst_daitar%")), 1 without a slope.

    CAPRI's GAMS (captrd/expert_support.gms l. 585-597):

          P_expertSupprt(RUNR,S_ColsEst,S_RowsEst,ExAnteT,"absolute")
                       $ ( P_expertSupprt(RUNR,S_ColsEst,S_RowsEst,"grate","absolute")
                         $ (OrdT(exAnteT) gt OrdT("%lst_daitar%")))
               = P_expertSupprt(RUNR,S_ColsEst,S_RowsEst,"%lst_daitar%","absolute")
               * ((  p_exTrapMinMax("min")-.1 $ P_T_ActAgg(s_colsEst,"DCOW")
                                          +p_maxmin(runr,S_ColsEst,S_RowsEst)
                   +(p_exTrapMinMax("max")-p_exTrapMinMax("min")+.2 $ P_T_ActAgg(s_colsEst,"DCOW")
                                                                -2*p_maxmin(runr,S_ColsEst,S_RowsEst)
                     )
                   *SIGMOID(P_expertSupprt(RUNR,S_ColsEst,S_RowsEst,"gpar","absolute")*(OrdT(exAnteT)-OrdT("%lst_daitar%"))))
                            $ P_expertSupprt(RUNR,S_ColsEst,S_RowsEst,"gpar","absolute")
        *                   in case that the growth rate could not be calculated: use no change
                + 1.        $ (NOT P_expertSupprt(RUNR,S_ColsEst,S_RowsEst,"gpar","absolute")));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    span = mx - mn + (0.2 if dcow else 0.0) - 2 * maxmin
    f = (mn - (0.1 if dcow else 0.0) + maxmin + span * _sigmoid(gpar * n)) if gpar else 1.0
    return base * f


def p_ExpertSupprt_GROF_COMI(cows):
    r"""p_ExpertSupprt(runr, "GROF", "COMI", EXANTET, "absolute") after %lst_daitar%: the cows' yields times their
    levels, in 1000 t.

    cows: (COMI, LEVL) of the dairy cows, in the caller's order.

    CAPRI's GAMS (captrd/expert_support.gms l. 606-609):

          p_ExpertSupprt(runr,"GROF","COMI",EXANTET,"absolute") $ (sum(P_T_ActAgg(s_colsEst,"DCOW"),p_ExpertSupprt(runr,s_colsEst,"COMI",EXANTET,"absolute"))
                                                                 $ (OrdT(exAnteT) gt OrdT("%lst_daitar%")))
              = sum(P_T_ActAgg(s_colsEst,"DCOW"),p_ExpertSupprt(runr,s_colsEst,"COMI",EXANTET,"absolute")
                                                *p_ExpertSupprt(runr,s_colsEst,"LEVL",EXANTET,"absolute"))/1000;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return sum(c * v for c, v in cows) / 1000.0


def p_ExpertSupprt_expost(pdata):
    r"""p_ExpertSupprt(runr, GROF.COMI / DCOW .LEVL .COMI, EXpost, "absolute"): p_data (for display).

    CAPRI's GAMS (captrd/expert_support.gms l. 618-618):

          p_ExpertSupprt(runr,"GROF","COMI",EXpost,"absolute") =P_Result(runr,"GROF","COMI",exPost,"p_data");

    CAPRI's GAMS (captrd/expert_support.gms l. 619-621):

          p_ExpertSupprt(runr,S_ColsEst,S_RowsEst,EXpost,"absolute")
            $ (  P_T_ActAgg(s_colsEst,"DCOW") $ (sameas(s_rowsEst,"LEVL") or sameas(s_rowsEst,"COMI") ))
            =P_Result(runr,S_ColsEst,S_RowsEst,exPost,"p_data");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return pdata


def P_expertSupprt_EU_yield(cows):
    r"""P_expertSupprt("A_EU_WEST" / "A_EU_EAST", DCOW, "COMI", yearsCur, "absolute"): the members' yields weighted by
    their levels.

    cows: (COMI, LEVL) of the members, in the caller's order.

    CAPRI's GAMS (captrd/expert_support.gms l. 624-630):

          P_expertSupprt("A_EU_WEST",S_ColsEst,S_RowsEst,yearsCur,"absolute")
                 $ (  P_T_ActAgg(s_colsEst,"DCOW") $ (sameas(s_rowsEst,"COMI") )
                    $ SUM(MS_TO_RMSAGG(ms,"A_EU_WEST"),   P_expertSupprt(ms,S_ColsEst,"LEVL",yearsCur,"absolute") )
                   $ (OrdT("Lst_exAnte") gt ORDT("%lst_daitar%")))
             = SUM(MS_TO_RMSAGG(ms,"A_EU_WEST"), P_expertSupprt(ms,S_ColsEst,S_RowsEst,yearsCur,"absolute")
                                                 * P_expertSupprt(ms,S_ColsEst,"LEVL",yearsCur,"absolute") )
             / SUM(MS_TO_RMSAGG(ms,"A_EU_WEST"),   P_expertSupprt(ms,S_ColsEst,"LEVL",yearsCur,"absolute") );

    CAPRI's GAMS (captrd/expert_support.gms l. 632-638):

          P_expertSupprt("A_EU_EAST",S_ColsEst,S_RowsEst,yearsCur,"absolute")
                 $ (  P_T_ActAgg(s_colsEst,"DCOW") $ (sameas(s_rowsEst,"COMI") )
                    $ SUM(MS_TO_RMSAGG(ms,"A_EU_EAST"),   P_expertSupprt(ms,S_ColsEst,"LEVL",yearsCur,"absolute") )
                   $ (OrdT("Lst_exAnte") gt ORDT("%lst_daitar%")))
             = SUM(MS_TO_RMSAGG(ms,"A_EU_EAST"), P_expertSupprt(ms,S_ColsEst,S_RowsEst,yearsCur,"absolute")
                                                 * P_expertSupprt(ms,S_ColsEst,"LEVL",yearsCur,"absolute") )
             / SUM(MS_TO_RMSAGG(ms,"A_EU_EAST"),   P_expertSupprt(ms,S_ColsEst,"LEVL",yearsCur,"absolute") );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return sum(c * v for c, v in cows) / sum(v for c, v in cows)


def P_expertSupprt_EU_sum(members):
    r"""P_expertSupprt("A_EU_WEST" / "A_EU_EAST", DCOW .LEVL / GROF.COMI, yearsCur, "absolute"): the members'
    summed.

    CAPRI's GAMS (captrd/expert_support.gms l. 641-644):

          P_expertSupprt("A_EU_WEST",S_ColsEst,S_RowsEst,yearsCur,"absolute")
                 $ (  P_T_ActAgg(s_colsEst,"DCOW") $ (sameas(s_rowsEst,"LEVL") )
                   $ (OrdT("Lst_exAnte") gt ORDT("%lst_daitar%")))
             = SUM(MS_TO_RMSAGG(ms,"A_EU_WEST"),   P_expertSupprt(ms,S_ColsEst,"LEVL",yearsCur,"absolute") );

    CAPRI's GAMS (captrd/expert_support.gms l. 646-649):

          P_expertSupprt("A_EU_EAST",S_ColsEst,S_RowsEst,yearsCur,"absolute")
                 $ (  P_T_ActAgg(s_colsEst,"DCOW") $ (sameas(s_rowsEst,"LEVL") )
                   $ (OrdT("Lst_exAnte") gt ORDT("%lst_daitar%")))
             = SUM(MS_TO_RMSAGG(ms,"A_EU_EAST"),   P_expertSupprt(ms,S_ColsEst,"LEVL",yearsCur,"absolute") );

    CAPRI's GAMS (captrd/expert_support.gms l. 652-655):

          P_expertSupprt("A_EU_WEST",S_ColsEst,S_RowsEst,yearsCur,"absolute")
                 $ (  sameas(s_colsEst,"GROF") $ (sameas(s_rowsEst,"COMI") )
                   $ (OrdT("Lst_exAnte") gt ORDT("%lst_daitar%")))
             = SUM(MS_TO_RMSAGG(ms,"A_EU_WEST"), P_expertSupprt(ms,S_ColsEst,S_RowsEst,yearsCur,"absolute"));

    CAPRI's GAMS (captrd/expert_support.gms l. 657-660):

          P_expertSupprt("A_EU_EAST",S_ColsEst,S_RowsEst,yearsCur,"absolute")
                 $ (  sameas(s_colsEst,"GROF") $ (sameas(s_rowsEst,"COMI") )
                   $ (OrdT("Lst_exAnte") gt ORDT("%lst_daitar%")))
             = SUM(MS_TO_RMSAGG(ms,"A_EU_EAST"), P_expertSupprt(ms,S_ColsEst,S_RowsEst,yearsCur,"absolute"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return sum(members)


def p_ExpertSupprt_DOMM_PRCM_COMI(value_daitar, grof, grof_daitar):
    r"""p_ExpertSupprt(ms, "DOMM" / "PRCM", "COMI", EXANTET, "absolute") after %lst_daitar%: moved with GROF.COMI.

    CAPRI's GAMS (captrd/expert_support.gms l. 668-674):

          p_ExpertSupprt(ms,s_colsEst,"COMI",EXANTET,"absolute") $ ( (sameas(s_colsEst,"DOMM") or sameas(s_colsEst,"PRCM"))
                                                                   $ (P_expertSupprt(MS,S_ColsEst,"COMI","%lst_daitar%","absolute") GT 1.E-4)
                                                                   $ (P_expertSupprt(MS,"GROF","COMI","%lst_daitar%","absolute") GT 1.E-4)
                                                                   $ (OrdT(exAnteT) gt OrdT("%lst_daitar%")))
              = P_expertSupprt(MS,S_ColsEst,"COMI","%lst_daitar%","absolute")
              * p_ExpertSupprt(ms,"GROF","COMI",EXANTET,"absolute")
              / P_expertSupprt(MS,"GROF","COMI","%lst_daitar%","absolute");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return value_daitar * grof / grof_daitar


def p_ExpertSupprt_MAPR_MILK(prcm_comi, prcm_sgmi):
    r"""p_ExpertSupprt(ms, "MAPR", "MILK", EXANTET, "absolute"): the cow milk processed plus the sheep and goat milk's
    support.

    CAPRI's GAMS (captrd/expert_support.gms l. 679-683):

          p_ExpertSupprt(ms,"MAPR","MILK",EXANTET,"absolute") $ p_ExpertSupprt(ms,"PRCM","COMI",EXANTET,"absolute")

              = p_ExpertSupprt(ms,"PRCM","COMI",EXANTET,"absolute")
        *         using the standard (trend based) support for sheep and goat milk to estimate aggregate MILK processing
              + P_Result(MS,"PRCM","SGMI",ExanteT,"support");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return prcm_comi + prcm_sgmi


def p_ExpertSupprt_dairy_Trustlevl(less, stable, n):
    r"""p_ExpertSupprt(runr, expertdairy_map, exanteT, "Trustlevl"): 8 (3 for EAAG, MAPR, PRCM, DOMM), x 0.99 a year
    after %lst_daitar% (x 1.01 for the milk production of the regions listed).

    less: EAAG, MAPR, PRCM or DOMM; stable: GROF.COMI of a listed region; n: OrdT(ExAnteT) - OrdT("%lst_daitar%").

    CAPRI's GAMS (captrd/expert_support.gms l. 687-707):

          p_ExpertSupprt(runr,Cols,Rows,exanteT,"Trustlevl") $ ( p_ExpertSupprt(runr,Cols,Rows,EXANTET,"absolute")
                                                               $ expertdairy_map(Cols,Rows))
             = (8 - 5 $ (sameas(Cols,"EAAG") or sameas(Cols,"MAPR")  or sameas(Cols,"PRCM") or sameas(Cols,"DOMM")))
        *                                                           impose more stability in some countries after trial and error
             *(.99+.02 $ (sameas(cols,"grof") $ sameas(rows,"comi") $ (   map_rr("HR000000",runr)
                                                                       or map_rr("IR000000",runr)
                                                                       or map_rr("RO000000",runr)
                                                                       or map_rr("LT000000",runr)
                                                                       or map_rr("LV000000",runr)
                                                                       or map_rr("HU000000",runr)
                                                                       or map_rr("SI000000",runr)
                                                                       or map_rr("SK000000",runr)
                                                                       or map_rr("IT000000",runr)
                                                                       or map_rr("MT000000",runr)
                                                                       or map_rr("PT000000",runr)
                                                                       or map_rr("FR000000",runr)
                                                                       or map_rr("SE000000",runr)
                                                                       or map_rr("FI000000",runr)
                                                                       or map_rr("TUR",runr)
                                                                       )
                         ))**max(0,ORDT(ExAnteT) - ORDT("%lst_daitar%"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return (8.0 - (5.0 if less else 0.0)) * (0.99 + (0.02 if stable else 0.0)) ** max(0, n)


def p_ExpertSupprt_EXPE_Trustlevl():
    r"""p_ExpertSupprt(runr, "EXPE", "COMI", exanteT, "Trustlevl").

    CAPRI's GAMS (captrd/expert_support.gms l. 710-710):

          p_ExpertSupprt(runr,"EXPE","COMI",exanteT,"Trustlevl") $ p_ExpertSupprt(runr,"EXPE","COMI",EXANTET,"absolute") = .1;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return .1


def P_Result_share_COMI(hcom, grof):
    r"""P_Result(., "share", "COMI", ., "support1"): HCOM over GROF of raw milk (the aggregates' from DG AGRI, the
    member states' ex post from p_data, the non-EU's ex ante from the supports).

    CAPRI's GAMS (captrd/expert_support.gms l. 719-720):

          P_Result(CurEuropAgg,"share","COMI",yearscur,"support1") $ P_Result(CurEuropAgg,"GROF","COMI",yearscur,"dgagri")
              = P_Result(CurEuropAgg,"HCOM","COMI",yearscur,"dgagri")/P_Result(CurEuropAgg,"GROF","COMI",yearscur,"dgagri");

    CAPRI's GAMS (captrd/expert_support.gms l. 731-732):

          P_Result(MS,"share","COMI",expostT,"support1") $ P_Result(MS,"GROF","COMI",expostT,"p_data")
              = P_Result(MS,"HCOM","COMI",expostT,"p_data")/P_Result(MS,"GROF","COMI",expostT,"p_data");

    CAPRI's GAMS (captrd/expert_support.gms l. 747-748):

          P_Result(MSnoEU28,"share","COMI",exanteT,"support1") $ P_Result(MSnoEU28,"GROF","COMI",exanteT,"support")
              = P_Result(MSnoEU28,"HCOM","COMI",exanteT,"support")/P_Result(MSnoEU28,"GROF","COMI",exanteT,"support");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return hcom / grof


def P_Result_share_COMI_MS(share_lst, aggregates):
    r"""P_Result(MS, "share", "COMI", exanteT, "support1"): the last ex-post share times its aggregates' change.

    aggregates: (the year's share, the last ex-post one) of the member state's aggregates, in the caller's order.

    CAPRI's GAMS (captrd/expert_support.gms l. 735-739):

          P_Result(MS,"share","COMI",exanteT,"support1")
              $ sum(MS_TO_RMSAGG(MS,CurEuropAgg),P_Result(CurEuropAgg,"share","COMI",exanteT,"support1"))
              = sum(lst_expostT,P_Result(MS,"share","COMI",lst_expostT,"support1")
                              * sum(MS_TO_RMSAGG(MS,CurEuropAgg),P_Result(CurEuropAgg,"share","COMI",exanteT,"support1")
                                                                /P_Result(CurEuropAgg,"share","COMI",lst_expostT,"support1") ));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return share_lst * sum(a / b for a, b in aggregates)


def P_Result_share_COMI_kept(share):
    r"""P_Result(., "share", "COMI", ., "support1"): %lst_dgagri%'s after it (EU member states); the year before's where
    it would rise or is missing (non-EU).

    CAPRI's GAMS (captrd/expert_support.gms l. 742-744):

          P_Result(MS,"share","COMI",exanteT,"support1") $ ( (ordt(exanteT) gt ordT("%lst_dgagri%")) $ sum(MS_TO_RMSAGG(MS,CurEuropAgg),1))
        *      = sum(exante $ (ordt(exante) eq ordT("%lst_dgagri%")), P_Result(MS,"share","COMI",exante,"support1") );
              = sum(Lst_DGAgri, P_Result(MS,"share","COMI",Lst_DGAgri,"support1") );

    CAPRI's GAMS (captrd/expert_support.gms l. 752-755):

              P_Result(MSnoEU28,"share","COMI",simulationYear,"support1")
              $ (   (P_Result(MSnoEU28,"share","COMI",simulationYear,"support1") gt P_Result(MSnoEU28,"share","COMI",simulationYear-1,"support1"))
                 or (not P_Result(MSnoEU28,"share","COMI",simulationYear,"support1")))
              = P_Result(MSnoEU28,"share","COMI",simulationYear-1,"support1") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (dairy_supports.dairy)."""
    return share


def P_Result_support_herd_floor(support, bas, bast, year, base_year, bast_year, lst_exante):
    r"""P_Result(MS, MAact, HerdLevl, ExAnteT, "support"): at least 90% a year of BAS (and of BAST, the smaller),
    and at least a linear decline to 20% of them by Lst_exAnte.

    CAPRI's GAMS (captrd/expert_support.gms l. 794-808):

             P_Result(MS,MAact,HerdLevl,ExAnteT,"support")
               = max( P_Result(MS,MAact,HerdLevl,ExAnteT,"support"),
                     (P_DATA(MS,mAACT,herdLevl,"BAS") *.9**(OrdT(ExanteT)-OrdT("BAS")))
                      $ (not P_DATA(MS,mAACT,herdLevl,"BAST")),
                     min( P_DATA(MS,mAACT,herdLevl,"BAST")*.9**(OrdT(ExanteT)-OrdT("BAST")),
                          P_DATA(MS,mAACT,herdLevl,"BAS")*.9**(OrdT(ExanteT)-OrdT("BAS")))
                      $ (    P_DATA(MS,mAACT,herdLevl,"BAST")),
                    (P_DATA(MS,mAACT,herdLevl,"BAS") *(1-.8*(OrdT(ExanteT)-OrdT("BAS"))
                                                           /(OrdT("Lst_exAnte")-OrdT("BAS"))))
                      $ (not P_DATA(MS,mAACT,herdLevl,"BAST")) ,
                     min( P_DATA(MS,mAACT,herdLevl,"BAST") *(1- .8*(OrdT(ExanteT)-OrdT("BAST"))
                                                                  /(OrdT("Lst_exAnte")-OrdT("BAST"))),
                          P_DATA(MS,mAACT,herdLevl,"BAS")  *(1-.8*(OrdT(ExanteT)-OrdT("BAS"))
                                                                 /(OrdT("Lst_exAnte")-OrdT("BAS"))))
                      $      P_DATA(MS,mAACT,herdLevl,"BAST"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_support.herd_floor; national_supports.supports for CS000000)."""
    if bast:
        f1 = min(bast * 0.9 ** (year - bast_year), bas * 0.9 ** (year - base_year))
        f2 = min(bast * (1 - 0.8 * (year - bast_year) / (lst_exante - bast_year)),
                 bas * (1 - 0.8 * (year - base_year) / (lst_exante - base_year)))
    else:
        f1 = bas * 0.9 ** (year - base_year)
        f2 = bas * (1 - 0.8 * (year - base_year) / (lst_exante - base_year))
    return max(support, f1, f2)


def p_ExpertSupprt_TOOU(support):
    r"""p_ExpertSupprt(MS, S_ColsEst, "TOOU", exAnte, "Absolute") without a trust level, where the output's price has
    expert information: the support.

    CAPRI's GAMS (captrd/expert_support.gms l. 817-823):

           p_ExpertSupprt(MS,S_ColsEst,"TOOU",exAnte,"Absolute")
             $ (   (NOT p_ExpertSupprt(MS,S_ColsEst,"TOOU",exAnte,"trustLevl"))
                 $ SUM(PACT_TO_Y(s_ColsEst,O) $ (   p_ExpertSupprt(MS,"UVAG",O,exAnte,"PercentChange")
                                                 or p_ExpertSupprt(MS,"UVAG",O,exAnte,"Absolute")
                                                 or P_Result(MS,"UVAG",O,ExAnte,"Longrun1")      ),   1)
                 $ P_Result(MS,S_ColsEst,"TOOU",exAnte,"Support"))
               = P_Result(MS,S_ColsEst,"TOOU",exAnte,"Support");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_support.toou)."""
    return support


def p_ExpertSupprt_TOOU_trustLevl(support, basm):
    r"""p_ExpertSupprt(MS, S_ColsEst, "TOOU", exAnte, "trustLevl"): half the support's ratio to BASM, at most 0.5, at
    least 0.5E-10.

    CAPRI's GAMS (captrd/expert_support.gms l. 826-834):

           p_ExpertSupprt(MS,S_ColsEst,"TOOU",exAnte,"trustLevl")
             $ (   (NOT p_ExpertSupprt(MS,S_ColsEst,"TOOU",exAnte,"trustLevl"))
                 $ SUM(PACT_TO_Y(s_ColsEst,O) $ (   p_ExpertSupprt(MS,"UVAG",O,exAnte,"PercentChange")
                                                 or p_ExpertSupprt(MS,"UVAG",O,exAnte,"Absolute")
                                                 or P_Result(MS,"UVAG",O,ExAnte,"Longrun1")      ),   1)
                 $ P_Result(MS,S_ColsEst,"TOOU",exAnte,"Support"))
               = 0.5*MAX(1.E-10,MIN(1,( P_Result(MS,S_ColsEst,"TOOU",exAnte,"Support")
                                      /P_Result(MS,S_ColsEst,"TOOU",exAnte,"BASM"))
                                     $ P_Result(MS,S_ColsEst,"TOOU",exAnte,"BASM"))) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (expert_support.toou)."""
    return 0.5 * max(1.e-10, min(1.0, support / basm) if basm else 0.0)


def _sigmoid(x):
    """GAMS's SIGMOID(x) = 1 / (1 + exp(-x))."""
    return 1.0 / (1.0 + math.exp(-x))
