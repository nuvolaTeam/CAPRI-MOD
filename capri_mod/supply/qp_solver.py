"""Compact active-set QP solver for the PMP supply problem.

The PMP supply optimisation is a small convex quadratic program:

    minimise   1/2 x' Q x + c' x
    subject to A x <= b            (land, nutrient, set-aside limits)
               x   >= 0            (non-negativity)

with ~40 variables per region. scipy's general ``trust-constr`` treats this as an
arbitrary nonlinear program and spends seconds per solve; exploiting the QP
structure directly brings it down by orders of magnitude.

This is a primal active-set method: hold a working set of active inequality
constraints, solve the equality-constrained KKT system for that set, then add the
most-violated inactive constraint or drop a constraint with a negative
multiplier, until the KKT conditions hold. For a small, convex, well-conditioned
QP this converges in a handful of iterations. If it fails to converge or Q is not
positive definite, the caller falls back to the robust general solver.
"""

from __future__ import annotations

import numpy as np


#: why the last call gave up (None if it succeeded) - for diagnosis only
LAST_FAIL = None


def solve_qp(Q: np.ndarray,
             c: np.ndarray,
             A: np.ndarray,
             b: np.ndarray,
             x0: np.ndarray | None = None,
             max_iter: int = 200,
             tol: float = 1e-8):
    """Solve 1/2 x'Qx + c'x  s.t.  A x <= b, x >= 0.

    Returns (x, ok). ``ok`` is False if the method did not produce a valid KKT
    point, signalling the caller to fall back to the general solver.
    """
    global LAST_FAIL
    LAST_FAIL = None
    n = Q.shape[0]

    # Fold the non-negativity bounds x >= 0 into the inequality set as -x <= 0,
    # so the whole problem is A_all x <= b_all.
    A_bound = -np.eye(n)
    b_bound = np.zeros(n)
    A_all = np.vstack([A, A_bound]) if A.size else A_bound
    b_all = np.concatenate([b, b_bound]) if b.size else b_bound
    m = A_all.shape[0]

    # Ensure Q is symmetric positive definite enough to factorise; add a tiny
    # regularisation if needed (PMP Q is PD by construction, this is a guard).
    Qs = 0.5 * (Q + Q.T)
    try:
        # cheap PD check via Cholesky
        np.linalg.cholesky(Qs + 1e-12 * np.eye(n))
    except np.linalg.LinAlgError:
        globals()["LAST_FAIL"] = "not positive definite"
        return None, False

    # Feasible start: project x0 (or zero) onto x >= 0; the unconstrained
    # minimiser is -Q^{-1} c, a good warm start when constraints are slack.
    try:
        x_unc = np.linalg.solve(Qs, -c)
    except np.linalg.LinAlgError:
        globals()["LAST_FAIL"] = "unconstrained solve singular"
        return None, False
    x = np.maximum(x_unc, 0.0) if x0 is None else np.maximum(x0, 0.0)

    # Working set: indices of A_all treated as active (equality) this iteration.
    # Start from constraints that x violates or nearly binds.
    working = set(np.where(A_all @ x >= b_all - tol)[0].tolist())

    for _ in range(max_iter):
        if working:
            W = sorted(working)
            Aw = A_all[W]
            bw = b_all[W]
            # KKT system for equality-constrained QP on the working set:
            #   [ Q   Aw' ] [ x ]   [ -c ]
            #   [ Aw  0   ] [ l ] = [ bw ]
            k = len(W)
            KKT = np.zeros((n + k, n + k))
            KKT[:n, :n] = Qs
            KKT[:n, n:] = Aw.T
            KKT[n:, :n] = Aw
            rhs = np.concatenate([-c, bw])
            try:
                sol = np.linalg.solve(KKT, rhs)
            except np.linalg.LinAlgError:
                globals()["LAST_FAIL"] = "singular KKT system"
                return None, False
            x_new = sol[:n]
            lam = sol[n:]
        else:
            x_new = x_unc
            lam = np.array([])
            W = []

        # Check inactive constraints for the largest violation.
        resid = A_all @ x_new - b_all           # <= 0 means satisfied
        inactive = [i for i in range(m) if i not in working]
        viol = [(resid[i], i) for i in inactive if resid[i] > tol]

        if not viol:
            # Feasible. Check multipliers: any negative => drop that constraint.
            if len(lam) and np.min(lam) < -tol:
                drop = W[int(np.argmin(lam))]
                working.discard(drop)
                x = x_new
                continue
            # KKT satisfied. The clip to zero below is not innocent: the
            # feasibility test above was run on the UNCLIPPED point, so if any
            # component is negative, clipping can move the solution off the
            # feasible set. Re-check after clipping and report failure rather
            # than returning an infeasible point as a success.
            x_out = np.maximum(x_new, 0.0)
            if m and np.max(A_all @ x_out - b_all) > 1e-6:
                globals()["LAST_FAIL"] = "infeasible after clipping"
                return None, False
            return x_out, True

        # Add the most-violated constraint to the working set.
        _, add = max(viol)
        working.add(add)
        x = x_new

    globals()["LAST_FAIL"] = "iteration limit"
    return None, False


def solve_qp_ldp(Q: np.ndarray, c: np.ndarray, A: np.ndarray, b: np.ndarray,
                 feas_tol: float = 1e-6):
    """Exact strictly convex QP via least-distance programming (Lawson & Hanson).

        min 1/2 x'Qx + c'x   s.t.  A x <= b,  x >= 0

    With Q = L L' and z = L'x + L^-1 c the objective is 1/2 ||z||^2 + const, so
    the problem is the least-distance programme  min ||z||  s.t.  G~ z >= h~,
    which Lawson & Hanson solve exactly through one NNLS:
        u = argmin_{u>=0} || [G~'; h~'] u - e_{n+1} ||,   r = residual,
        z = -r[:n] / r[n]     (r = 0  =>  infeasible).
    Finite and exact; needs no feasible start, so it cannot cycle - unlike the
    heuristic active-set loop above. The QP has a UNIQUE optimum (Q positive
    definite), so this returns the same solution as any other exact method.
    Returns (x, ok).
    """
    global LAST_FAIL
    from scipy.optimize import nnls
    n = Q.shape[0]
    Qs = 0.5 * (Q + Q.T)
    try:
        L = np.linalg.cholesky(Qs)
    except np.linalg.LinAlgError:
        LAST_FAIL = "ldp: not positive definite"
        return None, False
    G = np.vstack([-A, np.eye(n)]) if A.size else np.eye(n)
    h = np.concatenate([-b, np.zeros(n)]) if b.size else np.zeros(n)
    # scale rows of G for conditioning (does not change the feasible set)
    s = np.linalg.norm(G, axis=1)
    s[s == 0] = 1.0
    G, h = G / s[:, None], h / s
    Linv_c = np.linalg.solve(L, c)
    Gt = np.linalg.solve(L, G.T).T                 # G L'^-1
    ht = h + Gt @ Linv_c                           # h + G Q^-1 c
    E = np.vstack([Gt.T, ht[None, :]])
    f = np.zeros(n + 1)
    f[-1] = 1.0
    try:
        u, _ = nnls(E, f, maxiter=50 * E.shape[1])
    except Exception as exc:                       # pragma: no cover
        LAST_FAIL = f"ldp: nnls failed ({exc})"
        return None, False
    r = E @ u - f
    if abs(r[-1]) < 1e-14 or np.linalg.norm(r) < 1e-12:
        LAST_FAIL = "ldp: infeasible"
        return None, False
    z = -r[:n] / r[-1]
    x = np.linalg.solve(L.T, z - Linv_c)
    x = np.maximum(x, 0.0)
    if A.size and np.max(A @ x - b) > feas_tol * max(1.0, float(np.max(np.abs(b)))):
        LAST_FAIL = "ldp: infeasible after recovery"
        return None, False
    return x, True
