"""tools/check/compare_baseline_capri.py in the S7 coupling form ("capri"): the production compared with CAPRI's
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
    with open(ROOT / "capri_data" / "2017" / "market" / "market_prod_grof_2030.csv", newline="") as fh:
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
