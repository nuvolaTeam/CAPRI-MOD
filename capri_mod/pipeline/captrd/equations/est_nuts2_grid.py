r"""CAPTRD's bound statements of captrd/est_nuts2_grid.gms (CAPRI star 3.0): the retries' own statements after the bounds are opened (l. 42-121), as named
functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the bounded symbol: V_EstV.LO / .UP / .FX / .L). The functions take the numbers the statement reads
and return the bound; capri_mod/pipeline/captrd/estimate_nuts2.py (_grid_again) holds the
domain conditions, the loops over the regions and the sets and the order of the statements, and calls them. A bound
"before" is the one an earlier statement set (-inf / +inf where none did); the arithmetic is the port's, in its order of
operations, so the bounds are unchanged.
"""
from __future__ import annotations


def V_EstV_l_SUGB_SUGB(lo, up):
    r"""V_EstV.L of sugar beet's yield with data: the middle of its bounds.

    CAPRI's GAMS (captrd/est_nuts2_grid.gms l. 53-54):

                 v_estV.L(Rest,"SUGB","SUGB",exAnte) $ p_data(Rest,"SUGB","SUGB","nObs")
                  = 0.5*v_estV.Lo(Rest,"SUGB","SUGB",exAnte)+0.5*v_estV.UP(Rest,"SUGB","SUGB",exAnte) ;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._grid_again)."""
    return 0.5 * lo + 0.5 * up


def V_EstV_lo_GROF_tries(lo, n):
    r"""V_EstV.LO of sugar beet's and milk's production at its lower bound with a multiplier after 3 tries: x
    (1 - 0.01 n)^n.

    lo: the bound before; n: nRepeatedSolves.

    CAPRI's GAMS (captrd/est_nuts2_grid.gms l. 57-62):

                 v_estV.LO(Rest,"GROF","SUGB",exAnte) $ (    v_estV.M(Rest,"GROF","SUGB",exAnte)
                                                         $ v_estV.L(Rest,"SUGB","SUGB",exAnte)
                                                         $ (v_estV.LO(Rest,"GROF","SUGB",exAnte) eq v_estV.L(Rest,"GROF","SUGB",exAnte))
                                                         $ P_DATA(Rest,"GROF","SUGB","nObs")
                                                         $ (nRepeatedSolves(%REGIOND%) > 3))
                     = v_estV.LO(Rest,"GROF","SUGB",exAnte) * (1 - (0.01 * nRepeatedSolves(%REGIOND%)))**nRepeatedSolves(%REGIOND%);

    CAPRI's GAMS (captrd/est_nuts2_grid.gms l. 96-100):

                 v_estV.LO(Rest,"GROF","COMI",exAnte) $ (v_estV.M(Rest,"GROF","COMI",exAnte)
                                                      $ (v_estV.LO(Rest,"GROF","COMI",exAnte) eq v_estV.L(Rest,"GROF","COMI",exAnte))
                                                      $ P_DATA(Rest,"GROF","COMI","nObs")
                                                      $ (nRepeatedSolves(%REGIOND%) > 3))
                     = v_estV.LO(Rest,"GROF","COMI",exAnte) * (1 - (0.01 * nRepeatedSolves(%REGIOND%)))**nRepeatedSolves(%REGIOND%);

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._grid_again)."""
    return lo * (1 - 0.01 * n) ** n


def V_EstV_up_GROF_tries(up, n):
    r"""V_EstV.UP of sugar beet's and milk's production at its upper bound with a multiplier after 3 tries: x
    (1 + 0.01 n)^n.

    CAPRI's GAMS (captrd/est_nuts2_grid.gms l. 64-69):

                 v_estV.UP(Rest,"GROF","SUGB",exAnte) $ (     v_estV.M(Rest,"GROF","SUGB",exAnte)
                                                         $ v_estV.L(Rest,"SUGB","SUGB",exAnte)
                                                         $ (v_estV.UP(Rest,"GROF","SUGB",exAnte) eq v_estV.L(Rest,"GROF","SUGB",exAnte))
                                                         $ P_DATA(Rest,"GROF","SUGB","nObs")
                                                         $ (nRepeatedSolves(%REGIOND%) > 3))
                     = v_estV.UP(Rest,"GROF","SUGB",exAnte) * (1 + (0.01 * nRepeatedSolves(%REGIOND%)))**nRepeatedSolves(%REGIOND%);

    CAPRI's GAMS (captrd/est_nuts2_grid.gms l. 102-106):

                 v_estV.UP(Rest,"GROF","COMI",exAnte) $ (v_estV.M(Rest,"GROF","COMI",exAnte)
                                                      $ (v_estV.UP(Rest,"GROF","COMI",exAnte) eq v_estV.L(Rest,"GROF","COMI",exAnte))
                                                      $ P_DATA(Rest,"GROF","COMI","nObs")
                                                      $ (nRepeatedSolves(%REGIOND%) > 3))
                     = v_estV.UP(Rest,"GROF","COMI",exAnte) * (1 + (0.01 * nRepeatedSolves(%REGIOND%)))**nRepeatedSolves(%REGIOND%);

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._grid_again)."""
    return up * (1 + 0.01 * n) ** n


def V_EstV_l_GROF_SUGB(quts, step3_ms, quts_ms):
    r"""V_EstV.L of a region's sugar beet production under the quota: its quota's share of the member state's
    production.

    CAPRI's GAMS (captrd/est_nuts2_grid.gms l. 71-76):

                 v_estV.L(Rest,"GROF","SUGB",exAnte) $ (    P_result(MS,"QUTS","SUGB",exAnte,"p_data")
                                                        $ (CALYEA(exAnte) Ge 2006)
                                                        $ v_estV.L(Rest,"SUGB","SUGB",exAnte)
                                                        $ P_DATA(Rest,"GROF","SUGB","nObs"))
                                                    = P_result(Rest,"QUTS","SUGB",exAnte,"p_data") * P_Result(MS,"GROF","SUGB",exAnte,"Step3")
                                                                                        / P_result(MS,"QUTS","SUGB",exAnte,"p_data") ;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._grid_again)."""
    return quts * step3_ms / quts_ms


def V_EstV_SUGB_LEVL(lo_grof, up_grof, l_grof, yl):
    r"""V_EstV.LO, .UP and .L of a region's sugar beet area: its production's over the yield (t per ha).

    lo_grof, up_grof, l_grof: V_EstV.LO / .UP / .L(Rest, "GROF", "SUGB"); yl: V_EstV.L(Rest, "SUGB", "SUGB").
    Returns (lo, up, l).

    CAPRI's GAMS (captrd/est_nuts2_grid.gms l. 78-94):

                 v_estV.UP(Rest,"SUGB","LEVL",exAnte) $ (P_result(MS,"QUTS","SUGB",exAnte,"p_data")
                                                      $ (CALYEA(exAnte) Ge 2006)
                                                      $ v_estV.l(Rest,"SUGB","SUGB",exAnte)
                                                      $ P_DATA(Rest,"SUGB","LEVL","nObs"))
                                                    =  v_estV.UP(Rest,"GROF","SUGB",exAnte) / (v_estV.l(Rest,"SUGB","SUGB",exAnte)/1000) ;

                 v_estV.LO(Rest,"SUGB","LEVL",exAnte) $ (P_result(MS,"QUTS","SUGB",exAnte,"p_data")
                                                      $ (CALYEA(exAnte) Ge 2006)
                                                      $ v_estV.l(Rest,"SUGB","SUGB",exAnte)
                                                      $ P_DATA(Rest,"SUGB","LEVL","nObs"))
                                                    =  v_estV.LO(Rest,"GROF","SUGB",exAnte) / (v_estV.l(Rest,"SUGB","SUGB",exAnte)/1000) ;

                 v_estV.L(Rest,"SUGB","LEVL",exAnte) $ (P_result(MS,"QUTS","SUGB",exAnte,"p_data")
                                                     $ (CALYEA(exAnte) Ge 2006)
                                                     $ v_estV.L(Rest,"SUGB","SUGB",exAnte)
                                                     $ P_DATA(Rest,"SUGB","LEVL","nObs"))
                                                             =  v_estV.L(Rest,"GROF","SUGB",exAnte) / (v_estV.L(Rest,"SUGB","SUGB",exAnte)/1000) ;

    Departures from CAPRI: the port's x 0.001 for CAPRI's / 1000; the domain condition in the caller (estimate_nuts2._grid_again)."""
    return lo_grof / (yl * 0.001), up_grof / (yl * 0.001), l_grof / (yl * 0.001)


def V_EstV_LOSF_STRA():
    r"""V_EstV.LO and .UP of straw's losses: free above zero. Returns (lo, up).

    CAPRI's GAMS (captrd/est_nuts2_grid.gms l. 109-110):

             v_estV.LO(Rest,"LOSF","STRA",exante) = 0;
             v_estV.UP(Rest,"LOSF","STRA",exante) = inf;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._grid_again)."""
    return 0.0, float("inf")


def V_EstV_lo_RSET():
    r"""V_EstV.LO of a set-aside activity's level below 0.01: zero.

    CAPRI's GAMS (captrd/est_nuts2_grid.gms l. 121-121):

                 v_estV.LO(rEst,RSET,"LEVL",exAnte) $ ( (v_estV.LO(rEst,RSET,"LEVL",exAnte) lt 0.01) ) = 0;

    Departures from CAPRI: CAPRI sets it inside if (p_farmModelisRunning eq 1, ...) (l. 112), for the farm types only; the port applies it to
    the NUTS 2 regions too (as it did before this module: a finding, not changed here)."""
    return 0.0
