r"""CAPRI's preparation of the land-use change in the simulation (supply/prep_sim_luc.gms, star 3.0): the bounds on
forest, other land and artificial land.

capri_mod/supply/land.py (LandBlock._land_type_bounds) calls these; the shares are parameters (LUC_*, data read).
"""
from __future__ import annotations


def v_actLevl_bounds_foreOlndArtif(L0, ARTO, lo_own, lo_arto, up_own, up_arto):
    r"""(v_actLevl.LO, v_actLevl.UP)(regions, foreOlndArtif, "T"): a land type's bounds, L0 - min(a L0, b ARTO) to L0
    + min(9 L0, 0.35 ARTO) (a 0.9 and b 0.35, Corsica 0.98 and 0.75; ARTO the region's total area).

    CAPRI's GAMS (supply/prep_sim_luc.gms l. 587-593):

          v_actLevl.LO(%REGIONS%,foreOlndArtif,"T") = v_actLevl.L(%REGIONS%,foreOlndArtif,"T")
                                                    - min((.9+0.08 $ sameas(%REGIONS%,"FR830000"))*v_actLevl.L(%REGIONS%,foreOlndArtif,"T"),
                                                          (.35+0.4 $ sameas(%REGIONS%,"FR830000"))*%data%(%REGIONS%,"arto","levl","y"));

          v_actLevl.up(%REGIONS%,foreOlndArtif,"T") = v_actLevl.L(%REGIONS%,foreOlndArtif,"T")
                                                    + min(9*v_actLevl.L(%REGIONS%,foreOlndArtif,"T"),
                                                          .35*%data%(%REGIONS%,"arto","levl","y"));

    Departures from CAPRI: L0 the base areas (CAPRI's current levels: the same at the start); the land classes'
    bounds of l. 578-584 (CROP, GRSLND) not ported."""
    lo = L0 - min(lo_own * L0, lo_arto * ARTO)
    up = L0 + min(up_own * L0, up_arto * ARTO)
    return lo, up


def v_actLevl_lo_floor(L0, share):
    r"""v_actLevl.lo(REGIONS, "FORE" or "ARTIF", "T") under the landscape floor: forest at least 0.99 of its base, the
    artificial land 0.997 (share: LUC_FORE_FLOOR, LUC_ARTIF_FLOOR).

    CAPRI's GAMS (supply/prep_sim_luc.gms l. 599-605):

                v_actLevl.lo(%REGIONS%,"FORE","T") $ ( DATA(%REGIONS%,"FALL","FLOOR","Y") $ v_actLevl.L(%REGIONS%,"uaar","T")
                                                     $ v_actLevl.range(%REGIONS%,"FORE","T") $ data(%REGIONS%,"fore","levl","y"))
        *               usually only a 1% decline is considered plausible...
                      = .99* data(%REGIONS%,"fore","levl","y") $ (not data(%REGIONS%,"FORE","FLOOR","y"))
        *               but specific land use related policies (like support for carbn farming) might require other bounds
                      + data(%REGIONS%,"FORE","FLOOR","y")            $ data(%REGIONS%,"FORE","FLOOR","y")
                      ;

    and ARTIF at 0.997 (l. 607-610). Departures from CAPRI: no FORE FLOOR of a scenario (none in the Green Deal)."""
    return share * L0
