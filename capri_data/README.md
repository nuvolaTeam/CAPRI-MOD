# CAPRI-mod data layout

Status: revised 11 November 2026 against the code and the folder (docs/design/DATA_LAYOUT.md, steps (a)-(d)).

Every model input is CSV (or JSON), extracted from CAPRI star 3.0's data and results, or from other publishers, by a
builder in `tools/build/` that names its source; the model never reads GDX. The builders' own sources are Parquet, under
`sources/` (the one exception to the CSV rule, 3 November 2026). The folder keeps the **base years** apart from the
**baselines** projected from them:

```
capri_data/
├── 2017/                    base year 2017 (the only one): the model's inputs at CAPRI's 2017 base
│   ├── supply/              areas, yields, herds, costs, premiums, land market, intensities, PMP terms, elasticities
│   ├── market/              bilateral flows and parameters, world prices, demand, processing, dairy, biofuel, feed bulks
│   ├── policy/              CAP payments, tariffs, Green Deal target tables, mineral fertiliser rules
│   ├── environment/         emission coefficients, N balance inputs, fertiliser priors, manure losses and trade, LUC
│   ├── feed/                requirements, rations, fodder balances
│   └── abatement/           mitigation options: ammonia/ (N cascade, AD, leaching, Nitrates Directive, costs/),
│                            mitigation/ (feed, genetics, soil options), fertiliser options
├── baselines/               one folder per baseline, then one per projection <BAS><SIM> (run.baseline)
│   └── capri_greendeal_ref/ CAPRI's Green Deal baseline (res_2_1730greendeal_refdefaulta)
│       └── 1730/            its 2030 point, from the 2017 base: the same module folders as 2017/ (the files whose
│                            name carries 2030: PMP terms, land market and rents, fertiliser priors, the 2030 market,
│                            CAP ceilings ...) and trajectories/ (CAPRI's 2030 prices, premiums, rations and fodder,
│                            read by the projection layer)
├── codes/                   code lists, mappings and the unit catalogue: CAPRI's sets (capri/), the model's
│                            activities, commodities, regional units and trade regions with their CAPRI codes,
│                            model_parameters.csv (the sourced constants)
├── scenarios/               one folder per scenario or reference: settings.toml and its factors as CSV
│                            (capri_ref_2030, the default; captrd_2030; farm_to_fork_jrc121368; greendeal_group ...)
├── pipeline/                the data pipeline's inputs (CAPTRD-MOD's sets and data, the provider catalogue)
├── validation/              CAPRI reference results used by the tests and comparison tools
├── sources/                 the builders' sources as Parquet: raw/ (CAPRI's and others' values unchanged),
│                            intermediate/ (builder outputs other builders read); never read by the model
├── schema/                  SQL only: the declarations of every CSV (DuckDB SQL: types, keys, code lists, ranges,
│                            units), each file's provenance and checked notes, the numbers held in the model's code,
│                            and schema.json (the same as JSON, generated)
├── MANIFEST.json            every data file with its size and hash (generated)
├── FITNESS_FOR_USE.json     how far each output can be trusted (capri_mod/fitness.py)
└── *.md                     this file and the guides below
```

Guides in this folder:

| File | Content |
|---|---|
| `DATA_DICTIONARY.md` | each input file: content, source, shape; code glossary |
| `DATA_SOURCING_GUIDE.md` | where the data come from, how to check them, how to update them |
| `DATA_LOCATION_MAP.md`, `SYMBOL_EXTRACTION_GUIDE.md`, `DATA_ACQUISITION_REFERENCE.md` | where to find CAPRI symbols and files for a rebuild or a new base year; partly historical |
| `validation/VALIDATION.md`, `validation/HOW_TO_RUN_A_VALIDATION_SCENARIO.md` | the early validation report and how to produce a CAPRI scenario for comparison; current validation: README section 9 (Validation) |

## Base years and baselines

A CAPRI base year is self-contained: its prices, quantities and PMP parameters are calibrated together and must not
be mixed across years, so each base year has its own folder. A baseline is a projection from a base year (CAPRI's:
CAPTRD's trends and the CAPMOD run calibrated to them); it is not a base year, so it has its own folder under
`baselines/`, named by its origin, then by its years as CAPRI names its results, %BAS%%SIM% (the last two digits of
the base year and of the projection year: 1730, from 2017 to 2030). Another baseline (a Green Deal reference to 2040,
CAPTRD-MOD's own projection) goes beside it, `baselines/<name>/<BAS><SIM>/`, and a run picks it with the setting
`run.baseline` (default `capri_greendeal_ref`).

## File resolution

The model locates a file by its name (capri_mod/data/inputs.py, capri_mod/market/inputs.py and
capri_mod/data/loaders.py::resolve_data_file): a file whose name carries a year other than the base year
(`land_rents_2030.csv`) is in that year's folder of the run's baseline, `capri_mod.data.inputs.year_dir`
(`baselines/<run.baseline>/<BAS><SIM>/<module>/`); any other in the base year's (`<base year>/<module>/`);
the codes in `codes/`. The projection layer's tables are in the baseline's `trajectories/`
(`capri_mod.data.inputs.trajectories_dir`). The builders write to the same folders (tools/lib/paths.py: `data_year`).

## Adding a new base year

Not a working path yet: PMP terms and elasticities are CAPRI estimation outputs and need CAPRI's estimation for the
new year, not a copy; the planned route is the data pipeline (docs/design/CAPTRD_MOD.md: the COCO and CAPREG ports).
The readers take the base year from the run (`run.base_year`; KNOWN_ISSUES K52f).

## Checks

`python tools/check/validate_data.py` (the declarations of `schema/`: every CSV's columns, types, keys, code lists,
ranges and units, the rules, provenance, the files' catalogue with their vintages, and the crops' gross margins at the
base), `python tools/check/verify_schema.py`, `python tools/check/check_regression.py`.
