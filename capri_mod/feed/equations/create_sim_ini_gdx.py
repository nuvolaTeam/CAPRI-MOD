r"""CAPRI's requirements and feed shares at the start of a simulation (capmod/create_sim_ini_gdx.gms l. 417-461; CAPRI
star 3.0): the requirement functions at the year's herds and yields with CAPREG's corrections and the technical progress
(capmod/def_requirements.gms, capri_mod/feed/equations/def_requirements.py), corrected by the baseline feed calibration
(baseline/adjust.gms, adjust.py), then the feed shares widened by the feeds' rows, the feeds the member state does not
use excluded, and the production days of the member states and of DATA.

CAPRI writes the result to sim_ini_<...>.gdx (p_animReq, p_animExcrProtCorrFact, p_minFeedShare, p_maxFeedShare,
p_animProdDays, DATA "DAYS"), the start of its simulation; capmod.gms l. 1055-1075 holds the same sequence for a
simulation without that file. The baseline (%BASELINE% on) widens the shares with the same statements
(capmod/def_fert_and_requirements.gms l. 52-57) after its calibration.

One function per CAPRI statement block, on the requirement call's state (req_or_man_fnc_req.ReqState) and
SimIniInputs; create_sim_ini_gdx_feed runs the sequence. Departures from CAPRI: none in the functions.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.feed.equations import adjust as adj
from capri_mod.feed.equations import def_requirements as dr
from capri_mod.feed.equations import req_or_man_fnc_req as rq


@dataclass
class SimIniInputs:
    """The inputs of the sequence besides the requirement call's state and def_requirements.DefReqInputs: MS,
    CAPRI's member states; MAP_RR, CAPRI's regional hierarchy {(aggregate, region)}; DATA_BAS_GROF, the member states'
    feed use at "BAS" {(member state, feed): t}; Y_IS_BAS: CALYEA("Y") = CALYEA("BAS"). Written: DATA_DAYS_Y,
    DATA(RS, MAACT, "Days", "Y") {(region, animal): days}."""
    MS: tuple
    MAP_RR: frozenset
    DATA_BAS_GROF: dict
    Y_IS_BAS: bool = False
    DATA_DAYS_Y: dict = field(default_factory=dict)


def p_FeedShare_widened(st: rq.ReqState, a: adj.AdjustInputs) -> None:
    r"""The minimum feed shares times one minus, the maximum shares (but 1) times one plus the feeds' rows of
    p_animReq; a maximum share above 0.9999 becomes 1.

    CAPRI's GAMS (capmod/create_sim_ini_gdx.gms l. 436-439):

          p_minFeedShare(RU,MAACT,A,FEED) $ p_minFeedShare(RU,MAACT,A,FEED) = p_minFeedShare(RU,MAACT,A,FEED) * (1.-p_animReq(RU,MAACT,A,FEED));
        *
          p_maxFeedShare(RU,MAACT,A,FEED) $ (p_maxFeedShare(RU,MAACT,A,FEED) NE 1)      = p_maxFeedShare(RU,MAACT,A,FEED) * (1+p_animReq(RU,MAACT,A,FEED));
          p_maxFeedShare(RU,MAACT,A,FEED) $ (p_maxFeedShare(RU,MAACT,A,FEED) GT 0.9999) = 1.0;

    The feeds' rows are those of the requirement functions (1, feed/req_or_man_fnc.gms l. 1525), times CAPREG's
    correction (about 0 for the feeds) plus 1, times 1.005 a year since the base year (def_requirements.gms l. 74) and
    the baseline calibration's correction (1 for the feeds, baseline/fedtrm_fin.gms l. 47): at 2030 from 2017 about
    1.067, so the minimum shares turn slightly negative and the maximum shares double (as in sim_ini_21730). In CAPREG,
    where the statements come from (capreg.gms l. 2163-2172, not for the "_pw" feed version), the rows were the
    estimated deviations from the shares (below 0.01 set to 0). Departures from CAPRI: none."""
    ru = set(a.RU)
    for dct, sign in ((st.p_minFeedShare, -1.), (st.p_maxFeedShare, 1.)):
        for k, v in list(dct.items()):
            r, c, t, f = k
            if r not in ru or c not in st.MAACT or f not in rq.FEED or not v:
                continue
            if sign > 0 and v == 1:
                continue
            dct[k] = v * (1. + sign * st.req(r, c, t, f))
    for k, v in list(st.p_maxFeedShare.items()):
        if k[0] in ru and k[1] in st.MAACT and k[3] in rq.FEED and v > 0.9999:
            st.p_maxFeedShare[k] = 1.0


def p_maxFeedShare_not_fed(st: rq.ReqState, a: adj.AdjustInputs, s: SimIniInputs) -> None:
    r"""No maximum share of a feed its member state does not use (at "BAS" in the base year, else at "TRD").

    CAPRI's GAMS (capmod/create_sim_ini_gdx.gms l. 444-445):

          p_maxFeedShare(RU,maact,A,FEED) $ (not sum(MAP_RR(MS,RU), DATA(MS,"GROF",FEED,"BAS") $ (calyea("Y") EQ calyea("BAS"))
                                                                  + DATA(MS,"GROF",FEED,"TRD") $ (calyea("Y") NE calyea("BAS"))))= 0;

    The member states' "TRD" of a member state that is a regional unit itself is the one baseline/adjust.gms l. 73
    recomputed. Departures from CAPRI: none."""
    ms_of: dict = {}
    for m, r in s.MAP_RR:
        if m in s.MS:
            ms_of.setdefault(r, []).append(m)
    ru = set(a.RU)
    for k in list(st.p_maxFeedShare):
        r, c, t, f = k
        if r not in ru or c not in st.MAACT or f not in rq.FEED:
            continue
        used = sum((s.DATA_BAS_GROF.get((m, f), 0.0) if s.Y_IS_BAS
                    else float(a.DATA_TRD.get((m, "GROF", f), 0.0) or 0.0)) for m in ms_of.get(r, ()))
        if not used:
            st.p_maxFeedShare[k] = 0


def p_animReq_feed_rows_erased(st: rq.ReqState, a: adj.AdjustInputs) -> None:
    r"""The feeds' rows of p_animReq erased (used up by the shares).

    CAPRI's GAMS (capmod/create_sim_ini_gdx.gms l. 447):

          p_animReq(RS,MAACT,A,FEED) = 0;

    RS: CAPRI's regional units of all levels; the call's st.RS. Departures from CAPRI: none."""
    rs = set(st.RS)
    for k in list(st.p_animReq):
        if k[0] in rs and k[1] in st.MAACT and k[3] in rq.FEED:
            del st.p_animReq[k]


def p_animProdDays_MS(st: rq.ReqState, d: dr.DefReqInputs, s: SimIniInputs) -> None:
    r"""The member states' production days: their regions' days weighted by the herds.

    CAPRI's GAMS (capmod/create_sim_ini_gdx.gms l. 457-459):

          p_animProdDays(MS,MAACT,A) $ (SUM(MAP_RR(MS,RU),v_actLevl.L(RU,MAACT,A)) gt eps)
            = SUM(MAP_RR(MS,RU),p_animProdDays(RU,MAACT,A) * v_actLevl.L(RU,MAACT,A))
            / SUM(MAP_RR(MS,RU),                             v_actLevl.L(RU,MAACT,A)) ;

    eps: GAMS's smallest positive number (the condition is a positive herd). Departures from CAPRI: none."""
    ru = set(d.RU)
    regs: dict = {}
    for m, r in s.MAP_RR:
        if m in s.MS and r in ru:
            regs.setdefault(m, []).append(r)
    for m, rr in regs.items():
        for c in st.MAACT:
            for t in rq.A_ALL:
                w = sum(d.v_actLevl_L.get((r, c, t), 0.0) for r in rr)
                if w > 0:
                    st.p_animProdDays[(m, c, t)] = sum(st.p_animProdDays.get((r, c, t), 0.0)
                                                       * d.v_actLevl_L.get((r, c, t), 0.0) for r in rr) / w


def DATA_DAYS(st: rq.ReqState, s: SimIniInputs) -> None:
    r"""The production days in DATA: the technologies' days weighted by their shares.

    CAPRI's GAMS (capmod/create_sim_ini_gdx.gms l. 461):

          DATA(RS,MAACT,"Days","Y") $ DATA(RS,MAACT,"LEVL","Y") = SUM(A, p_animProdDays(RS,MAACT,A) * p_technFact(RS,MAACT,"LEVL",A));

    Departures from CAPRI: none."""
    for r in st.RS:
        for c in st.MAACT:
            if st.D(r, c, "LEVL"):
                s.DATA_DAYS_Y[(r, c)] = sum(st.p_animProdDays.get((r, c, t), 0.0) * st.tf(r, c, "LEVL", t)
                                            for t in rq.A_ALL)


def create_sim_ini_gdx_feed(st: rq.ReqState, d: dr.DefReqInputs, a: adj.AdjustInputs, s: SimIniInputs) -> tuple:
    r"""CAPRI's sequence of capmod/create_sim_ini_gdx.gms l. 421-461 where %BASELINE% is off: def_requirements.gms (its
    l. 22 is create_sim_ini's l. 421), baseline/adjust.gms on def_requirements' protein factor, the shares widened, the
    unused feeds excluded, the feeds' rows erased, the member states' days and DATA's. Returns (st, d, a, s)."""
    dr.def_requirements(st, d)
    a.p_animExcrProtCorrFact_Y = d.p_animExcrProtCorrFact_Y
    adj.adjust(st, a)
    p_FeedShare_widened(st, a)
    p_maxFeedShare_not_fed(st, a, s)
    p_animReq_feed_rows_erased(st, a)
    p_animProdDays_MS(st, d, s)
    DATA_DAYS(st, s)
    return st, d, a, s
