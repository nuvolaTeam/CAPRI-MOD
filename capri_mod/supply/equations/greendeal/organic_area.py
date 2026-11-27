r"""CAPRI's organic area target's yield gap (pol_input/greendeal/organic_area.gms, star 3.0).

capri_mod/supply/policy.py (PolicyBlock._organic_yield_gap) calls it.
"""
from __future__ import annotations

import pandas as pd


def DATA_Yild_percentageChange(p_organicYieldGap, p_organicYieldGap_CEN, pest_disagg=False):
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

    With the pesticide module (pest_disagg: setting supply.pest_disagg "agg5"), x 0.45 (l. 182-186):

        $iftheni.pes45  %pest_disagg%==on
        * Note2: reduce yield gaps according to the assumed share of pesticides which is 45% see inputs\PEST_COR.GMS,
        * because the pesticide part will be taken care of endogenously by a change in v_yldPestFac in supply_model.gms
            * 0.45
        $endif.pes45

    Departures from CAPRI: the gap's absolute value / 100 (a fraction); the scaling with the crop's target (l. 191-193)
    the caller's. The factor as CAPRI's code has it. A possible CAPRI error (reported 27 November 2026, not changed):
    inputs/pest_cor.gms l. 215-243 calibrates the pesticides' avoided damage to 45% of this gap
    (p_pestiEffectsByKultur = -0.45 x gap), the part the module's yield factor carries; the comment here asks to
    reduce the gap by that share, which leaves 55%, while the code keeps 45%."""
    for v in (p_organicYieldGap, p_organicYieldGap_CEN):
        if v is not None and pd.notna(v):
            return abs(float(v)) / 100.0 * (0.45 if pest_disagg else 1.0)
    return 0.0
