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


@pytest.fixture
def store(tmp_path):
    B, S = (IO.with_capri_codes(IO.to_long(x, p)) for x, p in ((_results(), "base"), (_results(scale=1.5), "scen")))
    kw = dict(reference="ref_x", year=2030, fingerprint_parts={"code": "a"}, root=tmp_path)
    IO.write_run(B, S, scenario="scen_a", run_id="r1",
                 meta={"conv": True, "it": 4, "settings_changed": {"market": {"demand_calibration": "capri"}},
                       "options": {"regions": "DE110000,FR240000"}}, **kw)
    IO.write_run(B, B, scenario="scen_b", run_id="r2", meta={"conv": False}, **kw)
    return tmp_path


def test_the_runs_are_listed_newest_first_with_their_metadata(store):
    r = RD.runs(store)
    assert list(r["scenario"]) == ["scen_b", "scen_a"]
    a = r[r["scenario"] == "scen_a"].iloc[0]
    assert a["converged"] and a["iterations"] == 4 and a["regions"] == 2 and a["reference"] == "ref_x"
    assert a["settings changed"] == "market.demand_calibration=capri"
    assert r[r["scenario"] == "scen_b"].iloc[0]["reference_run_id"] == "r1"     # the reference stored once


def test_the_scenario_is_matched_with_its_baseline(store):
    j = RD.scenario_vs_baseline(store, "scen_a", "r1", "supply", {"rows": ["activities"]})
    sw = j[(j["region"] == "DE110000") & (j["cols"] == "SWHE")].iloc[0]
    assert sw["baseline"] == 10.0 and sw["scenario"] == 15.0
    assert sw["scenario - baseline"] == 5.0 and np.isclose(sw["% change"], 50.0)
    # the browser writes nothing: the store's records are unchanged
    assert len(IO._runs(store)) == 3


def test_the_pivot_takes_single_rows_and_never_sums(store):
    j = RD.scenario_vs_baseline(store, "scen_a", "r1", "supply", {"rows": ["activities"]})
    t = RD.pivot(j, "scenario", "region", "cols")
    assert t.loc["FR240000", "SWHE"] == 30.0 and t.loc["NO080000", "DCOW"] == 15.0
    with pytest.raises(ValueError, match="several stored rows per cell"):
        RD.pivot(j, "scenario", "region", None)


def test_the_filters_choices_follow_the_other_filters(store):
    base, scen = RD.points(store, "scen_a", "r1")
    assert RD.choices(scen, "supply", {"rows": ["activities"]}, "cols") == ["DCOW", "SWHE"]
    assert "DE110000" in RD.choices(scen, "supply", {"cols": ["SWHE"]}, "region")


def test_two_runs_are_compared_row_by_row(store):
    a, b = RD.run_label("scen_a", "r1"), RD.run_label("scen_b", "r2")
    j = RD.compare_runs(store, a, "scenario", store, b, "scenario", None, {})
    d = RD.deviation_summary(j, "A", "B")
    assert int(d["one run only"].sum()) == 0 and int(d["rows differing"].sum()) > 0
    # the same point of the same run: nothing differs
    same = RD.deviation_summary(RD.compare_runs(store, a, "baseline", store, b, "baseline", None, {}), "A", "B")
    assert int(same["rows differing"].sum()) == 0 and float(same["max |rel diff| %"].max()) == 0.0


def test_a_run_without_iteration_records_has_an_empty_iteration_table(store):
    it = RD.iterations(store, "scen_a", "r1")
    assert list(it.columns) == ["point", "it", "measure", "value"] and it.empty
