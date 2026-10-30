"""CAPRI's bilateral trade system of one commodity in CasADi: the residual of `BilateralCommodity.residual` with
supply and use log-linear around the current point (as `MarketModule._bilateral_inner`), and its exact Jacobian
(market programme step G1, docs/design/ARCHITECTURE_REFACTOR.md section 6, G).

The equations are those of capri_mod/market/bilateral.py (arm/market_model.gms impPrice_, the two Armington nests,
SupBalM_), written once more as a CasADi expression so the Newton step has the exact Jacobian instead of finite
differences. capri_mod/tests/test_trade_ad.py checks the two against each other at random points.

Unknowns: z = log r over the regions that supply the commodity (the others held at their current ratio). Parameters
(numeric, set per call): the import-price matrices of the current tariffs and quota offsets, p = A r + B; the current
point (Sk, Dk, rk, PAk) and the local supply and use elasticities (es, ed); the residual scale.

trade_trq_function (step G2a, docs/design/MARKET_IPOPT_DESIGN.md section 6) adds CAPRI's tariff-rate quotas to the
system: their offsets become unknowns with CAPRI's sigmoid as their equations.
"""
from __future__ import annotations

import hashlib
from typing import Dict, Tuple

import numpy as np

_CACHE: Dict[tuple, object] = {}


def _key(sc, act) -> tuple:
    h = hashlib.sha1()
    for arr in (sc.beta, sc.dd, sc.dm, sc.Pd0, sc.PM0, sc.PA0, sc._has_dom, sc._has_imp):
        h.update(np.ascontiguousarray(arr).tobytes())
    h.update(np.asarray([sc.s1, sc.s2], float).tobytes())
    return (sc.name, len(sc.regions), tuple(int(i) for i in act), h.hexdigest())


def _system(sc, act, ca, z, A, B, Sk, Dk, rk, PAk, es, ed, offsets=None):
    """The trade system's expressions: (market residual of each region in act (1000 t), the flows X[i][j] of the
    importer rows of the quotas into each exporter j (dict, for the TRQ equations)). offsets: {exporter j: CasADi
    symbol} added to the import prices of the quota rows (BilateralCommodity.import_prices), or None."""
    n = len(sc.regions)
    pos = {i: j for j, i in enumerate(act)}
    s1, s2 = float(sc.s1), float(sc.s2)
    r = [ca.exp(z[pos[i]]) if i in pos else rk[i] for i in range(n)]
    beta = np.asarray(sc.beta, float)
    Pd = [float(sc.Pd0[i]) * r[i] for i in range(n)]
    rows = set(int(i) for i in sc._rows()) if offsets else set()
    p = {}
    for i in range(n):
        for j in range(n):
            if beta[i, j] > 0:
                pij = A[i, j] * r[j] + B[i, j]
                if i in rows and j in offsets:
                    pij = pij + offsets[j]
                p[i, j] = ca.fmax(pij, 1e-9)
    PM, PA = [], []
    for i in range(n):
        terms = [beta[i, j] * p[i, j] ** (1.0 - s2) for j in range(n) if beta[i, j] > 0]
        PM.append(ca.sum1(ca.vertcat(*terms)) ** (1.0 / (1.0 - s2)) if (sc._has_imp[i] and terms)
                  else float(sc.PM0[i]))
        pa = 0
        if sc._has_dom[i]:
            pa = pa + float(sc.dd[i]) * Pd[i] ** (1.0 - s1)
        if sc._has_imp[i]:
            pa = pa + float(sc.dm[i]) * PM[i] ** (1.0 - s1)
        PA.append(pa ** (1.0 / (1.0 - s1)) if (sc._has_dom[i] or sc._has_imp[i]) else float(sc.PA0[i]))
    S = [Sk[i] * (r[i] / rk[i]) ** es[i] for i in range(n)]
    D = [Dk[i] * (PA[i] / PAk[i]) ** ed[i] for i in range(n)]
    DS = [D[i] * float(sc.dd[i]) * (PA[i] / Pd[i]) ** s1 if sc._has_dom[i] else 0 for i in range(n)]
    M = [D[i] * float(sc.dm[i]) * (PA[i] / PM[i]) ** s1 if sc._has_imp[i] else 0 for i in range(n)]

    def flow(i, j):
        if i == j:
            return DS[j]
        return M[i] * beta[i, j] * (PM[i] / p[i, j]) ** s2 if beta[i, j] > 0 else 0

    res = []
    for j in act:
        sold = DS[j]
        for i in range(n):
            if i != j and beta[i, j] > 0:
                sold = sold + M[i] * beta[i, j] * (PM[i] / p[i, j]) ** s2
        res.append(S[j] - sold)
    quota_flows = {j: sum((flow(i, j) for i in sorted(rows)), 0) for j in (offsets or {})}
    return res, quota_flows


def _syms(ca, n, n_act):
    A = ca.SX.sym("A", n, n)
    B = ca.SX.sym("B", n, n)
    Sk, Dk, rk, PAk = (ca.SX.sym(nm, n) for nm in ("Sk", "Dk", "rk", "PAk"))
    es, ed = ca.SX.sym("es", n), ca.SX.sym("ed", n)
    scale = ca.SX.sym("scale", n_act)
    return A, B, Sk, Dk, rk, PAk, es, ed, scale


def trade_function(sc, act):
    """CasADi Function (z, A, B, Sk, Dk, rk, PAk, es, ed, scale) -> (residual[act] / scale, its Jacobian in z)."""
    k = _key(sc, act)
    f = _CACHE.get(k)
    if f is not None:
        return f
    import casadi as ca
    n = len(sc.regions)
    act = [int(i) for i in act]
    z = ca.SX.sym("z", len(act))
    A, B, Sk, Dk, rk, PAk, es, ed, scale = _syms(ca, n, len(act))
    res, _ = _system(sc, act, ca, z, A, B, Sk, Dk, rk, PAk, es, ed)
    g = ca.vertcat(*res) / scale
    f = ca.Function("trade_" + sc.name, [z, A, B, Sk, Dk, rk, PAk, es, ed, scale], [g, ca.jacobian(g, z)])
    _CACHE[k] = f
    return f


def trq_exporters(sc) -> np.ndarray:
    """The exporters under an EU tariff-rate quota with a price gap (BilateralCommodity.trq_solve's): the unknowns of
    the TRQ equations."""
    if sc.trq_row is None or sc.trq_Q is None or sc.trq_gap is None:
        return np.array([], dtype=int)
    return np.where((np.asarray(sc.trq_Q, float) > 0) & (np.asarray(sc.trq_gap, float) > 0))[0]


def trq_constants(sc, quota) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per quota exporter: (gap, k = share / quota, s0 = the sigmoid at the base fill), as trq_solve has them."""
    rows = sc._rows()
    gap = np.asarray(sc.trq_gap, float)[quota]
    k = np.asarray(sc.trq_share, float)[quota] / np.asarray(sc.trq_Q, float)[quota]
    s0 = []
    for j in quota:
        qb = float(sc.trq_Q0[j]) if sc.trq_Q0 is not None else float(sc.trq_Q[j])
        s0.append(float(sc._sig(sc.trq_share[j] / qb * float(sc.X0[rows, j].sum()))) if qb > 0 else 0.0)
    return gap, k, np.asarray(s0, float)


def trade_trq_function(sc, act):
    """Market programme step G2a: the trade system with CAPRI's tariff-rate quotas inside it, as in m_globMarket
    (trqSigmoidFunc_, TRQImports_, tarSpec_ of arm/market_model.gms), instead of the outer fixed point of
    BilateralCommodity.trq_solve.

    CasADi Function (z, o, A, B0, Sk, Dk, rk, PAk, es, ed, scale) -> (g, J):
      - unknowns: z = log r over act, and o = the quota offsets of the exporters trq_exporters(sc) (EUR/t, added to
        the import prices of the quota's importer rows);
      - B0: the fixed part of the import prices WITHOUT the offsets (import_price_matrices(sc, ..., offsets=False));
      - g = [market residual[act] / scale ; (o_j - gap_j (sig(k_j X_j) - s0_j)) / gap_j], X_j the flows of the quota
        rows into exporter j at these prices, sig CAPRI's sigmoid as BilateralCommodity._sig (TRQ_SLOPE,
        TRQ_FILL_MID, TRQ_ARG_CLIP);
      - J = the Jacobian of g in (z, o).
    The TRQ equation is trq_solve's fixed point with the flows' full response, not its local one."""
    k_ = ("trq",) + _key(sc, act)
    f = _CACHE.get(k_)
    if f is not None:
        return f
    import casadi as ca
    n = len(sc.regions)
    act = [int(i) for i in act]
    quota = [int(j) for j in trq_exporters(sc)]
    z = ca.SX.sym("z", len(act))
    o = ca.SX.sym("o", len(quota))
    A, B, Sk, Dk, rk, PAk, es, ed, scale = _syms(ca, n, len(act))
    res, qf = _system(sc, act, ca, z, A, B, Sk, Dk, rk, PAk, es, ed,
                      offsets={j: o[q] for q, j in enumerate(quota)})
    gap, kk, s0 = trq_constants(sc, quota)
    slope, mid, clip = float(sc.TRQ_SLOPE), float(sc.TRQ_FILL_MID), float(sc.TRQ_ARG_CLIP)
    trq = []
    for q, j in enumerate(quota):
        arg = ca.fmin(ca.fmax(slope * (kk[q] * qf[j] - mid), -clip), clip)
        trq.append((o[q] - gap[q] * (1.0 / (1.0 + ca.exp(-arg)) - s0[q])) / gap[q])
    g = ca.vertcat(ca.vertcat(*res) / scale, *trq)
    x = ca.vertcat(z, o)
    f = ca.Function("trade_trq_" + sc.name, [z, o, A, B, Sk, Dk, rk, PAk, es, ed, scale], [g, ca.jacobian(g, x)])
    _CACHE[k_] = f
    return f


def import_price_matrices(sc, tariff_adds=None, offsets: bool = True) -> Tuple[np.ndarray, np.ndarray]:
    """p = A r + B: the import prices of `BilateralCommodity.import_prices` split into the part proportional to the
    exporters' price ratios and the rest (base terms, quota offsets, CAPRI's ad valorem tariff on price plus transport).
    offsets=False leaves the quota offsets out (trade_trq_function has them as unknowns)."""
    n = len(sc.regions)
    A = np.array(sc.a, float, copy=True)
    B = np.array(sc.b, float, copy=True)
    if offsets and sc.trq_row is not None and sc.trq_offset is not None:
        rows = sc._rows()
        B[rows] = B[rows] + sc.trq_offset[None, :]
    for importer, pts in (tariff_adds or ()):
        if not pts:
            continue
        imp = np.atleast_1d(np.asarray(importer, dtype=int))
        ext = ~np.isin(np.arange(n), imp)
        tc = sc.tc if sc.tc is not None else np.zeros_like(sc.a0)
        for i_ in imp:
            A[i_] = A[i_] + np.where(ext, sc.a0[i_], 0.0) * float(pts) / 100.0
            B[i_] = B[i_] + np.where(ext, tc[i_], 0.0) * float(pts) / 100.0
    return A, B
