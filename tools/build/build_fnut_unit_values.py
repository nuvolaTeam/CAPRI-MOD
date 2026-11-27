"""CAPRI's base year unit values of the mineral fertilisers at producer and basic prices per member state (income I2b:
the purchases' account at producer and basic prices, reports/sol_simy.gms l. 2547-2548): DATA(MS, "UVAP" | "UVAB",
NITF | PHOF | POTF, "BAS"), EUR per t of N, P2O5, K2O in the base year's money. At a simulation year CAPRI moves them by
inflation alone (capmod/inflation_and_trend_interpolation.gms l. 69-70: the fertilisers are not in the market part),
which the model applies (coupling/equations/inflation_and_trend_interpolation.py DATA_UVAP_IO_SIMY, DATA_UVAB_IO_SIMY;
capri_mod/income/eaa.py).

Source: sim_ini_21730's DATA (CAPRI's simulation start of 2030, the reference export, tools/build/
build_simini_reference.py). The extract is kept (capri_data/sources/raw/capri/results/sim_ini_21730/
fnut_uvap_uvab_bas.parquet) for a build without the reference export.

Output
  capri_data/2017/environment/fnut_unit_values_2017.csv    ms, fnut, uvap_eur_t, uvab_eur_t

    python tools/build/build_fnut_unit_values.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
sys.path.insert(0, str(ROOT))
from paths import REFERENCE  # noqa: E402  (CAPRI's material outside the repository)
from _sources_io import read_source, write_source  # noqa: E402  (capri_data/sources: Parquet)

SIMINI = REFERENCE / "simini" / "simini_21730" / "DATA.csv.gz"
EXTRACT = ROOT / "capri_data" / "sources" / "raw" / "capri" / "results" / "sim_ini_21730" / "fnut_uvap_uvab_bas.parquet"
OUT = ROOT / "capri_data" / "2017" / "environment" / "fnut_unit_values_2017.csv"
FNUT = ("NITF", "PHOF", "POTF")                     # CAPRI's mineral fertilisers (sets.gms FNUT)
ITEMS = ("UVAP", "UVAB")


def items() -> pd.DataFrame:
    """sim_ini_21730's DATA(MS, UVAP | UVAB, FNUT, "BAS") of the model's member states (ms, item, fnut, value), written
    to the kept extract where the reference export is at hand, read from it otherwise."""
    from capri_mod.data.definitions import capri_ms
    from capri_mod.data.loaders import load_regional_animal_numbers
    ms = {capri_ms(r) for r in load_regional_animal_numbers(str(ROOT / "capri_data")).index}
    if SIMINI.exists():
        t = pd.read_csv(SIMINI, keep_default_na=False, float_precision="round_trip",
                        dtype={"d0": str, "d1": str, "d2": str, "d3": str})
        t = t[t.d0.isin(ms) & t.d1.isin(ITEMS) & t.d2.isin(FNUT) & (t.d3 == "BAS")]
        t = t[["d0", "d1", "d2", "value"]].rename(columns={"d0": "ms", "d1": "item", "d2": "fnut"})
        t = t.sort_values(["ms", "fnut", "item"], ignore_index=True)
        EXTRACT.parent.mkdir(parents=True, exist_ok=True)
        write_source(t, EXTRACT, index=False)
    return read_source(EXTRACT, keep_default_na=False)


def main() -> None:
    t = items()
    w = t.pivot_table(index=["ms", "fnut"], columns="item", values="value", aggfunc="first").reset_index()
    w = w.rename(columns={"UVAP": "uvap_eur_t", "UVAB": "uvab_eur_t"})[["ms", "fnut", "uvap_eur_t", "uvab_eur_t"]]
    if w[["uvap_eur_t", "uvab_eur_t"]].isna().any().any() or (w[["uvap_eur_t", "uvab_eur_t"]] <= 0).any().any():
        raise ValueError("a member state without CAPRI's UVAP or UVAB of a fertiliser")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    w.to_csv(OUT, index=False)
    print(f"{OUT.name}: {len(w)} member state x fertiliser rows ({w.ms.nunique()} member states); UVAP = UVAB in "
          f"{int((w.uvap_eur_t == w.uvab_eur_t).sum())}")


if __name__ == "__main__":
    main()
