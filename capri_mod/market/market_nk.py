"""MarketModule: the market's simultaneous solve by Newton-Krylov (market programme step G2, the project lead's choice
of 29 October 2026; docs/design/ARCHITECTURE_REFACTOR.md section 6, G).

CAPRI solves its market model as one simultaneous system (CONOPT on arm/market_model.gms). capri-mod's default solve
(BilateralSolveMixin._solve_bilateral) is a successive linearisation: each step re-evaluates the full model response
(supply functions, processing, dairy blocks, feed, biofuels, young animals) and solves each commodity's trade system
exactly with supply and use log-linear around that point; the links across commodities and blocks enter only between
steps (Anderson mixing accelerates them). This module solves the same equations at once:

    R(z) = 0,   z = log r (the producer price ratios the default solve moves),
    R    = each commodity's market-clearing residual (BilateralCommodity.residual; a pooled commodity's world balance),
           divided by the same scale as the default solve (S0 + D0, at least 1),

by Newton's method with the Jacobian-vector products taken as directional finite differences of R (one evaluation of
the full model response each), solved by GMRES, preconditioned by the block-diagonal Jacobian of the default solve's
own model (each commodity's trade system with the local supply and use elasticities, exact from CasADi, trade_ad.py;
a pooled commodity's scalar slope). The first Krylov iterate is therefore the default solve's step; further
iterates add the links across commodities and blocks. A backtracking line search on |R|_2 keeps each step a descent
step; the step clip of the default solve applies.

Departure from the agreed design (registered in docs/DEPARTURES_FROM_CAPRI.md, "Beyond CAPRI: options"): the
derivatives across blocks are finite differences, not CasADi expressions of every block. The equations and the
stopping rule are the default solve's (every relative residual and every quota move below market.tol), so the
equilibrium is the same; the path differs.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from capri_mod.settings import current as _settings


class NewtonKrylovMixin:
    """MarketModule methods for the Newton-Krylov market solve (setting market.solver = "newton_krylov")."""

    def _nk_layout(self, r: pd.DataFrame, sysd) -> List[Tuple[str, np.ndarray]]:
        """The unknowns: per commodity the regions the default solve moves (the supplying regions of a bilateral
        commodity; the common ratio of a pooled one, index -1)."""
        out = []
        for c in r.columns:
            if c in sysd:
                act = np.where(sysd[c].S0 > 1e-6)[0]
                if len(act):
                    out.append((c, act))
            else:
                out.append((c, np.array([-1])))
        return out

    def _nk_solve(self, r, exogenous_supply, trade_scenario, es, ed, size, tol, max_outer, verbose=False):
        """Newton-Krylov on R(log r) = 0 from r; returns as _solve_bilateral."""
        from scipy.sparse.linalg import LinearOperator, gmres
        from capri_mod.market.trade_ad import trade_function, import_price_matrices

        st = _settings()
        sclip = tuple(st.get("market.step_clip"))
        h = float(st.get("market.nk_fd_step"))
        kmax = int(st.get("market.nk_max_krylov"))
        sysd = self.par.bilat
        tadd = self._tariff_adds(trade_scenario)
        lay = self._nk_layout(r, sysd)
        offs = np.cumsum([0] + [len(a) for _, a in lay])
        n = int(offs[-1])
        cols = list(r.columns)
        ci = {c: cols.index(c) for c in cols}

        def pack(rr: pd.DataFrame) -> np.ndarray:
            a = rr.to_numpy(dtype=float)
            z = np.empty(n)
            for k, (c, act) in enumerate(lay):
                v = a[:, ci[c]]
                z[offs[k]:offs[k + 1]] = np.log(v[0:1] if act[0] < 0 else v[act])
            return z

        def unpack(z: np.ndarray, base: pd.DataFrame) -> pd.DataFrame:
            a = base.to_numpy(dtype=float, copy=True)
            for k, (c, act) in enumerate(lay):
                v = np.exp(z[offs[k]:offs[k + 1]])
                if act[0] < 0:
                    a[:, ci[c]] = v[0]
                else:
                    a[act, ci[c]] = v
            return pd.DataFrame(a, index=base.index, columns=base.columns)

        def resid(rr: pd.DataFrame):
            S, D, PAr, F, pc = self._bilateral_eval(rr, exogenous_supply, trade_scenario)
            g = np.empty(n)
            for k, (c, act) in enumerate(lay):
                sz = size(c)
                g[offs[k]:offs[k + 1]] = (F[c] / sz) if act[0] < 0 else (F[c][act] / sz[act])
            return g, (S, D, PAr, F, pc)

        frozen = np.zeros(n, dtype=bool)                       # the unknowns held (precond_blocks marks them)

        def precond_blocks(rr, S, D, PAr):
            """The default solve's Jacobian per commodity at rr, as LU-ready dense blocks."""
            frozen[:] = False
            blocks = []
            for k, (c, act) in enumerate(lay):
                if act[0] < 0:
                    s_, d_ = float(S[c].sum()), float(D[c].sum())
                    e_s = float((S[c] * es[c]).sum() / max(s_, 1e-9))
                    e_d = float((D[c] * ed[c]).sum() / max(d_, 1e-9))
                    if not (s_ > 0 and d_ > 0 and (e_s - e_d) > 1e-6):
                        # the default solve's own test (it moves a pooled ratio only when supply and use answer to
                        # it): a ratio no quantity answers to is not determined by the equations; it is held
                        frozen[offs[k]] = True
                        blocks.append(np.array([[1.0]]))
                        continue
                    blocks.append(np.array([[(s_ * e_s - d_ * e_d) / float(size(c)[0])]]))
                    continue
                sc = sysd[c]
                Am, Bm = import_price_matrices(sc, tadd.get(c))
                fn = trade_function(sc, act)
                rk = rr[c].to_numpy(dtype=float)
                pars = [Am, Bm, S[c].to_numpy(float), D[c].to_numpy(float), rk,
                        PAr[c].to_numpy(float) * sc.PA0, es[c].to_numpy(float), ed[c].to_numpy(float),
                        np.maximum(sc.S0 + sc.D0, 1.0)[act]]
                _, J = fn(np.log(rk[act]), *pars)
                blocks.append(np.asarray(J, float))
            return blocks

        def apply_prec(blocks, v):
            out = np.empty_like(v)
            for k, B in enumerate(blocks):
                seg = v[offs[k]:offs[k + 1]]
                try:
                    out[offs[k]:offs[k + 1]] = np.linalg.solve(B, seg)
                except np.linalg.LinAlgError:
                    out[offs[k]:offs[k + 1]] = np.linalg.lstsq(B, seg, rcond=None)[0]
            return out

        z = pack(r)
        g, ev = resid(r)
        converged = False
        it = 0
        n_evals = 1
        for it in range(max_outer):
            S, D, PAr, F, pc = ev
            err = float(np.max(np.abs(g))) if n else 0.0
            errs = {c: float(np.max(np.abs(F[c] / size(c)))) for c in F}
            self._bilat_errs = errs
            # EU tariff-rate quotas: the out-of-quota tariff follows the fill at the current flows, as the default solve
            trq_moved = 0.0
            for c, sc in sysd.items():
                if sc.trq_row is None:
                    continue
                X, _ = sc.flows(D[c].values, r[c].values, pc[c])
                old = sc.trq_offset.copy()
                sc.trq_solve(X, pc[c])
                trq_moved = max(trq_moved, float(np.max(np.abs(sc.trq_offset - old)
                                                        / np.maximum(float(np.min(sc.Pd0[sc._rows()])), 1.0))))
            if verbose:
                print(f"  market Newton-Krylov step {it}: max rel residual {err:.2e}, evaluations {n_evals}")
            if max(errs.values()) < tol and trq_moved < tol:
                converged = True
                break
            if trq_moved > 0:
                g, ev = resid(r)                                   # the quotas moved: the residual at the new tariffs
                n_evals += 1
                S, D, PAr, F, pc = ev
            blocks = precond_blocks(r, S, D, PAr)
            g0 = g.copy()

            def jv(v):
                """J v on the free unknowns; the identity on the held ones (their step is 0: right-hand side 0)."""
                nonlocal n_evals
                vf = np.where(frozen, 0.0, v)
                nv = float(np.linalg.norm(vf))
                if nv == 0:
                    return np.where(frozen, v, 0.0)
                eps = h / nv
                g1, _ = resid(unpack(z + eps * vf, r))
                n_evals += 1
                return np.where(frozen, v, (g1 - g0) / eps)
            J = LinearOperator((n, n), matvec=jv, dtype=float)
            M = LinearOperator((n, n), matvec=lambda v: apply_prec(blocks, v), dtype=float)
            rhs = np.where(frozen, 0.0, -g0)
            eta = min(0.1, max(float(np.linalg.norm(rhs)), 1e-3))
            try:
                dz, info = gmres(J, rhs, M=M, rtol=eta, restart=kmax, maxiter=1)
            except TypeError:                                      # SciPy before 1.12 names the tolerance tol
                dz, info = gmres(J, rhs, M=M, tol=eta, restart=kmax, maxiter=1)
            dz = np.where(frozen, 0.0, dz)
            if not np.all(np.isfinite(dz)):
                dz = np.where(frozen, 0.0, -apply_prec(blocks, g0))   # the default solve's step
            dz = np.clip(dz, np.log(sclip[0]), np.log(sclip[1]))
            # backtracking line search on |R|_2 (Armijo, c = 1e-4)
            f0 = float(np.dot(g0, g0))
            t, acc = 1.0, False
            while t >= 1.0 / 32:
                rt = unpack(z + t * dz, r)
                gt, evt = resid(rt)
                n_evals += 1
                if np.all(np.isfinite(gt)) and float(np.dot(gt, gt)) <= (1.0 - 1e-4 * t) * f0:
                    acc = True
                    break
                t *= 0.5
            if not acc:
                # no descent along the Newton direction: the default solve's (preconditioner) step, damped
                dz = np.clip(np.where(frozen, 0.0, -apply_prec(blocks, g0)), np.log(sclip[0]), np.log(sclip[1]))
                rt = unpack(z + 0.5 * dz, r)
                gt, evt = resid(rt)
                n_evals += 1
                t = 0.5
            z = z + t * dz
            r, g, ev = rt, gt, evt
        S, D, PAr, F, pc = ev
        self._bilat_err = float(max((float(np.max(np.abs(F[c] / size(c)))) for c in F), default=0.0))
        self.sv.bilat_last_r = r.copy()
        self._nk_evals = n_evals
        return r, S, D, PAr, pc, converged, it + 1
