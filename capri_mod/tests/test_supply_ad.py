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
