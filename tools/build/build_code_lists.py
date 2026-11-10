"""The model's code lists and their CAPRI codes, from CAPRI's own sets (data batch, docs/design/DATA_SCHEMA_DUCKDB.md).

The model keeps its own codes (the project lead's decision of 29 October 2026: option 1, a mapping table; CAPRI's codes
throughout may follow later). This builder writes:

  capri_data/codes/capri/<SET>.csv     CAPRI's code lists as instantiated in a CAPMOD run: code, text
                                              (PACT all production activities, MPACT, MCACT, MAACT, XX the market
                                              products, XX1 the market model's products with the non-agricultural good, income,
                                              land and feed energy, RALL all regional units)
  capri_data/codes/capri/FEED_TO_O.csv  CAPRI's feed bulks and their products: feed, row
  capri_data/codes/capri/MS_RU.csv     CAPRI's member states and their regional units (MAP_RR x MS x RU)
  capri_data/codes/capri/RM.csv, RMTP.csv, RM_TO_RMTP.csv, RMEU_to_RM.csv
                                       CAPRI's market regions, trade-policy blocks, the block of each market region
                                              and the EU's two market blocks, in CAPRI's set order (the market's move
                                              onto CAPRI's regions, MARKET_REGIONS_INVENTORY.md stage 1)
  capri_data/codes/model_commodities.csv the model's 58 market commodities (MARKET_COMMODITIES): code,
                                              capri_code, mapping_source

The trade regions' code list (codes/model_trade_regions.csv) and the activities' (codes/model_activities.csv: the
model's activities, their CAPRI activities and those of CAPRI's supply model, a source per row) are not written here
since 30 October 2026: they are declared tables, read by the model and the builders (tools/lib/_model_codes.py). The
activities' list is checked here: the model's crops and animals (definitions.CROPS, ANIMALS) in its order, every CAPRI
code in CAPRI's PACT.

The products' mapping is the one the builders already use, taken from one definition (build_feed_bulks.COMMODITY with
recalibrate_trade_2017.COMMODITY_MAP for the products that are not feed, which must agree, and CAPRI's code where the
model's is CAPRI's own). The builder stops if a model code has no mapping, a CAPRI code is not in CAPRI's set, or another
copy of a mapping in the code disagrees (build_dairy_world_markets.COMM and market/dairy.DAIRY_TRADED; build_dairy_trade_params.CODE
until that builder was removed with armington_params.csv, 29 October 2026), and checks that every regional unit is one of CAPRI's (RALL).

Source of CAPRI's sets: tools/build/build_capri_sets_reference.py's extract of sim_ini_21730.gdx (a CAPMOD restart file
of the project lead's installation; docs/EXTERNAL_SOURCES.md), given with --sets.

    python tools/build/build_code_lists.py --sets /path/to/capri_sources/reference/sets/simini_21730
"""
from __future__ import annotations

import argparse
import ast
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "capri_data" / "codes"
CAPRI_SETS = ("PACT", "MPACT", "MCACT", "MAACT", "XX", "XX1", "RALL", "COLS", "ROWS")


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
    # the model's activity and commodity lists read from definitions.py's source, not by importing it: importing
    # capri_mod.data reads the code lists this builder writes (codes/model_commodities.csv, codes/capri/CACT_TO_NGRP.csv,
    # PERM_NGRP.csv, FEED_TRD.csv; refactor stages 3-4), so the import made the builder depend on its own outputs and
    # the data could not be rebuilt from blank (tools/check/rebuild_from_blank.py, 3 November 2026)
    class D:
        CROPS, ANIMALS, MARKET_COMMODITIES = (literal("capri_mod/data/definitions.py", n)
                                              for n in ("CROPS", "ANIMALS", "MARKET_COMMODITIES"))

    capri = {s: read_set(a.sets, s) for s in CAPRI_SETS}
    # CAPRI's COLS holds a blank element (' '), DATAOUT's empty dim5 (capmod/set_and_store_dataout.gms l. 53:
    # DATAOUT(RSS,"",ColsOut,RowsOut)): not an item, and the long table's empty dim5 stands for it
    for s in ("COLS", "ROWS"):
        capri[s].pop("", None)
    problems = []

    def pairs(name):
        with open(Path(a.sets) / f"{name}.csv", newline="", encoding="utf-8") as fh:
            return [(r["d0"], r["d1"]) for r in csv.DictReader(fh)]

    # activities: the declared code list (codes/model_activities.csv, since 30 October 2026 the master, read by the
    # builders through tools/lib/_model_codes.py) checked against the model's activities and CAPRI's PACT
    with open(OUT / "model_activities.csv", newline="", encoding="utf-8") as fh:
        acts = list(csv.DictReader(fh))
    by_kind = {k: [r["code"] for r in acts if r["kind"] == k] for k in ("crop", "animal")}
    for kind, codes in (("crop", D.CROPS), ("animal", D.ANIMALS)):
        if list(codes) != by_kind[kind]:
            problems.append(f"model_activities.csv: its {kind}s {by_kind[kind]} are not definitions' {list(codes)}")
    for r in acts:
        for col in ("capri_codes", "capmod_codes"):
            for cc in r[col].split(";"):
                if cc not in capri["PACT"]:
                    problems.append(f"model_activities.csv {r['code']}: {col} {cc} is not in CAPRI's PACT")

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
    with open(ROOT / "capri_data" / "codes" / "regional_units.csv", newline="") as fh:
        units = [r["region"] for r in csv.DictReader(fh)]
    miss = [u for u in units if u not in capri["RALL"]]
    if miss:
        problems.append(f"regional units not in CAPRI's RALL: {miss}")

    # the model's activity classes (codes/model_activity_classes.csv, declared; N6) against CAPRI's sets, through the
    # activities' CAPRI codes: a row that differs must say so (its source names the departure, DEP-...)
    lt_of = {}
    for lt, pa in pairs("landTypes_to_pact"):
        lt_of.setdefault(pa, set()).add(lt)
    grp_of = {}
    for g, ca in pairs("cropDivGrps_mCact"):
        grp_of.setdefault(ca, set()).add(g)
    fodcrp = set(read_set(a.sets, "FODCRP"))
    # an activity is a fodder crop where CAPRI's FEDACT_TO_FODDI gives it a fodder item (MAIF, ROOF, OFAR, GRAE, GRAI);
    # FODCRP names the grass product GRAS, not GRAE and GRAI (the model's own activities since S2, 7 November 2026)
    fedact = {pa for pa, _f in pairs("FEDACT_TO_FODDI")}
    fod_of = lambda c: ({c} & fodcrp) | ({c} & fedact)
    capri_of = {r["code"]: r["capri_codes"].split(";") for r in acts}
    with open(OUT / "model_activity_classes.csv", newline="", encoding="utf-8") as fh:
        classes = list(csv.DictReader(fh))
    for r in classes:
        cc = capri_of.get(r["code"], [])
        declared = "DEP-" in r["source"]
        lts = set().union(*(lt_of.get(c, set()) for c in cc)) if cc else set()
        if r["land_type"] and lts and r["land_type"] not in lts and not declared:
            problems.append(f"model_activity_classes.csv {r['code']}: land type {r['land_type']}, CAPRI {sorted(lts)}")
        grps = set().union(*(grp_of.get(c, set()) for c in cc)) if cc else set()
        if (r["cropdiv_group"] or grps) and {r["cropdiv_group"]} != grps and not declared:
            problems.append(f"model_activity_classes.csv {r['code']}: crop-diversification group {r['cropdiv_group']!r}, "
                            f"CAPRI {sorted(grps)}")
        fc = set().union(*(fod_of(c) for c in cc)) if cc else set()
        if bool(int(r["fodder"])) != bool(fc) and not declared:
            problems.append(f"model_activity_classes.csv {r['code']}: fodder {r['fodder']}, CAPRI FODCRP {sorted(fc)}")
    # the further classes (N6, second part): a value that differs from CAPRI's set must say "<column>...: the model's"
    # in its source (or name its departure)
    mcact, oyani = set(read_set(a.sets, "MCACT")), set(read_set(a.sets, "OYANI"))
    eprd = {c for c, _ in pairs("EPRD_TO_GRP")}
    xx_of = {}
    for c, x in pairs("AACT_TO_XX"):
        xx_of.setdefault(c, set()).add(x)
    # the commodities' CAPRI codes as derived above (written below to codes/model_commodities.csv; until 3 November
    # 2026 read back from that file, this builder's own output)
    comm_capri = {c: cc for c, cc, _ in comms}
    for r in classes:
        cc, src = capri_of.get(r["code"], []), r["source"]
        own = lambda col: f"{col} {r[col]}: the model's" in src or f"{col}: the model's" in src or "DEP-" in src
        if r["code"] in D.CROPS:
            if bool(int(r["pesticide"])) != bool(set(cc) & mcact) and not own("pesticide"):
                problems.append(f"model_activity_classes.csv {r['code']}: pesticide {r['pesticide']}, CAPRI MCACT "
                                f"{sorted(set(cc) & mcact)}")
            if bool(int(r["share_term_arable"])) != bool(set(cc) & eprd) and not own("share_term_arable"):
                problems.append(f"model_activity_classes.csv {r['code']}: share_term_arable {r['share_term_arable']}, "
                                f"CAPRI EPRD_TO_GRP {sorted(set(cc) & eprd)}")
        if r["price_source"]:
            px = comm_capri.get(r["price_source"])
            capri_x = set().union(*(xx_of.get(c, set()) for c in cc)) if cc else set()
            if px is None:
                problems.append(f"model_activity_classes.csv {r['code']}: price_source {r['price_source']} is not a commodity")
            elif px not in capri_x and not own("price_source"):
                problems.append(f"model_activity_classes.csv {r['code']}: price_source {r['price_source']} ({px}), CAPRI "
                                f"AACT_TO_XX {sorted(capri_x)}")
        problems += [f"model_activity_classes.csv {r['code']}: young output {y} is not in CAPRI's OYANI"
                     for y in filter(None, r["young_outputs"].split(";")) if y not in oyani]
    # the ammonia technologies the N cascade's equations name (HOUSN_, STORN_, RUNHOUSN_, APPLN_: CAPRI writes the
    # lists in the equations, supply_model.gms l. 3200 ff., and so does the model): each one of CAPRI's MitiTechAmm
    amm = set(read_set(a.sets, "MitiTechAmm"))
    for path, name in (("capri_mod/supply/n_cascade.py", "HOUS_TECHS"), ("capri_mod/supply/n_cascade.py", "STOR_TECHS"),
                       ("capri_mod/supply/n_cascade.py", "RUNH_TECHS"), ("capri_mod/supply/n_cascade.py", "APPL_TECHS"),
                       ("capri_mod/supply/n_leaching.py", "APPL")):
        problems += [f"{path} {name}: {t} is not in CAPRI's MitiTechAmm" for t in literal(path, name) if t not in amm]
    # the prices that follow a market's (codes/model_price_follows.csv, declared; refactor stage 4)
    with open(OUT / "model_price_follows.csv", newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["activity"] not in capri_of:
                problems.append(f"model_price_follows.csv: {r['activity']} is not a model activity")
            if r["commodity"] not in comm_capri:
                problems.append(f"model_price_follows.csv: {r['commodity']} is not a model commodity")
    split_acts = set(read_set(a.sets, "SplitActs"))
    with open(OUT / "model_cattle_splits.csv", newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            for col in ("gains", "gives"):
                if r[col] not in capri["MAACT"]:
                    problems.append(f"model_cattle_splits.csv {r['split']}: {r[col]} is not in CAPRI's MAACT")
            if not {r["gains"], r["gives"]} <= split_acts and "the model's" not in r["source"]:
                problems.append(f"model_cattle_splits.csv {r['split']}: not in CAPRI's SplitActs and not declared the model's")
    lt_mrk = set(read_set(a.sets, "landTypesMrk"))
    with open(OUT / "model_land_types.csv", newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["code"] not in lt_mrk:
                problems.append(f"model_land_types.csv: {r['code']} is not in CAPRI's landTypesMrk")

    # CAPRI's market regions (the market's move onto CAPRI's regions, stage 1: MARKET_REGIONS_INVENTORY.md section 5):
    # RM (45 market regions), RMTP (42 trade-policy blocks), RM_TO_RMTP, RMEU_to_RM (the EU's two market blocks), in
    # CAPRI's set order; checked against RALL and against the behavioural regions' map codes/rms_to_rm.csv
    rm, rmtp = read_set(a.sets, "RM"), read_set(a.sets, "RMTP")
    rm_to_rmtp, rmeu_to_rm = pairs("RM_TO_RMTP"), pairs("RMEU_to_RM")
    for name, codes in (("RM", rm), ("RMTP", rmtp)):
        problems += [f"CAPRI's {name}: {c} is not in RALL" for c in codes if c not in capri["RALL"]]
    blocks_of = {}
    for r, t in rm_to_rmtp:
        blocks_of.setdefault(r, []).append(t)
        if t not in rmtp:
            problems.append(f"CAPRI's RM_TO_RMTP: {t} is not in RMTP")
    problems += [f"CAPRI's RM_TO_RMTP: {r} has {len(blocks_of.get(r, []))} trade-policy blocks, not one"
                 for r in rm if len(blocks_of.get(r, [])) != 1]
    problems += [f"CAPRI's RMEU_to_RM: {r} is not in RM" for _, r in rmeu_to_rm if r not in rm]
    # CAPRI's behavioural regions RMS and their market region RMS_TO_RM, every RMS in one RM: written below to
    # codes/rms.csv and codes/rms_to_rm.csv (until 3 November 2026 written by build_gl_demand.py, which reads them,
    # and checked here; the market's grouping step, tools/lib/_market_regions.py, reads them)
    rms, rms_to_rm = read_set(a.sets, "RMS"), pairs("RMS_TO_RM")
    rm_of_rms = {}
    for r, m in rms_to_rm:
        rm_of_rms.setdefault(r, []).append(m)
        if m not in rm:
            problems.append(f"CAPRI's RMS_TO_RM: {m} is not in RM")
    problems += [f"CAPRI's RMS_TO_RM: {r} has {len(rm_of_rms.get(r, []))} market regions, not one"
                 for r in rms if len(rm_of_rms.get(r, [])) != 1]
    if problems:
        raise SystemExit("code lists not written:\n  " + "\n  ".join(problems))
    for s, d in capri.items():
        write(OUT / "capri" / f"{s}.csv", ("code", "text"), sorted(d.items()))
    # two-dimensional sets: FEED_TO_O (feed bulks and their products) and MAP_RR restricted to each member state's
    # regional units (MS x RU), as envind/digestibility.gms and line_nitr.gms use them (3-NOP, K93)
    ms_, ru_ = set(read_set(a.sets, "MS")), set(read_set(a.sets, "RU"))
    write(OUT / "capri" / "FEED_TO_O.csv", ("feed", "row"), sorted(pairs("FEED_TO_O")))
    # the sets the model's activity classes are checked against (refactor stage 3, N6): land types of the land market
    # and of each activity, crop-diversification groups, fodder crops
    write(OUT / "capri" / "landTypesMrk.csv", ("code", "text"), sorted(read_set(a.sets, "landTypesMrk").items()))
    write(OUT / "capri" / "FODCRP.csv", ("code", "text"), sorted(read_set(a.sets, "FODCRP").items()))
    # CAPRI's permanent crop groups and the crop -> nutrient group map (fertiliser distribution; refactor stage 4)
    write(OUT / "capri" / "PERM_NGRP.csv", ("code", "text"), list(read_set(a.sets, "PERM_NGRP").items()))
    write(OUT / "capri" / "CACT_TO_NGRP.csv", ("cact", "ngrp"), pairs("CACT_TO_NGRP"))
    # CAPRI's traded feed bulks (global/fromimpact/sets.gms FEED_TRD), in CAPRI's set order (refactor stage 4)
    write(OUT / "capri" / "FEED_TRD.csv", ("code", "text"), list(read_set(a.sets, "FEED_TRD").items()))
    write(OUT / "capri" / "landTypes_to_pact.csv", ("land_type", "pact"), sorted(pairs("landTypes_to_pact")))
    write(OUT / "capri" / "cropDivGrps_mCact.csv", ("group", "mcact"), sorted(pairs("cropDivGrps_mCact")))
    write(OUT / "capri" / "MS_RU.csv", ("ms", "ru"), sorted((m, r) for m, r in pairs("Map_RR") if m in ms_ and r in ru_))
    write(OUT / "capri" / "RM.csv", ("code", "text"), list(rm.items()))
    write(OUT / "capri" / "RMTP.csv", ("code", "text"), list(rmtp.items()))
    write(OUT / "capri" / "RM_TO_RMTP.csv", ("rm", "rmtp"), rm_to_rmtp)
    write(OUT / "capri" / "RMEU_to_RM.csv", ("rmeu", "rm"), rmeu_to_rm)
    write(ROOT / "capri_data" / "codes" / "rms.csv", ("rms",), [(r,) for r in rms])
    write(ROOT / "capri_data" / "codes" / "rms_to_rm.csv", ("rms", "rm"), rms_to_rm)
    write(OUT / "model_commodities.csv", ("code", "capri_code", "mapping_source"), comms)
    differ = [(c, cc) for c, cc, _ in comms if c != cc]
    print(f"wrote {OUT.relative_to(ROOT)}: CAPRI's sets {', '.join(f'{s} {len(d)}' for s, d in capri.items())}; "
          f"{len(acts)} model activities checked (codes/model_activities.csv, declared), "
          f"{sum(r['capri_codes'] != r['code'] for r in acts)} not CAPRI's own code; "
          f"{len(comms)} commodities, {len(differ)} not CAPRI's own code ({', '.join(f'{c}={cc}' for c, cc in differ)}); "
          f"{len(units)} regional units, all in RALL")


if __name__ == "__main__":
    main()
