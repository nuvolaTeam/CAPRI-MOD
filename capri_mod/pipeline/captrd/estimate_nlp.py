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

With captrd.nlp_infeasible_marginals = "slp" (added 12 November 2026) the infeasible point is found as CONOPT finds it:
its phase 1 minimises the sum of infeasibilities from the solve's start with an active-set method. phase1_slp does
this as a sequential LP (the least-infeasibility LP on the linearised equations, HiGHS's dual simplex, a trust region)
from the start; the point is then polished by the least-infeasibility NLP (kept only if less infeasible), and the
marginals are read at a simplex vertex there (phase1_marginals: the LP within a box of nlp_at_bound_tol). CONOPT's
pivoting at degenerate vertices is not reproduced.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import casadi as ca
import numpy as np
import scipy.optimize as sopt
import scipy.sparse as sps

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
            "captrd.nlp_phase1_proximity", "captrd.nlp_phase1_slp_max_iter", "captrd.nlp_phase1_slp_radius",
            "captrd.nlp_tie_break")
    return {k.split(".", 1)[1]: st.get(k) for k in keys}


#: phase1_slp's trust region: a step is taken if it achieves this share of the predicted reduction; the radius doubles
#: above the second share, shrinks to a quarter on a rejected step; it stops when the predicted reduction falls below
#: SLP_STOP relative to the infeasibility (or the radius below SLP_MIN_RADIUS)
SLP_ACCEPT, SLP_EXPAND, SLP_GROW, SLP_SHRINK, SLP_STOP, SLP_MIN_RADIUS = 0.1, 0.75, 2.0, 0.25, 1.0e-10, 1.0e-12


def _max_violation(gv, lbg, ubg):
    return float(np.maximum(np.maximum(lbg - gv, gv - ubg), 0.0).max()) if len(gv) else 0.0


def _infeasibility(gv, lbg, ubg):
    return float(np.maximum(lbg - gv, 0.0).sum() + np.maximum(gv - ubg, 0.0).sum())


def _phase1_lp(gv, J, lbg, ubg, dlo, dup):
    """The least-infeasibility LP at a point: min sum(sp + sn) over the step d within [dlo, dup], with
    lbg <= g + J d - sp + sn <= ubg (sp, sn >= 0). HiGHS's dual simplex (a vertex, reduced costs as marginals)."""
    n, m = J.shape[1], J.shape[0]
    eq = np.isfinite(lbg) & np.isfinite(ubg) & (lbg == ubg)
    le = np.isfinite(ubg) & ~eq
    ge = np.isfinite(lbg) & ~eq
    I = sps.identity(m, format="csr")
    A = sps.hstack([J, -I, I], format="csr")
    c = np.concatenate([np.zeros(n), np.ones(m), np.ones(m)])
    A_ub = sps.vstack([A[le], -A[ge]], format="csr")
    b_ub = np.concatenate([ubg[le] - gv[le], gv[ge] - lbg[ge]])
    bounds = np.vstack([np.column_stack([dlo, dup]), np.column_stack([np.zeros(2 * m), np.full(2 * m, np.inf)])])
    bounds = [(None if not np.isfinite(a) else a, None if not np.isfinite(b) else b) for a, b in bounds]
    r = sopt.linprog(c, A_ub=A_ub if A_ub.shape[0] else None, b_ub=b_ub if A_ub.shape[0] else None,
                     A_eq=A[eq] if eq.any() else None, b_eq=(lbg[eq] - gv[eq]) if eq.any() else None,
                     bounds=bounds, method="highs-ds")
    if r.status != 0:
        raise RuntimeError(f"phase 1 LP: {r.message}")
    lam_g = np.zeros(m)
    if eq.any():
        lam_g[eq] = r.eqlin.marginals
    if A_ub.shape[0]:
        k = int(le.sum())
        lam_g[le] = r.ineqlin.marginals[:k]
        lam_g[ge] = -r.ineqlin.marginals[k:]
    return r.x[:n], float(r.fun), r.lower.marginals[:n], r.upper.marginals[:n], lam_g


def phase1_slp(gfun, jfun, xs, lb, ub, lbg, ubg, max_iter: int, radius: float, trace: Optional[list] = None):
    """CONOPT's phase 1 (the least sum of infeasibilities from the given point, with an active-set method) as a
    sequential LP with a trust region: from xs, the least-infeasibility LP on the linearised equations (HiGHS's dual
    simplex) gives the step; a step is kept if the true infeasibility falls. Returns the point, the sum of
    infeasibilities and the iterations. The SLP converges slowly where the least infeasibility is not at a vertex
    (CONOPT continues with second-order steps there): the caller polishes the point (the least-infeasibility NLP from
    it) and takes the marginals at the polished point (phase1_marginals).
    Departure from CAPRI (the solver): CONOPT's own phase 1 is replaced; its pivoting at degenerate vertices is not
    reproduced. Settings captrd.nlp_phase1_slp_max_iter, captrd.nlp_phase1_slp_radius (relative to max(1, |x|))."""
    x = np.clip(xs, lb, ub)
    gv = np.array(gfun(x)).ravel()
    f0 = _infeasibility(gv, lbg, ubg)
    delta = radius * np.maximum(1.0, np.abs(x))
    it = 0
    for it in range(1, max_iter + 1):
        Jd = jfun(x)
        r_, c_ = Jd.sparsity().get_triplet()
        J = sps.csr_matrix((np.array(Jd.nonzeros()), (r_, c_)), shape=Jd.shape)
        d, fl, _l, _u, _g = _phase1_lp(gv, J, lbg, ubg, np.maximum(lb - x, -delta), np.minimum(ub - x, delta))
        pred = f0 - fl
        if pred <= SLP_STOP * (1.0 + f0) or delta.max() < SLP_MIN_RADIUS:
            break
        xn = np.clip(x + d, lb, ub)
        gn = np.array(gfun(xn)).ravel()
        fn = _infeasibility(gn, lbg, ubg)
        if trace is not None:
            trace.append((it, f0, fl, fn, float(np.median(delta))))
        if f0 - fn >= SLP_ACCEPT * pred:
            if f0 - fn >= SLP_EXPAND * pred:
                delta = delta * SLP_GROW
            x, gv, f0 = xn, gn, fn
        else:
            delta = delta * SLP_SHRINK
    return x, f0, it


def phase1_marginals(gfun, jfun, x, lb, ub, lbg, ubg, tol_at: float):
    """The marginals of a least-infeasibility point as an active-set solver reports them: the least-infeasibility LP on
    the linearised equations within a box of tol_at x max(1, |x|) around x (HiGHS's dual simplex, a vertex): the
    reduced costs of the variables' own bounds within the box (IPOPT's sign: negative at a lower bound, positive at an
    upper one) and the equations' multipliers."""
    gv = np.array(gfun(x)).ravel()
    Jd = jfun(x)
    r_, c_ = Jd.sparsity().get_triplet()
    J = sps.csr_matrix((np.array(Jd.nonzeros()), (r_, c_)), shape=Jd.shape)
    delta = tol_at * np.maximum(1.0, np.abs(x))
    dlo, dup = np.maximum(lb - x, -delta), np.minimum(ub - x, delta)
    _d, _fl, ml, mu, lam_g = _phase1_lp(gv, J, lbg, ubg, dlo, dup)
    own_lo, own_up = (lb - x) >= -delta, (ub - x) <= delta
    lam = np.where(own_lo, -np.asarray(ml), 0.0) + np.where(own_up, -np.asarray(mu), 0.0)
    return lam, lam_g


def solve(p: E.Point, S: E.Sets, B: EB.BoundSets, d: EB.BoundData, lo: Dict[K2, float], up: Dict[K2, float],
          wvar: Dict[K2, float], start: Dict[K2, float], expertlo: Dict[K2, float] = None,
          expertup: Dict[K2, float] = None, basm: Optional[callable] = None, log: Optional[List[str]] = None,
          opts: Optional[dict] = None, widen: bool = True) -> Result:
    """m_trendMS for one member state and year. p: the point's data (support relative, as the bounds); lo, up: the
    bounds (estimate_bounds.bounds); wvar: wVarErr; start: the starting levels (CAPTRD: estP of the previous solve, else
    the support, estimate_ms.gms l. 79-90); basm(c, w): p_data's BASM (the widening's floor at zero). widen=False: one
    solve, no widening (clean_tiny.gms's solve, which aborts on an infeasible model instead)."""
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
    in_obj = np.array(ca.which_depends(f, X, 1, False), dtype=bool)
    # a position referenced only in a term whose condition is off (V(c, w) * n(c, w) with n false) is in no equation and
    # not in the objective: GAMS does not generate it, so it is not in the model and keeps its level (V_EstV.L); here it
    # is held at its start, so the interior point does not push it into its open box (found 12 November 2026: about
    # 40 positions per member state at 1e5, e.g. GROF of the dairy products, MAPR of the crops)
    absent = ~(np.array(ca.which_depends(G, X, 1, False), dtype=bool) | np.array(ca.which_depends(f, X, 1, False), dtype=bool)) \
        if G.shape[0] else np.zeros(X.shape[0], dtype=bool)
    slp = str(o["nlp_infeasible_marginals"]) == "slp"
    jfun = ca.Function("J", [X], [ca.jacobian(G, X)]) if slp else None
    phase1 = str(o["nlp_infeasible_marginals"]) in ("phase1", "slp")
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
        lb, ub = np.where(absent, xs, lb), np.where(absent, xs, ub)
        sol = solver(x0=xs, lbx=lb, ubx=ub, lbg=lbg, ubg=ubg)
        x = np.array(sol["x"]).ravel()
        gv = np.array(gfun(x)).ravel()
        viol = float(np.maximum(np.maximum(lbg - gv, gv - ubg), 0.0).max()) if len(gv) else 0.0
        status = solver.stats()["return_status"]
        log.append(f"try {ntry}: {status}, max. infeasibility {viol:.2e}, SSQ {float(sol['f']):.6g}")
        if status in SOLVER_ERRORS:
            raise RuntimeError(f"m_trendMS {d.ms} {d.year}: solver error {status} at try {ntry}")
        ok = viol <= float(o["nlp_tolinfeas"]) and status in ("Solve_Succeeded", "Solved_To_Acceptable_Level")
        if ok and o.get("nlp_tie_break"):
            x = _tie_break(X, f, G, x, xs, lb, ub, lbg, ubg, in_obj, o, log)
        if ok or not widen:
            return Result({k: float(x[i]) for i, k in enumerate(keys)}, float(sol["f"]), ok, ntry + 1, status,
                          lo_, up_)
        lam = np.array(sol["lam_x"]).ravel()
        x_ip, use_slp = x, slp
        if slp:
            # CONOPT's phase 1 from the solve's start (the sequential LP), then polished below
            x, f1, its = phase1_slp(gfun, jfun, xs, lb, ub, lbg, ubg, int(o["nlp_phase1_slp_max_iter"]),
                                    float(o["nlp_phase1_slp_radius"]))
            gv = np.array(gfun(x)).ravel()
            x_slp = x
            log.append(f"    phase 1 (SLP): {its} iterations, sum of infeasibilities {f1:.3e}")
            # CONOPT goes on to optimise from a feasible phase-1 point: the bounds are not widened then, the model is
            # solved again from it
            if _max_violation(gv, lbg, ubg) <= float(o["nlp_tolinfeas"]):
                sol = solver(x0=x, lbx=lb, ubx=ub, lbg=lbg, ubg=ubg)
                x2 = np.array(sol["x"]).ravel()
                viol2 = _max_violation(np.array(gfun(x2)).ravel(), lbg, ubg)
                status = solver.stats()["return_status"]
                log.append(f"    from the feasible phase-1 point: {status}, max. infeasibility {viol2:.2e}, "
                           f"SSQ {float(sol['f']):.6g}")
                if viol2 <= float(o["nlp_tolinfeas"]) and status in ("Solve_Succeeded", "Solved_To_Acceptable_Level"):
                    if o.get("nlp_tie_break"):
                        x2 = _tie_break(X, f, G, x2, xs, lb, ub, lbg, ubg, in_obj, o, log)
                    return Result({k: float(x2[i]) for i, k in enumerate(keys)}, float(sol["f"]), True, ntry + 1,
                                  status, lo_, up_)
                # departure: CONOPT would optimise on from the feasible point; IPOPT cannot (its interior-point start
                # leaves a feasible set without interior: Denmark and Austria 2030's Solve1). The widening then takes
                # the least-infeasibility point from IPOPT's infeasible solve, as with "phase1"
                x, gv, use_slp = x_ip, np.array(gfun(x_ip)).ravel(), False
                log.append("    phase 1: feasible but not solvable from it: the IPOPT phase 1 for this try")
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
        if use_slp:
            # the polished point only if it is less infeasible than the SLP's
            if _infeasibility(np.array(gfun(x)).ravel(), lbg, ubg) > f1:
                x = x_slp
                log.append("    phase 1: the SLP point kept")
            lam, _lam_g = phase1_marginals(gfun, jfun, x, lb, ub, lbg, ubg, tol_at)
        at_lo, at_up = _binding(keys, x, lam, lb, ub, tol_at, tol_m)
        _widen(ntry, keys, x, at_lo, at_up, lo_, up_, B, p, expertlo, expertup, basm)
        _oind_ocro(ntry, keys, x, at_lo, lo_)
        _again(ntry, d, B, lo_, up_, expertup, at_lo, at_up)
        # l. 349-353: the levels stay at the last solve's, but those with data go back to estP
        x0 = np.where(nobs_i & has_start, x_est, x)
    x = np.array(sol["x"]).ravel()
    return Result({k: float(x[i]) for i, k in enumerate(keys)}, float(sol["f"]), False, ntry + 1, status, lo_, up_)


#: _tie_break: the equations' band, a share of captrd.nlp_tolinfeas
TIE_BREAK_BAND = 0.1


def _tie_break(X, f, G, x, xs, lb, ub, lbg, ubg, in_obj, o, log):
    """Departure from CAPRI (the solver; decided by the project lead, 12 November 2026): among the optima of a feasible
    solve, the one whose positions outside the objective lie nearest the solve's start. CONOPT leaves a variable at its
    start unless an equation moves it; IPOPT, an interior-point method, drives the directions the objective leaves free
    to the middle of their bounds (Denmark 2030's olive oil imports and exports 5e8 against CAPTRD's 1.1: in the ex-ante
    years IMPT and EXPT enter only through their difference). The objective's variables are fixed at the solution; the
    others minimise their squared distance from the start (scaled by max(1, |start|)) within the equations and bounds.
    The objective is unchanged; applied after the solve only, so the widening's path is not affected. Kept only if
    feasible (captrd.nlp_tolinfeas)."""
    free = ~in_obj & (lb != ub)
    if not free.any():
        return x
    # the subproblem: the free positions as variables, the others constants, the equations that hold a free position
    fi = np.flatnonzero(free)
    Xf = ca.SX.sym("xf", len(fi))
    full = ca.SX(ca.DM(x))
    for j, i in enumerate(fi):
        full[int(i)] = Xf[j]
    Gfull = ca.Function("g", [X], [G])(full)
    rows = np.flatnonzero(np.array(ca.which_depends(Gfull, Xf, 1, True), dtype=bool))
    Gs = Gfull[rows.tolist()] if len(rows) else ca.SX(0, 1)
    xs_f = xs[fi]
    f2 = ca.sumsqr((Xf - ca.DM(xs_f)) / ca.DM(np.maximum(1.0, np.abs(xs_f))))
    tb = ca.nlpsol("tie_break", "ipopt", {"x": Xf, "f": f2, "g": Gs},
                   {"ipopt.print_level": 0, "print_time": 0, "ipopt.tol": float(o["nlp_tol"]),
                    "ipopt.max_iter": int(o["nlp_max_iter"])})
    # the equations as a band of a tenth of the feasibility tolerance: the subproblem has more equations than free
    # positions (each free position's equations are consistent at the solution), which IPOPT rejects as equalities
    band = TIE_BREAK_BAND * float(o["nlp_tolinfeas"])
    sol = tb(x0=x[fi], lbx=lb[fi], ubx=ub[fi], lbg=lbg[rows] - band, ubg=ubg[rows] + band)
    xn = x.copy()
    xn[fi] = np.array(sol["x"]).ravel()
    gv = np.array(ca.Function("g", [X], [G])(xn)).ravel()
    viol = float(np.maximum(np.maximum(lbg - gv, gv - ubg), 0.0).max()) if len(gv) else 0.0
    status = tb.stats()["return_status"]
    if viol > float(o["nlp_tolinfeas"]) or status not in ("Solve_Succeeded", "Solved_To_Acceptable_Level"):
        log.append(f"    tie-break: {status}, max. infeasibility {viol:.2e}: the solve's point kept")
        return x
    moved = int((np.abs(xn - x) > 1e-6 * np.maximum(1.0, np.abs(x)))[free].sum())
    log.append(f"    tie-break: {status}, {int(free.sum())} positions outside the objective, {moved} moved")
    return xn


def estp(x: Dict[K2, float], p: E.Point, S: E.Sets) -> Dict[K2, float]:
    """estimate_ms.gms l. 452-456: the levels stored (estP) are those of the positions with observations or a support,
    of the estimated columns (and STCM)."""
    return {k: v for k, v in x.items() if (k in p.nobs or p.support.get(k)) and (k[0] in S.cols_est or k[0] == "STCM")}


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
