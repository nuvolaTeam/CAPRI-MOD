# CAPRI-mod data layout

Data is organised by **base year**, then by **module category**:

```
capri_data/
  2017/                     base year (self-contained, mutually consistent)
    supply/                 areas, yields, herds, costs, PMP params, elasticities
    market/                 producer & world prices, Armington params,
                            FAO baseline/processing/elasticity JSONs
    policy/                 CAP payments, tariffs
    environment/            fertiliser N/P/K, manure, climate zones
    feed/                   rations, requirements, fodder balance
    abatement/              CAPRI's mitigation options (ammonia, fertiliser, breeding, feed)
  shared/                   cross-vintage data not tied to one base year
    trade_flows_2017.csv    bilateral trade (CAPRI 2017)
  trajectories/             CAPRI's 2030 trend projection and prices
  validation/               validation reports & CAPRI reference values
  sources/                  provenance: raw extracts the builders read, unit notes
    fao_2021/               FAOSTAT 2021 extracts (not read by the model)
  archive/                  superseded files
  MANIFEST.json             per-file source / vintage / units / shape
  DATA_SOURCING_REGISTRY.json  per-dataset nature (real CAPRI / FAO)
```

## Why base-year-first

A CAPRI base year is **self-contained**: its prices, quantities, and PMP
parameters are calibrated together and must not be mixed across years. Keeping
each base year in its own top-level folder enforces that consistency — a model
run selects one year folder and everything inside is guaranteed to match.

## Adding a new base year

1. Create `capri_data/<year>/` with the same five category subfolders.
2. Place that year's CAPRI files in the matching category (same filenames).
3. Load it with `CAPRIModel(data_dir="capri_data", base_year="<year>")`
   (loaders resolve `<data_dir>/<base_year>/<category>/<file>`).
4. Keep genuinely cross-vintage inputs (e.g. a trade year) in `shared/`.

## File resolution

`capri_mod/data/loaders.py::resolve_data_file` maps each filename to its
category and base year, with a flat-layout fallback for backward compatibility.
