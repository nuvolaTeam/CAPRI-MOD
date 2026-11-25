"""Land in the regional model: CAPRI's land market (the land types as variables, Trustee_land).

RegionalSupplyModel's methods, moved unchanged from capri_mod/supply/supply_module.py (the refactor's split into block mixins,
docs/dev/ARCHITECTURE_REFACTOR.md); the module-level names they use are supply_module's, given to
this module once supply_module is loaded (capri_mod.utils.mixins.inject_names); the annotations are not evaluated
(they name supply_module's types).
"""
from __future__ import annotations

from capri_mod.supply.equations.define_manure_trade_costs import p_manureBuyCostSlope
from capri_mod.supply.equations.prep_sim_luc import v_actLevl_bounds_foreOlndArtif, v_actLevl_lo_floor


class LandBlock:
    def _manure_trade_terms(self, fout: str):
        """CAPRI's trade terms of the region's manure market for nutrient fout (supply_module.manure_trade_terms) when
        supply.manure_trade_form is "capri", else None (the "net" form: one change of net trade each way from zero at
        supply.manure_pool_slope over the model's manure, no opening cost). Under "capri" the two columns are the
        changes of the region's gross exports and imports from CAPRI's calibration point (CAPRI's e_costMTrade: each
        direction with its own cost, supply/define_manure_trade_costs.gms), each bounded below by minus that trade
        (ev.pool_lb), the direction the region does not trade opening at CAPRI's calibrated constant; the constants of
        the trade the region has are calibrated with the model's base (CAPRI's FINALIZE)."""
        form = str(_settings().get("supply.manure_trade_form"))
        if form not in ("capri", "net"):
            raise ValueError(f'supply.manure_trade_form = "{form}": "capri" or "net"')
        if form == "net":
            return None
        tt = manure_trade_terms(self.data.region_id, fout)
        if tt is None:
            raise KeyError(f"{self.data.region_id} {fout}: no CAPRI manure trade terms (manure_pool_market_2030.csv)")
        return tt

    def _land_of(self, kind: str) -> float:
        """The region's land of a type (1000 ha; capri_data land_availability.csv, CAPRI's data). Missing data stop the
        run (no fallback: the former 200 / 30 / 80 kha stand-ins were never reached and are gone, 23 October 2026)."""
        land = getattr(self.data, "land", None)
        v = land.get(kind) if land is not None else None
        try:
            v = float(v)
        except (TypeError, ValueError):
            v = float("nan")
        if not np.isfinite(v):
            raise ValueError(f"{self.data.region_id}: no {kind} land in land_availability.csv")
        return v

    def _obligatory_set_aside(self, Aa, labels, n):
        """CAPRI's obligatory set-aside (supply/supply_model.gms SETA_, l. 2219-2241): the arable activities with a
        set-aside rate r (DATA(ru, act, "SETR"), percent) require r / (1 - r) ha of obligatory set-aside per ha, x
        (1 - NONS), on arable land: sum(act, level x (1 - NONS) x r / (1 - r)) = ISET (+GSET, TSET, NONF). CAPRI's
        ISET has no output, no input cost (no TOIN in its 2030 data), no premium and no PMP term (no level at the
        calibration point); prep_sim.gms l. 253 opens it where a rate is set. With nothing of its own in the objective,
        the ISET column equals that sum, so it is substituted: each activity's coefficient in the arable land balance
        (CAPRI's LandBalNoSlak_(ARAC), which carries ISET) rises by r / (1 - r), and the ISET area is that term of the
        solution (reported as ISET). The balance's base use (its right-hand side) stays the base's, without the
        obligation: the land it needs comes from the crops or from more arable land, at the land market's cost, as in
        CAPRI. NONS (CAPRI's non-food share on set-aside) is 0 in CAPRI's 2030 data and in its set-aside scenario.
        Applies where the scenario gives rates (the policy shock's set_aside_rates); returns Aa unchanged otherwise."""
        rates = getattr(self.ev, "set_aside_rates", None) or {}
        self.ev.seta_obl_vec = None
        if not rates:
            return Aa
        inc = np.zeros(n)
        for j, a in enumerate(self.acts[:n]):
            r = 0.01 * float(rates.get(a, 0.0) or 0.0)
            if r > 0:
                if not r < 1.0:
                    raise ValueError(f"{self.data.region_id}: set-aside rate of {a} {100 * r}% (below 100% needed)")
                inc[j] = r / (1.0 - r)
        if not inc.any():
            return Aa
        for lab, sign in (("arable_land", 1.0), ("arable_land_lo", -1.0)):
            if lab in labels:
                Aa[labels.index(lab), :n] += sign * inc
        self.ev.seta_obl_vec = inc
        return Aa

    def _land_type_bounds(self, Aa, ba, labels, n, li, L0):
        """CAPRI's bounds on the land types forest, other land and artificial land, foreOlndArtif (supply/prep_sim_luc.gms
        l. 586-612, Trustee_land):
          L0 - min(a x L0, b x ARTO) <= L <= L0 + min(9 x L0, 0.35 x ARTO)  (FORE, OLND, ARTIF; a = 0.9, b = 0.35,
          Corsica 0.98 and 0.75), ARTO the region's total area (luc_2030.csv);
          and where the landscape floor holds (DATA(FALL, FLOOR) > 0): FORE >= 0.99 x L0 ('usually only a 1% decline
          is considered plausible') and ARTIF >= 0.997 x L0 ('usually only a 0.3% decline is considered plausible').
          Not binding at the base point. ARTIF is a column of the land market since 20 November 2026 (K189; before,
          held at its base).
        Rows forest_lo, forest_up, other_land_lo, other_land_up, artificial_land_lo, artificial_land_up, forest_floor,
        artificial_land_floor; a region without ARTO gets the floors alone (none in the EU's data)."""
        from capri_mod.environmental.luc import LUCModel
        reg = self.data.region_id
        arto = (LUCModel.get().v.get(reg) or {}).get("ARTO")
        arto = float(arto) if arto is not None and arto == arto else None

        def tab(t):
            return float(t.get(reg, t["ALL"]))
        new_r, new_b = [], []

        def row(j, sign, rhs, lab):
            r = np.zeros(Aa.shape[1]); r[n + j] = sign
            new_r.append(r); new_b.append(rhs); labels.append(lab)
        for t, lab in (("FORE", "forest"), ("OLND", "other_land"), ("ARTIF", "artificial_land")):
            if t not in li or arto is None:
                continue
            j = li[t]; l0 = float(L0[j])
            lo, up = v_actLevl_bounds_foreOlndArtif(l0, arto, tab(param_table("LUC_LO_OWN_SHARE")),
                                                    tab(param_table("LUC_LO_ARTO_SHARE")), param("LUC_UP_OWN_FACTOR"),
                                                    param("LUC_UP_ARTO_SHARE"))
            row(j, -1.0, -lo + 1e-9 * max(1.0, l0), f"{lab}_lo")
            row(j, 1.0, up + 1e-9 * max(1.0, l0), f"{lab}_up")
        if "FORE" in li and float(getattr(self.ev, "fall_floor", 0.0) or 0.0) > 0 and float(L0[li["FORE"]]) > 0:
            l0 = float(L0[li["FORE"]])
            row(li["FORE"], -1.0, -v_actLevl_lo_floor(l0, param("LUC_FORE_FLOOR")) + 1e-9 * max(1.0, l0), "forest_floor")
        if "ARTIF" in li and float(getattr(self.ev, "fall_floor", 0.0) or 0.0) > 0 and float(L0[li["ARTIF"]]) > 0:
            l0 = float(L0[li["ARTIF"]])
            row(li["ARTIF"], -1.0, -v_actLevl_lo_floor(l0, param("LUC_ARTIF_FLOOR")) + 1e-9 * max(1.0, l0),
                "artificial_land_floor")
        if new_r:
            Aa = np.vstack([Aa] + new_r); ba = np.concatenate([ba, new_b])
        return Aa, ba

    def _land_augment(self, A_ub, b_ub, c_lin, x0):
        """Augment the regional QP with CAPRI's land market (LandMarket_,
        trustee-land variant): land-type areas L as variables, cost 1/2 L'Q L
        (p_pmpQuadLandTypes) with constants making the base areas optimal; land
        rows become  activities - land <= base limit - base land, i.e. exactly
        the current rows at base; total land <= base total; grassland >= (1 -
        allowance) x base (CAPRI Green Deal default allowance 0%). Returns None
        where the region has no land-market data."""
        self.ev.need_row = None
        self.ev.nrow_land = None
        lm = getattr(self.data, "land_market", None)
        if not lm or "quad" not in lm:
            return None
        labels = list(getattr(self.ev, "row_labels", []))
        LTall = list(lm["types"])          # the land types of the data, in the order of its quad
        keep = [LTall.index(t) for t in self.LAND_TYPES]
        # CAPRI's land block (supply_model.gms LandMarket_, LandBalNoSlak_, e_artoBal; equations/supply_model/land.py)
        from capri_mod.supply.equations.supply_model.land import (
            LandMarket_quad, LandMarket_cnst, LandBalNoSlak_landCol, LandBalNoSlak_baseUse, e_artoBal,
            permGrasGreening_land)
        # UNITS: CAPRI's land-market terms are per HECTARE, the model's land
        # variables in 1000 ha - hence x 1000. Verified: with observed land
        # rents the matrix then implies an arable land-supply elasticity of
        # median 0.062 (10th 0.010, 90th 0.334), the range of CAPRI's priors;
        # unscaled it implied a median of 62 and land converted far too easily.
        Qf = LandMarket_quad(lm["quad"], keep)
        L0 = np.array([float(lm["base_kha"].get(t, 0.0)) for t in self.LAND_TYPES])
        n, k = len(x0), len(keep)
        Qa = np.zeros((n + k, n + k)); Qa[:n, :n] = self.Q; Qa[n:, n:] = Qf
        ca = np.concatenate([c_lin, LandMarket_cnst(Qf, L0)])
        Aa = np.hstack([A_ub, np.zeros((A_ub.shape[0], k))]); ba = b_ub.astype(float).copy()
        li = {t: j for j, t in enumerate(self.LAND_TYPES)}
        rowmap = {"arable_land": [(li["ARAC"], 1.0)],
                  # CAPRI LandBalNoSlak_(GRAS): grassland activities = grassland. Arable fodder
                  # (MAIF, OFAR, ROOF) sits on ARABLE land, in the arable row; see _build_constraints
                  "grassland": [(li["GRAS"], 1.0)],
                  "permanent_land": [(li["FRUN"], 1.0)]}
        rows = []
        for lab, coeffs in rowmap.items():
            if lab not in labels:
                continue
            i = labels.index(lab)
            const = LandBalNoSlak_landCol(b_ub[i], coeffs, L0)
            for j, cf in coeffs:
                Aa[i, n + j] -= cf
            ba[i] = const
            rows.append((i, coeffs, const))
        if not rows:
            return None
        # CAPRI takes the land rents as given in its calibration (supply/cal_land_nests.gms, prep_cal.gms l. 125-156):
        # at the 2030 calibration point the land market is balanced at CAPRI's rents, not at the model's recovered
        # duals (docs/dev/LAND_RENT_CALIBRATION_PLAN.md)
        # Every land type with a level in CAPRI's region has a positive calibration rent (tools/build/build_land_rents.py
        # applies cal_land_nests.gms l. 204-226 where CAPRI's reported D_AREA is not positive). Before 23 October 2026
        # the base dual recovered from the model's own QP solution stood in at 2017 and for those cells at 2030; that QP
        # carried a 1% shadow-price proxy and a 15% grassland headroom (no proxies: removed). A land type without a
        # CAPRI rent has no level in CAPRI's region: rent 0.
        _rents = getattr(self.data, "land_rents", None)
        if _rents is None:
            raise ValueError(f"{self.data.region_id}: no CAPRI land rents for the land market (land_rents_<year>.csv)")
        _rlab = {"arable_land": "ARAC", "permanent_land": "FRUN", "grassland": "GRAS"}
        self.ev.land_rent_rows = {}
        for lab, coeffs in rowmap.items():
            t_ = _rlab.get(lab)
            m_ = float(_rents.get(t_, 0.0)) if _rents.get(t_, 0.0) == _rents.get(t_, 0.0) else 0.0
            self.ev.land_rent_rows[lab] = m_
            for j, cf in coeffs:
                ca[n + j] += m_ * cf
            # the activities' side of the same calibration (CAPRI's FOC at the calibration point, prep_cal.gms /
            # cal_land_nests.gms: revenue - cost - PMP marginal - land rent x land use = 0): the land row's dual at
            # the base is the rent, so the activities' linear terms carry it. Without this the rent was charged by
            # the land market but not in the activities' calibration, and the plain path (no NLP calibration) lost
            # 8-11% of its crops at base (KNOWN_ISSUES K68); the NLP form recalibrates its linear terms at the base
            # and absorbed the difference
            if lab in labels and m_:
                ca[:n] -= m_ * np.asarray(A_ub[labels.index(lab), :n], dtype=float)
        # ---- SURPLUS PER HECTARE OF CURRENT LAND (CAPRI e_SURTOTHa, e_EXCRET:
        # divided by sum(landTypesNoSlak, v_actLevl)). With it, a region gains
        # nothing per hectare by giving up farmland, and expanding it costs land
        # (land market). Limit = target per ha x (ARAC + GRAS + FRUN), as a
        # deviation from base land - identical at base.
        if "N_balance" in labels:
            i_nb_ = labels.index("N_balance")
            base_area_ = float(sum(v for a_, v in self._base_levels().items() if a_ in CROPS))
            if base_area_ > 0:
                # the target per ha (CAPRI's MAXS: SURTOT_REST_ on e_SURTOTHa, every term per ha of current land), not
                # the row's right-hand side per ha: that also holds the region's base manure trade (supply.
                # manure_base_trade "capri", K167), a level of the region (v_manureExports, v_manureImports), which does
                # not grow with the land (KNOWN_ISSUES K176: until 18 November 2026 an importer's land earned less than
                # the target per ha, ES420000 20.2 against 29.5 kg N; ES510000, an exporter, 155 against 93)
                _sr = getattr(self.ev, "surplus_row", None)
                tgt_ = float(_sr[1]) if _sr is not None else float(ba[i_nb_]) / base_area_
                lt_ = [t for t in ("ARAC", "GRAS", "FRUN") if t in li]
                for t in lt_:
                    Aa[i_nb_, n + li[t]] -= tgt_
                ba[i_nb_] -= tgt_ * float(sum(L0[li[t]] for t in lt_))
                # for a relaxed target (_relax_n_target): the land columns and base land
                self.ev.nrow_land = ([n + li[t] for t in lt_], float(sum(L0[li[t]] for t in lt_)), tgt_)
        # ---- FERTILISER ALLOCATION (CAPRI supply_model.gms NUTNED_): manure
        # REPLACES mineral fertiliser. Mineral N becomes a variable M >= crop need
        # - availability x manure applied (>= 0). Crops' CURRENT mineral N is
        # base mineral N x fertiliser intensity x need factor of the yield (_need_yf) - the
        # same terms the N row already applies (a first version used the BASE
        # amount and double-counted, turning crops into N sinks: pigs fell more,
        # not less). Crop need = current mineral N + manure-covered need (spread
        # by uptake, so the row returns exactly the base mineral N at base). The
        # N row takes M instead of crops' current mineral N; fertiliser is charged
        # on M at CAPRI's price (UVAG NITF) with the per-ha charge added back;
        # constants shift by the allocation row's base dual (= that price).
        k_extra = 0
        self.ev.cover_dbf_nb = 0.0
        if "N_balance" in labels:
            srow = getattr(self.ev, "surplus_row", None)
            nmin = srow[2] if srow is not None and len(srow) > 3 else None
            upt = srow[3] if srow is not None and len(srow) > 3 else None
            ybase = srow[4] if srow is not None and len(srow) > 4 else None
            bser = srow[0] if srow is not None else None
            a_av, pf = self._fert_alloc_params()
            if nmin and upt and bser is not None and a_av and pf:
                i_nb = labels.index("N_balance")
                mint = getattr(self.ev, "n_intensity", {}) or {}
                ycur = self.data.yields
                xb = np.maximum(self._base_levels().reindex(self.acts).fillna(0.0).values, 0.0)
                nm0 = np.array([float(nmin.get(a, 0.0)) if a in CROPS else 0.0 for a in self.acts])
                nmc = nm0.copy()
                for i, a in enumerate(self.acts):
                    if a in CROPS and nm0[i] > 0:
                        f_ = float(mint.get(a, 1.0))
                        if ybase is not None and hasattr(ybase, "get"):
                            y0 = float(ybase.get(a, 0.0)); yc = float(ycur.get(a, y0)) if hasattr(ycur, "get") else y0
                            if y0 > 0 and yc > 0:
                                f_ *= self._need_yf(a, y0, yc)
                        nmc[i] = nm0[i] * f_
                up = np.array([float(upt.get(a, 0.0)) if a in CROPS else 0.0 for a in self.acts])
                e = np.array([max(0.0, float(bser.get(a, 0.0))) if a in ANIMALS else 0.0 for a in self.acts])
                man0, w, m0 = float(e @ xb), float(up @ xb), float(nm0 @ xb)
                if w > 0 and m0 > 0:
                    u = a_av * man0 * up / w
                    cols = Aa.shape[1]
                    Qa = np.pad(Qa, ((0, 1), (0, 1))); Qa[-1, -1] = 1e-9
                    Aa = np.hstack([Aa, np.zeros((Aa.shape[0], 1))])
                    Aa[i_nb, :n] -= nmc
                    Aa[i_nb, -1] = 1.0
                    req = np.zeros(cols + 1); req[:n] = nmc + u - a_av * e; req[-1] = -1.0
                    Aa = np.vstack([Aa, req]); ba = np.concatenate([ba, [1e-9 * max(1.0, m0)]])
                    labels.append("alloc_mineral_N")
                    ca = np.concatenate([ca, [pf]])
                    ca[:n] = ca[:n] - pf * (nmc + u) + pf * a_av * e
                    self.ev.alloc_m0 = float(nmc @ np.maximum(x0, 0.0))
                    self.ev.alloc_row = Aa.shape[0] - 1
                    k_extra = 1
                    # CAPRI's catch crops (NUTNED_ l. 1076, e_BIOFIX): their N is an input of the
                    # balance and supplies crop need, so mineral N may fall by as much
                    dbf = self._cover_n_increment()
                    if dbf > 0:
                        ba[i_nb] -= dbf
                        ba[self.ev.alloc_row] += dbf
                        self.ev.cover_dbf_nb = dbf          # (the NLP form's chosen catch crops replace it)
        alloc_k = k_extra
        self.ev.alloc_cols = alloc_k
        self.ev.pool_cols = []
        self.ev.pool_cols_pk = {}
        self.ev.pool_lb = {}
        # ---- NATIONAL MANURE MARKET (CAPRI e_costMTrade, manuremarket/*). The
        # balance ALREADY makes manure replace mineral N linearly (availability
        # a, CAPRI fertiliser_substitution): the animals' row terms are about
        # (1 - a) x manure. Traded manure enters the same way: N row -(1 - a)
        # per t exported, +(1 - a) per t imported; objective: exporters pay the
        # pool price + the fertiliser they must now buy (a x p_f), importers
        # receive the pool price + the fertiliser they save. (A first version
        # used the full manure amount and no saving - pool prices of EUR
        # 58-98/kg; a second added a fertiliser allocation that counted
        # substitution twice.) Manure-application row +-1; CAPRI's quadratic
        # cost; exports <= manure produced. REGISTERED: (1 - a) also where
        # mineral N sits at its floor (strictly 1 there).
        # the manure and ammonia accounts in every EU solve: in EVERY EU solve with manure trade on (CAPRI: e_netMTrade, e_costMTrade are in every run), not
        # only under the N target; the N row takes the trade only where it exists. OBJECTIVE: the pool price alone
        # (+ the emission tax). CAPRI's cost constants are calibrated from the base duals (define_manure_trade_costs.gms
        # FINALIZE) so the base trade is optimal; with a fixed fertiliser price the fertiliser saved or bought per t
        # traded (sub x p_f) is part of what that calibration absorbs, and a deviation from the base trade is driven
        # by the change in manure's value (N target, crop-need row, tax) - the sub x p_f terms of the first version
        # made importers pay up to EUR 0.9/kg N at base and shifted every pool's price by the region's own sub x p_f.
        pool_k = 0
        _mc = self._mctx()
        if _mc is not None and getattr(self, "use_manure_pool", False):
            a_av, pf = self._fert_params_raw()
            man_d = _mc["man_d"]
            if a_av is not None and man_d is not None:
                i_nb = labels.index("N_balance") if "N_balance" in labels else None
                xb = np.maximum(self._base_levels().reindex(self.acts).fillna(0.0).values, 0.0)
                e = np.array([float(man_d.get(a, 0.0)) for a in self.acts])
                man0 = float(e @ xb)
                # the balance's own substitution factor (availability / mineral
                # efficiency, not availability alone), and the FLOOR: where the
                # region's mineral N is already zero, manure cannot displace any
                # more of it - traded manure then counts in full and carries no
                # fertiliser cost or saving (West Flanders, Antwerp)
                sub = 0.0
                env_ = getattr(self.seen, "env_for_surplus", None)
                if env_ is not None:
                    try:
                        sub = float(env_._substitution(self.data.region_id)[0])
                        cur = {a: float(v) for a, v in zip(self.acts, np.maximum(x0, 0.0))}
                        nb_now = env_.compute_nitrogen_balance(cur, self.data.yields, self.data.region_id,
                                                               yields_scen=self._yields_scen_now())
                        if float(nb_now.get("n_mineral_input", 1.0)) <= 1e-6:
                            sub = 0.0
                    except Exception as _exc:
                        import warnings as _w
                        _w.warn(f"manure market: substitution factor unavailable for "
                                f"{self.data.region_id} ({_exc!r}); using availability")
                        sub = float(a_av)
                # with the base trade a level of the region (supply.manure_base_trade "capri", K167) the animals'
                # manure (man_d) is their full manure and the base exports a constant of the region: the manure kept
                # at base, the pool's measure of the region's supply, is the same as with the shares
                _x0 = float(env_.base_manure_trade(self.data.region_id)[0]) \
                    if (env_ is not None and str(_settings().get("supply.manure_base_trade")) == "capri") else 0.0
                man0 = man0 - _x0
                if man0 > 1e-6:
                    pp = float(getattr(self.seen, "manure_pool_price", 0.0) or 0.0)
                    # CAPRI supply/define_manure_trade_costs.gms l. 66-71: p_manureBuyCostSlope = 50 / (GROF / 100), EUR
                    # 50 per t N for each 1% of the region's manure N supply traded. man0 is in t N (kg N per unit x
                    # 1000 units) and the objective in EUR 1000, so CAPRI's 50 is 0.05 here (supply.manure_pool_slope)
                    slope = p_manureBuyCostSlope(float(_settings().get("supply.manure_pool_slope")), man0)
                    # emission tax: the mineral N bought (export) or saved (import), sub x the accounts' soil N2O
                    # factor and the indirect N2O of its runoff and leaching per t N (kt CO2-eq x EUR/t = 1000 EUR);
                    # the NLP form takes exactly this term out again (_nlp_tax_terms), mineral N being endogenous there
                    g_ = float(getattr(self.seen, "ghg_tax", 0.0) or 0.0) * sub \
                        * (self._ef_mineral_n2o() + self._ef_mineral_lea()) / 1000.0
                    tt = self._manure_trade_terms("MANN")
                    pcols = []
                    for sign in (-1.0, +1.0):                  # -1 export, +1 import
                        Qa = np.pad(Qa, ((0, 1), (0, 1)))
                        Qa[-1, -1] = slope if tt is None else tt["sell_slope" if sign < 0 else "buy_slope"]
                        op = 0.0 if tt is None else tt["open_export" if sign < 0 else "open_import"]
                        ca = np.concatenate([ca, [(pp + g_ + op) if sign < 0 else (-pp - g_ + op)]])
                        Aa = np.hstack([Aa, np.zeros((Aa.shape[0], 1))])
                        if i_nb is not None:
                            Aa[i_nb, -1] = sign * (1.0 - sub)
                        if "mineral_N" in labels:
                            # mineral N: exported manure must be replaced (+sub), imported manure displaces it
                            Aa[labels.index("mineral_N"), -1] = -sign * sub
                        pcols.append(Aa.shape[1] - 1)
                    capr = np.zeros(Aa.shape[1]); capr[:n] = -e; capr[pcols[0]] = 1.0
                    # (with the base exports a constant, K167: base exports + change <= manure)
                    Aa = np.vstack([Aa, capr]); ba = np.concatenate([ba, [-_x0]])
                    labels.append("manure_export_cap")
                    self.ev.pool_cols = pcols
                    if tt is not None:
                        self.ev.pool_lb["N"] = {pcols[0]: -tt["e0"], pcols[1]: -tt["i0"]}
                    self.res.manure_supply0 = man0
                    self.res.pool_manure_vec = e.copy()
                    self.res.pool_manure_x0 = _x0
                    self.ev.pool_avail = sub
                    pool_k = 2
            # ---- CAPRI's P and K manure markets (manureTradeNew: e_netMTrade, e_costMTrade and the pools by FOUT,
            # MANP and MANK besides MANN; manuremarket/simu_manure_market.gms clears one market per nutrient). Their
            # columns enter the fertilisation block's P and K manure balances only (ManureNPK_), at the pool price of
            # the nutrient and CAPRI's quadratic cost, slope EUR 50 per t for each 1% of the region's excretion of
            # the nutrient traded (define_manure_trade_costs.gms l. 66-71, by FOUT); exports at most the manure P / K
            # applied in the region. As the N columns, they trade around CAPRI's base trade (in the accounts), and
            # the base calibration makes their base value optimal (CAPRI's cost constants, FINALIZE).
            if pool_k == 2:
                pkc, pk0, pkv = {}, {}, {}
                for nut in ("P", "K"):
                    vecs = self._pk_manure_vectors(nut)
                    if vecs is None:
                        continue
                    exc, app = vecs
                    grof = float(exc @ xb)
                    if grof <= 1e-6:
                        continue
                    slope_k = p_manureBuyCostSlope(float(_settings().get("supply.manure_pool_slope")), grof)
                    pp_k = float((getattr(self.seen, "manure_pool_price_pk", None) or {}).get(nut, 0.0) or 0.0)
                    tt_k = self._manure_trade_terms({"P": "MANP", "K": "MANK"}[nut])
                    cols_k = []
                    for sign in (-1.0, +1.0):              # -1 export, +1 import
                        Qa = np.pad(Qa, ((0, 1), (0, 1)))
                        Qa[-1, -1] = slope_k if tt_k is None else tt_k["sell_slope" if sign < 0 else "buy_slope"]
                        op = 0.0 if tt_k is None else tt_k["open_export" if sign < 0 else "open_import"]
                        ca = np.concatenate([ca, [(pp_k + op) if sign < 0 else (-pp_k + op)]])
                        Aa = np.hstack([Aa, np.zeros((Aa.shape[0], 1))])
                        cols_k.append(Aa.shape[1] - 1)
                    if tt_k is not None:
                        self.ev.pool_lb[nut] = {cols_k[0]: -tt_k["e0"], cols_k[1]: -tt_k["i0"]}
                    capr = np.zeros(Aa.shape[1]); capr[:n] = -app; capr[cols_k[0]] = 1.0
                    Aa = np.vstack([Aa, capr]); ba = np.concatenate([ba, [0.0]])
                    labels.append(f"manure_export_cap_{nut}")
                    pkc[nut], pk0[nut], pkv[nut] = cols_k, grof, app.copy()
                    pool_k += 2
                self.ev.pool_cols_pk = pkc
                self.res.manure_supply0_pk = pk0
                self.res.pool_manure_vec_pk = pkv
        # ---- MANURE WITHIN CROP NEED (CAPRI supply_model.gms fertDistExcr_ +
        # NUTNED_, an EQUALITY with mineral N >= 0; its over-application term is
        # commented out): a region can hold only as much manure as its crops can
        # use at their availability. As a row: mineral N still required >= 0,
        #   sum crops (current need x area) - sub x (manure + imports - exports) >= 0.
        # Without it importers absorbed unlimited paid manure and cut crops to
        # make room (cereal area -31% in importing regions). Regions already
        # beyond it at base are held at their base deficit. REGISTERED: applied
        # where the N target applies (CAPRI: always).
        # the manure and ammonia accounts in every EU solve: in every EU solve (CAPRI's NUTNED_ is in every run), not only under the N target
        _mc = self._mctx()
        if _mc is not None:
            nmin, ybase, man_d = _mc.get("nmin"), _mc.get("ybase"), _mc.get("man_d")
            env_ = getattr(self.seen, "env_for_surplus", None)
            if nmin and man_d is not None and env_ is not None:
                try:
                    sub_n = float(env_._substitution(self.data.region_id)[0])
                except Exception as _exc:
                    import warnings as _w
                    _w.warn(f"crop-need limit skipped for {self.data.region_id}: {_exc!r}")
                    sub_n = None
                if sub_n:
                    mint = getattr(self.ev, "n_intensity", {}) or {}
                    ycur = self.data.yields
                    need = np.zeros(n)
                    for j, a in enumerate(self.acts):
                        if a in CROPS:
                            v = float(nmin.get(a, 0.0)) * float(mint.get(a, 1.0))
                            if ybase is not None and hasattr(ybase, "get"):
                                y0 = float(ybase.get(a, 0.0)); yc = float(ycur.get(a, y0)) if hasattr(ycur, "get") else y0
                                if y0 > 0 and yc > 0:
                                    v *= self._need_yf(a, y0, yc)
                            need[j] = v
                    man = np.array([float(man_d.get(a, 0.0)) for a in self.acts])
                    # the nitrate additive's extra manure N displaces mineral N like any manure (the accounts:
                    # mineral - sub x extra); on the N row it was, on this row not (K9)
                    _nx = self._nitrate_extra()
                    man_now = man + np.array([float(_nx.get(a, 0.0)) for a in self.acts])
                    cap = np.zeros(Aa.shape[1]); cap[:n] = -need + sub_n * man_now
                    pc_ = getattr(self.ev, "pool_cols", []) or []
                    if len(pc_) == 2:
                        cap[pc_[0]] = -sub_n; cap[pc_[1]] = +sub_n
                    xb_ = np.maximum(self._base_levels().reindex(self.acts).fillna(0.0).values, 0.0)
                    v0 = float(cap[:n] @ xb_)
                    Aa = np.vstack([Aa, cap]); ba = np.concatenate([ba, [max(0.0, v0) + 1e-9 * max(1.0, float(need @ xb_))
                                                                         - self._cover_n_increment()]])
                    self.ev.need_row = Aa.shape[0] - 1
                    labels.append("crop_need")
        k_extra = alloc_k + pool_k
        allow = float(getattr(self, "grassland_allowance", 0.0))
        (tot_up, tot_lo), (b_tot_up, b_tot_lo) = e_artoBal(n + k + k_extra, n, k, L0)
        grs, b_grs = permGrasGreening_land(n + k + k_extra, n + li["GRAS"], L0[li["GRAS"]], allow)
        # TOTAL LAND IS CONSERVED (CAPRI's land-use balance: the land types add up to the region's
        # area). As an upper bound only, land leaving farming could vanish: under the nitrogen target
        # Brittany's land types fell from 2,328 to 1,495 kha, forest included. Now land leaving
        # farming goes to forest and other land, at the land market's own transformation costs.
        Aa = np.vstack([Aa, tot_up, tot_lo, grs])
        labels.extend(["land_total_up", "land_total_lo", "grassland_floor"])
        ba = np.concatenate([ba, [b_tot_up], [b_tot_lo], [b_grs]])
        Aa, ba = self._land_type_bounds(Aa, ba, labels, n, li, L0)
        # CAPRI LandBalNoSlak_ (supply_model.gms): for arable crops (ARAC), fruit and
        # nurseries (FRUN) and grassland (GRAS) the crops using a land type EQUAL the land
        # type's area - no idle land. Land leaves agriculture only through the land market
        # (its quadratic costs), never for free. As inequalities the rows let livestock
        # regions under the nitrogen target idle a third or more of their farmland (Ireland,
        # the Netherlands, Lombardy: -40 to -55%) against CAPRI's EU farmland +3%.
        # The equality holds at the BASE USE of each land type: the model's land data carry idle
        # land (availability above the crops' base area), which CAPRI's data do not, so the row
        # is  crops - land = base crops - base land,  i.e. a change in crops equals a change in
        # the land type. Holding it at the availability instead (an earlier version) forced the
        # base itself to fill or release idle land: the 2030 baseline never settled (land
        # updates of 0.004-0.006 for 25 iterations).
        extra_r, extra_b = [], []
        xb_ = np.concatenate([np.maximum(np.asarray(x0, dtype=float), 0.0), L0])
        for i, coeffs, const in rows:
            # (the base use never above the row's own limit: base crops exceed some regions' land data by
            # rounding, 0.002 kha in Brittany, and the pair of rows was then infeasible)
            # the upper row at the base use too: an equality, as CAPRI's LandBalNoSlak_. The grassland row kept the
            # land data's headroom above the base use (IE04 173 kha, NL13 6.5 kha): grass could grow onto it at no
            # land cost, and the base had no land rent for grass (its row slack, the lower row binding)
            up_b, lo_r, lo_b = LandBalNoSlak_baseUse(Aa[i], const, xb_, n, k)
            extra_r.append(lo_r); extra_b.append(lo_b)
            ba[i] = up_b
        if extra_r:
            Aa = np.vstack([Aa] + extra_r); ba = np.concatenate([ba, extra_b])
            labels.extend([labels[i] + "_lo" for i, _c, _k in rows])
        Aa = self._obligatory_set_aside(Aa, labels, n)
        self.ev.land_types_used = list(self.LAND_TYPES)
        start = np.concatenate([x0, L0] + ([np.array([getattr(self.ev, "alloc_m0", 0.0)])] if alloc_k else [])
                               + ([np.zeros(pool_k)] if pool_k else []))
        Qa, ca, Aa, ba, start = self._dairy_intensity_column(Qa, ca, Aa, ba, start, labels, n)
        Qa, ca, Aa, ba, start = self._histosol_columns(Qa, ca, Aa, ba, start, labels, n,
                                                       land_cols={t: n + j for t, j in li.items()})
        Qa, ca, Aa, ba, start = self._mix_columns(Qa, ca, Aa, ba, start, labels, n)   # CAPRI's T1/T2
        Qa, ca, Aa, ba, start = self._entitlement_columns(Qa, ca, Aa, ba, start, labels, n)   # K136: def_endCut
        self.ev.aug_labels = labels              # one label per row of the augmented problem (the NLP form reads them)
        return Qa, ca, Aa, ba, start, rows
