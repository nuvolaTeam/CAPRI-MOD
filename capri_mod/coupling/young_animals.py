"""Young animals between the supply models and the market: their balance by market region, prices from the market or the model's own update, the state the market clears.

CAPRIModel's methods, moved unchanged from capri_mod/model.py (refactor stage 4a,
docs/design/ARCHITECTURE_REFACTOR.md); the module-level names they use are model's, given to this
module once model is loaded (capri_mod.coupling.inject); the annotations are not evaluated.
"""
from __future__ import annotations


class YoungAnimalBlock:
    def _yani_market_region(self, reg: str) -> str:
        """The young-animal market of a supply region: CAPRI clears young animals per market region (yaniMarket_ per
        RM): the EU (one region) or its trade block; Norway its own (NOR, K56)."""
        mm = self.market_module
        return (mm.sup_region_of_country(reg) if hasattr(mm, "sup_region_of_country") else None) \
            or mm.eu_region_of_country(reg) or mm.EU[0]

    def _young_animal_net_by_country(self, supply_results) -> dict:
        """{country: {good: net balance (production - use, 1000 head)}} - _young_animal_balance per country (CAPRI's
        p_hessNQSupp rows for xxOmYani are per member state, calibrate_supply.gms)."""
        out = {}
        for reg, res in (supply_results or {}).items():
            net, _ = self._young_animal_balance({reg: res})
            cc = REGION_TO_COUNTRY.get(reg, reg)              # the country keys of aggregate_supply(by_country=True)
            d = out.setdefault(cc, {})
            for (_mr, g), v in net.items():
                d[g] = d.get(g, 0.0) + float(v)
        return out

    def _young_animal_balance(self, supply_results):
        """Net balance (production - use, 1000 head) and production of each young-animal good per young-animal market
        (EU27, or each EU trade block), {(market, good): value}, from the regional results and CAPRI's
        coefficients."""
        from capri_mod.supply.supply_module import young_animal_table
        tab = young_animal_table()
        net, prod = {}, {}
        for reg, res in (supply_results or {}).items():
            rec = tab.get(reg) or {}
            x = getattr(res, "activities", None)
            if x is None:
                continue
            mr = self._yani_market_region(reg)
            # bulls and heifers at the low-intensity activity turn over more animals per stall, each
            # bought as a young animal (Sprint 7c): z stalls x use per head x (low - high) / average
            cz = getattr(res, "cattle_shift", None) or {}
            ct = (self.data.get("cattle_intensity") or {}).get(reg) or {}
            from capri_mod.supply.supply_module import RegionalSupplyModel as _RSM0
            _member_splits = bool(getattr(_RSM0, "use_cattle_member_splits", False))
            for g, r in rec.items():
                p_ = sum(float(c) * float(x.get(a, 0.0) or 0.0) for a, c in r.get("produce", {}).items())
                u_ = sum(float(c) * float(x.get(a, 0.0) or 0.0) for a, c in r.get("use", {}).items())
                # every split of a cattle animal (key "BULL", "HFRS:rep", "CALV:male", ...): z stalls x use / production
                # per head x (a - b) / average; the intensity pairs' young bought as before (dyoung_rel)
                if not _member_splits:
                    # the intensity pairs alone (Sprint 7c), as in the validated runs r86 / r87
                    u_ += sum(float(c) * float(cz.get(a, 0.0)) * float(ct[a]["dyoung_rel"])
                              for a, c in r.get("use", {}).items() if a in cz and a in ct)
                    net[(mr, g)] = net.get((mr, g), 0.0) + p_ - u_
                    prod[(mr, g)] = prod.get((mr, g), 0.0) + p_
                    continue
                for k_, z_ in cz.items():
                    a_ = k_.split(":")[0]
                    if not z_ or k_ not in ct:
                        continue
                    cu = r.get("use", {}).get(a_)
                    if cu:
                        du = ct[k_].get(f"duse_{g}_rel")
                        du = float(ct[k_]["dyoung_rel"]) if du is None or du != du else float(du)
                        u_ += float(cu) * float(z_) * du
                    cp_ = r.get("produce", {}).get(a_) if _member_splits else None
                    dp = ct[k_].get(f"dprod_{g}_rel")
                    if cp_ and dp is not None and dp == dp:
                        p_ += float(cp_) * float(z_) * float(dp)
                net[(mr, g)] = net.get((mr, g), 0.0) + p_ - u_
                prod[(mr, g)] = prod.get((mr, g), 0.0) + p_
        return net, prod

    def _update_young_animal_prices(self, supply_results, ref) -> None:
        """Clear CAPRI's young-animal markets (arm/market_model.gms yaniMarket_ per market region): the net balance
        of each good in each young-animal market (the EU, or each EU trade block) stays at its baseline level (young
        animals are not traded with third countries nor, in CAPRI, between the trade blocks) and the prices adjust.
        As CAPRI's market model, the supply response is approximated from the supply models' PMP terms - here
        dx = Q^-1 dc per region (the normalised-quadratic approximation, CAPRI p_hessNQSupp) - and the approximation
        is renewed every outer iteration; a damped Newton step on the price ratios, per market."""
        from capri_mod.supply.supply_module import young_animal_table
        tab = young_animal_table()
        net, prod = self._young_animal_balance(supply_results)
        sm = self.supply_module
        markets = sorted({mr for (mr, _g) in ref})
        ratio_m = dict(getattr(sm, "yani_price_ratio_m", None) or {})
        worst = 0.0
        lo, hi = self.YANI_RATIO_BOUNDS
        for mr in markets:
            goods = sorted(g for (m_, g) in ref if m_ == mr)
            gi = {g: i for i, g in enumerate(goods)}
            J = np.zeros((len(goods), len(goods)))
            n_exact = 0
            for reg, res in (supply_results or {}).items():
                rec = tab.get(reg)
                model = getattr(sm, "_models", {}).get(reg)
                if not rec or self._yani_market_region(reg) != mr:
                    continue
                # the region's response from its solved NLP, constraints included (K65; SupplyModel._yani_response)
                ex = getattr(res, "yani_dnet", None)
                _ue = getattr(self, "use_yani_exact", None)
                if _ue is None:
                    from capri_mod.supply.supply_module import RegionalSupplyModel as _RSMe
                    _ue = bool(getattr(_RSMe, "use_cattle_member_splits", False))
                if ex is not None and _ue:
                    eg = {g: i for i, g in enumerate(ex["goods"])}
                    if all(g in eg for g in goods if g in rec):
                        dn = np.asarray(ex["dnet"], float)
                        for g2 in goods:
                            for g1 in goods:
                                if g2 in eg and g1 in eg:
                                    J[gi[g2], gi[g1]] += dn[eg[g2], eg[g1]]
                        n_exact += 1
                        continue
                if model is None or getattr(model, "Q", None) is None:
                    continue
                acts = list(model.acts)
                Qi = getattr(model, "_Q_inv", None)
                if Qi is None or Qi.shape[0] != len(acts):
                    Qi = np.linalg.pinv(np.asarray(model.Q, float))
                    model._Q_inv = Qi
                N = np.zeros((len(acts), len(goods))); v = np.zeros(len(goods))
                for g, r in rec.items():
                    if g not in gi:
                        continue
                    v[gi[g]] = float(r.get("value_eur_head", 0.0) or 0.0) * float(
                        ((self.data.get("young_animal_value_factor") or {}).get(reg) or {}).get(g, 1.0))
                    for a, c in r.get("produce", {}).items():
                        if a in acts:
                            N[acts.index(a), gi[g]] += float(c)
                    for a, c in r.get("use", {}).items():
                        if a in acts:
                            N[acts.index(a), gi[g]] -= float(c)
                J += N.T @ Qi @ (N * v)
                # the cattle splits (CAPRI's replacement heifers and calves with their own levels, per sex): their
                # response to the young-animal prices, z = H^-1 dc, with their own young-animal coefficients - without
                # it the per-sex markets saw only the animals' fixed mixes (male and female calves bought in fixed
                # proportion: a singular direction) and the prices of the two sexes ran apart (r89: x 8 and -1)
                ct = (self.data.get("cattle_intensity") or {}).get(reg) or {}
                from capri_mod.supply.supply_module import RegionalSupplyModel as _RSM1
                zk = [k for k in (getattr(res, "cattle_shift", None) or {}) if k in ct] \
                    if getattr(_RSM1, "use_cattle_member_splits", False) else []
                if zk:
                    from capri_mod.supply.supply_module import RegionalSupplyModel as _RSM
                    zk, Hz = _RSM.cattle_split_hessian(ct, zk)
                    if zk:
                        Nz = np.zeros((len(zk), len(goods)))
                        for i_, k_ in enumerate(zk):
                            a_ = k_.split(":")[0]
                            for g, r in rec.items():
                                if g not in gi:
                                    continue
                                cp_ = float(r.get("produce", {}).get(a_, 0.0) or 0.0)
                                cu_ = float(r.get("use", {}).get(a_, 0.0) or 0.0)
                                dp_ = ct[k_].get(f"dprod_{g}_rel")
                                du_ = ct[k_].get(f"duse_{g}_rel")
                                du_ = float(ct[k_]["dyoung_rel"]) if (du_ is None or du_ != du_) else float(du_)
                                dp_ = 0.0 if (dp_ is None or dp_ != dp_) else float(dp_)
                                Nz[i_, gi[g]] = cp_ * dp_ - cu_ * du_
                        J += Nz.T @ np.linalg.pinv(Hz) @ (Nz * v)
            gap = np.array([net.get((mr, g), 0.0) - ref[(mr, g)] for g in goods])
            # the imbalance relative to the market's production, or to a tenth of the good's production over all
            # young-animal markets where the market is smaller (Norway's: about 1% of the EU's calves, where solver
            # noise of 2 thousand heads was 0.8% and kept the outer loop from settling; REGISTERED tolerance choice)
            _tot = {g: sum(float(v_) for (m_, g_), v_ in prod.items() if g_ == g) for g in goods}
            _sms = float(_settings().get("young_animals.small_market_scale"))
            scale = np.array([max(prod.get((mr, g), 0.0), _sms * _tot[g], 1.0) for g in goods])
            worst = max(worst, float(np.max(np.abs(gap) / scale)) if len(goods) else 0.0)
            ratio = dict(ratio_m.get(mr) or {g: 1.0 for g in goods})
            try:
                d = np.linalg.solve(J, -gap)
            except np.linalg.LinAlgError:
                d = np.linalg.lstsq(J, -gap, rcond=None)[0]
            for g in goods:
                # the step is limited to 30% of the current price or of the base price, whichever is larger (d is the
                # change of the ratio; a limit relative to the current price alone could never cross zero)
                lim = float(_settings().get("young_animals.max_step")) * max(abs(ratio.get(g, 1.0)), 1.0)
                step = float(np.clip(self.YANI_RELAXATION * d[gi[g]], -lim, lim))
                ratio[g] = float(np.clip(ratio.get(g, 1.0) + step, lo, hi))
            ratio_m[mr] = ratio
        self._yani_imbalance = worst
        self._publish_young_animal_prices(ratio_m, ref, net, prod, markets)

    def _yani_in_market_now(self) -> bool:
        """The young-animal markets are cleared inside the market (CAPRI's yaniMarket_ with the market's supply
        functions): with CAPRI's market supply functions (market.market_supply_nq) built, for the EU market or each of
        CAPRI's two trade blocks (their Hessians, the sum of their member states'; since 29 October 2026 the blocks as
        the one EU market)."""
        mm = self.market_module
        hs = mm.par.supply_hessian or {}
        hl = list((hs.get("blocks") or {}).values()) if getattr(mm, "eu_blocks", False) else [hs.get("eu")]
        return (bool(getattr(self, "market_supply_nq", False)) and len(hl) > 0
                and all(h is not None and len(h) and any(str(x).startswith("YANI:") for x in h.index) for h in hl))

    def _young_animal_state_to_market(self, supply_results, ref) -> None:
        """The supply models' young-animal state for the market's clearing (CAPRI simu_calibration_to_supply.gms
        l. 166-175, 360-368: the market's young-animal net supply recalibrated to the supply models' latest solution):
        per market, each good's net balance now, its reference (the baseline's) and the price ratio those models saw;
        also the imbalance reported by the outer loop (net - reference over the market's production)."""
        net, prod = self._young_animal_balance(supply_results)
        ratio_m = dict(getattr(self.supply_module, "yani_price_ratio_m", None) or {})
        _tot = {}
        for (m_, g_), v_ in prod.items():
            _tot[g_] = _tot.get(g_, 0.0) + float(v_)
        _sms = float(_settings().get("young_animals.small_market_scale"))
        st, worst = {}, 0.0
        for mr in sorted({mr for (mr, _g) in ref}):
            goods = sorted(g for (m_, g) in ref if m_ == mr)
            for g in goods:
                sc_ = max(prod.get((mr, g), 0.0), _sms * _tot.get(g, 0.0), 1.0)
                worst = max(worst, abs(net.get((mr, g), 0.0) - ref[(mr, g)]) / sc_)
            st[mr] = {"goods": goods, "net": {g: float(net.get((mr, g), 0.0)) for g in goods},
                      "ref": {g: float(ref[(mr, g)]) for g in goods},
                      "seen": {g: float((ratio_m.get(mr) or {}).get(g, 1.0)) for g in goods},
                      "bounds": tuple(self.YANI_RATIO_BOUNDS)}
        self._yani_imbalance = worst
        self._yani_np = (net, prod)
        self.market_module.seen.yani_state = st
        self.market_module.ev.yani_market_now = {}

    def _young_animal_prices_from_market(self, ref) -> None:
        """The young-animal prices the market cleared, passed to the supply models with the same adaptive step as the
        products' prices (CAPRI passes every market price on through its price forecast, define_stepWeights.gms)."""
        now = self.market_module.ev.yani_market_now or {}
        if not now:
            return
        ratio_m = {k: dict(v) for k, v in (getattr(self.supply_module, "yani_price_ratio_m", None) or {}).items()}
        w_ = getattr(self, "_yani_w", None) or {}
        gp_ = getattr(self, "_yani_gprev", None) or {}
        _st = _settings()
        for mr, d in now.items():
            cur = ratio_m.setdefault(mr, {})
            for g, r_t in d.items():
                r0 = float(cur.get(g, 1.0))
                gap = float(r_t) - r0
                w = float(w_.get((mr, g), self.PRICE_SIGNAL_RELAXATION))
                if (mr, g) in gp_:
                    w = (max(_st.get("outer_loop.relax_floor"), w * _st.get("outer_loop.relax_step_down"))
                         if gap * gp_[(mr, g)] < 0 else min(self.PRICE_SIGNAL_RELAXATION, w * _st.get("outer_loop.relax_step_up")))
                w_[(mr, g)], gp_[(mr, g)] = w, gap
                if self._capri_price_update():
                    # CAPRI's price forecast on the young-animal prices the market cleared
                    yh = self.__dict__.setdefault("_capri_yani_hist", {})
                    yh[(mr, g)] = ((yh.get((mr, g)) or []) + [float(r_t)])[-4:]
                    cur[g] = float(self._capri_forecast(yh[(mr, g)], int(getattr(self, "_outer_iter_now", 0))))
                else:
                    cur[g] = r0 + w * gap
        self._yani_w, self._yani_gprev = w_, gp_
        net, prod = getattr(self, "_yani_np", ({}, {}))
        self._publish_young_animal_prices(ratio_m, ref, net, prod, sorted({mr for (mr, _g) in ref}))

    def _publish_young_animal_prices(self, ratio_m, ref, net, prod, markets) -> None:
        """Hand the young-animal prices of each market ({market: {good: ratio}}) to the supply models: per member
        state where markets are per trade block or Norway's, and the EU's production-weighted average otherwise."""
        sm = self.supply_module
        sm.yani_price_ratio_m = ratio_m
        # each member state's models see their market's prices; the EU average (production-weighted) for reporting
        bmap = self.market_module._ms_block_map() if getattr(self.market_module, "eu_blocks", False) else {}
        sm.yani_price_ratio_ms = {ms: ratio_m[rg] for ms, rg in bmap.items() if rg in ratio_m} if bmap else None
        # Norway's models: Norway's young-animal market (CAPRI yaniMarket_ per RM; K56)
        _smap = getattr(self.market_module, "SUP_NONEU_MS", {}) or {}
        _sms = {_smap[rg]: ratio_m[rg] for rg in _smap if rg in ratio_m}
        if _sms:
            sm.yani_price_ratio_ms = {**(sm.yani_price_ratio_ms or {}), **_sms}
        ratio = {}
        eu_markets = [m_ for m_ in markets if m_ not in _smap]
        for g in sorted({g for (_m, g) in ref}):
            # the EU's young-animal prices (its regions without a member-state entry above): EU markets only
            w = [(max(prod.get((m_, g), 0.0), 0.0), ratio_m.get(m_, {}).get(g, 1.0)) for m_ in eu_markets]
            if not w:
                continue
            ws = sum(x for x, _ in w)
            ratio[g] = sum(x * r_ for x, r_ in w) / ws if ws > 0 else float(np.mean([r_ for _, r_ in w]))
        sm.yani_price_ratio = ratio
        self._yani_detail = {f"{mr}|{g}": (round(float(ratio_m.get(mr, {}).get(g, 1.0)), 4),
                                            round(float(net.get((mr, g), 0.0) - ref[(mr, g)]), 2),
                                            round(float(prod.get((mr, g), 0.0)), 2))
                             for (mr, g) in ref}
        self._yani_trace.append({"ratio": dict(ratio), "imbalance": self._yani_imbalance, "markets": self._yani_detail})
        if self.verbose or getattr(self, "trace_outer", False):
            print("    [Young animals] imbalance %.4f | (ratio, net - ref, production) %s" % (
                self._yani_imbalance, self._yani_detail), flush=True)
