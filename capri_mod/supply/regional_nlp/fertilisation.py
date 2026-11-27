r"""The regional NLP's fertilisation block (moved from capri_mod/supply/capri_regional_nlp.py as it was, 26 November
2026).
"""
from __future__ import annotations

import hashlib
import os
from collections import OrderedDict

import numpy as np

from capri_mod.settings import current as _settings   # the numerical settings
from capri_mod.supply.regional_nlp.feed_terms import ca_eval, foc_fb_mode  # noqa: E402
from capri_mod.supply.regional_nlp.solver_options import linear_solver_options  # noqa: E402


class NLPFertilisationBlock:
    """CapriRegionalNLP's fertilisation rows and their outputs (_fert_block, _netf_eff, fert_outputs, fert_at)."""

    def _fert_block(self, npk, X, y, obj, g_rows, lbg, ubg, lbx, ubx):
        """CAPRI's fertilisation block, per nutrient n (N, P, K), the rows written by CAPRI's equations
        (capri_mod/supply/equations/supply_model/: nutrients.py NUTNED_, fertDistMine_, fertDistExcr_, fertDistCres_,
        ManureNPK_; inner_fert.py e_focFertDist, e_fertDistPartialRegu, e_fertDistReguMax; fert_limits.py e_synNMax;
        n_surplus.py SURTOT_REST_), supply_model.gms l. 862-1212 and 1527-1737:

          NUTNED_(g,n)    sum_c share_cg x_c need_cn          (need: CAPRI's per ha x need factor of yield x kappa_n)
                          = eff_n x_g,MINE + avail_n x_g,EXCR + avail_C x (x_g,CRES  [arable groups]
                                                                        | own residues [permanent groups])
          fertDistMine_   sum_g x_g,MINE = v_netPutQuant(n)  (purchases, >= 0, priced at CAPRI's unit value)
          fertDistExcr_   sum_g x_g,EXCR = manure applied   (ManureNPK_: excreted less losses, less net exports)
          fertDistCres_   sum_arable g x_g,CRES = arable residue pool
          e_focFertDist   (alpha_gs - 1) / x_gs - beta_gs = lambda_g e_s - mu_s,  mu_MINE = 0
                          (e_fertDistPartial written with the inverse directly: x >= 0.001 x mode, as CAPRI bounds it)
          avail_N         endogenous (endoManAvFact on): g0 + slope x (manure / land - base manure / land); the first
                          order conditions use the base factor, as CAPRI's e_focFertDist (v_nutAvailFactExcr)
        Flows in t, scaled by their prior modes; bounds 0.001-1000 x mode, duals within +-10 (set_fert_priors.gms)."""
        import casadi as ca
        from capri_mod.supply.equations.supply_model.nutrients import (
            NUTNED_, NUTNED_ownCres, NUTNED_availFact, NUTNED_supply, fertDistMine_, fertDistExcr_, fertDistCres_,
            ManureNPK_trade, ManureNPK_ammKept, fertDistCres_catc, v_nutAvailFactExcr_endo, NUTNED_legSh)
        from capri_mod.supply.equations.supply_model.inner_fert import (
            gamma_prior, e_focFertDist_dual, e_focFertDist_term, e_focFertDist_term_slack, e_fertDistPartialRegu_upper,
            e_fertDistReguMax, e_focFertDist_FB)
        from capri_mod.supply.equations.supply_model.fert_limits import e_synNMax
        from capri_mod.supply.equations.supply_model.n_surplus import SURTOT_REST_, e_BIOFIX_legSh
        from capri_mod.supply.equations.supply_model.objective import (
            LINEAR_netPutQuant, LINEAR_carbonTaxNITF, LINEAR_carbonTaxN2OLEA)
        from capri_mod.supply.equations.supply_model.mitigation import GHG_Mit_Cost_targFertSyn
        lin = lambda pairs: self._lin(y, pairs)
        pv = self._pv
        self.fert = {}
        nx0 = int(X.shape[0])
        new = []
        lc = [int(j) for j in (npk.get("land_cols") or npk.get("crop_cols") or [])]
        land = ca.sum1(y[lc]) if len(lc) > 1 else (y[lc[0]] if lc else 0)
        self.fert_rows = [len(g_rows), None]
        _u_lo = float(_settings().get("fertiliser.flow_lower_bound_mode_share"))
        # DEP-49's form of the first-order condition: "always", "off" (CAPRI's equality), or "fallback" (the default: CAPRI's
        # equality, the complementarity only in the retry of a solve that failed with it, nlp.py; npk["foc_fb"])
        _fb_on = bool(npk["foc_fb"]) if "foc_fb" in npk else foc_fb_mode() == "always"
        _fb_eps = float(_settings().get("fertiliser.foc_fb_smoothing"))
        self.excr_rows = {}                     # nutrient -> (row of fertDistExcr_, its scale): ManureNPK_'s value
        for nut, d in npk["nutrients"].items():
            G = d["groups"]
            flows = []                                              # (group index, source, mode t, accuracy)
            for gi, g_ in enumerate(G):
                for s_, m in g_["modes"].items():
                    a_ = g_["acc"].get(s_, 1.0) if isinstance(g_["acc"], dict) else float(g_["acc"])
                    flows.append((gi, s_, max(float(m), 1e-6), float(a_)))
            nfl = len(flows)
            pools = [s_ for s_ in ("EXCR", "CRES") if any(f[1] == s_ for f in flows)]
            T = float(np.mean([f[2] for f in flows]))
            Pscale = max(sum(f[2] for f in flows if f[1] == "MINE"), 1.0)
            r_nut0 = len(g_rows)
            u = ca.SX.sym(f"u{nut}", nfl)
            lam = ca.SX.sym(f"l{nut}", len(G))
            mu = ca.SX.sym(f"m{nut}", len(pools))
            Pv = ca.SX.sym(f"P{nut}", 1)
            P = Pv[0] * pv(Pscale)
            xv = u * pv([f[2] for f in flows])                      # flows in t
            x = [xv[i] for i in range(nfl)]
            e = {"MINE": pv(float(d["eff"])), "EXCR": pv(float(d["g0"])), "CRES": pv(float(d["gc"]))}
            # NUTNED_'s mineral and residue efficiencies: CAPRI's v_emiLoss of mineral N as functions of the options
            # (1 - GasRunTot, and 1 - N2O GasTot for the residues; supply_model.gms l. 1143, 1204, 1219), the first-order
            # conditions keep the base loss (CAPRI's p_emiLoss, l. 1629-1633)
            eN = self._netf_eff(d) if nut == "N" else None
            effM, effC = (eN if eN is not None else (e["MINE"], e["CRES"]))
            # the first-order conditions' factors (e_focFertDist, supply_model.gms l. 1621-1634): CAPRI writes the
            # residues' with the mineral N's total loss, v_nutAvailFactCRes x (1 - p_emiLoss(NETF, N, GasRunTot)),
            # where NUTNED_ (l. 1196) has their N2O loss alone; taken as CAPRI writes it (14 November 2026; with
            # CAPRI's priors the base allocation moves by less than 0.5 kg/ha, BG02 and RO05 checked)
            eF = dict(e)
            if nut == "N" and d.get("netf"):
                from capri_mod.supply.equations.supply_model import n_flow as _nf
                _L0 = _nf.netf(d["netf"]["fr"], float(d["netf"]["run_surf"]))
                eF["CRES"] = pv(float(d["gc"]) / (1.0 - float(_L0["N2O"])) * float(d["eff"]))
            E = lin(d["E"]); C = lin(d["C"])
            if float(d.get("E_const", 0.0) or 0.0) != 0.0:
                # the region's base manure trade as a level (CAPRI's ManureNPK_ with v_manureExports /
                # v_manureImports at the calibration point; supply.manure_base_trade "capri", K167): base imports - base
                # exports, t; the columns' manure is their full manure
                E = ManureNPK_trade(E, pv(float(d["E_const"])))
            if nut == "N" and getattr(self, "catc_n", None) is not None:
                C = fertDistCres_catc(C, self.catc_n)               # catch crops' BioFix N (fertDistCres_)
            if nut == "N" and self.amm_kept is not None:
                E = ManureNPK_ammKept(E, self.amm_kept)             # N the ammonia options keep (ManureNPK_)
            if nut == "N" and getattr(self, "_mni_cost_pending", None) is not None:
                # CAPRI's GHG_Mit_Cost_ for the inhibitor on manure on its own base, ManureNPK x (1 + incEmiAppl) x
                # (1 + NMAN s): the manure N pool E, at the tail (K183; until 19 November 2026 on the excreted N)
                from capri_mod.supply.equations.supply_model.mitigation import GHG_Mit_Cost_targFertMan
                s_m, S0m, slope_m, nman_m = self._mni_cost_pending[:4]
                obj = obj + GHG_Mit_Cost_targFertMan(E, s_m, pv(S0m), pv(slope_m), pv(nman_m))
                _xb = np.asarray(self.xb, float)
                self._mni_base = (sum(float(v_) * float(_xb[int(j_)]) for j_, v_ in d["E"] if int(j_) < len(_xb))
                                  + float(d.get("E_const", 0.0) or 0.0)) / 1000.0      # the pool at the base, kt
                self._mni_cost_pending = None
            if d.get("slope"):
                availE = v_nutAvailFactExcr_endo(e["EXCR"], pv(float(d["slope"])), E, land, pv(float(d["m0E"])))
            else:
                availE = e["EXCR"]
            # NUTNED_
            for gi, g_ in enumerate(G):
                sc_ = max(sum(m for (gj, s_, m, acc) in flows if gj == gi), 1.0)
                need = self._lin(y, g_["need"], scale=sc_)
                ls_ = getattr(self, "_legsh", None) if nut == "N" else None
                if ls_ is not None:
                    # the legume share's term (NUTNED_, l. 1111-1112) on OFAR's need columns of the group, the part
                    # that follows DATA(OFAR, NITF) (need_yf: v_cropNutNeedAddFact's part held, DEP-10 item 1b)
                    _nyf = g_.get("need_yf") or {}
                    _ofar = [(j_, c_ * float(_nyf.get(j_, 1.0))) for j_, c_ in g_["need"] if int(j_) in ls_["cols"]]
                    if _ofar:
                        need = NUTNED_legSh(need, self._lin(y, _ofar, scale=sc_), pv(ls_["need_share"]), ls_["v"])
                if g_["perm"] and g_["own"]:
                    need = NUTNED_ownCres(need, self._lin(y, [(c_, float(v_)) for c_, v_ in g_["own"]], scale=sc_),
                                          effC)
                # the flows' factors: fertiliser options (1 + sum v_Miti NMIN), inhibitor on manure (1 + v_Miti NMAN)
                sup = NUTNED_supply([(NUTNED_availFact(s_, availE, effM, effC, e[s_],
                                                       self.fert_eff if nut == "N" else None,
                                                       self.man_eff if nut == "N" else None), x[i])
                                     for i, (gj, s_, m, acc) in enumerate(flows) if gj == gi])
                g_rows.append(NUTNED_(need, sup, pv(1.0 / sc_))); lbg.append(0.0); ubg.append(0.0)
            # pools
            def pool_sum(s_):
                return sum(x[i] for i, f in enumerate(flows) if f[1] == s_)
            g_rows.append(fertDistMine_(pool_sum("MINE"), P, pv(1.0 / Pscale))); lbg.append(0.0); ubg.append(0.0)
            for s_ in pools:
                tot = pool_sum(s_)
                rhs = E if s_ == "EXCR" else C
                sc_ = max(sum(f[2] for f in flows if f[1] == s_), 1.0)
                if s_ == "EXCR":
                    self.excr_rows[nut] = (len(g_rows), sc_)
                if s_ == "CRES":
                    self.cres_rows = dict(getattr(self, "cres_rows", None) or {}, **{nut: (len(g_rows), sc_)})
                g_rows.append((fertDistExcr_ if s_ == "EXCR" else fertDistCres_)(tot, rhs, pv(1.0 / sc_)))
                lbg.append(0.0); ubg.append(0.0)
            # the regulations (e_fertDistPartialRegu, e_fertDistReguMax): a beta density on a group's flow with its
            # support (0, max per ha x the group's area) - the Green Deal's mineral caps by crop group ("f2f") and the
            # residue limits ("limCres")
            regs = {}
            regs_num = {}
            for (g_, s_), (mx, b1, b2) in (d.get("regs") or {}).items():
                gi_ = next((k for k, g2 in enumerate(G) if g2["g"] == g_), None)
                if gi_ is None:
                    continue
                Y = self._lin(y, [(j, float(mx) * float(sh)) for j, sh in G[gi_]["crops"]])
                regs[(gi_, s_)] = (Y, float(b1), float(b2))
                regs_num[(gi_, s_)] = [(int(j), float(mx) * float(sh)) for j, sh in G[gi_]["crops"]]
            # CAPRI's slack on the partial derivative of the prior density (v_fertDistPartialSlack, set_fert_priors.gms
            # l. 668-785; the Green Deal group's listed regions): free within +-bound t, here in units of the flow's
            # mode; e_fertDistPartial (partial + beta) (x + slack) = alpha - 1
            sl_ = d.get("partial_slack") or {}
            sl_i = [(i, float(sl_[(G[gi]["g"], s_)]) / m) for i, (gi, s_, m, acc) in enumerate(flows)
                    if float(sl_.get((G[gi]["g"], s_), 0.0) or 0.0) > 0]
            sig = ca.SX.sym(f"s{nut}", len(sl_i))
            sig_of = {i: sig[k] for k, (i, _) in enumerate(sl_i)}
            # first-order conditions of the inner model
            for i, (gi, s_, m, acc) in enumerate(flows):
                bm, a1 = gamma_prior(acc)                                  # normBeta (beta x mode), alpha - 1
                dual = e_focFertDist_dual(lam[gi], eF[s_], (mu[pools.index(s_)] if s_ in pools else 0))
                margin = float(_settings().get("fertiliser.support_margin"))
                if i in sig_of:
                    # the prior's part with the slack, the regulation's (e_fertDistPartialRegu) without it
                    Y_, b1_, b2_ = regs.get((gi, s_), (None, 1.0, 1.0))
                    term = e_focFertDist_term_slack(pv(a1), u[i], sig_of[i], pv(b1_ - 1.0), pv(bm), pv(m / T), dual)
                    if Y_ is not None:
                        term = e_fertDistPartialRegu_upper(term, pv(m * (b2_ - 1.0)), Y_, x[i])
                        g_rows.append(e_fertDistReguMax(x[i], Y_, margin, pv(1.0 / m))); lbg.append(-np.inf); ubg.append(0.0)
                elif (gi, s_) in regs:
                    Y, b1, b2 = regs[(gi, s_)]
                    term = e_fertDistPartialRegu_upper(e_focFertDist_term(pv(a1 + b1 - 1.0), u[i], pv(bm), pv(m / T), dual),
                                                       pv(m * (b2 - 1.0)), Y, x[i])
                    g_rows.append(e_fertDistReguMax(x[i], Y, margin, pv(1.0 / m))); lbg.append(-np.inf); ubg.append(0.0)
                else:
                    term = e_focFertDist_term(pv(a1), u[i], pv(bm), pv(m / T), dual)
                # DEPARTURE (K159, the project lead's decision of 15 November 2026): at a flow's lower bound the
                # first-order condition in the Fischer-Burmeister form (inner_fert.e_focFertDist_FB); CAPRI's equality
                # otherwise
                g_rows.append(e_focFertDist_FB(u[i], _u_lo, term, _fb_eps) if _fb_on else term)
                lbg.append(0.0); ubg.append(0.0)
            # CAPRI's mineral N cap per ha of land (minfert_redu_uaa.gms, e_synNMax): purchases <= cap x land
            if d.get("synNMax") is not None:
                self.synN_row = (len(g_rows), Pscale)
                g_rows.append(e_synNMax(P, pv(float(d["synNMax"])), land, pv(1.0 / Pscale))); lbg.append(-np.inf); ubg.append(0.0)
            # the purchases at their unit value (LINEAR_; equations/supply_model/objective.py)
            obj = obj + LINEAR_netPutQuant(P, pv(float(d["price"]) / 1000.0))
            if nut == "N" and getattr(self, "_fert_tech_pending", None) is not None:
                # the fertiliser options' cost on the N purchases (GHG_Mit_Cost_'s targFertSyn base: - cost x
                # v_netPutQuant(NITF) x (1 + sum (NMIN + EmiCalMin) v_Miti), kt; the factor is in the pending term, K175)
                obj = obj + GHG_Mit_Cost_targFertSyn(P, pv(1.0 / 1000.0), self._fert_tech_pending[0])
                self._fert_tech_pending = None
                self._fert_tech_P = True
            if nut == "N" and getattr(self, "_urea_pending", None) is not None:
                # the urea substitution's cost on the N purchases (GHG_Mit_Cost_'s UreaSubst base, l. 5063)
                from capri_mod.supply.equations.supply_model.mitigation import GHG_Mit_Cost_ureaSubst
                obj = obj + GHG_Mit_Cost_ureaSubst(P, pv(1.0 / 1000.0), self._urea_pending)
                self._urea_pending = None
            gt = self.spec.get("ghg_min") if nut == "N" else None
            if gt:
                # CAPRI's emission tax on the soil N2O of mineral N (N2OSYN, direct + volatilised x indirect), on the
                # purchases; with the nitrification inhibitor adopted, the accounts' factor on the share w of mineral N
                # under it: 1 - w + w (1 - lit) (1 + NMIN) (EnvironmentalModule.fert_side_factors)
                # (LINEAR_'s carbon tax on mineral fertiliser; equations/supply_model/objective.py)
                ef_dv = pv(float(gt["d"]) + float(gt["v"]))
                if gt.get("nitr") and self._nitr_phi is not None:
                    phi_, nm_ = self._nitr_phi
                    l2, l3 = gt["nitr"]
                    q_ = phi_ / (1.0 + nm_)
                    w_ = q_ / (q_ + 1.0 - phi_)
                    ef_d_nitr = pv(float(gt["d"]) * ((1.0 - l2) * (1.0 + nm_) - 1.0))
                    ef_v_nitr = pv(float(gt["v"]) * ((1.0 - l3) * (1.0 + nm_) - 1.0))
                    obj = obj + LINEAR_carbonTaxNITF(P, ef_dv, w_, ef_d_nitr, ef_v_nitr)
                else:
                    obj = obj + LINEAR_carbonTaxNITF(P, ef_dv)
                if float(gt.get("l", 0.0) or 0.0) > 0:
                    # the indirect N2O of the purchases' runoff and leaching (GWPN2OLEA_; SupplyModel._ef_mineral_lea)
                    obj = obj + LINEAR_carbonTaxN2OLEA(P, pv(float(gt["l"])))
            # the N-surplus rows in CAPRI's terms (SURTOT_REST_ with e_SURTOTHa: v_netPutQuant(NITF) + excretion +
            # fixation + deposition + residues - removal - net manure exports): the regional row with its mineral
            # parts replaced by the purchases
            if nut == "N":
                for lab_, mp in (npk.get("n_rows") or []):
                    i_ = self.labels.index(lab_)
                    Ai = self._A[i_] - np.asarray(mp, float)
                    rs = max(float(np.max(np.abs(Ai * self.sc))), 1.0)
                    self.n_rows_g = getattr(self, "n_rows_g", {})
                    self.n_rows_g[lab_] = (len(g_rows), rs)
                    nzA = [(j, float(Ai[j])) for j in np.nonzero(Ai)[0]]
                    _cn = (getattr(self, "catc_n", None) * pv(1.0 / rs)) if getattr(self, "catc_n", None) is not None else 0
                    # the catch crops' BioFix N is an input of the gross balance (e_BIOFIX)
                    ls_ = getattr(self, "_legsh", None)
                    if ls_ is not None:
                        # the legume share's fixation (e_BIOFIX, l. 1456-1457): OFAR's fixation, per technology x (1 +
                        # p_technFact(NITF, A)) (the mix column z: ydiff x z), x othImpact x v
                        _bf = y[ls_["col"]] + (pv(ls_["ydiff"]) * y[int(ls_["mix"])] if ls_.get("mix") is not None else 0)
                        _cn = _cn + e_BIOFIX_legSh(pv(ls_["fix"]) * _bf, pv(ls_["oi"]), ls_["v"]) * pv(1.0 / rs)
                    g_rows.append(SURTOT_REST_(self._lin(y, nzA, scale=rs), P, pv(1.0 / rs), _cn))
                    _add = float((npk.get("n_rows_rhs_add") or {}).get(lab_, 0.0))
                    lbg.append(-np.inf); ubg.append((float(self._b[i_]) + _add) / rs)
            vars_ = ca.vertcat(u, lam, mu, sig, Pv)
            o = nx0 + sum(int(v.shape[0]) for v in new)
            new.append(vars_)
            db = float(npk.get("dual_bound", 10.0))
            lbx += [_u_lo] * nfl + [-db * T] * (len(G) + len(pools)) + [-b_ for _, b_ in sl_i] + [0.0]
            ubx += [1e3] * nfl + [db * T] * (len(G) + len(pools)) + [b_ for _, b_ in sl_i] + [np.inf]
            self.fert[nut] = {"rows": (r_nut0, len(g_rows)), "flows": flows, "groups": [g_["g"] for g_ in G],
                              "pools": pools, "off": o, "nfl": nfl, "slack": [i for i, _ in sl_i],
                              "off_P": o + nfl + len(G) + len(pools) + len(sl_i), "Pscale": Pscale, "T": T,
                              "E": E, "C": C, "availE": availE, "price": float(d["price"]),
                              "regs": regs_num}
        self.fert_rows[1] = len(g_rows)
        self.fert_x0 = nx0
        X = ca.vertcat(X, *new)
        return X, obj

    def _netf_eff(self, d):
        """(mineral, residue) N efficiencies of NUTNED_ at the options' shares: CAPRI's GASTOTNETF_, RUNTOTNETF_ and
        GASRUNTOTNETF_ (supply_model.gms l. 3335-3394) with the mineral-N options' othImpact = 1 - (1 - lit)(1 + NMIN)
        on NH3SYN, NOXSYN, N2OSYN and NO3SRUN, winter cover's runoff reduction, the tillage options' othImpact on
        N2OSYN (- sum othImpact x share, l. 3392-3393) and the urea substitution's on NH3SYN (- v x othImpact,
        l. 3372-3377; initial share 0), written as the base efficiencies plus the change from the base
        point (the options at 0, winter cover and the tillage options at their base shares), so the base is exactly
        CAPRI's reported one: eff = eff0 - (GasRunTot(s) - GasRunTot(s0)), gc = gc0 (1 - N2O(s)) / (1 - N2O(s0)).
        None without the region's loss data or without options that move them. REGISTERED: CAPRI's reference run has
        no tillage term (its %ghgAbatement% off), its Green Deal step the term at the full shares; the model's base is
        CAPRI's reference and the term moves from the initial shares."""
        nf = d.get("netf")
        if not nf:
            return None
        from capri_mod.supply.equations.supply_model import n_flow as _nf
        from capri_mod.supply.equations.supply_model.nutrients import NUTNED_availFactMine_opt, NUTNED_availFactCRes_opt
        from capri_mod.supply.n_leaching import fert_effect          # ghgMiti.gms's othImpact, 1 - (1 - lit)(1 + NMIN)
        pv = self._pv
        syn = {"NH3": 0, "NOX": 0, "N2O": 0}; srun = 0; used = False
        for name, (ph, nm) in (self._fert_phi or {}).items():
            lit = (nf.get("lit") or {}).get(name) or {}
            for gas, item in (("NH3", "NH3SYN"), ("NOX", "NOXSYN"), ("N2O", "N2OSYN")):
                if item in lit:
                    syn[gas] = _nf.GASTOTNETF_fertSyn(syn[gas], pv(fert_effect(lit[item], nm)), ph); used = True
            if "NO3SRUN" in lit:
                srun = _nf.RUNTOTNETF_fertRun(srun, pv(fert_effect(lit["NO3SRUN"], nm)), ph); used = True
        m_wc, m0 = getattr(self, "_catc_m", None), float((self.spec.get("catc") or {}).get("m0", 0.0) or 0.0)
        if (self.spec.get("catc") or {}).get("fixmiti"):
            m_wc = None                       # the Green Deal group's fixed winter cover share: the cascade at base (K170)
        wr = float(nf.get("wc_red", 0.0))
        if m_wc is not None and wr > 0:
            used = True
        tn_ = getattr(self, "_till_n2o", None)
        ur_ = getattr(self, "_urea", None)
        if tn_ is not None or ur_ is not None:
            used = True
        if not used:
            return None
        fr, rsurf = nf["fr"], float(nf["run_surf"])
        L1 = _nf.netf(fr, rsurf, urea=(ur_[0] if ur_ is not None else 0.0), urea_eff=(ur_[1] if ur_ is not None else 0.0),
                      fert_syn=syn, till_n2o=(tn_[0] if tn_ is not None else 0.0),
                      m_run=_nf.RUNTOTNETF_cropFactor(wr, m_wc if m_wc is not None else m0, srun))
        L0 = _nf.netf(fr, rsurf, till_n2o=(float(tn_[1]) if tn_ is not None else 0.0),
                      m_run=_nf.RUNTOTNETF_cropFactor(wr, m0))
        # NUTNED_'s mineral and residue factors at the options' shares, from the base point (nutrients.py)
        effM = NUTNED_availFactMine_opt(pv(float(d["eff"])), L1["GasRunTot"], pv(float(L0["GasRunTot"])))
        effC = NUTNED_availFactCRes_opt(pv(float(d["gc"]) / (1.0 - float(L0["N2O"]))), L1["N2O"])
        self.netf_eff = (effM, effC)
        return effM, effC


    def fert_outputs(self, x):
        """{nutrient: {"purchase": t, "flows": {(group, source): t}, "availE": manure availability}}."""
        out = {}
        for nut, fb in (self.fert or {}).items():
            o = fb["off"]
            fl = {(fb["groups"][gi], s_): float(x[o + i]) * m for i, (gi, s_, m, acc) in enumerate(fb["flows"])}
            out[nut] = {"purchase": float(x[fb["off_P"]]) * fb["Pscale"], "flows": fl,
                        "availE": float(np.asarray(ca_eval(fb["availE"], self.X, x, self.p, self.pval)).ravel()[0])}
        return out


    def fert_at(self, x):
        """The fertilisation block solved nutrient by nutrient (its rows, its variables) at the values of x for every
        other variable: (x with the block's variables replaced, {nutrient: IPOPT status} of the blocks not solved)."""
        import casadi as ca
        x = np.asarray(x, float).copy()
        failed = {}
        for nut, fb in (self.fert or {}).items():
            r0, r1 = fb["rows"]
            o, o1 = fb["off"], fb["off_P"] + 1
            xf = ca.SX.sym("xf", o1 - o)
            Xs = ca.vertcat(ca.DM(x[:o]), xf, ca.DM(x[o1:]))
            gf = ca.Function("gf", [self.X, self.p], [self.g[r0:r1]])(Xs, ca.DM(self.pval))
            S = ca.nlpsol("C", "ipopt", {"x": xf, "f": 0, "g": gf},
                          {"ipopt.print_level": int(_settings().get("diagnostics.ipopt_print_level")), "print_time": 0,
                           "ipopt.tol": float(_settings().get("supply.nlp_fert_check_tol")),
                           "ipopt.max_iter": int(_settings().get("supply.nlp_max_iter")),
                           **linear_solver_options()})
            r = S(x0=x[o:o1], lbx=self.lbx[o:o1], ubx=self.ubx[o:o1], lbg=self.lbg[r0:r1], ubg=self.ubg[r0:r1])
            if not S.stats()["success"]:
                failed[nut] = S.stats()["return_status"]
                continue
            x[o:o1] = np.asarray(r["x"]).ravel()
        return x, failed
