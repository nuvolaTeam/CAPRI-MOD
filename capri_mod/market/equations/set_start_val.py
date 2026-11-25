r"""CAPRI's market model's start values and bounds (arm/set_start_val.gms, star 3.0): the processing quantities' and the
market prices' bounds.

capri_mod/market/market_bounds.py (capri_start_bounds) calls them, on the lifted system's unknowns (arrays).
"""
from __future__ import annotations

import numpy as np


def v_procQuant_bounds(Proc, lowLimitFactQuant, uppLimitFactQuant):
    r"""(v_procQuant.LO, v_procQuant.UP)(RMS, XX): a processing quantity's bounds, its level x P_lowLimitFactQuant
    (1e-5) to max(1, level) x P_uppLimitFactQuant (1e3); arrays.

    CAPRI's GAMS (arm/set_start_val.gms l. 32-37):

         v_procQuant.L (RMS,XX)          = DATA(RMS,"Proc",XX,"CUR") $ (DATA(RMS,"Proc",XX,"CUR") GT 1.E-8);
         v_procQuant.L(RM,XX)            = SUM(RMS_TO_RM(RMS,RM), v_procQuant.L (RMS,XX));
         v_procQuant.LO(RMS,XX)          = DATA(RMS,"Proc",XX,"CUR") * P_lowLimitFactQuant;
         v_procQuant.UP(RMS,XX)    $ DATA(RMS,"Proc",XX,"CUR")      = MAX(1,DATA(RMS,"Proc",XX,"CUR")) * P_uppLimitFactQuant;
         v_procQuant.fx(RMS,XX)    $ (NOT SUM(YY, ABS(p_hessNQProc(RMS,XX,YY,"CUR")+p_hessNQProc(RMS,YY,XX,"CUR")))) = DATA(RMS,"Proc",XX,"CUR");
         v_procQuant.FX(RMS,XX)    $ (v_procQuant.L(RMS,XX) LE 0.1)       = v_procQuant.L(RMS,XX);

    Departures from CAPRI: per market region's cell (CAPRI per behavioural region); the cells at or below 0.1 kt and
    those without ProcNQ_ not fixed (the lifted system keeps their defining row; capri_mod/market/market_bounds.py)."""
    b = np.asarray(Proc, float)
    return b * lowLimitFactQuant, np.maximum(1.0, b) * uppLimitFactQuant


def v_marketPrice_bounds(has_PMrk, level, lowLimitFactPrice, uppLimitFactPrice):
    r"""(v_marketPrice.LO, v_marketPrice.UP)(RM, XX) as price ratios: P_lowLimitFactPrice (0.1) to P_uppLimitFactPrice
    (10) where the market region has a market price in CAPRI's data, fixed at the level otherwise; arrays.

    CAPRI's GAMS (arm/set_start_val.gms l. 525-530):

         v_marketPrice.fx(Rall,XX) = 0;
         v_marketPrice.L (RM,XX) $ DATA(RM,"PMrk",XX,"CUR")   = DATA(RM,"PMrk",XX,"CUR");
         v_marketPrice.LO(RM,XX) $ DATA(RM,"PMrk",XX,"CUR")   = DATA(RM,"PMrk",XX,"CUR") * P_lowLimitFactPrice;
         v_marketPrice.UP(RM,XX) $ DATA(RM,"PMrk",XX,"CUR")   = DATA(RM,"PMrk",XX,"CUR") * (P_uppLimitFactPrice
        $ifi "%scenarioGroup%%shocktype%%simy%"=="agClim50iiimin2030"                      -P_uppLimitFactPrice*.85 $ sameas(XX,"FPRI")
                                                                                                               );

    Departures from CAPRI: in ratios to CAPRI's price (the model's unknowns), the cells without a price fixed at their
    start level (CAPRI's at 0: no market price); the agClim50 scenario's FPRI bound not ported; the PMrk_ cells'
    ratio floored at 1e-3 instead (capri_mod/market/bilateral.py pmrk_ratios)."""
    has = np.asarray(has_PMrk, bool)
    return np.where(has, lowLimitFactPrice, level), np.where(has, uppLimitFactPrice, level)
