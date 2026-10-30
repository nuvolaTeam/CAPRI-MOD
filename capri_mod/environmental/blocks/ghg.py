"""Greenhouse gases of the environmental accounts: manure N excretion and its loss shares, enteric and manure CH4, manure N2O (CAPRI's factors, the ammonia technologies' cascade, anaerobic digestion), CO2 coefficients (CAPRI's gases.gms and envind files).

EnvironmentalModule's methods, moved unchanged from capri_mod/environmental/environmental_module.py (refactor stage 4a,
docs/design/ARCHITECTURE_REFACTOR.md); the module-level names they use are environmental_module's, given to this
module once environmental_module is loaded (capri_mod.environmental.blocks.inject); the annotations are not evaluated.
"""
from __future__ import annotations


class GHGBlock:
    def _manure_loss_shares(self, region: str) -> dict:
        """CAPRI's manure N lost in housing and storage per kg excreted, by animal ((GASANI + RUNANI) / MANN, 2030
        reference; capri_data/2017/environment/manure_housing_losses_2030.csv). Raises where the data is missing."""
        c = self.__dict__.setdefault("_mloss_cache", {})
        if region not in c:
            t = self.data.get("manure_housing_losses") if hasattr(self, "data") else None
            if t is None:
                raise RuntimeError("no CAPRI manure housing losses (manure_housing_losses_2030.csv)")
            if region not in t.index:
                c[region] = {}
            else:
                r = t.loc[[region]]
                c[region] = dict(zip(r["animal"], r["loss_share"].astype(float)))
        return c[region]

    def _n_excretion(self, region: str, animal: str) -> float:
        cache = self.__dict__.setdefault("_nexc_cache", {})
        k = (region, animal)
        if k not in cache:
            cache[k] = self._n_excretion_uncached(region, animal)
        return cache[k]

    def _n_excretion_uncached(self, region: str, animal: str) -> float:
        """Manure N per head (kg), consistent with this model's herd units.

        First choice: CAPRI's 2017 regional manure N TOTAL for the activity
        divided by this model's herd (livestock_manure_n_coef.csv), built the
        same way as revenue per head. The previous source gave manure per CAPRI
        UNIT (animals fattened per year, 1,000 birds ...), while herds here are
        census stock, so EU totals were off by animal: bulls 0.17, heifers 0.10,
        calves 0.35, broilers 0.08, pigs 1.28, sheep and goats 1.49 of CAPRI's
        - near-cancelling in the EU total (0.93), but in the nitrogen constraint
        it put the burden on pigs and barely touched beef and poultry.
        """
        mc = self.data.get("livestock_manure_n_coef") if hasattr(self, "data") else None
        if mc is not None and region in mc.index and animal in mc.columns:
            import pandas as pd
            v = mc.at[region, animal]
            if pd.notna(v) and v > 0:
                return float(v)
        if mc is None:
            raise RuntimeError("livestock_manure_n_coef.csv is missing (tools/build/build_shg_split.py --reproduce)")
        return 0.0          # CAPRI has no such animal in the region (no herd)

    def _n_animal_products(self, region: str, activities) -> float:
        """N exported in animal products, t N (1000 head x kg N per head): CAPRI's CRPR_EXPT per model head."""
        tab = self.data.get("livestock_n_export_coef") if hasattr(self, "data") else None
        if tab is None:
            raise RuntimeError("livestock_n_export_coef.csv is missing (python tools/build/build_livestock_n_export_coef.py)")
        if region not in tab.index:
            return 0.0
        row = tab.loc[region]
        return float(sum(float(activities.get(a, 0.0)) * float(row[a]) for a in ANIMALS
                         if a in row.index and pd.notna(row[a])))

    def _ch4_per_head(self, kind: str, region: str, animal: str) -> float:
        """CAPRI's manure ("man") or enteric ("ent") CH4 per model head, kg (CH4MAN / CH4ENT: CAPRI total over the
        region's activities / the census herd; tools/build/build_ghg_coefs_2017.py; 2030 by CAPRI's reference factors).
        An animal CAPRI gives no such emission (poultry: no enteric CH4) has none."""
        tab = self.data.get("livestock_ch4%s_coef" % kind) if hasattr(self, "data") else None
        if tab is None:
            raise RuntimeError(f"livestock_ch4{kind}_coef.csv is missing (python tools/build/build_ghg_coefs_2017.py)")
        if region not in tab.index or animal not in tab.columns:
            return 0.0
        v = tab.at[region, animal]
        return float(v) if pd.notna(v) else 0.0

    def _co2_coefs(self, region: str):
        """(CO2 from liming, kg/ha of crop activity; urea share of mineral N), CAPRI's (crop_co2_coef.csv)."""
        tab = self.data.get("crop_co2_coef") if hasattr(self, "data") else None
        if tab is None:
            raise RuntimeError("crop_co2_coef.csv is missing (python tools/build/build_ghg_coefs_2017.py)")
        if region not in tab.index:
            return 0.0, 0.0
        return float(tab.at[region, "co2lim_kg_ha"]), float(tab.at[region, "urea_share"])

    def compute_ghg(
        self,
        activities: pd.Series,   # activity levels (1000 ha / 1000 heads)
        region: str,
        n_intensity: Optional[Dict[str, float]] = None,
        grass_shift: float = 0.0,
    ) -> Dict[str, float]:
        """
        Compute GHG emissions (kt CO2-eq) for a region. ``grass_shift``: grassland moved from
        intensive to extensive (1000 ha, Sprint 7a), whose fertiliser rate is GRAS's in proportion
        to CAPRI's need of each activity.

        Uses IPCC Tier 1 emission factors with EU-specific adjustments.
        """
        ghg = {g: 0.0 for g in GHG_TYPES}

        # 1. Enteric fermentation (CH4); nitrate in the ration: -10% per point of DM
        _ns = getattr(self, "_nitrate_share_now", None) or {}
        for animal in ANIMALS:
            heads = activities.get(animal, 0.0) * 1000  # convert 1000→heads
            _sf = float(((getattr(self, "_supp_ch4", None) or {}).get(region) or {}).get(animal, 1.0))
            ef    = self._ch4_per_head("ent", region, animal) * max(0.0, 1.0 - 10.0 * float(_ns.get(animal, 0.0))) * _sf
            ch4   = heads * ef / 1e6   # kt CH4
            # CATTLE FROM THE FEED MIX (CAPRI GWPCH4ENT_, envind/gases.gms): sum over feeds of
            # DM (t) x 1000 x GE (Mcal/kg DM) x 4.1868 x Ym / 55.65, in kt (/1e6)
            _fd = (getattr(self, "_feed_dm_now", None) or {}).get(animal)
            _fac = self._enteric_factors().get(animal) if _fd else None
            if _fd and _fac:
                _ctry = MS_CODE.get(str(getattr(self, "_region_now", ""))[:2],
                                                                        str(getattr(self, "_region_now", ""))[:2]) + "000000"
                _ge = _fac["ge"].get(_ctry) or _fac["ge"].get("EU")
                if _ge:
                    _kg = sum(float(dm_t) * 1000.0 * float(_ge.get(f, _ge.get("_mean", 0.0))) for f, dm_t in _fd.items())
                    ch4 = _kg * 4.1868 * _fac["ym"] / 55.65 / 1e6 * max(0.0, 1.0 - 10.0 * float(_ns.get(animal, 0.0))) * _sf
            ghg["CH4_ENT"] += ch4 * GWP_CH4   # kt CO2-eq

        # 2. Manure management (CH4 + N2O)
        for animal in ANIMALS:
            heads  = activities.get(animal, 0.0) * 1000
            n_excr = self._n_excretion(region, animal) * heads / 1e6  # kt N

            # CH4 from manure
            ef_ch4 = self._ch4_per_head("man", region, animal)
            ghg["CH4_MAN"] += (heads * ef_ch4 / 1e6) * GWP_CH4

            # N2O from manure: CAPRI's shares of manure N lost as N2O-N by stage - housing and
            # storage, application, grazing, leaching (gases.gms N2OMAN, N2OAPP, N2OGRA, N2OLEA;
            # tools/build/build_manure_n2o.py); the technologies' effects are applied in the accounts.
            # Indirect N2O from volatilised NH3 is its own item (N2O_IND). Without CAPRI's factors
            # for the region and animal: none (no herd; tests check every herd has them).
            _mf = self._manure_n2o_factor(region, animal)
            n2o_n = n_excr * (sum(_mf) if _mf is not None else 0.0)    # kt N2O-N
            n2o   = n2o_n * 44 / 28            # kt N2O
            ghg["N2O_MAN"] += n2o * GWP_N2O

        # 3. Agricultural soils (N2O)
        # N applied to soils = mineral fertiliser + organic (from manure) + fixation
        total_n_applied = 0.0
        for crop in CROPS:
            area = activities.get(crop, 0.0)
            n_rate = self._base_mineral_rate(region, crop) if area > 0 else 0.0
            # fertiliser per ha follows the crop's N intensity (1 = base)
            n_rate = n_rate * float((n_intensity or {}).get(crop, 1.0))
            total_n_applied += area * n_rate / 1e3   # 1000 ha x kg/ha = t; /1e3 -> kt N
            # (was /1e6: soil N2O, liming and urea CO2 came out in Mt while every other gas is in kt,
            # so the GHG total left them out - 83 kt of soil N2O in the EU instead of 83 Mt)

        if grass_shift:
            dl = self.grass_intensity_delta(region) or {}
            r_g = self._base_mineral_rate(region, "GRAS")
            if r_g > 0:
                # the grassland intensity shift's change of mineral N per ha (kg) on the shifted area (1000 ha)
                total_n_applied += grass_shift * float(dl.get("mineral_rate", 0.0)) / 1e3
        # Direct N2O from soils
        n2o_soil_n = total_n_applied * EF_SOIL_N2O_DIRECT
        ghg["N2O_SOIL"] += (n2o_soil_n * 44 / 28) * GWP_N2O

        # Indirect N2O (volatilisation path)
        n2o_indirect_n = total_n_applied * 0.10 * EF_SOIL_N2O_INDIRECT
        ghg["N2O_SOIL"] += (n2o_indirect_n * 44 / 28) * GWP_N2O

        # 4. Liming (CO2): CAPRI's coefficient per ha of every crop activity, grassland and fallow included
        # (gases.gms (16): the region's UAAR CO2LIM, kg CO2/ha; tools/build/build_ghg_coefs_2017.py)
        lim, urea_share = self._co2_coefs(region)
        ghg["CO2_LIME"] = sum(activities.get(c, 0.0) for c in CROPS) * lim / 1e3     # 1000 ha x kg/ha -> kt CO2

        # 5. Urea (CO2): mineral N x the member state's urea share x 44/28 (gases.gms (17)); compute_indicators
        # applies it to the balance's mineral N, as soil N2O
        ghg["CO2_UREA"] = total_n_applied * urea_share * 44.0 / 28.0

        return ghg

    def _enteric_factors(self) -> dict:
        """{animal: {"ym": Ym, "ge": {country: {feed: GE Mcal/kg DM, "_mean": ...}}}} from
        capri_data/2017/environment/enteric_feed_factors.csv (tools/build/build_enteric_feed_factors.py)."""
        cls = type(self)
        if cls._ENT_CACHE is None:
            out = {}
            rows = _inputs.current().rows("enteric_feed_factors.csv", "environment", required=False)
            if rows is not None:
                for r in rows:
                    if not r["ym"]:
                        continue
                    d = out.setdefault(r["animal"], {"ym": float(r["ym"]), "ge": {}})
                    d["ge"].setdefault(r["country"], {})[r["feed"]] = float(r["ge_mcal_per_kg_dm"])
                for d in out.values():
                    for g in d["ge"].values():
                        g["_mean"] = sum(g.values()) / len(g)
            cls._ENT_CACHE = out
        return cls._ENT_CACHE

    def _manure_n2o_factor(self, region, animal):
        """(f_man, f_app, f_gra, f_lea), t N2O-N per t of manure N (capri_data/2017/environment/
        manure_n2o_factors.csv), or None."""
        tab = self.__dict__.get("_mn2o_cache")
        if tab is None:
            t_ = _inputs.current().csv("manure_n2o_factors.csv", "environment", required=False)
            tab = ({(r.region, r.animal): (float(r.f_man), float(r.f_app), float(r.f_gra), float(r.f_lea))
                    for r in t_.itertuples()} if t_ is not None else {})
            self._mn2o_cache = tab
        return tab.get((region, animal))

    def _manure_n2o_tech(self, region):
        """{animal: {technology: (r_hou, r_app)}} (manure_n2o_tech.csv) and base shares {animal:
        {technology: share}} (ammonia_tech_model.csv ini, weighted as the supply model reports)."""
        cache = self.__dict__.setdefault("_mn2o_tech_cache", {})
        if region not in cache:
            inp = _inputs.current()
            if "_mn2o_tech_tab" not in self.__dict__:
                t_ = inp.csv("manure_n2o_tech.csv", "environment", required=False)
                self._mn2o_tech_tab = t_ if t_ is not None else pd.DataFrame(
                    columns=["region", "animal", "technology", "r_hou", "r_app"])
                from capri_mod.supply import ammonia_techs as _at
                self._amm_tm = _at.load(inp.path("ammonia_tech_model.csv", "abatement/ammonia"))
            t = self._mn2o_tech_tab[self._mn2o_tech_tab["region"] == region]
            eff = {}
            for r in t.itertuples():
                eff.setdefault(r.animal, {})[r.technology] = (float(r.r_hou), float(r.r_app))
            s0 = {}
            for a, subs in (self._amm_tm.get(region) or {}).items():
                for sb in subs:
                    for tt in sb["techs"]:
                        s0.setdefault(a, {})[tt["tech"]] = s0.get(a, {}).get(tt["tech"], 0.0) + sb["w"] * tt["ini"]
            cache[region] = (eff, s0)
        return cache[region]

    def _manure_n2o_cascade(self, region, animal, sh, s0):
        """(housing, application) multipliers of manure N2O from the N left after NH3 losses at
        shares sh against the base shares s0, over the animal's CAPRI sub-activities weighted by
        their manure N (ammonia_tech_model.csv; capri_mod/supply/ammonia_techs.stage_n)."""
        from capri_mod.supply import ammonia_techs as _at
        subs = (getattr(self, "_amm_tm", None) or {}).get(region, {}).get(animal) or []
        if not subs:
            return 1.0, 1.0
        full1 = {t: sh.get(t, s0.get(t, 0.0)) for t in set(s0) | set(sh)}
        H1 = F1 = H0 = F0 = 0.0
        for sb in subs:
            w = float(sb["w"]) * float(sb.get("mrel", 1.0) or 1.0)
            h1, f1 = _at.stage_n(sb, full1)
            h0, f0 = _at.stage_n(sb, {t["tech"]: t["ini"] for t in sb["techs"]})
            H1 += w * h1; F1 += w * f1; H0 += w * h0; F0 += w * f0
        return (H1 / H0 if H0 > 0 else 1.0), (F1 / F0 if F0 > 0 else 1.0)

    def _ad_ch4_factor(self, region, animal, ms, s0):
        """Manure CH4 at the AD share against the base share (ratio), over the animal's sub-activities weighted by
        their manure N; None without AD for the animal."""
        subs = [sb for sb in ((getattr(self, "_amm_tm", None) or {}).get(region, {}).get(animal) or []) if sb.get("ad")]
        if not subs:
            return None
        s1 = float(ms.get((animal, "AD_AnCh"), s0.get("AD_AnCh", 0.0)) or 0.0)
        b0 = float(s0.get("AD_AnCh", 0.0) or 0.0)
        F1 = F0 = W = 0.0
        for sb in subs:
            w = float(sb["w"]) * float(sb.get("mrel", 1.0) or 1.0)
            lg, r = sb["ad"]
            act = sb["key"].partition("|")[2]
            k = 0.0 if (self.ad_dairy_ch4 == "capri" and act in ("DCOL", "DCOH")) else (1.0 - r) / lg
            F1 += w * (1.0 - s1 * k); F0 += w * (1.0 - b0 * k); W += w
        return F1 / F0 if F0 > 0 else 1.0

    def _manure_n2o_full(self, region, animal, sh, s0, wc=(0.0, 0.0)):
        """(housing and storage, application) multipliers of manure N2O at option shares sh against the base shares
        s0 through CAPRI's full cascade (ammonia_techs.n2o), the animal's sub-activities weighted by their manure N;
        None where a sub-activity has no cascade data."""
        from capri_mod.supply import ammonia_techs as _at
        subs = (getattr(self, "_amm_tm", None) or {}).get(region, {}).get(animal) or []
        if not subs or any(_at.cascade_data(sb) is None for sb in subs):
            return None
        full1 = {t: sh.get(t, s0.get(t, 0.0)) for t in set(s0) | set(sh)}
        H1 = A1 = H0 = A0 = 0.0
        for sb in subs:
            w = float(sb["w"]) * float(sb.get("mrel", 1.0) or 1.0)
            h1, a1 = _at.n2o(sb, full1, wc[1])
            h0, a0 = _at.n2o(sb, {t["tech"]: t["ini"] for t in sb["techs"]}, wc[0])
            H1 += w * h1; A1 += w * a1; H0 += w * h0; A0 += w * a0
        return (H1 / H0 if H0 > 0 else 1.0), (A1 / A0 if A0 > 0 else 1.0)
