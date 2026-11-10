"""
CAPRI's global market model (arm/market_model.gms) for the EU supply that the regional supply models deliver.

Structure (docs/design/ARCHITECTURE_REFACTOR.md): MarketModule is assembled from one mixin per block of CAPRI's
market model, each in its own file of this package:
  calibration.py      base calibration (base quantities and prices, EU rows aligned to the supply models)
  bilateral_solve.py  the bilateral system (Armington nests, transport costs, tariffs, TRQs; bilateral.py) and its
                      solve: Newton per commodity with Anderson acceleration across the commodities' links
  demand.py           human consumption (Generalised Leontief demand) and the demand response of the other uses
  processing.py       processing (normalised quadratic ProcNQ_) and oilseed crushing
  dairy.py            the dairy block (raw milk, fat and protein to the nine dairy products)
  biofuel.py          biofuel feedstock demand and the biofuel markets
  feed.py             feed demand (EU feed bulks per member state, residual feeds, non-EU feed demand)
  supply.py           supply response outside the supply models (non-EU regions)
  welfare.py          CAPRI's welfare report (reports/welfare.gms)
  equilibrium.py      the result object (MarketEquilibrium)
Known differences from CAPRI's market are listed in docs/design/ARCHITECTURE_REFACTOR.md section 5.1 and
docs/KNOWN_ISSUES.md.
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
from capri_mod.data import definitions as _defs


from capri_mod.market.equilibrium import MarketEquilibrium  # noqa: F401  (re-exported)
from capri_mod.market.inputs import MarketInputs
from capri_mod.market.calibration import CalibrationMixin
from capri_mod.market.biofuel import BiofuelMixin
from capri_mod.market.dairy import DairyMixin
from capri_mod.market.feed import FeedMixin
from capri_mod.market.demand import DemandMixin
from capri_mod.market.processing import ProcessingMixin
from capri_mod.market.supply import SupplyMixin
from capri_mod.market.luc import LucMixin
from capri_mod.market.bilateral_solve import BilateralSolveMixin
from capri_mod.market.market_nk import NewtonKrylovMixin
from capri_mod.market.welfare import WelfareMixin


# ---------------------------------------------------------------------------
# MARKET MODULE
# ---------------------------------------------------------------------------

class MarketModule(NewtonKrylovMixin, CalibrationMixin, BiofuelMixin, DairyMixin, FeedMixin, DemandMixin, ProcessingMixin, SupplyMixin, LucMixin, BilateralSolveMixin,
                   WelfareMixin):
    """
    CAPRI's global market model for the given EU supply (arm/market_model.gms).

    The EU as CAPRI's two market regions (EU_WEST, EU_EAST), 25 other trade regions and 58 commodities: bilateral trade with two
    Armington nests, transport costs, tariffs and the EU's tariff-rate quotas (market/bilateral.py),
    Generalised Leontief food demand, processing (ProcNQ_, oilseed crushing), the dairy block (fat and
    protein), biofuel markets and feed bulks per member state. Non-EU supply is CAPRI's market supply
    functions (ProdNQ_, own and cross-price terms); EU supply comes from the regional supply models (fixed within one solve), and so does the supply
    of Norway (NO000000, CAPRI's market region NO000000 with supply models; SUP_NONEU_REGIONS, KNOWN_ISSUES K56).

    Solve: Newton per commodity on the bilateral system, with Anderson acceleration across the
    commodities' links (solve -> _solve_bilateral_equilibrium -> _solve_bilateral).
    """


    #: CAPRI's EU market structure: its two market regions A_EU_WEST and A_EU_EAST (gams/aggregation/defaultA.agg), the
    #: model's EU_WEST (EU-14) and EU_EAST (EU-13), each with its own market and Armington prices and bilateral trade
    #: between them, the member states inside (capri_data/codes/eu_market_blocks.csv; definitions.EU_BLOCKS). The one
    #: EU27 region of before (market.eu_blocks = false) was removed on 3 November 2026 (the market's move onto CAPRI's
    #: regions, stage 2); "EU27" stays a reporting row, the sum of the two (bilateral_solve._with_eu_aggregate).
    EU_BLOCK_REGIONS = _defs.EU_BLOCKS
    def __init__(self, data: dict, inputs: Optional["MarketInputs"] = None):
        self.data       = data
        #: the market's data adapter (inputs.py): every input file is read through it
        self.inputs     = inputs if inputs is not None else MarketInputs()
        self.commodities = MARKET_COMMODITIES
        self.regions = [x for r in ALL_TRADE_REGIONS for x in (self.EU_BLOCK_REGIONS if r == "EU27" else (r,))]
        self.EU = tuple(self.EU_BLOCK_REGIONS)
        self.n_comm     = len(self.commodities)
        self.n_reg      = len(self.regions)
        # market regions outside the EU whose market supply is their supply models' output (CAPRI's RMSSUP outside
        # the EU; KNOWN_ISSUES K56): the run's supply-model countries outside the EU (definitions.sup_noneu, the
        # setting run.supply_countries_outside_eu; Norway, NO000000, market region NO000000, by default), in their CAPRI
        # market region. Like the EU's, their supply is fixed within one market solve, anticipated against the prices
        # their models last saw, and the base calibration takes it at the model's own levels; their models see their
        # own market's prices.
        _sup = _defs.sup_noneu()
        self.SUP_NONEU_REGIONS = tuple(dict.fromkeys(tr for _c, tr in _sup.values()))
        #: supply-model country (NUTS-0 of the supply models) -> its non-EU market region
        self.SUP_NONEU_COUNTRY = {c: tr for c, tr in _sup.values()}
        #: non-EU market region -> CAPRI codes of its supply models' countries (member-state keyed tables), a tuple: one
        #: country for Norway, the UK and Turkey, six for WBA (CAPRI's RMS_TO_RM; until 4 November 2026 one code per
        #: region, the last of WBA's six, SUPPLY_NONEU_DESIGN step 8)
        self.SUP_NONEU_MS = {}
        for ms, (_c, tr) in _sup.items():
            self.SUP_NONEU_MS[tr] = self.SUP_NONEU_MS.get(tr, ()) + (ms,)
        #: the non-EU market regions with supply models in this market (SUP_NONEU_REGIONS)
        self.SUP = tuple(r for r in self.SUP_NONEU_REGIONS if r in self.regions)

        # Base data
        self.world_prices_base = data["world_prices"].reindex(self.commodities)
        _miss = [c for c in self.commodities if not (float(self.world_prices_base.get(c, float("nan"))) > 0)]
        if _miss:
            # no invented price (a fixed 200 EUR/t was used here): every market product needs CAPRI's world price
            raise ValueError(f"no base world price for market products {_miss} (capri_data world prices)")
        self.par.demand_cal   = None  # set by the bilateral calibration at the first solve

        # Compute baseline consumption and production
        self._calibrate_baseline()
        # Pristine base tables, restored at every baseline reset (see
        # CAPRIModel.run): EU rows of commodities WITHOUT farm-model supply
        # (oils, cakes, rice, fats, other food) are not re-aligned per run, so
        # whatever an earlier run left there persisted into later runs.
        self.par.base_production0 = self.par.base_production.copy()
        self.par.base_consumption0 = self.par.base_consumption.copy()

    def _market_year(self) -> int:
        """The market year (data["market_year"]): the year of CAPRI's market data the market calibrates to and of
        the yearly input files (bilateral flows, crushing, biofuels); the base year of the market's inputs where the
        data name none (K52f: 2017 written here before)."""
        d = self.data if isinstance(self.data, dict) else {}
        return int(d.get("market_year") or self._inp().base_year)

    def _inp(self) -> MarketInputs:
        """The data adapter (one for the package's own data where the module was built without __init__)."""
        inp = self.__dict__.get("inputs")
        if inp is None:
            inp = self.inputs = MarketInputs()
        return inp

    # ------------------------------------------------------------------
    # EU market regions (CAPRI's two blocks)
    # ------------------------------------------------------------------
    def _ms_block_map(self) -> Dict[str, str]:
        m = getattr(self, "_ms_block_cache", None)
        if m is None:
            m = self._inp().csv("eu_market_blocks.csv", "codes").set_index("ms")["block"].astype(str).to_dict()
            self._ms_block_cache = m
        return m

    def eu_region_of_ms(self, ms: str) -> Optional[str]:
        """The EU market region of a CAPRI member state (BL000000, DE000000, ...): its block; None for the supply-model
        countries outside the EU (Norway, NO000000: market region NO000000)."""
        if any(ms in v for v in self.SUP_NONEU_MS.values()):
            return None
        return self._ms_block_map().get(ms)

    def sup_region_of_country(self, cc: str) -> Optional[str]:
        """The non-EU market region of a supply-model country (its country code, as REGION_TO_COUNTRY, or one of its
        regional units): NO000000 for Norway, WBA for Serbia (RS, CS000000); None for the EU's countries. A unit's code
        is read through REGION_TO_COUNTRY (until 4 November 2026 its first two letters, which are not the country code
        for the UK, UKC00000 / GB, or Serbia, Montenegro and Kosovo)."""
        cc = str(cc)
        cc = _defs.REGION_TO_COUNTRY.get(cc, cc[:2])
        r = self.SUP_NONEU_COUNTRY.get(cc)
        return r if r in getattr(self, "SUP", ()) else None

    def _split_supply(self, exo: Optional[pd.DataFrame]):
        """The supply models' output by country split into the EU's rows (countries x products) and the non-EU
        market regions' totals ({region: Series}, Norway: NO000000). Norway's supply regions are not part of the EU's
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
        """Supply-model rows (countries, or the EU's market regions themselves) summed per EU market region (regions x
        columns); rows of supply-model countries outside the EU (Norway) are left out. Any other row stops (until
        4 November 2026 a row named after an EU block was read as country "EU" and dropped without a word)."""
        reg = []
        for c in df.index:
            r = str(c) if str(c) in self.EU else self.eu_region_of_country(c)
            if r is None and self.sup_region_of_country(c) is None:
                raise ValueError(f"supply row {c!r}: neither a supply-model country nor an EU market region {self.EU}")
            reg.append(r)
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
            try:
                b = self._inp().csv("eu_ms_balance_2030.csv", keep_default_na=False)
                b = b[b["commodity"].astype(str) != ""]
                b["region"] = [self.eu_region_of_ms(m) for m in b["ms"]]
                t = b.groupby(["region", "commodity"])[["prod_kt", "hcon_kt", "feed_kt", "proc_kt", "biof_kt"]].sum()
                t["use_kt"] = t[["hcon_kt", "feed_kt", "proc_kt", "biof_kt"]].sum(axis=1)
            except Exception as exc:
                raise RuntimeError(f"market: CAPRI's member-state balance could not be read ({exc!r})") from exc
            self._eu_msbal_cache = t
        return t

    def eu_split(self, commodity: str, item: str = "use_kt") -> Dict[str, float]:
        """Each EU market region's part of the EU total of a balance item of a commodity in CAPRI's 2030
        member-state data (equal parts where CAPRI has none of it)."""
        t = self._eu_ms_balance()
        v = {r: (float(t.at[(r, commodity), item]) if (r, commodity) in t.index else 0.0) for r in self.EU}
        tot = sum(v.values())
        if tot <= 0:
            return {r: 1.0 / len(self.EU) for r in self.EU}
        return {r: x / tot for r, x in v.items()}

    # ------------------------------------------------------------------
    # Domestic prices
    # ------------------------------------------------------------------

    def domestic_prices(
        self,
        world_prices: pd.Series,
        trade_scenario: Optional[Dict] = None,
    ) -> pd.DataFrame:
        """
        Each region's price level of each commodity at the given world prices: CAPRI's own market price of the region
        at the base (PMRK of the market year: the bilateral systems' Pd0, raw milk from raw_milk_prices_<year>.csv)
        moved by the commodity's world price index (world price / base world price). The reference price level of the
        response functions (dom0 at base world prices: crushing margins, the dairy blocks) and of the reported prices.

        Since 4 November 2026 (the project lead's decision of 3 November, docs/design/TARV_COMPARISON.md): until then
        world price x (1 + the region's aggregate ad valorem equivalent, policy/tariffs.csv), which put the levels at a
        median 0.84 of CAPRI's own (a factor beyond 2 in 254 of 2,565 cells). A scenario's tariff change acts through
        the import prices of the bilateral market (CAPRI's impPrice_: BilateralCommodity.import_prices'
        tariff_adds), not on this level; trade_scenario is kept for the interface.

        Returns DataFrame [region x commodity].
        """
        ref = self._reference_prices()
        wp = pd.Series({c: float(world_prices.get(c, self.world_prices_base[c]))
                        / max(float(self.world_prices_base[c]), 1e-9) for c in self.commodities})
        return ref.mul(wp, axis=1).astype(float)

    def _reference_prices(self) -> pd.DataFrame:
        """CAPRI's market prices at the base per region and commodity (the market year's PMRK), cached; a commodity or
        region without one stops."""
        ref = getattr(self, "_ref_price_cache", None)
        if ref is not None:
            return ref
        R, C = list(self.regions), list(self.commodities)
        ref = pd.DataFrame(np.nan, index=R, columns=C)
        for c, sc in (self._bilateral_raw() or {}).items():
            if c in ref.columns:
                ref[c] = pd.Series(np.asarray(sc.Pd0, float), index=list(sc.regions)).reindex(R)
        if "MILK" in C:
            mk = self._inp().csv(f"raw_milk_prices_{self._market_year()}.csv").set_index("region")["pmrk"]
            ref["MILK"] = mk.reindex(R).astype(float)
        miss = [(r, c) for r in R for c in C if not (np.isfinite(ref.at[r, c]) and ref.at[r, c] > 0)]
        if miss:
            raise ValueError(f"market: no CAPRI market price for {len(miss)} region-commodities, e.g. {miss[:5]}")
        self._ref_price_cache = ref
        return ref

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
        trade_scenario   : {"tariff_change": {importing region: {commodity: delta_pct}}}
        policy_scenario  : kept for the interface (the instruments act through the supply side)
        max_iter         : Newton rounds of the bilateral solve (default 100)
        verbose          : print iteration progress

        The premium market structure of earlier versions (SciPy root or tatonnement with an EU
        Armington premium) was removed on 20 October 2026 (KNOWN_ISSUES K54-2): no run path used it.
        """
        self._trade_scenario_now = trade_scenario
        if self.market_structure != "bilateral" or not self._bilateral_raw():
            raise ValueError(f"the market needs CAPRI's bilateral data ({self._inp().path('bilateral_flows_*.csv')})")
        return self._solve_bilateral_equilibrium(exogenous_supply, trade_scenario, verbose=verbose,
                                                 max_outer=int(max_iter) if max_iter else int(_settings().get("market.max_iter")))
