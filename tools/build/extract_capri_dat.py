"""Symbols of CAPRI's dat folder (capri_sources/dat, its GDX files as Parquet, one file per symbol), extracted to CSV with
every record (4 November 2026).

  dat/envind/fao_peatland.gdx  P(FAOregions) "Share of peatland in arable land" (FAO), read by envind/lulucf_carbon_decl.gms
      l. 695-697 as p_PEATSH: the organic-soil fallback of the Western Balkans and Turkey (prep_lulucf_carbon.gms l. 255-256)
      -> capri_data/sources/raw/capri/dat/envind/fao_peatland/fao_peatland_P.parquet  (fao_code, value)
  dat/miterra/mirror_non_changeable_parameters_norway.gdx, mirror_miterra_inputs_norway.gdx  p_NO_<symbol>: CAPRI's
      Norwegian MITERRA data, copied to NO000000 by envind/ammo.gms l. 252-343 (the 13 symbols whose targets the model
      reads) -> capri_data/sources/raw/capri/dat/miterra/<gdx>/<gdx>_p_NO_<symbol>.csv. Since 25 November 2026 from the
      project lead's installation, the version of CAPRI's 2030 Green Deal reference run (capri_sources/dat_local/
      miterra, as Parquet in capri_sources/dat_parquet/miterra by tools/build/convert_capri_gdx.py); until then from
      the dat mirror, whose p_NO_ControlStrategies differed in four records: the hens' and other poultry's
      low-emission housing shares (SA) of 2000 swapped (54 and 85 against 85 and 54) and none for 2020 (54 and 85).

    python tools/build/extract_capri_dat.py [capri_sources/dat] [--only=PREFIX]
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from paths import SOURCES  # noqa: E402
from _sources_io import write_source_text  # noqa: E402  (capri_data/sources: Parquet)

OUT = ROOT / "capri_data" / "sources" / "raw" / "capri" / "dat"
#: (Parquet file under dat, output file name, the output's columns); the output in sources/raw/capri/dat/<the Parquet
#: file's folder> (DATA_LAYOUT.md: the path mirrors the origin)
_NC, _MI = "miterra/mirror_non_changeable_parameters_norway", "miterra/mirror_miterra_inputs_norway"
SYMBOLS = (("envind/fao_peatland/P.parquet", "envind/fao_peatland_P.parquet", ["fao_code", "value"]),
           # CAPRI's mirrored MITERRA data of Norway (envind/ammo.gms l. 163-176, 252-343): the symbols whose targets the
           # model reads (tools/build/build_ammonia_tech_inputs.py READ), columns as those targets' without the region
           *((f"{d}/p_NO_{s}.parquet", f"{d}_p_NO_{s}.parquet", cols + ["value"]) for d, s, cols in (
               (_NC, "RCEmissions", ["animal_mitt", "item"]),
               (_NC, "ControlStrategies", ["animal_mitt", "strategy", "item"]),
               (_NC, "ReducControlStrategies", ["animal_mitt", "strategy", "item"]),
               (_NC, "FracEmGrazing", ["animal_mitt", "item"]),
               (_MI, "ReducEmhouse", ["animal_mitt", "gas", "tech_class"]),
               (_MI, "ReducEmstorage", ["animal_mitt", "gas", "tech_class"]),
               (_MI, "FracEmHouse", ["animal_mitt", "gas"]),
               (_MI, "FracEmStorage", ["animal_mitt", "gas"]),
               (_MI, "FracEmAppl", ["animal_mitt", "gas"]),
               (_MI, "EmFracFert", ["gas", "fertiliser"]),
               (_MI, "FracUseFert", ["fertiliser"]),
               (_MI, "NN_CorrFertFactDeviation", ["fertiliser", "year"]),
               (_MI, "bNumAniRains", ["animal_mitt", "year"]))))


#: the symbols read from the project lead's installation (capri_sources/dat_parquet: convert_capri_gdx.py's layout,
#: d1..dN, value, special) instead of the dat mirror
FROM_INSTALLATION = ("miterra/",)


def _read(src: Path, rel: str) -> pd.DataFrame:
    """The symbol's records, its index columns then "value"; from dat_parquet for FROM_INSTALLATION (its special values
    refused: none in these files)."""
    if not rel.startswith(FROM_INSTALLATION):
        return pd.read_parquet(src / rel)
    df = pd.read_parquet(src.parent / "dat_parquet" / rel)
    if "special" in df.columns:
        if (df["special"].astype(str) != "").any():
            raise ValueError(f"{rel}: special values {sorted(set(df['special']))}")
        df = df.drop(columns="special")
    return df


def main(src: Path, only: str | None = None) -> None:
    for rel, out, cols in SYMBOLS:
        if only and not rel.startswith(only):
            continue
        df = _read(src, rel)
        dims, val = list(df.columns[:-1]), df.columns[-1]
        if len(dims) != len(cols) - 1 or val != "value":  # noqa: SIM102
            raise ValueError(f"{rel}: columns {list(df.columns)}, expected {len(cols) - 1} dimensions and 'value'")
        dest = OUT / Path(rel).parent / Path(out).name
        dest.parent.mkdir(parents=True, exist_ok=True)
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(cols)
        w.writerows([*(str(r[d]) for d in dims), repr(float(r[val]))] for r in df.to_dict("records"))
        write_source_text(buf.getvalue(), dest)          # the table of that CSV text, as Parquet
        print(f"{dest.relative_to(ROOT)}: {len(df)} records")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--only")]
    only = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--only=")), None)
    main(Path(args[0]) if args else SOURCES / "dat", only)
