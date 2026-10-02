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
DIRECT    CAPRI's code is the region's own (DE110000 -> DE11).
RENAME    NUTS changed the code, not the boundary. Verified by matching CAPRI's
          own region names against Eurostat's (FR240000 "CENTRE" -> FRB0
          "Centre - Val de Loire", and so on for France, Greece, Sweden, Italy,
          Poland and Bulgaria).
MERGE     Two CAPRI regions became one (FI13 + FI1A -> FI1D).
SPLIT     One CAPRI region became several. Split by the children's own cattle
          numbers from Eurostat (tgs00045 and ef_lsk_bovine, 2016/2017).
NATIONAL  CAPRI holds only a national row: either a single-region country, or a
          country split by the same cattle key (Denmark, Lithuania, Slovenia,
          Croatia).
IRELAND   Boundaries shifted between old and new regions, so the split uses the
          year Eurostat published both (2016): IE01 -> IE04 65.4% / IE06 34.6%,
          IE02 -> IE05 86.2% / IE06 13.8%.
NORWAY    Four regions were redrawn into three; together they cover the same
          territory, so CAPRI's three are pooled and split by the four regions'
          2016 shares.
ZERO      CAPRI records no agriculture: Ceuta, Melilla and Brussels. Their rows
          held 725, 725 and 139 kha of phantom farmland.

Assumption: cattle shares are exact for cattle and a proxy for crops. It is
applied only where CAPRI itself holds no regional detail.

What is NOT mapped, and so is absent from the model: table olives (307), other marketable crops (1,156), nursery plants (181),
flowers (118) and other industrial crops (268). These are CAPRI activities the
model has no column for.

Usage
-----
    python tools/build_capri_base.py <dir with res_17<CC>.txt dumps>
"""

from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
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
EUROSTAT = _ROOT / "capri_data" / "sources" / "eurostat"

# ---------------------------------------------------------------- crop map --
#: model column -> CAPRI activities summed into it. Cotton is handled
#: separately: CAPRI's TEXT is "textile crops", which is cotton in the three
#: EU countries that grow it (Greece's TEXT is 325 kha, essentially all cotton)
#: and flax or hemp elsewhere.
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
    # olives for oil plus table olives: both are olive groves, and together
    # they give 5,010 kha against a real EU olive area of about 5.0 Mha
    "OLIV": ("OLIV", "TABO"), "GRAS": ("GRAS",), "TOBA": ("TOBA",),
    "MAIF": ("MAIF",), "RAPE": ("RAPE",), "SUNF": ("SUNF",), "SOYA": ("SOYA",),
    "OOIL": ("OOIL",),
    # "other fodder crops" = fodder on arable land plus fodder roots
    "OFOD": ("OFAR", "ROOF"),
    # the model has one non-productive column; CAPRI separates set-aside from fallow
    "SETA": ("SETA", "FALL"),
}
COTTON_COUNTRIES = ("EL", "ES", "BG")

#: animal_numbers column -> CAPRI HERD item
HERD_MAP = {"DCOW": "DCOW", "SCOW": "SCOW", "BULL": "BULL", "HEIF": "HEIF",
            "CALV": "CALV", "PIGS": "PIGS", "SOWS": "SOWS", "HENS": "HENS",
            "POUL": "POUL", "SHGO": "SHGT"}

#: cost columns verified equal to CAPRI TOIN on DE11, FR10 and ES61
COST_ANIMALS = ("DCOW", "BULL", "PIGF", "OANI")
COST_EXCLUDE = ("SETA", "WINE")
PERMANENT_CROPS = ("APPL", "OFRU", "CITR", "TAGR", "WINE", "OLIV")

# -------------------------------------------------------------- region map --
RENAME = {
    # France: NUTS 2016 recoded every region; boundaries unchanged
    "FRB0": "FR240000", "FRC1": "FR260000", "FRC2": "FR430000",
    "FRD1": "FR250000", "FRD2": "FR230000", "FRE1": "FR300000",
    "FRE2": "FR220000", "FRF1": "FR420000", "FRF2": "FR210000",
    "FRF3": "FR410000", "FRG0": "FR510000", "FRH0": "FR520000",
    "FRI1": "FR610000", "FRI2": "FR630000", "FRI3": "FR530000",
    "FRJ1": "FR810000", "FRJ2": "FR620000", "FRK1": "FR720000",
    "FRK2": "FR710000", "FRL0": "FR820000", "FRM0": "FR830000",
    # Greece
    "EL51": "EL110000", "EL52": "EL120000", "EL53": "EL130000",
    "EL54": "EL210000", "EL61": "EL140000", "EL62": "EL220000",
    "EL63": "EL230000", "EL64": "EL240000", "EL65": "EL250000",
    # Sweden
    "SE11": "SE010000", "SE12": "SE020000", "SE21": "SE090000",
    "SE22": "SE040000", "SE23": "SE0A0000", "SE31": "SE060000",
    "SE32": "SE070000", "SE33": "SE080000",
    # Italy
    "ITG1": "ITA00000", "ITG2": "ITB00000", "ITH3": "IT320000",
    "ITH4": "IT330000", "ITH5": "IT400000", "ITI1": "IT510000",
    "ITI2": "IT520000", "ITI3": "IT530000", "ITI4": "IT600000",
    # Poland
    "PL71": "PL110000", "PL72": "PL330000", "PL81": "PL310000",
    "PL82": "PL320000", "PL84": "PL340000",
    # Italy: CAPRI uses the pre-2010 numeric codes
    "ITC1": "IT110000", "ITC2": "IT120000", "ITC3": "IT130000",
    "ITC4": "IT200000", "ITF1": "IT710000", "ITF2": "IT720000",
    "ITF3": "IT800000", "ITF4": "IT910000", "ITF5": "IT920000",
    "ITF6": "IT930000",
    # Belgium and Luxembourg share one CAPRI file; BL2x are the Flemish and
    # BL3x the Walloon provinces, BL400000 is Luxembourg the country
    "BE21": "BL210000", "BE22": "BL220000", "BE23": "BL230000",
    "BE24": "BL240000", "BE25": "BL250000", "BE31": "BL310000",
    "BE32": "BL320000", "BE33": "BL330000", "BE34": "BL340000",
    "BE35": "BL350000", "LU00": "BL400000",
    # Romania: CAPRI numbers its regions RO01-RO08; matched by name
    "RO21": "RO010000", "RO22": "RO020000", "RO31": "RO030000",
    "RO41": "RO040000", "RO42": "RO050000", "RO11": "RO060000",
    "RO12": "RO070000", "RO32": "RO080000",
    # Bulgaria: CAPRI's own GAMS maps BG01-BG06 onto current NUTS-3 districts
    "BG31": "BG010000", "BG32": "BG020000", "BG33": "BG030000",
    "BG41": "BG040000", "BG42": "BG050000", "BG34": "BG060000",
}
MERGE = {"FI1D": ("FI130000", "FI1A0000")}
#: parent CAPRI code -> children; split by the children's cattle numbers
SPLIT = {
    "HU100000": ("HU11", "HU12"),
    "PL120000": ("PL91", "PL92"),
    "IT310000": ("ITH1", "ITH2"),
    "DED00000": ("DED2", "DED4", "DED5"),
    "FI180000": ("FI1B", "FI1C"),
    "DK000000": ("DK01", "DK02", "DK03", "DK04", "DK05"),
    "LT000000": ("LT01", "LT02"),
    "SI000000": ("SI03", "SI04"),
    "HR000000": ("HR03", "HR04"),
}
NATIONAL = {"CY00": "CY000000", "EE00": "EE000000",
            "LV00": "LV000000", "MT00": "MT000000"}
#: Croatia's other two rows are 2021 regions carved out of HR04; keeping them
#: would double-count. The City of Zagreb held 533 kha of crops.
#: Poland carries 21 rows where NUTS 2016 has 17: the pre-2018 codes PL31,
#: PL32, PL33 and PL34 sit alongside their renamed equivalents PL81, PL82,
#: PL72 and PL84, and both claim the same CAPRI region. Poland was counted
#: twice (its crop area came to 1.23x CAPRI's). The legacy rows are emptied.
ZERO = ("ES63", "ES64", "BE10", "HR05", "HR06",
        "PL31", "PL32", "PL33", "PL34")
IRELAND = {"IE04": (("IR010000", 0.654),),
           "IE05": (("IR020000", 0.862),),
           "IE06": (("IR010000", 0.346), ("IR020000", 0.138))}
NORWAY_PARENTS = ("NO080000", "NO090000", "NO0A0000")
NORWAY_CHILDREN = ("NO01", "NO03", "NO04", "NO05")

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


def cattle_shares(children):
    """Children's shares of their parent, from Eurostat cattle numbers."""
    vals = {}
    for name, flt in (("tgs00045_bovines_nuts2.csv", None),
                      ("ef_lsk_bovine_nuts2.csv",
                       lambda r: r["statinfo"] == "TOTAL" and r["lsu"] == "TOTAL")):
        path = EUROSTAT / name
        if not path.exists():
            continue
        for row in csv.DictReader(open(path, encoding="utf-8-sig")):
            if row["geo"] in children and row["OBS_VALUE"] and \
                    row["TIME_PERIOD"] in ("2016", "2017") and (flt is None or flt(row)):
                vals.setdefault(row["geo"], {})[row["TIME_PERIOD"]] = float(row["OBS_VALUE"])
    got = {c: (v.get("2016") or v.get("2017")) for c, v in vals.items()}
    missing = [c for c in children if not got.get(c)]
    assert not missing, f"no Eurostat cattle figure for {missing}"
    tot = sum(got.values())
    return {c: got[c] / tot for c in children}


def build_spec(capri: dict, regions) -> dict:
    """model region -> ((capri code, weight), ...)"""
    spec: dict = {}
    for reg in regions:
        if reg in ZERO:
            spec[reg] = ()
        elif reg in IRELAND:
            spec[reg] = IRELAND[reg]
        elif reg in RENAME:
            spec[reg] = ((RENAME[reg], 1.0),)
        elif reg in MERGE:
            spec[reg] = tuple((c, 1.0) for c in MERGE[reg])
        elif reg in NATIONAL:
            spec[reg] = ((NATIONAL[reg], 1.0),)
    for parent, children in SPLIT.items():
        shares = cattle_shares(children)
        for ch in children:
            spec[ch] = ((parent, shares[ch]),)
    for ch, share in cattle_shares(NORWAY_CHILDREN).items():
        spec[ch] = tuple((p, share) for p in NORWAY_PARENTS)
    for reg in regions:                      # direct: CAPRI code is the region's own
        if reg not in spec:
            code = reg + "0000"
            if code in capri:
                spec[reg] = ((code, 1.0),)
    return spec


# ---------------------------------------------------------------------------
# Crop-specific splits for Saxony and Croatia
# ---------------------------------------------------------------------------
#: CAPRI's own regional selection (capreg/regio_data_sel/p_REGIO), in CAPRI's
#: codes. Where it holds per-crop areas for the child regions, those replace the
#: single cattle key: a cattle key gives every crop the same split, which put
#: 91% of Croatia's olives in continental Croatia, and gave upland Chemnitz the
#: same share of maize as lowland Leipzig.
REGIO = _ROOT / "capri_data" / "sources" / "capreg" / "p_REGIO.csv.gz"

#: REGIO codes that differ from CAPRI's activity codes. VINE for wine is CAPRI's
#: own concordance entry; OLIT for olives is not in the concordance, but HR03's
#: OLIT for 2013 (18.6 kha) equals CAPRI's national Croatian olive area (18.6)
#: exactly, which fixes its meaning.
REGIO_CODE = {"TWIN": "VINE", "TAGR": "VINE", "OLIV": "OLIT", "TABO": "OLIT"}

#: Saxony was renumbered in NUTS 2013; REGIO holds it under the old codes.
SAXONY_OLD_TO_NEW = {"DED1": "DED4", "DED2": "DED2", "DED3": "DED5"}


def _regio_levels():
    import pandas as pd
    if not REGIO.exists():
        return None
    d = pd.read_csv(REGIO)
    return d[d["uni_1"] == "LEVL"]


def apply_crop_specific_splits(areas, capri):
    """Re-split Saxony and Croatia by crop, from CAPRI's own regional data.

    Saxony: each crop's parent area is divided by that crop's 2003-2007 shares
    across the three Direktionsbezirke. Croatia: HR03 (Adriatic) takes its own
    per-crop areas for 2011-2013, capped at the national total, and HR04 is the
    national remainder - exact, crop by crop. Any crop without regional data
    keeps the value it already had.
    """
    L = _regio_levels()
    if L is None:
        return []
    changed = []

    # --- Saxony
    sx = L[L["uni_0"].isin(SAXONY_OLD_TO_NEW) & L["uni_3"].between(2003, 2007)]
    sx = sx.groupby(["uni_2", "uni_0"])["value"].mean().unstack(1).fillna(0.0)
    parent = capri.get("DED00000", {}).get("LEVL", {})
    kids = [SAXONY_OLD_TO_NEW[k] for k in SAXONY_OLD_TO_NEW]
    if parent and all(k in areas.index for k in kids):
        for col, items in CROP_MAP.items():
            if col not in areas.columns:
                continue
            total = sum(parent.get(i, 0.0) for i in items)
            code = REGIO_CODE.get(items[0], items[0])
            if total <= 0 or code not in sx.index or sx.loc[code].sum() <= 0:
                continue
            row = sx.loc[code] / sx.loc[code].sum()
            for old, new in SAXONY_OLD_TO_NEW.items():
                areas.at[new, col] = total * float(row.get(old, 0.0))
        changed += kids

    # --- Croatia
    hr3 = L[(L["uni_0"] == "HR03") & L["uni_3"].between(2011, 2013)]
    hr3 = hr3.groupby("uni_2")["value"].mean()
    nat = capri.get("HR000000", {}).get("LEVL", {})
    if nat and {"HR03", "HR04"} <= set(areas.index):
        for col, items in CROP_MAP.items():
            if col not in areas.columns:
                continue
            total = sum(nat.get(i, 0.0) for i in items)
            code = REGIO_CODE.get(items[0], items[0])
            if total <= 0 or code not in hr3.index:
                continue
            adriatic = min(float(hr3[code]), total)
            areas.at["HR03", col] = adriatic
            areas.at["HR04", col] = total - adriatic
        changed += ["HR03", "HR04"]
    return changed


def main(dump_dir: Path):
    capri = read_capri(dump_dir)
    areas = pd.read_csv(AREAS, index_col=0)
    land = pd.read_csv(LAND, index_col=0)
    herds = pd.read_csv(HERDS, index_col=0)
    yields = pd.read_csv(YIELDS, index_col=0)
    costs = pd.read_csv(COSTS, index_col=0)
    prices = pd.read_csv(PRICES, index_col=0)
    nutrients = pd.DataFrame(index=sorted(pd.read_csv(AREAS, index_col=0).index),
                             columns=[c for c in CROP_MAP], dtype=float)

    spec = build_spec(capri, list(areas.index))
    missing = [r for r in areas.index if r not in spec]
    assert not missing, f"no CAPRI source for {missing}"

    def items(code, item):
        return capri.get(code, {}).get(item, {})

    for reg, sources in spec.items():
        # ---- levels: crop areas and herds
        for col, capri_cols in CROP_MAP.items():
            if col in areas.columns:
                areas.at[reg, col] = sum(
                    w * sum(items(c, "LEVL").get(a, 0.0) for a in capri_cols)
                    for c, w in sources)
        for col in ("COTT", "OFIB"):
            if col in areas.columns:
                use = (col == "COTT") == (reg[:2] in COTTON_COUNTRIES)
                areas.at[reg, col] = sum(
                    w * items(c, "LEVL").get("TEXT", 0.0) for c, w in sources) if use else 0.0
        for col, item in HERD_MAP.items():
            if col in herds.columns:
                herds.at[reg, col] = sum(w * items(c, "HERD").get(item, 0.0)
                                         for c, w in sources)
        if "COWS" in herds.columns:
            herds.at[reg, "COWS"] = herds.at[reg, "DCOW"] + herds.at[reg, "SCOW"]

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
        if reg in ZERO:
            land.loc[reg] = 0.0

    # replace the single cattle key with crop-specific shares where CAPRI's own
    # regional data allows it, then rebuild land for those regions
    for reg in apply_crop_specific_splits(areas, capri):
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
