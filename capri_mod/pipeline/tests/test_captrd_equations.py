"""CAPTRD's estimation equations as named functions (capri_mod/pipeline/captrd/equations/equations.py): each on its
GAMS statement (captrd/equations.gms). The residuals of estimate_ms.residuals are unchanged by construction (the same
operations in the same order; checked at CAPTRD's Step 2 points of every country and year when the move was made)."""
import casadi as ca

from capri_mod.pipeline.captrd.equations import equations as EQ


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
