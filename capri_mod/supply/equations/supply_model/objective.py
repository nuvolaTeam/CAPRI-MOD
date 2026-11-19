r"""CAPRI's objective (supply/supply_model.gms l. 4675-5056 and 5358-5433): LINEAR_, the linear part of the regional
objective, v_linObjePart.

Written so far: the fertilisation block's terms on the mineral N purchases v_netPutQuant(NITF) (the regional NLP's
fertilisation block, CapriRegionalNLP._fert_block): their value at the unit value (UVAG) and the emission tax on
mineral N's soil N2O, with the indirect N2O of the purchases' runoff and leaching at the same tax.

CAPRI's GAMS, LINEAR_ (l. 4694-4702, the purchases valued by their unit value; the other terms left out here):

    LINEAR_(RUNR)..    v_linObjePart(RUNR)  =E=
        SUM(  RUNR_OMOBJE(RUNR,OM_OBJE),
              v_netPutQuant(RUNR,OM_OBJE) * ( SUM(R_RAGG(RUNR,MSACT), (%data%(MSACT,"UVAG",OM_OBJE,"Y") $ (not p_useUvagScen) + (p_uvagScen(MSACT,OM_OBJE) $ p_useUvagScen) ))
                                            + (p_fnutuvag(RUNR,OM_OBJE) $ (p_useInputPScen $ sum(FNUT$sameas(OM_OBJE,FNUT),1)))    ))

CAPRI's GAMS, LINEAR_ (l. 4759-4765, the carbon tax on mineral fertiliser):

     +   v_netPutQuant(RUNR,"NITF")
         * (v_emiLoss(RUNR,"NETF","N2O","GasTot") + v_emiLoss(RUNR,"NETF","NH3","GasTot") * GHGEFS("EF4") + v_emiLoss(RUNR,"NETF","NOx","GasTot")* GHGEFS("EF4") )
             *  44/28      * p_globWarmPot("GN2O") *p_carbonTax("NETF","GWPA","perton")

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
    """The purchases valued at their unit value (LINEAR_, l. 4694-4702): uvag x P, kEUR (uvag per t / 1000)."""
    return uvag * v_netPutQuant


def LINEAR_carbonTaxNITF(v_netPutQuant, ef_dv, w=None, ef_d_nitr=None, ef_v_nitr=None):
    """The emission tax on mineral N's soil N2O (LINEAR_, l. 4759-4765): fac x P, fac = ef_dv (the direct and the
    volatilised N's indirect N2O x GWP x tax per t) [+ w (ef_d_nitr + ef_v_nitr): the nitrification inhibitor's change
    on the share w of mineral N under it]."""
    fac = ef_dv
    if w is not None:
        fac = fac + w * (ef_d_nitr + ef_v_nitr)
    return fac * v_netPutQuant


def LINEAR_carbonTaxN2OLEA(v_netPutQuant, ef_l):
    """The indirect N2O of the purchases' runoff and leaching at the emission tax (CAPRI's GWPN2OLEA_ in LINEAR_'s
    tax on the emission types, l. 4790-4797): ef_l x P."""
    return ef_l * v_netPutQuant
