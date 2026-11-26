r"""The bulls' and heifers' rows (feed/req_or_man_fnc.gms, 'man' mode; moved from
capri_mod/feed/equations/req_or_man_fnc.py as they were, 26 November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.data.definitions import capri_set
from capri_mod.feed.equations.manure_output.calves import _scaled_ms_daily  # noqa: E402
from capri_mod.feed.equations.manure_output.state import BULF, HEIF, ManState, curRows  # noqa: E402




# ------------------------------------------------------------------ (5) beef fattening
def p_dailyWgtIncrease_BULF(st: ManState) -> None:
    r"""Fattened bulls: the daily gain (kg), the member state's scaled by the region's stocking rate over the member
    state's, within CAPRI's limits; at most 0.4 kg plus 1.6 g per kg of final live weight.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 732-745):

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

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in BULF:
            if st.LEVL(r, a):
                st.p_dailyWgtIncrease[(r, a)] = min(st.lim(a, "DAILY", "up"),
                                                    max(st.lim(a, "DAILY", "lo"), _scaled_ms_daily(st, r, a))) / 1000
        for a in BULF:
            if st.LEVL(r, a) and st.dc(r, a, "BEEF") and st.p_dailyWgtIncrease.get((r, a)):
                st.p_dailyWgtIncrease[(r, a)] = min(st.p_dailyWgtIncrease[(r, a)],
                                                    0.4 + (st.dc(r, a, "BEEF") / st.p_carcassShare[a]) * 0.0016)


def p_fatngDays_BULF(st: ManState) -> None:
    r"""Fattened bulls: the fattening days, the gain from the 335 kg start to the final live weight at the daily gain,
    within CAPRI's limits.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 749-758):

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

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in BULF:
            if st.LEVL(r, a):
                st.p_fatngDays[(r, a)] = min(st.lim(a, "DAYS", "up"), max(st.lim(a, "DAYS", "lo"), (
                    st.dc(r, a, "BEEF") / st.p_carcassShare[a] - st.p_startWgt[a]) / st.p_dailyWgtIncrease[(r, a)]))


def p_meanLiveWgt_BULF(st: ManState) -> None:
    r"""Fattened bulls: the mean live weight, the start weight plus half the gain.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 760-761):

          p_meanLiveWgt(RS,BULF,%yr_A%)  $ %p_condition%(RS,BULF,"LEVL",%yr_A%)
            = p_startWgt(BULF) + (p_fatngDays(RS,BULF,%yr_A%) * p_dailyWgtIncrease(RS,BULF,%yr_A%)) / 2.;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in BULF:
            if st.LEVL(r, a):
                st.p_meanLiveWgt[(r, a)] = (st.p_startWgt[a]
                                            + (st.p_fatngDays[(r, a)] * st.p_dailyWgtIncrease[(r, a)]) / 2.)


def p_dataCopy_curRows_BULF(st: ManState) -> None:
    r"""Fattened bulls: P2O5 and K2O at the tail.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 763-767):

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,BULF,curRows,%yr%) $ p_dataCopy(RS,BULF,"LEVL",%yr%)
            = p_NutContManureKgM3("CATTLE",curRows) * p_fatngDays(RS,BULF,%yr_A%) * p_meanLiveWgt(RS,BULF,%yr_A%);
        *

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in BULF:
            if st.LEVL(r, a):
                for row in curRows:
                    st.p_dataCopy[(r, a, row)] = (st.p_NutContManureKgM3[("CATTLE", row)] * st.p_fatngDays[(r, a)]
                                                  * st.p_meanLiveWgt[(r, a)])


def p_dataCopy_DRMN_BULF(st: ManState) -> None:
    r"""Fattened bulls: the minimum dry matter of the fattening, by the daily gain's class (CAPRI working paper 97-12).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 772-781):

          p_dataCopy(RS,BULF,"DRMN",%yr_A%)  $ %p_condition%(RS,BULF,"LEVL",%yr_A%)
        *
            =   ( ( ( 0.029 -  0.00001914 * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_meanLiveWgt(RS,BULF,%yr_A%))  * p_fatngDays(RS,BULF,%yr_A%) )
                $ ( p_dailyWgtIncrease(RS,BULF,%yr_A%) LE 1.1)

                + (( ( 0.028 -  0.00001678 * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_fatngDays(RS,BULF,%yr_A%))
                $ ( p_dailyWgtIncrease(RS,BULF,%yr_A%) GT 1.1 AND p_dailyWgtIncrease(RS,BULF,%yr_A%) LT 1.3)

                + (( ( 0.0288 - 0.0000231  * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_fatngDays(RS,BULF,%yr_A%) )
                $ ( p_dailyWgtIncrease(RS,BULF,%yr_A%) GE 1.3);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in BULF:
            if st.LEVL(r, a):
                w, d, n = st.p_meanLiveWgt[(r, a)], st.p_dailyWgtIncrease[(r, a)], st.p_fatngDays[(r, a)]
                st.p_dataCopy[(r, a, "DRMN")] = (
                    (((0.029 - 0.00001914 * w) * w) * n) * (d <= 1.1)
                    + (((0.028 - 0.00001678 * w) * w) * n) * (1.1 < d < 1.3)
                    + (((0.0288 - 0.0000231 * w) * w) * n) * (d >= 1.3))


def p_crprReq_BULF(st: ManState) -> None:
    r"""Fattened bulls: the crude-protein requirement, a share of the minimum dry matter by the daily gain's class.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 783-792):

          p_crprReq(RS,BULF,A,%yr%) $  (p_dataCopy(RS,BULF,"LEVL",%yr%)*p_technFact(RS,BULF,"LEVL",A))
        *
            =  ((( 0.1602 - 0.0001228  * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_dataCopy(RS,BULF,"DRMN",%yr_A%)))
               $ ( p_dailyWgtIncrease(RS,BULF,%yr_A%) LE 1.1)

               + ((( 0.1657 - 0.0001214  * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_dataCopy(RS,BULF,"DRMN",%yr_A%)))
               $ ( p_dailyWgtIncrease(RS,BULF,%yr_A%) GT 1.1 AND p_dailyWgtIncrease(RS,BULF,%yr_A%) LT 1.3)

               + ((( 0.1493 - 0.00004405 * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_dataCopy(RS,BULF,"DRMN",%yr_A%)))
               $ ( p_dailyWgtIncrease(RS,BULF,%yr_A%) GE 1.3);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in BULF:
            if st.LEVL(r, a):
                w, d, dm = st.p_meanLiveWgt[(r, a)], st.p_dailyWgtIncrease[(r, a)], st.dc(r, a, "DRMN")
                for t in st.techs(r, a):
                    st.p_crprReq[(r, a, t)] = (((0.1602 - 0.0001228 * w) * dm) * (d <= 1.1)
                                               + ((0.1657 - 0.0001214 * w) * dm) * (1.1 < d < 1.3)
                                               + ((0.1493 - 0.00004405 * w) * dm) * (d >= 1.3))


# ------------------------------------------------------------------ (6) heifers fattening
def p_dailyWgtIncrease_HEIF(st: ManState) -> None:
    r"""Fattened heifers: the daily gain (kg), as the bulls' (without the final-weight cap).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 835-839):

          p_dailyWgtIncrease(RS,HEIF,%yr_A%)  $ %p_condition%(RS,HEIF,"LEVL",%yr_A%)
            = MIN(p_reqfcnlim(HEIF,"DAILY","up"),
                  MAX(p_reqfcnlim(HEIF,"DAILY","lo"),
                  SUM(R_RAGG(RS,MS),p_dataCopy(MS,HEIF,"DAILY",%yr%)/p_stockingRate(MS,%yr%))*p_stockingRate(RS,%yr%)))
             / 1000;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in HEIF:
            if st.LEVL(r, a):
                st.p_dailyWgtIncrease[(r, a)] = min(st.lim(a, "DAILY", "up"),
                                                    max(st.lim(a, "DAILY", "lo"), _scaled_ms_daily(st, r, a))) / 1000


def p_fatngDays_HEIF(st: ManState) -> None:
    r"""Fattened heifers: the fattening days from the 300 kg start, within CAPRI's limits.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 843-852):

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

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in HEIF:
            if st.LEVL(r, a):
                st.p_fatngDays[(r, a)] = min(st.lim(a, "DAYS", "up"), max(st.lim(a, "DAYS", "lo"), (
                    st.dc(r, a, "BEEF") / st.p_carcassShare[a] - st.p_startWgt[a]) / st.p_dailyWgtIncrease[(r, a)]))


def p_meanLiveWgt_HEIF(st: ManState) -> None:
    r"""Fattened heifers: the mean live weight.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 854-855):

          p_meanLiveWgt(RS,HEIF,%yr_A%) $ %p_condition%(RS,HEIF,"LEVL",%yr_A%)
            = ( p_startWgt(HEIF) + (p_fatngDays(RS,HEIF,%yr_A%) * p_dailyWgtIncrease(RS,HEIF,%yr_A%)) / 2. ) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in HEIF:
            if st.LEVL(r, a):
                st.p_meanLiveWgt[(r, a)] = (st.p_startWgt[a]
                                            + (st.p_fatngDays[(r, a)] * st.p_dailyWgtIncrease[(r, a)]) / 2.)


def p_dataCopy_curRows_HEIF(st: ManState) -> None:
    r"""Fattened heifers: P2O5 and K2O at the tail.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 858-862):

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,HEIF,curRows,%yr%) $ p_dataCopy(RS,HEIF,"LEVL",%yr%)
            = p_NutContManureKgM3("CATTLE",curRows) * p_fatngDays(RS,HEIF,%yr_A%) * p_meanLiveWgt(RS,HEIF,%yr_A%);
        $endif

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in HEIF:
            if st.LEVL(r, a):
                for row in curRows:
                    st.p_dataCopy[(r, a, row)] = (st.p_NutContManureKgM3[("CATTLE", row)] * st.p_fatngDays[(r, a)]
                                                  * st.p_meanLiveWgt[(r, a)])


def p_dataCopy_DRMN_HEIF(st: ManState) -> None:
    r"""Fattened heifers: the minimum dry matter of the fattening.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 866-867):

          p_dataCopy(RS,HEIF,"DRMN",%yr_A%) $ %p_condition%(RS,HEIF,"LEVL",%yr_A%)
            = ( ( 0.029 - 0.00001914 * p_meanLiveWgt(RS,HEIF,%yr_A%) ) * p_meanLiveWgt(RS,HEIF,%yr_A%)) * p_fatngDays(RS,HEIF,%yr_A%);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in HEIF:
            if st.LEVL(r, a):
                w = st.p_meanLiveWgt[(r, a)]
                st.p_dataCopy[(r, a, "DRMN")] = ((0.029 - 0.00001914 * w) * w) * st.p_fatngDays[(r, a)]


def p_crprReq_HEIF(st: ManState) -> None:
    r"""Fattened heifers: the crude-protein requirement.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 869-870):

          p_crprReq(RS,HEIF,A,%yr%) $ (p_dataCopy(RS,HEIF,"LEVL",%yr%)*p_technFact(RS,HEIF,"LEVL",A))
            = ( 0.1602 - 0.0001228  * p_meanLiveWgt(RS,HEIF,%yr_A%) ) * p_dataCopy(RS,HEIF,"DRMN",%yr_A%);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in HEIF:
            if st.LEVL(r, a):
                for t in st.techs(r, a):
                    st.p_crprReq[(r, a, t)] = (0.1602 - 0.0001228 * st.p_meanLiveWgt[(r, a)]) * st.dc(r, a, "DRMN")


# ------------------------------------------------------------------ (7) heifers raising
def p_meanLiveWgt_HEIR(st: ManState) -> None:
    r"""Raised heifers: the mean live weight, halfway from the 300 kg start to the adult female's weight.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 915-918):

          p_meanLiveWgt(RS,"HEIR",%yr_A%) $ %p_condition%(RS,"HEIR","LEVL",%yr_A%)
            = (( p_startWgt("HEIR") + p_femWgt(RS,%yr_A%) ) / 2 );
          p_meanLiveWgt(RS,"HEIR",%yr_A%) $ (%p_condition%(RS,"HEIR","LEVL",%yr_A%) $ (NOT p_meanLiveWgt(RS,"HEIR",%yr_A%)))
            = (p_startWgt("HEIR") + 575.)/2;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "HEIR"):
            st.p_meanLiveWgt[(r, "HEIR")] = ((st.p_startWgt["HEIR"] + st.p_femWgt[r]) / 2)
            if not st.p_meanLiveWgt[(r, "HEIR")]:
                st.p_meanLiveWgt[(r, "HEIR")] = (st.p_startWgt["HEIR"] + 575.) / 2


def p_fatngDays_HEIR(st: ManState) -> None:
    r"""Raised heifers: the raising days, the member state's, within CAPRI's limits.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 920-924):

          p_fatngDays(RS,"HEIR",%yr_A%)  $ %p_condition%(RS,"HEIR","LEVL",%yr_A%)
        *       Max days are 2 years (heifers reclassified as cows), min days are 10 months or a calving age of 12+10=22 months
            =  MIN(p_reqfcnlim("HEIR","DAYS","up"),
                   MAX(p_reqfcnlim("HEIR","DAYS","lo"),
                       SUM(R_RAGG(RS,MS),p_dataCopy(MS,"HEIR","DAYS",%yr%)))) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "HEIR"):
            st.p_fatngDays[(r, "HEIR")] = min(st.lim("HEIR", "DAYS", "up"), max(st.lim("HEIR", "DAYS", "lo"),
                                                                               st.ms_sum(r, lambda m: st.dc(m, "HEIR", "DAYS"))))


def p_dailyWgtIncrease_HEIR(st: ManState) -> None:
    r"""Raised heifers: the daily gain (kg), from the start to the mean weight over the raising days.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 926-927):

          p_dailyWgtIncrease(RS,"HEIR",%yr_A%) $ p_fatngDays(RS,"HEIR",%yr_A%)
            = ( p_meanLiveWgt(RS,"HEIR",%yr_A%)  - p_startWgt("HEIR") ) / p_fatngDays(RS,"HEIR",%yr_A%);

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.p_fatngDays.get((r, "HEIR")):
            st.p_dailyWgtIncrease[(r, "HEIR")] = ((st.p_meanLiveWgt.get((r, "HEIR"), 0.0) - st.p_startWgt["HEIR"])
                                                  / st.p_fatngDays[(r, "HEIR")])


def p_dataCopy_curRows_HEIR(st: ManState) -> None:
    r"""Raised heifers: P2O5 and K2O at the tail.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 929-933):

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,"HEIR",curRows,%yr%) $ p_dataCopy(RS,"HEIR","LEVL",%yr%)
            = p_NutContManureKgM3("CATTLE",curRows) * p_fatngDays(RS,"HEIR",%yr_A%) * p_meanLiveWgt(RS,"HEIR",%yr_A%);
        $endif

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "HEIR"):
            for row in curRows:
                st.p_dataCopy[(r, "HEIR", row)] = (st.p_NutContManureKgM3[("CATTLE", row)] * st.p_fatngDays[(r, "HEIR")]
                                                   * st.p_meanLiveWgt[(r, "HEIR")])


def p_crprReq_HEIR(st: ManState) -> None:
    r"""Raised heifers: the crude-protein requirement.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 935-939):

        * --- ... and nitrogen (copied below to CRPR if needed)
        *
          p_crprReq(RS,"HEIR",A,%yr%) $ (p_dataCopy(RS,"HEIR","LEVL",%yr%)*p_technFact(RS,"HEIR","LEVL",A))
            = ( 0.00127 * p_meanLiveWgt(RS,"HEIR",%yr_A%) + 0.00024 * p_dailyWgtIncrease(RS,"HEIR",%yr_A%) * 1000. + 0.1273 )
             * p_fatngDays(RS,"HEIR",%yr_A%);

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "HEIR"):
            for t in st.techs(r, "HEIR"):
                st.p_crprReq[(r, "HEIR", t)] = ((0.00127 * st.p_meanLiveWgt[(r, "HEIR")]
                                                 + 0.00024 * st.p_dailyWgtIncrease.get((r, "HEIR"), 0.0) * 1000. + 0.1273)
                                                * st.p_fatngDays[(r, "HEIR")])
