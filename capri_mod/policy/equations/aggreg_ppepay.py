r"""CAPRI's aggregation of the premiums (policy/aggreg_ppepay.gms, star 3.0): the effective premiums of a member state
as its units' level-weighted average and the payments of each scheme, million EUR.

capri_mod/policy/premiums.py (prme_table) and capri_mod/policy/mtr.py (base_payments) loop over the regions,
activities and schemes and call these.
"""
from __future__ import annotations


def p_premPaym_PREMDATA_MS(PREMDATA, LEVL):
    r"""p_premPaym(MSAGG, PPPACT, PSDPAY, PREMDATA) (here PRME over all schemes): a member state's premium of an
    activity, its units' level-weighted average (sequences over the units with a level, in the same order); None where
    the sum is 0 or the member state has no level.

    CAPRI's GAMS (policy/aggreg_ppepay.gms l. 75-77):

            p_premPaym(MSAGG,PPPACT,PSDPAY,PREMDATA) $ (p_premPaym(MSAGG,PPPACT,PSDPAY,"PRMD") and (p_dataCopy(MSAGG,PPPACT,"LEVL","Y") GT eps) and NTSLVL)
                = sum(MAP_RR(MSAGG,SRNUTS1) $ p_premPaym(SRNUTS1,PPPACT,PSDPAY,"PRMD"),
                         p_premPaym(SRNUTS1,PPPACT,PSDPAY,PREMDATA)*p_dataCopy(SRNUTS1,PPPACT,"LEVL","Y"))/p_dataCopy(MSAGG,PPPACT,"LEVL","Y");

    In this project's notation: P_ms = sum_r P_r L_r / sum_r L_r. Departures from CAPRI: the member state's average
    taken from its units directly (CAPRI's through NUTS 1, l. 62-64: the same weights), over the premium summed over the
    schemes (DATA PRME, l. 102-103) and the units' levels (the member state's level their sum)."""
    num = den = 0.0
    for p, lv in zip(PREMDATA, LEVL):
        num += p * lv
        den += lv
    return num / den if den > 0 and num else None


def p_premPaym_Total_PRME(PRME, LEVL):
    r"""p_premPaym(RU, "Total", PSDPAY, "PRME"): a unit's payments of a scheme, million EUR: the sum over its activities
    with a PRMD of PRME x the level / 1000 (sequences in the same order).

    CAPRI's GAMS (policy/aggreg_ppepay.gms l. 109-110):

            p_premPaym(RU,"Total",PSDPAY,"PRME") = sum(PPPACT $ p_premPaym(RU,PPPACT,PSDPAY,"PRMD"),
                        p_premPaym(RU,PPPACT,PSDPAY,"PRME") *p_dataCopy(RU,PPPACT,"LEVL","Y")) * 0.001;

    Departures from CAPRI: the x 0.001 on each term (the same value up to rounding)."""
    t = 0.0
    for p, lv in zip(PRME, LEVL):
        t += p * lv * 0.001
    return t
