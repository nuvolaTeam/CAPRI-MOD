"""The rural development declarations' assignments moved in block A6 (policy/rd_logic.gms;
docs/dev/ASSIGNMENTS_REFACTOR_PLAN.md): each function on CAPRI's statement and its conditions (None: the record left
or gone). The caller's results are unchanged by construction (the same operations in the same order)."""
from capri_mod.policy.equations import rd_logic as RL
from capri_mod.policy.equations._gams import EPS


def test_the_money_summed_up_where_a_region_has_none():
    assert RL.p_rdBudget_SRNUTS1(None, [1.5, 2.0]) == 3.5 and RL.p_rdBudget_SRNUTS1(0.0, [1.5]) == 1.5
    assert RL.p_rdBudget_SRNUTS1(4.0, [1.5]) is None                         # its own money kept
    assert RL.p_rdBudget_SRNUTS1(EPS, [1.5]) is None                         # EPS is money in a $ condition
    assert RL.p_rdBudget_MS(None, [EPS, 0.0]) == EPS and RL.p_rdBudget_MS(None, []) is None


def test_the_land_partition_and_the_levels():
    assert RL.p_landPartition_SRNUTS1([10.0, 5.0]) == 15.0 and RL.p_landPartition_MS([1.0, 2.0, 3.0]) == 6.0
    assert RL.DATA_LEVL_nuts1a([0.5, 0.25]) == 0.75
    assert RL.p_landPartition_share(30.0, 120.0) == 30.0 / 120.0 and RL.p_landPartition_share(30.0, 0.0) is None


def test_fadn_completed():
    assert RL.p_fadn_BL000000(1200.0, 35.0) == 1235.0 and RL.p_fadn_BL000000(0.0, 35.0) == 35.0
    assert RL.p_fadn_Total([1.0, 2.0, 4.0]) == 7.0 and RL.p_fadn_Tot(3.0, 4.5) == 7.5
    assert RL.p_aeLfa(5000.0, 40.0, 60.0) == 50.0
    assert RL.p_aeLfa(5000.0, 0.0, 0.0) is None and RL.p_aeLfa(0.0, 40.0, 60.0) is None


def test_the_ceilings_and_their_split_by_farm_type():
    # each measure's spend, its plan where nothing is spent, plus EPS: a region without money keeps an EPS ceiling
    assert RL.p_premDataE_ceilval([(3.0, 9.0), (None, 2.0)]) == 5.0
    assert RL.p_premDataE_ceilval([(EPS, 9.0)]) == EPS and RL.p_premDataE_ceilval([(None, None)]) == EPS
    assert RL.p_premDataE_ceilval([]) is None
    assert RL.p_premDataE_ceilval_ae_fadn(10.0, 30.0, 120.0) == 10.0 * (30.0 / 120.0)
    assert RL.p_premDataE_ceilval_ae_fadn(EPS, 30.0, 120.0) == EPS
    assert RL.p_premDataE_ceilval_ae_area(10.0, 0.0, 50.0) is None          # no share: the record gone
    assert RL.p_premDataE_ceilval_ae_levels(8.0, 25.0, 100.0) == 8.0 * (25.0 / 100.0)


def test_the_rates():
    assert RL.p_premDataE_DPRD_LFA(250.0, 0.4) == 250.0 * 0.4 and RL.p_premDataE_DPRD_LFA(250.0, 0.0) is None
    assert RL.p_premDataE_DPRD_N2K(500.0, 0.1) == 500.0 * 0.1 and RL.p_premDataE_DPRD_N2K_PGGRZE(500.0, 0.0) is None
    s, a, b = 0.3, 120.0, 40.0
    assert RL.p_premDataE_ae([s, s], a, b) == (s * a + (1 - s) * b) * 2
    assert RL.p_premDataE_ae([1.0], 5000.0, 0.0) == 2000.0                   # at most 2000 EUR per ha


def test_the_weights_and_the_scaling():
    assert RL.p_entlWght1_heavy(0.8) == 0.4 and RL.p_entlWght1_heavy(EPS) == EPS
    # the weight 1 where there is none, 0 for EPS; the rate 0 for EPS
    terms = [(100.0, None, 50.0), (20.0, 0.5, 80.0), (10.0, EPS, 30.0), (5.0, 1.0, EPS)]
    tot = RL.p_scaleRdPpePay_sum(terms)
    assert tot == 100.0 * 1.0 * 50.0 * 0.001 + 20.0 * 0.5 * 80.0 * 0.001
    assert RL.p_scaleRdPpePay(3.0, tot) == 3.0 / tot and RL.p_scaleRdPpePay(EPS, tot) == EPS
    assert RL.p_scaleRdPpePay(3.0, 0.0) == 0.0
    f = 0.4
    assert RL.p_premDataE_scaled(100.0, f) == 100.0 * f * 1.5
    assert RL.p_premDataE_scaled(5000.0, f) == 2000.0                        # at most 2000 EUR per ha
    assert RL.p_premDataE_scaled(100.0, EPS) == EPS and RL.p_premDataE_scaled(EPS, f) == EPS
    assert RL.p_premDataE_scaled(100.0, 0.0) is None and RL.p_premDataE_scaled(EPS, 0.0) is None
