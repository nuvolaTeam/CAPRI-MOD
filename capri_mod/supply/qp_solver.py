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
        return None, False

    # Feasible start: project x0 (or zero) onto x >= 0; the unconstrained
    # minimiser is -Q^{-1} c, a good warm start when constraints are slack.
    try:
        x_unc = np.linalg.solve(Qs, -c)
    except np.linalg.LinAlgError:
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
            # KKT satisfied: optimum found.
            return np.maximum(x_new, 0.0), True

        # Add the most-violated constraint to the working set.
        _, add = max(viol)
        working.add(add)
        x = x_new

    return None, False
