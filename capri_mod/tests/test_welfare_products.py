"""CAPRI's farm profit and domestic support by market product (reports/welfare.gms l. 441-468, 714-749;
capri_mod/income/welfare_products.py, register DEP-58), by hand."""
from types import SimpleNamespace

import pandas as pd
import pytest


def test_the_model_activities_market_products_are_capris():
    """Each model activity takes its CAPRI members' product in PACT_TO_XX as CAPRI's run built it (sim_ini_21730):
    the dairy cows and milk sheep BUTT (rep_sets.gms l. 118-120), the suckler cows, calves and heifers BEEF, the sows
    PORK, sugar beet SUGA, the fodder crops, the grassland, the fixed activities and the idle land INPE (l. 122)."""
    from capri_mod.income.welfare_products import cap_to_trd, pact_to_xx
    x = pact_to_xx()
    want = {"SWHE": "WHEA", "DWHE": "WHEA", "CORN": "MAIZ", "SUGB": "SUGA", "PARI": "RICE", "OLIV": "OLIO",
            "DCOW": "BUTT", "SHGM": "BUTT", "BCOW": "BEEF", "CALV": "BEEF", "HFRS": "BEEF", "BULL": "BEEF",
            "PIGS": "PORK", "PIGF": "PORK", "LAYS": "EGGS", "BROI": "POUM", "SHGF": "SGMT", "GRAE": "INPE",
            "MAIF": "INPE", "OANI": "INPE", "FALL": "INPE", "OCRO": "INPE"}
    for a, v in want.items():
        assert x[a] == v, a
    c = cap_to_trd()
    assert c["SWHE"] == "WHEA" and c["BEEF"] == "BEEF" and "COMI" not in c and "GRAS" not in c


def test_the_profit_and_support_by_product_of_a_member_state():
    """Two units of one member state: a product's ProfitAgr is its activities' MGVA x levels (the technology mix's
    MGVA on the area moved with its crop), INPE the activities outside the market's products plus the options' revenue
    less their cost, LAND the rents; PSEs minus the premium outlays over CAP_TO_TRD, INPE the outputs outside it; the
    rows add up to MGVA - RENT and to - PRME."""
    from capri_mod.income.welfare_products import welfare_by_product

    def unit(mgva, lev, mix=None, z=None, mo=0.0, mi=0.0):
        inc = {"MGVA_act": mgva, "MGVA_mix": mix or {}, "mitiO": mo, "mitiI": mi}
        inc["MGVA"] = (sum(v * lev[a] for a, v in mgva.items()) + sum(v * z[a] for a, v in (mix or {}).items())
                       + mo - mi)
        return SimpleNamespace(income=inc, activities=pd.Series(lev), technology_mix=z or {})
    sr = {"DE110000": unit({"SWHE": 500.0, "DCOW": 2000.0, "GRAI": -300.0}, {"SWHE": 100.0, "DCOW": 10.0, "GRAI": 20.0},
                           mix={"SWHE": 40.0}, z={"SWHE": 5.0}, mo=10.0, mi=30.0),
          "DE120000": unit({"DWHE": 400.0, "PIGS": 150.0}, {"DWHE": 10.0, "PIGS": 50.0})}
    feop = pd.DataFrame({"FEOP": [20.0, 1.5, 2.0, 0.5]},
                        index=pd.MultiIndex.from_tuples([("DE000000", "SWHE"), ("DE000000", "COMI"),
                                                         ("DE000000", "GRAS"), ("DE000000", "DWHE")]))
    t = welfare_by_product(sr, feop, {"DE110000": 3.0, "DE120000": 1.0}).loc["DE000000"]
    assert t.at["WHEA", "ProfitAgr"] == pytest.approx((500.0 * 100 + 40.0 * 5 + 400.0 * 10) / 1000)
    assert t.at["BUTT", "ProfitAgr"] == pytest.approx(20.0)
    assert t.at["PORK", "ProfitAgr"] == pytest.approx(7.5)
    assert t.at["INPE", "ProfitAgr"] == pytest.approx(-6.0 + 0.010 - 0.030)
    assert t.at["LAND", "ProfitAgr"] == pytest.approx(-4.0)
    mgva = sum(u.income["MGVA"] for u in sr.values()) / 1000
    assert t.ProfitAgr.sum() == pytest.approx(mgva - 4.0)
    assert t.at["WHEA", "PSEs"] == pytest.approx(-20.5) and t.at["INPE", "PSEs"] == pytest.approx(-3.5)
    assert t.PSEs.sum() == pytest.approx(-24.0)
    assert t.loc["BUTT"].isna()["PSEs"]                     # raw milk is outside the market's products: INPE


def test_the_pse_and_profit_statements():
    """PSEs = - FEOP - the support wedges x their quantities - FEOE - FEOS (l. 716-740); INPE = - FEOG (l. 745-746); the
    total the sum (l. 748); ProfitAgr's INPE and LAND (l. 454-460)."""
    from capri_mod.market.equations.welfare import (p_welfareRes_EAAG_PSEs, p_welfareRes_ProfitAgr_INPE,
                                                    p_welfareRes_ProfitAgr_LAND, p_welfareRes_PSEs_INPE,
                                                    p_welfareRes_PSEs_XX1)
    assert p_welfareRes_PSEs_XX1([167.083050130185]) == pytest.approx(-167.083050130185)      # Denmark's WHEA, 2030
    assert p_welfareRes_PSEs_XX1([1.0, 2.0], PSEi=10.0, Prod=500.0, FSEi=2.0, Feed=100.0, FEOE=0.5) == pytest.approx(
        -(3.0 + 5.0 + 0.2 + 0.5))
    assert p_welfareRes_PSEs_INPE([1.0, 2.5]) == -3.5 and p_welfareRes_EAAG_PSEs([-1.0, -2.0]) == -3.0
    assert p_welfareRes_ProfitAgr_INPE(5.0, [1.0], [0.5, 0.25]) == pytest.approx(5.25)
    assert p_welfareRes_ProfitAgr_LAND(12.0) == -12.0
