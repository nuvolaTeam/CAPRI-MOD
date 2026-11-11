"""The inputs of CAPTRD's biofuel trends (biofuel/biofuel_trends.gms, included by captrd/expert_support.gms l. 108 with
%NewBiofuelModule% on), as CSV.

Sources (the project lead's CAPRI installation, docs/EXTERNAL_SOURCES.md):
  gams/biofuel/biofuel_trends.gms   its sets (AllUnit, auxCols, auxRows, pCols, pRows, aux_to_pCols, aux_to_pRows,
                                    pYears, allFermentaStocks, FstGFermentaStocks, fuelMatch, fuelMap, agFuels; read by
                                    tools/lib/gams_sets.py), scaleCols and primesMs (transcribed below with their lines)
                                    and the table p_potentialStocks
  gams/captrd.gms                   PARAMETER Proc_Yields (l. 356-363)
  dat/biofuel/primes_ref_060722.gdx p_PrimesWithUnits (the reference run's %primesBiofuelFile%), converted to Parquet by
                                    tools/build/convert_capri_gdx.py (dat_parquet/biofuel/primes_ref_060722)
  dat/biofuel/fossilFuel.gdx        p_fossilFuel (dat_parquet/biofuel/fossilFuel)
  dat/biofuel/Biofuel_data.gms      the table p_taxData (the file's only table biofuel_trends.gms reads)
Output: capri_data/pipeline/captrd/sets/biofuel/<set>.csv (d0, d1, ...), capri_data/pipeline/captrd/dat/
biofuel_p_potentialstocks.csv, biofuel_proc_yields.csv, biofuel_p_primeswithunits.csv, biofuel_p_fossilfuel.csv,
biofuel_p_taxdata.csv. Records are kept as the sources hold them (labels as written); the port filters them to the
domains GAMS loads them over (execute_load drops records outside a domain).

    python tools/build/build_captrd_biofuel.py
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
import gams_sets as G                                      # noqa: E402
import gams_text as GT                                     # noqa: E402
from paths import SOURCES                                  # noqa: E402

GAMS = SOURCES / "course_capri_git" / "gams"
DAT = SOURCES / "course_capri_git" / "dat" / "biofuel"
PARQ = SOURCES / "dat_parquet" / "biofuel"
OUT_SETS = ROOT / "capri_data" / "pipeline" / "captrd" / "sets" / "biofuel"
OUT_DAT = ROOT / "capri_data" / "pipeline" / "captrd" / "dat"
SETS = ["AllUnit", "auxCols", "auxRows", "pCols", "pRows", "aux_to_pCols", "aux_to_pRows", "pYears", "allFermentaStocks",
        "FstGFermentaStocks", "fuelMatch", "fuelMap", "agFuels"]
#: transcribed: biofuel_trends.gms l. 456-457 (its quoted text stops the set reader) and l. 201-202 (SET.MSALL: CAPRI's
#: MSALL, capri_data/pipeline/captrd/sets/msall.csv, is added by the port)
TRANSCRIBED = {"scaleCols": ["secG", "mapr", "domm", "ntrd", "hcom", "biof"], "primesMs_extra": ["BE000000", "LU000000"]}


def _write(path: Path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
    print(f"{path.relative_to(ROOT)}: {len(rows)} records")


def main() -> None:
    import pandas as pd
    src = GAMS / "biofuel" / "biofuel_trends.gms"
    gs = G.read(src, GAMS, {"Aglink": "aglink2023dgAgri"})
    for n in SETS:
        m = gs.get(n)
        _write(OUT_SETS / f"{n.lower()}.csv", [f"d{i}" for i in range(len(m[0]))], m)
    text = GT.read_text(src)
    for n, members in TRANSCRIBED.items():
        _write(OUT_SETS / f"{n.lower()}.csv", ["d0"], [(x,) for x in members])
    recs = GT.table_records(text, "p_potentialStocks", 1, str(src))
    _write(OUT_DAT / "biofuel_p_potentialstocks.csv", ["region", "stock", "value"],
           [(r, c, repr(float(v))) for r, c, v in recs])
    ct = GT.read_text(GAMS / "captrd.gms")
    m = re.search(r"PARAMETER\s+Proc_Yields\s*\(rows\)\s*\"[^\"]*\"\s*/(.*?)/", ct, flags=re.I | re.S)
    py = [(a.upper(), repr(float(b))) for a, b in re.findall(r"(\w+)\s+([0-9.]+)", m.group(1))]
    _write(OUT_DAT / "biofuel_proc_yields.csv", ["row", "value"], py)
    for sym, folder, name, cols in (("p_PrimesWithUnits", "primes_ref_060722", "biofuel_p_primeswithunits",
                                     ["region", "col", "row", "unit", "year"]),
                                    ("p_fossilFuel", "fossilFuel", "biofuel_p_fossilfuel", ["region", "col", "row", "year"])):
        d = pd.read_parquet(PARQ / folder / f"{sym}.parquet")
        if d["special"].fillna("").ne("").any():
            raise ValueError(f"{sym}: special values")
        _write(OUT_DAT / f"{name}.csv", cols + ["value"],
               [(*k, repr(float(v))) for *k, v in zip(*[d[f"d{i + 1}"] for i in range(len(cols))], d.value)])
    bt = GT.read_text(DAT / "Biofuel_data.gms")
    recs = GT.table_records(bt, "p_taxData", 3, str(DAT / "Biofuel_data.gms"))
    _write(OUT_DAT / "biofuel_p_taxdata.csv", ["region", "fuel", "item", "year", "value"],
           [(*k, repr(float(v))) for *k, v in recs])


if __name__ == "__main__":
    main()
