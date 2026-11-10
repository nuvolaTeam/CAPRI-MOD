# Data layout by role

Status: proposed 5 November 2026 and decided by the project lead 5-6 November 2026 (section 5). Step (a), the moves,
done 6 November 2026 for capri_data/sources: its 121 files (and the sugar folder's README) under sources/raw and
sources/intermediate, every content unchanged
(reproduce_builders: 380 of 381 files rebuilt identical, the one difference K119, also on dev before the move; the
mini-EU Farm-to-Fork bit-identical outside the metadata). Step (c), Parquet for capri_data/sources, done 8 November
2026. Step (b), 10 November 2026: the table's 13 moves of model inputs (shared/ to codes/, trajectories/ to 2030/) and
the 43 files of 2017/ whose name carries 2030 (CAPRI's 2030 calibration point: PMP terms, land market and rents,
fertiliser priors, the 2030 market, CAP ceilings ...) to 2030/<module>/, contents unchanged; the model finds a file whose
name carries another year than the base year in that year's folder (capri_mod.data.inputs.year_of_file, used by the
data adapters and loaders.resolve_data_file), the builders write there. Left of step (b): the 2030 columns inside five
2017 files (cattle_intensity, dairy_intensity, cover_crops, labour_coef, set_aside_split: their "_2030" columns,
taken at the 2030 market year) to 2030/ files of their own, with the readers that pick the columns. The plan's step before CAPTRD-MOD ("the data layout by role",
VALIDATION_PLAN stage 2 item 3). Sections 1-2 describe the state before the move.

## 1. What is there today

Two trees:

- **capri_sources/** (outside the repository; tools/lib/paths.py LAYOUT): CAPRI's material as delivered (exports,
  gams, capreg, pmp2030, costsavings, dat, ...) and **reference/**, CAPRI's files converted to CSV for the parity tests
  (captrd_results 318 MB, capreg_tseries 398 MB, coco2, capreg_base, simini, fao_agg, sets, datam_mirror_2040).
- **capri_data/** (in the repository, 136 MB; 471 CSV files): 2017/ (216 CSV, the model's inputs by module), codes/
  (33), pipeline/ (82, CAPTRD's inputs), sources/ (113 CSV in 31 folders), scenarios/, trajectories/, shared/,
  validation/, schema/.

137 builders (tools/pipeline/builders.json) write 381 of the files.

## 2. What is wrong with capri_data/sources

1. **Three kinds of file under one name.** sources/ holds CAPRI's files converted to CSV as they are
   (convert_sources_to_csv, extract_capri_dat: capri_dat/*, capri_gams/*, nuts, water), tables computed from them by
   builders (baseline_pmp by build_pmp_2030 and build_pmp_recipe, market by eight builders, capreg by five, environment by
   three), and files with no writer at all.
2. **The same origin under several names.** CAPRI's dat/ghgtech is in two folders: sources/capri_dat/ghgtech (the AD
   base data and GAINS AD, 8 files) and sources/ghgtech (the fertiliser-technology literature review and miti_data_jul15,
   with capri_costsavings_2030.csv, which is a CAPRI result, not dat). Likewise envind (sources/envind,
   sources/capri_dat/envind, sources/capri_gams/envind) and policy (sources/policy, sources/capri_dat/policy,
   sources/capri_gams/pol_input).
3. **Files without a writer** (no builder declares them): sources/capmod (1), sources/capri_dat/ghgtech (8),
   sources/capri_dat/sugar (3 and a note), sources/eurostat (2), sources/unsourced (1).
4. **Folders nothing reads:** sources/capmod, sources/fao_2021 (only its README), and by the builders' declarations
   sources/environment and sources/fao_agg_2017 (the model reads nothing under sources/; some may be read by the
   checks: to confirm per file).
5. **Model inputs outside 2017/:** trajectories/ (the 2030 calibration-point tables) and shared/ (region tables),
   while 2017/ also holds 2030 tables (feed_ration_2017.csv carries the 2030 slopes).

## 3. Proposed layout (as decided, 6 November 2026)

Principles: a file's folder says its role; a converted file's path mirrors where it comes from; every file has one
writer; nothing without a reader; the model reads its inputs only (2017/, 2030/, codes/, scenarios/), never sources/
(capri_mod/data/inputs.py and capri_mod/market/inputs.py refuse sources/ since 3 November 2026).

```
capri_data/
  sources/                CAPRI's and others' material and the builders' work on it; read by the builders only
    raw/                  CAPRI's and others' values unchanged: files converted one to one, and the builders' kept
                          extracts of CAPRI's large result dumps (rows filtered, values unchanged, so a builder
                          rebuilds without the dump); the path mirrors the origin
      capri/dat/<CAPRI's own subfolder>    e.g. sources/raw/capri/dat/scen/ghgtech (all of dat/ghgtech's files, one folder)
      capri/gams/<subfolder>               e.g. sources/raw/capri/gams/envind, sources/raw/capri/gams/pol_input
      capri/results/<run>                  e.g. sources/raw/capri/results/costsavings_ini_21730_jul15
      capri/capreg, capri/estnlp, capri/star ...
      eurostat/, fao/, nuts/, jrc/         by publisher
    intermediate/<module>/  builder outputs read by other builders or by the checks (baseline_pmp, market build steps,
                          capreg extracts, the 2030 balances)
  2017/<module>/          the model's inputs at the 2017 base (as now)
  2030/<module>/          the model's inputs at the 2030 calibration point (from trajectories/ and, in step (b), the
                          2030 parts of 2017/)
  codes/  schema/  scenarios/  pipeline/  validation/   (as now; shared/ into codes/ by role)
capri_sources/            unchanged: the originals as delivered, outside the repository
```

The two ghgtech folders become sources/raw/capri/dat/scen/ghgtech (the files of CAPRI's dat/ghgtech: AD, GAINS, the
literature review, miti_data_jul15) and sources/raw/capri/results/costsavings_ini_21730_jul15 or
sources/intermediate/abatement (capri_costsavings_2030.csv, built by extract_capri_costsavings from CAPRI's result:
by what the builder does to it); the derived literature-review variant (_no3) goes to sources/intermediate/abatement.
File by file: DATA_LAYOUT_files.csv, every row settled on 6 November 2026: 89 files to sources/raw (one-to-one
conversions and kept extracts; for the kept extracts the run folder is named from the builder's source at the move),
32 to sources/intermediate, and 13 model inputs from shared/ to codes/ and from trajectories/ to
2030/. Twenty files have no writer yet, each with its reader named in the table: eleven from the
dat mirror (CAPRI's AD and GAINS data, the sugar quotas: to be added to extract_capri_dat); the literature review
p_litRevFertTechs (to convert_sources_to_csv, as its _all sibling); four CAPRI extracts with readers (the 2030 market
prices and stored unit values, the land-type PMP terms, the world-price check reference: a conversion builder each);
two Eurostat tables (a download builder); unsourced/producer_prices_no_builder.csv (a proxy with no source, read by
build_eu_producer_prices: to the proxy list); and capri_res/ref2030_welfare.csv, with no reader in the code (a check
reference to settle, or dropped).

## 4. How it is moved

1. A file-by-file table first (path, role, writer, readers, proposed path), for the project lead to check: every move
   is a row.
2. `git mv` per row; tools/lib/paths.py, builders.json, the builders' default paths, capri_mod's readers and the schema
   updated in the same commit; the schema, provenance and manifest regenerated.
3. The five writer-less groups get a builder (the conversion from capri_sources) or are dropped if nothing reads them.
4. Checks: tools/check/reproduce_builders.py (every builder rebuilds its files bit-identically at the new paths),
   validate_data (0 violations), a mini-EU run bit-identical to the run before, the suite.

## 5. Decided (the project lead, 5 November 2026, late evening)

1. The layout and names of section 3: agreed; raw/ and intermediate/ inside capri_data/sources (6 November 2026: the
   sources folder kept, so that the model's input folders hold no raw material).
2. capri_sources (reference/ included) stays outside the repository.
3. The timing is left to Claude: after DEP-22 reaches dev, before S7. In two steps: (a) moves only, every file's
   content unchanged, checked bit-identical; (b) the splits that change a file's content (the 2030 parts of 2017/,
   e.g. feed_ration_2017.csv's capri_slope_2030 column, into 2030/), each with its own check.
4. The sources are converted to Parquet for the Hugging Face download (decision E1), under the same raw/capri/...
   names so that the two trees match; the model's inputs in the repository stay CSV (the project's rule).

5. capri_data/sources (raw/ and intermediate/) is stored as Parquet in the repository (option B, 6 November 2026); the
   model's inputs (2017/, 2030/, codes/, scenarios/) stay CSV, as the project's rule requires (the model reads nothing
   under sources/). Consequences, in step (c) after the moves: one Parquet writer for every builder (tools/lib, fixed
   settings so that a rebuild writes the same bytes: compression, row groups, no index, the library version recorded);
   the schema declarations, validate_data, make_provenance and reproduce_builders extended to Parquet; each file's
   conversion checked value for value against its CSV (floats to the last digit) before the CSV is removed.
   **Done 8 November 2026** (branch pq): the 124 tables of capri_data/sources (115 CSV, 9 compressed .csv.xz) converted,
   48.5 MB of CSV to 11.0 MB of Parquet; each checked before its CSV was removed: read back equal to its CSV as
   read_csv(float_precision="round_trip") read it (values to the last bit, column names and types, row order), and its
   text as a dtype=str reader sees it equal up to how numbers print (in 32 files "320" against "320.0" or "1E-5"
   against "1e-05", the same numbers). The two builder intermediates kept as Parquet in 2017/abatement/ammonia
   (ammonia_cost_curves, ammonia_technology_effects) moved to sources/intermediate/ammonia, so no Parquet file is a
   model input. One reader and writer for every builder, tools/lib/_sources_io.py (read_source, write_source,
   write_source_text, source_records), on capri_mod/tableio.py's fixed settings (zstd, no wall-clock metadata): a
   builder writes the table its CSV text held, so a rebuilt file and a converted one are the same table. The 11
   compressed extracts and the two intermediates had no declaration (the data check counted only *.csv): declared in
   30_sources.sql. capri_mod/data/validate_data.py reads Parquet tables (as text, in file order) and flags any Parquet
   file outside sources; make_provenance and make_manifest_json count them. convert_sources_to_csv.py renamed
   convert_sources.py (it writes Parquet). The Hugging Face upload of the same files (decision E1) is not part of this
   step.
   The same Parquet files are also published on Hugging Face with capri_sources' Parquet (decision E1), so the
   download and the repository hold one copy of each file in one format.

## 6. The questions as asked

1. The layout of section 3 (raw / intermediate / 2017 / 2030 / definitions): agreed, or other names?
2. capri_sources/reference (about 900 MB of converted CAPRI files the parity tests read): keep it outside the
   repository (as now; the Hugging Face Parquet download, decision E1, can serve it) or bring part of it into raw/?
3. When: before S7 (S7, S1/S2 and luc_market add files, which then land in the right place from the start) or after
   Milestone A?
