r"""The regional NLP's pesticide block, CAPRI's pesticide module at its agg5 stage (setting supply.pest_disagg "agg5";
supply/supply_model.gms yldPestFac_ l. 4354-4385, pestiUse_ l. 4389-4398, pestiTot_ l. 4402-4408, SUPBAL_'s output
factor l. 4586-4594; capri_mod/supply/equations/supply_model/pesticides.py, pesti_test.py).

The variables: one per endogenous cell (crop c, technology T, aggregate i), a_cTi / ApplPerHa_cTi in [0, 10]
(set_supply_bounds.gms l. 180-189), started at 1 (prep_sim.gms l. 259-263; the solver's variable scaled by the
observed application, as GAMS's .scale: the applications span five orders of magnitude). The exogenous cells are
constants at ApplPerHa. The yield factor y_cT = yldPestFac_(NoDamageFac_cT, the cells) is an expression, not a
variable, bounded [0.1, 2] by a row where a cell of the crop-technology is endogenous (set_supply_bounds.gms
l. 204-212), as the port substitutes the other defined variables (v_netPutQuant).

The technology's level: x_T1 = X/2 + z, x_T2 = X/2 - z with the technology mix column z (capri_mod/supply/techn_mix.py),
X/2 each without one, X where the crop has one technology only.

The objective (minimised, the model's money): per crop-technology x_cT (-(R_cT) (y_cT - 1) + sum_i p_i a_cTi), with
R_cT the crop's market revenue per ha of the technology at this solve's prices (SUPBAL_'s output term through
v_netPutQuant: the revenue x (1 + (y - 1)); the fodder crops' output is in their balances, not here) and p_i the
aggregate's unit value (DATA(r, "UVAG", pestoAgg, "Y") over the money deflator; per kg per ha, as CAPRI's
objective: kg per ha x 1000 ha at UVAG is 1000 EUR, the unit of the levels' revenue).

The applications (setting supply.pest_applications): "exogenous", CAPRI's runs, every cell a constant at ApplPerHa x
the scenario's change factor (pol_input/cap_after_2023/ref.gms l. 21-23 fixes them, define_inputs.gms l. 117-136 moves
them; set_supply_bounds.gms l. 180-189); "endogenous", the variables above where no change factor is set.

The regional use per aggregate and its total as rows (pestiUse_, pestiTot_) with v_pestiQuantReg's bounds and the
quota QUTS of a scenario (set_supply_bounds.gms l. 192-198, define_inputs.gms l. 141-166).

PLAP stays in the crops' per-ha costs, where CAPRI takes it out of its inputs under the module (organic_io.gms
l. 69-71; register DEP-62): a constant of every
solve, which the calibration's linear terms absorb at the base; its scenario change is 0 under the module
(conventional_io.gms l. 132-133, supply/policy.py _apply_greendeal_input_changes).
"""
from __future__ import annotations

import numpy as np


class NLPPesticideBlock:
    """CapriRegionalNLP's pesticide block (_pest_block) and its start and outputs."""

    def _pest_terms(self, spec, y):
        """The applications' variables and per crop-technology its level, yield factor, applications and cost, built
        before the rows that carry the yield factor (pest_dev); _pest_block adds them to the problem."""
        self.pest, self._pest_pre = None, None
        ps = spec.get("pest")
        if not ps or not ps.get("crops"):
            return
        import casadi as ca
        from capri_mod.supply.equations.supply_model.pesticides import yldPestFac_
        endo = [(cr["act"], T, c["item"]) for cr in ps["crops"] for T, t in cr["techs"].items() for c in t["cells"]
                if c["endo"]]
        # the linear fall-back's form: "capri", CAPRI's smooth max (p_pestFudge); "epigraph", its damage share as a
        # variable D >= 1 - SlopLin a, D >= 0 (the max without the smoothing; the objective takes D to the max)
        epi = str(ps.get("linear_form", "capri")) == "epigraph"
        n_lin = sum(1 for cr in ps["crops"] for t in cr["techs"].values() for c in t["cells"]
                    if c["endo"] and not float(c["Expon"])) if epi else 0
        w = ca.SX.sym("pesti", len(endo) + n_lin)
        pv = self._pv
        from capri_mod.supply.equations.pesti_test import damage_share
        k, kd = 0, len(endo)
        epi_rows = []                                  # (D - (1 - SlopLin a)) >= 0
        terms, by_col = {}, {}
        for cr in ps["crops"]:
            Xc = y[int(cr["col"])]
            z = y[int(cr["mix"])] if cr.get("mix") is not None else None
            two = len(cr["techs"]) == 2
            for T, t in cr["techs"].items():
                if z is not None:
                    xT = 0.5 * Xc + (z if T == "T1" else -z)
                else:
                    xT = float(t["share"]) * Xc
                cells, cost, appl = [], 0, {}
                for c in t["cells"]:
                    if c["endo"]:
                        a = w[k] * pv(float(c["a0"]))
                        k += 1
                    else:
                        a = pv(float(c["a0"]))
                    # the power form at max(a, 0): IPOPT relaxes the bounds (bound_relax_factor 1e-8), and below 0 the
                    # power has no value (NaN); CONOPT keeps its bounds, so CAPRI never evaluates there
                    a_d = ca.fmax(a, 0) if float(c["Expon"]) else a
                    if epi and c["endo"] and not float(c["Expon"]):
                        D = w[kd]
                        kd += 1
                        epi_rows.append(D - (1.0 - pv(float(c["SlopLin"])) * a))
                    else:
                        D = damage_share(a_d, pv(float(c["SlopLin"])), pv(float(c["SlopExpo"])), float(c["Expon"]),
                                         sqrt=ca.sqrt)
                    cells.append((pv(float(c["maxDamage"])), D))
                    cost = cost + pv(float(c["price"])) * a
                    appl[c["item"]] = a
                # yldPestFac_ (pesti_test.yldPestFac_, its damage shares above): NoDamageFac - sum maxDamage x D
                yT = pv(float(t["NoDamageFac"])) - sum(md * D for md, D in cells)
                terms[(cr["act"], T)] = {"x": xT, "y": yT, "appl": appl, "cost": cost, "R": float(t["R"]),
                                         "endo": any(c["endo"] for c in t["cells"]),
                                         "sgn": ((0.5 if T == "T1" else -0.5) if two else 0.0)}
            by_col[int(cr["col"])] = cr["act"]
        self._pest_pre = {"w": w, "endo": endo, "terms": terms, "by_col": by_col, "epi_rows": epi_rows,
                          "n_lin": n_lin}

    def pest_dev(self, col, diff=0.0):
        """sum_T (1 + s_T diff) x_T (y_T - 1) of the crop of column col, or None: CAPRI's factor (1 + (v_yldPestFac -
        1)) on a term per ha of the technology, taken as the term's change; diff the place's T1 - T2 difference over
        the mean technology (techn_mix_2030.csv: yield_diff for the output, need_diff for NUTNED_), s_T +-1/2."""
        pp = getattr(self, "_pest_pre", None)
        if not pp or int(col) not in pp["by_col"]:
            return None
        a = pp["by_col"][int(col)]
        out = 0
        for (a_, T), t in pp["terms"].items():
            if a_ == a:
                out = out + (1.0 + t["sgn"] * float(diff)) * t["x"] * (t["y"] - 1.0)
        return out

    def _pest_block(self, spec, X, y, obj, g_rows, lbg, ubg, lbx, ubx):
        """The applications as variables, the yield factors' rows and the objective's two terms (above)."""
        pp = getattr(self, "_pest_pre", None)
        if not pp:
            return X, obj
        import casadi as ca
        from capri_mod.supply.equations.supply_model.pesticides import V_PESTIPERHA_BOUNDS, V_YLDPESTFAC_BOUNDS
        pv = self._pv
        nx0 = int(X.shape[0])
        out = {}
        for key, t in pp["terms"].items():
            obj = obj + t["x"] * (-pv(t["R"]) * (t["y"] - 1.0) + t["cost"])
            row = None
            if t["endo"]:
                row = len(g_rows)
                g_rows.append(t["y"]); lbg.append(V_YLDPESTFAC_BOUNDS[0]); ubg.append(V_YLDPESTFAC_BOUNDS[1])
            out[key] = {"x": t["x"], "y": t["y"], "appl": t["appl"], "row": row}
        for e_ in pp["epi_rows"]:
            g_rows.append(e_); lbg.append(0.0); ubg.append(np.inf)
        # CAPRI's emission tax on the residues' and fixation's N2O the yield factor moves (GWPN2OCRO_, GWPN2OLEA_ x
        # (1 + (v_yldPestFac - 1)); the objective's tax term, LINEAR_carbonTax_pestYield)
        from capri_mod.supply.equations.supply_model.objective import LINEAR_carbonTax_pestYield
        # (on every crop, 0 without the tax: the problem's structure is kept from solve to solve, its values parameters)
        for cr in spec["pest"]["crops"]:
            d_ = self.pest_dev(int(cr["col"]), float(cr.get("yield_diff", 0.0)))
            if d_ is not None:
                obj = obj + LINEAR_carbonTax_pestYield(pv(float(cr.get("ghg_y", 0.0) or 0.0)), d_)
        # CAPRI's regional use per aggregate and its total (pestiUse_, pestiTot_) as rows with v_pestiQuantReg's
        # bounds (set_supply_bounds.gms l. 192-198): [0, 10] x the aggregate's use at the base levels, the total at
        # most the quota where the scenario sets one (spec "quota", t)
        from capri_mod.supply.equations.supply_model.pesticides import pestiTot_, pestiUse_, v_pestiQuantReg_bounds
        items = sorted({i for t in pp["terms"].values() for i in t["appl"]})
        q0 = spec["pest"].get("use0") or {}
        uses = []
        for i in items:
            u = pestiUse_([(t["appl"][i], t["x"]) for t in pp["terms"].values() if i in t["appl"]])
            uses.append(u)
            if float(q0.get(i, 0.0) or 0.0) > 0:
                lo_, up_ = v_pestiQuantReg_bounds(float(q0[i]))
                g_rows.append(u); lbg.append(lo_); ubg.append(up_)
        if uses:
            lo_, up_ = v_pestiQuantReg_bounds(sum(float(v) for v in q0.values()), spec["pest"].get("quota"))
            g_rows.append(pestiTot_(uses)); lbg.append(lo_); ubg.append(up_)
        n = len(pp["endo"])
        X = ca.vertcat(X, pp["w"])
        lbx += [V_PESTIPERHA_BOUNDS[0]] * n + [0.0] * pp["n_lin"]
        ubx += [V_PESTIPERHA_BOUNDS[1]] * n + [np.inf] * pp["n_lin"]
        self.pest = {"off": nx0, "n": n, "endo": pp["endo"], "terms": out, "n_lin": pp["n_lin"]}
        return X, obj

    def pest_start(self, x):
        """x with the applications at the calibration point (their scaled value 1)."""
        p = getattr(self, "pest", None)
        if p and p["n"]:
            x[p["off"]:p["off"] + p["n"]] = 1.0
        if p and p.get("n_lin"):
            x[p["off"] + p["n"]:p["off"] + p["n"] + p["n_lin"]] = 0.0     # D at 1 - SlopLin ApplPerHa = 0
        return x

    def pest_outputs(self, x):
        """{(crop, technology): {"y": the yield factor, "appl": {aggregate: kg per ha}, "x": the level}} at x."""
        import casadi as ca
        p = getattr(self, "pest", None)
        if not p:
            return {}
        out = {}
        for key, t in p["terms"].items():
            exprs = [t["y"], t["x"]] + [t["appl"][i] for i in sorted(t["appl"])]
            f = ca.Function("pest", [self.X, self.p], [ca.vertcat(*[ca.SX(e) if not isinstance(e, ca.SX) else e
                                                                       for e in exprs])])
            v = np.asarray(f(x, self.pval)).ravel()
            out[key] = {"y": float(v[0]), "x": float(v[1]),
                        "appl": {i: float(v[2 + j]) for j, i in enumerate(sorted(t["appl"]))}}
        return out
