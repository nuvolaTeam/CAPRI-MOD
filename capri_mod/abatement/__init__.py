"""GHG abatement module — model-derived marginal abatement cost curves.

Derives CAPRI-mod's *own* marginal abatement cost (MAC) curve by imposing a
carbon price on the supply module and observing how production reallocates and
emissions fall. This is the economic (production-reallocation) abatement the
model can explain from its own validated economics — it is NOT fed abatement
numbers from any external study. The EcAMPA 2 report (JRC, 2016) is used only as
an *independent* comparison for the derived curve, never as an input.
"""
from .abatement_module import AbatementModule, MACCPoint, MACCResult
from .technological import TechnologicalAbatement, TechnicalAbatementResult, MeasureResult

__all__ = ["AbatementModule", "MACCPoint", "MACCResult", "TechnologicalAbatement", "TechnicalAbatementResult", "MeasureResult"]
