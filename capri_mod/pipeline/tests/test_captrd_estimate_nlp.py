"""Tests of the member-state estimation solved (capri_mod/pipeline/captrd/estimate_nlp.py): m_trendMS under the port's
bounds (fix_est.gms) with CAPTRD's widening of infeasible solves (estimate_ms.gms l. 222-436).

Checked against CAPTRD's second solve (Solve2) of Denmark 2030: its supports and wVarErr as CAPTRD stores them,
the port's bounds, CAPTRD's step2 (Solve1's result, estP) as the start. CAPTRD's own Solve2 was infeasible on its
first bounds and stores the bounds it widened them to: the port's widening must reach them. Checked 12 November 2026:
feasible after about 15 tries (CAPTRD at least 7), all but about 15 of 1,625 lower bounds and about 43 upper ones equal
CAPTRD's (the port widens the foodSh upper bounds with INHA's lower ones: IPOPT's multipliers at an infeasible point
spread over both bounds of the degenerate pair HCOM_ couples, CONOPT's marginal sits on one).

test_denmark_2030_solve1_objective_equals_captrds: Solve1 (CAPTRD's stored support1, the port's bounds on it, the start
at the support) against CAPTRD's step2, Solve1's result. CAPTRD stores the wVarErr of Solve2 only; Solve1's is rebuilt:
on the 2d chain's expert positions as define_stats_and_supports.gms l. 646-663 sets it (test_captrd_eu_supports.py's
chain), on the positions whose trust level stage 2f adds the trend's, MAX(0.05 |wAve|, wVarErr) (l. 327-329, as coded,
not for requirement and feed rows), wVarErr from CAPTRD's stored statistics as wVar x (1 - wR2) (l. 177-179 inverted;
wVar where wR2 is 0, its lower bound) or wAve^2 / 4 with one or two observations (l. 130); elsewhere the stored one.
Checked 12 November 2026: the port's optimum 0.5127, CAPTRD's step2 0.5138 under the same objective; 65% of the
positions within 0.5% of step2, 84% within 2%, the rest mostly trade positions (EXPT, IMPT, NTRD) and other directions
the objective leaves nearly free. With the stored (Solve2) wVarErr instead, step2 scores 2.27 against the port's 0.23:
stage 2f gives FEDM.OCER, FEDM.MOLA and INDM.OCER trust levels at DG AGRI's values (about a hundredth of support1),
and with them standard errors of about 0.2 where Solve1's, the trend's, are near 156 (FEDM.OCER).

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
from capri_mod.pipeline.tests.test_captrd_expert_support import assembled  # noqa: F401
from capri_mod.pipeline.tests.test_captrd_national_supports import (  # noqa: F401
    state, dgagri, aglink_p, scaled, result, need)
from capri_mod.pipeline.tests.test_captrd_macro import population  # noqa: F401


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


def _solve1_wvar(ms, y, assembled):  # noqa: F811
    """Solve1's wVarErr of one member state and year (see the module docstring)."""
    import numpy as np
    from capri_mod.csvio import read_csv
    from capri_mod.pipeline.captrd import final_supports as F
    from capri_mod.pipeline.captrd import prepare as P
    E0, TL0, sup0, X, s, nobs, ex = assembled
    dompos = pd.read_csv(P.SETS_DIR / "dompos.csv", keep_default_na=False).d0.tolist()
    W = F.wvarerr(E0, TL0)
    F.domm_wvarerr(W, sup0, [X.dgagri1, E0, ex["longrun1"]], ms=X.ms, s_colsest=s.s_colsest, s_rowsest=s.s_rowsest,
                   exante=X.exante, dompos=dompos)
    S = E.read_sets()
    out = dict(TB._by_year("wVarErr", ms, [y]).get(y, {}))
    trust = TB._by_year("TrustLevl", ms, [y]).get(y, {})
    d = read_csv(TB.RES / "data.csv.gz", dtype={"t": str}, keep_default_na=False)
    d = d[d.region == ms]
    st = {t: dict(zip(zip(g.col, g.row), g.value.astype(float))) for t, g in d.groupby("t")}
    tl0 = {(c, w) for (r, c, w, t) in TL0 if r == ms and t == y}
    for k in trust:
        n = st.get("nObs", {}).get(k, 0.0)
        if k in tl0 or not n or k[1] in S.reqst or k[1] in S.feed:
            continue
        wave, wvar, wr2 = (st.get(n_, {}).get(k, 0.0) for n_ in ("WAve", "wVar", "wR2"))
        werr = wave * wave * 0.25 if n <= 2 else wvar * (1.0 - wr2)
        out[k] = max(abs(wave) * 0.05, werr)
    out.update({(c, w): v for (r, c, w, t), v in W.items() if r == ms and t == y})
    return out


@pytest.mark.slow
@needs_reference
@need
def test_denmark_2030_solve1_objective_equals_captrds(prepared, assembled):  # noqa: F811
    pytest.importorskip("casadi")
    import numpy as np
    ms, y = "DK000000", 2030
    orig = TB._by_year
    TB._by_year = lambda n, m, ys: orig("support1" if n == "support" else n, m, ys)
    try:
        pos, (lo, up), _, (D, kw, sup_abs) = TB._case(ms, y, prepared)
    finally:
        TB._by_year = orig
    S = E.read_sets()
    B = EB.read_bound_sets()
    tab = {n: TB._by_year(n, ms, [y]).get(y, {}) for n in ("BASM", "step2")}
    basm = dict(TM._prepared_basm(ms))
    basm.update(kw["basm"])
    basm.update(tab["BASM"])
    kw = {**kw, "basm": basm}
    wvar = _solve1_wvar(ms, y, assembled)
    sup = D.res["Support"]
    p = E.Point(V=sup, support=sup, **{k: v for k, v in kw.items() if k not in ("lo", "up")}, lo=lo, up=up)
    ref = E.from_stored(E.Point(V=tab["step2"], support=sup_abs, **{**kw, "lo": {}, "up": {}}), S, tab["step2"])
    pp = prepared[(prepared.region == ms) & (prepared.t == "BASM")]
    pb = {(c, w): float(v) for c, w, v in zip(pp.col, pp.row, pp.value)}
    log = []
    r = N.solve(p, S, B, D, lo, up, wvar, {}, expertlo=D.res["expertlo"], expertup=D.res["expertup"],
                basm=lambda c, w: pb.get((c, w), 0.0), log=log)
    assert r.feasible, log[-3:]
    f_ref = float(E.objective(p, S, lambda c, w: ref.get((c, w), 0.0), wvar, r.lo, r.up, exante_t=not p.exante_d))
    assert abs(r.objective - f_ref) <= 0.01 * f_ref, (r.objective, f_ref)
    keys = [k for k in pos if k in ref or k in r.x]
    rel = np.array([abs(r.x.get(k, 0.0) - ref.get(k, 0.0)) / max(abs(ref.get(k, 0.0)), 1e-3) for k in keys])
    assert np.mean(rel <= 0.02) >= 0.8, np.mean(rel <= 0.02)

