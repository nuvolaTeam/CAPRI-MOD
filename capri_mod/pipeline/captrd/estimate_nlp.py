"""CAPTRD's member-state estimation solved: the NLP m_trendMS (estimate_ms.residuals, objective) under the bounds
(estimate_bounds.bounds), with CAPTRD's widening of the bounds of an infeasible solve (estimate_ms.gms l. 222-436), for
one member state and ex-ante year. IPOPT (CasADi) in place of CAPTRD's CONOPT.

The widening, as CAPTRD's: after an infeasible solve, the bounds at which the solution lies with a nonzero multiplier
are opened; in the first six tries only the activity levels (MPACT.LEVL: an upper bound to twice the level, a lower
one to half of it, l. 252-268), from the seventh on every position (a lower bound moved down by 90% of its absolute
value, at least 0.001, 1% for the processing yields of the secondary products, then at least zero where the base year
is positive; the upper ones alike, l. 270-321), the calories (INCE) by small steps with their expert bounds
(l. 276-288);
then the bounds CAPTRD sets again (l. 322-420: the activity levels' floor and range, the population, the sugar beets,
comi_bounds.gms, biofuel_bounds.gms below 30 tries, UAAR, the fixed land, ARTIF, the requirement functions' limits, the
365 days). After 50 tries CAPTRD stops (l. 222-229 and 568-571).

Departure from CAPRI (the solver): CONOPT's active-set solution lies exactly at its bounds and its marginals of an
infeasible solve mark the blocking bounds; IPOPT's interior-point solution approaches them, so a bound counts as
reached within captrd.nlp_at_bound_tol (relative) with a multiplier beyond captrd.nlp_marginal_tol. CONOPT reports an
infeasible model at the point of its phase 1, the least sum of infeasibilities, with that objective's marginals; IPOPT's
own infeasible stop also carries the objective's pull on the bounds. With captrd.nlp_infeasible_marginals = "phase1"
(the default) an infeasible solve is followed by that least-infeasibility problem (the equations' violations as
nonnegative slacks, their sum minimised within the bounds), and its point and marginals drive the widening. Where the objective
leaves directions free (a trade position without a support and its counterpart, both free of the objective), the
two solvers can end at different points of equal objective.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from capri_mod.pipeline.captrd import estimate_bounds as EB
from capri_mod.pipeline.captrd import estimate_ms as E

K2 = Tuple[str, str]
INF = float("inf")
#: estimate_ms.gms l. 252: the first tries (nRepeatedSolves <= 5) widen the activity levels only
LEVL_TRIES = 5
#: l. 262, 268: an activity level's bounds to twice and half the level
LEVL_UP_FAC = 2.0
LEVL_LO_FAC = 0.5
#: l. 296-311: a bound moves by 90% of its absolute value, at least 0.001; 1% for PRCY of the secondary products
WIDEN_SHARE = 0.9
WIDEN_SHARE_PRCY = 0.01
WIDEN_MIN = 0.001
#: l. 304-305: the processing yields not below 1% of their support
PRCY_FLOOR = 0.01
#: l. 314-315: the processing yields' upper bound at least 1.1 x the lower
PRCY_RANGE = 1.1
#: l. 280-287: the calories' bounds by (1 -/+ 1e-5 n)^n
INCE_STEP = 1.0e-5
#: IPOPT's returns that are solver errors, not an infeasible model: CAPTRD aborts on a solver error (EXECERROR,
#: estimate_ms.gms l. 230, 243), so the estimation stops rather than widen bounds after one
SOLVER_ERRORS = ("Insufficient_Memory", "Internal_Error", "Invalid_Option", "Invalid_Problem_Definition",
                 "Unrecoverable_Exception", "NonIpopt_Exception_Thrown", "Not_Enough_Degrees_Of_Freedom")
#: l. 330: the OIND / OCRO rule after 25 tries
OIND_OCRO_TRIES = 25
#: biofuel_bounds.gms is applied again below 30 tries (l. 381-384)
BIOFUEL_TRIES = 30
#: release_comi_yields.gms: the milk yields' step, LOSF.COMI's factors
COMI_STEP = 1.0e-4
LOSF_UP = 1.005
LOSF_LO = 0.995


@dataclass
class Result:
    x: Dict[K2, float]
    objective: float
    feasible: bool
    tries: int
    status: str
    lo: Dict[K2, float]
    up: Dict[K2, float]


def _settings():
    from capri_mod.settings import current
    st = current()
    keys = ("captrd.nlp_tol", "captrd.nlp_max_iter", "captrd.nlp_tolinfeas", "captrd.nlp_max_tries",
            "captrd.nlp_at_bound_tol", "captrd.nlp_marginal_tol", "captrd.nlp_infeasible_marginals",
            "captrd.nlp_phase1_proximity")
    return {k.split(".", 1)[1]: st.get(k) for k in keys}


def solve(p: E.Point, S: E.Sets, B: EB.BoundSets, d: EB.BoundData, lo: Dict[K2, float], up: Dict[K2, float],
          wvar: Dict[K2, float], start: Dict[K2, float], expertlo: Dict[K2, float] = None,
          expertup: Dict[K2, float] = None, basm: Optional[callable] = None, log: Optional[List[str]] = None,
          opts: Optional[dict] = None, widen: bool = True) -> Result:
    """m_trendMS for one member state and year. p: the point's data (support relative, as the bounds); lo, up: the
    bounds (estimate_bounds.bounds); wvar: wVarErr; start: the starting levels (CAPTRD: estP of the previous solve, else
    the support, estimate_ms.gms l. 79-90); basm(c, w): p_data's BASM (the widening's floor at zero). widen=False: one
    solve, no widening (clean_tiny.gms's solve, which aborts on an infeasible model instead)."""
    import casadi as ca
    o = dict(_settings())
    o.update(opts or {})
    expertlo, expertup = expertlo or {}, expertup or {}
    basm = basm or (lambda c, w: d.pd(c, w, "BASM"))
    keys: List[K2] = []
    idx: Dict[K2, int] = {}
    syms = []

    def var(c, w):
        k = (c, w)
        if k not in idx:
            idx[k] = len(keys)
            keys.append(k)
            syms.append(ca.SX.sym(f"{c}.{w}"))
        return syms[idx[k]]
    lo_, up_ = dict(lo), dict(up)
    res = E.residuals(E.Point(**{**p.__dict__, "lo": lo_, "up": up_}), S, var=var, level=start)
    f = E.objective(p, S, var, wvar, lo_, up_, exante_t=not p.exante_d)
    order = sorted(range(len(keys)), key=lambda i: keys[i])     # the variables in a fixed order
    keys = [keys[i] for i in order]
    syms = [syms[i] for i in order]
    idx = {k: i for i, k in enumerate(keys)}
    X = ca.vertcat(*syms)
    G = ca.vertcat(*[r[3] for r in res])
    lbg = np.array([0.0 if r[2] in "EG" else -INF for r in res])
    ubg = np.array([0.0 if r[2] in "EL" else INF for r in res])
    solver = ca.nlpsol("m_trendMS", "ipopt", {"x": X, "f": f, "g": G},
                       {"ipopt.print_level": 0, "print_time": 0, "ipopt.tol": float(o["nlp_tol"]),
                        "ipopt.max_iter": int(o["nlp_max_iter"]), "ipopt.fixed_variable_treatment": "make_constraint"})
    gfun = ca.Function("g", [X], [G])
    phase1 = str(o["nlp_infeasible_marginals"]) == "phase1"
    if phase1:
        # CONOPT reports an infeasible solve at its phase 1's point, the least sum of infeasibilities within the bounds,
        # with that objective's marginals: the bounds blocking feasibility, not those the objective pulls at
        # with nothing in the objective on X an interior-point solve drifts the free directions to the middle of their
        # boxes (up to the standard 1e9); CONOPT's phase 1 moves from the given point: a small proximity term to the
        # infeasible solve's point (xhat, scaled by max(1, |xhat|)), weight captrd.nlp_phase1_proximity
        m = int(G.shape[0])
        sp, sn = ca.SX.sym("sp", m), ca.SX.sym("sn", m)
        xh, xs_ = ca.SX.sym("xhat", X.shape[0]), ca.SX.sym("xscale", X.shape[0])
        f1 = ca.sum1(sp) + ca.sum1(sn) + float(o["nlp_phase1_proximity"]) * ca.sumsqr((X - xh) / xs_)
        ph1 = ca.nlpsol("m_trendMS_phase1", "ipopt",
                        {"x": ca.vertcat(X, sp, sn), "p": ca.vertcat(xh, xs_), "f": f1, "g": G - sp + sn},
                        {"ipopt.print_level": 0, "print_time": 0, "ipopt.tol": float(o["nlp_tol"]),
                         "ipopt.max_iter": int(o["nlp_max_iter"]),
                         "ipopt.fixed_variable_treatment": "make_constraint"})
    # l. 83-100: the positions with data start at estP (the previous solve's result) if there is one, else at the
    # support; the others at their levels (in Solve2: Solve1's result, estP)
    has_start = any(v for v in start.values())
    nobs_i = np.array([k in p.nobs for k in keys], dtype=bool)
    x_est = np.array([start.get(k, 0.0) if has_start else p.support.get(k, 0.0) for k in keys])
    x0 = np.array([start.get(k, 0.0) if has_start else p.support.get(k, 0.0) for k in keys])
    log = log if log is not None else []
    tol_at, tol_m = float(o["nlp_at_bound_tol"]), float(o["nlp_marginal_tol"])
    sol = None
    for ntry in range(int(o["nlp_max_tries"]) + 1):
        lb = np.array([lo_.get(k, -INF) for k in keys])
        ub = np.array([up_.get(k, INF) for k in keys])
        xs = np.clip(x0, np.where(np.isfinite(lb), lb, -1e30), np.where(np.isfinite(ub), ub, 1e30))
        sol = solver(x0=xs, lbx=lb, ubx=ub, lbg=lbg, ubg=ubg)
        x = np.array(sol["x"]).ravel()
        gv = np.array(gfun(x)).ravel()
        viol = float(np.maximum(np.maximum(lbg - gv, gv - ubg), 0.0).max()) if len(gv) else 0.0
        status = solver.stats()["return_status"]
        log.append(f"try {ntry}: {status}, max. infeasibility {viol:.2e}, SSQ {float(sol['f']):.6g}")
        if status in SOLVER_ERRORS:
            raise RuntimeError(f"m_trendMS {d.ms} {d.year}: solver error {status} at try {ntry}")
        ok = viol <= float(o["nlp_tolinfeas"]) and status in ("Solve_Succeeded", "Solved_To_Acceptable_Level")
        if ok or not widen:
            return Result({k: float(x[i]) for i, k in enumerate(keys)}, float(sol["f"]), ok, ntry + 1, status,
                          lo_, up_)
        lam = np.array(sol["lam_x"]).ravel()
        if phase1:
            nk = len(keys)
            viol_v = np.maximum(lbg - gv, 0.0), np.maximum(gv - ubg, 0.0)
            p1 = ph1(x0=np.concatenate([x, viol_v[1], viol_v[0]]), lbx=np.concatenate([lb, np.zeros(2 * m)]),
                     ubx=np.concatenate([ub, np.full(2 * m, INF)]), lbg=lbg, ubg=ubg,
                     p=np.concatenate([x, np.maximum(1.0, np.abs(x))]))
            if ph1.stats()["return_status"] in SOLVER_ERRORS:
                raise RuntimeError(f"m_trendMS {d.ms} {d.year}: phase 1 solver error {ph1.stats()['return_status']}")
            z = np.array(p1["x"]).ravel()
            x, lam = z[:nk], np.array(p1["lam_x"]).ravel()[:nk]
            log.append(f"    phase 1: {ph1.stats()['return_status']}, sum of infeasibilities {float(p1['f']):.3e}")
        at_lo, at_up = _binding(keys, x, lam, lb, ub, tol_at, tol_m)
        _widen(ntry, keys, x, at_lo, at_up, lo_, up_, B, p, expertlo, expertup, basm)
        _oind_ocro(ntry, keys, x, at_lo, lo_)
        _again(ntry, d, B, lo_, up_, expertup, at_lo, at_up)
        # l. 349-353: the levels stay at the last solve's, but those with data go back to estP
        x0 = np.where(nobs_i & has_start, x_est, x)
    x = np.array(sol["x"]).ravel()
    return Result({k: float(x[i]) for i, k in enumerate(keys)}, float(sol["f"]), False, ntry + 1, status, lo_, up_)


def _binding(keys, x, lam, lb, ub, tol_at, tol_m):
    """The bounds the solution lies at with a nonzero multiplier (GAMS: ABS(v.M) GT EPS and v.LO EQ v.L): {key: level}
    for the lower and the upper ones; fixed positions excluded."""
    at_lo, at_up = {}, {}
    for i, k in enumerate(keys):
        if abs(lam[i]) <= tol_m or lb[i] == ub[i]:
            continue
        if lam[i] < 0 and np.isfinite(lb[i]) and abs(x[i] - lb[i]) <= tol_at * max(1.0, abs(lb[i])):
            at_lo[k] = float(x[i])
        if lam[i] > 0 and np.isfinite(ub[i]) and abs(x[i] - ub[i]) <= tol_at * max(1.0, abs(ub[i])):
            at_up[k] = float(x[i])
    return at_lo, at_up


def _widen(ntry, keys, x, at_lo, at_up, lo_, up_, B, p, expertlo, expertup, basm):
    """estimate_ms.gms l. 252-321 (nRepeatedSolves = ntry)."""
    if ntry <= LEVL_TRIES:
        for k, v in at_up.items():
            if k[0] in B.mpact and k[1] == "LEVL" and up_.get(k) != expertup.get(k):
                up_[k] = v * LEVL_UP_FAC
        for k, v in at_lo.items():
            if k[0] in B.mpact and k[1] == "LEVL" and lo_.get(k) != expertlo.get(k):
                lo_[k] = v * LEVL_LO_FAC
        return
    cols = B.cols_est | {"STCM"}                    # l. 276, 321: STCM is opened with the rest
    moved = set()
    for k in sorted(at_lo):
        if k[1] == "INCE" and k[0] in _ncnc(p) and expertlo.get(k):
            lo_[k] = lo_[k] * (1 - INCE_STEP * ntry) ** ntry
            moved.add(("lo", k))
    for k in sorted(at_up):
        if k[1] == "INCE" and k[0] in _ncnc(p) and expertup.get(k):
            up_[k] = up_[k] * (1 + INCE_STEP * ntry) ** ntry
            moved.add(("up", k))
    for k in sorted(at_lo):
        c, w = k
        if ("lo", k) not in moved and c in cols and w in B.rows_est:
            sh = WIDEN_SHARE_PRCY if (c == "PRCY" and w in B.seco) else WIDEN_SHARE
            lo_[k] = lo_[k] - max(WIDEN_MIN, sh * abs(lo_[k]))
    for k in sorted(at_up):
        c, w = k
        if ("up", k) not in moved and c in cols and w in B.rows_est:
            sh = WIDEN_SHARE_PRCY if (c == "PRCY" and w in B.seco) else WIDEN_SHARE
            up_[k] = up_[k] + max(WIDEN_MIN, sh * abs(up_[k]))
    if ntry > LEVL_TRIES:
        for k in keys:
            c, w = k
            # a free position's lower bound is -inf in GAMS: MAX(0, -inf, ..) gives it the floor too
            if c in cols and w in B.rows_est and basm(c, w) > 0 and c not in ("NTRD", "INTP"):
                lo_[k] = max(0.0, lo_.get(k, -INF), PRCY_FLOOR * p.support.get(k, 0.0) if c == "PRCY" else 0.0)
            if c == "PRCY" and k in lo_ and lo_.get(k, -INF) != up_.get(k, INF):
                up_[k] = max(up_.get(k, INF), PRCY_RANGE * lo_[k])


def _oind_ocro(ntry, keys, x, at_lo, lo_):
    """estimate_ms.gms l. 330-346: after 25 tries the lower bounds of OIND and OCRO's levels at a binding bound go to
    zero where the solution has no production (GROF) of them."""
    if ntry <= OIND_OCRO_TRIES:                     # nRepeatedSolves > 25 (nRepeatedSolves = ntry here)
        return
    lev = dict(zip(keys, x))
    for c in ("OIND", "OCRO"):
        k = (c, "LEVL")
        if k in at_lo and lev.get(("GROF", c), 0.0) == 0.0:
            lo_[k] = 0.0


def _ncnc(p):
    return {c for c, w in p.nobs if w == "INCE"}


def _again(ntry, d, B, lo_, up_, expertup, at_lo, at_up):
    """estimate_ms.gms l. 322-420: the bounds CAPTRD sets again after widening."""
    pd, res, t = d.pd, d.res, d.year
    R = lambda rp, c, w: res.get(rp, {}).get((c, w), 0.0)                  # noqa: E731
    n = lambda c, w: pd(c, w, "nObs") != 0                                  # noqa: E731
    LO = lambda k: lo_.get(k, -INF)                                         # noqa: E731
    UP = lambda k: up_.get(k, INF)                                          # noqa: E731
    for a in sorted(B.mpact):
        k = (a, "LEVL")
        if n(a, "LEVL") and LO(k) != 0:
            lo_[k] = max(EB_LEVL_FLOOR * d.nuts2_with_data.get(a, 0), LO(k))
    for a in sorted(B.mpact):
        k = (a, "LEVL")
        if n(a, "LEVL") and LO(k) != UP(k) and UP(k) != expertup.get(k):
            up_[k] = max(LO(k) * PRCY_RANGE, UP(k))
    pop = R("p_data", "INHA", "LEVL")
    lo_[("INHA", "LEVL")] = up_[("INHA", "LEVL")] = pop
    if pd("QUTS", "SUGB", "BASM") and t >= 2006:
        lo_[("GROF", "SUGB")] = min(R("p_data", "QUTS", "SUGB"), LO(("GROF", "SUGB")))

    def fx(k, v):
        lo_[k] = v
        up_[k] = v
    sup = lambda c, w: R("Support", c, w)                                  # noqa: E731
    EB._comi(d, B, lo_, up_, LO, UP, n, pd, R, sup, fx, t)
    _release_comi(ntry, B, lo_, up_, n, at_lo, at_up)
    if ntry < BIOFUEL_TRIES:                        # nRepeatedSolves < 30 (the tries so far, l. 381)
        EB._biofuel(d, B, lo_, up_, UP, n, R, fx)
    for (c, w), s_ in sorted(res.get("Support", {}).items()):
        cc = R("coco", c, w)
        if s_ and cc and w != "COMI" and abs(s_) < 1e-12 and abs(cc) < 1e-12:
            fx((c, w), 0.0)
    if not R("coco", "UAAR", "LEVL") and not R("expertup", "UAAR", "LEVL"):
        up_[("UAAR", "LEVL")] = pd("UAAR", "LEVL", "BASM")
        lo_[("UAAR", "LEVL")] = pd("UAAR", "LEVL", "BASM") * EB_UAAR_DECLINE ** (t - d.ord_bas)
    for c in ("ARTO", "INLW", "KITC"):
        fx((c, "LEVL"), pd(c, "LEVL", "BASM"))
    lo_[("ARTIF", "LEVL")] = pd("ARTIF", "LEVL", "BASM")
    for (a, w, bd), v in sorted(B.reqfcnlim.items()):
        if a in B.maact and w in B.rows_est and n(a, "LEVL") and v:
            if bd == "lo":
                lo_[(a, w)] = max(LO((a, w)), v)
            elif bd == "up":
                up_[(a, w)] = min(UP((a, w)), v)
    for a in sorted(B.maact & B.aact365):
        fx((a, "DAYS"), EB_DAYS)


def _release_comi(ntry, B, lo_, up_, n, at_lo, at_up):
    """release_comi_yields.gms (estimate_ms.gms l. 378, after comi_bounds.gms): the milk yields at a binding bound of
    the last solve by (1 -/+ 1e-4 n)^n; LOSF.COMI with a multiplier, after five tries, by 0.995^n and 1.005^n (n: the
    tries so far, nRepeatedSolves before its increment)."""
    for c in sorted(B.cols_est):
        k = (c, "COMI")
        if (c, "COMI") not in B.pact_to_y or not n(c, "COMI"):
            continue
        if k in at_lo:
            lo_[k] = lo_.get(k, -INF) * (1 - COMI_STEP * ntry) ** ntry
        if k in at_up:
            up_[k] = up_.get(k, INF) * (1 + COMI_STEP * ntry) ** ntry
    k = ("LOSF", "COMI")
    if n("LOSF", "COMI") and ntry > LEVL_TRIES and (k in at_lo or k in at_up):
        up_[k] = up_.get(k, INF) * LOSF_UP ** ntry
        lo_[k] = lo_.get(k, -INF) * LOSF_LO ** ntry


#: estimate_ms.gms l. 336-337, 400-402, 418
EB_LEVL_FLOOR = 1.0e-5
EB_UAAR_DECLINE = 0.998
EB_DAYS = 365.0
