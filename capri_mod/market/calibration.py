"""MarketModule: the base calibration of the market (base quantities and prices, the EU rows aligned to the supply models, demand calibration factors).

Part of capri_mod.market.market_module.MarketModule (a mixin); moved out of market_module.py on 24 October 2026
without changing the code. CAPRI references are in the methods' docstrings."""

import numpy as np
import pandas as pd
from scipy.optimize import fsolve  # noqa: F401
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple

from capri_mod.params import param, param_table
from capri_mod.settings import setting, current as _settings
from capri_mod.data.definitions import (
    MARKET_COMMODITIES, ALL_TRADE_REGIONS,
)
from capri_mod.data.definitions import MS_CODE
from capri_mod.market.equilibrium import MarketEquilibrium  # noqa: F401
from capri_mod.market.state import MarketStateMixin


class CalibrationMixin(MarketStateMixin):
    """MarketModule methods for the base calibration of the market (base quantities and prices, the EU rows aligned to the supply models, demand calibration factors)."""


    def _calibrate_baseline(self):
        """
        Base production and use of every market region and product from CAPRI's own market data (October 2026):

        - CAPRI's bilateral market of the market year (bilateral_flows/regions_<year>.csv, the EU as CAPRI's two market regions; the data of the
          bilateral market itself): production = the region's market production (PROD), use = domestic sales +
          imports;
        - products without bilateral trade (raw milk): CAPRI's FAO_agg world balance (world_market_baseline.csv;
          dairy_world_baseline.csv for the dairy products; capri_mod/data/nested_tables.py);
        - none of either: zero.

        The bilateral market calibrates every region to its closure at these tables (S7, CAPRI's calibration point). This replaced hard-coded world production totals (~2012) allocated
        with fixed regional shares, which were overwritten for every product with CAPRI data and only remained as
        fall-backs (retired: docs/archive/MARKET_STRUCTURE_PLAN.md step 3).
        """
        comms = self.commodities
        regions = self.regions
        self.par.base_production  = pd.DataFrame(0.0, index=regions, columns=comms)
        self.par.base_consumption = pd.DataFrame(0.0, index=regions, columns=comms)
        inp = self._inp()
        year = self._market_year()
        sfx = ""                                        # the market data, the EU as CAPRI's two blocks
        ff, fr = f"bilateral_flows_{year}{sfx}.csv", f"bilateral_regions_{year}{sfx}.csv"
        if not inp.exists(ff):
            by = inp.base_year                  # the base year's market where the market year has none (K52f)
            ff, fr = f"bilateral_flows_{by}{sfx}.csv", f"bilateral_regions_{by}{sfx}.csv"
        bil = set()
        if inp.exists(ff) and inp.exists(fr):
            fl = inp.csv(ff)
            rg = inp.csv(fr)
            fl = fl[fl.commodity.isin(comms) & fl.importer.isin(regions) & fl.exporter.isin(regions)]
            use = fl.groupby(["importer", "commodity"])["q_kt"].sum()
            for t in rg[rg.commodity.isin(comms) & rg.region.isin(regions)].itertuples(index=False):
                self.par.base_production.at[t.region, t.commodity] = float(t.prod_kt)
            for (r, c), q in use.items():
                self.par.base_consumption.at[r, c] = float(q)
            bil = set(fl.commodity.unique())
        # products without bilateral trade: CAPRI's FAO_agg balances (one EU region: EU27; blocks: split by CAPRI's
        # member-state production and use)
        bal = {}
        from capri_mod.data.nested_tables import read_balances
        for fn in ("world_market_baseline.csv", "dairy_world_baseline.csv"):      # required (a missing file stops the run)
            for k, v in read_balances(inp.need(fn)).items():
                bal.setdefault(k, v)
        self.par.capri_world_balance = {k: v for k, v in bal.items()}
        for c in comms:
            if c in bil:
                continue
            for r in regions:
                if r in self.EU:
                    rec = bal.get(f"EU27|{c}", {})
                    sp, su = self.eu_split(c, "prod_kt")[r], self.eu_split(c, "use_kt")[r]
                    p_, u_ = float(rec.get("production", 0.0) or 0.0) * sp, float(rec.get("consumption", 0.0) or 0.0) * su
                else:
                    rec = bal.get(f"{r}|{c}", {})
                    p_, u_ = float(rec.get("production", 0.0) or 0.0), float(rec.get("consumption", 0.0) or 0.0)
                self.par.base_production.at[r, c] = p_
                self.par.base_consumption.at[r, c] = u_ if u_ > 0 else p_

        # BIOFUELS: every region's base output and biofuel use from CAPRI's 2030 market results (FAO_agg holds
        # biofuel trade only); the bilateral market replaces the use by the flows' total use at calibration
        bm = self._biofuel_market_params()
        for fuel in self.BIOFUELS:
            if fuel not in comms or not bm:
                continue
            for region in regions:
                self.par.base_production.at[region, fuel] = float(bm["prod0"].get((region, fuel), 0.0))
                self.par.base_consumption.at[region, fuel] = float(bm["use0"].get((region, fuel), 0.0)
                                                               + bm["proc0"].get((region, fuel), 0.0))
        # DDGS: output from the ethanol plants' feedstocks (prodQuantBiofBy_), EU use CAPRI's EU feed use; the
        # bilateral market replaces the use by the flows' total use at calibration
        bp = self._biofuel_params()
        if "DDGS" in comms and bp:
            fb = self._feed_bulk_params()
            for region in regions:
                q = float(bp["ddgs0"].get(region, 0.0))
                self.par.base_production.at[region, "DDGS"] = q
                self.par.base_consumption.at[region, "DDGS"] = (float(fb.get("feed0_reg", {}).get(region, {}).get("DDGS", q))
                                                            if region in self.EU else q)
        # RESIDUAL FEEDS (CAPRI MaprFeed_, Sprint 9h): the EU's output and feed use of the 2030 reference; the other
        # regions' bases come from the bilateral market at calibration
        fp = self._feed_byproduct_params()
        if fp:
            fb = self._feed_bulk_params()
            for p, d in fp["products"].items():
                if p not in comms:
                    continue
                for reg in self.EU:
                    if reg not in regions:
                        continue
                    q0 = float(((d.get("reg") or {}).get(reg) or d)["prod0"])
                    self.par.base_production.at[reg, p] = q0
                    self.par.base_consumption.at[reg, p] = float(fb.get("feed0_reg", {}).get(reg, {}).get(p, q0))


    # ------------------------------------------------------------------
    # CAPRI's calibration point (S7)
    # ------------------------------------------------------------------
    # (Until 8 November 2026 the "supply" form set the EU's and Norway's base rows from the supply models' output,
    # _align_eu_base_balance and _align_sup_base, with the EU's use from CAPRI's member-state self-sufficiency; removed
    # with that form, register DEP-5.)

    def _capri_milk_point(self) -> None:
        """Raw milk at CAPRI's calibration point (S7): each country's marketed raw
        milk DATA(RMSSUP, "Prod", "MILK", "CAL") (market_prod_grof_2030.csv, prod_kt), as CAPRI's dairy block and
        market are calibrated (the supply models' milk enters each iteration in proportion, arm/simu_calibration_to_
        supply.gms l. 240-243). The EU blocks' raw milk production and use (CAPRI does not trade raw milk: delivered to
        the member state's own dairies), the dairy block's base delivery per member state and block; Norway's
        (and any non-EU market region with supply models) the same. Replaces the FAO base-period raw milk of
        _calibrate_baseline for these regions."""
        t = self._inp().csv("market_prod_grof_2030.csv")
        milk = {str(r["capri_ms"]): float(r["prod_kt"]) for _, r in t[t["product"] == "MILK"].iterrows()}
        eu_ms = {m: q for m, q in milk.items() if self.eu_region_of_ms(m) in self.EU}
        reg = {rg: 0.0 for rg in self.EU}
        for m, q in eu_ms.items():
            reg[self.eu_region_of_ms(m)] += q
        if "MILK" in self.par.base_production.columns:
            for rg, q in reg.items():
                self.par.base_production.at[rg, "MILK"] = q
                self.par.base_consumption.at[rg, "MILK"] = q
                if self.par.eu_aligned_use is None:
                    self.par.eu_aligned_use = {}
                self.par.eu_aligned_use.setdefault(rg, {})["MILK"] = q
        self.par.dairy_S0 = float(sum(reg.values()))
        self.par.dairy_S0_ms = dict(eu_ms)
        self.par.dairy_S0_reg = dict(reg)
        self.ev.eu_milk_supply_now = dict(reg)
        self.par.sup_milk0 = {}
        for rg in getattr(self, "SUP", ()):
            q = sum(milk.get(m, 0.0) for m in (getattr(self, "SUP_NONEU_MS", {}) or {}).get(rg, (rg,)))
            if q > 0 and rg in self.par.base_production.index and "MILK" in self.par.base_production.columns:
                self.par.sup_milk0[rg] = q
                self.par.base_production.at[rg, "MILK"] = q
                self.par.base_consumption.at[rg, "MILK"] = q
        self.ev.sup_milk_now = dict(self.par.sup_milk0)

    def _demand_cal_factor(self, comm: str) -> float:
        cal = self.par.demand_cal
        if cal is not None and comm in cal.index:
            return float(cal[comm])
        return 1.0
