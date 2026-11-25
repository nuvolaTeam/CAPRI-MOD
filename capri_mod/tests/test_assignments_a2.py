"""The premium rules moved in block A2 (docs/dev/ASSIGNMENTS_REFACTOR_PLAN.md): each function on CAPRI's statement,
its conditions (None: the record left as it is) and GAMS's EPS. The callers' results are unchanged by construction (the
same operations in the same order; a sum of floats where the code summed, a loop where it accumulated)."""
import math

import pytest

from capri_mod.policy.equations import (aggreg_ppepay as AG, calc_mtr as CM, calc_mtr_top as CT, cap_2013_2020_cndp as CN,
                                        cap_2013_2020_transfers as TR, cap_2013_2020_vcs as VC, cap_2014_2020 as C14,
                                        def_endcut as EC, def_no_policy as NO, def_policy as DP, extend_rd_baseline as RD,
                                        implement_bps as B, mtr_until2013 as MU, nordicaid as NA_, policy as PO, prmcut as PC)
from capri_mod.policy.equations._gams import EPS, NA, above_eps, as_number, gams_sum, nonzero


def test_gams_values():
    assert nonzero(EPS) and not nonzero(0.0) and not nonzero(None) and nonzero(-1.0)
    assert not above_eps(EPS) and above_eps(1e-9) and not above_eps(None)
    assert gams_sum([EPS, 0.0, None]) == EPS and gams_sum([]) is None and gams_sum([1.0, EPS, 2.0]) == 3.0
    assert as_number(EPS) == 0.0 and as_number(None) == 0.0
    with pytest.raises(ValueError):
        as_number(NA)


def test_bps_convergence_statements():
    # a BPS region of two units: the ceilings, entitlements, the tunnel and the 30% rule
    assert B.p_premDataE_ceilval_fill(0.0, 5.0) == 5.0 and B.p_premDataE_ceilval_fill(4.0, 5.0) == 4.0
    assert B.ord_bpsYear(2017) == 3
    assert B.p_premData_ceillev([1.0, 2.0, 3.0]) == 6.0
    assert B.p_premDataE_ceilval(2.0, 100.0, 8.0) == 2.0 * 100.0 / 8.0
    assert B.p_bps_aiuv(10.0, 0.0) == 0.0 and B.p_bps_aiuv(10.0, 50.0) == 200.0
    assert B.p_bps_noConvergence(3.0, 20.0) == 150.0
    assert B.ybpsPre([2015, 2016, 2017, 2018, 2019], 2019) == [2015, 2016, 2017, 2018]
    assert B.rcur({"a": 1.0, "b": 0.0}, {"a": 1.0, "b": 0.0}) == ["a"]
    assert B.rbpsLo(90.0, 100.0) and not B.rbpsLo(100.0, 100.0) and B.rbpsUp(201.0, 200.0)
    # CAPRI's tunnel: a third of the gap closed in the first of three steps
    lo = B.p_premDataE_pgsaps_lo(60.0, 90.0, 0.5, 1, 2)
    assert lo == 60.0 + (90.0 - 60.0) * 0.5 * min(1.0, 1 / 3)
    assert B.p_premDataE_pgsaps_lo(60.0, 90.0, 1.0, 5, 2) == 90.0
    o = B.p_bps_envelopeOvershoot([10.0, 20.0], [100.0, 250.0], 5.5)
    assert math.isclose(o, (10 * 100 + 20 * 250) / 1000 - 5.5, rel_tol=1e-15)
    up = B.p_premDataE_pgsaps_linear(250.0, 200.0, o, [20.0], [250.0])
    assert math.isclose(up, 200.0 + 50.0 * (1 - o / (20.0 * 50.0 / 1000)), rel_tol=1e-14)
    assert B.p_premDataE_pgsaps_linear(200.0, 200.0, o, [20.0], [200.0]) == 200.0      # no distance: factor 0
    assert B.p_premDataE_pgsaps_rule30(100.0, 250.0) == 175.0
    # the overshoot left divided by the entitlements without the factor 1000 (K141, kept)
    assert B.p_premDataE_pgsaps_lo_overshoot(100.0, 0.2, [10.0]) == 100.0 - 0.02
    assert B.p_premData_ceilacv([100.0, 50.0], [2.0, 4.0], [1.0, 0.5]) == 100.0 * 2.0 * 1.0 / 1000 + 50.0 * 4.0 * 0.5 / 1000


def test_policy_gms_statements():
    assert PO.p_premData(NA) is None and PO.p_premData(EPS) == EPS
    assert PO.p_dataCopy_LEVL([1.0, 2.5]) == 3.5
    assert PO.p_premPaym_APPTYPE("perLivestockUnit") == 5 and PO.p_premPaym_APPTYPE(3) == 3
    assert PO.p_premPaym_PRMR(EPS, [10.0]) is None                 # EPS is a rate of its own
    assert PO.p_premPaym_PRMR(None, [10.0, EPS]) == 10.0 and PO.p_premPaym_PRMR(None, [EPS]) == EPS
    assert PO.p_premPaym_APPTYPE_inherit(5.0, None, [1, 0]) == 1
    assert PO.p_premPaym_APPTYPE_inherit(EPS, None, [1]) is None and PO.p_premPaym_APPTYPE_inherit(5.0, 2, [1]) is None
    assert PO.p_entlWght1(5.0, None, [0.5]) == 0.5 and PO.p_entlWght1(5.0, EPS, [0.5]) is None
    assert PO.p_premPaym_ApFact(1) == 1.0 and PO.p_premPaym_ApFact(3, Y=7000.0) == 7.0
    assert PO.p_premPaym_ApFact(4, HSTY=None, HSTY_CERE=5.5) == 5.5 and PO.p_premPaym_ApFact(4, HSTY=6.0, HSTY_CERE=5.5) == 6.0
    assert PO.p_premPaym_ApFact(5, LU=0.8, NONCAP=0.1) == 0.8 + 0.1 and PO.p_premPaym_ApFact(0) == 0.0
    assert PO.p_premPaym_PRMD(250.0, 0.8) == 200.0
    assert PO.p_premPaym_PRMD_reaggregate([100.0, 0.0, 300.0], [1.0, 5.0, 3.0], 9.0) == (100.0 + 900.0) / 9.0
    assert PO.p_premPaym_PRMD_reaggregate([0.0], [1.0], 1.0) is None
    assert PO.p_entlWght(None, 1) == 1.0 and PO.p_entlWght(EPS, 1) == 0.0 and PO.p_entlWght(0.5, 2, SLGT=800.0) == 0.4


def test_prmcut_and_aggregation_statements():
    assert PC.p_premPaym_Entl(10.0, 0.5) == 5.0
    assert PC.p_premData_CEILACL([1.0, 2.0]) == 3.0
    assert PC.p_premData_CEILACV([10.0], [200.0], [0.0]) == 10.0 * 200.0 * 1.0 * 0.001
    assert PC.p_premData_CEILCUT(12.0, 1.0, CEILLEV=10.0) == 10.0 / 12.0
    assert PC.p_premData_CEILCUT(8.0, 3.0, CEILLEV=10.0, CEILVAL=2.0) == 1.0 / 1.5
    assert PC.p_premData_CEILCUT(1.0, 1.0, CEILVAL=EPS) == EPS and PC.p_premData_CEILCUT(1.0, 1.0) is None
    assert PC.p_premPaym_CUTT(None, [None, 0.8, 0.5]) == 0.8 and PC.p_premPaym_CUTT(None, []) == 1.0
    assert PC.p_premPaym_CUTT(EPS, []) == 0.0 and PC.p_premPaym_CUTT(0.9, [0.5]) == 0.9
    assert PC.p_premModifFact_Y(2.0, 30.0, 60.0) == 1.0
    assert PC.p_premPaym_PRME(100.0, 0.9, 1.0) == 90.0 and PC.p_premPaym_PRME(100.0, 0.9, 1.0, 0.5) == 45.0
    assert PC.DATA_PRME([10.0, 20.0]) == 30.0
    assert AG.p_premPaym_PREMDATA_MS([100.0, 200.0], [1.0, 3.0]) == 700.0 / 4.0 and AG.p_premPaym_PREMDATA_MS([0.0], [1.0]) is None
    assert AG.p_premPaym_Total_PRME([100.0], [2.0]) == 0.2


def test_mtr_budget_statements():
    assert CM.p_premPaym_TOTAL_DPMTR([1.0, 2.0]) == 3.0
    # with modulation: the correction that meets the net ceiling
    assert CM.p_nationalCeilCut(80.0, 100.0, 10.0) == ((100.0 - 10.0) - 80.0) / 10.0 and CM.p_nationalCeilCut(0.0, 1.0, 1.0) == 0.0
    assert CM.p_premDataE_MODU_cut(10.0, -1.5) == 0.0 and CM.p_premDataE_MODU_cut(10.0, 1.0) == 20.0
    assert CM.p_nationalCeilCut_noModu(120.0, 100.0, 0.0) == 120.0 / 100.0 - 1 and CM.p_nationalCeilCut_noModu(120.0, 100.0, 1.0) == 0.0
    b = CM.p_DDPartialBudget([10.0, 0.0], [50.0, 0.0], [5.0, 0.0], [25.0, 0.0], 0.1, [100.0, 100.0])
    assert b == 10.0 * (50.0 - 5.0) / 50.0 * (1 - 25.0 / 100) * 1.1 * 100.0 / 100
    assert CM.p_DDPartialBudget([10.0], [50.0], [5.0], [100.0], 0.0, [100.0]) is None    # fully coupled
    assert CM.p_premDataE_DPFRMS_PGFRM(2.0, 400.0) == 5.0 and CM.p_premDataE_DPFRMF_PGARAB(2.0, 400.0) == 5.0


def test_mtr_top_statements():
    assert CT.p_premToDDTarget([None, None], 60.0) == 60.0 and CT.p_premToDDTarget([30.0, None], 60.0) is None
    assert CT.p_premToDDTarget([None], None) is None
    assert CT.p_premDataE_PSGROUP(None, 7.0) == 7.0 and CT.p_premDataE_PSGROUP(EPS, 7.0) is None
    assert CT.p_premDataE_APPTYPE(None, [5.0], "perLevl") == "perLevl"
    assert CT.p_premDataE_APPTYPE(None, [EPS, NA, "x", 0.0], "perLevl") is None
    assert CT.p_totalBudget([(2.0, 3.0, 4.0), (1.0, 5.0), (7.0,)]) == 24.0 + 5.0 + 7.0
    assert CT.p_totalBudget_factor(30.0, 15000.0) == 2.0 and CT.p_premDataE_DpAgEU10(3.0, 2.0) == 6.0
    assert CT.DATA_column("LEVL", True) == "TRD" and CT.DATA_column("LEVL", False) == "BAS"
    assert CT.DATA_column("SLGT", True) == "BAS" and CT.DATA_column("HSTY", False) == "Y"
    assert CT.p_premDataE_MODU(100.0, [4.0, 1.0]) == 100.0 * 5.0 * 0.01


def test_mtr_until2013_rules():
    assert MU.p_premDataE_DPMTR_CEILVAL(5.0) == 5.0
    assert MU.p_premDataE_DPMTR_CEILVAL_net([None, 2.0, EPS], 7.0) == 7.0 and MU.p_premDataE_DPMTR_CEILVAL_net([None], 7.0) is None
    assert MU.p_premDataE_dpSaps_ceilVal(None) is None and MU.p_premDataE_dpSaps_ceilVal_net(EPS, 3.0) == 3.0
    assert MU.p_premDataE_CEILVAL_fill(None, 4.0) == 4.0 and MU.p_premDataE_CEILVAL_fill(EPS, 4.0) is None
    assert MU.p_premDataE_dpSaps_ceilLev(1.0, 0.0) == 0.0 and MU.p_premDataE_dpSaps_ceilLev(None, 9.0) is None
    assert MU.p_premDataE_dpSaps_ceilLev_UAAR(1.0, None, 9.0) == 9.0 and MU.p_premDataE_dpSaps_ceilLev_UAAR(1.0, 2.0, 9.0) is None
    assert MU.p_premDataE_dpSaps_pgSaps(400.0, 100.0, 400.0, 1000.0) == 250.0
    assert MU.p_premDataE_where(EPS, "perLevl") == "perLevl" and MU.p_premDataE_where(None, 180.0) is None
    assert MU.p_premDataE_DPPULS_PGPROT(None) == EPS and MU.p_premDataE_DPPULS_PGPROT(1.0) is None
    assert MU.p_premDataE_DPDWHETR_PGDWHE(["285.", "40"]) == 325.0
    assert MU.p_premDataE_DPDCOW_PGDCOW(2030, 2006, 24.49) == 24.49 and MU.p_premDataE_DPDCOW_PGDCOW(2006, 2006, 24.49) is None
    assert MU.p_premDataE_DPDCOW_CEILVAL(24.49, 1000.0) == 24490.0
    assert MU.p_premDataE_DPNE_DCOW_CEILVAL(10.0, "1.42") == 14.2 and MU.p_premDataE_DPNE_DCOW_CEILVAL(EPS, "1.42") is None
    assert MU.p_premDataE_AT_DPSCOW_CEILLEV(100.0, "50.", add=True) == 150.0
    assert MU.p_premDataE_AT_DPSCOW_CEILLEV(None, "50.", add=False) == -50.0
    assert MU.p_percAffByModulation_Tot([50.0, 30.0], [0.10, 0.14]) == 50.0 * 0.10 + 30.0 * 0.14
    assert MU.p_couplPercent_fill(None, 25.0) == 25.0 and MU.p_couplPercent_fill(None, None) is None
    assert MU.p_couplPercent(EPS) == 0.0 and MU.p_couplPercent(25.0) == 25.0
    assert MU.p_premToDDTarget_E_fill(None, EPS) == EPS and MU.p_premToDDTarget(EPS) is None
    assert MU.p_premToDDTarget_rule(67.0, 2030, 2006) == 67.0 and MU.p_premToDDTarget_rule(67.0, 2005, 2006) is None


def test_rd_extension_statements():
    assert RD.p_rdBudget_plan(None, 5.0) == 5.0 and RD.p_rdBudget_plan(EPS, 5.0) is None
    assert RD.p_rdSpendingPeriod_abs([1.0, EPS]) == 1.0 and RD.p_rdSpendingPeriod_nobs([1.0, EPS, 0.0, 2.0]) == 2
    assert RD.p_rdSpendingPeriod_weight(EPS, 10.0) == EPS and RD.p_rdSpendingPeriod_weight(None, 10.0) is None
    assert RD.p_rdSpendingPeriod_weight(2.0, 10.0) == 0.2
    # rule 3, else rule 4's key; EPS over EPS is EPS
    assert RD.p_rdSpendingPeriod_weight_shock(3.0, 12.0, 0.7) == 0.25
    assert RD.p_rdSpendingPeriod_weight_shock(None, None, 0.7) == 0.7
    assert RD.p_rdSpendingPeriod_weight_shock(EPS, EPS, 0.7) == EPS
    with pytest.raises(ValueError):
        RD.p_rdSpendingPeriod_weight_shock(1.0, EPS, 0.7)
    assert RD.p_rdSpendingPeriod_weight_sum([0.2, EPS]) == 0.2 and RD.p_rdSpendingPeriod_weight_scaled(0.2, 0.5) == 0.4
    assert RD.p_rdSpendingPeriod_rest(10.0, 12.0) == 0.0 and RD.p_rdSpendingPeriod_rest(10.0, EPS) == 10.0
    assert RD.p_rdBudget_spend(6.0, 4, 7) == 2.0
    assert RD.p_rdBudget_spend_from_above(6.0, 0.25, 0.5, 4, 7) == 6.0 * 0.25 / 0.5 / 3
    assert RD.p_rdSpendingPeriod_ave(EPS, 7) == EPS and RD.p_rdSpendingPeriod_ave(None, 7) is None
    assert RD.p_rdSpendingPeriod_ave(14.0, 7) == 2.0


def test_cap14_and_national_statements():
    assert C14.p_2013_1307_AnnexII(None, 5.0) == 5.0 and C14.p_2013_1307_AnnexII(0.0, 5.0) == 0.0
    assert C14.p_premDataE_DPGREEN_CEILVAL(0.3, 100.0) == 30.0 and C14.p_premDataE_share_CEILVAL(2.0, 100.0) == 2.0
    assert C14.p_premDataE_dp_bps_CEILVAL(100.0, 10.0, 30.0, [2.0, 5.0, 0.0]) == 53.0
    assert C14.p_premDataE_AppType(1.0) == "perLevl" and C14.p_premDataE_AppType(0.0) is None
    assert TR.p_cap_2013_2020_transfers_dp_rd(200.0, 5.0) == 10.0
    assert TR.p_cap_2013_2020_transfers_dp_rd_fill(None, 10.0) == 10.0
    assert TR.p_premDataE_natCeilCAP14(5.0, 10.0) == 0.0 and TR.p_premDataE_natCeilCAP14(50.0, 10.0) == 40.0
    assert VC.p_premDataE_CEILVAL(None, 3.0) == 3.0 and VC.p_premDataE_apptype(0.0) is None and VC.p_premDataE_apptype(2.0) == "perLevl"
    assert CN.p_premDataE_PSGROUP(2.0, 400.0) == 5.0
    assert EC.p_entlLimit_cut(30.0, 600.0) == 50.0
    assert DP.p_premDataE_last({2015: 1.0, 2020: 2.0, 2040: 3.0}, 2030) == 2.0 and DP.p_premDataE_last({2040: 3.0}, 2030) is None
    assert NO.p_norwPremPact(100.0, 1.2) == 120.0 and NO.p_norwPremPact(100.0) == 100.0
    assert NA_.p_premDataE_psGroup([0.5, 0.25], [100.0, 40.0]) == 60.0
    assert NA_.p_premDataE_appType(False, [0.0, 3.0], "perLevl") == "perLevl" and NA_.p_premDataE_appType(False, [0.0], "perLevl") is None
