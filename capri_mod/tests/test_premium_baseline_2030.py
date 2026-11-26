"""The model's 2030 baseline premiums (tools/build/build_price_trajectory_2030.py): for the regions the ports
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
    the 2030/2017 ratio is 0; before 13 November 2026 the empty cell read as 1, the 2017 premium kept."""
    _, lsk, _ = built
    for unit in ("EL110000", "EL120000", "EL140000"):
        assert not port.get((unit, "DCOL")) and not port.get((unit, "DCOH"))
        assert lsk.at[unit, "DCOW"] == 0.0


def test_the_animals_capris_2017_data_pay_none_take_capris_2030_premium_per_head():
    """K210: CAPRI's 2017 data pay Croatia's and Sweden's animals no premium (capreg_cap_premium: empty rows), so the
    2017 coefficient x the 2030/2017 ratio gave them none in 2030, where CAPRI pays them (Croatia's dairy cows 108.7 EUR
    per head, 2017 money). There the projection takes CAPRI's 2030 premium per model head itself
    (capri_livestock_premium_2030.csv); elsewhere the coefficient x the ratio, which equals it within 0.4% (Finland's
    calves: the 2017 coefficient from the res_17 dumps)."""
    from capri_mod.projection.prices import apply_capri_prices_2030
    lp = pd.read_csv(ROOT / "capri_data" / "2017" / "supply" / "livestock_premium_coef.csv", index_col=0)
    lsk = pd.read_csv(TRAJ / "capri_livestock_premium_ratio_2030.csv", index_col=0)
    a30 = pd.read_csv(TRAJ / "capri_livestock_premium_2030.csv", index_col=0)
    both = (lp * lsk).reindex_like(a30)
    m = both.notna() & a30.notna() & (both.abs() > 1e-9)
    assert m.sum().sum() > 2000
    assert ((a30[m] - both[m]) / both[m]).abs().max().max() < 4e-3
    regs = ["HR000000", "SE020000", "DK000000", "EL110000"]
    d = {"livestock_premium_coef": lp.loc[regs].copy()}
    s = apply_capri_prices_2030(d, TRAJ, {}, {})
    out = d["livestock_premium_coef"]
    cattle = ["DCOW", "BCOW", "BULL", "HFRS"]
    assert lp.loc["HR000000"].isna().all() and lp.loc["SE020000", cattle].isna().all()
    assert out.at["HR000000", "DCOW"] == pytest.approx(a30.at["HR000000", "DCOW"], rel=1e-12)
    assert out.at["HR000000", "DCOW"] == pytest.approx(108.721, abs=1e-3)
    assert out.at["SE020000", "BULL"] == pytest.approx(a30.at["SE020000", "BULL"], rel=1e-12)
    assert out.at["DK000000", "DCOW"] == pytest.approx(lp.at["DK000000", "DCOW"] * lsk.at["DK000000", "DCOW"], rel=1e-12)
    assert out.at["EL110000", "DCOW"] == 0.0                     # the ratio's 0 kept (Greece's dairy cows, above)
    assert out.at["EL110000", "SHGF"] == pytest.approx(a30.at["EL110000", "SHGF"], rel=1e-12)
    l4 = lp.loc[regs]
    assert s["livestock_premium_2030_cells"] == int(((l4.isna() | (l4 == 0)) & a30.reindex_like(l4).notna()).sum().sum())
