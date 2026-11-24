r"""CAPRI's correction of the simulation year's requirements by its baseline feed calibration (baseline/adjust.gms;
CAPRI star 3.0): the requirements of def_requirements.gms (capri_mod/feed/equations/def_requirements.py) times the
calibration's corrections, the baseline's feed input coefficients as the start, and the feed use recomputed from them.

CAPRI runs it from capmod/create_sim_ini_gdx.gms l. 427 (and capmod.gms l. 1064) where %BASELINE% is off, after
def_requirements.gms. The corrections p_animReqCorrFac1 are the baseline calibration's p_animReqCorrFac
(baseline/fedtrm_fin.gms l. 47-48: the calibrated requirement over the requirement function's, 1 for the feeds' rows),
which capmod/load_feed.gms l. 71-76 loads from results/baseline/fedtrm_<...>.gdx; the feed input coefficients
p_feedInpCoeffLoad are the baseline's solution (l. 36-43: results/baseline/mefed_<...>.gdx).

One function per CAPRI statement block, on the requirement call's state (req_or_man_fnc_req.ReqState) and AdjustInputs.
CAPRI's feed version is "_pw" (star 3.0's default: feed/fedtrm_cal_pw.gms), so l. 51 and l. 57 apply and l. 50 does
not. CAPRI's REQM is its REQSR (sets.gms). Departures from CAPRI: none in the functions.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.feed.equations import req_or_man_fnc_req as rq


@dataclass
class AdjustInputs:
    """The inputs of baseline/adjust.gms besides the requirement call's state: RU, CAPRI's regional units;
    p_animReqCorrFac1, the baseline calibration's corrections {(region, animal, A, requirement or feed): factor}
    (absolute: the requirement is multiplied by it; an absent entry is CAPRI's 0); p_animExcrProtCorrFact_Y, the
    manure's protein factor at "Y" {(region, animal, A): factor} (def_requirements.py's, changed in place);
    p_feedInpCoeffLoad, the baseline's feed input coefficients {(region, animal, A, feed): kg per head};
    DATA_TRD, DATA at "TRD" {(region, column, row): value} (its GROF rows recomputed in place).
    Written: v_feedInpCoeff_L, the feed input coefficients' start {(region, animal, A, feed): kg per head}."""
    RU: tuple
    p_animReqCorrFac1: dict
    p_animExcrProtCorrFact_Y: dict
    p_feedInpCoeffLoad: dict
    DATA_TRD: dict
    v_feedInpCoeff_L: dict = field(default_factory=dict)


def p_animReq_corrected(st: rq.ReqState, a: AdjustInputs) -> None:
    r"""The requirements and the feeds' rows times the baseline calibration's corrections. A requirement without a
    correction becomes 0, as in CAPRI (the product with an absent entry).

    CAPRI's GAMS (baseline/adjust.gms l. 26-27):

           p_animReq(RU,MAACT,A,REQM)  $ (p_animReq(RU,MAACT,A,REQM) or sum(sameas(REQM,FEED),1))
              = p_animReq(RU,MAACT,A,REQM) * p_animReqCorrFac1(RU,MAACT,A,REQM);

    Departures from CAPRI: none."""
    ru = set(a.RU)
    for k, v in list(st.p_animReq.items()):
        r, c, t, item = k
        # $ (p_animReq or a feed's row): an absent feed row stays absent (0 times the correction)
        if r in ru and c in st.MAACT and item in rq.REQSR and v:
            st.p_animReq[k] = v * a.p_animReqCorrFac1.get(k, 0.0)


def p_animExcrProtCorrFact_corrected(st: rq.ReqState, a: AdjustInputs) -> None:
    r"""The manure's protein factor times the calibration's correction of the crude protein.

    CAPRI's GAMS (baseline/adjust.gms l. 31-32):

           p_animExcrProtCorrFact(RU,MAACT,A,"Y") $ p_technFact(RU,MAACT,"LEVL",A)
              = p_animExcrProtCorrFact(RU,MAACT,A,"Y") * p_animReqCorrFac1(RU,MAACT,A,"CRPR");

    Departures from CAPRI: none."""
    for (r, c, t), v in list(a.p_animExcrProtCorrFact_Y.items()):
        if r in a.RU and c in st.MAACT and st.tf(r, c, "LEVL", t):
            a.p_animExcrProtCorrFact_Y[(r, c, t)] = v * a.p_animReqCorrFac1.get((r, c, t, "CRPR"), 0.0)


def v_feedInpCoeff_start(st: rq.ReqState, a: AdjustInputs) -> None:
    r"""The feed input coefficients start at the baseline's (CAPRI's feed version "_pw"), and a feed the baseline did
    not feed gets no maximum share (it is not introduced).

    CAPRI's GAMS (baseline/adjust.gms l. 51-57):

        $ifi "%feedversion%"=="_pw" v_feedInpCoeff.l(RU,MAACT,A,FEED) = p_feedInpCoeffLoad(RU,MAACT,A,FEED);
             v_feedInpCoeff.m(RALL,MAACT,A,FEED)  = 0;
             v_feedInpCoeff.up(RALL,MAACT,A,FEED) = inf;

        *  --- Do not introduce FEED that was not present in baseline calibration:

        $ifi "%feedversion%"=="_pw" p_maxFeedShare(RU,MAACT,A,FEED) $ (not v_feedInpCoeff.l(RU,MAACT,A,FEED)) = 0;

    The marginals and the upper bounds (l. 52-53) are the solver's (capri_mod's regional model sets its own).
    Departures from CAPRI: none."""
    ru = set(a.RU)
    a.v_feedInpCoeff_L.update({k: v for k, v in a.p_feedInpCoeffLoad.items() if k[0] in ru})
    for k in list(st.p_maxFeedShare):
        r, c, t, f = k
        if r in ru and c in st.MAACT and f in rq.FEED and not a.v_feedInpCoeff_L.get(k, 0.0):
            st.p_maxFeedShare[k] = 0


def DATA_GROF_TRD(st: rq.ReqState, a: AdjustInputs) -> None:
    r"""The trend's feed use recomputed from the feed input coefficients, and no minimum share of a fodder the region
    hardly feeds (1 t or less).

    CAPRI's GAMS (baseline/adjust.gms l. 73-77):

         DATA(RU,"GROF",FEED,"TRD")
            = SUM( (MAACT,A) $ p_technFact(RU,MAACT,"LEVL",A), DATA(RU,MAACT,"LEVL","TRD")*v_feedInpCoeff.L(RU,MAACT,A,FEED)*p_technFact(RU,MAACT,"LEVL",A)) * 0.001;


         p_minFeedShare(RU,maact,A,FODDI) $ (DATA(RU,"GROF",FODDI,"TRD") le 1.E-3) = 0;

    Departures from CAPRI: none."""
    for r in a.RU:
        tot: dict = {}
        for (rr, c, t, f), v in a.v_feedInpCoeff_L.items():
            if rr == r and c in st.MAACT and f in rq.FEED and st.tf(r, c, "LEVL", t):
                levl = float(a.DATA_TRD.get((r, c, "LEVL"), 0.0) or 0.0)
                tot[f] = tot.get(f, 0.0) + levl * v * st.tf(r, c, "LEVL", t)
        for f in rq.FEED:
            a.DATA_TRD[(r, "GROF", f)] = tot.get(f, 0.0) * 0.001
    for k in list(st.p_minFeedShare):
        r, c, t, f = k
        if r in a.RU and c in st.MAACT and f in rq.FODDI and a.DATA_TRD.get((r, "GROF", f), 0.0) <= 1.E-3:
            st.p_minFeedShare[k] = 0


BLOCKS = (p_animReq_corrected, p_animExcrProtCorrFact_corrected, v_feedInpCoeff_start, DATA_GROF_TRD)


def adjust(st: rq.ReqState, a: AdjustInputs) -> tuple:
    r"""CAPRI's baseline/adjust.gms where the base and the simulation year differ: the blocks above in CAPRI's order.
    Returns (st, a)."""
    for block in BLOCKS:
        block(st, a)
    return st, a
