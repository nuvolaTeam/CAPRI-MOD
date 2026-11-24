r"""CAPRI's requirements at the simulation year (capmod/def_requirements.gms; CAPRI star 3.0): the requirement
functions at the year's yields (feed/req_or_man_fnc.gms 'req', capri_mod/feed/equations/req_or_man_fnc_req.py), kept as
the literature requirements, scaled by CAPREG's base-year corrections and by the yearly technical progress in feeding,
and the feed shares shifted with the main output's growth.

CAPRI runs it from capmod.gms l. 1061 (and capmod/create_sim_ini_gdx.gms l. 423), in baseline mode before the feed
calibration (capmod/def_fert_and_requirements.gms, baseline/fedtrm_*). CAPREG's corrections p_animReqCorrFac are
CAPREG's results reqrel_<base year><country>.gdx (capmod/load_feed.gms l. 56-60: p_animReqCorrFac1 of CAPREG).

After it CAPRI's baseline calibrates the requirements to the feed statistics (capmod/def_fert_and_requirements.gms
l. 38-57, baseline/fedtrm_*); its simulation runs def_requirements again and multiplies the result by the calibration's
corrections (baseline/adjust.gms, capri_mod/feed/equations/adjust.py).

One function per CAPRI statement block, on the requirement call's state (req_or_man_fnc_req.ReqState) with
DefReqInputs; def_requirements runs them in CAPRI's order. CAPRI's REQM is its REQSR (sets.gms: ALIAS(REQSR,REQM)).
Departures from CAPRI: none in the functions.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.feed.equations import req_or_man_fnc_req as rq


@dataclass
class DefReqInputs:
    """The inputs of def_requirements.gms besides the requirement call's: RU, CAPRI's regional units; MPACT, its
    production activities; PACT_TO_Y, {(animal, main output)}; DATA_BAS, DATA at "BAS"; p_animReqCorrFac, CAPREG's
    corrections {(region, animal, A, requirement or feed): value} (relative: the requirement is multiplied by
    value + 1);
    SIMY, BAS: CAPRI's CALYEA of the simulation and the base year; BAS_IS_SIM: %BAS% == %SIM% (CAPRI's ex-post run);
    FODDO, CAPRI's fodder outputs (sets.gms).
    Written by the functions: v_actLevl_L, p_yieldGrowth, p_animReqLit, p_animExcrProtCorrFact_Y, p_shiftMainOutput,
    and DATA_TRD (DATA at "TRD", the fodder outputs set to zero where no animal can use them)."""
    RU: tuple
    MPACT: tuple
    PACT_TO_Y: frozenset
    DATA_BAS: dict
    p_animReqCorrFac: dict
    SIMY: int
    BAS: int
    BAS_IS_SIM: bool = False
    FODDO: tuple = ()
    DATA_TRD: dict = field(default_factory=dict)
    v_actLevl_L: dict = field(default_factory=dict)
    p_yieldGrowth: dict = field(default_factory=dict)
    p_animReqLit: dict = field(default_factory=dict)
    p_animExcrProtCorrFact_Y: dict = field(default_factory=dict)
    p_shiftMainOutput: dict = field(default_factory=dict)


def v_actLevl(st: rq.ReqState, d: DefReqInputs) -> None:
    r"""The activity levels per technology: the level times the technology's share.

    CAPRI's GAMS (capmod/def_requirements.gms l. 22):

                v_actLevl.L(RU,MPACT,A) = DATA(RU,MPACT,"LEVL","Y") * p_technFact(RU,MPACT,"LEVL",A);

    Departures from CAPRI: none."""
    for r in d.RU:
        for a in d.MPACT:
            for t in rq.A_ALL:
                v = st.D(r, a, "LEVL") * st.tf(r, a, "LEVL", t)
                if v:
                    d.v_actLevl_L[(r, a, t)] = v


def p_yieldGrowth(st: rq.ReqState, d: DefReqInputs) -> None:
    r"""The growth of each animal's main output since the base year (the sum over its main outputs of the year's yield
    over the base year's).

    CAPRI's GAMS (capmod/def_requirements.gms l. 24-26):

                p_yieldGrowth(RS,MAACT) $ data(RS,MAACT,"LEVL","BAS")
                  = SUM(PACT_TO_Y(MAACT,animO) $ data(RS,MAACT,animO,"BAS"),
                      data(RS,MAACT,animO,"Y")/data(RS,MAACT,animO,"BAS") );

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in st.MAACT:
            if st.g(d.DATA_BAS, r, a, "LEVL"):
                d.p_yieldGrowth[(r, a)] = sum(st.D(r, a, o) / d.DATA_BAS[(r, a, o)] for (c, o) in d.PACT_TO_Y
                                              if c == a and st.g(d.DATA_BAS, r, a, o))


def DATA_FODDO_unused(st: rq.ReqState, d: DefReqInputs) -> None:
    r"""The fodder outputs (but straw) of a crop set to zero, at "TRD" and "Y", where no animal of the region can feed
    them.

    CAPRI's GAMS (capmod/def_requirements.gms l. 31-32):

               DATA(RU,MPACT,FODDO,"TRD") $ ((not sameas(FODDO,"STRA")) $ (NOT sum( (MAACT,A,FEED_TO_O(FODDI,FODDO)), p_maxFeedShare(RU,MAACT,A,FODDI))) $ pact_to_o(MPACT,FODDO)) = 0;
               DATA(RU,MPACT,FODDO,"Y")   $ ((not sameas(FODDO,"STRA")) $ (NOT sum( (MAACT,A,FEED_TO_O(FODDI,FODDO)), p_maxFeedShare(RU,MAACT,A,FODDI))) $ pact_to_o(MPACT,FODDO)) = 0;

    FODDO: CAPRI's fodder outputs (DefReqInputs.FODDO). Departures from CAPRI: none."""
    for r in d.RU:
        for foddo in d.FODDO:
            if foddo == "STRA":
                continue
            # SUM((MAACT, A, FEED_TO_O(FODDI, FODDO)), p_maxFeedShare(RU, MAACT, A, FODDI)): all the inputs it feeds
            if sum(st.g(st.p_maxFeedShare, r, a, t, fi) for fi, fo in st.FEED_TO_O if fo == foddo and fi in rq.FODDI
                   for a in st.MAACT for t in rq.A_ALL):
                continue
            for c, o in st.PACT_TO_O:
                if o == foddo and c in d.MPACT:
                    for dd in (d.DATA_TRD, st.DATA):
                        if (r, c, o) in dd:
                            dd[(r, c, o)] = 0


def p_animReqLit(st: rq.ReqState, d: DefReqInputs) -> None:
    r"""The literature requirements, kept before CAPRI's corrections.

    CAPRI's GAMS (capmod/def_requirements.gms l. 36):

               p_animReqLit(RU,MAACT,A,REQSC) = p_animReq(RU,MAACT,A,REQSC);

    Departures from CAPRI: none."""
    for (r, a, t, item), v in st.p_animReq.items():
        if r in d.RU and a in st.MAACT and item in rq.REQSC:
            d.p_animReqLit[(r, a, t, item)] = v


def erase_without_herd(st: rq.ReqState, d: DefReqInputs) -> None:
    r"""The requirements and feed shares erased where the technology has no herd.

    CAPRI's GAMS (capmod/def_requirements.gms l. 39-41):

               p_animReq(RU,MAACT,A,REQM)      $ (v_actLevl.L(RU,MAACT,A) LE 1.E-10) = 0;
               p_maxFeedShare(RU,MAACT,A,FEED) $ (v_actLevl.L(RU,MAACT,A) LE 1.E-10) = 0;
               p_minFeedShare(RU,MAACT,A,FEED) $ (v_actLevl.L(RU,MAACT,A) LE 1.E-10) = 0;

    Departures from CAPRI: none."""
    ru = set(d.RU)
    for dct, items in ((st.p_animReq, rq.REQSR), (st.p_maxFeedShare, rq.FEED), (st.p_minFeedShare, rq.FEED)):
        for k in list(dct):
            r, a, t, item = k
            if r in ru and a in st.MAACT and item in items and d.v_actLevl_L.get((r, a, t), 0.0) <= 1.E-10:
                dct[k] = 0


def p_animReqCorrFac_inequalities(st: rq.ReqState, d: DefReqInputs) -> None:
    r"""CAPREG's corrections of the inequality requirements (dry matter, fibre, intake) erased but lysine's: the
    baseline's inequality rows stay at the literature (except in CAPRI's ex-post run).

    CAPRI's GAMS (capmod/def_requirements.gms l. 46-52):

        *  --- fix requirements to "technology frontier" from the requirement functions
        *      multiplied with the correction from CAPREG in the base year
        *      but excluding inequality constraints like dry matter intake.
        *      The latter should push the baseline result towards engineerng information

        *      [except for expost run where we do not have a baseline feed calibration to reflect inefficiencies]
        $ifi not %BAS% == %SIM%   p_animReqCorrFac(RU,MAACT,A,REQMSN) $ (NOT SAMEAS(REQMSN,"LISI")) = 0;

    Departures from CAPRI: none."""
    if d.BAS_IS_SIM:
        return
    reqmsn = ("DRMN", "DRMX", "LISI", "FICO", "FICT", "FISM", "FISF", "FIDI", "FILG")    # CAPRI's REQMSN (sets.gms)
    for k in list(d.p_animReqCorrFac):
        if k[0] in d.RU and k[1] in st.MAACT and k[3] in reqmsn and k[3] != "LISI":
            d.p_animReqCorrFac[k] = 0


def p_animReq_CAPREG(st: rq.ReqState, d: DefReqInputs) -> None:
    r"""The requirements and the feeds' entries times CAPREG's corrections (+ 1), and the protein factor of the
    manure from CAPREG's protein correction.

    CAPRI's GAMS (capmod/def_requirements.gms l. 53-55):

               p_animReq(RU,MAACT,A,REQM) $ (p_animReq(RU,MAACT,A,REQM) or sum(sameas(REQM,FEED),1)) = p_animReq(RU,MAACT,A,REQM)  * (p_animReqCorrFac(RU,MAACT,A,REQM)+1.);
        *
               p_animExcrProtCorrFact(RU,MAACT,A,"Y") $ p_technFact(RU,MAACT,"LEVL",A) = p_animReqCorrFac(RU,MAACT,A,"CRPR")+1.;

    Departures from CAPRI: none."""
    for r in d.RU:
        for a in st.MAACT:
            for t in rq.A_ALL:
                for item in rq.REQSR:
                    v = st.req(r, a, t, item)
                    # $ (p_animReq or a feed's row): a feed's empty row stays 0 (0 times the correction)
                    if v:
                        st.p_animReq[(r, a, t, item)] = v * (d.p_animReqCorrFac.get((r, a, t, item), 0.0) + 1.)
                if st.tf(r, a, "LEVL", t):
                    d.p_animExcrProtCorrFact_Y[(r, a, t)] = d.p_animReqCorrFac.get((r, a, t, "CRPR"), 0.0) + 1.


def technical_progress(st: rq.ReqState, d: DefReqInputs) -> None:
    r"""The technical progress in feeding, a yearly rate since the base year: energy, protein, the manure's protein
    factor, fibre and intake capacities less 0.2% a year, lysine 0.3%, the feeds' entries plus 0.5%, the minimum dry
    matter less 0.5%, the maximum plus 0.2%.

    CAPRI's GAMS (capmod/def_requirements.gms l. 58-76):

               if ( CALYEA("%SIMY%") - CALYEA("BAS"),
        *
        *  ---  reduce requirements by 0.2 % per year to account for input saving technical
        *       progress in feeding
        *
        $batinclude 'util\title.gms' "'Techn. progress in feeding for year '"
        *
        *         --- take into account the ammount of "luxury" feeding in the base period, and shrink with 2%
        *
                  p_animReq(RU,MAACT,A,"ENNE") $ p_animReq(RU,MAACT,A,"ENNE") = p_animReq(RU,MAACT,A,"ENNE") * 0.998 **(CALYEA("%SIMY%")-CALYEA("BAS"));
                  p_animReq(RU,MAACT,A,"CRPR") $ p_animReq(RU,MAACT,A,"CRPR") = p_animReq(RU,MAACT,A,"CRPR") * 0.998 **(CALYEA("%SIMY%")-CALYEA("BAS"));
                  p_animExcrProtCorrFact(RU,MAACT,A,"Y") $ p_technFact(RU,MAACT,"LEVL",A) = p_animExcrProtCorrFact(RU,MAACT,A,"Y") * 0.998 **(CALYEA("%SIMY%")-CALYEA("BAS"));
                  p_animReq(RU,MAACT,A,"LISI") $ p_animReq(RU,MAACT,A,"LISI") = p_animReq(RU,MAACT,A,"LISI") * 0.997 **(CALYEA("%SIMY%")-CALYEA("BAS"));
                  p_animReq(RU,MAACT,A,REQDRM) $ p_animReq(RU,MAACT,A,REQDRM) = p_animReq(RU,MAACT,A,REQDRM) * 0.998 **(CALYEA("%SIMY%")-CALYEA("BAS"));
                  p_animReq(RU,MAACT,A,"FIDI") $ p_animReq(RU,MAACT,A,"FIDI") = p_animReq(RU,MAACT,A,"FIDI") * 0.998 **(CALYEA("%SIMY%")-CALYEA("BAS"));
        *
                  p_animReq(RU,MAACT,A,FEED) $ p_animReq(RU,MAACT,A,FEED)     = p_animReq(RU,MAACT,A,FEED)   * 1.005 **(CALYEA("%SIMY%")-CALYEA("BAS"));
                  p_animReq(RU,MAACT,A,"DRMN") $ p_animReq(RU,MAACT,A,"DRMN") = p_animReq(RU,MAACT,A,"DRMN") * 0.995 **(CALYEA("%SIMY%")-CALYEA("BAS"));
                  p_animReq(RU,MAACT,A,"DRMX") $ p_animReq(RU,MAACT,A,"DRMX") = p_animReq(RU,MAACT,A,"DRMX") * 1.002 **(CALYEA("%SIMY%")-CALYEA("BAS"));

    REQDRM holds FIDI: FIDI's rate is applied twice, as in CAPRI. Departures from CAPRI: none."""
    n = d.SIMY - d.BAS
    if not n:
        return
    reqdrm = ("FICO", "FICT", "FISM", "FISF", "FIDI", "FILG")    # CAPRI's REQDRM (sets.gms): FIDI also in l. 72
    rates = [("ENNE", 0.998), ("CRPR", 0.998), ("LISI", 0.997)] + [(x, 0.998) for x in reqdrm] + [("FIDI", 0.998)] \
        + [(f, 1.005) for f in rq.FEED] + [("DRMN", 0.995), ("DRMX", 1.002)]
    for k in list(d.p_animExcrProtCorrFact_Y):
        d.p_animExcrProtCorrFact_Y[k] = d.p_animExcrProtCorrFact_Y[k] * 0.998 ** n
    ru = set(d.RU)
    for item, rate in rates:
        for k, v in list(st.p_animReq.items()):
            if k[0] in ru and k[1] in st.MAACT and k[3] == item and v:
                st.p_animReq[k] = v * rate ** n


def feed_shares_with_yield_growth(st: rq.ReqState, d: DefReqInputs) -> None:
    r"""The feed shares shifted with the main output's growth: where it grew, the minimum shares divided and the
    maximum shares multiplied by its square.

    CAPRI's GAMS (capmod/def_requirements.gms l. 80-87):

        *
                  p_shiftMainOutput(RU,MAACT,A) $ p_technFact(RU,MAACT,"LEVL",A) = p_yieldGrowth(RU,MAACT);
        *
                  p_minFeedShare(RU,MAACT,A,FEED) $ ((p_shiftMainOutput(RU,MAACT,A) GT 1) $ p_minFeedShare(RU,MAACT,A,FEED))
                     = p_minFeedShare(RU,MAACT,A,FEED) / SQR(p_shiftMainOutput(RU,MAACT,A));

                  p_maxFeedShare(RU,MAACT,A,FEED) $ ((p_shiftMainOutput(RU,MAACT,A) GT 1) $ p_maxFeedShare(RU,MAACT,A,FEED))
                      = p_maxFeedShare(RU,MAACT,A,FEED) * SQR(p_shiftMainOutput(RU,MAACT,A));

    Departures from CAPRI: none."""
    if not (d.SIMY - d.BAS):
        return
    for r in d.RU:
        for a in st.MAACT:
            for t in rq.A_ALL:
                if st.tf(r, a, "LEVL", t):
                    d.p_shiftMainOutput[(r, a, t)] = d.p_yieldGrowth.get((r, a), 0.0)
    for (r, a, t), s in d.p_shiftMainOutput.items():
        if s > 1:
            for f in rq.FEED:
                if st.g(st.p_minFeedShare, r, a, t, f):
                    st.p_minFeedShare[(r, a, t, f)] = st.p_minFeedShare[(r, a, t, f)] / s ** 2
                if st.g(st.p_maxFeedShare, r, a, t, f):
                    st.p_maxFeedShare[(r, a, t, f)] = st.p_maxFeedShare[(r, a, t, f)] * s ** 2


def def_requirements(st: rq.ReqState, d: DefReqInputs) -> tuple:
    r"""CAPRI's capmod/def_requirements.gms: the activity levels and yield growth, the requirement call
    (req_or_man_fnc_req.req_or_man_fnc_req, on st), then the blocks above in CAPRI's order. Returns (st, d)."""
    v_actLevl(st, d)
    p_yieldGrowth(st, d)
    rq.req_or_man_fnc_req(st)
    for block in (DATA_FODDO_unused, p_animReqLit, erase_without_herd, p_animReqCorrFac_inequalities, p_animReq_CAPREG,
                  technical_progress, feed_shares_with_yield_growth):
        block(st, d)
    return st, d
