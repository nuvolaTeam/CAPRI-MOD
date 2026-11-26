"""A member state's accounts at producer prices (income I2c; capri_mod/income/eaa_ms.py, reports/sol_simy.gms l. 315,
789-799, 866, 874, 1889-1898, 1964-1970, 2389-2390, 2547-2562), by hand."""
from types import SimpleNamespace

import pandas as pd
import pytest


def test_the_member_state_statements():
    """NETF = GROF - SEDF - LOSF - INTF (l. 1970); SEDF and LOSF of a final product in proportion to production at "CUR"
    (l. 1889-1898); the young animals bought all internal and their output's internal use the same heads (l. 789-799);
    the fertilisers' purchases summed over the regions and their internal use the rest of the need (l. 315, 866); the
    manure's losses the rest of its internal use (l. 874); UVAP = UVAG x NETF / GROF (l. 2389-2390)."""
    from capri_mod.coupling.equations.sol_simy_ms import (DATA_INTF_FNUT, DATA_INTF_IYANI, DATA_INTF_OYANI,
                                                          DATA_LOSF_FOUT, DATA_LOSF_O_SIMY, DATA_NETF_FNUT_MSAGG,
                                                          DATA_NETF_MS, DATA_NETF_OYANI, DATA_SEDF_O_SIMY,
                                                          DATA_UVAP_MS)
    assert DATA_SEDF_O_SIMY(200.0, 5.0, 100.0) == 10.0 and DATA_SEDF_O_SIMY(200.0, 5.0, 100.0, END=False) == 0.0
    assert DATA_LOSF_O_SIMY(200.0, 0.0, 100.0) == 0.0 and DATA_LOSF_O_SIMY(200.0, 20.0, 0.0) == 0.0
    assert DATA_NETF_MS(200.0, 10.0, 40.0, 5.0) == 145.0
    assert DATA_NETF_OYANI(10.0, DATA_INTF_OYANI([DATA_INTF_IYANI(7.5)])) == 2.5
    assert DATA_NETF_MS(4.0, INTF=DATA_INTF_IYANI(4.0)) == 0.0
    netf = DATA_NETF_FNUT_MSAGG([100.0, 126.10097])
    assert DATA_NETF_MS(442.378514975935, INTF=DATA_INTF_FNUT(442.378514975935, netf)) == pytest.approx(netf)
    assert DATA_NETF_MS(30.0, LOSF=DATA_LOSF_FOUT(30.0, 12.0), INTF=12.0) == 0.0
    # Denmark's N fertiliser in CAPRI's 2030 reference: EAAP 156.91 = 600.68 x (226.10 / 442.38)^2
    uvap = DATA_UVAP_MS(600.676 * 1000 / 442.378514975935, 226.10097, 442.378514975935)
    assert 226.10097 * uvap / 1000 == pytest.approx(156.912, abs=0.01)
    assert DATA_UVAP_MS(100.0, 0.0, 5.0) is None


def test_the_animals_market_items_are_capris_outputs():
    """An animal's market item is CAPRI's output at the same place of its output table: the dairy cows' and milk
    sheep's milk COMI and SGMI, the poultry POUM, the others their own code."""
    from capri_mod.income.eaa_ms import animal_products, crop_products
    ap = animal_products()
    assert ap[("DCOW", "MILK")] == "COMI" and ap[("SHGM", "MILK")] == "SGMI" and ap[("LAYS", "POUL")] == "POUM"
    assert ap[("BROI", "POUL")] == "POUM" and ap[("DCOW", "BEEF")] == "BEEF" and ap[("PIGF", "PORK")] == "PORK"
    cp = crop_products()
    assert cp["CORN"] == "MAIZ" and cp["GRAE"] == "GRAS" and cp["GRAI"] == "GRAS" and cp["WINE"] == "TWIN"
    assert cp["SWHE"] == "SWHE" and "FALL" not in cp


def _unit():
    by_act = pd.DataFrame([("O", "SWHE", "SWHE", 100.0), ("O", "SWHE", None, 4.0), ("O", "MILK", "DCOW", 50.0),
                           ("O", "OTHER_O", "DCOW", 10.0), ("O", "GRAE", "GRAE", 20.0), ("O", "mitiO", None, 1.0),
                           ("I", "YOUNG", "DCOW", 5.0), ("I", "NITF", "SWHE", 11.0), ("I", "FCER", "DCOW", 30.0)],
                          columns=["side", "item", "activity", "EAAG"])
    other_o = pd.DataFrame([("DCOW", "MANN", 3.0), ("DCOW", "YCOW", 7.0)], columns=["activity", "item", "EAAG"])
    items = pd.DataFrame([("NITF", "I", 10.0, 1100.0, 11.0), ("FCER", "I", 30.0, 1000.0, 30.0)],
                         columns=["item", "side", "GROF", "UVAG", "EAAG"])
    purchases = pd.DataFrame([("NITF", 6.0)], columns=["item", "NETF"])
    young = pd.DataFrame([("YCOW", "ICOW", 4.0, 1.0)], columns=["item", "iyani", "GROF", "USE"])
    return SimpleNamespace(eaa={"by_act": by_act, "other_o": other_o, "items": items, "purchases": purchases,
                                "young": young, "EAAP": {"PRME": 8.0}})


def test_the_accounts_at_producer_prices_of_a_member_state():
    """Denmark (one unit) at CAPRI's 2030 farm balance: EAAP = EAAG x (NETF / GROF)^2 item by item, a crop's and the
    technology mix's item under the crop's product, the milk COMI, the grassland GRAS, the manure and the young animals
    bought 0, the young animals sold on their heads' net, the N fertiliser on the purchases over the need; TOOU and
    TOIN the sums, MGVA GVAP + PRME (l. 2547-2562)."""
    from capri_mod.data.inputs import current
    from capri_mod.income.eaa_ms import ms_accounts
    bal = current().csv("ms_farm_balance_2030.csv", "supply").set_index(["ms", "product"])

    def s(p):
        g, sd, l_ = bal.loc[("DK000000", p), ["grof", "sedf", "losf"]]
        return 1.0 - (sd + l_) / g
    a = ms_accounts({"DK000000": _unit(), "HR000000": SimpleNamespace(eaa=None)}, year=2030)
    assert set(a) == {"DK000000"}                    # Croatia's unit has no account
    t = a["DK000000"]["items"].set_index(["side", "item"])
    want_o = {"SWHE": 104.0 * s("SWHE") ** 2, "COMI": 50.0 * s("COMI") ** 2, "GRAS": 20.0 * s("GRAS") ** 2,
              "MANN": 0.0, "YCOW": 7.0 * 0.75 ** 2, "mitiO": 1.0}
    want_i = {"YOUNG": 0.0, "NITF": 11.0 * 0.6 ** 2, "FCER": 30.0}
    for side, w in (("O", want_o), ("I", want_i)):
        for k, v in w.items():
            assert t.loc[(side, k), "EAAP"] == pytest.approx(v), k
    assert ("O", "OTHER_O") not in t.index and ("O", "MILK") not in t.index
    assert t.loc[("I", "NITF"), "GROF"] == 10.0 and t.loc[("I", "NITF"), "NETF"] == pytest.approx(6.0)
    assert t.loc[("O", "YCOW"), "NETF"] == pytest.approx(3.0) and 0.0 < s("GRAS") < 0.5
    e = a["DK000000"]["EAAP"]
    assert e["TOOU"] == pytest.approx(sum(want_o.values())) and e["TOIN"] == pytest.approx(sum(want_i.values()))
    assert e["MGVA"] == pytest.approx(e["TOOU"] - e["TOIN"] + 8.0)
    # at basic prices: the N fertiliser's purchases at the base year's UVAB (outside the market part, l. 70), the crop's
    # product held in value alone none (a market product's needs its quantity), the model's own item at its value
    uv = current().csv("ms_unit_values_2017.csv", "supply").set_index(["ms", "item"]).uvab
    assert t.loc[("I", "NITF"), "EAAB"] == pytest.approx(6.0 * uv[("DK000000", "NITF")] / 1000.0)
    assert t.loc[("O", "SWHE"), "EAAB"] == 0.0 and t.loc[("O", "mitiO"), "EAAB"] == 0.0
    assert a["DK000000"]["EAAB"]["GVAB"] == pytest.approx(a["DK000000"]["EAAB"]["TOOU"] - a["DK000000"]["EAAB"]["TOIN"])


def test_the_member_state_needs_all_its_units():
    """Finland's accounts need all five of its units (capri_data/codes/regional_units.csv)."""
    from capri_mod.income.eaa_ms import ms_accounts
    assert ms_accounts({"FI190000": _unit()}, year=2030) == {}


def test_an_animals_other_outputs_by_capri_output():
    """OTHER_O split (eaa._other_output_parts): the manure per head x level x the member state's unit value, the milk
    for feeding per head x its value, the rest over the young animals the activity produces by value; the young
    animals' heads produced and used at the levels."""
    from capri_mod.data.inputs import current
    from capri_mod.fert.npk import manure_coef_table
    from capri_mod.income.eaa import _other_output_parts
    yc = {"cows": {"produce": {"HFRS": 0.5}, "use": {"DCOW": 0.25}, "value_eur_head": 1000.0},
          "calves_m": {"produce": {"DCOW": 0.4}, "use": {"CALV": 0.6}, "value_eur_head": 150.0},
          "calves_f": {"produce": {"DCOW": 0.4}, "use": {}, "value_eur_head": 130.0}}
    m = SimpleNamespace(_young_animal_coefs=lambda: yc,
                        data=SimpleNamespace(fodder_balance={"FCOM": {"producers": {"DCOW": 0.12}, "value_eur_t": 147.0}}))
    lev = {"DCOW": 500.0, "HFRS": 280.0, "CALV": 300.0}
    oo, young = _other_output_parts("DK000000", m, lev, {("O", "OTHER_O", "DCOW"): 100.0, ("O", "BEEF", "DCOW"): 9.0})
    oo = oo.set_index("item").EAAG
    uv = current().csv("ms_unit_values_2017.csv", "supply").set_index(["ms", "item"]).uvag
    man = {it: manure_coef_table(n).at["DK000000", "DCOW"] * 500.0 * uv[("DK000000", it)] / 1e6
           for it, n in (("MANN", "N"), ("MANP", "P"), ("MANK", "K"))}
    for it, v in man.items():
        assert oo[it] == pytest.approx(v), it
    assert oo["COMF"] == pytest.approx(0.12 * 500.0 * 147.0 / 1000.0)
    rest = 100.0 - sum(man.values()) - oo["COMF"]
    assert oo["YCAM"] == pytest.approx(rest * 60.0 / 112.0) and oo["YCAF"] == pytest.approx(rest * 52.0 / 112.0)
    assert oo.sum() == pytest.approx(100.0)
    y = young.set_index("item")
    assert y.at["YCOW", "GROF"] == pytest.approx(140.0) and y.at["YCOW", "USE"] == pytest.approx(125.0)
    assert y.at["YCAM", "iyani"] == "ICAM" and y.at["YCAM", "USE"] == pytest.approx(180.0)


def test_the_basic_price_unit_values():
    """UVAB at the solution (eaa_ms._uvab): a market product's UVAG plus the base year's wedge (sol_market.gms
    l. 1336-1337; Denmark's barley in CAPRI's 2030 reference: 165.70 + 146.97 - 131.25 = 181.42 EUR/t), in quantity
    only; a good outside the market part its base year UVAB by inflation (l. 70), in value as UVAB / UVAG of the base
    year; a CAPRI item with neither none; the model's own items at their value."""
    from capri_mod.income.eaa_ms import _uvab
    from capri_mod.coupling.equations.inflation_and_trend_interpolation import DATA_UVAB_IO_SIMY
    from capri_mod.market.equations.sol_market import DATA_UVAB_MARR
    assert DATA_UVAB_MARR(165.70, 146.97, 131.25) == pytest.approx(181.42)
    assert DATA_UVAB_MARR(165.70, float("nan"), 131.25) is None and DATA_UVAB_MARR(1.0, 2.0, float("nan")) == 3.0
    sets = ({"BARL", "BEEF"}, {"BARL", "BEEF", "COMI", "FCER"}, {"BARL", "BEEF", "COMI", "FCER", "GRAS", "INPO"})
    f = dict(defl=1.25, marr=sets[0], ioe=sets[1], io=sets[2], DATA_UVAB_MARR=DATA_UVAB_MARR,
             DATA_UVAB_IO_SIMY=DATA_UVAB_IO_SIMY)
    assert _uvab("BARL", 132.56, (131.25, 146.97), True, **f) == pytest.approx(132.56 + 15.72 / 1.25)
    assert _uvab("BEEF", 1000.0, (3708.6, 3926.6), False, **f) is None
    assert _uvab("GRAS", 6.05, (16.09, 33.52), True, **f) == pytest.approx(33.52)
    assert _uvab("INPO", 1000.0, (1341.55, 1341.55), False, **f) == pytest.approx(1000.0)
    assert _uvab("COMI", 529.2, (2766.4, 364.7), True, **f) is None and _uvab("FCER", 117.3, None, True, **f) is None
    assert _uvab("TOIN_lin", 1000.0, None, False, **f) == 1000.0
