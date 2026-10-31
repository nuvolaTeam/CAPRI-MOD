"""Mitigation in the regional model: the ammonia technologies, manure techniques and inhibitors, the winter cover (catch crops), the GHG price terms, histosol fallowing.

RegionalSupplyModel's methods, moved unchanged from capri_mod/supply/supply_module.py (refactor stage 3a,
docs/design/ARCHITECTURE_REFACTOR.md); the module-level names they use are supply_module's, given to
this module once supply_module is loaded (capri_mod.utils.mixins.inject_names); the annotations are not evaluated
(they name supply_module's types).
"""
from __future__ import annotations


class AbatementBlock:
    def _techs_inside(self) -> bool:
        """CAPRI's ammonia technologies are decision variables of the regional model (technologies on, rations
        available)."""
        return bool(getattr(self, "feed_rations", None) or {})

    def _amm_context(self):
        """(technology blocks per animal, manure N per unit, CAPRI NH3 share, substitution) or None."""
        techs = self._manure_techs()
        _mc = self._mctx()
        man_d = _mc["man_d"] if _mc else None
        env_ = getattr(self, "_env_for_surplus", None)
        if not techs or man_d is None or env_ is None:
            return None
        try:
            _sb = env_._substitution(self.data.region_id)
            sub = float(_sb[0]) if _sb else 0.0
            nh3 = (env_._nh3_factors().get(self.data.region_id) or {}).get("manure_share", {})
        except Exception as _exc:
            import warnings as _w
            _w.warn(f"manure technologies skipped for {self.data.region_id}: {_exc!r}")
            return None
        return techs, man_d, nh3, sub

    @staticmethod
    def _amm_scale(subs, mN, f):
        """N (t per activity unit of the sub-activity) per unit of the loss fraction: CAPRI's
        NH3 share of excreted N (its 2030 run, which embodies the base shares) over the loss
        the cascade gives at the base shares, so the accounts match at base."""
        from capri_mod.supply import ammonia_techs as _at
        if subs and all(_at.cascade_data(s) is not None for s in subs):
            # CAPRI's full cascade (n_cascade.py) gives CAPRI's losses per unit of excreted N as they are (checked
            # against its Green Deal reference run): the N per unit of the loss fraction is the manure N itself
            return mN
        L0 = sum(s["w"] * s["mrel"] * _at.loss(s, _at.initial(s)) for s in subs)
        return (mN * f / L0) if L0 > 0 else 0.0

    def _amm_incentive(self, labels) -> bool:
        return ("N_balance" in labels or "mineral_N" in labels
                or float(getattr(self, "ghg_tax", 0.0) or 0.0) > 0)

    def _catc_spec(self):
        """The winter cover option of this region for the NLP form ({"uaa", "m0", "lb", "ub", "k1", "lin", "sqr",
        "biofix", "row", "rhs"}), or None (switch off, outside the EU, no data). UAAR: the region's base crop area
        (CAPRI's data UAAR, fixed); lb: the Farm-to-Fork requirement's share (e_minCoverCrops), set by the caller in
        the simulation; the winterCover_ row: sum_c winter cover share_c x crop_c + m x UAAR <= UAAR + fallow floor
        (supply_model.gms l. 1979-1992), its right-hand side at least the base point's (REGISTERED: CAPRI's MaxShare
        is from CAPRI's crop levels, the row from the model's)."""
        if not is_eu(self.data.region_id):
            return None
        opt = _inputs.current().cached(                                   # a missing file is an error (K74)
            "winter_cover_option", lambda inp: inp.csv("winter_cover_option.csv", "abatement/mitigation").set_index("region"))
        cc = getattr(self.data, "cover_crops", None)
        wcs = getattr(self.data, "winter_cover_share", None)
        reg = self.data.region_id
        if reg not in opt.index or cc is None or wcs is None or str(opt.at[reg, "case"]) == "none":
            return None
        base = self._base_levels()
        uaa = float(sum(float(base.get(c, 0.0) or 0.0) for c in CROPS if c in base.index))
        if uaa <= 0:
            return None
        bf = cc.get("biofix_t_n_ha")
        bf = float(bf) if bf is not None and not pd.isna(bf) else 0.0
        m0 = float(opt.at[reg, "ini_share"])
        row = [(j, float(wcs.at[a, "share"])) for j, a in enumerate(self.acts) if a in wcs.index and float(wcs.at[a, "share"]) > 0]
        cov0 = sum(float(base.get(self.acts[j], 0.0) or 0.0) * s for j, s in row)
        rhs = max(uaa + float(getattr(self, "_fall_floor", 0.0) or 0.0), cov0 + m0 * uaa)
        # the upper bound CAPRI's MaxShare (supply/set_miti_bounds.gms l. 30-34; K74, 29 October 2026: was
        # max(MaxShare, IniShare), the same in every unit, none has its initial share above the maximum)
        return {"uaa": uaa, "m0": m0, "lb": 0.0, "ub": float(opt.at[reg, "max_share"]),
                "k1": float(opt.at[reg, "cost_lin_eur_ha"]), "lin": float(opt.at[reg, "pmp_lin"]),
                "sqr": float(opt.at[reg, "pmp_sqr"]), "biofix": bf, "row": row, "rhs": rhs,
                "potential": max(0.0, uaa - cov0)}

    def _nlp_abatement_spec(self, labels):
        """CAPRI's abatement options for the NLP form (ghgAbatement; capri-mod: the manure techniques with feeding inside):
        the ammonia options with their loss cascade, the fertiliser options (regional shares) on the crops' mineral N,
        the nitrification inhibitor on manure. {} where off."""
        out = {}
        if not self._techs_inside():
            return out
        _cs = self._catc_spec()
        if _cs is not None:
            out["catc"] = _cs
        ctx = self._amm_context()
        techs = self._tech_list()
        if ctx is not None and techs:
            subs, man_d, nh3, sub = ctx
            sc = {a: self._amm_scale(ss, float(man_d.get(a, 0.0) or 0.0), float(nh3.get(a, 0.0) or 0.0))
                  for a, ss in subs.items() if a in self.acts}
            out["amm"] = {"techs": techs, "subs": subs, "sc": sc, "wc": self._winter_cover_shares()}
        _tl = getattr(self, "_fert_techs_all", None) or []
        if _tl:
            ft = [(nm_, nmin_, a_, b_, smx_) for (nm_, nmin_, a_, b_, s0_, smx_) in _tl]
            mr = self._crop_mineral_now()
            cr = [(list(self.acts).index(c_), v_) for c_, v_ in mr.items() if c_ in self.acts and v_ > 0]
            if ft and cr:
                out["fert_tech"] = {"crops": cr, "techs": ft, "ecap": fert_efficiency_cap(self.data.region_id)}
        if self._ni_inside():
            nip = self._manure_inhibitor_params()
            if nip is not None:
                al = list(self.acts)
                out["mni"] = {"w": [(al.index(a_), float(m_)) for a_, m_ in nip["man_d"].items()
                                    if a_ in self.acts and float(m_ or 0.0) > 0],
                              "nman": float(nip["nman"]), "smax": nip["smax"], "S0": nip["S0"], "slope": nip["slope"],
                              "vtax": nip["v_tax"]}
                self._nlp_nip = nip
        return out

    def _nlp_tax_terms(self, tax, c, abat):
        """CAPRI's emission tax (ghgTax) in the NLP form, where mineral N is the fertilisation block's purchases
        (v_netPutQuant(NITF)): the soil N2O of mineral N is taxed on the purchases, so every term of the former conic form
        that priced mineral N through a fixed substitution comes out. The activities' own coefficients (ghg_tax.py, finite
        differences of the accounts at the baseline) need no change: the baseline of the NLP form hands the accounts its
        purchases (mineral_n_alloc), which they hold fixed, so those coefficients carry no mineral N2O.
          purchases        tax x (direct + volatilised x indirect) per t N; with the nitrification inhibitor the
                           accounts' side-effect factor on its share of mineral N
          manure trade     the export and import columns lose the tax on the mineral N they were taken to move
          ammonia options  their manure N2O through the cascade and the indirect N2O of the NH3
                           they keep; not the mineral N it displaces (purchases)
          inhibitor on manure  the tax value per t of manure N treated without the mineral N it displaces
        Returns (ghg_min for the NLP spec, c)."""
        from capri_mod.environmental.environmental_module import GWP_N2O
        k = 44.0 / 28.0 * GWP_N2O
        # CAPRI's N2OSYN and the mineral part of N2OAMM from the region's MITERRA fractions, as the accounts take them
        # (_mineral_n2o_parts; until 31 October 2026 IPCC's EF1 and 10% x EF4 here while the accounts had moved to
        # MITERRA on 27 October, KNOWN_ISSUES K107)
        dn_, dv_ = self._mineral_n2o_parts()
        ef_d, ef_v = dn_ * k, dv_ * k
        out = {"d": tax * ef_d / 1000.0, "v": tax * ef_v / 1000.0, "nitr": None,
               "l": tax * self._ef_mineral_lea() / 1000.0}
        l2 = fert_side_value(self.data.region_id, "NITR_INH", "N2OSYN")
        l3 = fert_side_value(self.data.region_id, "NITR_INH", "NH3SYN")
        if l2 is not None and l3 is not None:
            out["nitr"] = (float(l2), float(l3))
        c = np.asarray(c, float).copy()
        pc = getattr(self, "_pool_cols", None) or []
        if len(pc) == 2:
            g_ = tax * float(getattr(self, "_pool_avail", 0.0) or 0.0) * (self._ef_mineral_n2o() + self._ef_mineral_lea()) \
                / 1000.0
            if pc[0] < len(c):
                c[pc[0]] -= g_                       # export: paid the mineral N it was taken to buy
            if pc[1] < len(c):
                c[pc[1]] += g_                       # import: credited the mineral N it was taken to save
        if abat.get("amm"):
            abat["amm"]["tax_nh3"] = tax * self._ef_nh3_n2o() / 1000.0
        nip = getattr(self, "_nlp_nip", None)
        if abat.get("mni") and nip is not None:
            abat["mni"]["vtax"] = float(abat["mni"]["vtax"]) - tax * float(nip["sub"]) * float(nip["nman"]) \
                * self._ef_mineral_n2o()
        return out, c

    def _cover_n_increment(self) -> float:
        """N (t) from the catch crops added by the Farm-to-Fork requirement: increment (1000 ha)
        x CAPRI's BioFix (t N per ha) x 1000."""
        cv = getattr(self, "_cover", None)
        return float(cv["delta"]) * float(cv["biofix"]) * 1000.0 if cv else 0.0

    def _cover_crop_requirement(self, reduction: float, organic_share) -> None:
        """CAPRI's minimum catch-crop area under the Farm-to-Fork targets (e_minCoverCrops).

        pol_input/greendeal/organic_io.gms (coverCrop 50%) and conventional_io.gms (coverCrop =
        pesticide cut / 2, on the remaining target): with o the region's organic area target and
        r the pesticide cut (shares),
            minimum CATC = [0.5 o + 0.5 max(0, r - o)] x (UAAR - sum_c crop_c x winter cover share_c)
                           + baseline CATC
        CAPRI subtracts the area under winter cover with p_winterCoverShare0, the shares as given
        (NUTS2 entries for Austria and a few German regions only); elsewhere nothing is subtracted
        and the requirement exceeds the area that can carry a catch crop (its own winterCover_ row,
        with the filled shares) in 100 regions, an infeasible pair. REGISTERED: the filled shares
        (NUTS2 <- member state <- EU, define_greening_limits.gms) in both, and the requirement capped
        at that potential area at base. Sets self._cover: requirement and increment (1000 ha),
        UAAR, catch-crop N per ha and cost per ha."""
        cc = getattr(self.data, "cover_crops", None)
        wcs = getattr(self.data, "winter_cover_share", None)
        if cc is None or wcs is None or reduction <= 0:
            return
        base = self._base_levels()
        uaa = float(sum(float(base.get(c, 0.0) or 0.0) for c in CROPS if c in base.index))
        if uaa <= 0:
            return
        covered = sum(float(base.get(c, 0.0) or 0.0) * float(wcs.at[c, "share"])
                      for c in wcs.index if c in base.index)
        targets = getattr(self.data, "organic_targets_pp", None)
        o = 0.0
        if organic_share:
            v = targets.get("uaa_pp") if (targets is not None and hasattr(targets, "get")) else None
            o = (float(v) / 100.0 * max(0.0, (100.0 * float(organic_share) - 12.0) / 13.0) if v is not None and not pd.isna(v)
                 else max(0.0, float(organic_share) - self._organic_baseline()))
        f = 0.5 * o + 0.5 * max(0.0, reduction - o)
        c0 = float(cc.get("catc_share_2030", 0.0) or 0.0) * uaa
        pot = max(0.0, uaa - covered)
        req = min(f * pot + c0, max(pot, c0))
        bf = cc.get("biofix_t_n_ha")
        self._cover = {"req": req, "delta": max(0.0, req - c0), "base": c0, "uaa": uaa, "potential": pot,
                       "biofix": float(bf) if bf is not None and not pd.isna(bf) else 0.0,
                       "cost": float(cc.get("catc_cost_eur_ha", 0.0) or 0.0)}

    def _manure_techs(self):
        """CAPRI's ammonia technologies for this region: {animal: [sub-activity block]}
        (capri_data/2017/abatement/ammonia/ammonia_tech_model.csv, capri_mod/supply/ammonia_techs.py)."""
        from capri_mod.supply import ammonia_techs as _at
        techs = _at.load(_inputs.current().path("ammonia_tech_model.csv", "abatement/ammonia")).get(self.data.region_id, {})
        # Cost basis (KNOWN_ISSUES K63): CAPRI prices the options per animal place, places = v_actLevl x DAYS / 365
        # (GHG_Mit_Cost_), and stock_factor is DAYS / 365 per unit of CAPRI's activity level. The model's animal units
        # are its own heads (capri_level_ratio = model heads per CAPRI level unit: fattening pigs ~0.5, bulls ~0.4,
        # heifers ~0.2, poultry 250-1000), while the N an option saves is per model head (manure N per head). Places
        # per model head are therefore stock_factor / ratio; before 21 October 2026 the cost used stock_factor per
        # model head, so per unit of N saved the options of those animals cost ratio x CAPRI's (fattening pigs about
        # half, poultry 250-1000 times). Copies: _at.load's table is shared.
        rat = getattr(self.data, "capri_level_ratio", None)
        if techs and rat is not None:
            out = {}
            for a, subs in techs.items():
                r_ = rat.get(a) if hasattr(rat, "get") else None
                r_ = float(r_) if r_ is not None and r_ == r_ and float(r_) > 0 else 1.0
                out[a] = [dict(s_, stock=float(s_["stock"]) / r_) for s_ in subs] if r_ != 1.0 else subs
            return out
        return techs

    def _winter_cover_shares(self):
        """(base, current) winter cover share of the region, CAPRI's v_Miti(CATC, WinterCov): the 2030 catch-crop share
        (cover_crops.csv catc_share_2030, CAPRI's value) and, under the Farm-to-Fork catch-crop requirement, the required
        area over UAAR (self._cover)."""
        cc = getattr(self.data, "cover_crops", None)
        w0 = 0.0
        if cc is not None and hasattr(cc, "get"):
            v = cc.get("catc_share_2030")
            w0 = float(v) if v is not None and not pd.isna(v) else 0.0
        if getattr(self, "_wc_solved", None) is not None:
            return w0, float(self._wc_solved)                     # chosen in the NLP form
        cv = getattr(self, "_cover", None)
        w1 = float(cv["req"]) / float(cv["uaa"]) if cv and float(cv.get("uaa", 0.0) or 0.0) > 0 else w0
        return w0, w1

    def _amm_record(self, shares: dict):
        """Accounts for given shares {(animal, sub): {tech: share}} (missing: base shares):
        N relief and NH3 saved per activity unit, extra cost per unit, reported shares (share
        of the animal's units) and the shares for the next linearisation."""
        from capri_mod.supply import ammonia_techs as _at
        self._animal_n_relief, self._animal_nh3_saved, self._manure_tech_shares = {}, {}, {}
        self._animal_n_kept = {}
        self._amm_cost = {}
        ctx = self._amm_context()
        if ctx is None:               # no N balance this solve: base shares, for reporting
            for a, subs in self._manure_techs().items():
                if a in self.acts:
                    for s in subs:
                        for t in s["techs"]:
                            k = (a, t["tech"])
                            self._manure_tech_shares[k] = self._manure_tech_shares.get(k, 0.0) + s["w"] * t["ini"]
            return
        techs, man_d, nh3, sub = ctx
        wc0, wc1 = self._winter_cover_shares()
        last = {}
        for a, subs in techs.items():
            mN, f = float(man_d.get(a, 0.0) or 0.0), float(nh3.get(a, 0.0) or 0.0)
            if a not in self.acts or mN <= 0 or f <= 0:
                continue
            sc = self._amm_scale(subs, mN, f)
            saved = cost = nh3s = 0.0
            for s in subs:
                ini = _at.initial(s)
                sh = dict(ini); sh.update(shares.get((a, s["key"]), {}))
                last[(a, s["key"])] = sh
                # N kept in the manure (CAPRI's GasRunTot through the cascade) and the NH3 part of it
                saved += s["w"] * sc * s["mrel"] * (_at.loss(s, ini, wc0) - _at.loss(s, sh, wc1))
                nh3s += s["w"] * sc * s["mrel"] * (_at.nh3(s, ini, wc0) - _at.nh3(s, sh, wc1))
                cost += s["w"] * s["stock"] * _at.cost(s, sh)
                for t in s["techs"]:
                    k = (a, t["tech"])
                    self._manure_tech_shares[k] = self._manure_tech_shares.get(k, 0.0) + s["w"] * sh[t["tech"]]
            if abs(saved) > 0 or abs(nh3s) > 0:
                self._animal_n_relief[a] = sub * saved
                self._animal_n_kept[a] = saved
                self._animal_nh3_saved[a] = nh3s
            self._amm_cost[a] = cost
        self._amm_last = last

    def _apply_manure_techs(self, lam: float):
        """CAPRI's ammonia technologies, adopted under the N shadow price
        (docs/MITIGATION_IN_SUPPLY.md; CAPRI ammo_tech.gms + supply_model.gms).

        Per sub-activity, shares from CAPRI's first-order conditions (ammonia_techs.choose):
        marginal cost thresh + slope (s - ini) (CAPRI's calibrated kappa2 + gamma), marginal
        benefit lam x substitution factor x N saved per unit of share through the loss
        cascade; manure-management options share one limit (TotMit_, NH3MAN), application
        options another (NH3APP). Effects: the animal's N-row coefficient falls by sub x N
        saved; the extra cost per unit comes off its margin. At lam = 0 the base shares are
        recorded (for reporting)."""
        if self._techs_inside():
            return          # decided inside the regional model: keep its results
        from capri_mod.supply import ammonia_techs as _at
        ctx = self._amm_context()
        shares = {}
        if ctx is not None and lam and lam > 0:
            techs, man_d, nh3, sub = ctx
            for a, subs in techs.items():
                mN, f = float(man_d.get(a, 0.0) or 0.0), float(nh3.get(a, 0.0) or 0.0)
                if a not in self.acts or mN <= 0 or f <= 0:
                    continue
                sc = self._amm_scale(subs, mN, f)
                for s in subs:
                    shares[(a, s["key"])] = _at.choose(s, lam * sub, sc * s["mrel"])
        self._amm_record(shares)
        for a, c in (getattr(self, "_amm_cost", None) or {}).items():
            if c and a in self.net_revenues.index:
                self.net_revenues[a] = float(self.net_revenues[a]) - c

    def _apply_manure_inhibitor(self, lam: float):
        """CAPRI's nitrification inhibitors on applied manure (target N2OMAN, envind/ghgMiti.gms):
        manure N counts x (1 + share x NMAN) in the crop nutrient balance (NUTNED_), so the same
        crop need is met with less mineral N. NMAN as NMIN from QEmitt; restricted where
        over-fertilisation is low relative to the manure availability factor a (restMitFert):
        NMAN = 0 if x + 0.1 <= a, ((x + 0.1)/a - 1) ** 1.1 where smaller. Maximum share = 1 - the
        grazing share of manure N. Cost per tonne of manure N (GHG_Mit_Cost_: x v_ManureNPK),
        calibrated as the other options without farm-size curves (relSubs 1.2/0.2). Value per t
        of manure N: N-balance price x a x NMAN (the mineral N it replaces). Its share is separate
        from the mineral-fertiliser options (TotMitFertMan_), outside Tot_MitFert_.
        REGISTERED: the crop-need floor on mineral N keeps a x manure without the gain."""
        self._manure_ni_relief, self._manure_ni_nh3, self._manure_ni_share = {}, {}, 0.0
        if self._ni_inside():
            return                       # decided inside the regional model
        tax = float(getattr(self, "ghg_tax", 0.0) or 0.0)
        lam = float(lam or 0.0)
        if lam <= 0 and tax <= 0:
            return
        P = self._manure_inhibitor_params()
        if P is None:
            return
        sub, nman, smax, S0, slope, app_nh3, v_tax, man_d = (P[k] for k in (
            "sub", "nman", "smax", "S0", "slope", "app_nh3", "v_tax", "man_d"))
        v = 1000.0 * lam * sub * nman + v_tax                # EUR per t of manure N
        sh = min(max((v - S0) / slope, 0.0), smax)
        if sh <= 0:
            return
        c_t = S0 * sh + 0.5 * slope * sh * sh               # EUR per t of manure N
        for a in self.acts:
            mN = float(man_d.get(a, 0.0) or 0.0)
            if mN <= 0:
                continue
            self._manure_ni_relief[a] = sub * nman * sh * mN
            if a in self.net_revenues.index:
                # option cost; under the emission tax the tax saved per head at this share (the animal's own
                # coefficient is taken at no adoption) - the N value reaches the animal through the N row instead
                self.net_revenues[a] = float(self.net_revenues[a]) - (c_t - v_tax * sh) * mN / 1000.0
            if a in app_nh3:
                self._manure_ni_nh3[a] = sh * app_nh3[a]      # t NH3-N per activity unit
        self._manure_ni_share = sh

    def _ni_inside(self) -> bool:
        """Inhibitors on manure as a decision of the regional model (no N-price search)."""
        return self._techs_inside()

    def _manure_inhibitor_params(self):
        """The parameters of CAPRI's inhibitor on manure for this region (see _apply_manure_inhibitor), or None:
        sub, nman, smax, S0, slope (EUR per t of manure N), app_nh3 (t NH3-N per activity unit at full adoption),
        v_tax (EUR per t of manure N treated), man_d (t manure N per activity unit)."""
        tax = float(getattr(self, "ghg_tax", 0.0) or 0.0)
        # national entry (fert_options_jul15.csv is keyed by CAPRI codes)
        _ms = capri_ms(self.data.region_id)
        ni = next((t for t in fert_option_table().get(_ms, []) if str(t.option).upper() == "NITR_INH"), None)
        act_ = active_technologies()
        if ni is None or (act_ is not None and "NITR_INH" not in act_):
            return
        ctx = self._amm_context()
        if ctx is None:
            return
        techs, man_d, nh3, sub = ctx
        if sub <= 0:
            return
        q0, k1 = float(ni.QEmitt_noc), float(ni.costParLin)
        q = 0.9 * q0            # ghgMiti.gms l. 110: QEmitt(NITR_INH) = 0.9 x QEmitt(NOC), also for N2OMAN
        if not (q > 0 and q0 > q and k1 > 0):
            return
        nman = (q0 / q - 1.0) ** P_FERT_EFF_COR
        x = overfert_factor(self.data.region_id)
        if x is not None:
            cap = x + OVERFERT_MARKUP
            if cap <= sub:
                return
            if cap < (nman ** (1.0 / P_FERT_EFF_COR) + 1.0) * sub:
                nman = (cap / sub - 1.0) ** P_FERT_EFF_COR
        # maximum share: manure N not dropped on pasture (grazing shares of the ammonia data)
        base = self._base_levels()
        tot = graz = 0.0
        for a, subs in techs.items():
            if a not in self.acts:
                continue
            mn = float(man_d.get(a, 0.0) or 0.0) * float(base.get(a, 0.0) or 0.0)
            g = sum(s_["w"] * s_["g"] for s_ in subs)
            tot += mn; graz += mn * g
        smax = 1.0 - graz / tot if tot > 0 else 0.0
        if smax <= 0:
            return
        S0, slope = 0.2 * k1, k1 * (1.2 - 0.2) / smax
        if SupplyModule.fert_slope_with_saving:
            # CAPRI's pmpParSqr of the inhibitor on manure (envind/ghgMiti.gms l. 1036-1050), as the mineral options'
            # (_fert_techs, the same switch): + nmE x p_manureShadVal x ((1 + nmE m1)^-2 - (1 + nmE m0)^-2) / (m1 - m0),
            # m0 = IniShare 0, m1 = MaxShare; nmE = NMAN (EmiCalman is commented out in CAPRI, l. 945-958);
            # p_manureShadVal = the member state's unit value of mineral N x the region's availability of excreted
            # manure N (v_nutAvailFactExcr, l. 871; npk_region_2030.csv excr_avail)
            from capri_mod.fert.npk import NPKData as _NPK
            _npk = _NPK.get()
            _t = _npk.region(_npk.capri_region(self.data.region_id) or self.data.region_id, "N")
            _av = getattr(_t, "excr_avail", None) if _t is not None else None
            _pf = SupplyModule._nitf_price_ms(_ms)
            if _pf and _av is not None and _av == _av:
                slope += saving_slope(nman, _pf * float(_av), 0.0, smax)
        # application NH3 side effect (ghgMiti.gms l. 557-563, p_litRevFertTechs NH3APP): on
        # treated manure the application emission factor is (1 - lit) x (1 + NMAN) times
        # NOC's; base = the cascade's application loss at the ammonia options' latest shares
        from capri_mod.supply import ammonia_techs as _at
        lit = fert_side_value(self.data.region_id, "NITR_INH_MAN", "NH3APP")
        f_app = ((1.0 - lit) * (1.0 + nman) - 1.0) if lit is not None else 0.0
        last = getattr(self, "_amm_last", None) or {}
        app_nh3 = {}                                         # t NH3-N per activity unit at full adoption
        for a in self.acts:
            mN = float(man_d.get(a, 0.0) or 0.0)
            if mN > 0 and f_app and a in techs and float(nh3.get(a, 0.0) or 0.0) > 0:
                subs = techs[a]
                sc = self._amm_scale(subs, mN, float(nh3[a]))
                app = sum(s_["w"] * sc * s_["mrel"] * _at.app_loss(s_, last.get((a, s_["key"]), _at.initial(s_)),
                                                                    self._winter_cover_shares()[1])
                          for s_ in subs)
                app_nh3[a] = f_app * app
        v_tax = self._manure_inhibitor_tax_value(tax, sub, nman, man_d, app_nh3, base) if tax > 0 else 0.0
        return {"sub": sub, "nman": nman, "smax": smax, "S0": S0, "slope": slope, "app_nh3": app_nh3,
                "v_tax": v_tax, "man_d": man_d}

    def _manure_inhibitor_tax_value(self, tax, sub, nman, man_d, app_nh3, base) -> float:
        """CAPRI's emission tax on inhibitors on manure (Sprint 9m): EUR per t of manure N treated, the tax on the
        emissions it saves, as the accounts count them - (1) the mineral N it displaces (sub x NMAN per t) at the soil
        N2O factor; (2) application N2O x CAPRI's literature effect N2OAPP (EnvironmentalModule: fa x (1 - share x
        lit)), from the animals' application factor per t of excreted N; less (3) the indirect N2O of the extra
        application NH3 (NH3APP). Weighted over the region's animals by their base manure N (REGISTERED: weights and the
        ammonia cascade multiplier on application N2O held at base)."""
        from capri_mod.environmental.environmental_module import EF_SOIL_N2O_INDIRECT, GWP_N2O
        env_ = getattr(self, "_env_for_surplus", None)
        k = 44.0 / 28.0 * GWP_N2O
        v = sub * nman * self._ef_mineral_n2o()
        lit2 = fert_side_value(self.data.region_id, "NITR_INH_MAN", "N2OAPP")
        tot = n2o = nh3x = 0.0
        for a in self.acts:
            mN = float(man_d.get(a, 0.0) or 0.0); x = float(base.get(a, 0.0) or 0.0)
            if mN <= 0 or x <= 0:
                continue
            tot += mN * x
            nh3x += float(app_nh3.get(a, 0.0)) * x
            if lit2 and env_ is not None:
                try:
                    mf = env_._manure_n2o_factor(self.data.region_id, a)
                    ex = float(env_._n_excretion(self.data.region_id, a))          # kg N per head = t per 1000 heads
                except Exception:
                    mf, ex = None, 0.0
                if mf is not None:
                    n2o += float(mf[1]) * ex * x
        if tot <= 0:
            return 0.0
        v += (float(lit2 or 0.0) * n2o / tot) * k
        v -= (nh3x / tot) * EF_SOIL_N2O_INDIRECT * k
        return tax * v

    # ------------------------------------------------------------------------------------------
    # CAPRI's emission tax (ghgTax, Sprint 9i; capri_mod/supply/ghg_tax.py): EUR per t CO2-eq times each
    # column's emission per unit at the baseline; set by CAPRIModel (ghg_tax, ghg_coef) for EU regions
    # ------------------------------------------------------------------------------------------
    def _ghg_cost(self, kind, key=None) -> float:
        tax = float(getattr(self, "ghg_tax", 0.0) or 0.0)
        co = getattr(self, "ghg_coef", None)
        if tax <= 0 or not co:
            return 0.0
        v = co.get(kind)
        if key is not None:
            v = (v or {}).get(key, 0.0)
        return tax * float(v or 0.0)

    def _apply_ghg_tax(self) -> None:
        """Activities: net revenue - tax x emission per ha or head (CAPRI's objective term)."""
        # net revenues not rebuilt since the last application (same object): take that one back first
        prev = getattr(self, "_ghg_applied", None)
        if prev and getattr(self, "_ghg_nr_obj", None) is self.net_revenues:
            for a, d in prev.items():
                self.net_revenues[a] = float(self.net_revenues[a]) + d
        self._ghg_applied = {}
        self._ghg_nr_obj = self.net_revenues
        tax = float(getattr(self, "ghg_tax", 0.0) or 0.0)
        co = getattr(self, "ghg_coef", None)
        if tax <= 0 or not co:
            return
        for a, e in (co.get("act") or {}).items():
            if a in self.net_revenues.index:
                d = tax * float(e)
                self.net_revenues[a] = float(self.net_revenues[a]) - d
                self._ghg_applied[a] = d

    def _ghg_feed_cost(self):
        """Flexible feeds: tax x emission per t fed, in the regional objective's EUR/kg units ({(animal, feed)})."""
        tax = float(getattr(self, "ghg_tax", 0.0) or 0.0)
        co = getattr(self, "ghg_coef", None)
        if tax <= 0 or not co or not co.get("feed"):
            return None
        return {k: tax * float(e) / 1000.0 for k, e in co["feed"].items()}

    def _histosol_base_area(self, cls):
        base = self._base_levels()
        if cls == "crop":
            return float(sum(float(base.get(c, 0.0) or 0.0) for c in CROPS if c != "GRAS" and c in base.index))
        return float(base.get("GRAS", 0.0) or 0.0)

    def _histosol_columns(self, Qa, ca, Aa, ba, start, labels, n):
        """CAPRI's histosol fallowing (no_histosols.gms, idleHisto_), one column per class: F = 1000 ha of
        histosol cropland (iHisCr) or grassland (iHisGr) idled. It still occupies its land (arable or
        grassland row +1); 0 <= F <= MaxShare x share x base area of the class (base area fixed:
        REGISTERED); cost CAPRI's curvature 0.5 pmpParSqr F^2 / H per ha of histosol area H; linear term
        from the base dual of the land row (F = 0 optimal at base, CAPRI's IniShare 0), so fallowing
        rises where the land rent falls - CAPRI's calibration does the same with its own rent in
        costsaving0. Its N2O (and CO2, CH4) on the idled area stop (QEmitt = 1 - p_ghgTechHisto = 0)."""
        self._hist_cols = {}
        h = getattr(self.data, "histosol", None)
        if h is None or not hasattr(h, "get"):
            return Qa, ca, Aa, ba, start
        cal = getattr(self, "_hist_cal", None)
        pend = {}
        for cls, row_lab in self.HISTOSOL_CLASSES:
            sqr, sh, mx = h.get(f"pmp_sqr_{cls}"), float(h.get(f"share_{cls}", 0.0) or 0.0), h.get(f"maxshare_{cls}")
            if row_lab not in labels or sqr is None or pd.isna(sqr) or not (float(sqr) > 0) or sh <= 0 or mx is None or pd.isna(mx):
                continue
            H = sh * self._histosol_base_area(cls)
            if H <= 1e-6:
                continue
            col = np.zeros(Aa.shape[0]); col[labels.index(row_lab)] = 1.0
            if row_lab + "_lo" in labels:
                # the land row is an equality (CAPRI LandBalNoSlak_: the crops and the idled histosol area together
                # equal the land type): with F on the upper row alone, crops + F <= land <= crops held F at zero
                # wherever the pair is tight (arable and permanent land always) - no histosol was ever fallowed
                col[labels.index(row_lab + "_lo")] = -1.0
            if "landscape_floor" in labels:
                # idled histosols count towards the Biodiversity Strategy's set-aside and landscape target
                # (supply_model.gms e_setaLandscape_: setaFallow includes iHisCr and iHisGr)
                col[labels.index("landscape_floor")] = -1.0
            if cal is None or cls not in cal:
                pend[cls] = col
                continue
            Aa = np.hstack([Aa, col[:, None]])
            up = np.zeros(Aa.shape[1]); up[-1] = 1.0
            Aa = np.vstack([Aa, up]); ba = np.concatenate([ba, [float(mx) * H]])
            labels.append(f"hist_{cls}_up")
            Qa = np.pad(Qa, ((0, 1), (0, 1))); Qa[-1, -1] = float(sqr) / H
            ca = np.concatenate([ca, [cal[cls] + self._ghg_cost('hist', cls)]])
            start = np.concatenate([start, [0.0]])
            self._hist_cols[cls] = Aa.shape[1] - 1
        self._hist_pending = pend or None
        return Qa, ca, Aa, ba, start

    def _histosol_calibrate_from_duals(self, duals):
        pend = getattr(self, "_hist_pending", None)
        if not pend:
            return
        cal = dict(getattr(self, "_hist_cal", None) or {})
        if duals is not None:
            for cls, col in pend.items():
                if len(duals) >= len(col):
                    cal[cls] = -float(np.asarray(duals[:len(col)], float) @ col)
        self._hist_cal = cal
        self._hist_pending = None
