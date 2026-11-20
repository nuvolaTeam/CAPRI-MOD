"""CAPRI's manure pool market m_mPoolMarket solved as CAPRI solves it, "using nlp maximizing v_mPoolBenefits"
(manuremarket/simu_manure_market.gms l. 160), in its variables and four rows with IPOPT (capri_mod/coupling/manure.py
_pool_market_nlp; capri_mod/market/equations/manuremarket/declare_manure_market.py): on convex problems the same
clearing as the QP form (Clarabel), prices and shipments."""
import numpy as np
import pandas as pd
import pytest

import capri_mod.model as M                     # gives the coupling modules their names
from capri_mod.coupling.manure import ManureBlock
from capri_mod.settings import override

POOL = M.CAPRIModel.POOL_OF_PREFIX


class _Market:
    POOL_OF_PREFIX = POOL
    _clear_pool_capri = ManureBlock._clear_pool_capri
    _pool_market_nlp = ManureBlock._pool_market_nlp

    def __init__(self):
        self.par = type("P", (), {})()
        self.ev = type("E", (), {"outer_iter_now": 3, "greendeal_group": True})()
        self.res = type("R", (), {})()


def _case(seed, fout):
    """Regions of three pools with CAPRI's slopes (manure_pool_market_2030.csv) and random trade, values and costs."""
    from capri_mod.data import inputs as _inputs
    t = _inputs.current().csv("manure_pool_market_2030.csv", "environment", float_precision="round_trip")
    rng = np.random.default_rng(seed)
    sub = t[(t.fout == fout) & t.region.str[:2].isin(["NL", "DE", "FR", "DK"]) & ~t.region.str.endswith("000000")]
    sub = sub.groupby(sub.region.str[:2]).head(3)
    crec = []
    for r in sub.itertuples():
        e, i = rng.uniform(0, 0.5), rng.uniform(0, 0.5)
        crec.append({"reg": r.region, "k": POOL.get(r.region[:2], r.region[:2]), "e": e, "i": i,
                     "f": rng.normal(0, 0.05), "cs1": float(r.sell_slope) * rng.uniform(1, 3) + 1e-3,
                     "cb1": float(r.buy_slope) * rng.uniform(1, 3) + 1e-3, "rce": rng.normal(0, 0.1),
                     "rci": rng.normal(0, 0.1), "v": float(r.dual_cal) * rng.uniform(0.5, 1.5),
                     "emax": e + rng.uniform(0.5, 5), "elo": -rng.uniform(0, 0.3), "ilo": -rng.uniform(0, 0.3)})
    keys = sorted({c["k"] for c in crec})
    cost = {(a, b): float(rng.uniform(0.005, 0.05)) for a in keys for b in keys if a != b}
    return keys, crec, cost


@pytest.mark.parametrize("prod,fout,seed", [("N", "MANN", 0), ("P", "MANP", 1), ("K", "MANK", 2)])
def test_the_nlp_clears_the_pools_as_the_qp(prod, fout, seed):
    keys, crec, cost = _case(seed, fout)
    assert len(keys) >= 3 and len(crec) >= 9
    res = {}
    for solver in ("qp", "nlp"):
        with override({"outer_loop.manure_pool_solver": solver}):
            ok, p, ship, status, keep = _Market()._clear_pool_capri(prod, keys, [dict(c) for c in crec], cost, {})
        assert ok, (solver, status)
        res[solver] = (p, ship, keep)
    p_q, s_q, _ = res["qp"]
    p_n, s_n, keep = res["nlp"]
    assert max(abs(v) for v in p_q.values()) > 0.01 and max(abs(v) for v in s_q.values()) > 1.0   # trade and prices
    for k in keys:
        assert p_n[k] == pytest.approx(p_q[k], abs=1e-7)                 # EUR 1000 per t
        assert s_n[k] == pytest.approx(s_q[k], abs=1e-5)                 # kt
    assert len(keep["_nlp_x"]) > 2 * len(crec)                           # the clearing kept for the next start
    # started from it, the same clearing
    with override({"outer_loop.manure_pool_solver": "nlp"}):
        ok, p_w, s_w, status, _ = _Market()._clear_pool_capri(prod, keys, [dict(c) for c in crec], cost, keep)
    assert ok and all(p_w[k] == pytest.approx(p_n[k], abs=1e-8) for k in keys), status


def test_capris_trade_constants_are_held_from_the_first_clearing():
    """outer_loop.manure_pool_trade_consts "capri": CAPRI's p_manureSell/BuyCostConst, calibrated once and held
    (supply/define_manure_trade_costs.gms): a later clearing at other reduced costs keeps the first clearing's constants
    (the same clearing for the same other inputs); "solution" recomputes them (another clearing)."""
    keys, crec, cost = _case(5, "MANN")
    later = [dict(c, rce=c["rce"] + 0.3, rci=c["rci"] - 0.2) for c in crec]
    out = {}
    for mode in ("capri", "solution"):
        m = _Market()
        with override({"outer_loop.manure_pool_trade_consts": mode}):
            ok1, p1, s1, st1, _ = m._clear_pool_capri("N", keys, [dict(c) for c in crec], cost, {})
            ok2, p2, s2, st2, _ = m._clear_pool_capri("N", keys, [dict(c) for c in later], cost, {})
        assert ok1 and ok2, (mode, st1, st2)
        out[mode] = max(abs(p1[k] - p2[k]) for k in keys)
    assert out["capri"] < 1e-8 and out["solution"] > 1e-3, out
