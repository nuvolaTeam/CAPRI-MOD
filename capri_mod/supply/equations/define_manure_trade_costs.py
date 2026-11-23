r"""CAPRI's manure trade costs (supply/define_manure_trade_costs.gms, star 3.0): the cost slope of the traded manure.

capri_mod/supply/land.py (LandBlock._land_augment, the N, P and K pools) calls it.
"""
from __future__ import annotations


def p_manureBuyCostSlope(slope, GROF):
    r"""p_manureBuyCostSlope(regions, FOUT): the quadratic cost slope of the manure traded, EUR 50 per t for each 1% of
    the region's manure supply traded (slope: supply.manure_pool_slope, 0.05 in the model's EUR 1000 and t); the sale
    the same (p_manureSellCostSlope, l. 71).

    CAPRI's GAMS (supply/define_manure_trade_costs.gms l. 68-71):

            p_manureBuyCostSlope(%regions%,FOUT)$(p_manureSupply(%regions%,FOUT,"GROF"))
               =  50/{p_manureSupply(%regions%,FOUT,"GROF")/100};

            p_manureSellCostSlope(%regions%,FOUT)   =  p_manureBuyCostSlope(%regions%,FOUT);

    In this project's notation: s = 50 / (GROF / 100). Departures from CAPRI: the manure supply net of the base trade
    where the base trade is the region's (supply.manure_base_trade "capri", K167; the caller's GROF)."""
    return slope / (GROF / 100.0)
