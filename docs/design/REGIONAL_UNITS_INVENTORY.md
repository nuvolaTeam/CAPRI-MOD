# Moving to CAPRI's regional units: inventory (27 October 2026)

Read-only survey before the change (task: CAPRI's own regional units for EU27 + Norway). Nothing has been changed yet.
Companion files: `REGIONAL_UNITS_INVENTORY_files.csv` (every region-keyed data file), `REGIONAL_UNITS_model_vs_capri.csv`
(each model region and its CAPRI unit today), `REGIONAL_UNITS_capri_ru.csv` (CAPRI's 221 units).

## 1. CAPRI's regional units

CAPRI solves one supply model per regional unit (RU). In a run, `RU(SRNUTS2) $ SUM(MAP_RR(MS, SRNUTS2), 1)`
(capmod/define_regional_sets.gms l. 230), SRNUTS2 being defined in sets.gms l. 7803 (the NUTS-2 codes of each
country, plus one unit for each country without regional detail: DK, EE, LT, LV, SI, CY, MT, HR). The regions without
agriculture (urbanNUTS: BL100000, DE300000, DE500000, DE600000, ES630000, ES640000, AT130000, UKI00000) carry UAA 0
(capreg/cons_levls.gms l. 1519-1520) and have no results.

The units of CAPRI's Green Deal 2030 run (sources/capri_res/gd2030_endotech_ini_nbalance.csv: 270 codes, of which 250
are SRNUTS2 units and 20 country totals): **221 for EU27 + Norway** (EU27 215, Norway 6), plus UK 11, Turkey 12 and
the Western Balkans 6. CAPRI's codes follow older NUTS vintages in places (e.g. France 22, Poland 16 units).

## 2. The model's regions today

248 rows keyed by NUTS-2016 codes; 235 with agriculture, 13 empty (DE30, DE50, DE60, AT13, BE10, ES63, ES64: CAPRI's
urban regions; PL31-34, HR05-06: emptied as duplicates by build_capri_base.py `ZERO`).

| country | model rows | with agriculture | CAPRI units | difference |
|---|---:|---:|---:|---:|
| DE | 38 | 35 | 33 | +2 |
| DK | 5 | 5 | 1 | +4 |
| HR | 4 | 2 | 1 | +1 |
| HU | 8 | 8 | 7 | +1 |
| IE (CAPRI IR) | 3 | 3 | 2 | +1 |
| IT | 21 | 21 | 20 | +1 |
| LT | 2 | 2 | 1 | +1 |
| NO | 7 | 7 | 6 | +1 |
| PL | 21 | 17 | 16 | +1 |
| SI | 2 | 2 | 1 | +1 |
| all others | as CAPRI | | | 0 |
| **total** | **248** | **235** | **221** | **+14** |

`shared/region_capri_map.csv` (the map most builders use): 196 one-to-one, 24 "split" (several model regions share one
CAPRI unit: DED2/DED4/DED5, ITH1/ITH2, PL multiple, FI1B/FI1C, AT12/AT13, IE04-06, HU11/HU12), 1 "merge" (FI1D =
FI13 + FI1A), 27 "none" (the 13 empty rows, Denmark's 5, Slovenia's 2, Lithuania's 2, HR03/HR04, Estonia, Latvia,
Cyprus, Malta and 4 Norwegian rows). 12 CAPRI units are mapped by no model region in that file (CY, DK, EE, HR, LT, LV,
MT, SI, FI1A, NO08, NO09, NO0A); those regions reach CAPRI data by other paths (nuts_crosswalk.json,
capri_regio_concordance.json, builder-specific code), which is part of what the move cleans up. Where one CAPRI unit
is spread over several model regions, the builders split it on proxies (cattle shares and the like).

## 3. Data files keyed by region

274 CSV files under capri_data carry region codes (archive and pipeline folders left out):
- **99 use the model's codes**; 79 of them are read by the model (supply 44, environment 16, abatement 6, policy 3,
  feed 1, trajectories 4, sources read directly 4, shared/region_capri_map.csv). Each needs rebuilding on CAPRI's units.
  A builder was found by file name for most; 12 were traced by hand: the land market's `_regions` files are written by
  build_land_market.py (capri_mod/data/land_market_io.py), the animal PMP files by build_animal_pmp_capri_2030.py
  (`--splits`, `--pmp recipe`). **Five have no builder in the repository** (made from files the project lead supplied):
  - 2017/environment/n_deposition_regional.csv (CAPRI res_2 dataOut perHa ATMOSD) and fertiliser_substitution_2030.csv
    (dataOut fertDist_, nutNed_): read by the environmental and supply modules; builders to be written from CAPRI's
    results on the new units;
  - 2017/supply/livestock_intensity_bounds.csv (CAPREG DATA2 DCOL/DCOH YILD): read by the supply module; builder to be
    written;
  - 2017/supply/land_rent_regional.csv (Eurostat apri_lrnt, national values where a region is not published): read by
    the supply module; on CAPRI's units CAPRI's own rents (land_rents_<year>.csv, build_land_rents.py) may replace it
    (to be checked);
  - 2017/environment/capri_regional_n_balance_2030.csv: listed by the loader, read by no code (an orphan: remove).
- **175 use CAPRI's 8-character codes** (mostly sources/ and the CAPRI exports under 2017/market and abatement): they
  stay; only the builders' mapping step changes.
- **JSON files with model codes** (11): 2017/environment/nh3_factors_capri.json, 2017/feed/feed_ration_2017.json,
  fodder_balance_2017.json, 2017/supply/young_animals_2017.json, young_animals_by_sex_2017.json,
  trajectories/capri_ref_2030.json, captrd_2030.json, sources/estnlp/pela_cross_by_region.json,
  sources/residual_cost_calibration.json, and the two crosswalks (shared/nuts_crosswalk.json,
  nuts_version_correspondence.json), which the move makes unnecessary for EU27 + Norway.

## 4. Code

- 35 builders read the region map or a crosswalk (tools/build, tools/lib); build_capri_base.py holds the `ZERO` list.
- capri_mod: `SupplyModule.NON_EU_PREFIXES` ("NO"), `capri_ms()` (model region to CAPRI member state), loaders that
  key by NUTS-2016 codes, the market's member-state mapping (rms.csv, rms_to_rm.csv: CAPRI codes already).
- Tests name model regions (DE11, NL22, FRB0, IE04, ...): those that are not CAPRI units change with the move.
- Cached market supply Hessians are keyed by the region list: they will be measured again (one full measurement per
  reference baseline, about 50 minutes each on 2 cores).

## 5. Proposed order of work (for decision)

1. One region list and one map: the model's regions become CAPRI's 221 units. **Decision needed: region codes** -
   CAPRI's 8-character codes as the model's identifiers (DE110000; no map left between the two), or short codes
   derived from them (DE11). My recommendation: CAPRI's codes, so every CAPRI file is read without a translation.
2. Rebuild the 79 live files (and the JSON inputs) with their builders on that list; trace the 12 without a builder.
3. Remove the crosswalks, the `ZERO` list and the proxy splits; the 13 empty rows disappear.
4. Tests: replace region codes that are not CAPRI units.
5. Reference runs Farm-to-Fork and Green Deal 2030 on the new units (new Hessians), compared with r150 / r151
   indicator by indicator; the fodder band rows removed in the same runs (item agreed on 26 October).
6. Afterwards: restore the water and income modules on the new units; the UK, Turkey and the Western Balkans (their
   CAPREG files are in hand).
