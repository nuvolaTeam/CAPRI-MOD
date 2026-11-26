r"""CAPTRD's national expert supports of the dairy cows, the cow milk and the sheep and goats, and their copies (moved
from capri_mod/pipeline/captrd/equations/national_supports.py as they were, 26 November 2026).
"""
from __future__ import annotations




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
