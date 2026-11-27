r"""The dairy cows' requirements (feed/req_or_man_fnc.gms, 'req' mode; moved from
capri_mod/feed/equations/req_or_man_fnc_req.py as they were, 26 November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.feed.equations.req_or_man_fnc import (BULF, CALF, CALR, DCOW, HEIF, NRUMI, DATA_AGGR_YCOW,  # noqa: F401
                                                     p_stockingRate)
from capri_mod.data.definitions import capri_set
from capri_mod.feed.equations.requirements.state import ReqState, SUBENE, _set_req  # noqa: E402




# ------------------------------------------------------------------ (1) milk cows
def p_milkFatCont(st: ReqState) -> None:
    r"""The milk fat content, 4% in every region.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 152):

          p_milkFatCont(RS,"FATS") = 4.0;

    Departures from CAPRI: none."""
    for r in st.RS:
        st.p_milkFatCont[(r, "FATS")] = 4.0


def p_meanLiveWgt_DCOW(st: ReqState) -> None:
    r"""The dairy cows' mean live weight, 600 kg.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 156):

          p_meanLiveWgt(RS,DCOW,%yr_A%) $ %p_condition%(RS,DCOW,"LEVL",%yr_A%) = 600.0 ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in DCOW:
            for t in st.techs(r, a):
                st.p_meanLiveWgt[(r, a, t)] = 600.0


def p_animProdDays_DCOW(st: ReqState) -> None:
    r"""The dairy cows' production days, 365.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 160):

        $ifi %req% ==on  p_animProdDays(RS,DCOW,A %addtimedim%) $ p_technFact(RS,DCOW,"LEVL",A)      = 365;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in DCOW:
            for t in st.techs(r, a):
                st.p_animProdDays[(r, a, t)] = 365


def p_milkPerDay_DCOW(st: ReqState) -> None:
    r"""The dairy cows' milk per lactation day: the technology's milk sold and fed over 305 days.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 164-169):

          p_milkPerDay(RS,DCOW,%yr_A% %addtimedim%) $ %p_condition%(RS,DCOW,"LEVL",%yr_A%)


        $iftheni.perday %req% ==on
                      =  p_dataCopy(RS,DCOW,"COMI",%yr%)*(p_technFact(RS,DCOW,"COMI",A)+1.) / 305.
                       + p_dataCopy(RS,DCOW,"COMF",%yr%)*(p_technFact(RS,DCOW,"COMF",A)+1.) / 305.;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in DCOW:
            for t in st.techs(r, a):
                st.p_milkPerDay[(r, a, t)] = (st.dc(r, a, "COMI") * (st.tf(r, a, "COMI", t) + 1.) / 305.
                                              + st.dc(r, a, "COMF") * (st.tf(r, a, "COMF", t) + 1.) / 305.)


def p_crprReq_DCOW(st: ReqState) -> None:
    r"""The dairy cows' crude-protein requirement per head and year: lactation, maintenance and the dry period.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 179-185):

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
                                           * st.g(st.p_milkPerDay, r, a, t) * 305.
                                           + (117. + 0.6 * st.g(st.p_meanLiveWgt, r, a, t)) / 1000. * 365.
                                           + 1.300 * 42.)


def p_fatCorMilk_DCOW(st: ReqState) -> None:
    r"""The dairy cows' fat-corrected milk per day.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 192-193):

                    p_fatCorMilk(RS,DCOW,%yr_A% %addtimedim%) $ p_technFact(RS,DCOW,"LEVL",A)
                      = p_milkPerDay(RS,DCOW,%yr_A% %addtimedim%) * ( 0.4 + 0.15 * p_milkFatCont(RS,"FATS") );

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in DCOW:
            for t in st.techs(r, a):
                st.p_fatCorMilk[(r, a, t)] = st.g(st.p_milkPerDay, r, a, t) * (0.4 + 0.15 * st.p_milkFatCont[(r, "FATS")])


def p_animReq_DCOW_energy(st: ReqState) -> None:
    r"""The dairy cows' minimum dry matter of the lactation and their net energy for lactation, maintenance, activity
    (MITERRA's housing days and share) and pregnancy (IPCC 2006), and the total.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 197-222):

                    p_animReq(RS,DCOW,A,"DRMN" %addtimedim%) $ p_technFact(RS,DCOW,"LEVL",A)
                      = (0.0185 * p_meanLiveWgt(RS,DCOW,%yr_A%) + 0.305 * p_fatCorMilk(RS,DCOW,%yr_A% %addtimedim%)) * 305.;
        *
        *               -- net energy for lactation (from IPCC: NEl)
        *
                    p_animReq(RS,DCOW,A,"NEL" %addtimedim%)  $ p_technFact(RS,DCOW,"LEVL",A)
                      = ( 0.4  * p_milkFatCont(RS,"FATS")  + 1.47 ) * p_milkPerDay(RS,DCOW,%yr_A% %addtimedim%) * 305.;

        *               -- net energy for maintenance (from IPCC: NEm=Cfi*(Weight)**0.75, IPCC 2006)

                    p_animReq(RS,DCOW,A,"NEM" %addtimedim%)  $ p_technFact(RS,DCOW,"LEVL",A)
                      =  ( p_meanLiveWgt(RS,DCOW,%yr_A%)**0.75 * 0.386) * 365.;

        *               -- net energy for activity (from IPCC: NEa,
        *                  Ca: Stall/Pasture, shares from N2O Manure Management Miterra, IPCC 2006)

                    p_animReq(RS,DCOW,A,"NEA" %addtimedim%)  $ p_technFact(RS,DCOW,"LEVL",A)
                      =  ( p_meanLiveWgt(RS,DCOW,%yr_A%)**0.75 * 0.386)* 0.17
                       * (365-p_rcEmissions(RS,"DAICOW_L","HD"))*(1-p_rcEmissions(RS,"DAICOW_L","Et")/100);

        *               -- net energy for pregnancy (from IPCC: NEp, IPCC 2006)

                    p_animReq(RS,DCOW,A,"NEP" %addtimedim%)  $ p_technFact(RS,DCOW,"LEVL",A)
                      =  ( p_meanLiveWgt(RS,DCOW,%yr_A%)**0.75 * 0.386)* 0.10 * 365.;

                    p_animReq(RS,DCOW,A,"ENNE" %addtimedim%) $ p_technFact(RS,DCOW,"LEVL",A) = SUM(SUBENE, p_animReq(RS,DCOW,A,SUBENE %addtimedim%));

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in DCOW:
            for t in st.techs(r, a):
                w, m, fc = st.g(st.p_meanLiveWgt, r, a, t), st.g(st.p_milkPerDay, r, a, t), st.g(st.p_fatCorMilk, r, a, t)
                fat = st.p_milkFatCont[(r, "FATS")]
                _set_req(st, r, a, t, "DRMN", (0.0185 * w + 0.305 * fc) * 305.)
                _set_req(st, r, a, t, "NEL", (0.4 * fat + 1.47) * m * 305.)
                _set_req(st, r, a, t, "NEM", (w ** 0.75 * 0.386) * 365.)
                _set_req(st, r, a, t, "NEA", (w ** 0.75 * 0.386) * 0.17 * (365 - st.rc(r, "DAICOW_L", "HD"))
                         * (1 - st.rc(r, "DAICOW_L", "Et") / 100))
                _set_req(st, r, a, t, "NEP", (w ** 0.75 * 0.386) * 0.10 * 365.)
                _set_req(st, r, a, t, "ENNE", sum(st.req(r, a, t, s) for s in SUBENE))


def p_animReq_DCOW_dry_matter(st: ReqState) -> None:
    r"""The dairy cows' minimum dry matter with the dry period, the digestible fibre and the intake capacity.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 226-231):

                    p_animReq(RS,DCOW,A,"DRMN" %addtimedim%) $ p_technFact(RS,DCOW,"LEVL",A)
                      = p_animReq(RS,DCOW,A,"DRMN" %addtimedim%) + ( 0.0185 * p_meanLiveWgt(RS,DCOW,%yr_A%) ) * 60. ;
                    p_animReq(RS,DCOW,A,"FIDI" %addtimedim%) $ p_technFact(RS,DCOW,"LEVL",A)
                      = p_animReq(RS,DCOW,A,"DRMN" %addtimedim%) * (p_fatCorMilk(RS,DCOW,%yr_A% %addtimedim%)/100 - 0.29 + 43.92/ 100);
                    p_animReq(RS,DCOW,A,"FICO" %addtimedim%) $ p_technFact(RS,DCOW,"LEVL",A)
                      = p_meanLiveWgt(RS,DCOW,%yr_A%)**0.75 * 0.14 * 365. * 0.7 ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in DCOW:
            for t in st.techs(r, a):
                w, fc = st.g(st.p_meanLiveWgt, r, a, t), st.g(st.p_fatCorMilk, r, a, t)
                _set_req(st, r, a, t, "DRMN", st.req(r, a, t, "DRMN") + (0.0185 * w) * 60.)
                _set_req(st, r, a, t, "FIDI", st.req(r, a, t, "DRMN") * (fc / 100 - 0.29 + 43.92 / 100))
                _set_req(st, r, a, t, "FICO", w ** 0.75 * 0.14 * 365. * 0.7)
