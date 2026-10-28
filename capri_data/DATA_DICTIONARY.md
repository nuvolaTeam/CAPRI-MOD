# CAPRI-mod data dictionary

Status: revised 20 October 2026 against the code and the files; the core tables (shapes, sources, shared files)
revised again on 27 October 2026, after the move to CAPRI's 221 regional units. Shapes are rows × columns, the index
or key column not counted. The folder layout is in `capri_data/README.md` and README
section 6; per-file source, vintage and units are also in `MANIFEST.json` and `INPUT_SCHEMA.json`, and provenance in
`DATA_SOURCING_REGISTRY.json`. MANIFEST.json is not regenerated automatically and lags the files in places (shapes of
`world_prices.csv`, `armington_params.csv`, `fert_side_effects.csv`; sources of `base_areas.csv`, `yields.csv`).

Files are under `capri_data/<base_year>/<category>/` (only `2017/` exists); `trade_flows.csv` resolves to
`capri_data/shared/trade_flows_2017.csv` (`capri_mod/data/loaders.py::resolve_data_file`).

---

## Core files

### Supply (`2017/supply/`)

| File | Content | Source | Shape |
|---|---|---|---|
| `base_areas.csv` | base-year crop area by region and crop activity (1000 ha) | CAPRI 2017 regional results (capreg DATA2 LEVL; `tools/build/build_capri_base.py`) | 221 × 34 (all crop activities and OCRO, OIND, NURS, FLOW) |
| `yields.csv` | yield per ha (crops, t/ha; GRAS fresh matter kg/ha, converted at load) or per model head (animals: CAPRI's YILD / 1000, t of milk or meat; sows and hens in CAPRI's output unit / 1000) by region and activity | CAPRI 2017 regional results; crop columns rebuilt in Sprint 9s (`tools/build/build_crop_economics_2017.py`); animal columns from CAPRI's YILD on 23 October 2026 (`tools/build/build_animal_yields.py`; the load-time unit rescaling was removed) | 221 × 46 |
| `animal_numbers.csv` | herds by region (1000 head) | CAPRI 2017 regional results, DATA2 HERD (`tools/build/build_capri_base.py`); per-head coefficients are CAPRI's totals over these heads | 221 × 12: `DCOW`, `SCOW`, `COWS`, `BULL`, `HEIF`, `CALV`, `PIGS` (breeding sows), `PIGF` (fattening pigs = census pigs − sows; CAPRI's PIGF herd where CAPRI has no census total: DEA20000, DEB10000, FI200000), `HENS`, `POUL`, `SHGM`, `SHGF` (CAPRI's HERD) |
| `variable_costs.csv` | variable cost per activity (EUR/ha) | CAPRI DATA2 TOIN (Sprint 9s for crops; `tools/build/build_crop_economics_2017.py`, `build_shg_split.py`) | 221 × 46 |
| `crop_premium.csv` | CAP premium per region and model crop (EUR/ha) | CAPRI DATA2 PRME (`tools/build/build_crop_economics_2017.py`) | 221 × 34 |
| `land_availability.csv` | land by type (1000 ha): `ARABLE`, `PERMANENT`, `GRASSLAND`, `FALLOW` (`OTHER_AG` dropped on 27 October 2026: no builder) | CAPRI 2017 regional results (`tools/build/build_capri_base.py`) | 221 × 4 |
| `pmp_own_price_elasticities.csv` | own-price elasticities for the PMP calibration, per CAPRI region (228, member states included) and crop | CAPRI PELA | 2,375 rows |
| `supply_elasticities_regional.csv` | regional own-price supply elasticities, keyed by model region | CAPRI estnlp PELA with CAPRI's dampening rule (`tools/build/build_supply_elasticities_regional.py`) | 198 regions × 15 crops |

### Market (`2017/market/`)

| File | Content | Source | Shape |
|---|---|---|---|
| `world_prices.csv` | base-year world market price (EUR/t) | CAPRI `FAO_agg_17_defaulta` p_dataMarket 'World'.'PMRK'.<product>.'BAS' (code map and previous values in `sources/world_price_provenance.json`) | 62 rows: the 58 market commodities plus `DWHE`, `SUGB` (price-only rows) and `FATS`, `OFOD_M` (rows of removed markets, not read) |
| `armington_params.csv` | per commodity: `eps`, the own-price supply elasticity used for EU market supply where CAPRI's EU p_elasSupp file (`sources/arm/supply_elas_eu_all.json`) has no value (0 for products supplied only by their blocks) | dairy and residual feeds: tools/build/build_dairy_trade_params.py, build_feed_byproducts.py; the rest of unrecorded source (K72). The Armington elasticities are CAPRI's `p_rhoArm1`, `p_rhoArm2` in `armington_rho.csv`; the former `sigma`, `rho2` and `eta` columns were removed on 24 October 2026 (unused; no generic demand elasticity under CAPRI's Armington balance) | 62 rows, the same as `world_prices.csv` |
| `producer_prices.csv` | EU-wide producer price per commodity (EUR/t), the fallback where no regional price exists | CAPRI's production-weighted EU price (`tools/build/build_eu_producer_prices.py`, K34) | 42 rows |
| `fao_market_baseline.json` | market base balances by `region|product` (read by tools/build/build_world_market_baseline.py) | CAPRI FAO_agg (2017) | dict of 454 entries |

### Policy (`2017/policy/`)

| File | Content | Source | Shape |
|---|---|---|---|
| `cap_payments.csv` | payment engine rates per region (EUR/ha); `BPS` = CAPRI's premiums per ha of UAA over all schemes; `ANC`, `AES`, `ORGANIC`, `COUPLED` = 0 and unused (the split by scheme comes from `premium_scheme_shares_2030.csv`) | CAPRI PRME (`tools/build/build_crop_economics_2017.py`) | 221 × 5 |
| `cap_ceilings_2030.csv` | CAPRI's 2030 budgets by premium scheme, Mio EUR, per CAPRI member state and NUTS2 region: DPPIL1, DPPIL2, DPRD_LFA, DPRD_N2K, DPAE, DPNAT, DPTOTAL; the payments report's national envelopes (DPTOTAL) | CAPRI 2030 reference, dataOut CEILVAL (`tools/build/build_cap_ceilings_2030.py`) | 289 × 7 |
| `premium_scheme_shares_2030.csv` | per model region and activity, the part of the premium paid under DPPIL1, DPRD_LFA, DPRD_N2K, DPAE and DPNAT (sums to 1); Pillar II budget changes and the report's split by scheme | CAPRI 2030 reference, dataOut PRME by scheme / DPTOTAL, LEVL-weighted (`tools/build/build_cap_ceilings_2030.py`) | 8,709 rows (221 regions) |
| `tariffs.csv` | ad valorem protection per trade region and commodity | CAPRI's total protection from its 2017 bilateral flows (Sprint 9r; `tools/build/build_tariffs_2017.py`) | 30 × 52 |
| `eu_mfn_tariffs.csv` | EU import tariffs per commodity (fraction) | CAPRI | 1 × 32 |

### Environment (`2017/environment/`) and feed (`2017/feed/`)

| File | Content | Source | Shape |
|---|---|---|---|
| `nutrient_coefs.csv` | N, P2O5, K2O per ha of crop (the per-head animal rows of unrecorded source removed with the legacy nitrate-limit instrument, K33) | capreg DATA2 NITF/PHOF/POTF | 29 × 3 |
| `crop_nutrient_export.csv` | nutrient removed per t of crop (`N_kg_t`, `P_kg_t`, `K_kg_t`) | CAPRI | 35 × 3 |
| `climate_zones.csv` | climate-zone shares per CAPRI region or member state (`region`, `zone`, `pct`; 145 codes); read by `tools/build/build_ad_option.py`, not by the model | CAPRI | 521 rows |
| `feed_requirements.csv` | feed per head (t DM/head/yr) by animal and feed item | capreg DATA2 feed columns, fresh to dry matter | 9 animals × 11 feeds |

### Shared (`shared/`)

| File | Content |
|---|---|
| `trade_flows_2017.csv` | bilateral trade by exporter and importer (1000 t; 601 rows × 39 commodities); per MANIFEST.json recalibrated from CAPRI capmod `res_0_1717` (2017); not read by the model (an input of tools/check/validate_world_prices.py and tools/build/recalibrate_trade_2017.py); the bilateral market reads `2017/market/bilateral_flows_<year>.csv` |
| `regional_units.csv` | the model's regions: CAPRI's 221 regional units of the EU27 and Norway (8-character codes), their CAPRI member state and NUTS-0 country (`tools/build/build_regional_units.py`; `capri_mod/data/definitions.py`) |
| `capri_units_nuts2024.csv` | CAPRI unit → NUTS 2024 region, for reporting: group (connected set of units and regions), Eurostat UAA and the weight of each region in its group (`tools/build/build_nuts2024_reporting.py`; `capri_mod/nuts_reporting.py`) |
| `nuts_version_correspondence.json` | CAPRI codes → NUTS codes (kept for reporting; the model reads no region map since 27 October 2026: each region is its own CAPRI region) |
| `capri_member_state_codes.csv` | NUTS country prefix → CAPRI member state (see the row further down) |
| `rms.csv`, `rms_to_rm.csv` | CAPRI's market regions (RMS) and their trade blocks (RM); written by `tools/build/build_gl_demand.py`, read by the market builders, not by the model |
| `eu_market_blocks.csv` | member state → CAPRI's EU trade block (EU_WEST, EU_EAST) |
| `model_parameters.csv` | every constant of the economics and accounts (value, unit, kind, source; `capri_mod/params.py`) |

Archived, not read by the model (`capri_data/archive/`): `dairy_processing_params.json`, `gascoeff_params.json`,
earlier base areas and trade flows.

---

## Code glossary

Model activity codes (`capri_mod/data/definitions.py`):

| Code | Meaning | Code | Meaning |
|---|---|---|---|
| `SWHE` | soft wheat | `OLIV` | olives for oil (market product: olive oil) |
| `DWHE` | durum wheat | `TABO` | table olives |
| `RYEM` | rye and meslin | `TOBA` | tobacco |
| `BARL` | barley | `TEXT` | textile crops (cotton in EL, ES, BG; flax and hemp elsewhere) |
| `OATS` | oats | `GRAS` | grass (permanent grassland) |
| `CORN` | grain maize | `MAIF` | maize for forage / silage |
| `OCER` | other cereals | `OFOD` | other fodder crops |
| `PARI` | paddy rice (market product: milled rice) | `SETA` | set-aside |
| `OCRO` | other marketable crops | `DCOW` | dairy cows |
| `OIND` | other industrial crops | `BCOW` | suckler cows |
| `NURS` | nursery plants | `BULL` | bulls / fattening cattle |
| `FLOW` | flowers | `HFRS` | heifers |
| `POTA` | potatoes | `CALV` | calves |
| `SUGB` | sugar beet | `SHGM` | sheep and goats for milk |
| `SUNF` | sunflower seed | `SHGF` | sheep and goats for fattening |
| `RAPE` | rape and turnip rape | `PIGS` | breeding sows |
| `SOYA` | soya beans | `PIGF` | fattening pigs |
| `OOIL` | other oilseeds | `LAYS` | laying hens |
| `PULS` | pulses | `BROI` | broilers |
| `TOMA` | tomatoes | `OANI` | other animals |
| `OVEG` | other vegetables | | |
| `APPL` | apples and pears | | |
| `OFRU` | other fruit | | |
| `CITR` | citrus | | |
| `TAGR` | table grapes | | |
| `WINE` | wine | | |

Market-only codes: `SUGR` white sugar; `MILK` raw milk; `BUTR` butter; `SKIM` skimmed milk powder; `CHES` cheese;
`WHEY` whey powder; `FRMI` fresh milk products; `CREM` cream; `COCM` concentrated milk; `WMIO` whole milk powder;
`CASE` casein; `BEEF`, `PORK`, `POUL`, `SGMT` (sheep and goat meat), `EGGS`; `RAPO`, `SUNO`, `SOYO` (oils), `RAPC`,
`SUNC`, `SOYC` (cakes); `PLMO` palm oil; `OTHO` other vegetable oils; `FFIS` freshwater fish; `SFIS` saltwater fish;
`OAQU` other aquatic products; `COFF` coffee; `TEAS` tea; `COCO` cocoa; `BIOE` bio-ethanol; `BIOD` bio-diesel; `DDGS`
distillers' dried grains; `FENI`, `FPRI` CAPRI's residual feeds. Feed items in `feed_requirements.csv`: `RAPC`,
`SOYC`, `SUNC` (rapeseed, soya, sunflower cake: CAPRI's codes, as the market's; `RAPM`, `SOYM`, `SUFM` before 23 October 2026).

## Further files (added in October 2026)

| File | Content | Source / builder |
|---|---|---|
| `2017/feed/fodder_balance_2017.json` | Regional fodder balances: usable fodder per ha, base fodder value, fodder per head | `tools/build/build_fodder_balance.py` (CAPRI rations, UVAG) |
| `2017/supply/land_market_2017.csv` (and `_2030`; `_regions.csv` per-region source) | Land-type base areas (6 types) and CAPRI land-market matrices, long format region,row,col,value (row `base_kha` = levels); 221 regions. JSON until 23 October 2026 | `tools/build/build_land_market.py` (pmppar `p_pmpQuadLandTypes`) |
| `2017/environment/nh3_factors_capri.json` | Ammonia shares of excreted N per animal and of mineral N (221 regions) | `tools/build/build_nh3_factors.py` (CAPRI 2030 reference) |
| `2017/supply/young_animals_2017.json` | CAPRI's young-animal flows per model head (calves, young cattle, replacement cows, piglets, lambs: produced and used per head, base net, base value) | `tools/build/build_young_animals.py` (res_17); CAPRI's young-animal markets (`CAPRIModel._update_young_animal_prices`) |
| `2017/supply/livestock_product_value_coef.csv`, `livestock_product_value_by_market_coef.csv` | Value of an animal's final products (no young animals) per model head, total and by market (`ACT.MARKET`, e.g. `DCOW.MILK`, `DCOW.BEEF`): CAPRI quantity x national UVAG x LEVL / model heads. What a meat, milk or egg price change moves (quantity x price change) and the product share in livestock supply elasticities | `tools/build/build_shg_split.py` (`coefficient_tables`, through `build_livestock_output_coef.build_product_values_by_market`); the by-market file also by `tools/build/build_livestock_products.py` (res_17) |
| `2017/supply/mineral_n_price.csv` | Mineral fertiliser N unit value per country; not used by the default model | CAPRI 2017 national UVAG NITF |
| `2017/environment/manure_pool_costs.json` | CAPRI's 34 manure pools and 930 trade-cost links | `tools/build/build_manure_pool_costs.py` (CAPRI distance matrix) |
| `2017/abatement/ammonia/*.csv` | CAPRI's ammonia-technology inputs: control strategies, reduction factors, relative emissions, grazing fractions, Nitrates-Directive shares, peat shares, holdings by size class | `tools/build/build_ammonia_tech_inputs.py` (CAPRI `dat\miterra`, `dat\scen\ghgtech`, `dat\envind` exports); inputs of the builders below, not read by the model, except `RCEmissions.csv` (read by `capri_mod/feed/ration.py`) |
| `2017/abatement/ammonia/costs/*.csv` | Cost tables of CAPRI's ammonia technologies (investment, storage time, input demands and prices, application costs, grassland shares, N per m3, Nitrates-Directive storage) | `tools/build/build_ammonia_cost_tables.py` (tables A1-A10 in CAPRI `envind/ammo_tech.gms`) |
| `2017/abatement/ammonia/p_Heads.csv`, `capri_mann_days_2030.csv` | Heads by farm-size class; manure N and days per cycle per CAPRI region and animal activity (2030 reference) | `tools/build/build_ammonia_herd_inputs.py` |
| `2017/abatement/ammonia/ammonia_cost_curves.parquet` | CAPRI's ammonia-technology cost curves (alpha, beta, lower bound) per region, activity, manure system and technology | `tools/build/build_ammonia_cost_curves.py` (reproduces `ammo_tech.gms` m_CostAmm); an intermediate read by `tools/build/build_ammonia_tech_model.py`, not by the model |
| `2017/abatement/ammonia/ammonia_technologies.csv`, `ammonia_technology_effects.parquet` | CAPRI's ammonia-option entries of the technology table (costs, initial and maximum shares, applicability, remaining NH3) and their side effects on other gases, per region and animal activity; shares match CAPRI's endotech runs | `tools/build/build_ammonia_technologies.py`; an intermediate read by `tools/build/build_ammonia_tech_model.py`, not by the model |
| `2017/abatement/ammonia/ammonia_tech_model.csv` | CAPRI's ammonia options per model region, animal and CAPRI sub-activity: weight, stock factor, manure-N weight, group (NH3MAN/NH3APP), cost, CAPRI-calibrated slope and early-adopter threshold, initial and maximum shares, NH3 cuts at housing/storage/application, grazing share and MITERRA loss fractions | `tools/build/build_ammonia_tech_model.py`; `capri_mod/supply/ammonia_techs.py` |
| `sources/arm/capri_supply_elas_young_1720.csv` | CAPRI's calibrated supply elasticities of young animals per member state (YCAM, YCAF, YBUL, YHEI, YCOW; 2020 calibration) | `tools/build/build_young_animal_elasticities.py`; weights cattle elasticities in `capri_pmp.build_elasticity_table` |
| `2017/abatement/fert_options_jul15.csv` | CAPRI's fertiliser-efficiency options from miti_data_jul15 (national; regional VRT_SRUC): costs, PMP terms, relative subsidies, shares, QEmitt and no-control QEmitt | `tools/build/build_fert_options_jul15.py` from `sources/ghgtech/miti_data_jul15_p_ghgMiti.txt`; `RegionalSupplyModel._fert_techs` |
| `2017/environment/capri_crop_n_coefs_2030.csv` | CAPRI 2030 reference per region and crop: level, yield, NITF export coefficient, NCRD (residues + deposition, kg/ha), biological fixation (1000 t) | `tools/build/build_capri_crop_n_coefs.py`; `EnvironmentalModule._capri_crop_n` (gross N balance) |
| `2017/environment/capri_gnb_components_2030.csv` | CAPRI 2030 gross N balance items per region (kg N/ha): EXPPRD, CRESID, ATMOSD, BIOFIX, MINFER, EXCRET, MTRADE, SURTOT, residue unavailability and losses | `tools/build/build_capri_gnb_components.py`; scaling of per-crop coefficients, residue availability |
| `sources/eurostat/aei_pr_gnb_nitrogen.csv` | Eurostat gross nutrient balance, nitrogen, member states 1985–2023 (inputs, outputs, balance; tonnes and kg/ha) | validation only: `tools/check/validate_gnb_eurostat.py` |
| `2017/abatement/active_technologies.csv` | CAPRI's active mitigation options in its Green Deal reference (activeTech: ammonia, fertiliser, feed, carbon, other) | `tools/build/build_active_technologies.py` from `pol_input/greendeal/refpol_endotech_all_sup.gms`; filters the fertiliser options |
| `2017/abatement/mitigation/*.csv` | Inputs of CAPRI's feed-additive, genetics and soil options: dairy milk yields from CAPRI's 2030 baseline trends, tillage and cover-crop shares, ecological-focus-area cover crops, initial winter-cover shares, nutrient contents of feedstuffs | `tools/build/build_mitigation_inputs.py` (CAPRI `results\baseline\trends_1730`, `dat\envind`, `dat\policy`, `dat\feed`); inputs of the builders (`build_cover_crops.py`, `build_genetics_*.py`, `build_supplement_effects.py`); the model reads the built files (rows below), not these |
| `2017/supply/livestock_cost_coef.csv`, `livestock_output_value_coef.csv` | Livestock total inputs (TOIN) and total output (TOOU) per model head: CAPRI's regional totals / the model's head counts, the same basis as livestock revenue and output | `tools/build/build_livestock_output_coef.py` (capreg dumps) |
| `2017/environment/enteric_feed_factors.csv` | Gross energy (Mcal/kg DM) per country, cattle type and feed group, and Ym, for CAPRI's feed-based cattle enteric methane | `tools/build/build_enteric_feed_factors.py` (CAPRI `envind/def_digestibility.gms` NRC table, `create_rawdat_gascoeff_gdx.gms` IPCC table, `sets.gms` FEED_TO_O, capreg feed use) |
| `2017/environment/crop_nut_need_mult_fact_2030.csv` | CAPRI's over-fertilisation factor x (p_CropNutNeedMultFact, NITF, 2030) per region, limiting the fertiliser-efficiency technologies (Tot_MitFert_, regional maximum shares) | `tools/build/build_overfert_factors.py` (gdxdump of CAPRI `results\fert\priFertDist_<MS>1730defaulta.gdx`) |



### CAPRI 2030 prices (`trajectories/`)

| File | Content | Built by |
|---|---|---|
| `trajectories/capri_price_ratios_2030.csv` | member state, CAPRI product: UVAG 2017 and 2030, input deflator, real ratio (2030 price in 2017 money / 2017 price) | `tools/build/build_price_trajectory_2030.py` |
| `trajectories/capri_cap_premium_2030.csv` | model region × CAPRI activity: CAPRI's 2030 premium per unit in 2017 money | same |
| `trajectories/capri_livestock_premium_ratio_2030.csv` | model region × model animal: 2030/2017 premium ratio (real, 2017 activity-level weights) | same |
| `validation/greendeal_2030/capri_marginal_terms_{ini,max}_2030.csv.xz` (xz-compressed), `capri_unit_values_{ini,max}_2030.csv` | CAPRI's Farm-to-Fork reference: per-activity marginal terms (D_*), LEVL, MREV, TOOU, TOIN, MANN, PRME; national unit values | `tools/build/extract_capri_marginal_terms.py` |
| `sources/capri_baseline/capri_uvag_store_1730.csv` | CAPRI's calibrated 2030 unit values (p_uvagStore), member state × product | gdxdump of `data_uvag1730defaulta` |
| `sources/capri_baseline/capri_market_prices_1730.csv` | CAPRI market baseline prices (PPRI, CPRI) at the 2017 (BAS) and 2030 (CAL) points, member state × product | gdxdump of `data_market_1730defaulta` |
| `2017/supply/grass_intensity.csv` | CAPRI's two grassland activities per model region: extensive share of GRAS (share_ext), yields relative to the GRAS mean (yield_ext_rel, yield_int_rel), areas, CAPRI's PMP diagonal terms (q_ext, q_int, EUR/ha per 1000 ha) and their source | `tools/build/build_grass_intensity.py` (res_17, p_pmpQuadTechn) |
| `2017/supply/dairy_intensity.csv` | CAPRI's two dairy-cow activities per model region: low-yield share of DCOW, per-head changes from DCOH to DCOL relative to the average cow (milk, manure N, energy, protein, dry-matter limits), CAPRI's PMP diagonal terms (q_low, q_high) and their source | `tools/build/build_dairy_intensity.py` (res_17, p_pmpQuadTechn) |
| `2017/supply/cattle_intensity.csv` | CAPRI's low/high-intensity fattening bulls (BULL/BULH) and heifers (HEIL/HEIH) per model region and animal: stall shares, fattening days, per-stall changes from high to low relative to the animal's average (manure N, beef, young animals, energy, protein, dry-matter limits), PMP curvature of the stall shift (q_z) and its source | `tools/build/build_cattle_intensity.py` (res_17, p_pmpQuadTechn) |
| `2017/supply/livestock_output_by_product_coef.csv` | Each animal's output by CAPRI final product, columns `ACT.PRODUCT` (kt per 1000 head; sums to livestock_output_coef): the market bridge sends cull-cow beef to beef, sheep and goat milk to raw milk, hen meat to poultry | `tools/build/build_livestock_products.py` (res_17) |
| `2017/market/biofuel_feedstock.csv` | First-generation biofuel feedstocks per CAPRI market region (`ms`; `region` = model trade region) and biofuel: 2030-reference quantity (kt), biofuel yield PRCB, by-product yield PRCBY, feedstock and by-product prices, numeraire, CES elasticity | `tools/build/build_biofuel_market.py` (CAPRI 2030 market results) |
| `2017/market/biofuel_market.csv` | CAPRI's biofuel supply (SupplyBiof_), demand (biofDemShare_, biofDem_) and non-fuel processing (ProcNQ_: proc_kt, proc_hess, inpe) functions per CAPRI market region and biofuel, calibrated as `biofuel/def_biofuel_params.gms`: output and first-generation output (kt), fixed NAGR+SECG+EXOG output, producer price, feedstock cost per t biofuel, processing margin PR0, supply scale/alfa/beta/slope/turn; biofuel use (kt), consumer and Arm1 prices, fossil fuel price, total fuel use (kt, fossil + biofuel in fossil equivalents), oil equivalents, mandate share QUTS, observed share, demand MAX/Slope/Turn | `tools/build/build_biofuel_market.py` |
| `2017/market/biofuel_use_share.csv` | Biofuel share of EU use per market commodity (CAPRI 2030 reference) | `tools/build/build_biofuel_market.py` |
| `2017/abatement/mitigation/lownfeed_effects.csv` | CAPRI's low-nitrogen feeding per region and animal: protein requirement and manure N change, eligible share, cost, dsav (CAPRI's cost-saving drop between its ini and max calibration runs, EUR per model head) (envind/low_n_feed.gms) | `tools/build/build_lownfeed_effects.py` |
| `2017/abatement/mitigation/supplement_effects.csv` | CAPRI's feed supplements linseed and nitrate per region and cattle animal: requirement changes, eligible share, cost, CH4ENT change, dsav (as lownfeed_effects.csv) (envind/line_nitr.gms) | `tools/build/build_supplement_effects.py` |
| `2017/environment/fert_dist_priors_2030.csv` | Priors of CAPRI's inner fertiliser distribution model per CAPRI region (and country fallback, `level` nuts0) and crop group: area (1000 ha), mineral/manure/residue N per ha (kg), accuracy, mineral efficiency, manure availability | `tools/build/build_fert_dist_priors.py` |
| `2017/environment/fert_dist_crop_groups_2030.csv` | Model crop -> CAPRI crop group (NGRP) area shares per CAPRI region | `tools/build/build_fert_dist_priors.py` |
| `2017/policy/mineral_redu_exemptions.csv` | CAPRI's listed exemptions from the crop-specific mineral fertiliser reduction (factor x baseline, from year, othPol high) | `tools/build/build_mineral_redu_rules.py` |
| `2017/policy/mineral_redu_limcres.csv` | CAPRI's relaxations of the limCres regulation by year | `tools/build/build_mineral_redu_rules.py` |
| `2017/market/feed_bulks_eu.csv` | CAPRI's feed bulks per member state (FCER cereals, FPRO protein-rich feed incl. DDGS and FPRI, FENE energy-rich, FOTH other, FMIL milk products): products, model commodity, 2030 feed use (kt), EU Arm1 price (EUR/t), CES elasticity p_rhoFeed (feedBlkPrice_, feedShareEqu_) | `tools/build/build_feed_bulks.py` |
| `2017/market/feed_byproducts.csv` | CAPRI's residual feeds FENI, FPRI (MaprFeed_): EU 2030 output (kt) and parent commodities' weights (food/processing or biofuel use) | `tools/build/build_feed_byproducts.py` |
| `2017/market/feed_bulks_eu_share.csv` | Feed share of EU use per model commodity in the bulks (CAPRI 2030 reference) | `tools/build/build_feed_bulks.py` |
| `2017/market/dairy_processing.csv` | CAPRI's dairy block per member state: product and raw milk quantities, processing, fat and protein contents (%), prices, CSEI, INPE, fat and protein prices | `tools/build/build_dairy_processing.py` |
| `2017/market/dairy_hessian.csv` | Hessian of CAPRI's dairy NQ function per member state (symmetric, MILK row reversed) | `tools/build/build_dairy_processing.py` (elas_2_1730 p_hessNQDairy) |
| `2017/market/dairy_eu_balance.csv` | EU27 balance of nine dairy products and HCOM-weighted own-price demand elasticity | `tools/build/build_dairy_processing.py` |
| `2017/market/bilateral_flows_<year>.csv` | CAPRI's bilateral flows per (importer, exporter) and commodity, 2017 base market and 2030 reference: quantity (kt), import price split into exporter-price part a and fixed part b (EUR/t), a0, ad valorem tariff | `tools/build/build_bilateral_market.py` |
| `2017/market/bilateral_regions_<year>.csv` | CAPRI market price (PMRK) and production per model trade region | `tools/build/build_bilateral_market.py` |
| `2017/market/bilateral_trq_<year>.csv` | EU tariff-rate quotas per model exporter: quota (kt), out- minus in-quota price gap (EUR/t), imports under the quota regime | `tools/build/build_bilateral_market.py` (build_trq) |
| `2017/market/armington_rho.csv` | Armington substitution elasticities rho1, rho2 per market commodity | `tools/build/build_bilateral_market.py` (market1.gms, market1_ch.gms) |
| `2017/market/processing_yields.csv` | Olive oil per tonne of olives (member state), milled rice per tonne of paddy (EU) | `tools/build/build_processing_yields.py` |
| `2017/market/world_market_baseline.json` | Base balances (production, domestic use, imports, exports) of 32 market commodities per model trade region (kt); the EU's base self-sufficiency | `tools/build/build_world_market_baseline.py` (FAO_agg BAS) |
| `2017/market/sugar_processing.csv` | CAPRI's sugar processing per member state: beet harvested and processed, white sugar, PRCY, sugar per beet | `tools/build/build_sugar_processing.py` (2030 reference) |
| `2017/market/dairy_world_baseline.json` | World base balances of butter, SMP, cheese, whey per model trade region (kt) | `tools/build/build_dairy_world_markets.py` (FAO_agg BAS) |
| `2017/market/dairy_eu_demand_elas.csv` | EU food demand elasticities among the nine dairy products, own and cross (CAPRI p_ElasDem, HCOM-weighted) | `tools/build/build_dairy_processing.py` |
| `2017/market/dairy_world_processing.csv` | CAPRI's dairy block for the non-EU market regions: products, raw milk, contents, prices, food and feed use, extra-regional trade; MILKSUP = raw milk supply slope | `tools/build/build_dairy_world_blocks.py` |
| `2017/market/dairy_world_hessian.csv` | Dairy NQ Hessians of the non-EU market regions | `tools/build/build_dairy_world_blocks.py` |
| `2017/market/dairy_world_demand_elas.csv` | Food demand elasticities among the nine dairy products, non-EU regions | `tools/build/build_dairy_world_blocks.py` |
| `2017/supply/livestock_units.csv` | CAPRI's livestock units per model head (LEVW / LEVL over the animal's CAPRI members, 2017, / capri_level_ratio), region x animal; weights of the reported adoption shares | `tools/build/build_livestock_units.py` |
| `2017/abatement/mitigation/genetics_effects.csv` | CAPRI's cattle genomics per region and animal (genet_yld, genet_eff): eligible share, relative changes of milk, energy, protein, dry matter and manure N per adopting head PER UNIT of the technology parameter (tech_param), cost floor (CAPRI's per-place floor per model head) and per-unit cost, relSubs0/1, max_share (CAPRI's MaxShare with fixGenet_eff_to_iniValues on), dsav (CAPRI's cost-saving drop between its calibration runs, per unit of the parameter); scaled at run time by the scenario's settings | `tools/build/build_genetics_effects.py` (breeding.gms) |
| `shared/capri_member_state_codes.csv` | NUTS country prefix -> CAPRI member state (BE, LU -> BL000000; IE -> IR000000; GR -> EL000000; GB -> UK000000; others the same code); `capri_mod.data.definitions.MS_CODE` and `capri_ms()`, `tools/lib/_model_regions.CTRY` | CAPRI `sets.gms` NUTS0 |
| `2017/environment/livestock_n_export_coef.csv` | CAPRI's N exported in animal products per model head (CRPR_EXPT x LEVL over the animal's CAPRI members / model herd, per region group), kg N; the report item n_animal_products | `tools/build/build_livestock_n_export_coef.py` (res_17; fert/calc_nexport.gms) |
| `2017/supply/land_rents_2017.csv` | CAPRI's land rents at 2017 (D_AREA of ARAC, FRUN, GRAS; CAPRI's rule of cal_land_nests.gms l. 204-226 where D_AREA is not positive), EUR/ha; the land market at the 2017 market year | `tools/build/build_land_rents.py --year 2017` |
| `2017/environment/histosol.csv` | CAPRI's histosols per model region: organic-soil share of cropland and grassland, climate-weighted IPCC 2013 N2O factor, N2O/CO2/CH4 per ha of the class, and the fallowing option's calibration (costsaving0/1, MaxShare, PMP terms) | `tools/build/build_histosol.py` |
| `2017/environment/manure_n2o_factors.csv` | CAPRI's manure N2O by stage per region and animal: t N2O-N per t manure N for housing/storage (f_man), application (f_app), grazing (f_gra), leaching (f_lea) | `tools/build/build_manure_n2o.py` (res_17) |
| `2017/environment/manure_n2o_tech.csv` | CAPRI's ammonia technologies' relative effects on housing/storage (r_hou) and application (r_app) N2O, per region, animal and option | `tools/build/build_manure_n2o.py` |
| `2017/supply/plant_protection_cost.csv` | CAPRI's plant protection (PLAP x UVAG), other inputs (INPO) and fertiliser (FERT) costs per ha, per model region and crop; the pesticide and organic instruments use them | `tools/build/build_plant_protection_cost.py` (res_17) |
| `2017/supply/cover_crops.csv` | CAPRI's catch crops per model region: 2030 area as a share of UAAR, cost per ha (TOIN), N from fixation and residues per ha (BioFix from p_cInput) | `tools/build/build_cover_crops.py` |
| `2017/supply/winter_cover_share.csv` | Share of each crop's area under winter cover: as given in CAPRI (share0) and filled NUTS2 <- member state <- EU (share) | `tools/build/build_cover_crops.py` (wintercovershare.gms) |
| `2017/abatement/fert_side_effects.csv` | CAPRI's literature-review side effects of nitrification inhibitors: mineral N (N2OSYN, NH3SYN) and applied manure (NITR_INH_MAN: NH3APP, N2OAPP), relative change of emissions | `tools/build/build_fert_side_effects.py` (p_litRevFertTechs) |
| `validation/coupled_support_2030/capri_vcs_effect.csv.xz` | CAPRI 2030: reference vs no voluntary coupled support (levels, premiums, prices) | `tools/build/extract_capri_vcs_pair.py` |
| `sources/ghgtech/capri_costsavings_2030.csv` | CAPRI's mitigation calibration runs (ini, max): v_Miti levels and marginals | `tools/build/extract_capri_costsavings.py` |

### Files added after the tables above (not described in detail here)

| File | Builder |
|---|---|
| `2017/abatement/ammonia/n_cascade_factors.csv`, `n_cascade_region.csv`, `n_cascade_effects.csv` (CAPRI's N loss cascade, docs/N_CASCADE_SPEC.md) | `tools/build/build_n_cascade.py` |
| `2017/abatement/ammonia/n_leaching_region.csv` (leaching share, LEACHN_) | `tools/build/build_n_leaching.py` |
| `2017/abatement/ammonia/ad_option.csv` (anaerobic digestion, docs/AD_SPEC.md) | `tools/build/build_ad_option.py` |
| `2017/abatement/ammonia/nitrates_directive_min_shares.csv`, `nitrates_directive_obligations.csv`, `nvz_*.csv` (built, not applied) | `tools/build/build_nitrates_directive.py` |
| `2017/market/gl_demand_b.csv`, `gl_demand_goods.csv`, `gl_demand_regions.csv` (Generalised Leontief food demand) | `tools/build/build_gl_demand.py` |
| `2017/market/processing_nq_base.csv`, `processing_nq_hessian.csv` (ProcNQ_) | `tools/build/build_processing_nq.py` |
| `2017/market/welfare_base_2030.csv` (CAPRI's welfare base values, reports/welfare.gms) | `tools/build/build_welfare_base.py` |
| `2017/market/eu_ms_balance_2030.csv`, `shared/eu_market_blocks.csv` (EU trade blocks) | `tools/build/build_eu_ms_balance.py` |
| `2017/environment/luc_2030.csv` (land-use change model) | `tools/build/build_luc_2030.py` |
| `2017/environment/npk_crop_coefs_2030.csv`, `npk_region_2030.csv`, `fert_dist_priors_npk_2030.csv`, `livestock_manure_p_coef.csv`, `livestock_manure_k_coef.csv` (P and K) | `tools/build/build_npk_balance_2030.py` |

## Extracted, not used yet

*Removed 27 October 2026 (the project lead's decision, no builder and no reader): `2017/supply/input_requirements.csv`,
`pmp_diagonal_terms.csv`, `pmp_crossgroup_terms.csv` (CAPRI's estnlp VA/VD extracts of unrecorded origin; CAPRI's PMP
terms are read from `sources/capreg/pmp_quad_techn.csv`, `pmp_quad_pact.csv` and the 2030 exports) and
`2017/environment/manure_ch4_ef_regional.csv` (the accounts use `livestock_ch4man_coef.csv`).*

CAPRI data that the extractors write and no model code, builder or test reads at present (inventory of 27 October 2026).
Kept as the repository's copy of CAPRI's data, for the work that will need them; each is rewritten when its extractor
runs.

| File | Content | Written by |
|---|---|---|
| `2017/abatement/ammonia/ControlStrat_TS.csv`, `CorrND.csv`, `FracNVZNuts2.csv`, `FracNVZNuts2_full.csv`, `FracToepHouse.csv`, `FracToepStorage.csv`, `FracUseFert.csv`, `PercPeat.csv`, `ScalarArray.csv`, `rCorrND.csv`, `rLFManureBasis.csv`, `rLFManureND.csv`, `reducBio.csv` | MITERRA symbols of CAPRI's ammonia module not used by the model's ammonia options | `tools/build/build_ammonia_tech_inputs.py` (one file per GDX symbol) |
| `2017/abatement/ammonia/nitrates_directive_min_shares.csv` | Nitrates Directive minimum option shares by region | `tools/build/build_nitrates_directive.py` |
| `2017/abatement/ammonia/costs/scalars.csv` | scalar cost parameters of the ammonia options | `tools/build/build_ammonia_cost_tables.py` |
| `2017/abatement/mitigation/p_ccEfa.csv`, `p_tillageCover.csv`, `p_winterCoverShare0.csv` | catch crops as ecological focus area, tillage cover, initial winter-cover shares | `tools/build/build_mitigation_inputs.py` |
| `pipeline/captrd/sets/fixyield.csv`, `mrkbale.csv`, `reqst.csv` | empty CAPTRD sets, part of the complete set extraction | `tools/build/build_captrd_sets.py` |
| `sources/capreg/capreg_feed_use.csv`, `capreg_herds.csv`, `capreg_land.csv` | CAPREG DATA2 feed use, herds, land | `tools/build/extract_remaining_nine.py` |
| `sources/capreg/capreg_cost_components.csv.xz` | CAPREG DATA2 input cost components | `tools/build/extract_all_from_data2.py` |
| `sources/capmod/capmod_trade_flows_2017.csv.xz`, `capmod_world_prices_2017.csv` | CAPRI's 2017 bilateral trade flows and world prices (capmod res_0_1717) | `tools/build/ingest_capmod_market.py` |
| `sources/estnlp/gtap_armington.csv` | GTAP Armington elasticities mapped to the model's commodities | `tools/build/ingest_pela_gtap.py` |
| `validation/greendeal_2030/capri_marginal_terms_max_2030.csv.xz`, `capri_unit_values_max_2030.csv` | CAPRI's maximum-mitigation Green Deal run: marginal terms and unit values | `tools/build/extract_capri_marginal_terms.py` |

