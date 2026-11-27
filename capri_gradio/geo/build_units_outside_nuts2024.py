"""Builds capri_gradio/geo/units_outside_nuts2024.csv, the boundaries of CAPRI's units that the NUTS-2024 table does
not link (capri_data/codes/capri_units_nuts2024.csv covers the EU's and Norway's units): the United Kingdom, the
Western Balkans and Turkey, one shape per unit, for the GUI's maps.

Source: Eurostat GISCO, NUTS regions, 1:20 million, EPSG:4326
  https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_20M_<YEAR>_4326_LEVL_<L>.geojson
  (c) EuroGeographics for the administrative boundaries (GISCO's copyright notice; shown on every map).

- the UK (not in NUTS 2024): its NUTS-1 regions in NUTS 2021, the last version with the UK; CAPRI's UKJ00000 holds
  London (UKI) and the South East (UKJ): CAPRI maps its NUTS-2 region UKI_J1 to UKJ00 and none to UKI00
  (capdis/sets/sets.gms l. 2640-2641), so the two shapes are joined;
- the Western Balkans, one unit per country (AL000000, BA000000, CS000000 Serbia, KO000000 Kosovo, MK000000,
  MO000000 Montenegro): the country, NUTS 2024 level 0;
- Turkey, one unit per NUTS-1 region (TR100000 ... TRC00000): NUTS 2024 level 1.

One shape per unit, so a unit's value is drawn on its own territory: no split by area weights (the NUTS-2024 table's
weights are Eurostat's UAA, which it has not for these countries' regions). Kept as CSV (the project's rule for data
files): one row per unit, the GeoJSON geometry as text. The model does not read it; the GUI does
(capri_gradio/results_data.py nuts_mapping, nuts_geometry).

Usage: python capri_gradio/geo/build_units_outside_nuts2024.py [DIR]
  DIR holding NUTS_RG_20M_2021_4326_LEVL_1.geojson, NUTS_RG_20M_2024_4326_LEVL_0.geojson and
  NUTS_RG_20M_2024_4326_LEVL_1.geojson (downloaded when no DIR is given; needs shapely)
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

URL = "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/"
OUT = Path(__file__).resolve().parent / "units_outside_nuts2024.csv"
#: CAPRI's unit -> (NUTS version, level, the NUTS codes it covers)
UNITS = {
    # the UK's NUTS-1 regions (capdis/sets/sets.gms l. 2625-2655: London's UKI_J1 goes to UKJ00)
    **{f"UK{c}00000": ("2021", 1, (f"UK{c}",)) for c in "CDEFGHKLMN"},
    "UKJ00000": ("2021", 1, ("UKI", "UKJ")),
    # the Western Balkans' countries
    "AL000000": ("2024", 0, ("AL",)), "BA000000": ("2024", 0, ("BA",)), "CS000000": ("2024", 0, ("RS",)),
    "KO000000": ("2024", 0, ("XK",)), "MK000000": ("2024", 0, ("MK",)), "MO000000": ("2024", 0, ("ME",)),
    # Turkey's NUTS-1 regions
    **{f"TR{c}00000": ("2024", 1, (f"TR{c}",)) for c in "123456789ABC"},
}


def _files(src):
    out = {}
    for ver, lev in sorted({(v, l) for v, l, _ in UNITS.values()}):
        name = f"NUTS_RG_20M_{ver}_4326_LEVL_{lev}.geojson"
        if src is not None:
            doc = json.loads((Path(src) / name).read_text(encoding="utf-8"))
        else:
            import requests
            r = requests.get(URL + name, timeout=120)
            r.raise_for_status()
            doc = r.json()
        out[(ver, lev)] = {f["properties"]["NUTS_ID"]: f for f in doc["features"]}
    return out


def main():
    from shapely.geometry import mapping, shape
    from shapely.ops import unary_union
    feats = _files(sys.argv[1] if len(sys.argv) > 1 else None)
    rows = []
    for unit, (ver, lev, codes) in sorted(UNITS.items()):
        fs = feats[(ver, lev)]
        missing = [c for c in codes if c not in fs]
        if missing:
            raise SystemExit(f"GISCO's NUTS {ver} level {lev} lacks {missing} ({unit})")
        geom = unary_union([shape(fs[c]["geometry"]) for c in codes])
        name = " and ".join((fs[c]["properties"].get("NAME_LATN") or fs[c]["properties"]["NUTS_NAME"]).strip()
                            for c in codes)
        rows.append({"nuts_id": codes[-1], "country": fs[codes[0]]["properties"]["CNTR_CODE"],
                     "name": name, "capri_unit": unit, "nuts_version": ver, "nuts_level": lev,
                     "nuts_codes": "+".join(codes), "geometry": json.dumps(mapping(geom), separators=(",", ":"))})
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["nuts_id", "country", "name", "capri_unit", "nuts_version", "nuts_level",
                                           "nuts_codes", "geometry"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} units -> {OUT}")


if __name__ == "__main__":
    main()
