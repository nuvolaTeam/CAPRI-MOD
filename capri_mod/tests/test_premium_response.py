"""CAPRI's premium cut during a scenario's iterations (capri_mod/policy/premium_response.py): factors of 1 at the model's
baseline, a cut where a coupled scheme's ceiling binds harder, the weights of the last steps, nothing after step 10.
The model's baseline here is the trend levels summed per model activity in other units (x 0.3: the model's stalls
against CAPRI's produced heads), which the relative change makes irrelevant (DEP-48)."""
from __future__ import annotations

import pytest

from capri_mod.policy.premium_response import PremiumResponse, merge


SCALE = 0.3


def _model_levels(trend, members, units):
    """A model baseline: each model activity the sum of its CAPRI activities' trend levels, times SCALE."""
    return {u: {ma: SCALE * sum(trend.get((u, m), 0.0) for m in ms) for ma, ms in members.items()} for u in units}


@pytest.fixture(scope="module")
def pr():
    from capri_mod.policy import premiums as pm
    from capri_mod.policy.premium_response import _members
    tr = pm.trend_levels()
    return PremiumResponse(2030, 2017, (0.55, 0.3, 0.15), 10, _model_levels(tr, _members(), pm.eu_units(tr)))


def test_factors_are_one_at_the_models_baseline(pr):
    lev = _model_levels(pr.trend, pr.members, ["FR240000", "IR010000"])
    pr.history, pr.regions = [], set()
    pr.record(1, lev)
    f = pr.factors(1)
    assert set(f) == {"FR240000", "IR010000"}
    vals = [v for u in ("FR240000", "IR010000") for v in f.get(u, {}).values()]
    assert vals and max(abs(v - 1) for v in vals) < 1e-9


def test_more_suckler_cows_in_france_cut_frances_coupled_beef_premium(pr):
    """Doubling the suckler cows of every French unit doubles the cows under France's coupled beef schemes (VCS,
    ceilings in value): the cows' premium per head falls by about half (0.52 at FR240000); a crop's premium moves only
    through the ceilings it shares with the cows (an RD agri-environment scheme paid per livestock unit and per ha:
    soft wheat -0.02%)."""
    fr = [u for u in pr.units if u.startswith("FR")]
    lev = _model_levels(pr.trend, pr.members, fr)
    for u in fr:
        lev[u]["BCOW"] *= 2
    pr.history = []
    pr.record(1, lev)
    f = pr.factors(1)
    assert f["FR240000"]["BCOW"] == pytest.approx(0.52, abs=0.01)
    assert f["FR240000"]["SWHE"] == pytest.approx(1.0, abs=1e-3)


def test_the_steps_weights_and_the_tenth_step(pr):
    """The levels of the last three steps weighted 0.55 / 0.3 / 0.15; no new factors after step 10."""
    lev = _model_levels(pr.trend, pr.members, ["FR240000"])
    pr.history = []
    for s in (1, 2, 3, 4):
        pr.record(s, lev)
    assert len(pr.history) == 3
    assert pr.factors(11) is None
    assert merge({"FR240000": {"BCOW": 2.0}}, {"FR240000": {"BCOW": 0.5, "SWHE": 1.1}}) == {
        "FR240000": {"BCOW": 1.0, "SWHE": 1.1}}


def test_the_models_own_dairy_split_moves_dcol_and_dcoh_apart():
    """The dairy cows' shift z (Sprint 7b) moves z stalls from DCOH to DCOL: at an unchanged herd X, DCOL's level is
    its trend level times (s X + z) / (s X) and DCOH's times ((1 - s) X - z) / ((1 - s) X)."""
    import pandas as pd
    from capri_mod.policy import premiums as pm
    from capri_mod.policy.premium_response import ROOT, _members, model_splits
    di = pd.read_csv(ROOT / "capri_data" / "2017" / "supply" / "dairy_intensity.csv", index_col=0)
    u = "FR240000"
    sp = model_splits({"dairy_intensity": di}, u)
    s = float(di.at[u, "share_low"])
    tr = pm.trend_levels()
    base = _model_levels(tr, _members(), [u])
    p = PremiumResponse(2030, 2017, (0.55, 0.3, 0.15), 10, base, {u: {}}, {u: sp})
    X = base[u]["DCOW"]
    p.record(1, base, {u: {"DCOW": 0.1 * X}})
    lev = p.history[-1][1]
    assert lev[(u, "DCOL")] == pytest.approx(tr[(u, "DCOL")] * (s + 0.1) / s)
    assert lev[(u, "DCOH")] == pytest.approx(tr[(u, "DCOH")] * (1 - s - 0.1) / (1 - s))
    assert lev[(u, "SCOW")] == pytest.approx(tr[(u, "SCOW")])
