"""
Rebase CAPRI-Python to a newer base year from public data.

Pulls crop areas, yields, animal numbers and producer prices from the Eurostat
REST API (and, optionally, world prices / trade from FAOSTAT) and writes them
into capri_data/<year>/ in the format the model expects.

    python -m capri_mod.data.rebase --year 2022 --countries DE FR --dry-run
    python -m capri_mod.data.rebase --year 2022 --countries DE FR

Design notes
------------
* This does NOT need CAPRI. The model's PMP calibrator recomputes the cost
  matrix Q at runtime from base levels + net revenues + supply elasticities, so
  a new base year needs only the observable data below. Structural parameters
  (supply elasticities, Armington sigmas, emission factors) are carried forward
  from the 2017 folder — see `--carry-forward`.
* Eurostat returns NUTS-2 codes directly, which is the model's regional unit.
* Coverage is genuinely patchy for some crop/region combinations. The script
  reports coverage per file rather than silently filling gaps; see
  `coverage_report.json`.

Eurostat API
------------
Base:  https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/<dataset>
Format: JSON-stat 2.0.  Query params filter dimensions, e.g. ?geo=DE11&time=2022
Datasets used:
  apro_cpshr   crop production by NUTS-2 (area, yield, production)
  apro_mt_lscatl / apro_mt_lspig / apro_mt_lssheep  livestock by NUTS-2
  apri_ap_crpouta  agricultural producer prices (national)
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

try:
    import requests
except ImportError:  # requests is optional; urllib fallback
    requests = None
import urllib.parse
import urllib.request

EUROSTAT = ("https://ec.europa.eu/eurostat/api/dissemination/"
            "statistics/1.0/data")
FAOSTAT = "https://faostatservices.fao.org/api/v1/en/data"

# --------------------------------------------------------------------------- #
# Code maps: Eurostat -> CAPRI activity codes
# Eurostat crop codes (apro_cpshr "crops" dimension) -> model activity
# --------------------------------------------------------------------------- #
CROP_MAP: Dict[str, str] = {
    "C1120": "SWHE",   # common winter wheat and spelt
    "C1130": "DWHE",   # durum wheat
    "C1150": "RYEM",   # rye and winter cereal mixtures
    "C1200": "BARL",   # barley
    "C1300": "OATS",   # oats and spring cereal mixtures
    "C1500": "CORN",   # grain maize and corn-cob-mix
    "C0000": "OCER",   # cereals for the production of grain (residual -> OCER)
    "P1000": "PULS",   # dry pulses and protein crops
    "R1000": "POTA",   # potatoes
    "R2000": "SUGB",   # sugar beet
    "I1110": "RAPE",   # rape and turnip rape seeds
    "I1120": "SUNF",   # sunflower seed
    "I1130": "SOYA",   # soya
    "V0000": "OVEG",   # fresh vegetables (residual)
    "T0000": "TOMA",   # tomatoes  (verify code against dataset)
    "F1000": "APPL",   # apples
    "F0000": "OFRU",   # fruit (residual)
    "W1000": "WINE",   # grapes / wine
    "O1000": "OLIV",   # olives
    "G1000": "GRAS",   # permanent grassland
    "G2000": "MAIF",   # green maize (forage)
}

# Eurostat livestock datasets -> model animal codes
LIVESTOCK: Dict[str, Dict[str, str]] = {
    # dataset : { eurostat animal code : model code }
    "apro_mt_lscatl": {
        "A2300F": "DCOW",   # dairy cows
        "A2300G": "SCOW",   # non-dairy (suckler) cows
        "A2200M": "BULL",   # male bovine 1-2y / >2y  (aggregate; see notes)
        "A2200F": "HEIF",   # female bovine 1-2y
        "A2100": "CALV",    # bovine < 1 year
    },
    "apro_mt_lspig": {
        "A3100": "PIGS",    # pigs, total
        "A3132": "SOWS",    # breeding sows
    },
    "apro_mt_lssheep": {
        "A4100": "SHGO",    # sheep
    },
}

# Model activity -> Eurostat producer-price product code (apri_ap_crpouta)
PRICE_MAP: Dict[str, str] = {
    "SWHE": "01111",   # soft wheat
    "DWHE": "01112",   # durum wheat
    "BARL": "01113",
    "CORN": "01114",   # grain maize
    "OATS": "01115",
    "RYEM": "01116",
    "POTA": "01131",
    "SUGB": "01132",
    "RAPE": "01141",
    "SUNF": "01142",
    "SOYA": "01143",
}

# Files carried forward unchanged from the reference year (structural /
# slow-changing; not year-specific in any meaningful sense)
CARRY_FORWARD = {
    "supply": [
        "supply_elasticities_regional.csv",
        "pmp_own_price_elasticities.csv",
        "pmp_diagonal_terms.csv",       # reference only; Q is recomputed at runtime
        "pmp_crossgroup_terms.csv",     # reference only
        "input_requirements.csv",
        "variable_costs.csv",           # ideally updated; see --update-costs
        "land_availability.csv",
    ],
    "market": [
        "armington_params.csv",
        "world_prices.csv",
        "fao_market_baseline.json",
        "fao_processing_splits.json",
        "fao_demand_own_elas_eu.json",
    ],
    "policy": ["cap_payments.csv", "eu_mfn_tariffs.csv"],
    "environment": ["nutrient_coefs.csv", "crop_nutrient_export.csv",
                    "manure_ch4_ef_regional.csv", "climate_zones.csv"],
    "feed": ["feed_requirements.csv", "coco_feed_availability_national.csv"],
}


# --------------------------------------------------------------------------- #
# HTTP + JSON-stat
# --------------------------------------------------------------------------- #
def _get(url: str, params: dict, retries: int = 3, pause: float = 1.0) -> dict:
    """GET a JSON endpoint with light retry. Returns parsed JSON."""
    q = urllib.parse.urlencode(params, doseq=True)
    full = f"{url}?{q}"
    last = None
    for attempt in range(retries):
        try:
            if requests is not None:
                r = requests.get(full, timeout=60)
                r.raise_for_status()
                return r.json()
            with urllib.request.urlopen(full, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:            # noqa: BLE001
            last = e
            time.sleep(pause * (attempt + 1))
    raise RuntimeError(f"request failed after {retries} tries: {full}\n{last}")


def jsonstat_to_frame(js: dict) -> pd.DataFrame:
    """Flatten a JSON-stat 2.0 response into a tidy DataFrame.

    Eurostat returns a sparse value map keyed by the flattened index of the
    dimension cross-product; this expands it back into columns.
    """
    dims = js["id"]                      # dimension order
    sizes = js["size"]
    values = js.get("value", {})
    if isinstance(values, list):
        values = {str(i): v for i, v in enumerate(values) if v is not None}

    # category labels per dimension, ordered by their index
    cats = []
    for d in dims:
        idx = js["dimension"][d]["category"]["index"]
        if isinstance(idx, dict):
            ordered = sorted(idx.items(), key=lambda kv: kv[1])
            cats.append([k for k, _ in ordered])
        else:
            cats.append(list(idx))

    rows = []
    for flat_str, val in values.items():
        flat = int(flat_str)
        coords = []
        for i in range(len(dims) - 1, -1, -1):
            coords.insert(0, flat % sizes[i])
            flat //= sizes[i]
        rec = {d: cats[i][c] for i, (d, c) in enumerate(zip(dims, coords))}
        rec["value"] = val
        rows.append(rec)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Fetchers
# --------------------------------------------------------------------------- #
def fetch_crops(year: int, geos: List[str]) -> pd.DataFrame:
    """apro_cpshr: area (AR) and yield (YI) per NUTS-2 and crop."""
    js = _get(f"{EUROSTAT}/apro_cpshr", {
        "format": "JSON", "lang": "EN", "time": str(year),
        "geo": geos, "strucpro": ["AR", "YI"],
    })
    df = jsonstat_to_frame(js)
    df["activity"] = df["crops"].map(CROP_MAP)
    return df.dropna(subset=["activity"])


def fetch_livestock(year: int, geos: List[str]) -> pd.DataFrame:
    frames = []
    for dataset, codemap in LIVESTOCK.items():
        try:
            js = _get(f"{EUROSTAT}/{dataset}", {
                "format": "JSON", "lang": "EN", "time": str(year),
                "geo": geos, "animals": list(codemap),
            })
        except Exception as e:            # noqa: BLE001
            print(f"  ! {dataset}: {e}")
            continue
        d = jsonstat_to_frame(js)
        d["activity"] = d["animals"].map(codemap)
        frames.append(d.dropna(subset=["activity"]))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def fetch_producer_prices(year: int) -> pd.DataFrame:
    """apri_ap_crpouta: EU producer prices (national, EUR/t)."""
    js = _get(f"{EUROSTAT}/apri_ap_crpouta", {
        "format": "JSON", "lang": "EN", "time": str(year),
        "currency": "EUR", "unit": "EUR_T",
    })
    df = jsonstat_to_frame(js)
    inv = {v: k for k, v in PRICE_MAP.items()}
    df["activity"] = df.get("prod_veg", pd.Series(dtype=str)).map(inv)
    return df.dropna(subset=["activity"])


# --------------------------------------------------------------------------- #
# Writers (model formats)
# --------------------------------------------------------------------------- #
def write_areas(df: pd.DataFrame, out: Path) -> dict:
    a = df[df["strucpro"] == "AR"]
    t = a.pivot_table(index="geo", columns="activity", values="value", aggfunc="sum")
    t.index.name = "region"
    t.to_csv(out / "base_areas.csv")
    return {"file": "base_areas.csv", "regions": len(t), "activities": t.shape[1]}


def write_yields(df: pd.DataFrame, out: Path) -> dict:
    y = df[df["strucpro"] == "YI"]
    t = y.pivot_table(index="geo", columns="activity", values="value", aggfunc="mean")
    t.index.name = "region"
    t.to_csv(out / "yields.csv")
    return {"file": "yields.csv", "regions": len(t), "activities": t.shape[1]}


def write_animals(df: pd.DataFrame, out: Path) -> dict:
    if df.empty:
        return {"file": "animal_numbers.csv", "regions": 0, "activities": 0}
    t = df.pivot_table(index="geo", columns="activity", values="value", aggfunc="sum")
    if {"DCOW", "SCOW"} <= set(t.columns):
        t["COWS"] = t["DCOW"].fillna(0) + t["SCOW"].fillna(0)
    t.index.name = ""
    t.to_csv(out / "animal_numbers.csv")
    return {"file": "animal_numbers.csv", "regions": len(t), "activities": t.shape[1]}


def write_prices(df: pd.DataFrame, out: Path) -> dict:
    if df.empty:
        return {"file": "producer_prices.csv", "commodities": 0}
    s = df.groupby("activity")["value"].mean().rename("price")
    s.to_frame().to_csv(out / "producer_prices.csv")
    return {"file": "producer_prices.csv", "commodities": len(s)}


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def carry_forward(src_year: Path, dst_year: Path) -> List[str]:
    copied = []
    for cat, files in CARRY_FORWARD.items():
        (dst_year / cat).mkdir(parents=True, exist_ok=True)
        for fn in files:
            s = src_year / cat / fn
            if s.exists():
                shutil.copy(s, dst_year / cat / fn)
                copied.append(f"{cat}/{fn}")
    return copied


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--year", type=int, required=True, help="new base year, e.g. 2022")
    ap.add_argument("--countries", nargs="+", default=["DE"],
                    help="country codes; NUTS-2 regions are requested per country")
    ap.add_argument("--data-dir", default="capri_data")
    ap.add_argument("--from-year", default="2017",
                    help="reference year to carry structural files forward from")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan and the API calls, fetch nothing")
    args = ap.parse_args(argv)

    data_dir = Path(args.data_dir)
    src = data_dir / args.from_year
    dst = data_dir / str(args.year)

    print(f"Rebase {args.from_year} -> {args.year}   countries={args.countries}")
    print(f"  source: {src}\n  target: {dst}\n")

    if args.dry_run:
        print("DRY RUN — no requests will be made.\n")
        print("Would fetch from Eurostat:")
        print(f"  apro_cpshr        areas + yields, NUTS-2, time={args.year}")
        print(f"  apro_mt_lscatl / lspig / lssheep   livestock, NUTS-2")
        print(f"  apri_ap_crpouta   producer prices (national, EUR/t)")
        print("\nWould carry forward from", src, "(structural, not year-specific):")
        for cat, files in CARRY_FORWARD.items():
            for fn in files:
                print(f"  {cat}/{fn}")
        print("\nPMP cost matrix Q is recomputed at runtime — nothing to fetch.")
        return 0

    if not src.exists():
        print(f"ERROR: reference year folder not found: {src}")
        return 1

    (dst / "supply").mkdir(parents=True, exist_ok=True)
    (dst / "market").mkdir(parents=True, exist_ok=True)

    coverage = {"year": args.year, "countries": args.countries, "files": []}

    print("Fetching crops (areas, yields) ...")
    crops = fetch_crops(args.year, args.countries)
    coverage["files"].append(write_areas(crops, dst / "supply"))
    coverage["files"].append(write_yields(crops, dst / "supply"))

    print("Fetching livestock ...")
    animals = fetch_livestock(args.year, args.countries)
    coverage["files"].append(write_animals(animals, dst / "supply"))

    print("Fetching producer prices ...")
    prices = fetch_producer_prices(args.year)
    coverage["files"].append(write_prices(prices, dst / "market"))

    print("Carrying structural files forward ...")
    copied = carry_forward(src, dst)
    coverage["carried_forward"] = copied

    (dst / "coverage_report.json").write_text(json.dumps(coverage, indent=2))

    print("\nCoverage:")
    for f in coverage["files"]:
        print("  ", f)
    print(f"  carried forward: {len(copied)} files")
    print(f"\nWritten to {dst}. Next:")
    print(f"  1. Inspect {dst}/coverage_report.json — check regions/activities are complete.")
    print(f"  2. Run:  CAPRIModel(data_dir='{args.data_dir}', base_year='{args.year}')")
    print( "  3. Check the base reproduces: the PMP calibrator recomputes Q automatically.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
