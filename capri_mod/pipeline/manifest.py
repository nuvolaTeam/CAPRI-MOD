"""The download manifest: one CSV row per download, enough to repeat it and to check the file.

Columns: download_id, provider, dataset, url, query, downloaded_utc, provider_updated, sha256, bytes, rows, licence,
raw_path (relative to the store), status.
"""
from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from capri_mod.pipeline.config import store_dir

COLUMNS = ["download_id", "provider", "dataset", "url", "query", "downloaded_utc", "provider_updated", "sha256",
           "bytes", "rows", "licence", "raw_path", "status"]


def path() -> Path:
    return store_dir() / "manifest.csv"


def new_download_id(provider: str, dataset: str) -> str:
    return f"{provider}-{dataset}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def append(row: Dict[str, object]) -> None:
    unknown = set(row) - set(COLUMNS)
    if unknown:
        raise ValueError(f"manifest: unknown columns {sorted(unknown)}")
    p = path()
    p.parent.mkdir(parents=True, exist_ok=True)
    new = not p.exists()
    with open(p, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in COLUMNS})


def read() -> List[Dict[str, str]]:
    p = path()
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def verify(entry: Dict[str, str]) -> bool:
    """The raw file of a manifest row still matches its checksum."""
    f = store_dir() / entry["raw_path"]
    return f.exists() and sha256(f.read_bytes()) == entry["sha256"]
