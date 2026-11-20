r"""CAPRI's feeding block (supply/supply_model.gms l. 512-832): the animals' requirements and the feed use.

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026); this docstring keeps the block's overview, notation and departures.

Written: the regional NLP's feeding rows (CapriRegionalNLP.__init__, "REQSE_" and the fodder balances): REQSE_, the
requirements of energy (ENNE) and crude protein (CRPR) as equalities, and FEDUSE_, the feed use. The feed's PMP terms,
QUADRF_ with QUADRF1_, are in objective.py.

CAPRI's feed version _pw (the Green Deal step) has REQSE_ alone of the requirement rows in its simulation model:
REQSN_ (dry matter, fibre; l. 521-556), MAXSHR_ (l. 640-662) and MINSHR_ (l. 667-689) are not in the step. The NLP
writes REQSE_ only; feed/ration.py's calibration of the base rations uses them (CAPRI's feed PMP,
pmp_terms/define_const_pmp_param.gms), before the simulation.

Not written: SupplementPerc_ (l. 608-633; ghgAbatement), the linseed supplement's limit on the ration's fat
(KNOWN_ISSUES K93: linseed is a column of the regional model, supplement_effects.csv).

In this project's notation, for an animal a with herd h_a (1000 head) and per-head feed u_f (kg per head and year;
CAPRI's v_feedInpCoeff), the feeds' contents e_f (energy) and cp_f (crude protein) and the requirement R per head
(the base ration's supply: CAPRI's p_animReq x p_animProdDays, p_trimFeed = 0, met exactly by the base ration):

    REQSE_:   sum_{f flexible} u_f e_f / R + sum_{f fixed} u0_f e_f / R - 1 = 0     (and the same with cp_f)
    FEDUSE_:  F_f = h_a u_f (t), the non-tradable fodder's balance taking sum_a F_f / 1000 (1000 t)

Departures from CAPRI: the feeds outside feed/ration.py's FEED_ELAS are held at their base amount per head (the fixed
term; CAPRI's v_feedInpCoeff are variables for every feed with p_maxFeedShare). The requirement's changes by the
options' columns (supply/livestock.py _genetics_columns; z the heads adopting, CAPRI's v_Miti x v_actLevl) and by the
dairy and cattle split columns are linear terms d x z (the spec's req_extra), in REQSE_split's total form.
"""
from __future__ import annotations


def REQSE_(supply_flex, supply_fixed):
    r"""REQSE_(r, a, T, REQMSE) (l. 561-602) as the NLP's row, scaled by the requirement R per head: the flexible
    feeds' supply (sum_f u_f x content_f / R, the caller's sum), plus the fixed feeds' (their base amounts' supply / R),
    minus 1, = 0.

    CAPRI's GAMS, REQSE_ (l. 561-602):

         REQSE_(RUNR,MAACT,A,REQMSE %addtimedim%) $ (  p_animReq(RUNR,MAACT,A,REQMSE %addtimedim%) $ p_technFact(RUNR,MAACT,"LEVL",A) ) ..
    *
    *                                      --- animal requirements per activity level and day
             (v_animReq(RUNR,MAACT,A,REQMSE %addtimedim%)  $ p_trimFeed + p_animReq(RUNR,MAACT,A,REQMSE %addtimedim%) $ (Not p_trimFeed))
    $iftheni.lnf6 %ghgAbatement%==on
    *                                          -- considering a possible modification by mitigation option lowNFeed
                 * (1 + v_Miti(RUNR,MAACT,"lowNFeed","N2OEXCR")*p_ghgMiti(RUNR,MAACT,"lowNFeed","othImpact","CRPR") $ SAMEAS(REQMSE,"CRPR"))
    *                                          -- consider a reduction of energy need by option genet_eff:
                 * (1 + v_Miti(RUNR,MAACT,"genet_eff","rumFedEff")*p_ghgMiti(RUNR,MAACT,"genet_eff","othImpact",REQMSE) )
    *                                          -- consider a modification by mitigation option mlkYld
                 * (1 + v_Miti(RUNR,MAACT,"genet_yld","mlkYld")*p_ghgMiti(RUNR,MAACT,"genet_yld","othImpact",REQMSE) $ PACT_TO_Y(MAACT,"COMI"))
    $endif.lnf6
                 * p_animProdDays(RUNR,MAACT,A %addtimedim%)
    *                                      --- are covered by feeding of feedingstuff
                -  SUM(FEED $ p_maxFeedShare(RUNR,MAACT,A,FEED %addtimedim%),
                         v_feedInpCoeff(RUNR,MAACT,A,FEED %addtimedim%)
                            * SUM(R_RAGG(RUNR,MSACT),%data%(MSACT,REQMSE,FEED,%timedim%)))
    $iftheni.Lin1 %ghgAbatement%==on
    *          Protein saving through feed additive nitrates
               - p_animReq(RUNR,MAACT,A,"DRMA") * p_animProdDays(RUNR,MAACT,A)
                         * v_miti(RUNR,MAACT,"Nitr_tot","CH4ENT")*p_emisFeed(RUNR,MAACT,"T","Nitr_tot","CRPR")
                         $ (SAMEAS(REQMSE,"CRPR") $ (CATACT(MAACT)
                             $ sum(R_RAGG(RUNR,MSACT), mitiTech_map(MSACT,MAACT,"Nitr_tot","CH4ENT"))))
    *          Nutrients from Lineseed
               - ( p_animReq(RUNR,MAACT,A,"DRMA") * p_animProdDays(RUNR,MAACT,A)
    *          ... times maximum % of DM from line seed fat (=5%)
                 * sum(R_RAGG(RUNR,MSACT) $ (CATACT(MAACT) $ mitiTech_map(MSACT,MAACT,"Line_tot","CH4ENT")),
                   p_emisFeed(RUNR,MAACT,"T","Line_tot","ShrOfDM")
    *          ... times actual use (0<=v_miti<=1) of this maximum capacity (=> gives actual intake of fat from line seed)
                 * v_miti(RUNR,MAACT,"Line_tot","CH4ENT")
    *          ... divided by fat content of line seed (=> gives actual intake of fresh matter from line seed)
                 / p_emisFeed(RUNR,MAACT,"T","Line_tot","TotFAT")
    *          ... times REQMSE-content (=> gives actual intake of REQMSE from line seed that has to be deducted)
                 * p_emisFeed(RUNR,MAACT,"T","Line_tot",REQMSE)) ) $ (  p_emisFeed(RUNR,MAACT,"T","Line_tot","TotFAT")
                                                                      $ p_emisFeed(RUNR,MAACT,"T","Line_tot",REQMSE) )
    $endif.Lin1
    *
                   =E= 0.0;
    """
    return supply_flex + supply_fixed - 1.0


def REQSE_split(sup, v_actLevl, inv_X, d_z):
    r"""REQSE_ in the total form, where the herd's requirement moves with split or option columns: REQSE_'s per-head
    row (sup, from REQSE_) x the herd / X, minus the columns' terms d x z / (R X) (the caller's linear sum; X the herd's
    base level, at least 1e-3), = 0. CAPRI's GAMS: REQSE_'s docstring.
    """
    return sup * v_actLevl * inv_X - d_z


def FEDUSE_(v_actLevl, v_feedInpCoeff):
    r"""FEDUSE_(r, FEED) (l. 789-803), each animal's and feed's term: v_feedInpCoeff x v_actLevl (kg per head x 1000
    head = t); the non-tradable fodder's balances take each term / 1000 (CAPRI's v_feedQuantReg in 1000 t, substituted
    into SUPBAL_). CAPRI's straw and COMF losses (v_lossQuant) are not in the model's sum.

    CAPRI's GAMS, FEDUSE_ (l. 789-803):

       FEDUSE_(RUNR,FEED %addtimedim%) $ ( v_feedQuantReg.LO(RUNR,FEED %addtimedim%) ne v_feedQuantReg.UP(RUNR,FEED %addtimedim%) ) ..
    *
    *    ---  add up feed use over animals and alternatives (endogenous input coefficient in kg times
    *         herd size in 1000 animals), scaling to define feed use in 1000 t
    *
         SUM( (MAACT,A) $ p_maxFeedShare(RUNR,MAACT,A,FEED %addtimedim%),
    *
             v_feedInpCoeff(RUNR,MAACT,A,FEED %addtimedim%)*v_actLevl%over_time%(RUNR,MAACT,A %addtimedim%) ) / 1000.
    *
    *     --- permit some variation of straw v_lossQuant
    *
                          + v_lossQuant(RUNR,"STRA" %addtimedim%) $ SAMEAS(FEED,"FSTR")
                          + v_lossQuant(RUNR,"COMF" %addtimedim%) $ SAMEAS(FEED,"FCOM")
    *
                      =E= v_feedQuantReg(RUNR,FEED %addtimedim%);
    """
    return v_actLevl * v_feedInpCoeff
