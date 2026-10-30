"""Does every builder reproduce the files it wrote? (builder reproduction audit, K82 follow-up, 27 October 2026)

Each builder of tools/build is run on its own, on a clean checkout (the committed inputs), and the files it changes
are compared with the committed ones. A builder whose run leaves its outputs as committed reproduces them; a
difference means the committed file does not follow from its builder and the committed inputs (stale output, or a
builder changed after the file was written). Run one at a time, every builder sees the committed state, so the result
does not depend on a run order; the committed state is reproducible as a whole when every builder reproduces its own
files.

    python tools/check/reproduce_builders.py REPORT.csv [--only NAME ...] [--timeout S]
    python tools/check/reproduce_builders.py REPORT.csv --chain --only A B ...   (the writers of one file, in order)
    python tools/check/reproduce_builders.py REPORT.csv --chain --keep          (rebuild: every builder in order, the
                                                                                 outputs left in the tree to commit)

The working tree must be a clean git checkout: after each builder the tree is reset (git checkout, git clean of
capri_data). The external inputs (CAPRI dumps and the project lead's uploads) are looked up under UP and WORK below;
a builder whose input is absent is reported as not run. INVOCATIONS records the command of every builder.

Comparison of a changed file with its committed version: CSV (also .csv.xz/.gz) and Parquet as tables (same columns
and rows, numbers to rel. 1e-12 and abs. 1e-15, text equal), JSON as nested values with the same tolerance, other files
byte by byte. "equal values" means the file's bytes changed (formatting, order of rows) but not its content;
"identical (rewritten)" a file the builder wrote with the same bytes (the report lists every file a builder writes).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
UP = Path(os.environ.get("CAPRI_UPLOADS", "/mnt/user-data/uploads"))
WORK = Path(os.environ.get("CAPRI_WORK", "/home/claude/work"))
D17 = WORK / "capreg"                       # res_17<CC>.txt dumps of CAPREG's 2017 base (DATA2)
GAMS = WORK / "allgms" / "gams"             # CAPRI's GAMS code
REF = UP / "res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv"
SETS = WORK / "capri_reference" / "sets" / "simini_21730"   # CAPRI's sets (capri_reference/README.md), not in git
BP = "capri_data/sources/baseline_pmp"
S = "capri_data/2017/supply"

#: (builder, arguments, external inputs that must exist). Order: REGIONAL_UNITS_BUILDERS.md section 3, then the rest.
INVOCATIONS: list[tuple[str, list[str], list[Path]]] = [
    # the CSV conversion of the sources that were not CSV (reads the originals from git history)
    ("convert_sources_to_csv", [], []),
    ("extract_gd2030_nbalance", [], [REF]),
    ("build_regional_units", [], []),
    ("build_code_lists", ["--sets", str(SETS)], [SETS]),
    ("build_unit_catalogue", ["--gms", str(GAMS / "CAPRIunits.gms")], [GAMS / "CAPRIunits.gms"]),
    ("extract_all_from_data2", ["--export-dir", str(WORK / "inputs/capri_export_zip/capri_export")],
     [WORK / "inputs/capri_export_zip/capri_export"]),
    ("extract_remaining_nine", ["--export-dir", str(WORK / "inputs/capri_export_zip/capri_export")],
     [WORK / "inputs/capri_export_zip/capri_export"]),
    ("ingest_pmp_terms", ["--export-dir", str(WORK / "inputs/capri_export_zip/capri_export")],
     [WORK / "inputs/capri_export_zip/capri_export"]),
    ("ingest_pela_gtap", ["--dump-dir", str(WORK / "inputs/estnlp")], [WORK / "inputs/estnlp"]),
    ("build_supply_elasticities_regional", [], []),
    ("build_capri_base", [str(D17)], [D17]),
    ("build_crop_economics_2017", [str(D17)], [D17]),
    ("build_nutrient_coefs_regional", [str(D17)], [D17]),
    ("build_cap_ceilings_2030", [], [REF]),
    ("build_capri_baseline_surplus", [], []),
    ("build_cover_crops", [], [GAMS]),
    ("build_land_market", ["--year", "2017"], [D17, WORK / "landexp/land_export"]),
    ("build_land_market", ["--year", "2030"], [REF]),
    ("build_land_rents", ["--year", "2017"], [D17]),
    ("build_land_rents", ["--year", "2030"], [REF]),
    ("build_manure_losses", [], [UP / "res_2_1730greendeal_refdefaulta.zip"]),
    ("build_manure_trade_base", [], [REF]),
    ("build_nh3_factors", [], [WORK / "nh3/nh3_rows.txt"]),
    ("build_overfert_factors", [str(WORK / "inputs/fert/multfact_1730.txt")], [WORK / "inputs/fert/multfact_1730.txt"]),
    ("build_plant_protection_cost", [], [D17]),
    # the ammonia chain in dependency order (K88 census, 28 October 2026): CAPRI's ammonia input tables first, the cost
    # curves and technologies (whose intermediate the N loss cascade reads), the cascade (read by the fertiliser side
    # effects and the AD option), the AD option (read by the technology model), the technology model
    ("build_ammonia_cost_tables", [str(GAMS / "envind/ammo_tech.gms")], [GAMS / "envind/ammo_tech.gms"]),
    ("build_ammonia_herd_inputs", [str(UP / "scen.zip"), str(UP / "gd_full.zip")], [UP / "scen.zip", UP / "gd_full.zip"]),
    ("build_ammonia_tech_inputs", [str(UP / n) for n in ("LitRev_non_changeable_parameters.csv", "LitRev_inputs.csv",
                                                         "LitRev_input_manStor.csv", "LitRevAmmoTech.csv",
                                                         "holdingsLSU.csv", "nvzShare_LU.csv")],
     [UP / "LitRev_inputs.csv"]),
    ("build_ammonia_cost_curves", [], []),
    ("build_ammonia_technologies", [], []),
    ("build_n_cascade", [], []),
    ("build_fert_side_effects", [], []),
    ("build_ad_option", [], []),
    ("build_ammonia_tech_model", [], []),
    ("build_pmp_2030", [], [WORK / "up/pmp2030"]),
    ("build_pmp_recipe", ["--year", "2017"], [D17, REF]),
    ("build_pmp_recipe", ["--year", "2030"], [D17, REF]),
    ("build_pmp_capri_2030", [], [REF]),
    ("build_pmp_capri_2030", ["--techn", f"{BP}/recipe_2017_quad_techn.csv", "--year", "2017",
                              "--out", f"{S}/pmp_recipe_2017.csv"], [D17]),
    ("build_pmp_capri_2030", ["--techn", f"{BP}/recipe_2030_quad_techn.csv", "--year", "2030",
                              "--out", f"{S}/pmp_recipe_2030.csv"], [REF]),
    ("build_intensity_q_2030", [], []),
    ("build_trajectory_capri_ref", [], [REF, D17]),
    ("build_winter_cover_option", [], []),
    ("build_manure_n2o", [], [D17]),
    ("build_capri_level_ratio", [], [D17]),
    ("build_livestock_output_coef", [str(D17)], [D17]),
    ("build_livestock_premium_coef", [str(D17)], [D17]),
    ("build_livestock_n_export_coef", [], [D17]),
    ("build_ghg_coefs_2017", [str(D17)], [D17]),
    ("build_npk_balance_2030", [], [UP / "res_2_1730greendeal_refdefaulta.zip", D17]),
    ("build_young_animals", [], [D17]),
    ("build_feed_ration", [], [D17, WORK / "feedexp/feed_export"]),
    ("build_ration_trajectory_2030", [], [REF, D17]),
    ("build_price_trajectory_2030", [], [D17]),
    ("build_dairy_intensity", [], [D17]),
    ("build_cattle_intensity", [], [D17]),
    ("build_grass_intensity", [], [D17]),
    ("build_animal_pmp_capri_2030", [], [REF]),
    ("build_animal_pmp_capri_2030", ["--splits"], [REF]),
    ("build_animal_pmp_capri_2030", ["--techn", f"{BP}/recipe_2017_quad_techn.csv", "--year", "2017",
                                     "--out", f"{S}/pmp_recipe_2017_animals.csv"], [D17]),
    ("build_animal_pmp_capri_2030", ["--techn", f"{BP}/recipe_2017_quad_techn.csv", "--year", "2017", "--splits",
                                     "--out", f"{S}/pmp_recipe_2017_animals_members.csv"], [D17]),
    ("build_animal_pmp_capri_2030", ["--techn", f"{BP}/recipe_2030_quad_techn.csv", "--year", "2030",
                                     "--out", f"{S}/pmp_recipe_2030_animals.csv"], [REF]),
    ("build_animal_pmp_capri_2030", ["--techn", f"{BP}/recipe_2030_quad_techn.csv", "--year", "2030", "--splits",
                                     "--out", f"{S}/pmp_recipe_2030_animals_members.csv"], [REF]),
    ("build_labour_setaside", [], [D17, REF]),
    ("build_livestock_units", [], [D17]),
    ("build_fodder_balance", [], []),
    ("build_histosol", [], [GAMS]),
    ("build_lownfeed_effects", [], [UP / "animReq_SK.zip", D17]),
    ("build_livestock_products", [], [D17]),
    ("build_eu_producer_prices", [], []),
    ("build_digestibility_table", [str(GAMS)], [GAMS / "envind" / "def_digestibility.gms"]),
    ("build_supplement_effects", [], [WORK / "capreg"]),
    ("build_genetics_effects", [], [D17]),
    # not region-keyed, or member-state / market / CAPRI-coded
    ("build_active_technologies", [str(GAMS / "pol_input/greendeal/refpol_endotech_all_sup.gms")],
     [GAMS / "pol_input/greendeal/refpol_endotech_all_sup.gms"]),
    ("build_bilateral_market", [], [UP / "market_base_1717.txt"]),
    ("build_bilateral_market", ["--eu-blocks"], [UP / "market_base_1717.txt"]),
    ("build_biofuel_market", ["--year", "2017", "--dump", str(UP / "market_base_1717.txt"),
                              "--elas", str(UP / "elas_2_1717defaulta.csv")],
     [UP / "market_base_1717.txt", UP / "elas_2_1717defaulta.csv"]),
    ("build_biofuel_market", ["--year", "2030", "--dump", str(UP / "markmarket_greendeal_1730et_base_1717.txt"),
                              "--elas", str(UP / "elas_2_1730defaulta.csv")],
     [UP / "markmarket_greendeal_1730et_base_1717.txt", UP / "elas_2_1730defaulta.csv"]),
    ("build_cap_greening", [], [D17]),
    ("build_capri_eu27_levels", [str(UP / "markmarket_greendeal_1730et_base_1717.txt"), str(WORK / "capreg")],
     [UP / "markmarket_greendeal_1730et_base_1717.txt", WORK / "capreg"]),
    ("build_capri_crop_n_coefs", [str(UP / "res_2_1730greendeal_refdefaulta.zip")],
     [UP / "res_2_1730greendeal_refdefaulta.zip"]),
    ("build_capri_gnb_components", [str(UP / "res_2_1730greendeal_refdefaulta.zip")],
     [UP / "res_2_1730greendeal_refdefaulta.zip"]),
    ("build_crop_cost_shares", [], [D17]),
    ("build_crushing_parameters", ["--year", "2017", "--market", str(UP / "market_base_1717.txt"),
                                   "--elas", str(UP / "elas_2_1717defaulta.csv")],
     [UP / "market_base_1717.txt", UP / "elas_2_1717defaulta.csv"]),
    ("build_crushing_parameters", ["--year", "2030", "--market", str(UP / "markmarket_greendeal_1730et_base_1717.txt"),
                                   "--elas", str(UP / "elas_2_1730defaulta.csv")],
     [UP / "markmarket_greendeal_1730et_base_1717.txt", UP / "elas_2_1730defaulta.csv"]),
    ("build_dairy_processing", [], []),
    ("build_dairy_world_blocks", [], []),
    ("build_dairy_world_markets", [], []),
    ("build_enteric_feed_factors", [str(GAMS), str(D17)], [GAMS, D17]),
    ("build_eu_ms_balance", [], []),
    ("build_feed_bulks", [], []),
    ("build_feed_byproducts", [], []),
    ("build_world_prices", [], [UP / "fao_agg_17_datamarket.txt", D17]),
    ("build_eu_cake_feed", [], [UP / "fao_agg_17_datamarket.txt"]),
    ("build_feed_energy", [], [UP / "data_market_1730defaulta.csv"]),
    ("build_noneu_feed_nq", [], [UP / "data_market_1730defaulta.csv", UP / "elas_2_1730defaulta.csv"]),
    ("build_greendeal_targets", ["--gams", str(GAMS), "--gdxlib", str(WORK / "gdxlib")], [GAMS / "pol_input" / "greendeal"]),
    ("build_eu_market_blocks", ["--agg", str(GAMS / "aggregation" / "defaultA.agg")], [GAMS / "aggregation" / "defaultA.agg"]),
    ("build_organic_yield_gap", ["--xlsx", str(UP / "yield_effects_ppp.xlsx")], [UP / "yield_effects_ppp.xlsx"]),
    ("build_yield_price_elasticity", ["--gams", str(GAMS)], [GAMS / "supply" / "yield_elas.gms", GAMS / "global" / "fromimpact" / "sets.gms"]),
    ("build_mineral_n_price", [str(D17)], [D17]),
    ("build_pmp_own_price_elasticities", ["--dump-dir", str(WORK / "inputs" / "estnlp")], [WORK / "inputs" / "estnlp"]),
    ("build_capri_supply_elas_market", ["--src", str(UP / "p_elasSupp.txt")], [UP / "p_elasSupp.txt"]),
    ("build_capreg_national_prices", [str(D17)], [D17]),
    ("build_capri_own_price_elasticities", ["--src", str(UP)], [UP]),
    ("build_captrd_trajectory", ["--series", str(WORK / "capri_reference/captrd_results/1770/series.csv.gz")],
     [WORK / "capri_reference/captrd_results/1770/series.csv.gz"]),
    ("build_captrd_dat", [], [WORK / "hf_capri/dat/baseline/ageline/ageline.parquet"]),
    ("build_feed_demand_nonEU", [], [UP / "elas_2_1730defaulta.csv", UP / "data_market_1730defaulta.csv"]),
    ("build_fert_dist_priors", [], []),
    ("build_fert_options_jul15", [], []),
    ("build_gl_demand", [], [UP / "elas_2_1730defaulta.csv"]),
    ("build_irrigation_2017", [], []),
    ("build_luc_2030", [], [UP / "res_2_1730greendeal_refdefaulta.zip"]),
    ("build_manure_pool_costs", ["--dist", str(UP / "nuts2_center_distance.csv")], [UP / "nuts2_center_distance.csv"]),
    ("build_mineral_redu_rules", [], []),
    ("build_mitigation_inputs", [str(UP)], [UP / "trends_1730.csv"]),
    ("build_n_deposition_substitution", [], []),
    ("build_n_leaching", [], []),
    ("build_nuts2024_reporting", [], []),
    ("build_p_balance", [], []),
    ("build_processing_nq", [], [UP / "elas_2_1730defaulta.csv", UP / "markmarket_greendeal_1730et_base_1717.txt"]),
    ("build_welfare_base", [], [UP / "elas_2_1730defaulta.csv", UP / "data_market_1730defaulta.csv",
                                 UP / "markmarket_greendeal_1730et_base_1717.txt"]),
    ("build_eu_market_supply_nq", [], [UP / "elas_2_1730defaulta.csv", UP / "data_market_1730defaulta.csv",
                                       UP / "markmarket_greendeal_1730et_base_1717.txt"]),
    ("build_noneu_market_supply_nq", [], [UP / "elas_2_1730defaulta.csv", UP / "data_market_1730defaulta.csv",
                                          UP / "markmarket_greendeal_1730et_base_1717.txt"]),
    ("build_processing_seeds", [], []),
    ("build_processing_yields", [], [UP / "markmarket_greendeal_1730et_base_1717.txt"]),
    ("build_sugar_processing", [], []),
    ("build_supply_elas_nonEU", [], []),
    ("build_tariffs_2017", [], []),
    ("build_use_components", [], []),
    ("build_world_market_baseline", [], []),
    # the zip of the other member states' dumps is extracted first (the builder reads text files): see run()
    ("build_young_animal_elasticities", [str(UP / f"supply_elas_2_1720{c}defaulta.txt") for c in ("DE", "ES", "FR", "IT", "PL")]
     + ["unzip:" + str(UP / "supply_elas_2_1720REMAINI_NGdefaulta.zip")], [UP / "supply_elas_2_1720DEdefaulta.txt"]),
    ("extract_capri_costsavings", [str(WORK / "cs/costsavings_ini_21730_jul15.csv"),
                                   str(WORK / "cs/costsavings_max_21730_jul15.csv")], [WORK / "cs"]),
    ("extract_capri_marginal_terms", [str(REF), "ini"], [REF]),
    ("extract_capri_marginal_terms", [str(WORK / "gd/endomax/res_2_1730greendeal_refpol_endotech_all_maxdefaulta.csv"),
                                      "max"], [WORK / "gd/endomax"]),
    ("ingest_capmod_market", ["--dump", str(UP / "_symbols_base1717.txt")], [UP / "_symbols_base1717.txt"]),
    ("recalibrate_trade_2017", [], []),
]

#: not audited: utilities and writers of capri_reference/ (not committed) or of inputs held elsewhere
NOT_AUDITED = {
    "gdx_dump_symbol": "utility (dumps one GDX symbol)",
    "build_capreg_tseries_reference": "writes capri_reference/ (not committed)",
    "build_capri_sets_reference": "writes capri_reference/ (not committed)",
    "build_captrd_results_reference": "writes capri_reference/ (not committed)",
    "build_eu_outlook_2030": "input (DG AGRI outlook PDF) not held in the workspace",
    "build_n_cascade_validation": "a check, writes a validation table",
    "build_patched_inputs": "superseded one-off (see REGIONAL_UNITS_BUILDERS.md 4.4)",
    "extract_capri_vcs_pair": "input is a GDX inside a zip (cap_after_2014 reference)",
    "build_captrd_sets": "reads capri_reference/sets (not committed; build_capri_sets_reference writes it)",
    "build_trajectory_model_keys": "a module: add_model_keys is called by build_captrd_trajectory (the file's one "
                                   "writer); its command line edits a file in place",
    "build_animal_yields": "a module: build() is called by build_crop_economics_2017, the one writer of yields.csv",
    "convert_inputs_to_parquet": "a conversion step (Parquet decision deferred), not a builder of data",
}

TOL_REL, TOL_ABS = 1e-12, 1e-15


def git(*a: str, check: bool = True) -> str:
    return subprocess.run(["git", *a], cwd=ROOT, check=check, capture_output=True, text=True).stdout


def committed(path: str) -> bytes:
    return subprocess.run(["git", "show", f"HEAD:{path}"], cwd=ROOT, check=True, capture_output=True).stdout


def read_table(path: str, data: bytes) -> pd.DataFrame:
    if path.endswith(".parquet"):
        return pd.read_parquet(BytesIO(data))
    comp = "xz" if path.endswith(".xz") else "gzip" if path.endswith(".gz") else None
    return pd.read_csv(BytesIO(data), compression=comp, keep_default_na=False, dtype=str)


def num_diff(a: pd.Series, b: pd.Series) -> tuple[float, int]:
    """Largest relative difference of two text columns that hold numbers, and the count of differing text cells."""
    x, y = pd.to_numeric(a, errors="coerce"), pd.to_numeric(b, errors="coerce")
    both = x.notna() & y.notna()
    text_diff = int(((a != b) & ~both).sum())
    if not both.any():
        return 0.0, text_diff
    xv, yv = x[both].to_numpy(float), y[both].to_numpy(float)
    d = np.abs(xv - yv)
    s = np.maximum(np.abs(xv), np.abs(yv))
    rel = np.where(d <= TOL_ABS, 0.0, d / np.where(s > 0, s, 1.0))
    return float(rel.max()), text_diff


def compare_table(path: str, old: bytes, new: bytes) -> str:
    a, b = read_table(path, old), read_table(path, new)
    if path.endswith(".parquet"):
        a, b = a.astype(str), b.astype(str)
    if list(a.columns) != list(b.columns):
        if set(a.columns) == set(b.columns):
            b = b[list(a.columns)]
        else:
            return (f"columns differ: -{sorted(set(a.columns) - set(b.columns))[:6]} "
                    f"+{sorted(set(b.columns) - set(a.columns))[:6]}")
    if a.shape != b.shape:
        return f"shape {a.shape} -> {b.shape}"
    key = [c for c in a.columns if pd.to_numeric(a[c], errors="coerce").isna().all()]
    if key:
        a2, b2 = a.sort_values(key, kind="stable").reset_index(drop=True), b.sort_values(key, kind="stable").reset_index(drop=True)
        if (a2[key].to_numpy() == b2[key].to_numpy()).all():
            a, b = a2, b2
    worst, texts, where = 0.0, 0, ""
    for c in a.columns:
        r, t = num_diff(a[c], b[c])
        texts += t
        if r > worst:
            worst, where = r, c
    if worst <= TOL_REL and texts == 0:
        return "equal values"
    return f"max rel diff {worst:.3g} (column {where}); text cells differing {texts}"


def walk(a, b, path="") -> tuple[float, list[str]]:
    if isinstance(a, dict) and isinstance(b, dict):
        worst, notes = 0.0, []
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b:
                notes.append(f"{path}/{k} {'added' if k not in a else 'removed'}")
                continue
            w, n = walk(a[k], b[k], f"{path}/{k}")
            worst, notes = max(worst, w), notes + n
        return worst, notes
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return 0.0, [f"{path} length {len(a)} -> {len(b)}"]
        worst, notes = 0.0, []
        for i, (x, y) in enumerate(zip(a, b)):
            w, n = walk(x, y, f"{path}[{i}]")
            worst, notes = max(worst, w), notes + n
        return worst, notes
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        if (isinstance(a, float) and math.isnan(a)) and (isinstance(b, float) and math.isnan(b)):
            return 0.0, []
        d = abs(a - b)
        return (0.0 if d <= TOL_ABS else d / max(abs(a), abs(b))), []
    return 0.0, ([] if a == b else [f"{path}: {str(a)[:30]} -> {str(b)[:30]}"])


def compare(path: str, old: bytes, new: bytes) -> str:
    if old == new:
        return "identical"
    low = path.lower()
    try:
        if low.endswith((".csv", ".csv.xz", ".csv.gz", ".parquet")):
            return compare_table(path, old, new)
        if low.endswith(".json"):
            w, notes = walk(json.loads(old), json.loads(new))
            if w <= TOL_REL and not notes:
                return "equal values"
            return f"max rel diff {w:.3g}; {len(notes)} other differences {notes[:3]}"
    except Exception as e:  # noqa: BLE001
        return f"not comparable ({type(e).__name__}: {e})"
    return "bytes differ"


_OPEN = __import__("re").compile(r'^\d+\s+openat\(AT_FDCWD, "([^"]+)", ([A-Z_|]+)')
_REN = __import__("re").compile(r'^\d+\s+rename(?:at2?)?\((?:AT_FDCWD, )?"([^"]+)", (?:AT_FDCWD, )?"([^"]+)"')
_SKIP = ("/usr/", "/proc/", "/sys/", "/dev/", "/etc/", "/lib", "/opt/", "/root/", "/var/", "/run/")


def parse_strace(log: Path, tmp: str) -> dict:
    """A builder's strace log as {"reads", "writes", "code", "external"}: files under the repository (relative paths,
    the builder's working directory is the repository) read or written; the Python files it ran (code, the builder's
    own modules and capri_mod); files read outside the repository (CAPRI's sources). Failed opens, directories,
    Python's libraries and the temporary folder of zip arguments are left out. A file whose first access is a read is
    an input, also when the builder writes it afterwards (a read-modify-write, listed under "rewrites" as well)."""
    first, writes, code, ext = {}, set(), set(), set()
    if not log.exists():
        return {"reads": [], "writes": [], "code": [], "external": []}
    for line in log.read_text(errors="replace").splitlines():
        if "= -1" in line:
            continue
        m = _OPEN.match(line)
        if m:
            path, flags = m.group(1), m.group(2)
            if "O_DIRECTORY" in flags:
                continue
            new = [(path, "O_WRONLY" in flags or "O_RDWR" in flags or "O_CREAT" in flags)]
        else:
            m = _REN.match(line)
            if not m:
                continue
            new = [(m.group(1), True), (m.group(2), True)]
        for path, w in new:
            ap_ = Path(path) if path.startswith("/") else ROOT / path
            ap_ = Path(os.path.normpath(ap_))
            sp_ = str(ap_)
            if sp_.startswith(tmp) or sp_.startswith(_SKIP) or "__pycache__" in sp_ or "site-packages" in sp_ \
                    or "dist-packages" in sp_:
                continue
            try:
                rel = str(ap_.relative_to(ROOT))
            except ValueError:
                if not w:
                    ext.add(sp_)
                continue
            if rel.endswith(".py"):
                code.add(rel)
                continue
            first.setdefault(rel, "w" if w else "r")
            if w:
                writes.add(rel)
    reads = {f for f, k in first.items() if k == "r"}
    return {"reads": sorted(reads), "writes": sorted(writes), "rewrites": sorted(reads & writes), "code": sorted(code),
            "external": sorted(ext)}


def snapshot() -> dict:
    """Modification time of every file under capri_data (to see what a builder wrote, also where it wrote the same
    bytes)."""
    return {str(f.relative_to(ROOT)): f.stat().st_mtime_ns for f in (ROOT / "capri_data").rglob("*") if f.is_file()}


def reset():
    git("checkout", "--", ".")
    git("clean", "-fdq", "--", "capri_data", "capri_reference")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--chain", action="store_true", help="run the --only builders in order without resetting between them")
    ap.add_argument("--keep", action="store_true", help="with --chain: leave the outputs in the tree (a rebuild)")
    ap.add_argument("--trace", default="", help="run each builder under strace and write its reads and writes (JSON)")
    o = ap.parse_args()
    if git("status", "--porcelain", "--untracked-files=no").strip():
        sys.exit("the working tree has changes: run on a clean checkout (the tree is reset after each builder)")
    listed = {b for b, _, _ in INVOCATIONS} | set(NOT_AUDITED)
    unlisted = sorted(p.stem for p in (ROOT / "tools" / "build").glob("*.py") if p.stem not in listed)
    if unlisted:
        print("builders without an invocation:", ", ".join(unlisted))
    before = set(git("status", "--porcelain", "--untracked-files=all").splitlines())
    rows = []
    env = {**os.environ, "PYTHONHASHSEED": "0"}

    def run(name, args, needs):
        cmd = " ".join([name, *[a.replace(str(UP), "$UP").replace(str(WORK), "$WORK") for a in args]])
        missing = [str(p) for p in needs if not p.exists()]
        if missing:
            return cmd, "not run: input missing " + "; ".join(missing), ""
        t = time.time()
        # "unzip:Z": the text files of zip Z, extracted to a temporary folder, as arguments
        tmp = tempfile.mkdtemp(prefix="reproduce_builders_")
        full = []
        for a_ in args:
            if a_.startswith("unzip:"):
                with zipfile.ZipFile(a_[6:]) as z_:
                    z_.extractall(tmp)
                    full += sorted(str(Path(tmp) / n_) for n_ in z_.namelist() if not n_.endswith("/"))
            else:
                full.append(a_)
        pre, env_ = [], env
        if o.trace:
            # modules compiled from source into the temporary folder, so every module the builder imports is opened
            # as its .py and recorded as code (with a valid __pycache__ only the cached .pyc is opened, and imported
            # modules - tools/lib, other builders, capri_mod - were missing from the code lists until 29 October 2026)
            env_ = {**env, "PYTHONPYCACHEPREFIX": str(Path(tmp) / "pycache")}
            # every file the builder and its child processes open or rename (strace: also Parquet and other C-level
            # readers that a Python hook does not see)
            pre = ["strace", "-f", "-qq", "-e", "trace=openat,rename,renameat,renameat2", "-o", str(Path(tmp) / "strace.log")]
        try:
            r = subprocess.run(pre + [sys.executable, str(ROOT / "tools" / "build" / f"{name}.py"), *full], cwd=ROOT, env=env_,
                               capture_output=True, text=True, timeout=o.timeout)
            if o.trace:
                traces[cmd] = parse_strace(Path(tmp) / "strace.log", tmp)
            err = r.stderr.strip().splitlines()[-1][:200] if r.stderr.strip() else ""
            status = "ok" if r.returncode == 0 else f"failed (exit {r.returncode}): {err}"
        except subprocess.TimeoutExpired:
            status = f"timeout after {o.timeout} s"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return cmd, status, round(time.time() - t, 1)

    def record(cmd, status, sec, snap0):
        changed = [ln[3:] for ln in git("status", "--porcelain", "--untracked-files=all").splitlines() if ln not in before]
        snap1 = snapshot()
        # files written with the same bytes (git sees no change): reported as written, identical
        for f in sorted(f for f, t in snap1.items() if snap0.get(f) != t and f not in changed):
            rows.append({"builder": cmd, "status": status, "seconds": sec, "file": f, "result": "identical (rewritten)"})
        if not changed and not any(r["builder"] == cmd for r in rows):
            rows.append({"builder": cmd, "status": status, "seconds": sec, "file": "", "result": "no file changed"})
        for f in changed:
            if not git("ls-files", "--", f).strip():
                res = "new file (not committed)"
            elif not (ROOT / f).exists():
                res = "deleted"
            else:
                res = compare(f, committed(f), (ROOT / f).read_bytes())
            rows.append({"builder": cmd, "status": status, "seconds": sec, "file": f, "result": res})
        print(f"{cmd}: {status}, {sec} s, {len(changed)} files changed", flush=True)
        for row in rows:
            if row["builder"] == cmd and row["file"]:
                print(f"    {row['file']}: {row['result']}", flush=True)

    traces = {}
    selected = [inv for inv in INVOCATIONS if not o.only or inv[0] in o.only]
    if o.chain:
        # the selected builders one after the other, without a reset: the writers of one file in their order
        snap0 = snapshot()
        steps = []
        for inv in selected:
            steps.append(run(*inv))
            print(f"{steps[-1][0]}: {steps[-1][1]}, {steps[-1][2]} s", flush=True)
        record("chain: " + " -> ".join(c for c, _, _ in steps),
               "; ".join(f"{c.split()[0]} {st}" for c, st, _ in steps if st != "ok") or "ok",
               round(sum(x for _, _, x in steps if x != ""), 1), snap0)
        if not o.keep:
            reset()
    else:
        for inv in selected:
            snap0 = snapshot()
            cmd, status, sec = run(*inv)
            record(cmd, status, sec, snap0)
            reset()
    with open(o.report, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["builder", "status", "seconds", "file", "result"])
        w.writeheader()
        w.writerows(rows)
    print(f"report: {o.report}")
    if o.trace:
        Path(o.trace).write_text(json.dumps(traces, indent=1, sort_keys=True))
        print(f"trace: {o.trace}")


if __name__ == "__main__":
    main()
