"""The mitigation options' accounting cost per activity in CAPRI's report (reports/sol_simy.gms l. 1049-1072;
capri_mod/coupling/equations/sol_simy.py), by hand."""
import pytest


def test_the_cost_with_the_member_states_parameter_where_the_region_has_none():
    """Two targets: the region's linear parameter in the first, the member state's in the second; quadratic terms."""
    from capri_mod.coupling.equations.sol_simy import p_ghgMiti_emisAll_cost
    terms = [(10.0, 99.0, 0.0, 4.0, 0.5, 1.0), (0.0, 20.0, 2.0, 7.0, 0.2, 1.0)]
    want = (10 * 0.5 + 4 * 0.5 * 0.25) + (20 * 0.2 + 2 * 0.5 * 0.04)
    assert p_ghgMiti_emisAll_cost(terms, 1.0) == pytest.approx(want, rel=1e-15)
    assert p_ghgMiti_emisAll_cost(terms, 0.5) == pytest.approx(0.5 * want, rel=1e-15)


def test_genet_reps_factor_is_the_young_cows_price():
    from capri_mod.coupling.equations.sol_simy import p_ghgMiti_emisAll_cost
    assert p_ghgMiti_emisAll_cost([(0.01, 0.0, 0.0, 0.0, 0.3, 800.0)], 1.0) == pytest.approx(0.01 * 0.3 * 800.0)


def test_the_scaling_of_an_animal_and_of_a_crop():
    """An animal's option: its days / 365; a supplement option against enteric CH4: DRMA x days / 1000 x its share of
    dry matter; a supplement option outside that case: 0; a crop: 1."""
    from capri_mod.coupling.equations.sol_simy import p_ghgMiti_emisAll_cost_scale as sc
    assert sc(True, False, False, DAYS=292.0) == pytest.approx(0.8)
    v = sc(True, True, True, DAYS=292.0, DRMA=20.0, prodDays=300.0, ShrOfDM=0.02)
    assert v == pytest.approx(20 * 300 / 1000 * 0.02)
    assert sc(True, True, False, DAYS=292.0) == 0.0
    assert sc(False, True, True, DAYS=292.0) == 1.0


def test_the_fertiliser_options_cost_per_ha_on_the_application_before_the_options():
    """Mineral N 150 kg/ha, manure N 80 kg/ha; one option on each, the other options' othImpact raising the base."""
    from capri_mod.coupling.equations.sol_simy import p_ghgMiti_emisAll_cost_GainsTechFert as f
    v = f([(30.0, 0.0, 10.0, 0.0, 0.4)], 150.0, [(-0.1, 0.0, 0.5)], [(0.0, 12.0, 0.0, 0.0, 0.6)], 80.0, [])
    want = (30 * 0.4 + 10 * 0.5 * 0.16) * 0.15 * (1 - 0.05) + 12 * 0.6 * 0.08
    assert v == pytest.approx(want, rel=1e-15)


def test_urea_tillage_and_the_per_level_forms():
    from capri_mod.coupling.equations import sol_simy as S
    assert S.p_ghgMiti_emisAll_cost_UreaSubst([(5.0, 2.0, 0.3)]) == pytest.approx(5 * 0.3 + 2 * 0.5 * 0.09)
    assert S.p_ghgMiti_emisAll_cost_till(17.0, 2.0, 0.6) == 17.0
    assert S.p_ghgMiti_emisAll_cost_till(17.0, 2.0, 0.0) == 0.0
    assert S.p_ghgMiti_emisAll_cost_catc(6.0, 0.25) == pytest.approx(24.0)
    assert S.p_ghgMiti_emisAll_cost_catc(6.0, 1e-9) == 0.0
    assert S.p_ghgMiti_emisAll_cost_idlHis(300.0, 0.5) == pytest.approx(600.0)


def test_the_revenue_and_the_subsidy_linear_in_the_shares():
    from capri_mod.coupling.equations import sol_simy as S
    assert S.p_ghgMiti_emisAll_revenue([(0.0, 8.0, 0.5), (3.0, 9.0, 1.0)], 0.8) == pytest.approx((4.0 + 3.0) * 0.8)
    assert S.p_ghgMiti_emisAll_subsidy([(2.0, 0.0, 0.25)], 1.0) == pytest.approx(0.5)
    f = S.p_ghgMiti_emisAll_subsidy_GainsTechFert([(40.0, 0.0, 0.5)], 100.0, [], [], 0.0, [])
    assert f == pytest.approx(40 * 0.5 * 0.1)
    r = S.p_ghgMiti_emisAll_revenue_GainsTechFert([], 0.0, [], [(0.0, 10.0, 0.2)], 50.0, [(0.3, 0.0, 1.0)])
    assert r == pytest.approx(10 * 0.2 * 0.05 * 1.3)
    assert S.p_ghgMiti_emisAll_subsidy_UreaSubst([(6.0, 0.5)]) == pytest.approx(3.0)
    assert S.p_ghgMiti_emisAll_subsidy_till(4.0, 1.0, 0.0) == 0.0


def test_mitiI_and_mitiO_valued_at_their_price_give_the_options_cost_and_revenue():
    """mitiI x UVAG / 1000 is the cost at the year's prices; CATC has none (its cost is in its inputs); the
    subsidies add to the premiums."""
    from capri_mod.coupling.equations import sol_simy as S
    uv = S.DATA_UVAG_mitiRepRowsQ(1.019, 2030, 2017)
    assert uv == pytest.approx(1000.0 * 1.019 ** 13)
    q = S.DATA_mitiI("DCOW", [12.0, 3.0], uv)
    assert q * uv / 1000.0 == pytest.approx(15.0, rel=1e-15)
    assert S.DATA_mitiI("CATC", [12.0], uv) is None
    assert S.DATA_mitiO([4.0], uv) * uv / 1000.0 == pytest.approx(4.0, rel=1e-15)
    assert S.DATA_PRME_mitiSubs(250.0, S.DATA_mitiSubs([5.0, 1.5])) == pytest.approx(256.5)


def test_the_pmp_cost_kept_apart():
    """The same quadratic form on pmpParLin and pmpParSqr; winter cover's per-level division without a threshold."""
    from capri_mod.coupling.equations import sol_simy as S
    v = S.p_ghgMiti_emisAll_pmpcost([(2.0, 0.0, 0.0, 6.0, 0.5)], 0.5)
    assert v == pytest.approx((2 * 0.5 + 6 * 0.5 * 0.25) * 0.5)
    assert S.p_ghgMiti_emisAll_pmpcost_catc(3.0, 1e-9) == pytest.approx(3e9)
    assert S.p_ghgMiti_emisAll_pmpcost_catc(3.0, 0.0) == 3.0
    assert S.p_ghgMiti_emisAll_pmpcost_idlHis(3.0, 1e-9) == 0.0


def test_the_fertiliser_options_items_of_a_region():
    """Two options, one with the region's row and one with the member state's; the inhibitor on manure left to its
    block; cost per t of N x the mineral N bought x (1 + the options' N saving), in EUR 1000."""
    from collections import namedtuple
    from capri_mod.income.mitigation_items import fert_options_items
    R = namedtuple("R", "costParLin costParSqr pmpParSqr revenue")
    nan = float("nan")
    rows = {("DE110000", "VRT_SRUC"): R(50.0, 20.0, 30.0, nan), ("DE000000", "VRT_SRUC"): R(99.0, 99.0, 99.0, nan),
            ("DE000000", "PRECFARM"): R(300.0, nan, 300.0, 4.0)}
    shares = {"VRT_SRUC": 0.5, "PRECFARM": 0.1, "NITR_INH_MAN": 0.4}
    out = fert_options_items("DE110000", shares, {"VRT_SRUC": 0.2, "PRECFARM": 0.1}, 2000.0, rows)
    base = 2000.0 * (1 + 0.2 * 0.5 + 0.1 * 0.1)
    assert out["mitiI"] == pytest.approx(((50 * 0.5 + 20 * 0.5 * 0.25) + 300 * 0.1) * base / 1000.0)
    assert out["mitiO"] == pytest.approx(4.0 * 0.1 * base / 1000.0)
    assert out["mitiPmp"] == pytest.approx((30 * 0.5 * 0.25 + 300 * 0.5 * 0.01) * base / 1000.0)


def test_the_inhibitor_on_manure_on_the_manure_n_applied():
    from collections import namedtuple
    from capri_mod.income.mitigation_items import manure_inhibitor_items
    R = namedtuple("R", "costParLin costParSqr pmpParSqr revenue")
    rows = {("DE000000", "NITR_INH"): R(86.0, float("nan"), 158.0, float("nan"))}
    out = manure_inhibitor_items("DE110000", 0.4, 0.3, 500.0, rows)
    assert out["mitiI"] == pytest.approx(86 * 0.4 * 500.0 * (1 + 0.3 * 0.4) / 1000.0)
    assert out["mitiPmp"] == pytest.approx(158 * 0.5 * 0.16 * 500.0 * (1 + 0.3 * 0.4) / 1000.0)
    assert manure_inhibitor_items("DE110000", 0.0, 0.3, 500.0, rows)["mitiI"] == 0.0


def test_the_ammonia_options_and_ad_per_head_and_in_total():
    """Two sub-activities of the dairy cows (weights 0.5), one option each and AD with a revenue; places per unit
    0.9; 100 (1000 heads) cows: EUR 1000 = EUR per head x 1000 heads."""
    from capri_mod.income.mitigation_items import ammonia_items
    subs = {("DCOW", "R|DCOL"): {"w": 0.5, "stock": 0.9, "techs": {"CovStorHigh": (0.4, 30.0, 4.0, 0.0)}},
            ("DCOW", "R|DCOH"): {"w": 0.5, "stock": 0.9, "techs": {"AD_AnCh": (0.1, 10.0, 17.0, 13.5)}}}
    out = ammonia_items(subs, {"DCOW": 100.0})
    c = 0.5 * 0.9 * (30 * 0.4 + 4 * 0.5 * 0.16) + 0.5 * 0.9 * (10 * 0.1 + 17 * 0.5 * 0.01)
    assert out["mitiI_per_head"]["DCOW"] == pytest.approx(c)
    assert out["mitiI"] == pytest.approx(100.0 * c)
    assert out["mitiO"] == pytest.approx(100.0 * 0.5 * 0.9 * 13.5 * 0.1)


def test_winter_cover_tillage_and_legume_share_items():
    from collections import namedtuple
    from capri_mod.income import mitigation_items as M
    W = namedtuple("W", "cost_lin_eur_ha pmp_lin pmp_sqr")
    out = M.winter_cover_items({"endogenous": True, "share": 0.2, "uaa": 100.0, "req": 19.0}, W(150.0, -40.0, 300.0))
    assert out["mitiI"] == pytest.approx(150.0 * 19.0)
    assert out["mitiPmp"] == pytest.approx((-40 * 0.2 + 0.5 * 300 * 0.04) * 100.0)
    assert M.winter_cover_items({"endogenous": False, "req": 19.0}, W(150.0, 0.0, 0.0))["mitiI"] == 0.0
    rows = {"MinTill": W(20.0, 5.0, 10.0), "NoTill": W(-8.0, 2.0, 0.0)}
    out = M.tillage_items({"MinTill": 0.3, "NoTill": 0.1}, 50.0, rows)
    assert out["mitiI"] == pytest.approx((20 * 0.3 - 8 * 0.1) * 50.0)
    assert out["mitiPmp"] == pytest.approx((5 * 0.3 + 10 * 0.5 * 0.09 + 2 * 0.1) * 50.0)
    out = M.legume_share_items(0.25, 40.0, W(60.0, 10.0, 80.0))
    assert out["mitiI"] == pytest.approx(60 * 0.25 * 40.0)
    assert out["mitiPmp"] == pytest.approx((10 * 0.25 + 80 * 0.5 * 0.0625) * 40.0)


def test_urea_substitution_on_the_n_bought_and_as_capris_report_codes_it():
    """FIX-10: per t of N bought x the N bought (t; EUR 1000 = EUR/t x t / 1000), against CAPRI's report: the same
    parameter per ha of each crop."""
    from collections import namedtuple
    from capri_mod.income.mitigation_items import urea_substitution_items as u
    R = namedtuple("R", "cost_lin_eur_t pmp_lin pmp_sqr")
    r = R(12.0, 3.0, 40.0)
    out = u(0.5, 20000.0, {"SWHE": 30.0, "BARL": 10.0}, r)
    assert out["mitiI"] == pytest.approx(12 * 0.5 * 20000.0 / 1000.0)
    assert out["mitiPmp"] == pytest.approx((3 * 0.5 + 40 * 0.5 * 0.25) * 20.0)
    assert u(0.5, 20000.0, {"SWHE": 30.0, "BARL": 10.0}, r, form="capri")["mitiI"] == pytest.approx(12 * 0.5 * 40.0)
    with pytest.raises(ValueError):
        u(0.5, 1.0, {}, r, form="x")


def test_the_histosols_fallowing_at_capris_restoration_cost():
    from capri_mod.income.mitigation_items import histosol_fallow_items
    from capri_mod.params import param
    assert param("HISTOSOL_FALLOW_COST") == 216.0
    assert histosol_fallow_items({"iHisCr": 2.0, "iHisGr": 0.5})["mitiI"] == pytest.approx(216.0 * 2.5)



def test_the_herd_options_at_their_cost_per_head_adopting():
    """Breeding on 2 (1000) dairy cows, low-N feed on 10 (1000) bulls, a feed additive: each its cost per head
    adopting (CAPRI's scaling inside it) x the heads adopting."""
    from capri_mod.income.mitigation_items import herd_option_items
    eff = {("DCOW", "genet_yld"): {"cost_eur_head": 20.0}, ("BULL", "lowNFeed"): {"cost_eur_head": 5.0},
           ("DCOW", "LINE_Tot"): {"cost_eur_head": 30.0, "shr_of_dm": 0.05}}
    out = herd_option_items({("DCOW", "genet_yld"): 2.0, ("BULL", "lowNFeed"): 10.0, ("DCOW", "LINE_Tot"): 1.0}, eff)
    assert out["mitiI"] == pytest.approx(20 * 2 + 5 * 10 + 30 * 1)
    assert out["mitiI_by_animal"]["BULL"] == pytest.approx(50.0)


def test_the_feed_term_of_income_i1():
    """The solved ration at its report prices less the margins' feed (feed_lin x level), the herds with their feeding
    in the regional model only: 10 (1000) cows eating 2,000 t at 0.2 EUR/kg and 500 t at 0.03, their margin carrying
    40 EUR per head; an animal without feed_lin is left out."""
    import pandas as pd
    from types import SimpleNamespace
    from capri_mod.income.income_module import IncomeDistributionModule as I
    res = SimpleNamespace(feed_lin={"DCOW": 40.0}, activities=pd.Series({"DCOW": 10.0, "PIGF": 5.0}),
                          feed_t={"DCOW": {"FCER": 2000.0, "FGRA": 500.0}, "PIGF": {"FCER": 900.0}},
                          feed_price={"DCOW": {"FCER": 0.2, "FGRA": 0.03}, "PIGF": {"FCER": 0.2}})
    assert I.feed_term(res) == pytest.approx(2000 * 0.2 + 500 * 0.03 - 40.0 * 10.0)


def test_the_fed_fodder_at_capris_scenario_value():
    """CAPRI's UVAG(fodder, SIM) per t fed with FODDMARKUP 0 (K213): the fodder balance's dual at the solution (EUR/t,
    so / 1000 per kg); a feed without a balance at the ration's price."""
    import pandas as pd
    from types import SimpleNamespace
    from capri_mod.income.income_module import IncomeDistributionModule as I
    res = SimpleNamespace(feed_lin={"DCOW": 0.0}, activities=pd.Series({"DCOW": 10.0}),
                          feed_t={"DCOW": {"FGRA": 500.0, "FCER": 100.0}},
                          feed_price={"DCOW": {"FGRA": 0.03, "FCER": 0.2}}, fodder_duals={"fodder_FGRA": 42.0})
    assert I.feed_term(res) == pytest.approx(500 * 0.042 + 100 * 0.2)


def test_calc_inc_indic_mgva_and_the_regions_aggt():
    """An activity's MGVA at the solution: its linear margin less the change of its feed (EUR per head); the region's
    AGGT: the activities' MGVA x levels, less the options' cost plus their revenue (EUR 1000); ProfitAgr: AGGT - RENT."""
    from capri_mod.coupling.equations.calc_inc_indic import DATA_MGVA
    from capri_mod.coupling.equations.sol_simy import DATA_AGGT_MGVA
    from capri_mod.market.equations.welfare import p_welfareRes_EAAG_ProfitAgr
    assert DATA_MGVA(1500.0, 800.0, 860.0) == pytest.approx(1440.0)
    assert DATA_MGVA(300.0, 0.0, 0.0) == 300.0
    assert DATA_AGGT_MGVA([1440.0, 300.0], [10.0, 100.0], 7.0, 2.0) == pytest.approx(14400 + 30000 - 7 + 2)
    assert p_welfareRes_EAAG_ProfitAgr(44395.0, 395.0) == 44000.0


def test_income_parts_of_a_region():
    """income_parts on a hand-built region: two crops and a herd, the herd's solved ration dearer than its margin's
    feed by 6 EUR per head, a technology mix on 2 (1000) ha of SWHE, no mitigation option adopted."""
    import pandas as pd
    from types import SimpleNamespace
    from capri_mod.income.income_module import IncomeDistributionModule as I
    model = SimpleNamespace(net_revenues=pd.Series({"SWHE": 600.0, "MAIZ": 500.0, "DCOW": 1500.0}),
                            premiums=pd.Series({"SWHE": 200.0, "MAIZ": 200.0, "DCOW": 100.0}),
                            ev=SimpleNamespace(mix_dnr={"SWHE": 40.0}, nlp_nip=None),
                            data=SimpleNamespace(techn_mix=pd.DataFrame({"prem_diff_share": [0.1]}, index=["SWHE"]),
                                                 genetics_effects=None))
    sm = SimpleNamespace(_models={"FR810000": model})
    res = SimpleNamespace(activities=pd.Series({"SWHE": 100.0, "MAIZ": 0.0, "DCOW": 10.0}),
                          feed_lin={"DCOW": 800.0}, feed_t={"DCOW": {"FCER": 40000.0}},
                          feed_price={"DCOW": {"FCER": 0.2015}}, technology_mix={"SWHE": 2.0})
    ip = I(None).income_parts("FR810000", res, sm)
    feed = 40000 * 0.2015 - 800 * 10                         # EUR 1000: 8,060 - 8,000, 6 EUR per head x 10
    assert ip["FEED"] == pytest.approx(feed)
    assert ip["MGVA_act"] == pytest.approx({"SWHE": 600.0, "DCOW": 1500.0 - feed / 10})
    assert ip["MGVA"] == pytest.approx(600 * 100 + (1500 - 6) * 10 + 40 * 2)
    assert ip["PRME"] == pytest.approx(200 * 100 + 100 * 10 + 0.1 * 200 * 2)
    assert ip["mitiI"] == 0.0 and ip["mitiO"] == 0.0


def test_the_crops_toin_at_the_years_coefficients():
    """CAPRI's TOIN of a crop at the simulation year: TF_I x the yield-dependent inputs at the year's coefficients plus
    the fertilisers' need at their unit value (EUR per ha); DATA_MGVA swaps it for the margin's base cost."""
    from capri_mod.coupling.equations.calc_inc_indic import DATA_MGVA, DATA_TOIN_Y
    t = DATA_TOIN_Y(1000.0, 0.935, [200.0, 30.0, 50.0], [1000.0, 1500.0, 600.0])
    assert t == pytest.approx(935.0 + 0.2 * 1000 + 0.03 * 1500 + 0.05 * 600)
    assert DATA_MGVA(600.0, 0.0, 0.0, 1445.0, t) == pytest.approx(600.0 - (t - 1445.0))
    assert DATA_MGVA(600.0, 0.0, 0.0) == 600.0


def test_crop_toin_y_of_a_regional_model():
    """crop_toin_y on a hand-built regional model at the 2030 market year: the crops with a year coefficient (SWHE)
    get CAPRI's TOIN with CAPRI's 2030 need per crop and the nutrients' unit values of the region (DK000000, the
    model's data); a crop without one (MAIZ) and the animals keep the margin's cost; no table, no swap."""
    import pandas as pd
    from types import SimpleNamespace
    from capri_mod.fert.npk import NPKData, NUTRIENTS
    from capri_mod.income.income_module import IncomeDistributionModule as I
    model = SimpleNamespace(net_revenues=pd.Series({"SWHE": 600.0, "MAIZ": 500.0, "DCOW": 1500.0}),
                            data=SimpleNamespace(input_coefs_2030=pd.DataFrame({"iy_uvag_eur_ha": [1300.0]},
                                                                               index=["SWHE"]),
                                                 variable_costs=pd.Series({"SWHE": 1445.6, "MAIZ": 1200.0})),
                            _input_row_2030=lambda a, c: 1300.0 / 1.25 if a == "SWHE" else None,
                            _greendeal_tech_progress=lambda: 0.935)
    out = I.crop_toin_y("DK000000", model)
    D = NPKData.get()
    need = sum(D.crop_coef("DK000000", n, "SWHE", "need_kg_ha") * float(D.region("DK000000", n).uvag_eur_t)
               for n in NUTRIENTS) / 1000.0
    assert set(out) == {"SWHE"}
    assert out["SWHE"] == pytest.approx((1445.6, 0.935 * 1300.0 / 1.25 + need))
    assert 300.0 < need < 600.0
    model.data.input_coefs_2030 = None
    assert I.crop_toin_y("DK000000", model) == {}
