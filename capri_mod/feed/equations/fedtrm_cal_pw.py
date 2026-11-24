r"""CAPRI's baseline feed calibration (feed/fedtrm_cal_pw.gms; CAPRI star 3.0, feed version "_pw"): the estimation model
m_hpdFeed (feed/fedtrm_mod_pw.gms) solved for each member state from the top down, and its result stored as the
calibrated requirements.

Ported so far: the statements after a solve (l. 759-812) that turn the solution's feed input coefficients into the
calibrated requirements: the energy and protein requirements recomputed from the ration, the inequality requirements
(dry matter, fibre, lysine) at the ration where the ration needs less, and the uncorrected requirements kept for the
corrections of baseline/fedtrm_fin.gms (capri_mod/feed/equations/fedtrm_fin.py). The priors (feed/fedtrm_prior_pw.gms),
the model and its driver (l. 23-756) are the plan's S3b (claude/feed_calibration_port_plan_2026-11-24.md).

One function per CAPRI statement block, on CalState. Departures from CAPRI: none in the functions.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.feed.equations import req_or_man_fnc_req as rq

#: CAPRI's requirement sets (sets.gms): REQMSE the equalities, REQMSN the inequalities
REQMSE = ("ENNE", "CRPR")
REQMSN = ("DRMN", "DRMX", "LISI", "FICO", "FICT", "FISM", "FISF", "FIDI", "FILG")


@dataclass
class CalState:
    """CAPRI's symbols of the calibration of one set of regional units RUNR (CAPRI's dynamic set): p_animReq, the
    requirements per head and day {(region, animal, A, item): value} (changed in place: the calibrated ones);
    v_feedInpCoeff_L, the solution's
    feed input coefficients {(region, animal, A, feed): kg per head and year}; p_animProdDays {(region, animal, A):
    days}; p_maxFeedShare {(region, animal, A, feed): share}; DATA_content, the member states' contents
    {(member state, requirement, feed): per kg fresh matter}; R_RAGG_MS {region: its member state}; DATA_LEVL {(region,
    animal): herd}; v_animReq_L, the requirements' levels (written)."""
    RUNR: tuple
    MAACT: tuple
    p_animReq: dict
    v_feedInpCoeff_L: dict
    p_animProdDays: dict
    p_maxFeedShare: dict
    DATA_content: dict
    R_RAGG_MS: dict
    DATA_LEVL: dict
    v_animReq_L: dict = field(default_factory=dict)
    #: the uncorrected equality requirements during the statements after a solve (CAPRI's v_animReq.Scale)
    v_animReq_Scale: dict = field(default_factory=dict)

    def ration(self, r, a, t, item) -> float:
        """SUM(FEED $ p_maxFeedShare, v_feedInpCoeff.L * SUM(R_RAGG(RUNR, MSACT), DATA(MSACT, item, FEED, "Y")))."""
        m = self.R_RAGG_MS.get(r, r)
        return sum(self.v_feedInpCoeff_L.get((r, a, t, f), 0.0) * float(self.DATA_content.get((m, item, f), 0.0) or 0.0)
                   for f in rq.FEED if self.p_maxFeedShare.get((r, a, t, f), 0.0))


def v_animReq_start(c: CalState) -> None:
    r"""The requirements' levels start at the requirements (the inequality rows keep them: m_hpdFeed has no inequality
    requirement rows; the equality rows' levels are the solve's and are recomputed after it, v_animReq_from_ration).

    CAPRI's GAMS (feed/fedtrm_cal_pw.gms l. 275):

                v_animReq.L(RUNR,maact,A,REQM)     = p_animReq(RUNR,maact,A,REQM);

    Departures from CAPRI: none."""
    ru = set(c.RUNR)
    for k, v in c.p_animReq.items():
        if k[0] in ru and k[1] in c.MAACT and k[3] in rq.REQSR:
            c.v_animReq_L[k] = v


def v_animReq_DRMX(c: CalState) -> None:
    r"""The maximum dry matter intake at least 1.2 times the minimum (it is negative: at most -1.2 x DRMN).

    CAPRI's GAMS (feed/fedtrm_cal_pw.gms l. 762-763):

                    v_animReq.L(RUNR,maact,A,"DRMX")  $ v_animReq.L(RUNR,maact,A,"DRMX") =
                         MIN(v_animReq.L(RUNR,maact,A,"DRMX"),-(v_animReq.L(RUNR,maact,A,"DRMN") * 1.2));

    Departures from CAPRI: none."""
    for (r, a, t, item), v in list(c.v_animReq_L.items()):
        if item == "DRMX" and r in c.RUNR and a in c.MAACT and v:
            c.v_animReq_L[(r, a, t, item)] = min(v, -(c.v_animReq_L.get((r, a, t, "DRMN"), 0.0) * 1.2))


def v_animReq_from_ration(c: CalState) -> None:
    r"""The uncorrected requirements kept (CAPRI keeps them in v_animReq.Scale); the energy and protein requirements
    recomputed from the solution's ration per day; the inequality requirements at the ration's where it is lower.

    CAPRI's GAMS (feed/fedtrm_cal_pw.gms l. 789-802):

                    v_animReq.Scale(RUNR,maact,A,REQMSE) = p_animReq(RUNR,maact,A,REQMSE);
        *
        *           --- recalculate requirements for equality restriction from feeding coefficients to
        *               avoid tiny infeasibilities in calibration step
        *
                    v_animReq.l(RUNR,maact,A,REQMSE) $ p_animProdDays(RUNR,maact,A)
                                  = SUM(FEED $ p_maxFeedShare(RUNR,maact,A,FEED), v_feedInpCoeff.L(RUNR,maact,A,FEED)
                                      * SUM(R_RAGG(RUNR,MSACT),DATA(MSACT,REQMSE,FEED,"Y")))/p_animProdDays(RUNR,maact,A);

        *
                    v_animReq.l(RUNR,maact,A,REQMSN) $ (p_animProdDays(RUNR,maact,A) and v_animReq.l(RUNR,maact,A,REQMSN))
                                  =  MIN(v_animReq.l(RUNR,maact,A,REQMSN),
                                      SUM(FEED $ p_maxFeedShare(RUNR,maact,A,FEED), v_feedInpCoeff.L(RUNR,maact,A,FEED)
                                         * SUM(R_RAGG(RUNR,MSACT),DATA(MSACT,REQMSN,FEED,"Y")))/p_animProdDays(RUNR,maact,A));

    Returns nothing; the kept requirements go to c.v_animReq_Scale. Departures from CAPRI: none."""
    ru = set(c.RUNR)
    c.v_animReq_Scale = {k: v for k, v in c.p_animReq.items() if k[0] in ru and k[1] in c.MAACT and k[3] in REQMSE}
    keys = {(r, a, t) for (r, a, t) in c.p_animProdDays if r in ru and a in c.MAACT}
    for (r, a, t) in keys:
        days = c.p_animProdDays.get((r, a, t), 0.0)
        if not days:
            continue
        for item in REQMSE:
            v = c.ration(r, a, t, item) / days
            if v or (r, a, t, item) in c.v_animReq_L:
                c.v_animReq_L[(r, a, t, item)] = v
        for item in REQMSN:
            cur = c.v_animReq_L.get((r, a, t, item), 0.0)
            if cur:
                c.v_animReq_L[(r, a, t, item)] = min(cur, c.ration(r, a, t, item) / days)


def p_animReq_calibrated(c: CalState) -> None:
    r"""The calibrated energy and protein requirements stored on p_animReq, the uncorrected ones on the levels.

    CAPRI's GAMS (feed/fedtrm_cal_pw.gms l. 807-812):

                    p_animReq(RUNR,maact,A,REQMSE) $ DATA(RUNR,maact,"LEVL","Y") = v_animReq.L(RUNR,maact,A,REQMSE);
        *
        *            --- assign the UNCORRECTED requirements to v_animReq.L
        *
                    v_animReq.L(RUNR,maact,A,REQMSE)     = v_animReq.Scale(RUNR,maact,A,REQMSE);
                    v_animReq.Scale(RUNR,maact,A,REQMSE) = 0.;

    Departures from CAPRI: none."""
    ru = set(c.RUNR)
    for (r, a, t, item), v in list(c.v_animReq_L.items()):
        if item in REQMSE and r in ru and a in c.MAACT and c.DATA_LEVL.get((r, a), 0.0):
            c.p_animReq[(r, a, t, item)] = v
    for k in [k for k in c.v_animReq_L if k[3] in REQMSE and k[0] in ru and k[1] in c.MAACT]:
        c.v_animReq_L[k] = c.v_animReq_Scale.get(k, 0.0)
    c.v_animReq_Scale = {}


BLOCKS_AFTER_SOLVE = (v_animReq_DRMX, v_animReq_from_ration, p_animReq_calibrated)


def after_solve(c: CalState) -> CalState:
    r"""CAPRI's statements after a successful solve of m_hpdFeed (feed/fedtrm_cal_pw.gms l. 759-812, but the restart
    copy p_animReqCopy and the straw's DATA, l. 759-760 and 767-785, not ported yet): BLOCKS_AFTER_SOLVE in order."""
    for block in BLOCKS_AFTER_SOLVE:
        block(c)
    return c
