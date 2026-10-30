"""Animals in the regional model: the young-animal coefficients, columns and markets' response, the intensity and member splits of cattle, dairy and grassland (CAPRI's split activities), genetics, the fodder rows, the cake index and protein feed cost, the animals' cost per head.

RegionalSupplyModel's methods, moved unchanged from capri_mod/supply/supply_module.py (refactor stage 3a,
docs/design/ARCHITECTURE_REFACTOR.md); the module-level names they use are supply_module's, given to
this module once supply_module is loaded (capri_mod.supply.blocks.inject); the annotations are not evaluated
(they name supply_module's types).
"""
from __future__ import annotations


class LivestockBlock:
    def _young_animal_coefs(self) -> dict:
        """{good: {"produce": {act: per head}, "use": {act: per head}, "value_eur_head": v}} for this
        region (capri_data/2017/supply/young_animals_2017.json, tools/build/build_young_animals.py)."""
        rec = young_animal_table().get(self.data.region_id, {})
        fac = getattr(self.data, "young_value_factor", None) or {}
        if not fac:
            return rec
        return {g: {**r, "value_eur_head": float(r.get("value_eur_head", 0.0) or 0.0) * float(fac.get(g, 1.0))}
                for g, r in rec.items()}

    def young_animal_columns(self, cols, goods=None):
        """(goods, n, v): the net young-animal production per unit of each column of the regional QP (n, columns x
        goods: produce - use of the activities; for the cattle splits' columns z, (produce x dprod, with the member
        splits) - use x duse (dyoung for the pooled goods)), and the value per head v (EUR, with the market year's value
        factor) - exactly as the young-animal prices enter the objective (_apply_young_animal_prices, _cattle_columns)
        and the balances (CAPRIModel._young_animal_balance)."""
        coefs = self._young_animal_coefs()
        goods = sorted(coefs) if goods is None else list(goods)
        ct = getattr(self.data, "cattle_intensity", None) or {}
        ms = bool(getattr(type(self), "use_cattle_member_splits", False))
        n = np.zeros((len(cols), len(goods))); v = np.zeros(len(goods))
        idx = {c_: j for j, c_ in enumerate(cols)}
        for gi, g in enumerate(goods):
            rec = coefs.get(g) or {}
            v[gi] = float(rec.get("value_eur_head", 0.0) or 0.0)
            pr, us = rec.get("produce", {}) or {}, rec.get("use", {}) or {}
            for a in set(pr) | set(us):
                if a in idx:
                    n[idx[a], gi] += float(pr.get(a, 0.0) or 0.0) - float(us.get(a, 0.0) or 0.0)
            for j, lab in enumerate(cols):
                if not str(lab).startswith("cattle_z_"):
                    continue
                key = str(lab)[len("cattle_z_"):]
                di = ct.get(key)
                if di is None:
                    continue
                a_ = key.split(":")[0]
                cu = float(us.get(a_, 0.0) or 0.0)
                if cu:
                    du = di.get(f"duse_{g}_rel") if ms else None
                    du = float(di["dyoung_rel"]) if du is None or du != du else float(du)
                    n[j, gi] -= cu * du
                cp = float(pr.get(a_, 0.0) or 0.0) if ms else 0.0
                dp = di.get(f"dprod_{g}_rel")
                if cp and dp is not None and dp == dp:
                    n[j, gi] += cp * float(dp)
        return goods, n, v

    def _yani_response(self, nlp, res, cols):
        """{"goods", "dnet"}: dnet[g', g] = the change of the region's net young-animal balance of g' (1000 head) per
        unit change of the price ratio of g, from the solved NLP's sensitivity (CapriRegionalNLP.response) - the
        Jacobian of the young-animal markets' price update, constraints included."""
        goods, n, v = self.young_animal_columns(cols[:nlp.n0])
        if not len(goods) or not np.any(n):
            return None
        dy = nlp.response(res, -n * v[None, :])
        return {"goods": goods, "dnet": n.T @ dy}

    def _apply_young_animal_prices(self):
        ratio = getattr(self, "yani_price_ratio", None) or {}
        if not ratio:
            return
        for g, rec in self._young_animal_coefs().items():
            r_ = float(ratio.get(g, 1.0))
            if r_ == 1.0:
                continue
            v = float(rec.get("value_eur_head", 0.0) or 0.0)
            for a in set(rec.get("produce", {})) | set(rec.get("use", {})):
                if a in self.net_revenues.index:
                    n = float(rec.get("produce", {}).get(a, 0.0)) - float(rec.get("use", {}).get(a, 0.0))
                    self.net_revenues[a] = float(self.net_revenues[a]) + (r_ - 1.0) * v * n

    def _split_manure_factors(self, n_cols, acts):
        """[(column, animal, manure per head of the column / the animal's)] of the animal split and option columns:
        the dairy intensity split (dairy_intensity dmann_rel), the cattle splits (cattle_intensity[key] dmann_rel) and
        the genetics options (genetics_effects[(animal, option)] d_mann_rel)."""
        out = []
        j = getattr(self, "_dairy_col", None)
        di = getattr(self.data, "dairy_intensity", None)
        if j is not None and int(j) < n_cols and di is not None and "DCOW" in acts:
            out.append((int(j), "DCOW", float(di["dmann_rel"])))
        tab = getattr(self.data, "cattle_intensity", None) or {}
        for key, j in (getattr(self, "_cattle_cols", None) or {}).items():
            a = key.split(":")[0]
            if int(j) < n_cols and a in acts and key in tab:
                out.append((int(j), a, float(tab[key]["dmann_rel"])))
        gen = getattr(self.data, "genetics_effects", None) or {}
        for (a, opt), j in (getattr(self, "_genet_cols", None) or {}).items():
            if int(j) < n_cols and a in acts and (a, opt) in gen:
                out.append((int(j), a, float(gen[(a, opt)]["d_mann_rel"])))
        return out

    @classmethod
    def _cake_index(cls):
        """(weights, base prices) of the protein-feed cake index: the EU's base-period feed use of each cake (CAPRI's
        FAO_agg FEDM, eu_cake_feed_bas.csv, tools/build/build_eu_cake_feed.py) and its world price."""
        def load(inp):
            fe_ = inp.csv("eu_cake_feed_bas.csv", "market").set_index("product")["feed_kt"]
            wp = inp.csv("world_prices.csv", "market").set_index("commodity")["price"]
            w, p = {}, {}
            for c in ("SOYC", "RAPC", "SUNC"):
                fe = float(fe_.get(c, 0.0))
                if fe > 0 and c in wp.index:
                    w[c], p[c] = fe, float(wp[c])
            return (w, p)
        return _inputs.current().cached("cake_index", load)

    def _protein_feed_cost_change(self, q, price_shock) -> float:
        """Cost change of q tonnes of protein-rich feed under the cake prices."""
        w, p = self._cake_index()
        ws = sum(w.values())
        if q <= 0 or ws <= 0:
            return 0.0
        return q * sum((w[c] / ws) * p[c] * float(price_shock.get(c, 0.0)) for c in w)

    def _animal_cost_per_head(self, act: str) -> float:
        """The model's input cost per head of an animal activity, as _compute_net_revenues uses it: CAPRI's
        LEVL x TOIN per model head (livestock_cost_coef) where that is on, else the per-head TOIN."""
        _cc = getattr(self.data, "livestock_cost_coef", None)
        if _cc is not None and act in _cc.index \
                and pd.notna(_cc[act]) and float(_cc[act]) > 0:
            return float(_cc[act])
        v = float(self.data.variable_costs.get(act, 0.0))
        return v if np.isfinite(v) else 0.0          # an activity the region does not have (level fixed at 0)

    def _grass_intensity_column(self, Qa, ca, Aa, ba, start, labels, n, alloc_k):
        """Append CAPRI's grassland-intensity choice as one column z (1000 ha moved from GRAI to
        GRAE; GRAE = s0 x GRAS + z, GRAI = (1 - s0) x GRAS - z, so z = 0 is the base split):
          - N balance row: the balance change of a hectare of GRAE over one of GRAI
            (EnvironmentalModule.grass_intensity_delta, the accounts' own function);
          - grass fodder rows: production changes by u x (yield_ext - yield_int) / mean yield;
          - crop-need limit (manure within need): the change in the unit balance's mineral N (K19) and in CAPRI's
            minimum mineral share x need (K9);
          - 0 <= GRAE, GRAI: -z - s0 GRAS <= 0, z - (1 - s0) GRAS <= 0;
          - PMP: (q_ext + q_int) z^2 / 2 (CAPRI's p_pmpQuadTechn of GRAE and GRAI), linear term
            from the base duals of the rows z enters, so z = 0 is optimal at base (as CAPRI's
            PMP calibration makes the base split optimal)."""
        self._grass_col = None
        if "GRAS" not in self.acts or alloc_k:
            return Qa, ca, Aa, ba, start
        gi = getattr(self.data, "grass_intensity", None)
        env_ = getattr(self, "_env_for_surplus", None)
        if gi is None or env_ is None or not hasattr(gi, "get") or not (gi.get("q_ext", 0) > 0):
            return Qa, ca, Aa, ba, start
        dl = env_.grass_intensity_delta(self.data.region_id)
        if not dl:
            return Qa, ca, Aa, ba, start
        jg = list(self.acts).index("GRAS")
        s0 = float(gi["share_ext"]); dy = float(gi["yield_ext_rel"]) - float(gi["yield_int_rel"])
        col = np.zeros(Aa.shape[0])
        if "N_balance" in labels:
            col[labels.index("N_balance")] = float(dl.get("n_surplus", 0.0))
        for i, lab in enumerate(labels):
            if lab.startswith("fodder_") and i < Aa.shape[0] and Aa[i, jg] != 0.0:
                # GRAS's own coefficient is -u (row) or +u (band); production change u x dy per ha
                col[i] = Aa[i, jg] * dy
        nr = getattr(self, "_need_row", None)
        if nr is not None and nr < Aa.shape[0]:
            # the change in the unit balance's mineral N, the quantity every crop carries on this row and the accounts
            # apply (K19: it was the plain fertiliser rate, -3.65 against -39.9 t per 1000 ha in AT32; the model then
            # saw mineral N at its floor while the accounts went to -461 t); and CAPRI's NUTMIN_ floor moves with the
            # need of a hectare of GRAE over one of GRAI (K9)
            col[nr] = -float(dl.get("n_mineral_input", dl.get("mineral_rate", 0.0)))
        # LINEAR TERM: calibrated so that z = 0 is optimal in the base problem (CAPRI's PMP
        # calibration makes the base split of GRAE and GRAI optimal): c_z = - sum_i mu_i A_iz with
        # mu the duals of the rows z enters, from the region's first (baseline) solve, which is
        # made WITHOUT the column. Later solves carry the column with the stored term.
        cz = getattr(self, "_grass_cz", None)
        if cz is None:
            self._grass_pending_col = col
            self._grass_col = None
            return Qa, ca, Aa, ba, start
        self._grass_pending_col = None
        Aa = np.hstack([Aa, col[:, None]])
        lo = np.zeros(Aa.shape[1]); lo[-1] = -1.0; lo[jg] = -s0
        hi = np.zeros(Aa.shape[1]); hi[-1] = 1.0; hi[jg] = -(1.0 - s0)
        Aa = np.vstack([Aa, lo, hi]); ba = np.concatenate([ba, [1e-9, 1e-9]])
        labels.extend(["grass_z_lo", "grass_z_hi"])
        qz = float(gi["q_ext"]) + float(gi["q_int"])
        Qa = np.pad(Qa, ((0, 1), (0, 1))); Qa[-1, -1] = qz
        ca = np.concatenate([ca, [cz + self._ghg_cost('grass')]])
        start = np.concatenate([start, [0.0]])
        self._grass_col = Aa.shape[1] - 1
        return Qa, ca, Aa, ba, start

    def _dairy_intensity_column(self, Qa, ca, Aa, ba, start, labels, n):
        """CAPRI's two-intensity cattle activities: dairy cows (DCOL/DCOH, Sprint 7b), then fattening
        bulls (BULL/BULH) and heifers (HEIL/HEIH) (Sprint 7c)."""
        Qa, ca, Aa, ba, start = self._dairy_column_only(Qa, ca, Aa, ba, start, labels, n)
        Qa, ca, Aa, ba, start = self._cattle_columns(Qa, ca, Aa, ba, start, labels, n)
        return self._genetics_columns(Qa, ca, Aa, ba, start, labels, n)

    def _split_pending(self) -> bool:
        return (getattr(self, "_dairy_pending", None) is not None or bool(getattr(self, "_cattle_pending", None))
                or bool(getattr(self, "_genet_pending", None)))

    def _split_record(self, y) -> None:
        """z of the dairy, bull and heifer splits from a solution vector."""
        _dc = getattr(self, "_dairy_col", None)
        self._last_dairy_z = float(y[_dc]) if _dc is not None and _dc < len(y) else 0.0
        self._last_cattle_z = {a: float(y[c]) for a, c in (getattr(self, "_cattle_cols", None) or {}).items() if c < len(y)}
        self._last_genet_z = {k: max(0.0, float(y[c])) for k, c in (getattr(self, "_genet_cols", None) or {}).items() if c < len(y)}

    def _cattle_columns(self, Qa, ca, Aa, ba, start, labels, n):
        """One column z per split of a cattle animal into CAPRI's activities (1000 stalls moved from one CAPRI
        activity to another, CATTLE_SPLIT_MEMBERS): the intensity pairs (BULL: BULL/BULH; HFRS: HEIL/HEIH, Sprint 7c),
        the replacement heifers (HFRS:rep, HEIR against HEIH) and the calves (CALV:male CAMF against CAMR, CALV:female
        CAFF against CAFR). As the dairy split: manure-driven rows x (MANN per stall, a - b) / average; the feed
        block's requirement rows (feeding inside); bounds a = s_a X + z >= 0 and b = s_b X - (sum of the z taking from
        b) >= 0; PMP from CAPRI's own terms (q_z; splits taking from the same activity share its term q_b as their
        cross term); linear term from the base duals, plus the CHANGES under the scenario: beef revenue (beef per
        stall, a - b), the young animals bought (calves, young cattle) and sold (young cattle from raising calves,
        replacement cows from HEIR) at the young-animal price changes."""
        self._cattle_cols = {}
        tab = getattr(self.data, "cattle_intensity", None)
        if not tab:
            return Qa, ca, Aa, ba, start
        cz_all = getattr(self, "_cattle_cz", None) or {}
        pending = {}
        rows_ = [labels.index(l) for l in ("N_balance",) if l in labels]
        for extra in ("_need_row", "_alloc_row"):
            k = getattr(self, extra, None)
            if k is not None and k < Aa.shape[0] and k not in rows_ and (extra != "_alloc_row" or getattr(self, "_alloc_cols", 0)):
                rows_.append(k)
        ps = getattr(self, "_price_shock_now", None)
        pv = getattr(self.data, "livestock_product_value_by_market_coef", None)
        yr = getattr(self, "yani_price_ratio", None) or {}
        ycoef = self._young_animal_coefs() if yr else {}
        members = type(self).CATTLE_SPLIT_MEMBERS
        member_splits = getattr(type(self), "use_cattle_member_splits", True)
        placed = {}                                               # animal -> [(key, column, row, animal column)]
        for key, di in tab.items():
            a = key.split(":")[0]
            if a not in self.acts or key not in members or (":" in key and not member_splits):
                continue
            r = (getattr(self, "feed_rations", None) or {}).get(a)
            if r is None or not (float(di.get("q_z", 0) or 0) > 0):
                continue
            j = list(self.acts).index(a)
            col = np.zeros(Aa.shape[0])
            for i in rows_:
                col[i] = float(Aa[i, j]) * float(di["dmann_rel"])
            req = {"E": float(r.E) * float(di["denne_rel"]), "P": float(r.P) * float(di["dcrpr_rel"]),
                   "DMIN": float(r.DMIN) * float(di["ddrmn_rel"])}
            if np.isfinite(float(r.DMAX)):
                req["DMAX"] = float(r.DMAX) * float(di["ddrmx_rel"])
            if key not in cz_all:
                pending[key] = (col, req)
                continue
            Aa = np.hstack([Aa, col[:, None]])
            if not member_splits:
                # the intensity pair alone (Sprint 7c), rows in the order of the validated runs r86 / r87: bounds
                # low = s_low X + z >= 0, high = s_high X - z >= 0 right after the column, term q_z
                lo = np.zeros(Aa.shape[1]); lo[-1] = -1.0; lo[j] = -float(di["share_low"])
                hi = np.zeros(Aa.shape[1]); hi[-1] = 1.0; hi[j] = -float(di["share_high"])
                Aa = np.vstack([Aa, lo, hi]); ba = np.concatenate([ba, [1e-9, 1e-9]])
                labels.extend([f"cattle_z_{a}_lo", f"cattle_z_{a}_hi"])
                Qa = np.pad(Qa, ((0, 1), (0, 1))); Qa[-1, -1] = float(di["q_z"])
            else:
                Qa = np.pad(Qa, ((0, 1), (0, 1)))                # the split block is set below, per animal
                placed.setdefault(a, []).append((key, Aa.shape[1] - 1, di, j))
            dv = 0.0
            if ps is not None and pv is not None and hasattr(pv, "get"):
                bv = pv.get(f"{a}.BEEF")
                if bv is not None and pd.notna(bv):
                    dv += float(di["dbeef_rel"]) * float(bv) * float(ps.get("BEEF", ps.get(a, 0.0)) or 0.0)
            for g, rec in ycoef.items():                          # young animals bought and sold per stall
                chg = float(rec.get("value_eur_head", 0.0) or 0.0) * (float(yr.get(g, 1.0)) - 1.0)
                if not chg:
                    continue
                u = float(rec.get("use", {}).get(a, 0.0) or 0.0)
                if u:
                    du = di.get(f"duse_{g}_rel")
                    du = float(di["dyoung_rel"]) if du is None or du != du else float(du)
                    # (the product in the order of the validated runs r86 / r87)
                    dv -= du * u * float(rec.get("value_eur_head", 0.0) or 0.0) * (float(yr.get(g, 1.0)) - 1.0)
                p_ = float(rec.get("produce", {}).get(a, 0.0) or 0.0) if member_splits else 0.0
                dp = di.get(f"dprod_{g}_rel")
                if p_ and dp is not None and dp == dp and float(dp):
                    dv += float(dp) * p_ * chg
            ca = np.concatenate([ca, [cz_all[key] - dv + self._ghg_cost('cattle', key)]])
            start = np.concatenate([start, [0.0]])
            self._cattle_cols[key] = Aa.shape[1] - 1
            rx = dict(getattr(self, "_dairy_req_extra", None) or {})
            rx[a] = list(rx.get(a, [])) + [(Aa.shape[1] - 1, req)]
            self._dairy_req_extra = rx
        # per animal: CAPRI's activities x_m = s_m X + sum_k E_mk z_k (E_mk = +1 if split k moves stalls into m,
        # -1 out of m); bounds x_m >= 0, one row per activity; PMP block in z: E' diag(q_m) E (q_m: the activity's term
        # per model stall, q_b for the activity giving up stalls, q_z - q_b for the one gaining them)
        for a, lst in placed.items():
            qm, sm = {}, {}
            for key, c_, di, j in lst:
                ma, mb = members[key]
                qb = float(di.get("q_b", 0.0) or 0.0)
                qm.setdefault(mb, qb); qm.setdefault(ma, max(float(di["q_z"]) - qb, 0.0))
                sm.setdefault(ma, float(di["share_low"])); sm.setdefault(mb, float(di["share_high"]))
            for m in sorted(sm):
                row = np.zeros(Aa.shape[1]); row[lst[0][3]] = -sm[m]
                for key, c_, di, j in lst:
                    ma, mb = members[key]
                    row[c_] -= 1.0 if m == ma else (-1.0 if m == mb else 0.0)
                Aa = np.vstack([Aa, row]); ba = np.concatenate([ba, [1e-9]])
                labels.append(f"cattle_{a}_{m}_lo")
            for key1, c1, d1, _ in lst:
                for key2, c2, d2, _ in lst:
                    v_ = 0.0
                    for m, q_ in qm.items():
                        e1 = 1.0 if m == members[key1][0] else (-1.0 if m == members[key1][1] else 0.0)
                        e2 = 1.0 if m == members[key2][0] else (-1.0 if m == members[key2][1] else 0.0)
                        v_ += e1 * e2 * q_
                    Qa[c1, c2] = v_
        self._cattle_pending = pending or None
        return Qa, ca, Aa, ba, start

    @classmethod
    def cattle_split_hessian(cls, tab, keys):
        """The PMP block of the cattle splits keys (the columns of _cattle_columns): E' diag(q_m) E per animal, zero
        between animals; for the young-animal markets' anticipation of the splits' response (CAPRIModel)."""
        members = cls.CATTLE_SPLIT_MEMBERS
        keys = [k for k in keys if k in members and k in (tab or {})]
        H = np.zeros((len(keys), len(keys)))
        qm = {}
        for k in keys:
            a, (ma, mb) = k.split(":")[0], members[k]
            qb = float(tab[k].get("q_b", 0.0) or 0.0)
            qm.setdefault((a, mb), qb); qm.setdefault((a, ma), max(float(tab[k]["q_z"]) - qb, 0.0))
        for i, k1 in enumerate(keys):
            for j, k2 in enumerate(keys):
                a1, a2 = k1.split(":")[0], k2.split(":")[0]
                if a1 != a2:
                    continue
                v = 0.0
                for (a, m), q in qm.items():
                    if a != a1:
                        continue
                    e1 = 1.0 if m == members[k1][0] else (-1.0 if m == members[k1][1] else 0.0)
                    e2 = 1.0 if m == members[k2][0] else (-1.0 if m == members[k2][1] else 0.0)
                    v += e1 * e2 * q
                H[i, j] = v
        return keys, H

    def _cattle_calibrate_from_duals(self, duals):
        pend = getattr(self, "_cattle_pending", None)
        if not pend:
            return
        rd = getattr(self, "_last_req_duals", None) or {}
        cz = dict(getattr(self, "_cattle_cz", None) or {})
        if duals is not None and rd:
            sgn = {"DMAX": -1.0}
            for key, (col, req) in pend.items():
                a = key.split(":")[0]
                if len(duals) >= len(col):
                    cz[key] = -(float(np.asarray(duals[:len(col)], float) @ col)
                                + sum(float(rd.get((a, lab), 0.0)) * sgn.get(lab, 1.0) * v for lab, v in req.items()))
        self._cattle_cz = cz
        self._cattle_pending = None

    def _genetics_columns(self, Qa, ca, Aa, ba, start, labels, n):
        """One column g per region, animal and option (1000 heads adopting), CAPRI's breeding options and its
        low-nitrogen feeding (lowNFeed, Sprint 9g):
          - manure-driven rows (N balance, manure application, crop-need limit, mineral-N allocation):
            the animal's own coefficient x d_mann_rel;
          - the animal's requirement rows in the feed block: requirement x d_ener / d_crpr / d_drmn / d_drmx
            (feeding inside only);
          - 0 <= g <= eligible share x the animal's level (CAPRI MaxShare 1, IniShare 0);
          - cost (CAPRI GHG_Mit_Cost_ with breeding.gms's / low_n_feed.gms's calibration): linear term from the
            base duals plus relSubs0 x costParLin, so the option is not adopted at base (CAPRI: s = 0 optimal with a
            subsidy of relSubs0 x cost); quadratic gamma = max(floor c, c (relSubs1 - relSubs0) - (costsaving0 -
            costsaving1)) per unit of the share (floor 0.2 breeding, 0.05 low-N feed, 0.1 supplements), i.e.
            gamma / eligible heads at base per head adopting; the cost-saving drop is CAPRI's, from its ini and max
            calibration runs (column dsav);
          - milk revenue of the extra milk under the current milk price change (genet_yld)."""
        self._genet_cols = {}
        tab = getattr(self.data, "genetics_effects", None)
        if not tab:
            return Qa, ca, Aa, ba, start
        cal = getattr(self, "_genet_cz", None) or {}
        pend = {}
        rows_ = [labels.index(l) for l in ("N_balance",) if l in labels]
        for extra in ("_need_row", "_alloc_row"):
            k = getattr(self, extra, None)
            if k is not None and k < Aa.shape[0] and k not in rows_ and (extra != "_alloc_row" or getattr(self, "_alloc_cols", 0)):
                rows_.append(k)
        ps = getattr(self, "_price_shock_now", None)
        pv = getattr(self.data, "livestock_product_value_by_market_coef", None)
        base = self._base_levels()
        # the options' rows as plain dicts, once per table (Series lookups here were a visible share of each solve)
        _gm = self.__dict__.get("_genet_rows_memo")
        if _gm is None or _gm[0] is not tab:
            _gm = (tab, {k: (v.to_dict() if hasattr(v, "to_dict") else dict(v)) for k, v in tab.items()})
            self._genet_rows_memo = _gm
        for (a, opt), e in _gm[1].items():
            if a not in self.acts:
                continue
            r = (getattr(self, "feed_rations", None) or {}).get(a)
            L0 = float(base.get(a, 0.0) or 0.0)
            c = float(e.get("cost_eur_head", 0.0) or 0.0)
            if r is None or L0 <= 1e-6 or c <= 0 or not (float(e.get("elig_share", 0.0) or 0.0) > 0):
                continue
            j = list(self.acts).index(a)
            col = np.zeros(Aa.shape[0])
            for i in rows_:
                col[i] = float(Aa[i, j]) * float(e["d_mann_rel"])
            req = {"E": float(r.E) * float(e["d_ener_rel"]), "P": float(r.P) * float(e["d_crpr_rel"])}
            if float(e.get("d_drmn_rel", 0.0) or 0.0):
                req["DMIN"] = float(r.DMIN) * float(e["d_drmn_rel"])
            if float(e.get("d_drmx_rel", 0.0) or 0.0) and np.isfinite(float(r.DMAX)):
                req["DMAX"] = float(r.DMAX) * float(e["d_drmx_rel"])
            if (a, opt) not in cal:
                pend[(a, opt)] = (col, req)
                continue
            r0, r1 = float(e["relsubs0"]), float(e["relsubs1"])
            # pmpParsqr = max(floor x c, c (relSubs1 - relSubs0) - (costsaving0 - costsaving1)) per unit of the share
            # of the eligible heads (breeding.gms l. 447-458, floor 0.2; low_n_feed.gms 0.05; line_nitr.gms 0.1);
            # per head adopting: / (eligible heads at base). costsaving0 - costsaving1: the drop of the option's
            # marginal value between CAPRI's ini and max calibration runs (dsav, EUR per model head;
            # tools/lib/_capri_costsavings.py), taken out of the planned slope as CAPRI does (K67 F2)
            gf = float(e["gamma_floor"]) if ("gamma_floor" in e and pd.notna(e["gamma_floor"])) else 0.2
            ds_ = float(e.get("dsav", 0.0) or 0.0)
            gamma = max(gf * c, c * (r1 - r0) - (ds_ if np.isfinite(ds_) else 0.0))
            el_ = max(float(e["elig_share"]), 1e-6)
            Aa = np.hstack([Aa, col[:, None]])
            lo = np.zeros(Aa.shape[1]); lo[-1] = -1.0
            hi = np.zeros(Aa.shape[1]); hi[-1] = 1.0; hi[j] = -float(e["elig_share"])
            Aa = np.vstack([Aa, lo, hi]); ba = np.concatenate([ba, [1e-9, 1e-9]])
            labels.extend([f"genet_z_{a}_{opt}_lo", f"genet_z_{a}_{opt}_hi"])
            Qa = np.pad(Qa, ((0, 1), (0, 1))); Qa[-1, -1] = gamma / (L0 * el_)
            dv = 0.0
            dmr = float(e.get("d_milk_rel", 0.0) or 0.0)
            if dmr and ps is not None and pv is not None and hasattr(pv, "get"):
                mv = pv.get(f"{a}.MILK")
                if mv is not None and pd.notna(mv):
                    dv = dmr * float(mv) * float(ps.get("MILK", ps.get(a, 0.0)) or 0.0)
            ca = np.concatenate([ca, [cal[(a, opt)] + r0 * c - dv + self._ghg_cost('genet', (a, opt))]])
            start = np.concatenate([start, [0.0]])
            self._genet_cols[(a, opt)] = Aa.shape[1] - 1
            rx = dict(getattr(self, "_dairy_req_extra", None) or {})
            rx[a] = list(rx.get(a, [])) + [(Aa.shape[1] - 1, req)]
            self._dairy_req_extra = rx
        self._genet_pending = pend or None
        return Qa, ca, Aa, ba, start

    def _genetics_calibrate_from_duals(self, duals):
        """c_g = - (sum_i mu_i A_ig + the animal's requirement duals x the requirement changes) at base."""
        pend = getattr(self, "_genet_pending", None)
        if not pend:
            return
        rd = getattr(self, "_last_req_duals", None) or {}
        cz = dict(getattr(self, "_genet_cz", None) or {})
        if duals is not None and rd:
            sgn = {"DMAX": -1.0}
            for (a, opt), (col, req) in pend.items():
                if len(duals) >= len(col):
                    cz[(a, opt)] = -(float(np.asarray(duals[:len(col)], float) @ col)
                                     + sum(float(rd.get((a, lab), 0.0)) * sgn.get(lab, 1.0) * v for lab, v in req.items()))
        self._genet_cz = cz
        self._genet_pending = None

    def _dairy_column_only(self, Qa, ca, Aa, ba, start, labels, n):
        """Append CAPRI's dairy split as one column z (1000 heads moved from DCOH to DCOL; DCOL =
        s0 x DCOW + z, DCOH = (1 - s0) x DCOW - z, so z = 0 is the base split), Sprint 7b:
          - rows driven by manure N (N balance, manure application, crop-need limit, mineral-N
            allocation): DCOW's own coefficient x (MANN_DCOL - MANN_DCOH) / MANN_DCOW;
          - the cows' requirement rows in the feed block (energy, protein, dry-matter
            limits): DCOW's requirement x the relative change (req_extra; feeding inside only);
          - 0 <= DCOL, DCOH; PMP (q_DCOL + q_DCOH) z^2 / 2 (CAPRI's p_pmpQuadTechn);
          - linear term from the base duals (z = 0 optimal at base), plus the milk revenue change
            under the current milk price (milk per head (COMI_DCOL - COMI_DCOH) / COMI_DCOW).
        Calves, cull-cow beef and replacements are the same for both activities (CAPRI res_17)."""
        self._dairy_col = None
        self._dairy_req_extra = None
        if "DCOW" not in self.acts:
            return Qa, ca, Aa, ba, start
        di = getattr(self.data, "dairy_intensity", None)
        r = (getattr(self, "feed_rations", None) or {}).get("DCOW")
        if di is None or r is None or not hasattr(di, "get") or not (float(di.get("q_low", 0) or 0) > 0):
            return Qa, ca, Aa, ba, start
        jd = list(self.acts).index("DCOW")
        s0 = float(di["share_low"]); dm = float(di["dmann_rel"])
        col = np.zeros(Aa.shape[0])
        rows_ = [labels.index(l) for l in ("N_balance",) if l in labels]
        for extra in ("_need_row", "_alloc_row"):
            k = getattr(self, extra, None)
            if k is not None and k < Aa.shape[0] and k not in rows_ and (extra != "_alloc_row" or getattr(self, "_alloc_cols", 0)):
                rows_.append(k)
        for i in rows_:
            col[i] = float(Aa[i, jd]) * dm
        req = {"E": float(r.E) * float(di["denne_rel"]), "P": float(r.P) * float(di["dcrpr_rel"]),
               "DMIN": float(r.DMIN) * float(di["ddrmn_rel"])}
        if np.isfinite(float(r.DMAX)):
            req["DMAX"] = float(r.DMAX) * float(di["ddrmx_rel"])
        cz = getattr(self, "_dairy_cz", None)
        if cz is None:
            self._dairy_pending = (col, req)
            return Qa, ca, Aa, ba, start
        self._dairy_pending = None
        Aa = np.hstack([Aa, col[:, None]])
        lo = np.zeros(Aa.shape[1]); lo[-1] = -1.0; lo[jd] = -s0
        hi = np.zeros(Aa.shape[1]); hi[-1] = 1.0; hi[jd] = -(1.0 - s0)
        Aa = np.vstack([Aa, lo, hi]); ba = np.concatenate([ba, [1e-9, 1e-9]])
        labels.extend(["dairy_z_lo", "dairy_z_hi"])
        Qa = np.pad(Qa, ((0, 1), (0, 1))); Qa[-1, -1] = float(di["q_low"]) + float(di["q_high"])
        # milk revenue of the change under the current milk price (EUR per head = 1000 EUR per 1000 heads)
        ps = getattr(self, "_price_shock_now", None)
        pv = getattr(self.data, "livestock_product_value_by_market_coef", None)
        dmilk = 0.0
        if ps is not None and pv is not None and hasattr(pv, "get"):
            mv = pv.get("DCOW.MILK")
            if mv is not None and pd.notna(mv):
                dmilk = float(di["dcomi_rel"]) * float(mv) * float(ps.get("MILK", ps.get("DCOW", 0.0)) or 0.0)
        ca = np.concatenate([ca, [cz - dmilk + self._ghg_cost('dairy')]])
        start = np.concatenate([start, [0.0]])
        self._dairy_col = Aa.shape[1] - 1
        self._dairy_req_extra = {"DCOW": [(self._dairy_col, req)]}
        return Qa, ca, Aa, ba, start

    def _dairy_calibrate_from_duals(self, duals):
        """After the first (baseline) solve without the column: c_z = - (sum_i mu_i A_iz + sum over the
        cows' requirement rows of their dual x the requirement change)."""
        self._cattle_calibrate_from_duals(duals)
        self._genetics_calibrate_from_duals(duals)
        pend = getattr(self, "_dairy_pending", None)
        if pend is None:
            return
        col, req = pend
        rd = getattr(self, "_last_req_duals", None) or {}
        if duals is not None and len(duals) >= len(col) and rd:
            sgn = {"DMAX": -1.0}
            self._dairy_cz = -(float(np.asarray(duals[:len(col)], float) @ col)
                               + sum(float(rd.get(("DCOW", lab), 0.0)) * sgn.get(lab, 1.0) * v for lab, v in req.items()))
        self._dairy_pending = None

    def _grass_calibrate_from_duals(self, duals):
        """After the first (baseline) solve without the column: c_z = - sum_i mu_i A_iz."""
        col = getattr(self, "_grass_pending_col", None)
        if col is None:
            return
        if duals is not None and len(duals) >= len(col):
            self._grass_cz = -float(np.asarray(duals[:len(col)], float) @ col)
        self._grass_pending_col = None

    def _fodder_rows(self):
        """CAPRI-consistent fodder balance rows (non-tradable fodder, SUPBAL_):
        sum_animals use_t_head x heads - u x area_crop <= 0, exact at base.
        Returns [(row, base value EUR/t, rhs, label)]."""
        fb = getattr(self.data, "fodder_balance", None) or {}
        acts_idx = {a: i for i, a in enumerate(self.acts)}
        x0 = self._base_levels().reindex(self.acts).fillna(0.0).values
        out = []
        for feed, rec in fb.items():
            crop = rec.get("crop")
            if crop not in acts_idx:
                continue
            row = np.zeros(len(self.acts))
            row_b = np.zeros(len(self.acts))
            _rs = getattr(self, "ration_state", None) or {}
            _fr = getattr(self, "feed_rations", None) or {}
            for a, t in rec.get("use_t_head", {}).items():
                if a in acts_idx:
                    xr = (_rs.get(a) or {}).get("x", {})
                    row[acts_idx[a]] = float(xr[feed]) / 1000.0 if feed in xr else float(t)
                    # the BASE ration's use per head, for the base gap below (CAPRI's baseline fodder balance)
                    r_ = _fr.get(a)
                    if r_ is not None and feed in list(r_.feeds):
                        row_b[acts_idx[a]] = float(r_.x0[list(r_.feeds).index(feed)]) / 1000.0
                    else:
                        row_b[acts_idx[a]] = row[acts_idx[a]]
            if not row.any():
                continue
            row[acts_idx[crop]] = -float(rec["u_t_per_ha"])
            row_b[acts_idx[crop]] = row[acts_idx[crop]]
            scale = float(np.abs(row) @ np.abs(x0)) or 1.0
            # exact at base in both directions (K36): where the projected herds' fodder use and the projected fodder
            # output differ (use below output in FI1D, ITF5, ITG1...), the gap at base is carried as a constant, as
            # CAPRI's baseline holds its fodder balances. Before, rhs = max(0, gap): with use below output the band row
            # forced the fodder area down to the use, and the no-idle-land rule put the freed land on cereals
            # The gap is the BASE's: base rations x base herds (K46). It was taken with the current ration state, so
            # the balance's right-hand side moved with the rations every iteration - with feeding inside the regional
            # models (animal cells of this row replaced by the feed columns) a fodder balance that loosened or tightened
            # with the last solution's feeding; before, with the ration chosen outside the models at current prices.
            rhs = float(row_b @ x0) + 1e-9 * scale
            out.append((row, float(rec.get("value_eur_t", 0.0)), rhs, "fodder_" + feed))
        return out
