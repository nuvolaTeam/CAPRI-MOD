"""Policy rules in the regional model: CAP greening and crop diversification, the organic area target and yield gaps, the pesticide reduction, the Green Deal input changes, the yield response to prices and its input costs.

RegionalSupplyModel's methods, moved unchanged from capri_mod/supply/supply_module.py (the refactor's split into block mixins,
docs/dev/ARCHITECTURE_REFACTOR.md); the module-level names they use are supply_module's, given to
this module once supply_module is loaded (capri_mod.utils.mixins.inject_names); the annotations are not evaluated
(they name supply_module's types).
"""
from __future__ import annotations

from capri_mod.supply import entitlements as _entl
from capri_mod.supply.equations.define_greening_limits import p_DPGreeningLimits_permGras
from capri_mod.supply.equations.define_objc import p_linObjeCont_PLAP
from capri_mod.supply.equations.greendeal.conventional_io import DATA_GROF_percentageChange, DATA_Yild, p_yildReduction
from capri_mod.supply.equations.greendeal.conventional_io import pest_change_factor_greendeal
from capri_mod.supply.equations.greendeal.organic_io import DATA_GROF_PLAP_percentageChange as _organic_plap
from capri_mod.supply.equations.greendeal.landscape import p_DPGreeningLimits_cropDiv
from capri_mod.supply.equations.greendeal.load_organic_targets import p_organicAreaTarget, p_organicTargetScale
from capri_mod.supply.equations.greendeal.organic_area import DATA_Yild_percentageChange
from capri_mod.supply.equations.greendeal.organic_io import DATA_INPO_BAS_topup
from capri_mod.supply.equations.define_inputs import TF_I_trend
from capri_mod.supply.equations.prep_cal import p_dualGreening


class PolicyBlock:
    def _entitlement_columns(self, Qa, ca, Aa, ba, start, labels, n):
        """CAPRI's endogenous entitlement limit (policy/def_endCut.gms; supply_model.gms sumEntl_, overShotEntl_,
        l. 1885-1892, and the objective's - overshoot x Cut, l. 4768; capri_mod/supply/entitlements.py): one column,
        the overshoot o >= 0 (1000 ha) at Cut EUR per ha in the objective, and one row

            sum of the crop columns (CAPRI's MCACT) + the idled histosols - o <= the region's trend area

        so a hectare beyond the trend area earns no area payment. In the simulation year of CAPRI's trend levels
        (cap14_settings.csv trend_year), where the member state has a ceiling of a cut scheme (setting
        supply.entitlement_limit). CAPRI has one overshoot per cut scheme with the same limit: their sum is this one
        column at the sum of the cuts. At the calibration point the crops are at their trend levels (CAPRI's TRD is
        its 2030 calibration level) and the row is left out of the calibration, as the scenario's policy rows: the
        overshoot is zero there and the row's multiplier too, as in CAPRI's PMP terms (prep_sim_pmp_terms.gms l. 166)."""
        self.ev.entl_col = None
        self.res.entl = None
        if not getattr(type(self), "entitlement_limit", False):
            return Qa, ca, Aa, ba, start
        sim = getattr(self.data, "sim_year", None)
        d = _entl.data()
        if sim is None or int(sim) != int(d["settings"]["trend_year"]["TRD"]):
            return Qa, ca, Aa, ba, start
        lim = _entl.region_limit(self.data.region_id, list(self.acts), int(sim))
        if lim is None:
            return Qa, ca, Aa, ba, start
        cut, limit, cols = lim

        lev = d["levels"].get(self.data.region_id) or {}
        # CAPRI's sumEntl_ and overShotEntl_ (equations/supply_model/premiums.py); iHisCr and iHisGr are CAPRI crop
        # activities (MCACT): the idled histosols keep their entitlements
        from capri_mod.supply.equations.supply_model.premiums import overShotEntl_
        _hc = getattr(self.ev, "hist_cols", None) or {}
        row = overShotEntl_(Aa.shape[1], cols, [j for _cls, j in _hc.items()])
        for cls, j in _hc.items():
            limit += float(lev.get(_entl.HISTOSOL_CODES[cls], 0.0))

        Aa = np.hstack([Aa, np.zeros((Aa.shape[0], 1))])
        Aa = np.vstack([Aa, row])
        ba = np.concatenate([ba, [limit]])
        labels.append("entitlements")
        Qa = np.pad(Qa, ((0, 1), (0, 1)))
        ca = np.concatenate([ca, [cut]])
        used = float(row[:-1] @ np.asarray(start, float)[:len(row) - 1])
        start = np.concatenate([start, [max(0.0, used - limit)]])
        self.ev.entl_col = Aa.shape[1] - 1
        self.res.entl = {"cut": cut, "limit": limit}
        return Qa, ca, Aa, ba, start

    def _entl_record(self, y) -> None:
        """The solve's entitlements (res.entl, the region's result .entitlements): the eligible area (sumEntl), the
        overshoot and the premium it loses (overshoot x Cut, 1000 EUR), and the row's dual (EUR/ha; CAPRI's
        D_sumEntl with the opposite sign, reports/margcr.gms l. 309-310)."""
        j = getattr(self.ev, "entl_col", None)
        e = getattr(self.res, "entl", None)
        if j is None or e is None or j >= len(y):
            return
        over = float(y[j])
        e.update(overshoot=over, eligible=e["limit"] + over, premium_lost=over * e["cut"])
        labels = list(getattr(self.ev, "aug_labels", None) or [])
        zA = getattr(self.ev, "last_duals", None)
        if "entitlements" in labels and zA is not None and labels.index("entitlements") < len(zA):
            e["dual"] = float(zA[labels.index("entitlements")])

    def _cap_rules_spec(self):
        """CAPRI's greening rules of this region (policy/define_greening_limits.gms with
        scen/Premiums/Greening/cap_2013_2020_greening.gms; data tools/build/build_cap_greening.py):
          permGras     grassland >= its base area; its dual at calibration CAPRI's |arable rent - grassland rent|
          ecoSetAside  sum(crops but grassland) x r / (1 - r) <= sum(EFA activities x weight)  (r = 5%, efabasis
                       UAAR; weights FALL/VSET (SETA) 1, PULS 0.7, OFAR 0.7 x legume share, catch crops 0.3 where the
                       winter cover option is in the NLP; ISET 0, GSET/TSET none: CAPRI's 2017 and 2030 data have no
                       area under them; VSET and FALL each at its own weight, 1, since 7 November 2026: before, SETA = FALL + VSET)
          cropDiv      Shannon index of the annual crop groups >= its base value
        Where the base does not meet the ecological set-aside rule (the model's base data, not CAPRI's calibrated
        base), the rule is held at the base's own value (REGISTERED).
        ecoSetAside and cropDiv with the setting supply.env_const (true, K187): CAPRI star 3.0 lists both rows without a
        condition,

                 ecoSetAside_                                       (supply/supply_model_e_list_linear.gms l. 231-232)
                 cropDivGreening_

        so its 2030 reference and Green Deal step solve with them (their marginals are in the results:
        reports/margcr.gms l. 321-326 D_cropDivGreening, reports/greening.gms); the July 2026 release lists them only
        with %envConst% on (its l. 235-236), which the Green Deal step does not set (the "$exit" of
        pol_input/greendeal/refpol_endotech_all_sup.gms l. 398 before "$setglobal envConst on", l. 408).
        permGrasGreening_ is listed always."""
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
        _gj = [acts.index(g) for g in CROPS_ON_LAND["GRAS"] if g in acts]   # GRAE, GRAI (GRAS until 7 Nov 2026)
        if st.get(("active", "permGras")) and _gj:
            # only where grassland has a level: below the threshold of the activity bounds (an activity without a
            # level, held at zero, _build_constraints) CAPRI has no grassland variable and no rule; with a base of
            # 3.5e-11 kha (EL63, 2030) the rule asked for grass the bounds forbid and the NLP was infeasible (K69)
            _xg = p_DPGreeningLimits_permGras(xb[j] for j in _gj)
            if _xg > float(_settings().get("supply.absent_level")):
                # CAPRI's GRSACT is GRAE, GRAI, IHISGR, FALLGR (sets.gms l. 2940): the idled histosol grassland counts
                # towards the rule (permGrasGreening_ sums GRSACT; ddGreen maps every MCACT, policy_sets.gms l. 2045),
                # the base limit is GRAE + GRAI (define_greening_limits.gms l. 139-140). Without it the rule held the
                # productive grass at its base and the idled area took new land (KNOWN_ISSUES K157)
                _hg = (getattr(self.ev, "hist_cols", None) or {}).get("grass")
                # CAPRI's permGrasGreening_ (equations/supply_model/premiums.py)
                from capri_mod.supply.equations.supply_model.premiums import permGrasGreening_
                out["permGras"] = permGrasGreening_(_gj, _hg, _xg)
                # the rule's dual at the calibration point, CAPRI's assumption (supply/prep_cal.gms l. 118-131):
                # p_dualGreening = -|rent of arable land - rent of grassland|, charged to GRAE and GRAI in the
                # calibration's linear terms (EUR/ha; CapriRegionalNLP.calibrate fixes the row's multiplier at it)
                _r = getattr(self.data, "land_rents", None)
                if _r is not None and hasattr(_r, "get"):
                    ra, rg = _r.get("ARAC"), _r.get("GRAS")
                    if ra is not None and rg is not None and ra == ra and rg == rg:
                        out["permGras"]["cal_dual"] = -p_dualGreening(float(ra), float(rg))   # prep_cal.gms l. 118-119
        env_on = bool(getattr(type(self), "env_const", False))
        if env_on and st.get(("active", "ecoSetAside")):
            r = st.get(("setaside_rate_pct", "ARAB"), 0.0) / 100.0
            ms = self.data.region_id[:2]
            ms = MS_CODE.get(ms, ms)
            # OFAR at CAPRI's weight times the member state's legume share (ROOF does not count); until 7 November
            # 2026 the model's OFOD = OFAR + ROOF carried it scaled by OFAR's share of the two
            w = {"VSET": st.get(("weight", "VSET"), 0.0), "FALL": st.get(("weight", "FALL"), 0.0),
                 "PULS": st.get(("weight", "PULS"), 0.0),
                 "OFAR": st.get(("weight", "OFAR"), 0.0) * float(fleg.get(ms, 0.0))}
            row = []
            for j, a in enumerate(acts):
                if a in CROPS and a not in CROPS_ON_LAND["GRAS"]:
                    row.append((j, r / (1.0 - r) - w.get(a, 0.0)))
            v0 = sum(c_ * xb[j] for j, c_ in row)
            sc_ = max(1.0, sum(abs(c_) * xb[j] for j, c_ in row))
            # catch crops count at CAPRI's weight (setaEco includes CATC, p_DPgreeningWeight 0.3) where the NLP form
            # chooses them (the winter cover option: share m of UAAR, CapriRegionalNLP adds - w x UAAR x m to the row)
            wc = st.get(("weight", "CATC"), 0.0)
            cs_ = self._catc_spec() if wc > 0 else None
            if cs_ is not None:
                v0 -= wc * float(cs_["uaa"]) * float(cs_["m0"])
            # CAPRI calibrates its catch crops so that the rule holds at the base (supply/prep_cal.gms l. 68-99): in
            # its 2030 data the row binds to round-off in many regions. Where the model's base misses it by that
            # round-off the row is held at the base (rhs = the base gap); where it misses it by more than
            # supply.ecosetaside_hold_tol of the row's scale the base is not CAPRI's (REGISTERED where it acts, DEP-10):
            # the hold is recorded (spec "held") and reported. None at the 2030 base (9 November 2026: 5 EU regions
            # within 1e-7 thousand ha)
            held = v0 > float(_settings().get("supply.ecosetaside_hold_tol")) * sc_
            if held:
                import warnings as _w
                _w.warn(f"{self.data.region_id}: the ecological set-aside rule is held at the base, which misses it by "
                        f"{v0:.4g} thousand ha (CAPRI's base meets it: supply/prep_cal.gms l. 68-99)")
            # K188: CAPRI's calibration sizes its catch crops to fill the rule (prep_cal.gms l. 68-99: CATC = the
            # requirement less the other EFA activities), so where the requirement exceeds the other activities the rule
            # binds at CAPRI's base and its dual is the catch crops' input cost over their weight. The model's base takes
            # CAPRI's 2030 catch-crop share; there the rule is held at the base's own value (it misses CAPRI's fill by
            # the levels' round-off, IT32 0.06 thousand ha), in CAPRI's reference form. Where the other activities alone
            # meet the requirement (v0 <= -catch crops' part: a base other than CAPRI's 2030, e.g. 2017's PT18) CAPRI's
            # calibration would leave CATC at zero and the rule slack: no fill
            _cpart = wc * float(cs_["uaa"]) * float(cs_["m0"]) if cs_ is not None else 0.0
            fill = (_cpart > 0 and v0 > -_cpart
                    and str(_settings().get("supply.reference_winter_cover")) == "capri")
            out["ecoSetAside"] = {"row": row, "rhs": (v0 if fill else max(0.0, v0)) + 1e-9 * sc_, "scale": sc_,
                                  "base_gap": v0, "held": bool(held), "catc_w": wc if cs_ is not None else 0.0,
                                  "catc_fill": bool(fill)}
        if env_on and st.get(("active", "cropDiv")):
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
                F = float(getattr(self.ev, "fall_floor", 0.0) or 0.0)
                if F > 0:
                    H0 = p_DPGreeningLimits_cropDiv(H0, X, T, F)
                out["cropDiv"] = {"groups": list(grp.values()), "H0": H0 * (1 - 1e-9), "floors": fl}
        return out or None

    def _organic_baseline(self) -> float:
        """EU organic share already in place (CAPRI load_organic_targets.gms: the EU target is
        0.25 - 0.10). Only a fallback: every EU member state has CAPRI's own percentage-point
        targets (organic_targets_ms.csv), which already net out its existing organic area; CAPRI
        applies them uniformly to the member state's regions. (A per-country table of 2018-2019
        Eurostat shares used here before CAPRI's targets were loaded was no longer reached for any
        EU region and has been removed.)"""
        return param("ORGANIC_BASELINE_SHARE")

    def _input_cost(self, a: str, item: str, share_table: dict) -> float:
        """EUR/ha of input `item` (used for 'fert') for crop a: CAPRI's regional cost
        (tools/build/build_plant_protection_cost.py), else the EU-wide share of input cost times the
        crop's input cost (REGISTERED fallback, crops CAPRI does not grow in the region)."""
        t = getattr(self.data, "input_costs_ha", None)
        col = item + "_eur_ha"
        if t is not None:
            # the region's table as a plain dict, built once per table (scalar pandas lookups were ~10% of a run)
            memo = getattr(self.par, "input_cost_memo", None)
            if memo is None or memo[0] is not t:
                memo = (t, {(r, c_): float(v) for r, row in t.to_dict("index").items() for c_, v in row.items()
                            if isinstance(v, (int, float)) and v == v})
                self.par.input_cost_memo = memo
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
        loss = p_yildReduction(param("PESTICIDE_YIELD_LOSS_AT_50PCT"), reduction) if yield_loss else 0.0
        # (a cap of the loss at 0.90 was removed 23 October 2026: unsourced and never reached - the loss is at most
        # 0.20, at a 100% cut)

        prices = self._solve_prices()
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
            o = min(max(o, 0.0), float(_settings().get("supply.organic_share_cap")))
            conv = 1.0 - o
            # The yield loss must reach BOTH the objective and the reported
            # yields. It used to change net revenue only, so it steered what
            # farmers grew but left gross_output computed on unshocked yields:
            # EU cereal PRODUCTION fell 6% where CAPRI reports 15%, even though
            # our cereal AREA fell 5.9% against CAPRI's 4%. The area response
            # was never the problem; the yield effect was missing from the
            # output. CAPRI reports production, so this is what is compared.
            new_ylds[a] = DATA_Yild(y, loss, conv)
            nr[a] = float(nr.get(a, 0.0)) - p * y * loss * conv
            self._nr_item(a, "O", a, -p * y * loss * conv, kg=-y * loss * conv * 1000.0, uv=p)
        # plant protection and other inputs: CAPRI's regional input changes, set with the organic target's in
        # _apply_greendeal_input_changes (24 October 2026; before, per crop on the conventional share: KNOWN_ISSUES K74; the supply audit's findings S3 and S4, ARCHITECTURE_REFACTOR.md section 5.2)
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
            self._nr_item(a, "O", a, p * y0 * (factor - 1.0), kg=y0 * (factor - 1.0) * 1000.0, uv=p)
        self.data.yields = new_ylds
        self.net_revenues = nr
        self.ev.yield_price_factor = pf

    def _organic_yield_gap(self, activity: str) -> float:
        """Organic yield gap for one activity in this region, as a fraction: CAPRI's estimate for the region's PESETA
        macro-region and the product group, else the Central-European (CEN) one, as CAPRI borrows it
        (organic_area.gms l. 176-181; e.g. maize in NE and UK_IR). Before 24 October 2026 a flat 20% from the
        literature (ORGANIC_YIELD_GAP) took CEN's place."""
        table = getattr(self.data, "organic_yield_gap", None)
        _m = getattr(self.par, "oyg_memo", None)                  # per table: the lookup ran ~170k times per run
        if _m is None or _m[0] is not table:
            _m = (table, {})
            self.par.oyg_memo = _m
        if activity in _m[1]:
            return _m[1][activity]
        _m[1][activity] = v_ = self._organic_yield_gap_uncached(activity, table)
        return v_

    def _organic_yield_gap_uncached(self, activity: str, table) -> float:
        # CAPRI's maps (inputs/load_organic_yieldgap.gms): the crop's product group (pact2yieldGap) and the member
        # state's PESETA macro-region (ms2peseta)
        group = (getattr(self.data, "organic_yield_gap_groups", None) or {}).get(activity)
        reg_id = getattr(self.data, "region_id", "")
        from capri_mod.data.definitions import capri_ms
        region = (getattr(self.data, "organic_yield_gap_regions", None) or {}).get(capri_ms(reg_id))
        if table is None or not group or region is None:
            return 0.0
        return DATA_Yild_percentageChange(*(table.at[reg_, group] if (reg_ in table.index and group in table.columns)
                                            else None for reg_ in (region, "CEN")),
                                          pest_disagg=bool(getattr(self.data, "pesticides", None)))

    @staticmethod
    def _organic_target_scale(share: float) -> float:
        """CAPRI's scaling of its targets to the requested ambition, (orgTarg - 12) / (25 - 12)
        (load_organic_targets.gms l. 175, 183; orgTarg in %): exactly 1 at the 25% target."""
        return p_organicTargetScale(share, param("ORGANIC_OUTLOOK_PCT"), param("ORGANIC_TARGET_REF_PCT"))

    def _organic_region_target(self, share: float) -> float:
        """p_organicAreaTarget(ru): the member state's UAA target (organic_targets_uaa.gdx) scaled to the ambition; 0
        where CAPRI maps no code to the member state (Portugal, the regions outside the EU: _capri_ms_targets).
        Without CAPRI's target files the EU distance-to-target fallback, as _organic_converted does."""
        t = getattr(self.data, "organic_targets_pp", None)
        v = t.get("uaa_pp") if (t is not None and hasattr(t, "get")) else None
        if v is None or pd.isna(v):
            return max(0.0, float(share) - self._organic_baseline())
        return p_organicAreaTarget(v, self._organic_target_scale(share))

    def _organic_crop_target(self, activity: str, share: float) -> float:
        """p_organicAreaTargetCrops(ru, crop) of CAPRI's organic crops (0 for the other crops): the target of the
        crop's NGRP group (ORGANIC_CROP_TARGET). A member state with no value for the group in CAPRI's
        organic_targets.gdx gets 0, as in CAPRI (Ireland: no permanent, Malta: no grassland), and so does one CAPRI
        maps no code to (Portugal, the regions outside the EU: _capri_ms_targets)."""
        col = self.ORGANIC_CROP_TARGET.get(activity)
        if col is None:
            return 0.0
        t = getattr(self.data, "organic_targets_pp", None)
        if t is None or not hasattr(t, "get"):
            return max(0.0, float(share) - self._organic_baseline())
        v = t.get(col)
        if v is None or pd.isna(v):
            return 0.0
        return p_organicAreaTarget(v, self._organic_target_scale(share))

    def _input_row(self, activity: str, col: str) -> Optional[float]:
        """CAPRI's cost row of this region and activity (data.input_costs_ha, build_plant_protection_cost.py), or
        None where CAPRI has none."""
        t = getattr(self.data, "input_costs_ha", None)
        if t is None or activity not in t.index or col not in t.columns:
            return None
        v = t.at[activity, col]
        return float(v) if pd.notna(v) else None

    def _input_row_2030(self, activity: str, col: str) -> Optional[float]:
        """CAPRI's simulation-year coefficient of this region and activity at the 2030 market year
        (data.input_coefs_2030, tools/build/build_input_coefs_2030.py: DATA(BAS) x (1 - f + f G) before TF_I, at the
        member state's UVAP(2030)), in the model's money; the factor columns (yield_growth, inpo_yield_factor) as they
        are. None outside the 2030 market year or where CAPRI has none (the caller takes the 2017 row)."""
        t = getattr(self.data, "input_coefs_2030", None)
        sim = getattr(self.data, "sim_year", None)
        if t is None or sim is None or activity not in t.index or col not in t.columns:
            return None
        v = t.at[activity, col]
        if not pd.notna(v):
            return None
        if col in ("yield_growth", "inpo_yield_factor"):
            return float(v)
        return float(v) / _inputs.money_deflator(int(sim))

    def _animal_inpo_cost(self, animal: str) -> Optional[float]:
        """The animal's INPO cost per model head in CAPRI's objective form (the input cost table's INPO: register DEP-13
        step 3), with supply.animal_cost_form "capri"; None with "toin" or without the table (the caller takes TOIN's
        INPO share)."""
        from capri_mod.settings import current as _settings
        if str(_settings().get("supply.animal_cost_form")) != "capri":
            return None
        ic = getattr(self.data, "livestock_input_cost", None)
        if ic is None or "INPO" not in ic.columns or animal not in ic.index or not pd.notna(ic.at[animal, "INPO"]):
            return None
        return float(ic.at[animal, "INPO"])

    def _sim_input_cost(self, activity: str, col: str) -> Optional[float]:
        """The cost row the Green Deal's input changes and the yields' input update act on: CAPRI's simulation-year
        coefficient at the 2030 market year (_input_row_2030, register DEP-21), else CAPRI's 2017 coefficient at the
        region's 2017 unit value (_input_row)."""
        v = self._input_row_2030(activity, col)
        return v if v is not None else self._input_row(activity, col)

    def _greendeal_tech_progress(self) -> float:
        """CAPRI's input-saving progress of the simulation year, TF_I = 1 - 0.005 x (Y - BAS)
        (capmod/define_inputs.gms l. 66)."""
        base = int(_inputs.base_year())                          # the run's base year (K52f)
        sim = int(getattr(self.data, "sim_year", None) or base)
        return TF_I_trend(param("INPUT_SAVING_PROGRESS"), sim, base)

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
        r is the pesticide reduction. The scenario coefficient is (base + top-up) x TF_I with the change
        (equations/define_inputs.py TF_I: (1 + change) x TF_I with CAPRI-ERROR-FIX greendeal_inputs_keep_tech_change,
        (1 + change) alone as CAPRI's code runs, see the setting); the baseline's is base x TF_I. At the 2030 market year
        the base is CAPRI's simulation-year coefficient before TF_I, DATA(BAS) x (1 - f + f G) (define_inputs.gms
        l. 107-112, DATA_IY_Y; the top-up follows INPO's), valued at the member state's UVAP of 2030 (define_objc.gms
        l. 40-44), and an animal's INPO cost per head carries its INPO's (1 - f + f G) (input_coefs_2030.csv,
        _sim_input_cost; until 23 November 2026 CAPRI's 2017 coefficients at the regions' 2017 unit values, DEP-21: the
        change's base 3.6% (INPO) and 5.2% (PLAP) lower at the median). Their yield-dependent part follows the yields
        in _apply_yield_input_costs, at these changes' TF_I.
        """
        from capri_mod.supply.equations.define_inputs import TF_I
        r = max(0.0, float(pesticide_reduction or 0.0))
        o_R = self._organic_region_target(organic_share) if organic_share else 0.0
        pc_plap, pc_inpo = DATA_GROF_percentageChange(r, o_R)      # conventional_io.gms, organic_io.gms l. 74
        tf = self._greendeal_tech_progress()
        keep_tf = bool(getattr(type(self), "greendeal_inputs_keep_tech_change", True))

        def delta(base: float, topup: float, pc: float) -> float:
            # change of the cost against the baseline (base x TF_I); TF_I changes only where CAPRI sets a change
            return (base + topup) * TF_I(tf, pc, keep_tf) - base * tf

        topup_col = "eful_eur_ha" if getattr(type(self), "organic_topup_at_fuel_cost", True) else "eful_inpo_eur_ha"
        nr = self.net_revenues.copy()
        self.ev.greendeal_inputs = {"o_R": o_R, "pc_plap": pc_plap, "pc_inpo": pc_inpo, "tf": tf, "keep_tf": keep_tf}
        if getattr(self.data, "pesticides", None):
            # the pesticide module: PLAP is not an input (sets.gms, PACT_TO_I without PLAP), its change goes to every
            # application as one factor (pest_change_factor_greendeal), and PLAP's own change is 0 (conventional_io.gms
            # l. 132-133)
            self.ev.pest_change_factor = pest_change_factor_greendeal(pc_plap, _organic_plap(o_R) if o_R > 0 else 0.0)
            self.ev.greendeal_inputs["pc_plap_module"] = pc_plap
            pc_plap = 0.0
        for a in self.acts:
            d = 0.0
            if a in ANIMALS:
                inpo_ = self._animal_inpo_cost(a)
                sh = self._input_row(a, "inpo_toin_share")
                if inpo_ is not None and pc_inpo != 0.0:
                    # CAPRI's INPO term of p_linObjeCont per model head (capmod/define_objc.gms l. 39-44, register DEP-13
                    # step 3): the input cost table's INPO, the year's coefficient x TF_I at the member state's UVAP;
                    # the change acts on its coefficient before TF_I
                    d = delta(inpo_ / tf, 0.0, pc_inpo)
                elif sh is not None and pc_inpo != 0.0:
                    # the INPO coefficient's yield-growth part at the 2030 market year (define_inputs.gms l. 107-112;
                    # the per-head basis is the model's, DEP-13)
                    yf = self._input_row_2030(a, "inpo_yield_factor") or 1.0
                    d = delta(sh * self._animal_cost_per_head(a) * yf, 0.0, pc_inpo)
                if d:
                    # the change per head of the animal's average, in either form; its split columns move heads
                    # between CAPRI activities whose INPO differs (livestock.py, dinpo_rel; K189's per-head terms)
                    if getattr(self.ev, "greendeal_animal_inpo", None) is None:
                        self.ev.greendeal_animal_inpo = {}
                    self.ev.greendeal_animal_inpo[a] = d
                    self._nr_item(a, "I", "INPO", d)
            else:
                plap = self._sim_input_cost(a, "plap_eur_ha")
                inpo = self._sim_input_cost(a, "inpo_eur_ha")
                d_p = d_i = 0.0
                if plap is not None and pc_plap != 0.0:
                    d_p = delta(plap, 0.0, pc_plap)
                if inpo is not None:
                    o_a = self._organic_crop_target(a, organic_share) if organic_share else 0.0
                    eful = self._sim_input_cost(a, topup_col) or 0.0
                    topup = DATA_INPO_BAS_topup(o_a, eful)
                    if topup or pc_inpo:
                        d_i = delta(inpo, topup, pc_inpo)
                d += d_p
                d += d_i
                step_ = self._plap_crop_level_capri_step(a, pc_plap, tf, keep_tf, d_p)
                d += step_
                self._nr_item(a, "I", "PLAP", d_p + step_)
                self._nr_item(a, "I", "INPO", d_i)
                if d_p or d_i:
                    # the crop's plant-protection and other-input costs of this solve (the mix columns' technology
                    # factors act on them, supply/techn_mix.py)
                    if getattr(self.ev, "greendeal_crop_delta", None) is None:
                        self.ev.greendeal_crop_delta = {}
                    self.ev.greendeal_crop_delta[a] = (d_p, d_i)
            if d:
                nr[a] = float(nr.get(a, 0.0)) - d
        self.net_revenues = nr

    def _plap_capri_step_cost(self, a: str, pc_plap: float, tf: float, keep_tf: bool):
        """CAPRI's Green Deal step's plant-protection cost of crop a per ha at the crop's mean technology, in the model's
        money (P_s), and its reference's (Plantp_cost), or None without CAPRI's two values for the crop or outside a
        simulation year. CAPRI's step (pesticide disaggregation off) values the crop's PLAP coefficient at the member
        state's UVAP (capmod/define_objc.gms l. 40-44, p_linObjeCont), the coefficient changed by the Green Deal's
        regional percentage (capmod/define_inputs.gms l. 66-73):

            P_s = DATA(r, a, "PLAP") x UVAP(MS, "PLAP") / 1000 x (1 + pc) x [TF_I] / TF_I / deflator(2030)

        ([TF_I] with greendeal_inputs_keep_tech_change, FIX-5; plap_uvap_eur_ha of
        plant_protection_capri_step_2030.csv the first factors, in CAPRI's 2030 money)."""
        t = getattr(self.data, "plap_capri_step", None)
        sim = getattr(self.data, "sim_year", None)
        if t is None or a not in t.index or sim is None:
            return None
        q_uv, ppc = float(t.at[a, "plap_uvap_eur_ha"]), float(t.at[a, "plantp_cost_eur_ha"])
        defl = _inputs.money_deflator(int(sim))
        return p_linObjeCont_PLAP(q_uv, pc_plap, tf, keep_tf, defl), ppc / defl

    def _plap_crop_level_capri_step(self, a: str, pc_plap: float, tf: float, keep_tf: bool, d_p: float) -> float:
        """Comparison switch supply.greendeal_plap_crop_level_capri_step (DEP-51, its crop-level part; off by default):
        the change of crop a's mean plant-protection cost per ha (model money) that moves the model's Green Deal step to
        CAPRI's valuation, 0 with the switch off or without CAPRI's two values for the crop.

        CAPRI's 2030 reference and its PMP calibration ran with the pesticide module's aggregates (pestDisaggStage
        5_aggregates, PEST_DISAGG on: the crop pays its disaggregated pesticides, reported as Plantp_cost;
        reports/rep_sets.gms l. 378-380), its Green Deal step without them (stage none: the crop pays PLAP,
        Plantp_cost.PLAP, l. 384-386; _plap_capri_step_cost):

            reference (calibration):  Plantp_cost(r, a)
            Green Deal step:          P_s = DATA(r, a, "PLAP") x UVAP(MS, "PLAP") / 1000 x (1 + pc) x [TF_I] / TF_I

        The model has one representation in base and scenario and changes its own cost by d_p (delta() above); with the
        switch on it changes it by CAPRI's step less its reference instead:

            shift_a = P_s - Plantp_cost_a / deflator(2030) - d_p

        The technology mix columns keep the model's d_p; their T1 - T2 part is _plap_mix_capri_step."""
        if not bool(getattr(type(self), "greendeal_plap_crop_level_capri_step", False)):
            return 0.0
        c = self._plap_capri_step_cost(a, pc_plap, tf, keep_tf)
        if c is None:
            return 0.0
        P_s, ppc = c
        return P_s - ppc - float(d_p)

    def _plap_mix_capri_step(self, a: str, plap_diff: float, d_p: float) -> float:
        """Comparison switch supply.greendeal_plap_mix_capri_step (DEP-51, its T1 - T2 part; off by default): the cost
        per unit of crop a's technology mix column (T1 less T2 per ha, model money) that its Green Deal step adds to
        the column's linear term to move it to CAPRI's step; 0 with the switch off, outside the Green Deal group's
        solves or without CAPRI's values for the crop.

        CAPRI's technology factors of plant protection (intens/techf.gms l. 102-103, in sim_ini_21730 for the step):

            p_technFact(RS,TACT,"PLAP","T1")      $ (PACT_TO_I(TACT,"PLAP") and (NOT FNUT("PLAP"))) = +0.40;
            p_technFact(RS,TACT,"PLAP","T2")      $ (PACT_TO_I(TACT,"PLAP") and (NOT FNUT("PLAP"))) = -0.40;

        enter p_linObjeCont as DATA x (p_technFact + 1) x UVAP (capmod/define_objc.gms l. 42-44), a T1 - T2 cost of
        plap_diff (0.8) x the crop's PLAP cost, where PLAP is in the objective. CAPRI's 2030 reference and its PMP
        calibration ran with 5_aggregates: PLAP is out of PACT_TO_I (sets.gms l. 5365-5368), so techf.gms gives it no
        factor, and the pesticides that replace it get none (techf.gms sets PLAP's only), so its calibrated T1 - T2
        terms hold no plant-protection cost; its Green Deal step ran with "none", PLAP in the objective. With k the
        model's calibrated term of the column and k' CAPRI's,
        the calibration conditions at the base give k' = k + plap_diff x P_b (P_b the model's base cost of the crop,
        which the model's calibration held); in the step

            CAPRI:  k' + plap_diff x P_s          = k + plap_diff x (P_b + P_s)
            model:  k  + plap_diff x (P_b + d_p)

        so the column's cost moves by plap_diff x (P_s - d_p) (P_s _plap_capri_step_cost; d_p the model's change of the
        crop's cost, greendeal_crop_delta). The other terms of the two calibrations are taken as equal."""
        if not bool(getattr(type(self), "greendeal_plap_mix_capri_step", False)):
            return 0.0
        if not bool(getattr(self.ev, "greendeal_group", False)) or not plap_diff:
            return 0.0
        gi = getattr(self.ev, "greendeal_inputs", None) or {}
        tf = float(gi.get("tf", self._greendeal_tech_progress()))
        c = self._plap_capri_step_cost(a, float(gi.get("pc_plap", 0.0) or 0.0), tf, bool(gi.get("keep_tf", True)))
        if c is None:
            return 0.0
        return float(plap_diff) * (c[0] - float(d_p))

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
        (need_yield_factor). The change above is CAPRI's derivative at its 2030 reference; at the 2030 market year its
        costs are CAPRI's base coefficients at the member state's UVAP of 2030 (input_coefs_2030.csv, _sim_input_cost; the
        same as the 2017 rows' but for plant protection, whose regional UVAG differs: register DEP-21), else CAPRI's
        2017 coefficients at the regions' 2017 unit values. REGISTERED: the baseline's own cost carries no yield-growth or
        TF_I term (the calibration absorbs the level)."""
        y0s, yc = getattr(self.ev, "yields_solve0", None), self.data.yields
        if y0s is None or not hasattr(yc, "get") or not hasattr(y0s, "get"):
            return
        tf = self._greendeal_tech_progress()
        gi = getattr(self.ev, "greendeal_inputs", None) or {}
        keep = bool(gi.get("keep_tf", True))
        from capri_mod.supply.equations.define_inputs import TF_I
        tf_p = TF_I(tf, float(gi.get("pc_plap", 0.0) or 0.0), keep)
        tf_i = TF_I(tf, float(gi.get("pc_inpo", 0.0) or 0.0), keep)
        nr = None
        for a in self.acts:
            if a not in CROPS:
                continue
            y0, y = float(y0s.get(a, 0.0) or 0.0), float(yc.get(a, 0.0) or 0.0)
            if not (y0 > 0 and y > 0) or y == y0:
                continue
            k = ((self._sim_input_cost(a, "yd_rest_eur_ha") or 0.0) * tf
                 + (self._sim_input_cost(a, "yd_plap_eur_ha") or 0.0) * tf_p
                 + (self._sim_input_cost(a, "yd_inpo_eur_ha") or 0.0) * tf_i)
            if k:
                g = self._sim_input_cost(a, "yield_growth") or 1.0
                # CAPRI's bounds on the yield growth: G x rho within 0.5-1.5
                d = (min(param("YIELD_GROWTH_MAX"), max(param("YIELD_GROWTH_MIN"), g * y / y0)) - g) / g if g > 0 else (y / y0 - 1.0)
                if nr is None:
                    nr = self.net_revenues.copy()
                nr[a] = float(nr.get(a, 0.0)) - k * d
                # by item: the yield-dependent plant protection and other inputs, the rest of them (OTHER_I)
                self._nr_item(a, "I", "PLAP", (self._sim_input_cost(a, "yd_plap_eur_ha") or 0.0) * tf_p * d)
                self._nr_item(a, "I", "INPO", (self._sim_input_cost(a, "yd_inpo_eur_ha") or 0.0) * tf_i * d)
                self._nr_item(a, "I", "OTHER_I", (self._sim_input_cost(a, "yd_rest_eur_ha") or 0.0) * tf * d)
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

        The requested share scales the ambition (0.25 = CAPRI's full target). A
        land type with no record in CAPRI's file, or a member state CAPRI maps no
        code to, gives 0 (_capri_ms_targets), as CAPRI's sum does; the
        distance-to-target rule only without CAPRI's target files.
        """
        if targets is None:
            return default
        if activity in self.PERMANENT_LAND_CROPS:
            col = "permanent_pp"
        elif activity in CROPS_ON_LAND["GRAS"]:
            col = "grassland_pp"
        else:
            col = "arable_pp"
        val = targets[col]
        # CAPRI scales its targets to the requested ambition as (orgTarg - 12) / (25 - 12)
        # (load_organic_targets.gms; orgTarg in %), exactly 1 at the 25% target
        scale = self._organic_target_scale(share)
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

        prices = self._solve_prices()
        ylds = self.data.yields
        new_ylds = ylds.copy()
        nr = self.net_revenues.copy()
        converted_default = max(0.0, float(share) - self._organic_baseline())
        _org = getattr(self.data, "organic_targets_pp", None)
        # CAPRI's target per fertiliser crop group (p_organicAreaTargetCrops(ru, ngrp), load_organic_targets.gms
        # l. 160-188), for the mineral-N caps of organic_minfert_redu.gms 'region_and_crop': the class of the group
        # (crops_to_ngrp: arable land, grassland, permanent crops; VEGE the UAA target) at the member state's target
        # scaled to the ambition; 0 where CAPRI's files give the member state none. Without CAPRI's targets (outside
        # the EU) none is set and the cap falls back to the crops' conversion (fertilisation._npk_organic_cap)
        self.ev.organic_group_target = {}
        _cls = getattr(self.data, "organic_ngrp_class", None)
        if _org is not None and hasattr(_org, "get") and _cls:
            _sc = self._organic_target_scale(share)
            for g_, col_ in _cls.items():
                v_ = _org.get(col_)
                self.ev.organic_group_target[g_] = (0.0 if v_ is None or pd.isna(v_)
                                                    else max(0.0, min(1.0, float(v_) / 100.0 * _sc)))
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
            self._nr_item(a, "O", a, p * y * (yield_factor - 1.0), kg=y * (yield_factor - 1.0) * 1000.0, uv=p)
            self._nr_item(a, "I", "FERT", cost_change)
            # Converted land uses NO mineral fertiliser (CAPRI's
            # organic_minfert_redu.gms). Only its COST was removed here, so in
            # the nitrogen balance and the environmental accounts organic land
            # still spread full mineral N. The mineral-N factor travels the
            # same path as the fertiliser technologies (multiplied with them).
            if converted > 0:
                self.ev.n_intensity = getattr(self.ev, "n_intensity", {}) or {}
                self.ev.n_intensity[a] = self.ev.n_intensity.get(a, 1.0) * max(0.0, 1.0 - converted)
                # the conventional share alone, for CAPRI's minimum mineral share (NUTMIN_: 0 on organic land)
                self.ev.organic_conv = getattr(self.ev, "organic_conv", {}) or {}
                self.ev.organic_conv[a] = self.ev.organic_conv.get(a, 1.0) * max(0.0, 1.0 - converted)
                nc_ = self.data.nutrient_coefs
                if a in nc_.index and "N" in nc_.columns:
                    nc_ = nc_.copy()
                    nc_.at[a, "N"] = float(nc_.at[a, "N"]) * max(0.0, 1.0 - converted)
                    self.data.nutrient_coefs = nc_
        self.data.yields = new_ylds
        self.net_revenues = nr
