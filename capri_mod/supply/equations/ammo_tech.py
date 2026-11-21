"""CAPRI's urea substitution (UreaSubst, target NH3SYN) as envind/ammo_tech.gms sets it up (CAPRI star 3.0): the share of
the region's mineral N switched from urea to other fertilisers, its maximum share, its effect on the NH3 of mineral N,
its cost per t of N bought, and its calibration (the ammonia options' cases, l. 2840-2977, 3041-3047, 3100-3107).

Used by tools/build/build_urea_subst_option.py. The option's cost in CAPRI's objective is GHG_Mit_Cost_ on the mineral
N bought (supply/supply_model.gms l. 5062: - v_netPutQuant(NITF)): equations/supply_model/mitigation.py
GHG_Mit_Cost_ureaSubst.
"""
from __future__ import annotations


def MaxShare_UreaSubst(fracUseFert_Ureum):
    r"""p_ghgMiti(rs, cropMiti, UreaSubst, nh3syn, MaxShare): the member state's share of urea in its mineral N.

    CAPRI's GAMS (envind/ammo_tech.gms l. 2353-2354):

      p_ghgMiti(rs,"cropMiti","UreaSubst","nh3syn","IniShare") = 0;
      p_ghgMiti(rs,"cropMiti","UreaSubst","nh3syn","MaxShare") = sum(map_rr(nuts0,rs), p_fracUseFert(nuts0,"Ureum"));

    Departures from CAPRI: none (IniShare 0)."""
    return float(fracUseFert_Ureum)


def othImpact_NH3SYN_UreaSubst(emFracFert_NH3_Ureum, emFracFert_NH3_Other):
    r"""p_ghgMiti(rs, cropMiti, UreaSubst, othImpact, nh3syn): the NH3 emission factor of urea less that of the other
    mineral fertilisers, the option's term in GASTOTNETF_ (supply/supply_model.gms l. 3368-3377).

    CAPRI's GAMS (envind/ammo_tech.gms l. 2358-2361):

      p_ghgMiti(rs,"cropMiti","UreaSubst","nh3syn","qemitt")
         = sum(map_rr(nuts0,rs) $ p_emFracFert(nuts0,"NH3","Ureum"),p_emFracFert(nuts0,"NH3","Other") / p_emFracFert(nuts0,"NH3","Ureum"));
      p_ghgMiti(rs,"cropMiti","UreaSubst","othImpact","nh3syn")
         = sum(map_rr(nuts0,rs),p_emFracFert(nuts0,"NH3","Ureum") - p_emFracFert(nuts0,"NH3","Other"));

    Departures from CAPRI: none."""
    return float(emFracFert_NH3_Ureum) - float(emFracFert_NH3_Other)


def costParLin_UreaSubst(UVAG_NITF_BAS, fracUseFert_Ureum, fracUseFert_Other, p_infl, years_BAS_2007):
    r"""p_ghgMiti(rs, cropMiti, UreaSubst, nh3syn, costParLin): EUR per t of N switched, the price of the other mineral
    fertilisers less urea's (Reis et al. 2015: urea 289 EUR per t of urea in 2007, x 60/28 per t of N, inflated to the
    base year).

    CAPRI's GAMS (envind/ammo_tech.gms l. 2372-2375):

      p_ghgMiti(rs,"cropMiti","UreaSubst","nh3syn","costParLin")
         = sum(map_rr(nuts0,rs) $ p_fracUseFert(nuts0,"Other"),[data(NUTS0,"UVAG","NITF","BAS")
           - 289 * 60 / 28 * p_infl**(CALYEA("BAS")-CALYEA("2007")) * (p_fracUseFert(nuts0,"Ureum") + p_fracUseFert(nuts0,"Other"))]
           / p_fracUseFert(nuts0,"Other"));

    In this project's notation, p the member state's unit value of mineral N in the base year, u and o the shares of urea
    and the other fertilisers, i CAPRI's inflation: k = [p - 289 x 60/28 x i^(BAS - 2007) x (u + o)] / o.
    Departures from CAPRI: none here. (CAPRI does not inflate this cost to the simulation year: ammo_tech.gms l. 3355-3358
    inflates the animals' options only, and ghgMiti.gms's inflation, l. 155-158, runs before ammo_tech.gms; the builder
    keeps it so.)"""
    if not fracUseFert_Other:
        return 0.0
    return (float(UVAG_NITF_BAS) - 289.0 * 60.0 / 28.0 * float(p_infl) ** int(years_BAS_2007)
            * (float(fracUseFert_Ureum) + float(fracUseFert_Other))) / float(fracUseFert_Other)


def relSubs_ammTech(costParLin, revenue, IniShare, MaxIncrease, sensFac=1.0):
    r"""(relSubs0, relSubs1, case) of an ammonia option (envind/ammo_tech.gms l. 2863-2945; mitiTechAmm, UreaSubst among
    them).

    CAPRI's GAMS (envind/ammo_tech.gms l. 2863-2945):

      *     -- case 1: unit cost and observed shares are positive (without revenues)
        p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"relSubs1")
                $ (  (    (p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"costParLin") gt 0)
                      and (p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"revenue") eq 0)   )
                   $ (p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"IniShare") gt 0)
                   $ mitiTech_map(rs,pact,mitiTechAmm,targAmm) )
                 = 0.8
       * %sensFac%
                 * p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"MaxIncrease")
                 ;
      *     -- case 2: unit cost is negative or we have revenues and observed share is positive, but < MaxShare
        p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"relSubs1")
                $ (  (    (p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"costParLin") lt 0)
                       or (p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"revenue") gt 0)     )
                   $ (p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"IniShare") gt 0)
                   $ mitiTech_map(rs,pact,mitiTechAmm,targAmm) )
                 = (-0.2 $ (p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"costParLin") lt 0)
                    +0.2 $ ((p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"revenue")
                            *p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"costParLin")) gt 0) )
                 * %sensFac%
                 * p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"MaxIncrease")
                 ;
      *     -- case 3: unit cost is positive and observed share is zero
        p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"relSubs1")
                $ (  ((p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"costParLin")) gt 0)
                   $ (p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"IniShare") eq 0)
                  $ mitiTech_map(rs,pact,mitiTechAmm,targAmm) )        = 1.2 * %sensFac%
                  ;
        p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"relSubs0")
                $ (  ((p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"costParLin")) gt 0)
                   $ (p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"IniShare") eq 0)
                   $ mitiTech_map(rs,pact,mitiTechAmm,targAmm) )        = 0.2 * %sensFac%;
      *     -- case 4: unit cost is negative or we have revenues, but observed share is nonetheless zero
        p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"relSubs1")
                $ (  (    (p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"costParLin") lt 0)
                       or (p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"revenue") gt 0)     )
                   $ (p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"IniShare") eq 0)
                   $ mitiTech_map(rs,pact,mitiTechAmm,targAmm) )
                 = (-0.5 $ (p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"costParLin") lt 0)
                    +0.5 $ ((p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"revenue")
                            *p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"costParLin")) gt 0) )
                 * %sensFac%
                            ;
        p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"relSubs0")
                $ (  (    (p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"costParLin") lt 0)
                       or (p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"revenue") gt 0)     )
                   $ (p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"IniShare") eq 0)
                   $ mitiTech_map(rs,pact,mitiTechAmm,targAmm) )
                 = (-0.1 $ (p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"costParLin") lt 0)
                    +0.1 $ ((p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"revenue")
                            *p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"costParLin")) gt 0) )
                 * %sensFac%
                            ;

    The statements run in this order (a later one overwrites an earlier one where both conditions hold).
    Returns (relSubs0, relSubs1, case), 0 / 0 / None where no case applies. Departures from CAPRI: none."""
    k, rv = float(costParLin), float(revenue)
    r0 = r1 = 0.0
    case = None
    if k > 0 and rv == 0 and IniShare > 0:
        r1 = 0.8 * sensFac * MaxIncrease; case = 1
    if (k < 0 or rv > 0) and IniShare > 0:
        r1 = ((-0.2 if k < 0 else 0.0) + (0.2 if rv * k > 0 else 0.0)) * sensFac * MaxIncrease; case = 2
    if k > 0 and IniShare == 0:
        r1 = 1.2 * sensFac; r0 = 0.2 * sensFac; case = 3
    if (k < 0 or rv > 0) and IniShare == 0:
        r1 = ((-0.5 if k < 0 else 0.0) + (0.5 if rv * k > 0 else 0.0)) * sensFac
        r0 = ((-0.1 if k < 0 else 0.0) + (0.1 if rv * k > 0 else 0.0)) * sensFac
        case = 4
    return r0, r1, case


def Subs_ammTech(relSubs, costParLin):
    r"""Subs0 or Subs1 of an ammonia option: the relative subsidy times costParLin.

    CAPRI's GAMS (envind/ammo_tech.gms l. 2949-2950, 2976-2977):

        p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"Subs0")
        = p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"relSubs0")* p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"costParLin");
        ...
        p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"Subs1")
        = p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"relSubs1") * p_ghgMiti(rs,pact,mitiTechAmm,targAmm,"costParLin");

    Departures from CAPRI: none (premCapMitTech off: the RDP premiums of l. 2954-2971 do not apply)."""
    return float(relSubs) * float(costParLin)


def pmpParsqr_UreaSubst(Subs0, Subs1, MaxShare, IniShare, costParSqr=0.0):
    r"""gamma = pmpParsqr of the urea substitution (l. 3041-3047).

    CAPRI's GAMS (envind/ammo_tech.gms l. 3041-3047):

      p_ghgMiti(rs,"cropMiti","UreaSubst",targAmm,"pmpParsqr")
              $ (mitiTech_map(rs,"cropMiti","UreaSubst",targAmm) and (NOT p_ghgMiti(rs,"cropMiti","UreaSubst",targAmm,"costParsqr"))
              and (NOT p_ghgMiti(rs,"cropMiti","UreaSubst",targAmm,"pmpParsqr"))
              and (p_ghgMiti(rs,"cropMiti","UreaSubst",targAmm,"MaxShare")-p_ghgMiti(rs,"cropMiti","UreaSubst",targAmm,"IniShare")))
        = (p_ghgMiti(rs,"cropMiti","UreaSubst",targAmm,"Subs1") - p_ghgMiti(rs,"cropMiti","UreaSubst",targAmm,"Subs0"))
        / (p_ghgMiti(rs,"cropMiti","UreaSubst",targAmm,"MaxShare")-p_ghgMiti(rs,"cropMiti","UreaSubst",targAmm,"IniShare"))
        -  p_ghgMiti(rs,"cropMiti","UreaSubst",targAmm,"costParsqr")
      ;

    Departures from CAPRI: none."""
    d = float(MaxShare) - float(IniShare)
    return (float(Subs1) - float(Subs0)) / d - float(costParSqr) if d else 0.0


def pmpParlin_UreaSubst(revenue, costParLin, Subs0, pmpParSqr, IniShare, costParSqr=0.0):
    r"""beta = pmpParlin of the urea substitution (l. 3100-3107): the first-order condition at the initial share with the
    subsidy Subs0.

    CAPRI's GAMS (envind/ammo_tech.gms l. 3100-3107):

      p_ghgMiti(rs,"cropMiti","UreaSubst",targAmm,"pmpParlin")
              $ (mitiTech_map(rs,"cropMiti","UreaSubst",targAmm) and (NOT p_ghgMiti(rs,"cropMiti","UreaSubst",targAmm,"pmpParlin")))
        =  p_ghgMiti(rs,"cropMiti","UreaSubst",targAmm,"revenue")
         - p_ghgMiti(rs,"cropMiti","UreaSubst",targAmm,"costParLin")
         + p_ghgMiti(rs,"cropMiti","UreaSubst",targAmm,"Subs0")
         - ( p_ghgMiti(rs,"cropMiti","UreaSubst",targAmm,"costParSqr")
           + p_ghgMiti(rs,"cropMiti","UreaSubst",targAmm,"pmpParSqr"))
         * p_ghgMiti(rs,"cropMiti","UreaSubst",targAmm,"iniShare")
      ;

    Departures from CAPRI: none here. In the regional model the linear term is calibrated again at the base with the
    model's own marginal value of the share (CapriRegionalNLP.calibrate, DEP-30's rule: the first-order condition at the
    initial share Subs0), as CAPRI's ammonia options are with costsavings0 (l. 3366-3379; not applied to UreaSubst there,
    whose saving of N CAPRI's notional calibration leaves out)."""
    return float(revenue) - float(costParLin) + float(Subs0) - (float(costParSqr) + float(pmpParSqr)) * float(IniShare)
