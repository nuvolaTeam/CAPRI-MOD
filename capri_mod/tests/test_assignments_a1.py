"""The statements of the emission and nutrient accounts and of the projection's livestock rules moved in block A1+A3
(docs/dev/ASSIGNMENTS_REFACTOR_PLAN.md): each function on CAPRI's numbers and on the form its caller used before the
move (the same operations in the same order, so the same floating-point result)."""
import math

from capri_mod.environmental.equations.calc_nbalance import DATA_IMPORT, DATA_RUNANI, DATA_SURSOI, DATA_SURTOT
from capri_mod.environmental.equations.gases import EMISCALC_CO2UREA
from capri_mod.market.equations.welfare import p_welfareRes_ProfitAgr
from capri_mod.projection.equations.breeding import p_animReqCopy_ENNE_nonlact, p_animReqCopy_NEA_share
from capri_mod.projection.equations.calc_nexport import CRPR_EXPT_COMI
from capri_mod.supply.equations.fertned import p_technFact_FNUT
from capri_mod.supply.equations.line_nitr import p_ghgMiti_AComLN
from capri_mod.supply.equations.set_supply_bounds import v_emiLoss_bounds


def test_co2_urea_with_the_substitution_is_capris_product():
    # CAPRI: NMIN x max(urea share - v, 0) x 44/28; the base value NMIN x share x 44/28 times the factor
    nmin, f, v = 120.0, 0.3, 0.1
    base = nmin * f * 44 / 28
    assert math.isclose(EMISCALC_CO2UREA(base, f, v), nmin * max(f - v, 0.0) * 44 / 28, rel_tol=1e-14)
    assert EMISCALC_CO2UREA(base, f, 0.5) == 0.0
    assert EMISCALC_CO2UREA(base, f, v) == base * max(f - v, 0.0) / f


def test_the_nea_share_and_the_energy_apart_from_lactation():
    # no CAPRI row: HD = Et = 0, NEA = 0.17 NEM; NEM + NEP + NEA = NEM (1.1 + share)
    assert p_animReqCopy_NEA_share(0.0, 0.0) == 0.17 * 365.0 * 1.0 / 365.0
    s = p_animReqCopy_NEA_share(180.0, 40.0)
    assert math.isclose(s, 0.17 * (365 - 180) * (1 - 0.4) / 365, rel_tol=1e-14)
    nem = 600.0 ** 0.75 * 0.386 * 365.0
    assert math.isclose(p_animReqCopy_ENNE_nonlact(nem, s), nem + 0.10 * nem + nem * s, rel_tol=1e-14)
    assert p_animReqCopy_ENNE_nonlact(nem, s) == nem * (1.1 + s)


def test_milk_n_export_is_capris_0_0054_per_kg():
    assert CRPR_EXPT_COMI(1000.0) == 0.0054 * 1000.0


def test_the_p_balance_sums():
    ex, mt, mi, cr, ep, ru = 100.0, 12.5, 40.0, 7.25, 90.0, 1.5
    imp = DATA_IMPORT(ex, mt, mi, cr)
    assert imp == ex - mt + mi + cr
    assert DATA_SURTOT(imp, ep) == imp - ep
    assert DATA_SURSOI(DATA_SURTOT(imp, ep), ru) == imp - ep - ru
    assert DATA_RUNANI(3.0, 25.0, 0.04) == 3.0 * 25.0 * 0.04


def test_loss_shares_are_held_within_zero_and_one():
    assert v_emiLoss_bounds(-0.2) == 0.0 and v_emiLoss_bounds(1.3) == 1.0 and v_emiLoss_bounds(0.25) == 0.25


def test_the_variants_factor_and_the_linseed_nitrate_overlap():
    assert p_technFact_FNUT(None) == 1.0 and p_technFact_FNUT(0.12) == 1.12
    rL, rN, sL, sN = -0.1, -0.15, 0.4, 0.25
    assert p_ghgMiti_AComLN(rL, rN, sL, sN) == rL * rN * min(sL, sN)


def test_profit_agr_is_the_sum_of_net_revenues_times_levels():
    mgva, lev = [500.0, 1200.0, 300.0], [10.0, 2.5, 0.0]
    assert p_welfareRes_ProfitAgr(mgva, lev) == float(sum(m * x for m, x in zip(mgva, lev)))
