"""CAPRI's regional supply model in its original (non-convex) NLP form, built with CasADi and solved with IPOPT.

This builder writes the conic form's regional problem (feed_conic.solve_regional_conic; supply_form="conic", the
cross-check form since the NLP form of capri_regional_nlp.py became the default on 20 October 2026) in CAPRI's own
relations:

* ammonia options: CAPRI's loss cascade, exact (cascade="exact", needs the region's ammonia data) or the conic
  model's tangent (cascade="linear");
* fertiliser options: one regional share per technology (uniform_fert=True, CAPRI) or one per crop (the conic model);
* feeding per head x herd (feed="perhead", CAPRI's literal bilinear form) or total feed (feed="total", the same set);
* inhibitor on manure: share x manure N;
* the crop-need row (K9, need_row) with every term that changes mineral N, as the conic model writes it;
* optionally CAPRI's inner fertiliser distribution model (fd=..., supply_model.gms NUTNED_ per crop group,
  fertDistExcr_, e_focFertDist): flows per crop group and source, each group's need met, the manure and residue
  pools exhausted, and the first-order conditions of the inner model's posterior mode as equations - CAPRI's own
  coupling, non-convex.

Used by tools/nlp_check (the check against CAPRI's form) and, in the conic form, by the supply module where CAPRI's
crop-group allocation does not exist at the conic solution (fert_dist_inside).
"""
import numpy as np


def _cascade_loss(sub, sh):
    """CAPRI's NH3 loss per unit of excreted N (ammonia_techs.loss) with symbolic shares: sh {tech: expr}."""
    import casadi as ca
    def stage(rH, rS):
        hm = 1.0 - sub["g"]
        h = hm * sub["fH"] * (1.0 - rH)
        s = (hm - h) * sub["fS"] * (1.0 - rS)
        return h + s, hm - h - s
    RA = 0
    for t in sub["techs"]:
        if t["group"] == "APP":
            RA = RA + sh[t["tech"]] * t["rA"]
    man = [t for t in sub["techs"] if t["group"] == "MAN"]
    noc = 1.0
    for t in man:
        noc = noc - sh[t["tech"]]
    L0, P0 = stage(0.0, 0.0)
    L, P = noc * L0, noc * P0
    for t in man:
        l_, p_ = stage(t["rH"], t["rS"])
        L = L + sh[t["tech"]] * l_
        P = P + sh[t["tech"]] * p_
    return sub["g"] * sub["fG"] + L + P * sub["fA"] * (1.0 - RA)


class RegionNLP:
    def __init__(self, cap, uniform_fert=True, cascade="exact", feed="perhead", fd=None):
        import casadi as ca
        from scipy import sparse
        from capri_mod.supply.feed_conic import _feed_block
        self.cap = cap
        self.feed = feed
        Q, c, A, b, acts, rats, fod = cap["args"][:7]
        k = cap["kwargs"]
        xb = np.maximum(np.asarray(k["x_base"], float), 0.0)
        techs_in = k.get("techs") or []
        fert, n_row, m_row, rx, fg, mni = (k.get("fert"), k.get("n_row"), k.get("m_row"), k.get("req_extra"),
                                           k.get("feed_ghg"), k.get("mni"))
        prices = k.get("prices")
        Q = np.asarray(Q, float); A = np.asarray(A, float).copy(); b = np.asarray(b, float); c = np.asarray(c, float)
        n0, m_A = Q.shape[0], A.shape[0]
        B = _feed_block(n0, m_A, list(acts), rats, fod, xb) if rats else None
        nf = B["nf"] if B else 0
        act_idx = B["act_idx"] if B else {a: i for i, a in enumerate(acts)}
        self.acts, self.n0, self.nf, self.B, self.act_idx = list(acts), n0, nf, B, act_idx
        sc = np.maximum(np.abs(xb[:n0]), 1.0)
        self.sc = sc
        techs = [t for t in techs_in if t["act"] in act_idx and t["smax"] > 0]
        self.techs = techs
        fc_ = [(col, nc) for col, nc in (fert or {}).get("crops", []) if nc > 0]
        ft = (fert or {}).get("techs", [])
        self.fc, self.ft = fc_, ft
        # ---- variables ----
        z = ca.SX.sym("z", n0)                         # activities and auxiliaries, scaled by sc
        y = z * ca.DM(sc)
        fh = ca.SX.sym("f", nf)                        # feed per head, in units of the base ration (F^ = f x / X)
        sig = ca.SX.sym("s", len(techs))               # ammonia option shares (CAPRI v_Miti)
        nft = len(ft)
        if uniform_fert:
            phi = ca.SX.sym("p", nft)                  # one regional share per fertiliser technology (CAPRI)
        else:
            phi = ca.SX.sym("p", nft * len(fc_))       # per crop (the conic model's departure)
        use_mni = bool(mni) and float(mni.get("smax", 0.0)) > 0 and any(m > 0 for _, m in mni["w"])
        smv = ca.SX.sym("m", 1 if use_mni else 0)
        self.use_mni = use_mni
        tv = ca.SX.sym("t", nf if feed == "total" else 0)   # the conic model's perspective variable (total form)
        X = ca.vertcat(z, fh, sig, phi, smv, tv)
        self.n_t = tv.shape[0]
        persp = []
        self.sizes = (n0, nf, len(techs), phi.shape[0], smv.shape[0])
        # ---- feed in CAPRI's form ----
        F = []; obj = 0
        q0 = c.copy()
        if B:
            q0 = q0 - B["comp"]
            for kk, (a, f, r, j) in enumerate(B["feeds"]):
                xa = y[act_idx[a]]
                if feed == "perhead":
                    Fk = fh[kk] * xa / B["X"][kk]      # total feed in the conic model's scaled units
                else:
                    Fk = fh[kk]                         # total feed as variable (the conic model's form)
                F.append(Fk)
                qF = float(B["qF_cnst"][kk])
                if fg and (a, f) in fg:
                    qF += float(fg[(a, f)]) * B["S"][kk]
                if f not in fod:
                    pv = (prices or {}).get(a)
                    qF += (float(pv[j]) if pv is not None else float(r.p0[j])) * B["S"][kk]
                # t = F^2 X / x = f^2 x / X  (the perspective, written per head)
                if feed == "perhead":
                    obj = obj + qF * Fk + float(B["qT"][kk]) * fh[kk] * fh[kk] * xa / B["X"][kk]
                else:
                    # t x / X >= F^2 (the rotated cone: F = 0 where the herd is 0, whatever the feed's cost)
                    obj = obj + qF * Fk + float(B["qT"][kk]) * tv[kk]
                    persp.append(Fk * Fk - tv[kk] * xa / B["X"][kk])
        Fv = ca.vertcat(*F) if F else ca.SX(0, 1)
        Qs = 0.5 * (Q + Q.T)
        obj = obj + 0.5 * ca.mtimes([y.T, ca.DM(sparse.csr_matrix(Qs)), y]) + ca.dot(ca.DM(q0), y)
        # ---- ammonia options: CAPRI's cost per place, relative to the base shares ----
        for kk, t in enumerate(techs):
            sl, th, s0, w = float(t["slope"]), float(t["th"]), float(t["s0"]), float(t["w"])
            xa = y[act_idx[t["act"]]]
            d = sig[kk] - s0
            obj = obj + t["stock"] * w * xa * (th * d + 0.5 * sl * d * d)
            g = float(t.get("ghg", 0.0) or 0.0)
            if g:
                obj = obj + g * w * xa * d
            gn_ = float(t.get("ghg_n", 0.0) or 0.0)
            if gn_:
                self._gn = gn_                         # the tax on the N kept, added with the N saved below
        # ---- fertiliser options ----
        mexpr = []
        for i, (col, nc) in enumerate(fc_):
            area = y[col]
            E = 0; cost = 0
            for tt, (name, nm, a_, b_, smax) in enumerate(ft):
                p = phi[tt] if uniform_fert else phi[i * nft + tt]
                E = E + nm * p
                cost = cost + (a_ * p + 0.5 * b_ * p * p) * nc / 1000.0
            obj = obj + area * cost
            mexpr.append(nc * area / (1.0 + E))
        qt = (fert or {}).get("tax")
        if qt:
            for i, (col, nc) in enumerate(fc_):
                obj = obj + float(qt["m"]) * mexpr[i] - float(qt["m"]) * nc * y[col]
                for tt in range(nft):
                    p = phi[tt] if uniform_fert else phi[i * nft + tt]
                    obj = obj + float(qt["h"][tt]) * nc * p * y[col]
        # ---- inhibitor on manure ----
        if use_mni:
            W = 0
            for col, m in mni["w"]:
                W = W + m * y[int(col)]
            s_ = smv[0]
            obj = obj + W * (float(mni["S0"]) * s_ + 0.5 * float(mni["slope"]) * s_ * s_) / 1000.0 \
                - float(mni.get("vtax", 0.0)) * s_ * W / 1000.0
        # ---- linear rows of the captured problem, N rows with CAPRI's relations ----
        if B:
            for ri, ci in B["zero_cells"]:
                A[ri, ci] = 0.0
        fert_rows = [r_ for r_ in (n_row, m_row) if r_ is not None]
        for r_ in fert_rows:
            for col, nc in fc_:
                A[r_, col] -= nc
        # the crop-need row (K9) is written in MINUS mineral N (feed_conic): the crops' mineral part leaves with +n_c
        nr_ = k.get("need_row")
        nr_ = int(nr_) if (nr_ is not None and nr_ not in (n_row, m_row) and int(nr_) < m_A) else None
        self.need_row = nr_
        if nr_ is not None:
            for col, nc in fc_:
                A[nr_, col] += nc
        keep = np.ones(m_A, bool)
        keep[b > 1e4 * (np.abs(A) @ np.abs(xb[:n0]) + 1.0)] = False
        for r_ in fert_rows + ([nr_] if nr_ is not None else []):
            keep[r_] = True
        rowsA = ca.mtimes(ca.DM(sparse.csr_matrix(A)), y)
        extra = {}                                      # nonlinear additions per A row
        if B:
            fcols = B["fod_cols"].tocoo()
            for ri, kk, v in zip(fcols.row, fcols.col, fcols.data):
                if kk < nf:
                    extra[ri] = extra.get(ri, 0) + v * Fv[int(kk)]
        # ammonia: N kept from losses, CAPRI's cascade (exact), on the N row and the mineral N row
        amm = cap.get("amm") or {}
        relief = 0
        if techs and cascade == "linear":
            # the conic model's relation (validation of this builder): N saved per unit of share at the linearisation
            # point, relative to the base shares
            for kk, t in enumerate(techs):
                s_lin = float(t.get("s_lin", t["s0"]))
                relief = relief + t["sub"] * t["w"] * y[act_idx[t["act"]]] * (
                    t["ret"] * (sig[kk] - s_lin) + float(t.get("rel0", 0.0)))
        elif techs and amm:
            byk = {}
            for kk, t in enumerate(techs):
                byk.setdefault((t["act"], t["key"]), {})[t["tech"]] = sig[kk]
            for (a, key), shs in byk.items():
                sub = next(s for s in amm["subs"][a] if s["key"] == key)
                sh = {tt["tech"]: shs.get(tt["tech"], tt["ini"]) for tt in sub["techs"]}
                sh0 = {tt["tech"]: tt["ini"] for tt in sub["techs"]}
                L0 = _cascade_loss(sub, sh0); L1 = _cascade_loss(sub, sh)
                relief = relief + amm["sub"] * amm["sc"][a] * sub["mrel"] * sub["w"] * y[act_idx[a]] * (L0 - L1)
        # the emission tax on the N kept (indirect N2O of the NH3 kept, soil N2O of the mineral N it displaces): per t of
        # N kept; relief = sub x N kept
        gn_ = getattr(self, "_gn", 0.0)
        if gn_ and techs:
            sub_ = techs[0]["sub"]
            if sub_ > 0:
                obj = obj - gn_ * relief / sub_
        for r_, sg in [(r__, 1.0) for r__ in fert_rows] + ([(nr_, -1.0)] if nr_ is not None else []):
            add = 0
            for i in range(len(fc_)):
                add = add + mexpr[i]
            add = add - relief
            if use_mni:
                # the inhibitor's relief displaces mineral N: N row, mineral N row (K18) and crop-need row (K9)
                add = add - float(mni["eff"]) * smv[0] * W
            extra[r_] = extra.get(r_, 0) + sg * add
        g_rows = []; ub = []
        for e in persp:
            g_rows.append(e); ub.append(0.0)
        self.n_persp = len(persp)
        for ri in np.where(keep)[0]:
            g_rows.append(rowsA[int(ri)] + extra.get(int(ri), 0)); ub.append(float(b[ri]))
        self.row_index = {int(ri): len(persp) + n for n, ri in enumerate(np.where(keep)[0])}
        # feed requirement rows (per head x herd: linear in F and x, i.e. bilinear in CAPRI's form)
        if B:
            Gf = B["Gf"].tocsr()
            if rx:
                ri_, ci_, vv = [], [], []
                for i_, (a_, lab_) in enumerate(B["labels"]):
                    exs = rx.get(a_)
                    if exs and isinstance(exs, tuple):
                        exs = [exs]
                    for ex in (exs or []):
                        if lab_ in ex[1]:
                            sgn = -1.0 if lab_ == "DMAX" else 1.0
                            ri_.append(i_); ci_.append(int(ex[0])); vv.append(sgn * float(ex[1][lab_]) / B["scales"][i_])
                if ri_:
                    Gf = (Gf + sparse.csr_matrix((vv, (ri_, ci_)), shape=Gf.shape)).tocsr()
            Gy = Gf[:, :n0]; GF = Gf[:, n0:n0 + nf]
            gf = ca.mtimes(ca.DM(Gy), y) + ca.mtimes(ca.DM(GF), Fv)
            for i_ in range(gf.shape[0]):
                g_rows.append(gf[i_]); ub.append(0.0)
        # share limits (TotMit_ per sub-activity and option group; CAPRI's maximum shares)
        grp = {}
        for kk, t in enumerate(techs):
            grp.setdefault(t["grp"], []).append(kk)
        for _, ks in grp.items():
            g_rows.append(sum(sig[kk] for kk in ks)); ub.append(1.0)
        lbx = [0.0] * X.shape[0]; ubx = [np.inf] * X.shape[0]
        off = n0 + nf
        for kk, t in enumerate(techs):
            ubx[off + kk] = float(t["smax"])
        off += len(techs)
        if uniform_fert:
            for tt, (name, nm, a_, b_, smax) in enumerate(ft):
                ubx[off + tt] = float(smax)
            if nft:
                g_rows.append(sum(phi[tt] for tt in range(nft))); ub.append(1.0)
                ecap = (fert or {}).get("ecap")
                if ecap is not None:
                    g_rows.append(sum(float(ft[tt][1]) * phi[tt] for tt in range(nft))); ub.append(float(ecap))
        else:
            for i in range(len(fc_)):
                for tt, (name, nm, a_, b_, smax) in enumerate(ft):
                    ubx[off + i * nft + tt] = float(smax)
                g_rows.append(sum(phi[i * nft + tt] for tt in range(nft))); ub.append(1.0)
            ecap = (fert or {}).get("ecap")
            if fc_ and ecap is not None:
                g_rows.append(sum(nc * sum(float(ft[tt][1]) * phi[i * nft + tt] for tt in range(nft)) * y[col]
                                  for i, (col, nc) in enumerate(fc_))
                              - float(ecap) * sum(nc * y[col] for col, nc in fc_)); ub.append(0.0)
        off += phi.shape[0]
        if use_mni:
            ubx[off] = float(mni["smax"])
        lbg = [-np.inf] * len(ub)
        self.n_core = int(X.shape[0])
        self.fd_info = None
        if fd:
            X, g_rows, lbg, ub, lbx, ubx = self._fert_dist_block(fd, X, y, g_rows, lbg, ub, lbx, ubx,
                                                                 rowsA, extra, nr_)
        self.X, self.obj, self.g = X, obj, ca.vertcat(*g_rows)
        self.lbg, self.ubg, self.lbx, self.ubx = lbg, ub, lbx, ubx
        self.mexpr_f = ca.Function("mexpr", [X], [ca.vertcat(*mexpr)]) if mexpr else None
        self.W_f = ca.Function("W", [X], [W]) if use_mni else None
        self.n_keep = int(keep.sum())
        self._b = np.asarray(b, float)
        self._fc, self._ft, self._uniform = fc_, ft, uniform_fert
        self.n_row, self.m_row = n_row, m_row
        self.f_obj = ca.Function("f", [X], [obj])
        self.f_g = ca.Function("g", [X], [self.g])
        self.f_y = ca.Function("y", [X], [y])

    # ---- CAPRI's inner fertiliser distribution model inside the regional problem ----
    def _fert_dist_block(self, fd, X, y, g_rows, lbg, ub, lbx, ubx, rowsA, extra, nr_):
        """CAPRI supply_model.gms with useInnerFertDistModel: flows x_gs (crop group g, source s in MINE / EXCR /
        CRES, t N) with
          NUTNED_        sum_s e_s x_gs = N_g, N_g = w_g / W x (e_M M + e_E E + e_C C)   (the needs as the inner model
                         distributes them: base need per ha x group area x need factor, w_g; W = sum_g w_g)
          fertDistExcr_  sum_g x_gE = E (manure N applied), and the arable residue pool likewise
          e_focFertDist  (alpha_gs - 1) / x_gs - beta_gs [- regulation] = lambda_g e_s - mu_s   (mu_MINE = 0)
        with CAPRI's gamma prior per flow (mode = prior kg/ha x the group's area at the simulation's starting point,
        fixed: prep_sim.gms, set_fert_priors.gms; flows within 0.001 and 1000 x the mode) and
        the regulations' beta densities where the scenario has them. M (mineral N) is the regional problem's own:
        the crop-need row reads - M + floor <= b, so M = floor . y - row. Groups, flows and their activity columns
        come from fd (supply_module._fert_dist_spec)."""
        import casadi as ca
        G = fd["groups"]
        e = fd["e"]
        lin = lambda pairs: sum(float(v) * y[int(c)] for c, v in pairs) if pairs else 0
        # mineral N, manure applied, residue pool: linear in the regional problem's columns
        Mx = lin(fd["floor"]) - (rowsA[nr_] + extra.get(nr_, 0))
        Ex = lin(fd["E"])
        Cx = lin(fd["C"])
        T = e["MINE"] * Mx + e["EXCR"] * Ex + e["CRES"] * Cx
        A_g = [lin(g_["crops"]) for g_ in G]                       # group areas (1000 ha)
        w_g = [float(g_["per"]) * lin(g_["need"]) for g_ in G]     # base need per ha x area x factor
        W = sum(w_g)
        W0, T0 = float(fd["W0"]), max(float(fd["T0"]), 1.0)
        flows = []                                                 # (group index, source, p kg/ha, acc, cap)
        for gi, g_ in enumerate(G):
            for s_, spec in g_["flows"].items():
                flows.append((gi, s_) + tuple(spec))
        nfl = len(flows)
        # CAPRI's prior mode (t): prior per ha x the group's area at the simulation's starting point, a parameter
        # (prep_sim.gms, set_fert_priors.gms); flows are scaled by it and bounded as CAPRI bounds v_fertDist
        Aref = [float(g_.get("Aref", fd["A0"][gi])) for gi, g_ in enumerate(G)]
        m0 = np.array([max(float(p) * Aref[gi], 1e-6) for gi, s_, p, acc, cap in flows])
        xs = ca.SX.sym("xfd", nfl)                                 # flows / m0
        lam = ca.SX.sym("lfd", len(G))                             # lambda_g x T0 (scaled)
        pools = [s_ for s_ in ("EXCR", "CRES") if any(f[1] == s_ for f in flows)]
        mu = ca.SX.sym("mfd", len(pools))                          # mu_s x T0
        x = [xs[i] * m0[i] for i in range(nfl)]
        rows_eq = []
        for i, (gi, s_, p, acc, cap) in enumerate(flows):
            var_k = 1.0 / float(acc) ** 2                          # var = (m / acc)^2 = var_k m^2
            kb = (1.0 + np.sqrt(1.0 + 4.0 * var_k)) / (2.0 * var_k)        # beta = kb / m
            a1 = kb * kb * var_k - 1.0                             # alpha - 1
            m_cur = float(m0[i])                                   # prior mode (t), fixed
            ls = lam[gi] / T0 * e[s_] - (mu[pools.index(s_)] / T0 if s_ in pools else 0)
            term = a1 - kb * x[i] / m_cur - ls * x[i]
            if cap is not None:
                mx, racc, msh = cap
                b1 = float(msh) * float(racc) + 1.0
                b2 = float(racc) + 2.0 - b1 - 1.0
                capv = float(mx) * A_g[gi]
                term = term + (b1 - 1.0) - b2 * x[i] / (capv - x[i])
                g_rows.append(x[i] - capv); lbg.append(-np.inf); ub.append(0.0)
            rows_eq.append(term)
        for gi, g_ in enumerate(G):                                # NUTNED_: W sum_s e x - w_g T = 0, scaled
            sup = sum(e[s_] * x[i] for i, (gj, s_, *_r) in enumerate(flows) if gj == gi)
            rows_eq.append((W * sup - w_g[gi] * T) / (W0 * T0))
        for s_ in pools:                                           # fertDistExcr_ and the residue pool
            tot = sum(x[i] for i, (gj, s2, *_r) in enumerate(flows) if s2 == s_)
            rows_eq.append((tot - (Ex if s_ == "EXCR" else Cx)) / T0)
        for r_ in rows_eq:
            g_rows.append(r_); lbg.append(0.0); ub.append(0.0)
        n_old = int(X.shape[0])
        X = ca.vertcat(X, xs, lam, mu)
        # CAPRI prep_sim.gms: 0.001 x mode <= v_fertDist <= 1000 x mode ("division by zero happens if the variable
        # becomes zero... also helping scaling"); multipliers (x T0) within +-1e6
        lbx = list(lbx) + [1e-3] * nfl + [-1e6] * (len(G) + len(pools))
        ubx = list(ubx) + [1e3] * nfl + [1e6] * (len(G) + len(pools))
        self.fd_info = {"flows": flows, "m0": m0, "groups": [g_["g"] for g_ in G], "pools": pools, "off": n_old,
                        "Mx": Mx, "Ex": Ex, "Cx": Cx}
        return X, g_rows, lbg, ub, lbx, ubx

    def fd_start(self, x_core, fd):
        """Start for the distribution block: each flow at its prior mode (the first-order conditions hold there with
        lambda = mu = 0), scaled so each group meets its need."""
        if not self.fd_info:
            return x_core
        fi = self.fd_info
        n = len(fi["flows"])
        xs0 = np.ones(n)
        return np.concatenate([x_core, xs0, np.zeros(len(fi["groups"]) + len(fi["pools"]))])

    def fd_flows(self, x):
        """{(group, source): t N} of a solution."""
        fi = self.fd_info or {}
        off = fi.get("off", 0)
        return {(fi["groups"][gi], s_): float(x[off + i]) * float(fi["m0"][i]) for i, (gi, s_, *_r) in enumerate(fi.get("flows", []))}

    def to_conic(self, x, lam_g):
        """The NLP's solution in solve_regional_conic's outputs (cascade="linear", fertiliser shares per crop,
        feed="total"): (y, F, zA, info)."""
        n0, nf, nt, nphi, nm = self.sizes
        x = np.asarray(x, float).ravel(); lam_g = np.asarray(lam_g, float).ravel()
        y = np.asarray(self.f_y(x)).ravel()
        B = self.B
        F = {}
        for kk, (a, f, r, j) in enumerate(B["feeds"] if B else []):
            F[(a, f)] = float(x[n0 + kk]) * B["S"][kk]
        info = {"status": "Solved (IPOPT NLP)", "iterations": None, "n_feed_vars": nf}
        info["tech_M"] = {(t["act"], t["key"], t["tech"]): float(x[n0 + nf + kk]) * t["w"] * float(y[self.act_idx[t["act"]]])
                          for kk, t in enumerate(self.techs)}
        H, Mc = {}, {}
        nft = len(self._ft)
        mv = np.asarray(self.mexpr_f(x)).ravel() if self.mexpr_f is not None else []
        for i, (col, nc) in enumerate(self._fc):
            for tt, (name, *_r) in enumerate(self._ft):
                ph = float(x[n0 + nf + nt + (tt if self._uniform else i * nft + tt)])
                H[(col, name)] = ph * float(y[col])
            Mc[col] = float(mv[i]) if len(mv) else 0.0
        info["fert_H"] = H
        info["fert_m"] = Mc
        if nm:
            Wv = float(np.asarray(self.W_f(x)).ravel()[0]) if self.W_f is not None else 0.0
            info["mni_W"] = Wv
            info["mni_T"] = float(x[n0 + nf + nt + nphi]) * Wv
        else:
            info["mni_T"] = info["mni_W"] = 0.0
        zA = np.zeros(len(self._b))
        for r_, gi in self.row_index.items():
            zA[r_] = max(float(lam_g[gi]), 0.0)
        req = {}
        if B:
            off = self.n_persp + self.n_keep
            for i_, key_ in enumerate(B["labels"]):
                req[key_] = max(float(lam_g[off + i_]), 0.0) / B["scales"][i_]
        info["req_duals"] = req
        return y, F, zA, info

    # ---- the conic solution in CAPRI's variables ----
    def from_conic(self):
        y, F, zA, info = self.cap["out"]
        y = np.asarray(y, float)
        n0, nf, nt, nphi, nm = self.sizes
        x = np.zeros(n0 + nf + nt + nphi + nm + self.n_t)
        x[:n0] = y / self.sc[:n0]
        B = self.B
        for kk, (a, f, r, j) in enumerate(B["feeds"] if B else []):
            xa = max(y[self.act_idx[a]], 1e-12)
            Fh = F.get((a, f), 0.0) / B["S"][kk]
            x[n0 + kk] = Fh * B["X"][kk] / xa if self.feed == "perhead" else Fh
        Mv = info.get("tech_M", {})
        for kk, t in enumerate(self.techs):
            xa = y[self.act_idx[t["act"]]]
            M = Mv.get((t["act"], t["key"], t["tech"]), t["s0"] * t["w"] * xa)
            x[n0 + nf + kk] = M / (t["w"] * xa) if xa > 1e-12 else t["s0"]
        H = info.get("fert_H", {})
        nft = len(self.ft)
        if nphi == nft:
            area = sum(y[col] for col, _ in self.fc)
            for tt, (name, *_r) in enumerate(self.ft):
                x[n0 + nf + nt + tt] = sum(H.get((col, name), 0.0) for col, _ in self.fc) / area if area > 0 else 0.0
        else:
            for i, (col, nc) in enumerate(self.fc):
                for tt, (name, *_r) in enumerate(self.ft):
                    x[n0 + nf + nt + i * nft + tt] = H.get((col, name), 0.0) / y[col] if y[col] > 1e-9 else 0.0
        if nm:
            W = info.get("mni_W", 0.0)
            x[n0 + nf + nt + nphi] = info.get("mni_T", 0.0) / W if W > 0 else 0.0
        if self.n_t:
            for kk, (a, f, r, j) in enumerate(B["feeds"]):
                xa = y[self.act_idx[a]]
                x[n0 + nf + nt + nphi + nm + kk] = x[n0 + kk] ** 2 * B["X"][kk] / xa if xa > 1e-12 else 0.0
        nc_ = len(x)
        return np.clip(x, self.lbx[:nc_], self.ubx[:nc_])

    def violation(self, x):
        g = np.asarray(self.f_g(x)).ravel()
        v = np.maximum(np.maximum(g - np.asarray(self.ubg), np.asarray(self.lbg) - g), 0.0)
        xb = np.maximum(np.asarray(self.lbx) - x, 0.0) + np.maximum(x - np.asarray(self.ubx), 0.0)
        return float(max(v.max(initial=0.0), xb.max(initial=0.0))), int(np.argmax(v)) if v.size else -1

    def solve(self, x0, max_iter=3000, mu_strategy="adaptive", obj_scale=1.0):
        """IPOPT from x0. obj_scale divides the objective (the multipliers are returned in the unscaled problem's
        units). Returns (x, objective, lam_g, status, iterations)."""
        import casadi as ca
        nlp = {"x": self.X, "f": self.obj / float(obj_scale), "g": self.g}
        opts = {"ipopt.print_level": 0, "print_time": 0, "ipopt.max_iter": max_iter, "ipopt.tol": 1e-8,
                "ipopt.acceptable_tol": 1e-6, "ipopt.mu_strategy": mu_strategy}
        import time as _tm
        _t0 = _tm.time()
        S = ca.nlpsol("S", "ipopt", nlp, opts)
        _t1 = _tm.time()
        r = S(x0=x0, lbx=self.lbx, ubx=self.ubx, lbg=self.lbg, ubg=self.ubg)
        st = S.stats()
        self.last_solve_times = (_t1 - _t0, _tm.time() - _t1)
        return np.asarray(r["x"]).ravel(), float(r["f"]) * float(obj_scale), \
            np.asarray(r["lam_g"]).ravel() * float(obj_scale), st["return_status"], st.get("iter_count")


