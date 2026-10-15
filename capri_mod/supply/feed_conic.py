"""Feeding inside the regional supply model, as CAPRI (docs/FEED_IN_SUPPLY.md).

CAPRI chooses feed per head (v_feedInpCoeff) in the same optimisation as herds and fodder:
REQSN_/REQSE_ (requirements), FEDUSE_ (feed use = per-head feed x herd), SUPBAL_ (fodder),
QUADRF_ (feed PMP = herd x sum feed (CNST + 0.5 SLOP feed)). With TOTAL feed F = per-head feed
x herd as the variable everything is linear except the PMP term, which becomes 0.5 SLOP F^2/x
(the perspective of a quadratic): a rotated second-order cone. The regional problem becomes one
convex conic program, solved by Clarabel.

Inputs: the regional QP as assembled today (Q, c, A, b over n0 variables, the first n of which are
the activities), the calibrated rations of the region's animals (capri_mod.feed.ration.Ration:
base per-head feeds x0, contents e/cp/dm, trimmed requirements E/P/DMIN/DMAX, share limits, PMP
CNST/SLOP), and the indices of the fodder-balance rows.

Units: herds in 1000 heads, per-head feed in kg, so F = kg/head x 1000 heads = t; fodder rows are
in 1000 t (F / 1000); objective in 1000 EUR, so EUR/kg x t has the right numeric value.

BASE EXACTNESS: at the base ration the feed block's marginal cost per head equals
sum_f x0_f (p_f + CNST_f + 0.5 SLOP_f x0_f) (first-order conditions of the ration calibration);
that amount is subtracted from each animal's linear term, so every herd's base optimality
condition is unchanged. Fodder is valued through its balance (dual = CAPRI's unit value at base),
not at a price, so p_f = 0 for fodder in the objective.
"""
from __future__ import annotations

import os

import numpy as np

FODDER = ("FGRA", "FMAI", "FOFA", "FROO")


def build_feed_block(n0, acts, rations, fodder_rows):
    """Return the feed block: list of feed variables and the pieces to append.

    rations: {act: Ration}; fodder_rows: {feed: row index in A}.
    """
    act_idx = {a: i for i, a in enumerate(acts)}
    feeds = []          # (act, feed, ration, j_in_ration)
    for a, r in rations.items():
        if a not in act_idx:
            continue
        for j, f in enumerate(r.feeds):
            if r.flex[j]:
                feeds.append((a, f, r, j))
    return feeds, act_idx


# ---------------------------------------------------------------------------------------
# FAST PATH: the feed block of a region (rows, cones, scaling, compensation, fodder columns)
# does not change between solves - only the region's Q, c, A, b and current feed prices do.
# It is built once per region and cached; each call assembles it with the current problem
# using sparse matrices. Scaling uses BASE herds (x_base for the activities), so it is fixed.
# ---------------------------------------------------------------------------------------
_BLOCK_CACHE = {}


def _feed_block(n0, m_A, acts, rations, fodder_rows, xb):
    from scipy import sparse
    key = (id(rations), n0, m_A, tuple(acts), tuple(sorted(fodder_rows.items())))
    blk = _BLOCK_CACHE.get(key)
    # id() alone is unsafe: Python reuses the address of a freed dict, so another
    # region could hit this block. The block keeps a reference to its rations (the
    # address cannot be reused while cached) and every hit checks it is the same object.
    if blk is not None and blk.get("_rations") is rations:
        return blk
    feeds, act_idx = build_feed_block(n0, acts, rations, fodder_rows)
    nf = len(feeds); N = n0 + 2 * nf
    iF = {k: n0 + k for k in range(nf)}; iT = {k: n0 + nf + k for k in range(nf)}
    S, X = {}, {}
    for k, (a, f, r, j) in enumerate(feeds):
        X[k] = max(float(xb[act_idx[a]]), 1e-3)
        S[k] = max(float(r.x0[j]) * X[k], 1e-3)
    # objective parts: t (fixed), F (CNST part fixed; price added per call), activities' compensation
    qT = np.array([0.5 * float(r.slope[j]) * S[k] * S[k] / X[k] for k, (a, f, r, j) in enumerate(feeds)])
    qF_cnst = np.array([float(r.cnst[j]) * S[k] for k, (a, f, r, j) in enumerate(feeds)])
    comp = np.zeros(n0)
    for a, r in rations.items():
        if a not in act_idx:
            continue
        cmp_ = 0.0
        for j, f in enumerate(r.feeds):
            if r.flex[j]:
                p = 0.0 if f in fodder_rows else float(r.p0[j])
                cmp_ += float(r.x0[j]) * (p + float(r.cnst[j]) + 0.5 * float(r.slope[j]) * float(r.x0[j]))
        comp[act_idx[a]] = cmp_
    # fodder columns of A (rows m_A x 2nf) and the animals to remove from fodder rows
    fod_cols = sparse.lil_matrix((m_A, 2 * nf))
    for k, (a, f, r, j) in enumerate(feeds):
        if f in fodder_rows:
            fod_cols[fodder_rows[f], k] = S[k] / 1000.0
    zero_cells = [(ri, act_idx[a]) for ri in fodder_rows.values() for a in rations if a in act_idx]
    # feed rows (requirements, DM, shares), normalised
    rows = []; labels = []; scales = []
    for a, r in rations.items():
        if a not in act_idx:
            continue
        ks = [k for k, fe in enumerate(feeds) if fe[0] == a]
        fixed = ~np.asarray(r.flex, bool)
        def add(vec_act, vec_feed, lab):
            row = np.zeros(N); row[act_idx[a]] = vec_act
            for k, v in vec_feed:
                row[iF[k]] += v
            mx = float(np.max(np.abs(row)))
            rows.append(row / mx if mx > 0 else row); labels.append((a, lab)); scales.append(mx if mx > 0 else 1.0)
        for nut, vec, need in (("E", r.e, r.E), ("P", r.cp, r.P)):
            if need > 0:
                add(need - float(vec[fixed] @ r.x0[fixed]), [(k, -float(vec[feeds[k][3]]) * S[k]) for k in ks], nut)
        dfix = float(r.dm[fixed] @ r.x0[fixed])
        if r.DMIN > 0:
            add(r.DMIN - dfix, [(k, -float(r.dm[feeds[k][3]]) * S[k]) for k in ks], "DMIN")
        if np.isfinite(r.DMAX):
            add(-(r.DMAX - dfix), [(k, float(r.dm[feeds[k][3]]) * S[k]) for k in ks], "DMAX")
        for i, kind, v in r.shares:
            if not r.flex[i]:
                continue
            fv = []
            for k in ks:
                jj = feeds[k][3]
                c_ = -v * float(r.dm[jj]) * S[k] + (float(r.dm[jj]) * S[k] if jj == i else 0.0)
                fv.append((k, c_))
            sgn = -1.0 if kind == "min" else 1.0
            add(sgn * (-v * dfix), [(k, sgn * c_) for k, c_ in fv], "share_" + kind)
    Gf = sparse.csr_matrix(np.array(rows)) if rows else sparse.csr_matrix((0, N))
    # cone rows (3 per feed)
    cr, cc, cv = [], [], []
    for k, (a, f, r, j) in enumerate(feeds):
        xa = act_idx[a]; base = 3 * k
        for rr, col, v in ((base, xa, -1.0 / X[k]), (base, iT[k], -1.0), (base + 1, iF[k], -2.0),
                           (base + 2, xa, -1.0 / X[k]), (base + 2, iT[k], 1.0)):
            cr.append(rr); cc.append(col); cv.append(v)
    Gc = sparse.csr_matrix((cv, (cr, cc)), shape=(3 * nf, N))
    blk = dict(feeds=feeds, act_idx=act_idx, nf=nf, N=N, iF=iF, iT=iT, S=S, X=X, qT=qT, qF_cnst=qF_cnst,
               comp=comp, fod_cols=fod_cols.tocsr(), zero_cells=zero_cells, Gf=Gf, labels=labels, scales=scales, Gc=Gc,
               _rations=rations)
    _BLOCK_CACHE[key] = blk
    return blk


# ---------------------------------------------------------------------------------------
# GENERIC ASSEMBLY (v2): blocks of variables, linear rows and rotated cones, stacked once.
# Blocks: feed (cached), CAPRI's ammonia technologies, CAPRI's fertiliser technologies.
# ---------------------------------------------------------------------------------------
def _rot_cone_rows(N, u_col, v_terms, w_terms):
    """Rows for u*v >= w^2 (u = one column; v, w linear: lists of (col, coef)):
    ||(2w, u - v)|| <= u + v  ->  three rows G with h = 0 (Clarabel: h - G x in SOC)."""
    r0 = np.zeros(N); r1 = np.zeros(N); r2 = np.zeros(N)
    r0[u_col] -= 1.0
    for col, v in v_terms:
        r0[col] -= v
    for col, w in w_terms:
        r1[col] -= 2.0 * w
    r2[u_col] -= 1.0
    for col, v in v_terms:
        r2[col] += v
    return [r0, r1, r2]


def solve_regional_conic(Q, c, A, b, acts, rations, fodder_rows, x_base, prices=None,
                         techs=None, fert=None, n_row=None, tol=1e-8, req_extra=None, m_row=None, feed_ghg=None,
                         mni=None):
    """Regional problem with feeding (CAPRI REQSN_/REQSE_/FEDUSE_/QUADRF_), CAPRI's ammonia
    technologies (v_Miti) and CAPRI's fertiliser technologies, as one convex conic program.

    fert = {"crops": [(col, n_c)], "techs": [(name, NMIN, S0, slope, smax)]}: per fertilised crop
    c, mineral N m_c >= n_c area_c^2 / (area_c + sum_t NMIN_t H_ct)  (CAPRI: mineral N x
    (1 + E) = need, written per crop - exact, a rotated cone); H_ct adopted hectares,
    0 <= H_ct <= max_t area_c, sum_t H_ct <= area_c; cost per t of need (CAPRI) x need per ha
    n_c / 1000: (S0_t H + 0.5 slope_t H^2 / area_c) n_c / 1000 (CAPRI s0 = 0). The crop's mineral part n_c leaves its N-row coefficient and m_c
    enters with +1. DEPARTURE (registered): adoption is crop-specific; CAPRI uses one
    regional share per technology (uniform shares would make the problem non-convex).

    mni = {"w": [(col, mN_a)], "eff": sub x NMAN, "smax", "S0", "slope", "vtax"}: CAPRI's nitrification
    inhibitor on applied manure (capri-mod-proto). T = manure N treated (t), W = sum_a mN_a x_a (t);
    T <= smax W; the N row gains -eff T; cost per t treated S0 + 0.5 slope s with s = T / W, i.e.
    S0 T + 0.5 slope T^2 / W (EUR, perspective: rotated cone U W >= T^2) less the emission tax saved
    vtax T. One regional share, as CAPRI (the perspective keeps it convex).
    """
    import clarabel
    from scipy import sparse
    Q = np.asarray(Q, float); A = np.asarray(A, float).copy(); b = np.asarray(b, float); c = np.asarray(c, float)
    n0, m_A = Q.shape[0], A.shape[0]
    xb = np.maximum(np.asarray(x_base, float), 0.0)
    B = _feed_block(n0, m_A, acts, rations, fodder_rows, xb) if rations else None
    nf = B["nf"] if B else 0
    act_idx = B["act_idx"] if B else {a: i for i, a in enumerate(acts)}
    # ---- variable layout ----
    cols = {"n0": n0}
    N = n0 + 2 * nf                                        # y | F | t
    techs = [t for t in (techs or []) if t["act"] in act_idx and t["smax"] > 0]
    nt = len(techs); iM = {k: N + k for k in range(nt)}; iU = {k: N + nt + k for k in range(nt)}; N += 2 * nt
    fc = [(col, nc) for col, nc in (fert or {}).get("crops", []) if nc > 0]
    ft = (fert or {}).get("techs", [])
    nfc, nft = len(fc), len(ft)
    iH = {(i, t): N + i * nft + t for i in range(nfc) for t in range(nft)}; N += nfc * nft
    iMin = {i: N + i for i in range(nfc)}; N += nfc
    iV = {(i, t): N + i * nft + t for i in range(nfc) for t in range(nft)}; N += nfc * nft
    mw = [(int(col), float(m)) for col, m in ((mni or {}).get("w") or []) if m > 0]
    XW = float(sum(m * xb[col] for col, m in mw)) if mw else 0.0
    use_mni = bool(mw) and XW > 1e-9 and float(mni.get("smax", 0.0)) > 0
    if use_mni:
        iT, iTU = N, N + 1; N += 2
        ST = max(float(mni["smax"]) * XW, 1e-6)
    # ---- scales ----
    SM, XM = {}, {}
    for k, t in enumerate(techs):
        XM[k] = max(float(t["w"]) * float(xb[act_idx[t["act"]]]), 1e-3)     # sub-activity units at base
        SM[k] = max(max(t["s0"], 0.05 * t["smax"]) * XM[k], 1e-3)
    # ---- objective ----
    q = np.zeros(N); q[:n0] = c
    if B:
        q[:n0] -= B["comp"]
        qF = B["qF_cnst"].copy()
        for k, (a, f, r, j) in enumerate(B["feeds"]):
            # CAPRI's emission tax on enteric CH4 of the feed fed (ghgTax; EUR/kg of feed), fodder included
            if feed_ghg and (a, f) in feed_ghg:
                qF[k] += float(feed_ghg[(a, f)]) * B["S"][k]
            if f in fodder_rows:
                continue
            pv = (prices or {}).get(a)
            qF[k] += (float(pv[j]) if pv is not None else float(r.p0[j])) * B["S"][k]
        q[n0:n0 + nf] = qF; q[n0 + nf:n0 + 2 * nf] = B["qT"]
    # CAPRI's ammonia options (v_Miti): M = share x units of the sub-activity (w x herd). Cost per
    # animal place, relative to the base shares (CAPRI's calibration): thresh (s - s0) +
    # 0.5 slope (s - s0)^2, times places = stock x w x herd ->
    # stock [(thresh - slope s0) M + 0.5 slope M^2 / (w x) + (0.5 slope s0^2 - thresh s0) w x].
    for k, t in enumerate(techs):
        sl, th, s0, w = float(t["slope"]), float(t["th"]), float(t["s0"]), float(t["w"])
        q[iM[k]] = t["stock"] * (th - sl * s0) * SM[k]
        q[iU[k]] = 0.5 * sl * t["stock"] * SM[k] * SM[k] / (XM[k] * max(w, 1e-12))
        q[act_idx[t["act"]]] += t["stock"] * (0.5 * sl * s0 * s0 - th * s0) * w
        # CAPRI's emission tax on the option (per unit of M, relative to the base shares the activity's own
        # emission coefficient was taken at: the activity carries - ghg x s0 x w)
        g = float(t.get("ghg", 0.0) or 0.0)
        if g:
            q[iM[k]] += g * SM[k]
            q[act_idx[t["act"]]] -= g * s0 * w
        # the tax on the N kept (indirect N2O of the NH3, soil N2O of the mineral N it displaces), per t N kept, on the
        # cascade's tangent like the N row: - gn x [ret x (share - s_lin) + rel0] per unit of the sub-activity
        gn = float(t.get("ghg_n", 0.0) or 0.0)
        if gn:
            s_lin = float(t.get("s_lin", s0)); ret = float(t["ret"])
            q[iM[k]] -= gn * ret * SM[k]
            q[act_idx[t["act"]]] += gn * (ret * s_lin - float(t.get("rel0", 0.0))) * w
    # CAPRI's fertiliser options cost per tonne of crop N need (GHG_Mit_Cost_: x mineral N x
    # (1 + E)); crop c's need per ha = its base mineral N n_c (kg/ha) / 1000 (base E = 0)
    for i, (col, nc) in enumerate(fc):
        for tt, (name, nm, a_, b_, smax) in enumerate(ft):
            q[iH[(i, tt)]] = a_ * nc / 1000.0
            q[iV[(i, tt)]] = 0.5 * b_ * nc / 1000.0
    # CAPRI's emission tax on mineral N (ghgTax, Sprint 9l): fert["tax"] = {"m": per t of mineral N m_c, "h": [per
    # unit H per kg N/ha of need, by option]}. The crop's own emission coefficient already carries n_c x area at the
    # base factor, so the crop column gives that part back and m_c carries it at the solve's mineral N.
    qt = (fert or {}).get("tax")
    if qt:
        for i, (col, nc) in enumerate(fc):
            q[iMin[i]] += float(qt["m"])
            q[col] -= float(qt["m"]) * nc
            for tt in range(nft):
                q[iH[(i, tt)]] += float(qt["h"][tt]) * nc
    if use_mni:
        q[iT] = (float(mni["S0"]) - float(mni.get("vtax", 0.0))) * ST / 1000.0
        q[iTU] = 0.5 * float(mni["slope"]) * ST * ST / (1000.0 * XW)
    # ---- A rows (original constraints) with fodder columns, N-row changes ----
    if B:
        for ri, ci in B["zero_cells"]:
            A[ri, ci] = 0.0
    # the fertilised crops' mineral part leaves its coefficient on the N row and, with CAPRI's mineral
    # fertiliser cap (m_row: mineRedu), on the mineral N row; m_c enters both with +1
    fert_rows = [r_ for r_ in (n_row, m_row) if r_ is not None]
    for r_ in fert_rows:
        for col, nc in fc:
            A[r_, col] -= nc
    keep = np.ones(m_A, bool)
    keep[b > 1e4 * (np.abs(A) @ np.abs(xb) + 1.0)] = False
    for r_ in fert_rows:
        keep[r_] = True
    # assembled from blocks (a LIL matrix filled cell by cell was a visible share of each solve; same entries)
    A2 = A.copy()
    er, ec, ev = [], [], []                                  # entries of the columns after y | F | t
    # ammonia options: manure N kept from losses reaches the field and displaces mineral N (sub x ret per unit);
    # that is their whole effect on the N balance row and on the mineral N row (mineRedu) alike
    for r_ in [r__ for r__ in (n_row, m_row) if r__ is not None]:
        for k, t in enumerate(techs):
            coef = t["sub"] * t["ret"]
            er.append(r_); ec.append(iM[k] - (n0 + 2 * nf)); ev.append(-coef * SM[k])
            # tangent of CAPRI's loss cascade at the linearisation point s_lin: N saved per unit of the sub-activity
            # sub x [rel0 + ret x (share - s_lin)] (rel0 once per sub-activity); without s_lin/rel0, relative to the base
            s_lin = float(t.get("s_lin", t["s0"]))
            A2[r_, act_idx[t["act"]]] = A2[r_, act_idx[t["act"]]] + coef * s_lin * t["w"] \
                - t["sub"] * float(t.get("rel0", 0.0)) * t["w"]
    for r_ in fert_rows:
        for i in range(nfc):
            er.append(r_); ec.append(iMin[i] - (n0 + 2 * nf)); ev.append(1.0)
    if use_mni and n_row is not None:
        er.append(n_row); ec.append(iT - (n0 + 2 * nf)); ev.append(-float(mni["eff"]) * ST)
    _blocks = [sparse.csr_matrix(A2)]
    if 2 * nf:
        _blocks.append(B["fod_cols"] if B else sparse.csr_matrix((m_A, 2 * nf)))
    if N - (n0 + 2 * nf):
        _blocks.append(sparse.csr_matrix((ev, (er, ec)), shape=(m_A, N - (n0 + 2 * nf))))
    GA = sparse.hstack(_blocks).tocsr()
    GA.eliminate_zeros()
    GA = GA[keep]; hA = b[keep]
    lin, rhs = [GA], [hA]
    if B:
        Gf = sparse.hstack([B["Gf"], sparse.csr_matrix((B["Gf"].shape[0], N - (n0 + 2 * nf)))]).tocsr()
        # extra columns of the animals' requirement rows (CAPRI's dairy split: per head of DCOL
        # instead of DCOH the requirements change): req_extra = {act: (col, {label: change})},
        # change in the row's own units (requirement per head)
        if req_extra:
            ri, ci, vv = [], [], []
            for i_, (a_, lab_) in enumerate(B["labels"]):
                exs = req_extra.get(a_)
                if exs and isinstance(exs, tuple):
                    exs = [exs]
                for ex in (exs or []):
                    if lab_ in ex[1]:
                        sgn = -1.0 if lab_ == "DMAX" else 1.0
                        ri.append(i_); ci.append(int(ex[0])); vv.append(sgn * float(ex[1][lab_]) / B["scales"][i_])
            if ri:
                Gf = (Gf + sparse.csr_matrix((vv, (ri, ci)), shape=Gf.shape)).tocsr()
        lin.append(Gf); rhs.append(np.zeros(Gf.shape[0]))
    rows = []
    for k, t in enumerate(techs):
        r_ = np.zeros(N); r_[iM[k]] = SM[k]; r_[act_idx[t["act"]]] = -t["smax"] * t["w"]; rows.append(r_)
    grp = {}
    for k, t in enumerate(techs):                       # CAPRI TotMit_: NH3MAN, NH3APP per sub-activity
        grp.setdefault(t["grp"], []).append(k)
    for (a, key_, g_), ks in grp.items():
        r_ = np.zeros(N); r_[act_idx[a]] = -float(techs[ks[0]]["w"])
        for k in ks:
            r_[iM[k]] = SM[k]
        rows.append(r_)
    for i, (col, nc) in enumerate(fc):
        r_ = np.zeros(N); r_[col] = -1.0
        for tt, (name, nm, a_, b_, smax) in enumerate(ft):
            r_[iH[(i, tt)]] = 1.0
            r1 = np.zeros(N); r1[iH[(i, tt)]] = 1.0; r1[col] = -smax; rows.append(r1)
        rows.append(r_)
    # CAPRI Tot_MitFert_ (supply_model.gms): "Total N savings from fertilizer measures shall not
    # exceed overfertilisation": 1 + sum share x NMIN <= max(x + 0.1, 1). With crop-specific
    # adoption, each crop's gain is weighted by its N need n_c (over-fertilisation on crop c is
    # (x - 1) x its need): sum_c n_c sum_t NMIN_t H_ct <= cap x sum_c n_c area_c. Under CAPRI's
    # uniform shares this IS its constraint; area weights let adoption concentrate on N-hungry
    # crops and save more N than CAPRI allows (2030 Farm-to-Fork: herds cut ~1.7 points less).
    ecap = (fert or {}).get("ecap")
    if fc and ecap is not None:
        r_ = np.zeros(N)
        for i, (col, nc) in enumerate(fc):
            r_[col] = -float(ecap) * nc
            for tt in range(nft):
                r_[iH[(i, tt)]] = float(ft[tt][1]) * nc
        rows.append(r_)
    if use_mni:
        r_ = np.zeros(N); r_[iT] = ST
        for col, m in mw:
            r_[col] -= float(mni["smax"]) * m
        rows.append(r_)
    if rows:
        lin.append(sparse.csr_matrix(np.array(rows))); rhs.append(np.zeros(len(rows)))
    m_lin = sum(L.shape[0] for L in lin)
    # ---- cones ----
    soc = []
    if B:
        soc.append(sparse.hstack([B["Gc"], sparse.csr_matrix((B["Gc"].shape[0], N - (n0 + 2 * nf)))]).tocsr())
    cr_, cc_, cv_ = [], [], []                               # cone rows as triplets (same entries as dense rows)
    _nc = [0]

    def _cone(u_col, v_terms, w_terms):
        b0 = 3 * _nc[0]; _nc[0] += 1
        cr_.append(b0); cc_.append(u_col); cv_.append(-1.0)
        cr_.append(b0 + 2); cc_.append(u_col); cv_.append(-1.0)
        for col, v in v_terms:
            cr_.append(b0); cc_.append(col); cv_.append(-v)
            cr_.append(b0 + 2); cc_.append(col); cv_.append(v)
        for col, w in w_terms:
            cr_.append(b0 + 1); cc_.append(col); cv_.append(-2.0 * w)
    for k, t in enumerate(techs):
        xa = act_idx[t["act"]]
        # U x / XM >= M^2 (scaled), U priced with 1 / w (q[iU] above): the cost 0.5 slope M^2 / (w x) per place, as
        # documented. K2: the weight w of the sub-activity was missing, which made the quadratic cost w times too small
        # (adoption too high in split activities). The weight goes on the cost, not into the cone: written as
        # U w x / XM >= M^2 the same problem was declared PrimalInfeasible by Clarabel in three Romanian regions under
        # the emission tax (K11)
        _cone(iU[k], [(xa, 1.0 / XM[k])], [(iM[k], 1.0)])
    for i, (col, nc) in enumerate(fc):
        _cone(iMin[i], [(col, 1.0)] + [(iH[(i, tt)], ft[tt][1]) for tt in range(nft)], [(col, float(np.sqrt(nc)))])
        for tt in range(nft):
            _cone(iV[(i, tt)], [(col, 1.0)], [(iH[(i, tt)], 1.0)])
    if use_mni:
        _cone(iTU, [(col, m / XW) for col, m in mw], [(iT, 1.0)])
    if _nc[0]:
        Gc_ = sparse.csr_matrix((cv_, (cr_, cc_)), shape=(3 * _nc[0], N))
        Gc_.sum_duplicates(); Gc_.eliminate_zeros()
        soc.append(Gc_)
    n_soc = sum(S_.shape[0] for S_ in soc) // 3
    G = sparse.vstack(lin + [-sparse.identity(N, format="csr")] + soc).tocsc()
    h = np.concatenate(rhs + [np.zeros(N), np.zeros(3 * n_soc)])
    cones = [clarabel.NonnegativeConeT(m_lin + N)] + [clarabel.SecondOrderConeT(3)] * n_soc
    # ---- scaling and solve ----
    sc = np.ones(N); sc[:n0] = np.maximum(np.abs(xb), 1.0)
    Dg = sparse.diags(sc)
    P = sparse.block_diag([sparse.csc_matrix(0.5 * (Q + Q.T)), sparse.csc_matrix((N - n0, N - n0))]).tocsc()
    P = sparse.triu(Dg @ P @ Dg).tocsc(); G = (G @ Dg).tocsc(); q = q * sc
    st = clarabel.DefaultSettings(); st.verbose = False
    st.tol_feas = st.tol_gap_abs = st.tol_gap_rel = tol
    st.max_iter = 400; st.equilibrate_max_iter = 50
    sol = clarabel.DefaultSolver(P, q, G, h, cones, st).solve()
    # a stalled interior point (InsufficientProgress: IE05 under Farm-to-Fork with the inhibitor on manure at its
    # maximum share, relative gap 1e-4) is re-solved with more static regularisation of the KKT system; regions
    # solved at the first attempt are untouched
    for _reg in (1e-7, 1e-6):
        if str(sol.status) not in ("InsufficientProgress", "MaxIterations", "NumericalError"):
            break
        st.static_regularization_constant = _reg
        sol = clarabel.DefaultSolver(P, q, G, h, cones, st).solve()
    # a declared infeasibility is re-checked with tighter infeasibility tolerances (K14, docs/KNOWN_ISSUES.md): FI1C under
    # the Green Deal was declared DualInfeasible after 5 iterations, yet the same problem solves to a finite optimum with
    # tol_infeas 1e-12 (IPOPT agrees); before, the region fell back to the model without technologies in every iteration
    if str(sol.status) in ("PrimalInfeasible", "DualInfeasible", "AlmostPrimalInfeasible", "AlmostDualInfeasible"):
        st.static_regularization_constant = 1e-8
        st.tol_infeas_abs = st.tol_infeas_rel = 1e-12
        sol2 = clarabel.DefaultSolver(P, q, G, h, cones, st).solve()
        if str(sol2.status) in ("Solved", "AlmostSolved"):
            sol = sol2
    xs, z, status = np.array(sol.x), np.array(sol.z), str(sol.status)
    # IPOPT polish (CasADi): a solve Clarabel could not finish to its tolerances (AlmostSolved after a stall, or still
    # stalled) is completed by IPOPT on the SAME convex problem, started from Clarabel's point; kept only when feasible
    # and at least as good. IE05 under Farm-to-Fork: Clarabel AlmostSolved 2e-4 short of the optimum.
    if status in _POLISH_STATUSES:
        import time as _time
        _t0 = _time.time()
        pol = _ipopt_polish(P, q, G, h, m_lin, N, n_soc, xs, float(getattr(sol, "obj_val", np.inf)), status)
        if os.environ.get("CAPRI_POLISH_LOG"):
            _o, _d = float(getattr(sol, "obj_val", np.nan)), float(getattr(sol, "obj_val_dual", np.nan))
            print(f"POLISH {os.environ.get('CAPRI_POLISH_TAG', '')} {status} -> "
                  f"{'accepted' if pol is not None else 'rejected'} N={N} {_time.time() - _t0:.2f}s "
                  f"gap {abs(_o - _d) / max(1.0, abs(_o)):.1e} rp {float(getattr(sol, 'r_prim', np.nan)):.1e} "
                  f"rd {float(getattr(sol, 'r_dual', np.nan)):.1e}"
                  + (f" gain {(_o - float(0.5 * pol[0] @ (P @ pol[0]) + q @ pol[0] + 0.5 * pol[0] @ (P.T @ pol[0]) - 0.5 * pol[0] @ (sparse.diags(P.diagonal()) @ pol[0]))) / max(1.0, abs(_o)):.1e}" if pol is not None else ""),
                  flush=True)
        if pol is not None:
            xs, z_lin, status = pol
            z = np.concatenate([z_lin, np.zeros(len(z) - len(z_lin))])
    y = xs * sc
    F = {(B["feeds"][k][0], B["feeds"][k][1]): float(y[n0 + k]) * B["S"][k] for k in range(nf)} if B else {}
    zA = np.zeros(m_A); zA[keep] = z[:int(keep.sum())]
    # duals of the requirement rows per unit of requirement per head (row scale undone)
    req_duals = {}
    if B:
        off = int(keep.sum())
        for i_, key_ in enumerate(B["labels"]):
            req_duals[key_] = float(z[off + i_]) / B["scales"][i_]
    info = {"status": status, "iterations": getattr(sol, "iterations", None), "n_feed_vars": nf,
            "tech_M": {(t["act"], t["key"], t["tech"]): float(y[iM[k]]) * SM[k] for k, t in enumerate(techs)},
            "fert_H": {(fc[i][0], ft[tt][0]): float(y[iH[(i, tt)]]) for i in range(nfc) for tt in range(nft)},
            "fert_m": {fc[i][0]: float(y[iMin[i]]) for i in range(nfc)}, "req_duals": req_duals,
            "mni_T": (float(y[iT]) * ST if use_mni else 0.0),
            "mni_W": (float(sum(m * y[col] for col, m in mw)) if use_mni else 0.0)}
    return y[:n0], F, zA, info


# ---------------------------------------------------------------------------------------
# IPOPT polish of solves Clarabel could not finish (docs/KNOWN_ISSUES.md K4)
# ---------------------------------------------------------------------------------------
_POLISH_STATUSES = ("AlmostSolved", "InsufficientProgress", "MaxIterations", "NumericalError")
POLISH_STATS = {"calls": 0, "accepted": 0}


def _ipopt_polish(P, q, G, h, m_lin, N, n_soc, x0, obj0, status0):
    """min 0.5 x'Px + q'x  s.t.  h - Gx in (R+^m_lin x R+^N x SOC3^n_soc), the problem Clarabel was given (scaled), by
    IPOPT from Clarabel's point x0. The second-order cones as s0 >= 0, s0^2 - s1^2 - s2^2 >= 0 (the same set). Returns
    (x, duals of the m_lin linear rows, status) or None (CasADi missing, IPOPT failed, not feasible, or not better).
    The linear rows' duals are IPOPT's multipliers, in the units of Clarabel's (same objective, same rows)."""
    try:
        import casadi as ca
    except ImportError:
        return None
    from scipy import sparse
    POLISH_STATS["calls"] += 1
    Pf = sparse.csc_matrix(P)
    Pf = (Pf + Pf.T - sparse.diags(Pf.diagonal())).tocsc()
    G = sparse.csr_matrix(G)
    Gl, hl = G[:m_lin], np.asarray(h[:m_lin], float)
    Gc, hc = G[m_lin + N:], np.asarray(h[m_lin + N:], float)
    x = ca.SX.sym("x", N)
    f = 0.5 * ca.mtimes([x.T, ca.DM(Pf), x]) + ca.dot(ca.DM(np.asarray(q, float)), x)
    gl = ca.mtimes(ca.DM(Gl), x)
    parts, lb, ub = [gl], [-np.inf] * m_lin, list(hl)
    if n_soc:
        sv = ca.DM(hc) - ca.mtimes(ca.DM(Gc), x)
        s0, s1, s2 = sv[0::3], sv[1::3], sv[2::3]
        parts += [s0, s0 * s0 - s1 * s1 - s2 * s2]
        lb += [0.0] * (2 * n_soc); ub += [np.inf] * (2 * n_soc)
    g = ca.vertcat(*parts)
    opts = {"ipopt.print_level": 0, "print_time": 0, "ipopt.tol": 1e-9, "ipopt.max_iter": 3000,
            "ipopt.bound_push": 1e-8, "ipopt.bound_frac": 1e-8, "ipopt.mu_init": 1e-6,
            "ipopt.warm_start_init_point": "yes", "ipopt.sb": "yes"}
    try:
        S = ca.nlpsol("polish", "ipopt", {"x": x, "f": f, "g": g}, opts)
        r = S(x0=np.maximum(np.nan_to_num(x0), 0.0), lbx=0.0, ubx=np.inf, lbg=lb, ubg=ub)
    except Exception:
        return None
    st = S.stats().get("return_status", "")
    if st not in ("Solve_Succeeded", "Solved_To_Acceptable_Level"):
        return None
    xs = np.maximum(np.asarray(r["x"]).ravel(), 0.0)
    # feasibility in the problem's own terms, and the objective against Clarabel's
    viol_l = float(np.max(Gl @ xs - hl, initial=0.0))
    viol_c = 0.0
    if n_soc:
        sc_ = hc - Gc @ xs
        viol_c = float(np.max(np.sqrt(sc_[1::3] ** 2 + sc_[2::3] ** 2) - sc_[0::3], initial=0.0))
    tol_f = 1e-6 * (1.0 + float(np.max(np.abs(hl), initial=0.0)))
    fx = float(r["f"])
    if max(viol_l, viol_c) > tol_f:
        return None
    if np.isfinite(obj0) and status0 == "AlmostSolved" and fx > obj0 + 1e-9 * max(1.0, abs(obj0)):
        return None
    POLISH_STATS["accepted"] += 1
    return xs, np.maximum(np.asarray(r["lam_g"]).ravel()[:m_lin], 0.0), "Solved (IPOPT polish)"
