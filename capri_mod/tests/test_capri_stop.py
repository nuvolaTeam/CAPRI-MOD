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


def test_capri_special_smoothing_weights():
    """CAPRI's slower smoothing for problem products (define_stepWeights.gms l. 41-50): at step k, step j (the
    baseline j = 0) weighs max(0, 1 - srt (k + 1 - j)), normalised; the baseline is the signal 0."""
    from capri_mod.model import CAPRIModel
    f = CAPRIModel._capri_special_forecast
    # srt 0.15 at step 3: baseline 0.4, S1 0.55, S2 0.7, S3 0.85
    w = [0.4, 0.55, 0.7, 0.85]
    hist = [1.0, 2.0, 4.0]
    assert abs(f(hist, 0.15) - (w[1] * 1 + w[2] * 2 + w[3] * 4) / sum(w)) < 1e-12
    # weights reaching zero: srt 0.5 at step 3, only S3 (0.5) and S2 (0) of the steps; the baseline 0
    assert abs(f(hist, 0.5) - 4.0) < 1e-12
    import pandas as pd
    s = f([pd.Series({"a": 1.0}), pd.Series({"a": 3.0})], 0.15)
    assert abs(float(s["a"]) - (0.7 * 1 + 0.85 * 3) / (0.55 + 0.7 + 0.85)) < 1e-12


def test_capri_special_smoothing_setting_is_checked():
    from capri_mod.model import CAPRIModel
    from capri_mod.settings import override
    import pytest
    assert CAPRIModel._capri_step_special() == {}                       # CAPRI's Green Deal scenarios set none
    with override({"outer_loop.capri_step_special": [["MT000000", "MILK", 0.15], ["BG000000", "SOYA", 0.1]]}):
        assert CAPRIModel._capri_step_special() == {("MT000000", "MILK"): 0.15, ("BG000000", "SOYA"): 0.1}
    for bad in (["EU27", "SOYA", 0.1], ["BG000000", "SOYA", 1.5]):
        with override({"outer_loop.capri_step_special": [bad]}):
            with pytest.raises(ValueError):
                CAPRIModel._capri_step_special()
