# Archive

Files kept for reference. **Not read by the model at runtime** — but they contain
real, sourced CAPRI data worth preserving.

## Parameter files (not currently wired in)

- **`gascoeff_params.json`** — CAPRI's full GWP / emission-factor set (N2O = 310,
  CH4 = 21, i.e. IPCC SAR values, across all emission categories). The
  environmental module currently hardcodes a subset of these
  (`EF_ENTERIC_CH4`, `EF_MANURE_CH4`, N2O factors). Source: CAPRI
  `envind/gascoeff.gms`. Useful if the environmental module is extended to the
  full CAPRI emission accounting, or if GWP variants (SAR / AR4 / AR5) are made
  switchable.

- **`dairy_processing_params.json`** — dairy **processing cost shares**
  (procCostShare per product), a CAPRI→model code map, regional multipliers, and
  the milk/dairy markup. Source: CAPRI `arm/def_dairy_prices.gms` (Wiss. Beirat
  BML 2000, p.64). Note this is *distinct* from `fao_processing_splits.json`
  (which holds physical **yield** coefficients, e.g. milk→butter): these are
  **price/cost margins**. Useful if dairy price formation is modelled explicitly.

## Superseded data

- `base_areas_coco.csv`, `base_areas_eurostat.csv` — earlier vintages of base areas.
- `trade_flows_2005_backup.csv` — superseded trade vintage (live trade is FAO 2021).
