r"""CAPRI's report of the solved supply model (capmod/report_supply_model.gms, star 3.0): the PMP terms of the regional
objective at the solution, which CAPRI stores for the income and welfare accounts (income I3).

capri_mod/income/income_module.py (IncomeDistributionModule.producer_surplus) calls them with the regional NLP's
objective at the solution by part (CapriRegionalNLP.objective_parts).

Departures from CAPRI (each function's docstring): the units (EUR 1000; CAPRI's / 1000 to EUR million); v_labCap.scale
is 1 (set only in sens/sens.gms; supply_model/objective.py's module docstring); the model's PMP terms of the activity
levels are re-expressed on the income's cost basis (register DEP-55).
"""
from __future__ import annotations


def DATA_EAAG_PMPLevl(v_sumOfPmpTermsLevls, v_labCap_scale=1.0):
    r"""DATA(RU, "EAAG", "PMPLevl", "Y"): the PMP terms of the activity levels at the solution, with the sign of a
    gain (EUR 1000).

    CAPRI's GAMS (capmod/report_supply_model.gms l. 207-208):

        * --- Store items useful for income and welfare accounting
            DATA(RU,"EAAG","PMPLevl","Y") = -v_sumOfPmpTermsLevls.l(RU)*v_labCap.scale(RU) / 1000;

    In this project's notation: PMPLevl = - QUADRA_ = - (sum_j p_j y_j + 0.5 y'Qy) over the activity, technology-mix
    and split columns (supply_model/objective.py QUADRA_). Departures from CAPRI: the units (EUR 1000); the linear terms
    p_j are the model's re-expressed on the income's cost basis (income_module.producer_surplus, register DEP-55)."""
    return -float(v_sumOfPmpTermsLevls) * float(v_labCap_scale)


def DATA_EAAG_PMPFeed(v_sumOfPmpTermsFeed, v_labCap_scale=1.0):
    r"""DATA(RU, "EAAG", "PMPFeed", "Y"): the feeds' PMP terms at the solution (EUR 1000), CAPRI's sign.

    CAPRI's GAMS (capmod/report_supply_model.gms l. 209):

            DATA(RU,"EAAG","PMPFeed","Y") = v_sumOfPmpTermsFeed.l(RU)*v_labCap.scale(RU) / 1000;

    In this project's notation: PMPFeed = v_sumOfPmpTermsFeed = sum_a h_a sum_f u_f (CNST_f + 0.5 SLOP_f u_f)
    (supply_model/objective.py QUADRF_), CAPRI maximising; the model minimises, so its term enters with the opposite
    sign (the caller passes minus the model's feed PMP terms). Departures from CAPRI: the units (EUR 1000)."""
    return float(v_sumOfPmpTermsFeed) * float(v_labCap_scale)


def DATA_EAAG_PMPLandTrans(v_pmpCostLandMarket, v_landSupCost=0.0, v_labCap_scale=1.0):
    r"""DATA(RU, "EAAG", "PMPLandTrans", "Y"): minus the land market's PMP cost at the solution (EUR 1000), the
    branch without CAPRI's trustee land option (Trustee_land off).

    CAPRI's GAMS (capmod/report_supply_model.gms l. 210-220):

            DATA(RU,"EAAG","PMPLandTrans","Y") = (

        $iftheni.tru8 %Trustee_land%==ON
                   - v_pmpCostLandMarket.l(RU)*p_landMarketScale $ ((p_landIsFixed eq 0) $ (p_PMPStep1 ne 1) $ v_labCap.range(RU))
        *            activate for testing if calibration works with exogenously given land rents:
        *          - v_pmpCostLandMarket(RUNR)*p_landMarketScale $ ((p_PMPStep1 ne 1) $ v_labCap.range(RUNR) $ (not sameas(runr,"ukn00000")))
        $else.tru8
                   - v_pmpCostLandMarket.l(RU)*v_labCap.scale(runr) $ ((p_landIsFixed eq 0) $ (p_PMPStep1 ne 1) $ v_labCap.range(RU))
                   - v_landSupCost.l(RU)       $ ((p_landIsFixed eq 0) $ (p_PMPStep1 ne 1))
        $endif.tru8
            )/1000;

    In this project's notation: PMPLandTrans = - (v_pmpCostLandMarket + v_landSupCost), v_pmpCostLandMarket =
    sum_t (cnst_t + rent_t) L_t + 0.5 L'Q_L L over the land columns (supply_model/land.py LandMarket_cnst,
    LandMarket_quad; supply/land.py _land_augment). Departures from CAPRI: the units (EUR 1000); the model has no land
    supply cost (e_landSupCost): v_landSupCost 0; the conditions on p_landIsFixed and p_PMPStep1 hold in a simulation
    with the land market (the model's land market is its augmented problem; without it there are no land columns and
    the term is 0)."""
    return -(float(v_pmpCostLandMarket) * float(v_labCap_scale) + float(v_landSupCost))
