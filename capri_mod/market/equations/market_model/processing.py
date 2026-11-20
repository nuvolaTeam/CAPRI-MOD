r"""CAPRI's processing equations (arm/market_model.gms l. 1115-1179 and 1440-1523, of the behavioural functions): the
oilseeds' crushing margin (ProcMargO_), the normalised quadratic processing (ProcNQ_) made positive (ProcFudge_), the
oils' and cakes' output (ProcO_) at the CET yields (procYield_), and the residual feeds of milling and processing
(MaprFeed_).

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026, the supply phase); this docstring keeps the block's overview, notation and departures.

Written: the crushing chain and the other products' processing of the market's CasADi blocks
(capri_mod/market/processing_ad.py crush_function, proc_nq_function; the dairy block's processing, dairy_ad.py, uses
ProcFudge_), and the residual feeds' output (capri_mod/market/feed.py eu_feed_byproduct_output, use_ad.py). The
whole-market system's lifted processing cells carry their own fudge (market_system_ad.py, supply_system_ad.prod_fudge):
the assembled system's form (M3, M4).

In this project's notation, per behavioural region and seed s with oil o and cake c (r the price ratios to the
calibration point: r_s the seed's Armington ratio, r_o, r_c the oil's and cake's producer ratios; a1, ppo, ppc
CAPRI's prices at the calibration point, yo0, yc0 its yields, rho the CET parameter):

    procYield_  A_o = yo0 exp(rho l), A_c = yc0 exp(-rho l), l = log(((ppo r_o + 1e-3) / (ppo + 1e-3)) / ((ppc r_c
                + 1e-3) / (ppc + 1e-3))); with the mass correction solved, y_o = A_o + (S0 - T) / 2, y_c = A_c + (S0 - T)
                / 2, S0 = yo0 + yc0, T = (A_o + A_c + S0) / 2
    ProcMargO_  m = -a1 r_s + ppo r_o y_o + ppc r_c y_c
    ProcNQ_     q = q0 + sum_y h_y (m_y - m0_y) (the seeds), q = q0 - sum_y h_y (r_y - 1) (the other products)
    ProcFudge_  q + z log(1 + exp(-q / z)) + 1e-11, z = 0.01 min(1000, max(1e-11, q0))
    ProcO_      oil = q y_o, cake = q y_c
    MaprFeed_   prod = prod0 sum_c w_c u_c / u0_c       (the parents' food and processing or biofuel use)

Departures from CAPRI: the rows unscaled (CAPRI divides by their calibration values + 0.1 or + 1); ProcNQ_'s Hessian
terms on the price ratios (CAPRI's on the prices normalised by the INPE price, which the model holds); procYield_'s
implicit mass correction solved in closed form (the same solution); ProcFudge_ written as CAPRI's ncpcm (the smooth
max) evaluated with NumPy's logaddexp (max(0, u) + log1p(exp(-|u|)), u = -q / z); MaprFeed_ with CAPRI's constant
by-product share written as the parents' use ratio (prod / prod0 = sum_c w_c u_c / u0_c, w the parents' base shares).
"""
from __future__ import annotations


def ProcMargO_(a1, r_s, ppo, r_o, y_o, ppc, r_c, y_c):
    r"""ProcMargO_(RMS, SED) (l. 1118-1136): the crushing margin of an oilseed, the oil's and cake's value per t of
    seed less the seed's price, -a1 r_s + ppo r_o y_o + ppc r_c y_c (EUR/t; prices as CAPRI's calibration prices x the
    ratios).

    CAPRI's GAMS, ProcMargO_ (l. 1118-1136):

     ProcMargO_(RMS,SED) $ (
                                 (v_procMarg.LO(RMS,SED) NE v_procMarg.UP(RMS,SED))
                              $  (    SUM( SED_TO_CAK(SED,CAK), DATA(RMS,"Prod",CAK,"CUR"))
                                   or SUM( SED_TO_OIL(SED,OIL), DATA(RMS,"Prod",OIL,"CUR")))
                              $ DATA(RMS,"Proc",SED,"CUR")
                              $ XXX(SED)) ..
    *
         v_procMarg(RMS,SED)/(DATA(RMS,"PPRI",SED,"CUR")+1) =E=
             (SUM(RMS_TO_RM(RMS,RM), -v_Arm1Price(RM,SED))
             + SUM( SED_TO_CAK(SED,CAK) $ DATA(RMS,"Prod",CAK,"CUR"),
                       v_prodPrice(RMS,CAK) * (   (v_prodQuant(RMS,CAK)/v_procQuant(RMS,SED)) $ p_trim
                                                +  v_procYield(RMS,CAK)                      $ (NOT p_trim)))
             + SUM( SED_TO_OIL(SED,OIL) $ DATA(RMS,"Prod",OIL,"CUR"),
                       v_prodPrice(RMS,OIL) * (   (v_prodQuant(RMS,OIL)/v_procQuant(RMS,SED)) $ p_trim
                                                 +  v_procYield(RMS,OIL)                      $ (NOT p_trim))))
                           /(DATA(RMS,"PPRI",SED,"CUR")+1);
    """
    return -a1 * r_s + ppo * r_o * y_o + ppc * r_c * y_c


def ProcNQ_margin(q, h, m, m0):
    r"""ProcNQ_(RMS, SED) (l. 1140-1152), one term of an oilseed's crush: q + h (m - m0), h CAPRI's Hessian term on the
    margin of seed y (p_hessNQProc / PPri(INPE)), m its margin now and m0 at the calibration point (ProcMargO_).

    CAPRI's GAMS, ProcNQ_ (l. 1140-1152):

     ProcNQ_(RMS,XXX) $ ( (v_procQuant.lo(RMS,XXX) ne v_procQuant.UP(RMS,XXX)) $ DATA(RMS,"Proc",XXX,"CUR") ) ..
          (v_procQuantNeg(RMS,XXX) $ ( v_procQuant.LO(RMS,XXX) LE 0)
     +     v_procQuant(RMS,XXX)    $ ( v_procQuant.LO(RMS,XXX) GT 0)) / (DATA(RMS,"Proc",XXX,"CUR")+0.1)
          =E= (p_cnstNQProc(RMS,XXX)
              + SUM( YY $ p_hessNQProc(RMS,XXX,YY,"CUR"),
                      p_hessNQProc(RMS,XXX,YY,"CUR")
                         * (  v_procMarg(RMS,YY)  $ SED(YY)
                            - SUM(RMS_TO_RM(RMS,RM),  v_arm1Price(RM,YY) $ (NOT SED(YY))
                                                    - DATA(RMS,"PRCA",YY,"CUR"))))/DATA(RMS,"PPri","Inpe","CUR"))
                                                                    / (DATA(RMS,"Proc",XXX,"CUR")+0.1);
    """
    return q + h * (m - m0)


def ProcNQ_price(dq, h, r):
    r"""ProcNQ_(RMS, XXX) (l. 1140-1152), one term of a product's processing change: dq - h (r - 1), h CAPRI's
    Hessian term on the Armington price of y (the model's, on its ratio r). CAPRI's GAMS: ProcNQ_margin's docstring."""
    return dq - h * (r - 1.0)


def ProcFudge_(q, q0):
    r"""ProcFudge_(RMS, XXX) (l. 1158-1163): CAPRI's smooth max(q, 0), q + z (max(0, u) + log1p(exp(-|u|))) + 1e-11,
    u = -q / z, z = 0.01 min(1000, max(1e-11, q0)) (q0 the processing at the calibration point: a number or a CasADi
    expression). CasADi.

    CAPRI's GAMS, ProcFudge_ (l. 1158-1163):

     ProcFudge_(RMS,XXX) $ (      (v_procQuant.lo(RMS,XXX) LE 0)
                              $ (v_procQuant.lo(RMS,XXX) ne v_procQuant.UP(RMS,XXX)) $ DATA(RMS,"Proc",XXX,"CUR")) ..
         v_procQuant(RMS,XXX)/(abs(DATA(RMS,"Proc",XXX,"CUR"))+0.1)
            =E=  (-ncpcm(-v_procQuantNeg(RMS,XXX),0,1.E-2*min(1000,max(1.E-11,data(RMS,"Proc",XXX,"CUR")))) + 1.E-11)
                 /(abs(DATA(RMS,"Proc",XXX,"CUR"))+0.1);
    """
    import casadi as ca
    if isinstance(q0, (int, float)):
        z = 0.01 * min(1000.0, max(1e-11, float(q0)))
    else:
        z = 0.01 * ca.fmin(1000.0, ca.fmax(1e-11, q0))
    u = -q / z
    return q + z * (ca.fmax(0.0, u) + ca.log1p(ca.exp(-ca.fabs(u)))) + 1e-11


def ProcO_(q, y):
    r"""ProcO_(RMS, XXX) (l. 1168-1177): an oil's or cake's output from the crush q, q x its yield y (procYield_).

    CAPRI's GAMS, ProcO_ (l. 1168-1177):

     ProcO_(RMS,XXX) $ (   SUM(SED $ ( SED_TO_CAK(SED,XXX) OR SED_TO_OIL(SED,XXX)),
                                  DATA(RMS,"Proc",SED,"CUR")*DATA(RMS,"PrcY",XXX,"CUR"))
                                $   (v_prodQuant.lo(RMS,XXX) ne v_prodQuant.up(RMS,XXX))
                                $ (CAK(XXX) or OIL(XXX))
                                $   DATA(RMS,"Prod",XXX,"CUR")) ..
         v_prodQuant(RMS,XXX) / (DATA(RMS,"Prod",XXX,"CUR")+0.1)
            =E= SUM(SED $ ( SED_TO_CAK(SED,XXX) OR SED_TO_OIL(SED,XXX)),
                                                                   v_procQuant(RMS,SED) * v_procYield(RMS,XXX))
                              / (DATA(RMS,"Prod",XXX,"CUR")+0.1);
    """
    return q * y


def procYield_(e, ro, rc):
    r"""procYield_(RMS, XXX) (l. 1480-1521) in simulation, the oil's and cake's yields of one behavioural region at
    the oil's and cake's price ratios ro, rc: CAPRI's CET yields with the mass correction solved (the module's
    docstring); e the region's ppo, ppc (prices), yo0, yc0 (yields at the calibration point) and rho. CasADi.
    Returns (y_o, y_c).

    CAPRI's GAMS, procYield_ (l. 1480-1521):

     procYield_(RMS,XXX) $ (
                             SUM(SED $ ( SED_TO_CAK(SED,XXX) OR SED_TO_OIL(SED,XXX)),
                                              DATA(RMS,"Proc",SED,"CUR")*DATA(RMS,"Prod",XXX,"CUR"))
                             $ ((v_procYield.LO(RMS,XXX) ne v_procYield.UP(RMS,XXX)) or p_trim)
                             $ DATA(RMS,"Prod",XXX,"CUR")
                             $ (CAK(XXX) or OIL(XXX))) ..
         v_procYield(RMS,XXX)
              =E=
    *
    *              --- Define processing yield consistent during calibration of market balances
    *                  from consistent output of cake / oild and processing quantity of seed
    *
    *
                   SUM(SED $ (SED_TO_CAK(SED,XXX) OR SED_TO_OIL(SED,XXX)),
                                                      v_prodQuant(RMS,XXX)/v_procQuant(RMS,SED)) $ p_trim
                +  [
    *
    *               --- Yield of oil in simulation: derived from CET technology
    *
                    +  DATA(RMS,"PrcY",XXX,"CUR") * SUM(SED_TO_CAK(SED,CAK) $ SED_TO_OIL(SED,XXX),
                            EXP( p_rhoProc(RMS,SED) * log (  ((v_prodPrice(RMS,XXX)+1.E-3)/(DATA(RMS,"PPri",XXX,"CUR")+1.E-3))
                                                            /((v_prodPrice(RMS,CAK)+1.E-3)/(DATA(RMS,"PPri",CAK,"CUR")+1.E-3)))))
    *
    *               --- Yield of cake in simulation: derived from CET technology
    *
                    +  DATA(RMS,"PrcY",XXX,"CUR") * SUM(SED_TO_OIL(SED,OIL) $ SED_TO_CAK(SED,XXX),
                            EXP( p_rhoProc(RMS,SED) * log (  ((v_prodPrice(RMS,XXX)+1.E-3)/(DATA(RMS,"PPri",XXX,"CUR")+1.E-3))
                                                            /((v_prodPrice(RMS,OIL)+1.E-3)/(DATA(RMS,"PPri",OIL,"CUR")+1.E-3)))))
    *
    *               --- correct to keep mass flow balance
    *                   (if the sum of the simulated processing yields exceed the
    *                    per unit output of cake and oil in the calibration point,
    *                    correct both by 50% of error)
    *
                    + SUM((SED,YYY) $ (  (SED_TO_CAK(SED,YYY) or SED_TO_OIL(SED,YYY))
                                       $ (SED_TO_CAK(SED,XXX) or SED_TO_OIL(SED,XXX))),
                                 DATA(RMS,"PrcY",YYY,"CUR")-v_procYield(RMS,YYY))/2
                   ] $ (not p_trim);
    """
    import casadi as ca
    po, pc = e["ppo"] * ro, e["ppc"] * rc
    lo = ca.log(((po + 1e-3) / (e["ppo"] + 1e-3)) / ((pc + 1e-3) / (e["ppc"] + 1e-3)))
    Ao = e["yo0"] * ca.exp(e["rho"] * lo)
    Ac = e["yc0"] * ca.exp(-e["rho"] * lo)
    S0 = e["yo0"] + e["yc0"]
    T = (Ao + Ac + S0) / 2.0
    return Ao + (S0 - T) / 2.0, Ac + (S0 - T) / 2.0


def MaprFeed_(prod0, x):
    r"""MaprFeed_(RMSSUP, RESIMPX) (l. 1442-1452): a residual feed's output (FENI, FPRI), its output at the calibration
    point x x, the parents' weighted use ratio (sum_c w_c u_c / u0_c: food and processing, or biofuel processing).

    CAPRI's GAMS, MaprFeed_ (l. 1442-1452):

      MaprFeed_(RMSSUP,RESIMPX) $ ( SUM(SAMEAS(XX,RESIMPX),1)
                                    $ (v_prodQuant.lo(RMSSUP,RESIMPX) ne v_prodQuant.up(RMSSUP,RESIMPX))
                                    $ DATA(RMSSUP,"Prod",RESIMPX,"CUR")) ..
         v_prodQuant(RMSSUP,RESIMPX) / (DATA(RMSSUP,"Prod",RESIMPX,"CUR")+0.1)
              =E= (SUM(RESIMP_T_O(RESIMPX,XX),
                          v_consQuant(RMSSUP,XX) $ DATA(RMSSUP,"HCon",XX,"CUR")
                        + v_procQuant(RMSSUP,XX) $ DATA(RMSSUP,"Proc",XX,"CUR")
                        + v_biofProcQuant(RMSSUP,XX) $ (DATA(RMSSUP,"Biof",XX,"CUR") $ SAMEAS(XX,"SUGA")))
                                * p_feedByProdShare(RMSSUP,RESIMPX)
                                               ) / (DATA(RMSSUP,"Prod",RESIMPX,"CUR")+0.1);
    """
    return prod0 * x
