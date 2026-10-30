"""The market supply Hessian measured on the supply models (CAPRI's simu_calibration_to_supply: price shocks, the split by member state, the pending measurements).

CAPRIModel's methods, moved unchanged from capri_mod/model.py (refactor stage 4a,
docs/design/ARCHITECTURE_REFACTOR.md); the module-level names they use are model's, given to this
module once model is loaded (capri_mod.coupling.inject); the annotations are not evaluated.
"""
from __future__ import annotations


class HessianBlock:
    def _measure_pending_hessian(self, pend) -> None:
        """The market supply Hessian of the baseline that has just run (recorded in _hessian_pending), measured from the
        state the baseline left: called at the start of the scenario run that needs it, before the scenario changes
        anything (or right after the baseline the scenario ran for itself)."""
        from capri_mod.supply.supply_module import RegionalSupplyModel as _RSMh
        _RSMh.nlp_tol = float(self.nlp_tol_final)          # the baseline's solves after its loop
        try:
            self._progress("market supply Hessian of the baseline ...")
            _t_h = time.time()
            self.market_module.par.supply_hessian = self._market_supply_hessian(pend["price_signal"], pend["supply_results"],
                                                                            pend["regions"])
            self._hessian_key = pend["key"]
            self._progress(f"market supply Hessian of the baseline: {time.time() - _t_h:.0f} s")
        except Exception as _exc:
            warnings.warn(f"market supply Hessian not built ({_exc!r}); the market keeps its own-price "
                          "anticipation", RuntimeWarning, stacklevel=2)
            self.market_module.par.supply_hessian = None
            self._hessian_key = pend["key"]
            # recorded, so a run without CAPRI's market supply function shows it in its metadata (r131)
            self.market_supply_hessian_info = {"source": "failed", "error": repr(_exc)}

    def _market_supply_hessian(self, price_signal, supply_results, regions):
        """CAPRI's calibration of the market's supply functions to the supply models (supply/calibrate_supply.gms:
        193-508), on this baseline: per product y, the supply models' price of y is raised by 1% (sugar beet with sugar,
        durum with wheat, as the price signal moves them), every regional model re-solved, outputs bridged to the market
        products per member state; H[ms][x, y] = (Q_x(shocked) - Q_x(base)) / (change of y's price relative to base).
        The base is re-solved at the end, so the models leave as they came. Cached on disk by the base solution and
        settings (CAPRI stores it per baseline, supply_elas_*.gdx). Returns {"eu": DataFrame x by y, "ms": {ms: DataFrame}}."""
        import hashlib
        from pathlib import Path as _P
        regs = regions or list(self.data["areas"].index)
        sm = self.supply_module
        pol = dict(getattr(self, "_last_spol", {}) or {})
        sig0 = price_signal.copy()

        # young animals (CAPRI xxOmYani in p_hessNQSupp, calibrate_supply.gms l. 437-458): their net balance per country
        # is a row ("YANI:<good>") and their price a column, shocked as the products' are
        from capri_mod.supply.supply_module import young_animal_table as _yat
        yani_goods = sorted({g for rec in _yat().values() for g in rec})

        def bridged(res):
            self._ls_by_country = self._livestock_products_by_country(res)
            q_ = self._bridge_supply_to_market(sm.aggregate_supply(res, by_country=True)).fillna(0.0)
            if yani_goods:
                yn = self._young_animal_net_by_country(res)
                for g in yani_goods:
                    q_["YANI:" + g] = pd.Series({cc: v.get(g, 0.0) for cc, v in yn.items()}).reindex(q_.index).fillna(0.0)
            # the supply models' feed bulks per country (kt; CAPRI calibrate_supply.gms l. 521-560: the bulks'
            # response to the prices, p_feedBlkElas of the market's feedBlk_; audit M4): rows "FEEDBLK:<bulk>"
            bk = {}
            for r_, res_ in res.items():
                cc_ = REGION_TO_COUNTRY.get(r_, r_)
                for _a, bl_ in (getattr(res_, "feed_t", None) or {}).items():
                    for b_, t_ in (bl_ or {}).items():
                        if b_ in self.FEED_BULKS:
                            bk[(cc_, b_)] = bk.get((cc_, b_), 0.0) + float(t_) / 1000.0
            for b_ in self.FEED_BULKS:
                q_["FEEDBLK:" + b_] = pd.Series({cc_: v_ for (cc_, bb_), v_ in bk.items() if bb_ == b_}
                                                ).reindex(q_.index).fillna(0.0)
            return q_
        q0 = bridged(supply_results)
        skip = bool(_settings().get("market.hessian_skip_unchanged"))
        # BEYOND CAPRI (market.hessian_method = "kkt"): the shocks' regional solutions from the KKT conditions at the
        # base solution recorded by the base re-solve (capri_regional_nlp.KKT_MODE)
        kkt = str(_settings().get("market.hessian_method")) == "kkt"
        if kkt and not skip:
            raise ValueError('market.hessian_method = "kkt" needs market.hessian_skip_unchanged = true (its base '
                             're-solve records the base points)')
        from capri_mod.supply import capri_regional_nlp as _crn_h
        cols_y = [c for c in sig0.index if c in q0.columns and float(q0[c].clip(lower=0).sum()) > 1e-6]
        cols_y += [c for c in self.MARKET_SUPPLY_FEED_COLS if c in sig0.index and c not in cols_y]
        cols_y += ["YANI:" + g for g in yani_goods]
        key_src = (repr((sorted(regs), [round(float(v), 3) for v in q0.sum(axis=0).values], list(q0.columns),
                        [round(float(v), 6) for v in sig0.values], self.MARKET_SUPPLY_SHOCK,
                        bool(getattr(self, "use_manure_market", False)), str(getattr(self, "_endotech_key", "")),
                        # the regional models' calibration (K58): a Hessian measured before the ridge fit is stale
                        "nlp",               # the supply form, when there were two (keeps the cached Hessians' keys)
                        str(getattr(self.supply_module, "pmp_source", "capri2030")),
                        tuple(getattr(self.supply_module, "pmp_capri_parts", ())), __import__(
                            "capri_mod.supply.capri_regional_nlp", fromlist=["CAL_RIDGE"]).CAL_RIDGE,
                        tuple(yani_goods),
                        # 28 October 2026 (audit S13): activities of a calibrated part without a positive own PMP term
                        # are held at their level; their price response changes, their base level does not, so the
                        # base totals above would not tell a Hessian measured before from one measured after
                        "held-without-own-term",
                        # 28 October 2026 (K79): the regional solves' jump check changes which local optimum is kept
                        ("nlp_jump_check", str(_settings().get("supply.nlp_jump_check"))),
                        # 29 October 2026 (K79): the gain the jump check needs to switch
                        ("nlp_jump_gain", str(_settings().get("supply.nlp_jump_gain"))),
                        # 29 October 2026 (K79): the warm start from the last solution as it is
                        "warm-start-last-solution",
                        # the supply models' rules that change their price response (24 October 2026: S6-S10)
                        # (the rules whose switches were removed 27 October 2026 keep their values' place, so the
                        # cached Hessians' keys stay valid)
                        tuple(str(_settings().get(k_)) if k_ else v_ for k_, v_ in (
                            ("", "capri"), ("", "True"),        # need per ha from yield as CAPRI; yield-dependent inputs
                            ("", "True"), ("supply.cap_greening", ""), ("supply.fert_slope_with_saving", ""),
                            ("", "True"), ("", "True"),         # fertiliser options' cost on purchases; catch crops
                            # 26 October 2026 (K75): the NLP form without the lagged fodder band rows
                            ("", "True"))),     # the fodder band rows, removed 27 October 2026
                        # the measurement: every shock from the baseline's state (24 October 2026)
                        "shocks-from-base",
                        # 29 October 2026 (audit M4): the feed bulks' rows recorded as well
                        "feedblk-rows")
                        # differences to the base re-solved from the same state, regions a shock does not reach not
                        # re-solved (27 October 2026, market.hessian_skip_unchanged; off: the key as before)
                        + (("base-resolved-skip-unchanged", "full-solve-state") if skip else ())
                        # 29 October 2026: the shocks' solutions from the KKT conditions (beyond CAPRI)
                        + (("kkt-step",) if kkt else ()))
                   # at a scenario's state (market.hessian_scenario_iter): its young-animal and member-state milk
                   # prices too (a baseline's key is unchanged)
                   + (repr((sorted((getattr(sm, "yani_price_ratio", None) or {}).items()),
                            sorted((k_, sorted(v_.items())) for k_, v_ in (getattr(sm, "yani_price_ratio_ms", None) or {}).items()),
                            sorted((getattr(sm, "milk_price_dev_ms", None) or {}).items())))
                      if getattr(self, "_hessian_at_scenario", False) else ""))
        key = hashlib.sha1(key_src.encode()).hexdigest()[:16]
        cdir = _P(__file__).resolve().parents[2] / ".cache" / "market_supply_hessian"
        # Parquet (binary doubles, exact by construction). The Hessians cached as CSV before 27 October 2026 were
        # converted (read to the last digit, K82, and checked equal) and are no longer read
        cfile = cdir / f"{key}.parquet"
        if cfile.exists():
            from capri_mod import run_manifest
            run_manifest.note_read(cfile)              # the cached Hessian the run uses (run manifest)
            t = pd.read_parquet(cfile)
            ms_h = {ms: g.pivot(index="x", columns="y", values="dq").fillna(0.0) for ms, g in t.groupby("ms")}
            eu, sup, blocks = self._split_hessian(ms_h)
            # "products" kept as before (the columns with a response here, the prices shocked when computed); both
            # counts named in either case (29 October 2026)
            self.market_supply_hessian_info = {"source": "cache", "file": str(cfile), "products": len(eu.columns),
                                               "prices_shocked": len(cols_y), "columns_with_response": len(eu.columns)}
            self.__dict__.setdefault("market_supply_hessian_log", []).append(dict(self.market_supply_hessian_info))
            return {"eu": eu, "ms": ms_h, "sup": sup, "blocks": blocks}
        import time as _t
        import copy as _cp
        t0 = _t.time()
        fb0 = getattr(sm, "feed_bulk_ratio", None)
        rows = []
        # every shock starts from the baseline's solution, and the models leave as they came: the regional NLPs' warm
        # starts and path state (_nlp_*) and the N-price loop's state are restored before each shock and after the
        # base re-solve. Chained warm starts let IPOPT end the base re-solve at another stationary point of the
        # non-convex problem (DE11, 24 October 2026: 12 kt off the baseline, and the next baseline from that state
        # 2% less wheat), so the scenario started from a state the baseline never had
        # the regional models' state: the warm-start fields (_nlp*) and everything else a solve leaves for the next one
        # (RegionalSupplyModel.SOLVE_STATE: the ammonia options' linearisation point, rations, splits, last solutions).
        # Until 27 October 2026 only the _nlp* fields were saved: each shock started from the state the previous shock
        # left (the ammonia options' point differed at 1e-36, rations and splits possibly more)
        def _state_key(mo_, k_):
            if not skip:                                   # the measurement as before (cached Hessians keep their keys)
                return k_.startswith("_nlp")
            return (k_.startswith("_nlp") and k_ != "_nlp_times") or k_ in getattr(type(mo_), "SOLVE_STATE", ())

        def _snapshot():
            _c = _cp.deepcopy if skip else _cp.copy
            mods = {r_: {k_: _c(v_) for k_, v_ in mo_.__dict__.items() if _state_key(mo_, k_)}
                    for r_, mo_ in sm._models.items()}
            return mods, {n_: _cp.deepcopy(sm.__dict__.get(n_)) for n_ in getattr(sm, "_PAR_STATE", ())}

        def _restore(snap):
            mods, par = snap
            for r_, d_ in mods.items():
                mo_ = sm._models.get(r_)
                if mo_ is None:
                    continue
                for k_ in [k_ for k_ in mo_.__dict__ if _state_key(mo_, k_) and k_ not in d_]:
                    del mo_.__dict__[k_]
                mo_.__dict__.update({k_: (_cp.deepcopy if skip else _cp.copy)(v_) for k_, v_ in d_.items()})
            for n_, v_ in par.items():
                if v_ is None:
                    sm.__dict__.pop(n_, None)
                else:
                    sm.__dict__[n_] = _cp.deepcopy(v_)
        _snap0 = _snapshot()
        yr0 = (getattr(sm, "yani_price_ratio", None), getattr(sm, "yani_price_ratio_ms", None),
               getattr(sm, "yani_price_ratio_m", None))
        q_ref, n_skipped, n_solved = q0, 0, 0
        verify = skip and __import__("os").environ.get("CAPRI_HESSIAN_SKIP_VERIFY", "") == "1"
        if skip:
            # the base re-solved from the baseline's state first, each region's first solve fingerprinted: a shock
            # whose first solve in a region has the same inputs (the region does not see the shocked price) would
            # repeat this base solve exactly, so the region is not re-solved and its base result is taken. The
            # differences are taken to this re-solved base: the shocks start from the same state, so a region a shock
            # does not reach contributes exactly 0 (before, the re-solve's departure from the baseline's own solution,
            # up to 0.04 kt in r161, entered every column)
            sm.feed_bulk_ratio = fb0 if fb0 is not None else self.feed_bulk_price_ratios(sig0)
            _restore(_snap0)
            sm._hess_fp, sm._hess_verify = {}, {}
            sm._hess_probe = "record"
            if kkt:
                for mo_ in sm._models.values():
                    mo_.__dict__.pop("_kkt_base", None)
                    mo_.__dict__.pop("_kkt_ipopt", None)
                _crn_h.KKT_MODE = "record"
            try:
                res_b = sm.run(price_signals=sig0, policy_scenario=pol, regions=regs, verbose=False)
            finally:
                sm._hess_probe = None
                _crn_h.KKT_MODE = None
            q_ref = bridged(res_b)
            sm._hess_base_res = res_b
        try:
            _t_h0 = time.time()
            for _k_y, y in enumerate(cols_y):
                if _k_y and _k_y % 5 == 0:
                    self._progress(f"  market supply Hessian: {_k_y}/{len(cols_y)} price shocks, "
                                   f"{time.time() - _t_h0:.0f} s; {n_skipped} of {n_solved} regional solves skipped")
                sig = sig0.copy()
                if y.startswith("YANI:"):
                    # a young animal's price raised by the shock in every regional model (EU and Norway), the products'
                    # prices at the base
                    # (relative to its current price: 1 at a baseline, the scenario's at a scenario's state; Norway's models
                    # their own market's)
                    g_ = y[5:]
                    eu0 = {g: 1.0 for g in yani_goods}
                    eu0.update({g: float(v) for g, v in (yr0[0] or {}).items()})
                    dr = self.MARKET_SUPPLY_SHOCK * eu0.get(g_, 1.0)
                    sm.yani_price_ratio = {**eu0, g_: eu0.get(g_, 1.0) + dr}
                    if yr0[1]:
                        sm.yani_price_ratio_ms = {ms_: {**dict(d_), g_: float(dict(d_).get(g_, 1.0)) * (1.0 + self.MARKET_SUPPLY_SHOCK)}
                                                  for ms_, d_ in yr0[1].items()}
                        dr_ms = {ms_: self.MARKET_SUPPLY_SHOCK * float(dict(d_).get(g_, 1.0)) for ms_, d_ in yr0[1].items()}
                    else:
                        sm.yani_price_ratio_ms, dr_ms = None, {}
                    sm.yani_price_ratio_m = yr0[2]
                else:
                    dr = self.MARKET_SUPPLY_SHOCK * (1.0 + float(sig0.get(y, 0.0)))
                    sig[y] = float(sig0.get(y, 0.0)) + dr
                    if y == "SUGR" and "SUGB" in sig.index:
                        sig["SUGB"] = sig["SUGR"]
                    if y == "SWHE" and "DWHE" in sig.index:
                        sig["DWHE"] = sig["SWHE"]
                    sm.yani_price_ratio, sm.yani_price_ratio_ms, sm.yani_price_ratio_m = yr0
                    dr_ms = {}
                sm.feed_bulk_ratio = self.feed_bulk_price_ratios(sig)
                _restore(_snap0)
                if skip:
                    sm._hess_probe, sm._hess_shock = ("verify" if verify else "compare"), y
                if kkt:
                    _crn_h.KKT_MODE = "apply"
                try:
                    res = sm.run(price_signals=sig, policy_scenario=pol, regions=regs, verbose=False)
                finally:
                    sm._hess_probe = None
                    _crn_h.KKT_MODE = None
                n_skipped += sum(1 for r_ in res.values() if getattr(r_, "hess_unchanged", False))
                n_solved += len(res)
                # the price change each country's models saw (Norway's young-animal prices are its own market's)
                div = pd.Series([float(dr_ms.get(capri_ms(str(cc)), dr)) for cc in q0.index], index=q0.index)
                dq = (bridged(res) - q_ref).reindex(index=q0.index, columns=q0.columns).fillna(0.0).div(div, axis=0)
                for ms in dq.index:
                    for x in dq.columns:
                        v = float(dq.at[ms, x])
                        if abs(v) > 1e-9:
                            rows.append((ms, x, y, v))
        finally:
            sm._hess_probe = None
            _crn_h.KKT_MODE = None
            sm.__dict__.pop("_hess_base_res", None)
        n_kkt_ipopt = 0
        if kkt:
            for mo_ in sm._models.values():
                n_kkt_ipopt += int(mo_.__dict__.pop("_kkt_ipopt", 0) or 0)
                mo_.__dict__.pop("_kkt_base", None)
        # back to the base: the regional models' warm starts and states as the baseline left them
        sm.yani_price_ratio, sm.yani_price_ratio_ms, sm.yani_price_ratio_m = yr0
        sm.feed_bulk_ratio = fb0 if fb0 is not None else self.feed_bulk_price_ratios(sig0)
        _restore(_snap0)
        if skip:
            dev = float((q_ref - q0).abs().max().max())          # the base re-solved first
        else:
            res = sm.run(price_signals=sig0, policy_scenario=pol, regions=regs, verbose=False)
            dev = float((bridged(res) - q0).abs().max().max())
        _restore(_snap0)
        bad = sorted(k_ for k_, v_ in (getattr(sm, "_hess_verify", None) or {}).items() if not v_)
        n_ver = len(getattr(sm, "_hess_verify", None) or {})
        sm.__dict__.pop("_hess_fp", None)
        sm.__dict__.pop("_hess_verify", None)
        self._ls_by_country = self._livestock_products_by_country(supply_results)
        t = pd.DataFrame(rows, columns=["ms", "x", "y", "dq"])
        cdir.mkdir(parents=True, exist_ok=True)
        # written whole, then renamed: another process (parallel test workers, two runs) reads a complete file or none
        import os as _os
        _tmp = cdir / f"{key}.{_os.getpid()}.tmp"
        t.to_parquet(_tmp, index=False)
        _os.replace(_tmp, cfile)
        ms_h = {ms: g.pivot(index="x", columns="y", values="dq").fillna(0.0) for ms, g in t.groupby("ms")}
        eu, sup, blocks = self._split_hessian(ms_h)
        self.market_supply_hessian_info = {"source": "computed", "file": str(cfile), "products": len(cols_y),
                                           "prices_shocked": len(cols_y), "columns_with_response": len(eu.columns),
                                           "seconds": round(_t.time() - t0, 1), "base_resolve_max_dev_kt": dev}
        if kkt:
            # the regional solves of the shocks that IPOPT made (the shock changed the problem's structure)
            self.market_supply_hessian_info.update(method="kkt", kkt_ipopt_solves=n_kkt_ipopt)
        if skip:
            self.market_supply_hessian_info.update(regions_skipped=n_skipped, regions_shocked=n_solved)
            if verify:
                # CAPRI_HESSIAN_SKIP_VERIFY=1: the regions that would have been skipped were solved; their results must
                # equal the base re-solve's (else the fingerprint misses an input of the regional solve)
                self.market_supply_hessian_info.update(verified=n_ver, verify_mismatch=bad[:20])
                if bad:
                    warnings.warn(f"market supply Hessian: {len(bad)} region solves with the base's inputs gave "
                                  f"another result, e.g. {bad[:5]}", RuntimeWarning)
        self.__dict__.setdefault("market_supply_hessian_log", []).append(dict(self.market_supply_hessian_info))
        return {"eu": eu, "ms": ms_h, "sup": sup, "blocks": blocks}

    def _split_hessian(self, ms_h):
        """The market supply Hessian per country summed for the EU, and kept per non-EU market region with supply
        models (Norway: its own market supply function, K56). Norway's shocks are the same products' prices (one
        shock per product for all models; the cross terms between Norway's and the EU's prices do not arise, as each
        market region's supply depends only on the prices its own models see)."""
        mm = self.market_module
        sup_of = getattr(mm, "sup_region_of_country", lambda c: None)
        eu = self._sum_frames([h for cc, h in ms_h.items() if sup_of(cc) is None])
        sup = {}
        for cc, h in ms_h.items():
            rg = sup_of(cc)
            if rg is not None:
                sup[rg] = h if rg not in sup else sup[rg].add(h, fill_value=0.0)
        # CAPRI's two EU trade blocks: each block's member states, summed (each member state's models see its own
        # block's prices, so the measured response is to that block's price)
        blocks = {}
        if getattr(mm, "eu_blocks", False):
            bmap = mm._ms_block_map()
            for cc, h in ms_h.items():
                if sup_of(cc) is not None:
                    continue
                b_ = bmap.get(cc) or bmap.get(capri_ms(cc))
                if b_ is None:
                    raise ValueError(f"member state {cc} has no EU trade block (eu_market_blocks.csv)")
                blocks[b_] = h if b_ not in blocks else blocks[b_].add(h, fill_value=0.0)
        return eu, sup, blocks

    @staticmethod
    def _sum_frames(frames):
        out = None
        for f_ in frames:
            out = f_.copy() if out is None else out.add(f_, fill_value=0.0)
        return out.fillna(0.0) if out is not None else pd.DataFrame()
