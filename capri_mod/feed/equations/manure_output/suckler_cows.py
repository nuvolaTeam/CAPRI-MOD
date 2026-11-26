r"""The suckler cows' rows and the females' weight (feed/req_or_man_fnc.gms, 'man' mode; moved from
capri_mod/feed/equations/req_or_man_fnc.py as they were, 26 November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.data.definitions import capri_set
from capri_mod.feed.equations.manure_output.state import DCOW, ManState, curRows  # noqa: E402




# ------------------------------------------------------------------ (2) suckler cows
def p_dataCopy_curRows_SCOW(st: ManState) -> None:
    r"""The suckler cows' P2O5 and K2O at the tail: an amount per kg of milk fed plus the manure of a 550 kg cow.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 242-245):

        $iftheni.req4 not %req% ==on
                    p_dataCopy(RS,"SCOW",curRows,%yr%) $ p_dataCopy(RS,"SCOW","LEVL",%yr%) =     p_dataCopy(RS,"SCOW","COMF",%yr%) * p_addExcrPerkgMilk(curRows)
                                                                               + p_NutContManureKgM3("CATTLE",curRows) * 365. * 550.;
        $endif.req4

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SCOW"):
            for row in curRows:
                st.p_dataCopy[(r, "SCOW", row)] = (st.dc(r, "SCOW", "COMF") * st.p_addExcrPerkgMilk[row]
                                                   + st.p_NutContManureKgM3[("CATTLE", row)] * 365. * 550.)


def p_meanLiveWgt_SCOW(st: ManState) -> None:
    r"""The suckler cows' mean live weight, 550 kg.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 249):

          p_meanLiveWgt(RS,"SCOW",%yr_A%)  $ %p_condition%(RS,"SCOW","LEVL",%yr_A%) = 550.0 ;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SCOW"):
            st.p_meanLiveWgt[(r, "SCOW")] = 550.0


def p_milkPerDay_SCOW(st: ManState) -> None:
    r"""The suckler cows' milk per lactation day ('man' mode: the data's milk fed over 125 days).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 254-259):

          p_milkPerDay(RS,"SCOW",%yr_A% %addtimedim%) $ %p_condition%(RS,"SCOW","LEVL",%yr_A%)
        $iftheni.perday1 %req% ==on
                      = p_dataCopy(RS,"SCOW","COMF",%yr%)*(p_technFact(RS,"SCOW","COMF",A)+1.) / 125. ;
        $else.perday1
                      = p_dataCopy(RS,"SCOW","COMF",%yr%) / 125;
        $endif.perday1

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SCOW"):
            st.p_milkPerDay[(r, "SCOW")] = st.dc(r, "SCOW", "COMF") / 125


def p_crprReq_SCOW(st: ManState) -> None:
    r"""The suckler cows' crude-protein requirement per head and year: lactation (125 days), maintenance (365 days) and
    the last mating period (42 days).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 261-271):

        * --- calculation of CRPR as documented in old working paper from CAPRI 1996-1999 project
        *     NOTE: In order to share the code for calculation of N-excretions (MANN) and crude protein (CRPR) we first assign to p_crprReq
        *           and then copy in PART II to p_animReq (if needed)
        *
          p_crprReq(RS,"SCOW",A,%yr%) $ p_technFact(RS,"SCOW","LEVL",A)
        *      --- for lactation period
            =( 14. * p_milkFatCont(RS,"FATS") + 28.00 ) / 1000. * p_milkPerDay(RS,"SCOW",%yr_A% %addtimedim%) * 125.
        *      --- for maintenance (copied from HEIR)
             + (0.00127 * p_meanLiveWgt(RS,"SCOW",%yr_A%) + 0.1273 ) * 365.
        *      --- for last mating period
             + 1.300 * 42.;

    Departures from CAPRI: none."""
    for r in st.RS:
        for t in st.techs(r, "SCOW"):
            st.p_crprReq[(r, "SCOW", t)] = ((14. * st.p_milkFatCont[(r, "FATS")] + 28.00) / 1000.
                                            * st.p_milkPerDay.get((r, "SCOW"), 0.0) * 125.
                                            + (0.00127 * st.p_meanLiveWgt.get((r, "SCOW"), 0.0) + 0.1273) * 365.
                                            + 1.300 * 42.)


def p_femWgt(st: ManState) -> None:
    r"""The mean live weight of an adult female, the dairy and suckler cows' weighted by their herds (550 kg where the
    region has none).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 325-332):

        *     -- weighted average of dary cows and suckler cows
          p_femWgt(RS,%yr_A%) = 550;
          p_femWgt(RS,%yr_A%) $ (     sum(DCOW,p_dataCopy(RS,DCOW,"LEVL",%yr%)  *p_meanLiveWgt(RS,DCOW,%yr_A%))
                                  or          (p_dataCopy(RS,"SCOW","LEVL",%yr%)*p_meanLiveWgt(RS,"SCOW",%yr_A%)))
            =
                  (sum(DCOW,  p_dataCopy(RS,DCOW,"LEVL",%yr%)  *p_meanLiveWgt(RS,DCOW,%yr_A%))
                            + p_dataCopy(RS,"SCOW","LEVL",%yr%)*p_meanLiveWgt(RS,"SCOW",%yr_A%))
             /    (sum(DCOW,  p_dataCopy(RS,DCOW,"LEVL",%yr%)) + p_dataCopy(RS,"SCOW","LEVL",%yr%));

    Departures from CAPRI: none."""
    for r in st.RS:
        st.p_femWgt[r] = 550
        num = (sum(st.LEVL(r, a) * st.p_meanLiveWgt.get((r, a), 0.0) for a in DCOW)
               + st.LEVL(r, "SCOW") * st.p_meanLiveWgt.get((r, "SCOW"), 0.0))
        if sum(st.LEVL(r, a) * st.p_meanLiveWgt.get((r, a), 0.0) for a in DCOW) or \
                st.LEVL(r, "SCOW") * st.p_meanLiveWgt.get((r, "SCOW"), 0.0):
            st.p_femWgt[r] = num / (sum(st.LEVL(r, a) for a in DCOW) + st.LEVL(r, "SCOW"))
