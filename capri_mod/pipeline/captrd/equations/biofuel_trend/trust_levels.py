r"""The trust level supports (moved from capri_mod/pipeline/captrd/equations/biofuel_trends.py as they were, 26 November
2026).
"""
from __future__ import annotations




def P_expertSupprt_TrustLevl_7():
    r"""P_expertSupprt(MSIncl, ., SECO_BIOF / FossilFuels / bioStock / CERE, exAnte, "TrustLevl") of the biofuel
    positions, the fuels, the feedstocks and their coefficients with a value (PRCB and PRCBY where the feedstock is
    used): 7.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1428-1428):

          P_expertSupprt(MSIncl,COLS,SECO_BIOF,exAnte,"TrustLevl")   $ P_expertSupprt(MSIncl,COLS,SECO_BIOF,exAnte,"Absolute") = 7;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1434-1434):

          P_expertSupprt(MSIncl,COLS,FossilFuels,exAnte,"TrustLevl") $ P_expertSupprt(MSIncl,COLS,FossilFuels,exAnte,"Absolute") = 7;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1436-1436):

          P_expertSupprt(MSIncl,"BIOF",bioStock,exAnte,"TrustLevl")  $ P_expertSupprt(MSIncl,"BIOF",bioStock,exAnte,"Absolute") = 7;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1438-1438):

          P_expertSupprt(MSIncl,"BIOF","CERE",exAnte,"TrustLevl")    $ P_expertSupprt(MSIncl,"BIOF","CERE",exAnte,"Absolute") = 7;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1440-1440):

          P_expertSupprt(MSIncl,"PRCB",bioStock,exAnte,"TrustLevl")  $ P_expertSupprt(MSIncl,"BIOF",bioStock,exAnte,"Absolute") = 7;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1442-1442):

          P_expertSupprt(MSIncl,"PRCBY",bioStock,exAnte,"TrustLevl") $ P_expertSupprt(MSIncl,"BIOF",bioStock,exAnte,"Absolute") = 7;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return 7.0


def P_expertSupprt_TrustLevl_1():
    r"""P_expertSupprt(MSIncl, IMPT / EXPT, SECO_BIOF, exAnte, "TrustLevl") and the fuels' EXPD with a value: 1.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1430-1430):

          P_expertSupprt(MSIncl,"IMPT",SECO_BIOF,exAnte,"TrustLevl") $ P_expertSupprt(MSIncl,"IMPT",SECO_BIOF,exAnte,"Absolute") = 1;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1432-1432):

          P_expertSupprt(MSIncl,"EXPT",SECO_BIOF,exAnte,"TrustLevl") $ P_expertSupprt(MSIncl,"EXPT",SECO_BIOF,exAnte,"Absolute") = 1;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1444-1446):

          p_expertSupprt(MSIncl,"EXPD",fuels,exAnte,"TrustLevl")     $ (    p_expertSupprt(MSIncl,"UVAD",fuels,exAnte,"Absolute")
                                                                      and p_expertSupprt(MSIncl,"INHA",fuels,exAnte,"Absolute")
                                                                      and p_expertSupprt(MSIncl,"EXPD",fuels,exAnte,"Absolute")) = 1.;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return 1.


def p_expertSupprt_TrustLevl_DDGS():
    r"""p_expertSupprt(MSIncl, FEDM / DOMM / MAPR / EXPT / IMPT, "DDGS", exAnte, "TrustLevl") with a value: 3.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1448-1448):

          p_expertSupprt(MSIncl,"FEDM","DDGS",exAnte,"TrustLevl") $ p_expertSupprt(MSIncl,"FEDM","DDGS",exAnte,"Absolute") = 3;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1449-1449):

          p_expertSupprt(MSIncl,"DOMM","DDGS",exAnte,"TrustLevl") $ p_expertSupprt(MSIncl,"DOMM","DDGS",exAnte,"Absolute") = 3;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1450-1450):

          p_expertSupprt(MSIncl,"MAPR","DDGS",exAnte,"TrustLevl") $ p_expertSupprt(MSIncl,"MAPR","DDGS",exAnte,"Absolute") = 3;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1451-1451):

          p_expertSupprt(MSIncl,"EXPT","DDGS",exAnte,"TrustLevl") $ p_expertSupprt(MSIncl,"EXPT","DDGS",exAnte,"Absolute") = 3;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1452-1452):

          p_expertSupprt(MSIncl,"IMPT","DDGS",exAnte,"TrustLevl") $ p_expertSupprt(MSIncl,"IMPT","DDGS",exAnte,"Absolute") = 3;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return 3.0


def p_expertSupprt_NTRD_DDGS_TrustLevl(trust_expt, ntrd, expt):
    r"""p_expertSupprt(MSIncl, "NTRD", "DDGS", exAnte, "TrustLevl") with net trade and exports: the exports' trust
    times net trade over exports.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1456-1459):

          p_expertSupprt(MSIncl,"NTRD","DDGS",exAnte,"TrustLevl") $ (    p_expertSupprt(MSIncl,"NTRD","DDGS",exAnte,"Absolute")
                                                                   and p_expertSupprt(MSIncl,"EXPT","DDGS",exAnte,"Absolute"))
                 = 1* p_expertSupprt(MSIncl,"EXPT","DDGS",exAnte,"TrustLevl")
                 * P_expertSupprt(MSIncl,"NTRD","DDGS",ExAnte,"Absolute")/P_expertSupprt(MSIncl,"EXPT","DDGS",ExAnte,"Absolute") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return 1 * trust_expt * ntrd / expt
