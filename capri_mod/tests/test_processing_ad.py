"""Step G2e: CAPRI's processing demand in CasADi (capri_mod/market/processing_ad.py) equals the Python code it replaced
on 31 October 2026 (written out here as the reference: ProcessingMixin._crush_state and demand_response's ProcNQ_
loop), and its Jacobian equals finite differences."""
import numpy as np
import pandas as pd
import pytest


def _cet_yields(e, ro, rc):
    """ProcessingMixin._cet_yields before the move (procYield_, closed form)."""
    po, pc = e["ppo"] * ro, e["ppc"] * rc
    lo = np.log(((po + 1e-3) / (e["ppo"] + 1e-3)) / ((pc + 1e-3) / (e["ppc"] + 1e-3)))
    Ao = e["yo0"] * np.exp(e["rho"] * lo)
    Ac = e["yc0"] * np.exp(-e["rho"] * lo)
    S0 = e["yo0"] + e["yc0"]
    T = (Ao + Ac + S0) / 2.0
    return Ao + (S0 - T) / 2.0, Ac + (S0 - T) / 2.0


def _proc_fudge(q, q0):
    """ProcessingMixin._proc_fudge before steps G2e and G2f (CAPRI's ProcFudge_, market_model.gms l. 1158-1163)."""
    z = 0.01 * min(1000.0, max(1e-11, float(q0)))
    return float(q + z * np.logaddexp(0.0, -q / z) + 1e-11)


def _crush_state_python(mk, dom_prices, detail=None):
    """ProcessingMixin._crush_state before the move (with _cet_yields above and _proc_fudge)."""
    cp = mk._crush_params()
    pq = mk._proc_nq_params() or {}
    seeds = pq.get("seeds", {})
    Hrms = pq.get("Hrms", {})
    d0 = mk._dom0()
    _ri = {r: i for i, r in enumerate(dom_prices.index)}
    _ci = {c: j for j, c in enumerate(dom_prices.columns)}
    _v = dom_prices.values
    _d0 = d0.reindex(index=dom_prices.index, columns=dom_prices.columns).values
    ratio = lambda r, x: float(_v[_ri[r], _ci[x]]) / float(_d0[_ri[r], _ci[x]]) if float(_d0[_ri[r], _ci[x]]) > 0 else 1.0
    out = {}
    for (r, s), p in cp.items():
        o, c = mk.CRUSH_CHAINS[s]
        ents = seeds.get((r, s), [])
        if not ents:
            out[(r, s)] = (p["q0"], p["q0"] * p["yo"], p["q0"] * p["yc"])
            continue
        k = p["q0"] / sum(e["q0"] for e in ents)
        crush = oil = cake = oil0 = cake0 = 0.0
        for e in ents:
            Hr = Hrms.get(r, {}).get(e["rms"], {})
            q = k * e["q0"]
            for y in mk.CRUSH_CHAINS:
                h = Hr.get((s, y), 0.0)
                if h == 0.0:
                    continue
                ey = next((x for x in seeds.get((r, y), []) if x["rms"] == e["rms"]), None)
                if ey is None:
                    continue
                oy, cy = mk.CRUSH_CHAINS[y]
                yo, yc = _cet_yields(ey, ratio(r, oy), ratio(r, cy))
                m = -ey["a1"] * ratio(r, y) + ey["ppo"] * ratio(r, oy) * yo + ey["ppc"] * ratio(r, cy) * yc
                m0 = -ey["a1"] + ey["ppo"] * ey["yo0"] + ey["ppc"] * ey["yc0"]
                q += h * (m - m0)
            if detail is not None:
                yo_, yc_ = _cet_yields(e, ratio(r, o), ratio(r, c))
                dm_ = (-e["a1"] * ratio(r, s) + e["ppo"] * ratio(r, o) * yo_ + e["ppc"] * ratio(r, c) * yc_) \
                    - (-e["a1"] + e["ppo"] * e["yo0"] + e["ppc"] * e["yc0"])
                detail[(r, s, e["rms"])] = (k * e["q0"], q - k * e["q0"], dm_)
            q = _proc_fudge(q, k * e["q0"])
            yo, yc = _cet_yields(e, ratio(r, o), ratio(r, c))
            crush += q
            oil += q * yo
            cake += q * yc
            oil0 += k * e["q0"] * e["yo0"]
            cake0 += k * e["q0"] * e["yc0"]
        out[(r, s)] = (crush, p["q0"] * p["yo"] * (oil / oil0 if oil0 > 0 else 1.0),
                       p["q0"] * p["yc"] * (cake / cake0 if cake0 > 0 else 1.0))
    return out


def _proc_nq_python(mk, PR, P0):
    """demand_response's ProcNQ_ loop before the move (REF > 0, so DP / REF = PR)."""
    R = {r: i for i, r in enumerate(mk.regions)}
    Cc = {c: j for j, c in enumerate(mk.commodities)}
    pq = mk._proc_nq_params()
    P = P0.copy()
    for (reg, c), _shp in pq["share"].items():
        i, j = R.get(reg), Cc.get(c)
        if i is None or j is None or c in mk.CRUSH_CHAINS or c in mk._PROC_NQ_SKIP or P0[i, j] <= 0:
            continue
        Hra = pq["Ha"].get(reg, {})
        dq = 0.0
        for (x, y), hv in Hra.items():
            if x != c:
                continue
            jy = Cc.get(y)
            if jy is not None and y not in mk.CRUSH_CHAINS:
                dq -= hv * (PR[i, jy] - 1.0)
        P[i, j] = _proc_fudge(P0[i, j] + dq, P0[i, j])
    return P


@pytest.fixture(scope="module")
def market(solved_market):
    """The market after one baseline iteration on DE110000 and FR100000 (conftest.py)."""
    return solved_market


def _rel(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return float(np.max(np.abs(a - b) / np.maximum(np.abs(b), 1e-9))) if a.size else 0.0


def test_crush_state_matches_python(market):
    rng = np.random.default_rng(11)
    d0 = market._dom0()
    worst = 0.0
    for _ in range(5):
        dp = d0 * np.exp(rng.normal(0, 0.1, d0.shape))
        det_a, det_b = {}, {}
        a = market._crush_state(dp, detail=det_a)
        b = _crush_state_python(market, dp, detail=det_b)
        assert set(a) == set(b) and set(det_a) == set(det_b)
        worst = max(worst, _rel([a[k] for k in b], [b[k] for k in b]),
                    _rel([det_a[k] for k in det_b], [det_b[k] for k in det_b]))
    assert len(b) >= 3 and len(det_b) >= 3
    assert worst < 1e-12, worst


def test_proc_nq_matches_python_and_its_jacobian(market):
    import casadi as ca
    from capri_mod.market.processing_ad import proc_nq_function
    rng = np.random.default_rng(12)
    nR, nC = len(market.regions), len(market.commodities)
    PR = np.exp(rng.normal(0, 0.1, (nR, nC)))
    P0 = np.abs(rng.normal(100, 50, (nR, nC)))
    fn, cells = proc_nq_function(market._proc_nq_params(), list(market.regions), list(market.commodities),
                                 set(market.CRUSH_CHAINS) | set(market._PROC_NQ_SKIP), set(market.CRUSH_CHAINS))
    assert len(cells) >= 10
    p0c = np.array([P0[i, j] for i, j in cells])
    got = np.asarray(fn(PR, p0c)).ravel()
    ref = _proc_nq_python(market, PR, P0)
    assert _rel(got, [ref[i, j] for i, j in cells]) < 1e-13
    X = ca.SX.sym("X", nR, nC)
    J = ca.Function("J", [X], [ca.jacobian(fn(X, p0c), ca.vec(X))])
    Jv = np.asarray(J(PR))
    for k in range(0, len(cells), max(1, len(cells) // 10)):
        for col in np.nonzero(Jv[k])[0][:3]:
            j, i = divmod(int(col), nR)
            h = 1e-6
            Pp, Pm = PR.copy(), PR.copy()
            Pp[i, j] += h
            Pm[i, j] -= h
            fd = (np.asarray(fn(Pp, p0c)).ravel()[k] - np.asarray(fn(Pm, p0c)).ravel()[k]) / (2 * h)
            assert abs(Jv[k, col] - fd) <= 1e-5 * max(1.0, abs(fd))


def test_crush_jacobian(market):
    import casadi as ca
    from capri_mod.market.processing_ad import crush_function
    pq = market._proc_nq_params()
    fn, regions, pairs, keys = crush_function(market._crush_params(), pq["seeds"], pq["Hrms"], market.CRUSH_CHAINS)
    rng = np.random.default_rng(13)
    rat = np.exp(rng.normal(0, 0.1, (len(regions), 9)))
    X = ca.SX.sym("X", len(regions), 9)
    J = ca.Function("J", [X], [ca.jacobian(ca.vec(fn(X)[0]), ca.vec(X))])
    Jv = np.asarray(J(rat))
    base = np.asarray(fn(rat)[0]).ravel(order="F")
    for col in range(0, Jv.shape[1], 3):
        h = 1e-6
        rp, rm = rat.copy(), rat.copy()
        j, i = divmod(col, len(regions))
        rp[i, j] += h
        rm[i, j] -= h
        fd = (np.asarray(fn(rp)[0]).ravel(order="F") - np.asarray(fn(rm)[0]).ravel(order="F")) / (2 * h)
        assert np.allclose(Jv[:, col], fd, rtol=1e-5, atol=1e-6 * max(1.0, float(np.abs(base).max())))
