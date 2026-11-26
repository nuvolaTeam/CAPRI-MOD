r"""The sows' and fattening pigs' rows (feed/req_or_man_fnc.gms, 'man' mode; moved from
capri_mod/feed/equations/req_or_man_fnc.py as they were, 26 November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.data.definitions import capri_set
from capri_mod.feed.equations.manure_output.state import ManState, curRows  # noqa: E402




# ------------------------------------------------------------------ (8) sows
def p_dataCopy_curRows_SOWS(st: ManState) -> None:
    r"""Sows: P2O5 and K2O at the tail, the sow's (200 kg a year) and its piglets' (10 kg over 42 days) manure.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 986-996):

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,"SOWS",curRows,%yr%) $ p_dataCopy(RS,"SOWS","LEVL",%yr%)
            = p_NutContManureKgM3("SOWS",curRows) * ( 365. * 200.
        *      10 kg liveweight of piglet...
             + 10.*0.001*p_dataCopy(RS,"SOWS","YPIG",%yr%)
        *      ... over 42 days
        *pw    NOTE: might be improved using p_dataCopy(RS,"PIGF","YDAYS",%yr%), but this varies from 44 to 125 days.
        *      => revision postponed until there is time for thorough testing
             * 42);
        $endif

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SOWS"):
            for row in curRows:
                st.p_dataCopy[(r, "SOWS", row)] = st.p_NutContManureKgM3[("SOWS", row)] * (
                    365. * 200. + 10. * 0.001 * st.dc(r, "SOWS", "YPIG") * 42)


def p_crprReq_SOWS(st: ManState) -> None:
    r"""Sows: the crude-protein requirement, the sow's and 5.7 kg per piglet.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 998-1001):

        * --- ... and nitrogen (copied below to CRPR if needed)
        *
          p_crprReq(RS,"SOWS",A,%yr%) $ (p_dataCopy(RS,"SOWS","LEVL",%yr%)*p_technFact(RS,"SOWS","LEVL",A))
            = 101.71 + 46.5 + 0.001*p_dataCopy(RS,"SOWS","YPIG",%yr%) *(p_technFact(RS,"SOWS","YPIG",A)+1.)* 5.7;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SOWS"):
            for t in st.techs(r, "SOWS"):
                st.p_crprReq[(r, "SOWS", t)] = (101.71 + 46.5 + 0.001 * st.dc(r, "SOWS", "YPIG")
                                                * (st.tf(r, "SOWS", "YPIG", t) + 1.) * 5.7)


# ------------------------------------------------------------------ (9) pig fattening
def p_finalLiveWgt_PIGF(st: ManState) -> None:
    r"""Fattened pigs: the final live weight, the carcass over its share, at least just above the lightest weight
    class of CAPRI's requirement tables (CAPRI's fix for tiny herds).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1038-1058):

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

    Without CAPRI's tables (dat/feed/porkreq.gms) the fattened pigs are left out: nothing is assigned, and
    ManState.not_computed names them. Departures from CAPRI: none."""
    if not (st.p_pigsReqLowWgt and st.p_pigsReqHighWgt):
        st.not_computed.add("PIGF")
        return
    start = st.p_startWgt["PIGF"]
    lo = min((v for (c, k), v in st.p_pigsReqLowWgt.items() if k == "XALW" and v > start), default=0.0) + .1
    hi = min((v for (c, k), v in st.p_pigsReqHighWgt.items() if k == "XALW" and v > start), default=0.0) + .1
    for r in st.RS:
        if st.LEVL(r, "PIGF"):
            st.p_finalLiveWgt[(r, "PIGF")] = st.dc(r, "PIGF", "PORK") / st.p_carcassShare["PIGF"]
        st.p_finalLiveWgt[(r, "PIGF")] = max(st.p_finalLiveWgt.get((r, "PIGF"), 0.0), lo, hi)


#: CAPRI's switch between its low and high final-weight requirement tables (l. 1048: 0, the high table always)
SwitchLiveWgt = 0


def _pig_classes(st: ManState, table: dict, final: float):
    """The weight classes of a pig requirement table with start weight < XALW < the final live weight."""
    start = st.p_startWgt["PIGF"]
    return [c for (c, k), v in table.items() if k == "XALW" and start < v < final]


def p_fatngDays_PIGF(st: ManState) -> None:
    r"""Fattened pigs: the fattening days, those of the heaviest weight class below the final live weight.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1061-1067):

          p_fatngDays(RS,"PIGF",%yr_A%) $ ((p_finalLiveWgt(RS,"PIGF",%yr_A%) LT %SwitchLiveWgt%) $ p_finalLiveWgt(RS,"PIGF",%yr_A%) )
            = SMAX(porkFinWgtLo $ (     (p_pigsReqLowWgt(porkFinWgtLo,"XALW") < p_finalLiveWgt(RS,"PIGF",%yr_A%))
                                      $ (p_pigsReqLowWgt(porkFinWgtLo,"XALW") > p_startWgt("PIGF"))   ), p_pigsReqLowWgt(porkFinWgtLo,"XDUF"));
        *
          p_fatngDays(RS,"PIGF",%yr_A%) $ ((p_finalLiveWgt(RS,"PIGF",%yr_A%) GE  %SwitchLiveWgt%) $ p_finalLiveWgt(RS,"PIGF",%yr_A%) )
            = SMAX(porkFinWgtHi $ (     (p_pigsReqHighWgt(porkFinWgtHi,"XALW") < p_finalLiveWgt(RS,"PIGF",%yr_A%))
                                      $ (p_pigsReqHighWgt(porkFinWgtHi,"XALW") > p_startWgt("PIGF"))  ), p_pigsReqHighWgt(porkFinWgtHi,"XDUF"));

    Departures from CAPRI: none."""
    for r in st.RS:
        f = st.p_finalLiveWgt.get((r, "PIGF"), 0.0)
        if not f:
            continue
        table = st.p_pigsReqLowWgt if f < SwitchLiveWgt else st.p_pigsReqHighWgt
        st.p_fatngDays[(r, "PIGF")] = max((table[(c, "XDUF")] for c in _pig_classes(st, table, f)), default=0.0)


def p_dataCopy_curRows_PIGF(st: ManState) -> None:
    r"""Fattened pigs: P2O5 and K2O at the tail.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1069-1074):

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,"PIGF",curRows,%yr%) $ p_dataCopy(RS,"PIGF","LEVL",%yr%)
            = p_NutContManureKgM3("PIGF",curRows) * p_fatngDays(RS,"PIGF",%yr_A%)
                            * (p_finalLiveWgt(RS,"PIGF",%yr_A%)-p_startWgt("PIGF")) * 0.5;
        $endif

    Departures from CAPRI: none."""
    if not (st.p_pigsReqLowWgt and st.p_pigsReqHighWgt):
        return
    for r in st.RS:
        if st.LEVL(r, "PIGF"):
            for row in curRows:
                st.p_dataCopy[(r, "PIGF", row)] = (st.p_NutContManureKgM3[("PIGF", row)] * st.p_fatngDays.get((r, "PIGF"), 0.0)
                                                   * (st.p_finalLiveWgt[(r, "PIGF")] - st.p_startWgt["PIGF"]) * 0.5)


def p_crprReq_PIGF(st: ManState) -> None:
    r"""Fattened pigs: the crude-protein requirement, the sum over the weight classes up to the final live weight, plus
    15%.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1076-1092):

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

    Departures from CAPRI: none."""
    for r in st.RS:
        f = st.p_finalLiveWgt.get((r, "PIGF"), 0.0)
        if not (st.LEVL(r, "PIGF") and f):
            continue
        table = st.p_pigsReqLowWgt if f < SwitchLiveWgt else st.p_pigsReqHighWgt
        for t in st.techs(r, "PIGF"):
            st.p_crprReq[(r, "PIGF", t)] = sum(table[(c, "CRPR")] for c in _pig_classes(st, table, f))
    for k in [k for k in st.p_crprReq if k[1] == "PIGF" and st.p_crprReq[k]]:
        st.p_crprReq[k] = st.p_crprReq[k] * 1.15
