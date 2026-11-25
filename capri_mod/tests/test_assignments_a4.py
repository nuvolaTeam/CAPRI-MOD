"""The coupling's and the market's assignments moved in block A4 (docs/dev/ASSIGNMENTS_REFACTOR_PLAN.md): each function
on CAPRI's statement and its conditions (None: the record left as it is). The callers' results are unchanged by
construction (the same operations in the same order)."""
import math

import numpy as np

from capri_mod.coupling.equations import define_stepweights as DS
from capri_mod.coupling.equations import price_forecast as PF
from capri_mod.coupling.equations import simu_calibration_to_supply as SC
from capri_mod.coupling.equations import sol_simy as SS
from capri_mod.market.equations import def_biofuel_params as BF
from capri_mod.market.equations import set_start_val as SV
from capri_mod.market.equations import sol_market as SM
from capri_mod.market.equations import welfare as W
from capri_mod.market.equations.manuremarket import simu_manure_market as MM
from capri_mod.supply.equations.impose_upper_bound_on_elasticity import p_pmpQuadTechn_dampening


def test_the_stop_rule_statements():
    assert PF.p_iterChg(110.0, 90.0) == 200.0 * 20.0 / 200.0 and PF.p_iterChg(0.0, 0.0) == 0.0
    # the aggregate's price: the first step's production as the weight, members below 10 x 0.5 kt out
    p = PF.p_itemsInIters_UVAG([10.0, 3.0, 8.0], [20.0, 4.0, 10.0], [100.0, 999.0, None], 0.5)
    assert p == 100.0
    assert PF.p_itemsInIters_UVAG([10.0, 10.0], [20.0, 60.0], [100.0, 200.0], 0.5) == (20 * 100 + 60 * 200) / 80
    assert PF.p_itemsInIters_UVAG([0.0], [20.0], [100.0], 0.5) is None
    assert PF.p_iterChg_UVAG(100.0, 100.04, 50.0, 0.5, 0.05) is None          # moved by less than EUR 0.05
    assert PF.p_iterChg_UVAG(100.0, 101.0, 4.0, 0.5, 0.05) is None            # the aggregate produces too little
    assert PF.p_iterChg_UVAG(100.0, 101.0, 50.0, 0.5, 0.05) == PF.p_iterChg(100.0, 101.0)
    assert PF.p_iterChg_quantity(10.0, 10.4, 0.0, 0.5) is None
    assert PF.p_iterChg_quantity(10.0, 11.0, 50.0, 0.5) == 50.0                # the row's larger change kept
    assert PF.p_iterChg_NO000000(15, 15) and not PF.p_iterChg_NO000000(14, 15)
    assert PF.p_iterChg_TOT([0.2, 1.5, 0.7]) == 1.5 and PF.p_iterChg_TOT([]) == 0.0
    assert PF.p_iterChg_TOT_MAX([0.3], 1) == 1.0 and PF.p_iterChg_TOT_MAX([0.3], 2) == 0.3
    # more than two rows above p_minIterChg: the maximum; two or fewer: 0 (stop); the first step goes on
    assert PF.p_iterChg_TOT_MAX_CUR(0.3, [0.3, 0.2, 0.1], 0.05, 3) == (0.3, 3)
    assert PF.p_iterChg_TOT_MAX_CUR(0.3, [0.3, 0.2, 0.01], 0.05, 3) == (0.0, 2)
    assert PF.p_iterChg_TOT_MAX_CUR(1.0, [0.01], 0.05, 1) == (1.0, 0)
    assert DS.p_stepWgtSpecial(0.3, 2) == [max(0.0, 1 - 0.3 * 3), 1 - 0.3 * 2, 1 - 0.3]


def test_the_supply_hand_over_and_the_land_rent():
    assert SC.p_itemsInIters_prod(100.0, 0.95) == 95.0 and SC.p_itemsInIters_prod(100.0, 0.0) == 0.0
    assert SC.DATA_Prod_OMYANI(5.0, 20.0, 12.0) == 13.0
    assert SS.DATA_ProfitLandUse([300.0, 150.0, 0.0], [50.0, 0.0, 0.0], [10.0, 4.0, 1.0]) == 250.0 * 10 + 150.0 * 4


def test_the_consumer_welfare():
    B = np.array([[2.0, 0.5], [0.0, 1.0]])
    Bs = W.p_pbGL(B)
    assert Bs[1, 0] == 0.5 and Bs[0, 1] == 0.5 and W.p_pbGL(Bs).tolist() == Bs.tolist()
    p = W.PS_Y(np.array([1.0, 2.0, 3.0]), np.array([0.5, 1.2]), np.array([1.0, 1.0, 1.0]), np.array([True, True, False]))
    assert p.tolist() == [0.5, 2.2, 3.0]
    assert W.PS_Y(np.array([1.0]), np.array([0.0]), np.array([2.0]), np.array([True]))[0] == 0.05   # the 5% floor
    d, Y, p0, p1 = np.array([0.1, 0.2]), 10.0, np.array([1.0, 1.0]), np.array([1.1, 1.0])
    G = lambda q: float(np.sqrt(q) @ Bs @ np.sqrt(q))
    ev = W.p_welfareRes_CSSP(Bs, d, Y, p0, p1)
    assert ev == G(p0) / G(p1) * (Y - float(d @ p1)) - (Y - float(d @ p0))
    assert W.p_welfareRes_CSSP(Bs, d, Y, p0, p0) == 0.0


def test_the_industries_profits():
    assert W.p_welfareRes_ProfitProc(10.0, -2.0, 5.0) == 45.0
    assert W.p_welfareRes_ProfitProc_RESIMPX(12.0, 100.0, 1.1, 10.0) == (12.0 * 100.0 * 1.1 - 1000.0) / 1000.0
    assert W.p_welfareRes_ProfitProc_XXBIOF(50.0, 20.0, 40.0, 18.0) == (1000.0 - 720.0) / 1000.0
    assert W.p_welfareRes_ProfitFeed(200.0, 1.1, 10.0, -1.0) == 200.0 * 0.10000000000000009 * 9.5
    assert SM.DATA_ProcMarg_XXBIOF(800.0, 1.0, 650.0) == 150.0


def test_the_quota_rent():
    base, X = np.array([100.0, 200.0]), np.array([3.0, 1.0])
    ta, ts = np.array([20.0, np.nan]), np.array([5.0, 0.0])
    r = SM.p_trqBilat_Rent(base, ta, 5.0, ts, 0.0, X, 2.0, 4.0)
    assert r.tolist() == [(100.0 * 15 / 100 + 5.0) * 3.0 * 0.5, 0.0]     # NaN read as 0; the wedge at least 0
    assert SM.p_trqBilat_Rent(base, ta, 5.0, ts, 0.0, X, 10.0, 4.0)[0] == 20.0 * 3.0   # quota not filled


def test_the_bounds_the_ces_and_the_dampening():
    lo, up = SV.v_procQuant_bounds(np.array([0.5, 200.0]), 1e-5, 1e3)
    assert lo.tolist() == [0.5e-5, 200.0 * 1e-5] and up.tolist() == [1000.0, 200000.0]
    lo, up = SV.v_marketPrice_bounds(np.array([True, False]), np.array([1.0, 0.7]), 0.1, 10.0)
    assert lo.tolist() == [0.1, 0.7] and up.tolist() == [10.0, 0.7]
    assert math.isclose(BF.p_dpCESBiof(30.0, 100.0, 200.0, 250.0, 0.5), 0.3 * (0.8 ** 0.5), rel_tol=1e-15)
    e = p_pmpQuadTechn_dampening(np.array([2.0, 10.0, 100.0]), 4.5, 8.0)
    assert e[0] == 2.0 and e[1] == min(8.0, math.sqrt(10.0) + 4.5 - math.sqrt(4.5)) and e[2] == 8.0


def test_the_manure_market_statements():
    assert MM.p_itemsInIters_PSHW(0.3, True, 0.2, 0.1) == 0.3
    assert MM.p_itemsInIters_PSHW(None, True, 0.2, 0.1) == 0.2 and MM.p_itemsInIters_PSHW(None, False, 0.2, 0.1) == 0.1
    assert MM.p_mTradeReport_losf(12.0, 10.0) == 2.0
