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
            "OOIL": 20000,  "SUGB": 1900000,"SUGR": 180000, "POTA": 370000,
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
    ) -> pd.DataFrame:
        """
        Supply quantities by region and commodity (1000 t).
        If exogenous_supply is given (from supply module), use it for EU27.
        Otherwise, apply supply elasticity to price signal.
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
        supply[cols] = supply[cols].mul(factor[cols], axis=1).clip(lower=0.0)
        # CRUSHING: oil and cake supply = crush x yields (CAPRI ProcO_, Leontief)
        cp = self._crush_params()
        if cp:
            crush = self.crush_quantities(self.domestic_prices(world_prices, getattr(self, "_trade_scenario_now", None)))
            done = set()
            for (r, s), q in crush.items():
                o, c = self.CRUSH_CHAINS[s]
                for prod, y in ((o, cp[(r, s)]["yo"]), (c, cp[(r, s)]["yc"])):
                    if prod in supply.columns:
                        if (r, prod) not in done:
                            supply.at[r, prod] = 0.0
                            done.add((r, prod))
                        supply.at[r, prod] += q * y
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
        dp = dp.fillna(fallback)
        price_ratio = dp.div(wp0, axis=1)

        base = self.base_consumption.reindex(
            index=self.regions, columns=self.commodities).fillna(100.0)
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
        fu = getattr(self, "_feed_use", None)
        if fu and ie is not None:
            for c, (idx, sh) in fu.items():
                j = Cc.get(c)
                if j is None:
                    continue
                d0 = float(Bv[ie, j]) * float(CAL[j])
                if d0 <= 0:
                    continue
                rest = float(PR[ie, j]) ** float(ETA[j]) * ir ** float(INC[j])
                D[ie, j] = d0 * ((1.0 - sh) * rest + sh * idx)
        demand = pd.DataFrame(D, index=demand.index, columns=demand.columns)
        return demand.clip(lower=0.0).astype(float)

    def _demand_response_ref(
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
        dp = dp.fillna(fallback)
        price_ratio = dp.div(wp0, axis=1)

        base = self.base_consumption.reindex(
            index=self.regions, columns=self.commodities).fillna(100.0)
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
        fdp = self._feed_demand_params()
        if fdp:
            dom0 = getattr(self, "_dom0_cache", None)
            if dom0 is None:
                dom0 = self.domestic_prices(self.world_prices_base)
                self._dom0_cache = dom0
            for (r, c), prm in fdp.items():
                if r not in demand.index or c not in demand.columns:
                    continue
                sh = prm["feed_share"]
                ft = 1.0
                for j, e in prm["elasticities"].items():
                    if j in dp.columns and float(dom0.at[r, j]) > 0:
                        ft *= (float(dp.at[r, j]) / float(dom0.at[r, j])) ** e
                b = float(base.at[r, c]) * float(cal[c])
                food = float(price_ratio.at[r, c]) ** float(eta[c]) * float(income_ratio) ** float(inc[c])
                demand.at[r, c] = b * ((1.0 - sh) * food + sh * ft)
        # CRUSHING: the seed's crush responds to the crushing margin, not to the
        # seed's own demand elasticity. seed demand = (base - crush0) x f
        # + cal x crush0 + (crush - crush0), f the usual demand factor - at
        # base prices this is base x cal, unchanged.
        cp = self._crush_params()
        if cp:
            crush = self.crush_quantities(dp)
            for (r, s), q in crush.items():
                if s in demand.columns and r in demand.index:
                    q0 = cp[(r, s)]["q0"]; b = float(base.at[r, s])
                    f = float(demand.at[r, s]) / b if b > 0 else 0.0
                    demand.at[r, s] = max(0.0, (b - q0) * f + float(cal[s]) * q0 + (q - q0))
        # EU-ROW demand elasticities where CAPRI's EU values differ from the
        # rest of the world's (oils: EU -1.0 to -1.3, oils substituting for
        # each other; non-EU -0.143). Only commodities listed in the file;
        # every other commodity keeps one elasticity for all regions.
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
        if eu_eta and "EU27" in demand.index:
            for _c, _e in eu_eta.items():
                if _c in demand.columns:
                    demand.at["EU27", _c] = (float(base.at["EU27", _c]) * float(cal[_c])
                                             * float(price_ratio.at["EU27", _c]) ** _e
                                             * float(income_ratio) ** float(inc[_c]))
        # FEED DEMAND FOLLOWS HERDS (EU row, feed cereals). EU use is split into
        # a feed part, s x D0 x F/F0, driven by herd sizes x the feed table, and
        # the rest, (1 - s) x D0 x price and income terms. s is each cereal's
        # feed share of domestic use in CAPRI's 2030 balance; F/F0 is total
        # cereal feed now vs base. At base F = F0: the balance is unchanged.
        fu = getattr(self, "_feed_use", None)
        eu = "EU27" if "EU27" in demand.index else None
        if fu and eu is not None:
            for c, (idx, sh) in fu.items():
                if c not in demand.columns:
                    continue
                d0 = float(base.at[eu, c]) * float(cal[c])
                if d0 <= 0:
                    continue
                rest = float(price_ratio.at[eu, c]) ** float(eta[c]) * float(income_ratio) ** float(inc[c])
                demand.at[eu, c] = d0 * ((1.0 - sh) * rest + sh * idx)
        return demand.clip(lower=0.0).astype(float)

    @staticmethod
    def _income_elasticity(comm: str) -> float:
        """Engel income elasticities by commodity group (CAPRI-style):
        staples low/negative, livestock and processed goods higher."""
        staples = {"SWHE", "DWHE", "BARL", "CORN", "OCER", "POTA", "PULS"}
        livestock = {"BEEF", "PORK", "POUL", "SHGM", "EGGS", "MILK", "BUTR",
                     "CHES", "SKIM", "WMLK", "CREM"}
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
    ARMINGTON_PREMIUM_BOUNDS = (0.67, 1.5)

    #: Minimum recorded gross trade, as a share of EU consumption, for the
    #: Armington premium to apply at all.
    MIN_TRADE_SHARE_FOR_PREMIUM = 0.05

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
        for c in self.commodities:
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
        self._fao_eu_cache = rows
        return rows

    def _align_eu_base_balance(self, eu_supply: pd.Series) -> pd.DataFrame:
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
                    exogenous_supply.sum(axis=0))
                base_supply = self._align_eu_crush_products(base_supply)
            self._calibrate_demand_to_supply(base_supply, prices, trade_scenario)
            self._exempt_eu_from_world_calibration(base_supply, prices, trade_scenario)
            self._demand_cal_frozen = self._demand_cal.copy()
        else:
            self._demand_cal = self._demand_cal_frozen.copy()

        for iteration in range(max_iter):
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
            self.eu_premium = prem
        flows_final  = self.compute_trade_flows(
            supply_final, demand_final, prices, dom_prices
        )

        net_exports = supply_final.subtract(demand_final, fill_value=0)
        excess_dem  = demand_final.sum() - supply_final.sum()

        # Welfare decomposition (consumer surplus + producer surplus + budget)
        welfare = self._compute_welfare(
            supply_final, demand_final, prices, dom_prices, trade_scenario
        )

        return MarketEquilibrium(
            world_prices=prices,
            domestic_prices=dom_prices,
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
