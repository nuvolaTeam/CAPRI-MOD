"""Register DEP-13 step 2: CAPRI's 2030 outputs per model head at the 2030 market year (tools/build/
build_livestock_output_2030.py; capri_mod/projection/projection_module.py ProjectionModule.SUPBAL_outputsPerHead_Y)."""
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
T30 = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "supply" / "livestock_output_by_product_coef_2030.csv"
T17 = ROOT / "capri_data" / "2017" / "supply" / "livestock_output_by_product_coef.csv"


def _young():
    spec = importlib.util.spec_from_file_location("bya", ROOT / "tools" / "build" / "build_young_animals_2030.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_the_2030_table_covers_every_animal_with_a_2030_herd():
    """The same products as the 2017 table; every cell with a base-year output and a 2030 herd has a 2030 coefficient
    (the four without one, FI20 and NO07 broilers and AT32 hens, have no 2030 heads)."""
    a = pd.read_csv(T30, index_col=0, float_precision="round_trip")
    b = pd.read_csv(T17, index_col=0, float_precision="round_trip")
    assert sorted(a.columns) == sorted(b.columns) and set(a.index) == set(b.index)
    h = _young().herds_2030()
    for c in b.columns:
        an = c.split(".")[0]
        miss = [r for r in b.index if b.at[r, c] > 0 and not a.at[r, c] > 0]
        assert all(float(h.at[r, an]) == 0.0 for r in miss), (c, miss)
    # dairy cows' milk per cow 2030 over 2017: CAPRI's yield growth (the median 1.13)
    q = (a["DCOW.COMI"] / b["DCOW.COMI"]).median()
    assert 1.05 < q < 1.2


def test_the_outputs_per_head_take_capris_2030_and_the_values_follow():
    """SUPBAL_outputsPerHead_Y: each product's quantity per head becomes CAPRI's 2030, its value per head moves in
    proportion, the animal's totals by the change (the young animals' part of revenue and output value kept); a cell
    without CAPRI's 2030 output keeps the projected one."""
    from capri_mod.projection.projection_module import ProjectionModule
    bp = pd.DataFrame({"DCOW.COMI": [7.0, 6.0], "DCOW.BEEF": [0.10, 0.08]}, index=["R1", "R2"])
    pv = pd.DataFrame({"DCOW.MILK": [2800.0, 2400.0], "DCOW.BEEF": [300.0, 240.0]}, index=["R1", "R2"])
    t = pd.DataFrame({"DCOW.COMI": [7.0, float("nan")], "DCOW.BEEF": [0.11, 0.06]}, index=["R1", "R2"])
    oc = pd.DataFrame({"DCOW": [7.10, 6.08]}, index=["R1", "R2"])
    pvc = pd.DataFrame({"DCOW": [3100.0, 2640.0]}, index=["R1", "R2"])
    rev = pd.DataFrame({"DCOW": [2900.0, 2500.0]}, index=["R1", "R2"])
    ov = pd.DataFrame({"DCOW": [3500.0, 3000.0]}, index=["R1", "R2"])
    data = {"livestock_output_by_product_coef_2030": t, "livestock_output_coef": oc,
            "livestock_product_value_coef": pvc, "livestock_revenue_coef": rev, "livestock_output_value_coef": ov}
    ProjectionModule.SUPBAL_outputsPerHead_Y(data, 2030, bp, pv)
    assert bp.at["R1", "DCOW.BEEF"] == pytest.approx(0.11) and bp.at["R2", "DCOW.COMI"] == pytest.approx(6.0)
    assert pv.at["R1", "DCOW.BEEF"] == pytest.approx(330.0) and pv.at["R2", "DCOW.BEEF"] == pytest.approx(180.0)
    assert pv.at["R1", "DCOW.MILK"] == pytest.approx(2800.0)
    assert oc.at["R1", "DCOW"] == pytest.approx(7.11) and oc.at["R2", "DCOW"] == pytest.approx(6.06)
    for tab, v0 in ((pvc, 3100.0), (rev, 2900.0), (ov, 3500.0)):
        assert tab.at["R1", "DCOW"] == pytest.approx(v0 + 30.0)
    assert rev.at["R2", "DCOW"] == pytest.approx(2500.0 - 60.0)
    # another year without its table: nothing changes
    ProjectionModule.SUPBAL_outputsPerHead_Y(data, 2025, bp, pv)
    assert bp.at["R1", "DCOW.BEEF"] == pytest.approx(0.11)


def test_the_projection_to_capris_2030_reference_takes_its_outputs_per_head():
    """project_data with CAPRI's 2030 reference as the trajectory: every positive cell of the 2030 table is the
    projected coefficient, and each animal's output is the sum of its products (a trend projection, captrd_2030,
    keeps the outputs per head following its own yields: test_capri.test_projection_livestock_output_follows_yield)."""
    from capri_mod.data.inputs import trajectories_dir
    from capri_mod.model import CAPRIModel
    from capri_mod.projection import BaselineTrajectory, ProjectionModule
    m = CAPRIModel(data_dir=str(ROOT / "capri_data"), verbose=False)
    pm = ProjectionModule(m, BaselineTrajectory.from_file(str(ROOT / "capri_data" / "scenarios" / "capri_ref_2030")),
                          capri_prices_dir=str(trajectories_dir(str(ROOT / "capri_data"), 2030)))
    data, _ = pm.project_data(2030)
    bp, t = data["livestock_output_by_product_coef"], pd.read_csv(T30, index_col=0, float_precision="round_trip")
    n = 0
    for c in t.columns:
        for r in t.index[t[c] > 0].intersection(bp.index):          # the model's supply regions
            assert bp.at[r, c] == pytest.approx(float(t.at[r, c]), rel=1e-12), (r, c)
            n += 1
    assert n > 2000
    tot = data["livestock_output_coef"]
    for a in tot.columns:
        parts = [c for c in bp.columns if c.startswith(a + ".")]
        if parts:
            assert (bp[parts].sum(axis=1) - tot[a]).abs().max() < 1e-9, a
