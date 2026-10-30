"""Fertilisation and nitrogen in the regional model: CAPRI's NPK block (NUTNED_, the purchases, the organic and mineral caps, the fertiliser options), the emission factors of mineral N, the N balance price and tiered surplus target with JRC121368's relaxation, the nitrate terms.

RegionalSupplyModel's methods, moved unchanged from capri_mod/supply/supply_module.py (refactor stage 3a,
docs/design/ARCHITECTURE_REFACTOR.md); the module-level names they use are supply_module's, given to
this module once supply_module is loaded (capri_mod.supply.blocks.inject); the annotations are not evaluated
(they name supply_module's types).
"""
from __future__ import annotations


class FertilisationBlock:
    def _mctx(self):
        """CAPRI's crop nutrient balance terms for this solve: {"man_d": manure N per activity unit, "nmin": crops'
        base mineral N per ha, "ybase": base yields}, from the N target's row when the scenario has one, else from
        the context SupplyModule sets for every EU solve (CAPRI's NUTNED_ and manure market are in every run,
        Sprint 9k); None when neither is there."""
        srow = getattr(self, "_surplus_row", None)
        if srow is not None and len(srow) > 6:
            man_d = srow[6] if srow[6] is not None and hasattr(srow[6], "get") else None
            if man_d is not None:
                return {"man_d": man_d, "nmin": srow[2], "ybase": srow[4]}
        ctx = getattr(self, "_manure_ctx", None)
        return ctx if ctx and ctx.get("man_d") is not None else None

    def _ef_mineral_n2o(self) -> float:
        """t CO2-eq per t of mineral N in the accounts' soil N2O: CAPRI's N2OSYN + the mineral part of N2OAMM, from the
        region's MITERRA loss fractions (n_cascade.mineral_n2o_n; K74 S12, 27 October 2026: before, IPCC's EF1 + 10% x
        EF4 everywhere); IPCC's factors where CAPRI's fractions are missing (Norway: no cascade built, registered)."""
        c_ = self.__dict__.get("_ef_min_n2o_cache")
        if c_ is None:
            from capri_mod.environmental.environmental_module import (EF_SOIL_N2O_DIRECT, EF_SOIL_N2O_INDIRECT,
                                                                      GWP_N2O)
            from capri_mod.supply import n_cascade as _nc, n_leaching as _nl
            rs = _nl.capri_region(self.data.region_id)
            dn = _nc.mineral_n2o_n(_nc.load()[1].get(rs, {}), EF_SOIL_N2O_INDIRECT) if rs else None
            n2o_n = sum(dn) if dn else EF_SOIL_N2O_DIRECT + 0.10 * EF_SOIL_N2O_INDIRECT
            c_ = self.__dict__["_ef_min_n2o_cache"] = n2o_n * 44.0 / 28.0 * GWP_N2O
        return c_

    def _ef_mineral_lea(self) -> float:
        """t CO2-eq per t of mineral N bought in the indirect N2O of its runoff and leaching (CAPRI GWPN2OLEA_ a and c,
        capri_mod/supply/n_leaching.py): (RunTot_NETF + (1 - GasRunTot_NETF - EXPPRD/IMPORT) x L) x EF5 x 44/28, at the
        leaching share of CAPRI's Green Deal reference (REGISTERED: the options' effect on the share is in the accounts,
        not in this coefficient); 0 without CAPRI's data."""
        c_ = self.__dict__.get("_ef_lea_cache")
        if c_ is None:
            from capri_mod.supply import n_cascade as _nc, n_leaching as _nl
            from capri_mod.environmental.environmental_module import GWP_N2O
            rs = _nl.capri_region(self.data.region_id)
            d = _nl.load().get(rs) if rs else None
            g = _nc.load()[1].get(rs, {}) if rs else {}
            c_ = 0.0
            if d and d.get("exp_imp") is not None:
                L = d.get("leach_ini") if d.get("leach_ini") is not None else (d.get("leach_base") or 0.0)
                nf = _nc.netf(g, float(g.get("run_surf", 0.0)))
                c_ = max(0.0, nf["RunTot"] + (1.0 - nf["GasRunTot"] - float(d["exp_imp"])) * float(L)) \
                    * _nl.EF5 * 44.0 / 28.0 * GWP_N2O
            self._ef_lea_cache = c_
        return c_

    @staticmethod
    def _ef_nh3_n2o() -> float:
        """t CO2-eq per t of NH3-N volatilised from manure (the accounts' N2O_IND, CAPRI N2OAMM)."""
        from capri_mod.environmental.environmental_module import EF_SOIL_N2O_INDIRECT, GWP_N2O
        return EF_SOIL_N2O_INDIRECT * 44.0 / 28.0 * GWP_N2O

    def _need_yf(self, a, y0, yc, nut: str = "N") -> float:
        """The crop's nutrient need per ha at yield yc relative to its base yield y0, CAPRI's rule
        (capri_mod.fert.npk.need_yield_factor: the main-output part linear in the yield, the straw part with the
        scenario's yields before the price response)."""
        from capri_mod.fert.npk import need_yield_factor
        pf = float((getattr(self, "_yield_price_factor", None) or {}).get(a, 1.0))
        ys = float(yc) / pf if pf > 0 else None
        return need_yield_factor(self.data.region_id, a, float(y0), float(yc), ys, nut)

    def _yields_scen_now(self):
        """The crops' current yields without this solve's price response (the scenario's shifted yields), for the
        environmental accounts' need factors; None without a price response."""
        pf = getattr(self, "_yield_price_factor", None) or {}
        if not pf or not hasattr(self.data.yields, "get"):
            return None
        return {a: float(self.data.yields.get(a)) / f for a, f in pf.items()
                if f > 0 and self.data.yields.get(a) is not None}

    def _crop_mineral_now(self) -> dict:
        """Crops' mineral N per ha at this solve (kg N/ha): base rate x fertiliser intensity x CAPRI's need factor
        of the yield (`_need_yf`), the same terms the N row uses (`_mineral_row`), for the fertiliser options without
        an N row."""
        ctx = self._mctx() or {}
        ybase = ctx.get("ybase")
        mint = getattr(self, "_n_intensity", {}) or {}
        ycur = self.data.yields
        out = {}
        for a, v in (ctx.get("nmin") or {}).items():
            if a not in CROPS or a not in self.acts or not float(v or 0.0) > 0:
                continue
            _y0 = float(ybase.get(a, 0.0)) if (ybase is not None and hasattr(ybase, "get")) else 0.0
            _yc = float(ycur.get(a, _y0)) if hasattr(ycur, "get") else _y0
            _r = self._need_yf(a, _y0, _yc) if (_y0 > 0 and _yc > 0) else 1.0
            r_ = self._crop_mineral_rate(a) * float(mint.get(a, 1.0)) * _r
            if r_ > 0:
                out[a] = r_
        return out

    def _fert_tax_terms(self, ft) -> dict:
        """CAPRI's emission tax on mineral N and the fertiliser options (Sprint 9l), in the regional model's 1000 EUR:
        "m" per t of mineral N (the accounts' soil N2O, direct + volatilised x indirect, and the indirect N2O of its
        runoff and leaching, _ef_mineral_lea); "h" per unit of adopted area
        (1000 ha) per kg N/ha of need, by option. The accounts (EnvironmentalModule.fert_side_factors) count an option
        with CAPRI's literature side effects (p_litRevFertTechs: nitrification inhibitors) at (1 - lit) x (1 + NMIN)
        of the plain factor per kg of N under it, i.e. its N saving does not lower its N2O and the literature effect
        does: "h" gives back the saving's first-order tax (ef x NMIN) and charges - (ef_dir x lit_N2O + ef_vol x
        lit_NH3). Options without side-effect data lower N2O with the mineral N they save, through "m". REGISTERED:
        linearised at no adoption."""
        from capri_mod.environmental.environmental_module import (EF_SOIL_N2O_DIRECT, EF_SOIL_N2O_INDIRECT,
                                                                  GWP_N2O)
        tax = float(getattr(self, "ghg_tax", 0.0) or 0.0)
        k = 44.0 / 28.0 * GWP_N2O
        ef_d, ef_v = EF_SOIL_N2O_DIRECT * k, 0.10 * EF_SOIL_N2O_INDIRECT * k
        h = []
        for (nm_, nmin_, a_, b_, smx_) in ft:
            l2 = fert_side_value(self.data.region_id, str(nm_).upper(), "N2OSYN")
            l3 = fert_side_value(self.data.region_id, str(nm_).upper(), "NH3SYN")
            if l2 is None or l3 is None:
                h.append(0.0)
            else:
                h.append(tax * ((ef_d + ef_v) * float(nmin_) - (ef_d * float(l2) + ef_v * float(l3))) / 1000.0)
        return {"m": tax * (ef_d + ef_v + self._ef_mineral_lea()) / 1000.0, "h": h}

    def _tech_list(self):
        """Ammonia technologies for the regional model (CAPRI v_Miti): one entry per sub-activity
        and option. The loss cascade couples the two groups (N reaching the field); the N saved
        per unit of share is linearised at the shares of the previous solve (successive
        linearisation across outer iterations; at convergence CAPRI's relation holds)."""
        from capri_mod.supply import ammonia_techs as _at
        ctx = self._amm_context()
        if ctx is None:
            return []
        techs, man_d, nh3, sub = ctx
        wc0, wc1 = self._winter_cover_shares()
        last = getattr(self, "_amm_last", None) or {}
        # CAPRI's emission tax on the options (ghgTax; its v_CO2EquEmis follows v_Miti): per unit of M (share x
        # sub-activity unit), the manure N2O change through the loss cascade (the accounts' finite difference,
        # ghg_tax.ghg_coefficients "mtech", per head) less the indirect N2O of the NH3 kept and the soil N2O of the
        # mineral N it displaces (sub x N kept); kt CO2-eq per unit -> x tax = 1000 EUR, the objective's unit
        tax = float(getattr(self, "ghg_tax", 0.0) or 0.0)
        mtc = ((getattr(self, "ghg_coef", None) or {}).get("mtech") or {}) if tax > 0 else {}
        ef_n, ef_m = (self._ef_nh3_n2o(), self._ef_mineral_n2o()) if tax > 0 else (0.0, 0.0)
        out = []
        for a, subs in techs.items():
            mN, f = float(man_d.get(a, 0.0) or 0.0), float(nh3.get(a, 0.0) or 0.0)
            if a not in self.acts or mN <= 0 or f <= 0:
                continue
            sc = self._amm_scale(subs, mN, f)
            for s in subs:
                sh = last.get((a, s["key"])) or _at.initial(s)
                d = _at.marginal(s, sh, wc1)
                npl = sc * s["mrel"]
                # N saved per unit of the sub-activity at the linearisation point, relative to the base shares (exact
                # cascade): with it the regional model's relief is the TANGENT of CAPRI's cascade at that point,
                # rel0 + ret x (share - share there), so at a converged point the N saved is CAPRI's exactly (before,
                # ret x (share - base share) left out the cross term of the two option groups: the NLP check,
                # tools/nlp_check, found CAPRI's N balance violated by 8-365 t N in the five regions checked)
                rel0 = npl * (_at.loss(s, _at.initial(s), wc0) - _at.loss(s, sh, wc1))
                first = True
                for t in s["techs"]:
                    if t["slope"] is None or t["max"] <= 0:
                        continue
                    ret = max(0.0, -npl * d[t["tech"]])
                    # manure N2O through the cascade (the accounts' slope at the base shares, like every emission
                    # coefficient of the tax); the N kept is priced on its own (gn per t N kept) with the cascade's
                    # tangent, as the N row (K8: it was ret x (share - base share), K1's error)
                    g = tax * float(mtc.get((a, t["tech"]), 0.0) or 0.0) if tax > 0 else 0.0
                    gn = tax * (ef_n + sub * ef_m) / 1000.0 if tax > 0 else 0.0
                    out.append(dict(act=a, tech=t["tech"], key=s["key"], grp=(a, s["key"], t["group"]),
                                    w=s["w"], s0=t["ini"], smax=t["max"], slope=t["slope"], th=t["th"],
                                    ret=ret, sub=sub, stock=s["stock"], ghg=g, ghg_n=gn,
                                    s_lin=float(sh.get(t["tech"], t["ini"])), rel0=(rel0 if first else 0.0)))
                    first = False
        return out

    def _npk_spec(self, n_cols, x_start, A=None, labels=None):
        """CAPRI's crop nutrient balance of this region for the NLP form (capri_regional_nlp, block "fertilisation";
        data capri_mod/fert/npk.py): per nutrient (N, P, K) the crop groups with their need, permanent crops' own
        residues and the inner model's priors, the manure applied and the arable residue pool as linear functions of
        the columns, CAPRI's efficiencies, availability (endogenous for N: fert/endoManAvail.gms) and unit value.
        Need per ha: CAPRI's 2030 need (NITF/PHOF/POTF) x CAPRI's need factor of the yield (_need_yf, per nutrient)
        x kappa, kappa the region's need
        factor that closes NUTNED_ at base with the base mineral use (CAPRI's v_cropNutNeedMultFact, calibrated in
        the base and fixed in simulation; here one per region and nutrient). None outside CAPRI's EU data."""
        from capri_mod.fert.npk import NPKData, NUTRIENTS, PERM_NGRP, endo_slope
        from capri_mod.fert.inner_fert_dist import FERT_POST_ACCURACY
        env_ = getattr(self, "_env_for_surplus", None)
        if env_ is None:
            return None
        from capri_mod.fert.inner_fert_dist import InnerFertDist
        inner = env_.__dict__.get("_inner_fert")
        if inner is None:
            inner = env_._inner_fert = InnerFertDist()
        rid = self.data.region_id
        cr = inner.capri_region(rid)
        if cr is None:
            return None
        D = NPKData.get()
        acts = list(self.acts); n = len(acts)
        xb = np.maximum(self._base_levels().reindex(acts).fillna(0.0).values.astype(float), 0.0)
        yb = env_._cached_row("yields", rid) or {}
        ycur = self.data.yields
        sqn = {nut_: {} for nut_ in NUTRIENTS}      # CAPRI's need factor of the yield, per nutrient (_need_yf)
        for a in acts:
            if a in CROPS:
                y0 = float(yb.get(a, 0.0) or 0.0); yc = float(ycur.get(a, y0) or 0.0) if hasattr(ycur, "get") else y0
                for nut_ in NUTRIENTS:
                    sqn[nut_][a] = self._need_yf(a, y0, yc, nut_) if (y0 > 0 and yc > 0) else 1.0
        shares = D.crop_shares(cr)
        # manure N applied per unit of each column: the environmental accounts' own (excreted less housing and storage
        # losses, net of the base trade shares, imports per ha of crops), as the inner model reads it
        mint = dict(getattr(self, "_n_intensity", {}) or {})
        unitsN = {a: env_.unit_nitrogen_balance(a, ycur, rid, {k_: v_ for k_, v_ in mint.items() if k_ in (a, "__credit__")},
                                           yields_scen=self._yields_scen_now())
                  for a in acts}
        eN = np.array([float(unitsN[a].get("n_manure_applied", 0.0)) for a in acts])
        pool = [int(p_) for p_ in (getattr(self, "_pool_cols", None) or []) if int(p_) < n_cols]
        lt = list(getattr(self, "_land_types_used", None) or [])
        land_cols = [n + lt.index(t) for t in ("ARAC", "GRAS", "FRUN") if t in lt and n + lt.index(t) < n_cols] \
            if len(lt) and n + len(lt) <= n_cols else []
        crop_cols = [j for j, a in enumerate(acts) if a in CROPS]
        land0 = float(sum(xb[j] for j in crop_cols)) if not land_cols else \
            float(sum(np.asarray(x_start, float)[j] for j in land_cols))
        kap = self.__dict__.setdefault("_npk_kappa", {})
        out = {"capri_region": cr, "nutrients": {}, "land_cols": land_cols, "crop_cols": crop_cols}
        # the split columns: the grassland split moves area from CAPRI's GRAI to GRAE (z = GRAE - base GRAE, each of the
        # two half the grassland at base), so the GRAS groups' need changes by z x (need GRAE - need GRAI); the animal
        # split and option columns change their animal's manure in the proportion of their manure per head to the
        # animal's (the tables' dmann_rel / d_mann_rel, the factor their columns carry in the N rows), which reaches
        # ManureNPK_. Until 29 October 2026 the factor was read off the manure-application row or the N row, which
        # exist only with an N target: without one the split columns left the manure in NUTNED_ unchanged (K105).
        colsl = self._aug_col_labels(n_cols)
        j_gz = colsl.index("grass_z") if "grass_z" in colsl else None
        man_split = self._split_manure_factors(n_cols, acts)
        for nut in NUTRIENTS:
            sq = sqn[nut]
            R = D.region(cr, nut); P = D.priors(cr, nut)
            if R is None or P is None:
                continue
            eff = float(R.mine_eff) if R.mine_eff == R.mine_eff else 1.0
            g0 = float(R.excr_avail) if R.excr_avail == R.excr_avail else 0.0
            gc = float(R.cres_avail) if R.cres_avail == R.cres_avail else 0.0
            need = np.zeros(n); own = np.zeros(n); poolc = np.zeros(n); mine0 = np.zeros(n)
            for j, a in enumerate(acts):
                if a not in CROPS:
                    continue
                need[j] = D.crop_coef(cr, nut, a, "need_kg_ha")
                own[j] = D.crop_coef(cr, nut, a, "own_kg_ha")
                poolc[j] = D.crop_coef(cr, nut, a, "pool_kg_ha")
                mine0[j] = float(env_._base_mineral_rate(rid, a)) if nut == "N" else D.crop_coef(cr, nut, a, "mine_kg_ha")
            if nut == "N":
                man = eN.copy()
            else:
                # manure P2O5 / K2O per head (CAPRI 2017 totals / the model's herds), applied in the region in the
                # proportion CAPRI's 2030 reference applies it (net of the base net exports, ManureNPK_)
                man = np.array([D.manure_per_head(rid, nut, a) if a in ANIMALS else 0.0 for a in acts])
                # with manure trade off nothing leaves the region: all manure P / K applied, as for N
                if bool(getattr(getattr(self, "_env_for_surplus", None), "manure_trade_on", True)):
                    man = man * self._npk_applied_ratio(cr, nut)
            # kappa: NUTNED_ summed over the groups at base (all flows interior), the need net of the permanent
            # crops' own residues scaled together (REGISTERED: CAPRI's multiplier is on the need alone; with the model's
            # base levels and CAPRI's 2030 coefficients, scaling the need alone left the permanent groups' own residues
            # above their need in some regions, where NUTNED_ has no solution with positive flows):
            #   kappa x (need0 - gc x own0) = eff x M0 + g0 x E0 + gc x C0
            key = (cr, nut)
            if key not in kap:
                need0 = float(need @ xb); M0 = float(mine0 @ xb); E0 = float(man @ xb)
                C0 = float(poolc @ xb); O0 = float(own @ xb)
                net0 = need0 - gc * O0
                kap[key] = (eff * M0 + g0 * E0 + gc * C0) / net0 if net0 > 0 else 1.0
                kap[(key, "base")] = dict(need0=need0, M0=M0, E0=E0, C0=C0, O0=O0, land0=land0)
            k = kap[key]
            base = kap[(key, "base")]
            m0E = 1000.0 * base["E0"] / base["land0"] / 1000.0 if base["land0"] > 0 else 0.0   # kg/ha (t / kha)
            groups = []
            for gname, row in P.iterrows():
                crops = [(j, float(shares.get(acts[j], {}).get(gname, 0.0))) for j in crop_cols
                         if float(shares.get(acts[j], {}).get(gname, 0.0)) > 0]
                Aref = sum(sh * xb[j] for j, sh in crops)
                if Aref <= 1e-6:
                    continue
                perm = gname in PERM_NGRP
                modes = {}
                acc = {}
                ov = (getattr(self, "_npk_prior_override", None) or {}).get(nut)
                for s_, colname in (("MINE", "mine_kg_ha"), ("EXCR", "excr_kg_ha"), ("CRES", "cres_kg_ha")):
                    v_ = float(row[colname]) if row[colname] == row[colname] else 0.0
                    if ov is not None:
                        v_ = float(ov.get((gname, s_), 0.0)) / Aref        # the region's own calibrated posterior
                    if v_ > 0 and not (s_ == "CRES" and perm):
                        modes[s_] = v_ * Aref                               # t
                        acc[s_] = float(row["accuracy"]) if ov is None else FERT_POST_ACCURACY
                if not modes:
                    continue
                needl = [(j, sh * k * need[j] * sq.get(acts[j], 1.0)) for j, sh in crops if need[j] > 0]
                if j_gz is not None and "GRAS" in acts:
                    sh_g = float(shares.get("GRAS", {}).get(gname, 0.0))
                    dn = D.crop_coef(cr, nut, "GRAE", "need_kg_ha") - D.crop_coef(cr, nut, "GRAI", "need_kg_ha")
                    if sh_g > 0 and dn != 0.0:
                        needl.append((j_gz, sh_g * k * dn * sq.get("GRAS", 1.0)))
                groups.append({"g": gname, "perm": perm, "acc": acc, "modes": modes, "crops": crops,
                               "need": needl,
                               "own": [(j, sh * k * own[j]) for j, sh in crops if perm and own[j] > 0], "Aref": Aref})
            if not groups:
                continue
            # coverage check: the groups' need and own residues at base against the region's (kappa's) totals
            cov_need = sum(sum(v * xb[j] / sq.get(acts[j], 1.0) for j, v in g_["need"] if j < n) for g_ in groups)
            cov_own = sum(sum(v * xb[j] for j, v in g_["own"]) for g_ in groups)
            self.__dict__.setdefault("_npk_cov", {})[nut] = (cov_need, k * base["need0"], cov_own, base["O0"])
            Ecols = [(j, float(man[j])) for j in range(n) if man[j] != 0.0]
            if nut == "N":
                Ecols += [(j, float(man[acts.index(a_)]) * r_) for j, a_, r_ in man_split if man[acts.index(a_)] * r_ != 0.0]
            if pool and nut == "N" and len(pool) == 2:
                Ecols += [(pool[0], -1.0), (pool[1], 1.0)]
            elif pool and len(pool) == 2:
                # traded manure carries P and K in the region's manure proportions (REGISTERED: CAPRI trades MANP and
                # MANK as products of their own)
                rN = float(eN @ xb); rX = float(man @ xb)
                f_ = rX / rN if rN > 0 else 0.0
                Ecols += [(pool[0], -f_), (pool[1], f_)]
            out["nutrients"][nut] = {
                "groups": groups, "E": Ecols, "C": [(j, float(poolc[j])) for j in range(n) if poolc[j] > 0],
                "eff": eff, "g0": g0, "gc": gc, "slope": endo_slope(g0, m0E, nut), "m0E": m0E,
                "price": float(R.uvag_eur_t) if R.uvag_eur_t == R.uvag_eur_t else 0.0, "kappa": k,
                "M0": base["M0"]}
        out["dual_bound"] = float(getattr(self, "_npk_dual_bound", 10.0) or 10.0)
        return out if out["nutrients"] else None

    @staticmethod
    def _npk_base_alloc(nlp0, npk, yb):
        """The fertilisation block's N allocation at the calibration point, per ha of each group (kg/ha), with the
        base purchases and land: the baseline allocation the Green Deal caps are taken from."""
        if not npk or "N" not in (npk.get("nutrients") or {}) or not nlp0.fert:
            return None
        fo = nlp0.fert_outputs(nlp0.cal_point)
        o = fo["N"]
        yb = np.asarray(yb, float)
        per_ha_nut = {}
        for nut, d_ in npk["nutrients"].items():
            if nut not in fo:
                continue
            ar = {g_["g"]: float(sum(sh * yb[j] for j, sh in g_["crops"])) for g_ in d_["groups"]}
            per_ha_nut[nut] = {(g, s_): v / ar[g] for (g, s_), v in fo[nut]["flows"].items() if ar.get(g, 0.0) > 0}
        area = {g_["g"]: float(sum(sh * yb[j] for j, sh in g_["crops"])) for g_ in npk["nutrients"]["N"]["groups"]}
        per_ha = per_ha_nut["N"]
        lc = npk.get("land_cols") or npk.get("crop_cols") or []
        return {"per_ha": per_ha, "per_ha_nut": per_ha_nut, "area": area, "capri_region": npk.get("capri_region"),
                "purchase": o["purchase"], "land": float(sum(yb[j] for j in lc))}

    def _npk_organic_cap(self, npk):
        """CAPRI's organic area target on the fertilisation block (pol_input/greendeal/organic_area.gms ->
        organic_minfert_redu.gms, 'region_and_crop'): each crop group's mineral N per ha at most its baseline
        allocation x (1 - the group's organic conversion), as CAPRI's "f2f" regulation (beta density, mode 0.75 x max,
        accuracy 0.25); groups below 10 kg/ha at baseline capped at the baseline; "limCres" on residues for every
        nutrient at 1.2 x the baseline per ha (mode at the baseline, accuracy 10). The group's conversion is its crops'
        (capri-mod's organic targets per member state and crop class, the shares the I/O changes use), weighted by base
        area. Returns {nutrient: {(group, source): (max kg/ha, beta1, beta2)}} or {} without an organic target."""
        conv = getattr(self, "_organic_conv", None) or {}
        base = getattr(self, "_nlp_base_alloc", None)
        if not conv or base is None:
            return {}
        from capri_mod.fert.inner_fert_dist import beta_regulation
        acts = list(self.acts)
        xb = np.maximum(self._base_levels().reindex(acts).fillna(0.0).values.astype(float), 0.0)
        b1, b2 = beta_regulation(0.25, 0.75)
        out = {}
        dN = (npk.get("nutrients") or {}).get("N")
        if dN is not None:
            regs = {}
            for g_ in dN["groups"]:
                g = g_["g"]
                v = float(base["per_ha"].get((g, "MINE"), 0.0))
                if v <= 0:
                    continue
                w = sum(sh * xb[j] for j, sh in g_["crops"])
                share_conv = 1.0 - (sum(sh * xb[j] * float(conv.get(acts[j], 1.0)) for j, sh in g_["crops"]) / w
                                    if w > 0 else 1.0)
                mx = v if v < self.ORGANIC_SMALL_MINE_KG_HA else v * (1.0 - max(share_conv, 0.0))
                regs[(g, "MINE")] = (mx, b1, b2)
            out["N"] = regs
        f = self.ORGANIC_LIMCRES_FACTOR
        for nut, per in (base.get("per_ha_nut") or {}).items():
            if nut not in (npk.get("nutrients") or {}):
                continue
            r_ = out.setdefault(nut, {})
            for (g, s_), v in per.items():
                if s_ == "CRES" and v > 0:
                    c1 = (1.0 / f) * 10.0 + 1.0
                    r_[(g, "CRES")] = (v * f, c1, 10.0 + 2.0 - c1)
        return out

    @staticmethod
    def _merge_organic_regs(cur: dict, org: dict, small: set) -> dict:
        """The organic target's regulations ({(group, source): (max per ha, beta1, beta2)}) merged into those of the
        mineral reduction (cur), as CAPRI's files in their order (greendeal_scenarios.gms: organic_minfert_redu.gms,
        then minfert_redu_by_crop.gms): a regulation only the organic target sets is kept; for a mineral flow both
        set, the more stringent (min, minfert_redu_by_crop.gms l. 243-246), except for CAPRI's small groups
        (p_checkSmallMine, `small`), whose cap the mineral reduction sets at factor x baseline, replacing the organic
        one (l. 233-235; audit S2); the residue regulation (limCres) is the mineral reduction's."""
        out = dict(cur)
        for k_, v_ in org.items():
            if k_ not in out:
                out[k_] = v_
            elif k_[1] == "MINE" and v_[0] < out[k_][0] and k_[0] not in small:
                out[k_] = v_
        return out

    def _npk_mineral_cap(self, npk):
        """The Green Deal's mineral N reduction (self._mineral_cap) on the fertilisation block: "crp" - CAPRI's "f2f"
        regulation on each capped group's mineral flow (max per ha = the base allocation per ha x (1 - r), CAPRI's
        exemptions; beta density mode 0.75 x max, accuracy 0.25) and "limCres" on residues; "uaa" - purchases <=
        base mineral N per ha of land x (1 - r) x current land. The base allocation is this model's own (the
        fertilisation block at the calibration point), as CAPRI takes its baseline's."""
        mc = getattr(self, "_mineral_cap", None) or {}
        d = (npk.get("nutrients") or {}).get("N")
        base = getattr(self, "_nlp_base_alloc", None)
        if not mc or d is None or base is None:
            return
        r = float(mc.get("reduction", 0.0) or 0.0)
        if mc.get("kind") == "crp":
            from capri_mod.fert.inner_fert_dist import beta_regulation
            env_ = getattr(self, "_env_for_surplus", None)
            inner = env_.__dict__.get("_inner_fert") if env_ is not None else None
            if inner is None:
                return
            caps = inner.mineral_caps(self.data.region_id, base, r)
            # CAPRI's small groups (p_checkSmallMine): their cap replaces the organic target's (S2)
            self._nlp_mine_small = inner.small_mine_groups(self.data.region_id, base)
            lim = inner.limcres_caps(self.data.region_id, base)
            b1, b2 = beta_regulation(0.25, 0.75)
            regs = {(g, "MINE"): (float(v), b1, b2) for g, v in caps.items() if v > 0}
            for g, (mx, racc, msh) in lim.items():
                c1 = float(msh) * float(racc) + 1.0
                regs[(g, "CRES")] = (float(mx), c1, float(racc) + 2.0 - c1)
            d["regs"] = regs
            self._nlp_group_caps = caps
            # limCres for every nutrient (minfert_redu_by_crop.gms sets it over FNUT)
            for nut_, per_ in (base.get("per_ha_nut") or {}).items():
                d_ = (npk.get("nutrients") or {}).get(nut_)
                if nut_ == "N" or d_ is None:
                    continue
                rg_ = dict(d_.get("regs") or {})
                for g, (mx, racc, msh) in inner.limcres_caps(self.data.region_id, dict(base, per_ha=per_)).items():
                    c1 = float(msh) * float(racc) + 1.0
                    rg_[(g, "CRES")] = (float(mx), c1, float(racc) + 2.0 - c1)
                d_["regs"] = rg_
        else:
            land0 = float(base.get("land", 0.0) or 0.0)
            if land0 > 0:
                d["synNMax"] = (1.0 - r) * float(base["purchase"]) / land0

    def _n_row_mineral_parts(self, A, labels):
        """The mineral-N parts of the N_balance row's coefficients (t mineral N per unit of each column), from the
        environmental accounts' own unit balances (n_mineral_input) as the row is built from them: activities their
        unit balance's, manure exports and imports -/+ the substitution factor, the grassland split its delta, the
        dairy, cattle and option columns their animal's in proportion to their manure coefficient."""
        env_ = getattr(self, "_env_for_surplus", None)
        i_nb = labels.index("N_balance")
        mp = np.zeros(A.shape[1])
        if env_ is None:
            return mp
        rid = self.data.region_id
        ycur = self.data.yields
        mint = dict(getattr(self, "_n_intensity", {}) or {})
        acts = list(self.acts)
        unit = {}
        for j, a in enumerate(acts):
            mi = {k_: v_ for k_, v_ in mint.items() if k_ in (a, "__credit__")}
            unit[a] = float(env_.unit_nitrogen_balance(a, ycur, rid, mi, yields_scen=self._yields_scen_now())
                            .get("n_mineral_input", 0.0))
            mp[j] = unit[a]
        pc = getattr(self, "_pool_cols", None) or []
        if len(pc) == 2:
            sub = float(getattr(self, "_pool_avail", 0.0) or 0.0)
            if pc[0] < A.shape[1]:
                mp[pc[0]] = sub                 # export: the row has -(1 - sub): -1 organic, +sub mineral
            if pc[1] < A.shape[1]:
                mp[pc[1]] = -sub
        gc = getattr(self, "_grass_col", None)
        if gc is not None and gc < A.shape[1]:
            d = env_.grass_intensity_delta(rid) or {}
            mp[gc] = float(d.get("n_mineral_input", 0.0))
        cols = self._aug_col_labels(A.shape[1])
        for j, lab in enumerate(cols):
            a = None
            if lab == "dairy_z":
                a = "DCOW"
            elif lab.startswith("cattle_z_"):
                a = lab[len("cattle_z_"):].split(":")[0]
            elif lab.startswith("genet_z_"):
                a = lab[len("genet_z_"):].split("_")[0]
            if a in acts:
                ja = acts.index(a)
                if A[i_nb, ja] != 0:
                    mp[j] = unit[a] * float(A[i_nb, j]) / float(A[i_nb, ja])
        return mp

    def _npk_recalibrate_priors(self, spec, nuts, yb) -> bool:
        """CAPRI's fertiliser calibration (fert/ferttrm_years.gms, as capri_mod.fert.inner_fert_dist.calibrate) for
        the nutrients whose block has no solution at the base: blanket priors per crop group - the group's need at
        base (net of the permanent crops' own residues, at least 10% of the need) split equally over its sources
        (mineral, manure, and residues for arable groups), half of grassland's mineral prior moved to manure, accuracy
        2 (residues 5) - and their posterior at the base's levels, which becomes the region's simulation prior
        (accuracy 1). Returns whether every nutrient got one."""
        from capri_mod.supply.capri_regional_nlp import CapriRegionalNLP
        from capri_mod.fert.inner_fert_dist import (FERT_CAL_PRIOR_ACCURACY, FERT_CAL_CRES_ACCURACY,
                                                    FERT_CAL_MIN_NEED_SHARE, FERT_CAL_GRAS_MINE_TO_EXCR)
        import copy as _cp
        sp = dict(spec)
        npk = _cp.deepcopy(spec["npk"])
        yb = np.asarray(yb, float)
        for nut in nuts:
            d = npk["nutrients"][nut]
            for g_ in d["groups"]:
                nd = sum(v * yb[j] for j, v in g_["need"])
                ow = sum(v * yb[j] for j, v in g_["own"]) * float(d["gc"]) if g_["perm"] else 0.0
                R = max(FERT_CAL_MIN_NEED_SHARE * nd, nd - ow)
                k = 2.0 if g_["perm"] else 3.0
                m = R / k
                modes = {"MINE": m, "EXCR": m}
                if not g_["perm"]:
                    modes["CRES"] = m
                if g_["g"] == "GRAS":
                    modes["EXCR"] += FERT_CAL_GRAS_MINE_TO_EXCR * modes["MINE"]
                    modes["MINE"] *= 1.0 - FERT_CAL_GRAS_MINE_TO_EXCR
                g_["modes"] = {s_: max(v, 1e-6) for s_, v in modes.items()}
                g_["acc"] = {"MINE": FERT_CAL_PRIOR_ACCURACY, "EXCR": FERT_CAL_PRIOR_ACCURACY,
                             "CRES": FERT_CAL_CRES_ACCURACY}
        sp["npk"] = npk
        tmp = CapriRegionalNLP(sp)
        x, failed = tmp.fert_at(tmp.start(yb))
        ok = True
        ov = dict(getattr(self, "_npk_prior_override", None) or {})
        out = tmp.fert_outputs(x)
        for nut in nuts:
            if nut in failed:
                ok = False
                continue
            ov[nut] = dict(out[nut]["flows"])
        self._npk_prior_override = ov
        self._npk_prior_recalibrated = sorted(set(getattr(self, "_npk_prior_recalibrated", []) or []) | set(ov))
        return ok

    def _npk_applied_ratio(self, cr, nut):
        """CAPRI 2030: manure P/K applied in the region (net of net exports) per unit excreted (fertDistExcr_ /
        EXCRET), from the extract of tools/build/build_npk_balance_2030.py."""
        c = _inputs.current().cache.get("npk_applied_ratio")
        if c is None:
            import pandas as _pd
            s = _inputs.current().csv("npk_dataout_2030.csv.xz", "sources/environment", keep_default_na=False)
            s = s[(s.item == "") & (s.row.isin(["EXCRET", "MTRADE"]))]
            v = {(t.region, t.row, t.col): float(t.value) for t in s.itertuples(index=False)}
            c = {}
            for (r, row, col), x in v.items():
                if row == "EXCRET" and x > 0:
                    c[(r, {"PHOF": "P", "POTF": "K", "NITF": "N"}[col])] = max(0.0, 1.0 - v.get((r, "MTRADE", col), 0.0) / x)
            _inputs.current().cache["npk_applied_ratio"] = c
        # every unit of the model has CAPRI's regional value (K74, 29 October 2026: the national value and the 1.0
        # without a source, the fallbacks before, were reached by none)
        if (cr, nut) not in c:
            raise KeyError(f"{cr}: no CAPRI 2030 manure {nut} excretion in npk_dataout_2030.csv.xz")
        return c[(cr, nut)]

    def _crop_mineral_rate(self, a: str) -> float:
        """The crop's base mineral N application (kg N/ha; the environmental module's rate): the part of its
        balance coefficient that CAPRI's fertiliser technologies act on. Its unit coefficient also carries its
        share of the manure- and residue-covered need, which the animals' manure and the residues displace; at the
        base those cancel over the region. (Until Sprint 9e the technologies scaled the whole unit coefficient,
        which saved on the manure-covered need as well: ~40% more mineral N saved in the rows than in the accounts,
        Upper Bavaria wheat 108 against 77 kg N/ha.)"""
        env_ = getattr(self, "_env_for_surplus", None)
        if env_ is None:
            return 0.0
        try:
            return float(env_._base_mineral_rate(self.data.region_id, a))
        except Exception:
            return 0.0

    def tiered_surplus_target(self, surplus_per_ha: float) -> float:
        """CAPRI's tiered gross-nitrogen-balance target (JRC121368).

        25% cut on the first 50 kg N/ha of surplus, 50% on 50-100, 75% on
        100-150, 100% above 150. Returns the TARGET surplus per hectare.
        """
        target = 0.0
        for lo, hi, cut in ((0.0, 50.0, 0.25), (50.0, 100.0, 0.50),
                            (100.0, 150.0, 0.75), (150.0, 1e9, 1.0)):
            target += max(0.0, min(surplus_per_ha, hi) - lo) * (1.0 - cut)
        return target

    def _nitrate_extra(self) -> dict:
        """Extra N excretion from nitrate in the ration, t N per activity unit
        (1000 heads): 0.28 kg N per kg nitrate per head."""
        rs = getattr(self, "ration_state", None) or {}
        return {a: self.NITR_N_EXCR * float(v.get("nitr_kg", 0.0))
                for a, v in rs.items() if isinstance(v, dict) and float(v.get("nitr_kg", 0.0)) > 0}

    def _nitrate_row_term(self, a) -> float:
        """Extra manure N enters the balance like any manure: (1 - substitution)."""
        ex = self._nitrate_extra().get(a, 0.0)
        if ex <= 0:
            return 0.0
        env_ = getattr(self, "_env_for_surplus", None)
        try:
            sub = float(env_._substitution(self.data.region_id)[0]) if env_ is not None else 0.0
        except Exception:
            sub = 0.0
        return (1.0 - sub) * ex

    def _apply_balance_price(self, lam: float):
        """Fertiliser response to the nitrogen-balance price, as CAPRI models it.

        CAPRI's supply model has NO nitrogen yield response: crop yields are
        exogenous shifts (capmod/shift_yields.gms). It meets a nitrogen target
        partly through FERTILISER-EFFICIENCY TECHNOLOGIES - precision farming,
        variable-rate application, nitrification inhibitors, timing - which let
        the same crop need be met with less purchased fertiliser: in its crop
        nutrient balance mineral N counts x (1 + SUM_tech share x NMIN).
        JRC121368 states the GNB target was met 'with nitrogen mitigation
        technologies made available to farmers'.

        Shares follow CAPRI's first-order conditions per tonne of crop N need (the basis of
        CAPRI's cost of these options): marginal cost S0 + slope (s - s0) (CAPRI's calibration,
        _fert_techs) against the value lam x NMIN / (1 + E)^2 of the mineral N saved, with the
        options' shares summing to at most 1 (TotMit_) and CAPRI's Tot_MitFert_ cap on E.
        Mineral N per ha then falls by (1 + E0) / (1 + E) for every fertilised crop. YIELDS DO
        NOT CHANGE; each crop bears the extra cost in proportion to its N need.

        (This replaced a Mitscherlich intensity response that cut fertiliser
        THROUGH yield loss - not CAPRI's mechanism - under which crops carried too
        much of the adjustment: cereals 1.28x, oilseeds 1.42x CAPRI, herds too
        little.)
        """
        # keep factors already set this solve (organic land: no mineral N)
        self._n_intensity = getattr(self, "_n_intensity", {}) or {}
        if self._techs_inside():
            # decided inside the regional model: keep its results (a reset here, after
            # the last solve, erased the reported shares; the inhibitor on manure is inside too,
            # _apply_manure_inhibitor returns at once)
            self._apply_manure_inhibitor(lam)
            return None
        self._fert_tech_shares = {}
        self._apply_manure_techs(lam)
        self._apply_manure_inhibitor(lam)
        srow = getattr(self, "_surplus_row", None)
        _mc = getattr(self, "_mineral_cap", None) or {}
        techs = srow[5] if (srow is not None and len(srow) > 5) else (_mc.get("techs") or [])
        if not lam or lam <= 0 or not techs:
            return None
        nmin_ha = srow[2] if (srow is not None and len(srow) > 2) else (_mc.get("nmin") or {})
        base = self._base_levels()
        crops = [c for c in CROPS if c in self.acts and float(nmin_ha.get(c, 0.0)) > 0]
        if not crops:
            return None
        e0 = sum(nm * s0 for _, nm, _, _, s0, _ in techs)
        lam_t = 1000.0 * float(lam)          # EUR per t N (lam: kEUR/t)

        # CAPRI's choice per tonne of crop N need: min sum_t [S0 (s - s0) + 0.5 slope (s - s0)^2]
        # + lam / (1 + E), E = sum s NMIN, 0 <= s <= smax, sum s <= 1 (TotMit_), and Tot_MitFert_
        # E <= cap. First-order conditions: s_t = s0 + (lam NMIN_t / (1 + E)^2 - S0_t - mu_cap
        # NMIN_t - mu) / slope_t; E solved as a fixed point (the right side falls in E).
        def _at(E, mu_cap):
            def sh(mu):
                return {nm_: min(max(s0_ + (lam_t * nm / (1.0 + E) ** 2 - S0_ - mu_cap * nm - mu) / sl_, 0.0), smx)
                        for nm_, nm, S0_, sl_, s0_, smx in techs}
            o = sh(0.0)
            if sum(o.values()) > 1.0:
                lo, hi = 0.0, lam_t + max(t_[3] for t_ in techs)
                for _ in range(60):
                    mid = 0.5 * (lo + hi)
                    lo, hi = (mid, hi) if sum(sh(mid).values()) > 1.0 else (lo, mid)
                o = sh(hi)
            return o

        def _solve(mu_cap):
            lo, hi = 0.0, sum(nm * smx for _, nm, _, _, _, smx in techs)
            for _ in range(60):                           # E = g(E), g decreasing
                mid = 0.5 * (lo + hi)
                g = sum(v * nm for (nm_, nm, *_r), v in zip(techs, _at(mid, mu_cap).values()))
                lo, hi = (mid, hi) if g > mid else (lo, mid)
            return _at(hi, mu_cap)

        sh = _solve(0.0)
        cap = fert_efficiency_cap(self.data.region_id)
        E = sum(sh[nm_] * nm for nm_, nm, *_r in techs)
        if cap is not None and E > cap + 1e-12:
            lo, hi = 0.0, lam_t * max(1.0, max(nm for _, nm, *_r in techs))
            for _ in range(60):
                mid = 0.5 * (lo + hi)
                o = _solve(mid)
                lo, hi = (mid, hi) if sum(o[nm_] * nm for nm_, nm, *_r in techs) > cap else (lo, mid)
            sh = _solve(hi)
        e = sum(sh[nm_] * nm for nm_, nm, *_r in techs)
        f = (1.0 + e0) / (1.0 + e)
        if f >= 1.0 - 1e-9:
            return None
        # extra cost per t of need (EUR), charged per ha in proportion to each crop's need
        c_t = sum(S0_ * (sh[nm_] - s0_) + 0.5 * sl_ * (sh[nm_] - s0_) ** 2 for nm_, nm, S0_, sl_, s0_, smx in techs)
        nc = self.data.nutrient_coefs.copy()
        for c in crops:
            if c in nc.index and "N" in nc.columns:
                nc.at[c, "N"] = float(nc.at[c, "N"]) * f
            self._n_intensity[c] = self._n_intensity.get(c, 1.0) * f
            if c in self.net_revenues.index:
                need_t_ha = self._crop_mineral_rate(c) * (1.0 + e0) / 1000.0
                self.net_revenues[c] = float(self.net_revenues[c]) - c_t * need_t_ha
        # the same factor on the manure and residue credits (environmental module, "__credit__")
        self._n_intensity["__credit__"] = self._n_intensity.get("__credit__", 1.0) * f
        shares = {k: (v,) for k, v in sh.items()}
        self.data.nutrient_coefs = nc
        self._fert_tech_shares.update({k: v[0] for k, v in shares.items()})
        return self._n_intensity

    def _fert_params_raw(self):
        """(manure availability, mineral N price kEUR/t) without the allocation switch."""
        flag = getattr(self, "use_fert_allocation", False)
        try:
            self.use_fert_allocation = True
            return self._fert_alloc_params()
        finally:
            self.use_fert_allocation = flag

    def _fert_alloc_params(self):
        """(manure availability, mineral N price kEUR/t N) for this region, from
        CAPRI's reference allocation and its 2017 national UVAG of NITF."""
        if not getattr(self, "use_fert_allocation", False):
            return None, None
        reg = getattr(getattr(self, "data", None), "region_id", None)
        c = _inputs.current().cache.setdefault("fert_alloc", {})
        if not c:
            inp = _inputs.current()
            fs = inp.csv("fertiliser_substitution_2030.csv", "environment").set_index("region")
            c["av"] = fs["manure_availability"].to_dict()
            fp = inp.csv("mineral_n_price.csv", "supply").set_index("country")
            c["pf"] = (fp["eur_per_t_n"] / 1000.0).to_dict()
        a = c["av"].get(reg)
        from capri_mod.data.definitions import country_of
        p = c["pf"].get(country_of(reg)) if reg else None
        a = float(a) if a is not None and a == a else None
        return a, (float(p) if p is not None else None)

    def _relax_n_target(self, Qa, ca, Aa, ba, ya0):
        """JRC121368 (sect. 4.3.4, p. 23): regions where the tiered nitrogen target "generated
        infeasibilities in the model" had their reduction "set at the EU average (36%)". The
        report names no regions and the model takes the nine highest baseline surpluses up front
        (SupplyModule.JRC_CAPPED_N_REGIONS); this applies the same rule to any OTHER region whose
        target proves infeasible in the land-market problem - in the model these are Dutch regions
        that IMPORT manure in CAPRI's 2030 reference (52-123 kg N/ha, held fixed without the
        manure market). The target per hectare becomes the region's base surplus x (1 - 36%); with
        the target per current hectare (e_SURTOTHa) its land terms move with it. Records
        balance_shortfall (kg N/ha relaxed) and n_target_relaxed. Returns (y, ok, Aa, ba)."""
        labels = list(getattr(self, "_row_labels", []))
        srow = getattr(self, "_surplus_row", None)
        if "N_balance" not in labels or srow is None or len(srow) < 8 or srow[7] is None:
            return None, False, Aa, ba
        T = float(srow[1]); T2 = float(srow[7]) * (1.0 - SupplyModule.JRC_CAPPED_CUT)
        if not T2 > T + 1e-9:
            return None, False, Aa, ba
        k = labels.index("N_balance")
        A2, b2 = Aa.copy(), ba.copy()
        base_area = float(sum(v for a_, v in self._base_levels().items() if a_ in CROPS))
        nl = getattr(self, "_nrow_land", None)
        if nl:
            cols, L0sum, tgt = nl
            for c_ in cols:
                A2[k, c_] *= T2 / tgt
            b2[k] += (T2 - T) * (base_area - L0sum)
        else:
            b2[k] += (T2 - T) * base_area
        self._last_duals = None
        y = self._nlp_solve(Qa, ca, A2, b2, ya0)
        if y is None:
            return None, False, Aa, ba
        self.balance_shortfall = T2 - T
        self._n_target_relaxed = True
        self._n_relax_sticky = self._n_relax_key()
        return y, True, A2, b2

    def _n_relax_key(self):
        """The scenario's N target for this region (tiered target, base surplus): identifies the setting the
        JRC121368 relaxation belongs to; None without an N target."""
        srow = getattr(self, "_surplus_row", None)
        if srow is None or len(srow) < 8 or srow[7] is None:
            return None
        return (round(float(srow[1]), 9), round(float(srow[7]), 9))
