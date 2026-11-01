"""CAPRI's human consumption (the Generalised Leontief demand system) in CasADi: market programme step G2c
(docs/design/MARKET_IPOPT_DESIGN.md sections 5-6).

The block is written once, here, and the model evaluates it from here (DemandMixin._gl_eval and gl_food_ratio,
capri_mod/market/demand.py): the project lead's choice of one implementation per block (section 7, 30 October 2026). The
assembled market NLP of step G3 composes gl_block_function with the trade systems' Armington prices; until then the
default solve calls it numerically. CAPRI's equations (arm/market_model.gms l. 826-916, Cpri_ l. 3032-3039):

    x_i = [G_i / G (Y ir - F) + d_i] INHA / 1000,   G = sqrt(p)' B sqrt(p),  G_i = (B sqrt(p))_i / sqrt(p_i),
    F = d' p,   p = CPRI0 + (PR - 1) ARM1P0

per behavioural region (1000 t; p in EUR/kg, Y income per head, ir its ratio, INHA inhabitants), PR the Armington price
ratio of the model region's commodity. Two floors are the model's, not CAPRI's (as in demand.py before the move): a
consumer price at least 5% of its calibration value and a demand of at least 0 in the sums per model region.
Smooth elsewhere; at G3 they are kinks of the NLP (CasADi's fmax), to be registered or removed there.

Floating point: CasADi's matrix-vector products sum in their own order, so the values differ from NumPy's
(sq @ B) @ sq by rounding only (capri_mod/tests/test_demand_ad.py measures it).
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

_ENTRY: Dict[int, object] = {}


def gl_entry_function(n: int):
    """CasADi Function (p[n], d[n], B[n x n], Y, inha, ir) -> x[n]: one behavioural region's GL demand (1000 t)."""
    f = _ENTRY.get(n)
    if f is not None:
        return f
    import casadi as ca
    p, d = ca.SX.sym("p", n), ca.SX.sym("d", n)
    B = ca.SX.sym("B", n, n)
    Y, inha, ir = ca.SX.sym("Y"), ca.SX.sym("inha"), ca.SX.sym("ir")
    sq = ca.sqrt(p)
    Bs = ca.mtimes(B, sq)
    G = ca.dot(sq, Bs)
    F = ca.dot(d, p)
    x = (Bs / sq / G * (Y * ir - F) + d) * inha / 1000.0
    f = ca.Function(f"gl_x{n}", [p, d, B, Y, inha, ir], [x], ["p", "d", "B", "Y", "inha", "ir"], ["x"])
    _ENTRY[n] = f
    return f


def gl_eval(e: dict, p: np.ndarray, ir: float) -> np.ndarray:
    """One behavioural region's GL demand at consumer prices p (EUR/kg) and income ratio ir (1000 t)."""
    f = gl_entry_function(len(p))
    return np.asarray(f(np.asarray(p, float), np.asarray(e["d"], float), e["B"], float(e["Y"]), float(e["inha"]),
                        float(ir))).ravel()


def gl_block_function(groups: Dict[str, List[dict]], regions: List[str], n_com: int):
    """CasADi Function (PR[nR x nC], ir, d) -> (h[cells], x) for every behavioural region of `groups` (DemandMixin.
    _gl_params' groups, in their order):
      - d: the commitments of all behavioural regions, concatenated in that order (they move with the re-fit);
      - x: their demands, concatenated likewise;
      - h: per cell (model region, commodity) of `cells`, the sum of the demands of its goods, each floored at 0.
    Returns (the Function, cells: list of (region row, commodity column), the slices of d per behavioural region)."""
    import casadi as ca
    Rr = {r: i for i, r in enumerate(regions)}
    nR = len(regions)
    PR = ca.MX.sym("PR", nR, n_com)
    ir = ca.MX.sym("ir")
    sizes = [len(e["p0"]) for mr in groups for e in groups[mr]]
    d = ca.MX.sym("d", int(sum(sizes)))
    acc: Dict[Tuple[int, int], object] = {}
    order: List[Tuple[int, int]] = []
    xs, slices, o = [], [], 0
    for mr, ents in groups.items():
        i = Rr[mr]
        for e in ents:
            n = len(e["p0"])
            col, p0, a1 = e["col"], e["p0"], e["arm1p"]
            p = ca.vertcat(*[ca.fmax(p0[k] + (PR[i, int(col[k])] - 1.0) * a1[k], 0.05 * p0[k]) if col[k] >= 0
                             else ca.fmax(p0[k], 0.05 * p0[k]) for k in range(n)])
            x = gl_entry_function(n)(p, d[o:o + n], ca.DM(e["B"]), float(e["Y"]), float(e["inha"]), ir)
            xs.append(x)
            slices.append((o, o + n))
            o += n
            for k in range(n):
                if col[k] >= 0:
                    key = (i, int(col[k]))
                    if key not in acc:
                        acc[key] = 0
                        order.append(key)
                    acc[key] = acc[key] + ca.fmax(x[k], 0.0)
    cells = order
    h = ca.vertcat(*[acc[c] for c in cells]) if cells else ca.MX(0, 1)
    f = ca.Function("gl_food", [PR, ir, d], [h, ca.vertcat(*xs) if xs else ca.MX(0, 1)],
                    ["PR", "ir", "d"], ["h", "x"])
    # expanded to one SX function: the same operations in the same order, evaluated about three times faster than
    # the MX graph of 80 calls (31 October 2026)
    return f.expand(), cells, slices
