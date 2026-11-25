r"""CAPTRD's bound statements of captrd/estimate_ms.gms (CAPRI star 3.0): the member-state estimation's own bounds (l. 53-162)
and its bound-widening after an infeasible solve (l. 252-418), as named functions.

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


# --- the bound-widening after an infeasible solve (l. 252-418; estimate_nlp) ------------------------------------------


def V_EstV_up_LEVL_try(level):
    r"""V_EstV.UP of an activity's level at its upper bound with a multiplier in the first five tries (not an
    expert's bound): twice the level.

    CAPRI's GAMS (captrd/estimate_ms.gms l. 258-263):

                   v_estV.UP(Rest,MPACT,"LEVL",exAnte)      $ ( (ABS(v_estV.M(Rest,MPACT,"LEVL",exAnte)) GT EPS)
                                                              $ (v_estV.UP(Rest,MPACT,"LEVL",exAnte) EQ v_estV.L(Rest,MPACT,"LEVL",exAnte))
        *                                                     no early bound opening for expert bounds which may be tight on purpose
                                                              $ (not (   v_estV.UP(Rest,MPACT,"LEVL",exAnte)
                                                                      eq p_result(rEst,MPAct,"LEVL",exAnte,"expertup"))))
                      = v_estV.L(Rest,MPACT,"LEVL",exAnte)*2.0;

    Departures from CAPRI: none in the arithmetic; the domain condition, the binding bounds and the loops in the caller
    (estimate_nlp._widen, _oind_ocro, _again)."""
    return level * 2.0


def V_EstV_lo_LEVL_try(level):
    r"""V_EstV.LO of an activity's level at its lower bound with a multiplier in the first five tries (not an
    expert's bound): half the level.

    CAPRI's GAMS (captrd/estimate_ms.gms l. 265-270):

                   v_estV.LO(Rest,MPACT,"LEVL",exAnte)      $ ( (ABS(v_estV.M(Rest,MPACT,"LEVL",exAnte)) GT EPS)
                                                              $ (v_estV.LO(Rest,MPACT,"LEVL",exAnte) EQ v_estV.L(Rest,MPACT,"LEVL",exAnte))
        *                                                     no early bound opening for expert bounds which may be tight on purpose
                                                              $ (not (   v_estV.lo(Rest,MPACT,"LEVL",exAnte)
                                                                      eq p_result(rEst,MPAct,"LEVL",exAnte,"expertlo"))))
                      = v_estV.L(Rest,MPACT,"LEVL",exAnte)*0.5;

    Departures from CAPRI: none in the arithmetic; the domain condition, the binding bounds and the loops in the caller
    (estimate_nlp._widen, _oind_ocro, _again)."""
    return level * 0.5


def V_EstV_lo_INCE_try(lo, n):
    r"""V_EstV.LO of an activity's calories (INCE) at an expert's lower bound with a multiplier after five tries: x
    (1 - 1e-5 n)^n.

    lo: the bound before; n: nRepeatedSolves.

    CAPRI's GAMS (captrd/estimate_ms.gms l. 281-287):

                   V_EstV.LO(Rest,NCNC,"INCE",exAnte) $ (  P_DATA(Rest,NCNC,"INCE","nObs")
                                                              $ v_estV.M(Rest,NCNC,"INCE",exAnte)
                                                              $ p_result(rEst,NCNC,"INCE",exAnte,"expertlo")
                                                              $ (v_estV.LO(Rest,NCNC,"INCE",exAnte) eq v_estV.L(Rest,NCNC,"INCE",exAnte))
                                                              )
        *                    Permits only 2.5% opening:
                       = V_EstV.LO(Rest,NCNC,"INCE",exAnte) * (1 - (0.00001 * nRepeatedSolves(MS)))**nRepeatedSolves(MS);

    Departures from CAPRI: none in the arithmetic; the domain condition, the binding bounds and the loops in the caller
    (estimate_nlp._widen, _oind_ocro, _again)."""
    return lo * (1 - 1.0e-5 * n) ** n


def V_EstV_up_INCE_try(up, n):
    r"""V_EstV.UP of an activity's calories at an expert's upper bound with a multiplier after five tries: x
    (1 + 1e-5 n)^n.

    CAPRI's GAMS (captrd/estimate_ms.gms l. 289-294):

                   V_EstV.UP(Rest,NCNC,"INCE",exAnte) $ (  P_DATA(Rest,NCNC,"INCE","nObs")
                                                              $ v_estV.M(Rest,NCNC,"INCE",exAnte)
                                                              $ p_result(rEst,NCNC,"INCE",exAnte,"expertup")
                                                              $ (v_estV.UP(Rest,NCNC,"INCE",exAnte) eq v_estV.L(Rest,NCNC,"INCE",exAnte))
                                                              )
                       = V_EstV.UP(Rest,NCNC,"INCE",exAnte) * (1 + (0.00001 * nRepeatedSolves(MS)))**nRepeatedSolves(MS);

    Departures from CAPRI: none in the arithmetic; the domain condition, the binding bounds and the loops in the caller
    (estimate_nlp._widen, _oind_ocro, _again)."""
    return up * (1 + 1.0e-5 * n) ** n


def V_EstV_lo_widen(lo, prcy_seco):
    r"""V_EstV.LO of a position at its lower bound with a multiplier after five tries: 90% of its size lower (1% for
    the processing yields of the secondary products), at least 0.001.

    lo: the bound before; prcy_seco: the position is PRCY of a secondary product (SECO).

    CAPRI's GAMS (captrd/estimate_ms.gms l. 298-303):

                      v_estV.LO(Rest,S_ColsEst,S_RowsEst,ExAnte) $ ( (ABS(v_estV.M(Rest,S_ColsEst,S_RowsEst,ExAnte)) GT EPS)
                                                     and (v_estV.LO(Rest,S_ColsEst,S_RowsEst,ExAnte) EQ v_estV.L(Rest,S_ColsEst,S_RowsEst,ExAnte)))
                         = v_estV.LO(Rest,S_ColsEst,S_RowsEst,ExAnte)
        *                            try to maintain prcy in range defined in fix_est.gms:
                         - MAX(0.001,(0.9-.89 $ (sameas(s_colsest,"prcy") $ seco(s_rowsest)))
                                     *ABS(v_estV.LO(Rest,S_ColsEst,S_RowsEst,ExAnte)));

    Departures from CAPRI: CAPRI's share 0.9 - .89 is 0.010000000000000009 in floating point, the port's 0.01 (a last-digit difference, as the port
    had it); the domain condition and the binding bounds in the caller (estimate_nlp._widen)."""
    sh = 0.01 if prcy_seco else 0.9
    return lo - max(0.001, sh * abs(lo))


def V_EstV_lo_widen_floor(lo, support, prcy):
    r"""V_EstV.LO of a position with a positive base after five tries: not below zero, and the processing yields
    not below 1% of their support.

    lo: the bound before (-inf where none: GAMS's MAX(0, -inf, ..) gives the floor too); support: P_Result(.,
    "SUPPORT"); prcy: the column is PRCY.

    CAPRI's GAMS (captrd/estimate_ms.gms l. 305-309):

                      v_estV.LO(Rest,S_ColsEst,S_RowsEst,ExAnte) $ ( (p_data(Rest,S_ColsEst,S_RowsEst,"BASM") GT 0.)
                                                                   $ (NOT (SAMEAS(S_ColsEst,"NTRD") or SAMEAS(S_ColsEst,"INTP"))))
                         = MAX(0.,v_estV.LO(Rest,S_ColsEst,S_RowsEst,ExAnte),
        *                  ... but processing yields must not vanish because this creates a loophole to dump something into PRCM without an output via MAPR_
                              .01*P_Result(Rest,S_ColsEst,S_RowsEst,Exante,"SUPPORT") $ SAMEAS(S_ColsEst,"PRCY") );

    Departures from CAPRI: none in the arithmetic; the domain condition, the binding bounds and the loops in the caller
    (estimate_nlp._widen, _oind_ocro, _again)."""
    return max(0.0, lo, 0.01 * support if prcy else 0.0)


def V_EstV_up_widen(up, prcy_seco):
    r"""V_EstV.UP of a position at its upper bound with a multiplier after five tries: 90% of its size higher (1% for
    the processing yields of the secondary products), at least 0.001.

    CAPRI's GAMS (captrd/estimate_ms.gms l. 311-316):

                      v_estV.UP(Rest,S_ColsEst,S_RowsEst,ExAnte) $ ( (ABS(v_estV.M(Rest,S_ColsEst,S_RowsEst,ExAnte)) GT EPS)
                                                     and (v_estV.UP(Rest,S_ColsEst,S_RowsEst,ExAnte) EQ v_estV.L(Rest,S_ColsEst,S_RowsEst,ExAnte)))
                         = v_estV.UP(Rest,S_ColsEst,S_RowsEst,ExAnte)
        *                            try to maintain prcy in range defined in fix_est.gms:
                         + MAX(0.001,(0.9-.89 $ (sameas(s_colsest,"prcy") $ seco(s_rowsest)))
                                     *ABS(v_estV.UP(Rest,S_ColsEst,S_RowsEst,ExAnte)));

    Departures from CAPRI: CAPRI's 0.9 - .89 (as V_EstV_lo_widen); the domain condition and the binding bounds in the caller 
    (estimate_nlp._widen)."""
    sh = 0.01 if prcy_seco else 0.9
    return up + max(0.001, sh * abs(up))


def V_EstV_up_PRCY_range(up, lo):
    r"""V_EstV.UP of a processing yield not fixed: at least 1.1 x its lower bound.

    CAPRI's GAMS (captrd/estimate_ms.gms l. 317-318):

                      v_estV.UP(Rest,S_ColsEst,S_RowsEst,ExAnte) $ ( v_estV.range(Rest,S_ColsEst,S_RowsEst,ExAnte) $ SAMEAS(S_ColsEst,"PRCY"))
                         = MAX(v_estV.UP(Rest,S_ColsEst,S_RowsEst,ExAnte), 1.1*v_estV.LO(Rest,S_ColsEst,S_RowsEst,ExAnte));

    Departures from CAPRI: none in the arithmetic; the domain condition, the binding bounds and the loops in the caller
    (estimate_nlp._widen, _oind_ocro, _again)."""
    return max(up, 1.1 * lo)


def V_EstV_lo_MPACT_LEVL_again(lo, n_nuts2):
    r"""V_EstV.LO of an activity's level, where nonzero, after the widening: at least 1e-5 x the member state's NUTS 2
    regions with data (as l. 78-79).

    CAPRI's GAMS (captrd/estimate_ms.gms l. 328-329):

                   v_estV.LO(Rest,MPACT,"LEVL",exAnte) $ (p_data(Rest,MPACT,"LEVL","nObs") and (v_estV.LO(Rest,MPACT,"LEVL",exAnte) ne 0) )
                      = MAX(1.E-5*SUM(MAP_RR(Rest,SRNUTS2) $ p_data(SRNUTS2,MPACT,"LEVL","nObs"), 1),v_estV.LO(Rest,MPACT,"LEVL",exAnte));

    Departures from CAPRI: none in the arithmetic; the domain condition, the binding bounds and the loops in the caller
    (estimate_nlp._widen, _oind_ocro, _again)."""
    return max(1.0e-5 * n_nuts2, lo)


def V_EstV_lo_OIND_OCRO():
    r"""V_EstV.LO of OIND's and OCRO's levels at their lower bound with a multiplier and without production, after 25
    tries: zero.

    CAPRI's GAMS (captrd/estimate_ms.gms l. 337-345):

                      v_estV.LO(Rest,"OIND","LEVL",exAnte)      $ ((ABS(v_estV.M(Rest,"OIND","LEVL",exAnte)) GT EPS)
                                                           and (v_estV.LO(Rest,"OIND","LEVL",exAnte) EQ v_estV.L(Rest,"OIND","LEVL",exAnte))
                                                           and (v_estV.L(Rest,"GROF","OIND",exAnte) eq 0))
                          = 0;

                      v_estV.LO(Rest,"OCRO","LEVL",exAnte)      $ ((ABS(v_estV.M(Rest,"OCRO","LEVL",exAnte)) GT EPS)
                                                           and (v_estV.LO(Rest,"OCRO","LEVL",exAnte) EQ v_estV.L(Rest,"OCRO","LEVL",exAnte))
                                                           and (v_estV.L(Rest,"GROF","OCRO",exAnte) eq 0))
                           = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition, the binding bounds and the loops in the caller
    (estimate_nlp._widen, _oind_ocro, _again)."""
    return 0.0


def V_EstV_up_MPACT_LEVL_again(lo, up):
    r"""V_EstV.UP of an activity's level not fixed and not an expert's bound: at least 1.1 x its lower bound.

    CAPRI's GAMS (captrd/estimate_ms.gms l. 355-360):

                   v_estV.UP(Rest,MPACT,"LEVL",exAnte) $ ( p_data(Rest,MPACT,"LEVL","nObs")
                                                         $ v_estV.range(Rest,MPACT,"LEVL",exAnte)
        *                                                no general bound opening for expert bounds which may be tight on purpose
                                                         $ (not (v_estV.UP(Rest,MPACT,"LEVL",exAnte) eq p_result(rEst,MPAct,"LEVL",exAnte,"expertup")))
                                                         )
                      = MAX(v_estV.LO(Rest,MPACT,"LEVL",exAnte)*1.1,v_estV.UP(Rest,MPACT,"LEVL",exAnte));

    Departures from CAPRI: none in the arithmetic; the domain condition, the binding bounds and the loops in the caller
    (estimate_nlp._widen, _oind_ocro, _again)."""
    return max(lo * 1.1, up)


def V_EstV_fx_INHA_LEVL_again(pop):
    r"""V_EstV.FX of the population after the widening: the exogenous series.

    CAPRI's GAMS (captrd/estimate_ms.gms l. 362-362):

                   v_estV.FX(MS,"INHA","LEVL",exante) = p_result(MS,"INHA","LEVL",exante,"p_data");

    Departures from CAPRI: none in the arithmetic; the domain condition, the binding bounds and the loops in the caller
    (estimate_nlp._widen, _oind_ocro, _again)."""
    return pop


def V_EstV_lo_GROF_SUGB_again(quota, lo):
    r"""V_EstV.LO of sugar beet's production under a quota (from 2006) after the widening: at most the quota.

    CAPRI's GAMS (captrd/estimate_ms.gms l. 364-365):

                   v_estV.lo(MS,"GROF","SUGB",Exante) $ ( p_data(MS,"QUTS","SUGB","BASM") and calyea(ExAnte) GE 2006)
                                                  =  MIN(p_result(MS,"QUTS","SUGB",Exante,"p_data"),  v_estV.lo(MS,"GROF","SUGB",Exante)) ;

    Departures from CAPRI: none in the arithmetic; the domain condition, the binding bounds and the loops in the caller
    (estimate_nlp._widen, _oind_ocro, _again)."""
    return min(quota, lo)


def V_EstV_fx_tiny_again():
    r"""V_EstV.FX of a position with a near-zero support and COCO value (not milk) after the widening: zero.

    CAPRI's GAMS (captrd/estimate_ms.gms l. 382-387):

                   v_estV.FX(REST,s_colsEst,s_rowsEst,exAnte) $ (    P_Result(Rest,s_colsEst,s_rowsEst,Exante,"SUPPORT")
                                                                 and P_Result(Rest,s_colsEst,s_rowsEst,Exante,"coco")
        *                                                        do not interfere with comiBounds (as COMI is only completed in coco2 and therefore preliminary)
                                                                 and (not (SAMEAS(s_rowsEst,"COMI") ))
                                                                 and (ABS(P_Result(Rest,s_colsEst,s_rowsEst,Exante,"SUPPORT")) lt 1e-12)
                                                                 and (ABS(P_Result(Rest,s_colsEst,s_rowsEst,Exante,"coco")) lt 1e-12))  = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition, the binding bounds and the loops in the caller
    (estimate_nlp._widen, _oind_ocro, _again)."""
    return 0.0


def V_EstV_UAAR_again(basm, n):
    r"""V_EstV.LO and .UP of UAAR after the widening (without an expert's upper bound): at most the base, falling
    by at most 0.2% a year. Returns (lo, up).

    CAPRI's GAMS (captrd/estimate_ms.gms l. 393-398):

                   v_estV.UP(REST,"UAAR","LEVL",exAnte) $ ( (NOT P_Result(Rest,"UAAR","LEVL",ExAnte,"coco"))
                                                          $ (not p_result(Rest,"UAAR","LEVL",ExAnte,"expertup")))
                                                        = P_DATA(REST,"UAAR","LEVL","BASM");
                   v_estV.lO(REST,"UAAR","LEVL",exAnte) $ ( (NOT P_Result(Rest,"UAAR","LEVL",ExAnte,"coco"))
                                                          $ (not p_result(Rest,"UAAR","LEVL",ExAnte,"expertup")))
                                                        = P_DATA(REST,"UAAR","LEVL","BASM") * (0.998**(OrdT(exAnte)-OrdT("BAS")));

    Departures from CAPRI: none in the arithmetic; the domain condition, the binding bounds and the loops in the caller
    (estimate_nlp._widen, _oind_ocro, _again)."""
    return basm * 0.998 ** n, basm


def V_EstV_fx_land_again(basm):
    r"""V_EstV.FX of ARTO, INLW and KITC after the widening: their base.

    CAPRI's GAMS (captrd/estimate_ms.gms l. 403-405):

                   v_estV.FX(REST,"ARTO","LEVL",exAnte) = P_DATA(REST,"ARTO","LEVL","BASM");
                   v_estV.FX(REST,"INLW","LEVL",exAnte) = P_DATA(REST,"INLW","LEVL","BASM");
                   v_estV.FX(REST,"KITC","LEVL",exAnte) = P_DATA(REST,"KITC","LEVL","BASM");

    Departures from CAPRI: none in the arithmetic; the domain condition, the binding bounds and the loops in the caller
    (estimate_nlp._widen, _oind_ocro, _again)."""
    return basm


def V_EstV_lo_ARTIF_again(basm):
    r"""V_EstV.LO of artificial land after the widening: its base.

    CAPRI's GAMS (captrd/estimate_ms.gms l. 408-408):

                   v_estV.LO(REST,"ARTIF","LEVL",exAnte) = P_DATA(REST,"ARTIF","LEVL","BASM");

    Departures from CAPRI: none in the arithmetic; the domain condition, the binding bounds and the loops in the caller
    (estimate_nlp._widen, _oind_ocro, _again)."""
    return basm


def V_EstV_reqfcnlim_again(bound, lo, up, v):
    r"""V_EstV.LO or .UP of a requirement within the requirement functions' limits after the widening (as fix_est.gms
    l. 675-678). Returns the new bound, or None for another bound.

    CAPRI's GAMS (captrd/estimate_ms.gms l. 414-417):

                   v_estV.LO(Rest,MAACT,s_RowsEst,exAnte) $ (p_reqfcnlim(MAACT,s_RowsEst,"lo") $ p_data(Rest,MAACT,"LEVL","nObs"))
                                  = MAX(v_estV.LO(Rest,MAACT,s_RowsEst,exAnte),p_reqfcnlim(MAACT,s_RowsEst,"lo"));
                   v_estV.UP(Rest,MAACT,s_RowsEst,exAnte) $ (p_reqfcnlim(MAACT,s_RowsEst,"up")  $ p_data(Rest,MAACT,"LEVL","nObs"))
                                  = MIN(v_estV.UP(Rest,MAACT,s_RowsEst,exAnte),p_reqfcnlim(MAACT,s_RowsEst,"up"));

    Departures from CAPRI: none in the arithmetic; the domain condition, the binding bounds and the loops in the caller
    (estimate_nlp._widen, _oind_ocro, _again)."""
    if bound == "lo":
        return max(lo, v)
    if bound == "up":
        return min(up, v)
    return None


def V_EstV_fx_DAYS_again():
    r"""V_EstV.FX of the days of the animal activities with 365 days after the widening.

    CAPRI's GAMS (captrd/estimate_ms.gms l. 418-418):

                   v_estV.FX(Rest,MAACT,"DAYS",exAnte) $ AACTwith365days(MAACT) = 365;

    Departures from CAPRI: none in the arithmetic; the domain condition, the binding bounds and the loops in the caller
    (estimate_nlp._widen, _oind_ocro, _again)."""
    return 365.0
