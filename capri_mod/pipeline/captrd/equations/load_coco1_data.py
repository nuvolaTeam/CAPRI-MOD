r"""CAPTRD's statements of captrd/load_coco1_data.gms (CAPRI star 3.0, %NewBiofuelModule% ON): COCO's data prepared
(dataMS) and brought into p_data for the years after CAPREG's series, the biofuel positions, as named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). capri_mod/pipeline/captrd/coco.py holds the loops, the conditions and the
order, and calls them: prepare_country (dataMS, l. 46-333: pandas Series over the years of one country) and
apply_country (p_data, l. 253-551: pandas Series over (region, year)). The functions keep coco.py's pandas and numpy
operations, so the data are unchanged. Not ported (coco.py's docstring): p_result_MSnoEU (l. 429-486) and the market
aggregates' p_data (l. 553-554).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def dataMS_removed():
    r"""dataMS(MS, 'COCO1', ., ., years): removed (UVAD; the years without COCO UAAR; MAPR where a raw product has no
    PRCM; recent GROF and levels where the NUTS 2 regions have none; the flags of positions other than GROF where
    GROF is given; HCOM of the biofuels, rebooked to BIOF).

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 46-46):

           dataMS(MS,'coco1',delCocoCols,ROWS,Years) = 0.;

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 68-68):

           dataMS(MS,cocoitem,Cols,ROWS,years) $ (NOT usable_years(MS,Years)) = 0.;

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 72-73):

           dataMS(MS,"coco1","MAPR",ROWS,years) $ ( sum(PRCD(ROWS,ROWS1) $ (NOT dataMS(MS,"coco1","PRCM",ROWS1,years)) ,1)
                                                  $ (NOT SAMEAS(ROWS,"MILK"))) = 0;

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 222-227):

           dataMS(MS,"COCO1","GROF",O,years) $  (  (NOT SUM((map_rr(MS,NT2),BasYrsM), p_data(NT2,"GROF",O,BasYrsM)))
        *                                          single region MS are no problem:
                                                 $ (SUM(map_rr(MS,NT2),1) GT 1)
                                                 $ usable_years(MS,years)
                                                 $ (not exPost(years)))
              = 0;

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 229-233):

           dataMS(MS,"COCO1",MPACT,"LEVL",years) $ (  (NOT SUM((map_rr(MS,NT2),BasYrsM), p_data(NT2,MPACT,"LEVL",BasYrsM)))
                                                    $ (SUM(map_rr(MS,NT2),1) GT 1)
                                                    $ usable_years(MS,years)
                                                    $ (not exPost(years)))
              = 0;

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 240-247):

           dataMS(MS,'COCO1',MrkBaleE,ROWS_LOAD,exAnteD) $ (   (NOT SUM(MrkBaleE1 $ (  (NOT SAMEAS(MrkBaleE1,'GROF'))
                                                                                     $ (dataMS(MS,'COCO1',MrkBaleE,ROWS_LOAD,exAnteD) GT 1.E-12)),1))
                                                            $  SUM((years1),dataMS(MS,'COCO1',MrkBaleE,ROWS_LOAD,years1))
                                                            $  (dataMS(MS,'COCO1','GROF',ROWS_LOAD,exAnteD) GT 1.E-12)
                                                            $  (NOT colsNoCoco(MrkBaleE))
                                                            $  (NOT sameas(MrkBaleE,'GROF'))
                                                            $  usable_years(MS,exAnteD))
            = 0;

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 333-333):

           dataMS(MS,'COCO1','HCOM',biofuels,expostT_basm) = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.prepare_country)."""
    return 0.0


def dataMS_HERD(levl, days):
    r"""dataMS(MS, "coco1", AACT, "HERD", years) without one: the level times the days over 365.

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 76-79):

           dataMS(MS,"coco1",AACT,"HERD",years) $ ( (NOT dataMS(MS,"coco1",AACT,"HERD",years))
                                                  $      dataMS(MS,"coco1",AACT,"DAYS",years)
                                                  $      dataMS(MS,"coco1",AACT,"LEVL",years))
              = dataMS(MS,"coco1",AACT,"LEVL",years)*dataMS(MS,"coco1",AACT,"DAYS",years)/365;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.prepare_country)."""
    return levl * days / 365.0


def dataMS_LOSF(grof, losf_basm, grof_basm):
    r"""dataMS(MS, 'COCO1', 'LOSF', losfFromCoco2, exPostT): GROF at p_data's loss share of BASM.

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 87-90):

            dataMS(MS,'COCO1','LOSF',losfFromCoco2,exPostT) $ (  dataMS(MS,'COCO1','GROF',losfFromCoco2,exPostT)
                                                              $ P_data(MS,'GROF',losfFromCoco2,'BASM'))
                  = dataMS(MS,'COCO1','GROF',losfFromCoco2,exPostT)
                  * P_data(MS,'LOSF',losfFromCoco2,'BASM')/ P_data(MS,'GROF',losfFromCoco2,'BASM');

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.prepare_country)."""
    return grof * losf_basm / grof_basm


def dataMS_FEDM(grof, impt, uses, zero):
    r"""dataMS(MS, 'COCO1', 'FEDM', losfFromCoco2, exPostT): production plus imports less the other uses, not below
    zero.

    uses: SEDM, SEDF, INDM, PRCM, BIOF, HCOM, LOSM, LOSF, EXPT, STCM, in order (pandas Series).

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 95-107):

            dataMS(MS,'COCO1','FEDM',losfFromCoco2,exPostT) $ dataMS(MS,'COCO1','GROF',losfFromCoco2,exPostT)
                  = max(0, dataMS(MS,'COCO1','GROF',losfFromCoco2,exPostT)
                         + dataMS(MS,'COCO1','IMPT',losfFromCoco2,exPostT)
                         - dataMS(MS,'COCO1','SEDM',losfFromCoco2,exPostT)
                         - dataMS(MS,'COCO1','SEDF',losfFromCoco2,exPostT)
                         - dataMS(MS,'COCO1','INDM',losfFromCoco2,exPostT)
                         - dataMS(MS,'COCO1','PRCM',losfFromCoco2,exPostT)
                         - dataMS(MS,'COCO1','BIOF',losfFromCoco2,exPostT)
                         - dataMS(MS,'COCO1','HCOM',losfFromCoco2,exPostT)
                         - dataMS(MS,'COCO1','LOSM',losfFromCoco2,exPostT)
                         - dataMS(MS,'COCO1','LOSF',losfFromCoco2,exPostT)
                         - dataMS(MS,'COCO1','EXPT',losfFromCoco2,exPostT)
                         - dataMS(MS,'COCO1','STCM',losfFromCoco2,exPostT));

    Departures from CAPRI: the port subtracts the uses' sum, CAPRI each use in turn (the last digit may differ); the domain condition and the
    loops in the caller (coco.prepare_country)."""
    return (grof + impt - sum(uses, zero)).clip(lower=0.0)


def dataMS_NETF(grof, sedf, losf):
    r"""dataMS(MS, 'COCO1', 'NETF', losfFromCoco2, exPostT): GROF less seed and losses, not below zero.

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 108-111):

            dataMS(MS,'COCO1','NETF',losfFromCoco2,exPostT) $ dataMS(MS,'COCO1','GROF',losfFromCoco2,exPostT)
                  = Max(0, dataMS(MS,'COCO1','GROF',losfFromCoco2,exPostT)
                         - dataMS(MS,'COCO1','SEDF',losfFromCoco2,exPostT)
                         - dataMS(MS,'COCO1','LOSF',losfFromCoco2,exPostT));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.prepare_country)."""
    return (grof - sedf - losf).clip(lower=0.0)


def dataMS_DOMM(uses, zero):
    r"""dataMS(MS, 'COCO1', 'DOMM', losfFromCoco2, exPostT): the domestic uses (DOMM's set) summed, not below zero.

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 112-113):

            dataMS(MS,'COCO1','DOMM',losfFromCoco2,exPostT) $  dataMS(MS,'COCO1','GROF',losfFromCoco2,exPostT)
                  = max(0,sum(DOMM, dataMS(MS,'COCO1',DOMM,losfFromCoco2,exPostT))) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.prepare_country)."""
    return sum(uses, zero).clip(lower=0.0)


def dataMS_MAPR(netf):
    r"""dataMS(MS, 'COCO1', 'MAPR', ROWS_LOAD, exPostT) without one, where p_data has MAPR around the base year: NETF.

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 117-120):

           dataMS(MS,'COCO1','MAPR',ROWS_LOAD,exPostT) $ (  SUM(BASYRS5,p_data(MS,"MAPR",ROWS_LOAD,BASYRS5))
                                                          $ (NOT dataMS(MS,'COCO1','MAPR',ROWS_LOAD,exPostT) )
                                                          $ dataMS(MS,'COCO1','NETF',ROWS_LOAD,exPostT))
            = dataMS(MS,'COCO1','NETF',ROWS_LOAD,exPostT);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.prepare_country)."""
    return netf


def dataMS_flag():
    r"""dataMS(MS, 'COCO1', MrkBaleE / Cols_Load, ROWS_LOAD / 'LEVL', exAnteD) without one, where COCO has the series:
    a near-zero flag.

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 124-130):

           dataMS(MS,'COCO1',MrkBaleE,ROWS_LOAD,exAnteD) $ (   SUM((years1),dataMS(MS,'COCO1',MrkBaleE,ROWS_LOAD,years1))
        *                                              these may be empty in exAnteD as they are EAA residuals:
                                                            $ (NOT (SAMEAS('OANI',ROWS_LOAD) or SAMEAS('OCRO',ROWS_LOAD)) )
                                                            $ (NOT colsNoCoco(MrkBaleE))
                                                            $ usable_years(MS,exAnteD)
                                                            $ (NOT dataMS(MS,'COCO1',MrkBaleE,ROWS_LOAD,exAnteD) ))
            = 1E-13;

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 134-139):

           dataMS(MS,'COCO1',Cols_Load,'LEVL',exAnteD) $ (  SUM((years1),dataMS(MS,'COCO1',Cols_Load,'LEVL',years1))
        *                                              these may be empty in exAnteD as they are EAA residuals:
                                                          $ usable_years(MS,exAnteD)
                                                          $ (NOT (SAMEAS('OANI',Cols_LOAD) or SAMEAS('OCRO',Cols_LOAD)) )
                                                          $ (NOT dataMS(MS,'COCO1',Cols_Load,'LEVL',exAnteD) ))
            = 1E-13;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.prepare_country)."""
    return 1E-13


def BASM_mean(values):
    r"""dataMS(MS, 'COCO1', ., ., "BASM") and the non-EU countries' biofuel p_data(MSnoEU28, ., ., "BASM"): the mean of
    the nonzero BASYRSM values.

    values: the nonzero values (pandas Series).

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 143-146):

           dataMS(MS,'COCO1',COLS_LOAD,ROWS_LOAD,"BASM")
              $  sum(BasYrsM $ dataMS(MS,'COCO1',COLS_LOAD,ROWS_LOAD,BasYrsM), 1.)
            = sum(BasYrsM, dataMS(MS,'COCO1',COLS_LOAD,ROWS_LOAD,BasYrsM))
             /sum(BasYrsM $ dataMS(MS,'COCO1',COLS_LOAD,ROWS_LOAD,BasYrsM), 1.) ;

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 208-211):

           dataMS(MS,'COCO1',MPACT,ROWS_LOAD,"BASM")
              $  (sum(BasYrsM $ dataMS(MS,'COCO1',MPACT,ROWS_LOAD,BasYrsM), 1.) $ (DMPACT(MPACT) or P_T_ActAgg(MPACT,"SETF")))
            = sum(BasYrsM, dataMS(MS,'COCO1',MPACT,ROWS_LOAD,BasYrsM))
             /sum(BasYrsM $ dataMS(MS,'COCO1',MPACT,ROWS_LOAD,BasYrsM), 1.) ;

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 213-216):

           dataMS(MS,'COCO1',"UVAG",ROWS_LOAD,"BASM")
              $  sum(BasYrsM $ dataMS(MS,'COCO1',"UVAG",ROWS_LOAD,BasYrsM), 1.)
            = sum(BasYrsM, dataMS(MS,'COCO1',"UVAG",ROWS_LOAD,BasYrsM))
             /sum(BasYrsM $ dataMS(MS,'COCO1',"UVAG",ROWS_LOAD,BasYrsM), 1.) ;

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 380-383):

          p_data(MSnoEU28,BioColsCoco,rows,"BASM") $ (  (abs(p_data(MSnoEU28,BioColsCoco,rows,"BASM")) le 1.e-13)
                                                      $ sum(BASYRSM $(p_data(MSnoEU28,BioColsCoco,rows,BASYRSM)),1))
            = sum(BASYRSM,p_data(MSnoEU28,BioColsCoco,rows,BASYRSM))
                 /sum(BASYRSM $(p_data(MSnoEU28,BioColsCoco,rows,BASYRSM)),1) ;

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 385-388):

          p_data(MSnoEU28,cols,bioROWSCoco,"BASM") $ ( (abs(p_data(MSnoEU28,cols,bioROWSCoco,"BASM")) le 1.e-13)
                                                     $ sum(BASYRSM $(p_data(MSnoEU28,cols,bioROWSCoco,BASYRSM)),1))
            = sum(BASYRSM,p_data(MSnoEU28,cols,bioROWSCoco,BASYRSM))
                 /sum(BASYRSM $(p_data(MSnoEU28,cols,bioROWSCoco,BASYRSM)),1) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.prepare_country, coco.apply_country)."""
    return float(values.sum()) / len(values)


def dataMS_Splitacts(dsum, pbasm, dbasm, zero):
    r"""dataMS(MS, 'COCO1', Splitacts, ROWS_LOAD, years) without one: the aggregate's (DACT) times p_data's share of
    its BASM where p_data's BASM lies in (0, 2 x the aggregate's), else the difference added (at least 1E-12 where
    the two BASM sum above 1E-12).

    dsum: the aggregate's series (pandas Series); dbasm: its BASM.

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 156-174):

           dataMS(MS,'COCO1',Splitacts,ROWS_LOAD,years) $ (  SUM(DACT_TO_PACT(DACT,Splitacts),dataMS(MS,'COCO1',DACT,ROWS_LOAD,"BASM"))
                                                           $ (NOT dataMS(MS,'COCO1',Splitacts,ROWS_LOAD,years))
                                                           $ usable_years(MS,years)
                                                           $ p_data(MS,Splitacts,ROWS_LOAD,"BASM"))
            = SUM(DACT_TO_PACT(DACT,Splitacts),dataMS(MS,'COCO1',DACT,ROWS_LOAD,years))
            *     ( p_data(MS,Splitacts,ROWS_LOAD,"BASM")
                   / SUM(DACT_TO_PACT(DACT,Splitacts),dataMS(MS,'COCO1',DACT,ROWS_LOAD,"BASM")))
                   $ (    (  (p_data(MS,Splitacts,ROWS_LOAD,"BASM") LT SUM(DACT_TO_PACT(DACT,Splitacts),2*dataMS(MS,'COCO1',DACT,ROWS_LOAD,"BASM")))
                           $ (p_data(MS,Splitacts,ROWS_LOAD,"BASM") GT 0)))

        *       if corection factor would be dangerous (too large or zero) take correcting difference
        *       ... but variables initialised positive should stay positive:
             +  MAX(1E-12, SUM(DACT_TO_PACT(DACT,Splitacts),dataMS(MS,'COCO1',DACT,ROWS_LOAD,years))
                         + p_data(MS,Splitacts,ROWS_LOAD,"BASM")
                         - SUM(DACT_TO_PACT(DACT,Splitacts),dataMS(MS,'COCO1',DACT,ROWS_LOAD,"BASM")))
                          $ (  ( NOT (  (p_data(MS,Splitacts,ROWS_LOAD,"BASM") LT SUM(DACT_TO_PACT(DACT,Splitacts),2*dataMS(MS,'COCO1',DACT,ROWS_LOAD,"BASM")))
                                      $ (p_data(MS,Splitacts,ROWS_LOAD,"BASM") GT 0)))
                             $ ((  SUM(DACT_TO_PACT(DACT,Splitacts),dataMS(MS,'COCO1',DACT,ROWS_LOAD,"BASM"))
                                 + p_data(MS,Splitacts,ROWS_LOAD,"BASM")) GT 1E-12));

    Departures from CAPRI: the port compares with 2 x the sum of the aggregate's BASM, CAPRI with the sum of 2 x each; the domain condition
    and the loops in the caller (coco.prepare_country)."""
    if (pbasm < 2 * dbasm) and (pbasm > 0):
        return dsum * (pbasm / dbasm)
    return (dsum + pbasm - dbasm).clip(lower=1e-12) if (dbasm + pbasm) > 1e-12 else zero


def dataMS_SETF(fall, fall_basm, basm):
    r"""dataMS(MS, 'COCO1', SETF components, ROWS_LOAD, years): FALL's change from its BASM times p_data's BASM.

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 179-183):

           dataMS(MS,'COCO1',COLS,ROWS_LOAD,years) $ (  P_T_ActAgg(COLS,"SETF") $ p_data(MS,COLS,ROWS_LOAD,"BASM")
                                                      $ usable_years(MS,years)
                                                      $ dataMS(MS,'COCO1',"FALL",ROWS_LOAD,"BASM"))
            = dataMS(MS,'COCO1',"FALL",ROWS_LOAD,years)/dataMS(MS,'COCO1',"FALL",ROWS_LOAD,"BASM")
            * p_data(MS,COLS,ROWS_LOAD,"BASM") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.prepare_country)."""
    return fall / fall_basm * basm


def dataMS_VSET(vset, basm):
    r"""dataMS(MS, 'COCO1', 'VSET', 'LEVL', years) in ExAnteD: at most p_data's BASM.

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 190-193):

           dataMS(MS,'COCO1','VSET','LEVL',years) $ (  p_data(MS,'VSET','LEVL','BASM')
                                                     $ usable_years(MS,years) and ExAnteD(YEARS)
                                                     $ dataMS(MS,'COCO1','VSET','LEVL',years) )
            = MIN(p_data(MS,'VSET','LEVL','BASM'), dataMS(MS,'COCO1','VSET','LEVL',years) );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.prepare_country)."""
    return vset.clip(upper=basm)


def dataMS_UVAG(uvap, uvap_basm, uvag_basm):
    r"""dataMS(MS, 'COCO1', 'UVAG', ROWS_LOAD, years): UVAP's change from its BASM times p_data's BASM.

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 198-203):

           dataMS(MS,'COCO1','UVAG',ROWS_LOAD,years) $ ( SUM(BASYRS5,p_data(MS,"UVAG",ROWS_LOAD,BASYRS5))
                                                        $ usable_years(MS,years)
                                                        $   p_data(MS,"UVAG",ROWS_LOAD,"BASM")
                                                        $ dataMS(MS,'COCO1',"UVAP",ROWS_LOAD,"BASM"))
            = dataMS(MS,'COCO1',"UVAP",ROWS_LOAD,years)/dataMS(MS,'COCO1',"UVAP",ROWS_LOAD,"BASM")
            * p_data(MS,"UVAG",ROWS_LOAD,"BASM") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.prepare_country)."""
    return uvap / uvap_basm * uvag_basm


def dataMS_BIOF(biof, hcom):
    r"""dataMS(MS, 'COCO1', 'BIOF', biofuels, expostT_basm): plus HCOM (the biofuels' consumption booked to BIOF).

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 330-332):

           dataMS(MS,'COCO1','BIOF',biofuels,expostT_basm) $ dataMS(MS,'COCO1','HCOM',biofuels,expostT_basm)
              = dataMS(MS,'COCO1','BIOF',biofuels,expostT_basm)
              + dataMS(MS,'COCO1','HCOM',biofuels,expostT_basm);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.prepare_country)."""
    return biof + hcom


def p_data_from_COCO(coco, pbasm, cbasm):
    r"""p_data(MS, COLS_LOAD, ROWS_LOAD, years) of the usable years after the ex-post ones: COCO's times p_data's BASM
    over COCO's where that factor lies in (0, 2), else COCO's plus the difference of the BASM (as it is where the sum
    is negative, 0 below 1E-13, at least 1E-13).

    coco: COCO's series (pandas Series over (region, year)).

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 253-285):

           p_data(MS,COLS_LOAD,ROWS_LOAD,years) $ (  (not exPost(years))
                                                   $ usable_years(MS,years)
                                                   $ dataMS(MS,'COCO1',COLS_LOAD,ROWS_LOAD,years)
                                                   $ (dataMS(MS,'COCO1',COLS_LOAD,ROWS_LOAD,"BASM") or (p_data(MS,COLS_LOAD,ROWS_LOAD,"BASM") EQ 0)))
            = dataMS(MS,'COCO1',COLS_LOAD,ROWS_LOAD,years)
            * (p_data(MS,COLS_LOAD,ROWS_LOAD,"BASM")/dataMS(MS,'COCO1',COLS_LOAD,ROWS_LOAD,"BASM"))
                          $      (    (  (p_data(MS,COLS_LOAD,ROWS_LOAD,"BASM") GT 0)
        *                                                                            Factor 2 appeared to be the largest acceptable factor:
                                       $ (p_data(MS,COLS_LOAD,ROWS_LOAD,"BASM") LT (2*dataMS(MS,'COCO1',COLS_LOAD,ROWS_LOAD,"BASM")))))


        *       Correcting difference with conditionals if correction factor would be dangerous (too large or zero):

        *             case 1: for NTRD that does not require further measures:
             +(       ( dataMS(MS,'COCO1',COLS_LOAD,ROWS_LOAD,years)
                      + p_data(MS,COLS_LOAD,ROWS_LOAD,"BASM")
                      - dataMS(MS,'COCO1',COLS_LOAD,ROWS_LOAD,"BASM"))
                      $ ( (dataMS(MS,'COCO1',COLS_LOAD,ROWS_LOAD,years)+ p_data(MS,COLS_LOAD,ROWS_LOAD,"BASM")) LT 0)

        *             case 2: variables zero (<1E-13) according to coco and res_04 should stay zero:
                +     0
                      $ (  ((dataMS(MS,'COCO1',COLS_LOAD,ROWS_LOAD,years)+ p_data(MS,COLS_LOAD,ROWS_LOAD,"BASM")) GE 0)
                         $ ((dataMS(MS,'COCO1',COLS_LOAD,ROWS_LOAD,years)+ p_data(MS,COLS_LOAD,ROWS_LOAD,"BASM")) LT 1E-13))

        *             case 3: variables initialised positive should stay positive:
                +     MAX(1E-13, ( dataMS(MS,'COCO1',COLS_LOAD,ROWS_LOAD,years)
                                 + p_data(MS,COLS_LOAD,ROWS_LOAD,"BASM")
                                 - dataMS(MS,'COCO1',COLS_LOAD,ROWS_LOAD,"BASM")))
                      $ ( (dataMS(MS,'COCO1',COLS_LOAD,ROWS_LOAD,years)+ p_data(MS,COLS_LOAD,ROWS_LOAD,"BASM")) GE 1E-13)

               )           $     (NOT (  (p_data(MS,COLS_LOAD,ROWS_LOAD,"BASM") GT 0)
                                       $ (p_data(MS,COLS_LOAD,ROWS_LOAD,"BASM") LT (2*dataMS(MS,'COCO1',COLS_LOAD,ROWS_LOAD,"BASM")))))
                                      ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.apply_country)."""
    if pbasm > 0 and pbasm < 2 * cbasm:
        return coco * (pbasm / cbasm)
    s_ = coco + pbasm
    diff = coco + pbasm - cbasm
    return pd.Series(np.where(s_ < 0, diff, np.where(s_ < 1e-13, 0.0, np.maximum(1e-13, diff))), index=coco.index)


def p_data_GROF_flag(any_level):
    r"""p_data(MS, "GROF", O, years) above 1E-13 without a producing activity: 1E-13 where some activity has a level,
    else removed.

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 290-295):

           p_data(MS,"GROF",O,years) $  (  (NOT SUM(PACT_TO_O(MPACT,O) $ (p_data(MS,MPACT,"LEVL",years) GT 2E-13),1))
                                         $ usable_years(MS,years)
                                         $ (p_data(MS,"GROF",O,years) GT 1E-13)
                                         $ (not exPost(years)))
        *             If LEVL is exactly zero and hence may be estimated, so should be GROF
              = 1E-13 $ SUM(PACT_TO_O(MPACT,O) $ p_data(MS,MPACT,"LEVL",years),1);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.apply_country)."""
    return pd.Series(np.where(any_level > 0, 1e-13, 0.0), index=any_level.index)


def p_data_EAAG_flag():
    r"""p_data(MS, "EAAG", O, years) where GROF is that flag: the flag.

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 299-302):

           p_data(MS,"EAAG",O,years) $  (  (not exPost(years))
                                         $ usable_years(MS,years)
                                         $ (p_data(MS,"GROF",O,years) EQ 1E-13))
              = 1E-13 ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.apply_country)."""
    return 1E-13


def p_data_LEVL_flag(any_grof):
    r"""p_data(MS, MPACT, "LEVL", years) above 1E-13 without an output (set-aside excepted): 1E-13 where some output has
    GROF, else removed.

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 304-310):

           p_data(MS,MPACT,"LEVL",years) $  (  (NOT SUM(PACT_TO_O(MPACT,O) $ (p_data(MS,"GROF",O,years) GT 2E-13),1))
                                             $ usable_years(MS,years)
                                             $ (p_data(MS,MPACT,"LEVL",years) GT 1E-13)
                                             $ (NOT P_T_ActAgg(MPACT,"SETF"))
                                             $ (not exPost(years)))
        *             If GROF is exactly zero and hence may be estimated, so should be LEVL
              = 1E-13 $ SUM(PACT_TO_O(MPACT,O) $ p_data(MS,"GROF",O,years),1);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.apply_country)."""
    return pd.Series(np.where(any_grof > 0, 1e-13, 0.0), index=any_grof.index)


def p_data_bio(coco, flagged):
    r"""p_data(MS, BioColsCoco / ., ROWS_LOAD / bioROWSCoco, expostT_basm): COCO's biofuel positions, 1E-13 where COCO
    has none but some country has the position after 2002 (and COCO UAAR).

    flagged: where the flag is set (a boolean array on coco's index).

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 335-342):

           p_data(MS,BioColsCoco,ROWS_LOAD,expostT_basm) =dataMS(MS,'COCO1',BioColsCoco,ROWS_LOAD,expostT_basm)
        *                                                near zero assingment prevents that non-zero data are invented later
                                                         + 1E-13 $ (  (not dataMS(MS,'COCO1',BioColsCoco,ROWS_LOAD,expostT_basm))
                                                                    $  sum((bioExpostYears,MS1) $ dataMS(MS1,'COCO1',BioColsCoco,ROWS_LOAD,bioExpostYears),1)
                                                                    $  dataMS(MS,"COCO1","UAAR","LEVL",expostT_basm)
        *                                                           but near zero PRCB or PRCBY give weird projections in bio_trend.gms:
                                                                    $  (not (sameas(bioColsCoco,"PRCB") or sameas(bioColsCoco,"PRCBY")))
                                                                    $  bioExpostYears(expostT_basm));

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 343-349):

           p_data(MS,COLS_LOAD,bioROWSCoco,expostT_basm) $ (not sameas(cols_load,"uvad"))
                                                         =dataMS(MS,'COCO1',COLS_LOAD,bioROWSCoco,expostT_basm)
        *                                                near zero assingment prevents that non-zero data are invented later
                                                         + 1E-13 $ (  (not dataMS(MS,'COCO1',COLS_LOAD,bioROWSCoco,expostT_basm))
                                                                    $  sum((bioExpostYears,MS1) $ dataMS(MS1,'COCO1',COLS_LOAD,bioROWSCoco,bioExpostYears),1)
                                                                    $  dataMS(MS,"COCO1","UAAR","LEVL",expostT_basm)
                                                                    $  bioExpostYears(expostT_basm));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.apply_country)."""
    return coco + pd.Series(np.where(flagged, 1e-13, 0.0), index=coco.index)


def p_data_copy(value):
    r"""p_data(., ., ., expostT_basm / Years): taken over (the fuels' UVAG from COCO's UVAP; the non-EU countries'
    biofuel positions from fao_agg's p_biofuelData; their fossil fuels' UVAD from CPRI; the biofuels' UVAG and UVAP
    from PPRI and PMRK; PRCB, PRCBY; GLYC's prices; HCOM of the fuels from DOMM).

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 352-352):

           p_data(MS,"UVAG",fuels,expostT_basm) =dataMS(MS,'COCO1',"UVAP",fuels,expostT_basm);

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 370-371):

          p_data(MSnoEU28,BioColsCoco,rows,expostT_basm) $ (abs(p_data(MSnoEU28,BioColsCoco,rows,expostT_basm)) le 1e-13)
            = p_biofuelData(MSnoEU28,BioColsCoco,rows,expostT_basm);

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 372-374):

          p_data(MSnoEU28,cols,bioROWSCoco,expostT_basm) $ (abs(p_data(MSnoEU28,cols,bioROWSCoco,expostT_basm)) le 1e-13)
            = p_biofuelData(MSnoEU28,cols,bioROWSCoco,expostT_basm)
            ;

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 375-376):

          p_data(MSnoEU28,"UVAD",fosfuels,expostT_basm)  $ (abs(p_data(MSnoEU28,"UVAD",fosfuels,expostT_basm)) le 1e-13)
            = p_data(MSnoEU28,"CPRI",fosfuels,expostT_basm);

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 392-394):

          p_data(MS,"UVAG",biofuels,expostT_basm) $ ((abs(p_data(MS,"UVAG",biofuels,expostT_basm)) le 1.e-13)
                                                    $ p_biofuelData(MS,"PPRI",biofuels,expostT_basm))
            = p_biofuelData(MS,"PPRI",biofuels,expostT_basm);

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 396-398):

          p_data(MS,"UVAP",biofuels,expostT_basm) $ ( (abs(p_data(MS,"UVAP",biofuels,expostT_basm)) le 1.e-13)
                                                    $ p_biofuelData(MS,"PMRK",biofuels,expostT_basm))
            = p_biofuelData(MS,"PMRK",biofuels,expostT_basm);

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 408-410):

          p_data(MS,"PRCB",biostock,expostT_basm) $ ( (p_data(MS,"PRCB",biostock,expostT_basm) le 1.e-13)
                                                    $ p_biofuelData(MS,"PRCB",biostock,expostT_basm))
            = p_biofuelData(MS,"PRCB",biostock,expostT_basm);

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 412-414):

          p_data(MS,"PRCBY",biostock,expostT_basm) $ ( (p_data(MS,"PRCBY",biostock,expostT_basm)  le 1.e-13)
                                                     $ p_biofuelData(MS,"PRCBY",biostock,expostT_basm))
            = p_biofuelData(MS,"PRCBY",biostock,expostT_basm);

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 418-419):

          p_data(MS,"UVAG","GLYC",expostT_basm) $ (p_data(MS,"UVAG","GLYC",expostT_basm) le 1.e-13)
            = p_biofuelData(MS,"UVAG","GLYC",expostT_basm);

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 420-421):

          p_data(MS,"UVAP","GLYC",expostT_basm) $ (p_data(MS,"UVAP","GLYC",expostT_basm) le 1.e-13)
            = p_biofuelData(MS,"UVAP","GLYC",expostT_basm);

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 551-551):

           p_data(Rest,'HCOM',FUEL_ROWS,Years) = p_data(Rest,'DOMM',FUEL_ROWS,Years);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.apply_country)."""
    return value


def p_biofuelData_NAGR(nagr, exog):
    r"""p_biofuelData(MSnoEU28, "NAGR", biofuels, years): plus the exogenous demand.

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 364-365):

          p_biofuelData(MSnoEU28,"NAGR",biofuels,years) = p_biofuelData(MSnoEU28,"NAGR",biofuels,years)
            + p_biofuelData(MSnoEU28,"EXOG",biofuels,years);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.apply_country)."""
    return nagr + exog


def p_data_UVAD_biofuels(uvap, ctax):
    r"""p_data(MS, "UVAD", biofuels, expostT_basm) without one: the market price plus the consumption tax.

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 402-404):

          p_data(MS,"UVAD",biofuels,expostT_basm) $ ( (not p_data(MS,"UVAD",biofuels,expostT_basm))
                                                    $ p_data(MS,"UVAP",biofuels,expostT_basm))
            = p_data(MS,"UVAP",biofuels,expostT_basm)+ p_data(MS,"CTAX",biofuels,expostT_basm);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.apply_country)."""
    return uvap + ctax


def p_data_NAGR_default():
    r"""p_data(MS, "NAGR", SECO_BIOF, expostT_basm) from 2000 without one.

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 493-495):

           p_data(MS,"NAGR",SECO_BIOF,expostT_basm) $ (    ((ORDT(expostT_basm) GE ORDT("2000")) or SAMEAS(expostT_basm,"BASM"))
                                                       $ (NOT p_data(MS,"NAGR",SECO_BIOF,expostT_basm))
                                                       ) = 1E-15;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.apply_country)."""
    return 1E-15


def p_data_default():
    r"""p_data(MS, MAPR / DOMM / BIOF, SECO_BIOF / potentialStocks, expostT_basm) from 2000 without one (DOMM and BIOF
    without production or imports; the potential stocks with DOMM).

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 497-499):

           p_data(MS,"MAPR",SECO_BIOF,expostT_basm) $ (    ((ORDT(expostT_basm) GE ORDT("2000")) or SAMEAS(expostT_basm,"BASM"))
                                                       $ (NOT p_data(MS,"MAPR",SECO_BIOF,expostT_basm))
                                                       ) = 1E-14;

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 502-506):

           p_data(MS,"DOMM",SECO_BIOF,expostT_basm) $ (    ((ORDT(expostT_basm) GE ORDT("2000")) or SAMEAS(expostT_basm,"BASM"))
                                                       $ (p_data(MS,"MAPR",SECO_BIOF,expostT_basm) LT 1E-13)
                                                       $ (p_data(MS,"IMPT",SECO_BIOF,expostT_basm) LT 1E-13)
                                                       $ (NOT p_data(MS,"DOMM",SECO_BIOF,expostT_basm))
                                                       ) = 1E-14;

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 508-512):

           p_data(MS,"BIOF",SECO_BIOF,expostT_basm) $ (    ((ORDT(expostT_basm) GE ORDT("2000")) or SAMEAS(expostT_basm,"BASM"))
                                                       $ (p_data(MS,"MAPR",SECO_BIOF,expostT_basm) LT 1E-13)
                                                       $ (p_data(MS,"IMPT",SECO_BIOF,expostT_basm) LT 1E-13)
                                                       $ (NOT p_data(MS,"BIOF",SECO_BIOF,expostT_basm))
                                                       ) = 1E-14;

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 530-532):

           p_data(MS,"BIOF",potentialStocks,expostT_basm) $ (  ((ORDT(expostT_basm) GE ORDT("2000")) or SAMEAS(expostT_basm,"BASM"))
                                                             $ (NOT p_data(MS,"BIOF",potentialStocks,expostT_basm))
                                                             $ p_data(MS,"DOMM",potentialStocks,expostT_basm)) = 1E-14;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.apply_country)."""
    return 1E-14


def p_data_BIOF_stock(mapr, rate):
    r"""p_data(MS, "BIOF", "SWHE" / "RAPO", expostT_basm) where no stock is used: the biofuel's production over the
    extraction rate.

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 514-519):

           p_data(MS,"BIOF","SWHE",expostT_basm) $ (  (sum(STOCK_TO_FUEL(potentialStocks,"BIOE"),
                                                           p_data(MS,"BIOF",potentialStocks,expostT_basm)) LT 1E-12)
                                                    $ (p_data(MS,"MAPR","BIOE",expostT_basm) LT 1E-12)
                                                    $ p_data(MS,"DOMM","SWHE",expostT_basm)
                                                    $ ((ORDT(expostT_basm) GE ORDT("2000")) or SAMEAS(expostT_basm,"BASM")))
               = p_data(MS,"MAPR","BIOE",expostT_basm)/P_ExtrRates("BIOE","SWHE");

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 521-526):

           p_data(MS,"BIOF","RAPO",expostT_basm) $ (  (sum(STOCK_TO_FUEL(potentialStocks,"BIOD"),
                                                           p_data(MS,"BIOF",potentialStocks,expostT_basm)) LT 1E-12)
                                                    $ (p_data(MS,"MAPR","BIOD",expostT_basm) LT 1E-12)
                                                    $ ((ORDT(expostT_basm) GE ORDT("2000")) or SAMEAS(expostT_basm,"BASM"))
                                                    $ p_data(MS,"DOMM","RAPO",expostT_basm))
                                                 = p_data(MS,"MAPR","BIOD",expostT_basm)/P_ExtrRates("BIOD","RAPO");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.apply_country)."""
    return mapr / rate


def p_data_MAPR_DDGS(stocks, zero):
    r"""p_data(MS, "MAPR", "DDGS", expostT_basm) without one: the stocks' BIOF times their DDGS by-product
    coefficients.

    stocks: (BIOF, p_ByProduct) of the potential stocks with DDGS, in the caller's order.

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 535-539):

           p_data(MS,"MAPR","DDGS",expostT_basm) $ (  (sum(STOCK_TO_FUEL(potentialStocks,"BIOE"),
                                                           p_data(MS,"BIOF",potentialStocks,expostT_basm)) LT 1E-12)
                                                    $ (NOT p_data(MS,"MAPR","DDGS",expostT_basm))
                                                    $ ((ORDT(expostT_basm) GE ORDT("2000")) or SAMEAS(expostT_basm,"BASM")))
               = SUM(STOCK_TO_BY(potentialStocks,"DDGS"),p_data(MS,"BIOF",potentialStocks,expostT_basm)*p_ByProduct("DDGS",potentialStocks));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.apply_country)."""
    return sum((b * float(y) for b, y in stocks), zero)


def p_data_removed():
    r"""p_data(MS / Rest, ., ., years): removed (the years without COCO UAAR but the population; GROF of the secondary
    products).

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 544-544):

           p_data(MS,COLS,ROWS,years) $ ((NOT usable_years(MS,years)) $ (NOT (SAMEAS(COLS,"INHA") $ SAMEAS(ROWS,"LEVL"))))= 0;

    CAPRI's GAMS (captrd/load_coco1_data.gms l. 548-548):

           p_data(Rest,"GROF",SECOM,YEARS) = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops in the caller (coco.apply_country)."""
    return 0.0
