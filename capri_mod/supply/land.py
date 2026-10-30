"""Land in the regional model: CAPRI's land market (the land types as variables, Trustee_land).

RegionalSupplyModel's methods, moved unchanged from capri_mod/supply/supply_module.py (refactor stage 3a,
docs/design/ARCHITECTURE_REFACTOR.md); the module-level names they use are supply_module's, given to
this module once supply_module is loaded (capri_mod.utils.mixins.inject_names); the annotations are not evaluated
(they name supply_module's types).
"""
from __future__ import annotations


class LandBlock:
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

    def _land_augment(self, A_ub, b_ub, c_lin, x0):
        """Augment the regional QP with CAPRI's land market (LandMarket_,
        trustee-land variant): land-type areas L as variables, cost 1/2 L'Q L
        (p_pmpQuadLandTypes) with constants making the base areas optimal; land
        rows become  activities - land <= base limit - base land, i.e. exactly
        the current rows at base; total land <= base total; grassland >= (1 -
        allowance) x base (CAPRI Green Deal default allowance 0%). Returns None
        where the region has no land-market data."""
        self._need_row = None
        self._nrow_land = None
        lm = getattr(self.data, "land_market", None)
        if not lm or "quad" not in lm:
            return None
        labels = list(getattr(self, "_row_labels", []))
        LTall = ["ARAC", "GRAS", "FRUN", "FORE", "OLND", "ARTIF"]
        keep = [LTall.index(t) for t in self.LAND_TYPES]
        Qf = np.array(lm["quad"], dtype=float)[np.ix_(keep, keep)]
        # UNITS: CAPRI's land-market terms are per HECTARE, the model's land
        # variables in 1000 ha - hence x 1000. Verified: with observed land
        # rents the matrix then implies an arable land-supply elasticity of
        # median 0.062 (10th 0.010, 90th 0.334), the range of CAPRI's priors;
        # unscaled it implied a median of 62 and land converted far too easily.
        Qf = 1000.0 * 0.5 * (Qf + Qf.T) + 1e-9 * np.eye(len(keep))
        L0 = np.array([float(lm["base_kha"].get(t, 0.0)) for t in self.LAND_TYPES])
        n, k = len(x0), len(keep)
        Qa = np.zeros((n + k, n + k)); Qa[:n, :n] = self.Q; Qa[n:, n:] = Qf
        ca = np.concatenate([c_lin, -Qf @ L0])
        Aa = np.hstack([A_ub, np.zeros((A_ub.shape[0], k))]); ba = b_ub.astype(float).copy()
        li = {t: j for j, t in enumerate(self.LAND_TYPES)}
        rowmap = {"arable_land": [(li["ARAC"], 1.0)],
                  # CAPRI LandBalNoSlak_(GRAS): grassland activities = grassland. Arable fodder
                  # (MAIF, OFOD) sits on ARABLE land, in the arable row; see _build_constraints
                  "grassland": [(li["GRAS"], 1.0)],
                  "permanent_land": [(li["FRUN"], 1.0)]}
        rows = []
        for lab, coeffs in rowmap.items():
            if lab not in labels:
                continue
            i = labels.index(lab)
            const = float(b_ub[i]) - sum(cf * L0[j] for j, cf in coeffs)
            for j, cf in coeffs:
                Aa[i, n + j] -= cf
            ba[i] = const
            rows.append((i, coeffs, const))
        if not rows:
            return None
        # CAPRI takes the land rents as given in its calibration (supply/cal_land_nests.gms, prep_cal.gms l. 125-156):
        # at the 2030 calibration point the land market is balanced at CAPRI's rents, not at the model's recovered
        # duals (docs/LAND_RENT_CALIBRATION_PLAN.md)
        # Every land type with a level in CAPRI's region has a positive calibration rent (tools/build/build_land_rents.py
        # applies cal_land_nests.gms l. 204-226 where CAPRI's reported D_AREA is not positive). Before 23 October 2026
        # the base dual recovered from the model's own QP solution stood in at 2017 and for those cells at 2030; that QP
        # carried a 1% shadow-price proxy and a 15% grassland headroom (no proxies: removed). A land type without a
        # CAPRI rent has no level in CAPRI's region: rent 0.
        _rents = getattr(self.data, "land_rents", None)
        if _rents is None:
            raise ValueError(f"{self.data.region_id}: no CAPRI land rents for the land market (land_rents_<year>.csv)")
        _rlab = {"arable_land": "ARAC", "permanent_land": "FRUN", "grassland": "GRAS"}
        self._land_rent_rows = {}
        for lab, coeffs in rowmap.items():
            t_ = _rlab.get(lab)
            m_ = float(_rents.get(t_, 0.0)) if _rents.get(t_, 0.0) == _rents.get(t_, 0.0) else 0.0
            self._land_rent_rows[lab] = m_
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
                tgt_ = float(ba[i_nb_]) / base_area_
                lt_ = [t for t in ("ARAC", "GRAS", "FRUN") if t in li]
                for t in lt_:
                    Aa[i_nb_, n + li[t]] -= tgt_
                ba[i_nb_] -= tgt_ * float(sum(L0[li[t]] for t in lt_))
                # for a relaxed target (_relax_n_target): the land columns and base land
                self._nrow_land = ([n + li[t] for t in lt_], float(sum(L0[li[t]] for t in lt_)), tgt_)
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
        self._cover_dbf_nb = 0.0
        if "N_balance" in labels:
            srow = getattr(self, "_surplus_row", None)
            nmin = srow[2] if srow is not None and len(srow) > 3 else None
            upt = srow[3] if srow is not None and len(srow) > 3 else None
            ybase = srow[4] if srow is not None and len(srow) > 4 else None
            bser = srow[0] if srow is not None else None
            a_av, pf = self._fert_alloc_params()
            if nmin and upt and bser is not None and a_av and pf:
                i_nb = labels.index("N_balance")
                mint = getattr(self, "_n_intensity", {}) or {}
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
                    self._alloc_m0 = float(nmc @ np.maximum(x0, 0.0))
                    self._alloc_row = Aa.shape[0] - 1
                    k_extra = 1
                    # CAPRI's catch crops (NUTNED_ l. 1076, e_BIOFIX): their N is an input of the
                    # balance and supplies crop need, so mineral N may fall by as much
                    dbf = self._cover_n_increment()
                    if dbf > 0:
                        ba[i_nb] -= dbf
                        ba[self._alloc_row] += dbf
                        self._cover_dbf_nb = dbf          # (the NLP form's chosen catch crops replace it)
        alloc_k = k_extra
        self._alloc_cols = alloc_k
        self._pool_cols = []
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
        # Sprint 9k: in EVERY EU solve with manure trade on (CAPRI: e_netMTrade, e_costMTrade are in every run), not
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
                env_ = getattr(self, "_env_for_surplus", None)
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
                if man0 > 1e-6:
                    pp = float(getattr(self, "manure_pool_price", 0.0) or 0.0)
                    # CAPRI supply/define_manure_trade_costs.gms l. 66-71: p_manureBuyCostSlope = 50 / (GROF / 100), EUR
                    # 50 per t N for each 1% of the region's manure N supply traded. man0 is in t N (kg N per unit x
                    # 1000 units) and the objective in EUR 1000, so CAPRI's 50 is 0.05 here (supply.manure_pool_slope)
                    slope = float(_settings().get("supply.manure_pool_slope")) / (man0 / 100.0)
                    # emission tax: the mineral N bought (export) or saved (import), sub x the accounts' soil N2O
                    # factor and the indirect N2O of its runoff and leaching per t N (kt CO2-eq x EUR/t = 1000 EUR);
                    # the NLP form takes exactly this term out again (_nlp_tax_terms), mineral N being endogenous there
                    g_ = float(getattr(self, "ghg_tax", 0.0) or 0.0) * sub \
                        * (self._ef_mineral_n2o() + self._ef_mineral_lea()) / 1000.0
                    pcols = []
                    for sign in (-1.0, +1.0):                  # -1 export, +1 import
                        Qa = np.pad(Qa, ((0, 1), (0, 1))); Qa[-1, -1] = slope
                        ca = np.concatenate([ca, [(pp + g_) if sign < 0 else (-pp - g_)]])
                        Aa = np.hstack([Aa, np.zeros((Aa.shape[0], 1))])
                        if i_nb is not None:
                            Aa[i_nb, -1] = sign * (1.0 - sub)
                        if "mineral_N" in labels:
                            # mineral N: exported manure must be replaced (+sub), imported manure displaces it
                            Aa[labels.index("mineral_N"), -1] = -sign * sub
                        pcols.append(Aa.shape[1] - 1)
                    capr = np.zeros(Aa.shape[1]); capr[:n] = -e; capr[pcols[0]] = 1.0
                    Aa = np.vstack([Aa, capr]); ba = np.concatenate([ba, [0.0]])
                    labels.append("manure_export_cap")
                    self._pool_cols = pcols
                    self._manure_supply0 = man0
                    self._pool_manure_vec = e.copy()
                    self._pool_avail = sub
                    pool_k = 2
        # ---- MANURE WITHIN CROP NEED (CAPRI supply_model.gms fertDistExcr_ +
        # NUTNED_, an EQUALITY with mineral N >= 0; its over-application term is
        # commented out): a region can hold only as much manure as its crops can
        # use at their availability. As a row: mineral N still required >= 0,
        #   sum crops (current need x area) - sub x (manure + imports - exports) >= 0.
        # Without it importers absorbed unlimited paid manure and cut crops to
        # make room (cereal area -31% in importing regions). Regions already
        # beyond it at base are held at their base deficit. REGISTERED: applied
        # where the N target applies (CAPRI: always).
        # Sprint 9k: in every EU solve (CAPRI's NUTNED_ is in every run), not only under the N target
        _mc = self._mctx()
        if _mc is not None:
            nmin, ybase, man_d = _mc.get("nmin"), _mc.get("ybase"), _mc.get("man_d")
            env_ = getattr(self, "_env_for_surplus", None)
            if nmin and man_d is not None and env_ is not None:
                try:
                    sub_n = float(env_._substitution(self.data.region_id)[0])
                except Exception as _exc:
                    import warnings as _w
                    _w.warn(f"crop-need limit skipped for {self.data.region_id}: {_exc!r}")
                    sub_n = None
                if sub_n:
                    mint = getattr(self, "_n_intensity", {}) or {}
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
                    pc_ = getattr(self, "_pool_cols", []) or []
                    if len(pc_) == 2:
                        cap[pc_[0]] = -sub_n; cap[pc_[1]] = +sub_n
                    xb_ = np.maximum(self._base_levels().reindex(self.acts).fillna(0.0).values, 0.0)
                    v0 = float(cap[:n] @ xb_)
                    Aa = np.vstack([Aa, cap]); ba = np.concatenate([ba, [max(0.0, v0) + 1e-9 * max(1.0, float(need @ xb_))
                                                                         - self._cover_n_increment()]])
                    self._need_row = Aa.shape[0] - 1
                    labels.append("crop_need")
        k_extra = alloc_k + pool_k
        tot = np.zeros(n + k + k_extra); tot[n:n + k] = 1.0
        allow = float(getattr(self, "grassland_allowance", 0.0))
        grs = np.zeros(n + k + k_extra); grs[n + li["GRAS"]] = -1.0
        # TOTAL LAND IS CONSERVED (CAPRI's land-use balance: the land types add up to the region's
        # area). As an upper bound only, land leaving farming could vanish: under the nitrogen target
        # Brittany's land types fell from 2,328 to 1,495 kha, forest included. Now land leaving
        # farming goes to forest and other land, at the land market's own transformation costs.
        Aa = np.vstack([Aa, tot, -tot, grs])
        labels.extend(["land_total_up", "land_total_lo", "grassland_floor"])
        ba = np.concatenate([ba, [L0.sum() + 1e-9], [-L0.sum() + 1e-9 * max(1.0, L0.sum())],
                             [-(1.0 - allow) * L0[li["GRAS"]] + 1e-9]])
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
            scale = float(np.abs(Aa[i]).max()) if Aa[i].any() else 1.0
            # (never above the row's own limit: base crops exceed some regions' land data by
            # rounding, 0.002 kha in Brittany, and the pair of rows was then infeasible)
            used = min(float(Aa[i, :n + k] @ xb_), float(const))
            extra_r.append(-Aa[i].copy()); extra_b.append(-used + 1e-7 * max(1.0, abs(used)) + 1e-9 * scale)
            # the upper row at the base use too: an equality, as CAPRI's LandBalNoSlak_. The grassland row kept the
            # land data's headroom above the base use (IE04 173 kha, NL13 6.5 kha): grass could grow onto it at no
            # land cost, and the base had no land rent for grass (its row slack, the lower row binding)
            ba[i] = used + 1e-7 * max(1.0, abs(used)) + 1e-9 * scale
        if extra_r:
            Aa = np.vstack([Aa] + extra_r); ba = np.concatenate([ba, extra_b])
            labels.extend([labels[i] + "_lo" for i, _c, _k in rows])
        self._land_types_used = list(self.LAND_TYPES)
        start = np.concatenate([x0, L0] + ([np.array([getattr(self, "_alloc_m0", 0.0)])] if alloc_k else [])
                               + ([np.zeros(pool_k)] if pool_k else []))
        Qa, ca, Aa, ba, start = self._grass_intensity_column(Qa, ca, Aa, ba, start, labels, n, alloc_k)
        Qa, ca, Aa, ba, start = self._dairy_intensity_column(Qa, ca, Aa, ba, start, labels, n)
        Qa, ca, Aa, ba, start = self._histosol_columns(Qa, ca, Aa, ba, start, labels, n)
        self._aug_labels = labels              # one label per row of the augmented problem (the NLP form reads them)
        self._last_aug_A, self._last_aug_b = Aa, ba
        return Qa, ca, Aa, ba, start, rows
