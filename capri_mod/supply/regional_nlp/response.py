r"""The regional NLP's sensitivity of the solution and its results in the regional QP's terms (moved from
capri_mod/supply/capri_regional_nlp.py as they were, 26 November 2026).
"""
from __future__ import annotations

import hashlib
import os
from collections import OrderedDict

import numpy as np

from capri_mod.settings import current as _settings   # the numerical settings
from capri_mod.supply.regional_nlp.feed_terms import _AtP  # noqa: E402
from capri_mod.supply.regional_nlp.solver_options import _BLOCKS, _KKT, _SENS, _cache_max  # noqa: E402


class ResponseBlock:
    """CapriRegionalNLP's response, KKT record and step, manure values, objective parts and outputs."""

    # ---------------- sensitivity of the solution ----------------
    def response(self, res, D, tol=1e-9):
        """The solution's first-order response to linear changes of the objective (implicit function theorem on the
        KKT conditions at res): for each column d of D (n0 x k, a change of the linear cost of the regional QP's
        columns y per unit of a parameter), dy (n0 x k). Active set from IPOPT's solution: rows and variable bounds
        within 1e-6 of their bound with a multiplier above tol, equalities and fixed variables always; the reduced
        system solved in the active rows' null space Z: dX_F = -Z (Z' H_FF Z)^-1 Z' d_F (H the Lagrangian's Hessian, J the
        rows' Jacobian, in the scaled variables). Used for the young-animal markets' price update (CAPRIModel._update_young_animal_prices):
        the response of the whole regional model, feed, land, nutrient rows and split bounds included, where the PMP
        terms alone give the unconstrained response."""
        import casadi as ca
        key = self.graph_key()
        fn = _SENS.get(key)
        if fn is None:
            d = self._derivatives()
            jac = ca.Function("jac_g", [self.X, self.p], [ca.jacobian(self.g, self.X)])
            fn = (d["hess_lag"], jac)
            _SENS[key] = fn
            while len(_SENS) > int(_settings().get("run.nlp_derivative_cache_size")):
                _SENS.popitem(last=False)
        hess, jac = fn
        x = np.asarray(res["x"], float).ravel()
        lg = np.asarray(res["lam_g"], float).ravel()
        lx = np.asarray(res["lam_x"], float).ravel()
        Ht = np.asarray(ca.DM(hess(x, self.pval, 1.0, lg)).full(), float)
        H = Ht + Ht.T - np.diag(np.diag(Ht))
        J = np.asarray(ca.DM(jac(x, self.pval)).full(), float)
        gv = np.asarray(self.f_g(x)).ravel() if J.shape[0] else np.zeros(0)
        nX, n0 = len(x), self.n0
        near = lambda v, bnd: np.isfinite(bnd) & (np.abs(v - bnd) <= 1e-6 * (1.0 + np.abs(np.where(np.isfinite(bnd), bnd, 0.0))))
        fixed = self.lbx >= self.ubx
        at_b = fixed | ((near(x, self.lbx) | near(x, self.ubx)) & (np.abs(lx) > tol))
        Fr = np.nonzero(~at_b)[0]
        eq = self.lbg >= self.ubg
        act = eq | ((near(gv, self.lbg) | near(gv, self.ubg)) & (np.abs(lg) > tol))
        Ar = np.nonzero(act)[0]
        k = D.shape[1]
        DX = np.zeros((nX, k))
        DX[:n0] = np.asarray(D, float) * np.asarray(self.sc, float)[:, None]
        HF = H[np.ix_(Fr, Fr)]
        JA = J[np.ix_(Ar, Fr)]
        # null-space form: dX_F = -Z (Z' H Z)^-1 Z' d_F, Z a basis of the active rows' null space. Robust where the
        # active rows are linearly dependent (degenerate vertices: the fodder, land and split-bound rows often are),
        # where the full KKT matrix is singular and its solve returns the wrong sign
        from scipy.linalg import null_space
        Z = null_space(JA) if JA.shape[0] else np.eye(len(Fr))
        dX = np.zeros((nX, k))
        if Z.shape[1]:
            Hr = Z.T @ HF @ Z
            w, U = np.linalg.eigh(0.5 * (Hr + Hr.T))
            # a local minimum's reduced Hessian is positive definite; directions without curvature (or negative from
            # round-off) carry no response rather than an unbounded one
            wmax = float(np.max(np.abs(w))) if len(w) else 1.0
            inv = np.where(w > 1e-10 * wmax, 1.0 / np.where(w > 0, w, 1.0), 0.0)
            dX[Fr] = -Z @ (U @ (inv[:, None] * (U.T @ (Z.T @ DX[Fr]))))
        return dX[:n0] * np.asarray(self.sc, float)[:, None]

    def kkt_record(self, res) -> dict:
        """The point a KKT step starts from (kkt_step): the solution, its multipliers, and the problem's parameters and
        bounds at it."""
        return {"x": np.asarray(res["x"], float).copy(), "lam_x": np.asarray(res["lam_x"], float).copy(),
                "lam_g": np.asarray(res["lam_g"], float).copy(), "pval": np.asarray(self.pval, float).copy(),
                "lbx": self.lbx.copy(), "ubx": self.ubx.copy(), "lbg": self.lbg.copy(), "ubg": self.ubg.copy()}

    def kkt_step(self, base: dict, tol: float = 1e-9) -> dict:
        """The solution of this problem to first order from the recorded solution of the same graph at other parameter
        values and bounds (base, kkt_record): the implicit function theorem on the KKT conditions with the base's
        active set (market.hessian_method = "kkt", beyond CAPRI). With dp = p - p0 and the bounds' changes:

            active variable bounds (and fixed variables): dx_B = the bound's change
            active rows (and equalities):                 J_AF dx_F = the bound's change - dg/dp dp - J_AB dx_B
            stationarity on the free variables:           H_FF dx_F + H_FB dx_B + J_AF' dlam_A = -d(grad_x L)/dp dp

        H the Lagrangian's Hessian, J the rows' Jacobian, at the base point; the active set as in response (a bound or
        row within 1e-6 of its bound with a multiplier above tol). Solved as response does, in the null space Z of the
        active rows (robust where they are linearly dependent, at degenerate vertices): dx_F = x_p + Z w, x_p the
        least-norm solution of the rows, w from the reduced Hessian Z' H_FF Z (directions without curvature take no
        step). Then the multipliers: dlam_A by least squares from the stationarity, the active variables' bound
        multipliers from the stationarity of their rows. Returns the solve's dict ("status" "KKT_Step", "success" True,
        "iterations" 0). A regularised sparse KKT solve was tried first: its regularisation exceeded the smallest
        curvature of the reduced Hessian (1e-4 against 5e-3, DE110000) and turned the response's sign."""
        import casadi as ca
        from scipy.linalg import null_space
        key = self.graph_key()
        fn = _KKT.get(key)
        if fn is None:
            d = self._derivatives()
            lg = ca.SX.sym("lam_g", int(self.g.shape[0]))
            dp = ca.SX.sym("dp", int(self.p.shape[0]))
            grad = d["grad_f"](self.X, self.p)[1]
            gradL = grad + ca.jtimes(self.g, self.X, lg, True)
            fn = (d["hess_lag"],
                  ca.Function("jac_g", [self.X, self.p], [ca.jacobian(self.g, self.X)]),
                  ca.Function("dgradL", [self.X, self.p, lg, dp], [ca.jtimes(gradL, self.p, dp)]),
                  ca.Function("dg", [self.X, self.p, dp], [ca.jtimes(self.g, self.p, dp)]))
            _KKT[key] = fn
            while len(_KKT) > int(_settings().get("run.nlp_derivative_cache_size")):
                _KKT.popitem(last=False)
        hess, jac, dgradL, dgf = fn
        x0, lx0, lg0, p0 = base["x"], base["lam_x"], base["lam_g"], base["pval"]
        dpv = np.asarray(self.pval, float) - p0
        nX, m = len(x0), len(lg0)
        Ht = np.asarray(ca.DM(hess(x0, p0, 1.0, lg0)).full(), float)
        H = Ht + Ht.T - np.diag(np.diag(Ht))
        J = np.asarray(ca.DM(jac(x0, p0)).full(), float) if m else np.zeros((0, nX))
        rL = np.asarray(ca.DM(dgradL(x0, p0, lg0, dpv)).full(), float).ravel()
        rg = np.asarray(ca.DM(dgf(x0, p0, dpv)).full(), float).ravel() if m else np.zeros(0)
        g0 = np.asarray(ca.DM(self.f_g.f(x0, p0)).full(), float).ravel() if m else np.zeros(0)

        def near(v, bnd):
            fin = np.isfinite(bnd)
            return fin & (np.abs(v - bnd) <= 1e-6 * (1.0 + np.abs(np.where(fin, bnd, 0.0))))

        def change(new, old):
            with np.errstate(invalid="ignore"):
                dd = np.asarray(new, float) - np.asarray(old, float)
            return np.where(np.isfinite(dd), dd, 0.0)
        lbx0, ubx0, lbg0, ubg0 = base["lbx"], base["ubx"], base["lbg"], base["ubg"]
        fixed = lbx0 >= ubx0
        at_lo = fixed | (near(x0, lbx0) & (np.abs(lx0) > tol))
        at_up = ~at_lo & near(x0, ubx0) & (np.abs(lx0) > tol)
        Bm = at_lo | at_up
        dxB = np.where(at_lo, change(self.lbx, lbx0), np.where(at_up, change(self.ubx, ubx0), 0.0))
        eq = lbg0 >= ubg0
        g_lo = eq | (near(g0, lbg0) & (np.abs(lg0) > tol))
        g_up = ~g_lo & near(g0, ubg0) & (np.abs(lg0) > tol)
        db = np.where(g_lo, change(self.lbg, lbg0), np.where(g_up, change(self.ubg, ubg0), 0.0))
        F, B, A = np.nonzero(~Bm)[0], np.nonzero(Bm)[0], np.nonzero(g_lo | g_up)[0]
        dx = np.zeros(nX)
        dx[B] = dxB[B]
        HF = H[np.ix_(F, F)]
        JAF = J[np.ix_(A, F)]
        cA = db[A] - rg[A] - J[np.ix_(A, B)] @ dx[B]
        bF = rL[F] + H[np.ix_(F, B)] @ dx[B]
        if len(A):
            xp = np.linalg.lstsq(JAF, cA, rcond=None)[0]
            Z = null_space(JAF)
        else:
            xp, Z = np.zeros(len(F)), np.eye(len(F))
        dF = xp.copy()
        if Z.shape[1]:
            Hr = Z.T @ HF @ Z
            w, U = np.linalg.eigh(0.5 * (Hr + Hr.T))
            wmax = float(np.max(np.abs(w))) if len(w) else 1.0
            inv = np.where(w > 1e-10 * wmax, 1.0 / np.where(w > 0, w, 1.0), 0.0)
            dF = xp - Z @ (U @ (inv * (U.T @ (Z.T @ (HF @ xp + bF)))))
        dx[F] = dF
        dlg = np.zeros(m)
        if len(A):
            dlg[A] = np.linalg.lstsq(JAF.T, -(HF @ dF + bF), rcond=None)[0]
        dlx = np.zeros(nX)
        if len(B):
            dlx[B] = -(H[B] @ dx + rL[B] + (J[:, B].T @ dlg if m else 0.0))
        x = x0 + dx
        return {"x": x, "f": float(np.asarray(ca.DM(self.f_obj.f(x, self.pval)).full()).ravel()[0]),
                "lam_g": lg0 + dlg, "lam_x": lx0 + dlx, "status": "KKT_Step", "iterations": 0, "success": True,
                "warm": False}

    # ---------------- results in the regional QP's terms ----------------
    def manure_values(self, res) -> dict:
        """The value of one more t of manure nutrient applied in the region, per nutrient (EUR 1000 per t): the dual of
        the fertilisation block's EXCR pool row (fertDistExcr_), which carries the value of CAPRI's ManureNPK_ - CAPRI's
        PSHW (capmod/report_supply_model.gms l. 261: ManureNPK_.M), the point of the manure pool market's excess supply
        function (manuremarket/simu_manure_market.gms l. 60-89). The objective is a cost to minimise, the row
        (applied - manure) / scale = 0: the value is lambda / scale."""
        lam = res["lam_g"]
        return {nut: float(lam[gi]) / sc for nut, (gi, sc) in (getattr(self, "excr_rows", None) or {}).items()}

    def objective_parts(self, x) -> dict:
        """The objective at a point by part (income I3: the PMP terms CAPRI reports with its producer surplus,
        capmod/report_supply_model.gms l. 207-219), in the NLP's own terms (kEUR, the cost the model minimises):
          y, q0       the columns' levels and the linear terms per unit
          lin         per column of y: q0 x y (the linear term with the calibration's dq)
          quad        per column of y: 0.5 y (Q y) (QUADRA_'s quadratic part, with the land market's LandMarket_quad)
          feed_price, feed_ghg, feed_pmp   QUADRF_ split: sum F p (the tradable feeds at their price), sum F x the
                      emission tax per kg, sum F (CNST + 0.5 SLOP u) (CAPRI's v_sumOfPmpTermsFeed, the model's sign)
          blocks      what the options, the ration fat limit and the fertilisation blocks add (their CasADi expressions)
          obj         the objective (f_obj), and residual = obj - the parts' sum (a check: 0 up to rounding)."""
        import casadi as ca
        xv = np.asarray(x, float).ravel()
        y = np.asarray(self.f_y(xv), float).ravel()
        lin = np.asarray(self.q0, float) * y
        quad = 0.5 * y * (np.asarray(self._Qs_np, float) @ y)
        out = {"y": y, "q0": np.asarray(self.q0, float), "lin": lin, "quad": quad, "feed_price": 0.0, "feed_ghg": 0.0,
               "feed_pmp": 0.0}
        if self.nf and self._feed_np is not None:
            p_c, g_c, cn_c, hs_c, sc_c = self._feed_np
            Fv = np.asarray(self.f_F(xv), float).ravel()
            u = xv[self.n0:self.n0 + self.nf] * sc_c
            out["feed_price"] = float(Fv @ p_c)
            out["feed_ghg"] = float(Fv @ g_c)
            out["feed_pmp"] = float(Fv @ (cn_c + hs_c * u))
        if getattr(self, "_f_blocks", None) is None:
            key = self.graph_key()
            fb = _BLOCKS.get(key)
            if fb is None:
                fb = ca.Function("blocks", [self.X, self.p], [self._obj_rest - self._obj_base])
                _BLOCKS[key] = fb
                while len(_BLOCKS) > _cache_max():
                    _BLOCKS.popitem(last=False)
            else:
                _BLOCKS.move_to_end(key)
            self._f_blocks = _AtP(fb, self.pval)
        out["blocks"] = float(self._f_blocks(xv))
        out["obj"] = float(self.f_obj(xv))
        out["residual"] = out["obj"] - (float(lin.sum()) + float(quad.sum()) + out["feed_price"] + out["feed_ghg"]
                                        + out["feed_pmp"] + out["blocks"])
        return out

    def outputs(self, res):
        """(y, F {(act, feed): t}, zA (dual of each row of A, >= 0 for A y <= b), info) - the fields the supply module
        reads from the regional model."""
        x, lam_g, lam_x = res["x"], res["lam_g"], res["lam_x"]
        y = np.asarray(self.f_y(x)).ravel()
        Fv = np.asarray(self.f_F(x)).ravel()
        F = {(a, f): float(Fv[k]) for k, (a, f, r, j, s) in enumerate(self.feeds)}
        zA = np.zeros(self.m_A)
        for gi, (kind, i, jr, rs) in enumerate(self.gmap):
            l_ = float(lam_g[gi]) / rs
            if kind == "le":
                zA[i] = max(l_, 0.0)
            elif kind == "range":
                zA[i] = max(l_, 0.0); zA[jr] = max(-l_, 0.0)
            else:                                           # fodder equality: upper row (and its band) sign
                zA[i] = max(l_, 0.0)
                if jr is not None:
                    zA[jr] = max(-l_, 0.0)
        # the N-surplus row written with the purchases (e_SURTOTHa) and CAPRI's mineral cap per ha (e_synNMax): their
        # duals in the units of the regional rows they replace (1000 EUR per t N)
        for lab_, (gi, rs) in (getattr(self, "n_rows_g", None) or {}).items():
            if lab_ in self.labels:
                zA[self.labels.index(lab_)] = max(float(lam_g[gi]) / rs, 0.0)
        sr = getattr(self, "synN_row", None)
        if sr is not None and "mineral_N" in self.labels:
            zA[self.labels.index("mineral_N")] = max(float(lam_g[sr[0]]) / sr[1], 0.0)
        for i, (jx, a_) in self.bound_rows.items():
            l_ = float(lam_x[jx]) / (a_ * self.sc[jx])
            zA[i] = max(l_, 0.0)
        req = {}
        for (a, nut, gi, scale, total) in self.req_rows:
            mu = float(lam_g[gi]) / scale
            if not total:
                herd = max(float(y[self.act_idx[a]]), 1e-9)
                mu = mu / herd                              # per unit of the herd's requirement
            req[(a, nut)] = -mu
        info = {"status": res["status"], "iterations": res["iterations"], "n_feed_vars": self.nf,
                "req_duals": req, "objective": res["f"], "form": "nlp"}
        return y, F, zA, info
