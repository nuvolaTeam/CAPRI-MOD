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


def DATA_FEED_SIMY(v_feedInpCoeff_A, v_actLevl_A, LEVL):
    r"""DATA(RU, MAACT, FEED, SIMY) of an activity with a level: the feed per head of the solution, the technologies'
    feed input coefficients weighted by their levels over the activity's level (kg per head). The report's
    digestibility and gases (l. 1627 on) take their rations from here.

    CAPRI's GAMS (reports/sol_simy.gms l. 254-257):

        *
           DATA(RU,MAACT,FEED,"%SIMY%") $ DATA(RU,MAACT,"LEVL","%SIMY%")
                    = SUM(A $ p_maxFeedShare(RU,MAACT,A,FEED), v_feedInpCoeff.L(RU,MAACT,A,FEED)*v_actLevl.L(RU,MAACT,A))
                              / DATA(RU,MAACT,"LEVL","%SIMY%");

    v_feedInpCoeff_A, v_actLevl_A: {A: value} of the technologies with a p_maxFeedShare for the feed (the caller
    applies that condition and DATA's LEVL one). Departures from CAPRI: none."""
    return sum(float(v_feedInpCoeff_A.get(t, 0.0) or 0.0) * float(lv or 0.0) for t, lv in v_actLevl_A.items()) / LEVL
