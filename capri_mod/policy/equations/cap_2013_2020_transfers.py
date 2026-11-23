r"""CAPRI's transfers between the CAP's pillars (scen/Premiums/cap_2013_2020_transfers.gms, star 3.0): the money moved
from the direct payments to rural development, as a percentage of the national ceiling, filled to the simulation
year, and the national ceiling after it.

capri_mod/supply/entitlements.py (ms_ceilings) loops over the member states and years and calls these. The transfer
from pillar 2 is 0 (del_policy.gms has deleted the pillar-2 ceilings it is a share of).
"""
from __future__ import annotations


def p_cap_2013_2020_transfers_dp_rd(natCeilCap14, rel):
    r"""p_cap_2013_2020_transfers_dp_rd("abs", MS, SIMYYY): the money transferred to pillar 2, the national ceiling x
    the percentage / 100.

    CAPRI's GAMS (scen/Premiums/cap_2013_2020_transfers.gms l. 89-90):

        p_cap_2013_2020_transfers_dp_rd("abs",MS,SIMYYY)
            = p_natCapBudget(MS,"DPPIL1",SIMYYY) * p_cap_2013_2020_transfers_dp_rd("rel",MS,SIMYYY)/100;

    Departures from CAPRI: none (p_natCapBudget's pillar 1 the national ceiling, l. 82)."""
    return natCeilCap14 * rel / 100.0


def p_cap_2013_2020_transfers_dp_rd_fill(value, value_year_before):
    r"""p_cap_2013_2020_transfers_dp_rd("abs", MS, SIMYY) of a year up to the simulation year without a transfer: the
    year before's (None where neither has one).

    CAPRI's GAMS (scen/Premiums/cap_2013_2020_transfers.gms l. 98-101):

        LOOP(SIMYY $ [(calyea(SIMYY) GT 2005) AND (calyea(SIMYY) LE SMAX(SIMY,calyea(SIMY)))],

            p_cap_2013_2020_transfers_dp_rd("abs",MS,SIMYY) $ (NOT p_cap_2013_2020_transfers_dp_rd("abs",MS,SIMYY))
            = p_cap_2013_2020_transfers_dp_rd("abs",MS,SIMYY-1) ;

    Departures from CAPRI: from the first year of the transfers' table (CAPRI's from 2006: no transfer before it)."""
    return value if value is not None else value_year_before


def p_premDataE_natCeilCAP14(natCeilCap14, transfer_dp_rd):
    r"""p_premDataE(MS, SIMYY, "natCeilCAP14", "CEILVAL") after the transfer: the national ceiling less the money moved
    to pillar 2, at least 0.

    CAPRI's GAMS (scen/Premiums/cap_2013_2020_transfers.gms l. 109-112):

        p_premDataE(MS,SIMYY,"natCeilCAP14","CEILVAL") $ p_premDataE(MS,SIMYY,"natCeilCAP14","CEILVAL")
            = MAX[0, p_premDataE(MS,SIMYY,"natCeilCAP14","CEILVAL")
                   - p_cap_2013_2020_transfers_dp_rd("abs",MS,SIMYY)
                   + p_cap_2013_2020_transfers_rd_dp("abs",MS,SIMYY)];

    Departures from CAPRI: the transfer from pillar 2 left out (0, see the module)."""
    return max(0.0, natCeilCap14 - transfer_dp_rd)
