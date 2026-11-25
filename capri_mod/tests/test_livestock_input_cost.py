"""The animals' input costs in CAPRI's objective form (register DEP-13 step 3): p_linObjeCont (capmod/define_objc.gms
l. 39-44) and IobjCont (sets.gms l. 5059-5067) by hand, the 2017 table's parts adding up to the model's TOIN per head,
and the year's inputs in the projected cost (projection_module.p_linObjeCont_animals_Y)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
SUP = ROOT / "capri_data" / "2017" / "supply"


def test_p_linObjeCont_by_hand():
    """Two inputs, one with a technology factor: -0.001 x (10 x 1.2 x 1400 + 5 x 1 x 1000)."""
    from capri_mod.supply.equations.define_objc import p_linObjeCont
    v = p_linObjeCont({"INPO": 10.0, "IPHA": 5.0}, {"INPO": 0.2}, {"INPO": 1400.0, "IPHA": 1000.0})
    assert v == pytest.approx(-0.001 * (10 * 1.2 * 1400 + 5 * 1000), rel=1e-15)


def test_IobjCont_from_capris_sets():
    """IY: every input but IS's, the chicks, water and the mitigation input; IS from sets.gms's text."""
    from capri_mod.supply.equations.define_objc import IS_members, IobjCont
    text = """
    SET IS(I) Inputs intrasectorally produced /
*
        NITF,  PHOF , POTF,
*       Feedingsstuff + young animals
        FCER , FGRA,
        ICOW , ILAM /;
"""
    IS = IS_members(text)
    assert IS == ("NITF", "PHOF", "POTF", "FCER", "FGRA", "ICOW", "ILAM")
    iy = IobjCont(("NITF", "FCER", "ICOW", "ICHI", "WIRR", "WATR", "INPO", "IPHA", "mitiI"), IS, ("WIRR",))
    assert iy == ("WATR", "INPO", "IPHA")


def test_the_2017_parts_add_up_to_the_model_toin():
    """Per model region and animal, the inputs of IobjCont + YOUNG + FEED equal the model's TOIN per head
    (livestock_cost_coef.csv, the same per-head basis), within the UVAP-UVAG difference of the inputs (1e-4)."""
    from capri_mod.tableio import read_input
    t = read_input(SUP / "livestock_input_cost.csv")
    toin = read_input(SUP / "livestock_cost_coef.csv", index_col=0)
    s = t.groupby(["region", "animal"]).eur_head.sum()
    n, worst = 0, 0.0
    for (r, a), v in s.items():
        if r in toin.index and a in toin.columns and pd.notna(toin.at[r, a]) and float(toin.at[r, a]) > 1.0:
            worst = max(worst, abs(v / float(toin.at[r, a]) - 1.0))
            n += 1
    assert n > 2000 and worst < 1e-4, (n, worst)


def test_the_years_inputs_replace_2017s():
    """cost += sum_I (x_I,Y x TF_I / deflator - x_I,2017): one region, one animal, two inputs (the deflator and TF_I
    taken from the run's inputs and settings)."""
    from capri_mod.projection.projection_module import ProjectionModule
    from capri_mod.supply import inputs as _inputs
    from capri_mod.supply.equations.define_inputs import TF_I_trend
    from capri_mod.params import param
    c17 = {"R1": pd.DataFrame({"INPO": [30.0], "IPHA": [70.0], "YOUNG": [300.0], "FEED": [900.0]}, index=["DCOW"])}
    c30 = {"R1": pd.DataFrame({"INPO": [40.0], "IPHA": [90.0]}, index=["DCOW"])}
    toin = pd.DataFrame({"DCOW": [1300.0]}, index=["R1"])
    data = {"livestock_input_cost": c17, "livestock_input_cost_2030": c30, "livestock_cost_coef": toin}
    ProjectionModule.p_linObjeCont_animals_Y(data, 2030)
    tf = TF_I_trend(param("INPUT_SAVING_PROGRESS"), 2030, int(_inputs.base_year()))
    defl = _inputs.money_deflator(2030)
    assert toin.at["R1", "DCOW"] == pytest.approx(1300.0 + (40.0 + 90.0) * tf / defl - 100.0, rel=1e-14)
    assert c17["R1"].at["DCOW", "INPO"] == pytest.approx(40.0 * tf / defl, rel=1e-14)
    assert c17["R1"].at["DCOW", "FEED"] == 900.0
