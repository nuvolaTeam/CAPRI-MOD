"""
CAPRI-mod: Common Agricultural Policy Regionalised Impact Model
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

__version__ = "0.1.0"
__all__ = ["CAPRIModel"]


def __getattr__(name):
    # CAPRIModel imported on first use (PEP 562), so that importing a light module of the package (capri_mod.csvio in
    # the data builders) does not load the whole model: the builders' traced code dependencies are then their own
    # (tools/check/reproduce_builders.py --trace, 29 October 2026)
    if name == "CAPRIModel":
        from capri_mod.model import CAPRIModel
        return CAPRIModel
    raise AttributeError(f"module 'capri_mod' has no attribute {name!r}")
