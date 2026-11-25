r"""CAPRI's CAP 2014-2020 baseline scenario (scen/base_scenarios/CAP_2014_2020.gms, star 3.0): the national ceilings
of Regulation 1307/2013 Annex II over the BPS years, the ceilings of greening, the young-farmer, redistributive and
natural-constraint payments as shares of the national ceiling, the BPS (or SAPS) ceiling the rest, and the area
schemes' application type.

capri_mod/supply/entitlements.py (ms_ceilings) and capri_mod/policy/cap14_premiums.py (area_declarations) loop over
the member states, years and schemes and call these. The shares, the rates per hectare (PGSAPS 1000) and the Annex's
values are data read (cap14_*.csv, tools/build/build_cap14_entitlements.py).
"""
from __future__ import annotations


def p_2013_1307_AnnexII(value, value_year_before):
    r"""p_2013_1307_AnnexII(RALL, SIMYY) of a BPS year: its value, the year before's where it has none (None where
    neither has one; a value written 0 is one); the national ceiling natCeilCap14 is the filled Annex (l. 140-141).

    CAPRI's GAMS (scen/base_scenarios/CAP_2014_2020.gms l. 135-141):

            loop(bpsyears,
                p_2013_1307_AnnexII(RALL,SIMYY) $ [sameas(bpsyears,simyy) and (not p_2013_1307_AnnexII(RALL,SIMYY))]
                = p_2013_1307_AnnexII(RALL,SIMYY-1);
            );

             p_premDataE(MS,SIMYY,"NATCeilCAP14","CEILVAL") $ p_2013_1307_AnnexII(MS,SIMYY)
                = p_2013_1307_AnnexII(MS,SIMYY);

    Departures from CAPRI: none."""
    return value if value is not None else value_year_before


def p_premDataE_DPGREEN_CEILVAL(greening_share, natCeilCap14):
    r"""p_premDataE(MS, BPSYEARS, "DPGREEN", "CEILVAL"): the greening ceiling, the greening share (0.3) of the national
    ceiling after the transfer.

    CAPRI's GAMS (scen/base_scenarios/CAP_2014_2020.gms l. 309-311):

          p_premDataE(MS,BPSYEARS,"DPGREEN","CEILVAL") = p_dpGreeningShareCAP14(MS) * p_premDataE(MS,BPSYEARS,"natCeilCap14","CEILVAL");
          p_premDataE(MS,BPSYEARS,"DPGREEN","PGSAPS") $(  p_premDataE(MS,BPSYEARS,"DPGREEN","CEILVAL")) = 1000;
          p_premDataE(MS,BPSYEARS,"DPGREEN","AppType") $(  p_premDataE(MS,BPSYEARS,"DPGREEN","CEILVAL")) = perLevl;

    Departures from CAPRI: none (the rate and type: p_premDataE_AppType and the settings)."""
    return greening_share * natCeilCap14


def p_premDataE_share_CEILVAL(share_pct, natCeilCap14):
    r"""p_premDataE(MS, BPSYEARS, scheme, "CEILVAL") of DPYOUNG, DPFIRHA and DPNATCO: the scheme's percentage of the
    national ceiling (p_BPSYF, p_BPSRED, p_BPSNATCO).

    CAPRI's GAMS (scen/base_scenarios/CAP_2014_2020.gms l. 313-315):

          p_premDataE(MS,BPSYEARS,"DPYOUNG","CEILVAL") = p_BPSYF(MS,BPSYEARS)/100 * p_premDataE(MS,BPSYEARS,"natCeilCap14","CEILVAL");
          p_premDataE(MS,BPSYEARS,"DPYOUNG","PGSAPS") = 1000;
          p_premDataE(MS,BPSYEARS,"DPYOUNG","AppType")  $( p_premDataE(MS,BPSYEARS,"DPYOUNG","ceilval")) = perLevl;

    and the same for DPFIRHA (l. 318-320) and DPNATCO (l. 323-325). Departures from CAPRI: none."""
    return share_pct / 100.0 * natCeilCap14


def p_premDataE_dp_bps_CEILVAL(natCeilCap14, coupled, DPGREEN, shares):
    r"""p_premDataE(MS, BPSYEARS, "dp_bps" or "dpbps_SAPS", "CEILVAL"): the BPS ceiling (the SAPS one in the member
    states with the SAPS), the national ceiling less the coupled support of its regions (VCS, cotton: coupled, their
    sum), greening and the three shares' schemes (shares, their ceilings).

    CAPRI's GAMS (scen/base_scenarios/CAP_2014_2020.gms l. 336-343):

          p_premDataE(MS,BPSYEARS,"dp_bps","CEILVAL") $(not DPCAP14_SAPS(MS))
            = p_premDataE(MS,BPSYEARS,"natCeilCap14","CEILVAL")
             - SUM((rs,psdpay_vcs)  $ map_rr(ms,rs), p_premDataE(rs,BPSYEARS,psdpay_vcs,"ceilval"))
             - SUM((rs,psdpay_cscs) $ map_rr(ms,rs), p_premDataE(rs,BPSYEARS,psdpay_cscs,"ceilval"))
            - p_premDataE(MS,BPSYEARS,"DPGREEN","CEILVAL")
            - p_premDataE(MS,BPSYEARS,"DPYOUNG","CEILVAL")
            - p_premDataE(MS,BPSYEARS,"DPFIRHA","CEILVAL")
            - p_premDataE(MS,BPSYEARS,"DPNATCO","CEILVAL");

    and dpbps_SAPS the same (l. 348-355). Departures from CAPRI: the three shares' ceilings summed before they are
    subtracted (the same value up to rounding)."""
    return natCeilCap14 - coupled - DPGREEN - sum(shares)


def p_premDataE_AppType(CEILVAL):
    r"""p_premDataE(MS, BPSYEARS, scheme, "AppType") of the area schemes (DPGREEN, DPYOUNG, DPFIRHA, DPNATCO,
    dpbps_SAPS): per level where the member state has a ceiling of the scheme; None otherwise.

    CAPRI's GAMS (scen/base_scenarios/CAP_2014_2020.gms l. 357-358):

          p_premDataE(MS,BPSYEARS,"dpbps_SAPS","PGSAPS") $(DPCAP14_SAPS(MS)) = 1000;
          p_premDataE(MS,BPSYEARS,"dpbps_SAPS","apptype")$(DPCAP14_SAPS(MS)) = perLevl;

    and l. 311, 315, 320, 325 (the same where the ceiling is set). Departures from CAPRI: a ceiling above 0 (CAPRI's
    nonzero; a negative ceiling, not in the data, gets no type here); dpbps_SAPS per level where its ceiling is above
    0 (CAPRI's in every SAPS member state)."""
    return "perLevl" if CEILVAL > 0.0 else None
