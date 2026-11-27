r"""CAPRI's test of the pesticide calibration (supply/cal_pesti.gms l. 517-561, model m_pestiTest of
supply/declare_cal_pesti.gms l. 100-131, star 3.0): the farmer's choice of the applications with the calibrated damage
functions, at the calibration point (the applications must come back, the yield factor 1 within 1e-4) and at the price
at which the prior elasticity would end the use. The yield factor's equation is the supply model's (supply_model.gms
l. 4354-4385), so this file also holds the form the supply model will take.

The problem separates by region, crop, technology and aggregate (the yield factor is a sum over the aggregates, the
cost is linear), and each cell's is convex (SlopExpo > 0 and Expon > 1 by the calibration's bounds; the linear
fall-back's smooth form is convex), so the optimum is written from its first-order condition here (docs/CAPRI_DEPARTURES_REGISTER.md DEP-60).
"""
from __future__ import annotations

import math

from capri_mod.supply.equations.cal_pesti import P_PESTFUDGE, PESTI_ELA

#: the yield factor's tolerance at the calibration point (supply/cal_pesti.gms l. 556)
PESTI_CALI_TOL = 1e-4
#: the bounds of an endogenous application in the test, times the observed one (supply/cal_pesti.gms l. 520-521)
PESTI_TEST_BOUNDS = (0.0, 10.0)


def damage_share(v_pestiPerHa, SlopLin, SlopExpo, Expon, sqrt=math.sqrt):
    r"""The share of the maximum damage left at an application: the bracket of yldPestFac_.

    CAPRI's GAMS (supply/supply_model.gms l. 4376-4385):

                                  *[(1 - p_pestPar(RUNR,MCACT,pestoAgg,A,"SlopLin")
                                      * v_pestiPerHa(RUNR,MCACT,pestoAgg,A)
                                      + p_pestPar(RUNR,MCACT,pestoAgg,A,"SlopExpo")
                                      * v_pestiPerHa(RUNR,MCACT,pestoAgg,A)**p_pestPar(RUNR,MCACT,pestoAgg,A,"Expon"))
                                   $ p_pestPar(RUNR,MCACT,pestoAgg,A,"Expon")
        *                           Part 2: For simple linear function with fudging:
                                   +((     (1-p_pestPar(RUNR,MCACT,pestoAgg,A,"SlopLin")*v_pestiPerHa(RUNR,MCACT,pestoAgg,A))
                                      +SQRT(sqr(p_pestPar(RUNR,MCACT,pestoAgg,A,"SlopLin")*v_pestiPerHa(RUNR,MCACT,pestoAgg,A)-1)
                                           +p_pestFudge))/2)
                                   $ (not p_pestPar(RUNR,MCACT,pestoAgg,A,"Expon"))

    In this project's notation: with a = v_pestiPerHa, the power form 1 - SlopLin a + SlopExpo a^Expon where Expon is
    non-zero, else the smooth linear form ((1 - SlopLin a) + sqrt((SlopLin a - 1)^2 + p_pestFudge)) / 2.
    Departures from CAPRI: none."""
    a = v_pestiPerHa
    if Expon:
        return 1.0 - SlopLin * a + SlopExpo * a ** Expon
    return ((1.0 - SlopLin * a) + sqrt((SlopLin * a - 1.0) ** 2 + P_PESTFUDGE)) / 2.0


def yldPestFac_(NoDamageFac, cells, sqrt=math.sqrt):
    r"""v_yldPestFac(RUNR, MCACT, A): the yield factor from more or less plant protection.

    CAPRI's GAMS (supply/supply_model.gms l. 4354-4385):

            yldPestFac_(RUNR,MCACT,A) $ (v_yldPestFac.range(RUNR,MCACT,A) $ p_pestPar(RUNR,MCACT,"yild",A,"NoDamageFac"))..


                     v_yldPestFac(RUNR,MCACT,A) =E=
        *
        *            markup to pest-free state either due to full eradication or absense of pest =
        *            1 + sum of all damages in calibration point

                       p_pestPar(RUNR,MCACT,"yild",A,"NoDamageFac")
                                 - sum(PESTOAGG, ( p_pestPar(RUNR,MCACT,pestoAgg,A,"maxDamage")
                                                 $ (not p_pestPar(RUNR,MCACT,pestoAgg,A,"maxDamageCons"))
        *                           Max damage may be responsive to activity levels to pick up crop rotation effects.
                                               + ( p_pestPar(RUNR,MCACT,pestoAgg,A,"maxDamageCons")
        *                           The first possible effect is a damage increasing from the own area due to pest spreading
                                               +   p_pestPar(RUNR,MCACT,pestoAgg,A,"maxDamageOwn")*v_actLevl(RUNR,MCACT,A)
        *                           The second possible effect is damage decreasing from beneficial catch crop effects (for weeds)
                                                 + p_pestPar(RUNR,MCACT,pestoAgg,A,"maxDamageCatc")*v_actLevl(RUNR,"CATC",A))
        *                           Endogenous max damage would be signaled by a non-zero constant term:
                                                 $      p_pestPar(RUNR,MCACT,pestoAgg,A,"maxDamageCons") )
        *                           Max damage may be reduced with plant protection measures. Typically this is pesticide application
        *                           (possibly as an aggregate of single AIs), but mechanical weeding may be also included
        *                           Part 1: For 3 parameter power function:
                                  *[(1 - p_pestPar(RUNR,MCACT,pestoAgg,A,"SlopLin")
                                      * v_pestiPerHa(RUNR,MCACT,pestoAgg,A)
                                      + p_pestPar(RUNR,MCACT,pestoAgg,A,"SlopExpo")
                                      * v_pestiPerHa(RUNR,MCACT,pestoAgg,A)**p_pestPar(RUNR,MCACT,pestoAgg,A,"Expon"))
                                   $ p_pestPar(RUNR,MCACT,pestoAgg,A,"Expon")
        *                           Part 2: For simple linear function with fudging:
                                   +((     (1-p_pestPar(RUNR,MCACT,pestoAgg,A,"SlopLin")*v_pestiPerHa(RUNR,MCACT,pestoAgg,A))
                                      +SQRT(sqr(p_pestPar(RUNR,MCACT,pestoAgg,A,"SlopLin")*v_pestiPerHa(RUNR,MCACT,pestoAgg,A)-1)
                                           +p_pestFudge))/2)
                                   $ (not p_pestPar(RUNR,MCACT,pestoAgg,A,"Expon"))

    In this project's notation: NoDamageFac - sum over the aggregates of maxDamage x damage_share(v_pestiPerHa). cells:
    per aggregate (maxDamage, v_pestiPerHa, SlopLin, SlopExpo, Expon). Returns the right side.
    Departures from CAPRI: the maximum damage responding to the areas (maxDamageCons, maxDamageOwn, maxDamageCatc) is
    not written: CAPRI's calibration of the five aggregates sets none of them."""
    return NoDamageFac - sum(m * damage_share(a, sl, se, ex, sqrt) for m, a, sl, se, ex in cells)


def farmerObje_(margin, v_yldPestFac, purchases, testincrease=0.0):
    r"""The farmer's objective of the test: the yield's value net of the marginal fertiliser cost times the yield
    factor, less the pesticides bought.

    CAPRI's GAMS (supply/declare_cal_pesti.gms l. 100-115):

          farmerObje_..

              v_obje *1.e0
                 =E= sum((RUNR,MCACT,A) $ (pactCur(mCact) $ p_pestPar(RUNR,MCACT,"yild",A,"NoDamageYld")),
                             (p_pestPar(RUNR,MCACT,"yild",A,"NoDamageYld")-p_pestPar(RUNR,MCACT,"FERC",A,"margCostYld"))
        *                   * v_pestPar(Runr,MCACT,"yild",A,"yldPestFac")
                           * v_yldPestFac(runr,MCACT,A)

                           - sum(PESTOAGG $ pestCur(pestoAgg), ( data(runr,"uvag",pestoAgg,"y")
        *     Prices are only assigned to data() for elements of set inputs I (in calc_aver)=> Use crop specific aggregate prices:
        $Ifi %PESTDISAGGStage%==SelAI                          + p_pestPar(RUNR,MCACT,pestoAgg,A,"uvag") $ (not data(RUNR,"uvag",pestoAgg,"y"))
                                                               )
        *                                                      "Testincrease"=-1/prior to test choke price
                                                             *(1+p_pestiEla("testincrease"))
                                                             * v_pestiPerHa(RUNR,MCACT,pestoAgg,A))


    In this project's notation, per region, crop and technology (CAPRI sums them): margin x v_yldPestFac - sum over
    the aggregates of UVAG x (1 + testincrease) x v_pestiPerHa, margin = NoDamageYld - margCostYld(FERC). purchases:
    per aggregate (UVAG, v_pestiPerHa). Departures from CAPRI: none (the selAI line not ported)."""
    return margin * v_yldPestFac - sum(u * (1.0 + testincrease) * a for u, a in purchases)


def p_pestiEla_testincrease(prior=PESTI_ELA["prior"]):
    r"""The price increase of the test's first solve.

    CAPRI's GAMS (supply/cal_pesti.gms l. 530-531):

        *      Increase the input  price such that we should get a 100% reduction at the prior elasticity (if this applies to the large change)
          p_pestiEla("testincrease") = -1/p_pestiEla("Prior");

    In this project's notation: -1 / prior (3.33 at the prior elasticity -0.3). Departures from CAPRI: none."""
    return -1.0 / prior


def m_pestiTest_cell(ApplPerHa, priceDamagRatio, SlopLin, SlopExpo, Expon, endogenous, testincrease=0.0):
    r"""v_pestiPerHa of a cell at the optimum of m_pestiTest: the observed application where the cell is exogenous,
    else the application at which the damage avoided by the last unit equals its price, within the test's bounds.

    CAPRI's GAMS (supply/cal_pesti.gms l. 519-526, 538, 543-550):

          v_pestiPerHa.fx(RUNR,MCACT,pestoAgg,A) = p_pestPar(runr,mCACT,pestoAgg,A,"ApplPerHa") ;
          v_pestiPerHa.Lo(RUNR,MCACT,pestoAgg,A) $ p_pestPar(RUNR,MCACT,pestoAgg,A,"endogenous") = p_pestPar(runr,mCACT,pestoAgg,A,"ApplPerHa") * .0;
          v_pestiPerHa.up(RUNR,MCACT,pestoAgg,A) $ p_pestPar(RUNR,MCACT,pestoAgg,A,"endogenous") = p_pestPar(runr,mCACT,pestoAgg,A,"ApplPerHa") * 10;
          v_pestiPerHa.L(RUNR,MCACT,pestoAgg,A)  $ p_pestPar(RUNR,MCACT,pestoAgg,A,"endogenous") = 1e-1*p_pestPar(runr,mCACT,pestoAgg,A,"ApplPerHa") ;

          v_yldPestFac.fx(%regions%,MCACT,A) $ SUM(pestoAgg, p_pestPar(%regions%,mCACT,pestoAgg,A,"ApplPerHa")) = 1 ;
          v_yldPestFac.lo(RUNR,MCACT,A) $ SUM(pestoAgg $ p_pestPar(RUNR,MCACT,pestoAgg,A,"ApplPerHa"),1) = .0*v_yldPestFac.l(RUNR,MCACT,A);
          v_yldPestFac.up(RUNR,MCACT,A) $ SUM(pestoAgg $ p_pestPar(RUNR,MCACT,pestoAgg,A,"ApplPerHa"),1) = 2.*v_yldPestFac.l(RUNR,MCACT,A);
            ...
          p_pestPar(runr,mCACT,pestoAgg,A,"ApplPerHa2") = v_pestiPerHa.L(RUNR,MCACT,pestoAgg,A) ;
            ...
          p_pestiEla("testincrease") = 0;
          v_pestiPerHa.L(RUNR,MCACT,pestoAgg,A) = .99*p_pestPar(runr,mCACT,pestoAgg,A,"ApplPerHa") ;
          v_yldPestFac.l(%regions%,MCACT,A) $ SUM(pestoAgg, p_pestPar(%regions%,mCACT,pestoAgg,A,"ApplPerHa")) = 1 ;
        *

          v_pestiPerHa.Lo(RUNR,MCACT,pestoAgg,A) $ p_pestPar(RUNR,MCACT,pestoAgg,A,"endogenous") = p_pestPar(runr,mCACT,pestoAgg,A,"ApplPerHa") * .0;
          v_pestiPerHa.up(RUNR,MCACT,pestoAgg,A) $ p_pestPar(RUNR,MCACT,pestoAgg,A,"endogenous") = p_pestPar(runr,mCACT,pestoAgg,A,"ApplPerHa") * 10;
          SOLVE m_pestiTest USING NLP MaxIMIZING v_obje;

    In this project's notation, with p = priceDamagRatio x (1 + testincrease) (the pesticide's price over margin x
    maxDamage) and a in [0, 10 ApplPerHa]: the power form's a = ((SlopLin - p) / (SlopExpo Expon))^(1 / (Expon - 1)),
    0 where SlopLin <= p; the linear form's a = (1 + u) / SlopLin with u / sqrt(u^2 + p_pestFudge) = 1 - 2 p / SlopLin,
    0 where the avoided damage at 0 is not above p.

    Departures from CAPRI (register DEP-60; the project lead, 27 November 2026): the optimum from the first-order
    condition of the cell's problem, where CAPRI solves all cells of a region as one NLP (CONOPT). Why: the objective
    separates by cell (the yield factor is a sum over the aggregates, the cost linear) and each cell's problem is
    convex on its bounds (SlopExpo > 0 and Expon > 1 by the calibration's bounds; the linear form's smooth version), so
    this point, moved to the nearer bound where it lies outside, is the one optimum a solver reaches; it is exact and
    needs no solver (the project uses no CONOPT)."""
    a0 = float(ApplPerHa)
    if not (endogenous and priceDamagRatio):
        return a0
    lo, up = PESTI_TEST_BOUNDS[0] * a0, PESTI_TEST_BOUNDS[1] * a0
    p = float(priceDamagRatio) * (1.0 + testincrease)
    if Expon:
        a = 0.0 if SlopLin <= p else ((SlopLin - p) / (SlopExpo * Expon)) ** (1.0 / (Expon - 1.0))
    else:
        s = float(SlopLin)
        c = 1.0 - 2.0 * p / s
        at_zero = -1.0 / math.sqrt(1.0 + P_PESTFUDGE)            # u / sqrt(u^2 + fudge) at a = 0 (u = -1)
        a = 0.0 if c <= at_zero else (up if c >= 1.0 else (1.0 + c * math.sqrt(P_PESTFUDGE / (1.0 - c * c))) / s)
    return min(up, max(lo, a))


def pestiCaliProblems_map(v_yldPestFac):
    r"""Whether a crop and technology is a problem case of the calibration.

    CAPRI's GAMS (supply/cal_pesti.gms l. 556-556):

          pestiCaliProblems_map(runr,mCACT,A) $ (abs(v_yldPestFac.l(runr,MCACT,A)-1) gt 1e-4) = yes;

    In this project's notation: |v_yldPestFac - 1| > 1e-4 at the calibration point. Departures from CAPRI: none."""
    return abs(float(v_yldPestFac) - 1.0) > PESTI_CALI_TOL
