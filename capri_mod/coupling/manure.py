"""The manure pools between regions (CAPRI's manure trade, cleared between solves).

CAPRIModel's methods, moved unchanged from capri_mod/model.py (the refactor's split into block mixins,
docs/dev/ARCHITECTURE_REFACTOR.md); the module-level names they use are model's, given to this
module once model is loaded (capri_mod.coupling.inject); the annotations are not evaluated.
"""
from __future__ import annotations


from capri_mod import statekit as _cst   # the state objects' helpers
from capri_mod.market.equations.manuremarket.declare_manure_market import (e_mPoolBenefits, e_mPoolClear,
                                                                           e_mPoolExcessSupply, e_mPoolSurplus,
                                                                           e_mPoolSurplus_row, p_mTradeAddCost)
from capri_mod.market.equations.manuremarket.simu_manure_market import p_mPoolSupConst, p_stepWeights_average
#: the clearing's state kept per market between outer iterations, as paths in the model's state objects (the N
#: market's in the model's own sv and res; the P and K markets' copies in sv.pool_pk, swapped in for their clearing)
#: t per kt: CAPRI's pool trade is in kt, the supply in its slope in t (outer_loop.manure_pool_es_slope "capri_doc")
_T_PER_KT = 1000.0
_POOL_IMBALANCE, _POOL_WORST_KEY = "res.pool_imbalance", "res.pool_worst_key"
_POOL_STATE = ("sv.pool_state", "sv.pool_accel", _POOL_IMBALANCE, _POOL_WORST_KEY, "res.pool_solver_status",
               "res.pool_eu_unaccounted", "res.pool_losf")


class ManureBlock:
    def _update_manure_pools(self) -> None:
        """Clear CAPRI's manure markets, one per nutrient as CAPRI (manuremarket/simu_manure_market.gms: loop over
        FOUT, MANN, MANP, MANK, each solved on its own): the N market, then the P and K markets of the regions that
        have their columns. Each market keeps its own state between iterations; the convergence measure is the worst
        of the three."""
        sm = self.supply_module
        self._clear_pool("N")
        gaps = {"N": float(getattr(self.res, "pool_imbalance", 0.0) or 0.0)}
        worst_key = {"N": getattr(self.res, "pool_worst_key", "")}
        held = _cst.setdefault(self.sv, "pool_pk", {})
        for nut in ("P", "K"):
            if not any((getattr(mo.ev, "pool_cols_pk", None) or {}).get(nut) for mo in getattr(sm, "_models", {}).values()):
                continue
            st = held.setdefault(nut, {_POOL_IMBALANCE: 0.0})
            n_state = {k: _cst.get_path_or(self, k) for k in _POOL_STATE}
            for k in _POOL_STATE:
                _cst.set_path(self, k, st.get(k))
            try:
                self._clear_pool(nut)
            finally:
                for k in _POOL_STATE:
                    st[k] = _cst.get_path_or(self, k)
                for k, v in n_state.items():
                    _cst.set_path(self, k, v)
            gaps[nut] = float(st.get(_POOL_IMBALANCE) or 0.0)
            worst_key[nut] = st.get(_POOL_WORST_KEY) or ""
        self.res.pool_gaps = gaps
        w = max(gaps, key=gaps.get)
        self.res.pool_imbalance = gaps[w]
        if w != "N":
            self.res.pool_worst_key = f"{worst_key[w]}:{w}"

    def _clear_pool(self, prod: str = "N") -> None:
        """Clear one of CAPRI's manure markets (prod N, P or K) on the regions' EXACT schedules.

        Each region's solve gives threshold prices for trading, from the
        reduced costs of its trade variables at the solution:
          exports e(p) = clip((th_e - p)/s, 0, manure produced),
                   th_e = p_now + s e_now - rc_e
          imports i(p) = max(0, (p - th_i)/s),  th_i = p_now - s i_now + rc_i
        (s = CAPRI's trade-cost slope). Pool k's net export z_k(p) is their sum
        - piecewise linear WITH the kinks where regions start or stop trading
        (local slopes ignored them and the search stalled: plan vs realised
        4.0, then 2.3 x supply). The connected equilibrium is solved as the PRIMAL
        Takayama-Judge problem on these schedules (shipments between pools at CAPRI's
        trade costs c_kl, each pool's exports and imports on its schedule; a convex QP
        solved with the model's own solver). The dual price problem
        (min_p sum_k Phi_k(p_k) s.t. p_k - p_l <= c_kl) was solved with SLSQP before and
        failed on the schedules' kinks.
        """
        from scipy.optimize import nnls as _nnls
        sm = self.supply_module
        # the market's prices by country: the N market's in manure_pool_price, P and K in manure_pool_price_pk
        pools = dict((getattr(sm.seen, "manure_pool_price", None) or {}) if prod == "N"
                     else ((getattr(sm.seen, "manure_pool_price_pk", None) or {}).get(prod) or {}))
        cost = getattr(self.par, "pool_cost_cache", None)
        if cost is None:
            from capri_mod.data import inputs as _inputs, nested_tables as _nt
            # CAPRI's trade costs between the pools (tools/build/build_manure_pool_costs.py); a missing file stops the run
            cost = {}
            for k, v in _nt.read_manure_pools(_inputs.current().path("manure_pool_costs.csv", "environment"))["pairs"].items():
                a, b = k.split("|"); cost[(a, b)] = v["eur_per_t_n"] / 1000.0
            self.par.pool_cost_cache = cost
        sched, es, sup = {}, {}, {}
        form = str(_settings().get("outer_loop.manure_pool_form"))
        if form not in ("schedules", "capri"):
            raise ValueError(f'outer_loop.manure_pool_form = "{form}": "schedules" or "capri"')
        crec = []                           # the "capri" form's records per region (_clear_pool_capri)
        _st_m = _settings()                 # the multiplier recovery's tolerances and iterations (settings)
        for reg, mo in getattr(sm, "_models", {}).items():
            if prod == "N":
                pc = getattr(mo.ev, "pool_cols", []) or []
                s0 = float(getattr(mo.res, "manure_supply0", 0.0) or 0.0)
            else:
                pc = (getattr(mo.ev, "pool_cols_pk", None) or {}).get(prod) or []
                s0 = float((getattr(mo.res, "manure_supply0_pk", None) or {}).get(prod, 0.0) or 0.0)
            aug = getattr(mo.res, "last_aug", None)
            if len(pc) != 2 or aug is None or s0 <= 0:
                continue
            Q, c, A, b, y = aug
            if max(pc) >= len(y):          # stored problem predates the market columns
                continue
            # row duals: the regional NLP's own multipliers (its feed block is not in the stored
            # problem, so duals recovered from the stored problem's KKT conditions were wrong and the
            # pools stopped clearing); else recovered by NNLS from the active rows of the stored problem
            zc = getattr(mo.ev, "last_duals", None)
            if zc is not None and len(zc) == A.shape[0]:
                lam = np.maximum(np.asarray(zc, float), 0.0)
            else:
                act = [r for r in range(A.shape[0]) if A[r] @ y >= b[r] - _st_m.get("outer_loop.manure_pool_active_tol") * max(1.0, abs(float(b[r])))]
                bnd = [q for q in range(len(y)) if y[q] <= _st_m.get("outer_loop.manure_pool_bound_tol")]
                M = np.hstack([A[act].T if act else np.zeros((len(y), 0)), -np.eye(len(y))[:, bnd]])
                gvec = -(Q @ y + c)
                if M.shape[1]:
                    sc = np.maximum(np.abs(M).max(axis=0), 1e-12)
                    mu, _r = _nnls(M / sc, gvec, maxiter=int(_st_m.get("outer_loop.manure_pool_nnls_iter")) * M.shape[1]); mu = mu / sc
                    lam = np.zeros(A.shape[0]); lam[act] = mu[:len(act)]
                else:
                    lam = np.zeros(A.shape[0])
            je, ji = pc
            sl = float(Q[je, je])
            # the pool price the region was solved at (its export column's cost also carries the emission tax,
            # which belongs to the threshold, not to the price)
            pnow = float(getattr(mo.seen, "manure_pool_price", 0.0) or 0.0) if prod == "N" else \
                float((getattr(mo.seen, "manure_pool_price_pk", None) or {}).get(prod, 0.0) or 0.0)
            rce = max(0.0, float(c[je] + Q[je] @ y + A[:, je] @ lam))
            rci = max(0.0, float(c[ji] + Q[ji] @ y + A[:, ji] @ lam))
            rc_ = getattr(mo.res, "nlp_rc", None)
            if rc_ is not None and max(je, ji) < len(rc_):
                # the NLP form: IPOPT's own reduced costs (the fertilisation block is not in the stored A rows)
                rce, rci = max(0.0, float(rc_[je])), max(0.0, float(rc_[ji]))
            # QUASI-NEWTON correction: regions respond less than 1/s per unit of
            # price, because their own N shadow price moves as they trade. Each
            # pool's response factor kappa (realised / planned, Broyden-type)
            # scales the schedules: slope s / kappa, re-anchored at the current
            # trade and price.
            k_ = self.POOL_OF_PREFIX.get(reg[:2], reg[:2])
            kap = float(((getattr(self.sv, "pool_state", None) or {}).get("_kappa") or {}).get(k_, 1.0))
            sl = sl / max(kap, float(_settings().get("outer_loop.manure_pool_kappa_floor")))
            th_e = pnow + sl * float(y[je]) - rce
            th_i = pnow - sl * float(y[ji]) + rci
            # export cap = manure produced at the current solution (a first draft
            # read the LAST row as the cap, but the land rows follow it, so the
            # cap came from the grassland row and exports vanished)
            ev = getattr(mo.res, "pool_manure_vec", None) if prod == "N" else \
                (getattr(mo.res, "pool_manure_vec_pk", None) or {}).get(prod)
            emax = float(ev @ y[:len(ev)]) if ev is not None else 0.0
            if prod == "N":
                # the base exports a constant of the region (supply.manure_base_trade "capri", K167): what the change
                # of exports can take is the manure produced less them, as the region's own cap row
                emax -= float(getattr(mo.res, "pool_manure_x0", 0.0) or 0.0)
            k = self.POOL_OF_PREFIX.get(reg[:2], reg[:2])
            sched.setdefault(k, []).append((th_e, th_i, sl, max(emax, 0.0)))
            # the trade columns' lower bounds (supply.manure_trade_form "capri": minus the gross trade at CAPRI's
            # calibration point; "net": zero)
            lb_ = (getattr(mo.ev, "pool_lb", None) or {}).get(prod) or {}
            elo, ilo = float(lb_.get(je, 0.0)), float(lb_.get(ji, 0.0))
            if form != "capri" and (elo < 0 or ilo < 0):
                raise ValueError('outer_loop.manure_pool_form "schedules" clears trade from zero: it needs '
                                 'supply.manure_trade_form "net"')
            if form == "capri":
                mv_ = (getattr(mo.res, "manure_value", None) or {}).get(prod)
                crec.append({"reg": reg, "k": k, "e": float(y[je]), "i": float(y[ji]), "f": pnow,
                             "cs1": float(Q[je, je]), "cb1": float(Q[ji, ji]), "rce": rce, "rci": rci,
                             "v": None if mv_ is None else float(mv_), "emax": max(emax, 0.0),
                             "elo": elo, "ilo": ilo})
            es[k] = es.get(k, 0.0) + float(y[je]) - float(y[ji])
            sup[k] = sup.get(k, 0.0) + s0
        keys = sorted(sched)
        if not keys:
            self.res.pool_imbalance = 0.0
            return
        hist = getattr(self.sv, "pool_state", None) or {}
        if form == "capri":
            ok, pnew, ship, status, keep = self._clear_pool_capri(prod, keys, crec, cost, hist)
            self.res.pool_solver_status = status
            if ok:
                self.sv.pool_state = {"_plan": ship, "_kappa": {}, "_es": dict(es), **keep}
            else:
                pnew = {k: float(pools.get(k, 0.0)) for k in keys}
        else:
            hist = getattr(self.sv, "pool_state", None) or {}
            plan = hist.get("_plan")
            # Broyden-type update of each pool's response factor: realised change in
            # net exports over the change the previous plan expected
            kappa = dict(hist.get("_kappa") or {})
            es_prev = hist.get("_es") or {}
            if plan and es_prev:
                for k in es:
                    planned = float(plan.get(k, 0.0)) - float(es_prev.get(k, 0.0))
                    realised = float(es[k]) - float(es_prev.get(k, 0.0))
                    if abs(planned) > _settings().get("outer_loop.manure_pool_min_plan") * max(sup.get(k, 0.0), 1.0):
                        _klo, _khi = _settings().get("outer_loop.manure_pool_kappa_bounds")
                        kappa[k] = float(np.clip(kappa.get(k, 1.0) * realised / planned, _klo, _khi))
            hist["_kappa"] = kappa
            self.sv.pool_state = hist
            _ratios = {k: (abs(es[k] - plan.get(k, 0.0)) if plan else abs(es[k])) / sup[k] for k in keys}
            worst = max(_ratios.values())
            self.res.pool_worst_key = max(_ratios, key=_ratios.get)
            # ---- PRIMAL spatial equilibrium on the exact schedules (shipment side),
            # solved with the model's own exact QP solver (the dual price problem
            # with SLSQP failed on the kinks and kept stale prices).
            reg_list = [(k, te, ti, sl, em) for k in keys for (te, ti, sl, em) in sched[k]]
            arcs = [(a, b_, cc) for (a, b_), cc in cost.items() if a in sched and b_ in sched]
            nr, na = len(reg_list), len(arcs)
            nv = 2 * nr + na                                  # e_r, i_r, T_arc
            Qp = np.zeros((nv, nv)); cp_ = np.zeros(nv)
            min_sl = min(r_[3] for r_ in reg_list) if reg_list else 1.0
            for q, (k, te, ti, sl, em) in enumerate(reg_list):
                Qp[q, q] = sl; cp_[q] = -te                   # exporters' benefit (negated)
                Qp[nr + q, nr + q] = sl; cp_[nr + q] = ti     # importers' cost
            for t, (a, b_, cc) in enumerate(arcs):
                Qp[2 * nr + t, 2 * nr + t] = float(_settings().get("outer_loop.manure_pool_arc_ridge")) * min_sl; cp_[2 * nr + t] = cc   # scaled ridge
            rows, rhs, eqs, eqb = [], [], [], []
            for q, (k, te, ti, sl, em) in enumerate(reg_list):
                r_ = np.zeros(nv); r_[q] = 1.0; rows.append(r_); rhs.append(max(em, 0.0))    # e <= manure produced
            for k in keys:
                bal = np.zeros(nv)
                for q, rec in enumerate(reg_list):
                    if rec[0] == k:
                        bal[q] = 1.0; bal[nr + q] = -1.0
                for t, (a, b_, cc) in enumerate(arcs):
                    if a == k: bal[2 * nr + t] -= 1.0
                    if b_ == k: bal[2 * nr + t] += 1.0
                eqs.append(bal); eqb.append(0.0)                 # pool balance as a TRUE equality
            Ap, bp = np.array(rows), np.array(rhs)
            # Interior point (Clarabel, capri_mod/supply/convex_qp.py). An active-set loop
            # failed on the full EU (iteration limit; the balance written as two tight
            # inequalities made its KKT systems singular).
            from capri_mod.supply.convex_qp import solve_convex_qp
            # Scaled: objective by its largest coefficient (prices reach hundreds of EUR/kg N under
            # CAPRI's land rules, slopes differ by orders of magnitude after the kappa correction).
            # Clarabel's AlmostSolved (reduced accuracy) is accepted - the pool test below checks
            # the realised clearing anyway; a failed solve keeps the old prices and is reported.
            _sc = max(float(np.abs(cp_).max()), float(np.abs(Qp).max()), 1e-9)
            sol, ok, _info = solve_convex_qp(Qp / _sc, cp_ / _sc, Ap, bp, np.array(eqs), np.array(eqb),
                                             tol=float(_settings().get("outer_loop.manure_pool_qp_tol")))
            if not ok and "AlmostSolved" in str(_info.get("status", "")):
                ok = True
            if _info.get("y") is not None:
                _info["y"] = np.asarray(_info["y"], float) * _sc
            self.res.pool_solver_status = str(_info.get("status", "?"))
            pnew = {}
            if ok:
                # POOL PRICE = shadow price of the pool's balance equation. For an
                # exporting region the optimality condition is s e - th_e + y_k = 0,
                # so y_k = th_e - s e: the price definition itself, available for
                # EVERY pool. (Taken from actively trading regions only, a pool
                # whose regions did not trade kept a stale price and never cleared
                # - Malta, Cyprus, Lithuania, Latvia on the full EU.)
                yv = _info.get("y")
                for j, k in enumerate(keys):
                    if yv is not None and j < len(yv):
                        pnew[k] = float(yv[j])
                    else:
                        pnew[k] = float(pools.get(k, 0.0))
                ship = {k: 0.0 for k in keys}
                for t, (a, b_, cc) in enumerate(arcs):
                    ship[a] += sol[2 * nr + t]; ship[b_] -= sol[2 * nr + t]
                self.sv.pool_state = {"_plan": ship, "_kappa": kappa, "_es": dict(es)}
            else:
                pnew = {k: float(pools.get(k, 0.0)) for k in keys}
        # CLEARING test on the REALISED regional trade: net exports of each pool
        # must equal its planned net shipments (zero for a closed pool)
        plan_now = (hist.get("_plan") or {}) if isinstance(hist, dict) else {}
        worst = max(abs(es[k] - plan_now.get(k, 0.0)) / sup[k] for k in keys)
        self.res.pool_losf = float(worst)
        if form == "capri" and str(_settings().get("outer_loop.manure_pool_trade_consts")) == "capri":
            # with CAPRI's fixed trade cost constants the pool market does not see what else moves the regions' trade
            # (their N-surplus row), so the regions' trade and the market's plan need not meet: CAPRI reports the gap
            # (losf, simu_manure_market.gms l. 199-204: the supply models' net trade less the market's) and stops on
            # changes between its steps (capmod.gms l. 1369, p_itemsInIters with the market's EXPT and IMPT and the
            # supply models' MTRADE): the test is the change of the market's plan and of the regions' trade since
            # the clearing before, relative to the pool's supply; the gap kept as pool_losf
            es_prev = (hist.get("_es") or {}) if isinstance(hist, dict) else {}
            worst = max(max(abs(ship.get(k, 0.0) - plan_now.get(k, 0.0)), abs(es[k] - es_prev.get(k, es[k] + sup[k])))
                        / sup[k] for k in keys) if ok else 1.0
        if not ok:
            worst = max(worst, 1.0)
        # ADAPTIVE DAMPING of the move to the new equilibrium prices (exact for
        # the current regional schedules; the schedules shift as regions respond).
        # A fixed half step near the solution was stable but slow (full EU: worst
        # pool 5.1% -> 4.3% over 12 iterations). Now: full steps while the gap
        # keeps falling (x1.25 per fall, capped at 1), halved (min 0.25) when it
        # rises.
        acc = getattr(self.sv, "pool_accel", None) or {}
        _st_ = _settings()
        _pu = str(_st_.get("outer_loop.manure_pool_price_update"))
        if _pu not in ("damped", "capri"):
            raise ValueError(f'outer_loop.manure_pool_price_update = "{_pu}": "damped" or "capri"')
        if _pu == "capri":
            # CAPRI's (manuremarket/simu_manure_market.gms l. 214-226): the price sent back to the supply models
            # (p_exoDemand(pool, "UVAG", nutrient), read by supply_model.gms l. 4652) is the weighted average of the
            # pool's market prices (the balance's shadow prices, PMRK) of the last steps, with the weights of CAPRI's
            # price forecast (capmod/define_stepWeights.gms: 0.55 / 0.30 / 0.15, 0.4 / 0.3 / 0.2 / 0.1 from step 20),
            # normalised over the steps available; a failed clearing adds no step (its old prices are kept)
            ph = acc.setdefault("_phist", {})
            it1 = int(getattr(self.ev, "outer_iter_now", 0) or 0) + 1
            wts = tuple(_st_.get("outer_loop.capri_step_weights")
                        if it1 < int(_st_.get("outer_loop.capri_step_weights_late_from"))
                        else _st_.get("outer_loop.capri_step_weights_late"))
            n_keep = max(len(_st_.get("outer_loop.capri_step_weights")), len(_st_.get("outer_loop.capri_step_weights_late")))
            if ok:
                for k in list(pnew):
                    h_ = (ph.get(k) or []) + [float(pnew[k])]
                    ph[k] = h_[-n_keep:]
                    use = list(reversed(ph[k]))[:len(wts)]
                    pnew[k] = p_stepWeights_average(wts, use)
        else:
            om = float(acc.get("_omega", 1.0))
            prev_gap = acc.get("_gap")
            cur_gap = float(max(worst, abs(sum(es.values())) / max(sum(sup.values()), 1e-9)))
            if prev_gap is not None:
                om = (min(1.0, om * _st_.get("outer_loop.manure_pool_omega_up")) if cur_gap < prev_gap
                      else max(_st_.get("outer_loop.manure_pool_omega_min"), om * _st_.get("outer_loop.manure_pool_omega_down")))
            acc["_omega"], acc["_gap"] = om, cur_gap
            for k in list(pnew):
                p_old = None
                for reg_ in getattr(sm, "_models", {}):
                    if self.POOL_OF_PREFIX.get(reg_[:2], reg_[:2]) == k and reg_[:2] in pools:
                        p_old = float(pools[reg_[:2]]); break
                if p_old is not None:
                    pnew[k] = p_old + om * (pnew[k] - p_old)
        self.sv.pool_accel = acc
        out = {}
        for reg in getattr(sm, "_models", {}):
            k = self.POOL_OF_PREFIX.get(reg[:2], reg[:2])
            if k in pnew:
                out[reg[:2]] = pnew[k]
        if prod == "N":
            sm.seen.manure_pool_price = out
        else:
            _sst.setdefault(sm.seen, "manure_pool_price_pk", {})[prod] = out
        # EU-WIDE conservation: realised net exports into all pools should sum
        # to zero; on the full EU it lagged the per-pool measure (200 kt N
        # unaccounted at iteration 6 while every pool was within ~6%)
        eu_unacc = abs(sum(es.values())) / max(sum(sup.values()), 1e-9)
        self.res.pool_eu_unaccounted = float(eu_unacc)
        self.res.pool_imbalance = float(max(worst, eu_unacc))

    def _clear_pool_capri(self, prod, keys, crec, cost, hist):
        """CAPRI's pool market m_mPoolMarket (manuremarket/declare_manure_market.gms l. 99-204; simu_manure_market.gms
        l. 34-89) for one nutrient, on the regions' last solves (crec, from _clear_pool).

        Per region r (CAPRI's terms: P the value of the nutrient, P = - the model's pool price, a fee exporters pay):
          v_r   PSHW, the region's manure value at its solution (ManureNPK_.M; res.manure_value); missing (CAPRI: EPS):
                the price sent the step before, at the first step the calibration dual; at or below 1e-6: the
                step-weighted average of its PSHW of the steps before
          b_r   CAPRI's slope of the excess supply (manure_pool_market_2030.csv es_slope, outer_loop.manure_pool_es_slope)
          z_r   the net export of the last solve (the model's trade columns: the deviation from CAPRI's base trade,
                which the accounts hold); a_r = z_r - b_r v_r, so ES_r(p) = a_r + b_r p passes through (v_r, z_r)
          cs1, cb1  the regional NLP's trade cost slopes (CAPRI's p_manureSell/BuyCostSlope, supply/land.py)
          cs0, cb0  its trade cost constants, from the reduced costs of its trade columns at its solution (CAPRI's
                calibrated p_manureSell/BuyCostConst, FINALIZE of supply/define_manure_trade_costs.gms; the regional
                NLP holds them as the rows its trade columns enter), so the market model's first-order conditions hold
                at the region's solution
        max sum_r [a_r/b_r z_r - z_r^2/(2 b_r) - e_r (cs0 + cs1 e_r/2) - i_r (cb0 + cb1 i_r/2)] - sum_kl c_kl T_kl,
        z_r = e_r - i_r, s.t. per pool k: sum_{r in k} z_r = sum_l (T_kl - T_lk); e_r at most the manure produced.
        outer_loop.manure_pool_solver "nlp" (the default): as CAPRI solves it, "using nlp maximizing v_mPoolBenefits"
        (simu_manure_market.gms l. 160), in CAPRI's variables (v_manureExports, v_manureImports, v_mPoolExports,
        v_mPoolExcessSupply, v_mPoolSurplus, v_mPoolBenefits) and its four rows (e_mPoolExcessSupply, e_mPoolSurplus,
        e_mPoolClear, e_mPoolBenefits), with IPOPT for CAPRI's CONOPT, started from the clearing before
        (_pool_market_nlp); the pool price the dual of e_mPoolExcessSupply (l. 217, PMRK). Where a b_r is negative (a
        negative calibration dual) the problem need not be convex: IPOPT returns a local optimum, as CONOPT does.
        "qp": the same problem as a convex QP (Clarabel), with one balance row per pool (the excess supply and the
        surplus substituted); there a negative b_r must be outweighed by the region's trade cost slopes ((1/b +
        cs1)(1/b + cb1) >= 1/b^2), else the run stops. No calibration wedge in either: at the model's base the pools'
        trade deviations and prices are zero, an equilibrium.
        Returns (ok, prices in the model's convention, planned net shipments by pool, solver status, state to keep)."""
        st = _settings()
        fout = {"N": "MANN", "P": "MANP", "K": "MANK"}[prod]
        bc = getattr(self.par, "pool_es_cache", None)
        if bc is None:
            from capri_mod.data import inputs as _inputs
            t = _inputs.current().csv("manure_pool_market_2030.csv", "environment", float_precision="round_trip")
            bc = {(r, f): (float(b), float(d)) for r, f, b, d in zip(t.region, t.fout, t.es_slope, t.dual_cal)}
            # CAPRI's autarky buffers (declare_manure_market.gms l. 396-436): the pools' base net exports (kt, any
            # nutrient) and buffers (EUR 1000 per t; the Green Deal group's for its isolated pools)
            pool_ = lambda r: self.POOL_OF_PREFIX.get(r[:2], r[:2])     # noqa: E731
            net, buf, buf_gd = {}, {}, {}
            for r, f, x, b0, b1 in zip(t.region, t.fout, t.base_net_export_kt, t.buffer, t.buffer_greendeal):
                k = pool_(r)
                net[(k, f)] = net.get((k, f), 0.0) + float(x)
                buf[k], buf_gd[k] = max(buf.get(k, 0.0), float(b0)), max(buf_gd.get(k, 0.0), float(b1))
            bc = {"es": bc, "net": net, "buffer": buf, "buffer_greendeal": buf_gd}
            self.par.pool_es_cache = bc
        consts = str(st.get("outer_loop.manure_pool_trade_consts"))
        if consts not in ("solution", "capri"):
            raise ValueError(f'outer_loop.manure_pool_trade_consts = "{consts}": "solution" or "capri"')
        held = getattr(self.par, "pool_trade_consts", None)
        if held is None:
            held = self.par.pool_trade_consts = {}
        solver = str(st.get("outer_loop.manure_pool_solver"))
        if solver not in ("nlp", "qp"):
            raise ValueError(f'outer_loop.manure_pool_solver = "{solver}": "nlp" or "qp"')
        reg_terms = []
        mode = str(st.get("outer_loop.manure_pool_es_slope"))
        if mode not in ("capri_code", "capri_doc"):
            raise ValueError(f'outer_loop.manure_pool_es_slope = "{mode}": "capri_code" or "capri_doc"')
        # "capri_doc": the elasticity as written, supply and trade in one unit (CAPRI's code: trade in kt, supply in t)
        b_div = 1.0 if mode == "capri_code" else _T_PER_KT
        it1 = int(getattr(self.ev, "outer_iter_now", 0) or 0) + 1
        wts = tuple(st.get("outer_loop.capri_step_weights") if it1 < int(st.get("outer_loop.capri_step_weights_late_from"))
                    else st.get("outer_loop.capri_step_weights_late"))
        pshw_h = {r: list(v) for r, v in (hist.get("_pshw") or {}).items()}
        nr = len(crec)
        arcs = [(a, b_, cc) for (a, b_), cc in cost.items() if a in keys and b_ in keys]
        na = len(arcs)
        nv = 2 * nr + na
        Qp = np.zeros((nv, nv)); cp_ = np.zeros(nv)
        for q, r_ in enumerate(crec):
            key = (r_["reg"], fout)
            if key not in bc["es"]:
                raise KeyError(f"manure_pool_market_2030.csv: no slope for {key}")
            b, dual = bc["es"][key][0] / b_div, bc["es"][key][1]
            v = r_["v"]
            if v is None:
                # CAPRI's fall-back (simu_manure_market.gms l. 50-66): last step's price sent (the value, - the fee),
                # at the first step the calibration dual (in the model's money, EUR 1000 per t)
                v = -r_["f"] if pshw_h.get(r_["reg"]) else dual
            h_ = (pshw_h.get(r_["reg"]) or []) + [float(v)]
            pshw_h[r_["reg"]] = h_[-max(len(wts), 1):]
            if v <= float(st.get("outer_loop.manure_pool_pshw_floor")) and len(h_) > 1:
                use = list(reversed(h_))[:len(wts)]
                v = p_stepWeights_average(wts, use)
            z = r_["e"] - r_["i"]
            a = p_mPoolSupConst(z, b, v)
            cs1, cb1 = r_["cs1"], r_["cb1"]
            # the constants: the region's export (import) reduced cost = v + cs0 + cs1 e - P (P + cb0 + cb1 i - v)
            cs0 = r_["rce"] - r_["f"] - cs1 * r_["e"] - v
            cb0 = r_["rci"] + r_["f"] - cb1 * r_["i"] + v
            if consts == "capri":
                # CAPRI's p_manureSellCostConst and p_manureBuyCostConst, calibrated once at the base (FINALIZE of
                # supply/define_manure_trade_costs.gms) and held: the constants of the region's first clearing (the
                # baseline's calibration point), then fixed
                cs0, cb0 = held.setdefault((r_["reg"], fout), (cs0, cb0))
            be = 1.0 / b
            if solver == "qp" and b < 0 and ((be + cs1) < 0 or (be + cs1) * (be + cb1) < be * be):
                raise ValueError(f"manure pool {prod}: {r_['reg']} has a negative excess-supply slope ({b:.6g}) its "
                                 f"trade costs do not outweigh: the market model is not convex")
            ie, ii = q, nr + q
            reg_terms.append((a, b, cs0, cs1, cb0, cb1))
            q_ee, q_ii, q_ei, c_e, c_i = e_mPoolSurplus(a, b, cs0, cs1, cb0, cb1)
            Qp[ie, ie] += q_ee; Qp[ii, ii] += q_ii; Qp[ie, ii] -= q_ei; Qp[ii, ie] -= q_ei
            cp_[ie] = c_e
            cp_[ii] = c_i
        # CAPRI's autarky buffers (p_mTradeAddCost, declare_manure_market.gms l. 396-436): a link unused at the
        # calibration point costs (buffer_k + buffer_l) / 2 more, so that new flows need a price gap beyond the trade
        # cost; CAPRI's calibrated links are those from its exporting pools to its importing ones (at the 2030
        # calibration point BL, DE, NL to FR, for N and P), exempt in both directions. Its term max(0, P_l - P_k - c)
        # is zero here (the model's pool prices are equal, zero, at the base)
        tol_ = float(st.get("outer_loop.manure_pool_autarky_tol"))
        exp_ = {k for (k, f), x in bc["net"].items() if x > tol_}
        imp_ = {k for (k, f), x in bc["net"].items() if x < -tol_}
        used_ = {(a_, b_) for a_ in exp_ for b_ in imp_} | {(b_, a_) for a_ in exp_ for b_ in imp_}
        bf_ = bc["buffer_greendeal"] if bool(getattr(self.ev, "greendeal_group", False)) else bc["buffer"]
        for t, (a_, b_, cc) in enumerate(arcs):
            add_ = 0.0 if (a_, b_) in used_ else p_mTradeAddCost(bf_.get(a_, 0.0), bf_.get(b_, 0.0))
            cp_[2 * nr + t] = cc + add_
        Ap = np.zeros((nr, nv)); bp = np.zeros(nr)
        for q, r_ in enumerate(crec):
            Ap[q, q] = 1.0; bp[q] = r_["emax"]                # exports at most the manure produced
        Aeq = np.zeros((len(keys), nv))
        for j, k in enumerate(keys):
            for q, r_ in enumerate(crec):
                if r_["k"] == k:
                    Aeq[j, q] = 1.0; Aeq[j, nr + q] = -1.0
            for t, (a_, b_, cc) in enumerate(arcs):
                if a_ == k: Aeq[j, 2 * nr + t] -= 1.0
                if b_ == k: Aeq[j, 2 * nr + t] += 1.0
        if solver == "nlp":
            # the trade columns' lower bounds (minus the gross trade at CAPRI's calibration point under supply.
            # manure_trade_form "capri", zero under "net"), as the QP's shift below
            lo = np.array([float(r_.get("elo", 0.0)) for r_ in crec] + [float(r_.get("ilo", 0.0)) for r_ in crec])
            up = np.array([float(r_["emax"]) for r_ in crec] + [np.inf] * nr)
            x0 = np.array([float(r_["e"]) for r_ in crec] + [float(r_["i"]) for r_ in crec])
            ok, pnew, xs, status, its = self._pool_market_nlp(keys, crec, reg_terms, arcs, cp_[2 * nr:], lo, up, x0,
                                                               hist.get("_clear_x"))
            from capri_mod import runlog as _runlog
            _runlog.current().solver(f"--- Manure pool market {fout}: {nv:,} trade variables ({nr} regions, {na} links), "
                                     f"{len(keys)} pools; IPOPT {status}, {its} iterations")
            ship = {k: 0.0 for k in keys}
            if ok:
                for t, (a_, b_, cc) in enumerate(arcs):
                    ship[a_] += xs[2 * nr + t]; ship[b_] -= xs[2 * nr + t]
            self.res.pool_worst_key = ""
            return ok, pnew, ship, status, {"_pshw": pshw_h, "_clear_x": [float(v) for v in xs] if ok else hist.get("_clear_x")}
        from capri_mod.supply.convex_qp import solve_convex_qp
        # the regions' trade bounded below by minus their gross trade at CAPRI's calibration point (supply.manure_trade_
        # form "capri"; zero under "net"): solved in the shifted variables x' = x + s >= 0 (the solver bounds every
        # variable at zero), the same problem: c' = c - Q s, A x' <= b + A s, Aeq x' = Aeq s
        sh = np.zeros(nv)
        for q, r_ in enumerate(crec):
            sh[q], sh[nr + q] = -float(r_.get("elo", 0.0)), -float(r_.get("ilo", 0.0))
        cps = cp_ - Qp @ sh
        _sc = max(float(np.abs(cps).max()), float(np.abs(Qp).max()), 1e-12)
        sol, ok, info = solve_convex_qp(Qp / _sc, cps / _sc, Ap, bp + Ap @ sh, Aeq, Aeq @ sh,
                                        tol=float(st.get("outer_loop.manure_pool_qp_tol")))
        if sol is not None:
            sol = np.asarray(sol, float) - sh
        status = str(info.get("status", "?"))
        if not ok and "AlmostSolved" in status:
            ok = True
        from capri_mod import runlog as _runlog
        _runlog.current().solver(f"--- Manure pool market {fout}: {nv:,} variables ({nr} regions, {na} links), "
                                 f"{len(keys)} pools; Clarabel {status}, {info.get('iterations')} iterations")
        pnew, ship = {}, {k: 0.0 for k in keys}
        if ok:
            # Clarabel: Q x + c + Aeq' y = 0; an exporter's condition gives y_k = -(its marginal value + sell cost) =
            # the model's pool price (a fee), the value P = -y_k
            yv = np.asarray(info.get("y"), float) * _sc
            pnew = {k: float(yv[j]) for j, k in enumerate(keys)}
            for t, (a_, b_, cc) in enumerate(arcs):
                ship[a_] += sol[2 * nr + t]; ship[b_] -= sol[2 * nr + t]
        self.res.pool_worst_key = ""
        return ok, pnew, ship, status, {"_pshw": pshw_h}

    def _pool_market_nlp(self, keys, crec, reg_terms, arcs, arc_cost, lo, up, x0, x_prev=None):
        """CAPRI's m_mPoolMarket for one nutrient as CAPRI solves it, "using nlp maximizing v_mPoolBenefits"
        (manuremarket/simu_manure_market.gms l. 160; the model: declare_manure_market.gms l. 99-157, its four rows
        e_mPoolExcessSupply, e_mPoolSurplus, e_mPoolClear, e_mPoolBenefits, capri_mod/market/equations/manuremarket/
        declare_manure_market.py), with IPOPT for CAPRI's CONOPT.

        Variables: v_manureExports and v_manureImports per region (e, i; between lo and up: the exports at most the
        manure produced, both at least minus the gross trade at CAPRI's calibration point), v_mPoolExports per link (T >=
        0; the links with a trade cost, as simu_manure_market.gms l. 94-95 fixes the others), v_mPoolExcessSupply and
        v_mPoolSurplus per pool, v_mPoolBenefits. reg_terms: (a, b, cs0, cs1, cb0, cb1) per region (crec's order),
        arc_cost the links' p_mPoolTradeCost (with the autarky buffer). Start: x_prev, the clearing before when it has
        the same variables, else the regions' trade of their last solves (x0), no links' trade. Returns (ok, the pools'
        prices in the model's convention: minus CAPRI's PMRK, the dual of e_mPoolExcessSupply; the solution's e, i, T;
        IPOPT's status; its iterations)."""
        import casadi as ca
        from capri_mod.supply.capri_regional_nlp import linear_solver_options as _linear_solver_options
        st = _settings()
        nr, na, nk = len(crec), len(arcs), len(keys)
        e = ca.SX.sym("v_manureExports", nr); i = ca.SX.sym("v_manureImports", nr)
        T = ca.SX.sym("v_mPoolExports", na)
        ES = ca.SX.sym("v_mPoolExcessSupply", nk); S = ca.SX.sym("v_mPoolSurplus", nk)
        B = ca.SX.sym("v_mPoolBenefits")
        kix = {k: j for j, k in enumerate(keys)}
        g = []
        for j, k in enumerate(keys):                                  # e_mPoolExcessSupply(rManPool)
            m = [q for q, r_ in enumerate(crec) if r_["k"] == k]
            g.append(e_mPoolExcessSupply(ES[j], [e[q] for q in m], [i[q] for q in m]))
        for j, k in enumerate(keys):                                  # e_mPoolSurplus(rManPool)
            m = [q for q, r_ in enumerate(crec) if r_["k"] == k]
            g.append(e_mPoolSurplus_row(S[j], [(e[q], i[q]) + tuple(reg_terms[q]) for q in m]))
        for j, k in enumerate(keys):                                  # e_mPoolClear(rManPool)
            out_ = [T[t] for t, (a_, b_, _) in enumerate(arcs) if a_ == k]
            in_ = [T[t] for t, (a_, b_, _) in enumerate(arcs) if b_ == k]
            g.append(e_mPoolClear(out_, in_, ES[j]))
        g.append(e_mPoolBenefits(B, [S[j] for j in range(nk)], [T[t] for t in range(na)], list(arc_cost)))
        x = ca.vertcat(e, i, T, ES, S, B)
        nx = 2 * nr + na + 2 * nk + 1
        lbx = np.concatenate([lo, np.zeros(na), np.full(2 * nk + 1, -np.inf)])
        ubx = np.concatenate([up, np.full(na, np.inf), np.full(2 * nk + 1, np.inf)])
        # the start: the clearing before, else the regions' last trade and the rows' values at it
        if x_prev is not None and len(x_prev) == 2 * nr + na:
            et = np.asarray(x_prev, float)
        else:
            et = np.concatenate([x0, np.zeros(na)])
        et = np.minimum(np.maximum(et, np.concatenate([lo, np.zeros(na)])), np.concatenate([up, np.full(na, np.inf)]))
        z_ = et[:nr] - et[nr:2 * nr]
        es0 = np.array([sum(z_[q] for q, r_ in enumerate(crec) if r_["k"] == k) for k in keys])
        sur = np.zeros(nk)
        for q, r_ in enumerate(crec):
            a, b, cs0, cs1, cb0, cb1 = reg_terms[q]
            eq, iq = et[q], et[nr + q]
            sur[kix[r_["k"]]] += (a / b * (eq - iq) - (eq - iq) ** 2 / (2 * b) - eq * (cs0 + 0.5 * cs1 * eq)
                                  - iq * (cb0 + 0.5 * cb1 * iq))
        b0 = float(sur.sum() - np.dot(et[2 * nr:], arc_cost))
        xstart = np.concatenate([et, es0, sur, [b0]])
        sc = max(1.0, abs(b0), float(np.abs(sur).max()) if nk else 1.0)
        solver = ca.nlpsol("m_mPoolMarket", "ipopt", {"x": x, "f": -B / sc, "g": ca.vertcat(*g)},
                           {"ipopt.print_level": int(st.get("diagnostics.ipopt_print_level")), "print_time": 0,
                            "ipopt.tol": float(st.get("outer_loop.manure_pool_nlp_tol")),
                            "ipopt.max_iter": int(st.get("outer_loop.manure_pool_nlp_max_iter")),
                            **_linear_solver_options()})
        sol = solver(x0=xstart, lbx=lbx, ubx=ubx, lbg=0.0, ubg=0.0)
        stats = solver.stats()
        status = str(stats.get("return_status", "?"))
        ok = bool(stats.get("success")) or status in ("Solve_Succeeded", "Solved_To_Acceptable_Level")
        xs = np.asarray(sol["x"], float).ravel()
        lam = np.asarray(sol["lam_g"], float).ravel() * sc
        # e_mPoolExcessSupply's dual, GAMS's marginal of the maximisation (CAPRI's PMRK, the nutrient's value): with
        # f = -v_mPoolBenefits / sc and the rows g = 0, d v_mPoolBenefits / d (the row's right-hand side) = lam_g x sc
        pnew = {k: -float(lam[j]) for j, k in enumerate(keys)} if ok else {}
        return ok, pnew, xs[:2 * nr + na], status, int(stats.get("iter_count", 0) or 0)
