r"""CAPRI's complementary national direct payments (scen/Premiums/Coupling/CAP_2013_2020_CNDP.gms, star 3.0): the
decoupled ones' rate per unit of their premium group, from the ceiling and the member state's level.

capri_mod/policy/cap14_premiums.py (coupled_declarations) calls it.
"""
from __future__ import annotations


def p_premDataE_PSGROUP(ceilval, LEVL):
    r"""p_premDataE(MS, SIMYY, psdpay_dcndp, psgroup): a decoupled complementary payment's rate per unit of its group,
    its ceiling x 1000 over the member state's level of the group's activities (the caller keeps a level above 0).

    CAPRI's GAMS (scen/Premiums/Coupling/CAP_2013_2020_CNDP.gms l. 65-67):

        p_premDataE(MS,SIMYY,psdpay_dcndp,psgroup) $( SUM(PACT $ psg_to_a(psgroup,PACT), DATA(MS,PACT,"LEVL","Y"))  and psdpay_to_psgroup(psdpay_dcndp,psgroup))
                                                     = p_premDataE(MS,SIMYY,psdpay_dcndp,"ceilval") * 1000
                                                          /SUM(PACT $ psg_to_a(psgroup,PACT), DATA(MS,PACT,"LEVL","Y") ) ;

    Departures from CAPRI: with the year's ceiling (each data year's before the fill, so the last one's; the caller's)
    and the units' levels summed to the member state."""
    return ceilval * 1000.0 / LEVL
