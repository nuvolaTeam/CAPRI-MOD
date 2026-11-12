"""CAPTRD-MOD stage 2f: clean_tiny.gms (CAPRI star 3.0, captrd/clean_tiny.gms, included by estimate_ms.gms l. 446 after
Solve2): one more solve of m_trendMS that cleans the member state's result of tiny values.

From Solve2's levels (v_estV.L) and bounds, as clean_tiny.gms:
  - l. 22: p_tinyR = p_tiny x sqrt(the member state's NUTS 2 regions)
  - l. 26-43: SupportTiny, wVarErrTiny, Step3Tiny (the levels of the positions with observations or a support; DOMM.DDGS
    only with a support), loTiny, upTiny (the finite bounds of those positions) kept for the restore
  - l. 59: the support := Step3Tiny
  - l. 60-80: where a position is bounded and upTiny > loTiny: the bounds to +-0.5% of its level, at most 3 p_tiny away
    ($ level: a zero level fixes it at zero); l. 85-89: the variances of those positions at trust level 2
  - l. 94-156: the flags: support -1 (pull to zero) below p_tiny/2 (ColsTiny) or p_tinyR/2 (RowsTiny = LEVL), +1
    (pull up to p_tiny, p_tinyR, the upper bound there) up to p_tiny, p_tinyR; NTRD's support from the flagged trade;
    passed on LEVL -> GROF -> EAAG, fodder FEDM and DOMM; zero GROF (MAPR) without imports -> DOMPOS, DOMM, EXPT;
    HCOM -> INHA and EXPE; fodder LEVL -> ColsTinyFodd of the fodder input
  - l. 176-187: the yields of flagged outputs and activities, UVAG of flagged outputs fixed at their level
  - l. 190-224: lower bound 0 where pulled to zero; the aggregates' (GRPR, GRPC, UVAG of GRPR) bounds relaxed
  - l. 228-237: the levels at the planned solution; l. 241-254: the flagged positions' variances at trust level 10
    (LEVL x 0.1), NTRD's weak (trust level 1)
  - l. 270-284: the solve; again once if not optimal; an infeasible solve stops (CAPTRD aborts)
  - l. 296-327: the support, variances and bounds restored; the levels are the result (estP)

clean(...) returns the cleaned levels and the restored bounds (Solve2's: CAPTRD's stored Lo / up).
"""
from __future__ import annotations

import math
from dataclasses import replace
from typing import Dict, Optional, Tuple

from capri_mod.csvio import read_csv
from capri_mod.pipeline.captrd import estimate_bounds as EB
from capri_mod.pipeline.captrd import estimate_ms as E
from capri_mod.pipeline.captrd import estimate_nlp as N

K2 = Tuple[str, str]
INF = float("inf")
#: sets_captrd.gms l. 471: quantities and areas at member-state level are zero or at least p_tiny
P_TINY = 0.1
#: l. 60-80: the bounds of the positions kept within 0.5% of their level, at most 3 p_tiny away
KEEP_UP, KEEP_LO, KEEP_ABS = 1.005, 0.995, 3.0
#: l. 85-89, 241-250: the trust levels of the kept and the flagged positions (standard error = support x 0.05 / 3 x
#: 10 / trust level); the variance floor of the kept ones; the flagged LEVL's variance x (1 - 0.9)
SE_SHARE, TRUST_KEPT, TRUST_FLAGGED, TRUST_NTRD, VAR_FLOOR, LEVL_VAR_CUT = 0.05 / 3, 2.0, 10.0, 1.0, 0.01, 0.9
#: l. 196-224: the aggregates' bounds when a component is pulled to zero: +-1% of the level, at most 10 p_tiny
#: (p_tinyR) away; their unit values +-1% or +-1
AGG_UP, AGG_LO, AGG_ABS, UVAG_ABS = 1.01, 0.99, 10.0, 1.0


def tiny_sets(sets_dir=None) -> dict:
    """clean_tiny.gms's sets (build_captrd_sets.py): ColsTiny, RowsTiny, ColsTinyFodd, FODF, FEDACT_TO_FODDI, and the
    NUTS 2 regions of each member state (MAP_RR on SRNUTS2)."""
    from capri_mod.pipeline.captrd import prepare as _P
    d = _P.SETS_DIR if sets_dir is None else sets_dir
    one = lambda n: set(read_csv(d / f"{n}.csv", keep_default_na=False, dtype=str).d0)            # noqa: E731
    two = lambda n: [tuple(r) for r in read_csv(d / f"{n}.csv", keep_default_na=False, dtype=str)[["d0", "d1"]]
                     .itertuples(index=False)]                                                     # noqa: E731
    nt2 = one("srnuts2")
    n2: Dict[str, int] = {}
    for ms, r in two("map_rr"):
        if r in nt2 and r != ms:
            n2[ms] = n2.get(ms, 0) + 1
    return {"cols_tiny": one("colstiny"), "rows_tiny": one("rowstiny"), "cols_tiny_fodd": one("colstinyfodd"),
            "fodf": one("fodf"), "fedact_to_foddi": two("fedact_to_foddi"), "n_nuts2": n2}


def clean(p: E.Point, S: E.Sets, B: EB.BoundSets, d: EB.BoundData, r2: N.Result, wvar: Dict[K2, float],
          T: Optional[dict] = None, log: Optional[list] = None, opts: Optional[dict] = None) -> N.Result:
    """clean_tiny.gms after Solve2 (r2: Solve2's result, its levels and final bounds; p: Solve2's point, its support;
    wvar: Solve2's wVarErr). Returns the cleaned levels with Solve2's bounds (restored, as CAPTRD stores them)."""
    T = T or tiny_sets()
    pt = P_TINY
    ptr = pt * math.sqrt(T["n_nuts2"].get(d.ms, 0))
    x2, lo2, up2 = r2.x, r2.lo, r2.up
    est = lambda k: k[0] in S.cols_est and k[1] in S.rows_est                                     # noqa: E731
    keys = sorted(k for k in set(x2) | set(p.support) if est(k))
    nobs = p.nobs
    sup0 = p.support
    L = lambda k: x2.get(k, 0.0)                                                                  # noqa: E731
    LO = lambda k: lo2.get(k, -INF)                                                               # noqa: E731
    UP = lambda k: up2.get(k, INF)                                                                # noqa: E731
    # l. 26-43
    has = lambda k: ((k in nobs and k != ("DOMM", "DDGS")) or bool(sup0.get(k)))                  # noqa: E731
    step3t = {k: L(k) for k in keys if has(k)}
    has_b = lambda k: k in nobs or bool(sup0.get(k))                                              # noqa: E731
    lo_t = {k: LO(k) for k in keys if has_b(k) and LO(k) > -INF}
    up_t = {k: UP(k) for k in keys if has_b(k) and UP(k) < INF}
    # l. 59
    sup = {k: step3t.get(k, 0.0) for k in keys}
    lo, up = dict(lo2), dict(up2)
    wv = dict(wvar)
    # l. 60-89
    for k in keys:
        if (UP(k) < INF or LO(k) > -INF) and up_t.get(k, 0.0) > lo_t.get(k, 0.0):
            v = L(k)
            up[k] = max(KEEP_UP * v, KEEP_LO * v, v + KEEP_ABS * pt) if v else 0.0
            lo[k] = min(KEEP_UP * v, KEEP_LO * v, max(v - KEEP_ABS * pt, -INF if v < 0 else 0.0)) if v else 0.0
            if sup.get(k):
                wv[k] = max((sup[k] * SE_SHARE * 10.0 / TRUST_KEPT) ** 2, VAR_FLOOR)
    S3 = lambda k: step3t.get(k, 0.0)                                                             # noqa: E731
    U = lambda k: up.get(k, INF)                                                                  # noqa: E731
    Lb = lambda k: lo.get(k, -INF)                                                                # noqa: E731
    rows = sorted({k[1] for k in keys})
    cols = sorted({k[0] for k in keys})
    # l. 94-97
    for c in sorted(T["cols_tiny"]):
        for w in rows:
            k = (c, w)
            if est(k) and 0.0 < S3(k) < pt / 2:
                sup[k] = -1.0
    # l. 100-103
    for w in rows:
        k = ("NTRD", w)
        if est(k) and (sup.get(("EXPT", w)) == -1 or sup.get(("IMPT", w)) == -1) and U(k) > Lb(k):
            sup[k] = max(0.0, sup.get(("EXPT", w), 0.0)) - max(0.0, sup.get(("IMPT", w), 0.0))
    # l. 108-116
    for c in sorted(T["cols_tiny"]):
        for w in rows:
            k = (c, w)
            if est(k) and pt / 2 <= S3(k) <= pt:
                sup[k] = 1.0
                if U(k) > Lb(k):
                    up[k] = pt
    # l. 121-123
    for c in cols:
        for w in sorted(T["rows_tiny"]):
            k = (c, w)
            if est(k) and 0.0 < S3(k) < ptr / 2:
                sup[k] = -1.0
    # l. 127-139: LEVL -> GROF -> EAAG, fodder FEDM and DOMM
    for w in rows:
        if sum(sup.get((a, "LEVL"), 0.0) for a, o in S.pact_to_y if o == w and a in S.cols_est) == -1:
            sup[("GROF", w)] = -1.0
    for w in rows:
        if sup.get(("GROF", w)) == -1:
            sup[("EAAG", w)] = -1.0
    for w in sorted(T["fodf"]):
        if sup.get(("GROF", w)) == -1:
            sup[("FEDM", w)] = -1.0
            sup[("DOMM", w)] = -1.0
    # l. 144-147: zero GROF (MAPR) without imports
    for w in rows:
        if (sup.get(("GROF", w)) == -1 or sup.get(("MAPR", w)) == -1) and sup.get(("IMPT", w), 0.0) <= 0:
            for c in cols:
                if est((c, w)) and (c in S.dompos or c in ("DOMM", "EXPT")):
                    sup[(c, w)] = -1.0
    # l. 152-154: HCOM -> INHA, EXPE
    for w in rows:
        if sup.get(("HCOM", w)) == -1:
            for c in ("INHA", "EXPE"):
                if est((c, w)):
                    sup[(c, w)] = -1.0
    # l. 158-159: fodder LEVL -> ColsTinyFodd of the fodder input
    for f in sorted({fo for _a, fo in T["fedact_to_foddi"]}):
        if sum(sup.get((a, "LEVL"), 0.0) for a, fo in T["fedact_to_foddi"] if fo == f) == -1:
            for c in sorted(T["cols_tiny_fodd"]):
                if est((c, f)):
                    sup[(c, f)] = -1.0
    # l. 164-171
    for c in cols:
        for w in sorted(T["rows_tiny"]):
            k = (c, w)
            if est(k) and ptr / 2 <= S3(k) <= ptr:
                sup[k] = 1.0
                if U(k) > Lb(k):
                    up[k] = ptr
    # l. 176-187: the yields and unit values of flagged outputs fixed at their level
    for a, w in sorted(S.pact_to_o):
        k = (a, w)
        if a in S.cols_est and est(k) and (sup.get(("GROF", w)) == -1 or sup.get((a, "LEVL")) == -1):
            lo[k] = up[k] = L(k)
    for w in rows:
        k = ("UVAG", w)
        if est(k) and sup.get(("GROF", w)) == -1:
            lo[k] = up[k] = L(k)
    # l. 190-196: lower bound 0 where pulled to zero (the -1 not the original level)
    for k in keys:
        if sup.get(k) == -1 and sup.get(k) != S3(k) and U(k) > Lb(k):
            lo[k] = 0.0
    # l. 199-224: the aggregates
    for e in sorted(B.mrkbalee):
        for g in sorted(S.grpr):
            k = (e, g)
            if not est(k):
                continue
            if any((e, w) in nobs and sup.get((e, w)) == -1 for w, g_ in S.rows_to_g if g_ == g and w in S.rows_est) \
                    and U(k) > Lb(k):
                v = L(k)
                lo[k] = min(AGG_UP * v, AGG_LO * v, max(v - AGG_ABS * pt, -INF if v < 0 else 0.0)) if v else 0.0
    for g in sorted(S.grpc):
        k = (g, "LEVL")
        if not est(k):
            continue
        if any((c, "LEVL") in nobs and sup.get((c, "LEVL")) == -1 for c, g_ in S.cropc_to_g if g_ == g and c in S.mcact) \
                and U(k) > Lb(k):
            v = L(k)
            lo[k] = min(AGG_UP * v, AGG_LO * v, max(v - AGG_ABS * ptr, 0.0)) if v else 0.0
    for g in sorted(S.grpr):
        k = ("UVAG", g)
        if not est(k):
            continue
        if any(("EAAG", w) in nobs and sup.get(("EAAG", w)) == -1 for w, g_ in S.rows_to_g if g_ == g and w in S.rows_est) \
                and U(k) > Lb(k):
            v = L(k)
            lo[k] = min(AGG_LO * v, max(v - UVAG_ABS, 0.0)) if v else 0.0
            up[k] = max(AGG_UP * v, v + UVAG_ABS) if v else 0.0
    # l. 228-237: the levels at the planned solution
    start = dict(x2)
    for k in keys:
        if sup.get(k) == -1 and lo.get(k, -INF) == 0:
            start[k] = 0.0
        if sup.get(k) == 1 and k[1] in T["rows_tiny"] and up.get(k, INF) == ptr:
            start[k] = ptr
        elif sup.get(k) == 1 and up.get(k, INF) == pt:
            start[k] = pt
    # l. 241-254: the flagged positions' variances, NTRD's
    for k in keys:
        if sup.get(k) and sup.get(k) != S3(k) and up.get(k, INF) > lo.get(k, -INF):
            wv[k] = (sup[k] * SE_SHARE * 10.0 / TRUST_FLAGGED) ** 2 * (1.0 - LEVL_VAR_CUT * (k[1] == "LEVL"))
    for w in rows:
        k = ("NTRD", w)
        if est(k) and (sup.get(("EXPT", w)) == -1 or sup.get(("IMPT", w)) == -1) and up.get(k, INF) > lo.get(k, -INF):
            wv[k] = (1.0 * SE_SHARE * 10.0 / TRUST_NTRD) ** 2
    # l. 270-284: the solve, again once if not optimal; infeasible: CAPTRD aborts
    pc = replace(p, support=sup, lo=lo, up=up)
    o = {**(opts or {}), "nlp_max_tries": 0}
    r = N.solve(pc, S, B, d, lo, up, wv, start, log=log, opts=o, widen=False)
    if r.status not in ("Solve_Succeeded",):
        r = N.solve(pc, S, B, d, lo, up, wv, r.x, log=log, opts=o, widen=False)
    if not r.feasible:
        raise RuntimeError(f"clean_tiny {d.ms} {d.year}: the cleaning solve is infeasible ({r.status}); CAPTRD aborts")
    # l. 296-327: the support, variances and bounds restored (Lo, up stored are Solve2's)
    return N.Result(r.x, r.objective, True, r.tries, r.status, dict(lo2), dict(up2))
