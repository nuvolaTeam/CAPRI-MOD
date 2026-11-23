r"""CAPRI's greening limits (policy/define_greening_limits.gms, star 3.0): the permanent grassland's.

capri_mod/supply/policy.py (PolicyBlock._cap_rules_spec) calls it.
"""
from __future__ import annotations


def p_DPGreeningLimits_permGras(LEVL):
    r"""p_DPGreeningLimits(RU, "permGras"): the permanent grassland limit, the base levels of GRAI and GRAE (the
    caller's sequence over the grassland columns).

    CAPRI's GAMS (policy/define_greening_limits.gms l. 139-140):

        p_DPGreeningLimits(RU,"permGras") $ activeGreeningMeasures("permGras")
          = (DATA(RU,"GRAi","LEVL","Y") + DATA(RU,"GRAE","LEVL","Y"));

    Departures from CAPRI: none (the rule counts the idled histosol grassland too, GRSACT, the caller's row)."""
    return float(sum(LEVL))
