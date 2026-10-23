"""Download a dataset: the adapter's fetch, the raw file kept as received, the parsed rows appended to the raw-stage
Delta table, one manifest row. The same function serves the command line (python -m capri_mod.pipeline fetch).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from capri_mod.pipeline import manifest, store
from capri_mod.pipeline.config import store_dir


@dataclass
class FetchResult:
    download_id: str
    provider: str
    dataset: str
    rows: int
    raw_path: str
    table_version: int


def fetch(provider: str, dataset: str, filters: Optional[Dict[str, object]] = None, start: Optional[int] = None,
          end: Optional[int] = None) -> FetchResult:
    from capri_mod.pipeline.ingest import ADAPTERS
    if provider not in ADAPTERS:
        raise ValueError(f"no adapter for provider {provider!r} (have {sorted(ADAPTERS)})")
    ad = ADAPTERS[provider]
    did = manifest.new_download_id(provider, dataset)
    raw = ad.fetch(dataset, filters=filters, start=start, end=end)
    p = store.save_raw(provider, dataset, did, raw.ext, raw.data)
    rows, ver, upd = 0, None, ""
    if hasattr(ad, "parse_chunks"):
        # large bulk files (FAOSTAT): parsed and written in chunks, one table version each
        for ch in ad.parse_chunks(raw):
            ch["download_id"] = did
            ver = store.write(ch, "raw", provider, dataset)
            rows += len(ch)
        upd = (getattr(raw, "meta", None) or {}).get("DateUpdate", "")
    else:
        df = ad.parse(raw)
        df["download_id"] = did
        ver = store.write(df, "raw", provider, dataset)
        rows = len(df)
        upd = ad.provider_updated(df)
    manifest.append({"download_id": did, "provider": provider, "dataset": dataset, "url": raw.url,
                     "query": raw.query, "downloaded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                     "provider_updated": upd, "sha256": manifest.sha256(raw.data),
                     "bytes": len(raw.data), "rows": rows, "licence": ad.LICENCE,
                     "raw_path": str(p.relative_to(store_dir())), "status": "ok" if rows else "no rows"})
    return FetchResult(did, provider, dataset, rows, str(p), -1 if ver is None else ver)


def fetch_catalogue(only_provider: Optional[str] = None, only_dataset: Optional[str] = None) -> List[FetchResult]:
    from capri_mod.pipeline import catalogue
    from capri_mod.pipeline.ingest import ADAPTERS
    out = []
    skipped = {}
    for e in catalogue.load():
        if e.provider not in ADAPTERS:
            skipped[e.provider] = skipped.get(e.provider, 0) + int(e.status == "available")
            continue
        if e.status != "available":
            continue
        if (only_provider and e.provider != only_provider) or (only_dataset and e.dataset != only_dataset):
            continue
        out.append(fetch(e.provider, e.dataset, e.filters, e.start, e.end))
    if any(skipped.values()):
        print("not downloaded (no adapter yet): " + ", ".join(f"{k} {v} datasets" for k, v in skipped.items() if v))
    return out
