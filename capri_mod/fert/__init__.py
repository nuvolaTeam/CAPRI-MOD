"""Fertilizer distribution module.

Distributes national fertilizer totals to regional/crop application rates
(the CAPRI ``p_FertPerHa`` quantity), so the model can derive fertilizer
application for a base year that lacks a ready-made CAPRI ``nutrient_coefs``
file — the fertilizer half of a base-year update.
"""
from .fert_module import FertilizerModule, FertilizerResult

__all__ = ["FertilizerModule", "FertilizerResult"]
