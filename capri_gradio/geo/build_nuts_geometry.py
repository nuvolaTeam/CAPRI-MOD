"""Builds capri_gradio/geo/nuts2024_level2.csv, the NUTS-2024 level-2 boundaries the GUI's maps draw on.

Source: Eurostat GISCO, NUTS 2024, regions, 1:20 million, EPSG:4326, level 2
  https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_20M_2024_4326_LEVL_2.geojson
  (c) EuroGeographics for the administrative boundaries (GISCO's copyright notice; shown on every map).
Kept as CSV (the project's rule for data files): one row per region, the GeoJSON geometry as text.
The model does not read it: the results are on CAPRI's regional units, linked to NUTS 2024 by
capri_data/codes/capri_units_nuts2024.csv (capri_mod/nuts_reporting.py).

Usage: python capri_gradio/geo/build_nuts_geometry.py [GEOJSON]   (downloads the file when none is given)
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

URL = "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_20M_2024_4326_LEVL_2.geojson"
OUT = Path(__file__).resolve().parent / "nuts2024_level2.csv"


def main():
    if len(sys.argv) > 1:
        doc = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    else:
        import requests
        r = requests.get(URL, timeout=120)
        r.raise_for_status()
        doc = r.json()
    rows = []
    for f in doc["features"]:
        p = f["properties"]
        if int(p.get("LEVL_CODE", -1)) != 2:
            continue
        rows.append({"nuts_id": p["NUTS_ID"], "country": p["CNTR_CODE"], "name": p.get("NAME_LATN") or p.get("NUTS_NAME"),
                     "geometry": json.dumps(f["geometry"], separators=(",", ":"))})
    rows.sort(key=lambda r: r["nuts_id"])
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["nuts_id", "country", "name", "geometry"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} regions -> {OUT}")


if __name__ == "__main__":
    main()
