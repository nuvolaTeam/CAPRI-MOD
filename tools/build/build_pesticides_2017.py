"""CAPRI's pesticide data at the base year for the pesticide module (supply/cal_pesti.gms, 5_aggregates stage;
claude/pesticide_p1_audit_2026-11-27.md): the applications of the five pesticide aggregates per crop, their unit
values, and the maximum damage without plant protection.

Sources:
- CAPREG's 2017 results, DATA2 of capreg/res_17<CC>.gdx: DATA(region, crop, PESTOF..PESTOO, "Y") in g per ha and
  DATA(region, "UVAG" | "UVAB", PESTOF..PESTOO, "Y") in EUR per kg (supply/cal_pesti.gms l. 239). The year's data of
  the simulation take them as they are (Y = BAS: CAPTRD projects no pesticide item; sim_ini_21730's DATA at "Y"
  equals "BAS" for them).
- CAPREG's p_pestPar of capreg/pmppar_17<CC>.gdx (the file capmod/create_sim_ini_gdx.gms l. 400-410 loads):
  maxDamage(region, crop, aggregate, technology), built by CAPREG from JKI's priors (inputs/pest_cor.gms; the project
  lead's choice of 26 November 2026: read, not ported).
The extracts are kept (capri_data/sources/raw/capri/results/capreg/pesticide_data.parquet, pesticide_max_damage.parquet)
for a build without capri_sources.

Outputs
  capri_data/2017/supply/pesticides_2017.csv            region, activity, item, g_ha
  capri_data/2017/supply/pesticide_prices_2017.csv      region, item, uvag, uvab        (EUR per kg)
  capri_data/2017/supply/pesticide_max_damage_2017.csv  region, activity, item, technology, max_damage

    python tools/build/build_pesticides_2017.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from paths import SOURCES  # noqa: E402  (CAPRI's material outside the repository)
from _sources_io import read_source, write_source  # noqa: E402  (capri_data/sources: Parquet)

CAPREG = SOURCES / "results" / "capreg"
RAW = ROOT / "capri_data" / "sources" / "raw" / "capri" / "results" / "capreg"
EXTRACT_DATA, EXTRACT_DAMAGE = RAW / "pesticide_data.parquet", RAW / "pesticide_max_damage.parquet"
OUT = ROOT / "capri_data" / "2017" / "supply"


def pesTSAgg() -> tuple:
    """CAPRI's five pesticide aggregates (sets.gms; under agg5 pestoAgg = pesModDis = pesTSAgg, l. 4646-4655)."""
    with open(ROOT / "capri_data" / "codes" / "capri" / "pesTSAgg.csv", newline="") as fh:
        return tuple(r["code"] for r in csv.DictReader(fh))


def extracts() -> tuple:
    """The kept extracts, written from CAPREG's GDX files where they are at hand, read otherwise."""
    if (CAPREG / "pmppar_17AT.gdx").exists():
        from _gdx import read_symbol
        aggs = set(pesTSAgg())
        data, dmg = [], []
        for f in sorted(CAPREG.glob("res_17??.gdx")):
            for r, c, row, t, v in read_symbol(f, "DATA2"):
                if t == "Y" and row in aggs:
                    data.append((r, c, row, float(v)))
        for f in sorted(CAPREG.glob("pmppar_17??.gdx")):
            for r, c, it, a, item, v in read_symbol(f, "p_pestPar"):
                if item == "maxDamage" and it in aggs:
                    dmg.append((r, c, it, a, float(v)))
        RAW.mkdir(parents=True, exist_ok=True)
        write_source(pd.DataFrame(data, columns=["region", "col", "row", "value"])
                     .sort_values(["region", "col", "row"], ignore_index=True), EXTRACT_DATA, index=False)
        write_source(pd.DataFrame(dmg, columns=["region", "activity", "item", "technology", "max_damage"])
                     .sort_values(["region", "activity", "item", "technology"], ignore_index=True), EXTRACT_DAMAGE,
                     index=False)
    return (read_source(EXTRACT_DATA, keep_default_na=False, dtype={"region": str, "col": str, "row": str}),
            read_source(EXTRACT_DAMAGE, keep_default_na=False, dtype={"region": str, "activity": str}))


def main() -> None:
    data, dmg = extracts()
    prices = data[data.col.isin(("UVAG", "UVAB"))]
    apps = data[~data.col.isin(("UVAG", "UVAB")) & (data.value != 0)]
    # only the crops' rows: DATA2 also holds the aggregates' balance and value items (GROF, NETF, EAAG, ...) per region
    from capri_mod.data.definitions import capri_set
    mcact = set(capri_set("MCACT"))
    apps = apps[apps.col.isin(mcact)]
    OUT.mkdir(parents=True, exist_ok=True)
    apps.rename(columns={"col": "activity", "row": "item", "value": "g_ha"})[["region", "activity", "item", "g_ha"]] \
        .to_csv(OUT / "pesticides_2017.csv", index=False)
    p = prices.pivot_table(index=["region", "row"], columns="col", values="value", aggfunc="first").reset_index()
    p = p.rename(columns={"row": "item", "UVAG": "uvag", "UVAB": "uvab"})
    for c in ("uvag", "uvab"):
        if c not in p:
            p[c] = float("nan")
    p[["region", "item", "uvag", "uvab"]].sort_values(["region", "item"]).to_csv(
        OUT / "pesticide_prices_2017.csv", index=False)
    dmg[dmg.max_damage != 0].to_csv(OUT / "pesticide_max_damage_2017.csv", index=False)
    print(f"pesticides_2017.csv {len(apps)} rows; pesticide_prices_2017.csv {len(p)}; "
          f"pesticide_max_damage_2017.csv {int((dmg.max_damage != 0).sum())}")


if __name__ == "__main__":
    main()
