"""CAPRI's fertiliser options' parameters as envind/ghgMiti.gms sets them (CAPRI star 3.0): the restriction of the
inhibitor on manure's efficiency gain by the over-fertilisation (restMitFert), the shadow value of manure N that its
calibration uses, and the options' linear calibration term beta (pmpParlin) in this model's form (DEP-30).

Used by capri_mod/supply/abatement.py (_manure_inhibitor_params) and capri_mod/supply/capri_regional_nlp.py
(CapriRegionalNLP.calibrate).
"""
from __future__ import annotations


def othImpact_NMAN_restMitFert(NMAN, v_cropNutNeedMultFact, p_OverFertMarkUp, v_nutAvailFactExcr, p_fertEffCor):
    r"""p_ghgMiti(ru, cropMiti, Nitr_Inh, othImpact, NMAN) after the over-fertilisation restriction (restMitFert on, as
    in CAPRI's Green Deal runs): the inhibitor on manure cannot bring the manure N's contribution above the crops'
    need.

    CAPRI's GAMS (envind/ghgMiti.gms l. 531-543):

      p_ghgMiti(ru,"cropMiti","Nitr_Inh","othImpact","NMAN")
      $ ((v_cropNutNeedMultFact.l(ru,"NITF","T") + p_OverFertMarkUp) <= v_nutAvailFactExcr.l(ru,"mann")) = 0;

      p_ghgMiti(ru,"cropMiti","Nitr_Inh","othImpact","NMAN")
      $ ( v_nutAvailFactExcr.l(ru,"mann")
        $ (  (v_cropNutNeedMultFact.l(ru,"NITF","T") + p_OverFertMarkUp) > v_nutAvailFactExcr.l(ru,"mann"))
        $ (  (v_cropNutNeedMultFact.l(ru,"NITF","T") + p_OverFertMarkUp)
    *     othImpact=(NOC.QEmit/nitr_inh.QEmit-1)**fertEffCor<=>othImpact**(1/ferEffCor)+1=NOC.QEmit/nitr_inh.QEmit
           < (p_ghgMiti(ru,"cropMiti","Nitr_Inh","othImpact","NMAN") ** (1/p_fertEffCor) + 1)
           * v_nutAvailFactExcr.l(ru,"mann") )
        )
        = ((v_cropNutNeedMultFact.l(ru,"NITF","T") + p_OverFertMarkUp) / v_nutAvailFactExcr.l(ru,"mann") -1) ** p_fertEffCor;

    In this project's notation, x the over-fertilisation factor, m the mark-up, a the availability of excreted manure N
    (CAPRI's v_nutAvailFactExcr at the calibration point, npk_region_2030.csv excr_avail), e = p_fertEffCor:

        NMAN' = 0                         if x + m <= a
                ((x + m) / a - 1) ** e    if a < x + m < (NMAN ** (1/e) + 1) a
                NMAN                      otherwise

    Departures from CAPRI: none. (Until 21 November 2026 the model took a as its marginal manure substitution,
    (availability + slope x manure per ha) / mineral efficiency, instead of CAPRI's v_nutAvailFactExcr.)
    """
    cap = v_cropNutNeedMultFact + p_OverFertMarkUp
    a = v_nutAvailFactExcr
    if cap <= a:
        return 0.0
    if a and cap < (NMAN ** (1.0 / p_fertEffCor) + 1.0) * a:
        return (cap / a - 1.0) ** p_fertEffCor
    return NMAN


def p_manureShadVal(UVAG_NITF, v_nutAvailFactExcr):
    r"""p_manureShadVal(rs): the value of a t of excreted manure N, the member state's unit value of mineral N in the
    simulation year x the region's availability of excreted manure N; the price of the N the inhibitor on manure
    saves in CAPRI's calibration of its cost function (pmpParsqr, pmpParlin, l. 1029-1071).

    CAPRI's GAMS (envind/ghgMiti.gms l. 870-877; the two branches are the same statement):

      $iftheni %ghgTechCali% == ini
        p_manureShadVal(rs) = sum(map_rr(nuts0,rs),data(NUTS0,"UVAG","NITF","Y") * v_nutAvailFactExcr.l(rs,"mann"));
      $else
        p_manureShadVal(rs) = sum(map_rr(nuts0,rs),data(NUTS0,"UVAG","NITF","Y") * v_nutAvailFactExcr.l(rs,"mann"));
      $endif

    In this project's notation: psv = p_m a, p_m the member state's UVAG of NITF (npk_region_2030.csv uvag_eur_t, the
    model's money), a as in othImpact_NMAN_restMitFert. Departures from CAPRI: none."""
    return UVAG_NITF * v_nutAvailFactExcr


def pmpParlin_fertTech_DEP30(relSubs0_costParLin, foc_residual_per_unit, cal_relsubs0=True):
    r"""The fertiliser option's linear calibration term (beta, CAPRI's pmpParlin) in this model's form (DEP-30): the
    increment to the option's linear cost that makes its first-order condition at the initial share (0 for every
    fertiliser option) what CAPRI's derivation states, with the saving valued by the regional model's own marginal
    value of N instead of CAPRI's notional one.

    CAPRI's derivation (envind/ghgMiti.gms l. 725-731, the FOC of min C(m) N with a hypothetical subsidy):

      *     FOC:  dC(mi)/d(mi)*N+C(mi)*dN(mi)/d(mi)
      *         = {dC(mi)/d(mi)-C(mi)*E(mi)^-1*dE(mi)/d(mi)}*N=0
      *     As in PW 2014 relsubsi is hypothetically chosen such that mi is optimal for i=0 or i=1.
      *     Relsubs0 is nonzero only if m0=0 (assumed always true for fertiliser measures)

    and its solution for beta (l. 1048-1056, the 'alternative approach' CAPRI's runs use, with the costParLin and
    pmpParlin corrections of l. 1089-1118 that leave their sum unchanged):

      p_ghgMiti(rs,pact,fertTechNoSD,"N2OSYN","pmpParlin")
              $ (p_ghgMiti(rs,pact,fertTechNoSD,"N2OSYN","costParLin") and mitiTech_map(rs,pact,fertTechNoSD,"N2OSYN")
                and (1 + (p_ghgMiti(rs,pact,fertTechNoSD,"othImpact","NMIN") + p_ghgMiti(rs,pact,fertTechNoSD,"othImpact","EmiCalmin"))
                * p_ghgMiti(rs,pact,fertTechNoSD,"N2OSYN","Inishare"))**(-2))
        = p_ghgMiti(rs,pact,fertTechNoSD,"N2OSYN","costParLin") * [p_ghgMiti(rs,pact,fertTechNoSD,"N2OSYN","relSubs0")-1]
          - p_ghgMiti(rs,pact,fertTechNoSD,"N2OSYN","pmpParsqr") * p_ghgMiti(rs,pact,fertTechNoSD,"N2OSYN","Inishare")
          + (p_ghgMiti(rs,pact,fertTechNoSD,"othImpact","NMIN") + p_ghgMiti(rs,pact,fertTechNoSD,"othImpact","EmiCalmin"))
                * sum(map_rr(ms,rs),data(ms,"UVAG","NITF","Y"))
          * (1 + (p_ghgMiti(rs,pact,fertTechNoSD,"othImpact","NMIN") + p_ghgMiti(rs,pact,fertTechNoSD,"othImpact","EmiCalmin"))
                * p_ghgMiti(rs,pact,fertTechNoSD,"N2OSYN","Inishare"))**(-2)
      ;

    (the inhibitor on manure's, l. 1061-1071, the same with NMAN and p_manureShadVal). At IniShare 0 the option's linear
    cost costParLin + pmpParlin is relSubs0 costParLin + nmE p: its first-order condition at zero, with the saving at
    the notional value nmE p, is + relSubs0 costParLin, the subsidy CAPRI's early adopters need (l. 900-906:
    "some subsidy (20%) is needed to get a few early adopters to consider adoption").

    In this project's notation, for an option o with cost c1_o s + ... per unit of its base (the N purchases; for the
    inhibitor on manure the manure N pool) and the regional NLP's first-order residual at the base point, r_o / den_o
    = c1_o - V_o (V_o the model's own marginal value of the saving per unit, CapriRegionalNLP.calibrate):

        beta_o = relSubs0_o costParLin_o - r_o / den_o      (cal_relsubs0: c1_o + beta_o - V_o = relSubs0_o costParLin_o)
        beta_o = - r_o / den_o, where the option would leave zero (r_o < 0); 0 otherwise    (not cal_relsubs0)

    relSubs0_costParLin: the option's own relSubs0 x costParLin, the linear cost it is built with (_fert_techs' S0,
    _manure_inhibitor_params' S0), so that c1_o + beta_o = relSubs0 costParLin + V_o, CAPRI's relSubs0 costParLin +
    nmE p with the model's own value of the saving.

    Departures from CAPRI: DEP-30 (the project lead's decision of 31 October 2026), the saving at the model's own
    marginal value of N, not CAPRI's notional nmE p. cal_relsubs0 False is the form before 21 November 2026 (setting
    supply.fert_option_cal_relsubs0): the first-order condition made zero at the initial share, without CAPRI's
    relSubs0 costParLin, so the options moved off zero at any rise of the value of N where CAPRI's need it to exceed
    that subsidy (KNOWN_ISSUES K196).
    Returns the increment, or None where the option is left as it is."""
    if cal_relsubs0:
        return relSubs0_costParLin - foc_residual_per_unit
    if foc_residual_per_unit >= 0:
        return None
    return -foc_residual_per_unit
