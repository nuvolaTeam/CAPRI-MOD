"""Agricultural water-demand indicator.

Method
------
For each region r and crop c the irrigation (blue) water demand is

    demand(r,c) = CNIR(r,c) [mm]  x  irrigated_area(r,c) [ha]  x  10 [m3 per mm-ha]

where 1 mm of water over 1 ha = 10 m3, and

    irrigated_area(r,c) = irrigation_share(r) x crop_area(r,c)

CNIR is the crop *net irrigation requirement* (the blue water a crop needs beyond
effective rainfall), taken from CAPRI's CROPWAT-derived ``p_cropwatReq`` (item
CNIR, in mm). ``irrigation_share`` is the share of irrigable area in UAA from
CAPRI's ``p_irriShare`` (Eurostat Farm Structure Survey), using the year closest
to the model base year. ``crop_area`` is the supply module's solved activity
level for the crop.

Data provenance and coverage
----------------------------
- CNIR: CROPWAT (FAO) crop water requirements as shipped in CAPRI, 276 source
  regions x 29 crops. Physically sensible (0.1-1040 mm; Mediterranean high,
  northern near zero).
- irrigation share: CAPRI p_irriShare (Eurostat FSS), 1995-2018; the base-year
  value (2017) is used.
- Region codes: the CROPWAT/irrishare data use older NUTS vintages
  (NUTS-2006 for IT/FR/BG/RO, NUTS-2010 for EL). A code map
  (``_nuts_remap.json``) brings them onto the model's NUTS-2016 codes. Coverage
  after mapping is 176/248 regions, and crucially near-complete for the
  irrigation-intensive Mediterranean (ES 17/19, IT 20/21, FR 22/22, PT 7/7,
  EL 13/13) where irrigation demand actually concentrates. Regions without a
  CNIR/share match report NaN rather than a fabricated zero.

Interpretation
--------------
Comparative-static, like the rest of the model: the indicator's value is the
*change* in irrigation demand under a policy or crop-mix scenario relative to the
base, driven by how crop areas reallocate. Absolute levels carry the usual
caveats of the underlying CROPWAT coefficients.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

_HERE = Path(__file__).parent
MM_HA_TO_M3 = 10.0   # 1 mm depth over 1 ha = 10 m3


@dataclass
class WaterResult:
    """Regional irrigation water demand and its drivers."""

    by_region: pd.DataFrame          # region x {demand_Mm3, irr_area_1000ha, ...}
    total_demand_Mm3: float          # EU total irrigation water demand (million m3)
    by_crop_Mm3: pd.Series           # demand split by crop
    n_regions_covered: int
    notes: Dict = field(default_factory=dict)


def _parse_cropwat(path: Path, item: str = "CNIR") -> pd.DataFrame:
    """Parse CAPRI cropwat GAMS param -> DataFrame [region8, crop] = value (mm)."""
    rows = []
    pat = re.compile(r"\s*'([^']+)'\.'([^']+)'\.'([^']+)'\s+([-\d.]+)")
    with open(path) as fh:
        for line in fh:
            m = pat.match(line)
            if m and m.group(3) == item:
                rows.append((m.group(1), m.group(2), float(m.group(4))))
    df = pd.DataFrame(rows, columns=["region8", "crop", "value"])
    return df.pivot_table(index="region8", columns="crop", values="value")


def _parse_irrishare(path: Path, year: str = "2016") -> pd.Series:
    """Parse CAPRI irrishare GAMS param -> Series [region8] = share (fraction).

    The series carries both NUTS-region codes and national aggregates (e.g.
    ES000000). 2016 has the fullest regional detail (adjacent to the 2017 base;
    irrigation shares are structural and near-constant year to year). Both the
    regional and national entries are returned; the module applies a national
    fallback where a region has no regional share.
    """
    rows = []
    pat = re.compile(r"\s*'([^']+)'\.'([^']+)'\.'([^']+)'\.'([^']+)'\s+([-\d.]+)")
    with open(path) as fh:
        for line in fh:
            m = pat.match(line)
            if m and m.group(4) == year:
                rows.append((m.group(1), float(m.group(5))))
    s = pd.DataFrame(rows, columns=["region8", "share"]).set_index("region8")["share"]
    return s[~s.index.duplicated(keep="first")]


class WaterDemandModule:
    """Compute agricultural irrigation water demand by region.

    Parameters
    ----------
    data : dict
        Model data (for crop areas fallback and region list).
    cropwat_path, irrishare_path : Path, optional
        Locations of the CROPWAT and irrigation-share CSVs. If not given, the
        module looks for them under the data directory's ``sources/water``.
    base_year : str
        Year to read from the irrigation-share series (default "2017").
    """

    def __init__(self, data: dict,
                 cropwat_path: Optional[Path] = None,
                 irrishare_path: Optional[Path] = None,
                 base_year: str = "2016"):
        self.data = data
        self._remap = json.loads((_HERE / "_nuts_remap.json").read_text())
        self.cnir = _parse_cropwat(Path(cropwat_path)) if cropwat_path else None
        self.share = (_parse_irrishare(Path(irrishare_path), base_year)
                      if irrishare_path else None)

    # -- region code mapping (old NUTS vintages -> model NUTS-2016) --
    def _to_model_region(self, region8: str) -> Optional[str]:
        n2 = region8[:4]
        if n2 in self._remap:
            return self._remap[n2]
        model_regions = set(self.data["areas"].index)
        return n2 if n2 in model_regions else None

    def _mapped_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Reindex a region8-indexed frame onto model NUTS-2016 regions."""
        out = {}
        for r8 in frame.index:
            mr = self._to_model_region(r8)
            if mr is not None and mr not in out:   # first match wins
                out[mr] = frame.loc[r8]
        return pd.DataFrame(out).T

    def compute(self, supply_results: Optional[Dict] = None) -> WaterResult:
        """Compute irrigation water demand per region and crop.

        Parameters
        ----------
        supply_results : dict[region -> SupplyResult], optional
            If given, crop areas are taken from solved activity levels; otherwise
            the base areas from ``data['areas']`` are used.
        """
        if self.cnir is None or self.share is None:
            raise ValueError("water data not loaded; pass cropwat_path and "
                             "irrishare_path to WaterDemandModule")

        cnir = self._mapped_frame(self.cnir)          # region x crop, mm

        # irrigation share: build a per-model-region share with national fallback.
        # The raw series carries regional codes (mapped to NUTS-2016) plus national
        # aggregates (e.g. ES000000). A region uses its own share if present, else
        # its country's national share.
        raw_share = self.share
        national = {}
        regional = {}
        for r8, val in raw_share.items():
            if r8.endswith("000000"):
                national[r8[:2]] = float(val)
            else:
                mr = self._to_model_region(r8)
                if mr is not None and mr not in regional:
                    regional[mr] = float(val)
        areas_index = self.data["areas"].index
        share = {}
        for reg in areas_index:
            if reg in regional:
                share[reg] = regional[reg]
            elif reg[:2] in national:
                share[reg] = national[reg[:2]]
        share = pd.Series(share)

        # crop areas (1000 ha): solved levels if available, else base areas
        areas = self.data["areas"]
        if supply_results:
            area_rows = {}
            for reg, res in supply_results.items():
                acts = getattr(res, "activities", None)
                if acts is not None:
                    area_rows[reg] = acts
            if area_rows:
                areas = pd.DataFrame(area_rows).T.reindex(columns=areas.columns).fillna(0.0)

        crops = [c for c in cnir.columns if c in areas.columns]
        regions = [r for r in areas.index if r in cnir.index and r in share.index]

        rows = []
        crop_totals = pd.Series(0.0, index=crops)
        for reg in regions:
            sh = float(share.get(reg, np.nan))
            if not np.isfinite(sh):
                continue
            irr_area_total = 0.0
            demand_total = 0.0
            for c in crops:
                area_1000ha = float(areas.at[reg, c]) if c in areas.columns else 0.0
                cnir_mm = float(cnir.at[reg, c]) if c in cnir.columns else np.nan
                if area_1000ha <= 0 or not np.isfinite(cnir_mm):
                    continue
                irr_area = sh * area_1000ha * 1000.0            # ha
                demand_m3 = cnir_mm * irr_area * MM_HA_TO_M3    # m3
                demand_Mm3 = demand_m3 / 1e6                    # million m3
                irr_area_total += irr_area
                demand_total += demand_Mm3
                crop_totals[c] += demand_Mm3
            rows.append({
                "region": reg,
                "irrigation_share": sh,
                "irrigated_area_1000ha": irr_area_total / 1000.0,
                "water_demand_Mm3": demand_total,
            })

        df = pd.DataFrame(rows).set_index("region") if rows else pd.DataFrame()
        total = float(df["water_demand_Mm3"].sum()) if not df.empty else 0.0
        if not df.empty and total > 0:
            df["water_demand_m3_per_ha"] = (
                df["water_demand_Mm3"] * 1e6
                / (df["irrigated_area_1000ha"] * 1000.0).replace(0, np.nan))

        return WaterResult(
            by_region=df,
            total_demand_Mm3=total,
            by_crop_Mm3=crop_totals.sort_values(ascending=False),
            n_regions_covered=len(df),
            notes={
                "method": "demand = CNIR(mm) x irrigated_area(ha) x 10 m3/mm-ha; "
                          "irrigated_area = irrigation_share x crop_area",
                "cnir_source": "CAPRI CROPWAT p_cropwatReq (FAO)",
                "share_source": "CAPRI p_irriShare (Eurostat FSS)",
                "coverage": f"{len(df)}/{len(areas.index)} regions; near-complete "
                            "for the irrigation-intensive Mediterranean",
                "scope": "agricultural water DEMAND indicator; not catchment "
                         "hydrology; comparative-static (read the change vs base)",
            },
        )
