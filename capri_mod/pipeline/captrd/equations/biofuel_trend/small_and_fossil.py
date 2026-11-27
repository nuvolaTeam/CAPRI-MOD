r"""The small and tiny biofuel positions and the fossil fuels' supports (moved from
capri_mod/pipeline/captrd/equations/biofuel_trends.py as they were, 26 November 2026).
"""
from __future__ import annotations




def p_expertSupprt_BIOF_small():
    r"""p_expertSupprt(MSIncl, "BIOF", bioStock, exanteT, "Absolute") below 0.01: removed (CAPRI's statement twice).

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1253-1254):

          p_expertSupprt(MSIncl,"BIOF",bioStock,exanteT,"Absolute")
            $ ABS(p_expertSupprt(MSIncl,"BIOF",bioStock,exanteT,"Absolute") lt 0.01) = 0;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1256-1257):

          p_expertSupprt(MSIncl,"BIOF",bioStock,exanteT,"Absolute")
          $ ABS(p_expertSupprt(MSIncl,"BIOF",bioStock,exanteT,"Absolute") lt 0.01)   = 0;

    Departures from CAPRI: CAPRI's condition ABS(x lt 0.01) is the comparison's truth (x below 0.01, negative values included); the port
    tests x < 0.01 once, the second statement finding nothing left; the domain condition and the loops in the caller (biofuel_trends.trends)."""
    return 0.0


def p_expertSupprt_BIOF_tiny():
    r"""p_expertSupprt(MSIncl, "BIOF", bioStock, exanteT, "Absolute") of a member state without a value where its
    fuels are produced and the stock had demand or biofuel use in %BASprimes%: 1E-14.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1259-1264):

          p_expertSupprt(MSIncl,"BIOF",bioStock,exanteT,"Absolute")
             $ ((NOT p_expertSupprt(MSIncl,"BIOF",bioStock,exanteT,"Absolute"))
                and sum(STOCK_TO_FUEL(bioStock,seco_biof), p_expertSupprt(MSIncl,"MAPR",seco_biof,exanteT,"Absolute"))
                and( P_Result(MSIncl,"domm",bioStock,"%BASprimes%","P_DATA")or P_Result(MSIncl,"BIOF",bioStock,"%BASprimes%","P_DATA"))
                and SUM(SAMEAS(MS,MSIncl),1)
                )= 1e-14;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return 1e-14


def P_expertSupprt_BIOF_CERE(values):
    r"""P_expertSupprt(MSIncl, "BIOF", "CERE", exAnte, "Absolute"): the cereals' feedstock use summed.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1271-1272):

          P_expertSupprt(MSIncl,"BIOF","CERE",exAnte,"Absolute")
            = SUM(CERE,  P_expertSupprt(MSIncl,"BIOF",CERE,exAnte,"Absolute"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return sum(values)


def P_expertSupprt_PRCB_tiny(mapr):
    r"""P_expertSupprt(MSIncl, PRCB / PRCBY, bioStock, exAnte, "Absolute") of a member state's stock without feedstock
    use: 1E-14 where its fuels are produced, else removed.

    mapr: whether one of the stock's fuels has production.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1274-1278):

          P_expertSupprt(MSIncl,"PRCB",bioStock,exAnte,"Absolute")
                $ ( (NOT P_expertSupprt(MSIncl,"BIOF",bioStock,exAnte,"Absolute"))
                     and P_expertSupprt(MSIncl,"PRCB",bioStock,exAnte,"Absolute")
                    and SUM(SAMEAS(MS,MSIncl),1)) = 1e-14
                        $ sum(STOCK_TO_FUEL(bioStock,seco_biof), p_expertSupprt(MSIncl,"MAPR",seco_biof,exAnte,"Absolute"));

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1280-1283):

          P_expertSupprt(MSIncl,"PRCBY",bioStock,exAnte,"Absolute")
           $  ((NOT P_expertSupprt(MSIncl,"BIOF",bioStock,exAnte,"Absolute"))
                and SUM(SAMEAS(MS,MSIncl),1)) = 1e-14
                    $ sum(STOCK_TO_FUEL(bioStock,seco_biof), p_expertSupprt(MSIncl,"MAPR",seco_biof,exAnte,"Absolute"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return 1e-14 if mapr else 0.0


def P_expertSupprt_MAPR_BIOE(pairs, secg, nagr):
    r"""P_expertSupprt(MSIncl, "mapr", "bioe", exAnte, "Absolute"): ethanol production from its feedstocks (BIOF x
    PRCB), second generation and non-agricultural ethanol.

    pairs: (BIOF, PRCB) of the ethanol stocks.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1288-1293):

          P_expertSupprt(MSIncl,"mapr","bioe",exAnte,"Absolute")
            =  SUM(STOCK_TO_FUEL(bioStock,"bioe"),
               ( P_expertSupprt(MSIncl,"BIOF",biostock,exAnte,"Absolute")* P_expertSupprt(MSIncl,"prcb",biostock,exAnte,"Absolute")))
        *
               +  P_expertSupprt(MSIncl,"SECG","BIOE",exAnte,"Absolute")
               +  P_expertSupprt(MSIncl,"NAGR","BIOE",exAnte,"Absolute");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return sum(b * p for b, p in pairs) + secg + nagr


def P_expertSupprt_constBioPos(value_2020):
    r"""P_expertSupprt(MSIncl, cols, rows, EXANTE, "Absolute") of the EU28 member states' biofuel positions
    (map_constBioPos) after 2020, with %constBionergy%: their 2020 value.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1314-1316):

          P_expertSupprt(MSIncl,cols,rows,EXANTE,"Absolute") $ ( (ordt(exante) gt ordt("2020")) $ map_constBioPos(cols,rows)
                                                               $ MS_TO_RMSAGG(MSincl,"EU028000") )
            =  P_expertSupprt(MSIncl,cols,rows,"2020","Absolute") ;

    Departures from CAPRI: EPS of 2020 is carried as EPS by the caller; the positions are the caller's (biofuel_trends.trends: hold)."""
    return value_2020


def P_expertSupprt_fossil(hcom):
    r"""P_expertSupprt(MSIncl, DOMM / HCOM, fossilFuels, EXANTE, "Absolute"): PRIMES's household consumption.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1325-1325):

          P_expertSupprt(MSIncl,"DOMM",fossilFuels,EXANTE,"Absolute") =  p_primesResults(MSIncl,"HCOM",fossilFuels,exAnte);

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1326-1326):

          P_expertSupprt(MSIncl,"HCOM",fossilFuels,EXANTE,"Absolute") =  p_primesResults(MSIncl,"HCOM",fossilFuels,exAnte);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return hcom


def p_expertSupprt_INHA_fossil(hcom, inha):
    r"""p_expertSupprt(MSINCL, "INHA", fossilfuels, exAnteT, "Absolute") where p_data has the population: the
    consumption per head (kg).

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1336-1337):

          p_expertSupprt(MSINCL,"INHA",fossilfuels,exAnteT,"Absolute") $ P_Result(MSINCL,"INHA","LEVL",ExAnteT,"P_Data")
            = p_expertSupprt(MSINCL,"HCOM",fossilfuels,exAnteT,"Absolute") / P_Result(MSINCL,"INHA","LEVL",ExAnteT,"P_Data") *1000;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return hcom / inha * 1000
