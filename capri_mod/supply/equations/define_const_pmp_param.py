r"""CAPRI's constant PMP parameters (supply/pmp_terms/define_const_pmp_param.gms, star 3.0): the feeds' slope, where
CAPRI's calibrated slope is missing.

capri_mod/feed/ration.py (Ration.__init__) calls it.
"""
from __future__ import annotations

import numpy as np


def p_pmpFeedInpCoeff_SLOP(UVAG, UVAG_FCER, elasticity, feeding):
    r"""p_pmpFeedInpCoeff(regions, MAACT, A, FEED, "SLOP"): a feed's PMP slope, its price per kg (at least 10% of the
    cereals', FCER) over its own-price elasticity times the feeding (arrays over the feeds).

    CAPRI's GAMS (supply/pmp_terms/define_const_pmp_param.gms l. 104-124):

             p_pmpFeedInpCoeff(%regions%,MAACT,A,FEED,"SLOP") = 0;

             p_pmpFeedInpCoeff(%regions%,MAACT,A,FEED,"SLOP")
               = ( 1./p_assumedOwnPriceFeedElas(%regions%,FEED)
        *
        *        -- price pro kg product weight, but at least 10% of cereal prices
        *
                  * SUM(R_RAGG(%regions%,MS),
                         ABS( MAX(0.1*DATA(MS,"UVAG","FCER","Y")/1000,DATA(MS,"UVAG",FEED,"Y")/1000.))
        *
        *        -- divided by the smaller of 10 % of dry matter, divided by the dry matter content of the feed
        *                                     or the actual feeding in kg per year
        *
                      /MAX(p_animReq(%regions%,MAACT,A,"DRMA")*MIN(0.1,p_dryMatShareFeedSector(MS,FEED))
                                            * (    1 $ v_feedInpCoeff.L(%regions%,MAACT,A,FEED)
                                               + 0.1 $ (NOT v_feedInpCoeff.L(%regions%,MAACT,A,FEED)))
                                     *p_animProdDays(%regions%,MAACT,A)/DATA(MS,"DRMA",FEED,"Y"),
                           v_feedInpCoeff.L(%regions%,MAACT,A,FEED)))

                 ) $ (     DATA(%regions%,MAACT,"LEVL","Y")*p_technFact(%regions%,MAACT,"LEVL",A)
                       AND p_maxFeedShare(%regions%,MAACT,A,FEED));

    In this project's notation: s = max(p, 0.1 p_FCER) / (e x). Departures from CAPRI: divided by the feeding itself
    (CAPRI's max of it and 10% of the dry matter requirement), in the model's units; used only where CAPRI's own
    calibrated slope is missing (the caller's)."""
    return np.maximum(UVAG, 0.1 * UVAG_FCER) / (elasticity * feeding)
