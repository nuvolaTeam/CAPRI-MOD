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
    marginal value of N, not CAPRI's notional nmE p. cal_relsubs0 False makes the first-order condition zero where the
    option would leave zero, without relSubs0 costParLin: the fertiliser options' form before 21 November 2026 (its
    setting supply.fert_option_cal_relsubs0 retired on 23 November 2026; the options moved off zero at any rise of the
    value of N where CAPRI's need it to exceed that subsidy, KNOWN_ISSUES K196), kept for the urea substitution, whose
    calibration in CAPRI has no saving of N (CapriRegionalNLP.calibrate).
    Returns the increment, or None where the option is left as it is."""
    if cal_relsubs0:
        return relSubs0_costParLin - foc_residual_per_unit
    if foc_residual_per_unit >= 0:
        return None
    return -foc_residual_per_unit


def p_ghgMiti_QEmitt_NITR_INH(QEmitt_NOC, factor):
    r"""p_ghgMiti(RALL, "cropMiti", "Nitr_Inh", "N2OSYN", "qemitt"): the nitrification inhibitor's emission factor, 0.9
    x that of no option (factor: NITR_INH_EMISSION_FACTOR); the inhibitor on manure (N2OMAN) the same (l. 115).

    CAPRI's GAMS (envind/ghgMiti.gms l. 110-111):

          p_ghgMiti(RALL,"cropMiti","Nitr_Inh","N2OSYN","qemitt") $ p_ghgMiti(RALL,"cropMiti","Nitr_Inh","N2OSYN","qemitt")
           = p_ghgMiti(RALL,"cropMiti","noc","N2OSYN","qemitt") * 0.9;

    Departures from CAPRI: none."""
    return factor * QEmitt_NOC


def p_ghgMiti_maxShare_N2OMAN(grazed, total):
    r"""p_ghgMiti(RALL, "cropMiti", "Nitr_Inh", "N2OMAN", "maxShare"): the inhibitor on manure's maximum share, 1 less
    the share of the manure N dropped on pasture (grazed and total: the animals' base manure N, grazed and all; 0
    without manure).

    CAPRI's GAMS (envind/ghgMiti.gms l. 117-121):

          p_ghgMiti(RALL,"cropMiti","Nitr_Inh","N2OMAN","maxShare")
                 $ sum((MAACT,R_RAGG(Rall,NUTS0)),data(RALL,MAACT,"LEVL","BAS") * data(RALL,MAACT,"MANN","BAS"))
               = 1
               - sum((MAACT,R_RAGG(Rall,NUTS0)),p_Nemidat(NUTS0,MAACT,"N","TypeShare","GRAZ") * data(RALL,MAACT,"LEVL","BAS") * data(RALL,MAACT,"MANN","BAS"))
               / sum((MAACT,R_RAGG(Rall,NUTS0)),data(RALL,MAACT,"LEVL","BAS") * data(RALL,MAACT,"MANN","BAS"));

    Departures from CAPRI: the grazing shares the ammonia data's (the caller's sums)."""
    return 1.0 - grazed / total if total > 0 else 0.0


def p_ghgMiti_relSubs(maxShare, is_nitr_inh, relSubs1, relSubs0, relSubs1_adopted):
    r"""(p_ghgMiti(rs, pact, fertTechNoSD, targFert, "relSubs1"), ..."relSubs0"): the subsidies (relative to costParLin)
    the late and the early adopters need: 1.2 and 0.2 (MITI_RELSUBS1, MITI_RELSUBS0), 0.8 and 0 where the option is
    partly adopted already (maxShare below 1; not the nitrification inhibitor: MITI_RELSUBS1_ADOPTED).

    CAPRI's GAMS (envind/ghgMiti.gms l. 885-898):

          p_ghgMiti(rs,pact,fertTechNoSD,targFert,"relSubs1")
                  $ (  (p_ghgMiti(rs,pact,fertTechNoSD,targFert,"costParLin") gt 0) and mitiTech_map(rs,pact,fertTechNoSD,targFert))
                  = (1.2 * %sensFac%)
                    ;

        *     -- if the overfertilisation factor is already at a sufficiently low level so that the maxshare is below 1, we
        *        assume only 80% of cost for full adoption (case 1) because the technology is already adopted
          p_ghgMiti(rs,pact,fertTechNoSD,targFert,"relSubs1")
                  $ (  (p_ghgMiti(rs,pact,fertTechNoSD,targFert,"costParLin") gt 0) and mitiTech_map(rs,pact,fertTechNoSD,targFert)
                     and (p_ghgMiti(rs,pact,fertTechNoSD,targFert,"maxShare") < 1)
                     and (not sameas(fertTechNoSD,"nitr_inh"))
                     and ((p_ghgMiti(rs,"cropMiti",fertTechNoSD,"othImpact","NMIN") and sameas(targFert,"n2osyn"))
                     or  (p_ghgMiti(rs,"cropMiti",fertTechNoSD,"othImpact","NMAN") and sameas(targFert,"n2oman"))))
                  = (0.8  * %sensFac%);

    and relSubs0 at l. 904-916 (0.2, and 0 in the same case). Departures from CAPRI: %sensFac% 1; the NMIN / NMAN
    conditions the caller's (an option with an effect)."""
    if maxShare < 1.0 and not is_nitr_inh:
        return relSubs1_adopted, 0.0
    return relSubs1, relSubs0


def p_ghgMiti_pmpParsqr(costParLin, relSubs1, relSubs0, MaxShare, IniShare):
    r"""p_ghgMiti(rs, pact, fertTechNoSD, "N2OSYN", "pmpParsqr"), its cost part: costParLin (relSubs1 - relSubs0) /
    (MaxShare - IniShare); the inhibitor on manure (N2OMAN, l. 1029-1045) the same. The fertiliser saving's part is
    p_ghgMiti_pmpParsqr_saving, added by the caller (supply.fert_slope_with_saving).

    CAPRI's GAMS (envind/ghgMiti.gms l. 1011-1027):

          p_ghgMiti(rs,pact,fertTechNoSD,"N2OSYN","pmpParsqr")
                  $ (p_ghgMiti(rs,pact,fertTechNoSD,"N2OSYN","costParLin") and mitiTech_map(rs,pact,fertTechNoSD,"N2OSYN")
                    and (p_ghgMiti(rs,pact,fertTechNoSD,"N2OSYN","Maxshare") - p_ghgMiti(rs,pact,fertTechNoSD,"N2OSYN","Inishare"))
                    and [(1 + (p_ghgMiti(rs,pact,fertTechNoSD,"othImpact","NMIN") + p_ghgMiti(rs,pact,fertTechNoSD,"othImpact","EmiCalmin"))
                         * p_ghgMiti(rs,pact,fertTechNoSD,"N2OSYN","Inishare"))**(-2)]
                    and [(1 + (p_ghgMiti(rs,pact,fertTechNoSD,"othImpact","NMIN") + p_ghgMiti(rs,pact,fertTechNoSD,"othImpact","EmiCalmin"))
                         * p_ghgMiti(rs,pact,fertTechNoSD,"N2OSYN","Maxshare"))**(-2)])
            =    [ (p_ghgMiti(rs,pact,fertTechNoSD,"othImpact","NMIN") + p_ghgMiti(rs,pact,fertTechNoSD,"othImpact","EmiCalmin"))
                    * sum(map_rr(ms,rs),data(ms,"UVAG","NITF","Y"))
                 * ((1 + (p_ghgMiti(rs,pact,fertTechNoSD,"othImpact","NMIN") + p_ghgMiti(rs,pact,fertTechNoSD,"othImpact","EmiCalmin"))
                    * p_ghgMiti(rs,pact,fertTechNoSD,"N2OSYN","Maxshare"))**(-2)
                 -  (1 + (p_ghgMiti(rs,pact,fertTechNoSD,"othImpact","NMIN") + p_ghgMiti(rs,pact,fertTechNoSD,"othImpact","EmiCalmin"))
                    * p_ghgMiti(rs,pact,fertTechNoSD,"N2OSYN","Inishare"))**(-2))
                 +  p_ghgMiti(rs,pact,fertTechNoSD,"N2OSYN","costParLin")
                 * (p_ghgMiti(rs,pact,fertTechNoSD,"N2OSYN","relSubs1")-p_ghgMiti(rs,pact,fertTechNoSD,"N2OSYN","relSubs0"))]
                 / (p_ghgMiti(rs,pact,fertTechNoSD,"N2OSYN","Maxshare") - p_ghgMiti(rs,pact,fertTechNoSD,"N2OSYN","Inishare"))
          ;

    In this project's notation: g = [s + k (r1 - r0)] / (m1 - m0) with s the saving term. Departures from CAPRI: the
    two terms each divided by (m1 - m0) (the same value up to rounding)."""
    return costParLin * (relSubs1 - relSubs0) / (MaxShare - IniShare)


def p_ghgMiti_pmpParsqr_saving(nmE, value, IniShare, MaxShare):
    r"""The fertiliser saving's part of p_ghgMiti(..., "pmpParsqr"): nmE x value x ((1 + nmE m1)^-2 - (1 + nmE m0)^-2)
    / (m1 - m0), the N saved valued at its price (mineral N: the member state's unit value of NITF; manure N:
    p_manureShadVal), nmE = NMIN + EmiCalmin (NMAN for manure, EmiCalman commented out in CAPRI); 0 where it is not
    defined (m1 <= m0, or 1 + nmE m <= 0, CAPRI's conditions).

    CAPRI's GAMS (envind/ghgMiti.gms l. 1029-1045):

          p_ghgMiti(rs,"cropMiti",fertTechNoSD,"N2OMAN","pmpParsqr")
                  $ (p_ghgMiti(rs,"cropMiti",fertTechNoSD,"N2OMAN","costParLin") and mitiTech_map(rs,"cropMiti",fertTechNoSD,"N2OMAN")
                    and (p_ghgMiti(rs,"cropMiti",fertTechNoSD,"N2OMAN","Maxshare") - p_ghgMiti(rs,"cropMiti",fertTechNoSD,"N2OMAN","Inishare"))
                    and [(1 + (p_ghgMiti(rs,"cropMiti",fertTechNoSD,"othImpact","NMAN") + p_ghgMiti(rs,"cropMiti",fertTechNoSD,"othImpact","EmiCalman"))
                     * p_ghgMiti(rs,"cropMiti",fertTechNoSD,"N2OMAN","Inishare"))**(-2)]
                    and [(1 + (p_ghgMiti(rs,"cropMiti",fertTechNoSD,"othImpact","NMAN") + p_ghgMiti(rs,"cropMiti",fertTechNoSD,"othImpact","EmiCalman"))
                     * p_ghgMiti(rs,"cropMiti",fertTechNoSD,"N2OMAN","Maxshare"))**(-2)])
            =    [ (p_ghgMiti(rs,"cropMiti",fertTechNoSD,"othImpact","NMAN") + p_ghgMiti(rs,"cropMiti",fertTechNoSD,"othImpact","EmiCalman"))
                    * p_manureShadVal(rs)
                 * ((1 + (p_ghgMiti(rs,"cropMiti",fertTechNoSD,"othImpact","NMAN") + p_ghgMiti(rs,"cropMiti",fertTechNoSD,"othImpact","EmiCalman"))
                     * p_ghgMiti(rs,"cropMiti",fertTechNoSD,"N2OMAN","Maxshare"))**(-2)
                 -  (1 + (p_ghgMiti(rs,"cropMiti",fertTechNoSD,"othImpact","NMAN") + p_ghgMiti(rs,"cropMiti",fertTechNoSD,"othImpact","EmiCalman"))
                     * p_ghgMiti(rs,"cropMiti",fertTechNoSD,"N2OMAN","Inishare"))**(-2))
                 +  p_ghgMiti(rs,"cropMiti",fertTechNoSD,"N2OMAN","costParLin")
                 * (p_ghgMiti(rs,"cropMiti",fertTechNoSD,"N2OMAN","relSubs1")-p_ghgMiti(rs,"cropMiti",fertTechNoSD,"N2OMAN","relSubs0"))]
                 / (p_ghgMiti(rs,"cropMiti",fertTechNoSD,"N2OMAN","Maxshare") - p_ghgMiti(rs,"cropMiti",fertTechNoSD,"N2OMAN","Inishare"))
          ;

    Departures from CAPRI: divided by (m1 - m0) on its own (p_ghgMiti_pmpParsqr's departure)."""
    m0, m1 = IniShare, MaxShare
    if not m1 > m0 or 1.0 + nmE * m0 <= 0 or 1.0 + nmE * m1 <= 0:
        return 0.0
    return nmE * value * ((1.0 + nmE * m1) ** -2 - (1.0 + nmE * m0) ** -2) / (m1 - m0)


def p_ghgMiti_othImpact_EmiCalmin(p_emiloss, othImpact, p_fertEffCor):
    r"""p_ghgMiti(rs, "cropMiti", allTechFert, "othImpact", "EmiCalmin"): a fertiliser option's effect on the mineral N
    losses, the base losses of NETF (NH3, NOx, N2O gastot, runoff: p_emiloss) x the option's side effects (NH3SYN,
    NOXSYN, N2OSYN, NO3SRUN: othImpact, None as 0), raised to p_fertEffCor with its sign; 0 where it is 0.

    CAPRI's GAMS (envind/ghgMiti.gms l. 933-942):

          p_ghgMiti(rs,"cropMiti",allTechFert,"othImpact","EmiCalmin") $ mitiTech_map(rs,"cropMiti",allTechFert,"N2OSYN")
                 = p_emiloss(rs,"netf","nh3","gastot") * p_ghgMiti(rs,"cropMiti",allTechFert,"othImpact","NH3SYN")
                 + p_emiloss(rs,"netf","nox","gastot") * p_ghgMiti(rs,"cropMiti",allTechFert,"othImpact","NOXSYN")
                 + p_emiloss(rs,"netf","n2o","gastot") * p_ghgMiti(rs,"cropMiti",allTechFert,"othImpact","N2OSYN")
                 + p_emiloss(rs,"netf","n","runtot") * p_ghgMiti(rs,"cropMiti",allTechFert,"othImpact","NO3SRUN");

          p_ghgMiti(rs,"cropMiti",allTechFert,"othImpact","EmiCalmin") $ (p_ghgMiti(rs,"cropMiti",allTechFert,"othImpact","EmiCalmin")>0)
                 = p_ghgMiti(rs,"cropMiti",allTechFert,"othImpact","EmiCalmin")**p_fertEffCor;
          p_ghgMiti(rs,"cropMiti",allTechFert,"othImpact","EmiCalmin") $ (p_ghgMiti(rs,"cropMiti",allTechFert,"othImpact","EmiCalmin")<0)
                 = abs(p_ghgMiti(rs,"cropMiti",allTechFert,"othImpact","EmiCalmin"))**p_fertEffCor * (-1);

    Departures from CAPRI: the losses the N loss cascade's (capri_mod/supply/n_cascade.py, its region's)."""
    v = None
    for loss, eff in zip(p_emiloss, othImpact):
        t = loss * (eff or 0.0)
        v = t if v is None else v + t
    return (abs(v) ** p_fertEffCor) * (1.0 if v >= 0 else -1.0) if v else 0.0


def p_ghgMiti_othImpact_mitisyn(litRev, NMIN, share):
    r"""The emission factor's multiplier on mineral N from an option's side effect on an emission (p_ghgMiti(rs,
    "cropMiti", allTechFert, "othImpact", mitisyn) = -[(1 - lit)(1 + NMIN) - 1]) at the option's share of the mineral N
    (share, w): 1 - w + w (1 - lit)(1 + NMIN).

    CAPRI's GAMS (envind/ghgMiti.gms l. 552-555):

        p_ghgMiti(rs,"cropMiti",allTechFert,"othImpact",mitisyn)
            $ (p_ghgMiti(rs,"CropMiti","NOC","N2OSYN","QEmitt") and p_ghgMiti(rs,"CropMiti",allTechFert,"N2OSYN","QEmitt")
               and p_litRevFertTechs(rs,allTechFert,"mineral","mineral",mitisyn))
            =    [(1-p_litRevFertTechs(rs,allTechFert,"mineral","mineral",mitisyn)) * (p_ghgMiti(rs,"cropMiti",allTechFert,"othImpact","NMIN")+1) -1] *(-1);

    In this project's notation: F = 1 - w + w (1 - lit)(1 + NMIN) = 1 - w othImpact. Departures from CAPRI: the
    multiplier of the accounts (capri_mod/environmental/nitrogen.py fert_side_factors), not the side effect itself;
    the manure's side effects (l. 557-565) the regional NLP's (abatement.py)."""
    return 1.0 - share + share * (1.0 - litRev) * (1.0 + NMIN)
