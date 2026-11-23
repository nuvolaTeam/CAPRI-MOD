r"""CAPRI's Nordic aid (policy/nordicaid.gms, star 3.0): a region's rate per premium group from its shares in the Nordic
aid regions and their amounts, and the schemes' application types.

capri_mod/policy/nordic_aid.py (nordic_declarations) loops over the regions, schemes and groups and calls these; the
amounts, shares and ceilings (tables 2.5, 2.6, 2.9, 2.10) are data read (nordic_aid_*.csv).
"""
from __future__ import annotations


def p_premDataE_psGroup(share, amount):
    r"""p_premDataE(rs, "1995", psdpay_noa, psGroup): a region's rate, the sum over the Nordic aid regions it has a share
    in of the share times the region's amount per livestock unit or hectare (sequences in the same order).

    CAPRI's GAMS (policy/nordicaid.gms l. 127-131):

        p_premDataE(rs,"1995",psdpay_noa,psGroup)
            = SUM(rNoa $ p_nordicAidRegionShare(rs,rNoa),
                p_nordicAidRegionShare(rs,rNoa)
              *(p_nordicAid_2_5_perLU(psdpay_noa,psGroup,rNoa)
               +p_nordicAid_2_9_perHa(psdpay_noa,psGroup,rNoa)));

    In this project's notation: rate_r = sum_n s_rn a_n. Departures from CAPRI: the amounts per LU and per ha summed by
    the caller (one of them is 0 for each scheme)."""
    t = 0.0
    for s, a in zip(share, amount):
        t = t + s * a
    return t


def p_premDataE_appType(has_ceiling, rates, appType):
    r"""p_premDataE(rs, "1995", scheme, "appType"): the scheme's type (per level for the crops', per livestock unit for
    the animals', per yield for milk: nordic_aid_schemes.csv) where the region has a ceiling or a rate of it; None
    otherwise.

    CAPRI's GAMS (policy/nordicaid.gms l. 133-144):

        p_premDataE(rs,"1995",psdpay_noaCrop,"appType")
            $ [p_premDataE(rs,"1995",psdpay_noaCrop,"ceilval") or sum(psGroup, p_premDataE(rs,"1995",psdpay_noaCrop,psGroup))]
            = perLevl;

        p_premDataE(rs,"1995",psdpay_noaAnim,"appType")
            $ [p_premDataE(rs,"1995",psdpay_noaAnim,"ceilval") or sum(psGroup, p_premDataE(rs,"1995",psdpay_noaAnim,psGroup))]
            = perLivestockUnit;

        *   For dairy cows, the subsidy is per kg of milk
        p_premDataE(rs,"1995","dpNoaMilk","appType")
            $ [p_premDataE(rs,"1995","dpNoaMilk","ceilval") or sum(psGroup, p_premDataE(rs,"1995","dpNoaMilk",psGroup))]
            = perYield;

    Departures from CAPRI: a ceiling's presence, not its value, as the condition (no ceiling is 0 in the data); any
    rate nonzero (CAPRI's sum of the rates)."""
    return appType if (has_ceiling or any(rates)) else None
