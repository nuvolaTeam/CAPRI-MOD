r"""The bulls' and heifers' requirements (feed/req_or_man_fnc.gms, 'req' mode; moved from
capri_mod/feed/equations/req_or_man_fnc_req.py as they were, 26 November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.feed.equations.req_or_man_fnc import (BULF, CALF, CALR, DCOW, HEIF, NRUMI, DATA_AGGR_YCOW,  # noqa: F401
                                                     p_stockingRate)
from capri_mod.data.definitions import capri_set
from capri_mod.feed.equations.requirements.calves import _neg, _scaled_ms  # noqa: E402
from capri_mod.feed.equations.requirements.state import A_ALL, ReqState, SUBENE, _set_req  # noqa: E402




# ------------------------------------------------------------------ (5) beef fattening
def BULF_growth(st: ReqState) -> None:
    r"""Fattened bulls: the daily gain (the member state's scaled by the stocking rates, within CAPRI's limits, at
    most 0.4 kg plus 1.6 g per kg of final weight), the fattening days from the 335 kg start and the mean live weight.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 732-761):

          p_dailyWgtIncrease(RS,BULF,%yr_A%) $ %p_condition%(RS,BULF,"LEVL",%yr_A%)
            = MIN(p_reqfcnlim(BULF,"DAILY","up"),
                  MAX(p_reqfcnlim(BULF,"DAILY","lo"),
                      SUM(R_RAGG(RS,MS),p_dataCopy(MS,BULF,"DAILY",%yr%)/p_stockingRate(MS,%yr%))*p_stockingRate(RS,%yr%)))
             / 1000;

        * --- prevent high daily increase for beef with low final weights

          p_dailyWgtIncrease(RS,BULF,%yr_A%) $ ( %p_condition%(RS,BULF,"LEVL",%yr_A%) $ p_dataCopy(RS,BULF,"BEEF",%yr%)
                                               $ p_dailyWgtIncrease(RS,BULF,%yr_A%) )
            = MIN(p_dailyWgtIncrease(RS,BULF,%yr_A%),
        *pw       Permits 0.4+500*.0016= 1.2 kg per day at 500 kg, ie more than the old specification (=>1 kg)
        *         However the absolute upper limit has also been increased (1.4kg=>1.5kg) to reflect efficiency gains in the last decade
                  0.4 + ( p_dataCopy(RS,BULF,"BEEF",%yr%) / p_carcassShare(BULF) ) * 0.0016) ;
        *
        * --- fattening period (depending on final weight and final weight of male calves raised) and mean wgt
        *
          p_fatngDays(RS,BULF,%yr_A%) $  %p_condition%(RS,BULF,"LEVL",%yr_A%)
        *       an upper final age of 3.5 years is assumed in very extensive settings
            =  MIN(p_reqfcnlim(BULF,"DAYS","up"),
                   MAX(p_reqfcnlim(BULF,"DAYS","lo"),
                      ( p_dataCopy(RS,BULF,"BEEF",%yr%)
        $iftheni %req% ==on
                      *(p_technFact(RS,BULF,"BEEF",A)+1.)
        $endif
                      / p_carcassShare(BULF) - p_startWgt(BULF))
                      / p_dailyWgtIncrease(RS,BULF,%yr_A%) ) )  ;
        *
          p_meanLiveWgt(RS,BULF,%yr_A%)  $ %p_condition%(RS,BULF,"LEVL",%yr_A%)
            = p_startWgt(BULF) + (p_fatngDays(RS,BULF,%yr_A%) * p_dailyWgtIncrease(RS,BULF,%yr_A%)) / 2.;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in BULF:
            for t in st.techs(r, a):
                st.p_dailyWgtIncrease[(r, a, t)] = min(st.lim(a, "DAILY", "up"), max(st.lim(a, "DAILY", "lo"),
                                                                                    _scaled_ms(st, r, a, "DAILY"))) / 1000
                if st.dc(r, a, "BEEF") and st.p_dailyWgtIncrease[(r, a, t)]:
                    st.p_dailyWgtIncrease[(r, a, t)] = min(st.p_dailyWgtIncrease[(r, a, t)],
                                                           0.4 + (st.dc(r, a, "BEEF") / st.p_carcassShare[a]) * 0.0016)
            for t in st.techs(r, a):
                st.p_fatngDays[(r, a, t)] = min(st.lim(a, "DAYS", "up"), max(st.lim(a, "DAYS", "lo"), (
                    st.dc(r, a, "BEEF") * (st.tf(r, a, "BEEF", t) + 1.) / st.p_carcassShare[a] - st.p_startWgt[a])
                    / st.p_dailyWgtIncrease[(r, a, t)]))
                st.p_meanLiveWgt[(r, a, t)] = st.p_startWgt[a] + (st.p_fatngDays[(r, a, t)]
                                                                  * st.p_dailyWgtIncrease[(r, a, t)]) / 2.


def BULF_requirements(st: ReqState) -> None:
    r"""Fattened bulls: the minimum dry matter of the fattening by the daily gain's class, the crude protein, the net
    energy for growth, maintenance and activity, the total, the dry matter and intake capacity, and the production
    days (the fattening days).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 772-826):

          p_dataCopy(RS,BULF,"DRMN",%yr_A%)  $ %p_condition%(RS,BULF,"LEVL",%yr_A%)
        *
            =   ( ( ( 0.029 -  0.00001914 * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_meanLiveWgt(RS,BULF,%yr_A%))  * p_fatngDays(RS,BULF,%yr_A%) )
                $ ( p_dailyWgtIncrease(RS,BULF,%yr_A%) LE 1.1)

                + (( ( 0.028 -  0.00001678 * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_fatngDays(RS,BULF,%yr_A%))
                $ ( p_dailyWgtIncrease(RS,BULF,%yr_A%) GT 1.1 AND p_dailyWgtIncrease(RS,BULF,%yr_A%) LT 1.3)

                + (( ( 0.0288 - 0.0000231  * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_fatngDays(RS,BULF,%yr_A%) )
                $ ( p_dailyWgtIncrease(RS,BULF,%yr_A%) GE 1.3);
        *
          p_crprReq(RS,BULF,A,%yr%) $  (p_dataCopy(RS,BULF,"LEVL",%yr%)*p_technFact(RS,BULF,"LEVL",A))
        *
            =  ((( 0.1602 - 0.0001228  * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_dataCopy(RS,BULF,"DRMN",%yr_A%)))
               $ ( p_dailyWgtIncrease(RS,BULF,%yr_A%) LE 1.1)

               + ((( 0.1657 - 0.0001214  * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_dataCopy(RS,BULF,"DRMN",%yr_A%)))
               $ ( p_dailyWgtIncrease(RS,BULF,%yr_A%) GT 1.1 AND p_dailyWgtIncrease(RS,BULF,%yr_A%) LT 1.3)

               + ((( 0.1493 - 0.00004405 * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_dataCopy(RS,BULF,"DRMN",%yr_A%)))
               $ ( p_dailyWgtIncrease(RS,BULF,%yr_A%) GE 1.3);
        *
        *
        * --- next group of statements only needed for energy, dry matter etc, but not excretions
        $iftheni %req% ==on

        *     -- Calculation of Net energy for growth according to IPCC 2006 (Eq. 10.6)

          p_animReq(RS,BULF,A,"NEG" %addtimedim%)  $ p_technFact(RS,BULF,"LEVL",A)
            =  22.02 * (p_meanLiveWgt(RS,BULF,%yr_A%) / (p_coeffEnergyForGrowth(BULF) * p_femWgt(RS,%yr_A%)))**0.75
                     * (p_dailyWgtIncrease(RS,BULF,%yr_A%)**(1.097)) * p_fatngDays(RS,BULF,%yr_A%);

        *     -- net energy for maintenance (from IPCC: NEm=Cfi*(Weight)**0.75, IPCC 2006)

          p_animReq(RS,BULF,A,"NEM" %addtimedim%) $ p_technFact(RS,BULF,"LEVL",A)
           = ( p_meanLiveWgt(RS,BULF,%yr_A%)**0.75 * 0.370) * p_fatngDays(RS,BULF,%yr_A%);

        *     -- net energy for activity (from IPCC: NEa, Ca: Stall/Pasture, shares from N2O Manure Management Miterra, IPCC 2006)

          p_animReq(RS,BULF,A,"NEA" %addtimedim%)  $ p_technFact(RS,BULF,"LEVL",A)
            =  ( p_meanLiveWgt(RS,BULF,%yr_A%)**0.75 * 0.370)* 0.17
                 * (365-p_rcEmissions(RS,"OCOW_L","HD"))/365 * p_fatngDays(RS,BULF,%yr_A%);
        *
          p_animReq(RS,BULF,A,"ENNE" %addtimedim%) $ p_technFact(RS,BULF,"LEVL",A)     = SUM(SUBENE, p_animReq(RS,BULF,A,SUBENE %addtimedim%));
        *
        *     -- take mean dry matter intake from above and derive min and max

          p_animReq(RS,BULF,A,"DRMN" %addtimedim%) = p_dataCopy(RS,BULF,"DRMN",%yr_A%);
          p_animReq(RS,BULF,A,"DRMN" %addtimedim%) $ p_technFact(RS,BULF,"LEVL",A) = p_animReq(RS,BULF,A,"DRMN" %addtimedim%) * 0.8;
          p_animReq(RS,BULF,A,"DRMX" %addtimedim%) $ p_technFact(RS,BULF,"LEVL",A) = p_animReq(RS,BULF,A,"DRMN" %addtimedim%) * 1.5;
          p_animReq(RS,BULF,A,"FICT" %addtimedim%) $ p_technFact(RS,BULF,"LEVL",A) = p_animReq(RS,BULF,A,"DRMX" %addtimedim%) ;
        *
        *     -- total production days for conversion of requirements into daily values:

          p_animProdDays(RS,BULF,%yr_A% %addtimedim%) = p_fatngDays(RS,BULF,%yr_A%)      ;

    Departures from CAPRI: none."""
    drmn = {}
    for r in st.RS:
        for a in BULF:
            for t in st.techs(r, a):
                w, d, n = st.p_meanLiveWgt[(r, a, t)], st.p_dailyWgtIncrease[(r, a, t)], st.p_fatngDays[(r, a, t)]
                drmn[(r, a, t)] = ((((0.029 - 0.00001914 * w) * w) * n) * (d <= 1.1)
                                   + (((0.028 - 0.00001678 * w) * w) * n) * (1.1 < d < 1.3)
                                   + (((0.0288 - 0.0000231 * w) * w) * n) * (d >= 1.3))
                if st.dc(r, a, "LEVL"):
                    st.p_crprReq[(r, a, t)] = (((0.1602 - 0.0001228 * w) * drmn[(r, a, t)]) * (d <= 1.1)
                                               + ((0.1657 - 0.0001214 * w) * drmn[(r, a, t)]) * (1.1 < d < 1.3)
                                               + ((0.1493 - 0.00004405 * w) * drmn[(r, a, t)]) * (d >= 1.3))
                _set_req(st, r, a, t, "NEG", _neg(st, w, a, st.p_femWgt[(r, t)], d, n))
                _set_req(st, r, a, t, "NEM", (w ** 0.75 * 0.370) * n)
                _set_req(st, r, a, t, "NEA", (w ** 0.75 * 0.370) * 0.17 * (365 - st.rc(r, "OCOW_L", "HD")) / 365 * n)
                _set_req(st, r, a, t, "ENNE", sum(st.req(r, a, t, s) for s in SUBENE))
        for a in BULF:
            for t in A_ALL:
                if (r, a, t) in drmn:
                    _set_req(st, r, a, t, "DRMN", drmn[(r, a, t)])
            for t in st.techs(r, a):
                _set_req(st, r, a, t, "DRMN", st.req(r, a, t, "DRMN") * 0.8)
                _set_req(st, r, a, t, "DRMX", st.req(r, a, t, "DRMN") * 1.5)
                _set_req(st, r, a, t, "FICT", st.req(r, a, t, "DRMX"))
            for t in A_ALL:
                if (r, a, t) in st.p_fatngDays:
                    st.p_animProdDays[(r, a, t)] = st.p_fatngDays[(r, a, t)]


# ------------------------------------------------------------------ (6) heifers fattening
def HEIF_growth(st: ReqState) -> None:
    r"""Fattened heifers: the daily gain, the fattening days from the 300 kg start and the mean live weight.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 835-855):

          p_dailyWgtIncrease(RS,HEIF,%yr_A%)  $ %p_condition%(RS,HEIF,"LEVL",%yr_A%)
            = MIN(p_reqfcnlim(HEIF,"DAILY","up"),
                  MAX(p_reqfcnlim(HEIF,"DAILY","lo"),
                  SUM(R_RAGG(RS,MS),p_dataCopy(MS,HEIF,"DAILY",%yr%)/p_stockingRate(MS,%yr%))*p_stockingRate(RS,%yr%)))
             / 1000;

        * --- fattening period and mean wgt
        *
          p_fatngDays(RS,HEIF,%yr_A%) $ %p_condition%(RS,HEIF,"LEVL",%yr_A%)
        *       an upper final age of 3 years is implied (otherwise: reclassification to cows)
            =  MIN(p_reqfcnlim(HEIF,"DAYS","up"),
                   MAX(p_reqfcnlim(HEIF,"DAYS","lo"),
                      ( p_dataCopy(RS,HEIF,"BEEF",%yr%)
        $iftheni %req% ==on
                      *(p_technFact(RS,HEIF,"BEEF",A)+1.)
        $endif
                      / p_carcassShare(HEIF) - p_startWgt(HEIF))
                      / p_dailyWgtIncrease(RS,HEIF,%yr_A%) ) )  ;
        *
          p_meanLiveWgt(RS,HEIF,%yr_A%) $ %p_condition%(RS,HEIF,"LEVL",%yr_A%)
            = ( p_startWgt(HEIF) + (p_fatngDays(RS,HEIF,%yr_A%) * p_dailyWgtIncrease(RS,HEIF,%yr_A%)) / 2. ) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in HEIF:
            for t in st.techs(r, a):
                st.p_dailyWgtIncrease[(r, a, t)] = min(st.lim(a, "DAILY", "up"), max(st.lim(a, "DAILY", "lo"),
                                                                                    _scaled_ms(st, r, a, "DAILY"))) / 1000
                st.p_fatngDays[(r, a, t)] = min(st.lim(a, "DAYS", "up"), max(st.lim(a, "DAYS", "lo"), (
                    st.dc(r, a, "BEEF") * (st.tf(r, a, "BEEF", t) + 1.) / st.p_carcassShare[a] - st.p_startWgt[a])
                    / st.p_dailyWgtIncrease[(r, a, t)]))
                st.p_meanLiveWgt[(r, a, t)] = (st.p_startWgt[a] + (st.p_fatngDays[(r, a, t)]
                                                                   * st.p_dailyWgtIncrease[(r, a, t)]) / 2.)


def HEIF_requirements(st: ReqState) -> None:
    r"""Fattened heifers: the minimum dry matter of the fattening, the crude protein, the net energy for growth,
    maintenance and activity, the total, the dry matter and intake capacity, and the production days.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 866-904):

          p_dataCopy(RS,HEIF,"DRMN",%yr_A%) $ %p_condition%(RS,HEIF,"LEVL",%yr_A%)
            = ( ( 0.029 - 0.00001914 * p_meanLiveWgt(RS,HEIF,%yr_A%) ) * p_meanLiveWgt(RS,HEIF,%yr_A%)) * p_fatngDays(RS,HEIF,%yr_A%);
        *
          p_crprReq(RS,HEIF,A,%yr%) $ (p_dataCopy(RS,HEIF,"LEVL",%yr%)*p_technFact(RS,HEIF,"LEVL",A))
            = ( 0.1602 - 0.0001228  * p_meanLiveWgt(RS,HEIF,%yr_A%) ) * p_dataCopy(RS,HEIF,"DRMN",%yr_A%);
        *
        * --- next group of statements only needed for energy, dry matter etc, but not excretions
        $iftheni %req% ==on

        *      -- Calculation of Net energy for growth according to IPCC 2006 (Eq. 10.6)

          p_animReq(RS,HEIF,A,"NEG" %addtimedim%)  $ p_technFact(RS,HEIF,"LEVL",A)
            =  22.02 * (p_meanLiveWgt(RS,HEIF,%yr_A%) / (p_coeffEnergyForGrowth(HEIF) * p_femWgt(RS,%yr_A%)))**0.75
                     * (p_dailyWgtIncrease(RS,HEIF,%yr_A%)**(1.097)) * p_fatngDays(RS,HEIF,%yr_A%);

        *      -- net energy for maintenance (from IPCC: NEm=Cfi*(Weight)**0.75, IPCC 2006)

          p_animReq(RS,HEIF,A,"NEM" %addtimedim%)  $ p_technFact(RS,HEIF,"LEVL",A) = ( p_meanLiveWgt(RS,HEIF,%yr_A%)**0.75 * 0.322) * p_fatngDays(RS,HEIF,%yr_A%);

        *      -- net energy for activity (from IPCC: NEa, Ca: Stall/Pasture,
        *         shares from N2O Manure Management Miterra, IPCC 2006)
        *
          p_animReq(RS,HEIF,A,"NEA" %addtimedim%)  $ p_technFact(RS,HEIF,"LEVL",A)
            =  ( p_meanLiveWgt(RS,HEIF,%yr_A%)**0.75 * 0.322)* 0.17
             * (365-p_rcEmissions(RS,"OCOW_L","HD"))/365 * p_fatngDays(RS,HEIF,%yr_A%);


          p_animReq(RS,HEIF,A,"ENNE" %addtimedim%) $ p_technFact(RS,HEIF,"LEVL",A) = SUM(SUBENE, p_animReq(RS,HEIF,A,SUBENE %addtimedim%));

        * --- take mean dry matter intake from above and derive min and max

          p_animReq(RS,HEIF,A,"DRMN" %addtimedim%) = p_dataCopy(RS,HEIF,"DRMN",%yr_A%);
          p_animReq(RS,HEIF,A,"DRMN" %addtimedim%) $ p_technFact(RS,HEIF,"LEVL",A) = p_animReq(RS,HEIF,A,"DRMN" %addtimedim%) * 0.9;
          p_animReq(RS,HEIF,A,"DRMX" %addtimedim%) $ p_technFact(RS,HEIF,"LEVL",A) = p_animReq(RS,HEIF,A,"DRMN" %addtimedim%) * 1.5;
          p_animReq(RS,HEIF,A,"FICT" %addtimedim%) $ p_technFact(RS,HEIF,"LEVL",A) = p_animReq(RS,HEIF,A,"DRMX" %addtimedim%);
        *
        * ---- total production days for conversion of requirements into daily values:

          p_animProdDays(RS,HEIF,%yr_A% %addtimedim%) = p_fatngDays(RS,HEIF,%yr_A%)      ;

    Departures from CAPRI: none."""
    drmn = {}
    for r in st.RS:
        for a in HEIF:
            for t in st.techs(r, a):
                w, d, n = st.p_meanLiveWgt[(r, a, t)], st.p_dailyWgtIncrease[(r, a, t)], st.p_fatngDays[(r, a, t)]
                drmn[(r, a, t)] = ((0.029 - 0.00001914 * w) * w) * n
                if st.dc(r, a, "LEVL"):
                    st.p_crprReq[(r, a, t)] = (0.1602 - 0.0001228 * w) * drmn[(r, a, t)]
                _set_req(st, r, a, t, "NEG", _neg(st, w, a, st.p_femWgt[(r, t)], d, n))
                _set_req(st, r, a, t, "NEM", (w ** 0.75 * 0.322) * n)
                _set_req(st, r, a, t, "NEA", (w ** 0.75 * 0.322) * 0.17 * (365 - st.rc(r, "OCOW_L", "HD")) / 365 * n)
                _set_req(st, r, a, t, "ENNE", sum(st.req(r, a, t, s) for s in SUBENE))
        for a in HEIF:
            for t in A_ALL:
                if (r, a, t) in drmn:
                    _set_req(st, r, a, t, "DRMN", drmn[(r, a, t)])
            for t in st.techs(r, a):
                _set_req(st, r, a, t, "DRMN", st.req(r, a, t, "DRMN") * 0.9)
                _set_req(st, r, a, t, "DRMX", st.req(r, a, t, "DRMN") * 1.5)
                _set_req(st, r, a, t, "FICT", st.req(r, a, t, "DRMX"))
            for t in A_ALL:
                if (r, a, t) in st.p_fatngDays:
                    st.p_animProdDays[(r, a, t)] = st.p_fatngDays[(r, a, t)]


# ------------------------------------------------------------------ (7) heifers raising
def HEIR_growth(st: ReqState) -> None:
    r"""Raised heifers: the mean live weight (halfway from 300 kg to the adult female's), the raising days (the
    member state's, within CAPRI's limits) and the daily gain.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 915-927):

          p_meanLiveWgt(RS,"HEIR",%yr_A%) $ %p_condition%(RS,"HEIR","LEVL",%yr_A%)
            = (( p_startWgt("HEIR") + p_femWgt(RS,%yr_A%) ) / 2 );
          p_meanLiveWgt(RS,"HEIR",%yr_A%) $ (%p_condition%(RS,"HEIR","LEVL",%yr_A%) $ (NOT p_meanLiveWgt(RS,"HEIR",%yr_A%)))
            = (p_startWgt("HEIR") + 575.)/2;
        *
          p_fatngDays(RS,"HEIR",%yr_A%)  $ %p_condition%(RS,"HEIR","LEVL",%yr_A%)
        *       Max days are 2 years (heifers reclassified as cows), min days are 10 months or a calving age of 12+10=22 months
            =  MIN(p_reqfcnlim("HEIR","DAYS","up"),
                   MAX(p_reqfcnlim("HEIR","DAYS","lo"),
                       SUM(R_RAGG(RS,MS),p_dataCopy(MS,"HEIR","DAYS",%yr%)))) ;
        *
          p_dailyWgtIncrease(RS,"HEIR",%yr_A%) $ p_fatngDays(RS,"HEIR",%yr_A%)
            = ( p_meanLiveWgt(RS,"HEIR",%yr_A%)  - p_startWgt("HEIR") ) / p_fatngDays(RS,"HEIR",%yr_A%);

    Departures from CAPRI: none."""
    a = "HEIR"
    for r in st.RS:
        for t in st.techs(r, a):
            st.p_meanLiveWgt[(r, a, t)] = (st.p_startWgt[a] + st.p_femWgt[(r, t)]) / 2
            if not st.p_meanLiveWgt[(r, a, t)]:
                st.p_meanLiveWgt[(r, a, t)] = (st.p_startWgt[a] + 575.) / 2
        for t in st.techs(r, a):
            st.p_fatngDays[(r, a, t)] = min(st.lim(a, "DAYS", "up"), max(st.lim(a, "DAYS", "lo"),
                                                                         st.ms_sum(r, lambda m: st.dc(m, a, "DAYS"))))
        for t in A_ALL:
            if st.g(st.p_fatngDays, r, a, t):
                st.p_dailyWgtIncrease[(r, a, t)] = ((st.g(st.p_meanLiveWgt, r, a, t) - st.p_startWgt[a])
                                                    / st.p_fatngDays[(r, a, t)])


def HEIR_requirements(st: ReqState) -> None:
    r"""Raised heifers: the crude protein, the net energy for growth (over the year), maintenance and activity, the
    total, the dry matter and intake capacity, and the production days.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 937-975):

          p_crprReq(RS,"HEIR",A,%yr%) $ (p_dataCopy(RS,"HEIR","LEVL",%yr%)*p_technFact(RS,"HEIR","LEVL",A))
            = ( 0.00127 * p_meanLiveWgt(RS,"HEIR",%yr_A%) + 0.00024 * p_dailyWgtIncrease(RS,"HEIR",%yr_A%) * 1000. + 0.1273 )
             * p_fatngDays(RS,"HEIR",%yr_A%);
        *
        *
        * --- next group of statements only needed for energy, dry matter etc, but not excretions
        $iftheni %req% ==on

        *     -- Calculation of Net energy for growth according to IPCC 2006 (Eq. 10.6)

          p_animReq(RS,"HEIR",A,"NEG" %addtimedim%)  $ p_technFact(RS,"HEIR","LEVL",A)
            =  22.02 * (p_meanLiveWgt(RS,"HEIR",%yr_A%) / (p_coeffEnergyForGrowth("HEIR") * p_femWgt(RS,%yr_A%)))**0.75
                     * (p_dailyWgtIncrease(RS,"HEIR",%yr_A%)**(1.097)) * 365.;

        *     -- net energy for maintenance (from IPCC: NEm=Cfi*(Weight)**0.75, IPCC 2006)

          p_animReq(RS,"HEIR",A,"NEM" %addtimedim%) $ p_technFact(RS,"HEIR","LEVL",A)
            = ( p_meanLiveWgt(RS,"HEIR",%yr_A%)**0.75 * 0.322) * p_fatngDays(RS,"HEIR",%yr_A%);

        *     -- net energy for activity (from IPCC: NEa, Ca: Stall/Pasture,
        *        shares from N2O Manure Management Miterra, IPCC 2006)

          p_animReq(RS,"HEIR",A,"NEA" %addtimedim%)  $ p_technFact(RS,"HEIR","LEVL",A)
            =  ( p_meanLiveWgt(RS,"HEIR",%yr_A%)**0.75 * 0.322)* 0.17
             * (365-p_rcEmissions(RS,"OCOW_L","HD"));
        *
          p_animReq(RS,"HEIR",A,"ENNE" %addtimedim%) $ p_technFact(RS,"HEIR","LEVL",A) = SUM(SUBENE, p_animReq(RS,"HEIR",A,SUBENE %addtimedim%));
        *
        *     -- dry matter stuff is from CAPRI working paper 97-12

          p_animReq(RS,"HEIR",A,"DRMN" %addtimedim%) $ p_technFact(RS,"HEIR","LEVL",A)
            = (1.7770 + 0.0167 * p_meanLiveWgt(RS,"HEIR",%yr_A%) ) * p_fatngDays(RS,"HEIR",%yr_A%);
          P_animReq(RS,"HEIR",A,"DRMN" %addtimedim%) $ p_technFact(RS,"HEIR","LEVL",A) = p_animReq(RS,"HEIR",A,"DRMN" %addtimedim%) * 0.9;
          p_animReq(RS,"HEIR",A,"DRMX" %addtimedim%) $ p_technFact(RS,"HEIR","LEVL",A) = p_animReq(RS,"HEIR",A,"DRMN" %addtimedim%) * 1.5;
          p_animReq(RS,"HEIR",A,"FICT" %addtimedim%) $ p_technFact(RS,"HEIR","LEVL",A) = p_animReq(RS,"HEIR",A,"DRMX" %addtimedim%);
        *
        * ---- total production days for conversion of requirements into daily values:

          p_animProdDays(RS,"HEIR",%yr_A% %addtimedim%) = p_fatngDays(RS,"HEIR",%yr_A%)      ;

    Departures from CAPRI: none."""
    a = "HEIR"
    for r in st.RS:
        for t in st.techs(r, a):
            w, d, n = st.p_meanLiveWgt[(r, a, t)], st.g(st.p_dailyWgtIncrease, r, a, t), st.p_fatngDays[(r, a, t)]
            if st.dc(r, a, "LEVL"):
                st.p_crprReq[(r, a, t)] = (0.00127 * w + 0.00024 * d * 1000. + 0.1273) * n
            _set_req(st, r, a, t, "NEG", _neg(st, w, a, st.p_femWgt[(r, t)], d, 365.))
            _set_req(st, r, a, t, "NEM", (w ** 0.75 * 0.322) * n)
            _set_req(st, r, a, t, "NEA", (w ** 0.75 * 0.322) * 0.17 * (365 - st.rc(r, "OCOW_L", "HD")))
            _set_req(st, r, a, t, "ENNE", sum(st.req(r, a, t, s) for s in SUBENE))
            _set_req(st, r, a, t, "DRMN", (1.7770 + 0.0167 * w) * n)
            _set_req(st, r, a, t, "DRMN", st.req(r, a, t, "DRMN") * 0.9)
            _set_req(st, r, a, t, "DRMX", st.req(r, a, t, "DRMN") * 1.5)
            _set_req(st, r, a, t, "FICT", st.req(r, a, t, "DRMX"))
        for t in A_ALL:
            if (r, a, t) in st.p_fatngDays:
                st.p_animProdDays[(r, a, t)] = st.p_fatngDays[(r, a, t)]
