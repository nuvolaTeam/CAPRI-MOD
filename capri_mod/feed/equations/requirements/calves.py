r"""The calves' requirements: light, heavy and replacement calves (feed/req_or_man_fnc.gms, 'req' mode; moved from
capri_mod/feed/equations/req_or_man_fnc_req.py as they were, 26 November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.feed.equations.req_or_man_fnc import (BULF, CALF, CALR, DCOW, HEIF, NRUMI, DATA_AGGR_YCOW,  # noqa: F401
                                                     p_stockingRate)
from capri_mod.data.definitions import capri_set
from capri_mod.feed.equations.requirements.state import A_ALL, ReqState, SUBENE, _set_req  # noqa: E402




# ------------------------------------------------------------------ (3) fattening of calves
def _scaled_ms(st, r, a, row):
    """SUM(R_RAGG(r, MS), p_dataCopy(MS, a, row) / p_stockingRate(MS)) * p_stockingRate(r)."""
    return st.ms_sum(r, lambda m: st.dc(m, a, row) / st.p_stockingRate[m]) * st.p_stockingRate.get(r, 0.0)


def _final_CALF(st, r, a, t):
    """The fattened calf's final live weight of the technology: p_dataCopy BEEF x (p_technFact BEEF + 1) / carcass."""
    return st.dc(r, a, "BEEF") * (st.tf(r, a, "BEEF", t) + 1.) / st.p_carcassShare[a]


def p_dailyWgtIncrease_CALF(st: ReqState) -> None:
    r"""The fattened calves' daily gain (kg): the member state's scaled by the stocking rates, within CAPRI's limits.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 343-347):

          p_dailyWgtIncrease(RS,CALF,%yr_A%) $ %p_condition%(RS,CALF,"LEVL",%yr_A%)
            = MIN(p_reqfcnlim(CALF,"DAILY","up"),
                  MAX(p_reqfcnlim(CALF,"DAILY","lo"),
                  SUM(R_RAGG(RS,MS),p_dataCopy(MS,CALF,"DAILY",%yr%)/p_stockingRate(MS,%yr%))*p_stockingRate(RS,%yr%)))
             / 1000;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            for t in st.techs(r, a):
                st.p_dailyWgtIncrease[(r, a, t)] = min(st.lim(a, "DAILY", "up"), max(st.lim(a, "DAILY", "lo"),
                                                                                    _scaled_ms(st, r, a, "DAILY"))) / 1000


def p_animProdDays_CALF(st: ReqState) -> None:
    r"""The fattened calves' process length, the gain from 50 kg to the final weight at the daily gain, within
    CAPRI's limits.

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
            for t in st.techs(r, a):
                st.p_animProdDays[(r, a, t)] = min(st.lim(a, "DAYS", "up"), max(st.lim(a, "DAYS", "lo"), (
                    _final_CALF(st, r, a, t) - st.p_startWgt[a]) / st.p_dailyWgtIncrease[(r, a, t)]))


def CALF_light(st: ReqState) -> None:
    r"""(a) Light calves (final live weight up to 150 kg): the mean live weight and the fattening days (one phase).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 367-384):

          p_meanLiveWgt(RS,CALF,%yr_A%) $ ((  p_dataCopy(RS,CALF,"BEEF",%yr%)
        $iftheni.req7 %req% ==on
                                             *(p_technFact(RS,CALF,"BEEF",A)+1.)
        $endif.req7
                                             / p_carcassShare(CALF))  LE 150. )
        *                          increase up to mid point of fattening period:
            = (p_startWgt(CALF) + (p_animProdDays(RS,CALF,%yr_A% %addtimedim%) * p_dailyWgtIncrease(RS,CALF,%yr_A%)) / 2.)
            $ %p_condition%(RS,CALF,"LEVL",%yr_A%);
        *
        *         Fattening days for calculation of requirements equals total process length (only one phase considered)
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
            for t in A_ALL:
                light = _final_CALF(st, r, a, t) <= 150.
                if light:
                    st.p_meanLiveWgt[(r, a, t)] = ((st.p_startWgt[a] + (st.g(st.p_animProdDays, r, a, t)
                                                                        * st.g(st.p_dailyWgtIncrease, r, a, t)) / 2.)
                                                   if st.tf(r, a, "LEVL", t) else 0.0)
                st.p_fatngDays[(r, a, t)] = 0
                if light and st.tf(r, a, "LEVL", t):
                    st.p_fatngDays[(r, a, t)] = st.p_animProdDays[(r, a, t)]


def _crpr_lt150(w, d, n):
    """( - 0.00039 * mean live weight + 0.000628 * daily gain [g] - 0.0193 ) * days (l. 395-396, 459-460, 616-617)."""
    return (- 0.00039 * w + 0.000628 * d * 1000. - 0.0193) * n


def _crpr_gt150(w, d, n):
    """( 0.00109 * mean live weight + 0.00022 * daily gain [g] + 0.2027 ) * days (l. 532, 681-682)."""
    return (0.00109 * w + 0.00022 * d * 1000. + 0.2027) * n


def _neg(st, w, a, fem, d, n):
    """IPCC 2006's net energy for growth (eq. 10.6): 22.02 x (weight / (C x the adult female's)) ** 0.75 x the daily
    gain ** 1.097 x days, C = p_coeffEnergyForGrowth (l. 404-405, 468-469, 541-542, 625-626, 695-696, 801-802)."""
    return 22.02 * (w / (st.p_coeffEnergyForGrowth[a] * fem)) ** 0.75 * (d ** 1.097) * n


def p_crprReq_CALF_light(st: ReqState) -> None:
    r"""(a) Light calves: the crude-protein requirement.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 394-396):

          p_crprReq(RS,CALF,A,%yr%) $ (p_fatngDays(RS,CALF,%yr_A%) and p_technFact(RS,CALF,"LEVL",A))
            = ( - 0.00039 * p_meanLiveWgt(RS,CALF,%yr_A%)
                + 0.000628 * p_dailyWgtIncrease(RS,CALF,%yr_A%) * 1000. -0.0193 ) * p_fatngDays(RS,CALF,%yr_A%) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            for t in st.techs(r, a):
                if st.g(st.p_fatngDays, r, a, t):
                    st.p_crprReq[(r, a, t)] = _crpr_lt150(st.g(st.p_meanLiveWgt, r, a, t),
                                                          st.g(st.p_dailyWgtIncrease, r, a, t), st.p_fatngDays[(r, a, t)])


def p_animReq_CALF_light(st: ReqState) -> None:
    r"""(a) Light calves: the net energy for growth, maintenance and activity, the total, and the minimum dry matter.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 403-424):

          p_animReq(RS,CALF,A,"NEG" %addtimedim%)  $ p_fatngDays(RS,CALF,%yr_A%)
            = 22.02 * (p_meanLiveWgt(RS,CALF,%yr_A%) / (p_coeffEnergyForGrowth(CALF) * p_femWgt(RS,A)))**0.75
                    * (p_dailyWgtIncrease(RS,CALF,%yr_A%)**(1.097)) * p_fatngDays(RS,CALF,%yr_A%);

        *     -- net energy for maintenance (from IPCC: NEm=Cfi*(Weight)**0.75, IPCC 2006)

          p_animReq(RS,CALF,A,"NEM" %addtimedim%)  $ p_fatngDays(RS,CALF,%yr_A%)
            = ( p_meanLiveWgt(RS,CALF,%yr_A%)**0.75 * 0.322) * p_fatngDays(RS,CALF,%yr_A%);
        *
        *     -- net energy for activity (from IPCC: NEa, Ca: Stall/Pasture,
        *        shares from N2O Manure Management Miterra, IPCC 2006)
        *
          p_animReq(RS,CALF,A,"NEA" %addtimedim%)  $ p_fatngDays(RS,CALF,%yr_A%)
            =  ( p_meanLiveWgt(RS,CALF,%yr_A%)**0.75 * 0.322)* 0.17
             * (365-p_rcEmissions(RS,"OCOW_L","HD"))/365. * p_fatngDays(RS,CALF,%yr_A%);
        *
          p_animReq(RS,CALF,A,"ENNE" %addtimedim%) $ p_fatngDays(RS,CALF,%yr_A%) = SUM(SUBENE, p_animReq(RS,CALF,A,SUBENE %addtimedim%));
        *
        *     -- dry matter stuff is from CAPRI working paper 97-12

          p_animReq(RS,CALF,A,"DRMN" %addtimedim%) $ p_fatngDays(RS,CALF,%yr_A%)
            = ( 0.0271 * p_meanLiveWgt(RS,CALF,%yr_A%) - 0.433 ) * p_fatngDays(RS,CALF,%yr_A%) * 0.9 ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            for t in A_ALL:
                n = st.g(st.p_fatngDays, r, a, t)
                if not n:
                    continue
                w, d = st.g(st.p_meanLiveWgt, r, a, t), st.g(st.p_dailyWgtIncrease, r, a, t)
                _set_req(st, r, a, t, "NEG", _neg(st, w, a, st.p_femWgt[(r, t)], d, n))
                _set_req(st, r, a, t, "NEM", (w ** 0.75 * 0.322) * n)
                _set_req(st, r, a, t, "NEA", (w ** 0.75 * 0.322) * 0.17 * (365 - st.rc(r, "OCOW_L", "HD")) / 365. * n)
                _set_req(st, r, a, t, "ENNE", sum(st.req(r, a, t, s) for s in SUBENE))
                _set_req(st, r, a, t, "DRMN", (0.0271 * w - 0.433) * n * 0.9)


def CALF_heavy_b1(st: ReqState) -> None:
    r"""(b1) Heavy calves (final live weight above 150 kg), the first phase from 50 to 150 kg: mean live weight
    100 kg and the days of the 100 kg gain.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 432-448):

          p_meanLiveWgt(RS,CALF,%yr_A%)  $ ((  p_dataCopy(RS,CALF,"BEEF",%yr%)
        $iftheni.req11 %req% ==on
                                             *(p_technFact(RS,CALF,"BEEF",A)+1.)
        $endif.req11
                                             / p_carcassShare(CALF))  GT 150. )
        *     Note: 100 = (50+150)/2 = mean weight
            = 100.  $ %p_condition%(RS,CALF,"LEVL",%yr_A%);
        *
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
            for t in A_ALL:
                heavy = _final_CALF(st, r, a, t) > 150.
                if heavy:
                    st.p_meanLiveWgt[(r, a, t)] = 100. if st.tf(r, a, "LEVL", t) else 0.0
                st.p_fatngDays[(r, a, t)] = 0
                if heavy and st.tf(r, a, "LEVL", t):
                    st.p_fatngDays[(r, a, t)] = 100. / st.p_dailyWgtIncrease[(r, a, t)]


def p_crprReq_CALF_heavy_b1(st: ReqState) -> None:
    r"""(b1) Heavy calves, first phase: the crude-protein requirement.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 458-460):

          p_crprReq(RS,CALF,A,%yr%) $ (p_fatngDays(RS,CALF,%yr_A%) and p_technFact(RS,CALF,"LEVL",A))
            = ( - 0.00039 * p_meanLiveWgt(RS,CALF,%yr_A%)
                + 0.000628 * p_dailyWgtIncrease(RS,CALF,%yr_A%) * 1000. -0.0193 ) * p_fatngDays(RS,CALF,%yr_A%) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            for t in st.techs(r, a):
                if st.g(st.p_fatngDays, r, a, t):
                    st.p_crprReq[(r, a, t)] = _crpr_lt150(st.g(st.p_meanLiveWgt, r, a, t),
                                                          st.g(st.p_dailyWgtIncrease, r, a, t), st.p_fatngDays[(r, a, t)])


def p_animReq_CALF_heavy_b1(st: ReqState) -> None:
    r"""(b1) Heavy calves, first phase: the net energy for growth, maintenance and activity, the total, and the
    minimum dry matter.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 467-488):

          p_animReq(RS,CALF,A,"NEG" %addtimedim%) $ p_fatngDays(RS,CALF,%yr_A%)
            =  22.02 * (p_meanLiveWgt(RS,CALF,%yr_A%) / (p_coeffEnergyForGrowth(CALF) * p_femWgt(RS,%yr_A%)))**0.75
                     * (p_dailyWgtIncrease(RS,CALF,%yr_A%)**(1.097)) * p_fatngDays(RS,CALF,%yr_A%);

        *     -- net energy for maintenance (from IPCC: NEm=Cfi*(Weight)**0.75, IPCC 2006)
        *
          p_animReq(RS,CALF,A,"NEM" %addtimedim%) $ p_fatngDays(RS,CALF,%yr_A%)
            = ( p_meanLiveWgt(RS,CALF,%yr_A%)**0.75 * 0.322) * p_fatngDays(RS,CALF,%yr_A%);
        *
        *     -- net energy for activity (from IPCC: NEa, Ca: Stall/Pasture,
        *        shares from N2O Manure Management Miterra, IPCC 2006)
        *
          p_animReq(RS,CALF,A,"NEA" %addtimedim%) $ p_fatngDays(RS,CALF,%yr_A%)
            =  ( p_meanLiveWgt(RS,CALF,%yr_A%)**0.75 * 0.322)* 0.17
             * (365-p_rcEmissions(RS,"OCOW_L","HD"))/365. * p_fatngDays(RS,CALF,%yr_A%);
        *
          p_animReq(RS,CALF,A,"ENNE" %addtimedim%) $ p_fatngDays(RS,CALF,%yr_A%) = SUM(SUBENE, p_animReq(RS,CALF,A,SUBENE %addtimedim%));

        *     -- dry matter stuff is from CAPRI working paper 97-12

          p_animReq(RS,CALF,A,"DRMN" %addtimedim%) $ p_fatngDays(RS,CALF,%yr_A%)
            = ( 0.0271 * p_meanLiveWgt(RS,CALF,%yr_A%) - 0.433 ) * p_fatngDays(RS,CALF,%yr_A%) * 0.9 ;

    Departures from CAPRI: none."""
    p_animReq_CALF_light(st)


def CALF_heavy_b2(st: ReqState) -> None:
    r"""(b2) Heavy calves, the second phase from 150 kg to the final weight: the mean live weight and the phase's days.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 493-518):

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
        *
        * --- length of second phase
        *
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
            for t in A_ALL:
                heavy = _final_CALF(st, r, a, t) > 150.
                if heavy:
                    st.p_meanLiveWgt[(r, a, t)] = ((150. + (st.g(st.p_animProdDays, r, a, t)
                                                            * st.g(st.p_dailyWgtIncrease, r, a, t) - 100) / 2.)
                                                   if st.tf(r, a, "LEVL", t) else 0.0)
                st.p_fatngDays[(r, a, t)] = 0
                if heavy and st.tf(r, a, "LEVL", t):
                    d = st.p_dailyWgtIncrease[(r, a, t)]
                    st.p_fatngDays[(r, a, t)] = (st.p_animProdDays[(r, a, t)] * d - 100) / d


def p_crprReq_CALF_heavy_b2(st: ReqState) -> None:
    r"""(b2) Heavy calves, second phase: the crude-protein requirement, added to the first phase's.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 530-532):

          p_crprReq(RS,CALF,A,%yr%) $ (p_fatngDays(RS,CALF,%yr_A%) and p_technFact(RS,CALF,"LEVL",A))
            = p_crprReq(RS,CALF,A,%yr%)
             + ( 0.00109 * p_meanLiveWgt(RS,CALF,%yr_A%) + 0.00022 * p_dailyWgtIncrease(RS,CALF,%yr_A%) * 1000. + 0.2027 ) * p_fatngDays(RS,CALF,%yr_A%);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            for t in st.techs(r, a):
                if st.g(st.p_fatngDays, r, a, t):
                    st.p_crprReq[(r, a, t)] = st.g(st.p_crprReq, r, a, t) + _crpr_gt150(
                        st.g(st.p_meanLiveWgt, r, a, t), st.g(st.p_dailyWgtIncrease, r, a, t), st.p_fatngDays[(r, a, t)])


def p_animReq_CALF_heavy_b2(st: ReqState) -> None:
    r"""(b2) Heavy calves, second phase: the net energy for growth, maintenance and activity and the minimum dry
    matter, added to the first phase's; the total; and, for every calf, the maximum dry matter and the intake capacity.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 539-564):

          p_animReq(RS,CALF,A,"NEG" %addtimedim%)  $ p_fatngDays(RS,CALF,%yr_A%)
            =  p_animReq(RS,CALF,A,"NEG" %addtimedim%)
             + 22.02 * (p_meanLiveWgt(RS,CALF,%yr_A%) / (p_coeffEnergyForGrowth(CALF) * p_femWgt(RS,%yr_A%)))**0.75
                     * (p_dailyWgtIncrease(RS,CALF,%yr_A%)**(1.097)) * p_fatngDays(RS,CALF,%yr_A%);

        *     -- net energy for maintenance (from IPCC: NEm=Cfi*(Weight)**0.75, IPCC 2006)

          p_animReq(RS,CALF,A,"NEM" %addtimedim%)  $ p_fatngDays(RS,CALF,%yr_A%)
            = p_animReq(RS,CALF,A,"NEM" %addtimedim%) + ( p_meanLiveWgt(RS,CALF,%yr_A%)**0.75 * 0.322) * p_fatngDays(RS,CALF,%yr_A%);
        *
        *     -- net energy for activity (from IPCC: NEa, Ca: Stall/Pasture, shares from N2O Manure Management Miterra, IPCC 2006)
        *
          p_animReq(RS,CALF,A,"NEA" %addtimedim%)  $ p_fatngDays(RS,CALF,%yr_A%)
            =  p_animReq(RS,CALF,A,"NEA" %addtimedim%)
             + ( p_meanLiveWgt(RS,CALF,%yr_A%)**0.75 * 0.322)* 0.17
             * (365-p_rcEmissions(RS,"OCOW_L","HD"))/365.* p_fatngDays(RS,CALF,%yr_A%);
        *
          p_animReq(RS,CALF,A,"ENNE" %addtimedim%) $ p_fatngDays(RS,CALF,%yr_A%) = SUM(SUBENE, p_animReq(RS,CALF,A,SUBENE %addtimedim%));
        *
        *     -- dry matter stuff is from CAPRI working paper 97-12

          p_animReq(RS,CALF,A,"DRMN" %addtimedim%) $ p_fatngDays(RS,CALF,%yr_A%)
            = p_animReq(RS,CALF,A,"DRMN" %addtimedim%)
             + ( 2.433 + 0.0116 * p_meanLiveWgt(RS,CALF,%yr_A%) + 0.0002 * p_dailyWgtIncrease(RS,CALF,%yr_A%))*p_fatngDays(RS,CALF,%yr_A%)*0.9;
          p_animReq(RS,CALF,A,"DRMX" %addtimedim%)  = p_animReq(RS,CALF,A,"DRMN" %addtimedim%) * 1.5;
          p_animReq(RS,CALF,A,"FICT" %addtimedim%)  = p_animReq(RS,CALF,A,"DRMX" %addtimedim%) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            for t in A_ALL:
                n = st.g(st.p_fatngDays, r, a, t)
                if n:
                    w, d = st.g(st.p_meanLiveWgt, r, a, t), st.g(st.p_dailyWgtIncrease, r, a, t)
                    _set_req(st, r, a, t, "NEG", st.req(r, a, t, "NEG") + _neg(st, w, a, st.p_femWgt[(r, t)], d, n))
                    _set_req(st, r, a, t, "NEM", st.req(r, a, t, "NEM") + (w ** 0.75 * 0.322) * n)
                    _set_req(st, r, a, t, "NEA", st.req(r, a, t, "NEA") + (w ** 0.75 * 0.322) * 0.17
                             * (365 - st.rc(r, "OCOW_L", "HD")) / 365. * n)
                    _set_req(st, r, a, t, "ENNE", sum(st.req(r, a, t, s) for s in SUBENE))
                    _set_req(st, r, a, t, "DRMN", st.req(r, a, t, "DRMN")
                             + (2.433 + 0.0116 * w + 0.0002 * d) * n * 0.9)
            for t in A_ALL:
                if (r, a, t, "DRMN") in st.p_animReq or (r, a, t, "DRMX") in st.p_animReq:
                    _set_req(st, r, a, t, "DRMX", st.req(r, a, t, "DRMN") * 1.5)
                    _set_req(st, r, a, t, "FICT", st.req(r, a, t, "DRMX"))


# ------------------------------------------------------------------ (4) raising of calves
def CALR_weaning(st: ReqState) -> None:
    r"""Raised calves, the first 49 days (weaning): the crude protein, the net energy for lactation and the minimum
    dry matter of the milk powder.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 588-596):

          p_crprReq(RS,CALR,A,%yr%)  $ (p_dataCopy(RS,CALR,"LEVL",%yr%) * p_technFact(RS,CALR,"LEVL",A) )
            = 0.35  * 0.1 * (2.+2.+5.+6.+7.+8.+8.)/7 * 49;

        * --- next group of statements only needed for energy, dry matter etc, but not excretions
        $iftheni %req% ==on
          p_animReq(RS,CALR,A,"NEL" %addtimedim%)  $ p_technFact(RS,CALR,"LEVL",A)
            = 11.79 * 0.1 * (2.+2.+5.+6.+7.+8.+8.)/7 * 49;
          p_animReq(RS,CALR,A,"DRMN" %addtimedim%) $ p_technFact(RS,CALR,"LEVL",A)
            = 0.93  * 0.1 * (2.+2.+5.+6.+7.+8.+8.)/7 * 49;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            for t in st.techs(r, a):
                if st.dc(r, a, "LEVL"):
                    st.p_crprReq[(r, a, t)] = 0.35 * 0.1 * (2. + 2. + 5. + 6. + 7. + 8. + 8.) / 7 * 49
                _set_req(st, r, a, t, "NEL", 11.79 * 0.1 * (2. + 2. + 5. + 6. + 7. + 8. + 8.) / 7 * 49)
                _set_req(st, r, a, t, "DRMN", 0.93 * 0.1 * (2. + 2. + 5. + 6. + 7. + 8. + 8.) / 7 * 49)


def CALR_80_150(st: ReqState) -> None:
    r"""Raised calves, the next 125 days (80 to 150 kg): mean live weight, daily gain and days; the crude protein; the
    net energy for growth, maintenance and activity, the total, and the minimum dry matter added to the weaning's.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 601-645):

          p_meanLiveWgt(RS,CALR,%yr_A%)      $ %p_condition%(RS,CALR,"LEVL",%yr_A%) = ( 80. + 150.) / 2. ;
          p_dailyWgtIncrease(RS,CALR,%yr_A%) $ %p_condition%(RS,CALR,"LEVL",%yr_A%) = (150.-80.)/125.;
          p_fatngDays(RS,CALR,%yr_A%)        $ %p_condition%(RS,CALR,"LEVL",%yr_A%) = ( 150. - 80. ) / p_dailyWgtIncrease(RS,CALR,%yr_A%) ;
        *
        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,CALR,curRows,%yr%)  $ p_dataCopy(RS,CALR,"LEVL",%yr%)
            =  p_dataCopy(RS,CALR,curRows,%yr%)
             + p_NutContManureKgM3("CATTLE",curRows) * p_fatngDays(RS,CALR,%yr_A%) * p_meanLiveWgt(RS,CALR,%yr_A%);
        $endif

        * --- ... and nitrogen (copied below to CRPR if needed)
        *
           p_crprReq(RS,CALR,A,%yr%) $ (p_dataCopy(RS,CALR,"LEVL",%yr%) * p_technFact(RS,CALR,"LEVL",A) )
              =  p_crprReq(RS,CALR,A,%yr%)
               + ( - 0.00039 * p_meanLiveWgt(RS,CALR,%yr_A%)
                   + 0.000628 * p_dailyWgtIncrease(RS,CALR,%yr_A%) * 1000. - 0.0193 ) * p_fatngDays(RS,CALR,%yr_A%);
        *
        * --- next group of statements only needed for energy, dry matter etc, but not excretions
        $iftheni %req% ==on

        *               -- Calculation of Net energy for growth according to IPCC 2006 (Eq. 10.6)

                    p_animReq(RS,CALR,A,"NEG" %addtimedim%)  $ p_technFact(RS,CALR,"LEVL",A)
                      = 22.02 * (p_meanLiveWgt(RS,CALR,%yr_A%) / (p_coeffEnergyForGrowth(CALR) * p_femWgt(RS,%yr_A%)))**0.75
                              * (p_dailyWgtIncrease(RS,CALR,%yr_A%)**(1.097)) * p_fatngDays(RS,CALR,%yr_A%);

        *               -- net energy for maintenance (from IPCC: NEm=Cfi*(Weight)**0.75, IPCC 2006)
                    p_animReq(RS,CALR,A,"NEM" %addtimedim%)  $ p_technFact(RS,CALR,"LEVL",A)
                      = ( p_meanLiveWgt(RS,CALR,%yr_A%)**0.75 * 0.322) * p_fatngDays(RS,CALR,%yr_A%);

        *               -- net energy for activity (from IPCC: NEa, Ca: Stall/Pasture,
        *                                       shares from N2O Manure Management Miterra, IPCC 2006)
        *
                    p_animReq(RS,CALR,A,"NEA" %addtimedim%)  $ p_technFact(RS,CALR,"LEVL",A)
                      =  ( p_meanLiveWgt(RS,CALR,%yr_A%)**0.75 * 0.322)* 0.17
                       * (365-p_rcEmissions(RS,"OCOW_L","HD"))/365. * p_fatngDays(RS,CALR,%yr_A%);
        *
                    p_animReq(RS,CALR,A,"ENNE" %addtimedim%) $ p_technFact(RS,CALR,"LEVL",A) = SUM(SUBENE, p_animReq(RS,CALR,A,SUBENE %addtimedim%));
        *
        *               -- dry matter stuff is from CAPRI working paper 97-12

                    p_animReq(RS,CALR,A,"DRMN" %addtimedim%) $ p_technFact(RS,CALR,"LEVL",A)
                      =  p_animReq(RS,CALR,A,"DRMN" %addtimedim%)
                       + ( 0.0271 * p_meanLiveWgt(RS,CALR,%yr_A%) - 0.433 ) * p_fatngDays(RS,CALR,%yr_A%) * 0.9;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            for t in st.techs(r, a):
                st.p_meanLiveWgt[(r, a, t)] = (80. + 150.) / 2.
                st.p_dailyWgtIncrease[(r, a, t)] = (150. - 80.) / 125.
                st.p_fatngDays[(r, a, t)] = (150. - 80.) / st.p_dailyWgtIncrease[(r, a, t)]
            for t in st.techs(r, a):
                if st.dc(r, a, "LEVL"):
                    st.p_crprReq[(r, a, t)] = st.g(st.p_crprReq, r, a, t) + _crpr_lt150(
                        st.p_meanLiveWgt[(r, a, t)], st.p_dailyWgtIncrease[(r, a, t)], st.p_fatngDays[(r, a, t)])
            for t in st.techs(r, a):
                w, d, n = st.p_meanLiveWgt[(r, a, t)], st.p_dailyWgtIncrease[(r, a, t)], st.p_fatngDays[(r, a, t)]
                _set_req(st, r, a, t, "NEG", _neg(st, w, a, st.p_femWgt[(r, t)], d, n))
                _set_req(st, r, a, t, "NEM", (w ** 0.75 * 0.322) * n)
                _set_req(st, r, a, t, "NEA", (w ** 0.75 * 0.322) * 0.17 * (365 - st.rc(r, "OCOW_L", "HD")) / 365. * n)
                _set_req(st, r, a, t, "ENNE", sum(st.req(r, a, t, s) for s in SUBENE))
                _set_req(st, r, a, t, "DRMN", st.req(r, a, t, "DRMN") + (0.0271 * w - 0.433) * n * 0.9)


def CALR_last(st: ReqState) -> None:
    r"""Raised calves, the last phase (150 kg to the bulls' or heifers' start weight): its days from the member
    state's raising days scaled by the stocking rates, within CAPRI's limits; the daily gain and the mean live weight.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 654-668):

          p_fatngDays(RS,CALR,%yr_A%) $ %p_condition%(RS,CALR,"LEVL",%yr_A%)
            = MAX(p_reqfcnlim(CALR,"DAYS","lo")-49-125,
                  MIN(p_reqfcnlim(CALR,"DAYS","up")-49-125,
                  SUM(R_RAGG(RS,MS),(p_dataCopy(MS,CALR,"DAYS",%yr%)-49-125)/p_stockingRate(MS,%yr%))*p_stockingRate(RS,%yr%)));

          p_dailyWgtIncrease(RS,"CAMR",%yr_A%) $ (%p_condition%(RS,"CAMR","LEVL",%yr_A%) $ p_fatngDays(RS,"CAMR",%yr_A%))
            = (p_startWgt("BULF") - 150) / p_fatngDays(RS,"CAMR",%yr_A%) ;
          p_dailyWgtIncrease(RS,"CAFR",%yr_A%) $ (%p_condition%(RS,"CAFR","LEVL",%yr_A%) $ p_fatngDays(RS,"CAFR",%yr_A%))
            = (p_startWgt("HEIF") - 150) / p_fatngDays(RS,"CAFR",%yr_A%) ;

        * --- average live weight

          p_meanLiveWgt(RS,CALR,%yr_A%) $ %p_condition%(RS,CALR,"LEVL",%yr_A%)
        *             increase up to mid point of raising period:
            = 150. + (p_dailyWgtIncrease(RS,CALR,%yr_A%) * p_fatngDays(RS,CALR,%yr_A%)) / 2. ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            for t in st.techs(r, a):
                ms = st.ms_sum(r, lambda m: (st.dc(m, a, "DAYS") - 49 - 125) / st.p_stockingRate[m])
                st.p_fatngDays[(r, a, t)] = max(st.lim(a, "DAYS", "lo") - 49 - 125, min(
                    st.lim(a, "DAYS", "up") - 49 - 125, ms * st.p_stockingRate.get(r, 0.0)))
        for a, to in (("CAMR", "BULF"), ("CAFR", "HEIF")):
            for t in st.techs(r, a):
                if st.g(st.p_fatngDays, r, a, t):
                    st.p_dailyWgtIncrease[(r, a, t)] = (st.p_startWgt[to] - 150) / st.p_fatngDays[(r, a, t)]
        for a in CALR:
            for t in st.techs(r, a):
                st.p_meanLiveWgt[(r, a, t)] = 150. + (st.g(st.p_dailyWgtIncrease, r, a, t)
                                                      * st.g(st.p_fatngDays, r, a, t)) / 2.


def CALR_last_requirements(st: ReqState) -> None:
    r"""Raised calves, the last phase: the crude protein, the production days (the three phases), the net energy
    for growth, maintenance and activity and the minimum dry matter added to the first two phases'; the total; the
    maximum dry matter and the intake capacity.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 679-719):

          p_crprReq(RS,CALR,A,%yr%) $ (p_dataCopy(RS,CALR,"LEVL",%yr%)*p_technFact(RS,CALR,"LEVL",A) )
            =  p_crprReq(RS,CALR,A,%yr%)
             + (  0.00109 * p_meanLiveWgt(RS,CALR,%yr_A%)
                + 0.00022 * p_dailyWgtIncrease(RS,CALR,%yr_A%) * 1000. + 0.2027 )  * p_fatngDays(RS,CALR,%yr_A%)  ;
        *
        * --- next group of statements only needed for energy, dry matter etc, but not excretions
        $iftheni %req% ==on

        *     -- total production days for conversion of requirements into daily values:

          p_animProdDays(RS,CALR,%yr_A% %addtimedim%) $ p_technFact(RS,CALR,"LEVL",A) = 49. + 125 + p_fatngDays(RS,CALR,%yr_A%) ;

        *     -- Calculation of Net energy for growth according to IPCC 2006 (Eq. 10.6)

          p_animReq(RS,CALR,A,"NEG" %addtimedim%)  $ p_technFact(RS,CALR,"LEVL",A)
            =  p_animReq(RS,CALR,A,"NEG" %addtimedim%)
             + 22.02 * (p_meanLiveWgt(RS,CALR,%yr_A%) / (p_coeffEnergyForGrowth(CALR) * p_femWgt(RS,%yr_A%)))**0.75
                     * (p_dailyWgtIncrease(RS,CALR,%yr_A%)**(1.097)) * p_fatngDays(RS,CALR,%yr_A%);

        *     -- net energy for maintenance (from IPCC: NEm=Cfi*(Weight)**0.75, IPCC 2006)

          p_animReq(RS,CALR,A,"NEM" %addtimedim%)  $ p_technFact(RS,CALR,"LEVL",A)
           = p_animReq(RS,CALR,A,"NEM" %addtimedim%) + ( p_meanLiveWgt(RS,CALR,%yr_A%)**0.75 * 0.322) * p_fatngDays(RS,CALR,%yr_A%);

        *     -- net energy for activity (from IPCC: NEa, Ca: Stall/Pasture,
        *        shares from N2O Manure Management Miterra, IPCC 2006)
        *
          p_animReq(RS,CALR,A,"NEA" %addtimedim%)  $ p_technFact(RS,CALR,"LEVL",A)
            = p_animReq(RS,CALR,A,"NEA" %addtimedim%) + (p_meanLiveWgt(RS,CALR,%yr_A%)**0.75 * 0.322) * 0.17
                                         * (365-p_rcEmissions(RS,"OCOW_L","HD"))/365. * p_fatngDays(RS,CALR,%yr_A%);
        *
          p_animReq(RS,CALR,A,"ENNE" %addtimedim%) $ p_technFact(RS,CALR,"LEVL",A) = SUM(SUBENE, p_animReq(RS,CALR,A,SUBENE %addtimedim%));
        *
        *     -- dry matter stuff is from CAPRI working paper 97-12

          p_animReq(RS,CALR,A,"DRMN" %addtimedim%) $ p_technFact(RS,CALR,"LEVL",A)
            = p_animReq(RS,CALR,A,"DRMN" %addtimedim%)
             + (   2.433 + 0.0116 * p_meanLiveWgt(RS,CALR,%yr_A%)
                 + 0.0002 * p_dailyWgtIncrease(RS,CALR,%yr_A%) ) * p_fatngDays(RS,CALR,%yr_A%) * 0.9;
          p_animReq(RS,CALR,A,"DRMX" %addtimedim%) $ p_technFact(RS,CALR,"LEVL",A)= p_animReq(RS,CALR,A,"DRMN" %addtimedim%) * 1.5;
          p_animReq(RS,CALR,A,"FICT" %addtimedim%) $ p_technFact(RS,CALR,"LEVL",A)= p_animReq(RS,CALR,A,"DRMX" %addtimedim%);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            for t in st.techs(r, a):
                w, d, n = st.p_meanLiveWgt[(r, a, t)], st.g(st.p_dailyWgtIncrease, r, a, t), st.p_fatngDays[(r, a, t)]
                if st.dc(r, a, "LEVL"):
                    st.p_crprReq[(r, a, t)] = st.g(st.p_crprReq, r, a, t) + _crpr_gt150(w, d, n)
                st.p_animProdDays[(r, a, t)] = 49. + 125 + n
                _set_req(st, r, a, t, "NEG", st.req(r, a, t, "NEG") + _neg(st, w, a, st.p_femWgt[(r, t)], d, n))
                _set_req(st, r, a, t, "NEM", st.req(r, a, t, "NEM") + (w ** 0.75 * 0.322) * n)
                _set_req(st, r, a, t, "NEA", st.req(r, a, t, "NEA") + (w ** 0.75 * 0.322) * 0.17
                         * (365 - st.rc(r, "OCOW_L", "HD")) / 365. * n)
                _set_req(st, r, a, t, "ENNE", sum(st.req(r, a, t, s) for s in SUBENE))
                _set_req(st, r, a, t, "DRMN", st.req(r, a, t, "DRMN") + (2.433 + 0.0116 * w + 0.0002 * d) * n * 0.9)
                _set_req(st, r, a, t, "DRMX", st.req(r, a, t, "DRMN") * 1.5)
                _set_req(st, r, a, t, "FICT", st.req(r, a, t, "DRMX"))
