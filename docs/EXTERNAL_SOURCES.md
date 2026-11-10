# CAPRI's material outside git

Status: 31 October 2026. The model runs from the repository alone: its data are in `capri_data/`. The builders that
derive those data from CAPRI's own exports (tools/build, run by `doit`, `dodo.py`) also read CAPRI's material that is
not in git, because of its size (one export is 388 MB) and because it is CAPRI's. This page lists that material: where
it goes, what each file is, which CAPRI archive or export it comes from, and which builder reads it.

## Where it goes

All paths are relative to the repository. None names a folder of a particular machine, and
`capri_mod/tests/test_portable_paths.py` checks that no file does.

- **`capri_sources/`** at the repository root (not committed; `.gitignore`). Another folder can be used instead, named
  by the environment variable `CAPRI_SOURCES`. It can also be a symbolic link to CAPRI's folders.
- **`capri_sources/reference/`**: CAPRI's files converted for the parity tests and for two builders (section "The
  reference folder" below; another folder with `CAPRI_REFERENCE`). Until 4 November 2026 it was `capri_reference/` at
  the repository root, with its README in git.

The locations are defined once, in `tools/lib/paths.py` (`SOURCES`, `EXPORTS`, `REFERENCE`). The pipeline's
declaration (`tools/pipeline/builders.json`) writes them as `$SOURCES`, `$EXPORTS` and `$REFERENCE`.

If a file is missing:
- **doit** reports the task and skips it.
- **A builder run by hand** stops with the missing path and says which folder it belongs to and what that folder holds.

## Layout of `capri_sources/`

Each folder is listed with what it holds, where it comes from, and the builders that read it.

**`exports/`**: CAPRI's exports as delivered, one file each, not unpacked (list below).

**`datam_mirror_2040/`**: the project lead's extracts of CAPRI's 2040 results from the JRC DataM dashboard MRL_TO_LOQ_2
(import production standards, pesticides), four `.xlsx` files as uploaded on 5 November 2026 (the dashboard's four
copies of the area table are identical in levels: one kept).
- Read by: build_datam_mirror_2040_reference (to the reference folder only; not a model input).

**`capreg/`**: CAPREG's 2017 results, `res_17<MS>.txt`.
- From: the gdxdump listings of `output/results/capreg/res_17<MS>.gdx`, in `res_17zip.zip` (27 member states) plus single
  files. `tools/gams/dump_capreg_explicit.gms` makes them.
- Read by: about 40 builders, e.g. build_capri_base, build_crop_economics_2017, build_land_rents and build_world_prices.

**`capri_export/`**: CAPREG's DATA2 per country, `DATA2_<CC>.txt`, and the PMP terms `quadTechn_<CC>.txt` and
`quadPact_<CC>.txt`.
- From: `capri_export_zip.zip`; tools/gams/dump_capreg_explicit.gms makes the files.
- Read by: extract_all_from_data2, extract_remaining_nine, ingest_pmp_terms.

**`pmp2030/`**: CAPRI's 2030 PMP terms `pmppar_21730<CC>defaulta.txt` and the estnlp estimates
`estnlp_results_{PELA,VB,VD}.txt`.
- From: `tools/gams/export_pmp_2030.gms`, run in a CAPRI installation.
- Read by: build_pmp_2030, build_pmp_recipe.

**`feed_export/`**: CAPRI's feed PMP terms, `pmppar_17<CC>_feedpmp.csv`.
- From: `feed_export.zip`.
- Read by: build_feed_ration.

**`land_export/`**: CAPRI's land-market terms, `pmppar_17<CC>_p_pmpQuadLandTypes.csv` and the others of the zip.
- From: `land_export.zip`.
- Read by: build_land_market.

**`estnlp/`**: CAPRI's estnlp estimates, `estnlp_PELA.txt` and the others.
- From: `estnlp-gtap-trade.zip`.
- Read by: ingest_pela_gtap, build_pmp_own_price_elasticities.

**`supelas/`**: CAPRI's supply elasticities, `supply_elas_2_1720<CC>defaulta.txt`.
- From: `supply_elas_2_1720REMAINI_NGdefaulta.zip`, unpacked.
- Read by: the check tools/check/pmp_supply_elas_check.py. The builders read the zip itself, from `exports/`.

**`fert/`**: `multfact_1730.txt`, the gdxdump of `p_CropNutNeedMultFact` from `priFertDist_*1730*.gdx`.
- From: the command in tools/build/build_overfert_factors.py's docstring.
- Read by: build_overfert_factors.

**`costsavings/`**: `costsavings_{ini,max}_21730_jul15.csv`.
- From: `costsavings_ini_21730_jul15.zip`.
- Read by: extract_capri_costsavings.

**`gams/`**: CAPRI's GAMS source tree.
- From: `gams.zip`.
- Read by: build_ad_option, build_ammonia_cost_tables, build_bilateral_market, build_cover_crops,
  build_digestibility_table, build_enteric_feed_factors, build_eu_market_blocks, build_feed_bulks, build_histosol,
  build_manure_pool_costs, build_organic_yield_gap, build_unit_catalogue, build_yield_price_elasticity,
  build_active_technologies, build_greendeal_targets.

**`dat/`**: CAPRI's `dat` folder as parquet, the project's mirror of it.
- From: the project lead; and, on 10 November 2026, from the public mirror of CAPRI's dat folder on Hugging Face
  (dataset jrc-ai/capri, an older dat vintage): `arm/allpop/worldPop.parquet`, `arm/nutrient_cont_usda/
  p_nutrientCont.parquet`, `biofuel/fossilFuel/p_fossilFuel.parquet` (equal to the installation's fossilFuel.gdx).
- Read by: build_captrd_dat (`dat/baseline/ageline/ageline.parquet`).

**`results/global/`**: CAPRI's global results that CAPTRD reads (captrd/longrun_supports.gms):
`longrun_info_fac_defaulta.gdx` (p_longRunInfoAll) and `GLOBIOM_GL_longrun_defaulta.gdx` (p_globiomInfo).
- From: the project lead's installation (9-10 November 2026).
- Read by: not yet (CAPTRD-MOD Steps 2-3).

**`gams_extra/`**: `fortrd.gms`, CAPTRD's settings include as delivered (empty: the GUI sets CAPTRD's settings; the
reference run's are its META, docs/design/CAPTRD_MOD.md).

**`dat_parquet/`**: GDX files of `dat_local/` converted to Parquet by tools/build/convert_capri_gdx.py (every record,
NA and UNDF named in the column `special`), one folder per file and one file per symbol:
`baseline/aglink2023dgAgri_oriEUdata/` (all 29 symbols) and `baseline/AGLINK2019dgagri_oridata/p_aglinkOri.parquet`.
- Read by: capri_mod/pipeline/captrd/aglink.py (CAPTRD's Aglink stage; c, m, p, m_eq, p_dbvar and the 2019 fish data)
  and tools/build/build_captrd_aglink_sets.py (c, m, p, m_eq).

**`dat_local/`**: files of CAPRI's `dat` folder the mirror above does not hold, under their paths in `dat`:
`envind/lulucf_emissions_original_source.gms` (p_PEATSH_def), `policy/livestock_units.gms` (p_LUUnits) and
`scen/ghgtech/holdingsLSU.gdx` (p_holdLSU).
- From: the project lead's CAPRI installation (4 November 2026).
- Read by: extract_capri_dat_local (p_PEATSH_def); convert_sources_to_csv (p_LUUnits). holdingsLSU.gdx confirms
  capri_data/2017/abatement/ammonia/p_holdLSU.csv (identical records), built from a dump before.
- Goes to the Hugging Face set with the rest of capri_sources (MODEL_CONTENT_PLAN §12b).
- Added on 10 November 2026 (the project lead's installation; CAPTRD's inputs for Steps 2-3, docs/design/CAPTRD_MOD.md
  section 12.1), under their paths in `dat`:
  - `baseline/`: `aglink2023dgAgri_oriEUdata.gdx` (c, m, m_eq, p, p_dbvar), `AGLINK2019dgagri_oridata.gdx`
    (p_aglinkOri; delivered as aglink2019dgAgri_oriData.gdx, renamed to the name load_aglink2023dgAgri.gms l. 205
    reads), `aglink2023macro.xlsx` (CAPTRD makes ctrCode.gdx and aglink2023macro.gdx from it with gdxxrw, l. 913-927),
    `data_SSPV3_update.gdx` (SSP_data), `recent_mlk_yld.gdx` (p_recentMlkYld), `dairy_targets_agri.gms`,
    `necp_expert.gms`; not read by CAPTRD: `aglink2019OECD_oriData.gdx`,
    `Comtrade_UKR_2023_Export_Cereals-Oilseeds-Oils-Meals_Jan-Sep.xlsx` (arm/data_prep.gms);
  - `arm/`: `allpop.gdx` (worldPop), `allpop.gms`, `nutrient_cont_usda.gdx` (p_nutrientCont);
  - `coco/Agri_Prod.gdx` (p_AgriProd); `capreg/regional_mlk_prod.gms`;
  - `biofuel/`: `primes_ref_060722.gdx` (p_PrimesWithUnits; the run's %primesBiofuelFile%), `fossilFuel.gdx`
    (p_fossilFuel; equal to the mirror's record for record), `biofuel_data.gms`,
    `POTENCIA_processing/POTENCIA_transport_energy_outlook.gdx`;
  - `global/reg_mappings.xlsx` (GlobiomCountry, GlobiomCountry_FAOreg, FAOreg_AGLINKregions, l. 931-951).

**`results/permits/`**, **`results/arm/`**: CAPRI's GHG and technology result files, received 10 November 2026, as
capmod.gms l. 1641-1645 writes them (results\permits\res_<scenario>_21730.gdx: v_Miti, p_ghgMiti, EMISCALC,
v_actLevl, p_animReq, ...): the Green Deal step's (the project lead's run of 10 November 2026) and the
endogenous-technology reference's ini and max runs' (the files carry no META: their date and origin are not
recorded); and the market model's debug dump at the Green Deal step's preparatory solve (arm/prep_market.gms
l. 1211, chk_market_data_greendeal_greendeal_scenarios.gdx; META: 10 November 2026, GAMS 53.3).
- Read by: not yet (technology uptake and market-calibration checks).

**The published set** (Hugging Face, gated: nuvolaTeam/capri-mod-raw; docs/design/MODEL_CONTENT_PLAN.md §12b): the
files above under `originals/<path under capri_sources>` byte for byte, and their symbols as Parquet under
`capri/results/<file stem>/` (tools/build/convert_capri_gdx.py). Every file with its SHA-256, size and version (tag) in
tools/pipeline/capri_raw_manifest.json. First version `v2026.11.10` (10 November 2026): the six GDX files received that day
(exports/ and results/ above).

**`gdxlib/`**: GAMS's GDX library, `libgdxcclib64.so`. This is software, not data.
- From: built from the open-source GDX library (MIT; README section 3). No GAMS installation or licence is needed.
- Read by: build_greendeal_targets and build_capreg_tseries_reference. Another folder can be given with `--gdxlib` or
  the environment variable `CAPRI_GDXLIB`.

The archives named above are the files the project lead delivered (the "uploads"). Placing an archive's contents in
the folder named, unpacked, is all the set-up needed.

## The exports (`capri_sources/exports/`)

CAPRI's 2030 reference results:
- **`res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv`**: dataOut of the 2030 reference with the endogenous
  technologies, initial run.
  - Read by: build_animal_pmp_capri_2030, build_cap_ceilings_2030, build_labour_setaside, build_land_market,
    build_land_rents, build_manure_trade_base, build_pmp_capri_2030, build_pmp_recipe, build_ration_trajectory_2030,
    build_trajectory_capri_ref and others.
- **`res_2_1730greendeal_refdefaulta.zip`**: dataOut of the 2030 reference.
  - Read by: build_capri_crop_n_coefs, build_capri_gnb_components, build_fert_dist_priors, build_luc_2030,
    build_manure_losses, build_nh3_factors, build_npk_balance_2030, build_p_balance, build_plant_protection_cost.
- **`res_0_1717cap_after_2014_cal_from_data_caldefaulta.csv`**: the 2017 calibration run.
  - Read by: recalibrate_trade_2017, build_tariffs_2017.
- **`res_2_1730greendeal_refpol_endotech_all_maxdefaulta.gdx`** and **`res_2_1740greendeal_refpol_endotech_all_maxdefaulta.gdx`**
  (received 9 November 2026; kept as the project lead asked): CAPRI's result files of the endogenous-technology
  reference's "max" run for 2030 and 2040, as CAPMOD writes them (capmod/set_and_store_dataout.gms l. 477): dataOut
  (5,223,048 and 5,199,448 records), RALL, META (12,264 records each) and p_INFES. Their META: step "Run scenario without
  market model", scenario greendeal\refpol_endotech_all_max, base year 2017, run on 5 November 2025 with GAMS 45.7
  (2030 at 14:13:41, 2040 at 14:13:44), 15 iterations, every GUI setting as run. In the 2030 file every supply solve is
  feasible, two non-optimal in step 1 (NL120000, UKN00000). Not CAPRI's November 2026 runs with IPOPT forced; the
  2030 file is the GDX of the run whose dataOut the zip res_2_1730greendeal_refpol_endotech_all_maxdefaulta.zip
  holds as CSV (not compared value by value). Read by no builder yet.
- **`res_2_1730greendeal_refdefaulta.gdx`** and
  **`res_2_1730greendeal_lnds8_org18_pest20_mine13crp_surp30_diet00_oth00defaultA.gdx`** (received 10 November 2026):
  CAPRI's Green Deal 2030 reference and its 2030 Green Deal step (pol_input/greendeal/greendeal_scenarios.gms: landscape
  elements 8%, organic 18%, pesticides -20%, mineral fertiliser 13crp, N surplus -30%). The reference is CAPRI's shipped
  run (META: 5 November 2025, GAMS 45.7), the GDX of the zip above (the two agree in all 891,502 records of the member
  states and EU27yr19 in 2030, to the dump's 15 digits); the step is the project lead's run from it (META: 10 November
  2026, GAMS 53.3). Its META lists "Sensitivity experiments with features in supply model: true [default]", but its
  dataOut holds no experiment's records (set_and_store_dataout.gms l. 258-269 would store them under the experiments'
  names in the second dimension): the experiments did not run or did not write results.
  - Read by: extract_capri_gd_pair (capri_data/validation/greendeal_2030/capri_gd_effect.csv.xz).

The zip above, **`gd_full.zip`** (gd_full.txt) and **`markmarket_greendeal_1730et_base_1717.txt`** are one file: the
same dataOut dump of the 2030 reference (387,918,153 bytes, CRC 5c5903b6; checked 10 November 2026), under three names.

CAPRI's market exports:
- **`market_base_1717.txt`**, **`markmarket_greendeal_1730et_base_1717.txt`**: the market model's data for 2017 and 2030.
  - Read by: build_bilateral_market, build_biofuel_market, build_crushing_parameters, build_dairy_processing,
    build_feed_bulks, build_processing_nq, build_sugar_processing and others.
- **`data_market_1730defaulta.csv`**, **`elas_2_1717defaulta.csv`**, **`elas_2_1730defaulta.csv`**: market data and
  elasticities.
  - Read by: build_gl_demand, build_feed_demand_nonEU, build_eu_ms_balance, build_welfare_base and others.
- **`fao_agg_17_datamarket.txt`**: CAPRI's FAO aggregation.
  - Read by: build_world_prices, build_world_market_baseline, build_dairy_world_markets, build_eu_cake_feed.
- **`_symbols_base1717.txt`**: symbol listing of the 2017 market run.
  - Read by: ingest_capmod_market.

Supply elasticities:
- **`p_elasSupp.txt`**.
  - Read by: build_capri_supply_elas_market.
- **`supply_elas_2_1720{DE,ES,FR,IT,PL}defaulta.txt`** and **`supply_elas_2_1720REMAINI_NGdefaulta.zip`**.
  - Read by: build_capri_own_price_elasticities, build_young_animal_elasticities.

Mitigation and ammonia inputs:
- **`LitRevAmmoTech.csv`**, **`LitRev_input_manStor.csv`**, **`LitRev_inputs.csv`**,
  **`LitRev_non_changeable_parameters.csv`**, **`holdingsLSU.csv`**, **`nvzShare_LU.csv`**.
  - Read by: build_ammonia_tech_inputs.
- **`scen.zip`**, **`gd_full.zip`**.
  - Read by: build_ammonia_herd_inputs.
- **`animReq_SK.zip`**.
  - Read by: build_lownfeed_effects.
- **`priFertDist_1730defaulta.zip`**.
  - Read by: build_fert_dist_priors.
- **`trends_1730.csv`**, **`fedcof.gms`** (with tillageCover.csv, ccEfa.csv, wintercovershare.gms).
  - Read by: build_mitigation_inputs.
- **`yield_effects_ppp.xlsx`**.
  - Read by: build_organic_yield_gap.
- **`nuts2_center_distance.csv`**.
  - Read by: build_manure_pool_costs.

The complete and exact list, per builder invocation, is the `external` field of `tools/pipeline/builders.json`.

## The reference folder (`capri_sources/reference/`)

These are CAPRI files from the project lead's installation, converted to CSV. They are read-only and are read only by
the tests and the parity runs, never by the model (docs/design/CAPTRD_MOD.md section 6). Two folders are sources of
the data pipeline: `sets/simini_21730`, read by `tools/build/build_code_lists.py` (the code lists of
`capri_data/codes` and, since 3 November 2026, CAPRI's RMS and RMS_TO_RM in `capri_data/shared`), and
`captrd_results/1770`, read by `tools/build/build_captrd_trajectory.py` (the CAPTRD 2030 scenario). They are
large, so they are left out of the zip packages. Each folder is rebuilt from the uploaded originals by the tool
named below.

| Folder | Original | Content | Tool |
|---|---|---|---|
| `capreg_tseries/17/<CC>.csv.gz` | `Capreg_tseries/<CC>_17.gdx` (35 files) | CAPREG's time series `DATA(region, col, row, t)`, 1984–2018 plus BAS, BASM, CUR, MEAN, TRD, Y: the input CAPTRD reads as DATA1 (captrd.gms l. 486-505) | `tools/build_capreg_tseries_reference.py --src Capreg_tseries.zip` |
| `capreg_base/17/<CC>.csv.gz` | CAPREG's base-year results `res_17<CC>.gdx`: as text dumps `res_17<CC>.txt` (upload res_17zip.zip and single files), 8 as GDX files (UK, TU, AL, MK, CS, MO, BA, KO; uploaded 29 October 2026), Spain from the CAPRI GUI's CSV export `DATA2_res_17ES.csv` (upload capri_export_zip.zip; the export equals the dump in all 10,991 records of Denmark, 10 November 2026). <CC> is CAPTRD's file code, the first two characters of the country (TU for TUR) | CAPREG's base-year data `DATA2(region, col, row, "Y")`, the input CAPTRD reads as BASM (captrd.gms l. 528-580); 15 significant digits from the dumps, 17 from the GDX files | `tools/build/build_capreg_base_reference.py --src DIR_OR_ZIP [--src DIR]` |
| `coco2/17/coco2_output.csv.gz` | text listing `coco2.csv` of COCO's `coco2_output.gdx` (upload coco2.zip) | COCO's `DATA2(region, item, col, row, t)`, items INI, COCO1, COCO2, 1984–2019: what CAPTRD loads as dataMS (load_coco1_data.gms l. 24); 15 significant digits | `tools/build/build_coco2_reference.py --src coco2.zip` |
| `fao_agg/17/<symbol>.csv.gz` | text listing `FAO_agg_17_defaulta.csv` of the global database `fao_agg_17_defaulta.gdx` (upload FAO_agg_17_defaulta.zip) | `p_biofuelData`, `p_aglinkGrowthFactor` (load_coco1_data.gms l. 360); columns d0…dn, value, eps | `tools/build/build_fao_agg_reference.py --src FAO_agg_17_defaulta.zip` |
| `captrd_results/1770/<respos>.csv.gz` | `results_1770.gdx` (base 2017, simulation years 2018–2070) | CAPTRD's `p_result(region, col, row, t, respos)`, one file per result position (Step1, support, support1, wVarErr, step2, step3, series, P_Data, data statistics, …); `respos_counts.csv` lists all positions and `settings.csv` the run settings | `tools/build_captrd_results_reference.py --src results_1770.gdx --tag 1770` |
| `sets/simini_21730/<SET>.csv` | `sim_ini_21730.gdx` (CAPMOD restart file of the endotech Green Deal 2030 run) | the 1,972 CAPRI sets of that run (global sets.gms and loaded modules, with the run's switches applied), one file per set with `_index.csv`; sets defined only in CAPTRD (sets_captrd.gms) are not among them | `tools/build_capri_sets_reference.py --src sim_ini_21730.gdx --tag simini_21730` |
| `simini/simini_21730/<symbol>.csv.gz` | `sim_ini_21730.gdx` (the same restart file as `sets/simini_21730`) | CAPRI's calibrated 2030 market state for the move onto CAPRI's market regions and the ports' checks, and the per-technology terms of S1 (p_pmpCnst, p_technFact, since 7 November 2026): the symbols listed with their use in `tools/build/simini_reference_symbols.csv` (DATA, the trade flows and prices, TRQs, levies, entry prices, Armington and CES parameters, the GL demand and NQ Hessians, the market variables' levels and bounds), with `_index.csv`; parameters `d0…dn, value, eps`, variables `d0…dn, level, eps, lower, upper, marginal`; +INF/-INF as inf/-inf, NA as nan. `--check sim_ini_21730_1.gdx` found the 37 symbols identical in the second upload (2 November 2026), and all 51 on 7 November 2026 | `tools/build/build_simini_reference.py --src sim_ini_21730.gdx --tag simini_21730` |
| `datam_mirror_2040/<table>.csv` | the project lead's extracts of the JRC DataM dashboard MRL_TO_LOQ_2 (`capri_sources/datam_mirror_2040/*.xlsx`, uploaded 5 November 2026; data valid as of February 2026 per the dashboard) | CAPRI's 2040 results of the JRC study on aligning import production standards (pesticide active substances not approved in the EU), four scenarios (Baseline, switchX-scaleEFSA_5, switchX-scaleEFSA+min20, noadapt-noscale): utilised area per member state, EU production change per product (scenario not stated in the extract), producer prices per trade region and product, bilateral trade per reporter, product and partner (variable and unit not stated). Not read by the model or the pipeline: a future 2040 check for CAPTRD-MOD (MODEL_CONTENT_PLAN §14 item 19); the shock inputs and CAPRI's scenario code are not in the extracts | `tools/build/build_datam_mirror_2040_reference.py` |

Columns of the data files: `region, col, row, t, value, eps`.
- A record CAPRI stored as Eps (an explicit zero) has value 0 and eps = 1.
- A record CAPRI did not store is absent.

## Software outside Python

**GAMS** is needed only for the export scripts in `tools/gams/`, run in a CAPRI installation to produce the exports
above. The `dump_*.gms` scripts take CAPRI's folder on the command line, as in
`gams dump_capreg_explicit.gms --CAPRI=C:\path\to\capri-star3.0`, and stop with a message when it is not given.
`export_pmp_2030.gms` sets it in its first lines. These scripts have not been rerun since the change of 31 October
2026, because there is no CAPRI installation here.

**The GDX library** (`gdxlib/` above) is needed by the two builders that read .gdx files. It is open source and needs
no GAMS.

**pdftotext** (poppler-utils, available for Linux, macOS and Windows) is needed only by
`tools/build/build_eu_outlook_2030.py`, which parses the layout text of DG AGRI's outlook PDF into a validation file
(not part of the pipeline). It stops with a message when pdftotext is missing. A Python PDF library lays the text out
differently, and the PDF is not at hand to check a replacement against it, so the program stays.

**grep and unzip are no longer used.** The builders read CAPRI's listings and zip archives with Python's standard
library (`tools/lib/_grep.py`, since 31 October 2026); the text is the same as the tools gave.

**strace** (Linux) is needed only by `tools/check/reproduce_builders.py --trace`, which records the files each builder
opens to regenerate the pipeline's declaration (`tools/check/make_pipeline.py`). Without `--trace` the comparison runs
anywhere, and the tool stops with a message when strace is missing.

**The model's parallel regional solves** use `fork`. Where it does not exist (Windows), the model solves the regions in
one process, which is slower but gives the same results. The runs and tests are made on Linux; Windows and macOS have
not been tested.

## CAPRI's online documentation (read, not part of the inputs)

These pages explain CAPRI; no model input is built from them.
- CAPRI's documentation: https://bw-pages.thuenen.de/capri/capri/ (pointed to by the project lead, 1 November 2026).
- The CAPRI course of 2026 (Thünen Institute): https://bw-pages.thuenen.de/capri/course/ (pointed to by the project
  lead, 1 November 2026). Slides, exercises and GAMS files per session, under `course/pdf/DayN/`. For capri-mod:
  - the supply module and its calibration (days 5 and 6; `Day6/6_1_PMP_t.pdf`, `Day6/Ex. 1/PMP_test.gms`);
  - the market module (days 8 to 10). `Day8/intro to market session/8_2_Market_Model_Intro_2026.pdf` sets out the
    four regional levels RMSSUP, RMS, RM and RMTP (e.g. IR000000 in A_EU_WEST, policy block EU), the two Armington
    stages, the behavioural blocks (ProdNQ_, ProcO_, DairyNQ_, the GL demand, FeedNQ_, ProcNQ_) and the link to the
    supply models (price expectations, market supply functions calibrated each step). It does not cover TRQ
    functions, levies, entry prices, biofuels or the solver;
  - `Day8/intro to market session/results files/DatabaseofCAPRI.gdx`, a GDX of CAPRI's database for the exercises
    (not downloaded, not checked).
- CAPRI's wiki: https://www.capri-model.org/dokuwiki_help/doku.php

## Until 31 October 2026

Until 31 October 2026 the builders' defaults named two folders of the machine they were developed on (its uploads
folder and its work folder), and `dodo.py` read them from `CAPRI_UPLOADS` and `CAPRI_WORK`. The
GAMS scripts named the project lead's CAPRI folder. Two other things changed at the same time:
- The folders were renamed, e.g. `allgms/gams` became `gams` and `feedexp/feed_export` became `feed_export`.
- `build_nh3_factors` reads the 2030 reference zip itself. Before, it read `nh3_rows.txt`, rows grepped from it
  beforehand; reading the zip gives the same 80,303 rows, byte for byte, and the same output.
