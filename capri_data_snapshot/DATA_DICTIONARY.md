# CAPRI-Python Data Dictionary

Schema for every input file: what it holds, its index and columns, units, and shape.
Auto-generated from `MANIFEST.json` and the code definitions; see also
`capri_data/README.md` for the folder layout.

Files are under `capri_data/<base_year>/<category>/` (trade under `capri_data/shared/`).

---

## Supply

### `animal_numbers.csv`

Animal herd/flock sizes by region and animal activity.

- **Source:** COCO &nbsp; **Vintage:** 2017 &nbsp; **Units:** 1000 head
- **Shape:** 245 rows × 11 columns
- **Columns:** `DCOW`, `SCOW`, `COWS`, `BULL`, `HEIF`, `CALV`, `PIGS`, `SOWS`

### `base_areas.csv`

Base-year crop area by region and crop activity.

- **Source:** COCO &nbsp; **Vintage:** 2017 &nbsp; **Units:** 1000 ha
- **Shape:** 248 rows × 29 columns
- **Columns:** `SWHE`, `DWHE`, `RYEM`, `BARL`, `OATS`, `CORN`, `OCER`, `PULS`

### `input_requirements.csv`

Input use per unit of activity.

- **Source:** CAPRI estimation &nbsp; **Vintage:** 2017 &nbsp; **Units:** coefficient
- **Shape:** 26375 rows × 3 columns
- **Columns:** `input`, `crop`, `requirement`

### `land_availability.csv`

Available agricultural land by region and land type.

- **Source:** CAPRI/COCO &nbsp; **Vintage:** 2017 &nbsp; **Units:** 1000 ha
- **Shape:** 248 rows × 5 columns
- **Columns:** `ARABLE`, `PERMANENT`, `GRASSLAND`, `FALLOW`, `OTHER_AG`

### `pmp_crossgroup_terms.csv`

PMP cross-commodity cost terms (calibrate substitution).

- **Source:** CAPRI estimation &nbsp; **Vintage:** 2017 &nbsp; **Units:** EUR-based
- **Shape:** 7524 rows × 3 columns
- **Columns:** `group1`, `group2`, `coef`

### `pmp_diagonal_terms.csv`

PMP quadratic cost diagonal term per region and crop.

- **Source:** CAPRI estimation &nbsp; **Vintage:** 2017 &nbsp; **Units:** EUR-based
- **Shape:** 2560 rows × 2 columns
- **Columns:** `crop`, `pmp_diagonal`

### `pmp_own_price_elasticities.csv`

Target own-price elasticities used in PMP calibration.

- **Source:** CAPRI PELA &nbsp; **Vintage:** 2017 &nbsp; **Units:** elasticity
- **Shape:** 2375 rows × 2 columns
- **Columns:** `crop`, `own_price_elas`

### `supply_elasticities_regional.csv`

Region-specific own-price supply elasticities (from CAPRI PELA).

- **Source:** CAPRI PELA &nbsp; **Vintage:** 2017 &nbsp; **Units:** elasticity
- **Shape:** 228 rows × 15 columns
- **Columns:** `BARL`, `CORN`, `DWHE`, `MAIF`, `OATS`, `OCER`, `OFOD`, `POTA`

### `variable_costs.csv`

Variable production cost per activity.

- **Source:** CAPRI &nbsp; **Vintage:** 2017 &nbsp; **Units:** EUR/ha
- **Shape:** 248 rows × 40 columns
- **Columns:** `SWHE`, `DWHE`, `RYEM`, `BARL`, `OATS`, `CORN`, `OCER`, `POTA`

### `yields.csv`

Yield per hectare (crops) or per head (animals), by region and activity.

- **Source:** COCO &nbsp; **Vintage:** 2017 &nbsp; **Units:** t/ha (crops), t/head (dairy)
- **Shape:** 248 rows × 40 columns
- **Columns:** `SWHE`, `DWHE`, `RYEM`, `BARL`, `OATS`, `CORN`, `OCER`, `POTA`


## Market

### `armington_params.csv`

Armington trade substitution parameters per commodity.

- **Source:** CAPRI &nbsp; **Vintage:** 2017 &nbsp; **Units:** elasticity
- **Shape:** 32 rows × 3 columns
- **Columns:** `sigma`, `eta`, `eps`

### `producer_prices.csv`

Base-year producer price per region and commodity.

- **Source:** CAPRI SUA &nbsp; **Vintage:** 2017 &nbsp; **Units:** EUR/t
- **Shape:** 40 rows × 1 columns
- **Columns:** `price`

### `world_prices.csv`

Base-year world/reference price per commodity.

- **Source:** CAPRI SUA &nbsp; **Vintage:** 2017 &nbsp; **Units:** EUR/t
- **Shape:** 37 rows × 1 columns
- **Columns:** `price`


## Policy

### `cap_payments.csv`

CAP direct payments (BPS, ANC, AES, organic, coupled) per region.

- **Source:** CAPRI &nbsp; **Vintage:** 2017 &nbsp; **Units:** EUR/ha
- **Shape:** 248 rows × 5 columns
- **Columns:** `BPS`, `ANC`, `AES`, `ORGANIC`, `COUPLED`

### `eu_mfn_tariffs.csv`

EU MFN import tariffs per trade region and commodity.

- **Source:** CAPRI &nbsp; **Vintage:** 2017 &nbsp; **Units:** fraction
- **Shape:** 1 rows × 32 columns
- **Columns:** `SWHE`, `DWHE`, `BARL`, `CORN`, `OCER`, `RYEM`, `OATS`, `RAPE`


## Environment

### `climate_zones.csv`

Climate-zone classification per region (for emission factors).

- **Source:** CAPRI &nbsp; **Vintage:** static &nbsp; **Units:** category
- **Shape:** 521 rows × 2 columns
- **Columns:** `zone`, `pct`

### `crop_nutrient_export.csv`

Nutrient removed by harvested crop (for N-balance).

- **Source:** CAPRI &nbsp; **Vintage:** 2017 &nbsp; **Units:** kg/t
- **Shape:** 35 rows × 3 columns
- **Columns:** `N_kg_t`, `P_kg_t`, `K_kg_t`

### `manure_ch4_ef_regional.csv`

Regional methane emission factors for manure.

- **Source:** CAPRI &nbsp; **Vintage:** 2017 &nbsp; **Units:** kg CH4/head
- **Shape:** 46 rows × 2 columns
- **Columns:** `animal`, `ch4_ef_avg`

### `nutrient_coefs.csv`

Fertiliser application rates (N, P2O5, K2O) per crop.

- **Source:** capreg DATA2 (NITF/PHOF/POTF) &nbsp; **Vintage:** 2017 &nbsp; **Units:** kg/ha N,P2O5,K2O
- **Shape:** ? rows × ? columns


## Feed

### `coco_feed_availability_national.csv`

National feed availability by feed type.

- **Source:** COCO p_FeedAgri &nbsp; **Vintage:** 2017 &nbsp; **Units:** 1000 t
- **Shape:** 28 rows × 11 columns
- **Columns:** `OCER`, `SWHE`, `BARL`, `CORN`, `OFOD`, `GRAS`, `MILK`, `SOYM`

### `feed_requirements.csv`

Per-head feed requirement (t DM/head/yr) by animal and feed item.

- **Source:** capreg DATA2 feed cols (fresh->DM) &nbsp; **Vintage:** 2017 &nbsp; **Units:** t DM/head/yr
- **Shape:** ? rows × ? columns


## Shared (cross-vintage)

### `trade_flows.csv`

Bilateral trade flows between trade regions (FAO 2021).

- **Source:** FAO &nbsp; **Vintage:** 2021 &nbsp; **Units:** 1000 t
- **Shape:** 841 rows × 33 columns
- **Columns:** `importer`, `SWHE`, `DWHE`, `BARL`, `CORN`, `OCER`, `RAPE`, `SUNF`


## Other

### `dairy_processing_params.json`

—

- **Source:** GAMS arm/def_dairy_prices &nbsp; **Vintage:** 2017 &nbsp; **Units:** cost share
- **Shape:** ? rows × ? columns

### `fao_demand_own_elas_eu.json`

—

- **Source:** FAO_agg &nbsp; **Vintage:** 2017 &nbsp; **Units:** elasticity
- **Shape:** ? rows × ? columns

### `fao_market_baseline.json`

—

- **Source:** FAO_agg SUA &nbsp; **Vintage:** 2017 &nbsp; **Units:** 1000 t
- **Shape:** ? rows × ? columns

### `fao_processing_splits.json`

—

- **Source:** FAO comm. balances + GAMS &nbsp; **Vintage:** 2017 &nbsp; **Units:** ratio
- **Shape:** ? rows × ? columns

### `gascoeff_params.json`

—

- **Source:** IPCC 2006 / CAPRI &nbsp; **Vintage:** 2006 &nbsp; **Units:** kg/head or factor
- **Shape:** ? rows × ? columns


---

## Code glossary

Activity and commodity codes used across the files:

| Code | Meaning |
|------|---------|
| `APPL` | Apples and pears |
| `BARL` | Barley |
| `BCOW` | Beef cows (suckler) |
| `BROI` | Broilers |
| `BULL` | Bulls / fattening cattle |
| `CALV` | Calves (young animals) |
| `CITR` | Citrus |
| `CORN` | Grain maize |
| `COTT` | Cotton |
| `DCOW` | Dairy cows |
| `DWHE` | Durum wheat |
| `EGGS` | Eggs |
| `GRAS` | Grass (permanent grassland/fodder) |
| `HFRS` | Heifers |
| `LAYS` | Laying hens |
| `MAIF` | Maize for forage / silage |
| `MILK` | Milk |
| `OATS` | Oats |
| `OCER` | Other cereals |
| `OFIB` | Other fibre crops |
| `OFOD` | Other fodder crops |
| `OFRU` | Other fruits |
| `OLIV` | Olives / olive oil |
| `OOIL` | Other oilseeds |
| `OVEG` | Other vegetables |
| `PIGF` | Fattening pigs |
| `PIGS` | Pigs (breeding sows) |
| `POTA` | Potatoes |
| `PULS` | Pulses |
| `RAPE` | Rape and turnip rape |
| `RYEM` | Rye and maslin |
| `SETA` | Set-aside |
| `SHGP` | Sheep and goats |
| `SOYA` | Soya beans |
| `SUFM` | Protein meals |
| `SUGB` | Sugar beet |
| `SUGR` | Sugar (beet + refined) |
| `SUNF` | Sunflower seed |
| `SWHE` | Soft wheat |
| `TAGR` | Table grapes |
| `TOBA` | Tobacco |
| `TOMA` | Tomatoes |
| `WHEY` | Dairy products |
| `WINE` | Wine |
