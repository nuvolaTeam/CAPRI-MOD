"""The regional supply model's blocks (refactor stage 3a): mixins of supply_module.RegionalSupplyModel.

Their methods were moved unchanged from supply_module.py and use its module-level names (numpy as np, the settings,
the data tables' readers, SupplyModule, ...): inject gives each block module those names once supply_module is
loaded (a name a block defines itself is kept).
"""
from capri_mod.supply.blocks.livestock import LivestockBlock  # noqa: F401
from capri_mod.supply.blocks.fertilisation import FertilisationBlock  # noqa: F401
from capri_mod.supply.blocks.abatement import AbatementBlock  # noqa: F401
from capri_mod.supply.blocks.policy import PolicyBlock  # noqa: F401
from capri_mod.supply.blocks.land import LandBlock  # noqa: F401
from capri_mod.supply.blocks.nlp import NLPBlock  # noqa: F401

MODULES = ("livestock", "fertilisation", "abatement", "policy", "land", "nlp",)


def inject(names: dict) -> None:
    """Give every block module the names of supply_module (its globals), keeping the block's own."""
    import importlib
    for b in MODULES:
        mod = importlib.import_module(f"capri_mod.supply.blocks.{b}")
        for k, v in names.items():
            if not (k.startswith("__") and k.endswith("__")) and k not in mod.__dict__:
                mod.__dict__[k] = v
