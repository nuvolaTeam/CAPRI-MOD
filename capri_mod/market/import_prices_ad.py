"""G3.2a (claude/g3_plan.md): CAPRI's import prices of one bilateral commodity in CasADi, every policy regime included.

BilateralCommodity.import_prices (market/bilateral.py) computes them with numpy: p_ij = a_ij r_j + b_ij, plus the
change of the tariff-rate quotas' rates from their base (bilateral trqSigmoidFunc_ / tarSpec_ / tarAdVal_ and global
TRQImports_ / tarSpecW_ / tarAdValW_, the smaller of the two by ncpcm: BilateralCommodity._trq_off), plus the change
of the border measures' specific part (entry prices EntryPriceDriver_, tarSpecIfEntryPrice_, prefTriggerPrice_;
flexible levies FlexLevyNotCut_, FlexLevy_: BilateralCommodity.border_spec). The default solve evaluates them at the
current sigmas; G3 needs them as expressions of the prices r and the quotas' sigmas, which this module writes, cell by
cell in the numpy code's order of operations (the last quota writing a cell wins, as in _trq_rates).

    import_price_function(sc) -> CasADi Function (r[n], sB[nb], sW[ng], S[n], D[n]) -> p[cells]
        (S, D: supply and use, the weights of an aggregate exporter block's average market price, MarketPriceAgg_)
    cells(sc) -> the (importer, exporter) pairs of p, the flows with beta > 0

Checked against BilateralCommodity.import_prices at random prices and sigmas (capri_mod/tests/test_import_prices_ad.py).
The scenario's tariff additions (trade_scenario) are not in the function yet.
"""
from __future__ import annotations

from typing import List, Tuple

import numpy as np

_CACHE = {}


def cells(sc) -> List[Tuple[int, int]]:
    """The flows the import prices are needed for: importer i, exporter j with beta_ij > 0."""
    beta = np.asarray(sc.beta, float)
    return [(int(i), int(j)) for i, j in zip(*np.nonzero(beta > 0))]


def _ncpcm(ca, x, y, z):
    """GAMS's ncpCM(x, y, Z) = x - Z ln(1 + exp((x - y) / Z)), as BilateralCommodity.ncpcm (numpy's logaddexp(0, u):
    the stable form max(u, 0) + log1p(exp(-|u|)))."""
    u = (x - y) / z
    return x - z * (ca.fmax(u, 0) + ca.log1p(ca.exp(-ca.fabs(u))))


def _rates(ca, sc, sB, sW):
    """_trq_rates as {cell: expression} for the ad valorem (ta) and specific (ts) rates; absent cells keep their base."""
    ta, ts = {}, {}
    for m, g in enumerate(sc.trq_globals or ()):
        rows, cols = np.nonzero(_mask(sc, g["cover"]))
        for i, j in zip(rows, cols):
            if g["has_ta"]:
                ta[int(i), int(j)] = g["ta_pref"] + g["dta"] * sW[m]
            if g["has_ts"]:
                ts[int(i), int(j)] = g["ts_pref"] + g["dts"] * sW[m]
    for k, q in enumerate(sc.trq_quotas or ()):
        if q["regime"] == "entry_price":
            continue
        tb = q["ta_pref"] + q["dta"] * sB[k]
        sb = q["ts_pref"] + q["dts"] * sB[k]
        g = sc.trq_globals[q["glob"]] if q.get("glob") is not None else None
        if g is not None and g["has_ta"]:
            tw = g["ta_pref"] + g["dta"] * sW[q["glob"]]
            tb = _ncpcm(ca, tw, tb, max(1e-2, 1e-3 * abs(q["dta"])))
        if g is not None and g["has_ts"]:
            tw = g["ts_pref"] + g["dts"] * sW[q["glob"]]
            sb = _ncpcm(ca, tw, sb, max(1e-5, 1e-7 * abs(q["dts"])))
        for i in q["rows"]:
            for j in q["cols"]:
                if q["dta"] != 0 or (g is not None and g["has_ta"]):
                    ta[int(i), int(j)] = tb
                if q["dts"] != 0 or (g is not None and g["has_ts"]):
                    ts[int(i), int(j)] = sb
    return ta, ts


def _mask(sc, ix) -> np.ndarray:
    """A numpy index (a boolean matrix, a tuple of index arrays) as an n x n boolean matrix."""
    n = len(sc.regions)
    m = np.zeros((n, n), dtype=bool)
    m[ix] = True
    return m


def import_price_function(sc):
    """CasADi Function (r[n], sB[nb], sW[ng], S[n], D[n]) -> p[cells(sc)]: the import prices of the flows at the
    exporters' price ratios r and the quotas' sigmas (bilateral sB, global sW), BilateralCommodity.import_prices(r,
    sig=(sB, sW)) without the scenario's tariff additions, with the border measures' average market price of an
    aggregate exporter block (MarketPriceAgg_) weighted at supply S and use D (the numpy code: at mpagg_SD)."""
    key = (sc.name, id(sc))
    f = _CACHE.get(key)
    if f is not None:
        return f
    import casadi as ca
    n = len(sc.regions)
    nb, ng = len(sc.trq_quotas or ()), len(sc.trq_globals or ())
    r = ca.SX.sym("r", n)
    sB, sW = ca.SX.sym("sB", nb), ca.SX.sym("sW", ng)
    S, D = ca.SX.sym("S", n), ca.SX.sym("D", n)
    wq = sc.mpagg_weights(S, D)
    a, b, a0 = (np.asarray(x, float) for x in (sc.a, sc.b, sc.a0))
    tc = np.asarray(sc.tc, float) if sc.tc is not None else np.zeros((n, n))
    cl = cells(sc)
    has_trq = bool(sc.trq_quotas or sc.trq_globals)
    ta, ts = _rates(ca, sc, sB, sW) if has_trq else ({}, {})
    ta0 = np.nan_to_num(sc._trq_ta0) if has_trq else None
    ts0 = np.nan_to_num(sc._trq_ts0) if has_trq else None
    bd = sc.border
    # the border measures' CIF price per cell: a0 r + tc, averaged over the pair of policy blocks with the base flows;
    # for an aggregate exporter block its average market price (MarketPriceAgg_) plus the pair's transport cost
    # (TransportCostsAgg_), as BilateralCommodity.border_spec
    cif = {}
    if bd:
        grp_of = {}
        for gi, (ii, jj, w) in enumerate(bd.get("pairs") or ()):
            for x_, i in enumerate(np.atleast_1d(ii)):
                for y_, j in enumerate(np.atleast_1d(jj)):
                    grp_of[int(i), int(j)] = gi
        grp_expr = {}
        for gi, (ii, jj, w) in enumerate(bd.get("pairs") or ()):
            ii, jj, w = np.atleast_1d(ii), np.atleast_1d(jj), np.asarray(w, float)
            if len(jj) > 1:
                pd0 = np.asarray(sc.Pd0, float)
                pm = sum(wq[int(j)] * pd0[int(j)] * r[int(j)] for j in jj) / sum(wq[int(j)] for j in jj)
                grp_expr[gi] = pm + float((w * tc[np.ix_(ii, jj)]).sum() / w.sum())
                continue
            num = 0
            for x_, i in enumerate(ii):
                for y_, j in enumerate(jj):
                    num = num + float(w[x_, y_]) * (a0[i, j] * r[int(j)] + tc[i, j])
            grp_expr[gi] = num / float(w.sum())

        def cif_of(i, j):
            gi = grp_of.get((i, j))
            return grp_expr[gi] if gi is not None else a0[i, j] * r[j] + tc[i, j]
    out = []
    for (i, j) in cl:
        p = a[i, j] * r[j] + b[i, j]
        if has_trq:
            off = 0
            if (i, j) in ta:
                off = (a0[i, j] * r[j] + tc[i, j]) * (ta[i, j] - ta0[i, j]) / 100.0
            if (i, j) in ts and not (bd and int(bd["kind"][i, j]) == 2):
                off = off + (ts[i, j] - ts0[i, j])
            p = p + off
        if bd and "S0" in bd and int(bd["kind"][i, j]) in (1, 2):
            k = int(bd["kind"][i, j])
            c = cif_of(i, j)
            price = float(bd["price"][i, j])
            if k == 1:
                pref = float(bd["pref"][i, j])
                E = pref if pref > 0 else price
                qi = int(bd["quota"][i, j])
                if qi >= 0:
                    E = pref + (price - pref) * (sB[qi] if nb else 0.0)
                d = (E * 0.95 - c) / (price if price > 0 else 1.0) * float(bd["fac"][i, j])
                g = ca.exp(ca.fmin(0, d)) / (1.0 + 20.0 * ca.exp(-ca.fabs(d)))
                spec = g * float(bd["tars"][i, j])
            else:
                tars = ts[i, j] if (i, j) in ts else float(bd["tars"][i, j])
                z = 1e-3 * (price if price > 0 else 1.0)
                notcut = -_ncpcm(ca, -(price - c), 0.0, z)
                spec = _ncpcm(ca, notcut, tars, z)
            p = p + (spec - float(bd["S0"][i, j]))
        out.append(p)
    f = ca.Function("import_prices_" + sc.name, [r, sB, sW, S, D], [ca.vertcat(*out) if out else ca.SX(0, 1)],
                    ["r", "sB", "sW", "S", "D"], ["p"])
    _CACHE[key] = f
    return f
