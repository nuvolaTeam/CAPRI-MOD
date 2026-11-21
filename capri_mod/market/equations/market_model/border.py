r"""CAPRI's policy representation at the border (arm/market_model.gms l. 3131-3488): the tariff-rate quotas (the
quota's sigmoid trqSigmoidFunc_, the global quota's imports TRQImports_, the tariffs under the quotas tarAdVal_,
tarSpec_, tarAdValW_, tarSpecW_), the entry prices of fruit and vegetables (EntryPriceDriver_, tarSpecIfEntryPrice_,
prefTriggerPrice_) and the flexible levies of the cereals (FlexLevyNotCut_, FlexLevy_).

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026, the supply phase); this docstring keeps the block's overview, notation and departures.

Written: the trade blocks' border measures in their two forms, NumPy (capri_mod/market/bilateral.py
BilateralCommodity: _sig, _trq_rates, border_spec, and _TrqCells, the quotas' trials) and CasADi (import_prices_ad.py
_rates, import_price_function; trade_ad.py trade_trq_function; trade_system_ad.py). The functions of plain arithmetic
serve both forms; where the operations differ (exp, min, abs, clip) the CasADi function has a NumPy twin (_np), and
CAPRI's smoothed minimum ncpcm is an argument (bilateral.py's NumPy logaddexp form, import_prices_ad.py's CasADi
form). The policy blocks are written in shift form: CAPRI's import price at the base flows plus the change of the
rates from their base value (docs/dev/MARKET_TRQ_PORT.md).

In this project's notation, per quota (s its sigma, f its fill over its volume Q, the slope 200 of CAPRI's
p_trqSigmoidSlope, mid 0.97; pref and MFN the preferential and the out-of-quota rates, d = MFN - pref) and per flow
under a border measure (cif the exporter's market price plus the transport cost, TriggerP the trigger price, E the
entry price, fac CAPRI's p_entryPriceFac, TARS the bound specific tariff, MinBordP the minimum border price, z = 1e-3
MinBordP):

    trqSigmoidFunc_       s = 1 / (1 + exp(-clip(slope (f - mid))))   (global quotas: f the TRQImports_ over Q)
    TRQImports_           the cover's flows + sum over the bilateral quotas of -ncpcm(-(fill - Q), 0, 1e-3 Q)
    tarAdVal_, tarSpec_   pref + d s, the smaller of it and the global quota's rate by ncpcm (max(1e-2, 1e-3 |d|),
                          specific max(1e-5, 1e-7 |d|))
    tarAdValW_, tarSpecW_ pref + d s of the global quota
    prefTriggerPrice_     E = PrefTrigPrice + (TriggerP - PrefTrigPrice) s
    EntryPriceDriver_     dr = (E 0.95 - cif) / TriggerP x fac
    tarSpecIfEntryPrice_  tariff = exp(min(0, dr)) / (1 + 20 exp(-|dr|)) x TARS (or TsPref)
    FlexLevyNotCut_       -ncpcm(-(MinBordP - cif), 0, z)
    FlexLevy_             ncpcm(not cut, TARS or the quota's rate, z)

Departures from CAPRI: the rows unscaled; the sigmoid's argument slope (f - 0.97) with f = fill / Q (CAPRI's slope /
Q (fill - 0.97 Q), equal in exact arithmetic) clipped at +-60 against exp's overflow; the rates in shift form
(the change from their base value added to the import price at the base flows); the ad valorem rate's base the
exporter's market price plus the transport cost (impPrice_); the quotas solved by bisection on sigma in the default
solve (bilateral.py trq_solve; CAPRI's simultaneous solve; the assembled system has them as equations); the levy
replaces the specific tariff of its flow (border_spec); the trigger price the entry price's divisor where it is
positive (1 otherwise). TRQImports_ is written as the sums of its callers (bilateral.py trq_global_imports, NumPy;
trade_system_ad.py, CasADi). The quotas' diagnostics (bilateral.py trq_arguments, trq_equation_gap) write the
sigmoid once more.
"""
from __future__ import annotations

import numpy as np


def trqSigmoidFunc_(f, slope, mid, clip):
    r"""trqSigmoidFunc_(RMTP, RMTP1, XXX) (l. 3275-3284): a quota's sigma at its fill f over the volume,
    1 / (1 + exp(-a)), a = slope (f - mid) clipped to [-clip, clip]. CasADi (the global quotas' sigmoid of tarSpecW_
    and tarAdValW_ too, f their TRQImports_ over the volume).

    CAPRI's GAMS, trqSigmoidFunc_ (l. 3275-3284):

      trqSigmoidFunc_(RMTP,RMTP1,XXX) $
                  {
                    [ (p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR") GT eps) $ (p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR") NE 1.E+10)
                      $ (p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR") NE prohibitive) $ (p_tradeFlows(RMTP,RMTP1,XXX,"CUR") or p_arm2Commit(RMTP,RMTP1,xxx))]
                  } ..
              v_trqSigmoidFunc(RMTP,RMTP1,XXX) =E= Sigmoid(p_trqSigmoidSlope(RMTP,XXX)/p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR")
                                                        * (v_tradeFlows(RMTP,RMTP1,XXX)-p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR")*0.97));
    """
    import casadi as ca
    arg = ca.fmin(ca.fmax(slope * (f - mid), -clip), clip)
    return 1.0 / (1.0 + ca.exp(-arg))


def trqSigmoidFunc_np(f, slope, mid, clip):
    r"""trqSigmoidFunc_ (l. 3275-3284) in NumPy: 1 / (1 + exp(-clip(slope (f - mid), -clip, clip))). CAPRI's GAMS:
    trqSigmoidFunc_'s docstring."""
    return 1.0 / (1.0 + np.exp(-np.clip(slope * (f - mid), -clip, clip)))


def tarAdVal_(ta_pref, dta, s):
    r"""tarAdVal_(RMTP, RMTP1, XXX) (l. 3417-3470), a bilateral quota's ad valorem rate (points): ta_pref + dta s,
    dta the out-of-quota rate less the preferential one. Elementwise.

    CAPRI's GAMS, tarAdVal_ (l. 3417-3470):

      tarAdval_(RMTP,RMTP1,XXX) $ (  ((v_tarAdval.LO(RMTP,RMTP1,XXX) NE v_tarAdval.up(RMTP,RMTP1,XXX)) or p_trim)
                                 $   (( ( (p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR") GT eps) $ (p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR") NE 1.E+10))
                                      $ (p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR") NE prohibitive)
                                      $ ( ((p_trqBilat(RMTP,RMTP1,XXX,"TaMFN","CUR") gt eps) OR (p_trqBilat(RMTP,RMTP1,XXX,"TaPref","CUR") gt eps))
                                         $ (p_trqBilat(RMTP,RMTP1,XXX,"TaMFN","CUR") ne p_trqBilat(RMTP,RMTP1,XXX,"TaPref","CUR")) )
                                      $ ( not (p_trqBilat(RMTP,RMTP1,XXX,"PrefTrigPrice","CUR") gt EPS)) )
                                   or ( (p_trqGlobl(RMTP,XXX,"TrqNT","CUR") gt eps) $ (p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR") NE 1.E+10)
                                       $ (p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR") NE prohibitive)
                                       $ (NOT p_doubleZero(RMTP,RMTP1,XXX,"CUR"))
                                       $ ( (p_trqGlobl(RMTP,XXX,"TaMFN","CUR") gt eps)    OR (p_trqGlobl(RMTP,XXX,"TaPref","CUR") gt eps))    ))
                                 $   (not Sameas(RMTP,RMTP1)) $ (p_tradeFlows(RMTP,RMTP1,XXX,"CUR") or p_arm2Commit(RMTP,RMTP1,xxx))) ..
              v_tarAdval(RMTP,RMTP1,XXX)/100 =E=
              ((    ncpcm( v_tarAdVal(RMTP,"RW",XXX),
                   p_trqBilat(RMTP,RMTP1,XXX,"TaPref","CUR")
                + (p_trqBilat(RMTP,RMTP1,XXX,"TaMFN","CUR")-p_trqBilat(RMTP,RMTP1,XXX,"TaPref","CUR"))
                    * v_trqSigmoidFunc(RMTP,RMTP1,XXX),max(1.E-2,1.E-3*abs(p_trqBilat(RMTP,RMTP1,XXX,"TaMFN","CUR")
                                                                          -p_trqBilat(RMTP,RMTP1,XXX,"TaPref","CUR")))))
                             $ (   (p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR") gt eps)
                                 $ (p_trqGlobl(RMTP,XXX,"TrqNt","CUR") gt eps)
                                 $ ( (p_trqGlobl(RMTP,XXX,"TaPref","CUR") gt eps) or  (p_trqGlobl(RMTP,XXX,"TaMFN","CUR") gt eps)))
            + (
                   p_trqBilat(RMTP,RMTP1,XXX,"TaPref","CUR")
                + (p_trqBilat(RMTP,RMTP1,XXX,"TaMFN","CUR")-p_trqBilat(RMTP,RMTP1,XXX,"TaPref","CUR"))
                    * v_trqSigmoidFunc(RMTP,RMTP1,XXX))
                           $  (    (p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR") gt eps)
                                $  (    (p_trqGlobl(RMTP,XXX,"TrqNt","CUR") le eps)
                                    or  ( (p_trqGlobl(RMTP,XXX,"TaPref","CUR") le eps) $ (p_trqGlobl(RMTP,XXX,"TaMFN","CUR") le eps))))
            + v_tarAdval(RMTP,"RW",XXX) $ ( (p_trqGlobl(RMTP,XXX,"TrqNt","CUR") gt eps) $ (p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR") le eps)))/100
             ;
    """
    return ta_pref + dta * s


def tarAdVal_min(tw, tb, dta, ncpcm):
    r"""tarAdVal_ (l. 3417-3470) where the importer has a global quota too: the smaller of the global rate tw and the
    bilateral tb, ncpcm(tw, tb, max(1e-2, 1e-3 |dta|)); ncpcm the caller's form of CAPRI's smoothed minimum. CAPRI's
    GAMS: tarAdVal_'s docstring."""
    return ncpcm(tw, tb, max(1e-2, 1e-3 * abs(dta)))


def tarSpec_(ts_pref, dts, s):
    r"""tarSpec_(RMTP, RMTP1, XXX) (l. 3292-3363), a bilateral quota's specific rate (EUR/t): ts_pref + dts s.
    Elementwise.

    CAPRI's GAMS, tarSpec_ (l. 3292-3363):

      tarSpec_(RMTP,RMTP1,XXX) $ ( ((v_tarSpec.LO(RMTP,RMTP1,XXX) NE v_tarSpec.up(RMTP,RMTP1,XXX)) or p_trim) $
             ((       ( (p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR") GT eps) $ (p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR") NE 1.E+10))
                   $ (p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR") NE prohibitive)
                  $   (       ( (p_trqBilat(RMTP,RMTP1,XXX,"TsMFN","CUR") gt EPS) OR (p_trqBilat(RMTP,RMTP1,XXX,"TsPref","CUR") gt eps))
                             $ (p_trqBilat(RMTP,RMTP1,XXX,"TsMFN","CUR") ne p_trqBilat(RMTP,RMTP1,XXX,"TsPref","CUR"))
                             $ (DATA(RMTP,"TriggerP",XXX,"CUR") le eps) ) )
                or ( (p_trqGlobl(RMTP,XXX,"TrqNT","CUR") gt eps) $ (p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR") NE 1.E+10)
                    $ (p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR") NE prohibitive)
                    $ (NOT p_doubleZero(RMTP,RMTP1,XXX,"CUR")) $ (DATA(RMTP,"TriggerP",XXX,"CUR") le eps)
                    $ ( (p_trqGlobl(RMTP,XXX,"TsMFN","CUR") gt eps)  OR (p_trqGlobl(RMTP,XXX,"TsPref","CUR") gt eps )))
              )
                     $ (not Sameas(RMTP,RMTP1)) $ (p_tradeFlows(RMTP,RMTP1,XXX,"CUR") or p_arm2Commit(RMTP,RMTP1,xxx))) ..
                 v_tarSpec(RMTP,RMTP1,XXX)
              /(   MAX(p_trqBilat(RMTP,RMTP1,XXX,"TsMFN","CUR"),p_trqBilat(RMTP,RMTP1,XXX,"TsPref","CUR"))
                 + MAX(p_trqGlobl(RMTP,XXX,"TsMFN","CUR"),p_trqGlobl(RMTP,XXX,"TsPref","CUR")))
              =E=
             (
            + (    ncpcm(   v_tarSpec(RMTP,"RW",XXX),
                            p_trqBilat(RMTP,RMTP1,XXX,"TsPref","CUR")
                          + (  p_trqBilat(RMTP,RMTP1,XXX,"TsMFN","CUR") - p_trqBilat(RMTP,RMTP1,XXX,"TsPref","CUR"))
                             * v_trqSigmoidFunc(RMTP,RMTP1,XXX),max(1.E-5,1.E-7*ABS( p_trqBilat(RMTP,RMTP1,XXX,"TsMFN","CUR")
                                                                                   - p_trqBilat(RMTP,RMTP1,XXX,"TsPref","CUR")))))
                                             $ (     (p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR") gt eps)
                                                   $ (p_trqBilat(RMTP,RMTP1,XXX,"PrefTrigPrice","CUR") le EPS)
                                                   $ (p_trqGlobl(RMTP,XXX,"TrqNt","CUR") gt eps)
                                                   $ ( (p_trqGlobl(RMTP,XXX,"TsPref","CUR") gt eps) or  (p_trqGlobl(RMTP,XXX,"TsMFN","CUR") gt eps)))
            + (  p_trqBilat(RMTP,RMTP1,XXX,"TsPref","CUR")
                  + (  p_trqBilat(RMTP,RMTP1,XXX,"TsMFN","CUR") - p_trqBilat(RMTP,RMTP1,XXX,"TsPref","CUR"))
                         * v_trqSigmoidFunc(RMTP,RMTP1,XXX))
                                             $ (     (p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR") gt eps)
                                                   $ (p_trqBilat(RMTP,RMTP1,XXX,"PrefTrigPrice","CUR") le EPS)
                                                   $ (       (p_trqGlobl(RMTP,XXX,"TrqNt","CUR") le eps)
                                                         or  ( (p_trqGlobl(RMTP,XXX,"TsPref","CUR") le eps)
                                                             $ (p_trqGlobl(RMTP,XXX,"TsMFN","CUR") le eps))))
            + v_tarSpec(RMTP,"RW",XXX) $ ( (p_trqGlobl(RMTP,XXX,"TrqNt","CUR") gt eps)
                                         $ (p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR") le eps))
              )
              /(   MAX(p_trqBilat(RMTP,RMTP1,XXX,"TsMFN","CUR"),p_trqBilat(RMTP,RMTP1,XXX,"TsPref","CUR"))
                 + MAX(p_trqGlobl(RMTP,XXX,"TsMFN","CUR"),p_trqGlobl(RMTP,XXX,"TsPref","CUR")))
            ;
    """
    return ts_pref + dts * s


def tarSpec_min(tw, sb, dts, ncpcm):
    r"""tarSpec_ (l. 3292-3363) where the importer has a global quota too: ncpcm(tw, sb, max(1e-5, 1e-7 |dts|)).
    CAPRI's GAMS: tarSpec_'s docstring."""
    return ncpcm(tw, sb, max(1e-5, 1e-7 * abs(dts)))


def tarAdValW_(ta_pref, dta, s):
    r"""tarAdValW_(RMTP, "Rw", XXX) (l. 3475-3487), a global quota's ad valorem rate: ta_pref + dta s. Elementwise.

    CAPRI's GAMS, tarAdValW_ (l. 3475-3487):

      tarAdValW_(RMTP,"Rw",XXX) $ (  (p_trqGlobl(RMTP,XXX,"TrqNt","CUR") gt eps)
                                   $ (p_trqGlobl(RMTP,XXX,"TaPref","CUR")  lt p_trqGlobl(RMTP,XXX,"TaMFN","CUR"))
                                   $ ((p_trqGlobl(RMTP,XXX,"TaPref","CUR") gt eps) or (p_trqGlobl(RMTP,XXX,"TaMFN","CUR") gt eps)) ) ..
             v_tarAdval(RMTP,"RW",XXX)/(p_trqGlobl(RMTP,XXX,"TaMFN","CUR")+p_trqGlobl(RMTP,XXX,"TaPref","CUR"))
                 =E=
              (p_trqGlobl(RMTP,XXX,"TaPref","CUR")
                + (p_trqGlobl(RMTP,XXX,"TaMFN","CUR")-p_trqGlobl(RMTP,XXX,"TaPref","CUR"))
                     * sigmoid(  p_trqSigmoidSlope(RMTP,XXX)*(v_TRQImports(RMTP,XXX)
                               - p_trqGlobl(RMTP,XXX,"TrqNT","CUR")*0.97)/p_trqGlobl(RMTP,XXX,"TrqNT","CUR")))
                                 /(p_trqGlobl(RMTP,XXX,"TaMFN","CUR")+p_trqGlobl(RMTP,XXX,"TaPref","CUR"));
    """
    return ta_pref + dta * s


def tarSpecW_(ts_pref, dts, s):
    r"""tarSpecW_(RMTP, "Rw", XXX) (l. 3399-3412), a global quota's specific rate: ts_pref + dts s. Elementwise.

    CAPRI's GAMS, tarSpecW_ (l. 3399-3412):

      tarSpecW_(RMTP,"Rw",XXX) $ (  (p_trqGlobl(RMTP,XXX,"TrqNt","CUR")   gt eps)
                                $   (p_trqGlobl(RMTP,XXX,"TsPref","CUR")  lt p_trqGlobl(RMTP,XXX,"TsMFN","CUR"))
                                $   (   (p_trqGlobl(RMTP,XXX,"TsPref","CUR")  gt eps)
                                     or (p_trqGlobl(RMTP,XXX,"TsMFN","CUR")   gt eps)) ) ..
             v_tarSpec(RMTP,"RW",XXX)/(p_trqGlobl(RMTP,XXX,"TsMFN","CUR")+p_trqGlobl(RMTP,XXX,"TsPref","CUR")) =E=
               ( p_trqGlobl(RMTP,XXX,"TsPref","CUR")
                 + (   p_trqGlobl(RMTP,XXX,"TsMFN","CUR")
                      -p_trqGlobl(RMTP,XXX,"TsPref","CUR"))
                    * sigmoid( p_trqSigmoidSlope(RMTP,XXX)/p_trqGlobl(RMTP,XXX,"TrqNT","CUR")
                             * (v_TRQImports(RMTP,XXX)- p_trqGlobl(RMTP,XXX,"TrqNT","CUR")*0.97)))
                             /(p_trqGlobl(RMTP,XXX,"TsMFN","CUR")+p_trqGlobl(RMTP,XXX,"TsPref","CUR"));
    """
    return ts_pref + dts * s


def prefTriggerPrice_(pref, trig, s):
    r"""prefTriggerPrice_(RMTP, RMTP1, XXX) (l. 3369-3394): the entry price under a quota with a preferential trigger
    price, pref + (trig - pref) s. Elementwise.

    CAPRI's GAMS, prefTriggerPrice_ (l. 3369-3394):

      prefTriggerPrice_(RMTP,RMTP1,XXX) $ ( ((v_tarSpec.LO(RMTP,RMTP1,XXX) NE v_tarSpec.up(RMTP,RMTP1,XXX)) or p_trim) $
             (       ( (p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR") GT eps) $ (p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR") NE 1.E+10))
                    $  (p_trqBilat(RMTP,RMTP1,XXX,"TrqNT","CUR") NE prohibitive)
                    $  (p_trqBilat(RMTP,RMTP1,XXX,"PrefTrigPrice","CUR") gt EPS))
                     $ (not Sameas(RMTP,RMTP1)) $ (p_tradeFlows(RMTP,RMTP1,XXX,"CUR") or p_arm2Commit(RMTP,RMTP1,xxx))) ..
                 v_entryPrice(RMTP,RMTP1,XXX)
              /  p_trqBilat(RMTP,RMTP1,XXX,"PrefTrigPrice","CUR")
              =E=
              [  p_trqBilat(RMTP,RMTP1,XXX,"PrefTrigPrice","CUR")
                + (DATA(RMTP,"TriggerP",XXX,"CUR")  - p_trqBilat(RMTP,RMTP1,XXX,"PrefTrigPrice","CUR"))
                   * v_trqSigmoidFunc(RMTP,RMTP1,XXX) ]
              /  p_trqBilat(RMTP,RMTP1,XXX,"PrefTrigPrice","CUR")
            ;
    """
    return pref + (trig - pref) * s


def EntryPriceDriver_(E, cif, trig, fac):
    r"""EntryPriceDriver_(RMTP, RMTP1, XXX) (l. 3176-3189): the entry price's driver, (E 0.95 - cif) / trig x fac (0.95
    CAPRI's (0.98 + 0.92) / 2; trig the trigger price, 1 where it is not positive). Elementwise.

    CAPRI's GAMS, EntryPriceDriver_ (l. 3176-3189):

      EntryPriceDriver_(RMTP,RMTP1,XXX) $ (  (DATA(RMTP,"TriggerP",XXX,"CUR") gt eps)
                                        $ ((v_entryPriceDriver.LO(RMTP,RMTP1,XXX) NE v_entryPriceDriver.up(RMTP,RMTP1,XXX)) or p_Trim)
                                        $ (p_tradeFlows(RMTP,RMTP1,XXX,"CUR") or p_arm2Commit(RMTP,RMTP1,xxx))
                                        $ (NOT p_doubleZero(RMTP,RMTP1,XXX,"CUR"))
                                        $ (NOT SAMEAS(RMTP,RMTP1))) ..
       v_entryPriceDriver(RMTP,RMTP1,XXX) =E=
                  (v_entryPrice(RMTP,RMTP1,XXX) *(0.98+0.92)/2
                      - (v_marketPrice(RMTP1,XXX)+v_transpCost(RMTP,RMTP1,XXX))*p_exchgRateChangeFactor(RMTP,RMTP1))
                             / DATA(RMTP,"TriggerP",XXX,"CUR") * p_entryPriceFac(RMTP,RMTP1,XXX,"CUR");
    """
    return (E * 0.95 - cif) / trig * fac


def tarSpecIfEntryPrice_(d, tars):
    r"""tarSpecIfEntryPrice_(RMTP, RMTP1, XXX) (l. 3204-3216): the specific tariff of a flow under the entry price,
    exp(min(0, d)) / (1 + 20 exp(-|d|)) x tars, d EntryPriceDriver_'s. CasADi.

    CAPRI's GAMS, tarSpecIfEntryPrice_ (l. 3204-3216):

      tarSpecIfEntryPrice_(RMTP,RMTP1,XXX) $ (    (DATA(RMTP,"TriggerP",XXX,"CUR") gt eps)
                                 $ ((v_tarSpec.LO(RMTP,RMTP1,XXX) NE v_tarSpec.up(RMTP,RMTP1,XXX)) or p_Trim)
                                 $ (p_tradeFlows(RMTP,RMTP1,XXX,"CUR") or p_arm2Commit(RMTP,RMTP1,xxx))
                                 $ (NOT p_doubleZero(RMTP,RMTP1,XXX,"CUR")) $ (NOT SAMEAS(RMTP,RMTP1))) ..
        v_tarSpec(RMTP,RMTP1,XXX)/DATA(RMTP,"TARS",XXX,"CUR") =E=
            (EXP( MIN(0,v_entryPriceDriver(RMTP,RMTP1,XXX)))/(1+20*EXP(-ABS(v_entryPriceDriver(RMTP,RMTP1,XXX)))))
                             /DATA(RMTP,"TARS",XXX,"CUR")
                  * (  DATA(RMTP,"TARS",XXX,"CUR")              $   (  P_trqBilat(RMTP,RMTP1,XXX,"TsPref","CUR") le eps)
                     + p_trqBilat(RMTP,RMTP1,XXX,"TsPref","CUR")  $   (  p_trqBilat(RMTP,RMTP1,XXX,"TsPref","CUR") gt eps));
    """
    import casadi as ca
    g = ca.exp(ca.fmin(0, d)) / (1.0 + 20.0 * ca.exp(-ca.fabs(d)))
    return g * tars


def tarSpecIfEntryPrice_np(d, tars):
    r"""tarSpecIfEntryPrice_ (l. 3204-3216) in NumPy. CAPRI's GAMS: tarSpecIfEntryPrice_'s docstring."""
    g = np.exp(np.minimum(0.0, d)) / (1.0 + 20.0 * np.exp(-np.abs(d)))
    return g * tars


def FlexLevyNotCut_(minbord, cif, z, ncpcm):
    r"""FlexLevyNotCut_(RMTP, RMTP1, XXX) (l. 3236-3252): the levy before its cut, -ncpcm(-(minbord - cif), 0, z),
    CAPRI's smoothed max(0, minimum border price - cif); ncpcm the caller's form. Elementwise.

    CAPRI's GAMS, FlexLevyNotCut_ (l. 3236-3252):

      FlexLevyNotCut_(RMTP,RMTP1,XXX) $ ((DATA(RMTP,"MinBordP",XXX,"CUR") gt eps)
                                         $ ( v_flexLevy.lo(RMTP,RMTP1,XXX) ne v_flexLevy.up(RMTP,RMTP1,XXX))
                                         $ (p_tradeFlows(RMTP,RMTP1,XXX,"CUR") or p_arm2Commit(RMTP,RMTP1,xxx))
                                         $ (NOT p_doubleZero(RMTP,RMTP1,XXX,"CUR")) $ (NOT SAMEAS(RMTP,RMTP1))
                                         ) ..
        v_flexLevyNotCut(RMTP,RMTP1,XXX)/DATA(RMTP,"MinBordP",XXX,"CUR") =E=
               -ncpcm( -(  DATA(RMTP,"MinBordP",XXX,"CUR")
                         -(v_marketPrice(RMTP1,XXX)+v_transpCost(RMTP,RMTP1,XXX))*p_exchgRateChangeFactor(RMTP,RMTP1)),
                              0,1.E-3*DATA(RMTP,"MinBordP",XXX,"CUR"))
                                    /DATA(RMTP,"MinBordP",XXX,"CUR");
    """
    return -ncpcm(-(minbord - cif), 0.0, z)


def FlexLevy_(notcut, tars, z, ncpcm):
    r"""FlexLevy_(RMTP, RMTP1, XXX) (l. 3258-3268): the levy cut at the flow's specific tariff, ncpcm(notcut, tars, z).
    Elementwise.

    CAPRI's GAMS, FlexLevy_ (l. 3258-3268):

      FlexLevy_(RMTP,RMTP1,XXX) $ ( (DATA(RMTP,"MinBordP",XXX,"CUR") gt eps)
                                         $ ( v_flexLevy.lo(RMTP,RMTP1,XXX) ne v_flexLevy.up(RMTP,RMTP1,XXX))
                                         $ (p_tradeFlows(RMTP,RMTP1,XXX,"CUR") or p_arm2Commit(RMTP,RMTP1,xxx))
                                         $ (NOT p_doubleZero(RMTP,RMTP1,XXX,"CUR")) $ (NOT SAMEAS(RMTP,RMTP1))
                                         ) ..
             v_flexLevy(RMTP,RMTP1,XXX)/DATA(RMTP,"MinBordP",XXX,"CUR")
                =E= ncpcm(v_flexLevyNotCut(RMTP,RMTP1,XXX),v_tarSpec(RMTP,RMTP1,XXX),1.E-3*DATA(RMTP,"MinBordP",XXX,"CUR"))
                                   /DATA(RMTP,"MinBordP",XXX,"CUR");
    """
    return ncpcm(notcut, tars, z)
