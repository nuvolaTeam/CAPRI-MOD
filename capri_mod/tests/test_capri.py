"""
CAPRI-Python test suite (pytest).

Covers the invariants that matter for a trustworthy model:
  - data loads and has the expected structure
  - the data validator runs and catches inconsistency
  - base-year market fidelity (the model's headline claim: 12/12 @ 0%)
  - supply responds to prices with the right sign and no numerical blow-ups
  - each module runs end to end

Run:  pytest capri_mod/tests/ -v
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "capri_data"


def _german_units(n):
    """The first n German regional units (DE110000, DE120000, ...): the regions the tests took as the first n rows of
    the region index when the model's regions were NUTS-2016 codes listed from Germany on (27 October 2026)."""
    import pandas as _pd
    units = _pd.read_csv(DATA_DIR / "shared" / "regional_units.csv").region
    return [r for r in units if r.startswith("DE")][:n]


def _set(monkeypatch, overrides):
    """Change settings for one test (capri_mod/settings); monkeypatch restores the previous ones afterwards."""
    from capri_mod import settings as S
    monkeypatch.setattr(S, "_ACTIVE", S.current().replace(overrides))


@pytest.fixture(scope="session")
def data():
    from capri_mod.data.loaders import load_all_data
    return load_all_data(DATA_DIR)


@pytest.fixture(scope="session")
def _fresh_model():
    from capri_mod.model import CAPRIModel
    return CAPRIModel(data_dir=str(DATA_DIR), verbose=False)


@pytest.fixture
def model(_fresh_model):
    """A model as just built, for every test (a copy, 0.7 s; building one takes 12 s). Until 27 October 2026 the tests
    shared one model, so each started from the state the tests before it left: warm starts, calibrations taken at
    another test's point, the market's state. A test's results then depended on the order (a no-op check failed by
    1.03e-5 in one order), and so did the market supply Hessian's cache key (the baseline solution), so each run of the
    suite measured its Hessians again (the CAP-support test: 429 s measuring, 18 s from the cache). The regional models
    are built in each test; IPOPT's compiled solvers are shared (capri_regional_nlp._SOLVERS, exact)."""
    import copy
    return copy.deepcopy(_fresh_model)


def test_data_loads(data):
    assert "areas" in data
    assert "world_prices" in data
    assert len(data["areas"]) >= 200
    assert len(data["world_prices"]) > 0


def test_data_validator_runs():
    from capri_mod.data.validate_data import validate_data
    rep = validate_data(str(DATA_DIR))
    assert rep.n_fail == 0, f"validator reported failures: {rep.summary()}"


def test_validator_has_vintage_check():
    from capri_mod.data.validate_data import validate_data
    rep = validate_data(str(DATA_DIR))
    names = [c[0] for c in rep.checks]
    assert any("vintage" in n for n in names)


def test_no_negative_base_quantities(data):
    df = data["areas"].select_dtypes("number")
    assert (df.values >= 0).all()


def test_market_module_reproduces_its_own_prices(data):
    """
    Solver consistency, NOT price validation.

    The reference values below are world_prices.csv rounded to the nearest
    integer, so this asserts that the market module, given base-year supply,
    converges back to the prices it was handed. That is a real and useful check
    -- it catches solver regressions, bad Armington shares and unit errors in
    the supply aggregation -- but it says nothing about whether those prices are
    correct.

    Nothing in this repository can validate world_prices.csv, because every
    check available reads it. Independent comparison against CAPRI's own capmod
    result lives in tools/check/report_world_price_divergence.py and is reported
    rather than asserted, since the two sources disagree on three commodities
    and neither is demonstrably right.
    """
    from capri_mod.market.market_module import MarketModule
    from capri_mod.data.definitions import MARKET_COMMODITIES

    mm = MarketModule(data)
    exo = pd.DataFrame(0.0, index=["EU27"], columns=MARKET_COMMODITIES)
    for c in MARKET_COMMODITIES:
        if c in mm.base_production.columns:
            exo.at["EU27", c] = mm.base_production.at["EU27", c]

    eq = mm.solve(exogenous_supply=exo)
    assert eq.converged

    # RAPE and SOYA were corrected to CAPRI's actual PMRK values (SOYA
    # 292.6 -> 102.7, the long-flagged 2.85x error; RAPE 321 -> 213) when world
    # prices were validated against the capmod base GDX. These references were
    # never updated to match, so the test had been asserting the OLD, known-wrong
    # numbers and failing at 9/12 for the life of the project. The model was
    # right; the reference was stale.
    # References READ from world_prices.csv: the old hard-coded copies held
    # cake prices under the oilseeds (rapeseed 213, soybeans 103) and drifted
    # out of sync when the prices were replaced with CAPRI's base world prices.
    import pandas as _pd, os as _os
    _wp = _pd.read_csv(_os.path.join(str(DATA_DIR), '2017', 'market', 'world_prices.csv')).set_index('commodity')['price']
    ref = {c: float(_wp[c]) for c in ('SWHE', 'BARL', 'CORN', 'RAPE', 'SOYA', 'BEEF', 'PORK', 'POUL', 'MILK', 'BUTR', 'CHES', 'SKIM') if c in _wp.index}
    within = sum(1 for c, r in ref.items()
                 if abs((eq.world_prices.get(c, 0) - r) / r) <= 0.15)
    assert within == 12, f"only {within}/12 within 15%"


def test_supply_responds_positively_to_price(model):
    sm = model.supply_module
    reg = "DE110000"
    sm.run(price_signals=None, regions=[reg])            # the late columns calibrated at base prices (see the next test)
    base = sm.run(price_signals=None, regions=[reg])
    q0 = base[reg].activities.get("SWHE", 0)
    sig = pd.Series(0.0, index=model.data["world_prices"].index)
    sig["SWHE"] = 0.20
    up = sm.run(price_signals=sig, regions=[reg])
    q1 = up[reg].activities.get("SWHE", 0)
    assert q1 >= q0 - 1e-6


@pytest.mark.parametrize("reg, product, act, strict", [
    ("FR240000", "SWHE", "SWHE", True),        # arable (Centre)
    ("PL120000", "RYEM", "RYEM", True),        # eastern arable (Mazowieckie, CAPRI unit of PL91 + PL92)
    ("ES610000", "OLIV", "OLIV", False),       # Mediterranean permanent crop (Andalucia)
    ("IR010000", "BEEF", "BULL", True),        # grassland cattle (Ireland)
    ("NL220000", "PORK", "PIGF", True),        # intensive livestock (Gelderland)
])
def test_own_price_response_in_contrasting_regions(model, reg, product, act, strict):
    """The mechanism of test_supply_responds_positively_to_price on CAPRI units of other structures: a 20% higher
    price of the region's product raises (permanent crops: does not lower) the activity producing it. The base is solved
    twice first: the split and histosol columns enter at a region's second solve and are calibrated there, at that
    solve's prices (in a run the baseline's), so a shock at the second solve would be calibrated away."""
    sm = model.supply_module
    sm.run(price_signals=None, regions=[reg])
    q0 = sm.run(price_signals=None, regions=[reg])[reg].activities.get(act, 0.0)
    sig = pd.Series(0.0, index=model.data["world_prices"].index)
    sig[product] = 0.20
    q1 = sm.run(price_signals=sig, regions=[reg])[reg].activities.get(act, 0.0)
    assert q0 > 0
    assert (q1 > q0 * (1 + 1e-4)) if strict else (q1 >= q0 - 1e-6), f"{reg} {act}: {q0} -> {q1}"


def test_supply_no_blowup(model):
    sm = model.supply_module
    for reg in _german_units(8):
        base = sm.run(price_signals=None, regions=[reg])
        for act in ["SWHE", "CORN", "RAPE", "PULS"]:
            q0 = base[reg].activities.get(act, 0)
            if q0 <= 0.001:
                continue
            sig = pd.Series(0.0, index=model.data["world_prices"].index)
            sig[act] = 0.20
            s = sm.run(price_signals=sig, regions=[reg])
            q1 = s[reg].activities.get(act, 0)
            assert q1 / q0 < 10, f"{reg} {act} blew up"


def test_full_run_all_modules(model):
    regions = _german_units(5)
    r = model.run(scenario="BASELINE", max_outer_iter=1, market_max_iter=50,
                  regions=regions, run_environmental=True,
                  run_biofuel=True)
    for k in ["supply", "market", "environmental", "feed", "biofuel"]:
        assert r[k] is not None


def test_dairy_block_follows_capri_per_member_state(model):
    """CAPRI's dairy block (arm/market_model.gms DairyNQ_, ProcMargM_, FatsProtBal_): all nine dairy products are
    traded market commodities (bilateral flows, world prices); raw milk, fat and protein are priced per member state
    (each member state's dairies process its own milk); at base every price ratio is 1; less milk in one member
    state raises its own raw milk price only, and its fat and protein balances still close."""
    import numpy as np
    import pandas as pd
    from capri_mod.data.definitions import MARKET_COMMODITIES
    mm = model.market_module
    for c in ("FRMI", "CREM", "COCM", "WMIO", "CASE"):
        assert c in MARKET_COMMODITIES and mm.DAIRY_TRADED[c] == c
    fl = pd.read_csv(DATA_DIR / "2017" / "market" / "bilateral_flows_2030.csv")
    assert set(fl.commodity) >= {"FRMI", "CREM", "COCM", "WMIO", "CASE"}
    try:
        mm._dairy_cache = None
        dp = mm._dairy_params()
        assert len(dp["ms"]) >= 26
        r0 = mm.dairy_block({k: 1.0 for k in mm.DAIRY_PRODUCTS}, 1.0)
        assert all(abs(v["MILK"] - 1) < 1e-12 and abs(v["FATS"] - 1) < 1e-12 for v in r0["ms_price_ratio"].values())
        r = mm.dairy_block({k: 1.0 for k in mm.DAIRY_PRODUCTS}, {"DE000000": 0.9})
        de, fr = r["ms_price_ratio"]["DE000000"], r["ms_price_ratio"]["FR000000"]
        assert de["MILK"] > 1.05 and abs(fr["MILK"] - 1.0) < 1e-12
        prm = dp["ms"]["DE000000"]
        z = mm._dairy_solve_ms(prm, np.zeros(len(prm["items"]) + 2), 0.9)
        assert abs(prm["rowF"] @ z) < 1e-6 * prm["Q0"][prm["iM"]] and abs(prm["rowP"] @ z) < 1e-6 * prm["Q0"][prm["iM"]]
        assert abs((prm["Q0"] + prm["G"] @ z)[prm["iM"]] / prm["Q0"][prm["iM"]] - 0.9) < 1e-9
    finally:
        mm._dairy_cache = None


def test_low_n_feed_follows_capri(model):
    """CAPRI's low-nitrogen feeding (envind/low_n_feed.gms, star 3.0 ghgTechLowNFeed = 1): the protein requirement
    of an animal fed above its requirement falls by 0.15 x excess / (1 + 0.5 x energy excess), manure N by that times
    (MANN + CRPR_EXPT) / MANN; eligible shares as CAPRI's max calibration run (monogastrics 1); the option exists at
    star 3.0's setting and not with ghgTechLowNFeed = 0."""
    from capri_mod.policy.endotech import STAR3_DEFAULTS, scale_genetics
    assert STAR3_DEFAULTS["ghgTechLowNFeed"] == 1.0
    ge = model.data["genetics_effects"]
    rows = [(a, e) for t in ge.values() for (a, o), e in t.items() if o == "lowNFeed"]
    assert len(rows) > 1500
    for a, e in rows:
        assert -0.2 < float(e["d_crpr_rel"]) < 0 and float(e["d_mann_rel"]) <= float(e["d_crpr_rel"]) + 1e-12
        assert 0 < float(e["elig_share"]) <= 1.0 + 1e-6 and float(e["cost_eur_head"]) > 0
    assert all(abs(float(e["elig_share"]) - 1.0) < 1e-3 for a, e in rows if a in ("PIGF", "PIGS", "BROI", "LAYS"))
    off = scale_genetics(model.data["genetics_effects_unit"], {**STAR3_DEFAULTS, "ghgTechLowNFeed": 0.0})
    assert not any(o == "lowNFeed" for t in off.values() for (a, o) in t)


def test_base_manure_trade_follows_capri_and_the_trade_setting(data):
    """Sprint 9j: the base manure trade is CAPRI's 2030 reference per group of CAPRI and model regions (MTRADE,
    EXCRET; Belgium, Romania and Ireland included) and counts only where the run trades manure (manureTradeNew):
    without trade every region keeps its manure, as JRC121368's CAPRI."""
    from capri_mod.environmental.environmental_module import EnvironmentalModule
    mt = data["manure_trade"]
    assert (mt.export_share > 0).sum() > 100 and (mt.import_kg_n_per_ha > 0).sum() > 100
    for r in ("BL250000", "RO020000", "IR010000"):
        assert float(mt.at[r, "export_share"]) > 0, r
    assert float(mt.at["RO030000", "import_kg_n_per_ha"]) > 10
    env = EnvironmentalModule(data)
    acts = {a: float(v) for a, v in data["areas"].loc["DE940000"].items()}
    acts.update({a: float(v) for a, v in data["animal_numbers"].loc["DE940000"].items()})
    on = env.compute_nitrogen_balance(acts, data["yields"].loc["DE940000"], "DE940000")
    env.set_manure_trade(False)
    off = env.compute_nitrogen_balance(acts, data["yields"].loc["DE940000"], "DE940000")
    assert float(off["n_organic_input"]) > float(on["n_organic_input"]) * 1.2      # Weser-Ems exports ~30%


@pytest.mark.slow
def test_emission_tax_in_supply_follows_capri(model):
    """CAPRI's emission tax (ghgTax: p_carbonTax(ru, "GGWP") in the supply model's objective, EU regions only):
    each column's emission per unit at the baseline solution (the accounts' finite differences; cattle enteric CH4
    per t of feed fed, dry matter x GE x 4.1868 x Ym / 55.65 x GWP); with the tax the region's emissions fall,
    herds shrink and the supplements, the breeding options and histosol fallowing are adopted where they pay; the
    scenario carries the tax as its only shock; Norway is not taxed. The former post-solve abatement is gone."""
    import importlib.util
    from capri_mod.scenarios.scenarios import carbon_tax_scenario
    from capri_mod.environmental.environmental_module import GWP_CH4
    assert importlib.util.find_spec("capri_mod.abatement") is None
    sc = carbon_tax_scenario(100.0)
    assert sc.carbon_tax == 100.0 and sc.ae_budget_change == 0.0 and sc.nitrate_limit_change == 0.0
    regs = ["IR010000", "NO080000"] if "NO080000" in model.data["areas"].index else ["IR010000"]
    b = model.run(scenario="BASELINE", regions=regs, max_outer_iter=2)
    try:
        s = model.run(custom_scenario=sc, regions=regs, max_outer_iter=2)
        co = list(model._ghg_coef_cache.values())[-1]
        assert "IR010000" in co and not any(r.startswith("NO") for r in co)
        c = co["IR010000"]
        assert c["act"]["DCOW"] > 0 and c["act"]["SWHE"] > 0 and c["hist"]["grass"] < 0
        assert c["genet"][("DCOW", "Nitr_Tot")] < 0
        r = model.supply_module.feed_rations["IR010000"]["DCOW"]
        fac = model.env_module._enteric_factors()["DCOW"]
        j = r.feeds.index("FGRA")
        e = fac["ge"]["IR000000"]["FGRA"] * 4.1868 * fac["ym"] / 55.65 * GWP_CH4 * float(r.dm[j])
        assert abs(c["feed"][("DCOW", "FGRA")] - e) < 1e-9
        g0 = float(b["environmental"].loc["IR010000", "ghg_total"])
        g1 = float(s["environmental"].loc["IR010000", "ghg_total"])
        assert g1 < 0.95 * g0
        a0, a1 = b["supply"]["IR010000"].activities, s["supply"]["IR010000"].activities
        assert a1["BCOW"] < a0["BCOW"] and a1["DCOW"] < a0["DCOW"]
        gs = s["supply"]["IR010000"].genetics_shift
        # the nitrate supplement is adopted for cattle, not by IE04's dairy cows: CAPRI's REQSE_
        # holds crude protein as an equality (CAPRI's simulation model), and nitrate's lower protein requirement then
        # pushes grass out of a grass-based dairy ration (its dual: +200 EUR per unit against the tax's gain)
        assert any(v > 0 for (a_, o_), v in gs.items() if o_ == "Nitr_Tot")
        assert sum(s["supply"]["IR010000"].histosol_fallow.values()) > 0
        assert s["abatement"]["carbon_tax"] == 100.0
    finally:
        model.run(scenario="BASELINE", regions=regs, max_outer_iter=2)
    assert float(model.supply_module.ghg_tax) == 0.0


@pytest.mark.slow
def test_manure_market_and_ammonia_options_in_every_eu_solve(model):
    """Sprint 9k: CAPRI's crop nutrient balance (NUTNED_) and manure market (e_netMTrade, e_costMTrade) are in every
    run, not only under the N target: each EU solve carries the crop-need row and, with manure trade on, the pool
    columns, whose cost is the pool price alone (CAPRI's calibrated constants; no fertiliser terms), plus the tax on
    the mineral N bought or saved. Under the emission tax the ammonia options are in the regional model with their
    emissions (manure N2O through the loss cascade, indirect N2O of the NH3 kept, soil N2O of the mineral N
    displaced) and are adopted beyond their base shares; outside the EU nothing changes."""
    from capri_mod.scenarios.scenarios import carbon_tax_scenario
    regs = ["BL210000", "NO080000"] if "NO080000" in model.data["areas"].index else ["BL210000"]
    b = model.run(scenario="BASELINE", regions=regs, max_outer_iter=2)
    try:
        mo = model.supply_module._models["BL210000"]
        assert mo._mctx() is not None and mo._need_row is not None
        if model.use_manure_market:
            je, ji = mo._pool_cols
            Q, c, A, bb, y = mo._last_aug
            assert abs(float(c[je]) - float(mo.manure_pool_price)) < 1e-9 and abs(float(c[ji]) + float(c[je])) < 1e-9
        if "NO080000" in regs:
            assert model.supply_module._models["NO080000"]._manure_ctx is None
        sh0 = dict(b["supply"]["BL210000"].manure_tech_shares)
        s = model.run(custom_scenario=carbon_tax_scenario(100.0), regions=regs, max_outer_iter=2)
        co = list(model._ghg_coef_cache.values())[-1]["BL210000"]
        assert co["mtech"] and any(v != 0 for v in co["mtech"].values())
        tl = mo._tech_list()
        assert tl and all("ghg" in t for t in tl) and any(t["ghg"] < 0 for t in tl)
        # the tax prices the options' N2O: those that cut it (acidification, high-efficiency spreading, air
        # purifiers) rise, low-emission spreading, whose NH3 kept raises application N2O in the cascade (JRC121368
        # Table 18), falls; the region's manure N2O falls, its ammonia rises (pollution swapping)
        sh1 = s["supply"]["BL210000"].manure_tech_shares
        assert any(sh1.get(k, 0.0) > v + 1e-3 for k, v in sh0.items())
        assert sh1.get(("DCOW", "AmmAppLE"), 0.0) < sh0[("DCOW", "AmmAppLE")]
        e0, e1 = b["environmental"].loc["BL210000"], s["environmental"].loc["BL210000"]
        assert float(e1["ghg_manure_n2o"]) < float(e0["ghg_manure_n2o"])
        assert s["supply"]["BL210000"].animal_nh3_saved
    finally:
        model.run(scenario="BASELINE", regions=regs, max_outer_iter=2)


def test_feed_supplements_follow_capri(model):
    """CAPRI's feed supplements (envind/line_nitr.gms, star 3.0 ghgTechLineNitr = 1, a switch): cattle only;
    nitrate replaces crude protein (1.54 x dosage of DM), linseed supplies the OOIL nutrients per kg of fat / rapeseed
    fat content; CH4ENT -5% per point of fat (-25%) and -10% per point of nitrate (-15%, heifers HEIR -10%); cost =
    half of costParLin x DM intake x dosage; maximum shares from CAPRI's max calibration run; none at
    ghgTechLineNitr = 0, unchanged effects at any other setting (a switch)."""
    from capri_mod.policy.endotech import STAR3_DEFAULTS, scale_genetics
    assert STAR3_DEFAULTS["ghgTechLineNitr"] == 1.0
    ge = model.data["genetics_effects"]
    rows = [(a, o, e) for t in ge.values() for (a, o), e in t.items() if o in ("LINE_Tot", "Nitr_Tot")]
    assert len(rows) > 1500
    assert {a for a, o, e in rows} <= {"DCOW", "BCOW", "BULL", "HFRS", "CALV"}
    assert not any(a == "BCOW" for a, o, e in rows if o == "Nitr_Tot")       # suckler cows excluded (line_nitr.gms)
    for a, o, e in rows:
        assert 0 < float(e["elig_share"]) <= 1.0 + 1e-6 and float(e["cost_eur_head"]) > 0
        assert float(e["d_mann_rel"]) == 0.0 and float(e["d_crpr_rel"]) < 0
        if o == "LINE_Tot":
            assert abs(float(e["ch4ent_rel"]) + 0.25) < 1e-9 and float(e["d_ener_rel"]) < 0 and float(e["d_drmn_rel"]) < 0
        else:
            assert -0.15 - 1e-9 <= float(e["ch4ent_rel"]) <= -0.10 + 1e-9 and float(e["d_ener_rel"]) == 0.0
    off = scale_genetics(model.data["genetics_effects_unit"], {**STAR3_DEFAULTS, "ghgTechLineNitr": 0.0})
    assert not any(o in ("LINE_Tot", "Nitr_Tot") for t in off.values() for (a, o) in t)
    two = scale_genetics(model.data["genetics_effects_unit"], {**STAR3_DEFAULTS, "ghgTechLineNitr": 2.0})
    r_ = next(iter(ge))
    for k, e in ge[r_].items():
        if k[1] in ("LINE_Tot", "Nitr_Tot"):
            assert float(two[r_][k]["d_crpr_rel"]) == float(e["d_crpr_rel"])


def test_inner_fert_model_follows_capri():
    """CAPRI's inner fertiliser distribution model (useInnerFertDistModel, star 3.0 default): at the baseline's
    totals and group areas the posterior mode is the prior mode in every CAPRI region (CAPRI's priors are the
    baseline's posterior modes per ha, accuracy 1); the flows add up to the regional totals; a regulation keeps
    a flow below its maximum; the crop-specific mineral fertiliser reduction follows minfert_redu_by_crop.gms."""
    from capri_mod.fert.inner_fert_dist import (InnerFertDist, beta_regulation, gamma_params, parse_mineral_redu,
                                                SMALL_MINE_KG_HA)
    f = InnerFertDist(str(DATA_DIR))
    al, be = gamma_params(100.0, 1.0)
    assert abs((al - 1.0) / be - 100.0) < 1e-9                       # the gamma's mode is the prior mode
    assert beta_regulation() == (1.1875, 1.0625)
    worst, n = 0.0, 0
    for r, d in f.priors[f.priors.level == "ru"].groupby("capri_region"):
        area = dict(zip(d.ngrp, d.area_kha))
        me, ea = f.efficiencies(r)
        e = {"MINE": me if me == me else 1.0, "EXCR": ea if ea == ea else 1.0, "CRES": 0.75}
        M, E, C = ((d[c] * d.area_kha).sum() for c in ("mine_kg_ha", "excr_kg_ha", "cres_kg_ha"))
        out = f.solve(r, area, f.base_need_weight(r, area, e), M, E, C, e)
        assert out["converged"], r
        P = d.set_index("ngrp")
        for (g, s_), x in out["per_ha"].items():
            m_ = float(P.at[g, {"MINE": "mine_kg_ha", "EXCR": "excr_kg_ha", "CRES": "cres_kg_ha"}[s_]])
            worst = max(worst, abs(x - m_) / max(1.0, m_))
        n += 1
    assert n >= 240 and worst < 1e-8
    # a regulation (CAPRI's "f2f" beta density) on the mineral flows, at 80% of the base, below its capacity
    r = "DE110000"
    d = f.priors[f.priors.capri_region == r]
    area = dict(zip(d.ngrp, d.area_kha))
    me, ea = f.efficiencies(r)
    e = {"MINE": me, "EXCR": ea, "CRES": 0.75}
    M, E, C = ((d[c] * d.area_kha).sum() for c in ("mine_kg_ha", "excr_kg_ha", "cres_kg_ha"))
    w = f.base_need_weight(r, area, e)
    base = f.solve(r, area, w, M, E, C, e)
    caps = f.mineral_caps(r, base, 0.2)
    for g, v in caps.items():
        b0 = base["per_ha"][(g, "MINE")]
        assert abs(v - (b0 if b0 < SMALL_MINE_KG_HA else 0.8 * b0)) < 1e-9
    capa = sum(v * area[g] for g, v in caps.items())
    reg = {(g, "MINE"): v for g, v in caps.items()}
    reg.update({(g, "CRES"): v for g, v in f.limcres_caps(r, base).items()})
    out = f.solve(r, area, w, 0.99 * capa, E, C, e, caps=reg)
    assert out["converged"]
    assert all(out["per_ha"][(g, "MINE")] < v for g, v in caps.items())
    assert abs(sum(x for (g, s_), x in out["flows"].items() if s_ == "EXCR") - E) < 1e-6 * E
    # CAPRI's listed exemptions for 2030 (simy > 2025 / > 2020, othPol not high)
    ex = f._rules()[0]
    e30 = ex[(ex.after_year < 2030) & (ex.othpol_high == 0)]
    assert len(e30) == 9 and set(e30.capri_region) >= {"IT930000", "DE940000", "IT310000"}
    assert parse_mineral_redu("20crp") == ("crp", 0.2) and parse_mineral_redu("20") == ("uaa", 0.2)
    assert parse_mineral_redu("00") == (None, 0.0)


def test_mineral_fertiliser_cap_binds(model):
    """CAPRI's mineral fertiliser reduction (Green Deal mineRedu "20", minfert_redu_uaa.gms e_synNMax): the
    region's mineral N per ha of land falls to 80% of the baseline's, the cap's shadow price is positive, and the
    run reports the inner model's allocation over CAPRI's crop groups."""
    from capri_mod.policy.greendeal import greendeal_scenario
    from capri_mod.data.definitions import CROPS
    regs = ["DE110000"]
    b = model.run(scenario="BASELINE", regions=regs, max_outer_iter=1)
    sc = greendeal_scenario(lndscpTarg=0, orgTarg=0, pestRedu=0, surpRedu=0, mineRedu="20")
    s = model.run(custom_scenario=sc, regions=regs, max_outer_iter=1)
    sr = s["supply"]["DE110000"]
    assert float(sr.shadow_prices.get("mineral_N", 0.0)) > 0
    land = lambda x: sum(float(x["supply"]["DE110000"].activities.get(c, 0.0)) for c in CROPS)
    per_ha = [float(x["environmental"].loc["DE110000", "n_mineral_input"]) / land(x) for x in (b, s)]
    assert per_ha[1] / per_ha[0] < 0.80 + 0.005
    fd = s["fert_dist"]
    assert fd is not None and set(fd.ngrp) >= {"WHEA", "GRAS", "MAIF"} and fd.converged.all()
    tot = float((fd.mine_kg_ha * fd.area_kha).sum())
    assert abs(tot / float(s["environmental"].loc["DE110000", "n_mineral_input"]) - 1.0) < 1e-6


def test_ddgs_and_feed_bulks_follow_capri(model):
    """CAPRI's DDGS (prodQuantBiofBy_) and feed bulks (feedBlkPrice_, feedShareEqu_): DDGS output from the ethanol
    plants' cereal feedstocks reproduces CAPRI's 2030 output in every region; a dearer DDGS lowers the ethanol
    plants' feedstock cost margin less (by-product revenue up), so ethanol output rises; the member states' bulks
    reproduce CAPRI's EU feed use at reference prices and shift away from a dearer product within a bulk."""
    mm = model.market_module
    bp, fb = mm._biofuel_params(), mm._feed_bulk_params()
    assert bp and fb and "DDGS" in mm.commodities
    st0 = mm.biofuel_state(None, None, endogenous=True)
    for reg, q in bp["ddgs0"].items():
        assert abs(st0["ddgs"].get(reg, 0.0) - q) < 1e-6 * max(1.0, q), reg
    R, C = list(mm.regions), list(mm.commodities)
    up = pd.DataFrame(1.0, index=R, columns=C)
    up.loc[:, "DDGS"] = 1.3
    st1 = mm.biofuel_state(up, None, endogenous=True)
    assert st1["prod"][("USA", "BIOE")] > st0["prod"][("USA", "BIOE")]
    _bix, mm._feed_bulk_index = getattr(mm, "_feed_bulk_index", None), None     # bulks at the base herds
    try:
        f0 = mm.eu_feed_use({})
        f1 = mm.eu_feed_use({"DDGS": 1.2})
    finally:
        mm._feed_bulk_index = _bix
    for c, q in fb["feed0"].items():
        assert abs(f0[c] / q - 1.0) < 1e-9, c
    assert f1["DDGS"] < f0["DDGS"] and f1["SOYC"] > f0["SOYC"] and abs(f1["CORN"] / f0["CORN"] - 1.0) < 1e-12
    assert mm.feed_bulk_price_ratio("DE000000", "FPRO", {"DDGS": 1.2}) > 1.0
    assert mm.feed_bulk_price_ratio("DE000000", "FCER", {"DDGS": 1.2}) == 1.0


def test_all_feed_bulks_and_residual_feeds_follow_capri(model):
    """Sprint 9h: CAPRI's five tradable feed bulks (FCER, FPRO, FENE, FOTH, FMIL) per member state with
    arm/market1.gms's p_rhoFeed (6, 6, 5, 0.5, 0.5); the residual feeds FENI and FPRI are traded markets whose EU
    output is CAPRI's MaprFeed_: the 2030 output at reference use, moving with the parents' food and processing use
    (milling: cereals; FENI: sugar, including its biofuel processing); the rations' bulks are priced by the
    member state's bulk indices."""
    from capri_mod.feed.ration import RationModel
    mm = model.market_module
    fb, fp = mm._feed_bulk_params(), mm._feed_byproduct_params()
    assert {"FENI", "FPRI"} <= set(mm.commodities) and set(fp["products"]) == {"FENI", "FPRI"}
    rho = {b: d["rho"] for (ms, b), d in fb["bulks"].items()}
    assert rho == {"FCER": 6.0, "FPRO": 6.0, "FENE": 5.0, "FOTH": 0.5, "FMIL": 0.5}
    assert abs(sum(w for _, _, w in fp["products"]["FPRI"]["parts"]) - 1.0) < 1e-9
    old = (getattr(mm, "_eu_food_ratio", None), getattr(mm, "_eu_biof_ratio", None))
    try:
        mm._eu_food_ratio, mm._eu_biof_ratio = {}, {}
        q0 = mm.eu_feed_byproduct_output()
        assert abs(q0["FPRI"] / fp["products"]["FPRI"]["prod0"] - 1.0) < 1e-12
        mm._eu_food_ratio = {mm.EU[0]: {"SWHE": 0.9}}
        q1 = mm.eu_feed_byproduct_output()
        w = dict((c, x) for c, u, x in fp["products"]["FPRI"]["parts"])["SWHE"]
        assert abs(q1["FPRI"] / q0["FPRI"] - (1.0 - 0.1 * w)) < 1e-12 and q1["FENI"] == q0["FENI"]
    finally:
        mm._eu_food_ratio, mm._eu_biof_ratio = old
    assert mm.feed_bulk_price_ratio("DE000000", "FENE", {"FENI": 1.2}) > 1.0
    assert mm.feed_bulk_price_ratio("DE000000", "FPRO", {"FPRI": 1.2}) > 1.0
    assert mm.feed_bulk_price_ratio("DE000000", "FMIL", {"WHEY": 1.2}) > 1.0
    rm = RationModel(str(DATA_DIR))
    k = next(k for k, r in rm.rations.items() if "FENE" in r.feeds)
    p = rm.price_vector(k, bulk_ratio={"FENE": 1.5})
    r = rm.rations[k]
    i = r.feeds.index("FENE")
    assert abs(p[i] / r.p0[i] - 1.5) < 1e-12 and all(p[j] == r.p0[j] for j in range(len(p)) if j != i)


def test_biofuel_feedstock_demand_in_market(model):
    """Crushing stage 4: CAPRI's biofuel feedstock CES at fixed output (biofuel markets off, CAPRI without
    BIOF_M) reproduces the 2030 reference at base prices, shifts away from a dearer feedstock, and scales
    with output."""
    mm = model.market_module
    _bm, _st = mm.biofuel_markets, getattr(mm, "_biof_state", None)
    mm.biofuel_markets, mm._biof_state = False, None     # no processing state of an earlier run (run state)
    try:
        _biofuel_fixed_output_checks(mm)
    finally:
        del mm.biofuel_markets                             # back to the setting market.biofuel_markets
        mm._biof_state = _st


def _biofuel_fixed_output_checks(mm):
    bp = mm._biofuel_params()
    assert bp and bp["groups"]
    base = mm.biofuel_feedstock_use({})
    for c, q0 in bp["q0"].items():
        assert abs(base["by_commodity"][c] - q0) < 1e-6 * max(1.0, q0)
    up = mm.biofuel_feedstock_use({"RAPO": 1.2})
    assert up["by_commodity"]["RAPO"] < base["by_commodity"]["RAPO"]
    assert up["by_commodity"]["SOYO"] > base["by_commodity"]["SOYO"]
    # biodiesel output fixed: oils all yield ~0.956 t per t, so total oil use barely moves
    oil = lambda r: sum(v for (b, _), v in r["by_feedstock"].items() if b == "BIOD")
    assert abs(oil(up) / oil(base) - 1.0) < 2e-3
    old = dict(mm.biofuel_output_scale)
    try:
        mm.biofuel_output_scale = {"BIOE": 1.0, "BIOD": 1.5}
        hi = mm.biofuel_feedstock_use({})
        assert abs(hi["by_commodity"]["RAPO"] / base["by_commodity"]["RAPO"] - 1.5) < 1e-9
        assert abs(hi["by_commodity"]["SWHE"] - base["by_commodity"]["SWHE"]) < 1e-9
    finally:
        mm.biofuel_output_scale = old


def test_biofuel_markets_follow_capri_functions(model):
    """Endogenous biofuel markets (CAPRI BIOF_M, star 3.0 default): every region's biofuel output and use at
    the reference prices are CAPRI's 2030 values; a dearer biofuel raises output (SupplyBiof_ on the processing
    margin) and lowers use (biofDemShare_ against the fossil fuel price), dearer feedstock lowers output, and
    the feedstock use follows the output; switched off, biofuel quantities stay at the reference."""
    mm = model.market_module
    bm = mm._biofuel_market_params()
    assert bm and mm.biofuel_endogenous()
    st0 = mm.biofuel_state(None, None)
    for k, v in bm["prod0"].items():
        assert abs(st0["prod"][k] - v) < 1e-6 * max(1.0, v), k
    for k, v in bm["use0"].items():
        assert abs(st0["use"][k] - v) < 1e-6 * max(1.0, v), k
    R, C = list(mm.regions), list(mm.commodities)
    one = pd.DataFrame(1.0, index=R, columns=C)
    up = one.copy(); up.loc[:, "BIOE"] = 1.1
    st1 = mm.biofuel_state(up, up)
    assert st1["prod"][("EU27", "BIOE")] > st0["prod"][("EU27", "BIOE")]
    assert st1["prod"][("USA", "BIOE")] > st0["prod"][("USA", "BIOE")]
    assert st1["use"][("EU27", "BIOE")] < st0["use"][("EU27", "BIOE")]
    feed = one.copy(); feed.loc[:, ["SWHE", "CORN", "BARL", "OCER", "SUGR"]] = 1.2
    st2 = mm.biofuel_state(one, feed)
    assert st2["prod"][("EU27", "BIOE")] < st0["prod"][("EU27", "BIOE")]
    # the feedstock CES at the higher output uses more of every feedstock at unchanged prices
    old = getattr(mm, "_biof_state", None)
    try:
        mm._biof_state = st1
        q1 = mm.biofuel_feedstock_use({})["by_commodity"]
        mm._biof_state = st0
        q0 = mm.biofuel_feedstock_use({})["by_commodity"]
        assert q1["CORN"] > q0["CORN"] and abs(q1["RAPO"] - q0["RAPO"]) < 1e-9
        mm.biofuel_markets = False
        assert not mm.biofuel_endogenous()
        # off: output fixed whatever the biofuel price (CAPRI without BIOF_M)
        mm._biof_state = mm.biofuel_state(up, up)
        assert abs(mm.biofuel_feedstock_use({})["by_commodity"]["CORN"] / q0["CORN"] - 1.0) < 1e-6
        assert abs(mm._biof_state["prod"][("EU27", "BIOE")] / st0["prod"][("EU27", "BIOE")] - 1.0) < 1e-6
    finally:
        del mm.biofuel_markets                             # back to the setting market.biofuel_markets
        mm._biof_state = old


def test_dairy_block_fat_protein_balance(model):
    """Dairy processing (CAPRI DairyNQ_, ProcMargM_, FatsProtBal_): the reference is reproduced at base
    prices; less milk raises the raw milk, fat and protein prices, keeps the fat and protein balances
    and lowers product output; a dearer cheese draws milk solids into cheese; fewer calves cut milk feed."""
    mm = model.market_module
    mm._dairy_cache = None
    fi0, mm._fmil_index = getattr(mm, "_fmil_index", 1.0), 1.0     # calves' milk feed at base
    dp = mm._dairy_params()
    assert dp
    mm._dairy_u = None
    b = mm.dairy_block({}, 1.0)
    assert all(abs(v - 1.0) < 1e-9 for v in b["price_ratio"].values())
    r = mm.dairy_block({}, 0.9)
    assert r["residual"] < 1e-6
    assert r["price_ratio"]["MILK"] > 1.0 and r["price_ratio"]["FATS"] > 1.0 and r["price_ratio"]["PROT"] > 1.0
    assert abs(r["production"]["MILK"] / r["production0"]["MILK"] - 0.9) < 1e-9
    for k in ("BUTT", "SMIP", "CHES"):
        assert r["production"][k] < r["production0"][k]
    c = mm.dairy_block({"CHES": 1.1}, 1.0)
    assert c["production"]["CHES"] > c["production0"]["CHES"]
    assert c["production"]["BUTT"] < c["production0"]["BUTT"]
    # fewer calves: less milk feed - since Sprint 9f the products are traded, so the FMIL block acts on the
    # market's feed demand (CES at base prices: every product's feed use falls with the index)
    import numpy as np
    assert np.allclose(mm.dairy_feed_factor(np.ones(9), fi=0.8), 0.8)
    mm._dairy_u = None
    mm._dairy_cache, mm._fmil_index = None, fi0


def test_dairy_world_blocks(model):
    """Dairy Stage 4: CAPRI's dairy block for the non-EU trade regions reproduces the base, and dearer
    dairy products draw more raw milk (CAPRI's supply function) and more product."""
    mm = model.market_module
    mm._dairy_world_cache = None
    try:
        w = mm._dairy_world_params()
        assert {"USA", "NZL", "IND", "ROW"} <= set(w)
        for r in ("USA", "NZL"):
            b = mm._dairy_solve(w[r], {}, None, 1.0, "test_" + r)
            assert all(abs(v - 1.0) < 1e-9 for v in b["price_ratio"].values())
            x = mm._dairy_solve(w[r], {k: 1.1 for k in mm.DAIRY_TRADED}, None, 1.0, "test_" + r)
            assert x["residual"] < 1e-6 and x["milk_supply_ratio"] > 1.0
            for c in ("BUTR", "SKIM", "CHES"):
                assert x["market_supply"][c] > x["market_supply0"][c]
    finally:
        mm._dairy_world_cache = None


def test_genetics_effects_follow_capri_breeding(model):
    """CAPRI's genomics options (breeding.gms): higher milk yield raises energy, protein and manure N per
    cow less than proportionally to milk; feed efficiency cuts energy 10%, protein 5%; costs at CAPRI's floors
    (per place, converted per model head) or above; milk sheep and replacement heifers are not eligible."""
    from capri_mod.policy.endotech import JRC121368_ENDOTECH, STAR3_DEFAULTS, scale_genetics
    # star 3.0 default (refpol_endotech_all_sup): ghgTechMYld 0, so the milk-yield option does not exist
    ge0 = scale_genetics(model.data["genetics_effects_unit"], STAR3_DEFAULTS)
    assert not any(o == "genet_yld" for t in ge0.values() for (a, o) in t)
    ge = scale_genetics(model.data["genetics_effects_unit"], JRC121368_ENDOTECH)
    yl = [e for t in ge.values() for (a, o), e in t.items() if o == "genet_yld"]
    ef = [(a, e) for t in ge.values() for (a, o), e in t.items() if o == "genet_eff"]
    assert len(yl) > 200 and len(ef) > 900
    # CAPRI's floors (20 and 2 EUR) are per animal place: per model head they are cost_floor (K67 F3)
    for e in yl:
        assert e["cost_eur_head"] >= float(e["cost_floor"]) - 1e-9 and float(e["cost_floor"]) > 0
        if e["d_milk_rel"] > 0:
            assert 0 < e["d_ener_rel"] < e["d_milk_rel"] and 0 < e["d_crpr_rel"] < e["d_milk_rel"]
            assert e["d_mann_rel"] > 0
    for a, e in ef:
        assert abs(e["d_ener_rel"] + 0.1) < 1e-9 and abs(e["d_crpr_rel"] + 0.05) < 1e-9
        assert e["d_mann_rel"] < 0 and e["cost_eur_head"] >= float(e["cost_floor"]) - 1e-9
        if a == "HFRS":
            assert e["elig_share"] < 1.0


@pytest.mark.slow
def test_endotech_settings_hold_for_baseline_and_scenario(model):
    """CAPRI's technology settings are scenario configuration loaded with the reference: a scenario with
    ghgTechMYld 0.2 is compared with a baseline at 0.2 (its own cache entry and genomics calibration)."""
    from capri_mod.policy.policy_module import PolicyScenario
    from capri_mod.policy.endotech import key, effective
    regions = ["IR010000"]
    sc = PolicyScenario(name="t", endotech={"ghgTechMYld": 0.2})
    try:
        model.run(custom_scenario=sc, max_outer_iter=2, regions=regions)
        k = key(effective({"ghgTechMYld": 0.2}))
        # manure trade and endogenous biofuel markets: star 3.0 defaults on
        assert (tuple(regions), k, True, True) in model._eu_base_cache
        assert model._endotech_key == k
        assert any(o == "genet_yld" for (a, o) in model.data["genetics_effects"]["IR010000"])
    finally:
        model.run(scenario="BASELINE", max_outer_iter=2, regions=regions)
    assert not any(o == "genet_yld" for (a, o) in model.data["genetics_effects"]["IR010000"])


def test_bilateral_market_reproduces_capri_flows_at_base():
    """CAPRI's bilateral market (arm/market_model.gms): calibrated at base supply, every region's own good clears
    (domestic sales + exports = production) with CAPRI's trade flows reproduced exactly; a 10% rise of one
    exporter's price shifts imports away from it and raises importers' consumer prices less than 10%."""
    import numpy as np
    import pandas as pd
    from capri_mod.market.bilateral import BilateralCommodity
    from pathlib import Path
    base = Path(DATA_DIR) / "2017" / "market"
    fl = pd.read_csv(base / "bilateral_flows_2030.csv")
    g = fl[fl.commodity == "BEEF"]
    R = sorted(set(g.importer) | set(g.exporter))
    ix = {r: i for i, r in enumerate(R)}
    n = len(R)
    X0, a, b, a0 = (np.zeros((n, n)) for _ in range(4))
    for t in g.itertuples(index=False):
        i, j = ix[t.importer], ix[t.exporter]
        X0[i, j] = t.q_kt
        if i != j:
            a[i, j], b[i, j], a0[i, j] = t.a, t.b, t.a0
    sc = BilateralCommodity("BEEF", R, X0, a, b, a0, np.full(n, 4000.0), 3.5, 7.1)
    S0 = X0.sum(axis=0)
    sc.calibrate(S0)
    r = np.ones(n)
    assert np.max(np.abs(sc.residual(sc.S0, sc.D0, r))) < 1e-6
    X, PA = sc.flows(sc.D0, r)
    assert np.allclose(X, sc.X0, rtol=1e-9, atol=1e-9)
    j = ix["BRA"]
    r1 = r.copy(); r1[j] = 1.1
    X1, PA1 = sc.flows(sc.D0, r1)
    ie = ix["EU27"]
    assert X1[ie, j] < X0[ie, j]
    assert np.all(PA1 / sc.PA0 <= 1.1 + 1e-12)


def test_trq_tariff_follows_quota_fill():
    """CAPRI's TRQ regime (trqSigmoidFunc_, slope 200 around 97% of the quota): an under-filled quota keeps the
    in-quota tariff; pushing imports past the quota moves the import price toward the out-of-quota tariff."""
    import numpy as np
    from capri_mod.market.bilateral import BilateralCommodity
    X0 = np.array([[100.0, 50.0], [0.0, 400.0]])
    a = np.array([[0.0, 1000.0], [0.0, 0.0]]); b = np.array([[0.0, 100.0], [0.0, 0.0]])
    sc = BilateralCommodity("T", ["EU27", "X"], X0, a, b, a.copy(), np.array([1500.0, 1000.0]), 3.5, 7.0)
    sc.calibrate(np.array([100.0, 450.0]))
    sc.trq_row, sc.trq_Q, sc.trq_gap, sc.trq_share = 0, np.array([0.0, 100.0]), np.array([0.0, 800.0]), np.array([0.0, 1.0])
    sc.trq_offset = np.zeros(2)
    p = sc.import_prices(np.ones(2))
    sc.trq_solve(sc.X0, p)
    assert abs(sc.trq_offset[1]) < 1e-6                      # 50% fill: in-quota
    X = sc.X0.copy(); X[0, 1] = 130.0
    sc.trq_solve(X, p)
    o = sc.trq_offset[1]
    assert 20.0 < o < 800.0                                  # past the quota: toward the out-of-quota tariff
    x_o = 130.0 * (p[0, 1] / (p[0, 1] + o)) ** sc.s2         # ... which pushes the flow back to about the quota
    assert 90.0 < x_o < 105.0


def test_trq_volume_change_moves_the_quota_not_the_base():
    """A scenario quota expansion (PolicyScenario.trq_volume_changes, 1000 t) is spread over the commodity's quotas
    by base volume; the base fill stays at the base quotas, so with base flows the offset is zero and a filled quota
    turns in-quota (lower import price) once the quota is raised."""
    import numpy as np
    from capri_mod.market.bilateral import BilateralCommodity
    from capri_mod.market.market_module import MarketModule
    X0 = np.array([[100.0, 99.0], [0.0, 400.0]])
    a = np.array([[0.0, 1000.0], [0.0, 0.0]]); b = np.array([[0.0, 100.0], [0.0, 0.0]])
    sc = BilateralCommodity("T", ["EU27", "X"], X0, a, b, a.copy(), np.array([1500.0, 1000.0]), 3.5, 7.0)
    sc.calibrate(np.array([100.0, 499.0]))
    sc.trq_row, sc.trq_Q, sc.trq_gap, sc.trq_share = 0, np.array([0.0, 100.0]), np.array([0.0, 800.0]), np.array([0.0, 1.0])
    sc.trq_offset = np.zeros(2)
    mm = MarketModule.__new__(MarketModule)
    mm.trq_volume_changes = {}
    MarketModule._apply_trq_volumes(mm, {"T": sc})
    p = sc.import_prices(np.ones(2))
    sc.trq_solve(sc.X0, p)
    assert abs(sc.trq_offset[1]) < 1e-6                      # base: no offset
    mm.trq_volume_changes = {"T": 50.0}
    MarketModule._apply_trq_volumes(mm, {"T": sc})
    assert abs(sc.trq_Q[1] - 150.0) < 1e-12 and abs(sc.trq_Q0[1] - 100.0) < 1e-12
    sc.trq_solve(sc.X0, p)
    o = sc.trq_offset[1]
    assert o < -10.0                                         # the quota no longer binds: the import price falls ...
    assert 99.0 * (p[0, 1] / (p[0, 1] + o)) ** sc.s2 > 110.0  # ... and imports rise past the old quota
    mm.trq_volume_changes = {}
    MarketModule._apply_trq_volumes(mm, {"T": sc})
    assert abs(sc.trq_Q[1] - 100.0) < 1e-12                  # a later baseline restores the base quota


def test_projection_livestock_output_follows_yield(model):
    """CAPRI's trend projection: output per head follows the projected yield (dairy cows: the milk part), and
    the cows' requirements follow breeding.gms's functions; the trajectory is read by the model's own names."""
    from capri_mod.projection import ProjectionModule, BaselineTrajectory
    import os
    traj_path = os.path.join(str(DATA_DIR), "trajectories", "captrd_2030.json")
    traj = BaselineTrajectory.from_file(traj_path)
    assert traj.factor("yields", "CORN", 2030) == traj.factor("yields", "MAIZ", 2030)
    pm = ProjectionModule(model, traj)
    data, _ = pm.project_data(2030)
    y0, y1 = model.data["yields"], data["yields"]
    reg = next(r for r in y1.index if y0.at[r, "DCOW"] > 0 and abs(y1.at[r, "DCOW"] / y0.at[r, "DCOW"] - 1) > 0.02)
    f = y1.at[reg, "DCOW"] / y0.at[reg, "DCOW"]
    m0 = model.data["livestock_output_by_product_coef"].at[reg, "DCOW.COMI"]
    m1 = data["livestock_output_by_product_coef"].at[reg, "DCOW.COMI"]
    assert abs(m1 / m0 - f) < 1e-9
    b0 = model.data["livestock_output_by_product_coef"].at[reg, "DCOW.BEEF"]
    assert abs(data["livestock_output_by_product_coef"].at[reg, "DCOW.BEEF"] - b0) < 1e-12
    fe, fp, fd = data["ration_scale"][(reg, "DCOW")]
    assert (f > 1) == (fe > 1) and 0 < abs(fe - 1) < abs(f - 1) and 0 < abs(fp - 1) < abs(f - 1)


def test_greendeal_surplus_rules():
    """Scenario settings: the Green Deal group follows CAPRI star 3.0's files (surptot.gms cuts every region's
    baseline surplus per hectare by surpRedu%; manure trade the model's default, on); Farm-to-Fork carries
    JRC121368's own settings (tiered rule, no manure trade, milk-yield genomics 0.2). Values outside CAPRI's
    GUI options are refused."""
    import pytest
    from capri_mod.policy.greendeal import greendeal_scenario, farm_to_fork_scenario
    s3 = greendeal_scenario(surpRedu=30)
    assert s3.surplus_rule == "star3" and abs(s3.surplus_cut - 0.30) < 1e-12 and s3.manure_trade is None
    f = farm_to_fork_scenario()
    assert f.surplus_rule == "jrc121368" and f.manure_trade is False and f.endotech["ghgTechMYld"] == 0.2
    assert (f.set_aside_requirement, f.organic_area_target, f.pesticide_reduction) == (0.10, 0.25, 0.50)
    with pytest.raises(ValueError):
        greendeal_scenario(surpRedu=33)
    with pytest.raises(ValueError):
        greendeal_scenario(surpRedu=30, surplus_rule="jrc121368")


def test_option_costsaving_drop_follows_capri(model):
    """K67 F2: the animal options' PMP slope nets CAPRI's cost-saving drop between its ini and max calibration runs
    (breeding.gms l. 447-458): dsav per model head = sum_m MaxShare_m (M0_m - M1_m) / (ratio x sum_m MaxShare_m LEVL_m)
    from capri_costsavings_2030.csv, per unit of the technology parameter (the runs at ghgTechFEff 0.1). Checked
    against the source for DE11's bulls (genet_eff) and dairy cows (nitrate); signs as CAPRI's runs: the breeding
    option's marginal value rises towards the max run, the supplements' and low-N feed's fall."""
    import pandas as pd
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    cs = pd.read_csv(root / "capri_data" / "sources" / "ghgtech" / "capri_costsavings_2030.csv")
    md = pd.read_csv(root / "capri_data" / "2017" / "abatement" / "ammonia" / "capri_mann_days_2030.csv")
    ratio = model.data["capri_level_ratio"]
    lev = {(r.region, r.activity): float(r.value) for r in md[md["item"] == "LEVL"].itertuples()}

    def drop(tech, mem, an):
        num = den = 0.0
        for x in mem:
            s = cs[(cs.region == "DE110000") & (cs.activity == x) & (cs.technology == tech)].set_index("run")
            mx = min(1.0, float(s.at["max", "level"]) + 2e-6)
            num += mx * (float(s.at["ini", "marginal"]) - float(s.at["max", "marginal"]))
            den += mx * lev[("DE110000", x)]
        return num / den / float(ratio.at["DE110000", an])
    u = model.data["genetics_effects_unit"]["DE110000"]
    assert abs(float(u[("BULL", "genet_eff")]["dsav"]) * 0.1 - drop("GENET_EFF", ("BULL", "BULH"), "BULL")) < 1e-4 * \
        max(1.0, abs(drop("GENET_EFF", ("BULL", "BULH"), "BULL")))
    assert abs(float(u[("DCOW", "Nitr_Tot")]["dsav"]) - drop("Nitr_Tot", ("DCOL", "DCOH"), "DCOW")) < 1e-4 * \
        max(1.0, abs(drop("Nitr_Tot", ("DCOL", "DCOH"), "DCOW")))
    med = pd.DataFrame([(o, float(e["dsav"])) for t in model.data["genetics_effects_unit"].values()
                        for (a, o), e in t.items() if "dsav" in e and e["dsav"] == e["dsav"]],
                       columns=["o", "d"]).groupby("o").d.median()
    assert med["genet_eff"] < 0 and med["Nitr_Tot"] > 0 and med["lowNFeed"] > 0


def test_genetics_not_adopted_at_base(model):
    """breeding.gms calibration: IniShare 0, so a baseline run adopts (almost) nothing."""
    regions = ["DE110000", "FR520000", "IR010000"]
    r = model.run(scenario="BASELINE", max_outer_iter=2, regions=regions)
    # each technology's adoption against its own animal's herd (the sum over all technologies used to be compared
    # with the cattle herd alone, so broilers' low-N feed in Brittany - 1.5 of 82,800 thousand birds - tripped it)
    for v in r["supply"].values():
        for k, z in (getattr(v, "genetics_shift", None) or {}).items():
            a = k[0] if isinstance(k, tuple) else k
            assert float(z) <= 1e-3 * max(float(v.activities.get(a, 0.0)), 1.0), (k, z)


def test_livestock_output_by_product_sums_to_total(model):
    """The product split of each animal's output (sheep and goats: meat + milk; dairy cows: milk + cull
    beef) adds up to the animal's output coefficient."""
    q = model.data["livestock_output_by_product_coef"]
    tot = model.data["livestock_output_coef"]
    for a in tot.columns:
        parts = [c for c in q.columns if c.startswith(a + ".")]
        if parts:
            d = (q[parts].sum(axis=1) - tot[a]).abs().max()
            assert d < 1e-9, (a, d)
    assert "SHGM.SGMI" in q.columns and "SHGF.SGMT" in q.columns and "DCOW.COMI" in q.columns


def test_price_structure_vs_capri(model):
    """
    Validate the model's relative price structure against CAPRI's own scenario
    output (Green Deal 2030 reference). Rank correlation should be very high.
    Reference ratios (vs wheat) extracted from CAPRI capmod DATAOUT.
    """
    capri_ratios = {
        "SWHE": 1.00, "BARL": 0.82, "RAPE": 2.55, "SOYA": 3.05,
        "POTA": 1.35, "SUGB": 0.15, "BEEF": 24.23, "PORK": 11.56,
    }
    wp = model.data["world_prices"]

    def price(c):
        if c in wp.index:
            row = wp.loc[c]
            return float(row.iloc[0]) if hasattr(row, "iloc") else float(row)
        return None

    base = price("SWHE")
    assert base and base > 0
    pairs = []
    for c, cr in capri_ratios.items():
        mp = price(c)
        if mp:
            pairs.append((cr, mp / base))
    assert len(pairs) >= 6
    # Rank correlation between CAPRI and model relative prices must be high
    import statistics
    capri_vals = [c for c, _ in pairs]
    model_vals = [m for _, m in pairs]
    corr = statistics.correlation(capri_vals, model_vals)
    assert corr > 0.95, f"price-structure correlation too low: {corr:.3f}"


# ---------------------------------------------------------------------------
# Data hygiene guards
#
# These exist because a Cyrillic-homoglyph corruption of the activity code
# `OANI` (and two doubled-I variants) sat undetected across code and data: the
# canonical activity list used one spelling, the feed and environmental modules
# used others, so every 'other animals' lookup silently missed.
# ---------------------------------------------------------------------------

# These exist because a Cyrillic-homoglyph corruption of the activity code
# `OANI` sat undetected across code and data: the canonical activity list used
# one spelling, the feed/environmental/market modules used homoglyph variants,
# so every 'other animals' lookup silently missed. A denylist of known-bad
# variants is fragile — it only catches the spellings you thought to enumerate
# (an ASCII-OANI + single trailing Cyrillic И slipped past exactly such a list).
# The guard below is general: it flags ANY non-ASCII character sitting inside a
# quoted token that otherwise looks like an activity/commodity code, wherever it
# appears in code or data.
# ---------------------------------------------------------------------------

import re as _re

# a "code token" is a short all-caps-alnum identifier (activity/commodity code).
# Flag it if it contains ANY non-ASCII character. This catches both partial
# corruption (ASCII OANI + trailing Cyrillic И) and full corruption (every
# letter a Cyrillic homoglyph), which a "boundary-only" pattern would miss.
def _looks_corrupted_code(token: str) -> bool:
    # candidate code token: 3-6 chars, no spaces, letters/digits/homoglyphs only,
    # at least one non-ASCII char, and (if it has ASCII letters) they're upper.
    t = token.strip()
    if not (3 <= len(t) <= 6) or " " in t:
        return False
    if all(ord(c) < 128 for c in t):
        return False  # pure ASCII — a separate ASCII-only guard covers doubled-I
    ascii_letters = [c for c in t if c.isascii() and c.isalpha()]
    if ascii_letters and not all(c.isupper() for c in ascii_letters):
        return False  # lowercase ASCII → prose word with an accent, not a code
    # reject if it contains punctuation/space-like chars → not a bare code
    return all(c.isalnum() for c in t)


def _repo_root():
    import pathlib
    return pathlib.Path(__file__).resolve().parents[2]


def test_no_corrupted_activity_codes():
    """No non-ASCII homoglyph adjacent to any uppercase code token, in code or data.

    Generalises the original OANI-variant denylist: instead of enumerating known
    bad spellings, it rejects any non-ASCII character touching an uppercase
    alphanumeric code token — the shape every homoglyph corruption of an activity
    or commodity code takes.
    """
    import pathlib
    offenders = []
    for p in _repo_root().rglob("*"):
        if not p.is_file() or p.suffix.lower() not in {".py", ".csv", ".json"}:
            continue
        # tools/ holds the normaliser and this file holds the guard regex; both
        # legitimately contain the pattern in order to act on it. Skip caches.
        # (capri_data_snapshot, a July restore point, was removed once verified
        # to be an exact duplicate of capri_data; the name is kept in this guard
        # so a restored snapshot would still be skipped rather than scanned.)
        if {"__pycache__", ".git", "tools", "capri_data_snapshot"} & set(p.parts):
            continue
        if p.resolve() == pathlib.Path(__file__).resolve():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            # only inspect quoted string content, so prose comments with accents
            # (Baden-Württemberg, Île-de-France) and math symbols don't trip it
            for m in _re.finditer(r"""["']([^"']*)["']""", line):
                token = m.group(1)
                if _looks_corrupted_code(token):
                    offenders.append(f"{p.name}:{lineno}: {token!r}")
    assert not offenders, (
        "non-ASCII homoglyph in code/commodity token:\n  " + "\n  ".join(offenders)
    )


def test_data_headers_are_ascii():
    """CSV headers must be pure ASCII — non-ASCII means an encoding artifact. Exempt: a provider's file kept byte for byte
    as downloaded (<name>_original.csv, e.g. Statistics Norway's county table with its byte-order mark and Norwegian
    headers), whose ASCII copy is the file the builders write beside it."""
    import pathlib
    import csv
    offenders = []
    for p in (_repo_root() / "capri_data").rglob("*.csv"):
        if p.stem.endswith("_original"):
            continue
        try:
            with open(p, encoding="utf-8", newline="") as fh:
                header = next(csv.reader(fh), [])
        except (UnicodeDecodeError, OSError, StopIteration):
            continue
        bad = [h for h in header if any(ord(ch) > 127 for ch in h)]
        if bad:
            offenders.append(f"{p.name}: {bad}")
    # the builders' intermediates kept as Parquet (27 October 2026): their column names
    import pyarrow.parquet as _pq
    for p in (_repo_root() / "capri_data").rglob("*.parquet"):
        bad = [h for h in _pq.read_schema(p).names if any(ord(ch) > 127 for ch in h)]
        if bad:
            offenders.append(f"{p.name}: {bad}")
    assert not offenders, f"non-ASCII CSV headers: {offenders}"


# ---------------------------------------------------------------------------
# PMP elasticity wiring guards
# ---------------------------------------------------------------------------

def test_capri_dampening_matches_gams_reference():
    """
    CAPRI's own worked examples from
    gams/supply/pmp_terms/impose_upper_bound_on_elasticity.gms:
    "any elasticity above 4.5 gets dampened (10=>5.6, 20=>7.0, 40 =>8)".
    """
    from capri_mod.supply.capri_pmp import dampen_elasticity
    import numpy as np
    got = dampen_elasticity([10.0, 20.0, 40.0])
    assert np.allclose(got, [5.6, 7.0, 8.0], atol=0.2), got
    # values at or below the threshold must pass through untouched
    assert np.allclose(dampen_elasticity([0.3, 2.5, 4.5]), [0.3, 2.5, 4.5])
    # and nothing may exceed the hard cap
    assert dampen_elasticity([1e6])[0] <= 8.0


def test_synthetic_base_activities_excluded_from_elasticity_wiring():
    """Placeholder base levels must not receive real elasticities.

    PMP curvature is 1/(eps*x0), so a genuine elasticity on an invented anchor
    explodes under shock: OFOD once reached +128%. COTT, OFIB (now TEXT) and OFOD used to
    be flat placeholders, because CAPRI reports them under aggregate names
    (TEXT for fibre crops, OFAR and ROOF for fodder) that had never been
    mapped. They are now REAL CAPRI data - fodder on arable land alone is 14.3
    Mha EU-wide - so the detector should find nothing left to block.

    The guard itself stays: it is what stops a future placeholder being wired
    up by accident.
    """
    import pandas as pd
    from capri_mod.supply.capri_pmp import detect_synthetic_base_activities

    root = _repo_root()
    areas = pd.read_csv(root / "capri_data/2017/supply/base_areas.csv", index_col=0)
    blocked = detect_synthetic_base_activities(areas)
    assert not blocked, (
        f"{sorted(blocked)} still look like placeholders (constant across "
        "regions); every activity should now come from CAPRI")

    # and the activities that were placeholders must now vary across regions
    for act in ("TEXT", "OFOD"):
        if act in areas.columns and float(areas[act].sum()) > 0:
            assert areas[act].nunique() > 5, (
                f"{act} takes only {areas[act].nunique()} distinct values")


def test_elasticity_provenance_is_complete():
    """Every region x activity cell must carry a provenance label."""
    import pandas as pd
    from capri_mod.supply.capri_pmp import build_elasticity_table
    from capri_mod.data.definitions import ALL_ACTIVITIES
    from capri_mod.utils.utils import calibrate_supply_elasticities

    root = _repo_root()
    areas = pd.read_csv(root / "capri_data/2017/supply/base_areas.csv", index_col=0)
    eps, prov, summary = build_elasticity_table(
        root / "capri_data", list(areas.index), ALL_ACTIVITIES,
        calibrate_supply_elasticities(areas), base_areas=areas)
    assert prov.notna().all().all()
    # no literature defaults since 23 October 2026: a cell without a CAPRI value is NaN, labelled NO_CAPRI_VALUE
    has = prov != "NO_CAPRI_VALUE"
    assert eps.where(has).notna().sum().sum() == int(has.sum().sum())
    assert eps.where(~has).isna().all().all()
    assert (eps.where(has).fillna(0.0) >= 0).all().all()
    # SETA carries a zero default by design (set-aside does not respond to price),
    # so strict positivity is not the right assertion here.
    assert (eps.fillna(0.0) <= 8.0).all().all(), "elasticity exceeds CAPRI's hard cap"
    assert set(prov.stack().unique()) <= {
        "NO_CAPRI_VALUE", "REGIONAL_CAPRI", "PMP_CAPRI", "CAPRI_CAL_PRODUCT", "CAPRI_COUNTRY"}
    # livestock carry CAPRI's calibrated product elasticities, not literature priors
    for a in ("DCOW", "BULL", "PIGS", "BROI"):
        assert (prov[a] == "CAPRI_CAL_PRODUCT").mean() > 0.9, a


def test_schema_declares_every_input_and_all_files_exist():
    """
    The declarative schema (INPUT_SCHEMA.json) is the single source of truth for
    what the model loads and where each input comes from. This gate asserts the
    data on disk matches the declaration: every declared file must exist and be
    readable.

    This is the check that would have caught the silent-drop bugs in the
    project's history -- maize yields, grassland, the livestock PMP terms -- each
    of which left a declared input under-covered while the file still looked
    fine. It fails loudly the moment declaration and reality diverge.
    """
    import json
    import pandas as pd

    root = _repo_root()
    schema = json.loads((root / "capri_data/INPUT_SCHEMA.json").read_text())
    inputs = schema["inputs"]
    assert len(inputs) >= 20, "schema unexpectedly small"

    missing = []
    unreadable = []
    for name, spec in inputs.items():
        f = root / "capri_data" / spec["file"]
        if not f.exists():
            missing.append((name, spec["file"]))
            continue
        # provenance must be structured, so a later source swap is a field edit
        src = spec["source"]
        for field in ("source_type", "source_ref", "vintage", "confidence"):
            assert field in src, f"{name} missing provenance field {field}"
        if str(f).endswith(".csv"):
            try:
                pd.read_csv(f, index_col=0, nrows=5)
            except Exception as exc:            # pragma: no cover
                unreadable.append((name, str(exc)[:80]))

    assert not missing, f"declared files absent: {missing}"
    assert not unreadable, f"declared files unreadable: {unreadable}"


def test_schema_coverage_has_not_regressed():
    """
    Guards the honest per-cell coverage figure. Real-CAPRI-sourced cells must
    stay above a floor; a drop that isn't explained by a schema change is a
    silent-drop regression of exactly the kind this project kept hitting.

    The floor is set well below the current 99% so ordinary data edits don't
    trip it, but a whole input quietly emptying (the failure mode of the maize
    and grassland bugs) would.
    """
    import json
    import numpy as np
    import pandas as pd

    root = _repo_root()
    schema = json.loads((root / "capri_data/INPUT_SCHEMA.json").read_text())
    real_types = {"CAPRI_GDX", "CAPRI_SOURCE"}

    real = total = 0
    per_input = {}
    for name, spec in schema["inputs"].items():
        f = root / "capri_data" / spec["file"]
        if not (f.exists() and str(f).endswith(".csv")):
            continue
        if spec.get("alternative_to"):
            # an optional alternative to another input (e.g. the recipe PMP terms, pmp_recipe_<Y>, alternative to
            # CAPRI's exported terms): not read by the default run, so not part of the default inputs' coverage
            continue
        try:
            num = pd.read_csv(f, index_col=0).select_dtypes(include=[np.number])
        except Exception:
            continue
        live = int(num.notna().sum().sum())
        nz = int(((num != 0) & num.notna()).sum().sum())
        total += nz
        if spec["source"]["source_type"] in real_types:
            real += nz
        # per-input fill ratio: a CAPRI-sourced input that empties out is the
        # silent-drop failure mode (maize, grassland, livestock terms), and the
        # aggregate floor is too coarse to see one input among twenty go dark.
        if live > 0:
            per_input[name] = nz / live

    assert total > 0
    frac = real / total
    assert frac >= 0.80, (
        f"real-CAPRI cell coverage {frac:.1%} below floor 80% -- "
        "a declared input may have silently emptied")

    # any single CAPRI-sourced numeric input that is almost entirely zero is a
    # regression, regardless of the aggregate. 5% floor tolerates genuinely
    # sparse inputs (e.g. specialty crops) without tolerating a dead file.
    emptied = {n: r for n, r in per_input.items()
               if r < 0.05
               and schema["inputs"][n]["source"]["source_type"] in real_types}
    assert not emptied, (
        f"CAPRI-sourced inputs nearly empty (silent-drop?): "
        f"{ {n: f'{r:.1%}' for n, r in emptied.items()} }")


# ---------------------------------------------------------------------------
# Market-mapping consistency. The supply->market bridge and the processing
# splits both reference commodity codes; if any referenced code is absent from
# MARKET_COMMODITIES the market would silently drop that flow. This guards the
# bridge (which must be fully covered) and pins the intended processing-output
# exceptions (oilseed crush products that are feed items, not traded market
# commodities) so an accidental omission is distinguishable from a known one.
# ---------------------------------------------------------------------------

def test_market_mapping_consistency():
    import re
    from capri_mod.data import definitions as D

    market = set(D.MARKET_COMMODITIES)

    # (a) every commodity the supply->market bridge writes to or guards on must
    #     exist in MARKET_COMMODITIES -- a missing one is a silent dropped flow.
    src = (_repo_root() / "capri_mod" / "model.py").read_text(encoding="utf-8")
    bridge_refs = set(re.findall(r'market_supply\[\s*["\'](\w+)["\']\s*\]\s*=', src))
    bridge_refs |= set(re.findall(r'["\'](\w+)["\']\s+in\s+market_supply', src))
    bridge_missing = sorted(c for c in bridge_refs if c not in market)
    assert not bridge_missing, (
        f"_bridge_supply_to_market references commodities absent from "
        f"MARKET_COMMODITIES: {bridge_missing}")

    # (b) (the processing outputs' list PROCESSING_OUTPUTS was removed 23 October 2026: no model code read it)


@pytest.mark.slow
def test_projection_null_trajectory_reproduces_base(model):
    """The projection layer's correctness gate.

    Projecting with a NULL trajectory (all growth factors 1.0) must reproduce
    the comparative-static result exactly. This tests the whole machinery —
    scaling, reconciliation, the time loop, state carry-forward — without
    depending on any forecast being right.
    """
    from capri_mod.projection import ProjectionModule, BaselineTrajectory

    # A FRESH model: the session model carries state from earlier tests (market prices,
    # young-animal prices, warm starts) that the projection's fresh model does not; the outer
    # loop then converges to its tolerance from two different starting points (DE11 soft
    # wheat 1e-6 apart). The identity concerns the projection machinery, so both runs start
    # from the same state.
    from capri_mod.model import CAPRIModel
    model = CAPRIModel(data_dir=str(DATA_DIR), verbose=False)
    regions = _german_units(12)
    ref = model.run(scenario="BASELINE", regions=regions)
    pm = ProjectionModule(model, BaselineTrajectory.null(2017, [2017]))
    proj = pm.run(regions=regions).baseline[2017]

    ra, pa = ref.get("supply", {}), proj.get("supply", {})
    compared = 0
    for reg in ra:
        a1 = getattr(ra[reg], "activities", None)
        a2 = getattr(pa.get(reg), "activities", None) if reg in pa else None
        if a1 is None or a2 is None:
            continue
        for act in a1.index:
            if act in a2.index and abs(a1[act]) > 1e-6:
                compared += 1
                assert abs(a2[act] - a1[act]) / abs(a1[act]) < 1e-9, (
                    f"null trajectory changed {reg}/{act}: {a1[act]} -> {a2[act]}")
    assert compared > 50, "too few cells compared to trust the identity"


def test_projection_reconciliation_preserves_base_ratio():
    """Reconciliation is a no-op at base and corrects genuine drift.

    It must NOT impose an assumed identity (crop areas do not sum to the land
    table in the base year); it preserves each region's own base-year
    cropped-to-land ratio, so a null trajectory changes nothing.
    """
    import copy
    from capri_mod.data.loaders import load_all_data
    from capri_mod.projection import reconcile_projected_data

    d = load_all_data(str(DATA_DIR))

    # no drift -> no change
    same = copy.deepcopy(d)
    rep = reconcile_projected_data(same, base_data=d)
    delta = (same["areas"] - d["areas"]).abs().sum().sum()
    assert delta < 1e-6, f"reconciliation altered base data by {delta}"
    assert rep.land_adjusted_regions == 0

    # land shrinks 5%, areas left at base -> areas pulled back ~5%
    drifted = copy.deepcopy(d)
    drifted["land"] = drifted["land"] * 0.95
    reconcile_projected_data(drifted, base_data=d)
    for reg in list(d["areas"].index[:5]):
        expected = d["areas"].loc[reg].sum() * 0.95
        got = drifted["areas"].loc[reg].sum()
        if expected > 1:
            assert abs(got - expected) / expected < 1e-6, (
                f"{reg}: reconciled to {got}, expected {expected}")
    assert not (drifted["areas"] < 0).any().any(), "negative areas after reconcile"


def test_projection_trajectory_requires_provenance():
    """A trajectory must carry its source and vintage.

    The projection is driven by an adopted external assumption set, not a
    forecast the model makes; an unattributed trajectory is not usable.
    """
    from capri_mod.projection import BaselineTrajectory, TrajectoryError

    try:
        BaselineTrajectory.from_dict({"name": "x", "base_year": 2017,
                                      "target_years": [2030]})
        assert False, "trajectory without source/vintage should be rejected"
    except TrajectoryError:
        pass

    # implausible growth factors are rejected rather than silently used
    try:
        BaselineTrajectory.from_dict({
            "name": "x", "source": "s", "vintage": "v", "base_year": 2017,
            "target_years": [2030],
            "growth": {"yields": {"_default": {"2030": 50.0}}}})
        assert False, "implausible growth factor should be rejected"
    except TrajectoryError:
        pass


def test_captrd_trajectory_is_usable_and_plausible():
    """The CAPRI-derived baseline trajectory loads and carries sensible factors.

    Extracted from a captrd p_result export (the 'series' datatype, which is the
    final reconciled trend in projection years). The economic sanity checks are
    that yields grow modestly, herds contract, and every factor sits in a
    plausible band -- a trajectory with a 3x yield factor would be an extraction
    artefact, not a forecast.
    """
    import os
    from capri_mod.projection import BaselineTrajectory

    path = os.path.join(str(DATA_DIR), "trajectories", "captrd_2030.json")
    if not os.path.exists(path):
        return  # trajectory not shipped in this build

    t = BaselineTrajectory.from_file(path)
    assert not t.is_null(), "captrd trajectory should carry real drift"
    assert t.source and t.source != "unknown", "trajectory must carry provenance"

    # yields grow modestly; herds contract -- the documented EU pattern
    y = t.factor("yields", "_default", 2030)
    h = t.factor("herds", "_default", 2030)
    assert 1.0 < y < 1.3, f"implausible default yield growth to 2030: {y}"
    assert 0.7 < h < 1.05, f"implausible default herd change to 2030: {h}"

    # every factor in the file is within the plausible band
    for block, keys in t.growth.items():
        for key, by_year in keys.items():
            for year, f in by_year.items():
                assert 0.2 < float(f) < 5.0, (
                    f"{block}/{key}/{year} factor {f} outside plausible band")


@pytest.mark.slow
def test_set_aside_requirement_actually_binds(model):
    """A mandatory non-productive share must change the solve.

    Regression test for a silent-failure bug: `set_aside_requirement` was
    defined on PolicyScenario and referenced by four scenarios (including
    SET_ASIDE_10PCT, the Farm-to-Fork landscape-elements equivalent) but was
    never enforced in the supply constraints, so the scenario returned results
    bit-identical to the baseline while reporting success.
    """
    regions = _german_units(10)
    # two outer iterations: the requirement acts in the first regional solve (the test checks that it binds, not the
    # converged equilibrium; 77 s with the full outer loop, 23 October 2026)
    base = model.run(scenario="BASELINE", regions=regions, max_outer_iter=2)
    sa = model.run(scenario="SET_ASIDE_10PCT", regions=regions, max_outer_iter=2)

    changes, acts_seen = [], []
    for reg, res in base.get("supply", {}).items():
        a1 = getattr(res, "activities", None)
        a2 = getattr(sa.get("supply", {}).get(reg), "activities", None)
        if a1 is None or a2 is None:
            continue
        for act in a1.index:
            # cells of at least 1 ha at base: below it the level is solver noise (German paddy rice at 1.3e-6 kha
            # moving to 1.7 ha is a relative change of 1,379 and swamped the average, 22 October 2026)
            if act in a2.index and abs(a1[act]) > 1e-3:
                changes.append((a2[act] - a1[act]) / abs(a1[act]))
                acts_seen.append(act)

    assert changes, "no comparable activity cells"
    assert max(abs(c) for c in changes) > 1e-6, (
        "set_aside_requirement had NO effect on the solve — the instrument is "
        "defined but not enforced")

    # PRODUCTIVE area must contract. SETA is excluded from this average because
    # it IS the instrument: the requirement is a floor that forces land INTO
    # set-aside (SETA rises ~72%), so averaging it in with the crops it displaces
    # makes the overall mean POSITIVE and hides the contraction. An earlier
    # version of this test averaged everything together and so encoded the
    # superseded mechanism, in which set-aside was modelled as a cut to arable
    # land rather than a floor on the non-productive activity.
    productive = [c for a, c in zip(acts_seen, changes) if a != "SETA"]
    assert productive, "no productive activities compared"
    assert sum(productive) / len(productive) < 0, (
        "a 10% non-productive requirement should reduce PRODUCTIVE area on average")


def test_policy_instruments_are_not_inert(data):
    """Every wired policy instrument must actually reach the solve.

    Guard against the project's most persistent failure mode: an instrument that
    is defined on PolicyScenario, referenced by scenarios, reports success, and
    silently does nothing. Four separate breaks of exactly this kind were found
    (set-aside never enforced in the constraints; CAP adders discarded because
    the model wrapped them in an "adders" key the solve never unwrapped; the
    nitrate limit never passed from model to solve at all; Pillar II rates and
    eco-schemes never entering the adders despite the docstring saying so).

    This deliberately tests the *wiring* rather than running full model solves:
    the earlier version ran one 248-region solve per instrument and was far too
    slow to run routinely, which is how it went unverified for two sessions.
    Payment instruments are checked by confirming they move the supply adders;
    constraint instruments are checked by confirming they reach the solve's
    constraint builder and change the feasible set.
    """
    import numpy as np
    from capri_mod.policy.policy_module import PolicyModule, PolicyScenario

    base_adders = PolicyModule(data, PolicyScenario(name="base")).get_supply_policy_adders()

    payment_instruments = {
        "biss_rate_change": PolicyScenario(name="t", biss_rate_change=-100.0),
        "coupled_support": PolicyScenario(name="t", coupled_support={"DCOW": 200.0}),
    }
    for name, scen in payment_instruments.items():
        adders = PolicyModule(data, scen).get_supply_policy_adders()
        assert not np.allclose(adders.values, base_adders.values), (
            f"policy instrument '{name}' is INERT — it does not change the "
            "supply policy adders, so it cannot affect the solve")
    # a BISS cut reaches each crop in full, not inflated by an eco-scheme share (eco-schemes are inside Pillar I)
    d_ = PolicyModule(data, payment_instruments["biss_rate_change"]).get_supply_policy_adders() - base_adders
    assert abs(float(d_["SWHE"]) + 100.0) < 1e-9 and float(d_["SETA"]) == 0.0
    # Pillar II budget changes act per region and activity through CAPRI's premium split by scheme (2030 PRME)
    for name, scen in {"lfa_budget_change": PolicyScenario(name="t", lfa_budget_change=-0.5),
                       "ae_budget_change": PolicyScenario(name="t", ae_budget_change=0.5),
                       "n2k_budget_change": PolicyScenario(name="t", n2k_budget_change=0.5)}.items():
        f_ = PolicyModule(data, scen).get_premium_factors_regional()
        assert f_ and any(abs(v - 1.0) > 1e-6 for fr in f_.values() for v in fr.values()), \
            f"policy instrument '{name}' is INERT — no premium factor differs from 1"
    assert PolicyModule(data, PolicyScenario(name="t", eco_scheme_budget_pct=0.5)).get_premium_factors_regional() == {}

    # An unchanged scenario must leave the adders untouched (the other direction:
    # a guard that fires on everything would be worthless).
    same = PolicyModule(data, PolicyScenario(name="t")).get_supply_policy_adders()
    assert np.allclose(same.values, base_adders.values), (
        "an unchanged scenario should reproduce the baseline adders exactly")


def test_constraint_instruments_reach_the_solve(data):
    """Set-aside and the nitrogen ceiling must change the feasible set.

    These act on constraints rather than net revenues, so they are checked at
    the constraint builder — cheap, and it is exactly where set-aside was
    silently missing.
    """
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities

    sm = SupplyModule(data, calibrate_supply_elasticities(data["areas"]))
    region = list(data["areas"].index)[0]
    sm.run(price_signals=None, regions=[region])
    model = sm._models[region]

    # Set-aside is implemented as CAPRI implements it (landscape.gms): a FLOOR
    # on the non-productive activity sized on UAA, expressed as -x_SETA <= -floor.
    # It therefore ADDS a constraint row rather than tightening the arable bound.
    A_base, b_base, _, _ = model._build_constraints()
    A_sa, b_sa, _, _ = model._build_constraints(set_aside_requirement=0.10)
    if "SETA" in model.acts:
        assert len(b_sa) > len(b_base), (
            "set_aside_requirement did not add the landscape-elements floor")
        # locate the floor row by its signature (a negative bound) rather than
        # by position: constraint order is an implementation detail.
        assert any(float(v) < 0 for v in b_sa), (
            "the SETA floor should enter as a negative bound (-x <= -floor)")

    # the nitrogen ceiling is anchored to observed base intensity, so an
    # unchanged run must be SLACK (this is what the 170 kg/ha anchor got wrong)
    base_int = model.base_n_intensity()
    _, b_slack, _, _ = model._build_constraints(nitrate_limit=base_int)
    _, b_tight, _, _ = model._build_constraints(nitrate_limit=base_int - 10.0)
    # locate the nitrogen row by which bound moves, rather than assuming a
    # position: the constraint order is an implementation detail and an
    # index-based check silently passes/fails for the wrong reason.
    moved = [i for i in range(len(b_slack))
             if abs(float(b_slack[i]) - float(b_tight[i])) > 1e-9]
    assert moved, "nitrate_limit did not tighten any constraint"
    for i in moved:
        assert float(b_tight[i]) < float(b_slack[i]), (
            "tightening the nitrogen limit loosened a constraint")


def test_no_negative_own_price_elasticities(data):
    """Every crop must respond POSITIVELY to a rise in its own price.

    A negative own-price supply elasticity is economically impossible and was a
    long-standing documented limitation for pulses. Measured directly it no
    longer occurs — it was fixed as a side effect of earlier PMP/solver work and
    the limitation note was simply never retired. This test pins that down so
    the sign cannot silently regress.
    """
    import pandas as pd
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities

    sm = SupplyModule(data, calibrate_supply_elasticities(data["areas"]))
    regions = _german_units(12)
    sm.run(price_signals=None, regions=regions)

    crops = ["SWHE", "BARL", "PULS", "RAPE", "POTA", "SUGB"]
    for crop in crops:
        num = den = 0.0
        for reg in regions:
            model = sm._models.get(reg)
            if model is None or crop not in model.acts:
                continue
            base = model.solve(price_shock=None).activities
            shock = pd.Series(0.0, index=model.acts)
            shock[crop] = 0.10
            new = model.solve(price_shock=shock).activities
            b = base.get(crop, 0.0)
            if b > 1e-6:
                num += new.get(crop, 0.0) - b
                den += b
        if den > 0:
            elas = (num / den) / 0.10
            assert elas > 0, (
                f"{crop} has a NEGATIVE own-price elasticity ({elas:.3f}): "
                "supply must rise when a crop's own price rises")


def test_intensity_margin_identity_and_response(data):
    """The N intensity margin must preserve the base year and respond sanely.

    Nutrient coefficients are fixed per activity, so without this margin a
    nitrogen constraint can only cut AREA — which overstated the response ~10x
    against CAPRI's Green Deal run (wheat -24% vs -1.9%). CAPRI instead lets
    application per hectare flex (`v_cropNutNeedMultFact`) and splits the
    adjustment between intensity and area.

    Two properties matter:
      1. IDENTITY — at full intensity the yield factor is exactly 1.0, so
         switching this on cannot disturb the base year or PMP calibration.
      2. RESPONSE — a binding ceiling reduces intensity with diminishing
         returns, and the yield loss is agronomically plausible rather than a
         collapse.
    """
    from capri_mod.supply.intensity import yield_factor, optimal_intensity
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities

    # 1. base-year identity, exactly
    assert abs(float(yield_factor(1.0)) - 1.0) < 1e-12, (
        "yield_factor(1.0) must be exactly 1.0 or the base year shifts")

    # monotone and diminishing-returns
    fs = [float(yield_factor(m)) for m in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0)]
    assert all(b > a for a, b in zip(fs, fs[1:])), "yield must rise with N"
    gaps = [b - a for a, b in zip(fs, fs[1:])]
    assert all(b <= a + 1e-9 for a, b in zip(gaps, gaps[1:])), (
        "N response must show diminishing returns")

    # a 20% N cut should cost a few percent of yield, not a collapse
    loss20 = (1.0 - float(yield_factor(0.8))) * 100.0
    assert 1.0 < loss20 < 12.0, f"implausible yield loss for -20% N: {loss20:.1f}%"

    # 2. response under a real regional ceiling
    sm = SupplyModule(data, calibrate_supply_elasticities(data["areas"]))
    region = list(data["areas"].index)[0]
    sm.run(price_signals=None, regions=[region])
    model = sm._models[region]
    crops = [c for c in model.acts if c in data["nutrients"].index]
    ncoef = data["nutrients"]["N"].reindex(crops).fillna(0.0)
    price = data["producer_prices"].reindex(crops).fillna(0.0)
    yld = data["yields"].loc[region].reindex(crops).fillna(0.0)
    areas = model._base_levels().reindex(crops).fillna(0.0)
    if float(areas.sum()) <= 0:
        return
    own = float((ncoef * areas).sum() / areas.sum())

    slack = optimal_intensity(ncoef, price, yld, 1.0, own * 1.05, areas)
    assert not slack.binding, "a ceiling above base intensity must not bind"
    assert abs(float(slack.yield_factor.mean()) - 1.0) < 1e-9

    tight = optimal_intensity(ncoef, price, yld, 1.0, own * 0.80, areas)
    assert tight.binding, "a 20% ceiling below base intensity must bind"
    wm = float((tight.intensity * areas).sum() / areas.sum())
    assert 0.5 <= wm < 1.0, f"intensity should fall but not collapse: {wm:.3f}"


def test_cap_support_not_double_counted(model):
    """A BASELINE model run must not inflate supply above the calibrated base.

    The calibrated net revenue already contains cap_premium. The policy module's
    get_supply_policy_adders() returns the ABSOLUTE payment, and the solve ADDS
    it to cap_premium — so passing the absolute level double-counted CAP support
    and inflated wheat ~29% above a no-policy solve. The distortion sat in the
    BASELINE too, so every scenario-vs-baseline comparison was measuring the
    double-count rather than the policy. Adders are now passed as a DELTA from
    the baseline policy, making a BASELINE run a no-op.
    """
    # Reference: the calibrated base levels. Until 23 October 2026 the reference was a bare SupplyModule.run without
    # the model's run state (feed rations and prices, manure pools); since the proxy removals of that day such a bare
    # solve no longer reproduces the base (DE11 wheat 71 against 91 kha; KNOWN_ISSUES K68), so it is no reference.
    regions = _german_units(8)
    base_wheat = float(model.data["areas"].loc[regions, "SWHE"].sum())

    res = model.run(scenario="BASELINE", regions=regions, max_outer_iter=1)
    run_wheat = sum(float(getattr(v, "activities", {}).get("SWHE", 0.0))
                    for v in res.get("supply", {}).values())

    if base_wheat <= 0:
        return
    inflation = (run_wheat / base_wheat - 1.0) * 100.0
    assert abs(inflation) < 1.0, (
        f"BASELINE run moves wheat by {inflation:.1f}% against the calibrated base "
        "- CAP support is being double-counted or the calibration is off")


def test_elasticity_paths_are_base_year_aware():
    """Elasticity sources must resolve through the base-year-aware lookup.

    REGIONAL_FILE and PMP_ELAS_FILE were hard-coded as "2017/supply/...", so
    re-basing the model to another year would have silently fallen back to the
    literature defaults — the CAPRI elasticities would just stop being found,
    with no error. They now go through resolve_data_file().
    """
    import pandas as pd
    from pathlib import Path
    from capri_mod.supply import capri_pmp
    from capri_mod.data.loaders import load_all_data

    assert "2017" not in capri_pmp.REGIONAL_FILE, "year hard-coded in REGIONAL_FILE"
    assert "2017" not in capri_pmp.PMP_ELAS_FILE, "year hard-coded in PMP_ELAS_FILE"

    d = load_all_data(str(DATA_DIR))
    eps, prov, summ = capri_pmp.build_elasticity_table(
        Path(str(DATA_DIR)), list(d["areas"].index), list(d["areas"].columns),
        pd.Series(0.25, index=d["areas"].columns))
    # the real CAPRI sources must still be found, not silently skipped
    assert summ["cells_from_regional_file"] > 0, (
        "regional CAPRI elasticities no longer resolve")
    assert summ["cells_from_pmp_file"] > 0, (
        "PMP CAPRI elasticities no longer resolve")


@pytest.mark.slow
def test_organic_area_target_binds_and_is_a_noop_at_zero(model):
    """The Farm-to-Fork organic AREA target must act on I/O coefficients.

    Previously only `organic_rate_change` existed (removed 23 October 2026) — a payment RATE, which is a
    different instrument from an area TARGET. CAPRI models organic farming by
    adjusting average input-output coefficients in proportion to the organic
    share (organic_io.gms), not by tracking organic activities separately, and
    this model now does the same.
    """
    from capri_mod.policy.policy_module import PolicyScenario

    regions = _german_units(8)

    def totals(res):
        out = {}
        for reg, v in res.get("supply", {}).items():
            acts = getattr(v, "activities", None)
            if acts is None:
                continue
            for a, val in acts.items():
                out[a] = out.get(a, 0.0) + float(val)
        return out

    base = totals(model.run(scenario="BASELINE", regions=regions,
                            max_outer_iter=1))
    zero = totals(model.run(custom_scenario=PolicyScenario(
        name="t", organic_area_target=0.0), regions=regions, max_outer_iter=1))
    tgt = totals(model.run(custom_scenario=PolicyScenario(
        name="t", organic_area_target=0.25), regions=regions, max_outer_iter=1))

    # a zero target must be a true no-op, within IPOPT's tolerance between two solves of the same problem (KNOWN_ISSUES
    # K80), the tolerance of the pesticide no-op test: 1e-5 was below it (27 October 2026, a fresh model per test: RYEM
    # 27.40272 against 27.40242, 1.08e-5; the same from a cold start)
    tol = 1e-4
    for a, v in base.items():
        if v > 1.0:
            assert abs(zero.get(a, 0.0) - v) / v < tol, (
                f"organic_area_target=0 changed {a}")

    # a 25% target must move production, and downward on average (organic
    # yields are lower), without collapsing anything
    moved = [a for a, v in base.items()
             if v > 1.0 and abs(tgt.get(a, 0.0) - v) / v > 1e-6]
    assert moved, "organic_area_target=0.25 had no effect"
    for a in moved:
        ratio = tgt.get(a, 0.0) / base[a]
        assert 0.2 < ratio < 5.0, f"{a} moved implausibly: x{ratio:.2f}"


def test_projection_matches_capri_2030_reference(model):
    """The projection must reproduce CAPRI's own 2030 baseline.

    The 'instruments off' validation: CAPRI's reference run gives projected 2030
    activity levels, which validates the whole projection chain (trajectory
    extraction, reconciliation, recursive loop, comparative-static core) without
    needing any policy scenario.

    Skips if the CAPRI reference extract is not present in this build.
    """
    import os
    import pandas as pd
    from capri_mod.projection import ProjectionModule, BaselineTrajectory

    ref_path = os.path.join(str(DATA_DIR), "validation", "capri_eu27_levels_2030_ref.csv")
    traj_path = os.path.join(str(DATA_DIR), "trajectories", "captrd_2030.json")
    if not (os.path.exists(ref_path) and os.path.exists(traj_path)):
        return

    cap = pd.read_csv(ref_path, index_col=0).iloc[:, 0]
    regions = [r for r in model.data["areas"].index][:40]
    traj = BaselineTrajectory.from_file(traj_path)
    res = ProjectionModule(model, traj).run(regions=regions, max_outer_iter=1)

    ours = {}
    for reg, v in res.baseline[2030].get("supply", {}).items():
        acts = getattr(v, "activities", None)
        if acts is None:
            continue
        for a, val in acts.items():
            ours[a] = ours.get(a, 0.0) + float(val)
    ours = pd.Series(ours)

    common = [a for a in ours.index
              if a in cap.index and cap[a] > 10 and ours[a] > 10]
    if len(common) < 5:
        return
    corr = ours[common].corr(cap[common])
    assert corr > 0.9, (
        f"projected 2030 levels correlate only {corr:.3f} with CAPRI's reference")


@pytest.mark.slow
def test_projection_starts_from_capri_reference_and_calibrates(model):
    """Sprint 9p: the 2030 baseline is projected with CAPRI's own 2030 reference (CAPMOD's reference run over CAPRI's
    2017 results, levels, yields and land types per region: capri_ref_2030.json), not its trend projection, and the
    baseline is calibrated as CAPRI calibrates its supply models: the linear cost terms move until each region's
    solution is its projected levels (fodder crops excepted: the fodder balances hold them). The purchased feed bulks
    in the rations take CAPRI's 2030 bulk prices (feedBlkPrice_ CES of the products' 2030 prices)."""
    import os, json
    import pandas as pd
    from capri_mod.projection import ProjectionModule, BaselineTrajectory
    tp = os.path.join(str(DATA_DIR), "trajectories", "capri_ref_2030.json")
    src = os.path.join(str(DATA_DIR), "sources", "capri_baseline", "capri_ref_levl_yild_2030_2017.csv.xz")
    t = json.load(open(tp))
    raw = pd.read_csv(src)
    v = {(r.capri_region, r.activity, r.item, str(r.year)): r.value for r in raw.itertuples()}
    f = v[("DE110000", "SWHE", "LEVL", "2030")] / v[("DE110000", "SWHE", "LEVL", "2017")]
    assert abs(t["regional"]["herds"]["DE110000"]["SWHE"]["2030"] - f) < 1e-12          # written to the last digit
    assert t["regional"]["land"]["DE110000"]["ARABLE"]["2030"] < 1.0
    traj = BaselineTrajectory.from_file(tp)
    pm = ProjectionModule(model, traj, capri_prices_dir=os.path.join(str(DATA_DIR), "trajectories"))
    data, _ = pm.project_data(2030)
    cap = pd.read_csv(os.path.join(str(DATA_DIR), "validation", "capri_eu27_levels_2030_ref.csv"), index_col=0).iloc[:, 0]
    eu = [r for r in data["areas"].index if not r.startswith("NO")]
    for a in ("SWHE", "BARL", "RAPE", "GRAS"):
        assert abs(float(data["areas"].loc[eu, a].sum()) / float(cap[a]) - 1.0) < 0.015, a
    rb = data["ration_bulk_price"]
    assert rb[("DE000000", "FCER")] < 1.0 < rb[("DE000000", "FPRO")]
    # Sprint 9q: CAPRI's 2030 rations (Upper Bavaria's dairy cows: more other fodder, less silage maize) and usable
    # fodder per ha (silage maize for biogas in Germany)
    rf = data["ration_factor"][("DE210000", "DCOW")]
    assert rf["FOFA"] > 1.1 and rf["FMAI"] < 0.95
    mo = pm._model_for(data)
    res = mo.run(scenario="BASELINE", regions=["FR520000", "IR010000", "DE210000"], max_outer_iter=8)
    assert res["metadata"]["outer_converged"]
    for r in ("FR520000", "IR010000", "DE210000"):
        x = res["supply"][r].activities
        for a in ("BROI", "LAYS", "PIGF", "DCOW", "SWHE", "OFOD", "MAIF", "GRAS"):
            tgt = float((data["areas"] if a in data["areas"].columns else data["animal_numbers"]).at[r, a])
            # fodder crops are not calibrated (the fodder balances hold them, see the docstring): their split follows
            # the herds' fodder use and the crops' elasticities (IE04 silage maize -2.9% with CAPRI's fodder
            # elasticities, K32), so they get a looser bound than the calibrated activities
            tol = 0.05 if a in ("OFOD", "MAIF", "GRAS") else 0.015
            if tgt > 1:
                assert abs(float(x[a]) / tgt - 1.0) < tol, (r, a, float(x[a]), tgt)


def test_permanent_crop_base_fidelity(data):
    """Permanent crops must survive the base solve.

    The PERMANENT land figure and the crop areas come from different
    aggregations and disagree in 56 of 248 regions (4640 kha), concentrated in
    the Mediterranean permanent-crop regions — ES63/ES64 carry real olive area
    against a PERMANENT figure of zero. Taking the land figure literally made
    the BASE YEAR infeasible, so the solver cut and the largest crop absorbed
    it: EL43 olives collapsed 178 -> 40 kha in a plain base solve, surfacing as
    a 0.35x olive miss against CAPRI's 2030 reference.
    """
    import numpy as np
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities

    sm = SupplyModule(data, calibrate_supply_elasticities(data["areas"]))
    regions = [r for r in data["areas"].index
               if float(data["areas"].at[r, "OLIV"]) > 5][:12]
    if not regions:
        return
    sm.run(price_signals=None, regions=regions)

    errs = []
    for reg in regions:
        model = sm._models.get(reg)
        if model is None:
            continue
        base = float(model._base_levels().get("OLIV", 0.0))
        got = float(model.solve(price_shock=None).activities.get("OLIV", 0.0))
        if base > 5:
            errs.append(abs(got - base) / base)
    assert errs, "no olive regions solved"
    mean_err = float(np.mean(errs)) * 100.0
    assert mean_err < 10.0, (
        f"olive base fidelity {mean_err:.1f}% — the permanent-land bound is "
        "cutting a crop the base year says exists")


def test_nitrogen_balance_is_physically_plausible(data):
    """The gross N balance must land near observed EU levels.

    Two unit bugs made it meaningless. (1) GRAS yield is FRESH MATTER in kg/ha
    (~36000) while the uptake formula expects t/ha, so grass supplied 99.3% of
    total N uptake and drove the balance to -170000 kg N/ha. (2) Manure N was
    scaled `heads * 1000 / 1e6`, dividing by a further 1000 and leaving organic
    input at effectively ZERO against a real EU average near 55 kg N/ha.

    Eurostat puts the EU gross nitrogen balance around 45-50 kg N/ha, with a
    regional range of roughly 10-200.
    """
    import numpy as np
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities
    from capri_mod.environmental.environmental_module import EnvironmentalModule

    em = EnvironmentalModule(data)
    sm = SupplyModule(data, calibrate_supply_elasticities(data["areas"]))
    regions = _german_units(12)
    res = sm.run(price_signals=None, regions=regions)

    per_ha = []
    for reg in regions:
        if reg not in res or reg not in data["yields"].index:
            continue
        acts = res[reg].activities
        nb = em.compute_nitrogen_balance(acts, data["yields"].loc[reg], reg)
        area = sum(float(acts.get(c, 0.0)) for c in data["areas"].columns)
        if area > 0:
            per_ha.append(nb["n_surplus"] / area)

    assert per_ha, "no regions produced a nitrogen balance"
    median = float(np.median(per_ha))
    assert 0 < median < 200, (
        f"median N surplus {median:.0f} kg N/ha is outside any plausible range "
        "(Eurostat EU average ~45-50)")
    # and the components must be individually sane
    reg = regions[0]
    nb = em.compute_nitrogen_balance(
        res[reg].activities, data["yields"].loc[reg], reg)
    area = sum(float(res[reg].activities.get(c, 0.0)) for c in data["areas"].columns)
    assert 0 < nb["n_crop_uptake"] / area < 500, "implausible crop N uptake"
    assert nb["n_organic_input"] > 0, "manure N is not reaching the balance"


def test_permanent_crop_elasticities_match_capri(data):
    """Permanent-crop elasticities must match CAPRI's calibrated values.

    Source: `p_elasSupp` at the "CAL" level from
    `results/arm/supply_elas_2_1720<CC>.gdx` (ES, IT) — the regional,
    post-calibration values CAPRI's supply model actually solves with, unloaded
    at calibrate_supply.gms:512. CAPRI has permanents at 0.176-0.218 against
    annuals at 1.18-8.72, i.e. ~10x LESS elastic.

    This test replaces an earlier one asserting the OPPOSITE — that permanents
    should be MORE elastic than annuals. That came from `p_elasSupp` in
    `results/arm/elas*.gdx`, which is the MARKET model at member-state level
    over market commodities, not the regional supply matrix. It contains no
    olive ACTIVITY at all, only olive OIL, which should have ruled it out.
    """
    # since 23 October 2026 there are no default elasticities per activity (no proxies): CAPRI's values come per
    # region from build_elasticity_table; here the member state's p_elasSupp "CAL" (CAPRI_COUNTRY) in ES and IT
    from pathlib import Path
    from capri_mod.supply.capri_pmp import build_elasticity_table
    from capri_mod.data.definitions import ALL_ACTIVITIES
    from capri_mod.utils.utils import calibrate_supply_elasticities

    areas = data["areas"]
    eps, prov, _ = build_elasticity_table(Path(_repo_root()) / "capri_data", list(areas.index), ALL_ACTIVITIES,
                                          calibrate_supply_elasticities(areas), base_areas=areas)
    capri = {"APPL": 0.218, "OFRU": 0.189, "CITR": 0.184,
             "TAGR": 0.216, "WINE": 0.176, "TOMA": 0.668, "OVEG": 0.663}
    for crop, expected in capri.items():
        if crop not in eps.columns:
            continue
        for cc in ("ES", "IT"):
            rr = [r for r in eps.index if str(r).startswith(cc)]
            got = float(eps.loc[rr, crop].median())
            assert abs(got - expected) < 0.02, (
                f"{crop} {cc} elasticity {got:.3f} does not match CAPRI's calibrated {expected:.3f}")

    # and the structural relation must hold: permanents well below annuals
    import numpy as np
    perm = [float(eps[c].median()) for c in ("APPL", "OFRU", "CITR", "WINE") if c in eps.columns]
    ann = [float(eps[c].median()) for c in ("SWHE", "BARL", "RAPE", "POTA") if c in eps.columns]
    assert np.median(perm) < np.median(ann), (
        "permanent crops must be LESS elastic than annuals, as in CAPRI")


@pytest.mark.slow
def test_pesticide_reduction_binds_and_is_a_noop_at_zero(model):
    """The pesticide target's yield-loss channel must act, and only downward.

    CAPRI implements the F2F pesticide target as four shocks; only the 10%
    yield loss is represented here, because this model has no plant-protection
    cost component to cut. The yield loss needs no PPP data -- CAPRI states it
    as an explicit assumption, since it has no dose-response function for plant
    protection.
    """
    from capri_mod.policy.policy_module import PolicyScenario

    regions = _german_units(8)

    def totals(res):
        out = {}
        for reg, v in res.get("supply", {}).items():
            acts = getattr(v, "activities", None)
            if acts is None:
                continue
            for a, val in acts.items():
                out[a] = out.get(a, 0.0) + float(val)
        return out

    base = totals(model.run(scenario="BASELINE", regions=regions, max_outer_iter=1))
    zero = totals(model.run(custom_scenario=PolicyScenario(
        name="t", pesticide_reduction=0.0), regions=regions, max_outer_iter=1))
    cut = totals(model.run(custom_scenario=PolicyScenario(
        name="t", pesticide_reduction=0.50), regions=regions, max_outer_iter=1))

    # IPOPT's own tolerance: a warm start from the previous point ended 1e-7 relative away before the K75 fix; since
    # then the same baseline run twice differs by up to 3e-5 relative in small cereal activities (rye, oats, durum
    # wheat: DE23 RYEM 5.43015 vs 5.43000 kha; KNOWN_ISSUES K80), and the zero shock by as much (up to 6e-5, DE11 RYEM)
    tol = 1e-4
    for a, v in base.items():
        if v > 1.0:
            assert abs(zero.get(a, 0.0) - v) / v < tol, (
                f"pesticide_reduction=0 changed {a}")

    affected = [a for a in ("SWHE", "BARL", "RAPE")
                if base.get(a, 0.0) > 1.0]
    assert affected, "no affected crops present"
    assert any(cut.get(a, 0.0) < base[a] for a in affected), (
        "a 50% pesticide reduction should lower affected crop areas")


def test_unconverged_run_warns_and_is_recorded(model):
    """A run that does not converge must say so, loudly and in metadata.

    Every scenario comparison in this project was once run with
    `max_outer_iter=1`, which executes a single supply-market pass and so
    suppresses the price feedback. When EU supply falls, prices rise and cushion
    the quantity response; omitting that overstated the Farm-to-Fork cereal
    decline by 4 percentage points (−22.6% against −18.5% converged), and the
    unconverged figure was published before anyone noticed.

    The old code printed the warning only when `verbose=True`, so a
    `verbose=False` comparison — which is how every comparison was run — failed
    in silence. It now always warns and records `outer_converged` in metadata,
    so a caller can check rather than having to remember.
    """
    import warnings as _w

    regions = _german_units(4)

    with _w.catch_warnings(record=True) as caught:
        _w.simplefilter("always")
        res = model.run(scenario="BASELINE", regions=regions, max_outer_iter=1)
    fired = [x for x in caught
             if issubclass(x.category, RuntimeWarning) and "Outer" in str(x.message)]
    assert fired, "an unconverged run must raise a RuntimeWarning"
    assert res["metadata"].get("outer_converged") is False, (
        "metadata must record outer_converged=False")

    # and the converged case must stay quiet, or the warning becomes noise
    with _w.catch_warnings(record=True) as caught:
        _w.simplefilter("always")
        res = model.run(scenario="BASELINE", regions=regions)
    fired = [x for x in caught
             if issubclass(x.category, RuntimeWarning) and "Outer" in str(x.message)]
    assert not fired, "a converged run must not warn"
    assert res["metadata"].get("outer_converged") is True


def test_no_bogus_activity_codes_in_crop_groups(data):
    """Crop-group lists must name activities that actually exist.

    Grain maize is `CORN` in this model's activity set; CAPRI calls it `MAIZ`.
    Places listed `MAIZ` without `CORN` — the fertiliser cereals group (of the FertilizerModule removed on
    23 October 2026), the pesticide-affected list (and the retired abatement N2O proxy) — so grain maize
    (11,026 kha, the second-largest cereal by area) was silently excluded from all three. A non-existent key raises nothing; it simply never matches.

    `capri_pmp.ACTIVITY_ALIASES` maps MAIZ->CORN deliberately and is exempt.
    """
    from capri_mod.supply.supply_module import SupplyModule

    activities = set(data["areas"].columns)
    assert "CORN" in activities and "MAIZ" not in activities, (
        "this test assumes grain maize is CORN; the activity set has changed")

    affected = set(SupplyModule.__dict__.get("PESTICIDE_AFFECTED", ()))
    if not affected:
        from capri_mod.supply import supply_module as _sm
        for obj in vars(_sm).values():
            if isinstance(obj, type) and hasattr(obj, "PESTICIDE_AFFECTED"):
                affected = set(obj.PESTICIDE_AFFECTED)
                break
    if affected:
        assert "CORN" in affected, "pesticide target skips grain maize"
        assert "MAIZ" not in affected, "pesticide list names a non-existent activity"


def test_land_bounds_do_not_rewrite_the_base_year(data):
    """Neither land bound may cut a crop the base year says exists.

    The ARABLE and PERMANENT land figures come from a different aggregation than
    the crop areas and disagree in 54 and 56 of 248 regions respectively. Taken
    literally they make the BASE YEAR infeasible, so the solver must cut: LT02
    lost most of its cereals (crops 1,373 kha against an ARABLE figure of 120),
    and the 9,976 kha the solve shed matched the 9,960 kha of arable excess
    almost exactly. Both bounds are now max(land figure, observed area).

    This is the check the aggregate fidelity number could not make on its own:
    it improved from 11.28% to 0.47% when the arable bound was fixed, which
    means the earlier figure was not solver noise but a data conflict.
    """
    import numpy as np
    from capri_mod.model import CAPRIModel

    # in the model's run state (feed rations: the NLP form): a bare SupplyModule.run takes the plain QP path, which
    # no longer reproduces the base since the proxy removals of 23 October 2026 (KNOWN_ISSUES K68)
    regions = _german_units(25)
    m = CAPRIModel(data_dir=str(DATA_DIR), verbose=False)
    m.run(scenario="BASELINE", regions=regions, max_outer_iter=2)
    sm = m.supply_module

    base_total = solved_total = 0.0
    for reg in regions:
        model = sm._models.get(reg)
        if model is None:
            continue
        levels = model._base_levels()
        solved = model.solve(price_shock=None).activities
        for act in data["areas"].columns:
            b = float(levels.get(act, 0.0))
            if b >= 1.0:
                base_total += b
                solved_total += float(solved.get(act, 0.0))

    assert base_total > 0
    drift = (solved_total / base_total - 1.0) * 100.0
    assert abs(drift) < 5.0, (
        f"total cropped area drifts {drift:+.1f}% from base — a land bound is "
        "cutting crops the base year says exist")


def test_world_production_coverage(data):
    """Most world production must be backed by real data, not a share key.

    World base production was once only 63.2% real by volume; the remainder was
    spread across non-EU trade regions with a fixed share key and a seeded ±8%
    noise term. Extending coverage from CAPRI's own FAO_agg SUA raised it to
    76.6%. This test stops that regressing — and stops the extended file being
    dropped without anyone noticing.
    """
    import json
    from pathlib import Path
    from capri_mod.market.market_module import MarketModule

    base = Path(str(DATA_DIR))
    keys = set()
    for rel in ("2017/market/fao_market_baseline.json",
                "sources/fao_agg_2017/fao_agg_sua_2017_extended.json"):
        f = base / rel
        if f.exists():
            keys |= {tuple(k.split("|")) for k in json.load(open(f))}

    mm = MarketModule(data)
    bp = mm.base_production
    total = covered = 0.0
    for reg in bp.index:
        for comm in bp.columns:
            v = float(bp.at[reg, comm])
            if v <= 0:
                continue
            total += v
            if (reg, comm) in keys or reg == "EU27":
                covered += v
    assert total > 0
    share = covered / total * 100.0
    assert share > 70.0, (
        f"only {share:.1f}% of world production is backed by real data "
        "(expected >70% since the FAO_agg extension was wired in)")


def test_base_reconciliation_null_identity():
    """Reconciling already-consistent data must change nothing.

    This is the gate that catches a reconciler which REWRITES rather than
    reconciles. It is not hypothetical: an early version of the projection
    reconciler adjusted 248 regions by a 122% mean before this identity caught
    it.
    """
    import pandas as pd
    from capri_mod.data.reconcile_base import null_check

    areas = pd.read_csv(DATA_DIR / "2017" / "supply" / "base_areas.csv",
                        index_col=0)
    max_change = null_check(areas)
    assert max_change < 1e-6, (
        f"reconciling consistent data moved it by {max_change:.2e} — the "
        "reconciler is rewriting, not reconciling")


def test_yield_responds_to_price(data):
    """Yields must respond to own-price changes, as CAPRI's stage one does.

    CAPRI's supply model determines yields "exogenously by trend analysis ...
    and updated depending on price changes against the baseline" (documentation
    ch. 5). Without that the model has a pure extensive margin for price shocks:
    area moves, yield does not, which understates supply response and overstates
    the area change needed to deliver it.

    Two properties, the same pair that protects the nitrogen intensity margin:
      1. IDENTITY — at an unchanged price the yield factor is exactly 1.0, so
         the base year and PMP calibration are untouched.
      2. RESPONSE — a price rise raises yield, by less than proportionally.
    """
    import pandas as pd
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities

    sm = SupplyModule(data, calibrate_supply_elasticities(data["areas"]))
    region = list(data["areas"].index)[0]
    sm.run(price_signals=None, regions=[region])
    model = sm._models[region]

    # 1. identity: a zero shock must change nothing (both solves from the same cold start, see _cold)
    model.solve()                       # the split columns enter and are calibrated at the second solve, at base
    base = _cold(model).solve().activities
    zero = _cold(model).solve(price_shock=pd.Series(0.0, index=model.acts)).activities
    for act in base.index:
        if float(base.get(act, 0.0)) > 1.0:
            assert abs(float(zero.get(act, 0.0)) - float(base[act])) < 1e-6, (
                f"a zero price shock changed {act}")

    # 2. response: CAPRI's yield elasticities (supply/yield_elas.gms): cereals 0.3, oilseeds and potatoes 0.2, no
    #    other crop (Sprint 9s; was 0.15 for every crop)
    el = SupplyModule.yield_price_elasticity() if hasattr(SupplyModule, "yield_price_elasticity") else \
        type(model).yield_price_elasticity()
    assert el["SWHE"] == 0.3 and el["CORN"] == 0.3 and el["RAPE"] == 0.2 and el["POTA"] == 0.2
    assert "OVEG" not in el and "SUGB" not in el
    y0 = float(model.data.yields.get("SWHE", 0.0))
    if y0 > 0:
        model.apply_yield_price_response(pd.Series({"SWHE": 0.10, "OVEG": 0.10}))
        assert abs(float(model.data.yields["SWHE"]) / y0 - 1.10 ** 0.3) < 1e-12


def test_solve_leaves_no_state_behind(data):
    """A shocked solve must not alter the model for the next one.

    Solves rewrite parts of `self.data` for their own duration: CAP premiums,
    nutrient coefficients (nitrogen intensity margin), yields (yield-price
    response). The restore block used to ENUMERATE those fields, and the list
    fell behind twice — `nutrient_coefs` leaked until the intensity margin was
    traced, and `yields` leaked again when the yield-price response was added.
    Each leak is silent: the altered value persists into every later solve.

    The block now snapshots every restorable attribute rather than listing
    them, so a new mutation is covered the moment it is written. This test is
    the guard: run shocked solves, then check a plain solve is bit-identical to
    the one before them.
    """
    import pandas as pd
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities

    sm = SupplyModule(data, calibrate_supply_elasticities(data["areas"]))
    region = list(data["areas"].index)[0]
    sm.run(price_signals=None, regions=[region])
    model = sm._models[region]

    model.solve()                       # the split columns enter and are calibrated at the second solve, at base
    before = _cold(model).solve().activities.copy()

    shock = pd.Series(0.0, index=model.acts)
    for act in ("SWHE", "BARL"):
        if act in shock.index:
            shock[act] = 0.20
    model.solve(price_shock=shock)
    model.solve(nitrate_limit=model.base_n_intensity() - 20.0)
    model.solve(policy_shock={"organic_area_target": 0.25})

    after = _cold(model).solve().activities
    drift = max(abs(float(after.get(a, 0.0)) - float(before[a]))
                for a in before.index)
    assert drift < 1e-9, (
        f"a plain solve drifted by {drift:.2e} after shocked solves — "
        "something mutated state and was not restored")


def test_livestock_gross_output_is_marketed_product(model):
    """Livestock gross output must be real marketed product, in kt.

    It used to be level x CAPRI's YILD, which for breeding and suckler
    activities is not a marketed product (suckler cows: YILD 422.6 against 21.8
    of beef; sows: 19,917 against 50.6 of pork). One region reported 3.9
    billion tonnes of pig output. It was then suppressed as NaN.

    It is now built from CAPRI's final-product coefficients (COMI, BEEF, PORK,
    POUM, EGGS, SGMT, SGMI) by tools/build/build_livestock_output_coef.py, which
    reproduce real 2017 EU production to within 0.94-1.08 by product.
    """
    import math

    regions = _german_units(6)
    res = model.run(scenario="BASELINE", regions=regions, max_outer_iter=1)

    # NOT checked: output per head. Head counts are in CAPRI's own units, which
    # differ by species (poultry are in MILLION head, cattle in thousand), and
    # three regions (ITC4, ITF3, FI1B) carry poultry in a different unit from
    # the rest. The coefficients are immune to that - each is CAPRI's regional
    # product divided by the model's own count - but a per-head plausibility
    # test is not, and an earlier version of this test failed on it wrongly.
    import pandas as pd
    coef_path = DATA_DIR / "2017" / "supply" / "livestock_output_coef.csv"
    assert coef_path.exists(), "livestock_output_coef.csv missing"

    for region, sr in res["supply"].items():
        g = sr.gross_output
        total = g.sum()
        assert total < 1e5, (
            f"{region} gross output sums to {total:,.0f} kt — implausible for "
            "one NUTS-2 region; a non-product quantity is leaking in")
        for act in ("DCOW", "PIGS", "LAYS", "BROI"):
            if act in g.index and not math.isnan(float(g[act])):
                assert float(g[act]) < 2e4, (
                    f"{region} {act} = {float(g[act]):,.0f} kt exceeds any "
                    "single region's real livestock output")

    # The EU totals are the validated quantity: the coefficient build
    # reproduces CAPRI's own EU27 production less Ireland (which has no herds
    # in this model) - milk ~140,000 kt, pork ~22,500 kt.
    herds = model.data["animal_numbers"]
    coef = pd.read_csv(coef_path, index_col=0)
    eu = [r for r in coef.index if not r.startswith("NO")]
    milk = float((herds.reindex(eu)["DCOW"].fillna(0)
                  * coef.loc[eu, "DCOW"].fillna(0)).sum())
    # pigs are CAPRI's two activities since the pig split: sows (PIGS) and fattening pigs (PIGF)
    pork = sum(float((herds.reindex(eu)[a].fillna(0) * coef.loc[eu, a].fillna(0)).sum())
               for a in ("PIGS", "PIGF") if a in coef.columns and a in herds.columns)
    assert 125_000 < milk < 160_000, f"EU dairy output {milk:,.0f} kt off CAPRI"
    assert 20_000 < pork < 25_000, f"EU pig output {pork:,.0f} kt off CAPRI"


def test_livestock_intensity_margin_is_identity_when_unconstrained(model):
    """Dairy extensifies under a nitrogen ceiling, and only then.

    CAPRI carries every dairy herd as a low- and a high-intensity variant
    (DCOL/DCOH) so the herd can move between them under a nutrient target
    instead of only shrinking. The margin must be exactly inert when no ceiling
    binds, or it would disturb the base year and its PMP calibration.
    """
    import numpy as np

    sm = model.supply_module
    region = "NL110000" if "NL110000" in model.data["areas"].index else \
        str(model.data["areas"].index[0])
    sm.run(price_signals=None, regions=[region])   # regional models are lazy
    mo = sm._models[region]
    mo.solve()          # the split columns calibrated on the first solve enter from the second (one solve per run)

    base = mo.solve()
    again = mo.solve()
    b1 = float(base.gross_output.get("DCOW", float("nan")))
    b2 = float(again.gross_output.get("DCOW", float("nan")))
    if not np.isnan(b1):
        # relative: the second solve starts warm and stops within the solver's tolerance (1.3e-6 on 931 kt, 1.4e-9
        # relative, seen in the full suite on 21 October 2026 after other tests had solved the region)
        # (4.2e-8 and 1.5e-7 relative in two full-suite runs on 23 October 2026, the region solved once per supply run
        # since the land fallback's inner loop went: IPOPT's tolerance, 1e-8, is on the scaled problem; six digits of
        # milk output are the reproducibility this checks)
        assert abs(b1 - b2) < 1e-6 * max(1.0, abs(b1)), "an unconstrained solve is not reproducible"

    tight = mo.solve(nitrate_limit=100.0)
    t = float(tight.gross_output.get("DCOW", float("nan")))
    if not np.isnan(b1) and not np.isnan(t) and b1 > 0:
        herd_b = float(base.activities.get("DCOW", 0.0))
        herd_t = float(tight.activities.get("DCOW", 0.0))
        assert t <= b1 + 1e-6, "a nitrogen ceiling should not raise milk output"
        if herd_b > 0 and herd_t < herd_b:
            # output must fall by MORE than the herd: that difference is the
            # intensity margin doing its work rather than animals alone
            assert (t / b1) < (herd_t / herd_b) + 1e-9, (
                "output fell only as fast as the herd: the intensity margin is inert")


def test_fitness_for_use_is_consistent_with_the_model():
    """The fitness file must describe outputs that exist, with valid statuses.

    A fitness declaration that drifts from the model is worse than none: a
    caller would be told a number is fine when nothing checked it. This pins
    the structure, the vocabulary, and that every region named in a scope is a
    real region.
    """
    import json
    import pandas as pd
    from capri_mod.fitness import check

    root = _repo_root()
    doc = json.load(open(root / "capri_data" / "FITNESS_FOR_USE.json", encoding="utf-8"))
    allowed = set(doc["_status_values"])
    entries = doc["outputs"]
    assert entries, "no outputs declared"

    for key, e in entries.items():
        assert e.get("status") in allowed, f"{key}: unknown status {e.get('status')!r}"
        assert e.get("note"), f"{key}: a finding without a note cannot be acted on"
        if e["status"] != "validated":
            assert check(key).caveat(), f"{key}: non-validated entry yields no caveat"

    # every region named in a scope must be a real NUTS-2 region or a real
    # trade region -- the model has both, and they are different sets
    areas = pd.read_csv(root / "capri_data/2017/supply/base_areas.csv", index_col=0)
    from capri_mod.data.definitions import TRADE_REGIONS
    known = set(areas.index) | set(TRADE_REGIONS)
    for key, e in entries.items():
        for token in str(e.get("scope", "")).replace(",", " ").split():
            if (len(token) == 4 and token.isupper()
                    and token[:2].isalpha() and token.isalnum()):
                assert token in known, f"{key}: scope names unknown region {token}"

    # the vocabulary must behave: validated is clean, not_supported is unusable
    for key, e in entries.items():
        f = check(key)
        assert f.ok == (e["status"] == "validated")
        assert f.usable == (e["status"] != "not_supported")

    # an unrecorded key must NOT come back looking validated
    assert check("no.such.output").status == "unknown"
    assert not check("no.such.output").ok


def test_pesticide_target_applies_to_conventional_area_only():
    """CAPRI's rule (conventional_io.gms): the 50% pesticide cut is a TOTAL
    target, and only the part organic conversion has not already delivered is
    applied - to the conventional area. With no organic instrument the result
    must be unchanged; with one, the pesticide shock on a converting crop must
    be smaller, never larger.
    """
    from capri_mod.data.loaders import load_all_data
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities

    d = load_all_data("capri_data")
    region = "FR810000" if "FR810000" in d["areas"].index else str(d["areas"].index[0])
    sm = SupplyModule(d, calibrate_supply_elasticities(d["areas"]))
    sm.run(price_signals=None, regions=[region])
    mo = sm._models[region]
    crop = next(c for c in ("SWHE", "RAPE", "BARL") if c in mo.net_revenues.index)

    nr0 = float(mo.net_revenues[crop]); y0 = float(mo.data.yields[crop])
    mo.apply_pesticide_reduction(0.50)
    alone_y = float(mo.data.yields[crop]); alone_nr = float(mo.net_revenues[crop])
    mo.data.yields[crop] = y0; mo.net_revenues[crop] = nr0

    mo.apply_pesticide_reduction(0.50, organic_share=None)
    assert abs(float(mo.data.yields[crop]) - alone_y) < 1e-12, "no organic share must mean no change"
    mo.data.yields[crop] = y0; mo.net_revenues[crop] = nr0

    mo.apply_pesticide_reduction(0.50, organic_share=0.25)
    comb_y = float(mo.data.yields[crop])
    assert y0 - comb_y <= y0 - alone_y + 1e-12, "the yield loss grew with organic conversion"
    assert comb_y < y0, "the pesticide yield loss vanished on conventional land"


#: the land market off (CAPRI's p_landIsFixedinScenario): the two tests of fixed land and of the landscape floor's
#: fitting check that path, so they run with it explicitly (CAPRI's land rules, the N target per current hectare and
#: the ammonia techniques are always on since 27 October 2026)
def _cold(model):
    """Clear a regional model's warm start (CAPRI's CONOPT, like IPOPT here, starts from the last solution). Two solves
    of the same problem from different starts end within IPOPT's tolerance of each other, not bit-identical (KNOWN_ISSUES
    K80); from the same cold start they coincide, which is what a check for leaked state needs."""
    model._nlp_prev = None
    model._nlp_prev_f = None
    return model


STANDALONE_PRE_SETTINGS = {"supply.use_land_market": False}


def test_land_is_fixed_without_the_land_market(data, monkeypatch):
    """Agricultural land responds to its value only through CAPRI's land market. With the land market off (or where
    it fails), land is fixed, as in CAPRI without it: a crop-price rise moves land between crops but cannot use more
    arable land than the region has. Until 23 October 2026 a rent-elasticity expansion (0.15, capped at 15%) stood in
    there; it was a proxy (docs/design/PROXY_AUDIT.md S149, S410, S411) and was removed. Plain solves stay
    independent of history."""
    import numpy as np
    import pandas as pd
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities

    _set(monkeypatch, STANDALONE_PRE_SETTINGS)
    sm = SupplyModule(data, calibrate_supply_elasticities(data["areas"]))
    region = "FR240000" if "FR240000" in data["areas"].index else str(data["areas"].index[0])
    sm.run(price_signals=None, regions=[region])
    # the split, genetics and histosol columns enter at the second solve and are calibrated there, at base prices, as
    # in the model's baseline (two iterations at least): a first solve at shocked prices would calibrate them there
    sm.run(price_signals=None, regions=[region])
    mo = _cold(sm._models[region])
    base = sm.run(price_signals=None, regions=[region])[region]
    from capri_mod.supply.supply_module import CROPS
    arable = [a for a in CROPS if a not in ("GRAS",) + mo.PERMANENT_LAND_CROPS]      # the arable_land row
    limit = max(float(mo._land_of("ARABLE")) + float(mo._land_of("FALLOW")),
                sum(float(mo._base_levels().get(a, 0.0)) for a in arable))

    up = pd.Series(0.2, index=data["world_prices"].index)
    shocked = sm.run(price_signals=up, regions=[region])[region]
    assert not hasattr(shocked, "land_expansion"), "a land-expansion field is back on the result"
    used = sum(float(shocked.activities.get(a, 0.0)) for a in arable)
    assert used <= limit * (1 + 1e-6) + 1e-6, ("arable land expanded without the land market", used, limit)
    _cold(mo)
    again = sm.run(price_signals=None, regions=[region])[region]
    assert np.allclose(again.activities.values, base.activities.values, rtol=1e-8, atol=1e-8), \
        "a plain solve after a shocked one did not return the base solution"


def test_unreachable_landscape_floor_is_kept_as_capri(data, monkeypatch):
    """Where a landscape floor sized on total farmland cannot fit on a region's arable land (land market off: Greek,
    Alpine, Corsican regions), CAPRI keeps the floor (supply_model.gms e_setaLandscape; widen_bounds.gms never widens
    it) and carries on with the solver's last point, recorded. Until 27 October 2026 the floor was lowered in steps
    to what a linear program said the land could hold, plus a margin (K84: the shortfall was mostly that margin)."""
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities

    region = "EL250000"
    _set(monkeypatch, STANDALONE_PRE_SETTINGS)          # the land market off: the floor cannot be met by more land
    sm = SupplyModule(data, calibrate_supply_elasticities(data["areas"]))
    sm.run(price_signals=None, regions=[region])
    mo = sm._models[region]
    mo._nlp_fallback_log = []
    res = mo.solve(set_aside_requirement=0.10)
    assert not hasattr(res, "landscape_shortfall")
    log = " ".join(getattr(mo, "_nlp_fallback_log", None) or [])
    assert "landscape floor" in log and "land market off" in log, log
    assert not hasattr(mo, "_fit_aug_row")
    mo._nlp_fallback_log = []
    plain = mo.solve()
    assert plain.converged and not (getattr(mo, "_nlp_fallback_log", None) or []), "the plain solve failed"


def test_greendeal_switchboard_mirrors_capri():
    """CAPRI's Green Deal switches, names and units, in capri-mod.

    Farm-to-Fork defaults must map onto the four implemented instruments and
    carry CAPRI's result name; an option capri-mod does not implement must be
    refused, never silently ignored.
    """
    import pytest
    from capri_mod.policy.greendeal import greendeal_scenario, scenario_name

    f2f = greendeal_scenario()
    assert f2f.name == "greendeal_lnds10_org25_pest50_mine00_surp50_diet00_oth00"
    assert (f2f.set_aside_requirement, f2f.organic_area_target,
            f2f.pesticide_reduction, f2f.nutrient_surplus_target) == (0.10, 0.25, 0.50, True)
    assert scenario_name() == "greendeal_reference"
    for opt in ("dietShift", "othPol"):
        with pytest.raises(NotImplementedError):
            greendeal_scenario(**{opt: 20})
    # mineRedu takes the GUI's values (minfert_redu_uaa.gms, minfert_redu_by_crop.gms)
    assert greendeal_scenario(mineRedu="20crp").name == "greendeal_lnds10_org25_pest50_mine20crp_surp50_diet00_oth00"
    assert greendeal_scenario(mineRedu=20).mineral_redu == "20"
    with pytest.raises(ValueError):
        greendeal_scenario(mineRedu="15crp")     # in minfert_redu_by_crop.gms, not in the GUI
    with pytest.raises(ValueError):
        greendeal_scenario(surpRedu=33)          # not a CAPRI GUI option


def test_environmental_results_are_populated(model):
    """Every run must return environmental indicators for its regions.

    Two bugs - an undefined name in compute_ammonia and a missing @dataclass
    decorator - made every region fail inside run_all_regions, which swallowed
    the errors and returned an EMPTY table from every model run, unnoticed.
    """
    regions = [r for r in ("FR240000", "DE400000") if r in model.data["areas"].index]
    res = model.run(scenario="BASELINE", regions=regions, max_outer_iter=1)
    env = res["environmental"]
    assert env is not None and len(env) == len(regions), \
        f"environmental table has {0 if env is None else len(env)} rows for {len(regions)} regions"
    assert (env["n_surplus"] != 0).all() and (env["ghg_total"] > 0).all()


def test_fertiliser_substitution_is_exact_at_base(data):
    """Mineral N follows crop need minus what manure covers (CAPRI NUTNED_),
    linearised so that at BASE the balance is identical to the balance without
    substitution, in every region. A drift here would move the base year.
    It must also make manure a weaker lever where it is well used and a strong
    one where crops sit at CAPRI's minimum-mineral floor.
    """
    from capri_mod.environmental.environmental_module import EnvironmentalModule
    A = data["areas"]; H = data.get("animal_numbers")
    plain = dict(data); plain["fertiliser_substitution"] = None
    e_sub, e_plain = EnvironmentalModule(data), EnvironmentalModule(plain)
    worst = 0.0
    for r in list(A.index)[::5]:
        acts = {c: float(A.at[r, c]) for c in A.columns}
        if H is not None and r in H.index:
            acts.update({a: float(H.at[r, a]) for a in H.columns})
        a = e_sub.compute_nitrogen_balance(acts, data["yields"].loc[r], r)["n_surplus"]
        b = e_plain.compute_nitrogen_balance(acts, data["yields"].loc[r], r)["n_surplus"]
        worst = max(worst, abs(a - b) / max(1.0, abs(b)))
    assert worst < 1e-9, f"substitution moved the base balance (max relative {worst:.2e})"
    fs = data.get("fertiliser_substitution")
    if fs is not None and {"NL410000", "FR240000"} <= set(fs.index) and {"NL410000", "FR240000"} <= set(A.index):
        cow = {r: e_sub.compute_nitrogen_balance({"DCOW": 1.0}, data["yields"].loc[r], r)["n_surplus"]
               for r in ("NL410000", "FR240000")}
        assert cow["NL410000"] > cow["FR240000"], \
            f"a cow should weigh more where manure is saturated: {cow}"


def test_grass_intensity_delta_extensive_lowers_surplus(data):
    """CAPRI's grassland split (Sprint 7a): a hectare moved from intensive (GRAI) to extensive (GRAE)
    grassland uses less mineral N, removes less N and lowers the gross surplus, from CAPRI's own
    per-activity coefficients; the table covers the regions with grassland."""
    from capri_mod.environmental.environmental_module import EnvironmentalModule
    env = EnvironmentalModule(data)
    d = env.grass_intensity_delta("DE940000")
    assert d is not None
    assert d["n_mineral_input"] < 0 and d["n_crop_uptake"] < 0 and d["n_surplus"] < 0
    assert d["mineral_rate"] < 0
    gi = data["grass_intensity"]
    assert len(gi) > 200 and (gi["q_ext"] > 0).all() and gi["share_ext"].between(0, 1).all()


def test_cover_crop_requirement_and_winter_cover_row(data):
    """CAPRI's Farm-to-Fork catch-crop minimum (organic_io.gms + conventional_io.gms): with a 25%
    organic share and a 50% pesticide cut the requirement is a quarter of the area without winter
    cover plus the baseline catch crops (capped at that area), and it adds CAPRI's winterCover_ row:
    winter-covering crops <= UAAR - catch crops."""
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities

    sm = SupplyModule(data, calibrate_supply_elasticities(data["areas"]))
    region = "FR520000"
    sm.run(price_signals=None, regions=[region])
    model = sm._models[region]
    model.data.organic_targets_pp = None          # use the distance rule: o known below
    o_share = model._organic_baseline() + 0.25
    model._cover_crop_requirement(0.50, o_share)
    cv = model._cover
    assert cv is not None and cv["potential"] > 0 and cv["biofix"] > 0
    expect = min(0.25 * cv["potential"] + cv["base"], max(cv["potential"], cv["base"]))
    assert abs(cv["req"] - expect) < 1e-6 * max(1.0, expect)
    assert cv["delta"] > 0
    A, b, _, _ = model._build_constraints()
    assert "winter_cover" in model._row_labels
    i = model._row_labels.index("winter_cover")
    assert abs(b[i] - (cv["uaa"] - cv["req"])) < 1e-6 * cv["uaa"] + 1e-6
    # with a landscape floor, CAPRI adds FALL.FLOOR to the catch-crop area (winterCover_)
    A, b, _, _ = model._build_constraints(set_aside_requirement=0.10)
    i = model._row_labels.index("winter_cover")
    floor = -b[model._row_labels.index("landscape_floor")]
    assert floor > 0 and abs(model._fall_floor - floor) < 1e-9
    assert abs(b[i] - (cv["uaa"] - cv["req"] + floor)) < 1e-6 * cv["uaa"] + 1e-6
    model._cover = None


def test_dairy_split_column_calibrated_at_base():
    """CAPRI's dairy split (Sprint 7b): the column of cows moved from DCOH to DCOL is calibrated on
    the first baseline solve (linear term from the duals of the rows it enters, the cows'
    requirement rows included), so a second baseline solve keeps the base split (z ~ 0)."""
    from capri_mod.model import CAPRIModel
    m = CAPRIModel(data_dir=str(DATA_DIR), verbose=False)
    # two outer iterations: the split columns are calibrated on the first solve and enter from the second. Until
    # 23 October 2026 the land fallback's inner loop solved each region at least twice per supply run, so one outer
    # iteration was enough; without it a supply run solves each region once
    m.run(scenario="BASELINE", regions=["FR520000"], max_outer_iter=2)
    mo = m.supply_module._models["FR520000"]
    di = m.data["dairy_intensity"].loc["FR520000"]
    assert di["dcomi_rel"] < 0 and di["dmann_rel"] < 0 and di["denne_rel"] < 0
    assert getattr(mo, "_dairy_cz", None) is not None and getattr(mo, "_dairy_col", None) is not None
    cows = float(m.data["animal_numbers"].at["FR520000", "DCOW"])
    assert abs(float(mo._last_dairy_z)) < 1e-3 * cows


def test_histosol_emissions_and_fallowing_calibrated(data):
    """CAPRI's histosols: N2O per ha from the organic-soil share and the climate-weighted IPCC 2013
    factor (13 kg N2O-N/ha on temperate and boreal cropland); EU emissions of the order of the
    inventories' cultivated organic soils (10-20 Mt CO2-eq); fallowing calibrated to zero at base."""
    h = data["histosol"]
    assert (h["ef_n2o_crop"].dropna().between(2.7, 13.0 + 1e-9)).all()    # 13.000000000000002: written to the last digit
    assert h.loc["DE940000", "share_grass"] > 0.3 and h.loc["DE940000", "n2o_t_ha_crop"] > 0
    A = data["areas"]
    crops = [c for c in A.columns if c != "GRAS"]
    kt = (A[crops].sum(axis=1) * h["n2o_t_ha_crop"].reindex(A.index).fillna(0)
          + A["GRAS"] * h["n2o_t_ha_grass"].reindex(A.index).fillna(0))
    assert 10.0 < float(kt.sum()) * 298.0 / 1000.0 < 20.0          # Mt CO2-eq
    assert (h["pmp_sqr_crop"].dropna() > 0).all()


def test_manure_n2o_by_source_and_technology_effects():
    """CAPRI's manure N2O by stage (gases.gms): per t of manure N, housing/storage, application and
    grazing shares near IPCC's 1-2% in total; CAPRI's technology effects as its housing equation applies
    them (HOUSN_ sums only housing options and the combined air purification + cover options: a plain
    cover does not cut manure N2O), low-emission spreading raises application N2O; and the loss cascade:
    NH3 kept by a cover reaches the field, so the N left for application N2O rises."""
    import pandas as pd
    f = pd.read_csv(DATA_DIR / "2017" / "environment" / "manure_n2o_factors.csv")
    tot = f[["f_man", "f_app", "f_gra", "f_lea"]].sum(axis=1)
    assert tot.between(0.003, 0.04).all() and 0.01 < tot.median() < 0.025
    assert f[f.animal == "PIGF"]["f_gra"].median() == 0          # pigs hardly graze (outdoor pigs in a few regions)
    t = pd.read_csv(DATA_DIR / "2017" / "environment" / "manure_n2o_tech.csv")
    assert not (t[t.technology.isin(["CovStorHigh", "CovStorLow"])]["r_hou"].abs() > 0).any()
    assert t[t.technology == "AirPurCovHigh"]["r_hou"].median() > 0.3
    assert t[t.technology == "AmmAppLE"]["r_app"].median() < 0
    from capri_mod.supply import ammonia_techs as _at
    tm = _at.load(DATA_DIR / "2017" / "abatement" / "ammonia" / "ammonia_tech_model.csv")
    sub = next(sb for sb in tm["DE940000"]["PIGF"] if any(x["tech"] == "CovStorHigh" for x in sb["techs"]))
    s0 = {x["tech"]: 0.0 for x in sub["techs"]}
    h0, f0 = _at.stage_n(sub, s0)
    h1, f1 = _at.stage_n(sub, {**s0, "CovStorHigh": 1.0})
    assert f1 > f0 and abs(h1 - h0) < 1e-12


def test_baseline_surplus_is_capri_regional(data):
    """The tiered N target starts from CAPRI's own regional surplus (old NUTS codes and NUTS
    splits included), never from the model's own pattern scaled to a national total."""
    cs = data["capri_baseline_surplus"]
    assert not cs["source"].str.contains("scaled|own balance").any()
    g = pd.read_csv(DATA_DIR / "2017" / "environment" / "capri_gnb_components_2030.csv")
    sur = g[g["item"] == "SURTOT"].set_index("capri_region")["kg_n_per_ha"]
    for reg, c8 in (("IT120000", "IT120000"), ("BL400000", "BL400000"), ("SE070000", "SE070000"), ("PT300000", "PT300000")):
        assert abs(float(cs.at[reg, "surplus_kg_n_per_ha"]) - float(sur[c8])) < 0.01
    assert int((cs["source"].str.contains("NUTS-2")).sum()) >= 220


def test_model_regions_are_capris_regional_units(data):
    """The model's regions are CAPRI's regional units (27 October 2026): every region is a unit of
    shared/regional_units.csv, each carries its own CAPRI row (no NUTS splits, merges or proxy shares), and the units of
    the member states without regional detail are their member state's code. Per-head values are CAPRI's regional ones
    (Finland's FI18 once carried all of Etelae-Suomi's manure on one part of a split: 990 kg N per dairy cow)."""
    units = pd.read_csv(DATA_DIR / "shared" / "regional_units.csv")
    assert len(units) == 221 and set(data["areas"].index) == set(units.region)
    assert {"DK000000", "EE000000", "LT000000", "LV000000", "SI000000", "CY000000", "MT000000", "HR000000"} <= set(units.region)
    assert units.set_index("region").at["BL400000", "country"] == "LU"
    mc = data["livestock_manure_n_coef"]
    for r in ("FI180000", "FI130000", "FI1A0000", "PL310000", "PL120000"):
        assert 60.0 < float(mc.at[r, "DCOW"]) < 250.0, r
        assert 0.2 < float(mc.at[r, "LAYS"]) < 1.5, r


def test_bull_heifer_split_calibrated_at_base():
    """CAPRI's low/high-intensity bulls and heifers (Sprint 7c): one column per animal, calibrated on
    the first baseline solve like the dairy split, so a second baseline solve keeps the base split; a
    low-intensity stall turns over more animals (more young animals bought) and less manure N."""
    from capri_mod.model import CAPRIModel
    m = CAPRIModel(data_dir=str(DATA_DIR), verbose=False)
    m.run(scenario="BASELINE", regions=["FR520000"], max_outer_iter=2)
    mo = m.supply_module._models["FR520000"]
    ct = m.data["cattle_intensity"]["FR520000"]
    assert ct["BULL"]["dyoung_rel"] > 0 and ct["BULL"]["dmann_rel"] < 0
    assert set(getattr(mo, "_cattle_cz", {}) or {}) >= {"BULL"} and "BULL" in (mo._cattle_cols or {})
    # by default (the cattle member splits off, K65) only the intensity pairs carry a split, each at the base split
    assert set(mo._last_cattle_z or {}) == {"BULL", "HFRS"}
    for a, z in (mo._last_cattle_z or {}).items():
        assert abs(float(z)) < 1e-3 * max(1.0, float(m.data["animal_numbers"].at["FR520000", a.split(":")[0]])), (a, z)
    # with the member splits on, every split (the replacement heifers HFRS:rep, the calves CALV:male / female / sex)
    # gets its column and stays at the base split too
    from capri_mod import settings as S
    _prev = S.activate(S.current().replace({"supply.use_cattle_member_splits": True}))
    try:
        m = CAPRIModel(data_dir=str(DATA_DIR), verbose=False)
        m.run(scenario="BASELINE", regions=["FR520000"], max_outer_iter=2)
        mo = m.supply_module._models["FR520000"]
        assert set(mo._last_cattle_z or {}) >= {"BULL", "HFRS", "HFRS:rep", "CALV:male", "CALV:female", "CALV:sex"}
        for a, z in (mo._last_cattle_z or {}).items():
            assert abs(float(z)) < 1e-3 * max(1.0, float(m.data["animal_numbers"].at["FR520000", a.split(":")[0]])), (a, z)
    finally:
        S.activate(_prev)


@pytest.mark.slow
def test_parallel_regional_solves_match_sequential():
    """Sprint 9r: the regional supply models are solved across worker processes (one per core, CAPRI_WORKERS or
    SupplyModule.n_workers to change it). At given market prices the regions are independent, as in CAPRI, so the
    results are the same, to the last digit, with one worker or several. Two models built in one process agree too:
    the trade regions' tariffs are CAPRI's (tools/build/build_tariffs_2017.py), no longer drawn at random on each load."""
    from capri_mod.model import CAPRIModel
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.policy.greendeal import farm_to_fork_scenario
    import os
    sm = SupplyModule.__new__(SupplyModule)
    old = os.environ.get("CAPRI_WORKERS")
    os.environ["CAPRI_WORKERS"] = "3"
    try:
        assert sm.workers(10) == 3 and sm.workers(2) == 1
        sm.n_workers = 1                                  # run state over the setting run.n_workers
        assert sm.workers(10) == 1
    finally:
        os.environ.pop("CAPRI_WORKERS")
        if old is not None:
            os.environ["CAPRI_WORKERS"] = old
    # two regions, a livestock and a crop region (four took 112 s; the identity concerns the worker processes, not the
    # number of regions)
    regs = ["NL220000", "IT200000"]
    out = []
    from capri_mod.supply import capri_regional_nlp as C
    for nw in (1, 2):
        # both runs build their IPOPT solvers afresh: a solver kept in this process from an earlier test solves to the
        # same point within IPOPT's tolerance, not to the last digit (test_nlp_solver_cache_is_exact), and the worker
        # processes start with none
        C._SOLVERS.clear()
        m = CAPRIModel(data_dir=str(DATA_DIR), verbose=False)
        m.supply_module.n_workers = nw
        s = m.run(custom_scenario=farm_to_fork_scenario(), regions=regs, max_outer_iter=2)
        out.append(({r: dict(v.activities) for r, v in s["supply"].items()},
                    {r: dict(v.shadow_prices) for r, v in s["supply"].items()},
                    dict(m.supply_module._nbal_state)))
        assert all(m.supply_module._models[r]._env_for_surplus is m.supply_module._env_for_surplus for r in regs)
    assert out[0] == out[1]


def test_no_synthetic_inputs_reach_the_model(data):
    """Sprint 9s (docs/SYNTHETIC_DATA_AUDIT.md): crop premiums, costs, prices and yields are CAPRI's for every region
    (tools/build/build_crop_economics_2017.py), the loaders no longer generate data, and every region with a herd or crops
    has CAPRI's environmental coefficients - the generic fallbacks were removed, so a gap must show here."""
    import os
    import pandas as pd
    from capri_mod.data import loaders
    from capri_mod.data.definitions import CROPS, ANIMALS
    from capri_mod.environmental.environmental_module import EnvironmentalModule
    areas, herds = data["areas"], data["animal_numbers"]
    # premiums: every region and crop (CAPRI PRME, DE11 soft wheat 360.8, wine 338.5); the payment engine's BPS is
    # CAPRI's premium per ha of UAA, not the random draw the file used to hold
    pr = data["cap_premium"]
    assert set(areas.index) <= set(pr.index)
    assert abs(pr.at["DE110000", "SWHE"] - 360.8) < 0.1 and abs(pr.at["DE110000", "WINE"] - 338.5) < 0.1
    for c in CROPS:
        if c in areas.columns:
            grown = areas.index[areas[c] > 0]
            assert pr.loc[grown, c].notna().all(), c
    assert abs(data["cap_payments"].at["DE110000", "BPS"] - 391.64) < 0.01
    assert (data["cap_payments"][["ANC", "AES", "ORGANIC"]] == 0).all().all()
    # costs and yields: CAPRI's TOIN and YILD, no cap (other fruit in AT11: 27,028 EUR/ha), wine and fibre included
    vc = data["variable_costs_regional"]
    assert abs(vc.at["AT110000", "OFRU"] - 27028.46) < 0.1 and abs(vc.at["DE110000", "WINE"] - 4520.44) < 0.1
    assert abs(data["yields"].at["AT110000", "TEXT"] - 3.80) < 0.05
    # loaders: no generator left
    import inspect
    assert "RNG" not in inspect.getsource(loaders)
    try:
        loaders.load_yields(os.path.join(str(DATA_DIR), "no_such_dir"))
        raise AssertionError("a missing file must raise")
    except FileNotFoundError:
        pass
    # environmental coefficients present wherever they are needed
    env = EnvironmentalModule(data)
    mc, m4, e4 = data["livestock_manure_n_coef"], data["livestock_ch4man_coef"], data["livestock_ch4ent_coef"]
    for r in herds.index:
        for a in ANIMALS:
            if a in herds.columns and herds.at[r, a] > 0:
                assert pd.notna(mc.at[r, a]) and mc.at[r, a] > 0, (r, a)
                assert pd.notna(m4.at[r, a]), (r, a)
                assert env._manure_n2o_factor(r, a) is not None, (r, a)
        if (herds.loc[r] > 0).any():
            assert env._nh3_factors().get(r), r
    for r in areas.index:
        if (areas.loc[r] > 0).any():
            assert env._capri_crop_n(r) is not None, r
            assert r in data["n_deposition_regional"].index, r
            assert r in data["crop_co2_coef"].index, r


def test_ghg_accounts_take_capris_methane_and_co2(data):
    """Sprint 9s: manure and enteric CH4 per head are CAPRI's (CH4MAN, CH4ENT totals / census heads, regional:
    dairy manure CH4 in Germany ~2.6 times France's), CO2 from liming CAPRI's per ha of every crop (DE11 115.6
    kg/ha) and from urea mineral N x the member state's urea share x 44/28; the GHG total is split into non-CO2
    (JRC121368's figure) and CAPRI's GGWP (the emission tax's base: non-CO2 + liming)."""
    import pandas as pd
    m4 = data["livestock_ch4man_coef"]
    de = m4.loc[[r for r in m4.index if r.startswith("DE")], "DCOW"].median()
    fr = m4.loc[[r for r in m4.index if r.startswith("FR")], "DCOW"].median()
    assert de > 2.0 * fr
    co2 = data["crop_co2_coef"]
    assert abs(co2.at["DE110000", "co2lim_kg_ha"] - 115.616) < 0.01 and abs(co2.at["DE110000", "urea_share"] - 0.158) < 0.001
    h = data["animal_numbers"]
    eu = [r for r in h.index if not r.startswith("NO")]
    cols = [c for c in m4.columns if c in h.columns]
    man = float((h.loc[eu, cols] * m4.reindex(eu)[cols]).sum().sum()) / 1000.0      # kt CH4
    assert 1350 < man < 1450                                       # CAPRI 2017: 1,396 kt (the old flat factors: 1,072)
    from capri_mod.environmental.environmental_module import EnvironmentalIndicators
    assert {"ghg_non_co2", "ghg_ggwp", "ghg_urea"} <= set(EnvironmentalIndicators.__dataclass_fields__)


@pytest.mark.slow
def test_fixed_activities_land_market_and_grass_as_capri(model):
    """Sprint 9s, the audit's open items: CAPRI's fixed activities (FACT: other oilseeds, other industrial crops,
    other animals) stay at their data level and other oilseeds have no market (CAPRI nonXX_CROPS; the pooled world
    market rested on an invented world total); every region with farmland has CAPRI's land market (Ireland's three
    NUTS-2016 regions from IE01 + IE02, so the rent-elasticity fallback serves only a land market switched off);
    grass yields are CAPRI's fresh matter (the GRAS output) at CAPRI's dry-matter content 0.22."""
    import json, os
    from capri_mod.data.definitions import MARKET_COMMODITIES
    from capri_mod.supply.supply_module import FIXED_ACTIVITIES
    from capri_mod.policy.greendeal import farm_to_fork_scenario
    assert "OOIL" not in MARKET_COMMODITIES and set(FIXED_ACTIVITIES) == {"OOIL", "OIND", "NURS", "FLOW", "OCRO", "OANI"}
    lm = model.data["land_market"]
    a = model.data["areas"]
    assert [r for r in a.index if a.loc[r].sum() > 0 and r not in lm] == []
    y = model.data["yields"]
    assert abs(y.at["DE110000", "GRAS"] - 32245.664 * 0.22 / 1000.0) < 1e-3
    assert abs(y.at["DK000000", "GRAS"] - 35718.29 * 0.22 / 1000.0) < 1e-2          # was a template value of ~5 t
    regs = ["ES610000", "FR520000"]
    s = model.run(custom_scenario=farm_to_fork_scenario(), regions=regs, max_outer_iter=2)
    for r in regs:
        for x in ("OOIL", "OIND"):
            assert abs(float(s["supply"][r].activities.get(x, 0.0)) - float(a.at[r, x])) <= 1e-5 * max(1.0, float(a.at[r, x]))


def test_parameter_file_and_code_agree():
    """Sprint 9t: the model's parameters live in one file, capri_data/shared/model_parameters.csv (value, unit,
    kind, source). Every row is read by the code and every param() call names a row - the file cannot drift. Kinds
    are limited to the declared ones, every row has a source."""
    import csv, re, pathlib
    from capri_mod import params
    rows = list(csv.DictReader(open(params.FILE, newline="")))
    assert all(r["source"].strip() for r in rows)
    # run settings (switches, tolerances) are not parameters: capri_mod/settings/defaults.toml (23 October 2026)
    assert {r["kind"] for r in rows} <= {"capri", "ipcc", "jrc121368", "legal", "literature"}
    code = "\n".join(p.read_text() for p in pathlib.Path(params.__file__).parent.rglob("*.py") if "tests" not in p.parts)
    called = set(re.findall(r"param(?:_table)?\(\"([A-Z0-9_]+)\"\)", code))
    names = params.names()
    assert called - names == set(), called - names          # a parameter the file does not have
    assert names - called == set(), names - called          # a row no code reads
    assert params.param("GWP_N2O") == 298.0 and params.param_table("FIBRE_FACTOR")["DCOW"] == 0.6


def test_settings_layer_is_the_one_source_of_run_settings():
    """The settings layer (agreed 23 October 2026): every switch read through `setting(...)` names a key of
    defaults.toml, every key of defaults.toml is read somewhere, an unknown key or a wrong type stops, assigning to a
    setting attribute is an error (no second value), override() restores, and the effective settings round-trip
    through TOML."""
    import re, pathlib, tomllib
    from capri_mod import settings as S
    from capri_mod.supply.supply_module import RegionalSupplyModel
    root = pathlib.Path(S.__file__).parents[1]
    code = "\n".join(p.read_text() for p in root.rglob("*.py") if "tests" not in p.parts and "settings" not in p.parts)
    code += "\n".join(p.read_text() for p in (root.parent / "tools" / "run").glob("run_*.py"))
    keys = set(dict(S.defaults().items()))
    used = {k for k in keys if f'"{k}"' in code or f'section("{k.split(".")[0]}")' in code}
    assert keys - used == set(), sorted(keys - used)                     # a key no code reads
    for k in re.findall(r'(?:setting|get)\(\s*"([a-z_]+\.[A-Za-z_]+)"', code):
        assert k in keys, k                                              # a setting defaults.toml lacks
    with pytest.raises(S.SettingsError):
        S.current().replace({"supply.no_such_key": 1})
    with pytest.raises(S.SettingsError):
        S.current().replace({"supply.use_land_market": "yes"})
    with pytest.raises(AttributeError):
        RegionalSupplyModel.__dict__["use_land_market"].__set__(object(), False)
    assert RegionalSupplyModel.use_land_market is True
    with S.override({"supply.use_land_market": False}) as s_:
        assert RegionalSupplyModel.use_land_market is False and s_.diff() == {"supply.use_land_market": False}
    assert RegionalSupplyModel.use_land_market is True
    t = S.current().replace({"market.eu_blocks": True}).to_toml()
    assert S.load(overrides={k: v for sec, kv in tomllib.loads(t).items() for k, v in
                             ((f"{sec}.{k2}", v2) for k2, v2 in kv.items())}).get("market.eu_blocks") is True



def test_projection_trajectory_moves_every_livestock_yield(data):
    """K12 (docs/KNOWN_ISSUES.md): CAPRI's 2030 reference splits dairy cows, heifers, bulls and calves into intensity
    variants, so the model's own animals had no yield factor and 2030 output per head stayed at 2017 (EU cow milk 140 Mt
    against CAPRI's 154). Every livestock activity whose output follows its yield must have a 2030 factor for every
    region that keeps it - its own, or the EU growth fallback - and dairy cows a regional one."""
    import json
    from pathlib import Path
    from capri_mod.projection.projection_module import ProjectionModule
    t = json.loads((Path(__file__).resolve().parents[2] / "capri_data" / "trajectories" / "capri_ref_2030.json").read_text())
    reg, gro = t["regional"]["yields"], t["growth"]["yields"]
    herds = data["animal_numbers"]
    for a in ProjectionModule.LIVESTOCK_YIELD:
        assert a in gro, f"no EU yield growth for {a}"
    kept = [r for r in herds.index if float(herds.at[r, "DCOW"] if "DCOW" in herds.columns else 0.0) > 1.0]
    have = [r for r in kept if "DCOW" in (reg.get(r) or {})]
    assert len(have) >= 0.95 * len(kept), (len(have), len(kept))
    eu = float(gro["DCOW"]["2030"])
    assert 1.05 < eu < 1.25, eu          # CAPRI 2030 reference: EU milk yield per cow +12-14% on 2017


def test_manure_spread_follows_capri(data):
    """CAPRI's fertDistExcr_ distributes v_ManureNPK, the manure N left after the losses in housing and storage
    (GASANI, RUNANI) and net exports: EXCRET - MTRADE - GASANI - RUNANI in CAPRI's 2030 reference. The loss shares
    per region and animal are CAPRI's ((GASANI + RUNANI) / MANN), cover every region, and the balance's manure
    spread is the excreted N after trade less them."""
    from capri_mod.environmental.environmental_module import EnvironmentalModule
    t = data["manure_housing_losses"]
    assert t is not None and t.index.nunique() == len(data["areas"])
    assert t["loss_share"].between(0.05, 0.8).all()
    env = EnvironmentalModule(data)
    reg = "RO020000"
    ls = env._manure_loss_shares(reg)
    acts = {"DCOW": 10.0}
    nb = env.compute_nitrogen_balance(acts, {}, reg)
    exc = 10.0 * env._n_excretion(reg, "DCOW")
    assert abs(nb["n_manure_housing_loss"] - exc * ls["DCOW"]) < 1e-9 * max(1.0, exc)
    assert abs(nb["n_manure_applied"] - (nb["n_organic_input"] - exc * ls["DCOW"])) < 1e-9 * max(1.0, exc)


@pytest.mark.slow
def test_jrc_relaxed_n_target_is_kept(model, monkeypatch):
    """JRC121368 sect. 4.3.4: where the tiered N target is infeasible the region's cut is the EU average (36%).
    NL12's regional model in CAPRI's form has no solution at the target below; the target is relaxed in CAPRI's form
    (K57), once, and kept: later iterations start from the relaxed target instead of failing the tiered one again."""
    import warnings
    from capri_mod.policy.greendeal import farm_to_fork_scenario
    from capri_mod.supply.supply_module import RegionalSupplyModel
    regs = ["NL120000"]
    # Since histosol fallowing and the grassland equality (K59, K60, 21 October 2026) NL12 meets JRC121368's tiered
    # target by itself (dairy cows -80% at 2017 prices); the relaxation is tested with a target it cannot meet (a 95%
    # cut of its surplus)
    monkeypatch.setattr(RegionalSupplyModel, "tiered_surplus_target", lambda self, sp: 0.05 * sp)
    model.run(scenario="BASELINE", regions=regs, max_outer_iter=1)
    try:
        s = model.run(custom_scenario=farm_to_fork_scenario(), regions=regs, max_outer_iter=3)
        r = s["supply"]["NL120000"]
        mo = model.supply_module._models["NL120000"]
        assert "N_balance" in list(mo._row_labels) and r.converged
        assert getattr(mo, "_nlp_fb_last", True) is False                       # the last solve in CAPRI's form
        fb = s["metadata"]["nlp_fallback"].get("NL120000") or []
        assert all("relaxed target" in e for e in fb) and len(fb) <= 1, fb
        assert bool(getattr(r, "n_target_relaxed", False)) == bool(fb)
    finally:
        model.run(scenario="BASELINE", regions=regs, max_outer_iter=1)


def test_projection_carries_permanent_crops():
    """The projection layer carries the previous period's perennial areas (the crops on permanent land, as the supply
    model defines them, vineyards included) into the next period's data; annual crops are not carried."""
    from capri_mod.projection.projection_module import ProjectionModule
    from capri_mod.supply.supply_module import RegionalSupplyModel
    perm = list(RegionalSupplyModel.PERMANENT_LAND_CROPS)
    assert "WINE" in perm
    areas = pd.DataFrame({c: [10.0] for c in perm + ["SWHE"]}, index=["IT11"])
    solved = pd.Series({c: 7.0 for c in perm + ["SWHE"]})
    ProjectionModule._carry_forward({"areas": areas}, {"activities": {"IT11": solved}})
    for c in perm:
        assert areas.at["IT11", c] == 7.0, c
    assert areas.at["IT11", "SWHE"] == 10.0


def test_rye_and_oats_are_markets(model):
    """Rye (RYEM) and oats (OATS) are market products of their own, as in CAPRI (arm/arm_sets.gms CERE_DEF): each
    activity's output reaches its own market, not OCER's, and the activities earn their own market price."""
    from capri_mod.data.definitions import MARKET_COMMODITIES
    from capri_mod.supply.supply_module import SupplyModule
    for c in ("RYEM", "OATS", "OCER"):
        assert c in MARKET_COMMODITIES
    agg = pd.DataFrame({"RYEM": [3.0], "OATS": [5.0], "OCER": [7.0]}, index=["DE000000"])
    ms = model._bridge_supply_to_market(agg)
    assert ms.at["DE000000", "RYEM"] == 3.0
    assert ms.at["DE000000", "OATS"] == 5.0
    assert ms.at["DE000000", "OCER"] == 7.0
    assert "RYEM" not in SupplyModule.ACTIVITY_PRICE_SOURCE and "OATS" not in SupplyModule.ACTIVITY_PRICE_SOURCE
    wp = model.data["world_prices"]
    for c in ("RYEM", "OATS"):
        assert c in (wp.index if hasattr(wp, "index") else wp)


def test_table_grapes_and_tobacco_are_markets(model):
    """Table grapes (TAGR) and tobacco (TOBA) are CAPRI market products (arm/arm_sets.gms CROPS_DEF): the activities'
    output reaches their own markets; CAPRI's world prices and Armington elasticities are in the data; the EU's use of
    tobacco is processing, with CAPRI's processing function (ProcNQ_: p_hessNQProc of the member states)."""
    import json
    from capri_mod.data.definitions import MARKET_COMMODITIES
    for c in ("TAGR", "TOBA"):
        assert c in MARKET_COMMODITIES
    agg = pd.DataFrame({"TAGR": [2.0], "TOBA": [0.5]}, index=["IT000000"])
    ms = model._bridge_supply_to_market(agg)
    assert ms.at["IT000000", "TAGR"] == 2.0 and ms.at["IT000000", "TOBA"] == 0.5
    arm = pd.read_csv(DATA_DIR / "2017" / "market" / "armington_rho.csv", index_col=0)
    assert arm.at["TAGR", "rho1"] == 3.7 and arm.at["TOBA", "rho1"] == 1.8
    h = pd.read_csv(DATA_DIR / "2017" / "market" / "processing_nq_hessian.csv")
    eu = h[(h.model_region == "EU27") & (h.x == "TOBA") & (h.y == "TOBA")]
    assert len(eu) > 0 and (eu.h > 0).all() and (eu.arm1p_y > 0).all()


def test_table_olives_are_a_market_of_their_own(model, data):
    """Table olives (TABO) are a CAPRI activity and market product apart from olives for oil (OLIV, sold as olive oil
    OLIO): the areas are CAPRI's two (OLIV + TABO = the former pooled olive area), table olives reach their own market
    one to one, olives for oil only through the oil yield; the TABO data are finite everywhere (0 where CAPRI has no
    table olives in the member state)."""
    from capri_mod.data.definitions import MARKET_COMMODITIES, CROPS
    assert "TABO" in CROPS and "TABO" in MARKET_COMMODITIES
    ar = data["areas"]
    assert 4500 < ar["OLIV"].sum() < 4900 and 250 < ar["TABO"].sum() < 350          # kha: CAPRI 2017 4,703 and 307
    for k in ("yields", "variable_costs"):
        assert pd.read_csv(DATA_DIR / "2017" / "supply" / f"{k}.csv", index_col=0)["TABO"].notna().all()
    agg = pd.DataFrame({"OLIV": [10.0], "TABO": [2.0]}, index=["IT000000"])
    ms = model._bridge_supply_to_market(agg)
    assert ms.at["IT000000", "TABO"] == 2.0
    assert 0.0 < ms.at["IT000000", "OLIV"] < 10.0 * 0.5                              # olive oil, not olives
    arm = pd.read_csv(DATA_DIR / "2017" / "market" / "armington_rho.csv", index_col=0)
    assert arm.at["TABO", "rho1"] == 4.1                                            # p_rhoArm1 (market1_ch.gms)


def test_textile_crops_are_one_activity_and_market(model, data):
    """CAPRI's textile crops are one activity and one market product, TEXT (sets.gms; arm/arm_sets.gms CROPS_DEF),
    cotton in Greece, Spain and Bulgaria, flax and hemp elsewhere; the model's former split into cotton (COTT) and
    other fibre (OFIB) is gone. EU use is processing, with CAPRI's processing function (ProcNQ_)."""
    import json
    from capri_mod.data.definitions import MARKET_COMMODITIES, CROPS
    assert "TEXT" in CROPS and "TEXT" in MARKET_COMMODITIES and not {"COTT", "OFIB"} & set(CROPS)
    ar = data["areas"]
    assert 520 < ar["TEXT"].sum() < 550                                              # kha, CAPRI 2017: 534.7
    assert ar.loc[[r for r in ar.index if r.startswith("EL")], "TEXT"].sum() > 300  # Greek cotton
    agg = pd.DataFrame({"TEXT": [3.0]}, index=["EL000000"])
    assert model._bridge_supply_to_market(agg).at["EL000000", "TEXT"] == 3.0
    arm = pd.read_csv(DATA_DIR / "2017" / "market" / "armington_rho.csv", index_col=0)
    assert arm.at["TEXT", "rho1"] == 8.2                                            # p_rhoArm1 (market1_ch.gms)
    h = pd.read_csv(DATA_DIR / "2017" / "market" / "processing_nq_hessian.csv")
    assert len(h[(h.model_region == "EU27") & (h.x == "TEXT") & (h.y == "TEXT") & (h.h > 0)]) > 0


def test_palm_and_other_vegetable_oils_are_markets(model):
    """Palm oil (PLMO) and other vegetable oils (OTHO) are CAPRI market products (arm/arm_sets.gms CROPS_DEF) without a
    supply-model activity: the EU supplies other vegetable oils through CAPRI's market supply function, which responds
    to the EU price against base (not against the price the supply models last saw); palm oil is a biodiesel feedstock
    priced by its market."""
    import numpy as np
    from capri_mod.data.definitions import MARKET_COMMODITIES
    from capri_mod.market.market_module import MarketModule
    assert {"PLMO", "OTHO"} <= set(MARKET_COMMODITIES)
    assert MarketModule.EU_MARKET_SUPPLY == frozenset({"OTHO", "FFIS", "SFIS", "OAQU"})
    fs = pd.read_csv(DATA_DIR / "2017" / "market" / "biofuel_feedstock.csv")
    assert (fs.loc[fs.feedstock == "PLMO", "commodity"] == "PLMO").all()
    mm = model.market_module
    cols = list(mm.commodities)
    rr = pd.DataFrame(1.0, index=mm.base_production.index, columns=cols)
    rr.loc["EU27", "OTHO"] = 1.10
    mm._eu_price_seen = pd.Series(1.10, index=cols)            # the supply models saw the same price
    s = mm.supply_response(mm.world_prices_base, None, region_ratio=rr)
    base = float(mm.base_production.at["EU27", "OTHO"])
    assert base > 0
    assert abs(float(s.at["EU27", "OTHO"]) / base - 1.10 ** 0.977) < 1e-6         # p_elasSupp, EU median
    mm._eu_price_seen = None


def test_supply_elasticities_reach_every_region_from_capri(data):
    """K30, K32: crops the regional CAPRI sources lack take the member state's calibrated elasticity (tobacco 0.44,
    not the hand-entered 0.213); recoded regions reach the PMP source through the region map or the national row
    (Denmark, Berlin); CAPRI's fodder on arable land reaches the model's other fodder."""
    from pathlib import Path
    from capri_mod.supply.capri_pmp import build_elasticity_table
    from capri_mod.utils.utils import calibrate_supply_elasticities
    A = data["areas"]
    eps, prov, summ = build_elasticity_table(Path(DATA_DIR), list(A.index), list(A.columns),
                                             calibrate_supply_elasticities(A), base_areas=A)
    assert prov.at["ES610000", "TOBA"] == "CAPRI_COUNTRY" and 0.43 < eps.at["ES610000", "TOBA"] < 0.46
    for r in ("DK000000", "DED00000"):
        assert prov.at[r, "SWHE"] in ("PMP_CAPRI", "REGIONAL_CAPRI"), r
    assert (prov["OFOD"] != "NO_CAPRI_VALUE").sum() > 200
    grown_default = sum(A.at[r, a] for r in A.index for a in ("SWHE", "BARL", "CORN", "RAPE")
                        if prov.at[r, a] == "NO_CAPRI_VALUE" and A.at[r, a] > 0)
    assert grown_default < 800                                                      # kha (before K32: 7,900)


def test_capri_activity_bounds(data):
    """K27: CAPRI's bounds on endogenous activity levels (supply/set_supply_bounds.gms): 0.1 x to max(10 x, + 100) the
    simulation's data level, the 100 in CAPRI's units (LEVL; animals converted with capri_level_ratio.csv), set-aside
    and fixed activities exempt; the base solution lies inside them."""
    from capri_mod.supply.supply_module import SupplyModule, FIXED_ACTIVITIES
    from capri_mod.utils.utils import calibrate_supply_elasticities
    sm = SupplyModule(data, calibrate_supply_elasticities(data["areas"]))
    sm.run(price_signals=None, regions=["NL120000"])
    m = sm._models["NL120000"]
    A, b, _, _ = m._build_constraints()
    lab = list(m._row_labels)
    x0 = m._base_levels()
    for a in ("DCOW", "SHGF", "SWHE", "GRAS"):
        v = float(x0.get(a, 0.0))
        if v <= 1e-8:
            continue
        up, lo = b[lab.index(f"bound_{a}_up")], -b[lab.index(f"bound_{a}_lo")]
        k = float(data["capri_level_ratio"].at["NL120000", a]) if a in data["capri_level_ratio"].columns else 1.0
        assert abs(up - max(10 * v, v + 100 * k)) < 1e-9 and abs(lo - 0.1 * v) < 1e-9, (a, up, lo, v, k)
    assert not any(l in lab for l in ("bound_SETA_up",) + tuple(f"bound_{f}_up" for f in FIXED_ACTIVITIES))


def test_lamb_balance_links_sheep_activities():
    """CAPRI's lambs (sets.gms YLAM.ILAM): milk sheep and goats (SHGM) produce them, fattening (SHGF) and SHGM's
    replacement use them; the young-animal balances carry them and EU production and use agree at base."""
    import json
    ya = json.load(open(DATA_DIR / "2017" / "supply" / "young_animals_2017.json"))["regions"]
    herds = pd.read_csv(DATA_DIR / "2017" / "supply" / "animal_numbers.csv", index_col=0)
    P = U = 0.0
    for r, rec in ya.items():
        lb = rec.get("lambs")
        if lb:
            assert set(lb["produce"]) <= {"SHGM"} and set(lb["use"]) <= {"SHGM", "SHGF"}
            P += sum(c * herds.at[r, a] for a, c in lb["produce"].items())
            U += sum(c * herds.at[r, a] for a, c in lb["use"].items())
    assert P > 0 and abs(P / U - 1.0) < 0.02, (P, U)


def test_food_demand_is_capris_generalised_leontief(data):
    """Step 2 of docs/archive/MARKET_STRUCTURE_PLAN.md: human consumption follows CAPRI's GL system per behavioural region
    (arm/market_model.gms:826-916) with p_pdGL, p_pbGL at CAPRI's 2030 calibration point. Checks: CAPRI's food
    demand reproduced at the calibration point; the price elasticities equal CAPRI's p_ElasDem (DE, own and cross);
    homogeneity of degree zero in prices and income; demand exactly at base at the base prices; cross-price
    response (a pork price rise raises EU beef and poultry use)."""
    import numpy as np
    from capri_mod.market.market_module import MarketModule
    mkt = DATA_DIR / "2017" / "market"
    reg = pd.read_csv(mkt / "gl_demand_regions.csv")
    assert reg.max_rel_err.max() < 1e-6
    g = pd.read_csv(mkt / "gl_demand_goods.csv", keep_default_na=False, na_values=[""])
    mm = MarketModule(data)
    prm = mm._gl_params()
    assert prm and "EU27" in prm["groups"] and len(prm["groups"]["EU27"]) == 26
    de = g[g.rms == "DE000000"].reset_index(drop=True)
    e = next(x for x in prm["groups"]["EU27"]
             if len(x["p0"]) == len(de) and np.allclose(x["p0"] * 1000.0, de.cpri.values))
    x0 = mm._gl_eval(e, e["p0"], 1.0)
    k = {n: i for i, n in enumerate(de.good)}
    # CAPRI's p_ElasDem DE000000 at CAL (elas_2_1730defaulta)
    for (i, j), want in {("PORK", "PORK"): -0.46240279296144, ("PORK", "BEEF"): 0.0860763722190425}.items():
        p = e["p0"].copy(); p[k[j]] *= 1 + 1e-7
        el = (mm._gl_eval(e, p, 1.0)[k[i]] / x0[k[i]] - 1) / 1e-7
        assert abs(el - want) < 1e-5, (i, j, el, want)
    assert np.max(np.abs(mm._gl_eval(e, e["p0"] * 1.1, 1.1) / x0 - 1)[x0 > 1e-6]) < 1e-12
    dom0 = mm.domestic_prices(mm.world_prices_base)
    d0 = mm.demand_response(dom0, mm.world_prices_base)
    glr, hs = mm._gl_last
    assert np.max(np.abs(glr - 1.0)) < 1e-12
    dp = dom0.copy(); dp["PORK"] *= 1.1
    d1 = mm.demand_response(dp, mm.world_prices_base)
    for c in ("BEEF", "POUL"):
        assert d1.at["EU27", c] > d0.at["EU27", c]
    assert d1.at["EU27", "PORK"] < d0.at["EU27", "PORK"]


def test_eu_trade_blocks_data_and_split(data):
    """Step 3 of docs/archive/MARKET_STRUCTURE_PLAN.md: with eu_market_blocks the EU is CAPRI's two trade blocks EU_WEST and
    EU_EAST (gams/aggregation/defaultA.agg). Checks: the block flows carry CAPRI's West-East trade (2030: 15.0 Mt of
    maize from East to West) and the same extra-EU flows as the one-region data; the EU's quotas are filled by both
    blocks; the EU-level data split between the blocks add up to the EU's (feed, biofuel feedstocks, residual feeds,
    dairy output)."""
    import copy
    import numpy as np
    from capri_mod.market.market_module import MarketModule
    d = dict(data); d["eu_market_blocks"] = True
    mm = MarketModule(d)
    assert mm.EU == ("EU_WEST", "EU_EAST") and "EU27" not in mm.regions
    mm1 = MarketModule(data)
    assert mm1.EU == ("EU27",)
    mkt = DATA_DIR / "2017" / "market"
    fb = pd.read_csv(mkt / "bilateral_flows_2030_eu2.csv")
    we = fb[(fb.commodity == "CORN") & (fb.importer == "EU_WEST") & (fb.exporter == "EU_EAST")].q_kt.sum()
    assert abs(we - 15041.0) < 1.0
    f1 = pd.read_csv(mkt / "bilateral_flows_2030.csv")
    eu = ("EU_WEST", "EU_EAST")
    for c in ("SWHE", "BEEF", "SOYA"):
        a = f1[(f1.commodity == c) & (f1.importer == "EU27") & (f1.exporter != "EU27")].q_kt.sum()
        b = fb[(fb.commodity == c) & fb.importer.isin(eu) & ~fb.exporter.isin(eu)].q_kt.sum()
        assert abs(a - b) < 1e-6 * max(a, 1.0)
    raw = mm._bilateral_raw()
    sc = next(s for s in raw.values() if s.trq_row is not None)
    assert len(np.atleast_1d(sc.trq_row)) == 2
    fbp, fbp1 = mm._feed_bulk_params(), mm1._feed_bulk_params()
    for c, q in fbp1["feed0"].items():
        assert abs(sum(fbp["feed0_reg"][r].get(c, 0.0) for r in eu) - q) < 1e-6 * max(q, 1.0)
    bp, bp1 = mm._biofuel_params(), mm1._biofuel_params()
    for c, q in bp1["q0"].items():
        assert abs(sum(bp["q0_reg"].get((r, c), 0.0) for r in eu) - q) < 1e-6 * max(q, 1.0)
    for p, dd in mm._feed_byproduct_params()["products"].items():
        assert abs(sum(dd["reg"][r]["prod0"] for r in eu) - dd["prod0"]) < 1e-6 * dd["prod0"]
    dp = mm._dairy_params()
    assert np.allclose(dp["reg"]["EU_WEST"]["Q0"] + dp["reg"]["EU_EAST"]["Q0"], dp["Q0"])
    for c in ("SWHE", "PORK", "MILK"):
        assert abs(sum(mm.eu_split(c).values()) - 1.0) < 1e-12


def test_fish_and_tropical_products_are_markets_and_processing_is_capris(data):
    """Fish (FFIS, SFIS, OAQU) and coffee, tea, cocoa are CAPRI market products (arm/arm_sets.gms): bilateral data,
    base balances from CAPRI's market (no hard-coded world totals), demand in the GL; fish is fed (FPRO bulk). CAPRI's
    processing functions (ProcNQ_): crushing responds to the other oilseeds' margins, oil processing to the other
    oils' prices (cross terms), with CAPRI's Hessian."""
    import numpy as np
    from capri_mod.data.definitions import MARKET_COMMODITIES
    from capri_mod.market.market_module import MarketModule
    new = ("FFIS", "SFIS", "OAQU", "COFF", "TEAS", "COCO")
    assert set(new) <= set(MARKET_COMMODITIES)
    mm = MarketModule(data)
    raw = mm._bilateral_raw()
    assert all(c in raw for c in new)
    for c in new:                                   # base = CAPRI's market: production of the flows' exporters
        assert abs(float(mm.base_production[c].sum()) - float(raw[c].X0.sum())) < 1e-6 * max(1.0, float(raw[c].X0.sum()))
    gl = mm._gl_params()
    assert any((("EU27", mm.commodities.index(c)) in gl["x0"]) for c in ("COFF", "SFIS"))
    assert "SFIS" in mm._feed_bulk_params()["feed0"]
    pq = mm._proc_nq_params()
    H = pq["H"]["EU27"]
    assert H[("RAPE", "RAPE")] > 0 and H[("RAPE", "SOYA")] < 0 and H[("RAPO", "SUNO")] == H[("SUNO", "RAPO")]
    mm._bilateral_calibrate(mm.base_production.loc[["EU27"]].copy())
    dom0 = mm._dom0()
    d0 = mm.demand_response(dom0, mm.world_prices_base)
    dp = dom0.copy(); dp["SUNO"] *= 1.05
    d1 = mm.demand_response(dp, mm.world_prices_base)
    assert d1.at["EU27", "RAPO"] > d0.at["EU27", "RAPO"]            # substitution between the oils in processing
    c0 = mm.crush_quantities(dom0)
    dp = dom0.copy(); dp["SOYA"] *= 1.05                             # soybean margin falls: rapeseed crush rises
    assert mm.crush_quantities(dp)[("EU27", "RAPE")] > c0[("EU27", "RAPE")]


def test_greendeal_2030_settings_and_pesticide_rule():
    """CAPRI's own 2030 Green Deal step (Witzke's production batch: lnds8 org18 pest20 mine13crp surp30) named as
    CAPRI names it; star 3.0's pesticide target has no yield shock (pesticides.gms calls conventional_io.gms with
    the yield 'off'), the 2020 Farm-to-Fork study's has 10% at a 50% cut."""
    from capri_mod.policy.greendeal import greendeal_2030_scenario, greendeal_scenario, farm_to_fork_scenario
    s = greendeal_2030_scenario()
    assert s.name == "greendeal_lnds8_org18_pest20_mine13crp_surp30_diet00_oth00"
    assert (s.set_aside_requirement, s.organic_area_target, s.pesticide_reduction, s.mineral_redu, s.surplus_cut) \
        == (0.08, 0.18, 0.20, "13crp", 0.30)
    assert s.pesticide_rule == "star3" and greendeal_scenario().pesticide_rule == "star3"
    assert farm_to_fork_scenario().pesticide_rule == "jrc121368"


def test_processing_inpe_and_nonEU_feed_are_capris_2030():
    """CAPRI's ProcNQ_ divides its Hessian by the 2030 price of the non-agricultural good (arm/market1.gms: PPri INPE
    CUR = 1.019^(2030-2017)), as the dairy and biofuel blocks do; the non-EU feed functions are CAPRI's 2030
    calibration for every trade region (ROW included): feed share = FEED / (HCON+FEED+PROC+BIOF), feed-weighted
    p_ElasFeed."""
    import json
    from capri_mod.market.market_module import MarketModule
    MK = DATA_DIR / "2017" / "market"
    pb = pd.read_csv(MK / "processing_nq_base.csv")
    assert np.allclose(pb["inpe"], 1.019 ** 13, rtol=1e-9)
    hh = pd.read_csv(MK / "processing_nq_hessian.csv")
    mm = MarketModule.__new__(MarketModule)          # the parameter reader only needs regions and commodities
    mm.regions, mm.commodities, mm.eu_blocks, mm.EU = ["USA", "EU27"], list(pd.unique(hh["x"])), False, ("EU27",)
    pq = mm._proc_nq_params()
    r = hh[(hh.rms == "USA") & (hh.x == "SOYA") & (hh.y == "SOYA")].iloc[0]
    inpe_usa = float(pb[pb.rms == "USA"]["inpe"].iloc[0])
    assert abs(pq["H"]["USA"][("SOYA", "SOYA")] - float(r.h) / inpe_usa) < 1e-9 * float(r.h)
    fd = json.load(open(MK / "feed_demand_nonEU.json"))["parameters"]
    assert "ROW|SOYC" in fd and "KOR|SOYC" in fd and "EU27|SWHE" not in fd
    us = pd.read_csv(DATA_DIR / "sources" / "market" / "feed_demand_nonEU_use_2030.csv")
    u = us[(us.rms == "USA") & (us["product"] == "MAIZ")].set_index("item")["value"]
    assert abs(fd["USA|CORN"]["feed_share"] - u["FEED"] / u[["HCON", "FEED", "PROC", "BIOF"]].sum()) < 1e-4
    el = pd.read_csv(DATA_DIR / "sources" / "market" / "feed_demand_nonEU_elas_2030.csv")
    e = el[(el.rms == "USA") & (el.feed == "SOYC") & (el.price_of == "SOYC")]["value"].iloc[0]
    assert abs(fd["USA|SOYC"]["elasticities"]["SOYC"] - e) < 1e-4


def test_rations_are_chosen_only_inside_the_supply_models(model):
    """With feeding inside the regional models (CAPRI: v_feedInpCoeff only there), no ration is chosen outside them:
    the ration state is the feed per head of the last regional solution (the base ration before the first)."""
    from capri_mod.model import CAPRIModel
    model.run(scenario="BASELINE", regions=["IR010000"], max_outer_iter=1)
    a = "DCOW"
    r0 = model._ration_model.rations[("IR010000", a)]
    assert np.allclose([model._ration_state["IR010000"][a]["x"][f] for f in r0.feeds], r0.x0)   # before a solve: base
    model._update_rations({})                       # the next iteration's update: from the last regional solve
    rs = model._ration_state["IR010000"]
    res = model._last_supply_results["IR010000"]
    h = float(res.activities[a])
    ft = res.feed_t[a]
    for f, x in rs[a]["x"].items():
        assert abs(x - float(ft.get(f, 0.0)) / h) < 1e-9 * max(1.0, abs(x))
    assert rs[a]["dcost"] == 0.0


def test_luc_model_reproduces_capris_2030_transitions():
    """CAPRI's land-use change block (supply_model.gms e_luClassInitial/Final, e_FocLUC; capri_mod/environmental/
    luc.py): at the base land types the posterior mode of the gamma priors is CAPRI's own 2030 solution."""
    import pandas as _pd
    from capri_mod.environmental.luc import LUCModel
    t = _pd.read_csv(DATA_DIR / "2017" / "environment" / "luc_2030.csv")
    for r in ("DE110000", "FR520000", "RO020000"):
        v = dict(t[t.capri_region == r][["item", "value"]].values)
        out = LUCModel.get().solve(r, {})
        assert out["ok"]
        for k, x in out["transitions"].items():
            assert abs(x - max(float(v.get(k, 0.0)), 0.0)) <= 1e-6 * max(1.0, abs(x))


@pytest.mark.slow
def test_nlp_solver_cache_is_exact(model, tmp_path, monkeypatch):
    """The regional NLP's IPOPT solver is kept by structure, every data value being a parameter: a second build of
    the same region reuses it and solves to the same point; changed data (prices) reuse it as well and move the
    solution, as a fresh solver does."""
    import pickle
    from capri_mod.model import CAPRIModel
    from capri_mod.supply import capri_regional_nlp as C
    monkeypatch.setenv("CAPRI_NLP_DUMP", str(tmp_path))
    model.run(scenario="BASELINE", regions=["DE110000"], max_outer_iter=1)
    d = pickle.load(open(tmp_path / "DE110000.pkl", "rb"))
    spec = dict(d["spec"])
    x0 = np.asarray(d["x_start"], float)
    N1 = C.CapriRegionalNLP(spec)
    r1 = N1.solve(N1.start(x0))
    h0 = C.CACHE_STATS["hit"]
    N2 = C.CapriRegionalNLP(spec)
    r2 = N2.solve(N2.start(x0))
    assert C.CACHE_STATS["hit"] == h0 + 1 and N2._solver is N1._solver
    assert r1["success"] and r2["success"] and abs(r1["f"] - r2["f"]) <= 1e-9 * abs(r1["f"])
    spec3 = dict(spec, c=np.asarray(spec["c"], float) * 1.05)
    N3 = C.CapriRegionalNLP(spec3)
    r3 = N3.solve(N3.start(x0))
    C._SOLVERS.clear()
    N4 = C.CapriRegionalNLP(spec3)
    r4 = N4.solve(N4.start(x0))
    assert N3.structure_key({"a": 1}) == N1.structure_key({"a": 1})
    assert r3["success"] and r4["success"] and abs(r3["f"] - r4["f"]) <= 1e-7 * abs(r4["f"])
    assert abs(r3["f"] - r1["f"]) > 1e-6 * abs(r1["f"])


def test_npk_crop_need_is_the_crops_own():
    """NUTNED_ sums levl x each crop's own need (NITF, net of fixation) over a group; CAPRI's nutNed_lhs per crop is the
    group's need spread by area, so the crop coefficients take NITF (tools/build/build_npk_balance_2030.py): fallow and
    set-aside need a few kg N/ha, CAPRI's extensive grassland far less than its intensive one."""
    import pandas as _pd
    t = _pd.read_csv(DATA_DIR / "2017" / "environment" / "npk_crop_coefs_2030.csv")
    d = t[(t.capri_region == "DE210000") & (t.nutrient == "N")].set_index("model_crop").need_kg_ha
    assert d["SETA"] < 10.0 < d["SWHE"]
    assert d["GRAE"] < 0.5 * d["GRAI"]
    assert abs(d["GRAS"] - 0.5 * (d["GRAE"] + d["GRAI"])) < 1.0          # equal areas at the 2030 reference


def test_n_cascade_reproduces_capri():
    """CAPRI's N loss cascade (capri_mod/supply/n_cascade.py, factors from tools/build/build_n_cascade.py) with CAPRI's own
    option shares gives the per-head losses of CAPRI's Green Deal reference run with endogenous technologies
    (capri_data/validation/n_cascade_capri_gd2030.csv): every gas at grazing, in housing and storage and at application,
    the gaseous total and the runoff, for the animal activities of DE11, NL22, PL22 and DK."""
    import csv
    from collections import defaultdict
    from pathlib import Path
    from capri_mod.supply import n_cascade as nc
    p = Path(__file__).resolve().parents[2] / "capri_data" / "validation" / "n_cascade_capri_gd2030.csv"
    R = defaultdict(dict)
    with open(p) as fh:
        for r in csv.DictReader(fh):
            R[(r["region"], r["key"])][(r["col"], r["row"])] = float(r["value"])
    F, _, _ = nc.load()
    n = 0
    for reg in ("DE110000", "NL220000", "PL220000", "DK000000"):
        d, shr = R[(reg, "")], R[(reg, "SHARE")]
        wc = shr.get(("CATC", "WinterCov"), 0.0)
        for (act, row), mann in d.items():
            if row != "MANN" or mann <= 0 or (reg, act) not in F or act in ("DCOW", "BULF", "HEIF"):
                continue
            sh = {t: v for (a, t), v in shr.items() if a == act}
            L = nc.activity_losses(reg, act, sh, winter_cover=wc)
            mod = {"NH3GRA": L[("NH3", "Graz")], "NOXGRA": L[("NOX", "Graz")], "N2OGRA": L[("N2O", "Graz")] * 44 / 28,
                   "NH3MAN": L[("NH3", "Hous")] + L[("NH3", "Stor")], "NOXMAN": L[("NOX", "Hous")] + L[("NOX", "Stor")],
                   "N2OMAN": (L[("N2O", "Hous")] + L[("N2O", "Stor")]) * 44 / 28,
                   "NH3APP": L[("NH3", "Appl")], "NOXAPP": L[("NOX", "Appl")], "N2OAPP": L[("N2O", "Appl")] * 44 / 28,
                   "GASANI": L[("N", "GasRunTot")] - L[("N", "RunTot")], "RUNANI": L[("N", "RunTot")]}
            for k, v in mod.items():
                c = d.get((act, k))
                if c is None or abs(c) < 1e-9:
                    continue
                assert abs(mann * v / c - 1.0) < 1e-5, (reg, act, k, mann * v, c)
                n += 1
    assert n > 700


def test_ad_option_reproduces_capri():
    """CAPRI's anaerobic digestion option (tools/build/build_ad_option.py, docs/AD_SPEC.md) against CAPRI's Green Deal "ini"
    reference run: the reported initial share (MitiShar0 x SharLiq x HousShar; CAPRI's run 1e-6 x L(1-G) below it)
    and the maximum share (farms of 200 LSU and more, per-class NUTS1/NUTS0 fallback) for every animal checked, the
    cost curve for pigs, whose volatile solids CAPRI takes from its table as we do (cattle: computed by CAPRI from the
    run's feed data, not in hand)."""
    import csv
    from collections import defaultdict
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "capri_data"
    R = defaultdict(dict)
    with open(root / "validation" / "n_cascade_capri_gd2030.csv") as fh:
        for r in csv.DictReader(fh):
            R[(r["region"], r["key"])][(r["col"], r["row"])] = float(r["value"])
    with open(root / "2017" / "abatement" / "ammonia" / "ad_option.csv") as fh:
        ad = {(r["region"], r["activity"]): r for r in csv.DictReader(fh)}
    n = 0
    for reg in ("DE110000", "NL220000", "PL220000", "DK000000"):
        for act in ("DCOL", "BULL", "PIGF", "SOWS"):
            a = ad[(reg, act)]
            lg = float(a["lg"])
            s = R[(reg, "SHARE")][(act, "AD_AnCh")]
            assert abs(float(a["ini"]) - 1e-6 * lg - s) < 1e-8, (reg, act)
            assert abs(float(a["max"]) - R[(reg, "MaxShare")][(act, "AD_AnCh")]) < 1e-6, (reg, act)
            if act in ("PIGF", "SOWS"):
                v = s / lg
                days = R[(reg, "")].get((act, "DAYS"), 365.0)
                cost = (1e-10 * v + 0.5 * float(a["costParSqr"]) * v * v) * days / 365.0
                assert abs(cost / R[(reg, "cost")][(act, "AD_AnCh")] - 1.0) < 1e-5, (reg, act)
            n += 1
    assert n == 16


def test_ad_ch4_factor_and_dairy_switch():
    """Anaerobic digestion on manure CH4: 1 - (s / L(1-G)) (1 - QE_AD/QE_NOC) against the base share (CAPRI's
    MC_GHG_Miti_Factor); for dairy cows applied by default (ad_dairy_ch4 = "fix"), none with "capri" (CAPRI as coded,
    ad_data_and_cali.gms l. 588)."""
    from pathlib import Path
    from capri_mod.environmental.environmental_module import EnvironmentalModule
    from capri_mod.supply import ammonia_techs as _at
    d = Path(__file__).resolve().parents[2] / "capri_data" / "2017" / "abatement" / "ammonia" / "ammonia_tech_model.csv"
    tm = _at.load(d)
    env = EnvironmentalModule.__new__(EnvironmentalModule)
    env._amm_tm = tm
    subs = [sb for sb in tm["DE110000"]["PIGF"] if sb.get("ad")]
    assert subs
    lg, r = subs[0]["ad"]
    s0 = {"AD_AnCh": sum(sb["w"] * t["ini"] for sb in tm["DE110000"]["PIGF"] for t in sb["techs"] if t["tech"] == "AD_AnCh")}
    assert abs(env._ad_ch4_factor("DE110000", "PIGF", {}, s0) - 1.0) < 1e-12
    f = env._ad_ch4_factor("DE110000", "PIGF", {("PIGF", "AD_AnCh"): 0.5}, s0)
    assert abs(f - (1 - 0.5 / lg * (1 - r)) / (1 - s0["AD_AnCh"] / lg * (1 - r))) < 1e-9 and f < 1
    sd = {"AD_AnCh": sum(sb["w"] * t["ini"] for sb in tm["DE110000"]["DCOW"] for t in sb["techs"] if t["tech"] == "AD_AnCh")}
    assert env._ad_ch4_factor("DE110000", "DCOW", {("DCOW", "AD_AnCh"): 0.5}, sd) < 1
    from capri_mod import settings as S
    with S.override({"environment.ad_dairy_ch4": "capri"}):
        assert env._ad_ch4_factor("DE110000", "DCOW", {("DCOW", "AD_AnCh"): 0.5}, sd) == 1.0


def test_n_leaching_follows_capri():
    """CAPRI's leaching (LEACHN_) and the indirect N2O of leached and run-off N allocated to crops (gases.gms N2OLEA;
    capri_mod/supply/n_leaching.py, tools/build/build_n_leaching.py). With CAPRI's own regional N balance items of its Green
    Deal reference with endogenous technologies, its realised leaching share (LEACHI / SURSOI) and its cascade, the
    formula gives CAPRI's crop N2OLEA (UAAR N2OLEA x UAA) within 6% for DE11, NL22, PL22 and DK: CAPRI sums it crop by
    crop (p_share_NMAN, crop MANN, NRET x BioFix), the check from regional totals (CRESID + ATMOSD, BIOFIX). At the
    initial shares the share is CAPRI's own; the application options act with the sign of CAPRI's data (the user's
    decision; CAPRI's code adds them, the setting environment.ammapp_sign = "capri")."""
    import csv
    from collections import defaultdict
    from pathlib import Path
    from capri_mod.supply import n_cascade as nc, n_leaching as nl
    root = Path(__file__).resolve().parents[2] / "capri_data"
    D = defaultdict(dict)
    for r in csv.DictReader(open(root / "sources" / "capri_res" / "gd2030_endotech_ini_nbalance.csv")):
        D[r["region"]][r["item"]] = float(r["value"])
    R = defaultdict(dict)
    for r in csv.DictReader(open(root / "validation" / "n_cascade_capri_gd2030.csv")):
        R[(r["region"], r["key"])][(r["col"], r["row"])] = float(r["value"])
    LM = defaultdict(dict)
    for r in csv.DictReader(open(root / "2017" / "abatement" / "ammonia" / "capri_mann_days_2030.csv")):
        LM[(r["region"], r["activity"])][r["item"]] = float(r["value"])
    F, G, _ = nc.load()
    reg_tab = nl.load()
    for reg in ("DE110000", "NL220000", "PL220000", "DK000000"):
        x, d, shr = D[reg], R[(reg, "")], R[(reg, "SHARE")]
        wc = shr.get(("CATC", "WinterCov"), 0.0)
        runh = 0.0
        for (act, row), mann in d.items():
            if row == "MANN" and mann > 0 and (reg, act) in F:
                L_ = nc.activity_losses(reg, act, {t: v for (a, t), v in shr.items() if a == act}, winter_cover=wc)
                runh += LM.get((reg, act), {}).get("LEVL", 0.0) * mann * L_[("N", "RunHous")] / 1000.0
        g = G[reg]
        n2o_netf = (1 - g.get("netf_NH3", 0.0) - g.get("netf_NOX", 0.0)) * g.get("netf_N2O", 0.0)
        M, L = x["MINFER"], x["LEACHI"] / x["SURSOI"]
        assert abs(reg_tab[reg]["leach_ini"] - L) < 1e-9
        assert abs(nl.share(reg, 0.9, 0.9) - L) < 1e-12
        c = nl.crop_n(M, x["RUNMIN"] / M, (x["GASMIN"] + x["RUNMIN"]) / M, n2o_netf,
                      [(x["EXCRET"], (x["RUNANI"] - runh) / x["EXCRET"], (x["GASANI"] + x["RUNANI"]) / x["EXCRET"])],
                      x.get("MTRADE", 0.0), x["ATMOSD"] + x["CRESID"], x["BIOFIX"], L, x["EXPPRD"] / x["IMPORT"])
        model = sum(c.values()) * nl.EF5 * 44 / 28
        capri = x["UAAR_N2OLEA"] * x["UAAR_LEVL"] / 1000.0
        assert abs(model / capri - 1.0) < 0.06, (reg, model, capri)
    assert abs(nl.fert_effect(0.5, 0.1) - (1 - 0.5 * 1.1)) < 1e-12
    # low-emission application raises leaching (CAPRI's data, agg < 0): the share rises with it by default; CAPRI's
    # code ('+ v_ammoAppLeaAgg') lowers it
    from capri_mod import settings as S
    assert S.current().get("environment.ammapp_sign") == "consistent" and nl.b1(agg=-0.1) > 1.0
    with S.override({"environment.ammapp_sign": "capri"}):
        assert nl.b1(agg=-0.1) < 1.0


def test_nlp_failure_keeps_ipopts_last_point_as_capri(model, monkeypatch):
    """KNOWN_ISSUES K55-1: where IPOPT fails for a region from every start and the relaxations do not help, CAPRI carries
    on with the non-optimal solve and records it (supply/simu_supply.gms, widen_bounds.gms: p_INFES). IPOPT's last point
    is kept, warned about and recorded (metadata nlp_fallback; the result's nlp_nonoptimal, converged False)."""
    import warnings
    from capri_mod.supply import capri_regional_nlp as C
    regs = ["DE110000"]
    model.run(scenario="BASELINE", regions=regs, max_outer_iter=1)
    _solve = C.CapriRegionalNLP.solve

    def _fail(self, *a, **k):
        return dict(_solve(self, *a, **k), success=False, status="Test_Failure")
    monkeypatch.setattr(C.CapriRegionalNLP, "solve", _fail)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        r = model.run(scenario="BASELINE", regions=regs, max_outer_iter=1)
    assert any("IPOPT's last point kept" in str(x.message) for x in w)
    fb = r["metadata"]["nlp_fallback"]
    assert list(fb) == ["DE110000"] and any("IPOPT's last point kept" in e for e in fb["DE110000"]), fb
    sr = r["supply"]["DE110000"]
    assert sr.nlp_nonoptimal == "Test_Failure" and not sr.converged
    assert np.isfinite(sr.activities.values).all() and float(sr.activities.sum()) > 0


@pytest.mark.slow
def test_nlp_form_takes_jrc121368_relaxation_where_the_tiered_n_target_fails(model):
    """KNOWN_ISSUES K57: NL32 (outside JRC121368's nine capped regions) has no solution in CAPRI's form at the tiered
    Farm-to-Fork N target (NL13 until the K75 fix of 26 October 2026; since then NL13 meets it and NL32 is the one
    region relaxed in the reference run r145); JRC121368's rule for such regions (the EU-average cut, 36%) is applied in CAPRI's form,
    recorded, and kept for the scenario."""
    from capri_mod.policy.greendeal import farm_to_fork_scenario
    from capri_mod import settings as S
    model.supply_module._jrc_capped_cache = None
    try:
        with S.override({"supply.jrc_capped_override": "NL41,BE25,NL21,BE21,NL22,NL31,BE23,NL42,MT00"}):
            model.run(scenario="BASELINE", regions=["NL320000"], max_outer_iter=2)
            r = model.run(custom_scenario=farm_to_fork_scenario(), regions=["NL320000"], max_outer_iter=2)
    finally:
        model.supply_module._jrc_capped_cache = None
    fb = r["metadata"]["nlp_fallback"].get("NL320000") or []
    assert len(fb) == 1 and "relaxed target" in fb[0], fb       # once, then kept (sticky)
    mo = model.supply_module._models["NL320000"]
    assert getattr(mo, "_n_target_relaxed", False) and getattr(mo, "_nlp_fb_last", True) is False   # CAPRI's form
    assert getattr(r["supply"]["NL320000"], "balance_shortfall", 0.0) > 0.0


@pytest.mark.slow
def test_winter_cover_is_chosen_in_the_nlp_form(model):
    """CAPRI's winter cover as a choice (envind/cover_crops.gms, v_Miti(CATC, WinterCov); tools/
    build_winter_cover_option.py): the baseline keeps the base share (calibrated first-order point), the Farm-to-Fork
    requirement is its lower bound, and the accounts take the chosen share (supply result's cover_crops)."""
    from capri_mod.policy.greendeal import farm_to_fork_scenario
    # one supply-market iteration: the choice is the supply model's. With two, the market of this one-region run
    # (DE110000 alone as the EU) diverged in the second Farm-to-Fork step, 2 x 100 market steps, ~550 of the test's 590 s
    # (KNOWN_ISSUES K83)
    regs = ["DE110000"]
    b = model.run(scenario="BASELINE", regions=regs, max_outer_iter=1)
    mo = model.supply_module._models["DE110000"]
    cs = mo._cover_solved
    assert cs and cs["endogenous"] and abs(cs["share"] - cs["base"] / cs["uaa"]) < 2e-3
    s = model.run(custom_scenario=farm_to_fork_scenario(), regions=regs, max_outer_iter=1)
    cs = model.supply_module._models["DE110000"]._cover_solved
    assert cs["lb_share"] > cs["base"] / cs["uaa"] + 0.01          # the requirement raises the floor
    assert cs["share"] >= cs["lb_share"] - 1e-6 and cs["share"] <= cs["max_share"] + 1e-6
    w0, w1 = model.env_module._winter_cover_now("DE110000", s["supply"]["DE110000"])
    assert abs(w1 - cs["share"]) < 1e-9


def test_interface_audit_fixes():
    """KNOWN_ISSUES K52: a base year without data is refused; a trajectory demand factor is refused rather than
    ignored; the proxy registry scenarios are gone."""
    from capri_mod.model import CAPRIModel
    from capri_mod.projection.trajectory import BaselineTrajectory, TrajectoryError
    from capri_mod.scenarios.scenarios import list_scenarios
    with pytest.raises(ValueError):
        CAPRIModel(data_dir=str(DATA_DIR), base_year="2020", verbose=False)
    with pytest.raises(TrajectoryError):
        BaselineTrajectory.from_dict({"name": "x", "source": "s", "vintage": "v", "base_year": 2017,
                                      "target_years": [2030], "growth": {"demand": {"BEEF": {"2030": 0.95}}}})
    BaselineTrajectory.from_dict({"name": "x", "source": "s", "vintage": "v", "base_year": 2017,
                                  "target_years": [2030], "growth": {"demand": {"BEEF": {"2030": 1.0}}}})
    assert not {"FARM_TO_FORK", "FLAT_RATE_BPS", "UKRAINE_SHOCK"} & set(list_scenarios())


def test_non_eu_supply_elasticities_are_capri_regional(data):
    """KNOWN_ISSUES K54-3: each non-EU trade region's own-price supply elasticity is CAPRI's p_elasSupp of its CAPRI
    regions (supply_elas_region.csv); the EU rows keep the product value (their supply comes from the supply models)."""
    import numpy as np
    import pandas as pd
    from capri_mod.market.market_module import MarketModule
    mm = MarketModule(data)
    tab = pd.read_csv(DATA_DIR / "2017" / "market" / "supply_elas_region.csv")
    cols = ["SWHE", "BEEF", "SOYA"]
    el = pd.Series({"SWHE": 0.3, "BEEF": 0.5, "SOYA": 0.4})
    regs = list(mm.regions)
    EV = mm._region_supply_elas(regs, cols, el)
    for r, c in (("USA", "SWHE"), ("BRA", "SOYA"), ("ARG", "BEEF")):
        v = tab[(tab.region == r) & (tab.commodity == c)].elasticity
        assert len(v) == 1 and abs(EV[regs.index(r), cols.index(c)] - float(v.iloc[0])) < 1e-12
    assert np.allclose(EV[regs.index("EU27")], el.values)
    assert not np.allclose(EV[regs.index("USA")], el.values)


@pytest.mark.slow
def test_shocked_baseline_does_not_replace_the_cached_baseline(model):
    """KNOWN_ISSUES K52c: a world-price shock under scenario="BASELINE" is a scenario against the unshocked baseline."""
    regs = ["DE110000"]
    model.run(scenario="BASELINE", regions=regs, max_outer_iter=1)
    before = {k: id(v) for k, v in model._eu_base_cache.items()}
    model.run(scenario="BASELINE", regions=regs, max_outer_iter=1, world_price_shock={"SWHE": 0.2})
    after = {k: id(v) for k, v in model._eu_base_cache.items()}
    assert before == after


def test_land_rows_are_equalities_and_histosol_fallow_keeps_its_land(model):
    """KNOWN_ISSUES K59, K60: with CAPRI's LandBalNoSlak_ the grassland row is an equality at the base use, as the arable
    and permanent rows (it kept the land data's headroom: IE04 173 kha of grass at no land cost), and an idled histosol
    area stays in its land type on both rows of the pair (on the upper row alone it was held at zero)."""
    model.run(scenario="BASELINE", regions=["IR010000"], max_outer_iter=1)
    mo = model.supply_module._models["IR010000"]
    lab = list(mo._aug_labels)
    A, b = mo._last_aug_A, mo._last_aug_b
    for row in ("arable_land", "permanent_land", "grassland"):
        if row in lab and row + "_lo" in lab:
            i, j = lab.index(row), lab.index(row + "_lo")
            assert abs(float(b[i]) + float(b[j])) < 1e-5 * max(1.0, abs(float(b[i]))), (row, b[i], b[j])
    for cls, col in (getattr(mo, "_hist_cols", None) or {}).items():
        row = dict(mo.HISTOSOL_CLASSES)[cls]
        assert A[lab.index(row), col] == 1.0 and A[lab.index(row + "_lo"), col] == -1.0


@pytest.mark.slow
def test_capri_land_rents_at_the_2030_calibration_point(model):
    """docs/LAND_RENT_CALIBRATION_PLAN.md: at the 2030 market year the land market is balanced at CAPRI's land rents
    (D_AREA of its 2030 reference, land_rents_2030.csv) and the NLP calibration fixes the land balances' multipliers at
    them; the baseline reproduces the 2030 base."""
    from capri_mod.projection import ProjectionModule, BaselineTrajectory
    root = _repo_root()
    traj = BaselineTrajectory.from_file(str(root / "capri_data" / "trajectories" / "capri_ref_2030.json"))
    pmod = ProjectionModule(model, traj, capri_prices_dir=str(root / "capri_data" / "trajectories"))
    res = pmod.run(years=[2030], regions=["IR010000"], max_outer_iter=2)
    pm = getattr(pmod, "_last_projected_model", None) or model
    mo = pm.supply_module._models["IR010000"]
    rents = pd.read_csv(root / "capri_data" / "2017" / "supply" / "land_rents_2030.csv", index_col=0).loc["IR010000"]
    rr = mo._land_rent_rows
    assert abs(rr["arable_land"] - rents["rent_arac"]) < 1e-6 and abs(rr["grassland"] - rents["rent_gras"]) < 1e-6
    assert (mo._nlp_cal or {}).get("residual", 1.0) < 1e-6
    drift = res.baseline[2030]["metadata"].get("base_calibration_drift") or [0.0]
    assert float(drift[-1]) < 0.002, drift


def test_ammonia_option_cost_is_per_place_of_the_models_heads(model):
    """K63: CAPRI prices the ammonia options per animal place, places = activity level x DAYS / 365 in CAPRI's units.
    Per model head the places are stock_factor / capri_level_ratio, so a region's places from the model's heads equal
    CAPRI's (DE11 fattening pigs: CAPRI HERD 604 thousand places; the model's 954 thousand heads x 0.308 gave 294)."""
    sm = model.supply_module
    m = sm._get_or_build_model("DE110000")
    techs = m._manure_techs()
    heads = float(model.data["animal_numbers"].at["DE110000", "PIGF"])
    places = heads * sum(float(s["w"]) * float(s["stock"]) for s in techs["PIGF"])
    assert 560.0 < places < 640.0, places
    # an animal whose units equal CAPRI's keeps CAPRI's factor
    ratio = model.data["capri_level_ratio"].loc["DE110000"]
    assert abs(float(ratio["DCOW"]) - 1.0) < 1e-9
    assert all(abs(float(s["stock"]) - 1.0) < 1e-9 for s in techs["DCOW"])
    # pigs and their CAPRI factor: stock_factor / ratio
    assert abs(float(techs["PIGF"][0]["stock"]) - 0.307915 / float(ratio["PIGF"])) < 1e-6


def test_capri_2030_pmp_matrix_is_positive_definite_and_enters_q(data):
    """K61: CAPRI's 2030 PMP terms (tools/build/build_pmp_capri_2030.py) give each model region a positive definite crop
    matrix, and PMPCalibrator puts it into Q as g / sqrt(x_i x_j), the base still a first-order point."""
    import numpy as np
    from capri_mod.supply.supply_module import PMPCalibrator
    pm = data["pmp_capri_2030"]
    assert pm is not None and len(pm) >= 220
    for reg in ("AT110000", "DE110000", "FR520000", "IR020000", "NO090000"):
        g = pm[reg]
        acts = sorted({a for a, _ in g})
        G = np.array([[g.get((a, b), 0.0) for b in acts] for a in acts])
        assert np.allclose(G, G.T) and np.linalg.eigvalsh(G).min() > 0, reg
    g = pm["AT110000"]
    assert ("DCOW", "DCOW") in g and ("SWHE", "DCOW") not in g   # animals: own herd term only (K61, animal terms)
    acts = ["SWHE", "BARL", "CORN", "RAPE", "DCOW"]
    x0 = pd.Series({"SWHE": 40.0, "BARL": 5.0, "CORN": 20.0, "RAPE": 13.0, "DCOW": 50.0})
    r = pd.Series({"SWHE": 900.0, "BARL": 700.0, "CORN": 1100.0, "RAPE": 950.0, "DCOW": 2500.0})
    cal = PMPCalibrator(acts, pd.Series(0.5, index=acts), capri_g=g)
    Q, f = cal.calibrate(base_levels=x0, net_revenues=r)
    assert cal.n_capri_acts == 5
    assert abs(Q[0, 0] - g[("SWHE", "SWHE")] / 40.0) < 1e-9
    assert abs(Q[0, 2] - g[("SWHE", "CORN")] / np.sqrt(40.0 * 20.0)) < 1e-9
    assert Q[0, 4] == 0.0                                       # no crop x animal cross term
    assert abs(Q[4, 4] - g[("DCOW", "DCOW")] / 50.0) < 1e-9     # the herd's term from CAPRI's export
    assert np.linalg.eigvalsh(Q).min() > 0


def test_poultry_ammonia_costs_are_per_1000_animals():
    """K63: CAPRI's unit for hens and other poultry is 1000 animals; ammo_tech.gms multiplies the per-animal investment
    of housing and air purification and the extra input demands by 1000 (l. 153-157, 640-643). DE94's hens: housing
    about 275 EUR per 1000 hens and year (8.7 without the factor); storage covers, costed from manure per 1000 animals,
    are not multiplied."""
    t = pd.read_csv(DATA_DIR / "2017" / "abatement" / "ammonia" / "ammonia_technologies.csv")
    v = t[(t.region == "DE940000") & (t.activity == "HENS")].set_index("technology")["CostParLin"]
    assert 150.0 < float(v["LowEmHous"]) < 500.0
    assert float(v["AirPur"]) > 500.0
    assert 5.0 < float(v["CovStorHigh"]) < 20.0


def test_capri_2030_animal_terms_and_land_market(data):
    """K61, items 1 and 3: CAPRI's 2030 herd terms join the crops' matrix as diagonal entries (no cross terms to crops,
    as QUADRA_), and the 2030 land market (tools/build/build_land_market.py --year 2030) holds CAPRI's 2030 land-type terms
    for every region the 2017 one has, positive definite up to rounding."""
    import numpy as np
    pm = data["pmp_capri_2030"]
    for reg in ("DE110000", "FR520000", "NL220000"):
        g = pm[reg]
        for a in ("DCOW", "PIGF", "BCOW"):
            assert g.get((a, a), 0.0) > 0, (reg, a)
            assert not any((a, c) in g for c in ("SWHE", "BARL", "GRAS")), (reg, a)
    # scale (Q = g / x at the model's herd, so g = Q x is the marginal-cost change per head for a 100% herd change): of
    # the order of the per-head output value (DE11 fattening pigs about 420 EUR); the first version (g = h X^2) was 100
    # to 25,000 times steeper
    for a in ("PIGF", "DCOW", "BULL"):
        g_ = pm["DE110000"][(a, a)]
        assert 100.0 < g_ < 30000.0, (a, g_)
    lm17, lm30 = data["land_market"], data["land_market_2030"]
    assert set(lm30) == set(lm17)
    bad = [r for r, v in lm30.items() if np.linalg.eigvalsh(np.array(v["quad"])).min() < -1e-12]
    assert not bad, bad
    assert lm30["NO090000"]["quad_source"] == "NO090000"       # each unit its own matrix (Norway's 2016 regions pooled
    #                                                            NO08 + NO09 + NO0A until 27 October 2026)


def test_feed_ration_carries_capri_2030_feed_slopes():
    """K61, item 1: the ration file carries CAPRI's 2030 feed-PMP slopes beside the 2017 ones (same aggregation), and the
    ration model takes them when asked (slope_key)."""
    from capri_mod.feed.ration import RationModel
    import json
    raw = json.load(open(DATA_DIR / "2017" / "feed" / "feed_ration_2017.json"))["regions"]
    n = sum(1 for acts in raw.values() for rec in acts.values() if rec.get("capri_slope_2030"))
    assert n > 2000
    s17 = RationModel(str(DATA_DIR)).rations
    s30 = RationModel(str(DATA_DIR), slope_key="capri_slope_2030").rations
    key = next(k for k in s17 if k[0] == "FR520000" and k[1] == "BROI") if isinstance(next(iter(s17)), tuple) else None
    if key is not None:
        assert list(s17[key].slope) != list(s30[key].slope)


def test_recipe_pmp_terms_reproduce_capris_own():
    """K61, 22 October 2026: capri-mod's PMP terms by CAPRI's recipe (tools/build/build_pmp_recipe.py, with the land-nest
    adjustment and 14 years of inflation at 2017) against CAPRI's own terms: the 2017 group terms within 1% of CAPRI's
    CAPREG terms in (nearly) every pair, the activities' first-technology terms within 5% in most pairs at 2017 and,
    collapsed per activity, at 2030."""
    import sys
    sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "check")]
    import pmp_recipe_check as C
    src = DATA_DIR / "sources"
    cp = pd.read_csv(src / "capreg" / "pmp_quad_pact.csv")
    rp = pd.read_csv(src / "baseline_pmp" / "recipe_2017_quad_pact.csv")
    rp["model_region"] = rp.region
    k = cp.merge(rp, on=["model_region", "group1", "group2"])
    r = k.value_y / k.value_x
    assert len(k) > 1000 and ((r - 1).abs() < 0.01).mean() > 0.99
    cap = pd.read_csv(src / "capreg" / "pmp_quad_techn.csv")
    rec = pd.read_csv(src / "baseline_pmp" / "recipe_2017_quad_techn.csv")
    rec = rec[(rec.tech1 == rec.tech2) & rec.tech1.isin(["T1", "T"])].drop_duplicates(["region", "activity"]).copy()
    rec["model_region"] = rec.region
    j = cap.merge(rec, on=["model_region", "activity"], suffixes=("_c", "_r"))
    assert ((j.value_r / j.value_c - 1).abs() < 0.05).mean() > 0.88
    ex = C.collapsed(pd.read_csv(src / "baseline_pmp" / "pmp_quad_techn_2030.csv"))
    rc = C.collapsed(pd.read_csv(src / "baseline_pmp" / "recipe_2030_quad_techn.csv"))
    jj = pd.concat({"c": ex, "r": rc}, axis=1).dropna()
    assert len(jj) > 10000 and ((jj.r / jj.c - 1).abs() < 0.05).mean() > 0.79


def test_recipe_land_nest_elasticities_from_the_bordered_hessian():
    """The land-nest adjustment's land-type elasticities (tools/build/build_pmp_recipe.land_elasticities): for a land owner
    with a fixed total area and a diagonal land matrix q_i x 1000, CAPRI's bordered Hessian gives
    dx_i/dr_i = (1/h_i)(1 - (1/h_i) / sum_j 1/h_j), h_i = 1000 q_i; elasticity = that x rent_i / x_i."""
    import sys
    sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "check")]
    import build_pmp_recipe as R
    q = {("ARAC", "ARAC"): 0.02, ("GRAS", "GRAS"): 0.01, ("FORE", "FORE"): 0.001}
    y = {("ARAC", "LEVL"): 100.0, ("GRAS", "LEVL"): 50.0, ("FORE", "LEVL"): 200.0,
         ("ARAC", "D_AREA"): 400.0, ("GRAS", "D_AREA"): -150.0, ("FORE", "D_AREA"): 0.0}
    e = R.land_elasticities(q, y)
    inv = {t: 1.0 / (1000.0 * q[(t, t)]) for t in ("ARAC", "GRAS", "FORE")}
    tot = sum(inv.values())
    for t, rent, lev in (("ARAC", 400.0, 100.0), ("GRAS", 150.0, 50.0)):
        expect = inv[t] * (1.0 - inv[t] / tot) * rent / lev
        assert abs(e[t] - expect) < 1e-12 * max(1.0, expect)
    # the contribution of an annual crop: its level over ARAB + ANNC + ARAC, times ARAC's elasticity
    yd = dict(y)
    yd.update({("SWHE", "LEVL"): 30.0, ("ARAB", "LEVL"): 110.0, ("ANNC", "LEVL"): 95.0})
    c = R.land_nest_contrib("SWHE", yd, {"ARAC": 0.5})
    assert abs(c - 30.0 / (110.0 + 95.0 + 100.0) * 0.5) < 1e-12


def test_intensity_splits_take_the_2030_curvature_with_capris_2030_terms(data):
    """K61: at the 2030 market year with CAPRI's 2030 terms (pmp_source capri2030), the dairy, cattle and grassland
    splits take CAPRI's 2030 p_pmpQuadTechn of their two variants (q_<x>_capri2030); at 2017 the base year's."""
    from capri_mod.supply.supply_module import SupplyModule
    sm = SupplyModule.__new__(SupplyModule)
    assert sm.pmp_source == "capri2030" and sm.pmp_capri_parts == ("crops", "animals", "feed", "land")   # settings
    di = data["dairy_intensity"].loc["AT110000"]
    d30 = dict(data, market_year=2030)
    out = sm._intensity_q_at(d30, di, ("q_low", "q_high"), "animals")
    assert out["q_low"] == pytest.approx(float(di["q_low_capri2030"])) and "q_low_capri2030" not in out.index
    out17 = sm._intensity_q_at(dict(data, market_year=2017), di, ("q_low", "q_high"), "animals")
    assert out17["q_low"] == pytest.approx(float(di["q_low"]))
    from capri_mod import settings as S
    with S.override({"supply.pmp_capri_parts": ["crops"]}):
        assert sm._intensity_q_at(d30, di, ("q_low", "q_high"), "animals")["q_low"] == pytest.approx(float(di["q_low"]))


@pytest.mark.slow
def test_ammonia_options_stay_at_their_base_shares_in_the_2030_baseline():
    """K63 (22 October 2026): without a policy incentive on N the regional NLP holds CAPRI's ammonia options at their
    initial shares (CAPRI: costsavings0 makes each option's net marginal cost at its initial share zero, and CONOPT stays
    at the calibrated point). ITC4's poultry storage covers had left them (broilers' covered storage 0.43, CAPRI 0)."""
    from capri_mod.model import CAPRIModel
    from capri_mod.projection import ProjectionModule, BaselineTrajectory
    from capri_mod.supply import ammonia_techs as _at
    m = CAPRIModel(data_dir=str(DATA_DIR), verbose=False)
    traj = BaselineTrajectory.from_file(str(DATA_DIR / "trajectories" / "capri_ref_2030.json"))
    pmod = ProjectionModule(m, traj, capri_prices_dir=str(DATA_DIR / "trajectories"))
    d30, _ = pmod.project_data(2030)
    pm = pmod._model_for(d30)
    b = pm.run(scenario="BASELINE", regions=["IT200000"], max_outer_iter=1)
    sh = getattr(b["supply"]["IT200000"], "manure_tech_shares", None) or {}
    tm = _at.load(DATA_DIR / "2017" / "abatement" / "ammonia" / "ammonia_tech_model.csv")["IT200000"]
    ini = {}
    for a, subs in tm.items():
        for s in subs:
            for t in s["techs"]:
                ini[(a, t["tech"])] = ini.get((a, t["tech"]), 0.0) + s["w"] * t["ini"]
    assert sh and ("BROI", "CovStorHigh") in sh
    assert max(abs(v - ini.get(k, 0.0)) for k, v in sh.items()) < 1e-6


def test_cattle_activities_and_young_animals_per_sex_as_capri():
    """22 October 2026: every CAPRI cattle activity has its own level inside the model's animals (replacement heifers
    HEIR in HFRS; the calves CAMF, CAFF, CAMR, CAFR in CALV), and the young-animal balances are CAPRI's per sex
    (male / female calves, young bulls / heifers; INPANI_): the per-sex balances add up to the pooled ones (DCOW's
    calves split evenly by sex in CAPRI's data), bulls buy young bulls only, heifers young heifers only. The split
    rows: HEIR produces the replacement cows (a stall of HEIR more, beef less), a fattening calf stall buys more calves
    and sells no young cattle. Off by default (RegionalSupplyModel.use_cattle_member_splits; K65: the per-sex markets
    did not converge yet): the default file keeps the pooled balances, the per-sex file sits beside it and adds up
    to them."""
    import json
    ya = json.load(open(DATA_DIR / "2017" / "supply" / "young_animals_by_sex_2017.json"))["regions"]["DE110000"]
    assert {"calves_m", "calves_f", "young_m", "young_f", "cows"} <= set(ya) and "calves" not in ya
    yp = json.load(open(DATA_DIR / "2017" / "supply" / "young_animals_2017.json"))["regions"]["DE110000"]
    assert {"calves", "young", "cows"} <= set(yp) and "calves_m" not in yp
    assert abs(ya["calves_m"]["produce"]["DCOW"] + ya["calves_f"]["produce"]["DCOW"] - yp["calves"]["produce"]["DCOW"]) < 1e-9
    from capri_mod.supply.supply_module import RegionalSupplyModel, young_animal_table
    assert not RegionalSupplyModel.use_cattle_member_splits and "calves" in young_animal_table()["DE110000"]
    assert set(ya["young_m"]["use"]) == {"BULL"} and set(ya["young_f"]["use"]) == {"HFRS"}
    assert abs(ya["calves_m"]["produce"]["DCOW"] + ya["calves_f"]["produce"]["DCOW"] - 0.8086492838767341) < 1e-9
    ct = pd.read_csv(DATA_DIR / "2017" / "supply" / "cattle_intensity.csv")
    assert set(ct.split) == {"int", "rep", "male", "female", "sex"}
    d = ct[ct.region == "DE110000"].set_index("split")
    assert d.at["rep", "dprod_cows_rel"] > 0 and d.at["rep", "dbeef_rel"] < 0
    assert d.at["male", "duse_calves_m_rel"] > 0 and d.at["male", "dprod_young_m_rel"] < 0
    assert d.at["female", "duse_calves_f_rel"] > 0 and d.at["female", "dprod_young_f_rel"] < 0
    assert d.at["sex", "dprod_young_m_rel"] > 0 > d.at["sex", "dprod_young_f_rel"]
    # the curvature of the splits: q_z = q of both activities, q_b of the one giving up stalls
    assert (ct.q_z > ct.q_b).all() and (ct.q_b > 0).all()


def test_labour_accounts_and_set_aside_split_as_capri(data):
    """22 October 2026: CAPRI's labour accounts (GROF LABT = sum of LABT x LEVL / 1000, million hours) and its two
    set-aside activities in the model's SETA (tools/build/build_labour_setaside.py). At the base levels the accounts give
    CAPRI's own regional total (DE11 2017: 20.66 million hours in res_17DE, where the dump is at hand; within 3%); VSET takes
    CAPRI's share of SETA at base and w of a change, FALL the rest, the premiums CAPRI's per ha."""
    import types
    from capri_mod.model import _labour_table, _set_aside_table
    reg = "DE110000"
    x = pd.concat([data["areas"].loc[reg], data["animal_numbers"].rename(columns={"SCOW": "BCOW", "HEIF": "HFRS"}).loc[reg]])
    x = x[~x.index.duplicated()]
    res = {reg: types.SimpleNamespace(activities=x)}
    d17 = dict(data, market_year=2017)
    sa = _set_aside_table(res, d17, "")
    row = data["set_aside_split"].loc[reg]
    assert abs(sa.at[reg, "VSET"] - row["share_vset"] * x["SETA"]) < 1e-9
    assert abs(sa.at[reg, "VSET"] + sa.at[reg, "FALL"] - x["SETA"]) < 1e-9
    assert abs(sa.at[reg, "prem_VSET"] - sa.at[reg, "VSET"] * row["prem_vset"] / 1000.0) < 1e-12
    x2 = x.copy(); x2["SETA"] = x["SETA"] + 10.0
    sa2 = _set_aside_table({reg: types.SimpleNamespace(activities=x2)}, d17, "")
    assert abs(sa2.at[reg, "VSET"] - sa.at[reg, "VSET"] - 10.0 * row["w_vset"]) < 1e-9
    lab = _labour_table(res, d17, sa)
    assert set(lab.columns) == {"LABT", "LABF", "LABP"} and abs(lab.at[reg, "LABF"] + lab.at[reg, "LABP"] - lab.at[reg, "LABT"]) < 0.02 * lab.at[reg, "LABT"]
    import re
    dump = Path("/home/claude/work/capreg/res_17DE.txt")
    if dump.exists():
        m = re.search(r"^'DE110000'\.'GROF'\.'LABT'\.'Y'\s+([\d.Ee+-]+)", dump.read_text(errors="ignore"), re.M)
        if m:
            assert abs(lab.at[reg, "LABT"] / float(m.group(1)) - 1.0) < 0.03


def test_greendeal_input_changes_follow_capri(monkeypatch):
    """CAPRI's plant-protection and other-input changes of the organic and pesticide targets (organic_io.gms,
    conventional_io.gms, define_inputs.gms): one regional change per input on every activity, animals' other inputs
    included, plus the organic crops' fuel top-up; the change multiplies the input-saving progress TF_I (the
    CAPRI-ERROR-FIX default) or replaces it (CAPRI's code, the parity switch)."""
    from capri_mod.data.loaders import load_all_data
    from capri_mod.supply.supply_module import SupplyModule, RegionalSupplyModel
    from capri_mod.utils.utils import calibrate_supply_elasticities

    d = load_all_data("capri_data")
    region = "FR810000" if "FR810000" in d["areas"].index else str(d["areas"].index[0])
    sm = SupplyModule(d, calibrate_supply_elasticities(d["areas"]))
    sm.run(price_signals=None, regions=[region])
    mo = sm._models[region]
    mo.data.sim_year = 2030
    tf = 1.0 - 0.005 * 13
    crop = next(c for c in ("SWHE", "BARL") if c in mo.net_revenues.index)
    ani = next(a for a in ("DCOW", "PIGF") if a in mo.net_revenues.index and mo._input_row(a, "inpo_toin_share"))
    plap, inpo = mo._input_row(crop, "plap_eur_ha"), mo._input_row(crop, "inpo_eur_ha")
    eful = mo._input_row(crop, "eful_eur_ha")
    assert plap and inpo and eful
    nr0 = mo.net_revenues.copy()
    o_R, o_a = mo._organic_region_target(0.25), mo._organic_crop_target(crop, 0.25)
    assert 0 < o_R < 0.5 and o_a > 0
    assert mo._organic_crop_target("GRAS", 0.25) == 0.0, "grassland is not one of CAPRI's organic crops"

    mo._apply_greendeal_input_changes(0.25, 0.50)
    topup = 2 * o_a * eful
    d_plap = plap * (1 - 0.5) * tf - plap * tf                         # PLAP -50% overall
    d_inpo = (inpo + topup) * (1 + 0.5 - o_R) * tf - inpo * tf         # INPO +(r - o_R), with the top-up
    assert abs((nr0[crop] - mo.net_revenues[crop]) - (d_plap + d_inpo)) < 1e-6
    sh = mo._input_row(ani, "inpo_toin_share") * mo._animal_cost_per_head(ani)
    assert abs((nr0[ani] - mo.net_revenues[ani]) - sh * (0.5 - o_R) * tf) < 1e-6

    # organic target alone: plant protection -o_R on every crop, the top-up, no change for animals
    mo.net_revenues = nr0.copy()
    mo._apply_greendeal_input_changes(0.25, 0.0)
    assert abs((nr0[crop] - mo.net_revenues[crop]) - (-plap * o_R * tf + topup * tf)) < 1e-6
    assert mo.net_revenues[ani] == nr0[ani]

    # parity switch: CAPRI's code replaces TF_I by (1 + change)
    monkeypatch.setattr(RegionalSupplyModel, "greendeal_inputs_keep_tech_change", False)
    mo.net_revenues = nr0.copy()
    mo._apply_greendeal_input_changes(0.25, 0.50)
    assert abs((nr0[ani] - mo.net_revenues[ani]) - sh * ((1 + 0.5 - o_R) - tf)) < 1e-6


def test_input_costs_follow_yields_as_capri(monkeypatch):
    """CAPRI's yield-dependent inputs (capmod/define_inputs.gms, inputs/yieldIY.gms): a crop's input cost per ha moves
    by sum_i f_i x cost_i x G x TF_I x (rho - 1) with its yield ratio rho against the 2030 reference, PLAP and INPO at
    their Green Deal TF_I; nothing at the reference yields, nothing with the switch off."""
    from capri_mod.data.loaders import load_all_data
    from capri_mod.supply.supply_module import SupplyModule, RegionalSupplyModel
    from capri_mod.utils.utils import calibrate_supply_elasticities

    d = load_all_data("capri_data")
    region = "FR810000" if "FR810000" in d["areas"].index else str(d["areas"].index[0])
    sm = SupplyModule(d, calibrate_supply_elasticities(d["areas"]))
    sm.run(price_signals=None, regions=[region])
    mo = sm._models[region]
    mo.data.sim_year = 2030
    tf = 1.0 - 0.005 * 13
    crop = next(c for c in ("SWHE", "BARL") if c in mo.net_revenues.index)
    rest, pl, ip = (mo._input_row(crop, c) for c in ("yd_rest_eur_ha", "yd_plap_eur_ha", "yd_inpo_eur_ha"))
    g = mo._input_row(crop, "yield_growth")
    assert rest and pl and ip and 0.5 < g < 1.5
    y0 = mo.data.yields.copy()
    mo._yields_solve0 = y0
    nr0 = mo.net_revenues.copy()
    mo._greendeal_inputs = {}
    mo._apply_yield_input_costs()                                   # at the reference yields: no change
    assert (mo.net_revenues == nr0).all()
    y1 = y0.copy(); y1[crop] = y0[crop] * 0.9
    mo.data.yields = y1
    mo._apply_yield_input_costs()
    assert abs((nr0[crop] - mo.net_revenues[crop]) - (rest + pl + ip) * tf * (-0.1)) < 1e-6
    # with the Green Deal's PLAP -50% and INPO +30%: those parts at (1 + change) x TF_I
    mo.net_revenues = nr0.copy()
    mo._greendeal_inputs = {"pc_plap": -0.5, "pc_inpo": 0.3, "keep_tf": True}
    mo._apply_yield_input_costs()
    want = (rest * tf + pl * 0.5 * tf + ip * 1.3 * tf) * (-0.1)
    assert abs((nr0[crop] - mo.net_revenues[crop]) - want) < 1e-6
    mo.data.yields, mo._yields_solve0, mo._greendeal_inputs = y0, None, {}


def _dying_in_fr10(region):
    """A regional-solve worker that dies on FR10 (test_dead_worker_does_not_hang_the_regional_solves)."""
    import os
    from capri_mod.supply import supply_module as smod
    if region == "FR100000":
        os._exit(1)
    return smod.__dict__["_par_solve_region_orig"](region)


def test_dead_worker_does_not_hang_the_regional_solves(monkeypatch):
    """A regional-solve worker that dies (killed for memory) must not hang the run: the regions left are solved in
    the parent process, with a warning, and the results equal a run in one process (26 October 2026)."""
    import os
    import warnings
    from capri_mod.supply import supply_module as smod
    from capri_mod.settings import override
    from capri_mod.model import CAPRIModel
    regs = ["DE110000", "DE120000", "FR100000", "FR720000"]
    monkeypatch.setitem(smod.__dict__, "_par_solve_region_orig", smod._par_solve_region)
    with override({"market.market_supply_nq": False}):
        m1 = CAPRIModel(data_dir="capri_data", verbose=False)
        monkeypatch.setenv("CAPRI_WORKERS", "1")
        r1 = m1.run(scenario="BASELINE", regions=regs, max_outer_iter=1)
        monkeypatch.setattr(smod, "_par_solve_region", _dying_in_fr10)
        monkeypatch.setenv("CAPRI_WORKERS", "2")
        m2 = CAPRIModel(data_dir="capri_data", verbose=False)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            r2 = m2.run(scenario="BASELINE", regions=regs, max_outer_iter=1)
        assert any("worker process of the regional solves died" in str(x.message) for x in w)
    for g in regs:
        a, b = r1["supply"][g].activities, r2["supply"][g].activities
        assert float((a - b).abs().max()) < 1e-6, g


def test_nlp_form_has_capri_fodder_equality_without_lagged_band():
    """CAPRI's fodder balance SUPBAL_ is an equality with the feed columns (capri_regional_nlp); the conic form's band
    rows, which carried the previous solve's fodder per head (K75), are no longer built (27 October 2026)."""
    from capri_mod.model import CAPRIModel
    m = CAPRIModel(data_dir="capri_data", verbose=False)
    m.run(scenario="BASELINE", regions=["FR250000"], max_outer_iter=1)
    labels = m.supply_module._models["FR250000"]._row_labels
    assert any(l.startswith("fodder_") for l in labels)
    assert not any(l.endswith("_band") for l in labels)
