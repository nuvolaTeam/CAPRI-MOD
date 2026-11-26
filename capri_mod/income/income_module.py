"""Farm income by region, as CAPRI's reports compute it.

What it computes
----------------
For each region, agricultural income as CAPRI's reports compute it at the solution (reports/calc_inc_indic.gms, the
activity-based income AGGT of reports/sol_simy.gms l. 2586): the sum over activities of the modified gross value
added, MGVA = TOOU - TOIN + PRME, times the activity level, with the solved ration in the herds' inputs, the crops'
inputs at CAPRI's simulation-year coefficients (at the 2030 market year) and the mitigation options' cost an input and
their revenue an output (income I1, IncomeDistributionModule.income_parts):

    farm income     = sum_a MGVA_a x level_a - mitiI + mitiO   [EUR 1000]
    public support  = sum_a premium_a x level_a          (CAPRI's PRME: the premiums attached to the activities)
    market income   = farm income - public support

The supply models' results carry it (SupplyResult.income, set at each regional solve; SupplyResult.gross_margin is
its MGVA), and the welfare table reports it (coupling/reporting.py _welfare_supply). The policy module's CAP payments
(DirectPaymentsEngine, pillars 1 and 2) are reported beside the income (cap_payments_policy), not added to it: the
premiums are in the net revenues already (until 27 October 2026 they were counted twice).

Not yet CAPRI's: the product-based accounts (the EAA, reports/sol_simy.gms l. 2543-2570, with the fertiliser
purchases at the solution) and the activities' outputs and inputs item by item (income I2; the income inventory,
claude/income_inventory_2026-11-24.md).

Removed on 24 November 2026 (the project lead: follow CAPRI where a decision was pending): the distribution measures
across regions (the support share, income per hectare, a Gini coefficient of income and of payments, the top decile's
share). CAPRI's reports have no such measures; they were CAPRI-MOD's own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np
import pandas as pd


@dataclass
class IncomeResult:
    """Regional farm income."""

    by_region: pd.DataFrame          # region x {market_income, public_support, farm_income, cap_payments_policy}
    notes: Dict = field(default_factory=dict)


class IncomeDistributionModule:
    """Compute farm income by region (CAPRI's ProfitAgr form). The name is the module's since its start; the
    distribution measures it was named after were removed on 24 November 2026 (module docstring).

    Parameters
    ----------
    data : dict
        The model data dict.
    """

    def __init__(self, data: dict):
        self.data = data

    def income_parts(self, region, res, supply_module) -> dict:
        """A region's income at its solution in CAPRI's form (income I1; reports/calc_inc_indic.gms, sol_simy.gms
        l. 2586), EUR 1000 unless said:
          MGVA      CAPRI's activity-based income AGGT: sum over the activities of their MGVA at the solution x level
                    (coupling/equations/calc_inc_indic.py DATA_MGVA: the linear margin with the solved ration in place
                    of the feed it carries), with the technology mix's net revenue on the area moved to T1, less the
                    mitigation options' cost plus their revenue (coupling/equations/sol_simy.py DATA_AGGT_MGVA)
          PRME      the premiums x levels (CAPRI's PRME, with the technology mix's premium difference; mitiSubs is 0
                    in the model's runs, mitigation_items' module docstring)
          FEED      the solved ration at its report prices less the feed the margins carry (feed_term)
          mitiI, mitiO, mitiPmp, parts   the mitigation options' items (mitigation_items)
          MGVA_act  {activity: DATA_MGVA} per ha or head (EUR), the activities with a level
        Margins and premiums are per ha or per head in EUR; levels in 1000 ha or 1000 heads."""
        from capri_mod.coupling.equations.calc_inc_indic import DATA_MGVA
        from capri_mod.coupling.equations.sol_simy import DATA_AGGT_MGVA
        acts = getattr(res, "activities", None)
        m = getattr(supply_module, "_models", {}).get(region)
        if m is None or acts is None:
            raise ValueError(f"{region}: no solved supply model (run the supply module for the region first)")
        nr, pr = m.net_revenues, getattr(m, "premiums", None)
        if pr is None:
            raise ValueError(f"{region}: the supply model carries no premiums")
        lev = {a: float(acts.get(a, 0.0)) for a in nr.index}
        # CAPRI's crop technologies: the net revenue and premium of T1 less T2 on the area moved to T1 (z); the
        # premium difference is prem_diff_share x the crop's premium (supply/techn_mix.py)
        mz = dict(getattr(res, "technology_mix", None) or {})
        dnr = dict(getattr(getattr(m, "ev", None), "mix_dnr", None) or {})
        tm = getattr(getattr(m, "data", None), "techn_mix", None)
        prem_z = sum(float(tm.at[a, "prem_diff_share"]) * float(pr.get(a, 0.0)) * z
                     for a, z in mz.items() if tm is not None and a in tm.index)
        # the herds' feed at the solution (EUR 1000 per animal: the solved ration, the feed the margin carries)
        fd = self.feed_by_animal(res)
        # the crops' inputs at the simulation year's coefficients (CAPRI's TOIN at "Y") against the margins' base cost
        toin = self.crop_toin_y(region, m)
        mgva = {a: DATA_MGVA(float(nr[a]), fd[a][1] / lev[a], fd[a][0] / lev[a]) if a in fd else
                DATA_MGVA(float(nr[a]), 0.0, 0.0, *toin[a]) if a in toin else float(nr[a])
                for a in nr.index if lev[a] > 0}
        mi = self.mitigation_items(region, res, supply_module)
        return {"MGVA": DATA_AGGT_MGVA([v for _a, v in mgva.items()] + [float(dnr.get(a, 0.0)) for a in mz],
                                       [lev[a] for a in mgva] + [float(z) for z in mz.values()],
                                       mi["mitiI"], mi["mitiO"]),
                "PRME": float(sum(float(pr.get(a, 0.0)) * lev[a] for a in nr.index)) + prem_z,
                "FEED": float(sum(s_ - b_ for s_, b_ in fd.values())),
                "mitiI": mi["mitiI"], "mitiO": mi["mitiO"], "mitiPmp": mi["mitiPmp"], "parts": mi["parts"],
                "MGVA_act": mgva}

    @staticmethod
    def crop_toin_y(region, m) -> dict:
        """{crop: (the base cost per ha the margin carries, CAPRI's TOIN at the simulation year's coefficients)} (EUR per
        ha, the model's money; coupling/equations/calc_inc_indic.py DATA_TOIN_Y) for the crops of a regional model at
        the 2030 market year with CAPRI's year coefficients (input_coefs_2030.csv iy_uvag_eur_ha) and CAPRI's 2030
        nutrient need (capri_mod/fert/npk.py); empty elsewhere (at the base year CAPRI's "Y" is the base year's data,
        which the margins carry). The margin's base cost is the crop's input cost of the data (variable_costs.csv,
        CAPRI's 2017 TOIN at the regions' 2017 unit values), as supply_module._compute_net_revenues takes it."""
        from capri_mod.coupling.equations.calc_inc_indic import DATA_TOIN_Y
        from capri_mod.data.definitions import CROPS
        from capri_mod.fert.npk import NPKData, NUTRIENTS
        if getattr(getattr(m, "data", None), "input_coefs_2030", None) is None or not hasattr(m, "_input_row_2030"):
            return {}
        D = NPKData.get()
        cr = D.capri_region(region)
        if cr is None:
            return {}
        regs = {n: D.region(cr, n) for n in NUTRIENTS}
        if any(r_ is None for r_ in regs.values()):
            return {}
        uv = [float(regs[n].uvag_eur_t) if regs[n].uvag_eur_t == regs[n].uvag_eur_t else 0.0 for n in NUTRIENTS]
        tf = float(m._greendeal_tech_progress())
        vc = m.data.variable_costs
        out = {}
        for a in m.net_revenues.index:
            if a not in CROPS:
                continue
            iy = m._input_row_2030(a, "iy_uvag_eur_ha")
            c0 = vc.get(a) if hasattr(vc, "get") else None
            if iy is None or c0 is None or not np.isfinite(float(c0)):
                continue
            out[a] = (float(c0), DATA_TOIN_Y(iy, tf, [D.crop_coef(cr, n, a, "need_kg_ha") for n in NUTRIENTS], uv))
        return out

    def mitigation_items(self, region, res, supply_module) -> dict:
        """The mitigation options' items of a region's solution in CAPRI's report form (income I1;
        capri_mod/income/mitigation_items.py, reports/sol_simy.gms l. 1049-1465): {"mitiI", "mitiO", "mitiPmp"} in
        EUR 1000 and the blocks' parts. mitiI is the options' accounting cost (an input of TOIN), mitiO their revenue
        (an output of TOOU), mitiPmp their PMP cost (apart, not in MGVA; the blocks that keep CAPRI's PMP parameters
        only). The subsidy is 0 in the model's runs (mitigation_items' module docstring)."""
        from capri_mod.data.definitions import ANIMALS, TILLAGE_CROPS, capri_ms
        from capri_mod.income import mitigation_items as M
        from capri_mod.settings import current as _settings
        from capri_mod.supply import inputs as _inputs
        inp = _inputs.current()

        def rows_of(name, folder, key):
            def load(i):
                t = i.csv(name, folder)
                return {tuple(str(getattr(r, k_)).upper() if k_ == "option" else getattr(r, k_) for k_ in key): r
                        for r in t.itertuples(index=False)}
            return inp.cached(f"income_rows_{name}", load)

        m = getattr(supply_module, "_models", {}).get(region)
        acts = getattr(res, "activities", None)
        lev = {a: float(acts.get(a, 0.0) or 0.0) for a in (acts.index if acts is not None else [])}
        npk = getattr(res, "fert_npk", None) or {}
        nN = npk.get("N") or {}
        n_bought = float(nN.get("purchase", 0.0) or 0.0)
        n_manure = sum(float(v or 0.0) for (_g, src), v in (nN.get("flows") or {}).items() if src == "EXCR")
        shares = dict(getattr(res, "fert_tech_shares", None) or {})
        fert_rows = rows_of("fert_options_jul15.csv", "abatement", ("region", "option"))
        parts = {
            "fert": M.fert_options_items(region, shares, getattr(res, "fert_nmin", None) or {}, n_bought, fert_rows),
            "mni": M.manure_inhibitor_items(region, shares.get("NITR_INH_MAN"),
                                            ((getattr(getattr(m, "ev", None), "nlp_nip", None) or {}).get("nman")),
                                            n_manure, fert_rows),
            "amm": M.ammonia_items(getattr(res, "amm_subs", None) or {}, lev),
            "catc": M.winter_cover_items(getattr(res, "cover_crops", None) or {},
                                         rows_of("winter_cover_option.csv", "abatement/mitigation",
                                                 ("region",)).get((region,))),
            "till": M.tillage_items(getattr(res, "till_shares", None) or {},
                                    sum(lev.get(c, 0.0) for c in TILLAGE_CROPS),
                                    {str(t_): r_ for (r_reg, t_), r_ in rows_of(
                                        "tillage_options.csv", "abatement/mitigation",
                                        ("region", "technology")).items() if r_reg == region}),
            "legsh": M.legume_share_items(getattr(res, "legsh_share", None), lev.get("OFAR", 0.0),
                                          rows_of("legsh_option.csv", "abatement/mitigation",
                                                  ("region",)).get((region,))),
            "urea": M.urea_substitution_items(getattr(res, "urea_share", None), n_bought,
                                              {a: x for a, x in lev.items() if a not in ANIMALS and x > 0},
                                              rows_of("urea_subst_option.csv", "abatement/mitigation",
                                                      ("ms",)).get((capri_ms(region),)),
                                              form=str(_settings().get("income.urea_cost_base"))),
            "hist": M.histosol_fallow_items(getattr(res, "histosol_fallow", None) or {}),
            "herd": M.herd_option_items(getattr(res, "genetics_shift", None) or {},
                                        {k: (v.to_dict() if hasattr(v, "to_dict") else dict(v)) for k, v in
                                         (getattr(getattr(m, "data", None), "genetics_effects", None) or {}).items()}),
        }
        out = {k: sum(float(p_.get(k, 0.0) or 0.0) for p_ in parts.values()) for k in ("mitiI", "mitiO", "mitiPmp")}
        out["parts"] = {b_: {k: float(v) for k, v in p_.items() if k in ("mitiI", "mitiO", "mitiPmp")}
                        for b_, p_ in parts.items()}
        return out

    @staticmethod
    def feed_by_animal(res, ref_fodder_duals=None) -> dict:
        """The herds' feed in CAPRI's TOIN at the solution against the feed their margins carry (income I1; income
        inventory 8.3), EUR 1000 per animal whose feeding is in the regional model: (the solved ration at its report
        prices, the feed value per head the herd's linear term leaves out x the level). The solved ration is
        SupplyResult.feed_t x feed_price: the tradable feeds at the solve's prices, the fodder at the ration's value;
        the feed per head left out is feed_lin, the input cost table's FEED (register DEP-13 step 3). CAPRI's report
        takes the feed per head of the solution (reports/sol_simy.gms l. 254-257, DATA_FEED_SIMY) at the simulation's
        UVAG (calc_inc_indic.gms l. 34-38).

        With ref_fodder_duals (the baseline's fodder balances' duals, {"fodder_<feed>": EUR/t}), the fed fodder takes
        CAPRI's UVAG(fodder, SIM): FODDMARKUP = UVAG(BAS run) - PSHW(BAS run) x (1 - p_onFarmShare), UVAG(FODDO, SIM)
        = PSHW(SIM) x (1 - p_onFarmShare) + FODDMARKUP and the fed fodder's UVAG(FODDO, SIM) / (1 - p_onFarmShare)
        (sol_simy.gms l. 740-757), so per t fed the reference's value plus PSHW(SIM) - PSHW(reference) where the dual
        is per t fed (CAPRI's note at l. 737). The reference's value is the ration's (fodder_value_2030.csv). The
        region's income leaves that change out (income_parts): the fodder crops' output takes the same UVAG(FODDO,
        SIM), so in the region's total it is an internal flow that cancels."""
        lin = getattr(res, "feed_lin", None) or {}
        ft, fp = getattr(res, "feed_t", None) or {}, getattr(res, "feed_price", None) or {}
        acts = getattr(res, "activities", None)
        dual = getattr(res, "fodder_duals", None) or {}

        def price(a, f):
            p = float((fp.get(a) or {}).get(f, 0.0))
            k = f"fodder_{f}"
            if ref_fodder_duals and k in ref_fodder_duals and k in dual:
                p += (float(dual[k]) - float(ref_fodder_duals[k])) / 1000.0      # EUR/t -> EUR/kg
            return p
        return {a: (sum(float(t) * price(a, f) for f, t in (ft.get(a) or {}).items()),
                    float(v) * float(acts.get(a, 0.0) if acts is not None else 0.0)) for a, v in lin.items()}

    @staticmethod
    def feed_term(res, ref_fodder_duals=None) -> float:
        """The herds' feed at the solution less the feed their margins carry, summed over the animals (EUR 1000;
        feed_by_animal)."""
        return float(sum(s_ - b_ for s_, b_ in
                         IncomeDistributionModule.feed_by_animal(res, ref_fodder_duals).values()))

    def compute(self,
                supply_results: Dict,
                supply_module,
                cap_payments_by_region: Optional[pd.DataFrame] = None) -> IncomeResult:
        """Regional farm income (income_parts: CAPRI's activity-based income at the solution).

        Parameters
        ----------
        supply_results : dict[region -> SupplyResult]
            Each carries ``activities`` (solved levels) and, from the regional solve, ``income`` (income_parts).
        supply_module : SupplyModule
            The module that solved them: its regional models carry the net revenues and premiums per activity.
        cap_payments_by_region : DataFrame, optional
            ``DirectPaymentsEngine.compute_payments_by_region``: its ``total_payments`` (EUR 1000) are reported beside
            the income for comparison (cap_payments_policy), not added to it.
        """
        rows = []
        for region, res in supply_results.items():
            ip = getattr(res, "income", None) or self.income_parts(region, res, supply_module)
            income, support = ip["MGVA"], ip["PRME"]
            pol = (float(cap_payments_by_region.at[region, "total_payments"])
                   if cap_payments_by_region is not None and region in cap_payments_by_region.index else np.nan)
            rows.append({
                "region": region,
                "market_income": income - support,
                "public_support": support,
                "farm_income": income,
                "cap_payments_policy": pol,
            })
        df = pd.DataFrame(rows).set_index("region")
        return IncomeResult(by_region=df, notes={"n_regions": int(len(df))})
