"""CAPRI's gross account by item at a region's solution (income I2; capri_mod/income/eaa.py, reports/sol_simy.gms l.
685-687, 2549-2566, 2600-2615), by hand."""
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]


def _region():
    """A hand-built region at the base year: a crop with a yield change, the Green Deal's input changes and a technology
    mix column, a
    dairy herd and a bull herd fed in the regional model (the fodder at a different value per herd), the mitigation
    options' items; and I1's income of it (EUR 1000)."""
    m = SimpleNamespace(
        net_revenues=pd.Series({"SWHE": 540.0, "DCOW": 1995.0, "BULL": 1100.0}),
        revenues=pd.Series({"SWHE": 900.0, "DCOW": 3000.0, "BULL": 1500.0}),
        premiums=pd.Series({"SWHE": 200.0, "DCOW": 100.0, "BULL": 50.0}),
        output_items={"SWHE": [("SWHE", 6000.0, 150.0, 900.0)],
                      "DCOW": [("MILK", None, None, 2500.0), ("BEEF", None, None, 300.0), ("OTHER_O", None, None, 200.0)],
                      "BULL": [("BEEF", None, None, 1500.0)]},
        data=SimpleNamespace(variable_costs=pd.Series({"SWHE": 500.0}), sim_year=None, crop_inputs_2030=None,
                             input_coefs_2030=None,
                             livestock_input_cost=pd.DataFrame({"ELEC": [50.0, float("nan")], "FEED": [800.0, 400.0],
                                                                "INPO": [100.0, 50.0], "YOUNG": [150.0, float("nan")]},
                                                               index=["DCOW", "BULL"])),
        # the solve's changes of the margins by item (SupplyModule._nr_item): the crop's yield change at its price
        # (-200 kg at 150 EUR/t), its Green Deal plant-protection and other-input costs, the herd's other inputs
        ev=SimpleNamespace(nr_items={"SWHE": [("O", "SWHE", -30.0, -200.0, 150.0), ("I", "PLAP", 20.0, None, None),
                                              ("I", "INPO", 10.0, None, None)],
                                     "DCOW": [("I", "INPO", 5.0, None, None)]},
                           mix_parts={"SWHE": {"O": ("SWHE", 300.0, 150.0, 45.0),
                                               "I": {"INPO": 2.0, "PLAP": 3.0, "FERT": 4.0, "OTHER_I": 1.0},
                                               "PRME": 6.0}}))
    res = SimpleNamespace(activities=pd.Series({"SWHE": 100.0, "DCOW": 10.0, "BULL": 5.0}),
                          feed_t={"DCOW": {"FCER": 35000.0, "FGRA": 100000.0}, "BULL": {"FGRA": 20000.0}},
                          feed_price={"DCOW": {"FCER": 0.2, "FGRA": 0.02}, "BULL": {"FGRA": 0.03}},
                          feed_lin={"DCOW": 800.0, "BULL": 400.0}, technology_mix={"SWHE": 5.0})
    # I1 (income_parts): the crop's margin 900 - 30 - 500 - 20 - 10 + 200 = 540; the herds' margins with the solved ration (900 and 120 EUR per head)
    # in place of the feed they carry (800 and 400); the mix's net revenue 45 - 10 + 6 = 41 on 5 000 ha
    mgva_act = {"SWHE": 540.0, "DCOW": 1995.0 + 800.0 - 900.0, "BULL": 1100.0 + 400.0 - 120.0}
    ip = {"MGVA": 540.0 * 100 + mgva_act["DCOW"] * 10 + mgva_act["BULL"] * 5 + 41.0 * 5 - 30.0 + 10.0,
          "PRME": 200.0 * 100 + 100.0 * 10 + 50.0 * 5 + 6.0 * 5, "MGVA_act": mgva_act, "mitiI": 30.0, "mitiO": 10.0}
    return m, res, ip


def test_the_gross_account_by_item_of_a_region():
    """Each item's GROF and EAAG (EUR million): the crop's product in quantity (1000 t) at its price, with the mix
    column's output difference; the inputs' values; the feeds in quantity at their price where one price holds, in
    value where the fodder's value differs by herd; TOOU, TOIN, MGVA = TOOU - TOIN + PRME, equal to I1's AGGT."""
    from capri_mod.income.eaa import eaag_items
    m, res, ip = _region()
    e = eaag_items("FR810000", res, SimpleNamespace(_models={"FR810000": m}), ip=ip)
    it = e["items"].set_index(["side", "item"])
    assert it.loc[("O", "SWHE"), "GROF"] == pytest.approx(0.001 * ((6000.0 - 200.0) * 100 + 300.0 * 5))
    assert it.loc[("O", "SWHE"), "UVAG"] == 150.0
    assert it.loc[("O", "SWHE"), "EAAG"] == pytest.approx(((900.0 - 30.0) * 100 + 45.0 * 5) / 1000)
    want_o = {"MILK": 25.0, "BEEF": 3.0 + 7.5, "OTHER_O": 2.0, "mitiO": 0.01}
    for k, v in want_o.items():
        assert it.loc[("O", k), "EAAG"] == pytest.approx(v), k
    want_i = {"TOIN_lin": 50.0, "PLAP": 2.015, "INPO": 1.06 + 1.0 + 0.25, "ELEC": 0.5, "YOUNG": 1.5, "FCER": 7.0,
              "FGRA": 2.0 + 0.6, "FERT": 0.02, "OTHER_I": 0.005, "mitiI": 0.03}
    assert set(it.loc["I"].index) == set(want_i)          # the table's FEED left out for the herds fed in the model
    for k, v in want_i.items():
        assert it.loc[("I", k), "EAAG"] == pytest.approx(v), k
    assert it.loc[("I", "FCER"), "GROF"] == pytest.approx(35.0) and it.loc[("I", "FCER"), "UVAG"] == 200.0
    assert it.loc[("I", "FGRA"), "UVAG"] == 1000.0 and it.loc[("I", "FGRA"), "GROF"] == pytest.approx(2.6)
    assert e["TOOU"] == pytest.approx(87.225 + sum(want_o.values()))
    assert e["TOIN"] == pytest.approx(sum(want_i.values()))
    assert e["PRME"] == pytest.approx(21.28)
    assert e["MGVA"] == pytest.approx(e["TOOU"] - e["TOIN"] + e["PRME"])
    assert e["AGGT"] == pytest.approx(80.035)
    assert abs(e["DIFF"]) < 1e-12
    assert e["DIFF_act"] == pytest.approx({"SWHE": 0.0, "DCOW": 0.0, "BULL": 0.0}, abs=1e-12)
    # a change of the margin the items do not hold shows in DIFF, by activity
    ip["MGVA"] += 7.0 * 100
    ip["MGVA_act"]["SWHE"] += 7.0
    e = eaag_items("FR810000", res, SimpleNamespace(_models={"FR810000": m}), ip=ip)
    assert e["DIFF"] == pytest.approx(-0.7) and e["DIFF_act"]["SWHE"] == pytest.approx(-0.7)


def test_the_gross_account_at_the_years_coefficients(monkeypatch):
    """At the 2030 market year a crop's inputs are CAPRI's yield-dependent inputs item by item (crop_inputs_2030 x
    TF_I, in the model's money) and its NPK need per nutrient, whose sum is I1's TOIN at "Y" (DATA_TOIN_Y)."""
    from capri_mod.data.inputs import money_deflator
    from capri_mod.income import eaa
    from capri_mod.income.income_module import IncomeDistributionModule as I
    m, res, ip = _region()
    tf, d = 0.95, money_deflator(2030)
    items = {"SEED": 300.0, "EFUL": 200.0, "REPM": 70.0}
    npk = {"NITF": 100.0, "PHOF": 20.0, "POTF": 10.0}
    toin_y = sum(items.values()) * tf / d + sum(npk.values())
    monkeypatch.setattr(I, "crop_toin_y", staticmethod(lambda region, m_: {"SWHE": (500.0, toin_y)}))
    monkeypatch.setattr(eaa, "_crop_npk_parts", lambda region, m_, toin: {"SWHE": dict(npk)})
    m.data.sim_year = 2030
    m.data.crop_inputs_2030 = pd.DataFrame(items, index=["SWHE"])
    m._greendeal_tech_progress = lambda: tf
    ip["MGVA_act"]["SWHE"] = 540.0 - (toin_y - 500.0)
    ip["MGVA"] -= (toin_y - 500.0) * 100
    e = eaa.eaag_items("FR810000", res, SimpleNamespace(_models={"FR810000": m}), ip=ip)
    it = e["items"].set_index(["side", "item"])
    assert ("I", "TOIN_lin") not in it.index
    for k, v in items.items():
        assert it.loc[("I", k), "EAAG"] == pytest.approx(v * tf / d * 100 / 1000), k
    for k, v in npk.items():
        assert it.loc[("I", k), "EAAG"] == pytest.approx(v * 100 / 1000), k
    assert abs(e["DIFF"]) < 1e-12 and abs(e["DIFF_act"]["SWHE"]) < 1e-12


def test_the_account_statements():
    """GROF = 0.001 sum coefficient x level (l. 685-687); EAAG = GROF x UVAG / 1000 (l. 2549); TOOU and TOIN the sums
    (l. 2557-2558); MGVA = TOOU - TOIN + PRME (l. 2564-2566)."""
    from capri_mod.coupling.equations.sol_simy import (DATA_EAAG_IO, DATA_EAAG_MGVA, DATA_GEAAC_TOIN, DATA_GEAAC_TOOU,
                                                       DATA_GROF_IO)
    g = DATA_GROF_IO([6150.0, 5000.0], [100.0, 20.0])          # kg per ha x 1000 ha
    assert g == pytest.approx(715.0)                           # 1000 t
    assert DATA_EAAG_IO(g, 135.6) == pytest.approx(96.954)      # EUR million
    assert DATA_GEAAC_TOOU([1.0, 2.5]) == 3.5 and DATA_GEAAC_TOIN([]) == 0.0
    assert DATA_EAAG_MGVA(10.0, 4.0, 1.5) == 7.5


def test_the_crops_residue_nutrients_in_the_account():
    """K212: a crop's residues' nutrients (MANN, MANP, MANK; CAPRI's PACT_TO_O) are outputs in quantity at the member
    state's unit value, the technology mix column's T1 - T2 of them on the area moved; I1's MGVA holds the same
    (calc_inc_indic.py DATA_TOOU_FOUT), so the account still equals it."""
    from capri_mod.coupling.equations.calc_inc_indic import DATA_TOOU_FOUT
    from capri_mod.income.eaa import eaag_items
    m, res, ip = _region()
    fo = {"SWHE": {"MANN": (40.0, 500.0), "MANK": (100.0, 450.0)}}
    fom = {"SWHE": {"MANN": 2.0}}
    m.res = SimpleNamespace(last_fout=fo, last_fout_mix=fom)
    t_ha = DATA_TOOU_FOUT([40.0, 100.0], [500.0, 450.0])
    assert t_ha == pytest.approx(65.0)                                   # EUR per ha
    ip["MGVA_act"]["SWHE"] += t_ha
    ip["MGVA"] += t_ha * 100 + DATA_TOOU_FOUT([2.0], [500.0]) * 5
    e = eaag_items("FR810000", res, SimpleNamespace(_models={"FR810000": m}), ip=ip)
    it = e["items"].set_index(["side", "item"])
    assert it.loc[("O", "MANN"), "GROF"] == pytest.approx(0.001 * (40.0 * 100 + 2.0 * 5))     # 1000 t
    assert it.loc[("O", "MANN"), "UVAG"] == 500.0
    assert it.loc[("O", "MANK"), "EAAG"] == pytest.approx(100.0 * 100 * 450.0 / 1e6)
    assert abs(e["DIFF"]) < 1e-12 and abs(e["DIFF_act"]["SWHE"]) < 1e-12


def test_the_residues_unit_value_and_value():
    """CAPRI's unit value of the nutrients' outputs at 2030 is the member state's base year one x p_inflationFactor
    (capmod/inflation_and_trend_interpolation.gms l. 22-23, 67-72): in the model's 2017 money its base year value
    (npk_region_2030.csv fout_uvag_eur_t, sim_ini_21730's DATA(FR000000, "UVAG", MANN, "BAS") for FR24); with the
    crop's residues per ha it gives the crop's secondary revenue, checked against CAPRI's 2030 reference for FR24's
    soft wheat (dataOut UVAG MANN 631.55, MANP 1,353.57, MANK 570.25 EUR/t; SREV 105.05 EUR per ha; a check only)."""
    from capri_mod.coupling.equations.calc_inc_indic import DATA_TOOU_FOUT
    from capri_mod.coupling.equations.inflation_and_trend_interpolation import DATA_UVAG_IO_SIMY, p_inflationFactor
    from capri_mod.data.inputs import money_deflator
    f = p_inflationFactor(1.019, 2030, 2017)
    assert f == pytest.approx(money_deflator(2030), rel=1e-9)
    q = pd.read_csv(ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "environment" /
                    "npk_region_2030.csv").set_index(["capri_region", "nutrient"])
    assert q["fout_uvag_eur_t"].notna().all()
    uv = {n: float(q.at[("FR240000", n), "fout_uvag_eur_t"]) for n in ("N", "P", "K")}
    assert uv["N"] == pytest.approx(494.476435, rel=1e-8)
    capri_2030 = {"N": 631.553275403158, "P": 1353.57092743057, "K": 570.246417311741}
    for n, v in capri_2030.items():
        assert DATA_UVAG_IO_SIMY(uv[n], f) == pytest.approx(v, rel=1e-9), n
    c = pd.read_csv(ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "environment" /
                    "npk_crop_coefs_2030.csv").set_index(["capri_region", "model_crop", "nutrient"])
    kg = [float(c.at[("FR240000", "SWHE", n), "pool_kg_ha"]) for n in ("N", "P", "K")]
    assert DATA_TOOU_FOUT(kg, [capri_2030[n] for n in ("N", "P", "K")]) == pytest.approx(105.047816567923, rel=1e-6)
