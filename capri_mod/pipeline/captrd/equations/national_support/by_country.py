r"""CAPTRD's country rules of the national expert supports: AT, BL, DE, EL, IT, PT, CY, CS, BA, EE, RO, NO, TUR (moved
from capri_mod/pipeline/captrd/equations/national_supports.py as they were, 26 November 2026).
"""
from __future__ import annotations




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
