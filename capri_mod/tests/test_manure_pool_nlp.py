"""CAPRI's manure pool market m_mPoolMarket solved as CAPRI solves it, "using nlp maximizing v_mPoolBenefits"
(manuremarket/simu_manure_market.gms l. 160), in its variables and four rows with IPOPT (capri_mod/coupling/manure.py
_pool_market_nlp; capri_mod/market/equations/manuremarket/declare_manure_market.py): on convex problems the same
clearing as the same problem written as a convex QP (Clarabel; the model's form until 20 November 2026, kept here as
the cross-check since its setting was retired on 23 November 2026), prices and shipments."""
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


def _qp_clearing(keys, crec, reg_terms, arcs, arc_cost, lo):
    """The pool market as a convex QP (Clarabel) from the NLP's own problem data: minus the benefits, the regions'
    surplus by e_mPoolSurplus's coefficients, one balance row per pool, the regions' trade bounded below by lo (solved
    in the shifted variables x' = x - lo >= 0) and their exports by the manure produced; the pool price is the pool
    balance's dual in the model's convention (a fee). Returns (prices, net shipments by pool)."""
    from capri_mod.market.equations.manuremarket.declare_manure_market import e_mPoolSurplus
    from capri_mod.supply.convex_qp import solve_convex_qp
    nr, na = len(crec), len(arcs)
    nv = 2 * nr + na
    Qp, cp_ = np.zeros((nv, nv)), np.zeros(nv)
    for q, (a, b, cs0, cs1, cb0, cb1) in enumerate(reg_terms):
        q_ee, q_ii, q_ei, c_e, c_i = e_mPoolSurplus(a, b, cs0, cs1, cb0, cb1)
        ie, ii = q, nr + q
        Qp[ie, ie] += q_ee; Qp[ii, ii] += q_ii; Qp[ie, ii] -= q_ei; Qp[ii, ie] -= q_ei
        cp_[ie], cp_[ii] = c_e, c_i
    cp_[2 * nr:] = arc_cost
    Ap, bp = np.zeros((nr, nv)), np.zeros(nr)
    for q, r_ in enumerate(crec):
        Ap[q, q], bp[q] = 1.0, r_["emax"]
    Aeq = np.zeros((len(keys), nv))
    for j, k in enumerate(keys):
        for q, r_ in enumerate(crec):
            if r_["k"] == k:
                Aeq[j, q], Aeq[j, nr + q] = 1.0, -1.0
        for t, (a_, b_, cc) in enumerate(arcs):
            if a_ == k:
                Aeq[j, 2 * nr + t] -= 1.0
            if b_ == k:
                Aeq[j, 2 * nr + t] += 1.0
    sh = np.zeros(nv)
    sh[:2 * nr] = -np.asarray(lo, float)
    cps = cp_ - Qp @ sh
    sc = max(float(np.abs(cps).max()), float(np.abs(Qp).max()), 1e-12)
    sol, ok, info = solve_convex_qp(Qp / sc, cps / sc, Ap, bp + Ap @ sh, Aeq, Aeq @ sh, tol=1e-8)
    assert ok or "AlmostSolved" in str(info.get("status")), info.get("status")
    sol = np.asarray(sol, float) - sh
    y = np.asarray(info.get("y"), float) * sc
    ship = {k: 0.0 for k in keys}
    for t, (a_, b_, cc) in enumerate(arcs):
        ship[a_] += sol[2 * nr + t]; ship[b_] -= sol[2 * nr + t]
    return {k: float(y[j]) for j, k in enumerate(keys)}, ship


@pytest.mark.parametrize("prod,fout,seed", [("N", "MANN", 0), ("P", "MANP", 1), ("K", "MANK", 2)])
def test_the_nlp_clears_the_pools_as_the_qp(prod, fout, seed):
    keys, crec, cost = _case(seed, fout)
    assert len(keys) >= 3 and len(crec) >= 9
    seen = {}

    class _Spy(_Market):
        def _pool_market_nlp(self, *args):
            seen["args"] = args
            return ManureBlock._pool_market_nlp(self, *args)
    ok, p_n, s_n, status, keep = _Spy()._clear_pool_capri(prod, keys, [dict(c) for c in crec], cost, {})
    assert ok, status
    k_, c_, reg_terms, arcs, arc_cost, lo, up, x0, _prev = seen["args"]
    p_q, s_q = _qp_clearing(k_, c_, reg_terms, arcs, arc_cost, lo)
    assert max(abs(v) for v in p_q.values()) > 0.01 and max(abs(v) for v in s_q.values()) > 1.0   # trade and prices
    for k in keys:
        assert p_n[k] == pytest.approx(p_q[k], abs=1e-7)                 # EUR 1000 per t
        assert s_n[k] == pytest.approx(s_q[k], abs=1e-5)                 # kt
    assert len(keep["_clear_x"]) > 2 * len(crec)                           # the clearing kept for the next start
    # started from it, the same clearing
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
