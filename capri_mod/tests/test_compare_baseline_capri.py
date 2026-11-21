"""Tools/check/compare_baseline_capri.py in the "capri" coupling form (CAPRI's market calibration): the production compared with CAPRI's
marketed production (PROD at the calibration point) over the EU's member states only."""
from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _tool():
    spec = importlib.util.spec_from_file_location("compare_baseline_capri",
                                                  ROOT / "tools" / "check" / "compare_baseline_capri.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_marketed_production_sums_the_eu_member_states_only():
    from capri_mod.data.definitions import EU_MS_BLOCK
    t = _tool()
    got = t.capri_marketed_production()
    with open(ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "market" / "market_prod_grof_2030.csv", newline="") as fh:
        rows = list(csv.DictReader(fh))
    eu = sum(float(r["prod_kt"]) for r in rows if r["product"] == "WHEA" and r["capri_ms"] in EU_MS_BLOCK)
    allc = sum(float(r["prod_kt"]) for r in rows if r["product"] == "WHEA")
    assert abs(got["WHEA"] - eu) <= 1e-9 * eu
    assert allc > eu                      # the table also holds non-EU countries (Norway, the UK, the Balkans)
    # every product the tool maps to is in the table
    assert all(c in got for c in t.PROD_CODE.values())


def test_capri_mode_read_from_the_run_settings():
    t = _tool()
    assert t.capri_mode({"meta": {"settings": {"market": {"demand_calibration": "capri"}}}})
    assert not t.capri_mode({"meta": {"settings": {"market": {"demand_calibration": "supply"}}}})
    assert t.capri_mode({})                # the setting removed on 8 November 2026 with its "supply" form


def test_prices_against_capris_member_state_market_prices():
    """The results pages' baseline check compares the model's EU27 market price with CAPRI's member states' market
    prices PMRK weighted by production (the model's EU row weights its blocks so; K171), not with CAPRI's EU27yr19
    producer unit value after a median deflator: CAPRI's own EU27yr19 maize PMRK (163 EUR/t) is below every member
    state's (214-220). Animals whose heads are not CAPRI's level unit are compared in CAPRI's units."""
    t = _tool()
    with open(ROOT / "capri_data" / "validation" / "capri_ms_market_prices_2030_ref.csv", newline="") as fh:
        mz = [r for r in csv.DictReader(fh) if r["product"] == "MAIZ"]
    assert len(mz) >= 20 and min(float(r["pmrk_eur_t"]) for r in mz) > 200.0
    ref = sum(float(r["pmrk_eur_t"]) * float(r["grof_kt"]) for r in mz) / sum(float(r["grof_kt"]) for r in mz)
    o = {"act": ({},), "act_regional": ({"DE210000": {"BULL": 10.0}, "UKD00000": {"BULL": 99.0}},),
         "base_market": {"price": {"CORN": ref}, "prod": {}, "cons": {}}}
    out = t.rows(o)
    mp = [r for r in out if r[0] == "market price" and r[1] == "CORN"]
    assert len(mp) == 1 and abs(mp[0][3] / mp[0][4] - 1.0) < 1e-12
    assert not any(r[0].startswith("price (relative)") or r[0].startswith("growth") for r in out)
    import pandas as pd
    q = float(pd.read_csv(ROOT / "capri_data" / "2017" / "supply" / "capri_level_ratio.csv", index_col=0).at["DE210000", "BULL"])
    bu = [r for r in out if r[0] == "activity (CAPRI units)" and r[1] == "BULL"]
    assert len(bu) == 1 and abs(bu[0][3] - 10.0 / q) < 1e-9        # the EU units only, in CAPRI's units


def test_green_deal_prices_against_capris_member_state_market_prices():
    """The Green Deal check (tools/check/compare_capri_gd.py; the results pages' Green Deal tab) compares the model's EU
    market price change with CAPRI's member states' PMRK weighted by their production, each year (K171): CAPRI's own
    pulses PMRK rises about 2% where its EU27yr19 unit value UVAP stays flat. Raw milk against UVAP (CAPRI's PMRK of
    MILK is a constant of its market data)."""
    spec = importlib.util.spec_from_file_location("compare_capri_gd", ROOT / "tools" / "check" / "compare_capri_gd.py")
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    capri = g.capri_effect()
    t = g.price_table({"prices": {"PULS": 0.0, "MILK": 0.0, "SWHE": 0.0}}, capri).set_index("product")
    u = capri[(capri["region"] == "EU27yr19") & (capri["item"] == "UVAP")].set_index("activity")
    assert abs(t.at["PULS", "capri_pct"] - g._capri_market_price_change(capri, "PULS")) < 1e-12
    assert t.at["PULS", "capri_pct"] > 1.0 and abs(float(u.at["PULS", "pct_change"])) < 0.5
    assert abs(t.at["MILK", "capri_pct"] - float(u.at["MILK", "pct_change"])) < 1e-9
    assert "SWHE" in t.index                              # wheat's PMRK is CAPRI's WHEA
