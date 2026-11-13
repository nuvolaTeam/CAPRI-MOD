"""Step G2c: CAPRI's GL human consumption in CasADi (capri_mod/market/demand_ad.py) equals the equations as NumPy had
them until 31 October 2026 (written out here as the reference), and its Jacobian equals finite differences."""
import numpy as np
import pytest


def _gl_numpy(e, p, ir):
    """The NumPy form of demand.py before the move (DemandMixin._gl_eval)."""
    sq = np.sqrt(p)
    G = float(sq @ e["B"] @ sq)
    Gi = (e["B"] @ sq) / sq
    F = float(e["d"] @ p)
    return (Gi / G * (e["Y"] * ir - F) + e["d"]) * e["inha"] / 1000.0


def _num_numpy(prm, regions, PR, ir):
    """gl_food_ratio's loop before the move: the sums per (model region, commodity)."""
    Rr = {r: i for i, r in enumerate(regions)}
    num = np.zeros_like(PR, dtype=float)
    for mr, ents in prm["groups"].items():
        i = Rr[mr]
        for e in ents:
            col = e["col"]
            p = e["p0"].copy()
            m = col >= 0
            p[m] = p[m] + (PR[i, col[m]] - 1.0) * e["arm1p"][m]
            p = np.maximum(p, 0.05 * e["p0"])
            x = _gl_numpy(e, p, ir)
            np.add.at(num[i], col[m], np.maximum(x[m], 0.0))
    return num


@pytest.fixture(scope="module")
def market(solved_market):
    """The market after one baseline iteration on DE110000 and FR100000 (conftest.py)."""
    return solved_market


def test_gl_entry_matches_numpy(market):
    from capri_mod.market.demand_ad import gl_eval
    prm = market._gl_params()
    rng = np.random.default_rng(3)
    worst, n = 0.0, 0
    for ents in prm["groups"].values():
        for e in ents:
            p = e["p0"] * np.exp(rng.normal(0, 0.1, len(e["p0"])))
            ir = float(np.exp(rng.normal(0, 0.05)))
            a, b = gl_eval(e, p, ir), _gl_numpy(e, p, ir)
            rel = np.abs(a - b) / np.maximum(np.abs(b), 1e-6)
            worst = max(worst, float(rel.max()))
            n += 1
    assert n >= 50
    assert worst < 1e-11, worst


def test_gl_block_matches_numpy_and_its_jacobian(market):
    import casadi as ca
    from capri_mod.market.demand_ad import gl_block_function
    prm = market._gl_params()
    regions = list(market.regions)
    nC = len(market.commodities)
    rng = np.random.default_rng(4)
    PR = np.exp(rng.normal(0, 0.08, (len(regions), nC)))
    fn, cells, slices = gl_block_function(prm["groups"], regions, nC)
    dcat = np.concatenate([e["d"] for mr in prm["groups"] for e in prm["groups"][mr]])
    h = np.asarray(fn(PR, 1.02, dcat)[0]).ravel()
    ref = _num_numpy(prm, regions, PR, 1.02)
    got = np.zeros_like(ref)
    for (i, j), v in zip(cells, h):
        got[i, j] = v
    assert np.allclose(got, ref, rtol=1e-11, atol=1e-9)
    # every cell with a positive reference sum is one of the block's cells
    assert set(zip(*np.nonzero(ref))) <= set(cells)
    # the exact Jacobian in PR against central differences on a few cells
    P = ca.MX.sym("P", len(regions), nC)
    J = ca.Function("J", [P], [ca.jacobian(fn(P, 1.02, dcat)[0], ca.vec(P))])
    Jv = np.asarray(J(PR))
    picks = [k for k in range(len(cells)) if k % max(1, len(cells) // 15) == 0][:15]
    for k in picks:
        i, j = cells[k]
        for jj in sorted({j, (j + 1) % nC}):
            col = jj * len(regions) + i                  # ca.vec is column-major
            hstep = 1e-6
            Pp, Pm = PR.copy(), PR.copy()
            Pp[i, jj] += hstep
            Pm[i, jj] -= hstep
            fd = (np.asarray(fn(Pp, 1.02, dcat)[0]).ravel()[k] - np.asarray(fn(Pm, 1.02, dcat)[0]).ravel()[k]) / (2 * hstep)
            assert abs(Jv[k, col] - fd) <= 1e-5 * max(1.0, abs(fd)), (cells[k], jj, Jv[k, col], fd)


def test_gl_food_ratio_uses_the_block(market):
    """The model's call (DemandMixin.gl_food_ratio) gives the NumPy loop's ratios."""
    prm = market._gl_params()
    regions = list(market.regions)
    rng = np.random.default_rng(5)
    PR = np.exp(rng.normal(0, 0.05, (len(regions), len(market.commodities))))
    GLR, HS = market.gl_food_ratio(PR, None, 0.98)
    num = _num_numpy(prm, regions, PR, 0.98)
    Rr = {r: i for i, r in enumerate(regions)}
    for (mr, j), v0 in prm["x0"].items():
        if v0 > 0:
            assert abs(GLR[Rr[mr], j] - num[Rr[mr], j] / v0) <= 1e-11 * max(1.0, abs(GLR[Rr[mr], j]))
