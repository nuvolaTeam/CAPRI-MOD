r"""The regional NLP's core problem built in its constructor: the activities, the feeding, the fodder, the land rows
(moved from capri_mod/supply/capri_regional_nlp.py as it was, 26 November 2026).
"""
from __future__ import annotations

import hashlib
import os
from collections import OrderedDict

import numpy as np

from capri_mod.settings import current as _settings   # the numerical settings
from capri_mod.supply.regional_nlp.feed_terms import _AtP, _feed_scale, calibrate_feed_terms  # noqa: E402


class ProblemBlock:
    """CapriRegionalNLP's data parameters (_pv, _lin, _pmat) and constructor."""

    # ---------------- data values as parameters (solver cache) ----------------
    def _pv(self, v):
        """Data values (scalar or vector) as parameters of the graph: their symbols, the values recorded in order."""
        import casadi as ca
        a = np.atleast_1d(np.asarray(v, float)).ravel()
        s = ca.SX.sym("p", len(a))
        self._psyms.append(s)
        self._pvals.append(a)
        return s if len(a) > 1 or np.ndim(v) > 0 else s[0]

    def _lin(self, y, pairs, scale=1.0):
        """sum_c v_c y_c / scale with the coefficients as parameters (0 without pairs)."""
        if not pairs:
            return 0
        import casadi as ca
        cols = [int(c) for c, _ in pairs]
        vals = np.array([float(v) for _, v in pairs]) / scale
        if len(cols) == 1:
            return self._pv(vals[0]) * y[cols[0]]
        return ca.dot(self._pv(vals), y[cols])

    def _pmat(self, M):
        """A sparse matrix with its nonzeros as parameters (the pattern is structure)."""
        import casadi as ca
        from scipy import sparse
        Mc = sparse.csc_matrix(M)
        Mc.eliminate_zeros()
        Mc.sort_indices()
        sp = ca.Sparsity(Mc.shape[0], Mc.shape[1], Mc.indptr.astype(int).tolist(), Mc.indices.astype(int).tolist())
        if Mc.nnz == 0:
            return ca.SX(sp)
        return ca.SX(sp, self._pv(np.asarray(Mc.data, float)))

    def __init__(self, spec):
        import casadi as ca
        from capri_mod.supply.equations.supply_model.feeding import FEDUSE_, REQSE_, REQSE_split
        from capri_mod.supply.equations.supply_model.markets import SUPBAL_fodder_use
        from capri_mod.supply.equations.supply_model.objective import OBJEQF_, QUADRA_, QUADRF_
        self.spec = spec
        self._psyms, self._pvals = [], []
        Q = np.asarray(spec["Q"], float)
        c = np.asarray(spec["c"], float).copy()
        A = np.asarray(spec["A"], float).copy()
        b = np.asarray(spec["b"], float).copy()
        labels = list(spec["labels"])
        if len(labels) != A.shape[0]:
            raise ValueError(f"{len(labels)} row labels for {A.shape[0]} rows")
        acts = list(spec["acts"])
        # a missing input (NaN, inf) stops the build: IPOPT would stop at its first iteration (Invalid_Number_Detected)
        # and the run keep its starting point as a non-optimal solve (27 October 2026: 16 regions, a NaN cost of an
        # animal the region does not have); CAPRI stops on an execution error
        for nm_, arr_ in (("Q", Q), ("c", c), ("A", A), ("b", b)):
            bad_ = ~np.isfinite(arr_)
            if bad_.any():
                ix_ = np.argwhere(bad_)[0].tolist()
                what_ = (acts[ix_[0]] if nm_ == "c" else labels[ix_[0]] if nm_ in ("A", "b") else ix_)
                raise ValueError(f"non-finite {nm_} in the regional problem ({int(bad_.sum())} entries, first {what_})")
        n0, m_A = Q.shape[0], A.shape[0]
        self.n0, self.m_A, self.acts, self.labels = n0, m_A, acts, labels
        act_idx = {a: i for i, a in enumerate(acts)}
        self.act_idx = act_idx
        xb = np.maximum(np.asarray(spec["x_base"], float)[:n0], 0.0)
        self.xb = xb
        sc = np.maximum(np.abs(xb), 1.0)
        self.sc = sc
        rats = {a: r for a, r in (spec.get("rations") or {}).items() if a in act_idx}
        fod = dict(spec.get("fodder") or {})
        prices = spec.get("prices") or {}
        fg = spec.get("feed_ghg") or {}
        rx = spec.get("req_extra") or {}

        # ---------------- variables ----------------
        z = ca.SX.sym("z", n0)                       # columns of the regional QP, scaled
        self._scp = self._pv(sc)
        y = z * self._scp
        feeds = []                                   # (act, feed, ration, j, scale)
        for a, r in rats.items():
            for j, f in enumerate(r.feeds):
                if r.flex[j]:
                    feeds.append((a, f, r, j, _feed_scale(r, j)))
        nf = len(feeds)
        u = ca.SX.sym("u", nf)                       # per-head feed / scale (CAPRI v_feedInpCoeff)
        fhv = u * self._pv([fe[4] for fe in feeds]) if nf else u
        fh = [fhv[k] for k in range(nf)]
        X = ca.vertcat(z, u)
        self.feeds, self.nf = feeds, nf
        self._fhv = fhv

        # ---------------- feed calibration (REQSE_ only) ----------------
        cal = {a: calibrate_feed_terms(r, fod) for a, r in rats.items()}
        self.feed_cal = {a: {"lam": v[1], "delta": v[2]} for a, v in cal.items()}

        # ---------------- objective ----------------
        q0 = c.copy()
        obj = 0
        feed_lin = spec.get("feed_lin")
        for a, r in rats.items():
            cn = cal[a][0]
            fl = np.asarray(r.flex, bool)
            if feed_lin is not None and a in feed_lin:
                # CAPRI's objective form (supply.animal_cost_form "capri", register DEP-13 step 3): the herd's linear term
                # holds CAPRI's feed value per head (TOIN's FEED part); it is taken out, and QUADRF_ below alone charges
                # the feed, as CAPRI's objective (LINEAR_ has no feed, supply_model.gms l. 4752-4763)
                q0[act_idx[a]] -= float(feed_lin[a])
                continue
            # the herd's linear term carries the base ration's cost per head (CNST, 0.5 SLOP, tradable feeds at base
            # prices; fodder through its balance); it is taken out here and charged through QUADRF_ below, exactly as
            # the feed block's compensation, with the calibrated CNST
            pz = np.array([0.0 if f in fod else float(r.p0[j]) for j, f in enumerate(r.feeds)])
            q0[act_idx[a]] -= float(np.sum(np.where(fl, r.x0 * (pz + cn + 0.5 * r.slope * r.x0), 0.0)))
        F = []
        self._feed_np = None
        if nf:
            lin_c, half_s = np.zeros(nf), np.zeros(nf)
            p_c, ghg_c, cn_c = np.zeros(nf), np.zeros(nf), np.zeros(nf)
            for k, (a, f, r, j, s) in enumerate(feeds):
                cn = float(cal[a][0][j]) + float((spec.get("dcnst") or {}).get((a, f), 0.0))
                p = 0.0
                if f not in fod:
                    pv = prices.get(a)
                    p = float(pv[j]) if pv is not None else float(r.p0[j])
                ghg = float(fg.get((a, f), 0.0) or 0.0)       # emission tax per kg of feed, as the price
                lin_c[k] = p + ghg + cn
                half_s[k] = 0.5 * float(r.slope[j])
                p_c[k], ghg_c[k], cn_c[k] = p, ghg, cn
            # QUADRF_'s parts by CAPRI's category, for the report at the solution (objective_parts): the feeds' price
            # and emission tax (CAPRI's LINEAR_) and the PMP terms CNST + 0.5 SLOP u (v_sumOfPmpTermsFeed)
            self._feed_np = (p_c, ghg_c, cn_c, half_s.copy(), np.array([fe[4] for fe in feeds], float))
            herds = y[[act_idx[fe[0]] for fe in feeds]]
            Fv = FEDUSE_(herds, fhv)                           # t
            obj = obj + ca.sum1(QUADRF_(Fv, self._pv(lin_c), self._pv(half_s), fhv))
            F = [Fv[k] for k in range(nf)]
        if spec.get("dq") is not None:
            q0 = q0 + np.asarray(spec["dq"], float)            # the base calibration's linear terms (calibrate())
        Qs = 0.5 * (Q + Q.T)
        # the PMP quadratic is kept apart: its Hessian is the matrix itself, given to IPOPT directly (_derivatives)
        self._Qsx = self._pmat(Qs)
        quad = QUADRA_(self._Qsx, y)
        obj = obj + ca.dot(self._pv(q0), y)
        self.q0 = q0
        # the objective before the blocks below (the options, the ration fat limit, the fertilisation): what the blocks
        # add is their difference to the objective at the end (objective_parts)
        self._Qs_np, self._obj_base = Qs, obj

        # ---------------- rows of the regional QP ----------------
        # fodder balances: animal cells replaced by FEDUSE_ (per-head feed x herd / 1000, flexible and fixed feeds)
        extra = {}
        fod_rows = {}
        for f, ri in fod.items():
            fod_rows[ri] = f
            for a in rats:
                A[ri, act_idx[a]] = 0.0
            # the animals' milk for feeding (CAPRI's COMF, SGMF; SUPBAL_'s output side): their output per head, which
            # the line above cleared with the use
            for j_, t_ in ((spec.get("fodder_out") or {}).get(f) or {}).items():
                A[ri, int(j_)] -= float(t_)
        for a, r in rats.items():
            for j, f in enumerate(r.feeds):
                if f in fod and not r.flex[j] and float(r.x0[j]) > 0:
                    ri = fod[f]
                    A[ri, act_idx[a]] += float(r.x0[j]) / 1000.0
        for k, (a, f, r, j, s) in enumerate(feeds):
            if f in fod:
                ri = fod[f]
                extra[ri] = extra.get(ri, 0) + F[k] / 1000.0
        # classify rows
        lbx = np.zeros(n0 + nf); ubx = np.full(n0 + nf, np.inf)
        # the crops' technology mix columns z (x_T1 = X/2 + z, x_T2 = X/2 - z) are bounded by their two rows alone,
        # -X/2 <= z <= X/2 (techn_mix.py): z < 0 is the shift to CAPRI's low-yield technology T2; so are the dairy and
        # cattle intensity splits' (livestock.py: low = s_low X + z >= 0, high = s_high X - z >= 0; z < 0 moves heads
        # to the high-intensity activity). Until 15 November 2026 the default lower bound 0 held every such z at or
        # above the calibration point (KNOWN_ISSUES K155)
        for k_ in list(spec.get("mix_cols") or ()) + list(spec.get("split_cols") or ()):
            if int(k_) < n0:
                lbx[int(k_)] = -np.inf
        # the manure trade columns under CAPRI's form (supply.manure_trade_form "capri"): changes of the gross exports
        # and imports from CAPRI's calibration point, down to minus that trade
        for k_, v_ in (spec.get("col_lb") or {}).items():
            if int(k_) < n0:
                lbx[int(k_)] = float(v_) / sc[int(k_)]
        bound_rows = {}                                    # row -> (col, coef)
        nnz = (A != 0).sum(axis=1)
        for i in range(m_A):
            if nnz[i] == 1 and i not in fod_rows and i not in extra:
                jx = int(np.nonzero(A[i])[0][0])
                a_ = float(A[i, jx])
                lim = float(b[i]) / (a_ * sc[jx])
                if a_ > 0:
                    ubx[jx] = min(ubx[jx], lim)
                else:
                    lbx[jx] = max(lbx[jx], lim)
                bound_rows[i] = (jx, a_)
        for jx, v_ in (spec.get("fix_cols") or {}).items():
            lbx[int(jx)] = ubx[int(jx)] = float(v_) / sc[int(jx)]
        # a column whose bounds cross by the rows' tiny tolerances (fixed levels written as two rows) is fixed
        for jx in range(n0):
            if lbx[jx] > ubx[jx]:
                mid = 0.5 * (lbx[jx] + ubx[jx]); lbx[jx] = ubx[jx] = mid
        # pairs of opposite rows -> one ranged row
        used = set(bound_rows)
        pairs = {}                                         # upper row -> lower row
        lab_idx = {l: i for i, l in enumerate(labels)}
        for i, l in enumerate(labels):
            if i in used:
                continue
            for partner in (l + "_lo",):
                jr = lab_idx.get(partner)
                if jr is not None and jr not in used and np.allclose(A[jr], -A[i], rtol=0, atol=1e-12):
                    pairs[i] = jr; used.add(i); used.add(jr)
                    break
        self._A, self._b = A, b
        g_rows, lbg, ubg, gmap = [], [], [], []           # gmap: (kind, rows, scale)
        drop = set(spec.get("drop_labels") or ())
        self.dropped = [labels[i] for i in range(m_A) if labels[i] in drop]
        keep_rows = [i for i in range(m_A)
                     if not (i in bound_rows or (i in used and i not in pairs) or labels[i] in drop)]
        # the kept rows, each scaled by its largest coefficient (x the column scale), as one parametric matrix
        rsv = {}
        for i in keep_rows:
            rs = max(float(np.max(np.abs(A[i] * sc))), 1e-12)
            if i in extra:
                rs = max(rs, 1.0)
            rsv[i] = rs
        if keep_rows:
            Ak = A[keep_rows] / np.array([rsv[i] for i in keep_rows])[:, None]
            rowsK = ca.mtimes(self._pmat(Ak), y)
            n_ex = sum(1 for i in keep_rows if i in extra)
            ex_sc = self._pv([1.0 / rsv[i] for i in keep_rows if i in extra]) if n_ex else None
        k_ex = 0
        for kk, i in enumerate(keep_rows):
            rs = rsv[i]
            ex = rowsK[kk]                                     # the row / rs
            if i in extra:
                ex = SUPBAL_fodder_use(ex, extra[i], ex_sc[k_ex])   # + the flexible feeds' FEDUSE_ / rs
                k_ex += 1
            if i in fod_rows and fod_rows[i] in (spec.get("fodder_le") or ()):
                # SUPBAL_ with CAPRI's losses (the milk for feeding: v_lossQuant between 0 and infinity in FEDUSE_):
                # use <= output, at the balance's base constant
                g_rows.append(ex); lbg.append(-np.inf); ubg.append(float(b[i]) / rs)
                gmap.append(("le", i, None, rs))
            elif i in fod_rows:
                # SUPBAL_ for non-tradable fodder: production = use (an equality at the balance's base constant)
                g_rows.append(ex); lbg.append(float(b[i]) / rs); ubg.append(float(b[i]) / rs)
                gmap.append(("eq", i, pairs.get(i), rs))
            elif i in pairs:
                jr = pairs[i]
                g_rows.append(ex); lbg.append(-float(b[jr]) / rs); ubg.append(float(b[i]) / rs)
                gmap.append(("range", i, jr, rs))
            else:
                g_rows.append(ex); lbg.append(-np.inf); ubg.append(float(b[i]) / rs)
                gmap.append(("le", i, None, rs))
        self.n_lin = len(g_rows)

        # ---------------- REQSE_ ----------------
        req_rows = []                                      # (act, nut, row in g, scale, total?)
        for a, r in rats.items():
            ks = [k for k, fe in enumerate(feeds) if fe[0] == a]
            fixed = ~np.asarray(r.flex, bool)
            herd = y[act_idx[a]]
            exs = rx.get(a)
            if exs and isinstance(exs, tuple):
                exs = [exs]
            for nut, vec in (("E", r.e), ("P", r.cp)):
                R = float(vec @ r.x0)
                if R <= 0:
                    continue
                # supply / requirement - 1 (coefficients as parameters)
                cf = np.array([float(vec[feeds[k][3]]) / R for k in ks])
                sup = REQSE_(ca.dot(self._pv(cf), fhv[ks]) if len(ks) > 1
                             else (self._pv(cf[0]) * fh[ks[0]] if ks else 0),
                             self._pv(float(vec[fixed] @ r.x0[fixed]) / R))
                dz = [(int(col_), float(d_[nut])) for col_, d_ in (exs or []) if nut in d_ and float(d_[nut]) != 0.0]
                if dz:
                    # with a split column the requirement of the herd is R x herd + d x z (total form, bilinear)
                    Xa = max(float(xb[act_idx[a]]), 1e-3)
                    e_ = REQSE_split(sup, herd, self._pv(1.0 / Xa), self._lin(y, dz, scale=R * Xa))
                    req_rows.append((a, nut, len(g_rows), R * Xa, True))
                else:
                    e_ = sup
                    req_rows.append((a, nut, len(g_rows), R, False))
                g_rows.append(e_); lbg.append(0.0); ubg.append(0.0)
        self.req_rows = req_rows

        # ---------------- feed bounds (set_supply_bounds.gms) ----------------
        for k, (a, f, r, j, s) in enumerate(feeds):
            dmx = float(r.DMAX) if np.isfinite(float(r.DMAX)) else float(r.dm @ r.x0)
            ubx[n0 + k] = 10.0 * dmx / max(float(r.dm[j]), 1e-6) / s

        # ---------------- CAP greening (permGrasGreening_, ecoSetAside_, cropDivGreening_) ----------------
        self.cap_rows = {}
        cr_ = spec.get("cap_rules") or {}
        lin = lambda pairs: self._lin(y, pairs)
        for name in ("permGras", "ecoSetAside"):
            r_ = cr_.get(name)
            if r_:
                sc_ = max(float(r_.get("scale", 1.0)), 1e-6)
                self.cap_rows[name] = len(g_rows)
                g_rows.append(self._lin(y, r_["row"], scale=sc_)); lbg.append(-np.inf); ubg.append(float(r_["rhs"]) / sc_)
        cd = cr_.get("cropDiv")
        if cd:
            # Shannon index of the annual crop groups >= the base index:
            #   - sum_k X_k / T log(X_k / T) >= H0,  T = annual crop area (ANNC)
            # (+1e-6 kha rather than CAPRI's 1e-10: IPOPT relaxes bounds by 1e-8, and the log must stay defined)
            # Columns fixed at zero (activities without a level: CAPRI has no variable for them, set_supply_bounds /
            # prep_sim) are left out of the groups: they contribute nothing, and with IPOPT's fixed-variable treatment
            # (make_constraint) their trial values can fall below zero by more than the 1e-6 floor, where the log is
            # undefined (NaN in about 24 regions of the 2030 baseline, KNOWN_ISSUES K69)
            # The floor under each group's log: 1e-6 kha plus IPOPT's bound relaxation over the group's columns
            # (bound_relax_factor 1e-8 per scaled column, x 10; cd["floors"], the same in the base index H0). With 1e-6
            # alone a column of base level 166 kha at its relaxed bound (-6e-9 scaled) took a single-column group to
            # zero, the log to NaN, and IPOPT through 3000 iterations (LV000000, Green Deal 2030 cold start; K97)
            _fix0 = lambda j: lbx[int(j)] == 0.0 and ubx[int(j)] == 0.0
            fl_ = cd.get("floors") or [1e-6] * len(cd["groups"])
            Xk = [lin([(j, w) for j, w in gp if not _fix0(j)]) + float(f_) for gp, f_ in zip(cd["groups"], fl_)]
            T = sum(Xk)
            H = 0
            for x_ in Xk:
                H = H - x_ / T * ca.log(x_ / T)
            self.cap_rows["cropDiv"] = len(g_rows)
            g_rows.append(H); lbg.append(float(cd["H0"])); ubg.append(np.inf)

        lbx, ubx = list(lbx), list(ubx)
        # ---------------- abatement options (ghgAbatement: v_Miti) ----------------
        X, obj = self._abatement_block(spec, X, y, obj, g_rows, lbg, ubg, lbx, ubx)
        # ---------------- the ration fat limit with linseed (SupplementPerc_) ----------------
        X, obj = self._supplement_fat_block(spec, X, y, obj, g_rows, lbg, ubg, lbx, ubx)

        # ---------------- fertilisation (NUTNED_, pools, inner model) ----------------
        self.fert = None
        if spec.get("npk"):
            X, obj = self._fert_block(spec["npk"], X, y, obj, g_rows, lbg, ubg, lbx, ubx)
        if getattr(self, "_mni_cost_pending", None) is not None:
            # no N manure pool in the fertilisation block: the inhibitor on manure's cost on the excreted manure N
            s_m, S0m, slope_m, _, W_m, W_b = self._mni_cost_pending
            obj = obj + W_m * (self._pv(S0m) * s_m + self._pv(0.5 * slope_m) * s_m * s_m)
            self._mni_base = W_b
            self._mni_cost_pending = None
        if getattr(self, "_fert_tech_pending", None) is not None:
            # no N purchases in the model: the options' cost on the crops' base mineral N
            cost_, crops_ = self._fert_tech_pending
            obj = obj + self._lin(y, [(col, float(nc) / 1000.0) for col, nc in crops_]) * cost_
            self._fert_tech_base = sum(float(self.xb[int(col)]) * float(nc) / 1000.0 for col, nc in crops_)
            self._fert_tech_pending = None

        self._obj_rest, self._y = obj, y
        obj = OBJEQF_(obj, quad)
        self.X, self.obj, self.g = X, obj, ca.vertcat(*g_rows)
        self.lbg, self.ubg = np.array(lbg, float), np.array(ubg, float)
        self.lbx, self.ubx = np.array(lbx, float), np.array(ubx, float)
        self.gmap, self.bound_rows, self.pairs = gmap, bound_rows, pairs
        self.act_idx = act_idx
        # the data values: one parameter vector
        self.p = ca.vertcat(*self._psyms) if self._psyms else ca.SX.sym("p", 0)
        self.pval = np.concatenate(self._pvals) if self._pvals else np.zeros(0)
        self._psyms = self._pvals = None
        P = self.p
        self.f_y = _AtP(ca.Function("y", [X, P], [y]), self.pval)
        self.f_F = _AtP(ca.Function("F", [X, P], [ca.vertcat(*F)] if F else [ca.DM.zeros(0, 1)]), self.pval)
        self.f_obj = _AtP(ca.Function("f", [X, P], [obj]), self.pval)
        self.f_g = _AtP(ca.Function("g", [X, P], [self.g]), self.pval)
        self._solver = None
