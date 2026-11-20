r"""CAPRI's objective (supply/supply_model.gms l. 4675-5056 and 5358-5433): LINEAR_, the linear part of the regional
objective, v_linObjePart.

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026); this docstring keeps the block's overview, notation and departures.

Written so far: the fertilisation block's terms on the mineral N purchases v_netPutQuant(NITF) (the regional NLP's
fertilisation block, CapriRegionalNLP._fert_block): their value at the unit value (UVAG) and the emission tax on
mineral N's soil N2O, with the indirect N2O of the purchases' runoff and leaching at the same tax; the emission
tax's terms of the mitigation options (CapriRegionalNLP._abatement_block); and the feeds' PMP terms, QUADRF_ with
QUADRF1_ (CapriRegionalNLP.__init__'s objective).

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
    """The purchases valued at their unit value (LINEAR_, l. 4694-4702): uvag x P, kEUR (uvag per t / 1000).

    CAPRI's GAMS, LINEAR_ (l. 4694-4702, the purchases valued by their unit value; the other terms left out here):

        LINEAR_(RUNR)..    v_linObjePart(RUNR)  =E=
            SUM(  RUNR_OMOBJE(RUNR,OM_OBJE),
                  v_netPutQuant(RUNR,OM_OBJE) * ( SUM(R_RAGG(RUNR,MSACT), (%data%(MSACT,"UVAG",OM_OBJE,"Y") $ (not p_useUvagScen) + (p_uvagScen(MSACT,OM_OBJE) $ p_useUvagScen) ))
                                                + (p_fnutuvag(RUNR,OM_OBJE) $ (p_useInputPScen $ sum(FNUT$sameas(OM_OBJE,FNUT),1)))    ))
    """
    return uvag * v_netPutQuant


def LINEAR_carbonTaxNITF(v_netPutQuant, ef_dv, w=None, ef_d_nitr=None, ef_v_nitr=None):
    """The emission tax on mineral N's soil N2O (LINEAR_, l. 4759-4765): fac x P, fac = ef_dv (the direct and the
    volatilised N's indirect N2O x GWP x tax per t) [+ w (ef_d_nitr + ef_v_nitr): the nitrification inhibitor's change
    on the share w of mineral N under it].

    CAPRI's GAMS, LINEAR_ (l. 4759-4765, the carbon tax on mineral fertiliser):

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
    tax on the emission types, l. 4790-4797): ef_l x P."""
    return ef_l * v_netPutQuant


def LINEAR_carbonTax_ammOptions(ef, v_actLevl, d):
    r"""The emission tax on the ammonia options' change of the manure N2O through the loss cascade (LINEAR_'s tax on
    the emission types, l. 4790-4797, the options' share of v_CO2EquEmis): per option ef x v_actLevl x d, ef the tax's
    value per unit of the sub-activity and share (the base's own coefficient is in the activity's), d = s - s0.
    Vectors over the options (the builder sums).

    CAPRI's GAMS, LINEAR_'s tax on the emission types (l. 4790-4797):

            - sum(ghgs,p_carbonTax(RUNR,ghgs,"perton") * (
    $ifi not %mitiTecPol%==on   (v_CO2EquEmis(RUNR,ghgs) $ (not sameas(ghgs,"GWPA")) + v_CO2EquEmis(RUNR,"GGWP") $ sameas(ghgs,"GWPA"))
    $ifi     %mitiTecPol%==on   (v_FxActEmis(RUNR,ghgs)  $ (not sameas(ghgs,"GWPA")) + v_FxActEmis(RUNR,"GGWP")  $ sameas(ghgs,"GWPA"))
            * p_globWarmPot(ghgs) - p_carbonTax(RUNR,ghgs,"refGWP")))
    """
    return ef * v_actLevl * d


def LINEAR_carbonTax_NH3kept(ef, v_NH3kept):
    """The emission tax's value of the indirect N2O of the NH3 the ammonia options keep (LINEAR_'s tax on the emission
    types, l. 4790-4797): ef x the NH3-N kept (t); the builder subtracts it (the soil N2O of the mineral N it displaces
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
    r"""QUADRF_(r) (l. 4949-4951) with QUADRF1_(r, a) (l. 4955-4962) substituted, the feeds' PMP terms of the
    objective, per animal and flexible feed: F x (CNST + 0.5 SLOP x u), F = FEDUSE_'s herd x u (feeding.py), u the
    per-head feed (CAPRI's v_feedInpCoeff), half_SLOP = 0.5 SLOP. Vectors over the animals' feeds (the builder sums).

    CAPRI's GAMS, QUADRF_ and QUADRF1_ (l. 4949-4962):

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
