"""Step G1: the bilateral trade system in CasADi equals the numeric one, and its Jacobian equals finite differences
(capri_mod/market/trade_ad.py against capri_mod/market/bilateral.py)."""
import numpy as np
import pytest


@pytest.fixture(scope="module")
def market():
    from capri_mod.model import CAPRIModel
    from capri_mod.settings import override
    with override({"market.market_supply_nq": False}):
        m = CAPRIModel(data_dir="capri_data", verbose=False)
        m.run(scenario="BASELINE", regions=["DE110000", "FR100000"], max_outer_iter=1)
    return m.market_module


def test_casadi_trade_residual_and_jacobian_match(market):
    from capri_mod.market.trade_ad import trade_function, import_price_matrices
    rng = np.random.default_rng(1)
    checked = 0
    for c, sc in list(market.par.bilat.items())[:12]:
        act = np.where(sc.S0 > 1e-6)[0]
        if len(act) == 0:
            continue
        n = len(sc.regions)
        rk = np.exp(rng.normal(0, 0.05, n))
        _, _, PAk, _ = sc.prices(rk, sc.import_prices(rk))
        Sk = sc.S0 * np.exp(rng.normal(0, 0.05, n)); Dk = sc.D0 * np.exp(rng.normal(0, 0.05, n))
        es = rng.uniform(0.0, 0.8, n); ed = rng.uniform(-0.8, 0.0, n)
        scale = np.maximum(sc.S0[act] + sc.D0[act], 1.0)

        def G(z):
            r = rk.copy(); r[act] = np.exp(z)
            p = sc.import_prices(r); pre = sc.prices(r, p)
            S = Sk * (r / rk) ** es; D = Dk * (pre[2] / PAk) ** ed
            return sc.residual(S, D, r, p, pre=pre)[act] / scale
        A, B = import_price_matrices(sc)
        fn = trade_function(sc, act)
        z = np.log(rk[act]) + rng.normal(0, 0.03, len(act))
        g, J = fn(z, A, B, Sk, Dk, rk, PAk, es, ed, scale)
        g, J = np.asarray(g).ravel(), np.asarray(J)
        assert np.allclose(g, G(z), rtol=1e-9, atol=1e-11), c
        h = 1e-7
        Jfd = np.column_stack([(G(z + h * e) - G(z - h * e)) / (2 * h) for e in np.eye(len(z))])
        assert np.allclose(J, Jfd, rtol=1e-5, atol=1e-7), c
        checked += 1
    assert checked >= 5


def test_casadi_trade_with_trq_matches(market):
    """Step G2a: the trade system with the EU's tariff-rate quotas inside it (trade_trq_function) equals the numeric
    one (import_prices with the offsets, flows, CAPRI's sigmoid as BilateralCommodity._sig), Jacobian included."""
    from capri_mod.market.trade_ad import trade_trq_function, import_price_matrices, trq_exporters, trq_constants
    rng = np.random.default_rng(2)
    checked = 0
    for c, sc in market.par.bilat.items():
        quota = trq_exporters(sc)
        act = np.where(sc.S0 > 1e-6)[0]
        if len(quota) == 0 or len(act) == 0:
            continue
        n = len(sc.regions)
        rows = sc._rows()
        off0 = sc.trq_offset.copy()
        rk = np.exp(rng.normal(0, 0.05, n))
        _, _, PAk, _ = sc.prices(rk, sc.import_prices(rk))
        Sk = sc.S0 * np.exp(rng.normal(0, 0.05, n)); Dk = sc.D0 * np.exp(rng.normal(0, 0.05, n))
        es = rng.uniform(0.0, 0.8, n); ed = rng.uniform(-0.8, 0.0, n)
        scale = np.maximum(sc.S0[act] + sc.D0[act], 1.0)
        gap, k, s0 = trq_constants(sc, quota)

        def G(x):
            z, o = x[:len(act)], x[len(act):]
            r = rk.copy(); r[act] = np.exp(z)
            sc.trq_offset = off0.copy(); sc.trq_offset[quota] = o
            try:
                p = sc.import_prices(r); pre = sc.prices(r, p)
                S = Sk * (r / rk) ** es; D = Dk * (pre[2] / PAk) ** ed
                X, _ = sc.flows(D, r, p, pre=pre)
                mk = (S - X.sum(axis=0))[act] / scale
                tq = (o - gap * (sc._sig(k * X[rows][:, quota].sum(axis=0)) - s0)) / gap
            finally:
                sc.trq_offset = off0
            return np.concatenate([mk, tq])
        A, B0 = import_price_matrices(sc, offsets=False)
        fn = trade_trq_function(sc, act)
        x = np.concatenate([np.log(rk[act]) + rng.normal(0, 0.03, len(act)), off0[quota] + rng.normal(0, 1.0, len(quota))])
        g, J = fn(x[:len(act)], x[len(act):], A, B0, Sk, Dk, rk, PAk, es, ed, scale)
        g, J = np.asarray(g).ravel(), np.asarray(J)
        assert np.allclose(g, G(x), rtol=1e-9, atol=1e-11), c
        h = 1e-7
        Jfd = np.column_stack([(G(x + h * e) - G(x - h * e)) / (2 * h) for e in np.eye(len(x))])
        assert np.allclose(J, Jfd, rtol=1e-4, atol=1e-6), c
        checked += 1
    assert checked >= 1
