"""The blocks of EnvironmentalModule (refactor stage 4a): mixins of environmental_module.EnvironmentalModule.

Their methods were moved unchanged from environmental_module.py and use its module-level names: inject gives each block module
those names once environmental_module is loaded (a name a block defines itself is kept).
"""
from capri_mod.environmental.blocks.ghg import GHGBlock  # noqa: F401
from capri_mod.environmental.blocks.nitrogen import NitrogenBlock  # noqa: F401
from capri_mod.environmental.blocks.ammonia import AmmoniaBlock  # noqa: F401
from capri_mod.environmental.blocks.phosphorus import PhosphorusBlock  # noqa: F401
from capri_mod.environmental.blocks.biodiversity import BiodiversityBlock  # noqa: F401

MODULES = ("ghg", "nitrogen", "ammonia", "phosphorus", "biodiversity",)


def inject(names: dict) -> None:
    """Give every block module the names of environmental_module (its globals), keeping the block's own."""
    import importlib
    for b in MODULES:
        mod = importlib.import_module(f"capri_mod.environmental.blocks.{b}")
        for k, v in names.items():
            if not (k.startswith("__") and k.endswith("__")) and k not in mod.__dict__:
                mod.__dict__[k] = v
