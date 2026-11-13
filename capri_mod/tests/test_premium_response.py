"""CAPRI's premium cut during a scenario's iterations (capri_mod/policy/premium_response.py): factors of 1 at the trend
levels, a cut where a coupled scheme's ceiling binds harder, the weights of the last steps, nothing after step 10."""
from __future__ import annotations

import pytest

from capri_mod.policy.premium_response import PremiumResponse, merge


@pytest.fixture(scope="module")
def pr():
    return PremiumResponse(2030, 2017, (0.55, 0.3, 0.15), 10)


def _model_levels(pr, units):
    """The model levels that reproduce the trend levels (each model activity the sum of its CAPRI activities)."""
    out = {}
    for u in units:
        out[u] = {ma: sum(pr.trend.get((u, m), 0.0) for m in ms) for ma, ms in pr.members.items()}
    return out


def test_factors_are_one_at_the_trend_levels(pr):
    lev = _model_levels(pr, ["FR240000", "IR010000"])
    pr.history = []
    pr.record(1, lev)
    f = pr.factors(1)
    vals = [v for u in ("FR240000", "IR010000") for v in f.get(u, {}).values()]
    assert vals and max(abs(v - 1) for v in vals) < 1e-9


def test_more_suckler_cows_in_france_cut_frances_coupled_beef_premium(pr):
    """Doubling the suckler cows of every French unit doubles the cows under France's coupled beef schemes (VCS,
    ceilings in value): the cows' premium per head falls by about half (0.52 at FR240000); a crop's premium moves only
    through the ceilings it shares with the cows (an RD agri-environment scheme paid per livestock unit and per ha:
    soft wheat -0.02%)."""
    fr = [u for u in pr.units if u.startswith("FR")]
    lev = _model_levels(pr, fr)
    for u in fr:
        lev[u]["BCOW"] *= 2
    pr.history = []
    pr.record(1, lev)
    f = pr.factors(1)
    assert f["FR240000"]["BCOW"] == pytest.approx(0.52, abs=0.01)
    assert f["FR240000"]["SWHE"] == pytest.approx(1.0, abs=1e-3)


def test_the_steps_weights_and_the_tenth_step(pr):
    """The levels of the last three steps weighted 0.55 / 0.3 / 0.15; no new factors after step 10."""
    lev = _model_levels(pr, ["FR240000"])
    pr.history = []
    for s in (1, 2, 3, 4):
        pr.record(s, lev)
    assert len(pr.history) == 3
    assert pr.factors(11) is None
    assert merge({"FR240000": {"BCOW": 2.0}}, {"FR240000": {"BCOW": 0.5, "SWHE": 1.1}}) == {
        "FR240000": {"BCOW": 1.0, "SWHE": 1.1}}
