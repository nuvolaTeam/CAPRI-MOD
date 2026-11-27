r"""CAPRI's supply model's calibration parameters set in supply/pmp.gms (star 3.0): the on-farm share of an output, the
part of its production the farm does not market or feed (seed, losses), which values a fodder at the solution
(reports/sol_simy.gms l. 753, coupling/equations/sol_simy.py DATA_UVAG_FODDO). tools/build/build_fodder_onfarm_share.py
applies it to CAPRI's data of the year (KNOWN_ISSUES K213).
"""
from __future__ import annotations


def p_onFarmShare(oms, SEDF_MS, SEDM_MS, LOSF_MS, GROF_MS, LOSF_STRA_RS=0.0, GROF_STRA_RS=0.0):
    r"""p_onFarmShare(RS, OMS): the share of a region's output OMS used or lost on the farm: for any output but straw
    its member state's seed (SEDF, SEDM) and losses (LOSF) over its production (GROF), for straw 0.9 of the region's
    own losses over its production.

    CAPRI's GAMS (supply/pmp.gms l. 41-49):

          p_onFarmShare(RS,OMS) =
                               SUM(MAP_RR(MS,RS) $ DATA(MS,"GROF",OMS,"CUR"),
                                  (DATA(MS,"SEDF",OMS,"CUR")
                                  +DATA(MS,"SEDM",OMS,"CUR")
                                  +DATA(MS,"LOSF",OMS,"CUR")
                                     )/DATA(MS,"GROF",OMS,"CUR")) $ (NOT SAMEAS(OMS,"STRA"))

                              +   (DATA(RS,"LOSF","STRA","CUR") * 0.9
                                  /DATA(RS,"GROF","STRA","CUR")) $ (SAMEAS(OMS,"STRA") and DATA(RS,"GROF","STRA","CUR"));

    In this project's notation: s = (SEDF + SEDM + LOSF) / GROF of the member state (0 without its production), for
    straw s = 0.9 LOSF / GROF of the region; the items at "CUR", the simulation year's data (the base year: at "BAS"; 2030:
    sim_ini_21730's DATA at "TRD", from which the baseline's "CUR" starts: the seed bought, SEDM, has no value at "Y"
    there, so "Y" serves only the outputs without it, the fodders).

    Departures from CAPRI: none."""
    if str(oms) == "STRA":
        return 0.9 * float(LOSF_STRA_RS) / float(GROF_STRA_RS) if float(GROF_STRA_RS) else 0.0
    g = float(GROF_MS)
    return (float(SEDF_MS) + float(SEDM_MS) + float(LOSF_MS)) / g if g else 0.0
