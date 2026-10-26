"""The result of a market solve (MarketModule.solve)."""

from dataclasses import dataclass
from typing import Optional

import pandas as pd


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
