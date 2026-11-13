"""The results browser's reading layer (capri_gradio/results_data.py): read-only over a results store, its tables are the
store's rows matched and pivoted without sums. Gradio is not needed for these tests."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from capri_mod import io_results as IO
from capri_mod.tests.test_results_long import _results

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("results_data", ROOT / "capri_gradio" / "results_data.py")
RD = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RD)


#: the fixture's run ids as the page shows them (RD.ID_SHOWN characters) and the reference's whole id
IDS: dict = {}


@pytest.fixture
def store(tmp_path):
    B, S = (IO.with_capri_codes(IO.to_long(x, p)) for x, p in ((_results(), "base"), (_results(scale=1.5), "scen")))
    kw = dict(reference="ref_x", year=2030, fingerprint_parts={"code": "a"}, root=tmp_path)
    a = IO.write_run(B, S, scenario="scen_a",
                     meta={"conv": True, "it": 4, "settings_changed": {"market": {"demand_calibration": "capri"}},
                           "options": {"regions": "DE110000,FR240000"}}, **kw)
    b = IO.write_run(B, B, scenario="scen_b", meta={"conv": False}, **kw)
    IDS.update(r1=a["run_id"][:RD.ID_SHOWN], r2=b["run_id"][:RD.ID_SHOWN], ref=a["reference_run_id"])
    return tmp_path


def test_the_runs_are_listed_newest_first_with_their_metadata(store):
    r = RD.runs(store)
    assert list(r["scenario"]) == ["scen_b", "scen_a"]
    a = r[r["scenario"] == "scen_a"].iloc[0]
    assert a["converged"] and a["iterations"] == 4 and a["regions"] == 2 and a["reference"] == "ref_x"
    assert a["settings changed"] == "market.demand_calibration=capri"
    assert r[r["scenario"] == "scen_b"].iloc[0]["reference_run_id"] == IDS["ref"]   # the reference stored once
    assert RD.run_label("scen_a", r[r["scenario"] == "scen_a"].iloc[0]["run_id"]) == f"scen_a | {IDS['r1']}"


def test_the_scenario_is_matched_with_its_baseline(store):
    j = RD.scenario_vs_baseline(store, "scen_a", IDS["r1"], "supply", {"rows": ["activities"]})
    sw = j[(j["region"] == "DE110000") & (j["cols"] == "SWHE")].iloc[0]
    assert sw["baseline"] == 10.0 and sw["scenario"] == 15.0
    assert sw["scenario - baseline"] == 5.0 and np.isclose(sw["% change"], 50.0)
    # the browser writes nothing: the store's records are unchanged
    assert len(IO._runs(store)) == 3


def test_the_pivot_takes_single_rows_and_never_sums(store):
    j = RD.scenario_vs_baseline(store, "scen_a", IDS["r1"], "supply", {"rows": ["activities"]})
    t = RD.pivot(j, "scenario", "region", "cols")
    assert t.loc["FR240000", "SWHE"] == 30.0 and t.loc["NO080000", "DCOW"] == 15.0
    with pytest.raises(ValueError, match="several stored rows per cell"):
        RD.pivot(j, "scenario", "region", None)


def test_the_filters_choices_follow_the_other_filters(store):
    base, scen = RD.points(store, "scen_a", IDS["r1"])
    assert RD.choices(scen, "supply", {"rows": ["activities"]}, "cols") == ["DCOW", "SWHE"]
    assert "DE110000" in RD.choices(scen, "supply", {"cols": ["SWHE"]}, "region")


def test_two_runs_are_compared_row_by_row(store):
    a, b = RD.run_label("scen_a", IDS["r1"]), RD.run_label("scen_b", IDS["r2"])
    j = RD.compare_runs(store, a, "scenario", store, b, "scenario", None, {})
    d = RD.deviation_summary(j, "A", "B")
    assert int(d["one run only"].sum()) == 0 and int(d["rows differing"].sum()) > 0
    # the same point of the same run: nothing differs
    same = RD.deviation_summary(RD.compare_runs(store, a, "baseline", store, b, "baseline", None, {}), "A", "B")
    assert int(same["rows differing"].sum()) == 0 and float(same["max |rel diff| %"].max()) == 0.0


def test_a_run_without_iteration_records_has_an_empty_iteration_table(store):
    it = RD.iterations(store, "scen_a", IDS["r1"])
    assert list(it.columns) == ["point", "it", "measure", "value"] and it.empty


def test_additive_units_are_the_quantities_and_money():
    assert RD.additive("1000 ha") and RD.additive("1000 t") and RD.additive("EUR million")
    assert not RD.additive("EUR/t") and not RD.additive("%") and not RD.additive("")


def test_a_regional_item_is_drawn_on_its_nuts_regions(store):
    """Each of the fixture's units is one NUTS-2024 region (DE110000 DE11, FR240000 FRB0, NO080000 NO08): the map
    takes the unit's value; the % change is the unit's."""
    v = RD.unit_values(store, "scen_a", IDS["r1"], "supply", "SWHE", "activities")
    assert sorted(v["capri_unit"]) == ["DE110000", "FR240000", "NO080000"]
    m = RD.map_frame(v, "scenario").set_index("nuts2024")
    assert m.at["DE11", "value"] == 15.0 and m.at["FRB0", "value"] == 30.0 and m.at["NO08", "value"] == 75.0
    pc = RD.map_frame(v, "% change").set_index("nuts2024")
    assert np.isclose(pc.at["DE11", "value"], 50.0)


def test_member_states_sum_only_additive_items(store):
    v = RD.unit_values(store, "scen_a", IDS["r1"], "supply", "SWHE", "activities")
    ms = RD.member_state_frame(v.assign(unit="1000 ha"), "scenario").set_index("member_state")
    assert ms.at["DE", "scenario"] == 15.0 and ms.at["NO", "scenario"] == 75.0
    assert RD.member_state_frame(v.assign(unit="EUR/t"), "scenario").empty


def test_the_green_deal_tab_compares_the_run_with_capris_step(store):
    """The Green Deal tab (compare_capri_gd on a stored run): the fixture's wheat area rises 50% in its EU units, beside
    CAPRI's own change of the same units; Norway's unit is left out of the EU and of the map; an N balance item the
    run does not hold is left out."""
    c = RD.gd_capri_effect()
    lev = c[(c["item"] == "LEVL") & (c["activity"] == "SWHE")].set_index("region")
    a = RD.gd_activities(store, "scen_a", IDS["r1"])
    eu = a[(a["region"] == "EU27") & (a["activity"] == "SWHE")].iloc[0]
    assert np.isclose(eu["model_pct"], 50.0) and np.isclose(eu["capri_pct"], lev.at["EU27yr19", "pct_change"])
    assert "NO" not in set(a["region"])
    reg = RD.gd_regional(store, "scen_a", IDS["r1"], "SWHE").set_index("capri_unit")
    assert sorted(reg.index) == ["DE110000", "FR240000"]
    assert np.isclose(reg.at["DE110000", "model_pct"], 50.0)
    assert np.isclose(reg.at["DE110000", "capri_pct"], lev.at["DE110000", "pct_change"])
    m = RD.map_frame(RD.gd_unit_values(reg.reset_index(), "capri"), "% change").set_index("nuts2024")
    assert np.isclose(m.at["DE11", "value"], lev.at["DE110000", "pct_change"])
    assert RD.gd_n_balance(store, "scen_a", IDS["r1"]).empty
