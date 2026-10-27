# CAPRI-mod data sourcing guide

Status: revised 20 October 2026 against the code and the data. Answers: which data, which vintage, is it CAPRI's,
and where a better or newer version would come from.

## 1. Current state

The model runs on CAPRI's data only: the loaders raise when a file is missing, and there is no synthetic generator or
generic fallback left (docs/SYNTHETIC_DATA_AUDIT.md). The validator
(`python -m capri_mod.data.validate_data capri_data`, or `load_all_data(validate=True)`) reported on 20 October 2026:

- 12 pass, 1 warning (a stale row count in MANIFEST.json for `fert_side_effects.csv`), 0 fail;
- "no live synthetic data"; provenance of the registry's datasets: 38 CAPRI, 4 FAO, 0 synthetic.

| Block | Vintage | Source |
|---|---|---|
| Base data: areas, yields, prices, costs, premiums, herds' coefficients, PMP terms, elasticities | 2017 | CAPRI star 3.0's 2017 regional results (`res_17<MS>`, capreg DATA2), estimation outputs (PMP, PELA), FAO_agg |
| Herds | 2017 | CAPRI's herd sizes (DATA2 HERD), not its activity levels (registered); per-head coefficients are CAPRI's totals over them |
| Market | 2017 base and CAPRI's 2030 reference | CAPRI's bilateral market (`bilateral_flows_<year>.csv`), FAO_agg balances and prices, CAPRI's demand, processing, dairy, biofuel and feed parameters |
| Projection | 2030 | CAPRI star 3.0's 2030 Green Deal reference (`trajectories/capri_ref_2030.json`), CAPRI's 2030 prices, premiums, rations and fodder |
| Mitigation options, N cascade, leaching | CAPRI's Green Deal reference and its option data | CAPRI's mitigation data (`miti_data_jul15`), MITERRA tables, CAPRI's literature review |
| Constants | – | `shared/model_parameters.csv`, each with its source |

What is still not CAPRI's data, and where it acts: docs/SYNTHETIC_DATA_AUDIT.md, "Current state".

Known inconsistencies in the metadata (the data themselves are not affected):

- `DATA_SOURCING_REGISTRY.json` still describes `trade_flows.csv` as FAO 2021 and `world_prices.csv` as "CAPRI SUA,
  partially resolved", while MANIFEST.json records `shared/trade_flows_2017.csv` as recalibrated from CAPRI's
  capmod `res_0_1717` and `world_prices.csv` as CAPRI's FAO_agg PMRK; its `code_embedded_data` section names a
  biofuel module that no longer exists.
- MANIFEST.json still gives `base_areas.csv` and `yields.csv` the source "COCO" and shape notes from before Sprint 9s.

## 2. How the files fit together

- **`DATA_SOURCING_REGISTRY.json`**: per dataset, its nature (REAL_CAPRI, REAL_FAO, MIXED_BY_COLUMN, ...), vintage,
  source and the fixes made; also a log of findings. `tools/check/check_doc_coverage.py` checks that its significant
  entries are mentioned in README.md, CHANGELOG.md or docs/DATA_FIXES.md.
- **`MANIFEST.json`**: every live file's source, units, domain and expected shape; the validator compares the files
  with it.
- **`INPUT_SCHEMA.json`, `INPUT_MANIFEST.json`**: the declared inputs and where each must come from
  (`tools/check/verify_schema.py`; `test_schema_declares_every_input_and_all_files_exist`).
- **`FITNESS_FOR_USE.json`**: how far each output can be trusted (`capri_mod/fitness.py`).
- **The builders** (`tools/build_*.py`): each names its CAPRI source in its docstring. They need CAPRI's result
  dumps and code, which are not shipped; the data as shipped is what the model and the tests use.

Run the validator before trusting any run after a data change.

## 3. Updating the data

Three tiers, most consistent first:

1. **CAPRI's own results** (`results/{global,capreg,baseline,capmod,...}` of a CAPRI installation): best for
   consistency, because prices, quantities and PMP terms were estimated together. GDX files are converted to CSV with
   `tools/build/gdx_dump_symbol.py GDX SYMBOL OUT.csv` (needs the `gamsapi` package and GAMS's gdx library) or GAMS
   `gdxdump`. Where to find each symbol: `DATA_LOCATION_MAP.md`, `SYMBOL_EXTRACTION_GUIDE.md`,
   `capri_mod/data/find_symbol.py`.
2. **Public statistics** (FAOSTAT, Eurostat): more recent, but in other units and codes (FAOSTAT prices in USD,
   duplicate milk codes); mixing recent values into a 2017 base breaks its consistency. Used here only for checks
   (e.g. `sources/eurostat/aei_pr_gnb_nitrogen.csv`, `validation/eu_outlook_2020_2030.csv`).
3. **CAPRI network, JRC, published studies**: scenario results for validation (JRC121368) and methodology, not raw
   input data.

Rule: a full re-base must move prices, quantities and PMP terms to the same year, from CAPRI's own estimation. The
PMP terms and elasticities (CAPRI's `pmp_quad_techn`, `pmp_quad_pact` and their 2030 exports,
`pmp_own_price_elasticities`, `supply_elasticities_regional`) are estimation outputs: a new base year needs CAPRI's
PMP/PELA estimation for that year, not a copy of the 2017 terms. The model's `base_year` switch is not complete yet
(`capri_data/README.md`).

## 4. History

The guide was first written when two inputs, `feed_requirements.csv` and `nutrient_coefs.csv`, were generated by
the loader with random noise; both were replaced with capreg DATA2 values (registry: `REAL_CAPRI`). The remaining
synthetic items found later (premiums, costs, fibre yields, wine prices, tariffs, methane and CO2 factors) were
replaced in Sprints 9r-9t (docs/SYNTHETIC_DATA_AUDIT.md).
