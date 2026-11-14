"""The model's 2030 baseline premiums (tools/build/build_price_trajectory_2030.py, P2 step 2): for the regions the ports
cover they are the ported premiums (capri_mod/policy/premiums.py at CAPRI's trend levels) in 2017 money, every crop under
its model code (K145), and an activity the ports give no premium has none in 2030."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
TRAJ = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "trajectories"


@pytest.fixture(scope="module")
def built():
    cap = pd.read_csv(TRAJ / "capri_cap_premium_2030.csv", index_col=0)
    lsk = pd.read_csv(TRAJ / "capri_livestock_premium_ratio_2030.csv", index_col=0)
    pr = pd.read_csv(TRAJ / "capri_price_ratios_2030.csv")
    return cap, lsk, dict(zip(pr.ms, pr.deflator))


@pytest.fixture(scope="module")
def port():
    from capri_mod.policy import premiums as pm
    return pm.prme_table(2030, 2017)


def test_every_crop_takes_its_capri_codes_2030_premium(built):
    """WINE is CAPRI's TWIN (codes/model_activities.csv): until K145 its 2030 column was empty and the model kept the
    2017 premium."""
    cap, _, _ = built
    both = cap["TWIN"].notna()
    assert both.sum() > 100
    assert cap.loc[both, "WINE"].notna().all()
    assert (cap.loc[both, "WINE"] - cap.loc[both, "TWIN"]).abs().max() < 1e-9


def test_a_ported_units_crop_premiums_are_the_ports_in_2017_money(built, port):
    cap, _, defl = built
    for unit in ("EL110000", "FR240000", "DE110000"):
        d = defl[unit[:2]]
        for model, capri in (("SWHE", "SWHE"), ("CORN", "MAIZ"), ("OLIV", "OLIV"), ("WINE", "TWIN")):
            v = port.get((unit, capri))
            if v:
                assert cap.at[unit, model] == pytest.approx(v / d, rel=1e-9), (unit, model)


def test_an_activity_the_ports_give_no_premium_has_none_in_2030(built, port):
    """Greece's dairy cows: no 2030 premium in the ports (nor in CAPRI's 2030 reference, where they have levels), so
    the 2030/2017 ratio is 0; before P2 step 2 the empty cell read as 1, the 2017 premium kept."""
    _, lsk, _ = built
    for unit in ("EL110000", "EL120000", "EL140000"):
        assert not port.get((unit, "DCOL")) and not port.get((unit, "DCOH"))
        assert lsk.at[unit, "DCOW"] == 0.0
