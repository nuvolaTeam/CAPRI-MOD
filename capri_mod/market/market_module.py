"""
CAPRI Market Module
===================
Global spatial multi-commodity partial equilibrium model.

Implements the Armington (1969) assumption:
  - Goods from different origins are imperfect substitutes
  - Bilateral trade flows determined by price differentials and tariffs
  - Market clearing: excess supply = excess demand at equilibrium prices

Mathematical structure:
  For each commodity k and trade region r:
    Demand:     QD_r  = QD0_r × (PD_r / PD0_r)^η_k
    Supply:     QS_r  = QS0_r × (PS_r / PS0_r)^ε_k
    Armington:  import share_rj = (P_rj / Σ P_rj)^(-σ) / Σ(P_rj / Σ P_rj)^(-σ)
    Trade:      TRD_rj = M_r × share_rj
    Market clr: Σ_r QS_r = Σ_r QD_r  (spatial)

The system is solved as a mixed complementarity problem (MCP),
approximated here by Newton iteration on excess demand.

Reference: CAPRI Manual Chapter 5 (Market Module), Britz 2008.
           Armington, P.S. (1969). A theory of demand for products
           distinguished by place of production. IMF Staff Papers 16(1).
"""

import numpy as np
import pandas as pd
from scipy.optimize import fsolve
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple

from capri_mod.params import param, param_table
from capri_mod.settings import setting, current as _settings
from capri_mod.data.definitions import (
    MARKET_COMMODITIES, ALL_TRADE_REGIONS,
)
from capri_mod.data.definitions import MS_CODE


# ---------------------------------------------------------------------------
# DATA STRUCTURES
# ---------------------------------------------------------------------------

@dataclass
class MarketEquilibrium:
    """Results of a market module solve."""
    world_prices: pd.Series          # EUR/t, CIF
    domestic_prices: pd.DataFrame    # [region × commodity], EUR/t
    production: pd.DataFrame         # [region × commodity], 1000 t
    consumption: pd.DataFrame        # [region × commodity], 1000 t
    trade_flows: pd.DataFrame        # MultiIndex (exp, imp) × commodity
    net_exports: pd.DataFrame        # [region × commodity]
    welfare: pd.DataFrame            # [region × {consumer, producer, budget}]
    excess_demand: pd.Series         # residual per commodity (should ≈ 0)
    converged: bool = True
    iterations: int = 0
    #: each region's base domestic price moved by the world price index (no regional departure):
    #: domestic_prices against it is the region's premium over the world market
    wedge_prices: Optional[pd.DataFrame] = None
    #: EU biofuel block at the equilibrium (MarketModule.biofuel_feedstock_use): feedstock use by
    #: commodity and by feedstock, biofuel output (kt)
    biofuel: Optional[dict] = None
    #: EU dairy block at the equilibrium (MarketModule.dairy_block): price ratios of the products,
    #: raw milk, fat and protein; production of the nine products and raw milk delivered (kt)
    dairy: Optional[dict] = None


# ---------------------------------------------------------------------------
# MARKET MODULE
# ---------------------------------------------------------------------------

class MarketModule:
    """
    CAPRI's global market model for the given EU supply (arm/market_model.gms).

    30 trade regions (or the EU as two blocks, eu_blocks) and 58 commodities: bilateral trade with two
    Armington nests, transport costs, tariffs and the EU's tariff-rate quotas (market/bilateral.py),
    Generalised Leontief food demand, processing (ProcNQ_, oilseed crushing), the dairy block (fat and
    protein), biofuel markets and feed bulks per member state. Non-EU supply responds with own-price
    elasticities; EU supply comes from the regional supply models (fixed within one solve), and so does the supply
    of Norway (NOR, CAPRI's market region NO000000 with supply models; SUP_NONEU_REGIONS, KNOWN_ISSUES K56).

    Solve: Newton per commodity on the bilateral system, with Anderson acceleration across the
    commodities' links (solve -> _solve_bilateral_equilibrium -> _solve_bilateral).
    """


    #: CAPRI's EU market structure (docs/archive/MARKET_STRUCTURE_PLAN.md step 3): False - the EU is one market region
    #: (EU27); True - CAPRI's two trade blocks EU_WEST (EU-14) and EU_EAST (EU-13) of gams/aggregation/defaultA.agg,
    #: each with its own market and Armington prices and bilateral trade between them, the member states inside
    #: (capri_data/shared/eu_market_blocks.csv). Read when the module is built (data["eu_market_blocks"] overrides).
    eu_blocks = setting("market.eu_blocks", run_state=True)
    EU_BLOCK_REGIONS = ("EU_WEST", "EU_EAST")
    #: market regions outside the EU whose market supply is their supply models' output (CAPRI's RMSSUP outside the
    #: EU: Norway, NO000000, its own market region in aggregation/defaultA.agg; KNOWN_ISSUES K56). Like the EU's,
    #: their supply is fixed within one market solve, anticipated against the prices their models last saw, and
    #: the base calibration takes it at the model's own levels; their models see their own market's prices.
    SUP_NONEU_REGIONS = ("NOR",)
    #: supply-model country (NUTS-0 of the supply models) -> its non-EU market region
    SUP_NONEU_COUNTRY = {"NO": "NOR"}
    #: non-EU market region -> CAPRI code of its supply models' country (member-state keyed tables)
    SUP_NONEU_MS = {"NOR": "NO000000"}

    def __init__(self, data: dict):
        self.data       = data
        self.commodities = MARKET_COMMODITIES
        _eb = data.get("eu_market_blocks") if isinstance(data, dict) else None
        self.eu_blocks = bool(type(self).eu_blocks if _eb is None else _eb)
        if self.eu_blocks:
            self.regions = [x for r in ALL_TRADE_REGIONS for x in (self.EU_BLOCK_REGIONS if r == "EU27" else (r,))]
            self.EU = tuple(self.EU_BLOCK_REGIONS)
        else:
            self.regions = ALL_TRADE_REGIONS
            self.EU = ("EU27",)
        self.n_comm     = len(self.commodities)
        self.n_reg      = len(self.regions)
        #: the non-EU market regions with supply models in this market (SUP_NONEU_REGIONS)
        self.SUP = tuple(r for r in self.SUP_NONEU_REGIONS if r in self.regions)

        # Base data
        self.world_prices_base = data["world_prices"].reindex(self.commodities)
        _miss = [c for c in self.commodities if not (float(self.world_prices_base.get(c, float("nan"))) > 0)]
        if _miss:
            # no invented price (a fixed 200 EUR/t was used here): every market product needs CAPRI's world price
            raise ValueError(f"no base world price for market products {_miss} (capri_data world prices)")
        self.tariffs       = data["tariffs"]
        if self.eu_blocks and "EU27" in self.tariffs.index:
            # the EU's common external tariff applies to both blocks (no tariff between them: CAPRI's flows)
            _t = self.tariffs.copy()
            for _b in self.EU:
                _t.loc[_b] = _t.loc["EU27"]
            self.tariffs = _t.drop(index="EU27")
        self.armington     = data["armington"]
        self._demand_cal   = None  # set by the bilateral calibration at the first solve

        # Compute baseline consumption and production
        self._calibrate_baseline()
        # Pristine base tables, restored at every baseline reset (see
        # CAPRIModel.run): EU rows of commodities WITHOUT farm-model supply
        # (oils, cakes, rice, fats, other food) are not re-aligned per run, so
        # whatever an earlier run left there persisted into later runs.
        self._base_production0 = self.base_production.copy()
        self._base_consumption0 = self.base_consumption.copy()

    # ------------------------------------------------------------------
    # EU market regions (one region EU27, or CAPRI's two trade blocks)
    # ------------------------------------------------------------------
    def _ms_block_map(self) -> Dict[str, str]:
        m = getattr(self, "_ms_block_cache", None)
        if m is None:
            from pathlib import Path as _P
            f = _P(__file__).resolve().parents[2] / "capri_data" / "shared" / "eu_market_blocks.csv"
            m = pd.read_csv(f).set_index("ms")["block"].astype(str).to_dict()
            self._ms_block_cache = m
        return m

    def eu_region_of_ms(self, ms: str) -> Optional[str]:
        """The EU market region of a CAPRI member state (BL000000, DE000000, ...): EU27, or its trade block; None for
        the supply-model countries outside the EU (Norway, NO000000: market region NOR)."""
        if ms in self.SUP_NONEU_MS.values():
            return None
        if not self.eu_blocks:
            return "EU27"
        return self._ms_block_map().get(ms)

    def sup_region_of_country(self, cc: str) -> Optional[str]:
        """The non-EU market region of a supply-model country (two letters, or a NUTS code): NOR for Norway; None
        for the EU's countries."""
        r = self.SUP_NONEU_COUNTRY.get(str(cc)[:2])
        return r if r in getattr(self, "SUP", ()) else None

    def _split_supply(self, exo: Optional[pd.DataFrame]):
        """The supply models' output by country split into the EU's rows (countries x products) and the non-EU
        market regions' totals ({region: Series}, Norway: NOR). Norway's supply regions are not part of the EU's
        market supply (KNOWN_ISSUES K56)."""
        if exo is None:
            return None, {}
        c = getattr(self, "_split_cache", None)
        if c is not None and c[0] is exo:
            return c[1], c[2]
        reg = [self.sup_region_of_country(x) for x in exo.index]
        eu = exo.loc[[r is None for r in reg]]
        sup = {}
        for r in self.SUP:
            rows = exo.loc[[x == r for x in reg]]
            if len(rows):
                sup[r] = rows.sum(axis=0).astype(float)
        self._split_cache = (exo, eu, sup)
        return eu, sup

    #: model country (NUTS-0 of the supply models) -> CAPRI member state
    _COUNTRY_MS = MS_CODE

    def eu_region_of_country(self, cc: str) -> Optional[str]:
        """The EU market region of a supply-model country code (two letters, or a NUTS code)."""
        return self.eu_region_of_ms(self._COUNTRY_MS.get(str(cc)[:2], str(cc)[:2]) + "000000")

    def eu_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """Supply-model rows (countries) summed per EU market region (regions x columns); rows of countries outside
        the EU (Norway) are left out."""
        reg = [self.eu_region_of_country(c) for c in df.index]
        keep = [r is not None for r in reg]
        df = df.loc[keep]
        reg = [r for r in reg if r is not None]
        out = df.groupby(pd.Index(reg, name=None), sort=False).sum()
        return out.reindex(list(self.EU)).fillna(0.0)

    def _eu_ms_balance(self) -> pd.DataFrame:
        """CAPRI's 2030 member-state balance (tools/build/build_eu_ms_balance.py), summed per EU market region and model
        commodity: prod, hcon, feed, proc, biof (1000 t)."""
        t = getattr(self, "_eu_msbal_cache", None)
        if t is None:
            from pathlib import Path as _P
            f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "market" / "eu_ms_balance_2030.csv"
            try:
                b = pd.read_csv(f, keep_default_na=False)
                b = b[b["commodity"].astype(str) != ""]
                b["region"] = [self.eu_region_of_ms(m) for m in b["ms"]]
                t = b.groupby(["region", "commodity"])[["prod_kt", "hcon_kt", "feed_kt", "proc_kt", "biof_kt"]].sum()
                t["use_kt"] = t[["hcon_kt", "feed_kt", "proc_kt", "biof_kt"]].sum(axis=1)
            except Exception:
                t = pd.DataFrame()
            self._eu_msbal_cache = t
        return t

    def eu_split(self, commodity: str, item: str = "use_kt") -> Dict[str, float]:
        """Each EU market region's part of the EU total of a balance item of a commodity in CAPRI's 2030
        member-state data ({EU27: 1} with one EU region; equal parts where CAPRI has none of it)."""
        if not self.eu_blocks:
            return {"EU27": 1.0}
        t = self._eu_ms_balance()
        v = {r: (float(t.at[(r, commodity), item]) if (r, commodity) in t.index else 0.0) for r in self.EU}
        tot = sum(v.values())
        if tot <= 0:
            return {r: 1.0 / len(self.EU) for r in self.EU}
        return {r: x / tot for r, x in v.items()}

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
        import json as _json
        from pathlib import Path as _P
        mk = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "market"
        year = int(self.data.get("market_year", 2017) or 2017) if isinstance(self.data, dict) else 2017
        sfx = "_eu2" if self.eu_blocks else ""
        ff, fr = mk / f"bilateral_flows_{year}{sfx}.csv", mk / f"bilateral_regions_{year}{sfx}.csv"
        if not ff.exists():
            ff, fr = mk / f"bilateral_flows_2017{sfx}.csv", mk / f"bilateral_regions_2017{sfx}.csv"
        bil = set()
        if ff.exists() and fr.exists():
            fl = pd.read_csv(ff)
            rg = pd.read_csv(fr)
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
            f = mk / fn
            if f.exists():
                for k, v in _json.load(open(f))["balances"].items():
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
    # Domestic prices
    # ------------------------------------------------------------------

    def domestic_prices(
        self,
        world_prices: pd.Series,
        trade_scenario: Optional[Dict] = None,
    ) -> pd.DataFrame:
        """
        Compute domestic (wedge) prices from world prices + tariffs.
        p_domestic = p_world × (1 + tariff/100) × exchange_rate

        Returns DataFrame [region × commodity].
        """
        tariffs = self.tariffs.copy()
        if trade_scenario and "tariff_change" in trade_scenario:
            for comm, change in trade_scenario["tariff_change"].items():
                if comm in tariffs.columns:
                    tariffs[comm] = (tariffs[comm] + change).clip(lower=0)

        # Vectorised: this was a region x commodity loop of scalar .at[]
        # lookups, which dominated the market solve (2.3 million pandas reads
        # per run). The arithmetic is unchanged.
        wp = pd.Series({c: float(world_prices.get(c, self.world_prices_base[c]))
                        for c in self.commodities})
        tar = tariffs.reindex(index=self.regions,
                              columns=self.commodities).fillna(0.0)
        prices = tar.div(100.0).add(1.0).mul(wp, axis=1)
        return prices.astype(float)

    # ------------------------------------------------------------------
    # Supply and demand responses
    # ------------------------------------------------------------------

    #: seed -> (oil, cake)
    CRUSH_CHAINS = {"RAPE": ("RAPO", "RAPC"), "SUNF": ("SUNO", "SUNC"), "SOYA": ("SOYO", "SOYC")}

    #: Biofuel output relative to CAPRI's 2030 reference, per biofuel ({"BIOE": 1.0, "BIOD": 1.0}), when biofuel
    #: markets are NOT endogenous: CAPRI then fixes biofuel output (arm/fix_biofuel_market_vars.gms); a mandate
    #: scenario changes these quantities.
    biofuel_output_scale: Dict[str, float] = {"BIOE": 1.0, "BIOD": 1.0}
    #: Endogenous biofuel markets (CAPRI BIOF_M, star 3.0 GUI default ON; arm/prep_market.gms p_endoBioMarket):
    #: biofuel supply from the processing margin (SupplyBiof_), demand from mandates and the price relative to
    #: fossil fuel (biofDemShare_, biofDem_), bilateral trade; feedstock use follows the biofuel output. Off:
    #: biofuel quantities fixed at the reference, only the feedstock mix responds. A scenario setting
    #: (PolicyScenario.biofuel_markets), docs/BIOFUEL_MARKET.md.
    biofuel_markets = setting("market.biofuel_markets", run_state=True)
    BIOFUELS = ("BIOE", "BIOD")

    def _biofuel_params(self) -> dict:
        """First-generation biofuel feedstock demand, CAPRI's market equations (biofFeedCost_, biofFeedCostAgg_,
        Biof_, prodBiof_, prodQuantBiofBy_), per CAPRI market region.

        From capri_data/2017/market/biofuel_feedstock.csv (tools/build/build_biofuel_market.py): per CAPRI region and
        biofuel, the feedstocks' 2030-reference quantities q0, PRCB, PRCBY, by-product, prices and the numeraire;
        and biofuel_use_share.csv: EU biofuel use as a share of the EU use of each model commodity.
        Returns {"groups": [...], "share": {commodity: EU share}, "q0": {commodity: EU kt},
        "q0_reg": {(region, commodity): kt}, "ddgs0": {region: kt}} ({} when the files are absent).
        """
        cached = getattr(self, "_biof_cache", None)
        if cached is not None:
            return cached
        out = {}
        try:
            from pathlib import Path as _P
            base = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "market"
            f = pd.read_csv(base / "biofuel_feedstock.csv", keep_default_na=False)
            if "region" not in f.columns:
                f["region"] = "EU27"
            sh = pd.read_csv(base / "biofuel_use_share.csv")
            groups = []
            for (ms, fuel), g in f.groupby(["ms", "biofuel"], sort=True):
                reg = str(g["region"].iloc[0])
                if reg == "EU27" and self.eu_blocks:
                    reg = self.eu_region_of_ms(ms) or reg
                if reg not in self.regions:
                    continue
                q0 = g["biof_kt"].astype(float).values
                prcb = g["prcb"].astype(float).values
                p0 = g["feed_price"].astype(float).values
                prcby = g["prcby"].astype(float).values
                pby0 = g["byproduct_price"].astype(float).values
                by = prcby * pby0
                mu0 = p0 - by
                if (mu0 <= 0).any() or (q0 <= 0).any():
                    continue
                X0 = float((q0 * prcb).sum())
                mub0 = float((q0 * mu0).sum()) / X0                  # = CAPRI BiofFeedCost (checked by the builder)
                rho = float(g["rho"].iloc[0])
                dp = q0 / X0 * (mu0 / mub0) ** rho                   # def_biofuel_params.gms p_dpCESBiof
                ddgs = np.array([b_ == "DDGS" for b_ in g["byproduct"].astype(str)])
                groups.append(dict(ms=ms, fuel=fuel, region=reg, comm=list(g["commodity"].astype(str)),
                                   feed=list(g["feedstock"].astype(str)), q0=q0, prcb=prcb, p0=p0, by=by,
                                   prcby=prcby, ddgs=ddgs, X0=X0, mub0=mub0, rho=rho, dp=dp,
                                   num=int(np.argmax(g["numeraire"].astype(int).values))))
            share = {str(r.commodity): float(r.share) for r in sh.itertuples()
                     if r.commodity in self.commodities and float(r.share) > 0}
            q0c, q0r, dd0 = {}, {}, {}
            for gr in groups:
                for c, q in zip(gr["comm"], gr["q0"]):
                    if c and c in self.commodities:
                        q0r[(gr["region"], c)] = q0r.get((gr["region"], c), 0.0) + float(q)
                        if gr["region"] in self.EU and c in share:
                            q0c[c] = q0c.get(c, 0.0) + float(q)
                dd0[gr["region"]] = dd0.get(gr["region"], 0.0) + float((gr["q0"] * gr["prcby"] * gr["ddgs"]).sum())
            # biofuel share of use per EU market region: the region's feedstock use over its use (the EU use of the
            # file split by CAPRI's member-state use); one EU region: the file's share
            use_eu = {str(r.commodity): float(r.use_kt) for r in sh.itertuples()}
            share_reg = {}
            for reg in self.EU:
                for c, sh_ in share.items():
                    if not self.eu_blocks:
                        share_reg[(reg, c)] = sh_
                        continue
                    u = use_eu.get(c, 0.0) * self.eu_split(c)[reg]
                    q = q0r.get((reg, c), 0.0)
                    if u > 0 and q > 0:
                        share_reg[(reg, c)] = min(1.0, q / u)
            out = {"groups": groups, "share": share, "q0": q0c, "q0_reg": q0r, "ddgs0": dd0,
                   "share_reg": share_reg} if groups else {}
        except Exception:
            out = {}
        self._biof_cache = out
        return out

    def _biofuel_market_params(self) -> dict:
        """CAPRI's biofuel supply and demand functions per CAPRI market region (biofuel/def_biofuel_params.gms,
        calibrated by tools/build/build_biofuel_market.py to the 2030 reference): {(ms, fuel): row} plus the region
        totals at the reference (output, biofuel use, non-fuel processing). {} when the file is absent."""
        cached = getattr(self, "_biofm_cache", None)
        if cached is not None:
            return cached
        out = {}
        try:
            from pathlib import Path as _P
            f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "market" / "biofuel_market.csv"
            m = pd.read_csv(f)
            for col in ("proc_kt", "proc_hess", "inpe"):
                if col not in m.columns:
                    m[col] = 0.0
            gidx = {(g["ms"], g["fuel"]): k for k, g in enumerate(self._biofuel_params().get("groups", []))}
            rows = {}
            for r in m.itertuples(index=False):
                if r.region == "EU27" and self.eu_blocks:
                    r = r._replace(region=self.eu_region_of_ms(r.ms) or r.region)
                if r.region not in self.regions or r.biofuel not in self.commodities:
                    continue
                d = r._asdict()
                d["group"] = gidx.get((r.ms, r.biofuel))
                # CAPRI's mandate scenario (scen/bio_fuels/change_biof_mandate.gms) shifts the EU member states'
                # and the UK's QUTS
                d["mandate_region"] = (r.region in self.EU) or (r.ms == "UK000000")
                rows[(r.ms, r.biofuel)] = d
            prod0, use0, proc0 = {}, {}, {}
            for (ms, fuel), d in rows.items():
                k = (d["region"], fuel)
                prod0[k] = prod0.get(k, 0.0) + float(d["prod_kt"])
                use0[k] = use0.get(k, 0.0) + float(d["biof_kt"])
                proc0[k] = proc0.get(k, 0.0) + float(d["proc_kt"])
            out = {"rows": rows, "prod0": prod0, "use0": use0, "proc0": proc0} if rows else {}
        except Exception:
            out = {}
        self._biofm_cache = out
        return out

    #: CAPRI's mandate scenario (scen/bio_fuels/change_biof_mandate.gms): the EU member states' and the UK's
    #: blending mandates QUTS multiplied by this factor (PolicyScenario.biofuel_mandate; acts with endogenous
    #: biofuel markets, where QUTS enters biofDemShare_)
    biofuel_mandate: float = 1.0

    def biofuel_endogenous(self) -> bool:
        """Endogenous biofuel markets are on: the switch, the bilateral market, both biofuels traded, data."""
        return bool(getattr(self, "biofuel_markets", True)) and getattr(self, "market_structure", "") == "bilateral" \
            and all(b in self.commodities for b in self.BIOFUELS) and bool(self._biofuel_market_params())

    @staticmethod
    def _sigmoid(x):
        return 1.0 / (1.0 + np.exp(-np.clip(x, -500.0, 500.0)))

    def _biofuel_feed_group(self, g, ratio: Dict[str, float], X: Optional[float] = None, ddgs_ratio: float = 1.0):
        """One CAPRI region's feedstock CES for one biofuel at feedstock price ratios (Arm1 prices relative to
        the reference): returns (q per feedstock, mu_b). X = first-generation output (default: the reference
        output x biofuel_output_scale); ddgs_ratio = the region's DDGS producer price relative to the reference.

            mu_f = p_f0 x ratio_c - PRCBY_f x p_by          (biofFeedCost_; DDGS at its producer price, glycerine
                                                             fixed at 600 EUR/t as in CAPRI)
            mu_b = (sum_f dp_f mu_f^(1-rho))^(1/(1-rho))    (biofFeedCostAgg_)
            q_f  = dp_f X (mu_b / mu_f)^rho, f not the numeraire (Biof_)
            q_num = (X - sum_f q_f PRCB_f) / PRCB_num        (prodBiof_)
        """
        r = np.array([float(ratio.get(c, 1.0)) if c else 1.0 for c in g["comm"]])
        by = g["by"] * np.where(g["ddgs"], float(ddgs_ratio), 1.0)
        mu = np.maximum(g["p0"] * r - by, 1e-6)
        rho = g["rho"]
        mub = float((g["dp"] * mu ** (1.0 - rho)).sum()) ** (1.0 / (1.0 - rho))
        if X is None:
            X = g["X0"] * float((self.biofuel_output_scale or {}).get(g["fuel"], 1.0))
        q = g["dp"] * X * (mub / mu) ** rho
        n = g["num"]
        rest = float((q * g["prcb"]).sum() - q[n] * g["prcb"][n])
        q[n] = max(0.0, (X - rest) / g["prcb"][n])
        return q, mub

    def biofuel_state(self, prod_ratio: Optional[pd.DataFrame], arm_ratio: Optional[pd.DataFrame],
                      endogenous: Optional[bool] = None, use_only: bool = False) -> dict:
        """CAPRI's biofuel processing and biofuel markets at producer price ratios (prod_ratio: region x
        commodity, market prices relative to the reference) and Armington price ratios (arm_ratio), per CAPRI
        market region:

          supply  PR = PPRI0 x r_b / mu_b (biofPriceRel_; producer prices move with the market price,
                  multiplicative margin),  X = scale PR + exp(alfa + beta log(PR + 0.01)) SIGMOID(slope (PR - turn))
                  (SupplyBiof_); production = X + NAGR + SECG + EXOG (MaprBiof_, the last three fixed)
          DDGS    output = sum_f q_f PRCBY_f over the cereal feedstocks (prodQuantBiofBy_); its producer price
                  enters the feedstock cost (biofFeedCost_)
          demand  consumer price = CPRI0 + ARM1P0 (ra_b - 1) (Cpri_: additive tax and margins),
                  share = QUTS x mandate + MAX SIGMOID(Slope (CPRI / fossil CPRI - Turn)) (biofDemShare_),
                  BIOF = share x HCON x oilEqu_f / oilEqu_b (biofDem_; total fuel use and fossil prices fixed)
          other   non-fuel processing PROC = PROC0 - hess x ARM1P0 (ra_b - 1) / INPE (ProcNQ_, own term)

        Without endogenous biofuel markets (CAPRI without BIOF_M) biofuel output is the reference x
        biofuel_output_scale and only the feedstock mix and DDGS respond. Regions without a supply function (no
        feedstocks or no price relation) keep their reference output, without a demand function (no fossil fuel
        data or no use above the mandate) their reference use.
        Returns {"X": {(ms, fuel): kt}, "mub": {...}, "prod": {(region, fuel): kt}, "use": {...}, "proc": {...},
        "ddgs": {region: kt}, "ddgs_ratio": {region: ratio}, "endogenous": bool}."""
        endo = self.biofuel_endogenous() if endogenous is None else bool(endogenous)
        bm = self._biofuel_market_params()
        bp = self._biofuel_params()
        groups = bp.get("groups", [])
        scale = self.biofuel_output_scale or {}
        mand = float(1.0 if getattr(self, "biofuel_mandate", None) is None else self.biofuel_mandate)
        has_dd = "DDGS" in self.commodities

        # positional lookups (pandas scalar access here was a sizeable share of the market solve)
        _pi = {r: i for i, r in enumerate(prod_ratio.index)} if prod_ratio is not None else {}
        _pc = {c: j for j, c in enumerate(prod_ratio.columns)} if prod_ratio is not None else {}
        _pa = prod_ratio.to_numpy(dtype=float) if prod_ratio is not None else None
        _ai = {r: i for i, r in enumerate(arm_ratio.index)} if arm_ratio is not None else {}
        _ac = {c: j for j, c in enumerate(arm_ratio.columns)} if arm_ratio is not None else {}
        _aa = arm_ratio.to_numpy(dtype=float) if arm_ratio is not None else None

        def dratio(reg):
            if prod_ratio is None or not has_dd or reg not in _pi:
                return 1.0
            return float(_pa[_pi[reg], _pc["DDGS"]])

        def aratio(reg, c):
            if arm_ratio is None or not c or reg not in _ai or c not in _ac:
                return 1.0
            return float(_aa[_ai[reg], _ac[c]])

        X, MUB, prod, use, proc, ddgs, drat = {}, {}, {}, {}, {}, {}, {}
        rows = bm.get("rows", {})
        # first-generation output and feedstock cost of every feedstock group (not needed for use and processing)
        for g in ([] if use_only else groups):
            reg, key = g["region"], (g["ms"], g["fuel"])
            drat[reg] = dratio(reg)
            ratio = {c: aratio(reg, c) for c in g["comm"] if c}
            q1, mub = self._biofuel_feed_group(g, ratio, 1.0, drat[reg])
            MUB[key] = mub
            d = rows.get(key)
            x = g["X0"] * float(scale.get(g["fuel"], 1.0))
            if endo and d is not None and float(d["pr0"]) > 0:
                rb = float(_pa[_pi[reg], _pc[g["fuel"]]]) if prod_ratio is not None else 1.0
                PR = float(d["ppri"]) * rb / mub
                x = float(d["sup_scale"]) * PR + np.exp(float(d["sup_alfa"]) + float(d["sup_beta"]) * np.log(PR + 1e-2)) \
                    * float(self._sigmoid(float(d["sup_slope"]) * (PR - float(d["sup_turn"]))))
                x = max(0.0, x)
            X[key] = x
            ddgs[reg] = ddgs.get(reg, 0.0) + float((q1 * x * g["prcby"] * g["ddgs"]).sum())
        # output, use and processing of every CAPRI market region
        for (ms, fuel), d in rows.items():
            reg = d["region"]
            ra = aratio(reg, fuel)
            x = X.get((ms, fuel), float(d["x0_kt"]) * (1.0 if endo else float(scale.get(fuel, 1.0))))
            prod[(reg, fuel)] = prod.get((reg, fuel), 0.0) + x + float(d["fixed_kt"])
            u = float(d["biof_kt"])
            if endo and float(d["dem_slope"]) != 0.0 and float(d["fossil_cpri"]) > 0:
                cp = max(1e-6, float(d["cpri"]) + float(d["arm1p"]) * (ra - 1.0))
                quts = float(d["quts"]) * (mand if d["mandate_region"] else 1.0)
                share = quts + float(d["dem_max"]) * float(
                    self._sigmoid(float(d["dem_slope"]) * (cp / float(d["fossil_cpri"]) - float(d["dem_turn"]))))
                u = share * float(d["hcon_kt"]) * float(d["oil_eq_fossil"]) / float(d["oil_eq"])
            use[(reg, fuel)] = use.get((reg, fuel), 0.0) + u
            pc = float(d["proc_kt"])
            if endo and pc > 0 and float(d["proc_hess"]) != 0.0 and float(d["inpe"]) > 0:
                pc = max(0.0, pc - float(d["proc_hess"]) * float(d["arm1p"]) * (ra - 1.0) / float(d["inpe"]))
            proc[(reg, fuel)] = proc.get((reg, fuel), 0.0) + pc
        return {"X": X, "mub": MUB, "prod": prod, "use": use, "proc": proc, "ddgs": ddgs, "ddgs_ratio": drat,
                "endogenous": endo}

    def _biofuel_x(self, g) -> float:
        """First-generation output of a feedstock group: the current biofuel state's (endogenous with biofuel
        markets, else the reference x biofuel_output_scale)."""
        st = getattr(self, "_biof_state", None)
        if st is not None:
            return float(st["X"].get((g["ms"], g["fuel"]), g["X0"]))
        return g["X0"] * float((self.biofuel_output_scale or {}).get(g["fuel"], 1.0))

    def biofuel_feedstock_use_region(self, region: str, price_ratio: Dict[str, float]) -> Dict[str, float]:
        """Feedstock use for biofuels of one trade region by model commodity (kt) at its feedstock price ratios."""
        out = {}
        st = getattr(self, "_biof_state", None)
        dr = float((st or {}).get("ddgs_ratio", {}).get(region, 1.0))
        for g in self._biofuel_params().get("groups", []):
            if g["region"] != region:
                continue
            q, _ = self._biofuel_feed_group(g, price_ratio, self._biofuel_x(g), dr)
            for c, x in zip(g["comm"], q):
                if c:
                    out[c] = out.get(c, 0.0) + float(x)
        return out

    # ------------------------------------------------------------------
    # DAIRY PROCESSING (CAPRI arm/market_model.gms DairyNQ_, ProcMargM_, FatsProtBal_)
    # ------------------------------------------------------------------
    #: CAPRI dairy product -> market commodity. CAPRI trades all nine products of its dairy block bilaterally
    #: (Sprint 9f; until then fresh milk products, cream, concentrated milk, whole milk powder and casein cleared
    #: inside each block with fixed extra-regional trade)
    DAIRY_TRADED = {"BUTT": "BUTR", "SMIP": "SKIM", "CHES": "CHES", "WHEP": "WHEY", "FRMI": "FRMI", "CREM": "CREM",
                    "COCM": "COCM", "WMIO": "WMIO", "CASE": "CASE"}
    DAIRY_PRODUCTS = ("BUTT", "SMIP", "CHES", "FRMI", "CREM", "COCM", "WMIO", "CASE", "WHEP")
    #: products cleared inside a block (none since Sprint 9f; the block's algebra keeps the option)
    DAIRY_DOMESTIC = ()

    #: CAPRI's dairy processing in the market (docs/DAIRY_PROCESSING.md): on, as in CAPRI, where the dairy
    #: block is part of the market model (no switch). Since Sprint 9f all nine dairy products are traded and raw
    #: milk, fat and protein are priced per member state. False: dairy products as fixed CAPRI yields of milk.
    use_dairy_block = setting("market.use_dairy_block")

    def _dairy_algebra(self, tables):
        """CAPRI's dairy block as linear algebra for a set of regions that share price RATIOS.

        tables: iterable of (gi, H, milksup): gi = the region's rows indexed by item (the nine products and
        MILK with q_kt, proc_kt, fats_pct, prot_pct, price; INPE, FATS, PROT with their prices), H = {(row, col):
        h} its symmetric Hessian with the MILK row reversed, milksup = its raw milk supply slope
        (p_hessNQSupp MILK, or None where raw milk supply comes from outside: the EU's supply models).
        With z = (rho_k - 1 for the nine products, rho_MILK - 1, phi_fat - 1, phi_prot - 1):
            dm_s = Mm_s z  (ProcMargM_),  dQ_s = H_s dm_s / INPE_s = G_s z  (DairyNQ_),
        G = sum_s G_s; the fat and protein rows of FatsProtBal_; SM = raw milk supply per unit z_MILK."""
        items = list(self.DAIRY_PRODUCTS) + ["MILK"]
        ix = {k: i for i, k in enumerate(items)}
        nz = len(items) + 2
        iF, iP, iM = len(items), len(items) + 1, ix["MILK"]
        G = np.zeros((len(items), nz)); rowF = np.zeros(nz); rowP = np.zeros(nz)
        Q0 = np.zeros(len(items)); proc0 = np.zeros(len(items)); PQ = np.zeros(len(items)); SM = 0.0
        for gi, Hd, msup in tables:
            if "MILK" not in gi.index:
                continue
            inpe = float(gi.at["INPE", "price"]); pf0 = float(gi.at["FATS", "price"])
            pp0 = float(gi.at["PROT", "price"])
            Mm = np.zeros((len(items), nz)); f = np.zeros(len(items)); r = np.zeros(len(items))
            for k in items:
                if k not in gi.index or not float(gi.at[k, "q_kt"]) > 0:
                    continue
                i = ix[k]
                f[i], r[i] = float(gi.at[k, "fats_pct"]), float(gi.at[k, "prot_pct"])
                Mm[i, i] = float(gi.at[k, "price"])
                Mm[i, iF] = -f[i] * pf0
                Mm[i, iP] = -r[i] * pp0
                Q0[i] += float(gi.at[k, "q_kt"])
                PQ[i] += float(gi.at[k, "q_kt"]) * float(gi.at[k, "price"])
                pc = gi.at[k, "proc_kt"]
                proc0[i] += float(pc) if pd.notna(pc) else 0.0
            H = np.zeros((len(items), len(items)))
            for (rw, cl), h in Hd.items():
                if rw in ix and cl in ix:
                    H[ix[rw], ix[cl]] = float(h)
            Gs = H @ Mm / inpe
            G += Gs
            sgn = -np.ones(len(items)); sgn[iM] = 1.0                 # milk in, products out
            rowF += (sgn * f) @ Gs
            rowP += (sgn * r) @ Gs
            if msup is not None:
                SM += float(msup) * float(gi.at["MILK", "price"]) / inpe
        P9 = list(self.DAIRY_PRODUCTS)
        return dict(items=items, ix=ix, G=G, rowF=rowF, rowP=rowP, Q0=Q0, proc0=proc0, iF=iF, iP=iP, iM=iM,
                    dom=[ix[k] for k in self.DAIRY_DOMESTIC if Q0[ix[k]] > 0], SM=SM,
                    p9=np.array([PQ[ix[k]] / Q0[ix[k]] if Q0[ix[k]] > 0 else 1.0 for k in P9]))

    def _dairy_params(self) -> dict:
        """The EU dairy block (tools/build/build_dairy_processing.py): CAPRI's three equations (DairyNQ_, ProcMargM_,
        FatsProtBal_) with one block per member state, raw milk, fat and protein priced per member state as in
        CAPRI, the nine products at their EU market region's prices and traded bilaterally; raw milk delivered
        from the EU supply models; food demand among the nine products with CAPRI's own and cross elasticities;
        feed demand through the FMIL block."""
        if not self.use_dairy_block:
            return {}
        cached = getattr(self, "_dairy_cache", None)
        if cached is not None:
            return cached
        out = {}
        try:
            from pathlib import Path as _P
            base = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "market"
            dp = pd.read_csv(base / "dairy_processing.csv")
            hh = pd.read_csv(base / "dairy_hessian.csv")
            bal = pd.read_csv(base / "dairy_eu_balance.csv").set_index("product")
            tables = [(g.set_index("item"), {(e.row, e.col): e.h for e in hh[hh.ms == ms].itertuples()}, None)
                      for ms, g in dp.groupby("ms")]
            out = self._dairy_algebra(tables)
            # CAPRI clears raw milk, milk fat and protein per member state (FatsProtBal_, ProcMargM_, DairyNQ_ per
            # RMS; raw milk is not traded): one block per member state, the products at their EU prices
            out["ms"] = {ms: self._dairy_algebra([tb]) for ms, tb in zip([m for m, _ in dp.groupby("ms")], tables)}
            out["ms"] = {ms: a for ms, a in out["ms"].items() if a["Q0"][a["iM"]] > 0}
            P9 = list(self.DAIRY_PRODUCTS)
            Em = np.zeros((9, 9))
            fe = base / "dairy_eu_demand_elas.csv"
            if fe.exists():
                for r_ in pd.read_csv(fe).itertuples():
                    if r_.row in P9 and r_.col in P9:
                        Em[P9.index(r_.row), P9.index(r_.col)] = float(r_.elas)
            else:
                for k in self.DAIRY_DOMESTIC:
                    Em[P9.index(k), P9.index(k)] = float(bal.at[k, "eta_hcom"])
            out.update(E=Em, hc9=np.array([float(bal.at[k, "hcom_kt"]) for k in P9]),
                       fd9=np.array([float(bal.at[k, "fedm_kt"]) for k in P9]),
                       cons9={k: float(bal.at[k, "prod_kt"] - bal.at[k, "proc_kt"] + bal.at[k, "net_imports_kt"]) for k in P9},
                       net_imports0={k: float(bal.at[k, "net_imports_kt"]) for k in P9})
            # per EU market region: output and processing of its member states' blocks; food and feed use and total
            # use the EU's split by CAPRI's member-state human consumption, feed and use; net imports the rest
            reg = {}
            for rg in self.EU:
                if not self.eu_blocks:
                    reg[rg] = dict(Q0=out["Q0"], proc0=out["proc0"], hc9=out["hc9"], fd9=out["fd9"],
                                   cons9=out["cons9"], net_imports0=out["net_imports0"])
                    continue
                mss = [ms for ms in out["ms"] if self.eu_region_of_ms(ms) == rg]
                Q0 = sum((out["ms"][ms]["Q0"] for ms in mss), np.zeros_like(out["Q0"]))
                pr0 = sum((out["ms"][ms]["proc0"] for ms in mss), np.zeros_like(out["proc0"]))
                cm = {k: self.DAIRY_TRADED[k] for k in P9}
                hc = np.array([out["hc9"][i] * self.eu_split(cm[k], "hcon_kt")[rg] for i, k in enumerate(P9)])
                fd = np.array([out["fd9"][i] * self.eu_split(cm[k], "feed_kt")[rg] for i, k in enumerate(P9)])
                cons = {k: out["cons9"][k] * self.eu_split(cm[k], "use_kt")[rg] for k in P9}
                ix = out["ix"]
                ni = {k: cons[k] - float(Q0[ix[k]] - pr0[ix[k]]) for k in P9}
                reg[rg] = dict(Q0=Q0, proc0=pr0, hc9=hc, fd9=fd, cons9=cons, net_imports0=ni)
            out["reg"] = reg
        except Exception:
            out = {}
        self._dairy_cache = out
        return out

    def _dairy_world_params(self) -> dict:
        """CAPRI's dairy block for the non-EU trade regions (dairy Stage 4, tools/build/build_dairy_world_blocks.py):
        {trade region: params}, CAPRI's market regions of the trade region sharing price ratios; raw milk from
        CAPRI's own supply function (p_hessNQSupp MILK); food demand among the nine products with the
        regions' p_ElasDem weighted by food use; feed use of the products at CAPRI's level (FMIL index 1: the
        model has no non-EU herds), with the CES price term; extra-regional trade of the five non-traded
        products fixed."""
        if not self.use_dairy_block:
            return {}
        cached = getattr(self, "_dairy_world_cache", None)
        if cached is not None:
            return cached
        out = {}
        try:
            from pathlib import Path as _P
            base = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "market"
            wp = pd.read_csv(base / "dairy_world_processing.csv")
            hh = pd.read_csv(base / "dairy_world_hessian.csv")
            ee = pd.read_csv(base / "dairy_world_demand_elas.csv")
            P9 = list(self.DAIRY_PRODUCTS)
            for tr, gt in wp.groupby("trade_region"):
                if tr not in self.regions or tr == "EU27":
                    continue
                tables, hc, fd = [], np.zeros(9), np.zeros(9)
                Enum, Ew = np.zeros((9, 9)), np.zeros(9)
                for rms, g in gt.groupby("rms"):
                    gi = g.set_index("item")
                    ms_ = float(gi.at["MILKSUP", "price"]) if "MILKSUP" in gi.index else 0.0
                    tables.append((gi, {(e.row, e.col): e.h for e in hh[hh.rms == rms].itertuples()}, ms_))
                    for k in P9:
                        if k in gi.index:
                            h_ = float(gi.at[k, "hcon_kt"] or 0.0); hc[P9.index(k)] += h_
                            fd[P9.index(k)] += float(gi.at[k, "feed_kt"] or 0.0)
                            if h_ > 0:
                                Ew[P9.index(k)] += h_
                                for e in ee[(ee.rms == rms) & (ee.row == k)].itertuples():
                                    if e.col in P9:
                                        Enum[P9.index(k), P9.index(e.col)] += h_ * float(e.elas)
                prm = self._dairy_algebra(tables)
                E = np.where(Ew[:, None] > 0, Enum / np.maximum(Ew[:, None], 1e-12), 0.0)
                prm.update(E=E, hc9=hc, fd9=fd)
                if prm["Q0"][prm["iM"]] > 0 and prm["SM"] > 0:
                    out[tr] = prm
        except Exception:
            out = {}
        self._dairy_world_cache = out
        return out

    def _dairy_solve(self, dp, traded_ratio, milk_ratio=None, fi=1.0, key="EU27"):
        """Solve one dairy block. Unknowns: fat, protein and raw milk price ratios and the prices of the five
        products that clear inside the block (fresh milk products, cream, concentrated milk, whole milk
        powder, casein). Equations: fat and protein balances (FatsProtBal_); raw milk: dairies' demand =
        milk delivered (milk_ratio given: the EU) or = CAPRI's raw milk supply function (milk_ratio None);
        the five products: supply - fixed processing + fixed extra-regional net imports = food demand
        (own and cross p_ElasDem) + feed demand (FMIL index x CES 0.5)."""
        G, n = dp["G"], len(dp["items"]) + 2
        iF, iP, iM, dom = dp["iF"], dp["iP"], dp["iM"], dp["dom"]
        unk = [iF, iP, iM] + dom
        zt = np.zeros(n)
        for k, rho in traded_ratio.items():
            if k in dp["ix"]:
                zt[dp["ix"][k]] = float(rho) - 1.0
        mrow = G[iM].copy()
        if milk_ratio is None:
            mrow[iM] -= dp["SM"]                                       # supply moves with the milk price
            mrhs = 0.0
        else:
            mrhs = dp["Q0"][iM] * (float(milk_ratio) - 1.0)
        A = np.vstack([dp["rowF"], dp["rowP"], mrow, G[dom]])
        rhs0 = np.concatenate([[0.0, 0.0, mrhs], np.zeros(len(dom))])
        Au, c = A[:, unk], A @ zt
        nd = len(dom)
        P9 = list(self.DAIRY_PRODUCTS)
        dpos = [P9.index(dp["items"][i]) for i in dom]          # EU-cleared products the block produces
        rho_t = np.array([float(traded_ratio.get(k, 1.0)) for k in P9])

        def demand_change(ud):
            rho = rho_t.copy()
            rho[dpos] = np.maximum(1.0 + ud, 0.05)
            food = np.exp(dp["E"] @ np.log(rho))
            feed = self.dairy_feed_factor(rho, dp, fi)
            return (dp["hc9"] * (food - 1.0) + dp["fd9"] * (feed - 1.0))[dpos]

        cache = getattr(self, "_dairy_u_all", None)
        if cache is None:
            cache = self._dairy_u_all = {}
        u = cache.get(key)
        u = np.zeros(len(unk)) if u is None or len(u) != len(unk) else u.copy()
        for _ in range(60):
            dem = demand_change(u[3:])
            F = Au @ u + c - rhs0 - np.concatenate([np.zeros(3), dem])
            J = Au.copy()
            for q in range(nd):
                du = np.zeros(nd); du[q] = 1e-6
                J[3:, 3 + q] -= (demand_change(u[3:] + du) - dem) / 1e-6
            step = np.linalg.solve(J, -F)
            u = u + step
            if float(np.max(np.abs(step))) < 1e-12:
                break
        cache[key] = u
        z = zt.copy(); z[unk] = u
        Q = dp["Q0"] + G @ z
        items = dp["items"]
        res = {"price_ratio": {**{k: 1.0 + z[dp["ix"][k]] for k in items}, "FATS": 1.0 + z[iF], "PROT": 1.0 + z[iP]},
               "production": {k: float(Q[dp["ix"][k]]) for k in items},
               "production0": {k: float(dp["Q0"][dp["ix"][k]]) for k in items},
               "market_supply": {self.DAIRY_TRADED[k]: float(Q[dp["ix"][k]] - dp["proc0"][dp["ix"][k]])
                                 for k in self.DAIRY_TRADED},
               "market_supply0": {self.DAIRY_TRADED[k]: float(dp["Q0"][dp["ix"][k]] - dp["proc0"][dp["ix"][k]])
                                  for k in self.DAIRY_TRADED},
               "fmil_index": float(fi),
               "residual": float(np.max(np.abs(Au @ u + c - rhs0 - np.concatenate([np.zeros(3), demand_change(u[3:])]))))}
        if milk_ratio is None:
            res["milk_supply_ratio"] = 1.0 + dp["SM"] * z[iM] / dp["Q0"][iM]
        return res

    @staticmethod
    def _dairy_solve_ms(prm, zt, milk_ratio):
        """One member state's block with every product at its (EU) market price: the fat and protein balances
        (FatsProtBal_) and dairies' milk demand = milk delivered (DairyNQ_ for MILK) give the member state's
        fat, protein and raw milk prices; returns the full z (price ratios - 1)."""
        iF, iP, iM = prm["iF"], prm["iP"], prm["iM"]
        unk = [iF, iP, iM]
        A = np.vstack([prm["rowF"], prm["rowP"], prm["G"][iM]])
        rhs = np.array([0.0, 0.0, prm["Q0"][iM] * (float(milk_ratio) - 1.0)])
        u = np.linalg.solve(A[:, unk], rhs - A @ zt)
        z = zt.copy(); z[unk] = u
        return z

    def dairy_block(self, traded_ratio: Dict[str, float], milk_ratio) -> Optional[dict]:
        """The EU dairy block at given EU prices of the dairy products (relative to base, CAPRI codes) and raw milk
        delivered relative to base: per member state ({ms: ratio}, CAPRI: each member state's dairies process its
        own milk at its own fat, protein and raw milk prices) or, as a single number, the same in all."""
        dp = self._dairy_params()
        if not dp:
            return None
        if getattr(self, "_dairy_u", "unset") is None:                 # callers reset the start point
            (getattr(self, "_dairy_u_all", None) or {}).pop("EU27", None)
            self._dairy_u = "unset"
        items = dp["items"]
        n = len(items) + 2
        # traded_ratio: {product: ratio} for every member state, or {EU market region: {product: ratio}}
        per_reg = bool(traded_ratio) and all(isinstance(v, dict) for v in traded_ratio.values())

        def _zt(tr):
            z_ = np.zeros(n)
            for k, rho in tr.items():
                if k in dp["ix"]:
                    z_[dp["ix"][k]] = float(rho) - 1.0
            return z_
        zts = {rg: _zt(traded_ratio.get(rg, {}) if per_reg else traded_ratio) for rg in self.EU}
        zt = zts[self.EU[0]]
        Q = np.zeros(len(items)); Q0 = np.zeros(len(items)); proc0 = np.zeros(len(items))
        Qr = {rg: np.zeros(len(items)) for rg in self.EU}
        vm = vf = vp = vm0 = vf0 = vp0 = 0.0
        vmr = {rg: [0.0, 0.0] for rg in self.EU}
        msr = {}
        for ms, prm in dp["ms"].items():
            rg = self.eu_region_of_ms(ms) or self.EU[0]
            mr = float(milk_ratio.get(ms, 1.0)) if isinstance(milk_ratio, dict) else float(milk_ratio)
            z = self._dairy_solve_ms(prm, zts[rg], mr)
            q_ = prm["Q0"] + prm["G"] @ z
            Q += q_
            Qr[rg] += q_
            Q0 += prm["Q0"]; proc0 += prm["proc0"]
            msr[ms] = {"MILK": 1.0 + z[prm["iM"]], "FATS": 1.0 + z[prm["iF"]], "PROT": 1.0 + z[prm["iP"]],
                       "milk_delivered": mr}
            # EU aggregates for reporting: weights = the member state's base raw milk (fat, protein in it)
            w = prm["Q0"][prm["iM"]]
            vm += w * msr[ms]["MILK"]; vm0 += w
            vf += w * msr[ms]["FATS"]; vp += w * msr[ms]["PROT"]
            vmr[rg][0] += w * msr[ms]["MILK"]; vmr[rg][1] += w
        ix = dp["ix"]
        rgp = dp.get("reg") or {}
        res = {"price_ratio": {**{k: (1.0 + zt[ix[k]]) for k in items if k != "MILK"},
                               "MILK": vm / vm0, "FATS": vf / vm0, "PROT": vp / vm0},
               "milk_price_ratio_reg": {rg: (v[0] / v[1] if v[1] > 0 else 1.0) for rg, v in vmr.items()},
               "market_supply_reg": {rg: {self.DAIRY_TRADED[k]: float(Qr[rg][ix[k]] - rgp[rg]["proc0"][ix[k]])
                                          for k in self.DAIRY_TRADED} for rg in self.EU if rg in rgp},
               "ms_price_ratio": msr,
               "production": {k: float(Q[ix[k]]) for k in items},
               "production0": {k: float(Q0[ix[k]]) for k in items},
               "market_supply": {self.DAIRY_TRADED[k]: float(Q[ix[k]] - proc0[ix[k]]) for k in self.DAIRY_TRADED},
               "market_supply0": {self.DAIRY_TRADED[k]: float(Q0[ix[k]] - proc0[ix[k]]) for k in self.DAIRY_TRADED},
               "fmil_index": float(getattr(self, "_fmil_index", 1.0) or 1.0), "residual": 0.0}
        return res

    #: model country -> CAPRI member state of the dairy block
    _DAIRY_MS = MS_CODE

    def _milk_by_ms(self, exogenous_supply) -> Dict[str, float]:
        """Raw milk delivered per CAPRI member state from the supply models' rows (one per country)."""
        out = {}
        if exogenous_supply is None or "MILK" not in exogenous_supply.columns:
            return out
        for c, v in exogenous_supply["MILK"].items():
            ms = self._DAIRY_MS.get(str(c)[:2], str(c)[:2]) + "000000"
            out[ms] = out.get(ms, 0.0) + float(v)
        return out

    #: CES substitution among the products fed (CAPRI arm/market1.gms p_rhoFeed(RMSSUP,"FMIL") = 0.5)
    RHO_FMIL = param("RHO_FMIL")

    def dairy_feed_factor(self, rho, dp=None, fi=None) -> np.ndarray:
        """Feed use of each dairy product relative to base: FMIL block (calves' milk feed now / base)
        x (CES price index / own price)^0.5, value shares from CAPRI's 2030 feed use at base prices."""
        dp = dp if dp is not None else self._dairy_params()
        fd = dp["fd9"]
        rho = np.asarray(rho, float)
        v = fd * dp["p9"]
        w = v / v.sum() if v.sum() > 0 else np.ones_like(fd) / len(fd)
        sg = self.RHO_FMIL
        pb = float((w * rho ** (1.0 - sg)).sum()) ** (1.0 / (1.0 - sg))
        fi = float(getattr(self, "_fmil_index", 1.0) or 1.0) if fi is None else float(fi)
        return fi * (pb / rho) ** sg

    def _dairy_eu_prices(self, world_prices) -> Dict[str, float]:
        """EU prices of the traded dairy products relative to base, as the dairy block sees them: the
        wedge price x the current EU Armington premium (lagged within an outer iteration). With two EU market
        regions (bilateral market): {region: {product: ratio}}."""
        dom = self.domestic_prices(world_prices, getattr(self, "_trade_scenario_now", None))
        d0 = getattr(self, "_dom0_cache", None)
        if d0 is None:
            d0 = self.domestic_prices(self.world_prices_base)
            self._dom0_cache = d0
        bl = getattr(self, "_bilat_ratio_now", None)
        if bl is not None and self.eu_blocks:
            return {rg: {k: float(bl.at[rg, c]) if (c in bl.columns and rg in bl.index) else 1.0
                         for k, c in self.DAIRY_TRADED.items()} for rg in self.EU}
        if self.eu_blocks:
            return {rg: {k: 1.0 for k in self.DAIRY_TRADED} for rg in self.EU}
        if bl is not None and "EU27" in bl.index:
            return {k: float(bl.at["EU27", c]) if c in bl.columns else 1.0 for k, c in self.DAIRY_TRADED.items()}
        prem = getattr(self, "eu_premium", None) if getattr(self, "_eu_base_supply", None) is not None else None
        out = {}
        for k, c in self.DAIRY_TRADED.items():
            b = float(d0.at["EU27", c])
            pr = float(prem.get(c, 1.0)) if prem is not None else 1.0
            out[k] = float(dom.at["EU27", c]) / b * pr if b > 0 else 1.0
        return out

    def biofuel_feedstock_use(self, price_ratio: Dict[str, float]) -> dict:
        """EU feedstock use for biofuels at EU feedstock prices (relative to base; with two EU market regions
        {region: {commodity: ratio}}), CAPRI's equations
        (MarketModule._biofuel_feed_group); first-generation output from the biofuel market when endogenous,
        else the 2030-reference output x biofuel_output_scale. Returns {"by_commodity": {c: kt},
        "by_feedstock": {(fuel, feedstock): kt}, "output": {fuel: kt}} (output: first generation).
        """
        byc, byf, outp = {}, {}, {}
        for g in self._biofuel_params().get("groups", []):
            if g["region"] not in self.EU:
                continue
            X = self._biofuel_x(g)
            st = getattr(self, "_biof_state", None)
            pr = (price_ratio.get(g["region"], {}) if any(isinstance(v, dict) for v in price_ratio.values())
                  else price_ratio)
            q, _ = self._biofuel_feed_group(g, pr, X, float((st or {}).get("ddgs_ratio", {}).get(g["region"], 1.0)))
            outp[g["fuel"]] = outp.get(g["fuel"], 0.0) + X
            for c, f, x in zip(g["comm"], g["feed"], q):
                byf[(g["fuel"], f)] = byf.get((g["fuel"], f), 0.0) + float(x)
                if c:
                    byc[c] = byc.get(c, 0.0) + float(x)
        return {"by_commodity": byc, "by_feedstock": byf, "output": outp}

    def _feed_bulk_params(self) -> dict:
        """CAPRI's feed bulks of the member states (arm/market_model.gms feedBlkPrice_, feedShareEqu_;
        tools/build/build_feed_bulks.py): per (member state, bulk) the products' model commodities, 2030 feed quantities,
        value shares and the substitution elasticity; the feed share of EU use per commodity and the EU feed
        totals. {} when the files are absent."""
        cached = getattr(self, "_fbulk_cache", None)
        if cached is not None:
            return cached
        out = {}
        try:
            from pathlib import Path as _P
            base = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "market"
            f = pd.read_csv(base / "feed_bulks_eu.csv", keep_default_na=False)
            sh = pd.read_csv(base / "feed_bulks_eu_share.csv")
            bulks = {}
            for (ms, b), g in f.groupby(["ms", "bulk"], sort=True):
                q0 = g["feed_kt"].astype(float).values
                v0 = q0 * g["arm1p"].astype(float).values
                comm = [c if c in self.commodities else "" for c in g["commodity"].astype(str)]
                bulks[(ms, b)] = dict(comm=comm, q0=q0, s=v0 / v0.sum(), rho=float(g["rho"].iloc[0]))
            feed0, feed0_reg = {}, {r: {} for r in self.EU}
            for (ms, b), d in bulks.items():
                reg = self.eu_region_of_ms(ms)
                for c, q in zip(d["comm"], d["q0"]):
                    if c:
                        feed0[c] = feed0.get(c, 0.0) + float(q)
                        if reg in feed0_reg:
                            feed0_reg[reg][c] = feed0_reg[reg].get(c, 0.0) + float(q)
            share = {str(r.commodity): float(r.share) for r in sh.itertuples()
                     if r.commodity in self.commodities and r.commodity in feed0}
            # per EU market region: the region's feed over its use, the EU use (file) split by CAPRI's member-state
            # use (eu_split); one EU region: the file's share
            use_eu = {str(r.commodity): float(r.use_kt) for r in sh.itertuples()}
            share_reg = {}
            for reg in self.EU:
                share_reg[reg] = {}
                for c, sh_ in share.items():
                    if not self.eu_blocks:
                        share_reg[reg][c] = sh_
                        continue
                    u = use_eu.get(c, 0.0) * self.eu_split(c)[reg]
                    f = feed0_reg[reg].get(c, 0.0)
                    if u > 0 and f > 0:
                        share_reg[reg][c] = min(1.0, f / u)
            out = {"bulks": bulks, "feed0": feed0, "share": share, "feed0_reg": feed0_reg,
                   "share_reg": share_reg} if bulks else {}
            # Norway's bulks (CAPRI's feedBlkPrice_, feedShareEqu_ hold for every NUTS0 with supply models, RMSSUP):
            # its supply models' bulk price indices at its own market's prices, and its feed demand per product
            # following its herds, in its own market region NOR (KNOWN_ISSUES K56; not part of the EU's feed demand).
            # The feed share of Norway's use per commodity: CAPRI's 2030 feed over its use (HCOM + FEDM + INDM + BIOF
            # + LOSM + PRCM, feed_bulks_no.csv use_kt), as the EU's (feed_bulks_eu_share.csv)
            fno = base / "feed_bulks_no.csv"
            if out and fno.exists():
                pno, f0s, u0s, ms_reg = {}, {}, {}, {v: k for k, v in self.SUP_NONEU_MS.items()}
                tno = pd.read_csv(fno, keep_default_na=False)
                for (ms, b), g in tno.groupby(["ms", "bulk"], sort=True):
                    q0 = g["feed_kt"].astype(float).values
                    v0 = q0 * g["arm1p"].astype(float).values
                    comm = [c if c in self.commodities else "" for c in g["commodity"].astype(str)]
                    pno[(ms, b)] = dict(comm=comm, q0=q0, s=v0 / v0.sum(), rho=float(g["rho"].iloc[0]))
                    rg = ms_reg.get(ms)
                    uk = g["use_kt"].astype(float).values if "use_kt" in g.columns else np.zeros(len(g))
                    for c, q, u in zip(comm, q0, uk):
                        if c and rg is not None:
                            f0s.setdefault(rg, {})[c] = f0s.setdefault(rg, {}).get(c, 0.0) + float(q)
                            u0s.setdefault(rg, {})[c] = u0s.setdefault(rg, {}).get(c, 0.0) + float(u)
                out["bulks_sup"] = pno
                out["feed0_sup"] = f0s
                out["share_sup"] = {rg: {c: min(1.0, q / u0s[rg][c]) for c, q in f0.items() if u0s[rg].get(c, 0.0) > 0}
                                    for rg, f0 in f0s.items()}
        except Exception:
            out = {}
        self._fbulk_cache = out
        return out

    def feed_bulk_price_ratio(self, ms: str, bulk: str, price_ratio: Dict[str, float]) -> float:
        """CAPRI's bulk price index (feedBlkPrice_) of a member state relative to the reference:
        (sum_i s_i (p_i / p_i0)^(1 - rho))^(1 / (1 - rho)), s_i the reference value shares; products without a
        model market at the reference price. 1 where the member state has no such bulk."""
        fb = self._feed_bulk_params()
        d = (fb.get("bulks") or {}).get((ms, bulk)) or (fb.get("bulks_sup") or {}).get((ms, bulk))
        if d is None:
            return 1.0
        r = np.array([max(float(price_ratio.get(c, 1.0)), 1e-6) if c else 1.0 for c in d["comm"]])
        rho = d["rho"]
        return float((d["s"] * r ** (1.0 - rho)).sum()) ** (1.0 / (1.0 - rho))

    def eu_feed_use(self, price_ratio: Dict[str, float], region: Optional[str] = None) -> Dict[str, float]:
        """EU feed use per model commodity (kt) from the member states' bulks at the EU price ratios (CAPRI
        feedShareEqu_): q_i = q_i0 x (B / B0) x (P_B / p_i)^rho with prices relative to the reference; B / B0 from
        the supply models (_feed_bulk_index, 1 before any supply result). region: only the member states of that
        EU market region (their block's prices)."""
        fb = self._feed_bulk_params()
        bix = getattr(self, "_feed_bulk_index", None) or {}
        out = {}
        for (ms, b), d in (fb.get("bulks") or {}).items():
            if region is not None and self.eu_region_of_ms(ms) != region:
                continue
            r = np.array([max(float(price_ratio.get(c, 1.0)), 1e-6) if c else 1.0 for c in d["comm"]])
            rho = d["rho"]
            pb = float((d["s"] * r ** (1.0 - rho)).sum()) ** (1.0 / (1.0 - rho))
            q = d["q0"] * float(bix.get((ms, b), 1.0)) * (pb / r) ** rho
            for c, x in zip(d["comm"], q):
                if c:
                    out[c] = out.get(c, 0.0) + float(x)
        return out

    def sup_feed_use(self, region: str, price_ratio: Dict[str, float]) -> Dict[str, float]:
        """Feed use per model commodity (kt) of a non-EU market region with supply models (Norway) from its bulks
        at its price ratios (CAPRI feedShareEqu_, as eu_feed_use): q_i = q_i0 x (B / B0) x (P_B / p_i)^rho, B / B0
        from its supply models (_feed_bulk_index)."""
        fb = self._feed_bulk_params()
        bix = getattr(self, "_feed_bulk_index", None) or {}
        ms0 = self.SUP_NONEU_MS.get(region)
        out = {}
        for (ms, b), d in (fb.get("bulks_sup") or {}).items():
            if ms != ms0:
                continue
            r = np.array([max(float(price_ratio.get(c, 1.0)), 1e-6) if c else 1.0 for c in d["comm"]])
            rho = d["rho"]
            pb = float((d["s"] * r ** (1.0 - rho)).sum()) ** (1.0 / (1.0 - rho))
            q = d["q0"] * float(bix.get((ms, b), 1.0)) * (pb / r) ** rho
            for c, x in zip(d["comm"], q):
                if c:
                    out[c] = out.get(c, 0.0) + float(x)
        return out

    def _feed_byproduct_params(self) -> dict:
        """CAPRI's residual feeds (MaprFeed_; tools/build/build_feed_byproducts.py): per product the EU's 2030 output and
        its parent commodities' weights in the parents' food and processing use (food) or biofuel processing.
        {"products": {product: {"prod0": kt, "parts": [(commodity, use, weight)]}}, "parents": set} or {}."""
        cached = getattr(self, "_fbyp_cache", None)
        if cached is not None:
            return cached
        out = {}
        try:
            from pathlib import Path as _P
            f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "market" / "feed_byproducts.csv"
            t = pd.read_csv(f)
            prods = {}
            for p, g in t.groupby("product"):
                if p not in self.commodities:
                    continue
                ws = float(g["weight"].sum())                 # renormalised (the file's weights are rounded)
                prods[p] = {"prod0": float(g["prod0_kt"].iloc[0]),
                            "parts": [(str(r.commodity), str(r.use), float(r.weight) / ws) for r in g.itertuples()]}
                # per EU market region: output split by CAPRI's member-state production of the residual feed; the
                # parents' weights from the region's own food + processing (biofuel processing) use of each parent
                reg = {}
                for rg, f in self.eu_split(p, "prod_kt").items():
                    if not self.eu_blocks:
                        reg[rg] = {"prod0": prods[p]["prod0"], "parts": prods[p]["parts"]}
                        continue
                    parts = []
                    for r_ in g.itertuples():
                        it = ("biof_kt",) if str(r_.use) == "biofuel" else ("hcon_kt", "proc_kt")
                        tb = self._eu_ms_balance()
                        k = (rg, str(r_.commodity))
                        vb = sum(float(tb.at[k, x]) for x in it) if k in tb.index else 0.0
                        parts.append((str(r_.commodity), str(r_.use), vb))
                    tot = sum(x for _, _, x in parts)
                    reg[rg] = {"prod0": prods[p]["prod0"] * f,
                               "parts": [(c, u, x / tot) for c, u, x in parts] if tot > 0 else prods[p]["parts"]}
                prods[p]["reg"] = reg
            if prods:
                out = {"products": prods,
                       "parents": {c for d in prods.values() for c, _, _ in d["parts"] if c in self.commodities}}
        except Exception:
            out = {}
        self._fbyp_cache = out
        return out

    def eu_feed_byproduct_output(self, region: Optional[str] = None) -> Dict[str, float]:
        """EU output of the residual feeds (CAPRI MaprFeed_): prod0 x sum over the parents of weight x the
        parent's current food response (food and processing use) or biofuel feedstock use relative to the
        reference, from the last demand evaluation (1 before any). region: one EU market region (default: the
        first; with one EU region, the EU)."""
        region = region or self.EU[0]
        fp = self._feed_byproduct_params()
        fr = (getattr(self, "_eu_food_ratio", None) or {}).get(region, {})
        br = (getattr(self, "_eu_biof_ratio", None) or {}).get(region, {})
        out = {}
        for p, d in (fp.get("products") or {}).items():
            dr = (d.get("reg") or {}).get(region, d)
            x = sum(w * float((br if use == "biofuel" else fr).get(c, 1.0)) for c, use, w in dr["parts"])
            out[p] = dr["prod0"] * x
        return out

    def _apply_feed_byproduct_supply(self, S: pd.DataFrame) -> None:
        for reg in self.EU:
            if reg not in S.index:
                continue
            for p, q in self.eu_feed_byproduct_output(reg).items():
                if p in S.columns:
                    S.at[reg, p] = max(0.0, q)

    #: Human consumption from CAPRI's Generalised Leontief demand system (arm/market_model.gms:826-916) per
    #: behavioural region (EU member states, non-EU countries and country groups), with its cross-price and income
    #: terms; parameters from CAPRI's 2030 calibration (tools/build/build_gl_demand.py). Off: the earlier own-price
    #: constant-elasticity food response (no cross-price terms).
    food_demand_gl = setting("market.food_demand_gl")

    def _gl_params(self) -> dict:
        """CAPRI's GL food demand per behavioural region, grouped by model region.

        Returns {model region: [rms entries]} with, per CAPRI region: goods' model commodity column (-1: a good the
        model has no market for; its price stays at CAPRI's, as INPE's), d, B (symmetric), consumer prices at the
        calibration point (EUR/kg), income per head Y, inhabitants; plus "hs": (region, commodity) -> CAPRI's human
        consumption share of total use, and "x0": the demand at the calibration point per (region, commodity)."""
        cached = getattr(self, "_gl_cache", None)
        if cached is not None:
            return cached
        out = {}
        try:
            from pathlib import Path as _P
            d = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "market"
            goods = pd.read_csv(d / "gl_demand_goods.csv", keep_default_na=False, na_values=[""])
            bb = pd.read_csv(d / "gl_demand_b.csv")
            regs = pd.read_csv(d / "gl_demand_regions.csv").set_index("rms")
            Cc = {c: j for j, c in enumerate(self.commodities)}
            Rr = {r: i for i, r in enumerate(self.regions)}
            groups, hcon, use, x0 = {}, {}, {}, {}
            bgr = {r: g for r, g in bb.groupby("rms")}
            for rms, g in goods.groupby("rms", sort=True):
                mr = str(g["model_region"].iloc[0])
                if mr == "EU27" and self.eu_blocks:
                    mr = self.eu_region_of_ms(rms) or mr
                if mr not in Rr or rms not in regs.index or rms not in bgr:
                    continue
                names = list(g["good"])
                idx = {n: k for k, n in enumerate(names)}
                n = len(names)
                B = np.zeros((n, n))
                for i_, j_, v in bgr[rms][["i", "j", "b"]].itertuples(index=False):
                    if i_ in idx and j_ in idx:
                        B[idx[i_], idx[j_]] = v
                        B[idx[j_], idx[i_]] = v
                p0 = g["cpri"].to_numpy(dtype=float) / 1000.0
                if not np.all(p0 > 0):
                    continue
                col = np.array([Cc.get(str(m), -1) if isinstance(m, str) and m else -1
                                for m in g["model_commodity"]], dtype=int)
                e = {"col": col, "d": g["d"].to_numpy(dtype=float), "B": B, "p0": p0,
                     "Y": float(regs.at[rms, "Y"]), "inha": float(regs.at[rms, "inha"]), "rms": rms,
                     "good": np.array(names), "hcon": g["hcon"].to_numpy(dtype=float),
                     "use": g["use"].to_numpy(dtype=float)}
                e["d_cal"] = e["d"].copy()
                e["x0"] = self._gl_eval(e, p0, 1.0)
                groups.setdefault(mr, []).append(e)
                for k, j in enumerate(col):
                    if j < 0:
                        continue
                    key = (mr, int(j))
                    hcon[key] = hcon.get(key, 0.0) + float(g["hcon"].iloc[k])
                    use[key] = use.get(key, 0.0) + float(g["use"].iloc[k])
                    x0[key] = x0.get(key, 0.0) + float(e["x0"][k])
            out = {"groups": groups,
                   "hs": {k: min(1.0, hcon[k] / use[k]) for k in hcon if use[k] > 0 and hcon[k] > 0},
                   "x0": x0, "x0_cal": dict(x0), "use": use}
        except Exception as exc:  # never silent: the earlier food response is used instead
            import warnings as _w
            _w.warn(f"GL food demand not available ({exc}); own-price food response used", RuntimeWarning)
            out = {}
        self._gl_cache = out
        return out

    @staticmethod
    def _gl_eval(e: dict, p: np.ndarray, ir: float) -> np.ndarray:
        """CAPRI's GL demand of one region (1000 t): x_i = [G_i/G (Y - F) + d_i] INHA / 1000."""
        sq = np.sqrt(p)
        G = float(sq @ e["B"] @ sq)
        Gi = (e["B"] @ sq) / sq
        F = float(e["d"] @ p)
        return (Gi / G * (e["Y"] * ir - F) + e["d"]) * e["inha"] / 1000.0

    #: CAPRI's re-calibration of the GL commitments to given quantities and prices (arm/recalibrate_commitments.gms,
    #: trim_gl_commits.gms): the commitments d are moved as little as possible (least squares) so that the system
    #: reproduces the model's base human consumption at the calibration prices; b and income stay. The model's base
    #: use per region and commodity sets the target: CAPRI's human consumption of each behavioural region scaled by
    #: the ratio of the model's base use to CAPRI's use of the model region. False: CAPRI's 2030 commitments, the
    #: GL applied as a ratio to the model's base.
    gl_refit_commitments = setting("market.gl_refit_commitments")

    def _gl_refit(self, D0c: np.ndarray) -> None:
        """Re-fit the commitments of every behavioural region to the model's base use D0c (regions x commodities),
        as CAPRI's m_trimGLCommits: min sum (d - d_CAPRI)^2 s.t. x_i(p0, d) = target_i for the goods with human
        consumption (raw milk and INPE free; INPE absorbs the change in spending). The constraints are linear in d:
        d_i - a_i sum_k p_k d_k = q_i - a_i Y, a_i = G_i / G, so the least-squares solution is exact."""
        prm = self._gl_params()
        Rr = {r: i for i, r in enumerate(self.regions)}
        kfac = {}
        for (mr, j), u in prm["use"].items():
            if u > 0:
                kfac[(mr, j)] = float(D0c[Rr[mr], j]) / u
        info = []
        x0 = {}
        for mr, ents in prm["groups"].items():
            i = Rr[mr]
            for e in ents:
                p, d0, col = e["p0"], e["d_cal"], e["col"]
                sq = np.sqrt(p)
                G = float(sq @ e["B"] @ sq)
                a = (e["B"] @ sq) / sq / G
                k = np.array([kfac.get((mr, int(j)), 1.0) if j >= 0 else 1.0 for j in col])
                q = e["hcon"] * k * 1000.0 / e["inha"]                      # per head, kg
                con = (e["hcon"] > 1e-6) & (np.abs(a) > 0) & (e["good"] != "INPE") & (e["good"] != "MILK")
                A = np.where(con[:, None], -np.outer(a, p), 0.0)[con]
                A[np.arange(con.sum()), np.where(con)[0]] += 1.0
                b = (q - a * e["Y"])[con]
                r = b - A @ d0
                d = d0 + A.T @ np.linalg.solve(A @ A.T, r)
                e["d"] = d
                x = self._gl_eval(e, p, 1.0)
                e["x0"] = x
                err = float(np.max(np.abs(x[con] - (q * e["inha"] / 1000.0)[con]) / np.maximum(1e-9, x[con]))) if con.any() else 0.0
                info.append((e["rms"], mr, err, float(np.max(np.abs(d - d0)[con] / np.maximum(np.abs(d0[con]), 1e-9))) if con.any() else 0.0))
                for kk, j in enumerate(col):
                    if j >= 0:
                        x0[(mr, int(j))] = x0.get((mr, int(j)), 0.0) + float(x[kk])
        prm["x0"] = x0
        self.gl_refit_info = info

    def gl_food_ratio(self, PR: np.ndarray, ref: np.ndarray, ir: float = 1.0, D0c: np.ndarray = None):
        """Human consumption relative to the calibration point per (model region, commodity), and CAPRI's human
        consumption share of use. Consumer prices move additively with the model's domestic price (CAPRI
        Cpri_: Armington price + margin): p = CPRI0 + (PR - 1) x reference price."""
        prm = self._gl_params() if self.food_demand_gl else {}
        if not prm:
            return None, None
        if D0c is not None and self.gl_refit_commitments:
            key = getattr(self, "_gl_refit_key", None)
            if key is None or key.shape != D0c.shape or not np.array_equal(key, D0c):
                self._gl_refit(D0c)
                self._gl_refit_key = D0c.copy()
        Rr = {r: i for i, r in enumerate(self.regions)}
        num = np.zeros_like(PR, dtype=float)
        for mr, ents in prm["groups"].items():
            i = Rr[mr]
            for e in ents:
                col = e["col"]
                p = e["p0"].copy()
                m = col >= 0
                p[m] = p[m] + (PR[i, col[m]] - 1.0) * ref[i, col[m]] / 1000.0
                p = np.maximum(p, 0.05 * e["p0"])
                x = self._gl_eval(e, p, ir)
                np.add.at(num[i], col[m], np.maximum(x[m], 0.0))
        GLR = np.ones_like(num)
        HS = np.zeros_like(num)
        for (mr, j), v0 in prm["x0"].items():
            i = Rr[mr]
            if v0 > 0:
                GLR[i, j] = num[i, j] / v0
                HS[i, j] = prm["hs"].get((mr, j), 0.0)
        return GLR, HS

    def _feed_demand_params(self) -> dict:
        """(region, feed commodity) -> feed share and p_ElasFeed elasticities (non-EU)."""
        cached = getattr(self, "_fdp_cache", None)
        if cached is not None:
            return cached
        out = {}
        try:
            import json as _json
            from pathlib import Path as _P
            f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "market" / "feed_demand_nonEU.json"
            for key, v in _json.load(open(f))["parameters"].items():
                r, c = key.split("|")
                if r in self.regions and r not in self.EU and r != "EU27" and c in self.commodities:
                    out[(r, c)] = {"feed_share": float(v["feed_share"]),
                                   "elasticities": {k: float(x) for k, x in v["elasticities"].items() if k in self.commodities}}
        except Exception:
            out = {}
        self._fdp_cache = out
        return out

    #: CAPRI's processing demand functions (arm/market_model.gms ProcNQ_; tools/build/build_processing_nq.py): oilseed
    #: crushing linear in the crushing margins with CAPRI's Hessian (cross terms among the oilseeds), processing of
    #: the other products linear in the prices (cross terms among the vegetable oils). False: the earlier own-margin
    #: crushing elasticity and own-price response of processing.
    processing_nq = setting("market.processing_nq")
    #: products whose processing has its own block: dairy (fixed processing in the dairy block), biofuels (the
    #: biofuel market's non-fuel processing), raw milk
    _PROC_NQ_SKIP = frozenset({"MILK", "BUTR", "SKIM", "CHES", "WHEY", "FRMI", "CREM", "COCM", "WMIO", "CASE",
                               "BIOE", "BIOD"})

    def _proc_nq_params(self) -> dict:
        """CAPRI's processing Hessian summed per model region (the behavioural regions of a region share its prices),
        CAPRI's processing share of use per (region, commodity). {} when off or the files are absent."""
        if not self.processing_nq:
            return {}
        cached = getattr(self, "_procnq_cache", None)
        if cached is not None:
            return cached
        out = {}
        try:
            from pathlib import Path as _P
            d = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "market"
            hh = pd.read_csv(d / "processing_nq_hessian.csv", keep_default_na=False, na_values=[""])
            bb = pd.read_csv(d / "processing_nq_base.csv", keep_default_na=False, na_values=[""])

            def mreg(rms, mr):
                if mr == "EU27" and self.eu_blocks:
                    return self.eu_region_of_ms(rms) or mr
                return mr
            # ProcNQ_ divides H by the price of the non-agricultural good, DATA(RMS,"PPri","Inpe","CUR")
            inpe_rms = bb.groupby("rms")["inpe"].first().to_dict()
            H = {}
            for r in hh.itertuples(index=False):
                R = mreg(r.rms, r.model_region)
                if R not in self.regions or r.x not in self.commodities or r.y not in self.commodities:
                    continue
                inpe = float(inpe_rms[r.rms])
                k = H.setdefault(R, {})
                k[(r.x, r.y)] = k.get((r.x, r.y), 0.0) + float(r.h) / inpe
                if r.x != r.y:
                    k[(r.y, r.x)] = k.get((r.y, r.x), 0.0) + float(r.h) / inpe
            pr, us = {}, {}
            for r in bb.itertuples(index=False):
                R = mreg(r.rms, r.model_region)
                pr[(R, r.commodity)] = pr.get((R, r.commodity), 0.0) + float(r.proc_kt)
                us[(R, r.commodity)] = us.get((R, r.commodity), 0.0) + float(r.use_kt)
            # the share of use CAPRI's processing function carries (ProcNQ_ moves the processing quantity itself); at
            # most the whole use (where CAPRI's data have processing above use); before 23 October 2026 capped at 0.98
            share = {k: min(1.0, pr[k] / us[k]) for k in pr if us.get(k, 0.0) > 0 and pr[k] > 0}
            out = {"H": H, "share": share}
        except Exception as exc:
            import warnings as _w
            _w.warn(f"CAPRI processing functions not available ({exc}); own-price processing used", RuntimeWarning)
            out = {}
        self._procnq_cache = out
        return out

    def _crush_params(self) -> dict:
        """(region, seed) -> base crush, yields, elasticity and base margin terms.

        CAPRI data (crushing_parameters.csv, tools/build/build_crushing_parameters.py): crush = the seed's industrial use,
        yields = oil and cake production / crush, elasticity = p_ElasProc. Every
        pair takes CAPRI's own yields, as CAPRI's market does: a band that dropped
        five pairs whose yields look implausible (UKR, PAK, ZAF rapeseed, PAK
        soybeans: oil + cake 1.2-1.7 t per t of seed crushed; JPN sunflower) was
        removed 23 October 2026 (no proxies; the numbers had no source).
        """
        # The cache is keyed on what it depends on - the BASE prices and tariffs
        # of the oilseed-chain commodities. A plain cache built on first use
        # went stale when that use fell in a run with shifted base prices
        # (a long-lived model then disagreed with a fresh one: the projection
        # null-trajectory test caught a 0.04% difference).
        _cc = [c for c in ("RAPE", "SUNF", "SOYA", "RAPO", "SUNO", "SOYO", "RAPC", "SUNC", "SOYC")
               if c in self.commodities]
        try:
            _key = (tuple(round(float(self.world_prices_base.get(c, 0.0)), 9) for c in _cc),
                    tuple(map(tuple, self.tariffs.reindex(columns=_cc).fillna(0.0).round(9).values.tolist())),
                    tuple(round(float((getattr(self, "_eu_aligned_use", None) or {}).get(rg, {}).get(c, 0.0)), 6)
                          for rg in self.EU for c in ("RAPE", "SUNF", "SOYA")))
        except Exception:
            _key = None
        cached = getattr(self, "_crush_cache", None)
        if cached is not None and _key is not None and getattr(self, "_crush_cache_key", None) == _key:
            return cached
        self._crush_cache_key = _key
        out = {}
        from pathlib import Path as _P
        f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "market" / "crushing_parameters.csv"
        if not f.exists():
            raise FileNotFoundError(f"{f} is missing (python tools/build/build_crushing_parameters.py)")
        _t = pd.read_csv(f, keep_default_na=False)
        raw = {f"{x['region']}|{x['seed']}": {k: (float(x[k]) if x[k] != "" else None)
                                              for k in ("crush_kt", "oil_yield", "cake_yield", "elasticity",
                                                        "crush_share_of_use")}
               for x in _t.to_dict("records")}
        base_dom = self.domestic_prices(self.world_prices_base)
        for key, v in raw.items():
            r, s = key.split("|")
            if (r not in self.regions and not (r == "EU27" and self.eu_blocks)) or s not in self.CRUSH_CHAINS:
                continue
            yo, yc = float(v["oil_yield"]), float(v["cake_yield"])
            o, c = self.CRUSH_CHAINS[s]
            q0 = float(v["crush_kt"])
            _ov = (getattr(self, "_crush_q0_override", None) or {}).get((r, s))
            if _ov is not None:
                q0 = float(_ov)       # bilateral market: CAPRI's cake production of the market year / yield
            if r == "EU27" and self.eu_blocks:
                # CAPRI's two trade blocks: the EU parameters for each block, its crush share of seed use from
                # CAPRI's member-state processing and use (eu_ms_balance_2030.csv); base crush = share x the
                # block's aligned seed use (below)
                tb = self._eu_ms_balance()
                for rb in self.EU:
                    k = (rb, s)
                    if k not in tb.index or float(tb.at[k, "use_kt"]) <= 0:
                        continue
                    shb = float(tb.at[k, "proc_kt"]) / float(tb.at[k, "use_kt"])
                    _al = (getattr(self, "_eu_aligned_use", None) or {}).get(rb, {})
                    bb = float(_al.get(s, self.base_consumption.at[rb, s] if s in self.base_consumption.columns else 0.0))
                    if shb <= 0 or bb <= 0:
                        continue
                    ps, po, pc = (float(base_dom.at[rb, x]) for x in (s, o, c))
                    gross = yo * po + yc * pc
                    out[(rb, s)] = dict(q0=shb * bb, yo=yo, yc=yc, eps=float(v["elasticity"]),
                                        m0=gross - ps, gross=max(gross, 1.0))
                continue
            if r == "EU27":
                # EU base crush = CAPRI's crush SHARE of EU seed use x the
                # market's own EU base seed use. With all regions modelled
                # this equals CAPRI's crush exactly; with a subset it scales
                # consistently (on 12 regions EU rapeseed use is 581 kt -
                # a fixed 20,955 kt crush made non-crush use negative).
                share = float(v.get("crush_share_of_use") or 0.0)
                # the ALIGNED EU seed use: base_consumption is later divided
                # by the calibration factor (EU exemption), which shifted the
                # base crush after calibration and moved base prices
                _al = (getattr(self, "_eu_aligned_use", None) or {}).get("EU27", {})
                b = float(_al.get(s, self.base_consumption.at["EU27", s] if s in self.base_consumption.columns else 0.0))
                if share > 0 and b > 0:
                    q0 = share * b
            ps, po, pc = (float(base_dom.at[r, x]) for x in (s, o, c))
            gross = yo * po + yc * pc               # CAPRI: seed price + margin
            out[(r, s)] = dict(q0=q0, yo=yo, yc=yc, eps=float(v["elasticity"]),
                               m0=gross - ps, gross=max(gross, 1.0))
        self._crush_cache = out
        return out

    def _align_eu_crush_products(self, base_supply):
        """EU oil and cake base production = EU base crush x yields.

        The EU base crush follows the market's own EU base seed use (CAPRI's
        crush share x that use), so EU oil and cake base production must follow
        it too - otherwise crushing supplies less (or more) than the market was
        calibrated on and base prices move (rapeseed oil +1.1% once the EU seed
        rows were put on CAPRI's FAO_agg basis).
        """
        cp = self._crush_params()
        tot = {}
        for (r, s), p in cp.items():
            if r not in self.EU:
                continue
            o, c = self.CRUSH_CHAINS[s]
            tot[(r, o)] = tot.get((r, o), 0.0) + p["q0"] * p["yo"]
            tot[(r, c)] = tot.get((r, c), 0.0) + p["q0"] * p["yc"]
        for (r, prod), v in tot.items():
            if prod in self.base_production.columns and v > 0:
                self.base_production.at[r, prod] = v
                if prod in base_supply.columns and r in base_supply.index:
                    base_supply.at[r, prod] = v
        return base_supply

    def crush_quantities(self, dom_prices) -> dict:
        """Crush per (region, seed) at the given domestic prices (CAPRI ProcNQ_).

        CAPRI's crushing function is linear in the crushing margin
        (margin = oil yield x oil price + cake yield x cake price - seed price),
        with its elasticity expressed relative to the seed's gross value per
        tonne (seed price + margin), not to the small net margin:
            crush = q0 x [1 + eps x (margin - margin0) / gross0] ,
        floored at 1% of base (CAPRI's ProcFudge_ keeps processing positive).
        """
        out = {}
        _ri = {r: i for i, r in enumerate(dom_prices.index)}
        _ci = {c: j for j, c in enumerate(dom_prices.columns)}
        _v = dom_prices.values
        cp = self._crush_params()
        dm = {}
        for (r, s), p in cp.items():
            o, c = self.CRUSH_CHAINS[s]
            i = _ri[r]
            m = p["yo"] * float(_v[i, _ci[o]]) + p["yc"] * float(_v[i, _ci[c]]) - float(_v[i, _ci[s]])
            dm[(r, s)] = m - p["m0"]
        Hn = (self._proc_nq_params() or {}).get("H", {})
        for (r, s), p in cp.items():
            Hr = Hn.get(r, {})
            if (s, s) in Hr and Hr[(s, s)] > 0:
                # CAPRI ProcNQ_: crush moves by the Hessian times the change of every oilseed's crushing margin
                q = p["q0"] + sum(Hr.get((s, y), 0.0) * dm[(r, y)] for y in self.CRUSH_CHAINS if (r, y) in dm)
            else:
                q = p["q0"] * (1.0 + p["eps"] * dm[(r, s)] / p["gross"])
            out[(r, s)] = max(0.01 * p["q0"], q)
        return out

    def _region_supply_elas(self, regions, cols, el) -> np.ndarray:
        """regions x cols own-price supply elasticities: CAPRI's per non-EU region (capri_data/2017/market/
        supply_elas_region.csv), else 0 - where CAPRI has no p_elasSupp for a region and product its supply Hessian
        p_hessNQSupp has no term (arm/market1.gms), so the supply does not respond to the price. Until 23 October 2026
        those cells took the product's EU median or the Armington eps column (no CAPRI source; PROXY_AUDIT S176
        note). The processed products' supply is set by their blocks (crushing, dairy, biofuels) where CAPRI has
        them. EU rows: el (their supply comes from the supply models)."""
        key = (tuple(regions), tuple(cols), tuple(np.round(el.reindex(cols).to_numpy(dtype=float), 12)))
        cache = getattr(self, "_reg_elas_cache", None)
        if cache is not None and cache[0] == key:
            return cache[1]
        EV = np.tile(el.reindex(cols).to_numpy(dtype=float), (len(regions), 1))
        if getattr(self, "use_region_supply_elas", True):
            eu_ = set(self.EU)
            for i_, r_ in enumerate(regions):
                if r_ not in eu_:
                    EV[i_, :] = 0.0
            from pathlib import Path as _P
            f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "market" / "supply_elas_region.csv"
            if f.exists():
                ri = {r: i for i, r in enumerate(regions)}
                ci = {c: j for j, c in enumerate(cols)}
                eu = set(self.EU)
                for r_, c_, e_ in pd.read_csv(f)[["region", "commodity", "elasticity"]].itertuples(index=False):
                    if r_ in ri and c_ in ci and r_ not in eu:
                        EV[ri[r_], ci[c_]] = float(e_)
        self._reg_elas_cache = (key, EV)
        return EV

    #: non-EU supply with CAPRI's own-price elasticity per region (True) or one value per product for every region
    #: (False: CAPRI's EU median p_elasSupp, else the Armington eps; the market before 20 October 2026)
    use_region_supply_elas = setting("market.use_region_supply_elas")
    #: CAPRI's crushing margin (ProcMargO_): oil and cake at their producer prices, the seed at its Armington price
    #: (False: all three at Armington price ratios, the market before 20 October 2026)
    crush_margin_producer_prices = setting("market.crush_margin_producer_prices")

    def supply_response(
        self,
        world_prices: pd.Series,
        exogenous_supply: Optional[pd.DataFrame] = None,
        region_ratio: Optional[pd.DataFrame] = None,
        crush_dom: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Supply quantities by region and commodity (1000 t).
        If exogenous_supply is given (from supply module, one row per country), use it for EU27 (or the EU
        market regions) and, for Norway's rows, for its own market region NOR (SUP_NONEU_REGIONS).
        Otherwise, apply supply elasticity to price signal.

        region_ratio (bilateral market): each region's own market price relative to base, region x commodity; the
        supply elasticity then applies to the region's own price, the EU's supply-module output is
        anticipated against the EU price farmers last saw, and crushing and the dairy blocks see the
        regional prices (crush_dom: the price levels the crushers face).
        """
        # the supply models' output: the EU's countries, and the non-EU market regions with supply models (Norway)
        exo_all = exogenous_supply
        exogenous_supply, exo_sup = self._split_supply(exo_all)
        self._sup_active = set(exo_sup)
        sup_cols = {}
        if exogenous_supply is not None:
            # Only override the EU27 row with the supply-module output; keep
            # all other trade regions (USA, BRA, CHN, ROW, ...) at their
            # calibrated base production. Otherwise global supply collapses to
            # the EU subset and excess demand explodes.
            supply = self.base_production.copy()
            _ex = (self.eu_rows(exogenous_supply) if self.eu_blocks
                   else pd.DataFrame([exogenous_supply.sum(axis=0)], index=["EU27"]))
            # Norway (CAPRI RMSSUP outside the EU, K56): its market supply is its supply models' output, as the EU's
            for reg, ser in exo_sup.items():
                if reg not in supply.index:
                    continue
                for comm, v in ser.items():
                    if comm in supply.columns and float(v) > 1e-6:
                        supply.at[reg, comm] = float(v)
                        sup_cols.setdefault(reg, set()).add(comm)
            for comm in exogenous_supply.columns:
                if comm not in supply.columns:
                    continue
                for reg in self.EU:
                    eu_val = float(_ex.at[reg, comm]) if reg in _ex.index else 0.0
                    # 1e-6 (1 kg): solver noise in regions that do not grow the product is not supply. In a run on a
                    # subset of regions (tests) a product none of them grows came back as 1e-15 and replaced the EU's
                    # base supply, and the EU price ran to 1e7 (K16)
                    if eu_val > 1e-6 and reg in supply.index:
                        supply.at[reg, comm] = eu_val
        else:
            supply = self.base_production.copy()

        # Own-price supply elasticities from CAPRI's calibrated market model
        # (elas1717 p_elasSupp, EU medians). These replace the crop-oriented
        # Armington eps column, which stood in a blanket 0.15-0.25 for every
        # commodity -- including livestock, where CAPRI's real values are
        # 0.55-0.76. Commodities not in the file keep the eps fallback.
        real_supply = getattr(self, "_real_supply_elas", None)
        if real_supply is None:
            import json as _json
            from pathlib import Path as _P
            # (was resolved from the working directory, and a failure fell back silently to the eps column)
            _f = _P(__file__).resolve().parents[2] / "capri_data" / "sources" / "arm" / "supply_elas_eu_all.json"
            if not _f.exists():                             # no silent fallback (23 October 2026)
                raise FileNotFoundError("capri_data/sources/arm/supply_elas_eu_all.json (CAPRI's EU p_elasSupp) is missing")
            real_supply = _json.loads(open(_f).read())
            self._real_supply_elas = real_supply

        if "eps" not in self.armington.columns:            # no stand-in (removed 23 October 2026: 0.25)
            raise ValueError("armington_params.csv has no eps column")
        eps = self.armington["eps"]

        # Vectorised over commodities; arithmetic unchanged.
        ratio = pd.Series({
            c: float(world_prices.get(c, self.world_prices_base[c]))
               / max(float(self.world_prices_base[c]), 0.01)
            for c in self.commodities})
        el = pd.Series({
            c: (float(real_supply[c]) if c in real_supply else float(eps[c]))
            for c in self.commodities})
        cols = [c for c in self.commodities if c in supply.columns]
        # each non-EU region's own-price elasticity from CAPRI's market model (p_elasSupp "CAL" of its CAPRI regions,
        # production-weighted; tools/build/build_supply_elas_nonEU.py; KNOWN_ISSUES K54-3); the per-product value above
        # where CAPRI has none (processed products) and for the EU rows (their supply comes from the supply models)
        EV = self._region_supply_elas(list(supply.index), cols, el)
        if region_ratio is None:
            fac = ratio.reindex(cols).to_numpy(dtype=float)[None, :] ** EV
            supply[cols] = np.maximum(supply[cols].to_numpy(dtype=float) * fac, 0.0)
        else:
            # in arrays (pandas arithmetic here was a sizeable share of each market evaluation; same values)
            rr = region_ratio.reindex(index=supply.index, columns=cols).to_numpy(dtype=float)
            rr = np.maximum(np.where(np.isnan(rr), 1.0, rr), 1e-6)
            ev = el.reindex(cols).to_numpy(dtype=float)
            fac = rr ** EV
            # the EU market regions' supply before the price response (the supply models' latest output): EU27, or
            # each of CAPRI's two trade blocks
            s_exo_eu = ({r_: supply.loc[r_, cols].astype(float).copy() for r_ in self.EU if r_ in supply.index}
                        if exogenous_supply is not None else None)
            _sv_eu = {}
            seen_all = getattr(self, "_eu_price_seen", None)
            for reg in self.EU:
                if reg not in supply.index:
                    continue
                ie_ = list(supply.index).index(reg)
                # the price the supply models last saw: one Series (EU), or regions x commodities (EU market regions)
                seen = (seen_all.loc[reg] if isinstance(seen_all, pd.DataFrame) and reg in seen_all.index
                        else (seen_all if isinstance(seen_all, pd.Series) else None))
                sv = (np.maximum(np.nan_to_num(seen.reindex(cols).to_numpy(dtype=float), nan=1.0), 0.2)
                      if seen is not None else np.ones(len(cols)))
                # products the EU supplies through CAPRI's market supply function, not a supply-model activity
                # (other vegetable oils): their EU supply responds to the EU price against base, not against the
                # price the supply models last saw (that anticipation would vanish at convergence and hold them at base)
                for j, c in enumerate(cols):
                    if c in self.EU_MARKET_SUPPLY:
                        sv[j] = 1.0
                fac[ie_] = (rr[ie_] / sv) ** ev
                _sv_eu[reg] = sv
            # the non-EU market regions with supply models (Norway): the products of their supply models are
            # anticipated against the prices those models last saw (own market's prices), with the region's own
            # CAPRI elasticity (p_elasSupp of NO000000, supply_elas_region.csv); the products without a supply-model
            # activity (fish, ...) keep CAPRI's market supply function at the region's price against base
            seen_sup = getattr(self, "_sup_price_seen", None) or {}
            _sv_sup = {}
            for reg, sc_ in sup_cols.items():
                i_ = list(supply.index).index(reg)
                seen = seen_sup.get(reg)
                sv = (np.maximum(np.nan_to_num(seen.reindex(cols).to_numpy(dtype=float), nan=1.0), 0.2)
                      if seen is not None else np.ones(len(cols)))
                _sv_sup[reg] = sv
                for j, c in enumerate(cols):
                    if c in sc_:
                        fac[i_, j] = (rr[i_, j] / sv[j]) ** EV[i_, j]
            s_exo_sup = {reg: supply.loc[reg, cols].astype(float).copy() for reg in sup_cols}
            supply[cols] = np.maximum(supply[cols].to_numpy(dtype=float) * fac, 0.0)
            # CAPRI's market supply function for the supply models' products (arm/market_model.gms ProdNQ_, the
            # Hessian measured on the supply models at the baseline, model._market_supply_hessian): linear in the
            # prices, through the supply models' latest output at the prices they saw
            # (arm/simu_calibration_to_supply.gms:360-368), with the cross-price terms; it replaces the own-price
            # anticipation for those products
            # one Hessian for EU27, or one per trade block (the sum of its member states', CAPRIModel._split_hessian)
            _hs = getattr(self, "supply_hessian", None) or {}
            _hreg = {"EU27": _hs.get("eu")} if not self.eu_blocks else dict(_hs.get("blocks") or {})
            _hcache = getattr(self, "_hess_cache", None)
            if not isinstance(_hcache, dict):
                _hcache = {}
            for reg_, H in _hreg.items():
                if H is None or s_exo_eu is None or not len(H) or reg_ not in s_exo_eu or reg_ not in _sv_eu:
                    continue
                ie_ = list(supply.index).index(reg_)
                ck = (id(H), tuple(cols), tuple(exogenous_supply.columns))
                hc = _hcache.get(reg_)
                if hc is None or hc[0] != ck:
                    ex_cols = set(exogenous_supply.columns)
                    xs = [x for x in H.index if x in cols and x in ex_cols]
                    hc = (ck, xs, [cols.index(x) for x in xs],
                          H.reindex(index=xs, columns=cols).fillna(0.0).to_numpy(dtype=float))
                    _hcache[reg_] = hc
                _, xs, xj, Hm = hc
                if xs:
                    s0 = s_exo_eu[reg_].to_numpy(dtype=float)[xj]
                    q = s0 + Hm @ (rr[ie_] - _sv_eu[reg_])
                    keep = s0 > 1e-6
                    vals = supply.loc[reg_, cols].to_numpy(dtype=float).copy()
                    vals[np.asarray(xj)[keep]] = np.maximum(q[keep], 0.0)
                    supply.loc[reg_, cols] = vals
            self._hess_cache = _hcache
            # the same market supply function for Norway's supply models (its own Hessian, measured on its models)
            for reg, Hs in ((getattr(self, "supply_hessian", None) or {}).get("sup") or {}).items():
                if reg not in sup_cols or Hs is None or not len(Hs):
                    continue
                i_ = list(supply.index).index(reg)
                xs = [x for x in Hs.index if x in cols and x in sup_cols[reg]]
                if not xs:
                    continue
                xj = [cols.index(x) for x in xs]
                Hm = Hs.reindex(index=xs, columns=cols).fillna(0.0).to_numpy(dtype=float)
                s0 = s_exo_sup[reg].to_numpy(dtype=float)[xj]
                q = s0 + Hm @ (rr[i_] - _sv_sup[reg])
                keep = s0 > 1e-6
                vals = supply.loc[reg, cols].to_numpy(dtype=float).copy()
                vals[np.asarray(xj)[keep]] = np.maximum(q[keep], 0.0)
                supply.loc[reg, cols] = vals
        # CRUSHING: oil and cake supply = crush x yields (CAPRI ProcO_, Leontief)
        cp = self._crush_params()
        if cp:
            _cpn = getattr(self, "_crush_prices_now", None)
            crush = self.crush_quantities(_cpn if _cpn is not None else (crush_dom if crush_dom is not None else
                                          self.domestic_prices(world_prices, getattr(self, "_trade_scenario_now", None))))
            done = set()
            for (r, s), q in crush.items():
                o, c = self.CRUSH_CHAINS[s]
                for prod, y in ((o, cp[(r, s)]["yo"]), (c, cp[(r, s)]["yc"])):
                    if prod in supply.columns:
                        if (r, prod) not in done:
                            supply.at[r, prod] = 0.0
                            done.add((r, prod))
                        supply.at[r, prod] += q * y
        # DAIRY (CAPRI DairyNQ_, ProcMargM_, FatsProtBal_): EU raw milk is delivered to dairies, not
        # traded on the world milk market; the EU supply of butter, skimmed milk powder, cheese and
        # whey comes from the dairy block at the EU product prices and the milk delivered.
        if self._dairy_params() and all(r in supply.index for r in self.EU):
            if exogenous_supply is not None and "MILK" in exogenous_supply.columns and len(exogenous_supply):
                Sr = ({r: float(v) for r, v in self.eu_rows(exogenous_supply[["MILK"]])["MILK"].items()} if self.eu_blocks
                      else {"EU27": float(exogenous_supply["MILK"].sum())})
            else:
                Sr = {r: float(self.base_production.at[r, "MILK"]) for r in self.EU}
            S = sum(Sr.values())
            S0 = float(getattr(self, "_dairy_S0", None) or S)
            _m0 = getattr(self, "_dairy_S0_ms", None) or {}
            _m = self._milk_by_ms(exogenous_supply)
            _mr = ({ms: (_m[ms] / q0 if (q0 > 0 and ms in _m) else 1.0) for ms, q0 in _m0.items()} if (_m0 and _m)
                   else (S / S0 if S0 > 0 else 1.0))
            res = self.dairy_block(self._dairy_eu_prices(world_prices), _mr)
            if res is not None:
                for r in self.EU:
                    supply.at[r, "MILK"] = Sr[r]
                    for c, q in (res["market_supply_reg"].get(r) or {}).items():
                        if c in supply.columns:
                            supply.at[r, c] = max(0.0, q)
                self._eu_milk_supply_now = dict(Sr)
                self._dairy_last = res
        # NON-EU DAIRY (dairy Stage 4): each trade region's butter, SMP, cheese and whey from CAPRI's dairy
        # block with CAPRI's raw milk supply function, at the region's domestic prices; the market's base
        # quantities move with the block's relative change (the flat per-product elasticity is replaced)
        wpar = self._dairy_world_params()
        if wpar:
            dom = self.domestic_prices(world_prices, getattr(self, "_trade_scenario_now", None))
            d0 = getattr(self, "_dom0_cache", None)
            if d0 is None:
                d0 = self.domestic_prices(self.world_prices_base)
                self._dom0_cache = d0
            wl = {}
            self._sup_milk_now = {}
            for r, prm in wpar.items():
                if r not in supply.index:
                    continue
                if region_ratio is not None:
                    tr = {k: float(region_ratio.at[r, c]) if c in region_ratio.columns else 1.0
                          for k, c in self.DAIRY_TRADED.items()}
                else:
                    tr = {k: float(dom.at[r, c]) / float(d0.at[r, c]) if float(d0.at[r, c]) > 0 else 1.0
                          for k, c in self.DAIRY_TRADED.items()}
                # Norway (RMSSUP): raw milk delivered from its supply models (CAPRI market_model.gms ProdNQ_ NOTE2:
                # milk production in RMSSUP is covered by the supply models), its block's FMIL index from its herds;
                # the other regions: CAPRI's raw milk supply function
                mr_ = None
                m0_ = (getattr(self, "_sup_milk0", None) or {}).get(r)
                if r in exo_sup and "MILK" in exo_sup[r].index and m0_:
                    m_now = float(exo_sup[r]["MILK"])
                    mr_ = m_now / m0_
                    supply.at[r, "MILK"] = m_now
                    self._sup_milk_now[r] = m_now
                fi_ = float((getattr(self, "_fmil_index_sup", None) or {}).get(r, 1.0)) if mr_ is not None else 1.0
                res_r = self._dairy_solve(prm, tr, mr_, fi_, r)
                wl[r] = res_r
                for c, q in res_r["market_supply"].items():
                    q0 = res_r["market_supply0"][c]
                    if c in supply.columns and q0 > 1e-9:
                        supply.at[r, c] = max(0.0, float(self.base_production.at[r, c]) * q / q0)
            self._dairy_world_last = wl
        # BIOFUELS (CAPRI SupplyBiof_, MaprBiof_, prodQuantBiofBy_): each region's biofuel output is the sum over
        # its CAPRI market regions of first-generation output from the processing margin plus the fixed
        # non-agricultural, second-generation and exogenous output; without endogenous biofuel markets, the
        # reference output (first generation x biofuel_output_scale). DDGS comes from the ethanol plants' cereal
        # feedstocks in both cases (CAPRI keeps DDGS a market product without BIOF_M too).
        bm = self._biofuel_market_params()
        bp = self._biofuel_params()
        if bm or bp:
            d0 = self._dom0()
            par = None
            if crush_dom is not None:
                par = (crush_dom.reindex(index=d0.index, columns=d0.columns) / d0.where(d0 > 0)).fillna(1.0)
            st = self.biofuel_state(region_ratio, par)
            self._biof_state = st
            for (reg, fuel), q0 in (bm.get("prod0") or {}).items():
                if reg in supply.index and fuel in supply.columns:
                    supply.at[reg, fuel] = st["prod"].get((reg, fuel), q0)
            if "DDGS" in supply.columns:
                for reg, q in st["ddgs"].items():
                    if reg in supply.index:
                        supply.at[reg, "DDGS"] = q
        return supply

    def demand_response(
        self,
        domestic_prices: pd.DataFrame,
        world_prices: pd.Series,
    ) -> pd.DataFrame:
        """
        Consumption quantities by region and commodity (1000 t).

        Each block of use has its own response: feed (non-EU p_ElasFeed, EU feed bulks), crushing, biofuel
        feedstocks, dairy products, and human consumption from CAPRI's Generalised Leontief system per behavioural
        region (gl_food_ratio; own, cross-price and income terms) on CAPRI's HCON share of use. The rest of use
        (processing, industrial use, losses) keeps QD0 (P/P0)^eta, as all of food did before
        the GL (food_demand_gl False).
        """
        demand = pd.DataFrame(index=self.regions, columns=self.commodities, dtype=float)

        # No income change between a scenario and its baseline (comparative static, as CAPRI's scenario runs): the
        # GL system's income term stays at the baseline's (ir = 1). An Engel-elasticity proxy (0.1 / 0.5 / 0.3 by
        # group) applied to a GDP index was here; nothing ever set that index, so it never acted: removed (19 Oct 2026).

        # Real CAPRI demand elasticities (fao_agg p_demandElas), EU-average
        # own-price, mapped to model commodity codes. Overrides the generic eta.
        real_dem = getattr(self, "_real_demand_elas", None)
        if real_dem is None:
            real_dem = {}
            try:
                import json as _json
                from pathlib import Path as _P
                _b2 = _P(__file__).parent.parent.parent / "capri_data"
                from capri_mod.data.loaders import resolve_data_file
                f = resolve_data_file(_b2, "fao_demand_own_elas_eu.json")
                if f.exists():
                    raw = _json.load(open(f))
                    cmap = {"WHEA":"SWHE","BARL":"BARL","MAIZ":"CORN","BEEF":"BEEF",
                            "PORK":"PORK","POUM":"POUL","MILK":"MILK","BUTT":"BUTR",
                            "CHES":"CHES","SMIP":"SKIM","SOYA":"SOYA","SUGA":"SUGR"}
                    for sua, mc in cmap.items():
                        if sua in raw:
                            real_dem[mc] = raw[sua]
            except Exception:
                real_dem = {}
            self._real_demand_elas = real_dem

        # Vectorised; arithmetic unchanged.
        _noeta = [c for c in self.commodities if c not in real_dem and c not in self.armington.index]
        if _noeta:
            raise ValueError(f"no demand elasticity for market products {_noeta} (armington_params.csv eta)")
        eta = pd.Series({
            c: float(real_dem[c]) if c in real_dem else float(self.armington.at[c, "eta"])
            for c in self.commodities})
        cal = pd.Series({c: float(self._demand_cal_factor(c))
                         for c in self.commodities})
        wp0 = pd.Series({c: max(float(self.world_prices_base[c]), 0.01)
                         for c in self.commodities})
        fallback = pd.Series({c: float(world_prices.get(c, self.world_prices_base[c]))
                              for c in self.commodities})

        dp = domestic_prices.reindex(index=self.regions, columns=self.commodities)
        _dv = dp.to_numpy(dtype=float)
        if np.isnan(_dv).any():                         # fill by column in arrays (same values as fillna)
            dp = pd.DataFrame(np.where(np.isnan(_dv), fallback.reindex(self.commodities).to_numpy(dtype=float)[None, :],
                                       _dv), index=dp.index, columns=dp.columns)
        # PRICE RATIO against the BASE DOMESTIC price (world x base tariff), so
        # it is exactly 1 at base. It was taken against the base WORLD price,
        # which cut every tariff-protected region's base demand by
        # (1 + tariff)^eta before any change: EU beef (57.8% protection, eta
        # -0.4) at 0.833 of its aligned use - EU self-sufficiency 131% instead
        # of FAO's 109% - and the EU, exempt from the world calibration, kept
        # the error. A tariff change still enters through the domestic price.
        dom0 = getattr(self, "_dom0_cache", None)
        if dom0 is None:
            dom0 = self.domestic_prices(self.world_prices_base)
            self._dom0_cache = dom0
        # the reference prices and base use depend on static data only: built once per base (same values)
        _rc = getattr(self, "_demand_ref_cache", None)
        _bv = self.base_consumption.to_numpy()           # compared by value: the base is updated in place
        if (_rc is None or _rc[0] is not dom0 or _rc[1].shape != _bv.shape or not np.array_equal(_rc[1], _bv, equal_nan=True)
                or not wp0.equals(_rc[2]) or list(self.base_consumption.index) != _rc[5]
                or list(self.base_consumption.columns) != _rc[6]):
            ref = dom0.reindex(index=self.regions, columns=self.commodities)
            ref = ref.where(ref > 0).fillna(pd.DataFrame({c: [wp0[c]] * len(self.regions) for c in self.commodities},
                                                         index=self.regions))
            # a cell without base use has none (an invented 100 kt was used here; never hit with CAPRI's data)
            base = self.base_consumption.reindex(index=self.regions, columns=self.commodities).fillna(0.0)
            _rc = (dom0, _bv.copy(), wp0, ref, base, list(self.base_consumption.index),
                   list(self.base_consumption.columns))
            self._demand_ref_cache = _rc
        ref, base = _rc[3], _rc[4]
        price_ratio = dp / ref

        demand = (base.mul(cal, axis=1)
                      * price_ratio.pow(eta, axis=1))
        # NON-EU FEED DEMAND responds to feed prices (CAPRI p_ElasFeed): the
        # feed part of each region's use of a feed cereal or cake follows
        # prod_j (P_j / P0_j)^eps_j over the model's feed commodities (own and
        # cross), at that region's feed share of use (FAO_agg FEDM/DOMM). Prices
        # are relative to the BASE domestic price, so the term is exactly 1 at
        # base. EU feed demand is NOT handled here: in CAPRI it comes from the
        # supply models' ration choice.
        # ---- cell-level adjustments on NumPy arrays (same arithmetic and order
        # as the reference loops; pandas single-cell access cost ~0.1 s per call)
        R = {r: i for i, r in enumerate(self.regions)}
        Cc = {c: j for j, c in enumerate(self.commodities)}
        D = demand.values.astype(float).copy()
        Bv = base.values.astype(float)
        PR = price_ratio.values.astype(float)
        DPv = dp.values.astype(float)
        CAL = cal.reindex(self.commodities).values.astype(float)
        ETA = eta.reindex(self.commodities).values.astype(float)
        ir = 1.0
        # GL FOOD DEMAND (CAPRI arm/market_model.gms:826-916): the human-consumption part of each region's use
        # (CAPRI's HCON share of use) follows CAPRI's GL system with its cross-price and income terms; the blocks
        # below keep their own response for the other parts. OLDF is the factor each block applies to the part it
        # treats as food, SH the share of use the blocks give a response of their own (feed, crushing, biofuels);
        # the GL replaces OLDF on min(HCON share, 1 - SH) of use at the end.
        with np.errstate(divide="ignore", invalid="ignore"):
            OLDF = np.power(PR, ETA[None, :])
        SH = np.zeros_like(PR)
        GLR, HS = self.gl_food_ratio(PR, ref.values.astype(float), ir, D0c=Bv * CAL[None, :])
        fdp = self._feed_demand_params()
        if fdp:
            dom0 = getattr(self, "_dom0_cache", None)
            if dom0 is None:
                dom0 = self.domestic_prices(self.world_prices_base)
                self._dom0_cache = dom0
            D0 = dom0.reindex(index=self.regions, columns=self.commodities).values.astype(float)
            for (r, c), prm in fdp.items():
                i, j = R.get(r), Cc.get(c)
                if i is None or j is None:
                    continue
                sh = prm["feed_share"]
                ft = 1.0
                for jn, e in prm["elasticities"].items():
                    jj = Cc.get(jn)
                    if jj is not None and float(D0[i, jj]) > 0:
                        ft *= (float(DPv[i, jj]) / float(D0[i, jj])) ** e
                b = float(Bv[i, j]) * float(CAL[j])
                food = float(PR[i, j]) ** float(ETA[j])
                D[i, j] = b * ((1.0 - sh) * food + sh * ft)
                SH[i, j] = sh
        cp = self._crush_params()
        if cp:
            _cpn = getattr(self, "_crush_prices_now", None)
            crush = self.crush_quantities(_cpn if _cpn is not None else dp)
            for (r, sd), q in crush.items():
                i, j = R.get(r), Cc.get(sd)
                if i is None or j is None:
                    continue
                q0 = cp[(r, sd)]["q0"]; b = float(Bv[i, j])
                f = float(D[i, j]) / b if b > 0 else 0.0
                D[i, j] = max(0.0, (b - q0) * f + float(CAL[j]) * q0 + (q - q0))
                if b > 0:
                    SH[i, j] += q0 / b
        eu_eta = getattr(self, "_eu_eta_override", None)
        if eu_eta is None:
            eu_eta = {}
            try:
                import json as _json
                from pathlib import Path as _P
                _f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "market" / "eu_demand_elas_overrides.json"
                if _f.exists():
                    eu_eta = {k: float(v) for k, v in _json.load(open(_f)).items() if not k.startswith("_")}
            except Exception:
                eu_eta = {}
            self._eu_eta_override = eu_eta
        ie = R.get(self.EU[0])                         # the first EU market region (EU27 with one)
        fb = self._feed_bulk_params()
        self._eu_food_ratio = {}
        self._eu_feed_now = None
        self._eu_feed_now_reg = {}
        for _reg in self.EU:
            ie = R.get(_reg)
            if ie is None:
                continue
            if eu_eta:
                for _c, _e in eu_eta.items():
                    j = Cc.get(_c)
                    if j is not None:
                        D[ie, j] = (float(Bv[ie, j]) * float(CAL[j]) * float(PR[ie, j]) ** _e
                                   )
                        OLDF[ie, j] = float(PR[ie, j]) ** _e
            # EU FEED (CAPRI feedBlkPrice_, feedShareEqu_): the member states' feed bulks (cereals FCER, protein-rich
            # feed FPRO) follow their herds and rations (_feed_bulk_index, set from the supply models), and each
            # bulk is split into products with a CES on their prices (rho 6). The feed part of EU use of each product
            # (CAPRI's 2030 feed share) follows it; the rest keeps its food response.
            # Written as a correction of the row (feed part: bulk use instead of the food response), so that terms
            # added before (oilseed crushing, whose seeds are also fed whole: CAPRI's FOTH bulk) are kept; the same
            # as d0 ((1 - sh) rest + sh feed / f0) for the other rows (Sprint 9h).
            # The food response of the EU's use per commodity is kept for the residual feeds' output (MaprFeed_).
            # Per EU market region: its member states' bulks at the region's prices.
            fr = self._eu_food_ratio.setdefault(_reg, {})
            for c in (self._feed_byproduct_params().get("parents") or ()):
                j = Cc.get(c)
                if j is not None:
                    fr[c] = float(PR[ie, j]) ** float(eu_eta.get(c, ETA[j]))
            if fb:
                f0r = fb["feed0_reg"].get(_reg, {})
                feed = self.eu_feed_use({c: float(PR[ie, Cc[c]]) for c in fb["feed0"] if c in Cc},
                                        region=_reg if self.eu_blocks else None)
                self._eu_feed_now_reg[_reg] = feed
                if not self.eu_blocks:
                    self._eu_feed_now = feed
                for c, sh in fb["share_reg"].get(_reg, {}).items():
                    j = Cc.get(c)
                    f0 = f0r.get(c, 0.0)
                    if j is None or f0 <= 0:
                        continue
                    d0 = float(Bv[ie, j]) * float(CAL[j])
                    if d0 <= 0:
                        continue
                    rest = float(PR[ie, j]) ** float(eu_eta.get(c, ETA[j]))
                    D[ie, j] = float(D[ie, j]) + d0 * sh * (feed.get(c, f0) / f0 - rest)
                    SH[ie, j] += sh
            # RAW MILK: the EU's milk goes to its dairies (the dairy block prices it); the EU takes no part
            # in the world raw-milk market (CAPRI: raw milk is not traded with third countries)
            _ms_now = getattr(self, "_eu_milk_supply_now", None)
            if "MILK" in Cc and self._dairy_params() and _ms_now:
                D[ie, Cc["MILK"]] = float(_ms_now.get(_reg, 0.0) if isinstance(_ms_now, dict) else _ms_now)
                SH[ie, Cc["MILK"]] = 1.0
            # DAIRY PRODUCTS (dairy Stage 3): EU food use with CAPRI's own and cross-price elasticities among
            # the nine dairy products (p_ElasDem), EU feed use following the calves' milk feed (FMIL) with
            # CES substitution; per EU market region at its prices, its food and feed use (dairy params "reg")
            if self._dairy_params():
                _dp = self._dairy_params()
                _rp = _dp["reg"][_reg]
                _P9 = list(self.DAIRY_PRODUCTS)
                _dl = getattr(self, "_dairy_last", None) or {}
                _rho = np.array([float(PR[ie, Cc[self.DAIRY_TRADED[k]]]) if k in self.DAIRY_TRADED and self.DAIRY_TRADED[k] in Cc
                                 else float((_dl.get("price_ratio") or {}).get(k, 1.0)) for k in _P9])
                _rho = np.maximum(_rho, 0.05)
                _food = np.exp(_dp["E"] @ np.log(_rho))
                _feed = self.dairy_feed_factor(_rho)
                # CAPRI's FMIL bulk per member state (feedShareEqu_, Sprint 9h): each product's EU feed use from the
                # member states' FMIL bulks at the products' prices, where the bulk table has the product
                _fn = self._eu_feed_now_reg.get(_reg) or {}
                _f0 = (fb or {}).get("feed0_reg", {}).get(_reg, {}) if fb else {}
                for k, c in self.DAIRY_TRADED.items():
                    if c in _fn and float(_f0.get(c, 0.0)) > 0:
                        _feed[_P9.index(k)] = float(_fn[c]) / float(_f0[c])
                for k, c in self.DAIRY_TRADED.items():
                    j = Cc.get(c)
                    kk = _P9.index(k)
                    cons0 = float(_rp["cons9"].get(k, 0.0))
                    if j is None or cons0 <= 0:
                        continue
                    sh = min(1.0, float(_rp["fd9"][kk]) / cons0)
                    d0 = float(Bv[ie, j]) * float(CAL[j])
                    D[ie, j] = d0 * ((1.0 - sh) * float(_food[kk]) + sh * float(_feed[kk]))
                    OLDF[ie, j] = float(_food[kk])
                    SH[ie, j] = sh
        # NON-EU MARKET REGIONS WITH SUPPLY MODELS (Norway, CAPRI RMSSUP; K56): feed follows the supply models' herds
        # through the region's bulks (feedBlkPrice_, feedShareEqu_; CAPRI has no feed demand function FeedBal_ for
        # RMSSUP), at the region's prices, on CAPRI's feed share of its use; raw milk goes to its own dairies (not
        # traded). The dairy products fed follow its FMIL bulk in the dairy block below.
        _sup_now = getattr(self, "_sup_milk_now", None) or {}
        self._sup_feed_now = {}
        _dairy_cs = set(self.DAIRY_TRADED.values())
        for _reg in self.SUP:
            i = R.get(_reg)
            if i is None:
                continue
            if "MILK" in Cc and _reg in _sup_now:
                D[i, Cc["MILK"]] = float(_sup_now[_reg])
                SH[i, Cc["MILK"]] = 1.0
            if not fb or _reg not in (getattr(self, "_sup_active", None) or ()):
                continue
            f0r = (fb.get("feed0_sup") or {}).get(_reg, {})
            feed = self.sup_feed_use(_reg, {c: float(PR[i, Cc[c]]) for c in f0r if c in Cc})
            self._sup_feed_now[_reg] = feed
            for c, sh in (fb.get("share_sup") or {}).get(_reg, {}).items():
                j = Cc.get(c)
                f0 = f0r.get(c, 0.0)
                if j is None or f0 <= 0 or c in _dairy_cs:
                    continue
                d0 = float(Bv[i, j]) * float(CAL[j])
                if d0 <= 0:
                    continue
                sh = min(sh, max(0.0, 1.0 - SH[i, j]))
                rest = float(PR[i, j]) ** float(ETA[j])
                D[i, j] = float(D[i, j]) + d0 * sh * (feed.get(c, f0) / f0 - rest)
                SH[i, j] += sh
        # NON-EU DAIRY PRODUCTS (Sprint 9f): in the regions with CAPRI's dairy block, food use with the region's
        # own and cross p_ElasDem among the nine products, feed use with the FMIL CES at a fixed FMIL index (the
        # model has no non-EU herds; Norway: its FMIL bulk from its supply models' herds); weights: the block's 2030
        # human consumption and feed use
        _wpar = self._dairy_world_params()
        if _wpar:
            _P9 = list(self.DAIRY_PRODUCTS)
            for _r, _prm in _wpar.items():
                i = R.get(_r)
                if i is None:
                    continue
                _rho = np.array([float(PR[i, Cc[self.DAIRY_TRADED[k]]]) if self.DAIRY_TRADED[k] in Cc else 1.0
                                 for k in _P9])
                _rho = np.maximum(_rho, 0.05)
                _food = np.exp(_prm["E"] @ np.log(_rho))
                _feed = self.dairy_feed_factor(_rho, _prm, 1.0)
                _fs = self._sup_feed_now.get(_r)
                if _fs:
                    _f0s = (fb.get("feed0_sup") or {}).get(_r, {})
                    for k, c in self.DAIRY_TRADED.items():
                        if c in _fs and float(_f0s.get(c, 0.0)) > 0:
                            _feed[_P9.index(k)] = float(_fs[c]) / float(_f0s[c])
                for kk, k in enumerate(_P9):
                    j = Cc.get(self.DAIRY_TRADED[k])
                    hc, fd = float(_prm["hc9"][kk]), float(_prm["fd9"][kk])
                    if j is None or hc + fd <= 0:
                        continue
                    sh = fd / (hc + fd)
                    d0 = float(Bv[i, j]) * float(CAL[j])
                    D[i, j] = d0 * ((1.0 - sh) * float(_food[kk]) + sh * float(_feed[kk]))
                    OLDF[i, j] = float(_food[kk])
                    SH[i, j] = sh
        # BIOFUEL FEEDSTOCK USE (CAPRI biofFeedCost_, biofFeedCostAgg_, Biof_, prodBiof_): the biofuel part of
        # each region's use follows the CES feedstock choice at the biofuel output (the biofuel market's when
        # endogenous, else the reference), not the food response the rest of the row gets. The food factor that
        # the lines above applied to that part is taken back out, and the CES quantity put in.
        bp = self._biofuel_params()
        self._eu_biof_ratio = {}
        if bp:
            for reg in sorted({g["region"] for g in bp["groups"]}):
                i = R.get(reg)
                if i is None:
                    continue
                ratios = {c: float(PR[i, Cc[c]]) for c in self.commodities if c in Cc}
                bq = self.biofuel_feedstock_use_region(reg, ratios)
                for c, q in bq.items():
                    j = Cc.get(c)
                    if j is None:
                        continue
                    if reg in self.EU:
                        # EU: CAPRI's biofuel share of EU use applied to the model's EU use (the EU base is the
                        # supply models', not CAPRI's); per EU market region its own share and feedstock use
                        sh = bp["share_reg"].get((reg, c), 0.0)
                        q0 = bp["q0_reg"].get((reg, c), 0.0)
                        if sh <= 0 or q0 <= 0:
                            continue
                        d0 = float(Bv[i, j]) * float(CAL[j])
                        e = float(eu_eta.get(c, ETA[j]))
                        food = float(PR[i, j]) ** e
                        D[i, j] = D[i, j] + d0 * sh * (q / q0 - food)
                        SH[i, j] += sh
                        self._eu_biof_ratio.setdefault(reg, {})[c] = q / q0
                    else:
                        # non-EU: the region's use is CAPRI's, which holds CAPRI's feedstock quantity
                        q0 = bp["q0_reg"].get((reg, c), 0.0)
                        if q0 <= 0:
                            continue
                        food = float(PR[i, j]) ** float(ETA[j])
                        D[i, j] = D[i, j] + (q - q0 * food)
                        _d0 = float(Bv[i, j]) * float(CAL[j])
                        if _d0 > 0:
                            SH[i, j] += q0 / _d0
        # BIOFUEL USE (CAPRI biofDemShare_, biofDem_, Cpri_, ProcNQ_): the biofuel part of each region's use follows
        # the mandate and the biofuel's consumer price against fossil fuel, non-fuel processing CAPRI's processing
        # function. Without endogenous biofuel markets, use is fixed at the reference (CAPRI: no biofuel market).
        bm = self._biofuel_market_params()
        if bm:
            st = None
            if self.biofuel_endogenous():
                st = self.biofuel_state(None, pd.DataFrame(PR, index=self.regions, columns=self.commodities),
                                        use_only=True)
            for (reg, fuel), u0 in bm["use0"].items():
                i, j = R.get(reg), Cc.get(fuel)
                if i is None or j is None:
                    continue
                d0 = float(Bv[i, j]) * float(CAL[j])
                if st is None:
                    D[i, j] = d0
                else:
                    p0 = float(bm["proc0"].get((reg, fuel), 0.0))
                    D[i, j] = max(0.0, d0 - u0 - p0 + st["use"].get((reg, fuel), u0) + st["proc"].get((reg, fuel), p0))
        # PROCESSING (CAPRI ProcNQ_): the processing part of use (CAPRI's share) of the products other than the
        # oilseeds (crushing, above) moves by CAPRI's Hessian times the change of the Armington prices (cross terms
        # among the vegetable oils), replacing the own-price response that part had
        pq = self._proc_nq_params()
        if pq:
            REFv = ref.values.astype(float)
            for (reg, c), shp in pq["share"].items():
                i, j = R.get(reg), Cc.get(c)
                if i is None or j is None or c in self.CRUSH_CHAINS or c in self._PROC_NQ_SKIP:
                    continue
                Hr = pq["H"].get(reg, {})
                if not (Hr.get((c, c), 0.0) > 0):
                    continue
                d0 = float(Bv[i, j]) * float(CAL[j])
                if d0 <= 0:
                    continue
                shp = min(shp, max(0.0, 1.0 - SH[i, j]))
                if shp <= 0:
                    continue
                dq = 0.0
                for (x, y), hv in Hr.items():
                    if x != c:
                        continue
                    jy = Cc.get(y)
                    if jy is not None and y not in self.CRUSH_CHAINS:
                        dq -= hv * (float(DPv[i, jy]) - float(REFv[i, jy]))
                D[i, j] = float(D[i, j]) + d0 * shp * (1.0 - float(OLDF[i, j])) + dq
                SH[i, j] += shp
        if GLR is not None:
            hs = np.minimum(HS, np.clip(1.0 - SH, 0.0, 1.0))
            D0c = Bv * CAL[None, :]
            m = (hs > 0) & np.isfinite(OLDF) & (D0c > 0)
            D[m] = D[m] + (D0c * hs * (GLR - OLDF))[m]
            # the food response of the EU's use per commodity (residual feeds' output) includes the GL part
            for _reg, fr in self._eu_food_ratio.items():
                ie = R.get(_reg)
                for c in list(fr):
                    j = Cc[c]
                    w = 1.0 - min(SH[ie, j], 1.0)
                    if hs[ie, j] > 0 and w > 0:
                        fr[c] = OLDF[ie, j] + hs[ie, j] / w * (GLR[ie, j] - OLDF[ie, j])
        self._gl_last = (GLR, None if GLR is None else hs) if GLR is not None else None
        # share of each cell's base use left to the residual own-price response QD0 (P/P0)^eta (diagnostic)
        self._rest_share = np.clip(1.0 - SH - (hs if GLR is not None else 0.0), 0.0, 1.0)
        demand = pd.DataFrame(D, index=demand.index, columns=demand.columns)
        return demand.clip(lower=0.0).astype(float)

    # ------------------------------------------------------------------
    # The EU's base supply and demand
    # ------------------------------------------------------------------
    def set_eu_base(self, base_supply: pd.Series, base_demand: pd.Series):
        """Record the EU's base supply and demand at the model's own levels."""
        self._eu_base_supply = base_supply.astype(float)
        self._eu_base_demand = base_demand.astype(float)

    def excess_demand(
        self,
        world_prices: pd.Series,
        exogenous_supply: Optional[pd.DataFrame] = None,
        trade_scenario: Optional[Dict] = None,
    ) -> pd.Series:
        """
        Compute global excess demand for each commodity at given prices.
        ED_k = Σ_r QD_r(p) - Σ_r QS_r(p)
        At equilibrium: ED_k = 0 ∀ k.
        """
        dom_prices = self.domestic_prices(world_prices, trade_scenario)
        self._trade_scenario_now = trade_scenario
        supply = self.supply_response(world_prices, exogenous_supply)
        demand = self.demand_response(dom_prices, world_prices)

        ed = {}
        for comm in self.commodities:
            total_supply = supply[comm].sum() if comm in supply.columns else 0.0
            total_demand = demand[comm].sum() if comm in demand.columns else 0.0
            ed[comm] = total_demand - total_supply

        return pd.Series(ed)


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
            self._dairy_u = None
            self._dairy_u_all = {}
            self._eu_milk_supply_now = dict(self._dairy_S0_reg)
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
        self._sup_milk_now = dict(self._sup_milk0)

    def _demand_cal_factor(self, comm: str) -> float:
        cal = getattr(self, "_demand_cal", None)
        if cal is not None and comm in cal.index:
            return float(cal[comm])
        return 1.0

    # ------------------------------------------------------------------
    # Main solver (tatonnement / Newton)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # CAPRI's bilateral market (Sprint 8m; capri_mod/market/bilateral.py)
    # ------------------------------------------------------------------

    #: "bilateral": CAPRI's market model - a market price per region, total use an Armington aggregate of
    #: domestic sales and imports, imports a CES over origins, bilateral flows priced at the exporter's price
    #: plus CAPRI's transport costs and tariffs (data: tools/build/build_bilateral_market.py). "premium": the
    #: earlier approximation - one world price per commodity and an Armington premium for the EU.
    market_structure = "bilateral"
    #: EU products without a supply-model activity whose EU supply is CAPRI's market supply function (October 2026):
    #: other vegetable oils OTHO and the fish products FFIS, SFIS, OAQU (own-price p_elasSupp, EU medians 0.95-0.98). Palm oil has no EU
    #: supply in CAPRI's market model; FAO_agg's 105 kt (Belgian refining) stay at base.
    EU_MARKET_SUPPLY = frozenset({"OTHO", "FFIS", "SFIS", "OAQU"})
    #: CAPRI's market supply Hessian measured on the supply models at the baseline (model._market_supply_hessian)
    supply_hessian = None
    #: acceleration of the bilateral market's outer steps (_solve_bilateral): "anderson" (Anderson mixing over the last
    #: MARKET_AA_MEMORY steps of the fixed-point map log r -> log new; CAPRI's group and full-system stages serve the
    #: same purpose: the cross-product links a product-by-product step sees only between steps) or None (damped steps
    #: alone). Same equations and stopping rule (every relative residual < tol): the path changes, not the equilibrium.
    market_acceleration = setting("market.acceleration")
    MARKET_AA_MEMORY = setting("market.aa_memory")
    #: CAPRI's EU tariff-rate quotas in the bilateral market (bilateral_trq_<year>.csv)
    use_trq = setting("market.use_trq")
    #: crushing products: their own-price supply response is the crushing margin's
    _CRUSH_PRODUCTS = ("RAPO", "SUNO", "SOYO", "RAPC", "SUNC", "SOYC")

    def _bilateral_raw(self):
        """Uncalibrated bilateral systems for the market year (data['market_year'], else 2017)."""
        from capri_mod.market.bilateral import BilateralCommodity
        from pathlib import Path as _P
        year = int(self.data.get("market_year", 2017) or 2017)
        cached = getattr(self, "_bilat_raw_cache", None)
        if cached is not None and cached[0] == year:
            return cached[1]
        base = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "market"
        sfx = "_eu2" if self.eu_blocks else ""          # CAPRI's two EU trade blocks (build_bilateral_market --eu-blocks)
        ff = base / f"bilateral_flows_{year}{sfx}.csv"
        if not ff.exists():
            year = 2017
            ff = base / f"bilateral_flows_2017{sfx}.csv"
        if not ff.exists():
            self._bilat_raw_cache = (year, {})
            return {}
        fl = pd.read_csv(ff)
        rg = pd.read_csv(base / f"bilateral_regions_{year}{sfx}.csv")
        rho = pd.read_csv(base / "armington_rho.csv").set_index("commodity")
        R = list(self.regions)
        ix = {r: i for i, r in enumerate(R)}
        n = len(R)
        out = {}
        for c, g in fl.groupby("commodity"):
            if c not in self.commodities:
                continue
            X0, a, b, a0 = (np.zeros((n, n)) for _ in range(4))
            for t in g.itertuples(index=False):
                i, j = ix.get(t.importer), ix.get(t.exporter)
                if i is None or j is None:
                    continue
                X0[i, j] += t.q_kt
                if i != j:
                    a[i, j], b[i, j], a0[i, j] = t.a, t.b, t.a0
            pm = rg[rg.commodity == c].set_index("region")["pmrk"]
            Pd0 = np.array([float(pm.get(r, np.nan)) for r in R])
            fill = float(np.nanmedian(Pd0)) if np.isfinite(Pd0).any() else 1.0
            Pd0 = np.where(np.isfinite(Pd0) & (Pd0 > 0), Pd0, fill)
            out[c] = BilateralCommodity(c, R, X0, a, b, a0, Pd0,
                                        float(rho.at[c, "rho1"]) if c in rho.index else 8.0,
                                        float(rho.at[c, "rho2"]) if c in rho.index else 10.0)
        # EU tariff-rate quotas (tools/build/build_bilateral_market.py build_trq)
        ft = base / f"bilateral_trq_{year}.csv"
        if ft.exists() and getattr(self, "use_trq", True) and all(r in ix for r in self.EU):
            tq = pd.read_csv(ft)
            rows = [ix[r] for r in self.EU]                # the EU's quotas: imports of every EU market region
            for c, g in tq.groupby("commodity"):
                sc = out.get(c)
                if sc is None:
                    continue
                Q, gap, sh = np.zeros(n), np.zeros(n), np.zeros(n)
                for t in g.itertuples(index=False):
                    j = ix.get(t.exporter)
                    if j is None or float(sc.X0[rows, j].sum()) <= 0:
                        continue
                    Q[j], gap[j] = t.quota_kt, t.gap_eur_t
                    sh[j] = min(1.0, float(t.imports_kt) / float(sc.X0[rows, j].sum()))
                if (Q > 0).any():
                    sc.trq_row = rows[0] if len(rows) == 1 else rows
                    sc.trq_Q, sc.trq_gap, sc.trq_share = Q, gap, sh
                    sc.trq_offset = np.zeros(n)
        self._bilat_raw_cache = (year, out)
        return out

    def _eu_rows_ix(self):
        """Row index of the EU market region (one), or the list of the EU trade blocks' rows (None: no EU)."""
        R = list(self.regions)
        rows = [R.index(r) for r in self.EU if r in R]
        if not rows:
            return None
        return rows[0] if len(rows) == 1 else rows

    def _bilateral_ratio_frame(self, value=1.0) -> pd.DataFrame:
        return pd.DataFrame(value, index=list(self.regions), columns=list(self.commodities), dtype=float)

    def _dom0(self) -> pd.DataFrame:
        d0 = getattr(self, "_dom0_cache", None)
        if d0 is None:
            d0 = self.domestic_prices(self.world_prices_base)
            self._dom0_cache = d0
        return d0

    def _bilateral_calibrate(self, exogenous_supply) -> None:
        """Base of the bilateral market at the model's own supply (CAPRI's flows kept, domestic sales absorb
        the difference), demand calibration 1 for bilateral commodities, the world clearing calibration for
        the pooled ones (raw milk, other oilseeds)."""
        import copy as _copy
        raw = self._bilateral_raw()
        R = list(self.regions)
        # non-EU base production of the bilateral commodities: CAPRI's (domestic sales + exports)
        for c, sysc in raw.items():
            prod = sysc.X0.sum(axis=0)
            for i, r in enumerate(R):
                if r not in self.EU:
                    self.base_production.at[r, c] = float(prod[i])
        # non-EU crushing at CAPRI's cake production of the market year
        over = {}
        for (r, sd), prm in (self._crush_params() or {}).items():
            if r in self.EU:
                continue
            o, ck = self.CRUSH_CHAINS[sd]
            # the cake, or the oil where CAPRI records no cake from the crush (BGD soybeans, THA sunflower)
            for prod_, y_ in ((ck, prm["yc"]), (o, prm["yo"])):
                if prod_ in raw and y_ > 0:
                    q = float(self.base_production.at[r, prod_]) / y_
                    if q > 0:
                        over[(r, sd)] = q
                    break
        self._crush_q0_override = over
        self._crush_cache = None
        self._demand_cal = pd.Series(1.0, index=self.commodities)
        exo_eu, exo_sup = self._split_supply(exogenous_supply)
        base_supply = self._align_eu_base_balance(exo_eu.sum(axis=0), exo_eu) \
            if exogenous_supply is not None else None
        self._align_sup_base(exo_sup)
        if base_supply is not None:
            self._align_eu_crush_products(base_supply)
        one = self._bilateral_ratio_frame()
        dom0 = self._dom0()
        sysd = {}
        for _pass in range(2):
            S = self.supply_response(self.world_prices_base, exogenous_supply, region_ratio=one, crush_dom=dom0)
            sysd = {}
            for c, sysc in raw.items():
                sc = _copy.deepcopy(sysc)
                sc.calibrate(S[c].reindex(R).fillna(0.0).values)
                sysd[c] = sc
                for i, r in enumerate(R):
                    self.base_consumption.at[r, c] = float(sc.D0[i])
                if c in self.CRUSH_CHAINS:
                    if getattr(self, "_eu_aligned_use", None) is None:
                        self._eu_aligned_use = {}
                    for _rg in self.EU:
                        self._eu_aligned_use.setdefault(_rg, {})[c] = float(sc.D0[R.index(_rg)])
            self._crush_cache = None
            if base_supply is not None:
                self._align_eu_crush_products(base_supply)
        # the demand functions carry terms that are not 1 at the calibration point (EU feed use follows the
        # current herds, crushing, biofuels): base consumption is rescaled so that use at the reference prices
        # is exactly the closure's D0
        for _k in range(4):
            Dt = self.demand_response(dom0, self.world_prices_base)
            worst = 0.0
            for c, sc in sysd.items():
                for i, r in enumerate(R):
                    d = float(Dt.at[r, c])
                    if d > 1e-9 and sc.D0[i] > 0:
                        f = float(sc.D0[i]) / d
                        worst = max(worst, abs(f - 1.0))
                        self.base_consumption.at[r, c] = float(self.base_consumption.at[r, c]) * f
            if worst < 1e-12:
                break
        # pooled commodities: non-EU demand calibrated so the world clears at base (EU use set by alignment)
        pooled = [c for c in self.commodities if c not in sysd]
        S = self.supply_response(self.world_prices_base, exogenous_supply, region_ratio=one, crush_dom=dom0)
        D = self.demand_response(dom0, self.world_prices_base)
        # the regions whose use is set by the supply models (the EU; Norway with its supply models, whose raw milk
        # goes to its own dairies) keep it; the others' use is calibrated so that the world clears
        fixed = list(self.EU) + [r for r in self.SUP if r in exo_sup]
        others = [r for r in R if r not in fixed]
        cal = pd.Series(1.0, index=self.commodities)
        # where the bounds [0.2, 5] (not CAPRI's: PROXY_AUDIT S185) bind: {commodity: unbounded factor}; and the
        # bilateral systems' export-share caps (S192). Recorded for the runs' metadata and warned
        self.calibration_bound_hits = {"non_eu_use": {}, "export_share": {
            c: list(sc.export_cap_hits) for c, sc in sysd.items() if getattr(sc, "export_cap_hits", None)}}
        for c in pooled:
            s_all, d_eu, d_oth = float(S[c].sum()), float(D.loc[fixed, c].sum()), float(D.loc[others, c].sum())
            if d_oth > 1.0 and s_all - d_eu > 1.0:
                _raw = (s_all - d_eu) / d_oth
                cal[c] = min(5.0, max(0.2, _raw))
                if cal[c] != _raw:
                    self.calibration_bound_hits["non_eu_use"][c] = _raw
            if cal[c] != 1.0:
                for _rg in fixed:
                    self.base_consumption.at[_rg, c] /= float(cal[c])
        self._demand_cal = cal
        _h = self.calibration_bound_hits
        if _h["non_eu_use"] or _h["export_share"]:
            import warnings as _w
            _w.warn(f"market calibration bounds reached: non-EU use factor outside [0.2, 5] for "
                    f"{sorted(_h['non_eu_use'])}; export share above 0.98 for {sorted(_h['export_share'])}",
                    RuntimeWarning)
        for sc in sysd.values():
            if sc.trq_row is not None:
                sc.trq_offset = np.zeros(len(R))
        self._bilat = sysd
        self._bilat_last_r = None
        self._bilat_local_el = None

    def _bilateral_eval(self, r: pd.DataFrame, exogenous_supply, trade_scenario=None):
        """Full model response at producer price ratios r: supply, demand, consumer price ratios, residuals."""
        sysd = self._bilat
        dom0 = self._dom0()
        PAr = r.copy()
        pcache = {}
        tadd = (trade_scenario or {}).get("tariff_change", {}) if trade_scenario else {}
        ie = self._eu_rows_ix()
        for c, sc in sysd.items():
            rc = r[c].values
            p = sc.import_prices(rc, float(tadd.get(c, 0.0) or 0.0), ie)
            _, _, PA, _ = sc.prices(rc, p)
            PAr[c] = PA / sc.PA0
            pcache[c] = p
        dp = dom0.reindex(index=r.index, columns=r.columns) * PAr
        world = self.world_prices_base * self._bilateral_world_index(r)
        self._bilat_ratio_now = r
        # CAPRI's crushing margin (ProcMargO_, arm/market_model.gms): the seed at its Armington price (v_Arm1Price),
        # oil and cake at their producer prices (v_prodPrice); KNOWN_ISSUES K54-4
        cpd = dp
        if self.CRUSH_CHAINS and getattr(self, "crush_margin_producer_prices", True):
            cpd = dp.copy()
            _oc = sorted({x for oc in self.CRUSH_CHAINS.values() for x in oc if x in r.columns})
            d0r = dom0.reindex(index=r.index, columns=_oc)
            cpd[_oc] = d0r * r[_oc]
        self._crush_prices_now = cpd
        try:
            S = self.supply_response(world, exogenous_supply, region_ratio=r, crush_dom=dp)
            D = self.demand_response(dp, world)
        finally:
            self._crush_prices_now = None
        self._apply_feed_byproduct_supply(S)
        F = {}
        for c, sc in sysd.items():
            F[c] = sc.residual(S[c].values, D[c].values, r[c].values, pcache[c])
        for c in r.columns:
            if c not in sysd:
                F[c] = np.array([float(S[c].sum()) - float(D[c].sum())])
        return S, D, PAr, F, pcache

    def _bilateral_world_index(self, r: pd.DataFrame) -> pd.Series:
        """World price index per commodity: exporters' price ratios weighted by their base exports (bilateral
        commodities); the pooled commodities' common ratio."""
        out = pd.Series(1.0, index=self.commodities)
        sysd = getattr(self, "_bilat", None) or {}
        for c in self.commodities:
            if c in sysd:
                sc = sysd[c]
                e = (sc.X0 * sc._off).sum(axis=0)
                if e.sum() > 0:
                    out[c] = float((e * r[c].values).sum() / e.sum())
            else:
                out[c] = float(r[c].iloc[0])
        return out

    def _bilateral_local_el(self, r, exogenous_supply, trade_scenario):
        """Own-price response of supply and of total use per region and commodity (log-log), measured once
        per calibration by a uniform 1% price change of each commodity."""
        S0, D0, PA0, _, _ = self._bilateral_eval(r, exogenous_supply, trade_scenario)
        es = pd.DataFrame(0.0, index=r.index, columns=r.columns)
        ed = pd.DataFrame(0.0, index=r.index, columns=r.columns)
        h = 0.01
        for c in r.columns:
            r1 = r.copy()
            r1[c] = r1[c] * (1 + h)
            S1, D1, PA1, _, _ = self._bilateral_eval(r1, exogenous_supply, trade_scenario)
            with np.errstate(divide="ignore", invalid="ignore"):
                es[c] = np.where(S0[c] > 1e-6, np.log(np.maximum(S1[c], 1e-12) / S0[c]) / np.log(1 + h), 0.0)
                dpa = np.log(PA1[c] / PA0[c])
                ed[c] = np.where((D0[c] > 1e-6) & (np.abs(dpa) > 1e-9),
                                 np.log(np.maximum(D1[c], 1e-12) / D0[c]) / np.where(np.abs(dpa) > 1e-9, dpa, 1.0), 0.0)
        return es.clip(-0.5, 5.0).fillna(0.0), ed.clip(-5.0, 0.5).fillna(0.0)

    #: the trade systems' Newton keeps its Jacobian while the residual keeps falling fast (chord steps)
    TRADE_CHORD = setting("market.trade_chord")

    def _bilateral_inner(self, sc, Sk, Dk, rk, PAk, es, ed, tadd, ie):
        """Exact solve of one commodity's trade system with supply and use log-linear around the current
        point: S_i = Sk_i (r_i / rk_i)^es_i, D_i = Dk_i (PA_i / PAk_i)^ed_i."""
        act = np.where(sc.S0 > 1e-6)[0]
        if len(act) == 0:
            return rk
        scale = np.maximum(sc.S0[act] + sc.D0[act], 1.0)

        def G(z):
            r = rk.copy()
            r[act] = np.exp(z)
            p = sc.import_prices(r, tadd, ie)
            pre = sc.prices(r, p)                       # computed once, reused by the flows
            PA = pre[2]
            S = Sk * (r / rk) ** es
            D = Dk * (PA / PAk) ** ed
            return sc.residual(S, D, r, p, pre=pre)[act] / scale

        z = np.log(rk[act])
        g = G(z)
        J = None
        prev = None
        for _ in range(60):
            nrm = float(np.max(np.abs(g)))
            if nrm < 1e-12:
                break
            # Newton with a finite-difference Jacobian, kept while it keeps the residual falling fast (chord steps:
            # a fresh Jacobian costs one evaluation per region; same root and tolerance)
            if J is None or prev is None or nrm > 0.25 * prev or not self.TRADE_CHORD:
                m = len(z)
                J = np.empty((m, m))
                h = 1e-6
                for k in range(m):
                    zk = z.copy(); zk[k] += h
                    J[:, k] = (G(zk) - g) / h
            try:
                dz = np.linalg.solve(J, -g)
            except np.linalg.LinAlgError:
                dz = np.linalg.lstsq(J, -g, rcond=None)[0]
            dz = np.clip(dz, -0.5, 0.5)
            t = 1.0
            while t > 1e-3:
                g1 = G(z + t * dz)
                if float(np.max(np.abs(g1))) < nrm:
                    break
                t *= 0.5
            prev = nrm
            z = z + t * dz
            g = G(z)
        out = rk.copy()
        out[act] = np.exp(z)
        return out

    #: scenario change of the EU's tariff-rate quota volumes, {commodity: change in 1000 t} (PolicyScenario.
    #: trq_volume_changes, set by CAPRIModel.run; empty in a baseline run)
    trq_volume_changes: dict = {}

    def _apply_trq_volumes(self, sysd) -> None:
        """Set each EU tariff-rate quota to its base volume plus the scenario's change: a commodity's change (1000 t)
        is spread over its quotas (one per exporter, CAPRI's bilateral TrqNT) in proportion to their base volumes.
        The base fill, at which the base tariff regime is calibrated, stays at the base quotas (trq_Q0)."""
        ch = dict(getattr(self, "trq_volume_changes", None) or {})
        for c, sc in (sysd or {}).items():
            if getattr(sc, "trq_row", None) is None or sc.trq_Q is None:
                continue
            if sc.trq_Q0 is None:
                sc.trq_Q0 = sc.trq_Q.copy()
            tot = float(sc.trq_Q0.sum())
            d = float(ch.get(c, 0.0))
            sc.trq_Q = sc.trq_Q0 * max(0.0, 1.0 + d / tot) if (tot > 0 and d) else sc.trq_Q0.copy()

    def trq_commodities(self) -> list:
        """Commodities with an EU tariff-rate quota in CAPRI's bilateral data for the market year."""
        return sorted(c for c, sc in (self._bilateral_raw() or {}).items() if getattr(sc, "trq_row", None) is not None)

    def _solve_bilateral(self, exogenous_supply, trade_scenario=None, tol=None, max_outer=None, verbose=False):
        """CAPRI's market: successive linearisation - the full model response (supply module output anticipated,
        crushing, dairy blocks, feed and biofuel demand) is re-evaluated each step, and each commodity's trade
        system solved exactly with supply and use log-linear around that point."""
        _st = _settings()                                   # market.* : tolerance, rounds, damping, step clip
        if tol is None:
            tol = float(_st.get("market.tol"))
        if max_outer is None:
            max_outer = int(_st.get("market.max_iter"))
        _sclip = tuple(_st.get("market.step_clip"))
        # BASELINE RUN (no EU base recorded yet): the market is calibrated at THIS supply, prices stay at the
        # reference - CAPRI's reference run is a calibrated equilibrium at its reference prices. Each outer
        # iteration of the baseline recalibrates, so the calibration a scenario inherits is the one at the
        # converged baseline supply. Scenario runs keep it frozen.
        if getattr(self, "_eu_base_supply", None) is None or getattr(self, "_demand_cal_frozen", None) is None:
            self._bilateral_calibrate(exogenous_supply)
            self._apply_trq_volumes(self._bilat)
            self._demand_cal_frozen = self._demand_cal.copy()
            r = self._bilateral_ratio_frame()
            S, D, PAr, F, pc = self._bilateral_eval(r, exogenous_supply, trade_scenario)
            def _sz(c):
                if c in self._bilat:
                    return np.maximum(self._bilat[c].S0 + self._bilat[c].D0, 1.0)
                return np.array([max(float(S[c].sum()), 1.0)])
            self._bilat_base_resid = {c: float(np.max(np.abs(F[c] / _sz(c)))) for c in F}
            self._bilat_err = max(self._bilat_base_resid.values())
            self._bilat_converged = True
            self._bilat_last_r = r.copy()
            return r, S, D, PAr, pc, True, 0
        self._demand_cal = self._demand_cal_frozen.copy()
        sysd = self._bilat
        self._apply_trq_volumes(sysd)
        R = list(self.regions)
        ie = self._eu_rows_ix()
        tadd = (trade_scenario or {}).get("tariff_change", {}) if trade_scenario else {}
        r = self._bilateral_ratio_frame()
        last = getattr(self, "_bilat_last_r", None)
        if last is not None:
            r = last.reindex(index=r.index, columns=r.columns).fillna(1.0)
        if getattr(self, "_bilat_local_el", None) is None:
            self._bilat_local_el = self._bilateral_local_el(self._bilateral_ratio_frame(), exogenous_supply, trade_scenario)
        es, ed = self._bilat_local_el

        def size(c):
            if c in sysd:
                return np.maximum(sysd[c].S0 + sysd[c].D0, 1.0)
            return np.array([max(float(self.base_production[c].sum()), 1.0)])

        prev = np.inf
        damp = 1.0
        converged = False
        aa = getattr(self, "market_acceleration", None) == "anderson" and __import__("os").environ.get("CAPRI_MARKET_AA", "1") != "0"
        aa_z, aa_g = [], []                                  # history: log r and log new (the map's value)
        for it in range(max_outer):
            S, D, PAr, F, pc = self._bilateral_eval(r, exogenous_supply, trade_scenario)
            errs = {c: float(np.max(np.abs(F[c] / size(c)))) for c in F}
            err = max(errs.values())
            self._bilat_errs = errs
            if getattr(self, "_debug_trace", None) is not None:
                self._debug_trace.append((it, err, max(errs, key=errs.get), damp))
            if verbose:
                print(f"  bilateral market iter {it}: max rel residual {err:.2e}")
            # EU tariff-rate quotas: the out-of-quota tariff follows the fill of each quota at the current
            # flows (lagged by one step, damped)
            trq_moved = 0.0
            for c, sc in sysd.items():
                if sc.trq_row is None:
                    continue
                X, _ = sc.flows(D[c].values, r[c].values, pc[c])
                old_off = sc.trq_offset.copy()
                sc.trq_solve(X, pc[c])
                trq_moved = max(trq_moved, float(np.max(np.abs(sc.trq_offset - old_off) / np.maximum(float(np.min(sc.Pd0[sc._rows()])), 1.0))))
            if err < tol and trq_moved < tol:
                converged = True
                break
            prev_err = prev                                  # the previous step's residual (Anderson restart test)
            if err > prev * _st.get("market.damping_increase_threshold"):
                damp = max(_st.get("market.damping_min"), damp * _st.get("market.damping_down"))
            elif damp < 1.0 and err < prev * _st.get("market.damping_recover_threshold"):
                # the step came back under control: lengthen it again (a damping halved once stayed halved for the
                # rest of the solve, and the dairy products then crept to the tolerance in 40+ steps)
                damp = min(1.0, damp * _st.get("market.damping_up"))
            prev = err
            new = r.copy()
            for c in r.columns:
                if c in sysd:
                    rk = r[c].values
                    new[c] = self._bilateral_inner(sysd[c], S[c].values, D[c].values, rk, PAr[c].values * sysd[c].PA0,
                                                   es[c].values, ed[c].values, float(tadd.get(c, 0.0) or 0.0), ie)
                else:
                    # pooled market: one price ratio for all regions
                    s_, d_ = float(S[c].sum()), float(D[c].sum())
                    e_s = float((S[c] * es[c]).sum() / max(s_, 1e-9))
                    e_d = float((D[c] * ed[c]).sum() / max(d_, 1e-9))
                    if s_ > 0 and d_ > 0 and (e_s - e_d) > 1e-6:
                        new[c] = r[c] * (d_ / s_) ** (1.0 / (e_s - e_d))
            if aa:
                z = np.log(r.to_numpy(dtype=float)).ravel()
                g = np.log(np.maximum(new.to_numpy(dtype=float), 1e-300)).ravel()
                if err > prev_err * 0.999 or not np.all(np.isfinite(g)):
                    aa_z, aa_g = [], []                      # the residual did not fall: restart from a damped step
                aa_z.append(z); aa_g.append(g)
                aa_z, aa_g = aa_z[-(self.MARKET_AA_MEMORY + 1):], aa_g[-(self.MARKET_AA_MEMORY + 1):]
                f = g - z
                if len(aa_z) > 1:
                    F = np.column_stack([(aa_g[i + 1] - aa_z[i + 1]) - (aa_g[i] - aa_z[i]) for i in range(len(aa_z) - 1)])
                    Gd = np.column_stack([aa_g[i + 1] - aa_g[i] for i in range(len(aa_z) - 1)])
                    gam = np.linalg.lstsq(F, f, rcond=None)[0]
                    zn = g - Gd @ gam
                else:
                    zn = z + damp * f
                step = np.clip(zn - z, np.log(_sclip[0]), np.log(_sclip[1]))
                r = pd.DataFrame(np.exp(z + step).reshape(r.shape), index=r.index, columns=r.columns)
            else:
                r = r * (new / r).clip(lower=_sclip[0], upper=_sclip[1]) ** damp
        self._bilat_last_r = r.copy()
        self._bilat_converged = converged
        self._bilat_err = err
        return r, S, D, PAr, pc, converged, it + 1

    def _solve_bilateral_equilibrium(self, exogenous_supply, trade_scenario, verbose=False, max_outer=60) -> MarketEquilibrium:
        r, S, D, PAr, pc, converged, iters = self._solve_bilateral(exogenous_supply, trade_scenario, verbose=verbose,
                                                                    max_outer=max_outer)
        if not converged:
            # never silent: the market's balances are not met (largest relative residual and its product)
            import warnings as _w
            errs = getattr(self, "_bilat_errs", {}) or {}
            worst = max(errs, key=errs.get) if errs else "-"
            _w.warn(f"bilateral market did not converge in {iters} steps: largest relative residual "
                    f"{float(getattr(self, '_bilat_err', float('nan'))):.2e} ({worst})", RuntimeWarning)
        self._bilat_unconverged = None if converged else (iters, float(getattr(self, "_bilat_err", float("nan"))))
        sysd = self._bilat
        # RAW MILK with the dairy block: the EU milk price is the block's (fat and protein values of the products
        # less margins); raw milk is not traded, so it replaces the pooled market's ratio for the EU
        # world index from the market's own ratios, BEFORE the EU's raw milk takes the dairy block's price: for a
        # pooled product the index is the first region's ratio, and EU27 is the first region, so the reported world
        # raw milk price was the EU dairy block's (K17; the EU price signal itself was right: premium x world)
        widx = self._bilateral_world_index(r)
        _dl = getattr(self, "_dairy_last", None)
        if self._dairy_params() and _dl is not None and "MILK" in r.columns and all(x in r.index for x in self.EU):
            r = r.copy()
            for _rg in self.EU:
                r.at[_rg, "MILK"] = float((_dl.get("milk_price_ratio_reg") or {}).get(_rg, _dl["price_ratio"]["MILK"]))
        # Norway's raw milk: its dairy block's price (raw milk is not traded; CAPRI ProcMargM_ per RMS)
        _wl = getattr(self, "_dairy_world_last", None) or {}
        for _rg in self.SUP:
            if _rg in (getattr(self, "_sup_milk_now", None) or {}) and _rg in _wl and "MILK" in r.columns:
                r = r.copy()
                r.at[_rg, "MILK"] = float(_wl[_rg]["price_ratio"]["MILK"])
        #: producer price ratios (to base) of the non-EU market regions with supply models: the prices their
        #: supply models see (CAPRIModel; K56)
        self.sup_price_ratio = r.loc[[x for x in self.SUP if x in r.index]].copy()
        world = self.world_prices_base * widx
        dom0 = self._dom0()
        reported = dom0.reindex(index=r.index, columns=r.columns) * r
        wedge = dom0.reindex(index=r.index, columns=r.columns) * widx
        # the EU price farmers see: premium over the world index (model.py: signal = world ratio x premium); with two
        # EU market regions, per region (eu_premium_reg) and the production-weighted EU average (eu_premium)
        self.eu_premium_reg = pd.DataFrame({_rg: (r.loc[_rg] / widx).reindex(self.commodities).fillna(1.0)
                                            for _rg in self.EU}).T
        if self.eu_blocks:
            _w = S.loc[list(self.EU)].reindex(columns=self.commodities).fillna(0.0)
            _ws = _w.sum(axis=0)
            _avg = (self.eu_premium_reg * _w).sum(axis=0) / _ws.where(_ws > 0, 1.0)
            self.eu_premium = _avg.where(_ws > 0, self.eu_premium_reg.mean(axis=0))
            self._wedge_eu_last = wedge.loc[self.EU[0]]
        else:
            self.eu_premium = self.eu_premium_reg.loc["EU27"]
            self._wedge_eu_last = wedge.loc["EU27"]
        self._bilat_ratio_now = r
        idx = pd.MultiIndex.from_product([self.regions, self.regions], names=["exporter", "importer"])
        flows = pd.DataFrame(0.0, index=idx, columns=self.commodities)
        for c, sc in sysd.items():
            X, _ = sc.flows(D[c].values, r[c].values, pc[c])
            for i, imp in enumerate(self.regions):
                for j, exp in enumerate(self.regions):
                    if i != j and X[i, j] > 0:
                        flows.at[(exp, imp), c] = X[i, j]
        self.last_market_solver = "bilateral"
        welfare = self._compute_welfare(S, D, world, reported, trade_scenario)
        biof = None
        if self._biofuel_params() and all(x in reported.index for x in self.EU):
            _pr = {_rg: {c: float(PAr.at[_rg, c]) for c in self._biofuel_params()["share"] if c in PAr.columns}
                   for _rg in self.EU}
            biof = self.biofuel_feedstock_use(_pr if self.eu_blocks else _pr["EU27"])
            # biofuel markets: output, use and prices of every region (BIOF_M); first-generation output and the
            # processing margin (producer price over feedstock cost) of every EU member state
            st = getattr(self, "_biof_state", None) if self.biofuel_endogenous() else None
            biof["endogenous"] = st is not None
            if "DDGS" in S.columns:
                biof["ddgs"] = {"production": {r_: float(S.at[r_, "DDGS"]) for r_ in S.index},
                                "use": {r_: float(D.at[r_, "DDGS"]) for r_ in D.index},
                                "price_ratio": {r_: float(x_) for r_, x_ in r["DDGS"].items()}}
            bm = self._biofuel_market_params()
            if bm:
                biof["markets"] = {fuel: {"production": {r: float(S.at[r, fuel]) for r in S.index},
                                          "use": {r: float(D.at[r, fuel]) for r in D.index},
                                          "price_ratio": {r: float(r_) for r, r_ in r[fuel].items()}}
                                   for fuel in self.BIOFUELS if fuel in S.columns}
                if st is not None:
                    biof["member_states"] = {
                        f"{ms}|{fuel}": {"first_generation": float(st["X"].get((ms, fuel), d["x0_kt"])),
                                         "first_generation0": float(d["x0_kt"]),
                                         "margin": (float(d["ppri"]) * float(r.at[d["region"], fuel]) / st["mub"][(ms, fuel)]
                                                    if (ms, fuel) in st["mub"] else None),
                                         "margin0": float(d["pr0"]) or None}
                        for (ms, fuel), d in bm["rows"].items() if d["region"] in self.EU}
        if self.eu_blocks:
            S, D, reported, wedge, flows, world = self._with_eu_aggregate(S, D, reported, wedge, flows, world, dom0)
            if biof is not None:
                for k in ("markets",):
                    for fuel, v in (biof.get(k) or {}).items():
                        for it in ("production", "use"):
                            v[it]["EU27"] = sum(v[it].get(x, 0.0) for x in self.EU)
                        v["price_ratio"]["EU27"] = float(reported.at["EU27", fuel] / dom0.loc[list(self.EU), fuel].mean()) \
                            if fuel in reported.columns else 1.0
        return MarketEquilibrium(
            dairy=getattr(self, "_dairy_last", None) if self._dairy_params() else None,
            biofuel=biof, world_prices=world, domestic_prices=reported, wedge_prices=wedge,
            production=S, consumption=D, trade_flows=flows, net_exports=S.subtract(D, fill_value=0),
            welfare=welfare, excess_demand=(D.drop(index="EU27", errors="ignore").sum()
                                            - S.drop(index="EU27", errors="ignore").sum()) if self.eu_blocks
            else D.sum() - S.sum(), converged=converged, iterations=iters)

    def _with_eu_aggregate(self, S, D, reported, wedge, flows, world, dom0):
        """Two EU market regions: an EU27 reporting row (CAPRI's EU27yr19 aggregate) appended to production, use,
        prices and flows - quantities summed, prices the production-weighted average of the blocks' (use-weighted
        where the EU produces none). The market's own regions are unchanged; the row is for reporting and for the
        callers that read the EU as a whole."""
        eu = list(self.EU)
        S = S.copy(); D = D.copy(); reported = reported.copy(); wedge = wedge.copy()
        S.loc["EU27"] = S.loc[eu].sum(axis=0)
        D.loc["EU27"] = D.loc[eu].sum(axis=0)
        w = S.loc[eu].where(S.loc[eu].sum(axis=0) > 0, D.loc[eu], axis=1).reindex(columns=reported.columns).fillna(0.0)
        ws = w.sum(axis=0)
        for fr in (reported, wedge):
            avg = (fr.loc[eu] * w).sum(axis=0) / ws.where(ws > 0, 1.0)
            fr.loc["EU27"] = avg.where(ws > 0, fr.loc[eu].mean(axis=0))
        # flows: extra-EU flows of the aggregate (intra-EU flows between the blocks are not EU trade)
        fl = flows.copy()
        add = {}
        for (exp, imp), row in flows.iterrows():
            e_eu, i_eu = exp in eu, imp in eu
            if e_eu and i_eu:
                continue
            if e_eu or i_eu:
                key = ("EU27" if e_eu else exp, "EU27" if i_eu else imp)
                add[key] = add.get(key, 0.0) + row
        if add:
            extra = pd.DataFrame(add).T
            extra.index = pd.MultiIndex.from_tuples(extra.index, names=fl.index.names)
            fl = pd.concat([fl, extra])
        self._eu_aggregate_reported = True
        return S, D, reported, wedge, fl, world

    def solve(
        self,
        exogenous_supply: Optional[pd.DataFrame] = None,
        trade_scenario: Optional[Dict] = None,
        policy_scenario: Optional[Dict] = None,
        max_iter: Optional[int] = None,
        verbose: bool = False,
    ) -> MarketEquilibrium:
        """Solve CAPRI's bilateral spatial market (market/bilateral.py) for the given supply.

        exogenous_supply : supply from the supply module [region x commodity]
        trade_scenario   : {"tariff_change": {commodity: delta_pct}}
        policy_scenario  : kept for the interface (the instruments act through the supply side)
        max_iter         : Newton rounds of the bilateral solve (default 100)
        verbose          : print iteration progress

        The premium market structure of earlier versions (SciPy root or tatonnement with an EU
        Armington premium) was removed on 20 October 2026 (KNOWN_ISSUES K54-2): no run path used it.
        """
        self._trade_scenario_now = trade_scenario
        if self.market_structure != "bilateral" or not self._bilateral_raw():
            raise ValueError("the market needs CAPRI's bilateral data (capri_data/2017/market/bilateral_flows_*.csv)")
        return self._solve_bilateral_equilibrium(exogenous_supply, trade_scenario, verbose=verbose,
                                                 max_outer=int(max_iter) if max_iter else int(_settings().get("market.max_iter")))

    # ------------------------------------------------------------------
    # Welfare
    # ------------------------------------------------------------------

    def _compute_welfare(
        self,
        supply: pd.DataFrame,
        demand: pd.DataFrame,
        world_prices: pd.Series,
        domestic_prices: pd.DataFrame,
        trade_scenario: Optional[Dict] = None,
    ) -> pd.DataFrame:
        """
        Compute welfare effects (EUR million) by region.

        CS change ≈ -ΔP × QD0 - ½ΔP × ΔQD  (consumer surplus)
        PS change ≈  ΔP × QS0 + ½ΔP × ΔQS  (producer surplus)
        Budget     = tariff revenue           (government budget)
        """
        welfare_rows = []

        for region in self.regions:
            cs, ps, budget = 0.0, 0.0, 0.0

            for comm in self.commodities:
                wp0 = self.world_prices_base[comm]
                wp1 = world_prices.get(comm, self.world_prices_base[comm])
                dp0 = wp0  # baseline domestic ≈ world (no tariff change)
                dp1 = domestic_prices.at[region, comm] if (
                    region in domestic_prices.index and comm in domestic_prices.columns
                ) else wp1

                qd0 = self.base_consumption.at[region, comm] if (
                    region in self.base_consumption.index
                ) else 0.0
                qd1 = demand.at[region, comm] if region in demand.index else 0.0
                qs0 = self.base_production.at[region, comm] if (
                    region in self.base_production.index
                ) else 0.0
                qs1 = supply.at[region, comm] if region in supply.index else 0.0

                delta_p_cons = dp1 - dp0
                delta_p_prod = wp1 - wp0

                # Consumer surplus (negative when price rises)
                cs += -(delta_p_cons * qd0 + 0.5 * delta_p_cons * (qd1 - qd0))

                # Producer surplus
                ps +=  (delta_p_prod * qs0 + 0.5 * delta_p_prod * (qs1 - qs0))

                # Budget / tariff revenue
                tariff = self.tariffs.at[region, comm] if (
                    region in self.tariffs.index and comm in self.tariffs.columns
                ) else 0.0
                imports = max(0.0, qd1 - qs1)
                budget += (tariff / 100.0) * wp1 * imports

            welfare_rows.append({
                "region": region,
                "consumer_surplus": cs / 1e3,   # EUR billion
                "producer_surplus": ps / 1e3,
                "budget_effect":    budget / 1e3,
                "total_welfare":   (cs + ps + budget) / 1e3,
            })

        return pd.DataFrame(welfare_rows).set_index("region")

