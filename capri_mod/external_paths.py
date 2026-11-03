"""Where CAPRI's material outside git is (docs/EXTERNAL_SOURCES.md): capri_sources/ at the repository root, or the
folder the environment variable CAPRI_SOURCES names; CAPRI's files converted for the parity tests in its reference/
folder, or in CAPRI_REFERENCE (capri_reference/ at the repository root until 4 November 2026). The same rule as
tools/lib/paths.py, for the package and its tests."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = Path(os.environ["CAPRI_SOURCES"]).expanduser().resolve() if os.environ.get("CAPRI_SOURCES") \
    else ROOT / "capri_sources"
REFERENCE = Path(os.environ["CAPRI_REFERENCE"]).expanduser().resolve() if os.environ.get("CAPRI_REFERENCE") \
    else SOURCES / "reference"
