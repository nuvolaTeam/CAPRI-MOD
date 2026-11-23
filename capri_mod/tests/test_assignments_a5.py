"""The supply side's assignments moved in block A5 (docs/dev/ASSIGNMENTS_REFACTOR_PLAN.md): each function on CAPRI's
statement and its conditions. The callers' results are unchanged by construction (the same operations in the same
order)."""
import math

import numpy as np

from capri_mod.market.equations.set_prices import DATA_UVAG_DWHE, DATA_UVAG_Y
from capri_mod.projection.equations import breeding as BR
from capri_mod.supply.equations import ghgmiti as GM
from capri_mod.supply.equations import set_fert_priors as FP
from capri_mod.supply.equations.define_const_pmp_param import p_pmpFeedInpCoeff_SLOP
from capri_mod.supply.equations.define_greening_limits import p_DPGreeningLimits_permGras
from capri_mod.supply.equations.define_inputs import TF_I_trend
from capri_mod.supply.equations.define_manure_trade_costs import p_manureBuyCostSlope
from capri_mod.supply.equations.define_objc import p_linObjeCont_PLAP
from capri_mod.supply.equations.greendeal import conventional_io as CV
from capri_mod.supply.equations.greendeal import landscape as LS
from capri_mod.supply.equations.greendeal import load_organic_targets as LO
from capri_mod.supply.equations.greendeal import minfert_redu_by_crop as MR
from capri_mod.supply.equations.greendeal.organic_area import DATA_Yild_percentageChange
from capri_mod.supply.equations.greendeal.organic_io import DATA_INPO_BAS_topup
from capri_mod.supply.equations.greendeal.surptot import data_SURTOT_MAXS
from capri_mod.supply.equations.prep_cal import p_dualGreening
from capri_mod.supply.equations.prep_sim_luc import v_actLevl_bounds_foreOlndArtif, v_actLevl_lo_floor
from capri_mod.supply.equations.set_supply_bounds import v_actLevl_up_FALL


def test_the_prices_to_the_supply_models():
    assert DATA_UVAG_Y(0.1, 0.8) == 0.1 * 0.8 and DATA_UVAG_DWHE(0.5, 0.1) == 0.05


def test_the_green_deal_input_changes():
    # the organic target alone: PLAP -o_R; the pesticide target above it: PLAP -r, INPO + (r - o_R)
    assert CV.DATA_GROF_percentageChange(0.0, 0.2) == (-0.2, 0.0)
    assert CV.DATA_GROF_percentageChange(0.5, 0.2) == (-0.5, 0.5 - 0.2)
    assert CV.DATA_GROF_percentageChange(0.1, 0.2) == (-0.2, 0.0)          # the organic part covers the target
    assert CV.DATA_GROF_percentageChange(0.0, 0.0) == (0.0, 0.0)
    assert CV.p_yildReduction(0.10, 0.5) == 0.10 and CV.p_yildReduction(0.10, 0.25) == 0.05
    assert CV.DATA_Yild(8.0, 0.1, 0.75) == 8.0 * (1.0 - 0.1 * 0.75)
    assert DATA_INPO_BAS_topup(0.2, 50.0) == 20.0
    assert DATA_Yild_percentageChange(float("nan"), -25.0) == 0.25 and DATA_Yild_percentageChange(-10.0, -25.0) == 0.1
    assert DATA_Yild_percentageChange(None, None) == 0.0
    assert LO.p_organicTargetScale(0.25, 12.0, 25.0) == 1.0 and LO.p_organicTargetScale(0.10, 12.0, 25.0) == 0.0
    assert LO.p_organicAreaTarget(30.0, 1.0) == 0.3 and LO.p_organicAreaTarget(130.0, 1.0) == 1.0
    assert p_linObjeCont_PLAP(100.0, 0.0, 0.93, True, 1.25) == 80.0
    assert p_linObjeCont_PLAP(100.0, -0.5, 0.93, False, 1.0) == 100.0 * (0.5 / 0.93)
    assert TF_I_trend(0.005, 2030, 2017) == 1.0 - 0.005 * 13


def test_the_landscape_and_greening_limits():
    assert LS.DATA_FALL_FLOOR(0.10, 3.0, 1000.0, 5.0) == 1.0 * 0.03 * 1000.0 + 5.0
    X, T = [40.0, 60.0], 100.0
    H = -sum(x / T * math.log(x / T) for x in X)
    assert LS.p_DPGreeningLimits_cropDiv(H, X, T, 0.0) == min(H, H)
    assert LS.p_DPGreeningLimits_cropDiv(H, X, T, 50.0) < H                 # the floor evens the shares: lower limit
    assert p_DPGreeningLimits_permGras([10.0, 5.5]) == 15.5
    assert p_dualGreening(300.0, 120.0) == -180.0


def test_the_fertiliser_priors_and_the_mineral_reduction():
    var = FP.p_priFertDist_var(100.0, 1.0)
    beta = FP.p_priFertDist_beta(100.0, var)
    alpha = FP.p_priFertDist_alpha(beta, var)
    assert var == 10000.0 and math.isclose((alpha - 1.0) / beta, 100.0, rel_tol=1e-12)    # the gamma's mode
    b1 = FP.p_priFertDistRegu_beta1(0.75, 0.25)
    assert (b1, FP.p_priFertDistRegu_beta2(0.25, b1)) == (1.1875, 1.0625)
    assert MR.p_checkSmallMine(20.0, False, 30.0) and MR.p_checkSmallMine(80.0, True, 30.0)
    assert not MR.p_checkSmallMine(80.0, False, 30.0) and not MR.p_checkSmallMine(0.0, True, 30.0)
    assert MR.p_nMaxPerHa_MIN(80.0, 0.2, False) == 80.0 * 0.8 and MR.p_nMaxPerHa_MIN(20.0, 0.2, True, 1.1) == 22.0
    assert MR.p_priFertDistRegu_limCres(40.0, 1.3) == 52.0
    assert data_SURTOT_MAXS(120.0, 0.5) == 60.0


def test_the_mitigation_options():
    assert GM.p_ghgMiti_QEmitt_NITR_INH(0.01, 0.9) == 0.9 * 0.01
    assert GM.p_ghgMiti_maxShare_N2OMAN(30.0, 120.0) == 0.75 and GM.p_ghgMiti_maxShare_N2OMAN(0.0, 0.0) == 0.0
    assert GM.p_ghgMiti_relSubs(1.0, False, 1.2, 0.2, 0.8) == (1.2, 0.2)
    assert GM.p_ghgMiti_relSubs(0.6, False, 1.2, 0.2, 0.8) == (0.8, 0.0)
    assert GM.p_ghgMiti_relSubs(0.6, True, 1.2, 0.2, 0.8) == (1.2, 0.2)    # not the nitrification inhibitor
    assert GM.p_ghgMiti_pmpParsqr(10.0, 1.2, 0.2, 0.5, 0.0) == 20.0
    s = GM.p_ghgMiti_pmpParsqr_saving(0.5, 100.0, 0.0, 1.0)
    assert s == 0.5 * 100.0 * (1.5 ** -2 - 1.0) / 1.0 and GM.p_ghgMiti_pmpParsqr_saving(0.5, 100.0, 0.5, 0.5) == 0.0
    v = GM.p_ghgMiti_othImpact_EmiCalmin([0.1, 0.02, 0.01, 0.2], [-0.5, None, -0.3, 0.1], 0.5)
    assert v == -(abs(0.1 * -0.5 + 0.0 + 0.01 * -0.3 + 0.2 * 0.1) ** 0.5)
    assert GM.p_ghgMiti_othImpact_EmiCalmin([0.1], [None], 0.5) == 0.0


def test_the_breeding_options():
    assert BR.p_ghgMiti_maxShare_genet(0.8, 0.002) == 0.8 * 0.002
    assert BR.p_ghgMiti_othImpact_genet(-0.5, 0.1) == -0.05
    assert BR.p_ghgMiti_costParLin_genet(2.0, 30.0, 0.1) == 3.0 and BR.p_ghgMiti_costParLin_genet(2.0, 10.0, 0.1) == 2.0
    assert BR.p_ghgMiti_pmpParsqr_genet(10.0, 1.2, 0.2, 9.5, 0.2) == 2.0     # the floor binds
    assert BR.p_ghgMiti_pmpParsqr_genet(10.0, 1.2, 0.2, 1.0, 0.2) == 9.0


def test_the_supply_bounds_and_slopes():
    lo, up = v_actLevl_bounds_foreOlndArtif(100.0, 1000.0, 0.9, 0.35, 9.0, 0.35)
    assert (lo, up) == (100.0 - 90.0, 100.0 + 350.0)
    assert v_actLevl_lo_floor(200.0, 0.99) == 198.0
    assert v_actLevl_up_FALL(0.5, 2, 300.0) == 300.0
    assert p_manureBuyCostSlope(0.05, 200.0) == 0.025
    s = p_pmpFeedInpCoeff_SLOP(np.array([0.05, 0.3]), 0.2, np.array([1.0, 2.0]), np.array([10.0, 3.0]))
    assert s.tolist() == [0.05 / 10.0, 0.3 / 6.0]


def test_the_rows_across_blocks():
    import pandas as pd
    from capri_mod.coupling.equations.price_forecast import DATA_UVAG_forecast
    from capri_mod.market.equations.manuremarket.simu_manure_market import p_excessSupplyFromSupMod
    from capri_mod.market.equations.welfare import p_welfareRes_Welfare
    from capri_mod.policy.equations.def_endcut import p_entlLimit_Limit
    assert DATA_UVAG_forecast((0.55, 0.30, 0.15), [10.0, 20.0]) == (0.55 * 10.0 + 0.30 * 20.0) / sum((0.55, 0.30))
    s = DATA_UVAG_forecast((0.5, 0.5), [pd.Series([1.0, 2.0]), pd.Series([3.0, 4.0])])
    assert s.tolist() == [2.0, 3.0]
    assert GM.p_ghgMiti_othImpact_mitisyn(0.3, 0.1, 0.5) == 1.0 - 0.5 + 0.5 * 0.7 * 1.1
    assert p_excessSupplyFromSupMod(5.0, 2.0) == 3.0 and p_entlLimit_Limit([1.0, 2.0]) == 3.0
    assert FP.v_fertDistPartialSlack_bound(0.002, False, 0.1) == 0.002 and FP.v_fertDistPartialSlack_bound(1.0, True, 0.1) == 1.1
    df = pd.DataFrame({"CSSP": [1.0, 2.0], "TariffRev": [0.5, 0.0]}, index=["A", "B"])
    assert p_welfareRes_Welfare(df).tolist() == [1.5, 2.0]
