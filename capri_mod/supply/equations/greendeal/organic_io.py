r"""CAPRI's organic target's input changes (pol_input/greendeal/organic_io.gms, star 3.0): plant protection and the
organic crops' other inputs.

capri_mod/supply/policy.py (PolicyBlock._apply_greendeal_input_changes) calls these, through conventional_io.py for
the regional percentage.
"""
from __future__ import annotations


def DATA_GROF_PLAP_percentageChange(p_organicAreaTarget):
    r"""DATA(RU, "GROF", "PLAP", "percentageChange") of the organic target: plant protection falls by the region's UAA
    target (a share; 0 without one).

    CAPRI's GAMS (pol_input/greendeal/organic_io.gms l. 74-75):

           DATA(RU,"GROF","PLAP","percentageChange") $ (region_plap(ru) $ p_organicAreaTarget(ru))
              =  -%plapReduction% * p_organicAreaTarget(ru);

    In this project's notation: pc = - o_R. Departures from CAPRI: as a share (CAPRI's % with %plapReduction% 100)."""
    return -p_organicAreaTarget if p_organicAreaTarget > 0 else 0.0


def DATA_INPO_BAS_topup(p_organicAreaTargetCrops, EFUL):
    r"""The top-up of DATA(RU, organicCrops, "INPO", "BAS"): twice the crop's organic target x its fuel cost (EFUL;
    the setting organic_topup_at_fuel_cost, else EFUL's INPO valuation), per ha.

    CAPRI's GAMS (pol_input/greendeal/organic_io.gms l. 111-115):

          DATA(RU,organicCrops,"INPO","BAS") $ region_plap(ru)
             =  DATA(RU,organicCrops,"INPO","BAS")
                +  (DATA(RU,organicCrops,"EFUL","BAS") * (%plapReduction% * p_organicAreaTargetCrops(ru,organicCrops) *2/100)) $ (DATA(RU,organicCrops,"EFUL","BAS"))
                +  (DATA(RU,organicCrops,"SERI","BAS") * (%plapReduction% * p_organicAreaTargetCrops(ru,organicCrops) *2/100)) $ (DATA(RU,organicCrops,"SERI","BAS"))
                ;

    In this project's notation: dINPO = 2 o_a EFUL. Departures from CAPRI: the SERI term (services) not added; the
    top-up valued at the fuel cost (CAPRI-ERROR-FIX organic_topup_at_fuel_cost; CAPRI adds the quantity to INPO,
    valued at INPO's price)."""
    return 2.0 * p_organicAreaTargetCrops * EFUL
