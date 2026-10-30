"""Mixins whose methods were moved out of one module (refactor stages 3a and 4a, docs/design/ARCHITECTURE_REFACTOR.md).

The methods were moved unchanged and use the module-level names of the module they came from (numpy as np, the
settings, the data readers, ...). inject_names gives each mixin module those names once that module is loaded; a name
a mixin module defines itself is kept.
"""
from __future__ import annotations

import importlib
from typing import Iterable


def inject_names(names: dict, modules: Iterable[str]) -> None:
    """Give every module in `modules` (dotted names) the names in `names` (the source module's globals), keeping the
    module's own and leaving the dunder names out."""
    for m in modules:
        mod = importlib.import_module(m)
        for k, v in names.items():
            if not (k.startswith("__") and k.endswith("__")) and k not in mod.__dict__:
                mod.__dict__[k] = v
