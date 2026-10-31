"""Locations for the tools: the repository root and any tool by name, wherever it sits under tools/.

    tools/build   builders of the model's data files (capri_data/)
    tools/run     model runs
    tools/check   comparisons and diagnostics
    tools/gams    GAMS export scripts to run in a CAPRI installation
    tools/solvers builds of solver libraries outside the repository (IPOPT with SPRAL in OpenMP)
    tools/lib     modules shared by the tools (_model_regions, _capri_costsavings, this one)

ROOT is found by looking upward for pyproject.toml, so a tool keeps working if it moves between these folders.

CAPRI's own material that the builders read is not in the repository (its size and its licence): it goes in the folder
capri_sources/ at the repository root (not committed), or in the folder the environment variable CAPRI_SOURCES names.
Every location is relative to that folder, never to a particular machine; docs/EXTERNAL_SOURCES.md lists each file,
what it is and where it comes from. CAPRI's files converted for the parity tests stay in capri_reference/ (REFERENCE).
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
TOOLS = ROOT / "tools"
FOLDERS = ("lib", "build", "run", "check", "gams", "solvers")

#: CAPRI's material outside the repository (docs/EXTERNAL_SOURCES.md): capri_sources/ or $CAPRI_SOURCES
SOURCES = Path(os.environ["CAPRI_SOURCES"]).expanduser().resolve() if os.environ.get("CAPRI_SOURCES") \
    else ROOT / "capri_sources"
#: CAPRI's exports as delivered (result listings, market and elasticity exports, GAMS-dumped inputs)
EXPORTS = SOURCES / "exports"
#: CAPRI's files converted for the parity tests (tools/build/build_*_reference.py; not committed)
REFERENCE = ROOT / "capri_reference"

#: the folders under SOURCES and what each holds (the CAPRI archive or export it is unpacked from)
LAYOUT = {
    "exports": "CAPRI's exports as delivered, one file each (res_2_1730*.csv/.zip, markmarket_*.txt, elas_*.csv, "
               "data_market_*.csv, fao_agg_17_*.txt, LitRev*.csv, ...)",
    "gams": "CAPRI's GAMS source tree (gams.zip)",
    "capreg": "CAPREG's 2017 results res_17<MS>.txt, gdxdump listings (res_17zip.zip)",
    "capri_export": "CAPREG's DATA2 per country, DATA2_<CC>.txt (capri_export_zip.zip)",
    "pmp2030": "CAPRI's 2030 PMP terms pmppar_21730<CC>defaulta.txt and estnlp_results_*.txt "
               "(tools/gams/export_pmp_2030.gms)",
    "feed_export": "CAPRI's feed PMP terms pmppar_17<CC>_feedpmp.csv (feed_export.zip)",
    "land_export": "CAPRI's land-market terms pmppar_17<CC>_*.csv (land_export.zip)",
    "supelas": "CAPRI's supply elasticities supply_elas_2_1720<CC>defaulta.txt "
               "(supply_elas_2_1720REMAINI_NGdefaulta.zip and the single files)",
    "estnlp": "CAPRI's estnlp estimates estnlp_*.txt (estnlp-gtap-trade.zip)",
    "fert": "gdxdump of p_CropNutNeedMultFact, multfact_1730.txt (tools/build/build_overfert_factors.py)",
    "costsavings": "CAPRI's cost savings costsavings_{ini,max}_21730_jul15.csv (costsavings_ini_21730_jul15.zip)",
    "dat": "CAPRI's dat folder as parquet (the project's mirror)",
    "gdxlib": "the GDX library libgdxcclib64.so (open source, README section 3), for the builders that read .gdx files",
}


def hint(path) -> str:
    """Where a file of CAPRI's material belongs and where it comes from ("" for any other file)."""
    p = Path(path)
    for loc, name in ((REFERENCE, "capri_reference"), (SOURCES, "capri_sources")):
        try:
            rel = p.relative_to(loc)
        except ValueError:
            continue
        origin = LAYOUT.get(rel.parts[0], "") if loc == SOURCES and rel.parts else \
            "CAPRI's files converted for the parity tests (capri_reference/README.md)"
        return (f"{p} belongs to CAPRI's material, not in git: {name}/" + (f"{rel.parts[0]}/ holds {origin}" if origin
                else "") + ". See docs/EXTERNAL_SOURCES.md (capri_sources may be elsewhere: CAPRI_SOURCES).")
    return ""


def need(path, what: str = "") -> Path:
    """The path, or a FileNotFoundError that says where the file belongs and where it comes from."""
    p = Path(path)
    if p.exists():
        return p
    raise FileNotFoundError(f"{what + ': ' if what else ''}{p} not found. {hint(p)}".rstrip())


_excepthook = sys.excepthook


def _missing_source_hint(kind, exc, tb):
    """A tool that stops on a missing file of CAPRI's material also says where the file belongs and comes from."""
    _excepthook(kind, exc, tb)
    if issubclass(kind, FileNotFoundError) and getattr(exc, "filename", None) and hint(exc.filename):
        print(hint(exc.filename), file=sys.stderr)


sys.excepthook = _missing_source_hint


def tool_file(name: str) -> Path:
    """The file of a tool given its name (with or without .py)."""
    fn = name if name.endswith((".py", ".gms", ".sh")) else f"{name}.py"
    for d in FOLDERS:
        p = TOOLS / d / fn
        if p.exists():
            return p
    raise FileNotFoundError(f"no tool {fn} under {TOOLS} ({', '.join(FOLDERS)})")


def load_tool(name: str):
    """Import a tool as a module by name (the way several builders reuse each other's functions)."""
    p = tool_file(name)
    spec = importlib.util.spec_from_file_location(p.stem, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def add_tool_folders_to_path() -> None:
    for d in reversed(FOLDERS):
        s = str(TOOLS / d)
        if s not in sys.path:
            sys.path.insert(0, s)
