"""Paths and settings of the data pipeline (docs/design/CAPTRD_MOD.md sections 6-7, 9).

The store holds what the pipeline downloads and builds:
    <store>/raw/<provider>/<dataset>/<download_id>.<ext>   the provider's file as received (never edited)
    <store>/manifest.csv                                    one row per download (URL, time, checksum, licence, ...)
    <store>/delta/<stage>/<provider>/<dataset>/             Delta tables (stage "raw": the parsed downloads)
It is large and not part of the zip packages; the manifest lets anyone download the same files again.
Location: the environment variable CAPRI_PIPELINE_STORE, else the setting pipeline.store_dir, else
capri_data/pipeline/store.
"""
from __future__ import annotations

import os
from pathlib import Path

from capri_mod.settings import current as _settings

REPO = Path(__file__).resolve().parents[2]
CATALOGUE_DIR = REPO / "capri_data" / "pipeline" / "catalogue"


def store_dir() -> Path:
    env = os.environ.get("CAPRI_PIPELINE_STORE")
    if env:
        return Path(env)
    s = str(_settings().get("pipeline.store_dir") or "")
    return Path(s) if s else REPO / "capri_data" / "pipeline" / "store"


def setting(key: str):
    """A pipeline setting by its full key ("pipeline.http_timeout")."""
    return _settings().get(key)
