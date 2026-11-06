"""CAPRI's 2030 manure applied share, a model input since 3 November 2026 (2017/environment/
manure_npk_applied_share_2030.csv, tools/build/build_npk_balance_2030.py): the input reproduces 1 - MTRADE / EXCRET
from CAPRI's extract exactly, and the model reads no file under capri_data/sources."""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_the_input_is_capris_share_exactly():
    from capri_mod.csvio import read_csv
    from capri_mod.fert.npk import manure_applied_share
    s = read_csv(ROOT / "capri_data" / "sources" / "raw" / "capri" / "results" / "res_2_1730greendeal_refdefaulta" / "npk_dataout_2030.csv.xz", keep_default_na=False)
    s = s[(s.item == "") & (s.row.isin(["EXCRET", "MTRADE"]))]
    v = {(t.region, t.row, t.col): float(t.value) for t in s.itertuples(index=False)}
    want = {(r, {"PHOF": "P", "POTF": "K", "NITF": "N"}[col]): max(0.0, 1.0 - v.get((r, "MTRADE", col), 0.0) / x)
            for (r, row, col), x in v.items() if row == "EXCRET" and x > 0}
    got = manure_applied_share()
    assert got.keys() == want.keys() and all(got[k] == want[k] for k in want)


def test_the_model_reads_no_file_under_sources(tmp_path):
    from capri_mod.data.inputs import RunInputs
    from capri_mod.market.inputs import MarketInputs
    for inp in (RunInputs(tmp_path, "2017"), MarketInputs(tmp_path, "2017")):
        with pytest.raises(ValueError, match="capri_data/sources"):
            inp.path("npk_dataout_2030.csv.xz", "sources/environment")
