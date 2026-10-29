"""Irrigated shares and net irrigation requirements per regional unit and crop, base year 2017, for the irrigation
water-demand indicator (capri_mod/water).

Sources (CAPRI's water database inputs, gams/water_database.gms, as uploaded):
  capri_data/sources/water/irrishare.csv   p_irriShare(region, IRRI|IRR2, IRSH, year): share of irrigable (IRRI) and
                                           irrigated (IRR2, 'irrigated once a year') area in UAAR, Eurostat FSS
  capri_data/sources/water/cropwat.csv     p_cropwatReq(region, crop, CPET|CRAIN|CNIR|YRATIO|YFACT): CROPWAT crop
                                           water requirements, mm
  capri_data/sources/capreg/capreg_activity_levels.csv   CAPRI's 2017 levels (ROOF and OFAR, the model's OFOD)

Method. CAPRI's water database (water_database.gms) estimates each EU region's irrigated area per crop with a
highest-posterior-density fit (lines 513-640) to the FSS irrigated area of the region (IRR2, 'irrigated once a year':
the crops' irrigated areas add up to it, irArea_) and the FSS crop-specific irrigated areas (p_wdata_fss); rice
(PARI) is irrigated entirely. The FSS crop-specific data are not among our sources. Without them this builder keeps
CAPRI's two data-based parts and spreads the rest evenly:
  - the region's irrigated area = its IRR2 share x its UAA (the model's 2017 crop areas), as in CAPRI's fit;
  - rice entirely irrigated (lines 290-292);
  - the remaining irrigated area on the other crops CAPRI's water module irrigates (sets_water.gms WAggAct, with
    WaterDB on), one share for all of them, between 0.001 (line 668) and 1. CAPRI assumes one share across crops
    where the FSS gives a crop group only (line 294) and, where no crop data exist (Turkey, the Western Balkans, lines
    664-668), the IRR2 share on every crop without the adding-up; with the adding-up the region's observed irrigated
    area is kept, which CAPRI's EU estimate also does. A departure (docs/DEPARTURES_FROM_CAPRI.md).
Where the irrigated area exceeds all irrigable crops (irrigated grassland), the excess is left out and printed.
The IRR2 share is the unit's latest FSS observation up to 2017 (CAPRI fills the years between surveys with trend
estimates, lines 325-440; 2017 itself has regional values for 8 units only); a unit without a regional observation
takes its member state's (CAPRI's rule where data are national only, line 658).
The water requirement per irrigated ha is CROPWAT's net irrigation requirement CNIR (CAPRI's CWRB = 10 x CNIR m3/ha).

Model activities: CORN = CAPRI's MAIZ, WINE = TWIN, OFOD = ROOF + OFAR (CNIR weighted by CAPRI's 2017 levels).
Grassland, rye, oats, other cereals and tobacco are not irrigable in CAPRI's water module (no WAggAct).

Output: capri_data/2017/environment/irrigation_2017.csv
    region, activity, irrigated_share, cnir_mm, irr2_share, irr2_year, irr2_level (regional | national)
    python tools/build/build_irrigation_2017.py
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from capri_mod.csvio import read_csv, to_csv  # noqa: E402

SRC = ROOT / "capri_data" / "sources" / "water"
DEST = ROOT / "capri_data" / "2017" / "environment" / "irrigation_2017.csv"
BASE_YEAR = 2017
#: sets_water.gms MAP_AA: crops with rainfed and irrigated variants (ROOF, OFAR, TEXT with WaterDB on)
WAGG = ["SWHE", "DWHE", "BARL", "MAIZ", "RAPE", "SUNF", "SOYA", "MAIF", "ROOF", "OFAR", "PARI", "OLIV", "PULS", "POTA",
        "SUGB", "TEXT", "TOMA", "OVEG", "APPL", "OFRU", "CITR", "TAGR", "TABO", "TWIN"]
#: model activity -> CAPRI activities
MODEL = {**{c: (c,) for c in WAGG if c not in ("MAIZ", "TWIN", "ROOF", "OFAR")},
         "CORN": ("MAIZ",), "WINE": ("TWIN",), "OFOD": ("ROOF", "OFAR")}
#: capreg_activity_levels.csv names CAPRI's MAIZ as the model does
LEVEL_COL = {"MAIZ": "CORN"}
IRSH_MIN = 0.001      # water_database.gms line 668: max(0.001, IRR2 share)


def gams_records(path, n):
    pat = re.compile(r"\s*" + r"\.".join([r"'([^']+)'"] * n) + r"\s+([-\d.Ee+]+)")
    with open(path) as fh:
        return [m.groups() for m in map(pat.match, fh) if m]


def main():
    units = list(read_csv(ROOT / "capri_data" / "shared" / "regional_units.csv").region)
    sh = pd.DataFrame(gams_records(SRC / "irrishare.csv", 4), columns=["region", "item", "type", "year", "value"])
    sh = sh[(sh["item"] == "IRR2") & (sh.type == "IRSH")].astype({"year": int, "value": float})
    sh = sh[sh.year <= BASE_YEAR]
    latest = sh.sort_values("year").groupby("region").last()
    cw = pd.DataFrame(gams_records(SRC / "cropwat.csv", 3), columns=["region", "crop", "item", "value"])
    cnir = cw[cw["item"] == "CNIR"].astype({"value": float}).pivot_table(index="region", columns="crop", values="value")
    lev = read_csv(ROOT / "capri_data" / "sources" / "capreg" / "capreg_activity_levels.csv", index_col=0)

    uaa = read_csv(ROOT / "capri_data" / "2017" / "supply" / "base_areas.csv", index_col=0).sum(axis=1)
    rows, none, unplaced = [], [], {}
    for u in units:
        if u in latest.index:
            share, year, level = float(latest.at[u, "value"]), int(latest.at[u, "year"]), "regional"
        elif u[:2] + "000000" in latest.index:
            n = u[:2] + "000000"
            share, year, level = float(latest.at[n, "value"]), int(latest.at[n, "year"]), "national"
        else:
            none.append(u)
            continue
        lv, req = {}, {}
        for act, caps in MODEL.items():
            l_ = {}
            for c in caps:
                k = LEVEL_COL.get(c, c)
                if k not in lev.columns:
                    raise KeyError(f"{k}: not in capreg_activity_levels.csv")
                l_[c] = float(lev.at[u, k]) if pd.notna(lev.at[u, k]) else 0.0
            if sum(l_.values()) <= 1e-4:                                  # CAPRI: LEVL gt 1.e-4
                continue
            lv[act] = sum(l_.values())
            have = {c: float(cnir.at[u, c]) for c in caps if u in cnir.index and c in cnir.columns
                    and pd.notna(cnir.at[u, c])}
            w = sum(l_[c] for c in have)
            req[act] = sum(have[c] * l_[c] for c in have) / w if w > 0 else float("nan")
        # the region's irrigated area (IRR2 share x UAA) on its irrigable crops: rice entirely, the rest one share
        irr = share * float(uaa[u])
        rest = sum(v for a, v in lv.items() if a != "PARI")
        common = min(1.0, max(IRSH_MIN, (irr - lv.get("PARI", 0.0)) / rest)) if rest > 0 else IRSH_MIN
        placed = lv.get("PARI", 0.0) + common * rest
        if placed < 0.999 * irr:
            unplaced[u] = irr - placed
        for act in lv:
            rows.append({"region": u, "activity": act, "irrigated_share": 1.0 if act == "PARI" else common,
                         "cnir_mm": req[act], "irr2_share": share, "irr2_year": year, "irr2_level": level})
    out = pd.DataFrame(rows)
    DEST.parent.mkdir(parents=True, exist_ok=True)
    to_csv(out, DEST, index=False)
    reg = out.drop_duplicates("region")
    print(f"wrote {DEST.relative_to(ROOT)}: {len(out)} rows, {reg.region.nunique()} units "
          f"({(reg.irr2_level == 'national').sum()} on their member state's share; years "
          f"{reg.irr2_year.value_counts().sort_index().to_dict()}); no irrigation data: {none}; "
          f"rows without CNIR: {int(out.cnir_mm.isna().sum())} "
          f"({sorted(out[out.cnir_mm.isna()].region.unique())[:8]}...); irrigated area beyond the irrigable crops "
          f"(1000 ha): { {k: round(v, 2) for k, v in unplaced.items()} }")


if __name__ == "__main__":
    main()
