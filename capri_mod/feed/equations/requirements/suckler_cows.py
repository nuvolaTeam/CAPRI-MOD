r"""The suckler cows' requirements and the females' weight (feed/req_or_man_fnc.gms, 'req' mode; moved from
capri_mod/feed/equations/req_or_man_fnc_req.py as they were, 26 November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.feed.equations.req_or_man_fnc import (BULF, CALF, CALR, DCOW, HEIF, NRUMI, DATA_AGGR_YCOW,  # noqa: F401
                                                     p_stockingRate)
from capri_mod.data.definitions import capri_set
from capri_mod.feed.equations.requirements.state import A_ALL, ReqState, SUBENE, _set_req  # noqa: E402




# ------------------------------------------------------------------ (2) suckler cows
def p_meanLiveWgt_SCOW(st: ReqState) -> None:
    r"""The suckler cows' mean live weight, 550 kg, and production days, 365.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 249-250):

          p_meanLiveWgt(RS,"SCOW",%yr_A%)  $ %p_condition%(RS,"SCOW","LEVL",%yr_A%) = 550.0 ;
        $ifi %req% ==on  p_animProdDays(RS,"SCOW",A %addtimedim%)      $ p_technFact(RS,"SCOW","LEVL",A) = 365. ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for t in st.techs(r, "SCOW"):
            st.p_meanLiveWgt[(r, "SCOW", t)] = 550.0
            st.p_animProdDays[(r, "SCOW", t)] = 365.


def p_milkPerDay_SCOW(st: ReqState) -> None:
    r"""The suckler cows' milk per lactation day: the technology's milk fed over 125 days.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 254-256):

          p_milkPerDay(RS,"SCOW",%yr_A% %addtimedim%) $ %p_condition%(RS,"SCOW","LEVL",%yr_A%)
        $iftheni.perday1 %req% ==on
                      = p_dataCopy(RS,"SCOW","COMF",%yr%)*(p_technFact(RS,"SCOW","COMF",A)+1.) / 125. ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for t in st.techs(r, "SCOW"):
            st.p_milkPerDay[(r, "SCOW", t)] = st.dc(r, "SCOW", "COMF") * (st.tf(r, "SCOW", "COMF", t) + 1.) / 125.


def p_crprReq_SCOW(st: ReqState) -> None:
    r"""The suckler cows' crude-protein requirement per head and year.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 265-271):

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
                                            * st.g(st.p_milkPerDay, r, "SCOW", t) * 125.
                                            + (0.00127 * st.g(st.p_meanLiveWgt, r, "SCOW", t) + 0.1273) * 365.
                                            + 1.300 * 42.)


def p_animReq_SCOW(st: ReqState) -> None:
    r"""The suckler cows' fat-corrected milk, minimum dry matter, net energy for lactation, maintenance, activity
    and pregnancy (per calf born), the total, and their dry matter, digestible fibre and intake capacity.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 277-318):

                    p_fatCorMilk(RS,"SCOW",A %addtimedim%) $ p_technFact(RS,"SCOW","LEVL",A)
                      = p_milkPerDay(RS,"SCOW",%yr_A% %addtimedim%) * ( 0.4 + 0.15 * p_milkFatCont(RS,"FATS") ) ;
        *
        *               -- min. dry matter for lactation per. (CAPRI working paper 97-12)
        *
                    p_animReq(RS,"SCOW",A,"DRMN" %addtimedim%) $ p_technFact(RS,"SCOW","LEVL",A)
                      = (0.0185 * p_meanLiveWgt(RS,"SCOW",%yr_A%) + 0.305 * p_fatCorMilk(RS,"SCOW",%yr_A% %addtimedim%)) * 125.;
        *
        *               -- Net Energy calculation from IPCC
        *
                    p_animReq(RS,"SCOW",A,"NEL" %addtimedim%) $ p_technFact(RS,"SCOW","LEVL",A)
                      =  ( 0.4  * p_milkFatCont(RS,"FATS")  + 1.47 ) * p_milkPerDay(RS,"SCOW",%yr_A% %addtimedim%) * 125.;
        *
        *               -- net energy for maintenance (from IPCC: NEm=Cfi*(Weight)**0.75, IPCC 2006)
        *
                    p_animReq(RS,"SCOW",A,"NEM" %addtimedim%) $ p_technFact(RS,"SCOW","LEVL",A)
                      =  ( p_meanLiveWgt(RS,"SCOW",%yr_A%)**0.75 * 0.386) * 365.;
        *
        *               -- net energy for activity (from IPCC: NEa, Ca: Stall/Pasture,
        *                  shares from N2O Manure Management Miterra, IPCC 2006)
        *
                    p_animReq(RS,"SCOW",A,"NEA" %addtimedim%)  $ p_technFact(RS,"SCOW","LEVL",A)
                      =  ( p_meanLiveWgt(RS,"SCOW",%yr_A%)**0.75 * 0.386)* 0.17
                       * (365-p_rcEmissions(RS,"OCOW_L","HD"));
        *
        *               -- net energy for pregnancy (from IPCC: NEp, IPCC 2006)
        *
                    p_animReq(RS,"SCOW",A,"NEP" %addtimedim%) $ p_technFact(RS,"SCOW","LEVL",A)
                      =  ( p_meanLiveWgt(RS,"SCOW",%yr_A%)**0.75 * 0.386)* 0.10 * 365.
                       * (  p_dataCopy(RS,"SCOW","YCAM",%yr%)*(p_technFact(RS,"SCOW","YCAM",A)+1)
                          + p_dataCopy(RS,"SCOW","YCAF",%yr%)*(p_technFact(RS,"SCOW","YCAF",A)+1))/1000;

                    p_animReq(RS,"SCOW",A,"ENNE" %addtimedim%) $ p_technFact(RS,"SCOW","LEVL",A)  = SUM(SUBENE, p_animReq(RS,"SCOW",A,SUBENE %addtimedim%));
        *
        *               -- dry matter stuff is from CAPRI working paper 97-12

                    p_animReq(RS,"SCOW",A,"DRMN" %addtimedim%) $ p_technFact(RS,"SCOW","LEVL",A)
                      = p_animReq(RS,"SCOW",A,"DRMN" %addtimedim%) + ( 0.0185 * p_meanLiveWgt(RS,"SCOW",%yr_A%) ) * 240. ;
                    p_animReq(RS,"SCOW",A,"FIDI" %addtimedim%) $ p_technFact(RS,"SCOW","LEVL",A)
                      = p_animReq(RS,"SCOW",A,"DRMN" %addtimedim%) * (p_fatCorMilk(RS,"SCOW",%yr_A% %addtimedim%)/100 - 0.29 + 43.92/100);
                    p_animReq(RS,"SCOW",A,"FICO" %addtimedim%) $ p_technFact(RS,"SCOW","LEVL",A)
                      = p_meanLiveWgt(RS,"SCOW",%yr_A%)**0.75 * 0.14 * 365. * 0.7;

    Departures from CAPRI: none."""
    a = "SCOW"
    for r in st.RS:
        for t in st.techs(r, a):
            m, w = st.g(st.p_milkPerDay, r, a, t), st.g(st.p_meanLiveWgt, r, a, t)
            fat = st.p_milkFatCont[(r, "FATS")]
            st.p_fatCorMilk[(r, a, t)] = m * (0.4 + 0.15 * fat)
            fc = st.p_fatCorMilk[(r, a, t)]
            _set_req(st, r, a, t, "DRMN", (0.0185 * w + 0.305 * fc) * 125.)
            _set_req(st, r, a, t, "NEL", (0.4 * fat + 1.47) * m * 125.)
            _set_req(st, r, a, t, "NEM", (w ** 0.75 * 0.386) * 365.)
            _set_req(st, r, a, t, "NEA", (w ** 0.75 * 0.386) * 0.17 * (365 - st.rc(r, "OCOW_L", "HD")))
            _set_req(st, r, a, t, "NEP", (w ** 0.75 * 0.386) * 0.10 * 365.
                     * (st.dc(r, a, "YCAM") * (st.tf(r, a, "YCAM", t) + 1)
                        + st.dc(r, a, "YCAF") * (st.tf(r, a, "YCAF", t) + 1)) / 1000)
            _set_req(st, r, a, t, "ENNE", sum(st.req(r, a, t, s) for s in SUBENE))
            _set_req(st, r, a, t, "DRMN", st.req(r, a, t, "DRMN") + (0.0185 * w) * 240.)
            _set_req(st, r, a, t, "FIDI", st.req(r, a, t, "DRMN") * (fc / 100 - 0.29 + 43.92 / 100))
            _set_req(st, r, a, t, "FICO", w ** 0.75 * 0.14 * 365. * 0.7)


def p_femWgt(st: ReqState) -> None:
    r"""The mean live weight of an adult female per technology, the dairy and suckler cows' weighted by their herds
    (550 kg where the region has none).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 326-332):

          p_femWgt(RS,%yr_A%) = 550;
          p_femWgt(RS,%yr_A%) $ (     sum(DCOW,p_dataCopy(RS,DCOW,"LEVL",%yr%)  *p_meanLiveWgt(RS,DCOW,%yr_A%))
                                  or          (p_dataCopy(RS,"SCOW","LEVL",%yr%)*p_meanLiveWgt(RS,"SCOW",%yr_A%)))
            =
                  (sum(DCOW,  p_dataCopy(RS,DCOW,"LEVL",%yr%)  *p_meanLiveWgt(RS,DCOW,%yr_A%))
                            + p_dataCopy(RS,"SCOW","LEVL",%yr%)*p_meanLiveWgt(RS,"SCOW",%yr_A%))
             /    (sum(DCOW,  p_dataCopy(RS,DCOW,"LEVL",%yr%)) + p_dataCopy(RS,"SCOW","LEVL",%yr%));

    Departures from CAPRI: none."""
    for r in st.RS:
        for t in A_ALL:
            st.p_femWgt[(r, t)] = 550
            d = sum(st.dc(r, a, "LEVL") * st.g(st.p_meanLiveWgt, r, a, t) for a in DCOW)
            s = st.dc(r, "SCOW", "LEVL") * st.g(st.p_meanLiveWgt, r, "SCOW", t)
            if d or s:
                st.p_femWgt[(r, t)] = (d + s) / (sum(st.dc(r, a, "LEVL") for a in DCOW) + st.dc(r, "SCOW", "LEVL"))
