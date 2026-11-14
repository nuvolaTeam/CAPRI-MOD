"""G3.2b (claude/g3_plan.md): one bilateral commodity's market in CAPRI's form in CasADi, supply and use as unknowns.

The default solve's trade function (trade_ad._system) takes supply and use log-linear in the commodity's own price
around the outer step's point; G3 takes them as unknowns of their own (CAPRI's v_prodQuant and v_arm1Quant), defined by
the supply and use blocks, so this block is the trade part alone:

    trade_system_function(sc) -> CasADi Function (r[n], sB[nb], sW[ng], S[n], D[n]) ->
        (bal[n], trq[nqa], X[cells], PAr[n])
    bal  SupBalM_ / the trade system: S_j - DS_j - sum_i X_ij (1000 t), every region
    trq  trqSigmoidFunc_ of the active quotas (Q > 0), bilateral then global: sigma - Sigmoid(slope (fill / Q - 0.97)),
         fill TradeFlowsAgg_ (bilateral) or TRQImports_ (global: the cover's flows and the bilateral quotas' overfill,
         -ncpcm(-(fill_k - Q_k), 0, 1E-3 Q_k)); the argument clipped as BilateralCommodity._sig
    X    the flows of cells(sc) (importer, exporter), the diagonal the domestic sales
    PAr  each region's Armington price over its base (the use side's and the crushers' price ratio)

The prices are import_prices_ad's (every policy regime), the CES nests BilateralCommodity.prices / flows'. Checked
against BilateralCommodity.residual and trq_arguments (capri_mod/tests/test_import_prices_ad.py).
"""
from __future__ import annotations

import numpy as np

from capri_mod.market.import_prices_ad import _ncpcm, cells, import_price_function

_CACHE = {}


def active_quotas(sc):
    """BilateralCommodity.trq_active: (bilateral, global) indices of the quotas with a volume."""
    return ([k for k, q in enumerate(sc.trq_quotas or ()) if q["Q"] > 0],
            [m for m, g in enumerate(sc.trq_globals or ()) if g["Q"] > 0])


def trade_system_function(sc):
    """See the module's docstring."""
    key = (sc.name, id(sc), tuple(q["Q"] for q in (sc.trq_quotas or ())), tuple(g["Q"] for g in (sc.trq_globals or ())))
    f = _CACHE.get(key)
    if f is not None:
        return f
    import casadi as ca
    n = len(sc.regions)
    nb, ng = len(sc.trq_quotas or ()), len(sc.trq_globals or ())
    r = ca.SX.sym("r", n)
    sB, sW = ca.SX.sym("sB", nb), ca.SX.sym("sW", ng)
    S, D = ca.SX.sym("S", n), ca.SX.sym("D", n)
    cl = cells(sc)
    pv = import_price_function(sc)(r, sB, sW)
    beta = np.asarray(sc.beta, float)
    s1, s2 = float(sc.s1), float(sc.s2)
    p = {}
    for m, (i, j) in enumerate(cl):
        p[i, j] = ca.fmax(pv[m], 1e-9)
    by_imp = {}
    for (i, j) in cl:
        by_imp.setdefault(i, []).append(j)
    Pd = [float(sc.Pd0[i]) * r[i] for i in range(n)]
    PM, PA = [], []
    for i in range(n):
        if sc._has_imp[i] and i in by_imp:
            pm = 0
            for j in by_imp[i]:
                pm = pm + beta[i, j] * p[i, j] ** (1.0 - s2)
            PM.append(pm ** (1.0 / (1.0 - s2)))
        else:
            PM.append(float(sc.PM0[i]))
        if sc._has_dom[i] or sc._has_imp[i]:
            pa = 0
            if sc._has_dom[i]:
                pa = pa + float(sc.dd[i]) * Pd[i] ** (1.0 - s1)
            if sc._has_imp[i]:
                pa = pa + float(sc.dm[i]) * PM[i] ** (1.0 - s1)
            PA.append(pa ** (1.0 / (1.0 - s1)))
        else:
            PA.append(float(sc.PA0[i]))
    DS = [D[i] * float(sc.dd[i]) * (PA[i] / Pd[i]) ** s1 if sc._has_dom[i] else 0 for i in range(n)]
    M = [D[i] * float(sc.dm[i]) * (PA[i] / PM[i]) ** s1 if sc._has_imp[i] else 0 for i in range(n)]
    X = {}
    for (i, j) in cl:
        X[i, j] = DS[j] if i == j else M[i] * beta[i, j] * (PM[i] / p[i, j]) ** s2
    for i in range(n):
        if (i, i) not in X:
            X[i, i] = DS[i]
    bal = []
    for j in range(n):
        sold = X[j, j]
        for i in range(n):
            if i != j and (i, j) in X:
                sold = sold + X[i, j]
        bal.append(S[j] - sold)

    def fill(q):
        return sum((X[int(i), int(j)] for i in q["rows"] for j in q["cols"] if (int(i), int(j)) in X), 0)
    slope, mid, clip = float(sc.TRQ_SLOPE), float(sc.TRQ_FILL_MID), float(sc.TRQ_ARG_CLIP)
    bil, glo = active_quotas(sc)
    trq = []
    for k in bil:
        q = sc.trq_quotas[k]
        arg = ca.fmin(ca.fmax(slope * (fill(q) / q["Q"] - mid), -clip), clip)
        trq.append(sB[k] - 1.0 / (1.0 + ca.exp(-arg)))
    for m_ in glo:
        g = sc.trq_globals[m_]
        cov = np.zeros((n, n), dtype=bool)
        cov[g["cover"]] = True
        tot = sum((X[int(i), int(j)] for i, j in zip(*np.nonzero(cov)) if (int(i), int(j)) in X), 0)
        for k in g["bil"]:
            q = sc.trq_quotas[k]
            tot = tot - _ncpcm(ca, -(fill(q) - q["Q"]), 0.0, 1e-3 * q["Q"])
        arg = ca.fmin(ca.fmax(slope * (tot / g["Q"] - mid), -clip), clip)
        trq.append(sW[m_] - 1.0 / (1.0 + ca.exp(-arg)))
    PAr = ca.vertcat(*[PA[i] / float(sc.PA0[i]) for i in range(n)])
    f = ca.Function("trade_system_" + sc.name, [r, sB, sW, S, D],
                    [ca.vertcat(*bal), ca.vertcat(*trq) if trq else ca.SX(0, 1),
                     ca.vertcat(*[X[c] for c in cl]) if cl else ca.SX(0, 1), PAr],
                    ["r", "sB", "sW", "S", "D"], ["bal", "trq", "X", "PAr"])
    _CACHE[key] = f
    return f
