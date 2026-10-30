"""The model's activities and their CAPRI activities, for builders: capri_data/codes/model_activities.csv, a declared
code list with a source per row (HARDCODED_TABLES.md H2, 30 October 2026). Until then about a dozen builders each wrote
the same crosswalk as a Python literal.

  CROP_MAP, ANIMALS     model activity -> the CAPRI activities summed into it (capri_codes: CAPRI's data, CAPREG's
                        aggregates GRAS and SETA included)
  CROP_MAP_CAPMOD, ANIMALS_CAPMOD
                        the same with the activities of CAPRI's supply model that carry PMP terms (capmod_codes: GRAS as
                        GRAE + GRAI, SETA as VSET + FALL; every other activity as capri_codes)
"""
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[2]

with open(ROOT / "capri_data" / "codes" / "model_activities.csv", newline="") as _f:
    _ROWS = list(csv.DictReader(_f))


def _map(kind: str, col: str) -> dict:
    return {r["code"]: tuple(r[col].split(";")) for r in _ROWS if r["kind"] == kind}


CROP_MAP = _map("crop", "capri_codes")
ANIMALS = _map("animal", "capri_codes")
CROP_MAP_CAPMOD = _map("crop", "capmod_codes")
ANIMALS_CAPMOD = _map("animal", "capmod_codes")
