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
    """The trade system's expressions: (market residual of each region in act (1000 t), the flow function flow(i, j)
    (for the TRQ equations), the price ratios r). offsets: a function (r) -> {(i, j): CasADi expression} added to the
    import prices (BilateralCommodity.import_prices' quota offsets), or None."""
    n = len(sc.regions)
    pos = {i: j for j, i in enumerate(act)}
    s1, s2 = float(sc.s1), float(sc.s2)
    r = [ca.exp(z[pos[i]]) if i in pos else rk[i] for i in range(n)]
    beta = np.asarray(sc.beta, float)
    Pd = [float(sc.Pd0[i]) * r[i] for i in range(n)]
    off = offsets(r) if offsets else {}
    p = {}
    for i in range(n):
        for j in range(n):
            if beta[i, j] > 0:
                pij = A[i, j] * r[j] + B[i, j]
                if (i, j) in off:
                    pij = pij + off[i, j]
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
    return res, flow


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


def trq_quotas(sc) -> list:
    """The indices of the commodity's tariff-rate quotas with a volume (BilateralCommodity.trq_quotas): the unknowns of
    the TRQ equations."""
    return [k for k, q in enumerate(getattr(sc, "trq_quotas", None) or ()) if q["Q"] > 0]


def trade_trq_function(sc, act):
    """Market programme step G2a: the trade system with CAPRI's bilateral tariff-rate quotas inside it, as in
    m_globMarket (trqSigmoidFunc_, tarSpec_, tarAdval_ of arm/market_model.gms; docs/design/PORTS_STAGE4.md), instead
    of the outer fixed point of BilateralCommodity.trq_solve.

    CasADi Function (z, s, A, B0, Sk, Dk, rk, PAk, es, ed, scale) -> (g, J):
      - unknowns: z = log r over act, and s = the sigma of the quotas trq_quotas(sc);
      - B0: the fixed part of the import prices WITHOUT the quota offsets (import_price_matrices(sc, ..., offsets=
        False)); a quota's flows carry (a0 r + tc) dta/100 (s - sigma0) + dts (s - sigma0), r the exporter's ratio;
      - g = [market residual[act] / scale ; s_k - Sigmoid(slope (fill_k / Q_k - 0.97))], fill_k the quota's flows at
        these prices (TradeFlowsAgg_), the sigmoid as BilateralCommodity._sig (TRQ_SLOPE, TRQ_FILL_MID, TRQ_ARG_CLIP);
      - J = the Jacobian of g in (z, s).
    The TRQ equation is trq_solve's fixed point with the flows' full response, not its local one."""
    if getattr(sc, "trq_globals", None) or any(q["regime"] != "bilateral" for q in (sc.trq_quotas or ())):
        raise NotImplementedError(f"{sc.name}: G2a's trade function has CAPRI's bilateral quotas only; the global quotas "
                                  "(TRQImports_, the ncpcm minimum) and the entry prices are in the fixed-point solve "
                                  "(BilateralCommodity.trq_solve) until G3 writes them as equations")
    k_ = ("trq",) + _key(sc, act)
    f = _CACHE.get(k_)
    if f is not None:
        return f
    import casadi as ca
    n = len(sc.regions)
    act = [int(i) for i in act]
    qk = trq_quotas(sc)
    z = ca.SX.sym("z", len(act))
    sg = ca.SX.sym("s", len(qk))
    A, B, Sk, Dk, rk, PAk, es, ed, scale = _syms(ca, n, len(act))
    tc = np.asarray(sc.tc, float) if sc.tc is not None else np.zeros((n, n))
    a0 = np.asarray(sc.a0, float)
    beta = np.asarray(sc.beta, float)

    def offsets(r):
        out = {}
        for m, k in enumerate(qk):
            q = sc.trq_quotas[k]
            ds = sg[m] - float(sc.trq_sigma0[k])
            for i in q["rows"]:
                for j in q["cols"]:
                    if beta[i, j] > 0:
                        out[int(i), int(j)] = ((a0[i, j] * r[j] + tc[i, j]) * q["dta"] / 100.0 + q["dts"]) * ds
        return out

    res, flow = _system(sc, act, ca, z, A, B, Sk, Dk, rk, PAk, es, ed, offsets=offsets)
    slope, mid, clip = float(sc.TRQ_SLOPE), float(sc.TRQ_FILL_MID), float(sc.TRQ_ARG_CLIP)
    trq = []
    for m, k in enumerate(qk):
        q = sc.trq_quotas[k]
        fill = sum((flow(int(i), int(j)) for i in q["rows"] for j in q["cols"]), 0)
        arg = ca.fmin(ca.fmax(slope * (fill / q["Q"] - mid), -clip), clip)
        trq.append(sg[m] - 1.0 / (1.0 + ca.exp(-arg)))
    g = ca.vertcat(ca.vertcat(*res) / scale, *trq)
    x = ca.vertcat(z, sg)
    f = ca.Function("trade_trq_" + sc.name, [z, sg, A, B, Sk, Dk, rk, PAk, es, ed, scale], [g, ca.jacobian(g, x)])
    _CACHE[k_] = f
    return f


def import_price_matrices(sc, tariff_adds=None, offsets: bool = True) -> Tuple[np.ndarray, np.ndarray]:
    """p = A r + B: the import prices of `BilateralCommodity.import_prices` split into the part proportional to the
    exporters' price ratios and the rest (base terms, quota offsets, CAPRI's ad valorem tariff on price plus transport).
    offsets=False leaves the quota offsets out (trade_trq_function has them as unknowns)."""
    n = len(sc.regions)
    A = np.array(sc.a, float, copy=True)
    B = np.array(sc.b, float, copy=True)
    if offsets and getattr(sc, "trq_quotas", None) and sc.trq_offset is not None:
        B = B + sc.trq_offset
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
