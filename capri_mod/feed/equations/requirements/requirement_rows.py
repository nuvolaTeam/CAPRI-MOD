r"""p_animReq's rows: crude protein, the erasing, the signs, energy, per day, dry matter and the energy substitution
(feed/req_or_man_fnc.gms, 'req' mode; moved from capri_mod/feed/equations/req_or_man_fnc_req.py as they were, 26
November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.feed.equations.req_or_man_fnc import (BULF, CALF, CALR, DCOW, HEIF, NRUMI, DATA_AGGR_YCOW,  # noqa: F401
                                                     p_stockingRate)
from capri_mod.data.definitions import capri_set
from capri_mod.feed.equations.requirements.state import A_ALL, FEED, REQSE, REQSR, ReqState, SUBENE, _set_req  # noqa: E402




# ------------------------------------------------------------------ PART II: general assignments for requirements
def _techs_all(st):
    """(r, act, t) over the regions, CAPRI's animal activities and technologies."""
    return [(r, a, t) for r in st.RS for a in st.AACT for t in A_ALL]


def p_animReq_CRPR(st: ReqState) -> None:
    r"""The crude-protein requirement copied from p_crprReq, where the technology has a herd.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1482):

                    p_animReq(RS,AACT,A,"CRPR" %addtimedim%) $ (DATA(RS,AACT,"LEVL",%yr%)*p_technFact(RS,AACT,"LEVL",A)) = p_crprReq(RS,AACT,A,%yr%);

    Departures from CAPRI: none."""
    for r, a, t in _techs_all(st):
        if st.D(r, a, "LEVL") * st.tf(r, a, "LEVL", t):
            _set_req(st, r, a, t, "CRPR", st.g(st.p_crprReq, r, a, t))


def p_animReq_erase(st: ReqState) -> None:
    r"""The requirements erased where the technology has no herd.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1486):

                    p_animReq(RS,AACT,A,REQSR %addtimedim%) $ ( (DATA(RS,AACT,"LEVL",%yr%)*p_technFact(RS,AACT,"LEVL",A)) EQ 0.) = 0.0;

    Departures from CAPRI: none."""
    for r, a, t in _techs_all(st):
        if st.D(r, a, "LEVL") * st.tf(r, a, "LEVL", t) == 0.:
            for item in REQSR:
                if (r, a, t, item) in st.p_animReq:
                    _set_req(st, r, a, t, item, 0.0)


def p_animReq_signs(st: ReqState) -> None:
    r"""The maximum requirements with their sign turned (minimum constraints in the supply model), the long fibre
    from the digestible fibre, and the maximum dry matter at least 1.2 times the minimum.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1491-1501):

                    p_animReq(RS,AACT,A,"DRMX" %addtimedim%) = - p_animReq(RS,AACT,A,"DRMX" %addtimedim%);
                    p_animReq(RS,AACT,A,"FICT" %addtimedim%) = - p_animReq(RS,AACT,A,"FICT" %addtimedim%);
                    p_animReq(RS,AACT,A,"FICO" %addtimedim%) = - p_animReq(RS,AACT,A,"FICO" %addtimedim%);
                    p_animReq(RS,AACT,A,"FISM" %addtimedim%) = - p_animReq(RS,AACT,A,"FISM" %addtimedim%);
                    p_animReq(RS,AACT,A,"FISF" %addtimedim%) = - p_animReq(RS,AACT,A,"FISF" %addtimedim%);

        *           --- long fiber needs derived from FIDI (see paper 97/12, p. 17)
                    p_animReq(RS,AACT,A,"FILG" %addtimedim%)  = p_animReq(RS,AACT,A,"FIDI" %addtimedim%)/3.;
        *
                    p_animReq(RS,AACT,A,"DRMX" %addtimedim%) $ p_animReq(RS,AACT,A,"DRMN" %addtimedim%)
                      = -MAX(ABS(p_animReq(RS,AACT,A,"DRMX" %addtimedim%)),ABS(p_animReq(RS,AACT,A,"DRMN" %addtimedim%))* 1.2);

    Departures from CAPRI: none."""
    for k in list(st.p_animReq):
        if k[3] in ("DRMX", "FICT", "FICO", "FISM", "FISF"):
            st.p_animReq[k] = - st.p_animReq[k]
    for (r, a, t, item) in list(st.p_animReq):
        if item == "FIDI":
            _set_req(st, r, a, t, "FILG", st.p_animReq[(r, a, t, "FIDI")] / 3.)
    for (r, a, t, item) in list(st.p_animReq):
        if item == "DRMN" and st.p_animReq[(r, a, t, item)]:
            _set_req(st, r, a, t, "DRMX", -max(abs(st.req(r, a, t, "DRMX")), abs(st.req(r, a, t, "DRMN")) * 1.2))


def p_animReq_ENNE(st: ReqState) -> None:
    r"""Every energy requirement rebased to net energy for lactation (ENNE), where the technology has a herd.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1506-1507):

                    p_animReq(RS,AACT,A,"ENNE" %addtimedim%) $ (DATA(RS,AACT,"LEVL",%yr%)*p_technFact(RS,AACT,"LEVL",A))
                      =  SUM(REQSE, p_animReq(RS,AACT,A,REQSE %addtimedim%) * p_convFactEnergyUnitsToEnne(REQSE) );

    Departures from CAPRI: none."""
    for r, a, t in _techs_all(st):
        if st.D(r, a, "LEVL") * st.tf(r, a, "LEVL", t):
            _set_req(st, r, a, t, "ENNE", sum(st.req(r, a, t, e) * st.p_convFactEnergyUnitsToEnne[e] for e in REQSE))


def p_animReq_per_day(st: ReqState) -> None:
    r"""The requirements per day instead of per head; the feeds' entries set to 1; the requirements erased where the
    technology has no share.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1520-1529):

                    p_animReq(RS,AACT,A,REQSR %addtimedim%)  $ p_animProdDays(RS,AACT,%yr_A% %addtimedim%) = p_animReq(RS,AACT,A,REQSR %addtimedim%)/p_animProdDays(RS,AACT,%yr_A% %addtimedim%);
                    p_animReq(RS,AACT,A,SUBENE %addtimedim%) $ p_animProdDays(RS,AACT,%yr_A% %addtimedim%) = p_animReq(RS,AACT,A,SUBENE %addtimedim%)/p_animProdDays(RS,AACT,%yr_A% %addtimedim%);

                    p_animReq(RS,AACT,A,"Test" %addtimedim%) $ p_animProdDays(RS,AACT,%yr_A% %addtimedim%) = p_animReq(RS,AACT,A,"Test" %addtimedim%) / p_animProdDays(RS,AACT,%yr_A% %addtimedim%);
        *
                    p_animReq(RS,AACT,A,FEED %addtimedim%)   $ p_animProdDays(RS,AACT,%yr_A% %addtimedim%) = 1.0;
        *
                    p_animReq(RS,AACT,A,REQSR %addtimedim%)  $ (NOT p_technFact(RS,AACT,"LEVL",A)) = 0;

                    p_animReq(RS,AACT,A,"Test" %addtimedim%) $ p_animProdDays(RS,AACT,%yr_A% %addtimedim%) = 0;

    The entries "Test" are CAPRI's diagnostics, set to 0 at the end: not kept. Departures from CAPRI: none."""
    for r, a, t in _techs_all(st):
        n = st.g(st.p_animProdDays, r, a, t)
        if n:
            for item in REQSR + SUBENE:
                if (r, a, t, item) in st.p_animReq:
                    st.p_animReq[(r, a, t, item)] = st.p_animReq[(r, a, t, item)] / n
            for f in FEED:
                _set_req(st, r, a, t, f, 1.0)
        if not st.tf(r, a, "LEVL", t):
            for item in REQSR:
                if (r, a, t, item) in st.p_animReq:
                    _set_req(st, r, a, t, item, 0)


def p_animReq_DRMA(st: ReqState) -> None:
    r"""The average dry matter intake per day: between the minimum and the maximum, else from either.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1534-1543):

                    p_animReq(RS,AACT,A,"DRMA" %addtimedim%) $ (DATA(RS,AACT,"LEVL",%yr%)*p_technFact(RS,AACT,"LEVL",A)) = 0.0;
        *
                    p_animReq(RS,AACT,A,"DRMA" %addtimedim%) $ (p_animReq(RS,AACT,A,"DRMN" %addtimedim%) $ p_animReq(RS,AACT,A,"DRMX" %addtimedim%))
                      = p_animReq(RS,AACT,A,"DRMN" %addtimedim%) + (-p_animReq(RS,AACT,A,"DRMX" %addtimedim%) - p_animReq(RS,AACT,A,"DRMN"  %addtimedim%)) / 4.;
        *
                    p_animReq(RS,AACT,A,"DRMA" %addtimedim%) $  ( (NOT p_animReq(RS,AACT,A,"DRMA" %addtimedim%)) $ p_animReq(RS,AACT,A,"DRMN"  %addtimedim%))
                      = p_animReq(RS,AACT,A,"DRMN" %addtimedim%) * 1.1;
        *
                    p_animReq(RS,AACT,A,"DRMA" %addtimedim%) $  ( (NOT p_animReq(RS,AACT,A,"DRMA" %addtimedim%)) $ p_animReq(RS,AACT,A,"DRMX"  %addtimedim%))
                      = -p_animReq(RS,AACT,A,"DRMX" %addtimedim%) * 0.74;

    Departures from CAPRI: none."""
    for r, a, t in _techs_all(st):
        if st.D(r, a, "LEVL") * st.tf(r, a, "LEVL", t):
            _set_req(st, r, a, t, "DRMA", 0.0)
    for r, a, t in {(k[0], k[1], k[2]) for k in st.p_animReq}:
        mn, mx = st.req(r, a, t, "DRMN"), st.req(r, a, t, "DRMX")
        if mn and mx:
            _set_req(st, r, a, t, "DRMA", mn + (-mx - mn) / 4.)
        if not st.req(r, a, t, "DRMA") and mn:
            _set_req(st, r, a, t, "DRMA", mn * 1.1)
        if not st.req(r, a, t, "DRMA") and st.req(r, a, t, "DRMX"):
            _set_req(st, r, a, t, "DRMA", -st.req(r, a, t, "DRMX") * 0.74)


def p_animReqSubEne(st: ReqState) -> None:
    r"""The energy components stored apart and erased from the requirements; the production days erased where the
    technology has no share.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1548-1552):

                    p_animReqSubEne(RS,AACT,A,SUBENE %addtimedim%) = p_animReq(RS,AACT,A,SUBENE  %addtimedim%);
                    p_animReq(RS,AACT,A,SUBENE %addtimedim%)       = 0;

        *
                    p_animProdDays(RS,AACT,%yr_A% %addtimedim%) $ (NOT p_technFact(RS,AACT,"LEVL",A)) = 0;

    Departures from CAPRI: none."""
    for k in [k for k in st.p_animReq if k[3] in SUBENE]:
        st.p_animReqSubEne[k] = st.p_animReq.pop(k)
    for (r, a, t) in list(st.p_animProdDays):
        if not st.tf(r, a, "LEVL", t):
            st.p_animProdDays[(r, a, t)] = 0
