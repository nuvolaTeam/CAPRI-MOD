# CAPRI-mod data layout

Status: revised 20 October 2026 against the code and the folder.

Every input is CSV or JSON, extracted from CAPRI star 3.0's data and results and built by a script in
`tools/build_*.py` that names its source; the model never reads GDX (README section 4 (The data layer)). Data are organised by
**base year**, then by **module category**:

```
capri_data/
├── 2017/                  base year 2017 (the only one)
│   ├── supply/            areas, yields, herds, costs, premiums, land market, intensities, PMP terms, elasticities
│   ├── market/            bilateral flows and parameters (2017 and 2030), world prices, demand, processing, dairy,
│   │                      biofuel, feed bulks
│   ├── policy/            CAP payments, tariffs, Green Deal target tables, mineral fertiliser rules
│   ├── environment/       emission coefficients, N balance inputs, fertiliser priors, manure losses and trade, LUC
│   ├── feed/              requirements, rations, fodder balances
│   └── abatement/         mitigation options: ammonia/ (N cascade, AD, leaching, Nitrates Directive, costs/),
│                          mitigation/ (feed, genetics, soil options), fertiliser options
├── shared/                region maps (region_capri_map.csv, NUTS correspondences), EU trade blocks,
│                          model_parameters.csv, trade_flows_2017.csv
├── trajectories/          capri_ref_2030.json (default), captrd_2030.json, null.json, CAPRI's 2030
│                          prices, premiums, rations and fodder
├── validation/            CAPRI reference results used by the tests and comparison tools
├── sources/               the extracts the builders read (CAPRI result rows, MITERRA tables, literature review);
│                          not read by the model
├── schema/                the declarations of every CSV (DuckDB SQL: types, keys, code lists, ranges, units), each
│                          file's provenance and checked notes, the numbers held in the model's code, and
│                          schema.json (the same as JSON, generated)
├── MANIFEST.json                                           expected files and shapes
├── FITNESS_FOR_USE.json                                    how far each output can be trusted (capri_mod/fitness.py)
└── *.md                                                    this file and the guides below
```

Guides in this folder:

| File | Content |
|---|---|
| `DATA_DICTIONARY.md` | each input file: content, source, shape; code glossary |
| `DATA_SOURCING_GUIDE.md` | where the data come from, how to check them, how to update them |
| `DATA_LOCATION_MAP.md`, `SYMBOL_EXTRACTION_GUIDE.md`, `DATA_ACQUISITION_REFERENCE.md` | where to find CAPRI symbols and files for a rebuild or a new base year; partly historical |
| `validation/VALIDATION.md`, `validation/HOW_TO_RUN_A_VALIDATION_SCENARIO.md` | the early validation report and how to produce a CAPRI scenario for comparison; current validation: README section 9 (Validation) |

## Why base-year-first

A CAPRI base year is self-contained: its prices, quantities and PMP parameters are calibrated together and must not
be mixed across years. Keeping each base year in its own folder makes that visible. Files that are not tied to one
base year live in `shared/`; the 2030 projection data live in `trajectories/`, and some files under `2017/` already
hold CAPRI's 2030 reference values used by the projection (their names end in `_2030`).

## Adding a new base year

Not a working path yet. The intended steps are: create `capri_data/<year>/` with the same category subfolders, place
that year's files there under the same names, and load with `CAPRIModel(data_dir="capri_data", base_year="<year>")`.
But several modules read `capri_data/2017/` directly, so the `base_year` argument does not switch every file; that has
to be fixed first (README section 4 (The data layer)). PMP terms and elasticities are CAPRI estimation outputs and need
CAPRI's estimation for the new year, not a copy; the planned route is the data pipeline (docs/design/CAPTRD_MOD.md: the
COCO and CAPREG ports). (`capri_mod/data/rebase.py`, a Eurostat download into a new base folder that relied on the
elasticity calibration removed on 28 October 2026, was removed on 29 October 2026 with `reconcile_base.py`, K94.)

## File resolution

`capri_mod/data/loaders.py::resolve_data_file` looks a file up in `shared/` (for the files mapped there, e.g.
`trade_flows.csv` → `shared/trade_flows_2017.csv`), then in `<base_year>/<category>/` from its category table, then
in a flat `capri_data/<file>` fallback.

## Checks

`python -m capri_mod.data.validate_data capri_data` (files, shapes against MANIFEST.json, vintages, sanity,
provenance; 20 October 2026: 12 pass, 1 warning, a stale MANIFEST row count for `fert_side_effects.csv`),
`python tools/check/verify_schema.py`, `python tools/check/check_regression.py`.
