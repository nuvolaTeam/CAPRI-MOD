r"""CAPTRD's statements of policy/reformsugarquotas.gms (CAPRI star 3.0, batincluded by captrd/captrd_policy.gms l. 52
with years p_data): the sugar quotas after the 2006 reform, the buy-back and renunciation, the near-zero quotas, as
named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). capri_mod/pipeline/captrd/policy.py (sugar_quotas) holds the loops over the
countries, the quotas and the years and the conditions, and calls them; the arithmetic is the port's, so the quotas are
unchanged. %workStep% is not "Build database" (the CAPTRD branch, l. 129-145).
"""
from __future__ import annotations


def p_squotas_reform(quta, qutb):
    r"""p_squotas(msall, "quta" / "qutb" / "quts", simyy) from 2006: the B quota moved into A, B kept at 0.001 where
    there is an A quota. Returns (A, B or None where A is zero: no record).

    CAPRI's GAMS (policy/reformsugarquotas.gms l. 82-84):

         p_squotas(msall,"quta",simyy) $ (calyea(simyy) GE calyea("2006")) = p_squotas(msall,"quta",simyy) + p_squotas(msall,"qutb",simyy);
         p_squotas(msall,"qutb",simyy) $ ((calyea(simyy) GE calyea("2006")) AND p_squotas(msall,"quta",simyy)) = 0.001;
         p_squotas(MSALL,"quts",simyy1) = p_squotas(MSALL,"quta",simyy1) + p_squotas(MSALL,"qutb",simyy1);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.sugar_quotas)."""
    a = quta + qutb
    return a, (0.001 if a else None)


def p_squotas_quts(quta, qutb):
    r"""p_squotas(MSALL, "quts", simyy1): the A and B quotas summed, on the years of the run.

    CAPRI's GAMS (policy/reformsugarquotas.gms l. 84-84):

         p_squotas(MSALL,"quts",simyy1) = p_squotas(MSALL,"quta",simyy1) + p_squotas(MSALL,"qutb",simyy1);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.sugar_quotas)."""
    return quta + qutb


def p_PPSQ_cumulated(values):
    r"""p_PPSQRenounce / p_PPSQCBuyBack(MSALL, %lY%): the renunciation or the buy-back cumulated up to the year.

    values: the yearly values up to the year, in the caller's order.

    CAPRI's GAMS (policy/reformsugarquotas.gms l. 89-90):

            p_PPSQRenounce(MSALL,%lY%) = SUM(simyy $ (calyea(simyy) LE calyea(simyy1)), p_PPSQRenounce(MSALL,simyy));
            p_PPSQCBuyBack(MSALL,%lY%) = SUM(simyy $ (calyea(simyy) LE calyea(simyy1)), p_PPSQCBuyBack(MSALL,simyy));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.sugar_quotas)."""
    return sum(values)


def p_data_quotas_suga(quota, quts, buyback, renounce, withdraw):
    r"""p_data(MSALL, quotas, "suga", simyy1): the quota plus the buy-back, less the renunciation and the withdrawals,
    distributed over the A and B quotas by their shares; at least 0.0001 (where there is a quota).

    CAPRI's GAMS (policy/reformsugarquotas.gms l. 92-107):

            %2(MSALL,quotas,"suga",simyy1) $ p_squotas(MSALL,"quts",simyy1) = max(0.0001,

        *   Basic quotas...
                  p_squotas(MSALL,quotas,simyy1)

        *   ...plus C buy-back...
                + ( p_PPSQCBuyBack(MSALL,%lY%)

        *   ...minus accumulated renunciation...
                  - p_PPSQRenounce(MSALL,%lY%)

        *   ...minus temporary withdrawals of commission...
                  - p_PPSQWithdraw(MSALL,simyy1))

        *   ...distributed proportionally over A and B quotas.
                * p_squotas(MSALL,quotas,simyy1)/p_squotas(MSALL,"quts",simyy1));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.sugar_quotas)."""
    return max(0.0001, quota + (buyback - renounce - withdraw) * quota / quts)


def p_data_quotas_suga_small(eu_member):
    r"""p_data(MSALL, quotas, "suga", simyy1) of at most 1: near zero (1e-6) for the EU's members that year, else
    none.

    CAPRI's GAMS (policy/reformsugarquotas.gms l. 133-134):

         %2(MSALL,quotas,"suga",simyy1) $ (%2(MSALL,quotas,"suga",simyy1) Le 1)
            = 1.E-6 $ MAP_RRT("EU",MSALL,SIMYY1)  ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.sugar_quotas)."""
    return 1e-6 if eu_member else 0.0


def p_data_quotas_suga_no_quota():
    r"""p_data(MSALL, quotas, "suga", simyy1) from 2017 under an Aglink version without sugar quotas
    (noSugQuotaAglinkVersion, %expost% off): none.

    CAPRI's GAMS (policy/reformsugarquotas.gms l. 139-142):

         %2(MSALL,quotas,"suga",simyy1) $ ((calyea(simyy1) ge calyea("2017")) $ sum(sameas(curAglinkVersion,noSugQuotaAglinkVersion),1))
            = 0
        $ifi %MODE%==CAPMOD + eps
            ;

    Departures from CAPRI: the + eps of %MODE%==CAPMOD (l. 141) is not CAPTRD's; the domain condition in the caller (policy.sugar_quotas)."""
    return 0.0
