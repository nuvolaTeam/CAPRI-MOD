"""The market's grouping step: CAPRI's market regions (RM) and behavioural regions (RMS) to the model's market regions.

The market's move onto CAPRI's regions (docs/design/MARKET_REGIONS_INVENTORY.md, stage 1): every builder of the
market's data groups CAPRI's regions through this one step, read from data:

  capri_data/codes/capri/RM.csv          CAPRI's 45 market regions (set RM; tools/build/build_code_lists.py)
  capri_data/codes/capri/RMEU_to_RM.csv  CAPRI's two EU market blocks (RMEU_to_RM: EU_WEST A_EU_WEST, EU_EAST A_EU_EAST)
  capri_data/codes/rms_to_rm.csv        each behavioural region's market region (RMS_TO_RM; build_code_lists.py)
  capri_data/codes/model_market_regions.csv
                                         each market region's model region (declared): today 26 market regions are
                                         their own, the two EU blocks are the model's EU27, 17 are its ROW

Stage 2 makes the EU blocks the model's regions and stage 3 every market region its own; each changes only the
declared table. A code that is neither a market nor a behavioural region raises KeyError: until 3 November 2026 the
builders folded every unknown code into ROW (REGION_MAP.get(r, "ROW")), so a code they had not skipped as an
aggregate went to ROW silently.

CAPRI's market data also report EU27yr19, the EU's aggregate. With one EU region a builder that reads the EU at that
level gets EU27 for it; with the two blocks it reads the blocks instead (the aggregate is not a market region).
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODES = ROOT / "capri_data" / "codes"
#: CAPRI's EU aggregate in its market data, the level a one-EU builder reads the EU at
EU_AGGREGATE = "EU27yr19"
#: the model's one EU region
EU = "EU27"


def _rows(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def market_regions() -> tuple[str, ...]:
    """CAPRI's market regions RM, in its set order."""
    return tuple(r["code"] for r in _rows(CODES / "capri" / "RM.csv"))


@lru_cache(maxsize=1)
def eu_blocks() -> dict:
    """CAPRI's EU market regions and their block names: {"A_EU_WEST": "EU_WEST", "A_EU_EAST": "EU_EAST"}."""
    return {r["rm"]: r["rmeu"] for r in _rows(CODES / "capri" / "RMEU_to_RM.csv")}


@lru_cache(maxsize=1)
def rms_to_rm() -> dict:
    """CAPRI's behavioural regions and their market region (RMS_TO_RM)."""
    return {r["rms"]: r["rm"] for r in _rows(ROOT / "capri_data" / "codes" / "rms_to_rm.csv")}


@lru_cache(maxsize=1)
def grouping() -> dict:
    """Each market region's model region (codes/model_market_regions.csv); every RM has one row."""
    g = {r["rm"]: r["model_region"] for r in _rows(CODES / "model_market_regions.csv")}
    missing = [r for r in market_regions() if r not in g]
    if missing or len(g) != len(market_regions()):
        raise ValueError(f"codes/model_market_regions.csv does not list each market region once: missing {missing}")
    return g


def market_region(code: str) -> str:
    """CAPRI's market region of a code: a market region is its own, a behavioural region its RMS_TO_RM's. Both maps are
    read on the first call whatever the code (a builder's declared inputs do not depend on its data's codes)."""
    r2m = rms_to_rm()
    if code in grouping():
        return code
    rm = r2m.get(code)
    if rm is None:
        raise KeyError(f"{code}: neither one of CAPRI's market regions (RM) nor a behavioural region (RMS)")
    return rm


def model_region(code: str, eu_as_blocks: bool = False) -> str:
    """The model's market region of a CAPRI code: its market region's group (codes/model_market_regions.csv); with
    eu_as_blocks the EU's market regions are the model's two blocks (EU_WEST, EU_EAST: CAPRI's RMEU_to_RM). CAPRI's
    EU aggregate EU27yr19 is the one EU region (an error with the blocks)."""
    if code == EU_AGGREGATE:
        if eu_as_blocks:
            raise KeyError(f"{code}: CAPRI's EU aggregate, not a region when the EU is two blocks")
        return EU
    rm = market_region(code)
    if eu_as_blocks and rm in eu_blocks():
        return eu_blocks()[rm]
    return grouping()[rm]
