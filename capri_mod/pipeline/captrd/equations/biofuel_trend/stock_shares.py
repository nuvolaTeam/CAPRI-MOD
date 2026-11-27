r"""The agricultural fuel shares and the stock shares of the biofuels (moved from
capri_mod/pipeline/captrd/equations/biofuel_trends.py as they were, 26 November 2026).
"""
from __future__ import annotations




def p_agrFuel(mapr, secg, nagr, suga, prcb_suga, twin, prcb_twin, bioe):
    r"""p_agrFuel(MSIncl, runBio, exanteT) with production: the fuel from agricultural feedstocks, production less
    second generation and non-agricultural fuels (and for ethanol the sugar and wine ethanol already fixed), at least
    1E-14.

    bioe: the fuel is BIOE.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1154-1168):

            p_agrFuel(MSIncl,runBio,exanteT) $ p_expertSupprt(MSIncl,"MAPR",runBio,exanteT,"Absolute")
        *                    Total production
              = MAX(1e-14,   p_expertSupprt(MSIncl,"MAPR",runBio,exanteT,"Absolute")
        *                  - second generation fuels
                           - p_expertSupprt(MSIncl,"SECG",runBio,exanteT,"Absolute")
        *                  - biofuels not based on agricultural sources
                           - p_expertSupprt(MSIncl,"NAGR",runBio,exanteT,"Absolute")
                           -(
        *                    - sugar based bioethanol already fixed
                               p_expertSupprt(MSIncl,"BIOF","SUGA",exanteT,"Absolute")
                             * p_expertSupprt(MSIncl,"PRCB","SUGA",exanteT,"Absolute")
        *                    - fixed base period ethanol from wine
                             + p_expertSupprt(MSIncl,"BIOF","TWIN",exanteT,"Absolute")
                             * p_expertSupprt(MSIncl,"PRCB","TWIN",exanteT,"Absolute")) $ SAMEAS(RUNBIO,"BIOE") )
                                             ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    fix = (suga * prcb_suga + twin * prcb_twin) if bioe else 0.0
    return max(1e-14, mapr - secg - nagr - fix)


def p_stockShare_expostT(own, products):
    r"""p_stockShare(MSIncl, runStock, expostT): the stock's share of the fuel from its stocks (PRCB x BIOF of
    p_data), where both are nonzero.

    products: PRCB x BIOF of the fuel's stocks.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1172-1180):

            p_stockShare(MSIncl,runStock,expostT)
              $ (    SUM(STOCK_TO_FUEL(runStock1,runBio), P_Result(MSIncl,"PRCB",runStock1,expostT,"P_DATA")
                                                         *P_Result(MSIncl,"BIOF",runStock1,expostT,"P_DATA"))
                 and SUM(STOCK_TO_FUEL(runStock,runBio),  P_Result(MSIncl,"PRCB",runStock,expostT,"P_DATA")
                                                         *P_Result(MSIncl,"BIOF",runStock,expostT,"P_DATA")))
              = SUM(STOCK_TO_FUEL(runStock,runBio), P_Result(MSIncl,"PRCB",runStock,expostT,"P_DATA")
                                                    *P_Result(MSIncl,"BIOF",runStock,expostT,"P_DATA"))
              / SUM(STOCK_TO_FUEL(runStock1,runBio), P_Result(MSIncl,"PRCB",runStock1,expostT,"P_DATA")
                                                    *P_Result(MSIncl,"BIOF",runStock1,expostT,"P_DATA"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return own / sum(products)


def p_stockShare_exanteT(share_base):
    r"""p_stockShare(MSIncl, runStock, exanteT) of a stock with a processing coefficient in %BASprimes%: that year's
    share.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1184-1186):

            p_stockShare(MSIncl,runStock,exanteT)
              $ SUM(STOCK_TO_FUEL(runStock,runBio), P_Result(MSIncl,"PRCB",runStock,"%BASprimes%","P_DATA"))
                  = p_stockShare(MSIncl,runStock,"%BASprimes%");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return share_base


def p_stockShare_potential(share, potential):
    r"""p_stockShare(MSIncl, runStock, exanteT) of a stock whose DOMM has nObs: at least p_potentialStocks.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1189-1192):

            p_stockShare(MSIncl,runStock,exanteT)
              $  (SUM(STOCK_TO_FUEL(runStock,runBio),P_DATA(MSIncl,"DOMM",runStock,"nObs")))
              = SUM(STOCK_TO_FUEL(runStock,runBio) , MAX(p_stockShare(MSIncl,runStock,exanteT),
                                                         p_potentialStocks(MSIncl,runStock))  );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return max(share, potential)


def p_stockShare_runBio(shares):
    r"""p_stockShare(MSIncl, runBio, exanteT): the fuel's stocks' shares summed.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1196-1197):

            p_stockShare(MSIncl,runBio,exanteT)
             = SUM(STOCK_TO_FUEL(runStock1,runBio),p_stockShare(MSIncl,runStock1,exanteT)) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return sum(shares)


def p_stockShare_normalised(share, total):
    r"""p_stockShare(MSIncl, runStock, exanteT): the stock's share over the fuel's sum, where both are nonzero.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1200-1205):

            p_stockShare(MSIncl,runStock,exanteT)
              $ (    SUM(STOCK_TO_FUEL(runStock,runBio),p_stockShare(MSIncl,runBio,exanteT))
                 and SUM(STOCK_TO_FUEL(runStock,runBio),p_stockShare(MSIncl,runStock,exanteT)))

              = SUM(STOCK_TO_FUEL(runStock,runBio),p_stockShare(MSIncl,runStock,exanteT))
              / SUM(STOCK_TO_FUEL(runStock,runBio),p_stockShare(MSIncl,runBio,exanteT))  ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return share / total


def p_expertSupprt_BIOF_runStock(agr_fuel, share, prcb):
    r"""p_expertSupprt(MSIncl, "BIOF", runStock, exanteT, "Absolute") with a processing coefficient: the fuel from
    agricultural feedstocks times the stock's share over the coefficient.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1210-1218):

            p_expertSupprt(MSIncl,"BIOF",runStock,exanteT,"Absolute")
               $ SUM(STOCK_TO_FUEL(runStock,runBio), p_expertSupprt(MSIncl,"PRCB",runStock,exanteT,"Absolute"))

        *       - Baseline MAPR - NAGR - SECG of respective biofuel
                = (SUM(STOCK_TO_FUEL(runStock,runBio),p_agrFuel(MSIncl,runBio,exanteT))
        *       - multiplied with shares
                * p_stockShare(MSIncl,runStock,exanteT))
        *       - divided by processing coefficient
                / p_expertSupprt(MSIncl,"PRCB",runStock,exanteT,"Absolute")  ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return agr_fuel * share / prcb
