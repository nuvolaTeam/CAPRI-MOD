# CAPRI-mod Data Dictionary

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
- **Columns:** `DCOW`, `SCOW`, `COWS`, `BULL`, `HEIF`, `CALV`, `PIGS` (breeding sows), `PIGF` (fattening pigs = total pigs − sows; `tools/build_pig_split.py`), `HENS`, `POUL`, `SHGO`

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

Armington trade substitution parameters per commodity: one row per commodity the market module trades
(`definitions.MARKET_COMMODITIES` and the price-only rows), the same rows as `world_prices.csv`; biofuels BIOE and BIOD: `sigma` 2.2, `rho2` 4.5 (`special_ch/market1_ch.gms`), `eta` and `eps` 0 (biofuel quantities are fixed outside the bilateral market, the biofuel functions set them inside it).

- **Source:** CAPRI (`p_rhoArm1`, `p_rhoArm2`, literal in `arm/market1_ch.gms`) &nbsp; **Vintage:** 2017 &nbsp; **Units:** elasticity
- **Shape:** 41 rows × 4 columns
- **Columns:** `sigma` (first-stage substitution, domestic vs imports), `eta` (demand price elasticity), `eps` (supply price elasticity), `rho2` (second-stage substitution between import origins; empty where CAPRI sets none)

### `producer_prices.csv`

Base-year producer price per region and commodity.

- **Source:** CAPRI SUA &nbsp; **Vintage:** 2017 &nbsp; **Units:** EUR/t
- **Shape:** 40 rows × 1 columns
- **Columns:** `price`

### `world_prices.csv`

Base-year world market price per commodity: one row per commodity the market module trades and the price-only rows (41), the same rows
as `armington_params.csv`. Feed products, fodder and young animals have no world price (not traded in the model).

- **Source:** CAPRI `FAO_agg_17_defaulta` p_dataMarket 'World'.'PMRK'.<product>.'BAS' (code map and previous values in `sources/world_price_provenance.json`) &nbsp; **Vintage:** 2017 &nbsp; **Units:** EUR/t
- **Shape:** 41 rows × 2 columns
- **Columns:** `commodity`, `price`
- Until October 2026 the file had 43 rows: SOYA_OIL and SOYM (older names duplicating SOYO and SOYC at the same CAPRI
  prices) and WMLK, CREM (whole milk powder and cream, not in the market set) were price-only rows no module read;
  removed as orphans.


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

## Files added in October 2026

| File | Content | Source / builder |
|---|---|---|
| `2017/feed/fodder_balance_2017.json` | Regional fodder balances: usable fodder per ha, base fodder value, fodder per head | `tools/build_fodder_balance.py` (CAPRI rations, UVAG) |
| `2017/supply/land_market_2017.json` | Land-type base areas (6 types) and CAPRI land-market matrices, 236 regions | `tools/build_land_market.py` (pmppar `p_pmpQuadLandTypes`) |
| `2017/environment/nh3_factors_capri.json` | Ammonia shares of excreted N per animal and of mineral N, 244 regions | `tools/build_nh3_factors.py` (CAPRI 2030 reference) |
| `2017/supply/young_animals_2017.json` | CAPRI's young-animal flows per model head (calves, young cattle, replacement cows, piglets: produced and used per head, base net, base value) | `tools/build_young_animals.py` (res_17); CAPRI's young-animal markets (`CAPRIModel._update_young_animal_prices`) |
| `2017/supply/livestock_product_value_coef.csv`, `livestock_product_value_by_market_coef.csv` | Value of an animal's final products (no young animals) per model head, total and by market (`ACT.MARKET`, e.g. `DCOW.MILK`, `DCOW.BEEF`): CAPRI quantity x national UVAG x LEVL / model heads. What a meat, milk or egg price change moves (quantity x price change) and the product share in livestock supply elasticities | `tools/build_pig_split.py` → `build_livestock_output_coef.build_product_values_by_market` (res_17) |
| `2017/supply/mineral_n_price.csv` | Mineral fertiliser N unit value per country; not used by the default model | CAPRI 2017 national UVAG NITF |
| `2017/environment/manure_pool_costs.json` | CAPRI's 34 manure pools and 930 trade-cost links | `tools/build_manure_pool_costs.py` (CAPRI distance matrix) |
| `2017/abatement/ammonia/*.csv` | CAPRI's ammonia-technology inputs: control strategies, reduction factors, relative emissions, grazing fractions, Nitrates-Directive shares, peat shares, holdings by size class (10 files) | `tools/build_ammonia_tech_inputs.py` (CAPRI `dat\miterra`, `dat\scen\ghgtech`, `dat\envind` exports); not yet used by the model |
| `2017/abatement/ammonia/costs/*.csv` | Cost tables of CAPRI's ammonia technologies (investment, storage time, input demands and prices, application costs, grassland shares, N per m3, Nitrates-Directive storage) | `tools/build_ammonia_cost_tables.py` (tables A1-A10 in CAPRI `envind/ammo_tech.gms`) |
| `2017/abatement/ammonia/p_Heads.csv`, `capri_mann_days_2030.csv` | Heads by farm-size class; manure N and days per cycle per CAPRI region and animal activity (2030 reference) | `tools/build_ammonia_herd_inputs.py` |
| `2017/abatement/ammonia/ammonia_cost_curves.csv` | CAPRI's ammonia-technology cost curves (alpha, beta, lower bound) per region, activity, manure system and technology | `tools/build_ammonia_cost_curves.py` (reproduces `ammo_tech.gms` m_CostAmm); not yet used by the model |
| `2017/abatement/ammonia/ammonia_technologies.csv`, `ammonia_technology_effects.csv` | CAPRI's ammonia-option entries of the technology table (costs, initial and maximum shares, applicability, remaining NH3) and their side effects on other gases, per region and animal activity; shares match CAPRI's endotech runs | `tools/build_ammonia_technologies.py`; not yet used by the model |
| `2017/abatement/ammonia/ammonia_tech_model.csv` | CAPRI's ammonia options per model region, animal and CAPRI sub-activity: weight, stock factor, manure-N weight, group (NH3MAN/NH3APP), cost, CAPRI-calibrated slope and early-adopter threshold, initial and maximum shares, NH3 cuts at housing/storage/application, grazing share and MITERRA loss fractions | `tools/build_ammonia_tech_model.py`; `capri_mod/supply/ammonia_techs.py` |
| `sources/arm/capri_supply_elas_young_1720.csv` | CAPRI's calibrated supply elasticities of young animals per member state (YCAM, YCAF, YBUL, YHEI, YCOW; 2020 calibration) | `tools/build_young_animal_elasticities.py`; weights cattle elasticities in `capri_pmp.build_elasticity_table` |
| `2017/abatement/fert_options_jul15.csv` | CAPRI's fertiliser-efficiency options from miti_data_jul15 (national; regional VRT_SRUC): costs, PMP terms, relative subsidies, shares, QEmitt and no-control QEmitt | `tools/build_fert_options_jul15.py` from `sources/ghgtech/miti_data_jul15_p_ghgMiti.txt`; `RegionalSupplyModel._fert_techs` |
| `2017/environment/capri_crop_n_coefs_2030.csv` | CAPRI 2030 reference per region and crop: level, yield, NITF export coefficient, NCRD (residues + deposition, kg/ha), biological fixation (1000 t) | `tools/build_capri_crop_n_coefs.py`; `EnvironmentalModule._capri_crop_n` (gross N balance) |
| `2017/environment/capri_gnb_components_2030.csv` | CAPRI 2030 gross N balance items per region (kg N/ha): EXPPRD, CRESID, ATMOSD, BIOFIX, MINFER, EXCRET, MTRADE, SURTOT, residue unavailability and losses | `tools/build_capri_gnb_components.py`; scaling of per-crop coefficients, residue availability |
| `sources/eurostat/aei_pr_gnb_nitrogen.csv` | Eurostat gross nutrient balance, nitrogen, member states 1985–2023 (inputs, outputs, balance; tonnes and kg/ha) | validation only: `tools/validate_gnb_eurostat.py` |
| `2017/abatement/active_technologies.csv` | CAPRI's active mitigation options in its Green Deal reference (activeTech: ammonia, fertiliser, feed, carbon, other) | `tools/build_active_technologies.py` from `pol_input/greendeal/refpol_endotech_all_sup.gms`; filters the fertiliser options |
| `2017/abatement/mitigation/*.csv` | Inputs of CAPRI's feed-additive, genetics and soil options: dairy milk yields from CAPRI's 2030 baseline trends, tillage and cover-crop shares, ecological-focus-area cover crops, initial winter-cover shares, nutrient contents of feedstuffs | `tools/build_mitigation_inputs.py` (CAPRI `results\baseline\trends_1730`, `dat\envind`, `dat\policy`, `dat\feed`); not yet used by the model |
| `2017/supply/livestock_cost_coef.csv`, `livestock_output_value_coef.csv` | Livestock total inputs (TOIN) and total output (TOOU) per model head: CAPRI's regional totals / the model's head counts, the same basis as livestock revenue and output | `tools/build_livestock_output_coef.py` (capreg dumps) |
| `2017/environment/enteric_feed_factors.csv` | Gross energy (Mcal/kg DM) per country, cattle type and feed group, and Ym, for CAPRI's feed-based cattle enteric methane | `tools/build_enteric_feed_factors.py` (CAPRI `envind/def_digestibility.gms` NRC table, `create_rawdat_gascoeff_gdx.gms` IPCC table, `sets.gms` FEED_TO_O, capreg feed use) |
| `2017/environment/crop_nut_need_mult_fact_2030.csv` | CAPRI's over-fertilisation factor x (p_CropNutNeedMultFact, NITF, 2030) per region, limiting the fertiliser-efficiency technologies (Tot_MitFert_, regional maximum shares) | `tools/build_overfert_factors.py` (gdxdump of CAPRI `results\fert\priFertDist_<MS>1730defaulta.gdx`) |



### CAPRI 2030 prices (`trajectories/`)

| File | Content | Built by |
|---|---|---|
| `trajectories/capri_price_ratios_2030.csv` | member state, CAPRI product: UVAG 2017 and 2030, input deflator, real ratio (2030 price in 2017 money / 2017 price) | `tools/build_price_trajectory_2030.py` |
| `trajectories/capri_cap_premium_2030.csv` | model region × CAPRI activity: CAPRI's 2030 premium per unit in 2017 money | same |
| `trajectories/capri_livestock_premium_ratio_2030.csv` | model region × model animal: 2030/2017 premium ratio (real, 2017 activity-level weights) | same |
| `validation/greendeal_2030/capri_marginal_terms_{ini,max}_2030.csv.xz` (xz-compressed), `capri_unit_values_{ini,max}_2030.csv` | CAPRI's Farm-to-Fork reference: per-activity marginal terms (D_*), LEVL, MREV, TOOU, TOIN, MANN, PRME; national unit values | `tools/extract_capri_marginal_terms.py` |
| `sources/capri_baseline/capri_uvag_store_1730.csv` | CAPRI's calibrated 2030 unit values (p_uvagStore), member state × product | gdxdump of `data_uvag1730defaulta` |
| `sources/capri_baseline/capri_market_prices_1730.csv` | CAPRI market baseline prices (PPRI, CPRI) at the 2017 (BAS) and 2030 (CAL) points, member state × product | gdxdump of `data_market_1730defaulta` |
| `2017/supply/grass_intensity.csv` | CAPRI's two grassland activities per model region: extensive share of GRAS (share_ext), yields relative to the GRAS mean (yield_ext_rel, yield_int_rel), areas, CAPRI's PMP diagonal terms (q_ext, q_int, EUR/ha per 1000 ha) and their source | `tools/build_grass_intensity.py` (res_17, p_pmpQuadTechn) |
| `2017/supply/dairy_intensity.csv` | CAPRI's two dairy-cow activities per model region: low-yield share of DCOW, per-head changes from DCOH to DCOL relative to the average cow (milk, manure N, energy, protein, dry-matter limits), CAPRI's PMP diagonal terms (q_low, q_high) and their source | `tools/build_dairy_intensity.py` (res_17, p_pmpQuadTechn) |
| `2017/supply/cattle_intensity.csv` | CAPRI's low/high-intensity fattening bulls (BULL/BULH) and heifers (HEIL/HEIH) per model region and animal: stall shares, fattening days, per-stall changes from high to low relative to the animal's average (manure N, beef, young animals, energy, protein, dry-matter limits), PMP curvature of the stall shift (q_z) and its source | `tools/build_cattle_intensity.py` (res_17, p_pmpQuadTechn) |
| `2017/supply/livestock_output_by_product_coef.csv` | Each animal's output by CAPRI final product, columns `ACT.PRODUCT` (kt per 1000 head; sums to livestock_output_coef): the market bridge sends cull-cow beef to beef, sheep and goat milk to raw milk, hen meat to poultry | `tools/build_livestock_products.py` (res_17) |
| `2017/market/biofuel_feedstock.csv` | First-generation biofuel feedstocks per CAPRI market region (`ms`; `region` = model trade region) and biofuel: 2030-reference quantity (kt), biofuel yield PRCB, by-product yield PRCBY, feedstock and by-product prices, numeraire, CES elasticity | `tools/build_biofuel_market.py` (CAPRI 2030 market results) |
| `2017/market/biofuel_market.csv` | CAPRI's biofuel supply (SupplyBiof_), demand (biofDemShare_, biofDem_) and non-fuel processing (ProcNQ_: proc_kt, proc_hess, inpe) functions per CAPRI market region and biofuel, calibrated as `biofuel/def_biofuel_params.gms`: output and first-generation output (kt), fixed NAGR+SECG+EXOG output, producer price, feedstock cost per t biofuel, processing margin PR0, supply scale/alfa/beta/slope/turn; biofuel use (kt), consumer and Arm1 prices, fossil fuel price, total fuel use (kt, fossil + biofuel in fossil equivalents), oil equivalents, mandate share QUTS, observed share, demand MAX/Slope/Turn | `tools/build_biofuel_market.py` |
| `2017/market/biofuel_use_share.csv` | Biofuel share of EU use per market commodity (CAPRI 2030 reference) | `tools/build_biofuel_market.py` |
| `2017/abatement/mitigation/lownfeed_effects.csv` | CAPRI's low-nitrogen feeding per region and animal: protein requirement and manure N change, eligible share, cost (envind/low_n_feed.gms) | `tools/build_lownfeed_effects.py` |
| `2017/abatement/mitigation/supplement_effects.csv` | CAPRI's feed supplements linseed and nitrate per region and cattle animal: requirement changes, eligible share, cost, CH4ENT change (envind/line_nitr.gms) | `tools/build_supplement_effects.py` |
| `2017/environment/fert_dist_priors_2030.csv` | Priors of CAPRI's inner fertiliser distribution model per CAPRI region (and country fallback, `level` nuts0) and crop group: area (1000 ha), mineral/manure/residue N per ha (kg), accuracy, mineral efficiency, manure availability | `tools/build_fert_dist_priors.py` |
| `2017/environment/fert_dist_crop_groups_2030.csv` | Model crop -> CAPRI crop group (NGRP) area shares per CAPRI region | `tools/build_fert_dist_priors.py` |
| `2017/policy/mineral_redu_exemptions.csv` | CAPRI's listed exemptions from the crop-specific mineral fertiliser reduction (factor x baseline, from year, othPol high) | `tools/build_mineral_redu_rules.py` |
| `2017/policy/mineral_redu_limcres.csv` | CAPRI's relaxations of the limCres regulation by year | `tools/build_mineral_redu_rules.py` |
| `2017/market/feed_bulks_eu.csv` | CAPRI's feed bulks per member state (FCER cereals, FPRO protein-rich feed incl. DDGS and FPRI, FENE energy-rich, FOTH other, FMIL milk products): products, model commodity, 2030 feed use (kt), EU Arm1 price (EUR/t), CES elasticity p_rhoFeed (feedBlkPrice_, feedShareEqu_) | `tools/build_feed_bulks.py` |
| `2017/market/feed_byproducts.csv` | CAPRI's residual feeds FENI, FPRI (MaprFeed_): EU 2030 output (kt) and parent commodities' weights (food/processing or biofuel use) | `tools/build_feed_byproducts.py` |
| `2017/market/feed_bulks_eu_share.csv` | Feed share of EU use per model commodity in the bulks (CAPRI 2030 reference) | `tools/build_feed_bulks.py` |
| `2017/market/dairy_processing.csv` | CAPRI's dairy block per member state: product and raw milk quantities, processing, fat and protein contents (%), prices, CSEI, INPE, fat and protein prices | `tools/build_dairy_processing.py` |
| `2017/market/dairy_hessian.csv` | Hessian of CAPRI's dairy NQ function per member state (symmetric, MILK row reversed) | `tools/build_dairy_processing.py` (elas_2_1730 p_hessNQDairy) |
| `2017/market/dairy_eu_balance.csv` | EU27 balance of nine dairy products and HCOM-weighted own-price demand elasticity | `tools/build_dairy_processing.py` |
| `2017/market/bilateral_flows_<year>.csv` | CAPRI's bilateral flows per (importer, exporter) and commodity, 2017 base market and 2030 reference: quantity (kt), import price split into exporter-price part a and fixed part b (EUR/t), a0, ad valorem tariff | `tools/build_bilateral_market.py` |
| `2017/market/bilateral_regions_<year>.csv` | CAPRI market price (PMRK) and production per model trade region | `tools/build_bilateral_market.py` |
| `2017/market/bilateral_trq_<year>.csv` | EU tariff-rate quotas per model exporter: quota (kt), out- minus in-quota price gap (EUR/t), imports under the quota regime | `tools/build_bilateral_market.py` (build_trq) |
| `2017/market/armington_rho.csv` | Armington substitution elasticities rho1, rho2 per market commodity | `tools/build_bilateral_market.py` (market1.gms, market1_ch.gms) |
| `2017/market/processing_yields.csv` | Olive oil per tonne of olives (member state), milled rice per tonne of paddy (EU) | `tools/build_processing_yields.py` |
| `2017/market/world_market_baseline.json` | Base balances (production, domestic use, imports, exports) of 32 market commodities per model trade region (kt); the EU's base self-sufficiency | `tools/build_world_market_baseline.py` (FAO_agg BAS) |
| `2017/market/sugar_processing.csv` | CAPRI's sugar processing per member state: beet harvested and processed, white sugar, PRCY, sugar per beet | `tools/build_sugar_processing.py` (2030 reference) |
| `2017/market/dairy_world_baseline.json` | World base balances of butter, SMP, cheese, whey per model trade region (kt) | `tools/build_dairy_world_markets.py` (FAO_agg BAS) |
| `2017/market/dairy_eu_demand_elas.csv` | EU food demand elasticities among the nine dairy products, own and cross (CAPRI p_ElasDem, HCOM-weighted) | `tools/build_dairy_processing.py` |
| `2017/market/dairy_world_processing.csv` | CAPRI's dairy block for the non-EU market regions: products, raw milk, contents, prices, food and feed use, extra-regional trade; MILKSUP = raw milk supply slope | `tools/build_dairy_world_blocks.py` |
| `2017/market/dairy_world_hessian.csv` | Dairy NQ Hessians of the non-EU market regions | `tools/build_dairy_world_blocks.py` |
| `2017/market/dairy_world_demand_elas.csv` | Food demand elasticities among the nine dairy products, non-EU regions | `tools/build_dairy_world_blocks.py` |
| `2017/abatement/mitigation/genetics_effects.csv` | CAPRI's cattle genomics per region and animal (genet_yld, genet_eff): eligible share, relative changes of milk, energy, protein, dry matter and manure N per adopting head PER UNIT of the technology parameter (tech_param), cost floor and per-unit cost, relSubs0/1; scaled at run time by the scenario's settings | `tools/build_genetics_effects.py` (breeding.gms) |
| `shared/region_capri_map.csv` | Model region -> CAPRI region (per-unit values), CAPRI group and relation (one-to-one, split, merge, none), for the runtime | `tools/build_region_map.py` (tools/_model_regions.py) |
| `2017/environment/histosol.csv` | CAPRI's histosols per model region: organic-soil share of cropland and grassland, climate-weighted IPCC 2013 N2O factor, N2O/CO2/CH4 per ha of the class, and the fallowing option's calibration (costsaving0/1, MaxShare, PMP terms) | `tools/build_histosol.py` |
| `2017/environment/manure_n2o_factors.csv` | CAPRI's manure N2O by stage per region and animal: t N2O-N per t manure N for housing/storage (f_man), application (f_app), grazing (f_gra), leaching (f_lea) | `tools/build_manure_n2o.py` (res_17) |
| `2017/environment/manure_n2o_tech.csv` | CAPRI's ammonia technologies' relative effects on housing/storage (r_hou) and application (r_app) N2O, per region, animal and option | `tools/build_manure_n2o.py` |
| `2017/supply/plant_protection_cost.csv` | CAPRI's plant protection (PLAP x UVAG), other inputs (INPO) and fertiliser (FERT) costs per ha, per model region and crop; the pesticide and organic instruments use them | `tools/build_plant_protection_cost.py` (res_17) |
| `2017/supply/cover_crops.csv` | CAPRI's catch crops per model region: 2030 area as a share of UAAR, cost per ha (TOIN), N from fixation and residues per ha (BioFix from p_cInput) | `tools/build_cover_crops.py` |
| `2017/supply/winter_cover_share.csv` | Share of each crop's area under winter cover: as given in CAPRI (share0) and filled NUTS2 <- member state <- EU (share) | `tools/build_cover_crops.py` (wintercovershare.gms) |
| `2017/abatement/fert_side_effects.csv` | CAPRI's literature-review side effects of nitrification inhibitors: mineral N (N2OSYN, NH3SYN) and applied manure (NITR_INH_MAN: NH3APP, N2OAPP), relative change of emissions | `tools/build_fert_side_effects.py` (p_litRevFertTechs) |
| `validation/coupled_support_2030/capri_vcs_effect.csv.xz` | CAPRI 2030: reference vs no voluntary coupled support (levels, premiums, prices) | `tools/extract_capri_vcs_pair.py` |
| `sources/ghgtech/capri_costsavings_2030.csv` | CAPRI's mitigation calibration runs (ini, max): v_Miti levels and marginals | `tools/extract_capri_costsavings.py` |
