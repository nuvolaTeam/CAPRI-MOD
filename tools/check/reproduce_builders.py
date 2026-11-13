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
capri_data). The external inputs (CAPRI's exports and dumps) are looked up under capri_sources/ and capri_sources/reference/
(tools/lib/paths.py, docs/EXTERNAL_SOURCES.md);
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
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from paths import BASELINE_REF, EXPORTS, REFERENCE, SOURCES  # noqa: E402  (CAPRI's material: docs/EXTERNAL_SOURCES.md)

D17 = SOURCES / "capreg"                    # res_17<CC>.txt dumps of CAPREG's 2017 base (DATA2)
GAMS = SOURCES / "gams"                     # CAPRI's GAMS code
REF = BASELINE_REF                          # CAPRI's 2030 Green Deal baseline (the model's 2030 base)
INI = EXPORTS / "res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv"   # its calibration run (the N cascade checks)
SETS = REFERENCE / "sets" / "simini_21730"  # CAPRI's sets (docs/EXTERNAL_SOURCES.md), not in git
BP = "capri_data/sources/intermediate/baseline_pmp"
S = "capri_data/2017/supply"
S30 = "capri_data/baselines/capri_greendeal_ref/1730/supply"   # the 2030 inputs (DATA_LAYOUT step (b), 10 November 2026)

#: (builder, arguments, external inputs that must exist). Order: REGIONAL_UNITS_BUILDERS.md section 3, then the rest.
INVOCATIONS: list[tuple[str, list[str], list[Path]]] = [
    # the CSV conversion of the sources that were not CSV (reads the originals from git history)
    ("convert_sources", [], []),
    # CAPRI's dat GDX symbols (as Parquet in capri_sources/dat) and the dat files of the project lead's installation
    # (capri_sources/dat_local), to CSV (added to this list 6 November 2026; written by hand into builders.json before)
    ("extract_capri_dat", [], [SOURCES / "dat"]),
    ("extract_capri_dat_local", [], [SOURCES / "dat_local"]),
    ("extract_gd2030_nbalance", [], [INI]),
    # before its readers (build_cover_crops, build_histosol, build_price_trajectory_2030, ...): a chain rebuild runs
    # the list in order
    ("extract_capri_marginal_terms", [str(REF), "ref"], [REF]),
    # CAPRI's Green Deal 2030 step and its reference, as GDX from the project lead's installation (10 November 2026)
    ("extract_capri_gd_pair", [], [EXPORTS / "res_2_1730greendeal_refdefaulta.gdx",
                                   EXPORTS / "res_2_1730greendeal_lnds8_org18_pest20_mine13crp_surp30_diet00_oth00defaultA.gdx"]),
    ("build_regional_units", [], []),
    ("build_code_lists", ["--sets", str(SETS)], [SETS]),
    ("build_unit_catalogue", ["--gms", str(GAMS / "CAPRIunits.gms")], [GAMS / "CAPRIunits.gms"]),
    ("extract_all_from_data2", ["--export-dir", str(SOURCES / "capri_export")],
     [SOURCES / "capri_export"]),
    ("extract_remaining_nine", ["--export-dir", str(SOURCES / "capri_export")],
     [SOURCES / "capri_export"]),
    ("ingest_pmp_terms", ["--export-dir", str(SOURCES / "capri_export")],
     [SOURCES / "capri_export"]),
    ("ingest_pela_gtap", ["--dump-dir", str(SOURCES / "estnlp")], [SOURCES / "estnlp"]),
    ("build_supply_elasticities_regional", [], []),
    ("build_capri_base", [str(D17)], [D17]),
    ("build_crop_economics_2017", [str(D17)], [D17]),
    ("build_capreg_national_prices", [str(D17)], [D17]),
    ("build_model_premium_prices", [], []),            # after the crop premiums and the national prices
    ("build_nutrient_coefs_regional", [str(D17)], [D17]),
    ("build_cap_ceilings_2030", [], [REF]),
    ("build_capri_baseline_surplus", [], []),
    ("build_cover_crops", [], [GAMS]),
    ("build_land_market", ["--year", "2017"], [D17, SOURCES / "land_export"]),
    ("build_land_market", ["--year", "2030"], [REF]),
    ("build_land_rents", ["--year", "2017"], [D17]),
    ("build_land_rents", ["--year", "2030"], [REF]),
    ("build_manure_losses", [], [EXPORTS / "res_2_1730greendeal_refdefaulta.zip"]),
    ("build_manure_pool_market", [], []),         # from its kept extract (--parquet DIR / --download: the raw)
    ("build_manure_trade_base", [], [REF]),
    ("build_nh3_factors", [], [EXPORTS / "res_2_1730greendeal_refdefaulta.zip"]),
    ("build_overfert_factors", [str(SOURCES / "fert/multfact_1730.txt")], [SOURCES / "fert/multfact_1730.txt"]),
    ("build_plant_protection_cost", [], [D17]),
    # the ammonia chain in dependency order (K88 census, 28 October 2026): CAPRI's ammonia input tables first, the cost
    # curves and technologies (whose intermediate the N loss cascade reads), the cascade (read by the fertiliser side
    # effects and the AD option), the AD option (read by the technology model), the technology model
    ("build_ammonia_cost_tables", [str(GAMS / "envind/ammo_tech.gms")], [GAMS / "envind/ammo_tech.gms"]),
    ("build_ammonia_herd_inputs", [str(EXPORTS / "scen.zip"), str(EXPORTS / "gd_full.zip")], [EXPORTS / "scen.zip", EXPORTS / "gd_full.zip"]),
    ("build_ammonia_tech_inputs", [str(EXPORTS / n) for n in ("LitRev_non_changeable_parameters.csv", "LitRev_inputs.csv",
                                                         "LitRev_input_manStor.csv", "LitRevAmmoTech.csv",
                                                         "holdingsLSU.csv", "nvzShare_LU.csv")],
     [EXPORTS / "LitRev_inputs.csv"]),
    # the non-EU farm structure (envind/prep_farm_size_data_for_miti.gms), from the herd and holding inputs above; read
    # by the cost curves, the technologies and the AD option (added to this list 6 November 2026)
    ("build_farm_size_noneu", [], [GAMS / "envind/prep_farm_size_data_for_miti.gms"]),
    ("build_ammonia_cost_curves", [], []),
    ("build_ammonia_technologies", [], []),
    ("build_n_cascade", [], []),
    ("build_fert_side_effects", [], []),
    ("build_ad_option", [], []),
    ("build_ammonia_tech_model", [], []),
    ("build_pmp_2030", [], [SOURCES / "pmp2030"]),
    ("build_techn_2030", [], [REFERENCE / "simini" / "simini_21730" / "p_pmpCnst.csv.gz",
                              REFERENCE / "simini" / "simini_21730" / "p_technFact.csv.gz"]),
    ("build_techn_mix_2030", [], [REF]),
    ("build_pmp_recipe", ["--year", "2017"], [D17, REF]),
    ("build_pmp_recipe", ["--year", "2030"], [D17, REF]),
    ("build_pmp_capri_2030", [], [REF]),
    ("build_pmp_capri_2030", ["--techn", f"{BP}/recipe_2017_quad_techn.parquet", "--year", "2017",
                              "--out", f"{S}/pmp_recipe_2017.csv"], [D17]),
    ("build_pmp_capri_2030", ["--techn", f"{BP}/recipe_2030_quad_techn.parquet", "--year", "2030",
                              "--out", f"{S30}/pmp_recipe_2030.csv"], [REF]),
    ("build_intensity_q_2030", [], []),
    ("build_trajectory_capri_ref", [], [REF, D17]),
    ("build_winter_cover_option", [], []),
    ("build_manure_n2o", [], [D17]),
    ("build_capri_level_ratio", [], [D17]),
    ("build_livestock_output_coef", [str(D17)], [D17]),
    ("build_livestock_premium_coef", [str(D17)], [D17]),
    ("build_livestock_n_export_coef", [], [D17]),
    ("build_ghg_coefs_2017", [str(D17)], [D17]),
    ("build_npk_balance_2030", [], [EXPORTS / "res_2_1730greendeal_refdefaulta.zip", D17]),
    ("build_young_animals", [], [D17]),
    ("build_feed_ration", [], [D17, SOURCES / "feed_export"]),
    ("build_ration_trajectory_2030", [], [REF, D17]),
    ("build_price_trajectory_2030", [], [D17]),
    ("build_dairy_intensity", [], [D17]),
    ("build_cattle_intensity", [], [D17]),
    ("build_animal_pmp_capri_2030", [], [REF]),
    ("build_animal_pmp_capri_2030", ["--splits"], [REF]),
    ("build_animal_pmp_capri_2030", ["--techn", f"{BP}/recipe_2017_quad_techn.parquet", "--year", "2017",
                                     "--out", f"{S}/pmp_recipe_2017_animals.csv"], [D17]),
    ("build_animal_pmp_capri_2030", ["--techn", f"{BP}/recipe_2017_quad_techn.parquet", "--year", "2017", "--splits",
                                     "--out", f"{S}/pmp_recipe_2017_animals_members.csv"], [D17]),
    ("build_animal_pmp_capri_2030", ["--techn", f"{BP}/recipe_2030_quad_techn.parquet", "--year", "2030",
                                     "--out", f"{S30}/pmp_recipe_2030_animals.csv"], [REF]),
    ("build_animal_pmp_capri_2030", ["--techn", f"{BP}/recipe_2030_quad_techn.parquet", "--year", "2030", "--splits",
                                     "--out", f"{S30}/pmp_recipe_2030_animals_members.csv"], [REF]),
    ("build_labour_setaside", [], [D17, REF]),
    ("build_livestock_units", [], [D17]),
    ("build_fodder_balance", [], []),
    ("build_histosol", [], [GAMS]),
    ("build_lownfeed_effects", [], [EXPORTS / "animReq_SK.zip", D17]),
    ("build_livestock_products", [], [D17]),
    ("build_eu_producer_prices", [], []),
    ("build_digestibility_table", [str(GAMS)], [GAMS / "envind" / "def_digestibility.gms"]),
    ("build_fert_partial_slack", [str(GAMS)], [GAMS / "supply" / "set_fert_priors.gms"]),
    ("build_set_aside_scenario", [str(GAMS)], [GAMS / "scen" / "set_aside" / "set_aside_10.gms", GAMS / "sets.gms"]),
    ("build_supplement_effects", [], [SOURCES / "capreg"]),
    ("build_genetics_effects", [], [D17]),
    # not region-keyed, or member-state / market / CAPRI-coded
    ("build_active_technologies", [str(GAMS / "pol_input/greendeal/refpol_endotech_all_sup.gms")],
     [GAMS / "pol_input/greendeal/refpol_endotech_all_sup.gms"]),
    ("build_bilateral_market", [], [EXPORTS / "market_base_1717.txt"]),
    ("build_biofuel_market", ["--year", "2017", "--dump", str(EXPORTS / "market_base_1717.txt"),
                              "--elas", str(EXPORTS / "elas_2_1717defaulta.csv")],
     [EXPORTS / "market_base_1717.txt", EXPORTS / "elas_2_1717defaulta.csv"]),
    ("build_biofuel_market", ["--year", "2030", "--dump", str(EXPORTS / "markmarket_greendeal_1730et_base_1717.txt"),
                              "--elas", str(EXPORTS / "elas_2_1730defaulta.csv")],
     [EXPORTS / "markmarket_greendeal_1730et_base_1717.txt", EXPORTS / "elas_2_1730defaulta.csv"]),
    ("build_cap_greening", [], [D17]),
    ("build_capri_eu27_levels", [str(EXPORTS / "markmarket_greendeal_1730et_base_1717.txt"), str(SOURCES / "capreg")],
     [EXPORTS / "markmarket_greendeal_1730et_base_1717.txt", SOURCES / "capreg"]),
    ("build_capri_crop_n_coefs", [str(EXPORTS / "res_2_1730greendeal_refdefaulta.zip")],
     [EXPORTS / "res_2_1730greendeal_refdefaulta.zip"]),
    ("build_capri_gnb_components", [str(EXPORTS / "res_2_1730greendeal_refdefaulta.zip")],
     [EXPORTS / "res_2_1730greendeal_refdefaulta.zip"]),
    ("build_crop_cost_shares", [], [D17]),
    ("build_crushing_parameters", ["--year", "2017", "--market", str(EXPORTS / "market_base_1717.txt"),
                                   "--elas", str(EXPORTS / "elas_2_1717defaulta.csv")],
     [EXPORTS / "market_base_1717.txt", EXPORTS / "elas_2_1717defaulta.csv"]),
    ("build_crushing_parameters", ["--year", "2030", "--market", str(EXPORTS / "markmarket_greendeal_1730et_base_1717.txt"),
                                   "--elas", str(EXPORTS / "elas_2_1730defaulta.csv")],
     [EXPORTS / "markmarket_greendeal_1730et_base_1717.txt", EXPORTS / "elas_2_1730defaulta.csv"]),
    ("build_dairy_processing", [], []),
    ("build_dairy_world_blocks", [], []),
    ("build_dairy_world_markets", [], []),
    ("build_enteric_feed_factors", [str(GAMS), str(D17)], [GAMS, D17]),
    ("build_eu_ms_balance", [], []),
    ("build_feed_bulks", [], []),
    ("build_feed_byproducts", [], []),
    ("build_world_prices", [], [EXPORTS / "fao_agg_17_datamarket.txt", D17]),
    ("build_eu_cake_feed", [], [EXPORTS / "fao_agg_17_datamarket.txt"]),
    ("build_feed_energy", [], [EXPORTS / "data_market_1730defaulta.csv"]),
    ("build_noneu_feed_nq", [], [EXPORTS / "data_market_1730defaulta.csv", EXPORTS / "elas_2_1730defaulta.csv"]),
    ("build_greendeal_targets", ["--gams", str(GAMS), "--gdxlib", str(SOURCES / "gdxlib")], [GAMS / "pol_input" / "greendeal"]),
    ("build_cap14_entitlements", ["--gams", str(GAMS)], [GAMS / "scen", GAMS / "policy" / "policy_sets.gms", SETS,
                                                          REFERENCE / "simini" / "simini_21730" / "DATA.csv.gz"]),
    ("build_rd_inputs", ["--gams", str(GAMS)], [SOURCES / "results" / "policy" / "rd_budget.gdx",
                                                 SOURCES / "course_capri_git" / "dat", GAMS / "policy",
                                                 GAMS / "scen" / "Premiums" / "rd"]),
    ("build_nordic_aid", ["--gams", str(GAMS)], [GAMS / "policy" / "nordicaid.gms", SETS]),
    ("build_premium_policy_inputs", [], [REFERENCE / "simini" / "simini_21730" / "p_EntlWght1.csv.gz",
                                         REFERENCE / "simini" / "simini_21730" / "ntslvl.csv.gz",
                                         REFERENCE / "simini" / "simini_21730" / "p_AggregNUTS2.csv.gz"]),
    ("build_eu_market_blocks", ["--agg", str(GAMS / "aggregation" / "defaultA.agg")], [GAMS / "aggregation" / "defaultA.agg"]),
    ("build_organic_yield_gap", ["--xlsx", str(EXPORTS / "yield_effects_ppp.xlsx")], [EXPORTS / "yield_effects_ppp.xlsx"]),
    ("build_yield_price_elasticity", ["--gams", str(GAMS)], [GAMS / "supply" / "yield_elas.gms", GAMS / "global" / "fromimpact" / "sets.gms"]),
    ("build_mineral_n_price", [str(D17)], [D17]),
    ("build_pmp_own_price_elasticities", ["--dump-dir", str(SOURCES / "estnlp")], [SOURCES / "estnlp"]),
    ("build_capri_supply_elas_market", ["--src", str(EXPORTS / "p_elasSupp.txt")], [EXPORTS / "p_elasSupp.txt"]),
    ("build_capri_own_price_elasticities", ["--src", str(EXPORTS)], [EXPORTS]),
    ("build_captrd_trajectory", ["--series", str(REFERENCE / "captrd_results/1770/series.csv.gz")],
     [REFERENCE / "captrd_results/1770/series.csv.gz"]),
    ("build_captrd_dat", [], [SOURCES / "dat/baseline/ageline/ageline.parquet"]),
    ("build_captrd_estimation_params", [], []),   # from its kept extract (--parquet DIR / --download: the raw)
    ("build_feed_demand_nonEU", [], [EXPORTS / "elas_2_1730defaulta.csv", EXPORTS / "data_market_1730defaulta.csv"]),
    ("build_fert_dist_priors", [], []),
    ("build_fert_options_jul15", [], []),
    ("build_gl_demand", [], [EXPORTS / "elas_2_1730defaulta.csv"]),
    ("build_irrigation_2017", [], []),
    ("build_luc_2030", [], [EXPORTS / "res_2_1730greendeal_refdefaulta.zip"]),
    ("build_manure_pool_costs", ["--dist", str(EXPORTS / "nuts2_center_distance.csv")], [EXPORTS / "nuts2_center_distance.csv"]),
    ("build_mineral_redu_rules", [], []),
    ("build_mitigation_inputs", [str(EXPORTS)], [EXPORTS / "trends_1730.csv"]),
    ("build_n_deposition_substitution", [], []),
    ("build_n_leaching", [], []),
    ("build_nuts2024_reporting", [], []),
    ("build_p_balance", [], []),
    ("build_processing_nq", [], [EXPORTS / "elas_2_1730defaulta.csv", EXPORTS / "markmarket_greendeal_1730et_base_1717.txt"]),
    ("build_welfare_base", [], [EXPORTS / "elas_2_1730defaulta.csv", EXPORTS / "data_market_1730defaulta.csv",
                                 EXPORTS / "markmarket_greendeal_1730et_base_1717.txt"]),
    ("build_eu_market_supply_nq", [], [EXPORTS / "elas_2_1730defaulta.csv", EXPORTS / "data_market_1730defaulta.csv",
                                       EXPORTS / "markmarket_greendeal_1730et_base_1717.txt"]),
    ("build_noneu_market_supply_nq", [], [EXPORTS / "elas_2_1730defaulta.csv", EXPORTS / "data_market_1730defaulta.csv",
                                          EXPORTS / "markmarket_greendeal_1730et_base_1717.txt"]),
    ("build_processing_seeds", [], []),
    ("build_processing_yields", [], [EXPORTS / "markmarket_greendeal_1730et_base_1717.txt"]),
    # CAPRI's marketed over gross production at the 2030 calibration point (S7, grofNEprod), from sim_ini_21730's DATA
    ("build_market_prod_grof_2030", [], [REFERENCE / "simini" / "simini_21730" / "DATA.csv.gz"]),
    # CAPRI's land-use-change estimation of the market outside the EU (luc_market), from sim_ini_21730
    ("build_luc_market", [], [REFERENCE / "simini" / "simini_21730" / "p_lucPriorMrk.csv.gz",
                              REFERENCE / "simini" / "simini_21730" / "p_shFstInSecMrk.csv.gz",
                              REFERENCE / "simini" / "simini_21730" / "DATA.csv.gz"]),
    ("build_sugar_processing", [], []),
    ("build_supply_elas_nonEU", [], []),
    ("build_use_components", [], []),
    ("build_world_market_baseline", [], []),
    # the zip of the other member states' dumps is extracted first (the builder reads text files): see run()
    ("build_young_animal_elasticities", [str(EXPORTS / f"supply_elas_2_1720{c}defaulta.txt") for c in ("DE", "ES", "FR", "IT", "PL")]
     + ["unzip:" + str(EXPORTS / "supply_elas_2_1720REMAINI_NGdefaulta.zip")], [EXPORTS / "supply_elas_2_1720DEdefaulta.txt"]),
    ("extract_capri_costsavings", [str(SOURCES / "costsavings/costsavings_ini_21730_jul15.csv"),
                                   str(SOURCES / "costsavings/costsavings_max_21730_jul15.csv")], [SOURCES / "costsavings"]),
    ("ingest_capmod_market", ["--dump", str(EXPORTS / "_symbols_base1717.txt")], [EXPORTS / "_symbols_base1717.txt"]),
]

#: not audited: utilities and writers of capri_sources/reference/ (not committed) or of inputs held elsewhere
NOT_AUDITED = {
    "gdx_dump_symbol": "utility (dumps one GDX symbol)",
    "convert_capri_gdx": "converter of the published source set (writes outside capri_data; MODEL_CONTENT_PLAN 12b)",
    "make_raw_manifest": "writes tools/pipeline/capri_raw_manifest.json from a staged upload (MODEL_CONTENT_PLAN 12b)",
    "build_capreg_tseries_reference": "writes capri_sources/reference/ (not committed)",
    "build_capri_sets_reference": "writes capri_sources/reference/ (not committed)",
    "build_captrd_results_reference": "writes capri_sources/reference/ (not committed)",
    "build_datam_mirror_2040_reference": "writes capri_sources/reference/ (not committed)",
    "build_eu_outlook_2030": "input (DG AGRI outlook PDF) not held in the workspace",
    "build_n_cascade_validation": "a check, writes a validation table",
    "build_patched_inputs": "superseded one-off (see REGIONAL_UNITS_BUILDERS.md 4.4)",
    "extract_capri_vcs_pair": "input is a GDX inside a zip (cap_after_2014 reference)",
    "build_captrd_sets": "reads capri_sources/reference/sets (not committed; build_capri_sets_reference writes it)",
    "build_trajectory_model_keys": "a module: add_model_keys is called by build_captrd_trajectory (the file's one "
                                   "writer); its command line edits a file in place",
    "build_animal_yields": "a module: build() is called by build_crop_economics_2017, the one writer of yields.csv",
    "convert_inputs_to_parquet": "a conversion step (Parquet decision deferred), not a builder of data",
    "recalibrate_trade_2017": "a module: CAPRI's reporting aggregates (AGGREGATES) and the commodity map (COMMODITY_MAP) the market builders read; its matrix, shared/trade_flows_2017.csv, read by no code, removed 3 November 2026",
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


def placeholder(p: str) -> str:
    """A path with CAPRI's locations as $EXPORTS, $REFERENCE and $SOURCES (tools/lib/paths.py), so the pipeline's
    declaration holds no machine's paths."""
    if p.startswith("unzip:"):
        return "unzip:" + placeholder(p[6:])
    for loc, tok in ((EXPORTS, "$EXPORTS"), (REFERENCE, "$REFERENCE"), (SOURCES, "$SOURCES")):
        if p == str(loc) or p.startswith(str(loc) + os.sep):
            return tok + p[len(str(loc)):].replace(os.sep, "/")
    return p


def expand(p: str) -> str:
    """The inverse of placeholder."""
    if p.startswith("unzip:"):
        return "unzip:" + expand(p[6:])
    for loc, tok in ((EXPORTS, "$EXPORTS"), (REFERENCE, "$REFERENCE"), (SOURCES, "$SOURCES")):
        if p == tok or p.startswith(tok + "/"):
            return str(loc) + p[len(tok):]
    return p


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
            outside = any(sp_ == str(loc) or sp_.startswith(str(loc) + os.sep) for loc in (SOURCES, REFERENCE))
            try:
                if outside:
                    raise ValueError
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
    git("clean", "-fdq", "--", "capri_data")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--chain", action="store_true", help="run the --only builders in order without resetting between them")
    ap.add_argument("--keep", action="store_true", help="with --chain: leave the outputs in the tree (a rebuild)")
    ap.add_argument("--trace", default="", help="run each builder under strace and write its reads and writes (JSON)")
    o = ap.parse_args()
    if o.trace and not shutil.which("strace"):
        sys.exit("--trace runs each builder under strace, a Linux tool not found here: the trace (and "
                 "tools/check/make_pipeline.py after it) needs Linux; the comparison without --trace runs anywhere")
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
        cmd = " ".join([name, *[placeholder(a) for a in args]])
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
