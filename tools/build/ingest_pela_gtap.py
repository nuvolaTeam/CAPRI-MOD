"""
Ingest CAPRI's PELA elasticities and the GTAP Armington parameters.

PELA
----
`dat/estnlp/results.gdx`, symbol PELA, dimensioned region x crop x crop x year.
The third index is the crop whose price the response is measured against, so the
diagonal is own-price and the rest are genuine cross-price elasticities.

Two findings on inspection:

1. The model's existing supply_elasticities_regional.csv reproduces the 2005
   own-price slice EXACTLY -- 0.0% median deviation across 107 regions and 13
   crops. So that file was correctly derived; it was simply truncated. PELA
   covers 228 regions, more than double.

2. 480,473 of the 522,985 records are cross-price and entirely unused. The
   supply module currently derives its Q off-diagonals from a heuristic or from
   the group-level p_pmpQuadPact; these are the activity-level estimates.

Vintage: PELA runs 1986-2005 and stops twelve years before the base year. The
2005 slice is used because it is the most recent available and because it is
what the existing file already used. This is a real limitation, not a choice
worth hiding: supply elasticities are structural enough that a twelve-year gap
is defensible, but it should be stated.

GTAP
----
`dat/arm/GTP57_134.gdx` is the raw GTAP database. esubd is the Armington
elasticity between imports and domestic supply; esubm is the intra-import
elasticity, conventionally twice esubd. Sectors are GTAP codes, so a concordance
to CAPRI commodities is required and is declared explicitly below rather than
inferred.

Usage
-----
    python tools/build/ingest_pela_gtap.py --dump-dir /path/to/dumps
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
PELA_REC = re.compile(
    r"^'([A-Z]{2}[A-Z0-9]{6})'\.'([A-Z0-9]+)'\.'([A-Z0-9]+)'\.'(\d{4})'\s+([-\d.Ee+]+)")
GTAP_REC = re.compile(r"^'([a-z_]+)'\s+([-\d.Ee+]+)")

PELA_YEAR = "2005"

# GTAP sector -> CAPRI/model commodities. GTAP aggregates far more coarsely than
# CAPRI, so this is one-to-many and every mapping is a judgement that belongs in
# the open rather than inside a lookup.
GTAP_CONCORDANCE = {
    "wht": ["SWHE", "DWHE"],              # wheat
    "gro": ["BARL", "CORN", "OCER", "RYEM", "OATS"],   # other grains
    "pdr": ["PARI"],                       # paddy rice
    "osd": ["RAPE", "SUNF", "SOYA", "OOIL"],           # oil seeds
    "c_b": ["SUGB"],                       # cane and beet
    "v_f": ["POTA", "TOMA", "OVEG", "APPL", "OFRU", "CITR", "TAGR"],
    "pfb": ["TEXT"],                       # plant fibres
    "ocr": ["PULS", "OLIV", "TOBA"],       # other crops
    "ctl": ["BEEF"],                       # cattle
    "oap": ["PORK", "POUM", "SGMT"],       # other animal products
    "rmk": ["MILK"],                       # raw milk
    "mil": ["BUTR", "CHES", "SKIM"],       # dairy products
    "vol": ["RAPO", "SUNO", "SOYO"],       # vegetable oils
    "sgr": ["SUGA"],                       # sugar
}


def parse_pela(path: Path, year: str) -> pd.DataFrame:
    rows = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = PELA_REC.match(line)
            if m and m.group(4) == year:
                rows.append((m.group(1), m.group(2), m.group(3), float(m.group(5))))
    return pd.DataFrame(rows, columns=["region", "crop", "wrt", "value"])


def parse_gtap(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = GTAP_REC.match(line)
            if m:
                out[m.group(1)] = float(m.group(2))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", required=True, type=Path)
    ap.add_argument("--data-dir", type=Path, default=Path("capri_data"))
    args = ap.parse_args()

    out = args.data_dir / "sources" / "estnlp"
    out.mkdir(parents=True, exist_ok=True)

    # the model's regions are CAPRI's regional units (shared/regional_units.csv): each CAPRI code is its own region
    # (until 27 October 2026 mapped through shared/nuts_crosswalk.json, which left 21 regions unmatched)
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
    from _model_regions import UNITS
    rev = {u: u for u in UNITS}

    # ---- PELA ---------------------------------------------------------
    pela = parse_pela(args.dump_dir / "estnlp_PELA.txt", PELA_YEAR)
    pela["model_region"] = pela.region.map(rev)
    pela = pela.dropna(subset=["model_region"])
    pela["crop"] = pela.crop.replace({"MAIZ": "CORN"})
    pela["wrt"] = pela.wrt.replace({"MAIZ": "CORN"})

    own = pela[pela.crop == pela.wrt].pivot_table(
        index="model_region", columns="crop", values="value", aggfunc="mean")
    cross = pela[pela.crop != pela.wrt][
        ["model_region", "crop", "wrt", "value"]]

    own.to_csv(out / "pela_own_price.csv")
    # the supply module's form (SupplyModule.cross_price, used with the elasticity-based PMP terms): {region:
    # {"crop|wrt": elasticity}}; until 27 October 2026 this file had no builder in the repository
    byreg = {r: {f"{c}|{w}": float(v) for c, w, v in zip(g.crop, g.wrt, g.value)}
             for r, g in cross.groupby("model_region", sort=True)}
    (out / "pela_cross_by_region.json").write_text(json.dumps(byreg))

    print(f"PELA {PELA_YEAR}: {len(pela):,} records reaching "
          f"{pela.model_region.nunique()} model regions")
    print(f"  own-price   : {own.shape[0]} regions x {own.shape[1]} crops")
    print(f"  cross-price : {len(cross):,} records "
          f"({100*(cross.value < 0).mean():.0f}% negative, i.e. substitutes)")

    cur_path = args.data_dir / "2017/supply/supply_elasticities_regional.csv"
    if cur_path.exists():
        cur = _read_csv(cur_path, index_col=0)
        new_regions = [r for r in own.index if r not in cur.index]
        print(f"  regions gained over the current file: {len(new_regions)} "
              f"({cur.shape[0]} -> {own.shape[0]})")

    # ---- GTAP ---------------------------------------------------------
    esubd = parse_gtap(args.dump_dir / "gtap_esubd.txt")
    esubm = parse_gtap(args.dump_dir / "gtap_esubm.txt")
    rows = []
    for sector, commodities in GTAP_CONCORDANCE.items():
        if sector not in esubd:
            continue
        for c in commodities:
            rows.append({"commodity": c, "gtap_sector": sector,
                         "esubd": esubd[sector],
                         "esubm": esubm.get(sector, np.nan)})
    arm = pd.DataFrame(rows).set_index("commodity")
    arm.to_csv(args.data_dir / "sources" / "estnlp" / "gtap_armington.csv")
    print(f"\nGTAP: {len(esubd)} sectors, {len(arm)} model commodities mapped")


    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()
