"""CAPRI's feed chain of the simulation year (capri_mod/feed/chain.py): its literal tables, and the chain for Denmark on
CAPRI's inputs against CAPRI's 2030 reference start sim_ini_21730 (tools/check/check_feed_chain_2030.py)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "lib"), str(ROOT / "tools" / "check")]

from capri_mod.feed import chain  # noqa: E402

#: the simulation's start against sim_ini_21730 (relative): Denmark's largest, 9.5e-6 (SHGF's FISF), on 25 November 2026
TOL_START = 1e-4


def test_the_literal_tables_are_the_checks():
    """req_or_man_params reads capri_data/2017/feed/req_or_man_params.csv as the requirement checks read it."""
    import check_manure_output_2030 as chk
    mine, ref = chain.req_or_man_params(), chk.params()
    assert set(mine) == set(ref)
    for sym in ref:
        assert mine[sym] == ref[sym], sym


@pytest.mark.slow
def test_denmark_gives_capris_2030_start():
    """Denmark, its year's data from CAPREG's base year and CAPRI's trends: the calibration's feed input coefficients
    within 1e-4 of sim_ini_21730's, and the simulation's start (p_animReq, the protein factor, the shares, the days)
    within TOL_START."""
    from paths import REFERENCE
    import feed_chain_inputs as fci
    if not (REFERENCE / "simini" / "simini_21730" / "v_feedInpCoeff.csv.gz").exists() or \
            not (fci.CAPREG_BASE / "DK.csv.gz").exists():
        pytest.skip("CAPRI's reference run or CAPREG's base year is not available")
    try:
        fci.raw_folder(None)
    except Exception as e:        # no access to the gated raw dataset
        pytest.skip(f"the raw dataset is not available: {e}")
    import check_feed_chain_2030 as chk
    import check_fedtrm_cal_2030 as fc
    import check_requirements_2030 as req
    import pandas as pd
    res = chain.feed_chain(fci.chain_inputs("DK"))
    ref = pd.read_csv(req.SIMINI / "v_feedInpCoeff.csv.gz", dtype={"d0": str, "d1": str, "d2": str, "d3": str})
    tt = fc.compare(res.cal, ref)
    assert len(tt) > 100 and (tt.rel.abs() < 1e-4).all()
    assert not tt.attrs["extra"]
    for (name, item), xs in chk.start_stats(res).items():
        assert max(x[0] for x in xs) <= TOL_START, (name, item, max(xs))
