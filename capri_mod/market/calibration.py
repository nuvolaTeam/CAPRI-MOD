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

        - CAPRI's bilateral market of the market year (bilateral_flows/regions_<year>[_eu2].csv, the data of the
          bilateral market itself): production = the region's market production (PROD), use = domestic sales +
          imports;
        - products without bilateral trade (raw milk): CAPRI's FAO_agg world balance (world_market_baseline.json;
          dairy_world_baseline.json for the dairy products);
        - none of either: zero.

        The EU's rows are then set from the supply models (_align_eu_base_balance) and the bilateral market
        calibrates every region to its closure. This replaced hard-coded world production totals (~2012) allocated
        with fixed regional shares, which were overwritten for every product with CAPRI data and only remained as
        fall-backs (retired: docs/archive/MARKET_STRUCTURE_PLAN.md step 3).
        """
        comms = self.commodities
        regions = self.regions
        self.base_production  = pd.DataFrame(0.0, index=regions, columns=comms)
        self.base_consumption = pd.DataFrame(0.0, index=regions, columns=comms)
        self._base_net_exports_eu = {}
        inp = self._inp()
        year = int(self.data.get("market_year", 2017) or 2017) if isinstance(self.data, dict) else 2017
        sfx = "_eu2" if self.eu_blocks else ""
        ff, fr = f"bilateral_flows_{year}{sfx}.csv", f"bilateral_regions_{year}{sfx}.csv"
        if not inp.exists(ff):
            ff, fr = f"bilateral_flows_2017{sfx}.csv", f"bilateral_regions_2017{sfx}.csv"
        bil = set()
        if inp.exists(ff) and inp.exists(fr):
            fl = inp.csv(ff)
            rg = inp.csv(fr)
            fl = fl[fl.commodity.isin(comms) & fl.importer.isin(regions) & fl.exporter.isin(regions)]
            use = fl.groupby(["importer", "commodity"])["q_kt"].sum()
            ext = fl[fl.importer != fl.exporter]
            exp_ = ext.groupby(["exporter", "commodity"])["q_kt"].sum()
            imp_ = ext.groupby(["importer", "commodity"])["q_kt"].sum()
            for t in rg[rg.commodity.isin(comms) & rg.region.isin(regions)].itertuples(index=False):
                self.base_production.at[t.region, t.commodity] = float(t.prod_kt)
            for (r, c), q in use.items():
                self.base_consumption.at[r, c] = float(q)
            bil = set(fl.commodity.unique())
            for r in self.EU:
                for c in bil:
                    self._base_net_exports_eu.setdefault(r, {})[c] = float(exp_.get((r, c), 0.0) - imp_.get((r, c), 0.0))
        # products without bilateral trade: CAPRI's FAO_agg balances (one EU region: EU27; blocks: split by CAPRI's
        # member-state production and use)
        bal = {}
        for fn in ("world_market_baseline.json", "dairy_world_baseline.json"):
            if inp.exists(fn):
                for k, v in inp.json(fn)["balances"].items():
                    bal.setdefault(k, v)
        self._capri_world_balance = {k: v for k, v in bal.items()}
        for c in comms:
            if c in bil:
                continue
            for r in regions:
                if r in self.EU and self.eu_blocks:
                    rec = bal.get(f"EU27|{c}", {})
                    sp, su = self.eu_split(c, "prod_kt")[r], self.eu_split(c, "use_kt")[r]
                    p_, u_ = float(rec.get("production", 0.0) or 0.0) * sp, float(rec.get("consumption", 0.0) or 0.0) * su
                else:
                    rec = bal.get(f"{r}|{c}", {})
                    p_, u_ = float(rec.get("production", 0.0) or 0.0), float(rec.get("consumption", 0.0) or 0.0)
                self.base_production.at[r, c] = p_
                self.base_consumption.at[r, c] = u_ if u_ > 0 else p_
                if r in self.EU:
                    self._base_net_exports_eu.setdefault(r, {})[c] = p_ - (u_ if u_ > 0 else p_)

        # BIOFUELS: every region's base output and biofuel use from CAPRI's 2030 market results (FAO_agg holds
        # biofuel trade only); the bilateral market replaces the use by the flows' total use at calibration
        bm = self._biofuel_market_params()
        for fuel in self.BIOFUELS:
            if fuel not in comms or not bm:
                continue
            for region in regions:
                self.base_production.at[region, fuel] = float(bm["prod0"].get((region, fuel), 0.0))
                self.base_consumption.at[region, fuel] = float(bm["use0"].get((region, fuel), 0.0)
                                                               + bm["proc0"].get((region, fuel), 0.0))
        # DDGS: output from the ethanol plants' feedstocks (prodQuantBiofBy_), EU use CAPRI's EU feed use; the
        # bilateral market replaces the use by the flows' total use at calibration
        bp = self._biofuel_params()
        if "DDGS" in comms and bp:
            fb = self._feed_bulk_params()
            for region in regions:
                q = float(bp["ddgs0"].get(region, 0.0))
                self.base_production.at[region, "DDGS"] = q
                self.base_consumption.at[region, "DDGS"] = (float(fb.get("feed0_reg", {}).get(region, {}).get("DDGS", q))
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
                    self.base_production.at[reg, p] = q0
                    self.base_consumption.at[reg, p] = float(fb.get("feed0_reg", {}).get(reg, {}).get(p, q0))


    # ------------------------------------------------------------------
    # A consistent EU base balance
    # ------------------------------------------------------------------
    #: The EU used to be left out of the real-FAO production override, because
    #: its supply comes from the supply module at solve time. Left out, it became
    #: the RESIDUAL of a hard-coded world total minus every region with real data:
    #: wheat 55.9 Mt against a real ~139, maize 169.0 against ~73. Consumption,
    #: derived as production minus (correct) net exports, inherited the error -
    #: wheat 28.1 Mt against a real 108.9 - and a single world calibration factor
    #: then spread the inconsistency across every region. Every EU price ratio in
    #: the Armington premium was computed on that.
    #:
    #: Now: EU production is the model's own base output, so the market, the
    #: premium and the solve see one EU; EU consumption keeps FAO's own EU
    #: consumption-to-production ratio, which comes from one source with one set
    #: of definitions, so it is the EU's real self-sufficiency even where levels
    #: differ; and the world balance closes over the OTHER regions.
    def _fao_eu_rows(self) -> dict:
        rows = getattr(self, "_fao_eu_cache", None)
        if rows is not None:
            return rows
        rows = {}
        # CAPRI's own EU balance (FAO_agg, member states summed: production MAPR, domestic use DOMM). The FAO
        # extract (fao_market_baseline.json) was read first as a fallback; CAPRI's balance covers every EU
        # commodity it had, so the fallback was inert and was removed (20 October 2026, KNOWN_ISSUES K54-6)
        for key, rec in (getattr(self, "_capri_world_balance", None) or {}).items():
            r, c = key.split("|")
            if r == "EU27" and float(rec.get("production", 0) or 0) > 0 and float(rec.get("consumption", 0) or 0) > 0:
                rows[c] = {"production": float(rec["production"]), "consumption": float(rec["consumption"])}
        self._fao_eu_cache = rows
        return rows

    def _align_eu_base_balance(self, eu_supply: pd.Series, by_country: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Set the EU's base production and consumption consistently, per EU market region (one region: the EU;
        CAPRI's two trade blocks: each block from its member states' supply-model rows, by_country)."""
        fao = self._fao_eu_rows()
        if self.eu_blocks:
            if by_country is None:
                raise ValueError("two EU market regions need the supply per country (by_country)")
            sup = self.eu_rows(by_country)
        else:
            sup = pd.DataFrame([eu_supply], index=["EU27"])
        base_supply = pd.DataFrame(0.0, index=list(self.EU), columns=self.commodities)
        if getattr(self, "_eu_aligned_use", None) is None:
            self._eu_aligned_use = {}
        tb = self._eu_ms_balance() if self.eu_blocks else None
        for reg in self.EU:
            ne = (getattr(self, "_base_net_exports_eu", {}) or {}).get(reg, {})
            al = self._eu_aligned_use.setdefault(reg, {})
            for comm in self.commodities:
                p_model = float(sup.at[reg, comm]) if (reg in sup.index and comm in sup.columns) else 0.0
                if p_model <= 0:
                    base_supply.at[reg, comm] = float(self.base_production.at[reg, comm])
                    continue
                if self.eu_blocks:
                    k = (reg, comm)
                    fp = float(tb.at[k, "prod_kt"]) if k in tb.index else 0.0
                    fc = float(tb.at[k, "use_kt"]) if k in tb.index else 0.0
                else:
                    rec = fao.get(comm, {})
                    fp, fc = float(rec.get("production", 0) or 0), float(rec.get("consumption", 0) or 0)
                if fp > 0 and fc > 0:
                    cons = p_model * fc / fp                 # the source's self-sufficiency
                else:
                    cons = max(1.0, p_model - float(ne.get(comm, 0.0)))
                self.base_production.at[reg, comm] = p_model
                self.base_consumption.at[reg, comm] = cons
                # the ALIGNED EU use, before calibration rescales base_consumption
                # (_exempt_eu_from_world_calibration divides it by the calibration
                # factor); the EU base crush is anchored on this value
                al[comm] = cons
                base_supply.at[reg, comm] = p_model
        # DAIRY: EU base production of the traded dairy products = CAPRI's 2030 reference output of the
        # dairy block, consumption = that + CAPRI's extra-EU net imports; raw milk is all used in the EU
        dp = self._dairy_params()
        if dp and float(eu_supply.get("MILK", 0.0) or 0.0) > 0:
            self._dairy_S0 = float(eu_supply.get("MILK"))
            # raw milk delivered per member state at base (the dairy blocks' milk ratios)
            self._dairy_S0_ms = self._milk_by_ms(by_country) if by_country is not None else None
            self._dairy_S0_reg = {reg: float(sup.at[reg, "MILK"]) if reg in sup.index else 0.0 for reg in self.EU}
            self.sv.dairy_u = None
            self.sv.dairy_u_all = {}
            self.ev.eu_milk_supply_now = dict(self._dairy_S0_reg)
            for reg in self.EU:
                m0 = self._dairy_S0_reg[reg]
                self.base_production.at[reg, "MILK"] = m0
                self.base_consumption.at[reg, "MILK"] = m0
                self._eu_aligned_use[reg]["MILK"] = m0
                base_supply.at[reg, "MILK"] = m0
                rp = dp["reg"][reg]
                for k, c in self.DAIRY_TRADED.items():
                    i = dp["ix"][k]
                    q = float(rp["Q0"][i] - rp["proc0"][i])
                    cons = q + float(rp["net_imports0"].get(k, 0.0))
                    self.base_production.at[reg, c] = q
                    self.base_consumption.at[reg, c] = cons
                    self._eu_aligned_use[reg][c] = cons
                    base_supply.at[reg, c] = q
        return base_supply

    def _align_sup_base(self, exo_sup: Dict[str, pd.Series]) -> None:
        """Base of the non-EU market regions with supply models (Norway, K56) at their supply models' output, as the
        EU's (_align_eu_base_balance): production of the supply models' products = the models' (bilateral products:
        the closure's domestic sales absorb the difference to CAPRI's flows); raw milk all delivered to the region's
        own dairies (use = production; CAPRI does not trade raw milk), the dairy block's base delivery recorded."""
        self._sup_milk0 = {}
        dairy = set(self.DAIRY_TRADED.values())
        for reg, ser in (exo_sup or {}).items():
            if reg not in self.base_production.index:
                continue
            for c, v in ser.items():
                if c in self.base_production.columns and float(v) > 1e-6 and c not in dairy:
                    self.base_production.at[reg, c] = float(v)
            m0 = float(ser.get("MILK", 0.0) or 0.0)
            if m0 > 0 and "MILK" in self.base_production.columns:
                self._sup_milk0[reg] = m0
                self.base_consumption.at[reg, "MILK"] = m0
        self.ev.sup_milk_now = dict(self._sup_milk0)

    def _demand_cal_factor(self, comm: str) -> float:
        cal = getattr(self, "_demand_cal", None)
        if cal is not None and comm in cal.index:
            return float(cal[comm])
        return 1.0
