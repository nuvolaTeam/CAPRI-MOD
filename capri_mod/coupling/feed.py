"""Feed between the supply models and the market: the bulk feed price ratios, the rations' update, the market's feed demand from the supply models.

CAPRIModel's methods, moved unchanged from capri_mod/model.py (refactor stage 4a,
docs/design/ARCHITECTURE_REFACTOR.md); the module-level names they use are model's, given to this
module once model is loaded (capri_mod.coupling.inject); the annotations are not evaluated.
"""
from __future__ import annotations


class FeedBlock:
    def feed_bulk_price_ratios(self, price_signal) -> dict:
        """{(member state, bulk): price relative to the base} of CAPRI's feed bulks (feedBlkPrice_) at the EU
        price changes of the price signal (MarketModule.feed_bulk_price_ratio)."""
        mm = self.market_module
        sig = price_signal if price_signal is not None else {}
        ratio = {c: 1.0 + float(sig.get(c, 0.0)) for c in mm.commodities} if hasattr(sig, "get") else {}
        # EU trade blocks: the member state's block prices (EU signal + the block's departure)
        _dev = (getattr(self, "_eu_dev", None) or {}) if (getattr(mm, "eu_blocks", False) and price_signal is not None) else {}
        rr = {rg: {c: v + float(d.get(c, 0.0)) for c, v in ratio.items()} for rg, d in _dev.items()}
        _fb = mm._feed_bulk_params()
        out = {k: mm.feed_bulk_price_ratio(k[0], k[1], rr.get(mm.eu_region_of_ms(k[0]), ratio))
               for k in (_fb.get("bulks") or {})}
        # Norway's supply models: its own bulks at its own market's prices (the EU signal plus Norway's departure;
        # K56)
        _sd = (getattr(self, "_sup_dev", None) or {}) if price_signal is not None else {}
        _ms_reg = {v: k for k, v in (getattr(mm, "SUP_NONEU_MS", {}) or {}).items()}
        for k in (_fb.get("bulks_sup") or {}):
            d_ = _sd.get(_ms_reg.get(k[0]))
            rs = {c: v + float(d_.get(c, 0.0)) for c, v in ratio.items()} if d_ is not None else ratio
            out[k] = mm.feed_bulk_price_ratio(k[0], k[1], rs)
        return out

    def _update_rations(self, price_signal) -> None:
        """CAPRI's rations and the current feed prices for the feeding block inside the regional models (the ration is
        chosen there), and the ration state (feed per head of the last regional solution) for the market's feed
        index. Cereals and protein-rich feed: the member state's CAPRI bulk price indices (feedBlkPrice_); home-grown
        fodder through its balance; feeds without a market at base value."""
        from capri_mod.feed.ration import ration_model_for, rations_by_region, feed_prices_by_region
        rm = getattr(self, "_ration_model", None)
        if rm is None:
            rm = ration_model_for(self.data, self.data_dir if hasattr(self, "data_dir") else None,
                                  getattr(self.supply_module, "pmp_source", "capri2030"),
                                  getattr(self.supply_module, "pmp_capri_parts", ()))
            self._ration_model = rm
        # FEED BULK PRICES per member state (CAPRI feedBlkPrice_): the CES price index of the member state's
        # cereals (FCER) and protein-rich feed (FPRO, with cakes, DDGS, pulses, oils, milling by-products)
        bix = self.feed_bulk_price_ratios(price_signal)
        self.supply_module.feed_bulk_ratio = bix
        state = {}
        newprev = {}
        _last = getattr(self, "_last_supply_results", None) or {}
        # FEEDING INSIDE THE SUPPLY MODELS (CAPRI: v_feedInpCoeff is chosen only there, together with herds and
        # fodder): no ration is chosen outside them. The ration state is the feed per head of each region's last
        # regional solution (base ration before the first), kept for what reads it: the market's feed index where a
        # region returned no feed.
        for (reg, act), r in rm.rations.items():
            _res = _last.get(reg) if (price_signal is not None and hasattr(_last, "get")) else None
            _ft = (getattr(_res, "feed_t", None) or {}).get(act) if _res is not None else None
            _acts = getattr(_res, "activities", None) if _res is not None else None
            _h = float(_acts.get(act, 0.0)) if _acts is not None else 0.0
            if _ft and _h > 0:
                x = np.array([float(_ft.get(f_, 0.0)) / _h for f_ in r.feeds])
            else:
                x = np.array(r.x0, dtype=float)
            newprev[(reg, act)] = x
            state.setdefault(reg, {})[act] = {"x": dict(zip(r.feeds, x)), "dcost": 0.0,
                                              "nitr_kg": 0.0, "nitr_share": 0.0}
        self.supply_module.ration_state = state
        # rations and CURRENT feed prices for feeding inside the supply model
        # the per-region rations dicts are built ONCE per ration model and reused, so the
        # feed-in-supply block cache (keyed on the dict's identity) hits; only prices change
        if getattr(self, "_feed_rations_for", None) is not rm:
            self._feed_rations_stable = rations_by_region(rm)
            self._feed_rations_for = rm
        _fp = feed_prices_by_region(rm, bix)
        self.supply_module.feed_rations = self._feed_rations_stable
        self.supply_module.feed_prices = _fp
        self._ration_state = state
        self._ration_prev = newprev

    def _set_feed_demand(self, supply_results) -> None:
        """Pass EU feed use (current and base) to the market.

        The market module never referred to animals: feed demand was a fixed
        part of each cereal's demand curve, so when herds shrank the market did
        not see the feed they no longer ate (Farm-to-Fork: pigs -15%, cereal
        prices +13% against CAPRI's +8%). Feed use = sum over regions and
        animals of heads x feed per head (t/head, livestock_feed_coef.csv; the ration where feeding is in the supply
        models);
        base use from each regional model's own base levels, so the base year
        cannot move. Broilers are counted per census place (4.35 birds a year).
        """
        mm = self.market_module
        try:
            if not supply_results:
                mm.seen.feed_bulk_index = None
                return
            from capri_mod.data.definitions import ANIMALS
            # feed bulks per member state (CAPRI v_feedBlk): cereals FCER and protein-rich feed FPRO, now and base
            blk = {}
            fmil = [0.0, 0.0]                       # feed from milk products (FMIL): now, base (the EU's)
            fmil_sup = {}                           # the same for Norway's dairy block (own market region, K56)
            _sup_of = getattr(mm, "sup_region_of_country", lambda c: None)
            for region, res in supply_results.items():
                ms = self.member_state_of(region)
                _srg = _sup_of(region)
                _fm = fmil if _srg is None else fmil_sup.setdefault(_srg, [0.0, 0.0])
                bc = blk.setdefault((ms, "FCER"), [0.0, 0.0])
                bpr = blk.setdefault((ms, "FPRO"), [0.0, 0.0])
                mo = getattr(self.supply_module, "_models", {}).get(region)
                b0 = mo._base_levels() if mo is not None else None
                fc = getattr(mo.data, "livestock_feed_coef", None) if mo is not None else None
                for a in ANIMALS:
                    x = float(res.activities.get(a, 0.0))
                    x0 = float(b0.get(a, 0.0)) if b0 is not None else x
                    q = float(fc.get(f"{a}_cereals", float("nan"))) if fc is not None else float("nan")
                    qp = float(fc.get(f"{a}_protein", float("nan"))) if fc is not None else float("nan")
                    # with the EU ration wired in: current cereals and protein
                    # feed per head from the ration; base from the base ration
                    _rr = ((getattr(self, "_ration_state", None) or {}).get(region) or {}).get(a)
                    _r0 = getattr(self, "_ration_model", None)
                    if _rr and _r0 is not None and (region, a) in _r0.rations:
                        _rb = _r0.rations[(region, a)]
                        xb = dict(zip(_rb.feeds, _rb.x0))
                        # feeding inside the supply model: the region's own feed totals (t)
                        _ft = (getattr(res, "feed_t", None) or {}).get(a)
                        # every tradable bulk of CAPRI (FEED_TRD: FCER, FPRO, FENE, FOTH, FMIL; Sprint 9h adds the
                        # last three per member state)
                        for _b in self.FEED_BULKS:
                            if _b in xb:
                                _acc = blk.setdefault((ms, _b), [0.0, 0.0])
                                _acc[0] += (_ft.get(_b, 0.0) if _ft is not None else x * _rr["x"].get(_b, 0.0)) / 1000.0
                                _acc[1] += x0 * xb[_b] / 1000.0
                        if "FMIL" in xb:              # feed from milk products (calves; CAPRI FMIL)
                            _fm[0] += (_ft.get("FMIL", 0.0) if _ft is not None else x * _rr["x"].get("FMIL", 0.0)) / 1000.0
                            _fm[1] += x0 * xb["FMIL"] / 1000.0
                        continue
                    if qp == qp:                    # protein-rich feed, t per head
                        bpr[0] += x * qp
                        bpr[1] += x0 * qp
                    if q == q:                      # CAPRI total / our herd, t per head
                        bc[0] += x * q
                        bc[1] += x0 * q
                    # (no coefficient: no herd of the animal in the region at base in CAPRI, so no feed; the national
                    # feed table that stood here as a fallback had no builder and was removed, KNOWN_ISSUES K99)
            # CAPRI's market splits each member state's bulks into products (feedShareEqu_,
            # MarketModule.eu_feed_use); the market gets each bulk's change against the base
            mm.seen.feed_bulk_index = {k: (v[0] / v[1] if v[1] > 0 else 1.0) for k, v in blk.items()}
            # the bulks at base (kt): the market's bulk demand (feedBlk_, audit M4) turns the measured responses into
            # elasticities with them
            mm.seen.feed_bulk_base = {k: float(v[1]) for k, v in blk.items()}
            # DAIRY PRODUCTS FED (dairy Stage 3): the FMIL block follows the calves' milk feed, as CAPRI's
            # feed block FMIL (SMIP, WMIO, CASE, WHEP, BUTT, CREM, COCM, CHES, FRMI) follows the supply models
            mm.seen.fmil_index = (fmil[0] / fmil[1]) if fmil[1] > 0 else 1.0
            mm.seen.fmil_index_sup = {rg: (v[0] / v[1] if v[1] > 0 else 1.0) for rg, v in fmil_sup.items()}
        except Exception:
            mm.seen.feed_bulk_index = None
