r"""CAPRI's landscape target (pol_input/greendeal/landscape.gms, star 3.0): the fallow floor and the crop diversification
limit lowered under it.

capri_mod/supply/supply_module.py (RegionalSupplyModel._build_constraints) and capri_mod/supply/policy.py
(PolicyBlock._cap_rules_spec) call these; the member states' missing shares are data read (p_setAsideTarget).
"""
from __future__ import annotations

import numpy as np


def DATA_FALL_FLOOR(lndscpTarg, p_setAsideTarget, UAAR, SETF):
    r"""DATA(ru, "FALL", "FLOOR", SIMY): the fallow floor, the requested share over the 10% target (lndscpTarg / 10)
    x the member state's missing share of UAA x UAAR, plus the existing set-aside (SETF).

    CAPRI's GAMS (pol_input/greendeal/landscape.gms l. 54-57):

          data(ru,"FALL","FLOOR","%simy%") $ p_baselineDataout(ru,"","UAAR","LEVL","%simy%")
        *     In a transition phase (say for 2025) we may specify targets lower thn 10%:
            = %lndscpTarg%/10*p_setAsideTarget(ru) * p_baselineDataout(ru,"","UAAR","LEVL","%simy%")
              + p_baselineDataout(ru,"","SETF","LEVL","%simy%");

    In this project's notation: F = (s / 0.10) (m / 100) UAAR + SETF (s the share, m the missing share in points).
    Departures from CAPRI: UAAR and SETF the model's base (CAPRI's baseline dataout)."""
    return (lndscpTarg / 0.10) * (p_setAsideTarget / 100.0) * UAAR + SETF


def p_DPGreeningLimits_cropDiv(cropDiv, X, T, FLOOR):
    r"""p_DPGreeningLimits(RU, "cropDiv") under the fallow floor: the smaller of the limit and the Shannon index with
    the floor added to every group's area and to the annual area (X the groups' areas, T the annual area), so that the
    rising fallow land does not make the rule infeasible (the caller applies it where the floor is above 0).

    CAPRI's GAMS (pol_input/greendeal/landscape.gms l. 75-90):

           p_DPGreeningLimits(RU,"cropDiv") $  (activeGreeningMeasures("cropDiv")
                                            $   data(ru,"FALL","FLOOR","%simy%"))

           = min( p_DPGreeningLimits(RU,"cropDiv"),

             -sum(cropDivGrps $ SUM(cropDivGrps_mCact(cropDivGrps,annualCrops), DATA(RU,annualCrops,"LEVL","Y")),

                   (SUM(cropDivGrps_mCact(cropDivGrps,annualCrops),DATA(RU,annualCrops,"LEVL","Y"))
                   + data(ru,"FALL","FLOOR","%simy%"))
                    /(DATA(RU,"Annc","LEVL","Y") + data(ru,"FALL","FLOOR","%simy%"))

                 * LOG((SUM(cropDivGrps_mCact(cropDivGrps,annualCrops), DATA(RU,annualCrops,"LEVL","Y"))
                                    + data(ru,"FALL","FLOOR","%simy%"))
                    /(DATA(RU,"Annc","LEVL","Y") + data(ru,"FALL","FLOOR","%simy%")))
                 ))
            ;

    In this project's notation: H0 = min(H0, - sum_g (X_g + F)/(T + F) log((X_g + F)/(T + F))). Departures from
    CAPRI: the groups' areas with the model's floors under the logs (the caller's), T their sum."""
    return min(cropDiv, -sum((x + FLOOR) / (T + FLOOR) * np.log((x + FLOOR) / (T + FLOOR)) for x in X))
