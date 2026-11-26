r"""CAPTRD's estimation bounds of the net trade, the intermediate use, labour, the expert corridor, UAAR, the artificial
land, the land, set-aside, the tiny supports and sugar beet (captrd/fix_est.gms; moved from
capri_mod/pipeline/captrd/equations/fix_est.py as they were, 26 November 2026).
"""
from __future__ import annotations




def V_EstV_NTRD():
    r"""V_EstV.LO and .UP of net trade: free. Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 727-728):

           v_estV.UP(REST,"NTRD",S_RowsEst,exAnte) $ NUTS0(Rest) = +inf;
           v_estV.lO(REST,"NTRD",S_RowsEst,exAnte) $ NUTS0(REST)  = -inf;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return -float("inf"), float("inf")


def V_EstV_INTP(support):
    r"""V_EstV.LO and .UP of intervention stocks: within twice the support's size. Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 730-734):

           v_estV.lo(Rall,"INTP",S_RowsEst,Exante) $ p_data(Rall,"INTP",S_RowsEst,"nObs")
               = -ABS(P_Result(Rall,"INTP",S_RowsEst,Exante,"Support")) * 2;

           v_estV.UP(Rall,"INTP",S_RowsEst,Exante) $ p_data(Rall,"INTP",S_RowsEst,"nObs")
               = +ABS(P_Result(Rall,"INTP",S_RowsEst,Exante,"Support")) * 2;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return -abs(support) * 2, abs(support) * 2


def V_EstV_GROF_labour(w, basm, mins, maxs):
    r"""V_EstV.LO and .UP of labour (LABO, LABN, LABH): the base times LABO's exogenous minimum and maximum shares,
    widened by 5 points for LABO and LABN.

    w: the row; basm: p_data(., "GROF", w, "BASM"); mins, maxs: p_result(., "MINS" / "MAXS", "LABO", "p_data").
    Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 740-756):

           v_estV.LO(Rest,"GROF","LABO",exante) $ p_data(Rest,"GROF","LABO","BASM")
               = MAX(0,p_data(Rest,"GROF","LABO","BASM") * (p_result(REST,"MINS","LABO",EXANTE,"p_data") - 0.05));

           v_estV.LO(Rest,"GROF","LABN",exante) $ p_data(Rest,"GROF","LABN","BASM")
               = Max(0,p_data(Rest,"GROF","LABN","BASM") * (p_result(REST,"MINS","LABO",EXANTE,"p_data") - 0.05));

           v_estV.LO(Rest,"GROF","LABH",exante) $ p_data(Rest,"GROF","LABH","BASM")
               = MAX(0,p_data(Rest,"GROF","LABH","BASM") * (p_result(REST,"MINS","LABO",EXANTE,"p_data")));

           v_estV.UP(Rest,"GROF","LABO",exante) $ p_data(Rest,"GROF","LABO","BASM")
               = p_data(Rest,"GROF","LABO","BASM") * (p_result(REST,"MAXS","LABO",EXANTE,"p_data") + 0.05);

           v_estV.UP(Rest,"GROF","LABN",exante) $ p_data(Rest,"GROF","LABN","BASM")
               = p_data(Rest,"GROF","LABN","BASM") * (p_result(REST,"MAXS","LABO",EXANTE,"p_data") + 0.05);

           v_estV.UP(Rest,"GROF","LABH",exante) $ p_data(Rest,"GROF","LABH","BASM")
               = p_data(Rest,"GROF","LABH","BASM") * (p_result(REST,"MAXS","LABO",EXANTE,"p_data"));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    dl, du = {"LABO": (-0.05, 0.05), "LABN": (-0.05, 0.05), "LABH": (0.0, 0.0)}[w]
    return max(0.0, basm * (mins + dl)), basm * (maxs + du)


def V_EstV_expert_corridor(lo, up, expert):
    r"""V_EstV.LO and .UP of a position whose support is the expert's: within at least 10% of it.

    lo, up: the bounds before; expert: P_Result(., "Expert"). Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 764-780):

           v_estV.LO(Rest,S_ColsEst,S_RowsEst,exAnte) $   (
                                                              (  P_Result(Rest,S_ColsEst,S_RowsEst,exAnte,"Expert")
                                                              EQ P_Result(Rest,S_ColsEst,S_RowsEst,exAnte,"Support"))
                                                          $ (  v_estV.LO(Rest,S_ColsEst,S_RowsEst,exAnte)
                                                              NE v_estV.UP(Rest,S_ColsEst,S_RowsEst,exAnte))
                                                          $  P_Result(Rest,S_ColsEst,S_RowsEst,exAnte,"Expert")
                                                          $ p_data(Rest,S_ColsEst,S_RowsEst,"nObs"))
           = MIN(v_estV.LO(Rest,S_ColsEst,S_RowsEst,exAnte), 0.9*P_Result(Rest,S_ColsEst,S_RowsEst,exAnte,"Expert"));

           v_estV.UP(Rest,S_ColsEst,S_RowsEst,exAnte)   $ (
                                                              (  P_Result(Rest,S_ColsEst,S_RowsEst,exAnte,"Expert")
                                                              EQ P_Result(Rest,S_ColsEst,S_RowsEst,exAnte,"Support"))
                                                          $ (  v_estV.LO(Rest,S_ColsEst,S_RowsEst,exAnte)
                                                              NE v_estV.UP(Rest,S_ColsEst,S_RowsEst,exAnte))
                                                          $  P_Result(Rest,S_ColsEst,S_RowsEst,exAnte,"Expert")
                                                          $ p_data(Rest,S_ColsEst,S_RowsEst,"nObs"))
           = MAX(v_estV.UP(Rest,S_ColsEst,S_RowsEst,exAnte), 1.1*P_Result(Rest,S_ColsEst,S_RowsEst,exAnte,"Expert"));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return min(lo, 0.9 * expert), max(up, 1.1 * expert)


def V_EstV_UAAR(basm, n):
    r"""V_EstV.LO and .UP of the utilised agricultural area: at most the base, falling by at most 0.2% a year.

    basm: p_data(., "UAAR", "LEVL", "BASM"); n: OrdT(exAnte) - OrdT("BAS"). Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 785-795):

           v_estV.UP(REST,"UAAR","LEVL",exAnte)
                                                   $ (NOT P_Result(Rest,"UAAR","LEVL",ExAnte,"coco"))
           = p_data(REST,"UAAR","LEVL","BASM");

        *       ... and cannot change by more than -0.2% per annum
        *      (Even though this is less than observed in some MS15 (ES, IT, AT, PT, SE, FI))
        *
           v_estV.lO(REST,"UAAR","LEVL",exAnte)
                                                   $ (NOT P_Result(Rest,"UAAR","LEVL",ExAnte,"coco"))
           = p_data(REST,"UAAR","LEVL","BASM")
                                                * (0.998**(OrdT(exAnte)-OrdT("BAS")));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return basm * 0.998 ** n, basm


def V_EstV_ARTIF(basm, n_obs, up, t, ord_bas, as_coded):
    r"""V_EstV.LO and .UP of artificial land: at least its base, at most growing by 2% a year (and the upper bound
    before).

    basm: p_data(MSEst, "ARTIF", "LEVL", "BASM"); n_obs: it has data; up: the bound before (+inf where none); t,
    ord_bas: OrdT(ExAnte), OrdT("BAS"); as_coded: l. 810's parenthesis as coded. Returns (lo, up).

    l. 810 reads 1.02**(OrdT(ExAnte)) - OrdT("BAS"): the year as the exponent (CAPRI-ERROR, a misplaced parenthesis;
    FIX-7). Fixed (the default, as_coded False), 1.02**(OrdT(ExAnte) - OrdT("BAS")) as the comment's "max. 2%
    increase per year"; the max with the previous bound kept, as coded, so where that is the standard 1e9 the bound
    stays 1e9.

    CAPRI's GAMS (captrd/fix_est.gms l. 805-811):

           v_estV.LO(MSEst,"ARTIF","LEVL",exAnte) $ Rest(MSest)
                       = sum(REST $ (MAP_RR(MSEst,Rest) $ p_data(Rest,"ARTIF","LEVL","nObs")),
                                     P_DATA(REST,"ARTIF","LEVL","BASM"));
        *       -- let's impose a suitable upper bound (max. 2% increase per year, or the previous bound)
           v_estV.UP(MSEst,"ARTIF","LEVL",exAnte) $ Rest(MSest)
                      = max( v_estV.LO(MSEst,"ARTIF","LEVL",exAnte) * 1.02**(OrdT(ExAnte)) - OrdT("BAS"),
                             v_estV.UP(MSEst,"ARTIF","LEVL",exAnte));

    l. 810's parenthesis (above, setting captrd.artif_upper_bound_as_coded); the sum over the member state's regions is
    the member state's own BASM (the member state's estimation only)."""
    lo = basm if n_obs else 0.0
    cap = lo * 1.02 ** t - ord_bas if as_coded else lo * 1.02 ** (t - ord_bas)
    return lo, max(cap, up)


def V_EstV_fx_land(basm):
    r"""V_EstV.FX of the fixed land uses ARTO, INLW and KITC: their base.

    CAPRI's GAMS (captrd/fix_est.gms l. 814-816):

           v_estV.FX(Rest,"ARTO","LEVL",exAnte) = P_DATA(Rest,"ARTO","LEVL","BASM");
           v_estV.FX(Rest,"INLW","LEVL",exAnte) = P_DATA(Rest,"INLW","LEVL","BASM");
           v_estV.FX(Rest,"KITC","LEVL",exAnte) = P_DATA(Rest,"KITC","LEVL","BASM");

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return basm


def V_EstV_fx_RSET():
    r"""V_EstV.FX of the set-aside activities' levels where the western EU has no set-aside rate: zero.

    CAPRI's GAMS (captrd/fix_est.gms l. 822-822):

            v_estV.fx(REST,RSET,"LEVL",exAnte) $ (not sum((grcu,CurEUWestAgg),p_data(CurEUWestAgg,GRCU,"SETR",ExAnte))) = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return 0.0


def V_EstV_fx_tiny_support():
    r"""V_EstV.FX of a position with a near-zero support and COCO value in the years with data: zero.

    CAPRI's GAMS (captrd/fix_est.gms l. 827-834):

            v_estV.FX(REST,s_colsEst,s_rowsEst,exAnte) $ (    P_Result(Rest,s_colsEst,s_rowsEst,Exante,"SUPPORT")
        *                                           do not interfere with comi_Bounds (as COMI is only completed in coco2)
                                                $ (not (SAMEAS(s_rowsEst,"COMI") or SAMEAS(s_rowsEst,"SUGA")))
                                                $ (ABS(P_Result(Rest,s_colsEst,s_rowsEst,Exante,"SUPPORT")) lt 1e-12)
                                                $ ExAnteD(ExAnte)
                                                $ (ABS(P_Result(Rest,s_colsEst,s_rowsEst,Exante,"coco")) lt 1e-12)
                                                $ P_Result(Rest,s_colsEst,s_rowsEst,Exante,"p_data")
                                                )  = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return 0.0


def V_EstV_lo_SUGB():
    r"""V_EstV.LO of sugar beet's level, EAAG and TOOU where it has no production: zero.

    CAPRI's GAMS (captrd/fix_est.gms l. 849-851):

           v_estV.LO(Rest,"SUGB","LEVL",Exante) $ (v_estV.LO(Rest,"GROF","SUGB",Exante) eq  0) = 0;
           v_estV.LO(Rest,"EAAG","SUGB",Exante) $ (v_estV.LO(Rest,"GROF","SUGB",Exante) eq  0) = 0;
           v_estV.LO(Rest,"SUGB","TOOU",Exante) $ (v_estV.up(Rest,"GROF","SUGB",Exante) eq  0) = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return 0.0
