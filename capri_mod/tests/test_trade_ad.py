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
    for c, sc in list(market._bilat.items())[:12]:
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
