"""Locations for the tools: the repository root and any tool by name, wherever it sits under tools/.

    tools/build   builders of the model's data files (capri_data/)
    tools/run     model runs
    tools/check   comparisons and diagnostics
    tools/gams    GAMS export scripts to run in a CAPRI installation
    tools/lib     modules shared by the tools (_model_regions, _capri_costsavings, this one)

ROOT is found by looking upward for pyproject.toml, so a tool keeps working if it moves between these folders.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
TOOLS = ROOT / "tools"
FOLDERS = ("lib", "build", "run", "check", "gams")


def tool_file(name: str) -> Path:
    """The file of a tool given its name (with or without .py)."""
    fn = name if name.endswith((".py", ".gms", ".sh")) else f"{name}.py"
    for d in FOLDERS:
        p = TOOLS / d / fn
        if p.exists():
            return p
    raise FileNotFoundError(f"no tool {fn} under {TOOLS} ({', '.join(FOLDERS)})")


def load_tool(name: str):
    """Import a tool as a module by name (the way several builders reuse each other's functions)."""
    p = tool_file(name)
    spec = importlib.util.spec_from_file_location(p.stem, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def add_tool_folders_to_path() -> None:
    for d in reversed(FOLDERS):
        s = str(TOOLS / d)
        if s not in sys.path:
            sys.path.insert(0, s)
