"""The market's state between its blocks (refactor stage 2b, docs/design/MARKET_STATE_INVENTORY.md).

MarketEvalState holds what one market evaluation (BilateralSolveMixin._bilateral_eval: supply_response ->
demand_response -> the by-product blocks) passes from one block to the next, which the blocks kept before as
attributes of the module (`_dairy_last`, `_biof_state`, ...). This first step only gathers them in one object: they
keep their lifetime (they are not reset per evaluation here, as they were not before), so the results are unchanged.
The resets the inventory found missing (section 3, risks 1, 5, 8, 9) are behaviour changes, made one at a time
afterwards.

CAPRI's counterpart: the market model's variables of one solve (arm/market_model.gms), held by GAMS in the model, not
passed between Python blocks.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, Optional


@dataclass
class MarketEvalState:
    #: the bilateral system's price ratios of the evaluation (read by the dairy block)
    bilat_ratio_now: Any = None
    #: crushing prices of the evaluation (supply and demand of the crushing block); None outside an evaluation
    crush_prices_now: Any = None
    #: the non-EU behavioural regions' feed energy price ratios of the evaluation (CAPRI's FeedBal_, audit M3:
    #: {CAPRI region: FEDE / FEDE at calibration}); None outside an evaluation or with market.noneu_feed_nq off
    fede_now: Any = None
    #: the non-EU market regions whose supply is the supply models' in this solve
    sup_active: Any = None
    #: the dairy block's solution inside the raw milk clearing (audit M5), for supply_response
    dairy_m5_now: Any = None
    #: raw milk delivered against the supply models' (kt), from the member states' milk clearing
    milk_dq_now: Optional[dict] = None          # {EU market region: kt} (M5)
    #: the EU's raw milk supply per member state at the evaluation (dairy block)
    eu_milk_supply_now: Any = None
    #: the EU dairy block's last solution
    dairy_last: Any = None
    #: raw milk of the non-EU regions with supply models, and of the other non-EU regions, at the evaluation
    sup_milk_now: Any = None
    world_milk_now: Any = None
    #: Norway's raw milk supply function in the market (market.sup_milk_in_market): {region: {"k", "L", "dL"}} and
    #: the MILK row's response to the other prices (kt) of the evaluation
    sup_milk_terms: Any = None
    sup_milk_cross: Any = None
    #: the non-EU dairy blocks' last solutions
    dairy_world_last: Any = None
    #: the biofuel markets' state (processing quantities, prices) of the evaluation
    biof_state: Any = None
    #: the young-animal prices that clear the market's young-animal markets ({region: {good: ratio}})
    yani_market_now: Any = None
    #: feed use per EU region and per non-EU region with supply models at the evaluation
    eu_feed_now_reg: Any = None
    sup_feed_now: Any = None
    #: the EU's biofuel feedstock use and food use relative to base, per region (feed by-products)
    eu_biof_ratio: Any = None
    eu_food_ratio: Any = None

    def setdefault(self, name: str, default):
        """The field's value, set to default first when it is None (dict.setdefault for the fields)."""
        v = getattr(self, name)
        if v is None:
            v = default
            setattr(self, name, v)
        return v

    def clear(self):
        """Every field back to None."""
        for f in fields(self):
            setattr(self, f.name, None)


@dataclass
class MarketSolveState:
    """What one market solve carries from its last step to the next solve (warm starts), formerly attributes of the
    module. Kept for the whole run as before; model.py resets the bilateral warm start and local elasticities where
    it did (a new market structure)."""
    #: the bilateral system's last price ratios (warm start of the next solve)
    bilat_last_r: Any = None
    #: local supply and demand elasticities of the bilateral solve, measured at the first scenario solve
    bilat_local_el: Any = None
    #: the dairy blocks' last solutions per region (warm start)
    dairy_u_all: Any = None
    #: "unset", or None when a caller asks the EU dairy block to drop its warm start (dairy.py)
    dairy_u: Any = "unset"


@dataclass
class MarketParameters:
    """What the market's calibration builds once per base (or per calibration) and the blocks read, formerly
    attributes of the module. Moved as they are: model.py still resets and caches them field by field where it did
    (the baseline cache _eu_base_cache), so results are unchanged; caching this object per baseline is the next,
    behaviour-changing step (MARKET_STATE_INVENTORY.md section 3, risks 3 and 4)."""
    #: base production and consumption per market region and product (kt), as aligned to the supply models
    base_production: Any = None
    base_consumption: Any = None
    #: their pristine copies, restored at every baseline run
    base_production0: Any = None
    base_consumption0: Any = None
    #: the EU's base net exports per region, CAPRI's world balance records, the EU's aligned other uses
    base_net_exports_eu: Any = None
    capri_world_balance: Any = None
    eu_aligned_use: Any = None
    #: the dairy block's base raw milk supply: EU total, per member state, per market region
    dairy_S0: Any = None
    dairy_S0_ms: Any = None
    dairy_S0_reg: Any = None
    #: base raw milk delivery of the non-EU regions with supply models (Norway, K56)
    sup_milk0: Any = None
    #: crushing base quantities from the baseline's alignment
    crush_q0_override: Any = None
    #: the demand calibration (working copy) and its frozen copy (None: recalibrate at the next solve)
    demand_cal: Any = None
    demand_cal_frozen: Any = None
    #: the calibrated bilateral trade systems per commodity
    bilat: Any = None
    #: the market supply Hessian (CAPRI's p_hessNQSupp, measured by model.py)
    supply_hessian: Any = None


@dataclass
class MarketSeen:
    """What CAPRIModel sets on the market before a solve: the prices and quantities its supply models saw or delivered
    (formerly attributes of the module). Kept for the whole run as before (cleared where model.py cleared them)."""
    #: EU prices (as ratios to base) the EU's supply models saw, per EU market region (Series or frame)
    eu_price_seen: Any = None
    #: the same for the non-EU regions with supply models ({market region: Series})
    sup_price_seen: Any = None
    #: {CAPRI member state: raw milk price level its supply models saw (1 + signal)}
    milk_seen_ms: Any = None
    #: the young-animal markets cleared inside the market: {market region: {"goods": [...], "net": {good: net balance of
    #: the supply models' latest solution}, "ref": {good: the baseline's net balance}, "seen": {good: price ratio those
    #: models saw}}}
    yani_state: Any = None
    #: feed bulk use of the supply models relative to base, per (member state, bulk); None: 1
    feed_bulk_index: Any = None
    #: the supply models' feed bulks at base, kt per (member state, bulk) (the market's bulk demand, audit M4)
    feed_bulk_base: Any = None
    #: the EU's supply outside a run on a subset of regional units (KNOWN_ISSUES K83): the base output of the EU units
    #: not in the run, per country (the rows of the supply models' table) and market commodity, kt; None in a run on
    #: every unit. The market adds it to the EU's supply, moved by the member states' CAPRI market supply functions
    eu_excluded_base: Any = None
    #: calves' milk feed relative to base, EU (None: 1) and per non-EU region with supply models
    fmil_index: Any = None
    fmil_index_sup: Any = None
    #: the EU's base supply at the model's own levels (set_eu_base); None in a baseline run until it is recorded
    eu_base_supply: Any = None


#: the module attributes refactor stage 2b moved (old name: new place) or removed (step 3, write-only): a read or a
#: write of an old name raises (RuntimeError, so that getattr(obj, name, default) cannot hide it)
MOVED = {
    "base_consumption": "par.base_consumption",
    "_base_consumption0": "par.base_consumption0",
    "_base_net_exports_eu": "par.base_net_exports_eu",
    "base_production": "par.base_production",
    "_base_production0": "par.base_production0",
    "_bilat": "par.bilat",
    "_bilat_last_r": "sv.bilat_last_r",
    "_bilat_local_el": "sv.bilat_local_el",
    "_bilat_ratio_now": "ev.bilat_ratio_now",
    "_biof_state": "ev.biof_state",
    "_capri_world_balance": "par.capri_world_balance",
    "_crush_prices_now": "ev.crush_prices_now",
    "_crush_q0_override": "par.crush_q0_override",
    "_dairy_S0": "par.dairy_S0",
    "_dairy_S0_ms": "par.dairy_S0_ms",
    "_dairy_S0_reg": "par.dairy_S0_reg",
    "_dairy_last": "ev.dairy_last",
    "_dairy_m5_now": "ev.dairy_m5_now",
    "_dairy_u": "sv.dairy_u",
    "_dairy_u_all": "sv.dairy_u_all",
    "_dairy_world_last": "ev.dairy_world_last",
    "_demand_cal": "par.demand_cal",
    "_demand_cal_frozen": "par.demand_cal_frozen",
    "_eu_aligned_use": "par.eu_aligned_use",
    "_eu_base_supply": "seen.eu_base_supply",
    "_eu_biof_ratio": "ev.eu_biof_ratio",
    "_eu_feed_now_reg": "ev.eu_feed_now_reg",
    "_eu_food_ratio": "ev.eu_food_ratio",
    "_eu_milk_supply_now": "ev.eu_milk_supply_now",
    "_eu_price_seen": "seen.eu_price_seen",
    "_feed_bulk_index": "seen.feed_bulk_index",
    "_fmil_index": "seen.fmil_index",
    "_fmil_index_sup": "seen.fmil_index_sup",
    "_milk_dq_now": "ev.milk_dq_now",
    "_milk_seen_ms": "seen.milk_seen_ms",
    "_sup_active": "ev.sup_active",
    "_sup_feed_now": "ev.sup_feed_now",
    "_sup_milk0": "par.sup_milk0",
    "_sup_milk_now": "ev.sup_milk_now",
    "_sup_price_seen": "seen.sup_price_seen",
    "supply_hessian": "par.supply_hessian",
    "_world_milk_now": "ev.world_milk_now",
    "_yani_market_now": "ev.yani_market_now",
    "_yani_state": "seen.yani_state",
    "_prem_prev": "removed (stage 2b step 3: written, never read)",
    "_prem_w": "removed (stage 2b step 3: written, never read)",
    "_prem_d": "removed (stage 2b step 3: written, never read)",
    "_eu_base_demand": "removed (stage 2b step 3: written, never read)",
    "_eu_feed_now": "removed (stage 2b step 3: written, never read)",
    "_milk_dL_now": "removed (stage 2b step 3: written, never read)",
    "_wedge_eu_last": "removed (stage 2b step 3: written, never read)",
    "last_market_solver": "removed (stage 2b step 3: written, never read)",
    "_eu_aggregate_reported": "removed (stage 2b step 3: written, never read)",
    "_rest_share": "removed (stage 2b step 3: written, never read)",
    "_bilat_converged": "removed (stage 2b step 3: written, never read)",
    "_bilat_unconverged": "removed (stage 2b step 3: written, never read)",
}


class MarketStateMixin:
    """`par`, `ev`, `sv` and `seen`: the module's MarketParameters, MarketEvalState, MarketSolveState and MarketSeen,
    created on first use (also on modules built without __init__, as the tests' stubs are)."""

    def __getattr__(self, name):
        # only reached for names the instance and its class do not have
        if name in MOVED:
            raise RuntimeError(f"market attribute {name} is now {MOVED[name]} (refactor stage 2b)")
        raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")

    def __setattr__(self, name, value):
        if name in MOVED:
            raise RuntimeError(f"market attribute {name} is now {MOVED[name]} (refactor stage 2b)")
        object.__setattr__(self, name, value)

    @property
    def seen(self) -> MarketSeen:
        st = self.__dict__.get("_seen")
        if st is None:
            st = self.__dict__["_seen"] = MarketSeen()
        return st

    @property
    def par(self) -> MarketParameters:
        st = self.__dict__.get("_par")
        if st is None:
            st = self.__dict__["_par"] = MarketParameters()
        return st

    @property
    def ev(self) -> MarketEvalState:
        st = self.__dict__.get("_ev")
        if st is None:
            st = self.__dict__["_ev"] = MarketEvalState()
        return st

    @property
    def sv(self) -> MarketSolveState:
        st = self.__dict__.get("_sv")
        if st is None:
            st = self.__dict__["_sv"] = MarketSolveState()
        return st
