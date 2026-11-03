"""Norway as its own market region (KNOWN_ISSUES K56).

CAPRI (aggregation/defaultA.agg) has Norway as a market region of its own, NO000000, linked to supply models (RMSSUP,
global/fromimpact/sets.gms: RMSSUP = NUTS0): its market supply is its supply models' output (ProdNQ_ calibrated to
them, arm/market_model.gms), its feed follows its supply models' herds through its bulks (feedBlkPrice_,
feedShareEqu_; FeedBal_ only for regions without supply models), its raw milk goes to its own dairies, and its supply
models see its own prices. capri-mod's trade region NO000000 (NOR until 3 November 2026) follows that: CAPRI's bilateral data for NO000000 (no longer
folded into ROW), Norway's supply regions NO01-NO07 out of the EU's market supply and EU totals.

Run:  python -m pytest -q -p no:cacheprovider capri_mod/tests/test_norway_market.py
"""
from pathlib import Path
import os
import lzma
import sys
import types

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
#: CAPRI's material outside git (tools/lib/paths.py, docs/EXTERNAL_SOURCES.md): a check that needs it is skipped
#: where it is absent
SOURCES = Path(os.environ.get("CAPRI_SOURCES") or ROOT / "capri_sources")
DATA_DIR = ROOT / "capri_data"
MKT = DATA_DIR / "2017" / "market"
NO_REGIONS = ["NO020000", "NO060000", "NO070000", "NO080000", "NO090000", "NO0A0000"]


@pytest.fixture(scope="module")
def data():
    from capri_mod.data.loaders import load_all_data
    return load_all_data(DATA_DIR)


def test_norway_is_a_trade_region_of_its_own():
    """NO000000 is a trade region of its own (44 trade regions since 3 November 2026: CAPRI's 45 market regions, the EU's two blocks one trade region), the EU blocks hold no Norwegian
    country, CAPRI's NO000000 maps to itself (CAPRI's code since 3 November 2026)."""
    from capri_mod.data.definitions import ALL_TRADE_REGIONS, EU_MS_BLOCK, sup_noneu, TRADE_REGION_OF_CAPRI
    sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "check")]
    from _market_regions import model_region          # the market's grouping step (tools/lib)
    assert len(ALL_TRADE_REGIONS) == 44 and "ROW" not in ALL_TRADE_REGIONS and "NO000000" in ALL_TRADE_REGIONS
    assert TRADE_REGION_OF_CAPRI["NO000000"] == "NO000000" and "NO000000" in ALL_TRADE_REGIONS
    assert sup_noneu() == {"NO000000": ("NO", "NO000000")} and "NO000000" not in EU_MS_BLOCK
    assert model_region("NO000000") == "NO000000"


def test_supply_countries_outside_eu_setting():
    """run.supply_countries_outside_eu decides the run's supply-model countries outside the EU (CAPRI's per-country
    switches): Norway by default; none when empty, Norway's units then out of the run; a country without regional
    units is refused."""
    import pytest
    from capri_mod import settings
    from capri_mod.data.definitions import sup_noneu, in_run, SUP_NONEU_ALL
    assert "NO000000" in SUP_NONEU_ALL
    assert list(sup_noneu()) == ["NO000000"] and in_run("NO020000") and in_run("DE110000")
    with settings.override({"run.supply_countries_outside_eu": []}):
        assert sup_noneu() == {} and not in_run("NO020000") and in_run("DE110000")
    with settings.override({"run.supply_countries_outside_eu": ["XX000000"]}):
        with pytest.raises(ValueError, match="no regional units"):
            sup_noneu()


def test_norway_market_data_are_capris_no000000():
    """Every per-region market file carries Norway from CAPRI's own NO000000 data, and ROW no longer does: production
    of the bilateral market = CAPRI's PROD of NO000000, tariffs from CAPRI's import prices into NO000000, Norway's GL
    food demand, processing functions and dairy block are NO000000's; the EU's dairy block holds no Norway; Norway has
    no non-EU feed demand function (CAPRI: FeedBal_ only outside RMSSUP)."""
    import json
    with lzma.open(DATA_DIR / "sources" / "market" / "bilateral_dataout_2030.csv.xz", "rt") as fh:
        src = pd.read_csv(fh, keep_default_na=False)
    p = src[(src.r1 == "NO000000") & (src.r2 == "") & (src["item"] == "PROD")].set_index("product")["value"].astype(float)
    rg = pd.read_csv(MKT / "bilateral_regions_2030.csv")
    nor = rg[rg.region == "NO000000"].set_index("commodity")["prod_kt"]
    for model_c, capri_c in (("BARL", "BARL"), ("SFIS", "SFIS"), ("POUL", "POUM"), ("PORK", "PORK")):
        assert abs(float(nor[model_c]) - float(p[capri_c])) < 1e-4 * max(1.0, float(p[capri_c])), model_c
    for f in ("bilateral_flows_2017.csv", "bilateral_flows_2030.csv"):
        fl = pd.read_csv(MKT / f)
        assert ((fl.importer == "NO000000") & (fl.exporter == "NO000000")).any(), f
    tar = pd.read_csv(DATA_DIR / "2017" / "policy" / "tariffs.csv", index_col=0)
    assert "NO000000" in tar.index and float(tar.at["NO000000", "BEEF"]) > 0
    gl = pd.read_csv(MKT / "gl_demand_regions.csv")
    assert gl.loc[gl.rms == "NO000000", "model_region"].tolist() == ["NO000000"]
    assert "NO000000" in set(pd.read_csv(MKT / "processing_nq_base.csv").query("rms == 'NO000000'").model_region)
    assert "NO000000" not in set(pd.read_csv(MKT / "dairy_processing.csv").ms)
    wp = pd.read_csv(MKT / "dairy_world_processing.csv")
    assert set(wp.loc[wp.rms == "NO000000", "trade_region"]) == {"NO000000"}
    from capri_mod.data.nested_tables import read_feed_demand
    fd = read_feed_demand(MKT / "feed_demand_nonEU.csv")
    assert not any(k.startswith("NO000000|") for k in fd)
    se = pd.read_csv(MKT / "supply_elas_region.csv")
    assert (se.region == "NO000000").any()


def test_eu_and_norway_rows_are_split(data):
    """Norway's supply-model rows go to NO000000, not to the EU's market region(s)."""
    from capri_mod.market.market_module import MarketModule
    mm = MarketModule(data)
    assert mm.SUP == ("NO000000",) and "NO000000" in mm.regions
    assert mm.eu_region_of_ms("NO000000") is None and mm.eu_region_of_ms("DE000000") in mm.EU
    assert mm.sup_region_of_country("NO090000") == "NO000000" and mm.sup_region_of_country("DE") is None
    exo = pd.DataFrame({"BARL": [10.0, 3.0, 2.0]}, index=["DE", "DK", "NO"])
    assert mm.eu_rows(exo).loc[mm.eu_region_of_ms("DE000000"), "BARL"] == 13.0      # DE and DK: one block
    eu, sup = mm._split_supply(exo)
    assert list(eu.index) == ["DE", "DK"] and float(sup["NO000000"]["BARL"]) == 2.0


def _eu_countries(mm):
    """One country per EU market region (CAPRI's two blocks since 3 November 2026): [(region, country)], DE for its
    block and PL for the other."""
    out = {}
    for c in ("DE", "PL"):
        out.setdefault(mm.eu_region_of_ms(c + "000000"), c)
    return list(out.items())


def _exo_with_norway(mm):
    """Supply by country: one country per EU market region at that region's CAPRI base (_eu_countries), Norway's 5%
    above CAPRI's (the supply models' output differs from CAPRI's), with raw milk."""
    cols = list(mm.commodities)
    pairs = _eu_countries(mm)
    rows = [mm.par.base_production.loc[r, cols].astype(float) for r, _ in pairs]
    no = mm.par.base_production.loc["NO000000", cols].astype(float) * 1.05
    return pd.DataFrame(rows + [no], index=[c for _, c in pairs] + ["NO"])


def test_norway_market_supply_is_its_models_and_the_base_is_reproduced(data):
    """CAPRI's RMSSUP treatment for Norway: at the reference prices the market reproduces the base with Norway's market
    supply = its supply models' output (the closure's domestic sales absorb the difference to CAPRI's flows), its raw
    milk all to its own dairies; Norway's supply responds to its own price relative to the price its models saw, and
    the EU's supply is not touched by Norway's."""
    from capri_mod.market.market_module import MarketModule
    mm = MarketModule(data)
    exo = _exo_with_norway(mm)
    mm._bilateral_calibrate(exo)
    r = mm._bilateral_ratio_frame()
    S, D, PAr, F, pc = mm._bilateral_eval(r, exo)
    size = {c: np.maximum(sc.S0 + sc.D0, 1.0) for c, sc in mm.par.bilat.items()}
    assert max(float(np.max(np.abs(F[c] / size[c]))) for c in mm.par.bilat) < 1e-6
    for c in ("BARL", "SWHE", "BEEF", "POUL", "OATS"):
        assert abs(float(S.at["NO000000", c]) - float(exo.at["NO", c])) < 1e-9 * max(1.0, float(exo.at["NO", c])), c
        for rg, cc in _eu_countries(mm):
            assert abs(float(S.at[rg, c]) - float(exo.at[cc, c])) < 1e-6 * max(1.0, float(exo.at[cc, c])), (rg, c)
    assert abs(float(D.at["NO000000", "MILK"]) - float(exo.at["NO", "MILK"])) < 1e-9 * float(exo.at["NO", "MILK"])
    assert abs(mm.par.sup_milk0["NO000000"] - float(exo.at["NO", "MILK"])) < 1e-9
    # Norway's barley 10% dearer than its models saw: Norway's supply follows (own CAPRI elasticity), the EU's not
    mm.seen.sup_price_seen = {"NO000000": pd.Series(1.0, index=mm.commodities)}
    r1 = r.copy()
    r1.at["NO000000", "BARL"] = 1.10
    S1 = mm.supply_response(mm.world_prices_base, exo, region_ratio=r1, crush_dom=mm._dom0())
    assert float(S1.at["NO000000", "BARL"]) > float(exo.at["NO", "BARL"]) * 1.001
    for rg, cc in _eu_countries(mm):
        assert abs(float(S1.at[rg, "BARL"]) - float(exo.at[cc, "BARL"])) < 1e-9 * float(exo.at[cc, "BARL"])
    # ... and once the models have seen that price, the market takes their output as it is
    mm.seen.sup_price_seen = {"NO000000": pd.Series(1.0, index=mm.commodities).where(lambda x: x.index != "BARL", 1.10)}
    S2 = mm.supply_response(mm.world_prices_base, exo, region_ratio=r1, crush_dom=mm._dom0())
    assert abs(float(S2.at["NO000000", "BARL"]) - float(exo.at["NO", "BARL"])) < 1e-9 * float(exo.at["NO", "BARL"])
    # with CAPRI's market supply function measured on Norway's models (market_supply_nq): linear through their output
    mm.par.supply_hessian = {"sup": {"NO000000": pd.DataFrame([[50.0]], index=["BARL"], columns=["BARL"])}}
    mm.seen.sup_price_seen = {"NO000000": pd.Series(1.0, index=mm.commodities)}
    try:
        S3 = mm.supply_response(mm.world_prices_base, exo, region_ratio=r1, crush_dom=mm._dom0())
        assert abs(float(S3.at["NO000000", "BARL"]) - (float(exo.at["NO", "BARL"]) + 50.0 * 0.10)) < 1e-6
        for rg, cc in _eu_countries(mm):
            assert abs(float(S3.at[rg, "BARL"]) - float(exo.at[cc, "BARL"])) < 1e-9 * float(exo.at[cc, "BARL"])
    finally:
        mm.par.supply_hessian = None



def test_norway_raw_milk_responds_inside_the_market(data):
    """CAPRI keeps ProdNQ_ MILK of the regions with supply models in the market, re-anchored to their models' milk
    (arm/simu_calibration_to_supply.gms l. 198-201, 423-427; market.sup_milk_in_market, step F): Norway's milk delivered
    = its models' milk + the Hessian's MILK row x (its dairy-block milk price and the other prices against those its
    models saw), and its products move with the milk price by the MILK column (the block's price of the previous
    evaluation); with the switch off the milk is its models'."""
    from capri_mod.market.market_module import MarketModule
    mm = MarketModule(data)
    exo = _exo_with_norway(mm)
    mm._bilateral_calibrate(exo)
    r1 = mm._bilateral_ratio_frame().copy()
    r1.at["NO000000", "BARL"] = 1.10
    m_now = float(exo.at["NO", "MILK"])
    b_now = float(exo.at["NO", "BARL"])
    H = pd.DataFrame([[50.0, -10.0], [-20.0, 400.0]], index=["BARL", "MILK"], columns=["BARL", "MILK"])
    mm.par.supply_hessian = {"sup": {"NO000000": H}}
    mm.seen.sup_price_seen = {"NO000000": pd.Series(1.0, index=mm.commodities)}
    mm.ev.dairy_world_last = None
    try:
        S1 = mm.supply_response(mm.world_prices_base, exo, region_ratio=r1, crush_dom=mm._dom0())
        pm = float(mm.ev.dairy_world_last["NO000000"]["price_ratio"]["MILK"])
        # dearer barley: less milk delivered (cross term -20 x 0.10), so the dairies bid the milk price up
        assert pm > 1.0
        assert abs(float(S1.at["NO000000", "MILK"]) - (m_now + 400.0 * (pm - 1.0) - 2.0)) < 1e-6 * m_now
        assert float(S1.at["NO000000", "MILK"]) < m_now
        # the first evaluation has no block price yet: barley as before
        assert abs(float(S1.at["NO000000", "BARL"]) - (b_now + 5.0)) < 1e-6
        # the next evaluation: barley responds to the block's milk price by the MILK column
        S2 = mm.supply_response(mm.world_prices_base, exo, region_ratio=r1, crush_dom=mm._dom0())
        assert abs(float(S2.at["NO000000", "BARL"]) - (b_now + 5.0 - 10.0 * (pm - 1.0))) < 1e-6
        from capri_mod.settings import override
        with override({"market.sup_milk_in_market": False}):
            S3 = mm.supply_response(mm.world_prices_base, exo, region_ratio=r1, crush_dom=mm._dom0())
        assert abs(float(S3.at["NO000000", "MILK"]) - m_now) < 1e-9 * m_now
    finally:
        mm.par.supply_hessian = None

def test_norway_feed_and_dairy_follow_its_supply_models(data):
    """Norway's feed bulks (feed_bulks_no.csv, CAPRI NO000000 FEED and ARM1P) give its feed use at base, and the feed
    share of its use is CAPRI's (FEED over HCON + FEED + PROC + BIOF + INDM + LOSM); its dairy block takes its raw
    milk from its supply models: less milk raises Norway's raw milk price."""
    from capri_mod.market.market_module import MarketModule
    mm = MarketModule(data)
    fb = mm._feed_bulk_params()
    f0 = fb["feed0_sup"]["NO000000"]
    assert f0["BARL"] > 100 and f0["SOYC"] > 50
    q = mm.sup_feed_use("NO000000", {})
    assert all(abs(q[c] - f0[c]) < 1e-9 * max(1.0, f0[c]) for c in f0)
    sh = fb["share_sup"]["NO000000"]
    # at most the whole use (the 0.98 cap was removed on 23 October 2026, no CAPRI source; PROXY_AUDIT)
    assert 0 < sh["BARL"] <= 1.0 and 0 < sh["SOYC"] <= 1.0
    q1 = mm.sup_feed_use("NO000000", {"BARL": 1.1})                       # dearer barley: less barley, more oats fed
    assert q1["BARL"] < f0["BARL"] and q1["OATS"] > f0["OATS"]
    w = mm._dairy_world_params()
    assert "NO000000" in w
    b = mm._dairy_solve(w["NO000000"], {}, 1.0, 1.0, "test_NOR")
    assert all(abs(v - 1.0) < 1e-9 for v in b["price_ratio"].values())
    x = mm._dairy_solve(w["NO000000"], {}, 0.95, 1.0, "test_NOR")
    assert x["price_ratio"]["MILK"] > 1.0 and x["residual"] < 1e-6


def test_norway_young_animals_hessian_and_bulk_prices_are_its_own(data):
    """Norway's young animals clear in its own market (CAPRI yaniMarket_ per RM); its market supply Hessian is kept
    apart from the EU's; its supply models' feed bulk prices are at Norway's price signal."""
    from capri_mod.model import CAPRIModel
    from capri_mod.market.market_module import MarketModule
    mm = MarketModule(data)
    fake = types.SimpleNamespace(market_module=mm, _sum_frames=CAPRIModel._sum_frames, sv=types.SimpleNamespace())
    assert CAPRIModel._yani_market_region(fake, "NO090000") == "NO000000"
    assert CAPRIModel._yani_market_region(fake, "DE110000") == mm.eu_region_of_ms("DE000000")
    h = lambda v: pd.DataFrame([[v]], index=["BARL"], columns=["BARL"])
    # CAPRI's two EU trade blocks: one Hessian per block, the sum of its member states' (eu_market_blocks.csv);
    # Norway's on its own; the EU total for reporting
    eu, sup, blocks = CAPRIModel._split_hessian(fake, {"DE": h(2.0), "DK": h(1.0), "PL": h(4.0), "NO": h(0.5)})
    assert float(eu.at["BARL", "BARL"]) == 7.0 and float(sup["NO000000"].at["BARL", "BARL"]) == 0.5
    bm = mm._ms_block_map()
    exp = {}
    for cc, v in (("DE000000", 2.0), ("DK000000", 1.0), ("PL000000", 4.0)):
        exp[bm[cc]] = exp.get(bm[cc], 0.0) + v
    assert {b: float(H.at["BARL", "BARL"]) for b, H in blocks.items()} == exp
    fake.sv.sup_dev = {"NO000000": pd.Series({"BARL": 0.2})}
    sig = pd.Series(0.0, index=mm.commodities)
    out = CAPRIModel.feed_bulk_price_ratios(fake, sig)
    assert out[("NO000000", "FCER")] > 1.0
    assert abs(out[("DE000000", "FCER")] - 1.0) < 1e-12


def test_flatten_outputs_reports_norway_apart():
    """flatten_outputs: the EU's totals leave Norway's regions out; Norway's are reported apart."""
    from capri_mod.io_results import flatten_outputs
    from capri_mod.market.market_module import MarketEquilibrium
    prod = pd.DataFrame({"BARL": [100.0, 5.0]}, index=["EU27", "NO000000"])
    mkt = MarketEquilibrium(world_prices=pd.Series({"BARL": 150.0}), domestic_prices=prod * 2, production=prod,
                            consumption=prod, trade_flows=pd.DataFrame(), net_exports=prod * 0,
                            welfare=pd.DataFrame(), excess_demand=pd.Series(dtype=float))
    env = pd.DataFrame({"ghg_total": [10.0, 1.0, 2.0]}, index=["DE110000", "NO080000", "NO020000"])
    o = flatten_outputs({"market": mkt, "environmental": env})
    assert o["prod_EU27_BARL"] == 100.0 and o["prod_NOR_BARL"] == 5.0 and o["price_NOR_BARL"] == 10.0
    assert o["env_EU_ghg_total"] == 10.0 and o["env_NO_ghg_total"] == 3.0


def test_norway_has_pig_herds_and_per_head_coefficients():
    """Norway's supply regions have CAPRI's pig herds (K56, 21 October 2026 evening; tools/build/build_capri_base.py):
    positive sows (PIGS) and fattening pigs (PIGF), and finite, positive per-head pork output and manure N. Where
    CAPRI's dump is at hand, heads x coefficients give CAPRI's Norwegian totals (NO000000: HERD; LEVL x PORK,
    LEVL x MANN of SOWS and PIGF)."""
    import re
    from collections import defaultdict
    sup, env = DATA_DIR / "2017" / "supply", DATA_DIR / "2017" / "environment"
    h = pd.read_csv(sup / "animal_numbers.csv", index_col=0).loc[NO_REGIONS, ["PIGS", "PIGF"]]
    assert (h.to_numpy() > 0).all()
    pork = pd.read_csv(sup / "livestock_output_by_product_coef.csv", index_col=0).loc[NO_REGIONS, ["PIGS.PORK", "PIGF.PORK"]]
    mann = pd.read_csv(env / "livestock_manure_n_coef.csv", index_col=0).loc[NO_REGIONS, ["PIGS", "PIGF"]]
    for t in (pork, mann):
        v = t.to_numpy(dtype=float)
        assert np.isfinite(v).all() and (v > 0).all()
    dump = SOURCES / "capreg" / "res_17NO.txt"
    if not dump.exists():
        return
    pat = re.compile(r"^'NO000000'\.'(SOWS|PIGF)'\.'(HERD|LEVL|PORK|MANN)'\.'Y'\s+(-?\d[\d.Ee+\-]*)")
    c = defaultdict(dict)
    for line in open(dump, errors="ignore"):
        m = pat.match(line)
        if m:
            c[m.group(1)][m.group(2)] = float(m.group(3))
    for col, act in (("PIGS", "SOWS"), ("PIGF", "PIGF")):
        assert abs(float(h[col].sum()) - c[act]["HERD"]) < 1e-6 * c[act]["HERD"], col
        q = float((h[col] * pork[f"{col}.PORK"]).sum())                      # kt
        assert abs(q - c[act]["LEVL"] * c[act]["PORK"] / 1000.0) < 1e-6 * q, col
        n = float((h[col] * mann[col]).sum())                                # t N
        assert abs(n - c[act]["LEVL"] * c[act]["MANN"]) < 1e-6 * n, col


def test_norway_run_on_its_own_supply_models():
    """A baseline with Norway's supply regions: the EU's market supply holds none of Norway's output, Norway's market
    supply is its models' (pork too, since Norway's regions have pigs, K56), the base is reproduced at the reference
    prices and Norway's supply models see Norway's prices. With no EU unit in the run, the EU's supply is its units'
    base output through their member states' market supply functions (K83, since 31 October 2026; before, the market's
    own base table), at the reference prices that base output itself."""
    from capri_mod.model import CAPRIModel
    m = CAPRIModel(data_dir=str(DATA_DIR), verbose=False)
    with pytest.warns(RuntimeWarning):
        b = m.run(scenario="BASELINE", regions=["NO080000"], max_outer_iter=1)
    mm = m.market_module
    P = b["market"].production
    ex = m._bridge_supply_to_market(m.supply_module.aggregate_supply(b["supply"], by_country=True))
    assert float(ex.at["NO", "PORK"]) > 0
    for c in ("BARL", "OATS", "BEEF", "MILK", "SGMT", "PORK"):
        assert abs(float(P.at["NO000000", c]) - float(ex.at["NO", c])) < 1e-6 * max(1.0, float(ex.at["NO", c])), c
        # no EU unit in the run: the EU's supply is its units' base output (K83), Norway's output not in it
        xr = mm._eu_excluded_rows()
        for rg in mm.EU:
            assert abs(float(P.at[rg, c]) - float(xr.at[rg, c])) < 1e-6 * max(1.0, float(P.at[rg, c])), (rg, c)
    assert float(mm._bilat_err) < 1e-6
    assert float((mm.sup_price_ratio - 1.0).abs().max().max()) < 1e-9


@pytest.mark.slow
def test_norway_prices_follow_its_own_market_in_a_scenario():
    """Farm-to-Fork on one EU region and Norway (2 outer iterations: a diagnostic run, K10): Norway's supply models get
    Norway's market prices (price_dev_ms NO000000), which differ from the EU's; the EU's market supply holds no
    Norwegian output."""
    from capri_mod.model import CAPRIModel
    from capri_mod.policy.greendeal import farm_to_fork_scenario
    m = CAPRIModel(data_dir=str(DATA_DIR), verbose=False)
    regs = ["IR010000", "NO080000"]
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        b = m.run(scenario="BASELINE", regions=regs, max_outer_iter=2)
        s = m.run(custom_scenario=farm_to_fork_scenario(), regions=regs, max_outer_iter=2)
    mm = m.market_module
    assert "NO000000" in (m.supply_module.seen.price_dev_ms or {})
    rb, rs = b["market"].domestic_prices, s["market"].domestic_prices
    d = (rs / rb - 1.0)
    assert float((d.loc["NO000000"] - d.loc[mm.eu_region_of_ms("IR000000")]).abs().max()) > 1e-3
    ex = m._bridge_supply_to_market(m.supply_module.aggregate_supply(s["supply"], by_country=True))
    # Norway's raw milk in the market (market.sup_milk_in_market, step F; simu_calibration_to_supply.gms l. 423-427):
    # its supply models' milk moved by its raw milk supply function, k x (its dairy block's milk price level - the
    # level the models saw) + the MILK row's response to the other prices; equal to the models' milk at convergence
    assert "NO" in ex.index
    t = (mm.ev.sup_milk_terms or {}).get("NO000000")
    P = float(mm.ev.dairy_world_last["NO000000"]["price_ratio"]["MILK"])
    resp = (t["k"] * (P - t["L"]) + float((mm.ev.sup_milk_cross or {}).get("NO000000", 0.0))) if t else 0.0
    assert abs(float(ex.at["NO", "MILK"]) + resp - float(s["market"].production.at["NO000000", "MILK"])) < 1e-6
    # EU raw milk: the EU supply models' output and the base raw milk of the EU's units outside the run (K83), plus
    # the member states' response to their milk prices in the dairy block (audit M5, MarketModule.ev.milk_dq_now),
    # with no Norwegian milk in it
    xr = mm._eu_excluded_rows()
    eu_milk = (float(ex.drop(index="NO")["MILK"].sum()) + float(sum(xr.at[rg, "MILK"] for rg in mm.EU))
               + float(sum((mm.ev.milk_dq_now or {}).values())))
    assert abs(float(sum(s["market"].production.at[rg, "MILK"] for rg in mm.EU)) - eu_milk) < 1e-6
