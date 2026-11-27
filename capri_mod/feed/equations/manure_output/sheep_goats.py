r"""The sheep and goats' rows (feed/req_or_man_fnc.gms, 'man' mode; moved from
capri_mod/feed/equations/req_or_man_fnc.py as they were, 26 November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.data.definitions import capri_set
from capri_mod.feed.equations.manure_output.state import ManState, curRows  # noqa: E402




# ------------------------------------------------------------------ (12) sheep and goats for milk
def p_sharGoatHerd(st: ManState) -> None:
    r"""Sheep and goats for milk: the goats' share of the member state's sheep and goat herds (10% where unknown).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1250-1255):

          p_sharGoatHerd(RS,%yr%) $ p_dataCopy(RS,"SHGM","LEVL",%yr%)
            = SUM(R_RAGG(RS,MS), p_dataCopy(MS,"GOAT","HERD",%yr%)
                               /(p_dataCopy(MS,"GOAT","HERD",%yr%)+p_dataCopy(MS,"SHEP","HERD",%yr%)))
                 $      SUM(R_RAGG(RS,MS), p_dataCopy(MS,"GOAT","HERD",%yr%)+p_dataCopy(MS,"SHEP","HERD",%yr%))
             +0.1
                 $ (NOT SUM(R_RAGG(RS,MS), p_dataCopy(MS,"GOAT","HERD",%yr%)+p_dataCopy(MS,"SHEP","HERD",%yr%)));

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SHGM"):
            tot = st.ms_sum(r, lambda m: st.dc(m, "GOAT", "HERD") + st.dc(m, "SHEP", "HERD"))
            st.p_sharGoatHerd[r] = (st.ms_sum(r, lambda m: st.dc(m, "GOAT", "HERD")
                                              / (st.dc(m, "GOAT", "HERD") + st.dc(m, "SHEP", "HERD"))) if tot else 0.0) \
                + (0.1 if not tot else 0.0)


def p_meanLiveWgt_SHGM(st: ManState) -> None:
    r"""Sheep and goats for milk: the ewes' (55 kg) and goats' (60 kg) mean live weights, and the activity's, weighted
    by the goats' share.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1259-1264):

          p_meanLiveWgt(RS,"EWES",%yr_A%)  $ %p_condition%(RS,"SHGM","LEVL",%yr_A%) = 55. ;
          p_meanLiveWgt(RS,"GOAT",%yr_A%)  $ %p_condition%(RS,"SHGM","LEVL",%yr_A%) = 60. ;
        *
          p_meanLiveWgt(RS,"SHGM",%yr_A%)  $ %p_condition%(RS,"SHGM","LEVL",%yr_A%)
            = p_meanLiveWgt(RS,"EWES",%yr_A%) * (1-p_sharGoatHerd(RS,%yr%))
             +p_meanLiveWgt(RS,"GOAT",%yr_A%) * p_sharGoatHerd(RS,%yr%) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SHGM"):
            st.p_meanLiveWgt[(r, "EWES")] = 55.
            st.p_meanLiveWgt[(r, "GOAT")] = 60.
            s = st.p_sharGoatHerd.get(r, 0.0)
            st.p_meanLiveWgt[(r, "SHGM")] = st.p_meanLiveWgt[(r, "EWES")] * (1 - s) + st.p_meanLiveWgt[(r, "GOAT")] * s


def p_milkPerDay_SHGM(st: ManState) -> None:
    r"""Sheep and goats for milk: the milk per milking day (170 days), sold and fed.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1268-1272):

           p_milkPerDay(RS,"SHGM",%yr_A% %addtimedim%)  $ %p_condition%(RS,"SHGM","LEVL",%yr_A%) =
        $ifi %req% ==on (p_technFact(RS,"SHGM","SGMI",A)+1.) *
                         p_dataCopy(RS,"SHGM","SGMI",%yr%) / 170. +
        $ifi %req% ==on (p_technFact(RS,"SHGM","SGMF",A)+1.) *
                         p_dataCopy(RS,"SHGM","SGMF",%yr%) / 170.;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SHGM"):
            st.p_milkPerDay[(r, "SHGM")] = st.dc(r, "SHGM", "SGMI") / 170. + st.dc(r, "SHGM", "SGMF") / 170.


def p_dataCopy_curRows_SHGM(st: ManState) -> None:
    r"""Sheep and goats for milk: P2O5 and K2O at the tail, the cattle manure per kg of live weight and day.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1274-1278):

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,"SHGM",curRows,%yr%) $ p_dataCopy(RS,"SHGM","LEVL",%yr%)
            = p_NutContManureKgM3("CATTLE",curRows) * 365. * p_meanLiveWgt(RS,"SHGM",%yr_A%);
        $endif

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SHGM"):
            for row in curRows:
                st.p_dataCopy[(r, "SHGM", row)] = (st.p_NutContManureKgM3[("CATTLE", row)] * 365.
                                                   * st.p_meanLiveWgt[(r, "SHGM")])


def p_crprReq_EWES(st: ManState) -> None:
    r"""Sheep and goats for milk: the ewes' crude-protein requirement, maintenance (135 days), milking (170 days) and
    the last mating period (60 days, g).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1283-1289):

          p_crprReq(RS,"EWES",A,%yr%) $ (p_dataCopy(RS,"SHGM","LEVL",%yr%)*p_technFact(RS,"SHGM","LEVL",A))
        *     -- for maintenance
            =   ( 0.026 + 0.0014 * p_meanLiveWgt(RS,"EWES",%yr_A%)) * 135.
        *     -- for milk production
              + ( 0.0634 + 0.0012 * p_meanLiveWgt(RS,"EWES",%yr_A%) + 0.0895 * p_milkPerDay(RS,"SHGM",%yr_A% %addtimedim%)) * 170.
        *     -- for last mating period
              + ( ( 2.22 * p_meanLiveWgt(RS,"EWES",%yr_A%) - 19.88) * 1.35 ) * 60. / 1000. ;

    In this project's notation, as GAMS's precedence reads it: only the last period's term is divided by 1000.
    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SHGM"):
            w, m = st.p_meanLiveWgt[(r, "EWES")], st.p_milkPerDay[(r, "SHGM")]
            for t in st.techs(r, "SHGM"):
                st.p_crprReq[(r, "EWES", t)] = ((0.026 + 0.0014 * w) * 135.
                                                + (0.0634 + 0.0012 * w + 0.0895 * m) * 170.
                                                + ((2.22 * w - 19.88) * 1.35) * 60. / 1000.)


def p_crprReq_GOAT(st: ManState) -> None:
    r"""Sheep and goats for milk: the goats' crude-protein requirement (g, over 1000).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1292-1299):

          p_crprReq(RS,"GOAT",A,%yr%) $ (p_dataCopy(RS,"SHGM","LEVL",%yr%)*p_technFact(RS,"SHGM","LEVL",A))
        *     -- for maintenance
        *        NOTE: the maintenance component of phases (1) + (2) is aggregated for GOAT: 135+170=305 days
            = ( ( 12.66 + 0.8 * p_meanLiveWgt(RS,"GOAT",%yr_A%)) * 305.
        *     -- for milk production
              + ( 61. * p_milkPerDay(RS,"SHGM",%yr_A% %addtimedim%)) * 170.
        *     -- for last mating period
              + ( 1.425 * p_meanLiveWgt(RS,"GOAT",%yr_A%) + 14.666) * 60. ) / 1000. ;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SHGM"):
            w, m = st.p_meanLiveWgt[(r, "GOAT")], st.p_milkPerDay[(r, "SHGM")]
            for t in st.techs(r, "SHGM"):
                st.p_crprReq[(r, "GOAT", t)] = ((12.66 + 0.8 * w) * 305. + (61. * m) * 170.
                                                + (1.425 * w + 14.666) * 60.) / 1000.


def p_crprReq_SHGM(st: ManState) -> None:
    r"""Sheep and goats for milk: the activity's crude-protein requirement, the goats' and ewes' by the goats' share.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1301-1304):

          p_crprReq(RS,"SHGM",A,%yr%) $ p_dataCopy(RS,"SHGM","LEVL",%yr%)
            =   (  p_crprReq(RS,"GOAT",A,%yr%) * p_sharGoatHerd(RS,%yr%)
                 + p_crprReq(RS,"EWES",A,%yr%) * (1-p_sharGoatHerd(RS,%yr%)))
                                        ;

    Departures from CAPRI: none (over CAPRI's technologies with an ewe's or goat's requirement)."""
    for r in st.RS:
        if st.LEVL(r, "SHGM"):
            s = st.p_sharGoatHerd.get(r, 0.0)
            for t in {k[2] for k in st.p_crprReq if k[0] == r and k[1] in ("EWES", "GOAT")}:
                st.p_crprReq[(r, "SHGM", t)] = (st.p_crprReq.get((r, "GOAT", t), 0.0) * s
                                                + st.p_crprReq.get((r, "EWES", t), 0.0) * (1 - s))


# ------------------------------------------------------------------ (13) sheep and goats fattening
def p_dailyWgtIncrease_SHGF(st: ManState) -> None:
    r"""Sheep and goats fattening: the daily gain (g), the member state's, within CAPRI's limits.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1407-1410):

          p_dailyWgtIncrease(RS,"SHGF",%yr_A%)  $ %p_condition%(RS,"SHGF","LEVL",%yr_A%)
            = MIN(p_reqfcnlim("SHGF","DAILY","up"),
                  MAX(p_reqfcnlim("SHGF","DAILY","lo"),
                      SUM(R_RAGG(RS,MS),p_dataCopy(MS,"SHGF","DAILY",%yr%)))) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SHGF"):
            st.p_dailyWgtIncrease[(r, "SHGF")] = min(st.lim("SHGF", "DAILY", "up"), max(
                st.lim("SHGF", "DAILY", "lo"), st.ms_sum(r, lambda m: st.dc(m, "SHGF", "DAILY"))))


def p_fatngDays_SHGF(st: ManState) -> None:
    r"""Sheep and goats fattening: the fattening days, the final live weight (the carcass over its share) at the daily
    gain, between 10 and 365.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1414-1416):

          p_fatngDays(RS,"SHGF",%yr_A%)  $ %p_condition%(RS,"SHGF","LEVL",%yr_A%)
            = MIN(365. , MAX(10. ,( p_dataCopy(RS,"SHGF","SGMT",%yr%)/ p_carcassShare("SHGF") )
                                 /(p_dailyWgtIncrease(RS,"SHGF",%yr_A%)/1000.))) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SHGF"):
            st.p_fatngDays[(r, "SHGF")] = min(365., max(10., (st.dc(r, "SHGF", "SGMT") / st.p_carcassShare["SHGF"])
                                                        / (st.p_dailyWgtIncrease[(r, "SHGF")] / 1000.)))


def p_meanLiveWgt_SHGF(st: ManState) -> None:
    r"""Sheep and goats fattening: the mean live weight, half the final weight (carcass between 8 and 25 kg).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1420-1422):

          p_meanLiveWgt(RS,"SHGF",%yr_A%)  $ %p_condition%(RS,"SHGF","LEVL",%yr_A%)
        *    Bounds as in coco1_anim:
            = MAX(8.,MIN(25.,p_dataCopy(RS,"SHGF","SGMT",%yr%)))/p_carcassShare("SHGF")/2.;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SHGF"):
            st.p_meanLiveWgt[(r, "SHGF")] = max(8., min(25., st.dc(r, "SHGF", "SGMT"))) / st.p_carcassShare["SHGF"] / 2.


def p_dataCopy_curRows_SHGF(st: ManState) -> None:
    r"""Sheep and goats fattening: P2O5 and K2O at the tail.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1425-1429):

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,"SHGF",curRows,%yr%) $ p_dataCopy(RS,"SHGF","LEVL",%yr%)
            = p_NutContManureKgM3("CATTLE",curRows) * p_fatngDays(RS,"SHGF",%yr_A%) * p_meanLiveWgt(RS,"SHGF",%yr_A%);
        $endif

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SHGF"):
            for row in curRows:
                st.p_dataCopy[(r, "SHGF", row)] = (st.p_NutContManureKgM3[("CATTLE", row)] * st.p_fatngDays[(r, "SHGF")]
                                                   * st.p_meanLiveWgt[(r, "SHGF")])


def p_crprReq_SHGF(st: ManState) -> None:
    r"""Sheep and goats fattening: the crude-protein requirement (g, over 1000).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1433-1435):

          p_crprReq(RS,"SHGF",A,%yr%) $ (p_dataCopy(RS,"SHGF","LEVL",%yr%)*p_technFact(RS,"SHGF","LEVL",A))
            = ( ( 21.778 + 0.33 * p_meanLiveWgt(RS,"SHGF",%yr_A%) + 0.258 * p_dailyWgtIncrease(RS,"SHGF",%yr_A%))
               * 1.35 * p_fatngDays(RS,"SHGF",%yr_A%)) / 1000.;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SHGF"):
            for t in st.techs(r, "SHGF"):
                st.p_crprReq[(r, "SHGF", t)] = ((21.778 + 0.33 * st.p_meanLiveWgt[(r, "SHGF")]
                                                 + 0.258 * st.p_dailyWgtIncrease[(r, "SHGF")])
                                                * 1.35 * st.p_fatngDays[(r, "SHGF")]) / 1000.
