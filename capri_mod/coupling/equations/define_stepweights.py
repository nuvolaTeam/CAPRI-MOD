r"""CAPRI's weights of the price forecast (capmod/define_stepWeights.gms, star 3.0): the slower smoothing of the problem
products (p_stepWgtSpecial).

capri_mod/coupling/price_step.py (PriceStepBlock._capri_special_forecast) calls it.
"""
from __future__ import annotations


def p_stepWgtSpecial(srt, step):
    r"""p_stepWgtSpecial(MS, rows, stepx) before the normalisation: at the step k the weight of step j, max(0, 1 - srt
    (k + 1 - j)) for j = 0 (TRD, the baseline) to k (a list over j).

    CAPRI's GAMS (capmod/define_stepWeights.gms l. 47-52):

            p_stepWgtSpecial(MS,rows,stepx) $ ( (stepx.pos LE (step.pos+1))
                                              $ p_stepWgtSpecial(ms,rows,"srt")  )
                                     = MAX(0,1. - p_stepWgtSpecial(ms,rows,"srt") * (2+step.pos-stepx.pos)) ;
            p_stepWgtSpecial(MS,rows,stepx) $ SUM(STEPx1, p_stepWgtSpecial(MS,rows,stepx1))

                  =  p_stepWgtSpecial(MS,rows,stepx)/ SUM(STEPx1, p_stepWgtSpecial(MS,rows,stepx1));

    In this project's notation: w_j = max(0, 1 - srt (k + 1 - j)), j = stepx.pos - 1 (stepx's first element TRD).
    Departures from CAPRI: the normalisation (l. 50-52) applied by the caller to the weighted average (sum w v / sum
    w; CAPRI's sum (w / sum w) v: the same value up to rounding)."""
    return [max(0.0, 1.0 - float(srt) * (step + 1 - j)) for j in range(step + 1)]
