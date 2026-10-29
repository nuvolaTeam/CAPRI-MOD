# Settings inventory (for review before anything moves)

Companion to `SETTINGS_INVENTORY.csv` (427 rows, one per setting, constant, embedded table, scenario preset or CLI flag).
Read-only survey of 23 October 2026. No code was changed. Every `current_location` was resolved against the file by a
script (it matches the quoted token on that exact line). `capri_equivalent` is the code's own citation unless marked
`[v]`, which means I checked the symbol or value by grep in `allgms/gams`. Empty means not identified (not guessed).
Numeric guards (1e-12, 1e-9 and the like), the 44/28 and 17/14 ratios and unit factors are grouped into one row per file.
Inline numbers inside functions are covered for substantive model parameters only.

## Update 27 October 2026: switches whose alternative never ran

A review of the two reference runs (r150 Farm-to-Fork, r151 Green Deal 2030) and the recorded runs since about r100
found no non-default value for any switch or choice setting. With the project lead's decision, the settings whose
other value was an earlier capri-mod form (the "before 24 October" branches of the supply audit, the square-root need
rule, the staged NLP tolerance, the secant young-animal update, the ration's nitrate ingredient, ...) or the model
without a block CAPRI always has (manure techniques, intensities, genetics, dairy block, GL demand, TRQs, LUC, ...)
were removed with the code of their unused value; 19 run options that only mirrored a setting were removed (use
`--set`), and the unwired water and income modules. Kept: CAPRI's own options (manure trade, land market, biofuel
markets, EU blocks, greening, PMP source), the parity switches of the CAPRI-ERROR-FIX corrections, the numerical and
comparison options (price update, stop rule, acceleration, exact Jacobian), `market.market_supply_nq` (fast tests run
without the Hessian), the fodder band rows (removed with the regional-units change, which recomputes the Hessian),
`pmp_cross_terms` "none" (CAPRI's decomposition experiment) and two departures still to be brought to CAPRI's setting
(`use_cattle_member_splits`, K65; `fert_slope_with_saving`, K77). Column `status_27oct` of the CSV marks every removed
row; the rest of this survey is left as written on 23 October.

## Counts
| proposed_home | rows | | module (file) | rows | toml / param / map / scen / cli / keep |
|---|---|---|---|---|---|
| toml | 160 | | supply/* | 129 | 68 / 26 / 18 / 0 / 0 / 17 |
| param_csv | 106 (53 existing rows + 53 new) | | model_parameters.csv | 67 | 14 / 53 / - / - / - / - |
| mapping_csv | 55 | | model.py | 58 | 47 / 1 / 6 / 4 / 0 / 0 |
| cli | 41 | | tools/run/run_f2f_2030.py (+compare_runs) | 46 | 3 / 0 / 0 / 2 / 41 / 0 |
| keep_code | 35 | | market/* | 38 | 17 / 7 / 10 / 2 / 0 / 2 |
| scenario_file | 30 | | policy/* + scenarios/* | 31 | 1 / 5 / 1 / 22 / 0 / 2 |
| | | | environmental, feed, fert, data, projection, utils, other | 58 | 10 / 14 / 20 / 0 / 0 / 14 |

TOML rows by section: supply 62, market 24, outer_loop 23, run 11, young_animals 10, fertiliser 10, projection 8,
diagnostics 7, environment 4, endotech 1 (one row covering 5 keys). The 14 `model_setting` rows of model_parameters.csv
are counted under toml. **Sections I added:** `fertiliser` (inner fertiliser model switches), `environment`
(accounting choices), and `diagnostics` (trace flags and the `CAPRI_*` environment variables).

## Proposed `capri_mod/settings/defaults.toml` skeleton (values = current behaviour)
Compact form: several keys per line separated by `;`. The real file has one key per line. This content was also checked
as one-key-per-line TOML (comments and [v] marks removed): it parses, 153 keys.
```
[run]          base_year="2017" (only 2017 exists); manure_trade=true (use_manure_market; manureTradeNew, star3 GUI on)
               n_workers="auto" (env CAPRI_WORKERS); run_environmental=true; report_biofuel=false; output_root="outputs"
               nlp_cache_size=64 (env CAPRI_NLP_CACHE); hash_seed=0 (PYTHONHASHSEED, launcher sets it)
[outer_loop]   max_outer_iter=25 (CAPRI %STEPS%); outer_tolerance=0.005 (CAPRI p_minIterChg 0.05 %, other metric [v])
               supply_gap_tol=0.005; nbal_update_tol=0.001 (was land_update_tol); base_cal_tol=0.002; manure_pool_tol=0.03
               manure_max_outer_iter=60; manure_extend_min_iter=25; price_relaxation=0.5
               relax_step_down=0.5; relax_floor=0.1; relax_step_up=1.25 (adaptive step, model.py:802-866)
               milk_ms_step="adaptive" ("capri" = define_stepWeights.gms [v]); capri_step_weights=[0.55,0.30,0.15]
               capri_step_weights_late=[0.4,0.3,0.2,0.1]; capri_lowsteps=20 [v]; milk_ms_relax_floor=0.02
               milk_ms_min_share=0.01; sup_gap_min_prod=5.0 (10 x p_minAbsProdIterChg 0.5 [v]); norway_gap_last_iter=15 [v]
               nlp_staged_tol=false; nlp_tol_early=1e-6; nlp_tol_final=1e-8; nlp_tol_switch=4.0
               manure_pool_kappa_bounds=[0.05,1.5]; manure_pool_omega={up=1.25,down=0.5,min=0.25}
               manure_pool_qp_tol=1e-8
[supply]       pmp_source="capri2030" (K61)
               pmp_capri_parts=["crops","animals","feed","land"]; pmp_cross_terms="capri" (p_useCropSpecificQMatrix 0)
               pmp_apply_dampening=true (impose_upper_bound_on_elasticity.gms [v]); pmp_share_term=true
               use_capri_elasticities=true; use_land_market=true (p_landIsFixedinScenario 0 [v])
               land_no_slack=true (LandBalNoSlak_ [v]); land_row_equality=true; surplus_per_current_ha=true (e_SURTOTHa [v])
               use_manure_techs=true
               use_nitrate_in_ration=false; fodder_band=true
               use_livestock_cost_coef=true; amm_fix_without_policy=true; nlp_calibrate=true
               cap_greening=true (permGrasGreening_ [v]); winter_cover_endogenous=true; ni_inside_model=true
               use_grass_intensity=true; use_dairy_intensity=true; use_cattle_intensity=true; use_cattle_member_splits=false
               use_genetics=true; use_option_costsaving_drop=true; use_histosol_fallow=true; use_capri_activity_bounds=true
               absent_activities_fixed=false (CAPRI: true); absent_output_cleared=true; n_relax_sticky=true
               nlp_n_relax=true; jrc_capped_override="" (land_supply_elasticity, land_expansion_cap: removed 23 Oct 2026)
               nbal_tol_abs=0.01; nbal_tol_rel=1e-3; nbal_inner_max=16 (land_inner_max, land_tol: removed)
               nlp_tol=1e-8; nlp_max_iter=3000; nlp_warm_max_iter=200; nlp_acceptable_tol=1e-6; nlp_max_cpu_time=60
               nlp_cal_tol=1e-6; manure_pool_slope=0.05
[market]       biofuel_markets=true (BIOF_M [v]); eu_blocks=false (CAPRI defaultA.agg: two blocks); use_dairy_block=true
               food_demand_gl=true; gl_refit_commitments=true; processing_nq=true; use_region_supply_elas=true
               crush_margin_producer_prices=true; use_trq=true; market_supply_nq=false (calibrate_supply.gms)
               nq_price_shock=0.01; market_structure="bilateral"; acceleration="anderson"; aa_memory=5
               trade_chord=true; max_iter=100; tol=1e-7; step_clip=[0.2,5.0]; damping={min=0.25,down=0.5,up=1.5}
[young_animals] enabled=true (yaniMarket_ [v]); tol=0.005; relaxation=0.7; use_secant=false; use_exact="auto"
               ratio_bounds=[-50,50]; max_step=0.3; small_market_scale=0.1
[endotech]     ghgTechMYld=0.0; ghgTechFEff=0.1; ghgTechLowNFeed=1.0; ghgTechLineNitr=1.0; fixGenetToIni=1.0
                 (= STAR3_DEFAULTS, refpol_endotech_all_sup.gms; the star3/jrc121368 presets go to scenario files)
[projection]   trajectory="capri_ref"; capri_prices=true; calibrate_baseline=true; base_cal_rounds=4
               base_cal_fodder=false; base_cal_stall_ratio=0.95; sim_year=2030 (inner_fert_dist.SIM_YEAR)
               captrd_factor_bounds=[0.2,5.0]; trajectory_factor_bounds=[0.1,10.0]
[fertiliser]   use_fert_allocation=false; use_nutned_always=true; nlp_fertilisation=true
               npk_dual_bound_wide=1000 (CAPRI +-10); exempt_cap_factor=1.0 (CAPRI p_checkSmallMine: 1.0 x baseline for exempted groups); fd_tol=1e-9; fd_max_iter=100
[environment]  luc_model=true; ad_dairy_ch4="fix" ("capri" = as coded); ammapp_sign="consistent" ("capri" = CAPRI's sign)
               luc_ipopt_tol=1e-12; luc_max_iter=500
[diagnostics]  verbose=true; trace_outer=false; slow_region_seconds=60; disable_qp=false; dump_regions=""
               (+ nlp_dump, fd_dump, trace_recal, trace_yani, cal_debug, polish_log from the CAPRI_* env vars)
```

## Unsourced numeric constants (notes contain `unsourced`; ids in the CSV)
- **Proxies that change results:** land fallbacks 200/30/80 kha (S097, 7 sites); default elasticity 0.25 (S064, S132,
  S176, S255); PMP shadow-price proxy (S063); N in animal products 0.25 (S199); raw-milk 0.9575 (S057); FCER price 0.2
  (S211); fert efficiency 1.2 (S213); dairy maintenance x1.1 (S275); Pillar II shares 0.30/0.20/0.08 (S291); BISS 200 and
  UAA 100 (S290); national envelopes (S289); intervention factors (S294); the supply elasticity table outside the
  permanents (S256); LAND_SUPPLY_ELASTICITY and LAND_EXPANSION_CAP (S410, S411).
- **Caps and heuristics:** pesticide loss cap 0.90 (S091); grass row 0.2, fodder headroom 1.15, roughage 1.5/0.1 (S106,
  S123, S124); safety rail (S131); share caps 0.98/0.95 (S165, S177, S192); rho_base 0.05 (S065); share-term floor 0.1
  (S228); manure pool slope (S107); mineral cap x1.1 (S083); land cap fallback 0.15 duplicating the parameter (S149).
- **Numerical loop settings (no economics):** S017-S019, S023, S028, S031, S032, S035, S041, S042, S050-S054, S140,
  S144-S148, S153, S181, S185, S188-S191, S242, S277, S278.

## Unsure how to classify
`grassland_allowance` (scenario vs supply setting, S002); manure pool slope (economic vs numerical, S107); the
`LIVESTOCK_YIELD_TO_TONNE` unit table (mapping vs parameter, S085); `market_structure` (only one valid value; remove?,
S177); `CARRIED_SETTINGS` (S275), which is obsolete once settings are an object; the feed share rules (S205), a keyed
CAPRI table that could be param_csv or its own CSV; `MARKET_SUPPLY_SHOCK` (S039), a CAPRI procedure value I put in
toml.

## Defaults that differ (the settings layer must reproduce current behaviour exactly)
1. **Class duplicates:** `RegionalSupplyModel` declares `use_manure_techs`, `land_no_slack`, `surplus_per_current_ha`
   and `use_manure_pool` as False, while `CAPRIModel` declares True. The model overwrites them at outer iteration 0
   (model.py:607-612), so only a standalone `RegionalSupplyModel` sees the False values.
2. **getattr fallbacks contradict declarations** (harmless today, wrong if the declaration goes):
   - `nlp_staged_tol` falls back to True (model.py:589) and `market_supply_nq` to True (:1027).
   - Many True switches fall back to False, for example `use_land_market`, `use_genetics`,
     `cap_greening`, `ni_inside_model` and `use_*_intensity`.
   - `use_cattle_member_splits` falls back to True at supply_module.py:4337. `pmp_source` falls back to "elasticity".
3. **Hidden switches** (read by getattr, never declared): `milk_ms_step`, `trace_outer`,
   `jrc_capped_override`, `n_relax_sticky`, `nlp_n_relax`, `land_row_equality` and `fodder_band`.
4. **Projection carry-over:** `ProjectionModule.CARRIED_SETTINGS` copies 18 instance attributes plus market
   `use_dairy_block`. Instance changes to anything else are lost in 2030 runs:
   - `--no-gl-demand` (sets `market_module.food_demand_gl`) had no effect in run_f2f_2030: **fixed 23 October 2026**
     (carried with `use_dairy_block`; default runs unchanged, the flag is True in both models).
   - The same loss affects `calibrate_baseline`, `nlp_*`, `milk_ms_step`, `ration_damping` and `use_yani_secant`.
   - The run tool avoids it for `--eu-blocks`, `--cattle-member-splits`, `--yani-pmp-response`, `--nutmin`, `--pmp` and
     `--pmp-parts` by setting **class** attributes. Those then persist for the whole process.
5. **Scenario defaults:** `PolicyScenario.pesticide_rule` is "jrc121368", but `greendeal_scenario()` defaults to
   "star3". `carbon_tax_scenario()` defaults to 100 EUR/t, but the run tool uses 50. Every PolicyScenario carries
   `eco_scheme_budget_pct = 0.25`.
6. **Market iterations:** `run()` passes `market_max_iter = 100`, but `MarketModule.solve()` called alone uses 60.
   `ConvergenceTracker` defaults (0.001/50) are always overridden.
7. **Run tool:** `max_outer_iter = 25` is raised to 60 with manure trade on. F2F has manure trade off, so it keeps 25.
8. **No-op flags:** `--feed-in-supply`, `--land-no-slack`, `--surplus-per-ha`, `--surplus-current-ha`, `--young-animals`,
   `--dairy-block` and `--no-market-nq` change nothing. The `--no-dairy-block` help text says "(the default)", but the
   default is on.

## Other findings
- **Duplicated maps:** the country -> CAPRI member-state map exists in 9 copies. `POOL_OF_PREFIX` and ration.py:170
  have no GR->EL. One CSV could replace them, derived from `region_capri_map.csv`.
- **Duplicated constants:**
  - FracGASF 0.10 is hard-coded 6 times.
  - 55.65 (environmental_module.py:274) duplicates the `MJ_PER_KG_CH4` parameter.
  - `ENDO_MAN_AV_SLOPE` and the CAPRI bounds 0.999/300/0.2 [v] appear in both environmental_module and fert/npk.
  - `WINTERCOV` 0.35 appears twice.
- **CAPRI values not cited in the code but verified:** relSubs 1.2/0.8/0.2 (S101), rhoArm defaults 8/10 (S183).
- **Orphans:** `capri_reference.py` (15 tables, no importer); `definitions.BASE_YEAR = 2012` (wrong), `PROJECTION_YEARS`
  and `PROCESSING_OUTPUTS`; `NTM_AVE_PCT`; `calibrate_demand_elasticities`; ARMINGTON_PREMIUM_LO/HI and
  MIN_TRADE_SHARE_FOR_PREMIUM (`_net_ratio_premium` is never called).
- **Departures from CAPRI to confirm in toml comments:** market_supply_nq off, eu_blocks off, fodder_at_shadow_price off,
  absent_activities_fixed off, ammapp_sign "consistent", ad_dairy_ch4 "fix".
- **Conflict with the design:** the params.py docstring says solver tolerances stay in code. The agreed design moves
  them to toml.
