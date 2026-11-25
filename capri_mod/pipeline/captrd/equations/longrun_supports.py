r"""CAPTRD's statements of captrd/longrun_supports.gms (CAPRI star 3.0, included by expert_support.gms l. 786; with
%GlobiomAact% and %FixExogenFactGlobiom% off): the expert supports from the long-run sources, as named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). capri_mod/pipeline/captrd/longrun_supports.py (supports) holds the loops over
the member states, the positions and the long-run years, the conditions and the order, and calls them; so does
capri_mod/pipeline/captrd/macro.py (inha_pdata) for INHA's p_data (l. 368-389). The arithmetic is the port's, so the
supports are unchanged.
"""
from __future__ import annotations


def P_DATA_B2000(values):
    r"""P_DATA(RMall, COLS, ROWS, "B2000"): the 1999-2001 mean of p_data over the years with a value.

    values: the nonzero values of the years B2000yr, in order.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 43-64):

           P_DATA(RMall,COLS,ROWS,"B2000")
             $ (   SUM(B2000yr, P_Result(RMall,Cols,Rows,B2000Yr,"P_Data"))
               $  (    SAMEAS(COLS,"UVAG") or SAMEAS(COLS,"DOMM") or SAMEAS(COLS,"GROF")
                    or SAMEAS(COLS,"MAPR") or SAMEAS(ROWS,"LEVL") or SAMEAS(ROWS,"HERD")
        *           Since many years the GLOBIOM breakdown of total demand into HCOM, FEDM, BIOF has not been used,
        *           because the demand side components from GLOBIOM often differ from CAPRI (mostly due to booking differences
        *           FAO <=> Eurocstat) and an adhoc breakdown has been used for the demand components. The resulting CAPRI projetions
        *           for HCOM often showed implausible demand growth while the original HCOM projections from GLOBIOM appeared more reasonable.
        *           => In connection with the following GLOBIOM file we started to also use the HCOM projection (not yet tested
        *           with other GLOBIOM files but might also improve demand projections there)
        $ifi "%SelecScen%"=="globiom_eu_bright_s0_2023+REFERENCE+REFERENCE"  or SAMEAS(COLS,"HCOM")
        $ifi "%SelecScen%"=="GLOBIOM_EU_EUCLIMIT6_S2_50CV"                   or SAMEAS(COLS,"HCOM")
        *              THere will be no external supports but B2000 helps in communicating feed efficiency:
                    or (REQ_FEED(ROWS) $ PACT(COLS))
                    or ReqsT(Rows)
        *              To use the change factor of GROF.COMI
        *              also for PRCM.COMI and PRCM.MILK:
                    or ((SAMEAS(ROWS,"MILK") or SAMEAS(ROWS,"COMI")) $ SAMEAS(COLS,"PRCM"))
        *              Implied yields will be calculated if atributable to a single activity:
                    or (PACT_TO_Y(COLS,ROWS) $ OfromOnePact(ROWS))  )
               $  (OrdT('lst_exAnte') GE  OrdT('%lst_dgagri%')) )
               = SUM(B2000yr, P_Result(RMall,Cols,Rows,B2000Yr,"P_Data") ) / SUM(B2000yr $ P_Result(RMall,Cols,Rows,B2000Yr,"P_Data") ,1 );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (longrun_supports.supports)."""
    return sum(values) / len(values)


def p_result_B2000(value):
    r"""p_result(RMall, S_ColsEst, S_RowsEst, Exante, "B2000") of a series with nObs: B2000.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 68-69):

           p_result(RMall,S_ColsEst,S_RowsEst,Exante,"B2000") $ p_data(RMall,S_ColsEst,S_RowsEst,"nObs")
              = p_data(RMall,S_ColsEst,S_RowsEst,"B2000");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (longrun_supports.supports)."""
    return value


def p_longrunInfo(value):
    r"""p_longrunInfo(MS, ., ., info, longYr) and the shares of B2000: the selected scenario's p_longRunInfoAll.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 107-107):

          p_longrunInfo(MS,cols,rows,info,longYr) = p_longRunInfoAll(MS,cols,rows,info,"%SelecScen%",longYr) ;

    CAPRI's GAMS (captrd/longrun_supports.gms l. 110-110):

          p_longrunInfo(MS,cols,rows,"share","B2000") = p_longRunInfoAll(MS,cols,rows,"share","%SelecScen%","B2000") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (longrun_supports.supports)."""
    return value


def p_longrunInfo_2000():
    r"""p_longrunInfo(MS / "World", ., ., "factorB2000", "2000") of a series with a factor: 1.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 113-114):

          p_longrunInfo(MS,cols,rows,'factorB2000',"2000") $ SUM(longYr $ p_longRunInfoAll(MS,cols,rows,'factorB2000',"%SelecScen%",longYr),1)
               = 1;

    CAPRI's GAMS (captrd/longrun_supports.gms l. 119-119):

            p_longrunInfo('World',cols,rows,'factorB2000',"2000") $ SUM(longYr $ p_longrunInfo('World',cols,rows,'factorB2000',longYr),1)=1;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (longrun_supports.supports)."""
    return 1.0


def p_longrunInfo_World_oils(soya):
    r"""p_longrunInfo("World", "UVAP", "RAPE" / "SUNF", "factorB2000", years): soya's price factor.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 117-117):

            p_longrunInfo('World','UVAP','RAPE','factorB2000',years) = p_longrunInfo('World','UVAP','SOYA','factorB2000',years) ;

    CAPRI's GAMS (captrd/longrun_supports.gms l. 118-118):

            p_longrunInfo('World','UVAP','SUNF','factorB2000',years) = p_longrunInfo('World','UVAP','SOYA','factorB2000',years) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (longrun_supports.supports)."""
    return soya


def p_longrunInfo_PROD_SGM(factor_from):
    r"""p_longrunInfo("PL000000", "PROD", "SGMT" / "SGMI", "factorB2000", longYr) after 2030 (bright) or 2040 (cv50):
    the factor of that year.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 158-160):

          p_longrunInfo(MSincl,"PROD",rows,'factorB2000',longYr)  $ ( (Ordt(longYr) gt Ordt("2030")) $ sameas(MSincl,"PL000000")
                                                                    $ (sameas(rows,"SGMT") or sameas(rows,"SGMI")))
              =   p_longrunInfo(MSincl,"PROD",rows,'factorB2000',"2030") ;

    CAPRI's GAMS (captrd/longrun_supports.gms l. 178-180):

          p_longrunInfo(MSincl,"PROD",rows,'factorB2000',longYr)  $ ( (Ordt(longYr) gt Ordt("2040")) $ sameas(MSincl,"PL000000")
                                                                    $ (sameas(rows,"SGMT") or sameas(rows,"SGMI")))
              =   p_longrunInfo(MSincl,"PROD",rows,'factorB2000',"2040") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (longrun_supports.supports)."""
    return factor_from


def p_longrunInfo_PROD_EGGS(prod_2030, domm, domm_2030):
    r"""p_longrunInfo(NO, CY, MT, "PROD", "EGGS", "factorB2000", longYr) after 2030 (bright): 2030's production factor
    moved with demand's.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 164-169):

          p_longrunInfo(MSincl,"PROD",rows,'factorB2000',longYr)  $ ( (Ordt(longYr) gt Ordt("2030"))
                                                                    $ (sameas(MSincl,"NO000000") or sameas(MSincl,"CY000000") or sameas(MSincl,"MT000000"))
                                                                    $ p_longrunInfo(MSincl,"DOMM",rows,'factorB2000',"2030")
                                                                    $ sameas(rows,"EGGS") )
              =   p_longrunInfo(MSincl,"PROD",rows,'factorB2000',"2030")
                * p_longrunInfo(MSincl,"DOMM",rows,'factorB2000',longYr)/p_longrunInfo(MSincl,"DOMM",rows,'factorB2000',"2030") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (longrun_supports.supports)."""
    return prod_2030 * domm / domm_2030


def p_longrunInfo_suga_dropped():
    r"""p_longrunInfo(MS, mrkBaleE, "suga", info, longYr) where biofuel takes more than 80% of sugar: removed.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 185-185):

            p_longrunInfo(MS,mrkBaleE,"suga",info,longYr) $ (p_longrunInfo(MS,"biof","suga","share",longYr) gt .8) = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (longrun_supports.supports)."""
    return 0.0


def P_Result_Longrun(factor, b2000):
    r"""P_Result(MS, ., longYr, "Longrun") of the levels (not of herds), production (GROF from PROD, not IHEI and YHEI),
    market production (MAPR from PROD), demand (DOMM) and milk processing (PRCM from PROD): the long-run factor times
    B2000.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 196-200):

           P_Result(MS,Cols,'LEVL',longYr,'Longrun') $ (    P_DATA(MS,COLS,'LEVL','BASM')
        *                                              See NOTE2 on "virtual" animals in GLOBIOM
        $ifi %GlobiomAact%==off                          and (NOT P_DATA(MS,COLS,'HERD','BASM'))
                                                       )
               = p_longrunInfo(MS,COLS,'LEVL','factorB2000',longYr)*P_DATA(MS,COLS,'LEVL','B2000');

    CAPRI's GAMS (captrd/longrun_supports.gms l. 202-207):

           P_Result(MS,'GROF',Rows,longYr,'Longrun') $ (    P_DATA(MS,'GROF',ROWS,'BASM')
        *                                              derived from HEIR.LEVL in convert_globiom, about line 944
        *                                              => excluded due to NOTE2 above on GLOBIOM "virtual" animals
        $ifi %GlobiomAact%==off                          and (NOT (SAMEAS(ROWS,"IHEI") or SAMEAS(ROWS,"YHEI")))
                                                       )
               = p_longrunInfo(MS,'PROD',rows,'factorB2000',longYr)*P_DATA(MS,'GROF',ROWS,'B2000');

    CAPRI's GAMS (captrd/longrun_supports.gms l. 277-279):

           P_Result(MS,'MAPR',Rows,longYr,'Longrun') $ ( (OrdT('lst_exAnte') GE  OrdT('%lst_dgagri%'))
                                                      $ P_DATA(MS,'MAPR',ROWS,'BASM'))
               = p_longrunInfo(MS,'PROD',rows,'factorB2000',longYr)*P_DATA(MS,'MAPR',ROWS,'B2000');

    CAPRI's GAMS (captrd/longrun_supports.gms l. 287-289):

           P_Result(MS,'DOMM',Rows,longYr,'Longrun') $ ( (OrdT('lst_exAnte') GE  OrdT('%lst_dgagri%'))
                                                      $ P_DATA(MS,'DOMM',ROWS,'BASM'))
               = p_longrunInfo(MS,'DOMM',rows,'factorB2000',longYr)*P_DATA(MS,'DOMM',ROWS,'B2000');

    CAPRI's GAMS (captrd/longrun_supports.gms l. 291-292):

           P_Result(MS,'PRCM',Rows,longYr,'Longrun') $ ( (SAMEAS(ROWS,"MILK") or SAMEAS(ROWS,"COMI")))
             = p_longrunInfo(MS,'PROD',rows,'factorB2000',longYr)*P_DATA(MS,'PRCM',ROWS,'B2000');

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (longrun_supports.supports)."""
    return factor * b2000


def P_Result_Longrun_small():
    r"""P_Result(MS, ., "LEVL" / GROF, longYr, "Longrun") where the long-run source's own B2000 is below a tenth of
    CAPRI's: removed.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 212-216):

           P_Result(MS,Cols,'LEVL',longYr,'Longrun') $ ((   (0.1*P_DATA(MS,COLS,'LEVL','B2000'))
                                                          gt p_longRunInfoAll(MS,cols,"LEVL","data","%SelecScen%","B2000"))
                                                        $  p_longRunInfoAll(MS,cols,"LEVL","data","%SelecScen%","B2000")
                                                        $  (not sameas(cols,"INHA")))
               = 0;

    CAPRI's GAMS (captrd/longrun_supports.gms l. 218-221):

           P_Result(MS,'GROF',Rows,longYr,'Longrun') $ ( (   (0.1*P_DATA(MS,'GROF',ROWS,'B2000'))
                                                           gt p_longRunInfoAll(MS,'PROD',ROWS,"data","%SelecScen%","B2000"))
                                                        $ p_longRunInfoAll(MS,'PROD',ROWS,"data","%SelecScen%","B2000"))
               = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (longrun_supports.supports)."""
    return 0.0


def p_result_longrun_yield(prod, levl, b2000):
    r"""p_result(MS, COLS, ROWS, longYr, "longrun") of an output of one production activity: the production factor over
    the level factor times B2000.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 228-236):

           p_result(MS,COLS,ROWS,longYr,"longrun") $ (    (   p_longrunInfo(MS,'PROD',rows,'factorB2000',longYr)
                                                            $ p_longrunInfo(MS,COLS,'LEVL','factorB2000',longYr))
                                                      and PACT_TO_Y(COLS,ROWS)
        *                                                See NOTE2 above on "virtual" animals in GLOBIOM
        $ifi %GlobiomAact%==off                       and (NOT P_DATA(MS,COLS,'HERD','BASM'))
                                                      and P_Result(MS,'GROF',Rows,longYr,'Longrun')
                                                      and OfromOnePact(ROWS))
             = p_longrunInfo(MS,'PROD',rows,'factorB2000',longYr)
              /p_longrunInfo(MS,COLS,'LEVL','factorB2000',longYr)*P_DATA(MS,COLS,ROWS,'B2000');

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (longrun_supports.supports)."""
    return prod / levl * b2000


def P_Result_Longrun_UVAG(factor, b2000, infl, n):
    r"""P_Result(MS, "UVAG", ., longYr, "Longrun") (COMI from MILK's): the price factor times B2000, inflated by p_infl
    over the n = OrdT(longYr) - OrdT("Bas") years.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 280-283):

           P_Result(MS,'UVAG',Rows,longYr,'Longrun') $ ( (OrdT('lst_exAnte') GE  OrdT('%lst_dgagri%'))
                                                      $ P_DATA(MS,'UVAG',ROWS,'BASM'))
        *        according to an email by S Frank to pw 10.07.12 PRICES ARE REAL AND IN YR 2000 USD (we ignore exchange rate changes)
               = p_longrunInfo(MS,'UVAP',rows,'factorB2000',longYr)*P_DATA(MS,'UVAG',ROWS,'B2000')*p_infl**(OrdT(longYr)-Ordt("Bas"));

    CAPRI's GAMS (captrd/longrun_supports.gms l. 284-286):

           P_Result(MS,'UVAG',"COMI",longYr,'Longrun') $ ( (OrdT('lst_exAnte') GE  OrdT('%lst_dgagri%'))
                                                        $ P_DATA(MS,'UVAG',"COMI",'BASM'))
               = p_longrunInfo(MS,'UVAP',"MILK",'factorB2000',longYr)*P_DATA(MS,'UVAG',"COMI",'B2000')*p_infl**(OrdT(longYr)-Ordt("Bas"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (longrun_supports.supports)."""
    return factor * b2000 * infl ** n


def P_Result_Longrun_HCOM(share, share_b2000, domm, b2000):
    r"""P_Result(MS, "HCOM", ., longYr, "Longrun"): GLOBIOM's food share's change times demand's factor times B2000.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 303-305):

           P_Result(MS,'HCOM',Rows,longYr,'Longrun') $ (p_longrunInfo(MS,'HCOM',rows,'share',"B2000"))
              =  p_longrunInfo(MS,'HCOM',rows,'share',longYr)/p_longrunInfo(MS,'HCOM',rows,'share',"B2000")
                *p_longrunInfo(MS,'DOMM',rows,'factorB2000',longYr)*P_DATA(MS,'HCOM',ROWS,'B2000');

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (longrun_supports.supports)."""
    return share / share_b2000 * domm * b2000


def P_Result_Longrun_fill(value, value_next, year, long_year, long_next):
    r"""P_Result(MS, ., Fillyears, "Longrun"): linear between the long-run years.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 320-324):

              P_Result(MS,Cols,Rows,Fillyears,"Longrun") $ SUM( (longYr1) $ P_Result(MS,Cols,Rows,longYr1,"Longrun"),1)
              =  P_Result(MS,Cols,Rows,longYr,"Longrun")
              +  (ORDT(Fillyears)-ORDT(longYr))
              *  (P_Result(MS,Cols,Rows,longYr+1,"Longrun") - P_Result(MS,Cols,Rows,longYr,"Longrun"))
              /  (ORDT(longYr+1)-ORDT(longYr));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (longrun_supports.supports)."""
    return value + (year - long_year) * (value_next - value) / (long_next - long_year)


def P_Result_Longrun_dropped():
    r"""P_Result(MS, ., years, "Longrun") outside yearsCur, and ex post but 2000, BAST, BAS and INHA.LEVL: removed.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 326-326):

           P_Result(MS,Cols,Rows,years,"Longrun") $ (NOT yearsCur(years)) = 0;

    CAPRI's GAMS (captrd/longrun_supports.gms l. 329-332):

           P_Result(MS,Cols,Rows,expostT,"Longrun") $ (NOT (   (ORDT(expostT) eq ORDT("2000"))
                                                            or (ORDT(expostT) EQ ORDT("BAST"))
                                                            or (ORDT(expostT) EQ ORDT("BAS"))
                                                            or (SAMEAS(cols,"INHA") $ SAMEAS(rows,"LEVL") ))) = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (longrun_supports.supports)."""
    return 0.0


def P_Result_fac_Longrun(base, longrun):
    r"""P_Result(MS, ., "fac", "Longrun"): BAST (else BASM) over the long-run value of BAST's year (else of %baseyear%),
    where that is above 1% of it.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 342-349):

           P_Result(MS,Cols,Rows,"fac","Longrun")
              $ (  (  SUM(bastY, P_Result(MS,Cols,Rows,bastY,"Longrun")) $      P_DATA(MS,COLS,ROWS,"BAST")
                    + P_Result(MS,Cols,Rows,"%baseyear%","Longrun")      $ (NOT P_DATA(MS,COLS,ROWS,"BAST")))
                gt  (1.E-2*abs(P_DATA(MS,COLS,ROWS,"BAST") + P_DATA(MS,COLS,ROWS,"BASM") $ (NOT P_DATA(MS,COLS,ROWS,"BAST")))))
              = (P_DATA(MS,COLS,ROWS,"BAST") + P_DATA(MS,COLS,ROWS,"BASM") $ (NOT P_DATA(MS,COLS,ROWS,"BAST")))
              / (  SUM(bastY, P_Result(MS,Cols,Rows,bastY,"Longrun")) $      P_DATA(MS,COLS,ROWS,"BAST")
                 + P_Result(MS,Cols,Rows,"%baseyear%","Longrun")      $ (NOT P_DATA(MS,COLS,ROWS,"BAST")))
              ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (longrun_supports.supports)."""
    return base / longrun


def P_Result_Longrun_scaled(value, fac):
    r"""P_Result(MS, ., years, "Longrun") with a factor: scaled to BAST.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 351-352):

           P_Result(MS,Cols,Rows,years,"Longrun") $ P_Result(MS,Cols,Rows,"fac","Longrun")
              =    P_Result(MS,Cols,Rows,years,"Longrun")*P_Result(MS,Cols,Rows,"fac","Longrun");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (longrun_supports.supports)."""
    return value * fac


def P_Result_INHA_pdata(macro, macro_bas, basm):
    r"""P_Result(MS, "INHA", "LEVL", years, "p_data") after BAST: the Aglink macro population's change from BAS times
    BASM, where all three are given.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 368-376):

           P_Result(MS,'INHA','LEVL',years,"p_data") $ (ORDT(years) GT ORDT("BAST"))
             = (   (p_aglinkMacro(MS,'INHA',years)/p_aglinkMacro(MS,'INHA',"BAS"))* P_DATA(MS,'INHA','LEVL',"BASM"))
                $ (p_aglinkMacro(MS,'INHA',years) $ p_aglinkMacro(MS,'INHA',"BAS") $ P_DATA(MS,'INHA','LEVL',"BASM"))
                +  p_globiomTightLink(MS,'INHA','LEVL',"%SelecScen%",years) * P_DATA(MS,'INHA','LEVL',"BASM")
                $ (  p_globiomTightLink(MS,'INHA','LEVL',"%SelecScen%",years) $ P_DATA(MS,'INHA','LEVL',"BASM")
                   $ (not p_aglinkMacro(MS,'INHA',years)))
                +  P_Result(MS,'INHA','LEVL',years,"Longrun")
                $ ( (NOT (p_globiomTightLink(MS,'INHA','LEVL',"%SelecScen%",years) $ P_DATA(MS,'INHA','LEVL',"BASM")))
                  $ (NOT (p_aglinkMacro(MS,'INHA',years) $ p_aglinkMacro(MS,'INHA',"BAS") $ P_DATA(MS,'INHA','LEVL',"BASM")))) ;

    Departures from CAPRI: the terms of p_globiomTightLink and of the Longrun population (l. 371-376) are not ported: the first is zero for
    the ex-ante years (captrd.gms l. 317), the second empty in the reference run; the condition and the loops in the
    caller (macro.inha_pdata)."""
    return macro / macro_bas * basm


def P_Result_INHA_pdata_WorldPop(basm, world_pop, world_pop_bas):
    r"""P_Result(MS, "INHA", "LEVL", exAnte, "p_data") without one: BASM times the UN population's change from the base
    year.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 386-389):

           P_Result(MS,'INHA','LEVL',exAnte,"p_data") $ ( (NOT P_Result(MS,'INHA','LEVL',exAnte,"p_data"))
                                                         $ SUM(BASY,WorldPop(BASY,MS)))
              = P_Result(MS,'INHA','LEVL',exAnte,"BASM")
              * WorldPop(exAnte,MS) / SUM(BASY,WorldPop(BASY,MS));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (macro.inha_pdata)."""
    return basm * world_pop / world_pop_bas


def p_ExpertSupprt_hcom_suga(support, inha, basm, inha_basm):
    r"""p_ExpertSupprt(ms, "hcom", "suga", exanteT, "absolute"): the support per head, between 0.8 and 1.2 times the
    base's per head, times the population.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 427-431):

           p_ExpertSupprt(ms,"hcom","suga",exanteT,"absolute") $ p_result(MS,"hcom","suga",exAnteT,"support")
             = max(.8,min(1.2, p_result(MS,"hcom","suga",exAnteT,"support")/ P_Result(MS,'INHA','LEVL',exAnteT,"p_data")
                             /(p_result(MS,"hcom","suga",exAnteT,"BASM")/ P_Result(MS,'INHA','LEVL',exAnteT,"BASM"))))
             * (p_result(MS,"hcom","suga",exAnteT,"BASM")/ P_Result(MS,'INHA','LEVL',exAnteT,"BASM"))
             *  P_Result(MS,'INHA','LEVL',exAnteT,"p_data") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (longrun_supports.supports)."""
    return max(0.8, min(1.2, support / inha / (basm / inha_basm))) * (basm / inha_basm) * inha


def P_Result_Expert_PercentChange(percent, basm):
    r"""P_Result(MS, ., exAnte, "Expert") from %phaseInYr% where Longrun has 2050: BASM changed by the national
    PercentChange.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 446-451):

           P_Result(MS,Cols,Rows,exAnte,"Expert")
             $ (  p_ExpertSupprt(MS,Cols,Rows,exAnte,"PercentChange")
                $ P_Result(MS,Cols,Rows,"2050","Longrun")
                $ (OrdT("lst_exAnte") GT  OrdT("%lst_dgagri%"))
                $ (OrdT(ExAnte) GE  OrdT("%phaseInYr%")))
             =  (1+p_ExpertSupprt(MS,COLS,ROWS,exAnte,"PercentChange")/100) * P_DATA(MS,COLS,ROWS,"BASM");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (longrun_supports.supports)."""
    return (1 + percent / 100) * basm


def P_Result_Expert_lst_dgagri(value):
    r"""P_Result(MS, ., exAnte, "Expert") after %lst_dgagri% without one: %lst_dgagri%'s.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 454-458):

           P_Result(MS,Cols,Rows,exAnte,"Expert")
             $ (  P_Result(MS,Cols,Rows,"%lst_dgagri%","Expert")
                $ (NOT P_Result(MS,Cols,Rows,exAnte,"Expert"))
                $ (OrdT(ExAnte) GT  OrdT("%lst_dgagri%")))
             =  P_Result(MS,Cols,Rows,"%lst_dgagri%","Expert");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (longrun_supports.supports)."""
    return value


def P_Result_Longrun1(longrun, expert, support, year, phase_in, ir):
    r"""P_Result(MS, ., ExAnte, "Longrun1") after %phaseInYr%: Longrun weighted from 0 at %phaseInYr% to p_longWgt (0.9,
    Ireland's 0.2 less) in 2050 with the exponent p_longExp (0.7), the Expert (else the Support) the rest.

    ir: the member state is IR000000.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 466-494):

           P_Result(MS,Cols,Rows,ExAnte,"Longrun1") $ (    (ORDT(ExAnte) GT ORDT("%phaseInYr%"))
                                                       and P_Result(MS,Cols,ROWS,exAnte,"Longrun")
        *          In general GLOBIOM has ignored the Irish "Food Harvest 2020" which gives big trouble for dairy =>
        $ifi %SelecScen%==primes_bas_apr13+BioenScen_100+WRLD_NTRD_YDFR_YCHG_LUC5by and (NOT (SAMEAS(rows,"COMI") $ SAMEAS(ms,"IR000000")))
        $ifi "%SelecScen%"=="primes_ref_2015+REFERENCE+REFERENCE"                   and (NOT (mlkPro(rows) $ SAMEAS(ms,"IR000000")))
        $ifi "%SelecScen%"=="primes_ref_2016+REFERENCE+REFERENCE"                   and (NOT (MlkProAndComi(rows) $ SAMEAS(ms,"IR000000")))
        $ifi "%SelecScen%"=="globiom_eu_2018+REFERENCE+REFERENCE"                   and (NOT (MlkProAndComi(rows) $ SAMEAS(ms,"IR000000")))
        $ifi "%SelecScen%"=="globiom_eu_euclimit5+REFERENCE+REFERENCE"              and (NOT (MlkProAndComi(rows) $ SAMEAS(ms,"IR000000")))
        $ifi "%SelecScen%"=="globiom_eu_nov2020+REFERENCE+REFERENCE"                and (NOT (MlkProAndComi(rows) $ SAMEAS(ms,"IR000000")))
        $ifi "%SelecScen%"=="globiom_eu_bright_s0_2023+REFERENCE+REFERENCE"         and (NOT (MlkProAndComi(rows) $ SAMEAS(ms,"IR000000")))
        $ifi "%SelecScen%"=="GLOBIOM_EU_EUCLIMIT6_S2_50CV"                          and (NOT (MlkProAndComi(rows) $ SAMEAS(ms,"IR000000")))

        $ifi "%SelecScen%"=="globiom_eu_suprema+scenRCPref+baseline"                and (NOT (MlkProAndComi(rows) $ SAMEAS(ms,"IR000000")))
                                                      )
              =    P_Result(MS,Cols,Rows,ExAnte,"Longrun")
        *          Weight for Longrun increases from 0 to p_longWgt as 2050 is approached
                 *  ((min(ORDT("2050"),ORDT(ExAnte))-ORDT("%phaseInYr%"))/(ORDT("2050")-ORDT("%phaseInYr%")))**p_longExp
                 *  ( p_longWgt
        *          As GLOBIOM has ignored the Irish "Food Harvest 2020" reduce weight for globiom (for non-dairy)=>
                    - .2 $ sameas(MS,"IR000000"))
        *
                 + (   P_Result(MS,Cols,Rows,ExAnte,"Expert")
                     + P_Result(MS,Cols,Rows,ExAnte,"Support") $ (NOT P_Result(MS,Cols,Rows,ExAnte,"Expert")))
        *          Weight for extrapolated info decreases from 1 to (1-p_longWgt) as 2050 is approached
                 * [1 - ((min(ORDT("2050"),ORDT(ExAnte))-ORDT("%phaseInYr%"))/(ORDT("2050")-ORDT("%phaseInYr%")))**p_longExp
                      * ( p_longWgt
        *          As GLOBIOM has ignored the Irish "Food Harvest 2020" reduce weight for globiom (for non-dairy)=>
                        - .2 $ sameas(MS,"IR000000"))]
                 ;

    Departures from CAPRI: the port computes the weight once, CAPRI writes it twice; the domain condition (the milk positions of Ireland out)
    and the loops in the caller (longrun_supports.supports)."""
    wt = ((min(2050, year) - phase_in) / (2050 - phase_in)) ** 0.7 * (0.9 - 0.2 * ir)
    return longrun * wt + (expert or support) * (1 - wt)


def p_ExpertSupprt_PercentChange_Longrun1(longrun1, basm):
    r"""p_ExpertSupprt(MS, ., exante, "PercentChange") where an Expert and Longrun1 are given: Longrun1's change from
    BASM in percent.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 497-507):

           p_ExpertSupprt(MS,cols,rows,exante,"PercentChange")
        *                               P_result(Expert) given here indicates that the merged longrun1 should become expert
        *                               NOTE: If P_result(Expert) is not given here, we have two cases:
        *                                     1) DGAgri1     given => Longrun will be remerged with DGAgri1
        *                                     2) DGAgri1 not given => Merged Longrun1 from above will become Expert
        *                                        in define_EU_supports.gms

                                     $ (  P_Result(MS,Cols,Rows,ExAnte,"Expert")
                                        $ P_Result(MS,Cols,Rows,ExAnte,"Longrun1")
                                        $ P_DATA(MS,COLS,ROWS,"BASM"))
              = P_Result(MS,Cols,Rows,ExAnte,"Longrun1") / P_DATA(MS,COLS,ROWS,"BASM") *100.-100.;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (longrun_supports.supports)."""
    return longrun1 / basm * 100. - 100.


def p_ExpertSupprt_Absolute_Longrun1(longrun1):
    r"""p_ExpertSupprt(MS, S_ColsEst, S_RowsEst, exAnte, "Absolute") where nothing else is given (no Absolute,
    PercentChange or DG AGRI outlook; not the Western Balkans or Turkey): Longrun1.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 516-526):

           p_ExpertSupprt(MS,S_ColsEst,S_RowsEst,exAnte,"Absolute")
             $ (NOT (   p_ExpertSupprt(MS,S_ColsEst,S_RowsEst,exAnte,"Absolute")
                     or p_ExpertSupprt(MS,S_ColsEst,S_RowsEst,exAnte,"PercentChange")
                     or Sum(Lst_DGAgri,  P_Result(MS,S_ColsEst,S_RowsEst,Lst_DGAgri,"DGAgri1")
                                       + SUM(MAP_RR(CurEuropAgg,MS),P_Result(CurEuropAgg,S_ColsEst,S_RowsEst,Lst_DGAgri,"DGAgri1"))
                                       $ (NOT (P_Result(MS,S_ColsEst,S_RowsEst,Lst_DGAgri,"DGAgri1"))))
                     or (MAP_RR("WBA",MS) or SAMEAS(MS,"TUR"))
                     or (OrdT("lst_exAnte") LE  OrdT("%lst_dgagri%"))
        *            phasing in before 2020 would give higher wgt to the long run source:
                    or (OrdT(ExAnte) LE  ORDT("%phaseInYr%"))) )
                 =   P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"Longrun1") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (longrun_supports.supports)."""
    return longrun1


def p_ExpertSupprt_TrustLevl_Longrun1(yield_or_milk, levl, absolute, fore, olnd):
    r"""p_ExpertSupprt(MS, S_ColsEst, S_RowsEst, exAnte, "TrustLevl") of Longrun1 as Absolute: 1 for yields
    (PACT_TO_Y), milk and the levels below 0.1, else 5; FORE + 3, OLND + 1.

    yield_or_milk: PACT_TO_Y or mlkProAndComi; levl: the row is LEVL.

    CAPRI's GAMS (captrd/longrun_supports.gms l. 530-545):

           p_ExpertSupprt(MS,S_ColsEst,S_RowsEst,exAnte,"TrustLevl")
             $ ( (p_ExpertSupprt(MS,S_ColsEst,S_RowsEst,exAnte,"Absolute") EQ P_Result(MS,S_ColsEst,S_RowsEst,ExAnte,"Longrun1"))
        *       phasing in before 2020 would give higher wgt to the long run source:
               $ p_ExpertSupprt(MS,S_ColsEst,S_RowsEst,exAnte,"Absolute") $ (OrdT(ExAnte) GT  ORDT("%phaseInYr%")))
        *              Low trustlevl to steer these over related variables (PRCM.MILK,PRCM.COMI or GROF+LEVL for yields):
             = 1 $      (   PACT_TO_Y(S_ColsEst,S_RowsEst)
                         or mlkProAndComi(S_RowsEst)
        *                tiny levls should not cause huge penalties
                         or (SAMEAS(S_RowsEst,"LEVL") and (p_ExpertSupprt(MS,S_ColsEst,S_RowsEst,exAnte,"Absolute") LT 0.1)))
             + 5 $ (NOT (   PACT_TO_Y(S_ColsEst,S_RowsEst)
                         or mlkProAndComi(S_RowsEst)
                         or (SAMEAS(S_RowsEst,"LEVL") and (p_ExpertSupprt(MS,S_ColsEst,S_RowsEst,exAnte,"Absolute") LT 0.1))))
        *       high weight for land use info from GLOBIOM:
             + 3 $ SAMEAS(S_Colsest,"FORE")
             + 1 $ SAMEAS(S_ColsEst,"OLND")
                 ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (longrun_supports.supports)."""
    low = yield_or_milk or (levl and absolute < 0.1)
    return (1.0 if low else 5.0) + 3.0 * fore + 1.0 * olnd
