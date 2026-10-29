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
| `build_shg_split` (a one-time migration of October 2026: SHGO split into SHGM and SHGF, then 13 builders rerun) | 22 | the base builders now take SHGM and SHGF from CAPRI directly (`build_capri_base`, `build_animal_yields`); `animal_numbers.csv` has no SHGO left. To check: a full rebuild without it reproduces the data; then retired |
| base tables written in turn, each builder its columns | `yields.csv`, `variable_costs.csv`, `sources/capreg/capreg_producer_prices.csv`, `market/producer_prices.csv` | each builder writes its part to its own intermediate; one assembly task writes the table (same columns, order and format) |
| `market/armington_params.csv`: rows added by `build_dairy_trade_params` and `build_feed_byproducts` | 1 | done (29 October 2026): the file and `build_dairy_trade_params` removed, its one column `eps` acting on no result (K72) |
| `sources/capreg/capreg_nutrient_coefs.csv`: `extract_all_from_data2`, `extract_remaining_nine` | 1 | one extractor |
| a builder reading its own previous output (`recalibrate_trade_2017.py`: `trade_flows_2017.csv` for its column list) | 1+ | the trace lists them (`rewrites`); each reads its inputs only |

## Builders not read by the model

No orphan: `build_nitrates_directive` builds CAPRI's Nitrates Directive minimum shares, applied only with CAPRI's
`NDtech` (off in its Green Deal runs, so not applied here); `ingest_capmod_market`'s extracts are read by the world-price
checks (`tools/check/validate_world_prices.py`, `report_world_price_divergence.py`).

## Steps

1. Trace every builder (about 1 h).
2. One writer per table (above), each change checked byte for byte.
3. `dodo.py`: one task per builder invocation, `file_dep` from the trace (inputs, CAPRI sources, the builder's code),
   `targets` its writes; `reproduce_builders.py` keeps the census (each builder alone) and takes its order from doit.
4. Full rebuild from the sources with doit: every committed file reproduced.
