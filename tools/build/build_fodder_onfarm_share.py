"""CAPRI's on-farm share of the fodders per member state (supply/pmp.gms l. 41-49, p_onFarmShare; KNOWN_ISSUES K213):
the share of a fodder's production its farms lose or keep as seed, (SEDF + SEDM + LOSF) / GROF, for the fodder crops'
outputs GRAS, MAIF, OFAR and ROOF. A fodder crop's output is valued at the solution at UVAG(FODDO) = PSHW x (1 -
p_onFarmShare) + FODDMARKUP (reports/sol_simy.gms l. 753): the dual of the fodder's balance on the part not lost, which
the income takes (capri_mod/income/income_module.py crop_fodder_output).

Source: sim_ini_21730's DATA(MS, item, FODDO, year) (CAPRI's simulation start of 2030, the reference export,
tools/build/build_simini_reference.py): at "Y" for 2030 (CAPRI's "CUR" at the simulation year), at "BAS" for the base
year. The extract is kept (capri_data/sources/raw/capri/results/sim_ini_21730/fodder_onfarm_items.parquet) for a build
without the reference export. The statement is capri_mod/supply/equations/pmp.py p_onFarmShare.

Outputs
  capri_data/2017/feed/fodder_onfarm_share_2017.csv                                   ms, product, onfarm_share (BAS)
  capri_data/baselines/capri_greendeal_ref/1730/feed/fodder_onfarm_share_2030.csv    ms, product, onfarm_share (Y)

    python tools/build/build_fodder_onfarm_share.py
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
EXTRACT = ROOT / "capri_data" / "sources" / "raw" / "capri" / "results" / "sim_ini_21730" / "fodder_onfarm_items.parquet"
FODDO = ("GRAS", "MAIF", "OFAR", "ROOF")            # CAPRI's fodder crops' outputs (FEED_TO_O of FGRA, FMAI, FOFA, FROO)
ITEMS = ("GROF", "LOSF", "SEDF", "SEDM")
YEARS = {"BAS": ROOT / "capri_data" / "2017" / "feed" / "fodder_onfarm_share_2017.csv",
         "Y": ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "feed" / "fodder_onfarm_share_2030.csv"}


def items() -> pd.DataFrame:
    """sim_ini_21730's DATA rows of the member states' fodder balances (ms, item, product, year, value), written to the
    kept extract where the reference export is at hand, read from it otherwise."""
    from capri_mod.data.definitions import capri_ms
    from capri_mod.data.loaders import load_regional_animal_numbers
    ms = {capri_ms(r) for r in load_regional_animal_numbers(str(ROOT / "capri_data")).index}
    if SIMINI.exists():
        t = pd.read_csv(SIMINI, keep_default_na=False, float_precision="round_trip",
                        dtype={"d0": str, "d1": str, "d2": str, "d3": str})
        t = t[t.d0.isin(ms) & t.d1.isin(ITEMS) & t.d2.isin(FODDO) & t.d3.isin(tuple(YEARS))]
        t = t[["d0", "d1", "d2", "d3", "value"]].rename(columns={"d0": "ms", "d1": "item", "d2": "product", "d3": "year"})
        t = t.sort_values(["ms", "product", "year", "item"], ignore_index=True)
        EXTRACT.parent.mkdir(parents=True, exist_ok=True)
        write_source(t, EXTRACT, index=False)
    return read_source(EXTRACT, keep_default_na=False)


def main() -> None:
    from capri_mod.supply.equations.pmp import p_onFarmShare
    t = items()
    for year, out in YEARS.items():
        d = {(m_, p_, i_): float(v_) for m_, i_, p_, y_, v_ in zip(t.ms, t["item"], t["product"], t.year, t.value)
             if y_ == year}
        rows = []
        for m_, p_ in sorted({(m_, p_) for m_, p_, _i in d}):
            g = d.get((m_, p_, "GROF"), 0.0)
            if g <= 0:
                continue
            s = p_onFarmShare(p_, d.get((m_, p_, "SEDF"), 0.0), d.get((m_, p_, "SEDM"), 0.0),
                              d.get((m_, p_, "LOSF"), 0.0), g)
            rows.append(dict(ms=m_, product=p_, onfarm_share=s))
        o = pd.DataFrame(rows, columns=["ms", "product", "onfarm_share"])
        if ((o.onfarm_share < 0) | (o.onfarm_share >= 1)).any():
            raise ValueError(f"{out.name}: an on-farm share outside [0, 1)")
        out.parent.mkdir(parents=True, exist_ok=True)
        o.to_csv(out, index=False)
        print(f"{out.name}: {len(o)} member state x product rows; median by product "
              f"{o.groupby('product').onfarm_share.median().round(3).to_dict()}")


if __name__ == "__main__":
    main()
