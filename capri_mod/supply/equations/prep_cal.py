r"""CAPRI's preparation of the calibration (supply/prep_cal.gms, star 3.0): the permanent grassland rule's dual at the
calibration point.

capri_mod/supply/policy.py (PolicyBlock._cap_rules_spec) calls it; capri_mod/supply/capri_regional_nlp.py
(CapriRegionalNLP.calibrate) fixes the rule's multiplier at it.
"""
from __future__ import annotations


def p_dualGreening(D_AREA_ARAB, D_AREA_GRAS):
    r"""p_dualGreening(regions, GRAS): the permanent grassland rule's dual at the calibration point, minus the gap
    between the arable and the grassland rent (EUR/ha; the rule's multiplier its absolute value).

    CAPRI's GAMS (supply/prep_cal.gms l. 118-119):

          p_dualGreening(%regions%,GRAS)$[activeGreeningMeasures("permGras")]
            =- ABS((DATA(%regions%,"ARAB","D_AREA","Y") - DATA(%regions%,"GRAS","D_AREA","Y")));

    Departures from CAPRI: the rents CAPRI's assumed land rents (cal_land_nests.gms; the caller's); the multiplier
    fixed in the calibration's fit (CAPRI's term in GRAE's linear terms, l. 127-132, the same first-order
    condition)."""
    return -abs(D_AREA_ARAB - D_AREA_GRAS)
