"""Build a BaselineTrajectory from a CAPRI ``captrd`` trend-results export.

Why this matters
----------------
CAPRI's baseline engine (``captrd``) fits historical trends and reconciles them
against AGLINK/Outlook expert supports, producing a projected data set. Using
*CAPRI's own baseline* as the projection driver is what makes an eventual
scenario-magnitude comparison apples-to-apples: both models then start from the
same view of where the world is heading, so a difference in results is a
difference in economic response rather than in baseline assumptions.

Input format
------------
A ``gdxdump`` of ``p_result`` from ``results/baseline/results_<BAS><SIM>.gdx``::

    'BL000000'.'SWHE'.'YILD'.'2030'.'series'  8515.98,

The five dimensions are ``(region, activity, item, year, datatype)``.

Datatypes, and which one to read
--------------------------------
- ``P_Data`` / ``series`` in *historical* years — observations.
- ``step1``/``step2``/``step3`` — successive fitted-trend steps.
- ``support`` / ``support1`` — the AGLINK expert targets the trend is
  reconciled toward.
- ``BASM`` — a constant base-mean reference; it does **not** vary by projection
  year and is therefore *not* the projection.
- **``series`` in future years** — the final reconciled trend, i.e. CAPRI's
  projected baseline value. This is what the extractor reads. (Verified: for a
  given series ``BASM`` is identical across 2020/2025/2030/2040 while ``series``
  moves, and ``series`` coincides with ``step3`` in projection years.)

Items mapped to trajectory blocks
---------------------------------
``YILD`` -> yields, ``LEVL`` -> herds/areas, ``PRIC`` -> prices. Growth factors
are cumulative ratios ``value(target) / value(base)``, matching the trajectory
schema. Ratios outside a plausible band are dropped rather than passed through,
so a divide-by-near-zero cannot inject a nonsense factor into a projection.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, Optional

import numpy as np

_LINE = re.compile(
    r"\s*'([^']+)'\.'([^']+)'\.'([^']+)'\.'(\d+)'\.'([^']+)'\s+([-\d.eE]+)")

#: CAPRI item -> trajectory block
ITEM_TO_BLOCK = {
    "YILD": "yields",
    "LEVL": "herds",       # activity level: herd size for animals, area for crops
    "PRIC": "world_prices",
}

#: factors outside this band are treated as artefacts, not signal
MIN_FACTOR, MAX_FACTOR = 0.2, 5.0


def _iter_rows(path: Path, years: Iterable[str], datatype: str = "series"):
    years = set(str(y) for y in years)
    with open(path, errors="ignore") as fh:
        for line in fh:
            m = _LINE.match(line)
            if not m:
                continue
            region, act, item, year, dtype, value = m.groups()
            if dtype != datatype or year not in years:
                continue
            try:
                yield region, act, item, year, float(value)
            except ValueError:
                continue


def extract_trajectory(
    captrd_csv: Path,
    base_year: int = 2017,
    target_year: int = 2030,
    name: str = "captrd_baseline",
    source: str = "CAPRI captrd trend results (p_result, series), "
                  "reconciled against AGLINK/EU Outlook supports",
    vintage: str = "unknown",
    region_filter: Optional[Iterable[str]] = None,
) -> Dict:
    """Extract cumulative growth factors and return a trajectory dict.

    Factors are aggregated across regions to a per-activity median, which is
    robust to the outliers a per-cell ratio inevitably produces at small bases.
    Per-region detail is deliberately not carried into the trajectory: the
    trajectory schema drives model-wide blocks, and a median keeps the adopted
    assumption legible and auditable rather than opaque.
    """
    base, target = str(base_year), str(target_year)
    values: Dict[tuple, Dict[str, float]] = defaultdict(dict)

    for region, act, item, year, val in _iter_rows(captrd_csv, (base, target)):
        if item not in ITEM_TO_BLOCK:
            continue
        if region_filter and region[:2] not in set(region_filter):
            continue
        values[(region, act, item)][year] = val

    ratios: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for (region, act, item), by_year in values.items():
        b, t = by_year.get(base), by_year.get(target)
        if not b or not t or b == 0:
            continue
        f = t / b
        if not np.isfinite(f) or not (MIN_FACTOR < f < MAX_FACTOR):
            continue
        ratios[ITEM_TO_BLOCK[item]][act].append(f)

    # Per-region detail. A ratio taken at a tiny base is not information — a
    # cell going 0.01 -> 0.5 is a 50x "growth rate" that would wreck a
    # projection — so a region only gets its own factor where the base value is
    # substantial. Everything else falls back to the per-activity median, which
    # is what the whole trajectory used before regional detail was carried.
    MIN_BASE = 1.0
    regional: Dict[str, Dict[str, Dict[str, Dict[str, float]]]] = defaultdict(
        lambda: defaultdict(dict))
    for (region, act, item), by_year in values.items():
        if item not in ITEM_TO_BLOCK:
            continue
        b, t = by_year.get(base), by_year.get(target)
        if not b or not t or b < MIN_BASE:
            continue
        f = t / b
        if not np.isfinite(f) or not (MIN_FACTOR < f < MAX_FACTOR):
            continue
        model_region = region[:4]
        regional[ITEM_TO_BLOCK[item]][model_region][act] = {
            str(target_year): round(float(f), 4)}

    growth: Dict[str, Dict[str, Dict[str, float]]] = {}
    for block, by_act in ratios.items():
        block_entries: Dict[str, Dict[str, float]] = {}
        all_f: list = []
        for act, fs in by_act.items():
            if len(fs) < 3:          # too thin to be a defensible assumption
                continue
            block_entries[act] = {str(target_year): round(float(np.median(fs)), 4)}
            all_f.extend(fs)
        if all_f:
            block_entries["_default"] = {
                str(target_year): round(float(np.median(all_f)), 4)}
        if block_entries:
            growth[block] = block_entries

    return {
        "name": name,
        "source": source,
        "vintage": vintage,
        "base_year": base_year,
        "target_years": [target_year],
        "growth": growth,
        "regional": {b: dict(v) for b, v in regional.items()},
        "_provenance": {
            "extracted_from": str(captrd_csv),
            "datatype_read": "series (final reconciled trend in projection years; "
                             "BASM is a constant base-mean, not the projection)",
            "aggregation": "per-activity median of per-region cumulative ratios",
            "factor_band": [MIN_FACTOR, MAX_FACTOR],
            "min_cells_per_activity": 3,
            "regional_detail": ("per-region factors carried where the base value "
                                f"is >= {MIN_BASE}; the per-activity median is "
                                "the fallback elsewhere"),
        },
    }


def write_trajectory(traj: Dict, path: Path) -> Path:
    Path(path).write_text(json.dumps(traj, indent=1))
    return Path(path)
