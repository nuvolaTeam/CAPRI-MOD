r"""CAPTRD's expert bounds on p_result, Belgium's (BL4) included (moved from
capri_mod/pipeline/captrd/equations/national_supports.py as they were, 26 November 2026).
"""
from __future__ import annotations




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
