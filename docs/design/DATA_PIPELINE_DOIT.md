# The data pipeline as doit tasks (28 October 2026, the project lead's decision)

Goal: every model input under `capri_data` built by exactly one task, every task declaring what it reads and writes,
the order derived from those declarations (doit, `dodo.py`), a rebuild running only what an input change affects.
Results unchanged: a full rebuild must reproduce every committed file byte for byte.

## Why

- The rebuild list (`tools/check/reproduce_builders.py` INVOCATIONS) is ordered by hand. The K88 census found one order
  error that left stale data (the ammonia technology model built before the AD option, the AD option before the N loss
  cascade: up to 1.6e-4 relative in the technology model's initial shares). A static scan found 56 more reads of files
  that the list builds later; all of them are CAPRI extracts that the census shows unchanged, so they did no harm.
- 30 of the 280 builder-written files have more than one writer, so a builder cannot be checked on its own and the
  order decides the data.

## doit (0.37), checked

- Order from `file_dep` / `targets`: a task runs after the task that writes its inputs, whatever the declaration order.
- Change detection by content (`check_file_uptodate = "md5"`): a touched file reruns nothing, a changed one reruns its
  dependants.
- Two tasks with one target are refused ("Two different tasks can't have a common target").

## Dependencies: traced, not declared by hand

`reproduce_builders.py --trace OUT.json` runs each builder under strace and records the files it opens: reads (first
access a read), writes, read-modify-writes, the Python files it ran and the files it read outside the repository
(CAPRI's sources). strace also sees Parquet and other C-level reads and child processes (the N loss cascade reads
`ammonia_technology_effects.parquet`, which a search of the code for `.csv` names misses).

## Files with several writers (K88 census)

| Pattern | Files | Plan |
|---|---|---|
| `build_shg_split` (a one-time migration of October 2026: SHGO split into SHGM and SHGF, then 13 builders rerun) | 22 | done (29 October 2026): retired; its coefficient step (the only writer of three per-head tables) moved into `build_livestock_output_coef`, and its SHGM/SHGF costs and EU price rows (the only writer of those cells, found by rebuilding the tables from blank) kept as `build_sheep_goat_inputs`, unchanged |
| base tables written in turn, each builder its columns | `yields.csv`, `variable_costs.csv`, `sources/capreg/capreg_producer_prices.csv`, `market/producer_prices.csv` | done (29 October 2026): one owner each, built from scratch (`build_crop_economics_2017` the first three, `build_eu_producer_prices` the last; the other builders' parts became functions they call); the rows no builder computes declared in `sources/unsourced/producer_prices_no_builder.csv` (K72) |
| `market/armington_params.csv`: rows added by `build_dairy_trade_params` and `build_feed_byproducts` | 1 | done (29 October 2026): the file and `build_dairy_trade_params` removed, its one column `eps` acting on no result (K72) |
| `sources/capreg/capreg_nutrient_coefs.csv`: `extract_all_from_data2`, `extract_remaining_nine` | 1 | done (29 October 2026): `extract_all_from_data2` only |
| a builder reading its own previous output (`recalibrate_trade_2017.py`: `trade_flows_2017.csv` for its column list) | 9 (trace of 29 October 2026) | done (29 October 2026): `build_capri_base` (the layout of its three tables), `recalibrate_trade_2017` (its column list) and `build_crop_cost_shares` (the set-aside row, which CAPRI's data give: share 1) now build from their inputs only; `build_capri_baseline_surplus`, `build_livestock_products`, `build_manure_trade_base` read their output only for a printed comparison, removed; `build_feed_byproducts`' rows of `world_prices.csv` and its provenance moved to the table's new owner `build_world_prices` (every row from its CAPRI source; the placeholder rows `FATS`, `OFOD_M` removed; the rows at the source's full precision, at most 0.02% from the committed 2- and 1-decimal values); `build_trajectory_model_keys` edits `captrd_2030.json` in place and the file's CAPRI-keyed part has no extractor: out of the pipeline (K91). Each checked by a rebuild from blank, byte for byte (`world_prices.csv` changed as stated) |
| an extractor reading the model's tables for a printed comparison (`extract_all_from_data2`: `producer_prices.csv`, `nutrient_coefs.csv`) | 1 | done (29 October 2026): comparison removed (it closed a cycle: the extract feeds those tables) |

## Builders not read by the model

No orphan: `ingest_capmod_market`'s extracts are read by the world-price checks (`tools/check/validate_world_prices.py`, `report_world_price_divergence.py`).

## How a rebuild is checked (29 October 2026)

A chain run over the committed files is not enough: builders that read a table before writing it (a read-modify-write;
`build_capri_base` keeps the cells it does not compute) leave a cell that no builder writes as it was, so the file
still compares identical. The retirement of `build_shg_split` passed that test with 442 cost cells and two price rows
left without a writer. The check is therefore a rebuild from blank: the tables emptied (index and columns kept), the
builders run, every file compared byte for byte; with doit, the full rebuild runs from the sources on an empty
`capri_data` output set.

## Steps

1. Trace every builder: done (29 October 2026, `builder_trace4.json`: 117 invocations, each reproducing its files).
2. One writer per table, each change checked byte for byte: done (the tables above).
3. `dodo.py`: one task per builder invocation from `tools/pipeline/builders.json` (generated by
   `tools/check/make_pipeline.py` from the trace: inputs, CAPRI sources, the builder's code as `file_dep`, its writes
   as `targets`; the generator stops on a file with two writers or a cycle); the data checks
   (`tools/check/validate_data.py`) as the last task. An argument `unzip:Z` runs the builder on the files of zip Z, as
   `reproduce_builders.py` does. Done.
4. Full rebuild from the sources with doit (`tools/check/rebuild_from_blank.py`): done 29 October 2026, all 289
   outputs of the 117 tasks deleted and rebuilt, every file identical to the committed one (the first attempt stopped
   at the one builder given a zip archive, fixed in step 3).

Kept: `reproduce_builders.py` (each builder alone on the committed inputs, the census) and its trace mode, from which
`builders.json` is regenerated when a builder's reads or writes change (`make_pipeline.py TRACE --check` first).
Out of the pipeline: `build_trajectory_model_keys` (K91) and the tools listed in `reproduce_builders.NOT_AUDITED`.

Removed 29 October 2026 (the project lead's decision: the extractors write only what the model, or a builder of its
inputs, reads; KNOWN_ISSUES K102): `build_nitrates_directive` and its inputs and outputs (CAPRI's Nitrates Directive
minimum shares, applied only with CAPRI's NDtech, off in its Green Deal runs: read by no code), the 13 symbols of
`build_ammonia_tech_inputs` no code reads, `build_ammonia_cost_tables`' scalars.csv, `build_mitigation_inputs`'
p_tillageCover, p_ccEfa and p_winterCoverShare0. `build_ammonia_tech_inputs` now also gets CAPRI's holdingsLSU and
nvzShare_LU dumps, whose p_holdLSU.csv and p_nvzShare_lu.csv the builders read and no traced invocation wrote (their
output is the committed files, byte for byte).

