"""Tests of the member-state estimation solved (capri_mod/pipeline/captrd/estimate_nlp.py): m_trendMS under the port's
bounds (fix_est.gms) with CAPTRD's widening of infeasible solves (estimate_ms.gms l. 222-436).

Checked against CAPTRD's second solve (Solve2) of Denmark 2030: its supports and wVarErr as CAPTRD stores them,
the port's bounds, CAPTRD's step2 (Solve1's result, estP) as the start. CAPTRD's own Solve2 was infeasible on its
first bounds and stores the bounds it widened them to: the port's widening must reach them. Checked 12 November 2026:
feasible after about 15 tries (CAPTRD at least 7), all but about 15 of 1,625 lower bounds and about 43 upper ones equal
CAPTRD's (the port widens the foodSh upper bounds with INHA's lower ones: IPOPT's multipliers at an infeasible point
spread over both bounds of the degenerate pair HCOM_ couples, CONOPT's marginal sits on one).

Open: the solution itself against CAPTRD's step3 (about 36% of the positions within 0.5%): step3 is the result of a
further cleaning solve (clean_tiny.gms, rem_tiny.gms) on supports and bounds of its own, IPOPT's widening passes over
other blocking bounds than CONOPT's, and the trade positions without a term in the objective are free.
"""
from __future__ import annotations

import pandas as pd
import pytest

from capri_mod.pipeline.captrd import estimate_bounds as EB
from capri_mod.pipeline.captrd import estimate_ms as E
from capri_mod.pipeline.captrd import estimate_nlp as N
from capri_mod.pipeline.tests import test_captrd_estimate_bounds as TB
from capri_mod.pipeline.tests import test_captrd_estimate_ms as TM
from capri_mod.pipeline.tests.test_captrd_estimate_bounds import needs_reference, prepared  # noqa: F401


@pytest.mark.slow
@needs_reference
def test_denmark_2030_solve2_widens_to_captrds_bounds(prepared):  # noqa: F811
    pytest.importorskip("casadi")
    ms, y = "DK000000", 2030
    pos, (lo, up), (Lr, Ur), (D, kw, sup_abs) = TB._case(ms, y, prepared)
    S = E.read_sets()
    B = EB.read_bound_sets()
    tab = {n: TB._by_year(n, ms, [y]).get(y, {}) for n in ("wVarErr", "BASM", "step2")}
    basm = dict(TM._prepared_basm(ms))
    basm.update(kw["basm"])
    basm.update(tab["BASM"])
    kw = {**kw, "basm": basm}
    sup = D.res["Support"]
    p = E.Point(V=sup, support=sup, **{k: v for k, v in kw.items() if k not in ("lo", "up")}, lo=lo, up=up)
    start = E.from_stored(E.Point(V=tab["step2"], support=sup_abs, **{**kw, "lo": {}, "up": {}}), S, tab["step2"])
    pp = prepared[(prepared.region == ms) & (prepared.t == "BASM")]
    pb = {(c, w): float(v) for c, w, v in zip(pp.col, pp.row, pp.value)}
    log = []
    r = N.solve(p, S, B, D, lo, up, tab["wVarErr"], start, expertlo=D.res["expertlo"], expertup=D.res["expertup"],
                basm=lambda c, w: pb.get((c, w), 0.0), log=log)
    assert r.feasible, log[-3:]
    assert r.tries >= 7                      # CAPTRD's general widening starts at the seventh try
    bad_lo = TB._diff(pos, r.lo, Lr, -float("inf"))
    bad_up = TB._diff(pos, r.up, Ur, float("inf"))
    assert len(bad_lo) <= 0.02 * len(pos), bad_lo[:10]
    assert len(bad_up) <= 0.04 * len(pos), bad_up[:10]
    # every equation holds at the solution
    res = E.residuals(E.Point(**{**p.__dict__, "V": r.x, "lo": r.lo, "up": r.up}), S, level=start)
    assert not E.violations(res, 1e-4)


def test_widening_rules():
    """estimate_ms.gms l. 252-321: activity levels only in the first six tries; then 90% of the bound, at least 0.001,
    1% for the processing yields of secondary products; the floor at zero where the base year is positive."""
    B = EB.read_bound_sets()
    p = E.Point(V={}, nobs=set(), bas={}, basm={}, const={}, slope={}, pdata={}, coco=set(),
                support={("PRCY", "RAPO"): 0.4}, lo={}, up={}, year=2030)
    keys = [("SWHE", "LEVL"), ("FEDM", "SWHE"), ("PRCY", "RAPO")]
    lo = {("SWHE", "LEVL"): 100.0, ("FEDM", "SWHE"): 50.0, ("PRCY", "RAPO"): 0.39}
    up = {("SWHE", "LEVL"): 120.0, ("FEDM", "SWHE"): 60.0, ("PRCY", "RAPO"): 0.41}
    at_lo = {("SWHE", "LEVL"): 100.0, ("FEDM", "SWHE"): 50.0, ("PRCY", "RAPO"): 0.39}
    lo1, up1 = dict(lo), dict(up)
    N._widen(3, keys, None, at_lo, {}, lo1, up1, B, p, {}, {}, lambda c, w: 1.0)
    assert lo1[("SWHE", "LEVL")] == 50.0 and lo1[("FEDM", "SWHE")] == 50.0
    lo2, up2 = dict(lo), dict(up)
    N._widen(6, keys, None, at_lo, {}, lo2, up2, B, p, {}, {}, lambda c, w: 1.0)
    assert lo2[("FEDM", "SWHE")] == pytest.approx(5.0)
    assert lo2[("PRCY", "RAPO")] == pytest.approx(0.39 - max(0.001, 0.01 * 0.39))
    assert up2[("PRCY", "RAPO")] == pytest.approx(max(0.41, 1.1 * lo2[("PRCY", "RAPO")]))
