r"""CAPRI's income indicators per activity (reports/calc_inc_indic.gms, star 3.0), which its simulation year's report
calls on the supply models' regions (reports/sol_simy.gms l. 2533). capri_mod/income/income_module.py
(IncomeDistributionModule.income_parts) calls them at each regional solution (income I1).
"""
from __future__ import annotations


def DATA_MGVA(r, FEED_lin, FEED_sol):
    r"""DATA(RU, MPACT, "MGVA", SIMY) of an activity with a level, per ha or head (EUR): its outputs less its inputs at
    the solution, valued at the simulation year's unit values, plus its premiums.

    CAPRI's GAMS (reports/calc_inc_indic.gms l. 30-49):

            DATA(%regions%,MPACT,"TOOU","%SIMY%")  $ p_dataCopy(%regions%,MPACT,"LEVL","%SIMY%")
              = SUM( PACT_TO_O(MPACT,O), p_dataCopy(%regions%,MPACT,O,"%SIMY%") * p_dataCopy(%regions%,"UVAG",O,"%SIMY%"))   * 0.001;
            DATA(%regions%,MPACT,"TOOU","Y")   $ DATA(%regions%,MPACT,"LEVL","%SIMY%") = DATA(%regions%,MPACT,"TOOU","%SIMY%");
        *
            p_dataCopy(%regions%,"UVAG",I,"%SIMY%")      = DATA(%regions%,"UVAG",I,"%SIMY%");
            p_dataCopy(%regions%,MPACT,I,"%SIMY%")       = DATA(%regions%,MPACT,I,"%SIMY%");
            DATA(%regions%,MPACT,"TOIN","%SIMY%") $ p_DataCopy(%regions%,MPACT,"LEVL","%SIMY%")
              =  SUM( PACT_TO_I(MPACT,I) $ p_DataCopy(%regions%,MPACT,I,"%SIMY%"),
                     p_DataCopy(%regions%,MPACT,I,"%SIMY%") * p_DataCopy(%regions%,"UVAG",I,"%SIMY%")) * 0.001;
            DATA(%regions%,MPACT,"TOIN","Y")   $ DATA(%regions%,MPACT,"LEVL","%SIMY%") = DATA(%regions%,MPACT,"TOIN","%SIMY%");
        *
            DATA(%regions%,MPACT,"GVAP","%SIMY%") $ DATA(%regions%,MPACT,"LEVL","%SIMY%")
              =  DATA(%regions%,MPACT,"TOOU","%SIMY%")   - DATA(%regions%,MPACT,"TOIN","%SIMY%");
            DATA(%regions%,MPACT,"GVAP","Y")   $ DATA(%regions%,MPACT,"LEVL","%SIMY%") = DATA(%regions%,MPACT,"GVAP","%SIMY%");
        *
        *   ---- modified gross value added
        *
            DATA(%regions%,MPACT,"MGVA","%SIMY%") $ DATA(%regions%,MPACT,"LEVL","%SIMY%")
               =  DATA(%regions%,MPACT,"GVAP","%SIMY%") + DATA(%regions%,MPACT,"PRME","%SIMY%");
            DATA(%regions%,MPACT,"MGVA","Y")   $ DATA(%regions%,MPACT,"LEVL","%SIMY%") = DATA(%regions%,MPACT,"MGVA","%SIMY%");

    In this project's notation: MGVA_a = TOOU_a - TOIN_a + PRME_a. The model's form: the activity's linear margin r_a
    (supply_module._compute_net_revenues, LINEAR_netRevenue: revenue - input cost + premium per unit, at the solve's
    prices and the year's coefficients) less the change of its feed, the solved ration per unit at its report prices
    FEED_sol against the feed value per unit the margin carries FEED_lin (CAPRI's TOIN takes the solution's feed,
    sol_simy.gms l. 254-257):

        MGVA_a = r_a - (FEED_sol_a - FEED_lin_a)

    Departures from CAPRI: the activity's outputs, inputs and premiums are not kept item by item, so TOOU, TOIN and
    GVAP are not computed apart (income inventory 8.6, route 1; CAPRI's form item by item, TOIN = SUM(I, DATA(a, I,
    "Y") x UVAG_I), needs the year's coefficients per input); the mitigation options' cost and revenue, which
    sol_simy.gms l. 1471-1473 put in the activities' TOIN and TOOU (mitiI, mitiO), are booked at the region
    (coupling/equations/sol_simy.py DATA_AGGT_MGVA), since the model has several of them per region only (the
    fertiliser options, urea substitution, the winter cover: capri_mod/income/mitigation_items.py); the region's total
    is the same."""
    return float(r) - (float(FEED_sol) - float(FEED_lin))
