r"""CAPRI's manure pool market in the simulation (manuremarket/simu_manure_market.gms, star 3.0): the refit of each
region's excess supply to its supply model's last solution (p_mPoolSupConst) and the step-weighted averages of the
prices (the manure value of a region near or below zero, the pool prices sent back to the supply models), with
CAPRI's step weights normalised over the steps available (capmod/define_stepWeights.gms).

CAPRI's GAMS statement of each assignment is in the docstring of the function that writes it; this docstring keeps
the overview, notation and departures.

Written: CAPRIModel._clear_pool_capri and _clear_pool (capri_mod/coupling/manure.py).

In this project's notation, per region (z its net export at its last solve, v its manure value there, CAPRI's PSHW,
b CAPRI's slope of the excess supply) and per weighted average (w the step weights, the latest first, x the values of
the last steps, the latest first):

    p_mPoolSupConst        a = z - b v           (ES = a + b P passes through (v, z))
    p_stepWeights_average  sum_s w_s x_s / sum_s w_s, over the steps available

Departures from CAPRI: the weights over the steps the model keeps (CAPRI's are conditioned on a change in the step,
p_iterChg); the fall-back price of a missing manure value (l. 50-66) in the caller.
"""
from __future__ import annotations


def p_mPoolSupConst(z, b, v):
    r"""p_mPoolSupConst(ru, fout) (l. 87-89), the constant of a region's excess supply refitted to its last solution,
    z - b v. A float.

    CAPRI's GAMS, p_mPoolSupConst (manuremarket/simu_manure_market.gms l. 87-89):

     p_mPoolSupConst(ru,fout)
         = p_excessSupplyFromSupMod(fout,ru)
         - p_mPoolSupSlope(ru,fout)*p_priceFromSupMod(fout,ru);
    """
    return z - b * v


def p_stepWeights_average(wts, use):
    r"""The step-weighted average of the last steps' values use (the latest first) with CAPRI's weights wts (the
    latest first), normalised over the steps available, sum w x / sum w: a region's manure value near or below zero
    (l. 76-78) and the pool prices sent back to the supply models (p_exoDemand, l. 222-227). A float.

    CAPRI's GAMS, p_priceFromSupMod (manuremarket/simu_manure_market.gms l. 76-78):

     p_priceFromSupMod(fout,ru) $ ((p_priceFromSupMod(fout,ru) le 1e-6) $ card(stepsWithWeights))
       = SUM(stepsWithWeights, p_itemsInIters(ru,"PSHW",FOUT,stepsWithWeights) * p_stepWeights(stepsWithWeights))
       / SUM(stepsWithWeights,                                                   p_stepWeights(stepsWithWeights));

    CAPRI's GAMS, p_exoDemand (manuremarket/simu_manure_market.gms l. 222-227):

     p_exoDemand(rManPool,"uvag",fout) = e_mPoolExcessSupply.m(rManPool,fout);
     if( card(stepsWithWeights),
        p_exoDemand(rManPool,"uvag",fout)
           = SUM(stepsWithWeights,
                p_itemsInIters(rManPool,"PMRK",FOUT,stepsWithWeights) * p_stepWeights(stepsWithWeights));
     );

    CAPRI's GAMS, the weights' normalisation (capmod/define_stepWeights.gms l. 40-41):

         p_stepWeights(STEP1) $ SUM(STEP2, p_stepWeights(STEP2))
               =  p_stepWeights(STEP1)/SUM(STEP2, p_stepWeights(STEP2));
    """
    return sum(w_ * x_ for w_, x_ in zip(wts, use)) / sum(wts[:len(use)])
