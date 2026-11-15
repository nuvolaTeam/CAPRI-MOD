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


def build(mm, r, exogenous_supply, trade_scenario):
    """The lifted market system at the module's state after one evaluation at r, with the quotas' sigmoid slope as a
    parameter: a dict with its Functions F(x, slope) and Jacobian, the start x0, the equations kept (the empty balances
    out), the unknowns held (their prices), the row scales, CAPRI's slope; NotImplementedError where it cannot be
    built."""
    import casadi as ca
    from capri_mod.market.market_system_ad import market_system, market_x0
    t0 = time.time()
    mm._bilateral_eval(r, exogenous_supply, trade_scenario)
    fs, _, _, _ = market_system(mm, exogenous_supply, trade_scenario)
    s = ca.SX.sym("slope")
    # with CAPRI's bounds the processing and non-EU feed cells are unknowns too (their bounds and fudge rows)
    fn, lay, x, F = market_system(mm, exogenous_supply, trade_scenario, lifted=True, slope=s, fudge=True,
                                  lift_use=str(_settings().get("market.bounds")) == "capri")
    fm = lay["fm"]
    x0 = market_x0(mm, lay)
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


def chain_market_solve(mm, r, exogenous_supply, trade_scenario, method: str = "chain"):
    """The market system solved from the start r (and the module's state); method "chain" (Newton, then the
    continuation, then IPOPT: solve(ctx, "auto")) or "ipopt"; the solution's price ratios as a frame like r, or None
    (see the module's docstring)."""
    try:
        ctx = build(mm, r, exogenous_supply, trade_scenario)
    except NotImplementedError as e:
        print(f"    market solve by the chain not possible here ({e}); the fixed point solves it", flush=True)
        return None
    t1 = time.time()
    xs, ok, msg = solve(ctx, "auto" if method == "chain" else "ipopt")
    worst, rr = residual(ctx, xs)
    lay, keep = ctx["lay"], ctx["keep"]
    if not ok and rr.size:
        names = [f"{n}[{k}]" for n, m in lay["eqs"] for k in range(m)]
        msg += f" (largest at {names[int(keep[int(np.argmax(rr))])]})"
    print(f"    market solve by the chain: {msg}; largest scaled residual {worst:.1e}; {time.time() - t1:.1f} s (system "
          f"built in {ctx['built']:.1f} s)", flush=True)
    mm._chain_last = (ctx, xs)              # for diagnostics (tools/check): the system and its solution
    if not ok:
        return None
    return apply(mm, ctx, xs, r, exogenous_supply, trade_scenario)
