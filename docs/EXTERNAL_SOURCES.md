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
- **`capri_reference/`** at the repository root: CAPRI's files converted for the parity tests (capri_reference/README.md;
  only its README is committed).

The locations are defined once, in `tools/lib/paths.py` (`SOURCES`, `EXPORTS`, `REFERENCE`). The pipeline's
declaration (`tools/pipeline/builders.json`) writes them as `$SOURCES`, `$EXPORTS` and `$REFERENCE`.

If a file is missing:
- **doit** reports the task and skips it.
- **A builder run by hand** stops with the missing path and says which folder it belongs to and what that folder holds.

## Layout of `capri_sources/`

Each folder is listed with what it holds, where it comes from, and the builders that read it.

**`exports/`**: CAPRI's exports as delivered, one file each, not unpacked (list below).

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
- From: the project lead.
- Read by: build_captrd_dat (`dat/baseline/ageline/ageline.parquet`).

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

## Software outside Python

**GAMS** is needed only for the export scripts in `tools/gams/`, run in a CAPRI installation to produce the exports
above. The `dump_*.gms` scripts take CAPRI's folder on the command line, as in
`gams dump_capreg_explicit.gms --CAPRI=C:\path\to\capri-star3.0`, and stop with a message when it is not given.
`export_pmp_2030.gms` sets it in its first lines. These scripts have not been rerun since the change of 31 October
2026, because there is no CAPRI installation here.

**The GDX library** (`gdxlib/` above) is needed by the two builders that read .gdx files. It is open source and needs
no GAMS.

**strace** (Linux) is needed only by `tools/check/reproduce_builders.py --trace`, which records the files each builder
opens to regenerate the pipeline's declaration (`tools/check/make_pipeline.py`). Without `--trace` the comparison runs
anywhere, and the tool stops with a message when strace is missing.

**The model's parallel regional solves** use `fork`. Where it does not exist (Windows), the model solves the regions in
one process, which is slower but gives the same results. The runs and tests are made on Linux; Windows and macOS have
not been tested.

## Until 31 October 2026

Until 31 October 2026 the builders' defaults named two folders of the machine they were developed on (its uploads
folder and its work folder), and `dodo.py` read them from `CAPRI_UPLOADS` and `CAPRI_WORK`. The
GAMS scripts named the project lead's CAPRI folder. Two other things changed at the same time:
- The folders were renamed, e.g. `allgms/gams` became `gams` and `feedexp/feed_export` became `feed_export`.
- `build_nh3_factors` reads the 2030 reference zip itself. Before, it read `nh3_rows.txt`, rows grepped from it
  beforehand; reading the zip gives the same 80,303 rows, byte for byte, and the same output.
