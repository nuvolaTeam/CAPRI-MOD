r"""The laying hens' and poultry fattening's rows (feed/req_or_man_fnc.gms, 'man' mode; moved from
capri_mod/feed/equations/req_or_man_fnc.py as they were, 26 November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.data.definitions import capri_set
from capri_mod.feed.equations.manure_output.state import ManState, curRows  # noqa: E402




# ------------------------------------------------------------------ (10) hens
def p_meanLiveWgt_HENS(st: ManState) -> None:
    r"""Laying hens: the mean live weight, 1.9 kg.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1137):

          p_meanLiveWgt(RS,"HENS",%yr_A%) $ %p_condition%(RS,"HENS","LEVL",%yr_A%)  = 1.9;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "HENS"):
            st.p_meanLiveWgt[(r, "HENS")] = 1.9


def p_dataCopy_curRows_HENS(st: ManState) -> None:
    r"""Laying hens: P2O5 and K2O at the tail, per 1000 hens (CAPRI's unit of the activity).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1139-1143):

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,"HENS",curRows,%yr%) $ p_dataCopy(RS,"HENS","LEVL",%yr%)
            = p_NutContManureKgM3("POULTRY",curRows) * p_meanLiveWgt(RS,"HENS",%yr_A%) * 365. * 1000.;
        $endif

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "HENS"):
            for row in curRows:
                st.p_dataCopy[(r, "HENS", row)] = (st.p_NutContManureKgM3[("POULTRY", row)] * st.p_meanLiveWgt[(r, "HENS")]
                                                   * 365. * 1000.)


def p_crprReq_HENS(st: ManState) -> None:
    r"""Laying hens: the crude-protein requirement, maintenance and the eggs (57 g each).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1145-1148):

        * --- ... and nitrogen
        *         NOTE: This should equal:  p_animReq(RS,"HENS",A,"ENMC") / 11.1 * 0.14 ;
          p_crprReq(RS,"HENS",A,%yr%) $ (p_dataCopy(RS,"HENS","LEVL",%yr%)*p_technFact(RS,"HENS","LEVL",A))
            = ( 0.46 * p_meanLiveWgt(RS,"HENS",%yr_A%)**0.75 + 0.57 * (p_dataCopy(RS,"HENS","EGGS",%yr%)/57.)/365.)*365.*1000./11.1*0.14;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "HENS"):
            for t in st.techs(r, "HENS"):
                st.p_crprReq[(r, "HENS", t)] = ((0.46 * st.p_meanLiveWgt[(r, "HENS")] ** 0.75
                                                 + 0.57 * (st.dc(r, "HENS", "EGGS") / 57.) / 365.) * 365. * 1000. / 11.1 * 0.14)


# ------------------------------------------------------------------ (11) poultry fattening
def p_meanLiveWgt_POUF(st: ManState) -> None:
    r"""Poultry fattening: the mean live weight, half the final weight (the meat over its share), at least 250 g.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1186-1194):

          p_meanLiveWgt(RS,"POUF",%yr_A%) $ %p_condition%(RS,"POUF","LEVL",%yr_A%)
            = MAX(  p_dataCopy(RS,"POUF","POUM",%yr%)*0.001
        $iftheni %req% ==on
                  *(p_technFact(RS,"POUF","POUM",A)+1.)
        $endif
        *           average wgt = final wgt * 0.5, as iniital wgt is near zero
                  / p_carcassShare("POUF") * 0.5,
        *        ... but at least 250g
                 0.25) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "POUF"):
            st.p_meanLiveWgt[(r, "POUF")] = max(st.dc(r, "POUF", "POUM") * 0.001 / st.p_carcassShare["POUF"] * 0.5, 0.25)


def p_animProdDays_POUF(st: ManState) -> None:
    r"""Poultry fattening: the process days, the member state's, within CAPRI's limits.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1196-1200):

        *        Max days are about 150 days (turkeys including some empty days), min days are about 30 days (broilers)
          p_animProdDays(RS,"POUF",%yr_A% %addtimedim%)  $ %p_condition%(RS,"POUF","LEVL",%yr_A%)
                = MIN(p_reqfcnlim("POUF","DAYS","up"),
                      MAX(p_reqfcnlim("POUF","DAYS","lo"),
                          SUM(R_RAGG(RS,MS),p_dataCopy(MS,"POUF","DAYS",%yr%)))) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "POUF"):
            st.p_animProdDays[(r, "POUF")] = min(st.lim("POUF", "DAYS", "up"), max(st.lim("POUF", "DAYS", "lo"),
                                                                                   st.ms_sum(r, lambda m: st.dc(m, "POUF", "DAYS"))))


def p_dataCopy_curRows_POUF(st: ManState) -> None:
    r"""Poultry fattening: P2O5 and K2O at the tail, per 1000 places.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1202-1206):

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,"POUF",curRows,%yr%) $ p_dataCopy(RS,"POUF","LEVL",%yr%)
            = p_NutContManureKgM3("POULTRY",curRows) * p_animProdDays(RS,"POUF",%yr_A% %addtimedim%) * p_meanLiveWgt(RS,"POUF",%yr_A%) * 1000.;
        $endif

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "POUF"):
            for row in curRows:
                st.p_dataCopy[(r, "POUF", row)] = (st.p_NutContManureKgM3[("POULTRY", row)] * st.p_animProdDays[(r, "POUF")]
                                                   * st.p_meanLiveWgt[(r, "POUF")] * 1000.)


def p_crprReq_POUF(st: ManState) -> None:
    r"""Poultry fattening: the crude-protein requirement, the dry matter intake of the fattening times a crude-protein
    content from 23% (500 g chicks) down to 19% (1.9 kg).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1208-1217):

        * --- ... and nitrogen
        *         NOTE: This should equal:  p_animReq(RS,"POUF",A,"DRMA") * (0.23 - 0.04 * MAX(0,p_meanLiveWgt(RS,"POUF",%yr_A%)-0.50) ) / 0.87;
          p_crprReq(RS,"POUF",A,%yr%) $ (p_dataCopy(RS,"POUF","LEVL",%yr%)*p_technFact(RS,"POUF","LEVL",A))
        *         dry matter need according to paper 97-12
        *         (matches rule of thumb that intake is about twice the final weight)
            =  (1.6463 * ((p_meanLiveWgt(RS,"POUF",%yr_A%)*2.0)**1.3023) * 0.87 * 1000)
        *          ... which are finally linked to CRPR:
        *              starting with a CRPR content of 23 % for 500 gr weighting chicks, dropping to 19% for 1.9 kg final weight
        *             (replaces the assumption of 19% from paper 97-12)
             * (0.23 - 0.04 * MAX(0,p_meanLiveWgt(RS,"POUF",%yr_A%)-0.50) ) / 0.87;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "POUF"):
            w = st.p_meanLiveWgt[(r, "POUF")]
            for t in st.techs(r, "POUF"):
                st.p_crprReq[(r, "POUF", t)] = ((1.6463 * ((w * 2.0) ** 1.3023) * 0.87 * 1000)
                                                * (0.23 - 0.04 * max(0, w - 0.50)) / 0.87)
