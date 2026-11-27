r"""The regional NLP's calibration to the base (moved from capri_mod/supply/capri_regional_nlp.py as it was, 26 November
2026).
"""
from __future__ import annotations

import hashlib
import os
from collections import OrderedDict

import numpy as np

from capri_mod.settings import current as _settings   # the numerical settings


class CalibrationBlock:
    """CapriRegionalNLP's calibrate."""

    # ---------------- calibration to the base ----------------
    def calibrate(self, y_base, tol=None):
        """Linear terms that make the base a first-order point of this model, as CAPRI's PMP calibration does.

        1. The base point: the columns at y_base, the base rations, and the fertilisation block solved at those
           levels (its equations determine flows, purchases and the inner model's duals).
        2. The multipliers of the rows active at base and of the bounds active at base: the least-squares solution of
           the first-order conditions of every variable that is not an activity (land types, split columns, manure
           trade, feeds, the fertilisation block), with the signs of the inequalities.
        3. What remains in the first-order conditions of the feeds goes into their CNST (QUADRF_), what remains in
           those of the columns into their linear terms (the herd's own term takes the change of its feed cost).
        Returns {"dq": per column, "dcnst": {(act, feed): EUR/kg}, "residual": largest residual left on the variables
        without a linear term (the fertilisation block), "ok": bool}."""
        import casadi as ca
        from scipy.optimize import lsq_linear
        if tol is None:                                    # the setting supply.nlp_cal_tol
            from capri_mod.settings import current as _settings
            tol = float(_settings().get("supply.nlp_cal_tol"))
        nX = int(self.X.shape[0]); n0, nf = self.n0, self.nf
        xb = self.start(y_base)
        lbx, ubx = self.lbx.copy(), self.ubx.copy()
        fix = np.zeros(nX, bool); fix[:n0 + nf] = True
        if self.fert:
            xb, failed = self.fert_at(xb)
            if failed:
                return {"ok": False, "why": "fertilisation block at base: " + ", ".join(f"{k} {v}" for k, v in failed.items()),
                        "fert_failed": list(failed)}
        grad = np.asarray(ca.Function("gr", [self.X, self.p], [ca.gradient(self.obj, self.X)])(xb, self.pval)).ravel()
        J = ca.Function("J", [self.X, self.p], [ca.jacobian(self.g, self.X)])(xb, self.pval)
        J = np.asarray(ca.DM(J).full())
        g = np.asarray(self.f_g(xb)).ravel()
        fin_u, fin_l = np.isfinite(self.ubg), np.isfinite(self.lbg)
        at_u = fin_u & (np.abs(g - np.where(fin_u, self.ubg, 0.0)) <= tol * np.maximum(1.0, np.abs(np.where(fin_u, self.ubg, 0.0))))
        at_l = fin_l & (np.abs(g - np.where(fin_l, self.lbg, 0.0)) <= tol * np.maximum(1.0, np.abs(np.where(fin_l, self.lbg, 0.0))))
        act = np.where(at_u | at_l)[0]
        lo_l = np.where(at_u[act] & at_l[act], -np.inf, np.where(at_u[act], 0.0, -np.inf))
        hi_l = np.where(at_u[act] & at_l[act], np.inf, np.where(at_u[act], np.inf, 0.0))
        # variable bounds active at base (not the activities': their residual is the calibration)
        free = np.ones(nX, bool); free[:len(self.acts)] = False
        # the crops' technology mix columns are calibrated as the activities are: their residual is their linear
        # term (CAPRI's p_pmpCnst per technology), not a source of row multipliers
        for k_ in self.spec.get("mix_cols") or ():
            if k_ < nX:
                free[k_] = False
        # the pesticide applications (supply.pest_disagg "agg5") are not calibrated here: their first-order conditions
        # are the pesticide calibration's (supply/cal_pesti.gms pestiOptimal_ at its margin); their residual at the base
        # is reported (pest_residual), not a source of row multipliers
        _pp = getattr(self, "pest", None)
        if _pp and _pp["n"]:
            free[_pp["off"]:_pp["off"] + _pp["n"] + _pp.get("n_lin", 0)] = False
        fu, fl_ = np.isfinite(ubx), np.isfinite(lbx)
        vb_u = free & fu & (np.abs(xb - np.where(fu, ubx, 0.0)) <= tol * np.maximum(1.0, np.abs(np.where(fu, ubx, 0.0))))
        vb_l = free & fl_ & (np.abs(xb - np.where(fl_, lbx, 0.0)) <= tol * np.maximum(1.0, np.abs(np.where(fl_, lbx, 0.0)))) & ~vb_u
        ib = np.where(vb_u | vb_l)[0]
        # the fertilisation block first: its variables (flows, the inner model's duals, purchases) enter only its own
        # rows, so the block's multipliers follow from their first-order conditions alone (a square linear system)
        lam_fix = np.zeros(len(g))
        blk_rows, blk_vars = [], []
        for nut, fb in (self.fert or {}).items():
            r0, r1 = fb["rows"]; o, o1 = fb["off"], fb["off_P"] + 1
            Rb, Vb = np.arange(r0, r1), np.arange(o, o1)
            sol_b, *_ = np.linalg.lstsq(J[Rb][:, Vb].T, -grad[Vb], rcond=None)
            lam_fix[Rb] = sol_b
            blk_rows += list(Rb); blk_vars += list(Vb)
        if blk_rows:
            free[np.array(blk_vars)] = False
            keep_act = ~np.isin(act, np.array(blk_rows))
            act, lo_l, hi_l = act[keep_act], lo_l[keep_act], hi_l[keep_act]
        # CAPRI's land rents as given (supply/cal_land_nests.gms, prep_cal.gms: the "assumed land rent" of each
        # activity's land type), not fitted: the land balances' multipliers fixed at the rents (EUR/ha; the upper row
        # takes a positive rent, its mirrored lower row a negative one), the rest of the fit around them
        fixr = self.spec.get("land_rent_rows") or {}
        land_rows = []
        if fixr:
            for gi, (kind, i, jr, rs) in enumerate(self.gmap):
                lab = self.labels[i] if i is not None and i < len(self.labels) else None
                if lab in fixr:
                    r_ = float(fixr[lab])
                    lam_fix[gi] = r_ * rs if kind == "range" else max(r_, 0.0) * rs
                    land_rows.append(gi)
                elif lab is not None and lab.endswith("_lo") and lab[:-3] in fixr and kind == "le":
                    lam_fix[gi] = max(-float(fixr[lab[:-3]]), 0.0) * rs
                    land_rows.append(gi)
            if land_rows:
                keep_act = ~np.isin(act, np.array(land_rows))
                act, lo_l, hi_l = act[keep_act], lo_l[keep_act], hi_l[keep_act]
        self.cal_land_rows = land_rows
        # the permanent-grassland rule's multiplier at CAPRI's assumed dual (supply/prep_cal.gms l. 118-131:
        # p_dualGreening = -|arable rent - grassland rent|, in GRAE's and GRAI's linear terms), not zero
        pg = (self.spec.get("cap_rules") or {}).get("permGras") or {}
        gi_pg = self.cap_rows.get("permGras") if hasattr(self, "cap_rows") else None
        if gi_pg is not None and pg.get("cal_dual") is not None:
            lam_fix[gi_pg] = float(pg["cal_dual"]) * max(float(pg.get("scale", 1.0)), 1e-6)
            land_rows = land_rows + [gi_pg]
            keep_act = ~np.isin(act, np.array([gi_pg]))
            act, lo_l, hi_l = act[keep_act], lo_l[keep_act], hi_l[keep_act]
        # CAPRI's limit of the ration's fat (SupplementPerc_): the fat share enters its own row only and has no cost, so
        # where it is interior at the base the row's multiplier is its first-order condition's, -grad / J (0 at a base
        # without linseed), as the fertilisation block's above; the slack at its lower bound takes the rest where that
        # has the bound's sign (else it stays in the fit, and its residual shows). Until 24 November 2026 these rows were
        # fitted with the rest: the fit, whose cost the feeds' residuals dominate (they go into CNST), stopped at its
        # tolerance with multipliers of about 1e-4 where 0 is exact (IR01's calibration residual 4.7e-4, KNOWN_ISSUES K198)
        sf_rows, nu_fix = [], {}
        for _a, d_ in sorted((getattr(self, "supp_fat", None) or {}).items()):
            r_, ip, is_ = d_.get("row"), d_["off"], d_["off"] + 1
            if r_ is None or J[r_, ip] == 0:
                continue
            if not (lbx[ip] + tol * max(1.0, abs(lbx[ip])) < xb[ip] < ubx[ip] - tol * max(1.0, abs(ubx[ip]))):
                continue                                            # the share at a bound: fitted with the rest
            lam_fix[r_] = -float(grad[ip]) / float(J[r_, ip])
            free[ip] = False
            sf_rows.append(r_)
            r_s = float(grad[is_]) + float(J[r_, is_]) * lam_fix[r_]
            if xb[is_] <= lbx[is_] + tol * max(1.0, abs(lbx[is_])) and r_s >= 0:
                nu_fix[is_] = -r_s                                  # the slack's lower bound (its multiplier <= 0)
                free[is_] = False
        if sf_rows:
            keep_act = ~np.isin(act, np.array(sf_rows))
            act, lo_l, hi_l = act[keep_act], lo_l[keep_act], hi_l[keep_act]
        grad_fit = grad + J.T @ lam_fix if (blk_rows or land_rows or sf_rows) else grad
        ib = np.array([i for i in ib if free[i]], int)
        # least squares on the free variables: grad + J' lam + nu = 0
        W = np.where(free)[0]
        wgt = np.ones(nX); wgt[n0:n0 + nf] = 1e-3                  # feeds: their residual goes into CNST
        M = np.hstack([J[act][:, W].T, np.eye(nX)[ib][:, W].T]) * wgt[W][:, None]
        rhs = -grad_fit[W] * wgt[W]
        lo = np.concatenate([lo_l, np.where(vb_u[ib], 0.0, -np.inf)])
        hi = np.concatenate([hi_l, np.where(vb_u[ib], np.inf, 0.0)])
        # rows and bounds that no free variable enters (rows on the activities alone: CAP rules, activity bounds)
        # get no multiplier from the fit: zero, as in CAPRI's calibration where only the calibration constraints'
        # duals enter the linear terms
        # (no free variable at all, e.g. a region whose columns are all fixed: nothing to fit)
        keep = (np.abs(M).max(axis=0) > 0) if M.shape[0] else np.zeros(M.shape[1], bool)
        mult = np.zeros(M.shape[1])
        if keep.any():
            Mk = M[:, keep]
            csc = np.maximum(np.abs(Mk).max(axis=0), 1e-12)
            # a small ridge term picks the least-norm multipliers where the fit leaves them undetermined: a row and a
            # bound active on the same variable with opposite signs (grassland_lo, land_GRAS - GRAS <= 0, with
            # land_GRAS at its lower bound) admit any pair (lam, -lam); unregularised the fit returned 6e13 for IE04,
            # and the activity's linear term took it (GRAS 5e10 EUR/ha, an objective gradient of 1e14 that made
            # IPOPT's scaled tolerances meaningless and its solutions depend on the path). The fit's residual is
            # unchanged where the multipliers are determined (CAPRI takes the duals of its calibration solve, unique
            # at the solver's basis)
            nk = Mk.shape[1]
            Ma = np.vstack([Mk / csc, np.sqrt(float(_settings().get("supply.nlp_cal_ridge"))) * np.eye(nk)])
            ra = np.concatenate([rhs, np.zeros(nk)])
            sol = lsq_linear(Ma, ra, bounds=(lo[keep] * csc, hi[keep] * csc),
                             max_iter=int(_settings().get("supply.nlp_cal_lsq_max_iter")))
            mult[keep] = sol.x / csc
        else:
            sol = type("S", (), {"status": 0})()
        lam = lam_fix.copy(); lam[act] = mult[:len(act)]
        nu = np.zeros(nX); nu[ib] = mult[len(act):]
        for k_, v_ in nu_fix.items():
            nu[k_] = v_
        res = grad + J.T @ lam + nu
        # feeds -> CNST; then the herds' linear terms take their ration's cost change
        dcnst = {}
        dq = np.zeros(n0)
        for k, (a, f, r_, j, s_) in enumerate(self.feeds):
            ia = self.act_idx[a]
            herd = float(xb[ia]) * self.sc[ia]
            if herd <= 1e-9:
                continue
            d = -res[n0 + k] / (herd * s_)
            dcnst[(a, f)] = d
            fk = float(xb[n0 + k]) * s_
            res[ia] += self.sc[ia] * d * fk                        # d(obj)/dz_a of herd x f x d
            res[n0 + k] = 0.0
        for j in range(n0):
            rj = res[j]
            at_lb = np.isfinite(lbx[j]) and xb[j] <= lbx[j] + tol * max(1.0, abs(lbx[j]))
            if at_lb and j < len(self.acts) and rj > 0:
                continue                                          # an activity at zero with a positive reduced cost
            dq[j] = -rj / self.sc[j]
        # the options (CAPRI calibrates their cost functions to the base shares): residuals into thresh / the linear
        # cost; an option at zero with a positive reduced cost stays as it is
        dabat = {}
        am = self.abat.get("amm") if getattr(self, "abat", None) else None
        if am:
            for k, t in enumerate(am["techs"]):
                j = am["off"] + k
                at0 = xb[j] <= lbx[j] + 1e-12
                if at0 and res[j] >= 0:
                    res[j] = 0.0; continue
                den = float(t["stock"]) * float(t["w"]) * float(xb[self.act_idx[t["act"]]]) * self.sc[self.act_idx[t["act"]]]
                if den > 0:
                    dabat[("amm", t["act"], t["key"], t["tech"])] = -res[j] / den
                    res[j] = 0.0
        # the fertiliser options and the inhibitor on manure (IniShare 0): their linear term beta from the residual at
        # zero (equations/ghgmiti.py pmpParlin_fertTech_DEP30: CAPRI's relSubs0 x costParLin left at the base,
        # KNOWN_ISSUES K196)
        from capri_mod.supply.equations.ghgmiti import pmpParlin_fertTech_DEP30
        fa = self.abat.get("fert") if getattr(self, "abat", None) else None
        if fa:
            for k, t in enumerate(fa["techs"]):
                j = fa["off"] + k
                den = getattr(self, "_fert_tech_base", 0.0)
                if getattr(self, "_fert_tech_P", None) and self.fert and "N" in self.fert:
                    fbN = self.fert["N"]
                    den = float(xb[fbN["off_P"]]) * fbN["Pscale"] / 1000.0      # base N purchases, kt
                b_ = pmpParlin_fertTech_DEP30(float(t[2]), res[j] / den, True) if den > 0 else None
                if b_ is not None:
                    dabat[("fert", t[0])] = b_
                res[j] = 0.0
        cc_ = self.abat.get("catc") if getattr(self, "abat", None) else None
        if cc_:
            j = cc_["off"]
            cs_ = self.spec.get("catc") or {}
            if cc_["uaa"] > 0:
                at0 = xb[j] <= 1e-12                                # at zero (an option not used at the base)
                fixed = ubx[j] - lbx[j] <= 1e-12                    # held at the base share (K188, no fill)
                m0_ = float(xb[j])
                r_ref = float(res[j] - nu[j])                       # the residual before the share's bound
                # the option's own form (its cost curve) differs from the calibration's by uaa x ((lin_opt + sqr_opt m0)
                # - (lin + sqr m0)) in this first-order condition (K188: the calibration in CAPRI's reference form, the
                # CATC activity at its input cost, lin = sqr = 0); its calibration term from that residual
                r_opt = r_ref + cc_["uaa"] * (
                    float(cs_.get("lin_opt", cs_.get("lin", 0.0))) + float(cs_.get("sqr_opt", cs_.get("sqr", 0.0))) * m0_
                    - float(cs_.get("lin", 0.0)) - float(cs_.get("sqr", 0.0)) * m0_)
                _cr = (getattr(self, "cres_rows", None) or {}).get("N")
                if cs_.get("ref_form") and _cr is not None and getattr(self, "_catc_ncoef", 0.0):
                    # the option's form has the BioFix N the reference form leaves out: its term in the residue
                    # pool's row (tot - C) / sc at that row's multiplier
                    r_opt += float(lam[_cr[0]]) * (-float(self._catc_ncoef) / float(_cr[1]))
                if not (at0 and r_opt >= 0):
                    dabat[("catc",)] = -r_opt / cc_["uaa"]
                if "lin_opt" in cs_ and not (at0 and r_ref >= 0):
                    # the reference form's own term: zero where the rule's multiplier takes the input cost (CAPRI's
                    # calibration point, where its catch crops fill the rule, supply/prep_cal.gms l. 68-99); zero too
                    # where the share is held (the Green Deal's catch crops then cost their input cost, as CAPRI's)
                    dabat[("catc_ref",)] = 0.0 if fixed else -r_ref / cc_["uaa"]
            res[j] = 0.0
        ma = self.abat.get("mni") if getattr(self, "abat", None) else None
        if ma:
            j = ma["off"]
            den = getattr(self, "_mni_base", 0.0)
            b_ = pmpParlin_fertTech_DEP30(float(ma["S0"]), res[j] / den, True) if den > 0 else None
            if b_ is not None:
                dabat[("mni",)] = b_
            res[j] = 0.0
        # the tillage options: CAPRI's first-order condition at the initial share, costParLin - costsaving0 - Subs0 +
        # pmpParLin + pmpParSqr m0 = 0 (envind/tillage.gms l. 834-842), with the model's own marginal value of the
        # share in place of CAPRI's costsaving0 (DEP-30's rule): the residual per ha of tillage area left at Subs0
        tl_ = self.abat.get("till") if getattr(self, "abat", None) else None
        if tl_:
            for k, t in enumerate(tl_["techs"]):
                j = tl_["off"] + k
                den = float(tl_["area0"])
                if den > 0:
                    dabat[("till", t["name"])] = pmpParlin_fertTech_DEP30(float(t.get("subs0", 0.0)), res[j] / den, True)
                res[j] = 0.0
        # the urea substitution: CAPRI's calibration has no saving of N in it (ammo_tech.gms l. 3100-3107, no
        # costsavings0 for it, l. 3366-3379), so its linear term Subs0 is kept; only where the model's own value of the
        # N it keeps would move the base off zero is the term raised to it (an option at zero with a positive reduced
        # cost stays as it is)
        ur_ = self.abat.get("urea") if getattr(self, "abat", None) else None
        if ur_:
            j = ur_["off"]
            den = 0.0
            if self.fert and "N" in self.fert:
                fbN = self.fert["N"]
                den = float(xb[fbN["off_P"]]) * fbN["Pscale"] / 1000.0          # base N purchases, kt
            b_ = pmpParlin_fertTech_DEP30(float(ur_["subs0"]), res[j] / den, False) if den > 0 else None
            if b_ is not None:
                dabat[("urea",)] = b_
            res[j] = 0.0
        # the legume share: CAPRI's linear term is Subs0 plus p_fertCostGains, the value of the N need it removes at the
        # member state's mineral N price (envind/leg_share.gms l. 53-73), so its first-order condition at zero is Subs0
        # at that notional value; the model leaves Subs0 there with its own value of the N need and fixation
        # (DEP-30's rule): the residual per ha of OFAR
        lg_ = self.abat.get("legsh") if getattr(self, "abat", None) else None
        if lg_:
            j = lg_["off"]
            den = float(lg_["x0"])
            if den > 0:
                dabat[("legsh",)] = pmpParlin_fertTech_DEP30(float(lg_["subs0"]), res[j] / den, True)
            res[j] = 0.0
        # the pesticide applications' first-order conditions at the base (scaled variables): a check of the pesticide
        # calibration's margin against this model's, reported apart (CAPRI's check_cal.gms: v_yldPestFac = 1)
        pest_res = None
        if _pp and _pp["n"]:
            o_ = _pp["off"]
            pest_res = res[o_:o_ + _pp["n"]].copy()
            res[o_:o_ + _pp["n"] + _pp.get("n_lin", 0)] = 0.0
        rest = np.abs(res[n0 + nf:]).max() if nX > n0 + nf else 0.0
        self.cal_point = xb
        return {"ok": True, "dq": dq, "dcnst": dcnst, "dabat": dabat, "residual": float(rest), "lam": lam,
                "n_active": int(len(act)), "lsq_status": int(sol.status), "pest_residual": pest_res}
