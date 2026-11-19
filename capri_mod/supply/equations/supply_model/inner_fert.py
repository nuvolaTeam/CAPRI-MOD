r"""CAPRI's inner fertiliser distribution model (supply/supply_model.gms l. 1498-1756): the first-order conditions of
the statistical model that distributes each nutrient's pools (manure, mineral, crop residues) over the crop groups,
with the gamma priors of the flows (supply/set_fert_priors.gms) and the beta densities of the regulations.

The model writes CAPRI's normalized form (p_useNormalizedFertDistInFOC: the flows divided by their prior mode,
e_normalizeFertDist) without the inverse function: the partial derivative of the prior's log density enters the
first-order condition directly as (normAlpha - 1) / u - normBeta, with u = v_normalizedFertDist (CAPRI writes it as
e_fertDistPartial's product, (v_fertDistPartial + normBeta) x u = normAlpha - 1, the same equation for u > 0; the
flows' lower bound is 0.001 x mode, set_fert_priors.gms).

CAPRI's GAMS, e_normalizeFertDist (l. 1535-1539):

    e_normalizeFertDist(runr,ngrp,fnut,distpos) $ [p_priFertDist(runr,"priMode",distpos,fnut,ngrp,"Y") and p_useNormalizedFertDistInFoc] ..

        v_normalizedFertDist(runr,ngrp,fnut,distpos)
            =E=
        v_fertDist(runr,ngrp,fnut,distpos) / p_priFertDist(runr,"priMode",distpos,fnut,ngrp,"Y");

CAPRI's GAMS, e_fertDistPartial (l. 1543-1561):

    e_fertDistPartial(runr,fnut,ngrp,distpos) $ [p_priFertDist(runr,"priMode",distPos,fnut,ngrp,"Y") and p_useInnerFertDistModel] ..

        [(v_fertDistPartial(runr,fnut,ngrp,distpos) + p_priFertDist(runr,"beta",distpos,fnut,ngrp,"y"))
           * (v_fertDist(runr,ngrp,fnut,distPos)
            + v_fertDistPartialSlack(runr,fnut,ngrp,distpos) $ v_fertDistPartialSlack.range(runr,fnut,ngrp,distpos) )
        ] $ [not p_useNormalizedFertDistInFOC]

        +

        [(v_fertDistPartial(runr,fnut,ngrp,distpos) + p_priFertDist(runr,"normBeta",distpos,fnut,ngrp,"y"))
           * (v_normalizedFertDist(runr,ngrp,fnut,distPos)
            + v_fertDistPartialSlack(runr,fnut,ngrp,distpos) $ v_fertDistPartialSlack.range(runr,fnut,ngrp,distpos) )
        ]  $ p_useNormalizedFertDistInFOC

           =E=

        + p_priFertDist(runr,"normAlpha",distpos,fnut,ngrp,"y") $      p_useNormalizedFertDistInFOC
        + p_priFertDist(runr,"alpha",distpos,fnut,ngrp,"y")     $ [not p_useNormalizedFertDistInFOC]
        - 1 ;

CAPRI's GAMS, e_fertDistReguMax (l. 1579-1585; the form on total flows, l. 1668-1674, has priMax and v_fertDist):

   e_fertDistReguMax(fertDistRegulation,runr,fnut,ngrp) $ p_priFertDistRegu(fertDistRegulation,runr,"priMaxPerHa",fnut,ngrp,"y") ..

       v_fertDistReguSlack(fertDistRegulation,runr,fnut,ngrp)
           =E=
       p_priFertDistRegu(fertDistRegulation,runr,"priMaxPerHa",fnut,ngrp,"y")
       -sum(distpos, v_fertDistPerHa(runr,ngrp,fnut,distPos)*p_fertDistReguWgt(fertDistRegulation,distPos))
        ;

CAPRI's GAMS, e_fertDistPartialRegu (l. 1588-1606; the form on total flows, l. 1677-1691, without the area factor):

   e_fertDistPartialRegu(fertDistRegulation,runr,fnut,ngrp,distPos)
     $ [     p_priFertDistRegu(fertDistRegulation,runr,"priModePerHa",fnut,ngrp,"y")
         and p_fertDistReguWgt(fertDistRegulation,distPos)] ..

      v_fertDistPartialRegu(fertDistRegulation,runr,fnut,ngrp,distPos)
    * SUM( (CACT_TO_NGRP(MCACT,NGRP),A) $ p_technFact(RUNR,MCACT,"LEVL",A), v_actLevl(RUNR,MCACT,A))
         =E=
             (p_priFertDistRegu(fertDistRegulation,runr,"beta1",fnut,ngrp,"y")-1)
             * (1 / sum(distPos1, v_fertDistPerHa(runr,ngrp,fnut,distPos1)*p_fertDistReguWgt(fertDistRegulation,distPos1)))
             * p_fertDistReguWgt(fertDistRegulation,distPos)
           + (p_priFertDistRegu(fertDistRegulation,runr,"beta2",fnut,ngrp,"y")-1)
             * (-1 / v_fertDistReguSlack(fertDistRegulation,runr,fnut,ngrp))
             * p_fertDistReguWgt(fertDistRegulation,distPos)
      ;

CAPRI's GAMS, e_focFertDist (l. 1613-1649; the same at l. 1698-1733 with the regulations on total flows):

    e_focFertDist(runr,fnut,ngrp,distpos) $ [p_priFertDist(runr,"priMode",distPos,fnut,ngrp,"Y") and p_useInnerFertDistModel] ..

          v_fertDistPartial(runr,fnut,ngrp,distpos)
        + sum(fertDistRegulation  $ [    p_priFertDistRegu(fertDistRegulation,runr,"priModePerHa",fnut,ngrp,"y")
                                                         and p_fertDistReguWgt(fertDistRegulation,distPos)],
            v_fertDistPartialRegu(fertDistRegulation,runr,fnut,ngrp,distPos))
        + v_slackFertDist(runr,fnut,ngrp,distpos) $ p_useSlackFertDist
        =E=
        (
            +[ (v_dualNutNed(runr,fnut,ngrp)
                  *SUM( FOUT_T_N(FOUT,FNUT),v_nutAvailFactExcr(RUNR,FOUT))
                  - v_dualNutSup(runr,fnut,distPos))]                  $ sameas(distPos,"excr")
            +[ (v_dualNutNed(runr,fnut,ngrp)
                  *SUM( FOUT_T_N(FOUT,FNUT),v_nutAvailFactCRes(RUNR,FOUT))
                  * (1.-p_emiLoss(RUNR,"NETF","N","GasRunTot") $ SAMEAS(FNUT,"NITF") )
                  - v_dualNutSup(runr,fnut,distPos))]                   $ sameas(distPos,"cres")
            +[ (v_dualNutNed(runr,fnut,ngrp)
                  * (1.-p_emiLoss(RUNR,"NETF","N","GasRunTot") $ SAMEAS(FNUT,"NITF") )
                  - v_dualNutSup(runr,fnut,distPos))]                   $ sameas(distPos,"mine")
        )
        * (  p_priFertDist(runr,"priMode",distPos,fnut,ngrp,"Y")  $      p_useNormalizedFertDistInFOC
           + 1                                                    $ [not p_useNormalizedFertDistInFOC])
        ;

CAPRI's GAMS, the gamma prior's parameters (supply/set_fert_priors.gms l. 230-237):

    p_priFertDist(%regions%,"normBeta",distpos,fnut,ngrp,"y") $ p_priFertDist(%regions%,"priMode",distpos,fnut,ngrp,"y")
        =   sqr(p_priFertDist(%regions%,"accuracy",distpos,fnut,ngrp,"y")) / 2
        * [ 1 + sqrt(1 + 4/sqr(p_priFertDist(%regions%,"accuracy",distpos,fnut,ngrp,"y")) )];

    p_priFertDist(%regions%,"normAlpha",distpos,fnut,ngrp,"y") $ p_priFertDist(%regions%,"priMode",distpos,fnut,ngrp,"y")
        =   sqr(p_priFertDist(%regions%,"normBeta",distpos,fnut,ngrp,"y"))
          / sqr(p_priFertDist(%regions%,"accuracy",distpos,fnut,ngrp,"y"));

In this project's notation, for the flow s of group g (u = x / m, m the prior mode, k = 1 / accuracy^2; lambda_g the
dual of NUTNED_, mu_s the dual of the source's pool, 0 for the mineral pool; T the mean prior mode, the duals'
scale; e_s the source's availability factor):

    normBeta = (1 + sqrt(1 + 4 k)) / (2 k),   normAlpha - 1 = normBeta^2 k - 1
    term     = (normAlpha - 1) / (u + sigma) + (beta1 - 1) / u - normBeta - (m / T) (lambda_g e_s - mu_s)
               - m (beta2 - 1) / (Y - x)
    e_focFertDist:  term = 0       (CAPRI's equality; or K159's complementarity form, below)
    e_fertDistReguMax:  x - margin Y <= 0,   Y = the regulation's maximum per ha x the group's area

sigma = v_fertDistPartialSlack (the Green Deal group's listed regions; else absent), beta1 and beta2 the
regulation's beta density (present only for a regulated flow; beta1 - 1 then sits with the prior's alpha), Y the
regulation's support.

Departures from CAPRI:
- K159 (the project lead's decision of 15 November 2026; DEP-49): at a flow's lower bound 0.001 x mode the first-order
  condition has the bound's multiplier nu >= 0 as well, term + nu = 0 with nu (u - lb) = 0, written as the smoothed
  Fischer-Burmeister function of (u - lb, -term) (e_focFertDist_FB); by default only in the retry of a failed solve.
- The regulations' slack v_fertDistReguSlack is the support's distance Y - x itself (no slack variable), and the
  support's bound is margin x Y (fertiliser.support_margin, CAPRI's 0.999 on the slack).
"""
from __future__ import annotations

import numpy as np


def gamma_prior(accuracy: float):
    """CAPRI's normalized gamma prior of a fertiliser flow (set_fert_priors.gms l. 230-237): (normBeta, normAlpha - 1)
    from the flow's accuracy, the mode being 1."""
    var_k = 1.0 / accuracy ** 2
    bm = (1.0 + np.sqrt(1.0 + 4.0 * var_k)) / (2.0 * var_k)      # normBeta
    a1 = bm * bm * var_k - 1.0                                  # normAlpha - 1
    return bm, a1


def e_focFertDist_dual(v_dualNutNed, availFact, v_dualNutSup):
    """e_focFertDist's right-hand side before the mode factor (l. 1613-1649): v_dualNutNed x the source's availability
    factor - v_dualNutSup (0 for the mineral source, which has no pool row of its own)."""
    return v_dualNutNed * availFact - v_dualNutSup


def e_focFertDist_term(normAlpha1, u, normBeta, mode_T, dual):
    """e_focFertDist written as one term, = 0, for a flow without slack or regulation: v_fertDistPartial (from
    e_fertDistPartial with the inverse written directly) - mode x the dual term (in the duals' scale T)."""
    return normAlpha1 / u - normBeta - mode_T * dual


def e_focFertDist_term_slack(normAlpha1, u, slack, regu1, normBeta, mode_T, dual):
    """The same for a flow with CAPRI's slack v_fertDistPartialSlack (e_fertDistPartial: the prior's part takes
    u + slack); regu1 = beta1 - 1 of the flow's regulation (e_fertDistPartialRegu's first term, without the slack), 0
    without a regulation."""
    return normAlpha1 / (u + slack) + regu1 / u - normBeta - mode_T * dual


def e_fertDistPartialRegu_upper(term, regu2, Y, x):
    """e_fertDistPartialRegu's second term, added to the first-order condition of a regulated flow:
    - mode x (beta2 - 1) / v_fertDistReguSlack, the slack being Y - x."""
    return term - regu2 / (Y - x)


def e_fertDistReguMax(x, Y, margin, inv_mode):
    """e_fertDistReguMax as the support's bound (l. 1579-1585): x - margin x Y <= 0, scaled by 1 / mode."""
    return (x - margin * Y) * inv_mode


def e_focFertDist_FB(u, u_lo, term, eps):
    """K159's form of e_focFertDist (DEPARTURE, DEP-49): the smoothed Fischer-Burmeister function of (u - lb, -term),
    zero where term = 0 inside the bounds, or u = lb and term <= 0."""
    import casadi as ca
    a_ = u - u_lo
    b_ = -term
    return a_ + b_ - ca.sqrt(a_ * a_ + b_ * b_ + eps)
