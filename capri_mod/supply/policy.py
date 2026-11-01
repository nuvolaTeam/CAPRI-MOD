"""Policy rules in the regional model: CAP greening and crop diversification, the organic area target and yield gaps, the pesticide reduction, the Green Deal input changes, the yield response to prices and its input costs.

RegionalSupplyModel's methods, moved unchanged from capri_mod/supply/supply_module.py (refactor stage 3a,
docs/design/ARCHITECTURE_REFACTOR.md); the module-level names they use are supply_module's, given to
this module once supply_module is loaded (capri_mod.utils.mixins.inject_names); the annotations are not evaluated
(they name supply_module's types).
"""
from __future__ import annotations


class PolicyBlock:
    def _cap_rules_spec(self):
        """CAPRI's greening rules of this region (policy/define_greening_limits.gms with
        scen/Premiums/Greening/cap_2013_2020_greening.gms; data tools/build/build_cap_greening.py):
          permGras     grassland >= its base area; its dual at calibration CAPRI's |arable rent - grassland rent|
          ecoSetAside  sum(crops but grassland) x r / (1 - r) <= sum(EFA activities x weight)  (r = 5%, efabasis
                       UAAR; weights FALL/VSET (SETA) 1, PULS 0.7, OFAR 0.7 x legume share, catch crops 0.3 where the
                       winter cover option is in the NLP; ISET 0, GSET/TSET none: CAPRI's 2017 and 2030 data have no
                       area under them, so SETA = FALL + VSET at weight 1)
          cropDiv      Shannon index of the annual crop groups >= its base value
        Where the base does not meet the ecological set-aside rule (the model's base data, not CAPRI's calibrated
        base), the rule is held at the base's own value (REGISTERED)."""
        if not getattr(type(self), "cap_greening", False):
            return None
        import pandas as _pd

        def load(inp):
            st = inp.csv("cap_greening_2013_2020.csv", "policy")
            fl = inp.csv("cap_greening_fleg_ms.csv", "policy").set_index("ms")["fleg_share"].to_dict()
            return ({(r.item, r.key): float(r.value) for r in st.itertuples(index=False)}, fl)
        st, fleg = _inputs.current().cached("cap_greening", load)
        acts = list(self.acts)
        xb = np.maximum(self._base_levels().reindex(acts).fillna(0.0).values.astype(float), 0.0)
        out = {}
        if st.get(("active", "permGras")) and "GRAS" in acts:
            j = acts.index("GRAS")
            # only where grassland has a level: below the threshold of the activity bounds (an activity without a
            # level, held at zero, _build_constraints) CAPRI has no grassland variable and no rule; with a base of
            # 3.5e-11 kha (EL63, 2030) the rule asked for grass the bounds forbid and the NLP was infeasible (K69)
            if xb[j] > ABSENT_LEVEL:
                out["permGras"] = {"row": [(j, -1.0)], "rhs": -xb[j] * (1 - 1e-9), "scale": xb[j]}
                # the rule's dual at the calibration point, CAPRI's assumption (supply/prep_cal.gms l. 118-131):
                # p_dualGreening = -|rent of arable land - rent of grassland|, charged to GRAE and GRAI in the
                # calibration's linear terms (EUR/ha; CapriRegionalNLP.calibrate fixes the row's multiplier at it)
                _r = getattr(self.data, "land_rents", None)
                if _r is not None and hasattr(_r, "get"):
                    ra, rg = _r.get("ARAC"), _r.get("GRAS")
                    if ra is not None and rg is not None and ra == ra and rg == rg:
                        out["permGras"]["cal_dual"] = abs(float(ra) - float(rg))
        if st.get(("active", "ecoSetAside")):
            r = st.get(("setaside_rate_pct", "ARAB"), 0.0) / 100.0
            ms = self.data.region_id[:2]
            ms = MS_CODE.get(ms, ms)
            ofar = 1.0
            env_ = getattr(self, "_env_for_surplus", None)
            try:
                from capri_mod.fert.npk import NPKData
                cr = env_._inner_fert.capri_region(self.data.region_id) if env_ is not None and \
                    env_.__dict__.get("_inner_fert") is not None else None
                if cr is not None:
                    ofar = float(NPKData.get().crop_shares(cr).get("OFOD", {}).get("OFAR", 1.0))
            except Exception:
                pass
            w = {"SETA": st.get(("weight", "FALL"), 0.0), "PULS": st.get(("weight", "PULS"), 0.0),
                 "OFOD": st.get(("weight", "OFAR"), 0.0) * float(fleg.get(ms, 0.0)) * ofar}
            row = []
            for j, a in enumerate(acts):
                if a in CROPS and a != "GRAS":
                    row.append((j, r / (1.0 - r) - w.get(a, 0.0)))
            v0 = sum(c_ * xb[j] for j, c_ in row)
            sc_ = max(1.0, sum(abs(c_) * xb[j] for j, c_ in row))
            # catch crops count at CAPRI's weight (setaEco includes CATC, p_DPgreeningWeight 0.3) where the NLP form
            # chooses them (the winter cover option: share m of UAAR, CapriRegionalNLP adds - w x UAAR x m to the row)
            wc = st.get(("weight", "CATC"), 0.0)
            cs_ = self._catc_spec() if wc > 0 else None
            if cs_ is not None:
                v0 -= wc * float(cs_["uaa"]) * float(cs_["m0"])
            out["ecoSetAside"] = {"row": row, "rhs": max(0.0, v0) + 1e-9 * sc_, "scale": sc_, "base_gap": v0,
                                  "catc_w": wc if cs_ is not None else 0.0}
        if st.get(("active", "cropDiv")):
            grp = {}
            for j, a in enumerate(acts):
                g = self.CROPDIV_GROUPS.get(a)
                if g is not None:
                    grp.setdefault(g, []).append((j, 1.0))
            # floors under the logs: CAPRI's 1e-10 is 1e-6 here, plus IPOPT's bound relaxation over the group's columns
            # (1e-8 per column in the NLP's scaling, max(|base level|, 1); x 10), so that no trial point within the
            # relaxed bounds takes a group to zero (K97); the same floors in the NLP's row
            fl = [1e-6 + 1e-7 * sum(w * max(abs(float(xb[j])), 1.0) for j, w in gp) for gp in grp.values()]
            X = [sum(xb[j] for j, _ in gp) + f_ for gp, f_ in zip(grp.values(), fl)]
            T = sum(X)
            if T > 0 and len(X) > 1:
                H0 = -sum(x / T * np.log(x / T) for x in X)
                # with the Biodiversity Strategy's fallow floor F, CAPRI lowers the limit to avoid infeasibility
                # (pol_input/greendeal/landscape.gms l. 75-90, as coded there: F added to every group and to the
                # annual area): H0 = min(H0, - sum_g (X_g + F)/(T + F) log((X_g + F)/(T + F)))
                F = float(getattr(self, "_fall_floor", 0.0) or 0.0)
                if F > 0:
                    H0 = min(H0, -sum((x + F) / (T + F) * np.log((x + F) / (T + F)) for x in X))
                out["cropDiv"] = {"groups": list(grp.values()), "H0": H0 * (1 - 1e-9), "floors": fl}
        return out or None

    def _organic_baseline(self) -> float:
        """EU organic share already in place (CAPRI load_organic_targets.gms: the EU target is
        0.25 - 0.10). Only a fallback: every EU member state has CAPRI's own percentage-point
        targets (organic_targets_ms.csv), which already net out its existing organic area; CAPRI
        applies them uniformly to the member state's regions. (A per-country table of 2018-2019
        Eurostat shares used here before CAPRI's targets were loaded was no longer reached for any
        EU region and has been removed.)"""
        return self.ORGANIC_BASELINE_SHARE

    def _input_cost(self, a: str, item: str, share_table: dict) -> float:
        """EUR/ha of input `item` (used for 'fert') for crop a: CAPRI's regional cost
        (tools/build/build_plant_protection_cost.py), else the EU-wide share of input cost times the
        crop's input cost (REGISTERED fallback, crops CAPRI does not grow in the region)."""
        t = getattr(self.data, "input_costs_ha", None)
        col = item + "_eur_ha"
        if t is not None:
            # the region's table as a plain dict, built once per table (scalar pandas lookups were ~10% of a run)
            memo = self.__dict__.get("_input_cost_memo")
            if memo is None or memo[0] is not t:
                memo = (t, {(r, c_): float(v) for r, row in t.to_dict("index").items() for c_, v in row.items()
                            if isinstance(v, (int, float)) and v == v})
                self._input_cost_memo = memo
            v = memo[1].get((a, col))
            if v is not None:
                return v
        c = float(self.data.variable_costs.get(a, 0.0))
        return c * float(share_table.get(a, 0.0) or 0.0) if c > 0 else 0.0

    def apply_pesticide_reduction(self, reduction: float,
                                  organic_share: Optional[float] = None, yield_loss: bool = True) -> None:
        """Apply the Farm-to-Fork pesticide target as CAPRI does (pol_input/greendeal/conventional_io.gms).

        Here: the yield loss on the conventional area of the affected crops (the jrc121368 rule; CAPRI star 3.0
        calls conventional_io.gms with the yield shock off) and the minimum catch-crop area (pesticide cut / 2, see
        _cover_crop_requirement). The plant-protection and other-input changes are regional and are set together
        with the organic target's in _apply_greendeal_input_changes.

        The loss is scaled linearly from CAPRI's 50% reference, and net revenue
        is rebuilt from the reduced yields so the price and CAP components stay
        intact. Mutates net_revenues for one solve; the caller restores it.
        """
        reduction = float(reduction)
        if reduction <= 0:
            return
        # yield_loss False: CAPRI star 3.0's Green Deal group (pesticides.gms: the yield shock 'off')
        loss = self.PESTICIDE_YIELD_LOSS_AT_50PCT * (reduction / 0.50) if yield_loss else 0.0
        # (a cap of the loss at 0.90 was removed 23 October 2026: unsourced and never reached - the loss is at most
        # 0.20, at a 100% cut)

        prices = self.data.producer_prices
        ylds = self.data.yields
        new_ylds = ylds.copy()
        nr = self.net_revenues.copy()
        # CAPRI applies the pesticide target to the CONVENTIONAL area only
        # (pol_input/greendeal/conventional_io.gms). The 50% cut is a TOTAL
        # target: organic conversion already delivers part of it, since organic
        # hectares use no plant protection, and only the REMAINING cut is made on
        # conventional land, so the overall reduction stays 50%. The yield loss
        # and the rise in other inputs likewise fall on the conventional share.
        # Applying all three to every hectare double-counted wherever organic and
        # pesticide instruments combine; it made oilseed area fall 12-13% under
        # Farm-to-Fork against the ~5% implied by CAPRI's figures.
        _targets = getattr(self.data, "organic_targets_pp", None)
        _org_default = (max(0.0, float(organic_share) - self._organic_baseline())
                        if organic_share else 0.0)
        for a in self.acts:
            if a not in self.PESTICIDE_AFFECTED:
                continue
            p = float(prices.get(a, 0.0))
            y = float(ylds.get(a, 0.0)) if hasattr(ylds, "get") else 0.0
            if p <= 0 or y <= 0:
                continue
            o = (self._organic_converted(a, organic_share, _targets, _org_default)
                 if organic_share else 0.0)
            o = min(max(o, 0.0), 0.99)
            conv = 1.0 - o
            # The yield loss must reach BOTH the objective and the reported
            # yields. It used to change net revenue only, so it steered what
            # farmers grew but left gross_output computed on unshocked yields:
            # EU cereal PRODUCTION fell 6% where CAPRI reports 15%, even though
            # our cereal AREA fell 5.9% against CAPRI's 4%. The area response
            # was never the problem; the yield effect was missing from the
            # output. CAPRI reports production, so this is what is compared.
            new_ylds[a] = y * (1.0 - loss * conv)
            nr[a] = float(nr.get(a, 0.0)) - p * y * loss * conv
        # plant protection and other inputs: CAPRI's regional input changes, set with the organic target's in
        # _apply_greendeal_input_changes (24 October 2026; before, per crop on the conventional share: KNOWN_ISSUES K74 S3/S4)
        self.data.yields = new_ylds
        self.net_revenues = nr
        self._cover_crop_requirement(float(reduction), organic_share)

    #: Yield response to a change in the crop's own price, CAPRI's: yields "updated depending on price changes
    #: against the baseline" (supply/endog_yields.gms: yield x (price / last price) ** p_yieldElas), with
    #: p_yieldElas from supply/yield_elas.gms - cereals 0.3, oilseeds 0.2, potatoes 0.2, no other crop
    #: (capri_data/2017/supply/yield_price_elasticity.csv). It was 0.15 for every crop, a literature value.
    @staticmethod
    def yield_price_elasticity() -> Dict[str, float]:
        return _inputs.current().cached("yield_price_elasticity", lambda inp: {
            r.crop: float(r.elasticity) for r in inp.csv("yield_price_elasticity.csv", "supply").itertuples()})

    def apply_yield_price_response(self, price_shock: pd.Series) -> None:
        """Let yields respond to own-price changes, as CAPRI's stage one does.

        yield_new = yield_base * (1 + price_change) ** elasticity (CAPRI's, per crop)

        At an unchanged price the factor is exactly 1.0, so the base year is
        reproduced bit-for-bit and PMP calibration is untouched -- the same
        identity that protects the nitrogen intensity margin.

        Net revenue is rebuilt from the adjusted yields, so the price effect
        enters once through quantity and once through the yield, which is what
        a two-stage decision implies. Mutates net_revenues and data.yields for
        one solve; the caller's finally block restores both.
        """
        if price_shock is None:
            return
        elas = self.yield_price_elasticity()

        prices = self.data.producer_prices
        ylds = self.data.yields
        if not hasattr(ylds, "copy"):
            return
        new_ylds = ylds.copy()
        # the price response's factor per crop: CAPRI's straw yield (and so the straw part of the nutrient need)
        # follows the scenario's yield shifts but not this response (supply/endog_yields.gms; need_yield_factor)
        pf = {}
        nr = self.net_revenues.copy()
        for a in self.acts:
            if a not in CROPS:
                continue
            dp = float(price_shock.get(a, 0.0)) if hasattr(price_shock, "get") else 0.0
            eps = float(elas.get(a, 0.0))
            if dp == 0.0 or eps <= 0:
                continue
            # a price fall below -100% is not meaningful; clamp the base
            factor = max(1.0 + dp, 0.01) ** eps
            y0 = float(ylds.get(a, 0.0))
            if y0 <= 0:
                continue
            new_ylds[a] = y0 * factor
            pf[a] = factor
            p = float(prices.get(a, 0.0)) * (1.0 + dp)
            # the extra revenue from the yield change alone
            nr[a] = float(nr.get(a, 0.0)) + p * y0 * (factor - 1.0)
        self.data.yields = new_ylds
        self.net_revenues = nr
        self._yield_price_factor = pf

    def _organic_yield_gap(self, activity: str) -> float:
        """Organic yield gap for one activity in this region, as a fraction: CAPRI's estimate for the region's PESETA
        macro-region and the product group, else the Central-European (CEN) one, as CAPRI borrows it
        (organic_area.gms l. 176-181; e.g. maize in NE and UK_IR). Before 24 October 2026 a flat 20% from the
        literature (ORGANIC_YIELD_GAP) took CEN's place."""
        table = getattr(self.data, "organic_yield_gap", None)
        _m = self.__dict__.get("_oyg_memo")                  # per table: the lookup ran ~170k times per run
        if _m is None or _m[0] is not table:
            _m = (table, {})
            self._oyg_memo = _m
        if activity in _m[1]:
            return _m[1][activity]
        _m[1][activity] = v_ = self._organic_yield_gap_uncached(activity, table)
        return v_

    def _organic_yield_gap_uncached(self, activity: str, table) -> float:
        # CAPRI's maps (inputs/load_organic_yieldgap.gms): the crop's product group (pact2yieldGap) and the member
        # state's PESETA macro-region (ms2peseta)
        group = (getattr(self.data, "organic_yield_gap_groups", None) or {}).get(activity)
        reg_id = getattr(self.data, "region_id", "") or getattr(self, "region", "")
        from capri_mod.data.definitions import capri_ms
        region = (getattr(self.data, "organic_yield_gap_regions", None) or {}).get(capri_ms(reg_id))
        if table is None or not group or region is None:
            return 0.0
        for reg_ in (region, "CEN"):
            v = table.at[reg_, group] if (reg_ in table.index and group in table.columns) else None
            if v is not None and pd.notna(v):
                return abs(float(v)) / 100.0
        return 0.0

    @staticmethod
    def _organic_target_scale(share: float) -> float:
        """CAPRI's scaling of its targets to the requested ambition, (orgTarg - 12) / (25 - 12)
        (load_organic_targets.gms l. 175, 183; orgTarg in %): exactly 1 at the 25% target."""
        return max(0.0, (100.0 * float(share) - 12.0) / (25.0 - 12.0))

    def _organic_region_target(self, share: float) -> float:
        """p_organicAreaTarget(ru): the member state's UAA target (organic_targets_uaa.gdx) scaled to the ambition.
        A region without CAPRI's targets (outside the EU) takes the EU distance-to-target fallback, as
        _organic_converted does."""
        t = getattr(self.data, "organic_targets_pp", None)
        v = t.get("uaa_pp") if (t is not None and hasattr(t, "get")) else None
        if v is None or pd.isna(v):
            return max(0.0, float(share) - self._organic_baseline())
        return max(0.0, min(1.0, float(v) / 100.0 * self._organic_target_scale(share)))

    def _organic_crop_target(self, activity: str, share: float) -> float:
        """p_organicAreaTargetCrops(ru, crop) of CAPRI's organic crops (0 for the other crops): the target of the
        crop's NGRP group (ORGANIC_CROP_TARGET). A member state with no value for the group in CAPRI's
        organic_targets.gdx gets 0, as in CAPRI (Portugal: no arable or permanent-crop entry; Ireland: no permanent,
        Malta: no grassland)."""
        col = self.ORGANIC_CROP_TARGET.get(activity)
        if col is None:
            return 0.0
        t = getattr(self.data, "organic_targets_pp", None)
        if t is None or not hasattr(t, "get"):
            return max(0.0, float(share) - self._organic_baseline())
        v = t.get(col)
        if v is None or pd.isna(v):
            return 0.0
        return max(0.0, min(1.0, float(v) / 100.0 * self._organic_target_scale(share)))

    def _input_row(self, activity: str, col: str) -> Optional[float]:
        """CAPRI's cost row of this region and activity (data.input_costs_ha, build_plant_protection_cost.py), or
        None where CAPRI has none."""
        t = getattr(self.data, "input_costs_ha", None)
        if t is None or activity not in t.index or col not in t.columns:
            return None
        v = t.at[activity, col]
        return float(v) if pd.notna(v) else None

    def _greendeal_tech_progress(self) -> float:
        """CAPRI's input-saving progress of the simulation year, TF_I = 1 - 0.005 x (Y - BAS)
        (capmod/define_inputs.gms l. 66)."""
        base = int(str(_settings().get("run.base_year")))
        sim = int(getattr(self.data, "sim_year", None) or base)
        return 1.0 - 0.005 * (sim - base)

    def _apply_greendeal_input_changes(self, organic_share: float, pesticide_reduction: float) -> None:
        """CAPRI's plant-protection (PLAP) and other-input (INPO) changes of the Green Deal organic and pesticide
        targets, in an EU region.

        CAPRI sets them as one regional percentage change per input (DATA(ru, "GROF", I, "percentageChange")) that
        define_inputs.gms l. 70-73 applies to the coefficient of EVERY activity (animals' other inputs included), and
        tops up the organic crops' other inputs:
          organic_io.gms l. 74      PLAP: -100 x o_R  (o_R the region's UAA target)
          organic_io.gms l. 111-115 INPO of each organic crop + EFUL x 2 x its crop target (the top-up)
          conventional_io.gms l. 90-275 (with organic targets) or l. 276-463 (without), when o_R < r:
                                    PLAP: -r overall (the remaining target on the conventional area plus the organic
                                    part); INPO: +otherCostChange x remaining / r = +(r - o_R), pesticides.gms passing
                                    otherCostChange = r
        r is the pesticide reduction. The scenario coefficient is (base + top-up) x (1 + change) x TF_I with
        CAPRI-ERROR-FIX greendeal_inputs_keep_tech_change, or (base + top-up) x (1 + change) without TF_I as CAPRI's
        code runs (see the setting); the baseline's is base x TF_I. The model's costs are CAPRI's 2017 coefficients
        valued at 2017 unit values (REGISTERED: CAPRI changes its simulation-year coefficients; their yield-dependent
        part follows the yields in _apply_yield_input_costs, at these changes' TF_I).
        """
        r = max(0.0, float(pesticide_reduction or 0.0))
        o_R = self._organic_region_target(organic_share) if organic_share else 0.0
        pc_plap = -o_R if o_R > 0 else 0.0
        pc_inpo = 0.0
        if r > 0 and o_R < r:
            pc_plap = -r
            pc_inpo = r - o_R
        tf = self._greendeal_tech_progress()
        keep_tf = bool(getattr(type(self), "greendeal_inputs_keep_tech_change", True))

        def delta(base: float, topup: float, pc: float) -> float:
            # change of the cost against the baseline (base x TF_I); TF_I is replaced only where CAPRI sets a change
            if pc == 0.0:
                return tf * topup
            return (base + topup) * (1.0 + pc) * (tf if keep_tf else 1.0) - base * tf

        topup_col = "eful_eur_ha" if getattr(type(self), "organic_topup_at_fuel_cost", True) else "eful_inpo_eur_ha"
        nr = self.net_revenues.copy()
        self._greendeal_inputs = {"o_R": o_R, "pc_plap": pc_plap, "pc_inpo": pc_inpo, "tf": tf, "keep_tf": keep_tf}
        for a in self.acts:
            d = 0.0
            if a in ANIMALS:
                sh = self._input_row(a, "inpo_toin_share")
                if sh is not None and pc_inpo != 0.0:
                    d = delta(sh * self._animal_cost_per_head(a), 0.0, pc_inpo)
            else:
                plap = self._input_row(a, "plap_eur_ha")
                inpo = self._input_row(a, "inpo_eur_ha")
                if plap is not None and pc_plap != 0.0:
                    d += delta(plap, 0.0, pc_plap)
                if inpo is not None:
                    o_a = self._organic_crop_target(a, organic_share) if organic_share else 0.0
                    eful = self._input_row(a, topup_col) or 0.0
                    topup = 2.0 * o_a * eful
                    if topup or pc_inpo:
                        d += delta(inpo, topup, pc_inpo)
            if d:
                nr[a] = float(nr.get(a, 0.0)) - d
        self.net_revenues = nr

    def _apply_yield_input_costs(self) -> None:
        """The crops' input costs follow their yields, as CAPRI's define_inputs.gms sets the coefficient of a directly
        yield-dependent input (sets.gms IY: seed, plant protection, repairs, energy, irrigation, other inputs,
        services) to BAS x (1 - f + f x G) x TF_I, G the yield growth since the base year (bounded 0.5-1.5) and f
        CAPRI's p_inputDemandFactor. CAPRI re-runs it after the scenario's yield shifts (capmod/shift_yields.gms) and
        after each price-driven yield update (supply/endog_yields.gms), so against the 2030 reference the cost per ha
        moves by
            sum_i f_i x cost_i x G x TF_I x (rho - 1),   rho = yield now / reference yield
        (build_plant_protection_cost.py: yd_rest, yd_plap, yd_inpo per ha; TF_I with the Green Deal changes of PLAP
        and INPO, _apply_greendeal_input_changes). Fertiliser is not in IY: it follows the crops' need
        (need_yield_factor). REGISTERED: the model's costs are CAPRI's 2017 coefficients (no yield-growth or TF_I term
        in the baseline cost); the change above is CAPRI's derivative at its 2030 reference."""
        y0s, yc = getattr(self, "_yields_solve0", None), self.data.yields
        if y0s is None or not hasattr(yc, "get") or not hasattr(y0s, "get"):
            return
        tf = self._greendeal_tech_progress()
        gi = getattr(self, "_greendeal_inputs", None) or {}
        keep = bool(gi.get("keep_tf", True))
        tf_of = lambda pc: tf if not pc else (1.0 + pc) * (tf if keep else 1.0)
        tf_p, tf_i = tf_of(float(gi.get("pc_plap", 0.0) or 0.0)), tf_of(float(gi.get("pc_inpo", 0.0) or 0.0))
        nr = None
        for a in self.acts:
            if a not in CROPS:
                continue
            y0, y = float(y0s.get(a, 0.0) or 0.0), float(yc.get(a, 0.0) or 0.0)
            if not (y0 > 0 and y > 0) or y == y0:
                continue
            k = ((self._input_row(a, "yd_rest_eur_ha") or 0.0) * tf + (self._input_row(a, "yd_plap_eur_ha") or 0.0) * tf_p
                 + (self._input_row(a, "yd_inpo_eur_ha") or 0.0) * tf_i)
            if k:
                g = self._input_row(a, "yield_growth") or 1.0
                # CAPRI's bounds on the yield growth: G x rho within 0.5-1.5
                d = (min(1.5, max(0.5, g * y / y0)) - g) / g if g > 0 else (y / y0 - 1.0)
                if nr is None:
                    nr = self.net_revenues.copy()
                nr[a] = float(nr.get(a, 0.0)) - k * d
        if nr is not None:
            self.net_revenues = nr

    def _organic_converted(self, activity: str, share: float, targets,
                           default: float) -> float:
        """Share of this activity's area that converts to organic.

        CAPRI does not move every member state to 25%. It burden-shares the EU's
        15-point shock (25% target minus 10% existing) across member states and
        crop groups: gams/pol_input/greendeal/organic_targets.gdx gives the extra
        points for arable land, permanent grassland and permanent crops, per
        member state, and those weight to exactly 15.0 points EU-wide. France
        converts 45.6% of its permanent crops, Austria 5.0%; Austria, already
        past 25%, still converts 7.5 points of UAA where a distance-to-25% rule
        gave it nothing.

        The requested share scales the ambition (0.25 = CAPRI's full target).
        Falls back to the member state's UAA-wide figure, then to the
        distance-to-target rule, where a crop group has no entry.
        """
        if targets is None:
            return default
        if activity in self.PERMANENT_LAND_CROPS:
            col = "permanent_pp"
        elif activity == "GRAS":
            col = "grassland_pp"
        else:
            col = "arable_pp"
        val = targets.get(col) if hasattr(targets, "get") else None
        if val is None or pd.isna(val):
            val = targets.get("uaa_pp") if hasattr(targets, "get") else None
        if val is None or pd.isna(val):
            return default
        # CAPRI scales its targets to the requested ambition as (orgTarg - 12) / (25 - 12)
        # (load_organic_targets.gms; orgTarg in %), exactly 1 at the 25% target
        scale = max(0.0, (100.0 * float(share) - 12.0) / (25.0 - 12.0))
        return max(0.0, min(1.0, float(val) / 100.0 * scale))

    def apply_organic_area_target(self, share: float) -> None:
        """Adjust average I/O coefficients for an organic AREA target (CAPRI pol_input/greendeal/organic_area.gms,
        organic_io.gms '100' 'off' 'off' '50').

        CAPRI does not track organic and conventional activities separately but adjusts the average coefficients of
        a region in proportion to its organic targets (p_organicAreaTarget for the region's UAA,
        p_organicAreaTargetCrops for the organic crops). Here: the organic yield gap of the organic crops
        (organic_area.gms PART III) and the fertiliser saving on converted land. Plant protection (-100% x the UAA
        target, every crop) and other inputs (the organic crops' top-up) are set in _apply_greendeal_input_changes,
        together with the pesticide target's changes, since CAPRI applies both through one regional input factor.

        Mutates net_revenues for the duration of one solve; the caller's finally block restores it.
        """
        share = float(share)
        if share <= 0:
            return

        prices = self.data.producer_prices
        ylds = self.data.yields
        new_ylds = ylds.copy()
        nr = self.net_revenues.copy()
        converted_default = max(0.0, float(share) - self._organic_baseline())
        _org = getattr(self.data, "organic_targets_pp", None)
        for a in self.acts:
            converted = self._organic_converted(a, share, _org, converted_default)
            if a not in CROPS:
                continue
            p = float(prices.get(a, 0.0))
            y = float(ylds.get(a, 0.0)) if hasattr(ylds, "get") else 0.0
            if p <= 0 or y <= 0:
                continue
            # CAPRI's organic yield gaps are FADN-based estimates by macro-region and product group (JRC Seville for
            # the SUPREMA project, loaded in organic_area.gms): e.g. Southern Europe fruits 22.5%, olives and vines
            # 11.6%; Central Europe fruits 51.3%, cereals 42.9%.
            # the organic yield gap (organic_area.gms PART III, l. 176-199): organic crops in an NGRP group with a gap
            # estimate, scaled by the crop's organic target (before 24 October 2026: every crop with a gap group,
            # grassland, fodder and other oilseeds included, at the arable / grassland / permanent target)
            # No 0.45 discount: organic_area.gms applies it only with %pest_disagg% on (an endogenous pesticide yield
            # response, v_yldPestFac), which the Farm-to-Fork set-up does not use.
            o_y = self._organic_crop_target(a, share) if a in self.ORGANIC_YIELD_GAP_CROPS else 0.0
            gap = self._organic_yield_gap(a) if o_y > 0 else 0.0
            yield_factor = 1.0 - gap * o_y
            # the fertiliser saving on converted land (its cost leaves the objective here; in the NLP form the
            # conventional share's cost is replaced by the priced purchases). Plant protection and other inputs:
            # _apply_greendeal_input_changes (CAPRI's regional changes and the organic crops' top-up)
            cost_change = -converted * self._input_cost(a, "fert", self.FERT_COST_SHARE)
            # As with the pesticide instrument, the yield gap must reach the
            # REPORTED yields too, not only the objective. CAPRI reports
            # PRODUCTION, and a yield gap that never lands in yields is
            # invisible there: EU cereal production fell 6% here against
            # CAPRI's 15%, while cereal AREA fell 5.9% against CAPRI's 4%.
            new_ylds[a] = y * yield_factor
            delta = (p * y * (yield_factor - 1.0)) - cost_change
            nr[a] = float(nr.get(a, 0.0)) + delta
            # Converted land uses NO mineral fertiliser (CAPRI's
            # organic_minfert_redu.gms). Only its COST was removed here, so in
            # the nitrogen balance and the environmental accounts organic land
            # still spread full mineral N. The mineral-N factor travels the
            # same path as the fertiliser technologies (multiplied with them).
            if converted > 0:
                self._n_intensity = getattr(self, "_n_intensity", {}) or {}
                self._n_intensity[a] = self._n_intensity.get(a, 1.0) * max(0.0, 1.0 - converted)
                # the conventional share alone, for CAPRI's minimum mineral share (NUTMIN_: 0 on organic land)
                self._organic_conv = getattr(self, "_organic_conv", {}) or {}
                self._organic_conv[a] = self._organic_conv.get(a, 1.0) * max(0.0, 1.0 - converted)
                nc_ = self.data.nutrient_coefs
                if a in nc_.index and "N" in nc_.columns:
                    nc_ = nc_.copy()
                    nc_.at[a, "N"] = float(nc_.at[a, "N"]) * max(0.0, 1.0 - converted)
                    self.data.nutrient_coefs = nc_
        self.data.yields = new_ylds
        self.net_revenues = nr
