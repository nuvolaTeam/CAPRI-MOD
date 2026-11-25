r"""CAPRI's upper bound on the supply elasticities (supply/pmp_terms/impose_upper_bound_on_elasticity.gms, star 3.0):
the dampening of an elasticity above p_elasHigh.

capri_mod/supply/capri_pmp.py (dampen_elasticity) calls it.
"""
from __future__ import annotations

import numpy as np


def p_pmpQuadTechn_dampening(e, elasHigh, elasCap):
    r"""The dampened own-price elasticity of p_pmpQuadTechn(RU, QACT, A, A): an elasticity above p_elasHigh becomes
    min(8, sqrt(e) + p_elasHigh - sqrt(p_elasHigh)) (8: ELAS_CAP), the others pass (arrays).

    CAPRI's GAMS (supply/pmp_terms/impose_upper_bound_on_elasticity.gms l. 19-34):

            p_pmpQuadTechn(RU,QACT,A,A) $ (p_testElas(RU,QACT,A,"dampening","before") GT p_elasHigh(QACT))
            =
        *       1./(MIN(8,sqrt(p_testElas(RU,QACT,A,"dampening","before"))+2.5)
        *pw130319 (1) The previous original dampening formula is not dampening, but INCREASING the elasticity for 4.5<p_testelas(before)<4.66
        *         (2) The hardcoded threshold is cumbersome to modify
        *         => The following formula gives ALMOST the same results but solves issues #1 + #2:
              1./(MIN(8,sqrt(p_testElas(RU,QACT,A,"dampening","before"))+p_elasHigh(QACT)-sqrt(p_elasHigh(QACT)))
                    * (1 $ (Not QCACT(QACT)) + (1. - 0.2 * SQRT(DATA(RU,QACT,"LEVL","Y")/ (DATA(RU,"ARAB","LEVL","Y") $ ((NOT (SAMEAS(QACT,"GRAE") or SAMEAS(QACT,"GRAI"))) and QCACT(QACT))
                                                                                       + DATA(RU,"GRAS","LEVL","Y") $ (SAMEAS(QACT,"GRAE") or SAMEAS(QACT,"GRAI"))))) $ QCACT(QACT)))
        *
        *      --- the maximum of the costs, the land rents or
        *          the revenues plus premiums, in average over the technologies
        *          to mimick the initialization from estimated ones
        *
                * p_revenues(RU,QACT,A)
                                      / (DATA(RU,QACT,"LEVL","Y") *  p_technFact(RU,QACT,"LEVL",A));

    Departures from CAPRI: the elasticity itself dampened (CAPRI sets the PMP term from it; the share term, 1 - 0.2
    sqrt(the crop's share), and the revenues per level are capri_pmp.py's share_term and its build); a negative
    elasticity's root taken at 0."""
    e = np.asarray(e, dtype=float)
    damped = np.minimum(elasCap, np.sqrt(np.maximum(e, 0.0)) + elasHigh - np.sqrt(elasHigh))
    return np.where(e > elasHigh, damped, e)
