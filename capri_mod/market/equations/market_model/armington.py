r"""CAPRI's adding-up conditions and Armington system (arm/market_model.gms l. 2595-2841): the supply balance
(SupBalM_) and the two Armington nests' quantities, the import aggregate's and the domestic sales' shares of use
(arm2QuantShares_, domSalesShares_) and the bilateral flows' shares of the import aggregate (importShares_).

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026, the supply phase); this docstring keeps the block's overview, notation and departures.

Written: the bilateral commodities' trade blocks in their three forms, each calling the functions with its own
arguments: NumPy (capri_mod/market/bilateral.py BilateralCommodity.flows, residual: the default solve), CasADi per
region (trade_ad.py _system: the trade function with its exact Jacobian) and CasADi per cell (trade_system_ad.py: the
assembled market system). The functions are elementwise, the same expression for NumPy arrays and CasADi scalars;
the sums over the flows stay the callers' (each its own order).

In this project's notation, per commodity, importer i and exporter j (D_i the use, CAPRI's v_arm1Quant; PA_i the
Armington price, Pd_i the market price, PM_i the import aggregate's price, p_ij the import price; dd_i, dm_i, beta_ij
CAPRI's share parameters p_dpCESTrade; s1, s2 the substitution elasticities p_rhoArm1, p_rhoArm2):

    domSalesShares_   DS_i = D_i dd_i (PA_i / Pd_i)^s1
    arm2QuantShares_  M_i = D_i dm_i (PA_i / PM_i)^s1
    importShares_     X_ij = M_i beta_ij (PM_i / p_ij)^s2
    SupBalM_          S_j - DS_j - sum_{i != j} X_ij = 0 (the residual, 1000 t; the exports' sum is expQuant_)

Departures from CAPRI: the rows unscaled; the modified Armington terms (v_gammaCES, pv_theta, p_arm2Commit) are 1 and
0 in the step (modArmington off: arm/cal_armington.gms l. 82-90 fixes them and exits, p_arm2Commit = 0 at
market_model.gms l. 225), so importShares_ is the standard CES share and HicksNeutral_ and tradeFlowFudge_ are empty;
the import prices floored at 1e-9 (the callers'); SupBalM_ without the intervention stock change and the C-sugar
term (M5; CSugarPrice_ empty in the step). ArmBal1_ (the use as the sum of human consumption, feed, processing and
biofuel processing) is the use side's sum (capri_mod/market/demand.py, use_ad.py).
"""
from __future__ import annotations


def domSalesShares_(D, dd, PA, Pd, s1):
    r"""domSalesShares_(RM, XXX) (l. 2721-2730): the domestic sales, D dd (PA / Pd)^s1. Elementwise (NumPy or CasADi).

    CAPRI's GAMS, domSalesShares_ (l. 2721-2730):

      domSalesShares_(RM,XXX) $ ( v_domSales.up(RM,XXX) $ (v_domSales.LO(RM,XXX) ne v_domSales.UP(RM,XXX))) ..
          v_domSales(RM,XXX)/(p_tradeFlows(RM,RM,XXX,"CUR")+1.)
                   =E=  v_arm1Quant(RM,XXX)/(p_tradeFlows(RM,RM,XXX,"CUR")+1.)
                      * p_dpCESTrade(RM,RM,XXX)
                      * [ v_arm1Price(RM,XXX) / v_marketPrice(RM,XXX) ] ** p_rhoArm1(RM,XXX);
    """
    return D * dd * (PA / Pd) ** s1


def arm2QuantShares_(D, dm, PA, PM, s1):
    r"""arm2QuantShares_(RM, XXX) (l. 2706-2715): the import aggregate, D dm (PA / PM)^s1. Elementwise.

    CAPRI's GAMS, arm2QuantShares_ (l. 2706-2715):

      arm2QuantShares_(RM,XXX) $ ( v_arm2Quant.up(RM,XXX) $ (v_arm2Quant.LO(RM,XXX) ne v_arm2Quant.UP(RM,XXX))) ..
          v_arm2Quant(RM,XXX)/(DATA(RM,"ARM2",XXX,"CUR")+1.)
                   =E=  v_arm1Quant(RM,XXX)/(DATA(RM,"ARM2",XXX,"CUR")+1.)
                      * p_dpCESTrade(RM,"RW",XXX)
                      * [ v_arm1Price(RM,XXX) / v_arm2Price(RM,XXX) ] ** p_rhoArm1(RM,XXX) ;
    """
    return D * dm * (PA / PM) ** s1


def importShares_(M, beta, PM, p, s2):
    r"""importShares_(RM, RM1, XXX) (l. 2749-2781): a bilateral import flow, M beta (PM / p)^s2 (the standard CES
    share: v_gammaCES and pv_theta at 1, no commitment term in the step). Elementwise.

    CAPRI's GAMS, importShares_ (l. 2749-2781):

      importShares_(RM,RM1,XXX) $ ( (p_tradeFlows(RM,RM1,XXX,"Cur") or p_arm2Commit(rm,rm1,xxx)) $ (not SAMEAS(RM,RM1))
                                    $  (v_tradeFlows.range(RM,RM1,XXX) or NonZeroFixedImportFlow(RM,RM1,XXX) or pv_theta.range(rm,rm1,xxx))) ..
          ( v_tradeFlows(RM,RM1,XXX)   $ (v_tradeFlows.lo(RM,RM1,XXX) gt 0)
          + v_tradeFlowNeg(RM,RM1,XXX) $ (v_tradeFlows.lo(RM,RM1,XXX) le 0))
                       /(p_tradeFlows(RM,RM1,XXX,"Cur")+1.)
                   =E= [v_arm2Quant(RM,XXX)
                      *  v_gammaCES(rm, xxx) ** (p_rhoArm2(rm, xxx) - 1)
                      * p_dpCESTrade(RM,RM1,XXX)
                      *  pv_theta(rm,rm1,xxx) ** (p_realRhoArm2(rm,xxx) * p_rhoArm2(rm,xxx))
                      * (  v_arm2Price(RM,XXX)
                        / (   v_impPrice(RM,RM1,XXX)       $ (NOT NonZeroFixedImportFlow(RM,RM1,XXX))
                          +   v_impShadowPrice(RM,RM1,XXX) $ (    NonZeroFixedImportFlow(RM,RM1,XXX)) )) ** p_rhoArm2(RM,XXX)
                      + p_arm2Commit(RM,RM1,XXX)]
                       /(p_tradeFlows(RM,RM1,XXX,"Cur")+1.)
         ;
    """
    return M * beta * (PM / p) ** s2


def SupBalM_(S, sold):
    r"""SupBalM_(RM, XXX) (l. 2632-2650): the supply balance's residual, S - sold, sold the domestic sales plus the
    exports (1000 t). Elementwise.

    CAPRI's GAMS, SupBalM_ (l. 2632-2650):

      SupBalM_(RM,XXX) $ (not xxOMYani(XXX)) ..
          v_domSales(RM,XXX)
             /( (DATA(RM,"DSales",XXX,"CUR")+DATA(RM,"Prod",XXX,"CUR"))*0.5 $ (not p_trim)  + 1 $ p_trim + 0.1)
              =E=
             (   v_prodQuant(RM,XXX) $ DATA(RM,"Prod",XXX,"CUR")
              - v_expQuant(RM,XXX)   $ (DATA(RM,"Exports",XXX,"CUR") or p_trim)
              - V_intervStockChange(RM,XXX) $ sum(rm_to_rmtp(rm,rmtp) $ ( (DATA(RMTP,"PADM",XXX,"CUR") gt eps)
                                                                        $ (DATA(RMTP,"STKS",XXX,"CUR") gt eps)),1)
              - SUM(RMS_TO_RM(RMS,RM) $ ( DATA(RMS,"Prod",XXX,"CUR") $ sameas(XXX,"SUGA")
                                        $ DATA(RMS,"Biof","SUGA","CUR") $ (data(RMS,"QUTS","SUGA","CUR") gt eps)),
                v_biofProcQuant(RMS,"SUGA")
                )
     $ifi %capri_sr%==on     - (V_privStockFin(RM,XXX)-DATA(RM,"STKINI",XXX,"CUR")) $ ( p_stockDemElas(RM,XXX) $ (DATA(RM,"STKINI",XXX,"CUR") gt eps) )
             )
             /( (DATA(RM,"DSales",XXX,"CUR")+DATA(RM,"Prod",XXX,"CUR"))*0.5 $ (not p_trim)  + 1 $ p_trim + 0.1);
    """
    return S - sold
