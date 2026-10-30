"""The phosphorus balance (P2O5; docs/P_BALANCE.md): CAPRI's applied ratios and runoff.

EnvironmentalModule's methods, moved unchanged from capri_mod/environmental/environmental_module.py (refactor stage 4a,
docs/design/ARCHITECTURE_REFACTOR.md); the module-level names they use are environmental_module's, given to this
module once environmental_module is loaded (capri_mod.environmental.blocks.inject); the annotations are not evaluated.
"""
from __future__ import annotations


class PhosphorusBlock:
    def _p_capri_region(self, region):
        """The CAPRI region of the fertilisation block's data (InnerFertDist.capri_region, as SupplyModel._npk_spec)."""
        inner = self.__dict__.get("_inner_fert")
        if inner is None:
            from capri_mod.fert.inner_fert_dist import InnerFertDist
            inner = self._inner_fert = InnerFertDist()
        return inner.capri_region(region)

    def _p_applied_ratio(self, capri_region):
        """Manure P2O5 applied in the region per unit excreted at CAPRI's 2030 reference, 1 - MTRADE / EXCRET (the
        fertilisation block's ManureNPK_ for P, SupplyModel._npk_applied_ratio; npk_dataout_2030.csv.xz)."""
        c = getattr(type(self), "_P_APPL", None)
        if c is None:
            s = _inputs.current().csv("npk_dataout_2030.csv.xz", "sources/environment", keep_default_na=False)
            s = s[(s.item == "") & (s.col == "PHOF") & (s.row.isin(["EXCRET", "MTRADE"]))]
            v = {(t.region, t.row): float(t.value) for t in s.itertuples(index=False)}
            c = {r: max(0.0, 1.0 - v.get((r, "MTRADE"), 0.0) / x) for (r, row), x in v.items() if row == "EXCRET" and x > 0}
            type(self)._P_APPL = c
        return c.get(capri_region, c.get(capri_region[:2] + "000000", 1.0))

    def _p_runtot(self, region, ms=None, wc=0.0, fert_mrun=0.0, initial=False) -> Dict[str, float]:
        """CAPRI's runoff share of excreted manure N, v_emiLoss(N, RunTot) = RunHous + RunSurf, per animal through the
        loss cascade (capri_mod/supply/n_cascade.py) at the option shares ms (or CAPRI's initial shares), the winter cover
        share wc and the manure inhibitor's runoff effect, the animal's CAPRI sub-activities weighted by their manure N
        (as _leach_animals). CAPRI applies the same share to manure P2O5 (calc_nbalance.gms l. 71, 103-106, RUNANI). RunHous
        and RunSurf are held within CAPRI's bounds of a loss share, [0, 1] (v_emiLoss.lo/up). A sub-activity without
        cascade data runs off nothing (CAPRI reports no RUNANI there)."""
        from capri_mod.supply import ammonia_techs as _at, n_cascade as _nc
        self._manure_n2o_tech(region)                 # loads CAPRI's sub-activities (ammonia_tech_model.csv)
        tm = (getattr(self, "_amm_tm", None) or {}).get(region, {})
        out = {}
        for a_ in ANIMALS:
            subs = tm.get(a_) or []
            sh = {t: v for (aa, t), v in (ms or {}).items() if aa == a_}
            W = R = 0.0
            for sb in subs:
                w = float(sb["w"]) * float(sb.get("mrel", 1.0) or 1.0)
                W += w
                cd = _at.cascade_data(sb)
                if cd is None:
                    continue
                s_ = {t["tech"]: t["ini"] for t in sb["techs"]}
                if not initial:
                    s_ = {t_: sh.get(t_, v_) for t_, v_ in s_.items()}
                f, rsurf, eff = cd
                L = _nc.losses(f, rsurf, s_, eff, m_runsurf=(1.0 - _nc.WINTERCOV_NO3 * wc - fert_mrun, 1.0),
                               m_appl_run=1.0 - _nc.WINTERCOV_NO3 * wc)
                # CAPRI bounds every loss share to [0, 1] (supply/set_supply_bounds.gms l. 240-243, v_emiLoss.lo/up), so
                # options cannot drive the runoff below zero; the cascade evaluated at the solution's shares can
                R += w * (min(max(float(L[("N", "RunHous")]), 0.0), 1.0) + min(max(float(L[("N", "RunSurf")]), 0.0), 1.0))
            if W > 0:
                out[a_] = R / W
        return out

    def compute_phosphorus_balance(self, acts, yields, region: str, supply_result=None) -> Dict[str, float]:
        """CAPRI's gross phosphate balance of the region (reports/calc_nbalance.gms, FNUT = PHOF), t P2O5.

        EXCRET  sum over animals of herd x manure P2O5 per head (CAPRI's 2017 MANP totals / the model's herds,
                livestock_manure_p_coef.csv; the split and option columns leave it unchanged, as in the regional model's
                fertilisation block)
        MTRADE  EXCRET - manure P2O5 applied in the region (ManureNPK_): with the NLP form's fertilisation block the
                sum of its manure flows; without it (no supply result: the accounts at the base data) CAPRI's 2030 share applied
                (1 - MTRADE / EXCRET) plus the region's manure trade carried in the region's P/N proportion, as the
                block builds it
        MINFER  the block's P2O5 purchases (v_netPutQuant); without the block, CAPRI's NUTNED_ for P summed over the
                crop groups with the block's data (p_balance.nutned_mineral; at the base levels the base purchases)
        CRESID  sum over crops of area x CAPRI's residue output PCRD x yield / base yield
        EXPPRD  sum over crops of area x CAPRI's retention PRET x yield / base yield (both with the grassland split
                column's GRAE - GRAI difference)
        RUNANI  sum over animals of manure P2O5 x CAPRI's N runoff share RunTot (_p_runtot)
        IMPORT, SURTOT, SURSOI  CAPRI's sums (p_balance.balance).
        Removal and residues follow the yield as the N accounts do (CAPRI: e_EXPPRD and e_CRESID scale with the yield
        factors of its mitigation and pesticide options)."""
        from capri_mod.environmental import p_balance as _pb
        from capri_mod.fert.npk import NPKData, PERM_NGRP
        if hasattr(acts, "to_dict"):
            acts = acts.to_dict()
        if hasattr(yields, "to_dict"):
            yields = yields.to_dict()
        cr = self._p_capri_region(region)
        if cr is None:
            raise RuntimeError(f"no CAPRI fertilisation data for {region} (fert_dist_priors_2030.csv)")
        D, C = NPKData.get(), _pb.PCropCoefs.get()
        y0 = self._cached_row("yields", region) or {}
        yr = {}
        for c in CROPS:
            b, y = float(y0.get(c, 0.0) or 0.0), yields.get(c)
            yr[c] = float(y) / b if (b > 0 and y is not None and float(y) >= 0) else 1.0
        x = {c: max(float(acts.get(c, 0.0) or 0.0), 0.0) for c in CROPS}
        h = {a: max(float(acts.get(a, 0.0) or 0.0), 0.0) for a in ANIMALS}
        z = float(getattr(supply_result, "grass_ext_shift", 0.0) or 0.0) if supply_result is not None else 0.0
        # removal and residues (EXPPRD, CRESID)
        expprd = sum(x[c] * C.coef(cr, c)[0] * yr[c] for c in CROPS)
        cresid = sum(x[c] * C.coef(cr, c)[1] * yr[c] for c in CROPS)
        if z:
            ge, gi = C.coef(cr, "GRAE"), C.coef(cr, "GRAI")
            expprd += z * (ge[0] - gi[0]) * yr.get("GRAS", 1.0)
            cresid += z * (ge[1] - gi[1]) * yr.get("GRAS", 1.0)
        # excretion (EXCRET)
        manp = {a: D.manure_per_head(region, "P", a) for a in ANIMALS}
        excret = sum(h[a] * manp[a] for a in ANIMALS)
        npk = getattr(supply_result, "fert_npk", None) or {}
        blk = npk.get("P") if isinstance(npk, dict) else None
        ratio = self._p_applied_ratio(cr) if bool(getattr(self, "manure_trade_on", True)) else 1.0
        # the need multiplier (kappa) is calibrated at the base and fixed in simulation (CAPRI's
        # v_cropNutNeedMultFact): the regional model's block computes it once, at the run's baseline, with that
        # baseline's manure trade setting; the base manure applied here follows the first setting seen for the region
        ratio_base = self.__dict__.setdefault("_p_ratio_base", {}).setdefault(cr, ratio)
        if blk is not None:
            applied = sum(float(v) for (g, s_), v in blk["flows"].items() if s_ == "EXCR")
            minfer = float(blk["purchase"])
            src = "nlp"
        else:
            # CAPRI's NUTNED_ for P summed over the groups, with the block's own data (SupplyModel._npk_spec)
            A0 = self.data["areas"].loc[region] if region in self.data["areas"].index else {}
            H0 = self.data["animal_numbers"].loc[region] if region in self.data["animal_numbers"].index else {}
            xb = {c: max(float(A0.get(c, 0.0) or 0.0), 0.0) for c in CROPS}
            hb = {a: max(float(H0.get(a, 0.0) or 0.0), 0.0) for a in ANIMALS}
            E0 = ratio_base * sum(hb[a] * manp[a] for a in ANIMALS)
            applied = ratio * excret
            mt = getattr(supply_result, "manure_trade", None) if supply_result is not None else None
            if mt and (abs(float(mt[0])) > 0 or abs(float(mt[1])) > 0):
                # traded manure carries P in the region's base manure P/N proportion (the block's pool columns)
                ba = dict(xb); ba.update(hb)
                rN = float(self.compute_nitrogen_balance(ba, dict(y0), region).get("n_manure_applied", 0.0))
                applied += (E0 / rN if rN > 0 else 0.0) * (float(mt[1]) - float(mt[0]))
            sh = D.crop_shares(cr)
            col = lambda k: {c: D.crop_coef(cr, "P", c, k) for c in CROPS}
            need, own, pool, mine0 = col("need_kg_ha"), col("own_kg_ha"), col("pool_kg_ha"), col("mine_kg_ha")
            own_perm = {c: own[c] * sum(v for g, v in (sh.get(c) or {}).items() if g in PERM_NGRP) for c in CROPS}
            _pf = (getattr(supply_result, "yield_price_factor", None) or {}) if supply_result is not None else {}
            sq = {}
            for c in CROPS:
                b_ = float(y0.get(c, 0.0) or 0.0)
                ys_ = b_ * yr[c] / float(_pf[c]) if float(_pf.get(c, 0.0) or 0.0) > 0 else None
                sq[c] = (need_yield_factor(region, c, b_, b_ * yr[c], None if ys_ is None else float(ys_), "P")
                         if (yr[c] > 0 and b_ > 0) else (1.0 if yr[c] > 0 else 0.0))
            grass = None
            if z:
                grass = (z, D.crop_coef(cr, "P", "GRAE", "need_kg_ha") - D.crop_coef(cr, "P", "GRAI", "need_kg_ha"),
                         sq.get("GRAS", 1.0))
            m = _pb.nutned_mineral(D, cr, need, own, own_perm, pool, mine0, xb, x, sq, E0, applied, grass)
            if m is None:
                raise RuntimeError(f"no CAPRI P need data for {region} ({cr})")
            minfer = max(0.0, m)
            src = "nutned"
        # runoff of manure P (RUNANI): CAPRI's N runoff share at the solution's options and winter cover
        ms = getattr(supply_result, "manure_tech_shares", None) if supply_result is not None else None
        wc = self._winter_cover_now(region, supply_result)[1]
        fmr = 0.0
        if supply_result is not None:
            fs = getattr(supply_result, "fert_tech_shares", None) or {}
            s_nim = float(fs.get("NITR_INH_MAN", 0.0) or 0.0)
            if s_nim > 0:
                from capri_mod.supply import n_leaching as _nl
                from capri_mod.supply.supply_module import fert_side_value as _fsv
                v_ = _fsv(region, "NITR_INH_MAN", "NO3MRUN")
                nm_ = float((getattr(supply_result, "fert_nmin", None) or {}).get("NITR_INH_MAN", 0.0) or 0.0)
                fmr = s_nim * (_nl.fert_effect(v_, nm_) if v_ is not None else 0.0)
        rt = self._p_runtot(region, ms, wc, fmr)
        runani = sum(h[a] * manp[a] * float(rt.get(a, 0.0)) for a in ANIMALS)
        b = _pb.balance(excret, excret - applied, minfer, cresid, expprd, runani)
        b["mineral_source"] = src
        return b
