r"""CAPRI's voluntary coupled support (scen/Premiums/Coupling/CAP_2013_2020_vcs.gms, star 3.0): the coupled ceilings
filled from the base year to the simulation year and their application type.

capri_mod/supply/entitlements.py (ms_ceilings) and capri_mod/policy/cap14_premiums.py (coupled_declarations) call
these; the ceilings themselves are data read (cap14_coupled_ceilings.csv).
"""
from __future__ import annotations


def p_premDataE_CEILVAL(value, value_year_before):
    r"""p_premDataE(RS, SIMYY, psdpay_vcs, "CEILVAL") of a year from the base year to the simulation year without a
    ceiling: the year before's (None where neither has one; the cotton payment's, CAP_2013_2020_cscs.gms, the same).

    CAPRI's GAMS (scen/Premiums/Coupling/CAP_2013_2020_vcs.gms l. 40-43):

            LOOP( SIMYY $ ((CALYEA(SIMYY) GE CALYEA("BAS")) $ (CALYEA(SIMYY) LE CALYEA("Y"))),
                p_premDataE(RS,SIMYY,psdpay_vcs,"CEILVAL")  $ (NOT p_premDataE(RS,SIMYY,psdpay_vcs,"CEILVAL"))
                  = p_premDataE(RS,SIMYY-1,psdpay_vcs,"CEILVAL");
                );

    Departures from CAPRI: none."""
    return value if value is not None else value_year_before


def p_premDataE_apptype(CEILVAL):
    r"""p_premDataE(rs, SIMYY, psdpay_vcs, "apptype"): per level where the region has a ceiling of the scheme (the
    complementary national payments the same, CAP_2013_2020_CNDP.gms l. 86-94); None otherwise.

    CAPRI's GAMS (scen/Premiums/Coupling/CAP_2013_2020_vcs.gms l. 49-51):

         p_premDataE(rs,SIMYY,psdpay_vcs,"apptype") $ [(not p_premDataE(rs,SIMYY,psdpay_vcs,"apptype"))
                                                          and p_premDataE(rs,SIMYY,psdpay_vcs,"ceilval")]
                                                = perLevl;

    Departures from CAPRI: none (no coupled scheme's data gives a type of its own)."""
    return "perLevl" if CEILVAL else None
