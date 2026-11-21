r"""CAPRI's calibration of the Armington system (arm/cal_armington.gms, star 3.0): the CES share parameters
p_dpCESTrade at the calibration point, from the base flows and prices, and the import aggregate's and the Armington
prices there.

CAPRI's GAMS statement of each assignment is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026, the supply phase); this docstring keeps the overview, notation and departures. The
module is named after CAPRI's file (the calibration block C1, docs/dev/MARKET_EQUATION_REFACTOR_PLAN.md); the
functions after the symbols CAPRI assigns.

Written: the trade blocks' calibration (capri_mod/market/bilateral.py BilateralCommodity.calibrate), at the start of
every run. CAPRI computes the parameters when it generates the simulation's start point sim_ini (arm/market1.gms
l. 625; docs/dev/calibration_equations_inventory.csv).

In this project's notation, per commodity, importer i and exporter j at the calibration point (X_ij the flows, DS_i
the domestic sales, M_i the imports, D_i = DS_i + M_i the use; p_ij the import prices, Pd_i the market price; s1, s2
p_rhoArm1, p_rhoArm2):

    v_arm2Price      PM_i = sum_j X_ij p_ij / M_i                     (the import aggregate's price)
    arm1Price_       PA_i = (DS_i Pd_i + M_i PM_i) / D_i             (the Armington price, by value)
    p_dpCESTrade     beta_ij = X_ij / M_i (p_ij / PM_i)^s2           (the bilateral flows' shares)
                     dd_i = DS_i / D_i (Pd_i / PA_i)^s1               (the domestic sales')
                     dm_i = M_i / D_i (PM_i / PA_i)^s1                (the import aggregate's, CAPRI's "RW")

Departures from CAPRI: the calibration point the model's (its base supply closes the flows: domestic sales absorb
the difference between the model's production and CAPRI's, bilateral.py calibrate); the Armington price at it by
value, CAPRI's arm1Price_ (market_model.gms l. 2921-2931, the calibration's form), where CAPRI's sim_ini carries its
DATA arm1P; the modified Armington system's calibration (pv_theta, v_gammaCES, l. 82-89 on) off.
"""
from __future__ import annotations


def v_arm2Price(val, M):
    r"""The import aggregate's price at the calibration point (arm/cal_armington.gms l. 39-42), the imports' value
    over their quantity, val / M. Elementwise.

    CAPRI's GAMS, v_arm2Price (arm/cal_armington.gms l. 39-42):

         v_arm2Quant.l(RM,XXX) = sum(RM1 $ (p_tradeFlows(RM,RM1,XXX,"Cur") and (not sameas(RM,RM1))),  v_tradeFlows.l(RM,RM1,XXX));
         v_arm2Val.l(RM,XXX)   = sum(RM1 $ (p_tradeFlows(RM,RM1,XXX,"Cur") and (not sameas(RM,RM1))),  v_tradeFlows.l(RM,RM1,XXX)*v_impPrice.l(RM,RM1,XXX));
         v_arm2Price.l(RM,XXX) $ v_arm2Quant.l(RM,XXX) = v_arm2Val.l(RM,XXX)/v_arm2Quant.l(RM,XXX);
    """
    return val / M


def arm1Price_(DS, Pd, M, PM, D):
    r"""arm1Price_(RM, XXX) (arm/market_model.gms l. 2921-2931), the Armington price at the calibration point by
    value, (DS Pd + M PM) / D. Elementwise.

    CAPRI's GAMS, arm1Price_ (arm/market_model.gms l. 2921-2931):

      arm1Price_(RM,XXX) $ ( (v_domSales.up(RM,XXX) ne 0) or (v_Arm2Quant.up(RM,XXX) ne 0) ) ..
           v_arm1Price(RM,XXX) * v_Arm1Quant(RM,XXX)/1000.
                / (DATA(RM,"arm1P",XXX,"CUR")+1)
            =E=  (
                          v_marketPrice(RM,XXX) * v_domSales(RM,XXX) /1000
                        + v_arm2Price(RM,XXX)   * v_arm2Quant(RM,XXX)/1000
                 )
                 /(DATA(RM,"arm1P",XXX,"CUR")+1) ;
    """
    return (DS * Pd + M * PM) / D


def p_dpCESTrade_bilateral(X, M, P, PM, s2):
    r"""p_dpCESTrade(RM, RM1, XXX) of a bilateral flow (arm/cal_armington.gms l. 46-50): (X / M) (P / PM)^s2.
    Elementwise.

    CAPRI's GAMS, p_dpCESTrade (arm/cal_armington.gms l. 46-50):

         p_dpCESTrade(RM,RM1,XXX) $ (p_tradeFlows(RM,RM1,XXX,"Cur") and (not sameas(RM,RM1)))
              = v_tradeFlows.l(RM,RM1,XXX)/(  v_arm2Quant.l(RM,XXX)
                      * [ v_arm2Price.l(RM,XXX) / v_impPrice.l(RM,RM1,XXX) ] ** p_rhoArm2(RM,XXX));
    """
    return (X / M) * (P / PM) ** s2


def p_dpCESTrade_domestic(DS, D, Pd, PA, s1):
    r"""p_dpCESTrade(RM, RM, XXX), the domestic sales' share (arm/cal_armington.gms l. 53-57): DS / D (Pd / PA)^s1.
    Elementwise.

    CAPRI's GAMS, p_dpCESTrade (arm/cal_armington.gms l. 53-57):

         p_dpCESTrade(RM,RM,XXX) $ (p_tradeFlows(RM,RM,XXX,"Cur") )
              = v_domSales.l(RM,XXX)/(  v_arm1Quant.l(RM,XXX)
                      * [ v_arm1Price.l(RM,XXX) / v_marketPrice.l(RM,XXX) ] ** p_rhoArm1(RM,XXX));
    """
    return DS / D * (Pd / PA) ** s1


def p_dpCESTrade_RW(M, D, PM, PA, s1):
    r"""p_dpCESTrade(RM, "RW", XXX), the import aggregate's share (arm/cal_armington.gms l. 60-64): M / D (PM /
    PA)^s1. Elementwise.

    CAPRI's GAMS, p_dpCESTrade (arm/cal_armington.gms l. 60-64):

         p_dpCESTrade(RM,"RW",XXX) $ (v_arm2Quant.l(RM,XXX) )
              = v_arm2Quant.l(RM,XXX)/(  v_arm1Quant.l(RM,XXX)
                      * [ v_arm1Price.l(RM,XXX) / v_arm2Price.l(RM,XXX) ] ** p_rhoArm1(RM,XXX));
    """
    return M / D * (PM / PA) ** s1
