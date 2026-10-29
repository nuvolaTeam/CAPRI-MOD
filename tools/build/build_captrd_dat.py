"""CAPRI's data include files that CAPTRD reads, as CSV for CAPTRD-MOD.

Sources (CAPRI star 3.0 dat folder, from the project lead's installation, kept unchanged in
capri_data/sources/capri_dat/):
  policy/livestock_units.gms             p_LUUnits(act)              livestock units per head (prep_data_for_estimation
                                                                     .gms l. 160-162, the stocking density LU)
  biofuel/biofuel_technology_params.gms  p_ExtrRates(fuel, stock)    biofuel per ton of feedstock (load_coco1_data.gms
                                                                     l. 524-537, the default biostocks)
                                         p_ByProduct(byprod, stock)  by-product per ton of feedstock (l. 545-548, DDGS)
CAPTRD includes the first from policy/rd_static.gms or the policy sets, the second at captrd.gms l. 340-341
(%NewBiofuelModule% = ON).

GAMS labels are case-insensitive: they are written in upper case ("BioE" is BIOE).

Output: capri_data/pipeline/captrd/dat/{p_luunits, p_extrrates, p_byproduct}.csv

    python tools/build/build_captrd_dat.py
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "capri_data" / "sources" / "capri_dat"
OUT = ROOT / "capri_data" / "pipeline" / "captrd" / "dat"


def parameter_list(path: Path, name: str, dim: int):
    """The records of `parameter name(...) "text" / k1.k2 value ... /;` (comment lines starting with * skipped)."""
    text = path.read_text(encoding="ascii")
    m = re.search(rf"parameter\s+{name}\s*\([^)]*\)[^/]*/(.*?)/\s*;", text, flags=re.I | re.S)
    if not m:
        raise KeyError(f"{name} not in {path}")
    out = []
    for ln in m.group(1).splitlines():
        if not ln.strip() or ln.lstrip().startswith("*"):
            continue
        s = re.sub(r"\s*\.\s*", ".", ln.strip())           # "BioD .RAPO" -> "BioD.RAPO"
        parts = s.split()
        if len(parts) != 2:
            raise ValueError(f"{path}: {name}: unreadable line {ln!r}")
        keys = parts[0].upper().split(".")
        if len(keys) != dim:
            raise ValueError(f"{path}: {name}: {dim} keys expected in {ln!r}")
        out.append((*keys, float(parts[1])))
    if len({r[:-1] for r in out}) != len(out):
        raise ValueError(f"{path}: {name}: duplicate keys")
    return out


def _write(name, header, rows):
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / f"{name}.csv", "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        for r in rows:
            w.writerow((*r[:-1], repr(r[-1])))
    print(f"{name}.csv: {len(rows)} records")


def main() -> None:
    _write("p_luunits", ["act", "value"], parameter_list(SRC / "policy" / "livestock_units.gms", "p_LUUnits", 1))
    bio = SRC / "biofuel" / "biofuel_technology_params.gms"
    _write("p_extrrates", ["fuel", "stock", "value"], parameter_list(bio, "p_ExtrRates", 2))
    _write("p_byproduct", ["byproduct", "stock", "value"], parameter_list(bio, "p_ByProduct", 2))


if __name__ == "__main__":
    main()
