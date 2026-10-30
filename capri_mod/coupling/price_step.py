"""The outer loop's price step and stop rule as CAPRI's (capmod/price_forecast.gms, the stop test).

CAPRIModel's methods, moved unchanged from capri_mod/model.py (refactor stage 4a,
docs/design/ARCHITECTURE_REFACTOR.md); the module-level names they use are model's, given to this
module once model is loaded (capri_mod.coupling.inject); the annotations are not evaluated.
"""
from __future__ import annotations


class PriceStepBlock:
    def _capri_stop_step(self, supply_results, market_eq) -> Optional[dict]:
        """One step of CAPRI's stop rule (capri_mod.utils.capri_stop.CapriStopRule; capmod/price_forecast.gms): the
        step's production, feed use and market prices per member state. Items, as CAPRI's where the model has them:
        - production: the supply models' output bridged to the market's products per member state (kt), CAPRI's
          grof of the outputs at member-state level;
        - feed: the traded feed bulks (FCER, FPRO, FENE, FMIL, FOTH; CAPRI's FEED rows without straw and the
          non-traded fodder FODDIS, which it sets to zero) per member state, kt;
        - prices: the market's solution of the step (CAPRI's UVAG before the price forecast): the domestic prices of
          the member state's market region (EU27 or its trade block; Norway's own), EUR/t; raw milk per member state:
          the EU's raw milk price x its dairy block's price relative to the EU's (the member states' own base milk
          price levels are not at hand: they matter only for the aggregate's weights and the EUR 0.05 filter); young
          animals as the market's price ratios (no price level at hand, so CAPRI's EUR 0.05 filter is not applied to
          them; they are out of the step's maximum as in CAPRI). Departures: one price per market region for every
          member state in it, where CAPRI has each member state's price; the aggregates are CAPRI's trade blocks EU_West and EU_East
          (capri_data/shared/eu_market_blocks.csv) - EU015000 and WBA, also in CAPRI's REGAGGU, are not used.
        Returns the step's verdict, or None when the items cannot be formed."""
        from capri_mod.data.definitions import capri_ms
        from capri_mod.utils.capri_stop import CapriStopRule
        if not supply_results:
            return None
        if getattr(self, "_capri_stop", None) is None:
            blocks = read_input(Path(getattr(self, "data_dir", None) or Path(__file__).resolve().parents[2] / "capri_data") / "shared" / "eu_market_blocks.csv")
            aggs = {b: list(g["ms"]) for b, g in blocks.groupby("block")}
            self._capri_stop = CapriStopRule(aggs, yani_rows=(), no_abs_price_rows=())
        rule = self._capri_stop
        # production per member state (kt)
        q = self._bridge_supply_to_market(self.supply_module.aggregate_supply(supply_results, by_country=True)).fillna(0.0)
        prod = {}
        for cc, row in q.iterrows():
            d = prod.setdefault(capri_ms(cc), {})
            for c, v in row.items():
                if float(v) > 0:
                    d[str(c)] = d.get(str(c), 0.0) + float(v)
        # feed use per member state (kt): the traded feed bulks
        traded = ("FCER", "FPRO", "FENE", "FMIL", "FOTH")
        feed = {}
        for r_, res in supply_results.items():
            ft = getattr(res, "feed_t", None) or {}
            d = feed.setdefault(capri_ms(r_), {})
            for _a, bulks in ft.items():
                for b_, t_ in (bulks or {}).items():
                    if b_ in traded:
                        d[b_] = d.get(b_, 0.0) + float(t_) / 1000.0
        # the market's prices per member state (EUR/t, young animals as ratios): its domestic prices of the step
        # (the member state's trade block, or Norway's market), raw milk per member state from its dairy block
        dp = getattr(market_eq, "domestic_prices", None) if market_eq is not None else None
        if dp is None or not len(dp):
            return None
        _mmk = self.market_module
        bmap = _mmk._ms_block_map() if getattr(_mmk, "eu_blocks", False) else {}
        _smap = getattr(_mmk, "SUP_NONEU_MS", {}) or {}
        ms_reg = {capri_ms(v): k for k, v in _smap.items()}            # Norway's market region
        eu_reg = [r_ for r_ in _mmk.EU if r_ in dp.index]
        price = {}
        for ms in prod:
            rg = ms_reg.get(ms) or bmap.get(ms) or (eu_reg[0] if len(eu_reg) == 1 else None)
            if rg is None or rg not in dp.index:
                continue
            price[ms] = {str(c): float(v) for c, v in dp.loc[rg].items() if v == v and float(v) > 0}
        _dl = _mmk.ev.dairy_last or {}
        _eu = float((_dl.get("price_ratio") or {}).get("MILK", 0.0) or 0.0)
        if _eu > 0:
            for ms, v in (_dl.get("ms_price_ratio") or {}).items():
                if ms in price and "MILK" in price[ms]:
                    price[ms]["MILK"] = price[ms]["MILK"] * float(v["MILK"]) / _eu
        ya = self.market_module.ev.yani_market_now or {}
        yrows = set()
        # a supply-model country outside the EU takes its own market region's young-animal prices (Norway: NOR); the
        # EU's member states, those of the EU's market regions (the run's, definitions.sup_noneu)
        _sup_mr = {ms_: tr_ for ms_, (_c, tr_) in sup_noneu().items()}
        _sup_regions = set(_sup_mr.values())
        for mr, d in ya.items():
            for g, rt in d.items():
                yrows.add("YANI:" + g)
                for ms in price:
                    if (mr == _sup_mr[ms]) if ms in _sup_mr else (mr not in _sup_regions):
                        price[ms]["YANI:" + g] = float(rt)
        rule.yani_rows |= yrows
        rule.no_abs_price_rows |= yrows
        return rule.record(prod, feed, price)

    @staticmethod
    def _capri_price_update() -> bool:
        """outer_loop.price_update = "capri": every price passed to the supply models is CAPRI's price forecast
        (capmod/define_stepWeights.gms, price_forecast.gms l. 376-397) instead of the adaptive step."""
        return str(_settings().get("outer_loop.price_update")) == "capri"

    @staticmethod
    def _capri_forecast(hist, outer_iter):
        """CAPRI's price forecast: the weighted average of the market's prices of the last steps, newest last in
        hist; 0.55 / 0.30 / 0.15, from the 20th step 0.4 / 0.3 / 0.2 / 0.1 (define_stepWeights.gms), normalised over
        the steps available. Works on floats and on pandas Series alike."""
        st = _settings()
        w = tuple(st.get("outer_loop.capri_step_weights")
                  if outer_iter + 1 < int(st.get("outer_loop.capri_step_weights_late_from"))
                  else st.get("outer_loop.capri_step_weights_late"))
        use = list(reversed(hist))[:len(w)]
        tot = sum(w[:len(use)])
        out = None
        for w_, v_ in zip(w, use):
            out = w_ * v_ if out is None else out + w_ * v_
        return out / tot

    @staticmethod
    def _capri_special_forecast(hist, srt):
        """CAPRI's slower smoothing for a problem product (define_stepWeights.gms l. 41-50, price_forecast.gms
        l. 384-386): at step k the weight of step j is max(0, 1 - srt (k + 1 - j)) for j = 0 (TRD, the baseline: signal
        0) to k, normalised; hist holds the market's prices of steps 1..k, newest last (floats or Series)."""
        k = len(hist)
        vals = [0.0 * hist[0]] + list(hist)
        w = [max(0.0, 1.0 - float(srt) * (k + 1 - j)) for j in range(k + 1)]
        tot = sum(w)
        out = None
        for w_, v_ in zip(w, vals):
            out = w_ * v_ if out is None else out + w_ * v_
        return out / tot

    @staticmethod
    def _capri_step_special() -> dict:
        """outer_loop.capri_step_special as {(member state, product): srt}, as CAPRI's p_stepWgtSpecial(ms, product,
        "srt")."""
        out = {}
        for e in (_settings().get("outer_loop.capri_step_special") or []):
            rg, pr, srt = str(e[0]), str(e[1]), float(e[2])
            if not (0.0 < srt < 1.0):
                raise ValueError(f"outer_loop.capri_step_special {e!r}: srt in (0, 1)")
            if not (len(rg) == 8 and rg.endswith("000000")):
                raise ValueError(f"outer_loop.capri_step_special {e!r}: a member state as CAPRI (e.g. MT000000)")
            out[(rg, pr)] = srt
        return out
