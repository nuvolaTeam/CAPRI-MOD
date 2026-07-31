"""
Extract the nine remaining model inputs from the capreg DATA2 dumps.

Everything here is already in dumps held locally; no new GAMS run is required.

    LEVL                    activity levels -> base_areas, land_availability,
                            animal_numbers
    PRME                    CAP premium per activity -> cap_payments
    NITF PHOF POTF          fertiliser application -> nutrient_coefs
    MANN MANP MANK          manure nutrients (new input; the environmental
                            module currently hardcodes N excretion)
    FEED FCER FGRA FMAI     feed use by item -> feed availability
    FROO FOFA FPRO FCOM
    FMIL FSGM FSTR FOTH

On cap payments
---------------
The live cap_payments.csv is region x instrument (BPS, ANC, AES, ORGANIC), so a
region's payment is applied uniformly across its activities. CAPRI's PRME is per
activity: at DE11 it is 360.79 EUR/ha for soft wheat, 108.24 for dairy cows and
8.20 for bulls. Since the premium enters net revenue directly, a uniform
application distorts the relative profitability of every activity within a
region -- which is exactly what the PMP calibration is trying to capture.

Usage
-----
    python tools/extract_remaining_nine.py --export-dir /path/to/capri_export
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

RECORD = re.compile(
    r"^'([A-Z]{2}[A-Z0-9]{6})'\.'([A-Z0-9_]+)'\.'([A-Za-z0-9_]+)'\.'Y'\s+([-\d.Ee+]+)")

LEVEL = "LEVL"
PREMIUM = "PRME"
HERD = "HERD"
NUTRIENTS = {"NITF": "N", "PHOF": "P2O5", "POTF": "K2O"}
MANURE = {"MANN": "N", "MANP": "P2O5", "MANK": "K2O"}
FEED_ITEMS = ["FEED", "FCER", "FGRA", "FMAI", "FROO", "FOFA",
              "FPRO", "FCOM", "FMIL", "FSGM", "FSTR", "FOTH"]

# Aggregate land categories, carried in DATA2 as pseudo-activities.
LAND_CATEGORIES = ["UAAR", "ARAB", "GRAE", "GRAI", "SETA", "FALL", "OLND"]

WANTED = ({LEVEL, PREMIUM, HERD} | set(NUTRIENTS) | set(MANURE) | set(FEED_ITEMS))


def parse(path: Path) -> pd.DataFrame:
    rows = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = RECORD.match(line)
            if m and m.group(3) in WANTED:
                rows.append((m.group(1), m.group(2), m.group(3), float(m.group(4))))
    return pd.DataFrame(rows, columns=["region", "activity", "item", "value"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export-dir", required=True, type=Path)
    ap.add_argument("--data-dir", type=Path, default=Path("capri_data"))
    args = ap.parse_args()

    files = sorted(args.export_dir.glob("DATA2_*.txt"))
    print(f"parsing {len(files)} files for {len(WANTED)} items...")
    df = pd.concat([parse(f) for f in files], ignore_index=True)
    df = df.drop_duplicates(["region", "activity", "item"], keep="last")

    cw = json.loads((args.data_dir / "shared/nuts_crosswalk.json").read_text())
    rev = {}
    for mr, codes in cw.get("aliases", {}).items():
        for c in codes:
            rev.setdefault(c, mr)
    for mr, c in cw["resolved"].items():
        rev.setdefault(c, mr)
    df["model_region"] = df.region.map(rev)
    df = df.dropna(subset=["model_region"])
    df["activity"] = df.activity.replace({"MAIZ": "CORN"})

    out = args.data_dir / "sources" / "capreg"
    out.mkdir(parents=True, exist_ok=True)
    summary = {}

    def wide(item, exclude_land=True):
        sub = df[df.item == item]
        if exclude_land:
            sub = sub[~sub.activity.isin(LAND_CATEGORIES)]
        return sub.pivot_table(index="model_region", columns="activity",
                               values="value", aggfunc="last")

    # 1. activity levels -> base areas and animal numbers
    levl = wide(LEVEL)
    levl.to_csv(out / "capreg_activity_levels.csv")
    summary["activity_levels"] = list(levl.shape)
    print(f"activity levels : {levl.shape[0]} regions x {levl.shape[1]} activities")

    # 2. land categories
    land = df[(df.item == LEVEL) & (df.activity.isin(LAND_CATEGORIES))].pivot_table(
        index="model_region", columns="activity", values="value", aggfunc="last")
    land.to_csv(out / "capreg_land.csv")
    summary["land"] = list(land.shape)
    print(f"land categories : {land.shape[0]} regions x {list(land.columns)}")

    # 3. CAP premiums per activity
    prme = wide(PREMIUM)
    prme.to_csv(out / "capreg_cap_premium.csv")
    summary["cap_premium"] = list(prme.shape)
    print(f"CAP premiums    : {prme.shape[0]} regions x {prme.shape[1]} activities")

    # 4. herd sizes
    herd = wide(HERD)
    herd.to_csv(out / "capreg_herds.csv")
    summary["herds"] = list(herd.shape)
    print(f"herd sizes      : {herd.shape[0]} regions x {herd.shape[1]} animals")

    # 5. fertiliser application
    nu = df[df.item.isin(NUTRIENTS)].copy()
    nu["nutrient"] = nu.item.map(NUTRIENTS)
    nu[["model_region", "activity", "nutrient", "value"]].to_csv(
        out / "capreg_nutrient_coefs.csv", index=False)
    summary["nutrients"] = int(len(nu))
    print(f"fertiliser      : {len(nu):,} records")

    # 6. manure nutrients
    ma = df[df.item.isin(MANURE)].copy()
    ma["nutrient"] = ma.item.map(MANURE)
    ma[["model_region", "activity", "nutrient", "value"]].to_csv(
        out / "capreg_manure_nutrients.csv", index=False)
    summary["manure"] = int(len(ma))
    print(f"manure          : {len(ma):,} records")

    # 7. feed use
    fe = df[df.item.isin(FEED_ITEMS)]
    fe[["model_region", "activity", "item", "value"]].to_csv(
        out / "capreg_feed_use.csv", index=False)
    summary["feed"] = int(len(fe))
    print(f"feed use        : {len(fe):,} records")

    (args.data_dir / "validation" / "remaining_nine_extraction.json").write_text(
        json.dumps(summary, indent=1))
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()
