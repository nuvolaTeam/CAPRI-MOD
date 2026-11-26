"""The blocks of CAPRIModel (the refactor's split into block mixins): mixins of model.CAPRIModel.

Their methods were moved unchanged from model.py and use its module-level names: inject gives each block module
those names once model is loaded (a name a block defines itself is kept).
"""
from capri_mod.coupling.hessian import HessianBlock  # noqa: F401
from capri_mod.coupling.feed import FeedBlock  # noqa: F401
from capri_mod.coupling.young_animals import YoungAnimalBlock  # noqa: F401
from capri_mod.coupling.price_step import PriceStepBlock  # noqa: F401
from capri_mod.coupling.manure import ManureBlock  # noqa: F401
from capri_mod.coupling.bridge import BridgeBlock  # noqa: F401
from capri_mod.coupling.reporting import ReportingBlock  # noqa: F401
# moved from model.py on 26 November 2026 (the refactor of the large modules)
from capri_mod.coupling.run_scenario import RunScenarioBlock  # noqa: F401
from capri_mod.coupling.result_tables import ResultTablesBlock  # noqa: F401

MODULES = ("hessian", "feed", "young_animals", "price_step", "manure", "bridge", "reporting", "run_scenario",
           "result_tables")


def inject(names: dict) -> None:
    """Give every block module the names of model (its globals), keeping the block's own."""
    import importlib
    for b in MODULES:
        mod = importlib.import_module(f"capri_mod.coupling.{b}")
        for k, v in names.items():
            if not (k.startswith("__") and k.endswith("__")) and k not in mod.__dict__:
                mod.__dict__[k] = v
