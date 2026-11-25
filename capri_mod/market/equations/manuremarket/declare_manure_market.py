r"""CAPRI's manure pool market model (manuremarket/declare_manure_market.gms, star 3.0): the regions' surplus in the
pool market (e_mPoolSurplus) and the autarky buffer of the trade links unused at the calibration point
(p_mTradeAddCost).

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026, the supply phase); this docstring keeps the overview, notation and departures.

Written: CAPRIModel._clear_pool_capri (capri_mod/coupling/manure.py), the market m_mPoolMarket for one nutrient, as
CAPRI writes and solves it, "using nlp maximizing v_mPoolBenefits" (simu_manure_market.gms l. 160): CAPRI's variables
and its four rows e_mPoolExcessSupply, e_mPoolSurplus, e_mPoolClear, e_mPoolBenefits (the functions below), with IPOPT
for CAPRI's CONOPT, the pool price the dual of e_mPoolExcessSupply (simu_manure_market.gms l. 217, PMRK). The same
problem as a convex QP (Clarabel: the minimum of minus the benefits under one balance row per pool, the excess supply
and the surplus substituted, e_mPoolSurplus's coefficients; the model's form until 20 November 2026, a setting until
23 November 2026) is the cross-check of capri_mod/tests/test_manure_pool_nlp.py.

In this project's notation, per region r (e its exports to its pool, i its imports, z = e - i its net export; the
excess supply ES = a + b P, P the nutrient's value; cs0, cs1 and cb0, cb1 the sell and buy costs' constants and
slopes) and per link of pools k, l (buffer_k CAPRI's autarky buffer):

    e_mPoolSurplus   a / b z - z^2 / (2 b) - e (cs0 + cs1 e / 2) - i (cb0 + cb1 i / 2), written as the QP's
                     coefficients of its negative: Q_ee = 1/b + cs1, Q_ii = 1/b + cb1, Q_ei = -1/b, c_e = -a/b + cs0,
                     c_i = a/b + cb0
    p_mTradeAddCost  (buffer_k + buffer_l) / 2 on the links unused at the calibration point

Departures from CAPRI: CAPRI's calibration of the pool market at the step's start (m_mPoolMarketCal, l. 168-204: the
price wedges v_mPoolPriceCal that make the baseline trade an equilibrium) is not needed in the model's form: the
model's net exports and prices are the deviations from CAPRI's base trade, zero at the base, an equilibrium (so
e_mPoolBenefits has no calibration term); the trade cost constants cs0, cb0 from the reduced costs of the regions'
trade columns at their solution (CAPRI's calibrated constants, supply/define_manure_trade_costs.gms); the fixed
third-country exports of e_mPoolClear drop out of the pools' balances in the deviation form; p_mTradeAddCost's price
gap term (max(0, P_l - P_k - c)) zero (the pool prices equal at the base); exports bounded by the manure produced.
"""
from __future__ import annotations


def e_mPoolSurplus(a, b, cs0, cs1, cb0, cb1):
    r"""e_mPoolSurplus(rManPool, curFout) (l. 114-127), one region's surplus as the QP's coefficients of its negative
    in (e, i): (Q_ee, Q_ii, Q_ei, c_e, c_i) = (1/b + cs1, 1/b + cb1, 1/b, -a/b + cs0, a/b + cb0), Q_ei entering with a
    minus sign; a, b the excess supply's constant and slope, cs0, cs1 and cb0, cb1 the sell and buy costs'. Floats.

    CAPRI's GAMS, e_mPoolSurplus (manuremarket/declare_manure_market.gms l. 114-127):

     e_mPoolSurplus(rManPool,curFout) ..
         v_mPoolSurplus(rManPool,curFout)
             =E= sum(rManPool_to_ru(rManPool,ru),
                     p_mPoolSupConst(ru,curFout)/p_mPoolSupSlope(ru,curFout)*(v_manureExports(ru,curFout) - v_manureImports(ru,curFout))
                       - 1/(2*p_mPoolSupSlope(ru,curFout))*sqr(v_manureExports(ru,curFout) - v_manureImports(ru,curFout))
               - v_manureExports(ru,curFout)
                     * (        p_manureSellCostConst(ru,curFout)
                        + 1/2 * p_manureSellCostSlope(ru,curFout) * v_manureExports(ru,curFout))
               - v_manureImports(ru,curFout)
                     * (        p_manureBuyCostConst(ru,curFout)
                        + 1/2 * p_manureBuyCostSlope(ru,curFout) * v_manureImports(ru,curFout))
             );
    """
    be = 1.0 / b
    return be + cs1, be + cb1, be, -a * be + cs0, a * be + cb0


def e_mPoolExcessSupply(v_mPoolExcessSupply, v_manureExports, v_manureImports):
    r"""e_mPoolExcessSupply(rManPool, curFout) (l. 99-104) as a row, = 0: the pool's excess supply less the sum of its
    regions' net exports. v_manureExports, v_manureImports: sequences over the pool's regions (CasADi or floats).

    CAPRI's GAMS, e_mPoolExcessSupply (manuremarket/declare_manure_market.gms l. 99-104):

     e_mPoolExcessSupply(rManPool,curFout) ..
         v_mPoolExcessSupply(rManPool,curFout)
             =E= sum(rManPool_to_ru(rManPool,ru),
                       v_manureExports(ru,curFout)
                       -v_manureImports(ru,curFout)
                       ) ;
    """
    return v_mPoolExcessSupply - sum(e - i for e, i in zip(v_manureExports, v_manureImports))


def e_mPoolSurplus_row(v_mPoolSurplus, regions):
    r"""e_mPoolSurplus(rManPool, curFout) (l. 114-127) as a row, = 0, in CAPRI's variables (the NLP form): the pool's
    surplus less the sum over its regions of a / b z - z^2 / (2 b) - e (cs0 + cs1 e / 2) - i (cb0 + cb1 i / 2),
    z = e - i. regions: (e, i, a, b, cs0, cs1, cb0, cb1) per region, e and i CasADi expressions (e_mPoolSurplus above
    writes the same equation as a QP's coefficients).

    CAPRI's GAMS, e_mPoolSurplus (manuremarket/declare_manure_market.gms l. 114-127):

     e_mPoolSurplus(rManPool,curFout) ..
         v_mPoolSurplus(rManPool,curFout)
             =E= sum(rManPool_to_ru(rManPool,ru),
                     p_mPoolSupConst(ru,curFout)/p_mPoolSupSlope(ru,curFout)*(v_manureExports(ru,curFout) - v_manureImports(ru,curFout))
                       - 1/(2*p_mPoolSupSlope(ru,curFout))*sqr(v_manureExports(ru,curFout) - v_manureImports(ru,curFout))
               - v_manureExports(ru,curFout)
                     * (        p_manureSellCostConst(ru,curFout)
                        + 1/2 * p_manureSellCostSlope(ru,curFout) * v_manureExports(ru,curFout))
               - v_manureImports(ru,curFout)
                     * (        p_manureBuyCostConst(ru,curFout)
                        + 1/2 * p_manureBuyCostSlope(ru,curFout) * v_manureImports(ru,curFout))
             );
    """
    tot = 0
    for e, i, a, b, cs0, cs1, cb0, cb1 in regions:
        z = e - i
        tot = tot + a / b * z - 1.0 / (2.0 * b) * z * z - e * (cs0 + 0.5 * cs1 * e) - i * (cb0 + 0.5 * cb1 * i)
    return v_mPoolSurplus - tot


def e_mPoolClear(exports_out, exports_in, v_mPoolExcessSupply, exportsToThirdCountries=0.0):
    r"""e_mPoolClear(rManPool, curFout) (l. 130-140) as a row, = 0: the pool's net exports to the other pools less its
    excess supply net of the fixed third-country exports. exports_out, exports_in: v_mPoolExports(k, l) and
    v_mPoolExports(l, k) over the pool's links.

    CAPRI's GAMS, e_mPoolClear (manuremarket/declare_manure_market.gms l. 130-140):

     e_mPoolClear(rManPool,curFout) ..
         sum(rmp1 $ ((not sameas(rmp1,rManPool))
                       $ ((p_mPoolTradeCost(rmp1,rManPool) gt 0) or (p_mPoolTradeCost(rManPool,rmp1) gt 0))),
                       v_mPoolExports(rManPool,rmp1,curFout) - v_mPoolExports(rmp1,rManPool,curFout))
             =E=
         v_mPoolExcessSupply(rManPool,curFout)
             - sum(rManPool_to_ru(rManPool,ru), p_manureExportsToThirdCountries(ru,curFout,"y"));

    The model's deviation form has no third-country term (0)."""
    return sum(exports_out) - sum(exports_in) - (v_mPoolExcessSupply - exportsToThirdCountries)


def e_mPoolBenefits(v_mPoolBenefits, v_mPoolSurplus, v_mPoolExports, p_mPoolTradeCost, v_mPoolExcessSupply=(),
                    v_mPoolPriceCal=()):
    r"""e_mPoolBenefits (l. 153-157) as a row, = 0: the benefits less the pools' surplus, plus the links' trade costs
    and the calibration wedges' term (none in the model's form: v_mPoolPriceCal empty).

    CAPRI's GAMS, e_mPoolBenefits (manuremarket/declare_manure_market.gms l. 153-157):

     e_mPoolBenefits ..
         v_mPoolBenefits =E=  sum(rmp1, v_mPoolSurplus(rmp1,curFout))
                            - sum((rmp1,rmp2) $ (not sameas(rmp1,rmp2)),
                                v_mPoolExports(rmp1,rmp2,curFout)*p_mPoolTradeCost(rmp1,rmp2))
                            - sum(rmp1, v_mPoolExcessSupply(rmp1,curFout)*v_mPoolPriceCal(rmp1,curFout));
    """
    return (v_mPoolBenefits - sum(v_mPoolSurplus) + sum(t * c for t, c in zip(v_mPoolExports, p_mPoolTradeCost))
            + sum(x * w for x, w in zip(v_mPoolExcessSupply, v_mPoolPriceCal)))


def p_mTradeAddCost(buf_k, buf_l):
    r"""p_mTradeAddCost(rmp1, rmp2) (l. 427-431), the autarky buffer added to the trade cost of a link unused at the
    calibration point: (buf_k + buf_l) / 2 (the price gap term zero at the model's base). A float.

    CAPRI's GAMS, p_mTradeAddCost (manuremarket/declare_manure_market.gms l. 427-431):

     p_mTradeAddCost(rmp1,rmp2)
        $ [(sum(fout, (v_mPoolExports.l(rmp1,rmp2,fout) + v_mPoolExports.l(rmp2,rmp1,fout))) lt p_mTradeAutarkyTol)
           and sum(fout, v_mPoolExports.range(rmp1,rmp2,fout))]
        = max(0, smax(fout, v_mPoolPrice.l(rmp2,fout) - v_mPoolPrice.l(rmp1,fout) - p_mPoolTradeCost(rmp1,rmp2))
                 + (p_mTradeAutarkyBuffer(rmp1) + p_mTradeAutarkyBuffer(rmp2))/2);
    """
    return 0.5 * (buf_k + buf_l)
