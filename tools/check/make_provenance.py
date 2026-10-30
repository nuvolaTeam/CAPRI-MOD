"""Each data file's provenance as SQL, from the pipeline's trace: capri_data/schema/01_provenance.sql.

For every CSV under capri_data (archive/ left out) one row of the table provenance:
  file      the file
  nature    capri: built from CAPRI's own code, data or results only
            capri-publication: from CAPRI's published results (JRC121368) only
            external: from sources other than CAPRI only (Eurostat, FAO)
            mixed: from CAPRI and other sources (origins lists them)
            source-extract: a source file kept in capri_data/sources (its origin in origins; its builder when one
            writes it: the CSV conversion of a non-CSV original, tools/build/convert_sources_to_csv.py)
            declared: a table kept by hand with a source per row, read as declared (no builder)
            no-builder: none of the above (to resolve)
  origins   the origins of the leaves its builders read, through every builder in between (CAPRI, JRC121368,
            Eurostat, FAO, EC, unsourced; a source file's own row may name where CAPRI took it from, as "USDA via
            CAPRI")
  builder   the builder that writes it (tools/build/<builder>.py; several invocations: the task names)
  sources   the files outside the repository its builder chain reads ($UP: the project lead's uploads, $WORK: the work
            folder of CAPRI's dumps), runs of numbered files collapsed (res_17<CC>.txt)

The trace is tools/pipeline/builders.json (tools/check/make_pipeline.py). Files written by no traced builder are
looked up in DECLARED, SOURCE_ORIGIN, UNTRACED and NO_BUILDER_ORIGIN below; the rest are "no-builder".
The notes that need a person (checked statements on a file's content or quality) are kept apart, in
capri_data/schema/02_provenance_notes.sql, which this script does not touch.

    python tools/check/make_provenance.py           # writes capri_data/schema/01_provenance.sql
    python tools/check/make_provenance.py --check   # exit 1 if the file is not up to date (the test); writes nothing
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = ROOT / "tools" / "pipeline" / "builders.json"
OUT = ROOT / "capri_data" / "schema" / "01_provenance.sql"

#: the origin of the files kept under capri_data/sources, by folder (each folder's README or builder states it)
SOURCE_ORIGIN = {
    "jrc121368": "JRC121368", "eurostat": "Eurostat", "nuts": "Eurostat", "fao_2021": "FAO", "unsourced": "unsourced",
}
#: CAPRI's folders under sources (every other folder): CAPRI's code, data (dat), CAPREG, COCO, CAPMOD results
SOURCE_DEFAULT = "CAPRI"
#: tables kept by hand, with a source per row, read as declared (KNOWN_ISSUES K101)
DECLARED = {"capri_data/shared/capri_member_state_codes.csv", "capri_data/shared/model_parameters.csv",
            "capri_data/schema/model_units.csv"}
#: the origin of the external files the builders read: every one is CAPRI's (its exports, dumps, dat files and
#: code), checked 29 October 2026 against the builders' docstrings
EXTERNAL_ORIGIN = "CAPRI"
#: files written by builders that the trace has not run yet (added after the last retrace), by file or folder prefix:
#: builder, origins (from the builder's docstring); a retrace moves them into builders.json
UNTRACED = {
    "capri_data/pipeline/captrd/sets/": ("build_captrd_sets", "CAPRI"),
    "capri_data/pipeline/captrd/dat/": ("build_captrd_dat", "CAPRI"),
    "capri_data/validation/eu_outlook_2020_2030.csv": ("build_eu_outlook_2030", "EC"),
    "capri_data/validation/n_cascade_capri_gd2030.csv": ("build_n_cascade_validation", "CAPRI"),
    # the CSV conversion of the sources that were not CSV (30 October 2026); under capri_data/sources they stay
    # source extracts, with their converter named
    "capri_data/sources/water/": ("convert_sources_to_csv", "CAPRI"),
    "capri_data/sources/capri_gams/": ("convert_sources_to_csv", "CAPRI"),
    "capri_data/sources/capri_dat/biofuel/": ("convert_sources_to_csv", "CAPRI"),
    "capri_data/sources/capri_dat/coco/": ("convert_sources_to_csv", "CAPRI"),
    "capri_data/sources/capri_dat/policy/": ("convert_sources_to_csv", "CAPRI"),
    "capri_data/sources/envind/fao_landuse_2000_P.csv": ("convert_sources_to_csv", "CAPRI"),
    "capri_data/sources/envind/ipcc_wetlands_p_emifacOrganicSoil_ori.csv": ("convert_sources_to_csv", "CAPRI"),
    "capri_data/sources/envind/orgsoil_share_p_orgsoilori.csv": ("convert_sources_to_csv", "CAPRI"),
    "capri_data/sources/ghgtech/LitRevFertTech_p_litRevFertTechs_all.csv": ("convert_sources_to_csv", "CAPRI"),
    "capri_data/sources/ghgtech/miti_data_jul15_p_ghgMiti.csv": ("convert_sources_to_csv", "CAPRI"),
    "capri_data/sources/ghgtech/miti_data_jul15_allMitiTech.csv": ("convert_sources_to_csv", "CAPRI"),
    "capri_data/sources/ghgtech/miti_data_jul15_mitiTech_map.csv": ("convert_sources_to_csv", "CAPRI"),
    "capri_data/sources/ghgtech/miti_data_jul15_mitiTarget.csv": ("convert_sources_to_csv", "CAPRI"),
    "capri_data/sources/ghgtech/miti_data_jul15_mitiInfo.csv": ("convert_sources_to_csv", "CAPRI"),
    "capri_data/sources/policy/minfert_redu_by_crop_p_checkSmallMine.csv": ("convert_sources_to_csv", "CAPRI"),
    "capri_data/sources/policy/minfert_redu_by_crop_limCres.csv": ("convert_sources_to_csv", "CAPRI"),
    "capri_data/sources/eu_tariff_provenance.csv": ("convert_sources_to_csv", "CAPRI"),
    "capri_data/sources/capri_star/nutrient_cont_usda_p_nutrientCont.csv": ("convert_sources_to_csv", "USDA via CAPRI"),
    "capri_data/sources/nuts/": ("convert_sources_to_csv", "Eurostat"),
}
#: files without a builder whose origin was established by a check (02_provenance_notes.sql gives the evidence)
NO_BUILDER_ORIGIN = {
    "capri_data/2017/environment/climate_zones.csv": "CAPRI",
    "capri_data/sources/capri_dat/sugar/p_SQuotas.csv": "CAPRI",
    "capri_data/sources/capri_dat/sugar/p_PPSQRenounce.csv": "CAPRI",
    "capri_data/sources/capri_dat/sugar/p_PPSQCBuyBack.csv": "CAPRI",
}


def _untraced(rel):
    """UNTRACED's (builder, origin) of a file, by its path or a folder prefix."""
    return next((v for k, v in UNTRACED.items() if rel == k or (k.endswith("/") and rel.startswith(k))), None)


def _collapse(paths):
    """res_17AT.txt, res_17BG.txt, ... -> res_17<CC>.txt (runs of files that differ in a country code)."""
    groups = defaultdict(list)
    for p in paths:
        k = re.sub(r"(?<=[_/])(?:[A-Z]{2}|TUR?)(?=[_.])|(?<=_17)[A-Z]{2}(?=[_.])|(?<=21730)[A-Z]{2}(?=default)", "<CC>", p)
        groups[k].append(p)
    return sorted(k if len(v) > 1 else v[0] for k, v in groups.items())


def provenance(root: Path = ROOT):
    tasks = json.loads((root / "tools" / "pipeline" / "builders.json").read_text())["tasks"]
    writer = {}
    for t in tasks:
        for o in t["outputs"]:
            writer[o] = t

    memo = {}

    def leaves(f, seen=()):
        """(origins, externals) of file f."""
        if f in memo:
            return memo[f]
        if f in seen:
            return set(), set()
        t = writer.get(f)
        if t is None:
            if f.startswith("capri_data/sources/"):
                folder = f.split("/")[2]
                res = ({SOURCE_ORIGIN.get(folder, SOURCE_DEFAULT)}, set())
            elif f in DECLARED:
                res = ({"declared"}, set())
            else:
                res = (set(), set())
            memo[f] = res
            return res
        origins, ext = set(), set(t["external"])
        if t["external"]:
            origins.add(EXTERNAL_ORIGIN)
        for i in t["inputs"]:
            if not i.startswith("capri_data/"):
                continue
            o, e = leaves(i, seen + (f,))
            origins |= o
            ext |= e
        memo[f] = (origins, ext)
        return memo[f]

    rows = []
    for p in sorted(root.joinpath("capri_data").rglob("*.csv")):
        rel = str(p.relative_to(root))
        if "archive" in p.parts:
            continue
        t = writer.get(rel)
        if rel.startswith("capri_data/sources/") and t is None:
            folder = rel.split("/")[2]
            hit = _untraced(rel)
            rows.append((rel, "source-extract", hit[1], hit[0] + " (not in the trace yet)", None) if hit else
                        (rel, "source-extract", SOURCE_ORIGIN.get(folder, SOURCE_DEFAULT), None, None))
            continue
        if rel in DECLARED:
            rows.append((rel, "declared", "per row", None, None))
            continue
        if t is None:
            hit = _untraced(rel)
            if hit:
                o = hit[1]
                rows.append((rel, "capri" if o == "CAPRI" else "external", o, hit[0] + " (not in the trace yet)",
                             None))
            elif rel in NO_BUILDER_ORIGIN:
                o = NO_BUILDER_ORIGIN[rel]
                rows.append((rel, "capri" if o == "CAPRI" else "external", o, None, None))
            else:
                rows.append((rel, "no-builder", "", None, None))
            continue
        origins, ext = leaves(rel)
        origins.discard("declared")
        o = sorted(origins)
        if o == ["CAPRI"]:
            nature = "capri"
        elif o == ["JRC121368"]:
            nature = "capri-publication"
        elif o and "CAPRI" not in o and "JRC121368" not in o:
            nature = "external"
        elif o:
            nature = "mixed"
        else:
            nature = "no-builder"
        builders = sorted({x["task"] for x in tasks if rel in x["outputs"]})
        rows.append((rel, nature, ", ".join(o), ", ".join(builders), "; ".join(_collapse(sorted(ext))) or None))
    return rows


def _q(v):
    return "NULL" if v is None else "'" + str(v).replace("'", "''") + "'"


def render(rows) -> str:
    lines = [
        "-- Provenance of every CSV under capri_data: generated by tools/check/make_provenance.py from the pipeline's trace",
        "-- (tools/pipeline/builders.json); do not edit by hand. Notes checked by a person: 02_provenance_notes.sql.",
        "",
        "CREATE TABLE provenance (",
        "    file VARCHAR PRIMARY KEY,",
        "    nature VARCHAR NOT NULL CHECK (nature IN ('capri', 'capri-publication', 'external', 'mixed', "
        "'source-extract', 'declared', 'no-builder')),",
        "    origins VARCHAR NOT NULL,",
        "    builder VARCHAR,",
        "    sources VARCHAR,",
        "    note VARCHAR",
        ");",
        "COMMENT ON TABLE provenance IS 'each data file: its nature, the origins of what its builders read, its builder, "
        "the files outside the repository its builder chain reads';",
        "INSERT INTO provenance (file, nature, origins, builder, sources) VALUES",
    ]
    vals = [f"  ({_q(f)}, {_q(n)}, {_q(o)}, {_q(b)}, {_q(s)})" for f, n, o, b, s in rows]
    lines.append(",\n".join(vals) + ";")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    rows = provenance()
    from collections import Counter
    print(Counter(r[1] for r in rows))
    nb = [r[0] for r in rows if r[1] == "no-builder"]
    if nb:
        print("no builder:", *nb, sep="\n  ")
    out = render(rows)
    if a.check:
        ok = OUT.exists() and OUT.read_text(encoding="utf-8") == out
        print("up to date" if ok else f"{OUT.relative_to(ROOT)} is not up to date: run tools/check/make_provenance.py")
        raise SystemExit(0 if ok else 1)
    OUT.write_text(out, encoding="utf-8")
    print(f"{len(rows)} files -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
