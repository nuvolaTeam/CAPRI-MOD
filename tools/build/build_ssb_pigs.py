"""Statistics Norway's pig census by county, 1 January 2017, for Norway's pig split (KNOWN_ISSUES K56).

Source: capri_data/sources/ssb/ssb_husdyr_fylke_2017_original.csv - SSB's table "Talet pa ymse husdyr per 1. januar,
etter fylke" (Statistikkbanken tables 03710 / 03791) as downloaded by the project lead, unchanged (semicolon separated,
UTF-8 with BOM): the national series 2007-2017, then the 2017 county rows; columns Mjolkegeit, Alssvin (breeding pigs),
Slaktesvin (fattening pigs: slaughtered or sold live in the previous year), Verpehoner, Slaktekylling.

Output: capri_data/sources/ssb/ssb_pigs_county_2017.csv - county, its NUTS 2016 region, breeding and fattening pigs.
Checked: the county sums equal SSB's national 2017 row (89,138 breeding pigs, 1,607,644 fattening pigs).

    python tools/build/build_ssb_pigs.py
"""
from __future__ import annotations
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "capri_data" / "sources" / "ssb"
#: old counties (until 2019) to NUTS 2016 regions
NUTS2016 = {"Østfold": "NO03", "Akershus og Oslo": "NO01", "Hedmark": "NO02", "Oppland": "NO02", "Buskerud": "NO03",
            "Vestfold": "NO03", "Telemark": "NO03", "Aust-Agder": "NO04", "Vest-Agder": "NO04", "Rogaland": "NO04",
            "Hordaland": "NO05", "Sogn og Fjordane": "NO05", "Møre og Romsdal": "NO05", "Sør-Trøndelag": "NO06",
            "Nord-Trøndelag": "NO06", "Nordland": "NO07", "Troms - Romsa": "NO07", "Finnmark - Finnmárku": "NO07"}


def main() -> None:
    rows = [l.split(";") for l in (D / "ssb_husdyr_fylke_2017_original.csv").read_text(encoding="utf-8-sig").splitlines()]
    head = rows[0]
    ia, isl = head.index("Alssvin"), head.index("Slaktesvin")
    nat = next(r for r in rows if r and r[0] == "2017")                    # first 2017 row: the national series
    start = max(i for i, r in enumerate(rows) if r and r[0] == "2017")     # last 2017 row: the counties' header
    cty = [r for r in rows[start + 1:] if r and r[0].strip()]
    out = [(r[0].strip(), NUTS2016[r[0].strip()], int(r[ia]), int(r[isl])) for r in cty]
    assert len(out) == len(NUTS2016)
    assert sum(o[2] for o in out) == int(nat[ia]) and sum(o[3] for o in out) == int(nat[isl]), "county sums"
    with open(D / "ssb_pigs_county_2017.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["county", "nuts2016", "breeding_pigs_alssvin", "fattening_pigs_slaktesvin"])
        w.writerows(out)
    print(f"wrote ssb_pigs_county_2017.csv: {len(out)} counties; sums {sum(o[2] for o in out)}, "
          f"{sum(o[3] for o in out)} = SSB's national 2017 row")


if __name__ == "__main__":
    main()
