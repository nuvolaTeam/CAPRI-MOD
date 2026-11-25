r"""CAPRI's N exported with the animals' products (fert/calc_nexport.gms, star 3.0): the N in the cow milk, which the
projection layer adds to a dairy cow's N export per head when its milk yield is projected
(ProjectionModule._project_livestock).
"""
from __future__ import annotations


def CRPR_EXPT_COMI(COMI):
    r"""The cow milk's term of a ruminant's N export per head (CRPR_EXPT), 0.0054 kg N per kg of cow milk COMI (CAPRI's
    0.0054, from FAO 2018's protein content).

    CAPRI's GAMS (fert/calc_nexport.gms l. 44):

                                    + (DATA(RS,MRUMI,"COMI",%yr%) * 0.0054) $ PACT_TO_O(MRUMI,"COMI")

    In this project's notation: N_milk = 0.0054 x COMI. Departures from CAPRI: the projection adds the term of the
    yield's change (COMI the change of milk per head) to the base N export per head (the outputs other than milk scale
    linearly with the yield)."""
    return 0.0054 * COMI
