"""One market solve on the market's equations as one system in CAPRI's form (market.solver = "chain" or
"ipopt"; docs/dev/MARKET_SYSTEM.md).

The system is capri_mod/market/market_system_ad.py's lifted form (the producer price ratios of the bilateral
commodities, the active quotas' sigmas, the young-animal prices, the dairy blocks, FEDE and the non-EU rents, with the
Armington ratios, supply and use as unknowns of their own and their defining equations; CAPRI's m_globMarket). The
balances of a region-commodity without supply, use or trade are left out and their prices held (MARKET_SYSTEM.md, the assembled system);
the rest is square. Each equation is divided by its largest derivative at the start. The start is the module's state,
the previous solve's solution. Two methods:

- "chain": Newton's method with the exact sparse Jacobian (CasADi), globalised by a backtracking line search on
  the largest scaled residual or Powell's dogleg trust region (market.newton_step); the linear solves by market.newton_linear_solver: "pardiso" (Intel MKL's PARDISO
  through pypardiso, an optional package under Intel's licence, installed by the user like CAPRI's CONOPT) or "mumps" (bundled with
  CasADi, open). Where its line search stalls (a quota's steep sigmoid), a continuation on the quotas' slope
  (market.trq_slope_steps, then CAPRI's 200: CAPRI's own way in trim_trqs.gms), then IPOPT from the start. The fastest
  measured (MARKET_SYSTEM.md, the solver comparison).
- "ipopt": IPOPT with a zero objective and the equations as equality constraints, as CAPRI solves its market with
  CONOPT; its linear solver market.ipopt_linear_solver: "mumps" (bundled; the METIS ordering and mumps_mem_percent
  100: MUMPS's defaults are refused their workspace on this market) or one of HSL's (ma27, ma57, ma77, ma86, ma97:
  Coin-HSL, under STFC's licence, built and installed by the user like CAPRI's CONOPT; market.hsl_library its library),
  the Lagrangian's Hessian by L-BFGS. With CAPRI's bounds (market.bounds) this is the method that takes them.

Both stop at market.chain_tol, at most market.chain_max_iter iterations. `chain_market_solve` returns the solution's price ratios
(and sets the quotas' sigmas and their rate offsets, then settles the fixed point's lagged evaluation state at it), or
None when the system cannot be built (a trade scenario's tariff additions, a region-commodity without a base price; the
message says which) or the method does not solve it; the caller (the fixed point of bilateral_solve.py) then goes on
from its own start, or from the solution, which it confirms in its first evaluation. CAPRI's bounds and widen_bounds:
market.bounds (market_bounds.py; in progress, MARKET_BOUNDS_PLAN.md).
"""
from __future__ import annotations

import time

import numpy as np

from capri_mod.settings import current as _settings


def _scales(mm, lay) -> np.ndarray:
    """Each equation's scale: the balances S0 + D0 (the fixed point's test), the quotas 1, the young-animal markets
    their net supply, the dairy blocks their base raw milk, FeedBal_ the energy fed at calibration, the land markets the
    calibration land, the Armington ratios 1, supply and use their base quantity (at least 1)."""
    from capri_mod.market.feed_ad import fedebal_arrays
    out = []
    for name, n in lay["eqs"]:
        if name == "bal":
            out += [np.maximum(np.asarray(sc.S0 + sc.D0, float), 1.0) for sc in mm.par.bilat.values()]
        elif name in ("trq", "PAdef"):
            out.append(np.ones(n))
        elif name == "yani":
            st = mm.seen.yani_state or {}
            out.append(np.array([max(abs(float(st[reg]["net"][g])), 1.0) for reg, goods in lay["ylay"] for g in goods]))
        elif name == "dairyE":
            dp = mm._dairy_params()
            out.append(np.repeat([max(float(dp["ms"][m]["Q0"][dp["ms"][m]["iM"]]), 1.0) for m in lay["ms"]], 3))
        elif name == "dairyW":
            wp = mm._dairy_world_params()
            out.append(np.repeat([max(float(wp[r]["Q0"][wp[r]["iM"]]), 1.0) for r in lay["wl"]], 3))
        elif name == "feed":
            nfp = mm._noneu_feed_params()
            out.append(np.array([max(abs(fedebal_arrays(nfp["rms"][s], lay["cols"], [])["e_const"]), 1.0)
                                 for s in lay["rms"]]))
        elif name == "land":
            LP = mm._noneu_land_params()
            out.append(np.concatenate([np.maximum(LP[s]["L0"], 1.0) for s in lay["lrms"]]) if lay["lrms"]
                       else np.zeros(0))
        elif name in ("Sdef", "Ddef"):
            b = mm.par.base_production if name == "Sdef" else mm.par.base_consumption
            v = b.reindex(index=lay["regions"], columns=lay["cols"]).fillna(0.0).to_numpy(dtype=float)
            out.append(np.maximum(np.abs(v).ravel(order="F"), 1.0))
    sc_ = np.concatenate(out) if out else np.zeros(0)
    if sc_.size != lay["n_F"]:
        raise RuntimeError(f"market_chain: {sc_.size} scales for {lay['n_F']} equations")
    return sc_


def _ma28(lib_path: str):
    """HSL's MA28 (sparse unsymmetric LU, Coin-HSL's libcoinhsl, STFC's licence) through ctypes: (A, b) -> A^-1 b.
    MA28AD factorises (threshold pivoting u = 0.1, MC23AD's block triangular form first, MA28's defaults), MA28CD
    solves; the arrays' lengths (6 x the non-zeros) doubled where MA28 reports them short (IFLAG -3, -4, -5, -6)."""
    import ctypes
    import ctypes.util
    path = lib_path or ctypes.util.find_library("coinhsl") or ctypes.util.find_library("hsl")
    if not path:
        raise RuntimeError("market.newton_linear_solver = \"ma28\" needs Coin-HSL's library (market.hsl_library)")
    lib = ctypes.CDLL(path)
    # MA28's message units (COMMON /MA28ED/ LP, MP, LBLOCK, GROW) set to 0: no messages; the short arrays are retried
    units = (ctypes.c_int * 2).in_dll(lib, "ma28ed_")
    units[0], units[1] = 0, 0
    I, D = ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_double)

    def ptr(a, t):
        return a.ctypes.data_as(t)

    def solve(A, b):
        A = A.tocoo()
        n, nz = A.shape[0], A.nnz
        fill = 6
        while True:
            licn = lirn = fill * nz
            a = np.zeros(licn)
            a[:nz] = A.data
            icn = np.zeros(licn, dtype=np.int32)
            icn[:nz] = A.col + 1
            irn = np.zeros(lirn, dtype=np.int32)
            irn[:nz] = A.row + 1
            ikeep = np.zeros(5 * n, dtype=np.int32)
            iw = np.zeros(8 * n, dtype=np.int32)
            w = np.zeros(n)
            flag = ctypes.c_int(0)
            lib.ma28ad_(ctypes.byref(ctypes.c_int(n)), ctypes.byref(ctypes.c_int(nz)), ptr(a, D),
                        ctypes.byref(ctypes.c_int(licn)), ptr(irn, I), ctypes.byref(ctypes.c_int(lirn)), ptr(icn, I),
                        ctypes.byref(ctypes.c_double(0.1)), ptr(ikeep, I), ptr(iw, I), ptr(w, D), ctypes.byref(flag))
            if flag.value >= 0:
                break
            if flag.value in (-3, -4, -5, -6) and fill < 96:
                fill *= 2
                continue
            raise RuntimeError(f"MA28AD: IFLAG {flag.value}")
        x = np.array(b, dtype=float)
        lib.ma28cd_(ctypes.byref(ctypes.c_int(n)), ptr(a, D), ctypes.byref(ctypes.c_int(licn)), ptr(icn, I),
                    ptr(ikeep, I), ptr(x, D), ptr(w, D), ctypes.byref(ctypes.c_int(1)))
        return x
    return solve


def _linear_solver(name):
    """(A, b) -> A^-1 b with a sparse direct solver: "pardiso" (MKL PARDISO via pypardiso; "mumps" when the package is
    not installed, with a message), "mumps" (CasADi's) or "ma28" (HSL's, Coin-HSL's library market.hsl_library)."""
    import casadi as ca
    if name == "ma28":
        return "ma28", _ma28(str(_settings().get("market.hsl_library")))
    if name == "pardiso":
        try:
            import pypardiso
            return "pardiso", lambda A, b: pypardiso.spsolve(A.tocsr(), b)
        except ImportError:
            print("    market.newton_linear_solver = \"pardiso\" needs the package pypardiso (Intel MKL's PARDISO, Intel's "
                  "licence): MUMPS instead", flush=True)
    elif name != "mumps":
        raise ValueError(f"market.newton_linear_solver: {name!r} (\"pardiso\", \"mumps\" or \"ma28\")")

    def mumps(A, b):
        A = A.tocsc()
        M = ca.DM(ca.Sparsity(A.shape[0], A.shape[1], A.indptr.tolist(), A.indices.tolist()), A.data)
        ls = ca.Linsol("ipopt_mumps", "mumps", M.sparsity())
        ls.sfact(M)
        ls.nfact(M)
        return np.asarray(ls.solve(M, ca.DM(b)), float).ravel()
    return "mumps", mumps


def _newton(fF, fJ, x0, keep, sc, tol, max_iter, slope):
    """Newton's method on the scaled square system F(x, slope)[keep] / sc = 0 over x[keep]; (x, ok, Jacobians
    factorised, the largest scaled residual). Converged when the largest scaled residual is at most tol. The step by
    market.newton_step:

    - "linesearch": the Newton step, halved until the largest scaled residual falls (the form of the first solver trials);
    - "dogleg": Powell's dogleg trust region on the merit 0.5 ||r||^2 (MINPACK's hybrj, SciPy's fsolve): the Newton
      step where it lies in the trust region, otherwise the dogleg between the Cauchy (steepest-descent) point and the
      Newton step; accepted when the merit falls by at least 1e-4 of the decrease the linear model predicts; the
      region shrunk (x 0.25) where the model predicts poorly (ratio below 0.25) and widened (x 2) where it predicts well
      (above 0.75) at the region's edge. A rejected step reuses the factorisation.

    Stalled: no descent (line search), the trust region below 1e-12 of the step (dogleg), or the residual (the largest
    scaled residual; the merit's root for the dogleg) not halved over market.newton_stall_steps Jacobians (Newton
    creeping along a quota's flat sigmoid: 200 steps for 6.9e-3 on the base market at +5% soft wheat)."""
    import scipy.sparse as sps
    st = _settings()
    _, solve = _linear_solver(str(st.get("market.newton_linear_solver")))
    mode = str(st.get("market.newton_step"))
    if mode not in ("linesearch", "dogleg"):
        raise ValueError(f"market.newton_step: {mode!r} (\"linesearch\" or \"dogleg\")")
    D = sps.diags(1.0 / sc[keep])
    x = x0.copy()

    def res(v):
        return np.asarray(fF(v, slope), float).ravel()[keep] / sc[keep]
    r = res(x)
    nk = float(np.max(np.abs(r))) if r.size else 0.0
    it = 0
    k_stall = int(st.get("market.newton_stall_steps"))
    hist = [nk if mode == "linesearch" else float(np.linalg.norm(r))]
    delta = None
    while nk > tol and it < max_iter:
        A = D @ fJ(x, slope).sparse().tocsr()[keep, :][:, keep]
        pn = solve(A, -r)
        it += 1
        if mode == "linesearch":
            t = 1.0
            while True:
                xt = x.copy()
                xt[keep] += t * pn
                rt = res(xt)
                nt = float(np.max(np.abs(rt)))
                if nt < nk or t < 1e-6:
                    break
                t *= 0.5
            if not nt < nk:
                break                               # no descent along Newton's direction: stalled
            x, r, nk = xt, rt, nt
            hist.append(nk)
        else:
            g = A.T @ r                             # the merit's gradient
            Ag = A @ g
            pc = -(float(g @ g) / max(float(Ag @ Ag), 1e-300)) * g      # the Cauchy point
            npn, npc = float(np.linalg.norm(pn)), float(np.linalg.norm(pc))
            if delta is None:
                delta = npn
            f0 = 0.5 * float(r @ r)
            accepted = False
            while not accepted:
                if npn <= delta:
                    p = pn
                elif npc >= delta:
                    p = (delta / npc) * pc
                else:                               # the dogleg: pc + tau (pn - pc) on the region's edge
                    dd = pn - pc
                    a_, b_, c_ = float(dd @ dd), 2.0 * float(pc @ dd), npc ** 2 - delta ** 2
                    tau = (-b_ + np.sqrt(max(b_ * b_ - 4.0 * a_ * c_, 0.0))) / (2.0 * a_)
                    p = pc + tau * dd
                lin = r + A @ p
                pred = f0 - 0.5 * float(lin @ lin)
                xt = x.copy()
                xt[keep] += p
                rt = res(xt)
                ft = 0.5 * float(rt @ rt) if np.all(np.isfinite(rt)) else np.inf
                rho = (f0 - ft) / pred if pred > 0 else -1.0
                np_ = float(np.linalg.norm(p))
                if rho < 0.25:
                    delta = 0.25 * np_
                elif rho > 0.75 and np_ >= 0.99 * delta:
                    delta = 2.0 * delta
                if rho > 1e-4:
                    accepted = True
                elif delta < 1e-12 * max(npn, 1.0):
                    break
            if not accepted:
                break                               # the trust region collapsed: stalled
            x, r = xt, rt
            nk = float(np.max(np.abs(r)))
            hist.append(float(np.linalg.norm(r)))
        if len(hist) > k_stall and hist[-1] > 0.5 * hist[-1 - k_stall]:
            break                                   # creeping: not halved over the last k_stall steps
    return x, nk <= tol, it, nk


def _lifted(mm, r, exogenous_supply, trade_scenario):
    """The lifted market system at the module's state after one evaluation at r: (fn, lay, x, F, slope symbol, x0)."""
    import casadi as ca
    from capri_mod.market.market_system_ad import market_system, market_x0
    mm._bilateral_eval(r, exogenous_supply, trade_scenario)
    s = ca.SX.sym("slope")
    # with CAPRI's bounds the processing and non-EU feed cells are unknowns too (their bounds and fudge rows)
    fn, lay, x, F = market_system(mm, exogenous_supply, trade_scenario, lifted=True, slope=s, fudge=True,
                                  lift_use=str(_settings().get("market.bounds")) == "capri")
    return fn, lay, x, F, s, market_x0(mm, lay)


def within_capri_start_bounds(mm, lay, x0, tol=1e-9) -> bool:
    """Whether x0 (the fixed point's equilibrium in the lifted system's unknowns) lies within CAPRI's start bounds
    (set_start_val.gms; market_bounds.capri_start_bounds), each within tol x max(1, |bound|). The equilibrium solves
    the system's equations, so inside the bounds it is the bounded problem's solution too (every paired equation met,
    no bound active): the bounded solve can be skipped. Its equations are the model's form there (DEP-37's processing
    fudge always on; the bounded system's rows within their bounds differ by it, 7e-6 at most in the mini-EU Green Deal
    pair of 26 November 2026)."""
    from capri_mod.market.market_bounds import capri_start_bounds
    lb, ub = capri_start_bounds(mm, lay, x0)
    lb, ub = np.asarray(lb, float), np.asarray(ub, float)
    x0 = np.asarray(x0, float)
    ok_lo = ~np.isfinite(lb) | (x0 >= lb - tol * np.maximum(1.0, np.abs(lb)))
    ok_up = ~np.isfinite(ub) | (x0 <= ub + tol * np.maximum(1.0, np.abs(ub)))
    return bool(np.all(ok_lo & ok_up))


def build(mm, r, exogenous_supply, trade_scenario, lifted=None):
    """The lifted market system at the module's state after one evaluation at r, with the quotas' sigmoid slope as a
    parameter: a dict with its Functions F(x, slope) and Jacobian, the start x0, the equations kept (the empty balances
    out), the unknowns held (their prices), the row scales, CAPRI's slope; NotImplementedError where it cannot be
    built. lifted: _lifted's result at the same state, when already built."""
    import casadi as ca
    from capri_mod.market.market_system_ad import market_system
    t0 = time.time()
    fn, lay, x, F, s, x0 = lifted if lifted is not None else _lifted(mm, r, exogenous_supply, trade_scenario)
    # the plain system's sparsity: its empty balances (rows without an entry), out of the lifted system's equations
    fs, _, _, _ = market_system(mm, exogenous_supply, trade_scenario)
    fm = lay["fm"]
    sp = fs.jac_sparsity(0, 0)
    empty = np.nonzero(np.diff(np.asarray(sp.T.colind())) == 0)[0]
    keep = np.setdiff1d(np.arange(lay["n_F"]), empty)
    fF3 = ca.Function("market_system_F", [x, s, fm], [F])
    fJ3 = ca.Function("market_system_J", [x, s, fm], [ca.jacobian(F, x)])
    slope = float(next(iter(mm.par.bilat.values())).TRQ_SLOPE)
    ctx = dict(fn=fn, lay=lay, x=x, F=F, s=s, fm=fm, x0=x0, keep=keep, empty=empty, slope=slope, mm=mm)
    # the ProdNQ_ cells' modes (supply_system_ad.prodnq_cell): the model's floor without CAPRI's bounds; with them, the
    # row within its bounds, CAPRI's ProdFudge_ where a cell's lower bound is at or below 0
    ctx["fmv"] = (_fudge_modes(ctx, _bounds(ctx)[0]) if str(_settings().get("market.bounds")) == "capri"
                  else np.zeros(len(lay["fudge_cells"]) + len(lay.get("lift_cells") or ())))
    fF = lambda v, sl: fF3(v, sl, ctx["fmv"])      # noqa: E731
    fJ = lambda v, sl: fJ3(v, sl, ctx["fmv"])      # noqa: E731
    # each equation divided by its largest derivative at the start (row scaling): the equations in the units of the
    # unknown that moves them most. The blocks' own scales (_scales) leave an equation that responds weakly to its
    # unknown loose: FeedBal_ divided by the energy fed lets FEDE miss by 1e-2 within a 1e-10 tolerance
    Ja = abs(fJ(x0, slope).sparse().tocsr())
    sc = np.maximum(np.asarray(Ja.max(axis=1).todense()).ravel(), 1e-12)
    ctx.update(fF=fF, fJ=fJ, sc=sc, built=time.time() - t0)
    return ctx


def _fudge_modes(ctx, lbx) -> np.ndarray:
    """The fudge rows' modes under CAPRI's bounds: 1 (the fudge) where the unknown's lower bound is at or below 0, else
    2 (the row within its bounds); the ProdNQ_ cells (ProdFudge_, market_model.gms l. 2421: v_prodQuant.lo LE 0), then
    the lifted processing and non-EU feed cells (ProcFudge_ l. 1158, v_procQuant.lo LE 0; FeedFudge_ l. 1054,
    v_feedQuant.lo LE 0)."""
    lay = ctx["lay"]
    nR = len(lay["regions"])
    off, o = {}, 0
    for nm, n in lay["x"]:
        off[nm] = o
        o += n
    lb = np.asarray(lbx, float)
    idx = np.array([off.get("S", 0) + j * nR + i for i, j, _ in lay["fudge_cells"]], int)
    m = np.where(lb[idx] <= 0.0, 1.0, 2.0) if idx.size else np.zeros(0)
    nl = len(lay.get("lift_cells") or ())
    if nl and "L" in off:
        ml = np.where(lb[off["L"]:off["L"] + nl] <= 0.0, 1.0, 2.0)
        m = np.concatenate([m, ml])
    elif nl:
        m = np.concatenate([m, np.zeros(nl)])
    return m


def _eqs(ctx, expr):
    """expr with the slope at CAPRI's and the cells' modes at the current ones."""
    import casadi as ca
    return ca.substitute([expr], [ctx["s"], ctx["fm"]], [ca.SX(ctx["slope"]), ca.SX(ca.DM(ctx["fmv"]))])[0]


def _mcp_system(ctx, lbx, ubx):
    """The bounded system as a mixed complementarity problem (G3.4 point 2, the project lead's choice of 16 November
    2026): each unknown x_i with its equation F_i (the lifted system's blocks pair one to one: balances and prices,
    quota rows and sigmas, the dairy blocks, FEDE, the land rents, each lifted definition and its unknown), l <= x <= u
    perp F: F_i = 0 inside the bounds, F_i >= 0 at l, F_i <= 0 at u. Written with the Fischer-Burmeister function
    phi(a, b) = a + b - sqrt(a^2 + b^2 + eps) in Billups' box form Phi = phi(x - l, -phi(u - x, -F)) (one-sided
    bounds phi(x - l, F), -phi(u - x, -F); free F; fixed x - l: the cell's equation dropped, as CAPRI generates none
    for a fixed cell), on the scaled equations F / sc oriented per block so that each rises with its own unknown
    (the sign of the block's median Jacobian diagonal at the start). eps = market.ssn_fb_smoothing. Returns
    (Phi(x, slope), its Jacobian, sgn): numerical functions of (x, slope) at the current modes, from the system's own
    F and Jacobian (ctx["fF"], ctx["fJ"]): each Phi_i depends on x_i and F_i only, so its Jacobian is
    diag(c) + diag(d) J_F with c, d the Fischer-Burmeister function's partial derivatives (until 27 November 2026 a
    second symbolic Jacobian, the same numbers at about 20 s more per market solve)."""
    import scipy.sparse as sps
    sc = np.asarray(ctx["sc"], float)
    n = int(sc.size)
    lay = ctx["lay"]
    J0 = ctx["fJ"](ctx["x0"], ctx["slope"]).sparse().tocsr()
    dg = np.asarray(J0.diagonal(), float)
    sgn = np.ones(n)
    o = 0
    for nm, k in lay["eqs"]:
        if k:
            d = dg[o:o + k]
            d = d[np.abs(d) > 1e-14]
            sgn[o:o + k] = -1.0 if (d.size and np.median(d) < 0) else 1.0
        o += k
    eps = float(_settings().get("market.ssn_fb_smoothing"))
    lbx, ubx = np.asarray(lbx, float), np.asarray(ubx, float)
    lo, up = np.isfinite(lbx), np.isfinite(ubx)
    fixed = lo & up & (lbx == ubx)
    both = lo & up & ~fixed
    onlo, onup = lo & ~up, up & ~lo
    w = sgn / sc

    def _parts(x, slope):
        """(Phi, c, d): Phi(x) and its partial derivatives in x_i (c) and in the scaled, oriented F_i (d)."""
        x = np.asarray(x, float).ravel()
        f = np.asarray(ctx["fF"](x, slope), float).ravel() * w
        P, c, d = f.copy(), np.zeros(n), np.ones(n)

        def phi(a, b):
            s = np.sqrt(a * a + b * b + eps)
            return a + b - s, 1.0 - a / s, 1.0 - b / s
        if fixed.any():
            P[fixed], c[fixed], d[fixed] = x[fixed] - lbx[fixed], 1.0, 0.0
        if onlo.any():
            v, pa, pb = phi(x[onlo] - lbx[onlo], f[onlo])
            P[onlo], c[onlo], d[onlo] = v, pa, pb
        if onup.any():
            v, pa, pb = phi(ubx[onup] - x[onup], -f[onup])
            P[onup], c[onup], d[onup] = -v, pa, pb
        if both.any():
            q, qa, qb = phi(ubx[both] - x[both], -f[both])
            v, pa, pb = phi(x[both] - lbx[both], -q)
            P[both] = v
            c[both] = pa + pb * qa                 # d(-q)/dx_i = qa (through u - x), d(-q)/df = qb
            d[both] = pb * qb
        return P, c, d

    class _J:
        def __init__(self, A):
            self._A = A

        def sparse(self):
            return self._A

    def fP(x, slope):
        return _parts(x, slope)[0]

    def fJP(x, slope):
        _, c, d = _parts(x, slope)
        JF = ctx["fJ"](np.asarray(x, float).ravel(), slope).sparse().tocsr()
        return _J((sps.diags(c) + sps.diags(d * w) @ JF).tocsr())
    return fP, fJP, sgn


def _trf(ctx, x0, lbx, ubx, tol, slope):
    """SciPy's trust-region reflective least squares (least_squares, method "trf", the sparse Jacobian, LSMR) on the
    scaled system within [lbx, ubx] (G3.4 point 2): min ||F / sc||^2; a residual left where a bound binds (as CAPRI's
    infeasible solve before widen_bounds). Fixed unknowns held. Returns (x, ok, message)."""
    from scipy.optimize import least_squares
    keep, sc = ctx["keep"], ctx["sc"]
    free = lbx < ubx
    x = np.clip(x0.copy(), lbx, ubx)
    idx = np.nonzero(free)[0]

    def full(z):
        v = x.copy(); v[idx] = z
        return v

    def fun(z):
        return np.asarray(ctx["fF"](full(z), slope), float).ravel()[keep] / sc[keep]

    def jac(z):
        J = ctx["fJ"](full(z), slope).sparse().tocsr()[keep, :][:, idx]
        import scipy.sparse as sps
        return sps.diags(1.0 / sc[keep]) @ J
    lb_, ub_ = lbx[idx], ubx[idx]
    z0 = np.clip(x[idx], np.nextafter(lb_, np.inf), np.nextafter(ub_, -np.inf))
    r = least_squares(fun, z0, jac=jac, bounds=(lb_, ub_), method="trf", tr_solver="lsmr", x_scale="jac",
                      xtol=1e-15, ftol=1e-15, gtol=1e-15, max_nfev=int(_settings().get("market.trf_max_nfev")))
    xs = full(r.x)
    nk = float(np.max(np.abs(r.fun))) if r.fun.size else 0.0
    return xs, nk <= tol, f"TRF {r.status} in {r.nfev} evaluations, largest residual {nk:.1e}"


def solve(ctx, method: str):
    """Solve the built system by method: "newton" (at CAPRI's slope), "continuation" (Newton at the slopes of
    market.trq_slope_steps, then CAPRI's, each from the last; CAPRI's own way in trim_trqs.gms), "ipopt", or "auto"
    (newton, then continuation from the start where it stalls, then IPOPT from the start); (x, ok, message). With
    market.bounds = "capri" IPOPT takes CAPRI's bounds and widens them as CAPRI (market_bounds.py)."""
    st = _settings()
    tol = float(st.get("market.chain_tol"))
    max_iter = int(st.get("market.chain_max_iter"))
    fF, fJ, x0, keep, sc, slope = ctx["fF"], ctx["fJ"], ctx["x0"], ctx["keep"], ctx["sc"], ctx["slope"]
    lin, _ = _linear_solver(str(st.get("market.newton_linear_solver")))
    if method == "newton":
        x, ok, it, nk = _newton(fF, fJ, x0, keep, sc, tol, max_iter, slope)
        return x, ok, f"Newton ({lin}) {'converged' if ok else 'stalled at %.1e' % nk} in {it} steps"
    if method == "continuation":
        steps = [float(v) for v in st.get("market.trq_slope_steps") if float(v) < slope] + [slope]
        x, done = x0, []
        for sl in steps:
            x, ok, it, nk = _newton(fF, fJ, x, keep, sc, tol if sl == slope else max(tol, 1e-6), max_iter, sl)
            done.append(f"{sl:g}: {it}")
            if not ok:
                return x, False, f"continuation ({lin}) stalled at slope {sl:g} at {nk:.1e} (steps {', '.join(done)})"
        return x, True, f"continuation ({lin}) converged (steps per slope {', '.join(done)})"
    if method in ("ssn", "trf"):
        # G3.4 point 2: the bounds in the Newton chain. ssn: the semismooth Newton on the MCP form (_mcp_system), at the
        # continuation's slopes (each from the last, as "continuation"); trf: the trust-region reflective least squares
        # at the same slopes. With market.bounds = "none" both are the unbounded system (ssn = Newton)
        lbx, ubx = _bounds(ctx)
        lbx, ubx = lbx.copy(), ubx.copy()
        lbx[ctx["empty"]], ubx[ctx["empty"]] = x0[ctx["empty"]], x0[ctx["empty"]]
        steps = [float(v) for v in st.get("market.trq_slope_steps") if float(v) < slope] + [slope]
        x, done = np.clip(x0.copy(), lbx, ubx), []
        if method == "ssn":
            fP, fJP, sgn = _mcp_system(ctx, lbx, ubx)
            allk = np.arange(int(x0.size))
            one = np.ones(int(x0.size))
            if ctx.get("from_equilibrium"):
                # started at the fixed point's equilibrium, which solves the system at CAPRI's slope: Newton there
                # first; the continuation from the lower slopes only where it stalls
                x1, ok, it, nk = _newton(fP, fJP, x, allk, one, tol, max_iter, slope)
                if ok:
                    x = x1
                    steps, done = [], [f"{slope:g}: {it}"]
            for sl in steps:
                x, ok, it, nk = _newton(fP, fJP, x, allk, one, tol, max_iter, sl)
                done.append(f"{sl:g}: {it}")
                if not ok:
                    return x, False, (f"semismooth Newton ({lin}) stalled at slope {sl:g} at {nk:.1e} "
                                      f"(steps {', '.join(done)})")
            msg = f"semismooth Newton ({lin}) converged (steps per slope {', '.join(done)})"
            if str(st.get("market.bounds")) == "capri":
                x, ok, wmsg = simu_market_widen(ctx, x, lbx, ubx, sgn, tol, max_iter, slope)
                msg += wmsg
                return x, ok, msg
            return x, True, msg
        for sl in steps:
            x, ok, msg = _trf(ctx, x, lbx, ubx, tol, sl)
            done.append(f"{sl:g}: {msg}")
            if not ok:
                return x, False, "; ".join(done)
        return x, True, "; ".join(done)
    if method == "ipopt":
        lbx, ubx = _bounds(ctx)
        lbx, ubx = lbx.copy(), ubx.copy()
        lbx[ctx["empty"]], ubx[ctx["empty"]] = x0[ctx["empty"]], x0[ctx["empty"]]
        ils = str(st.get("market.ipopt_linear_solver"))
        xs, ok, stat = _ipopt(ctx, x0, lbx, ubx, tol, max_iter)
        msgs = [f"IPOPT ({ils.upper()}) {stat}"]
        if str(st.get("market.bounds")) == "capri":
            # CAPRI's simu_market.gms l. 92-150: at most two solves; after an infeasible one, the bounds that hold it
            # widened (widen_bounds.gms FULL), from the bounds' multipliers of a least-infeasibility solve (CONOPT's
            # infeasibility report in CAPRI; IPOPT has none: DEP-45's phase 1, as CAPTRD-MOD's estimation)
            from capri_mod.market.market_bounds import widen
            for _try in range(int(st.get("market.widen_bounds_tries"))):
                if ok:
                    break
                xp, lam = _phase1(ctx, xs, lbx, ubx, tol, max_iter)
                lbx, ubx, moved = widen(ctx["mm"], ctx["lay"], xp, lbx, ubx, lam, base=x0)
                lbx[ctx["empty"]], ubx[ctx["empty"]] = x0[ctx["empty"]], x0[ctx["empty"]]
                ctx["bounds"] = (lbx, ubx)
                # ProdFudge_ where a widened lower bound is at or below 0 (CAPRI: the fudge rows enter with the bounds)
                ctx["fmv"] = _fudge_modes(ctx, lbx)
                if not moved:
                    msgs.append("infeasible, no bound to widen")
                    break
                xs, ok, stat = _ipopt(ctx, np.clip(xp, lbx, ubx), lbx, ubx, tol, max_iter)
                msgs.append(f"{moved} bounds widened, IPOPT {stat}")
        return xs, ok, "; ".join(msgs)
    if method == "auto":
        msgs = []
        for m in ("newton", "continuation", "ipopt"):
            x, ok, msg = solve(ctx, m)
            if ok and m != "ipopt" and str(st.get("market.bounds")) == "capri":
                # Newton and the continuation take no bounds: a solution outside CAPRI's goes to IPOPT, which takes them
                from capri_mod.market.market_bounds import violated
                lb, ub = _bounds(ctx)
                out = violated(ctx["lay"], x, lb, ub, tol=1e-9)
                if out:
                    ok = False
                    msg += f"; outside CAPRI's bounds in {len(out)} unknowns (first {out[0][0]}[{out[0][1]}])"
            msgs.append(msg)
            if ok:
                break
        return x, ok, "; ".join(msgs)
    raise ValueError(f"unknown method of the market system {method!r}")


def simu_market_widen(ctx, x, lbx, ubx, sgn, tol, max_iter, slope) -> tuple:
    r"""CAPRI's GAMS (arm/simu_market.gms l. 95-145):

          while ( ((m_globMarket.NumInfes > 0) and (Abs(m_globMarket.Suminfes) GT 1.E-5)) and (p_nRepeatedSolves LE 1),
        *
        *  v_prodQuant.l(RMS,"OTHO") = v_prodQuant.l(RMS,"OTHO") * uniform(0.90,1.1);


        $batinclude 'util\title.gms' "'Solve market, year %SIMY%, step '" ORD(step):0:0 "'('" CARD(STEP):0:0 "'), try # '" p_nRepeatedSolves:0:0
        *
        *
        *       --- on try # 3 during last iteration, print solution
        *
                if ( (p_nRepeatedSolves eq 1) and (ord(Step) eq card(step)), m_globMarket.solprint = 1);
        *
                SOLVE m_globMarket USING DNLP Minimizing V_dummy;

        *       abort "stop";

                if ( ord(step) eq card(step), m_globMarket.Reslim = m_globMarket.Reslim * 1.5;);

                if ( m_globMarket.suminfes gt 1.E+6,
        $include 'arm\treat_enormous_infes.gms'
                );
        *
        $batinclude 'arm\check_square.gms' %system.fn% %system.incline%


                if ( EXECERROR > 0,
                           putclose caplog "*** --- Global market model of simulation loop Nr. ", step.pos, " could not been solved - CAPRI aborted" /;
                           putclose caplog "*** --- Probably your scenario assumptions were too drastic. Try to use less dramatic changes" /;
                           putclose caplog "*** --- If that doesn't help, contact CAPRI expert" /;
                   abort "internal error");
        *
        *          --- some error in triangular part (zero iterations): try to switch it off ...
                if (m_globMarket.iterusd eq 0,
                   m_globMarket.Optfile = 103;
                else
                   m_globMarket.Optfile = 603;
                );
        *
                if ( ((m_globMarket.solvestat eq 2) or (m_globMarket.solvestat eq 3) or (p_nRepeatedSolves > 0)),
        *        --- ressource/iteration interrupt on last try or more then one solve: use pre-steps in next try again
                     p_lstIters(XXGRPS) = 100;
                );
        *
        *          --- infeasible: widen bounds
                if ( (m_globMarket.numinfes gt 0),
        *
        $batinclude 'arm\widen_bounds.gms' FULL
                );
        *
                p_nRepeatedSolves = P_nRepeatedSolves + 1;
          );

    The project's notation: x the lifted system's unknowns at the semismooth Newton's solution of the bounded MCP
    (CAPRI's first SOLVE), lbx / ubx CAPRI's start bounds (set_start_val.gms; market_bounds.capri_start_bounds), F the
    system's equations in their own units (ctx["fF"]) and Fo = F / sc x sgn the scaled, oriented ones the MCP pairs
    with x. NumInfes / SumInfes: the unknowns at a bound whose paired equation is left unmet (Fo > 0 at a lower bound,
    < 0 at an upper one, beyond the solve's tolerance tol) and the sum of |F| over them: the MCP's solution is CAPRI's
    infeasible solve, the residual left where a bound holds. While SumInfes > 1e-5 and at most market.widen_bounds_tries
    widenings (CAPRI: p_nRepeatedSolves LE 1, two solves, so one widening between them; the default 1): the bounds of
    those unknowns widened by widen_bounds.gms FULL's rules (market_bounds.widen, the unknowns named by their unmet
    equation as CAPRI's by CONOPT's marginals), the fudge rows switched on where a widened lower bound is at or below 0
    (ProdFudge_, ProcFudge_, FeedFudge_: _fudge_modes), and the MCP solved again from x at CAPRI's slope. CAPRI's
    widening after the last solve (the loop's body ends with it) is not repeated: its bounds are reset at the next
    market solve (set_start_val.gms), so they act on nothing.

    Not ported: the options and the solver's own handling (Reslim, Optfile 103/603, p_lstIters, treat_enormous_infes,
    check_square), which are CONOPT's; the release of the trade flows fixed by the widening (l. 159-185), as the trade
    flows are not unknowns of the lifted system.

    Departures from CAPRI: the infeasible cells are named by the MCP's unmet equations at their bounds, not by CONOPT's
    phase-1 marginals (register DEP-50); SumInfes is measured on the lifted system's equations in their own units.

    Returns (x, ok, message suffix)."""
    from capri_mod.market.market_bounds import widen
    st = _settings()
    x0 = ctx["x0"]
    sc = ctx["sc"]
    msg = ""
    for _try in range(int(st.get("market.widen_bounds_tries"))):
        F = np.asarray(ctx["fF"](x, slope), float).ravel()
        Fo = F / sc * sgn
        free = lbx < ubx
        btol = 1e-8 * np.maximum(1.0, np.abs(x))
        atl = free & np.isfinite(lbx) & (x - lbx <= btol)
        atu = free & np.isfinite(ubx) & (ubx - x <= btol)
        infes = (atl & (Fo > tol)) | (atu & (Fo < -tol))
        num_infes = int(infes.sum())
        sum_infes = float(np.abs(F[infes]).sum())
        if num_infes == 0 or sum_infes <= 1e-5:
            break
        lam = np.where(infes, np.abs(Fo), 0.0)
        lbx, ubx, moved = widen(ctx["mm"], ctx["lay"], x, lbx, ubx, lam, tol=1e-8, base=x0)
        lbx[ctx["empty"]], ubx[ctx["empty"]] = x0[ctx["empty"]], x0[ctx["empty"]]
        ctx["bounds"] = (lbx, ubx)
        ctx["fmv"] = _fudge_modes(ctx, lbx)
        if not moved:
            msg += f"; {num_infes} unknowns held at a bound (SumInfes {sum_infes:.2e}), no bound to widen"
            break
        fP, fJP, sgn = _mcp_system(ctx, lbx, ubx)
        n = int(x0.size)
        x, ok, it, nk = _newton(fP, fJP, np.clip(x, lbx, ubx), np.arange(n), np.ones(n), tol, max_iter, slope)
        msg += (f"; {num_infes} unknowns held at a bound (SumInfes {sum_infes:.2e}): {moved} bounds widened, "
                f"semismooth Newton {'converged' if ok else 'stalled at %.1e' % nk} in {it} steps")
        if not ok:
            return x, False, msg
    return x, True, msg


def _bounds(ctx) -> tuple:
    """The unknowns' bounds for the solve: CAPRI's start bounds (market.bounds = "capri", market_bounds.py) or
    none ("none"); cached in ctx."""
    b = ctx.get("bounds")
    if b is None:
        mode = str(_settings().get("market.bounds"))
        x0 = ctx["x0"]
        if mode == "capri":
            from capri_mod.market.market_bounds import capri_start_bounds
            b = capri_start_bounds(ctx["mm"], ctx["lay"], x0)
        elif mode == "none":
            b = (np.full(x0.size, -np.inf), np.full(x0.size, np.inf))
        else:
            raise ValueError(f"market.bounds: {mode!r} (\"none\" or \"capri\")")
        ctx["bounds"] = b
    return b


def _ipopt_opts(tol, max_iter) -> dict:
    """IPOPT's options: the tolerances, the linear solver (market.ipopt_linear_solver; MUMPS with the METIS
    ordering, or HSL's with market.hsl_library), the Lagrangian's Hessian by L-BFGS."""
    st = _settings()
    ils = str(st.get("market.ipopt_linear_solver"))
    opts = {"ipopt.print_level": 0, "print_time": False, "ipopt.sb": "yes", "ipopt.tol": tol,
            "ipopt.constr_viol_tol": tol, "ipopt.max_iter": max_iter, "ipopt.linear_solver": ils,
            "ipopt.hessian_approximation": "limited-memory"}
    if ils == "mumps":
        opts.update({"ipopt.mumps_pivot_order": 5, "ipopt.mumps_mem_percent": 100})
    elif ils in ("ma27", "ma57", "ma77", "ma86", "ma97"):
        lib = str(st.get("market.hsl_library"))
        if lib:
            opts["ipopt.hsllib"] = lib              # else IPOPT looks for libhsl / libcoinhsl on the library path
    else:
        raise ValueError(f"market.ipopt_linear_solver: {ils!r} (\"mumps\" or an HSL solver: ma27, ma57, ma77, "
                         "ma86, ma97)")
    return opts


def _ipopt(ctx, x0, lbx, ubx, tol, max_iter) -> tuple:
    """IPOPT on the system with a zero objective (CAPRI's V_dummy), the equations kept as equality constraints divided
    by their row scales, the unknowns within [lbx, ubx]; (x, ok, status text)."""
    import casadi as ca
    x, F, keep, sc = ctx["x"], ctx["F"], ctx["keep"], ctx["sc"]
    g = _eqs(ctx, F[keep.tolist()] / ca.DM(sc[keep]))
    solver = ca.nlpsol("market_system_ipopt", "ipopt", {"x": x, "f": ca.SX(0.0), "g": g}, _ipopt_opts(tol, max_iter))
    sol = solver(x0=x0, lbx=lbx, ubx=ubx, lbg=0.0, ubg=0.0)
    stats = solver.stats()
    xs = np.asarray(sol["x"], float).ravel()
    viol = float(np.max(np.abs(np.asarray(sol["g"], float)))) if keep.size else 0.0
    ok = bool(stats.get("success")) and viol <= 10.0 * tol
    return xs, ok, f"{stats.get('return_status')} in {stats.get('iter_count')} iterations"


def _phase1(ctx, x0, lbx, ubx, tol, max_iter) -> tuple:
    """The least-infeasibility solve (as CONOPT's phase 1 reports an infeasible model; CAPTRD-MOD's DEP-45): min
    sum(p + n) + mu ||x - x0||^2 over x within [lbx, ubx] and p, n >= 0 with F(x)[keep] / sc - p + n = 0, mu
    market.widen_phase1_proximity (a small term that makes the point unique); (x, the unknowns' bound multipliers lam_x,
    negative at a lower bound, positive at an upper one)."""
    import casadi as ca
    x, F, keep, sc = ctx["x"], ctx["F"], ctx["keep"], ctx["sc"]
    m = int(keep.size)
    pv, nv = ca.SX.sym("p", m), ca.SX.sym("n", m)
    g = _eqs(ctx, F[keep.tolist()] / ca.DM(sc[keep])) - pv + nv
    mu = float(_settings().get("market.widen_phase1_proximity"))
    f = ca.sum1(pv + nv) + mu * ca.sumsqr(x - ca.DM(np.asarray(x0, float)))
    z = ca.vertcat(x, pv, nv)
    solver = ca.nlpsol("market_system_phase1", "ipopt", {"x": z, "f": f, "g": g}, _ipopt_opts(tol, max_iter))
    r0 = np.abs(np.asarray(ctx["fF"](np.asarray(x0, float), ctx["slope"]), float).ravel()[keep] / sc[keep])
    z0 = np.concatenate([np.asarray(x0, float), r0, r0])
    lbz = np.concatenate([lbx, np.zeros(2 * m)])
    ubz = np.concatenate([ubx, np.full(2 * m, np.inf)])
    sol = solver(x0=z0, lbx=lbz, ubx=ubz, lbg=0.0, ubg=0.0)
    n = int(np.asarray(x0).size)
    return (np.asarray(sol["x"], float).ravel()[:n], np.asarray(sol["lam_x"], float).ravel()[:n])


def residual(ctx, xs) -> tuple:
    """The largest scaled residual at xs (row scales) and the scaled residuals of the equations kept."""
    keep, sc = ctx["keep"], ctx["sc"]
    rr = np.abs(np.asarray(ctx["fF"](xs, ctx["slope"]), float).ravel()[keep]) / sc[keep]
    return float(rr.max()) if rr.size else 0.0, rr


def apply(mm, ctx, xs, r, exogenous_supply, trade_scenario):
    """The solution as the fixed point's start: the price ratios (a frame like r), the quotas' sigmas and their rate
    offsets set, the fixed point's lagged evaluation state settled at it."""
    lay = ctx["lay"]
    out = r.copy()
    o = 0
    sysd = mm.par.bilat
    for name, n in lay["x"]:
        v = xs[o:o + n]
        if name.startswith("r_"):
            c = name[2:]
            out.loc[list(sysd[c].regions), c] = v
        elif name.startswith("sB_") or name.startswith("sW_"):
            c = name[3:]
            _, _, bil, glo = lay["sig"][c]
            sc_ = sysd[c]
            if name.startswith("sB_"):
                s_ = np.asarray(sc_.trq_sigma, float).copy()
                s_[bil] = v
                sc_.trq_sigma = s_
            else:
                s_ = np.asarray(sc_.trq_sigmaW, float).copy()
                s_[glo] = v
                sc_.trq_sigmaW = s_
        o += n
    # the quotas' rate offsets the fixed point's import prices read, at the solution's sigmas and prices
    for c, sc_ in sysd.items():
        if (sc_.trq_quotas or sc_.trq_globals) and sc_.trq_sigma is not None:
            sc_.trq_set_offsets(out[c].reindex(list(sc_.regions)).to_numpy(dtype=float))
    # the fixed point's evaluation reads its blocks' state of the previous evaluation (the non-EU land and FEDE blocks
    # the previous raw milk prices: KNOWN_ISSUES K147); evaluated again at the solution's prices until its supply
    # settles, so that the fixed point starts from that state at the solution
    st = _settings()
    tol = float(st.get("market.chain_tol"))
    prev = None
    for k in range(int(st.get("market.chain_settle_evals"))):
        S_, D_, _, _, _ = mm._bilateral_eval(out, exogenous_supply, trade_scenario)
        q = np.concatenate([S_.to_numpy(dtype=float).ravel(), D_.to_numpy(dtype=float).ravel()])
        if prev is not None and float(np.max(np.abs(q - prev) / np.maximum(np.abs(prev), 1.0))) < tol:
            break
        prev = q
    return out


def chain_market_solve(mm, r, exogenous_supply, trade_scenario, method: str = "chain", from_equilibrium=False):
    """The market system solved from the start r (and the module's state); method "chain" (Newton, then the
    continuation, then IPOPT: solve(ctx, "auto")), "ipopt" or "ssn" (the semismooth Newton on the MCP form, CAPRI's
    bounds; after the fixed point with market.bounds = "capri"); from_equilibrium: r is the fixed point's equilibrium
    (the semismooth Newton starts at CAPRI's slope); the solution's price ratios as a frame like r, or None (see the
    module's docstring)."""
    try:
        if from_equilibrium and str(_settings().get("market.bounds")) == "capri":
            t1 = time.time()
            lifted = _lifted(mm, r, exogenous_supply, trade_scenario)
            if within_capri_start_bounds(mm, lifted[1], lifted[5]):
                print(f"    market solve by the chain: the fixed point's equilibrium within CAPRI's start bounds, kept "
                      f"({time.time() - t1:.1f} s)", flush=True)
                del lifted
                import gc
                gc.collect()
                return r
            ctx = build(mm, r, exogenous_supply, trade_scenario, lifted=lifted)
            del lifted
        else:
            ctx = build(mm, r, exogenous_supply, trade_scenario)
    except NotImplementedError as e:
        print(f"    market solve by the chain not possible here ({e}); the fixed point solves it", flush=True)
        return None
    ctx["from_equilibrium"] = bool(from_equilibrium)
    t1 = time.time()
    xs, ok, msg = solve(ctx, {"chain": "auto", "ipopt": "ipopt", "ssn": "ssn"}[method])
    worst, rr = residual(ctx, xs)
    lay, keep = ctx["lay"], ctx["keep"]
    if not ok and rr.size:
        names = [f"{n}[{k}]" for n, m in lay["eqs"] for k in range(m)]
        msg += f" (largest at {names[int(keep[int(np.argmax(rr))])]})"
    print(f"    market solve by the chain: {msg}; largest scaled residual {worst:.1e}; {time.time() - t1:.1f} s (system "
          f"built in {ctx['built']:.1f} s)", flush=True)
    # the system is not kept on the module: its CasADi graphs take some GB, which the regional solves' forked workers
    # would carry (a mini-EU run with market.bounds = "capri" had a worker killed for memory, 26 November 2026)
    try:
        if not ok:
            return None
        return apply(mm, ctx, xs, r, exogenous_supply, trade_scenario)
    finally:
        ctx.clear()
        import gc
        gc.collect()
        try:                                   # glibc keeps freed memory in the process unless asked to return it
            import ctypes
            ctypes.CDLL("libc.so.6").malloc_trim(0)
        except (OSError, AttributeError):
            pass
