"""CAPRI's land market data as CSV (land_market_<year>.csv and land_market_<year>_regions.csv).

land_market_<year>.csv, one row per value:
    region, row, col, value
    row "base_kha": the region's land-type level (1000 ha) of land type col;
    row a land type: CAPRI's p_pmpQuadLandTypes(row, col) for the region (per ha).
land_market_<year>_regions.csv: region, quad_source, share_of_source, min_eigenvalue.

read() returns {region: {"base_kha": {lt: v}, "quad": [[...]], "quad_source", "min_eigenvalue"[, "share_of_source"]}},
the structure the supply models use; the land types in the order of the file (ARAC, GRAS, FRUN, FORE, OLND, ARTIF).
"""
from __future__ import annotations

import csv
from pathlib import Path


def read(stem: Path):
    """stem: .../land_market_<year> (without extension). None if the file is missing."""
    f = Path(str(stem) + ".csv")
    if not f.exists():
        return None
    base, quad, order = {}, {}, []
    with open(f, newline="") as h:
        for r in csv.DictReader(h):
            reg, row, col, v = r["region"], r["row"], r["col"], float(r["value"])
            if row == "base_kha":
                base.setdefault(reg, {})[col] = v
                if col not in order:
                    order.append(col)
            else:
                quad.setdefault(reg, {})[(row, col)] = v
    meta = {}
    fm = Path(str(stem) + "_regions.csv")
    if fm.exists():
        with open(fm, newline="") as h:
            for r in csv.DictReader(h):
                m = {"quad_source": r["quad_source"], "min_eigenvalue": float(r["min_eigenvalue"])}
                if r.get("share_of_source"):
                    m["share_of_source"] = float(r["share_of_source"])
                meta[r["region"]] = m
    out = {}
    for reg in base:
        q = quad.get(reg, {})
        out[reg] = {"base_kha": base[reg], "quad": [[q.get((a, b), 0.0) for b in order] for a in order], **meta.get(reg, {})}
    return out


def write(stem: Path, regions: dict, land_types) -> None:
    """Write the two CSV files from {region: {...}} (the structure read() returns)."""
    with open(str(stem) + ".csv", "w", newline="") as h:
        w = csv.writer(h)
        w.writerow(["region", "row", "col", "value"])
        for reg, d in regions.items():
            for t in land_types:
                w.writerow([reg, "base_kha", t, repr(float(d["base_kha"].get(t, 0.0)))])
            for i, a in enumerate(land_types):
                for j, b in enumerate(land_types):
                    w.writerow([reg, a, b, repr(float(d["quad"][i][j]))])
    with open(str(stem) + "_regions.csv", "w", newline="") as h:
        w = csv.writer(h)
        w.writerow(["region", "quad_source", "share_of_source", "min_eigenvalue"])
        for reg, d in regions.items():
            sh = d.get("share_of_source")
            w.writerow([reg, d.get("quad_source", ""), "" if sh is None else repr(float(sh)),
                        repr(float(d.get("min_eigenvalue", float("nan"))))])
