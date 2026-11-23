r"""CAPRI's endogenous entitlement limit (policy/def_endCut.gms, star 3.0): the cut per hectare beyond the limit.

capri_mod/supply/entitlements.py (ms_cuts) calls it.
"""
from __future__ import annotations


def p_entlLimit_cut(CEILVAL, Limit):
    r"""p_entlLimit(MS, dpEndCut, ddEndCut, "cut"): the member state's ceilings of the cut schemes x 1000 over the sum
    of its regions' limits (their trend crop areas), EUR per ha; a region takes its member state's (l. 92).

    CAPRI's GAMS (policy/def_endCut.gms l. 88-92):

         p_entlLimit(MS,dpEndCut,ddEndCut,"cut")  $ [PSDPAY_cutEndog(dpEndCut) and dpEndCut_to_ddEndCut( dpEndCut,ddEndCut)]=
                             p_premDataE(MS,"%SIMY%",dpEndCut,"CEILVAL") * 1000 /
                             sum(MAP_RR(MS,RU), p_entlLimit(RU,dpEndCut,ddEndCut,"Limit"));

         p_entlLimit(RU,dpEndCut,ddEndCut,"cut") $  [PSDPAY_cutEndog(dpEndCut) and dpEndCut_to_ddEndCut( dpEndCut,ddEndCut)] = sum(MAP_RR(MS,RU),  p_entlLimit(MS,dpEndCut,ddEndCut,"cut"));

    Departures from CAPRI: the schemes' ceilings summed first (CEILVAL their sum: the schemes share the limit, so the
    region's objective loses the sum of their cuts; the same value up to rounding)."""
    return CEILVAL * 1000.0 / Limit
