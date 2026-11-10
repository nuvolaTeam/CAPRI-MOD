# Moving the market to CAPRI's market regions: inventory and plan (1 November 2026)

Read-only survey before the change, as decided by the project lead today ("the CAPRI way"): the market model works on
CAPRI's 45 market regions RM, with tariffs and quotas on CAPRI's 42 policy blocks RMTP and the behavioural regions RMS
mapped to them by RMS_TO_RM. Once that is done, CAPRI's TRQs (global and bilateral, all importers), flexible levies,
entry prices and the market's land and yield block can be ported as CAPRI writes them. **Nothing has been changed.**
Model for this note: docs/design/REGIONAL_UNITS_INVENTORY.md (the supply side's move to CAPRI's 221 units, 27 October).

Branch read: manifest-sql, HEAD 9be8c8c. DEP-31 to DEP-40 were then on branch step-g (merged into manifest-sql since)
(HEAD c953471) and not yet merged into manifest-sql; they are cited from there.

**Labels.** [V] = verified for this note (file read, GDX symbol read, or data compared with a small script);
[I] = inferred (read from code or documents but not run or not checked in data). File:line refers to manifest-sql.

Sources of CAPRI's sets and data: `sim_ini_21730_1.gdx` (uploaded by the project lead, 1 November 2026; CAPRI's
calibrated 2030 market state) (read with gams.core.gdx through
tools/lib/_gdx.py). The sets RM, RMTP, RMS, RMS_TO_RM, RM_TO_RMTP, RMS_TO_RMTP, RMSSUP in that file are identical to the
CSV export already in capri_reference/sets/simini_21730/ (made from sim_ini_21730.gdx; the two GDX files differ in
size by one byte, the sets are the same) [V], and capri_data/codes/rms_to_rm.csv equals sim_ini's RMS_TO_RM [V].

---

## 1. CAPRI's market regions, and capri-mod's 28 regions in them

### 1.1 CAPRI (sim_ini_21730_1.gdx) [V]

- **RM**: 45 market regions ("regional aggregates with own policy presentation").
- **RMTP**: 42 policy blocks = RM minus RM_not_RMTP (ARG, BRA, URUPAR, A_EU_WEST, A_EU_EAST) plus RMTP_not_RM
  (**MER** = ARG + BRA + URUPAR; **EU** = A_EU_WEST + A_EU_EAST). RMFTA = {MER, EU} (free-trade areas).
- **RMS**: 80 behavioural regions; RMSSUP 35 (with supply models: 26 EU member states, UK000000, NO000000, TUR, the six
  Western Balkan countries), RMSnoSup 45.
- **RMAGG** (RM made of several RMS): A_EU_WEST, A_EU_EAST, MED, URUPAR, MER_OTH, WBA.

| RM | RMTP | RMS members | | RM | RMTP | RMS members |
|---|---|---|---|---|---|---|
| A_EU_WEST | EU | BL DK DE EL ES FR IR IT NL AT PT SE FI (13, `…000000`) | | CHN | CHN | CHN |
| A_EU_EAST | EU | CZ HU PL SI SK EE LT LV CY MT BG RO HR (13) | | JAP | JAP | JAP |
| UK000000 | UK000000 | UK000000 | | MAL (Malaysia) | MAL | MAL |
| NO000000 | NO000000 | NO000000 | | INDO | INDO | INDO |
| TUR | TUR | TUR | | TAW | TAW | TAW |
| WBA | WBA | AL MK CS MO BA KO (`…000000`) | | SKOR | SKOR | SKOR |
| CH | CH | CH | | VIET | VIET | VIET |
| REU | REU | REU | | THAI | THAI | THAI |
| RUS | RUS | RUS | | ASOCE_LDC | ASOCE_LDC | ASOCE_LDC |
| UKR | UKR | UKR | | ASOCE_REST | ASOCE_REST | ASOCE_REST |
| BEL (Belarus) | BEL | BEL | | AUS | AUS | AUS |
| KAZ | KAZ | KAZ | | NZL | NZL | NZL |
| FSU | FSU | FSU | | USA | USA | USA |
| MOR | MOR | MOR | | CAN | CAN | CAN |
| MIDEAST | MIDEAST | MIDEAST | | MEX | MEX | MEX |
| NGA | NGA | NGA | | ARG | **MER** | ARG |
| ETH | ETH | ETH | | BRA | **MER** | BRA |
| ZAF | ZAF | ZAF | | URUPAR | **MER** | URU PAR |
| AFR_LDC | AFR_LDC | AFR_LDC | | MSA_ACP | MSA_ACP | MSA_ACP |
| AFR_REST | AFR_REST | AFR_REST | | RSA (rest of S. and Middle America) | RSA | RSA |
| IND | IND | IND | | MED | MED | TUN ALG EGY ISR |
| PAK | PAK | PAK | | MER_OTH | MER_OTH | VEN CHL BOL |
| BGD | BGD | BGD | | | | |

### 1.2 capri-mod's market regions today [V]

28 regions, in the order of capri_data/codes/model_trade_regions.csv (a declared code list, read by
capri_mod/data/definitions.py:195-215 into `ALL_TRADE_REGIONS`, `TRADE_REGION_OF_CAPRI`); 29 with `market.eu_blocks =
true` (EU27 replaced by EU_WEST, EU_EAST; market_module.py:85-90). Default `eu_blocks = false`
(capri_mod/settings/defaults.toml:234).

| capri-mod | CAPRI RM it holds | RMTP | note |
|---|---|---|---|
| EU27 (eu_blocks: EU_WEST, EU_EAST) | A_EU_WEST + A_EU_EAST | EU | data from CAPRI's reporting block EU27yr19 (model_trade_regions.csv row 1); block names differ from CAPRI's RM codes (A_EU_WEST/A_EU_EAST; EU_WEST/EU_EAST are CAPRI's RMEU names, RMEU_to_RM) |
| USA CAN BRA ARG AUS NZL CHN IND RUS UKR TUR MEX PAK BGD NGA ZAF ETH WBA | the RM of the same code (18) | same, except ARG, BRA → MER | one-to-one |
| IDN, JPN, KOR, THA, VNM, MAR | INDO, JAP, SKOR, THAI, VIET, MOR | same | one-to-one, **code differs** |
| NOR, GBR | NO000000, UK000000 | same | one-to-one, **code differs** |
| **ROW** | **17 RM**: CH, REU, BEL, KAZ, FSU, MIDEAST, AFR_LDC, AFR_REST, MAL, TAW, ASOCE_LDC, ASOCE_REST, MSA_ACP, RSA, MED, URUPAR, MER_OTH | 17 RMTP, but URUPAR's is MER | 23 RMS (14 single + MED's 4 + URUPAR's 2 + MER_OTH's 3) |

Counts: 26 one-to-one (8 with another code) + EU27 → 2 RM + ROW → 17 RM = 45 [V]. The policy block **MER is cut
across three capri-mod regions** (ARG, BRA and part of ROW) [V].

Code hazard [V]: `definitions.is_eu()` and `capri_ms()` (definitions.py:317-332) read a code's first two letters, so
`is_eu("BEL")` (Belarus) → True as BL000000, `is_eu("BGD")` → True as BG000000 (BGD is already a capri-mod region),
`is_eu("SKOR")` → True as SK000000; `is_eu("A_EU_WEST")` → False. No call on a market region code was found
(market, coupling, model.py, io_results.py: the calls take supply regions or member states) [I], but a move to
CAPRI's codes must not route market codes through these functions.

---

## 2. Region-keyed market input files

61 CSV files in capri_data/2017/market [V]: **13 carry no region key**, **9 are keyed by member state only**, **5 by
behavioural region only (CAPRI codes)**, **34 by capri-mod's trade regions** (often next to an RMS column). Plus four
outside that folder. Builders: tools/pipeline/builders.json (no DATA_SOURCING_REGISTRY.json exists on this branch;
capri_data/MANIFEST.json gives reader and builder per file) [V]. The extract files under capri_data/sources/market (since 6 November 2026
capri_data/sources/raw/capri/results/<CAPRI file>/: bilateral_dataout_*.csv.xz, bilateral_trq_dataout_*.csv, ...) are keyed by CAPRI codes and stay.

Rebuild class: **D** direct from CAPRI's RM-level data (the region map becomes the identity); **R** regrouping of the
behavioural-region rows the builder already reads (`model_region`/`trade_region` := RMS_TO_RM(rms)); **N** new
extraction; **U** unchanged (member-state or RMS keyed; only block names may change).

### 2.1 Keyed by capri-mod's trade regions (34 + 3 outside the folder)

| File(s) | Region key and set today [V] | Builder | Built from | Rebuild | CAPRI symbol at sim_ini |
|---|---|---|---|---|---|
| bilateral_flows_2017.csv, _2030.csv | importer, exporter: 28 (EU27 … ROW) | build_bilateral_market.py (`build`, l. 125-195) | dataOut ImportQ, ImportP, Fob, TCost, TaAppl of market_base_1717.txt / markmarket_greendeal_1730et_base_1717.txt, via sources/market/bilateral_dataout_<y>.csv.xz | **D** (use the `_eu2` extract, identity map; the two variants collapse into one file per year) | p_tradeFlows(RM,RM1,XX,"CAL"), p_impPrice(…,"CAL"), p_transpCost(…,"CAL"). **Checked:** the 2030 `_eu2` extract equals p_tradeFlows CAL over all 20,705 RM×RM pairs (max abs diff 0.16 kt, sum 2.1 kt) [V] |
| bilateral_flows_2017_eu2.csv, _2030_eu2.csv | 29 (EU_WEST, EU_EAST … ROW) | same, `--eu-blocks` | the same extract, A_EU_* kept | **D** (becomes the only form) | as above |
| bilateral_regions_2017/2030[_eu2].csv (4) | region: 28 / 29 | same | dataOut PMRK, PROD | **D** | DATA(RM,"PMRK"/"PROD",XX,"CAL"). **Checked** for USA, CHN, BRA, JAP, NO000000, WBA, A_EU_WEST, A_EU_EAST against the `_eu2` file: PROD within 0.3 kt, PMRK within 2e-4 relative, once DATA's SWHE/OLIV/PARI rows are read as the market products WHEA/OLIO/RICE [V] |
| bilateral_trq_2017.csv, _2030.csv | exporter: 16 (AUS CAN IND MAR MEX NOR NZL PAK ROW THA TUR UKR USA VNM WBA ZAF); importer implicit = EU | same (`build_trq`, l. 199-246) | dataOut rows `'EU'.<exporter>.(TrqNT, TAMFN, TSMFN, TaAppl, TsAppl, Fob, TCost, ImportQ)` (l. 212) | **N**: every importer block, keyed (importer RMTP, exporter RMTP); the exporter MER kept | p_trqBilat(RMTP,RMTP1,XX,item,"CAL"), p_trqGlobl(RMTP,XX,item,"CAL"), p_trqSigmoidSlope |
| policy/tariffs.csv | region: 28 | build_tariffs_2017.py | derived: total ad-valorem equivalent per region from the 2017 flows (l. 86 maps CAPRI regions with REGION_MAP, ROW default); EU row from sources/market/eu_tariff_provenance.csv | **D** (same formula per RM) or replace (open question 11) | DATA(RM,"TARV",XX,"CAL") exists (e.g. 51 products for USA) [V]; not compared |
| world_market_baseline.csv | region: 28 | build_world_market_baseline.py (l. 80-82: skips aggregates, EU member states → EU27, rest by `trade_region`) | FAO_agg p_dataMarket BAS (fao_agg_17_datamarket.txt) | **R** (EU per block = sum of its member states) | not in sim_ini (FAO_agg) |
| dairy_world_baseline.csv | region: 28 | build_dairy_world_markets.py (l. 63-65) | the same FAO_agg extract | **R** | not in sim_ini |
| crushing_parameters_2017/2030.csv | region: 27 (no NZL), with `capri_regions` lists | build_crushing_parameters.py (EU27 rows l. 132-150) | market dumps + elas_2 | **R** | DATA(RMS,"PROC"/"PRCY",…,"CAL") [I] |
| biofuel_feedstock_2017/2030.csv | ms (RMS, 55/60) + region (21) | build_biofuel_market.py (`model_region`, l. 139, 224) | dumps + elas_2 | **R** | p_bioSupPar, p_bioDemPar, p_dpCESBiof (RMS) [I] |
| biofuel_market_2017/2030.csv | ms (76/79) + region (28) + rmssup | same (l. 271) | same | **R** | same |
| dairy_world_processing.csv | trade_region (27, no EU27) + rms (54) | build_dairy_world_blocks.py | markmarket + elas_2 | **R** | p_hessNQDairy (RMS) |
| feed_demand_nonEU.csv, _capri_regions.csv, _elasticities.csv | region: 23 (no EU27, GBR, NOR, TUR, WBA) + capri_region (45 RMS) | build_feed_demand_nonEU.py (l. 124) | data_market Data_CAL FEED; elas_2 p_ElasFeed | **R** | DATA(RMS,"FEED",XX,"CAL"); p_hessNQFeed |
| gl_demand_goods.csv, gl_demand_regions.csv | rms (80) + model_region (27: **no WBA**) | build_gl_demand.py (l. 123) | data_market, elas_2 | **R** (and fixes the WBA defect, §4.3) | p_pdGL (3,685 records = the 3,685 rows of gl_demand_goods.csv [V]), p_pbGL |
| welfare_base_2030.csv | rms + model_region (27: no WBA) | build_welfare_base.py (takes model_region from gl_demand_goods, l. 99) | data_market, elas_2, markmarket | **R** | dataOut welfare items [I] |
| use_components.csv | rms + model_region (28) | build_use_components.py (l. 58) | data_market | **R** | DATA(RMS,"HCON"/"FEED"/"PROC"/"BIOF",…,"CAL") |
| processing_nq_base.csv, processing_nq_hessian.csv | rms + model_region (28) | build_processing_nq.py (l. 93) | data_market, elas_2 | **R** | p_hessNQProc |
| processing_seeds.csv | rms + model_region (27) | build_processing_seeds.py (l. 65) | data_market | **R** | DATA(RMS,"PRCY",…) [I] |
| noneu_feed_base.csv, noneu_feed_nq.csv | trade_region (23) + rms (45) | build_noneu_feed_nq.py (l. 76, 85) | data_market, elas_2 | **R** | p_hessNQFeed |
| noneu_feed_totals.csv | trade_region (27) | build_noneu_feed_nq.py | data_market | **R** | DATA(RMS,"FEED",…,"CAL") |
| noneu_market_supply_nq.csv | trade_region (27) + rms (54) | build_noneu_market_supply_nq.py (l. 141, 144) | data_market, elas_2, markmarket | **R** | p_hessNQSupp(RMS,XX,YY,"CUR") (92,592 records) |
| supply_elas_region.csv | region (27) + capri_regions | build_supply_elas_nonEU.py (l. 70) | supply/capri_supply_elas_market_1717.csv, bilateral_dataout_2017 | **R** | p_elasSupp in sim_ini holds only the "YILD" item (1,216 records, 45 RMS) [V]; the builder reads the 2017 elasticities |
| shared/trade_flows_2017.csv | exporter, importer: 28 | recalibrate_trade_2017.py | res_0_1717 capmod dump, FAO 2021 | none found that is needed: only an alias in capri_mod/data/loaders.py:98, no reader by name [V] → **orphan candidate** (remove) | — |
| codes/model_trade_regions.csv | the 28 codes and their CAPRI code | declared (no builder) | — | replaced by CAPRI's RM / RMTP / RM_TO_RMTP lists | sets RM, RMTP, RM_TO_RMTP |

### 2.2 Member-state keyed (9): U

dairy_hessian.csv, dairy_processing.csv (26 EU MS), eu_market_supply_base.csv, eu_market_supply_nq.csv (26),
eu_ms_balance_2030.csv (26 + column `block` EU_WEST/EU_EAST → A_EU_* if codes change), feed_bulks_eu.csv (26),
feed_bulks_no.csv (NO000000), processing_yields.csv (11 incl. `_EU`), sugar_processing.csv (23 incl. AL, BA, CS, UK)
[V]. One base change: **feed_bulks_eu.csv** prices every member state's bulks at the **EU27yr19** Arm1 price
(build_feed_bulks.py:152) while CAPRI's feedBlkPrice_ uses each RMSSUP's own RM Arm1 price (arm/market_model.gms
l. 951-962, `sum(RMS_TO_RM(RMSSUP,RM), DATA(RM,"Arm1P",XX,"CUR"))`) [V]: on RM it reads A_EU_WEST / A_EU_EAST.

### 2.3 Keyed by RMS only (5): U

dairy_world_demand_elas.csv, dairy_world_hessian.csv, gl_demand_b.csv, noneu_feed_conv.csv, noneu_feed_energy.csv
(its `rm` column already holds CAPRI's RM codes, incl. MED, MER_OTH, URUPAR) [V].

### 2.4 No region key (13)

armington_rho.csv, biofuel_use_share_2017/2030.csv, dairy_eu_balance.csv, dairy_eu_demand_elas.csv,
eu_cake_feed_bas.csv, feed_bulks_eu_share.csv, feed_byproducts.csv, feed_cal_content.csv (read by no model code;
builder intermediate), producer_prices.csv, supply_elas_eu.csv, world_market_baseline_products.csv, world_prices.csv
[V]. Two of them change with the regions through their builders [I]: world_prices.csv (FPRI is the export-weighted
price over the trade regions' flows, build_world_prices.py:86-93: splitting ROW adds its internal exports) and
feed_byproducts.csv (reads the EU27 row of bilateral_regions_2030.csv, build_feed_byproducts.py:45-48). The EU-level
files (dairy_eu_*, feed_bulks_eu_share, biofuel_use_share) are used per EU block today only through eu_split-type
allocations (§3.2); to be checked file by file in stage 2 [I].

**armington_rho.csv** [V]: sim_ini's p_rhoArm1 and p_rhoArm2 hold one value per product, identical in all 45 RM (no
product has two values); capri-mod's file equals them for every product.

### 2.5 Builders involved

About 20 (§2.1-2.4): build_bilateral_market, build_tariffs_2017, recalibrate_trade_2017 (home of `REGION_MAP` l. 54,
`trade_region()` l. 68-75 and `AGGREGATES` l. 80-88, imported by most others), build_world_market_baseline,
build_dairy_world_markets, build_dairy_world_blocks, build_crushing_parameters, build_biofuel_market,
build_feed_demand_nonEU, build_gl_demand, build_welfare_base, build_use_components, build_processing_nq,
build_processing_seeds, build_noneu_feed_nq, build_noneu_market_supply_nq, build_supply_elas_nonEU, build_feed_bulks,
build_eu_ms_balance, build_eu_market_blocks, build_world_prices, build_feed_byproducts. Every one reaches the region
set through `REGION_MAP.get(r, "ROW")` or `trade_region(r)` plus an "EU member state → EU27" rule; one change of that
mapping (identity on RM, RMS → RM by RMS_TO_RM) serves them all [I: read, not run].

Schema declarations that reference the code list (capri_data/schema): `REFERENCES model_trade_regions (code)` in
20_market_2017.sql:54 (noneu_market_supply_nq), 21_market_inputs.sql:20 (supply_elas_region), 22_market_feed_energy.sql:54,
69, 79 (noneu_feed_base, noneu_feed_nq, noneu_feed_totals), and the consistency query 20_market_2017.sql:86-89
(`coalesce(t.code, 'ROW')`) [V]. The other region columns (importer/exporter in 23_market_more.sql:7-162, model_region
l. 599-735) are free VARCHAR [V].

---

## 3. Code that depends on capri-mod's region set

Counts [V]: `eu_blocks` appears in 19 capri_mod files and 25 tools files; `self.EU` in 11 capri_mod files (78
occurrences); the market's region names in 6 test files (129 occurrences: test_capri.py 36, test_norway_market.py 64,
test_market_layers.py 9, test_welfare.py 9, test_capri_stop.py 6, test_market_nk.py 5). **No code line special-cases
ROW**: ROW exists only in the data (builders' default `"ROW"`), the code list and one comment (supply.py:85) [V].

### 3.1 Region list and maps

- definitions.py:189-192 (`EU_MS_BLOCK`, `EU_BLOCKS` from codes/eu_market_blocks.csv), 195-215 (`ALL_TRADE_REGIONS`,
  `TRADE_REGION_OF_CAPRI` from codes/model_trade_regions.csv), 218-253 (`SUP_NONEU_ALL`, `sup_noneu`: non-EU
  supply-model country → trade region through rms_to_rm.csv and TRADE_REGION_OF_CAPRI).
- market_module.py:30, 77, 85-92 (the region list: EU27 or the blocks), 99-106 (`SUP_NONEU_REGIONS`,
  `SUP_NONEU_COUNTRY`, `SUP_NONEU_MS`, `SUP`); imports of ALL_TRADE_REGIONS in calibration.py, feed.py, biofuel.py,
  demand.py, supply.py, bilateral_solve.py, dairy.py, processing.py (l. 15 of each) and data/loaders.py:23.
- tools/build/recalibrate_trade_2017.py:54-88 (REGION_MAP, trade_region, AGGREGATES); build_bilateral_market.py:96
  (`EU_BLOCKS = {"A_EU_WEST": "EU_WEST", ...}`), 130-134 (`skip`, `mp = REGION_MAP.get(r, "ROW")`).

### 3.2 EU27 special-casing (literal "EU27" / "EU27yr19")

- market_module.py:115-120 (EU tariff row copied to both blocks), 158-165 (`eu_region_of_ms`: "EU27"), 225-235
  (`eu_split`: `{"EU27": 1.0}`; equal parts where CAPRI has none), 256-262 (tariff scenario keys "EU", "EU27",
  "EU27yr19").
- calibration.py:49-52 (file suffix `_eu2`), 82-85 (non-bilateral products: the FAO_agg EU27 balance split to the
  blocks by `eu_split`), 157, 166-187 (`_align_eu_base_balance`, one EU or per block).
- bilateral_solve.py:40-47 (suffix), 75-91 (TRQs attached only if all EU rows exist), 98-104 (tariff scenario keys),
  601-607 (`eu_premium`), 621, 644-658, 660-689 (`_with_eu_aggregate`: the EU27 reporting row).
- supply.py:89-90, 227 (Hessian `{"EU27": ...}` or blocks), 318-319, 469, 496, 540, 623, 643, 688.
- demand.py:54, 198, 322-324; processing.py:55, 149, 157, 176, 186-187; dairy.py:144, 182, 247, 379, 493-505;
  biofuel.py:56, 61, 99, 130; feed.py:135, 247, 420; welfare.py:115, 444-451.
- model.py:1314-1315 (EU27 production and consumption kept from the market result).

### 3.3 The eu_blocks option (CAPRI's two EU regions)

Setting `market.eu_blocks` (defaults.toml:232-234, "DEPARTURE ... to be switched to CAPRI's setting"; read at
market_module.py:75, 83-84; data key `eu_market_blocks`). Every branch listed in 3.2 and 3.6 has its blocks side
already. DEPARTURES_FROM_CAPRI.md:357 records "Farm-to-Fork deviation 4.22 → 4.65 when tried" and "the market supply
Hessian ... is not built for the blocks yet"; the code does build per-block Hessians (coupling/hessian.py:358-370,
market/supply.py:227), so that sentence is stale or refers to the cache [I: not run].

### 3.4 ROW handling

Only in builders: `REGION_MAP.get(..., "ROW")` in build_bilateral_market.py:134, 232; build_tariffs_2017.py:86;
build_noneu_market_supply_nq.py:141, 144; build_noneu_feed_nq.py:76, 85; build_gl_demand.py:123; and through
`trade_region()` default in the others; the AGGREGATES skip (recalibrate_trade_2017.py:80-88) which contains **MER**
(and A_EU_WEST, A_EU_EAST, EU) [V]. Schema rule 20_market_2017.sql:89.

### 3.5 Norway and the UK

- Norway as market region NOR with supply models: definitions.py:218-253; market_module.py:99-106, 158-190
  (`sup_region_of_country`, `_split_supply`); model.py:631-636, 949; coupling/price_step.py:61-62;
  coupling/young_animals.py:15-16, 265; coupling/feed.py:26, 103; coupling/hessian.py:351-357; market/feed.py
  (feed_bulks_no.csv); setting `run.supply_countries_outside_eu = ["NO000000"]` (defaults.toml:28); the stop rule's
  Norway code (utils/capri_stop.py:50, model.py:1454: "NO000000", CAPRI's code already).
- UK: biofuel.py:138 (`r.ms == "UK000000"`: mandate region); GBR otherwise only through data.
- Builders: build_bilateral_market.py:131, 133 (`UK000000`, `NO000000` kept, other `…000000` skipped).

### 3.6 Coupling of the EU supply models to the market region(s)

- model.py:620-636 (each member state's models get the EU signal plus its block's departure, `_ms_block_map`),
  757-763 (`eu_price_seen` per block), 838-866 (block departures relaxed, `eu_premium_reg`), 873-880
  (capri_step_special per block).
- coupling/price_step.py:25-65 (CAPRI's step aggregates are EU_West, EU_East from eu_market_blocks.csv; prices of the
  member state's market region).
- coupling/hessian.py:345-370 (`_split_hessian`: EU, per block, per non-EU supply region).
- coupling/young_animals.py:15-16, 195, 262-265; coupling/feed.py:18-26, 103; supply/supply_module.py:2951.
- market/supply.py:496-688 (EU rows per member state → block).

### 3.7 Reports and run scripts

- io_results.py:53, 77-99 (keys `prod_EU27_*`, `price_EU27_*` and the NOR rows); biofuel/__init__.py:42-44 (EU27).
- bilateral_solve.py:660-689 keeps an "EU27" reporting row when the EU has two blocks (quantities summed, prices
  weighted) [V]: readers of "EU27" keep working if that row is kept.
- tools/run/run_f2f_2030.py:188, 259-312, 336; tools/run/run_vcs_2030.py:132; tools/check/validate_world_prices.py:85-89;
  tools/check/milk_shock_check.py:28, 34; tools/check/check_regression.py:118-121 [V].

### 3.8 Not affected

capri_mod/pipeline/captrd (CAPTRD-MOD) already works on CAPRI's own sets (`EU_EAST`, `BUR`, rms_to_rm; prepare.py:259-322,
policy.py:33-35) [V]; the supply side's 221 units are unaffected.

---

## 4. What changes in results, what is a pure regrouping

### 4.1 Pure moves (no result change expected) [I unless marked]

- Renaming the 8 codes (IDN→INDO, JPN→JAP, KOR→SKOR, THA→THAI, VNM→VIET, MAR→MOR, NOR→NO000000, GBR→UK000000) and the
  blocks (EU_WEST/EU_EAST→A_EU_WEST/A_EU_EAST), if the project lead takes CAPRI's codes.
- Making the builders work on RM first and group to the model's regions in one step (stage 1): with the current
  grouping the files must come out identical.
- Removing shared/trade_flows_2017.csv (no reader found) [V for the search].

### 4.2 Behaviour changes

1. **EU as two market regions** (DEP-3 removed): separate prices and Armington nests for A_EU_WEST and A_EU_EAST and the
   flows between them (e.g. maize A_EU_EAST → A_EU_WEST 15,041 kt at CAL [V]). Recorded effect when tried: F2F
   deviation 4.22 → 4.65 (DEPARTURES_FROM_CAPRI.md:357). The register's non-default note "with `market.eu_blocks =
   true`, the young-animal markets are updated between market solves instead of inside them"
   (CAPRI_DEPARTURES_REGISTER.md:98-99) **becomes a default departure** unless fixed in the same stage.
2. **ROW split into 17 RM**: each gets its own market price, Armington nests and policy; trade between them, today
   ROW's domestic sales, becomes bilateral trade with transport costs and tariffs. Size [V]: 49,871 kt of the
   1,234,408 kt of flows between distinct CAPRI regions in the 2030 extract with the EU as EU27yr19
   (sources/raw/capri/results/markmarket_greendeal_1730et_base_1717/bilateral_dataout_2030.csv.xz, 44 regions; 4.0%, tonnes summed over products); ROW takes 27%
   of capri-mod's inter-region imports in bilateral_flows_2030.csv and holds a median 12% of world production (above
   30% for 8 of 57 products, e.g. cocoa 69%, palm oil 34%). Non-EU supply, feed, processing and GL demand of the 23
   RMS respond to their own RM's prices instead of one ROW price. At the base point nothing should move; in
   scenarios results change.
3. **TRQs**: today the EU's quotas only, summed per capri-mod exporter (DEP-34, DEP-35). Found in this survey [V]:
   the EU's quotas against **MER** (beef 61.1, sheep and goat meat 33.5, poultry 519.0, sugar 334.1 kt in the 2030
   dataOut; EU × MER quotas are in sim_ini's p_trqBilat at CAL) are **dropped** by build_bilateral_market.py:225
   (MER is in AGGREGATES), not registered as a departure; the quotas of ROW's members (CH, MED, REU, RSA, AFR_REST,
   MSA_ACP, ...) are pooled into one "ROW" quota (e.g. sugar 1,360 kt). On RM: quotas per RMTP pair as CAPRI
   (trqSigmoidFunc_(RMTP,RMTP1,XXX), fill from TradeFlowsAgg_).
4. **Non-EU importers' bilateral TRQs** (DEP-34) [V, sim_ini p_trqBilat TrqNT at "CAL", finite values]: EU 81
   quotas (8,612.6 kt) against 22 exporter blocks; **MED 11, MOR 16, NO000000 5, RUS 2, TUR 15** (plus very large
   values, ≥ 1e8, for CHN 2, TUR 1, EU 200). MED is inside capri-mod's ROW today. This differs from
   G3_MARKET_INVENTORY.md l. 34 on step-g ("about 20 importers besides the EU blocks"), which was read from the 2030
   dataOut; to reconcile (open question 7).
5. **Global TRQs** (DEP-33) [V, p_trqGlobl TrqNT at "CAL"]: 70 quotas for 12 importers: CAN 3, CH 15, CHN 4, EU 13
   (7,007.7 kt), IND 4, JAP 5, MED 11, NO000000 5, NZL 1, RUS 3, TAW 1, USA 5. **CH, MED and TAW are inside ROW**: their
   global quotas cannot be represented on the 28 regions.
6. **Flexible levies** [V]: p_flexLevy has importer EU only, against 35 exporter blocks, for BARL MAIZ OATS OCER RICE
   RYEM SUGA WHEA. **Entry prices** [V]: p_entryPriceFac importers EU and UK000000 (APPL, CITR, TAGR, TOMA). Both act
   per (RMTP, RMTP1) pair in impPrice_ (arm/market_model.gms l. 2848-2909, read), so exporter blocks inside ROW need
   their own prices.
7. **Market land and yield block**: per RMS (Yield_, LandSupplyMNL_, ... ; G3_MARKET_INVENTORY.md "45 behavioural
   regions"); does not need RM itself, but each RMS must see its own RM's prices, which ROW pooling prevents [I].
8. **Base-data effects of rebuilding**: feed bulk prices per EU block instead of EU27yr19 (§2.2); FPRI's world price
   (§2.4); the EU blocks' balances of non-bilateral products from their member states instead of the `eu_split`
   allocation of the EU27 total (calibration.py:82-85, market_module.py:225-235, which also falls back to equal parts)
   — a proxy removed [I].
9. **Size**: 45 instead of 28/29 regions; product × (importer ≠ exporter) flows: 20,705 at CAL on RM [V] against
   11,340 in bilateral_flows_2030_eu2.csv today [V]. Per-commodity Newton systems grow from 29 to 45; the IPOPT market of step G grows
   accordingly [I]. More small regions with autarkic products (cf. BEYOND-4's flat equilibrium for Japan's sunflower
   cake) may give more degenerate markets [I].

### 4.3 A defect found (independent of the move) [V]

gl_demand_goods.csv, gl_demand_regions.csv and welfare_base_2030.csv put the six Western Balkan RMS (AL, BA, CS, KO,
MK, MO) in **ROW**, while use_components.csv and processing_nq_base.csv put them in **WBA**: build_gl_demand.py:123
maps `rmap.get(r, "ROW")` on RM codes only (the RMS_TO_RM map is read at l. 114 but not used there), and
build_welfare_base.py:99 copies that column. demand.py:53 takes `model_region` as it is, so WBA's human consumption is
modelled inside ROW's demand while its market is WBA. The move fixes it (RMS_TO_RM); it could also be fixed now.

### 4.4 Departures the move removes or touches (CAPRI_DEPARTURES_REGISTER.md; DEP-31…40 on step-g)

| Row | Effect of the move |
|---|---|
| DEP-3 one EU27 block | **removed** (stage 2) |
| non-default note: young animals updated between solves with eu_blocks | **becomes default** at stage 2 unless lifted (G2g) |
| DEP-33 no global TRQs | removable only on RM (CH, MED, TAW importers) — stage 5 |
| DEP-34 TRQs of the EU only | **removed** at stage 4 (MED, MOR, NO000000, RUS, TUR) |
| DEP-35 TRQs summed per model exporter | **removed** at stage 4 (RMTP pairs; MER restored) |
| DEP-36 out-of-quota tariff frozen as a gap | touched: port tarAdVal_ per RMTP pair at stage 4 |
| DEP-40 one Armington elasticity per commodity | touched: at sim_ini CAPRI's values are identical across RM, so it has no numerical effect at this baseline [V]; reading per RM makes the row moot |
| DEP-31 pooled commodities with a world balance; DEP-32 PMrk_ for regions without supply; DEP-5 non-EU use factor in [0.2, 5] | touched: more regions, more regions without supply of a product [I] |
| DEP-16 fixed-point market solve; DEP-37, DEP-38, DEP-39 floors and fudges | touched (per region; size) [I] |
| DEP-7 non-EU supply (UK, Turkey, WB without supply models), DEP-29 Norway's dairy lag, DEP-12 plain CES | unchanged |
| KNOWN_ISSUES K45 (EGY, ALG mapped into ROW) | superseded: they sit in MED |
| unregistered: EU × MER quotas dropped; WBA demand in ROW | to register or fix (open questions 8, 9) |

---

## 5. Staged plan (moves separate from behaviour changes)

Each stage is a separate commit series; checks as asked. The F2F/GD gate is run per batch as the project lead decides
(the agreed rule), suggested after stages 1-4 and again after 5-7.

| Stage | Content | Kind | Check |
|---|---|---|---|
| 0 | Decisions (§6: codes, EU reporting row, order with step G, source of truth) | — | — |
| 1 (**done 3 November 2026**, see below) | CAPRI's region lists as data: shared/market_regions.csv (RM, label), policy_blocks.csv (RMTP), rm_to_rmtp.csv, rms_to_rm.csv (exists), from sim_ini through a builder (as build_regional_units.py did). One grouping step in recalibrate_trade_2017 (RM → model region, today: identity on 26, A_EU_* → EU27 or blocks, 17 RM → ROW) used by all ~20 builders. Remove shared/trade_flows_2017.csv. | move | **builders reproduce**: every file of §2 identical to today's (as tools/check/compare_rekeyed.py did for the units) |
| 1b | WBA fix in build_gl_demand / build_welfare_base | behaviour (small) | rebuilt files differ only in WBA's 6 RMS; mini-EU run |
| 2 | EU = A_EU_WEST + A_EU_EAST only: `eu_blocks` removed as an option, the single-EU branches (§3.2) deleted, feed-bulk prices per block, EU balances per block from member states, young-animal markets inside the solve (or the departure registered as default) | behaviour (DEP-3) | eu_blocks=true run on today's code reproduced exactly before deleting branches; then **base reproduces** (market alone at CAPRI's 2030 CAL supply: per-RM PROD, PMRK, flows against DATA / p_tradeFlows "CAL"); market Hessians measured per block (about 50 minutes per reference baseline, REGIONAL_UNITS_INVENTORY §4); **mini-EU run** |
| 3 | ROW → 17 RM (grouping = identity); codes renamed if decided; tests' region names updated (6 files) | behaviour | **base reproduces CAPRI's 2030 calibrated market at sim_ini's state** for all 45 RM (flows: the eu2 extract already matches to 0.16 kt); mini-EU run |
| 4 | Bilateral TRQs per (RMTP, RMTP1) for every importer with quotas (EU, MED, MOR, NO000000, RUS, TUR), MER restored, fill = TradeFlowsAgg_, tarAdVal_ on the current price (DEP-34, -35, -36) | behaviour | at the base: CAPRI's quota fills (p_trqBilat ImportsR) and import prices (p_impPrice "CAL") per pair; equation-level unit tests against market_model.gms l. 3275-3475; mini-EU run; **F2F/GD gate** (batch 1-4) |
| 5 | Global TRQs: TRQImports_, tarSpecW_, tarAdValW_ for the 12 importers (DEP-33) | behaviour | base fills vs p_trqGlobl; mini-EU |
| 6 | Flexible levies (p_flexLevy, MinBordP) and entry prices (p_entryPriceFac, TriggerP) | behaviour | base tariffs vs p_flexLevy "CAL"; mini-EU |
| 7 | Market land and yield block for the RMS without supply models | behaviour | base vs DATA(RMS, LEVL/YILD, "CAL"); mini-EU; **F2F/GD gate** (batch 5-7) |

Effort, **an estimate only** (by comparison with the regional-units move, inventory to rebuilt data in about two
days, 27-28 October): stage 1 one to one and a half days; 1b half a day; stage 2 one to two days plus the Hessian
measurements; stage 3 one to two days including a base-reproduction check tool; stage 4 two to three days; stage 5
about two days; stage 6 one to two days; stage 7 three to five days. In total roughly 12-18 working days, gate runs
and their analysis not included. Uncertain mainly in stages 4 and 7 (new equations) and in solve behaviour at 45
regions.

**Largest risks** [I]: (a) convergence and run time of the fixed-point market solve with 45 regions and more small
autarkic markets, before step G's IPOPT solve exists; (b) DEP-5's baseline recalibration (non-EU use factor bounded in
[0.2, 5]) acting on 17 new regions; (c) the young-animal departure becoming default at stage 2; (d) results keyed by
region codes (io_results keys, r150/r151 comparisons) breaking if codes change and the EU27 reporting row is dropped;
(e) the `is_eu`/`capri_ms` prefix rule misreading BEL, BGD, SKOR if ever applied to market codes.

---

## 6. Open questions for the project lead

1. **Codes**: CAPRI's RM codes as the model's identifiers (JAP, INDO, SKOR, THAI, VIET, MOR, NO000000, UK000000,
   A_EU_WEST, A_EU_EAST; MER and EU for the blocks), as decided for the supply units on 27 October? My recommendation:
   yes, with a guard that market codes never pass through `is_eu`/`capri_ms`.
2. **EU reporting row**: keep "EU27" (bilateral_solve.py:660-689, read by io_results and the run scripts) or report
   under CAPRI's EU27yr19 / the policy block EU?
3. **Order**: stages 1-3 before step G's G3 assembly (so G3 is written on RM and RMTP directly, without ROW), and
   relative to refactor stage 3 (supply objects) now in progress?
4. **Source of truth**: build from sim_ini_21730_1.gdx (extracted to CSV sources, per the project rule) or keep the
   dataOut text exports? At CAL they agree for flows and regional prices and production (§2.1). Which of the two
   sim_ini files is authoritative (they differ by one byte; the sets are identical)?
5. **2017 market year** (BEYOND-7 base-year mode): rebuild on RM too from market_base_1717 (its eu2 extract exists)?
6. **Young-animal markets** with two EU blocks: fix inside the solve at stage 2, or accept as a registered default
   departure until G2g?
7. **Non-EU bilateral TRQs**: sim_ini at CAL has five importers besides the EU (MED, MOR, NO000000, RUS, TUR);
   G3_MARKET_INVENTORY.md says about 20. Which source should stage 4 follow (I suggest sim_ini "CAL", the state the
   simulation starts from)?
8. **EU × MER quotas dropped** by the builder (unregistered): register now as part of DEP-35, or fix ahead of the move?
9. **WBA's food demand in ROW** (§4.3): fix now as a bug (a small rebuild of three files), or with stage 1b?
10. **DEP-40**: CAPRI's 2030 data have one Armington elasticity per product in all RM; keep the row (formal departure)
    or note that it has no effect at this baseline?
11. **tariffs.csv**: keep capri-mod's derived ad-valorem equivalent (2017 flows) per RM, or use CAPRI's DATA(RM,
    "TARV", XX, "CAL") — to be compared first?
12. **Beyond CAPRI**: nothing proposed; the move is towards CAPRI's structure.

Facts that came from memory rather than the files: none were needed beyond the project rules (CSV inputs, follow
CAPRI, gate per batch).

## 7. Decisions (1 November 2026, the project lead)

The project lead agreed with the recommendations given with this inventory ("take CAPRI"):

1. **Codes**: CAPRI's RM and RMTP codes become the market's identifiers (question 1), after `is_eu`/`capri_ms` are
   guarded so that a market code never passes through them (BEL, BGD, SKOR).
2. **EU reporting row**: "EU27" is kept in the reports as the sum of A_EU_WEST and A_EU_EAST, so comparisons with
   earlier runs and with JRC121368 still work (question 2).
3. **Order**: the move comes after refactor stage 3's second half (supply's parameter and state objects) and before
   G3 and the ports of CAPRI's TRQs, flexible levies, entry prices and the market's land and yield block (question 3).
4. **Source**: the 2030 market is built from sim_ini (CAPRI's calibrated 2030 state), extracted to CSV sources; the
   dataOut text exports are kept for cross-checks (question 4). The two sim_ini files have the same sets and
   parameters. The non-EU bilateral TRQs therefore follow sim_ini at "CAL" (question 7); G3_MARKET_INVENTORY.md's
   "about 20 importers" is to be reconciled with it.
5. **Errors found by the survey**: the Western Balkans' food demand placed in ROW by build_gl_demand.py is fixed as an
   error in its own commit, separate from the move (question 9; done 1 November 2026 on branch k79-amm-resolve). The
   EU's quotas against MER cannot be represented exactly before the move (one quota over ARG, BRA and URUPAR, the last
   inside ROW; capri-mod's quotas are per exporting region): registered as DEP-41 and fixed by the move, where quotas
   sit on RMTP (question 8; the project lead's decision of 1 November 2026, preferred to a split rule).
6. **Tariffs**: CAPRI's own DATA(RM, "TARV", XX, "CAL") replaces capri-mod's derived tariffs.csv, after a documented
   comparison of the two (question 11).
7. **Young-animal markets with two EU blocks**: fixed inside the solve in the stage that makes the two EU regions
   permanent, not registered as a departure (question 6).

2 November 2026, the project lead: the 2017 market year is rebuilt on RM too (question 5), from market_base_1717 (its extract with the two EU regions exists); the DEP-40 row is kept, with the note that CAPRI's 2030 data have one Armington elasticity per product in every RM, so it has no effect at this baseline (question 10). Order of the work (the project lead, 2 November 2026): refactor stage 3 (supply's parameter and state objects), then this move, then the 29 supply units outside the EU (SUPPLY_NONEU_DESIGN.md).

2 November 2026 (evening), the project lead: the order is revised. The refactor is finished first (stage 3 N6, stage 4's
second half, stage 5), then the full scenario runs, then this move; meanwhile the move's data preparation that touches
no model code goes ahead (the sim_ini parameter extract to CSV and stage 1's region files). Stages fixed: the 2017
market year is rebuilt on RM in stage 1; CAPRI's TARV tariffs replace tariffs.csv in stage 2 (after the documented
comparison); the young-animal timing is fixed in stage 2 in the current market solve (G2g later writes the same markets
as G3's equations); the Farm-to-Fork and Green Deal gates after stages 1-4 and after stages 5-7
(docs/design/MODEL_CONTENT_PLAN.md).

Preparation done 2 November 2026 (branch market-rm, not yet merged): CAPRI's region lists are written by
build_code_lists from sim_ini's sets as capri_data/codes/capri/RM.csv (45), RMTP.csv (42), RM_TO_RMTP.csv and
RMEU_to_RM.csv, in CAPRI's set order, next to CAPRI's other sets, instead of the names shared/market_regions.csv,
policy_blocks.csv and rm_to_rmtp.csv of §5 stage 1; the builder checks them against RALL and codes/rms_to_rm.csv
against CAPRI's RMS_TO_RM. No model code reads them yet. The 37 sim_ini symbols the move and the ports need are
extracted to capri_reference/simini/simini_21730 (tools/build/build_simini_reference.py).

### Stage 1, done (3 November 2026, branch market-rm)

- CAPRI's region lists as code lists from sim_ini's sets (tools/build/build_code_lists.py): codes/capri/RM.csv, RMTP.csv,
  RM_TO_RMTP.csv, RMEU_to_RM.csv, and CAPRI's RMS and RMS_TO_RM in codes/rms.csv and codes/rms_to_rm.csv (written by
  build_gl_demand.py before; same bytes). The names differ from the plan's (shared/market_regions.csv, policy_blocks.csv,
  rm_to_rmtp.csv): CAPRI's own set names, as the other code lists under codes/capri.
- One grouping step, tools/lib/_market_regions.py, read from the declared table codes/model_market_regions.csv (each of
  the 45 RM and its model region: 26 their own, A_EU_WEST and A_EU_EAST EU27, 17 ROW); the 16 market builders use it in
  place of REGION_MAP, trade_region() and their own EU rules. A code neither RM nor RMS raises (it went to ROW before).
  Stages 2 and 3 change only that table.
- shared/trade_flows_2017.csv removed (no reader), with FAOSTAT's sources/fao_2021/trade_flows_2021.csv (read only by
  its builder's comparison); recalibrate_trade_2017.py keeps AGGREGATES and COMMODITY_MAP as a module.
- capri_ms / is_eu refuse CAPRI's RM and RMTP codes that are not member states (section 7, decision 1).
- The 2017 market year: its files are built from CAPRI's 2017 market data (market_base_1717, FAO_agg 2017) through the
  same grouping step, so stages 2 and 3 regroup both years by the table.
- Checks: every builder reproduces its outputs (82 files of the 16 builders); the data rebuild from blank reproduces all
  357 outputs; mini-EU run identical to dev (meta only); full suite passed. On the way, the rebuild from blank was
  repaired (it had stopped since 30 October): build_regional_units restricted to the modelled member states,
  builders.json re-traced (the code lists capri_mod.data reads on import), build_code_lists no longer reading its own
  outputs, dodo.py expanding zip arguments and fixing the hash seed.

