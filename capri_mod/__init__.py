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
import os as _os
import sys as _sys

#: The BLAS and OpenMP thread limits, one thread per process unless the environment sets more (KNOWN_ISSUES K198).
#: The regional solves fork one worker per core, and NumPy's and SciPy's OpenBLAS and the OpenMP runtime each start
#: one thread per core in every worker: on 4 cores the workers ran 7-10 threads each and the run took about twice as
#: long. The libraries read these variables when they load, so they are set here, before capri_mod imports NumPy;
#: tools/run/'s scripts set them before their own imports.
THREAD_LIMITS = ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")


def _limit_threads():
    late = "numpy" in _sys.modules and "OPENBLAS_NUM_THREADS" not in _os.environ
    for _v in THREAD_LIMITS:
        _os.environ.setdefault(_v, "1")
    if late:
        import warnings
        warnings.warn("NumPy was imported before capri_mod without OPENBLAS_NUM_THREADS: its BLAS keeps one thread per "
                      "core in every regional-solve worker (slower runs). Set OPENBLAS_NUM_THREADS=1, "
                      "OMP_NUM_THREADS=1 and MKL_NUM_THREADS=1 before starting Python, or import capri_mod first.",
                      RuntimeWarning, stacklevel=3)


_limit_threads()

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
