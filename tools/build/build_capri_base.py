#!/usr/bin/env python3
"""Rebuild every region's base data from CAPRI.

Why
---
The base data was assembled by filling a template for all regions and then
overwriting it with CAPRI values only where CAPRI had a number under the code
that was looked up. Three consequences, all found by checking against CAPRI:

* 152 of the 154 checkable regions carried crops CAPRI does not record - about
  3.5 million hectares of template values (sugar beet 8.0, tobacco 1.0, fibre
  1.0, set-aside 3.0 repeated region after region), including citrus in the
  Aosta Valley, grain maize in Finland and olives in northern Spain.
* 100 of 248 regions had no CAPRI source at all, because NUTS renamed or split
  them (all of France, Greece, Sweden, much of Italy and Poland, Ireland,
  Saxony, Croatia, Norway, and the countries CAPRI holds only nationally).
* CAPRI's OFAR - fodder on arable land, 14.3 million hectares EU-wide - had no
  counterpart in the model at all, and nor did fallow (5.5 Mha).

This tool builds all of it from CAPRI, once, with an explicit region map and an
explicit crop map. It replaces tools/build_ireland.py and
tools/build_split_regions.py, which handled single cases; keeping several
pipelines writing the same files caused a real error earlier, when a stale
version ran alongside a new one.

How regions map
---------------
Since 27 October 2026 the model's regions are CAPRI's regional units under CAPRI's own codes
(capri_data/shared/regional_units.csv, tools/build/build_regional_units.py): every region takes its own
CAPRI row. Until then the model had 248 NUTS-2016 regions, matched to CAPRI's codes by renames, merges,
splits by Eurostat cattle numbers (Denmark, Lithuania, Slovenia, Croatia, Saxony, ...), Ireland's 2016
boundary shares, Norway's pooled regions and crop-specific splits from CAPREG's p_REGIO; all of that is gone
(docs/design/REGIONAL_UNITS_INVENTORY.md).

What was NOT mapped when this was written (all are mapped now): table olives (307), other marketable crops (1,156), nursery plants (181),
flowers (118) and other industrial crops (268). These are CAPRI activities the
model has no column for.

Usage
-----
    python tools/build/build_capri_base.py <dir with res_17<CC>.txt dumps>

Writes base_areas, land_availability, animal_numbers and nutrients_regional (supply) on the units, each from scratch:
every cell from CAPRI's dumps (one writer per table, 29 October 2026). Yields, costs and producer prices are written
by build_crop_economics_2017.py.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
_ROOT = Path(__file__).resolve().parents[2]
SUPPLY = _ROOT / "capri_data" / "2017" / "supply"
AREAS, LAND = SUPPLY / "base_areas.csv", SUPPLY / "land_availability.csv"
HERDS, YIELDS = SUPPLY / "animal_numbers.csv", SUPPLY / "yields.csv"
COSTS = SUPPLY / "variable_costs.csv"
#: mineral nitrogen applied, kg N/ha, by region and crop (CAPRI's NMIN). CAPRI
#: reports mineral (NMIN) and manure (NMAN) nitrogen separately per activity;
#: their EU totals, 9.47 and 5.89 Mt, match the real ~10.8 and ~7. NITF is NOT
#: an application rate - it equals NRET, a nitrogen requirement.
NUTRIENTS = SUPPLY / "nutrients_regional.csv"
#: the layouts of the tables written (columns in the committed files' order)
AREA_COLS = ["SWHE", "DWHE", "RYEM", "BARL", "OATS", "CORN", "OCER", "PARI", "PULS", "SUGB", "POTA", "TOMA", "OVEG",
             "APPL", "OFRU", "CITR", "TAGR", "WINE", "OLIV", "TABO", "GRAS", "TOBA", "TEXT", "MAIF", "OFOD", "SETA",
             "RAPE", "SUNF", "SOYA", "OOIL", "OCRO", "OIND", "NURS", "FLOW"]
LAND_COLS = ["ARABLE", "PERMANENT", "GRASSLAND", "FALLOW"]
HERD_COLS = ["DCOW", "SCOW", "COWS", "BULL", "HEIF", "CALV", "PIGS", "PIGF", "HENS", "POUL", "SHGM", "SHGF"]
PRICES = _ROOT / "capri_data" / "sources" / "capreg" / "capreg_producer_prices.csv"

# ---------------------------------------------------------------- crop map --
#: model column -> CAPRI activities summed into it. Textile crops are CAPRI's one activity TEXT (cotton in the
#: three EU countries that grow it, Greece's TEXT being 325 kha, flax and hemp elsewhere); until October 2026 the
#: model split it by country into cotton (COTT) and other fibre (OFIB), tools/build_text_merge.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import _model_codes as _MC  # noqa: E402  the model's activities and their CAPRI activities (codes/model_activities.csv)
CROP_MAP = dict(_MC.CROP_MAP)

#: animal_numbers column -> CAPRI HERD item
HERD_MAP = {"DCOW": "DCOW", "SCOW": "SCOW", "BULL": "BULL", "HEIF": "HEIF",
            "CALV": "CALV", "HENS": "HENS",
            "POUL": "POUL", "SHGM": "SHGM", "SHGF": "SHGF"}   # CAPRI's two sheep and goat activities' herds
#                                                        (until 27 October 2026 the census SHGT, split afterwards by
#                                                        build_shg_split.py at CAPRI's HERD shares of the region group)

#: cost columns verified equal to CAPRI TOIN on DE11, FR10 and ES61
COST_ANIMALS = ("DCOW", "BULL", "PIGF", "OANI")
COST_EXCLUDE = ("SETA", "WINE")
PERMANENT_CROPS = ("APPL", "OFRU", "CITR", "TAGR", "WINE", "OLIV", "TABO")

_ROW = re.compile(r"'([A-Z]{2}[A-Z0-9]{6})'\.'([A-Z]+)'\.'([A-Z]+)'\.'Y'\s+([^,\s]+)")


def _num(tok: str) -> float:
    t = tok.strip().upper()
    if t in ("EPS", "NA", "UNDF", "+INF", "-INF", "INF"):
        return 0.0
    try:
        return float(tok)
    except ValueError:
        return 0.0


def read_capri(dump_dir: Path) -> dict:
    """{capri code: {item: {activity: value}}} for every dump."""
    out: dict = defaultdict(lambda: defaultdict(dict))
    for path in sorted(dump_dir.glob("res_17*.txt")):
        for line in open(path, errors="ignore"):
            m = _ROW.match(line)
            if m and m.group(3) in ("LEVL", "HERD", "YILD", "TOIN", "MPRI",
                                    "NMIN", "MREV"):
                out[m.group(1)][m.group(3)][m.group(2)] = _num(m.group(4))
    return out


def build_spec(capri: dict, regions) -> dict:
    """model region -> ((CAPRI code, weight), ...): on CAPRI's units, each region's own row (used by
    build_crop_economics_2017 and build_ghg_coefs_2017)."""
    missing = [r for r in regions if r not in capri]
    assert not missing, f"no CAPRI rows for {missing}"
    return {r: ((r, 1.0),) for r in regions}


def units() -> list:
    """The model's regions: CAPRI's regional units (shared/regional_units.csv)."""
    with open(_ROOT / "capri_data" / "shared" / "regional_units.csv", newline="") as f:
        return [r["region"] for r in csv.DictReader(f)]


def intensive_values(capri, sources, item, cols):
    """CAPRI's per-unit item (YILD, TOIN, MPRI, NMIN) of each column over the region's sources, weighted by the level of
    the column's first CAPRI activity (CROP_MAP; an animal column is its own CAPRI code), a source without level counted
    by its weight; only positive values. Used by build_crop_economics_2017.py for the four animal columns of the
    costs and prices (COST_ANIMALS)."""
    vals = {}
    for col in cols:
        num = den = 0.0
        for c, w in sources:
            a = CROP_MAP.get(col, (col,))[0]
            lv = w * capri.get(c, {}).get("LEVL", {}).get(a, 0.0)
            v = capri.get(c, {}).get(item, {}).get(a, 0.0)
            if v > 0:
                num += (lv if lv > 0 else w) * v
                den += (lv if lv > 0 else w)
        if den > 0:
            vals[col] = num / den
    return vals


def main(dump_dir: Path):
    capri = read_capri(dump_dir)
    regs = units()
    missing = [r for r in regs if r not in capri]
    assert not missing, f"no CAPRI rows for {missing}"

    # the three tables from scratch on the units, in their layout (until 29 October 2026 the builder took the layout,
    # and any cell it does not write, from the committed file: a read of its own output, so the tables could not be
    # built from blank). The column orders are the files' as committed: the model takes its crop order from
    # base_areas.csv (capri_pmp, the supply model), so the order is kept, not re-sorted.
    areas = pd.DataFrame(index=pd.Index(regs, name="region"), columns=AREA_COLS, dtype=float)
    land = pd.DataFrame(index=pd.Index(regs, name="region"), columns=LAND_COLS, dtype=float)
    herds = pd.DataFrame(index=pd.Index(regs), columns=HERD_COLS, dtype=float)
    # (land_availability's OTHER_AG, of unknown origin and written by no builder, was dropped 27 October 2026)
    nutrients = pd.DataFrame(index=pd.Index(regs, name=areas.index.name), columns=[c for c in CROP_MAP], dtype=float)
    spec = build_spec(capri, regs)

    def items(code, item):
        return capri.get(code, {}).get(item, {})

    for reg, sources in spec.items():
        # ---- levels: crop areas and herds
        for col, capri_cols in CROP_MAP.items():
            if col in areas.columns:
                areas.at[reg, col] = sum(
                    w * sum(items(c, "LEVL").get(a, 0.0) for a in capri_cols)
                    for c, w in sources)
        for col, item in HERD_MAP.items():
            if col in herds.columns:
                herds.at[reg, col] = sum(w * items(c, "HERD").get(item, 0.0)
                                         for c, w in sources)
        if "COWS" in herds.columns:
            herds.at[reg, "COWS"] = herds.at[reg, "DCOW"] + herds.at[reg, "SCOW"]
        # pigs: PIGS = sows (CAPRI SOWS), PIGF = the census total less the sows (CAPRI's 'PIGS' HERD - 'SOWS' HERD), as
        # tools/build_pig_split.py did (a one-off script, no longer in the repository); where CAPRI has no census total
        # (Norway, res_17NO.txt), CAPRI's own PIGF herd (as the removed tools/build/build_norway_pigs.py did for Norway)
        sows = sum(w * items(c, "HERD").get("SOWS", 0.0) for c, w in sources)
        census = sum(w * items(c, "HERD").get("PIGS", 0.0) for c, w in sources)
        herds.at[reg, "PIGS"] = sows
        herds.at[reg, "PIGF"] = (max(census - sows, 0.0) if census > 0
                                 else sum(w * items(c, "HERD").get("PIGF", 0.0) for c, w in sources))

        # ---- intensive values: the N applied per ha (NMIN). Yields, costs and producer prices are written by
        # build_crop_economics_2017.py, their one writer since 29 October 2026 (this builder's first pass over them,
        # from each crop's first CAPRI activity, was overwritten there; the four animal columns it computed are taken
        # from intensive_values by that builder)
        for col, v in intensive_values(capri, sources, "NMIN", [c for c in areas.columns if c in CROP_MAP]).items():
            nutrients.at[reg, col] = v

        # ---- land from the rebuilt areas
        v = areas.loc[reg]
        perm = float(v[[c for c in PERMANENT_CROPS if c in v.index]].sum())
        grass, fallow = float(v.get("GRAS", 0.0)), float(v.get("SETA", 0.0))
        land.at[reg, "PERMANENT"], land.at[reg, "GRASSLAND"] = perm, grass
        land.at[reg, "FALLOW"] = fallow
        land.at[reg, "ARABLE"] = float(v.sum()) - perm - grass - fallow

    for df, p in ((areas, AREAS), (land, LAND), (herds, HERDS), (nutrients, NUTRIENTS)):
        df.to_csv(p)
    eu = [r for r in areas.index if not r.startswith("NO")]
    print(f"rebuilt {len(spec)} regions | EU crop area {areas.loc[eu].sum().sum():,.0f} kha "
          f"| EU dairy cows {herds.loc[eu, 'DCOW'].sum():,.0f} thousand")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
