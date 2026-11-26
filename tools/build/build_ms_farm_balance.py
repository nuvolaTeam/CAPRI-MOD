"""CAPRI's member states' farm balance of the outputs and their unit values in the base year (income I2c: a member
state's accounts at producer and basic prices, reports/sol_simy.gms l. 1891-1898, 1966-1970, 2389, 2547-2548).

At a simulation year CAPRI sets a final product's seed and losses on farm in fixed proportion to its production at
"CUR" (sol_simy.gms l. 1891-1898: SEDF(SIMY) = GROF(SIMY) x SEDF(CUR) / GROF(CUR), LOSF the same), so the model needs
the member state's GROF, SEDF and LOSF at "CUR": sim_ini_21730's DATA at "Y" for 2030, at "BAS" for the base year. The
unit values at producer and basic prices of the base year (UVAP, UVAB, UVAG at "BAS") are the basic-price account's
(reports/sol_market.gms l. 1325-1337; capmod/inflation_and_trend_interpolation.gms l. 67-72).

Source: sim_ini_21730's DATA (CAPRI's simulation start of 2030, the reference export, tools/build/
build_simini_reference.py). The extract is kept (capri_data/sources/raw/capri/results/sim_ini_21730/
ms_farm_balance_items.parquet) for a build without the reference export.

Outputs
  capri_data/2017/supply/ms_farm_balance_2017.csv                                   ms, product, grof, sedf, losf (BAS)
  capri_data/baselines/capri_greendeal_ref/1730/supply/ms_farm_balance_2030.csv     ms, product, grof, sedf, losf (Y)
  capri_data/2017/supply/ms_unit_values_2017.csv                                    ms, item, uvag, uvap, uvab (BAS)

    python tools/build/build_ms_farm_balance.py
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
EXTRACT = ROOT / "capri_data" / "sources" / "raw" / "capri" / "results" / "sim_ini_21730" / "ms_farm_balance_items.parquet"
BAL = ("GROF", "SEDF", "LOSF")
UV = ("UVAG", "UVAP", "UVAB")
BALANCE = {"BAS": ROOT / "capri_data" / "2017" / "supply" / "ms_farm_balance_2017.csv",
           "Y": ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "supply" / "ms_farm_balance_2030.csv"}
VALUES = ROOT / "capri_data" / "2017" / "supply" / "ms_unit_values_2017.csv"


def items() -> pd.DataFrame:
    """sim_ini_21730's DATA rows of the member states (ms, item, product, year, value): the farm balance of CAPRI's
    outputs (O) at "BAS" and "Y" and the unit values of its items (IO) at "BAS"; written to the kept extract where the
    reference export is at hand, read from it otherwise."""
    from capri_mod.data.definitions import capri_ms, capri_set
    from capri_mod.data.loaders import load_regional_animal_numbers
    ms = {capri_ms(r) for r in load_regional_animal_numbers(str(ROOT / "capri_data")).index}
    out_set, io_set = set(capri_set("O")), set(capri_set("IO"))
    if SIMINI.exists():
        t = pd.read_csv(SIMINI, keep_default_na=False, float_precision="round_trip",
                        dtype={"d0": str, "d1": str, "d2": str, "d3": str})
        t = t[t.d0.isin(ms)]
        bal = t[t.d1.isin(BAL) & t.d2.isin(out_set) & t.d3.isin(tuple(BALANCE))]
        uv = t[t.d1.isin(UV) & t.d2.isin(io_set) & (t.d3 == "BAS")]
        t = pd.concat([bal, uv])[["d0", "d1", "d2", "d3", "value"]]
        t = t.rename(columns={"d0": "ms", "d1": "item", "d2": "product", "d3": "year"})
        t = t.sort_values(["ms", "product", "year", "item"], ignore_index=True)
        EXTRACT.parent.mkdir(parents=True, exist_ok=True)
        write_source(t, EXTRACT, index=False)
    return read_source(EXTRACT, keep_default_na=False)


def main() -> None:
    t = items()
    for year, out in BALANCE.items():
        b = t[t["item"].isin(BAL) & (t.year == year)]
        w = b.pivot_table(index=["ms", "product"], columns="item", values="value", aggfunc="first").reset_index()
        for c in BAL:
            if c not in w:
                w[c] = 0.0
        w = w.fillna(0.0)
        w = w[w.GROF > 0].rename(columns={"GROF": "grof", "SEDF": "sedf", "LOSF": "losf"})
        out.parent.mkdir(parents=True, exist_ok=True)
        w[["ms", "product", "grof", "sedf", "losf"]].to_csv(out, index=False)
        print(f"{out.name}: {len(w)} member state x output rows")
    u = t[t["item"].isin(UV) & (t.year == "BAS")]
    w = u.pivot_table(index=["ms", "product"], columns="item", values="value", aggfunc="first").reset_index()
    w = w.rename(columns={"product": "item", "UVAG": "uvag", "UVAP": "uvap", "UVAB": "uvab"})
    for c in ("uvag", "uvap", "uvab"):
        if c not in w:
            w[c] = float("nan")
    w[["ms", "item", "uvag", "uvap", "uvab"]].to_csv(VALUES, index=False)
    print(f"{VALUES.name}: {len(w)} member state x item rows")


if __name__ == "__main__":
    main()
