"""G3.2a: the import prices of every bilateral commodity in CasADi (capri_mod/market/import_prices_ad.py) equal
BilateralCommodity.import_prices with the quotas' sigmas given (bilateral and global quotas, entry prices, flexible
levies), at the base and at random prices and sigmas: the 2017 market of a solved baseline (quotas; the 2017 market
year has no entry prices nor levies) and the 2030 market calibrated at CAPRI's 2030 data (the border measures too)."""
import numpy as np
import pytest


@pytest.fixture(scope="module")
def market_2030():
    """The market of 2030 (data["market_year"]), its bilateral systems calibrated at CAPRI's 2030 market data."""
    from capri_mod.data.loaders import load_all_data
    from capri_mod.market.market_module import MarketModule
    from pathlib import Path
    d = load_all_data(str(Path(__file__).resolve().parents[2] / "capri_data"))
    d["market_year"] = 2030
    mm = MarketModule(d)
    mm._bilateral_calibrate()
    mm._apply_trq_volumes(mm.par.bilat)
    return mm


@pytest.mark.slow
def test_import_prices_in_casadi_equal_the_numeric_ones_2017(solved_market):
    _check(solved_market, need_border=False)


@pytest.mark.slow
def test_import_prices_in_casadi_equal_the_numeric_ones_2030(market_2030):
    _check(market_2030, need_border=True)


def _check(market, need_border):
    from capri_mod.market.import_prices_ad import cells, import_price_function
    rng = np.random.default_rng(14112026)
    checked = {"quotas": 0, "globals": 0, "entry": 0, "levy": 0}
    worst = 0.0
    for c, sc in market.par.bilat.items():
        n = len(sc.regions)
        nb, ng = len(sc.trq_quotas or ()), len(sc.trq_globals or ())
        f = import_price_function(sc)
        cl = cells(sc)
        if not cl:
            continue
        ii, jj = np.array([i for i, _ in cl]), np.array([j for _, j in cl])
        checked["quotas"] += nb
        checked["globals"] += ng
        if sc.border:
            checked["entry"] += int((np.asarray(sc.border["kind"]) == 1).sum())
            checked["levy"] += int((np.asarray(sc.border["kind"]) == 2).sum())
        trials = [(np.ones(n), sc.trq_sigma, sc.trq_sigmaW)]
        for _ in range(4):
            trials.append((rng.uniform(0.7, 1.4, n), rng.uniform(0.0, 1.0, nb) if nb else None,
                           rng.uniform(0.0, 1.0, ng) if ng else None))
        for r, sB, sW in trials:
            sB_ = np.zeros(0) if sB is None else np.asarray(sB, float)
            sW_ = np.zeros(0) if sW is None else np.asarray(sW, float)
            sig = (sB_, sW_) if (nb or ng) else None
            p_num = sc.import_prices(r, sig=sig)[ii, jj]
            p_ad = np.asarray(f(r, sB_, sW_)).ravel()
            rel = np.abs(p_ad - p_num) / np.maximum(np.abs(p_num), 1.0)
            worst = max(worst, float(rel.max()))
            assert rel.max() < 1e-12, (c, float(rel.max()), cl[int(rel.argmax())])
    print("checked", checked, "worst relative difference", worst)
    assert checked["quotas"] > 0 and checked["globals"] > 0
    if need_border:
        assert checked["entry"] > 0 and checked["levy"] > 0


@pytest.mark.slow
def test_trade_system_in_casadi_equals_the_numeric_one(market_2030):
    """G3.2b: trade_system_function's balances, quota equations and flows equal BilateralCommodity.residual, flows and
    trq_arguments at random prices, sigmas, supply and use (the 2030 market: every policy regime)."""
    from capri_mod.market.import_prices_ad import cells
    from capri_mod.market.trade_system_ad import active_quotas, trade_system_function
    rng = np.random.default_rng(1411)
    worst = {"bal": 0.0, "trq": 0.0, "X": 0.0}
    for c, sc in market_2030.par.bilat.items():
        n = len(sc.regions)
        nb, ng = len(sc.trq_quotas or ()), len(sc.trq_globals or ())
        f = trade_system_function(sc)
        cl = cells(sc)
        ii, jj = (np.array([i for i, _ in cl], int), np.array([j for _, j in cl], int)) if cl else (None, None)
        for t in range(3):
            r = np.ones(n) if t == 0 else rng.uniform(0.7, 1.4, n)
            S = sc.S0 * (1.0 if t == 0 else rng.uniform(0.8, 1.2, n))
            D = sc.D0 * (1.0 if t == 0 else rng.uniform(0.8, 1.2, n))
            sB = rng.uniform(0, 1, nb) if nb else np.zeros(0)
            sW = rng.uniform(0, 1, ng) if ng else np.zeros(0)
            sig = (sB, sW) if (nb or ng) else None
            p = sc.import_prices(r, sig=sig)
            X, _ = sc.flows(D, r, p)
            bal_num = sc.residual(S, D, r, p)
            out = f(r, sB, sW, S, D)
            bal = np.asarray(out[0]).ravel()
            sc_ = np.maximum(np.abs(sc.S0) + np.abs(sc.D0), 1.0)
            worst["bal"] = max(worst["bal"], float(np.max(np.abs(bal - bal_num) / sc_)))
            if cl:
                xa = np.asarray(out[2]).ravel()
                worst["X"] = max(worst["X"], float(np.max(np.abs(xa - X[ii, jj]) / np.maximum(np.abs(X[ii, jj]), 1.0))))
            bil, glo = active_quotas(sc)
            if bil or glo:
                s_now = np.concatenate([sB[bil], sW[glo]])
                trq_num = s_now - 1.0 / (1.0 + np.exp(-sc.trq_arguments(X, (bil, glo))))
                worst["trq"] = max(worst["trq"], float(np.max(np.abs(np.asarray(out[1]).ravel() - trq_num))))
    print("worst", worst)
    assert worst["bal"] < 1e-11 and worst["X"] < 1e-11 and worst["trq"] < 1e-11, worst
