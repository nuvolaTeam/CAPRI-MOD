"""CAPRI's marketed over gross production at the 2030 calibration point, per country with supply models and market
product (S7, docs/design/S7_DEMAND_CALIBRATION.md; 6 November 2026).

CAPRI's default $setglobal grofNEprod on (capmod/set_global_variables.gms l. 144-148: "PROD does not include seed use
and losses") hands the market each supply product as the supply models' gross production times CAPRI's ratio at the
calibration point (arm/simu_calibration_to_supply.gms l. 219-247):

  prod(XX, step) = sum over rows mapped to XX (CAP_TO_TRD) of GROF(row, step)  x  prod(XX, "trd") / grof(XX, "trd")

with prod(XX, "trd") = DATA(RMSSUP, "Prod", XX, "CAL") and grof(XX, "trd") = sum over CAP_TO_TRD of
DATA(RMSSUP, "GROF", row, "TRD") (arm/prep_market.gms l. 1290-1300); rice from paddy (PARI), olive oil from olives
(OLIV) and raw milk (MILK) from cow and sheep and goat milk (COMI + SGMI) the same way (l. 230-243). Both items are in
CAPRI's market restart file of the 2030 Green Deal reference, sim_ini_21730.gdx (DATA), converted under
$REFERENCE/simini/simini_21730 (docs/EXTERNAL_SOURCES.md).

The records used are kept in capri_data/sources/raw/capri/results/sim_ini_21730/ (rows filtered, values unchanged), so
the table rebuilds without CAPRI's file.

Output: capri_data/2030/market/market_prod_grof_2030.csv
  capri_ms   CAPRI's country with supply models (RMSSUP)
  product    CAPRI's market product (XX)
  prod_kt    DATA(capri_ms, "Prod", product, "CAL")
  grof_kt    the sum of DATA(capri_ms, "GROF", row, "TRD") over the rows CAPRI maps to the product
  ratio      prod_kt / grof_kt
  (a pair is written where both are positive)

    python tools/build/build_market_prod_grof_2030.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from paths import REFERENCE  # noqa: E402  (CAPRI's files converted to CSV, outside the repository)
from _sources_io import read_source, source_records, write_source  # noqa: E402  (capri_data/sources: Parquet)

SIMINI = REFERENCE / "simini" / "simini_21730" / "DATA.csv.gz"
SETS = REFERENCE / "sets" / "simini_21730"
KEEP_DIR = ROOT / "capri_data" / "sources" / "raw" / "capri" / "results" / "sim_ini_21730"
KEEP = KEEP_DIR / "data_prod_grof_rmssup.parquet"
OUT = ROOT / "capri_data" / "2030" / "market" / "market_prod_grof_2030.csv"
#: the market products whose gross rows are not their own (arm/simu_calibration_to_supply.gms l. 230-243)
SPECIAL = {"RICE": ("PARI",), "OLIO": ("OLIV",), "MILK": ("COMI", "SGMI")}


def _set(name: str) -> list:
    return pd.read_csv(SETS / f"{name}.csv", dtype=str)["d0"].tolist()


def _pairs(name: str) -> list:
    t = pd.read_csv(SETS / f"{name}.csv", dtype=str)
    return list(zip(t["d0"], t["d1"]))


def extract() -> pd.DataFrame:
    """The records of DATA used: PROD at CAL and GROF at TRD of the countries with supply models."""
    rmssup = set(_set("RMSSUP"))
    keep = []
    for ch in pd.read_csv(SIMINI, dtype=str, chunksize=500_000):
        c = ch[ch["d0"].isin(rmssup)
               & (((ch["d1"] == "PROD") & (ch["d3"] == "CAL")) | ((ch["d1"] == "GROF") & (ch["d3"] == "TRD")))]
        keep.append(c[["d0", "d1", "d2", "d3", "value"]])
    out = pd.concat(keep).rename(columns={"d0": "capri_ms", "d1": "item", "d2": "row", "d3": "col"})
    used = set()
    for xx, grof_rows in _products().items():
        used |= {("PROD", xx)} | {("GROF", r) for r in grof_rows}
    out = out[[(i, r) in used for i, r in zip(out["item"], out["row"])]]
    return out.sort_values(["capri_ms", "item", "row"]).reset_index(drop=True)


def _products() -> dict:
    """CAPRI's market products of the supply models and the gross rows each is made of: XX_SUPPLY less the young
    animals (xxOmYani, which CAPRI hands over as production less their use, l. 207-213), through CAP_TO_TRD, and the
    special cases (rice, olive oil, raw milk)."""
    yani = set(_set("xxOmYani"))
    to_trd = {}
    for row, xx in _pairs("CAP_TO_TRD"):
        to_trd.setdefault(xx, []).append(row)
    products = {xx: tuple(to_trd.get(xx, (xx,))) for xx in _set("XX_SUPPLY") if xx not in yani}
    products.update(SPECIAL)
    return products


def main() -> None:
    if SIMINI.exists():
        KEEP_DIR.mkdir(parents=True, exist_ok=True)
        write_source(extract(), KEEP, index=False)
    src = read_source(KEEP, dtype={"capri_ms": str, "item": str, "row": str, "col": str})
    v = {(r.capri_ms, r.item, r.row): float(r.value) for r in src.itertuples()}
    products = _products()
    rows = []
    for ms in sorted({k[0] for k in v}):
        for xx, grof_rows in sorted(products.items()):
            p = v.get((ms, "PROD", xx), 0.0)
            g = sum(v.get((ms, "GROF", r), 0.0) for r in grof_rows)
            if p > 0 and g > 0:
                rows.append(dict(capri_ms=ms, product=xx, prod_kt=p, grof_kt=g, ratio=p / g))
    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False)
    print(f"{len(df)} rows -> {OUT.relative_to(ROOT)}")
    print(df.groupby("product")["ratio"].describe()[["count", "min", "50%", "max"]].to_string(float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    main()
