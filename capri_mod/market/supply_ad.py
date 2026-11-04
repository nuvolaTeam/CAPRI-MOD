"""CAPRI's market supply functions (ProdNQ_) in CasADi: market programme step G2b, first part
(docs/design/MARKET_IPOPT_DESIGN.md sections 5-6).

The functions are written once, here, and the model evaluates them from here (SupplyMixin._noneu_market_supply_nq and
_eu_market_supply_nq, capri_mod/market/supply.py): the project lead's choice of one implementation per block (section
7, 30 October 2026). The assembled market NLP of step G3 composes them with the trade systems' prices; until then the
default solve calls them numerically. CAPRI's equation (arm/market_model.gms ProdNQ_, the normalised quadratic supply
function with p_hessNQSupp, here in the ratio form of tools/build/build_noneu_market_supply_nq.py):

    q_x = max(0, q0_x + sum_y h_xy (r_y - 1) + h_xM (m - 1) + sum_s f_xs (FEDE_s - 1) + l_x)

per market region and product x: r the region's price ratios of the market products, m its dairy block's raw milk
price ratio, FEDE_s the feed energy price ratio of its CAPRI region s (audit M3), l_x the change from the land rents of
its CAPRI regions (the land block, noneu_land_solve, an input here: it is lifted with the land block). h in kt per unit
of price ratio. The floor at 0 is the model's (as supply.py before the move): a kink for G3 (CasADi's fmax), to be
registered or removed there.

Floating point: the sums run in CasADi's order (matrix-vector products), so the values differ from the loops of
supply.py before the move by rounding only (capri_mod/tests/test_supply_ad.py measures it).
"""
from __future__ import annotations

from typing import Dict, List, Sequence

import numpy as np


def nq_rows_function(name: str, n_cols: int, H: np.ndarray, hm: Sequence[float], HF: np.ndarray):
    """CasADi Function (q0[n_x], r[n_cols], m, fede[n_s], lsh[n_x]) -> (q[n_x], dq[n_x]) for the n_x products of one
    market region: q0 their base supply (an input: the market's base moves with its calibration), H (n_x x n_cols) the
    terms in the market products' price ratios, hm (n_x) the terms in the raw milk price ratio, HF (n_x x n_s) the
    terms in the feed energy prices of its CAPRI regions."""
    import casadi as ca
    nx, ns = H.shape[0], HF.shape[1]
    q0, r, m = ca.SX.sym("q0", nx), ca.SX.sym("r", n_cols), ca.SX.sym("m")
    fede, lsh = ca.SX.sym("fede", ns), ca.SX.sym("lsh", nx)
    dq = (ca.mtimes(ca.DM(H), r - 1.0) + ca.DM(np.asarray(hm, float)) * (m - 1.0)
          + (ca.mtimes(ca.DM(HF), fede - 1.0) if ns else 0) + lsh)
    q = ca.fmax(q0 + dq, 0.0)
    return ca.Function(name, [q0, r, m, fede, lsh], [q, dq], ["q0", "r", "m", "fede", "lsh"], ["q", "dq"])


def build_rows(terms: Dict[str, Dict[str, float]], cols: List[str],
               fede_terms: Dict[str, Dict[str, float]] = None) -> dict:
    """The arrays of nq_rows_function for one region from the model's parameters: terms {x: {y: h}} (y a market
    product, or MILK), fede_terms {CAPRI region: {x: h}}. Rows: the products x in cols, in the order of `terms` (the
    caller leaves those without base supply as they are). Returns {"rows", "H", "hm", "HF", "rms"}."""
    ci = {c: j for j, c in enumerate(cols)}
    rows = [x for x in terms if x in ci]
    rms = sorted(fede_terms or {})
    H = np.zeros((len(rows), len(cols)))
    hm = np.zeros(len(rows))
    HF = np.zeros((len(rows), len(rms)))
    for i, x in enumerate(rows):
        for y, h in terms[x].items():
            if y == "MILK":
                hm[i] += float(h)
            elif y in ci:
                H[i, ci[y]] += float(h)
        for k, s in enumerate(rms):
            HF[i, k] = float((fede_terms[s] or {}).get(x, 0.0))
    return {"rows": rows, "H": H, "hm": hm, "HF": HF, "rms": rms}


def hess_rows_function(name: str, Hm: np.ndarray):
    """CasADi Function (s0[n_x], dP[n_cols], extra[n_x]) -> (q[n_x], q_raw[n_x]): CAPRI's ProdNQ_ of the supply models' products
    (the market supply Hessian measured on the supply models at the baseline, arm/simu_calibration_to_supply.gms
    l. 360-368: the constant re-anchored to the models' latest output s0 at the prices they saw), q = max(0, s0 + Hm dP
    + extra), dP the price change against the prices the models saw (raw milk's at 0 where the dairy block prices it,
    NQ_PRICE_AS_SEEN), extra the young animals' and raw milk's terms of their clearing (lifted in G2g); q_raw the same
    without the floor."""
    import casadi as ca
    nx, nc = Hm.shape
    s0, dP, extra = ca.SX.sym("s0", nx), ca.SX.sym("dP", nc), ca.SX.sym("extra", nx)
    qr = s0 + ca.mtimes(ca.DM(Hm), dP) + extra
    return ca.Function(name, [s0, dP, extra], [ca.fmax(qr, 0.0), qr], ["s0", "dP", "extra"], ["q", "q_raw"])


_ANT = {}


def anticipation_function(n_r: int, n_c: int):
    """CasADi Function (S[n_r x n_c], RR, SV, E) -> max(0, S (RR / SV)^E) elementwise: the market supply before
    ProdNQ_, CAPRI's own-price response of the supply models' output anticipated against the prices they saw (EU
    rows: SV the prices the EU's models last saw, E CAPRI's EU p_elasSupp; supply-model rows outside the EU likewise
    with the region's own elasticities; the other rows: SV = 1, E their own-price elasticity, 0 where ProdNQ_ applies)."""
    f = _ANT.get((n_r, n_c))
    if f is not None:
        return f
    import casadi as ca
    S, RR, SV, E = (ca.SX.sym(n, n_r, n_c) for n in ("S", "RR", "SV", "E"))
    f = ca.Function(f"anticipation_{n_r}x{n_c}", [S, RR, SV, E], [ca.fmax(S * (RR / SV) ** E, 0.0)],
                    ["S", "RR", "SV", "E"], ["q"])
    _ANT[(n_r, n_c)] = f
    return f


_POOL = {}


def pooled_residual_function(n_r: int):
    """CasADi Function (S[n_r], D[n_r]) -> F: the world balance of a pooled commodity (one price ratio for all market
    regions: raw milk outside the dairy blocks, the other oilseeds; capri-mod's departure DEP-31, CAPRI's wldMarket_
    being m_netTrade's), sum S - sum D."""
    f = _POOL.get(n_r)
    if f is None:
        import casadi as ca
        S, D = ca.SX.sym("S", n_r), ca.SX.sym("D", n_r)
        f = ca.Function(f"pooled_{n_r}", [S, D], [ca.sum1(S) - ca.sum1(D)], ["S", "D"], ["F"])
        _POOL[n_r] = f
    return f
