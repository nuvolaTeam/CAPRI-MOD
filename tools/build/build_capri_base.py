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

Writes base_areas, land_availability, animal_numbers, yields, variable_costs (supply), nutrients_regional and
sources/capreg/capreg_producer_prices.csv on the units, with the columns they have; the columns other builders
add (the sheep and goat split, the animal yields, prices of other items, OTHER_AG) are filled when those run.
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
PRICES = _ROOT / "capri_data" / "sources" / "capreg" / "capreg_producer_prices.csv"

# ---------------------------------------------------------------- crop map --
#: model column -> CAPRI activities summed into it. Textile crops are CAPRI's one activity TEXT (cotton in the
#: three EU countries that grow it, Greece's TEXT being 325 kha, flax and hemp elsewhere); until October 2026 the
#: model split it by country into cotton (COTT) and other fibre (OFIB), tools/build_text_merge.py.
CROP_MAP = {
    "SWHE": ("SWHE",), "DWHE": ("DWHE",), "RYEM": ("RYEM",), "BARL": ("BARL",),
    "OATS": ("OATS",), "CORN": ("MAIZ",), "OCER": ("OCER",),
    # paddy rice: 427 kha EU, concentrated in Italy, Spain, Portugal and Greece
    "PARI": ("PARI",), "PULS": ("PULS",),
    # minor activities CAPRI records separately: other marketable crops,
    # other industrial crops, nursery plants and flowers (1,721 kha EU)
    "OCRO": ("OCRO",), "OIND": ("OIND",), "NURS": ("NURS",), "FLOW": ("FLOW",),
    "SUGB": ("SUGB",), "POTA": ("POTA",), "TOMA": ("TOMA",), "OVEG": ("OVEG",),
    "APPL": ("APPL",), "OFRU": ("OFRU",), "CITR": ("CITR",), "TAGR": ("TAGR",),
    "WINE": ("TWIN",),
    # olives for oil and table olives, CAPRI's two activities (separate since October 2026,
    # tools/build_tabo_split.py; together 5,010 kha against a real EU olive area of about 5.0 Mha)
    "OLIV": ("OLIV",), "TABO": ("TABO",), "GRAS": ("GRAS",), "TOBA": ("TOBA",),
    "MAIF": ("MAIF",), "RAPE": ("RAPE",), "SUNF": ("SUNF",), "SOYA": ("SOYA",),
    "OOIL": ("OOIL",), "TEXT": ("TEXT",),
    # "other fodder crops" = fodder on arable land plus fodder roots
    "OFOD": ("OFAR", "ROOF"),
    # the model has one non-productive column; CAPRI separates set-aside from fallow
    "SETA": ("SETA", "FALL"),
}

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


def main(dump_dir: Path):
    capri = read_capri(dump_dir)
    regs = units()
    missing = [r for r in regs if r not in capri]
    assert not missing, f"no CAPRI rows for {missing}"

    def frame(path):
        """the table on the units: as it is if it already holds exactly the units (this builder re-run, or the producer
        prices written by extract_all_from_data2.py first), else its columns, empty (columns other builders fill stay
        empty until they run)"""
        t = _read_csv(path, index_col=0)
        if sorted(map(str, t.index)) == sorted(regs):
            return t.reindex(regs).astype(float)
        return pd.DataFrame(index=pd.Index(regs, name=t.index.name), columns=t.columns, dtype=float)
    areas, land, herds = frame(AREAS), frame(LAND), frame(HERDS)
    # OTHER_AG (other agricultural land): written by no builder, of unknown origin (template-like values: 6.25, 2.97619);
    # read only by the environmental module's HNV indicator through the land total. Dropped 27 October 2026
    land = land.drop(columns=["OTHER_AG"], errors="ignore")
    yields, costs, prices = frame(YIELDS), frame(COSTS), frame(PRICES)
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

        # ---- intensive values: area-weighted across sources
        def intensive(item, capri_code_for):
            vals = {}
            for col in capri_code_for:
                num = den = 0.0
                for c, w in sources:
                    a = CROP_MAP.get(col, (col,))[0]
                    lv = w * items(c, "LEVL").get(a, 0.0)
                    v = items(c, item).get(a, 0.0)
                    if v > 0:
                        num += (lv if lv > 0 else w) * v
                        den += (lv if lv > 0 else w)
                if den > 0:
                    vals[col] = num / den
            return vals

        crop_cols = [c for c in areas.columns if c in CROP_MAP and c != "GRAS"]
        for col, v in intensive("YILD", crop_cols).items():
            yields.at[reg, col] = v / 1000.0
        cost_cols = [c for c in costs.columns
                     if (c in CROP_MAP or c in COST_ANIMALS) and c not in COST_EXCLUDE]
        for col, v in intensive("TOIN", cost_cols).items():
            costs.at[reg, col] = v
        price_cols = [c for c in prices.columns if c in CROP_MAP or c in COST_ANIMALS]
        for col, v in intensive("MPRI", price_cols).items():
            prices.at[reg, col] = v
        for col, v in intensive("NMIN", [c for c in areas.columns if c in CROP_MAP]).items():
            nutrients.at[reg, col] = v

        # Grass is not traded, so CAPRI carries a DUMMY price for it - exactly
        # 1000 EUR/t in every region - while its real valuation sits in MREV
        # (362 EUR/ha in DE11). Copying the dummy through gave grass a net
        # revenue of 6,125 EUR/ha and made it the largest item in the regional
        # gross margin. The price is derived from CAPRI's own revenue instead,
        # on the dry-matter yield the model actually uses.
        if "GRAS" in prices.columns:
            mrev = sum(w * items(c, "MREV").get("GRAS", 0.0) for c, w in sources)
            raw_gras = float(yields.at[reg, "GRAS"]) if "GRAS" in yields.columns else 0.0
            dm_yield = raw_gras / 1000.0 * 0.20 if raw_gras > 100 else raw_gras
            if mrev > 0 and dm_yield > 0:
                prices.at[reg, "GRAS"] = mrev / dm_yield

        # ---- land from the rebuilt areas
        v = areas.loc[reg]
        perm = float(v[[c for c in PERMANENT_CROPS if c in v.index]].sum())
        grass, fallow = float(v.get("GRAS", 0.0)), float(v.get("SETA", 0.0))
        land.at[reg, "PERMANENT"], land.at[reg, "GRASSLAND"] = perm, grass
        land.at[reg, "FALLOW"] = fallow
        land.at[reg, "ARABLE"] = float(v.sum()) - perm - grass - fallow

    for df, p in ((areas, AREAS), (land, LAND), (herds, HERDS),
                  (yields, YIELDS), (costs, COSTS), (prices, PRICES),
                  (nutrients, NUTRIENTS)):
        df.to_csv(p)
    eu = [r for r in areas.index if not r.startswith("NO")]
    print(f"rebuilt {len(spec)} regions | EU crop area {areas.loc[eu].sum().sum():,.0f} kha "
          f"| EU dairy cows {herds.loc[eu, 'DCOW'].sum():,.0f} thousand")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
