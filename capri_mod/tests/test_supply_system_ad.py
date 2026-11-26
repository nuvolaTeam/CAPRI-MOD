"""The market's supply side as one CasADi function with its blocks' equations (capri_mod/market/
supply_system_ad.py) equals MarketModule.supply_response, and the blocks' residuals vanish, at the evaluation's own
block solutions: at a solved market and at random prices around it (the market of the model's data at CAPRI's base
supply rows: crushing, the dairy blocks, the non-EU ProdNQ_ rows with FEDE and the land rents, biofuels). The young
animals, the member states' raw milk response and Norway's supply models need a supply run's state: checked at captured
solves of a Farm-to-Fork run (tools/check/market_system_supply.py, MARKET_SYSTEM.md)."""
import numpy as np
import pytest


@pytest.fixture(scope="module")
def solved_base():
    """The market of the model's data solved at CAPRI's base supply rows."""
    from pathlib import Path
    from capri_mod.data.loaders import load_all_data
    from capri_mod.market.market_module import MarketModule
    root = Path(__file__).resolve().parents[2]
    mm = MarketModule(load_all_data(str(root / "capri_data")))
    exo = mm.capri_base_supply_rows()
    assert mm.solve(exogenous_supply=exo).converged
    return mm, exo


@pytest.mark.slow
def test_the_assembled_market_system_holds_at_the_default_solves_equilibrium(solved_base):
    """The assembled market system (capri_mod/market/market_system_ad.py): square, structurally nonsingular once the empty balances are out,
    and at the default solve's equilibrium every block's equations hold within that solve's tolerances. The balances within 1e-6 of S0 + D0, not market.tol (1e-7): the
    solve meets its test at its own last evaluation (9.0e-8 here), whose non-EU land and FEDE blocks read the previous
    evaluation's raw milk prices; evaluated again at the same prices the residual is 1.3e-7, and it drifts on (1.4e-7)
    as that lag is worked off (MARKET_SYSTEM.md, the assembled system)."""
    from capri_mod.market.market_system_ad import market_system, market_x0
    mm, exo = solved_base
    mm._bilateral_eval(mm.sv.bilat_last_r.copy(), exo, None)
    fn, lay, _, _ = market_system(mm, exo)
    assert lay["n_x"] == lay["n_F"] > 2000
    F, milk_bal, _, _ = (np.asarray(v, float).ravel() for v in fn(market_x0(mm, lay)))
    o = 0
    for name, n in lay["eqs"]:
        v = F[o:o + n]
        if name == "bal":
            sc = np.concatenate([np.maximum(np.asarray(s.S0 + s.D0, float), 1.0) for s in mm.par.bilat.values()])
            assert float(np.max(np.abs(v) / sc)) <= 1e-6, name
        elif n:
            assert float(np.max(np.abs(v) / _scale(mm, lay, name))) <= 1e-6, name
        o += n
    # raw milk is cleared in each region's dairy block (K165)
    assert milk_bal.size and float(np.max(np.abs(milk_bal))) <= 1e-6
    # structure: without the balances that are empty (no supply, use or trade) and with their prices fixed, the
    # system is square with full structural rank
    import casadi as ca
    sp = fn.jac_sparsity(0, 0)
    er = set(np.nonzero(np.diff(np.asarray(sp.T.colind())) == 0)[0].tolist())
    keep = [i for i in range(sp.size1()) if i not in er]
    assert ca.sprank(sp.sub(keep, keep, False)[0]) == len(keep)


def _scale(mm, lay, name):
    """An equation block's scale: the dairy blocks' base raw milk, FeedBal_'s energy fed at calibration, the land
    markets' calibration land; 1 for the quotas (and the young animals, absent here)."""
    if name == "dairyE":
        dp = mm._dairy_params()
        return np.repeat([max(float(dp["ms"][m]["Q0"][dp["ms"][m]["iM"]]), 1.0) for m in lay["ms"]], 3)
    if name == "dairyW":
        wp = mm._dairy_world_params()
        return np.repeat([max(float(wp[r]["Q0"][wp[r]["iM"]]), 1.0) for r in lay["wl"]], 3)
    if name == "feed":
        from capri_mod.market.feed_ad import fedebal_arrays
        nfp = mm._noneu_feed_params()
        return np.array([max(abs(fedebal_arrays(nfp["rms"][s], lay["cols"], [])["e_const"]), 1.0) for s in lay["rms"]])
    if name == "land":
        LP = mm._noneu_land_params()
        return np.concatenate([np.maximum(LP[s]["L0"], 1.0) for s in lay["lrms"]])
    return 1.0


@pytest.mark.slow
def test_the_lifted_market_system_has_the_same_solution(solved_base):
    """The lifted form (the Armington ratios, supply and use as unknowns with their defining equations, CAPRI's
    form): at the default solve's equilibrium its definitions hold exactly and its other equations equal the
    substituted form's; its Jacobian is sparse."""
    from capri_mod.market.market_system_ad import market_system, market_x0
    mm, exo = solved_base
    mm._bilateral_eval(mm.sv.bilat_last_r.copy(), exo, None)
    fs, ls, _, _ = market_system(mm, exo)
    fl, ll, _, _ = market_system(mm, exo, lifted=True)
    xs, xl = market_x0(mm, ls), market_x0(mm, ll)
    assert np.array_equal(xl[:ls["n_x"]], xs)
    Fs = np.asarray(fs(xs)[0], float).ravel()
    Fl = np.asarray(fl(xl)[0], float).ravel()
    # the same up to rounding of the quantities they are differences of (balances of 1e4 kt: 1e-12 is a few ulps)
    assert float(np.max(np.abs(Fl[:ls["n_F"]] - Fs))) <= 1e-8
    assert float(np.max(np.abs(Fl[ls["n_F"]:]))) <= 1e-9
    sp = fl.jac_sparsity(0, 0)
    assert sp.nnz() < 0.01 * ll["n_x"] * ll["n_F"]


@pytest.mark.slow
def test_the_supply_system_equals_supply_response_at_its_block_solutions(solved_base):
    from capri_mod.market.supply_system_ad import supply_inputs, supply_system
    mm, exo = solved_base
    r0 = mm.sv.bilat_last_r.copy()
    rng = np.random.default_rng(14112026)
    byp = {(reg, p) for reg in mm.EU for p in mm.eu_feed_byproduct_output(reg)}
    base = None
    for trial in range(3):
        r = r0 * (rng.uniform(0.85, 1.2, r0.shape) if trial else 1.0)
        S1, _, PAr, _, _ = mm._bilateral_eval(r, exo, None)
        f, lay = supply_system(mm, exo)
        PA = PAr.reindex(index=lay["regions"], columns=lay["cols"]).fillna(1.0).to_numpy(dtype=float)
        out = f(*supply_inputs(mm, lay, PA))
        S = np.asarray(out[0], float)
        ref = S1.reindex(index=lay["regions"], columns=lay["cols"]).to_numpy(dtype=float)
        d = np.abs(S - ref) / np.maximum(np.abs(ref), 1.0)
        for i, rg in enumerate(lay["regions"]):
            for j, c in enumerate(lay["cols"]):
                if (rg, c) in byp:
                    d[i, j] = 0.0
        assert float(d.max()) <= 1e-12, (trial, float(d.max()))
        for k in (2, 3):
            e = np.asarray(out[k], float).ravel()
            assert e.size and float(np.abs(e).max()) <= 1e-8, (trial, k, float(np.abs(e).max()))
        if base is None:
            base = ref
        else:
            # the random prices move the supply (the check is not between two constants)
            assert float((np.abs(ref - base) / np.maximum(np.abs(base), 1.0)).max()) > 0.05


@pytest.mark.slow
@pytest.mark.parametrize("method,linsol", [("chain", "pardiso"), ("ipopt", "mumps")])
def test_the_market_solved_by_the_chain_is_the_fixed_points_equilibrium(solved_base, capsys, method, linsol):
    """Market.solver = "chain" / "ipopt" (capri_mod/market/market_chain.py): from the solved base, a supply change
    (+5% soft wheat everywhere) solved by the chain and by the fixed point gives the same prices; the fixed point confirms
    the chain's solution in at most two evaluations."""
    import pickle
    from capri_mod.settings import override
    if linsol == "pardiso":
        pytest.importorskip("pypardiso")
    mm, exo = solved_base
    exo2 = exo.copy()
    exo2["SWHE"] = exo2["SWHE"] * 1.05
    m_fp, m_chain = pickle.loads(pickle.dumps(mm)), pickle.loads(pickle.dumps(mm))
    e_fp = m_fp.solve(exogenous_supply=exo2)
    with override({"market.solver": method, "market.newton_linear_solver": linsol}):
        e_chain = m_chain.solve(exogenous_supply=exo2)
    out = capsys.readouterr().out
    assert "market solve by the chain:" in out and ("converged" in out or "Solve_Succeeded" in out), out[-500:]
    assert e_fp.converged and e_chain.converged
    assert e_chain.iterations <= 2 < e_fp.iterations, (e_chain.iterations, e_fp.iterations)
    a, b = m_fp.sv.bilat_last_r, m_chain.sv.bilat_last_r.reindex(index=m_fp.sv.bilat_last_r.index,
                                                              columns=m_fp.sv.bilat_last_r.columns)
    cols = list(m_fp.par.bilat)
    d = (np.abs(a[cols] - b[cols]) / np.maximum(np.abs(a[cols]), 1e-3)).to_numpy().max()
    assert d <= 1e-5, d
    r0 = mm.sv.bilat_last_r.reindex(index=a.index, columns=a.columns)
    assert float((np.abs(a[cols] - r0[cols]) / np.maximum(np.abs(r0[cols]), 1e-3)).to_numpy().max()) > 1e-3


def test_prod_fudge_is_capris_ncpcm_form():
    """supply_system_ad.prod_fudge: mode 0 the model's floor, 2 the row, 1 CAPRI's ProdFudge_ (market_model.gms
    l. 2420-2431) as GAMS defines ncpCM(x, y, Z) = x - Z ln(1 + exp((x - y) / Z)), evaluated here directly where exp
    does not overflow, at bases below, inside and above the clip of Z (1e-11 to 1000)."""
    import casadi as ca
    from capri_mod.market.supply_system_ad import prod_fudge
    q, m = ca.SX.sym("q"), ca.SX.sym("m")
    for base in (1e-14, 0.37, 52.0, 5.0e4):
        f = ca.Function("f", [q, m], [prod_fudge(q, m, base)])
        z = 1e-2 * min(1000.0, max(1e-11, base))
        for v in np.concatenate([np.linspace(-30 * z, 30 * z, 61), [-1e3, -1.0, 0.0, 1.0, 1e3]]):
            assert float(f(v, 0)) == max(v, 0.0)
            assert float(f(v, 2)) == v
            if abs(v) / z < 600:
                x = -v
                ncpcm = x - z * np.log1p(np.exp((x - 0.0) / z))
                ref = -ncpcm + 1e-11
                assert abs(float(f(v, 1)) - ref) <= 1e-12 * max(1.0, abs(ref)), (base, v)
        # smooth: the derivative of the fudge goes from 0 to 1 through 1/2 at 0
        dg = ca.Function("dg", [q], [ca.jacobian(prod_fudge(q, 1.0, base), q)])
        assert abs(float(dg(0.0)) - 0.5) < 1e-12
        assert float(dg(-50 * z)) < 1e-20 and abs(float(dg(50 * z)) - 1.0) < 1e-20


@pytest.mark.slow
def test_the_lifted_processing_and_feed_reproduce_the_default_form(solved_base):
    """CAPRI's v_procQuant and v_feedQuant as unknowns of the lifted system (market.bounds "capri", MARKET_BOUNDS_PLAN
    step 4): with every mode at 0 (the model's form) their defining rows hold at the start and every other equation
    equals the system without them; at the calibration point no fudge row is needed (CAPRI's chk_market_data holds no
    ProcFudge_ or FeedFudge_): ProcNQ_'s and FeedNQ_'s rows equal the model's values there to rounding, within CAPRI's
    start bounds, and CAPRI's fudge (mode 1) moves them by less than its smoothing term."""
    import casadi as ca
    from capri_mod.market.market_bounds import capri_start_bounds
    from capri_mod.market.market_system_ad import market_system, market_x0
    mm, exo = solved_base
    mm._bilateral_eval(mm.sv.bilat_last_r.copy(), exo, None)
    f0, l0, _, _ = market_system(mm, exo, lifted=True, fudge=True)
    f1, l1, _, _ = market_system(mm, exo, lifted=True, fudge=True, lift_use=True)
    lc = l1["lift_cells"]
    kinds = {c[0] for c in lc}
    assert {"proc", "feed"} <= kinds, kinds
    x0, x1 = market_x0(mm, l0), market_x0(mm, l1)
    nL = len(lc)
    assert np.array_equal(x1[:l0["n_x"]], x0)
    nfm = len(l0["fudge_cells"])
    F0 = np.asarray(f0(x0, np.zeros(nfm))[0], float).ravel()
    F1 = np.asarray(f1(x1, np.zeros(nfm + nL))[0], float).ravel()
    assert l1["eqs"][-1] == ("Ldef", nL)
    assert float(np.max(np.abs(F1[-nL:]))) <= 1e-9
    assert float(np.max(np.abs(F1[:l0["n_F"]] - F0))) <= 1e-8
    # at the start the cells are inside CAPRI's start bounds
    lb, ub = capri_start_bounds(mm, l1, x1)
    L = x1[-nL:]
    assert np.all(L >= lb[-nL:] - 1e-12) and np.all(L <= ub[-nL:] + 1e-12)
    # CAPRI's fudge on the row (mode 1): at the calibration point within its smoothing term of the row itself
    b = np.array([c[3] for c in lc])
    F1f = np.asarray(f1(x1, np.concatenate([np.zeros(nfm), np.ones(nL)]))[0], float).ravel()[-nL:]
    z = 1e-2 * np.minimum(1000.0, np.maximum(1e-11, b))
    assert np.all(np.abs(F1f) <= z * np.log(2.0) + 1e-8)
    del ca


@pytest.mark.slow
def test_the_semismooth_newton_solves_the_bounded_market_from_the_fixed_point(solved_base):
    """G3.4 point 2 (market_chain "ssn", _mcp_system): under CAPRI's bounds (market.bounds = "capri"), started at the
    fixed point's equilibrium of +5% soft wheat, the semismooth Newton on the MCP form converges and keeps that
    equilibrium's prices within 1e-6; at its solution the complementarity holds: the equations within 1e-7 inside
    the bounds, the oriented equation >= 0 at a lower bound and <= 0 at an upper one."""
    import pickle
    from capri_mod.market import market_chain as MC
    from capri_mod.settings import override
    pytest.importorskip("pypardiso")
    mm, exo = solved_base
    exo2 = exo.copy()
    exo2["SWHE"] = exo2["SWHE"] * 1.05
    with override({"market.bounds": "capri"}):
        m = pickle.loads(pickle.dumps(mm))
        assert m.solve(exogenous_supply=exo2).converged
        ctx = MC.build(m, m.sv.bilat_last_r.copy(), exo2, None)
        xs, ok, msg = MC.solve(ctx, "ssn")
        assert ok, msg
        lb, ub = MC._bounds(ctx)
        nr = sum(len(sc.regions) for sc in m.par.bilat.values())
        x0 = ctx["x0"]
        assert float(np.max(np.abs(xs[:nr] - x0[:nr]) / np.maximum(np.abs(x0[:nr]), 1e-3))) <= 1e-6
        _, _, sgn = MC._mcp_system(ctx, lb, ub)
        Fo = np.asarray(ctx["fF"](xs, ctx["slope"]), float).ravel() / ctx["sc"] * sgn
        free = lb < ub
        tol = 1e-8 * np.maximum(1.0, np.abs(xs))
        atl, atu = free & (xs - lb <= tol), free & (ub - xs <= tol)
        inside = free & ~atl & ~atu
        assert float(np.abs(Fo[inside]).max()) <= 1e-7
        assert (Fo[atl] >= -1e-8).all() and (Fo[atu] <= 1e-8).all()


@pytest.mark.slow
def test_the_market_under_capris_bounds_is_the_fixed_point_then_the_semismooth_newton(solved_base, capsys):
    """market.bounds = "capri" (the project lead's decision of 16 November 2026): MarketModule.solve runs the fixed
    point, then the semismooth Newton from its equilibrium (bilateral_solve, market_chain "ssn"), skipped where the
    equilibrium lies within CAPRI's start bounds (market_chain.within_capri_start_bounds); on +5% soft wheat it
    converges and its prices are the fixed point's within 1e-6 (no bound but the quotas' saturated sigmas binds)."""
    import pickle
    from capri_mod.settings import override
    pytest.importorskip("pypardiso")
    mm, exo = solved_base
    exo2 = exo.copy()
    exo2["SWHE"] = exo2["SWHE"] * 1.05
    m_fp, m_b = pickle.loads(pickle.dumps(mm)), pickle.loads(pickle.dumps(mm))
    assert m_fp.solve(exogenous_supply=exo2).converged
    with override({"market.bounds": "capri"}):
        e_b = m_b.solve(exogenous_supply=exo2)
    out = capsys.readouterr().out
    assert e_b.converged and ("semismooth Newton" in out or "within CAPRI's start bounds" in out), out[-500:]
    a, b = m_fp.sv.bilat_last_r, m_b.sv.bilat_last_r.reindex(index=m_fp.sv.bilat_last_r.index,
                                                            columns=m_fp.sv.bilat_last_r.columns)
    cols = list(m_fp.par.bilat)
    assert (np.abs(a[cols] - b[cols]) / np.maximum(np.abs(a[cols]), 1e-3)).to_numpy().max() <= 1e-6


@pytest.mark.slow
def test_capris_widening_after_the_bounded_solve_under_a_pork_cut(solved_base):
    """CAPRI's second market solve (arm/simu_market.gms l. 95-145, market_chain.simu_market_widen): under -90% pork the
    semismooth Newton from the fixed point's equilibrium leaves processing cells at CAPRI's start lower bound with their
    equation unmet (CAPRI's infeasible solve); their bounds are widened by widen_bounds.gms's rule for v_procQuant
    (l. 125-129: L - 10 x max(10, Proc, |L|), applied here by hand), ProcFudge_ switched on where the lower bound is then
    at or below 0, and the second solve leaves no unknown at a bound with its equation unmet (SumInfes <= 1e-5), the
    complementarity holding at the widened bounds."""
    import pickle
    from capri_mod.market import market_chain as MC
    from capri_mod.settings import override
    pytest.importorskip("pypardiso")
    mm, exo = solved_base
    exo2 = exo.copy()
    exo2["PORK"] = exo2["PORK"] * 0.10
    m = pickle.loads(pickle.dumps(mm))
    assert m.solve(exogenous_supply=exo2).converged

    def unmet(ctx, x, lb, ub, sgn, tol):
        F = np.asarray(ctx["fF"](x, ctx["slope"]), float).ravel()
        Fo = F / ctx["sc"] * sgn
        free = lb < ub
        bt = 1e-8 * np.maximum(1.0, np.abs(x))
        atl = free & np.isfinite(lb) & (x - lb <= bt)
        atu = free & np.isfinite(ub) & (ub - x <= bt)
        return (atl & (Fo > tol)) | (atu & (Fo < -tol)), F, Fo, atl, atu, free

    with override({"market.bounds": "capri", "market.widen_bounds_tries": 0}):
        ctx = MC.build(m, m.sv.bilat_last_r.copy(), exo2, None)
        x1, ok, msg = MC.solve(ctx, "ssn")
        assert ok, msg
        lb, ub = (v.copy() for v in MC._bounds(ctx))
        x0 = ctx["x0"]
        lb[ctx["empty"]], ub[ctx["empty"]] = x0[ctx["empty"]], x0[ctx["empty"]]
        _, _, sgn = MC._mcp_system(ctx, lb, ub)
        tol = 1e-10
        bad, F1, _, _, _, _ = unmet(ctx, x1, lb, ub, sgn, tol)
    assert bad.sum() > 0 and float(np.abs(F1[bad]).sum()) > 1e-5
    o, offL = 0, None
    for nm, n in ctx["lay"]["x"]:
        if nm == "L":
            offL = o
        o += n
    lc = ctx["lay"]["lift_cells"]
    bad_L = [k for k in np.nonzero(bad)[0] if offL is not None and offL <= k < offL + len(lc)]
    assert bad_L and all(lc[k - offL][0] == "proc" for k in bad_L)
    with override({"market.bounds": "capri", "market.widen_bounds_tries": 1}):
        x2, ok2, msg2 = MC.simu_market_widen(ctx, x1.copy(), lb.copy(), ub.copy(), sgn, tol,
                                             200, ctx["slope"])
        assert ok2 and "bounds widened" in msg2, msg2
        lb2, ub2 = MC._bounds(ctx)
        for k in bad_L:
            b = float(lc[k - offL][3])
            assert lb2[k] == pytest.approx(x1[k] - 10.0 * max(10.0, b, abs(x1[k])), rel=1e-12)
            assert lb2[k] <= 0 and ctx["fmv"][len(ctx["lay"]["fudge_cells"]) + (k - offL)] == 1.0
        _, _, sgn2 = MC._mcp_system(ctx, lb2, ub2)
        bad2, F2, Fo2, atl, atu, free = unmet(ctx, x2, lb2, ub2, sgn2, tol)
    assert float(np.abs(F2[bad2]).sum()) <= 1e-5
    inside = free & ~atl & ~atu
    assert float(np.abs(Fo2[inside]).max()) <= 1e-7
