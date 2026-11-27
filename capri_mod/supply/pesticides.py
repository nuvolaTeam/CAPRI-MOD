"""CAPRI's pesticide module in the regional model (setting supply.pest_disagg "agg5"): the regional NLP's pesticide spec
from the region's calibrated cells (RegionData.pesticides, pesticide_par_2030.csv) at this solve's revenues
(capri_mod/supply/regional_nlp/pesticides.py builds the block).

RegionalSupplyModel's methods (the block-mixin pattern).
"""
from __future__ import annotations

import numpy as np

from capri_mod.data import inputs as _inputs

#: CAPRI's two crop technologies (p_technFact LEVL): T1 high yield, T2 low yield (techn_mix.py)
TECHS = ("T1", "T2")


class PesticideBlock:
    def _nlp_pest_spec(self, A, labels) -> dict | None:
        """{"crops": [{act, col, mix, techs: {T: {share, R, NoDamageFac, cells: [...]}}}]} for the regional NLP, or None
        without the module. Per crop of the region with a base level and calibrated cells: its column, its technology
        mix column, and per technology the level's share (without a mix column), the value per ha of the output the
        yield factor moves R (SUPBAL_'s output, sold: CAPRI's NoDamageYld of the technology, its outputs x unit value x
        (1 + technology factor) x (1 - p_onFarmShare), over the deflator, moved by this solve's change of the crop's
        price; 0 for the fodder crops, whose output is in their balances), NoDamageFac, and the cells: aggregate, ApplPerHa,
        maxDamage, the terms, endogenous, the unit value in the model's money (DATA(UVAG) / deflator; per kg of
        v_pestiPerHa, as CAPRI's farmerObje_ and SUPBAL_: kg per ha x 1000 ha at UVAG, 1000 EUR)."""
        P = getattr(self.data, "pesticides", None)
        if not P:
            return None
        cells, ndf = P["cells"], P["no_damage_fac"]
        acts = list(self.acts)
        base = self._base_levels()
        mixc = dict(getattr(self.ev, "mix_cols", None) or {})
        tm = getattr(self.data, "techn_mix", None)
        defl = float(_inputs.money_deflator(int(self.data.sim_year)))
        ndy = P.get("no_damage_yld") or {}
        ps = getattr(self.ev, "price_shock_now", None)
        fod_rows = [i for i, l in enumerate(labels) if l.startswith("fodder_")]
        from capri_mod.settings import current as _settings_
        # CAPRI's applications: a scenario's change factor (define_inputs.gms l. 131-132) on every cell; with it, or
        # with the reference's fix (setting supply.pest_applications "exogenous", CAPRI's runs), a cell is exogenous at
        # that level (set_supply_bounds.gms l. 180-189); endogenous only where neither holds
        cf = float(getattr(self.ev, "pest_change_factor", None) or 1.0)
        endo_ok = str(_settings_().get("supply.pest_applications")) == "endogenous" and cf == 1.0
        # a quota on the region's total (DATA(RU, "QUTS", "pesTotal")): QUTS = factor x GROF, GROF the use at the base
        # levels; the exogenous cells scaled by QUTS / GROF (define_inputs.gms l. 141-166)
        qf = float(getattr(self.ev, "pest_quota_factor", None) or 0.0)
        qscale = 1.0
        crops = []
        for a in sorted(set(cells.index.get_level_values("activity"))):
            if a not in acts or not float(base.get(a, 0.0) or 0.0) > 1e-6:
                continue
            j = acts.index(a)
            ca_ = cells.xs(a, level="activity")
            techs = [T for T in TECHS if T in set(ca_.index.get_level_values("technology"))]
            if not techs:
                continue
            fodder = any(A[i, j] != 0.0 for i in fod_rows)
            # the price's change of this solve (the crops' unit values, _compute_net_revenues)
            pf = 1.0 + (float(ps.get(a, 0.0) or 0.0) if ps is not None and hasattr(ps, "get") else 0.0)
            k = mixc.get(a)
            td = {}
            for T in techs:
                ct = ca_.xs(T, level="technology")
                if not ndf.get((a, T)):
                    continue
                cl = [dict(item=i, a0=float(r.appl_per_ha) * cf, maxDamage=float(r.max_damage),
                           SlopLin=float(r.slop_lin), SlopExpo=float(r.slop_expo), Expon=float(r.expon),
                           endo=bool(r.endogenous > 0) and endo_ok, endo_flag=bool(r.endogenous > 0),
                           price=float(r.uvag) / defl)
                      for i, r in ct.iterrows() if float(r.appl_per_ha) > 0.0]
                if not cl:
                    continue
                R = 0.0 if fodder else float(ndy.get((a, T), 0.0)) / defl * pf
                td[T] = dict(share=(1.0 / len(techs)), R=R, NoDamageFac=float(ndf[(a, T)]), cells=cl)
            if td:
                two = len(td) == 2 and tm is not None and a in tm.index
                crops.append(dict(act=a, col=j, mix=(int(k) if k is not None and len(techs) == 2 else None),
                                  techs=td, fodder=fodder,
                                  # the T1 - T2 differences of the places the yield factor enters (techn_mix_2030.csv)
                                  yield_diff=float(tm.loc[a, "yield_diff"]) if two else 0.0,
                                  need_diff=float(tm.loc[a, "need_diff"]) if two else 0.0,
                                  res_diff={"N": float(tm.loc[a, "mann_diff"]) if two else 0.0,
                                            "P": float(tm.loc[a, "manp_diff"]) if two else 0.0,
                                            "K": float(tm.loc[a, "mank_diff"]) if two else 0.0},
                                  # the residues' share that follows the yield: N (MANN - AtmDep) / MANN, which the mix's
                                  # MANN factor carries (0.4 x that share, techn_mix_2030.csv); without the mix not known
                                  # here (None: the term left out, counted in the block's outputs)
                                  res_share={"N": (float(tm.loc[a, "mann_diff"]) / float(tm.loc[a, "yield_diff"])
                                                   if two and float(tm.loc[a, "yield_diff"]) else None),
                                             "P": 1.0, "K": 1.0},
                                  # CAPRI's emission tax on the yield factor's change of the residues' and fixation's
                                  # N2O (GWPN2OCRO_, GWPN2OLEA_), EUR per ha and unit of (y - 1) at the baseline's
                                  # coefficient (ghg_tax.pest_yield_coefficients); 0 without the tax
                                  ghg_y=float(self._ghg_cost("pest", a))))
        from capri_mod.settings import current as _settings
        quota = None
        if crops and qf > 0:
            quota = self._pest_quota(crops, base, qf)
        # each aggregate's use at the base levels and the applications' level of this solve (v_pestiQuantReg.l,
        # prep_sim.gms l. 266-268), the base of its bounds
        use0 = {}
        for cr in crops:
            X = float(base.get(cr["act"], 0.0) or 0.0)
            for t in cr["techs"].values():
                w_ = 0.5 if len(cr["techs"]) == 2 else float(t["share"])
                for c in t["cells"]:
                    use0[c["item"]] = use0.get(c["item"], 0.0) + c["a0"] * X * w_
        return {"crops": crops, "linear_form": str(_settings().get("supply.pest_linear_form")), "quota": quota,
                "change_factor": cf, "use0": use0} if crops else None

    def _pest_quota(self, crops, base, qf) -> float:
        """CAPRI's quota on the region's total pesticide use, t (define_inputs.gms l. 141-166): QUTS = qf x GROF, GROF
        the cells' use at the base levels (the technologies at half the level each, z = 0 at the base, or their share);
        the exogenous cells (not endogenous in the calibration, p_pestPar "endogenous") scaled by QUTS / GROF in place
        (DATA(RU, mCact, pestoAgg, "Y") x QUTS / GROF), as CAPRI's l. 164-166."""
        from capri_mod.supply.equations.define_inputs import DATA_QUTS_pesTotal
        grof = 0.0
        for cr in crops:
            X = float(base.get(cr["act"], 0.0) or 0.0)
            for t in cr["techs"].values():
                grof += sum(c["a0"] for c in t["cells"]) * X * (0.5 if len(cr["techs"]) == 2 else float(t["share"]))
        quts = DATA_QUTS_pesTotal(grof, qf)
        if grof > 0:
            for cr in crops:
                for t in cr["techs"].values():
                    for c in t["cells"]:
                        if not c["endo_flag"]:
                            c["a0"] = c["a0"] * quts / grof
        return quts

    def _n_row_pest_parts(self) -> dict:
        """{column: (res, rem, fix)} of the crops, t N per unit at the mean technology and this solve's yields: the
        residues (DATA(MANN) less the deposition), the removal (DATA(NITF)) and the fixation, the N_balance row's own
        unit balances (the environmental accounts' n_crop_residues, n_crop_uptake, n_fixation; as
        fertilisation.py _n_row_mineral_parts), for the yield factor's terms in the N surplus (SURTOT_pestTerms)."""
        env_ = getattr(self.seen, "env_for_surplus", None)
        if env_ is None:
            return {}
        from capri_mod.data.definitions import CROPS
        rid, ycur = self.data.region_id, self.data.yields
        mint = dict(getattr(self.ev, "n_intensity", {}) or {})
        out = {}
        for j, a in enumerate(self.acts):
            if a not in CROPS:
                continue
            mi = {k_: v_ for k_, v_ in mint.items() if k_ in (a, "__credit__")}
            u = env_.unit_nitrogen_balance(a, ycur, rid, mi, yields_scen=self._yields_scen_now())
            out[j] = (float(u.get("n_crop_residues", 0.0)), float(u.get("n_crop_uptake", 0.0)),
                      float(u.get("n_fixation", 0.0)))
        return out

    def _insolve_factors(self, activities) -> dict:
        """{crop: (tf, ned)}: the crop's in-solve yield factors at this solution, CAPRI's per-technology factors summed
        over its technologies (insolve_yield_factors): tf the change of the output (SUPBAL_: x (1 + p_technFact(yield,
        A)) x (1 + (v_yldPestFac - 1))), ned the need's factor (NUTNED_: x (1 + need's technology term) x (1 +
        (v_yldPestFac - 1))), over the level; the technology mix (z, techn_mix_2030.csv yield_diff, need_diff) and the
        pesticide module's yield factors (res.last_pest). Crops with neither: not listed."""
        from capri_mod.supply.equations.supply_model.pesticides import insolve_yield_factors
        tm = getattr(self.data, "techn_mix", None)
        mz = dict(getattr(self.res, "last_mix_z", None) or {})
        lp = dict(getattr(self.res, "last_pest", None) or {})
        out = {}
        for a in sorted(set(mz) | {k[0] for k in lp}):
            X = float(activities.get(a, 0.0) or 0.0)
            if not X > 1e-9:
                continue
            two = tm is not None and a in tm.index and (a in mz or ((a, "T1") in lp and (a, "T2") in lp))
            yd = float(tm.at[a, "yield_diff"]) if two else 0.0
            nd = float(tm.at[a, "need_diff"]) if two else 0.0
            z = float(mz.get(a, 0.0))
            if two:
                xs = {"T1": X / 2.0 + z, "T2": X / 2.0 - z}
            else:
                xs = {k[1]: X for k in lp if k[0] == a} or {"T": X}
            ys = {T: float(lp[(a, T)]["y"]) if (a, T) in lp else 1.0 for T in xs}
            out[a] = insolve_yield_factors(X, xs, ys, yd, nd)
        return out
