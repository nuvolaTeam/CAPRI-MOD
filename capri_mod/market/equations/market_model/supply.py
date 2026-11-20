r"""CAPRI's supply functions in the market (arm/market_model.gms l. 1524-1656, of the behavioural functions): the
normalised quadratic supply (ProdNQ_) and the young-animal markets (yaniMarket_).

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026, the supply phase); this docstring keeps the block's overview, notation and departures.

Written: the market's CasADi supply blocks (capri_mod/market/supply_ad.py: nq_rows_function, the ratio form of the
market regions without supply models and of the EU's products no supply model produces; hess_rows_function, the
measured Hessian of the supply models' products; yani_function), which SupplyMixin (capri_mod/market/supply.py) and
the assembled system (supply_system_ad.py, Norway's rows and young-animal markets there) evaluate. The floors and
ProdFudge_ (fudging.py) are the callers'.

In this project's notation, per market region and product x (r the region's price ratios of the market products, m
its raw milk price ratio, FEDE_s the feed energy price ratio of its CAPRI region s, l_x the change from the land rents
of its CAPRI regions, h in kt per unit of price ratio; for the supply models' products s0 their latest output, dP the
price change against the prices they saw, Hm the Hessian measured on them; for the young animals y, net their net
supply at the models' solution, ref the reference, dr their prices' change):

    ProdNQ_      q_x = max(0, q0_x + sum_y h_xy (r_y - 1) + h_xM (m - 1) + sum_s f_xs (FEDE_s - 1) + l_x)
                 (the ratio form), q = max(0, s0 + Hm dP + e) (the measured Hessian; e the young animals' and raw
                 milk's terms of their clearing)
    yaniMarket_  net + H_YP dP + H_YY dr (+ e) - ref = 0

Departures from CAPRI: the rows unscaled (CAPRI divides by DATA Prod + 0.1, and yaniMarket_ by half the gross
flows + 1); ProdNQ_'s Hessian on the price ratios (tools/build/build_noneu_market_supply_nq.py: CAPRI's p_hessNQSupp
x (PPRI0 - support) / INPE, INPE's price held), the raw milk's support terms (PSEd, PSEI, AREP) in the milk price
ratio; the crude oil cost term (p_oilCostShare x DATA UVAG CRDO PercentageChange) left out: the step sets no oil price
change (set only in pol_input/liaise/liaise_scen.gms l. 464-465 and scen/macro_environment/oil_price_50.gms l. 21);
the EU's supply-model products by one measured Hessian per EU market region (the sum of its member states'; CAPRI's
ProdNQ_ per member state, ProdA_ summing them), the constant re-anchored to the models' latest output at the prices
they saw (arm/simu_calibration_to_supply.gms l. 360-368); the floor at 0 the model's (DEP-39; ProdFudge_ in the
assembled system). rmsYaniMarket_ (l. 1613-1634) is empty in the step: its set xx_no_ppri_but_rmsYaniMarket_equ is
killed at l. 552 and filled only in pol_input/outlook2022/max_factor_levl_.gms l. 46, which the step does not
include. The young animals' and raw milk's terms of the products' supply (H_PY dr, the milk prices') and ProdNQ_'s
numeric forms in supply.py (_milk_terms, _excluded_milk_resp, _noneu_milk_shift; the K83 units' rows in
supply_system_ad.py) stay terms of their callers.
"""
from __future__ import annotations

import numpy as np


def ProdNQ_(H, r, hm, m, HF, fede, lsh):
    r"""ProdNQ_(RMS, XX1) (l. 1529-1572) in the ratio form, the change of the rows' supply from their calibration
    point, H (r - 1) + hm (m - 1) + HF (FEDE - 1) + lsh: H (n_x x n_cols) the terms in the market products' price ratios
    r, hm (n_x) those in the raw milk price ratio m, HF (n_x x n_s) those in the feed energy price ratios of the
    region's CAPRI regions (none: n_s = 0), lsh the change from the land rents (an input). CasADi; H, hm, HF numbers.
    The rows' supply is max(0, q0 + the change) (the caller's floor).

    CAPRI's GAMS, ProdNQ_ (l. 1529-1572):

      ProdNQ_(RMS,XX1) $ (  (    (NOT xx_no_prodNQ_equation(XX1,RMS))
                               $ (not sameas(XX1,"FEDE")))
                               $  (XXX1(XX1) or XXX1("Fede") or xx1Land(XX1)
     $ifi %crpInputInMrk%==on                or xx1CrpInput(xx1)
                                  )
                           $ (v_prodQuant.lo(RMS,XX1) ne v_prodQuant.up(RMS,XX1))
                           $ DATA(RMS,"Prod",XX1,"CUR"))  ..
           (v_prodQuantNeg(RMS,XX1) $ ( v_prodQuant.LO(RMS,XX1) LE 0)
      +     v_prodQuant(RMS,XX1)    $ ( V_prodQuant.LO(RMS,XX1) GT 0)) / (DATA(RMS,"Prod",XX1,"CUR")+0.1)
            =E= (p_cnstNQSupp(RMS,XX1)
                 + SUM( YY1 $ (DATA(RMS,"PPri",YY1,"CUR") $ (NOT SAMEAS(YY1,"INPE")) $ DATA(RMS,"PROD",YY1,"CUR")),
                                p_hessNQSupp(RMS,XX1,YY1,"CUR")
                              * (v_prodPrice(RMS,YY1)
                                  - DATA(RMS,"PPri",YY1,"CUR") * p_oilCostShare(RMS,YY1) * DATA(RMS,"UVAG","CRDO","PercentageChange")/100
                                  + (DATA(RMS,"PSEd",YY1,"CUR")
                                  +  DATA(RMS,"PSEI",YY1,"CUR")
                                  + DATA(RMS,"AREP",YY1,"CUR")*(1-DATA(RMS,"DECP",YY1,"CUR"))) $ SAMEAS(YY1,"MILK")
     $iftheni.spam15 not %supremaMrk%==on
                                  - DATA(RMS,"PSEd",YY1,"CUR") $  xx1Land(YY1)
     $endif.spam15
                                )/v_prodPrice(RMS,"Inpe")
                       )
                 + SUM( feed_trd $ p_hessNQSupp(RMS,XX1,feed_trd,"Cur"),
                                p_hessNQSupp(RMS,XX1,feed_trd,"CUR")
                              * v_feedBlkPrice(RMS,feed_trd)/v_prodPrice(RMS,"Inpe"))
                              )
                              /(DATA(RMS,"Prod",XX1,"CUR")+0.1);
    """
    import casadi as ca
    ns = HF.shape[1]
    return (ca.mtimes(ca.DM(H), r - 1.0) + ca.DM(np.asarray(hm, float)) * (m - 1.0)
            + (ca.mtimes(ca.DM(HF), fede - 1.0) if ns else 0) + lsh)


def ProdNQ_hess(s0, Hm, dP, extra=None):
    r"""ProdNQ_(RMS, XX1) (l. 1529-1572) of the supply models' products, the row before the floor: s0 + Hm dP (+
    extra), s0 the models' latest output (the constant re-anchored there), Hm (n_x x n_cols) the market supply Hessian
    measured on the models at the baseline, dP the price change against the prices they saw, extra the young animals'
    and raw milk's terms (none: left out). CasADi; Hm numbers. CAPRI's GAMS: ProdNQ_'s docstring."""
    import casadi as ca
    q = s0 + ca.mtimes(ca.DM(Hm), dP)
    return q if extra is None else q + extra


def yaniMarket_(net, H_YP, dP, H_YY, dr, ref, extra=None):
    r"""yaniMarket_(RM, xxOmYani) (l. 1579-1602), the residual of a market region's young-animal markets, net + H_YP
    dP + H_YY dr (+ extra) - ref: net the young animals' net supply at the supply models' latest solution, H_YP
    (n_y x n_cols) and H_YY (n_y x n_y) the Hessian's young-animal rows in the products' price change dP and in the
    young-animal prices' change dr, extra the change from the member states' milk prices (none: left out), ref the
    reference net supply. CasADi; H_YP, H_YY numbers.

    CAPRI's GAMS, yaniMarket_ (l. 1579-1602):

      yaniMarket_(RM,xxOmYani) $ ( sum(RM_TO_RMS(RM,RMSSUP),v_prodPrice.range(RMSSUP,xxOmYAni)) $ XXX(xxOmYani) ) ..
            sum(RM_TO_RMS(RM,RMSSUP),
                 p_cnstNQSupp(RMSSUP,xxOmYani)
                   + sum(YY1 $ (DATA(RMSSUP,"PPri",YY1,"CUR") $ (NOT SAMEAS(YY1,"INPE")) $ DATA(RMSSUP,"PROD",YY1,"CUR")),
                                p_hessNQSupp(RMSSUP,xxOmYani,YY1,"CUR")
                                  * v_prodPrice(RMSSUP,YY1)/v_prodPrice(RMSSUP,"Inpe"))
                 + SUM( feed_trd $ p_hessNQSupp(RMSSUP,xxOmYani,feed_trd,"Cur"),
                                p_hessNQSupp(RMSSUP,xxOmYani,feed_trd,"CUR")
                                  * v_feedBlkPrice(RMSSUP,feed_trd)/v_prodPrice(RMSSUP,"Inpe"))
             )
                  / (sum(RM_TO_RMS(RM,RMSSUP),
                      DATA(RMSSUP,"GROF",xxOmYani,"CUR")
                       +SUM(O_TO_YANI(xxOmYani,IYANI), DATA(RMSSUP,"GROF",IYANI,"CUR")))*0.5 + 1)
               =E=  sum(RM_TO_RMS(RM,RMSSUP),
                     DATA(RMSSUP,"GROF",xxOmYani,"CUR")
                      -SUM(O_TO_YANI(xxOmYani,IYANI), DATA(RMSSUP,"GROF",IYANI,"CUR")))
                  / (sum(RM_TO_RMS(RM,RMSSUP),
                      DATA(RMSSUP,"GROF",xxOmYani,"CUR")
                       +SUM(O_TO_YANI(xxOmYani,IYANI), DATA(RMSSUP,"GROF",IYANI,"CUR")))*0.5 + 1);
    """
    import casadi as ca
    res = net + ca.mtimes(ca.DM(H_YP), dP) + ca.mtimes(ca.DM(H_YY), dr)
    if extra is not None:
        res = res + extra
    return res - ref
