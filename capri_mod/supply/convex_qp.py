"""Convex quadratic programming: Clarabel when installed, else an interior-point fallback.

    min 1/2 x'Qx + c'x   s.t.   A x <= b,   Aeq x = beq,   x >= 0

Used for the manure-pool spatial equilibrium (CAPRI solves its pool market,
m_mPoolMarket, with CONOPT). The active-set loop in qp_solver.py changes one
constraint per step; on the full EU (~1,200 variables, hundreds of bounds
switching) it failed at 200 iterations and crawled at 5,000. Interior-point
(Newton) methods converge in a few dozen steps almost regardless of how many
constraints end up binding.

Clarabel (Apache-2.0, `pip install clarabel`) is used when importable; the
fallback is a dense primal-dual interior-point method with Mehrotra's
predictor-corrector, so the model also runs where nothing extra is installed.
Q must be positive semi-definite; for a unique solution, positive definite.
Returns (x, ok, info).
"""
from __future__ import annotations

import numpy as np


def solve_convex_qp(Q, c, A=None, b=None, Aeq=None, beq=None, tol: float = 1e-9,
                    max_iter: int = 200, prefer: str = "auto"):
    n = len(c)
    A = np.zeros((0, n)) if A is None else np.asarray(A, float)
    b = np.zeros(0) if b is None else np.asarray(b, float)
    Aeq = np.zeros((0, n)) if Aeq is None else np.asarray(Aeq, float)
    beq = np.zeros(0) if beq is None else np.asarray(beq, float)
    if prefer in ("auto", "clarabel"):
        try:
            return _clarabel(Q, c, A, b, Aeq, beq, tol)
        except ImportError:
            if prefer == "clarabel":
                raise
    return _ipm(np.asarray(Q, float), np.asarray(c, float), A, b, Aeq, beq, tol, max_iter)


def _clarabel(Q, c, A, b, Aeq, beq, tol):
    import clarabel
    from scipy import sparse
    n = len(c)
    # Clarabel form: A_cl x + s = b_cl, s in cones (zero cone first, then nonnegative)
    A_cl = sparse.vstack([sparse.csc_matrix(Aeq), sparse.csc_matrix(A), -sparse.identity(n)]).tocsc()
    b_cl = np.concatenate([beq, b, np.zeros(n)])
    P = sparse.triu(sparse.csc_matrix(0.5 * (Q + Q.T))).tocsc()
    cones = []
    if len(beq):
        cones.append(clarabel.ZeroConeT(len(beq)))
    cones.append(clarabel.NonnegativeConeT(len(b) + n))
    st = clarabel.DefaultSettings()
    st.verbose = False
    st.tol_gap_abs = st.tol_gap_rel = st.tol_feas = tol
    sol = clarabel.DefaultSolver(P, np.asarray(c, float), A_cl, b_cl, cones, st).solve()
    ok = str(sol.status) in ("Solved", "SolverStatus.Solved")
    zz = np.array(sol.z)
    return np.maximum(np.array(sol.x), 0.0), ok, {"solver": "clarabel", "status": str(sol.status),
                                                  "iterations": getattr(sol, "iterations", None),
                                                  "y": zz[:len(beq)], "z": zz[len(beq):len(beq) + len(b)]}


def _ipm(Q, c, A, b, Aeq, beq, tol, max_iter):
    """Dense primal-dual interior point (Mehrotra predictor-corrector).

    Inequalities G x + s = h, s >= 0 with G = [A; -I], h = [b; 0]; equalities
    Aeq x = beq with free multipliers y. Newton system reduced to
        [Q + G' W G   Aeq'] [dx]   [rhs_x]
        [Aeq           0  ] [dy] = [rhs_y],   W = Z S^-1.
    """
    n = len(c)
    Q = 0.5 * (Q + Q.T)
    G = np.vstack([A, -np.eye(n)])
    h = np.concatenate([b, np.zeros(n)])
    m, p = G.shape[0], Aeq.shape[0]
    x = np.zeros(n)
    s = np.maximum(h - G @ x, 1.0)
    z = np.ones(m)
    y = np.zeros(p)
    scale = max(1.0, float(np.max(np.abs(c))) if n else 1.0, float(np.max(np.abs(h))) if m else 1.0)
    it = 0
    for it in range(1, max_iter + 1):
        rd = Q @ x + c + G.T @ z + (Aeq.T @ y if p else 0.0)
        rp = G @ x + s - h
        re = Aeq @ x - beq if p else np.zeros(0)
        mu = float(s @ z) / m if m else 0.0
        if (np.linalg.norm(rd, np.inf) <= tol * scale and np.linalg.norm(rp, np.inf) <= tol * scale
                and (not p or np.linalg.norm(re, np.inf) <= tol * scale) and mu <= tol * scale):
            return np.maximum(x, 0.0), True, {"solver": "ipm", "iterations": it, "y": y.copy()}
        w = z / s
        H = Q + G.T @ (w[:, None] * G)
        K = np.block([[H, Aeq.T], [Aeq, np.zeros((p, p))]]) if p else H
        try:
            lu = np.linalg.lu_factor(K) if hasattr(np.linalg, "lu_factor") else None
        except Exception:
            lu = None

        def newton(rc):
            rhs_x = -rd - G.T @ (w * rp) + G.T @ (rc / s)
            rhs = np.concatenate([rhs_x, -re]) if p else rhs_x
            sol = np.linalg.solve(K, rhs)
            dx = sol[:n]
            dy = sol[n:] if p else np.zeros(0)
            dz = w * (G @ dx + rp) - rc / s
            ds = -(rc + s * dz) / z
            return dx, dy, dz, ds

        def step(v, dv):
            neg = dv < 0
            return min(1.0, float(np.min(-v[neg] / dv[neg]))) if neg.any() else 1.0

        try:
            dx, dy, dz, ds = newton(s * z)                       # affine (predictor)
        except np.linalg.LinAlgError:
            return np.maximum(x, 0.0), False, {"solver": "ipm", "iterations": it, "status": "singular"}
        a_aff = min(step(s, ds), step(z, dz))
        mu_aff = float((s + a_aff * ds) @ (z + a_aff * dz)) / m if m else 0.0
        sigma = (mu_aff / mu) ** 3 if mu > 0 else 0.0
        dx, dy, dz, ds = newton(s * z + ds * dz - sigma * mu)   # corrector
        a = 0.99 * min(step(s, ds), step(z, dz))
        x, y, z, s = x + a * dx, (y + a * dy if p else y), z + a * dz, s + a * ds
    return np.maximum(x, 0.0), False, {"solver": "ipm", "iterations": it, "status": "max_iter"}
