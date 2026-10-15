"""CAPRI's calibrated supply elasticities of young animals per member state.

Source: results/arm/supply_elas_2_1720<MS>defaulta.gdx (p_ElasSupp(MS, item, item, "CAL")), dumped
to text (uploads supply_elas_2_1720{DE,ES,FR,IT,PL}defaulta.txt and the zip of the remaining
countries). The base-year file elas_2_1717 carries the dummy value 1 for young animals (CAPRI
deletes it in supply/calibrate_supply.gms), so the calibrated 2020 values are used (REGISTERED).

Output: capri_data/sources/arm/capri_supply_elas_young_1720.csv (region, item, value) for YCAM,
YCAF, YBUL, YHEI, YCOW, YPIG.
Usage: python tools/build_young_animal_elasticities.py <dump files ...>
"""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "capri_data" / "sources" / "arm" / "capri_supply_elas_young_1720.csv"
PAT = re.compile(r"'([^']+)'\.'([^']+)'\.'([^']+)'\.'CAL'\s+([-0-9.eE+]+)")
ITEMS = {"YCAM", "YCAF", "YBUL", "YHEI", "YCOW", "YPIG"}


def main(files):
    rows = {}
    for f in files:
        for line in open(f, encoding="latin-1"):
            m = PAT.match(line)
            if m and m.group(2) == m.group(3) and m.group(2) in ITEMS and m.group(1).endswith("000000"):
                rows[(m.group(1), m.group(2))] = float(m.group(4))
    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["region", "item", "value"])
        for (r, i), v in sorted(rows.items()):
            w.writerow([r, i, v])
    print(len(rows), "values,", len({r for r, _ in rows}), "member states ->", OUT.name)


if __name__ == "__main__":
    main(sys.argv[1:])
