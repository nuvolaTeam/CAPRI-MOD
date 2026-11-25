r"""CAPRI's simulation year's report (reports/sol_simy.gms, star 3.0): the land owners' profit.

capri_mod/coupling/reporting.py (ReportingBlock._welfare_supply) calls it.
"""
from __future__ import annotations


def DATA_ProfitLandUse(d_area, d_area_lo, area):
    r"""DATA(RU, "ProfitLandUse", "LAND", SIMY): the land rents, each land type's area x its rent at the solution, the
    dual of its land row less that of its lower bound (sequences over the land types in the same order; EUR/ha x 1000
    ha = EUR 1000).

    CAPRI's GAMS (reports/sol_simy.gms l. 181-190):

           DATA(RU,"ProfitLandUse","LAND","%SIMY%")      = DATA(RU,"UAAR","levl","%SIMY%")*DATA(RU,"UAAR","d_area","Y")*0.001;
        *                                                   hypothetical rent if ASYM were completely used for non-ag:
        *                                                   Note: valuing ASYM with the agric rent x fac should give total ProfitLandUse>0
           DATA(RU,"ProfitLandUse","INPE","%SIMY%")      = (DATA(RU,"asym","levl","y")*DATA(RU,"UAAR","d_area","Y")  *20
        *                                                   opportunity cost as part of ASYM was not used for non-ag but for UAAR:
                                                           - v_landSupCost.l(RU)) * 0.001
        *                                                   The previous calculation may still miss the transformation cost
        *                                                   between agricultural land types, see branch f2f, r9566:
        *                                                  - v_pmpCostLandMarket.l(ru)) * 0.001
                                                         ;

    In this project's notation: RENT = sum_t (d_t - d_t^lo) A_t over ARAC, GRAS, FRUN. Departures from CAPRI: per
    land type with its own dual (CAPRI's UAAR x one d_area); the non-agricultural part (INPE, l. 184-190) not
    computed; the caller's units (EUR 1000, CAPRI's million EUR x 0.001)."""
    return sum((d - lo) * a for d, lo, a in zip(d_area, d_area_lo, area))
