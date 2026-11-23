r"""CAPRI's 2003 reform's set-up (policy/calc_mtr_top.gms, star 3.0): the decoupling targets passed to the member
states and units, the year's declarations filled from the EU aggregates, the EU-10's Agenda 2000 schemes scaled to the
SAPS budget, the base year's data the payments are computed at and the modulated money.

capri_mod/policy/mtr.py (dd_targets, declarations_of_year, _unit_data, decoupled_budgets) loops over the regions,
schemes and items and calls these.
"""
from __future__ import annotations

import numpy as np

from capri_mod.policy.equations._gams import EPS, NA, nonzero


def p_premToDDTarget(premToDDTarget, premToDDTarget_from):
    r"""p_premToDDTarget(R, SIMY, PSDPAY_MTR_EL, DDTarget) of a region that has no target of the scheme (premToDDTarget,
    its values over the targets before any is set): the region's it inherits from (EU011000, BUR, EU_WEST for their
    member states; the member state for its units); None where it keeps its own or that is 0.

    CAPRI's GAMS (policy/calc_mtr_top.gms l. 47-50):

            option kill=RUNR;
            RUNR(MS) $ MAP_RR("EU011000",MS) = YES;
            p_premToDDTarget(RUNR,SIMY,PSDPay_MTR_EL,DDTarget) $ (not sum(DDTarget1, p_premToDDTarget(RUNR,SIMY,PSDPay_MTR_EL,DDTarget1)))
                                               = p_premToDDTarget("EU011000",SIMY,PSDPay_MTR_EL,DDTarget);

    and the same at l. 52-56 (RO000000, BG000000 from BUR), 60-63 (EU_WEST's members) and 67-68 (the units from their
    member state). Departures from CAPRI: none (the regions, RUNR, the caller's)."""
    if any(premToDDTarget):
        return None
    return premToDDTarget_from if premToDDTarget_from else None


def p_premDataE_PSGROUP(value, value_from):
    r"""p_premDataE(MS, SIMY, PSDPAY, PSGROUP) of a member state without a rate of its own (EPS is one): the rate of
    EU015000 or EU025000 (the latter for the EU-25 from 2004 and the EU-27 from 2007, as CAPRI writes l. 101-103);
    BL400000's from BL000000 (l. 118-119); None where it keeps its own.

    CAPRI's GAMS (policy/calc_mtr_top.gms l. 94-103):

            p_premDataE(MS,SIMY,PSDPAY,PSGROUP)   $ ((NOT p_premDataE(MS,SIMY,PSDPAY,PSGROUP))
                   and MAP_RR("EU015000",MS)) = p_premDataE("EU015000",SIMY,PSDPAY,PSGROUP);

            p_premDataE(MS,SIMY,PSDPAY,PSGROUP)   $ ((NOT p_premDataE(MS,SIMY,PSDPAY,PSGROUP))
                   and (MAP_RR("EU015000",MS) or ((CALYEA(SIMY) GE CALYEA("2004")) and MAP_RR("EU025000",MS))))
                    = p_premDataE("EU025000",SIMY,PSDPAY,PSGROUP);

            p_premDataE(MS,SIMY,PSDPAY,PSGROUP)   $ ((NOT p_premDataE(MS,SIMY,PSDPAY,PSGROUP))
                and (MAP_RR("EU015000",MS) or ((CALYEA(SIMY) GE CALYEA("2007")) and MAP_RR("EU027000",MS))))
                 = p_premDataE("EU025000",SIMY,PSDPAY,PSGROUP);

    Departures from CAPRI: the year's declarations (def_policy.gms's, the caller's), not the time series."""
    return None if nonzero(value) else value_from


def p_premDataE_APPTYPE(APPTYPE, PSGROUP_values, APPTYPE_from):
    r"""p_premDataE(MS, SIMY, PSDPAY, "APPTYPE") of a member state with a rate above 0 and no application type of its
    own: EU015000's, then EU025000's, then EU028000's (the caller's order); None where the condition is false or the
    aggregate has none.

    CAPRI's GAMS (policy/calc_mtr_top.gms l. 106-116):

            p_premDataE(MS,SIMY,PSDPAY,"APPTYPE") $ ((NOT p_premDataE(MS,SIMY,PSDPAY,"APPTYPE"))
                          and sum(PSGROUP $ (p_premDataE(MS,SIMY,PSDPAY,PSGROUP) GT 0),1))
                =   p_premDataE("EU015000",SIMY,PSDPAY,"APPTYPE");

            p_premDataE(MS,SIMY,PSDPAY,"APPTYPE") $ ((NOT p_premDataE(MS,SIMY,PSDPAY,"APPTYPE"))
                          and sum(PSGROUP $ (p_premDataE(MS,SIMY,PSDPAY,PSGROUP) GT 0),1))
                =   p_premDataE("EU025000",SIMY,PSDPAY,"APPTYPE");

            p_premDataE(MS,SIMY,PSDPAY,"APPTYPE") $ ((NOT p_premDataE(MS,SIMY,PSDPAY,"APPTYPE"))
                          and sum(PSGROUP $ (p_premDataE(MS,SIMY,PSDPAY,PSGROUP) GT 0),1))
                =   p_premDataE("EU028000",SIMY,PSDPAY,"APPTYPE");

    Departures from CAPRI: none."""
    if nonzero(APPTYPE):
        return None
    if not any(v not in (EPS, NA) and not isinstance(v, str) and v > 0 for v in PSGROUP_values):
        return None
    return APPTYPE_from


def p_totalBudget(terms):
    r"""p_totalBudget(MS, SIMY): an EU-10 or BUR member state's Agenda 2000 budget, the sum of its schemes' ceiling
    levels times rates (times the historical cereal yield for DPGRCU) and DPNE_MEAT's ceiling value; terms the seven
    terms' factors in CAPRI's order (one factor for the last).

    CAPRI's GAMS (policy/calc_mtr_top.gms l. 159-166):

                  p_totalBudget(MS,SIMY) $ ((p_premDataE(MS,SIMY,"DPMTR","CEILVAL") gt eps) and (MAP_RR("EU010000",MS) or MAP_RR("BUR",MS)))
                     = p_premDataE(MS,SIMY,"DPGRCU","CeilLev")    * DATA(MS,"CERE","HSTY",SIMY) * p_premDataE(MS,SIMY,"DPGRCU","PGGRCU")
                     + p_premDataE(MS,SIMY,"DPSCOW","CeilLev")    * p_premDataE(MS,SIMY,"DPSCOW","PGSCOW")
                     + p_premDataE(MS,SIMY,"DPBULF","CeilLev")    * p_premDataE(MS,SIMY,"DPBULF","PGBULF")
                     + p_premDataE(MS,SIMY,"DPSHGM","CeilLev")    * p_premDataE(MS,SIMY,"DPSHGM","PGSHGM")
                     + p_premDataE(MS,SIMY,"DPSL_ADCT","CeilLev") * p_premDataE(MS,SIMY,"DPSL_ADCT","PGMEAT")
                     + p_premDataE(MS,SIMY,"DPSL_CALV","CeilLev") * p_premDataE(MS,SIMY,"DPSL_CALV","PGCALV")
                     + p_premDataE(MS,SIMY,"DPNE_MEAT","CeilVal");

    Departures from CAPRI: none (NA in a term, which GAMS propagates, the caller's)."""
    return sum(float(np.prod(x)) if len(x) > 1 else x[0] for x in terms)


def p_totalBudget_factor(CEILVAL, totalBudget):
    r"""p_totalBudget(MS, SIMY) as the scaling factor: the SAPS budget (DPMTR's ceiling, million EUR) over the Agenda
    2000 budget (EUR 1000).

    CAPRI's GAMS (policy/calc_mtr_top.gms l. 174-175):

                  p_totalBudget(MS,SIMY) $ (p_totalBudget(MS,SIMY) gt eps)
                       = p_premDataE(MS,SIMY,"DPMTR","CEILVAL")/(p_totalBudget(MS,SIMY)*0.001);

    Departures from CAPRI: none."""
    return CEILVAL / (totalBudget * 0.001)


def p_premDataE_DpAgEU10(value, totalBudget):
    r"""p_premDataE(MS, SIMY, DpAgEU10, "CeilVal"), or its group rates above EPS where it has no ceiling value: scaled
    by the factor so that the Agenda 2000 schemes exhaust the SAPS budget.

    CAPRI's GAMS (policy/calc_mtr_top.gms l. 179-186):

                  p_premDataE(MS,SIMY,DpAgEU10,"CeilVal") $ p_totalBudget(MS,SIMY)
                       = p_premDataE(MS,SIMY,DpAgEU10,"CeilVal") * p_totalBudget(MS,SIMY);
        *

                  p_premDataE(MS,SIMY,DpAgEU10,PSGROUP)  $ ((NOT p_premDataE(MS,SIMY,DpAgEU10,"CeilVal"))
                                                                   and p_totalBudget(MS,SIMY)
                                                                   and (p_premDataE(MS,SIMY,DpAgEU10,PSGROUP) gt eps))
                                                           = p_premDataE(MS,SIMY,DpAgEU10,PSGROUP) * p_totalBudget(MS,SIMY);

    Departures from CAPRI: none (a value written EPS or NA kept, NA's factor NA, by the caller)."""
    return value * totalBudget


def DATA_column(item, ms_eu10_or_bur):
    r"""DATA(RU, MPACT, item, "Y") for the base year's payments: the column of the base data the item is taken from: the
    levels at BAS (at TRD for the EU-10's and BUR's units), the yields and the young animals' inputs at BAS, the
    historical yields at the year (Y).

    CAPRI's GAMS (policy/calc_mtr_top.gms l. 188-201):

                   DATA(RU,MPACT,"LEVL","Y") = DATA(RU,MPACT,"LEVL","%1");
        ***end redundant section
        *
        *          --- make a copy of the current output and young animal input coefficients.
        *              They are replaced by the base values during the following call to prmcut
        *
                   DATA(RU,MPACT,O,"CUR")     $ PACT_TO_Y(MPACT,O)      = DATA(RU,MPACT,O,"Y");
                   DATA(RU,MAACT,IYANI,"CUR") $ PACT_TO_I(MAACT,IYANI)  = DATA(RU,MAACT,IYANI,"Y");

                   DATA(RU,MPACT,O,"Y")       $ PACT_TO_Y(MPACT,O)      = DATA(RU,MPACT,O,"%1");
                   DATA(RU,MAACT,IYANI,"Y")   $ PACT_TO_I(MAACT,IYANI)  = DATA(RU,MAACT,IYANI,"%1");

                   DATA(RU,MPACT,"LEVL","Y") $  SUM(MAP_RR(MS,RU) $ ( MAP_RR("EU010000",MS) OR MAP_RR("BUR",MS)),1)
                                                                        = DATA(RU,MPACT,"LEVL","TRD");

    (%1 is BAS.) Departures from CAPRI: the base data's columns read from mtr_base_data.csv (tools/build/
    build_mtr_inputs.py); the historical yields (HSTY) at Y, not replaced (they are not outputs)."""
    if item == "LEVL":
        return "TRD" if ms_eu10_or_bur else "BAS"
    if item in ("YILD", "SLGT"):
        return "BAS"
    if item == "HSTY":
        return "Y"
    return None


def p_premDataE_MODU(PRME, percAffByModulation):
    r"""p_premDataE(RS, SIMY, PSDPAY, "MODU"): the money modulated from a scheme, million EUR: its payments x the sum
    of its producer groups' (PSGG_TO_P) total shares subject to modulation in the member state x 0.01.

    CAPRI's GAMS (policy/calc_mtr_top.gms l. 220-222):

                 p_premDataE(RS,SIMY,PSDPAY,"MODU")
                         = sum(PSGG_TO_P(PSGG,PSDPAY),
                                                      p_premPaym(RS,"Total",PSDPAY,"PRME")*sum(MAP_RR(MS,RS), p_percAffByModulation(PSGG,"TOT",MS))*0.01);

    In this project's notation: M_s = P_s (sum_g share_g) 0.01. Departures from CAPRI: the payments factored out of
    the sum over the groups (the same value up to rounding); per member state (CAPRI's RS, BL400000 with its own
    shares, l. 224-226, a NUTS 1 region the model does not run)."""
    return PRME * sum(percAffByModulation) * 0.01
