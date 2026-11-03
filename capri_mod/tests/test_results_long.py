"""The long results table (refactor stage 5; capri_mod/io_results.py): CAPRI's DATAOUT layout, CAPRI's codes declared
in capri_data/codes/results_items.csv, the reference stored once in the Delta store, the pickle's blocks rebuilt.

The run script checks every run's table against its pickle (tools/run/run_f2f_2030.py: "identical to the pickle's
blocks"); these tests check the mechanics on a small set of results in the shape of the model's."""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from capri_mod import io_results as IO
from capri_mod.market.equilibrium import MarketEquilibrium
from capri_mod.supply.supply_module import SupplyResult

ROOT = Path(__file__).resolve().parents[2]


def _results(scale=1.0):
    """Two EU regional units and one of Norway's, three trade regions, two commodities."""
    sup = {}
    for reg, k in (("DE110000", 1.0), ("FR240000", 2.0), ("NO080000", 5.0)):
        v = SupplyResult(region_id=reg, activities=pd.Series({"SWHE": 10.0 * k * scale, "DCOW": 3.0 * k}),
                         gross_output=pd.Series({"SWHE": 70.0 * k * scale, "DCOW": 21.0 * k}),
                         gross_margin=100.0 * k, shadow_prices={"arable_land": 0.5 * k})
        v.manure_tech_shares = {("DCOW", "AmmAppHE"): 0.25}
        v.converged = True
        sup[reg] = v
    regs, coms = ["EU27", "USA", "NO000000"], ["SWHE", "MILK"]
    tab = pd.DataFrame([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], index=regs, columns=coms) * scale
    flows = pd.DataFrame([[0.5, 0.0]] * 9, columns=coms,
                         index=pd.MultiIndex.from_product([regs, regs], names=["exporter", "importer"]))
    mkt = MarketEquilibrium(world_prices=pd.Series({"SWHE": 180.0, "MILK": 350.0}), domestic_prices=tab * 100,
                            production=tab, consumption=tab * 0.9, trade_flows=flows, net_exports=tab * 0.1,
                            welfare=pd.DataFrame({"CSSP": [1.0, 2.0, 3.0]}, index=regs),
                            excess_demand=pd.Series({"SWHE": 0.0, "MILK": 0.0}))
    env = pd.DataFrame({"ghg_total": [1.0, 2.0, 4.0], "n_use_efficiency": [0.5, 0.6, 0.7]},
                       index=pd.Index(["DE110000", "FR240000", "NO080000"], name="region"))
    lab = pd.DataFrame({"LABT": [1.0, 2.0, 3.0]}, index=["DE110000", "FR240000", "NO080000"])
    return {"supply": sup, "market": mkt, "environmental": env, "labour": lab, "set_aside": lab.rename(
        columns={"LABT": "SETA"}), "metadata": {"n_outer_iterations": 3}, "outer_history": [{"it": 1}]}


def test_the_table_has_dataouts_layout_and_capris_codes():
    t = IO.with_capri_codes(IO.to_long(_results(), "base"))
    assert not t.duplicated(["point", "block", "region", "dim5", "cols", "rows"]).any()
    # the supply's items in rows, the activity in cols: DATA(RU, "SWHE", "LEVL")
    r = t[(t.block == "supply") & (t.region == "DE110000") & (t.cols == "SWHE") & (t.rows == "activities")].iloc[0]
    assert (r.capri_region, r.capri_cols, r.capri_rows, r.value) == ("DE110000", "SWHE", "LEVL", 10.0)
    # the market's items in cols, the product in rows: DATA(RM, "Prod", XX); the model's EU27 is CAPRI's EU27yr19
    r = t[(t.block == "market") & (t.region == "EU27") & (t.cols == "production") & (t.rows == "SWHE")].iloc[0]
    assert (r.capri_region, r.capri_cols, r.capri_rows) == ("EU27yr19", "PROD", "WHEA")
    # bilateral flows: the importer as region, the exporter in dim5 (DATAOUT(RMALL, RMALL1, "ImportQ", XX))
    r = t[(t.cols == "trade_flows") & (t.region == "NO000000") & (t.dim5 == "USA") & (t.rows == "SWHE")].iloc[0]
    assert (r.capri_region, r.capri_dim5, r.capri_cols) == ("NO000000", "USA", "ImportQ")
    # a crop's gross output is its product's GROF; an animal's is not mapped (applies_to)
    r = t[(t.block == "supply") & (t.region == "DE110000") & (t.cols == "SWHE") & (t.rows == "gross_output")].iloc[0]
    assert (r.capri_cols, r.capri_rows, r.value) == ("GROF", "SWHE", 70.0)
    # an aggregated activity (DCOW: CAPRI's DCOL and DCOH), an animal's gross output and an unmapped item keep CAPRI's
    # columns empty
    for m in ((t.cols == "DCOW") & (t.rows == "activities"), (t.cols == "DCOW") & (t.rows == "gross_output"),
              t.rows == "gross_margin"):
        assert (t[m][["capri_region", "capri_cols", "capri_rows"]] == "").all().all()
    # EU totals as the run script sums them: Norway's regions left out; no total of a share (n_use_efficiency)
    eu = t[(t.region == "EU27") & (t.block == "supply") & (t.rows == "activities")]
    assert dict(zip(eu.cols, eu.value)) == {"SWHE": 30.0, "DCOW": 9.0}
    env = t[(t.block == "environmental") & (t.region == "EU27")]
    assert dict(zip(env.rows, env.value)) == {"ghg_total": 3.0}
    # an item with fixed CAPRI codes: the region's labour, DATA(RU, "GROF", "LABT")
    r = t[(t.block == "labour") & (t.region == "FR240000")].iloc[0]
    assert (r.capri_cols, r.capri_rows, r.value) == ("GROF", "LABT", 2.0)
    # run metadata and the iterations' record are not rows
    assert not t.block.isin(["metadata", "outer_history"]).any()


def test_an_undeclared_item_stops_the_table():
    r = _results()
    r["supply"]["DE110000"].no_such_item = 1.0
    with pytest.raises(ValueError, match="no_such_item"):
        IO.with_capri_codes(IO.to_long(r, "base"))


def test_every_item_the_supply_module_writes_is_declared():
    """Every field of SupplyResult and every attribute the supply module sets on a regional result is declared in
    results_items.csv, whatever the scenario's options: an item filled only under an option (manure trade's P and K,
    the mineral caps, the nitrate rule) otherwise passes the runs without it and stops the writing of one with it
    (the Green Deal 2030 gate, 3 November 2026: supply.manure_trade_pk)."""
    import dataclasses
    import re
    import capri_mod.supply.supply_module as SM
    src = Path(SM.__file__).read_text()
    written = set(re.findall(r"\bresult\.([a-z_][a-z0-9_]*)\s*=(?!=)", src))
    fields = {f.name for f in dataclasses.fields(SupplyResult)}
    it = IO.results_items()
    declared = set(it.loc[it.block == "supply", "item"])
    assert written, "no result attribute found in the supply module's source"
    assert sorted((written | fields) - set(IO._SUPPLY_TEXT) - declared) == []


def test_every_capri_code_of_the_items_is_capris():
    """results_items.csv: each CAPRI code is in CAPRI's COLS or ROWS (capri_data/codes/capri), in the dimension the
    item takes, with the place where CAPRI sets it."""
    def codes(f):
        with open(ROOT / "capri_data" / "codes" / "capri" / f, newline="") as fh:
            return {r["code"] for r in csv.DictReader(fh)}
    sets = {"cols": codes("COLS.csv"), "rows": codes("ROWS.csv")}
    it = IO.results_items()
    assert not it.duplicated(["block", "item"]).any()
    assert set(it.item_dim) <= {"cols", "rows"}
    assert ((it.item_dim == "cols") == it.block.isin(IO.ITEM_IN_COLS)).all()
    for r in it[it.capri_cols != ""].itertuples():
        assert r.capri_rows != "" and r.capri_source, (r.block, r.item)
        assert r.capri_cols == "*" or r.capri_cols in sets["cols"], (r.block, r.item, r.capri_cols)
        assert r.capri_rows in ("*", "act") or r.capri_rows in sets["rows"], (r.block, r.item, r.capri_rows)


def test_the_reference_is_stored_once_and_the_pickles_blocks_come_back(tmp_path):
    base, scen = _results(), _results(scale=1.5)
    B, S = (IO.with_capri_codes(IO.to_long(x, p)) for x, p in ((base, "base"), (scen, "scen")))
    # the run's metadata has tuple keys (the young animals' markets, the Hessian's records): written as text
    kw = dict(reference="ref_x", year=2030, fingerprint_parts={"code": "a"},
              meta={"conv": True, "markets": {("EU27", "CALV"): 1.0}}, root=tmp_path)
    r1 = IO.write_run(B, S, scenario="scen_a", run_id="r1", **kw)
    r2 = IO.write_run(B, S, scenario="scen_b", run_id="r2", **kw)
    assert not r1["reference_reused"] and r2["reference_reused"] and r2["reference_run_id"] == "r1"
    # another fingerprint (other code or data) stores the reference again
    r3 = IO.write_run(B, S, scenario="scen_a", run_id="r3", **{**kw, "fingerprint_parts": {"code": "b"}})
    assert not r3["reference_reused"]
    runs = IO._runs(tmp_path)
    assert sorted(runs[runs.kind == "reference"].run_id) == ["r1", "r3"]
    rb, rs, rec = IO.read_run(tmp_path, "scen_a")
    assert rec["run_id"] == "r3" and (tmp_path / "meta" / "scen_a" / "r3" / "meta.json").is_file()
    import json
    assert json.loads((tmp_path / "meta" / "scen_a" / "r3" / "meta.json").read_text())["markets"] == {"EU27|CALV": 1.0}
    blocks = IO.pickle_blocks(*IO.as_points(rb, rs))
    assert blocks["act"] == ({"SWHE": 30.0, "DCOW": 9.0}, {"SWHE": 45.0, "DCOW": 9.0})
    assert blocks["base_market"]["prod"] == {"SWHE": 1.0, "MILK": 2.0}
    assert blocks["act_regional"][1]["NO080000"] == {"SWHE": 75.0, "DCOW": 15.0}
    env = blocks["environmental"][0]
    assert env.loc["FR240000", "n_use_efficiency"] == 0.6 and "EU27" not in env.index
    # check_pickle finds a changed number
    out = {k: v for k, v in blocks.items()}
    out["act"] = ({"SWHE": 30.0, "DCOW": 9.0}, {"SWHE": 45.0 + 1e-12, "DCOW": 9.0})
    assert IO.check_pickle(blocks, out) and not IO.check_pickle(blocks, blocks)


def test_the_table_is_read_by_partition(tmp_path):
    """The store is a Delta table partitioned by scenario and run id: a reader takes one partition without the rest."""
    from deltalake import DeltaTable
    B, S = (IO.with_capri_codes(IO.to_long(_results(), p)) for p in ("base", "scen"))
    IO.write_run(B, S, scenario="scen_a", reference="ref_x", year=2030, run_id="r1", fingerprint_parts={},
                 meta={}, root=tmp_path)
    dt = DeltaTable(str(tmp_path / "long"))
    assert dt.metadata().partition_columns == ["scenario", "run_id"]
    part = dt.to_pandas(filters=[("scenario", "=", "ref_x")])
    assert set(part.scenario) == {"ref_x"} and len(part) == len(B)
    assert np.array_equal(np.sort(part.value.to_numpy()), np.sort(B.value.to_numpy()))


def test_the_run_metadata_is_declared():
    """capri_mod/run_meta.py: a key the declaration does not have, or a Hessian record of another source, is refused."""
    from pydantic import ValidationError
    from capri_mod.run_meta import HessianRecord, RunManifest
    HessianRecord(source="computed", products=50, seconds=1.0)
    with pytest.raises(ValidationError):
        HessianRecord(source="guessed")
    with pytest.raises(ValidationError):
        HessianRecord(source="cache", new_field=1)
    m = dict(created="2026-11-03 02:00:00 +0100", seconds_recorded=1, git={"commit": "abc", "changed_files": []},
             software={"python": "3.13"}, environment={}, command=["x"], inputs={"a.csv": {"sha256": "0", "bytes": 1}},
             external_inputs={})
    RunManifest(**m)
    with pytest.raises(ValidationError):
        RunManifest(**{**m, "inputs": {"a.csv": {"sha256": "0"}}})


def test_a_nested_record_comes_back_exactly():
    """encode_record / decode_record (the run script's EU summaries and the outer iterations' records): types kept
    (tuple, list, array, int, bool, NumPy float, text, None, empty containers, tuple keys)."""
    x = {"a": (1.5, 2, True), "b": [{"k": None, "s": "LU"}, []], ("BULL", "AmmAppHE"): np.float64(0.25),
         "c": np.array([1.0, 2.0]), "d": {}, "e": ()}
    y = IO.decode_record(IO.encode_record(x))
    assert y.keys() == x.keys() and y["a"] == (1.5, 2, True) and type(y["a"][1]) is int and y["a"][2] is True
    assert y["b"] == [{"k": None, "s": "LU"}, []] and type(y[("BULL", "AmmAppHE")]) is np.float64
    assert np.array_equal(y["c"], x["c"]) and y["d"] == {} and y["e"] == ()


def test_the_pickle_comes_back_from_the_store(tmp_path):
    """load_store: the blocks rebuilt from the long rows, the summaries (with the environmental tables' label order)
    and both iteration records."""
    base, scen = _results(), _results(scale=1.5)
    B, S = (IO.with_capri_codes(IO.to_long(x, p)) for x, p in ((base, "base"), (scen, "scen")))
    env = (base["environmental"], scen["environmental"])
    out = {"environmental": env, "adoption": ({"PRECFARM": 0.1}, {"PRECFARM": 0.2}), "histosol": {"fallow": 1.0}}
    IO.write_run(B, S, scenario="s", reference="r", year=2030, run_id="a", fingerprint_parts={}, meta={},
                 root=tmp_path, summary=IO.summary_of({**out, "act": None}),
                 iterations=([{"it": 1, "signal": {"SWHE": 0.0}}], [{"it": 1}, {"it": 2}]))
    got = IO.load_run(f"store:{tmp_path}:s")
    assert got["adoption"] == out["adoption"] and got["histosol"] == {"fallow": 1.0}
    assert list(got["environmental"][0].index) == list(env[0].index)
    assert list(got["environmental"][0].columns) == list(env[0].columns)
    assert got["outer_history"] == ([{"it": 1, "signal": {"SWHE": 0.0}}], [{"it": 1}, {"it": 2}])
