"""K189's per-head terms: CAPRI's Green Deal changes every activity's other-input (INPO) coefficient by one regional
percentage (pol_input/greendeal/conventional_io.gms; capmod/define_inputs.gms l. 70-73), so the CAPRI activities a
model animal's split columns move heads between change by their own base INPO; the columns carry that difference
(capri_mod/supply/livestock.py _split_inpo_change; dinpo_rel of dairy_intensity.csv and cattle_intensity.csv)."""
from pathlib import Path

import pandas as pd
import pytest

from capri_mod.supply.livestock import LivestockBlock

ROOT = Path(__file__).resolve().parents[2]
SUP = ROOT / "capri_data" / "2017" / "supply"


def test_the_members_inpo_difference_is_capris():
    """dinpo_rel_2030 = (INPO of DCOL - INPO of DCOH) / INPO of DCOW at CAPRI's 2030 reference (dataOut of
    res_2_1730greendeal_refdefaulta, DE210000: 26.8973, 34.3617, 30.6295)."""
    d = pd.read_csv(SUP / "dairy_intensity.csv", index_col=0)
    assert float(d.at["DE210000", "dinpo_rel_2030"]) == pytest.approx((26.897279 - 34.361689) / 30.629484, abs=1e-6)
    c = pd.read_csv(SUP / "cattle_intensity.csv")
    assert c.dinpo_rel.notna().all() and (c.dinpo_rel != 0).mean() > 0.9


class _Block:
    _split_inpo_change = LivestockBlock._split_inpo_change

    def __init__(self, d):
        self.ev = type("E", (), {"greendeal_animal_inpo": d})()


def test_the_split_column_carries_the_change():
    """The animal's change per head (the Green Deal's INPO change of its average head) times the members' relative
    difference; nothing without the Green Deal's input change."""
    b = _Block({"DCOW": 12.0, "BULL": 3.0})
    assert b._split_inpo_change("DCOW", {"dinpo_rel": -0.25}) == pytest.approx(-3.0)
    assert b._split_inpo_change("BULL", pd.Series({"dinpo_rel": 0.08})) == pytest.approx(0.24)
    assert b._split_inpo_change("HFRS", {"dinpo_rel": 1.4}) == 0.0
    assert _Block(None)._split_inpo_change("DCOW", {"dinpo_rel": -0.25}) == 0.0
    assert b._split_inpo_change("DCOW", {"dinpo_rel": float("nan")}) == 0.0
