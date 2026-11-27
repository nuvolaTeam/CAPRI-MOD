"""The Green Deal's input changes and the yields' input update on CAPRI's simulation-year coefficients (register DEP-21;
capmod/define_inputs.gms, capri_mod/supply/equations/define_inputs.py; tools/build/build_input_coefs_2030.py)."""
from pathlib import Path

import pandas as pd
import pytest

from capri_mod.supply.equations.define_inputs import DATA_IY_Y, TF_I, p_yieldGrowth

ROOT = Path(__file__).resolve().parents[2]
SUP30 = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "supply"


def test_define_inputs_statements():
    """TF_I (l. 66, 70-73), p_yieldGrowth (l. 80-82, 96-97, 101-102), DATA(IY, Y) (l. 107-112)."""
    tf = 1.0 - 0.005 * 13
    assert TF_I(tf) == tf and TF_I(tf, 0.0, False) == tf
    assert TF_I(tf, -0.5) == pytest.approx(0.5 * tf)                    # scenAugmentsTechChange on (FIX-5's fix)
    assert TF_I(tf, -0.5, False) == pytest.approx(0.5)                  # CAPRI's code: the change replaces TF_I
    assert p_yieldGrowth([7.0], [6.0], 10.0) == pytest.approx(7.0 / 6.0)
    assert p_yieldGrowth([7.0, 3.0], [0.0, 2.0], 10.0) == pytest.approx(1.5)   # outputs without a base yield left out
    assert p_yieldGrowth([12.0], [6.0], 10.0) == 1.5 and p_yieldGrowth([12.0], [6.0], 10.0, bounded=False) == 2.0
    assert p_yieldGrowth([0.0], [6.0], 10.0) == 1.0                     # no yield coefficient: no change
    assert p_yieldGrowth([7.0], [6.0], 0.0) == 0.0                      # no base level: not assigned
    assert DATA_IY_Y(100.0, 0.5, 1.2, tf) == pytest.approx(100.0 * (0.5 + 0.5 * 1.2) * tf)
    assert DATA_IY_Y(0.0, 0.5, 1.2, tf) is None


def test_the_2030_coefficients_reproduce_capris_reference():
    """The table's plant-protection coefficient x TF_I at the member state's UVAP is CAPRI's 2030 reference coefficient
    at it (plant_protection_capri_step_2030.csv: dataOut PLAP at 2030 x UVAP(2030) / 1000), within the listing's
    printed precision, in every EU row the two share with a base coefficient. Grassland has none in sim_ini_21730
    (GRAE, GRAI: no DATA(PLAP) at BAS or Y), so define_inputs.gms leaves it and the Green Deal's change does not reach
    it; dataOut reports a PLAP for it (from elsewhere, not traced), which the table does not take."""
    t = pd.read_csv(SUP30 / "input_coefs_2030.csv")
    s = pd.read_csv(SUP30 / "plant_protection_capri_step_2030.csv")
    m = t.merge(s, on=["region", "activity"])
    m = m[m.plap_uvap_eur_ha > 0]
    assert set(m[m.plap_eur_ha == 0].activity) == {"GRAE", "GRAI"}
    m = m[m.plap_eur_ha > 0]
    assert len(m) > 5500
    r = m.plap_eur_ha * (1.0 - 0.005 * 13) / m.plap_uvap_eur_ha
    assert (r - 1.0).abs().max() < 1e-5
    an = t[t.inpo_yield_factor.notna()]
    assert set(an.activity) >= {"DCOW", "BCOW", "PIGF", "PIGS", "LAYS", "BROI"}
    de = an[(an.region == "DE210000")].set_index("activity").inpo_yield_factor
    assert de["DCOW"] > 1.0 and de["BCOW"] == pytest.approx(1.0, abs=0.02)   # milk yield grows, the suckler cow's hardly


def test_the_crops_inputs_item_by_item_add_up_to_the_yield_dependent_part():
    """crop_inputs_2030.csv holds iy_uvag_eur_ha's terms, CAPRI's directly yield-dependent inputs of a crop at 2030 item
    by item (income I2): they add up to the column in every crop row, and the items are CAPRI's IY of the crops."""
    t = pd.read_csv(SUP30 / "input_coefs_2030.csv")
    it = pd.read_csv(SUP30 / "crop_inputs_2030.csv")
    # CAPRI's IY of the crops (sets.gms IY without water and mitigation; the builder's IY_CROP)
    assert set(it.item) <= {"CAOF", "SEED", "PLAP", "REPM", "REPB", "ELEC", "EGAS", "EFUL", "ELUB", "IRRO", "INPO", "SERI"}
    assert {"PLAP", "SEED", "INPO"} <= set(it.item)
    s = it.groupby(["region", "activity"]).eur_ha.sum()
    c = t[t.iy_uvag_eur_ha.notna()].set_index(["region", "activity"]).iy_uvag_eur_ha
    c = c[c > 0]
    assert set(s.index) == set(c.index)
    assert ((s.reindex(c.index) - c).abs() <= 1e-9 * c.abs().clip(lower=1.0)).all()


def test_the_green_deal_input_changes_act_on_the_2030_coefficients():
    """At the 2030 market year the Green Deal's PLAP and INPO changes and the organic top-up act on CAPRI's
    simulation-year coefficients (input_coefs_2030.csv, deflated), an animal's INPO cost per head carries its INPO's
    yield factor; outside it the 2017 rows (test_capri.py::test_greendeal_input_changes_follow_capri)."""
    from capri_mod.data.inputs import money_deflator
    from capri_mod.data.loaders import load_all_data
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities

    d = load_all_data("capri_data")
    region = "FR810000"
    sm = SupplyModule(d, calibrate_supply_elasticities(d["areas"]))
    sm.run(price_signals=None, regions=[region])
    mo = sm._models[region]
    mo.data.sim_year = 2030
    t = pd.read_csv(SUP30 / "input_coefs_2030.csv")
    mo.data.input_coefs_2030 = t[t.region == region].set_index("activity").drop(columns=["region", "levl_capri"])
    defl = money_deflator(2030)
    tf = 1.0 - 0.005 * 13
    crop, ani = "SWHE", "DCOW"
    row = mo.data.input_coefs_2030.loc[crop]
    plap, inpo, eful = row.plap_eur_ha / defl, row.inpo_eur_ha / defl, row.eful_eur_ha / defl
    assert mo._sim_input_cost(crop, "plap_eur_ha") == pytest.approx(plap)
    assert plap != pytest.approx(mo._input_row(crop, "plap_eur_ha"), rel=1e-3)
    # the animal's INPO per head in CAPRI's objective form at 2030 (register DEP-13 step 3), as the projection sets it
    # (projection_module.p_linObjeCont_animals_Y): CAPRI's 2030 coefficient x TF_I / the deflator
    c30 = pd.read_csv(SUP30 / "livestock_input_cost_2030.csv")
    x30 = float(c30[(c30.region == region) & (c30.animal == ani) & (c30["item"] == "INPO")].eur_head.iloc[0])
    inpo30 = x30 * tf / defl
    assert inpo30 != pytest.approx(float(mo.data.livestock_input_cost.at[ani, "INPO"]), rel=1e-3)
    mo.data.livestock_input_cost.at[ani, "INPO"] = inpo30
    nr0 = mo.net_revenues.copy()
    o_R, o_a = mo._organic_region_target(0.25), mo._organic_crop_target(crop, 0.25)
    mo._apply_greendeal_input_changes(0.25, 0.50)
    topup = 2 * o_a * eful
    d_plap = plap * (1 - 0.5) * tf - plap * tf
    d_inpo = (inpo + topup) * (1 + 0.5 - o_R) * tf - inpo * tf
    assert (nr0[crop] - mo.net_revenues[crop]) == pytest.approx(d_plap + d_inpo, abs=1e-6)
    assert (nr0[ani] - mo.net_revenues[ani]) == pytest.approx(inpo30 * (0.5 - o_R), abs=1e-6)
    # the former form (supply.animal_cost_form "toin"): TOIN's INPO share with its INPO's 2030 yield factor
    from capri_mod import settings as S
    yf = float(mo.data.input_coefs_2030.at[ani, "inpo_yield_factor"])
    sh = mo._input_row(ani, "inpo_toin_share") * mo._animal_cost_per_head(ani) * yf
    with S.override({"supply.animal_cost_form": "toin"}):
        mo.net_revenues = nr0.copy()
        mo._apply_greendeal_input_changes(0.25, 0.50)
        assert (nr0[ani] - mo.net_revenues[ani]) == pytest.approx(sh * (0.5 - o_R) * tf, abs=1e-6)
    # the yields' input update takes the 2030 coefficients' derivative (yd_* at the member state's UVAP)
    mo.net_revenues = nr0.copy()
    y0 = mo.data.yields.copy()
    mo.ev.yields_solve0, mo.ev.greendeal_inputs = y0, {}
    y1 = y0.copy(); y1[crop] = y0[crop] * 0.9
    mo.data.yields = y1
    mo._apply_yield_input_costs()
    k = sum(float(row[c]) for c in ("yd_rest_eur_ha", "yd_plap_eur_ha", "yd_inpo_eur_ha")) / defl * tf
    assert (nr0[crop] - mo.net_revenues[crop]) == pytest.approx(k * (-0.1), abs=1e-6)
    mo.data.yields, mo.ev.yields_solve0 = y0, None
