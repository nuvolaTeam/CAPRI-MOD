"""CAPRI's rule for how a crop's nutrient data per ha follow its yield: fert/fertned.gms rerun at the yields
(capri_mod.fert.npk need_yield_factor and fout_yield_change; capri_mod/supply/equations/fertned.py fertned_at_yields;
KNOWN_ISSUES K189)."""
import pandas as pd
import pytest

from capri_mod.fert import npk
from capri_mod.supply.equations import fertned as FN

ENV = npk.__file__.rsplit("/capri_mod/", 1)[0] + "/capri_data/baselines/capri_greendeal_ref/1730/environment/"


@pytest.fixture(scope="module")
def data():
    return npk.NPKData.get()


def _parts(r, crop, nut):
    t = pd.read_csv(ENV + "capri_crop_fertned_parts_2030.csv", float_precision="round_trip")
    row = t[(t.capri_region == r) & (t.crop == crop) & (t.nutrient == nut)].iloc[0]
    return tuple(float(row[k]) for k in FN.FERTNED_PARTS)


def test_the_parts_rebuild_capris_simulation_data():
    """fertned's statements on the stored arguments give CAPRI's simulation DATA(crop, NITF) and DATA(crop, MANN) of
    the K191 rebuild (DE21 soft wheat and intensive grassland)."""
    n = pd.read_csv(ENV + "capri_crop_n_coefs_2030.csv", float_precision="round_trip").set_index(["capri_region", "crop"])
    dep = pd.read_csv(npk.__file__.rsplit("/capri_mod/", 1)[0] + "/capri_data/2017/environment/n_deposition_regional.csv"
                      ).set_index("region").deposition_kg_n_per_ha
    for crop in ("SWHE", "GRAI", "RAPE"):
        a, b = FN.fertned_at_yields(*_parts("DE210000", crop, "NITF"), 1.0, 1.0, AtmDep=float(dep["DE210000"]))
        assert a == pytest.approx(float(n.at[("DE210000", crop), "data_nitf"]), rel=1e-9)
        assert b == pytest.approx(float(n.at[("DE210000", crop), "data_mann"]), rel=1e-9)


def test_scenario_shift_moves_main_output_and_straw(data):
    """A scenario yield shift (capmod/shift_yields.gms) scales the main output and straw alike: a cereal's need between
    fertned's bounds moves one to one with the yield."""
    o_hp, stra, nm, ns, mx, dbl, *_ = _parts("FR250000", "SWHE", "NITF")
    n0 = o_hp * 0.001 * nm + stra * 0.001 * ns
    assert 15.0 < 0.9 * n0 and n0 < mx
    assert npk.need_yield_factor("FR250000", "SWHE", 7.0, 6.3) == pytest.approx(0.9)


def test_price_driven_yield_moves_the_main_part_only(data):
    """endog_yields.gms updates the main output only: the straw's part stays at the scenario's yield."""
    o_hp, stra, nm, ns, *_ = _parts("FR250000", "SWHE", "POTF")
    a, s = o_hp * 0.001 * nm, stra * 0.001 * ns
    assert a > 0 and s > 0
    f = npk.need_yield_factor("FR250000", "SWHE", 7.0, 7.35, y_scen=7.0, nut="K")
    assert f == pytest.approx((a * 1.05 + s) / (a + s))
    f2 = npk.need_yield_factor("FR250000", "SWHE", 7.0, 6.3 * 1.05, y_scen=6.3, nut="K")
    assert f2 == pytest.approx((a * 0.9 * 1.05 + s * 0.9) / (a + s))


def test_a_crop_at_the_floor_stays_until_the_yield_takes_it_across(data):
    """fertned.gms's MAX(15, ...): a crop whose need is at the floor does not move with a small yield change, and moves
    once the yield takes the need above 15 kg per ha (the earlier linear shares fixed it at the base)."""
    t = pd.read_csv(ENV + "capri_crop_fertned_parts_2030.csv", float_precision="round_trip")
    t = t[(t.nutrient == "NITF") & (t.o_hp > 0)]
    v = t.o_hp * 0.001 * t.need_main + t.stra * 0.001 * t.need_stra
    row = t[(v > 5.0) & (v < 13.0) & (t.stra == 0)].iloc[0]
    v0 = float(row.o_hp * 0.001 * row.need_main)
    assert v0 * 1.1 < 15.0 and npk.need_yield_factor(row.capri_region, row.crop, 1.0, 1.1) == pytest.approx(1.0)
    k = 20.0 / v0                                           # the yield that takes the need to 20 kg per ha
    assert npk.need_yield_factor(row.capri_region, row.crop, 1.0, k) == pytest.approx(20.0 / 15.0)


def test_residues_follow_the_new_need(data):
    """MANN = min(deposition + DATA(NITF) x residue share, 0.95 DATA(NITF)) + straw left (fertned.gms l. 242-286): the
    change from the base, DE21 rapeseed (no straw) by the residue share of the need's change."""
    p = _parts("DE210000", "RAPE", "NITF")
    o_hp, stra, nm, ns, mx, dbl, rr, rp, *_ = p
    assert rp == 1 and stra == 0
    n0 = FN.fertned_at_yields(*p, 1.0, 1.0, AtmDep=12.0)[0]
    d = npk.fout_yield_change("DE210000", "RAPE", 3.0, 3.3, None, "N", AtmDep=12.0)
    assert d == pytest.approx(0.1 * n0 * rr)


def test_model_region_and_no_data(data):
    cr = data.capri_region("FR720000")
    assert cr is not None
    assert npk.need_yield_factor("FR720000", "SWHE", 7.0, 6.3) == pytest.approx(
        npk.need_yield_factor(cr, "SWHE", 7.0, 6.3))
    # no CAPRI region: the rule of a crop without straw between the bounds (linear)
    assert npk.need_yield_factor(None, "SWHE", 7.0, 6.3) == pytest.approx(0.9)
    assert npk.need_yield_factor("FR720000", "SWHE", 0.0, 6.3) == 1.0
    # fallow has no main output: no fertned arguments, no change of its deliveries
    assert npk.fout_yield_change("FR720000", "FALL", 1.0, 1.1) is None
