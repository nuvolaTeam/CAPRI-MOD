"""The tables of capri_data/sources (Parquet since 8 November 2026) for the tests: tools/lib/_sources_io.py's readers,
which give a table as its former CSV read with the same options gave it."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "_sources_io", Path(__file__).resolve().parents[2] / "tools" / "lib" / "_sources_io.py")
_m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m)

read_source = _m.read_source
source_records = _m.source_records
