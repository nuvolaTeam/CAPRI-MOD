r"""CAPRI's organic area target's yield gap (pol_input/greendeal/organic_area.gms, star 3.0).

capri_mod/supply/policy.py (PolicyBlock._organic_yield_gap) calls it.
"""
from __future__ import annotations

import pandas as pd


def DATA_Yild_percentageChange(p_organicYieldGap, p_organicYieldGap_CEN):
    r"""DATA(ms, organicCrops, "Yild", "percentageChange") before the target's scaling: the organic yield gap of the
    member state's PESETA region and the crop's product group, the Central-European (CEN) one where it has none; as a
    fraction (0 where neither is set; NaN is no value).

    CAPRI's GAMS (pol_input/greendeal/organic_area.gms l. 176-181):

          DATA(ms,organicCrops,"Yild","percentageChange")
            = sum(ms2peseta(ms,pesetaRegion),
                 sum(pact2yieldGap(organicCrops,yieldGapProd), p_organicYieldGap(pesetaRegion,yieldGapProd)
                                                             + p_organicYieldGap("CEN",yieldGapProd)
                                                             $ (not p_organicYieldGap(pesetaRegion,yieldGapProd))
                                                             ))

    Departures from CAPRI: the gap's absolute value / 100 (a fraction); the scaling with the crop's target (l. 191-193)
    the caller's; no 0.45 factor (pest_disagg off)."""
    for v in (p_organicYieldGap, p_organicYieldGap_CEN):
        if v is not None and pd.notna(v):
            return abs(float(v)) / 100.0
    return 0.0
