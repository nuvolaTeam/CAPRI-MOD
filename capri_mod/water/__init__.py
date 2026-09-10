"""Agricultural water-demand indicator module.

Computes irrigation water demand per region from CAPRI's CROPWAT-derived crop
net irrigation requirements and Eurostat-derived irrigated-area shares, driven by
the crop areas the supply module solves. This is the agricultural water *demand*
side — an indicator layer of the same shape as the environmental and fertilizer
modules. It does NOT model catchment hydrology (whether that demand depletes a
given aquifer), which is a separate domain.
"""
from .water_module import WaterDemandModule, WaterResult

__all__ = ["WaterDemandModule", "WaterResult"]
