r"""CAPTRD's bound statements of captrd/release_comi_yields.gms (CAPRI star 3.0): the milk yields' bounds released
step by step after an infeasible solve (estimate_ms.gms l. 371, est_nuts2_grid.gms l. 44), as named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the bounded symbol). capri_mod/pipeline/captrd/estimate_nlp.py (_release_comi) holds the domain
conditions, the binding bounds and the loops, and calls them; the arithmetic is the port's, so the bounds are
unchanged.
"""
from __future__ import annotations


def V_EstV_lo_COMI_release(lo, n):
    r"""V_EstV.LO of a milk yield at its lower bound with a multiplier: x (1 - 1e-4 n)^n.

    lo: the bound before; n: nRepeatedSolves (the tries so far).

    CAPRI's GAMS (captrd/release_comi_yields.gms l. 24-29):

                   V_EstV.LO(Rest,S_ColsEst,"COMI",exAnte) $ (  P_DATA(Rest,S_ColsEst,"COMI","nObs")
                                                              $ v_estV.M(Rest,S_ColsEst,"COMI",exAnte)
                                                              $ (v_estV.LO(Rest,S_ColsEst,"COMI",exAnte) eq v_estV.L(Rest,S_ColsEst,"COMI",exAnte))
                                                              $ PACT_TO_Y(S_ColsEst,"COMI"))

                       = V_EstV.LO(Rest,S_ColsEst,"COMI",exAnte) * (1 - (0.0001 * nRepeatedSolves(%REGIOND%)))**nRepeatedSolves(%REGIOND%);

    Departures from CAPRI: none in the arithmetic; the domain condition, the binding bounds and the loops in the caller
    (estimate_nlp._release_comi)."""
    return lo * (1 - 1.0e-4 * n) ** n


def V_EstV_up_COMI_release(up, n):
    r"""V_EstV.UP of a milk yield at its upper bound with a multiplier: x (1 + 1e-4 n)^n.

    CAPRI's GAMS (captrd/release_comi_yields.gms l. 31-36):

                   V_EstV.UP(Rest,S_ColsEst,"COMI",exAnte) $ (  P_DATA(Rest,S_ColsEst,"COMI","nObs")
                                                              $ v_estV.M(Rest,S_ColsEst,"COMI",exAnte)
                                                              $ (v_estV.UP(Rest,S_ColsEst,"COMI",exAnte) eq v_estV.L(Rest,S_ColsEst,"COMI",exAnte))
                                                              $ PACT_TO_Y(S_ColsEst,"COMI"))

                       = V_EstV.UP(Rest,S_ColsEst,"COMI",exAnte) * (1 + (0.0001 * nRepeatedSolves(%REGIOND%)))**nRepeatedSolves(%REGIOND%);

    Departures from CAPRI: none in the arithmetic; the domain condition, the binding bounds and the loops in the caller
    (estimate_nlp._release_comi)."""
    return up * (1 + 1.0e-4 * n) ** n


def V_EstV_LOSF_COMI_release(lo, up, n):
    r"""V_EstV.UP and .LO of milk's losses with a multiplier after five tries: x 1.005^n and x 0.995^n. Returns
    (lo, up).

    CAPRI's GAMS (captrd/release_comi_yields.gms l. 39-45):

                   v_estV.UP(Rest,"LOSF","COMI",exAnte) $ (p_data(Rest,"LOSF","COMI","nObs")
                                                           and  (nRepeatedSolves(%REGIOND%) gt 5) and v_estV.M(Rest,"LOSF","COMI",exAnte))
                       = v_estV.UP(Rest,"LOSF","COMI",exAnte) * ( 1.005 ** nRepeatedSolves(%REGIOND%) );

                   v_estV.LO(Rest,"LOSF","COMI",exAnte) $ (p_data(Rest,"LOSF","COMI","nObs")
                                                           and  (nRepeatedSolves(%REGIOND%) gt 5) and v_estV.M(Rest,"LOSF","COMI",exAnte))
                       = v_estV.LO(Rest,"LOSF","COMI",exAnte) * ( 0.995 ** nRepeatedSolves(%REGIOND%) );

    Departures from CAPRI: none in the arithmetic; the domain condition, the binding bounds and the loops in the caller
    (estimate_nlp._release_comi)."""
    return lo * 0.995 ** n, up * 1.005 ** n
