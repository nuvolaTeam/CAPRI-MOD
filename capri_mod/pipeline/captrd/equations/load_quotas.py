r"""CAPTRD's statements of sugar/load_quotas.gms (CAPRI star 3.0, batincluded by captrd/captrd_policy.gms l. 51 with
years p_data): the sugar quotas' years, as named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). capri_mod/pipeline/captrd/policy.py (sugar_quotas) holds the loops over the
countries, the quotas and the years and the conditions, and calls them; the arithmetic is the port's, so the quotas are
unchanged.
"""
from __future__ import annotations


def p_SQuotas_before1999(quota_1999):
    r"""p_SQuotas(MSALL, Quotas, years) before 1999: 1999's quota.

    CAPRI's GAMS (sugar/load_quotas.gms l. 41-41):

        p_SQuotas(MSALL,Quotas,%1)  $ (CALYEA(%1) LT CALYEA("1999")) = p_SQuotas(MSALL,Quotas,"1999");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.sugar_quotas)."""
    return quota_1999


def p_SQuotas_fill(previous):
    r"""p_SQuotas(MSALL, Quotas, SIMYY) where the year has none: the year before's (sequentially, a LOOP up to the last
    year of the run).

    CAPRI's GAMS (sugar/load_quotas.gms l. 43-45):

        LOOP(SIMYY $ (CALYEA(SIMYY) LE SMAX(%1, CALYEA(%1))),
            p_SQuotas(MSALL,Quotas,SIMYY) $ (NOT p_SQuotas(MSALL,Quotas,SIMYY)) = p_SQuotas(MSALL,Quotas,SIMYY-1);
        );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.sugar_quotas)."""
    return previous


def p_SQuotas_QUTS(quta, qutb):
    r"""p_SQuotas(MSALL, "QUTS", years): the A and B quotas summed.

    CAPRI's GAMS (sugar/load_quotas.gms l. 49-49):

        p_SQuotas(MSALL,"QUTS",%1)  = p_SQuotas(MSALL,"QutB",%1) +p_SQuotas(MSALL,"QutA",%1) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.sugar_quotas)."""
    return quta + qutb
