"""Convex quadratic programming with Clarabel (Apache-2.0, a dependency of capri-mod):

    min 1/2 x'Qx + c'x   s.t.   A x <= b,   Aeq x = beq,   x >= 0

Used for the manure-pool spatial equilibrium (CAPRI solves its pool market, m_mPoolMarket, with CONOPT); an
interior-point method converges in a few dozen steps however many bounds end up binding (an active-set loop failed
on the full EU, ~1,200 variables). Q must be positive semi-definite; for a unique solution, positive definite.
Returns (x, ok, info). (A built-in interior-point fallback for installations without Clarabel was removed on
26 October 2026 with the conic form: Clarabel is required.)
"""
from __future__ import annotations

import numpy as np


def solve_convex_qp(Q, c, A=None, b=None, Aeq=None, beq=None, tol: float = 1e-9):
    n = len(c)
    A = np.zeros((0, n)) if A is None else np.asarray(A, float)
    b = np.zeros(0) if b is None else np.asarray(b, float)
    Aeq = np.zeros((0, n)) if Aeq is None else np.asarray(Aeq, float)
    beq = np.zeros(0) if beq is None else np.asarray(beq, float)
    return _clarabel(Q, c, A, b, Aeq, beq, tol)


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
