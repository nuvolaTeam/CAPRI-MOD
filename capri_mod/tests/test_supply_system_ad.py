"""G3.2c/e: the market's supply side as one CasADi function with its blocks' equations (capri_mod/market/
supply_system_ad.py) equals MarketModule.supply_response, and the blocks' residuals vanish, at the evaluation's own
block solutions: at a solved market and at random prices around it (the market of the model's data at CAPRI's base
supply rows: crushing, the dairy blocks, the non-EU ProdNQ_ rows with FEDE and the land rents, biofuels). The young
animals, the member states' raw milk response and Norway's supply models need a supply run's state: checked at captured
solves of a Farm-to-Fork run (tools/check/g3_supply_system.py, G3_SYSTEM.md)."""
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
    """G3.2e (capri_mod/market/market_system_ad.py): square, structurally nonsingular once the empty balances are out,
    and at the default solve's equilibrium every block's equations hold within that solve's tolerances. The balances within 1e-6 of S0 + D0, not market.tol (1e-7): the
    solve meets its test at its own last evaluation (9.0e-8 here), whose non-EU land and FEDE blocks read the previous
    evaluation's raw milk prices; evaluated again at the same prices the residual is 1.3e-7, and it drifts on (1.4e-7)
    as that lag is worked off (G3_SYSTEM.md, G3.2e)."""
    from capri_mod.market.market_system_ad import market_system, market_x0
    mm, exo = solved_base
    mm._bilateral_eval(mm.sv.bilat_last_r.copy(), exo, None)
    fn, lay, _, _ = market_system(mm, exo)
    assert lay["n_x"] == lay["n_F"] > 2000
    F, pooled, _, _ = (np.asarray(v, float).ravel() for v in fn(market_x0(mm, lay)))
    o = 0
    for name, n in lay["eqs"]:
        v = F[o:o + n]
        if name == "bal":
            sc = np.concatenate([np.maximum(np.asarray(s.S0 + s.D0, float), 1.0) for s in mm.par.bilat.values()])
            assert float(np.max(np.abs(v) / sc)) <= 1e-6, name
        elif n:
            assert float(np.max(np.abs(v) / _scale(mm, lay, name))) <= 1e-6, name
        o += n
    assert float(np.max(np.abs(pooled))) <= 1e-6
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
@pytest.mark.parametrize("method,linsol", [("g3_newton", "pardiso"), ("g3_ipopt", "mumps")])
def test_the_market_solved_by_g3_is_the_fixed_points_equilibrium(solved_base, capsys, method, linsol):
    """market.solver = "g3_newton" / "g3_ipopt" (capri_mod/market/market_g3.py): from the solved base, a supply change
    (+5% soft wheat everywhere) solved by G3 and by the fixed point gives the same prices; the fixed point confirms
    G3's solution in at most two evaluations."""
    import pickle
    from capri_mod.settings import override
    if linsol == "pardiso":
        pytest.importorskip("pypardiso")
    mm, exo = solved_base
    exo2 = exo.copy()
    exo2["SWHE"] = exo2["SWHE"] * 1.05
    m_fp, m_g3 = pickle.loads(pickle.dumps(mm)), pickle.loads(pickle.dumps(mm))
    e_fp = m_fp.solve(exogenous_supply=exo2)
    with override({"market.solver": method, "market.g3_linear_solver": linsol}):
        e_g3 = m_g3.solve(exogenous_supply=exo2)
    out = capsys.readouterr().out
    assert "market solve by G3:" in out and ("converged" in out or "Solve_Succeeded" in out), out[-500:]
    assert e_fp.converged and e_g3.converged
    assert e_g3.iterations <= 2 < e_fp.iterations, (e_g3.iterations, e_fp.iterations)
    a, b = m_fp.sv.bilat_last_r, m_g3.sv.bilat_last_r.reindex(index=m_fp.sv.bilat_last_r.index,
                                                              columns=m_fp.sv.bilat_last_r.columns)
    cols = list(m_fp.par.bilat)
    d = (np.abs(a[cols] - b[cols]) / np.maximum(np.abs(a[cols]), 1e-3)).to_numpy().max()
    assert d <= 1e-5, d
    r0 = mm.sv.bilat_last_r.reindex(index=a.index, columns=a.columns)
    assert float((np.abs(a[cols] - r0[cols]) / np.maximum(np.abs(r0[cols]), 1e-3)).to_numpy().max()) > 1e-3
