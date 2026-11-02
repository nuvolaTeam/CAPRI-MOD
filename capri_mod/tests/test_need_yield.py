"""CAPRI's rule for how a crop's nutrient need per ha follows its yield (fert/fertned.gms; capri_mod.fert.npk)."""
import pandas as pd
import pytest

from capri_mod.fert import npk


@pytest.fixture(scope="module")
def data():
    D = npk.NPKData.get()
    if not D.has_yield_shares:
        pytest.skip("npk_crop_coefs_2030.csv without main_share/straw_share")
    return D


def test_shares_are_parts_of_the_need(data):
    for (r, nut), d in data.crop.items():
        assert (d.main_share >= -1e-9).all() and (d.straw_share >= -1e-9).all(), (r, nut)
        assert (d.main_share + d.straw_share <= 1.0 + 1e-6).all(), (r, nut)


def test_scenario_shift_moves_the_whole_need_of_a_cereal(data, monkeypatch):
    m, s = data.yield_shares("FR250000", "N", "SWHE")
    assert 0.5 < m < 1.0 and 0.0 < s < 0.5 and m + s == pytest.approx(1.0)
    # a scenario yield shift (shift_yields.gms) scales main output and straw alike: need moves one to one
    assert npk.need_yield_factor("FR250000", "SWHE", 7.0, 6.3) == pytest.approx(0.9)


def test_price_driven_yield_moves_the_main_part_only(data, monkeypatch):
    m, s = data.yield_shares("FR250000", "K", "SWHE")
    f = npk.need_yield_factor("FR250000", "SWHE", 7.0, 7.35, y_scen=7.0, nut="K")
    assert f == pytest.approx(1.0 + m * 0.05)
    # both: scenario shift x price response; straw only with the shift
    f2 = npk.need_yield_factor("FR250000", "SWHE", 7.0, 6.3 * 1.05, y_scen=6.3, nut="K")
    assert f2 == pytest.approx(m * 0.9 * 1.05 + s * 0.9 + (1.0 - m - s))


def test_model_region_and_no_data(data, monkeypatch):
    cr = data.capri_region("FR720000")
    assert cr is not None
    assert npk.need_yield_factor("FR720000", "SWHE", 7.0, 6.3) == pytest.approx(
        npk.need_yield_factor(cr, "SWHE", 7.0, 6.3))
    # no CAPRI region: the rule of a crop without straw (linear)
    assert npk.need_yield_factor(None, "SWHE", 7.0, 6.3) == pytest.approx(0.9)
    assert npk.need_yield_factor("FR720000", "SWHE", 0.0, 6.3) == 1.0


def test_builder_reads_capri_constants():
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "tools" / "build"))
    import build_npk_balance_2030 as B
    assert B.straw_content() == {"NITF": 5.0, "PHOF": 3.0, "POTF": 18.0}
    lo, mx, dbl = B.need_bounds()
    assert lo == 15.0 and mx == {"NITF": 400.0, "PHOF": 320.0, "POTF": 280.0}
    assert dbl == {"GRAE", "GRAI", "OFAR", "MAIF"}
