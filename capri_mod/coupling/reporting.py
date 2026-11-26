"""Reports of a run: the welfare of the supply side, comparisons of runs, the reporter, the trace of the slowest regional solves.

CAPRIModel's methods, moved unchanged from capri_mod/model.py (the refactor's split into block mixins,
docs/dev/ARCHITECTURE_REFACTOR.md); the module-level names they use are model's, given to this
module once model is loaded (capri_mod.coupling.inject); the annotations are not evaluated.
"""
from __future__ import annotations
from capri_mod.coupling.equations.sol_simy import DATA_ProfitLandUse


class ReportingBlock:
    def _trace_nlp_regions(self, top=4):
        """Outer-loop trace of the NLP form: the regions whose activity levels moved most since the last outer
        iteration (max over the columns of |dy| / max(|y|, 1% of the region's largest column)), with the starts IPOPT
        used (warm / prev / start, then a relaxation) and its iterations, and the counts of each path."""
        import numpy as _np
        prev = getattr(self.sv, "trace_nlp_prev", None) or {}
        cur, rows, paths = {}, [], {}
        for r_, m_ in (self.supply_module._models or {}).items():
            y_ = getattr(m_.sv, "nlp_y", None)
            if y_ is None:
                continue
            cur[r_] = y_
            p_ = getattr(m_.res, "nlp_path", None) or ("?", 0)
            paths[p_[0]] = paths.get(p_[0], 0) + 1
            y0 = prev.get(r_)
            if y0 is not None and len(y0) == len(y_):
                # relative to the column's level, at least 1% of the region's largest column
                d_ = _np.abs(y_ - y0) / _np.maximum(_np.abs(y0), max(0.01 * float(_np.max(_np.abs(y0))), 1e-6))
                j_ = int(_np.argmax(d_))
                rows.append((float(d_[j_]), r_, j_, p_))
        self.sv.trace_nlp_prev = cur
        import time as _t
        _now = _t.time()
        _dt = _now - getattr(self.sv, "trace_nlp_t", _now)
        self.sv.trace_nlp_t = _now
        if not cur:
            return
        rows.sort(reverse=True)
        cols = lambda r_, j_: (list(getattr(self.supply_module._models[r_].sv, "nlp_cols", None) or [])[j_:j_ + 1] or [j_])[0]
        print(f"    [nlp] {_dt:.0f} s | paths " + ", ".join(f"{k} {v}" for k, v in sorted(paths.items()))
              + (" | moved " + "; ".join(f"{r_} {cols(r_, j_)} {d:.3f} ({p_[0]}, {p_[1]} it)" for d, r_, j_, p_ in rows[:top])
                 if rows else ""), flush=True)

    def _welfare_supply(self, supply_results) -> Optional[pd.DataFrame]:
        """The welfare components CAPRI takes from the supply models for the regions that have them (RMSSUP: the EU,
        Norway; reports/welfare.gms l. 416-467, 841-846), per supply-model region, EUR million (levels):
          MGVA      the region's income at the solution in CAPRI's form (income I1: SupplyResult.income, set by the
                    regional solve; IncomeDistributionModule.income_parts): the activities' MGVA x levels with the
                    solved ration, less the mitigation options' cost plus their revenue (CAPRI's AGGT, reports/
                    sol_simy.gms l. 2586, for its EAAG MGVA)
          RENT      the land rents: each land type's area x its rent at the solution, the dual of its land row
                    (EUR/ha; CAPRI's UAAR x d_area, reports/sol_simy.gms l. 181)
          ProfitAgr      the farms' profit, MGVA - RENT, and ProfitLandUse the land owners', RENT: CAPRI's accounts
                    with its land market (welfare.gms supremaMrk, l. 841-846), as in CAPRI's 2030 reference run (EU27:
                    MGVA 302,113 - rents 58,994 = ProfitAgr 243,119; capri_data/sources/raw/capri/results/
                    ref2030_welfare.parquet)
          PSEs      the budget's cost of the premiums, minus the premiums paid (CAPRI -FEOP, -FEOG of the products
                    without a market)
          mitiI, mitiO, mitiPmp  the mitigation options' accounting cost, revenue and PMP cost in CAPRI's report form
                    (reports/sol_simy.gms l. 1049-1465; mitiI and mitiO inside MGVA, mitiPmp apart)
          OBJE, PMPLevl, PMPFeed, PMPLandTrans, agProdSurplus  CAPRI's producer surplus rows of the region (income I3,
                    IncomeDistributionModule.producer_surplus; reports/sol_simy.gms l. 2578-2595): the supply model's
                    objective, its PMP terms and MGVA + the PMP terms; absent (NaN) where the solve recorded no parts
          TOOU, TOIN, EAAG_MGVA, EAAG_DIFF  the gross account by item's total output and input, its MGVA (TOOU - TOIN +
                    PRME) and its difference to MGVA (income I2, capri_mod/income/eaa.py; reports/sol_simy.gms l.
                    2557-2566, 2600-2615); the items are in results["eaa"]
        The market's agents' components are in results["market"].welfare. A failure here does not stop the run: it
        is warned and the table is None."""
        if not supply_results:
            return None
        try:
            from capri_mod.income.income_module import IncomeDistributionModule
            from capri_mod.market.equations.welfare import p_welfareRes_EAAG_ProfitAgr
            im = IncomeDistributionModule(self.data)
            rows = {}
            rlab = {"arable_land": "ARAC", "grassland": "GRAS", "permanent_land": "FRUN"}
            for reg, res in supply_results.items():
                ip = getattr(res, "income", None) or im.income_parts(reg, res, self.supply_module)
                sp = getattr(res, "shadow_prices", None) or {}
                lt = getattr(res, "land_types", None) or {}
                # EUR/ha x 1000 ha = EUR 1000
                rent = DATA_ProfitLandUse([float(sp.get(lab, 0.0)) for lab in rlab],
                                          [float(sp.get(lab + "_lo", 0.0)) for lab in rlab],
                                          [float(lt.get(t, 0.0)) for t in rlab.values()])
                rows[reg] = {"MGVA": ip["MGVA"] / 1000.0, "RENT": rent / 1000.0,
                             "ProfitAgr": p_welfareRes_EAAG_ProfitAgr(ip["MGVA"], rent) / 1000.0,
                             "ProfitLandUse": rent / 1000.0, "PSEs": -ip["PRME"] / 1000.0,
                             "mitiI": ip["mitiI"] / 1000.0, "mitiO": ip["mitiO"] / 1000.0,
                             "mitiPmp": ip["mitiPmp"] / 1000.0}
                for k_ in ("OBJE", "PMPLevl", "PMPFeed", "PMPLandTrans", "agProdSurplus"):
                    if k_ in ip:
                        rows[reg][k_] = float(ip[k_]) / 1000.0
                # the gross account by item's totals (income I2, SupplyResult.eaa, EUR million)
                ea = getattr(res, "eaa", None)
                if ea:
                    rows[reg].update({"TOOU": ea["TOOU"], "TOIN": ea["TOIN"], "EAAG_MGVA": ea["MGVA"],
                                      "EAAG_DIFF": ea["DIFF"]})
            return pd.DataFrame.from_dict(rows, orient="index")
        except Exception as exc:
            warnings.warn(f"welfare: the supply models' components could not be computed ({exc!r})")
            return None

    def compare(
        self,
        baseline_results: Dict,
        scenario_results: Dict,
        output_path: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Compare two scenario results, computing absolute and relative differences.

        Returns a DataFrame of key indicator changes.
        """
        diffs = {}

        # Market prices
        if baseline_results.get("market") and scenario_results.get("market"):
            b_prices = baseline_results["market"].world_prices
            s_prices = scenario_results["market"].world_prices
            from capri_mod.data.definitions import NO_WORLD_PRICE
            for comm in b_prices.index:
                if comm in NO_WORLD_PRICE:
                    continue                   # raw milk: no world price (K165)
                bp = b_prices.get(comm, np.nan)
                sp = s_prices.get(comm, np.nan)
                if bp and not np.isnan(bp) and bp > 0:
                    diffs[f"price_{comm}_pct"] = 100 * (sp - bp) / bp

        # EU farm income
        b_supply = baseline_results.get("supply", {})
        s_supply = scenario_results.get("supply", {})
        if b_supply and s_supply:
            b_income = sum(r.gross_margin for r in b_supply.values()) / 1e6
            s_income = sum(r.gross_margin for r in s_supply.values()) / 1e6
            diffs["farm_income_EUR_billion_change"] = s_income - b_income
            diffs["farm_income_pct_change"] = 100 * (s_income - b_income) / max(b_income, 1)

        # Welfare
        b_mkt = baseline_results.get("market")
        s_mkt = scenario_results.get("market")
        if b_mkt and s_mkt and hasattr(b_mkt, "welfare") and hasattr(s_mkt, "welfare"):
            # CAPRI's welfare (reports/welfare.gms), world totals: the market's agents (market/welfare.py) and, for
            # the regions with supply models, the farms' MGVA and the premiums' budget cost (_welfare_supply)
            tot = 0.0
            for comp in list(getattr(s_mkt.welfare, "columns", [])):
                if comp in b_mkt.welfare.columns and comp != "Welfare":
                    d_ = float(s_mkt.welfare[comp].sum() - b_mkt.welfare[comp].sum())
                    diffs[f"welfare_{comp}_EUR_million_change"] = d_
                    tot += d_
            b_ws, s_ws = baseline_results.get("welfare_supply"), scenario_results.get("welfare_supply")
            if b_ws is not None and s_ws is not None:
                for comp, lab in (("ProfitAgr", "ProfitAgr_supply_models"), ("ProfitLandUse", "ProfitLandUse"),
                                  ("PSEs", "PSEs")):
                    d_ = float(s_ws[comp].sum() - b_ws[comp].sum())
                    diffs[f"welfare_{lab}_EUR_million_change"] = d_
                    tot += d_
                diffs["welfare_EUR_million_change"] = tot

        # Environmental
        b_env = baseline_results.get("environmental")
        s_env = scenario_results.get("environmental")
        if b_env is not None and s_env is not None and not b_env.empty and not s_env.empty:
            for col in ["ghg_total", "n_surplus", "nh3_total"]:
                if col in b_env.columns and col in s_env.columns:
                    b_val = b_env[col].sum()
                    s_val = s_env[col].sum()
                    diffs[f"{col}_pct_change"] = 100 * (s_val - b_val) / max(b_val, 1)

        comparison = pd.Series(diffs, name=f"{baseline_results['scenario']} → {scenario_results['scenario']}")

        if self.verbose:
            print("\n=== Scenario Comparison ===")
            print(f"  {baseline_results['scenario']} → {scenario_results['scenario']}")
            for key, val in diffs.items():
                print(f"  {key:45s}: {val:+.2f}")
            print()

        if output_path:
            comparison.to_csv(output_path)
            print(f"Comparison saved to: {output_path}")

        return comparison

    def get_reporter(self, results: Dict) -> ResultsReporter:
        """Get a ResultsReporter for exporting results."""
        return ResultsReporter(results)
