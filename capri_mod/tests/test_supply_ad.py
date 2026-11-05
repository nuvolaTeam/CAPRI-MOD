"""Step G2b, first part: CAPRI's market supply functions ProdNQ_ in CasADi (capri_mod/market/supply_ad.py) equal the
loops supply.py had until 4 November 2026 (written out here as the reference), and their Jacobian equals finite
differences."""
import numpy as np
import pandas as pd
import pytest


def _noneu_loop(mm, supply, cols, ratio_of, milk_ratio_of, sup_cols, fede, lshift_of):
    """SupplyMixin._noneu_market_supply_nq before the move."""
    P = mm._noneu_nq_params()
    ci = {c: j for j, c in enumerate(cols)}
    for reg, d in P.items():
        if reg not in supply.index:
            continue
        r_ = ratio_of(reg)
        mr = float(milk_ratio_of(reg))
        skip = sup_cols.get(reg, set())
        fd = d.get("fede") or {}
        lshift = lshift_of(reg)
        for x, terms in d["rows"].items():
            if x not in ci or x in skip or x not in supply.columns:
                continue
            q0 = float(mm.par.base_production.at[reg, x]) if x in mm.par.base_production.columns else 0.0
            if q0 <= 0:
                continue
            dq = 0.0
            for y, h in terms.items():
                if y == "MILK":
                    dq += h * (mr - 1.0)
                elif y in ci:
                    dq += h * (float(r_[ci[y]]) - 1.0)
            for rms, fx in fd.items():
                if x in fx:
                    dq += fx[x] * (float(fede.get(rms, 1.0)) - 1.0)
            dq += lshift.get(x, 0.0)
            supply.at[reg, x] = max(q0 + dq, 0.0)


def _eu_loop(mm, supply, cols, ratio_of):
    """SupplyMixin._eu_market_supply_nq before the move."""
    P = mm._eu_market_supply_nq_params()
    ci = {c: j for j, c in enumerate(cols)}
    for rg, terms in P.items():
        if rg not in supply.index:
            continue
        r_ = ratio_of(rg)
        for x in mm.EU_MARKET_SUPPLY:
            if x not in ci or x not in supply.columns:
                continue
            q0 = float(mm.par.base_production.at[rg, x]) if x in mm.par.base_production.columns else 0.0
            if q0 <= 0:
                continue
            dq = sum(h * (float(r_[ci[y]]) - 1.0) for (x_, y), h in terms.items() if x_ == x and y in ci)
            supply.at[rg, x] = max(q0 + dq, 0.0)


@pytest.fixture(scope="module")
def market():
    from pathlib import Path
    from capri_mod.data.loaders import load_all_data
    from capri_mod.market.market_module import MarketModule
    return MarketModule(load_all_data(Path(__file__).resolve().parents[2] / "capri_data"))


def _ratios(mm, cols, seed):
    rng = np.random.default_rng(seed)
    return {r: 1.0 + 0.3 * rng.standard_normal(len(cols)) for r in mm.regions}


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_prodnq_equals_the_loops(market, seed):
    mm = market
    cols = [c for c in mm.commodities if c in mm.par.base_production.columns]
    R = _ratios(mm, cols, seed)
    rng = np.random.default_rng(100 + seed)
    milk = {r: 1.0 + 0.2 * rng.standard_normal() for r in mm.regions}
    fede = {s: 1.0 + 0.2 * rng.standard_normal() for d in mm._noneu_nq_params().values() for s in (d.get("fede") or {})}
    mm.ev.fede_now = fede
    mm.ev.land_now = None                                  # no land shift: the land block is lifted with its own stage
    mm._welf_noneu_nq = {}
    sup_cols = {r: set(mm.SUP_NONEU_MS) for r in mm.SUP}
    a, b = mm.par.base_production.copy(), mm.par.base_production.copy()
    _noneu_loop(mm, a, cols, R.__getitem__, milk.__getitem__, sup_cols, fede, lambda r: {})
    mm._noneu_market_supply_nq(b, cols, R.__getitem__, milk.__getitem__, sup_cols)
    _eu_loop(mm, a, cols, R.__getitem__)
    mm._eu_market_supply_nq(b, cols, R.__getitem__)
    x, y = a.to_numpy(float), b.to_numpy(float)
    assert (x != y).sum() < x.size                         # something was computed
    rel = np.abs(x - y) / np.maximum(np.abs(x), 1e-9)
    assert rel.max() < 1e-12, (rel.max(), np.unravel_index(rel.argmax(), rel.shape))


def test_prodnq_jacobian_equals_finite_differences(market):
    from capri_mod.market.supply_ad import build_rows, nq_rows_function
    import casadi as ca
    mm = market
    cols = [c for c in mm.commodities if c in mm.par.base_production.columns]
    reg, d = next((r, d) for r, d in mm._noneu_nq_params().items() if d["rows"])
    a = build_rows(d["rows"], cols, d.get("fede") or {})
    f = nq_rows_function("t", len(cols), a["H"], a["hm"], a["HF"])
    q0 = mm._nq_q0(reg, a["rows"]) + 1e3                    # away from the floor
    r0 = np.ones(len(cols)) * 1.05
    rs = ca.MX.sym("r", len(cols))
    dq = f(ca.DM(q0), rs, 1.0, np.ones(len(a["rms"])), np.zeros(len(a["rows"])))[1]
    J = np.asarray(ca.Function("j", [rs], [ca.jacobian(dq, rs)])(r0))
    eps = 1e-6
    for j in range(len(cols)):
        e = np.zeros(len(cols)); e[j] = eps
        fd = (np.asarray(f(q0, r0 + e, 1.0, np.ones(len(a["rms"])), np.zeros(len(a["rows"])))[1]).ravel()
              - np.asarray(f(q0, r0 - e, 1.0, np.ones(len(a["rms"])), np.zeros(len(a["rows"])))[1]).ravel()) / (2 * eps)
        assert np.allclose(J[:, j], fd, rtol=1e-6, atol=1e-6)


def test_hessian_supply_function_equals_the_numpy_form_and_its_jacobian():
    """ProdNQ_ with the measured Hessian (supply_ad.hess_rows_function): max(0, s0 + Hm dP + extra) as supply.py had it
    until 4 November 2026, and the Jacobian in dP equal to Hm where the floor does not bind."""
    import casadi as ca
    from capri_mod.market.supply_ad import hess_rows_function
    rng = np.random.default_rng(7)
    Hm = rng.standard_normal((9, 30)) * 50
    f = hess_rows_function("t", Hm)
    for _ in range(5):
        s0, dP, ex = rng.uniform(0, 500, 9), 0.2 * rng.standard_normal(30), rng.standard_normal(9)
        q, qr = (np.asarray(v).ravel() for v in f(s0, dP, ex))
        assert np.allclose(qr, s0 + Hm @ dP + ex, rtol=1e-13, atol=1e-10)
        assert np.array_equal(q, np.maximum(qr, 0.0))
    s0 = np.full(9, 1e4)
    d = ca.MX.sym("d", 30)
    J = np.asarray(ca.Function("j", [d], [ca.jacobian(f(s0, d, np.zeros(9))[0], d)])(np.zeros(30)))
    assert np.allclose(J, Hm, rtol=1e-14)


def test_anticipation_function_equals_the_numpy_form():
    """The own-price response before ProdNQ_ (supply_ad.anticipation_function): max(0, S (RR / SV)^E) as supply.py had
    it until 4 November 2026 (rr ** EV, the EU's and the supply-model regions' rows against the prices they saw)."""
    from capri_mod.market.supply_ad import anticipation_function
    rng = np.random.default_rng(3)
    S = rng.uniform(-1, 1000, (12, 40))
    RR, SV = rng.uniform(0.3, 2.0, (12, 40)), rng.uniform(0.3, 2.0, (12, 40))
    E = rng.uniform(-0.5, 2.0, (12, 40))
    E[rng.random((12, 40)) < 0.4] = 0.0
    q = np.asarray(anticipation_function(12, 40)(S, RR, SV, E))
    ref = np.maximum(S * (RR / SV) ** E, 0.0)
    assert np.allclose(q, ref, rtol=1e-14, atol=0.0)


def test_pooled_residual_function():
    """The pooled commodities' world balance (supply_ad.pooled_residual_function): sum S - sum D, as before."""
    from capri_mod.market.supply_ad import pooled_residual_function
    rng = np.random.default_rng(11)
    S, D = rng.uniform(0, 1e4, 45), rng.uniform(0, 1e4, 45)
    F = float(np.asarray(pooled_residual_function(45)(S, D)).ravel()[0])
    assert abs(F - (float(S.sum()) - float(D.sum()))) <= 1e-9 * float(S.sum())


def test_land_residual_function_equals_the_numpy_form(market):
    """The market land block outside the EU (supply_ad.land_residual_function): residual and Jacobian as
    SupplyMixin.noneu_land_solve had them in NumPy until 4 November 2026 (the analytic Jacobian
    H - avail sh (B - sh B)), at random rent changes."""
    from capri_mod.market.supply_ad import land_residual_function
    P = market._noneu_land_params()
    if not P:
        pytest.skip("market.noneu_land_market off")
    rng = np.random.default_rng(5)
    n = 0
    for rms, d in list(P.items())[:25]:
        fr = np.asarray(d["free"])
        if not len(fr):
            continue
        f = land_residual_function("t", d)
        for _ in range(3):
            dr = rng.standard_normal(len(fr)) * 50
            base = d["L0"] * (1 + 0.1 * rng.standard_normal(len(fr)))
            rent = d["rent0"].copy(); rent[fr] += dr
            z = d["alu"] + d["B"] @ rent
            e = np.exp(z - z.max()); sh = e / e.sum()
            Fr = base + d["H"] @ dr - (d["avail"] * sh)[fr]
            Jr = d["H"] - (d["avail"] * sh[:, None] * (d["B"] - sh @ d["B"]))[np.ix_(fr, fr)]
            Fv, J = f(dr, base)
            sc = np.maximum(np.abs(Fr), np.maximum(d["L0"], 1.0) * 1e-12)
            assert np.all(np.abs(np.asarray(Fv).ravel() - Fr) <= 1e-12 * np.maximum(np.abs(base), 1.0) + 1e-9), rms
            assert np.allclose(np.asarray(J).reshape(Jr.shape), Jr, rtol=1e-10, atol=1e-12 * float(np.abs(Jr).max())), rms
            n += 1
    assert n > 0


@pytest.mark.parametrize("singular", [False, True])
def test_young_animal_clearing_equals_the_former_code(singular):
    """yaniMarket_ (supply_ad.yani_function, step G2g) through SupplyMixin._yani_clear equals the NumPy code it had
    until 4 November 2026 (least squares on H_YY, prices clipped to the bounds), with a singular H_YY too."""
    from capri_mod.market import supply as msup
    cls = next(v for k, v in vars(msup).items() if isinstance(v, type) and hasattr(v, "_yani_clear"))
    stub = cls.__new__(cls)
    rng = np.random.default_rng(21 + singular)
    goods = ["calves", "heifers", "piglets", "lambs"]
    prods = ["BEEF", "PORK", "SGMT", "MILK", "COWS"]
    yi = ["YANI:" + g for g in goods]
    idx = prods + yi
    M = rng.standard_normal((len(idx), len(idx))) * 30
    H = pd.DataFrame(M + M.T, index=idx, columns=idx)
    if singular:
        H.loc[yi[3], yi] = H.loc[yi[2], yi].values             # two equal rows: H_YY singular
    st = {"goods": goods, "net": {g: float(rng.uniform(50, 150)) for g in goods},
          "ref": {g: float(rng.uniform(50, 150)) for g in goods},
          "seen": {g: float(rng.uniform(0.8, 1.2)) for g in goods}, "bounds": (0.5, 1.6)}
    stub.seen.yani_state = {"EU27": st}
    cols, xs = prods, ["BEEF", "PORK", "MILK"]
    for _ in range(4):
        dP = 0.1 * rng.standard_normal(len(cols))
        ey = rng.standard_normal(len(goods))
        out = np.asarray(stub._yani_clear("EU27", H, xs, cols, dP, extra_y=ey), float).ravel()
        H_YP = H.reindex(index=yi, columns=cols).to_numpy(float)
        H_YY = H.reindex(index=yi, columns=yi).to_numpy(float)
        H_PY = H.reindex(index=xs, columns=yi).to_numpy(float)
        n_now = np.array([st["net"][g] for g in goods]); ref = np.array([st["ref"][g] for g in goods])
        r_seen = np.array([st["seen"][g] for g in goods])
        dr = np.linalg.lstsq(H_YY, ref - n_now - H_YP @ dP - ey, rcond=None)[0]
        r = np.clip(r_seen + dr, 0.5, 1.6)
        got = np.array([stub.ev.yani_market_now["EU27"][g] for g in goods])
        assert np.allclose(got, r, rtol=1e-12, atol=1e-12), (got, r)
        assert np.allclose(out, H_PY @ (r - r_seen), rtol=1e-11, atol=1e-10)
