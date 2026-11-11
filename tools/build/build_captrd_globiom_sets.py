"""The sets and mappings of CAPRI's conversion of GLOBIOM-EU's projections into long-run change factors
(global/convert_globiom.gms with --GlobiomVersion=Globiom_EU and the GLOBIOM-EU file of the long-run selection), as CSV.

Source (the project lead's CAPRI installation, docs/EXTERNAL_SOURCES.md): gams/global/convert_globiom.gms and the file
it includes, global/globiom_to_fao_reg.gms. Its $if branches are selected by tools/lib/gams_preproc.py with
GlobiomVersion = Globiom_EU, BAS = 17 and glo_scen = bright (the file sets glo_scen to euclimit7, l. 267; with either the
branches are the same but for the input file's name and the scenario lines, l. 277-286); the set statements of the
selected lines are read by tools/lib/gams_sets.py. MLKSECO (GLOBIOM_TO_ROWS's ALMILK.(set.MLKSECO)) comes from CAPRI's
sets in sim_ini_21730 (capri_reference/sets/simini_21730).

Not here: the sets the GLOBIOM file itself holds (ALLITEM, REGION58, ALLCOUNTRY, REGION58_COUNTRY_MAP, ANIMAL, EU_CROP,
allLC_TYPE, ...), read with its parameters by capri_mod/pipeline/captrd/globiom.py; the sets convert_globiom.gms
assigns in its statements (toFAME, youngHeif, the mapped subsets), transcribed there.

Also transcribed: the GLOBIOM-EU long-run selections convert_globiom.gms knows (its glo_scen options, l. 269-286), with
the GLOBIOM file and the scenario (macroScen, bioEnScen, IEAscen) of each (SelecScen_map).

And CAPRI's sets it uses (CAPRI_SETS), copied from sim_ini_21730's.

Output: capri_data/pipeline/captrd/sets/globiom/<set>.csv (d0[, d1, d2]),
capri_data/pipeline/captrd/dat/globiom_scenarios.csv (scenario, glo_scen, file, macro_scen, bioen_scen, iea_scen).
    python tools/build/build_captrd_globiom_sets.py
"""
from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
import gams_preproc as GP                                  # noqa: E402
import gams_sets as G                                      # noqa: E402
from paths import REFERENCE, SOURCES                       # noqa: E402

GAMS = SOURCES / "course_capri_git" / "gams"
SIMINI = REFERENCE / "sets" / "simini_21730"
OUT = ROOT / "capri_data" / "pipeline" / "captrd" / "sets" / "globiom"
CONTROL = {"GlobiomVersion": "Globiom_EU", "BAS": "17", "BaseYear_lst2": "17"}
#: the sets written, as convert_globiom.gms names them
SETS = ["longYr", "longYrSel", "longYrSelWo00", "PROCPR", "GLOBIOMrows", "vegoil", "GLOBIOM_TO_ROWS", "GLOBIOMcols",
        "GLOBIOMmacro", "Macro", "GLOBIOM_TO_COLS", "YLDFEEDCONV", "POLESregion", "POLES_to_GLOBIOMregion", "MONO",
        "DemPosDis", "TradePos", "MrkPos", "longtext_GLOBIOM_FAOREGMAP"]
#: CAPRI's sets convert_globiom.gms and create_longrun_info.gms use (sets.gms, arm/arm_sets.gms, global/fao_codes_new.gms),
#: copied from the run's instantiation (FAORegions_map as CAPMOD's fao_codes_new.gms leaves it: the trade aggregates'
#: codes, l. 559, are added by globiom.region_map)
CAPRI_SETS = ["RMall", "RW", "RM", "RMS", "RW_TO_RM", "RMS_TO_RM", "NUTS0", "MSALL", "EUAllAgg", "FAORegions",
              "FAORegions_map", "SECOM", "LandUseARTO"]
#: convert_globiom.gms l. 269-286: SelecScen, glo_scen, GLOfilename and SelecScen_map of each GLOBIOM-EU selection
SCENARIOS = [
    ("globiom_eu_nov2020+REFERENCE+REFERENCE", "", "GLOBIOM-EU_EUCLIMIT5_V2FB_25102020", "primes_ref_2020", "REFERENCE",
     "REFERENCE"),
    ("GLOBIOM_EU_EUCLIMIT6_S2_50CV", "euclimit7", "GLOBIOM-EU_EUCLIMIT6_S2_50CV", "primes_CTP2040", "GHG_CO2_50_FIX",
     "REFERENCE"),
    ("globiom_eu_bright_s0_2023+REFERENCE+REFERENCE", "bright", "globiom_eu_bright_s0_2023+REFERENCE+REFERENCE",
     "primes_REFCTP", "REFERENCE", "REFERENCE"),
]
#: the commands whose files the reader cannot open (GDX loads, CAPRI's settings and sets); the FAO mapping is read
SKIP = ("$GDXIN", "$LOAD", "$INCLUDE", "$BATINCLUDE")


def _write(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow([f"d{i}" for i in range(len(rows[0]))])
        w.writerows(rows)
    print(f"{path.relative_to(ROOT)}: {len(rows)} records")


def main() -> None:
    src = (GAMS / "global" / "convert_globiom.gms").read_text(encoding="latin-1")
    src = src.replace("$setlocal glo_scen euclimit7", "$setlocal glo_scen bright")
    r = GP.preprocess(src, CONTROL)
    if r.undecided:
        raise SystemExit(f"undecided conditions: {r.undecided}")
    lines = dict(r.lines)
    keep = lambda s: not s.upper().startswith(SKIP) or "globiom_to_fao_reg" in s      # noqa: E731
    text = "\n".join((lines.get(i, "") if keep(lines.get(i, "")) else "").replace("\\", "/")
                     for i in range(1, max(lines) + 1))
    base = G.GamsSets()
    with open(SIMINI / "MLKSECO.csv", newline="") as fh:
        base.put("MLKSECO", [(row["d0"],) for row in csv.DictReader(fh)])
    base.put("allLC_TYPE", [])                     # ALLITEM's set.allLC_TYPE: the GLOBIOM file's, added by globiom.py
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "convert_globiom_eu.gms"
        p.write_text(text + "\n", encoding="latin-1")
        gs = G.read(p, GAMS, {}, base)
    for n in SETS:
        m = gs.get(n)
        if not m:
            raise SystemExit(f"{n}: no members read")
        if n == "longtext_GLOBIOM_FAOREGMAP":
            m = [(a.strip(), b, c) for a, b, c in m]
        _write(OUT / f"{n.lower()}.csv", m)
    for n in CAPRI_SETS:
        with open(SIMINI / f"{n}.csv", newline="") as fh:
            r = csv.reader(fh)
            hdr = next(r)
            k = sum(1 for h in hdr if h.startswith("d"))
            _write(OUT / f"{n.lower()}.csv", [tuple(row[:k]) for row in r])
    p = ROOT / "capri_data" / "pipeline" / "captrd" / "dat" / "globiom_scenarios.csv"
    with open(p, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["scenario", "glo_scen", "file", "macro_scen", "bioen_scen", "iea_scen"])
        w.writerows(SCENARIOS)
    print(f"{p.relative_to(ROOT)}: {len(SCENARIOS)} records")


if __name__ == "__main__":
    main()
