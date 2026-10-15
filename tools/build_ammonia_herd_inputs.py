"""Herd inputs of CAPRI's ammonia cost model, to CSV.

- heads by farm-size class (CAPRI dat/scen/ghgtech/AD_basedata p_Heads, from the scen export)
- manure N per animal (MANN), days per production cycle (DAYS) and activity level (LEVL,
  used to weight CAPRI's activities into the model's animal categories), per CAPRI region and
  animal activity, from CAPRI's 2030 reference results (gd_full) - ammo_tech.gms uses them
  (data(rs,maact,"mann"/"days","y")) to turn manure into storage volume.

Usage: python tools/build_ammonia_herd_inputs.py <scen.zip> <gd_full.zip>
"""
import csv, gzip, io, sys, zipfile
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "capri_data" / "2017" / "abatement" / "ammonia"
ANIMALS = {b"DCOL", b"DCOH", b"DCOW", b"BULL", b"BULH", b"BULF", b"HEIL", b"HEIH", b"HEIF", b"HEIR", b"SCOW",
           b"CAMF", b"CAFF", b"CAMR", b"CAFR", b"PIGF", b"SOWS", b"HENS", b"POUF", b"SHGM", b"SHGF"}


def heads(scen_zip):
    z = zipfile.ZipFile(scen_zip)
    raw = z.read("scen/ghgtech/AD_basedata/p_Heads.csv.gz")
    rows = list(csv.reader(io.StringIO(gzip.decompress(raw).decode("utf-8"))))
    with open(OUT / "p_Heads.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["region", "ad_activity", "size_class", "value"])
        for r in rows[1:]:
            w.writerow(r)
    return len(rows) - 1


def mann_days(gd_zip, year=b"2030"):
    z = zipfile.ZipFile(gd_zip); n = 0
    with z.open("gd_full.txt") as f, open(OUT / "capri_mann_days_2030.csv", "w", newline="") as g:
        w = csv.writer(g); w.writerow(["region", "activity", "item", "value"])
        for raw in f:
            if b"'MANN'" not in raw and b"'DAYS'" not in raw and b"'LEVL'" not in raw:
                continue
            p = raw.split(b"'.'")
            if len(p) < 5 or p[2] not in ANIMALS or not p[4].startswith(year):
                continue
            reg = p[0].lstrip(b"'").decode(); val = raw.rsplit(None, 1)[-1].rstrip(b",")
            w.writerow([reg, p[2].decode(), p[3].decode(), float(val)]); n += 1
    return n


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    print("p_Heads rows:", heads(sys.argv[1]))
    print("MANN/DAYS rows:", mann_days(sys.argv[2]))
