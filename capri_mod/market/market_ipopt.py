"""G3: one market solve by IPOPT on the market's equations as one system in CAPRI's form (market.solver = "ipopt").

The system is capri_mod/market/market_system_ad.py's lifted form (the producer price ratios of the bilateral
commodities, the active quotas' sigmas, the young-animal prices, the dairy blocks, FEDE and the non-EU rents, with the
Armington ratios, supply and use as unknowns of their own and their defining equations; CAPRI's m_globMarket), with a
zero objective and the equations as equality constraints, as CAPRI solves its market with CONOPT. The balances of a
region-commodity without supply, use or trade are left out and their prices held (G3_SYSTEM.md, G3.2e). The start is
the module's state, the previous solve's solution. IPOPT: MUMPS with the METIS ordering and mumps_mem_percent 100 (with
MUMPS's defaults the factorisation's workspace is refused on this market), the Lagrangian's Hessian by L-BFGS, the
tolerances market.ipopt_tol, at most market.ipopt_max_iter iterations; each equation divided by its largest
derivative at the start.

`ipopt_market_solve` returns the solution's price ratios (and sets the quotas' sigmas), or None when the system cannot
be built (a trade scenario's tariff additions, a region-commodity without a base price; the message says which) or
IPOPT does not solve it; the caller (the fixed point of bilateral_solve.py) then goes on from its own start. Not yet:
CAPRI's bounds and widen_bounds (G3.4).
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
        raise RuntimeError(f"market_ipopt: {sc_.size} scales for {lay['n_F']} equations")
    return sc_


def ipopt_market_solve(mm, r, exogenous_supply, trade_scenario):
    """IPOPT on the market system from the start r (and the module's state); the solution's price ratios as a frame
    like r, or None (see the module's docstring)."""
    import casadi as ca
    from capri_mod.market.market_system_ad import market_system, market_x0
    st = _settings()
    t0 = time.time()
    try:
        # one evaluation at the start: the module's evaluation state (which blocks are active, their last solutions)
        mm._bilateral_eval(r, exogenous_supply, trade_scenario)
        fs, _, _, _ = market_system(mm, exogenous_supply, trade_scenario)
        fn, lay, x, F = market_system(mm, exogenous_supply, trade_scenario, lifted=True)
    except NotImplementedError as e:
        print(f"    market solve by IPOPT not possible here ({e}); the fixed point solves it", flush=True)
        return None
    x0 = market_x0(mm, lay)
    sp = fs.jac_sparsity(0, 0)
    empty = np.nonzero(np.diff(np.asarray(sp.T.colind())) == 0)[0]
    keep = np.setdiff1d(np.arange(lay["n_F"]), empty)
    # each equation divided by its largest derivative at the start (row scaling): the equations in the units of the
    # unknown that moves them most. The blocks' own scales (_scales) leave an equation that responds weakly to its
    # unknown loose: FeedBal_ divided by the energy fed lets FEDE miss by 1e-2 within a 1e-10 tolerance
    Jf = ca.Function("market_g3_jac", [x], [ca.jacobian(F, x)])
    Ja = abs(Jf(x0).sparse().tocsr())
    sc = np.maximum(np.asarray(Ja.max(axis=1).todense()).ravel(), 1e-12)
    lbx, ubx = -np.inf * np.ones(lay["n_x"]), np.inf * np.ones(lay["n_x"])
    lbx[empty], ubx[empty] = x0[empty], x0[empty]
    tol = float(st.get("market.ipopt_tol"))
    opts = {"ipopt.print_level": 0, "print_time": False, "ipopt.sb": "yes", "ipopt.tol": tol,
            "ipopt.constr_viol_tol": tol, "ipopt.max_iter": int(st.get("market.ipopt_max_iter")),
            "ipopt.linear_solver": "mumps", "ipopt.mumps_pivot_order": 5, "ipopt.mumps_mem_percent": 100,
            "ipopt.hessian_approximation": "limited-memory"}
    solver = ca.nlpsol("market_g3", "ipopt", {"x": x, "f": ca.SX(0.0), "g": F[keep.tolist()] / ca.DM(sc[keep])},
                       opts)
    t1 = time.time()
    sol = solver(x0=x0, lbx=lbx, ubx=ubx, lbg=0.0, ubg=0.0)
    stats = solver.stats()
    xs = np.asarray(sol["x"], float).ravel()
    viol = float(np.max(np.abs(np.asarray(sol["g"], float)))) if keep.size else 0.0
    Fs = np.abs(np.asarray(fn(xs)[0], float).ravel())[keep] / _scales(mm, lay)[keep]
    ok = bool(stats.get("success")) and viol <= 10.0 * tol
    print(f"    market solve by IPOPT: {stats.get('return_status')} in {stats.get('iter_count')} iterations, "
          f"largest scaled residual {viol:.1e} (by the blocks' scales {float(Fs.max()) if Fs.size else 0.0:.1e}); "
          f"{time.time() - t1:.1f} s (system and solver built in {t1 - t0:.1f} s)",
          flush=True)
    mm._g3_last = (fn, lay, xs)          # for diagnostics (tools/check): the system and its solution
    if not ok:
        return None
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
    # the quotas' rate offsets the fixed point's import prices read, at IPOPT's sigmas and prices
    for c, sc_ in sysd.items():
        if (sc_.trq_quotas or sc_.trq_globals) and sc_.trq_sigma is not None:
            sc_.trq_set_offsets(out[c].reindex(list(sc_.regions)).to_numpy(dtype=float))
    # the fixed point's evaluation reads its blocks' state of the previous evaluation (the non-EU land and FEDE blocks
    # the previous raw milk prices: KNOWN_ISSUES K147); evaluated again at IPOPT's prices until its supply settles, so
    # that the fixed point starts from that state at IPOPT's solution
    prev = None
    for k in range(int(st.get("market.ipopt_settle_evals"))):
        S_, D_, _, _, _ = mm._bilateral_eval(out, exogenous_supply, trade_scenario)
        q = np.concatenate([S_.to_numpy(dtype=float).ravel(), D_.to_numpy(dtype=float).ravel()])
        if prev is not None and float(np.max(np.abs(q - prev) / np.maximum(np.abs(prev), 1.0))) < tol:
            break
        prev = q
    return out
