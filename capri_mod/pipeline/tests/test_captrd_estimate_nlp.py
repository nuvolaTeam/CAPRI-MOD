"""Tests of the member-state estimation solved (capri_mod/pipeline/captrd/estimate_nlp.py): m_trendMS under the port's
bounds (fix_est.gms) with CAPTRD's widening of infeasible solves (estimate_ms.gms l. 222-436).

Checked against CAPTRD's second solve (Solve2) of Denmark 2030: its supports and wVarErr as CAPTRD stores them,
the port's bounds, CAPTRD's step2 (Solve1's result, estP) as the start. CAPTRD's own Solve2 was infeasible on its
first bounds and stores the bounds it widened them to: the port's widening must reach them. Checked 12 November 2026:
with the phase-1 marginals (captrd.nlp_infeasible_marginals, the default) feasible after 26 tries (CAPTRD at least
7), all but 7 of the 1,625 lower bounds and 5 upper ones equal CAPTRD's; with IPOPT's own marginals of the infeasible
solves 15 tries and 13 and 41 (the foodSh upper bounds opened with INHA's lower ones, coupled by HCOM_, as IPOPT's
infeasible stop also carries the objective's pull). The widening turns on near-ties (a bound counts or not within a
tolerance), so its path moves with small differences of the inputs: until 12 November 2026 the data preparation
summed over Python sets in hash order, and runs of this test on the same code gave 7 or 25 differing lower bounds;
with the sums in sorted order the preparation is bit-identical between runs. With the phase 1's proximity term
(captrd.nlp_phase1_proximity) and the deterministic preparation: 16 tries, 8 lower and 10 upper bounds differ.
Hence 2%. These counts are the "phase1" marginals'; since 13 November 2026 the default is "slp" (CONOPT's phase 1 as a
sequential LP, estimate_nlp.phase1_slp, with the IPOPT phase 1 for a try whose phase-1 point is feasible but not
solvable from) and the tie-break; the tests' thresholds hold with it.

test_solve1_objective_equals_captrds: Solve1 (CAPTRD's stored support1, the port's bounds on it, the start
at the support) against CAPTRD's step2, Solve1's result. CAPTRD stores the wVarErr of Solve2 only; Solve1's is rebuilt:
on the 2d chain's expert positions as define_stats_and_supports.gms l. 646-663 sets it (test_captrd_eu_supports.py's
chain), on the positions whose trust level stage 2f adds the trend's, MAX(0.05 |wAve|, wVarErr) (l. 327-329, as coded,
not for requirement and feed rows), wVarErr from CAPTRD's stored statistics as wVar x (1 - wR2) (l. 177-179 inverted;
wVar where wR2 is 0, its lower bound) or wAve^2 / 4 with one or two observations (l. 130); elsewhere the stored one.
Checked 12 November 2026 with the phase-1 marginals: Denmark 2030, the port's optimum 0.51391, CAPTRD's step2 0.51385
under the same objective, 62% of the positions within 2% of step2; Austria 2030, 1,084.8 against 1,092.9, 80% within
2% (with IPOPT's own marginals 787.6: bounds of INHA, foodSh and HCOM opened that CAPTRD did not open). The other
positions are mostly trade (EXPT, IMPT, NTRD) and other directions the objective leaves nearly free, so the objective,
not the share of equal positions, is the test. With the stored (Solve2) wVarErr instead, step2 scores 2.27 against the port's 0.23:
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
from capri_mod.csvio import read_csv
from capri_mod.pipeline.tests import test_captrd_estimate_bounds as TB
from capri_mod.pipeline.tests import test_captrd_estimate_ms as TM
from capri_mod.pipeline.tests.test_captrd_estimate_bounds import needs_reference, prepared  # noqa: F401
from capri_mod.pipeline.tests.test_captrd_expert_support import assembled  # noqa: F401
from capri_mod.pipeline.tests.test_captrd_national_supports import (  # noqa: F401
    state, dgagri, aglink_p, scaled, result, need)
from capri_mod.pipeline.tests.test_captrd_macro import population  # noqa: F401


def EB_SETS():
    from capri_mod.pipeline.captrd import prepare as _P
    return _P.SETS_DIR


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
    counts = (len(bad_lo), len(bad_up), r.tries)
    print("Solve2 DK 2030: lower, upper bounds differing, tries", counts)
    assert len(bad_lo) <= 0.02 * len(pos), (counts, bad_lo[:10])
    assert len(bad_up) <= 0.02 * len(pos), (counts, bad_up[:10])
    # every equation holds at the solution
    res = E.residuals(E.Point(**{**p.__dict__, "V": r.x, "lo": r.lo, "up": r.up}), S, level=start)
    assert not E.violations(res, 1e-4)
    # stage 2f: clean_tiny.gms, then copy_labour_biofuel_on_presult.gms, against CAPTRD's step3 on the positions it
    # holds. The widening's path moves the result by several points (the share within 2% after Solve2 on the port's
    # bounds was 84-94% between runs whose inputs differed in their last digits), so the check starts from Solve2 on
    # CAPTRD's own final bounds (a bound CAPTRD does not store is 0, or infinite where the port's is: an infinite bound
    # is not exported either; NTRD free): feasible at the first solve. 12 November
    # 2026: 95.4% within 2% (Solve2 alone 85.4%), with the full preparation of all countries; the rest the solves' points
    # in the objective's flat directions (trade, the young cattle's feed mix)
    from capri_mod.pipeline.captrd import clean_tiny as CT, step3_copies as SC
    Lc, Uc = dict(lo), dict(up)
    for k in pos:
        Lc[k] = Lr.get(k, -float("inf") if (k[0] == "NTRD" or lo.get(k, -float("inf")) == -float("inf")) else 0.0)
        Uc[k] = Ur.get(k, float("inf") if (k[0] == "NTRD" or up.get(k, float("inf")) == float("inf")) else 0.0)
    pL = E.Point(**{**p.__dict__, "lo": Lc, "up": Uc})
    rL = N.solve(pL, S, B, D, Lc, Uc, tab["wVarErr"], start, expertlo=D.res["expertlo"], expertup=D.res["expertup"],
                 basm=lambda c, w: pb.get((c, w), 0.0))
    assert rL.feasible and rL.tries == 1
    rc = CT.clean(pL, S, B, D, rL, tab["wVarErr"])
    st3 = TB._by_year("step3", ms, [y]).get(y, {})
    ex = TB._by_year("Expert", ms, [y]).get(y, {})
    ref3 = E.from_stored(E.Point(V=st3, support=sup_abs, **{**kw, "lo": {}, "up": {}}), S, st3)
    ex_r = E.from_stored(E.Point(V=ex, support=sup_abs, **{**kw, "lo": {}, "up": {}}), S, ex)
    fos = set(read_csv(EB_SETS() / "fosfuels.csv", keep_default_na=False, dtype=str).d0)
    x3 = SC.copy(rc.x, lambda c, w: pb.get((c, w), 0.0), S.mpact, set(S.mpact) | {a for a, _o in S.pact_to_io}, fos,
                 ex_r, D.res.get("p_data", {}).get(("INHA", "LEVL"), 0.0))
    held = [k for k in sorted(st3) if k in ref3 and k[0] in S.cols_est and k[1] in S.rows_est]
    share = lambda V: sum(abs(V.get(k, 0.0) - ref3[k]) <= 0.02 * max(abs(ref3[k]), 1.0) for k in held) / len(held)  # noqa: E731
    s2, s3 = share(rL.x), share(x3)
    print(f"step3 DK 2030 (Solve2 on CAPTRD's bounds): share within 2%: Solve2 {s2:.3f}, after clean_tiny and the "
          f"copies {s3:.3f} of {len(held)}")
    assert s3 >= 0.93 and s3 > s2 + 0.05


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
@pytest.mark.parametrize("ms,y", [("DK000000", 2030), ("AT000000", 2030)])
def test_solve1_objective_equals_captrds(prepared, assembled, ms, y):  # noqa: F811
    pytest.importorskip("casadi")
    import numpy as np
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
    assert np.mean(rel <= 0.02) >= 0.55, np.mean(rel <= 0.02)

