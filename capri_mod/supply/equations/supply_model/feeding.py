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

Written since 24 November 2026: the rows of the baseline feed calibration's model m_hpdFeed (feed/fedtrm_mod_pw.gms
l. 294-300, capri_mod/feed/equations/fedtrm_mod_pw.py) in CAPRI's form, unscaled: REQSE_trim, NutContFeed_ (l. 693-705),
FeedAggrShare_ (l. 751-755), FEDUSE_row, FEDUSEA_ (l. 807-811), FEDUSES_ (l. 815-819) and FEDAGGR_ (l. 823-827).

Written since 21 November 2026 (KNOWN_ISSUES K93): SupplementPerc_ (l. 608-633; ghgAbatement), the limit of the ration's
fat with linseed (a column of the regional model, supplement_effects.csv), in the total form below; its slack's penalty in
GHG_Mit_Cost_ is mitigation.py GHG_Mit_Cost_supplementSlack.

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


def SupplementPerc_(fat_feeds_per_head, inv_DRMA_days, ShrOfDM, v_Miti_heads, v_actLevl, inv_X0, v_supplementPerc,
                    v_supplementSlack):
    r"""SupplementPerc_(r, a, Line_tot) (l. 608-633) as the NLP's row, in the total form: CAPRI's row (the ration's fat as
    a share of the dry-matter intake = v_supplementPerc + v_supplementSlack) times the herd over its base level, so that
    the share of linseed v = z / X enters as the heads adopting z, = 0.

    CAPRI's GAMS, SupplementPerc_ (l. 606-633):

        *        --- for the mitigation technology of feeding additional lipids from Linseed (OFLA) the maximum
        *            of total fat must be below 5% of DM intake
             SupplementPerc_(RUNR,MAACT,SupplTechTot)
                                      $ (CATACT(MAACT)
                                      $ (p_animReq(RUNR,MAACT,"T","DRMA")*p_animProdDays(RUNR,MAACT,"T"))
                                      $ p_technFact(RUNR,MAACT,"LEVL","T")
                                      $ (sameas(SupplTechTot,"line_tot"))
                                      $ sum((R_RAGG(RUNR,MSACT)), mitiTech_map(MSACT,MAACT,SupplTechTot,"CH4ENT")))..

        *     fat in the feed bulks
                  [ SUM(FEED $ (sameas(SupplTechTot,"Line_tot") $ p_maxFeedShare(RUNR,MAACT,"T",FEED)),
                        v_feedInpCoeff(RUNR,MAACT,"T",FEED)
                          * sum(R_RAGG(RUNR,MSACT),p_emisFeed(RUNR,MAACT,"T",FEED,"TotFAT")))

        *     fat in the feed additive lineseed added
                  + p_animReq(RUNR,MAACT,"T","DRMA") * p_animProdDays(RUNR,MAACT,"T")
        *           ... from max capacity
                  * sum(R_RAGG(RUNR,MSACT),p_emisFeed(RUNR,MAACT,"T",SupplTechTot,"ShrOfDM"))
        *          ... times actual use of this capacity (=> gives actual intake of fat from line seed)
                  * v_miti(RUNR,MAACT,SupplTechTot,"CH4ENT")]

        *     as a share of DM intake
              / [p_animReq(RUNR,MAACT,"T","DRMA") * p_animProdDays(RUNR,MAACT,"T")]

                     =E=

        *                                                 Slack = excess beyond 5% (heavily penalised)
              v_supplementPerc(RUNR,MAACT,SupplTechTot) + v_supplementSlack(RUNR,MAACT,SupplTechTot);

    Bounds (supply/set_miti_bounds.gms l. 471-476), the NLP's variable bounds: 0 <= v_supplementPerc <= 0.05,
    v_supplementSlack >= 0.

        v_supplementPerc.up(%REGIONS%,PACT,"line_tot") $ sum(R_RAGG(%REGIONS%,NUTS0),mitiTech_map(NUTS0,PACT,"line_tot","CH4ENT"))
         = .05;
        v_supplementPerc.lo(%REGIONS%,PACT,"line_tot") $ sum(R_RAGG(%REGIONS%,NUTS0),mitiTech_map(NUTS0,PACT,"line_tot","CH4ENT"))
         = 0;
        v_supplementSlack.lo(%REGIONS%,PACT,"line_tot") $ sum(R_RAGG(%REGIONS%,NUTS0),mitiTech_map(NUTS0,PACT,"line_tot","CH4ENT"))
         = 0;

    In this project's notation, for a cattle animal a with herd X (1000 head; X0 at base), per-head feeds u_f (kg as fed;
    the fixed feeds at their base amounts), TotFAT_f the feed bulks' fat per kg (supplement_fat.csv; envind/
    line_nitr.gms l. 175-176), D the dry-matter intake per head and year (CAPRI's p_animReq(DRMA) x p_animProdDays), sh
    = ShrOfDM (linseed's fat as a share of the dry matter, 5%), z the heads adopting (CAPRI's v_Miti x v_actLevl), p and
    s the percentage and its slack:

        CAPRI:  (sum_f u_f TotFAT_f + D sh z / X) / D = p + s
        here:   (sum_f u_f TotFAT_f / D - p - s) X / X0 + sh z / X0 = 0

    the same row times X / X0 (X > 0). The caller passes the feeds' fat per head (fat_feeds_per_head), 1 / D, X and
    1 / X0. Departures from CAPRI: D is the model's dry-matter intake per head of supplement_effects.csv (tools/build/
    build_supplement_effects.py: breeding.gms's estimate DRMN + (|DRMX| - DRMN) / 4, the basis of the linseed column's
    dosage and cost), at the run's requirements; the model's animals each carry one row where CAPRI has one per activity
    (DCOW for DCOL and DCOH, ...), with the feed bulks' fat of its activities (they differ only by the grazing share,
    which its activities share)."""
    return ((fat_feeds_per_head * inv_DRMA_days - v_supplementPerc - v_supplementSlack) * v_actLevl * inv_X0
            + ShrOfDM * v_Miti_heads * inv_X0)


# --- the rows of the baseline feed calibration's model m_hpdFeed (feed/fedtrm_mod_pw.gms l. 294-300;
#     capri_mod/feed/equations/fedtrm_mod_pw.py), in CAPRI's form: unscaled, with p_trimFeed = 1

def REQSE_trim(v_animReq, p_animProdDays, ration):
    r"""REQSE_(r, a, A, REQMSE) (l. 561-602) as m_hpdFeed has it: the requirement a variable (p_trimFeed = 1,
    feed/fedtrm_cal_pw.gms l. 32) times the days, minus the ration's supply (the caller's SUM over the feeds with a
    maximum share of v_feedInpCoeff x the member state's content, DATA(MSACT, REQMSE, FEED)), = 0. CAPRI's GAMS:
    REQSE_'s docstring.

    Departures from CAPRI: none. The terms of %ghgAbatement% are not in the row: CAPRI's baseline runs with it off
    (capmod/set_global_variables.gms l. 215; the policy files of the GHG scenarios set it on)."""
    return v_animReq * p_animProdDays - ration


def NutContFeed_(v_NutContFeed, nut, drma):
    r"""NutContFeed_(r, a, A, REQMSE, FeedAggr) (l. 693-705): the aggregate's content of the requirement per kg dry
    matter, v_NutContFeed = nut / (drma + 0.0001), with nut the SUM over the aggregate's feeds of v_feedInpCoeff x the
    member state's content of the requirement and drma the same with its dry matter (the caller's sums), as
    v_NutContFeed - nut / (drma + 0.0001) = 0.

    CAPRI's GAMS, NutContFeed_ (l. 690-705):

        *
        *   --- nutrition content in total feed of animal category (energy and protein per kg dry matter: for calibration)
        *
             NutContFeed_(RUNR,MAACT,A,REQMSE,FeedAggr %addtimedim%) $ (   p_NutContFeed(RUNR,MAACT,A,REQMSE,FeedAggr,"MIN" %addtimedim%)
                                                          or  p_NutContFeed(RUNR,MAACT,A,REQMSE,FeedAggr,"MAX" %addtimedim%)
                                                          or  p_nutContFeed(RUNR,MAACT,A,REQMSE,FeedAggr,"MEAN" %addtimedim%)) ..
        *
             v_NutContFeed(RUNR,MAACT,A,REQMSE,FeedAggr %addtimedim%) =E=
        *           nutrition in feed diveded by dry matter of feed
                    SUM((Feed_FeedAggr(FEED,FeedAggr)),
                             v_feedInpCoeff(RUNR,MAACT,A,FEED  %addtimedim%)
                                 * SUM(R_RAGG(RUNR,MSACT),%data%(MSACT,REQMSE,FEED,%timedim%)))

                    / (SUM((Feed_FeedAggr(FEED,FeedAggr)),
                             v_feedInpCoeff(RUNR,MAACT,A,FEED  %addtimedim%)
                                 * SUM(R_RAGG(RUNR,MSACT),%data%(MSACT,"DRMA",FEED,%timedim%))) + 0.0001);

    Departures from CAPRI: none."""
    return v_NutContFeed - nut / (drma + 0.0001)


def FeedAggrShare_(v_feedInpCoeff_aggr, v_feedInpCoeff_FeedTotal, v_FeedAggrShare):
    r"""FeedAggrShare_(r, a, A, FeedAggr) (l. 751-755): the aggregate's share of the dry matter intake (both
    v_feedInpCoeff of the aggregates, in dry matter by FEDAGGR_), as v_feedInpCoeff(FeedAggr) / (v_feedInpCoeff(
    "FeedTotal") + 1E-12) - v_FeedAggrShare = 0.

    CAPRI's GAMS, FeedAggrShare_ (l. 749-755):

        *        --- calculate share of concentrate and roughage (for calibration)
        *
             FeedAggrShare_(RUNR,MAACT,A,FeedAggr %addtimedim%) $ (  p_animReq(RUNR,MAACT,A,"DRMA" %addtimedim%)) ..
        *
                      v_feedInpCoeff(RUNR,MAACT,A,FeedAggr %addtimedim%) / (v_feedInpCoeff(RUNR,MAACT,A,"FeedTotal" %addtimedim%) + 1E-12)

                                         =E= v_FeedAggrShare(RUNR,MAACT,A,FeedAggr %addtimedim%) ;

    Departures from CAPRI: none."""
    return v_feedInpCoeff_aggr / (v_feedInpCoeff_FeedTotal + 1E-12) - v_FeedAggrShare


def FEDUSE_row(use_t, v_lossQuant_STRA, v_lossQuant_COMF, v_feedQuantReg):
    r"""FEDUSE_(r, FEED) (l. 789-803) as m_hpdFeed has it: the feed use of the animals (the caller's SUM of FEDUSE_'s
    terms, v_feedInpCoeff x v_actLevl in t) / 1000, plus the straw's losses for FSTR and COMF's for FCOM (the caller
    passes 0 for the other feeds), minus v_feedQuantReg (1000 t), = 0. CAPRI's GAMS: FEDUSE_'s docstring.

    Departures from CAPRI: none."""
    return use_t / 1000. + v_lossQuant_STRA + v_lossQuant_COMF - v_feedQuantReg


def FEDUSEA_(use_units, v_feedInpCoeff_RUNAGG, v_actLevl_RUNAGG):
    r"""FEDUSEA_(RUNAGG, a, A, FEED) (l. 807-811): the units' feed use of the animal (the caller's SUM over RUNR with a
    maximum share of v_feedInpCoeff x v_actLevl) equals the aggregate's, as use_units minus the aggregate's
    coefficient times its herd = 0.

    CAPRI's GAMS, FEDUSEA_ (l. 805-811):

        * ---------- recover average coefficient (needed in calibration step) ------------------------
        *                                                                                                 $ (v_feedInpCoeff.UP(RUNAGG,MAACT,A,FEED) NE 0)   $ capreg
            FEDUSEA_(RUNAGG,MAACT,A,FEED %addtimedim%) $ (p_maxFeedShare(RUNAGG,MAACT,A,FEED %addtimedim%)
                                             $ (SUM(RUNR, 1.) NE 1.)  $ ((not FODDI(FEED)) or (SAMEAS(FEED,"FSTR")) )) ..
        *
              SUM( RUNR $ p_maxFeedShare(RUNR,MAACT,A,FEED %addtimedim%), v_feedInpCoeff(RUNR,MAACT,A,FEED %addtimedim%)*v_actLevl%over_time%(RUNR,MAACT,A %addtimedim%))
                 =E= v_feedInpCoeff(RUNAGG,MAACT,A,FEED %addtimedim%)*v_actLevl%over_time%(RUNAGG,MAACT,A %addtimedim%);

    Departures from CAPRI: none."""
    return use_units - v_feedInpCoeff_RUNAGG * v_actLevl_RUNAGG


def FEDUSES_(v_feedQuantReg, p_feedQuant):
    r"""FEDUSES_(r, FEED) (l. 815-819): the regional feed use fixed at the given quantity, as v_feedQuantReg -
    p_feedQuant = 0.

    CAPRI's GAMS, FEDUSES_ (l. 813-819):

        * ---------- fix sectoral feed use or use of non-tradeable feed (needed in calibration step) --
        *
            FEDUSES_(RUNR,FEED %addtimedim%) $  (p_feedQuant(RUNR,FEED %addtimedim%) GT 1.E-6)..
        *
              v_feedQuantReg(RUNR,FEED %addtimedim%)

            =E= p_feedQuant(RUNR,FEED %addtimedim%);

    Departures from CAPRI: none."""
    return v_feedQuantReg - p_feedQuant


def FEDAGGR_(v_feedInpCoeff_aggr, drma):
    r"""FEDAGGR_(r, a, A, FeedAggr) (l. 823-827): the aggregate's coefficient is its feeds' dry matter (the caller's
    SUM over the aggregate's feeds of v_feedInpCoeff x the member state's DRMA), as v_feedInpCoeff(FeedAggr) - drma = 0.

    CAPRI's GAMS, FEDAGGR_ (l. 821-827):

        * ---------- aggregate to roughage, concentrate feed, etc (in DRMA, needed in calibration step) ------------------------
        *
            FEDAGGR_(RUNR,MAACT,A,FeedAggr %addtimedim%) $ p_technFact(RUNR,MAACT,"LEVL",A) ..
        *
              v_feedInpCoeff(RUNR,MAACT,A,FeedAggr %addtimedim%)
                =E= SUM(Feed_FeedAggr(Feed,FeedAggr), v_feedInpCoeff(RUNR,MAACT,A,FEED %addtimedim%)
                                                    * SUM(R_RAGG(RUNR,MSACT),%data%(MSACT,"DRMA",FEED,%timedim%)));

    Departures from CAPRI: none."""
    return v_feedInpCoeff_aggr - drma
