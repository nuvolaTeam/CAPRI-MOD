r"""The sows' and fattening pigs' requirements (feed/req_or_man_fnc.gms, 'req' mode; moved from
capri_mod/feed/equations/req_or_man_fnc_req.py as they were, 26 November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.feed.equations.req_or_man_fnc import (BULF, CALF, CALR, DCOW, HEIF, NRUMI, DATA_AGGR_YCOW,  # noqa: F401
                                                     p_stockingRate)
from capri_mod.data.definitions import capri_set
from capri_mod.feed.equations.requirements.state import A_ALL, REQSC, ReqState, _set_req  # noqa: E402




# ------------------------------------------------------------------ (8) sows
def SOWS_requirements(st: ReqState) -> None:
    r"""Sows: the crude protein, the production days (365), the metabolisable energy for pigs, the dry matter,
    lysine and the minimum and maximum dry matter, per sow and its piglets.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1000-1021):

          p_crprReq(RS,"SOWS",A,%yr%) $ (p_dataCopy(RS,"SOWS","LEVL",%yr%)*p_technFact(RS,"SOWS","LEVL",A))
            = 101.71 + 46.5 + 0.001*p_dataCopy(RS,"SOWS","YPIG",%yr%) *(p_technFact(RS,"SOWS","YPIG",A)+1.)* 5.7;
        *
        *
        * --- next group of statements only needed for energy, dry matter etc, but not excretions
        $iftheni %req% ==on

          p_animProdDays(RS,"SOWS",%yr_A% %addtimedim%) $ p_technFact(RS,"SOWS","LEVL",A)= 365. ;
        *
          p_animReq(RS,"SOWS",A,"ENNE" %addtimedim%) $ p_technFact(RS,"SOWS","LEVL",A) = 0;
          p_animReq(RS,"SOWS",A,"ENMP" %addtimedim%) $ p_technFact(RS,"SOWS","LEVL",A)
            = 8219.75  +  3703.2 + 0.001*p_dataCopy(RS,"SOWS","YPIG",%yr%)*(p_technFact(RS,"SOWS","YPIG",A)+1.) * 404.75;
        *
          p_animReq(RS,"SOWS",A,"DRMA" %addtimedim%) $ p_technFact(RS,"SOWS","LEVL",A)
            = 610.35 + 261 + 0.001*p_dataCopy(RS,"SOWS","YPIG",%yr%) *(p_technFact(RS,"SOWS","YPIG",A)+1.) * 26.1;
        *
          p_animReq(RS,"SOWS",A,"LISI" %addtimedim%) $ p_technFact(RS,"SOWS","LEVL",A)
            = 0.610 + 0.372 + 0.001*p_dataCopy(RS,"SOWS","YPIG",%yr%) * (p_technFact(RS,"SOWS","YPIG",A)+1.)* 0.074;
        *
          p_animReq(RS,"SOWS",A,"DRMN" %addtimedim%) $ p_technFact(RS,"SOWS","LEVL",A) = p_animReq(RS,"SOWS",A,"ENMP" %addtimedim%) / 14.82 ;
        *
          p_animReq(RS,"SOWS",A,"DRMX" %addtimedim%) $ p_technFact(RS,"SOWS","LEVL",A) = p_animReq(RS,"SOWS",A,"ENMP" %addtimedim%) / 13.47 ;

    Departures from CAPRI: none."""
    a = "SOWS"
    for r in st.RS:
        for t in st.techs(r, a):
            yp = 0.001 * st.dc(r, a, "YPIG") * (st.tf(r, a, "YPIG", t) + 1.)
            if st.dc(r, a, "LEVL"):
                st.p_crprReq[(r, a, t)] = 101.71 + 46.5 + yp * 5.7
            st.p_animProdDays[(r, a, t)] = 365.
            _set_req(st, r, a, t, "ENNE", 0)
            _set_req(st, r, a, t, "ENMP", 8219.75 + 3703.2 + yp * 404.75)
            _set_req(st, r, a, t, "DRMA", 610.35 + 261 + yp * 26.1)
            _set_req(st, r, a, t, "LISI", 0.610 + 0.372 + yp * 0.074)
            _set_req(st, r, a, t, "DRMN", st.req(r, a, t, "ENMP") / 14.82)
            _set_req(st, r, a, t, "DRMX", st.req(r, a, t, "ENMP") / 13.47)


# ------------------------------------------------------------------ (9) pig fattening
#: CAPRI's switch between its low and high final-weight requirement tables (l. 1048: 0, the high table always)
SwitchLiveWgt = 0


def PIGF_requirements(st: ReqState) -> None:
    r"""Fattened pigs: the final live weight (the carcass over its share, at least just above the lightest weight
    class of CAPRI's tables), the fattening days, the crude protein (the classes' sum, plus 15%), the other
    requirements summed over the weight classes up to the final weight, and the production days (the member state's).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1038-1127):

          p_finalLiveWgt(RS,"PIGF",%yr_A%)  $ %p_condition%(RS,"PIGF","LEVL",%yr_A%)
            = (p_dataCopy(RS,"PIGF","PORK",%yr%)
        $iftheni %req% ==on
             *(p_technFact(RS,"PIGF","PORK",A)+1.)
        $endif
             / p_carcassShare("PIGF")) ;
        *
        * --- the version before 2013-3-10 may be reactivated as follows:
        *$setlocal SwitchLiveWgt 115
        *     after problems detected in DK (MK/PW 2013-3-10) modify setting to use high final weight function regardless of statistical weight
        $setlocal SwitchLiveWgt 0

        *     -- fix for special case where slaughter weights of PIGF may be below the smallest weight considered in req fnc
        *        (encountered in TUR with tiny LEVL): smin(porkFinWgtHi, p_pigsReqHighWgt(porkFinWgtHi,"XALW")) > p_finalLiveWgt(RS,"PIGF",%yr_A%)
        *        This gives p_fatngDays = -inf and zero requirements. To counteract this, we simply raise p_finalLiveWgt, if needed
        *        contrary to the data, to barely exceed the minimum p_pigsReqHighWgt(porkFinWgtHi,"XALW") (about 20.5 kg)

          p_finalLiveWgt(RS,"PIGF",%yr_A%)
            = max(p_finalLiveWgt(RS,"PIGF",%yr_A%),
                  SMIN(porkFinWgtLo $ (p_pigsReqLowWgt(porkFinWgtLo,"XALW") > p_startWgt("PIGF")), p_pigsReqLowWgt(porkFinWgtLo,"XALW"))+.1,
                  SMIN(porkFinWgtHi $ (p_pigsReqHighWgt(porkFinWgtHi,"XALW") > p_startWgt("PIGF")), p_pigsReqHighWgt(porkFinWgtHi,"XALW"))+.1);


          p_fatngDays(RS,"PIGF",%yr_A%) $ ((p_finalLiveWgt(RS,"PIGF",%yr_A%) LT %SwitchLiveWgt%) $ p_finalLiveWgt(RS,"PIGF",%yr_A%) )
            = SMAX(porkFinWgtLo $ (     (p_pigsReqLowWgt(porkFinWgtLo,"XALW") < p_finalLiveWgt(RS,"PIGF",%yr_A%))
                                      $ (p_pigsReqLowWgt(porkFinWgtLo,"XALW") > p_startWgt("PIGF"))   ), p_pigsReqLowWgt(porkFinWgtLo,"XDUF"));
        *
          p_fatngDays(RS,"PIGF",%yr_A%) $ ((p_finalLiveWgt(RS,"PIGF",%yr_A%) GE  %SwitchLiveWgt%) $ p_finalLiveWgt(RS,"PIGF",%yr_A%) )
            = SMAX(porkFinWgtHi $ (     (p_pigsReqHighWgt(porkFinWgtHi,"XALW") < p_finalLiveWgt(RS,"PIGF",%yr_A%))
                                      $ (p_pigsReqHighWgt(porkFinWgtHi,"XALW") > p_startWgt("PIGF"))  ), p_pigsReqHighWgt(porkFinWgtHi,"XDUF"));
        *
        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,"PIGF",curRows,%yr%) $ p_dataCopy(RS,"PIGF","LEVL",%yr%)
            = p_NutContManureKgM3("PIGF",curRows) * p_fatngDays(RS,"PIGF",%yr_A%)
                            * (p_finalLiveWgt(RS,"PIGF",%yr_A%)-p_startWgt("PIGF")) * 0.5;
        $endif

        * --- ... and nitrogen (copied below to CRPR if needed)
        *
          p_crprReq(RS,"PIGF",A,%yr%) $ ( (p_dataCopy(RS,"PIGF","LEVL",%yr%)*p_technFact(RS,"PIGF","LEVL",A))
                                        $ (p_finalLiveWgt(RS,"PIGF",%yr_A%) LT %SwitchLiveWgt%)
                                        $  p_finalLiveWgt(RS,"PIGF",%yr_A%) )
            = SUM(porkFinWgtLo $ ( (p_pigsReqLowWgt(porkFinWgtLo,"XALW")<p_finalLiveWgt(RS,"PIGF",%yr_A%))
                                 $ (p_pigsReqLowWgt(porkFinWgtLo,"XALW")>p_startWgt("PIGF")) ),      p_pigsReqLowWgt(porkFinWgtLo,"CRPR"));
        *
          p_crprReq(RS,"PIGF",A,%yr%) $ ( (p_dataCopy(RS,"PIGF","LEVL",%yr%)*p_technFact(RS,"PIGF","LEVL",A))
                                        $ (p_finalLiveWgt(RS,"PIGF",%yr_A%) GE %SwitchLiveWgt%)
                                        $  p_finalLiveWgt(RS,"PIGF",%yr_A%) )
             = SUM(porkFinWgtHi $ ( (p_pigsReqHighWgt(porkFinWgtHi,"XALW")<p_finalLiveWgt(RS,"PIGF",%yr_A%))
                                  $ (p_pigsReqHighWgt(porkFinWgtHi,"XALW")>p_startWgt("PIGF")) ),    p_pigsReqHighWgt(porkFinWgtHi,"CRPR"));
        *
        * --- unmotivated correction of Italian table from before 2007. Unclear if this is still needed, beneficial or harmful.

          p_crprReq(RS,"PIGF",A,%yr%) $ p_crprReq(RS,"PIGF",A,%yr%) = p_crprReq(RS,"PIGF",A,%yr%) * 1.15;
        *
        * --- next group of statements only needed for energy, dry matter etc, but not excretions
        $iftheni.req1 %req% ==on

          p_animReq(RS,"PIGF",A,"ENNE" %addtimedim%) $ p_technFact(RS,"PIGF","LEVL",A) = 0;

        *     -- requirements for pig with final weight < threshold

          p_animReq(RS,"PIGF",A,REQSC %addtimedim%) $ (  p_technFact(RS,"PIGF","LEVL",A)
                                         $ (p_finalLiveWgt(RS,"PIGF",%yr_A%) LT %SwitchLiveWgt%)
                                         $ p_finalLiveWgt(RS,"PIGF",%yr_A%)
                                         $ (not sameas("CRPR",REQSC)))
            = SUM(porkFinWgtLo $ ( (p_pigsReqLowWgt(porkFinWgtLo,"XALW")<p_finalLiveWgt(RS,"PIGF",%yr_A%))
                                 $ (p_pigsReqLowWgt(porkFinWgtLo,"XALW")>p_startWgt("PIGF")) ),  p_pigsReqLowWgt(porkFinWgtLo,REQSC));

        *     -- requirements for pig with final weight > threshold

          p_animReq(RS,"PIGF",A,REQSC %addtimedim%) $ (  p_technFact(RS,"PIGF","LEVL",A)
                                         $ (p_finalLiveWgt(RS,"PIGF",%yr_A%) GE %SwitchLiveWgt%)
                                         $ p_finalLiveWgt(RS,"PIGF",%yr_A%)
                                         $ (not sameas("CRPR",REQSC)))
            = SUM(porkFinWgtHi $ ( (p_pigsReqHighWgt(porkFinWgtHi,"XALW")<p_finalLiveWgt(RS,"PIGF",%yr_A%))
                                 $ (p_pigsReqHighWgt(porkFinWgtHi,"XALW")>p_startWgt("PIGF")) ), p_pigsReqHighWgt(porkFinWgtHi,REQSC));
        *
        *     -- total production days for conversion of requirements into daily values:
        *        pw091111 NOTE: These are taken from COCO, rather than from the tables,
        *        because the fattening days from the tables are in conflict with statistical information.
        *        Thus we accept some inconsistency between the fattening days implicit in the requirement calculation (Italian tables)
        *        and the production days used to convert between total and daily values. The latter are based on statistics,
        *        because they will also serve to convert between LEVL and HERD.
        *
        *pw  p_animProdDays(RS,"PIGF",%yr_A%) $ p_technFact(RS,"PIGF","LEVL",A) = MAX(p_fatngDays(RS,"PIGF",A),10);
          p_animProdDays(RS,"PIGF",%yr_A% %addtimedim%) $ p_technFact(RS,"PIGF","LEVL",A)
            = MAX(SUM(R_RAGG(RS,MS),p_dataCopy(MS,"PIGF","DAYS",%yr%)),
                  p_reqfcnlim("PIGF","DAYS","lo"));

    Without CAPRI's tables (dat/feed/porkreq.gms) the fattened pigs are left out (ReqState.not_computed).
    Departures from CAPRI: none."""
    a = "PIGF"
    if not (st.p_pigsReqLowWgt and st.p_pigsReqHighWgt):
        st.not_computed.add(a)
        return
    start = st.p_startWgt[a]
    lo = min((v for (c, k), v in st.p_pigsReqLowWgt.items() if k == "XALW" and v > start), default=0.0) + .1
    hi = min((v for (c, k), v in st.p_pigsReqHighWgt.items() if k == "XALW" and v > start), default=0.0) + .1

    def classes(table, f):
        return [c for (c, k), v in table.items() if k == "XALW" and start < v < f]
    items = sorted({k for (_, k) in st.p_pigsReqHighWgt} | {k for (_, k) in st.p_pigsReqLowWgt})
    for r in st.RS:
        for t in st.techs(r, a):
            st.p_finalLiveWgt[(r, a, t)] = st.dc(r, a, "PORK") * (st.tf(r, a, "PORK", t) + 1.) / st.p_carcassShare[a]
        for t in A_ALL:
            st.p_finalLiveWgt[(r, a, t)] = max(st.g(st.p_finalLiveWgt, r, a, t), lo, hi)
        for t in A_ALL:
            f = st.p_finalLiveWgt[(r, a, t)]
            table = st.p_pigsReqLowWgt if f < SwitchLiveWgt else st.p_pigsReqHighWgt
            st.p_fatngDays[(r, a, t)] = max((table[(c, "XDUF")] for c in classes(table, f)), default=0.0)
        for t in st.techs(r, a):
            f = st.p_finalLiveWgt[(r, a, t)]
            table = st.p_pigsReqLowWgt if f < SwitchLiveWgt else st.p_pigsReqHighWgt
            if st.dc(r, a, "LEVL"):
                st.p_crprReq[(r, a, t)] = sum(table[(c, "CRPR")] for c in classes(table, f))
        for t in A_ALL:
            if st.g(st.p_crprReq, r, a, t):
                st.p_crprReq[(r, a, t)] = st.p_crprReq[(r, a, t)] * 1.15
        for t in st.techs(r, a):
            _set_req(st, r, a, t, "ENNE", 0)
        for t in st.techs(r, a):
            f = st.p_finalLiveWgt[(r, a, t)]
            table = st.p_pigsReqLowWgt if f < SwitchLiveWgt else st.p_pigsReqHighWgt
            for item in REQSC:
                if item == "CRPR":
                    continue
                _set_req(st, r, a, t, item, sum(table.get((c, item), 0.0) for c in classes(table, f)))
        for t in st.techs(r, a):
            st.p_animProdDays[(r, a, t)] = max(st.ms_sum(r, lambda m: st.dc(m, a, "DAYS")), st.lim(a, "DAYS", "lo"))
    del items
