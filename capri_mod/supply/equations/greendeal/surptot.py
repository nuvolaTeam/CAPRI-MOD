r"""CAPRI's nutrient surplus target (pol_input/greendeal/surptot.gms, star 3.0): the maximum N surplus per ha.

capri_mod/supply/supply_module.py (SupplyModule._solve_region_impl, the star3 rule) calls it.
"""
from __future__ import annotations


def data_SURTOT_MAXS(baseline_surplus, surpRedu):
    r"""data(srnuts2, "SURTOT", "MAXS", "Y"): the maximum N surplus per ha of an EU NUTS 2 region, its baseline surplus
    per ha x (1 - the reduction), every region alike (the relaxations apply from 2090 only).

    CAPRI's GAMS (pol_input/greendeal/surptot.gms l. 36-56):

          data(srnuts2,"SURTOT","MAXS","Y") $ (  SUM(R_RAGG(rall1,"EU27yr19"), R_RAGG(srnuts2,rall1))
                                                $ (p_baselineDataout(srnuts2,"perHa","SURTOT","NITF","%simy%") gt 0))

           = max(0,
        *          Some selective relaxations for regions, that gave infes or zero manure price results:
        *          Note: These relaxations were not needed anymore in inth July 2024 Catalyse scenarios, hence deactivated...
                 p_baselineDataout(srnuts2,"perHa","SURTOT","NITF","%simy%")*.6 $ ( (sameas(srnuts2,"sk030000") or sameas(srnuts2,"sk040000"))
        *                                                                           ... by requiring "gt 2090":
                                                                                  $ (calyea("%simy%") gt 2090)),
                 p_baselineDataout(srnuts2,"perHa","SURTOT","NITF","%simy%")*.6 $ ( (  sameas(srnuts2,"EL140000") or sameas(srnuts2,"ES120000")
                                                                                    or sameas(srnuts2,"ES130000")
                                                                                    or sameas(srnuts2,"EL250000") or sameas(srnuts2,"EL130000")
                                                                                    )
                                                                                  $ (calyea("%simy%") ge 2090)),
                 p_baselineDataout(srnuts2,"perHa","SURTOT","NITF","%simy%")*.7 $ ( (  sameas(srnuts2,"EL240000") or sameas(srnuts2,"EL430000")
                                                                                    )
                                                                                  $ (calyea("%simy%") ge 2090)),
                 p_baselineDataout(srnuts2,"perHa","SURTOT","NITF","%simy%")*.8 $ ( (sameas(srnuts2,"EL420000") or sameas(srnuts2,"EL410000"))
                                                                                  $ (calyea("%simy%") ge 2090)),
                 p_baselineDataout(srnuts2,"perHa","SURTOT","NITF","%simy%")*(1-%homogeneous_target%/100)
                ) * 0.001;

    In this project's notation: MAXS = s0 (1 - r). Departures from CAPRI: kg per ha (CAPRI's x 0.001, t); the
    baseline the model's own surplus per ha; the 2090 relaxations not applied (the simulation year 2030)."""
    return baseline_surplus * (1.0 - surpRedu)
