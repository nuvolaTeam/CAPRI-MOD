"""CAPTRD's sets of estimated series (capri_data/pipeline/captrd/sets, tools/build/build_captrd_sets.py) against the series
CAPTRD actually estimated in the reference run (capri_reference/captrd_results/1770, data position nObs > 0)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
SETS = ROOT / "capri_data" / "pipeline" / "captrd" / "sets"
RES = ROOT / "capri_reference" / "captrd_results" / "1770"


def _set(name):
    return set(pd.read_csv(SETS / f"{name}.csv").d0)


def test_group_mappings_are_consistent():
    cg = pd.read_csv(SETS / "cropc_to_g.csv")
    assert set(cg.d1) == _set("grpc")
    rg = pd.read_csv(SETS / "rows_to_g.csv")
    assert set(rg.d1) == _set("grpr")
    assert _set("grpc") <= _set("s_colsest") and _set("grpr") <= _set("s_rowsest")


@pytest.mark.skipif(not (RES / "data.csv.gz").exists(), reason="CAPTRD reference results not built")
def test_every_estimated_series_is_in_the_sets():
    d = pd.read_csv(RES / "data.csv.gz")
    n = d[(d.t == "nObs") & (d.value > 0)][["col", "row"]].drop_duplicates()
    assert len(n) > 1800
    assert n.col.isin(_set("s_colsest")).all(), sorted(set(n.col) - _set("s_colsest"))
    assert n.row.isin(_set("s_rowsest")).all(), sorted(set(n.row) - _set("s_rowsest"))
