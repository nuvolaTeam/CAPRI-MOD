r"""The calves' rows: light, heavy and replacement calves (feed/req_or_man_fnc.gms, 'man' mode; moved from
capri_mod/feed/equations/req_or_man_fnc.py as they were, 26 November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.data.definitions import capri_set
from capri_mod.feed.equations.manure_output.state import CALF, CALR, ManState, curRows  # noqa: E402




# ------------------------------------------------------------------ (3) fattening of calves
def _scaled_ms_daily(st: ManState, r, a):
    """SUM(R_RAGG(r, MS), p_dataCopy(MS, a, "DAILY") / p_stockingRate(MS)) * p_stockingRate(r)."""
    return st.ms_sum(r, lambda m: st.dc(m, a, "DAILY") / st.p_stockingRate[m]) * st.p_stockingRate.get(r, 0.0)


def p_dailyWgtIncrease_CALF(st: ManState) -> None:
    r"""The fattened calves' daily weight gain (kg): their member state's, scaled by the region's stocking rate over the
    member state's, within CAPRI's limits.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 343-347):

          p_dailyWgtIncrease(RS,CALF,%yr_A%) $ %p_condition%(RS,CALF,"LEVL",%yr_A%)
            = MIN(p_reqfcnlim(CALF,"DAILY","up"),
                  MAX(p_reqfcnlim(CALF,"DAILY","lo"),
                  SUM(R_RAGG(RS,MS),p_dataCopy(MS,CALF,"DAILY",%yr%)/p_stockingRate(MS,%yr%))*p_stockingRate(RS,%yr%)))
             / 1000;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            if st.LEVL(r, a):
                st.p_dailyWgtIncrease[(r, a)] = min(st.lim(a, "DAILY", "up"),
                                                    max(st.lim(a, "DAILY", "lo"), _scaled_ms_daily(st, r, a))) / 1000


def p_animProdDays_CALF(st: ManState) -> None:
    r"""The fattened calves' process length: the gain from the 50 kg start to the final live weight (the carcass over
    its share) at the daily gain, within CAPRI's limits.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 353-361):

          p_animProdDays(RS,CALF,%yr_A% %addtimedim%)  $ %p_condition%(RS,CALF,"LEVL",%yr_A%)
            = MIN(p_reqfcnlim(CALF,"DAYS","up"),
                  MAX(p_reqfcnlim(CALF,"DAYS","lo"),
                  ( p_dataCopy(RS,CALF,"BEEF",%yr%) / p_carcassShare(CALF)
        $iftheni.req6 %req% ==on
                            *(p_technFact(RS,CALF,"BEEF",A)+1.)
        $endif.req6
                  - p_startWgt(CALF))
                  / p_dailyWgtIncrease(RS,CALF,%yr_A%) ) );

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            if st.LEVL(r, a):
                st.p_animProdDays[(r, a)] = min(st.lim(a, "DAYS", "up"), max(st.lim(a, "DAYS", "lo"), (
                    st.dc(r, a, "BEEF") / st.p_carcassShare[a] - st.p_startWgt[a]) / st.p_dailyWgtIncrease[(r, a)]))


def _final_wgt_CALF(st: ManState, r, a):
    """p_dataCopy(r, a, "BEEF") / p_carcassShare(a): the fattened calf's final live weight ('man' mode)."""
    return st.dc(r, a, "BEEF") / st.p_carcassShare[a]


def p_meanLiveWgt_CALF_light(st: ManState) -> None:
    r"""(a) Light calves (final live weight up to 150 kg): the mean live weight, the start weight plus half the gain.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 367-374):

          p_meanLiveWgt(RS,CALF,%yr_A%) $ ((  p_dataCopy(RS,CALF,"BEEF",%yr%)
        $iftheni.req7 %req% ==on
                                             *(p_technFact(RS,CALF,"BEEF",A)+1.)
        $endif.req7
                                             / p_carcassShare(CALF))  LE 150. )
        *                          increase up to mid point of fattening period:
            = (p_startWgt(CALF) + (p_animProdDays(RS,CALF,%yr_A% %addtimedim%) * p_dailyWgtIncrease(RS,CALF,%yr_A%)) / 2.)
            $ %p_condition%(RS,CALF,"LEVL",%yr_A%);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            if _final_wgt_CALF(st, r, a) <= 150.:
                st.p_meanLiveWgt[(r, a)] = ((st.p_startWgt[a] + (st.p_animProdDays.get((r, a), 0.0)
                                                                 * st.p_dailyWgtIncrease.get((r, a), 0.0)) / 2.)
                                            if st.LEVL(r, a) else 0.0)


def p_fatngDays_CALF_light(st: ManState) -> None:
    r"""(a) Light calves: the fattening days, the whole process (one phase).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 377-384):

          p_fatngDays(RS,CALF,%yr_A%) = 0;
          p_fatngDays(RS,CALF,%yr_A%) $ ( (  ( p_dataCopy(RS,CALF,"BEEF",%yr%)
        $iftheni.req8 %req% ==on
                                             *(p_technFact(RS,CALF,"BEEF",A)+1.)
        $endif.req8
                                             / p_carcassShare(CALF))  LE 150. )
                                        $ %p_condition%(RS,CALF,"LEVL",%yr_A%))
            = p_animProdDays(RS,CALF,%yr_A% %addtimedim%);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            st.p_fatngDays[(r, a)] = 0
            if _final_wgt_CALF(st, r, a) <= 150. and st.LEVL(r, a):
                st.p_fatngDays[(r, a)] = st.p_animProdDays[(r, a)]


def p_dataCopy_curRows_CALF_light(st: ManState) -> None:
    r"""(a) Light calves: P2O5 and K2O at the tail, the cattle manure per kg of live weight and day.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 386-390):

        * --- Excretions of potassium and phosphorus...
        $iftheni.req9 not %req% ==on
          p_dataCopy(RS,CALF,curRows,%yr%) $ p_dataCopy(RS,CALF,"LEVL",%yr%)
            = p_NutContManureKgM3("CATTLE",curRows) * p_fatngDays(RS,CALF,%yr_A%)  * p_meanLiveWgt(RS,CALF,%yr_A%) ;
        $endif.req9

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            if st.LEVL(r, a):
                for row in curRows:
                    st.p_dataCopy[(r, a, row)] = (st.p_NutContManureKgM3[("CATTLE", row)] * st.p_fatngDays[(r, a)]
                                                  * st.p_meanLiveWgt.get((r, a), 0.0))


def _crpr_growth_lt150(mlw, daily, days):
    """( - 0.00039 * mean live weight + 0.000628 * daily gain [g] - 0.0193 ) * days: the crude protein of a calf's
    growth up to 150 kg (CAPRI's coefficients, feed/req_or_man_fnc.gms l. 395-396, 459-460, 616-617)."""
    return (- 0.00039 * mlw + 0.000628 * daily * 1000. - 0.0193) * days


def _crpr_growth_gt150(mlw, daily, days):
    """( 0.00109 * mean live weight + 0.00022 * daily gain [g] + 0.2027 ) * days: the crude protein of a calf's growth
    above 150 kg (CAPRI's coefficients, feed/req_or_man_fnc.gms l. 532, 681-682)."""
    return (0.00109 * mlw + 0.00022 * daily * 1000. + 0.2027) * days


def p_crprReq_CALF_light(st: ManState) -> None:
    r"""(a) Light calves: the crude-protein requirement of the fattening.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 392-396):

        * --- ... and nitrogen (copied below to CRPR if needed)
        *
          p_crprReq(RS,CALF,A,%yr%) $ (p_fatngDays(RS,CALF,%yr_A%) and p_technFact(RS,CALF,"LEVL",A))
            = ( - 0.00039 * p_meanLiveWgt(RS,CALF,%yr_A%)
                + 0.000628 * p_dailyWgtIncrease(RS,CALF,%yr_A%) * 1000. -0.0193 ) * p_fatngDays(RS,CALF,%yr_A%) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            if st.p_fatngDays.get((r, a)):
                for t in st.techs(r, a):
                    st.p_crprReq[(r, a, t)] = _crpr_growth_lt150(st.p_meanLiveWgt.get((r, a), 0.0),
                                                                 st.p_dailyWgtIncrease.get((r, a), 0.0),
                                                                 st.p_fatngDays[(r, a)])


def p_meanLiveWgt_CALF_heavy_b1(st: ManState) -> None:
    r"""(b1) Heavy calves (final live weight above 150 kg), first phase from 50 to 150 kg: mean live weight 100 kg.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 432-438):

          p_meanLiveWgt(RS,CALF,%yr_A%)  $ ((  p_dataCopy(RS,CALF,"BEEF",%yr%)
        $iftheni.req11 %req% ==on
                                             *(p_technFact(RS,CALF,"BEEF",A)+1.)
        $endif.req11
                                             / p_carcassShare(CALF))  GT 150. )
        *     Note: 100 = (50+150)/2 = mean weight
            = 100.  $ %p_condition%(RS,CALF,"LEVL",%yr_A%);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            if _final_wgt_CALF(st, r, a) > 150.:
                st.p_meanLiveWgt[(r, a)] = 100. if st.LEVL(r, a) else 0.0


def p_fatngDays_CALF_heavy_b1(st: ManState) -> None:
    r"""(b1) Heavy calves, first phase: the days of the 100 kg gain.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 440-448):

          p_fatngDays(RS,CALF,%yr_A%) = 0;
          p_fatngDays(RS,CALF,%yr_A%) $ ( (  ( p_dataCopy(RS,CALF,"BEEF",%yr%)
        $iftheni.req12 %req% ==on
                                             *(p_technFact(RS,CALF,"BEEF",A)+1.)
        $endif.req12
                                             / p_carcassShare(CALF))  GT 150. )
                                        $ %p_condition%(RS,CALF,"LEVL",%yr_A%))
        *     Note: 100 = 150-50 = increase in phase (b1):
            = 100. / p_dailyWgtIncrease(RS,CALF,%yr_A%);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            st.p_fatngDays[(r, a)] = 0
            if _final_wgt_CALF(st, r, a) > 150. and st.LEVL(r, a):
                st.p_fatngDays[(r, a)] = 100. / st.p_dailyWgtIncrease[(r, a)]


def p_dataCopy_curRows_CALF_heavy_b1(st: ManState) -> None:
    r"""(b1) Heavy calves, first phase: P2O5 and K2O at the tail.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 450-454):

        * --- Excretions of potassium and phosphorus...
        $iftheni.req13 not %req% ==on
          p_dataCopy(RS,CALF,curRows,%yr%) $ ( p_dataCopy(RS,CALF,"LEVL",%yr%)  $ p_fatngDays(RS,CALF,%yr_A%)  )
            = p_NutContManureKgM3("CATTLE",curRows) * p_fatngDays(RS,CALF,%yr_A%)  * p_meanLiveWgt(RS,CALF,%yr_A%) ;
        $endif.req13

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            if st.LEVL(r, a) and st.p_fatngDays.get((r, a)):
                for row in curRows:
                    st.p_dataCopy[(r, a, row)] = (st.p_NutContManureKgM3[("CATTLE", row)] * st.p_fatngDays[(r, a)]
                                                  * st.p_meanLiveWgt.get((r, a), 0.0))


def p_crprReq_CALF_heavy_b1(st: ManState) -> None:
    r"""(b1) Heavy calves, first phase: the crude-protein requirement.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 456-460):

        * --- ... and nitrogen (copied below to CRPR if needed)
        *
          p_crprReq(RS,CALF,A,%yr%) $ (p_fatngDays(RS,CALF,%yr_A%) and p_technFact(RS,CALF,"LEVL",A))
            = ( - 0.00039 * p_meanLiveWgt(RS,CALF,%yr_A%)
                + 0.000628 * p_dailyWgtIncrease(RS,CALF,%yr_A%) * 1000. -0.0193 ) * p_fatngDays(RS,CALF,%yr_A%) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            if st.p_fatngDays.get((r, a)):
                for t in st.techs(r, a):
                    st.p_crprReq[(r, a, t)] = _crpr_growth_lt150(st.p_meanLiveWgt.get((r, a), 0.0),
                                                                 st.p_dailyWgtIncrease.get((r, a), 0.0),
                                                                 st.p_fatngDays[(r, a)])


def p_meanLiveWgt_CALF_heavy_b2(st: ManState) -> None:
    r"""(b2) Heavy calves, second phase from 150 kg to the final weight: 150 kg plus half the phase's gain.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 493-503):

          p_meanLiveWgt(RS,CALF,%yr_A%) $ ((  p_dataCopy(RS,CALF,"BEEF",%yr%)
        $iftheni %req% ==on
                                            *(p_technFact(RS,CALF,"BEEF",A)+1.)
        $endif
                                            / p_carcassShare(CALF))  GT 150. )
        *       wgt at end of phase b1:
            =(   150.
        *         increase in b1+b2:
             +(p_animProdDays(RS,CALF,%yr_A% %addtimedim%) * p_dailyWgtIncrease(RS,CALF,%yr_A%)
        *         increase in b1:
               - 100 ) / 2.)  $ %p_condition%(RS,CALF,"LEVL",%yr_A%);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            if _final_wgt_CALF(st, r, a) > 150.:
                st.p_meanLiveWgt[(r, a)] = ((150. + (st.p_animProdDays.get((r, a), 0.0)
                                                     * st.p_dailyWgtIncrease.get((r, a), 0.0) - 100) / 2.)
                                            if st.LEVL(r, a) else 0.0)


def p_fatngDays_CALF_heavy_b2(st: ManState) -> None:
    r"""(b2) Heavy calves, second phase: its length.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 507-518):

          p_fatngDays(RS,CALF,%yr_A%) = 0;
          p_fatngDays(RS,CALF,%yr_A%) $ ( (  ( p_dataCopy(RS,CALF,"BEEF",%yr%)
        $iftheni %req% ==on
                                             *(p_technFact(RS,CALF,"BEEF",A)+1.)
        $endif
                                             / p_carcassShare(CALF))  GT 150. )
                                        $ %p_condition%(RS,CALF,"LEVL",%yr_A%))
        *     increase in b1+b2:
            =(p_animProdDays(RS,CALF,%yr_A% %addtimedim%) * p_dailyWgtIncrease(RS,CALF,%yr_A%)
        *     increase in b1:
              - 100)
            / p_dailyWgtIncrease(RS,CALF,%yr_A%);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            st.p_fatngDays[(r, a)] = 0
            if _final_wgt_CALF(st, r, a) > 150. and st.LEVL(r, a):
                d = st.p_dailyWgtIncrease[(r, a)]
                st.p_fatngDays[(r, a)] = (st.p_animProdDays[(r, a)] * d - 100) / d


def p_dataCopy_curRows_CALF_heavy_b2(st: ManState) -> None:
    r"""(b2) Heavy calves, second phase: P2O5 and K2O at the tail, added to the first phase's.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 521-526):

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,CALF,curRows,%yr%) $ ( p_dataCopy(RS,CALF,"LEVL",%yr%) $ p_fatngDays(RS,CALF,%yr_A%)  )
            =  p_dataCopy(RS,CALF,curRows,%yr%)
             + p_NutContManureKgM3("CATTLE",curRows) * p_fatngDays(RS,CALF,%yr_A%)  * p_meanLiveWgt(RS,CALF,%yr_A%);
        $endif

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            if st.LEVL(r, a) and st.p_fatngDays.get((r, a)):
                for row in curRows:
                    st.p_dataCopy[(r, a, row)] = (st.dc(r, a, row) + st.p_NutContManureKgM3[("CATTLE", row)]
                                                  * st.p_fatngDays[(r, a)] * st.p_meanLiveWgt.get((r, a), 0.0))


def p_crprReq_CALF_heavy_b2(st: ManState) -> None:
    r"""(b2) Heavy calves, second phase: the crude-protein requirement, added to the first phase's.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 528-532):

        * --- ... and nitrogen (copied below to CRPR if needed)
        *
          p_crprReq(RS,CALF,A,%yr%) $ (p_fatngDays(RS,CALF,%yr_A%) and p_technFact(RS,CALF,"LEVL",A))
            = p_crprReq(RS,CALF,A,%yr%)
             + ( 0.00109 * p_meanLiveWgt(RS,CALF,%yr_A%) + 0.00022 * p_dailyWgtIncrease(RS,CALF,%yr_A%) * 1000. + 0.2027 ) * p_fatngDays(RS,CALF,%yr_A%);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            if st.p_fatngDays.get((r, a)):
                for t in st.techs(r, a):
                    st.p_crprReq[(r, a, t)] = st.p_crprReq.get((r, a, t), 0.0) + _crpr_growth_gt150(
                        st.p_meanLiveWgt.get((r, a), 0.0), st.p_dailyWgtIncrease.get((r, a), 0.0), st.p_fatngDays[(r, a)])


# ------------------------------------------------------------------ (4) raising of calves
def CALR_weaning(st: ManState) -> None:
    r"""Raised calves, the first 49 days (weaning, 50 to 80 kg): fattening days, mean live weight and P2O5 and K2O at
    the tail.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 576-583):

        $iftheni not %req% ==on
          p_fatngDays(RS,CALR,%yr_A%) $ p_dataCopy(RS,CALR,"LEVL",%yr%)
            = 49;
          p_meanLiveWgt(RS,CALR,%yr_A%) $ p_dataCopy(RS,CALR,"LEVL",%yr%)
            = (50+80)/2;
          p_dataCopy(RS,CALR,curRows,%yr%)  $ p_dataCopy(RS,CALR,"LEVL",%yr%)
            = p_NutContManureKgM3("CATTLE",curRows) * p_fatngDays(RS,CALR,%yr_A%) * p_meanLiveWgt(RS,CALR,%yr_A%);
        $endif

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            if st.LEVL(r, a):
                st.p_fatngDays[(r, a)] = 49
                st.p_meanLiveWgt[(r, a)] = (50 + 80) / 2
                for row in curRows:
                    st.p_dataCopy[(r, a, row)] = (st.p_NutContManureKgM3[("CATTLE", row)] * st.p_fatngDays[(r, a)]
                                                  * st.p_meanLiveWgt[(r, a)])


def p_crprReq_CALR_weaning(st: ManState) -> None:
    r"""Raised calves, weaning: the crude protein of the milk powder, in increasing quantity over the seven weeks.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 585-589):

        * --- milking powder in increasing quantity
        *
        *     (remember that nitrogen excretions are copied below to CRPR if needed)
          p_crprReq(RS,CALR,A,%yr%)  $ (p_dataCopy(RS,CALR,"LEVL",%yr%) * p_technFact(RS,CALR,"LEVL",A) )
            = 0.35  * 0.1 * (2.+2.+5.+6.+7.+8.+8.)/7 * 49;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            if st.LEVL(r, a):
                for t in st.techs(r, a):
                    st.p_crprReq[(r, a, t)] = 0.35 * 0.1 * (2. + 2. + 5. + 6. + 7. + 8. + 8.) / 7 * 49


def CALR_80_150(st: ManState) -> None:
    r"""Raised calves, the next 125 days (80 to 150 kg): mean live weight, daily gain and fattening days.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 601-603):

          p_meanLiveWgt(RS,CALR,%yr_A%)      $ %p_condition%(RS,CALR,"LEVL",%yr_A%) = ( 80. + 150.) / 2. ;
          p_dailyWgtIncrease(RS,CALR,%yr_A%) $ %p_condition%(RS,CALR,"LEVL",%yr_A%) = (150.-80.)/125.;
          p_fatngDays(RS,CALR,%yr_A%)        $ %p_condition%(RS,CALR,"LEVL",%yr_A%) = ( 150. - 80. ) / p_dailyWgtIncrease(RS,CALR,%yr_A%) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            if st.LEVL(r, a):
                st.p_meanLiveWgt[(r, a)] = (80. + 150.) / 2.
                st.p_dailyWgtIncrease[(r, a)] = (150. - 80.) / 125.
                st.p_fatngDays[(r, a)] = (150. - 80.) / st.p_dailyWgtIncrease[(r, a)]


def p_dataCopy_curRows_CALR_80_150(st: ManState) -> None:
    r"""Raised calves, 80 to 150 kg: P2O5 and K2O at the tail, added to the weaning's.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 605-610):

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,CALR,curRows,%yr%)  $ p_dataCopy(RS,CALR,"LEVL",%yr%)
            =  p_dataCopy(RS,CALR,curRows,%yr%)
             + p_NutContManureKgM3("CATTLE",curRows) * p_fatngDays(RS,CALR,%yr_A%) * p_meanLiveWgt(RS,CALR,%yr_A%);
        $endif

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            if st.LEVL(r, a):
                for row in curRows:
                    st.p_dataCopy[(r, a, row)] = (st.dc(r, a, row) + st.p_NutContManureKgM3[("CATTLE", row)]
                                                  * st.p_fatngDays[(r, a)] * st.p_meanLiveWgt[(r, a)])


def p_crprReq_CALR_80_150(st: ManState) -> None:
    r"""Raised calves, 80 to 150 kg: the crude-protein requirement, added to the weaning's.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 612-617):

        * --- ... and nitrogen (copied below to CRPR if needed)
        *
           p_crprReq(RS,CALR,A,%yr%) $ (p_dataCopy(RS,CALR,"LEVL",%yr%) * p_technFact(RS,CALR,"LEVL",A) )
              =  p_crprReq(RS,CALR,A,%yr%)
               + ( - 0.00039 * p_meanLiveWgt(RS,CALR,%yr_A%)
                   + 0.000628 * p_dailyWgtIncrease(RS,CALR,%yr_A%) * 1000. - 0.0193 ) * p_fatngDays(RS,CALR,%yr_A%);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            if st.LEVL(r, a):
                for t in st.techs(r, a):
                    st.p_crprReq[(r, a, t)] = st.p_crprReq.get((r, a, t), 0.0) + _crpr_growth_lt150(
                        st.p_meanLiveWgt[(r, a)], st.p_dailyWgtIncrease[(r, a)], st.p_fatngDays[(r, a)])


def p_fatngDays_CALR_last(st: ManState) -> None:
    r"""Raised calves, the last phase (150 kg to the bulls' or heifers' start weight): its days, the member state's
    raising days less the first two phases', scaled by the region's stocking rate over the member state's, within
    CAPRI's limits.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 654-657):

          p_fatngDays(RS,CALR,%yr_A%) $ %p_condition%(RS,CALR,"LEVL",%yr_A%)
            = MAX(p_reqfcnlim(CALR,"DAYS","lo")-49-125,
                  MIN(p_reqfcnlim(CALR,"DAYS","up")-49-125,
                  SUM(R_RAGG(RS,MS),(p_dataCopy(MS,CALR,"DAYS",%yr%)-49-125)/p_stockingRate(MS,%yr%))*p_stockingRate(RS,%yr%)));

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            if st.LEVL(r, a):
                ms = st.ms_sum(r, lambda m: (st.dc(m, a, "DAYS") - 49 - 125) / st.p_stockingRate[m])
                st.p_fatngDays[(r, a)] = max(st.lim(a, "DAYS", "lo") - 49 - 125,
                                             min(st.lim(a, "DAYS", "up") - 49 - 125, ms * st.p_stockingRate.get(r, 0.0)))


def p_dailyWgtIncrease_CALR_last(st: ManState) -> None:
    r"""Raised calves, the last phase: the daily gain from 150 kg to the start weight of the bulls (male calves) or the
    heifers (female calves).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 659-662):

          p_dailyWgtIncrease(RS,"CAMR",%yr_A%) $ (%p_condition%(RS,"CAMR","LEVL",%yr_A%) $ p_fatngDays(RS,"CAMR",%yr_A%))
            = (p_startWgt("BULF") - 150) / p_fatngDays(RS,"CAMR",%yr_A%) ;
          p_dailyWgtIncrease(RS,"CAFR",%yr_A%) $ (%p_condition%(RS,"CAFR","LEVL",%yr_A%) $ p_fatngDays(RS,"CAFR",%yr_A%))
            = (p_startWgt("HEIF") - 150) / p_fatngDays(RS,"CAFR",%yr_A%) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a, to in (("CAMR", "BULF"), ("CAFR", "HEIF")):
            if st.LEVL(r, a) and st.p_fatngDays.get((r, a)):
                st.p_dailyWgtIncrease[(r, a)] = (st.p_startWgt[to] - 150) / st.p_fatngDays[(r, a)]


def p_meanLiveWgt_CALR_last(st: ManState) -> None:
    r"""Raised calves, the last phase: the mean live weight, 150 kg plus half the phase's gain.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 664-668):

        * --- average live weight

          p_meanLiveWgt(RS,CALR,%yr_A%) $ %p_condition%(RS,CALR,"LEVL",%yr_A%)
        *             increase up to mid point of raising period:
            = 150. + (p_dailyWgtIncrease(RS,CALR,%yr_A%) * p_fatngDays(RS,CALR,%yr_A%)) / 2. ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            if st.LEVL(r, a):
                st.p_meanLiveWgt[(r, a)] = 150. + (st.p_dailyWgtIncrease.get((r, a), 0.0) * st.p_fatngDays[(r, a)]) / 2.


def p_dataCopy_curRows_CALR_last(st: ManState) -> None:
    r"""Raised calves, the last phase: P2O5 and K2O at the tail, added to the first two phases'.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 670-675):

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
                    p_dataCopy(RS,CALR,curRows,%yr%)  $ p_dataCopy(RS,CALR,"LEVL",%yr%)
                      =  p_dataCopy(RS,CALR,curRows,%yr%)
                       + p_NutContManureKgM3("CATTLE",curRows) * p_fatngDays(RS,CALR,%yr_A%) * p_meanLiveWgt(RS,CALR,%yr_A%);
        $endif

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            if st.LEVL(r, a):
                for row in curRows:
                    st.p_dataCopy[(r, a, row)] = (st.dc(r, a, row) + st.p_NutContManureKgM3[("CATTLE", row)]
                                                  * st.p_fatngDays[(r, a)] * st.p_meanLiveWgt[(r, a)])


def p_crprReq_CALR_last(st: ManState) -> None:
    r"""Raised calves, the last phase: the crude-protein requirement, added to the first two phases'.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 677-682):

        * --- ... and nitrogen (copied below to CRPR if needed)
        *
          p_crprReq(RS,CALR,A,%yr%) $ (p_dataCopy(RS,CALR,"LEVL",%yr%)*p_technFact(RS,CALR,"LEVL",A) )
            =  p_crprReq(RS,CALR,A,%yr%)
             + (  0.00109 * p_meanLiveWgt(RS,CALR,%yr_A%)
                + 0.00022 * p_dailyWgtIncrease(RS,CALR,%yr_A%) * 1000. + 0.2027 )  * p_fatngDays(RS,CALR,%yr_A%)  ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            if st.LEVL(r, a):
                for t in st.techs(r, a):
                    st.p_crprReq[(r, a, t)] = st.p_crprReq.get((r, a, t), 0.0) + _crpr_growth_gt150(
                        st.p_meanLiveWgt[(r, a)], st.p_dailyWgtIncrease.get((r, a), 0.0), st.p_fatngDays[(r, a)])
