"""Step G2f: CAPRI's dairy blocks in CasADi (capri_mod/market/dairy_ad.py) equal the code dairy.py had until 4 November
2026 (written out here as the reference: _dairy_proc_change, the member states' three solves and the non-EU block's
solve), and their Jacobian is the equations' matrix."""
import numpy as np
import pytest

from capri_mod.tests.test_processing_ad import _proc_fudge


def _proc_change_ref(mm, dp, zt):
    """DairyMixin._dairy_proc_change before the move: (dproc, fat row's right-hand side, protein row's)."""
    n_it = len(dp["items"])
    dproc = np.zeros(n_it)
    rF = rP = 0.0
    H = (mm._proc_nq_params() or {}).get("Harms") or {}
    if not H:
        return dproc, rF, rP
    mk = {c: k for k, c in mm.DAIRY_TRADED.items()}
    ix = dp["ix"]
    for part in dp.get("parts") or ():
        hr = H.get(part["rms"])
        if not hr:
            continue
        d = np.zeros(n_it)
        for (x, y), hv in hr.items():
            kx, ky = mk.get(x), mk.get(y)
            if kx is None or kx not in ix or ky is None or ky not in ix:
                continue
            i = ix[kx]
            if part["proc0"][i] <= 0:
                continue
            d[i] -= hv * float(zt[ix[ky]])
        for i in np.nonzero(d)[0]:
            q0 = float(part["proc0"][i])
            d[i] = _proc_fudge(q0 + d[i], q0) - q0
        dproc += d
        rF -= float(part["f"] @ d)
        rP -= float(part["r"] @ d)
    return dproc, rF, rP


def _solve_ref(prm, zt, rfp, kq=0.0, mrhs=0.0, zfix=None):
    """_dairy_solve_ms (kq = 0), _dairy_solve_ms_resp, _dairy_solve_ms_at (zfix given) and the linear solve of
    _dairy_solve (kq = SM) before the move."""
    iF, iP, iM = prm["iF"], prm["iP"], prm["iM"]
    if zfix is not None:
        z = zt.copy()
        z[iM] = zfix
        A = np.vstack([prm["rowF"], prm["rowP"]])
        z[[iF, iP]] = np.linalg.solve(A[:, [iF, iP]], np.array(rfp) - A @ z + A[:, [iF, iP]] @ z[[iF, iP]])
        return z
    unk = [iF, iP, iM]
    mrow = prm["G"][iM].copy()
    mrow[iM] -= kq
    A = np.vstack([prm["rowF"], prm["rowP"], mrow])
    z = zt.copy()
    z[unk] = np.linalg.solve(A[:, unk], np.array([rfp[0], rfp[1], mrhs]) - A @ zt)
    return z


@pytest.fixture(scope="module")
def market():
    from pathlib import Path
    from capri_mod.data.loaders import load_all_data
    from capri_mod.market.market_module import MarketModule
    return MarketModule(load_all_data(Path(__file__).resolve().parents[2] / "capri_data"))


def _zt(mm, prm, rng):
    zt = np.zeros(len(prm["items"]) + 2)
    for k in mm.DAIRY_TRADED:
        if k in prm["ix"]:
            zt[prm["ix"][k]] = 0.25 * rng.standard_normal()
    return zt


def _close(a, b, tol):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return float(np.max(np.abs(a - b) / np.maximum(np.abs(b), 1.0))) <= tol


@pytest.mark.parametrize("seed", [0, 1])
def test_member_state_blocks_equal_the_former_solves(market, seed):
    mm = market
    rng = np.random.default_rng(seed)
    n = 0
    for ms, prm in mm._dairy_params()["ms"].items():
        zt = _zt(mm, prm, rng)
        dpr, rF, rP = _proc_change_ref(mm, prm, zt)
        assert _close(mm._dairy_proc_change(prm, zt), dpr, 1e-12), ms
        Q0 = float(prm["Q0"][prm["iM"]])
        mr = 1.0 + 0.1 * rng.standard_normal()
        s = mm._dairy_solve_ms(prm, zt, mr)
        assert _close(s["z"], _solve_ref(prm, zt, (rF, rP), mrhs=Q0 * (mr - 1.0)), 1e-12), ms
        assert _close(s["q"], prm["Q0"] + prm["G"] @ s["z"], 1e-12) and _close(s["dproc"], dpr, 1e-12)
        k, L = rng.uniform(0.0, 1.0), 1.0 + 0.1 * rng.standard_normal()
        s = mm._dairy_solve_ms_resp(prm, zt, mr, k, L)
        ref = _solve_ref(prm, zt, (rF, rP), kq=Q0 * k, mrhs=Q0 * (mr - 1.0) + Q0 * k * (1.0 - L))
        assert _close(s["z"], ref, 1e-12), ms
        s = mm._dairy_solve_ms_at(prm, zt, mm.MILK_PRICE_FLOOR)
        assert _close(s["z"], _solve_ref(prm, zt, (rF, rP), zfix=mm.MILK_PRICE_FLOOR - 1.0), 1e-12), ms
        n += 1
    assert n >= 26


def test_world_blocks_equal_the_former_solve(market):
    mm = market
    rng = np.random.default_rng(9)
    n = 0
    for r, prm in mm._dairy_world_params().items():
        tr = {k: float(np.exp(0.2 * rng.standard_normal())) for k in mm.DAIRY_TRADED}
        zt = np.zeros(len(prm["items"]) + 2)
        for k, v in tr.items():
            if k in prm["ix"]:
                zt[prm["ix"][k]] = v - 1.0
        dpr, rF, rP = _proc_change_ref(mm, prm, zt)
        sh = 0.05 * prm["Q0"][prm["iM"]] * rng.standard_normal()
        x = mm._dairy_solve(prm, tr, None, 1.0, milk_shift=sh)
        ref = _solve_ref(prm, zt, (rF, rP), kq=prm["SM"], mrhs=sh)
        assert _close(x["z"], ref, 1e-12), r
        assert x["residual"] < 1e-8 * max(1.0, prm["Q0"][prm["iM"]]), r
        Q = prm["Q0"] + prm["G"] @ ref
        for k, c in mm.DAIRY_TRADED.items():
            i = prm["ix"][k]
            assert abs(x["market_supply"][c] - (Q[i] - prm["proc0"][i] - dpr[i])) <= 1e-8 * max(1.0, abs(Q[i])), (r, c)
        assert abs(x["milk_supply_ratio"] - (1.0 + (prm["SM"] * ref[prm["iM"]] + sh) / prm["Q0"][prm["iM"]])) < 1e-10
        n += 1
    assert n >= 5


def test_block_jacobian_is_the_equations_matrix(market):
    """The residual is linear in the unknowns: its Jacobian is the rows' coefficients on (z_FATS, z_PROT, z_MILK), with
    the raw milk supply's slope on the milk row, and the milk row replaced by z_MILK = zfix where the price is held."""
    mm = market
    for ms, prm in list(mm._dairy_params()["ms"].items())[:5]:
        f = mm._dairy_fn(prm)
        unk = [prm["iF"], prm["iP"], prm["iM"]]
        A = np.vstack([prm["rowF"], prm["rowP"], prm["G"][prm["iM"]]])[:, unk]
        A[2, 2] -= 7.0
        J = np.asarray(f(np.zeros(len(prm["items"]) + 2), np.zeros(3), 7.0, 0.0, 0.0, 0.0)[1])
        assert np.allclose(J, A, rtol=1e-14, atol=0.0)
        J = np.asarray(f(np.zeros(len(prm["items"]) + 2), np.zeros(3), 7.0, 0.0, 1.0, -0.5)[1])
        assert np.allclose(J[:2], A[:2], rtol=1e-14, atol=0.0) and np.array_equal(J[2], [0.0, 0.0, 1.0])
