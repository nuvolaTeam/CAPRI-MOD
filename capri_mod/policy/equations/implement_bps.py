r"""CAPRI's basic payment scheme (policy/implement_bps.gms, star 3.0): the units' BPS ceilings from the member state's,
their entitlements, and the convergence of their unit values (IUV) within a BPS region (the tunnel, the linear model,
the 30% rule).

Each function computes one statement for one unit (or one BPS region's sum); capri_mod/policy/bps.py (bps_rates,
converge) loops over the member states, BPS regions, years and units, reads the data and passes the numbers. The
proportional model (l. 290-296) no member state uses; it is not ported.
"""
from __future__ import annotations


def p_premDataE_ceilval_fill(ceilval, ceilval_year_before):
    r"""p_premDataE(rall, simyy, "dp_bps", "ceilval") of a year without a ceiling: the year before's.

    CAPRI's GAMS (policy/implement_bps.gms l. 107-111):

        loop(simyy $ simyyy(simyy),
            p_premDataE(rall,simyy,"dp_bps","ceilval")
                $ [not p_premDataE(rall,simyy,"dp_bps","ceilval")]
                = p_premDataE(rall,simyy-1,"dp_bps","ceilval");
        );

    In this project's notation: C_y = C_y if C_y else C_{y-1}, the years in order (the caller passes the year before's
    filled value). Departures from CAPRI: none (applied to the member state's ceiling, the only one the step uses)."""
    return ceilval if ceilval else ceilval_year_before


def ord_bpsYear(year):
    r"""ord_bpsYear(simyyy): the year's ordinal from the reform's start, the year minus 2014.

    CAPRI's GAMS (policy/implement_bps.gms l. 113-115):

        parameter ord_bpsYear(simyy) "Ordinal number of bps year, used for tunnel";
        *   Beware, the 2014 is hard coded first year of reform, a bit dangerous but readable.
        ord_bpsYear(simyyy) = calyea(simyyy)-2014;

    Departures from CAPRI: none."""
    return year - 2014


def p_premData_ceillev(LEVL):
    r"""p_premData(ru, "dp_bps", "ceillev"): a unit's payment entitlements, the sum of its trend levels of CAPRI's crops
    (MCACT), the same in every year of the reform (l. 132-133).

    CAPRI's GAMS (policy/implement_bps.gms l. 127-133):

        p_premData(ru,"dp_bps","ceillev")
            = SUM(mcact, p_dataLocal(ru,mcact,"levl","y"));

        *   Assume that the number of entitlements is identical in each year
        p_premDataE(ru,simyyy,"dp_bps","ceillev")
            = p_premData(ru,"dp_bps","ceillev");

    In this project's notation: E_r = sum_{a in MCACT} L_ra (the levels in the caller's order). Departures from CAPRI:
    the levels the step's trend (the caller's), CAPRI's trends_%BAS%%SIM%.gdx. Summed term by term in order (Python's
    sum of floats is compensated since 3.12: a different last digit)."""
    e = 0.0
    for v in LEVL:
        e += v
    return e


def p_premData_ceilacv(PRME, LEVL, entlWght):
    r"""p_premData(ru, psdpay_mtr, "ceilacv"): a unit's payments under the 2004-2013 regime's decoupled schemes (the
    BPS's key), million EUR: the sum over its activities and schemes of PRME x the entitlements (the level x the
    weight) / 1000 (sequences in the same order; the caller's schemes DPFRMS, DPFRMF and DPREG).

    CAPRI's GAMS (policy/implement_bps.gms l. 147-150):

        execute_load "%scrdir%\policyIUV.gdx"   p_premPaym;
        p_premData(ru,psdpay_mtr,"ceilacv") = sum(pppact, p_premPaym(ru,pppact,psdpay_mtr,"prme")
                                                         *p_premPaym(ru,pppact,psdpay_mtr,"entl")
                                                         /1000);

    In this project's notation: K_r = sum_{a,s} PRME_ras L_ra w_ras / 1000. Departures from CAPRI: summed over the
    schemes at once (CAPRI per scheme, then over them in l. 161-167); DPSAPS, the fourth scheme of PSDPAY_MTR, is the
    SAPS member states' (no BPS) and not computed; the entitlements as the level times the weight (CAPRI's Entl, the
    same product)."""
    t = 0.0
    for p, lv, w in zip(PRME, LEVL, entlWght):
        t += p * lv * w / 1000.0
    return t


def p_bps_entitlements(ceillev):
    r"""p_bps_entitlements(ms, rbps): the BPS region's entitlements, the sum of its units'.

    CAPRI's GAMS (policy/implement_bps.gms l. 136-137):

        p_bps_entitlements(ms,rbps)
            = SUM(bps_region_to_ru(ms,rbps,ru), p_premData(ru,"dp_bps","ceillev"));

    Departures from CAPRI: none."""
    return sum(ceillev)


def p_premData_ceilacv_MS(ceilacv):
    r"""p_premData(ms, psdpay_mtr, "ceilacv"): the member state's MTR payments, the sum of its units'.

    CAPRI's GAMS (policy/implement_bps.gms l. 155-156):

        p_premData(ms,psdpay_mtr,"ceilacv")
            = sum(ru $ map_rr(ms,ru), p_premData(ru,psdpay_mtr,"ceilacv"));

    In this project's notation: K_ms = sum_r K_r. Departures from CAPRI: the keys already summed over the schemes (the
    sum over psdpay_mtr of l. 161-167 taken first, capri_mod/policy/mtr.py)."""
    return sum(ceilacv)


def p_premDataE_ceilval(key, ceilval_MS, key_MS):
    r"""p_premDataE(ru, simyyy, "dp_bps", "ceilval"): a unit's BPS ceiling, the member state's distributed by the units'
    MTR payments (the key; the caller keeps the units with a key).

    CAPRI's GAMS (policy/implement_bps.gms l. 160-168):

        loop(ms,
            p_premDataE(ru,simyyy,"dp_bps","ceilval") $ [SUM(psdpay_mtr, p_premData(ru,psdpay_mtr,"ceilacv"))
                                                        and map_rr(ms,ru)]
        *   - Historical single farm payment in this region
                = SUM(psdpay_mtr, p_premData(ru,psdpay_mtr,"ceilacv"))
        *   - Scaled to fit new envelope
                    *p_premDataE(ms,simyyy,"dp_bps","ceilval")
                    /SUM(psdpay_mtr, p_premData(ms,psdpay_mtr,"ceilacv"));
        );

    In this project's notation: C_ry = K_r C_ms,y / K_ms. Departures from CAPRI: none here (a member state none of whose
    units has a key takes their entitlements as the key in the caller, KNOWN_ISSUES K142)."""
    return key * ceilval_MS / key_MS


def p_bps_envelope(ceilval):
    r"""p_bps_envelope(ms, rbps, simyyy): the BPS region's envelope, the sum of its units' ceilings.

    CAPRI's GAMS (policy/implement_bps.gms l. 172-173):

        p_bps_envelope(ms,rbps,simyyy) $ bps_region_used(ms,rbps)
            = SUM(bps_region_to_ru(ms,rbps,ru), p_premDataE(ru,simyyy,"dp_bps","ceilval"));

    Departures from CAPRI: none."""
    return sum(ceilval)


def p_bps_aiuv(envelope, entitlements):
    r"""p_bps_aiuv(ms, rbps, simyyy): the BPS region's average unit value, its envelope x 1000 / its entitlements (0
    without entitlements).

    CAPRI's GAMS (policy/implement_bps.gms l. 176-178):

        p_bps_aiuv(ms,rbps,simyyy) $ p_bps_entitlements(ms,rbps)
            = p_bps_envelope(ms,rbps,simyyy)*1000
            / p_bps_entitlements(ms,rbps);

    In this project's notation: AIUV = ENV x 1000 / E. Departures from CAPRI: none."""
    return envelope * 1000.0 / entitlements if entitlements else 0.0


def p_bps_noConvergence(ceilval, ceillev):
    r"""p_bps_noConvergence(ru, simyyy): a unit's IUV before the convergence, its ceiling x 1000 / its entitlements.

    CAPRI's GAMS (policy/implement_bps.gms l. 181-183):

        p_bps_noConvergence(ru,simyyy) $ p_premData(ru,"dp_bps","ceillev")
            = p_premDataE(ru,simyyy,"dp_bps","ceilval")*1000
            / p_premData(ru,"dp_bps","ceillev");

    In this project's notation: IUV0_r = C_r x 1000 / E_r (the caller keeps the units with entitlements). Departures
    from CAPRI: none."""
    return ceilval * 1000.0 / ceillev


def ybpsPre(years, final_year):
    r"""ybpsPre: the reform's years before the BPS region's final year (ybpsFin the final year, ybpsPost the years from
    it).

    CAPRI's GAMS (policy/implement_bps.gms l. 201-203):

            ybpsFin(simyyy) = yes $ [calyea(simyyy) eq p_bps_final_year(ms,rbps)];
            ybpsPost(simyyy) = yes $ [calyea(simyyy) ge p_bps_final_year(ms,rbps)];
            ybpsPre(simyyy) = yes - ybpsPost(simyyy);

    Departures from CAPRI: none (ybpsFin is the final year itself; ybpsPost is used only through ybpsPre)."""
    return [y for y in years if y < final_year]


def rcur(units, ceillev):
    r"""rcur: the BPS region's units, those with entitlements (the others have no IUV, l. 181).

    CAPRI's GAMS (policy/implement_bps.gms l. 206-207):

            option kill=rcur;
            rcur(ru) = yes $ bps_region_to_ru(ms,rbps,ru);

    Departures from CAPRI: the units without entitlements left out here (CAPRI keeps them in rcur, where their IUV is
    0 and they add nothing to the sums)."""
    return [u for u in units if ceillev[u]]


def p_bps_targetIUV(aiuv, target_share):
    r"""p_bps_targetIUV(ru, simyyy): the IUV the units below converge to, a share of the region's average.

    CAPRI's GAMS (policy/implement_bps.gms l. 211-212):

            p_bps_targetIUV(ru,simyyy)
                = p_bps_aiuv(ms,rbps,simyyy) * p_bps_tunnel_target_share(ms,rbps);

    Departures from CAPRI: none."""
    return aiuv * target_share


def rbpsLo(noConvergence_final, targetIUV_final):
    r"""rbpsLo(rcur): whether a unit's IUV before the convergence is below the target in the final year.

    CAPRI's GAMS (policy/implement_bps.gms l. 215-217):

            rbpsLo(ru) = no;
            rbpsLo(rcur)
                = yes $ sum(ybpsFin, p_bps_noConvergence(rcur,ybpsFin) LT p_bps_targetIUV(rcur,ybpsFin));

    Departures from CAPRI: none."""
    return noConvergence_final < targetIUV_final


def rbpsUp(noConvergence_final, aiuv_final):
    r"""rbpsUp(rcur): whether a unit's IUV before the convergence is above the region's average in the final year.

    CAPRI's GAMS (policy/implement_bps.gms l. 220-222):

            rbpsUp(ru) = no;
            rbpsUp(rcur)
                = yes $ sum(ybpsFin,p_bps_noConvergence(rcur,ybpsFin) GT p_bps_aiuv(ms,rbps,ybpsFin));

    Departures from CAPRI: none."""
    return noConvergence_final > aiuv_final


def p_premDataE_pgsaps_lo(noConvergence, targetIUV, gap_closure, ord_year, card_pre):
    r"""p_premDataE(rbpsLo, simyyy, "dp_bps", "pgsaps") before the overshoot's allocation: a unit below the target
    closes the gap's share in equal steps up to the final year, fully from it.

    CAPRI's GAMS (policy/implement_bps.gms l. 230-237):

            p_premDataE(rbpsLo,simyyy,"dp_bps","pgsaps")
        *       ...pre-convergence value
                = p_bps_noConvergence(rbpsLo,simyyy)
        *       ...plus share of difference to mean to cover
                + (p_bps_targetIUV(rbpsLo,simyyy)-p_bps_noConvergence(rbpsLo,simyyy))
                * p_bps_tunnel_gap_closure(ms,rbps)
        *       ...divided in equal steps up to implementation year and then fully (1).
                * min(1, ord_bpsYear(simyyy)/(1+card(ybpsPre)));

    In this project's notation: IUV = IUV0 + (T - IUV0) g min(1, ord / (1 + |pre|)). Departures from CAPRI: none."""
    return noConvergence + (targetIUV - noConvergence) * gap_closure * min(1.0, ord_year / (1 + card_pre))


def p_premDataE_pgsaps_rest(noConvergence):
    r"""p_premDataE(rcur, simyyy, "dp_bps", "pgsaps") of a unit not below the target: its IUV before the convergence.

    CAPRI's GAMS (policy/implement_bps.gms l. 241-242):

            p_premDataE(rcur,simyyy,"dp_bps","pgsaps") $ [not rbpsLo(rcur)]
                = p_bps_noConvergence(rcur,simyyy);

    Departures from CAPRI: none."""
    return noConvergence


def p_bps_envelopeOvershoot(ceillev, pgsaps, envelope):
    r"""p_bps_envelopeOvershoot(ms, rbps, simyyy): the BPS region's payments at the units' IUVs minus its envelope
    (sequences over rcur in the same order); computed again after the 30% rule (l. 304-306).

    CAPRI's GAMS (policy/implement_bps.gms l. 247-249):

            p_bps_envelopeOvershoot(ms,rbps,simyyy)
                = sum(rcur, p_premDataE(rcur,simyyy,"dp_bps","ceillev")*p_premDataE(rcur,simyyy,"dp_bps","pgsaps")/1000)
                - p_bps_envelope(ms,rbps,simyyy);

    In this project's notation: O = sum_r E_r IUV_r / 1000 - ENV. Departures from CAPRI: none."""
    return sum(e * p / 1000.0 for e, p in zip(ceillev, pgsaps)) - envelope


def p_premDataE_pgsaps_linear(noConvergence, aiuv, overshoot, ceillev_up, noConvergence_up):
    r"""p_premDataE(rbpsUp, simyyy, "dp_bps", "pgsaps") of the linear model: a unit above the average gives up the same
    share of its distance to the average, the share that removes the overshoot (0 when the units above have no
    distance; ceillev_up and noConvergence_up are the units above's, in the same order).

    CAPRI's GAMS (policy/implement_bps.gms l. 253-260):

            p_premDataE(rbpsUp,simyyy,"dp_bps","pgsaps") $ bps_region_to_option(ms,rbps,"bps_linear")
                = p_bps_aiuv(ms,rbps,simyyy)
                + (p_bps_noConvergence(rbpsUp,simyyy) - p_bps_aiuv(ms,rbps,simyyy))
                * (1 - p_bps_envelopeOvershoot(ms,rbps,simyyy)
                     / sum(rcur $ rbpsUp(rcur), p_premDataE(rcur,simyyy,"dp_bps","ceillev")
                                              *(p_bps_noConvergence(rcur,simyyy)-p_bps_aiuv(ms,rbps,simyyy))/1000))
                     $ sum(rcur $ rbpsUp(rcur), p_bps_noConvergence(rcur,simyyy)-p_bps_aiuv(ms,rbps,simyyy))
                                              ;

    In this project's notation: IUV = AIUV + (IUV0 - AIUV) (1 - O / sum_up E (IUV0 - AIUV) / 1000), the factor 0 when
    sum_up (IUV0 - AIUV) = 0. Departures from CAPRI: none."""
    den = sum(e * (x - aiuv) / 1000.0 for e, x in zip(ceillev_up, noConvergence_up))
    gap_up = sum(x - aiuv for x in noConvergence_up)
    f = (1.0 - overshoot / den) if gap_up else 0.0
    return aiuv + (noConvergence - aiuv) * f


def p_premDataE_pgsaps_rule30(pgsaps, noConvergence):
    r"""p_premDataE(rbpsUp, simyyy, "dp_bps", "pgsaps") under the 30% rule: a unit above the average keeps at least 70%
    of its IUV before the convergence.

    CAPRI's GAMS (policy/implement_bps.gms l. 299-300):

            p_premDataE(rbpsUp,simyyy,"dp_bps","pgsaps")   $ bps_region_to_option(ms,rbps,"bps_30_percent_rule")
                = max(p_premDataE(rbpsUp,simyyy,"dp_bps","pgsaps"), p_bps_noConvergence(rbpsUp,simyyy)*0.70);

    Departures from CAPRI: none."""
    return max(pgsaps, noConvergence * 0.70)


def p_premDataE_pgsaps_lo_overshoot(pgsaps, overshoot, ceillev_lo):
    r"""p_premDataE(rbpsLo, simyyy, "dp_bps", "pgsaps") after the 30% rule: the overshoot left taken from the units below
    the target, divided by their entitlements (ceillev_lo, theirs).

    CAPRI's GAMS (policy/implement_bps.gms l. 309-312):

            p_premDataE(rbpsLo,simyyy,"dp_bps","pgsaps")
                = p_premDataE(rbpsLo,simyyy,"dp_bps","pgsaps")
                - p_bps_envelopeOvershoot(ms,rbps,simyyy)
                / sum(rbpsLo1, p_premDataE(rbpsLo1,simyyy,"dp_bps","ceillev"));

    In this project's notation: IUV = IUV - O / sum_lo E. Departures from CAPRI: none; the units as CAPRI writes them
    (million EUR over thousand ha, without the x 1000 of l. 177: the envelope stays overshot where the 30% rule binds, a
    CAPRI bug kept, KNOWN_ISSUES K141)."""
    return pgsaps - overshoot / sum(ceillev_lo)
