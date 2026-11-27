"""CAPRI's new energy crops (NECR) at the simulation year, per regional unit: their level and output (register DEP-9,
KNOWN_ISSUES K138).

NECR is one of CAPRI's fixed crop activities (MFCACT, sets.gms l. 131-143; held at its level, supply/prep_sim.gms
l. 250 v_actLevl.FX for FACT). CAPREG has no level of it in the base year in any country: its level and output appear
at the simulation year only, from CAPRI's trend projection (capmod/load_base_data_and_trends.gms l. 337-338: "It seems
as if NECR.OCRO yields and NECR.LEVL are invented in CAPTRD"; CAPTRD's expert support, biofuel_trends: a level where
PRIMES has lignocellulosic crops, a revenue of 250 per ha). Its one output is OCRO (PACT_TO_O NECR.(OCRO, MANN, MANP,
MANK), sets.gms l. 5221; PACT_TO_Y NECR.OCRO, l. 5411), measured in constant prices as OCRO is (l. 136-137); its
inputs (PACT_TO_I NECR.(NITF, ..., INPO), l. 5326) carry no data at the simulation year.

Source: sim_ini_21730's DATA (CAPRI's simulation start of 2030, the reference export, tools/build/
build_simini_reference.py): DATA(RU, "NECR", "LEVL" | "OCRO", "Y"). The extract is kept (capri_data/sources/raw/capri/
results/sim_ini_21730/necr_items.parquet, every NECR column at "Y" of the regional units) for a build without the
reference export. The builder stops if NECR has any other column at "Y" than its level, its output and the level's
split by use (LEVL_1, the area for fuel bioenergy, LEVL_2 the rest: biofuel/resids.gms through
capmod/load_base_data_and_trends.gms; capri_mod/projection/equations/year_data/residues.py DATA_NECR_LEVL_1_2).

Output
  capri_data/baselines/capri_greendeal_ref/1730/supply/necr_2030.csv    region, levl_kha, yield
      levl_kha: DATA(RU, "NECR", "LEVL", "Y"), 1000 ha; yield: DATA(RU, "NECR", "OCRO", "Y") / 1000, the unit of
      the model's yields of the value-measured crops (capri_data/2017/supply/yields.csv OCRO: CAPRI's YILD / 1000)

    python tools/build/build_necr_2030.py [--year 2030]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
sys.path.insert(0, str(ROOT))
from paths import REFERENCE  # noqa: E402  (CAPRI's material outside the repository)
from _sources_io import read_source, write_source  # noqa: E402  (capri_data/sources: Parquet)

#: the columns of NECR at the simulation year: its level, its output, the level's split by use
EXPECTED = {"LEVL", "OCRO", "LEVL_1", "LEVL_2"}


def items(year: int) -> pd.DataFrame:
    """sim_ini's DATA(RU, "NECR", column, "Y") of the regional units (region, col, value), written to the kept extract
    where the reference export is at hand, read from it otherwise."""
    simini = REFERENCE / "simini" / f"simini_2{year % 100 + 1700}" / "DATA.csv.gz"
    extract = ROOT / "capri_data" / "sources" / "raw" / "capri" / "results" / f"sim_ini_2{year % 100 + 1700}" / \
        "necr_items.parquet"
    units = set(pd.read_csv(ROOT / "capri_data" / "codes" / "regional_units.csv", keep_default_na=False).region)
    if simini.exists():
        t = pd.read_csv(simini, keep_default_na=False, float_precision="round_trip",
                        dtype={"d0": str, "d1": str, "d2": str, "d3": str})
        t = t[t.d0.isin(units) & (t.d1 == "NECR") & (t.d3 == "Y")]
        t = t[["d0", "d2", "value"]].rename(columns={"d0": "region", "d2": "col"})
        t = t.sort_values(["region", "col"], ignore_index=True)
        extract.parent.mkdir(parents=True, exist_ok=True)
        write_source(t, extract, index=False)
    return read_source(extract, keep_default_na=False)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2030)
    year = ap.parse_args().year
    t = items(year)
    extra = sorted(set(t.col) - EXPECTED)
    if extra:
        raise ValueError(f"NECR has columns at 'Y' beyond its level and output: {extra}")
    w = t.pivot_table(index="region", columns="col", values="value", aggfunc="first")
    w = w[w.get("LEVL", 0) > 0]
    if w["OCRO"].isna().any() or (w["OCRO"] <= 0).any():
        raise ValueError("a regional unit with NECR's level and no output")
    out = pd.DataFrame({"region": w.index, "levl_kha": w["LEVL"].values, "yield": w["OCRO"].values / 1000.0})
    dst = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / f"1{year % 100 + 700}" / "supply" / \
        f"necr_{year}.csv"
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(dst, index=False)
    print(f"{dst.name}: {len(out)} regional units, {out.levl_kha.sum():.1f} thousand ha "
          f"(EU {out[~out.region.str[:2].isin(['UK', 'NO', 'TU', 'AL', 'MK', 'CS', 'MO', 'BA', 'KO'])].levl_kha.sum():.1f})")


if __name__ == "__main__":
    main()
