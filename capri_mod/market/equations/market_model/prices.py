r"""CAPRI's price equations (arm/market_model.gms l. 2842-3130, the PRICES block): the import prices (impPrice_), the
two Armington price indexes (arm1PriceAgg_, arm2PriceAgg_), the consumer price (CPri_), the market price of a region
without production (PMrk_) and the average market price of an aggregate policy block (MarketPriceAgg_).

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026, the supply phase); this docstring keeps the block's overview, notation and departures.

Written: CPri_ for the GL demand's goods (capri_mod/market/demand_ad.py gl_block_function); impPrice_'s exporter-price
part and the Armington price indexes in the trade blocks' three forms (NumPy: bilateral.py BilateralCommodity
import_prices, prices; CasADi per region, trade_ad.py _system; CasADi per cell, trade_system_ad.py and
import_prices_ad.py), each calling the elementwise functions with its own arguments, the sums the callers'; PMrk_ in
bilateral.py pmrk_ratios and market_system_ad.py; MarketPriceAgg_'s weights in bilateral.py mpagg_weights (NumPy and
CasADi).

In this project's notation (CPRI0 and ARM1P0 CAPRI's consumer and Armington prices at the calibration point, EUR/kg;
PR the model region's Armington price ratio to it; for the trade blocks r_j the exporter's market price ratio, a_ij
and b_ij the import price's parts proportional to it and fixed, Pd_i = Pd0_i r_i the market price, dd, dm, beta the
share parameters, s1, s2 the substitution elasticities, PA0, Pd0 the Armington and market prices at the calibration
point):

    impPrice_        p_ij = a_ij r_j + b_ij (+ the quotas' and border measures' terms, M5)
    arm2PriceAgg_    PM_i = (sum_j beta_ij p_ij^(1 - s2))^(1 / (1 - s2))
    arm1PriceAgg_    PA_i = (dd_i Pd_i^(1 - s1) + dm_i PM_i^(1 - s1))^(1 / (1 - s1))
    CPri_            p = CPRI0 + (PR - 1) ARM1P0
    PMrk_            r_i = (PA_i + Pd0_i - PA0_i) / Pd0_i   (the regions without production)
    MarketPriceAgg_  P_block = sum_i w_i P_i / sum_i w_i, w_i = 1 + D_i (+ S_i where the region has no use at the
                     calibration point)

CAPRI's consumer price is the Armington price plus the margins (CTAX for the biofuels, CMrg, less the consumer
support CSEd and CSEi), fixed in the simulation; with the Armington price ARM1P0 x PR, that is CPRI0 + (PR - 1) ARM1P0.
CAPRI's producer price (PPri_, l. 3046-3060) is the market price times the calibrated relative margin plus the support
per tonne (PSEi, PSEd, AREP, held; additivePPriMargin off, arm/prep_market.gms l. 258): the model's unknown r is the
market and producer price ratio at once, the support's share of the producer price in ProdNQ_'s parameters (supply.py
_noneu_nq_params: (PPRI0 - support) / INPE).

Departures from CAPRI: the rows unscaled; the margins held at CAPRI's calibration point (CPRI0 - ARM1P0); the model
floors the consumer price at 5% of CPRI0 (demand_ad.py; not in CAPRI); the modified Armington terms (v_gammaCES,
pv_theta) at 1 in the step (armington.py's docstring); impPrice_'s exchange rate factor at 1 (as CAPRI's step,
arm/cal_models.gms l. 357-358) and CAPRI's ad valorem tariff on the market price plus the transport cost in a_ij and
b_ij (a = fob (1 + ta / 100), b = tc (1 + ta / 100) + ts, tools/build/build_bilateral_market.py l. 161, the flows'
averages within a model region); PMrk_'s ratio floored at 1e-3
(the default solve's, bilateral.py; CAPRI's lower bound on the market price); MarketPriceAgg_'s average written in two
forms (NumPy in bilateral.py border_spec, CasADi in import_prices_ad.py), which round differently. The biofuels'
consumer price (capri_mod/market/biofuel_ad.py) is written apart (the biofuel block, M2).
"""
from __future__ import annotations


def CPri_(cpri0, ra, arm1p0):
    r"""CPri_(RMS, XXX) (l. 3032-3038): the consumer price, cpri0 + (ra - 1) x arm1p0 (EUR/kg): CAPRI's consumer price
    at the calibration point moved by the change of the Armington price (ra its ratio, arm1p0 CAPRI's Armington price
    at the calibration point), the margins held.

    CAPRI's GAMS, Cpri_ (l. 3032-3038):

     Cpri_(RMS,XXX) $ ( (DATA(RMS,"HCon",XXX,"CUR") or DATA(RMS,"BIOF",XXX,"CUR") $XXBIOF(XXX)) ) ..
          v_consPrice(RMS,XXX)/(DATA(RMS,"CPRI",XXX,"CUR")+1)
                               =E= SUM(RMS_TO_RM(RMS,RM), v_arm1Price(RM,XXX)
                                 + DATA(RMS,"CTAX",XXX,"CUR") $ XXBIOF(XXX)
                                 + DATA(RMS,"CMrg",XXX,"CUR")
                                 - DATA(RMS,"CSEd",XXX,"CUR")
    """
    return cpri0 + (ra - 1.0) * arm1p0


def impPrice_(a, r, b):
    r"""impPrice_(RM, RM1, XXX) (l. 2849-2910), the import price's part in the exporter's market price: a r + b, a the
    part proportional to the exporter's market price ratio r (the market price with the ad valorem tariff and the
    exchange rate), b the fixed part (transport cost, specific tariffs, the quotas' base terms). Elementwise. The
    quotas' and border measures' terms are added by the callers (M5).

    CAPRI's GAMS, impPrice_ (l. 2849-2910):

      impPrice_(RM,RM1,XXX) $ ((p_tradeFlows(RM,RM1,XXX,"CUR") or p_arm2Commit(rm,rm1,xxx)) $ (not SAMEAS(RM,RM1))) ..
          v_impPrice(RM,RM1,XXX)/(p_impPrice(RM,RM1,XXX,"CUR")+1)   =E=
      {
            [v_marketPrice(RM1,XXX)
            + v_transpCost(RM,RM1,XXX)
            - sum(RM_TO_RMTP(rm1,rmtp1), v_perUnitExportSub(RMtp1,XXX)  $ ( (DATA(RMtp1,"PADM",XXX,"CUR") gt eps) $ (DATA(RMtp1,"FEOE_max",XXX,"CUR") GT eps)
                                    $ (NOT sum(RM1_TO_RMTP(rm,rmtp)  , p_doubleZero(RMtp,RMtp1,XXX,"CUR") )))
     							   + p_trqGlobl(RMTP1,XXX,"CarbBordEx","Cur")
     							   )
                 ] * p_exchgRateChangeFactor(RM,RM1)
               *  [ 1. + 0.01 * sum( (rmtp,rmtp1) $ (RM_TO_RMTP(rm,rmtp) $ RM_TO_RMTP(rm1,rmtp1)), v_tarAdVal(RMTP,RMTP1,XXX)
                                                            $ ( (NOT  p_doubleZero(RMTP,RMTP1,XXX,"CUR")) $ (NOT SAMEAS(RMTP,RMTP1))))]
               +  [
                   sum((RM_TO_RMTP(rm,rmtp),RM1_TO_RMTP(rm1,rmtp1)), v_tarSpec(RMTP,RMTP1,XXX)
                                                             $ (   (DATA(RMTP,"MinBordP",XXX,"CUR") LE eps)
                                                                or (p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR") eq prohibitive) ))
                   +  sum((RM_TO_RMTP(rm,rmtp),RM1_TO_RMTP(rm1,rmtp1)), v_flexLevy(RMTP,RMTP1,XXX)
                                                             $ (   (DATA(RMtp,"MinBordP",XXX,"CUR") GT eps)
                                                                 $ (p_trqBilat(RMtp,RMtp1,XXX,"TrqNT","CUR") ne prohibitive) ))
                   ] $ [ (NOT sum((RM_TO_RMTP(rm,rmtp),RM1_TO_RMTP(rm1,rmtp1)),p_doubleZero(RMTP,RMTP1,XXX,"CUR")))
                                                  $ (not same_pblock(rm,rm1))]
               +    sum((RM_TO_RMTP(rm,rmtp),RM1_TO_RMTP(rm1,rmtp1)), p_trqBilat(RMTP,RMTP1,XXX,"CarbBordAd","CUR"))
      }
                       /(p_impPrice(RM,RM1,XXX,"CUR")+1) ;
    """
    return a * r + b


def arm2PriceAgg_term(beta, p, s2):
    r"""arm2PriceAgg_(RM, XXX) (l. 3004-3028), one import flow's term of the import aggregate's price index: beta
    p^(1 - s2). Elementwise. CAPRI's GAMS: arm2PriceAgg_'s docstring."""
    return beta * p ** (1.0 - s2)


def arm2PriceAgg_(pm, s2):
    r"""arm2PriceAgg_(RM, XXX) (l. 3004-3028): the import aggregate's price from the sum of its terms pm
    (arm2PriceAgg_term), pm^(1 / (1 - s2)) (v_gammaCES and pv_theta at 1). Elementwise.

    CAPRI's GAMS, arm2PriceAgg_ (l. 3004-3028):

      arm2PriceAgg_(RM,XXX) $ ( (v_Arm2Val.lo(RM,XXX) ne v_Arm2Val.up(RM,XXX))
                              $ (sum(RM1 $ ( (p_tradeFlows(RM,RM1,XXX,"Cur") or p_arm2Commit(rm,rm1,xxx))
                                           $ (not SAMEAS(RM,RM1)) $ p_dpCesTrade(RM,RM1,XXX) ),
                                     p_dpCesTrade(RM,RM1,XXX) * (( v_impPrice.l(RM,RM1,XXX)       $ (NOT NonZeroFixedImportFlow(RM,RM1,XXX))
                                                                 + v_impShadowPrice.l(RM,RM1,XXX) $ (    NonZeroFixedImportFlow(RM,RM1,XXX)) )
                                                                  /(data(RM,"Arm2P",XXX,"CUR")+1)) ** (1-p_rhoArm2(RM,XXX)) ))
                              )..
          v_arm2Price(RM,XXX) / (data(RM,"Arm2P",XXX,"CUR")+1) =E=
          (1 / v_gammaCES(rm, xxx)) *
          sum(RM1 $ ((p_tradeFlows(RM,RM1,XXX,"Cur") or p_arm2Commit(rm,rm1,xxx)) $ (not SAMEAS(RM,RM1)) $  p_dpCesTrade(RM,RM1,XXX)),
                  (pv_theta(rm, rm1, xxx)**(p_rhoArm2(rm, xxx) - 1)) *
                  p_dpCesTrade(RM,RM1,XXX) * ((   v_impPrice(RM,RM1,XXX)       $ (NOT NonZeroFixedImportFlow(RM,RM1,XXX))
                                          +   v_impShadowPrice(RM,RM1,XXX) $ (    NonZeroFixedImportFlow(RM,RM1,XXX)) )
                                         /(data(RM,"Arm2P",XXX,"CUR")+1)   ) ** (1-p_rhoArm2(RM,XXX))
             ) ** (1/(1-p_rhoArm2(RM,XXX)));
    """
    return pm ** (1.0 / (1.0 - s2))


def arm1PriceAgg_term(d, P, s1):
    r"""arm1PriceAgg_(RM, XXX) (l. 2950-2956), one nest's term of the Armington price index: d P^(1 - s1) (d the
    domestic sales' or the import aggregate's share parameter, P the market or the import aggregate's price).
    Elementwise. CAPRI's GAMS: arm1PriceAgg_'s docstring."""
    return d * P ** (1.0 - s1)


def arm1PriceAgg_(pa, s1):
    r"""arm1PriceAgg_(RM, XXX) (l. 2950-2956): the Armington price from the sum of its terms pa (arm1PriceAgg_term),
    pa^(1 / (1 - s1)). Elementwise.

    CAPRI's GAMS, arm1PriceAgg_ (l. 2950-2956):

      arm1PriceAgg_(RM,XXX) $ ( (v_domSales.up(RM,XXX) ne 0) or (v_Arm2Quant.up(RM,XXX) ne 0) )..
          v_arm1Price(RM,XXX) / (data(RM,"Arm1P",XXX,"CUR")+1) =E=
            (  (p_dpCesTrade(RM,RM,XXX)   * (v_marketPrice(RM,XXX)/ (data(RM,"Arm1P",XXX,"CUR")+1)) ** (1-p_rhoArm1(RM,XXX))) $ p_dpCesTrade(RM,RM,XXX)
             + (p_dpCesTrade(RM,"RW",XXX) * (v_arm2Price(RM,XXX)  / (data(RM,"Arm1P",XXX,"CUR")+1)) ** (1-p_rhoArm1(RM,XXX))) $ p_dpCesTrade(RM,"RW",XXX)
             ) ** (1/(1-p_rhoArm1(RM,XXX)));
    """
    return pa ** (1.0 / (1.0 - s1))


def PMrk_(PA, Pd0, PA0):
    r"""PMrk_(RM, XXX) (l. 3074-3080): the market price ratio of a region without production, (PA + Pd0 - PA0) /
    Pd0: its Armington price PA (EUR/t) plus the margin calibrated at the calibration point (CAPRI's DATA PMrkMrg =
    PMrk - arm1P, arm/data_fit.gms l. 955). Elementwise.

    CAPRI's GAMS, PMrk_ (l. 3074-3080):

       PMrk_(RM,XXX)  $ (  (NOT v_prodQuant.UP(RM,XXX))
                        or (not (v_domSales.range(RM,XXX) or v_prodQuant.range(RM,XXX) or DATA(RM,"Exports",XXX,"CUR")))) ..
           v_marketPrice(RM,XXX)/(DATA(RM,"PMrk",XXX,"CUR")+1)
                =E= ( v_arm1Price(RM,XXX) + DATA(RM,"PMrkMrg",XXX,"CUR") $ (NOT v_prodQuant.UP(RM,XXX)))
                    /(DATA(RM,"PMrk",XXX,"CUR")+1);
    """
    return (PA + Pd0 - PA0) / Pd0


def MarketPriceAgg_weights(S, D, nod):
    r"""MarketPriceAgg_(RMTP, XXX) (l. 3088-3100), the weights of an aggregate block's average market price: 1 + D_i
    (+ S_i where nod_i, the region without use at the calibration point), per region; S, D NumPy arrays or CasADi
    expressions. A list.

    CAPRI's GAMS, MarketPriceAgg_ (l. 3088-3100):

     MarketPriceAgg_(RMTP,XXX) $ { (not xxOmYani(XXX))
                                 $ SUM(RM $  RMTP_TO_RM(RMTP,RM),  v_marketPrice.range(RM,XXX) )
                                 $ [ SUM(RM $  RMTP_TO_RM(RMTP,RM),  (v_Arm1Quant.UP(RM,XXX) gt eps) )
                                   + SUM(RM $  RMTP_TO_RM(RMTP,RM),  (v_prodQuant.UP(RM,XXX) gt eps) ) ]
                                 $ RMTPagg(RMTP)
                                 }..
           v_marketPrice(RMTP,XXX)  =E=
             {  SUM[RMTP_TO_RM(RMTP,RM),
                   v_marketPrice(RM,XXX) * (1 + v_Arm1Quant(RM,XXX) + v_prodQuant(rm,xxx) $ (not DATA(RM,"ARM1",XXX,"CUR")))]
             /  SUM[RMTP_TO_RM(RMTP,RM),    1 + v_Arm1Quant(RM,XXX) + v_prodQuant(rm,xxx) $ (not DATA(RM,"ARM1",XXX,"CUR"))] } ;
    """
    return [1.0 + D[i] + (S[i] if nod[i] else 0.0) for i in range(len(nod))]
