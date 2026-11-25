r"""CAPTRD's statements of global/create_longrun_info.gms (CAPRI star 3.0) on CAPREG's time series and the global
database before the GLOBIOM conversion's base-year factors (convert_globiom.gms l. 2017-2145), as named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it. capri_mod/pipeline/captrd/
globiom.py (prepare_capreg, prepare_datamarket) holds the loops and the conditions, and calls them; the arithmetic is
the port's.
"""
from __future__ import annotations


def P_capregData_UVAP(uvap_2002, uvad, prii, uvad_prii_2002):
    r"""P_capregData(NUTS0, "UVAP", rows, threeYearAv) without a value: 2002's moved by UVAD + PRII's change from
    2002.

    CAPRI's GAMS (global/create_longrun_info.gms l. 91-95):

          P_capregData(NUTS0,"UVAP",rows,threeYearAv) $ (not P_capregData(NUTS0,"UVAP",rows,threeYearAv)
                                                  and (P_capregData(NUTS0,"UVAD",rows,"2002") + P_capregData(NUTS0,"PRII",rows,"2002")))
           = P_capregData(NUTS0,"UVAP",rows,"2002")
             * (P_capregData(NUTS0,"UVAD",rows,threeYearAv) + P_capregData(NUTS0,"PRII",rows,threeYearAv))
             / (P_capregData(NUTS0,"UVAD",rows,"2002") + P_capregData(NUTS0,"PRII",rows,"2002"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (prepare_capreg, prepare_datamarket))."""
    return uvap_2002 * (uvad + prii) / uvad_prii_2002


def p_dataMarket_PROD(mapr):
    r"""p_dataMarket(RMAll, "PROD", rows, SIMYY) without a value: MAPR.

    CAPRI's GAMS (global/create_longrun_info.gms l. 98-98):

          p_dataMarket(RMAll,"PROD",rows,SIMYY) $ (NOT p_dataMarket(RMAll,"PROD",rows,SIMYY)) = p_dataMarket(RMAll,"MAPR",rows,SIMYY);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (prepare_capreg, prepare_datamarket))."""
    return mapr


def P_capregData_PROD(value):
    r"""P_capregData(NUTS0, "PROD", rows, SIMYY) without a value: GROF (MAPR for the secondary products, SECOM).

    CAPRI's GAMS (global/create_longrun_info.gms l. 100-102):

          P_capregData(NUTS0,"PROD",rows,SIMYY) $ (NOT P_capregData(NUTS0,"PROD",rows,SIMYY))
           = P_capregData(NUTS0,"GROF",rows,SIMYY) $ (NOT SECOM(ROWS))
           + P_capregData(NUTS0,"MAPR",rows,SIMYY) $      SECOM(ROWS) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (prepare_capreg, prepare_datamarket))."""
    return value
