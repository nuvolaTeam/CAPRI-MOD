"""CAPRI's regional supply model in its own form, solved as a non-convex NLP with IPOPT (docs/dev/NLP_PORT_DESIGN.md).

CAPRI solves m_capModQ (supply/supply_model.gms) with CONOPT; this module writes the same equations block by block and
solves them with IPOPT (CasADi). What capri-mod already builds as data and calibration is taken over as it is: the
regional QP as assembled by RegionalSupplyModel (activity and auxiliary columns, PMP matrix Q and linear terms c,
land-market columns, land and bound rows, with one label per row) and the calibrated rations. What is CAPRI's here:

* feeding (block "feeding"; equations/supply_model/feeding.py REQSE_, FEDUSE_; objective.py QUADRF_):
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
Conservation and no tillage, the urea substitution and the legume share in temporary grassland are the regional
model's columns since 21 November 2026 (_abatement_block), and CAPRI's limit of the ration's fat with linseed
(SupplementPerc_, its slack's penalty in GHG_Mit_Cost_) its rows the same day (_supplement_fat_block). Not built: buffer
strips, biodiversity options and biochar (KNOWN_ISSUES K93).

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

from capri_mod.settings import current as _settings   # the numerical settings

from capri_mod.supply.regional_nlp.solver_options import (  # noqa: E402,F401  the parts (moved as they were)
    _SOLVERS, _SENS, _BLOCKS, CACHE_STATS, _KKT, _feed_hash,
    problem_fingerprint, linear_solver_options, _cache_max)
from capri_mod.supply.regional_nlp.feed_terms import (  # noqa: E402,F401  the parts (moved as they were)
    _cascade_loss, _AtP, ca_eval, _feed_scale, foc_fb_mode, calibrate_feed_terms)
from capri_mod.supply.regional_nlp.problem import (  # noqa: E402,F401  the parts (moved as they were)
    ProblemBlock)
from capri_mod.supply.regional_nlp.fertilisation import (  # noqa: E402,F401  the parts (moved as they were)
    NLPFertilisationBlock)
from capri_mod.supply.regional_nlp.abatement import (  # noqa: E402,F401  the parts (moved as they were)
    NLPAbatementBlock)
from capri_mod.supply.regional_nlp.calibration import (  # noqa: E402,F401  the parts (moved as they were)
    CalibrationBlock)
from capri_mod.supply.regional_nlp.response import (  # noqa: E402,F401  the parts (moved as they were)
    ResponseBlock)


# the ridge weight of the calibration's multiplier fit (CapriRegionalNLP.calibrate): the setting supply.nlp_cal_ridge

#: the market supply Hessian from the KKT conditions (market.hessian_method = "kkt"; beyond CAPRI, which re-solves its
#: supply models at 1% price shocks): None, "record" (the base solve: each successful solve's primal-dual point is kept
#: on the regional model, per graph) or "apply" (a shock: a solve of a recorded graph is replaced by the first-order
#: step of the KKT conditions from the recorded point, CapriRegionalNLP.kkt_step). Set by model._market_supply_hessian
#: before the supply module's run; the forked workers inherit it
KKT_MODE = None

#: called as SOLVE_PROBE(fingerprint) before each IPOPT solve when set (the market supply Hessian's skip of regions a
#: price shock does not reach: SupplyModule._solve_region, model._market_supply_hessian); None otherwise
SOLVE_PROBE = None


class CapriRegionalNLP(ProblemBlock, NLPFertilisationBlock, NLPAbatementBlock, CalibrationBlock,
                       ResponseBlock):
    """One region's supply model in CAPRI's form.

    spec: Q, c, A, b (the regional QP, A y <= b), labels (one per row of A), acts (activity names: the first len(acts)
    columns), rations {act: Ration}, fodder {feed: row of A}, x_base (base point of all columns, for scaling and the
    base-exactness check), prices {act: feed price vector aligned with the ration's feeds} or None, req_extra
    {act: [(col, {"E": d, "P": d, ...})]} or None (requirement change per unit of a split column), feed_ghg
    {(act, feed): EUR per t of feed} or None.
    """

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
        tl_ = self.abat.get("till") if getattr(self, "abat", None) else None
        if tl_:
            for k, t in enumerate(tl_["techs"]):
                x[tl_["off"] + k] = float(t["m0"])                # the tillage options at their initial shares
        for a, d in (getattr(self, "supp_fat", None) or {}).items():
            # the fat percentage and its slack where SupplementPerc_ holds at the start's ration and linseed
            F = self.supplement_fat_share(x, a)
            x[d["off"]] = min(max(F, 0.0), 0.05)
            x[d["off"] + 1] = max(F - 0.05, 0.0)
        if self.fert:
            for nut, fb in self.fert.items():
                o = fb["off"]
                x[o:o + fb["nfl"]] = 1.0                       # flows at their prior modes
                x[fb["off_P"]] = sum(m for (gi, s_, m, acc) in fb["flows"] if s_ == "MINE") / fb["Pscale"]
            x = self.inside_regulations(np.clip(x, self.lbx, self.ubx))
        return np.clip(x, self.lbx, self.ubx)

    def inside_regulations(self, x, margin=None, only_outside=False):
        """x with every regulated flow (CAPRI's beta-density regulations) moved inside its support: at most margin x
        its maximum at x's own column levels. A start outside the support (the prior mode above a Green Deal cap)
        leaves IPOPT on the wrong side of the density's pole. With only_outside, a flow is moved (to margin x its
        maximum) only where it lies outside the support; the warm start from the last solution (K79): a solution's
        flows near their maximum stay where they are, so the point fits the last solution's multipliers. margin: the
        setting supply.nlp_start_regulation_margin unless given."""
        if margin is None:
            margin = float(_settings().get("supply.nlp_start_regulation_margin"))
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

    def solve(self, x0, max_iter=None, tol=None, print_level=None, lam=None):
        """IPOPT from x0; with lam = (lam_x, lam_g) of a previous solve of the same structure, IPOPT's warm start from
        that primal-dual point (CAPRI's CONOPT also restarts from the last solution, its basis included). tol is
        required: until 5 November 2026 a default of 1e-8 served the retries with relaxed fertiliser caps, now the
        setting supply.nlp_relax_try_tol."""
        import time as _t
        from capri_mod.settings import current as _settings
        _st = _settings()
        if max_iter is None:
            max_iter = int(_st.get("supply.nlp_max_iter"))
        if tol is None:
            raise ValueError("CapriRegionalNLP.solve needs its tolerance (outer_loop.nlp_tol_final or "
                             "supply.nlp_relax_try_tol): no default")
        if print_level is None:
            print_level = int(_st.get("diagnostics.ipopt_print_level"))
        t0 = _t.time()
        opts = {"ipopt.print_level": print_level, "print_time": 0, "ipopt.max_iter": max_iter, "ipopt.tol": tol,
                "ipopt.acceptable_tol": float(_st.get("supply.nlp_acceptable_tol")), "ipopt.mu_strategy": str(_st.get("supply.nlp_mu_strategy")),
                "ipopt.honor_original_bounds": str(_st.get("supply.nlp_honor_original_bounds")),
                "ipopt.constr_viol_tol": float(_st.get("supply.nlp_constr_viol_tol")),
                "ipopt.acceptable_iter": int(_st.get("supply.nlp_acceptable_iter")),
                "ipopt.bound_relax_factor": float(_st.get("supply.nlp_bound_relax_factor")),
                "ipopt.nlp_scaling_method": str(_st.get("supply.nlp_scaling_method")),
                "ipopt.nlp_scaling_max_gradient": float(_st.get("supply.nlp_scaling_max_gradient")),
                "ipopt.fixed_variable_treatment": str(_st.get("supply.nlp_fixed_variable_treatment")),
                # a guard: a regional solve normally takes well under a second; one that stalls is cut and the caller's
                # next start (or fallback) follows
                "ipopt.max_cpu_time": float(_st.get("supply.nlp_max_cpu_time")), **linear_solver_options()}
        warm = lam is not None and len(lam[0]) == len(self.lbx) and len(lam[1]) == len(self.lbg)
        if warm:
            # a warm start normally takes 14-23 iterations (docs/dev/NLP_PORT_DESIGN.md "Speed"); one from a point whose
            # active set no longer fits can take over a thousand (DEB2 1,252 in the Green Deal baseline), where the
            # cold start from the same point (the caller's next start) takes a few hundred at most
            opts["ipopt.max_iter"] = min(int(max_iter), int(_st.get("supply.nlp_warm_max_iter")))
            opts.update({"ipopt.warm_start_init_point": "yes",
                         "ipopt.mu_init": float(_st.get("supply.nlp_warm_start_mu_init")),
                         "ipopt.warm_start_bound_push": float(_st.get("supply.nlp_warm_start_bound_push")),
                         "ipopt.warm_start_mult_bound_push": float(_st.get("supply.nlp_warm_start_mult_bound_push")),
                         "ipopt.warm_start_slack_bound_push": float(_st.get("supply.nlp_warm_start_slack_bound_push"))})
        from capri_mod import runlog as _runlog
        _log_file, _log_at = None, 0
        if _runlog.current().at("solver"):
            # run.verbosity "solver": IPOPT's own log of this solve (as GAMS's log shows the solver's). IPOPT opens its
            # output file once per solver object and appends each solve's log, so each cached solver of this process
            # (the regions solve in parallel processes) has its own file, read from where this solve starts
            import hashlib as _hl
            import os as _os
            import tempfile as _tf
            _h = _hl.sha1(repr(self.structure_key(opts)).encode()).hexdigest()[:16]
            _log_file = _os.path.join(_tf.gettempdir(), f"capri_mod_ipopt_{_os.getpid()}_{_h}.log")
            opts = dict(opts, **{"ipopt.output_file": _log_file,
                                 "ipopt.file_print_level": int(_st.get("run.solver_log_print_level"))})
        S = self._get_solver(opts)
        if _log_file is not None:
            _log_at = _runlog.solver_log_size(_log_file)
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
        out = {"x": x, "f": float(r["f"]), "lam_g": np.asarray(r["lam_g"]).ravel(),
               "lam_x": np.asarray(r["lam_x"]).ravel(), "status": st["return_status"],
               "iterations": st.get("iter_count"), "success": bool(st.get("success")), "warm": warm}
        if _log_file is not None:
            out["log"] = {"log": _runlog.read_solver_log(_log_file, _log_at), "n_x": int(len(self.lbx)), "n_g": int(len(self.lbg)), "seconds": self.solve_s,
                          "status": st["return_status"], "iterations": int(st.get("iter_count") or 0),
                          "start": "warm" if warm else "cold",
                          "linear_solver": str(opts["ipopt.linear_solver"] if "ipopt.linear_solver" in opts
                                               else "mumps")}
        return out
