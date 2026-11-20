r"""CAPRI's objective (supply/supply_model.gms l. 4616-4983 and 5358-5433): LINEAR_, the linear part of the regional
objective, v_linObjePart.

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026); this docstring keeps the block's overview, notation and departures.

Written so far: the fertilisation block's terms on the mineral N purchases v_netPutQuant(NITF) (the regional NLP's
fertilisation block, CapriRegionalNLP._fert_block): their value at the unit value (UVAG) and the emission tax on
mineral N's soil N2O, with the indirect N2O of the purchases' runoff and leaching at the same tax; the emission
tax's terms of the mitigation options (CapriRegionalNLP._abatement_block); the feeds' PMP terms, QUADRF_ with
QUADRF1_ (CapriRegionalNLP.__init__'s objective); the activities' net revenues (LINEAR_netRevenue,
supply_module._compute_net_revenues), the PMP terms of the activity levels (QUADRA_ with GRPLEVL_) and the objective's
composition (OBJEQF_).

Not written: labCap_ (l. 4808-4810), v_labCap, the PMP terms' sum, which enters OBJEQF_ only through its scale
v_labCap.scale (set only in sens/sens.gms, l. 103 and 309; 1 in the Green Deal step) and through the conditions
v_labCap.lo ne v_labCap.up (true: v_labCap is free, p_fixLabCapViaPMP = 0, capmod.gms l. 531). fixTechfShares_ (l. 4813-4817) is empty in the step: its
p_fixTechfShares is set only in sens/sens.gms (l. 151, 305).

In this project's notation (per nutrient; P = the purchases, t, CAPRI's - v_netPutQuant; the objective in kEUR; uvag
the unit value per kg, here per t / 1000):

    LINEAR_netPutQuant     uvag x P
    LINEAR_carbonTaxNITF   [ (N2O + (NH3 + NOx) EF4) x 44/28 x GWP(N2O) x tax ] x P        (N only)
    LINEAR_carbonTaxN2OLEA [ the indirect N2O of the purchases' runoff and leaching x 44/28 x GWP x tax ] x P

The tax factors per t are the build's (supply.fertilisation, spec "ghg_min": d the direct N2O, v the volatilised N's
indirect N2O, l the runoff's and leaching's (CAPRI's GWPN2OLEA_; SupplyModel._ef_mineral_lea)).

Departures from CAPRI: CAPRI's v_emiLoss(NETF, N2O, GasTot) moves with the fertiliser options (GASTOTNETF_); the model
takes the accounts' factor on the share w of mineral N under the nitrification inhibitor, 1 - w + w (1 - lit)(1 + NMIN)
(EnvironmentalModule.fert_side_factors), added to the base factor as w (d_nitr + v_nitr); the leaching term is priced
on the purchases at CAPRI's Green Deal reference leaching share (REGISTERED: SupplyModel._ef_mineral_lea).
"""
from __future__ import annotations


def LINEAR_netPutQuant(v_netPutQuant, uvag):
    """The purchases valued at their unit value (LINEAR_, l. 4635-4643): uvag x P, kEUR (uvag per t / 1000).

    CAPRI's GAMS, LINEAR_ (l. 4635-4643, the purchases valued by their unit value; the other terms left out here):

        LINEAR_(RUNR)..    v_linObjePart(RUNR)  =E=
            SUM(  RUNR_OMOBJE(RUNR,OM_OBJE),
                  v_netPutQuant(RUNR,OM_OBJE) * ( SUM(R_RAGG(RUNR,MSACT), (%data%(MSACT,"UVAG",OM_OBJE,"Y") $ (not p_useUvagScen) + (p_uvagScen(MSACT,OM_OBJE) $ p_useUvagScen) ))
                                                + (p_fnutuvag(RUNR,OM_OBJE) $ (p_useInputPScen $ sum(FNUT$sameas(OM_OBJE,FNUT),1)))    ))
    """
    return uvag * v_netPutQuant


def LINEAR_carbonTaxNITF(v_netPutQuant, ef_dv, w=None, ef_d_nitr=None, ef_v_nitr=None):
    """The emission tax on mineral N's soil N2O (LINEAR_, l. 4686-4692): fac x P, fac = ef_dv (the direct and the
    volatilised N's indirect N2O x GWP x tax per t) [+ w (ef_d_nitr + ef_v_nitr): the nitrification inhibitor's change
    on the share w of mineral N under it].

    CAPRI's GAMS, LINEAR_ (l. 4686-4692, the carbon tax on mineral fertiliser):

         +   v_netPutQuant(RUNR,"NITF")
             * (v_emiLoss(RUNR,"NETF","N2O","GasTot") + v_emiLoss(RUNR,"NETF","NH3","GasTot") * GHGEFS("EF4") + v_emiLoss(RUNR,"NETF","NOx","GasTot")* GHGEFS("EF4") )
                 *  44/28      * p_globWarmPot("GN2O") *p_carbonTax("NETF","GWPA","perton")
    """
    fac = ef_dv
    if w is not None:
        fac = fac + w * (ef_d_nitr + ef_v_nitr)
    return fac * v_netPutQuant


def LINEAR_carbonTaxN2OLEA(v_netPutQuant, ef_l):
    """The indirect N2O of the purchases' runoff and leaching at the emission tax (CAPRI's GWPN2OLEA_ in LINEAR_'s
    tax on the emission types, l. 4717-4724): ef_l x P."""
    return ef_l * v_netPutQuant


def LINEAR_carbonTax_ammOptions(ef, v_actLevl, d):
    r"""The emission tax on the ammonia options' change of the manure N2O through the loss cascade (LINEAR_'s tax on
    the emission types, l. 4717-4724, the options' share of v_CO2EquEmis): per option ef x v_actLevl x d, ef the tax's
    value per unit of the sub-activity and share (the base's own coefficient is in the activity's), d = s - s0.
    Vectors over the options (the builder sums).

    CAPRI's GAMS, LINEAR_'s tax on the emission types (l. 4717-4724):

            - sum(ghgs,p_carbonTax(RUNR,ghgs,"perton") * (
    $ifi not %mitiTecPol%==on   (v_CO2EquEmis(RUNR,ghgs) $ (not sameas(ghgs,"GWPA")) + v_CO2EquEmis(RUNR,"GGWP") $ sameas(ghgs,"GWPA"))
    $ifi     %mitiTecPol%==on   (v_FxActEmis(RUNR,ghgs)  $ (not sameas(ghgs,"GWPA")) + v_FxActEmis(RUNR,"GGWP")  $ sameas(ghgs,"GWPA"))
            * p_globWarmPot(ghgs) - p_carbonTax(RUNR,ghgs,"refGWP")))
    """
    return ef * v_actLevl * d


def LINEAR_carbonTax_NH3kept(ef, v_NH3kept):
    """The emission tax's value of the indirect N2O of the NH3 the ammonia options keep (LINEAR_'s tax on the emission
    types, l. 4717-4724): ef x the NH3-N kept (t); the builder subtracts it (the soil N2O of the mineral N it displaces
    follows the purchases, LINEAR_carbonTaxNITF). CAPRI's GAMS: LINEAR_carbonTax_ammOptions's docstring."""
    return ef * v_NH3kept


def LINEAR_carbonTax_manInhibitor(W, ef, v_Miti):
    """The emission tax's value of the inhibitor on manure (the accounts' emission factors): per t of excreted manure N
    treated, W x ef x s (W the excreted manure N, kt); the builder subtracts it. CAPRI's GAMS:
    LINEAR_carbonTax_ammOptions's docstring."""
    return W * ef * v_Miti


def LINEAR_carbonTax_N2OCRO(ef, catcBioFix):
    """The emission tax on the catch crops' crop-residue N2O (N2OCRO: BioFix x CATC x EF1 x 44/28, in GN2O and so in the
    taxed GGWP; their soil carbon CO2SEQ is not in GGWP): ef x the catch crops' BioFix N (t, from the base share).
    CAPRI's GAMS: LINEAR_carbonTax_ammOptions's docstring."""
    return ef * catcBioFix


def QUADRF_(v_feedUse, lin, half_SLOP, v_feedInpCoeff):
    r"""QUADRF_(r) (l. 4876-4878) with QUADRF1_(r, a) (l. 4882-4889) substituted, the feeds' PMP terms of the
    objective, per animal and flexible feed: F x (CNST + 0.5 SLOP x u), F = FEDUSE_'s herd x u (feeding.py), u the
    per-head feed (CAPRI's v_feedInpCoeff), half_SLOP = 0.5 SLOP. Vectors over the animals' feeds (the builder sums).

    CAPRI's GAMS, QUADRF_ and QUADRF1_ (l. 4876-4889):

        QUADRF_(RUNR) ..
    *
            v_sumOfPmpTermsFeed(RUNR) =E= SUM(  (MAACT) $ p_technFact(RUNR,MAACT,"LEVL","T"), v_actLevl(RUNR,MAACT,"T") * v_pmpCostFeedPerAnim(RUNR,MAACT,"T") );
    *
    *  --- PMP for feed use per per region, activity and technology
    *
        QUADRF1_(RUNR,MAACT %addtimedim%) $ p_technFact(RUNR,MAACT,"LEVL","T") ..
    *
          v_pmpCostFeedPerAnim(RUNR,MAACT,"T") =E=
             SUM(  (FEED) $ p_maxFeedShare(RUNR,MAACT,"T",FEED %addtimedim%),
                  v_feedInpCoeff(RUNR,MAACT,"T",FEED %addtimedim%)
                     *    (p_pmpFeedInpCoeff(RUNR,MAACT,"T",FEED,"CNST")
                              + 0.5 * v_feedInpCoeff(RUNR,MAACT,"T",FEED %addtimedim%)*p_pmpFeedInpCoeff(RUNR,MAACT,"T",FEED,"SLOP")) );

    In this project's notation, for an animal a with herd h_a and a flexible feed f:

        QUADRF_ = sum_a h_a x QUADRF1_a,   QUADRF1_a = sum_f u_f (c_f + 0.5 s_f u_f),   written as sum (h_a u_f)(c_f + 0.5 s_f u_f)

    Departures from CAPRI: the linear coefficient c_f adds to CNST (capri_regional_nlp.calibrate_feed_terms, with
    CapriRegionalNLP.calibrate's correction dcnst) the tradable feed's price (CAPRI: the feed's
    use in its product's market balance, valued in LINEAR_ through v_netPutQuant x UVAG) and the emission tax per kg of
    feed (the spec's feed_ghg); the model minimises the cost, CAPRI maximises v_obje.
    """
    return v_feedUse * (lin + half_SLOP * v_feedInpCoeff)


def LINEAR_netRevenue(revenue, cost, premium):
    r"""LINEAR_(r) (l. 4635-4769), its terms per unit of an activity: the activity's output value (CAPRI's sales,
    v_netPutQuant x UVAG, through SUPBAL_ per unit of the activity), less its variable cost (p_linObjeCont, CAPRI's
    negative values), plus its premium (DATA(PRME) x (1 + p_technFact(PRME))): the model's net revenue per ha or head
    (supply_module._compute_net_revenues).

    CAPRI's GAMS, LINEAR_'s sales (l. 4635-4643) and its activity term (l. 4752-4763):

        LINEAR_(RUNR)..    v_linObjePart(RUNR)  =E=
    *
    *       --- sales/purchases valued by "unit value" price
    *           from gross Economic Accounts for Agriculture
    *
            SUM(  RUNR_OMOBJE(RUNR,OM_OBJE),
                  v_netPutQuant(RUNR,OM_OBJE) * ( SUM(R_RAGG(RUNR,MSACT), (%data%(MSACT,"UVAG",OM_OBJE,"Y") $ (not p_useUvagScen) + (p_uvagScen(MSACT,OM_OBJE) $ p_useUvagScen) ))
                                                + (p_fnutuvag(RUNR,OM_OBJE) $ (p_useInputPScen $ sum(FNUT$sameas(OM_OBJE,FNUT),1)))    ))
        ...
    *      --- activity levels multiplied with
    *          variable costs (excluding feed and animals), negative values
    *          premimums for specific alternatives
    *          premimums defined in policy data set
    *
         +  SUM(  (MPACT,A)  $ p_technFact(RUNR,MPACT,"LEVL",A),
                 v_actLevl(RUNR,MPACT,A)  * (   p_linObjeCont(RUNR,MPACT,A) +  (p_inputPScen(RUNR,MPACT,A) $ p_useInputPScen)
                                          +%data%(RUNR,MPACT,"PRME","Y")*(1+p_technFact(RUNR,MPACT,"PRME",A))
    *                                         For technical testing, here an opportunity to simply add "income" to an activity, which has to have an upper bound
                                              +DATA(RUNR,MPACT,"mgvaShift","Y") $ DATA(RUNR,MPACT,"maxLevl","Y")
                                          ))

    In this project's notation, for an activity a: r_a = R_a - C_a + PRME_a.

    Departures from CAPRI: the output value per head is CAPRI's MREV or TOOU (supply_module._compute_net_revenues: TOOU
    with the market part moving with its prices), the cost per head CAPRI's regional TOIN over the model's heads, the
    premium per head CAPRI's LEVL x PRME over the model's heads (livestock_*_coef.csv); where feeding is not inside the
    model, the feed cost moves with the feed prices (CAPRI: QUADRF_ and the feeds' market balances).
    """
    return revenue - cost + premium


def QUADRA_lin(p_pmpCnst, netRevenue):
    r"""QUADRA_(r)'s linear part (l. 5284-5354: v_actLevl x p_pmpCnst) less LINEAR_'s activity terms (LINEAR_netRevenue):
    the regional problem's linear coefficients, the model minimising 0.5 x'Qx + (f - r)'x where CAPRI maximises
    LINEAR_ - QUADRA_. Vectors over the activities. CAPRI's GAMS: QUADRA_'s docstring."""
    return p_pmpCnst - netRevenue


def QUADRA_(Q, y):
    r"""QUADRA_(r) (l. 5284-5354) with GRPLEVL_(r, GRP) (l. 4892-4895) substituted, the quadratic part of the PMP terms
    of the activity levels in the regional NLP: 0.5 y'Qy, Q the regional problem's matrix: the model's PMP matrix
    (supply_module: the crops' terms from CAPRI's 2030 calibration, the technologies' and the crop groups' collapsed to
    the model's activities, tools/build/build_pmp_capri_2030.py) and, with the land market, LandMarket_'s terms on the
    land columns (land.py LandMarket_quad). CasADi (the NLP gives its Hessian to IPOPT directly).

    CAPRI's GAMS, QUADRA_ (l. 5284-5354; the water module's terms, off in the step, left out):

        QUADRA_(RUNR) ..  v_sumOfPmpTermsLevls(RUNR) =E= (
    *               Linear part
    *pw             (specified in tems of mPact to cover the case of watermodule==on where qAct differs from mPact)
                    sum((mpact,A) $ (p_technFact(RUNR,mpact,"LEVL",A) $ (p_PMPStep1 ne 1)),
                        v_actLevl(RUNR,mpact,A)*p_pmpCnst(RUNR,mpact,A))
    *               plus the v_sumOfPmpTermsLevlstic part multiplied by 0.5 for easy derivatives
                    + 0.5 * (
    *
    *               multiplied by the diagonal effects (direct own area cost effect)
                        sum((qact,A,A1) $ (p_technFact(RUNR,qact,"LEVL",A) $ p_technFact(RUNR,qact,"LEVL",A1)),
                           v_actLevl(RUNR,qact,A)*v_actLevl(RUNR,qact,A1)
                           * (    p_pmpQuadTechn(RUNR,qact,A,A1)
    *                            + (SUM(EPRD_TO_GRP(qact,GRP),p_pmpQuadPact(RUNR,GRP,GRP))/p_technFact(RUNR,qact,"LEVL",A)) $ (SAMEAS(A,A1) $ (p_useCropSpecificQMatrix eq 0))
                                + (p_pmpQuadPact(RUNR,qact,qact)/p_technFact(RUNR,qact,"LEVL",A))                          $ (SAMEAS(A,A1) $ (p_useCropSpecificQMatrix eq 1))))
    *               plus the crop group effects
                      + sum((GRP,GRP1) $ (p_useCropSpecificQMatrix eq 0),
                               v_actLevl(RUNR,GRP,"T")*v_actLevl(RUNR,GRP1,"T")*
                                   (p_pmpQuadPact(RUNR,GRP,GRP1) $ (p_ordGrp(GRP) le p_ordGrp(GRP1))
                                  + p_pmpQuadPact(RUNR,GRP1,GRP) $ (p_ordGrp(GRP) gt p_ordGrp(GRP1))))
    *               wipes out the mapping of the diagonal element
    *                - SUM(EPRD_TO_GRP(qact,GRP) $ (p_useCropSpecificQMatrix eq 0),
    *                     SQR(SUM(A $ p_technFact(RUNR,qact,"LEVL",A), v_actLevl(RUNR,qact,A)))
    *                                         * p_pmpQuadPact(RUNR,GRP,GRP))
    *               plus the full Q effect
                      + sum((qact,qact1) $ ( (NOT SAMEAS(qact,qact1)) $ (p_useCropSpecificQMatrix eq 1)),
                               SUM(A $ p_technFact(RUNR,qact,"LEVL",A),  v_actLevl(RUNR,qact,A))
                             * SUM(A $ p_technFact(RUNR,qact1,"LEVL",A), v_actLevl(RUNR,qact1,A))
                                *  (p_pmpQuadPact(RUNR,qact,qact1) $ (qact.pos le qact1.pos)
                                  + p_pmpQuadPact(RUNR,qact1,qact) $ (qact.pos gt qact1.pos))))
    *               plus the effect of changing irrigation / rainfed shares
        ...
    $endif.wmod2
                    );

    GRPLEVL_ (l. 4892-4895):

        GRPLEVL_(RUNR,GRP) $ (SUM( (qact,A) $ (EPRD_TO_GRP(qact,GRP) $ p_technFact(RUNR,qact,"LEVL",A)), 1)
                                      $ p_pmpQuadPact(RUNR,GRP,GRP) $ (not p_useCropSpecificQMatrix) ) ..
               v_actLevl(RUNR,GRP,"T") =E= SUM( (qact,A) $ (EPRD_TO_GRP(qact,GRP) $ p_technFact(RUNR,qact,"LEVL",A)), v_actLevl(RUNR,qact,A));

    In this project's notation: QUADRA_ = f'x + 0.5 x'Qx (the linear part in QUADRA_lin).

    Departures from CAPRI: the PMP terms are calibrated by the model (supply_module: Q from CAPRI's 2030 terms where
    CAPRI has them, else from the supply elasticities; f so that the base is optimal) and the crop groups' levels are
    substituted into Q.
    """
    import casadi as ca
    return 0.5 * ca.mtimes([y.T, Q, y])


def OBJEQF_(obj_rest, quad):
    r"""OBJEQF_ (l. 4773-4806) for one region, as the regional NLP minimises it: the objective's other terms, summed as
    the builder adds them (CapriRegionalNLP.__init__ and its blocks: the feeds' QUADRF_, the linear coefficients
    QUADRA_lin with the land market's LandMarket_cnst, the mitigation options' GHG_Mit_Cost_, the fertilisation
    block's LINEAR_ terms), plus QUADRA_'s quadratic part (with LandMarket_quad), kept apart for its Hessian.

    CAPRI's GAMS, OBJEQF_ (l. 4773-4806):

        OBJEQF_..  v_obje =E= SUM(RUNR,
    *
    *           --- revenues - variable costs
    *
                v_linObjePart(RUNR) - v_sumOfPmpTermsLevls(RUNR)*v_labCap.scale(runr) $ ( v_labCap.lo(RUNR) ne v_labCap.up(RUNR))
    *
    *           --- contribution of PMP terms for feeding
    *
               + v_sumOfPmpTermsFeed(RUNR)*v_labCap.scale(runr) $ ((p_PMPStep1 ne 1) $ ( v_labCap.lo(RUNR) ne v_labCap.up(RUNR)))
    *
    *          --- cost of GHG mitigation options
    *
    $iftheni.aba3 %ghgAbatement%==on
               - v_GHG_Mit_Cost(RUNR)
    $endif.aba3
    *
    *           --- land market
    *
    $iftheni.tru8 %Trustee_land%==ON
               - v_pmpCostLandMarket(RUNR)*p_landMarketScale $ ((p_landIsFixed eq 0) $ (p_PMPStep1 ne 1) $ v_labCap.range(RUNR))
    *            activate for testing if calibration works with exogenously given land rents:
    *          - v_pmpCostLandMarket(RUNR)*p_landMarketScale $ ((p_PMPStep1 ne 1) $ v_labCap.range(RUNR) $ (not sameas(runr,"ukn00000")))
    $else.tru8
               - v_pmpCostLandMarket(RUNR)*v_labCap.scale(runr) $ ((p_landIsFixed eq 0) $ (p_PMPStep1 ne 1) $ (v_labCap.lo(RUNR) ne v_labCap.up(RUNR)))
               - v_landSupCost(RUNR)       $ ((p_landIsFixed eq 0) $ (p_PMPStep1 ne 1))
    $endif.tru8
    *           --- water supply cost
    $iftheni.wcos %WaterModule%==ON
               -  sum(wsource, v_watSupCost(RUNR,wsource,"WS_IRR"))
    $endif.wcos
               );

    Departures from CAPRI: the sign (the model minimises - v_obje); v_labCap.scale is 1 in the step (labCap_ is not
    written: the module's docstring).
    """
    return obj_rest + quad
