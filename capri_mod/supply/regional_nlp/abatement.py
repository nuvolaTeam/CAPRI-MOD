r"""The regional NLP's abatement block and the ration's fat (moved from capri_mod/supply/capri_regional_nlp.py as they
were, 26 November 2026).
"""
from __future__ import annotations

import hashlib
import os
from collections import OrderedDict

import numpy as np

from capri_mod.settings import current as _settings   # the numerical settings
from capri_mod.supply.regional_nlp.feed_terms import _cascade_loss  # noqa: E402


class NLPAbatementBlock:
    """CapriRegionalNLP's abatement and ration-fat rows and their outputs."""

    def _abatement_block(self, spec, X, y, obj, g_rows, lbg, ubg, lbx, ubx):
        self._fert_tech_pending = None; self._fert_tech_P = None; self._mni_cost_pending = None
        """CAPRI's abatement options inside the regional model (ghgAbatement on; supply_model.gms GHG_Mit_Cost_,
        TotMit_, the v_emiLoss cascade), as far as capri-mod has their data:
          ammonia options per animal and sub-activity (housing/storage MAN group, application APP group): shares
            v_Miti in [0, max], one per option, the groups' shares <= 1; cost per place stock x w x herd x
            (thresh (s - s0) + 0.5 slope (s - s0)^2); N kept from losses through CAPRI's loss cascade
            (ammonia_techs.loss) enters the manure applied (ManureNPK_)
          fertiliser options: one regional share per option (v_Miti(cropMiti, tech)), mineral N x (1 + sum share
            NMIN) in NUTNED_, cost per t of need (a share + 0.5 b share^2) x crop mineral N x area, shares <= max,
            sum <= 1 and sum NMIN share <= the region's cap
          nitrification inhibitor on manure: one regional share, manure N x (1 + share NMAN) in NUTNED_, cost per t of
            manure N treated"""
        import casadi as ca
        # CAPRI's equations of the options (supply/supply_model.gms), one function each
        from capri_mod.supply.equations.supply_model.mitigation import (
            TotMit_, GHG_Mit_Cost_herd, Tot_MitFert_, GHG_Mit_Cost_perShare, GHG_Mit_Cost_targFertSyn_factor,
            GHG_Mit_Cost_targFertSyn_base, GHG_Mit_Cost_targFertMan_excr, GHG_Mit_Cost_catc)
        from capri_mod.supply.equations.supply_model.objective import (
            LINEAR_carbonTax_ammOptions, LINEAR_carbonTax_NH3kept, LINEAR_carbonTax_manInhibitor, LINEAR_carbonTax_N2OCRO)
        from capri_mod.supply.equations.supply_model.nutrients import (
            manExportOrAppl_kept, NUTNED_mitiExcr, fertDistCres_catcBioFix)
        from capri_mod.supply.equations.supply_model.premiums import catcMiti_, winterCover_, ecoSetAside_catc
        self.amm_kept = None; self.fert_eff = None; self.man_eff = None; self._nitr_phi = None; self._fert_phi = {}
        self.n_rows_g = {}; self.synN_row = None
        self.abat = {}
        new = []
        nx0 = int(X.shape[0])
        # CAPRI's winter cover (catch crops) as a choice (envind/cover_crops.gms; supply_model.gms catcMiti_,
        # winterCover_, e_minCoverCrops): the share m of UAAR, cost per ha of UAAR (costParLin + pmpParLin) m
        # + 1/2 pmpParSqr m^2 (+ the calibration's linear term), the land not under winter cover as its limit, its
        # BioFix N in the arable residue pool (fertDistCres_), its share in the loss cascade's runoff (RUNSURFN_)
        self._catc_m = None; self.catc_n = None; self._catc_ncoef = 0.0
        cs = spec.get("catc")
        if cs:
            zc = ca.SX.sym("catc", 1)
            m = zc[0]
            uaa, m0 = float(cs["uaa"]), float(cs["m0"])
            # the calibration term: the option's (its cost curve), or with the share fixed (the CATC activity at its
            # input cost) the reference form's where the calibration was in that form (K188; zero before, K170)
            _da = spec.get("dabat") or {}
            dl = float(_da.get(("catc_ref",), 0.0)) if cs.get("fixmiti") else float(_da.get(("catc",), 0.0))
            # the land of catcMiti_ and GHG_Mit_Cost_ (K186): with the option a choice the current land,
            # sum(landTypesNoSlak, v_actLevl), the fertilisation block's land columns, as U + (L - L0) so that the base
            # is the calibration's; with the share held (FixMiti, the reference form) U (m the CATC level over U)
            uaaEqu, lc_ = self._pv(uaa), []
            if not cs.get("fixmiti") and not cs.get("ref_form"):
                npk_ = spec.get("npk") or {}
                lc_ = [int(j) for j in (npk_.get("land_cols") or npk_.get("crop_cols") or []) if int(j) < self.n0]
                if lc_:
                    uaaEqu = self._pv(uaa - float(sum(self.xb[j] for j in lc_))) + ca.sum1(y[lc_])
            catc_lev = catcMiti_(uaaEqu, m)
            # GHG_Mit_Cost_ on the UAA; winterCover_ with catcMiti_'s area (mitigation.py, premiums.py)
            obj = obj + GHG_Mit_Cost_catc(uaaEqu, self._pv(float(cs["k1"]) + float(cs["lin"]) + dl),
                                          self._pv(0.5 * float(cs["sqr"])), m)
            g_rows.append(winterCover_(self._lin(y, [(int(j), float(s)) for j, s in cs["row"]]),
                                       catc_lev, self._pv(1.0 / uaa)))
            lbg.append(-np.inf); ubg.append(float(cs["rhs"]) / uaa)
            self._catc_m = m
            # ecoSetAside_: catch crops on the eligible side at CAPRI's weight (setaEco includes CATC)
            eco = (spec.get("cap_rules") or {}).get("ecoSetAside") or {}
            if float(eco.get("catc_w", 0.0) or 0.0) > 0 and "ecoSetAside" in getattr(self, "cap_rows", {}):
                ie = self.cap_rows["ecoSetAside"]
                sce = max(float(eco.get("scale", 1.0)), 1e-6)
                g_rows[ie] = ecoSetAside_catc(g_rows[ie], self._pv(float(eco["catc_w"]) / sce) * uaaEqu, m)
            # fertDistCres_'s winter cover term (t N; nutrients.py): the catch crops' BioFix N in the arable residue
            # pool and the gross balance only with CAPRI's %ghgAbatement% on (supply_model.gms l. 1073-1079), so not
            # in its reference form (K188); on the whole catch-crop area as CAPRI's (supply.catch_crop_biofix_area
            # "capri", K204), or on the area above the base share ("increment", the form until 24 November 2026)
            self._catc_ncoef = uaa * 1000.0 * float(cs["biofix"])                        # t N per unit share at base
            _catc0 = m0 * uaa if str(_settings().get("supply.catch_crop_biofix_area")) == "increment" else 0.0
            self.catc_n = (None if cs.get("ref_form")
                           else fertDistCres_catcBioFix(self._pv(1000.0 * float(cs["biofix"])), catc_lev,
                                                        self._pv(_catc0)))
            gt_ = spec.get("ghg_min")
            if gt_ and self.catc_n is not None:
                # CAPRI's emission tax on the catch crops' crop-residue N2O (N2OCRO: BioFix x CATC x EF1 x 44/28, in
                # GN2O and so in the taxed GGWP; their soil carbon CO2SEQ is not in GGWP)
                obj = obj + LINEAR_carbonTax_N2OCRO(self._pv(float(gt_["d"])), self.catc_n)
            new.append(zc)
            lbx += [float(cs.get("lb", 0.0))]; ubx += [float(cs["ub"])]
            self.abat["catc"] = {"off": nx0, "uaa": uaa, "m0": m0, "land_cols": lc_}
        am = spec.get("amm")
        if am and am.get("techs"):
            techs = [t for t in am["techs"] if t["act"] in self.act_idx and t["smax"] > 0]
            sig = ca.SX.sym("sig", len(techs))
            if techs:
                pv = self._pv
                th_ = [float(t["th"]) + float((spec.get("dabat") or {}).get(("amm", t["act"], t["key"], t["tech"]), 0.0))
                       for t in techs]
                d = sig - pv([float(t["s0"]) for t in techs])
                hv = y[[self.act_idx[t["act"]] for t in techs]]
                # GHG_Mit_Cost_ on the herd (mitigation.py)
                obj = obj + ca.sum1(GHG_Mit_Cost_herd(pv([float(t["stock"]) * float(t["w"]) for t in techs]), hv,
                                                      pv(th_), pv([0.5 * float(t["slope"]) for t in techs]), d))
                # CAPRI's emission tax (ghgTax) on the options' manure N2O through the loss cascade, per unit of the
                # sub-activity and share from the base shares (the activity's own coefficient is taken there)
                tg = [float(t.get("ghg", 0.0) or 0.0) * float(t["w"]) for t in techs]
                if any(tg):
                    obj = obj + ca.sum1(LINEAR_carbonTax_ammOptions(pv(tg), hv, d))
            byk = {}
            for kk, t in enumerate(techs):
                byk.setdefault((t["act"], t["key"]), {})[t["tech"]] = sig[kk]
            from capri_mod.supply import ammonia_techs as _at
            kept = 0
            kept_nh3 = 0
            for (a, key), shs in byk.items():
                sub = next(s_ for s_ in am["subs"][a] if s_["key"] == key)
                sh = {tt["tech"]: shs.get(tt["tech"], tt["ini"]) for tt in sub["techs"]}
                sh0 = {tt["tech"]: tt["ini"] for tt in sub["techs"]}
                wy = self._pv(float(am["sc"][a]) * float(sub["mrel"]) * float(sub["w"])) * y[self.act_idx[a]]
                if _at.cascade_data(sub) is not None:
                    # CAPRI's full cascade (GRAZN_ ... APPLN_): the manure keeps every N loss the options avoid
                    # (manExportOrAppl_: MANN x (1 - GasRunTot)); the NH3 part for the tax's indirect N2O
                    w0_, w1_ = am.get("wc") or (0.0, 0.0)
                    _wc_free = self._catc_m is not None and not (spec.get("catc") or {}).get("fixmiti")
                    if _wc_free:
                        w1_ = self._catc_m
                    # CAPRI bounds every loss at zero (set_supply_bounds.gms: v_emiLoss.lo = 0): options from different
                    # groups whose effects on one loss add up to more than 1 must not drive it negative. A row for
                    # each loss that can turn negative at the options' maximum shares and is not negative at base.
                    # The cascade is evaluated once per share set (base, current) and its parts reused
                    L0 = _at.cascade(sub, sh0, w0_)
                    L1 = _at.cascade(sub, sh, w1_)
                    smx_ = {tt_["tech"]: float(tt_["smax"]) for tt_ in techs if tt_["act"] == a and tt_["key"] == key}
                    shx = {tt["tech"]: smx_.get(tt["tech"], tt["ini"]) for tt in sub["techs"]}
                    Lx = _at.cascade(sub, shx, 1.0 if _wc_free else float(w0_))
                    for k_, v_ in Lx.items():
                        if k_[1] in ("RunTot", "GasRunTot") or float(v_) >= -1e-12 or float(L0.get(k_, 0.0)) < 0.0:
                            continue
                        g_rows.append(L1[k_]); lbg.append(0.0); ubg.append(np.inf)
                    _nh3 = lambda L_: L_[("NH3", "Graz")] + L_[("NH3", "Hous")] + L_[("NH3", "Stor")] + L_[("NH3", "Appl")]
                    kept = kept + manExportOrAppl_kept(wy, L0[("N", "GasRunTot")], L1[("N", "GasRunTot")])
                    kept_nh3 = kept_nh3 + manExportOrAppl_kept(wy, _nh3(L0), _nh3(L1))
                else:
                    # manExportOrAppl_ as above, with the old loss function (one difference for both sums)
                    d_ = _cascade_loss(sub, sh0) - _cascade_loss(sub, sh)
                    kept = kept + wy * d_
                    kept_nh3 = kept_nh3 + wy * d_
            self.amm_kept = kept
            if float(am.get("tax_nh3", 0.0) or 0.0) > 0:
                # the indirect N2O of the NH3 the options keep (the soil N2O of the mineral N it displaces follows the
                # purchases in the fertilisation block)
                obj = obj - LINEAR_carbonTax_NH3kept(self._pv(float(am["tax_nh3"])), kept_nh3)
            grp = {}
            for kk, t in enumerate(techs):
                grp.setdefault(t["grp"], []).append(kk)
            for _, ks in grp.items():
                # TotMit_ for the options' group (no control eliminated)
                g_rows.append(TotMit_([sig[kk] for kk in ks])); lbg.append(-np.inf); ubg.append(1.0)
            o_amm = nx0 + sum(int(v.shape[0]) for v in new)
            new.append(sig)
            if am.get("fixed"):
                # CONOPT's behaviour without a policy incentive (supply_module, K63): the options
                # stay at their base shares
                lbx += [float(t["s0"]) for t in techs]; ubx += [float(t["s0"]) for t in techs]
            else:
                lbx += [0.0] * len(techs); ubx += [float(t["smax"]) for t in techs]
            self.abat["amm"] = {"techs": techs, "off": o_amm}
        ft = spec.get("fert_tech")
        if ft and ft.get("techs") and ft.get("crops"):
            T_ = ft["techs"]
            phi = ca.SX.sym("phi", len(T_))
            pv = self._pv
            ec_ = ft.get("emical") or {}
            # the options' parameters in the order the graph records them (per option: NMIN, NMIN + EmiCalMin, the cost
            # terms), then CAPRI's sums over the options (mitigation.py)
            p_nm, p_nmec, p_c1, p_c2, phis = [], [], [], [], []
            for tt, (name, nm, a_, b_, smax) in enumerate(T_):
                if str(name).upper() == "NITR_INH":
                    self._nitr_phi = (phi[tt], float(nm))
                self._fert_phi[str(name)] = (phi[tt], float(nm))
                p_nm.append(pv(float(nm)))
                p_nmec.append(pv(float(nm) + float(ec_.get(name, 0.0) or 0.0)))
                a_ = float(a_) + float((spec.get("dabat") or {}).get(("fert", name), 0.0))
                p_c1.append(pv(a_)); p_c2.append(pv(0.5 * float(b_))); phis.append(phi[tt])
            Eff = Tot_MitFert_(p_nm, phis)                       # sum v_Miti NMIN: Tot_MitFert_, NUTNED_'s factor
            Ebase = GHG_Mit_Cost_targFertSyn_factor(p_nmec, phis)
            cost = GHG_Mit_Cost_perShare(p_c1, p_c2, phis)
            # CAPRI's GHG_Mit_Cost_ (supply_model.gms l. 5062-5068): the fertiliser options' cost per t of crop N need
            # met by mineral N, - cost x v_netPutQuant(NITF) x (1 + sum (NMIN + EmiCalMin) v_Miti) (KNOWN_ISSUES K175:
            # until 18 November 2026 on the purchases alone, 10-17% too cheap at the Green Deal's shares); the
            # fertilisation block's N purchases take it (_fert_block), else the crops' base mineral N (the build's end).
            # Every option's IniShare is 0, so the base and its calibration are unchanged
            self._fert_tech_pending = (GHG_Mit_Cost_targFertSyn_base(cost, Ebase), list(ft["crops"]))
            self.fert_eff = Eff
            # TotMit_ for the fertiliser options (no control eliminated); Tot_MitFert_ <= its cap less 1
            g_rows.append(TotMit_([phi[tt] for tt in range(len(T_))])); lbg.append(-np.inf); ubg.append(1.0)
            if ft.get("ecap") is not None:
                g_rows.append(Eff); lbg.append(-np.inf); ubg.append(float(ft["ecap"]))
            o = nx0 + sum(int(v.shape[0]) for v in new)
            new.append(phi)
            lbx += [0.0] * len(T_); ubx += [float(t[4]) for t in T_]
            self.abat["fert"] = {"techs": T_, "off": o}
        mni = spec.get("mni")
        if mni and float(mni.get("smax", 0.0)) > 0 and any(m_ > 0 for _, m_ in mni["w"]):
            sm = ca.SX.sym("mni", 1)
            W = self._lin(y, [(c_, float(m_) / 1000.0) for c_, m_ in mni["w"]])        # excreted manure N, kt
            s_ = sm[0]
            S0m = float(mni["S0"]) + float((spec.get("dabat") or {}).get(("mni",), 0.0))
            # the emission tax's value per t of excreted manure N treated (the accounts' emission factors)
            obj = obj - LINEAR_carbonTax_manInhibitor(W, self._pv(float(mni.get("vtax", 0.0))), s_)
            self.man_eff = NUTNED_mitiExcr(self._pv(float(mni["nman"])), s_)       # NUTNED_'s 1 + v_Miti NMAN
            if "N" in ((spec.get("npk") or {}).get("nutrients") or {}):
                # CAPRI's GHG_Mit_Cost_ on its base for targFertMan, ManureNPK x (1 + incEmiAppl) x (1 + NMAN s): the
                # fertilisation block's manure N pool, so the term is added there (_fert_block; KNOWN_ISSUES K183)
                self._mni_cost_pending = (s_, S0m, float(mni["slope"]), float(mni["nman"]), W,
                                          sum(float(m_) * float(self.xb[int(c_)]) for c_, m_ in mni["w"]) / 1000.0)
                self._mni_base = None                     # set by _fert_block: the pool at the calibration point, kt
            else:
                obj = obj + GHG_Mit_Cost_targFertMan_excr(W, self._pv(S0m), self._pv(0.5 * float(mni["slope"])), s_)
                self._mni_base = sum(float(m_) * float(self.xb[int(c_)]) for c_, m_ in mni["w"]) / 1000.0
            o = nx0 + sum(int(v.shape[0]) for v in new)
            new.append(sm)
            lbx += [0.0]; ubx += [float(mni["smax"])]
            self.abat["mni"] = {"off": o, "S0": float(mni["S0"])}        # relSubs0 x costParLin, the calibration's
        # conservation and no tillage (envind/tillage.gms; abatement._till_spec): the shares v_Miti(cropMiti, tech,
        # CO2SEQ) of the tillage area, TotMit_ with no control, GHG_Mit_Cost_ on the tillage area, NoTill's N2O of
        # mineral N in the loss cascade (GASTOTNETF_, _netf_eff)
        self._till_n2o = None
        ts = spec.get("till")
        if ts and ts.get("techs"):
            from capri_mod.supply.equations.supply_model.mitigation import GHG_Mit_Cost_till
            T_ = ts["techs"]
            zt = ca.SX.sym("till", len(T_))
            L = self._lin(y, [(int(c_), 1.0) for c_ in ts["cols"]])                       # tillage area, 1000 ha
            _da = spec.get("dabat") or {}
            for k_, t in enumerate(T_):
                c1 = float(t["k1"]) + float(t["lin"]) + float(_da.get(("till", t["name"]), 0.0))
                obj = obj + GHG_Mit_Cost_till(L, self._pv(c1), self._pv(0.5 * float(t["sqr"])), zt[k_])
            # TotMit_(cropMiti, CO2SEQ): no control + the options = 1, no control >= 0
            g_rows.append(TotMit_([zt[k_] for k_ in range(len(T_))])); lbg.append(-np.inf); ubg.append(1.0)
            # GASTOTNETF_'s tillage term, sum over the options of othImpact N2OSYN x share, and its base value
            self._till_n2o = (sum(self._pv(float(t["n2osyn"])) * zt[k_] for k_, t in enumerate(T_)),
                              sum(float(t["n2osyn"]) * float(t["m0"]) for t in T_))
            o = nx0 + sum(int(v.shape[0]) for v in new)
            new.append(zt)
            lbx += [0.0] * len(T_); ubx += [float(t["ub"]) for t in T_]
            self.abat["till"] = {"off": o, "techs": T_,
                                 "area0": sum(float(self.xb[int(c_)]) for c_ in ts["cols"] if int(c_) < len(self.xb))}
        # urea substitution (envind/ammo_tech.gms; abatement._urea_spec): the share v of the mineral N bought switched
        # from urea, TotMit_ with no control, GHG_Mit_Cost_ on the purchases (the fertilisation block, _fert_block),
        # its NH3 of mineral N in the loss cascade (GASTOTNETF_, _netf_eff). Only with the N fertilisation block (its
        # purchases and loss cascade carry the option)
        self._urea = None; self._urea_pending = None
        us = spec.get("urea")
        if us and "N" in ((spec.get("npk") or {}).get("nutrients") or {}) and float(us.get("m1", 0.0)) > 0:
            zu = ca.SX.sym("urea", 1)
            c1 = float(us["c1"]) + float((spec.get("dabat") or {}).get(("urea",), 0.0))
            self._urea_pending = GHG_Mit_Cost_perShare([self._pv(c1)], [self._pv(0.5 * float(us["c2"]))], [zu[0]])
            self._urea = (zu[0], self._pv(float(us["eff"])))
            g_rows.append(TotMit_([zu[0]])); lbg.append(-np.inf); ubg.append(1.0)
            o = nx0 + sum(int(v.shape[0]) for v in new)
            new.append(zu)
            lbx += [0.0]; ubx += [float(us["m1"])]
            self.abat["urea"] = {"off": o, "subs0": float(us["subs0"])}
        # the legume share in temporary grassland (envind/leg_share.gms; abatement._legsh_spec): the share v of OFAR,
        # TotMit_ with no control, GHG_Mit_Cost_ on OFAR's level, OFAR's fixation x (1 + othImpact v) in NUTNED_ and the
        # N-surplus row (the fertilisation block, _fert_block). Only with the N fertilisation block
        self._legsh = None
        ls = spec.get("legsh")
        if ls and "N" in ((spec.get("npk") or {}).get("nutrients") or {}) and float(ls.get("m1", 0.0)) > 0:
            from capri_mod.supply.equations.supply_model.mitigation import GHG_Mit_Cost_legSh
            zl = ca.SX.sym("legsh", 1)
            c1 = float(ls["c1"]) + float((spec.get("dabat") or {}).get(("legsh",), 0.0))
            obj = obj + GHG_Mit_Cost_legSh(y[int(ls["col"])], self._pv(c1), self._pv(0.5 * float(ls["c2"])), zl[0])
            self._legsh = {"v": zl[0], "cols": {int(ls["col"])} | ({int(ls["mix"])} if ls.get("mix") is not None else set()),
                           "need_share": float(ls["need_share"]), "oi": float(ls["oi"]), "fix": float(ls["fix"]),
                           "col": int(ls["col"]), "mix": ls.get("mix"), "ydiff": float(ls.get("ydiff", 0.0))}
            g_rows.append(TotMit_([zl[0]])); lbg.append(-np.inf); ubg.append(1.0)
            o = nx0 + sum(int(v.shape[0]) for v in new)
            new.append(zl)
            lbx += [0.0]; ubx += [float(ls["m1"])]
            self.abat["legsh"] = {"off": o, "subs0": float(ls["subs0"]), "x0": float(ls["x0"])}
        if new:
            X = ca.vertcat(X, *new)
        return X, obj

    def _supplement_fat_block(self, spec, X, y, obj, g_rows, lbg, ubg, lbx, ubx):
        """CAPRI's limit of the ration's fat with linseed (SupplementPerc_, supply/supply_model.gms l. 608-633; ghgAbatement
        on, where the member state has Line_tot): per cattle animal with the linseed column (supply/livestock.py
        _genetics_columns, LINE_Tot), the fat percentage p, 0 <= p <= 0.05, and its slack s >= 0 (supply/
        set_miti_bounds.gms l. 471-476), the row in its total form (equations/supply_model/feeding.py SupplementPerc_:
        the feed bulks' fat per head, the flexible feeds' and the fixed ones' at their base amounts, and the linseed's
        sh z / X0), and the slack's penalty in the objective (GHG_Mit_Cost_, equations/supply_model/mitigation.py
        GHG_Mit_Cost_supplementSlack: CAPRI's v_Miti^2 v_actLevl = z^2 / X at the current herd, since 23 November 2026;
        the herd floored at 1e-6 of its base level, a guard against a division by zero that no solution reaches). spec["supp_fat"]: {animal: {"col", "shr", "D", "fat": {feed: kg of fat per kg}}}
        (abatement._supp_fat_spec)."""
        import casadi as ca
        from capri_mod.supply.equations.supply_model.feeding import SupplementPerc_
        from capri_mod.supply.equations.supply_model.mitigation import GHG_Mit_Cost_supplementSlack
        self.supp_fat = {}
        sf = spec.get("supp_fat") or {}
        rats = spec.get("rations") or {}
        new = []
        nx0 = int(X.shape[0])
        for a, d in sorted(sf.items()):
            r = rats.get(a)
            if r is None or a not in self.act_idx or not float(d.get("D", 0.0)) > 0:
                continue
            ia = self.act_idx[a]
            tf = {f: float((d.get("fat") or {}).get(f, 0.0)) for f in r.feeds}
            ks = [k for k, fe in enumerate(self.feeds) if fe[0] == a]
            fixed = ~np.asarray(r.flex, bool)
            fat_fix = float(sum(float(r.x0[j]) * tf[f] for j, f in enumerate(r.feeds) if fixed[j]))
            cf = [tf[self.feeds[k][1]] for k in ks]
            fat_h = (ca.dot(self._pv(cf), self._fhv[ks]) if len(ks) > 1
                     else (self._pv(cf[0]) * self._fhv[ks[0]] if ks else 0)) + self._pv(fat_fix)
            D, sh, col = float(d["D"]), float(d["shr"]), int(d["col"])
            X0 = max(float(self.xb[ia]), 1e-3)
            ps = ca.SX.sym("suppFat_" + a, 2)                    # v_supplementPerc, v_supplementSlack
            zc = y[col]
            row_ = len(g_rows)                                   # the row's place in g (calibrate fixes its multiplier)
            g_rows.append(SupplementPerc_(fat_h, self._pv(1.0 / D), self._pv(sh), zc, y[ia], self._pv(1.0 / X0),
                                          ps[0], ps[1]))
            lbg.append(0.0); ubg.append(0.0)
            obj = obj + GHG_Mit_Cost_supplementSlack(zc * zc / ca.fmax(y[ia], self._pv(1e-6 * X0)), self._pv(D),
                                                     ps[1])
            o = nx0 + 2 * len(new)
            new.append(ps)
            lbx += [0.0, 0.0]; ubx += [0.05, np.inf]
            self.supp_fat[a] = {"off": o, "ia": ia, "col": col, "D": D, "shr": sh, "ks": ks, "cf": cf,
                                "fat_fix": fat_fix, "row": row_}
        if new:
            X = ca.vertcat(X, *new)
        return X, obj

    def supplement_fat_share(self, x, a):
        """The ration's fat share of animal a at x (SupplementPerc_'s left side: the feed bulks' fat per head and the
        linseed's, over the intake D), or None without the row."""
        d = (getattr(self, "supp_fat", None) or {}).get(a)
        if d is None:
            return None
        x = np.asarray(x, float)
        u = [float(x[self.n0 + k]) * self.feeds[k][4] for k in d["ks"]]
        Xa = float(x[d["ia"]]) * float(self.sc[d["ia"]])
        z = float(x[d["col"]]) * float(self.sc[d["col"]])
        fat = float(np.dot(d["cf"], u)) + d["fat_fix"]
        return fat / d["D"] + (d["shr"] * z / Xa if Xa > 0 else 0.0)

    def abatement_outputs(self, x):
        """Shares of the options at x: {"amm": {(act, key, tech): share}, "fert": {tech: share}, "mni": share,
        "catc": share, "catc_area": 1000 ha, "till": {tech: share}, "urea": share, "legsh": share}."""
        out = {}
        a = self.abat.get("amm")
        if a:
            out["amm"] = {(t["act"], t["key"], t["tech"]): float(x[a["off"] + k]) for k, t in enumerate(a["techs"])}
        f = self.abat.get("fert")
        if f:
            out["fert"] = {t[0]: float(x[f["off"] + k]) for k, t in enumerate(f["techs"])}
        m = self.abat.get("mni")
        if m:
            out["mni"] = float(x[m["off"]])
        c_ = self.abat.get("catc")
        if c_:
            out["catc"] = float(x[c_["off"]])
            out["catc_area"] = self.catc_area(x)
        t_ = self.abat.get("till")
        if t_:
            out["till"] = {t["name"]: float(x[t_["off"] + k]) for k, t in enumerate(t_["techs"])}
        u_ = self.abat.get("urea")
        if u_:
            out["urea"] = float(x[u_["off"]])
        l_ = self.abat.get("legsh")
        if l_:
            out["legsh"] = float(x[l_["off"]])
        sf_ = getattr(self, "supp_fat", None)
        if sf_:
            out["supp_fat"] = {a: (float(x[d["off"]]), float(x[d["off"] + 1])) for a, d in sf_.items()}
        return out

    def catc_area(self, x):
        """The catch crop area of the solution x (1000 ha), catcMiti_: the share times U, with the option a choice
        times U + (L - L0), the current land (K186; _abatement_block)."""
        c_ = self.abat.get("catc")
        if not c_:
            return 0.0
        land = float(c_["uaa"])
        if c_.get("land_cols"):
            yv = np.asarray(self.f_y(x)).ravel()
            land += float(sum(yv[j] - self.xb[j] for j in c_["land_cols"]))
        return float(x[c_["off"]]) * land
