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
    #: the non-EU market regions whose supply is the supply models' in this solve
    sup_active: Any = None
    #: the dairy block's solution inside the raw milk clearing (audit M5), for supply_response
    dairy_m5_now: Any = None
    #: raw milk delivered against the supply models' (kt), from the member states' milk clearing
    milk_dq_now: Optional[float] = None
    #: the EU's raw milk supply per member state at the evaluation (dairy block)
    eu_milk_supply_now: Any = None
    #: the EU dairy block's last solution
    dairy_last: Any = None
    #: raw milk of the non-EU regions with supply models, and of the other non-EU regions, at the evaluation
    sup_milk_now: Any = None
    world_milk_now: Any = None
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


class MarketStateMixin:
    """`par`, `ev` and `sv`: the module's MarketParameters, MarketEvalState and MarketSolveState, created on first use
    (also on modules built without __init__, as the tests' stubs are)."""

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
