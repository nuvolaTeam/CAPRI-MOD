r"""CAPRI's priors of the inner fertiliser distribution model (supply/set_fert_priors.gms, star 3.0): the gamma
priors' parameters and the beta densities of the "regulations".

capri_mod/fert/inner_fert_dist.py (gamma_params, beta_regulation) and capri_mod/supply/fertilisation.py call these.
The regulations' mode share (0.75 of the maximum, l. 297-299) and accuracy (0.25, l. 303-306; 10 for limCres, l.
320-323) are the parameters FERT_REGU_MODE_SHARE and FERT_REGU_ACCURACY (data read). The gamma prior of the regional
NLP is supply_model/inner_fert.py's gamma_prior (the normalised form).
"""
from __future__ import annotations

from math import sqrt


def p_priFertDist_var(priMode, accuracy):
    r"""p_priFertDist(regions, "var", distpos, fnut, ngrp, "y"): the gamma prior's variance, (mode / accuracy)^2.

    CAPRI's GAMS (supply/set_fert_priors.gms l. 242-244):

        p_priFertDist(%regions%,"var",distpos,fnut,ngrp,"y") $ p_priFertDist(%regions%,"priMode",distpos,fnut,ngrp,"y")
            =   sqr(p_priFertDist(%regions%,"priMode",distpos,fnut,ngrp,"y")
                   /p_priFertDist(%regions%,"accuracy",distpos,fnut,ngrp,"y") );

    Departures from CAPRI: none."""
    return (priMode / accuracy) ** 2


def p_priFertDist_beta(priMode, var):
    r"""p_priFertDist(regions, "beta", ...): the gamma prior's rate, (mode + sqrt(mode^2 + 4 var)) / (2 var).

    CAPRI's GAMS (supply/set_fert_priors.gms l. 247-251):

        p_priFertDist(%regions%,"beta",distpos,fnut,ngrp,"y") $ p_priFertDist(%regions%,"priMode",distpos,fnut,ngrp,"y")
            =   1/(2*p_priFertDist(%regions%,"var",distpos,fnut,ngrp,"y"))
            *[ p_priFertDist(%regions%,"priMode",distpos,fnut,ngrp,"y")
              + sqrt(   sqr(p_priFertDist(%regions%,"priMode",distpos,fnut,ngrp,"y"))
                      + 4*p_priFertDist(%regions%,"var",distpos,fnut,ngrp,"y") ) ];

    Departures from CAPRI: (m + sqrt) / (2 var) (CAPRI's 1 / (2 var) x (m + sqrt): the same value up to rounding)."""
    return (priMode + sqrt(priMode * priMode + 4.0 * var)) / (2.0 * var)


def p_priFertDist_alpha(beta, var):
    r"""p_priFertDist(regions, "alpha", ...): the gamma prior's shape, beta^2 var.

    CAPRI's GAMS (supply/set_fert_priors.gms l. 254-256):

        p_priFertDist(%regions%,"alpha",distpos,fnut,ngrp,"y") $ p_priFertDist(%regions%,"priMode",distpos,fnut,ngrp,"y")
            =   sqr(p_priFertDist(%regions%,"beta",distpos,fnut,ngrp,"y"))
              *     p_priFertDist(%regions%,"var",distpos,fnut,ngrp,"y");

    Departures from CAPRI: none."""
    return beta * beta * var


def p_priFertDistRegu_beta1(mode_over_max, accuracy):
    r"""p_priFertDistRegu(fertDistRegulation, regions, "beta1", fnut, ngrp, "y"): the regulation density's first
    parameter, mode / max x accuracy + 1 (mode_over_max: the mode as a share of the maximum, per ha with
    %priModePerHa% on, on totals otherwise, l. 349-353).

    CAPRI's GAMS (supply/set_fert_priors.gms l. 328-332):

        p_priFertDistRegu(fertDistRegulation,%regions%,"beta1",fnut,ngrp,"y")
            $ p_priFertDistRegu(fertDistRegulation,%regions%,"priModePerHa",fnut,ngrp,"y")
            =   p_priFertDistRegu(fertDistRegulation,%regions%,"priModePerHa",fnut,ngrp,"y")
            /   p_priFertDistRegu(fertDistRegulation,%regions%,"priMaxPerHa",fnut,ngrp,"y")
            *   p_priFertDistRegu(fertDistRegulation,%regions%,"accuracy",fnut,ngrp,"y")+1;

    Departures from CAPRI: the ratio mode / max given (its mode share; the same value)."""
    return mode_over_max * accuracy + 1.0


def p_priFertDistRegu_beta2(accuracy, beta1):
    r"""p_priFertDistRegu(fertDistRegulation, regions, "beta2", fnut, ngrp, "y"): accuracy + 2 - beta1 (l. 356-359 the
    same without %priModePerHa%).

    CAPRI's GAMS (supply/set_fert_priors.gms l. 335-338):

        p_priFertDistRegu(fertDistRegulation,%regions%,"beta2",fnut,ngrp,"y")
            $ p_priFertDistRegu(fertDistRegulation,%regions%,"priModePerHa",fnut,ngrp,"y")
            =   (p_priFertDistRegu(fertDistRegulation,%regions%,"accuracy",fnut,ngrp,"y") + 2)
            -   p_priFertDistRegu(fertDistRegulation,%regions%,"beta1",fnut,ngrp,"y");

    Departures from CAPRI: none."""
    return accuracy + 2.0 - beta1


def v_fertDistPartialSlack_bound(priMode, listed, extra):
    r"""The bound of v_fertDistPartialSlack(regions, fnut, ngrp, distpos) in CAPRI's Green Deal group: a flow's slack
    lies within +-(its prior mode + 0.1 for the listed (region, group) pairs: extra, fertiliser.partial_slack_listed_add_t),
    for the flows with a mode below 5e-3 t (fertiliser.partial_slack_tiny_t, the caller's condition) or listed; elsewhere
    fixed at 0 (l. 668, the caller's: no slack).

    CAPRI's GAMS (supply/set_fert_priors.gms l. 773-782):

        v_fertDistPartialSlack.lo(%regions%,fnut,ngrp,distpos) $ [ p_priFertDist(%regions%,"priMode",distPos,fnut,ngrp,"Y")
                                                                 $ curNuts2(%regions%)
                                                                 $ (   (p_priFertDist(%regions%,"priMode",distPos,fnut,ngrp,"Y") lt 5e-3)
                                                                    or extraSlackRegion_to_ngrp(%regions%,ngrp) ) ]
          = -1.*p_priFertDist(%regions%,"priMode",distPos,fnut,ngrp,"Y") -.1 $ extraSlackRegion_to_ngrp(%regions%,ngrp);
        v_fertDistPartialSlack.up(%regions%,fnut,ngrp,distpos) $ [ p_priFertDist(%regions%,"priMode",distPos,fnut,ngrp,"Y")
                                                                 $ curNuts2(%regions%)
                                                                 $ (   (p_priFertDist(%regions%,"priMode",distPos,fnut,ngrp,"Y") lt 5e-3)
                                                                    or extraSlackRegion_to_ngrp(%regions%,ngrp) ) ]
          = 1.*p_priFertDist(%regions%,"priMode",distPos,fnut,ngrp,"Y") + .1 $ extraSlackRegion_to_ngrp(%regions%,ngrp);

    Departures from CAPRI: the bound's size, the caller using it on both sides."""
    return float(priMode) + (extra if listed else 0.0)
