r"""CAPTRD's bound statements of captrd/estimate_nuts2.gms (CAPRI star 3.0): the NUTS 2 estimation's own bounds (l. 92-400, after fix_est.gms for the regions), as named
functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the bounded symbol: V_EstV.LO / .UP / .FX / .L). The functions take the numbers the statement reads
and return the bound; capri_mod/pipeline/captrd/estimate_nuts2.py (bounds) holds the
domain conditions, the loops over the regions and the sets and the order of the statements, and calls them. A bound
"before" is the one an earlier statement set (-inf / +inf where none did); the arithmetic is the port's, in its order of
operations, so the bounds are unchanged.
"""
from __future__ import annotations


def V_EstV_up_LEVL(step3_ms, basm_ms, basm, nyr):
    r"""V_EstV.UP of a region's level: the national change applied to its base growing by 1.5% a year, at least
    the base + 0.01.

    the national change applied to the region's base, p_result(MS, c, w, "Step3") / p_data(MS, c, w, "BASM") x
    p_data(Rest, c, w, "BASM"): step3_ms, basm_ms, basm the three; nyr: OrdT(Exante) - OrdT("BAS").

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 95-99):

                 v_estV.UP(Rest,S_ColsEst,"LEVL",exAnte) $ (    p_data(Rest,S_ColsEst,"LEVL","BASM")
                                                            and v_estV.range(Rest,S_ColsEst,"LEVL",exAnte))
                     = MAX(p_result(MS,S_ColsEst,"LEVL",exAnte,"Step3")/p_data(MS,S_ColsEst,"LEVL","BASM") * p_data(Rest,S_ColsEst,"LEVL","BASM")
                                      * (1.015**(OrdT(Exante)-OrdT("BAS"))),
                           p_data(Rest,S_ColsEst,"LEVL","BASM")+0.01);

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2.bounds)."""
    return max(_ratio(step3_ms, basm_ms, basm) * 1.015 ** nyr, basm + 0.01)


def V_EstV_up_GRPC(ups):
    r"""V_EstV.UP of a crop group's level: its crops' upper bounds (those with data) x 1.01.

    ups: V_EstV.UP(Rest, crop, "LEVL") of the group's crops with level data, in the caller's order.

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 101-102):

                 v_estV.UP(Rest,Grpc,"LEVL",exAnte) $ p_data(Rest,Grpc,"LEVL","BASM")
                            = SUM(CROPC_TO_G(MCACT,GRPC) $ p_data(Rest,MCACT,"LEVL","nObs"), v_estV.UP(Rest,MCACT,"LEVL",exAnte)) * 1.01;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2.bounds)."""
    return sum(ups) * 1.01


def V_EstV_up_LEVL_expert(up, expert):
    r"""V_EstV.UP of a region's level with an expert level: at least the expert's + 0.01.

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 105-109):

                 v_estV.UP(Rest,S_ColsEst,"LEVL",exAnte) $ (    p_data(Rest,S_ColsEst,"LEVL","BASM")
                                                            and v_estV.range(Rest,S_ColsEst,"LEVL",exAnte)
                                                            and p_result(Rest,S_ColsEst,"LEVL",exAnte,"Expert"))
                     = MAX(v_estV.UP(Rest,S_ColsEst,"LEVL",exAnte),
                           p_result(Rest,S_ColsEst,"LEVL",exAnte,"Expert")+0.01);

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2.bounds)."""
    return max(up, expert + 0.01)


def V_EstV_lo_LEVL(step3_ms, basm_ms, basm, nyr):
    r"""V_EstV.LO of a region's level: at most its base - 0.01 (at least 1e-10) and the national change applied
    to the base falling by 1.5% a year.

    the national change applied to the region's base, p_result(MS, c, w, "Step3") / p_data(MS, c, w, "BASM") x
    p_data(Rest, c, w, "BASM"): step3_ms, basm_ms, basm the three; nyr: OrdT(Exante) - OrdT("BAS").

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 111-115):

                 v_estV.LO(Rest,S_ColsEst,"LEVL",exAnte) $ (    p_data(Rest,S_ColsEst,"LEVL","BASM")
                                                            and v_estV.range(Rest,S_ColsEst,"LEVL",exAnte))
                     = MIN(MAX(1.E-10,p_data(Rest,S_ColsEst,"LEVL","BASM")-0.01),
                           p_result(MS,S_ColsEst,"LEVL",exAnte,"Step3")/p_data(MS,S_ColsEst,"LEVL","BASM") * p_data(Rest,S_ColsEst,"LEVL","BASM")
                           * (0.985**(OrdT(Exante)-OrdT("BAS"))));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2.bounds)."""
    return min(max(1.0e-10, basm - 0.01), _ratio(step3_ms, basm_ms, basm) * 0.985 ** nyr)


def V_EstV_lo_LEVL_expert(lo, expert):
    r"""V_EstV.LO of a region's level with an expert level: at most the expert's - 0.01.

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 118-122):

                 v_estV.LO(Rest,S_ColsEst,"LEVL",exAnte) $ (    p_data(Rest,S_ColsEst,"LEVL","BASM")
                                                            and v_estV.range(Rest,S_ColsEst,"LEVL",exAnte)
                                                            and p_result(Rest,S_ColsEst,"LEVL",exAnte,"Expert"))
                     = MIN(v_estV.LO(Rest,S_ColsEst,"LEVL",exAnte),
                           p_result(Rest,S_ColsEst,"LEVL",exAnte,"Expert")-0.01);

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2.bounds)."""
    return min(lo, expert - 0.01)


def V_EstV_lo_GRPC(los):
    r"""V_EstV.LO of a crop group's level: its crops' lower bounds (those with data) x 0.99.

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 124-125):

                 v_estV.LO(Rest,Grpc,"LEVL",exAnte) $ p_data(Rest,Grpc,"LEVL","BASM")
                            = SUM(CROPC_TO_G(MCACT,GRPC) $ p_data(Rest,MCACT,"LEVL","nObs"), v_estV.LO(Rest,MCACT,"LEVL",exAnte)) * 0.99;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2.bounds)."""
    return sum(los) * 0.99


def V_EstV_up_IO(lo, up, step3_ms, basm_ms, basm, nyr):
    r"""V_EstV.UP of a region's input or output coefficient (not a feed, not straw): the national change applied
    to the base growing by 2% a year, at least 1.001 x it and the bound before + 0.1, at least the lower bound + 0.1.

    lo, up: the bounds before (-inf / +inf where none); the national change applied to the region's base, p_result(MS, c, w, "Step3") / p_data(MS, c, w, "BASM") x
    p_data(Rest, c, w, "BASM"): step3_ms, basm_ms, basm the three; nyr: OrdT(Exante) - OrdT("BAS").

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 131-143):

                 v_estV.UP(Rest,MPACT,S_RowsEst,exAnte) $ (p_data(MS,MPACT,S_RowsEst,"BASM") and p_data(Rest,MPACT,S_RowsEst,"BASM")
                                    and PACT_TO_IO(MPACT,S_RowsEst)  and (NOT SUM(SAMEAS(FEED,S_RowsEst),1)) and (NOT SAMEAS(S_RowsEst,"STRA")))
                     = MAX(v_estV.LO(Rest,MPACT,S_RowsEst,exAnte)+0.1,
        *
        *               -- ensure that the change projected at Member State level can be applied at NUTS 2 level as well
        *
                         MIN(MAX(v_estV.UP(Rest,MPACT,S_RowsEst,exAnte)+0.1,
                               p_result(MS,MPACT,S_RowsEst,exAnte,"Step3")/p_data(MS,MPACT,S_RowsEst,"BASM") * p_data(Rest,MPACT,S_RowsEst,"BASM")*1.001),
        *
        *                 -- relative change projected at Member State level, plus 2% corridor per year
        *
                                  p_result(MS,MPACT,S_RowsEst,exAnte,"Step3")/p_data(MS,MPACT,S_RowsEst,"BASM") * p_data(Rest,MPACT,S_RowsEst,"BASM")
                                                                                                                   * (1.02**(OrdT(Exante)-OrdT("BAS")))));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2.bounds)."""
    return max(lo + 0.1, min(max(up + 0.1, _ratio(step3_ms, basm_ms, basm) * 1.001),
                             _ratio(step3_ms, basm_ms, basm) * 1.02 ** nyr))


def V_EstV_FSTR(bas_ms, step3_ms, bas, up):
    r"""V_EstV.LO and .UP of the straw feed of an animal activity where the member state feeds straw and the
    region produces it: from zero to the largest of the member state's base and result, the region's base and the
    bound before.

    bas_ms, step3_ms: p_data(MS, a, "FSTR", "BAS"), p_result(MS, a, "FSTR", "Step3"); bas: p_data(Rest, a, "FSTR",
    "BAS"); up: the bound before (+inf where none: then 0, as CAPRI's $ (ne inf)). Returns (lo, up).

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 145-155):

                 p_data(Rest,MAACT,"FSTR","nObs") $ ( (     p_data(MS,MAACT,"FSTR","BAS") or p_result(MS,MAACT,"FSTR",exAnte,"Step3"))
                                                        and p_data(Rest,"GROF","STRA","BAS")) = 1;

                 v_estV.UP(Rest,MAACT,"FSTR",exAnte) $ (     (p_data(MS,MAACT,"FSTR","BAS") or p_result(MS,MAACT,"FSTR",exAnte,"Step3"))
                                                          and p_data(Rest,"GROF","STRA","BAS"))
                     = MAX(p_data(MS,MAACT,"FSTR","BAS"),p_result(MS,MAACT,"FSTR",exAnte,"Step3"),
                           p_data(Rest,MAACT,"FSTR","BAS"),v_estV.UP(Rest,MAACT,"FSTR",exAnte) $ (v_estV.UP(Rest,MAACT,"FSTR",exAnte) ne inf));

                 v_estV.LO(Rest,MAACT,"FSTR",exAnte) $ (    (p_data(MS,MAACT,"FSTR","BAS") or p_result(MS,MAACT,"FSTR",exAnte,"Step3"))
                                                         and p_data(Rest,"GROF","STRA","BAS"))
                     = 0;

    Departures from CAPRI: the observation flag (l. 145-146) the caller adds to the region's data (new_nobs); the domain condition in the caller
    (estimate_nuts2.bounds)."""
    return 0.0, max(bas_ms, step3_ms, bas, up if up < float("inf") else 0.0)


def V_EstV_lo_IO(lo, up, step3_ms, basm_ms, basm):
    r"""V_EstV.LO of a region's input or output coefficient (not a feed): at least 80% of the national change
    applied to the base, at most 0.999 x it and the bound before - 0.1, at most the upper bound - 0.1.

    lo, up: the bounds before; the national change applied to the region's base, p_result(MS, c, w, "Step3") / p_data(MS, c, w, "BASM") x
    p_data(Rest, c, w, "BASM"): step3_ms, basm_ms, basm the three.

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 160-165):

                 v_estV.LO(Rest,MPACT,S_RowsEst,exAnte) $ (p_data(MS,MPACT,S_RowsEst,"BASM") and p_data(Rest,MPACT,S_RowsEst,"BASM")
                                    and PACT_TO_IO(MPACT,S_RowsEst)  and (NOT SUM(SAMEAS(FEED,S_RowsEst),1)))
                     =  MIN(v_estV.UP(Rest,MPACT,S_RowsEst,exAnte)-0.1,
                            MAX(MIN(v_estV.LO(Rest,MPACT,S_RowsEst,exAnte)-0.1,
                                 p_result(MS,MPACT,S_RowsEst,exAnte,"Step3")/p_data(MS,MPACT,S_RowsEst,"BASM") * p_data(Rest,MPACT,S_RowsEst,"BASM")*0.999),
                               p_result(MS,MPACT,S_RowsEst,exAnte,"Step3")/p_data(MS,MPACT,S_RowsEst,"BASM") * p_data(Rest,MPACT,S_RowsEst,"BASM")*0.8));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2.bounds)."""
    return min(up - 0.1, max(min(lo - 0.1, _ratio(step3_ms, basm_ms, basm) * 0.999),
                             _ratio(step3_ms, basm_ms, basm) * 0.8))


def V_EstV_NoYieldDrop(step3_ms, basm_ms, basm, nyr):
    r"""V_EstV.LO and .UP of a region's yield that may not fall: the national change applied to its base, x
    min(0.98, 0.995^n) and x max(1.02, 1.005^n).

    the national change applied to the region's base, p_result(MS, c, w, "Step3") / p_data(MS, c, w, "BASM") x
    p_data(Rest, c, w, "BASM"): step3_ms, basm_ms, basm the three; nyr: OrdT(Exante) - OrdT("BAS"). Returns (lo, up).

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 169-177):

                 v_estV.LO(Rest,MPACT,S_RowsEst,exAnte) $ (p_data(MS,MPACT,S_RowsEst,"BASM") and p_data(Rest,MPACT,S_RowsEst,"BASM")
                                    and PACT_TO_Y(MPACT,S_RowsEst)  and noYieldDrop(MPACT))
                     = (p_result(MS,MPACT,S_RowsEst,exAnte,"Step3")/p_data(MS,MPACT,S_RowsEst,"BASM") * p_data(Rest,MPACT,S_RowsEst,"BASM"))
                                                                                                        * MIN(0.98,0.995**(OrdT(Exante)-OrdT("BAS")));

                 v_estV.UP(Rest,MPACT,S_RowsEst,exAnte) $ (p_data(MS,MPACT,S_RowsEst,"BASM") and p_data(Rest,MPACT,S_RowsEst,"BASM")
                                    and PACT_TO_Y(MPACT,S_RowsEst)  and noYieldDrop(MPACT))
                     = (p_result(MS,MPACT,S_RowsEst,exAnte,"Step3")/p_data(MS,MPACT,S_RowsEst,"BASM") * p_data(Rest,MPACT,S_RowsEst,"BASM"))
                                                                                                            * MAX(1.02,1.005**(OrdT(Exante)-OrdT("BAS")));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2.bounds)."""
    r = _ratio(step3_ms, basm_ms, basm)
    return r * min(0.98, 0.995 ** nyr), _ratio(step3_ms, basm_ms, basm) * max(1.02, 1.005 ** nyr)


def V_EstV_lo_floor(lo):
    r"""V_EstV.LO of a region's position the member state has positive: at least 1e-10 (set twice by CAPRI).

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 182-184):

                 v_estV.LO(Rest,MPACT,S_RowsEst,exAnte) $ (   (p_data(MS,MPACT,S_RowsEst,"BASM") GT 0)
                                                            $ p_data(Rest,MPACT,S_RowsEst,"nObs"))
                    = MAX(1.E-10,v_estV.LO(Rest,MPACT,S_RowsEst,exAnte));

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 222-225):

                 v_estV.LO(Rest,MPACT,S_RowsEst,exAnte) $ ( ( p_data(MS,MPACT,S_RowsEst,"BASM") GT 0)
                                                          $ p_result(MS,MPACT,S_RowsEst,exAnte,"Step3")
                                                          $ p_data(Rest,MPACT,S_RowsEst,"nObs"))
                    = MAX(1.E-10,v_estV.LO(Rest,MPACT,S_RowsEst,exAnte));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2.bounds)."""
    return max(1.0e-10, lo)


def V_EstV_lo_zero():
    r"""V_EstV.LO of a feed the member state feeds and the region has no base for, and of a position the member
    state's result has zero: zero.

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 186-187):

                 v_estV.LO(Rest,MPACT,FEED,exAnte) $ ( (p_data(MS,MPACT,FEED,"BAS") GT 0) and (not p_data(Rest,MPACT,FEED,"BAS"))) = 0;
                 v_estV.LO(Rest,MPACT,S_RowsEst,exAnte) $ (  p_result(MS,MPACT,S_RowsEst,exAnte,"Step3") eq 0)                               = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2.bounds)."""
    return 0.0


def V_EstV_MEAT_EGGS(step3_ms, basm_ms, basm):
    r"""V_EstV.LO and .UP of the regions' meat and egg outputs (PORK, BEEF, POUM, SGMT, EGGS): almost fixed at the
    national change applied to the base (x 0.999 - 0.1, x 1.001 + 0.1).

    the national change applied to the region's base, p_result(MS, c, w, "Step3") / p_data(MS, c, w, "BASM") x
    p_data(Rest, c, w, "BASM"): step3_ms, basm_ms, basm the three. Returns (lo, up).

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 192-220):

                 v_estV.LO(Rest,MAACT,"PORK",exAnte) $ p_data(Rest,MAACT,"PORK","nObs")
                   =  p_result(MS,MAACT,"PORK",exAnte,"Step3")/p_data(MS,MAACT,"PORK","BASM") * p_data(Rest,MAACT,"PORK","BASM")*0.999-0.1;
        *
                 v_estV.LO(Rest,MAACT,"BEEF",exAnte) $ p_data(Rest,MAACT,"BEEF","nObs")
                   =  p_result(MS,MAACT,"BEEF",exAnte,"Step3")/p_data(MS,MAACT,"BEEF","BASM") * p_data(Rest,MAACT,"BEEF","BASM")*0.999-0.1;
        *
                 v_estV.LO(Rest,MAACT,"POUM",exAnte) $ p_data(Rest,MAACT,"POUM","nObs")
                   =  p_result(MS,MAACT,"POUM",exAnte,"Step3")/p_data(MS,MAACT,"POUM","BASM") * p_data(Rest,MAACT,"POUM","BASM")*0.999-0.1;
        *
                 v_estV.LO(Rest,MAACT,"SGMT",exAnte) $ p_data(Rest,MAACT,"SGMT","nObs")
                   =  p_result(MS,MAACT,"SGMT",exAnte,"Step3")/p_data(MS,MAACT,"SGMT","BASM") * p_data(Rest,MAACT,"SGMT","BASM")*0.999-0.1;
        *
                 v_estV.LO(Rest,MAACT,"EGGS",exAnte) $ p_data(Rest,MAACT,"EGGS","nObs")
                   =  p_result(MS,MAACT,"EGGS",exAnte,"Step3")/p_data(MS,MAACT,"EGGS","BASM") * p_data(Rest,MAACT,"EGGS","BASM")*0.999-0.1;

                 v_estV.UP(Rest,MAACT,"PORK",exAnte) $ p_data(Rest,MAACT,"PORK","nObs")
                   =  p_result(MS,MAACT,"PORK",exAnte,"Step3")/p_data(MS,MAACT,"PORK","BASM") * p_data(Rest,MAACT,"PORK","BASM")*1.001+0.1;
        *
                 v_estV.UP(Rest,MAACT,"BEEF",exAnte) $ p_data(Rest,MAACT,"BEEF","nObs")
                   =  p_result(MS,MAACT,"BEEF",exAnte,"Step3")/p_data(MS,MAACT,"BEEF","BASM") * p_data(Rest,MAACT,"BEEF","BASM")*1.001+0.1;
        *
                 v_estV.UP(Rest,MAACT,"POUM",exAnte) $ p_data(Rest,MAACT,"POUM","nObs")
                   =  p_result(MS,MAACT,"POUM",exAnte,"Step3")/p_data(MS,MAACT,"POUM","BASM") * p_data(Rest,MAACT,"POUM","BASM")*1.001+0.1;
        *
                 v_estV.UP(Rest,MAACT,"SGMT",exAnte) $ p_data(Rest,MAACT,"SGMT","nObs")
                   =  p_result(MS,MAACT,"SGMT",exAnte,"Step3")/p_data(MS,MAACT,"SGMT","BASM") * p_data(Rest,MAACT,"SGMT","BASM")*1.001+0.1;
        *
                 v_estV.UP(Rest,MAACT,"EGGS",exAnte) $ p_data(Rest,MAACT,"EGGS","nObs")
                   =  p_result(MS,MAACT,"EGGS",exAnte,"Step3")/p_data(MS,MAACT,"EGGS","BASM") * p_data(Rest,MAACT,"EGGS","BASM")*1.001+0.1;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2.bounds)."""
    return (_ratio(step3_ms, basm_ms, basm) * 0.999 - 0.1, _ratio(step3_ms, basm_ms, basm) * 1.001 + 0.1)


def V_EstV_fx_no_ms_level():
    r"""V_EstV.FX of an activity's positions where the member state's result has no level: zero (set twice).

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 229-230):

                 v_estV.FX(Rest,MPACT,S_RowsEst,exAnte) $ (p_data(Rest,MPACT,S_RowsEst,"nobs")
                                      and (NOT SUM(RaggEst, p_result(RaggEst,MPACT,"LEVL",exAnte,"Step3")))) = 0;

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 368-369):

                 v_estV.FX(Rest,MPACT,S_RowsEst,exAnte) $ (p_data(Rest,MPACT,S_RowsEst,"nobs")
                                                           and (NOT SUM(RaggEst, p_result(RaggEst,MPACT,"LEVL",exAnte,"Step3")))) = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2.bounds)."""
    return 0.0


def V_EstV_GROF(terms):
    r"""V_EstV.LO and .UP of a region's production from its activities' levels' and coefficients' bounds: the
    level bound the coefficient's sign picks times the coefficient's bound, x 0.99 or x 1.01, in t (+1 above).

    terms: (V_EstV.LO, .UP of the level, V_EstV.LO, .UP of the coefficient) of the activities with data producing
    or using the row, in the caller's order. Returns (lo, up).

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 234-253):

                 v_estV.LO(Rest,"GROF",S_RowsEst,exante)
                       $ SUM(MPACT $ (PACT_TO_IO(MPACT,S_RowsEst) AND p_data(Rest,MPACT,S_RowsEst,"nObs") and p_data(Rest,MPACT,"LEVL","nObs")),1)
                       = SUM(MPACT $ (PACT_TO_IO(MPACT,S_RowsEst) AND p_data(Rest,MPACT,S_RowsEst,"nObs") and p_data(Rest,MPACT,"LEVL","nObs")),
                                              (   MIN(v_estV.LO(Rest,MPACT,"LEVL",exAnte),v_estV.UP(Rest,MPACT,"LEVL",exAnte))
                                                      $ (v_estV.LO(Rest,MPACT,S_RowsEst,exAnte) GT 0)
                                                + MAX(v_estV.LO(Rest,MPACT,"LEVL",exAnte),v_estV.UP(Rest,MPACT,"LEVL",exAnte))
                                                      $ (v_estV.LO(Rest,MPACT,S_RowsEst,exAnte) LT 0))
                                                  * v_estV.LO(Rest,MPACT,S_RowsEst,exAnte)
                                                   * (   0.99 $ (v_estV.LO(Rest,MPACT,S_RowsEst,exAnte) GT 0)
                                                       + 1.01 $ (v_estV.LO(Rest,MPACT,S_RowsEst,exAnte) LT 0)))/1000.;
        *
                 v_estV.UP(Rest,"GROF",S_RowsEst,exante)
                       $ SUM(MPACT $ (PACT_TO_IO(MPACT,S_RowsEst) AND p_data(Rest,MPACT,S_RowsEst,"nObs") and p_data(Rest,MPACT,"LEVL","nObs")),1)
                       = SUM(MPACT $ (PACT_TO_IO(MPACT,S_RowsEst) AND p_data(Rest,MPACT,S_RowsEst,"nObs") and p_data(Rest,MPACT,"LEVL","nObs")),
                                              (   MAX(v_estV.LO(Rest,MPACT,"LEVL",exAnte),v_estV.UP(Rest,MPACT,"LEVL",exAnte))
                                                     $ (v_estV.LO(Rest,MPACT,S_RowsEst,exAnte) GT 0)
                                                + MIN(v_estV.LO(Rest,MPACT,"LEVL",exAnte),v_estV.UP(Rest,MPACT,"LEVL",exAnte))
                                                     $ (v_estV.LO(Rest,MPACT,S_RowsEst,exAnte) LT 0))
                                                  * v_estV.UP(Rest,MPACT,S_RowsEst,exAnte)  * (   0.99 $ (v_estV.LO(Rest,MPACT,S_RowsEst,exAnte) LT 0)
                                                                                            + 1.01 $ (v_estV.LO(Rest,MPACT,S_RowsEst,exAnte) GT 0)))/1000. + 1;

    Departures from CAPRI: the products are GAMS's (zero where a factor is zero, also against an infinite bound: _gmul); the port's x 0.001 for
    CAPRI's / 1000 may differ in the last digit; the domain condition and the activities in the caller
    (estimate_nuts2.bounds)."""
    lsum, usum = _grof_sums(terms)
    return lsum * 0.001, usum * 0.001 + 1.0


def V_EstV_up_GROF_fodder(up, ups):
    r"""V_EstV.UP of a fodder's production (FODDI or FODDO): at least the summed upper bounds of its linked
    fodder (FEED_TO_O).

    up: the bound before; ups: the linked fodder's upper bounds, in the caller's order.

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 260-263):

                 v_estV.UP(Rest,"GROF",FODDI,exAnte)
                    = MAX(v_estV.UP(Rest,"GROF",FODDI,exAnte),SUM(FEED_TO_O(FODDI,FODDO), v_estV.UP(Rest,"GROF",FODDO,exAnte)));
                 v_estV.UP(Rest,"GROF",FODDO,exAnte)
                    = MAX(v_estV.UP(Rest,"GROF",FODDO,exAnte),SUM(FEED_TO_O(FODDI,FODDO), v_estV.UP(Rest,"GROF",FODDI,exAnte)));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2.bounds)."""
    return max(up, sum(ups))


def V_EstV_lo_GROF_fodder(lo, los):
    r"""V_EstV.LO of a fodder's production: at most the summed lower bounds of its linked fodder.

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 265-268):

                 v_estV.LO(Rest,"GROF",FODDI,exAnte)
                    = MIN(v_estV.LO(Rest,"GROF",FODDI,exAnte),SUM(FEED_TO_O(FODDI,FODDO), v_estV.LO(Rest,"GROF",FODDO,exAnte)));
                 v_estV.LO(Rest,"GROF",FODDO,exAnte)
                    = MIN(v_estV.LO(Rest,"GROF",FODDO,exAnte),SUM(FEED_TO_O(FODDI,FODDO), v_estV.LO(Rest,"GROF",FODDI,exAnte)));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2.bounds)."""
    return min(lo, sum(los))


def V_EstV_lo_LOSF(lo_grof, losf_ms, grof_ms):
    r"""V_EstV.LO of a fodder's losses: 90% of its production's lower bound at the member state's loss rate.

    lo_grof: V_EstV.LO(Rest, "GROF", x); losf_ms, grof_ms: ESTP(MS, "LOSF" / "GROF", x) (the rate zero where
    GROF is).

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 276-279):

                 v_estV.LO(Rest,"LOSF",losfFromCoco2,exAnte) $ ((v_estV.LO(Rest,"GROF",losfFromCoco2,exAnte) gt 0))
                    = .9 * v_estV.LO(Rest,"GROF",losfFromCoco2,exAnte)
                    * SUM(MSEst $ ESTP(MSEst,"GROF",losfFromCoco2,exAnte),
                                   ESTP(MSEST,"LOSF",losfFromCoco2,exAnte)/ESTP(MSEst,"GROF",losfFromCoco2,exAnte));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2.bounds)."""
    rate = losf_ms / grof_ms if grof_ms else 0.0
    return 0.9 * lo_grof * rate


def V_EstV_up_LOSF(up_grof, losf_ms, grof_ms):
    r"""V_EstV.UP of a fodder's losses: 110% of its production's upper bound at the member state's loss rate.

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 281-285):

                 v_estV.UP(Rest,"LOSF",losfFromCoco2,exAnte) $ (   (v_estV.UP(Rest,"GROF",losfFromCoco2,exAnte) gt 0)
                                                         $ (v_estV.UP(Rest,"GROF",losfFromCoco2,exAnte) lt inf)  )
                    = 1.1 * v_estV.UP(Rest,"GROF",losfFromCoco2,exAnte)
                    * SUM(MSEst $ ESTP(MSEst,"GROF",losfFromCoco2,exAnte),
                                   ESTP(MSEST,"LOSF",losfFromCoco2,exAnte)/ESTP(MSEst,"GROF",losfFromCoco2,exAnte));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2.bounds)."""
    rate = losf_ms / grof_ms if grof_ms else 0.0
    return 1.1 * up_grof * rate


def V_EstV_l_SUGB_SUGB(lo, up):
    r"""V_EstV.L of sugar beet's yield: the middle of its bounds.

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 292-292):

                 v_estV.L(Rest,"SUGB","SUGB",exAnte) = 0.5*v_estV.Lo(Rest,"SUGB","SUGB",exAnte)+0.5*v_estV.UP(Rest,"SUGB","SUGB",exAnte) ;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2.bounds)."""
    return 0.5 * lo + 0.5 * up


def V_EstV_GROF_SUGB(quts, step3_ms, quts_ms, expert, trust):
    r"""V_EstV.LO and .UP of a region's sugar beet production under the quota (from 2006): its quota's share of
    the member state's production x 0.95 and x 1.05, or the regional expert's x 0.9 / x 1.1 where trusted above 4.

    quts, quts_ms: p_result(Rest / MS, "QUTS", "SUGB", "p_data"); step3_ms: p_result(MS, "GROF", "SUGB", "Step3");
    expert, trust: the region's Expert and its p_ExpertSupprt TrustLevl. Returns (lo, up).

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 294-311):

                 v_estV.UP(Rest,"GROF","SUGB",exAnte) $ (p_result(MS,"QUTS","SUGB",exAnte,"p_data") and p_data(Rest,"GROF","SUGB","nObs")
                                                         and (CALYEA(exAnte) Ge 2006))
                    = max(
        *                  --- quota share x over-quota production at MS level  +5%
                                                p_result(Rest,"QUTS","SUGB",exAnte,"p_data") * p_result(MS,"GROF","SUGB",exAnte,"Step3")
                                                         / p_result(MS,"QUTS","SUGB",exAnte,"p_data")            *1.05,
        *                   --- OR the regional expert supports on GROF (if any) + 10%
                            (p_result(Rest,'GROF','SUGB',Exante,'Expert') * 1.1) $ (p_ExpertSupprt(Rest,'GROF','SUGB',Exante,'TrustLevl') gt 4));


                 v_estV.LO(Rest,"GROF","SUGB",exAnte) $ (p_result(MS,"QUTS","SUGB",exAnte,"p_data") and p_data(Rest,"GROF","SUGB","nObs")
                                                         and (CALYEA(exAnte) Ge 2006) )
                    = min(
        *                  --- quota share x over-quota production at MS level        - 5%
                                                p_result(Rest,"QUTS","SUGB",exAnte,"p_data") * p_result(MS,"GROF","SUGB",exAnte,"Step3")
                                                         / p_result(MS,"QUTS","SUGB",exAnte,"p_data")            *0.95,
        *                   --- OR the regional expert supports on GROF (if any) - 10%
                            (p_result(Rest,'GROF','SUGB',Exante,'Expert') * .9) $ (p_ExpertSupprt(Rest,'GROF','SUGB',Exante,'TrustLevl') gt 4));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2.bounds)."""
    share = quts * step3_ms / quts_ms
    up = max(share * 1.05, (expert * 1.1) if trust > 4.0 else 0.0)
    lo = min(share * 0.95, (expert * 0.9) if trust > 4.0 else 0.0)
    return lo, up


def V_EstV_SUGB_LEVL(lo_grof, up_grof, yl):
    r"""V_EstV.LO and .UP of a region's sugar beet area: its production's bounds over the yield (t per ha).

    lo_grof, up_grof: V_EstV.LO / .UP(Rest, "GROF", "SUGB"); yl: V_EstV.L(Rest, "SUGB", "SUGB"). Returns (lo, up).

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 319-328):

                 v_estV.UP(Rest,"SUGB","LEVL",exAnte) $ (p_result(MS,"QUTS","SUGB",exAnte,"p_data") and p_data(Rest,"SUGB","LEVL","nObs")
                                                         and v_estV.L(Rest,"SUGB","SUGB",exAnte)
                                                         and (CALYEA(exAnte) Ge 2006))
                    =  v_estV.UP(Rest,"GROF","SUGB",exAnte) / (v_estV.l(Rest,"SUGB","SUGB",exAnte)/1000) ;


                 v_estV.LO(Rest,"SUGB","LEVL",exAnte) $ (p_result(MS,"QUTS","SUGB",exAnte,"p_data") and p_data(Rest,"SUGB","LEVL","nObs")
                                                         and v_estV.L(Rest,"SUGB","SUGB",exAnte)
                                                         and (CALYEA(exAnte) Ge 2006))
                    =  v_estV.LO(Rest,"GROF","SUGB",exAnte) / (v_estV.L(Rest,"SUGB","SUGB",exAnte)/1000) ;

    Departures from CAPRI: the levels CAPRI sets alongside (V_EstV.L of GROF and the area, l. 314-316, 331-334) are the start point's, not set
    here; the expert yield of l. 338-348 (p_ExpertSupprt "Absolute", not in the stored results) not ported (the caller
    stops where it would apply); the port's x 0.001 for CAPRI's / 1000."""
    return lo_grof / (yl * 0.001), up_grof / (yl * 0.001)


def V_EstV_lo_ARTIF(basm, step3_ms, basm_ms, arto, inlw, lo_uaar):
    r"""V_EstV.LO of a region's artificial land: the national change applied to its base, then 99% of the
    smaller of it and the land left beside the total area's inland waters and UAAR's lower bound.

    basm, basm_ms: P_DATA(Rest / MS, "ARTIF", "LEVL", "BASM"); step3_ms: P_Result(MS, "ARTIF", "LEVL", "Step3");
    arto, inlw: P_DATA(Rest, "ARTO" / "INLW", "LEVL", "BASM"); lo_uaar: V_EstV.LO(Rest, "UAAR", "LEVL"). Returns
    (the first statement's bound, the second's).

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 354-355):

                  v_estV.LO(Rest,"ARTIF","LEVL",exAnte)$(P_DATA(MS,"ARTIF","LEVL","BASM") and MAP_RR(MS,REST)) =
                  P_DATA(Rest,"ARTIF","LEVL","BASM") * [p_result(MS,"ARTIF","LEVL",Exante,"step3")/P_DATA(MS,"ARTIF","LEVL","BASM")] ;

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 361-366):

                 v_estV.LO(REST,"ARTIF","LEVL",exAnte) = .99 *min( P_DATA(REST,"ARTIF","LEVL","BASM")
                                                                 *P_Result(MS,"ARTIF","LEVL",ExAnte,"Step3")
                                                                 /P_DATA(MS,"ARTIF","LEVL","BASM"),
                                                                  P_DATA(REST,"ARTO","LEVL","BASM")
                                                                 -P_DATA(Rest,"INLW","LEVL","BASM")
                                                                 -v_estV.lo(Rest,"UAAR","LEVL",exAnte))    ;

    Departures from CAPRI: both statements only where the member state's base is nonzero (CAPRI's second has no condition and would divide by
    zero); the domain condition in the caller (estimate_nuts2.bounds)."""
    return basm * step3_ms / basm_ms, 0.99 * min(basm * step3_ms / basm_ms, arto - inlw - lo_uaar)


def V_EstV_expert(expert):
    r"""V_EstV.LO or .UP of a region's position with an expert bound: the expert's, as a last resort.

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 377-380):

                 v_estV.lo(rEst,S_ColsEst,S_RowsEst,Exante) $ p_result(rEst,S_ColsEst,S_RowsEst,exAnte,"expertlo")
                    = p_result(rEst,S_ColsEst,S_RowsEst,exAnte,"expertlo") ;
                 v_estV.up(rEst,S_ColsEst,S_RowsEst,Exante) $ p_result(rEst,S_ColsEst,S_RowsEst,exAnte,"expertup")
                    = p_result(rEst,S_ColsEst,S_RowsEst,exAnte,"expertup") ;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2.bounds)."""
    return expert


def V_EstV_LOSF_STRA():
    r"""V_EstV.LO and .UP of straw's losses: free above zero (with an observation flag). Returns (lo, up).

    CAPRI's GAMS (captrd/estimate_nuts2.gms l. 398-400):

                 p_data(Rest,"LOSF","STRA","nObs") = 1;
                 v_estV.LO(Rest,"LOSF","STRA",exante) = 0;
                 v_estV.UP(Rest,"LOSF","STRA",exante) = inf;

    Departures from CAPRI: the observation flag (l. 398) the caller adds to the region's data (new_nobs)."""
    return 0.0, float("inf")


def _ratio(step3_ms, basm_ms, basm):
    """The national change applied to the region's base: Step3(MS) / BASM(MS) x BASM(region), 0 where BASM(MS) is."""
    return step3_ms / basm_ms * basm if basm_ms else 0.0


def _gmul(x, y):
    """GAMS's product: zero if either factor is zero (also against an infinite bound)."""
    return 0.0 if (x == 0 or y == 0) else x * y


def _grof_sums(terms):
    """The sums of l. 234-253 (and est_Nuts2_grid_openbound.gms l. 204-237) over (level lo, level up, coefficient lo,
    coefficient up): the level bound the coefficient's lower bound's sign picks, times the coefficient's bound, x 0.99
    or x 1.01."""
    lsum, usum = 0.0, 0.0
    for ll, ul, lc, uc in terms:
        lv = (min(ll, ul) if lc > 0 else 0.0) + (max(ll, ul) if lc < 0 else 0.0)
        lsum += _gmul(_gmul(lv, lc), (0.99 if lc > 0 else 0.0) + (1.01 if lc < 0 else 0.0))
        uv = (max(ll, ul) if lc > 0 else 0.0) + (min(ll, ul) if lc < 0 else 0.0)
        usum += _gmul(_gmul(uv, uc), (0.99 if lc < 0 else 0.0) + (1.01 if lc > 0 else 0.0))
    return lsum, usum
