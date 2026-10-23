"""HTTP for the provider adapters: retries with a doubling wait on network errors, 429 and 5xx answers.

Uses requests with the environment's proxy and CA settings (nothing is disabled). Credentials, if a provider ever
needs them, come from environment variables named in that provider's adapter.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Optional

from capri_mod.pipeline.config import setting


class DownloadError(RuntimeError):
    """A download that failed after the retries, or an answer the adapter cannot use."""


@dataclass
class Response:
    url: str
    status: int
    content: bytes
    headers: Dict[str, str]


def get(url: str, params: Optional[dict] = None, headers: Optional[dict] = None,
        timeout: Optional[float] = None, retries: Optional[int] = None) -> Response:
    import requests
    timeout = float(setting("pipeline.http_timeout") if timeout is None else timeout)
    retries = int(setting("pipeline.http_retries") if retries is None else retries)
    wait = float(setting("pipeline.http_retry_wait"))
    last = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, params=params, headers=headers or {}, timeout=timeout)
            if r.status_code == 429 or r.status_code >= 500:
                last = f"HTTP {r.status_code}"
            else:
                return Response(r.url, r.status_code, r.content, dict(r.headers))
        except requests.RequestException as e:
            last = f"{type(e).__name__}: {e}"
        if attempt < retries:
            time.sleep(wait * 2 ** attempt)
    raise DownloadError(f"{url}: failed after {retries + 1} attempts ({last})")
