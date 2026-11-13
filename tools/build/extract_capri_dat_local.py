"""CAPRI data files of capri_sources/dat_local, extracted to CSV (4 November 2026).

capri_sources/dat holds CAPRI's GDX files only, and not every one: these came from the project lead's
CAPRI installation (C:\\capri-star3.0\\dat\\...) and are kept in capri_sources/dat_local/ under the same paths
(docs/EXTERNAL_SOURCES.md). Every record as the file holds it; one CSV per symbol, named after CAPRI's symbol.

  dat/envind/lulucf_emissions_original_source.gms  PARAMETER p_PEATSH_def(rAll) "Share of peatland in arable land"
      (percent; Carre et al. 2009 via JRC; the Western Balkans take Croatia's, per the file's comment), read by
      envind/prep_lulucf_carbon.gms l. 258-259 as the organic-soil fallback of the Western Balkans and Turkey
      -> capri_data/sources/raw/capri/dat_local/envind/lulucf_emissions_original_source_p_PEATSH_def.parquet  (region, value)

dat/scen/ghgtech/holdingsLSU.gdx, also from the installation, is not extracted here: its p_holdLSU is already a model
input, capri_data/2017/abatement/ammonia/p_holdLSU.csv (build_ammonia_tech_inputs.py, from a dump), and the 9,597
records are identical (checked 4 November 2026).

(dat/policy/livestock_units.gms, p_LUUnits, also from the installation, was converted before by
convert_sources.py: capri_dat/policy/livestock_units_p_LUUnits.parquet, the same 18 records.)

    python tools/build/extract_capri_dat_local.py [capri_sources/dat_local]
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
import gams_text as G  # noqa: E402
from paths import SOURCES  # noqa: E402
from _sources_io import write_source_text  # noqa: E402  (capri_data/sources: Parquet)

OUT = ROOT / "capri_data" / "sources" / "raw" / "capri" / "dat_local"


def main(src: Path) -> None:
    txt = (src / "envind" / "lulucf_emissions_original_source.gms").read_text(encoding="latin-1")
    peat = G.parameter_records(txt, "p_PEATSH_def", 1)
    p1 = OUT / "envind" / "lulucf_emissions_original_source_p_PEATSH_def.parquet"
    p1.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["region", "value"])
    w.writerows(peat)
    write_source_text(buf.getvalue(), p1)                # the table of that CSV text, as Parquet
    print(f"{p1.relative_to(ROOT)}: {len(peat)} records")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else SOURCES / "dat_local")
