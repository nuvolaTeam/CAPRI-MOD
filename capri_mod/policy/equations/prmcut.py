r"""CAPRI's premium cut (policy/prmcut.gms, star 3.0): the entitlements, the paid quantity and value under each ceiling,
the cut factor, its passing down the regional levels, the premium modification factors' rescaling and the effective
premium PRME.

Each function computes one statement for one region and scheme (or one unit, activity and scheme);
capri_mod/policy/premium_cut.py (premiums) and capri_mod/policy/mtr.py (_rescaled_modif) loop over them. The farm
types (p_aggregNuts2) and the per-technology premiums (p_premiumsPerTechnology) are not ported: the technology
factor is an input, 0 without one.
"""
from __future__ import annotations

from capri_mod.policy.equations._gams import EPS


def p_premPaym_Entl(LEVL, entlWght):
    r"""p_premPaym(RU, PPPACT, PSDPAY, "Entl"): a unit's entitlements of a scheme, its level times the entitlement
    weight (the caller keeps the weights above EPS).

    CAPRI's GAMS (policy/prmcut.gms l. 66-67):

            p_premPaym(RU,PPPACT,PSDPAY,"Entl") $ (p_entlWght(RU,PPPACT,PSDPAY) gt eps)
                   = p_dataCopy(RU,PPPACT,"LEVL","Y") * p_entlWght(RU,PPPACT,PSDPAY);

    Departures from CAPRI: none."""
    return LEVL * entlWght


def p_premData_CEILACL(Entl):
    r"""p_premData(R, PSDPAY, "CEILACL"): the quantity under a region's ceiling, the sum of the entitlements of its
    units' activities with a declared premium (the caller's sequence; an EU aggregate adds its member states' sums).

    CAPRI's GAMS (policy/prmcut.gms l. 138-140):

            p_premData(MS,PSDPAY,"CEILACL") $ (p_premData(MS,PSDPAY,"CEILLEV") GT eps)
                =   sum((MAP_RR(MS,RU),PPPACT) $ p_premPaym(RU,PPPACT,PSDPAY,"PRMD"),
                               p_premPaym(RU,PPPACT,PSDPAY,"Entl") );

    and the same for the EU aggregates (l. 126-127, from the member states), NUTS 1 (l. 150-151) and NUTS 2 (l.
    162-163). Departures from CAPRI: computed for every region with a ceiling (CAPRI's only where CEILLEV is above
    EPS; the cut uses it only there); an aggregate's from its member states' units' entitlements."""
    q = 0.0
    for e in Entl:
        q += e
    return q


def p_premData_CEILACV(Entl, PRMD, technFactMod):
    r"""p_premData(R, PSDPAY, "CEILACV"): the value under a region's ceiling, million EUR: the sum of entitlements x
    PRMD x (1 + the technology factor) / 1000 (sequences in the same order).

    CAPRI's GAMS (policy/prmcut.gms l. 142-144):

            p_premData(MS,PSDPAY,"CEILACV") $ (p_premData(MS,PSDPAY,"CEILVAL") GT eps)
                =   sum((MAP_RR(MS,RU),PPPACT) $ p_premPaym(RU,PPPACT,PSDPAY,"PRMD"),
                         p_premPaym(RU,PPPACT,PSDPAY,"Entl") * p_premPaym(RU,PPPACT,PSDPAY,"PRMD") * (1.+p_technFactMod(RU,PPPACT,PSDPAY))) * 0.001;

    and the same for the EU aggregates (l. 132-134, at the member states' PRMD), NUTS 1 (l. 153-155) and NUTS 2 (l.
    165-167). Departures from CAPRI: the x 0.001 on each term (CAPRI's on the sum; the same value up to rounding);
    computed for every region with a ceiling."""
    v = 0.0
    for e, p, t in zip(Entl, PRMD, technFactMod):
        v += e * p * (1.0 + t) * 0.001
    return v


def _ratio(used, ceiling):
    return used / ceiling if isinstance(ceiling, (int, float)) and ceiling > 0 else 0.0


def p_premData_CEILCUT(CEILACL, CEILACV, CEILLEV=None, CEILVAL=None):
    r"""p_premData(RSEU, PSDPAY, "CEILCUT"): a region's cut factor, 1 / max(1, used / ceiling) over the ceilings above
    EPS; EPS where a ceiling is EPS; None where the region has no ceiling of the scheme.

    CAPRI's GAMS (policy/prmcut.gms l. 203-211):

            p_premData(RSEU,PSDPAY,"CEILCUT") = 0;

            p_premData(RSEU,PSDPAY,"CEILCUT") $ ( ((p_premData(RSEU,PSDPAY,"CEILLEV") GT eps) OR (p_premData(RSEU,PSDPAY,"CEILVAL") GT eps)) $ PSDPAY_T_R(RSEU,PSDPAY))
                = 1/MAX(1, MAX( (p_premData(RSEU,PSDPAY,"CEILACL") / p_premData(RSEU,PSDPAY,"CEILLEV")) $ (p_premData(RSEU,PSDPAY,"CEILLEV") gt eps)
                               ,(p_premData(RSEU,PSDPAY,"CEILACV") / p_premData(RSEU,PSDPAY,"CEILVAL")) $ (p_premData(RSEU,PSDPAY,"CEILVAL") gt eps)));
        *

            p_premData(RSEU,PSDPAY,"CEILCUT") $ ((    (p_premData(RSEU,PSDPAY,"CEILLEV") $ (p_premData(RSEU,PSDPAY,"CEILLEV") eq eps))
                                                   or (p_premData(RSEU,PSDPAY,"CEILVAL") $ (p_premData(RSEU,PSDPAY,"CEILVAL") eq eps)) ) $ PSDPAY_T_R(RSEU,PSDPAY)) = eps;

    In this project's notation: CUT = 1 / max(1, CEILACL / CEILLEV, CEILACV / CEILVAL). Departures from CAPRI: a region
    whose ceilings are both 0 (not EPS) has a cut of 1 here (CAPRI's 1 / max(1, 0, 0) too), and one with no ceiling
    record none (CAPRI's 0, which passes nothing down since the units then take the level above's)."""
    if CEILLEV == EPS or CEILVAL == EPS:
        return EPS
    if CEILLEV is None and CEILVAL is None:
        return None
    return 1.0 / max(1.0, _ratio(CEILACL, CEILLEV), _ratio(CEILACV, CEILVAL))


def p_premPaym_CUTT(CEILCUT, CEILCUT_above):
    r"""p_premPaym(RU, "CUTT", PSDPAY, "CEILCUT"): a unit's cut factor, its own, else that of the nearest level above it
    with one (NUTS 1, the member state, its EU aggregate: the caller's order, None where a level has none), else 1;
    EPS gives 0.

    CAPRI's GAMS (policy/prmcut.gms l. 219-269):

            p_premPaym(RSEU,"CUTT",PSDPAY,"CEILCUT") $ PSDPAY_T_R(RSEU,PSDPAY)
             = p_premData(RSEU,PSDPAY,"CEILCUT") $ p_premData(RSEU,PSDPAY,"CEILCUT");

    then the member states from REGAGGP (l. 228-229), NUTS 1 from the member states (l. 238-240), NUTS 2 from NUTS 1
    (l. 248-250), each where it has none, the sum over its parents with one, and

            p_premPaym(RUNR,"CUTT",PSDPAY,"CEILCUT") $ ( (NOT p_premPaym(RUNR,"CUTT",PSDPAY,"CEILCUT"))   $ PSDPAY_T_R(RUNR,PSDPAY)) = 1;

            p_premPaym(RUNR,"CUTT",PSDPAY,"CEILCUT") $ ((p_premPaym(RUNR,"CUTT",PSDPAY,"CEILCUT") eq eps) $ PSDPAY_T_R(RUNR,PSDPAY))= 0;

    Departures from CAPRI: the nearest level's factor taken directly (CAPRI passes it down level by level, a sum over
    the level's parents: one parent each in the model's hierarchy, so the same value)."""
    k = CEILCUT
    if k is None:
        k = next((c for c in CEILCUT_above if c is not None), 1.0)
    return 0.0 if k == EPS else k


def p_premModifFact_Y(premModifFact, PRMD_L_w, PRMD_L_modif):
    r"""p_premModifFact(RUNR, "Y", PPPACT, PSDPAY): a premium modification factor rescaled so that the scheme pays per
    unit what the weights pay: the factor x sum PRMD L w / sum PRMD L modif over the scheme's activities with a PRMD
    (the caller's two sums; the caller keeps the factors where PRMD L modif is above EPS and the sum is nonzero).

    CAPRI's GAMS (policy/prmcut.gms l. 275-281):

            p_premModifFact(RUNR,"Y",PPPACT,PSDPAY) $ ( ((  p_premPaym(RUNR,PPPACT,PSDPAY,"PRMD")
                                                          * p_dataCopy(RUNR,PPPACT,"LEVL","Y")*p_premModifFact(RUNR,"Y",PPPACT,PSDPAY)) gt eps) $ PSDPAY_T_A(PPPACT,PSDPAY))
              = p_premModifFact(RUNR,"Y",PPPACT,PSDPAY) *
                 SUM(PPPACT1 $ p_premPaym(RUNR,PPPACT1,PSDPAY,"PRMD"),
                       p_premPaym(RUNR,PPPACT1,PSDPAY,"PRMD")*p_dataCopy(RUNR,PPPACT1,"LEVL","Y")*p_entlWght(RUNR,PPPACT1,PSDPAY))
               / SUM(PPPACT1 $ p_premPaym(RUNR,PPPACT1,PSDPAY,"PRMD"),
                       p_premPaym(RUNR,PPPACT1,PSDPAY,"PRMD")*p_dataCopy(RUNR,PPPACT1,"LEVL","Y")*p_premModifFact(RUNR,"Y",PPPACT1,PSDPAY));

    In this project's notation: m' = m sum_a PRMD_a L_a w_a / sum_a PRMD_a L_a m_a. Departures from CAPRI: none."""
    return premModifFact * PRMD_L_w / PRMD_L_modif


def p_premPaym_PRME(PRMD, CUTT, entlWght, premModifFact=None):
    r"""p_premPaym(RUNR, PPPACT, PSDPAY, "PRME"): the effective premium per unit of the activity, PRMD x the cut x the
    entitlement weight, or the premium modification factor where one is set (the caller keeps the activities with a
    level and a PRMD).

    CAPRI's GAMS (policy/prmcut.gms l. 289-292):

            p_premPaym(RUNR,PPPACT,PSDPAY,"PRME") $ ( (p_dataCopy(RUNR,PPPACT,"LEVL","Y") $ p_premPaym(RUNR,PPPACT,PSDPAY,"PRMD")) $ PSDPAY_T_A(PPPACT,PSDPAY))
               = p_premPaym(RUNR,PPPACT,PSDPAY,"PRMD") * p_premPaym(RUNR,"CUTT",PSDPAY,"CEILCUT")
                * (  p_entlWght(RUNR,PPPACT,PSDPAY)           $ (NOT p_premModifFact(RUNR,"Y",PPPACT,PSDPAY))
                   + p_premModifFact(RUNR,"Y",PPPACT,PSDPAY)  $  p_premModifFact(RUNR,"Y",PPPACT,PSDPAY));

    In this project's notation: PRME = PRMD x CUT x (m if m else w). Departures from CAPRI: none."""
    return PRMD * CUTT * (premModifFact or entlWght)


def DATA_PRME(PRME):
    r"""DATA(RUNR, PPPACT, "PRME", "Y"): an activity's effective premium over all schemes, the sum of its schemes'.

    CAPRI's GAMS (policy/prmcut.gms l. 297-298):

            DATA(RUNR,PPPACT,"PRME","Y") $ p_dataCopy(RUNR,PPPACT,"LEVL","Y")
               = sum(PSDPAY_T_R(RUNR,PSDPAY), p_premPaym(RUNR,PPPACT,PSDPAY,"PRME"));

    Departures from CAPRI: the per-technology premiums (l. 300-312, p_premiumsPerTechnology) not ported."""
    t = 0.0
    for v in PRME:
        t += v
    return t
