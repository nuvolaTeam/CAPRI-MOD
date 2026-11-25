r"""CAPRI's baseline feed calibration (feed/fedtrm_cal_pw.gms; CAPRI star 3.0, feed version "_pw"): the estimation model
m_hpdFeed (feed/fedtrm_mod_pw.gms, capri_mod/feed/equations/fedtrm_mod_pw.py) solved for each member state from the top
down, and its result stored as the calibrated requirements and the data's feeding.

The driver (l. 23-886), on FedtrmState (capri_mod/feed/equations/fedtrm_prep.py) after fedtrm_prep and fedtrm_prior_pw:
by regional level (CAPRI's R_LEVL) the aggregates RAGG; for each, its units RUNR and its aggregate RUNAGG, the priors of
the requirements, the herds fixed, the bounds and the start (setup_RAGG), the solve, CAPRI's re-solves after an
infeasible solve or one with tiny coefficients, and the statements after the final solve (store_results): the
calibrated energy and protein requirements recomputed from the ration, the inequality requirements (dry matter,
fibre, lysine) at the ration where the ration needs less, the uncorrected requirements kept for the corrections of
baseline/fedtrm_fin.gms (capri_mod/feed/equations/fedtrm_fin.py), the straw's balance and the feeding in DATA.

One function per CAPRI statement block, on FedtrmState (the statements after a solve on CalState, a view of it).
Departures from CAPRI: the solver (IPOPT) and CST_ (fedtrm_mod_pw.py); the start of the units' average intake
FeedTotalSubRegionAvg at 1 (FeedTotalSubRegionAvg_start: from CAPRI's 0, IPOPT stops early); no restart point
(CAPRI's mefed file of an earlier baseline is not in the material: CAPRI's own fallback start); the aggregates of a
level solved one after the other (CAPRI's grid solves them in parallel; their units are disjoint); the functions'
own. Not ported: the farm
types (CAPRI's baseline runs without), the restart copies, the checking parameters p_feedDetail, p_feed and
p_feedPlus001DM (l. 889-979), and the copy of DATA by member state (l. 69-90, 881-885 and 981-986, a memory device:
the port's state holds one member state).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.data.definitions import capri_set
from capri_mod.feed.equations import fedtrm_mod_pw as mp
from capri_mod.feed.equations import req_or_man_fnc_req as rq
from capri_mod.feed.equations.fedtrm_mod_pw import INF

#: CAPRI's requirement sets (sets.gms; capri_data/codes/capri): REQMSE the equalities, REQMSN the inequalities
REQMSE = capri_set("REQMSE")
REQMSN = capri_set("REQMSN")


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
    r"""CAPRI's statements after a successful solve of m_hpdFeed that turn the ration into the calibrated requirements
    (feed/fedtrm_cal_pw.gms l. 762-812, but the straw's DATA, l. 767-785, in store_results): BLOCKS_AFTER_SOLVE in
    order, on CalState alone (tools/check/check_fedtrm_after_solve_2030.py)."""
    for block in BLOCKS_AFTER_SOLVE:
        block(c)
    return c


# --- the driver (feed/fedtrm_cal_pw.gms l. 23-756 and 757-847): for one member state on FedtrmState st after
#     fedtrm_prep and fedtrm_prior_pw; one function per CAPRI statement block

#: CAPRI's limits of the solves (feed/fedtrm_mod_pw.gms l. 52-53): at most 20 further solves of a set of units, and no
#: opening of the bounds by the solver's marginals
p_nSolveMax = 20
p_BoundOpening = 0


def RAGG_of_level(st, R_LEVL: str) -> tuple:
    r"""The aggregates solved at a regional level (CAPRI's RAGG): at "TOP" the member state alone (RAGG "TOP"); at "MS"
    the member state if it has NUTS 1 or NUTS 2 units below it; at "NUTS1" its NUTS 1 units that have NUTS 2 units
    below them; at "Nuts2" the farm types' regions (none: CAPRI's baseline runs without farm types); then every
    aggregate but "TOP" with at most one region of RSEU mapped to it dropped. NUTS1 is the member state's SRNUTS1 and
    NUTS2 its regional units RU (baseline/fedtrm_prep.gms, fedtrm_prep.py).

    CAPRI's GAMS (feed/fedtrm_cal_pw.gms l. 104-135):

                  option kill=RAGG;
                  IF ( SAMEAS(R_LEVL,"TOP"),
        *
        *             --- the "TOP" level only solve the equation for the member State,
        *                without NUTS I or NUTS II regions
        *
                     RAGG("TOP") = YES;
                  elseif ( SAMEAS(R_LEVL,"MS") ),
        *
        *             --- Member state level: included if there are NUTS I regions or if there are NUTS 2 regions in the Member State
        *
                      RAGG(MS)    $ (SUM(MAP_RR(MS,NUTS1) $ (NOT SAMEAS(MS,NUTS1)),1) or SUM(MAP_RR(MS,NUTS2) $ (NOT SAMEAS(MS,NUTS2)),1)) = YES;

                  elseif ( SAMEAS(R_LEVL,"NUTS1") ),
        *
        *             --- NUTS 1 level: included if the NUTS I regions comprise NUTS II regions, and if NUTS1 is not equal MS
        *
                     RAGG(NUTS1) $ (MAP_RR(MS,NUTS1) and (NOT SAMEAS(MS,NUTS1)) and SUM(MAP_RR(NUTS1,NUTS2) $ (NOT SAMEAS(NUTS1,NUTS2)),1)) = YES;

                  else
        *
        *            --- NUTS 2 level: included if farm types are present for the NUTS II region
        *
                     RAGG(NUTS2)  $ (SUM(Types_to_r(NUTS2,Types),1) and MAP_RR(MS,NUTS2) and CARD(Types)) = YES;
        $ifi %FARM_B%==on        MAP_RR(RAGG,Types) $ (Types_to_r(RAGG,TYPES)) = YES;

                  );


                  RAGG(RAGG) $ (( NOT (SUM(RSEU $ MAP_RR(RAGG,RSEU), 1.)>1.)) and (NOT SAMEAS(RAGG,"TOP"))
        $ifi %FARM_B%==on   and not (SUM(Types_to_r(RAGG,Types),1))
                  ) = NO;

    Departures from CAPRI: none."""
    ms, mr, n1, n2 = st.MS, st.MAP_RR, set(st.SRNUTS1), set(st.RU)
    lv = R_LEVL.upper()
    if lv == "TOP":
        return ("TOP",)
    if lv == "MS":
        ragg = [ms] if (any((ms, r) in mr for r in n1 if r != ms) or any((ms, r) in mr for r in n2 if r != ms)) else []
    elif lv == "NUTS1":
        ragg = [r for r in st.SRNUTS1 if (ms, r) in mr and r != ms and any((r, k) in mr for k in n2 if k != r)]
    else:
        ragg = []
    rseu = set(st.RSEU)
    return tuple(r for r in ragg if sum(1 for (a, k) in mr if a == r and k in rseu) > 1)


def RUNAGG_RUNR(st, R_LEVL: str, RAGG: str) -> tuple:
    r"""The aggregate (CAPRI's RUNAGG) and the units solved below it (RUNR): at "TOP" both the member state; below, the
    aggregate RAGG and its NUTS 1 units (the member state with NUTS 1 units) or its NUTS 2 units, RAGG itself left out.

    CAPRI's GAMS (feed/fedtrm_cal_pw.gms l. 148-153; again at l. 566-568 when a solution is collected):

                  IF ( SAMEAS(R_LEVL,"TOP"),
        *
        *             --- First step: adjust requirements for average of member state
        *
                     RUNAGG(MS)     = YES;
                     RUNR  (MS)     = YES;

    and below "TOP", CAPRI's GAMS (feed/fedtrm_cal_pw.gms l. 203-210; again at l. 570-577):

                     RUNAGG(RAGG)           = YES;
        *
                     if ( (SAMEAS(RAGG,MS) and (SUM( MAP_RR(MS,NUTS1) $ (NOT SAMEAS(MS,NUTS1)),1))),
                        RUNR(NUTS1) $ MAP_RR(MS,NUTS1) = YES;
                     else
                        RUNR(NUTS2)    $ (MAP_RR(RAGG,NUTS2)and (SUM( MAP_RR(MS,NUTS2),1)))   = YES;
        $ifi %FARM_B%==on   if ((CARD(Types) and SUM(NUTS2 $ SAMEAS(RAGG,NUTS2),1)), RUNR(Types) $ Types_to_r(RAGG,TYPES)    = YES);
                        RUNR(RAGG) = NO;

    Returns (RUNAGG, RUNR). Departures from CAPRI: none (no farm types)."""
    ms, mr = st.MS, st.MAP_RR
    if R_LEVL.upper() == "TOP":
        return (ms,), (ms,)
    if RAGG == ms and any((ms, r) in mr for r in st.SRNUTS1 if r != ms):
        runr = [r for r in st.SRNUTS1 if (ms, r) in mr]
    else:
        runr = [r for r in st.RU if (RAGG, r) in mr] if any((ms, r) in mr for r in st.RU) else []
        runr = [r for r in runr if r != RAGG]
    return (RAGG,), tuple(runr)


def p_aprDistAnimReq_TOP(st, RUNR) -> None:
    r"""The "TOP" level: the requirements' prior mean, the requirement functions' energy and protein raised by a mark-up
    growing with the member state's surplus of deliveries over requirements and with the animal's assumed
    inefficiency; the requirements' levels start at the functions'; their standard deviations; the feeds without a
    maximum share fixed at 0.

    CAPRI's GAMS (feed/fedtrm_cal_pw.gms l. 169-194):

                     p_aprDistAnimReq(RUNR,maact,A,REQMSE,"MEAN")   $ p_animReq(RUNR,maact,A,REQMSE) = p_animReq(RUNR,maact,A,REQMSE);

                     p_aprDistAnimReq(RUNR,maact,A,REQMSE,"MEAN")   $ (p_animReq(RUNR,maact,A,REQMSE) and (sameas(REQMSE,"ENNE") or sameas(REQMSE,"CRPR")))
                        = p_animReq(RUNR,maact,A,REQMSE)

                          * (1.06 + 0.35*(MAX(0.01,p_aprDistAnimReq(MS,"ALL","T",REQMSE,"Mean")-0.06)**4.)
                          *p_aprDistAnimReq("ALL",maact,"T","ALL","StdDev"));

        *
        *
        *            --- starting point for the requirements is "science" = result of requirement function (req_or_man_fnc.gms)

                     v_animReq.L(MS,maact,A,REQM) = p_animReq(MS,maact,A,REQM);
        *
        *            --- standard deviation: assumed general coefficient of variance for requirements
        *                                    times original requirements
        *                                    times "assumed inefficiency" of maact

                     p_aprDistAnimReq(RUNR,maact,A,REQMSE,"StdDev") $ p_animReq(RUNR,maact,A,REQMSE)
                         = p_aprDistAnimReq("ALL","ALL","T",REQMSE,"StdDev") * p_animReq(RUNR,maact,A,REQMSE)
                         * p_aprDistAnimReq("ALL",maact,"T","ALL","StdDev");
        *
        *            --- fix to zero if no maxshare is defined (e.g. FEED is not allowed for the animal type or not available in the region)
        *
                     v_feedInpCoeff.FX(RUNR,maact,A,FEED)  $  (NOT p_maxFeedShare(RUNR,maact,A,FEED)) = 0;
                     v_feedInpCoeff.L (RUNR,maact,A,FEED)  $  (NOT p_maxFeedShare(RUNR,maact,A,FEED)) = 0;

    Departures from CAPRI: none (the standard deviations are not read by hpdFeed_, which weighs the requirements by
    p_animReq, in CAPRI too)."""
    d, ms = st.p_aprDistAnimReq, st.MS
    for r in RUNR:
        for a in st.MAACT:
            for t in st.A:
                for q in st.REQMSE:
                    p = st.p_animReq.get((r, a, t, q), 0.0)
                    if p:
                        d[(r, a, t, q, "Mean")] = p
                    if p and q in ("ENNE", "CRPR"):
                        d[(r, a, t, q, "Mean")] = p * (
                            1.06 + 0.35 * (max(0.01, d.get((ms, "ALL", "T", q, "Mean"), 0.0) - 0.06) ** 4.)
                            * d.get(("ALL", a, "T", "ALL", "StdDev"), 0.0))
    for a in st.MAACT:
        for t in st.A:
            for q in st.REQM:
                st.v_animReq.L[(ms, a, t, q)] = st.p_animReq.get((ms, a, t, q), 0.0)
    for r in RUNR:
        for a in st.MAACT:
            for t in st.A:
                for q in st.REQMSE:
                    p = st.p_animReq.get((r, a, t, q), 0.0)
                    if p:
                        d[(r, a, t, q, "StdDev")] = (d.get(("ALL", "ALL", "T", q, "StdDev"), 0.0) * p
                                                     * d.get(("ALL", a, "T", "ALL", "StdDev"), 0.0))
                for f in st.FEED:
                    if not st.p_maxFeedShare.get((r, a, t, f), 0.0):
                        st.v_feedInpCoeff.fx((r, a, t, f), 0.0)


def p_aprDistAnimReq_regional(st, RAGG, RUNR) -> None:
    r"""Below "TOP": the units' prior mean of the requirements, the requirement functions' times the aggregate's
    calibrated over its uncorrected requirement; their standard deviations; the units' feed use started at the
    aggregate's where it has none; the aggregate's feed use fixed; the units' feeds the aggregate does not feed (its
    own fodder excepted) and the feeds without a maximum share fixed at 0; the feed aggregates fixed at 0 where none of
    their feeds may enter, otherwise at least 1e-6, starting at 1.

    CAPRI's GAMS (feed/fedtrm_cal_pw.gms l. 224-256):

                     p_aprDistAnimReq(RUNR,maact,A,REQMSE,"MEAN")  $ v_animReq.L(RAGG,maact,A,REQMSE) =

                          p_animReq(RUNR,maact,A,REQMSE)
                            *  p_animReq(RAGG,maact,A,REQMSE)/v_animReq.L(RAGG,maact,A,REQMSE);
        *
        *            --- standard deviation: expected mean times assumed coefficient of variance for requirements
        *                                    times assumed coefficient of variance for animal type
        *
                     p_aprDistAnimReq(RUNR,maact,A,REQMSE,"StdDev") $ p_animReq(RUNR,maact,A,REQMSE)
                         = p_aprDistAnimReq(RUNR,maact,A,REQMSE,"MEAN")
                            *p_aprDistAnimReq("ALL","ALL","T",REQMSE,"StdDev")*p_aprDistAnimReq("ALL",maact,"T","ALL","StdDev");
        *
        *            --- feed use per animal initialised from regional aggregate
        *
                     v_feedInpCoeff.L(RUNR,maact,A,FEED) $ ((SUM(FEED1, v_feedInpCoeff.L(RUNR,maact,A,FEED1)) EQ 0.) and p_technFact(RUNR,maact,"LEVL",A))
                       = v_feedInpCoeff.L(RAGG,maact,A,FEED);
        *
        *            --- fix feed use for regional aggregate
        *
                     v_feedInpCoeff.FX(RAGG,maact,A,FEED) = v_feedInpCoeff.L(RAGG,maact,A,FEED);
        *
        *            --- don t allow feed input coefficient in regions if not found in higher aggregate
        *                (erases FEDUSEA_ equation), exemption: own produced fodder
        *
                     v_feedInpCoeff.FX(RUNR,maact,A,FEED) $ ( (NOT FODDIS(FEED)) and (NOT v_feedInpCoeff.L(RAGG,maact,A,FEED))) = 0;
        *
        *            --- fix to zero if no maxshare (feed not allowed for animal type or not availabe in region)
        *
                     v_feedInpCoeff.FX(RUNR,maact,A,FEED) $ ( NOT p_maxFeedShare(RUNR,maact,A,FEED)) = 0;
                     v_feedInpCoeff.L (RUNR,maact,A,FEED) $ ( NOT p_maxFeedShare(RUNR,maact,A,FEED)) = 0;
                     v_feedInpCoeff.FX(RUNR,maact,A,FeedAggr)  $ (NOT SUM(Feed_FeedAggr(Feed,FeedAggr), v_feedInpCoeff.up(RUNR,MAACT,A,FEED))) = 0.;
                     v_feedInpCoeff.LO(RUNR,maact,A,FeedAggr)  $ (SUM(Feed_FeedAggr(Feed,FeedAggr), p_maxFeedShare(RUNR,maact,A,FEED))) = 1E-6;
                     v_feedInpCoeff.L(RUNR,maact,A,FeedAggr)  $ (SUM(Feed_FeedAggr(Feed,FeedAggr), p_maxFeedShare(RUNR,maact,A,FEED))) = 1;

    Departures from CAPRI: none (the standard deviations: p_aprDistAnimReq_TOP)."""
    d, fic = st.p_aprDistAnimReq, st.v_feedInpCoeff
    for r in RUNR:
        for a in st.MAACT:
            for t in st.A:
                for q in st.REQMSE:
                    va = st.v_animReq.l((RAGG, a, t, q))
                    if va:
                        d[(r, a, t, q, "Mean")] = st.p_animReq.get((r, a, t, q), 0.0) * st.p_animReq.get(
                            (RAGG, a, t, q), 0.0) / va
                for q in st.REQMSE:
                    if st.p_animReq.get((r, a, t, q), 0.0):
                        d[(r, a, t, q, "StdDev")] = (d.get((r, a, t, q, "Mean"), 0.0)
                                                     * d.get(("ALL", "ALL", "T", q, "StdDev"), 0.0)
                                                     * d.get(("ALL", a, "T", "ALL", "StdDev"), 0.0))
    for r in RUNR:
        for a in st.MAACT:
            for t in st.A:
                if st.p_technFact.get((r, a, "LEVL", t), 0.0) and sum(fic.l((r, a, t, f)) for f in st.FEED) == 0.:
                    for f in st.FEED:
                        fic.L[(r, a, t, f)] = fic.l((RAGG, a, t, f))
    for a in st.MAACT:
        for t in st.A:
            for f in st.FEED:
                fic.fx((RAGG, a, t, f), fic.l((RAGG, a, t, f)))
    foddis = set(st.FODDIS)
    for r in RUNR:
        for a in st.MAACT:
            for t in st.A:
                for f in st.FEED:
                    if f not in foddis and not fic.l((RAGG, a, t, f)):
                        fic.fx((r, a, t, f), 0.0)
                for f in st.FEED:
                    if not st.p_maxFeedShare.get((r, a, t, f), 0.0):
                        fic.fx((r, a, t, f), 0.0)
                        fic.L[(r, a, t, f)] = 0.0
                _feed_aggregates_bounds(st, r, a, t)


def _feed_aggregates_bounds(st, r, a, t) -> None:
    """CAPRI's three statements on the feed aggregates' coefficients (l. 254-256, in p_aprDistAnimReq_regional's
    quote): fixed at 0 where none of the aggregate's feeds has an upper bound above 0, and where one of its feeds has
    a maximum share at least 1e-6, starting at 1."""
    fic = st.v_feedInpCoeff
    for g in st.FeedAggr:
        feeds = [f for (f, g2) in st.Feed_FeedAggr if g2 == g]
        if not sum(fic.up((r, a, t, f)) for f in feeds):
            fic.fx((r, a, t, g), 0.0)
        if sum(st.p_maxFeedShare.get((r, a, t, f), 0.0) for f in feeds):
            fic.LO[(r, a, t, g)] = 1E-6
            fic.L[(r, a, t, g)] = 1.0


def v_actLevl_fix(st, RUNR) -> None:
    r"""The herds fixed at the data's; the requirements and the feed shares of animals without a herd deleted.

    CAPRI's GAMS (feed/fedtrm_cal_pw.gms l. 260-269):

                 v_actLevl.FX(RUNR,maact,A)   = DATA(RUNR,maact,"LEVL","Y") * p_technFact(RUNR,maact,"LEVL",A);
        *
        *        --- rest of statements is valid for all regional levels
        *
        *
        *        --- delete requirements, minimum and maximum shares if no activity level
        *
                 p_animReq(RUNR,maact,A,REQM)       $ (NOT v_actLevl.L(RUNR,maact,A))      = 0;
                 p_maxFeedShare(RUNR,maact,A,FEED)  $ (NOT v_actLevl.L(RUNR,maact,A))      = 0;
                 p_minFeedShare(RUNR,maact,A,FEED)  $ (NOT v_actLevl.L(RUNR,maact,A))      = 0;

    Departures from CAPRI: none (v_actLevl is fixed: its level is the model's constant)."""
    for r in RUNR:
        for a in st.MAACT:
            for t in st.A:
                v = st.DATA.get((r, a, "LEVL"), 0.0) * st.p_technFact.get((r, a, "LEVL", t), 0.0)
                if v:
                    st.v_actLevl_L[(r, a, t)] = v
                else:
                    st.v_actLevl_L.pop((r, a, t), None)
                if not v:
                    for q in st.REQM:
                        st.p_animReq.pop((r, a, t, q), None)
                    for f in st.FEED:
                        st.p_maxFeedShare.pop((r, a, t, f), None)
                        st.p_minFeedShare.pop((r, a, t, f), None)


def v_animReq_start_bounds(st, RUNR) -> None:
    r"""The requirements' levels start at the requirement functions', the energy and protein at their prior mean;
    their bounds 50% to 150% of the prior mean (reversed for a negative requirement).

    CAPRI's GAMS (feed/fedtrm_cal_pw.gms l. 275-285):

                v_animReq.L(RUNR,maact,A,REQM)     = p_animReq(RUNR,maact,A,REQM);
        *                ... except for ENNE+CRPR that have been scaled above to reflect the sectoral imbalance
                v_animReq.L(RUNR,maact,A,REQMSE) = p_aprDistAnimReq(RUNR,maact,A,REQMSE,"Mean");
        *
        *       --- general upper and lower bounds at +50%/50% precent around expected mean
        *
                v_animReq.LO(RUNR,maact,A,REQMSE) =  0.5 * p_aprDistAnimReq(RUNR,maact,A,REQMSE,"MEAN") $ p_animReq(RUNR,maact,A,REQMSE);
                v_animReq.UP(RUNR,maact,A,REQMSE) =  1.5 * p_aprDistAnimReq(RUNR,maact,A,REQMSE,"MEAN") $ p_animReq(RUNR,maact,A,REQMSE);
        *
                v_animReq.UP(RUNR,maact,A,REQMSE) $ (p_animReq(RUNR,maact,A,REQMSE) LT 0) = 0.5 * p_aprDistAnimReq(RUNR,maact,A,REQMSE,"MEAN");
                v_animReq.lo(RUNR,maact,A,REQMSE) $ (p_animReq(RUNR,maact,A,REQMSE) LT 0) = 1.5 * p_aprDistAnimReq(RUNR,maact,A,REQMSE,"MEAN");

    Departures from CAPRI: none."""
    d, va = st.p_aprDistAnimReq, st.v_animReq
    for r in RUNR:
        for a in st.MAACT:
            for t in st.A:
                for q in st.REQM:
                    va.L[(r, a, t, q)] = st.p_animReq.get((r, a, t, q), 0.0)
                for q in st.REQMSE:
                    mean, p = d.get((r, a, t, q, "Mean"), 0.0), st.p_animReq.get((r, a, t, q), 0.0)
                    va.L[(r, a, t, q)] = mean
                    va.LO[(r, a, t, q)] = 0.5 * mean if p else 0.0
                    va.UP[(r, a, t, q)] = 1.5 * mean if p else 0.0
                    if p < 0:
                        va.UP[(r, a, t, q)] = 0.5 * mean
                        va.LO[(r, a, t, q)] = 1.5 * mean


def p_feedQuant_units(st, RUNR) -> None:
    r"""The units' fodder available: the priors' feed balance (re-aggregated there), the fodder's maximum shares 0
    where none is available, the straw the crops' straw output; the fodder no animal may eat at GAMS's EPS (numerically
    0 here: nothing later reads it as nonzero, FEDUSES_ needs more than 1e-6).

    CAPRI's GAMS (feed/fedtrm_cal_pw.gms l. 311-327):

                 p_feedQuant(RUNR,FODDI)   $ (not sameas("FSTR",FODDI))
        *           Note: the following has been reaggregated across regions in fedtrm_prior
                    = p_feedBalance(RUNR,FODDI,"allAni","FEDM","FedmSup");

                 p_maxFeedShare(RUNR,AACT,A,FODDI) $ ((NOT p_feedQuant(RUNR,FODDI)) and (not sameas("FSTR",FODDI)))  = 0;

        *
        *        --- during the feed calibration, available straw = GROF.STRA = p_feedQuant.
        *            The endogneous v_lossQuant in FEDUSE_ permits losses of straw
        *
                 p_feedQuant(RUNR,"FSTR")
                   = SUM( PACT_TO_O(MPACT,"STRA"), DATA(RUNR,MPACT,"LEVL","Y")*DATA(RUNR,MPACT,"STRA","Y")*0.001);

        *       --- attention: the eps is introduced to ensure that the feeding coefficients become zero
        *                      when no fodder is produced!
        *
                 p_feedQuant(RUNR,FODDI) $ (not sum( (maact,a), p_maxFeedShare(RUNR,MAACT,A,FODDI))) = eps;

    Departures from CAPRI: none."""
    straw_acts = [p for (p, o) in st.PACT_TO_O if o == "STRA" and p in set(st.MPACT)]
    for r in RUNR:
        for fo in st.FODDI:
            if fo != "FSTR":
                v = st.p_feedBalance.get((r, fo, "allAni", "FEDM", "FedmSup"), 0.0)
                if v:
                    st.p_feedQuant[(r, fo)] = v
                else:
                    st.p_feedQuant.pop((r, fo), None)
        for fo in st.FODDI:
            if fo != "FSTR" and not st.p_feedQuant.get((r, fo), 0.0):
                for k in [k for k in st.p_maxFeedShare if k[0] == r and k[1] in st.AACT and k[3] == fo]:
                    del st.p_maxFeedShare[k]
        st.p_feedQuant[(r, "FSTR")] = sum(st.DATA.get((r, p, "LEVL"), 0.0) * st.DATA.get((r, p, "STRA"), 0.0) * 0.001
                                          for p in straw_acts)
        for fo in st.FODDI:
            if not any(st.p_maxFeedShare.get((r, a, t, fo), 0.0) for a in st.MAACT for t in st.A):
                st.p_feedQuant[(r, fo)] = 0.0


def v_lossQuant_bounds(st, RAGG, RUNR) -> None:
    r"""The straw's losses: at least 90% of its production at "TOP", 80% below (so at most 10% or 20% may be fed), at
    most all of it; the member state's at the data's (production less feed use); none where no crop yields straw; no
    losses of COMF.

    CAPRI's GAMS (feed/fedtrm_cal_pw.gms l. 329-354):

                 v_lossQuant.FX(RUNR,"STRA") = 0;
                 v_lossQuant.FX(RUNR,"COMF") = 0;
        *
        *                                     at most 10% on the MS level and 20% on regional level may be fed to animals
                 v_lossQuant.LO(RUNR,"STRA") =  DATA(RUNR,"GROF","STRA","Y") * ( 0.90 $ (    SAMEAS(RAGG,"TOP"))
                                                                               + 0.80 $ (NOT SAMEAS(RAGG,"TOP")));
                 v_lossQuant.UP(RUNR,"STRA") =  DATA(RUNR,"GROF","STRA","Y");

                 v_lossQuant.FX(MS,"STRA") $ (not capreg) = DATA(MS,"GROF","STRA","Y") - DATA(MS,"FEDM","STRA","Y");


        *        --- feeding use for straw equals production on farm

                 if(SUM((RUNR,TYPES)$SAMEAS(RUNR,TYPES),1),

                      DATA(RUNR,"GROF","STRA","Y")$(DATA(RUNR,"GROF","STRA","Y") le 1E-6) = 0;
                      p_feedQuant(RUNR,"FSTR") $(DATA(RUNR,"GROF","STRA","Y")    le 1E-6) = 0;

                      p_maxFeedShare(RUNR,AACT,A,"FSTR") $ ((DATA(RUNR,"GROF","STRA","Y") le 1E-6) $ p_technFact(RUNR,AACT,"LEVL",A) ) = 0.0;

                      v_lossQuant.UP(RUNR,"STRA") $ CAPREG   =  DATA(RUNR,"GROF","STRA","Y");
                      v_lossQuant.LO(RUNR,"STRA") $ CAPREG   =  0;
                     );

                 v_lossQuant.FX(RUNR,"STRA") $ (not sum( (CACT,A), DATA(RUNR,CACT,"LEVL","Y") * p_technFact(RUNR,CACT,"LEVL",A)
                                                                                          * DATA(RUNR,CACT,"STRA","Y"))) = 0;

    Departures from CAPRI: none (no farm types: the statements of l. 342-351 do not apply; CAPRI's baseline is not
    capreg)."""
    lq, cact = st.v_lossQuant, set(st.CACT)
    for r in RUNR:
        lq.fx((r, "STRA"), 0.0)
        lq.fx((r, "COMF"), 0.0)
        g = st.DATA.get((r, "GROF", "STRA"), 0.0)
        lq.LO[(r, "STRA")] = g * (0.90 if RAGG == "TOP" else 0.80)
        lq.UP[(r, "STRA")] = g
    ms = st.MS
    lq.fx((ms, "STRA"), st.DATA.get((ms, "GROF", "STRA"), 0.0) - st.DATA.get((ms, "FEDM", "STRA"), 0.0))
    for r in RUNR:
        if not sum(st.DATA.get((r, c, "LEVL"), 0.0) * st.p_technFact.get((r, c, "LEVL", t), 0.0)
                   * st.DATA.get((r, c, "STRA"), 0.0) for c in cact for t in st.A):
            lq.fx((r, "STRA"), 0.0)


def v_lossQuant_start(st, RUNR) -> None:
    r"""The straw's losses start at 95% of its production.

    CAPRI's GAMS (feed/fedtrm_cal_pw.gms l. 386):

                 v_lossQuant.L(RUNR,"STRA") = 0.95 * DATA(RUNR,"GROF","STRA","Y");

    Departures from CAPRI: none."""
    for r in RUNR:
        st.v_lossQuant.L[(r, "STRA")] = 0.95 * st.DATA.get((r, "GROF", "STRA"), 0.0)


def start_values(st, RUNR) -> None:
    r"""The start: the requirements at the requirement functions', the feed input coefficients at their prior mean
    (CAPRI's uniform(1, 1) draws are 1: randomStartVal is off); no restart point (CAPRI's mefed file of an earlier
    baseline is not in the material, p_fedtrmHasIniPoint 0, l. 36-37).

    CAPRI's GAMS (feed/fedtrm_cal_pw.gms l. 398-420):

                 p_second =Gsecond(jnow);
        *         display p_second;
                 p_count = 0;
                 loop(lines $ (p_count lt p_second),
        *            only REQSE_ is part of model (former REQSN_ is discarded)         default is: uniLow=uniUpp=1
                 v_animReq.L(RUNR,maact,A,REQMSE)  = p_animReq(RUNR,maact,A,REQMSE)  * uniform(%UniLow%,%UniUpp%);
                 v_feedInpCoeff.L(RUNR,maact,A,FEED) = p_feedInpCoeff(RUNR,maact,A,Feed,"Mean")  * uniform(%UniLow%,%UniUpp%);
        *            Increasing by (eg) 10 implies that we pick one of 60/10=6 possible sets of random numbers
        *            (=> repeated runs use different sets of random numbers depending on system second)
        *            Increasing by 60 implies that we pick one of 60/60=1 possible sets of random numbers
        *            (=> repeated runs use different always the same set of random numbers)
                 p_count = p_count +60;
                 );

        *        Use start values from previous solve if available

                 v_animReq.L(RUNR,maact,A,REQMSE)    $ p_fedtrmHasIniPoint(MS) = p_animReqCopy(RUNR,maact,A,REQMSE);
                 v_animReq.L(RAGG,"ALL","T",REQMSE)  $ p_fedtrmHasIniPoint(MS) = p_animReqCopy(RAGG,"ALL","T",REQMSE);
        *       ... and if old start value was > 0 because that might be a very bad starting point:
                 v_feedInpCoeff.L(RUNR,maact,A,FEED) $ (p_fedtrmHasIniPoint(MS) $ p_feedInpCoeffLoad(RUNR,maact,A,FEED))
                                                     = p_feedInpCoeffLoad(RUNR,maact,A,FEED) $ p_maxFeedShare(RUNR,maact,A,FEED);
                 v_feedCost.L(RUNR,maact,A)          $ p_fedtrmHasIniPoint(MS) = p_feedCostLoad(RUNR,maact,A);
                 v_lossQuant.L(RUNR,"STRA")          $ p_fedtrmHasIniPoint(MS) = p_lossQuantLoad(RUNR,"STRA");

    Departures from CAPRI: the loop over lines runs once; in CAPRI it runs once unless the system clock's second is 0
    (p_second = 0: then not at all, and the start stays at the earlier statements')."""
    for r in RUNR:
        for a in st.MAACT:
            for t in st.A:
                for q in st.REQMSE:
                    st.v_animReq.L[(r, a, t, q)] = st.p_animReq.get((r, a, t, q), 0.0) * 1.0
                for f in st.FEED:
                    st.v_feedInpCoeff.L[(r, a, t, f)] = st.p_feedInpCoeff.get((r, a, t, f, "Mean"), 0.0) * 1.0


def v_feedInpCoeff_aggregates_start(st, RUNR) -> None:
    r"""The feed aggregates start at the sum of their feeds; the feeds without a maximum share fixed at 0; the
    aggregates' bounds (_feed_aggregates_bounds).

    CAPRI's GAMS (feed/fedtrm_cal_pw.gms l. 422-435):

                 v_feedInpCoeff.L(RUNR,maact,A,FEEDAggr) = sum(FEED_FEEDAggr(FEED,FEEDAggr), v_feedInpCoeff.L(RUNR,maact,A,FEED));
        *
        *
                 v_animReq.l(RUNAGG,"ALL","T",REQMSE)
                  $  (SUM( (RUNR,maact,A) $ p_aprDistAnimReq(RUNR,maact,A,REQMSE,"Mean"), v_actLevl.L(RUNR,maact,A) * p_aprDistAnimReq(RUNR,maact,A,REQMSE,"MEAN")))
                  =   SUM( (RUNR,maact,A) $ p_aprDistAnimReq(RUNR,maact,A,REQMSE,"Mean"), v_actLevl.L(RUNR,maact,A) * v_animReq.L(RUNR,maact,A,REQMSE))
                    / SUM( (RUNR,maact,A) $ p_aprDistAnimReq(RUNR,maact,A,REQMSE,"Mean"), v_actLevl.L(RUNR,maact,A) * p_aprDistAnimReq(RUNR,maact,A,REQMSE,"MEAN"));
        *
        *
                 v_feedInpCoeff.FX(RUNR,maact,A,FEED)  $ (NOT p_maxFeedShare(RUNR,maact,A,FEED)) = 0.;
                 v_feedInpCoeff.L(RUNR,maact,A,FEED)   $ (NOT p_maxFeedShare(RUNR,maact,A,FEED)) = 0.;
                 v_feedInpCoeff.FX(RALL,maact,A,FeedAggr)  $ (NOT SUM(Feed_FeedAggr(Feed,FeedAggr), v_feedInpCoeff.up(RALL,MAACT,A,FEED))) = 0.;
                 v_feedInpCoeff.LO(RUNR,maact,A,FeedAggr)  $ (SUM(Feed_FeedAggr(Feed,FeedAggr), p_maxFeedShare(RUNR,maact,A,FEED))) = 1E-6;
                 v_feedInpCoeff.L(RUNR,maact,A,FeedAggr)  $ (SUM(Feed_FeedAggr(Feed,FeedAggr), p_maxFeedShare(RUNR,maact,A,FEED))) = 1;

    Departures from CAPRI: the level of v_animReq(RUNAGG, "ALL", "T", REQMSE) (l. 425-428) is not set: it is MEANDEV_'s
    variable, a row not in m_hpdFeed, and only CAPRI's restart copy reads it."""
    fic = st.v_feedInpCoeff
    for r in RUNR:
        for a in st.MAACT:
            for t in st.A:
                for g in st.FeedAggr:
                    fic.L[(r, a, t, g)] = sum(fic.l((r, a, t, f)) for (f, g2) in st.Feed_FeedAggr if g2 == g)
    for r in RUNR:
        for a in st.MAACT:
            for t in st.A:
                for f in st.FEED:
                    if not st.p_maxFeedShare.get((r, a, t, f), 0.0):
                        fic.fx((r, a, t, f), 0.0)
    for r in st.rall_in_ms():
        for a in st.MAACT:
            for t in st.A:
                _feed_aggregates_bounds_rall(st, r, a, t, r in set(RUNR))


def _feed_aggregates_bounds_rall(st, r, a, t, in_runr: bool) -> None:
    """_feed_aggregates_bounds as the driver repeats it at l. 433-435, 503-505 and 671-673 (in the quotes of the
    functions calling it): the first statement over RALL (here the member state's regions), the other two over
    RUNR."""
    fic = st.v_feedInpCoeff
    for g in st.FeedAggr:
        feeds = [f for (f, g2) in st.Feed_FeedAggr if g2 == g]
        if not sum(fic.up((r, a, t, f)) for f in feeds):
            fic.fx((r, a, t, g), 0.0)
        if in_runr and sum(st.p_maxFeedShare.get((r, a, t, f), 0.0) for f in feeds):
            fic.LO[(r, a, t, g)] = 1E-6
            fic.L[(r, a, t, g)] = 1.0


def v_feedQuantReg_bounds(st, RUNR) -> None:
    r"""The fodder's use starts at the coefficients' and is held within 0.1% of the available (straw free; FEDUSES_
    fixes what is given); the fodder's minimum shares dropped where hardly any is available; the feeds' use starts at
    the coefficients' (straw with its losses).

    CAPRI's GAMS (feed/fedtrm_cal_pw.gms l. 439-452):

                 v_feedQuantReg.L(RUNR,FODDI)
                     = SUM( (maact,A) $ p_maxFeedShare(RUNR,maact,A,FODDI), v_feedInpCoeff.L(RUNR,maact,A,FODDI)*v_actLevl.L(RUNR,maact,A)) / 1000.;

                 v_feedQuantReg.LO(RUNR,FODDI) $ (NOT SAMEAS(FODDI,"FSTR")) = p_feedQuant(RUNR,FODDI) * 0.999;
                 v_feedQuantReg.UP(RUNR,FODDI) $ (NOT SAMEAS(FODDI,"FSTR")) = MAX(p_feedQuant(RUNR,FODDI) * 1.001,p_feedQuant(RUNR,FODDI) + 1.E-6);
        *        MaK probably outdated - p_minfeedshare is not used any more in allocation under this specification
                 p_minFeedShare(RUNR,MAACT,A,FODDI) $ (p_feedQuant(RUNR,FODDI) le 1.E-3) = 0;

        *
                 OPTION p_aprDistAnimReq:3:4:1;
        *
                 v_feedQuantReg.L(RUNR,FEED)
                   = SUM( (maact,A) $ p_maxFeedShare(RUNR,maact,A,FEED),
                        v_feedInpCoeff.L(RUNR,maact,A,FEED)*v_actLevl.L(RUNR,maact,A)) / 1000. + v_lossQuant.L(RUNR,"STRA") $ SAMEAS(FEED,"FSTR");

    Departures from CAPRI: none."""
    fq, fic = st.v_feedQuantReg, st.v_feedInpCoeff

    def use(r, f):
        return sum(fic.l((r, a, t, f)) * st.v_actLevl_L.get((r, a, t), 0.0) for a in st.MAACT for t in st.A
                   if st.p_maxFeedShare.get((r, a, t, f), 0.0)) / 1000.
    for r in RUNR:
        for fo in st.FODDI:
            fq.L[(r, fo)] = use(r, fo)
            if fo != "FSTR":
                q = st.p_feedQuant.get((r, fo), 0.0)
                fq.LO[(r, fo)] = q * 0.999
                fq.UP[(r, fo)] = max(q * 1.001, q + 1.E-6)
        for fo in st.FODDI:
            if st.p_feedQuant.get((r, fo), 0.0) <= 1.E-3:
                for a in st.MAACT:
                    for t in st.A:
                        st.p_minFeedShare.pop((r, a, t, fo), None)
        for f in st.FEED:
            fq.L[(r, f)] = use(r, f) + (st.v_lossQuant.l((r, "STRA")) if f == "FSTR" else 0.0)


def v_feedInpCoeff_soft_bounds(st, R_LEVL, RAGG, RUNAGG, RUNR) -> None:
    r"""The feed input coefficients' bounds, turned into soft bounds: a lower bound of 10% of the prior mean (below the
    top, at most 75% of the aggregate's), an upper one of four times the prior mean (at least 35 t, 45 t for hens); an
    animal fed in one unit only takes the aggregate's coefficient (within 1%); the feeds without a maximum share fixed
    at 0; the limits kept as the objective's UppLim and LowLim, the upper bound then lifted and the lower one kept at
    10% of it at "TOP", 0.1% at "MS" and 0 below (straw: 0); the start kept ("ini") for later solves.

    CAPRI's GAMS (feed/fedtrm_cal_pw.gms l. 482-525):

                 v_feedInpCoeff.LO(RUNR,maact,A,FEED)
                                                      = MIN(0.1 * p_feedInpCoeff(RUNR,maact,A,FEED,"MEAN"),
                                                            0.75 * SUM(RUNAGG, v_feedInpCoeff.LO(RUNAGG,maact,A,FEED)))
                                                      $      SUM(RUNAGG $ (v_feedInpCoeff.LO(RUNAGG,maact,A,FEED) gt 0),1)
                                                      +  (0.1 * p_feedInpCoeff(RUNR,maact,A,FEED,"MEAN"))
                                                      $ (NOT SUM(RUNAGG $ (v_feedInpCoeff.LO(RUNAGG,maact,A,FEED) gt 0),1));

                 v_feedInpCoeff.UP(RUNR,maact,A,FEED) = MAX(4 * p_feedInpCoeff(RUNR,maact,A,FEED,"MEAN"), 35000 + 10000 $ sameas(maact,"HENS"));

        *             In case that some mAACT is only produced in one RUNR of the current RAGG (has been solved previously)
        *             the lower level feed input coeffs in RUNR have to be identical to those in the RAGG region due to FEDUSEA_

                 v_feedInpCoeff.LO(RUNR,maact,A,FEED) $ ((sum(runr1 $ p_maxFeedShare(RUNR1,maact,A,FEED),1) eq 1) $ (card(runr) gt 1))
                                                      = 0.99 * v_feedInpCoeff.L(RAGG,maact,A,FEED) ;
                 v_feedInpCoeff.UP(RUNR,maact,A,FEED) $ ((sum(runr1 $ p_maxFeedShare(RUNR1,maact,A,FEED),1) eq 1) $ (card(runr) gt 1))
                                                      = 1.01 * v_feedInpCoeff.L(RAGG,maact,A,FEED) ;
                 v_feedInpCoeff.l(RUNR,maact,A,FEED) $ ((sum(runr1 $ p_maxFeedShare(RUNR1,maact,A,FEED),1) eq 1) $ (card(runr) gt 1))
                                                      = v_feedInpCoeff.L(RAGG,maact,A,FEED) ;

                 v_feedInpCoeff.FX(RALL,maact,A,FEED)  $ (NOT p_maxFeedShare(RALL,maact,A,FEED)) = 0.;
                 v_feedInpCoeff.L(RALL,maact,A,FEED)   $ (NOT p_maxFeedShare(RALL,maact,A,FEED)) = 0.;
                 v_feedInpCoeff.FX(RALL,maact,A,FeedAggr)  $ (NOT SUM(Feed_FeedAggr(Feed,FeedAggr), v_feedInpCoeff.up(RALL,MAACT,A,FEED))) = 0.;
                 v_feedInpCoeff.LO(RUNR,maact,A,FeedAggr)  $ (SUM(Feed_FeedAggr(Feed,FeedAggr), p_maxFeedShare(RUNR,maact,A,FEED))) = 1E-6;
                 v_feedInpCoeff.L(RUNR,maact,A,FeedAggr)  $ (SUM(Feed_FeedAggr(Feed,FeedAggr), p_maxFeedShare(RUNR,maact,A,FEED))) = 1;

                 p_feedInpCoeff(RUNR,MAACT,A,FEED,"uppLim") $ (  v_feedInpCoeff.range(RUNR,maact,A,FEED)
                                                               $ (v_feedInpCoeff.UP(RUNR,maact,A,FEED) lt inf)
                                                               $ (v_feedInpCoeff.UP(RUNR,maact,A,FEED) gt 0))
                     = v_feedInpCoeff.UP(RUNR,maact,A,FEED);

                 p_feedInpCoeff(RUNR,MAACT,A,FEED,"lowLim") $ (  v_feedInpCoeff.range(RUNR,maact,A,FEED)
                                                               $ (v_feedInpCoeff.lo(RUNR,maact,A,FEED) gt 0))
                     = v_feedInpCoeff.lo(RUNR,maact,A,FEED);

                 v_feedInpCoeff.UP(RUNR,maact,A,FEED) $ p_feedInpCoeff(RUNR,MAACT,A,FEED,"uppLim") = inf;
        *             Lower bounds close to zero are maintained as this turned out to help the solver
                 v_feedInpCoeff.lo(RUNR,maact,A,FEED) $ p_feedInpCoeff(RUNR,MAACT,A,FEED,"lowLim")
                     = p_feedInpCoeff(RUNR,MAACT,A,FEED,"lowLim")
                     * ( 1.E-1 $ ( (not sameas(feed,"fstr")) $ SAMEAS(R_LEVL,"TOP"))
                       + 1.E-3 $ ( (not sameas(feed,"fstr")) $ SAMEAS(R_LEVL,"MS")));
        *         v_feedInpCoeff.lo(RUNR,maact,A,FEED) $ p_feedInpCoeff(RUNR,MAACT,A,FEED,"lowLim") = 0;

        *             Initial values are stored for checking and for additioanl soluiton attempts in case of infeasibilities
                 p_feedInpCoeff(RUNR,MAACT,A,FEED,"ini") $ v_feedInpCoeff.l(RUNR,maact,A,FEED) = v_feedInpCoeff.l(RUNR,maact,A,FEED);

    Departures from CAPRI: none."""
    fic, pfc = st.v_feedInpCoeff, st.p_feedInpCoeff
    for r in RUNR:
        for a in st.MAACT:
            for t in st.A:
                for f in st.FEED:
                    k, mean = (r, a, t, f), pfc.get((r, a, t, f, "Mean"), 0.0)
                    pos = [ra for ra in RUNAGG if fic.lo((ra, a, t, f)) > 0]
                    fic.LO[k] = (min(0.1 * mean, 0.75 * sum(fic.lo((ra, a, t, f)) for ra in RUNAGG)) if pos
                                 else 0.1 * mean)
                    fic.UP[k] = max(4 * mean, 35000 + (10000 if a == "HENS" else 0))
    if len(RUNR) > 1:
        for a in st.MAACT:
            for t in st.A:
                for f in st.FEED:
                    if sum(1 for r1 in RUNR if st.p_maxFeedShare.get((r1, a, t, f), 0.0)) == 1:
                        lv = fic.l((RAGG, a, t, f))
                        for r in RUNR:
                            fic.LO[(r, a, t, f)] = 0.99 * lv
                            fic.UP[(r, a, t, f)] = 1.01 * lv
                            fic.L[(r, a, t, f)] = lv
    for r in st.rall_in_ms():
        for a in st.MAACT:
            for t in st.A:
                for f in st.FEED:
                    if not st.p_maxFeedShare.get((r, a, t, f), 0.0):
                        fic.fx((r, a, t, f), 0.0)
                        fic.L[(r, a, t, f)] = 0.0
                _feed_aggregates_bounds_rall(st, r, a, t, r in set(RUNR))
    lv = R_LEVL.upper()
    for r in RUNR:
        for a in st.MAACT:
            for t in st.A:
                for f in st.FEED:
                    k = (r, a, t, f)
                    lo, up = fic.lo(k), fic.up(k)
                    if up - lo and up < INF and up > 0:
                        pfc[(r, a, t, f, "UppLim")] = up
                    if up - lo and lo > 0:
                        pfc[(r, a, t, f, "LowLim")] = lo
                    if pfc.get((r, a, t, f, "UppLim"), 0.0):
                        fic.UP[k] = INF
                    if pfc.get((r, a, t, f, "LowLim"), 0.0):
                        fic.LO[k] = pfc[(r, a, t, f, "LowLim")] * (
                            (1.E-1 if (f != "FSTR" and lv == "TOP") else 0.0)
                            + (1.E-3 if (f != "FSTR" and lv == "MS") else 0.0))
                    if fic.l(k):
                        pfc[(r, a, t, f, "ini")] = fic.l(k)


def FeedTotalSubRegionAvg_start(st, RUNAGG, RUNR) -> None:
    r"""The start of the units' average dry matter intake v_feedInpCoeff(RUNAGG, a, A, "FeedTotalSubRegionAvg") at 1,
    as CAPRI starts the feed aggregates (l. 435, 505, 673), for the animals with an energy requirement in a unit (the
    domain of hpdFeed_'s second term).

    CAPRI's GAMS: none (a departure). The variable enters only hpdFeed_'s second term (its defining row MeanFeedTotal_,
    feed/fedtrm_mod_pw.gms l. 120-126, is not in m_hpdFeed) and the _pw driver never sets its level, so CAPRI starts it
    at 0.

    Departures from CAPRI: the start at 1. The term divides by the variable itself, (FT - avg) / (avg + 0.001), so from
    0 its gradient is huge and IPOPT's gradient-based scaling of the objective, set at the start, then lets the solve
    stop early on a flat objective: on DK000000 at a point 3e-7 worse in the objective than CAPRI's, with coefficients
    up to 0.4% apart; from 1 at CAPRI's point (the objective equal to 1e-12, the coefficients' median deviation 2e-10;
    scratchpad s3b/probe_obj3.py, 24 November 2026). The start changes no optimum."""
    for ra in RUNAGG:
        for a in st.MAACT:
            for t in st.A:
                if any(st.p_animReq.get((r, a, t, "ENNE"), 0.0) for r in RUNR):
                    st.v_feedInpCoeff.L[(ra, a, t, "FeedTotalSubRegionAvg")] = 1.0


def setup_RAGG(st, R_LEVL, RAGG):
    """CAPRI's statements before the first solve of an aggregate (feed/fedtrm_cal_pw.gms l. 142-525), in CAPRI's order
    (the feed cost's prior and bounds, l. 360-381, left out with CST_: capri_mod/feed/equations/fedtrm_mod_pw.py), and
    the start of the units' average intake (FeedTotalSubRegionAvg_start, a departure). Returns (RUNAGG, RUNR)."""
    RUNAGG, RUNR = RUNAGG_RUNR(st, R_LEVL, RAGG)
    if R_LEVL.upper() == "TOP":
        p_aprDistAnimReq_TOP(st, RUNR)
    else:
        p_aprDistAnimReq_regional(st, RAGG, RUNR)
    v_actLevl_fix(st, RUNR)
    v_animReq_start_bounds(st, RUNR)
    p_feedQuant_units(st, RUNR)
    v_lossQuant_bounds(st, RAGG, RUNR)
    v_lossQuant_start(st, RUNR)
    start_values(st, RUNR)
    v_feedInpCoeff_aggregates_start(st, RUNR)
    v_feedQuantReg_bounds(st, RUNR)
    v_feedInpCoeff_soft_bounds(st, R_LEVL, RAGG, RUNAGG, RUNR)
    FeedTotalSubRegionAvg_start(st, RUNAGG, RUNR)
    return RUNAGG, RUNR


def relax_infeasible(st, RAGG, RUNR) -> None:
    r"""After an infeasible solve (p_BoundOpening is 0: no opening by marginals): the start restored; after 5 solves
    the lower soft bounds' remaining floor cut tenfold, after 10 removed; the feeds without a maximum share fixed at 0
    and the aggregates' bounds again; after 15 solves the requirements within 30% to 170% of their prior mean.

    CAPRI's GAMS (feed/fedtrm_cal_pw.gms l. 656-680):

        *
        *            --- restore initial values for several solution attempts
        *
                     v_feedInpCoeff.l(RUNR,maact,A,FEED) = p_feedInpCoeff(RUNR,MAACT,A,FEED,"ini");

        *                Should not contrain feasibility (or confuse the solver):
                     v_feedCost.LO(RUNR,maact,A) = 0;

        *                After x trials we further relax the lower bounds here, but independent from marginals and for all coefficients
                     v_feedInpCoeff.lo(RUNR,maact,A,FEED)  $ (p_feedInpCoeff(RUNR,MAACT,A,FEED,"lowLim") $ (p_nSolved(RAGG) gt 5))
                       = v_feedInpCoeff.lo(RUNR,maact,A,FEED)  / 10;
                     v_feedInpCoeff.lo(RUNR,maact,A,FEED)  $ (p_feedInpCoeff(RUNR,MAACT,A,FEED,"lowLim") $ (p_nSolved(RAGG) gt 10))
                       = 0;
                     v_feedInpCoeff.FX(RALL,maact,A,FEED)  $ (NOT p_maxFeedShare(RALL,maact,A,FEED)) = 0.;
                     v_feedInpCoeff.L(RALL,maact,A,FEED)   $ (NOT p_maxFeedShare(RALL,maact,A,FEED)) = 0.;
                     v_feedInpCoeff.FX(RALL,maact,A,FeedAggr)  $ (NOT SUM(Feed_FeedAggr(Feed,FeedAggr), v_feedInpCoeff.up(RALL,MAACT,A,FEED))) = 0.;
                     v_feedInpCoeff.LO(RUNR,maact,A,FeedAggr)  $ (SUM(Feed_FeedAggr(Feed,FeedAggr), p_maxFeedShare(RUNR,maact,A,FEED))) = 1E-6;
                     v_feedInpCoeff.L(RUNR,maact,A,FeedAggr)  $ (SUM(Feed_FeedAggr(Feed,FeedAggr), p_maxFeedShare(RUNR,maact,A,FEED))) = 1;
        *
        *                After y trials also relax the bounds on requirements, again independent from marginals and for all animals
                     v_animReq.LO(RUNR,maact,A,REQMSE) $ (p_nSolved(RAGG) gt 15)  =  0.3 * p_aprDistAnimReq(RUNR,maact,A,REQMSE,"MEAN") $ p_animReq(RUNR,maact,A,REQMSE);
                     v_animReq.UP(RUNR,maact,A,REQMSE) $ (p_nSolved(RAGG) gt 15)  =  1.7 * p_aprDistAnimReq(RUNR,maact,A,REQMSE,"MEAN") $ p_animReq(RUNR,maact,A,REQMSE);
        *
                     v_animReq.UP(RUNR,maact,A,REQMSE) $ ((p_animReq(RUNR,maact,A,REQMSE) LT 0) $ (p_nSolved(RAGG) gt 15) )= 0.3 * p_aprDistAnimReq(RUNR,maact,A,REQMSE,"MEAN");
                     v_animReq.lo(RUNR,maact,A,REQMSE) $ ((p_animReq(RUNR,maact,A,REQMSE) LT 0) $ (p_nSolved(RAGG) gt 15) )= 1.7 * p_aprDistAnimReq(RUNR,maact,A,REQMSE,"MEAN");

    Departures from CAPRI: v_feedCost's lower bound (l. 662) is not set: CST_ is left out."""
    fic, pfc, n = st.v_feedInpCoeff, st.p_feedInpCoeff, st.p_nSolved[RAGG]
    for r in RUNR:
        for a in st.MAACT:
            for t in st.A:
                for f in st.FEED:
                    fic.L[(r, a, t, f)] = pfc.get((r, a, t, f, "ini"), 0.0)
                    if pfc.get((r, a, t, f, "LowLim"), 0.0) and n > 5:
                        fic.LO[(r, a, t, f)] = fic.lo((r, a, t, f)) / 10
                    if pfc.get((r, a, t, f, "LowLim"), 0.0) and n > 10:
                        fic.LO[(r, a, t, f)] = 0.0
    rr = set(RUNR)
    for r in st.rall_in_ms():
        for a in st.MAACT:
            for t in st.A:
                for f in st.FEED:
                    if not st.p_maxFeedShare.get((r, a, t, f), 0.0):
                        fic.fx((r, a, t, f), 0.0)
                        fic.L[(r, a, t, f)] = 0.0
                _feed_aggregates_bounds_rall(st, r, a, t, r in rr)
    if n > 15:
        d, va = st.p_aprDistAnimReq, st.v_animReq
        for r in RUNR:
            for a in st.MAACT:
                for t in st.A:
                    for q in st.REQMSE:
                        p, mean = st.p_animReq.get((r, a, t, q), 0.0), d.get((r, a, t, q, "Mean"), 0.0)
                        va.LO[(r, a, t, q)] = 0.3 * mean if p else 0.0
                        va.UP[(r, a, t, q)] = 1.7 * mean if p else 0.0
                        if p < 0:
                            va.UP[(r, a, t, q)] = 0.3 * mean
                            va.LO[(r, a, t, q)] = 1.7 * mean


def fix_tiny_coefficients(st, RUNR) -> bool:
    r"""Where the solution has feed input coefficients of at most 1e-6 but not 0, all coefficients of at most 1e-6 are
    fixed at 0 for one more solve (CAPRI: tiny values trouble the later PMP calibration). Returns whether any was.

    CAPRI's GAMS (feed/fedtrm_cal_pw.gms l. 714-724):

                 elseif (    sum((RUNR,maact,A,FEED) $ ( (v_feedInpCoeff.L(RUNR,maact,A,FEED) LE 1.E-6)
                                                       $ (v_feedInpCoeff.L(RUNR,maact,A,FEED) NE 0)),  1)
                        and (p_nSolved(RAGG) <= p_nSolveMax)),
        *                and (p_nSolved(RAGG) <= 50)),
        *
        *           --- if the solution produces very small feed input coefficients, set to zero and resolve
        *               MaK: It might happen that some tiny values are sometimes a bit above or below the 1E-6 depending on the gams version, start value or .....
        *                    This leads to INF percenatge changes in the sensitivity tests, but avoids problems in pmp calibration (small values can create trouble there)
        *
                    v_feedInpCoeff.L (RUNR,maact,A,FEED) $ (v_feedInpCoeff.L(RUNR,maact,A,FEED) LE 1.E-6) = 0;
                    v_feedInpCoeff.FX(RUNR,maact,A,FEED) $ (v_feedInpCoeff.L(RUNR,maact,A,FEED) LE 1.E-6) = 0;

    Departures from CAPRI: none. With IPOPT's interior solution a coefficient CONOPT would leave at its bound 0 ends
    slightly above it, so this re-solve is the rule here, not the exception."""
    fic = st.v_feedInpCoeff
    keys = [(r, a, t, f) for r in RUNR for a in st.MAACT for t in st.A for f in st.FEED]
    if not any(fic.l(k) <= 1.E-6 and fic.l(k) != 0 for k in keys):
        return False
    for k in keys:
        if fic.l(k) <= 1.E-6:
            fic.L[k] = 0.0
            fic.fx(k, 0.0)
    return True


def DATA_straw(st, RUNR) -> None:
    r"""The straw's balance in the data after the solve: the straw fed (FSTR's production) the use less the losses, the
    losses, and the balance's positions and unit values that follow.

    CAPRI's GAMS (feed/fedtrm_cal_pw.gms l. 767-785):

                    DATA(RUNR,"GROF","FSTR","Y") = v_feedQuantReg.L(RUNR,"FSTR") - v_lossQuant.L(RUNR,"STRA");
                    DATA(RUNR,"LOSF","STRA","Y") $ DATA(RUNR,"GROF","STRA","Y")
                                                 = v_lossQuant.L(RUNR,"STRA");

                    DATA(RUNR,"LOSF","STRA","CUR") = DATA(RUNR,"LOSF","STRA","Y");
                    DATA(RUNR,"GROF","STRA","CUR") = DATA(RUNR,"GROF","STRA","Y");
                    DATA(RUNR,"STCM","STRA","Y") = 0;
                    DATA(RUNR,"NETF","FSTR","Y") = DATA(RUNR,"GROF","FSTR","Y");
                    DATA(RUNR,"NETF","STRA","Y") = DATA(RUNR,"GROF","FSTR","Y");
                    DATA(RUNR,"FEDM","FSTR","Y") = DATA(RUNR,"GROF","FSTR","Y");
                    DATA(RUNR,"FEDM","STRA","Y") = DATA(RUNR,"GROF","FSTR","Y");
                    DATA(RUNR,"DOMM","STRA","Y") = DATA(RUNR,"GROF","FSTR","Y");
                    DATA(RUNR,"MAPR","STRA","Y") = DATA(RUNR,"NETF","STRA","Y");
        *
                    DATA(RUNR,"UVAG","STRA","Y") $ DATA(RUNR,"GROF","STRA","Y")
                                                 = DATA(RUNR,"UVAP","STRA","Y") * DATA(RUNR,"NETF","STRA","Y")/DATA(RUNR,"GROF","STRA","Y");
                    DATA(RUNR,"UVAP","FSTR","Y") = DATA(RUNR,"UVAP","STRA","Y");
                    DATA(RUNR,"UVAB","FSTR","Y") = DATA(RUNR,"UVAP","STRA","Y");
                    DATA(RUNR,"UVAG","FSTR","Y") = DATA(RUNR,"UVAP","STRA","Y");

    Departures from CAPRI: none; the "CUR" positions (l. 771-772) are not kept: the port's DATA is the year's ("Y")."""
    D = st.DATA
    for r in RUNR:
        D[(r, "GROF", "FSTR")] = st.v_feedQuantReg.l((r, "FSTR")) - st.v_lossQuant.l((r, "STRA"))
        if D.get((r, "GROF", "STRA"), 0.0):
            D[(r, "LOSF", "STRA")] = st.v_lossQuant.l((r, "STRA"))
        D[(r, "STCM", "STRA")] = 0.0
        g = D[(r, "GROF", "FSTR")]
        for k in (("NETF", "FSTR"), ("NETF", "STRA"), ("FEDM", "FSTR"), ("FEDM", "STRA"), ("DOMM", "STRA")):
            D[(r,) + k] = g
        D[(r, "MAPR", "STRA")] = D[(r, "NETF", "STRA")]
        if D.get((r, "GROF", "STRA"), 0.0):
            D[(r, "UVAG", "STRA")] = D.get((r, "UVAP", "STRA"), 0.0) * D[(r, "NETF", "STRA")] / D[(r, "GROF", "STRA")]
        for c in ("UVAP", "UVAB", "UVAG"):
            D[(r, c, "FSTR")] = D.get((r, "UVAP", "STRA"), 0.0)


def DATA_feeding(st, RUNR) -> None:
    r"""The calibration's result stored in the data: the requirements and the feed per head, the days, the feed
    produced and its net supply; the units' priors deleted.

    CAPRI's GAMS (feed/fedtrm_cal_pw.gms l. 816-846):

                    DATA(RUNR,maact,REQSR,"Y") = SUM(A, p_animReq(RUNR,maact,A,REQSR) * p_technFact(RUNR,maact,"LEVL",A ));
        *
        *           --- store feeding per head in data matrix
        *
                    DATA(RUNR,maact,FEED,"Y") = SUM(A, v_feedInpCoeff.L(RUNR,maact,A,FEED) * p_technFact(RUNR,maact,"LEVL",A ));
        *
        *           --- store feeding cost per head in data matrix
        *
                    DATA(RUNR,maact,"FEED","Y") = SUM(A, v_feedCost.L(RUNR,maact,A) * p_technFact(RUNR,maact,"LEVL",A));

                    DATA(RUNR,DACT,"FEED","Y") $ (DATA(RUNR,DACT,"LEVL","Y") gt eps)
                       = SUM( DACT_TO_PACT(DACT,MACT), DATA(RUNR,MACT,"FEED","Y")*DATA(RUNR,MACT,"LEVL","Y"))/DATA(RUNR,DACT,"LEVL","Y");
        *
                    p_technFact(RUNR,maact,"FEED",A) $ DATA(RUNR,maact,"FEED","Y")
                        = v_feedCost.L(RUNR,maact,A) / DATA(RUNR,maact,"FEED","Y") - 1.;
        *
        *           --- store days
        *
                    DATA(RUNR,maact,"CATT","Y") = SUM(A, p_animProdDays(RUNR,maact,A) * p_technFact(RUNR,maact,"LEVL",A));
                    DATA(RUNR,maact,"DAYS","Y") = DATA(RUNR,maact,"CATT","Y");
        *
        *           --- store total production, including v_lossQuant
        *
                    DATA(RUNR,"GROF",FEED,"Y")      = SUM( maact, DATA(RUNR,maact,FEED,"Y") * DATA(RUNR,maact,"LEVL","Y")) * 0.001;
        *
                    DATA(RUNR,"NETF",FEED_TRD,"Y")  = DATA(RUNR,"GROF",FEED_TRD,"Y");
        *
                    p_aprDistAnimReq(RUNR,maact,A,REQMSE,"Mean")    = 0.;
                    p_aprDistAnimReq(RUNR,maact,A,REQMSE,"StdDev")  = 0.;
                    p_aprDistFeedCost(RUNR,maact,A,"Mean")         = 0.;
                    p_aprDistFeedCost(RUNR,maact,A,"StdDev")       = 0.;

    Departures from CAPRI: the feed cost per head (DATA "FEED", p_technFact "FEED", l. 824-830), its prior
    p_aprDistFeedCost (l. 845-846) and the "Penalty" row (l. 847-853) are not written: CST_ and v_feedCost are left
    out (capri_mod/feed/equations/fedtrm_mod_pw.py)."""
    D, fic = st.DATA, st.v_feedInpCoeff
    for r in RUNR:
        for a in st.MAACT:
            for q in st.REQSR:
                D[(r, a, q)] = sum(st.p_animReq.get((r, a, t, q), 0.0) * st.p_technFact.get((r, a, "LEVL", t), 0.0)
                                   for t in st.A)
            for f in st.FEED:
                D[(r, a, f)] = sum(fic.l((r, a, t, f)) * st.p_technFact.get((r, a, "LEVL", t), 0.0) for t in st.A)
            D[(r, a, "CATT")] = sum(st.p_animProdDays.get((r, a, t), 0.0) * st.p_technFact.get((r, a, "LEVL", t), 0.0)
                                    for t in st.A)
            D[(r, a, "DAYS")] = D[(r, a, "CATT")]
        for f in st.FEED:
            D[(r, "GROF", f)] = sum(D.get((r, a, f), 0.0) * D.get((r, a, "LEVL"), 0.0) for a in st.MAACT) * 0.001
        for f in st.FEED_TRD:
            D[(r, "NETF", f)] = D[(r, "GROF", f)]
        for k in [k for k in st.p_aprDistAnimReq if k[0] == r and k[1] in st.MAACT and k[3] in st.REQMSE]:
            del st.p_aprDistAnimReq[k]


def store_results(st, RAGG, RUNR) -> None:
    """CAPRI's statements after an aggregate's final solve (feed/fedtrm_cal_pw.gms l. 757-847): DRMX, the straw's data,
    the calibrated requirements (after_solve's blocks) and the data's feeding. The restart copy p_animReqCopy (l. 759-
    760) is not kept: no restart file is written."""
    c = CalState(RUNR=tuple(RUNR), MAACT=st.MAACT, p_animReq=st.p_animReq, v_feedInpCoeff_L=st.v_feedInpCoeff.L,
                 p_animProdDays=st.p_animProdDays, p_maxFeedShare=st.p_maxFeedShare, DATA_content=st.DATA,
                 R_RAGG_MS={r: st.MS for r in RUNR},
                 DATA_LEVL={(r, a): st.DATA.get((r, a, "LEVL"), 0.0) for r in RUNR for a in st.MAACT},
                 v_animReq_L=st.v_animReq.L)
    v_animReq_DRMX(c)
    DATA_straw(st, RUNR)
    v_animReq_from_ration(c)
    p_animReq_calibrated(c)
    DATA_feeding(st, RUNR)


def solve_RAGG(st, RAGG, RUNAGG, RUNR, log=None) -> dict:
    """SOLVE m_hpdFeed for the aggregate's units (capri_mod/feed/equations/fedtrm_mod_pw.py), counted in
    p_nSolved."""
    m = mp.m_hpdFeed(st, RUNR, RUNAGG)
    res = mp.solve_m_hpdFeed(m)
    st.p_nSolved[RAGG] = st.p_nSolved.get(RAGG, 0) + 1
    res.update(variables=len(m.X), rows=len(m.G), solves=st.p_nSolved[RAGG])
    if log is not None:
        log.append((RAGG, res))
    return res


def calibrate_RAGG(st, R_LEVL, RAGG, log=None) -> None:
    r"""One aggregate: its set-up, the first solve, then CAPRI's REPEAT until its solution is kept: after an infeasible
    solve the bounds relaxed and solved again (at most p_nSolveMax times, then CAPRI aborts); after one with tiny
    coefficients these fixed at 0 and solved again; otherwise the results stored.

    CAPRI's GAMS (feed/fedtrm_cal_pw.gms l. 585-587; the branches' statements in relax_infeasible,
    fix_tiny_coefficients and store_results):

                 if ( p_nSolved(ragg) gt (p_nSolveMax+1), abort "Internal error, probably no model solution returned in %system.fn%, line %system.incline%");

                 if ( ((m_hpdFeed.numinfes > 0) OR (m_hpdFeed.modelstat eq 4)) and (p_nSolved(RAGG) <= p_nSolveMax),

    CAPRI's GAMS, the second branch (feed/fedtrm_cal_pw.gms l. 714-716):

                 elseif (    sum((RUNR,maact,A,FEED) $ ( (v_feedInpCoeff.L(RUNR,maact,A,FEED) LE 1.E-6)
                                                       $ (v_feedInpCoeff.L(RUNR,maact,A,FEED) NE 0)),  1)
                        and (p_nSolved(RAGG) <= p_nSolveMax)),

    CAPRI's GAMS, the third branch (feed/fedtrm_cal_pw.gms l. 735):

                 elseif ( ( m_hpdFeed.numinfes > 0) OR (m_hpdFeed.modelstat eq 4) ),

    CAPRI's GAMS, its abort and the last branch (feed/fedtrm_cal_pw.gms l. 753-755):

                     abort "infeasibilities in feed calibration in %system.fn%, line %system.incline%";

                 else

    Departures from CAPRI: the aggregates of a level are solved one after the other, where CAPRI's grid mode solves
    them in parallel (their units are disjoint: the same result); an aggregate still infeasible after p_nSolveMax
    solves raises an error, CAPRI's abort."""
    RUNAGG, RUNR = setup_RAGG(st, R_LEVL, RAGG)
    st.p_nSolved[RAGG] = 0
    res = solve_RAGG(st, RAGG, RUNAGG, RUNR, log)
    while True:
        if st.p_nSolved[RAGG] > p_nSolveMax + 1:
            raise RuntimeError(f"feed calibration of {RAGG}: no solution after {st.p_nSolved[RAGG]} solves")
        if not res["feasible"] and st.p_nSolved[RAGG] <= p_nSolveMax:
            relax_infeasible(st, RAGG, RUNR)
            res = solve_RAGG(st, RAGG, RUNAGG, RUNR, log)
        elif st.p_nSolved[RAGG] <= p_nSolveMax and fix_tiny_coefficients(st, RUNR):
            res = solve_RAGG(st, RAGG, RUNAGG, RUNR, log)
        elif not res["feasible"]:
            raise RuntimeError(f"infeasibilities in the feed calibration of {RAGG} ({st.MS}) after "
                               f"{st.p_nSolved[RAGG]} solves: {res}")
        else:
            store_results(st, RAGG, RUNR)
            return


def fedtrm_cal_pw(st, log=None):
    r"""The baseline feed calibration of one member state (feed/fedtrm_cal_pw.gms l. 81-886), on FedtrmState st after
    fedtrm_prep and fedtrm_prior_pw: the standard deviations (fedtrm_mod_pw.gms l. 67-86), then by regional level (R_LEVL,
    CAPRI's order) each aggregate calibrated (calibrate_RAGG). log, a list, receives each solve's result.

    Departures from CAPRI: the module docstring's and those of the functions."""
    mp.p_aprDistAnimReq_StdDev(st)
    for lev in st.R_LEVL:
        for ragg in RAGG_of_level(st, lev):
            calibrate_RAGG(st, lev, ragg, log)
    return st
