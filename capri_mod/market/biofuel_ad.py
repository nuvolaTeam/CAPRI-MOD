"""CAPRI's biofuel block in CasADi: market programme step G2g, first part (docs/design/MARKET_IPOPT_DESIGN.md sections
5-6).

Written once, here, and evaluated from here by BiofuelMixin (capri_mod/market/biofuel.py): the project lead's choice of
one implementation per block (section 7, 30 October 2026). The equations (arm/market_model.gms; CAPRI references in
biofuel.py's docstrings), with the operations in the order biofuel.py had them before the move:

    biofFeedCost_      mu_f = max(p0_f r_f - PRCBY_f p_by,f, 1e-6)       (DDGS at its producer price ratio dd)
    biofFeedCostAgg_   mu_b = (sum_f dp_f mu_f^(1 - rho))^(1 / (1 - rho))
    Biof_              q_f = dp_f X (mu_b / mu_f)^rho                     (f not the numeraire)
    prodBiof_          q_num = max(0, (X - sum_(f != num) q_f PRCB_f) / PRCB_num)
    biofPriceRel_,     PR = PPRI0 r_b / mu_b,
    SupplyBiof_        X = max(0, scale PR + exp(alfa + beta log(PR + 0.01)) SIGMOID(slope (PR - turn)))
    Cpri_, biofDemShare_, biofDem_
                       cp = max(1e-6, CPRI0 + ARM1P0 (ra - 1)),
                       BIOF = (QUTS + MAX SIGMOID(Slope (cp / fossil CPRI - Turn))) HCON oilEqu_fossil / oilEqu_b
    ProcNQ_ (own term) PROC = max(0, PROC0 - hess ARM1P0 (ra - 1) / INPE)

SIGMOID(x) = 1 / (1 + exp(-x)) with x clipped to [-500, 500] (as biofuel.py: exp overflows beyond). The max(0, .) and
max(1e-6, .) floors are the model's, kinks for G3 (CasADi's fmax), to be registered or removed there.
"""
from __future__ import annotations

import numpy as np

_FN = {}


def _sigmoid(ca, x):
    return 1.0 / (1.0 + ca.exp(-ca.fmin(ca.fmax(x, -500.0), 500.0)))


def feed_group_function(name: str, g: dict):
    """CasADi Function (r[n], X, dd) -> (q[n], mub): one CAPRI region's feedstock CES for one biofuel (a group of
    BiofuelMixin._biofuel_params), r the feedstocks' Armington price ratios (1 for a feedstock without a model
    market), X the first-generation output, dd the region's DDGS producer price ratio."""
    import casadi as ca
    n = len(g["q0"])
    r, X, dd = ca.SX.sym("r", n), ca.SX.sym("X"), ca.SX.sym("dd")
    ddg = np.asarray(g["ddgs"], bool)
    by = ca.DM(np.asarray(g["by"], float)) * ca.vertcat(*[dd if ddg[i] else ca.SX(1.0) for i in range(n)])
    mu = ca.fmax(ca.DM(np.asarray(g["p0"], float)) * r - by, 1e-6)
    rho = float(g["rho"])
    mub = ca.dot(ca.DM(np.asarray(g["dp"], float)), mu ** (1.0 - rho)) ** (1.0 / (1.0 - rho))
    q = ca.DM(np.asarray(g["dp"], float)) * X * (mub / mu) ** rho
    k = int(g["num"])
    prcb = np.asarray(g["prcb"], float)
    rest = ca.dot(q, ca.DM(prcb)) - q[k] * prcb[k]
    q[k] = ca.fmax(0.0, (X - rest) / prcb[k])
    return ca.Function(name, [r, X, dd], [q, mub], ["r", "X", "dd"], ["q", "mub"])


def supply_function():
    """CasADi Function (rb, mub, ppri, scale, alfa, beta, slope, turn) -> X: SupplyBiof_ at the biofuel's producer
    price ratio rb and the feedstock cost mub (one function for every region: its parameters are inputs)."""
    f = _FN.get("supply")
    if f is None:
        import casadi as ca
        rb, mub, ppri, sc, al, be, sl, tu = (ca.SX.sym(s) for s in ("rb", "mub", "ppri", "scale", "alfa", "beta",
                                                                      "slope", "turn"))
        PR = ppri * rb / mub
        x = ca.fmax(0.0, sc * PR + ca.exp(al + be * ca.log(PR + 1e-2)) * _sigmoid(ca, sl * (PR - tu)))
        f = _FN["supply"] = ca.Function("biof_supply", [rb, mub, ppri, sc, al, be, sl, tu], [x],
                                        ["rb", "mub", "ppri", "scale", "alfa", "beta", "slope", "turn"], ["X"])
    return f


def demand_function():
    """CasADi Function (ra, cpri, arm1p, quts, dmax, slope, fossil, turn, hcon, oil_fossil, oil_b) -> BIOF: the
    biofuel use at its Armington price ratio ra (Cpri_, biofDemShare_, biofDem_; quts with the mandate applied)."""
    f = _FN.get("demand")
    if f is None:
        import casadi as ca
        names = ("ra", "cpri", "arm1p", "quts", "dmax", "slope", "fossil", "turn", "hcon", "oil_fossil", "oil_b")
        ra, cpri, arm1p, quts, dmax, sl, fos, tu, hcon, ofos, ob = (ca.SX.sym(s) for s in names)
        cp = ca.fmax(1e-6, cpri + arm1p * (ra - 1.0))
        share = quts + dmax * _sigmoid(ca, sl * (cp / fos - tu))
        f = _FN["demand"] = ca.Function("biof_demand", [ra, cpri, arm1p, quts, dmax, sl, fos, tu, hcon, ofos, ob],
                                        [share * hcon * ofos / ob], list(names), ["BIOF"])
    return f


def proc_function():
    """CasADi Function (ra, proc0, hess, arm1p, inpe) -> PROC: the biofuel's non-fuel processing (ProcNQ_, own
    price term)."""
    f = _FN.get("proc")
    if f is None:
        import casadi as ca
        ra, pc, h, a, inpe = (ca.SX.sym(s) for s in ("ra", "proc0", "hess", "arm1p", "inpe"))
        f = _FN["proc"] = ca.Function("biof_proc", [ra, pc, h, a, inpe], [ca.fmax(0.0, pc - h * a * (ra - 1.0) / inpe)],
                                      ["ra", "proc0", "hess", "arm1p", "inpe"], ["PROC"])
    return f
