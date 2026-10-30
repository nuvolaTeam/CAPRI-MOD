"""CAPRI's regional supply model in its own form, solved as a non-convex NLP with IPOPT (docs/NLP_PORT_DESIGN.md).

CAPRI solves m_capModQ (supply/supply_model.gms) with CONOPT; this module writes the same equations block by block and
solves them with IPOPT (CasADi). What capri-mod already builds as data and calibration is taken over as it is: the
regional QP as assembled by RegionalSupplyModel (activity and auxiliary columns, PMP matrix Q and linear terms c,
land-market columns, land and bound rows, with one label per row) and the calibrated rations. What is CAPRI's here:

* feeding (block "feeding"):
    REQSE_   per head, an EQUALITY for energy (ENNE) and crude protein (CRPR) only (feed version _pw: REQSN_, MAXSHR_,
             MINSHR_ are not in the simulation model);  sum_f v_feedInpCoeff_f x content_f = requirement, with the
             requirement the base ration's supply (CAPRI simulates with the trimmed p_animReq, p_trimFeed = 0, so the
             base ration meets it exactly).
    FEDUSE_  feed use = per-head feed x herd / 1000 (bilinear), entering the non-tradable fodder balances.
    QUADRF_  herd x sum_f f (CNST + 0.5 SLOP f), with the feed's price for tradable feeds.
    Bounds   0 <= v_feedInpCoeff <= 10 x DRMX / DM content (supply/set_supply_bounds.gms).
* fodder (SUPBAL_ for FODDO): production = feed use, an EQUALITY (the former conic form had a one-sided band).
* single-variable rows (CAPRI's activity bounds, fixed levels) as variable bounds; pairs of opposite rows as one ranged
  row (land balances: equal at base use, LandBalNoSlak_).

* fertilisation: NUTNED_ for N, P2O5 and K2O per crop group with the first-order conditions of CAPRI's inner fertiliser
  model inside, mineral purchases at CAPRI's unit values, endogenous manure availability (manure trade rows).
* CAP greening (permGras, ecoSetAside, cropDiv Shannon), the N-surplus target, the Green Deal's mineral caps and organic
  area target, the ammonia, fertiliser-technique and inhibitor options through CAPRI's N loss cascade, the emission tax.

Breeding, low-N feed, linseed, nitrate and 3-NOP (and histosol fallowing) are linear columns the supply module adds.
Not built: legume share, tillage, urea substitution, buffer strips, biodiversity options, biochar, and CAPRI's ration
fat constraint SupplementPerc_ (KNOWN_ISSUES K93).

CALIBRATION of the feed terms. The rations were calibrated (feed/ration.py) with CAPRI's fixed feed shares and dry-matter
limits; CAPRI's simulation model has only REQSE_. As CAPRI's PMP calibration does, the linear terms are set so that the
base ration is optimal under the simulation model's own constraints: per animal the requirement duals (energy,
protein; free in sign, equalities) are the least-squares fit of the base first-order conditions
    p_f + CNST_f + SLOP_f x0_f = lambda_E e_f + lambda_P cp_f        (feeds used at base)
and CNST takes the residual; feeds not used at base keep a non-negative reduced cost. The animal's own linear term is
compensated by the change in the base ration's cost, so the herd's first-order condition at base is unchanged.
"""
from __future__ import annotations

import hashlib
import os
from collections import OrderedDict

import numpy as np


#: IPOPT solvers by the structure of the problem (SOLVER CACHE). Every data value of the model enters its CasADi graph
#: as a parameter, so two builds with the same structure (columns, rows, feeds, groups, options) give the same graph
#: whatever the numbers; the graph's serialisation is the key. A data value left as a constant only costs a cache miss,
#: never a wrong solve. The cache is per process: the regional solves' worker processes are forked for each round
#: of solves, so it serves the solves of a region within a round and, run in one process, across rounds. Least recently
#: used entries go beyond CAPRI_NLP_CACHE (default 64; about 6 MB each). (Sending the workers' solvers back to the main
#: process was tried: the full run ran out of memory.)
_SOLVERS: "OrderedDict[tuple, object]" = OrderedDict()
#: the Lagrangian's Hessian and the rows' Jacobian per graph, for CapriRegionalNLP.response
_SENS: "OrderedDict[str, tuple]" = OrderedDict()
# IPOPT's iteration limits, tolerances and CPU guard, and the solver cache size, are settings
# (capri_mod/settings/defaults.toml [supply] nlp_*, [run] nlp_cache_size)
CACHE_STATS = {"hit": 0, "miss": 0}


#: ridge weight of the calibration's multiplier fit (CapriRegionalNLP.calibrate), relative to the scaled columns
CAL_RIDGE = 1e-10

#: the market supply Hessian from the KKT conditions (market.hessian_method = "kkt"; beyond CAPRI, which re-solves its
#: supply models at 1% price shocks): None, "record" (the base solve: each successful solve's primal-dual point is kept
#: on the regional model, per graph) or "apply" (a shock: a solve of a recorded graph is replaced by the first-order
#: step of the KKT conditions from the recorded point, CapriRegionalNLP.kkt_step). Set by model._market_supply_hessian
#: before the supply module's run; the forked workers inherit it
KKT_MODE = None
#: the KKT step's functions per graph (the Lagrangian's gradient's and the rows' directional derivatives in p)
_KKT: "OrderedDict[str, tuple]" = OrderedDict()

#: called as SOLVE_PROBE(fingerprint) before each IPOPT solve when set (the market supply Hessian's skip of regions a
#: price shock does not reach: SupplyModule._solve_region, model._market_supply_hessian); None otherwise
SOLVE_PROBE = None


def _feed_hash(h, o, depth=0):
    """Everything in o that a solve can read, in a fixed order, into the hash h: arrays by dtype, shape and bytes,
    floats exactly, containers in order (dicts and sets sorted by key), objects by their attributes."""
    if depth > 12:
        h.update(b"<deep>")
        return
    if o is None or isinstance(o, (bool, int, str, bytes)):
        h.update(repr((type(o).__name__, o)).encode())
    elif isinstance(o, float):
        h.update(b"f" + np.float64(o).tobytes())
    elif isinstance(o, np.generic):
        h.update(repr(o.dtype).encode() + np.asarray(o).tobytes())
    elif isinstance(o, np.ndarray):
        a = np.ascontiguousarray(o)
        if a.dtype == object:
            h.update(b"objarr" + repr(a.shape).encode())
            for v in a.ravel():
                _feed_hash(h, v, depth + 1)
        else:
            h.update(repr((a.dtype.str, a.shape)).encode() + a.tobytes())
    elif isinstance(o, (list, tuple)):
        h.update(b"(" + str(len(o)).encode())
        for v in o:
            _feed_hash(h, v, depth + 1)
        h.update(b")")
    elif isinstance(o, dict):
        h.update(b"{" + str(len(o)).encode())
        for k in sorted(o, key=repr):
            h.update(repr(k).encode())
            _feed_hash(h, o[k], depth + 1)
        h.update(b"}")
    elif isinstance(o, (set, frozenset)):
        _feed_hash(h, sorted(o, key=repr), depth + 1)
    elif type(o).__name__ == "DM" and hasattr(o, "full"):          # CasADi numbers
        _feed_hash(h, np.asarray(o.full()), depth + 1)
    elif hasattr(o, "to_numpy") and hasattr(o, "index"):          # pandas
        _feed_hash(h, (type(o).__name__, list(o.index), list(getattr(o, "columns", [])), o.to_numpy()), depth + 1)
    elif hasattr(o, "__dict__"):
        h.update(type(o).__qualname__.encode())
        _feed_hash(h, vars(o), depth + 1)
    else:
        h.update(repr(o).encode())                                  # (a CasADi object: its printed expression)


def problem_fingerprint(spec, kw, opts) -> str:
    """A digest of one IPOPT solve's inputs: the problem specification, the start, bounds, parameters and warm-start
    multipliers, and the options. Two solves with the same digest give the same result (IPOPT is deterministic)."""
    import hashlib
    h = hashlib.sha256()
    _feed_hash(h, spec)
    _feed_hash(h, kw)
    _feed_hash(h, opts)
    return h.hexdigest()


def linear_solver_options() -> dict:
    """IPOPT's linear solver options from supply.nlp_linear_solver / supply.nlp_hsllib, for every IPOPT solve of the
    model. MUMPS (the default) adds no option, so its solver objects and cache keys are those of before the setting; an
    HSL solver needs its library, and a missing one stops here rather than IPOPT failing in every region (IPOPT returns
    Invalid_Option, which the regional fallbacks would treat as a failed solve)."""
    from capri_mod.settings import current as _settings
    ls = str(_settings().get("supply.nlp_linear_solver")).strip().lower()
    if ls == "mumps":
        return {}
    if ls == "spral":
        # SPRAL (BSD licence) is part of CasADi's IPOPT; it runs on OpenMP. IPOPT's documentation asks for
        # OMP_CANCELLATION=TRUE and OMP_PROC_BIND=TRUE; the model runs its regional solves in CAPRI_WORKERS processes,
        # so each solve takes one thread (OMP_NUM_THREADS=1) unless the environment says otherwise. The OpenMP runtime
        # reads them when it starts: the run scripts set them before (tools/run), this is the fallback
        for k_, v_ in (("OMP_CANCELLATION", "TRUE"), ("OMP_PROC_BIND", "TRUE"), ("OMP_NUM_THREADS", "1")):
            os.environ.setdefault(k_, v_)
        return {"ipopt.linear_solver": "spral"}
    if ls not in ("ma27", "ma57", "ma77", "ma86", "ma97"):
        raise ValueError(f"supply.nlp_linear_solver = {ls!r}: mumps, spral, ma27, ma57, ma77, ma86 or ma97")
    lib = str(_settings().get("supply.nlp_hsllib")).strip()
    if not lib or not os.path.isfile(lib):
        raise FileNotFoundError(f"supply.nlp_linear_solver = {ls!r} needs the HSL library: supply.nlp_hsllib = {lib!r}")
    return {"ipopt.linear_solver": ls, "ipopt.hsllib": lib}


def _cache_max():
    """Solver objects kept: CAPRI_NLP_CACHE if set (a property of the machine's memory), else run.nlp_cache_size."""
    from capri_mod.settings import current as _settings
    try:
        return int(os.environ.get("CAPRI_NLP_CACHE", "") or _settings().get("run.nlp_cache_size"))
    except ValueError:
        return int(_settings().get("run.nlp_cache_size"))


def _cascade_loss(sub, sh):
    """CAPRI's NH3 loss per unit of excreted N (ammonia_techs.loss) with symbolic shares: sh {tech: expr}."""
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


class _AtP:
    """A CasADi function of (x, p) evaluated at the model's parameter values: f(x)."""

    def __init__(self, f, p):
        self.f, self.p = f, p

    def __call__(self, x):
        return self.f(x, self.p)


def ca_eval(expr, X, x, p=None, pval=None):
    import casadi as ca
    if p is None:
        return ca.Function("e", [X], [expr])(x)
    return ca.Function("e", [X, p], [expr])(x, pval)


def _feed_scale(r, j):
    """Scale of a per-head feed variable (kg/head): its base amount, or 1% of the base dry matter intake in this feed's
    units where the base ration does not use it."""
    x0 = float(r.x0[j])
    if x0 > 0:
        return x0
    D0 = float(r.dm @ r.x0)
    return max(0.01 * D0 / max(float(r.dm[j]), 1e-6), 1e-6)


def calibrate_feed_terms(r, fodder=()):
    """CNST of each flexible feed so that the base ration solves CAPRI's simulation feeding problem (REQSE_ only).

    Returns (cnst_new, lam {"E": .., "P": ..}, delta) with delta = cnst_new - r.cnst. Prices at base: the ration's p0
    (for fodder the base value, the expected dual of its balance)."""
    fl = np.asarray(r.flex, bool)
    g = np.where(fl, r.p0 + r.cnst + r.slope * r.x0, 0.0)
    pos = fl & (r.x0 > 0)
    lam = {"E": 0.0, "P": 0.0}
    cols, keys = [], []
    for k, v, R in (("E", r.e, float(r.e @ r.x0)), ("P", r.cp, float(r.cp @ r.x0))):
        if R > 0:
            cols.append(v); keys.append(k)
    delta = np.zeros(len(r.feeds))
    if pos.any() and cols:
        M = np.array(cols).T[pos]
        if not getattr(r, "lam", None):
            # the ration's requirements were below the base supply (not binding: its terms give the feeds no marginal
            # value). CAPRI simulates with the requirement trimmed to the base supply, which binds: the requirement
            # duals are then the fit of the feeds' base prices on their contents (non-negative), as feed/ration.py
            # does for a binding requirement
            from scipy.optimize import nnls
            sc_ = np.maximum(np.abs(M).max(axis=0), 1e-12)
            sol, _ = nnls(M / sc_, r.p0[pos])
            sol = sol / sc_
        else:
            sol, *_ = np.linalg.lstsq(M, g[pos], rcond=None)
        lam.update(dict(zip(keys, sol.tolist())))
    shadow = lam["E"] * r.e + lam["P"] * r.cp
    delta[pos] = shadow[pos] - g[pos]
    zero = fl & ~(r.x0 > 0)
    # feeds not used at base: reduced cost g - shadow >= 0 (keep the ration's own term where it already is)
    delta[zero] = np.maximum(shadow[zero] - g[zero], 0.0)
    return r.cnst + delta, lam, delta


class CapriRegionalNLP:
    """One region's supply model in CAPRI's form.

    spec: Q, c, A, b (the regional QP, A y <= b), labels (one per row of A), acts (activity names: the first len(acts)
    columns), rations {act: Ration}, fodder {feed: row of A}, x_base (base point of all columns, for scaling and the
    base-exactness check), prices {act: feed price vector aligned with the ration's feeds} or None, req_extra
    {act: [(col, {"E": d, "P": d, ...})]} or None (requirement change per unit of a split column), feed_ghg
    {(act, feed): EUR per t of feed} or None.
    """

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

        # ---------------- feed calibration (REQSE_ only) ----------------
        cal = {a: calibrate_feed_terms(r, fod) for a, r in rats.items()}
        self.feed_cal = {a: {"lam": v[1], "delta": v[2]} for a, v in cal.items()}

        # ---------------- objective ----------------
        q0 = c.copy()
        obj = 0
        for a, r in rats.items():
            cn = cal[a][0]
            fl = np.asarray(r.flex, bool)
            # the herd's linear term carries the base ration's cost per head (CNST, 0.5 SLOP, tradable feeds at base
            # prices; fodder through its balance); it is taken out here and charged through QUADRF_ below, exactly as
            # the feed block's compensation, with the calibrated CNST
            pz = np.array([0.0 if f in fod else float(r.p0[j]) for j, f in enumerate(r.feeds)])
            q0[act_idx[a]] -= float(np.sum(np.where(fl, r.x0 * (pz + cn + 0.5 * r.slope * r.x0), 0.0)))
        F = []
        if nf:
            lin_c, half_s = np.zeros(nf), np.zeros(nf)
            for k, (a, f, r, j, s) in enumerate(feeds):
                cn = float(cal[a][0][j]) + float((spec.get("dcnst") or {}).get((a, f), 0.0))
                p = 0.0
                if f not in fod:
                    pv = prices.get(a)
                    p = float(pv[j]) if pv is not None else float(r.p0[j])
                ghg = float(fg.get((a, f), 0.0) or 0.0)       # emission tax per kg of feed, as the price
                lin_c[k] = p + ghg + cn
                half_s[k] = 0.5 * float(r.slope[j])
            herds = y[[act_idx[fe[0]] for fe in feeds]]
            Fv = herds * fhv                                   # t
            obj = obj + ca.sum1(Fv * (self._pv(lin_c) + self._pv(half_s) * fhv))
            F = [Fv[k] for k in range(nf)]
        if spec.get("dq") is not None:
            q0 = q0 + np.asarray(spec["dq"], float)            # the base calibration's linear terms (calibrate())
        Qs = 0.5 * (Q + Q.T)
        # the PMP quadratic is kept apart: its Hessian is the matrix itself, given to IPOPT directly (_derivatives)
        self._Qsx = self._pmat(Qs)
        quad = 0.5 * ca.mtimes([y.T, self._Qsx, y])
        obj = obj + ca.dot(self._pv(q0), y)
        self.q0 = q0

        # ---------------- rows of the regional QP ----------------
        # fodder balances: animal cells replaced by FEDUSE_ (per-head feed x herd / 1000, flexible and fixed feeds)
        extra = {}
        fod_rows = {}
        for f, ri in fod.items():
            fod_rows[ri] = f
            for a in rats:
                A[ri, act_idx[a]] = 0.0
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
                ex = ex + extra[i] * ex_sc[k_ex]
                k_ex += 1
            if i in fod_rows:
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
                sup = (ca.dot(self._pv(cf), fhv[ks]) if len(ks) > 1 else (self._pv(cf[0]) * fh[ks[0]] if ks else 0)) \
                    + self._pv(float(vec[fixed] @ r.x0[fixed]) / R) - 1.0
                dz = [(int(col_), float(d_[nut])) for col_, d_ in (exs or []) if nut in d_ and float(d_[nut]) != 0.0]
                if dz:
                    # with a split column the requirement of the herd is R x herd + d x z (total form, bilinear)
                    Xa = max(float(xb[act_idx[a]]), 1e-3)
                    e_ = sup * herd * self._pv(1.0 / Xa) - self._lin(y, dz, scale=R * Xa)
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

        # ---------------- fertilisation (NUTNED_, pools, inner model) ----------------
        self.fert = None
        if spec.get("npk"):
            X, obj = self._fert_block(spec["npk"], X, y, obj, g_rows, lbg, ubg, lbx, ubx)
        if getattr(self, "_fert_tech_pending", None) is not None:
            # no N purchases in the model: the options' cost on the crops' base mineral N
            cost_, crops_ = self._fert_tech_pending
            obj = obj + self._lin(y, [(col, float(nc) / 1000.0) for col, nc in crops_]) * cost_
            self._fert_tech_base = sum(float(self.xb[int(col)]) * float(nc) / 1000.0 for col, nc in crops_)
            self._fert_tech_pending = None

        self._obj_rest, self._y = obj, y
        obj = obj + quad
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

    def _fert_block(self, npk, X, y, obj, g_rows, lbg, ubg, lbx, ubx):
        """CAPRI's fertilisation block, per nutrient n (N, P, K), with ghgAbatement off (losses at CAPRI's fixed
        shares, supply_model.gms l. 860-1215, 1535-1725):

          NUTNED_(g,n)    sum_c share_cg x_c need_cn          (need: CAPRI's per ha x need factor of yield x kappa_n)
                          = eff_n x_g,MINE + avail_n x_g,EXCR + avail_C x (x_g,CRES  [arable groups]
                                                                        | own residues [permanent groups])
          fertDistMine_   sum_g x_g,MINE = v_netPutQuant(n)  (purchases, >= 0, priced at CAPRI's unit value)
          fertDistExcr_   sum_g x_g,EXCR = manure applied   (ManureNPK_: excreted less losses, less net exports)
          fertDistCres_   sum_arable g x_g,CRES = arable residue pool
          e_focFertDist   (alpha_gs - 1) / x_gs - beta_gs = lambda_g e_s - mu_s,  mu_MINE = 0
                          (e_fertDistPartial written with the inverse directly: x >= 0.001 x mode, as CAPRI bounds it)
          avail_N         endogenous (endoManAvFact on): g0 + slope x (manure / land - base manure / land); the first
                          order conditions use the base factor, as CAPRI's e_focFertDist (v_nutAvailFactExcr)
        Flows in t, scaled by their prior modes; bounds 0.001-1000 x mode, duals within +-10 (set_fert_priors.gms)."""
        import casadi as ca
        lin = lambda pairs: self._lin(y, pairs)
        pv = self._pv
        self.fert = {}
        nx0 = int(X.shape[0])
        new = []
        lc = [int(j) for j in (npk.get("land_cols") or npk.get("crop_cols") or [])]
        land = ca.sum1(y[lc]) if len(lc) > 1 else (y[lc[0]] if lc else 0)
        self.fert_rows = [len(g_rows), None]
        for nut, d in npk["nutrients"].items():
            G = d["groups"]
            flows = []                                              # (group index, source, mode t, accuracy)
            for gi, g_ in enumerate(G):
                for s_, m in g_["modes"].items():
                    a_ = g_["acc"].get(s_, 1.0) if isinstance(g_["acc"], dict) else float(g_["acc"])
                    flows.append((gi, s_, max(float(m), 1e-6), float(a_)))
            nfl = len(flows)
            pools = [s_ for s_ in ("EXCR", "CRES") if any(f[1] == s_ for f in flows)]
            T = float(np.mean([f[2] for f in flows]))
            Pscale = max(sum(f[2] for f in flows if f[1] == "MINE"), 1.0)
            r_nut0 = len(g_rows)
            u = ca.SX.sym(f"u{nut}", nfl)
            lam = ca.SX.sym(f"l{nut}", len(G))
            mu = ca.SX.sym(f"m{nut}", len(pools))
            Pv = ca.SX.sym(f"P{nut}", 1)
            P = Pv[0] * pv(Pscale)
            xv = u * pv([f[2] for f in flows])                      # flows in t
            x = [xv[i] for i in range(nfl)]
            e = {"MINE": pv(float(d["eff"])), "EXCR": pv(float(d["g0"])), "CRES": pv(float(d["gc"]))}
            E = lin(d["E"]); C = lin(d["C"])
            if nut == "N" and getattr(self, "catc_n", None) is not None:
                C = C + self.catc_n                                 # catch crops' BioFix N (fertDistCres_)
            if nut == "N" and self.amm_kept is not None:
                E = E + self.amm_kept                               # N the ammonia options keep (ManureNPK_)
            if d.get("slope"):
                availE = e["EXCR"] + pv(float(d["slope"])) * (E / land - pv(float(d["m0E"])))
            else:
                availE = e["EXCR"]
            # NUTNED_
            for gi, g_ in enumerate(G):
                sc_ = max(sum(m for (gj, s_, m, acc) in flows if gj == gi), 1.0)
                need = self._lin(y, g_["need"], scale=sc_)
                if g_["perm"] and g_["own"]:
                    need = need - self._lin(y, [(c_, float(d["gc"]) * float(v_)) for c_, v_ in g_["own"]], scale=sc_)
                sup = 0
                for i, (gj, s_, m, acc) in enumerate(flows):
                    if gj == gi:
                        f_ = availE if s_ == "EXCR" else e[s_]
                        if nut == "N" and s_ == "MINE" and self.fert_eff is not None:
                            f_ = f_ * (1 + self.fert_eff)            # fertiliser options (1 + sum v_Miti NMIN)
                        if nut == "N" and s_ == "EXCR" and self.man_eff is not None:
                            f_ = f_ * (1 + self.man_eff)             # inhibitor on manure (1 + v_Miti NMAN)
                        sup = sup + f_ * x[i]
                g_rows.append(need - sup * pv(1.0 / sc_)); lbg.append(0.0); ubg.append(0.0)
            # pools
            def pool_sum(s_):
                return sum(x[i] for i, f in enumerate(flows) if f[1] == s_)
            g_rows.append((pool_sum("MINE") - P) * pv(1.0 / Pscale)); lbg.append(0.0); ubg.append(0.0)
            for s_ in pools:
                tot = pool_sum(s_)
                rhs = E if s_ == "EXCR" else C
                sc_ = max(sum(f[2] for f in flows if f[1] == s_), 1.0)
                g_rows.append((tot - rhs) * pv(1.0 / sc_)); lbg.append(0.0); ubg.append(0.0)
            # the regulations (e_fertDistPartialRegu, e_fertDistReguMax): a beta density on a group's flow with its
            # support (0, max per ha x the group's area) - the Green Deal's mineral caps by crop group ("f2f") and the
            # residue limits ("limCres")
            regs = {}
            regs_num = {}
            for (g_, s_), (mx, b1, b2) in (d.get("regs") or {}).items():
                gi_ = next((k for k, g2 in enumerate(G) if g2["g"] == g_), None)
                if gi_ is None:
                    continue
                Y = self._lin(y, [(j, float(mx) * float(sh)) for j, sh in G[gi_]["crops"]])
                regs[(gi_, s_)] = (Y, float(b1), float(b2))
                regs_num[(gi_, s_)] = [(int(j), float(mx) * float(sh)) for j, sh in G[gi_]["crops"]]
            # first-order conditions of the inner model
            for i, (gi, s_, m, acc) in enumerate(flows):
                var_k = 1.0 / acc ** 2
                bm = (1.0 + np.sqrt(1.0 + 4.0 * var_k)) / (2.0 * var_k)      # beta x mode
                a1 = bm * bm * var_k - 1.0                                  # alpha - 1
                dual = lam[gi] * e[s_] - (mu[pools.index(s_)] if s_ in pools else 0)
                if (gi, s_) in regs:
                    Y, b1, b2 = regs[(gi, s_)]
                    term = pv(a1 + b1 - 1.0) / u[i] - pv(bm) - pv(m / T) * dual - pv(m * (b2 - 1.0)) / (Y - x[i])
                    g_rows.append((x[i] - 0.999 * Y) * pv(1.0 / m)); lbg.append(-np.inf); ubg.append(0.0)
                else:
                    term = pv(a1) / u[i] - pv(bm) - pv(m / T) * dual
                g_rows.append(term); lbg.append(0.0); ubg.append(0.0)
            # CAPRI's mineral N cap per ha of land (minfert_redu_uaa.gms, e_synNMax): purchases <= cap x land
            if d.get("synNMax") is not None:
                self.synN_row = (len(g_rows), Pscale)
                g_rows.append((P - pv(float(d["synNMax"])) * land) * pv(1.0 / Pscale)); lbg.append(-np.inf); ubg.append(0.0)
            obj = obj + pv(float(d["price"]) / 1000.0) * P
            if nut == "N" and getattr(self, "_fert_tech_pending", None) is not None:
                # the fertiliser options' cost on the N purchases (GHG_Mit_Cost_: - cost x v_netPutQuant(NITF), kt)
                obj = obj + P * pv(1.0 / 1000.0) * self._fert_tech_pending[0]
                self._fert_tech_pending = None
                self._fert_tech_P = True
            gt = self.spec.get("ghg_min") if nut == "N" else None
            if gt:
                # CAPRI's emission tax on the soil N2O of mineral N (N2OSYN, direct + volatilised x indirect), on the
                # purchases; with the nitrification inhibitor adopted, the accounts' factor on the share w of mineral N
                # under it: 1 - w + w (1 - lit) (1 + NMIN) (EnvironmentalModule.fert_side_factors)
                fac = pv(float(gt["d"]) + float(gt["v"]))
                if gt.get("nitr") and self._nitr_phi is not None:
                    phi_, nm_ = self._nitr_phi
                    l2, l3 = gt["nitr"]
                    q_ = phi_ / (1.0 + nm_)
                    w_ = q_ / (q_ + 1.0 - phi_)
                    fac = fac + w_ * (pv(float(gt["d"]) * ((1.0 - l2) * (1.0 + nm_) - 1.0))
                                      + pv(float(gt["v"]) * ((1.0 - l3) * (1.0 + nm_) - 1.0)))
                obj = obj + fac * P
                if float(gt.get("l", 0.0) or 0.0) > 0:
                    # the indirect N2O of the purchases' runoff and leaching (GWPN2OLEA_; SupplyModel._ef_mineral_lea)
                    obj = obj + pv(float(gt["l"])) * P
            # the N-surplus rows in CAPRI's terms (SURTOT_REST_ with e_SURTOTHa: v_netPutQuant(NITF) + excretion +
            # fixation + deposition + residues - removal - net manure exports): the regional row with its mineral
            # parts replaced by the purchases
            if nut == "N":
                for lab_, mp in (npk.get("n_rows") or []):
                    i_ = self.labels.index(lab_)
                    Ai = self._A[i_] - np.asarray(mp, float)
                    rs = max(float(np.max(np.abs(Ai * self.sc))), 1.0)
                    self.n_rows_g = getattr(self, "n_rows_g", {})
                    self.n_rows_g[lab_] = (len(g_rows), rs)
                    nzA = [(j, float(Ai[j])) for j in np.nonzero(Ai)[0]]
                    _cn = (getattr(self, "catc_n", None) * pv(1.0 / rs)) if getattr(self, "catc_n", None) is not None else 0
                    # the catch crops' BioFix N is an input of the gross balance (e_BIOFIX)
                    g_rows.append(self._lin(y, nzA, scale=rs) + P * pv(1.0 / rs) + _cn)
                    _add = float((npk.get("n_rows_rhs_add") or {}).get(lab_, 0.0))
                    lbg.append(-np.inf); ubg.append((float(self._b[i_]) + _add) / rs)
            vars_ = ca.vertcat(u, lam, mu, Pv)
            o = nx0 + sum(int(v.shape[0]) for v in new)
            new.append(vars_)
            db = float(npk.get("dual_bound", 10.0))
            lbx += [1e-3] * nfl + [-db * T] * (len(G) + len(pools)) + [0.0]
            ubx += [1e3] * nfl + [db * T] * (len(G) + len(pools)) + [np.inf]
            self.fert[nut] = {"rows": (r_nut0, len(g_rows)), "flows": flows, "groups": [g_["g"] for g_ in G],
                              "pools": pools, "off": o, "nfl": nfl,
                              "off_P": o + nfl + len(G) + len(pools), "Pscale": Pscale, "T": T,
                              "E": E, "C": C, "availE": availE, "price": float(d["price"]),
                              "regs": regs_num}
        self.fert_rows[1] = len(g_rows)
        self.fert_x0 = nx0
        X = ca.vertcat(X, *new)
        return X, obj

    def _abatement_block(self, spec, X, y, obj, g_rows, lbg, ubg, lbx, ubx):
        self._fert_tech_pending = None; self._fert_tech_P = None
        """CAPRI's abatement options inside the regional model (ghgAbatement on; supply_model.gms GHG_Mit_Cost_,
        TotMit_, the v_emiLoss cascade), as far as capri-mod has their data:
          ammonia options per animal and sub-activity (housing/storage MAN group, application APP group): shares
            v_Miti in [0, max], one per option, the groups' shares <= 1; cost per place stock x w x herd x
            (thresh (s - s0) + 0.5 slope (s - s0)^2); N kept from losses through CAPRI's loss cascade
            (ammonia_techs.loss) enters the manure applied (ManureNPK_)
          fertiliser options: one regional share per option (v_Miti(cropMiti, tech)), mineral N x (1 + sum share
            NMIN) in NUTNED_, cost per t of need (a share + 0.5 b share^2) x crop mineral N x area, shares <= max,
            sum <= 1 and sum NMIN share <= the region's cap
          nitrification inhibitor on manure: one regional share, manure N x (1 + share NMAN) in NUTNED_, cost per t of
            manure N treated"""
        import casadi as ca
        self.amm_kept = None; self.fert_eff = None; self.man_eff = None; self._nitr_phi = None
        self.n_rows_g = {}; self.synN_row = None
        self.abat = {}
        new = []
        nx0 = int(X.shape[0])
        # CAPRI's winter cover (catch crops) as a choice (envind/cover_crops.gms; supply_model.gms catcMiti_,
        # winterCover_, e_minCoverCrops): the share m of UAAR, cost per ha of UAAR (costParLin + pmpParLin) m
        # + 1/2 pmpParSqr m^2 (+ the calibration's linear term), the land not under winter cover as its limit, its
        # BioFix N in the arable residue pool (fertDistCres_), its share in the loss cascade's runoff (RUNSURFN_)
        self._catc_m = None; self.catc_n = None
        cs = spec.get("catc")
        if cs:
            zc = ca.SX.sym("catc", 1)
            m = zc[0]
            uaa, m0 = float(cs["uaa"]), float(cs["m0"])
            dl = float((spec.get("dabat") or {}).get(("catc",), 0.0))
            obj = obj + self._pv(uaa) * (self._pv(float(cs["k1"]) + float(cs["lin"]) + dl) * m
                                        + self._pv(0.5 * float(cs["sqr"])) * m * m)
            g_rows.append((self._lin(y, [(int(j), float(s)) for j, s in cs["row"]]) + self._pv(uaa) * m)
                          * self._pv(1.0 / uaa))
            lbg.append(-np.inf); ubg.append(float(cs["rhs"]) / uaa)
            self._catc_m = m
            # ecoSetAside_: catch crops on the eligible side at CAPRI's weight (setaEco includes CATC)
            eco = (spec.get("cap_rules") or {}).get("ecoSetAside") or {}
            if float(eco.get("catc_w", 0.0) or 0.0) > 0 and "ecoSetAside" in getattr(self, "cap_rows", {}):
                ie = self.cap_rows["ecoSetAside"]
                sce = max(float(eco.get("scale", 1.0)), 1e-6)
                g_rows[ie] = g_rows[ie] - self._pv(float(eco["catc_w"]) * uaa / sce) * m
            self.catc_n = self._pv(uaa * 1000.0 * float(cs["biofix"])) * (m - self._pv(m0))      # t N
            gt_ = spec.get("ghg_min")
            if gt_:
                # CAPRI's emission tax on the catch crops' crop-residue N2O (N2OCRO: BioFix x CATC x EF1 x 44/28, in
                # GN2O and so in the taxed GGWP; their soil carbon CO2SEQ is not in GGWP)
                obj = obj + self._pv(float(gt_["d"])) * self.catc_n
            new.append(zc)
            lbx += [float(cs.get("lb", 0.0))]; ubx += [float(cs["ub"])]
            self.abat["catc"] = {"off": nx0, "uaa": uaa, "m0": m0}
        am = spec.get("amm")
        if am and am.get("techs"):
            techs = [t for t in am["techs"] if t["act"] in self.act_idx and t["smax"] > 0]
            sig = ca.SX.sym("sig", len(techs))
            if techs:
                pv = self._pv
                th_ = [float(t["th"]) + float((spec.get("dabat") or {}).get(("amm", t["act"], t["key"], t["tech"]), 0.0))
                       for t in techs]
                d = sig - pv([float(t["s0"]) for t in techs])
                hv = y[[self.act_idx[t["act"]] for t in techs]]
                obj = obj + ca.sum1(pv([float(t["stock"]) * float(t["w"]) for t in techs]) * hv
                                    * (pv(th_) * d + pv([0.5 * float(t["slope"]) for t in techs]) * d * d))
                # CAPRI's emission tax (ghgTax) on the options' manure N2O through the loss cascade, per unit of the
                # sub-activity and share from the base shares (the activity's own coefficient is taken there)
                tg = [float(t.get("ghg", 0.0) or 0.0) * float(t["w"]) for t in techs]
                if any(tg):
                    obj = obj + ca.sum1(pv(tg) * hv * d)
            byk = {}
            for kk, t in enumerate(techs):
                byk.setdefault((t["act"], t["key"]), {})[t["tech"]] = sig[kk]
            from capri_mod.supply import ammonia_techs as _at
            kept = 0
            kept_nh3 = 0
            for (a, key), shs in byk.items():
                sub = next(s_ for s_ in am["subs"][a] if s_["key"] == key)
                sh = {tt["tech"]: shs.get(tt["tech"], tt["ini"]) for tt in sub["techs"]}
                sh0 = {tt["tech"]: tt["ini"] for tt in sub["techs"]}
                wy = self._pv(float(am["sc"][a]) * float(sub["mrel"]) * float(sub["w"])) * y[self.act_idx[a]]
                if _at.cascade_data(sub) is not None:
                    # CAPRI's full cascade (GRAZN_ ... APPLN_): the manure keeps every N loss the options avoid
                    # (manExportOrAppl_: MANN x (1 - GasRunTot)); the NH3 part for the tax's indirect N2O
                    w0_, w1_ = am.get("wc") or (0.0, 0.0)
                    if self._catc_m is not None:
                        w1_ = self._catc_m
                    # CAPRI bounds every loss at zero (set_supply_bounds.gms: v_emiLoss.lo = 0): options from different
                    # groups whose effects on one loss add up to more than 1 must not drive it negative. A row for
                    # each loss that can turn negative at the options' maximum shares and is not negative at base.
                    # The cascade is evaluated once per share set (base, current) and its parts reused
                    L0 = _at.cascade(sub, sh0, w0_)
                    L1 = _at.cascade(sub, sh, w1_)
                    smx_ = {tt_["tech"]: float(tt_["smax"]) for tt_ in techs if tt_["act"] == a and tt_["key"] == key}
                    shx = {tt["tech"]: smx_.get(tt["tech"], tt["ini"]) for tt in sub["techs"]}
                    Lx = _at.cascade(sub, shx, 1.0 if self._catc_m is not None else float(w0_))
                    for k_, v_ in Lx.items():
                        if k_[1] in ("RunTot", "GasRunTot") or float(v_) >= -1e-12 or float(L0.get(k_, 0.0)) < 0.0:
                            continue
                        g_rows.append(L1[k_]); lbg.append(0.0); ubg.append(np.inf)
                    _nh3 = lambda L_: L_[("NH3", "Graz")] + L_[("NH3", "Hous")] + L_[("NH3", "Stor")] + L_[("NH3", "Appl")]
                    kept = kept + wy * (L0[("N", "GasRunTot")] - L1[("N", "GasRunTot")])
                    kept_nh3 = kept_nh3 + wy * (_nh3(L0) - _nh3(L1))
                else:
                    d_ = _cascade_loss(sub, sh0) - _cascade_loss(sub, sh)
                    kept = kept + wy * d_
                    kept_nh3 = kept_nh3 + wy * d_
            self.amm_kept = kept
            if float(am.get("tax_nh3", 0.0) or 0.0) > 0:
                # the indirect N2O of the NH3 the options keep (the soil N2O of the mineral N it displaces follows the
                # purchases in the fertilisation block)
                obj = obj - self._pv(float(am["tax_nh3"])) * kept_nh3
            grp = {}
            for kk, t in enumerate(techs):
                grp.setdefault(t["grp"], []).append(kk)
            for _, ks in grp.items():
                g_rows.append(sum(sig[kk] for kk in ks)); lbg.append(-np.inf); ubg.append(1.0)
            o_amm = nx0 + sum(int(v.shape[0]) for v in new)
            new.append(sig)
            if am.get("fixed"):
                # CONOPT's behaviour without a policy incentive (supply_module, K63): the options
                # stay at their base shares
                lbx += [float(t["s0"]) for t in techs]; ubx += [float(t["s0"]) for t in techs]
            else:
                lbx += [0.0] * len(techs); ubx += [float(t["smax"]) for t in techs]
            self.abat["amm"] = {"techs": techs, "off": o_amm}
        ft = spec.get("fert_tech")
        if ft and ft.get("techs") and ft.get("crops"):
            T_ = ft["techs"]
            phi = ca.SX.sym("phi", len(T_))
            Eff = 0; cost = 0
            pv = self._pv
            for tt, (name, nm, a_, b_, smax) in enumerate(T_):
                if str(name).upper() == "NITR_INH":
                    self._nitr_phi = (phi[tt], float(nm))
                Eff = Eff + pv(float(nm)) * phi[tt]
                a_ = float(a_) + float((spec.get("dabat") or {}).get(("fert", name), 0.0))
                cost = cost + (pv(a_) * phi[tt] + pv(0.5 * float(b_)) * phi[tt] * phi[tt])
            # CAPRI's GHG_Mit_Cost_: the fertiliser options' cost per t of mineral N purchased (- cost x
            # v_netPutQuant(NITF)); the fertilisation block's N purchases take it (_fert_block), else the crops' base
            # mineral N (the build's end)
            self._fert_tech_pending = (cost, list(ft["crops"]))
            self.fert_eff = Eff
            g_rows.append(sum(phi[tt] for tt in range(len(T_)))); lbg.append(-np.inf); ubg.append(1.0)
            if ft.get("ecap") is not None:
                g_rows.append(Eff); lbg.append(-np.inf); ubg.append(float(ft["ecap"]))
            o = nx0 + sum(int(v.shape[0]) for v in new)
            new.append(phi)
            lbx += [0.0] * len(T_); ubx += [float(t[4]) for t in T_]
            self.abat["fert"] = {"techs": T_, "off": o}
        mni = spec.get("mni")
        if mni and float(mni.get("smax", 0.0)) > 0 and any(m_ > 0 for _, m_ in mni["w"]):
            sm = ca.SX.sym("mni", 1)
            W = self._lin(y, [(c_, float(m_) / 1000.0) for c_, m_ in mni["w"]])
            s_ = sm[0]
            S0m = float(mni["S0"]) + float((spec.get("dabat") or {}).get(("mni",), 0.0))
            obj = obj + W * (self._pv(S0m - float(mni.get("vtax", 0.0))) * s_ + self._pv(0.5 * float(mni["slope"])) * s_ * s_)
            self.man_eff = self._pv(float(mni["nman"])) * s_
            self._mni_base = sum(float(m_) * float(self.xb[int(c_)]) for c_, m_ in mni["w"]) / 1000.0
            o = nx0 + sum(int(v.shape[0]) for v in new)
            new.append(sm)
            lbx += [0.0]; ubx += [float(mni["smax"])]
            self.abat["mni"] = {"off": o}
        if new:
            X = ca.vertcat(X, *new)
        return X, obj

    def abatement_outputs(self, x):
        """Shares of the options at x: {"amm": {(act, key, tech): share}, "fert": {tech: share}, "mni": share}."""
        out = {}
        a = self.abat.get("amm")
        if a:
            out["amm"] = {(t["act"], t["key"], t["tech"]): float(x[a["off"] + k]) for k, t in enumerate(a["techs"])}
        f = self.abat.get("fert")
        if f:
            out["fert"] = {t[0]: float(x[f["off"] + k]) for k, t in enumerate(f["techs"])}
        m = self.abat.get("mni")
        if m:
            out["mni"] = float(x[m["off"]])
        c_ = self.abat.get("catc")
        if c_:
            out["catc"] = float(x[c_["off"]])
        return out

    def fert_outputs(self, x):
        """{nutrient: {"purchase": t, "flows": {(group, source): t}, "availE": manure availability}}."""
        out = {}
        for nut, fb in (self.fert or {}).items():
            o = fb["off"]
            fl = {(fb["groups"][gi], s_): float(x[o + i]) * m for i, (gi, s_, m, acc) in enumerate(fb["flows"])}
            out[nut] = {"purchase": float(x[fb["off_P"]]) * fb["Pscale"], "flows": fl,
                        "availE": float(np.asarray(ca_eval(fb["availE"], self.X, x, self.p, self.pval)).ravel()[0])}
        return out

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
        grad_fit = grad + J.T @ lam_fix if (blk_rows or land_rows) else grad
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
            Ma = np.vstack([Mk / csc, np.sqrt(CAL_RIDGE) * np.eye(nk)])
            ra = np.concatenate([rhs, np.zeros(nk)])
            sol = lsq_linear(Ma, ra, bounds=(lo[keep] * csc, hi[keep] * csc), lsmr_tol="auto", max_iter=5000)
            mult[keep] = sol.x / csc
        else:
            sol = type("S", (), {"status": 0})()
        lam = lam_fix.copy(); lam[act] = mult[:len(act)]
        nu = np.zeros(nX); nu[ib] = mult[len(act):]
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
        fa = self.abat.get("fert") if getattr(self, "abat", None) else None
        if fa:
            for k, t in enumerate(fa["techs"]):
                j = fa["off"] + k
                if xb[j] <= lbx[j] + 1e-12 and res[j] >= 0:
                    res[j] = 0.0; continue
                den = getattr(self, "_fert_tech_base", 0.0)
                if getattr(self, "_fert_tech_P", None) and self.fert and "N" in self.fert:
                    fbN = self.fert["N"]
                    den = float(xb[fbN["off_P"]]) * fbN["Pscale"] / 1000.0      # base N purchases, kt
                if den > 0:
                    dabat[("fert", t[0])] = -res[j] / den
                    res[j] = 0.0
        cc_ = self.abat.get("catc") if getattr(self, "abat", None) else None
        if cc_:
            j = cc_["off"]
            if not (xb[j] <= lbx[j] + 1e-12 and res[j] >= 0) and cc_["uaa"] > 0:
                dabat[("catc",)] = -res[j] / cc_["uaa"]
            res[j] = 0.0
        ma = self.abat.get("mni") if getattr(self, "abat", None) else None
        if ma:
            j = ma["off"]
            if not (xb[j] <= lbx[j] + 1e-12 and res[j] >= 0):
                den = getattr(self, "_mni_base", 0.0)
                if den > 0:
                    dabat[("mni",)] = -res[j] / den
            res[j] = 0.0
        rest = np.abs(res[n0 + nf:]).max() if nX > n0 + nf else 0.0
        self.cal_point = xb
        return {"ok": True, "dq": dq, "dcnst": dcnst, "dabat": dabat, "residual": float(rest), "lam": lam,
                "n_active": int(len(act)), "lsq_status": int(sol.status)}

    def fert_at(self, x):
        """The fertilisation block solved nutrient by nutrient (its rows, its variables) at the values of x for every
        other variable: (x with the block's variables replaced, {nutrient: IPOPT status} of the blocks not solved)."""
        import casadi as ca
        x = np.asarray(x, float).copy()
        failed = {}
        for nut, fb in (self.fert or {}).items():
            r0, r1 = fb["rows"]
            o, o1 = fb["off"], fb["off_P"] + 1
            xf = ca.SX.sym("xf", o1 - o)
            Xs = ca.vertcat(ca.DM(x[:o]), xf, ca.DM(x[o1:]))
            gf = ca.Function("gf", [self.X, self.p], [self.g[r0:r1]])(Xs, ca.DM(self.pval))
            S = ca.nlpsol("C", "ipopt", {"x": xf, "f": 0, "g": gf},
                          {"ipopt.print_level": 0, "print_time": 0, "ipopt.tol": 1e-10, "ipopt.max_iter": 3000,
                           **linear_solver_options()})
            r = S(x0=x[o:o1], lbx=self.lbx[o:o1], ubx=self.ubx[o:o1], lbg=self.lbg[r0:r1], ubg=self.ubg[r0:r1])
            if not S.stats()["success"]:
                failed[nut] = S.stats()["return_status"]
                continue
            x[o:o1] = np.asarray(r["x"]).ravel()
        return x, failed

    # ---------------- starting points ----------------
    def start(self, y_cols, per_head=None):
        """x from column values y (unscaled) and per-head feed {(act, feed): kg/head} (default: the base ration)."""
        y_cols = np.asarray(y_cols, float)[:self.n0]
        x = np.zeros(int(self.X.shape[0]))
        x[:self.n0] = y_cols / self.sc
        for k, (a, f, r, j, s) in enumerate(self.feeds):
            v = (per_head or {}).get((a, f))
            x[self.n0 + k] = (float(v) if v is not None else float(r.x0[j])) / s
        am = self.abat.get("amm") if getattr(self, "abat", None) else None
        if am:
            for k, t in enumerate(am["techs"]):
                x[am["off"] + k] = float(t["s0"])                # the options at their base shares
        cc_ = self.abat.get("catc") if getattr(self, "abat", None) else None
        if cc_:
            x[cc_["off"]] = cc_["m0"]                             # winter cover at its base share
        if self.fert:
            for nut, fb in self.fert.items():
                o = fb["off"]
                x[o:o + fb["nfl"]] = 1.0                       # flows at their prior modes
                x[fb["off_P"]] = sum(m for (gi, s_, m, acc) in fb["flows"] if s_ == "MINE") / fb["Pscale"]
            x = self.inside_regulations(np.clip(x, self.lbx, self.ubx))
        return np.clip(x, self.lbx, self.ubx)

    def inside_regulations(self, x, margin=0.95, only_outside=False):
        """x with every regulated flow (CAPRI's beta-density regulations) moved inside its support: at most margin x
        its maximum at x's own column levels. A start outside the support (the prior mode above a Green Deal cap)
        leaves IPOPT on the wrong side of the density's pole. With only_outside, a flow is moved (to margin x its
        maximum) only where it lies outside the support; the warm start from the last solution (K79): a solution's
        flows near their maximum stay where they are, so the point fits the last solution's multipliers."""
        x = np.asarray(x, float).copy()
        y = x[:self.n0] * self.sc
        for nut, fb in (self.fert or {}).items():
            for i, (gi, s_, m, acc) in enumerate(fb["flows"]):
                cols = (fb.get("regs") or {}).get((gi, s_))
                if not cols:
                    continue
                Y = sum(v * y[j] for j, v in cols)
                k = fb["off"] + i
                if Y > 0 and x[k] * m > (Y if only_outside else margin * Y):
                    x[k] = max(margin * Y / m, self.lbx[k])
        return np.clip(x, self.lbx, self.ubx)

    def base_start(self):
        return self.start(self.xb)

    def violation(self, x):
        g = np.asarray(self.f_g(x)).ravel()
        v = np.maximum(np.maximum(g - self.ubg, self.lbg - g), 0.0)
        xv = np.maximum(self.lbx - x, 0.0) + np.maximum(x - self.ubx, 0.0)
        return float(max(v.max(initial=0.0), xv.max(initial=0.0))), int(np.argmax(v)) if v.size else -1

    # ---------------- solve ----------------
    def graph_key(self):
        """The serialised graph's hash: equal for two builds with the same structure."""
        import casadi as ca
        if getattr(self, "_skey", None) is None:
            s = ca.Function("s", [self.X, self.p], [self.obj, self.g]).serialize()
            self._skey = hashlib.sha1(s.encode()).hexdigest()
        return self._skey

    def structure_key(self, opts):
        """The key of this problem's solver in the cache: the serialised graph (data values are parameters, so equal
        graphs are equal problems up to the parameter values and the bounds) with the solver options."""
        return (self.graph_key(), tuple(sorted(opts.items())))

    def _derivatives(self):
        """The objective's gradient and the Lagrangian's Hessian for IPOPT, with the PMP quadratic 0.5 y'Qy written
        directly (gradient Q y, Hessian Q, in the scaled columns z: diag(sc) Q diag(sc)) and the rest by CasADi's
        automatic differentiation. The same functions CasADi would generate; built this way they cost a third of the
        time (the dense quadratic otherwise dominates the colouring of the Hessian)."""
        import casadi as ca
        X, P, n0 = self.X, self.p, self.n0
        nX = int(X.shape[0])
        lf = ca.SX.sym("lam_f")
        lg = ca.SX.sym("lam_g", int(self.g.shape[0]))
        Qy = ca.mtimes(self._Qsx, self._y)
        gq = ca.vertcat(self._scp * Qy, ca.SX(nX - n0, 1))
        grad = ca.gradient(self._obj_rest, X) + gq
        grad_f = ca.Function("nlp_grad_f", [X, P], [self.obj, grad], ["x", "p"], ["f", "grad_f_x"])
        H = ca.hessian(lf * self._obj_rest + ca.dot(lg, self.g), X)[0]
        D = ca.diag(self._scp)
        Qz = ca.mtimes([D, self._Qsx, D])
        H = H + lf * ca.diagcat(Qz, ca.SX(nX - n0, nX - n0))
        hess = ca.Function("nlp_hess_l", [X, P, lf, lg], [ca.triu(H)], ["x", "p", "lam_f", "lam_g"],
                           ["triu_hess_gamma_x_x"])
        return {"grad_f": grad_f, "hess_lag": hess}

    def _get_solver(self, opts):
        import casadi as ca
        key = self.structure_key(opts)
        S = _SOLVERS.get(key)
        if S is None:
            CACHE_STATS["miss"] += 1
            o = dict(opts)
            o.update(self._derivatives())
            S = ca.nlpsol("S", "ipopt", {"x": self.X, "p": self.p, "f": self.obj, "g": self.g}, o)
            _SOLVERS[key] = S
            while len(_SOLVERS) > _cache_max():
                _SOLVERS.popitem(last=False)
        else:
            CACHE_STATS["hit"] += 1
            _SOLVERS.move_to_end(key)
        return S

    def solve(self, x0, max_iter=None, tol=1e-8, print_level=0, lam=None):
        """IPOPT from x0; with lam = (lam_x, lam_g) of a previous solve of the same structure, IPOPT's warm start from
        that primal-dual point (CAPRI's CONOPT also restarts from the last solution, its basis included)."""
        import time as _t
        from capri_mod.settings import current as _settings
        _st = _settings()
        if max_iter is None:
            max_iter = int(_st.get("supply.nlp_max_iter"))
        t0 = _t.time()
        opts = {"ipopt.print_level": print_level, "print_time": 0, "ipopt.max_iter": max_iter, "ipopt.tol": tol,
                "ipopt.acceptable_tol": float(_st.get("supply.nlp_acceptable_tol")), "ipopt.mu_strategy": "adaptive",
                "ipopt.fixed_variable_treatment": str(_st.get("supply.nlp_fixed_variable_treatment")),
                # a guard: a regional solve normally takes well under a second; one that stalls is cut and the caller's
                # next start (or fallback) follows
                "ipopt.max_cpu_time": float(_st.get("supply.nlp_max_cpu_time")), **linear_solver_options()}
        warm = lam is not None and len(lam[0]) == len(self.lbx) and len(lam[1]) == len(self.lbg)
        if warm:
            # a warm start normally takes 14-23 iterations (docs/NLP_PORT_DESIGN.md "Speed"); one from a point whose
            # active set no longer fits can take over a thousand (DEB2 1,252 in the Green Deal baseline), where the
            # cold start from the same point (the caller's next start) takes a few hundred at most
            opts["ipopt.max_iter"] = min(int(max_iter), int(_st.get("supply.nlp_warm_max_iter")))
            opts.update({"ipopt.warm_start_init_point": "yes", "ipopt.mu_init": 1e-6,
                         "ipopt.warm_start_bound_push": 1e-9, "ipopt.warm_start_mult_bound_push": 1e-9,
                         "ipopt.warm_start_slack_bound_push": 1e-9})
        S = self._get_solver(opts)
        self._solver = S
        self.build_s = _t.time() - t0
        t0 = _t.time()
        kw = dict(x0=x0, p=self.pval, lbx=self.lbx, ubx=self.ubx, lbg=self.lbg, ubg=self.ubg)
        if warm:
            kw.update(lam_x0=np.asarray(lam[0], float), lam_g0=np.asarray(lam[1], float))
        if SOLVE_PROBE is not None:
            SOLVE_PROBE(problem_fingerprint(self.spec, kw, opts))
        r = S(**kw)
        st = S.stats()
        self.solve_s = _t.time() - t0
        x = np.asarray(r["x"]).ravel()
        return {"x": x, "f": float(r["f"]), "lam_g": np.asarray(r["lam_g"]).ravel(),
                "lam_x": np.asarray(r["lam_x"]).ravel(), "status": st["return_status"],
                "iterations": st.get("iter_count"), "success": bool(st.get("success")), "warm": warm}

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
            while len(_SENS) > 16:
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
            while len(_KKT) > 16:
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
