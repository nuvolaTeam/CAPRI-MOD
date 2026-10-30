"""The manure pools between regions (CAPRI's manure trade, cleared between solves).

CAPRIModel's methods, moved unchanged from capri_mod/model.py (refactor stage 4a,
docs/design/ARCHITECTURE_REFACTOR.md); the module-level names they use are model's, given to this
module once model is loaded (capri_mod.coupling.inject); the annotations are not evaluated.
"""
from __future__ import annotations


class ManureBlock:
    def _update_manure_pools(self) -> None:
        """Clear CAPRI's CONNECTED manure pools on the regions' EXACT schedules.

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
        import json as _json
        from pathlib import Path as _P
        from scipy.optimize import nnls as _nnls, minimize as _min
        sm = self.supply_module
        pools = dict(getattr(sm, "manure_pool_price", None) or {})
        cost = getattr(self, "_pool_cost_cache", None)
        if cost is None:
            f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "environment" / "manure_pool_costs.json"
            cost = {}
            if f.exists():
                for k, v in _json.load(open(f))["pairs"].items():
                    a, b = k.split("|"); cost[(a, b)] = v["eur_per_t_n"] / 1000.0
            self._pool_cost_cache = cost
        sched, es, sup = {}, {}, {}
        for reg, mo in getattr(sm, "_models", {}).items():
            pc = getattr(mo, "_pool_cols", []) or []
            aug = getattr(mo, "_last_aug", None)
            s0 = float(getattr(mo, "_manure_supply0", 0.0) or 0.0)
            if len(pc) != 2 or aug is None or s0 <= 0:
                continue
            Q, c, A, b, y = aug
            if max(pc) >= len(y):          # stored problem predates the market columns
                continue
            # row duals: the regional NLP's own multipliers (its feed block is not in the stored
            # problem, so duals recovered from the stored problem's KKT conditions were wrong and the
            # pools stopped clearing); else recovered by NNLS from the active rows of the stored problem
            zc = getattr(mo, "_last_duals", None)
            if zc is not None and len(zc) == A.shape[0]:
                lam = np.maximum(np.asarray(zc, float), 0.0)
            else:
                act = [r for r in range(A.shape[0]) if A[r] @ y >= b[r] - 1e-6 * max(1.0, abs(float(b[r])))]
                bnd = [q for q in range(len(y)) if y[q] <= 1e-9]
                M = np.hstack([A[act].T if act else np.zeros((len(y), 0)), -np.eye(len(y))[:, bnd]])
                gvec = -(Q @ y + c)
                if M.shape[1]:
                    sc = np.maximum(np.abs(M).max(axis=0), 1e-12)
                    mu, _r = _nnls(M / sc, gvec, maxiter=60 * M.shape[1]); mu = mu / sc
                    lam = np.zeros(A.shape[0]); lam[act] = mu[:len(act)]
                else:
                    lam = np.zeros(A.shape[0])
            je, ji = pc
            sl = float(Q[je, je])
            # the pool price the region was solved at (its export column's cost also carries the emission tax,
            # which belongs to the threshold, not to the price)
            pnow = float(getattr(mo, "manure_pool_price", 0.0) or 0.0)
            rce = max(0.0, float(c[je] + Q[je] @ y + A[:, je] @ lam))
            rci = max(0.0, float(c[ji] + Q[ji] @ y + A[:, ji] @ lam))
            rc_ = getattr(mo, "_nlp_rc", None)
            if rc_ is not None and max(je, ji) < len(rc_):
                # the NLP form: IPOPT's own reduced costs (the fertilisation block is not in the stored A rows)
                rce, rci = max(0.0, float(rc_[je])), max(0.0, float(rc_[ji]))
            # QUASI-NEWTON correction: regions respond less than 1/s per unit of
            # price, because their own N shadow price moves as they trade. Each
            # pool's response factor kappa (realised / planned, Broyden-type)
            # scales the schedules: slope s / kappa, re-anchored at the current
            # trade and price.
            k_ = self.POOL_OF_PREFIX.get(reg[:2], reg[:2])
            kap = float(((getattr(self, "_pool_state", None) or {}).get("_kappa") or {}).get(k_, 1.0))
            sl = sl / max(kap, 1e-3)
            th_e = pnow + sl * float(y[je]) - rce
            th_i = pnow - sl * float(y[ji]) + rci
            # export cap = manure produced at the current solution (a first draft
            # read the LAST row as the cap, but the land rows follow it, so the
            # cap came from the grassland row and exports vanished)
            ev = getattr(mo, "_pool_manure_vec", None)
            emax = float(ev @ y[:len(ev)]) if ev is not None else 0.0
            k = self.POOL_OF_PREFIX.get(reg[:2], reg[:2])
            sched.setdefault(k, []).append((th_e, th_i, sl, max(emax, 0.0)))
            es[k] = es.get(k, 0.0) + float(y[je]) - float(y[ji])
            sup[k] = sup.get(k, 0.0) + s0
        keys = sorted(sched)
        if not keys:
            self._pool_imbalance = 0.0
            return
        hist = getattr(self, "_pool_state", None) or {}
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
        self._pool_state = hist
        _ratios = {k: (abs(es[k] - plan.get(k, 0.0)) if plan else abs(es[k])) / sup[k] for k in keys}
        worst = max(_ratios.values())
        self._pool_worst_key = max(_ratios, key=_ratios.get)
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
            Qp[2 * nr + t, 2 * nr + t] = 1e-3 * min_sl; cp_[2 * nr + t] = cc   # scaled ridge
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
        self._pool_solver = _info
        self._pool_solver_status = str(_info.get("status", "?"))
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
            self._pool_flows = {(a, b_): float(sol[2 * nr + t]) for t, (a, b_, cc) in enumerate(arcs) if sol[2 * nr + t] > 1e-3}
            self._pool_state = {"_plan": ship, "_kappa": kappa, "_es": dict(es)}
        else:
            pnew = {k: float(pools.get(k, 0.0)) for k in keys}
        # CLEARING test on the REALISED regional trade: net exports of each pool
        # must equal its planned net shipments (zero for a closed pool)
        plan_now = (hist.get("_plan") or {}) if isinstance(hist, dict) else {}
        worst = max(abs(es[k] - plan_now.get(k, 0.0)) / sup[k] for k in keys)
        if not ok:
            worst = max(worst, 1.0)
        # ADAPTIVE DAMPING of the move to the new equilibrium prices (exact for
        # the current regional schedules; the schedules shift as regions respond).
        # A fixed half step near the solution was stable but slow (full EU: worst
        # pool 5.1% -> 4.3% over 12 iterations). Now: full steps while the gap
        # keeps falling (x1.25 per fall, capped at 1), halved (min 0.25) when it
        # rises.
        acc = getattr(self, "_pool_accel", None) or {}
        om = float(acc.get("_omega", 1.0))
        prev_gap = acc.get("_gap")
        cur_gap = float(max(worst, abs(sum(es.values())) / max(sum(sup.values()), 1e-9)))
        if prev_gap is not None:
            _st_ = _settings()
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
        self._pool_accel = acc
        out = {}
        for reg in getattr(sm, "_models", {}):
            k = self.POOL_OF_PREFIX.get(reg[:2], reg[:2])
            if k in pnew:
                out[reg[:2]] = pnew[k]
        sm.manure_pool_price = out
        # EU-WIDE conservation: realised net exports into all pools should sum
        # to zero; on the full EU it lagged the per-pool measure (200 kt N
        # unaccounted at iteration 6 while every pool was within ~6%)
        eu_unacc = abs(sum(es.values())) / max(sum(sup.values()), 1e-9)
        self._pool_eu_unaccounted = float(eu_unacc)
        self._pool_imbalance = float(max(worst, eu_unacc))
        self._pool_trace = getattr(self, "_pool_trace", []) + [(float(worst), float(eu_unacc))]
