"""CAPTRD's Aglink-COSIMO sets and mappings (Aglink 2023, DG AGRI), as mapping CSVs for CAPTRD-MOD's stage 2a.

CAPTRD loads the Aglink data in baseline/load_aglink2023dgAgri.gms (captrd.gms l. 593; CAPRI star 3.0). Its sets come
from, in the order GAMS compiles them:
  1  the Aglink data file aglink2023dgAgri_oriEUdata.gdx: c, m, p and m_eq (loaded as m_eq_ini; l. 52-60 of the load)
  2  baseline/aglink2023dgAgri_sets.gms, which includes baseline/mainsets_MTO2023.gms (Aglink's own sets)
  3  global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms (l. 197-198 of the load)
on top of CAPRI's global sets (sets.gms), taken from CAPRI's own instantiation (capri_sources/reference/sets/simini_21730,
tools/build/build_capri_sets_reference.py), as build_captrd_sets.py does.

The data statements of those files are read by tools/lib/gams_sets.py; the set assignments (a few per file) are
transcribed below with their line numbers. The FAO sets that fao_codes_new.gms loads from faodata.gdx are not read
(CAPTRD's Aglink stage does not use them: checked in load_aglink2023dgAgri.gms, which uses no FAO set before its macro
part, l. 902).

Output: capri_data/pipeline/captrd/sets/aglink2023dgAgri/<name>.csv (one column per dimension: d0, d1, ...), the sets
these files declare and the global ones they extend (cols, rows: their full membership after the extension); and _unparsed.csv, the statements left to this builder or not needed (with the decision).

    python tools/build/build_captrd_aglink_sets.py [--gams DIR] [--gdx DIR]
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
import gams_sets as G                                      # noqa: E402
from paths import REFERENCE, SOURCES                       # noqa: E402

OUT = ROOT / "capri_data" / "pipeline" / "captrd" / "sets" / "aglink2023dgAgri"
AGLINK = "aglink2023dgAgri"
#: the compile-time settings these files test (captrd.gms; the reference run results_1770's)
GLOBALS = {"AGLINK": AGLINK, "PGMNAME": "captrd", "COCO2": "NO", "regmap": "off"}
#: the statements the builder transcribes (file, line): handled in _assignments
TRANSCRIBED = {
    ("mainsets_MTO2023.gms", 1781), ("mainsets_MTO2023.gms", 2119), ("mainsets_MTO2023.gms", 2120),
    ("aglink2023dgAgri_sets.gms", 52),
    ("aglink2023dgAgri_sets.gms", 190), ("aglink2023dgAgri_sets.gms", 191), ("aglink2023dgAgri_sets.gms", 195),
    ("aglink2023dgAgri_sets.gms", 198), ("aglink2023dgAgri_sets.gms", 199), ("aglink2023dgAgri_sets.gms", 200),
    ("aglink2023dgAgri_sets.gms", 201), ("aglink2023dgAgri_sets.gms", 202),
    ("aglink2023dgAgri_sets.gms", 432), ("aglink2023dgAgri_sets.gms", 433), ("aglink2023dgAgri_sets.gms", 434),
    ("aglink2023dgAgri_sets.gms", 435), ("aglink2023dgAgri_sets.gms", 436), ("aglink2023dgAgri_sets.gms", 437),
    ("aglink2023dgAgri_sets.gms", 439), ("aglink2023dgAgri_sets.gms", 447), ("aglink2023dgAgri_sets.gms", 449),
    ("aglink2023dgAgri_mappings.gms", 36), ("aglink2023dgAgri_mappings.gms", 37),
    ("aglink2023dgAgri_mappings.gms", 218), ("aglink2023dgAgri_mappings.gms", 221),
    ("aglink2023dgAgri_mappings.gms", 267), ("aglink2023dgAgri_mappings.gms", 269),
    ("aglink2023dgAgri_mappings.gms", 359), ("aglink2023dgAgri_mappings.gms", 360),
    ("aglink2023dgAgri_mappings.gms", 361),
}
#: statements not needed for CAPTRD's sets: checks, displays, parameters, the FAO sets of faodata.gdx
NOT_NEEDED = "check, display, parameter or FAO statement (not a set CAPTRD's Aglink stage reads)"


def _gdx_sets(gdx_dir: Path, gs: G.GamsSets) -> None:
    import pandas as pd
    for sym, name in (("c", "c"), ("m", "m"), ("p", "p"), ("m_eq", "m_eq_ini")):
        d = pd.read_parquet(gdx_dir / f"{sym}.parquet")
        gs.put(name, [(x,) for x in d["d1"]])


def _k(m):
    return tuple(G.key(x) for x in m)


def _add(gs: G.GamsSets, name: str, members) -> None:
    cur = gs.get(name) if gs.has(name) else []
    gs.put(name, list(cur) + list(members))


def _remove(gs: G.GamsSets, name: str, keys) -> None:
    ks = {_k(m) for m in keys}
    gs.put(name, [m for m in gs.get(name) if _k(m) not in ks])


def _pre_sets_assignments(gs: G.GamsSets) -> None:
    """Statements of mainsets_MTO2023.gms and aglink2023dgAgri_sets.gms needed before the later declarations."""


def _assignments(gs: G.GamsSets) -> None:
    """The set assignments, in GAMS's order."""
    # mainsets_MTO2023.gms l. 1781-1784: m_eq = m_eq_ini + not_m_eq (the declaration's data; read by hand because
    # m_eq_ini comes from the GDX file); l. 1785 Alias(m_eq, MMM, MMM1, MMM2) is applied by the reader
    gs.put("m_eq", list(gs.get("m_eq_ini")) + list(gs.get("not_m_eq")))
    for a in ("MMM", "MMM1", "MMM2"):
        gs.aliases[G.key(a)] = G.key("m_eq")
    # l. 2119-2120
    _add(gs, "AGLCOSnoEUNC", gs.get("AGLCOSallC"))
    _remove(gs, "AGLCOSnoEUNC", [("EUN",)])
    # aglink2023dgAgri_sets.gms l. 52-59: aglinkCols = MMM + three aggregates
    gs.put("aglinkCols", list(gs.get("MMM")) + [("QP..CG",), ("QP..NAGR",), ("QP..SEC",)])


def _assignments_sets(gs: G.GamsSets) -> None:
    rm = {_k(m) for m in gs.get("regions_map")}
    # aglink2023dgAgri_sets.gms l. 190-202
    _add(gs, "agEUreg", [("EUN",)])
    _add(gs, "agEUreg", [m for m in gs.get("CCC") if (G.key("EUN"), G.key(m[0])) in rm])
    _add(gs, "agEUparts", [m for m in gs.get("CCC") if (G.key("EUN"), G.key(m[0])) in rm])
    _add(gs, "agEurop", gs.get("agEUreg"))
    _add(gs, "agEurop", [("TUR",), ("GBR",), ("NOR",), ("EUE",)])
    # l. 432-449 (agColsSummable: its declaration's data first, then these)
    _remove(gs, "agColsSummable", [("FO..SHR",)])
    _add(gs, "agColsSummable", gs.get("agcolsFrm"))
    _remove(gs, "agColsSummable", [("YLD",)])
    _add(gs, "agColsSummable", [("POP",)])
    _add(gs, "agColsSummable", gs.get("agBioVar"))
    _remove(gs, "agColsSummable", [("BF..BD..CONV",), ("BF..ET..CONV",), ("MBD",), ("BD..ADJ",)])


def _assignments_mappings(gs: G.GamsSets) -> None:
    # aglink2023dgAgri_mappings.gms l. 36-37
    _add(gs, "rmAggSup", [("EU013000",), ("EU014000",)])
    # l. 218, 221
    mapped = {G.key(b) for _, b in gs.get("AglinkRegions_map")}
    gs.put("AglinkRegionsMapped", [m for m in gs.get("AglinkRegions") if G.key(m[0]) in mapped])
    gs.put("AglinkRegionsNotMapped", [m for m in gs.get("AglinkRegions") if G.key(m[0]) not in mapped])
    # l. 267, 269
    cm = gs.get("aglinkCols_map")
    gs.put("ColsMappedAglink", [m for m in gs.get("cols") if G.key(m[0]) in {G.key(a) for a, _ in cm}])
    n_cols = {}
    for a, b in cm:
        n_cols[G.key(b)] = n_cols.get(G.key(b), 0) + 1
    gs.put("aglinkColsMapped", [m for m in gs.get("aglinkCols") if n_cols.get(G.key(m[0]), 0) == 1])
    # l. 359-361
    rmap = gs.get("aglinkRows_map")
    gs.put("RowsMappedAglink", [m for m in gs.get("rows") if G.key(m[0]) in {G.key(a) for a, _ in rmap}])
    n_rows = {}
    for a, b in rmap:
        n_rows[G.key(b)] = n_rows.get(G.key(b), 0) + 1
    gs.put("aglinkRowsMapped", [m for m in gs.get("aglinkRows") if n_rows.get(G.key(m[0]), 0) == 1] + [("FH",)])


def build(gams: Path, gdx: Path, ref: Path) -> G.GamsSets:
    import pandas as pd
    base = G.GamsSets()
    for f in sorted(ref.glob("*.csv")):
        d = pd.read_csv(f, keep_default_na=False, dtype=str)
        cols = [c for c in d.columns if c.startswith("d")]
        base.put(f.stem, [tuple(r) for r in d[cols].itertuples(index=False)])
    _gdx_sets(gdx, base)
    glob = dict(GLOBALS, curdir=str(gams))
    known = {k: len(v) for k, v in base.sets.items()}
    # 2: the sets file, which includes mainsets_MTO2023.gms; m_eq needs its data by hand (l. 1781), and aglinkCols
    # (l. 52) needs MMM: the reader leaves both unparsed, filled in after it, and the later statements that use them
    # are read in a second pass
    gs = G.read(gams / "baseline" / f"{AGLINK}_sets.gms", gams, glob, base)
    _assignments(gs)
    unparsed = list(gs.unparsed)
    gs.unparsed = []
    gs = G.read(gams / "baseline" / f"{AGLINK}_sets.gms", gams, glob, gs)      # second pass, with MMM and aglinkCols
    _assignments(gs)
    _assignments_sets(gs)
    unparsed = list(gs.unparsed)
    gs = G.read(gams / "global" / "fao_codes_new.gms", gams, glob, gs)
    gs = G.read(gams / "baseline" / f"{AGLINK}_mappings.gms", gams, glob, gs)
    _assignments_mappings(gs)
    gs.unparsed = unparsed + gs.unparsed[len(unparsed):]
    # the sets these files declare, and CAPRI's global sets they extend (cols and rows, l. 63-64 of the mappings)
    gs.declared = sorted(k for k in gs.sets if k not in known or len(gs.sets[k]) != known[k])
    return gs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gams", type=Path, default=SOURCES.parent / "capri_sources" / "course_capri_git" / "gams")
    ap.add_argument("--gdx", type=Path, default=SOURCES.parent / "capri_sources" / "dat_parquet" / "baseline"
                    / f"{AGLINK}_oriEUdata")
    ap.add_argument("--ref", type=Path, default=REFERENCE / "sets" / "simini_21730")
    a = ap.parse_args()
    gs = build(a.gams, a.gdx, a.ref)
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.csv"):
        old.unlink()
    for k in gs.declared:
        mem = gs.sets[k]
        n = max((len(m) for m in mem), default=1)
        with open(OUT / f"{gs.names.get(k, k)}.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow([f"d{i}" for i in range(n)])
            w.writerows(mem)
    with open(OUT / "_aliases.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["alias", "set"])
        w.writerows(sorted((a_, s_) for a_, s_ in gs.aliases.items() if s_ in set(gs.declared) or a_ in set(gs.declared)))
    with open(OUT / "_unparsed.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["file", "line", "statement", "handled"])
        for f, n, s in gs.unparsed:
            fn = Path(f).name
            w.writerow([fn, n, " ".join(s.split())[:200], "transcribed" if (fn, n) in TRANSCRIBED else NOT_NEEDED])
    print(f"{len(gs.declared)} sets -> {OUT}")


if __name__ == "__main__":
    main()
