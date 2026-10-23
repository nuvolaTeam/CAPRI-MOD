"""The pipeline's store: raw files, Delta tables per stage, CSV export (docs/design/CAPTRD_MOD.md section 6).

Delta tables keep every write as a version (deltalake, Apache-2.0); each row carries the download_id it came from,
so a table holds all downloads of a dataset and `latest()` selects the newest. True zeros and missing values stay
apart: a missing observation has value NaN and the provider's flag (e.g. Eurostat "c", confidential), never 0.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from capri_mod.pipeline.config import store_dir


def raw_path(provider: str, dataset: str, download_id: str, ext: str) -> Path:
    return store_dir() / "raw" / provider / dataset / f"{download_id}.{ext}"


def save_raw(provider: str, dataset: str, download_id: str, ext: str, data: bytes) -> Path:
    p = raw_path(provider, dataset, download_id, ext)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p


def table_path(stage: str, provider: str, dataset: str) -> Path:
    return store_dir() / "delta" / stage / provider / dataset


def write(df: pd.DataFrame, stage: str, provider: str, dataset: str) -> int:
    """Append a frame to the stage's Delta table of the dataset; returns the table version written."""
    import pyarrow as pa
    from deltalake import DeltaTable, write_deltalake
    if "download_id" not in df.columns:
        raise ValueError("store.write: every row needs its download_id")
    p = table_path(stage, provider, dataset)
    p.parent.mkdir(parents=True, exist_ok=True)
    tab = pa.Table.from_pandas(df, preserve_index=False)
    write_deltalake(str(p), tab, mode="append", schema_mode="merge")
    return DeltaTable(str(p)).version()


def read(stage: str, provider: str, dataset: str, version: Optional[int] = None) -> pd.DataFrame:
    from deltalake import DeltaTable
    p = table_path(stage, provider, dataset)
    if not p.exists():
        raise FileNotFoundError(f"no {stage} table for {provider}/{dataset} in {store_dir()}")
    dt = DeltaTable(str(p), version=version) if version is not None else DeltaTable(str(p))
    return dt.to_pandas()


def latest(stage: str, provider: str, dataset: str) -> pd.DataFrame:
    """The rows of the newest download of the dataset."""
    df = read(stage, provider, dataset)
    if df.empty:
        return df
    last = sorted(df["download_id"].unique())[-1]
    return df[df["download_id"] == last].reset_index(drop=True)


def export_csv(stage: str, provider: str, dataset: str, out: Path, all_downloads: bool = False) -> Path:
    df = read(stage, provider, dataset) if all_downloads else latest(stage, provider, dataset)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False, lineterminator="\n")
    return out
