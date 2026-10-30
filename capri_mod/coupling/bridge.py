"""Supply to market: the supply models' output aggregated to the market's commodities and regions (livestock products, dairy and processing yields, sugar per beet).

CAPRIModel's methods, moved unchanged from capri_mod/model.py (refactor stage 4a,
docs/design/ARCHITECTURE_REFACTOR.md); the module-level names they use are model's, given to this
module once model is loaded (capri_mod.coupling.inject); the annotations are not evaluated.
"""
from __future__ import annotations


class BridgeBlock:
    def _livestock_products_by_country(self, supply_results):
        """Livestock market supply by country (1000 t): each region's animal output split into CAPRI's
        final products at the region's own product composition (livestock_output_by_product_coef) -
        dairy cows into milk and cull-cow beef, sheep and goats into meat and milk, laying hens into eggs
        and poultry meat. The split is the base composition per head; output itself follows the herd and
        the intensity splits (gross_output)."""
        coef = self.data.get("livestock_output_by_product_coef") if isinstance(self.data, dict) else None
        if coef is None or not supply_results:
            return None
        from collections import defaultdict as _dd
        from capri_mod.data.definitions import REGION_TO_COUNTRY
        cols = {}
        for c in coef.columns:
            a, p = c.split(".", 1)
            if p in self.LIVESTOCK_PRODUCT_MARKET:
                cols.setdefault(a, []).append((c, self.LIVESTOCK_PRODUCT_MARKET[p]))
        rows = _dd(lambda: _dd(float))
        for r, res in supply_results.items():
            go = getattr(res, "gross_output", None)
            if go is None or r not in coef.index:
                continue
            key = REGION_TO_COUNTRY.get(r, r)
            for a, parts in cols.items():
                g = float(go.get(a, 0.0)) if a in go.index else 0.0
                if not g == g or g == 0.0:
                    continue
                v = [(float(coef.at[r, c]) if pd.notna(coef.at[r, c]) else 0.0, m) for c, m in parts]
                tot = sum(x for x, _ in v)
                if tot > 0:
                    for x, m in v:
                        rows[key][m] += g * x / tot
        return pd.DataFrame({k: dict(v) for k, v in rows.items()}).T.fillna(0.0) if rows else None

    def _bridge_supply_to_market(
        self,
        supply_agg: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Map supply module activity gross outputs (crops/animals) to
        market module commodity definitions.

        Some activities produce multiple commodities (e.g. oilseeds → oil + meal).
        Animals produce meat, milk, eggs.
        """
        from capri_mod.data.definitions import MARKET_COMMODITIES

        market_supply = pd.DataFrame(0.0,
                                      index=supply_agg.index,
                                      columns=MARKET_COMMODITIES)

        # Direct mappings (activity → market commodity)
        direct_maps = {
            "BARL": "BARL",
            "CORN": "CORN", "OCER": "OCER", "RYEM": "RYEM", "OATS": "OATS", "RAPE": "RAPE",
            "SUNF": "SUNF", "SOYA": "SOYA",
            "POTA": "POTA", "PULS": "PULS",
            "TOMA": "TOMA", "OVEG": "OVEG", "APPL": "APPL",
            "OFRU": "OFRU", "CITR": "CITR", "TAGR": "TAGR", "TOBA": "TOBA", "TABO": "TABO", "TEXT": "TEXT", "WINE": "WINE",
            # (wheat, olives and paddy rice are bridged below, as CAPRI's wheat, olive oil and milled rice)
        }
        # LIVESTOCK (milk is handled by the dairy block below). The meat markets
        # meat, milk and egg supply never moved with the herds: under
        # Farm-to-Fork pig supply fell ~10% while the pork price changed by
        # exactly 0.0% (CAPRI: +43%). Each product is the sum of the
        # activities producing it, from their marketed gross output.
        # The model's own animal codes (definitions.ANIMALS): BCOW suckler cows,
        # HFRS heifers, PIGF a second pig activity, SHGM / SHGF sheep and goats. An
        # earlier version of this map used HEIF/SCOW/SOWS/SHEP/GOAT, which do not
        # exist here, so beef came from bulls and calves only, pork from one pig
        # activity of two, and sheep and goat meat got nothing.
        livestock_maps = {
            "BEEF": ("BULL", "BCOW", "HFRS", "CALV"),
            "PORK": ("PIGS", "PIGF"),
            "POUL": ("BROI",),
            "EGGS": ("LAYS",),
            "SGMT": ("SHGM", "SHGF"),
        }
        # (Oil and cake supply now comes from crushing inside the market.)
        _lsc = getattr(self, "_ls_by_country", None)
        for mcomm, acts in livestock_maps.items():
            present = [a for a in acts if a in supply_agg.columns]
            if _lsc is not None and mcomm in _lsc.columns and mcomm in market_supply.columns:
                market_supply[mcomm] = _lsc[mcomm].reindex(market_supply.index).fillna(0.0)
            elif present and mcomm in market_supply.columns:
                market_supply[mcomm] = supply_agg[present].sum(axis=1)

        for act, mcomm in direct_maps.items():
            if act in supply_agg.columns and mcomm in market_supply.columns:
                market_supply[mcomm] = supply_agg[act]
        # wheat: CAPRI's market product is wheat (WHEA = soft + durum); durum's price follows it
        if "SWHE" in market_supply.columns:
            market_supply["SWHE"] = sum(supply_agg[a] for a in ("SWHE", "DWHE") if a in supply_agg.columns)
        # olives and paddy rice reach the market as CAPRI's olive oil and milled rice (processing_yields.csv)
        for act, mc in (("OLIV", "OLIV"), ("PARI", "PARI")):
            if act in supply_agg.columns and mc in market_supply.columns:
                market_supply[mc] = supply_agg[act] * pd.Series(
                    {r: self._processing_yield(r, act) for r in supply_agg.index}).reindex(supply_agg.index)
        # rye (RYEM) and oats (OATS) are markets of their own, as in CAPRI (arm/arm_sets.gms CERE_DEF)

        # Oilseeds: the seeds go to the seed markets; oil and cake come from crushing in the market.
        # The market commodities RAPE and SUNF are the SEEDS: they carry seed
        # world prices, and EU demand for them is calibrated to FAO seed use,
        # crushing included (CAPRI's 2030 reference: rapeseed production 22.4
        # Mt, of which 27.6 Mt processed with imports). The seed quantity used to
        # be multiplied by the OIL extraction yield (0.42) and passed to the seed
        # market, so the market saw EU rapeseed at 7.4 Mt and sunflower at 4.1
        # instead of ~19 and ~10. Percentage changes survived the constant
        # factor, which is why it went unnoticed; the EU's weight in world
        # oilseed markets did not.
        if "RAPE" in supply_agg.columns:
            market_supply["RAPE"] = supply_agg["RAPE"]
        if "SUNF" in supply_agg.columns:
            market_supply["SUNF"] = supply_agg["SUNF"]
        if "SOYA" in supply_agg.columns:
            market_supply["SOYA"] = supply_agg["SOYA"]

        # Sugar beet -> white sugar in the member state (CAPRI: MAPR(SUGA) = PRCY x PRCM(SUGB), 96% of the EU
        # harvest processed): sugar per tonne of beet harvested from CAPRI's 2030 reference, per member state
        # (tools/build/build_sugar_processing.py). Beet has no market of its own; its price follows the sugar price.
        if "SUGB" in supply_agg.columns and "SUGR" in market_supply.columns:
            market_supply["SUGR"] = supply_agg["SUGB"] * pd.Series(
                {r: self._sugar_per_beet(r) for r in supply_agg.index}).reindex(supply_agg.index)

        # Dairy: DCOW gross output -> milk tonnes via a calibrated factor, then
        # split into products with real FAO ratios. DCOW gross_output is already
        # a (per-animal, non-tonne) unit, so a single calibrated factor maps it
        # to base milk production; re-multiplying by a raw milk yield here would
        # double-convert (it inflated milk ~1.3x and all dairy products with it).
        if "DCOW" in supply_agg.columns:
            # raw milk = cow milk COMI + sheep and goat milk SGMI by CAPRI's product split of each
            # animal's output (livestock_output_by_product_coef); the old route took dairy-cow output
            # x 0.9575 and left sheep and goat milk in the sheep-meat market (that stand-in, never reached, removed
            # 23 October 2026: without the product split the run stops)
            if _lsc is None or "MILK" not in _lsc.columns:
                raise ValueError("raw milk needs CAPRI's product split of the animals' output "
                                 "(livestock_output_by_product_coef.csv)")
            milk = _lsc["MILK"].reindex(market_supply.index).fillna(0.0)
            if "MILK" in market_supply.columns:
                market_supply["MILK"] = milk
            # dairy products at CAPRI's own member-state yields of its 2030 reference (output less
            # processing, per tonne of raw milk produced: dairy_processing.csv), replacing FAO EU-average
            # ratios (cheese 0.0456 against CAPRI's 0.068). With the dairy block on, the market replaces
            # these by the block's output.
            for mc, ck in (("BUTR", "BUTT"), ("SKIM", "SMIP"), ("CHES", "CHES"), ("WHEY", "WHEP"), ("FRMI", "FRMI"),
                           ("CREM", "CREM"), ("COCM", "COCM"), ("WMIO", "WMIO"), ("CASE", "CASE")):
                if mc in market_supply.columns:
                    market_supply[mc] = milk * pd.Series(
                        {r: self._dairy_yield(r, ck) for r in market_supply.index}).reindex(market_supply.index)

        # Beef: from cattle activities. Head counts must be converted to carcass
        # tonnage — previously heads were equated directly to BEEF tonnes, which
        # inflated EU beef supply ~300x and drove market non-convergence. The
        # per-head factor is calibrated so the bridge reproduces base production
        # (EU average carcass yield over the whole cattle herd, incl. cows/calves).
        # (An older meat-and-eggs block stood here. Its codes were right, but it
        # scaled each product by an arbitrary "market slot" factor (pork x
        # 0.00004116),
        # so near-zero values reached the market, which then kept its own fixed
        # base: meat prices never moved with the herds in any scenario. It also
        # silently overwrote the livestock mapping above. Removed; dairy, which
        # maps correctly, is kept as it was.)

        return market_supply

    def _dairy_yield(self, region: str, product: str) -> float:
        """A dairy product's output less processing per tonne of raw milk (cow + sheep and goat) in the
        region's member state, CAPRI 2030 reference (dairy_processing.csv; Norway: dairy_world_processing.csv, per
        tonne of raw milk delivered); EU ratio where CAPRI has no dairy data for the member state."""
        tab = getattr(self, "_dairy_yield_cache", None)
        if tab is None:
            from pathlib import Path
            from capri_mod.data.loaders import resolve_data_file
            base = Path(getattr(self, "data_dir", None) or Path(__file__).resolve().parents[2] / "capri_data")
            f = resolve_data_file(base, "dairy_processing.csv")
            dp = read_input(f)
            net = (dp["q_kt"].fillna(0.0) - dp["proc_kt"].fillna(0.0))
            dp = dp.assign(net=net)
            raw = dp[dp["item"].isin(["COMI", "SGMI"])].groupby("ms")["q_kt"].sum()
            tab = {}
            for k in ("BUTT", "SMIP", "CHES", "WHEP", "FRMI", "CREM", "COCM", "WMIO", "CASE"):
                q = dp[dp["item"] == k].set_index("ms")["net"]
                tab.update({(ms, k): float(q.get(ms, 0.0)) / float(raw[ms]) for ms in raw.index if raw[ms] > 0})
                tab[("_EU", k)] = float(q.sum()) / float(raw.sum())
            # Norway's dairies (its own market region since K56: CAPRI's NO000000 block, dairy_world_processing.csv):
            # output less processing per tonne of raw milk delivered (MILK), CAPRI 2030 reference
            fw = resolve_data_file(base, "dairy_world_processing.csv")
            if fw.exists():
                wp_ = read_input(fw)
                for ms in ("NO000000",):
                    g = wp_[wp_["rms"] == ms].set_index("item")
                    if "MILK" in g.index and float(g.at["MILK", "q_kt"]) > 0:
                        for k in ("BUTT", "SMIP", "CHES", "WHEP", "FRMI", "CREM", "COCM", "WMIO", "CASE"):
                            if k in g.index:
                                tab[(ms, k)] = float(g.at[k, "q_kt"] - (g.at[k, "proc_kt"] if pd.notna(g.at[k, "proc_kt"])
                                                                       else 0.0)) / float(g.at["MILK", "q_kt"])
            self._dairy_yield_cache = tab
        ms = self._CAPRI_MS.get(str(region)[:2], str(region)[:2]) + "000000"
        return tab.get((ms, product), tab[("_EU", product)])

    def _processing_yield(self, region: str, raw: str) -> float:
        """CAPRI's olive oil per tonne of olives (member state) and milled rice per tonne of paddy (EU),
        2030 reference (processing_yields.csv)."""
        tab = getattr(self, "_proc_yield_cache", None)
        if tab is None:
            from pathlib import Path
            from capri_mod.data.loaders import resolve_data_file
            base = Path(getattr(self, "data_dir", None) or Path(__file__).resolve().parents[2] / "capri_data")
            f = resolve_data_file(base, "processing_yields.csv")
            py = read_input(f)
            tab = {(r["ms"], r["raw"]): float(r["yield"]) for _, r in py.iterrows()}
            self._proc_yield_cache = tab
        if raw == "PARI":
            return tab[("_EU", "PARI")]
        ms = self._CAPRI_MS.get(str(region)[:2], str(region)[:2]) + "000000"
        return tab.get((ms, raw), tab[("_EU", raw)])

    def _sugar_per_beet(self, region: str) -> float:
        """White sugar per tonne of sugar beet harvested in the region's member state (CAPRI 2030 reference:
        MAPR(SUGA) / GROF(SUGB)); member states without beet in CAPRI take the EU ratio."""
        tab = getattr(self, "_sugar_rate_cache", None)
        if tab is None:
            sp = self.data.get("sugar_processing")
            tab = {}
            if sp is not None and len(sp):
                eu = sp[~sp.index.isin(["UK000000", "AL000000", "BA000000", "CS000000", "MK000000", "ME000000",
                                        "KO000000", "TUR", "NO000000", "CH000000"])]
                tab = {ms: float(r["sugar_per_beet"]) for ms, r in sp.iterrows()}
                tab["_EU"] = float(eu["sugar_mapr_kt"].sum() / eu["beet_grof_kt"].sum())
            self._sugar_rate_cache = tab
        ms = self._CAPRI_MS.get(str(region)[:2], str(region)[:2]) + "000000"
        if ms in tab:
            return tab[ms]
        if "_EU" in tab:
            return tab["_EU"]
        raise RuntimeError("sugar_processing.csv missing: run tools/build/build_sugar_processing.py")
