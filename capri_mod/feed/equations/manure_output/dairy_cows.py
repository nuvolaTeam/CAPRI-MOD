r"""The dairy cows' rows (feed/req_or_man_fnc.gms, 'man' mode; moved from capri_mod/feed/equations/req_or_man_fnc.py as
they were, 26 November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.data.definitions import capri_set
from capri_mod.feed.equations.manure_output.state import DCOW, ManState, curRows  # noqa: E402




# ------------------------------------------------------------------ (1) milk cows
def p_dataCopy_curRows_DCOW(st: ManState) -> None:
    r"""The dairy cows' P2O5 and K2O at the tail: an amount per kg of milk (cow milk sold and fed) plus 18 m3 of manure
    a year of a 600 kg cow.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 144-148):

        $iftheni.req2 not %req% ==on
                    p_dataCopy(RS,DCOW,curRows,%yr%) $ p_dataCopy(RS,DCOW,"LEVL",%yr%)
                      = (p_dataCopy(RS,DCOW,"COMI",%yr%) + p_dataCopy(RS,DCOW,"COMF",%yr%))  * p_addExcrPerkgMilk(curRows)
                       + p_NutContManureKgM3("CATTLE",curRows) * 365. * 600.;
        $endif.req2

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in DCOW:
            if st.LEVL(r, a):
                for row in curRows:
                    st.p_dataCopy[(r, a, row)] = ((st.dc(r, a, "COMI") + st.dc(r, a, "COMF")) * st.p_addExcrPerkgMilk[row]
                                                  + st.p_NutContManureKgM3[("CATTLE", row)] * 365. * 600.)


def p_milkFatCont(st: ManState) -> None:
    r"""The milk fat content, 4% in every region.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 150-152):

        * --- default if regional milk content is not known: 4 %
        *
          p_milkFatCont(RS,"FATS") = 4.0;

    Departures from CAPRI: none."""
    for r in st.RS:
        st.p_milkFatCont[(r, "FATS")] = 4.0


def p_meanLiveWgt_DCOW(st: ManState) -> None:
    r"""The dairy cows' mean live weight, 600 kg.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 156):

          p_meanLiveWgt(RS,DCOW,%yr_A%) $ %p_condition%(RS,DCOW,"LEVL",%yr_A%) = 600.0 ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in DCOW:
            if st.LEVL(r, a):
                st.p_meanLiveWgt[(r, a)] = 600.0


def p_milkPerDay_DCOW(st: ManState) -> None:
    r"""The dairy cows' milk per lactation day ('man' mode: the data's milk sold and fed over 305 days).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 164-173):

          p_milkPerDay(RS,DCOW,%yr_A% %addtimedim%) $ %p_condition%(RS,DCOW,"LEVL",%yr_A%)


        $iftheni.perday %req% ==on
                      =  p_dataCopy(RS,DCOW,"COMI",%yr%)*(p_technFact(RS,DCOW,"COMI",A)+1.) / 305.
                       + p_dataCopy(RS,DCOW,"COMF",%yr%)*(p_technFact(RS,DCOW,"COMF",A)+1.) / 305.;
        $else.perday
                     =  p_dataCopy(RS,DCOW,"COMI",%yr%) / 305.
                      + p_dataCopy(RS,DCOW,"COMF",%yr%) / 305.;
        $endif.perday

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in DCOW:
            if st.LEVL(r, a):
                st.p_milkPerDay[(r, a)] = st.dc(r, a, "COMI") / 305. + st.dc(r, a, "COMF") / 305.


def p_crprReq_DCOW(st: ManState) -> None:
    r"""The dairy cows' crude-protein requirement per head and year: lactation (305 days), maintenance (365 days) and
    the dry period (42 days).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 175-185):

        * --- calculation of CRPR as documented in old working paper from CAPRI 1996-1999 project
        *     NOTE: In order to share the code for calulation of N-excretions (MANN) and crude protein (CRPR) we first assign to p_crprReq
        *           and then copy in PART II to p_animReq (if needed)
        *
          p_crprReq(RS,DCOW,A,%yr%) $ p_technFact(RS,DCOW,"LEVL",A)
        *     -- for lactation period
            =  ( 14. * p_milkFatCont(RS,"FATS") + 28.00 ) / 1000. * p_milkPerDay(RS,DCOW,%yr_A% %addtimedim%) * 305.
        *     -- for maintenance
             + ( 117. + 0.6 * p_meanLiveWgt(RS,DCOW,%yr_A%)  ) /1000.  * 365.
        *     -- for dry period
             + 1.300 * 42.;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in DCOW:
            for t in st.techs(r, a):
                st.p_crprReq[(r, a, t)] = ((14. * st.p_milkFatCont[(r, "FATS")] + 28.00) / 1000.
                                           * st.p_milkPerDay.get((r, a), 0.0) * 305.
                                           + (117. + 0.6 * st.p_meanLiveWgt.get((r, a), 0.0)) / 1000. * 365.
                                           + 1.300 * 42.)
