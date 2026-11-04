"""CAPRI's processing demand in CasADi: oilseed crushing (ProcMargO_, ProcNQ_, ProcFudge_, ProcO_, procYield_) and the
normalised quadratic processing of the other products (ProcNQ_, ProcFudge_); market programme step G2e
(docs/design/MARKET_IPOPT_DESIGN.md sections 5-6).

Written once, here; the model evaluates it from here (ProcessingMixin._crush_state, DemandMixin.demand_response),
the project lead's choice of one implementation per block (section 7, 30 October 2026). The equations, operations and
order of the sums are those of capri_mod/market/processing.py and demand.py before the move (31 October 2026); their
CAPRI references (arm/market_model.gms l. 1118-1176, 1480-1520) are in those docstrings. ProcFudge_ is CAPRI's smooth
max(q, 0): q + z log(1 + exp(-q/z)) + 1e-11, z = 0.01 min(1000, max(1e-11, PROC0)), written as NumPy's logaddexp
evaluates it (max(0, u) + log1p(exp(-|u|)), u = -q/z), so the values are the same to the last bit where the operations
are.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

def crush_columns(chains: Dict[str, Tuple[str, str]]) -> List[str]:
    """The crushing chain's commodities in the order of the crush function's ratio columns: seed, oil, cake."""
    cols = []
    for s, (o, c) in chains.items():
        cols += [s, o, c]
    return cols


def _fudge(ca, q, q0):
    """CAPRI's ProcFudge_ (market_model.gms l. 1158-1163; processing.py _proc_fudge until G2f): q0 a number or a CasADi
    expression."""
    if isinstance(q0, (int, float)):
        z = 0.01 * min(1000.0, max(1e-11, float(q0)))
    else:
        z = 0.01 * ca.fmin(1000.0, ca.fmax(1e-11, q0))
    u = -q / z
    return q + z * (ca.fmax(0.0, u) + ca.log1p(ca.exp(-ca.fabs(u)))) + 1e-11


def _cet(ca, e, ro, rc):
    """CAPRI's procYield_ (processing.py _cet_yields): oil and cake yields of one behavioural region."""
    po, pc = e["ppo"] * ro, e["ppc"] * rc
    lo = ca.log(((po + 1e-3) / (e["ppo"] + 1e-3)) / ((pc + 1e-3) / (e["ppc"] + 1e-3)))
    Ao = e["yo0"] * ca.exp(e["rho"] * lo)
    Ac = e["yc0"] * ca.exp(-e["rho"] * lo)
    S0 = e["yo0"] + e["yc0"]
    T = (Ao + Ac + S0) / 2.0
    return Ao + (S0 - T) / 2.0, Ac + (S0 - T) / 2.0


def crush_function(cp: dict, seeds: dict, Hrms: dict, chains: Dict[str, Tuple[str, str]]):
    """CasADi Function rat[nr x 9] -> (out[n_pairs x 3], detail[n_entries x 2]) for every (region, seed) of cp
    (ProcessingMixin._crush_params, in its order):
      - rat: per region of cp (in order of first appearance) the price ratios of the chain's commodities
        (crush_columns: seed, oil, cake per seed), the seed's Armington ratio, the oil's and cake's producer ratios;
      - out: crush, oil output, cake output per pair;
      - detail: per behavioural region of the pairs with entries (in order): the crush change before ProcFudge_ and
        the own margin change (the welfare report's detail of _crush_state).
    Returns (Function, regions (rows of rat), pairs, the entries' keys (region, seed, behavioural region))."""
    import casadi as ca
    cols = crush_columns(chains)
    ci = {x: j for j, x in enumerate(cols)}
    regions: List[str] = []
    for (r, _s) in cp:
        if r not in regions:
            regions.append(r)
    ri = {r: i for i, r in enumerate(regions)}
    rat = ca.SX.sym("rat", len(regions), len(cols))

    def ratio(r, x):
        return rat[ri[r], ci[x]]
    rows, det, keys = [], [], []
    pairs = list(cp)
    for (r, s) in pairs:
        p = cp[(r, s)]
        o, c = chains[s]
        ents = seeds.get((r, s), [])
        if not ents:
            rows.append(ca.horzcat(p["q0"], p["q0"] * p["yo"], p["q0"] * p["yc"]))
            continue
        k = p["q0"] / sum(e["q0"] for e in ents)
        crush = oil = cake = 0.0
        oil0 = cake0 = 0.0
        for e in ents:
            Hr = Hrms.get(r, {}).get(e["rms"], {})
            q = k * e["q0"]
            for y in chains:
                h = Hr.get((s, y), 0.0)
                if h == 0.0:
                    continue
                ey = next((x for x in seeds.get((r, y), []) if x["rms"] == e["rms"]), None)
                if ey is None:
                    continue
                oy, cy = chains[y]
                yo, yc = _cet(ca, ey, ratio(r, oy), ratio(r, cy))
                m = -ey["a1"] * ratio(r, y) + ey["ppo"] * ratio(r, oy) * yo + ey["ppc"] * ratio(r, cy) * yc
                m0 = -ey["a1"] + ey["ppo"] * ey["yo0"] + ey["ppc"] * ey["yc0"]
                q = q + h * (m - m0)
            yo_, yc_ = _cet(ca, e, ratio(r, o), ratio(r, c))
            dm_ = (-e["a1"] * ratio(r, s) + e["ppo"] * ratio(r, o) * yo_ + e["ppc"] * ratio(r, c) * yc_) \
                - (-e["a1"] + e["ppo"] * e["yo0"] + e["ppc"] * e["yc0"])
            det.append(ca.horzcat(q - k * e["q0"], dm_))
            keys.append((r, s, e["rms"]))
            q = _fudge(ca, q, k * e["q0"])
            crush = crush + q
            oil = oil + q * yo_
            cake = cake + q * yc_
            oil0 += k * e["q0"] * e["yo0"]
            cake0 += k * e["q0"] * e["yc0"]
        rows.append(ca.horzcat(crush, p["q0"] * p["yo"] * (oil / oil0 if oil0 > 0 else 1.0),
                               p["q0"] * p["yc"] * (cake / cake0 if cake0 > 0 else 1.0)))
    out = ca.vertcat(*rows) if rows else ca.SX(0, 3)
    detail = ca.vertcat(*det) if det else ca.SX(0, 2)
    f = ca.Function("crush", [rat], [out, detail], ["rat"], ["out", "detail"])
    return f, regions, pairs, keys


def proc_nq_function(pq: dict, regions: List[str], commodities: List[str], skip: set, skip_price: set):
    """CasADi Function (PR[nR x nC], P0[cells]) -> P[cells]: the processing of the other products (demand.py's
    PROCESSING loop: ProcNQ_ with CAPRI's Hessian on the Armington price ratios, then ProcFudge_), for the cells
    (region row, commodity column) of pq's shares that it covers, in their order. `skip`: the processed commodities
    left out (the oilseeds, crushed in their own block, and ProcessingMixin._PROC_NQ_SKIP); `skip_price`: the prices
    left out of the Hessian's terms (the oilseeds'). P0 > 0 is the caller's condition, checked per call."""
    import casadi as ca
    R = {r: i for i, r in enumerate(regions)}
    Cc = {c: j for j, c in enumerate(commodities)}
    PR = ca.SX.sym("PR", len(regions), len(commodities))
    cells, terms = [], []
    for (reg, c), _shp in pq["share"].items():
        i, j = R.get(reg), Cc.get(c)
        if i is None or j is None or c in skip:
            continue
        Hra = pq["Ha"].get(reg, {})
        dq = 0.0
        for (x, y), hv in Hra.items():
            if x != c:
                continue
            jy = Cc.get(y)
            if jy is not None and y not in skip_price:
                dq = dq - hv * (PR[i, jy] - 1.0)
        cells.append((i, j))
        terms.append(dq)
    P0 = ca.SX.sym("P0", len(cells))
    P = ca.vertcat(*[_fudge(ca, P0[k] + terms[k], P0[k]) for k in range(len(cells))]) if cells else ca.SX(0, 1)
    f = ca.Function("proc_nq", [PR, P0], [P], ["PR", "P0"], ["P"])
    return f, cells
