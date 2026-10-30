"""Nitrogen of the environmental accounts: CAPRI's gross nitrogen balance (e_SURTOTHa) and its items, the fertiliser distribution, manure trade and substitution, the fertiliser options' side effects, winter cover, leaching and mineral N2O.

EnvironmentalModule's methods, moved unchanged from capri_mod/environmental/environmental_module.py (refactor stage 4a,
docs/design/ARCHITECTURE_REFACTOR.md); the module-level names they use are environmental_module's, given to this
module once environmental_module is loaded (capri_mod.environmental.blocks.inject); the annotations are not evaluated.
"""
from __future__ import annotations


class NitrogenBlock:
    def set_manure_trade(self, on: bool) -> None:
        """CAPRI's manure trade on or off for the run (CAPRIModel; the base trade shares count only when on)."""
        on = bool(on)
        if getattr(self, "manure_trade_on", True) != on:
            self.__dict__.pop("_sub_cache", None)
        self.manure_trade_on = on

    def _substitution(self, region):
        """(marginal availability/efficiency, manure-covered need per ha of crops at base).

        The first term is mineral N replaced per unit of manure N at the margin
        (_manure_marginal_factor, CAPRI's NUTNED_ with its endogenous availability).
        The second term is the base manure N available to crops (after export,
        plus imports) times availability/efficiency, spread per ha of base
        cropland: the part of the crops' need that manure covered at base.
        """
        cache = self.__dict__.setdefault("_sub_cache", {})
        if region in cache:
            return cache[region]
        out = None
        try:
            ratio = self._manure_marginal_factor(region)
            if ratio is not None:
                A = self.data["areas"]; H = self.data.get("animal_numbers")
                area0 = float(sum(float(A.at[region, c]) for c in A.columns if c in CROPS)) if region in A.index else 0.0
                man0 = 0.0
                if H is not None and region in H.index:
                    man0 = sum(float(H.at[region, a]) * self._n_excretion(region, a) for a in H.columns if a in ANIMALS)
                mt = self.data.get("manure_trade") if getattr(self, "manure_trade_on", True) else None
                if mt is not None and region in mt.index:
                    man0 *= max(0.0, 1.0 - float(mt.at[region, "export_share"]))
                    imp_ha = float(mt.at[region, "import_kg_n_per_ha"])
                else:
                    imp_ha = 0.0
                if area0 > 0 and ratio == ratio:
                    out = (ratio, ratio * (man0 / area0 + imp_ha))
        except Exception:
            out = None
        cache[region] = out
        return out

    def _gnb_row(self, region):
        """CAPRI's 2030 balance items for the CAPRI region of a model region (national where the
        region is not separate in CAPRI), from capri_gnb_components_2030.csv, or {}."""
        g = getattr(type(self), "_GNB_TOT", None)
        if g is None:
            g = _inputs.current().csv("capri_gnb_components_2030.csv", "environment").pivot_table(
                index="capri_region", columns="item", values="kg_n_per_ha")
            type(self)._GNB_TOT = g
        self._capri_crop_n(region)                         # builds the region map
        r8 = getattr(type(self), "_CROP_N_MAP", {}).get(region)
        if r8 is None or r8 not in g.index:
            r8 = capri_ms(region)
        return g.loc[r8].to_dict() if r8 in g.index else {}

    def _manure_marginal_factor(self, region):
        """Mineral N replaced per unit of manure N applied, at the margin (CAPRI NUTNED_).

        NUTNED_ is an equality: crop need = mineral x (1 - losses) + manure x availability +
        residues. Manure distribution across crop groups is free, so a change in manure changes
        mineral N by availability / mineral efficiency whatever the minimum-mineral floors of
        individual groups (they bind only when manure grows). With CAPRI's endogenous availability
        (endoManAvFact, on in the Green Deal runs; fert/endoManAvail.gms) availability falls with
        manure per ha: g = g0 + b (m - m0), b = -0.0015 per kg N/ha, flattened so that g stays
        within [min(0.2, g0), max(0.999, g0)] between 0 and max(300, m0) kg/ha. The manure N
        available to crops is m g(m), whose derivative at base is g0 + b m0.
        Data: CAPRI 2030 reference, fertDist_excr / nutNed_excr_unavailable / fertDist_mine /
        nutNed_mine_loss per ha (capri_gnb_components_2030.csv); the earlier table
        (fertiliser_substitution_2030.csv) where those are missing."""
        row = self._gnb_row(region)
        g0 = eff = m0 = None
        try:
            ex = float(row.get("fertDist_excr_perha", float("nan")))
            un = float(row.get("nutNed_excr_unavailable_perha", float("nan")))
            mi = float(row.get("fertDist_mine_perha", float("nan")))
            lo = float(row.get("nutNed_mine_loss_gasRunTot_perha", float("nan")))
            if ex == ex and un == un and ex > 0:
                g0, m0 = 1.0 + un / ex, ex
            if mi == mi and lo == lo and mi > 0:
                eff = 1.0 + lo / mi
        except Exception:
            pass
        fs = self.data.get("fertiliser_substitution") if hasattr(self, "data") else None
        if fs is not None and region in fs.index:
            if g0 is None:
                g0 = float(fs.at[region, "manure_availability"])
            if eff is None:
                eff = float(fs.at[region, "mineral_efficiency"])
        if g0 is None or not eff or eff <= 0:
            return None
        if m0 is None or m0 <= 0:
            return g0 / eff
        b = self.ENDO_MAN_AV_SLOPE
        if g0 - m0 * b > max(0.999, g0):
            b = (g0 - max(0.999, g0)) / m0
        top = max(300.0, m0) - m0
        if top > 0 and g0 + top * b < min(0.2, g0):
            b = (min(0.2, g0) - g0) / top
        return max(g0 + b * m0, 0.0) / eff

    def _cached_row(self, key: str, region: str):
        """One region's row of a data table as a plain dict, cached (or None)."""
        cache = self.__dict__.setdefault("_row_cache", {})
        ck = (key, region)
        if ck not in cache:
            t = self.data.get(key) if hasattr(self, "data") else None
            cache[ck] = (t.loc[region].to_dict()
                         if t is not None and hasattr(t, "index") and region in t.index else None)
        return cache[ck]

    def _capri_crop_n(self, region):
        """{model crop: (removal, residues, fixation) kg N per ha} for this region from CAPRI's 2030
        reference, each item scaled so the region's totals equal CAPRI's EXPPRD and CRESID."""
        cls = type(self)
        if cls._CROP_N is None:
            inp = _inputs.current()
            cls._CROP_N = {}
            t = inp.csv("capri_crop_n_coefs_2030.csv", "environment")
            tot = inp.csv("capri_gnb_components_2030.csv", "environment").pivot_table(
                index="capri_region", columns="item", values="kg_n_per_ha")
            # the model's regions are CAPRI's units: each its own CAPRI region (a dict that returns the key)
            cls._CROP_N_MAP = IdentityMap()
            for r8, g8 in t.groupby("capri_region"):
                d = {row.crop: row for row in g8.itertuples(index=False)}
                if "GRAE" in d or "GRAI" in d:
                    d.pop("GRAS", None)                       # aggregate of GRAE + GRAI
                lv = sum(float(x.levl) for x in d.values())
                if r8 not in tot.index or lv <= 0:
                    continue
                # Removal key per crop: the crop's NITF in CAPRI's results is its need NET of
                # biological fixation (NUTNED_: retention x (1 - fBNF) x over-fertilisation), while
                # fixation is fBNF of the gross need (JRC96482, eq. 1: Nbiofix = NITF x LEVL x fBNF,
                # fBNF 75% for soya and pulses, 5-17% for grass). Gross need = NITF + fixation per ha
                # (pulses: 52 + 149 kg/ha in Saxony-Anhalt, removal 4x the net figure).
                def _gross(x):
                    fx = float(x.biofix_t) * 1000.0 / float(x.levl) if (x.biofix_t == x.biofix_t and float(x.levl) > 0) else 0.0
                    return float(x.nitf) + fx
                sx = sum(float(x.levl) * _gross(x) for x in d.values())
                # NCRD = "N from crop residues and atmospheric deposition, kg/ha" (sets.gms);
                # e_CRESID: CRESID + ATMOSD = sum levl x NCRD, so residues = NCRD - deposition
                dep = float(tot.at[r8, "ATMOSD"]) if "ATMOSD" in tot.columns else 0.0
                res_ha = lambda x: max(0.0, (float(x.ncrd) if x.ncrd == x.ncrd else 0.0) - dep) \
                    if (x.ncrd == x.ncrd and float(x.ncrd) > 0) else 0.0
                sr = sum(float(x.levl) * res_ha(x) for x in d.values())
                uaa = lv
                ke = float(tot.at[r8, "EXPPRD"]) * uaa / sx if sx > 0 and "EXPPRD" in tot.columns else 1.0
                kr = float(tot.at[r8, "CRESID"]) * uaa / sr if sr > 0 and "CRESID" in tot.columns else 0.0
                out = {}
                from capri_mod.data.definitions import CROPS as _CR
                for mc in _CR:
                    src = [d[c] for c in cls._CAPRI_CROP.get(mc, (mc,)) if c in d]
                    L = sum(float(x.levl) for x in src)
                    if L <= 0:
                        continue
                    rem = sum(float(x.levl) * _gross(x) for x in src) / L * ke
                    res = sum(float(x.levl) * res_ha(x) for x in src) / L * kr
                    fix = sum((float(x.biofix_t) if x.biofix_t == x.biofix_t else 0.0) for x in src) * 1000.0 / L
                    out[mc] = (rem, res, fix)
                # CAPRI's two grassland activities on their own (the model's GRAS pools
                # them; grass_intensity_delta() needs each)
                for gc in ("GRAE", "GRAI"):
                    if gc in d and float(d[gc].levl) > 0:
                        x = d[gc]
                        out[gc] = (_gross(x) * ke, res_ha(x) * kr,
                                   (float(x.biofix_t) if x.biofix_t == x.biofix_t else 0.0) * 1000.0 / float(x.levl))
                cls._CROP_N[r8] = out
        to8 = getattr(cls, "_CROP_N_MAP", {})
        r8 = to8.get(region)
        if r8 is None or r8 not in cls._CROP_N:
            nc = capri_ms(region)
            r8 = nc
        res = cls._CROP_N.get(r8)
        ov = self.__dict__.get("_grass_override")
        if ov and res and ov in res:
            res = dict(res); res["GRAS"] = res[ov]
        return res

    def _base_mineral_rate(self, region, crop):
        """Base mineral N per ha of a crop: CAPRI's regional NMIN; none where CAPRI has none (fallow, set-aside: CAPRI's
        results carry no NMIN for FALL, VSET, SETA; K100)."""
        _regn = self._cached_row("mineral_n_regional", region)
        rate = None
        if _regn is not None and crop in _regn:
            v = _regn[crop]
            if v == v and v > 0:
                rate = float(v)
        if rate is None:
            rate = 0.0
        ov = self.__dict__.get("_grass_override")
        if ov and crop == "GRAS":
            # one of CAPRI's grassland activities: the GRAS rate in proportion to its need
            # (removal net of fixation) over the pooled GRAS need
            self.__dict__["_grass_override"] = None
            try:
                cn = self._capri_crop_n(region) or {}
            finally:
                self.__dict__["_grass_override"] = ov
            if ov in cn and "GRAS" in cn:
                w_ov = max(cn[ov][0] - cn[ov][2], 0.0)
                w_g = max(cn["GRAS"][0] - cn["GRAS"][2], 0.0)
                if w_g > 0:
                    rate *= w_ov / w_g
        return rate

    def grass_intensity_delta(self, region, n_intensity=None) -> dict:
        """Balance change (t N per 1000 ha) of moving grassland from CAPRI's intensive activity
        GRAI to its extensive GRAE: the unit balance of a hectare of GRAE minus one of GRAI, each
        with its own CAPRI removal, residues and fixation and its share of the GRAS mineral rate by
        need, at base yield; manure and residue credits keep the base distribution by need.
        Used for the supply model's extensification column and for the accounts, so the two agree."""
        cache = self.__dict__.setdefault("_grass_delta_cache", {})
        key = (region, tuple(sorted((n_intensity or {}).items())))
        if key in cache:
            return cache[key]
        cn = self._capri_crop_n(region) or {}
        if "GRAE" not in cn or "GRAI" not in cn:
            cache[key] = None
            return None
        self._need_base(region); self._residue_availability(region)      # base caches first
        y0 = self._cached_row("yields", region) or {}
        out = {}
        try:
            for gc in ("GRAE", "GRAI"):
                self.__dict__["_grass_override"] = gc
                out[gc] = self.compute_nitrogen_balance({"GRAS": 1.0}, y0, region, n_intensity)
        finally:
            self.__dict__["_grass_override"] = None
        d = {k: float(out["GRAE"].get(k, 0.0)) - float(out["GRAI"].get(k, 0.0))
             for k in out["GRAE"] if isinstance(out["GRAE"].get(k), (int, float))}
        rates = []
        for gc in ("GRAE", "GRAI"):
            self.__dict__["_grass_override"] = gc
            try:
                rates.append(self._base_mineral_rate(region, "GRAS"))
            finally:
                self.__dict__["_grass_override"] = None
        d["mineral_rate"] = rates[0] - rates[1]
        cache[key] = d
        return d

    def _need_weight(self, region, crop):
        """A crop's N need per ha at base yield, the key by which CAPRI distributes manure and
        pooled residues (eq. 5.10: need = retention x (1 - biological-fixation share) x
        over-fertilisation): CAPRI's removal net of fixation; the mineral rate where CAPRI has
        no coefficient."""
        cn = self._capri_crop_n(region)
        if cn and crop in cn:
            return max(float(cn[crop][0]) - float(cn[crop][2]), 0.0)
        return self._base_mineral_rate(region, crop)

    def _need_base(self, region):
        """(base crop need weight M0 = sum of base area x base mineral rate, base cropland A0).

        CAPRI spreads available manure and residue N over crops BY NEED (NUTNED_,
        fertDistExcr_); the base mineral rate is the model's crop-need weight, so a hectare
        of fallow (no need, no fertiliser) receives no manure or residue credit."""
        cache = self.__dict__.setdefault("_need_base_cache", {})
        if region in cache:
            return cache[region]
        M0 = A0 = Ma = 0.0
        A = self.data["areas"] if hasattr(self, "data") else None
        if A is not None and region in A.index:
            for c in CROPS:
                if c in A.columns:
                    a = float(A.at[region, c] or 0.0)
                    if a > 0:
                        A0 += a
                        M0 += a * self._need_weight(region, c)
                        if c not in self.OWN_RESIDUE_CROPS:
                            Ma += a * self._need_weight(region, c)
        cache[region] = (M0, A0, Ma)
        return M0, A0, Ma

    def _residue_availability(self, region):
        """(availability of residue N to crops, base ARABLE residue N per unit of arable crop need)."""
        cache = self.__dict__.setdefault("_res_av_cache", {})
        if region in cache:
            return cache[region]
        av, r0 = 0.0, 0.0
        cn = self._capri_crop_n(region) or {}
        try:
            g = getattr(type(self), "_GNB_TOT", None)
            if g is None:
                g = _inputs.current().csv("capri_gnb_components_2030.csv", "environment").pivot_table(
                    index="capri_region", columns="item", values="kg_n_per_ha")
                type(self)._GNB_TOT = g
            to8 = getattr(type(self), "_CROP_N_MAP", {})
            r8 = to8.get(region)
            if r8 is None or r8 not in g.index:
                r8 = capri_ms(region)
            if r8 in g.index:
                pool = float(g.at[r8, "CRESID"]) + float(g.at[r8, "ATMOSD"])
                lost = -float(g.loc[r8].get("nutNed_cres_unavailable_perha", 0.0) or 0.0) \
                       - float(g.loc[r8].get("nutNed_cres_loss_gasRunTot_perha", 0.0) or 0.0)
                if pool > 0 and lost == lost:
                    av = min(max(1.0 - lost / pool, 0.0), 1.0)
            areas = self.data["areas"].loc[region] if region in self.data["areas"].index else None
            _, _, Ma = self._need_base(region)
            if areas is not None and Ma > 0:
                R = sum(float(areas.get(c, 0.0) or 0.0) * cn[c][1] for c in cn
                        if c not in self.OWN_RESIDUE_CROPS)
                r0 = R / Ma
        except Exception:
            av, r0 = 0.0, 0.0
        cache[region] = (av, r0)
        return av, r0

    def unit_nitrogen_balance(self, activity: str, yields, region: str,
                              n_intensity: Optional[Dict[str, float]] = None, yields_scen=None) -> Dict[str, float]:
        """compute_nitrogen_balance for ONE unit of one activity, memoised. The balance of {a: 1} reads only the
        activity's own yield (and its yield before the price response, yields_scen), its own intensity factor and the
        "__credit__" factor (plus static data and the manure trade setting), so those form the key; the supply models
        ask for it hundreds of thousands of times per run."""
        y = yields.get(activity) if hasattr(yields, "get") else None
        ys = yields_scen.get(activity) if hasattr(yields_scen, "get") else None
        mi = n_intensity or {}
        key = (region, activity, None if y is None else float(y), None if ys is None else float(ys),
               mi.get(activity), mi.get("__credit__"), bool(getattr(self, "manure_trade_on", True)))
        memo = self.__dict__.setdefault("_unit_nb_memo", {})
        r = memo.get(key)
        if r is None:
            r = self.compute_nitrogen_balance({activity: 1.0}, yields, region, n_intensity, yields_scen=yields_scen)
            memo[key] = r
        return dict(r)

    def compute_nitrogen_balance(
        self,
        activities: pd.Series,
        yields: pd.Series,
        region: str,
        n_intensity: Optional[Dict[str, float]] = None,
        yields_scen=None,
    ) -> Dict[str, float]:
        """
        Compute soil nitrogen balance (OECD/Eurostat methodology).

        Crop need per ha follows the yield by CAPRI's rule (capri_mod.fert.npk.need_yield_factor); yields_scen: the
        crops' yields before the price response (the straw part of the need follows those), None: the yields.

        N inputs:
          - Mineral fertilizer
          - Organic manure
          - Biological N fixation (legumes)
          - Atmospheric deposition
          - Other organic inputs

        N outputs:
          - Crop N uptake (= yield × N content coefficient)
          - N in animal products

        Surplus = Inputs - Outputs (kg N / ha)
        """
        n = {}

        # --- Inputs ---
        # Mineral fertilizer (from nutrient coefficients × area)
        n_mineral = 0.0
        # CAPRI reports mineral (NMIN) and manure (NMAN) nitrogen separately per
        # activity and region; their EU totals, 9.47 and 5.89 Mt N, match the
        # real ~10.8 and ~7. Regional rates matter: a single EU-wide table gave
        # German regions EU-average fertilisation and a surplus of 14 kg N/ha
        # where Germany's is among Europe's highest.
        _reg_n = self.data.get("mineral_n_regional") if hasattr(self, "data") else None
        _sub = self._substitution(region)
        # fixed per-region data, cached as plain dicts (identical values; pandas
        # row and cell access dominated the cost of this function)
        _ybase = self._cached_row("yields", region)
        _regn = self._cached_row("mineral_n_regional", region)
        if hasattr(activities, "to_dict"):
            activities = activities.to_dict()
        if hasattr(yields, "to_dict"):
            yields = yields.to_dict()
        if hasattr(yields_scen, "to_dict"):
            yields_scen = yields_scen.to_dict()
        _ysc = yields_scen if hasattr(yields_scen, "get") else {}

        def _nyf(c_, y0_, y_):
            ys_ = _ysc.get(c_)
            return need_yield_factor(region, c_, y0_, y_, None if ys_ is None else float(ys_), "N")
        n_mineral_plain = 0.0
        n_need_manure_part = 0.0
        n_need_w = 0.0                      # crop need weight: base mineral rate x intensity x need factor of yield
        _M0, _A0, _ = self._need_base(region) if _sub is not None else (0.0, 0.0, 0.0)
        _sub_w = (_sub[1] * _A0 / _M0) if (_sub is not None and _M0 > 0) else 0.0
        # Crop factors (n_intensity[crop]) = organic share x technology factor scale the crop's
        # own mineral rate; the parts of need covered by manure and residues scale with the
        # technology factor alone ("__credit__"). Organic land uses no mineral N (CAPRI
        # organic_minfert_redu.gms) but its need is still met by manure and residues, so mineral
        # N falls by the organic share of the MINERAL rate - scaling the whole need cut it by up
        # to twice the mineral actually applied where manure covers most need.
        _fc = float((n_intensity or {}).get("__credit__", 1.0))
        for crop in CROPS:
            area = activities.get(crop, 0.0)
            _m = float((n_intensity or {}).get(crop, 1.0))
            # need follows yield by CAPRI's rule (fert/fertned.gms; need_yield_factor)
            _sq = 1.0
            if _sub is not None and area > 0 and _ybase is not None:
                _y0 = float(_ybase.get(crop, 0.0)); _y = float(yields.get(crop, _y0)) if hasattr(yields, "get") else _y0
                if _y0 > 0 and _y > 0:
                    _sq = _nyf(crop, _y0, _y)
            rate = self._base_mineral_rate(region, crop) if area > 0 else 0.0
            n_mineral_plain += area * rate * _m
            n_mineral += area * rate * _m * _sq
            _w = self._need_weight(region, crop) if (area > 0 and _sub is not None) else 0.0
            if crop not in self.OWN_RESIDUE_CROPS:
                n_need_w += area * _w * _fc * _sq
            if _sub is not None and area > 0:
                # the manure-covered part of need, spread over crops BY NEED (CAPRI
                # fertDistExcr_): sub[1] per ha of base cropland = sub[1] x A0 / M0 per
                # unit of need; fallow carries none
                n_need_manure_part += area * _w * _fc * _sq * _sub_w

        # Organic N from manure
        n_organic = 0.0
        n_housing_loss = 0.0          # CAPRI GASANI + RUNANI: lost in housing and storage before application
        _ls = self._manure_loss_shares(region)
        for animal in ANIMALS:
            # Activity levels are in 1000 head and _n_excretion returns kg N per
            # head per year (DCOW ~105, matching the literature 100-120), so the
            # product is already in the same 1000-kg-N unit as every other term
            # here (deposition is area in 1000 ha x 20 kg/ha). The previous
            # `heads * 1000 ... / 1e6` divided by a further 1000 and left manure
            # N at effectively ZERO in the balance — FR10 showed 0.0 kg N/ha of
            # organic input against a real EU average near 55.
            heads_1000 = activities.get(animal, 0.0)
            n_excr = self._n_excretion(region, animal)
            n_organic += heads_1000 * n_excr
            n_housing_loss += heads_1000 * n_excr * float(_ls.get(animal, 0.0))
        # MANURE TRADE (CAPRI's manExportOrAppl_): exporting regions keep
        # (1 - export share) of their manure N, importing regions receive
        # manure spread over their cropland. Shares from CAPRI's 2030 reference
        # (tools/build/build_manure_trade_base.py: 1.2 Mt N traded between regions).
        # only where the run trades manure (CAPRI's manureTradeNew; a scenario setting held for its baseline: without
        # it, as JRC121368's CAPRI, every region keeps all its manure, Sprint 9j)
        _mt = self.data.get("manure_trade") if (hasattr(self, "data") and getattr(self, "manure_trade_on", True)) else None
        _exp_sh, _imp_ha = 0.0, 0.0
        if _mt is not None and region in getattr(_mt, "index", []):
            _exp_sh = float(_mt.at[region, "export_share"])
            _imp_ha = float(_mt.at[region, "import_kg_n_per_ha"])
        n_organic *= max(0.0, 1.0 - _exp_sh)

        # CAPRI's crop removal, crop residues and biological fixation per crop and region
        # (supply_model.gms e_EXPPRD, e_CRESID, e_BIOFIX; 2030 reference coefficients,
        # capri_crop_n_coefs_2030.csv), scaled with the current yield over the model's own
        # base yield (CAPRI multiplies by its yield factors). Replaces the hard-coded N
        # contents per tonne (wheat 20 kg/t, default 10) and fixation rates, which removed
        # 40% more N than CAPRI's net removal and left out the residue input.
        _cn = self._capri_crop_n(region)
        n_residues = 0.0
        _own_need = _own_res = 0.0
        n_crop_uptake_c = n_fix_c = 0.0
        if _cn:
            for crop in CROPS:
                area = activities.get(crop, 0.0)
                co = _cn.get(crop)
                if area <= 0 or co is None:
                    continue
                yr = 1.0
                _nf = 1.0
                if _ybase is not None:
                    _y0 = float(_ybase.get(crop, 0.0) or 0.0)
                    _y = float(yields.get(crop, _y0) or 0.0) if hasattr(yields, "get") else _y0
                    if _y0 > 0 and _y >= 0:
                        yr = _y / _y0
                        _nf = _nyf(crop, _y0, _y) if _y > 0 else 0.0
                n_crop_uptake_c += area * co[0] * yr
                n_residues += area * co[1] * yr
                if crop in self.OWN_RESIDUE_CROPS:
                    # own residues cover own need: base credit x intensity x CAPRI's need factor of the
                    # yield on the need side, residues actually left on the credit side
                    _fc_ = float((n_intensity or {}).get("__credit__", 1.0))
                    _own_need += area * co[1] * _fc_ * _nf
                    _own_res += area * co[1] * yr
                n_fix_c += area * co[2] * yr

        # Biological N fixation: CAPRI's per crop and region (BIOFIX, _capri_crop_n)
        if not _cn and any(activities.get(c, 0.0) > 0 for c in CROPS):
            raise RuntimeError(f"no CAPRI crop N coefficients for {region} (capri_crop_n_coefs_2030.csv)")
        n_fixation = n_fix_c

        # Atmospheric deposition (~20 kg N/ha/year EU average)
        total_uaa = sum(activities.get(a, 0.0) for a in CROPS)
        # Atmospheric deposition per region from CAPRI's 2030 reference
        # (EMEP-based; median 10 kg N/ha, 1-48 by region), replacing a flat
        # 20 kg N/ha that put EU deposition at 1.8x CAPRI's.
        _dep = self.data.get("n_deposition_regional") if hasattr(self, "data") else None
        _dep_ha = 0.0
        if total_uaa > 0 and (_dep is None or region not in getattr(_dep, "index", [])):
            raise RuntimeError(f"no CAPRI deposition for {region} (n_deposition_regional.csv)")
        if _dep is not None and region in getattr(_dep, "index", []):
            _v = float(_dep.at[region, "deposition_kg_n_per_ha"])
            if _v == _v and _v >= 0:
                _dep_ha = _v
        n_deposition = total_uaa * _dep_ha

        n_manure_import = sum(activities.get(a, 0.0) for a in CROPS) * _imp_ha
        # MINERAL FERTILISER FOLLOWS CROP NEED (CAPRI supply_model.gms NUTNED_):
        # mineral N covers what manure, residues and deposition leave of the
        # crops' need, each net of losses. Linearised around the base: crops
        # carry the share of their need that manure covered at base, and the
        # manure actually available displaces mineral N at
        # availability / efficiency (median 0.44 / 0.91 across CAPRI regions).
        # At base the total equals the previous mineral input exactly. When
        # herds shrink mineral N rises; when cropland shrinks it falls by the
        # crop's full need. A region total is clipped at zero; single-animal
        # unit balances are not - their negative term IS the displacement.
        # Fertiliser technologies raise the efficiency of MINERAL N (CAPRI: mineral x (1 + E)
        # covers what need leaves after manure and residues), so they shrink the mineral N
        # net of those credits: need and credits scale with the same factor ("__credit__", the
        # regional technology factor; the crops' own factors carry it on their mineral rate).
        # Scaling only the need side made a technology save mineral N it never displaced -
        # up to 2x the mineral actually applied where manure and residues cover most need.
        if _sub is not None:
            n_mineral += n_need_manure_part - _fc * _sub[0] * (n_organic + n_manure_import)
            if total_uaa > 0:
                n_mineral = max(n_mineral, 0.0)
        # (after the manure clip: a linear term, so one crop's unit balance carries its own
        # displacement, as an animal's carries its manure's)
        # CROP RESIDUES displace mineral N as manure does (CAPRI NUTNED_: residue and deposition N
        # count towards crop need at their availability, 1 - nutNed_cres_unavailable / (CRESID +
        # ATMOSD), ~0.75). Arable residues are pooled and spread over arable crops by need (at
        # base every arable crop carries the pool's credit in proportion to its need, fallow
        # none); grassland and permanent crops keep their own (CAPRI eq. 5.10). A crop mix or
        # yield that leaves more residues lowers the mineral N needed.
        if _cn and _sub is not None:
            _ar, _r0 = self._residue_availability(region)
            if _ar > 0:
                n_mineral += _ar * (_r0 * n_need_w - _fc * (n_residues - _own_res))   # arable pool
                n_mineral += _ar * (_own_need - _fc * _own_res)                       # grass, permanent
        total_inputs = n_mineral + n_organic + n_fixation + n_deposition + n_manure_import + n_residues

        # --- Outputs ---
        # Crop N uptake: CAPRI's per crop and region (_capri_crop_n)
        n_crop_uptake = n_crop_uptake_c
        # N in livestock products
        # N in livestock products: CAPRI's CRPR_EXPT per head (fert/calc_nexport.gms; livestock_n_export_coef.csv,
        # tools/build/build_livestock_n_export_coef.py) x heads. Until 23 October 2026: 25% of excreted N (no source)
        n_animal_output = self._n_animal_products(region, activities)

        # GROSS NITROGEN BALANCE outputs are crop and fodder removals only
        # (OECD/Eurostat; CAPRI's land and soil budgets, Koeble et al. 2026,
        # Table 4). Excretion already excludes the N retained in animal
        # products, so subtracting a share of it double-counted - and made every
        # animal look 25% cleaner in the nitrogen constraint. Reported only.
        total_outputs = n_crop_uptake

        # Balance
        surplus = total_inputs - total_outputs
        nue = total_outputs / max(total_inputs, 1.0)

        return {
            "n_mineral_input": n_mineral,
            "n_mineral_plain": n_mineral_plain,
            "n_organic_input": n_organic,
            "n_fixation": n_fixation,
            "n_crop_residues": n_residues,
            "n_deposition": n_deposition,
            "n_crop_uptake": n_crop_uptake,
            "n_animal_products": n_animal_output,
            "n_surplus": surplus,
            "n_use_efficiency": nue,
            # pools of CAPRI's fertiliser distribution (fertDistExcr_, fertDistCres_; inner model): manure N
            # applied in the region - CAPRI's v_ManureNPK: excreted, less the losses in housing and storage
            # (GASANI, RUNANI), less net exports (EXCRET - MTRADE - GASANI - RUNANI, exact in CAPRI's 2030
            # reference) - the arable residue pool, own residues of the permanent groups
            "n_manure_applied": n_organic + n_manure_import - n_housing_loss,
            "n_manure_import": n_manure_import,
            "n_manure_housing_loss": n_housing_loss,
            "n_residue_pool": (n_residues - _own_res) if _cn else 0.0,
            "n_own_residues": _own_res if _cn else 0.0,
        }

    def fert_distribution(self, region, acts, yields, nb, nb_raw, mineral_cap=None, mode_crops=None,
                          cal_priors=None, yields_scen=None) -> Optional[list]:
        """CAPRI's inner fertiliser distribution model for one region (capri_mod.fert.inner_fert_dist): mineral N
        (the balance's), manure N applied (the balance's own manure plus imports, after endogenous trade and the
        herd adjustments) and the arable residue pool, distributed over CAPRI's crop groups; needs at CAPRI's base
        per ha x area x CAPRI's need factor of the yield (NUTNED_, fert/fertned.gms; need_yield_factor). With the crop-specific mineral fertiliser reduction the
        "f2f" (mineral N) and "limCres" (residues) regulations apply. Rows: region, capri_region, ngrp, area_kha,
        mine/excr/cres kg_ha, mine_cap_kg_ha, cap_scale (> 1 where the accounts' mineral N exceeds the caps'
        capacity and the caps were scaled to report an allocation), converged. mode_crops: the crop areas CAPRI's
        prior modes are fixed at (the supply model's starting point; None: the current areas)."""
        from capri_mod.fert.inner_fert_dist import InnerFertDist
        inner = self.__dict__.get("_inner_fert")
        if inner is None:
            inner = self._inner_fert = InnerFertDist()
        inner.set_variant(bool(getattr(self, "manure_trade_on", True)))
        if cal_priors is not None and cal_priors[0][1] == inner.variant:
            inner._pri_cal[cal_priors[0]] = cal_priors[1]       # the regional model's calibrated priors
        if inner.capri_region(region) is None:
            return None
        if hasattr(acts, "to_dict"):
            acts = acts.to_dict()
        crops = {c: float(acts.get(c, 0.0) or 0.0) for c in CROPS if float(acts.get(c, 0.0) or 0.0) > 0}
        _yb = self._cached_row("yields", region) or {}
        fac = {}
        for c in crops:
            y0 = float(_yb.get(c, 0.0) or 0.0)
            y = float(yields.get(c, y0) or 0.0) if hasattr(yields, "get") else y0
            ys = yields_scen.get(c) if hasattr(yields_scen, "get") else None
            fac[c] = need_yield_factor(region, c, y0, y, None if ys is None else float(ys), "N") \
                if (y0 > 0 and y > 0) else 1.0
        M = float(nb.get("n_mineral_input", 0.0))
        E = float(nb_raw.get("n_manure_applied", 0.0)) + float(nb.get("n_organic_input", 0.0)) \
            - float(nb_raw.get("n_organic_input", 0.0))
        # the N the ammonia options keep in housing, storage and spreading stays in the manure (CAPRI: lower GASANI,
        # higher v_ManureNPK) - set per region by the accounts above
        E += float(getattr(self, "_n_kept_last", getattr(self, "_nh3_saved_last", 0.0)) or 0.0)
        C = float(nb_raw.get("n_residue_pool", 0.0))
        av = float(self._residue_availability(region)[0] or 0.0)
        caps, gcaps = None, {}
        if mineral_cap and mineral_cap.get("group_caps"):
            gcaps = mineral_cap["group_caps"]
            caps = {(g, "MINE"): v for g, v in gcaps.items() if v > 0}
            for g, v in (mineral_cap.get("limcres") or {}).items():
                caps[(g, "CRES")] = v
        out = inner.allocate(region, crops, M, E, C, av, crop_factor=fac, caps=caps, mode_crop_areas=mode_crops)
        cap_scale = 1.0
        if caps and (out is None or not out["converged"]):
            # The supply model holds mineral N at most at the caps' capacity, sum_g cap_g x area_g; the beta
            # densities' support is open (x < cap), so at the capacity itself the regulated mode does not exist,
            # and the accounts' mineral N can exceed the row's by their own adjustments (catch crops, realised
            # yields; ~0.1%). Then the caps are scaled to leave 0.2% room, and the scale is reported.
            ar_ = inner.group_areas(region, crops)
            capa = sum(v * ar_.get(g, 0.0) for (g, s_), v in caps.items() if s_ == "MINE" and not isinstance(v, tuple))
            free = [g for g in ar_ if (g, "MINE") not in caps]
            if capa > 0 and not free:
                cap_scale = max(1.0, M / (0.998 * capa))
                caps2 = {k: (v * cap_scale if (k[1] == "MINE" and not isinstance(v, tuple)) else v) for k, v in caps.items()}
                out = inner.allocate(region, crops, M, E, C, av, crop_factor=fac, caps=caps2, mode_crop_areas=mode_crops)
        if out is None and caps:
            # regulations infeasible at this solution: report the unregulated allocation, flagged
            out = inner.allocate(region, crops, M, E, C, av, crop_factor=fac, mode_crop_areas=mode_crops)
            if out is not None:
                out["converged"] = False
        if out is None:
            return None
        rows = []
        for g, A in out["area"].items():
            ph = {s_: float(out["per_ha"].get((g, s_), 0.0)) for s_ in ("MINE", "EXCR", "CRES")}
            rows.append(dict(region=region, capri_region=out["capri_region"], ngrp=g, area_kha=float(A),
                             mine_kg_ha=ph["MINE"], excr_kg_ha=ph["EXCR"], cres_kg_ha=ph["CRES"],
                             mine_cap_kg_ha=float(gcaps.get(g, float("nan"))) if gcaps else float("nan"),
                             cap_scale=cap_scale, converged=bool(out["converged"])))
        return rows

    def fert_side_factors(self, region, shares, nmin) -> Optional[Dict[str, float]]:
        """Emission factor multipliers on mineral N from CAPRI's nitrification-inhibitor side
        effects (capri_data/2017/abatement/fert_side_effects.csv, tools/build/build_fert_side_effects.py):
        F = 1 - w + w (1 - lit) (1 + NMIN), w = the option's share of mineral N. None when the
        region has no inhibitor adoption."""
        s = float((shares or {}).get("NITR_INH", 0.0) or 0.0)
        if not s > 0:
            return None
        cls = type(self)
        if cls._FERT_SIDE is None:
            tab = _inputs.current().csv("fert_side_effects.csv", "abatement")
            cls._FERT_SIDE = {(r.region, r.technology, r.item): float(r.value) for r in tab.itertuples()}
        tab = cls._FERT_SIDE
        lit = {i: tab.get((region, "NITR_INH", i)) for i in ("N2OSYN", "NH3SYN")}
        if any(v is None for v in lit.values()):
            return None
        nm = float((nmin or {}).get("NITR_INH", 0.0) or 0.0)
        s = min(s, 1.0)
        w = (s / (1.0 + nm)) / (s / (1.0 + nm) + 1.0 - s)
        return {i: 1.0 - w + w * (1.0 - v) * (1.0 + nm) for i, v in lit.items()}

    def _winter_cover_now(self, region, supply_result):
        """(base, current) winter cover share (CAPRI's v_Miti(CATC, WinterCov)): the 2030 catch-crop share and, under
        the catch-crop requirement, the required area over UAAR (supply result's cover_crops)."""
        cc = self.data.get("cover_crops") if hasattr(self, "data") else None
        w0 = 0.0
        if cc is not None and region in getattr(cc, "index", []):
            v = cc.at[region, "catc_share_2030"]
            w0 = float(v) if v == v else 0.0
        cv = getattr(supply_result, "cover_crops", None) or {}
        w1 = float(cv["req"]) / float(cv["uaa"]) if cv.get("req") is not None and float(cv.get("uaa", 0.0) or 0.0) > 0 else w0
        return w0, w1

    def _leach_animals(self, region, acts, ms, wc, initial=False, fert_mrun=0.0):
        """Per animal (t N excreted, RunSurf, GasRunTot, sum over the application options of no3mlea x share) through
        CAPRI's cascade at the current option shares ms (or the initial shares), the sub-activities weighted by their
        manure N; animals without cascade data are left out."""
        from capri_mod.supply import ammonia_techs as _at, n_cascade as _nc
        from capri_mod.supply.n_leaching import APPL
        out = []
        tm = (getattr(self, "_amm_tm", None) or {}).get(region, {})
        for a_ in ANIMALS:
            x_ = float(acts.get(a_, 0.0) or 0.0)
            subs = tm.get(a_) or []
            if x_ <= 0 or not subs or any(_at.cascade_data(sb) is None for sb in subs):
                continue
            n_a = self._n_excretion(region, a_) * x_ * 1000.0 / 1e3          # kg/head x 1000 heads -> t N
            sh = {t: v for (aa, t), v in (ms or {}).items() if aa == a_}
            W = RS = GR = AG = 0.0
            for sb in subs:
                w = float(sb["w"]) * float(sb.get("mrel", 1.0) or 1.0)
                s_ = {t["tech"]: t["ini"] for t in sb["techs"]}
                if not initial:
                    s_ = {t_: sh.get(t_, v_) for t_, v_ in s_.items()}
                f, rsurf, eff = _at.cascade_data(sb)
                m = 1.0 - _nc.WINTERCOV_NO3 * wc - fert_mrun
                L = _nc.losses(f, rsurf, s_, eff, m_runsurf=(m, 1.0), m_appl_run=1.0 - _nc.WINTERCOV_NO3 * wc)
                W += w
                RS += w * L[("N", "RunSurf")]
                GR += w * L[("N", "GasRunTot")]
                AG += w * sum(float(eff.get((t_, "no3mlea"), 0.0)) * float(s_.get(t_, 0.0)) for t_ in APPL)
            if W > 0:
                out.append((n_a, RS / W, GR / W, AG / W))
        return out

    def _mineral_n2o_n(self, region):
        """(direct, indirect) N2O-N per unit of mineral N: CAPRI's from the region's MITERRA fractions
        (n_cascade.mineral_n2o_n), else IPCC's EF1 and 10% x EF4."""
        c_ = self.__dict__.setdefault("_min_n2o_cache", {})
        if region not in c_:
            from capri_mod.supply import n_cascade as _nc, n_leaching as _nl
            rs = _nl.capri_region(region)
            dn = _nc.mineral_n2o_n(_nc.load()[1].get(rs, {}), EF_SOIL_N2O_INDIRECT) if rs else None
            c_[region] = dn if dn else (EF_SOIL_N2O_DIRECT, 0.10 * EF_SOIL_N2O_INDIRECT)
        return c_[region]

    def leaching(self, region, acts, nb, supply_result=None):
        """CAPRI's leaching share of the soil surplus (LEACHN_) and the N leached and run off from the fields that
        carries indirect N2O (gases.gms N2OLEA allocated to crops), capri_mod/supply/n_leaching.py. Returns {share,
        components (t N), n2o_n (t N2O-N), leached (t N below the root zone)} or None without CAPRI's data."""
        from capri_mod.supply import n_cascade as _nc, n_leaching as _nl
        from capri_mod.supply.supply_module import fert_side_value as _fsv
        rs = _nl.capri_region(region)
        d = _nl.load().get(rs) if rs else None
        if not d or d.get("exp_imp") is None:
            return None
        e = float(d["exp_imp"])
        _, G, _ = _nc.load()
        g = G.get(rs, {})
        wc0, wc1 = self._winter_cover_now(region, supply_result)
        fs = getattr(supply_result, "fert_tech_shares", None) or {}
        nmin = getattr(supply_result, "fert_nmin", None) or {}
        s_ni, s_nim = float(fs.get("NITR_INH", 0.0) or 0.0), float(fs.get("NITR_INH_MAN", 0.0) or 0.0)

        def _eff(tech, item, nm):
            v = _fsv(region, tech, item)
            return 0.0 if v is None else _nl.fert_effect(v, nm)
        e_slea = _eff("NITR_INH", "NO3SLEA", nmin.get("NITR_INH", 0.0))
        e_srun = _eff("NITR_INH", "NO3SRUN", nmin.get("NITR_INH", 0.0))
        e_mlea = _eff("NITR_INH_MAN", "NO3MLEA", nmin.get("NITR_INH_MAN", 0.0))
        e_mrun = _eff("NITR_INH_MAN", "NO3MRUN", nmin.get("NITR_INH_MAN", 0.0))
        # mineral N: CAPRI's NETF losses (GASTOTNETF_, RUNTOTNETF_ with winter cover and the inhibitor's NO3SRUN)
        M = float(nb.get("n_mineral_input", 0.0) or 0.0)
        nf = _nc.netf(g, float(g.get("run_surf", 0.0)), m_run=1.0 - _nc.WINTERCOV_NO3 * wc1 - s_ni * e_srun)
        ms = getattr(supply_result, "manure_tech_shares", None) or {}
        an1 = self._leach_animals(region, acts, ms, wc1, fert_mrun=s_nim * e_mrun)
        an0 = self._leach_animals(region, acts, ms, wc0, initial=True)
        man_net = float(nb.get("n_manure_applied", 0.0) or 0.0)
        oth = (float(nb.get("n_crop_residues", 0.0) or 0.0) + float(nb.get("n_deposition", 0.0) or 0.0)) \
            * (1.0 - nf["N2O"])
        den = M * (1.0 - nf["GasRunTot"]) + man_net + oth
        nmin_sh = M * (1.0 - nf["GasRunTot"]) / den if den > 0 else 0.0
        nman_sh = man_net / den if den > 0 else 0.0

        def _agg(an):
            w = sum(n * (1.0 - gr) for n, _, gr, _ in an)
            return sum(n * (1.0 - gr) * ag for n, _, gr, ag in an) / w if w > 0 else 0.0
        b_now = _nl.b1(wc1, _agg(an1), nmin_sh, nman_sh, s_ni * e_slea, s_nim * e_mlea)
        b_ini = _nl.b1(wc0, _agg(an0))
        L = _nl.share(rs, b_now, b_ini)
        if L is None:
            return None
        comp = _nl.crop_n(M, nf["RunTot"], nf["GasRunTot"], nf["N2O"], [(n, r_, gr) for n, r_, gr, _ in an1],
                          -float(nb.get("n_manure_import", 0.0) or 0.0),
                          float(nb.get("n_crop_residues", 0.0) or 0.0) + float(nb.get("n_deposition", 0.0) or 0.0),
                          float(nb.get("n_fixation", 0.0) or 0.0), L, e)
        tot = sum(comp.values())
        return {"share": L, "b1": b_now, "b1_ini": b_ini, "components": comp, "n_runoff_leached": tot,
                "n2o_n": tot * _nl.EF5}
