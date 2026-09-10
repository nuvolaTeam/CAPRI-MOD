"""Baseline trajectory — the projection's external, versioned driver.

Design principle (README §10.2): the trajectory is *not* a forecast CAPRI-mod
makes. It is an adopted external assumption set, versioned and swappable, whose
provenance is recorded like any other data source. A projection is defended not
by claiming the trajectory is right, but by showing which conclusions hold across
a range of plausible trajectories.

Schema
------
A trajectory is a JSON document::

    {
      "name":        "eu_outlook_2024",
      "source":      "European Commission, EU Agricultural Outlook 2024-2035",
      "vintage":     "2024-12",
      "base_year":   2017,
      "target_years": [2020, 2025, 2030],
      "growth": {
         "yields":        {"SWHE": {"2030": 1.12}, "_default": {"2030": 1.08}},
         "demand":        {"BEEF": {"2030": 0.95}, "_default": {"2030": 1.05}},
         "world_prices":  {"_default": {"2030": 1.10}},
         "herds":         {"DCOW": {"2030": 0.92}, "_default": {"2030": 1.00}},
         "land":          {"_default": {"2030": 0.99}}
      }
    }

Growth entries are **cumulative multiplicative factors relative to the base
year** (1.12 = +12% by 2030), not annual rates — this keeps them directly
comparable to how the Outlook publishes its projections and avoids compounding
ambiguity. A ``_default`` entry supplies the factor for any key not named
explicitly; a missing block or missing year means "no change" (factor 1.0),
so a trajectory can be as sparse as the evidence supports.

The NULL trajectory (all factors 1.0) must reproduce the comparative-static
result exactly — that identity is the projection layer's primary correctness
test, and it needs no forecast data at all.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


class TrajectoryError(ValueError):
    """Raised when a trajectory is malformed or internally inconsistent."""


# Blocks a trajectory may drive. Anything else is rejected loudly rather than
# silently ignored, so a typo in a trajectory file cannot pass unnoticed.
KNOWN_BLOCKS = {"yields", "demand", "world_prices", "herds", "land"}


@dataclass
class BaselineTrajectory:
    """An external baseline trajectory: growth factors by block, key and year."""

    name: str
    source: str
    vintage: str
    base_year: int
    target_years: List[int]
    growth: Dict[str, Dict[str, Dict[str, float]]] = field(default_factory=dict)
    #: Optional per-region detail: regional[block][region][key][year] = factor.
    #: Falls back to ``growth`` wherever a region has no entry, so a trajectory
    #: can carry regional detail for the activities where the source supports it
    #: and activity-level medians elsewhere.
    regional: Dict[str, Dict[str, Dict[str, Dict[str, float]]]] = field(
        default_factory=dict)

    # ---------------------------------------------------------------- loading
    @classmethod
    def from_file(cls, path: Path) -> "BaselineTrajectory":
        data = json.loads(Path(path).read_text())
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "BaselineTrajectory":
        missing = [k for k in ("name", "source", "vintage", "base_year",
                               "target_years") if k not in data]
        if missing:
            raise TrajectoryError(
                f"trajectory is missing required provenance fields: {missing}. "
                "A trajectory must always carry its source and vintage — an "
                "unattributed forecast is not usable as a projection driver.")
        growth = data.get("growth", {}) or {}
        unknown = set(growth) - KNOWN_BLOCKS
        if unknown:
            raise TrajectoryError(
                f"unknown trajectory blocks {sorted(unknown)}; "
                f"expected any of {sorted(KNOWN_BLOCKS)}")
        traj = cls(
            name=data["name"], source=data["source"], vintage=data["vintage"],
            base_year=int(data["base_year"]),
            target_years=[int(y) for y in data["target_years"]],
            growth=growth,
            regional=data.get("regional", {}) or {},
        )
        traj.validate()
        return traj

    @classmethod
    def null(cls, base_year: int = 2017,
             target_years: Optional[List[int]] = None) -> "BaselineTrajectory":
        """A no-change trajectory. Projecting with it must reproduce the base.

        This is the identity used to test the projection machinery itself,
        independent of any forecast assumption.
        """
        return cls(
            name="null", source="none (identity trajectory for testing)",
            vintage="n/a", base_year=base_year,
            target_years=target_years or [base_year],
            growth={},
        )

    # ------------------------------------------------------------- validation
    def validate(self) -> None:
        for year in self.target_years:
            if year < self.base_year:
                raise TrajectoryError(
                    f"target year {year} precedes base year {self.base_year}")
        for block, keys in self.growth.items():
            for key, by_year in keys.items():
                for year, factor in by_year.items():
                    f = float(factor)
                    if f <= 0:
                        raise TrajectoryError(
                            f"non-positive growth factor {f} for "
                            f"{block}/{key}/{year}; factors are cumulative "
                            "multipliers relative to the base year")
                    if f > 10 or f < 0.1:
                        raise TrajectoryError(
                            f"implausible growth factor {f} for "
                            f"{block}/{key}/{year} (>10x or <0.1x). If this is "
                            "intended, split the horizon into steps.")

    # ---------------------------------------------------------------- lookup
    def factor(self, block: str, key: str, year: int,
               region: Optional[str] = None) -> float:
        """Cumulative growth factor for a block/key/year; 1.0 if unspecified.

        If ``region`` is given and the trajectory carries per-region detail for
        that block, the region's own factor is used. Regional detail is the
        better quantity where the source supports it — collapsing CAPRI's
        region x activity trends to a per-activity median gives Andalusia and
        Denmark the same wheat-yield growth. The per-activity value remains the
        fallback wherever a region has no defensible estimate of its own.
        """
        if block not in self.growth:
            return 1.0
        entries = self.growth[block]

        # per-region detail, when present, wins over the activity-level value
        if region is not None:
            regional = self.regional.get(block, {}).get(region)
            if regional:
                by_year_r = regional.get(key)
                if by_year_r:
                    val_r = by_year_r.get(str(year), by_year_r.get(int(year)))
                    if val_r is not None:
                        return float(val_r)

        by_year = entries.get(key) or entries.get("_default")
        if not by_year:
            return 1.0
        val = by_year.get(str(year), by_year.get(int(year)))
        return 1.0 if val is None else float(val)

    def is_null(self) -> bool:
        """True if every factor in the trajectory is 1.0 (no drift)."""
        for keys in self.growth.values():
            for by_year in keys.values():
                for factor in by_year.values():
                    if float(factor) != 1.0:
                        return False
        return True

    def provenance(self) -> Dict:
        return {
            "name": self.name, "source": self.source, "vintage": self.vintage,
            "base_year": self.base_year, "target_years": list(self.target_years),
            "blocks_driven": sorted(self.growth.keys()),
            "is_null": self.is_null(),
        }
