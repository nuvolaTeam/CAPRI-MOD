"""The dataset catalogue: capri_data/pipeline/catalogue/datasets.toml, one [[dataset]] table per dataset the pipeline
downloads. It is configuration (what to fetch and how it maps to CAPRI), so it is TOML like the settings layer, with
comments and nested filters; not a data input.

Keys: provider (eurostat | faostat | oecd | dgagri), dataset (the provider's current code), filters ({dimension:
code or [codes]}), start, end, status (available | discontinued | replaced_partially | unknown), capri_items,
coco_source, and the descriptive old_code_in_capri, replacement, dimensions, regional_level, notes.
Adding a dataset is adding a table; an unknown provider, an unknown key or a malformed filter stops the run.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from capri_mod.pipeline.config import CATALOGUE_DIR

#: the providers of the design (CAPTRD_MOD.md section 7); an adapter exists so far for eurostat only
PROVIDERS = ("eurostat", "faostat", "oecd", "dgagri")
REQUIRED = ("provider", "dataset", "status")
KEYS = REQUIRED + ("filters", "start", "end", "capri_items", "coco_source", "notes", "old_code_in_capri",
                   "replacement", "dimensions", "regional_level")
STATUSES = ("available", "discontinued", "replaced_partially", "unknown")


@dataclass
class Entry:
    provider: str
    dataset: str
    filters: Dict[str, object]
    start: Optional[int]
    end: Optional[int]
    capri_items: str
    coco_source: str
    status: str
    notes: str


def path() -> Path:
    return CATALOGUE_DIR / "datasets.toml"


def load(p: Optional[Path] = None) -> List[Entry]:
    p = Path(p) if p else path()
    with open(p, "rb") as fh:
        try:
            tabs = tomllib.load(fh).get("dataset", [])
        except tomllib.TOMLDecodeError as e:
            raise ValueError(f"{p}: {e}") from None
    out = []
    for i, r in enumerate(tabs, start=1):
        where = f"{p} [[dataset]] #{i} ({r.get('provider')}/{r.get('dataset')})"
        miss = [k for k in REQUIRED if k not in r]
        if miss:
            raise ValueError(f"{where}: missing {miss}")
        unknown = set(r) - set(KEYS)
        if unknown:
            raise ValueError(f"{where}: unknown keys {sorted(unknown)}")
        if r["provider"] not in PROVIDERS:
            raise ValueError(f"{where}: unknown provider {r['provider']!r} (known: {sorted(PROVIDERS)})")
        if r["status"] not in STATUSES:
            raise ValueError(f"{where}: status {r['status']!r} not in {STATUSES}")
        filt = r.get("filters", {})
        if not isinstance(filt, dict):
            raise ValueError(f"{where}: filters must be a table {{dimension = code or [codes]}}")
        out.append(Entry(r["provider"], r["dataset"], dict(filt), r.get("start"), r.get("end"),
                         r.get("capri_items", ""), r.get("coco_source", ""), r["status"], r.get("notes", "")))
    return out


def find(provider: str, dataset: str) -> Optional[Entry]:
    for e in load():
        if e.provider == provider and e.dataset == dataset:
            return e
    return None
