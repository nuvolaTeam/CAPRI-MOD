"""CAPRI's stop rule for the supply-market iterations (capmod/price_forecast.gms; capri_mod/utils/capri_stop.py) and
CAPRI's price forecast as an option for every price (outer_loop.price_update)."""
import pytest

from capri_mod.utils.capri_stop import CapriStopRule


def _rule():
    return CapriStopRule({"EU_WEST": ["FR000000", "DE000000"]}, yani_rows={"YANI:calves"},
                         no_abs_price_rows={"YANI:calves"})


def test_first_step_goes_on_and_changes_are_capri_percent():
    r = _rule()
    prod = {"FR000000": {"BEEF": 1000.0, "SWHE": 30000.0}, "DE000000": {"BEEF": 1100.0}}
    price = {ms: {"BEEF": 4000.0, "SWHE": 180.0} for ms in prod}
    v1 = r.record(prod, {}, price)
    assert v1["go_on"] and v1["max"] >= 1.0                       # l. 363: the first step counts at least 1%
    prod2 = {"FR000000": {"BEEF": 1010.0, "SWHE": 30000.0}, "DE000000": {"BEEF": 1100.0}}
    v2 = r.record(prod2, {}, price)
    # 2 |1010 - 1000| / 2010 x 100
    assert v2["rows"]["BEEF"] == pytest.approx(200 * 10 / 2010)
    assert v2["count"] == 1 and not v2["go_on"]                    # one row above 0.05%: CAPRI stops (needs > 2)


def test_thresholds_young_animals_and_count():
    r = _rule()
    prod = {"FR000000": {"BEEF": 1000.0, "PORK": 2000.0, "MILK": 25000.0},
            "DE000000": {"BEEF": 1100.0}}
    price = {ms: {"BEEF": 4000.0, "PORK": 1500.0, "MILK": 350.0, "YANI:calves": 1.0} for ms in prod}
    r.record(prod, {"FR000000": {"FCER": 5000.0}}, price)
    prod2 = {"FR000000": {"BEEF": 1000.4, "PORK": 2010.0, "MILK": 25100.0},
             "DE000000": {"BEEF": 1100.0}}
    price2 = {ms: {"BEEF": 4000.04, "PORK": 1500.0, "MILK": 350.0, "YANI:calves": 1.10} for ms in prod}
    v = r.record(prod2, {"FR000000": {"FCER": 5002.0}}, price2)
    assert "BEEF" not in v["rows"]          # production change below 0.5 kt; price change below EUR 0.05
    assert "FCER" not in v["rows"]          # feed change below 2.5 kt
    assert v["rows"]["YANI:calves"] > 9     # young-animal price ratio, no EUR filter ...
    assert v["max"] == pytest.approx(v["rows"]["PORK"])           # ... but out of the step's maximum
    assert v["count"] == 3 and v["go_on"]   # PORK, MILK and young animals above 0.05%: more than two rows


def test_norway_out_from_the_15th_step():
    r = CapriStopRule({"EU_WEST": ["NO000000"]})
    for k in range(1, 16):
        v = r.record({"NO000000": {"BEEF": 100.0 + 5 * k, "PORK": 100.0 + 5 * k, "MILK": 1000.0 + 50 * k}}, {}, {})
        if 1 < k < 15:
            assert v["go_on"]
    assert v["step"] == 15 and v["rows"] == {} and not v["go_on"]


def test_capri_forecast_weights():
    from capri_mod.model import CAPRIModel
    f = CAPRIModel._capri_forecast
    assert f([1.0], 0) == pytest.approx(1.0)
    assert f([1.0, 2.0], 1) == pytest.approx((0.55 * 2 + 0.30 * 1) / 0.85)
    assert f([1.0, 2.0, 3.0, 4.0], 5) == pytest.approx(0.55 * 4 + 0.30 * 3 + 0.15 * 2)
    assert f([1.0, 2.0, 3.0, 4.0], 19) == pytest.approx(0.4 * 4 + 0.3 * 3 + 0.2 * 2 + 0.1 * 1)


def test_model_records_capri_verdict_and_can_stop_on_it():
    from capri_mod.settings import override
    from capri_mod.model import CAPRIModel
    with override({"outer_loop.stop_rule": "capri", "outer_loop.price_update": "capri",
                   "market.market_supply_nq": False}):
        m = CAPRIModel(data_dir="capri_data", verbose=False)
        r = m.run(scenario="BASELINE", regions=["DE110000", "FR100000"], max_outer_iter=6)
    cs = r["metadata"]["capri_stop"]
    assert cs is not None and cs["step"] >= 1
    hist = m._outer_history
    assert all(h["conv"]["capri"] is not None for h in hist)
    last = m._capri_stop.steps[-1]
    # every item kind is formed: prices at the trade block, production and feed per member state
    assert last["aggp"].get("EU_WEST", {}).get("MILK", 0) > 0 and last["aggp"]["EU_WEST"].get("BEEF", 0) > 0
    assert last["prod"]["DE000000"].get("MILK", 0) > 0 and last["feed"]["FR000000"].get("FCER", 0) > 0
    if r["metadata"]["outer_converged"]:
        assert not cs["go_on"]
