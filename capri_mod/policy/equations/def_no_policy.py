r"""CAPRI's Norwegian payments (policy/def_no_policy.gms, star 3.0): a unit's rate from the national rate and its
regional factor.

capri_mod/policy/norway.py (norway_premiums) loops over the schemes, activities and units and calls it; the rates and
factors are data read (norway_premiums.csv).
"""
from __future__ import annotations


def p_norwPremPact(national, factor=None):
    r"""p_norwPremPact(RU, %1, PSDPAY_NO, PACT): a Norwegian unit's rate per activity unit, the national rate times its
    regional factor (l. 20-21), the national rate where it has none (l. 38-39); its variants take it (l. 56-60, the
    caller's DACT_TO_PACT).

    CAPRI's GAMS (policy/def_no_policy.gms l. 20-21):

          p_norwPremPact(RU,%1,PSDPAY_NO,PACT) $ (MAP_RR("NO000000",RU) and (p_norwPremPact_E("NO000000",%1,PSDPAY_NO,PACT) gt eps))
              = p_norwPremPact_E(RU,%1,PSDPAY_NO,PACT)*p_norwPremPact_E("NO000000",%1,PSDPAY_NO,PACT);

    and

          p_norwPremPact(RU,%1,PSDPAY_NO,PACT) $ ((not p_norwPremPact_E(RU,%1,PSDPAY_NO,PACT)) and MAP_RR("NO000000",RU))
             = p_norwPremPact_E("NO000000",%1,PSDPAY_NO,PACT);

    In this project's notation: rate_r = rate_NO x f_r, or rate_NO. Departures from CAPRI: the national rate times the
    factor in that order (CAPRI's factor x rate, the same product); the output payments (l. 28-33, 46-51) not computed
    (they pay nothing in CAPMOD, capri_mod/policy/norway.py, KNOWN_ISSUES K144)."""
    return national * factor if factor is not None else national
