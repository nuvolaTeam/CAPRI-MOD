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


def test_the_uks_units_are_drawn_on_their_nuts_2021_regions():
    """The UK is not in NUTS 2024: its 11 CAPRI units are drawn on their NUTS-2021 level-1 regions, London joined to
    the South East (CAPRI's UKJ00000), and CAPRI's Green Deal pair holds their levels for the comparison's maps."""
    import pandas as pd
    m = RD.nuts_mapping()
    uk = m[m["capri_unit"].str.startswith("UK")]
    assert len(uk) == 11 and set(uk["weight"]) == {1.0} and uk["group"].is_unique
    assert not set(uk["group"]) & set(m.loc[~m["capri_unit"].str.startswith("UK"), "group"])
    ids = {f["id"] for f in RD.nuts_geometry()["features"]}
    assert set(uk["nuts2024"]) <= ids and "UKI" not in ids
    v = pd.DataFrame({"capri_unit": ["UKJ00000"], "unit": "1000 ha", "baseline": [10.0], "scenario": [12.0]})
    assert np.isclose(RD.map_frame(v, "% change").set_index("nuts2024").at["UKJ", "value"], 20.0)
    assert RD.gd_capri_effect_uk()["region"].nunique() == 11


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


def test_the_farm_to_fork_comparison_reads_jrc121368_with_its_sources(store):
    """The tab's Farm-to-Fork comparison: the run's indicators (compare_runs.indicators, % change from its baseline)
    beside JRC121368's published figures, each with its source (capri_data/validation/farm_to_fork_2030); the
    fixture's wheat-led cereals output rises 50% where the run holds it."""
    import pandas as pd

    ref = pd.read_csv(ROOT / "capri_data" / "validation" / "farm_to_fork_2030" / "jrc121368_eu27.csv")
    assert ref["source"].str.startswith("JRC121368").all() and set(ref["kind"]) <= {"table", "text", "figure"}
    d = RD.f2f_jrc(store, "scen_a", IDS["r1"]).set_index("indicator")
    assert set(d.index) == set(ref["indicator"])
    assert d.at["pork price", "jrc_pct"] == 43.0 and d.at["pork price", "kind"] == "table"
    assert np.isclose(d.at["N surplus", "jrc_pct"], -33.5)
    assert set(d["group"]) == {"prices", "herds and production", "environment"}


def test_the_run_choices_show_the_date_and_keep_the_parsed_label(store):
    ch = RD.run_choices(store)
    r = RD.runs(store)
    shown, value = ch[0]
    assert value == RD.run_label(r.iloc[0]["scenario"], r.iloc[0]["run_id"])
    assert shown == f"{str(r.iloc[0]['created'])[:16]} · {value}"
    assert RD.parse_label(value) == (r.iloc[0]["scenario"], str(r.iloc[0]["run_id"])[:RD.ID_SHOWN])


def test_codes_are_named_from_capris_texts_by_their_context():
    # CAPRI's own code: ROWS.csv's text
    assert RD.code_label("SWHE", "cols", "supply") == "SWHE · Soft wheat"
    # a model activity under its own code, named by the CAPRI activity it stands for (codes/model_activities.csv)
    assert RD.code_name("PIGS", "cols", "supply") == "Sows for piglet production"
    assert RD.code_name("CORN", "cols", "supply") == "Grain maize"
    # the same code as a market product: the CAPRI product it stands for (codes/model_commodities.csv)
    assert RD.code_name("SWHE", "rows", "market") == "Aggregate of soft wheat and durum"
    # regions from RALL.csv, the model's EU27 through its CAPRI market region
    assert RD.code_label("ES410000", "region") == "ES410000 · Castilla-Leon"
    assert RD.code_name("EU27", "region") == "European Union 27 after Brexit year 2019"
    # no name: the code alone; a name repeating the code is not shown
    assert RD.code_label("activities", "rows", "supply") == "activities"
    assert RD.code_label("USA", "dim5", "market") == "USA"


def test_the_matched_rows_get_name_columns(store):
    j = RD.scenario_vs_baseline(store, "scen_a", IDS["r1"], "supply", {"rows": ["activities"]})
    n = RD.with_names(j, "supply")
    assert list(n.columns).index("cols name") == list(n.columns).index("cols") + 1
    assert set(n.loc[n["cols"] == "SWHE", "cols name"]) == {"Soft wheat"}
    assert len(n) == len(j)


def test_the_page_opens_on_results_with_the_other_tabs_disabled_unless_asked_for_all_tabs(store, tmp_path):
    gr = pytest.importorskip("gradio")
    import sys
    sys.path.insert(0, str(ROOT / "capri_gradio"))
    import capri_gui as G
    import assistant_llm as L
    for all_tabs in (False, True):
        app = G.build(L.make_backend("none", "", "", ""), tmp_path / "scen", [store], all_tabs=all_tabs)
        tabs = {b.label: b for b in app.blocks.values() if isinstance(b, gr.Tab)}
        # every top tab shown; Assistant, Scenario and Run usable only with all_tabs
        assert all(tabs[k].visible is True for k in ("Assistant", "Scenario", "Run", "Results", "Map"))
        assert all(tabs[k].interactive is all_tabs for k in ("Assistant", "Scenario", "Run"))
        assert tabs["Results"].interactive is True
        # the page opens on Results
        top = [b for b in app.blocks.values() if isinstance(b, gr.Tabs) and b.selected == "results"]
        assert len(top) == 1 and tabs["Results"].id == "results"
        # and the results on the comparison with CAPRI
        inner = [b for b in app.blocks.values() if isinstance(b, gr.Tabs) and b.selected == "capri"]
        assert len(inner) == 1 and tabs["Comparison with CAPRI"].id == "capri"
        # every button as wide as its label (no growth in its row; the page's CSS for columns)
        btns = [b for b in app.blocks.values() if isinstance(b, gr.Button)]
        assert btns and all(b.scale == 0 and "capri-btn" in (b.elem_classes or []) for b in btns)


def test_the_page_title_carries_the_logo_on_its_line(store, tmp_path):
    """18 November 2026 (the project lead): capri-mod's logo beside the page's title, on the same line; the vector
    logo (capri_gradio/assets/capri_mod_logo.svg, no embedded image) inline, with the title line's style in the page's
    CSS (a light ground under the logo in the dark theme)."""
    gr = pytest.importorskip("gradio")
    import base64
    import sys
    sys.path.insert(0, str(ROOT / "capri_gradio"))
    import capri_gui as G
    import assistant_llm as L
    svg = G.LOGO.read_text()
    assert svg.startswith("<svg") and "<image" not in svg and "<path" in svg
    for all_tabs, title in ((False, "capri-mod results"), (True, "capri-mod")):
        app = G.build(L.make_backend("none", "", "", ""), tmp_path / "scen", [store], all_tabs=all_tabs)
        heads = [b.value for b in app.blocks.values() if isinstance(b, gr.HTML) and "capri-head" in str(b.value)]
        assert len(heads) == 1, heads
        h = heads[0]
        assert f'<h2 style="margin:0">{title}</h2>' in h and 'class="capri-logo"' in h
        # the size inline, so the logo is drawn at it before the page's CSS arrives
        assert f'height="{G.LOGO_H}"' in h and f"height:{G.LOGO_H}px" in h and "display:flex" in h
        b64 = h.split("data:image/svg+xml;base64,")[1].split('"')[0]
        assert base64.b64decode(b64).decode() == svg
    assert ".capri-head" in G.PAGE_CSS and ".dark .capri-logo" in G.PAGE_CSS and ".capri-btn" in G.PAGE_CSS


def test_the_tabs_read_as_a_menu(store, tmp_path):
    """18 November 2026 (the project lead: the tabs looked like plain text): the page's top tabs carry capri-tabs-top,
    the results' tabs capri-tabs-sub, and the page's CSS gives both bold labels on a framed, tinted ground, the open tab
    in the accent colour; the tabs nested in them (the comparison with CAPRI's) take the sub style."""
    gr = pytest.importorskip("gradio")
    import sys
    sys.path.insert(0, str(ROOT / "capri_gradio"))
    import capri_gui as G
    import results_browser as RB
    import assistant_llm as L
    app = G.build(L.make_backend("none", "", "", ""), tmp_path / "scen", [store])
    tabs = [b for b in app.blocks.values() if isinstance(b, gr.Tabs)]
    top = [b for b in tabs if "capri-tabs-top" in (b.elem_classes or [])]
    sub = [b for b in tabs if "capri-tabs-sub" in (b.elem_classes or [])]
    assert len(top) == 1 and top[0].selected == "results"
    assert len(sub) == 1 and sub[0].selected == "capri"
    for part in ('.capri-tabs-top > .tab-wrapper button[role="tab"]', '.capri-tabs-sub .tabs > .tab-wrapper',
                 "font-weight: 700", "font-weight: 600", ".selected", "var(--color-accent)", ":disabled"):
        assert part in RB.TAB_CSS, part
    assert RB.TAB_CSS in G.PAGE_CSS and RB.TAB_CSS in RB.PAGE_STYLE
