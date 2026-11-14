"""G3: one market solve on the market's equations as one system in CAPRI's form (market.solver = "g3_newton" or
"g3_ipopt"; docs/design/G3_SYSTEM.md).

The system is capri_mod/market/market_system_ad.py's lifted form (the producer price ratios of the bilateral
commodities, the active quotas' sigmas, the young-animal prices, the dairy blocks, FEDE and the non-EU rents, with the
Armington ratios, supply and use as unknowns of their own and their defining equations; CAPRI's m_globMarket). The
balances of a region-commodity without supply, use or trade are left out and their prices held (G3_SYSTEM.md, G3.2e);
the rest is square. Each equation is divided by its largest derivative at the start. The start is the module's state,
the previous solve's solution. Two methods:

- "g3_newton": Newton's method with the exact sparse Jacobian (CasADi), globalised by a backtracking line search on
  the largest scaled residual or Powell's dogleg trust region (market.g3_newton_step); the linear solves by market.g3_linear_solver: "pardiso" (Intel MKL's PARDISO through pypardiso,
  an optional package under Intel's licence, installed by the user like CAPRI's CONOPT) or "mumps" (bundled with
  CasADi, open). Where its line search stalls (a quota's steep sigmoid), a continuation on the quotas' slope
  (market.g3_slope_steps, then CAPRI's 200: CAPRI's own way in trim_trqs.gms), then IPOPT from the start. The fastest
  measured (G3_SYSTEM.md, the solver comparison).
- "g3_ipopt": IPOPT with a zero objective and the equations as equality constraints, as CAPRI solves its market with
  CONOPT; its linear solver market.g3_ipopt_linear_solver: "mumps" (bundled; the METIS ordering and mumps_mem_percent
  100: MUMPS's defaults are refused their workspace on this market) or one of HSL's (ma27, ma57, ma77, ma86, ma97:
  Coin-HSL, under STFC's licence, built and installed by the user like CAPRI's CONOPT; market.g3_hsllib its library),
  the Lagrangian's Hessian by L-BFGS. With bounds (G3.4) this is the method that takes them.

Both stop at market.g3_tol, at most market.g3_max_iter iterations. `g3_market_solve` returns the solution's price ratios
(and sets the quotas' sigmas and their rate offsets, then settles the fixed point's lagged evaluation state at it), or
None when the system cannot be built (a trade scenario's tariff additions, a region-commodity without a base price; the
message says which) or the method does not solve it; the caller (the fixed point of bilateral_solve.py) then goes on
from its own start, or from the solution, which it confirms in its first evaluation. Not yet: CAPRI's bounds and
widen_bounds (G3.4).
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
        raise RuntimeError(f"market_g3: {sc_.size} scales for {lay['n_F']} equations")
    return sc_


def _ma28(lib_path: str):
    """HSL's MA28 (sparse unsymmetric LU, Coin-HSL's libcoinhsl, STFC's licence) through ctypes: (A, b) -> A^-1 b.
    MA28AD factorises (threshold pivoting u = 0.1, MC23AD's block triangular form first, MA28's defaults), MA28CD
    solves; the arrays' lengths (6 x the non-zeros) doubled where MA28 reports them short (IFLAG -3, -4, -5, -6)."""
    import ctypes
    import ctypes.util
    path = lib_path or ctypes.util.find_library("coinhsl") or ctypes.util.find_library("hsl")
    if not path:
        raise RuntimeError("market.g3_linear_solver = \"ma28\" needs Coin-HSL's library (market.g3_hsllib)")
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
    not installed, with a message), "mumps" (CasADi's) or "ma28" (HSL's, Coin-HSL's library market.g3_hsllib)."""
    import casadi as ca
    if name == "ma28":
        return "ma28", _ma28(str(_settings().get("market.g3_hsllib")))
    if name == "pardiso":
        try:
            import pypardiso
            return "pardiso", lambda A, b: pypardiso.spsolve(A.tocsr(), b)
        except ImportError:
            print("    market.g3_linear_solver = \"pardiso\" needs the package pypardiso (Intel MKL's PARDISO, Intel's "
                  "licence): MUMPS instead", flush=True)
    elif name != "mumps":
        raise ValueError(f"market.g3_linear_solver: {name!r} (\"pardiso\", \"mumps\" or \"ma28\")")

    def mumps(A, b):
        A = A.tocsc()
        M = ca.DM(ca.Sparsity(A.shape[0], A.shape[1], A.indptr.tolist(), A.indices.tolist()), A.data)
        ls = ca.Linsol("g3_mumps", "mumps", M.sparsity())
        ls.sfact(M)
        ls.nfact(M)
        return np.asarray(ls.solve(M, ca.DM(b)), float).ravel()
    return "mumps", mumps


def _newton(fF, fJ, x0, keep, sc, tol, max_iter, slope):
    """Newton's method on the scaled square system F(x, slope)[keep] / sc = 0 over x[keep]; (x, ok, Jacobians
    factorised, the largest scaled residual). Converged when the largest scaled residual is at most tol. The step by
    market.g3_newton_step:

    - "linesearch": the Newton step, halved until the largest scaled residual falls (the form of G3.2-G3.3);
    - "dogleg": Powell's dogleg trust region on the merit 0.5 ||r||^2 (MINPACK's hybrj, SciPy's fsolve): the Newton
      step where it lies in the trust region, otherwise the dogleg between the Cauchy (steepest-descent) point and the
      Newton step; accepted when the merit falls by at least 1e-4 of the decrease the linear model predicts; the
      region shrunk (x 0.25) where the model predicts poorly (ratio below 0.25) and widened (x 2) where it predicts well
      (above 0.75) at the region's edge. A rejected step reuses the factorisation.

    Stalled: no descent (line search), the trust region below 1e-12 of the step (dogleg), or the residual (the largest
    scaled residual; the merit's root for the dogleg) not halved over market.g3_stall_steps Jacobians (Newton
    creeping along a quota's flat sigmoid: 200 steps for 6.9e-3 on the base market at +5% soft wheat)."""
    import scipy.sparse as sps
    st = _settings()
    _, solve = _linear_solver(str(st.get("market.g3_linear_solver")))
    mode = str(st.get("market.g3_newton_step"))
    if mode not in ("linesearch", "dogleg"):
        raise ValueError(f"market.g3_newton_step: {mode!r} (\"linesearch\" or \"dogleg\")")
    D = sps.diags(1.0 / sc[keep])
    x = x0.copy()

    def res(v):
        return np.asarray(fF(v, slope), float).ravel()[keep] / sc[keep]
    r = res(x)
    nk = float(np.max(np.abs(r))) if r.size else 0.0
    it = 0
    k_stall = int(st.get("market.g3_stall_steps"))
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
    fn, lay, x, F = market_system(mm, exogenous_supply, trade_scenario, lifted=True, slope=s)
    x0 = market_x0(mm, lay)
    sp = fs.jac_sparsity(0, 0)
    empty = np.nonzero(np.diff(np.asarray(sp.T.colind())) == 0)[0]
    keep = np.setdiff1d(np.arange(lay["n_F"]), empty)
    fF = ca.Function("market_g3_F", [x, s], [F])
    fJ = ca.Function("market_g3_J", [x, s], [ca.jacobian(F, x)])
    slope = float(next(iter(mm.par.bilat.values())).TRQ_SLOPE)
    # each equation divided by its largest derivative at the start (row scaling): the equations in the units of the
    # unknown that moves them most. The blocks' own scales (_scales) leave an equation that responds weakly to its
    # unknown loose: FeedBal_ divided by the energy fed lets FEDE miss by 1e-2 within a 1e-10 tolerance
    Ja = abs(fJ(x0, slope).sparse().tocsr())
    sc = np.maximum(np.asarray(Ja.max(axis=1).todense()).ravel(), 1e-12)
    return dict(fn=fn, lay=lay, x=x, F=F, s=s, x0=x0, keep=keep, empty=empty, fF=fF, fJ=fJ, sc=sc, slope=slope,
                built=time.time() - t0)


def solve(ctx, method: str):
    """Solve the built system by method: "newton" (at CAPRI's slope), "continuation" (Newton at the slopes of
    market.g3_slope_steps, then CAPRI's, each from the last; CAPRI's own way in trim_trqs.gms), "ipopt", or "auto"
    (newton, then continuation from the start where it stalls, then IPOPT from the start); (x, ok, message)."""
    import casadi as ca
    st = _settings()
    tol = float(st.get("market.g3_tol"))
    max_iter = int(st.get("market.g3_max_iter"))
    fF, fJ, x0, keep, sc, slope = ctx["fF"], ctx["fJ"], ctx["x0"], ctx["keep"], ctx["sc"], ctx["slope"]
    lin, _ = _linear_solver(str(st.get("market.g3_linear_solver")))
    if method == "newton":
        x, ok, it, nk = _newton(fF, fJ, x0, keep, sc, tol, max_iter, slope)
        return x, ok, f"Newton ({lin}) {'converged' if ok else 'stalled at %.1e' % nk} in {it} steps"
    if method == "continuation":
        steps = [float(v) for v in st.get("market.g3_slope_steps") if float(v) < slope] + [slope]
        x, done = x0, []
        for sl in steps:
            x, ok, it, nk = _newton(fF, fJ, x, keep, sc, tol if sl == slope else max(tol, 1e-6), max_iter, sl)
            done.append(f"{sl:g}: {it}")
            if not ok:
                return x, False, f"continuation ({lin}) stalled at slope {sl:g} at {nk:.1e} (steps {', '.join(done)})"
        return x, True, f"continuation ({lin}) converged (steps per slope {', '.join(done)})"
    if method == "ipopt":
        x, F, s = ctx["x"], ctx["F"], ctx["s"]
        lbx, ubx = -np.inf * np.ones(len(x0)), np.inf * np.ones(len(x0))
        lbx[ctx["empty"]], ubx[ctx["empty"]] = x0[ctx["empty"]], x0[ctx["empty"]]
        g = ca.substitute(F[keep.tolist()] / ca.DM(sc[keep]), s, ca.SX(slope))
        ils = str(st.get("market.g3_ipopt_linear_solver"))
        opts = {"ipopt.print_level": 0, "print_time": False, "ipopt.sb": "yes", "ipopt.tol": tol,
                "ipopt.constr_viol_tol": tol, "ipopt.max_iter": max_iter, "ipopt.linear_solver": ils,
                "ipopt.hessian_approximation": "limited-memory"}
        if ils == "mumps":
            opts.update({"ipopt.mumps_pivot_order": 5, "ipopt.mumps_mem_percent": 100})
        elif ils in ("ma27", "ma57", "ma77", "ma86", "ma97"):
            lib = str(st.get("market.g3_hsllib"))
            if lib:
                opts["ipopt.hsllib"] = lib              # else IPOPT looks for libhsl / libcoinhsl on the library path
        else:
            raise ValueError(f"market.g3_ipopt_linear_solver: {ils!r} (\"mumps\" or an HSL solver: ma27, ma57, ma77, "
                             "ma86, ma97)")
        solver = ca.nlpsol("market_g3", "ipopt", {"x": x, "f": ca.SX(0.0), "g": g}, opts)
        sol = solver(x0=x0, lbx=lbx, ubx=ubx, lbg=0.0, ubg=0.0)
        stats = solver.stats()
        xs = np.asarray(sol["x"], float).ravel()
        viol = float(np.max(np.abs(np.asarray(sol["g"], float)))) if keep.size else 0.0
        ok = bool(stats.get("success")) and viol <= 10.0 * tol
        return xs, ok, f"IPOPT ({ils.upper()}) {stats.get('return_status')} in {stats.get('iter_count')} iterations"
    if method == "auto":
        msgs = []
        for m in ("newton", "continuation", "ipopt"):
            x, ok, msg = solve(ctx, m)
            msgs.append(msg)
            if ok:
                break
        return x, ok, "; ".join(msgs)
    raise ValueError(f"G3 method {method!r}")


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
    tol = float(st.get("market.g3_tol"))
    prev = None
    for k in range(int(st.get("market.g3_settle_evals"))):
        S_, D_, _, _, _ = mm._bilateral_eval(out, exogenous_supply, trade_scenario)
        q = np.concatenate([S_.to_numpy(dtype=float).ravel(), D_.to_numpy(dtype=float).ravel()])
        if prev is not None and float(np.max(np.abs(q - prev) / np.maximum(np.abs(prev), 1.0))) < tol:
            break
        prev = q
    return out


def g3_market_solve(mm, r, exogenous_supply, trade_scenario, method: str = "g3_newton"):
    """The market system solved from the start r (and the module's state); method "g3_newton" (Newton, then the
    continuation, then IPOPT: solve(ctx, "auto")) or "g3_ipopt"; the solution's price ratios as a frame like r, or None
    (see the module's docstring)."""
    try:
        ctx = build(mm, r, exogenous_supply, trade_scenario)
    except NotImplementedError as e:
        print(f"    market solve by G3 not possible here ({e}); the fixed point solves it", flush=True)
        return None
    t1 = time.time()
    xs, ok, msg = solve(ctx, "auto" if method == "g3_newton" else "ipopt")
    worst, rr = residual(ctx, xs)
    lay, keep = ctx["lay"], ctx["keep"]
    if not ok and rr.size:
        names = [f"{n}[{k}]" for n, m in lay["eqs"] for k in range(m)]
        msg += f" (largest at {names[int(keep[int(np.argmax(rr))])]})"
    print(f"    market solve by G3: {msg}; largest scaled residual {worst:.1e}; {time.time() - t1:.1f} s (system "
          f"built in {ctx['built']:.1f} s)", flush=True)
    mm._g3_last = (ctx, xs)              # for diagnostics (tools/check): the system and its solution
    if not ok:
        return None
    return apply(mm, ctx, xs, r, exogenous_supply, trade_scenario)
