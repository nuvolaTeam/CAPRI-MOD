r"""The laying hens' and poultry fattening's requirements (feed/req_or_man_fnc.gms, 'req' mode; moved from
capri_mod/feed/equations/req_or_man_fnc_req.py as they were, 26 November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.feed.equations.req_or_man_fnc import (BULF, CALF, CALR, DCOW, HEIF, NRUMI, DATA_AGGR_YCOW,  # noqa: F401
                                                     p_stockingRate)
from capri_mod.data.definitions import capri_set
from capri_mod.feed.equations.requirements.state import ReqState, _set_req  # noqa: E402




# ------------------------------------------------------------------ (10) hens
def HENS_requirements(st: ReqState) -> None:
    r"""Laying hens (per 1000 hens): the mean live weight 1.9 kg, the crude protein, the production days, the egg
    yield per day, the metabolisable energy for chicken, the dry matter, lysine and the minimum and maximum dry matter.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1137-1175):

          p_meanLiveWgt(RS,"HENS",%yr_A%) $ %p_condition%(RS,"HENS","LEVL",%yr_A%)  = 1.9;

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,"HENS",curRows,%yr%) $ p_dataCopy(RS,"HENS","LEVL",%yr%)
            = p_NutContManureKgM3("POULTRY",curRows) * p_meanLiveWgt(RS,"HENS",%yr_A%) * 365. * 1000.;
        $endif

        * --- ... and nitrogen
        *         NOTE: This should equal:  p_animReq(RS,"HENS",A,"ENMC") / 11.1 * 0.14 ;
          p_crprReq(RS,"HENS",A,%yr%) $ (p_dataCopy(RS,"HENS","LEVL",%yr%)*p_technFact(RS,"HENS","LEVL",A))
            = ( 0.46 * p_meanLiveWgt(RS,"HENS",%yr_A%)**0.75 + 0.57 * (p_dataCopy(RS,"HENS","EGGS",%yr%)/57.)/365.)*365.*1000./11.1*0.14;
        *
        * --- next group of statements only needed for energy, dry matter etc, but not excretions
        $iftheni %req% ==on

          p_animProdDays(RS,"HENS",%yr_A% %addtimedim%) $ p_technFact(RS,"HENS","LEVL",A) = 365;

        *     -- average eggs weight (57 gr.)

          p_eggYield(RS,A) $ p_technFact(RS,"HENS","LEVL",A) = (p_dataCopy(RS,"HENS","EGGS",%yr%)*(p_technFact(RS,"HENS","EGGS",A)+1.) / 57.) / 365. ;
        *
        *     -- Requirement from Kirchgessner 7th ed, p. 453

          p_animReq(RS,"HENS",A,"ENNE" %addtimedim%) $ p_technFact(RS,"HENS","LEVL",A) = 0;
          p_animReq(RS,"HENS",A,"ENMC" %addtimedim%) $ p_technFact(RS,"HENS","LEVL",A)
             = (  0.46 * p_meanLiveWgt(RS,"HENS",%yr_A%)**0.75
        *         - 1 MJ / 100 g eqq => 0.57 MJ / 57 g egg as assumed above
                + 0.57 * p_eggYield(RS,%yr_A%)  ) * 365. * 1000. ;
        *
          p_animReq(RS,"HENS",A,"DRMA" %addtimedim%) $ p_technFact(RS,"HENS","LEVL",A) = p_animReq(RS,"HENS",A,"ENMC" %addtimedim%) / 12. ;
        *
        *     -- mg of lysine
          p_animReq(RS,"HENS",A,"LISI" %addtimedim%) $ p_technFact(RS,"HENS","LEVL",A) =
                            0.0095 * p_dataCopy(RS,"HENS","EGGS",%yr%)*(p_technFact(RS,"HENS","EGGS",A)+1.) + 60. * 1.9 ;
        *
          p_animReq(RS,"HENS",A,"DRMN" %addtimedim%) $ p_technFact(RS,"HENS","LEVL",A) = p_animReq(RS,"HENS",A,"ENMC" %addtimedim%) / 15.0 ;
        *
          p_animReq(RS,"HENS",A,"DRMX" %addtimedim%) $ p_technFact(RS,"HENS","LEVL",A) = p_animReq(RS,"HENS",A,"ENMC" %addtimedim%) /  8.0 ;

    Departures from CAPRI: none."""
    a = "HENS"
    for r in st.RS:
        for t in st.techs(r, a):
            st.p_meanLiveWgt[(r, a, t)] = 1.9
        for t in st.techs(r, a):
            w = st.p_meanLiveWgt[(r, a, t)]
            if st.dc(r, a, "LEVL"):
                st.p_crprReq[(r, a, t)] = (0.46 * w ** 0.75 + 0.57 * (st.dc(r, a, "EGGS") / 57.) / 365.) \
                    * 365. * 1000. / 11.1 * 0.14
            st.p_animProdDays[(r, a, t)] = 365
            st.p_eggYield[(r, t)] = (st.dc(r, a, "EGGS") * (st.tf(r, a, "EGGS", t) + 1.) / 57.) / 365.
            _set_req(st, r, a, t, "ENNE", 0)
            _set_req(st, r, a, t, "ENMC", (0.46 * w ** 0.75 + 0.57 * st.p_eggYield[(r, t)]) * 365. * 1000.)
            _set_req(st, r, a, t, "DRMA", st.req(r, a, t, "ENMC") / 12.)
            _set_req(st, r, a, t, "LISI", 0.0095 * st.dc(r, a, "EGGS") * (st.tf(r, a, "EGGS", t) + 1.) + 60. * 1.9)
            _set_req(st, r, a, t, "DRMN", st.req(r, a, t, "ENMC") / 15.0)
            _set_req(st, r, a, t, "DRMX", st.req(r, a, t, "ENMC") / 8.0)


# ------------------------------------------------------------------ (11) poultry fattening
def POUF_requirements(st: ReqState) -> None:
    r"""Poultry fattening (per 1000 places): the mean live weight (half the final weight, at least 250 g), the
    production days (the member state's, within CAPRI's limits), the crude protein, the dry matter, the
    metabolisable energy for chicken, lysine and the minimum and maximum dry matter.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1186-1239):

          p_meanLiveWgt(RS,"POUF",%yr_A%) $ %p_condition%(RS,"POUF","LEVL",%yr_A%)
            = MAX(  p_dataCopy(RS,"POUF","POUM",%yr%)*0.001
        $iftheni %req% ==on
                  *(p_technFact(RS,"POUF","POUM",A)+1.)
        $endif
        *           average wgt = final wgt * 0.5, as iniital wgt is near zero
                  / p_carcassShare("POUF") * 0.5,
        *        ... but at least 250g
                 0.25) ;
        *
        *        Max days are about 150 days (turkeys including some empty days), min days are about 30 days (broilers)
          p_animProdDays(RS,"POUF",%yr_A% %addtimedim%)  $ %p_condition%(RS,"POUF","LEVL",%yr_A%)
                = MIN(p_reqfcnlim("POUF","DAYS","up"),
                      MAX(p_reqfcnlim("POUF","DAYS","lo"),
                          SUM(R_RAGG(RS,MS),p_dataCopy(MS,"POUF","DAYS",%yr%)))) ;
        *
        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,"POUF",curRows,%yr%) $ p_dataCopy(RS,"POUF","LEVL",%yr%)
            = p_NutContManureKgM3("POULTRY",curRows) * p_animProdDays(RS,"POUF",%yr_A% %addtimedim%) * p_meanLiveWgt(RS,"POUF",%yr_A%) * 1000.;
        $endif

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
        *
        *
        * --- next group of statements only needed for energy, dry matter etc, but not excretions
        $iftheni %req% ==on
        *
        *     -- dry matter need according to paper 97-12
        *        (matches rule of thumb that intake is about twice the final weight)
        *
          p_animReq(RS,"POUF",A,"DRMA" %addtimedim%) $ p_technFact(RS,"POUF","LEVL",A)
            = 1.6463 * ((p_meanLiveWgt(RS,"POUF",%yr_A%)*2.0)**1.3023) * 0.87 * 1000;
        *
        *      -- assume that the energy need is covered with a mix of 80% wheat and 20% soy cake
        *         (replaces the assumption of 19% from paper 97-12)
          p_animReq(RS,"POUF",A,"ENNE" %addtimedim%) $ p_technFact(RS,"POUF","LEVL",A) = 0;
        *
          p_animReq(RS,"POUF",A,"ENMC" %addtimedim%) $ p_technFact(RS,"POUF","LEVL",A)  = p_animReq(RS,"POUF",A,"DRMA" %addtimedim%)/0.89 * 12.392;
        *
          p_animReq(RS,"POUF",A,"LISI" %addtimedim%) $ p_technFact(RS,"POUF","LEVL",A)  = p_crprReq(RS,"POUF",A,%yr%) * 0.011 ;
        *
          p_animReq(RS,"POUF",A,"DRMN" %addtimedim%) $ p_technFact(RS,"POUF","LEVL",A)  = p_animReq(RS,"POUF",A,"DRMA" %addtimedim%) * 0.8;
        *
          p_animReq(RS,"POUF",A,"DRMX" %addtimedim%) $ p_technFact(RS,"POUF","LEVL",A)  = p_animReq(RS,"POUF",A,"DRMA" %addtimedim%) * 1.2 ;

    Departures from CAPRI: none."""
    a = "POUF"
    for r in st.RS:
        for t in st.techs(r, a):
            st.p_meanLiveWgt[(r, a, t)] = max(st.dc(r, a, "POUM") * 0.001 * (st.tf(r, a, "POUM", t) + 1.)
                                              / st.p_carcassShare[a] * 0.5, 0.25)
            st.p_animProdDays[(r, a, t)] = min(st.lim(a, "DAYS", "up"), max(st.lim(a, "DAYS", "lo"),
                                                                            st.ms_sum(r, lambda m: st.dc(m, a, "DAYS"))))
        for t in st.techs(r, a):
            w = st.p_meanLiveWgt[(r, a, t)]
            if st.dc(r, a, "LEVL"):
                st.p_crprReq[(r, a, t)] = ((1.6463 * ((w * 2.0) ** 1.3023) * 0.87 * 1000)
                                           * (0.23 - 0.04 * max(0, w - 0.50)) / 0.87)
            _set_req(st, r, a, t, "DRMA", 1.6463 * ((w * 2.0) ** 1.3023) * 0.87 * 1000)
            _set_req(st, r, a, t, "ENNE", 0)
            _set_req(st, r, a, t, "ENMC", st.req(r, a, t, "DRMA") / 0.89 * 12.392)
            _set_req(st, r, a, t, "LISI", st.g(st.p_crprReq, r, a, t) * 0.011)
            _set_req(st, r, a, t, "DRMN", st.req(r, a, t, "DRMA") * 0.8)
            _set_req(st, r, a, t, "DRMX", st.req(r, a, t, "DRMA") * 1.2)
