"""CAPRI's regional N balance of its Green Deal 2030 run with endogenous technologies ('ini'), from the run's results.

Data written
  capri_data/sources/capri_res/gd2030_endotech_ini_nbalance.csv  region, item, value: CAPRI's regional N balance
      items of the run (dataOut '' . item . NITF . 2030, 1000 t N): MINFER GASMIN RUNMIN NH3MIN EXPPRD IMPORT ATMOSD
      CRESID BIOFIX EXCRET GASANI RUNANI MTRADE SURSOI LEACHI; UAAR LEVL (1000 ha) and UAAR N2OLEA (kg N2O per ha)

Read by tools/build/build_regional_units.py (CAPRI's units of the run) and tools/build/build_n_leaching.py (the leaching
share). Until 29 October 2026 build_n_leaching.py wrote this file too, which made the unit list depend on the ammonia
chain that depends on the unit list (a cycle; docs/design/DATA_PIPELINE_DOIT.md); one extractor per source file.

    python tools/build/extract_gd2030_nbalance.py [res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv]
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "capri_data" / "sources" / "capri_res" / "gd2030_endotech_ini_nbalance.csv"
ITEMS = ("MINFER", "GASMIN", "RUNMIN", "NH3MIN", "EXPPRD", "IMPORT", "ATMOSD", "CRESID", "BIOFIX", "EXCRET", "GASANI",
         "RUNANI", "MTRADE", "SURSOI", "LEACHI")
DUMP = "/mnt/user-data/uploads/res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv"


def extract(dump):
    """The run's regional N balance items -> OUT."""
    pat = re.compile(r"'([A-Z]{2}[0-9A-Z]{6})'\.''\.'([^']+)'\.'([^']+)'\.'2030'\s+([-0-9.eE+]+)")
    rows = []
    with open(dump) as fh:
        for line in fh:
            m = pat.match(line)
            if not m:
                continue
            reg, col, row, v = m.groups()
            if (row == "NITF" and col in ITEMS) or (col == "UAAR" and row in ("LEVL", "N2OLEA")):
                item = col if row == "NITF" else f"UAAR_{row}"
                rows.append([reg, item, float(v)])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["region", "item", "value"])
        w.writerows(rows)
    return rows


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else DUMP
    print(len(extract(src)), "records ->", OUT)
