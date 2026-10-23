# COCO input datasets: catalogue v1 (23 October 2026)

Companion to `datasets_catalogue.csv` (108 rows). File paths are relative to `/home/claude/work/allgms/gams`. Eurostat existence and dimensions were checked on 23-10-2026 against the TOC (12,286 lines) and the SDMX dataflow/DSD endpoints. Anything not checked is marked *unknown* or *inferred*.

## 1. How COCO gets its raw data

COCO does not read Eurostat directly. There are two stages.

1. **`eurostat_raw.gms` (pre-processing, run separately).**
   - It `$include`s GAMS-readable CSV files from `dat/eurostat_raw/`: `Agri_prod.csv`, `eco_act.csv`, `agri_pri.csv`, `feed_agri.csv`, `food_rel_pri.csv`, `population.csv`, `cons_exp.csv`, `gdp_index.csv`, `exch_rate.csv`, `cons_pri_ind.csv`, `land_cov.csv` and `regio.csv` (eurostat_raw.gms:175, 241, 318, 374, 430, 496, 549, 607, 663, 720, 786, 933).
   - Each CSV holds a parameter keyed by (item, Eurostat geo, year). The item is one string per series: `<table>_<dim codes in the old TSV order>`, e.g. `apro_cpnh1_C1000_AR` or `aact_eaa01_01000_PROD_PP_MIO_EUR`.
   - The item lists, with labels and the source table names ("Items from file: …"), are in `eurostat_raw/*_codes.gms`.
   - Geo codes become CAPRI member states through `EuroReg_to_Coco` (eurostat_raw/reg_mapping.gms:63-123; for example EL and GR both map to EL000). Currencies go through `EuroCur_to_Coco` (:182-237).
   - The item → CAPRI (col, row) mappings are the sets `AgriProdMAP`, `EcoActMAP`, `AgriPriMAP`, `FeedagriMAP` and `FoodRelPriMAP` (eurostat_raw/agriculture_mapping.gms:11, 540, 1072, 1090, 1376), plus the macro maps (eurostat_raw/econfinc_mapping.gms), `mapping_land_use_ori_eurostat` (eurostat_raw/land_use_mapping.gms:34) and `cols_rows_regio` (eurostat_raw/regio_mapping.gms:21).
   - Outputs: `dat/coco/{agri_prod, eco_act, agri_pri, feed_agri, food_rel_pri, population, cons_exp, gdp_index, exch_rate, cons_pri_ind, land_cov}.gdx`, plus `dat/capreg/regio.gdx` and `land_cov_regio.gdx`.
   - The CSVs come from a bulk download. Their metadata says "Data from bulk download of Eurostat Statistics … converted in CSV format" (eurostat_raw/agri_prod_codes.gms:4). For apro_mk the selection is made "by the general download via R-routine" (coco/coco1_eurostat.gms:148). **That R routine and the whole `dat/` tree are not in this GAMS copy.**
2. **COCO1/COCO2 load the GDX files.**
   - COCO1: agri_prod (coco/coco1_eurostat.gms:82-85), exch_rate (:3247), eco_act (:3264-3267), agri_pri (:3656-3659) and land_cov (coco/coco1_landuse.gms:88).
   - COCO2: population (coco/coco2_collect.gms:437), cons_exp (:801-802), gdp_index (:894), cons_pri_ind (:965), feed_agri (coco/coco2_feed.gms:109) and food_rel_pri (coco/coco2_ilo_adjust.gms:427).
   - Older stored selections are still used as fall-backs. `zpa1_march2010.gdx` (coco/coco1_eurostat.gms:48-73) supplies EL fruit and vegetables, ROO1/ROO2, calves and milk deliveries.
   - About 20 country files in `dat/coco/*.gms` hold national corrections (coco/coco1_eurostat.gms:159-2882).
3. **FAO part.**
   - COCO reads `results/global/data_market_raw.gdx` (coco/coco1_load_fao_data_mapped.gms:34). This file is already mapped to CAPRI codes.
   - It is built by `global/load_fao_data_new.gms` (unload at :376) from `results/fao/faodata.gdx` (:88).
   - `faodata.gdx` is built by `prepare_faostat_database.gms` → `fao/fao_balance_consolidation.gms`, which consolidates FAO GDX extracts stored in `dat/fao/`.
   - After loading, COCO rescales to 1000 t / 1000 ha and rebooks DEMD→DOMM, RICE→PARI (/0.666) and TABO→OLIV (coco1_load_fao_data_mapped.gms:38-70).

**Consequence for the download layer:** the "stored copy" that CAPRI relies on for discontinued tables is `dat/eurostat_raw/*.csv` together with `dat/coco/zpa1_march2010.gdx`. Neither is in `/home/claude/work/allgms`. They must be obtained from the user's CAPRI installation (open question 1).

## 2. Datasets by CAPRI block

Status abbreviations: **avail** = available, **disc** = discontinued (the API answers 404 "not available for dissemination" and the code is not in the TOC), **partial** = replaced partially, **frozen** = available but no longer updated.

### Crops: areas, production, yields
- **apro_cpnh1 + apro_cpnh1_h** (avail; `_h` frozen at 1999). These feed LEVL (AR, and MA for GRAS/FARA), GROF (PR) and DRMA (HU) (agriculture_mapping.gms:1377-1570).
  - Yields are not taken from Eurostat. COCO computes YILD = GROF/LEVL·1000 (coco/coco1_cropyields.gms:27-41).
  - **Codes renamed** (checked): AR→AR_THS_HA, PR→HPRD_THS_T, MA→MAR_THS_HA, HU→HUMD_PC.
  - CAPRI uses *national* humidity. Using apro_cpsh1 (EU standard humidity, named in CAPTRD_MOD.md 8.1) would be a departure from CAPRI.
- **apro_cpp_crop** (disc). Feeds LEV3/PROD for DWH1, RAP1, POT1, POT2 and fodder crops, and DRMX (:1382-1585). COCO keeps it as a fall-back (coco/coco1_eurostat.gms:130-137).
- **ef_oluft** (disc), **ef_lu_ovcropaa** (frozen 1990-2007). Feed the FSS areas LEV2 and LEV21 (:2571-2648, :2662-2746); LEV21 fills LEV2 when it is missing (eurostat_raw.gms:254). Successors: ef_lus_allcrops / ef_lus_main (2005-2023).

### Animals: herds, slaughter, milk, eggs
- **Herds.**
  - apro_mt_lscatl, lspig, lssheep and lsgoat (avail): SUR1-SUR4 and NOM1-NOM4 (:1613-1720). **Month code M12 → M11_M12.**
  - apro_mt_lsequi (frozen 1997): OANI.LEVL.
  - ef_olslsuft (frozen 2013) and ef_ls_ovaareg (frozen 2007): poultry SUR4/SUR41.
  - Sheep and goat herds are prolonged with UNFCCC CRF data (coco/coco1_eurostat.gms:111-125).
- **Slaughter and live trade.**
  - apro_mt_pann (avail): SLGH, SLGT, IMPL/EXPL, IMPT/EXPT (:1587-1779).
  - apro_mt_sloth (avail): SLGHDOM/SLGTDOM.
  - **meatitem codes changed:** SL/EL/IL → SLAUGHT/EXP/IMP (correspondence inferred) and SLD → SLAUGHT_OTH.
- **Milk.** apro_mk_farm and apro_mk_pobta (avail; codes unchanged) cover the farm uses and dairy production (:1781-1848). DG AGRI dairy series complete them (coco/coco1_eurostat.gms:145-200).
- **Eggs and poultry.** apro_ec_lshen and apro_ec_poula are downloaded but have **no active mapping** (the HENS line is commented out at :1744).

### Market balances (IMPT, EXPT, FEDM, HCOM, INDM, SEDT, LOST, STCM, STKM, USAP, PRCM, DOMM)
- **Eurostat (all discontinued).**
  - apro_cpb_cerea, drpul, foil, fruveg, potat, rice, sugar and wine (:1926-2568).
  - apro_mt_bal (:1753-2390), apro_mk_bal (:1849-1925) and apro_ec_bal (:2391-2402).
  - Partial successors: apro_cbs_cer (SWHE, DWHE, BARL, MAIZ) and apro_cbs_oil (RAPE, SUNF, SOYA seeds), 2016-2024. No successor exists for animal products, pulses, fruit and vegetables, potatoes, rice, sugar, wine, oils or cakes.
- **FAO (what CAPRI uses beyond its stored copy).** CAPRI's FAO balances come from **CB + FBS** (2010-) and **CBH + FBSH** (-2013) (fao/fao_balance_consolidation.gms:102-116, 842-849), not from SCL. Production comes from QCL (`ProductionAndRessources2023.gdx`). Bilateral trade comes from **TM** (`FAO_trade_matrix_1986_2021.gdx`, fao/do_trade_consolidation_for_one_group.gms:235).
- **Comext.** Sugar trade comes from Comext (coco/coco1_eurostat.gms:2882; the included file has no download code).

### Prices
- **Absolute prices.**
  - apri_ap_crpouta, anouta and ina (avail, **end 2024**): PRI2/PRG2.
  - apri_ap_hcouta, haouta and hia (frozen 1969-2006): PRIC/PRIG (:1090-1231).
  - From 2025, only input prices exist (apri_aip_en/fs/ft, 2025 only). No absolute output-price successor was found in the TOC; the price indices apri_pi_outa/ina are the candidates.
- **EAA price indices.** aact_eaa05 → PRII. **CAPRI uses base 2005 (I05), which is no longer published** (units are now I20/I15/I10/I_N_1).

### EAA economic accounts
- **aact_eaa01** (avail) → EAAP, EAAB, EAAS and EAAT for outputs, inputs and income positions (:12-315).
  - **Dimension renamed:** itm_newa → am_item (01000 → AM010000; pattern inferred).
  - indic_agr codes: PROD_BP → PRD_BP, PROD_PP → PRD_PP, SUBS → SUB.
- **aact_eaa03** → EAAC (constant prices). CAPRI's unit is MIO_EUR, while the current units are CLV20/15/10_MEUR. Which reference year the stored copy uses: unknown.
- **aact_uv03** (frozen 2018) → EAAQ quantities. They serve as fall-back GROF for meat and OILC (coco/coco1_anim.gms:816 etc.).
- **aact_ali01** → GROF of LABO/LABN (AM400000/AM420000).
- Downloaded but not mapped: aact_eaa02, aact_eaa06, aact_uv01, aact_uv02 and aact_ali02.
- Pesticides: a manual xlsx (coco/coco1_eaa.gms:557-561); the link to aei_fm_salpest09 is inferred.
- Fertiliser quantities: IFA (coco/coco1_eaa.gms:536).

### Land use
- **apro_cpp_luse** (disc) → LEV1 for land totals and categories (:1459-1476). Successors are partial:
  - agricultural items are in apro_cpnh1/cpsh1 (UAA, ARA, J0000, PECR, Q0000, N0000, E0000);
  - total area, land, forest and inland water need lan_use_ovw or FAOSTAT RL.
- **LUCAS land cover.** lan_lcv_ovw is the only one applied (coco/coco1_landuse.gms:78-84). lan_lcv_fao, lan_use_ovw and lan_settl are mapped but "not applied". The data are NUTS2, aggregated to member states through nutsall_mappings.gdx (eurostat_raw.gms:833-846).
- **FAO land use.** levFAO comes from FAO land items 6601-6646 (fao/fao_balance_consolidation.gms:340-351; coco/coco1_landuse.gms:57-72). Other sources come from dat/coco/landuse_data_and_sets*.gdx (CLC, CRF, HILDA), which were not traced.

### Population, GDP and consumer data (COCO2)
- demo_pjan → INHA.
- nama_10_gdp (PD10_EUR, B1GQ) → UVAD.
- nama_10_co3_p3 (CP_MEUR) → EXP3.
- prc_hicp_aind / prc_hicp_inw → CPII / SHAR. Both are titled "(1996-2025)"; their ECOICOP ver.2 successors are prc_hicp_ainr / prc_hicp_iw.
- ert_bil_eur_a / ert_h_eur_a → exchange rates.
- food_pd_prc1 (disc) → PRIR; candidate successor prc_ppp_ind(_1).
- Feed balances food_in_afeed1 and bilaares (disc) → FEDM by feed category. No Eurostat successor found.
- Other COCO2 sources outside Eurostat and FAO: UNSTATS, ILO consumer prices, and Aglink 2019 (DG AGRI) for sweeteners (coco/coco2_collect.gms:266, 808, 1184).

### Regional (CAPREG, listed for completeness)
- **Discontinued:** agr_r_crops, agr_r_acs, agr_r_landuse, agr_r_animal, agr_r_accts and ef_oluaareg.
- **CAPRI's own replacement:** "apro_cpnhr/_h … for replacement of deprecated archive-files agr_r_acs and agr_r_crops", and FSS from ef_lu_ovcropaa, ef_oluaareg and ef_lus_allcrops (capreg/build_regio2022_gdx.gms:77-78).
- **Other successors:** apro_mt_ls_r (animals) and aact_eaa01_r (accounts).

## 3. FAOSTAT bulk files (names checked in datasets_E.json)

| Domain | File | Used by CAPRI as |
|---|---|---|
| QCL | `Production_Crops_Livestock_E_All_Data_(Normalized).zip` | `ProductionAndRessources2023.gdx` (inferred) |
| CB | `CommodityBalances_(non-food)_(2010-)_E_All_Data_(Normalized).zip` | `com_bal.gdx` |
| CBH | `CommodityBalances_(non-food)_(-2013_old_methodology)_E_All_Data_(Normalized).zip` | `com_bal_hist2013.gdx` |
| FBS | `FoodBalanceSheets_E_All_Data_(Normalized).zip` | `food_bal_sheets.gdx` |
| FBSH | `FoodBalanceSheetsHistoric_E_All_Data_(Normalized).zip` | `food_bal_sheets_hist2013.gdx` |
| TM | `Trade_DetailedTradeMatrix_E_All_Data_(Normalized).zip` | `FAO_trade_matrix_1986_2021.gdx` |
| TCL | `Trade_CropsLivestock_E_All_Data_(Normalized).zip` | `tradestat.gdx` (biofuel module only) |
| RL | `Inputs_LandUse_E_All_Data_(Normalized).zip` | land items; storage file not confirmed |
| RP | `Inputs_Pesticides_Use_E_All_Data_(Normalized).zip` | element 5157 in faodata |
| RFN | `Inputs_FertilizersNutrient_E_All_Data_(Normalized).zip` | CAPRI uses a manual `FAO_fert_pest.xlsx` |
| PP | `Prices_E_All_Data_(Normalized).zip` | manual download (fao_balance_consolidation.gms:280) |
| OA | `Population_E_All_Data_(Normalized).zip` | `population_2020.gdx` (inferred) |
| SCL | `SUA_Crops_Livestock_E_All_Data_(Normalized).zip` | not used by CAPRI (proposed in CAPTRD_MOD.md 8.1) |

The domain ↔ GDX correspondences are inferred from file names and element codes. CAPRI does not name the FAOSTAT domains in code.

## 4. Points where this differs from CAPTRD_MOD.md

- **SCL.** 8.1 proposes FAOSTAT SCL for the remaining uses. CAPRI uses CB + FBS (+CBH/FBSH). Choosing SCL is a departure from CAPRI; my view is that it may be better because it is one SUA framework, but this is for you to decide.
- **Humidity.** 8.1 names apro_cpsh1 first. CAPRI uses apro_cpnh1 (national humidity), so apro_cpsh1 would also be a departure.
- **Format changes beyond section 5.** These are additional to the crop renaming recorded there:
  - aact_eaa*: itm_newa → am_item; I05 base gone; constant-price units are now CLV20/15/10;
  - apro_mt_pann/sloth: meatitem renamed;
  - livestock surveys: month M12 → M11_M12;
  - HICP moved to ECOICOP ver.2.

## 5. Open questions

1. Obtain the stored copy (`dat/eurostat_raw/*.csv`, `dat/coco/*.gdx` including `zpa1_march2010.gdx`, `dat/fao/*.gdx`, `dat/coco/*.gms` country files) from the user's CAPRI installation. Without it, the discontinued series and the reference values cannot be reproduced.
2. Which years and download date the stored CSVs contain: unknown (metadata is inside the CSVs).
3. Verify the inferred code correspondences on data:
   - am_item = "AM" + old code + "0";
   - SL/EL/IL → SLAUGHT/EXP/IMP;
   - the aact_eaa03 reference year.
4. Feed balances (food_in_afeed1, bilaares) and food_pd_prc1 have no confirmed successor.
5. The DG AGRI dairy series: which agridata endpoint, if any, reproduces dg_agri_dairy.gms. Also, coco/dg_agri_mapping.gms is not included anywhere.
6. Whether national IMPT/EXPT in data_market_raw.gdx come from the FAO balances or from TM.
7. Output prices for 2025 and later, given SAIO (indices or another source).
8. The `coco/*_ori_eurostat.gms` and `coco/eurostat_*_mapping.gms` files are older copies not included by any program. The active ones are under `eurostat_raw/`; I cited those.
