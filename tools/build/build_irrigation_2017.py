"""Irrigated shares and net irrigation requirements per regional unit and crop, base year 2017, for the irrigation
water-demand indicator (capri_mod/water).

Sources (CAPRI's water database inputs, gams/water_database.gms, as uploaded; gdxdumps converted to CSV by
tools/build/convert_sources.py):
  capri_data/sources/raw/capri/dat/water/irrishare_p_irriShare.parquet   p_irriShare(region, IRRI|IRR2, IRSH, year): share of
                                           irrigable (IRRI) and irrigated (IRR2, 'irrigated once a year') area in UAAR,
                                           Eurostat FSS
  capri_data/sources/raw/capri/dat/water/cropwat_p_cropwatReq.parquet   p_cropwatReq(region, crop, CPET|CRAIN|CNIR|YRATIO|YFACT):
                                           CROPWAT crop water requirements, mm
  capri_data/sources/intermediate/capreg/capreg_activity_levels.parquet   CAPRI's 2017 levels

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

Model activities: CORN = CAPRI's MAIZ, WINE = TWIN; ROOF and OFAR their own (until S2, 7 November 2026, OFOD = ROOF +
OFAR, CNIR weighted by CAPRI's 2017 levels).
Grassland, rye, oats, other cereals and tobacco are not irrigable in CAPRI's water module (no WAggAct).

Output: capri_data/2017/environment/irrigation_2017.csv
    region, activity, irrigated_share, cnir_mm, irr2_share, irr2_year, irr2_level (regional | national)
    python tools/build/build_irrigation_2017.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from capri_mod.csvio import read_csv, to_csv  # noqa: E402
import sys as _sys_nc  # noqa: E402
_sys_nc.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2] / "tools" / "lib"))
from _model_regions import national_code as _national_code  # noqa: E402  (TUR for Turkey's units, 4 November 2026)
from _sources_io import read_source, source_records, write_source  # noqa: E402  (capri_data/sources: Parquet)

SRC = ROOT / "capri_data" / "sources" / "raw" / "capri" / "dat" / "water"
DEST = ROOT / "capri_data" / "2017" / "environment" / "irrigation_2017.csv"
BASE_YEAR = 2017
#: sets_water.gms MAP_AA: crops with rainfed and irrigated variants (ROOF, OFAR, TEXT with WaterDB on)
WAGG = ["SWHE", "DWHE", "BARL", "MAIZ", "RAPE", "SUNF", "SOYA", "MAIF", "ROOF", "OFAR", "PARI", "OLIV", "PULS", "POTA",
        "SUGB", "TEXT", "TOMA", "OVEG", "APPL", "OFRU", "CITR", "TAGR", "TABO", "TWIN"]
#: model activity -> CAPRI activities
MODEL = {**{c: (c,) for c in WAGG if c not in ("MAIZ", "TWIN")},
         "CORN": ("MAIZ",), "WINE": ("TWIN",)}   # ROOF and OFAR the model's own since S2 (7 November 2026)
#: capreg_activity_levels.parquet names CAPRI's MAIZ as the model does
LEVEL_COL = {"MAIZ": "CORN"}
IRSH_MIN = 0.001      # water_database.gms line 668: max(0.001, IRR2 share)


def records(name):
    """A gdxdump converted to CSV (tools/build/convert_sources.py), every column as text."""
    return read_source(SRC / name, dtype=str, keep_default_na=False)       # Parquet (_sources_io)


def main():
    units = list(read_csv(ROOT / "capri_data" / "codes" / "regional_units.csv").region)
    sh = records("irrishare_p_irriShare.parquet")
    sh = sh[(sh["item"] == "IRR2") & (sh.type == "IRSH")].astype({"year": int, "value": float})
    sh = sh[sh.year <= BASE_YEAR]
    latest = sh.sort_values("year").groupby("region").last()
    cw = records("cropwat_p_cropwatReq.parquet")
    cnir = cw[cw["item"] == "CNIR"].astype({"value": float}).pivot_table(index="region", columns="crop", values="value")
    lev = read_source(ROOT / "capri_data" / "sources" / "intermediate" / "capreg" / "capreg_activity_levels.parquet", index_col=0)

    uaa = read_csv(ROOT / "capri_data" / "2017" / "supply" / "base_areas.csv", index_col=0).sum(axis=1)
    rows, none, unplaced = [], [], {}
    for u in units:
        if u in latest.index:
            share, year, level = float(latest.at[u, "value"]), int(latest.at[u, "year"]), "regional"
        elif _national_code(u) in latest.index:
            n = _national_code(u)
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
                    raise KeyError(f"{k}: not in capreg_activity_levels.parquet")
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
