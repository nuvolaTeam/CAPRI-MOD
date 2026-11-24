"""CAPTRD's estimation equations as named functions (capri_mod/pipeline/captrd/equations/equations.py): each on its
GAMS statement (captrd/equations.gms), and the NUTS 2 model's own (equations/nuts2.py). The residuals of
estimate_ms.residuals and estimate_nuts2.residuals and the objectives are unchanged by construction (the same operations
in the same order; checked exactly at CAPTRD's Step 2 points when the moves were made)."""
import casadi as ca

from capri_mod.pipeline.captrd.equations import equations as EQ
from capri_mod.pipeline.captrd.equations import nuts2 as NT


def test_the_balances_and_shares():
    assert EQ.AREAB_([10.0, 20.0], 30.0) == 0.0 and EQ.LANDUSEB_([5.0], 7.0) == -2.0
    assert EQ.GROF_([(8.0, 100.0), (2.0, 50.0)], 0.9) == (800.0 + 100.0) * 0.001 - 0.9
    assert EQ.MBAL_(100.0, True, 40.0, False, 10.0, True, [30.0, 80.0]) == 0.0      # GROF counts, MAPR not
    assert EQ.SEED_(100.0, True, [3.0, 2.0]) == 100.0 * 0.95 - 5.0
    assert EQ.HERD_(50.0, 100.0, 182.5) == 50.0 - 100.0 * 182.5 / 365


def test_the_processing_and_the_molasses_vinasse():
    assert EQ.MAPR_([(10.0, 0.5)], None, 5.0) == 0.0
    # molasses less the ethanol beets' vinasse: BIOF(SUGA) / PRCY(SUGA) x PRCY(MOLA) x 0.9
    assert EQ.MAPR_([(10.0, 0.5)], (2.0, 0.25, 0.1), 5.0) == 5.0 - (5.0 - 2.0 / 0.25 * 0.1 * 0.9)


def test_the_set_aside_and_the_rates_band():
    assert EQ.OSET_([(100.0, 10.0)], [11.0]) == 100.0 * 0.01 * 10.0 / (1.0 - 0.01 * 10.0) - 11.0
    assert EQ.PosUp_(2.0, 100.0, 3.0, 100.0) == 2.0 - (3.0 * 0.8 - 0.1)
    assert EQ.PosLo_(2.0, 100.0, 3.0, 100.0) == 2.0 - (3.0 * 1.2 + 0.1)
    assert EQ.Dailyup_(1200.0, 300.0, 0.5) == 1.2 - (0.4 + 600.0 * 0.0016)


def test_the_requirements():
    # (Const + Slope x main output) x efficiency x requirement = the feeds' contents
    r = EQ.REQS_(100.0, 0.5, [40.0, 20.0], 0.98, 1.0, [(2.0, 30.0), (1.0, 6.0)])
    assert r == (100.0 + 0.5 * 60.0) * 0.98 * 1.0 - (60.0 + 6.0)


def test_symbols_give_expressions():
    x, y = ca.SX.sym("x"), ca.SX.sym("y")
    e = EQ.PosUp_(x, y, 2.0, 4.0)
    assert float(ca.Function("f", [x, y], [e])(1.0, 8.0)) == 1.0 - (8.0 * 2.0 / 4.0 * 0.8 - 0.1)


def test_the_objective():
    # a deviation: ((v - support) / (max(sqrt(wVarErr), 0.005 x support) + 1e-5))^2 x 1000, over
    # (0.10 x support / the same)^2 + 1; a weight multiplies both; the STCM pull adds (s / max(0.05 x sg, 1e-5))^2 x 1000
    sig = max(4.0 ** 0.5, 0.005 * 100.0) + 1.0e-5
    one = ((110.0 - 100.0) / sig) ** 2 * 1000.0 / ((0.10 * 100.0 / sig) ** 2 + 1.0)
    assert EQ.SSQS_([(110.0, 100.0, 4.0, None)]) == one
    assert EQ.SSQS_([(110.0, 100.0, 4.0, 0.5)]) == ((110.0 - 100.0) / sig) ** 2 * 0.5 * 1000.0 / ((0.10 * 100.0 / sig) ** 2 * 0.5 + 1.0)
    pull = (2.0 / max(0.05 * 20.0, 1.0e-5)) ** 2 * 1000.0
    assert EQ.SSQS_(iter([(110.0, 100.0, 4.0, None), (2.0, 20.0)])) == (((110.0 - 100.0) / sig) ** 2 * 1000.0 + pull) / ((0.10 * 100.0 / sig) ** 2 + 1.0)
    assert EQ.SSQS_([]) == 0.0


def test_the_nuts2_adding_up():
    assert NT.MSGROF_(iter([2.0, 3.0]), 6.0) == -1.0 and NT.MSLEVL_([1.0], 1.0) == 0.0
    assert NT.MSLANDUSE_([4.0, 5.0], 9.0) == 0.0 and NT.MSindmMaif_([], 2.0) == -2.0
    # the feed use in t, each side plus 10 kg a head
    r = NT.MSFEEDI_([(100.0, 50.0), (20.0, 30.0)], [100.0, 20.0, 5.0], 125.0, 44.0)
    assert r == (100.0 * 50.0 * 0.001 + 20.0 * 30.0 * 0.001) + (100.0 * 10.0 * 0.001 + 20.0 * 10.0 * 0.001
                                                                  + 5.0 * 10.0 * 0.001) - 125.0 * (44.0 + 10.0) * 0.001


def test_the_nuts2_fodder():
    assert NT.MSlosfFoddo_(3.0, 100.0, 5.0, 200.0) == 3.0 - 100.0 * 0.025
    assert NT.MSlosfFoddo_(3.0, 100.0, 5.0, 0.0) == 3.0          # no member-state GROF: rate zero
    assert NT.EFED_(100.0, 5.0, True, 7.0, False, [60.0, 35.0]) == 100.0 - 5.0 - 95.0


def test_the_bounds_of_fix_est():
    from capri_mod.pipeline.captrd.equations import fix_est as FE
    lo, up = FE.V_EstV_IO(100.0, 13, 53, "WHEA", True)
    assert lo == 100.0 * max(0.975 ** 13, 1 - 0.3 * 13 / 53) and up == 100.0 * min(1.025 ** 13, 1 + 0.3 * 13 / 53 + 10.0)
    assert FE.V_EstV_IO(100.0, 13, 53, "YCHI", False)[0] == 100.0 * max(0.975 ** 13, 1 - 0.3 * 13 / 53 - 1.0)
    assert FE.V_EstV_OYANI_expert(2.0, None) == (1.0, None)
    # food intake as GAMS reads it: BAST x 0.98^n + BASM (CAPRI-ERROR, kept)
    assert FE.V_EstV_INHA(10.0, 4.0, 12, 13) == (10.0 * 0.98 ** 12 + 4.0, 10.0 * 1.02 ** 12 + 4.0)
    assert FE.V_EstV_up_TWIN("ES000000", 100.0) == 117.355 and FE.V_EstV_up_TWIN("DK000000", 1.0) is None
    assert FE.V_EstV_up_physical(("TOBA", "TOBA"), 3000.0, 9000.0) == 4500.0
    assert FE.V_EstV_up_GRAS("GRAI", True, 1000.0, 1.0e9) == 160000.0
    # ARTIF: l. 810 as coded, the year as the exponent, or as its comment states it (FIX-7)
    assert FE.V_EstV_ARTIF(5.0, True, 1.0e9, 2030, 2017, False) == (5.0, max(5.0 * 1.02 ** 13, 1.0e9))
    assert FE.V_EstV_ARTIF(5.0, True, 6.0, 2030, 2017, True) == (5.0, max(5.0 * 1.02 ** 2030 - 2017, 6.0))


def test_the_bounds_of_milk_biofuels_and_the_member_state():
    from capri_mod.pipeline.captrd.equations import biofuel_bounds as BF
    from capri_mod.pipeline.captrd.equations import comi_bounds as CB
    from capri_mod.pipeline.captrd.equations import estimate_ms as EM
    assert CB.P_DATA_DCOW_COMI(6000.0, 1.0, 9000.0, 3.0, 5.0) == (6000.0 + 27000.0) / 4.0
    assert CB.P_DATA_DCOW_COMI(6000.0, 0.0, 9000.0, 0.0, 5.0) == 5.0
    assert CB.V_EstV_COMI(1.0, 1.0, 1.0, 7000.0, 7000.0, 0.0, 10, 0.0, 9.0) == (1.0125 ** 10, 9.0)
    assert CB.V_EstV_COMI_prev(5.0, 6.0, None, True, 5) == (5.0, 6.0)
    assert CB.V_EstV_COMI_prev(5.0, 5.5, 5.0, True, 4) == (5.0 * 1.0025 ** 4, 5.0 * 1.0025 ** 4 * 1.1)
    assert BF.V_EstV_SECO_BIOF("BIOF", 100.0) == (100.0 * 0.9999, 100.0 * 1.05)
    assert EM.V_EstV_lo_std("CSSP", "WHEA", 10.0, -3.0, 0.0, 0.0, 0.0, 0.0) == max(0.1, -3.0)
    assert EM.V_EstV_MPACT_LEVL(0.0, 1.0, 3) == (None, 1.0)
    assert EM.V_EstV_MPACT_LEVL(1e-9, 0.0, 3) == (1.0e-5 * 3, 1.0e-5 * 3 * 1.1)


def test_the_nuts2_bounds():
    from capri_mod.pipeline.captrd.equations import estimate_nuts2 as NB
    # the national change applied to the region's base: Step3(MS) / BASM(MS) x BASM(region)
    assert NB.V_EstV_up_LEVL(120.0, 100.0, 10.0, 13) == max(120.0 / 100.0 * 10.0 * 1.015 ** 13, 10.01)
    assert NB.V_EstV_lo_LEVL(120.0, 0.0, 10.0, 13) == 0.0          # no member-state base: the ratio is zero
    assert NB.V_EstV_MEAT_EGGS(2.0, 1.0, 3.0) == (6.0 * 0.999 - 0.1, 6.0 * 1.001 + 0.1)
    # production from the levels' and coefficients' bounds: GAMS's products (zero against an infinite bound)
    assert NB.V_EstV_GROF([(10.0, 20.0, 5.0, 6.0), (0.0, float("inf"), 0.0, 1.0)]) == (
        10.0 * 5.0 * 0.99 * 0.001, 20.0 * 6.0 * 1.01 * 0.001 + 1.0)
    assert NB.V_EstV_GROF_SUGB(10.0, 500.0, 100.0, 80.0, 5.0) == (min(47.5, 72.0), max(52.5, 88.0))
    assert NB.V_EstV_lo_ARTIF(2.0, 3.0, 4.0, 10.0, 1.0, 8.0) == (1.5, 0.99 * min(1.5, 1.0))


def test_the_nuts2_retries():
    from capri_mod.pipeline.captrd.equations import est_nuts2_grid as GR
    from capri_mod.pipeline.captrd.equations import est_nuts2_grid_openbound as OB
    assert OB.V_EstV_lo_coef(1.0, 5.0, False, True, False) == max(0.0, 1.0 - max(0.1, 0.05))
    assert OB.V_EstV_lo_coef(1.0, -5.0, False, False, False) == 1.0 - max(0.1, 0.25)
    assert OB.V_EstV_REQST(20.0, 0.05) == (10.0, 0.05)
    assert OB.V_EstV_lo_LEVL_open(1.0, True) == 0.9 and OB.V_EstV_lo_LEVL_open(5.0e-6, False) == 0.0
    assert GR.V_EstV_up_GROF_tries(100.0, 5) == 100.0 * 1.05 ** 5
    assert GR.V_EstV_SUGB_LEVL(50.0, 60.0, 55.0, 70000.0) == (50.0 / 70.0, 60.0 / 70.0, 55.0 / 70.0)
