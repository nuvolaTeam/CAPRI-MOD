"""The model's code lists and their CAPRI codes, from CAPRI's own sets (data batch, docs/design/DATA_SCHEMA_DUCKDB.md).

The model keeps its own codes (the project lead's decision of 29 October 2026: option 1, a mapping table; CAPRI's codes
throughout may follow later). This builder writes:

  capri_data/schema/codes/capri/<SET>.csv     CAPRI's code lists as instantiated in a CAPMOD run: code, text
                                              (PACT all production activities, MPACT, MCACT, MAACT, XX the market
                                              products, XX1 the market model's products with the non-agricultural good, income,
                                              land and feed energy, RALL all regional units)
  capri_data/schema/codes/capri/FEED_TO_O.csv  CAPRI's feed bulks and their products: feed, row
  capri_data/schema/codes/capri/MS_RU.csv     CAPRI's member states and their regional units (MAP_RR x MS x RU)
  capri_data/schema/codes/model_activities.csv  the model's 46 activities (capri_mod/data/definitions.py CROPS,
                                              ANIMALS): code, kind, capri_codes (";"-joined CAPRI activities summed
                                              into it), mapping_source
  capri_data/schema/codes/model_commodities.csv the model's 58 market commodities (MARKET_COMMODITIES): code,
                                              capri_code, mapping_source

The mappings are the ones the builders already use, taken from one definition each (crops: build_capri_base.CROP_MAP;
animals: build_animal_yields.ANIMALS; market products: build_feed_bulks.COMMODITY with
recalibrate_trade_2017.COMMODITY_MAP for the products that are not feed, which must agree, and CAPRI's code where the
model's is CAPRI's own). The builder stops if a model code has no mapping, a CAPRI code is not in CAPRI's set, or another copy of
a mapping in the code disagrees (build_livestock_units, build_plant_protection_cost, build_supplement_effects for the
animals; build_dairy_world_markets.COMM and market/dairy.DAIRY_TRADED for the products; build_dairy_trade_params.CODE
until that builder was removed with armington_params.csv, 29 October 2026), and checks that every regional unit is one of CAPRI's (RALL).

Source of CAPRI's sets: tools/build/build_capri_sets_reference.py's extract of sim_ini_21730.gdx (a CAPMOD restart file
of the project lead's installation; capri_reference/README.md), given with --sets.

    python tools/build/build_code_lists.py --sets /path/to/capri_reference/sets/simini_21730
"""
from __future__ import annotations

import argparse
import ast
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "capri_data" / "schema" / "codes"
CAPRI_SETS = ("PACT", "MPACT", "MCACT", "MAACT", "XX", "XX1", "RALL")


def literal(path, name):
    """A module-level dict or tuple of a builder, read without running the builder."""
    tree = ast.parse((ROOT / path).read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            tgt = node.targets[0] if isinstance(node, ast.Assign) else node.target
            if getattr(tgt, "id", getattr(tgt, "attr", None)) == name:
                return ast.literal_eval(node.value)
    raise KeyError(f"{path}: no {name}")


def read_set(sets_dir, name):
    with open(Path(sets_dir) / f"{name}.csv", newline="", encoding="utf-8") as fh:
        return {r["d0"]: (r.get("text") or "") for r in csv.DictReader(fh)}


def write(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sets", required=True, help="folder of CAPRI's sets (build_capri_sets_reference.py output)")
    a = ap.parse_args()
    from capri_mod.data import definitions as D

    capri = {s: read_set(a.sets, s) for s in CAPRI_SETS}
    problems = []

    # activities
    crop_src, anim_src = "tools/build/build_capri_base.py CROP_MAP", "tools/build/build_animal_yields.py ANIMALS"
    crop_map = literal("tools/build/build_capri_base.py", "CROP_MAP")
    anim_map = literal("tools/build/build_animal_yields.py", "ANIMALS")
    for path, name in (("tools/build/build_livestock_units.py", "ANIMALS"),
                       ("tools/build/build_plant_protection_cost.py", "ANIMALS"),
                       ("tools/build/build_supplement_effects.py", "MAP")):
        other = literal(path, name)
        for k, v in other.items():
            if tuple(anim_map.get(k, ())) != tuple(v):
                problems.append(f"{path} {name}[{k}] = {v}, {anim_src} {anim_map.get(k)}")
    acts = []
    for kind, codes, mp, src in (("crop", D.CROPS, crop_map, crop_src), ("animal", D.ANIMALS, anim_map, anim_src)):
        for c in codes:
            if c not in mp:
                problems.append(f"{kind} {c}: no CAPRI activity in {src}")
                continue
            for cc in mp[c]:
                if cc not in capri["PACT"]:
                    problems.append(f"{kind} {c}: {cc} is not in CAPRI's PACT")
            acts.append((c, kind, ";".join(mp[c]), src))
    extra = sorted(set(crop_map) - set(D.CROPS)) + sorted(set(anim_map) - set(D.ANIMALS))
    if extra:
        problems.append(f"mapped but not a model activity: {extra}")

    # market commodities: build_feed_bulks.COMMODITY is CAPRI -> model
    prod_src = "tools/build/build_feed_bulks.py COMMODITY"
    to_model = literal("tools/build/build_feed_bulks.py", "COMMODITY")
    to_capri, src_of = {}, {}
    for cc, m in to_model.items():
        if m in to_capri and to_capri[m] != cc:
            problems.append(f"{prod_src}: {m} from both {to_capri[m]} and {cc}")
        to_capri[m], src_of[m] = cc, prod_src
    # the trade builder's map (model -> CAPRI) has the products that are not feed (poultry meat): the union of the
    # two, which must agree where both have a product
    trade_src = "tools/build/recalibrate_trade_2017.py COMMODITY_MAP"
    for m, cc in literal("tools/build/recalibrate_trade_2017.py", "COMMODITY_MAP").items():
        if m in to_capri and to_capri[m] != cc:
            problems.append(f"{trade_src}: {m} -> {cc}, {prod_src} -> {to_capri[m]}")
        elif m not in to_capri:
            to_capri[m], src_of[m] = cc, trade_src
    checks = [("tools/build/build_dairy_world_markets.py", "COMM", True),            # CAPRI -> model
              ("capri_mod/market/dairy.py", "DAIRY_TRADED", True)]
    for path, name, capri_first in checks:
        for k, v in literal(path, name).items():
            if not isinstance(v, str):
                continue
            m, cc = (v, k) if capri_first else (k, v)
            want = to_capri.get(m, m if m in capri["XX"] else None)
            if want != cc:
                problems.append(f"{path} {name}: {m} -> {cc}, {prod_src} -> {want}")
    comms = []
    for c in D.MARKET_COMMODITIES:
        if c in to_capri:
            cc, src = to_capri[c], src_of[c]
        elif c in capri["XX"]:
            cc, src = c, "CAPRI's own code (XX)"
        else:
            problems.append(f"commodity {c}: no CAPRI market product")
            continue
        if cc not in capri["XX"]:
            problems.append(f"commodity {c}: {cc} is not in CAPRI's XX")
        comms.append((c, cc, src))

    # regional units
    with open(ROOT / "capri_data" / "shared" / "regional_units.csv", newline="") as fh:
        units = [r["region"] for r in csv.DictReader(fh)]
    miss = [u for u in units if u not in capri["RALL"]]
    if miss:
        problems.append(f"regional units not in CAPRI's RALL: {miss}")

    if problems:
        raise SystemExit("code lists not written:\n  " + "\n  ".join(problems))
    for s, d in capri.items():
        write(OUT / "capri" / f"{s}.csv", ("code", "text"), sorted(d.items()))
    # two-dimensional sets: FEED_TO_O (feed bulks and their products) and MAP_RR restricted to each member state's
    # regional units (MS x RU), as envind/digestibility.gms and line_nitr.gms use them (3-NOP, K93)
    def pairs(name):
        with open(Path(a.sets) / f"{name}.csv", newline="", encoding="utf-8") as fh:
            return [(r["d0"], r["d1"]) for r in csv.DictReader(fh)]
    ms_, ru_ = set(read_set(a.sets, "MS")), set(read_set(a.sets, "RU"))
    write(OUT / "capri" / "FEED_TO_O.csv", ("feed", "row"), sorted(pairs("FEED_TO_O")))
    write(OUT / "capri" / "MS_RU.csv", ("ms", "ru"), sorted((m, r) for m, r in pairs("Map_RR") if m in ms_ and r in ru_))
    write(OUT / "model_activities.csv", ("code", "kind", "capri_codes", "mapping_source"), acts)
    write(OUT / "model_commodities.csv", ("code", "capri_code", "mapping_source"), comms)
    differ = [(c, cc) for c, cc, _ in comms if c != cc]
    print(f"wrote {OUT.relative_to(ROOT)}: CAPRI's sets {', '.join(f'{s} {len(d)}' for s, d in capri.items())}; "
          f"{len(acts)} model activities, {sum(a[2] != a[0] for a in acts)} not CAPRI's own code; "
          f"{len(comms)} commodities, {len(differ)} not CAPRI's own code ({', '.join(f'{c}={cc}' for c, cc in differ)}); "
          f"{len(units)} regional units, all in RALL")


if __name__ == "__main__":
    main()
