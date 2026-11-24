r"""CAPTRD's bound statements of captrd/estimate_ms.gms (CAPRI star 3.0): the member-state estimation's own bounds (l. 53-162), as named
functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (the assignments
refactor's style: one function per statement block, named after the bounded symbol, V_EstV.LO / .UP / .FX). The
functions take the numbers the statement reads and return the bound; capri_mod/pipeline/captrd/estimate_bounds.py
(bounds) holds the domain conditions, the loops over the sets and the order of the statements, and calls them. A
bound "before" is the one an earlier statement set (-inf / +inf where none did); the arithmetic is the port's, in its
order of operations, so the bounds are unchanged.
"""
from __future__ import annotations


def V_EstV_up_std():
    r"""V_EstV.UP of every position with data: the standard upper bound, 1e9.

    CAPRI's GAMS (captrd/estimate_ms.gms l. 55-55):

             v_estV.UP(MS,S_ColsEst,S_RowsEst,exAnte) $ p_data(MS,S_ColsEst,S_RowsEst,"nObs") = 1.E+9;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return 1.0e9


def V_EstV_lo_std(c, w, support, cssp, ocro_r, oani_r, ocro_c, oani_c):
    r"""V_EstV.LO of every position with data or a support: 1% of the support, or the base's negative values of
    CSSP, of the OCRO and OANI rows and columns.

    c, w: the position; support: P_Result(MS, c, w, "Support"); cssp: p_data(MS, "CSSP", w, "BASM"); ocro_r,
    oani_r: p_data(MS, c, "OCRO" / "OANI", "BASM"); ocro_c, oani_c: p_data(MS, "OCRO" / "OANI", w, "BASM").

    CAPRI's GAMS (captrd/estimate_ms.gms l. 60-68):

             v_estV.lo(MS,S_ColsEst,S_RowsEst,Exante) $ (p_data(MS,S_ColsEst,S_RowsEst,"nObs")
                                                         or p_result(MS,S_ColsEst,S_RowsEst,ExAnte,"Support") )

                = MAX(  p_result(MS,S_ColsEst,S_RowsEst,ExAnte,"Support") * 0.01,
                      + p_data(MS,"CSSP",S_RowsEst,"BASM")  $ ((p_data(MS,"CSSP",S_RowsEst,"BASM")  LT 0) and sameas(S_ColsEst,"CSSP"))
                      + p_data(MS,S_ColsEst,"OCRO","BASM")  $ ((p_data(MS,S_ColsEst,"OCRO","BASM")  LT 0) and sameas(S_RowsEst,"OCRO"))
                      + p_data(MS,S_ColsEst,"OANI","BASM")  $ ((p_data(MS,S_ColsEst,"OANI","BASM")  LT 0) and sameas(S_RowsEst,"OANI"))
                      + p_data(MS,"OCRO",S_RowsEst,"BASM")  $ ((p_data(MS,"OCRO",S_RowsEst,"BASM")  LT 0) and sameas(S_ColsEst,"OCRO"))
                      + p_data(MS,"OANI",S_RowsEst,"BASM")  $ ((p_data(MS,"OANI",S_RowsEst,"BASM")  LT 0) and sameas(S_ColsEst,"OANI")));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    extra = 0.0
    if c == "CSSP" and cssp < 0:
        extra += cssp
    if w == "OCRO" and ocro_r < 0:
        extra += ocro_r
    if w == "OANI" and oani_r < 0:
        extra += oani_r
    if c == "OCRO" and ocro_c < 0:
        extra += ocro_c
    if c == "OANI" and oani_c < 0:
        extra += oani_c
    return max(support * 0.01, extra)


def V_EstV_MPACT_LEVL(lo, up, n_nuts2):
    r"""V_EstV.LO and .UP of an activity's level: the lower bound, where nonzero, at least 1e-5 x the member state's
    NUTS 2 regions with data; the upper bound at least 1.1 x the lower.

    lo, up: the bounds before (-inf / +inf where none); n_nuts2: the regions with the activity's level data. Returns
    (lo, up), lo None where it stays.

    CAPRI's GAMS (captrd/estimate_ms.gms l. 78-82):

             v_estV.LO(Rest,MPACT,"LEVL",exAnte) $ (p_data(Rest,MPACT,"LEVL","nObs") and (v_estV.LO(Rest,MPACT,"LEVL",exAnte) ne 0) )
                = MAX(1.E-5*SUM(MAP_RR(Rest,SRNUTS2) $ p_data(SRNUTS2,MPACT,"LEVL","nObs"), 1),v_estV.LO(Rest,MPACT,"LEVL",exAnte));

             v_estV.UP(Rest,MPACT,"LEVL",exAnte) $ p_data(Rest,MPACT,"LEVL","nObs")
                = MAX(v_estV.LO(Rest,MPACT,"LEVL",exAnte)*1.1,v_estV.UP(Rest,MPACT,"LEVL",exAnte));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    new_lo = max(1.0e-5 * n_nuts2, lo) if lo != 0 else None
    return new_lo, max((lo if new_lo is None else new_lo) * 1.1, up)


def V_EstV_lo_GROF_SUGB(lo, quota):
    r"""V_EstV.LO of sugar beet's production under a quota (from 2006): at most the quota.

    CAPRI's GAMS (captrd/estimate_ms.gms l. 108-109):

             v_estV.lo(MS,"GROF","SUGB",Exante) $ ( p_data(MS,"QUTS","SUGB","BASM") and calyea(ExAnte) GE 2006)
                =  MIN(v_estV.lo(MS,"GROF","SUGB",Exante),p_result(MS,"QUTS","SUGB",Exante,"p_data")) ;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return min(lo, quota)


def V_EstV_fx_INHA_LEVL(pop):
    r"""V_EstV.FX of the population: the exogenous series.

    CAPRI's GAMS (captrd/estimate_ms.gms l. 114-114):

             v_estV.FX(MS,"INHA","LEVL",exante) = p_result(MS,"INHA","LEVL",exante,"p_data");

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return pop


def V_EstV_lo_sugar_quota():
    r"""V_EstV.LO of sugar beet's level, TOOU, production, exports, domestic use and sugar's processing without a
    sugar quota: zero.

    CAPRI's GAMS (captrd/estimate_ms.gms l. 120-125):

             v_estV.lo(MS,'SUGB','LEVL',exAnte)$(not p_result(ms,'QUTS','SUGA',exAnte,"p_data")) = 0;
             v_estV.lo(MS,'SUGB','TOOU',exAnte)$(not p_result(ms,'QUTS','SUGA',exAnte,"p_data")) = 0;
             v_estV.lo(MS,'GROF','SUGB',exAnte)$(not p_result(ms,'QUTS','SUGA',exAnte,"p_data")) = 0;
             v_estV.lo(MS,'EXPT','SUGB',exAnte)$(not p_result(ms,'QUTS','SUGA',exAnte,"p_data")) = 0;
             v_estV.lo(MS,'DOMM','SUGB',exAnte)$(not p_result(ms,'QUTS','SUGA',exAnte,"p_data")) = 0;
             v_estV.lo(MS,'MAPR','SUGA',exAnte)$(not p_result(ms,'QUTS','SUGA',exAnte,"p_data")) = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return 0.0


def V_EstV_expert(expert):
    r"""V_EstV.LO or .UP of a position with an expert bound (expertlo, expertup): the expert's, as a last resort.

    CAPRI's GAMS (captrd/estimate_ms.gms l. 159-162):

                 v_estV.lo(rEst,S_ColsEst,S_RowsEst,Exante) $ p_result(rEst,S_ColsEst,S_RowsEst,exAnte,"expertlo")
                    = p_result(rEst,S_ColsEst,S_RowsEst,exAnte,"expertlo") ;
                 v_estV.up(rEst,S_ColsEst,S_RowsEst,Exante) $ p_result(rEst,S_ColsEst,S_RowsEst,exAnte,"expertup")
                    = p_result(rEst,S_ColsEst,S_RowsEst,exAnte,"expertup") ;

    none; the aglinkTightLink bounds before it (l. 127-154) are off in the reference run and not ported."""
    return expert
