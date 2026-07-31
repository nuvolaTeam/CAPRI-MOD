"""
CAPRI-Python: Common Agricultural Policy Regionalised Impact Model
==================================================================
A Python implementation of the CAPRI modelling system architecture.

Structure mirrors the original GAMS-based CAPRI:
  - supply/     : Regional NLP programming models (NUTS-2)
  - market/     : Global Armington spatial equilibrium model
  - policy/     : CAP instrument handling (TRQs, SPS, greening, etc.)
  - environmental/ : GHG, nitrogen, land use indicators
  - data/       : Commodity sets, region definitions, data loaders
  - scenarios/  : Baseline and counterfactual scenario management
  - utils/      : Calibration, convergence, reporting

Reference: Britz & Witzke (2012), CAPRI Model Documentation.
           https://www.capri-model.org
"""

from capri_python.model import CAPRIModel

__version__ = "0.1.0"
__all__ = ["CAPRIModel"]
