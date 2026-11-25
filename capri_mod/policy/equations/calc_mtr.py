r"""CAPRI's 2003 reform's budgets (policy/calc_mtr.gms, star 3.0): the member state's payments eligible for decoupling
and their modulation, the correction to the national ceiling, the budget of each decoupling target per unit and the
farm-specific schemes' declarations (DPFRMS, DPFRMF).

capri_mod/policy/mtr.py (decoupled_budgets, decoupled_declarations) loops over the member states, units, schemes and
targets and calls these. Not ported (they touch none of the BPS key's schemes): the coupled remainder's rescaling (l.
105-224), the agri-environment boost (l. 230-250), the EU flat rate (l. 324-358), the greening top-up (l. 584-646),
the endogenous cut's limits (l. 658-745) and the fallow-land variants (l. 765-813).
"""
from __future__ import annotations


def p_premPaym_TOTAL_DPMTR(values):
    r"""p_premPaym(MS, "TOTAL", "DPMTR", "PRME") and "MODU": the member state's payments of the schemes eligible for
    decoupling (PSDPAY_MTR_EL) and their modulation, the sums over the schemes (computed again after the modulation's
    scaling, l. 70-71).

    CAPRI's GAMS (policy/calc_mtr.gms l. 40-44):

            p_premPaym(MS,"TOTAL","DPMTR","PRME")
               = SUM(PSDPAY_MTR_EL, p_premPaym(MS,"TOTAL",PSDPAY_MTR_EL,"PRME"));

            p_premPaym(MS,"TOTAL","DPMTR","MODU")
               = SUM(PSDPAY_MTR_EL, p_premDataE(MS,SIMY,PSDPAY_MTR_EL,"MODU"));

    Departures from CAPRI: none."""
    return sum(values)


def p_nationalCeilCut(CEILVAL, PRME, MODU):
    r"""p_nationalCeilCut(MS, SIMY) with modulation: the relative correction of the modulation that makes the
    payments net of it meet the national ceiling; 0 without a ceiling, payments or modulation.

    CAPRI's GAMS (policy/calc_mtr.gms l. 49-60):

            p_nationalCeilCut(MS,SIMY) = 0;

            p_nationalCeilCut(MS,SIMY) $ (    p_premDataE(MS,SIMY,"DPMTR","CEILVAL")
                                              $ p_premPaym(MS,"TOTAL","DPMTR","PRME")
                                              $ p_premPaym(MS,"TOTAL","DPMTR","MODU"))
        *
        *       -- relate the error (= difference between net ceiling from legislation and calculated totals
        *          from past premium schemes minus total modulation)
        *          to total modulation = gives the necessary relative correction for modulation rates
        *
                = ((p_premPaym(MS,"TOTAL","DPMTR","PRME") - p_premPaym(MS,"TOTAL","DPMTR","MODU"))-p_premDataE(MS,SIMY,"DPMTR","CEILVAL"))
                  /p_premPaym(MS,"TOTAL","DPMTR","MODU");

    In this project's notation: cut = ((P - M) - C) / M. Departures from CAPRI: none."""
    if CEILVAL and PRME and MODU:
        return ((PRME - MODU) - CEILVAL) / MODU
    return 0.0


def p_premDataE_MODU_cut(MODU, nationalCeilCut):
    r"""p_premDataE(MS, SIMY, PSDPAY_MTR_EL, "MODU") scaled by the correction (at least to 0).

    CAPRI's GAMS (policy/calc_mtr.gms l. 65-66):

            p_premDataE(MS,SIMY,PSDPAY_MTR_EL,"MODU")
               = p_premDataE(MS,SIMY,PSDPAY_MTR_EL,"MODU") *  MAX(0,p_nationalCeilCut(MS,SIMY)+1);

    Departures from CAPRI: none."""
    return MODU * max(0.0, nationalCeilCut + 1)


def p_nationalCeilCut_noModu(CEILVAL, PRME, MODU):
    r"""p_nationalCeilCut(MS, SIMY) without modulation: the correction of the payment rates that meets the national
    ceiling directly; 0 otherwise.

    CAPRI's GAMS (policy/calc_mtr.gms l. 78-82):

            p_nationalCeilCut(MS,SIMY) = 0;
            p_nationalCeilCut(MS,SIMY) $ (    p_premDataE(MS,SIMY,"DPMTR","CEILVAL")
                                              $ p_premPaym(MS,"TOTAL","DPMTR","PRME")
                                              $ (NOT p_premPaym(MS,"TOTAL","DPMTR","MODU")) )
                = p_premDataE(MS,SIMY,"DPMTR","CEILVAL")/p_premPaym(MS,"TOTAL","DPMTR","PRME") - 1;

    In this project's notation: cut = C / P - 1. Departures from CAPRI: none."""
    return CEILVAL / PRME - 1 if (CEILVAL and PRME and not MODU) else 0.0


def p_DDPartialBudget(PRME, PRME_MS, MODU_MS, couplPercent, nationalCeilCut, premToDDTarget):
    r"""p_DDPartialBudget(RU, DDTARGET, SIMY): a unit's budget for a decoupling target, million EUR: over the schemes
    eligible for decoupling (sequences in the same order) its base payments x the member state's share left after
    the modulation x the decoupled share x (1 + the correction) x the scheme's share for the target; None where it is
    not above 0.

    CAPRI's GAMS (policy/calc_mtr.gms l. 259-280):

           p_DDPartialBudget(RU,DDTARGET,SIMY)

            = MAX(0,sum(PSDPAY_MTR_EL $ (p_premPaym(RU,"Total",PSDPAY_MTR_EL,"PRME") gt eps),

        *
        *                --- total payments in that scheme in the reference period
        *
                                p_premPaym(RU,"Total",PSDPAY_MTR_EL,"PRME")
        *
        *                --- times modulated premiums in relation to not modulated ones
        *
                                 * SUM(R_RAGG(RU,MS), (p_premPaym(MS,"TOTAL",PSDPAY_MTR_EL,"PRME")-p_premDataE(MS,SIMY,PSDPAY_MTR_EL,"MODU"))
                                                                                                  /p_premPaym(MS,"TOTAL",PSDPAY_MTR_EL,"PRME")

        *
        *                --- times the decoupling factor (1 minus the coupling factor)
        *
                                        *  (1 - p_couplPercent(PSDPAY_MTR_EL,SIMY,MS)/100 * (1.-p_dpGreeningShare(MS)) ) * (1+p_nationalCeilCut(MS,SIMY)))
        *
        *                --- times the distribution factors
        *
                                                     * p_premToDDTarget(RU,SIMY,PSDPay_MTR_EL,DDTARGET)/100));

    In this project's notation: B = sum_s P_rs (P_s - M_s) / P_s (1 - c_s / 100) (1 + cut) T_s / 100. Departures from
    CAPRI: the greening share 0 (policy_sets.gms kills p_dpGreeningShare in the chain), so its factor left out; the
    member state's schemes without payments skipped (CAPRI divides by them only where the unit has payments, which
    the member state then has too)."""
    b = 0.0
    for v, p, m, cp, t in zip(PRME, PRME_MS, MODU_MS, couplPercent, premToDDTarget):
        if v <= 0 or not p:
            continue
        b += (v * (p - m) / p * (1 - cp / 100) * (1 + nationalCeilCut) * t / 100)
    return b if b > 0 else None


def p_premDataE_DPFRMS_PGFRM(CeilVal, LEVL_PGREF):
    r"""p_premDataE(RU, SIMY, "DPFRMS", "PGFRM"): the farm-specific scheme's rate per ha, its budget (its ceiling, the
    target DDFRMS's budget, l. 298) x 1000 over the unit's base levels of the reference activities (PGREF; its ceiling
    level, l. 304-305, the caller's where the rate is set).

    CAPRI's GAMS (policy/calc_mtr.gms l. 298-305):

            p_premDataE(RU,SIMY,"DPFRMS","CeilVal") = p_DDPartialBudget(RU,"DDFRMS",SIMY);

            p_premDataE(RU,SIMY,"DPFRMS","PGFRM")  $ sum(MPACT $ PSG_TO_A("PGREF",MPACT), p_dataCopy(RU,MPACT,"LEVL","BAS"))
                                          = p_premDataE(RU,SIMY,"DPFRMS","CeilVal")*1000
                                          / sum(PSG_TO_A("PGREF",MPACT), p_dataCopy(RU,MPACT,"LEVL","BAS"));

            p_premDataE(RU,SIMY,"DPFRMS","CeilLev") $ p_premDataE(RU,SIMY,"DPFRMS","PGFRM")
                                          = sum(PSG_TO_A("PGREF",MPACT), p_dataCopy(RU,MPACT,"LEVL","BAS"));

    Departures from CAPRI: none."""
    return CeilVal * 1000 / LEVL_PGREF


def p_premDataE_DPFRMF_PGARAB(CeilVal, LEVL_land):
    r"""p_premDataE(RU, SIMY, "DPFRMF", "PGARAB") and "PGGRAS": the farm flat rate per ha of arable land and grass, its
    budget (the target DDFRMF's) x 1000 over the unit's base levels of CAPRI's crops in either group.

    CAPRI's GAMS (policy/calc_mtr.gms l. 310-316):

            p_premDataE(RU,SIMY,"DPFRMF","CeilVal") = p_DDPartialBudget(RU,"DDFRMF",SIMY);

            p_premDataE(RU,SIMY,"DPFRMF","PGARAB")  $ sum(MCACT $ (PSG_TO_A("PGARAB",MCACT) or PSG_TO_A("PGGRAS",MCACT)), p_dataCopy(RU,MCACT,"LEVL","BAS"))
                                          = p_premDataE(RU,SIMY,"DPFRMF","CeilVal")*1000
                                          / sum(MCACT $ (PSG_TO_A("PGARAB",MCACT) or PSG_TO_A("PGGRAS",MCACT)), p_dataCopy(RU,MCACT,"LEVL","BAS"));

            p_premDataE(RU,SIMY,"DPFRMF","PGGRAS")  = p_premDataE(RU,SIMY,"DPFRMF","PGARAB");

    Departures from CAPRI: none."""
    return CeilVal * 1000 / LEVL_land
