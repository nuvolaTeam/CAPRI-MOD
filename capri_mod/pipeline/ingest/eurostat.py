"""Eurostat adapter: the dissemination API's SDMX 2.1 data queries in SDMX-CSV.

Endpoint (setting pipeline.eurostat_api, default https://ec.europa.eu/eurostat/api/dissemination):
    {api}/sdmx/2.1/data/{dataset}[/{key}]?format=SDMX-CSV&compressed=true[&startPeriod=Y&endPeriod=Y]
    key: one position per dimension in the dataset's order, '.'-separated, '+' for several codes, empty for all
    (e.g. apro_cpsh1: freq.crops.strucpro.geo -> "A.C1110..AT+BE").
Answer: gzip'd CSV with the columns DATAFLOW, LAST UPDATE, the dimensions (lower case), TIME_PERIOD, OBS_VALUE,
OBS_FLAG, CONF_STATUS. A confidential or missing cell has an empty OBS_VALUE and its flag (e.g. "c"); it is kept as
NaN with the flag, never as 0 (true zeros and missing values apart, CAPTRD_MOD.md section 6).
Large extractions are answered asynchronously: an XML message with a key, then
    {api}/1.0/async/status/{key}  until AVAILABLE, and  {api}/1.0/async/data/{key}
(Eurostat API documentation, "Asynchronous API"; implemented as documented, not yet exercised on a live request).
Structure: {api}/sdmx/2.1/datastructure/ESTAT/{dataset} lists the dimensions in order.
Licence: Commission Decision 2011/833/EU (reuse with acknowledgement), except third-party data flagged as such.
"""
from __future__ import annotations

import gzip
import io
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from capri_mod.pipeline import http
from capri_mod.pipeline.config import setting

PROVIDER = "eurostat"
LICENCE = "Eurostat: Commission Decision 2011/833/EU"
_FIXED = ["DATAFLOW", "LAST UPDATE", "TIME_PERIOD", "OBS_VALUE", "OBS_FLAG", "CONF_STATUS"]


@dataclass
class RawDownload:
    url: str
    query: str
    data: bytes                     # as received (gzip'd CSV)
    ext: str
    meta: Dict[str, str] = field(default_factory=dict)


def _api() -> str:
    return str(setting("pipeline.eurostat_api")).rstrip("/")


def dimensions(dataset: str) -> List[str]:
    """The dataset's dimensions in key order (without TIME_PERIOD), from its data structure definition."""
    r = http.get(f"{_api()}/sdmx/2.1/datastructure/ESTAT/{dataset}")
    if r.status != 200:
        raise http.DownloadError(f"eurostat {dataset}: structure not available (HTTP {r.status})")
    dims = re.findall(rb'<s:Dimension [^>]*id="([^"]+)"', r.content) or re.findall(rb'Dimension id="([^"]+)"', r.content)
    return [d.decode() for d in dims if d != b"TIME_PERIOD"]


def build_key(dims: List[str], filters: Optional[Dict[str, object]]) -> str:
    """The SDMX key for {dimension: code or list of codes}; unknown dimension names stop the query."""
    filters = filters or {}
    unknown = set(filters) - set(dims)
    if unknown:
        raise ValueError(f"eurostat: no dimension {sorted(unknown)} (dimensions: {dims})")
    parts = []
    for d in dims:
        v = filters.get(d)
        parts.append("" if v is None else ("+".join(map(str, v)) if isinstance(v, (list, tuple, set)) else str(v)))
    return ".".join(parts)


def fetch(dataset: str, filters: Optional[Dict[str, object]] = None, start: Optional[int] = None,
          end: Optional[int] = None) -> RawDownload:
    key = build_key(dimensions(dataset), filters) if filters else ""
    url = f"{_api()}/sdmx/2.1/data/{dataset}" + (f"/{key}" if key else "")
    params = {"format": "SDMX-CSV", "compressed": "true"}
    if start is not None:
        params["startPeriod"] = str(start)
    if end is not None:
        params["endPeriod"] = str(end)
    r = http.get(url, params=params)
    data = r.content
    if r.status != 200:
        raise http.DownloadError(f"eurostat {dataset}: HTTP {r.status}: {data[:300]!r}")
    if data[:1] == b"<":
        data = _async(dataset, data)
    query = "&".join(f"{k}={v}" for k, v in params.items()) + (f"&key={key}" if key else "")
    return RawDownload(url=r.url, query=query, data=data, ext="csv.gz" if data[:2] == b"\x1f\x8b" else "csv")


def _async(dataset: str, msg: bytes) -> bytes:
    """Eurostat's asynchronous extraction: the first answer is an XML message with a key (or an error)."""
    text = msg.decode("utf-8", "replace")
    if "Fault" in text or "faultstring" in text:
        raise http.DownloadError(f"eurostat {dataset}: {re.sub(r'<[^>]+>', ' ', text)[:400].strip()}")
    m = re.search(r"<[^>]*key>([^<]+)</", text)
    if not m:
        raise http.DownloadError(f"eurostat {dataset}: unexpected answer: {text[:300]}")
    key = m.group(1).strip()
    poll, waited = float(setting("pipeline.eurostat_async_poll")), 0.0
    limit = float(setting("pipeline.eurostat_async_max_wait"))
    while waited <= limit:
        s = http.get(f"{_api()}/1.0/async/status/{key}").content.decode("utf-8", "replace")
        if "AVAILABLE" in s:
            return http.get(f"{_api()}/1.0/async/data/{key}").content
        if any(w in s for w in ("EXPIRED", "FAILED", "UNKNOWN_REQUEST")):
            raise http.DownloadError(f"eurostat {dataset}: asynchronous extraction {key}: {s[:300]}")
        time.sleep(poll)
        waited += poll
    raise http.DownloadError(f"eurostat {dataset}: asynchronous extraction {key} not ready after {limit:.0f} s")


def parse(raw: RawDownload) -> pd.DataFrame:
    """Long table: the dataset's dimension columns, time, value (NaN where empty), flag, conf_status, last_update."""
    data = gzip.decompress(raw.data) if raw.data[:2] == b"\x1f\x8b" else raw.data
    df = pd.read_csv(io.BytesIO(data), dtype=str, keep_default_na=False)
    missing = [c for c in ("TIME_PERIOD", "OBS_VALUE") if c not in df.columns]
    if missing:
        raise http.DownloadError(f"eurostat: not an SDMX-CSV answer (no {missing})")
    dims = [c for c in df.columns if c not in _FIXED]
    out = df[dims].copy()
    out["time"] = df["TIME_PERIOD"]
    out["value"] = pd.to_numeric(df["OBS_VALUE"].replace("", None), errors="raise")
    out["flag"] = df["OBS_FLAG"] if "OBS_FLAG" in df.columns else ""
    out["conf_status"] = df["CONF_STATUS"] if "CONF_STATUS" in df.columns else ""
    out["last_update"] = df["LAST UPDATE"] if "LAST UPDATE" in df.columns else ""
    return out


def provider_updated(df: pd.DataFrame) -> str:
    v = df["last_update"].dropna().unique().tolist() if "last_update" in df.columns else []
    return ";".join(sorted(set(v)))[:200]
