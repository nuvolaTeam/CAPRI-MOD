"""CAPRI data files the Hugging Face mirror of CAPRI's dat folder does not hold, extracted to CSV (4 November 2026).

The mirror (capri_sources/dat) converts CAPRI's GDX files only, and not every one: these came from the project lead's
CAPRI installation (C:\\capri-star3.0\\dat\\...) and are kept in capri_sources/dat_local/ under the same paths
(docs/EXTERNAL_SOURCES.md). Every record as the file holds it; one CSV per symbol, named after CAPRI's symbol.

  dat/envind/lulucf_emissions_original_source.gms  PARAMETER p_PEATSH_def(rAll) "Share of peatland in arable land"
      (percent; Carre et al. 2009 via JRC; the Western Balkans take Croatia's, per the file's comment), read by
      envind/prep_lulucf_carbon.gms l. 258-259 as the organic-soil fallback of the Western Balkans and Turkey
      -> capri_data/sources/capri_dat/envind/lulucf_emissions_original_source_p_PEATSH_def.csv  (region, value)
  dat/scen/ghgtech/holdingsLSU.gdx                 p_holdLSU(rall, ad_activity, fsclass) holdings per livestock-unit
      size class, read by envind/prep_farm_size_data_for_miti.gms l. 129
      -> capri_data/sources/capri_dat/ghgtech/holdingsLSU_p_holdLSU.csv  (region, activity, fsclass, value)

(dat/policy/livestock_units.gms, p_LUUnits, also from the installation, was converted before by
convert_sources_to_csv.py: capri_dat/policy/livestock_units_p_LUUnits.csv, the same 18 records.)

    python tools/build/extract_capri_dat_local.py [capri_sources/dat_local]
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
import gams_text as G  # noqa: E402
from _gdx import read_symbol  # noqa: E402
from paths import SOURCES  # noqa: E402

OUT = ROOT / "capri_data" / "sources" / "capri_dat"


def main(src: Path) -> None:
    txt = (src / "envind" / "lulucf_emissions_original_source.gms").read_text(encoding="latin-1")
    peat = G.parameter_records(txt, "p_PEATSH_def", 1)
    p1 = OUT / "envind" / "lulucf_emissions_original_source_p_PEATSH_def.csv"
    p1.parent.mkdir(parents=True, exist_ok=True)
    with open(p1, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["region", "value"])
        w.writerows(peat)
    hold = read_symbol(src / "scen" / "ghgtech" / "holdingsLSU.gdx", "p_holdLSU")
    p2 = OUT / "ghgtech" / "holdingsLSU_p_holdLSU.csv"
    p2.parent.mkdir(parents=True, exist_ok=True)
    with open(p2, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["region", "activity", "fsclass", "value"])
        w.writerows((r, a, c, repr(float(v))) for r, a, c, v in hold)
    print(f"{p1.relative_to(ROOT)}: {len(peat)} records; {p2.relative_to(ROOT)}: {len(hold)} records")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else SOURCES / "dat_local")
