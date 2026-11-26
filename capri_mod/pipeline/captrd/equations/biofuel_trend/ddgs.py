r"""The DDGS supports (moved from capri_mod/pipeline/captrd/equations/biofuel_trends.py as they were, 26 November 2026).
"""
from __future__ import annotations




def p_expertSupprt_MAPR_DDGS(pairs):
    r"""p_expertSupprt(MSIncl, "MAPR", "DDGS", exanteT, "Absolute"): the by-product yields times the feedstock use,
    summed over the stocks giving DDGS.

    pairs: (PRCBY, BIOF) of those stocks.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1224-1227):

          p_expertSupprt(MSIncl,"MAPR","DDGS",exanteT,"Absolute")
             $ SUM(STOCK_TO_BY(OSECO,"DDGS"), p_expertSupprt(MSIncl,"PRCBY",OSECO,exanteT,"Absolute"))
             = SUM(STOCK_TO_BY(OSECO,"DDGS"), p_expertSupprt(MSIncl,"PRCBY",OSECO,exanteT,"Absolute")
             * p_expertSupprt(MSIncl,"BIOF",OSECO,exanteT,"Absolute") );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return sum(a * b for a, b in pairs)


def p_expertSupprt_FEDM_DDGS(mapr, fpro):
    r"""p_expertSupprt(MSIncl, "FEDM", "DDGS", exanteT, "Absolute"): DDGS production times one less its share of DDGS
    and the feed protein (GROF.FPRO of BASM).

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1232-1236):

          p_expertSupprt(MSIncl,"FEDM","DDGS",exanteT,"Absolute")
               $ (p_expertSupprt(MSIncl,"MAPR","DDGS",exanteT,"Absolute")+P_Result(MSIncl,"GROF","FPRO",exanteT,"BASM"))
               = p_expertSupprt(MSIncl,"MAPR","DDGS",exanteT,"Absolute")
               * (1. - p_expertSupprt(MSIncl,"MAPR","DDGS",exanteT,"Absolute")
                     /(p_expertSupprt(MSIncl,"MAPR","DDGS",exanteT,"Absolute")+P_Result(MSIncl,"GROF","FPRO",exanteT,"BASM")));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return mapr * (1. - mapr / (mapr + fpro))


def p_expertSupprt_DOMM_DDGS(fedm):
    r"""p_expertSupprt(MSIncl, "DOMM", "DDGS", exanteT, "Absolute"): its feed use.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1238-1238):

          p_expertSupprt(MSIncl,"DOMM","DDGS",exanteT,"Absolute") = p_expertSupprt(MSIncl,"FEDM","DDGS",exanteT,"Absolute");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return fedm


def p_expertSupprt_NTRD_DDGS(mapr, domm):
    r"""p_expertSupprt(MSIncl, "NTRD", "DDGS", exanteT, "Absolute") with production: production less demand.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1240-1241):

          p_expertSupprt(MSIncl,"NTRD","DDGS",exanteT,"Absolute") $ p_expertSupprt(MSIncl,"MAPR","DDGS",exanteT,"Absolute")
              = p_expertSupprt(MSIncl,"MAPR","DDGS",exanteT,"Absolute") - p_expertSupprt(MSIncl,"DOMM","DDGS",exanteT,"Absolute") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return mapr - domm


def p_expertSupprt_IMPT_DDGS(mapr):
    r"""p_expertSupprt(MSIncl, "IMPT", "DDGS", exanteT, "Absolute") with feed use: 5% of production, at least
    1E-12.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1245-1246):

          p_expertSupprt(MSIncl,"IMPT","DDGS",exanteT,"Absolute") $ p_expertSupprt(MSIncl,"FEDM","DDGS",exanteT,"Absolute")
              = MAX(1.E-12,0.05*p_expertSupprt(MSIncl,"MAPR","DDGS",exanteT,"Absolute"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return max(1.E-12, 0.05 * mapr)


def p_expertSupprt_EXPT_DDGS(impt, ntrd):
    r"""p_expertSupprt(MSIncl, "EXPT", "DDGS", exanteT, "Absolute"): imports plus net trade.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1247-1248):

          p_expertSupprt(MSIncl,"EXPT","DDGS",exanteT,"Absolute")
                                    = p_expertSupprt(MSIncl,"IMPT","DDGS",exanteT,"Absolute")+p_expertSupprt(MSIncl,"NTRD","DDGS",exanteT,"Absolute") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return impt + ntrd
