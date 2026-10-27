# Rebuilding the data on CAPRI's regional units: log (27 October 2026)

The model's regions are now CAPRI's 221 regional units of the EU27 and Norway under CAPRI's 8-character codes
(`capri_data/shared/regional_units.csv`, `tools/build/build_regional_units.py`; inventory: `REGIONAL_UNITS_INVENTORY.md`;
builders and their order: `REGIONAL_UNITS_BUILDERS.md`). Every region-keyed file was rebuilt by its builder on the units
and compared with the file on the old NUTS-2016 regions (`tools/check/compare_rekeyed.py`,
`tools/check/compare_rekeyed_json.py`, against branch `next`): for the 196 regions whose CAPRI unit was theirs alone
(one-to-one in the old `shared/region_capri_map.csv`), the rebuilt row must equal the old row, since both read the same
CAPRI row. Every difference found is listed below with its cause. The other 25 units replace 52 old regions (splits,
merges, national copies, the 13 empty rows); their values are now CAPRI's own and have no old counterpart to compare.

## Code

- `capri_mod/data/definitions.py`: `NUTS2_REGIONS`, `ALL_REGIONS`, `REGION_TO_COUNTRY` read from `regional_units.csv`
  (the hard-coded list of 248 NUTS-2016 codes is gone); `country_of(region)` gives the NUTS-0 country (BE, LU, IE ...)
  by which the per-country tables are keyed (organic and landscape targets, mineral fertiliser prices, PESETA regions):
  a unit's first two characters are CAPRI's member state (BL, IR), not the country, and BL400000 is Luxembourg.
  CAPRI's prefixes are not used as country keys because IR (Ireland) is Iran among the market's ISO codes.
  `IdentityMap`: region -> CAPRI region is the identity.
- Model code reads no region map any more: `capri_pmp.py` (elasticity table), `fert/npk.py`, `fert/inner_fert_dist.py`,
  `supply/n_leaching.py`, the environmental module's crop N terms and the supply module's fertiliser options took the
  CAPRI region from `shared/region_capri_map.csv`, the NUTS crosswalk or the NUTS correspondence; each region is now its
  own CAPRI region, the member state's row the fallback where CAPRI's table has no row for it.
- Builders (`tools/lib/_model_regions.py`): `capri_groups` and `region_to_capri` are the identity on the units;
  `is_unit`, `regional_row` replace the test "code does not end in 000000", which dropped the units of the member states
  without regional detail (DK000000 ...). `build_capri_base.py`: each unit reads its own CAPRI row; removed the renames,
  the merge, the splits by Eurostat cattle numbers, the national copies, Ireland's 2016 shares, Norway's pooling, the
  Saxony and Croatia crop re-splits from p_REGIO, the `ZERO` list. The DATA2, PMP-term and PELA ingests
  (`extract_all_from_data2.py`, `extract_remaining_nine.py`, `ingest_pmp_terms.py`, `ingest_pela_gtap.py`,
  `build_intensity_q_2030.py`) take CAPRI's codes as they are, without the crosswalk (which left 21 regions unmatched).
  `build_land_market.py`: the split, orphan, Norway and Ireland handling and the one-off `--repair-splits` removed. The
  crop and animal PMP builders: Norway's pooling removed. `build_livestock_output_coef.py`, `build_feed_ration.py`: the
  BL -> (BE, LU), IR -> IE prefix tables removed (the units carry CAPRI's prefixes).
- Builders written for files that had none: `build_n_deposition_substitution.py` (n_deposition_regional.csv,
  fertiliser_substitution_2030.csv, from capri_gnb_components_2030.csv), `build_livestock_intensity_bounds.py`
  (res_17 DCOL/DCOH YILD), `ingest_pela_gtap.py` now also writes `pela_cross_by_region.json`.
- Builders write full precision where they still rounded (ammonia technology model, manure losses and trade, baseline
  surplus, GHG coefficients, sheep-goat per-head tables, ration and price trajectories, EU producer prices): the
  exact-I/O decision of 27 October.
- Removed: `shared/nuts_crosswalk.json` and `tools/build/build_nuts_crosswalk.py`, `shared/region_capri_map.csv` and
  `tools/build/build_region_map.py`, `shared/capri_regio_concordance.json` (read by nothing),
  `tools/build/build_norway_pigs.py`, `build_ssb_pigs.py` and `sources/ssb/` (Norway's 2016 regions), the sources of
  the removed splits (`sources/capreg/p_REGIO.csv.gz`, `sources/eurostat/ef_lsk_bovine_nuts2.csv`,
  `tgs00045_bovines_nuts2.csv`), and three orphans: `2017/supply/land_rent_regional.csv` (loaded, never read; with
  `sources/eurostat/apri_lrnt.csv`), `2017/environment/capri_regional_n_balance_2030.csv` (listed by the loader, read by
  nothing), the OTHER_AG column of land_availability.csv (no builder; read only by the HNV indicator's land total).
  Kept: `shared/nuts_version_correspondence.json` (CAPRI codes -> NUTS codes, for reporting on current NUTS, task 237).

## Files: what differs on the one-to-one units, and why

Equal to the last digit (or to the old file's rounding) on the 196 one-to-one units: base_areas (one cell, below),
nutrients_regional, capreg_cap_premium, capreg_nutrient_coefs, pmp_quad_pact, pmp_quad_techn, pela_own_price,
pela_cross_by_region.json, supply_elasticities_regional, premium_scheme_shares_2030, capri_baseline_surplus_2030,
cover_crops, winter_cover_share, winter_cover_option, fert_side_effects, land_market_2017/2030 (+ _regions),
land_rents_2017/2030, manure_housing_losses_2030, manure_trade_2030, nh3_factors_capri.json,
crop_nut_need_mult_fact_2030, plant_protection_cost, ammonia_tech_model, manure_n2o_factors, manure_n2o_tech,
pmp_capri_2030, intensity_q_capri2030, capri_ref_2030.json, captrd_2030.json, young_animals_2017.json,
young_animals_by_sex_2017.json, feed_ration_2017.json, fodder_balance_2017.json, capri_ref_ration_2030,
capri_ref_fodder_2030, capri_price_ratios_2030, capri_cap_premium_2030, capri_livestock_premium_ratio_2030,
dairy_intensity, livestock coefficient tables (output, revenue, cost, output value, product value, by product, by
market, manure N, P, K, N export, CH4, premium), livestock_feed_coef, livestock_units, histosol, lownfeed_effects,
supplement_effects, genetics_effects, crop_co2_coef, livestock_intensity_bounds, market producer prices (crops).

Differences, each explained:

| file, column | old | new | cause |
|---|---|---|---|
| base_areas PARI, ES230000 | 0 | 0.081 kha | CAPRI's LEVL (the old 0 came from an earlier writer); the EU paddy rice price moves 226.13 -> 226.18 EUR/t |
| animal_numbers PIGS, PIGF | census PIGS - SOWS, by the removed one-off tools/build_pig_split.py | the same rule, now in build_capri_base | the rule had no builder |
| animal_numbers PIGF, DEA20000, DEB10000, FI200000 | 0 | CAPRI's PIGF HERD (20.8, 32.2, 0.28 thousand) | CAPRI has fattening pigs there but no census total or sows; the old split set both to 0. Now CAPRI's PIGF herd, as Norway's regions had. Follows into the PIGF level ratio, yield, PMP term, labour, feed ration and livestock units of these three |
| animal_numbers SHGM, SHGF | census SHGT x CAPRI's HERD share (build_shg_split) | CAPRI's SHGM, SHGF HERD | up to 1e-6 relative (CAPRI's SHGT = SHGM + SHGF to 1e-11); follows into the sheep and goat per-head coefficients at the same order |
| land_availability OTHER_AG | values of unknown origin (6.25, 2.97619 ...) | dropped | no builder; read only by the HNV indicator's land total |
| yields, variable_costs: crops CAPRI has nowhere in the member state (citrus, olives, table grapes in Germany; durum wheat in Poland; soya in the Netherlands ...; 12 columns, 513 cells) | values of the synthetic template removed in Sprint 9s (DE11 citrus 24.2 t/ha, 1,599 EUR/ha; wine 1,313 EUR/ha) | 0 | build_crop_economics_2017 left such cells as the file had them; now 0, as the file had for rice outside the rice countries |
| capreg_producer_prices TWIN, Spain, Greece, Hungary | 1361.6 everywhere | CAPRI's regional MPRI (403, 74, 336 ...) | a stale fill; now CAPRI's DATA2 value, equal to the model's WINE price column |
| capreg_producer_prices CITR, TAGR of regions without the crop | a price | empty | the loader falls back to the national, then the EU price |
| market producer_prices SHGM, SHGF | 770.27, 5108.85 | 803.72, 5103.85 EUR | herd-weighted EU means of CAPREG's regional prices, now over every unit (Denmark, Ireland, Poland's units ... had none) |
| grass_intensity q (13 units), cattle_intensity q (79 rows), set_aside_split w_vset_capri2030 (63 units) | the country's median (REGISTERED fallback) | CAPRI's own PMP terms | the crosswalk had left these regions without CAPRI's terms (e.g. Sicily's set-aside weight 0.49 -> CAPRI's 0.0015). Used by default (pmp_source capri2030) |
| n_deposition_regional (38 units) | Italy's national deposition 11.89 kg N/ha on every Italian region | CAPRI's regional ATMOSD (6.9 - 30.9) | the supplied file used the national row where its code lookup failed |
| fertiliser_substitution_2030 manure_availability, mineral_efficiency (52 units) | the EU median of CAPRI's regions | CAPRI's regional values (e.g. IT120000 availability 0.44 -> 0.85) | the same; the two unused columns (mineral_share_of_need, need_at_floor_share) not rebuilt |
| crop_premium, cap_payments BPS, rounding of other files | rounded (4 to 8 digits) | full precision | exact I/O |
| pmp_recipe_2017, pmp_recipe_2030 (+ animals), intensity_q_recipe2017/2030, set_aside_split w_vset and w_vset_recipe2030 | built from an older version of recipe_*_quad_techn.csv | built from the current one | the old files did not follow their inputs (recipe_2017_quad_techn.csv itself reproduces from its builder to 2e-9). Used only with pmp_source = recipe, except w_vset (base-year set-aside weight) |
| gtap_armington.csv | COTT, OFIB rows | TEXT row | the file predated the textile merge (read by no model code) |

## Open: orphans found, not removed (not part of the move; for decision)

`sources/residual_cost_calibration.json`, `sources/capreg/capreg_feed_availability_regional.csv` (read by nothing,
written by nothing), `sources/capreg/capreg_levels.csv`, `capreg_yields.csv`, `derived_elasticities_from_pmp.csv` and
their scripts `ingest_capreg_data2.py`, `derive_elasticities_from_pmp.py` (read only by each other),
`sources/ifs/Mapping_reg_IFSCAPRI_201020.csv`, `sources/capri_dat/policy/shannon_index_nuts2_ifmcap.csv` (read by
nothing). Several builders still load `nuts_version_correspondence.json` without using it.
