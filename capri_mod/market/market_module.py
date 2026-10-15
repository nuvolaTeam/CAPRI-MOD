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
from capri_mod.data.definitions import (
    MARKET_COMMODITIES, ALL_TRADE_REGIONS,
)


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
    #: world price x (1 + tariff) for every region - the price before the EU
    #: Armington premium (domestic_prices carries the EU's producer price)
    wedge_prices: Optional[pd.DataFrame] = None
    #: EU biofuel block at the equilibrium (MarketModule.biofuel_feedstock_use): feedstock use by
    #: commodity and by feedstock, biofuel output (kt)
    biofuel: Optional[dict] = None
    #: EU dairy block at the equilibrium (MarketModule.dairy_block): price ratios of the products,
    #: raw milk, fat and protein; production of the nine products and raw milk delivered (kt)
    dairy: Optional[dict] = None


# ---------------------------------------------------------------------------
# ARMINGTON DEMAND SYSTEM
# ---------------------------------------------------------------------------

class ArmingtonDemand:
    """
    CES/Armington demand aggregator for a single trade region and commodity.

    Computes import demand allocation across origins given prices.

    The CES aggregator:
        Q_total = [Σ_j δ_j × q_j^((σ-1)/σ)]^(σ/(σ-1))
    implies:
        q_j / q_k = (δ_j / δ_k) × (p_k / p_j)^σ    (Armington demand)
    """

    def __init__(self, sigma: float, base_shares: pd.Series, base_price: float):
        """
        Parameters
        ----------
        sigma      : Armington substitution elasticity
        base_shares: baseline import shares by origin (sums to 1)
        base_price : baseline aggregate import price index
        """
        self.sigma       = sigma
        self.base_shares = base_shares / base_shares.sum()
        self.base_price  = base_price
        # CES share parameters δ_j (calibrated to base shares)
        # At base: δ_j ∝ s_j (share) when prices equal
        self.delta = self.base_shares.copy()

    def price_index(self, prices_by_origin: pd.Series) -> float:
        """
        CES price index (Armington composite price).
        P = [Σ_j δ_j × p_j^(1-σ)]^(1/(1-σ))
        """
        p = prices_by_origin.reindex(self.delta.index).fillna(
            prices_by_origin.mean()
        ).values
        d = self.delta.values
        s = self.sigma

        if s == 1.0:
            # Cobb-Douglas case
            return float(np.prod(p ** d))
        else:
            exponent = 1 - s
            val = (d * p ** exponent).sum()
            if val <= 0:
                return float(prices_by_origin.mean())
            return float(val ** (1.0 / exponent))

    def import_shares(self, prices_by_origin: pd.Series) -> pd.Series:
        """
        Armington import shares: s_j = δ_j × (P/p_j)^σ
        """
        P = self.price_index(prices_by_origin)
        p = prices_by_origin.reindex(self.delta.index).fillna(
            prices_by_origin.mean()
        )
        shares = self.delta * (P / p.clip(lower=0.01)) ** self.sigma
        shares = shares / shares.sum()   # normalise to sum to 1
        return shares

    def import_quantities(
        self,
        total_imports: float,
        prices_by_origin: pd.Series,
    ) -> pd.Series:
        """Allocate total import quantity across origins."""
        shares = self.import_shares(prices_by_origin)
        return shares * total_imports


# ---------------------------------------------------------------------------
# MARKET MODULE
# ---------------------------------------------------------------------------

class MarketModule:
    """
    Global agricultural market model.

    Solves for world prices that clear markets in all commodities
    simultaneously, given supply quantities from the supply module
    and demand functions.

    Convergence algorithm:
      Tatonnement / Newton iterations on excess demand:
        P_{t+1} = P_t × (1 + α × ED_t / QS_t)
      until max|ED| < tolerance.
    """


    #: market equilibrium method: "root" (default: SciPy Newton-type solve of the
    #: excess-demand equations; full-EU Farm-to-Fork residuals 1e-13 to 1e-16, one
    #: outer iteration fewer, same results within 0.2 points) or "tatonnement"
    #: (excess-demand price adjustment to 1%; also the automatic fallback)
    market_solver = "root"
    def __init__(self, data: dict):
        self.data       = data
        self.commodities = MARKET_COMMODITIES
        self.regions    = ALL_TRADE_REGIONS
        self.n_comm     = len(self.commodities)
        self.n_reg      = len(self.regions)

        # Base data
        self.world_prices_base = data["world_prices"].reindex(
            self.commodities).fillna(200.0)
        self.tariffs       = data["tariffs"]
        self.trade_flows_base = data["trade_flows"]
        self.armington     = data["armington"]
        self._demand_cal   = None  # set by _calibrate_demand_to_supply at solve time

        # Calibrate Armington aggregators
        self._build_armington_systems()

        # Compute baseline consumption and production
        self._calibrate_baseline()
        # Pristine base tables, restored at every baseline reset (see
        # CAPRIModel.run): EU rows of commodities WITHOUT farm-model supply
        # (oils, cakes, rice, fats, other food) are not re-aligned per run, so
        # whatever an earlier run left there persisted into later runs.
        self._base_production0 = self.base_production.copy()
        self._base_consumption0 = self.base_consumption.copy()

    def _build_armington_systems(self):
        """Build Armington demand aggregators for each (region, commodity)."""
        self.armington_systems: Dict[Tuple[str,str], ArmingtonDemand] = {}

        for comm in self.commodities:
            sigma = self.armington.at[comm, "sigma"] if comm in self.armington.index else 3.0

            for importer in self.regions:
                # Base import shares from trade flows
                flows = self.trade_flows_base
                total_imports = 0.0
                shares_dict = {}

                for exporter in self.regions:
                    if exporter == importer:
                        continue
                    if (exporter, importer) in flows.index and comm in flows.columns:
                        val = flows.at[(exporter, importer), comm]
                        if val > 0:
                            shares_dict[exporter] = val
                            total_imports += val

                if total_imports < 1.0:
                    # Tiny importer — allocate uniformly across major exporters
                    major = [r for r in self.regions if r != importer][:5]
                    shares_dict = {r: 1.0 for r in major}

                base_shares = pd.Series(shares_dict)
                base_price = self.world_prices_base.get(comm, 200.0)

                self.armington_systems[(importer, comm)] = ArmingtonDemand(
                    sigma=sigma,
                    base_shares=base_shares,
                    base_price=base_price,
                )

    def _calibrate_baseline(self):
        """
        Calibrate baseline production and consumption.

        Uses FAOSTAT-approximate world totals allocated across trade regions
        via fixed production shares. Consumption = Production + NetImports,
        ensuring markets balance at baseline world prices.
        """
        flows = self.trade_flows_base
        comms = self.commodities
        regions = self.regions

        self.base_production  = pd.DataFrame(0.0, index=regions, columns=comms)
        self.base_consumption = pd.DataFrame(0.0, index=regions, columns=comms)

        # FAOSTAT-approximate world production totals (1000 t, ~2012 baseline)
        world_prod_ref = {
            "SWHE": 780000, "DWHE": 40000,  "BARL": 155000, "CORN": 1150000,
            "OCER": 80000,  "RAPE": 72000,  "SUNF": 55000,  "SOYA": 370000,
            "SUGB": 1900000,"SUGR": 180000, "POTA": 370000,
            "PULS": 88000,  "TOMA": 180000, "OVEG": 900000, "APPL": 85000,
            "OFRU": 220000, "CITR": 145000, "WINE": 70000,  "OLIV": 20000,
            "MILK": 900000, "BUTR": 11000,  "SKIM": 8000,   "CHES": 22000,
            "WHEY": 15000,  "BEEF": 70000,  "PORK": 120000, "POUL": 130000,
            "SHGM": 15000,  "EGGS": 80000,  "FATS": 25000,  "OFOD_M": 50000,
            # sum of the 21 trade regions, CAPRI FAO_agg p_dataMarket BAS
            "RAPO": 22725, "SUNO": 14962, "SOYO": 50892, "RAPC": 30983, "SUNC": 16028, "SOYC": 215197,
        }

        # Production shares by trade region (must sum to ~1.0)
        prod_share_base = {
            "EU27": 0.18, "USA": 0.12, "CHN": 0.22, "IND": 0.11,
            "BRA":  0.09, "RUS": 0.06, "IDN": 0.04, "JPN": 0.02,
            "MEX":  0.02, "ARG": 0.05, "AUS": 0.03, "NZL": 0.01,
            "CAN":  0.03, "TUR": 0.02, "KOR": 0.01, "THA": 0.02,
            "VNM":  0.01, "PAK": 0.02, "BGD": 0.01, "NGA": 0.02,
            "ZAF":  0.01, "ETH": 0.01, "EGY": 0.01, "MAR": 0.01,
            "DZA":  0.005,"SAU": 0.005,"IRN": 0.01, "ROW": 0.07,
        }
        # Normalise so shares sum to 1 across known regions
        total_share = sum(prod_share_base.get(r, 0.005) for r in regions)
        prod_share  = {r: prod_share_base.get(r, 0.005) / total_share for r in regions}

        rng = np.random.default_rng(123)

        # Real production for NON-EU trade regions only (CAPRI FAO_agg SUA).
        # Real bilateral trade flows are now used for the net-trade identity.
        # EU27 base is left synthetic because its supply is overridden by the
        # supply module at solve time; injecting real EU27 levels unbalances
        # the base (supply-module output != SUA consumption at base price).
        real_world = {}
        try:
            import json as _json
            from pathlib import Path as _P
            from capri_mod.data.loaders import resolve_data_file
            _b = _P(__file__).parent.parent.parent / "capri_data"
            f = resolve_data_file(_b, "fao_market_baseline.json")
            if f.exists():
                raw = _json.load(open(f))
                for key, rec in raw.items():
                    r, c = key.split("|")
                    if (r != "EU27" or c in ("RAPO", "SUNO", "SOYO", "RAPC", "SUNC", "SOYC")) \
                            and rec.get("production", 0) > 0:
                        real_world[(r, c)] = rec["production"]
            # Extended coverage from CAPRI's own FAO_agg SUA (p_dataMarket,
            # item MAPR). Same source family as the file above, so the vintage
            # is consistent; it adds the trade regions that were missing
            # entirely (DZA, ETH, MAR, TUR, KOR via ALG/MOR/SKOR) and fills
            # commodity gaps in regions already covered. Loaded SECOND and only
            # where the primary file has no value, so the existing, validated
            # cells are never displaced -- the market price test reproduces
            # CAPRI's PMRK 12/12 off those, and this must not disturb them.
            f2 = _b / "sources" / "fao_agg_2017" / "fao_agg_sua_2017_extended.json"
            if f2.exists():
                raw2 = _json.load(open(f2))
                # FAO names paddy rice RICE; this model's activity is PARI.
                # Reading the file without the alias would drop rice silently,
                # the same failure as the MAIZ/CORN and TWIN/WINE codes.
                FAO_ALIASES = {"RICE": "PARI"}
                for key, rec in raw2.items():
                    r, c = key.split("|")
                    c = FAO_ALIASES.get(c, c)
                    if r == "EU27" or (r, c) in real_world:
                        continue
                    if rec.get("production", 0) > 0:
                        real_world[(r, c)] = rec["production"]
        except Exception:
            real_world = {}
        # DAIRY PRODUCTS: every region's base production from CAPRI's FAO_agg (dairy Stage 2,
        # tools/build_dairy_world_markets.py), the world total their sum. The FAO_agg codes BUTT,
        # SMIP, WHEP never matched the market's BUTR, SKIM, WHEY (so every region got an invented
        # share of a hard-coded world total) and the primary file's cheese item is not cheese (USA 28 kt
        # against CAPRI's 5,889).
        try:
            import json as _json
            from pathlib import Path as _P
            _fd = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "market" / "dairy_world_baseline.json"
            if _fd.exists():
                _bal = _json.load(open(_fd))["balances"]
                _dc = {k.split("|")[1] for k in _bal}
                for c in _dc:
                    if c not in comms:
                        continue
                    world_prod_ref[c] = sum(float(v.get("production", 0.0)) for k, v in _bal.items()
                                            if k.endswith("|" + c))
                    for r in regions:
                        real_world[(r, c)] = float(_bal.get(f"{r}|{c}", {}).get("production", 0.0))
        except Exception:
            pass

        # EVERY REGION'S BASE BALANCE FROM CAPRI'S FAO_agg (tools/build_world_market_baseline.py), the world
        # total their sum: one CAPRI source for all commodities it covers, replacing the mix above (whose sugar
        # was sugar cane, and whose pork, eggs and maize totals were 40-50% above CAPRI's). Commodities without
        # a CAPRI world balance (DWHE, PARI, OOIL, OLIV) keep the previous base.
        try:
            import json as _json
            from pathlib import Path as _P
            _fw = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "market" / "world_market_baseline.json"
            if _fw.exists():
                _bal = _json.load(open(_fw))["balances"]
                self._capri_world_balance = _bal
                for c in {k.split("|")[1] for k in _bal}:
                    if c not in comms:
                        continue
                    world_prod_ref[c] = sum(float(v.get("production", 0.0)) for k, v in _bal.items()
                                            if k.endswith("|" + c))
                    for r in regions:
                        real_world[(r, c)] = float(_bal.get(f"{r}|{c}", {}).get("production", 0.0))
        except Exception:
            pass

        for comm in comms:
            w_prod = world_prod_ref.get(comm, 10000)

            # Pre-compute net trade per region from baseline flows
            net_exports = {r: 0.0 for r in regions}
            for exporter in regions:
                for importer in regions:
                    if exporter == importer:
                        continue
                    key = (exporter, importer)
                    if key in flows.index and comm in flows.columns:
                        v = float(flows.at[key, comm])
                        net_exports[exporter] += v
                        net_exports[importer] -= v

            # Assign production first, then reconcile the world total.
            #
            # Production is drawn as w_prod * prod_share (which sums to w_prod),
            # but the real_world SUA overrides replace individual regions, so the
            # total drifts away from w_prod — for oilseeds it landed ~27% high
            # (RAPE 91.6 kt against a 72 kt reference, SOYA 472 against 370).
            # Consumption is then derived from the trade identity against that
            # inflated production, leaving world demand ~21% above world supply
            # at base prices. The market solver, working correctly, drove RAPE
            # and SOYA prices 34% and 65% below reference to clear a market that
            # was never balanced — which is what the price-reproduction test had
            # been failing on. Rescaling the non-overridden regions restores
            # sum(production) == w_prod while keeping the SUA levels exact.
            raw_prod, overridden = {}, {}
            for region in regions:
                ps = prod_share[region]
                if (region, comm) in real_world:
                    overridden[region] = max(1.0, real_world[(region, comm)])
                else:
                    # Residual regions take their production share of whatever
                    # the real sources do not cover. A +/-8% random multiplier
                    # used to be applied here; it was seeded, so it was
                    # reproducible, but it was invented variation presented as
                    # data and it served no modelling purpose. Removed: the
                    # allocation is now a deterministic share.
                    #
                    # This affects little. After the FAO_agg extension only 6.7%
                    # of world production is allocated this way, and 5.9 points
                    # of that is ROW, a residual aggregate by construction; the
                    # only genuinely allocated countries are Iran (0.54%) and
                    # Saudi Arabia (0.25%), which CAPRI's own FAO aggregate does
                    # not separate from MIDEAST either.
                    raw_prod[region] = max(1.0, w_prod * ps)

            fixed_total = sum(overridden.values())
            free_total = sum(raw_prod.values())
            target_free = w_prod - fixed_total
            if free_total > 0 and target_free > 0:
                scale = target_free / free_total
                raw_prod = {r: max(1.0, v * scale) for r, v in raw_prod.items()}

            for region in regions:
                prod = overridden.get(region, raw_prod.get(region, 1.0))
                # A region cannot export more than it produces. Where the SUA
                # override or the drawn share leaves production below net
                # exports, raw consumption goes NEGATIVE and the max(1.0, ...)
                # clamp below silently FABRICATES consumption out of nothing —
                # this was the entire source of the base-year oilseed imbalance
                # (ROW "produced" 1094 kt of soy while exporting 123407, and the
                # clamp injected exactly the 122314 kt by which world demand
                # exceeded world supply). Raising production to cover net
                # exports keeps the trade identity feasible and leaves the
                # clamp with nothing to invent.
                ne = net_exports.get(region, 0.0)
                if region == "EU27":
                    self._base_net_exports_eu = getattr(self, "_base_net_exports_eu", {})
                    self._base_net_exports_eu[comm] = ne
                if ne > 0 and prod < ne:
                    prod = ne
                cons = max(1.0, prod - ne)

                self.base_production.at[region, comm]  = prod
                self.base_consumption.at[region, comm] = cons

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
                self.base_consumption.at[region, "DDGS"] = (float(fb.get("feed0", {}).get("DDGS", q))
                                                            if region == "EU27" else q)
        # RESIDUAL FEEDS (CAPRI MaprFeed_, Sprint 9h): the EU's output and feed use of the 2030 reference; the other
        # regions' bases come from the bilateral market at calibration
        fp = self._feed_byproduct_params()
        if fp and "EU27" in regions:
            fb = self._feed_bulk_params()
            for p, d in fp["products"].items():
                if p in comms:
                    self.base_production.at["EU27", p] = d["prod0"]
                    self.base_consumption.at["EU27", p] = float(fb.get("feed0", {}).get(p, d["prod0"]))

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
        wp = pd.Series({c: float(world_prices.get(c, 200.0))
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
    biofuel_markets: bool = True
    BIOFUELS = ("BIOE", "BIOD")

    def _biofuel_params(self) -> dict:
        """First-generation biofuel feedstock demand, CAPRI's market equations (biofFeedCost_, biofFeedCostAgg_,
        Biof_, prodBiof_, prodQuantBiofBy_), per CAPRI market region.

        From capri_data/2017/market/biofuel_feedstock.csv (tools/build_biofuel_market.py): per CAPRI region and
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
                        if gr["region"] == "EU27" and c in share:
                            q0c[c] = q0c.get(c, 0.0) + float(q)
                dd0[gr["region"]] = dd0.get(gr["region"], 0.0) + float((gr["q0"] * gr["prcby"] * gr["ddgs"]).sum())
            out = {"groups": groups, "share": share, "q0": q0c, "q0_reg": q0r, "ddgs0": dd0} if groups else {}
        except Exception:
            out = {}
        self._biof_cache = out
        return out

    def _biofuel_market_params(self) -> dict:
        """CAPRI's biofuel supply and demand functions per CAPRI market region (biofuel/def_biofuel_params.gms,
        calibrated by tools/build_biofuel_market.py to the 2030 reference): {(ms, fuel): row} plus the region
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
                if r.region not in self.regions or r.biofuel not in self.commodities:
                    continue
                d = r._asdict()
                d["group"] = gidx.get((r.ms, r.biofuel))
                # CAPRI's mandate scenario (scen/bio_fuels/change_biof_mandate.gms) shifts the EU member states'
                # and the UK's QUTS
                d["mandate_region"] = (r.region == "EU27") or (r.ms == "UK000000")
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
        mand = float(getattr(self, "biofuel_mandate", 1.0) or 1.0)
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
    #: CAPRI dairy product -> the model's market commodity (traded products); the other five
    #: (FRMI, CREM, COCM, WMIO, CASE) clear inside the EU dairy block
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
    use_dairy_block = True

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
        """The EU dairy block (tools/build_dairy_processing.py): CAPRI's three equations per member state
        (_dairy_algebra), EU-common price ratios applied to each member state's own 2030-reference level
        (CAPRI prices raw milk, fat and protein per member state: REGISTERED), raw milk delivered from the
        EU supply models; food demand among the nine products with CAPRI's own and cross elasticities;
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
        except Exception:
            out = {}
        self._dairy_cache = out
        return out

    def _dairy_world_params(self) -> dict:
        """CAPRI's dairy block for the non-EU trade regions (dairy Stage 4, tools/build_dairy_world_blocks.py):
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
        zt = np.zeros(n)
        for k, rho in traded_ratio.items():
            if k in dp["ix"]:
                zt[dp["ix"][k]] = float(rho) - 1.0
        Q = np.zeros(len(items)); Q0 = np.zeros(len(items)); proc0 = np.zeros(len(items))
        vm = vf = vp = vm0 = vf0 = vp0 = 0.0
        msr = {}
        for ms, prm in dp["ms"].items():
            mr = float(milk_ratio.get(ms, 1.0)) if isinstance(milk_ratio, dict) else float(milk_ratio)
            z = self._dairy_solve_ms(prm, zt, mr)
            Q += prm["Q0"] + prm["G"] @ z
            Q0 += prm["Q0"]; proc0 += prm["proc0"]
            msr[ms] = {"MILK": 1.0 + z[prm["iM"]], "FATS": 1.0 + z[prm["iF"]], "PROT": 1.0 + z[prm["iP"]],
                       "milk_delivered": mr}
            # EU aggregates for reporting: weights = the member state's base raw milk (fat, protein in it)
            w = prm["Q0"][prm["iM"]]
            vm += w * msr[ms]["MILK"]; vm0 += w
            vf += w * msr[ms]["FATS"]; vp += w * msr[ms]["PROT"]
        ix = dp["ix"]
        res = {"price_ratio": {**{k: (1.0 + zt[ix[k]]) for k in items if k != "MILK"},
                               "MILK": vm / vm0, "FATS": vf / vm0, "PROT": vp / vm0},
               "ms_price_ratio": msr,
               "production": {k: float(Q[ix[k]]) for k in items},
               "production0": {k: float(Q0[ix[k]]) for k in items},
               "market_supply": {self.DAIRY_TRADED[k]: float(Q[ix[k]] - proc0[ix[k]]) for k in self.DAIRY_TRADED},
               "market_supply0": {self.DAIRY_TRADED[k]: float(Q0[ix[k]] - proc0[ix[k]]) for k in self.DAIRY_TRADED},
               "fmil_index": float(getattr(self, "_fmil_index", 1.0) or 1.0), "residual": 0.0}
        return res

    #: model country -> CAPRI member state of the dairy block
    _DAIRY_MS = {"BE": "BL", "LU": "BL", "IE": "IR", "GR": "EL"}

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
        wedge price x the current EU Armington premium (lagged within an outer iteration)."""
        dom = self.domestic_prices(world_prices, getattr(self, "_trade_scenario_now", None))
        d0 = getattr(self, "_dom0_cache", None)
        if d0 is None:
            d0 = self.domestic_prices(self.world_prices_base)
            self._dom0_cache = d0
        bl = getattr(self, "_bilat_ratio_now", None)
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
        """EU feedstock use for biofuels at EU feedstock prices (relative to base), CAPRI's equations
        (MarketModule._biofuel_feed_group); first-generation output from the biofuel market when endogenous,
        else the 2030-reference output x biofuel_output_scale. Returns {"by_commodity": {c: kt},
        "by_feedstock": {(fuel, feedstock): kt}, "output": {fuel: kt}} (output: first generation).
        """
        byc, byf, outp = {}, {}, {}
        for g in self._biofuel_params().get("groups", []):
            if g["region"] != "EU27":
                continue
            X = self._biofuel_x(g)
            st = getattr(self, "_biof_state", None)
            q, _ = self._biofuel_feed_group(g, price_ratio, X, float((st or {}).get("ddgs_ratio", {}).get("EU27", 1.0)))
            outp[g["fuel"]] = outp.get(g["fuel"], 0.0) + X
            for c, f, x in zip(g["comm"], g["feed"], q):
                byf[(g["fuel"], f)] = byf.get((g["fuel"], f), 0.0) + float(x)
                if c:
                    byc[c] = byc.get(c, 0.0) + float(x)
        return {"by_commodity": byc, "by_feedstock": byf, "output": outp}

    def _feed_bulk_params(self) -> dict:
        """CAPRI's feed bulks of the member states (arm/market_model.gms feedBlkPrice_, feedShareEqu_;
        tools/build_feed_bulks.py): per (member state, bulk) the products' model commodities, 2030 feed quantities,
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
            feed0 = {}
            for (ms, b), d in bulks.items():
                for c, q in zip(d["comm"], d["q0"]):
                    if c:
                        feed0[c] = feed0.get(c, 0.0) + float(q)
            share = {str(r.commodity): float(r.share) for r in sh.itertuples()
                     if r.commodity in self.commodities and r.commodity in feed0}
            out = {"bulks": bulks, "feed0": feed0, "share": share} if bulks else {}
        except Exception:
            out = {}
        self._fbulk_cache = out
        return out

    def feed_bulk_price_ratio(self, ms: str, bulk: str, price_ratio: Dict[str, float]) -> float:
        """CAPRI's bulk price index (feedBlkPrice_) of a member state relative to the reference:
        (sum_i s_i (p_i / p_i0)^(1 - rho))^(1 / (1 - rho)), s_i the reference value shares; products without a
        model market at the reference price. 1 where the member state has no such bulk."""
        d = (self._feed_bulk_params().get("bulks") or {}).get((ms, bulk))
        if d is None:
            return 1.0
        r = np.array([max(float(price_ratio.get(c, 1.0)), 1e-6) if c else 1.0 for c in d["comm"]])
        rho = d["rho"]
        return float((d["s"] * r ** (1.0 - rho)).sum()) ** (1.0 / (1.0 - rho))

    def eu_feed_use(self, price_ratio: Dict[str, float]) -> Dict[str, float]:
        """EU feed use per model commodity (kt) from the member states' bulks at the EU price ratios (CAPRI
        feedShareEqu_): q_i = q_i0 x (B / B0) x (P_B / p_i)^rho with prices relative to the reference; B / B0 from
        the supply models (_feed_bulk_index, 1 before any supply result)."""
        fb = self._feed_bulk_params()
        bix = getattr(self, "_feed_bulk_index", None) or {}
        out = {}
        for (ms, b), d in (fb.get("bulks") or {}).items():
            r = np.array([max(float(price_ratio.get(c, 1.0)), 1e-6) if c else 1.0 for c in d["comm"]])
            rho = d["rho"]
            pb = float((d["s"] * r ** (1.0 - rho)).sum()) ** (1.0 / (1.0 - rho))
            q = d["q0"] * float(bix.get((ms, b), 1.0)) * (pb / r) ** rho
            for c, x in zip(d["comm"], q):
                if c:
                    out[c] = out.get(c, 0.0) + float(x)
        return out

    def _feed_byproduct_params(self) -> dict:
        """CAPRI's residual feeds (MaprFeed_; tools/build_feed_byproducts.py): per product the EU's 2030 output and
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
            if prods:
                out = {"products": prods,
                       "parents": {c for d in prods.values() for c, _, _ in d["parts"] if c in self.commodities}}
        except Exception:
            out = {}
        self._fbyp_cache = out
        return out

    def eu_feed_byproduct_output(self) -> Dict[str, float]:
        """EU output of the residual feeds (CAPRI MaprFeed_): prod0 x sum over the parents of weight x the
        parent's current food response (food and processing use) or biofuel feedstock use relative to the
        reference, from the last demand evaluation (1 before any)."""
        fp = self._feed_byproduct_params()
        fr = getattr(self, "_eu_food_ratio", None) or {}
        br = getattr(self, "_eu_biof_ratio", None) or {}
        out = {}
        for p, d in (fp.get("products") or {}).items():
            x = sum(w * float((br if use == "biofuel" else fr).get(c, 1.0)) for c, use, w in d["parts"])
            out[p] = d["prod0"] * x
        return out

    def _apply_feed_byproduct_supply(self, S: pd.DataFrame) -> None:
        if "EU27" not in S.index:
            return
        for p, q in self.eu_feed_byproduct_output().items():
            if p in S.columns:
                S.at["EU27", p] = max(0.0, q)

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
                if r in self.regions and r != "EU27" and c in self.commodities:
                    out[(r, c)] = {"feed_share": float(v["feed_share"]),
                                   "elasticities": {k: float(x) for k, x in v["elasticities"].items() if k in self.commodities}}
        except Exception:
            out = {}
        self._fdp_cache = out
        return out

    def _crush_params(self) -> dict:
        """(region, seed) -> base crush, yields, elasticity and base margin terms.

        CAPRI data (crushing_parameters.json): crush = the seed's industrial use,
        yields = oil and cake production / crush, elasticity = p_ElasProc. Pairs
        whose yields are physically impossible (oil + cake > 1.05 t per t, or a
        yield outside 0.1-0.95) keep simple supply curves - three such pairs in
        CAPRI's base data (UKR rapeseed, JPN sunflower, PAK soybeans).
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
                    tuple(round(float((getattr(self, "_eu_aligned_use", None) or {}).get(c, 0.0)), 6)
                          for c in ("RAPE", "SUNF", "SOYA")))
        except Exception:
            _key = None
        cached = getattr(self, "_crush_cache", None)
        if cached is not None and _key is not None and getattr(self, "_crush_cache_key", None) == _key:
            return cached
        self._crush_cache_key = _key
        out = {}
        try:
            import json as _json
            from pathlib import Path as _P
            f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "market" / "crushing_parameters.json"
            raw = _json.load(open(f))["parameters"]
            base_dom = self.domestic_prices(self.world_prices_base)
            for key, v in raw.items():
                r, s = key.split("|")
                if r not in self.regions or s not in self.CRUSH_CHAINS or v.get("elasticity") is None:
                    continue
                yo, yc = float(v["oil_yield"]), float(v["cake_yield"])
                if not (0.1 <= yo <= 0.95 and 0.1 <= yc <= 0.95 and yo + yc <= 1.05):
                    continue
                o, c = self.CRUSH_CHAINS[s]
                q0 = float(v["crush_kt"])
                _ov = (getattr(self, "_crush_q0_override", None) or {}).get((r, s))
                if _ov is not None:
                    q0 = float(_ov)       # bilateral market: CAPRI's cake production of the market year / yield
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
                    _al = getattr(self, "_eu_aligned_use", None) or {}
                    b = float(_al.get(s, self.base_consumption.at["EU27", s] if s in self.base_consumption.columns else 0.0))
                    if share > 0 and b > 0:
                        q0 = share * b
                ps, po, pc = (float(base_dom.at[r, x]) for x in (s, o, c))
                gross = yo * po + yc * pc               # CAPRI: seed price + margin
                out[(r, s)] = dict(q0=q0, yo=yo, yc=yc, eps=float(v["elasticity"]),
                                   m0=gross - ps, gross=max(gross, 1.0))
        except Exception:
            out = {}
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
            if r != "EU27":
                continue
            o, c = self.CRUSH_CHAINS[s]
            tot[o] = tot.get(o, 0.0) + p["q0"] * p["yo"]
            tot[c] = tot.get(c, 0.0) + p["q0"] * p["yc"]
        for prod, v in tot.items():
            if prod in self.base_production.columns and v > 0:
                self.base_production.at["EU27", prod] = v
                if prod in base_supply.columns:
                    base_supply.at["EU27", prod] = v
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
        for (r, s), p in self._crush_params().items():
            o, c = self.CRUSH_CHAINS[s]
            i = _ri[r]
            m = p["yo"] * float(_v[i, _ci[o]]) + p["yc"] * float(_v[i, _ci[c]]) - float(_v[i, _ci[s]])
            out[(r, s)] = max(0.01 * p["q0"], p["q0"] * (1.0 + p["eps"] * (m - p["m0"]) / p["gross"]))
        return out

    def supply_response(
        self,
        world_prices: pd.Series,
        exogenous_supply: Optional[pd.DataFrame] = None,
        region_ratio: Optional[pd.DataFrame] = None,
        crush_dom: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Supply quantities by region and commodity (1000 t).
        If exogenous_supply is given (from supply module), use it for EU27.
        Otherwise, apply supply elasticity to price signal.

        region_ratio (bilateral market): each region's own market price relative to base, region x commodity; the
        supply elasticity then applies to the region's own price, the EU's supply-module output is
        anticipated against the EU price farmers last saw, and crushing and the dairy blocks see the
        regional prices (crush_dom: the price levels the crushers face).
        """
        if exogenous_supply is not None:
            # Only override the EU27 row with the supply-module output; keep
            # all other trade regions (USA, BRA, CHN, ROW, ...) at their
            # calibrated base production. Otherwise global supply collapses to
            # the EU subset and excess demand explodes.
            supply = self.base_production.copy()
            for comm in exogenous_supply.columns:
                if comm not in supply.columns:
                    continue
                eu_val = exogenous_supply[comm].sum()
                if eu_val > 0 and "EU27" in supply.index:
                    supply.at["EU27", comm] = eu_val
        else:
            supply = self.base_production.copy()

        # Own-price supply elasticities from CAPRI's calibrated market model
        # (elas1717 p_elasSupp, EU medians). These replace the crop-oriented
        # Armington eps column, which stood in a blanket 0.15-0.25 for every
        # commodity -- including livestock, where CAPRI's real values are
        # 0.55-0.76. Commodities not in the file keep the eps fallback.
        real_supply = getattr(self, "_real_supply_elas", None)
        if real_supply is None:
            real_supply = {}
            try:
                from capri_mod.data.loaders import resolve_data_file
                import json as _json
                _b = resolve_data_file("capri_data", "sources/arm")
                _f = resolve_data_file(_b, "supply_elas_eu_all.json")
                real_supply = _json.loads(open(_f).read())
            except Exception:
                real_supply = {}
            self._real_supply_elas = real_supply

        eps = self.armington["eps"] if "eps" in self.armington.columns else pd.Series(0.25, index=self.commodities)

        # Vectorised over commodities; arithmetic unchanged.
        ratio = pd.Series({
            c: float(world_prices.get(c, 200.0))
               / max(float(self.world_prices_base.get(c, 200.0)), 0.01)
            for c in self.commodities})
        el = pd.Series({
            c: (float(real_supply[c]) if c in real_supply
                else (float(eps.get(c, 0.25)) if hasattr(eps, "get") else 0.25))
            for c in self.commodities})
        factor = ratio.pow(el)
        cols = [c for c in self.commodities if c in supply.columns]
        if region_ratio is None:
            supply[cols] = supply[cols].mul(factor[cols], axis=1).clip(lower=0.0)
        else:
            # in arrays (pandas arithmetic here was a sizeable share of each market evaluation; same values)
            rr = region_ratio.reindex(index=supply.index, columns=cols).to_numpy(dtype=float)
            rr = np.maximum(np.where(np.isnan(rr), 1.0, rr), 1e-6)
            ev = el.reindex(cols).to_numpy(dtype=float)
            fac = rr ** ev[None, :]
            if "EU27" in supply.index:
                ie_ = list(supply.index).index("EU27")
                seen = getattr(self, "_eu_price_seen", None)
                sv = (np.maximum(np.nan_to_num(seen.reindex(cols).to_numpy(dtype=float), nan=1.0), 0.2)
                      if seen is not None else np.ones(len(cols)))
                fac[ie_] = (rr[ie_] / sv) ** ev
            supply[cols] = np.maximum(supply[cols].to_numpy(dtype=float) * fac, 0.0)
        # CRUSHING: oil and cake supply = crush x yields (CAPRI ProcO_, Leontief)
        cp = self._crush_params()
        if cp:
            crush = self.crush_quantities(crush_dom if crush_dom is not None else
                                          self.domestic_prices(world_prices, getattr(self, "_trade_scenario_now", None)))
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
        if self._dairy_params() and "EU27" in supply.index:
            S = float(exogenous_supply["MILK"].sum()) if (exogenous_supply is not None and "MILK" in exogenous_supply.columns) \
                else float(self.base_production.at["EU27", "MILK"])
            S0 = float(getattr(self, "_dairy_S0", None) or S)
            _m0 = getattr(self, "_dairy_S0_ms", None) or {}
            _m = self._milk_by_ms(exogenous_supply)
            _mr = ({ms: (_m[ms] / q0 if (q0 > 0 and ms in _m) else 1.0) for ms, q0 in _m0.items()} if (_m0 and _m)
                   else (S / S0 if S0 > 0 else 1.0))
            res = self.dairy_block(self._dairy_eu_prices(world_prices), _mr)
            if res is not None:
                supply.at["EU27", "MILK"] = S
                for c, q in res["market_supply"].items():
                    if c in supply.columns:
                        supply.at["EU27", c] = max(0.0, q)
                self._eu_milk_supply_now = S
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
            for r, prm in wpar.items():
                if r not in supply.index:
                    continue
                if region_ratio is not None:
                    tr = {k: float(region_ratio.at[r, c]) if c in region_ratio.columns else 1.0
                          for k, c in self.DAIRY_TRADED.items()}
                else:
                    tr = {k: float(dom.at[r, c]) / float(d0.at[r, c]) if float(d0.at[r, c]) > 0 else 1.0
                          for k, c in self.DAIRY_TRADED.items()}
                res_r = self._dairy_solve(prm, tr, None, 1.0, r)
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

        Faithful to CAPRI's Generalised Leontief demand structure in that
        quantity responds to own price AND to per-capita income (Engel effect):
            QD = QD0 × (P/P0)^eta × (Y/Y0)^income_elas
        where the income term is the demand-side counterpart of the GL
        expenditure function's dependence on income per capita. Cross-price
        effects are captured through the Armington layer.
        """
        demand = pd.DataFrame(index=self.regions, columns=self.commodities, dtype=float)

        # Per-capita income proxy from GDP index (relative to base = 100)
        income_ratio = getattr(self, "_income_ratio", None)
        if income_ratio is None:
            income_ratio = 1.0

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
        eta = pd.Series({
            c: float(real_dem[c]) if c in real_dem else
               (float(self.armington.at[c, "eta"])
                if c in self.armington.index else -0.25)
            for c in self.commodities})
        inc = pd.Series({c: float(self._income_elasticity(c))
                         for c in self.commodities})
        cal = pd.Series({c: float(self._demand_cal_factor(c))
                         for c in self.commodities})
        wp0 = pd.Series({c: max(float(self.world_prices_base.get(c, 200.0)), 0.01)
                         for c in self.commodities})
        fallback = pd.Series({c: float(world_prices.get(c, 200.0))
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
            base = self.base_consumption.reindex(index=self.regions, columns=self.commodities).fillna(100.0)
            _rc = (dom0, _bv.copy(), wp0, ref, base, list(self.base_consumption.index),
                   list(self.base_consumption.columns))
            self._demand_ref_cache = _rc
        ref, base = _rc[3], _rc[4]
        price_ratio = dp / ref

        demand = (base.mul(cal, axis=1)
                      * price_ratio.pow(eta, axis=1)
                      * inc.rpow(float(income_ratio)))
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
        INC = inc.reindex(self.commodities).values.astype(float)
        ir = float(income_ratio)
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
                food = float(PR[i, j]) ** float(ETA[j]) * ir ** float(INC[j])
                D[i, j] = b * ((1.0 - sh) * food + sh * ft)
        cp = self._crush_params()
        if cp:
            crush = self.crush_quantities(dp)
            for (r, sd), q in crush.items():
                i, j = R.get(r), Cc.get(sd)
                if i is None or j is None:
                    continue
                q0 = cp[(r, sd)]["q0"]; b = float(Bv[i, j])
                f = float(D[i, j]) / b if b > 0 else 0.0
                D[i, j] = max(0.0, (b - q0) * f + float(CAL[j]) * q0 + (q - q0))
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
        ie = R.get("EU27")
        if eu_eta and ie is not None:
            for _c, _e in eu_eta.items():
                j = Cc.get(_c)
                if j is not None:
                    D[ie, j] = (float(Bv[ie, j]) * float(CAL[j]) * float(PR[ie, j]) ** _e
                                * ir ** float(INC[j]))
        # EU FEED (CAPRI feedBlkPrice_, feedShareEqu_): the member states' feed bulks (cereals FCER, protein-rich
        # feed FPRO) follow their herds and rations (_feed_bulk_index, set from the supply models), and each
        # bulk is split into products with a CES on their prices (rho 6). The feed part of EU use of each product
        # (CAPRI's 2030 feed share) follows it; the rest keeps its food response.
        # Written as a correction of the row (feed part: bulk use instead of the food response), so that terms
        # added before (oilseed crushing, whose seeds are also fed whole: CAPRI's FOTH bulk) are kept; the same
        # as d0 ((1 - sh) rest + sh feed / f0) for the other rows (Sprint 9h).
        # The food response of the EU's use per commodity is kept for the residual feeds' output (MaprFeed_).
        fb = self._feed_bulk_params()
        self._eu_food_ratio = {}
        if ie is not None:
            for c in (self._feed_byproduct_params().get("parents") or ()):
                j = Cc.get(c)
                if j is not None:
                    self._eu_food_ratio[c] = float(PR[ie, j]) ** float(eu_eta.get(c, ETA[j])) * ir ** float(INC[j])
        self._eu_feed_now = None
        if fb and ie is not None:
            feed = self.eu_feed_use({c: float(PR[ie, Cc[c]]) for c in fb["feed0"] if c in Cc})
            self._eu_feed_now = feed
            for c, sh in fb["share"].items():
                j = Cc.get(c)
                f0 = fb["feed0"].get(c, 0.0)
                if j is None or f0 <= 0:
                    continue
                d0 = float(Bv[ie, j]) * float(CAL[j])
                if d0 <= 0:
                    continue
                rest = float(PR[ie, j]) ** float(eu_eta.get(c, ETA[j])) * ir ** float(INC[j])
                D[ie, j] = float(D[ie, j]) + d0 * sh * (feed.get(c, f0) / f0 - rest)
        # RAW MILK: the EU's milk goes to its dairies (the dairy block prices it); the EU takes no part
        # in the world raw-milk market (CAPRI: raw milk is not traded with third countries)
        if ie is not None and "MILK" in Cc and self._dairy_params() and getattr(self, "_eu_milk_supply_now", None):
            D[ie, Cc["MILK"]] = float(self._eu_milk_supply_now)
        # DAIRY PRODUCTS (dairy Stage 3): EU food use with CAPRI's own and cross-price elasticities among
        # the nine dairy products (p_ElasDem), EU feed use following the calves' milk feed (FMIL) with
        # CES substitution; the five EU-cleared products' prices come from the dairy block
        if ie is not None and self._dairy_params():
            _dp = self._dairy_params()
            _P9 = list(self.DAIRY_PRODUCTS)
            _dl = getattr(self, "_dairy_last", None) or {}
            _rho = np.array([float(PR[ie, Cc[self.DAIRY_TRADED[k]]]) if k in self.DAIRY_TRADED and self.DAIRY_TRADED[k] in Cc
                             else float((_dl.get("price_ratio") or {}).get(k, 1.0)) for k in _P9])
            _rho = np.maximum(_rho, 0.05)
            _food = np.exp(_dp["E"] @ np.log(_rho))
            _feed = self.dairy_feed_factor(_rho)
            # CAPRI's FMIL bulk per member state (feedShareEqu_, Sprint 9h): each product's EU feed use from the
            # member states' FMIL bulks at the products' prices, where the bulk table has the product
            _fn = getattr(self, "_eu_feed_now", None) or {}
            _f0 = (fb or {}).get("feed0", {}) if fb else {}
            for k, c in self.DAIRY_TRADED.items():
                if c in _fn and float(_f0.get(c, 0.0)) > 0:
                    _feed[_P9.index(k)] = float(_fn[c]) / float(_f0[c])
            for k, c in self.DAIRY_TRADED.items():
                j = Cc.get(c)
                kk = _P9.index(k)
                cons0 = float(_dp["cons9"].get(k, 0.0))
                if j is None or cons0 <= 0:
                    continue
                sh = min(0.95, float(_dp["fd9"][kk]) / cons0)
                d0 = float(Bv[ie, j]) * float(CAL[j])
                D[ie, j] = d0 * ((1.0 - sh) * float(_food[kk]) * ir ** float(INC[j]) + sh * float(_feed[kk]))
        # NON-EU DAIRY PRODUCTS (Sprint 9f): in the regions with CAPRI's dairy block, food use with the region's
        # own and cross p_ElasDem among the nine products, feed use with the FMIL CES at a fixed FMIL index (the
        # model has no non-EU herds); weights: the block's 2030 human consumption and feed use
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
                for kk, k in enumerate(_P9):
                    j = Cc.get(self.DAIRY_TRADED[k])
                    hc, fd = float(_prm["hc9"][kk]), float(_prm["fd9"][kk])
                    if j is None or hc + fd <= 0:
                        continue
                    sh = fd / (hc + fd)
                    d0 = float(Bv[i, j]) * float(CAL[j])
                    D[i, j] = d0 * ((1.0 - sh) * float(_food[kk]) * ir ** float(INC[j]) + sh * float(_feed[kk]))
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
                    if reg == "EU27":
                        # EU: CAPRI's biofuel share of EU use applied to the model's EU use (the EU base is the
                        # supply models', not CAPRI's)
                        sh = bp["share"].get(c, 0.0)
                        q0 = bp["q0"].get(c, 0.0)
                        if sh <= 0 or q0 <= 0:
                            continue
                        d0 = float(Bv[i, j]) * float(CAL[j])
                        e = float(eu_eta.get(c, ETA[j]))
                        food = float(PR[i, j]) ** e * ir ** float(INC[j])
                        D[i, j] = D[i, j] + d0 * sh * (q / q0 - food)
                        self._eu_biof_ratio[c] = q / q0
                    else:
                        # non-EU: the region's use is CAPRI's, which holds CAPRI's feedstock quantity
                        q0 = bp["q0_reg"].get((reg, c), 0.0)
                        if q0 <= 0:
                            continue
                        food = float(PR[i, j]) ** float(ETA[j]) * ir ** float(INC[j])
                        D[i, j] = D[i, j] + (q - q0 * food)
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
        demand = pd.DataFrame(D, index=demand.index, columns=demand.columns)
        return demand.clip(lower=0.0).astype(float)

    @staticmethod
    def _income_elasticity(comm: str) -> float:
        """Engel income elasticities by commodity group (CAPRI-style):
        staples low/negative, livestock and processed goods higher."""
        staples = {"SWHE", "DWHE", "BARL", "CORN", "OCER", "POTA", "PULS"}
        livestock = {"BEEF", "PORK", "POUL", "SHGM", "EGGS", "MILK", "BUTR",
                     "CHES", "SKIM"}
        if comm in ("RAPC", "SUNC", "SOYC"):
            return 0.0      # cakes are feed: demand follows herds, not income
        if comm in staples:
            return 0.1
        if comm in livestock:
            return 0.5
        return 0.3

    def compute_trade_flows(
        self,
        supply: pd.DataFrame,
        demand: pd.DataFrame,
        world_prices: pd.Series,
        domestic_prices: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Compute bilateral trade flows using Armington allocation.

        For each importing region r:
          Total imports M_r = max(0, QD_r - QS_r)
          Flow from j to r: TRD_{jr} = M_r × share_{jr}(prices)
        """
        flows_idx = pd.MultiIndex.from_product(
            [self.regions, self.regions], names=["exporter", "importer"]
        )
        flows = pd.DataFrame(0.0, index=flows_idx, columns=self.commodities)

        for comm in self.commodities:
            for importer in self.regions:
                sup = supply.at[importer, comm] if importer in supply.index else 0.0
                dem = demand.at[importer, comm] if importer in demand.index else 0.0
                total_imports = max(0.0, dem - sup)

                if total_imports < 0.001:
                    continue

                # Price of goods from each exporting origin (CIF basis)
                prices_by_origin = pd.Series({
                    exp: world_prices.get(comm, 200.0) * 1.05  # +5% transport
                    for exp in self.regions if exp != importer
                })

                arm_sys = self.armington_systems.get((importer, comm))
                if arm_sys is None:
                    # Uniform allocation
                    exporters = [r for r in self.regions if r != importer]
                    for exp in exporters:
                        flows.at[(exp, importer), comm] = total_imports / len(exporters)
                else:
                    alloc = arm_sys.import_quantities(total_imports, prices_by_origin)
                    for exp, qty in alloc.items():
                        if (exp, importer) in flows.index:
                            flows.at[(exp, importer), comm] = qty

        return flows


    # ------------------------------------------------------------------
    # Armington price premium for the EU
    # ------------------------------------------------------------------
    #: Without this, every regional price is a fixed wedge on the world price,
    #: so the EU is a price-taker: when EU supply falls, imports fill the gap at
    #: an unchanged price. That is the law of one price, not an Armington
    #: market. Under Farm-to-Fork it held EU prices to +1.6-3% where CAPRI
    #: reports +8% (cereals), +12% (oilseeds) and +15% (vegetables and permanent
    #: crops), and so let supply keep falling: oilseeds and permanent crops
    #: overshot CAPRI's published production changes by ~40%.
    #:
    #: In an Armington market domestic and imported goods are imperfect
    #: substitutes, so imports only expand if the domestic price rises relative
    #: to the import price. The first-order condition gives
    #:     (p_D / p_D0) = ((M/D) / (M0/D0)) ** (1/sigma)
    #: for a net importer (M imports, D domestic supply), and the mirror image
    #: on the export share for a net exporter. sigma is CAPRI's own substitution
    #: elasticity from armington_params.csv. The premium is exactly 1 at the
    #: base, so calibration, price reproduction and the base year are untouched.
    ARMINGTON_PREMIUM_BOUNDS = (param("ARMINGTON_PREMIUM_LO"), param("ARMINGTON_PREMIUM_HI"))

    #: Minimum recorded gross trade, as a share of EU consumption, for the
    #: Armington premium to apply at all.
    MIN_TRADE_SHARE_FOR_PREMIUM = param("MIN_TRADE_SHARE_FOR_PREMIUM")

    def set_eu_base(self, base_supply: pd.Series, base_demand: pd.Series):
        """Record the EU's base supply and demand at the model's own levels."""
        self._eu_base_supply = base_supply.astype(float)
        self._eu_base_demand = base_demand.astype(float)

    def _eu_gross_trade(self) -> dict:
        """Extra-EU gross imports and exports per commodity, from the trade file.

        The trade file puts intra-EU flows on the EU27->EU27 diagonal, so its
        EU rows to and from other regions are genuine extra-EU trade - unlike
        FAO's EU27 totals, which sum member states and include intra-EU flows.
        """
        g = getattr(self, "_eu_gross_cache", None)
        if g is not None:
            return g
        g = {}
        try:
            from pathlib import Path as _P
            f = _P(__file__).resolve().parents[2] / "capri_data" / "shared" / "trade_flows_2017.csv"
            t = pd.read_csv(f)
            imp = t[(t["importer"] == "EU27") & (t["exporter"] != "EU27")]
            exp = t[(t["exporter"] == "EU27") & (t["importer"] != "EU27")]
            for c in self.commodities:
                if c in t.columns:
                    g[c] = (float(imp[c].sum()), float(exp[c].sum()))
        except Exception:
            g = {}
        # Commodities the trade file records no trade for (sugar, durum wheat)
        # get CAPRI's own extra-EU trade from its 2030 reference instead, so
        # their EU price can respond. Without it they carried no premium, and
        # durum - starting from zero imports - inflated the cereal import check.
        try:
            from pathlib import Path as _P
            f2 = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "market" / "eu_gross_trade_supplement.csv"
            if f2.exists():
                sup = pd.read_csv(f2, index_col=0)
                for c in sup.index:
                    if c in self.commodities and max(g.get(c, (0.0, 0.0))) <= 0:
                        g[c] = (float(sup.at[c, "imports_kt"]), float(sup.at[c, "exports_kt"]))
        except Exception:
            pass
        self._eu_gross_cache = g
        return g

    def _net_ratio_premium(self, P0, Q0, P, Q, sig, r2) -> float:
        """Fallback when gross flows cannot be closed consistently: the net-trade
        ratio formula, never a silent 1.0."""
        lo, hi = self.ARMINGTON_PREMIUM_BOUNDS
        M0, M = Q0 - P0, Q - P
        if M0 > 0.01 * Q0 and M > 0:
            ratio, e = (M / P) / (M0 / P0), sig
        elif M0 < -0.01 * Q0 and M < 0:
            ratio, e = ((-M0) / Q0) / ((-M) / Q), r2
        else:
            ratio, e = (Q / P) / (Q0 / P0), sig
        return float(min(max(ratio ** (1.0 / e), lo), hi))

    def eu_armington_premium(self, supply: pd.Series, demand: pd.Series) -> pd.Series:
        """Per-commodity EU price relative to the wedge price, from gross trade.

        Two-sided Armington clearing. EU production P must equal domestic sales
        D plus exports X. Domestic sales compete with imports M at the
        first-level elasticity sigma: D/M = (D0/M0) * x**(-sigma), with D + M = Q.
        Exports compete in foreign import markets at the second-level
        elasticity rho2: X = X0 * x**(-rho2). Here x is the EU price relative to
        its base (the premium). One monotone equation per commodity,
            Q * r(x)/(1+r(x)) + X0 * x**(-rho2) = P,
        solved by bisection. It holds exactly at x = 1 in the base.

        An earlier version used NET trade in a ratio formula. With small net
        positions (EU maize net imports ~6 Mt of 73) the ratio moved several-fold
        for modest supply changes, making prices far too sensitive - cereal
        prices rose +17-20% under Farm-to-Fork against CAPRI's +8% - and the
        outer loop stopped converging. Gross base flows come from the trade
        file; the smaller gross flow is taken as recorded and the larger one
        closes the EU's base balance, so real two-way trade is kept.
        """
        prem = pd.Series(1.0, index=self.commodities)
        P0s = getattr(self, "_eu_base_supply", None)
        Q0s = getattr(self, "_eu_base_demand", None)
        if P0s is None or Q0s is None:
            return prem
        lo, hi = self.ARMINGTON_PREMIUM_BOUNDS
        gross = self._eu_gross_trade()
        _dairy = bool(self._dairy_params())
        for c in self.commodities:
            if _dairy and c == "MILK":                 # priced by the dairy block (solve)
                continue
            P0, Q0 = float(P0s.get(c, 0.0)), float(Q0s.get(c, 0.0))
            P, Q = float(supply.get(c, 0.0)), float(demand.get(c, 0.0))
            if min(P0, Q0, P, Q) <= 1e-6:
                continue
            sig = float(self.armington.at[c, "sigma"]) if c in self.armington.index else 3.0
            r2 = sig
            if c in self.armington.index and "rho2" in self.armington.columns:
                v = self.armington.at[c, "rho2"]
                if pd.notna(v) and float(v) > 0:
                    r2 = float(v)
            if sig <= 0:
                continue
            # Gross trade enters as a SCALE-FREE intensity: the smaller gross
            # flow relative to the larger. Levels cannot be used - the trade file
            # records rapeseed imports of 28.6 Mt against a market EU consumption
            # of 10.1 Mt (it counts products in seed equivalent), which made
            # domestic sales negative and silently dropped the premium. The flows
            # are rebuilt around the market's own EU net position, so the base
            # closes exactly.
            Mtf, Xtf = gross.get(c, (0.0, 0.0))
            big = max(Mtf, Xtf)
            # An Armington premium only describes a good the EU actually trades.
            # Sugar beet is processed near where it is grown and barely traded;
            # with no import share to work with, any supply change drove its
            # premium to a bound and the anticipated supply response threw it to
            # the other one, every outer iteration (1.500 -> 0.744 -> 1.500),
            # which kept the whole loop from converging. Where recorded gross
            # trade is under 5% of EU consumption, the EU price follows the world
            # price through the wedge, with no premium.
            if big < self.MIN_TRADE_SHARE_FOR_PREMIUM * Q0:
                continue
            g = min(Mtf, Xtf) / big if big > 0 else 0.0
            g = min(max(g, 0.0), 0.9)
            N0 = Q0 - P0                               # net imports at base
            if N0 >= 0:
                M0 = max(N0 / (1.0 - g), 0.01 * Q0)
                X0 = M0 - N0
            else:
                X0 = max(-N0 / (1.0 - g), 0.01 * P0)
                M0 = X0 + N0
            M0 = min(M0, 0.9 * Q0)
            X0 = P0 - Q0 + M0
            D0 = Q0 - M0
            if D0 <= 0 or M0 <= 0 or X0 < 0:
                prem[c] = self._net_ratio_premium(P0, Q0, P, Q, sig, r2)
                continue
            # The traded-goods rule must hold for the flows the premium actually
            # USES, not only for the recorded ones. Durum, given CAPRI-derived
            # trade, passed the recorded-trade test, but the market sees its EU
            # balance as almost exactly even, so the rebuilt flows fell to the
            # 91 kt floor each way; with that import share the premium turned
            # so steep that Farm-to-Fork stopped converging (15 iterations).
            if M0 + X0 < self.MIN_TRADE_SHARE_FOR_PREMIUM * Q0:
                continue
            k = D0 / M0

            def f(x):
                r = k * x ** (-sig)
                return Q * r / (1.0 + r) + X0 * x ** (-r2) - P

            if f(lo) <= 0:
                prem[c] = lo
                continue
            if f(hi) >= 0:
                prem[c] = hi
                continue
            a, b = lo, hi
            for _ in range(60):
                m = 0.5 * (a + b)
                if f(m) > 0:
                    a = m
                else:
                    b = m
            prem[c] = 0.5 * (a + b)
        return prem

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
        try:
            import json as _json
            from pathlib import Path as _P
            from capri_mod.data.loaders import resolve_data_file
            f = resolve_data_file(_P(__file__).parent.parent.parent / "capri_data",
                                  "fao_market_baseline.json")
            if f.exists():
                for key, rec in _json.load(open(f)).items():
                    r, c = key.split("|")
                    if r == "EU27":
                        rows[c] = rec
        except Exception:
            rows = {}
        # CAPRI's own EU balance (FAO_agg, member states summed: production MAPR, domestic use DOMM) where it
        # has the commodity; the FAO extract's EU sugar was 2.6 Mt produced and used (CAPRI 16.7 and 18.9)
        for key, rec in (getattr(self, "_capri_world_balance", None) or {}).items():
            r, c = key.split("|")
            if r == "EU27" and float(rec.get("production", 0) or 0) > 0 and float(rec.get("consumption", 0) or 0) > 0:
                rows[c] = {"production": float(rec["production"]), "consumption": float(rec["consumption"])}
        self._fao_eu_cache = rows
        return rows

    def _align_eu_base_balance(self, eu_supply: pd.Series, by_country: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Set the EU's base production and consumption consistently."""
        fao = self._fao_eu_rows()
        ne = getattr(self, "_base_net_exports_eu", {}) or {}
        base_supply = pd.DataFrame(0.0, index=["EU27"], columns=self.commodities)
        for comm in self.commodities:
            p_model = float(eu_supply.get(comm, 0.0) or 0.0)
            if p_model <= 0:
                base_supply.at["EU27", comm] = float(self.base_production.at["EU27", comm])
                continue
            rec = fao.get(comm, {})
            fp, fc = float(rec.get("production", 0) or 0), float(rec.get("consumption", 0) or 0)
            if fp > 0 and fc > 0:
                cons = p_model * fc / fp                 # FAO's self-sufficiency
            else:
                cons = max(1.0, p_model - float(ne.get(comm, 0.0)))
            self.base_production.at["EU27", comm] = p_model
            self.base_consumption.at["EU27", comm] = cons
            # the ALIGNED EU use, before calibration rescales base_consumption
            # (_exempt_eu_from_world_calibration divides it by the calibration
            # factor); the EU base crush is anchored on this value
            if not hasattr(self, "_eu_aligned_use") or self._eu_aligned_use is None:
                self._eu_aligned_use = {}
            self._eu_aligned_use[comm] = cons
            base_supply.at["EU27", comm] = p_model
        # DAIRY: EU base production of the traded dairy products = CAPRI's 2030 reference output of the
        # dairy block, consumption = that + CAPRI's extra-EU net imports; raw milk is all used in the EU
        dp = self._dairy_params()
        if dp and float(eu_supply.get("MILK", 0.0) or 0.0) > 0:
            self._dairy_S0 = float(eu_supply.get("MILK"))
            # raw milk delivered per member state at base (the dairy blocks' milk ratios)
            self._dairy_S0_ms = self._milk_by_ms(by_country) if by_country is not None else None
            self._dairy_u = None
            self._dairy_u_all = {}
            self.base_production.at["EU27", "MILK"] = self._dairy_S0
            self.base_consumption.at["EU27", "MILK"] = self._dairy_S0
            self._eu_aligned_use["MILK"] = self._dairy_S0
            base_supply.at["EU27", "MILK"] = self._dairy_S0
            self._eu_milk_supply_now = self._dairy_S0
            for k, c in self.DAIRY_TRADED.items():
                i = dp["ix"][k]
                q = float(dp["Q0"][i] - dp["proc0"][i])
                cons = q + float(dp["net_imports0"].get(k, 0.0))
                self.base_production.at["EU27", c] = q
                self.base_consumption.at["EU27", c] = cons
                self._eu_aligned_use[c] = cons
                base_supply.at["EU27", c] = q
        return base_supply

    def _exempt_eu_from_world_calibration(self, base_supply, prices, trade_scenario):
        """Close the world balance over the non-EU regions.

        demand_response multiplies every region by one factor per commodity. The
        EU's consumption is now set deliberately, so the factor is computed from
        the other regions alone and the EU's base consumption is pre-divided by
        it, leaving EU demand exactly where it was set.
        """
        dom = self.domestic_prices(prices, trade_scenario)
        supply = self.supply_response(prices, base_supply)
        self._demand_cal = pd.Series(1.0, index=self.commodities)
        demand = self.demand_response(dom, prices)
        others = [r for r in demand.index if r != "EU27"]
        cal = pd.Series(1.0, index=self.commodities)
        for comm in self.commodities:
            s_all = float(supply[comm].sum()) if comm in supply.columns else 0.0
            d_eu = float(demand.at["EU27", comm]) if "EU27" in demand.index else 0.0
            d_oth = float(demand.loc[others, comm].sum())
            if d_oth > 1.0 and s_all - d_eu > 1.0:
                cal[comm] = (s_all - d_eu) / d_oth
        cal = cal.clip(lower=0.2, upper=5.0)
        if "EU27" in self.base_consumption.index:
            for comm in self.commodities:
                if cal[comm] > 0:
                    self.base_consumption.at["EU27", comm] /= float(cal[comm])
        self._demand_cal = cal

    def _calibrate_demand_to_supply(
        self,
        exogenous_supply: Optional[pd.DataFrame],
        prices: pd.Series,
        trade_scenario: Optional[Dict],
    ) -> None:
        """
        Calibrate the demand base so the base period is a market equilibrium.

        At base prices, compute world supply (including the supply-module
        override for EU27) and world demand. For each commodity, rescale the
        per-region base consumption by supply/demand so that total demand
        equals total supply at the base price. Cross-price and income terms
        in demand_response then operate as deviations around this calibrated
        base, so the solved base-period prices reproduce the reference levels.

        The scaling is stored (self._demand_cal) and applied inside
        demand_response, leaving the raw base_consumption untouched.
        """
        dom_prices = self.domestic_prices(prices, trade_scenario)
        supply = self.supply_response(prices, exogenous_supply)
        # Demand at base without any calibration factor (reset first)
        self._demand_cal = pd.Series(1.0, index=self.commodities)
        demand = self.demand_response(dom_prices, prices)

        total_supply = supply.sum(axis=0)
        total_demand = demand.sum(axis=0)

        cal = pd.Series(1.0, index=self.commodities)
        for comm in self.commodities:
            d = float(total_demand.get(comm, 0.0))
            s = float(total_supply.get(comm, 0.0))
            if d > 1.0 and s > 1.0:
                # factor that brings demand onto supply at base price
                cal[comm] = s / d
        # Clip to a sane range so a bad base datum can't distort things wildly
        self._demand_cal = cal.clip(lower=0.2, upper=5.0)

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
    #: plus CAPRI's transport costs and tariffs (data: tools/build_bilateral_market.py). "premium": the
    #: earlier approximation - one world price per commodity and an Armington premium for the EU.
    market_structure = "bilateral"
    #: CAPRI's EU tariff-rate quotas in the bilateral market (bilateral_trq_<year>.csv)
    use_trq = True
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
        ff = base / f"bilateral_flows_{year}.csv"
        if not ff.exists():
            year = 2017
            ff = base / "bilateral_flows_2017.csv"
        if not ff.exists():
            self._bilat_raw_cache = (year, {})
            return {}
        fl = pd.read_csv(ff)
        rg = pd.read_csv(base / f"bilateral_regions_{year}.csv")
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
        # EU tariff-rate quotas (tools/build_bilateral_market.py build_trq)
        ft = base / f"bilateral_trq_{year}.csv"
        if ft.exists() and getattr(self, "use_trq", True) and "EU27" in ix:
            tq = pd.read_csv(ft)
            ie = ix["EU27"]
            for c, g in tq.groupby("commodity"):
                sc = out.get(c)
                if sc is None:
                    continue
                Q, gap, sh = np.zeros(n), np.zeros(n), np.zeros(n)
                for t in g.itertuples(index=False):
                    j = ix.get(t.exporter)
                    if j is None or sc.X0[ie, j] <= 0:
                        continue
                    Q[j], gap[j] = t.quota_kt, t.gap_eur_t
                    sh[j] = min(1.0, float(t.imports_kt) / float(sc.X0[ie, j]))
                if (Q > 0).any():
                    sc.trq_row, sc.trq_Q, sc.trq_gap, sc.trq_share = ie, Q, gap, sh
                    sc.trq_offset = np.zeros(n)
        self._bilat_raw_cache = (year, out)
        return out

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
                if r != "EU27":
                    self.base_production.at[r, c] = float(prod[i])
        # non-EU crushing at CAPRI's cake production of the market year
        over = {}
        for (r, sd), prm in (self._crush_params() or {}).items():
            if r == "EU27":
                continue
            o, ck = self.CRUSH_CHAINS[sd]
            if ck in raw and prm["yc"] > 0:
                q = float(self.base_production.at[r, ck]) / prm["yc"]
                if q > 0:
                    over[(r, sd)] = q
        self._crush_q0_override = over
        self._crush_cache = None
        self._demand_cal = pd.Series(1.0, index=self.commodities)
        base_supply = self._align_eu_base_balance(exogenous_supply.sum(axis=0), exogenous_supply) \
            if exogenous_supply is not None else None
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
                    self._eu_aligned_use[c] = float(sc.D0[R.index("EU27")])
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
        others = [r for r in R if r != "EU27"]
        cal = pd.Series(1.0, index=self.commodities)
        for c in pooled:
            s_all, d_eu, d_oth = float(S[c].sum()), float(D.at["EU27", c]), float(D.loc[others, c].sum())
            if d_oth > 1.0 and s_all - d_eu > 1.0:
                cal[c] = min(5.0, max(0.2, (s_all - d_eu) / d_oth))
            if cal[c] != 1.0:
                self.base_consumption.at["EU27", c] /= float(cal[c])
        self._demand_cal = cal
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
        ie = list(self.regions).index("EU27") if "EU27" in self.regions else None
        for c, sc in sysd.items():
            rc = r[c].values
            p = sc.import_prices(rc, float(tadd.get(c, 0.0) or 0.0), ie)
            _, _, PA, _ = sc.prices(rc, p)
            PAr[c] = PA / sc.PA0
            pcache[c] = p
        dp = dom0.reindex(index=r.index, columns=r.columns) * PAr
        world = self.world_prices_base * self._bilateral_world_index(r)
        self._bilat_ratio_now = r
        S = self.supply_response(world, exogenous_supply, region_ratio=r, crush_dom=dp)
        D = self.demand_response(dp, world)
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
        for _ in range(40):
            nrm = float(np.max(np.abs(g)))
            if nrm < 1e-12:
                break
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
            z = z + t * dz
            g = G(z)
        out = rk.copy()
        out[act] = np.exp(z)
        return out

    def _solve_bilateral(self, exogenous_supply, trade_scenario=None, tol=1e-7, max_outer=60, verbose=False):
        """CAPRI's market: successive linearisation - the full model response (supply module output anticipated,
        crushing, dairy blocks, feed and biofuel demand) is re-evaluated each step, and each commodity's trade
        system solved exactly with supply and use log-linear around that point."""
        # BASELINE RUN (no EU base recorded yet): the market is calibrated at THIS supply, prices stay at the
        # reference - CAPRI's reference run is a calibrated equilibrium at its reference prices. Each outer
        # iteration of the baseline recalibrates, so the calibration a scenario inherits is the one at the
        # converged baseline supply. Scenario runs keep it frozen.
        if getattr(self, "_eu_base_supply", None) is None or getattr(self, "_demand_cal_frozen", None) is None:
            self._bilateral_calibrate(exogenous_supply)
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
        R = list(self.regions)
        ie = R.index("EU27") if "EU27" in R else None
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
                trq_moved = max(trq_moved, float(np.max(np.abs(sc.trq_offset - old_off) / np.maximum(sc.Pd0[sc.trq_row], 1.0))))
            if err < tol and trq_moved < tol:
                converged = True
                break
            if err > prev * 0.999:
                damp = max(0.25, damp * 0.5)
            elif damp < 1.0 and err < prev * 0.95:
                # the step came back under control: lengthen it again (a damping halved once stayed halved for the
                # rest of the solve, and the dairy products then crept to the tolerance in 40+ steps)
                damp = min(1.0, damp * 1.5)
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
            r = r * (new / r).clip(lower=0.2, upper=5.0) ** damp
        self._bilat_last_r = r.copy()
        self._bilat_converged = converged
        self._bilat_err = err
        return r, S, D, PAr, pc, converged, it + 1

    def _solve_bilateral_equilibrium(self, exogenous_supply, trade_scenario, verbose=False) -> MarketEquilibrium:
        r, S, D, PAr, pc, converged, iters = self._solve_bilateral(exogenous_supply, trade_scenario, verbose=verbose)
        sysd = self._bilat
        # RAW MILK with the dairy block: the EU milk price is the block's (fat and protein values of the products
        # less margins); raw milk is not traded, so it replaces the pooled market's ratio for the EU
        _dl = getattr(self, "_dairy_last", None)
        if self._dairy_params() and _dl is not None and "MILK" in r.columns and "EU27" in r.index:
            r = r.copy()
            r.at["EU27", "MILK"] = float(_dl["price_ratio"]["MILK"])
        widx = self._bilateral_world_index(r)
        world = self.world_prices_base * widx
        dom0 = self._dom0()
        reported = dom0.reindex(index=r.index, columns=r.columns) * r
        wedge = dom0.reindex(index=r.index, columns=r.columns) * widx
        # the EU price farmers see: premium over the world index (model.py: signal = world ratio x premium)
        self.eu_premium = (r.loc["EU27"] / widx).reindex(self.commodities).fillna(1.0)
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
        if self._biofuel_params() and "EU27" in reported.index:
            biof = self.biofuel_feedstock_use({c: float(PAr.at["EU27", c]) for c in self._biofuel_params()["share"]
                                               if c in PAr.columns})
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
                                         "margin": (float(d["ppri"]) * float(r.at["EU27", fuel]) / st["mub"][(ms, fuel)]
                                                    if (ms, fuel) in st["mub"] else None),
                                         "margin0": float(d["pr0"]) or None}
                        for (ms, fuel), d in bm["rows"].items() if d["region"] == "EU27"}
        return MarketEquilibrium(
            dairy=getattr(self, "_dairy_last", None) if self._dairy_params() else None,
            biofuel=biof, world_prices=world, domestic_prices=reported, wedge_prices=wedge,
            production=S, consumption=D, trade_flows=flows, net_exports=S.subtract(D, fill_value=0),
            welfare=welfare, excess_demand=D.sum() - S.sum(), converged=converged, iterations=iters)

    def solve(
        self,
        exogenous_supply: Optional[pd.DataFrame] = None,
        trade_scenario: Optional[Dict] = None,
        policy_scenario: Optional[Dict] = None,
        max_iter: int = 200,
        tolerance: float = 0.010,
        step_size: float = 0.06,
        verbose: bool = False,
    ) -> MarketEquilibrium:
        """
        Solve for market equilibrium prices.

        Uses tatonnement (excess demand proportional price adjustment):
          P_{t+1} = P_t × exp(α × ED_t / QS_t)

        Convergence criterion: max|ED_k / QS_k| < tolerance

        Parameters
        ----------
        exogenous_supply : supply from supply module [region × commodity]
        trade_scenario   : {"tariff_change": {commodity: delta_pct}}
        policy_scenario  : additional policy instruments (export subsidies etc.)
        max_iter         : maximum iterations
        tolerance        : convergence threshold (relative excess demand)
        step_size        : tatonnement step (α)
        verbose          : print iteration progress
        """
        self._trade_scenario_now = trade_scenario
        if getattr(self, "market_structure", "premium") == "bilateral" and self._bilateral_raw():
            return self._solve_bilateral_equilibrium(exogenous_supply, trade_scenario, verbose=verbose)
        self._bilat_ratio_now = None
        prices = self.world_prices_base.copy().astype(float)
        converged = False
        iteration = 0

        # --- Market calibration (CAPRI-style cal_market step) ---
        # Calibrate the demand base so the BASE period is an equilibrium -- but do
        # this only ONCE, against base supply, then freeze it. The previous code
        # recalibrated demand to match whatever supply was passed on every solve,
        # so a scenario supply cut was instantly matched by an equal demand cut
        # and no price ever moved (a 30% beef supply cut produced 0% price change).
        # Freezing the calibration at base means scenario supply changes create
        # genuine excess demand and the tatonnement moves prices, as a market
        # model must.
        if getattr(self, "_demand_cal_frozen", None) is None:
            base_supply = pd.DataFrame(0.0, index=["EU27"], columns=self.commodities)
            for comm in self.commodities:
                if comm in getattr(self, "base_production", pd.DataFrame()).columns:
                    base_supply.at["EU27", comm] = self.base_production.at["EU27", comm]
            # Use the model's OWN EU output where it is known, and give the EU a
            # base balance consistent with it (see _align_eu_base_balance).
            # The supply module passes one row per member state; the EU total is
            # their sum, exactly as supply_response forms it.
            if exogenous_supply is not None and len(exogenous_supply) > 0:
                base_supply = self._align_eu_base_balance(
                    exogenous_supply.sum(axis=0), exogenous_supply)
                base_supply = self._align_eu_crush_products(base_supply)
            self._calibrate_demand_to_supply(base_supply, prices, trade_scenario)
            self._exempt_eu_from_world_calibration(base_supply, prices, trade_scenario)
            self._demand_cal_frozen = self._demand_cal.copy()
        else:
            self._demand_cal = self._demand_cal_frozen.copy()

        # NEWTON-TYPE SOLVE (market_solver = "root"): the same equations - relative
        # excess demand (demand - supply) / supply = 0 for every commodity - solved
        # with SciPy's root (Powell hybrid) on log price ratios z = log(p / p_base),
        # to 1e-8 instead of tatonnement's 1%. CAPRI solves its market model as a
        # system of equations (CONOPT). Safeguard: if root fails or a price falls
        # below the floor (half the base price), tatonnement runs as before.
        self.last_market_solver = "tatonnement"
        if getattr(self, "market_solver", "tatonnement") == "root":
            from scipy.optimize import root as _root
            comms = list(prices.index)
            pb = self.world_prices_base.reindex(comms).astype(float).clip(lower=1e-9).values

            def _f(z):
                pr = pd.Series(pb * np.exp(z), index=comms)
                dp = self.domestic_prices(pr, trade_scenario)
                su = self.supply_response(pr, exogenous_supply).sum(axis=0)
                de = self.demand_response(dp, pr).sum(axis=0)
                return ((de - su) / su.clip(lower=1.0)).reindex(comms).fillna(0.0).values

            z0 = np.log(np.maximum(prices.reindex(comms).values, 1e-9) / pb)
            try:
                sol = _root(_f, z0, method="hybr", options={"xtol": 1e-10, "maxfev": 4000})
                pr = pd.Series(pb * np.exp(sol.x), index=comms)
                resid = float(np.max(np.abs(_f(sol.x))))
                self.last_root_info = {"success": bool(sol.success), "nfev": int(sol.nfev), "max_rel_ed": resid}
                if resid < min(tolerance, 1e-6) and bool((pr >= self.world_prices_base.reindex(comms) * 0.5 - 1e-9).all()):
                    prices = pr
                    self.last_market_solver = "root"
            except Exception as _exc:
                self.last_root_info = {"success": False, "error": repr(_exc)}
        for iteration in range(max_iter if self.last_market_solver != "root" else 1):
            dom_prices = self.domestic_prices(prices, trade_scenario)
            supply = self.supply_response(prices, exogenous_supply)
            demand = self.demand_response(dom_prices, prices)

            total_supply = supply.sum(axis=0)
            total_demand = demand.sum(axis=0)
            ed = total_demand - total_supply

            # Relative excess demand
            rel_ed = ed / total_supply.clip(lower=1.0)
            max_rel = rel_ed.abs().max()

            if verbose and iteration % 20 == 0:
                print(f"  Market iter {iteration:3d}: max|rel_ED| = {max_rel:.6f}")

            if max_rel < tolerance:
                converged = True
                break

            # Tatonnement price update: raise prices where demand > supply
            prices = prices * np.exp(step_size * rel_ed.clip(-0.3, 0.3))
            # Price floor: 50% of base price (no collapse to zero)
            price_floor = self.world_prices_base * 0.5
            prices = prices.clip(lower=price_floor)

        if verbose:
            status = "CONVERGED" if converged else "NOT CONVERGED"
            print(f"  Market module: {status} after {iteration+1} iterations")

        # Final equilibrium quantities
        dom_prices = self.domestic_prices(prices, trade_scenario)
        supply_final = self.supply_response(prices, exogenous_supply)
        demand_final = self.demand_response(dom_prices, prices)

        # EU Armington premium, solved together with an ANTICIPATED EU supply
        # response. The supply module produced exogenous_supply at the EU price
        # it was shown (_eu_price_seen, relative to base). If the market set the
        # premium treating that supply as fixed, the supply side would then
        # react in full and the two would chase each other across many outer
        # iterations - each one a full re-solve of 248 regional models. Instead
        # the market lets EU supply respond with CAPRI's own market-level
        # supply elasticities, as CAPRI's market module does, so the supply
        # module only corrects the approximation. At a converged point the EU
        # price equals the price seen and the anticipation vanishes: this
        # changes the path to the equilibrium, not the equilibrium.
        self.eu_premium = pd.Series(1.0, index=self.commodities)
        if "EU27" in dom_prices.index and getattr(self, "_eu_base_supply", None) is not None:
            wedge_eu = dom_prices.loc["EU27"].copy()
            seen = getattr(self, "_eu_price_seen", None)
            seen = (seen.reindex(self.commodities).fillna(1.0).clip(lower=0.2)
                    if seen is not None else pd.Series(1.0, index=self.commodities))
            wratio = pd.Series({c: float(prices.get(c, 200.0))
                                / max(float(self.world_prices_base.get(c, 200.0)), 0.01)
                                for c in self.commodities})
            real = getattr(self, "_real_supply_elas", None) or {}
            eps = self.armington["eps"] if "eps" in self.armington.columns else None
            el = pd.Series({c: (float(real[c]) if c in real else
                                (float(eps.get(c, 0.25)) if eps is not None else 0.25))
                            for c in self.commodities})
            p_exog = supply_final.loc["EU27"].copy()
            prem = pd.Series(1.0, index=self.commodities)
            for _ in range(40):
                rel = wratio * prem
                p_ant = p_exog * (rel / seen).clip(lower=0.2).pow(el)
                target = self.eu_armington_premium(p_ant, demand_final.loc["EU27"])
                new_prem = prem + 0.5 * (target.reindex(prem.index).fillna(1.0) - prem)
                dom_prices.loc["EU27"] = wedge_eu * new_prem.reindex(dom_prices.columns).fillna(1.0)
                demand_final = self.demand_response(dom_prices, prices)
                done = float((new_prem - prem).abs().max()) < 1e-5
                prem = new_prem
                if done:
                    break
            # ADAPTIVE DAMPING OF THE PREMIUM between outer iterations. Where the EU barely
            # imports and exports a tenth of output (eggs: imports 0.07% of use), the premium
            # is steep in supply - a 10% fall in egg output takes it to its bound - and solver
            # noise of 0.2% in regional output made it cycle between 1.23 and 1.42 for 25
            # iterations. Each commodity's step toward the newly cleared premium is halved when
            # its direction flips (floor 0.1) and recovers otherwise. Path only: at the fixed
            # point the cleared premium equals the previous one.
            prev = getattr(self, "_prem_prev", None)
            if prev is not None:
                w = getattr(self, "_prem_w", None)
                if w is None:
                    w = pd.Series(1.0, index=prem.index)
                d = prem - prev.reindex(prem.index).fillna(1.0)
                dprev = getattr(self, "_prem_d", None)
                if dprev is not None:
                    flip = (d * dprev.reindex(d.index).fillna(0.0)) < 0
                    w = w.where(~flip, (w * 0.5).clip(lower=0.1))
                    w = w.where(flip, (w * 1.25).clip(upper=1.0))
                prem = prev.reindex(prem.index).fillna(1.0) + w * d
                self._prem_w, self._prem_d = w, d
            # RAW MILK: the EU milk price is the dairy block's (fat and protein values of the products
            # less processing margins), carried as the premium over the world milk price
            _dl = getattr(self, "_dairy_last", None)
            if _dl is not None and "MILK" in prem.index and float(wratio.get("MILK", 0.0)) > 0:
                prem["MILK"] = float(_dl["price_ratio"]["MILK"]) / float(wratio["MILK"])
            self._prem_prev = prem.copy()
            self.eu_premium = prem
            # dom_prices carries the EU price ONCE: wedge x the (damped) premium. The loop above wrote
            # wedge x its own premium into it, and the reported price then multiplied by the premium
            # again: reported = wedge x premium x premium (Farm-to-Fork butter +32% reported against
            # +18% paid; every premium commodity's reported EU price change was inflated the same way,
            # while the supply side was always shown world x premium, once)
            dom_prices.loc["EU27"] = wedge_eu * prem.reindex(dom_prices.columns).fillna(1.0).values
            self._wedge_eu_last = wedge_eu
        flows_final  = self.compute_trade_flows(
            supply_final, demand_final, prices, dom_prices
        )

        net_exports = supply_final.subtract(demand_final, fill_value=0)
        excess_dem  = demand_final.sum() - supply_final.sum()

        # Welfare decomposition (consumer surplus + producer surplus + budget)
        welfare = self._compute_welfare(
            supply_final, demand_final, prices, dom_prices, trade_scenario
        )

        # REPORTED EU PRICE = the producer price farmers respond to: world x
        # tariff x the Armington premium. Results used to report the EU row
        # without the premium, and every Farm-to-Fork comparison with CAPRI read
        # it (pork +13.9% reported vs +25.5% actually paid; poultry +9.9 vs
        # +19.5%). The wedge prices stay available as wedge_prices.
        reported = dom_prices.copy()                    # EU row: wedge x premium (set above)
        wedge = dom_prices.copy()
        if "EU27" in wedge.index and getattr(self, "_eu_base_supply", None) is not None \
                and getattr(self, "_wedge_eu_last", None) is not None:
            wedge.loc["EU27"] = self._wedge_eu_last
        biof = None
        if self._biofuel_params() and "EU27" in dom_prices.index:
            d0 = getattr(self, "_dom0_cache", None)
            if d0 is None:
                d0 = self.domestic_prices(self.world_prices_base)
            biof = self.biofuel_feedstock_use(
                {c: float(dom_prices.at["EU27", c]) / float(d0.at["EU27", c])
                 for c in self._biofuel_params()["share"] if float(d0.at["EU27", c]) > 0})
        return MarketEquilibrium(
            dairy=getattr(self, "_dairy_last", None) if self._dairy_params() else None,
            biofuel=biof,
            world_prices=prices,
            domestic_prices=reported,
            wedge_prices=wedge,
            production=supply_final,
            consumption=demand_final,
            trade_flows=flows_final,
            net_exports=net_exports,
            welfare=welfare,
            excess_demand=excess_dem,
            converged=converged,
            iterations=iteration + 1,
        )

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
                wp0 = self.world_prices_base.get(comm, 200.0)
                wp1 = world_prices.get(comm, 200.0)
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


def eu_gross_trade(mm, supply: "pd.Series", demand: "pd.Series",
                   premium: "pd.Series") -> "pd.DataFrame":
    """EU gross imports and exports implied by the Armington clearing.

    Rebuilds, per commodity, the base gross flows exactly as
    MarketModule.eu_armington_premium does, then evaluates them at the solved
    premium x: imports M = Q / (1 + r(x)) with r(x) = (D0/M0) x^-sigma, exports
    X = X0 x^-rho2. These are the flows the model solves with, reported rather
    than recomputed by a separate method.
    """
    import pandas as pd
    P0s, Q0s = mm._eu_base_supply, mm._eu_base_demand
    gross = mm._eu_gross_trade()
    rows = []
    for c in mm.commodities:
        P0, Q0 = float(P0s.get(c, 0.0)), float(Q0s.get(c, 0.0))
        P, Q = float(supply.get(c, 0.0)), float(demand.get(c, 0.0))
        if min(P0, Q0, P, Q) <= 1e-6:
            continue
        sig = float(mm.armington.at[c, "sigma"]) if c in mm.armington.index else 3.0
        r2 = sig
        if c in mm.armington.index and "rho2" in mm.armington.columns:
            v = mm.armington.at[c, "rho2"]
            if pd.notna(v) and float(v) > 0:
                r2 = float(v)
        Mtf, Xtf = gross.get(c, (0.0, 0.0))
        big = max(Mtf, Xtf)
        if big < mm.MIN_TRADE_SHARE_FOR_PREMIUM * Q0:
            rows.append((c, max(Q0 - P0, 0.0), max(P0 - Q0, 0.0),
                         max(Q - P, 0.0), max(P - Q, 0.0), "net only"))
            continue
        g = min(max(min(Mtf, Xtf) / big, 0.0), 0.9)
        N0 = Q0 - P0
        if N0 >= 0:
            M0 = max(N0 / (1.0 - g), 0.01 * Q0)
        else:
            X0 = max(-N0 / (1.0 - g), 0.01 * P0); M0 = X0 + N0
        M0 = min(M0, 0.9 * Q0); X0 = P0 - Q0 + M0; D0 = Q0 - M0
        if D0 <= 0 or M0 <= 0 or X0 < 0:
            continue
        if M0 + X0 < mm.MIN_TRADE_SHARE_FOR_PREMIUM * Q0:      # as in the premium
            rows.append((c, max(Q0 - P0, 0.0), max(P0 - Q0, 0.0),
                         max(Q - P, 0.0), max(P - Q, 0.0), "net only"))
            continue
        x = float(premium.get(c, 1.0))
        rx = (D0 / M0) * x ** (-sig)
        rows.append((c, M0, X0, Q / (1.0 + rx), X0 * x ** (-r2), "gross"))
    return pd.DataFrame(rows, columns=["commodity", "imports_base", "exports_base",
                                       "imports", "exports", "basis"]).set_index("commodity")
