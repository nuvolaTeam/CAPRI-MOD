"""Builds capri_gradio/geo/uk_nuts2021_level1.csv, the boundaries of CAPRI's UK units for the GUI's maps.

The United Kingdom is not in NUTS 2024 (capri_gradio/geo/nuts2024_level2.csv, capri_data/codes/capri_units_nuts2024.csv),
so its units had no shape on the maps. CAPRI's UK units are NUTS-1 regions (UKC00000 ... UKN00000), drawn here on the
last NUTS version with the UK:

Source: Eurostat GISCO, NUTS 2021, regions, 1:20 million, EPSG:4326, level 1
  https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_20M_2021_4326_LEVL_1.geojson
  (c) EuroGeographics for the administrative boundaries (GISCO's copyright notice; shown on every map).

One unit per NUTS-1 region, except CAPRI's UKJ00000, which holds London (UKI) and the South East (UKJ): CAPRI maps its
NUTS-2 region UKI_J1 to UKJ00 and none to UKI00 (capdis/sets/sets.gms l. 2640-2641), so the two shapes are joined.
Kept as CSV (the project's rule for data files): one row per unit, the GeoJSON geometry as text. The model does not
read it; the GUI does (results_data.nuts_geometry, nuts_mapping).

Usage: python capri_gradio/geo/build_uk_geometry.py [GEOJSON]   (downloads the file when none is given; needs shapely)
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

URL = "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_20M_2021_4326_LEVL_1.geojson"
OUT = Path(__file__).resolve().parent / "uk_nuts2021_level1.csv"
#: CAPRI's unit of each UK NUTS-1 region (capdis/sets/sets.gms l. 2625-2655: London's UKI_J1 goes to UKJ00)
UNIT = {"UKC": "UKC00000", "UKD": "UKD00000", "UKE": "UKE00000", "UKF": "UKF00000", "UKG": "UKG00000",
        "UKH": "UKH00000", "UKI": "UKJ00000", "UKJ": "UKJ00000", "UKK": "UKK00000", "UKL": "UKL00000",
        "UKM": "UKM00000", "UKN": "UKN00000"}


def main():
    from shapely.geometry import mapping, shape
    from shapely.ops import unary_union
    if len(sys.argv) > 1:
        doc = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    else:
        import requests
        r = requests.get(URL, timeout=120)
        r.raise_for_status()
        doc = r.json()
    feats = {f["properties"]["NUTS_ID"]: f for f in doc["features"]
             if f["properties"]["CNTR_CODE"] == "UK" and int(f["properties"].get("LEVL_CODE", -1)) == 1}
    missing = sorted(set(UNIT) - set(feats))
    if missing:
        raise SystemExit(f"GISCO's file lacks the UK regions {missing}")
    rows = []
    for unit in sorted(set(UNIT.values())):
        codes = sorted(c for c, u in UNIT.items() if u == unit)
        geom = unary_union([shape(feats[c]["geometry"]) for c in codes])
        nuts_id = unit[:3]
        name = " and ".join(feats[c]["properties"].get("NAME_LATN") or feats[c]["properties"]["NUTS_NAME"]
                            for c in codes)
        rows.append({"nuts_id": nuts_id, "country": "UK", "name": name, "capri_unit": unit,
                     "nuts_codes": "+".join(codes),
                     "geometry": json.dumps(mapping(geom), separators=(",", ":"))})
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["nuts_id", "country", "name", "capri_unit", "nuts_codes", "geometry"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} units -> {OUT}")


if __name__ == "__main__":
    main()
