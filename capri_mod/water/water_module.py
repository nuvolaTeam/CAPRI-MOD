"""Irrigation water-demand indicator.

Method
------
For each region r and crop c the net irrigation water requirement is

    demand(r,c) = CNIR(r,c) [mm] x irrigated_area(r,c) [ha] x 10 [m3 per mm-ha]
    irrigated_area(r,c) = irrigated_share(r,c) x crop_area(r,c)

CNIR is CROPWAT's crop net irrigation requirement (the blue water a crop needs beyond effective rainfall) from CAPRI's
water database (p_cropwatReq; CAPRI's CWRB = 10 x CNIR m3/ha). The irrigated shares follow CAPRI's water database
(water_database.gms): each region's irrigated area (Eurostat FSS 'irrigated once a year', p_irriShare IRR2, x UAA) on
the crops CAPRI's water module irrigates, rice entirely and the other crops at one common share (CAPRI fits
crop-specific shares to FSS crop data we do not have). They are built by tools/build/build_irrigation_2017.py into
capri_data/2017/environment/irrigation_2017.csv, which records the survey year and whether the share is the unit's own
or its member state's. crop_area is the supply module's solved level, or the base area.

Scope
-----
- Net requirement at the field, not abstraction: CAPRI's irrigation-method efficiencies (drip, sprinkler, surface)
  are not applied.
- Crop-specific irrigated shares: CAPRI estimates them for EU regions from the FSS crop data; those data are not among
  our sources, so the irrigable crops of a region other than rice share one irrigated share
  (docs/DEPARTURES_FROM_CAPRI.md).
- Comparative-static: the shares are fixed, the indicator moves with the crop areas; the irrigated/rainfed split of
  CAPRI's water module (supply with water, 'Use water module in supply models', off in CAPRI's reference runs) is not
  modelled.
- Not covered: Ireland (no irrigation share in CAPRI's data), Norway (no CROPWAT requirements), textile crops (no
  CROPWAT requirement): NaN or zero contribution, reported in the result's notes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd


MM_HA_TO_M3 = 10.0   # 1 mm depth over 1 ha = 10 m3


@dataclass
class WaterResult:
    """Regional irrigation water requirement and its drivers."""

    by_region: pd.DataFrame          # region x {irr2_share, irrigated_area_1000ha, water_demand_Mm3, ...}
    total_demand_Mm3: float          # total over the covered regions (million m3)
    by_crop_Mm3: pd.Series           # demand by crop
    n_regions_covered: int
    notes: Dict = field(default_factory=dict)


class WaterDemandModule:
    """Irrigation water requirement by region and crop.

    data: the model data dict (base areas, data["areas"], 1000 ha).
    irrigation_path: the irrigation table; default the run's environment/irrigation_2017.csv (capri_mod/data/inputs.py).
    """

    def __init__(self, data: dict, irrigation_path: Optional[Path] = None):
        self.data = data
        from capri_mod.data.inputs import current
        inp = current()
        self.table = inp.read(Path(irrigation_path)) if irrigation_path else inp.csv("irrigation_2017.csv", "environment")

    def _areas(self, supply_results: Optional[Dict]) -> pd.DataFrame:
        base = self.data["areas"]
        if not supply_results:
            return base
        rows = {r: res.activities for r, res in supply_results.items()
                if getattr(res, "activities", None) is not None}
        return pd.DataFrame(rows).T.reindex(columns=base.columns).fillna(0.0)

    def compute(self, supply_results: Optional[Dict] = None) -> WaterResult:
        """supply_results: {region: SupplyResult}; without them, the base areas. Regions not in the irrigation table
        (Ireland) are left out; crops without a CNIR count as no requirement and are listed in the notes."""
        areas = self._areas(supply_results)
        t = self.table[self.table.region.isin(areas.index) & self.table.activity.isin(areas.columns)].copy()
        t["area_1000ha"] = [float(areas.at[r, a]) for r, a in zip(t.region, t.activity)]
        t["irrigated_1000ha"] = t.irrigated_share * t.area_1000ha
        t["demand_Mm3"] = t.cnir_mm * MM_HA_TO_M3 * t.irrigated_1000ha * 1000.0 / 1e6
        g = t.groupby("region")
        df = pd.DataFrame({
            "irr2_share": g.irr2_share.first(),
            "irr2_year": g.irr2_year.first(),
            "irr2_level": g.irr2_level.first(),
            "irrigated_area_1000ha": g.irrigated_1000ha.sum(),
            "water_demand_Mm3": g.demand_Mm3.sum(min_count=1),
        })
        df["water_demand_m3_per_ha"] = (df.water_demand_Mm3 * 1e6
                                        / (df.irrigated_area_1000ha * 1000.0).replace(0, np.nan))
        missing = t[t.cnir_mm.isna() & (t.irrigated_1000ha > 0)]
        total = float(df.water_demand_Mm3.sum())
        return WaterResult(
            by_region=df,
            total_demand_Mm3=total,
            by_crop_Mm3=t.groupby("activity").demand_Mm3.sum().sort_values(ascending=False),
            n_regions_covered=int(df.water_demand_Mm3.notna().sum()),
            notes={
                "method": "demand = CNIR(mm) x 10 m3/mm-ha x irrigated area; irrigated area = irrigated share x "
                          "crop area (FSS irrigated area of the region; rice entirely, one share for the other "
                          "irrigable crops)",
                "regions_without_irrigation_data": sorted(set(areas.index) - set(self.table.region)),
                "irrigated_1000ha_without_cnir": {k: float(v) for k, v in
                                                  missing.groupby("activity").irrigated_1000ha.sum().items()},
                "scope": "net irrigation requirement at the field (no irrigation-method efficiency); "
                         "comparative-static (read the change against the base)",
            },
        )
