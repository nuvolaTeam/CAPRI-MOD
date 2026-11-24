r"""CAPTRD's equations of the NUTS 2 estimation m_trendNT2 that the member-state model has not (captrd/equations.gms,
CAPRI star 3.0): the regions of a member state add up to the member state's estimate, which is fixed, and the regions'
fodder balances.

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the equation style of
the supply and market refactors). Each function returns the residual, lhs - rhs, of an =E= equation;
capri_mod/pipeline/captrd/estimate_nuts2.py (residuals) holds the domain conditions and the loops over the regions
and the sets, and calls these with the terms it gathers in the sets' order. The terms are V_EstV's values or, for
the NLP, CasADi symbols: the functions are arithmetic only, in the order of operations the port had. m_trendNT2's
other blocks (AREAB_, GROF_, REQS_, ...) are the member-state functions (equations.py), written region by region;
its objective is equations.SSQS_ with the regions' weights.

In this project's notation: V(r, c, w) is V_EstV(r, c, w, exAnteY) for a region r of the member state (Rest), M(c, w)
V_EstV(MSEst, c, w, exAnteY), the member state's, fixed at its own estimate; n(r, c, w) p_data(r, c, w, "nObs")
nonzero.
"""
from __future__ import annotations


def MSGROF_(regional, ms):
    r"""A product's regional gross production adds up to the member state's.

    regional: V(r, GROF, w) of the regions with GROF data; ms: M(GROF, w).

    CAPRI's GAMS, MSGROF_ (captrd/equations.gms l. 182-195):

           MSGROF_(MSEst,S_RowsEst,exAnteY) $ ( SUM( (Rest,MPact) $ (    MAP_RR(MSEst,Rest)
                                                                     $ PACT_TO_IO(MPACT,S_RowsEst)
                                                                     $ p_data(Rest,MPACT,"LEVL","nObs")
                                                                     $ (   V_EstV.LO(Rest,MPACT,S_RowsEst,exAnteY)
                                                                        ne V_EstV.UP(Rest,MPACT,S_RowsEst,exAnteY))),1)
                                               $ p_data(MSEst,"GROF",S_RowsEst,"nObs")
                                               $ (NOT SAMEAS(S_RowsEst,"STRA"))
                                               $ (NOT SUM(SAMEAS(FEED,S_RowsEst),1))
                                               $ (NOT GRPR(S_RowsEst))
                                               ) ..
        *
              SUM(Rest $ (MAP_RR(MSEst,Rest) and p_data(Rest,"GROF",S_RowsEst,"nObs")),V_EstV(Rest,"GROF",S_RowsEst,exAnteY))
        *
              =E= V_EstV(MSEst,"GROF",S_RowsEst,exAnteY);

    Departures from CAPRI: none; the domain condition (a producing activity's coefficient not fixed in a region, no straw, feed or group)
    in the caller (estimate_nuts2.residuals)."""
    return sum(regional) - ms


def MSLEVL_(regional, ms):
    r"""An activity's regional levels add up to the member state's.

    regional: V(r, a, LEVL) of the regions with level data; ms: M(a, LEVL).

    CAPRI's GAMS, MSLEVL_ (captrd/equations.gms l. 199-210):

           MSLEVL_(MSEst,MPACT,exAnteY) $ (  p_data(MSEst,MPACT,"LEVL","nObs") $ (NOT RSET(MPACT))
                                           $ S_ColsEst(MPACT) $ SUM(MAP_RR(MSEst,Rest),1)
        *pw                                If we require splitActsHI=splitActsLo through splitfix_ for the NUTS2 problem,
        *                                  we have to remove (eg) splitActsLo from MSLEVL_ to avoid infeasibilites due to inaccuracies.
        *                                  Aggregation to MS level should still hold for splitActsLo and we test this is est_nuts2_grid.gms.
        *                                  The net effect of activating splitfix_ for NUTS2 should be less solution time (and nonsense)
                                           $ (NOT SplitActsLo(MPACT))
                                           ) ..
        *
              SUM(Rest $ (MAP_RR(MSEst,Rest) and p_data(Rest,MPACT,"LEVL","nObs")), V_EstV(Rest,MPACT,"Levl",exAnteY))
        *
              =E= V_EstV(MSEst,MPACT,"LEVL",exAnteY);

    Departures from CAPRI: none; the domain condition (not RSET, not SplitActsLo) in the caller (estimate_nuts2.residuals)."""
    return sum(regional) - ms


def MSLANDUSE_(regional, ms):
    r"""Forest (FORE) or artificial land (ARTIF): the regional levels add up to the member state's.

    regional: V(r, c, LEVL) of the regions with level data; ms: M(c, LEVL).

    CAPRI's GAMS, MSLANDUSE_ (captrd/equations.gms l. 218-224):

           MSLANDUSE_(MSEst,S_ColsEst,exAnteY) $ (    SUM(MAP_RR(MSEst,Rest),1)
                                                 $ (SAMEAS(S_ColsEst,"FORE") or SAMEAS(S_ColsEst,"ARTIF") )
                                                 $ p_data(MSEst,S_ColsEst,"LEVL","nObs")) ..
        *
              SUM(Rest $ (MAP_RR(MSEst,Rest) $ p_data(Rest,S_ColsEst,"LEVL","nObs")), V_EstV(Rest,S_ColsEst,"Levl",exAnteY))
        *
              =E= V_EstV(MSEst,S_ColsEst,"LEVL",exAnteY);

    Departures from CAPRI: none; the domain condition (FORE and ARTIF, the member state's data) in the caller
    (estimate_nuts2.residuals)."""
    return sum(regional) - ms


def MSFEEDI_(feeds, levels, ms_levl, ms_feed):
    r"""A marketable feed's use by an animal activity: the regions' add up to the member state's, each
    side plus 10 kg a head (the scaling of very small uses).

    feeds: (V(r, a, LEVL), V(r, a, f)) of the regions with level and feed data; levels: V(r, a, LEVL) of the regions
    with level data (consumed after feeds); ms_levl, ms_feed: M(a, LEVL), M(a, f).

    CAPRI's GAMS, MSFEEDI_ (captrd/equations.gms l. 230-240):

           MSFEEDI_(MSEst,MPACT,Feed,exAnteY) $ ( p_data(MSEst,MPACT,Feed,"nObs") and (not FODDI(Feed))
              and (not EX_FEED(MSEst,MPACT,Feed,exAnteY)) and SUM(Rest $ (MAP_RR(MSEst,Rest)
              and p_data(Rest,MPACT,"LEVL","nObs") and p_data(Rest,MPACT,Feed,"nObs")),1)) ..
        *
              SUM(Rest $ (MAP_RR(MSEst,Rest) and p_data(Rest,MPACT,"LEVL","nObs") and p_data(Rest,MPACT,Feed,"nObs")),
                 V_EstV(Rest,MPACT,"Levl",exAnteY)*V_EstV(Rest,MPACT,Feed,exAnteY)/1000)
        *
              + SUM(Rest $ (MAP_RR(MSEst,Rest) and p_data(Rest,MPACT,"LEVL","nObs")),
                      V_EstV(Rest,MPACT,"Levl",exAnteY)*10/1000)
        *
              =E= V_EstV(MSEst,MPACT,"LEVL",exAnteY)*(V_EstV(MSEst,MPACT,Feed,exAnteY)+10)/1000;

    Departures from CAPRI: none; the domain condition (not FODDI, not EX_FEED) in the caller (estimate_nuts2.residuals)."""
    lhs = sum(levl * feed * 0.001 for levl, feed in feeds) + sum(levl * 10.0 * 0.001 for levl in levels)
    return lhs - ms_levl * (ms_feed + 10.0) * 0.001


def MSlosfFoddo_(losf, grof, ms_losf, ms_grof):
    r"""A region's fodder losses at the member state's loss rate.

    losf, grof: V(r, LOSF, o), V(r, GROF, o); ms_losf, ms_grof: the member state's estimate ESTP(LOSF, o) and
    ESTP(GROF, o) (the rate is zero where that GROF is zero).

    CAPRI's GAMS, MSlosfFoddo_ (captrd/equations.gms l. 474-485):

           MSlosfFoddo_(rEst,FODDO,exAnteY) $ (p_data(rEst,"GROF",FODDO,"nObs") $ (not SAMEAS(FODDO,"STRA")))..
        *
              V_EstV(rEst,"LOSF",FODDO,exAnteY)
        *
              =E=

             V_EstV(rEst,"GROF",FODDO,exAnteY)
        *
        *        -- same loss rate as at MS level when working at regional level
        *
                * SUM(MSEst $ ESTP(MSEst,"GROF",FODDO,exAnteY),
                                    ESTP(MSEST,"LOSF",FODDO,exAnteY)/ESTP(MSEst,"GROF",FODDO,exAnteY)) ;

    Departures from CAPRI: none; the domain condition (GROF data, not STRA) in the caller (estimate_nuts2.residuals)."""
    rate = ms_losf / ms_grof if ms_grof else 0.0
    return losf - grof * rate


def MSindmMaif_(regional, ms):
    r"""Green maize's industrial (biogas) use: the regions' adds up to the member state's.

    regional: V(r, INDM, MAIF) of the regions with data; ms: M(INDM, MAIF).

    CAPRI's GAMS, MSindmMaif_ (captrd/equations.gms l. 490-495):

           MSindmMaif_(MSEst,exAnteY) $ ( SUM(MAP_RR(MSEst,Rest) $ p_data(rEst,"INDM","MAIF","nObs"),1)
                                        $ p_data(MSEst,"INDM","MAIF","nObs") ) ..
        *
              SUM(MAP_RR(MSEst,Rest) $ p_data(rEst,"INDM","MAIF","nObs"),V_EstV(Rest,"INDM","MAIF",exAnteY))
        *
              =E= V_EstV(MSEst,"INDM","MAIF",exAnteY);

    Departures from CAPRI: none; the domain condition in the caller (estimate_nuts2.residuals)."""
    return sum(regional) - ms


def EFED_(grof, losf, n_losf, indm, n_indm, feeds):
    r"""A region's fodder is fed: its production net of losses and biogas use equals the use of its feeds.

    grof, losf, indm: V(r, GROF, o), V(r, LOSF, o), V(r, INDM, o); n_losf, n_indm: their data (n(r, LOSF, o),
    n(r, INDM, o)); feeds: V(r, GROF, f) of the feeds f of FEED_TO_O(f, o) with data.

    CAPRI's GAMS, EFED_ (captrd/equations.gms l. 500-508):

           EFED_(rest,FODDO,exAnteY) $ (  SUM(FEED_TO_O(FEED,FODDO) , p_data(Rest,"GROF",FEED,"nObs")) $(not sum(sameas(Foddo,ex_endofodderUse),1))
                                        $ p_data(Rest,"GROF",FODDO,"nObs"))..

             V_EstV(Rest,"GROF",FODDO,exAnteY) - V_EstV(Rest,"LOSF",FODDO,exAnteY) $ p_data(Rest,"LOSF",FODDO,"nObs")

                                               - V_EstV(Rest,"INDM",FODDO,exAnteY) $ p_data(Rest,"INDM",FODDO,"nObs")

                =E= SUM(FEED_TO_O(FEED,FODDO) $ p_data(Rest,"GROF",FEED,"nObs"),
                   V_EstV(Rest,"GROF",FEED,exAnteY));

    Departures from CAPRI: ex_endofodderUse, empty outside the farm types, is not ported; the domain condition in the caller
    (estimate_nuts2.residuals)."""
    lhs = grof - losf * n_losf - indm * n_indm
    return lhs - sum(feeds)
