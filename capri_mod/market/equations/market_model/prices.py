r"""CAPRI's price equations (arm/market_model.gms l. 2842-3130, the PRICES block): the consumer price (CPri_).

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026, the supply phase); this docstring keeps the block's overview, notation and departures.

Written: CPri_ for the GL demand's goods (capri_mod/market/demand_ad.py gl_block_function).

In this project's notation (CPRI0 and ARM1P0 CAPRI's consumer and Armington prices at the calibration point, EUR/kg;
PR the model region's Armington price ratio to it):

    CPri_   p = CPRI0 + (PR - 1) ARM1P0

CAPRI's consumer price is the Armington price plus the margins (CTAX for the biofuels, CMrg, less the consumer
support CSEd and CSEi), fixed in the simulation; with the Armington price ARM1P0 x PR, that is CPRI0 + (PR - 1) ARM1P0.

Departures from CAPRI: the margins held at CAPRI's calibration point (CPRI0 - ARM1P0); the model floors the consumer
price at 5% of CPRI0 (demand_ad.py; not in CAPRI); CAPRI scales the row by CPRI + 1. The biofuels' consumer price
(capri_mod/market/biofuel_ad.py) is written apart (the biofuel block, M2).
"""
from __future__ import annotations


def CPri_(cpri0, ra, arm1p0):
    r"""CPri_(RMS, XXX) (l. 3032-3038): the consumer price, cpri0 + (ra - 1) x arm1p0 (EUR/kg): CAPRI's consumer price
    at the calibration point moved by the change of the Armington price (ra its ratio, arm1p0 CAPRI's Armington price
    at the calibration point), the margins held.

    CAPRI's GAMS, Cpri_ (l. 3032-3038):

     Cpri_(RMS,XXX) $ ( (DATA(RMS,"HCon",XXX,"CUR") or DATA(RMS,"BIOF",XXX,"CUR") $XXBIOF(XXX)) ) ..
          v_consPrice(RMS,XXX)/(DATA(RMS,"CPRI",XXX,"CUR")+1)
                               =E= SUM(RMS_TO_RM(RMS,RM), v_arm1Price(RM,XXX)
                                 + DATA(RMS,"CTAX",XXX,"CUR") $ XXBIOF(XXX)
                                 + DATA(RMS,"CMrg",XXX,"CUR")
                                 - DATA(RMS,"CSEd",XXX,"CUR")
    """
    return cpri0 + (ra - 1.0) * arm1p0
