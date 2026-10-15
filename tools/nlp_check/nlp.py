"""Check the regional conic model against CAPRI's original (non-convex) formulation with IPOPT (CasADi).

python tools/nlp_check/nlp.py CAPDIR [REGION ...]

For each captured regional problem (tools/nlp_check/capture.py) the same data are written in CAPRI's own form and
solved with IPOPT from several starting points:

* feeding per head (CAPRI v_feedingLevl): total feed = feed per head x herd, a bilinear term (the conic model uses total
  feed and the perspective of the feed cost - exact by algebra);
* CAPRI's ammonia technologies (v_Miti, NH3MAN / NH3APP): shares per sub-activity, N saved through CAPRI's loss
  cascade exactly (housing -> storage -> application; supply_model.gms HOUSN_, STORN_, APPLN_), bilinear in the
  manure-management and application shares and in the herd (the conic model linearises the N saved per unit of share
  at the previous solve's shares);
* CAPRI's fertiliser technologies (gainsTechFert): ONE regional share per technology, mineral N = need / (1 + sum
  share x NMIN) (the conic model lets each crop adopt separately - registered departure);
* CAPRI's inhibitor on manure: one regional share s, N relief s x NMAN x sub x manure N (bilinear), cost per t of
  manure N (the conic model: perspective in T = s W - exact by algebra).

Everything else - PMP terms, land, constraints, prices - is the captured problem itself. Reported per region: the
objective of the conic solution evaluated in CAPRI's form (with its violation of CAPRI's constraints), IPOPT's best
objective over the starts, and the main differences (activities, shares, N price).
"""
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


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
    def __init__(self, cap, uniform_fert=True, cascade="exact", feed="perhead"):
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
        keep = np.ones(m_A, bool)
        keep[b > 1e4 * (np.abs(A) @ np.abs(xb[:n0]) + 1.0)] = False
        for r_ in fert_rows:
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
        for r_ in fert_rows:
            add = 0
            for i in range(len(fc_)):
                add = add + mexpr[i]
            add = add - relief
            if use_mni and r_ == n_row:
                add = add - float(mni["eff"]) * smv[0] * W
            extra[r_] = extra.get(r_, 0) + add
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
        self.X, self.obj, self.g = X, obj, ca.vertcat(*g_rows)
        self.lbg, self.ubg, self.lbx, self.ubx = [-np.inf] * len(ub), ub, lbx, ubx
        self.n_row, self.m_row = n_row, m_row
        self.f_obj = ca.Function("f", [X], [obj])
        self.f_g = ca.Function("g", [X], [self.g])
        self.f_y = ca.Function("y", [X], [y])

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
        return np.clip(x, self.lbx, self.ubx)

    def violation(self, x):
        g = np.asarray(self.f_g(x)).ravel()
        v = np.maximum(g - np.asarray(self.ubg), 0.0)
        xb = np.maximum(np.asarray(self.lbx) - x, 0.0) + np.maximum(x - np.asarray(self.ubx), 0.0)
        return float(max(v.max(initial=0.0), xb.max(initial=0.0))), int(np.argmax(v)) if v.size else -1

    def solve(self, x0, max_iter=3000):
        import casadi as ca
        nlp = {"x": self.X, "f": self.obj, "g": self.g}
        opts = {"ipopt.print_level": 0, "print_time": 0, "ipopt.max_iter": max_iter, "ipopt.tol": 1e-8,
                "ipopt.acceptable_tol": 1e-6, "ipopt.mu_strategy": "adaptive"}
        S = ca.nlpsol("S", "ipopt", nlp, opts)
        r = S(x0=x0, lbx=self.lbx, ubx=self.ubx, lbg=self.lbg, ubg=self.ubg)
        st = S.stats()
        return np.asarray(r["x"]).ravel(), float(r["f"]), np.asarray(r["lam_g"]).ravel(), st["return_status"], \
            st.get("iter_count")


def report(cap, uniform=True, starts=5, seed=0, cascade="exact", feed="perhead"):
    import time
    P = RegionNLP(cap, uniform_fert=uniform, cascade=cascade, feed=feed)
    n0, nf, nt, nphi, nm = P.sizes
    xc = P.from_conic()
    fc_obj = float(P.f_obj(xc)); vc, vrow = P.violation(xc)
    rng = np.random.default_rng(seed)
    # starting points: the conic solution; the base (herds, rations, base shares); perturbed bases
    xb = np.zeros_like(xc)
    xb[:n0] = np.maximum(np.asarray(cap["kwargs"]["x_base"], float)[:n0], 0.0) / P.sc[:n0]
    xb[n0:n0 + nf] = 1.0
    xb[n0 + nf:n0 + nf + nt] = [t["s0"] for t in P.techs]
    if P.n_t:
        xb[len(xb) - P.n_t:] = 1.0
    pts = [("conic", xc), ("base", xb)] + [(f"rand{i}", xb * rng.uniform(0.7, 1.3, xb.size)) for i in range(starts - 2)]
    res = []
    for lab, x0 in pts:
        t0 = time.time()
        x, f, lam, st, it = P.solve(np.clip(x0, P.lbx, P.ubx))
        v, _ = P.violation(x)
        res.append((lab, f, v, st, it, time.time() - t0, x, lam))
    return P, xc, fc_obj, vc, vrow, res


def _summary(P, xc, fc_obj, res):
    ok = [r for r in res if r[3] in ("Solve_Succeeded", "Solved_To_Acceptable_Level") and r[2] < 1e-3]
    if not ok:
        return None, "no start converged: " + ", ".join(sorted(set(r[3] for r in res)))
    best = min(ok, key=lambda r: r[1])
    spread = max(r[1] for r in ok) - min(r[1] for r in ok)
    return best, f"{len(ok)}/{len(res)} starts, spread {spread / abs(best[1]):.1e}"


def main():
    """Per region: (1) the conic model's own relations in this builder (check of the builder: same optimum);
    (2) CAPRI's exact loss cascade, fertiliser shares per crop; (3) CAPRI's exact cascade and one regional share per
    fertiliser technology; (4) as (3) with feeding per head (CAPRI's literal bilinear form)."""
    capdir = Path(sys.argv[1])
    regs = sys.argv[2:] or sorted(p.stem for p in capdir.glob("*.pkl"))
    cases = [("1 builder check (conic relations)", dict(uniform=False, cascade="linear", feed="total")),
             ("2 exact cascade, fert per crop", dict(uniform=False, cascade="exact", feed="total")),
             ("3 exact cascade, fert regional", dict(uniform=True, cascade="exact", feed="total")),
             ("4 as 3, feeding per head", dict(uniform=True, cascade="exact", feed="perhead"))]
    for reg in regs:
        cap = pickle.load(open(capdir / f"{reg}.pkl", "rb"))
        print(f"\n=== {reg} (tax {cap['tax']})")
        for lab, kw in cases:
            P, xc, fc_obj, vc, vrow, res = report(cap, **kw)
            n0, nf, nt, nphi, nm = P.sizes
            best, note = _summary(P, xc, fc_obj, res)
            print(f"  [{lab}] conic point: objective {fc_obj:.6e}, max violation {vc:.3g} | {note}")
            if best is None:
                continue
            x = best[6]
            yb = np.asarray(P.f_y(x)).ravel(); yc = np.asarray(P.f_y(xc)).ravel()
            print(f"      NLP optimum {best[1]:.6e}: NLP - conic {(best[1] - fc_obj) / abs(fc_obj):+.2e} (relative)")
            d = [(P.acts[i], yc[i], yb[i]) for i in range(len(P.acts)) if max(abs(yc[i]), abs(yb[i])) > 1.0]
            d.sort(key=lambda t: -abs(t[2] - t[1]) / max(abs(t[1]), 1.0))
            print("      activities (conic -> NLP): " + ", ".join(f"{a} {u:.1f}->{v:.1f}" for a, u, v in d[:5]))
            if nt:
                sc_ = xc[n0 + nf:n0 + nf + nt]; sb = x[n0 + nf:n0 + nf + nt]
                k = int(np.argmax(np.abs(sb - sc_)))
                print(f"      ammonia shares: mean |diff| {np.mean(np.abs(sb - sc_)):.3f}, max {abs(sb[k] - sc_[k]):.3f} "
                      f"({P.techs[k]['act']} {P.techs[k]['key'].split('|')[-1]} {P.techs[k]['tech']} {sc_[k]:.3f}->{sb[k]:.3f})")
            if nphi == len(P.ft) and nphi:
                o = n0 + nf + nt
                print("      fertiliser shares: " + ", ".join(f"{P.ft[t][0]} {xc[o + t]:.3f}->{x[o + t]:.3f}"
                                                         for t in range(len(P.ft))))
            if nm:
                o = n0 + nf + nt + nphi
                print(f"      inhibitor on manure: {xc[o]:.4f} -> {x[o]:.4f}")
            if P.n_row is not None and P.n_row in P.row_index:
                print(f"      N price: conic {float(cap['out'][2][P.n_row]):.2f} -> NLP {best[7][P.row_index[P.n_row]]:.2f}")


if __name__ == "__main__":
    main()
