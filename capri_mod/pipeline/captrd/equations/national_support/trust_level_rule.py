r"""CAPTRD's trust level rule of the national expert supports (p_ExpertSupprt_trustlevl_rule) (moved from
capri_mod/pipeline/captrd/equations/national_supports.py as it was, 26 November 2026).
"""
from __future__ import annotations




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
