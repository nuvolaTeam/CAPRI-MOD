# Proxy audit (no-proxies decision)

Audit of 23 October 2026. Read-only: no file under `capri_mod/`, `tools/` or `capri_data/` was changed and the model
was not run. Input: the 105 rows of `SETTINGS_INVENTORY.csv` whose notes contain "unsourced" or "proxy", plus the
`numeric_constant`/`table` rows with an empty or "no" source.

## Status after the removal (23 October 2026, evening)

Done in the code and data (the rows below keep the audit as it was written):

- **(a), all 28 rows and the two eu_blocks sites of S165:** removed. Where data could be missing the code now raises.
  - S410, S411, S149: the rent-elasticity land expansion and its machinery (the land loop in the supply module, the base
    solve for `_lambda0`) are gone. Without CAPRI's land market, or where it fails in a region, land is fixed. The
    outer-loop metric that tracked land and the N-balance price now tracks the N price only (`outer_loop.nbal_update_tol`).
  - S294: `InterventionSystem` deleted. CAPRI's intervention stocks are to be ported into the market (project lead: "port
    capri").
  - S213, S214: `fert/fert_module.py` deleted, with its two tests and the `fertilizer_module` argument of
    `EnvironmentalModule`.
  - S231: the runtime guard is gone; the function stays as a data check in the tests.
- **(b):**
  - S063, S123: CAPRI's rent rule (`tools/build/build_land_rents.py`) for the 11 regions' cells; the dual recovery and lambda
    are removed.
  - S043, S203, S208: one table, `capri_data/shared/capri_member_state_codes.csv` (CAPRI `sets.gms` NUTS0). It replaces
    37 inline maps, in 10 package modules and 8 builders.
  - S199: N in products is CAPRI's CRPR_EXPT per model head (`livestock_n_export_coef.csv`,
    `tools/build/build_livestock_n_export_coef.py`). Simulated years: milk +0.0054 kg N per kg (calc_nexport.gms); the other
    animals scale with output per head.
  - S269: the animal yield columns are CAPRI's YILD per model head / 1000 (`tools/build/build_animal_yields.py`); the loader
    heuristic is deleted.
    - DCOW changes in 54 regions. These are the regions without their own CAPRI row, plus BG and HR.
    - BG and HR fell from 6.4-8.2 to 3.3-3.9 t (CAPRI's values).
    - DCOW yield enters only the intensity margin (with a nitrate limit) and the reported milk scaling.
  - S289, S291, S292: CAPRI's 2030 budgets (CEILVAL) and premium split by scheme (PRME by scheme).
    - Data: `cap_ceilings_2030.csv` and `premium_scheme_shares_2030.csv`, built by `tools/build/build_cap_ceilings_2030.py`.
    - The payments report splits each region's premiums by scheme. National envelopes are CAPRI's DPTOTAL, and the
      utilisation is no longer clipped.
    - The Pillar II instruments are now budget changes: `lfa_budget_change`, `ae_budget_change` and `n2k_budget_change`.
      They act through premium factors per region and activity.
    - `organic_rate_change` is removed, because CAPRI has no organic scheme. `eco_scheme_budget_pct` is now a reporting
      split inside Pillar I.
    - A BISS cut of 100 EUR/ha now gives -100 per crop. It used to give -125, because an eco-scheme share was added on
      top of Pillar I.
  - S309, S311, S312: their scenarios were deleted earlier the same day (project lead: "Delete both").
- **(e):**
  - S107, S138, S209: cited in the code.
  - S107: the units are checked. man0 is in t N and the objective in EUR 1000, so CAPRI's EUR 50 is 0.05.
  - S275: CAPRI's activity term NEA = 0.17 NEM (365 - HD)(1 - Et/100) / 365 is added. HD and Et are the member state's
    (RCEmissions.csv); where CAPRI has no row, HD = Et = 0, as the GAMS zeros give.
- **(f):**
  - S065: no cross terms are built for crops that CAPRI's own PMP matrix does not cover (as CAPRI's QUADRA_, which has
    none for them). This removed the 5 capped pairs.
  - S185, S192: hits are recorded in `metadata["market_calibration_bound_hits"]` and warned. The reference runs show
    where they bind (CHANGELOG).
  - S083 (mineral cap x1.1): replaced on 24 October 2026 (KNOWN_ISSUES K71). No blanket factor: only the crop groups
    whose need is out of reach under the cap are exempted, at their baseline (CAPRI's p_checkSmallMine level 1.0),
    found by solving where CAPRI lists them by hand. Mostly PERM under Bulgaria's, Finland's, Croatia's and
    Lithuania's organic targets.
  - Still open, waiting for a decision: S131 (removed earlier the same day), S165 reached part, S173 (removed earlier the
    same day), S256, S305, S306.
- **Armington eps provenance (note to S176):**
  - DWHE, SUGB, FATS and OFOD_M: no market supply in the model, so the value is unused.
  - SUGR, WINE, OLIV, PARI, PLMO, COFF, TEAS and COCO: every producing non-EU region has CAPRI's own p_elasSupp
    (`supply_elas_region.csv`), so the eps column is not used.
  - FENI: 1 region (0.2% of non-EU output). FPRI: 5 regions (43%).
  - The processed products (butter, SMP, cheese, whey, the oils and cakes; biofuels, DDGS, fresh milk products, cream,
    concentrated milk, whole milk powder and casein at 0) use eps in every non-EU region that produces them. CAPRI
    supplies these through its processing blocks. Whether the model's processing replaces this supply function for
    them is the next thing to check.

## How "reached" was checked

- **Default run:** `tools/run/run_f2f_2030.py` with defaults: supply form nlp, PMP capri2030 (crops, animals, feed and land
  parts), trajectory capri_ref, scenario `farm_to_fork_scenario()`. The F2F scenario has manure trade off, the JRC121368
  tiered surplus rule and `eu_blocks` off.
- **Input data:** each fallback condition was evaluated on the input files, loaded the way the code loads them:
  `capri_data/2017/...`, `capri_data/shared/...` and `capri_data/trajectories/...`. Counts use the 2017 base levels. The
  2030 levels are the 2017 data times CAPRI's 2030 factors, so presence and absence of rows are the same.
- **Run outputs:** where the outcome depends on the solve, the latest default run was used:
  `/home/claude/work/runs/r99_f2f_capri.pkl` (23 Oct 13:45, nlp, capri2030, converged in 15 iterations). Its metadata
  and per-region results were read.
- **Light Python only:** `capri_pmp.build_elasticity_table` was called to get the elasticity provenance. It reads CSVs
  and solves nothing.

## Summary

| action | items |
|---|---|
| (a) remove and fail loudly: never reached in the default run | 28 rows (S030, S057, S062, S064, S085, S091, S097, S106, S124, S132, S149, S176, S177, S211, S213, S214, S228, S231, S255, S265, S281, S290, S294, S410, S411, S412, S413, S414), plus the two eu_blocks sites of S165 |
| (b) replace with CAPRI data already in the workspace | 12 rows (S043, S063, S123, S199, S203, S208, S269, S289, S291, S309, S311, S312), plus the 5 cells of S256 that have an unused CAPRI value |
| (c) replace with CAPRI data not in the workspace | 0 required (one optional export, see below) |
| (d) replace with official statistics | 0 (every item has a CAPRI source or no source at all) |
| (e) keep: the number is CAPRI's own | 4 rows (S107, S138, S209, S275). S275 and S107 come with caveats. |
| (f) needs a project-lead decision | 11 rows (S065, S083, S131, S165 reached part, S173, S185, S192, S256, S292, S305, S306) |
| numerical, not data | 37 rows (listed at the end) |
| mapping or definition, not a number | 13 rows (listed at the end) |

Total 105 rows: 28 + 12 + 4 + 11 + 37 + 13. S165 is counted once, under (f), although two of its sites are never
reached.

### What the project lead must provide

No CAPRI export is strictly required. Every replacement found is either already in the workspace or comes from CAPRI's
own GAMS rules. What is needed:

1. **Decisions** (section f):
   - **S256 / S064:** 159 region x crop cells have no PMP term in CAPRI's 2030 calibration and no CAPRI elasticity.
     34.5 of their 37 kha is OOIL; CAPRI has no own-price `p_ElasSupp` for OOIL or OIND in any member state.
   - **S065:** the 0.05 cap on cross terms outside CAPRI's own terms.
   - **S083:** the 1.1 x base relaxation of mineral caps when the NLP fails. CAPRI has the factor, but only for a listed
     set of region x crop exceptions, and only for `simy > 2035`.
   - **S131, S165, S173, S185, S192:** guards with no CAPRI counterpart.
   - **S292:** the reporting clip at 150%.
   - **S305 / S306:** two scenario presets with no CAPRI source.
2. **Optional export:** `DATA(RS,MAACT,"CRPR_EXPT","Y")` for 2030 (item S199).
   - It is not in the 2030 `dataOut` CSV: 0 hits in `res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv`.
   - The 2017 values are in the workspace.
   - It is only needed if the exact CAPRI 2030 figure is wanted. Otherwise it can be computed with CAPRI's own
     coefficients in `fert/calc_nexport.gms:26ff`, which is the preferred route because it needs no export.
3. **Scope choices.** Neither is needed for the default run:
   - **S291:** whether to replace the Pillar II participation shares with CAPRI's per-region RD budgets
     (`CEILVAL` of `DPRD_LFA`, `DPRD_AE1..8`, `DPRD_N2K`).
   - **S294:** whether to implement CAPRI's intervention-stock system (`arm/market_model.gms:452-461`) or delete the
     unused stub.

### Proxies that touch default results

Most proxies are never reached. The ones the default run does reach:

- **S063 + S123: base land duals in 11 regions (likely to matter, size not quantified).**
  - Where CAPRI's 2030 land rent is not positive, the base land-row dual comes from the model's plain QP:
    - grassland in AT11, EL62, EL63, EL64, FI19, FI20, ITF5, MT00, NL41 and PT20;
    - every land type in PT20.
  - That QP is built with the PMP shadow-price proxy (1% of revenue, floor 1) and with the 1.15 grassland headroom,
    which leaves the grassland row slack at base.
  - CAPRI applies its own rule for these cells instead (`supply/cal_land_nests.gms:204-226`):
    - arable land: at least 1.25 x PRME;
    - grassland: min(1, 0.2 x TOOU).
- **S083: mineral caps relaxed in 2 regions.** In r99 the mineral caps were relaxed to 1.1 x base in HR03 and HR04,
  and the duals were widened in LT01 (`meta["nlp_relaxed"]`, which does not say whether this happened in the baseline
  or the scenario). CAPRI's 2030 settings have no exception for these regions.
- **S173: five non-EU crushing chains dropped.** The plausibility band removes JPN SUNF, PAK RAPE, PAK SOYA, UKR RAPE
  and ZAF RAPE from CAPRI's crushing function. They fall back to the own-price processing response. These are CAPRI's
  own yields; UKR rapeseed is the largest of the five.
- **S165: processing and feed shares capped at 0.98.** 68 of 620 (region, commodity) shares (non-EU) and 5 of
  Norway's 23 feed shares are capped. At most 2% of use moves from CAPRI's function to the own-price demand.
- **S256: 159 cells on literature elasticities.** 159 region x crop cells in 143 regions, with 37 kha of 2017 area,
  calibrate their PMP curvature on literature defaults.
- **S269: animal yield units rescaled in 397 cells.** A unit heuristic rescales animal yields in 397 region x animal
  cells across 8 animals. The factors are between 3.2 and 945,556, not the 1000 of a t/kg unit change. No effect on a
  default supply or market path was found: output, revenue and PMP use CAPRI's per-head coefficients, and the
  projection uses yield ratios. The trace was not exhaustive.
- **S065: one pair-level cap in 5 regions.** 5 crop pairs in 5 regions (DEA5, EL65, ITH4, PT16, PT17).
- **Not verified:**
  - S131 (safety rail): it is evaluated in every baseline solve after the first outer iteration and binds only for
    moves above 50% of base.
  - S185 and S192: depend on the run state.
  - Each needs a logged hit count in the next run.
- **Reporting only:** S199, S289 and S292 change reported numbers only (`n_animal_products`, the policy summary). They
  do not change the solve.

---

## (a) Remove and fail loudly: never reached in the default run

| id | name | location | value | reached? | real source found | action | notes |
|---|---|---|---|---|---|---|---|
| S097 | land fallbacks ARABLE/PERMANENT/GRASSLAND | supply_module.py:3270 (+3698, 4888, 4899, 4949, 4976, 4987) | 200 / 30 / 80 kha | No. 0 of 248 regions lack a row in `land_availability.csv`, and all 5 columns have 0 NaN. The projection keeps the columns. | CAPRI land data already loaded (land_availability.csv, CAPRI) | remove + fail loudly | 13 regions have genuine zero land (city-states, ES63/64, PL31-34, HR05/06). These are data zeros, not the fallback. |
| S057 | raw-milk fallback factor | model.py:2189 | 0.9575 | No. `livestock_output_by_product_coef.csv` covers 248 of 248 regions (DCOW.COMI > 0 in 240). MILK comes from COMI + SGMI. | CAPRI's product split (already used) | remove + fail loudly | Reached only if the whole file is missing. |
| S062 | PMP base level fill | supply_module.py:348 | 0.01 | No. `_base_levels()` already fills NaN with 0, so `fillna(0.01)` never sees a NaN. | none needed | remove | |
| S064 | PMP default elasticity | supply_module.py:360 (+6053) | 0.25 | No. The elasticity table is complete for 46 activities x 248 regions. | see S256 | remove + fail loudly | The 0.25 copies at :6053, capri_pmp.py:175 and utils.py:21 are the same. |
| S132 | SupplyModule default elasticity | supply_module.py:6375 | 0.25 | No. model.py:203 always passes a Series. | n/a | remove (require the argument) | |
| S255 | calibrate_supply_elasticities default_eps | utils.py:21 | 0.25 | No. Only the OLS branch uses it, and that needs `price_history`, which no caller passes. | n/a | remove the OLS branch | |
| S176 | market default supply elasticity | market_module.py:1724 | 0.25 | No. The `armington_params.csv` eps column has 0 NaN for 62 commodities. | n/a | remove + fail loudly | Related, outside this inventory: 32 commodities use the Armington `eps` column because CAPRI's EU `p_elasSupp` (`supply_elas_eu_all.json`) lacks them. Examples: DWHE 0.25, SUGB 0.20, SUGR 0.22, WINE 0.18, OLIV 0.20, PARI 0.28, dairy 0.20-0.30. The MANIFEST labels them "CAPRI", but several are round numbers. Their provenance is worth a separate check. |
| S211 | FCER price fallback | ration.py:350 | 0.2 | No. 0 of 2,558 (region, animal) rations lack an FCER price. | n/a | remove + fail loudly | |
| S213 | fertiliser efficiency fallback | fert_module.py:154 | 1.2 | No. `FertilizerModule` is never built outside tests, and `EnvironmentalModule` is built without it. | CAPRI p_FertPerHa already used | remove (module orphan) | |
| S214 | per_crop_rates max_plausible | fert_module.py:158 | 500 kg/ha | No (same module). | n/a | remove with S213 | |
| S290 | BISS / UAA fallbacks | policy_module.py:261, :257 | 200 EUR/ha; 100 kha | No. BPS is present for 248 of 248 regions (`cap_payments.csv`, CAPRI) and land for 248 of 248. | CAPRI BPS (already used) | remove + fail loudly | |
| S294 | intervention trigger factors | policy_module.py:364-374 | 1.1, 1.05, 0.3 (and the 50% buy-in) | No. `InterventionSystem.apply_intervention` is never called; `summarise_policy` only reads stocks, which are all 0. | CAPRI has an intervention-stock system: `arm/market_model.gms:452-461` (v_buyingToIntervStock, v_releaseFromIntervStock, share equations). | remove; implementing CAPRI's is a scope choice for the project lead | The intervention prices in the same class (101.31 EUR/t cereals, 2217.5 butter, 1698 SMP) are the Reg. (EU) 1308/2013 values. Only the trigger factors are invented. |
| S030 | surplus_cut fallback | model.py:680 | 0.5 | No. `PolicyScenario.surplus_cut` always has a value (dataclass default 0.5; F2F 0.5). | n/a | remove (use the field) | |
| S124 | roughage buy-in headroom | supply_module.py:5053 | 1.5, 0.1 | No. 235 of 235 regions with herds have `fodder_balance_2017.json` rows, so the buy-in branch never runs. | CAPRI SUPBAL_ (already used) | remove + fail loudly | |
| S106 | grassland row arable share | supply_module.py:3851, :4977 | 0.2 | No. It is used only with `land_no_slack` off; the default is on. | CAPRI LandBalNoSlak_ (already used) | remove with the off branch | |
| S091 | pesticide yield-loss cap | supply_module.py:2519 | 0.90 | No. loss = 0.10 x (cut / 0.5), which is at most 0.20 at a 100% cut; F2F gives 0.10. | JRC121368 10% loss (parameter) | remove | |
| S228 | share-term floor | capri_pmp.py:71 (+ supply_module.py:390) | 0.1 | No. 1 - 0.2 x sqrt(share) is at least 0.8. | CAPRI share term (SHARE_COEF 0.2) | remove | |
| S231 | detect_synthetic min_regions | capri_pmp.py:94 | 30 | No. It blocks 0 activities (`build_elasticity_table` summary). | n/a | remove (synthetic data is gone) | |
| S177 | dairy feed share cap | market_module.py:2173 | 0.95 | No. With one EU region the largest feed share is 0.871 (whey, `dairy_eu_balance.csv`). | CAPRI dairy balance | remove | It could bind only with `eu_blocks` on. |
| S165 (461, 1094) | biofuel and feed share caps in eu_blocks | market_module.py:461, :1094 | 0.98 | No. Both sites run only with `eu_blocks`, which is off. | n/a | remove | The reached sites are under (f). |
| S410 | LAND_SUPPLY_ELASTICITY | model_parameters.csv:51 (read supply_module.py:5306) | 0.15 | No for every region with land. It applies only where the land market did not solve. In r99 the 13 regions without land types are the 13 zero-land regions; 0 of 235 regions with land. | CAPRI land market (land_market_2030.json, already used) | remove; fail if a region with land lacks land-market data | The "1 x 0.13 + 3 x 0.01" derivation is not CAPRI's. It still triggers an extra base solve to compute `_lambda0` wherever `land_rent > 0`. |
| S411 | LAND_EXPANSION_CAP | model_parameters.csv:52 | 0.15 | No (same as S410). | as S410 | remove | |
| S149 | land_cap fallback | supply_module.py:7056 | 0.15 | No (same as S410). | as S410 | remove | |
| S085 | LIVESTOCK_YIELD_TO_TONNE | supply_module.py:2189 (dup :2051) | DCOW 1, others 1e-3 | No. 0 active region x animal cells lack CAPRI's MREV/TOOU coefficient, so the yield x price revenue never runs. | CAPRI MREV/TOOU (already used) | remove with the yield-revenue fallback | |
| S281 | water module base year | water_module.py:119 | 2016 | No. `WaterModule` is not called by the model or tools. | irrishare.csv | remove or set to 2017 if revived | The docstring says 2017. |
| S265 | definitions BASE_YEAR / PROJECTION_YEARS | definitions.py:346 | 2012; [2030, 2040, 2050] | No (orphan, and wrong). | n/a | delete | |
| S412-S414 | ARMINGTON_PREMIUM_LO/HI, MIN_TRADE_SHARE_FOR_PREMIUM | model_parameters.csv:53-55 | 0.67 / 1.5 / 0.05 | No (only `_net_ratio_premium`, which nothing calls). | n/a | delete | |

## (b) Replace with CAPRI data already in the workspace

| id | name | location | value | reached? | real source found | action | notes |
|---|---|---|---|---|---|---|---|
| S063 | PMP shadow-price proxy | supply_module.py:353 | lambda = max(1% x net revenue, 1) | Always. `calibrate()` is never passed LP duals (supply_module.py:2091). The NLP recalibration (`capri_regional_nlp.calibrate`) then absorbs it into the activities' linear terms. It still sets the plain-QP solution used to recover the base land-row duals (`_land_augment`, :3873-3889). Those duals are kept only where CAPRI's 2030 rent is not positive: grassland in 10 regions and all land types in PT20 (`land_rents_2030.csv`). | CAPRI's calibration rents, `supply/cal_land_nests.gms`: arable `MAX(estimate, 1.25 x PRME)` (:204-209); grassland with a non-positive residual rent `MIN(1, 0.2 x TOOU)` (:221-226). D_AREA is in the 2030 reference CSV (`land_rents_2030.csv` is built from it); PRME and TOOU per land type are in the same file. | Apply CAPRI's rule to the 11 regions' cells, then drop lambda (calibrate with lambda = 0). | Effect on results not quantified. 248 of 248 regions have a rent row. |
| S123 | fodder headroom | supply_module.py:4980 | 1.15 x base GRAS | Reached in `b_ub` for 230 regions (GRAS = GRASSLAND in the 2017 data, so 1.15 x GRAS is larger). In the land-market problem it is overridden by the equality rows (`land_no_slack` and `land_row_equality`, :4167-4183). In the plain QP used for dual recovery it leaves the grassland row slack, so the recovered grassland dual is 0. | CAPRI LandBalNoSlak_ (equality); rents as in S063 | Remove the headroom (RHS = land figure, equality); same fix as S063. | Line 4979 also holds a dead expression (`... if False`). |
| S199 | N in animal products | environmental_module.py:897 | 25% of excreted N | Always; reporting only (`n_animal_products`). The gross N balance excludes it (comment :899-904). | CAPRI item CRPR_EXPT (N exported in products per head): 2017 values in `capri_data/sources/envind/res17_mann_crpr_expt.csv` (15,240 rows, 284 regions, from res_17*.txt). The formula is `fert/calc_nexport.gms:26ff` (BEEF x 0.022-0.0285 / carcass ratio, milk protein, ...). Use in excretion: `feed/req_or_man_fnc.gms:1825`. | Replace with CRPR_EXPT x LEVL: 2017 from the file; for simulated years apply calc_nexport.gms's coefficients to the model's product output. | CRPR_EXPT is not in the 2030 dataOut CSV (0 hits). An exact 2030 export is optional. |
| S269 | animal yield unit threshold | loaders.py:286 | 10, rescale by large/small median | Reached: 397 region x animal cells are rescaled. Counts and factors: BCOW 56 (x1,667), HFRS 60 (x9,675), CALV 56 (x7,827), SHGM 16 (x8.0), SHGF 27 (x3.2), PIGS 56 (x1,568), LAYS 64 (x865,260), BROI 62 (x945,556). | CAPRI YILD per region: `/home/claude/work/capreg/res_17<MS>.txt`, all 27 MS dumps present (e.g. AT SCOW YILD 502.05, matching yields.csv AT11 501.82). The small cluster sits in regions without their own CAPRI entry (DE30, DED2/4/5, ITH1/2, ...). | Rebuild the animal yield columns from YILD using the region groups in `tools/lib/_model_regions.py` (SPLITS_MERGES); then delete the heuristic. | No effect found on default solve paths (see summary); not traced exhaustively. |
| S289 | national envelopes | policy_module.py:229 | MS -> EUR million ("approximate 2023-2027") | Always; reporting only (`summarise_policy`, not in the F2F pickle). | CAPRI 2030 national ceilings: dataOut(MS,'','CEILVAL','DPPIL1','2030') and 'DPPIL2' [Mio EUR] in `/mnt/user-data/uploads/res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv`. Examples: FR 8,702 vs 7,000 in code; DE 5,176 vs 5,900; BL = BE + LU 570.5. Symbol: p_premDataE(...,"CEILVAL"), `policy/calc_mtr_top.gms:159-175`. | Extract to a CSV and use it. | With the present numbers, utilisation is HR 14% and FI 401% (2017 land), so the comparison is not meaningful today. |
| S291 | Pillar II participation shares | policy_module.py:268 (+492-494) | ANC 0.30, AECS 0.20, organic 0.08 | Always computed, but no effect on F2F: rate changes are 0 and the adders enter as scenario minus baseline (model.py:510-516). `cap_payments.csv` has ANC = AES = ORGANIC = 0 in 248 of 248 regions. | CAPRI does not use participation shares. It holds per-region RD budgets: CEILVAL of DPRD_LFA, DPRD_AE1..AE8, DPRD_N2K and DPPIL2, about 294 regions each, in the same 2030 CSV. Measures are defined in `policy/policy_sets.gms:750-819`. | Data: extract the DPRD_* budgets (workspace). The mechanism change (budgets per region in place of shares) is a scope choice for the project lead. | The zero Pillar II columns in `cap_payments.csv` are a data gap of their own. |
| S043 | POOL_OF_PREFIX | model.py:1496 | BE/LU->BL, IE->IR | Always (mapping) | `capri_data/shared/region_capri_map.csv` | Use the shared map | Missing GR->EL is harmless: model regions use EL. |
| S203 | inline country map (enteric) | environmental_module.py:269 | BE/LU->BL, IE->IR, GR->EL | Always (mapping) | as S043 | Use the shared map | |
| S208 | inline country map (stable time) | ration.py:170 | BE/LU->BL, IE->IR | Always (mapping) | as S043 | Use the shared map | As S043: harmless. |
| S309 | cap_2023_2027_scenario | scenarios.py:98 | eco 0.25, set-aside 0.04, AECS +10 | No (not in the default run) | `scen/base_scenarios/CAP_2023_2027.gms` (allgms) | Transcribe from the CAPRI file | |
| S311 | wto_falconer_scenario | scenarios.py:124 | per-commodity cuts | No | `scen/trade_policies/WTO/falconer.gms` (tiered formula) | Implement CAPRI's formula | |
| S312 | n_limits_scenario | scenarios.py:144 | nitrate limit -20, AECS +20 | No | `scen/NLimits/sur_nlimits.gms` (p_nMinLimit by group) | Transcribe | |

## (e) Keep: the number is CAPRI's own

| id | name | location | value | reached? | CAPRI source | notes |
|---|---|---|---|---|---|---|
| S209 | feed price floor | ration.py:233 | max(p, 0.1 x cereal price) | It enters only the formula slope, which stands in where CAPRI's 2030 feed-PMP slope is missing: 135 flexible feed cells (FSTR, FCOM, FROO, FSGM, FGRA) in 14 regions. The other 3,529 floored cells take CAPRI's slope. | `supply/pmp_terms/define_const_pmp_param.gms:107-110`: `MAX(0.1*DATA(MS,"UVAG","FCER","Y")/1000, DATA(MS,"UVAG",FEED,"Y")/1000)` | Cite in code. |
| S275 | dairy maintenance factor | projection_module.py:352 | 1.1 x REQ_NEM | No: in the default run CAPRI's 2030 ration factors (`capri_ref_ration_2030.csv`) cover 235 of 235 DCOW rations and replace this scaling. It is reached with `--base-prices` or `--trajectory captrd`. | `envind/breeding.gms:184-198`: ENNE = NEL + NEM + NEP + NEA, with NEP = 0.10 x NEM (so 1.1 x NEM = NEM + NEP) and NEA = 0.17 x NEM x grazing share | Keep 1.1 with this citation. To be exactly CAPRI's, add NEA = 0.17 x NEM x (365 - HD)(1 - Et/100) / 365 per region. HD and Et are in `abatement/ammonia/RCEmissions.csv` (workspace). |
| S107 | manure pool schedule slope | supply_module.py:4042 | 0.05 / (man0 / 100) | No in F2F (manure trade off). Reached in star3 and greendeal2030 runs. | `supply/define_manure_trade_costs.gms:66-71`: slope = 50 / (GROF / 100), i.e. EUR 50 per t for each 1% of regional manure supply traded | 0.05 matches 50 if the model works in EUR/kg; confirm the units of `man0`. |
| S138 | FODDER_ACTS | supply_module.py:6788 | GRAS MAIF OFOD ROOF | Always (set) | `sets.gms:5606` FODF / OFAR, GRAS, ROOF, MAIF / (OFOD = CAPRI OFAR) | Cite. |

## (f) Needs a project-lead decision

| id | name | location | value | reached? | real source found | why a decision |
|---|---|---|---|---|---|---|
| S256 | supply elasticity defaults table | utils.py:58 | SWHE 0.30 ... OANI 0.18 | 3,805 cells are LITERATURE_DEFAULT; 2,119 have a positive base. In the default run CAPRI's 2030 PMP terms replace the curvature of covered activities (all active animals are covered). 159 region x crop cells in 143 regions still use the literature value. By crop: OOIL 60, TABO 21, TEXT 18, TOBA 16, OIND 13, WINE 6, PARI 5, RYEM 4, OCRO 4, TAGR 4, FLOW 4, others 1 each. Area: 37 kha (OOIL 34.5). | CAPRI has no 2030 PMP term for these cells (`pmppar_21730*.gdx` via `pmp_capri_2030.csv`) and no own-price p_ElasSupp at MS level for OOIL or OIND in any `supply_elas_2_1720<MS>defaulta` export. Only 5 cells have a CAPRI MS value that is not used (RYEM in ITC3, ITH4, BE24, BE25; SOYA in EL61; file in uploads). | Choose a rule for crops CAPRI does not calibrate in a region. CAPRI's own logic gives an activity without p_technFact no level (`absent_activities_fixed`). Options: fix the cells at base, or use the MS value where one exists. The 5 cells with a CAPRI value are a (b) fix. |
| S065 | PMP cross-term cap rho_base | supply_module.py:440 | 0.05 | 5 pairs in DEA5, EL65, ITH4, PT16 and PT17: uncovered crops of one group with a PELA cross elasticity or p_pmpQuadPact term, capped at 0.05. | CAPRI uses p_pmpQuadPact at group level with no cap (`supply_model.gms QUADRA_`). PELA activity cross terms are not CAPRI's simulation structure. | Keep the cap, drop PELA terms for uncovered pairs, or use p_pmpQuadPact uncapped. |
| S083 | mineral cap relaxation | supply_module.py:1495 | 1.1 x base allocation | Reached: in r99, HR03 and HR04 ("caps"; LT01 "duals" only; `meta["nlp_relaxed"]`). | The factor is CAPRI's (`pol_input/greendeal/minfert_redu_by_crop.gms:110ff`, p_checkSmallMine = 1.1 x baseline), but CAPRI applies it only to an explicit region x crop list and only for simy > 2035. There is no HR or LT entry. | A solver-failure fallback CAPRI does not have at 2030: keep and document, or fail. |
| S131 | price-response safety rail | supply_module.py:6081 | rail = clip(4 x max(eps, 0.3) x shock, 0.5, 6) | Evaluated in every baseline solve after outer iteration 1 (`price_shock` is always passed, :7314), and in scenario solves without a surplus row. Binds only for moves above 50% of base. Hit count unknown. | None: CAPRI has no post-solve clamp. | Remove (CAPRI) or keep as a guard; first log hits in a run. |
| S165 (1119, 1472) | processing and Norway feed share caps | market_module.py:1119, :1472 | 0.98 | Reached: 68 of 620 (region, commodity) processing shares exceed 0.98 (`processing_nq_base.csv`, mostly 1.0: COCO, TEXT, PLMO, RAPO...). 5 of Norway's 23 feed shares exceed it (`feed_bulks_no.csv`). | CAPRI's ProcNQ_ moves the processing quantity itself (`arm/market_model.gms`); no share cap. | Keep (guards the residual own-price part) or restructure to CAPRI's form; small effect. |
| S173 | crush yield plausibility band | market_module.py:1521 | [0.1, 0.95], sum <= 1.05 | Reached: 5 of 50 entries are dropped. JPN SUNF has cake 0.022; PAK RAPE, PAK SOYA, UKR RAPE and ZAF RAPE have oil + cake of 1.20, 1.20, 1.72 and 1.29. | They are CAPRI's own yields (`crushing_parameters.json`). | A data guard that drops CAPRI data. Check those five yields in CAPRI before deciding. |
| S185 | non-EU use calibration bounds | market_module.py:2732 | [0.2, 5] | Depends on the run state; not determinable from inputs. | None in CAPRI | Log hits; decide. |
| S192 | bilateral max export share | bilateral.py:47 | 0.98 | Depends on the run state (the model's base supply against CAPRI's flows). | None in CAPRI | Log hits; decide. |
| S292 | budget utilisation clip | policy_module.py:318 | 150% | Always; reporting only. With today's envelopes it binds for about 15 of 28 entries (NO has envelope 0, so infinite). | n/a | Remove once S289 uses CAPRI's ceilings. |
| S305 | cap_reform_2030_scenario | scenarios.py:42 | BISS -30, eco 0.35, AECS +20, set-aside 0.04 | No | None ("Hypothetical") | Delete or keep as a labelled illustrative scenario. |
| S306 | wto_liberalisation_scenario | scenarios.py:59 | tariffs -50%, TRQ +40..150 kt | No | None; CAPRI's WTO files define other rules (falconer.gms, wtoDefra.gms, g20.gms) | Delete or base on a CAPRI file. |

## Numerical, not data (no further work)

S017, S018, S019 (IPOPT tolerances and staging), S023, S028 (outer iteration limits), S031, S032, S035 (price-step and
milk member-state step factors), S041 (ration damping), S042 (fodder ratio bounds; only with `fodder_at_shadow_price`,
off), S050, S051 (young-animal secant and step), S052, S054 (manure pool kappa and omega), S125 (feasibility slack
ladders), S127 (fodder band switch; band width 1e-3 x base use around CAPRI's SUPBAL_ equality), S140 (base-calibration
stall ratio), S144-S148 (N-price and land loop tolerances and limits), S151 (slow-region diagnostic), S153
(fert-dist NLP max_iter), S181 (Anderson memory), S187-S191 (market Newton, damping, clip, iteration limits), S226
(ghg_tax finite difference), S227 (intensity greedy step), S236 (`CAPRI_NLP_CACHE`), S242 (NLP start inside regulation
support, 0.95), S272 (load-time data-validation thresholds), S277 (CAPTRD factor band; only with `--trajectory
captrd`), S278 (trajectory plausibility check: raises an error, it does not substitute a value).

## Mappings and definitions (not numeric proxies)

| id | item | note |
|---|---|---|
| S121 | HISTOSOL_CLASSES | crop -> arable_land, grass -> grassland |
| S202 | compute_indicators PERM | near-duplicate of PERMANENT_LAND_CROPS; reporting |
| S253 | luc CLS | land-class codes |
| S261 | PROCESSING_OUTPUTS | orphan; delete |
| S263 | NUTS2_REGIONS / TRADE_REGIONS | `region_capri_map.csv` exists; consolidate |
| S266 | loader file registry | could become a manifest |
| S270 | CAPRI_PRICE_ALIASES | TWIN -> WINE, OFAR -> OFOD: CAPRI code aliases |
| S271 | rebase code maps | data-rebuild tool |
| S274 | _BLOCK_TARGETS | block -> data key |
| S279 | projection price maps | model -> CAPRI product |
| S283 | income top decile 0.10 | indicator definition |
| S308 | SCENARIO_REGISTRY | name -> constructor |
| S358 | trajectory file map | run-tool option map |

## Uploads relevant to this audit (`/mnt/user-data/uploads`)

- **CAPRI result exports:**
  - `res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv` and .zip (2030 reference dataOut: CEILVAL, D_AREA,
    TOOU, PRME...);
  - `res_2_1730greendeal_refdefaulta.txt` and .zip;
  - `res_2_1730greendeal_refpol_endotech_all_maxdefaulta.zip`;
  - `res_2_1730cap_after_2014_*.zip`;
  - `res_0_1717cap_after_2014_cal_from_data_caldefaulta.csv`;
  - `res_17IT*.txt` and `res_17zip.zip` (2017 CAPREG; the extracted dumps are in `/home/claude/work/capreg/`).
- **Elasticities:**
  - `supply_elas_2_1720{DE,ES,FR,IT,PL}defaulta.txt` and `supply_elas_2_1720REMAINI_NGdefaulta.zip` (the other 21 MS);
  - `elas_2_1717defaulta.csv`, `elas_2_1730defaulta.csv`, `elas1717defaulta_export.xlsx`;
  - `p_elasSupp.txt`, `fao_agg_17_supplyelas.txt`.
- **Market:** `fao_agg_17.txt`, `fao_agg_17_datamarket.txt`, `FAO_agg_17_defaulta.zip`, `market_base_1717.txt`,
  `markmarket_greendeal_1730et_base_1717*.txt`, `data_market_*.csv`, `estnlp-gtap-trade.zip`.
- **Feed and fertiliser:**
  - `feed_export*.zip`, `export_feed_coeff.csv`, `export_anim_req.csv`, `animReq_SK.zip`, `fedcof.gms`;
  - `priFertDist_1730defaulta.zip`, `export_fert_out.csv`;
  - `costsavings_ini_21730_jul15*.zip`, `LitRev*.csv`, `non_changeable_parameters.csv`, `miterra_inputs.csv`,
    `input_manStor.csv`, `nvzShare_LU.csv`, `holdingsLSU.csv`.
- **Other CAPRI inputs:** `land_export.zip`, `capreg.zip`, `coco.zip`, `coco2.zip`, `baseline.zip`, `scen.zip`,
  `scen_greendeal_2030*`, `gd_full.zip`, `capri_export_zip.zip`, `export_DATA2.csv`, `trends_1730.csv`,
  `wintercovershare.gms`, `irrishare.csv`, `cropwat.csv`, `landscape_targets.csv`, `organic_targets*.csv`,
  `tillageCover.csv`, `ccEfa.csv`, `gams.zip` (CAPRI source, extracted to `/home/claude/work/allgms`).
- **Official statistics:** `estat_apri_lrnt_en.csv` (land rents), `tgs00045_page_linear_2_0.csv`,
  `ef_lsk_bovine_*.csv.gz`, NUTS correspondence spreadsheets.

## Hardcoded data recorded in the data sourcing registry (moved here 29 October 2026)

The registry's section `code_embedded_data` (constants in code, not data files) moved here with its log
(docs/KNOWN_ISSUES_REGISTRY_LOG.md). State on 29 October 2026:

| Registry entry | Location named | State |
|---|---|---|
| biofuel conversion coefficients (REALITY_CALIBRATED: standard agronomic yields, mandate calibrated to EU output) | `biofuel/biofuel_module.py` | gone: the module no longer exists (`capri_mod/biofuel/` holds only `__init__.py`); biofuels are CAPRI's market blocks |
| environmental proxy factors (FRAC_GASF, HNV, NH3 shares; IPCC/literature defaults) | `environmental/environmental_module.py` | FRAC_GASF no longer in the code (N losses by CAPRI's cascade, K51); the HNV farmland indicator remains a proxy: permanent grassland plus 0.5 x the area of PULS, SOYA and GRAS (hand-set weight; GRAS counted twice, as grassland and among the "legumes"); reporting only (`compute_biodiversity_indicators`), KNOWN_ISSUES K96 |
