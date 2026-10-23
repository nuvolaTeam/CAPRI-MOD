# Open data pipeline for a CAPRI-like database: state of the art and sources (22 Oct 2026)

How each claim was checked:
- **[T]** = I tested it myself with a live API call or download on 22 Oct 2026.
- **[R]** = I read it from the cited web page or document but did not test it.
- **[C]** = I read it in the local CAPRI STAR 3.0 GAMS source at `/home/claude/work/allgms/gams/` (coco/, capreg/, coco1.gms, capreg.gms).
- **[I]** = my own inference, not stated in any source.

The source URLs are numbered [n] and listed at the end.

---

## 1. CAPRI COCO and CAPREG: documented methods and changes after 2020

### 1.1 Documentation status
- The current manual is online at bw-pages.thuenen.de/capri/capri/ [1]. Its chapter "The CAPRI Data Base" [2] has sections on COCO (national), CAPREG (regional), input allocation, the global database and policy data. The "Version 2022" PDF (`caprijan2022.pdf`, dated 18/01/2022) is linked from the same site [3] [R].
- The COCO and CAPREG text is the least up-to-date part of the manual:
  - The COCO data-coverage table (Table 4) still says EU15 1984–2018/2019, DE+EU12 1989–2018/2019, Western Balkans/TR 1995–2018/2019 and NO 1984–2017 [2] [R].
  - The CAPREG text in the online page is fragmentary. It names `agr_r_landuse` (now discontinued), FSS `ef_lu_ovcropaa` and CORINE/LUCAS, and says LUCAS was "considered but not implemented" [2] [R]. The STAR 3.0 code does include a LUCAS loader, so the page is behind the code (see 1.3).
- The release notes on the "Getting started" page list STAR 1.0–2.8 with **no dated database updates** and nothing on COCO/CAPREG. STAR 3 is mentioned only as tested with GAMS 51 and CONOPT 3 [4] [R].
- COCO originates in the CAPSIM database: Witzke, Tonini & Zintl (2008), JRC EUR 23381, "Complete and Consistent Database (COCO)". It has two steps: (1) include and combine input data, (2) calculate complete and consistent data [5] [R].
- capri-model.org lists no open data download for the COCO/CAPREG database. The wiki content is CC BY-SA 4.0, and no software licence is named for the code [6] [R].

### 1.2 COCO methods (manual [2] [R] plus code [C])
- **Data overlay (COCO1).** COCO1 uses the first-best source and fills gaps from second- and third-best sources, applying conversion factors for definitional differences [2][3] [R]. The sources are:
  - Eurostat `aact`, `apri` and `apro` tables, plus `nama_10`, `prc_hicp` and `prc_ppp`;
  - FAOSTAT, COMEXT, USDA, Aglink-Cosimo, DG AGRI, UNFCCC CRF and national yearbooks.

  `coco1_eurostat.gms` documents many manual fixes per country: deletions, rescaling, and national files for NO, FR, DK, EL, DE, EE, RO, UK, IE, AT, IT and CZ [C].
- **Estimation.** The manual describes a simultaneous **Bayesian HPD** estimation (citing Heckelei et al. 2005). Its constraints are accounting identities, aggregation restrictions, and bounds from engineering knowledge or series moments, with the aim of "minimal corrections" [2] [R]. In the code [C]:
  - It is split into separate consistency NLPs:
    - `coco1_estima`: herds, animal market balances and EAA for animal products;
    - `coco1_estimb`: crop market balances, with production fixed;
    - `coco1_estimc1`: land use classes, including non-agricultural land;
    - `coco1_estimc2`: area, yield and production within UAAR.
  - Example: `SOLVE AnimNSSQ MINIMIZING v_SSQ USING NLP` minimises a weighted sum of squared deviations.
  - Crop yields are smoothed with a Hodrick-Prescott filter [2].
  - `correct_data_jumps.gms` (2023/02, Kesting, concept by Witzke) corrects series breaks.
- **COCO2.** COCO2 estimates consumer prices, losses, the feed sector (by-products, roughage, requirements), ILO labour and LULUCF carbon [2] [R][C].
- **Eurostat balances.** The manual notes that Eurostat stopped most market balances after 2014. Cereal and oilseed balances came back in 2019 only for 2017, and FAO commodity balances end in 2013. COCO therefore relies on old balances plus FAO [2] [R]. Discontinued Eurostat tables (`apro_cpp_luse`, `bilaares`, `food_in_afeed1`) are "kept on EuroCARE servers" [2] [R].

### 1.3 CAPREG methods (code [C], manual sections 3.3.x of [3])
- `cons_levls.gms` makes NUTS1/NUTS2 activity levels and land use match the national COCO data. It uses an explicit **HPD objective** (`v_hdp`, "minimize the deviations between the a priori probability…"), with relative standard errors such as 10% of level, scaled by UAAR, and includes outlier detection on regional yields [C].
- `cons_yields.gms` makes regional yields aggregate exactly to national production and starts an **HP filter** (`hp_filter.gms`). `trend.gms` estimates national OLS trends on levels and yields [C].
- Changes after 2020 that are visible in the code [C]:
  - `build_regio2022_gdx.gms` (2022-02, Witzke/Götz; FSS-based disaggregation credited to M. Blanco): REGIO rebuilt from "Eurostat 2021" data, completed with AgriProd and FSS data.
  - `check_and_cor_regio_rev2022.gms`: manual deletion of dubious regional observations.
  - `reaggregate_nuts_rev2022.gms` (21.01.22): re-aggregation of NUTS splits and merges for EL, FI, IE and PL, covering the NUTS 2013 and 2016 revisions. Older mappings come from `nuts1995-1999.xlsx` … `nuts2006_2010.xlsx`.
  - `load_LUCAS.gms` (27/10/21, Himics): LUCAS land use with gap filling.
  - `coco1_land_hilda.gms` (2023/02, Kesting): HILDA+ priors for land consolidation.
- The regional Eurostat inputs coded in `capreg/RegioOriEurostat.gms` are `agr_r_accts`, `agr_r_animal`, `agr_r_crops`, `agr_r_landuse`, `agr_r_milkpr`, `demo_r_d3avg`, `ef_ls_ovlsureg`, `ef_olslsureg`, `ef_oluaareg` and `ef_r_nuts` [C]. Most of them are now discontinued (section 2.3).

### 1.4 The CAPRI time series paper in Scientific Data
- The paper exists: Koeble R., Leip A., Kempen M., Petersen J.-E., Gomez O., Leip D., Catarino R., Bielza M., Weiss F., Rotllan-Puig X., Paracchini M.L., See L., van der Velde M., **"EU Wide Disaggregated CAPRI Model Data: Crops, Livestock, Nitrogen In- and Outputs (Timeseries 2000-2018)"**, *Scientific Data*, doi:10.1038/s41597-026-06919-8. It was accepted on 17 Feb 2026 [7][8] [R; I read the PIK "article in press" PDF because nature.com, PMC and IIASA blocked automated access].
- **Data:** Zenodo **10.5281/zenodo.13992301**, **CC BY 4.0**. The record holds 1 km GeoTIFF packages (crop area for 35 activities, yield for 37, livestock density for 18 categories, N-budget parameters), the FSU shapefile and CSV files [8] [R]. I could not reach Zenodo from the shell, so this is not tested.
- **What it is:** CAPRI trunk r10667 (March 2023). The base year 2017 is the 2016–2018 average over 231 CAPRI regions, mostly NUTS2 2016, for EU27 without HR plus the UK. It is disaggregated to 215,199 Farm Structure Units, with a 2010 gridded FSS prior and "primacy of land stability" when stepping backwards and forwards over 2000–2018 [8] [R].
- **What it is not:** it does not publish the COCO/CAPREG national or NUTS2 tables (market balances, prices, EAA). The code needed (r10667) is "available on request" via the Bonn SVN and needs GAMS [8] [R].
- Related open datasets that are not built from CAPRI:
  - JRC harmonised subnational crop statistics, EU27, 1975–2020, NUTS 2016 (Ronchetti et al. 2024, ESSD 16:1623). The data DOI 10.2905/685949ff… requires an EC login [9] [R].
  - EuroCrops v2.0, parcel-level crop types linked to IFS/FADN (ESSD preprint essd-2025-752, Jan 2026; DOI 10.2905/b9fb9e67…) [10] [R].

---

## 2. Eurostat datasets for a CAPRI-like database

All codes below were checked against the Eurostat catalogue TOC (`api/dissemination/catalogue/toc/txt`) on 22 Oct 2026 [T]. The ones marked "API" in the last column also returned data from `statistics/1.0/data/<code>` [T]. Periods are the TOC "data start–end" values.

### 2.1 Active datasets

**Crops and land use**

| Code | Content | Period | Level | Check |
|---|---|---|---|---|
| `apro_cpsh1` | Crop area/production/yield, EU standard humidity; includes UAA and land-use aggregates (UAA, ARA, …) | 2000–2026 | national | API |
| `apro_cpnh1` / `apro_cpnh1_h` | Crops, national humidity / historical | 2000–2026 / 1950–1999 | national | API / TOC |
| `apro_cpshr`, `apro_cpnhr` (`apro_cpnhr_h` 1975–1999) | Crops by NUTS2 | 2000–2024 | **NUTS2** | API |

**Livestock**

| Code | Content | Period | Level | Check |
|---|---|---|---|---|
| `apro_mt_lscatl`, `apro_mt_lspig` | Bovine / pig herds (May-June and Nov-Dec surveys) | 1959/1969–2026 | national | API |
| `apro_mt_lssheep`, `apro_mt_lsgoat` | Sheep / goats | 1960–2025 | national | API |
| `apro_mt_ls_r` | Animal populations by NUTS2 (49 categories) | 1977–2025 | **NUTS2** | API |
| `apro_ec_poula`, `apro_mt_lsavch_r` | Poultry; average chicken population by NUTS2 | 1967–2025; –2025 | nat / NUTS2 | TOC |

**Milk and meat**

| Code | Content | Period | Level | Check |
|---|---|---|---|---|
| `apro_mk_farm`, `apro_mk_pobta`, `apro_mk_cola`, `apro_mk_fatprot` | Milk on farm, collection & dairy products, fat/protein | 1960/68–2024/25 | national | API (first 3) |
| `agr_r_milkpr` | Cow milk production on farms by NUTS2 | 1995–2024 | **NUTS2** | API |
| `apro_mt_pann`, `apro_mt_sloth`, `apro_mt_pheadm` | Slaughterings (in and outside slaughterhouses), monthly meat and trade | 1950–2025, 2009–2025 | national | API (pann) |

**Market balances**

| Code | Content | Period | Level | Check |
|---|---|---|---|---|
| `apro_cbs_cer`, `apro_cbs_oil` | Cereal / oilseed balance items (production, trade intra/extra EU, stocks, uses incl. feed, industry, biofuel) | 2016–2024 | national | API, see note |

Coverage of `apro_cbs_cer` / `apro_cbs_oil` [T, full download]: only BG, EE, EL, FI, HR, HU, IE, IT, LT, LU, LV, PL, PT, RO, SI, SK for 2017–2024, plus DE for 2019–2023, TR for 2016–2023, UK 2018 and RS 2024. There is **no AT, BE, CY, CZ, DK, ES, FR, MT, NL or SE, and no EU aggregate**. 236 cereal cells and 347 oilseed cells are flagged `CONF_STATUS=C`.

**Economic accounts and labour**

| Code | Content | Period | Level | Check |
|---|---|---|---|---|
| `aact_eaa01`…`aact_eaa06` | EAA at current / n-1 / reference-year / real prices, indices, income | 1973–2025 | national | API (01, 04) |
| `aact_eaa01_r`, `aact_eaa02_r`, `aact_eaa05_r` | EAA by NUTS2 (90 items; PRD_BP, PRD_PP, SUB, TAX) | 1980/1999–2024 | **NUTS2** | API |
| `aact_ali01`, `aact_ali01_r` | Labour input (AWU) | 1973–2025 / 1995–2023 | nat / NUTS2 | TOC |

**Prices**

| Code | Content | Period | Level | Check |
|---|---|---|---|---|
| `apri_ap_crpouta`, `apri_ap_anouta`, `apri_ap_ina` | Absolute selling prices (crops, animals), input prices | 2000–**2024** (last update 15.05.2025) | national | API |
| `apri_aip_en`, `apri_aip_fs`, `apri_aip_ft` | **New** absolute input prices: energy, feed, fertiliser (nutrient content) | **2025 only** | national | TOC |
| `apri_pi_outa`, `apri_pi_ina` (+ `_q`) | Price indices, output / input | 1994/95–2025 | national | TOC |
| `apri_lprc`, `apri_lrnt` | Land prices and rents | 2011–2024 | regional | TOC |

**Farm structure (FSS/IFS)**

| Code | Content | Period | Level | Check |
|---|---|---|---|---|
| `ef_lus_main`, `ef_lus_allcrops`, `ef_lus_pegrass`, `ef_lus_irri`, `ef_lsk_main`, `ef_lsk_bovine` (+ pigs, sheep, goats, poultry), `ef_m_farmleg`, `ef_m_irri` | IFS/FSS by farm type, economic size and UAA class | survey years **2005, 2007, 2010, 2013, 2016, 2020, 2023** [T] | **NUTS2** | API (lus_main, lsk_main, m_farmleg) |

**Land cover/use, nutrients, organic, trade**

| Code | Content | Period | Level | Check |
|---|---|---|---|---|
| `lan_lcv_ovw`, `lan_use_ovw` | LUCAS land cover / use | 2009–2022 | NUTS2 | API (structure) |
| `aei_fm_usefert` | Inorganic fertiliser consumption (N, P) | 1995–2024 | national | API |
| `aei_pr_gnb` | Gross nutrient balance (N, P; 40 indicators incl. inputs/outputs) | 1985–2023 | **national only** (EU27, 27 MS, NO, CH, UK, TR) [T] | API |
| `aei_fm_ms` | Manure storage | 2000–2010 | NUTS3 | TOC |
| `org_cropar`, `org_croppro`, `org_lstspec` | Organic area, production, livestock | 2012–2024 | national | API (cropar) |
| Comext `DS-045409` | EU trade by HS/CN8 (endpoint `api/comext/dissemination/statistics/1.0/data/DS-045409`) | 1988– | reporter × partner | API |

### 2.2 Code and format changes to handle
- **STRUCPRO code harmonisation, May 2026** [T + Eurostat information note of 31 Mar 2026 [11]]. Crop datasets now use `AR_THS_HA`, `MAR_THS_HA`, `HUMD_EU_PC`, `HPRD_HUMD_EU_THS_T` and `YLD_HUMD_EU_T_HA`. Eurostat says the old-to-new mapping is "available in the bulk download facility" [11]. Any extractor written for the old codes (e.g. `AR`, `PR_HU_EU`) breaks.
- **Confidentiality and flags.** SDMX-CSV now carries separate `OBS_FLAG` and `CONF_STATUS` columns [T]. Confidential cells come with an empty `OBS_VALUE` and `CONF_STATUS=C` (e.g. `ef_lus_main` ITC4 2020: 304 of 2,904 HA cells). In JSON-stat the status shows as `"|C"`. Other flags I saw: `b` (break; all `apro_mt_ls_r` ITC4 2022 values), `e`, `n`, `d`, `m` [T].
- **New price structure from 2025.** Regulation (EU) 2022/2379 (SAIO) covers animal production, crop production, agricultural prices, nutrients and plant protection products. It applies from 1 Jan 2025 and repeals Regs 1165/2008, 543/2009, 1185/2009 and Dir 96/16 [12] [R]. The new 2025-only `apri_aip_*` tables and the old absolute price tables stopping at 2024 fit this change [I]. As of today I found **no Eurostat absolute output-price table for 2025** [T, TOC search].

### 2.3 Discontinued or frozen tables that CAPRI STAR 3.0 still reads [C], checked [T]
- **Gone** (not in TOC, and API returns `404 ERR_NOT_FOUND_4` where tested):
  - Crop balances `apro_cpb_cerea`, `_drpul`, `_foil`, `_fruveg`, `_potat`, `_rice`, `_sugar`, `_wine`;
  - `apro_cpp_crop`, `apro_cpp_luse`;
  - Animal-product balances `apro_mt_bal`, `apro_mk_bal`, `apro_ec_bal`;
  - Regional `agr_r_crops`, `agr_r_animal`, `agr_r_landuse`, `agr_r_accts`;
  - `food_in_afeed1`, `bilaares`, `food_pd_prc1`, `ef_oluft`, `ef_oluaareg`, `demo_r_d3avg`.
- **Frozen:**
  - `aact_uv01`–`03`, the EAA unit values used for COCO prices: 1980–2018, last update 2020;
  - `agr_r_accts_h` (EAA NUTS2 to 2012);
  - `ef_lu_ovcropaa` and `ef_ls_ovaareg` (1990–2007);
  - `ef_olslsureg` and `ef_olslsuft` (2005–2013);
  - `apri_ap_h*` (to 2006).
- **Successors:**
  - `aact_eaa01_r` → regional EAA;
  - `apro_cpshr`/`apro_cpnhr` → regional crops;
  - `apro_mt_ls_r` → regional animals;
  - `ef_lus_*`/`ef_lsk_*`/`ef_m_*` → farm structure;
  - `apro_cbs_*` → partial crop balances;
  - for animal-product balances there is **no Eurostat successor** [I, from TOC search].

---

## 3. DG AGRI agri-food data portal (agridata)

- **API** [T]:
  - Base URL `https://api.tech.ec.europa.eu/agrifood`. The OpenAPI spec is at `/agrifood/v3/api-docs` ("Agrifood API Documentation 4.0.3-RELEASE", 116 paths), with per-sector docs at `https://agridata.ec.europa.eu/extensions/API_Documentation/<sector>.html` (e.g. `cereals.html`) [13][14].
  - No authentication was needed. Responses are JSON arrays.
- **Endpoint groups** [T, from spec]:
  - `cereal`, `oilseeds`, `rice`, `sugar`, `oliveOil`, `wine`, `fruitAndVegetable` (supply-chain prices);
  - `beef`, `pigmeat`, `sheepAndGoat`, `poultry` (incl. eggs), `liveAnimal`, `dairy`, `rawMilk`;
  - `fertiliser` (EU-level prices), `organic`;
  - `taxud/weeklyData/import|export` (customs surveillance, CN8/TARIC10);
  - `indicators/pmef` and `cmefIndicators` (CAP monitoring indicators).

  Most sectors have `/prices` and `/production` endpoints with filters such as `memberStateCodes`, `years`, `months`, `marketingYears` (yyyy/yyyy) and `beginDate`/`endDate` (dd/mm/yyyy).
- **Tested calls:**
  - `cereal/production?memberStateCodes=IT&years=2025` returns area/production/yield by crop;
  - `dairy/production` returns monthly product volumes;
  - `rawMilk/prices` and `fertiliser/prices` return data;
  - `cereal/prices?…&marketingYears=2025/2026` returns weekly port and market prices.

  Some filter combinations return HTTP 404 "No results found" rather than an empty list.
- **Data-quality note** [T]: prices come back as **strings with a currency sign and mixed decimal separators**, e.g. `"€265,23"` (cereals) vs `"€53.49"` (raw milk). Parsing has to handle both.
- **No balance-sheet or outlook endpoint** in the spec [T]. Trade in the API is limited to TAXUD weekly surveillance. Full trade data comes from Eurostat Comext.
- **EU agricultural outlook:**
  - The 2025-35 edition was published on 16 Dec 2025 [15] [R]; the report is at op.europa.eu [15].
  - The medium-term page still lists the 2024-35 PDF as the newest document and **offers no XLSX/CSV**. It points to the portal's outlook page and JRC Sankey diagrams [16] [R].
  - The portal page `DataPortal/outlook.html` describes short-term (EU balance sheets: production, trade, consumption, stocks) and medium-term (10-year balance sheets plus macro assumptions) data "visualised in tables and graphs" [17] [T]. `DashboardMTO/MediumTermOutlook.html` is an embedded dashboard app with no static data-file link in its HTML [T].
  - I found **no machine-readable download** for the outlook tables. Export, if any, is through the dashboard UI (not tested).
- **FADN/FSDN:** the public database consists of the FarmEconomyFocus dashboards (EU and country, crop, livestock and mixed farms). Data is aggregated only, and detailed data is available on request for research [18] [R]. There is no API endpoint in the spec [T].

---

## 4. FAOSTAT and OECD-FAO Outlook

### FAOSTAT
- **Bulk catalogue:** `https://bulks-faostat.fao.org/production/datasets_E.json` (69 datasets) [T]. Each dataset has a `FileLocation` pointing to `…_E_All_Data_(Normalized).zip`. Relevant codes and update dates [T]:

| Code | Content | Last update |
|---|---|---|
| QCL | Crops and livestock production | 2025-12-31; zip 33.9 MB |
| SCL | Supply Utilization Accounts 2010– | 2025-11-01; 89.5 MB |
| FBS | Food Balances 2010– | 2025-10-28 |
| FBSH | Food Balances to 2013, old methodology | 2023-03-10 |
| CB | Commodity Balances, non-food, 2010– | 2026-06-15 |
| TCL | Trade, crops and livestock products | 2026-07-24 |
| TM | Detailed trade matrix | 2025-12-23; 420.7 MB |
| PP | Producer prices | 2026-10-09 |
| QV | Value of production | 2026-05-11 |
| RFN / RFB | Fertilizers by nutrient / by product | 2026-07-30 |
| RL | Land use | 2026-10-02 |
| ESB | Cropland nutrient balance | 2025-12-05 |
| EMN | Livestock manure | 2025-10-28 |
| LC | Land cover | 2026-07-17 |
| GT | Emissions totals | 2025-10-28 |
| OA | Population | 2026-03-09 |

- **REST API:** `faostatservices.fao.org/api/v1/...` returned **HTTP 401** [T]. A third-party client's documentation says a free FAOSTAT API account and token are required [19] [R]. The bulk zips need no authentication [T].
- **Licence:** FAO statistical databases are CC BY 4.0 unless stated otherwise, plus FAO terms of use [20] [R].
- **Methodological break:** FBS/SCL use the new methodology from 2010, while FBSH (old methodology) runs to 2013 [T, catalogue names].

### OECD-FAO Agricultural Outlook (SDMX, `sdmx.oecd.org/public/rest`) [T]
- Dataflows under agency **`OECD.TAD.ATM`**:

| Dataflow | Version |
|---|---|
| `DSD_AGR@DF_OUTLOOK_2021_2030` | 1.0 |
| `DSD_AGR@DF_OUTLOOK_2022_2031` | 1.0 |
| `DSD_AGR@DF_OUTLOOK_2023_2032` | 1.0 |
| `DSD_AGR@DF_OUTLOOK_2024_2033` | 1.1 |
| `DSD_AGR@DF_OUTLOOK_2025_2034` | 1.1 |
| **`DSD_AGR@DF_OUTLOOK_2026_2035`** (latest) | 1.1 |

- **Dimensions, in key order:** `REF_AREA.FREQ.COMMODITY.MEASURE.UNIT_MEASURE.VERSION_ID`, then `TIME_PERIOD`.
  - Commodity codes follow CPC 2.1 (e.g. `CPC_0111` = wheat).
  - Measures include `AH` (area harvested), `BF` (biofuel use) and `QP_ET` (ethanol production).
  - Areas include `EU`, `EU15`, …
  - Attributes include `UNIT_MULT` and `OBS_STATUS`.
- **Working query** [T]: `…/data/OECD.TAD.ATM,DSD_AGR@DF_OUTLOOK_2026_2035,1.1/EU.A.CPC_0111..../?startPeriod=2034&endPeriod=2035&format=csvfilewithlabels` returns 36 rows. The key needs **all 6 positions**; with 5, the API answers "Not enough key values".
- **Licence:** the OECD moved to open access in July 2024 [21] [R]. I could not retrieve the licence text itself, so the exact licence and any terms for jointly produced OECD-FAO data are **not confirmed**.

---

## 5. Existing open-source tools and related projects

| Tool | Version / date | Licence | Notes |
|---|---|---|---|
| `eurostat` (PyPI) | 1.1.1, 2024-06-13 | MIT | Eurostat API wrapper [T PyPI] |
| `sdmx1` (PyPI, khaeru/sdmx) | 2.28.0, 2026-10-18 | Apache-2.0 | Actively maintained fork of pandaSDMX. Has ESTAT/OECD/FAO source definitions (not tested here) [T PyPI] |
| `pandaSDMX` | 1.10.0, 2023-02-25, Python <3.12 | Apache-2.0 | **Stale.** Use sdmx1 or pysdmx instead [T PyPI] |
| `pysdmx` (sdmx.io) | 1.21.0, 2026-10-16 | Apache-2.0 | [T PyPI] |
| `faostat` (PyPI) | 2.0.1, 2026-03-11 | MIT | Uses the FAOSTAT API, so it is probably affected by the 401/token requirement [T PyPI; I] |
| R `eurostat` (rOpenGov) | 3.7.x listed on rdocumentation | not verified | [22] |
| R `regions` (rOpenGov) | 0.1.8, 2021 | GPL-3 | NUTS validation/recoding and imputation [23] [R] |
| R `nuts` | 1.0.0, 2024-03-22 | MIT | Converts NUTS 2006/2010/2013/2016/2021 by spatial interpolation (JRC 100 m area/population/land-use grids). **No NUTS 2024** [24] [R] |
| `nuts-finder` (PyPI) | 21.5.5.14 | MIT | Point → NUTS lookup [T PyPI] |

- **Open consolidated agricultural databases** comparable to COCO/CAPREG: **none found.**
  - CAPRI publishes the disaggregated outputs described in 1.4, not its COCO/CAPREG tables.
  - The AGMEMOD page mentions an internal Excel database (1973–2017) and says nothing about public availability or licence [25] [R].
  - The FSDN/FADN public database is aggregated dashboards only [18].
  - The closest open building blocks are the JRC subnational crop statistics [9], EuroCrops v2.0 [10] and the CAPRI disaggregated Zenodo data [8].

---

## 6. Data-quality issues relevant to reconciliation

1. **NUTS versions mixed inside one dataset over time** [T]. Eurostat regional tables use the geo codes valid for each reference year and do **not** back-cast consistently:
   - `apro_cpshr` and `apro_mt_ls_r` use NUTS 2021 codes (NL31, NL33, PT16, PT17) to 2022 and NUTS 2024 codes (NL35, NL36, PT19, PT1A, PT1D) from 2023 onward. `ef_lus_main` does the same: 2016/2020 vs 2023.
   - `aact_eaa01_r` instead has PT in NUTS 2024 back to 2016, and NL in NUTS 2024 only from 2020, with NUTS 2021 codes to 2021.
   - The `apro_cpshr` geo codelist holds 649 codes from several versions, e.g. both ITD/ITH and FR24/FRB0 [T].
   - The pipeline therefore needs a (dataset, geo, year) → target-version mapping, not a single recode.
2. **Changes from NUTS 2021 to NUTS 2024** at NUTS2 [T, Eurostat change file [26]]:
   - NL: Utrecht and Zuid-Holland boundary shift, NL31→NL35 and NL33→NL36;
   - PT: PT17 split into PT1A and PT1B, new PT1D carved from PT16 and PT18 (now PT19, PT1C);
   - IT: ITH5/ITI3 boundary shift below the NUTS2 level;
   - BE: one name change.
3. **NUTS versions and when they apply to data transmission** [27] [R]:

| Version | Regulation | Transmission years |
|---|---|---|
| NUTS 2013 | 1319/2013 | 2015–17 |
| NUTS 2016 | 2016/2066 | 2018–20 |
| NUTS 2021 | 2019/1755 | 2021–23 |
| NUTS 2024 | 2023/674 | 2024–26 |
| **NUTS 2027** | **2026/195** | 2027 onward |

   Change files exist for 2013→2016, 2016→2021 and 2021→2024 (xlsx), and 2024→2027 (document) [27]. The correspondence page links `Correspondence-table-2024-NUTS-SR-EN-DE-FR.xlsx` and states that it is based on NUTS 2027 and LAU 2025 (last update 27 Apr 2026) [28] [R].
4. **Confidential cells** (`CONF_STATUS=C`, value missing) [T]:
   - frequent in IFS cross-classifications;
   - present in the crop balance sheets (236 cereal and 347 oilseed cells);
   - small crops and small countries are typical cases [I].

   These are not zeros. Reconciliation should treat them as unknown, bounded by the published totals.
5. **Breaks:** flag `b` (e.g. `apro_mt_ls_r` 2022 ITC4). Others:
   - the IFS 2020 methodology change from FSS [8];
   - the FBS methodology change in 2010;
   - EAA unit values frozen at 2018;
   - absolute prices ending at 2024 under the SAIO transition;
   - the STRUCPRO code renaming (May 2026).
6. **Coverage holes:**
   - national balances for animal products are missing entirely, and crop balances lack 10 Member States [T];
   - `aei_pr_gnb` is national only [T];
   - regional crop data end in 2024 while national data reach 2026 [T];
   - IFS covers only the survey years (2005, 2007, 2010, 2013, 2016, 2020, 2023) [T].
7. **Definitional differences:**
   - FSS/IFS reference-day herds vs annual-production herds in CAPRI [8];
   - EU standard humidity vs national humidity, which are separate datasets [T];
   - FSS farm land attributed to the holder's address, so UAA can exceed physical area [8].

---

## 7. Implications for the pipeline

1. **Ingestion layer.**
   - Eurostat: use the SDMX 2.1 or 3.0 **SDMX-CSV** endpoint [29] for whole datasets, because it keeps `OBS_FLAG` and `CONF_STATUS` as columns. Use JSON-stat only for small queries. Pin the TOC "last update" date and raw file hash per dataset in a manifest so runs are reproducible.
   - FAOSTAT: use the bulk zips only; the API requires authentication.
   - OECD: use the SDMX CSV with all 6 key positions.
   - DG AGRI: use REST JSON, with a robust price-string parser.
2. **Code-list versioning.** Expect Eurostat code changes such as STRUCPRO (2026). Keep CAPRI ↔ Eurostat mappings in versioned CSV files, as CAPRI does in `eurostat_*_mapping.gms`, and fail loudly when a code is unmapped.
3. **Replacing discontinued CAPRI sources.**
   - Crop and animal market balances: no full Eurostat replacement exists. The options are:
     - `apro_cbs_*`, partial: 16 MS + DE;
     - FAOSTAT SCL/FBS/CB from 2010 (complete but with a different methodology);
     - production from `apro_*` combined with Comext trade (net trade; stocks and uses then have to be estimated).

     This is where a COCO-like estimator does most of its work. CAPRI itself falls back on old balances plus FAO [2]. Which hierarchy to use is a decision for you.
   - Unit values (`aact_uv*`, frozen at 2018): derive implicit unit values as EAA value divided by an `apro` quantity. This is my proposal, not a documented CAPRI step.
4. **Estimator.** Port the HPD/weighted least-squares structure of COCO1 (`estima`, `estimb`, `estimc1`/`c2`) and CAPREG (`cons_levls`, `cons_yields` plus the HP filter) as separate constrained least-squares problems, solvable with the existing IPOPT setup. Confidential and missing cells become free variables bounded by published aggregates. Flag `b` breaks should lower the prior weight on pre-break observations.
5. **Regional layer.**
   - Pick one target NUTS version for CAPREG. CAPRI regions are mostly NUTS2 2016 [8].
   - Recode each (dataset, year) via the official change files: in practice the NL and PT 2024 changes plus the 2016/2021 chains.
   - For true boundary changes such as PT1D, a split needs weights. Options are IFS 2020 microdata aggregates if available, or the R `nuts` package's grid-based weights (which only reach NUTS 2021).
   - Do not rely on Eurostat back-casting, because it differs by dataset.
6. **Prices.** From 2025, absolute output prices are not yet published. Plan a fallback: EAA implicit prices, price indices (`apri_pi_*`) chained to the last absolute level, FAOSTAT PP, and DG AGRI market prices (weekly/monthly, Member-State level).
7. **Outlook alignment.** Use OECD-FAO `DF_OUTLOOK_2026_2035` via SDMX. The DG AGRI MTO 2025-35 tables have no machine-readable source that I could find. Ask DG AGRI, or use the report tables, if MTO targets are needed for the baseline.
8. **Licensing.**
   - Eurostat: reuse under Commission Decision 2011/833/EU with acknowledgement. This is not formally CC BY, and there are restrictions on non-EU and third-party data [30].
   - FAO: CC BY 4.0 [20].
   - OECD: open access; licence to be confirmed [21].
   - CAPRI disaggregated data: CC BY 4.0 [8].
   - Recording source and licence per series in the output database is cheap and protects redistribution.
9. **Beyond CAPRI.** These are options for you to decide on, not recommendations to adopt automatically:
   - (a) Use the JRC harmonised subnational crop statistics [9] as an extra prior for CAPREG yields, which would go beyond Eurostat REGIO.
   - (b) Use LUCAS `lan_*` and EuroCrops [10] as land-use priors, as CAPRI started doing with LUCAS and HILDA.
   - (c) Publish the reconciled national and NUTS2 database itself, with provenance flags. CAPRI does not currently do this.

---

## Sources
1. CAPRI online manual — https://bw-pages.thuenen.de/capri/capri/
2. CAPRI manual, "The CAPRI Data Base" — https://bw-pages.thuenen.de/capri/capri/the_capri_data_base.html
3. CAPRI documentation 2022 (PDF) — https://capri-model.org/lib/exe/fetch.php?media=docs:caprijan2022.pdf
4. CAPRI "Getting started" / release notes — https://bw-pages.thuenen.de/capri/capri/getting_started_with_capri.html
5. Witzke, Tonini, Zintl (2008), CAPSIM database, JRC44285 — https://publications.jrc.ec.europa.eu/repository/handle/JRC44285
6. capri-model.org home page — https://capri-model.org/
7. Koeble et al., Scientific Data, doi:10.1038/s41597-026-06919-8 — https://www.nature.com/articles/s41597-026-06919-8
8. Same paper, article-in-press PDF (PIK repository; the version I read) — https://publications.pik-potsdam.de/rest/items/item_34367_1/component/file_34368/content ; data: https://doi.org/10.5281/zenodo.13992301
9. Ronchetti et al. (2024), ESSD 16:1623 — https://essd.copernicus.org/articles/16/1623/2024/
10. Claverie et al., EuroCrops v2.0, ESSD preprint — https://essd.copernicus.org/preprints/essd-2025-752/
11. Eurostat information note on STRUCPRO, 31 Mar 2026 — https://ec.europa.eu/eurostat/databrowser-backend/api/public/explanatory-notes/get/Info_note_APRO_CROPS_20260331.pdf
12. Regulation (EU) 2022/2379 (summary via FAOLEX/UNEP LEAP) — https://leap.unep.org/en/countries/eu/national-legislation/regulation-eu-20222379-statistics-agricultural-input-and-output
13. agridata API docs (cereals) — https://agridata.ec.europa.eu/extensions/API_Documentation/cereals.html
14. agridata OpenAPI spec — https://api.tech.ec.europa.eu/agrifood/v3/api-docs
15. DG AGRI news on the EU Agricultural Outlook 2025-35, 16 Dec 2025 — https://agriculture.ec.europa.eu/media/news/eu-agricultural-outlook-2025-35-eu-agriculture-navigates-challenges-while-embracing-opportunities-2025-12-16_en
16. DG AGRI medium-term outlook page — https://agriculture.ec.europa.eu/data-and-analysis/markets/outlook/medium-term_en
17. agridata outlook page — https://agridata.ec.europa.eu/extensions/DataPortal/outlook.html
18. FSDN page — https://agriculture.ec.europa.eu/data-and-analysis/farm-structures-and-economics/fsdn_en
19. faostat-mcp documentation (third party; describes API registration) — https://glama.ai/mcp/servers/berba-q/faostat-mcp
20. FAO statistical database terms of use — https://www.fao.org/contact-us/terms/db-terms-of-use
21. OECD press release on open access, July 2024 — https://www.oecd.org/en/about/news/press-releases/2024/07/oecd-data-publications-and-analysis-become-freely-accessible.html
22. R eurostat on rdocumentation — https://www.rdocumentation.org/packages/eurostat/versions/3.7.5
23. R regions on rdocumentation — https://rdocumentation.org/packages/regions/versions/0.1.8
24. R nuts on CRAN — https://search.r-project.org/CRAN/packages/nuts/index.html
25. AGMEMOD at Thünen — https://www.thuenen.de/en/thuenen-institute/compound-structures/the-thuenen-modelling-network/models/agmemod
26. Eurostat NUTS 2021–2024 change file — https://ec.europa.eu/eurostat/documents/345175/629341/NUTS2021-NUTS2024.xlsx/2b35915f-9c14-6841-8197-353408c4522d?t=1717505289640
27. Eurostat NUTS history — https://ec.europa.eu/eurostat/web/nuts/history
28. Eurostat NUTS correspondence tables — https://ec.europa.eu/eurostat/en/web/nuts/correspondence-tables
29. Eurostat API getting started — https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-getting-started
30. Eurostat copyright notice — https://ec.europa.eu/eurostat/en/help/copyright-notice

Endpoints I tested myself: Eurostat TOC `https://ec.europa.eu/eurostat/api/dissemination/catalogue/toc/txt?lang=en`; `…/api/dissemination/statistics/1.0/data/<code>`; `…/api/dissemination/sdmx/2.1/data/<code>/?format=SDMX-CSV`; `…/api/comext/dissemination/statistics/1.0/data/DS-045409`; FAOSTAT `https://bulks-faostat.fao.org/production/datasets_E.json`; OECD `https://sdmx.oecd.org/public/rest/dataflow/OECD.TAD.ATM/all/latest` and the `/data/` query in section 4; agridata `https://api.tech.ec.europa.eu/agrifood/api/...`; PyPI JSON API.
