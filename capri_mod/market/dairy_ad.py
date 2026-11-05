"""CAPRI's dairy blocks in CasADi: market programme step G2f (docs/design/MARKET_IPOPT_DESIGN.md sections 5-6).

Written once, here, and evaluated from here by DairyMixin (capri_mod/market/dairy.py: dairy_block for the member
states, _dairy_solve for the non-EU dairy regions): the project lead's choice of one implementation per block (section
7, 30 October 2026). One block (a member state, or the behavioural regions of a non-EU trade region sharing its price
ratios; DairyMixin._dairy_algebra), with z the price ratios - 1 of the nine products, raw milk, fat and protein
(arm/market_model.gms; their CAPRI references are in dairy.py's docstrings):

    ProcNQ_, ProcFudge_   dproc_k = fudge(proc0_k + sum_j D_kj z_j, proc0_k) - proc0_k    (per region of the block)
    FatsProtBal_          rowF z = - sum_k f_k dproc_k,  rowP z = - sum_k r_k dproc_k
    DairyNQ_ (MILK)       G_M z - kq z_M = mrhs     (the dairies' milk demand against the milk delivered)

kq the raw milk supply's slope on z_M (0 where the milk delivered is given: the EU's member states without the
response of audit M5; Q0 k with it; SM outside the EU), mrhs the delivered milk's change (kt). With fix = 1 the milk row
is replaced by z_M = zfix (a member state's price held at its lower bound, DairyMixin.MILK_PRICE_FLOOR). The unknowns u
= (z_FATS, z_PROT, z_MILK); the products' z are given (all nine traded since Sprint 9f). The system is linear in u, so
the default solve takes one Newton step from u = 0 with the function's Jacobian (solve_block); in G3 the residual is
the block's equations with u among the NLP's unknowns.

ProcFudge_ applies where the change is not exactly 0 (as dairy.py before the move: if_else, a jump of about 1e-11 kt at
a zero change, to be registered or removed in G3). Floating point: CasADi's sums run in their own order, so the values
differ from dairy.py's code before the move by rounding only (capri_mod/tests/test_dairy_ad.py measures it).
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np

from capri_mod.market.processing_ad import _fudge


def dairy_proc_parts(prm: dict, harms: Dict[str, dict], traded: Dict[str, str]) -> List[dict]:
    """The block's processing (ProcNQ_, audit M9) per region: D (items x z) the terms -h / INPE x ARM1P0 of the
    processing Hessian (harms {region: {(market code x, market code y): h}}, ProcessingMixin._proc_nq_params' Harms) for
    the products the region processes at base, its base processing, fat and protein contents."""
    mk = {c: k for k, c in traded.items()}
    ix = prm["ix"]
    n_it = len(prm["items"])
    out = []
    for part in prm.get("parts") or ():
        hr = harms.get(part["rms"])
        if not hr:
            continue
        D = np.zeros((n_it, n_it + 2))
        for (x, y), hv in hr.items():
            kx, ky = mk.get(x), mk.get(y)
            if kx is None or kx not in ix or ky is None or ky not in ix:
                continue
            i = ix[kx]
            if part["proc0"][i] <= 0:
                continue
            D[i, ix[ky]] -= float(hv)
        out.append({"D": D, "proc0": np.asarray(part["proc0"], float), "f": np.asarray(part["f"], float),
                    "r": np.asarray(part["r"], float)})
    return out


def dairy_block_function(name: str, prm: dict, parts: List[dict]):
    """CasADi Function (zt[n], u[3], kq, mrhs, fix, zfix) -> (res[3], J[3x3], z[n], q[n_it], dproc[n_it]): the block's
    equations at the products' z (zt; its fat, protein and milk entries are replaced by u), their Jacobian in u, the
    full z, the block's output Q0 + G z (DairyNQ_) and its processing change."""
    import casadi as ca
    n_it = len(prm["items"])
    n = n_it + 2
    iF, iP, iM = prm["iF"], prm["iP"], prm["iM"]
    zt, u = ca.SX.sym("zt", n), ca.SX.sym("u", 3)
    kq, mrhs, fix, zfix = ca.SX.sym("kq"), ca.SX.sym("mrhs"), ca.SX.sym("fix"), ca.SX.sym("zfix")
    z = ca.SX(zt)
    z[iF], z[iP], z[iM] = u[0], u[1], u[2]
    dproc = ca.SX.zeros(n_it)
    rF = rP = ca.SX(0.0)
    for p in parts:
        dr = ca.mtimes(ca.DM(p["D"]), zt)
        d = ca.SX.zeros(n_it)
        for i in np.nonzero(np.any(p["D"] != 0.0, axis=1))[0]:
            q0 = float(p["proc0"][i])
            d[int(i)] = ca.if_else(dr[int(i)] != 0, _fudge(ca, q0 + dr[int(i)], q0) - q0, 0.0)
        dproc = dproc + d
        rF = rF - ca.dot(ca.DM(p["f"]), d)
        rP = rP - ca.dot(ca.DM(p["r"]), d)
    G = np.asarray(prm["G"], float)
    resF = ca.dot(ca.DM(np.asarray(prm["rowF"], float)), z) - rF
    resP = ca.dot(ca.DM(np.asarray(prm["rowP"], float)), z) - rP
    resM = (1.0 - fix) * (ca.dot(ca.DM(G[iM]), z) - kq * z[iM] - mrhs) + fix * (z[iM] - zfix)
    res = ca.vertcat(resF, resP, resM)
    q = ca.DM(np.asarray(prm["Q0"], float)) + ca.mtimes(ca.DM(G), z)
    return ca.Function(name, [zt, u, kq, mrhs, fix, zfix], [res, ca.jacobian(res, u), z, q, dproc],
                       ["zt", "u", "kq", "mrhs", "fix", "zfix"], ["res", "J", "z", "q", "dproc"])


def solve_block(f, zt: np.ndarray, kq: float = 0.0, mrhs: float = 0.0, fix: float = 0.0, zfix: float = 0.0) -> dict:
    """The block's unknowns at the given prices: one Newton step from u = 0 (the equations are linear in u). Returns
    {u, z, q, dproc, residual (largest absolute value of the equations at u)}."""
    a = (zt, np.zeros(3), float(kq), float(mrhs), float(fix), float(zfix))
    r0, J = f(*a)[:2]
    u = np.linalg.solve(np.asarray(J, float), -np.asarray(r0, float).ravel())
    res, _, z, q, dproc = f(zt, u, *a[2:])
    return {"u": u, "z": np.asarray(z, float).ravel(), "q": np.asarray(q, float).ravel(),
            "dproc": np.asarray(dproc, float).ravel(), "residual": float(np.max(np.abs(np.asarray(res, float))))}
