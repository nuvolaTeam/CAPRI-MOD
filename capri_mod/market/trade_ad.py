"""CAPRI's bilateral trade system of one commodity in CasADi: the residual of `BilateralCommodity.residual` with
supply and use log-linear around the current point (as `MarketModule._bilateral_inner`), and its exact Jacobian
(market programme step G1, docs/design/ARCHITECTURE_REFACTOR.md section 6, G).

The equations are those of capri_mod/market/bilateral.py (arm/market_model.gms impPrice_, the two Armington nests,
SupBalM_), written once more as a CasADi expression so the Newton step has the exact Jacobian instead of finite
differences. capri_mod/tests/test_trade_ad.py checks the two against each other at random points.

Unknowns: z = log r over the regions that supply the commodity (the others held at their current ratio). Parameters
(numeric, set per call): the import-price matrices of the current tariffs and quota offsets, p = A r + B; the current
point (Sk, Dk, rk, PAk) and the local supply and use elasticities (es, ed); the residual scale.
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


def trade_function(sc, act):
    """CasADi Function (z, A, B, Sk, Dk, rk, PAk, es, ed, scale) -> (residual[act] / scale, its Jacobian in z)."""
    k = _key(sc, act)
    f = _CACHE.get(k)
    if f is not None:
        return f
    import casadi as ca
    n = len(sc.regions)
    act = [int(i) for i in act]
    pos = {i: j for j, i in enumerate(act)}
    z = ca.SX.sym("z", len(act))
    A = ca.SX.sym("A", n, n)
    B = ca.SX.sym("B", n, n)
    Sk, Dk, rk, PAk = (ca.SX.sym(nm, n) for nm in ("Sk", "Dk", "rk", "PAk"))
    es, ed = ca.SX.sym("es", n), ca.SX.sym("ed", n)
    scale = ca.SX.sym("scale", len(act))
    s1, s2 = float(sc.s1), float(sc.s2)
    r = [ca.exp(z[pos[i]]) if i in pos else rk[i] for i in range(n)]
    beta = np.asarray(sc.beta, float)
    Pd = [float(sc.Pd0[i]) * r[i] for i in range(n)]
    p = {}
    for i in range(n):
        for j in range(n):
            if beta[i, j] > 0:
                p[i, j] = ca.fmax(A[i, j] * r[j] + B[i, j], 1e-9)
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
    res = []
    for j in act:
        sold = DS[j]
        for i in range(n):
            if i != j and beta[i, j] > 0:
                sold = sold + M[i] * beta[i, j] * (PM[i] / p[i, j]) ** s2
        res.append(S[j] - sold)
    g = ca.vertcat(*res) / scale
    f = ca.Function("trade_" + sc.name, [z, A, B, Sk, Dk, rk, PAk, es, ed, scale], [g, ca.jacobian(g, z)])
    _CACHE[k] = f
    return f


def import_price_matrices(sc, tariff_adds=None) -> Tuple[np.ndarray, np.ndarray]:
    """p = A r + B: the import prices of `BilateralCommodity.import_prices` split into the part proportional to the
    exporters' price ratios and the rest (base terms, quota offsets, CAPRI's ad valorem tariff on price plus transport)."""
    n = len(sc.regions)
    A = np.array(sc.a, float, copy=True)
    B = np.array(sc.b, float, copy=True)
    if sc.trq_row is not None and sc.trq_offset is not None:
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
