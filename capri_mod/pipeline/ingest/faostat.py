"""FAOSTAT adapter: the bulk files (the query API needs registration and was not responding; CAPTRD_MOD.md section 5).

Index: https://bulks-faostat.fao.org/production/datasets_E.json lists every dataset (DatasetCode, DateUpdate,
FileLocation of its zip). Each zip holds "<name>_E_All_Data_(Normalized).csv" with the columns
    Area Code, Area Code (M49), Area, Item Code, Item Code (CPC), Item, Element Code, Element, Year Code, Year,
    Unit, Value, Flag, Note
(trade matrix TM: Reporter / Partner Country Code instead of Area Code). Domains COCO uses: QCL, CB, CBH, FBS, FBSH, TM,
RL, RP, RFN, PP (capri_data/pipeline/catalogue/datasets.toml).
The bulk file has no server-side filter: filters given as {column: code or [codes]} on the CSV's own column names are
applied while the file is read in chunks, so the large files (TM: 410 MB zipped, 52 million rows) never sit in
memory whole. Licence: CC BY 4.0 (FAO).
"""
from __future__ import annotations

import io
import json
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, Optional

import pandas as pd

from capri_mod.pipeline import http
from capri_mod.csvio import read_csv

PROVIDER = "faostat"
LICENCE = "FAO: CC BY 4.0"
INDEX = "https://bulks-faostat.fao.org/production/datasets_E.json"
CHUNK = 500_000


@dataclass
class RawDownload:
    url: str
    query: str
    data: bytes
    ext: str
    meta: Dict[str, str] = field(default_factory=dict)
    filters: Dict[str, object] = field(default_factory=dict)
    start: Optional[int] = None
    end: Optional[int] = None


def index() -> Dict[str, dict]:
    r = http.get(INDEX)
    if r.status != 200:
        raise http.DownloadError(f"faostat index: HTTP {r.status}")
    return {d["DatasetCode"]: d for d in json.loads(r.content)["Datasets"]["Dataset"]}


def fetch(dataset: str, filters: Optional[Dict[str, object]] = None, start: Optional[int] = None,
          end: Optional[int] = None) -> RawDownload:
    ix = index()
    if dataset not in ix:
        raise http.DownloadError(f"faostat: no dataset {dataset!r} in the bulk index")
    e = ix[dataset]
    r = http.get(e["FileLocation"], timeout=1800)
    if r.status != 200 or r.content[:2] != b"PK":
        raise http.DownloadError(f"faostat {dataset}: HTTP {r.status}, not a zip")
    q = json.dumps({"filters": filters or {}, "start": start, "end": end}, sort_keys=True)
    return RawDownload(url=e["FileLocation"], query=q, data=r.content, ext="zip",
                       meta={"DateUpdate": e.get("DateUpdate", ""), "rows": str(e.get("FileRows", ""))},
                       filters=dict(filters or {}), start=start, end=end)


def _csv_member(z: zipfile.ZipFile) -> str:
    names = [n for n in z.namelist() if n.endswith(".csv") and "All_Data" in n and "(Normalized)" in n]
    if len(names) != 1:
        raise http.DownloadError(f"faostat: expected one normalized data CSV in the zip, found {names}")
    return names[0]


def parse_chunks(raw: RawDownload) -> Iterator[pd.DataFrame]:
    """The normalized CSV in chunks: the file's own columns (snake_case), time, value (NaN where empty), flag."""
    z = zipfile.ZipFile(io.BytesIO(raw.data))
    with z.open(_csv_member(z)) as fh:
        for ch in read_csv(fh, dtype=str, keep_default_na=False, chunksize=CHUNK, encoding="latin-1"):
            for col, v in (raw.filters or {}).items():
                if col not in ch.columns:
                    raise ValueError(f"faostat: no column {col!r} (columns: {list(ch.columns)})")
                vals = [str(x) for x in (v if isinstance(v, (list, tuple, set)) else [v])]
                ch = ch[ch[col].isin(vals)]
            if "Year" in ch.columns and (raw.start is not None or raw.end is not None):
                y = pd.to_numeric(ch["Year"].str[:4], errors="coerce")
                if raw.start is not None:
                    ch = ch[y >= raw.start]
                    y = y[y >= raw.start]
                if raw.end is not None:
                    ch = ch[y <= raw.end]
            if ch.empty:
                continue
            out = ch.drop(columns=[c for c in ("Value", "Year Code") if c in ch.columns]).copy()
            out.columns = [c.lower().replace(" ", "_").replace("(", "").replace(")", "") for c in out.columns]
            out = out.rename(columns={"year": "time"})
            out["value"] = pd.to_numeric(ch["Value"].replace("", None), errors="raise") if "Value" in ch.columns else float("nan")
            if "flag" not in out.columns:
                out["flag"] = ""
            yield out.reset_index(drop=True)


def parse(raw: RawDownload) -> pd.DataFrame:
    parts = list(parse_chunks(raw))
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def provider_updated(df: pd.DataFrame) -> str:
    return ""
