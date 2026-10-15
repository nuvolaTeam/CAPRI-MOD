"""EU biofuel results (reporting only).

With endogenous biofuel markets (CAPRI BIOF_M, the default) the market also carries biofuel supply, demand and
trade (MarketModule.biofuel_state; docs/BIOFUEL_MARKET.md); the result then reports the EU's total biofuel
output, use and price change as well.

Biofuel feedstock demand is part of the market model (MarketModule._biofuel_params,
biofuel_feedstock_use; CAPRI arm/market_model.gms biofFeedCost_, biofFeedCostAgg_, Biof_,
prodBiof_). The post-solve BiofuelModule - fixed blending share, hard-coded conversion
yields and feedstock splits, a demand the market never saw - was retired with crushing stage 4.
This package only turns the market's biofuel block into a run result.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class BiofuelResult:
    bioethanol_kt: float = 0.0                                       # EU first-generation output
    biodiesel_kt: float = 0.0
    feedstock_demand: Dict[str, float] = field(default_factory=dict)  # model commodity -> kt
    feedstock_by_type: Dict[str, float] = field(default_factory=dict)  # "BIOD.RAPO" -> kt (CAPRI codes)
    output_scale: Dict[str, float] = field(default_factory=dict)     # relative to CAPRI's 2030 reference
    endogenous: bool = False                                          # biofuel markets endogenous (BIOF_M)
    eu_production_kt: Dict[str, float] = field(default_factory=dict)  # BIOE/BIOD, all generations
    eu_use_kt: Dict[str, float] = field(default_factory=dict)
    eu_price_ratio: Dict[str, float] = field(default_factory=dict)   # EU market price relative to the reference


def from_market(biof: Optional[dict], scale: Optional[dict] = None) -> Optional[BiofuelResult]:
    if not biof:
        return None
    out = biof.get("output", {})
    return BiofuelResult(
        bioethanol_kt=round(float(out.get("BIOE", 0.0)), 1),
        biodiesel_kt=round(float(out.get("BIOD", 0.0)), 1),
        feedstock_demand={k: round(float(v), 1) for k, v in biof.get("by_commodity", {}).items()},
        feedstock_by_type={f"{a}.{b}": round(float(v), 1) for (a, b), v in biof.get("by_feedstock", {}).items()},
        output_scale=dict(scale or {}),
        endogenous=bool(biof.get("endogenous", False)),
        eu_production_kt={f: round(float(v["production"].get("EU27", 0.0)), 1) for f, v in (biof.get("markets") or {}).items()},
        eu_use_kt={f: round(float(v["use"].get("EU27", 0.0)), 1) for f, v in (biof.get("markets") or {}).items()},
        eu_price_ratio={f: float(v["price_ratio"].get("EU27", 1.0)) for f, v in (biof.get("markets") or {}).items()})
