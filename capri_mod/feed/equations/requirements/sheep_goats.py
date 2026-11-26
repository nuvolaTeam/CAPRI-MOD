r"""The sheep and goats' requirements and the other animals' manure (feed/req_or_man_fnc.gms, 'req' mode; moved from
capri_mod/feed/equations/req_or_man_fnc_req.py as they were, 26 November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.feed.equations.req_or_man_fnc import (BULF, CALF, CALR, DCOW, HEIF, NRUMI, DATA_AGGR_YCOW,  # noqa: F401
                                                     p_stockingRate)
from capri_mod.data.definitions import capri_set
from capri_mod.feed.equations.requirements.state import A_ALL, REQSC, ReqState, SUBENE, _set_req  # noqa: E402




# ------------------------------------------------------------------ (12) sheep and goats for milk
def SHGM_growth(st: ReqState) -> None:
    r"""Sheep and goats for milk: the goats' share of the member state's herds, the ewes', goats' and the activity's
    mean live weights, and the milk per milking day.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1250-1272):

          p_sharGoatHerd(RS,%yr%) $ p_dataCopy(RS,"SHGM","LEVL",%yr%)
            = SUM(R_RAGG(RS,MS), p_dataCopy(MS,"GOAT","HERD",%yr%)
                               /(p_dataCopy(MS,"GOAT","HERD",%yr%)+p_dataCopy(MS,"SHEP","HERD",%yr%)))
                 $      SUM(R_RAGG(RS,MS), p_dataCopy(MS,"GOAT","HERD",%yr%)+p_dataCopy(MS,"SHEP","HERD",%yr%))
             +0.1
                 $ (NOT SUM(R_RAGG(RS,MS), p_dataCopy(MS,"GOAT","HERD",%yr%)+p_dataCopy(MS,"SHEP","HERD",%yr%)));
        *
        * --- average live weights and milk yields
        *
          p_meanLiveWgt(RS,"EWES",%yr_A%)  $ %p_condition%(RS,"SHGM","LEVL",%yr_A%) = 55. ;
          p_meanLiveWgt(RS,"GOAT",%yr_A%)  $ %p_condition%(RS,"SHGM","LEVL",%yr_A%) = 60. ;
        *
          p_meanLiveWgt(RS,"SHGM",%yr_A%)  $ %p_condition%(RS,"SHGM","LEVL",%yr_A%)
            = p_meanLiveWgt(RS,"EWES",%yr_A%) * (1-p_sharGoatHerd(RS,%yr%))
             +p_meanLiveWgt(RS,"GOAT",%yr_A%) * p_sharGoatHerd(RS,%yr%) ;
        *
        *  --- ewes milk production period is ususally 140 - 220 days. Assumed average: 170 days

           p_milkPerDay(RS,"SHGM",%yr_A% %addtimedim%)  $ %p_condition%(RS,"SHGM","LEVL",%yr_A%) =
        $ifi %req% ==on (p_technFact(RS,"SHGM","SGMI",A)+1.) *
                         p_dataCopy(RS,"SHGM","SGMI",%yr%) / 170. +
        $ifi %req% ==on (p_technFact(RS,"SHGM","SGMF",A)+1.) *
                         p_dataCopy(RS,"SHGM","SGMF",%yr%) / 170.;

    Departures from CAPRI: none."""
    a = "SHGM"
    for r in st.RS:
        if st.dc(r, a, "LEVL"):
            tot = st.ms_sum(r, lambda m: st.dc(m, "GOAT", "HERD") + st.dc(m, "SHEP", "HERD"))
            st.p_sharGoatHerd[r] = (st.ms_sum(r, lambda m: st.dc(m, "GOAT", "HERD")
                                              / (st.dc(m, "GOAT", "HERD") + st.dc(m, "SHEP", "HERD"))) if tot else 0.0) \
                + (0.1 if not tot else 0.0)
        for t in st.techs(r, a):
            s = st.g(st.p_sharGoatHerd, r)
            st.p_meanLiveWgt[(r, "EWES", t)] = 55.
            st.p_meanLiveWgt[(r, "GOAT", t)] = 60.
            st.p_meanLiveWgt[(r, a, t)] = 55. * (1 - s) + 60. * s
            st.p_milkPerDay[(r, a, t)] = ((st.tf(r, a, "SGMI", t) + 1.) * st.dc(r, a, "SGMI") / 170.
                                          + (st.tf(r, a, "SGMF", t) + 1.) * st.dc(r, a, "SGMF") / 170.)


def SHGM_crude_protein(st: ReqState) -> None:
    r"""Sheep and goats for milk: the ewes' and goats' crude-protein requirements (maintenance, milking, the last
    mating period) and the activity's, by the goats' share.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1283-1304):

          p_crprReq(RS,"EWES",A,%yr%) $ (p_dataCopy(RS,"SHGM","LEVL",%yr%)*p_technFact(RS,"SHGM","LEVL",A))
        *     -- for maintenance
            =   ( 0.026 + 0.0014 * p_meanLiveWgt(RS,"EWES",%yr_A%)) * 135.
        *     -- for milk production
              + ( 0.0634 + 0.0012 * p_meanLiveWgt(RS,"EWES",%yr_A%) + 0.0895 * p_milkPerDay(RS,"SHGM",%yr_A% %addtimedim%)) * 170.
        *     -- for last mating period
              + ( ( 2.22 * p_meanLiveWgt(RS,"EWES",%yr_A%) - 19.88) * 1.35 ) * 60. / 1000. ;
        *

          p_crprReq(RS,"GOAT",A,%yr%) $ (p_dataCopy(RS,"SHGM","LEVL",%yr%)*p_technFact(RS,"SHGM","LEVL",A))
        *     -- for maintenance
        *        NOTE: the maintenance component of phases (1) + (2) is aggregated for GOAT: 135+170=305 days
            = ( ( 12.66 + 0.8 * p_meanLiveWgt(RS,"GOAT",%yr_A%)) * 305.
        *     -- for milk production
              + ( 61. * p_milkPerDay(RS,"SHGM",%yr_A% %addtimedim%)) * 170.
        *     -- for last mating period
              + ( 1.425 * p_meanLiveWgt(RS,"GOAT",%yr_A%) + 14.666) * 60. ) / 1000. ;
        *
          p_crprReq(RS,"SHGM",A,%yr%) $ p_dataCopy(RS,"SHGM","LEVL",%yr%)
            =   (  p_crprReq(RS,"GOAT",A,%yr%) * p_sharGoatHerd(RS,%yr%)
                 + p_crprReq(RS,"EWES",A,%yr%) * (1-p_sharGoatHerd(RS,%yr%)))
                                        ;

    As GAMS's precedence reads the ewes' statement, only the last period's term is divided by 1000.
    Departures from CAPRI: none."""
    a = "SHGM"
    for r in st.RS:
        if not st.dc(r, a, "LEVL"):
            continue
        for t in st.techs(r, a):
            we, wg, m = st.p_meanLiveWgt[(r, "EWES", t)], st.p_meanLiveWgt[(r, "GOAT", t)], st.p_milkPerDay[(r, a, t)]
            st.p_crprReq[(r, "EWES", t)] = ((0.026 + 0.0014 * we) * 135.
                                            + (0.0634 + 0.0012 * we + 0.0895 * m) * 170.
                                            + ((2.22 * we - 19.88) * 1.35) * 60. / 1000.)
            st.p_crprReq[(r, "GOAT", t)] = ((12.66 + 0.8 * wg) * 305. + (61. * m) * 170.
                                            + (1.425 * wg + 14.666) * 60.) / 1000.
        s = st.g(st.p_sharGoatHerd, r)
        for t in A_ALL:
            st.p_crprReq[(r, a, t)] = (st.g(st.p_crprReq, r, "GOAT", t) * s + st.g(st.p_crprReq, r, "EWES", t) * (1 - s))


def SHGM_requirements(st: ReqState) -> None:
    r"""Sheep and goats for milk: the production days (365); the ewes' and goats' net energy for maintenance,
    activity (MITERRA's housing days) and lactation, their totals and minimum dry matter; the activity's by the goats'
    share; its maximum dry matter and intake capacity; the ewes' and goats' entries erased.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1310-1396):

                    p_animProdDays(RS,"SHGM",%yr_A% %addtimedim%) $ p_technFact(RS,"SHGM","LEVL",A) = 365;
        *
        *
        *           --- requirements for ewes

        *               -- net energy for maintenance (from IPCC: NEm=Cfi*(Weight)**0.75, IPCC 2006)
        *                  NOTE (pw121011) This was mistakenly deleted in the old trunk at some point and also neglected in the new trunk!
                    p_animReq(RS,"EWES",A,"NEM" %addtimedim%)  $ p_technFact(RS,"SHGM","LEVL",A)
                      =  ( p_meanLiveWgt(RS,"EWES",%yr_A%)**0.75 * 0.217) * p_animProdDays(RS,"SHGM",%yr_A% %addtimedim%);

        *               -- net energy for activity (from IPCC: NEa, Ca: Stall/Pasture,
        *                  shares from N2O Manure Management Miterra, IPCC 2006)
                    p_animReq(RS,"EWES",A,"NEA" %addtimedim%)  $ p_technFact(RS,"SHGM","LEVL",A)
                      =  p_meanLiveWgt(RS,"EWES",%yr_A%) * p_animProdDays(RS,"SHGM",%yr_A% %addtimedim%)
                       *   ( (365-p_rcEmissions(RS,"SHEGOA","HD"))* 0.0107
                            + p_rcEmissions(RS,"SHEGOA","HD") * 0.009)/365;

        *               -- net energy for lactation (from IPCC: NEl, EVmilk=4.6 MJ/kg) multiplied with milk production days (=170)

                    p_animReq(RS,"EWES",A,"NEL" %addtimedim%) $ p_technFact(RS,"SHGM","LEVL",A) =  ( 4.6 * p_milkPerDay(RS,"SHGM",%yr_A% %addtimedim%)) * 170.;
        *
                    p_animReq(RS,"EWES",A,"ENNE" %addtimedim%) $ p_technFact(RS,"SHGM","LEVL",A) = SUM(SUBENE, p_animReq(RS,"EWES",A,SUBENE %addtimedim%));
        *
        *               -- DRMN is added up from 3 phases: (1) only maintenance = 135 days (2) milking = 170 days (3) final mating = 60 days

                    p_animReq(RS,"EWES",A,"DRMN" %addtimedim%) $ p_technFact(RS,"SHGM","LEVL",A)
        *                  - for maintenance
                      = ( ( ( 0.36 + 0.023 * p_meanLiveWgt(RS,"EWES",%yr_A%)) * 135.
        *                  - for milk production
                        + ( 1.112 + 0.0187 * p_meanLiveWgt(RS,"EWES",%yr_A%) + 0.279 * p_milkPerDay(RS,"SHGM",%yr_A% %addtimedim%)) * 170.
        *                  - for last mating period
                        + ( 0.0268 * p_meanLiveWgt(RS,"EWES",%yr_A%) - 0.24) * 60. ) );
        *
        *
        *           --- requirements for goats
        *
        *               -- net energy for maintenance (from IPCC: NEm=Cfi*(Weight)**0.75, IPCC 2006)

                    p_animReq(RS,"GOAT",A,"NEM" %addtimedim%) $ p_technFact(RS,"SHGM","LEVL",A)
                      = ( p_meanLiveWgt(RS,"GOAT",%yr_A%)**0.75 * 0.217) * p_animProdDays(RS,"SHGM",%yr_A% %addtimedim%);

        *               -- net energy for activity (from IPCC: NEa, Ca: Stall/Pasture, shares from N2O Manure Management Miterra, IPCC 2006)

                    p_animReq(RS,"GOAT",A,"NEA" %addtimedim%)  $ p_technFact(RS,"SHGM","LEVL",A)
                       =  p_meanLiveWgt(RS,"GOAT",%yr_A%) * p_animProdDays(RS,"SHGM",%yr_A% %addtimedim%)
                        * (  (365-p_rcEmissions(RS,"SHEGOA","HD"))* 0.0107
                           + p_rcEmissions(RS,"SHEGOA","HD") * 0.009)/365;

        *               -- net energy for lactation (from IPCC: NEl, EVmilk=4.6 MJ/kg) multiplied with milk production days (=170)

                    p_animReq(RS,"GOAT",A,"NEL" %addtimedim%) $ p_technFact(RS,"SHGM","LEVL",A) =  ( 4.6 * p_milkPerDay(RS,"SHGM",%yr_A% %addtimedim%)) * 170.;
        *
                    p_animReq(RS,"GOAT",A,"ENNE" %addtimedim%) $ p_technFact(RS,"SHGM","LEVL",A) = SUM(SUBENE,p_animReq(RS,"GOAT",A,SUBENE %addtimedim%));
        *
        *               -- DRMN is added up from 3 phases: (1) only maintenance = 135 days (2) milking = 170 days (3) final mating = 60 days
        *                  NOTE: the maintenance component of phases (1) + (2) is aggregated: 135+170=305 days
        *
                    p_animReq(RS,"GOAT",A,"DRMN" %addtimedim%) $ p_technFact(RS,"SHGM","LEVL",A)
        *                  - for maintenance
                       = ( ( ( 0.55 + 0.013 * p_meanLiveWgt(RS,"GOAT",%yr_A%)) * 305.
        *                  - for milk production
                          +  0.3 * p_milkPerDay(RS,"SHGM",%yr_A% %addtimedim%) * 170.
        *                  - for last mating period
                          + ( 0.0122 * p_meanLiveWgt(RS,"GOAT",%yr_A%) + 0.5316) * 60. ) );
        *
        *
        *           --- aggregation to SHGM
        *
                    p_animReq(RS,"SHGM",A,REQSC %addtimedim%)   $ p_technFact(RS,"SHGM","LEVL",A)
                      = ( p_animReq(RS,"GOAT",A,REQSC %addtimedim%) * p_sharGoatHerd(RS,%yr%)
                       +  p_animReq(RS,"EWES",A,REQSC %addtimedim%) * (1-p_sharGoatHerd(RS,%yr%)));
        *
                    p_animReq(RS,"SHGM",A,SUBENE %addtimedim%)  $ p_technFact(RS,"SHGM","LEVL",A)
                      = ( p_animReq(RS,"GOAT",A,SUBENE %addtimedim%) * p_sharGoatHerd(RS,%yr%)
                       +  p_animReq(RS,"EWES",A,SUBENE %addtimedim%) * (1-p_sharGoatHerd(RS,%yr%)));


                    p_animReq(RS,"SHGM",A,"ENNE" %addtimedim%) $ p_technFact(RS,"SHGM","LEVL",A) = 0;
                    p_animReq(RS,"SHGM",A,"ENNE" %addtimedim%) $ p_technFact(RS,"SHGM","LEVL",A) = SUM(SUBENE, p_animReq(RS,"SHGM",A,SUBENE %addtimedim%));
        *
                    p_animReq(RS,"SHGM",A,"DRMX" %addtimedim%) $ p_technFact(RS,"SHGM","LEVL",A) = p_animReq(RS,"SHGM",A,"DRMN" %addtimedim%) * 1.5;
                    p_animReq(RS,"SHGM",A,"FISM" %addtimedim%) $ p_technFact(RS,"SHGM","LEVL",A) = ( 120. * p_meanLiveWgt(RS,"SHGM",%yr_A%) ** 0.75 ) / 1000. * 365.;
        *
                    p_animReq(RS,"GOAT",A,REQSC %addtimedim%)  = 0;
                    p_animReq(RS,"GOAT",A,SUBENE %addtimedim%) = 0;
                    p_animReq(RS,"EWES",A,REQSC %addtimedim%)  = 0;
                    p_animReq(RS,"EWES",A,SUBENE %addtimedim%) = 0;

    Departures from CAPRI: none."""
    a = "SHGM"
    for r in st.RS:
        for t in st.techs(r, a):
            st.p_animProdDays[(r, a, t)] = 365
            n, m, hd = st.p_animProdDays[(r, a, t)], st.p_milkPerDay[(r, a, t)], st.rc(r, "SHEGOA", "HD")
            for x, k in (("EWES", 0.217), ("GOAT", 0.217)):
                w = st.p_meanLiveWgt[(r, x, t)]
                _set_req(st, r, x, t, "NEM", (w ** 0.75 * k) * n)
                _set_req(st, r, x, t, "NEA", w * n * ((365 - hd) * 0.0107 + hd * 0.009) / 365)
                _set_req(st, r, x, t, "NEL", (4.6 * m) * 170.)
                _set_req(st, r, x, t, "ENNE", sum(st.req(r, x, t, s) for s in SUBENE))
            we, wg = st.p_meanLiveWgt[(r, "EWES", t)], st.p_meanLiveWgt[(r, "GOAT", t)]
            _set_req(st, r, "EWES", t, "DRMN", ((0.36 + 0.023 * we) * 135.
                                                + (1.112 + 0.0187 * we + 0.279 * m) * 170.
                                                + (0.0268 * we - 0.24) * 60.))
            _set_req(st, r, "GOAT", t, "DRMN", ((0.55 + 0.013 * wg) * 305.
                                                + 0.3 * m * 170.
                                                + (0.0122 * wg + 0.5316) * 60.))
        s = st.g(st.p_sharGoatHerd, r)
        for t in st.techs(r, a):
            for item in REQSC + SUBENE:
                g_, e_ = st.req(r, "GOAT", t, item), st.req(r, "EWES", t, item)
                if (r, "GOAT", t, item) in st.p_animReq or (r, "EWES", t, item) in st.p_animReq \
                        or (r, a, t, item) in st.p_animReq:
                    _set_req(st, r, a, t, item, g_ * s + e_ * (1 - s))
            _set_req(st, r, a, t, "ENNE", 0)
            _set_req(st, r, a, t, "ENNE", sum(st.req(r, a, t, x) for x in SUBENE))
            _set_req(st, r, a, t, "DRMX", st.req(r, a, t, "DRMN") * 1.5)
            _set_req(st, r, a, t, "FISM", (120. * st.p_meanLiveWgt[(r, a, t)] ** 0.75) / 1000. * 365.)
    for k in [k for k in st.p_animReq if k[1] in ("EWES", "GOAT")]:
        del st.p_animReq[k]


# ------------------------------------------------------------------ (13) sheep and goats fattening
def SHGF_requirements(st: ReqState) -> None:
    r"""Sheep and goats fattening: the daily gain (g, the member state's within CAPRI's limits), the fattening days,
    the mean live weight, the crude protein, the energy (from metabolisable energy for ruminants), the minimum and
    maximum dry matter, the intake capacity and the production days.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1407-1465):

          p_dailyWgtIncrease(RS,"SHGF",%yr_A%)  $ %p_condition%(RS,"SHGF","LEVL",%yr_A%)
            = MIN(p_reqfcnlim("SHGF","DAILY","up"),
                  MAX(p_reqfcnlim("SHGF","DAILY","lo"),
                      SUM(R_RAGG(RS,MS),p_dataCopy(MS,"SHGF","DAILY",%yr%)))) ;

        * --- fattening period

          p_fatngDays(RS,"SHGF",%yr_A%)  $ %p_condition%(RS,"SHGF","LEVL",%yr_A%)
            = MIN(365. , MAX(10. ,( p_dataCopy(RS,"SHGF","SGMT",%yr%)/ p_carcassShare("SHGF") )
                                 /(p_dailyWgtIncrease(RS,"SHGF",%yr_A%)/1000.))) ;

        * --- average live weight

          p_meanLiveWgt(RS,"SHGF",%yr_A%)  $ %p_condition%(RS,"SHGF","LEVL",%yr_A%)
        *    Bounds as in coco1_anim:
            = MAX(8.,MIN(25.,p_dataCopy(RS,"SHGF","SGMT",%yr%)))/p_carcassShare("SHGF")/2.;
        *
        *
        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,"SHGF",curRows,%yr%) $ p_dataCopy(RS,"SHGF","LEVL",%yr%)
            = p_NutContManureKgM3("CATTLE",curRows) * p_fatngDays(RS,"SHGF",%yr_A%) * p_meanLiveWgt(RS,"SHGF",%yr_A%);
        $endif

        * --- ... and nitrogen (copied below to CRPR if needed)
        *
          p_crprReq(RS,"SHGF",A,%yr%) $ (p_dataCopy(RS,"SHGF","LEVL",%yr%)*p_technFact(RS,"SHGF","LEVL",A))
            = ( ( 21.778 + 0.33 * p_meanLiveWgt(RS,"SHGF",%yr_A%) + 0.258 * p_dailyWgtIncrease(RS,"SHGF",%yr_A%))
               * 1.35 * p_fatngDays(RS,"SHGF",%yr_A%)) / 1000.;
        *
        *
        * --- next group of statements only needed for energy, dry matter etc, but not excretions
        $iftheni.req15 %req% ==on
        *
        *            From http://www.gumpenstein.at/viehwirt/sachver.pdf, 040106 where it is clearly indicated that this is ME
        *            (gives higher requirement than the version commented out below), converted from ME into net energy lactation
        *
                    p_animReq(RS,"SHGF",A,"ENNE" %addtimedim%) $ p_technFact(RS,"SHGF","LEVL",A) = 0;
                    p_animReq(RS,"SHGF",A,"ENNE" %addtimedim%)  $ p_technFact(RS,"SHGF","LEVL",A)
                         = (0.1596 * p_meanLiveWgt(RS,"SHGF",%yr_A%) + 0.0303 * p_dailyWgtIncrease(RS,"SHGF",%yr_A%) - 0.56)
        *                -- Assume 20% is from sucked SGMI:
                          * (1.- 0.2) * p_fatngDays(RS,"SHGF",%yr_A%) * p_convFactEnergyUnitsToEnne("ENMR");

                    p_animReq(RS,"SHGF",A,"DRMN" %addtimedim%) $ p_technFact(RS,"SHGF","LEVL",A)
                      = (0.038286 * p_meanLiveWgt(RS,"SHGF",%yr_A%) + 0.06381) * p_fatngDays(RS,"SHGF",%yr_A%) ;
        *
                    p_animReq(RS,"SHGF",A,"DRMX" %addtimedim%) $ p_technFact(RS,"SHGF","LEVL",A)
                      = p_animReq(RS,"SHGF",A,"DRMN" %addtimedim%) * 1.5;
        *
                    p_animReq(RS,"SHGF",A,"FISF" %addtimedim%) $ p_technFact(RS,"SHGF","LEVL",A)
                      = ( 75. * p_meanLiveWgt(RS,"SHGF",%yr_A%)** 0.75 ) / 1000. * p_fatngDays(RS,"SHGF",%yr_A%);
        *
        *
        *               -- total production days for conversion of requirements into daily values (usually includes some empty days due to seasonality):
        *                  NOTE: Imposing additional wide constraints here is just a consistency check. Usually the bounds are set tighter in coco1_anim.
                    p_animProdDays(RS,"SHGF",%yr_A% %addtimedim%) $ p_technFact(RS,"SHGF","LEVL",A)
                      = MIN(p_reqfcnlim("SHGF","DAYS","up"),
                            MAX(p_reqfcnlim("SHGF","DAYS","lo"),
                                SUM(R_RAGG(RS,MS),p_dataCopy(MS,"SHGF","DAYS",%yr%)))) ;

    Departures from CAPRI: none."""
    a = "SHGF"
    for r in st.RS:
        for t in st.techs(r, a):
            st.p_dailyWgtIncrease[(r, a, t)] = min(st.lim(a, "DAILY", "up"), max(
                st.lim(a, "DAILY", "lo"), st.ms_sum(r, lambda m: st.dc(m, a, "DAILY"))))
            st.p_fatngDays[(r, a, t)] = min(365., max(10., (st.dc(r, a, "SGMT") / st.p_carcassShare[a])
                                                      / (st.p_dailyWgtIncrease[(r, a, t)] / 1000.)))
            st.p_meanLiveWgt[(r, a, t)] = max(8., min(25., st.dc(r, a, "SGMT"))) / st.p_carcassShare[a] / 2.
        for t in st.techs(r, a):
            w, d, n = st.p_meanLiveWgt[(r, a, t)], st.p_dailyWgtIncrease[(r, a, t)], st.p_fatngDays[(r, a, t)]
            if st.dc(r, a, "LEVL"):
                st.p_crprReq[(r, a, t)] = ((21.778 + 0.33 * w + 0.258 * d) * 1.35 * n) / 1000.
            _set_req(st, r, a, t, "ENNE", 0)
            _set_req(st, r, a, t, "ENNE", (0.1596 * w + 0.0303 * d - 0.56) * (1. - 0.2) * n
                     * st.p_convFactEnergyUnitsToEnne["ENMR"])
            _set_req(st, r, a, t, "DRMN", (0.038286 * w + 0.06381) * n)
            _set_req(st, r, a, t, "DRMX", st.req(r, a, t, "DRMN") * 1.5)
            _set_req(st, r, a, t, "FISF", (75. * w ** 0.75) / 1000. * n)
            st.p_animProdDays[(r, a, t)] = min(st.lim(a, "DAYS", "up"), max(
                st.lim(a, "DAYS", "lo"), st.ms_sum(r, lambda m: st.dc(m, a, "DAYS"))))


# ------------------------------------------------------------------ (14) other animals
def DATA_OANI_FOUT(st: ReqState) -> None:
    r"""Other animals: no manure output.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1472):

                     DATA(RS,"OANI",FOUT,%yr%) = 0;

    Departures from CAPRI: none."""
    for r in st.RS:
        for row in ("MANN", "MANP", "MANK"):
            st.DATA[(r, "OANI", row)] = 0
