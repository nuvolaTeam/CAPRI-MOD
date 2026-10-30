"""The regional model's solve in CAPRI's form (capri_regional_nlp.CapriRegionalNLP with IPOPT): the build, the starts, the warm and jump checks, the mineral-cap exemptions, the last-point fallback.

RegionalSupplyModel's methods, moved unchanged from capri_mod/supply/supply_module.py (refactor stage 3a,
docs/design/ARCHITECTURE_REFACTOR.md); the module-level names they use are supply_module's, given to
this module once supply_module is loaded (capri_mod.utils.mixins.inject_names); the annotations are not evaluated
(they name supply_module's types).
"""
from __future__ import annotations


class NLPBlock:
    def _aug_col_labels(self, n_cols):
        """One label per column of the regional problem: activities, land types, the mineral-N allocation column,
        manure exports and imports, the split and option columns, histosol fallow."""
        lab = list(self.acts)
        n = len(lab)
        extra = {}
        lt = list(getattr(self, "_land_types_used", None) or [])
        if lt and n + len(lt) <= n_cols and getattr(self, "_last_aug_cols", None) != "plain":
            for k_, t in enumerate(lt):
                extra[n + k_] = "land_" + t
            if getattr(self, "_alloc_cols", 0):
                extra[n + len(lt)] = "alloc_mineral_N"
        pc = getattr(self, "_pool_cols", None) or []
        if len(pc) == 2:
            extra[int(pc[0])] = "manure_export"; extra[int(pc[1])] = "manure_import"
        if getattr(self, "_grass_col", None) is not None:
            extra[int(self._grass_col)] = "grass_z"
        if getattr(self, "_dairy_col", None) is not None:
            extra[int(self._dairy_col)] = "dairy_z"
        for a_, j_ in (getattr(self, "_cattle_cols", None) or {}).items():
            extra[int(j_)] = f"cattle_z_{a_}"
        for (a_, o_), j_ in (getattr(self, "_genet_cols", None) or {}).items():
            extra[int(j_)] = f"genet_z_{a_}_{o_}"
        for c_, j_ in (getattr(self, "_hist_cols", None) or {}).items():
            extra[int(j_)] = f"hist_{c_}"
        out = lab + [extra.get(j, f"col{j}") for j in range(n, n_cols)]
        return out

    @staticmethod
    def _nlp_mine_fingerprint(npk):
        """The mineral-N caps of the fertilisation block (MINE regulations) as a hashable key; None without any."""
        if npk is None:
            return None
        items = sorted((nut, repr(k_), round(float(v_[0]), 9)) for nut, d_ in npk["nutrients"].items()
                       for k_, v_ in (d_.get("regs") or {}).items() if k_[1] == "MINE")
        return hash(tuple(items)) if items else None

    def _nlp_relax_spec(self, spec, kind, groups=None, wide=True):
        """The spec with a relaxation of the mineral caps. "duals": the inner model's duals widened to +-1000 (REGISTERED,
        CAPRI's own workaround is a slack). "caps": the crop groups in `groups` exempted as CAPRI exempts groups in
        minfert_redu_by_crop.gms (p_checkSmallMine: the group's cap at factor x its baseline mineral N per ha, "no
        backsliding"; factor fertiliser.exempt_cap_factor, CAPRI's 1.0 for its small groups), with the duals widened
        when `wide`. groups None: every capped group."""
        import copy as _cp
        sp_ = dict(spec, npk=_cp.deepcopy(spec["npk"]))
        if kind == "duals" or wide:
            sp_["npk"]["dual_bound"] = float(_settings().get("fertiliser.npk_dual_bound_wide"))
        if kind == "caps":
            base_ = (getattr(self, "_nlp_base_alloc", None) or {}).get("per_ha") or {}
            f_ = float(_settings().get("fertiliser.exempt_cap_factor"))
            rg_ = sp_["npk"]["nutrients"]["N"].get("regs") or {}
            for k_ in list(rg_):
                if k_[1] == "MINE" and (groups is None or k_[0] in groups):
                    rg_[k_] = (max(float(rg_[k_][0]), f_ * float(base_.get(k_, 0.0))),) + tuple(rg_[k_][1:])
        return sp_

    @staticmethod
    def _nlp_cap_shortfall(spec, x):
        """The mineral-capped crop groups ordered by how far their N need is out of reach at the levels x (t N):
        need - own residues - (mineral efficiency x cap + manure availability x the manure flow's upper bound + residue
        availability x the residue flow's upper bound), the flows' bounds 1000 x their prior modes as CAPRI's
        (supply/prep_sim.gms). A positive value: the group cannot meet its need under its cap whatever the rest of the
        region does. Returns [(group, shortfall)], largest first."""
        d = ((spec.get("npk") or {}).get("nutrients") or {}).get("N")
        if d is None:
            return []
        x = np.asarray(x, float)
        lin = lambda pairs: float(sum(float(v) * x[int(j)] for j, v in pairs if int(j) < len(x)))
        regs = d.get("regs") or {}
        out = []
        for g_ in d["groups"]:
            k_ = (g_["g"], "MINE")
            if k_ not in regs:
                continue
            need = lin(g_["need"])
            if g_.get("perm") and g_.get("own"):
                need -= float(d["gc"]) * lin(g_["own"])
            area = lin(g_["crops"])
            sup = float(d["eff"]) * float(regs[k_][0]) * area
            m_ = g_.get("modes") or {}
            sup += float(d["g0"]) * 1000.0 * float(m_.get("EXCR", 0.0))
            sup += float(d["gc"]) * 1000.0 * float(m_.get("CRES", 0.0))
            out.append((g_["g"], need - sup))
        return sorted(out, key=lambda t: -t[1])

    def _capri_nlp_solve(self, Q, c, A, b, x_start):
        """The regional problem in CAPRI's form (capri_regional_nlp.CapriRegionalNLP), solved with IPOPT from the
        region's previous solution (CAPRI's CONOPT starts from the last solution; then without the duals, then cold from
        the caller's start). Returns the columns' solution, or None on failure (the caller's relaxations follow; on its
        last attempt, _nlp_accept_last, IPOPT's last point is returned and recorded in _nlp_fallback_log, the run's
        metadata["nlp_fallback"])."""
        self._n_solves = int(getattr(self, "_n_solves", 0) or 0) + 1
        self.__dict__.pop("_nlp_n_target_cause", None)
        self._wc_solved = None; self._cover_solved = None
        self._yani_dnet = None
        from capri_mod.supply.capri_regional_nlp import CapriRegionalNLP
        rats = getattr(self, "feed_rations", None) or {}
        self._fd_model = None
        lab_row = list(getattr(self, "_row_labels", []) or [])
        labels = list(getattr(self, "_aug_labels", None) or [])
        if len(labels) != A.shape[0]:
            labels = lab_row if len(lab_row) == A.shape[0] else None
        if labels is None:
            raise RuntimeError(f"{self.data.region_id}: no row labels for the {A.shape[0]} rows of the regional problem")
        fod = {l.replace("fodder_", ""): k for k, l in enumerate(labels)
               if l.startswith("fodder_")}
        n = len(self.acts)
        xb = np.maximum(np.asarray(x_start, float), 0.0).copy()
        xb[:n] = np.maximum(self._base_levels().reindex(list(self.acts)).fillna(0.0).values, 0.0)
        _rx = getattr(self, "_dairy_req_extra", None)
        _rx = _rx if (_rx and max(c_ for a_ in _rx for c_, _ in _rx[a_]) < Q.shape[0]) else None
        c = np.asarray(c, float).copy()
        npk = self._npk_spec(Q.shape[0], x_start, A, labels)
        drop = []
        if npk is not None:
            # CAPRI's fertilisation replaces the regional crop-need row (an approximation of NUTNED_) and
            # the fertiliser cost per ha: mineral N, P and K are bought at CAPRI's unit value (v_netPutQuant(FNUT))
            drop = ["crop_need"]
            oc_ = getattr(self, "_organic_conv", None) or {}
            for j, a in enumerate(self.acts):
                if a in CROPS:
                    # (on converted land the organic I/O change already took the fertiliser cost out: only the
                    # conventional share's is left in c)
                    c[j] -= float(self._input_cost(a, "fert", self.FERT_COST_SHARE)) * float(oc_.get(a, 1.0))
        abat = self._nlp_abatement_spec(labels) if npk is not None else {}
        if npk is not None:
            # capri-mod's manure-application limit and mineral-N allocation row are not CAPRI's
            drop += ["alloc_mineral_N"]
        tax_ = float(getattr(self, "ghg_tax", 0.0) or 0.0)
        ghg_min = None
        if tax_ > 0 and npk is not None:
            ghg_min, c = self._nlp_tax_terms(tax_, c, abat)
        spec = dict(Q=Q, c=c, A=A, b=b, labels=labels, acts=list(self.acts), rations=rats, fodder=fod, x_base=xb,
                    prices=getattr(self, "feed_prices", None), req_extra=_rx, feed_ghg=self._ghg_feed_cost(),
                    npk=npk, drop_labels=drop, cap_rules=self._cap_rules_spec(), ghg_min=ghg_min,
                    land_rent_rows=dict(getattr(self, "_land_rent_rows", None) or {}), **abat)
        if npk is not None and getattr(self, "_alloc_cols", 0):
            spec["fix_cols"] = {n + len(getattr(self, "_land_types_used", [])): 0.0}
        self._last_feed_dm = None
        self._last_feed_t = None
        self._nlp_ok = False
        # CAPRI's calibration: the base is a first-order point of the model it is simulated with. Once per region, at
        # the first solve (the baseline's base point and prices); the linear terms are kept by column and feed
        cols = self._aug_col_labels(Q.shape[0])
        cal = getattr(self, "_nlp_cal", None)
        _late = ("grass_z", "dairy_z", "cattle_z_", "genet_z_", "hist_")
        if cal is not None and cal.get("cols") is not None and \
                any(l_.startswith(_late) for l_ in set(cols) - set(cal["cols"])):
            if os.environ.get("CAPRI_TRACE_RECAL"):
                print("RECAL", self.data.region_id, sorted(set(cols) - set(cal["cols"]))[:6], flush=True)
            # the split and histosol columns enter after the region's first solve (their linear terms come from that
            # solve's duals, at the baseline's prices): calibrate again, so that the base is a first-order point
            # of the problem with them
            cal = None
        try:
            # the scenario's policy rows are not part of the base the model is calibrated at (CAPRI calibrates in its
            # baseline)
            pol_rows = [l_ for l_ in ("N_balance", "mineral_N", "landscape_floor", "winter_cover") if l_ in labels]
            spec_sim = spec
            spec = dict(spec_sim, drop_labels=list(drop) + pol_rows)
            _fp = None
            if self.__dict__.pop("_nlp_cal_check", False) or cal is None:
                _fp = _spec_fingerprint(spec, yb_n=np.asarray(x_start, float), xb=xb[:n])
                if cal is not None and cal.get("fp") != _fp:
                    cal = None              # made on another calibration problem (a baseline checks it, see run)
            if cal is None:
                nlp0 = CapriRegionalNLP(spec)
                yb = np.asarray(x_start, float).copy()
                yb[:n] = xb[:n]
                out = nlp0.calibrate(yb)
                if not out.get("ok") and out.get("fert_failed") and npk is not None:
                    # CAPRI's priors (its 2030 posterior per ha) admit no allocation at this model's base: CAPRI's
                    # fertiliser calibration at this base instead (blanket priors, posterior at the base's own levels),
                    # as CAPRI recalibrates whenever its baseline changes
                    if self._npk_recalibrate_priors(spec, out["fert_failed"], yb):
                        npk = self._npk_spec(Q.shape[0], x_start, A, labels)
                        spec["npk"] = npk
                        nlp0 = CapriRegionalNLP(spec)
                        out = nlp0.calibrate(yb)
                if not out.get("ok") and out.get("fert_failed") and npk is not None:
                    # CAPRI bounds the inner model's duals at +-10 to help its solver (set_fert_priors.gms: "limit the
                    # dual values to reasonable range"); groups with tiny areas can need more at the model's base
                    # (CAPRI's own workaround there is a slack on the partial derivative, v_fertDistPartialSlack).
                    # Widened for this region (REGISTERED, recorded as npk_dual_bound)
                    self._npk_dual_bound = float(_settings().get("fertiliser.npk_dual_bound_wide"))
                    npk = self._npk_spec(Q.shape[0], x_start, A, labels)
                    spec["npk"] = npk
                    nlp0 = CapriRegionalNLP(spec)
                    out = nlp0.calibrate(yb)
                if out.get("ok"):
                    cal = {"dq": {cols[j]: float(v) for j, v in enumerate(out["dq"]) if v != 0.0},
                           "dcnst": dict(out["dcnst"]), "dabat": dict(out.get("dabat") or {}),
                           "residual": out["residual"],
                           "purchase0": {k_: v_["purchase"] for k_, v_ in nlp0.fert_outputs(nlp0.cal_point).items()},
                           "base_alloc": self._npk_base_alloc(nlp0, npk, yb),
                           "obj0": float(nlp0.f_obj(nlp0.cal_point)), "cols": list(cols)}
                else:
                    cal = {"dq": {}, "dcnst": {}, "failed": out.get("why")}
                    import warnings as _w
                    _w.warn(f"NLP calibration failed for {self.data.region_id}: {out.get('why')}", RuntimeWarning)
                cal["fp"] = _fp
                self._nlp_cal = cal
                self._nlp_base_alloc = cal.get("base_alloc")
            # the simulation's spec: the policy rows back, in CAPRI's terms where the NLP form writes them
            spec = dict(spec_sim, npk=spec.get("npk"))
            npk = spec["npk"]
            if spec.get("amm") and not self._amm_incentive(labels):
                # K63: without a policy incentive on N (no N-surplus row, no mineral cap, no emission tax) CAPRI's
                # options stay at their calibrated shares (CONOPT starts at the calibrated point, a first-order point
                # after costsavings0); IPOPT's interior start left that point along the options' joint direction
                spec["amm"] = dict(spec["amm"], fixed=True)
            if spec.get("catc"):
                # the Farm-to-Fork catch-crop requirement (e_minCoverCrops) as the option's lower bound; the option
                # carries the winterCover_ row itself
                _cv = getattr(self, "_cover", None)
                if _cv and float(_cv.get("uaa", 0.0) or 0.0) > 0:
                    _lb = float(_cv["req"]) / float(spec["catc"]["uaa"])
                    spec["catc"] = dict(spec["catc"], lb=_lb, ub=max(float(spec["catc"]["ub"]), _lb))
                spec["drop_labels"] = list(spec["drop_labels"]) + ["winter_cover"]
            if npk is not None:
                import copy as _cp
                npk = _cp.deepcopy(npk)
                spec["npk"] = npk
                # CAPRI's organic area target: the inner model's "f2f" and "limCres" regulations by crop group
                # (organic_minfert_redu.gms), set before the mineral fertiliser reduction, which keeps the more
                # stringent of the two (minfert_redu_by_crop.gms: min(); its limCres replaces the organic one)
                org_regs = self._npk_organic_cap(npk)
                self._nlp_mine_small = set()
                if "mineral_N" in labels:
                    # CAPRI's mineral fertiliser reduction in its own terms: the inner model's regulations by crop
                    # group (minfert_redu_by_crop.gms) or e_synNMax (minfert_redu_uaa.gms); the summed row goes
                    self._npk_mineral_cap(npk)
                    spec["drop_labels"] = list(spec["drop_labels"]) + ["mineral_N"]
                for nut_, rg in org_regs.items():
                    d_ = npk["nutrients"].get(nut_)
                    if d_ is None:
                        continue
                    d_["regs"] = self._merge_organic_regs(d_.get("regs") or {}, rg,
                                                          self._nlp_mine_small if nut_ == "N" else set())
                if "N_balance" in labels:
                    # the N-surplus target with the mineral N of the fertilisation block (CAPRI SURTOT_REST_ /
                    # e_SURTOTHa): the row's linear mineral parts out, the purchases in
                    npk["n_rows"] = [("N_balance", self._n_row_mineral_parts(A, labels))]
                    if spec.get("catc"):
                        # the requirement's catch-crop N was put on the row as a constant; the
                        # NLP form's catch-crop share carries it (catc_n), so the constant is taken back out
                        npk["n_rows_rhs_add"] = {"N_balance": float(getattr(self, "_cover_dbf_nb", 0.0) or 0.0)}
                    spec["drop_labels"] = list(spec["drop_labels"]) + ["N_balance"]
            if cal is not None:
                spec["dq"] = np.array([cal["dq"].get(l_, 0.0) for l_ in cols])
                spec["dcnst"] = cal["dcnst"]
                spec["dabat"] = cal.get("dabat") or {}
            # a relaxation once needed under these mineral caps is kept for the rest of the scenario (CAPRI's
            # exemptions are set once, before its solves, not by iteration); without this the region switched between
            # the relaxed and the strict problem from one outer iteration to the next
            _fp = self._nlp_mine_fingerprint(npk)
            _keep = getattr(self, "_nlp_relax_keep", None)
            if _fp is not None and _keep is not None and _keep[0] == _fp:
                spec0 = spec
                spec = self._nlp_relax_spec(spec, _keep[1], *(_keep[2:4] if len(_keep) > 2 else ()))
                npk = spec["npk"]
            else:
                _keep = None
                spec0 = spec
            from capri_mod.supply import capri_regional_nlp as _crn
            if _crn.SOLVE_PROBE is not None:
                # the market supply Hessian's skip test (SupplyModule._solve_region), before the build: the problem, the
                # start and the warm-start state decide this solve and those after it (IPOPT and the build are
                # deterministic), so a region whose digest is the base's is not built or solved again
                _crn.SOLVE_PROBE(_crn.problem_fingerprint(
                    spec, {"x_start": np.asarray(x_start, float), "prev": getattr(self, "_nlp_prev", None),
                           "f_prev": getattr(self, "_nlp_prev_f", None), "keep": _keep},
                    {"tol": float(getattr(type(self), "nlp_tol", 1e-8)),
                     "warm_check": float(getattr(type(self), "nlp_warm_check", 0.01)),
                     "jump_check": float(getattr(type(self), "nlp_jump_check", 0.0) or 0.0),
                     "jump_gain": float(getattr(type(self), "nlp_jump_gain", 0.0) or 0.0)}))
            nlp = CapriRegionalNLP(spec)
            if os.environ.get("CAPRI_NLP_DUMP"):
                import pickle as _pk
                _pk.dump(dict(spec=spec, x_start=np.asarray(x_start, float), cols=cols, cal=cal),
                         open(os.path.join(os.environ["CAPRI_NLP_DUMP"], f"{self.data.region_id}.pkl"), "wb"))
        except Exception as _exc:
            import warnings as _w
            if os.environ.get("CAPRI_TRACE_NLP_BUILD"):            # diagnostics: the build's traceback
                import traceback as _tb
                _tb.print_exc()
            _w.warn(f"NLP build failed for {self.data.region_id}: {_exc!r}")
            return None
        # warm start: the previous solution where the problem has the same columns, else the caller's start with the
        # base ration
        prev = getattr(self, "_nlp_prev", None)
        gk = nlp.graph_key()
        shape = (nlp.n0, tuple(k[:2] for k in nlp.feeds), len(nlp.lbx))
        starts = []
        if prev is not None and len(prev) == 4 and prev[2] == shape:
            xw = nlp.inside_regulations(np.clip(prev[1], nlp.lbx, nlp.ubx))
            if prev[0] == gk:
                # IPOPT's warm start from the last primal-dual point: the last solution as it is (as CAPRI's CONOPT
                # restarts from its last solution), its regulated flows moved only where they lie outside their
                # support. Until 29 October 2026 the warm start took the point with every flow above 0.95 of its
                # maximum pulled back (the cold start's rule) and the last solution's multipliers: an inconsistent
                # start that stopped at the iteration cap where flows sat near their maximum, and the cold restart
                # that followed could end at another local optimum (HU230000, Green Deal 2030; KNOWN_ISSUES K79)
                xl = nlp.inside_regulations(np.clip(prev[1], nlp.lbx, nlp.ubx), only_outside=True)
                starts.append(("warm", xl, prev[3]))
            starts.append(("prev", xw, None))
        starts.append(("start", nlp.start(np.asarray(x_start, float)), None))
        res = None
        kinds = []
        _tol = float(getattr(type(self), "nlp_tol", 1e-8))
        _tried = []
        _km = _crn.KKT_MODE
        _kb = self.__dict__.setdefault("_kkt_base", {}) if _km else None

        def _nsolve(nlp_, xs_, lam=None, tol=None):
            # the market supply Hessian from the KKT conditions (market.hessian_method = "kkt"): a shock's solve of a
            # graph the base solved is the first-order step from the base's solution (CapriRegionalNLP.kkt_step);
            # else IPOPT, counted (_kkt_ipopt) where the method asked for a step
            if _km == "apply":
                b_ = _kb.get(nlp_.graph_key())
                if b_ is not None and len(b_["pval"]) == len(nlp_.pval) and len(b_["x"]) == len(nlp_.lbx):
                    return nlp_.kkt_step(b_)
                self._kkt_ipopt = int(getattr(self, "_kkt_ipopt", 0) or 0) + 1
            return nlp_.solve(xs_, lam=lam, tol=tol) if tol is not None else nlp_.solve(xs_, lam=lam)
        for kind, xs, lam_ in starts:
            res = _nsolve(nlp, xs, lam=lam_, tol=_tol)
            if res["status"] == "KKT_Step":
                kind = "kkt"
            kinds.append(kind)
            _tried.append((kind, res["status"], float(res["f"]), int(res["iterations"] or 0)))
            if res["success"] or res["status"] in ("Solved_To_Acceptable_Level",):
                break
        _f_prev = getattr(self, "_nlp_prev_f", None)
        if (kinds and kinds[-1] == "warm" and _f_prev is not None
                and float(res["f"]) > _f_prev + float(getattr(type(self), "nlp_warm_check", 0.01)) * abs(_f_prev)):
            # a warm start (IPOPT from the previous primal-dual point, small barrier) can end at a worse stationary
            # point of the non-convex per-head feeding and stay there in every later iteration (Brittany, Farm-to-Fork
            # 2030: livestock at their lower bounds, objective 9% worse, "Solve_Succeeded"; KNOWN_ISSUES K75). Where
            # its objective is more than nlp_warm_check (relative) worse than the last iteration's, the region is also
            # solved from the previous point and from the standard start, and the lowest objective is kept.
            for kind, xs, lam_ in [s_ for s_ in starts if s_[0] != "warm"]:
                r_ = _nsolve(nlp, xs, lam=lam_, tol=_tol)
                _tried.append((kind, r_["status"], float(r_["f"]), int(r_["iterations"] or 0)))
                if (r_["success"] or r_["status"] in ("Solved_To_Acceptable_Level",)) and float(r_["f"]) < float(res["f"]):
                    res = r_
                    kinds.append("checked:" + kind)
        _jt = float(getattr(type(self), "nlp_jump_check", 0.0) or 0.0)
        # the jump check of this solve, None where it did not act: the largest move, the starts it solved and the one
        # kept (model metadata nlp_jump_check, the outer history's "jump_check")
        self._nlp_jump = None
        _y0 = getattr(self, "_nlp_y", None)
        if (_jt > 0 and _y0 is not None and res is not None and res.get("x") is not None
                and (res["success"] or res["status"] in ("Solved_To_Acceptable_Level",))
                and list(getattr(self, "_nlp_cols", None) or []) == list(cols)):
            # K79: a jump of the activity levels between outer iterations (a non-convex regional problem whose warm
            # start, or the cold restart after a failed warm start, ended at another local optimum): the region is
            # also solved from the starts not yet tried and the lowest objective is kept
            _y1 = np.asarray(nlp.outputs(res)[0], float).ravel()
            _y0 = np.asarray(_y0, float).ravel()
            if len(_y1) == len(_y0) and len(_y0):
                _sc = np.maximum(np.abs(_y0), 0.01 * float(np.max(np.abs(_y0))))
                _mv = float(np.max(np.abs(_y1 - _y0) / np.maximum(_sc, 1e-12)))
                if _mv > _jt:
                    _done = {k_[0] for k_ in _tried}
                    _f0, _n0 = float(res["f"]), len(_tried)
                    for kind, xs, lam_ in [s_ for s_ in starts if s_[0] not in _done and s_[0] != "warm"]:
                        r_ = _nsolve(nlp, xs, lam=lam_, tol=_tol)
                        _tried.append(("jump:" + kind, r_["status"], float(r_["f"]), int(r_["iterations"] or 0)))
                        # kept only where it gains more than nlp_jump_gain (relative): a lower objective by solver
                        # noise is the same optimum, and switching to it moved the levels for nothing (K79)
                        _gain = float(getattr(type(self), "nlp_jump_gain", 0.0) or 0.0)
                        if ((r_["success"] or r_["status"] in ("Solved_To_Acceptable_Level",))
                                and float(r_["f"]) < float(res["f"]) - _gain * max(1.0, abs(float(res["f"])))):
                            res = r_
                            kinds.append("jump:" + kind)
                    self._nlp_jump = {"move": round(_mv, 6), "f": _f0, "solved": [t_[0] for t_ in _tried[_n0:]],
                                      "kept": kinds[-1], "f_kept": float(res["f"])}
        _ok = lambda r_: r_["success"] or r_["status"] in ("Solved_To_Acceptable_Level",)
        _lab = lambda k_: ((k_[1] if k_[1] == "duals" else "caps:" + "+".join(k_[2]) + (",duals" if k_[3] else ""))
                           if k_ is not None else None)
        self._nlp_relaxed = _lab(_keep)
        _order = ("duals", "caps")
        # a kept exemption that no longer suffices is extended (the next group), not dropped
        _todo = (_order[_order.index(_keep[1]) + 1:] or ("caps",)) if _keep is not None else _order

        def _try(sp_):
            try:
                nlp_ = CapriRegionalNLP(sp_)
                return nlp_, _nsolve(nlp_, nlp_.start(np.asarray(x_start, float)))
            except Exception:
                return None, None
        if (not _ok(res) and _fp is not None and _todo and getattr(self, "_nlp_try_n_relax", False)
                and _km != "apply"):
            # K89: with a tiered N target in force, which constraint makes the problem infeasible: solved once without
            # the N-surplus row (CAPRI SURTOT_REST_ / e_SURTOTHa). Feasible without it: the target is the cause, not the
            # mineral caps, so no cap is exempted here and the caller tries JRC121368's relaxed target (where the caps
            # still bind there, its own solve searches the exemptions). Before, the exemption search ran first: in
            # NL320000 (Farm-to-Fork) 30 cold solves, all failing, before the relaxed target solved
            _np0 = spec0.get("npk") or {}
            if _np0.get("n_rows"):
                _, res_n = _try(dict(spec0, npk=dict(_np0, n_rows=[], n_rows_rhs_add={})))
                if res_n is not None and _ok(res_n):
                    _todo = ()
                    self._nlp_n_target_cause = True
        if not _ok(res) and _fp is not None and _todo:
            # the Green Deal's mineral caps (organic target, mineRedu) as CAPRI's regulations can leave a crop group's
            # need out of reach (e.g. a permanent-crop group with a high organic target, its mineral N cut by the
            # converted share, and a manure prior near zero). CAPRI's runs hit this and exempt the groups concerned by
            # region and group (minfert_redu_by_crop.gms, p_checkSmallMine: cap at 1.0-1.2 x baseline). REGISTERED:
            # first the duals widened to +-1000; then the groups exempted one at a time, those whose need is out of
            # reach first (_nlp_cap_shortfall), at fertiliser.exempt_cap_factor x baseline, with CAPRI's duals and
            # then the widened ones; recorded as nlp_relaxed ("caps:GROUP+...")
            for kind_ in _todo:
                found = None
                if kind_ == "duals":
                    sp_ = self._nlp_relax_spec(spec0, "duals")
                    nlp_, res_ = _try(sp_)
                    if res_ is not None and _ok(res_):
                        found = (nlp_, res_, sp_, (_fp, "duals"))
                else:
                    ex_ = list(_keep[2]) if (_keep is not None and _keep[1] == "caps") else []
                    cand = [g for g, _ in self._nlp_cap_shortfall(spec0, x_start) if g not in ex_]
                    n_kept = len(ex_)
                    for g in cand:
                        ex_.append(g)
                        for wide_ in (False, True):
                            sp_ = self._nlp_relax_spec(spec0, "caps", tuple(ex_), wide_)
                            nlp_, res_ = _try(sp_)
                            if res_ is not None and _ok(res_):
                                found = (nlp_, res_, sp_, (_fp, "caps", tuple(ex_), wide_))
                                break
                        if found:
                            break
                    if found:
                        # the smallest set: a group added on the way is dropped again where the rest suffices
                        wide_ = found[3][3]
                        for g in list(ex_[n_kept:-1]):
                            trial = tuple(x for x in ex_ if x != g)
                            sp_ = self._nlp_relax_spec(spec0, "caps", trial, wide_)
                            nlp_, res_ = _try(sp_)
                            if res_ is not None and _ok(res_):
                                ex_ = list(trial)
                                found = (nlp_, res_, sp_, (_fp, "caps", trial, wide_))
                if found:
                    nlp, res, sp_, k_ = found[0], found[1], found[2], found[3]
                    npk, spec = sp_["npk"], sp_         # later re-solves (amm-fixed) keep the relaxation
                    gk = nlp.graph_key()
                    shape = (nlp.n0, tuple(k[:2] for k in nlp.feeds), len(nlp.lbx))
                    self._nlp_relax_keep = k_
                    self._nlp_relaxed = _lab(k_)
                    kinds.append(self._nlp_relaxed)
                    break
        self._nlp_times = (getattr(nlp, "build_s", 0.0), getattr(nlp, "solve_s", 0.0))
        _nonopt = None
        if not _ok(res):
            import warnings as _w
            _w.warn(f"NLP solve {res['status']} for {self.data.region_id} after {res['iterations']} iterations",
                    RuntimeWarning)
            self._nlp_failed = "nlp:" + str(res["status"])
            if not getattr(self, "_nlp_accept_last", False) or res.get("x") is None:
                return None
            # the caller's last attempt: CAPRI carries on with a non-optimal solve and records it (supply/simu_supply.gms,
            # p_INFES); IPOPT's last point is kept, recorded in the run's metadata (nlp_fallback) and warned about
            _nonopt = str(res["status"])
            self._nlp_nonoptimal = _nonopt
            _w.warn(f"{self.data.region_id}: IPOPT's last point kept ({_nonopt}, non-optimal), as CAPRI keeps a "
                    f"non-optimal solve", RuntimeWarning)
        if _km == "record" and _nonopt is None:
            _kb[gk] = nlp.kkt_record(res)
        _am = spec.get("amm")
        if (_nonopt is None and _am and not _am.get("fixed")
                and "N_balance" in labels and "mineral_N" not in labels
                and not float(getattr(self, "ghg_tax", 0.0) or 0.0) > 0):
            # the N-surplus row slack (dual ~0): the options at their base shares (CONOPT stays at
            # the calibrated shares unless moving pays through the policy row)
            _zA = nlp.outputs(res)[2]
            if float(_zA[labels.index("N_balance")]) <= 1e-9:
                try:
                    spec_f = dict(spec, amm=dict(_am, fixed=True))
                    nlp_f = CapriRegionalNLP(spec_f)
                    res_f = _nsolve(nlp_f, np.clip(res["x"], nlp_f.lbx, nlp_f.ubx), tol=_tol)
                    if _ok(res_f):
                        nlp, res, spec = nlp_f, res_f, spec_f
                        gk = nlp.graph_key()
                        shape = (nlp.n0, tuple(k[:2] for k in nlp.feeds), len(nlp.lbx))
                        kinds.append("amm-fixed")
                except Exception:
                    pass
        if _km == "record" and _nonopt is None:
            _kb[gk] = nlp.kkt_record(res)
        self._nlp_prev = (gk, res["x"], shape, (res["lam_x"], res["lam_g"]))
        self._nlp_prev_f = float(res["f"])
        # the starts tried and the last one's IPOPT iterations (diagnostics of the outer loop, model.trace_outer)
        self._nlp_path = ("/".join(kinds), int(res["iterations"]))
        if os.environ.get("CAPRI_NLP_DUMP") and self.data.region_id in os.environ.get("CAPRI_NLP_TRACE", "").split(","):
            # diagnostics only: every solve of the traced regions, with the previous point, the starts tried and the
            # point kept (CAPRI_NLP_TRACE=FRH0,...; KNOWN_ISSUES K75)
            import pickle as _pk
            _fn = os.path.join(os.environ["CAPRI_NLP_DUMP"], f"{self.data.region_id}.trace.pkl")
            _rec = dict(spec=spec, prev=prev, tried=_tried, kinds=list(kinds), x=np.asarray(res["x"], float).copy(),
                        status=res["status"], f=float(res["f"]))
            with open(_fn, "ab") as _fh:
                _pk.dump(_rec, _fh)
        y, F, zA, info = nlp.outputs(res)
        self._nlp_y = np.asarray(y, float).ravel().copy()
        self._nlp_cols = list(cols)
        # the young-animal markets' price update: this solution's response to the young-animal prices (K65)
        self._yani_dnet = None
        _ye = getattr(type(self), "yani_exact_response", None)
        if _ye is None:
            _ye = bool(getattr(type(self), "use_cattle_member_splits", False))
        if _ye and getattr(self, "yani_price_ratio", None):
            try:
                self._yani_dnet = self._yani_response(nlp, res, list(cols))
            except Exception as _exc:                       # the caller falls back to the PMP terms' response
                if os.environ.get("CAPRI_TRACE_YANI"):
                    print("YANI response failed", self.data.region_id, repr(_exc), flush=True)
                self._yani_dnet = None
        self._last_npk = nlp.fert_outputs(res["x"]) if nlp.fert else None
        ab = nlp.abatement_outputs(res["x"]) if getattr(nlp, "abat", None) else {}
        self._nlp_abatement = ab
        if "catc" in ab:
            # the winter cover share chosen, for the cascade's accounts and the supply result (cover_crops)
            _c = spec["catc"]
            self._wc_solved = float(ab["catc"])
            self._cover_solved = {"req": self._wc_solved * _c["uaa"], "uaa": _c["uaa"], "base": _c["m0"] * _c["uaa"],
                                  "delta": (self._wc_solved - _c["m0"]) * _c["uaa"], "biofix": _c["biofix"],
                                  "share": self._wc_solved, "lb_share": float(_c.get("lb", 0.0)),
                                  "max_share": float(_c["ub"]), "endogenous": True,
                                  "potential": float(_c.get("potential", 0.0))}
        if self._last_npk:
            for nut, o_ in self._last_npk.items():
                gs = {g_["g"]: g_ for g_ in npk["nutrients"][nut]["groups"]}
                yv = np.asarray(nlp.f_y(res["x"])).ravel()
                o_["area"] = {g: float(sum(sh * yv[j] for j, sh in gs[g]["crops"])) for g in gs}
            if "N" in self._last_npk:
                # the allocation the regional model solved, for the accounts' report (fert_dist)
                self._fd_model = {"capri_region": npk["capri_region"], "flows": self._last_npk["N"]["flows"],
                                  "area": self._last_npk["N"]["area"], "converged": True}
        self._last_feed = F
        self._last_duals = zA
        # the columns' reduced costs at the NLP solution (IPOPT's bound multipliers, per unit of the column): the
        # manure pools read the trade columns' from here, as their duals through the A rows miss the fertilisation
        # block (manure applied reaches NUTNED_ and the purchases)
        self._nlp_rc = -np.asarray(res["lam_x"][:nlp.n0], float) / np.asarray(nlp.sc, float)
        self._nlp_ok = _nonopt is None
        if _nonopt is None:
            self._nlp_failed = None
        else:
            if getattr(self, "_nlp_fallback_log", None) is None:
                self._nlp_fallback_log = []
            self._nlp_fallback_log.append(f"nlp:{_nonopt} -> IPOPT's last point kept (non-optimal, as CAPRI)")
        self._nlp_status = str(info.get("status"))
        self._last_req_duals = info.get("req_duals") or {}
        self._manure_ni_relief, self._manure_ni_nh3, self._manure_ni_share = {}, {}, 0.0
        self._fert_inside_factor = {}
        self._fert_inside_weight = {}
        self._fert_tech_shares = {}
        if self._techs_inside():
            # the options' shares for the accounts (relief and NH3 saved per head from CAPRI's cascade)
            sh = {}
            for (a_, key_, tech_), v_ in (ab.get("amm") or {}).items():
                sh.setdefault((a_, key_), {})[tech_] = float(v_)
            self._amm_record(sh)
        if ab.get("fert"):
            self._fert_tech_shares = {k_: float(v_) for k_, v_ in ab["fert"].items()}
        if ab.get("mni") is not None and getattr(self, "_nlp_nip", None):
            _sh = float(ab["mni"]); _nip = self._nlp_nip
            if _sh > 1e-9:
                for a_, m_ in _nip["man_d"].items():
                    m_ = float(m_ or 0.0)
                    if m_ > 0 and a_ in self.acts:
                        self._manure_ni_relief[a_] = _nip["sub"] * _nip["nman"] * _sh * m_
                        if a_ in _nip["app_nh3"]:
                            self._manure_ni_nh3[a_] = _sh * _nip["app_nh3"][a_]
                self._manure_ni_share = _sh
                self._fert_tech_shares = dict(getattr(self, "_fert_tech_shares", None) or {})
                self._fert_tech_shares["NITR_INH_MAN"] = _sh
        acts_ = list(self.acts); dm = {}; ft = {}
        for a, r in rats.items():
            if a not in acts_:
                continue
            herd = float(y[acts_.index(a)])
            for j, f in enumerate(r.feeds):
                amt = F.get((a, f)) if r.flex[j] else float(r.x0[j]) * herd
                if amt is not None and amt > 0:
                    dm.setdefault(a, {})[f] = float(amt) * float(r.dm[j])
                    ft.setdefault(a, {})[f] = float(amt)
        self._last_feed_dm = dm
        self._last_feed_t = ft
        return y

    def _nlp_solve(self, Q, c, A, b, x_start):
        """Solve the regional problem in CAPRI's form (_capri_nlp_solve, IPOPT), or None. With _nlp_try_n_relax set by
        the caller, a failure is marked "n_target" (_nlp_fb_last), and the caller retries at JRC121368's relaxed N
        target; with _nlp_accept_last set (the caller's last attempt), IPOPT's last point is kept, as CAPRI carries on
        with a non-optimal solve (supply/simu_supply.gms, widen_bounds.gms; p_INFES)."""
        self._last_npk = None
        self._nlp_rc = None
        self._last_feed_dm = None                  # never carry a previous solve's feed
        self._last_feed_t = None
        self._nlp_ok = False
        self._nlp_fb_last = False
        y = self._capri_nlp_solve(Q, c, A, b, x_start)
        if y is None and getattr(self, "_nlp_try_n_relax", False):
            self._nlp_fb_last = "n_target"
        return y

    def _note_floor_failure(self):
        """Where the regional model has no solution with a landscape floor in it, say so in the run's record
        (nlp_fallback): CAPRI keeps the floor as it is (supply_model.gms e_setaLandscape; widen_bounds.gms widens
        feeding, nutrient, land-use-change and fertiliser bounds, never the floor) and carries on with the solver's last
        point. CAPRI's Green Deal runs have the land market on, which lets grassland become arable land; without it a
        floor sized on total farmland may not fit on the arable land (K84)."""
        if "landscape_floor" not in list(getattr(self, "_row_labels", []) or []):
            return
        if getattr(self, "_nlp_fallback_log", None) is None:
            self._nlp_fallback_log = []
        msg = ("no solution with the landscape floor " + ("(land market on)" if getattr(self, "use_land_market", False)
               else "(land market off: CAPRI's Green Deal runs have it on)") + "; the solver's last point kept, as CAPRI")
        if msg not in self._nlp_fallback_log:
            self._nlp_fallback_log.append(msg)

    def _nlp_last_point(self, Q, c, A, b, x_start):
        """The caller's last attempt: CAPRI's form solved again with IPOPT's last point kept where it fails, as CAPRI
        carries on with a non-optimal solve (supply/simu_supply.gms, widen_bounds.gms; p_INFES), recorded in the run's
        metadata (nlp_fallback). Only where the NLP cannot be built at all is there nothing to keep: the run stops, as
        CAPRI aborts on an execution error."""
        self._nlp_accept_last = True
        try:
            y = self._nlp_solve(Q, c, A, b, x_start)
        finally:
            self._nlp_accept_last = False
        if y is None:
            raise RuntimeError(f"{self.data.region_id}: the regional model in CAPRI's form could not be built or solved "
                               f"({getattr(self, '_nlp_failed', None) or 'NLP build failed'})")
        return y
