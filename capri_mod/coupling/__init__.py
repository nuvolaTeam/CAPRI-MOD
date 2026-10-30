"""The blocks of CAPRIModel (refactor stage 4a): mixins of model.CAPRIModel.

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

MODULES = ("hessian", "feed", "young_animals", "price_step", "manure", "bridge", "reporting",)


def inject(names: dict) -> None:
    """Give every block module the names of model (its globals), keeping the block's own."""
    import importlib
    for b in MODULES:
        mod = importlib.import_module(f"capri_mod.coupling.{b}")
        for k, v in names.items():
            if not (k.startswith("__") and k.endswith("__")) and k not in mod.__dict__:
                mod.__dict__[k] = v
