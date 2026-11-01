# Refactor stage 3, second half: the supply's parameters and state objects (plan)

Plan only, for the project lead's review; nothing in the repository was changed. Written 1-2 November 2026 on branch
k79-amm-resolve at HEAD cfbf746 (worktree /home/claude/work/wt_k79). Line numbers are those of that HEAD and will move.
Naming: ARCHITECTURE_REFACTOR's table has stages 3a and 3b done (the mixins, the data adapter); this second half is called 3c below.

Sources read: docs/design/ARCHITECTURE_REFACTOR.md (sections 1-3), docs/design/MARKET_STATE_INVENTORY.md,
capri_mod/market/state.py and capri_mod/tests/test_market_layers.py (stage 2b), capri_mod/supply/*.py,
capri_mod/coupling/hessian.py, the coupling's and model.py's uses of the supply objects, capri_data/schema/03_code_data.sql
and 04_code_data_status.sql, docs/design/HARDCODED_TABLES.md, capri_data/shared/model_parameters.csv,
capri_mod/params.py, capri_mod/settings/defaults.toml.

Method. The inventory comes from an AST scan of the class bodies of RegionalSupplyModel (supply_module.py) and its six
block mixins (livestock, fertilisation, abatement, policy, land, nlp), and of SupplyModule: every `self.X = ...`,
augmented assignment, `setattr(self, "X")`, `self.__dict__["X"]` / `.setdefault("X")` / `.pop("X")`, every in-place
mutation (`self.X[k] = ...`, `self.X.update(...)`), and every read (`self.X`, `getattr(self, "X", ...)`,
`self.__dict__.get("X")`, `"X" in self.__dict__`). A second scan finds the same names in the rest of capri_mod
(coupling, model.py, environmental, income, projection), in the tests and in tools. The classification of each
attribute was made by reading the code at the write and read sites.

Marking. **[verified]** = read in the code at the lines cited; **[inferred]** = my reading of lifetimes or effects, not
checked by running the model (no tests or model runs: a test suite was running on this 2-core machine; only
read-only AST and grep scans, and make_code_data.py --check).

## 0. Summary

- **186 instance attributes** are set outside `__init__`: 148 on RegionalSupplyModel (131 by its own methods, 17 by
  SupplyModule or the coupling on the regional models), 38 on SupplyModule (23 by itself, 15 by CAPRIModel). Three more
  names are read with a getattr default and never written anywhere. Class-level attributes: 33 on
  RegionalSupplyModel, 20 on SupplyModule (section 1.4).
- By kind (RegionalSupplyModel / SupplyModule): per-base parameters 30 / 9; state carried between solves 9 / 6;
  working state rebuilt in every solve and passed between blocks 46 / 0; results and diagnostics 49 / 6; inputs set from
  outside before a solve 13 / 17; settings held per instance 1 / 0.
- Proposed objects, consistent with the market's state.py: per regional model `par`, `sv`, `ev`, `seen` and one more,
  `res` (the last solve's outputs and diagnostics, which the market does not need); per SupplyModule `par`, `sv`,
  `seen`, `res`. One departure from the market's form is proposed (section 3.2): slot classes in which an unset field is
  absent, as an unset attribute is today, instead of dataclass fields defaulting to None.
- 15 commits that move state (3 preparatory, 1 removal of write-only attributes, 8 block moves, 2 for
  SupplyModule, 1 documentation) and 7 commits that move numbers and code tables, gated in 6 batches. Effort: an estimate of
  7-10 working days (section 5).
- Main risks: the Hessian's restore and the workers' return copy state by attribute name, through `__dict__`, which
  bypasses any guard; 351 `getattr(self, ...)` calls in the seven supply files, most with defaults, can hide a moved
  or missing name; `hasattr` and identity tests whose result would change if absent fields got a None default; the test
  that compares one and two workers to the last digit does not fork (sections 1.3, 4.3).

## 1. Inventory

### 1.1 Classes used

The task's four classes, with (b) split in two and the inputs from outside kept apart (they are the market's `seen`):

| class | meaning | analogue in stage 2b |
|---|---|---|
| a | per-base parameter: built once per base or calibration, including what the first solves calibrate lazily (the split columns' linear terms from the duals, CAPRI's NLP calibration) and memos of base data | MarketParameters (par) |
| b1 | state carried between solves or outer iterations: warm starts, linearisation points, kept relaxations, the N-price loop | MarketSolveState (sv) |
| b2 | working state of one solve: rebuilt (or reset) in every solve, written by one block and read by another later in the same solve | MarketEvalState (ev) |
| c | per-run result or diagnostic: read after the solve (by SupplyModule, the coupling, reports, tests) or never read | (returned values) |
| e | inputs set from outside before a solve: by SupplyModule on each regional model, or by CAPRIModel on SupplyModule | MarketSeen (seen) |
| d | setting or class constant | (class attributes) |

The list `RegionalSupplyModel.SOLVE_STATE` (supply_module.py:516-521; 32 names, found on 27 October 2026 by comparing
a model's attributes before and after a solve) is not the set of b1: it holds every attribute a solve *changes*, so
it mixes b1 (`_amm_last`, `_wc_solved`), b2 (`_price_shock_now`, `_ghg_nr_obj`, `_last_req_duals`), c (`_last_land`,
`_npk_cov`, write-only) and one input (`feed_rations`). Conversely two b1 attributes are not in it and do not start
with `_nlp` (section 1.3). [verified]

### 1.2 Counts per block

Block = the file of the methods that write the attribute (the core is RegionalSupplyModel's own methods in
supply_module.py: net revenues, constraints, the solve flow). The full list with the writes and reads (file:line) is in
Appendix A.

| block | a | b1 | b2 | c | e | d | total |
|---|---|---|---|---|---|---|---|
| core | 5 |  | 8 | 11 |  |  | 24 |
| livestock | 11 |  | 5 | 3 | 5 |  | 24 |
| fertilisation | 6 | 1 | 2 | 4 |  | 1 | 14 |
| land |  |  | 12 | 6 | 2 |  | 20 |
| abatement | 2 | 1 | 9 | 4 | 5 |  | 21 |
| policy | 2 |  | 3 |  |  |  | 5 |
| nlp | 4 | 7 | 7 | 21 | 1 |  | 40 |
| **RegionalSupplyModel** | 30 | 9 | 46 | 49 | 13 | 1 | 148 |
| **SupplyModule** | 9 | 6 |  | 6 | 17 |  | 38 |

Notes on the counts. "core" holds the PMP terms' working copies: `f`, `net_revenues`, `premiums` (class a) are set in
`__init__` and changed later (`f` by SupplyModule.calibrate_to_base, supply_module.py:2518; `net_revenues` mutated by
the blocks inside every solve and restored at its end, 1494 and 1525), so they are in the count; `Q`, `data`, `acts`,
`n`, `rid`, `_gross_rev`, `n_capri_pmp_acts`, `supply_elasticities` are only set in `__init__` and are not. The PMP
calibration itself (PMPCalibrator, capri_pmp.py) keeps no state on the regional model beyond `Q` and `f`. [verified]

### 1.3 Findings of the inventory (each is a risk for the moves; none is fixed by this plan's moves)

1. **Two carried states are outside the Hessian's restore.** `_n_relax_sticky` (fertilisation.py:818,
   supply_module.py:1709; read at 1683 before any write in the solve: the relaxed N target "once found in this
   scenario") and `_ghg_applied` (abatement.py:495) are neither in SOLVE_STATE nor named `_nlp*`, so the market
   supply Hessian (hessian.py:187-211) does not restore them between price shocks. [verified] Effect today: none
   expected, because the Hessian is measured at a baseline (no N target, `_n_relax_key` None) and `_ghg_applied` acts
   only within one solve (`_ghg_nr_obj is self.net_revenues` is false in the next solve, since `net_revenues` is a new
   object after each `_solve_once`). [inferred] With `market.hessian_scenario_iter` > 0 (a measurement at the
   scenario's state) the first could matter.
2. **The restore copies field by field, by name, through `__dict__`.** `_snapshot` deep-copies each attribute on its
   own (hessian.py:193-195) and `_restore` deletes the state attributes absent from the snapshot and writes the others
   back (204-206). With `market.hessian_skip_unchanged = false` only the `_nlp*` names are saved, by shallow copy
   (188-189, 193). [verified] Consequences for the moves: (i) the set of restored values is defined by a name prefix
   that the moves remove (`_nlp_prev` becomes `sv.nlp_prev`); (ii) deep-copying a whole state object at once would
   share sub-objects between fields that today are copied apart (deepcopy's memo), so a restore of whole objects is not
   a pure move; (iii) `__dict__` writes bypass any `__getattr__`/`__setattr__` guard.
3. **The `_nlp*` set restored today holds 27 names of four classes**: the calibration (`_nlp_cal`, `_nlp_base_alloc`,
   `_nlp_cal_store`: a), the warm starts (`_nlp_prev`, `_nlp_prev_f`, `_nlp_y`, `_nlp_cols`, `_nlp_relax_keep`: b1),
   flags of one solve (b2) and diagnostics (`_nlp_fallback_log`, `_nlp_path`, ...: c). A shock's fallback entries are
   thus discarded with the restore. [verified]
4. **What crosses the fork.** Workers are forked per `_solve_regions` call (supply_module.py:3191); each returns its
   result, the whole regional model pickled (minus the shared `_env_for_surplus`, 3286), the region's entries of
   `_PAR_STATE` (`_nbal_state`, `_nbal_bracket`, `_nbal_prev`, 3136, 3287) and the new entries of `_PAR_CACHES`
   (`_mctx_cache`, `_balance_cache`, `_mcap_cache`, `_hess_fp`, `_hess_verify`, 3137, 3288). [verified] So every
   regional model's state travels automatically (it is pickled with the model), while a SupplyModule attribute written
   in a worker and not listed is lost: today `_inner_fert` (a lazy InnerFertDist, 2633-2635), harmless because it is
   rebuilt. [verified for the code path; harmlessness inferred] Class-level state (`nlp_tol`, `use_fert_allocation`,
   `use_manure_pool`, set on the class by model.py:580, 590-591 and hessian.py:41) reaches the workers by fork only.
5. **The parallel test does not fork.** test_parallel_regional_solves_match_sequential (test_capri.py:2622) runs two
   regions with `n_workers` 1 and 2, but `workers(2)` is `max(1, min(2, 2 - 1)) = 1` (supply_module.py:3151), so both
   runs are serial (3169). [verified by reading; not run] test_dead_worker_does_not_hang_the_regional_solves
   (test_capri.py:3998) does fork (4 regions, 2 workers) but compares activities to 1e-6 after one iteration, with a
   worker killed. The mini-EU run (20 units, `run.n_workers = 0`: the machine's cores) forks.
6. **`hasattr` and identity tests.** `run()` resets the N-price state only `if price_signals is None or not
   hasattr(self, "_nbal_state")` (2776); `_apply_ghg_tax` tests `_ghg_nr_obj is self.net_revenues` (abatement.py:492);
   `_base_levels_cache` is keyed on `id()` of two data frames (supply_module.py:677); the regional feed block's cache
   is keyed on the identity of the rations dicts (coupling/feed.py:70-73, comment). [verified] A field defaulting to
   None makes `hasattr` always true; a copy breaks an identity key.
7. **Reads that always take their default.** `_dairy_yield_base` (supply_module.py:1846), `_last_aug_cols` (nlp.py:19)
   and `region` (policy.py:270) are read with getattr defaults and written nowhere in capri_mod or tools. [verified by
   grep]
8. **12 write-only attributes** (never read by the model, coupling, reports or tools; tests read two): `_last_land`,
   `_last_aug_A`, `_last_aug_b` (tests), `_mineral_row_m`, `_last_plain` (read only by run_f2f_2030.py's optional
   CAPRI_DUMP_REGIONS dump, l. 456), `_fert_inside_weight`, `_nlp_abatement`, `_npk_cov`, `_nlp_group_caps`,
   `_manure_ni_share`, `_last_feed`, `_nlp_times`; on SupplyModule `_base_cal_drift`. Nine of them are restored by the
   Hessian for nothing (six in SOLVE_STATE, three named `_nlp*`; `_nlp_times` only when the skip mode is off). [verified by grep]
9. **An instance copy shadows a class switch.** `_fert_params_raw` sets `self.use_fert_allocation = True` and back to
   the old value (fertilisation.py:758-763), which leaves an instance attribute; model.py:590 later sets the switch on
   the class, which no longer reaches that instance. Inert today (the only value ever set is False, the class
   default). [verified]
10. **SupplyModule is used as storage by the coupling.** `yani_price_ratio_m` is written by CAPRIModel
    (model.py:540, coupling/young_animals.py:260) and the Hessian, and read only by the coupling, never by
    SupplyModule. [verified]
11. **Module-level state** outside the two classes, not in this inventory: capri_regional_nlp's `_SOLVERS` (IPOPT
    solver cache, l. 53; a kept solver solves "to the same point within IPOPT's tolerance, not to the last digit",
    test_capri.py comment at 2645-2648), `KKT_MODE`, `SOLVE_PROBE` (the Hessian's switches), `CACHE_STATS`; the data
    caches `ammonia_techs._CACHE`/`_CD`, `n_cascade._NZ`/`_DATA`, `n_leaching._REG`. [verified that they exist; their
    keys not checked] They stay as they are in this stage (proposal: stage 4's coupling objects or a later step).

### 1.4 Class-level attributes (class d)

RegionalSupplyModel (33, supply_module.py:516-990): 11 settings read through `setting(...)` (nlp_warm_check,
nlp_jump_check, nlp_jump_gain, use_land_market, grassland_allowance, yani_exact_response, cap_greening,
greendeal_inputs_keep_tech_change, organic_topup_at_fuel_cost, absent_activities_fixed, use_cattle_member_splits); 3
class attributes changed as run state (`nlp_tol` 590, `use_fert_allocation` 945, `use_manure_pool` 948); 2 class
defaults of per-instance inputs (`yani_price_ratio` 559, `_manure_ctx` 951); 3 declared parameters read with
`param()` at import (NITR_N_EXCR 933, ORGANIC_BASELINE_SHARE 903, PESTICIDE_YIELD_LOSS_AT_50PCT 915); 2 CAPRI constants
written as numbers (ORGANIC_SMALL_MINE_KG_HA 583, ORGANIC_LIMCRES_FACTOR 585); 2 input columns read through the
adapter (FEED_CEREAL_MIX 694, FERT_COST_SHARE 929); 9 code tables (CROPDIV_GROUPS 576, ORGANIC_CROPS 864,
ORGANIC_CROP_TARGET 870, ORGANIC_YIELD_GAP_CROPS 877, PERMANENT_LAND_CROPS 907, PESTICIDE_AFFECTED 924, LAND_TYPES 937,
CATTLE_SPLIT_MEMBERS 972, HISTOSOL_CLASSES 987); SOLVE_STATE. The six mixins define no class attributes. [verified]

SupplyModule (20): 12 settings (pmp_source 2027, pmp_capri_parts 2030, use_land_market, grassland_allowance,
jrc_capped_override 2034, fert_slope_with_saving 2414, BASE_CAL_ROUNDS 2465, NBAL_TOL_ABS, NBAL_TOL_REL, NBAL_INNER_MAX
2665-2668, SLOW_REGION_SECONDS 2800, n_workers 3134 with run_state); 3 declared parameters (JRC_CAPPED_N_REGIONS,
JRC_CAPPED_CUT 2039-2040, FERT_EFF_COR 2310); 3 code tables (ACTIVITY_PRICE_SOURCE 2720, EU_POLICY_KEYS 2659,
FODDER_ACTS 2467); `_PAR_STATE`, `_PAR_CACHES`. [verified]

## 2. The numbers in the supply code

### 2.1 The census's rows for the supply files

03_code_data.sql is up to date with the code (`tools/check/make_code_data.py --check`: "up to date", run read-only).
It has 56 rows for capri_mod/supply/, all classified in 04_code_data_status.sql, all with action "keep" today:

| status | rows | proposed destination |
|---|---|---|
| capri | 22 | the declared parameters file, with the GAMS citation already in 04 |
| physical | 13 (the 44/28 mass ratio in 6 functions; MJ per Mcal) | the declared parameters file, kind physical, as agreed on 31 October (but see question Q5) |
| literature | 4 (JRC121368's tiered surplus rule: 0.25, 0.75, 50, 150) | the declared parameters file, kind jrc121368, or the scenario's files in stage 5 (Q10) |
| numerical | 8 | settings (defaults.toml), except one used only by tests |
| technical | 9 | settings (cache sizes, progress print) or kept (the 2017/2030 market-year selectors) |

Row by row (file:line from 03; source and note from 04):

| where | scope | value | status | source | note | destination |
|---|---|---|---|---|---|---|
| abatement.py:198 | AbatementBlock._cover_crop_requirement | 13.0 | capri | gams/pol_input/greendeal/load_organic_targets.gms l. 175, 183 | (orgTarg - 12) / (25 - 12): 13 = 25 - 12 | parameters |
| abatement.py:383 | AbatementBlock._manure_inhibitor_params | 0.9 | capri | gams/envind/ghgMiti.gms l. 110-115 | inhibitor emission factor 0.9 x NOC, copied to N2OMAN | parameters |
| abatement.py:406 | AbatementBlock._manure_inhibitor_params | 1.2 | capri | gams/envind/ghgMiti.gms l. 885-887 | relSubs1 of the nitrification inhibitor | parameters |
| abatement.py:406,406 | AbatementBlock._manure_inhibitor_params | 0.2 | capri | gams/envind/ghgMiti.gms l. 904-906 | relSubs0 of the nitrification inhibitor | parameters |
| fertilisation.py:386 | FertilisationBlock._npk_organic_cap | 0.25 | capri | gams/supply/set_fert_priors.gms l. 302-306 | regulation accuracy | parameters |
| fertilisation.py:386 | FertilisationBlock._npk_organic_cap | 0.75 | capri | gams/supply/set_fert_priors.gms l. 297-299 | regulation mode share | parameters |
| fertilisation.py:451 | FertilisationBlock._npk_mineral_cap | 0.25 | capri | gams/supply/set_fert_priors.gms l. 302-306 | regulation accuracy | parameters |
| fertilisation.py:451 | FertilisationBlock._npk_mineral_cap | 0.75 | capri | gams/supply/set_fert_priors.gms l. 297-299 | regulation mode share | parameters |
| livestock.py:429 | LivestockBlock._genetics_columns | 0.2 | capri | gams/envind/breeding.gms l. 452 | pmpParsqr floor 0.2 x costParLin of the breeding options, where the data give no gamma_flo | parameters |
| n_cascade.py:189 | WINTERCOV_NO3 | 0.35 | capri | gams/envind/cover_crops.gms l. 400-402 | winter cover's reduction of runoff and leaching; duplicate of n_leaching.WINTERCOV_NO3LEA | parameters |
| n_leaching.py:38 | EF5 | 0.0075 | capri | gams/envind/create_rawdat_gascoeff_gdx.gms l. 713 | leaching/runoff N2O factor EF5 (also IPCC 2006 vol. 4 table 11.3) | parameters |
| n_leaching.py:39 | WINTERCOV_NO3LEA | 0.35 | capri | gams/envind/cover_crops.gms l. 402 | winter cover's reduction of the leaching factor | parameters |
| policy.py:285 | PolicyBlock._organic_target_scale | 25.0 | capri | gams/pol_input/greendeal/load_organic_targets.gms l. 175, 183 | organic target scaling (orgTarg - 12) / (25 - 12) | parameters |
| policy.py:327 | PolicyBlock._greendeal_tech_progress | 0.005 | capri | gams/capmod/define_inputs.gms l. 64-66 | 0.5% input-saving progress per year | parameters |
| policy.py:420 | PolicyBlock._apply_yield_input_costs | 1.5 | capri | gams/capmod/define_inputs.gms l. 102 | yield growth bounded to [0.5, 1.5] in the input cost adjustment | parameters |
| policy.py:459 | PolicyBlock._organic_converted | 25.0 | capri | gams/pol_input/greendeal/load_organic_targets.gms l. 175, 183 | organic target scaling (orgTarg - 12) / (25 - 12) | parameters |
| supply_module.py:2364 | SupplyModule._fert_techs | 0.9 | capri | gams/envind/ghgMiti.gms l. 110-111 | inhibitor emission factor 0.9 x NOC | parameters |
| supply_module.py:2396 | SupplyModule._fert_techs | 0.2 | capri | gams/envind/ghgMiti.gms l. 904-906 | relSubs0 of the fertiliser options | parameters |
| supply_module.py:2396 | SupplyModule._fert_techs | 0.8 | capri | gams/envind/ghgMiti.gms l. 891-898 | relSubs1 where maxShare < 1 (CAPRI also requires an NMIN/NMAN effect of the option) | parameters |
| supply_module.py:2396 | SupplyModule._fert_techs | 1.2 | capri | gams/envind/ghgMiti.gms l. 885-887 | relSubs1 of the fertiliser options | parameters |
| supply_module.py:583 | RegionalSupplyModel.ORGANIC_SMALL_MINE_KG_HA | 10.0 | capri | gams/pol_input/greendeal/organic_minfert_redu.gms l. 51 | 0.01 t/ha = 10 kg/ha small-mineral-N threshold | parameters |
| supply_module.py:585 | RegionalSupplyModel.ORGANIC_LIMCRES_FACTOR | 1.2 | capri | gams/pol_input/greendeal/organic_minfert_redu.gms l. 116 | limCres maximum 1.2 x baseline residues per ha | parameters |
| fertilisation.py:628 | FertilisationBlock.tiered_surplus_target | 0.25 | literature | JRC121368 tiered surplus rule (sect. 4.3.4 as cited in policy_module.py) | 25% cut on the first 50 kg N/ha | parameters (jrc121368; scenario in stage 5?) |
| fertilisation.py:628,628 | FertilisationBlock.tiered_surplus_target | 50.0 | literature | JRC121368 tiered surplus rule (sect. 4.3.4 as cited in policy_module.py) | tier bounds 50 and 100 kg N/ha | parameters (jrc121368; scenario in stage 5?) |
| fertilisation.py:629 | FertilisationBlock.tiered_surplus_target | 0.75 | literature | JRC121368 tiered surplus rule (sect. 4.3.4 as cited in policy_module.py) | 75% cut on 100-150 kg N/ha | parameters (jrc121368; scenario in stage 5?) |
| fertilisation.py:629,629 | FertilisationBlock.tiered_surplus_target | 150.0 | literature | JRC121368 tiered surplus rule (sect. 4.3.4 as cited in policy_module.py) | tier bound 150 kg N/ha | parameters (jrc121368; scenario in stage 5?) |
| capri_pmp.py:95 | <module> | 30.0 | numerical |  | data-check threshold of detect_synthetic_base_activities, used only in tests (PROXY_AUDIT  | into its test (used only by tests) |
| capri_regional_nlp.py:1053 | CapriRegionalNLP.calibrate | 5000.0 | numerical |  | lsq_linear iteration limit | settings |
| capri_regional_nlp.py:1138 | CapriRegionalNLP.fert_at | 3000.0 | numerical |  | IPOPT iteration limit of the fertilisation-block sub-solve (same value as supply.nlp_max_i | settings |
| capri_regional_nlp.py:1171 | CapriRegionalNLP | 0.95 | numerical |  | IPOPT start moved inside the regulation support (PROXY_AUDIT S242) | settings |
| capri_regional_nlp.py:62 | CAL_RIDGE | 1e-10 | numerical |  | ridge weight of the calibration's multiplier fit | settings |
| capri_regional_nlp.py:685 | CapriRegionalNLP._fert_block | 0.999 | numerical |  | keeps regulated flows strictly inside the beta-density support (CAPRI: open support (0, pr | settings |
| policy.py:177 | PolicyBlock.apply_pesticide_reduction | 0.99 | numerical |  | organic share capped at 99% so the conventional share stays positive | settings |
| supply_module.py:60 | ABSENT_LEVEL | 1e-08 | numerical |  | level at or below which an activity counts as absent (CAPRI: no p_technFact) | settings |
| abatement.py:134 | AbatementBlock._nlp_tax_terms | 28.0 | physical |  | N2O/N2O-N mass ratio 44/28 | parameters (physical) - see Q5 |
| abatement.py:134 | AbatementBlock._nlp_tax_terms | 44.0 | physical |  | N2O/N2O-N mass ratio 44/28 | parameters (physical) - see Q5 |
| abatement.py:450 | AbatementBlock._manure_inhibitor_tax_value | 28.0 | physical |  | N2O/N2O-N mass ratio 44/28 | parameters (physical) - see Q5 |
| abatement.py:450 | AbatementBlock._manure_inhibitor_tax_value | 44.0 | physical |  | N2O/N2O-N mass ratio 44/28 | parameters (physical) - see Q5 |
| fertilisation.py:128 | FertilisationBlock._fert_tax_terms | 28.0 | physical |  | N2O/N2O-N mass ratio 44/28 | parameters (physical) - see Q5 |
| fertilisation.py:128 | FertilisationBlock._fert_tax_terms | 44.0 | physical |  | N2O/N2O-N mass ratio 44/28 | parameters (physical) - see Q5 |
| fertilisation.py:32 | FertilisationBlock._ef_mineral_n2o | 28.0 | physical |  | N2O/N2O-N mass ratio 44/28 | parameters (physical) - see Q5 |
| fertilisation.py:32 | FertilisationBlock._ef_mineral_n2o | 44.0 | physical |  | N2O/N2O-N mass ratio 44/28 | parameters (physical) - see Q5 |
| fertilisation.py:67 | FertilisationBlock._ef_mineral_lea | 28.0 | physical |  | N2O/N2O-N mass ratio 44/28 | parameters (physical) - see Q5 |
| fertilisation.py:67 | FertilisationBlock._ef_mineral_lea | 44.0 | physical |  | N2O/N2O-N mass ratio 44/28 | parameters (physical) - see Q5 |
| fertilisation.py:75 | FertilisationBlock._ef_nh3_n2o | 28.0 | physical |  | N2O/N2O-N mass ratio 44/28 | parameters (physical) - see Q5 |
| fertilisation.py:75 | FertilisationBlock._ef_nh3_n2o | 44.0 | physical |  | N2O/N2O-N mass ratio 44/28 | parameters (physical) - see Q5 |
| ghg_tax.py:42 | MJ_PER_MCAL | 4.1868 | physical |  | MJ per Mcal | parameters (physical) - see Q5 |
| capri_regional_nlp.py:1311 | CapriRegionalNLP.response | 16.0 | technical |  | cache size of sensitivity factorisations | settings |
| capri_regional_nlp.py:1389 | CapriRegionalNLP.kkt_step | 16.0 | technical |  | cache size of KKT factorisations | settings |
| supply_module.py:2127,2127,2133 | SupplyModule._pmp_terms_for | 2017.0 | technical |  | market-year switch choosing the 2030 data variant | keep (a data-variant selector) |
| supply_module.py:2128 | SupplyModule._pmp_terms_for | 2030.0 | technical |  | market-year switch choosing the 2030 data variant | keep (a data-variant selector) |
| supply_module.py:2145,2145 | SupplyModule._intensity_q_at | 2017.0 | technical |  | market-year switch choosing the 2030 data variant | keep (a data-variant selector) |
| supply_module.py:2146 | SupplyModule._intensity_q_at | 2030.0 | technical |  | market-year switch choosing the 2030 data variant | keep (a data-variant selector) |
| supply_module.py:2291 | SupplyModule._build_region_data | 2030.0 | technical |  | market-year switch choosing the 2030 data variant | keep (a data-variant selector) |
| supply_module.py:2291,2291,2298,2298 | SupplyModule._build_region_data | 2017.0 | technical |  | market-year switch choosing the 2030 data variant | keep (a data-variant selector) |
| supply_module.py:2783 | SupplyModule.run | 50.0 | technical |  | progress print every 50 regions | settings |

Duplicates to merge into one parameter each: CAPRI's relSubs0 0.2 / relSubs1 1.2 and the inhibitor factor 0.9
(ghgMiti.gms) in both SupplyModule._fert_techs and AbatementBlock._manure_inhibitor_params; winter cover's 0.35
(cover_crops.gms) in n_cascade.py and n_leaching.py; the organic-target scaling 25 (and 13 = 25 - 12) in
policy.py twice and abatement.py once; the regulation accuracy 0.25 and mode share 0.75 (set_fert_priors.gms) in
`_npk_mineral_cap` and `_npk_organic_cap`. ORGANIC_SMALL_MINE_KG_HA (10, organic_minfert_redu.gms) and
model_parameters.csv's SMALL_MINE_KG_HA (30, minfert_redu_by_crop.gms) are different CAPRI parameters, not duplicates;
the same for the two LIMCRES factors (1.2 and 1.3). [verified in the files cited]

### 2.2 What the census does not list

make_code_data.py leaves out 0, 1, -1, 0.5, the integers up to 12, powers of ten and numbers in range(), round() or a
message (its docstring, l. 13-19). In the supply files that filter drops 85 occurrences of 0.5 or of an integer from 2
to 12 outside subscripts (my scan; most are indices, tuple lengths, exponents). Read by hand, at least these are model
constants, unclassified: [verified that the numbers stand there; the sources are inferred unless cited in the code]

| where | value | what it is |
|---|---|---|
| fertilisation.py:347 | 10.0 | getattr default of `_npk_dual_bound`: CAPRI's bound on the inner model's duals (set_fert_priors.gms, per the comment at nlp.py:195-196), a parameter hidden in a default |
| fertilisation.py:409-410 | 10.0, 2.0 | the crop residues' regulation c1 = 10 / f + 1 (source not cited) |
| fertilisation.py:628 | 0.50 | JRC121368's tiered rule, the 50-100 kg tier (its neighbours 0.25 and 0.75 are in the census) |
| policy.py:420 | 0.5 | lower bound of the yield growth (define_inputs.gms l. 102; the census has the upper bound 1.5) |
| policy.py:148 | 0.50 | the 50% pesticide cut at which PESTICIDE_YIELD_LOSS_AT_50PCT is defined |
| policy.py:285, 459; abatement.py:198 | 12.0 | the organic-target scaling's lower end (load_organic_targets.gms l. 175, 183; the census has 25 and 13) |
| abatement.py:200 | 0.5, 0.5 | weights of the catch-crop requirement (organic share and the rest; source not cited) |
| supply_module.py:2892 | 0.5 | the default surplus cut when the scenario gives none (50%, the Farm-to-Fork's surpRedu; inferred): a scenario parameter |
| supply_module.py:1396 | 10.0, 0.1, 100.0 | bounds of a land row's limit (source not cited) |
| fertilisation.py:711, 719, 731 | 60 | bisection iterations (numerical: settings) |

Proposal: before the number commits, one read-only pass over these supply files without the filter, each number
classified by hand in 04 (Q7). The 116 CAPRI constants of 31 October are a lower bound.

### 2.3 The declared parameters file and the adapter

The declared parameters file exists: capri_data/shared/model_parameters.csv (38 rows: name, key, value, unit, kind,
source, used_in), read by capri_mod/params.py. The supply code reads 11 of its parameters with `param()`, at import, into
module or class constants (capri_pmp.py:47-61 ELAS_HIGH, ELAS_CAP, SHARE_COEF; ghg_tax.py:43 MJ_PER_KG_CH4;
supply_module.py:64, 88, 903, 915, 933, 2039, 2040). params.py reads a fixed path next to the package
(`FILE = .../capri_data/shared/model_parameters.csv`, params.py:19), not the run's data directory: it is outside the
data adapter (capri_mod/data/inputs.py, RunInputs), which follows `data_dir` and the base year. [verified]

Proposal (consistent with ARCHITECTURE_REFACTOR section 3, "read through the data adapters into the parameter
objects"): extend model_parameters.csv rather than add a second file; RunInputs gets a `parameters()` reader of
`<data_dir>/shared/model_parameters.csv`; the supply's values are read when SupplyModule builds its parameters (or the
regional model's `par`), not at import. For a run on capri_data the values are the same, so the move is checked by an
identical run; for a run on another data directory it is a behaviour change (it would read that directory's file), to
be confirmed (Q6). The test that the file and the code agree (test_capri.py:2763) is adapted.

Settings: the numerical and technical numbers go to capri_mod/settings/defaults.toml under [supply] (solver ones) or
[diagnostics] (the progress print every 50 regions, supply_module.py:2783). Two remarks: capri_regional_nlp.CAL_RIDGE
enters the market supply Hessian's cache key (hessian.py:114-115), so the setting's value must be read there too; the
fertilisation sub-solve's 3000 iterations (capri_regional_nlp.py:1138) are "the same value as supply.nlp_max_iter"
(04): it should read that setting, not get a new one.

### 2.4 Code tables (HARDCODED_TABLES.md H2-H4) in the supply files

| table | where | likely source (to be checked against CAPRI's sets) |
|---|---|---|
| CROPDIV_GROUPS | supply_module.py:576 | sets.gms annualCrops / cropDivGrps (comment at 574-575) |
| ORGANIC_CROPS, ORGANIC_CROP_TARGET, ORGANIC_YIELD_GAP_CROPS | supply_module.py:864, 870, 877 | load_organic_targets.gms, load_organic_yieldgap.gms |
| PERMANENT_LAND_CROPS | supply_module.py:907 | one of the five copies of the permanent crops (HARDCODED_TABLES) |
| PESTICIDE_AFFECTED | supply_module.py:924 | derived from CROPS minus four codes |
| LAND_TYPES, HISTOSOL_CLASSES | supply_module.py:937, 987 | CAPRI's land types (11 copies of ARAC/GRAS/FRUN) |
| CATTLE_SPLIT_MEMBERS | supply_module.py:972 | the model's cattle activities and CAPRI's members |
| FIXED_ACTIVITIES | supply_module.py:56 | model classification |
| ACTIVITY_PRICE_SOURCE, FODDER_ACTS | supply_module.py:2720, 2467 | animal -> product (one of three copies, with capri_pmp.LIVESTOCK_PRODUCT and coupling/bridge.py's inverse) |
| ARABLE_ACTIVITIES, LIVESTOCK_PRODUCT, LIVESTOCK_YOUNG, COUNTRY_ELAS_ALIASES, ACTIVITY_ALIASES | capri_pmp.py:89-141 | crosswalks |
| HOUS_TECHS, STOR_TECHS, RUNH_TECHS, APPL_TECHS; APPL | n_cascade.py:31-36; n_leaching.py:42 | CAPRI's ammonia technology sets (ghgMiti / the MITERRA cascade) |
| _MS_ALIAS | supply_module.py:1983 | member-state code aliases |

EU_POLICY_KEYS (2659) is a set of keys of the scenario dict, not codes of data: it stays in the code. H3 (CAPRI's own
sets) needs a builder that extracts them into capri_data/shared/sets/ (HARDCODED_TABLES plan step 3); builders are run
by the maintainers only.

## 3. Proposed objects

### 3.1 Objects and what goes where

capri_mod/supply/state.py, beside capri_mod/market/state.py, with the same names for the same roles. Field names drop
the leading underscore, as in 2b (`_nlp_prev` -> `sv.nlp_prev`).

Per regional model (RegionalSupplyModel):

| object | class | fields (from the inventory; Appendix A) |
|---|---|---|
| `par` RegionalParameters | a | the split and histosol calibrations and their pending flags (grass_cz, grass_pending_col, dairy_cz, dairy_pending, cattle_cz, cattle_pending, genet_cz, genet_pending, genet_key, genet_cz_store, hist_cal, hist_pending); CAPRI's NLP calibration (nlp_cal, nlp_base_alloc, nlp_cal_store, npk_dual_bound, npk_prior_override, npk_prior_recalibrated); base_cal_shift; the memos (base_levels_cache, ef_lea_cache, ef_min_n2o_cache, min_n2o_parts_cache, npk_kappa, input_cost_memo, oyg_memo, genet_rows_memo); later (Q8) Q, f, net_revenues0, premiums0, gross_rev |
| `sv` RegionalSolveState | b1 | nlp_prev, nlp_prev_f, nlp_y, nlp_cols, nlp_relax_keep, kkt_base, amm_last, wc_solved, n_relax_sticky |
| `ev` RegionalEvalState | b2 | the problem's layout (row_labels, aug_labels, fall_floor, mineral_row, alloc_cols/m0/row, cover_dbf_nb, land_rent_rows, land_types_used, need_row, nrow_land, pool_avail, pool_cols, pool_cols_pk, grass_col, dairy_col, dairy_req_extra, cattle_cols, genet_cols, hist_cols); the solve's arguments (surplus_row, mineral_cap, nbal_price, price_shock_now, yields_solve0); the blocks' intermediate results (greendeal_inputs, cover, n_intensity, organic_conv, yield_price_factor, manure_ni_relief, manure_ni_nh3, animal_n_relief, amm_cost, ghg_applied, ghg_nr_obj, nlp_nip, nlp_mine_small, last_req_duals, last_duals); the solve's control flags (nlp_accept_last, nlp_try_n_relax, nlp_fb_last, nlp_n_target_cause, nlp_failed) |
| `res` RegionalResults | c | the last solve's outputs read by SupplyModule, the coupling and the reports (last_grass_z, last_dairy_z, last_cattle_z, last_genet_z, last_hist_fallow, last_manure_trade, last_manure_trade_pk, last_mineral_n, last_npk, last_aug, last_feed_dm, last_feed_t, land_solution, cover_solved, fd_model, yani_dnet, fert_tech_shares, fert_inside_factor, manure_tech_shares, animal_n_kept, animal_nh3_saved, manure_supply0, manure_supply0_pk, pool_manure_vec, pool_manure_vec_pk, nlp_rc, nlp_ok, nlp_status, nlp_nonoptimal, balance_shortfall, n_target_relaxed) and the diagnostics (n_solves, kkt_ipopt, nlp_fallback_log, nlp_jump, nlp_path, nlp_relaxed) |
| `seen` RegionalSeen | e | what SupplyModule sets before each solve (feed_rations, feed_prices, feed_bulk_ratio, ration_state, yani_price_ratio, manure_pool_price, manure_pool_price_pk, ghg_tax, ghg_coef, manure_ctx, fert_techs_all, env_for_surplus) and model.py's nlp_cal_check |

Per SupplyModule:

| object | class | fields |
|---|---|---|
| `par` SupplyParameters | a | the per-region caches (mctx_cache, balance_cache, mcap_cache), jrc_capped_cache, inner_fert, env_for_surplus, genetics_key; later the declared parameters read through the adapter (section 2.3) |
| `sv` SupplySolveState | b1 | nbal_state, nbal_bracket, nbal_prev (today's _PAR_STATE); base_cal_round, base_cal_prev, base_cal_stalled |
| `seen` SupplySeen | e | what CAPRIModel sets (feed_rations, feed_prices, feed_bulk_ratio, ration_state, ghg_tax, ghg_coef, manure_pool_price, manure_pool_price_pk, manure_trade_on, yani_price_ratio, yani_price_ratio_ms, yani_price_ratio_m, price_dev_ms, milk_price_dev_ms) and the Hessian's switches (hess_probe, hess_shock, hess_base_res) |
| `res` SupplyResults | c | max_nbal_update, max_nbal_region, worker_failures, hess_fp, hess_verify |

`ev` keeps its lifetime in the moves (it is not reset per solve, as 2b kept the market's): the fields that SupplyModule
or the coupling read after the solve (`last_duals`, `land_types_used`, `pool_cols`, `pool_avail`, `cover`,
`animal_n_relief`; Appendix A, column "other") are read from the last solve's `ev`. A reset of `ev` at the start of
each solve would be a behaviour change.

`data`, `_models`, `Q`, `acts`, `n`, `rid` stay where they are in this stage. The 12 write-only attributes and the 3
reads without writers are removed, not moved (as 2b's step 3). The settings and class constants stay class attributes;
the three class attributes changed as run state (`nlp_tol`, `use_fert_allocation`, `use_manure_pool`) stay too in the
moves (their move to `seen` changes which processes see a change, so it is a separate step, Q11).

CAPRI's counterpart, for orientation: `par` holds what CAPRI keeps as calibrated parameters (p_pmp*, the fertiliser
priors, p_feedBlkElas...), `sv` what GAMS keeps implicitly as variable levels and marginals between solves (CONOPT
starts from the last solution), `ev` CAPRI's intermediate parameters of one simulation step, `res` its result
parameters. [inferred mapping]

### 3.2 Form of the objects: slot classes, not dataclasses with None defaults (a departure from 2b, my proposal)

The market's objects are dataclasses whose fields default to None (state.py:19-146). For the supply I propose classes
with `__slots__` and no defaults, so that an unset field is absent exactly as an unset attribute is today:
`getattr(self.sv, "nlp_prev", D)` returns D, `self.sv.nlp_prev` raises AttributeError, `hasattr` is false, `del`
works, and an undeclared field name cannot be written (slots forbid it). Reasons, from the inventory:

- the seven supply files hold 351 `getattr(self, ...)` calls (grep), most with defaults, and 9 supply names are read with
  different defaults at different places (`_land_types_used` with `[]` at supply_module.py:1718 and None at
  fertilisation.py:234; `_organic_conv`, `_pool_cols`, `_yield_price_factor`, `_fert_tech_shares` alike; my scan). A
  None default would change any reader that relies on its own default (`dict(getattr(self, "_x", {}))` becomes
  `dict(None)`); with slots each `getattr(self, "_x", D)` becomes `getattr(self.ev, "x", D)` with the same meaning;
- `run()`'s `hasattr(self, "_nbal_state")` (2776) and the AttributeError handlers on the result paths (e.g.
  supply_module.py:3121) depend on absence;
- the Hessian's restore deletes the fields absent from the snapshot (hessian.py:204-205); with slots `delattr`
  reproduces it.

Slot objects pickle and deep-copy (protocol 2 and later; Python 3.13 here). Converting to dataclass defaults, as the
market, can follow later field by field, each a reviewed behaviour-neutral change. This differs from what 2b did; I
think it is the better choice for the supply because a pure move is then mechanical (Q1).

### 3.3 The guard (as state.MOVED)

A `SupplyStateMixin` on RegionalSupplyModel and SupplyModule, as MarketStateMixin: `__getattr__` and `__setattr__`
raise RuntimeError for a name in `MOVED_REGIONAL` / `MOVED_MODULE` ("now ev.row_labels (refactor stage 3c)"), so
`getattr(obj, old, default)` cannot hide it; `__setattr__` calls `object.__setattr__` otherwise, so the `setting`
descriptors keep raising on writes to non-run-state settings (settings/__init__.py:282-287). The properties create the
objects on first use, so stubs built with `__new__` work (as the tests' stubs of the market).

What it does not catch: `obj.__dict__[...]` reads and writes (hessian.py, `_par_solve_region`, set_genetics_effects
2099-2117, `self.__dict__.pop("_nlp_cal_check")` nlp.py:176, model.py's `_m._nlp_cal_check` goes through `__setattr__`
and is caught) and string names held in tuples (SOLVE_STATE, _PAR_STATE, _PAR_CACHES, run_f2f_2030.py:456). Hence a
static test: an AST scan of capri_mod and tools for string constants equal to a MOVED name in `getattr`/`setattr`/
`hasattr`/`__dict__` calls and subscripts and in those tuples (the market's test only checks the runtime guard,
test_market_layers.py:190-202; 2b found 13 leftover uses after its rebase, 7 of them string getattr reads or writes that
"would have done nothing", CHANGELOG l. 346-350).

### 3.4 The Hessian's snapshot and restore

Today: the restored set is "names starting with `_nlp` (except `_nlp_times` in the skip mode) plus SOLVE_STATE" for
every regional model, plus `_PAR_STATE` on SupplyModule (hessian.py:187-211). Proposal:

1. First, before any move, replace the prefix rule by declared tuples equal to today's set:
   `NLP_STATE` (the 27 `_nlp*` names the code writes) and SOLVE_STATE. Pure if no other `_nlp*` attribute exists; a
   test asserts after solves that every `_nlp*` key in a model's `__dict__` is in NLP_STATE.
2. With the objects, the tuples become dotted paths (`("sv", "nlp_prev")`, `("par", "nlp_cal")`, ...), and the
   restore keeps today's semantics exactly: each field copied on its own (deepcopy in the skip mode, shallow copy of the
   NLP_STATE fields only otherwise), fields absent in the snapshot deleted. The restore never copies whole objects in
   the moves (finding 1.3-2). `_PAR_STATE` becomes the fields of SupplySolveState marked "per region, returned by the
   workers".
3. As a later behaviour change, if wanted: restore `sv` (and `ev`) whole and leave `par` and `res` alone, which adds
   `n_relax_sticky` and `ghg_applied` to the restore and drops the calibration and diagnostics (Q2). Its own check.

Every move changes the Python files that make up the Hessian cache key's code fingerprint (hessian.py:17-33: every .py
of capri_mod except market, tests, pipeline), so each gate run measures the Hessian again: the restore path is
exercised at every gate. [verified that the fingerprint covers capri_mod/supply and capri_mod/coupling]

### 3.5 The workers (fork)

The regional models are pickled back whole, so their `par`, `sv`, `ev`, `res` and `seen` travel with them; `seen`'s
`env_for_surplus` (a shared EnvironmentalModule) is removed before pickling and re-attached in the parent, as today
(3198, 3286). `_par_solve_region` returns, for SupplyModule, the region's entries of the fields of `sv` and `par`
declared as per-region and worker-returned (today's _PAR_STATE and _PAR_CACHES), and the parent merges them into the
same fields (3200-3207: `setdefault` on the field, region entry set or removed). A field written in a worker but not
declared is lost, as today; the guard is a test (section 4.3, R1). The class-level run state (`nlp_tol`, ...) is
untouched and still reaches the workers by fork.


## 4. Commits, checks and risks

### 4.1 The check of every commit

- **Reference**: on the starting HEAD, the mini-EU Farm-to-Fork run (tools/run/run_mini_eu.py: 20 units,
  PYTHONHASHSEED=0, run_f2f_2030.py in a subprocess) kept as `runs/REFERENCE_s3c.pkl`, with the machine's worker count
  noted. Its run time measured, to size the gates.
- **Each commit**: the same run, compared with tools/check/compare_pickles_exact.py at `--rtol 1e-12` (its absolute
  tolerance is 1e-12, l. 37, 63), every path reported; plus the test suite (pytest-xdist -n 2, the project's setting).
  For the number commits also `tools/check/make_code_data.py --check` after regenerating 03 and removing the moved
  rows from 04.
- **Conditions for a bit-identical comparison** [inferred, from the code]: run the gate alone on the machine, because
  IPOPT's CPU-time guard (`supply.nlp_max_cpu_time = 60`) can cut a solve short under load, which would make two runs of
  the same code differ; run both sides as fresh processes (the solver cache `_SOLVERS` changes the last digits,
  test_capri.py:2645-2648; run_mini_eu.py already starts a subprocess); same worker count on both sides. The Hessian
  is re-measured at every commit (section 3.4), on both sides only if the reference is made with the cache cleared,
  which I recommend so that the reference is not a Hessian read from disk.
- **Cadence**: the project lead prefers gates per batch (several changes checked together). Each commit is pure, so a
  batch can be gated once and bisected if it fails. Proposed batches below (B1-B6), six mini-EU runs and six suites.

### 4.2 Sequence

State moves (no behaviour change in any commit; "updates" = every reader and writer in supply, coupling, model.py,
environmental/income readers, tests and tools, in the same commit):

| # | commit | content | guard added | batch |
|---|---|---|---|---|
| S0a | tests before moves | (i) the workers test on 3 regions so that it forks (finding 1.3-5), comparing results, every model's restored fields and SupplyModule's _PAR_STATE between 1 and 2 workers; (ii) a Hessian round trip: snapshot, a shocked solve, restore, the restored fields bit-equal to the snapshot and a re-solve equal to the base; (iii) an inventory test: after solves, the instance attributes of a regional model and of SupplyModule are in a declared list (Appendix A), so new state cannot appear unclassified | the three tests | B1 |
| S0b | Hessian restore by declared lists | `NLP_STATE` (27 names) replaces the `_nlp` prefix (hessian.py:187-190); same set, same copy functions | test: no `_nlp*` attribute outside NLP_STATE after solves | B1 |
| S0c | state module | capri_mod/supply/state.py: the slot classes (empty), SupplyStateMixin with empty MOVED tables on both classes, the restore helpers taking dotted paths; the static test of section 3.3 | static string scan | B1 |
| S1 | write-only and phantom names removed | the 12 + 1 write-only attributes and the 3 reads without writers (finding 1.3-7, 1.3-8), also out of SOLVE_STATE / NLP_STATE; tests reading `_last_aug_A/_b` adapted | names in MOVED as "removed" | B1 |
| S2 | NLP block, carried state and calibration | sv.nlp_prev, nlp_prev_f, nlp_y, nlp_cols, nlp_relax_keep, kkt_base, wc_solved; par.nlp_cal, nlp_base_alloc, nlp_cal_store, npk_dual_bound; readers in hessian.py, set_genetics_effects, model.py | MOVED entries; restore list renamed | B2 |
| S3 | NLP block, working state and results | the other nlp.py attributes into ev and res; readers in model.py (1080-1093, 1387-1391), coupling/reporting.py, coupling/manure.py | idem | B2 |
| S4 | livestock and feed | the split columns (ev), their calibrations (par), last_*_z (res) | idem | B2 |
| S5 | fertilisation | memos and priors (par), n_relax_sticky (sv), the rest (ev, res); `_fert_params_raw` keeps its instance toggle as it is (finding 1.3-9 is a separate change) | idem | B3 |
| S6 | land | the land market's layout and the manure pools (ev, res); readers in coupling/manure.py (27, 80-136) | idem | B3 |
| S7 | abatement | amm_last (sv), the ammonia and inhibitor accounts (ev, res), histosols (par, ev); `ghg_nr_obj` kept as a reference, never copied | idem; identity test of `_apply_ghg_tax`'s undo | B3 |
| S8 | policy and core | policy's memos (par) and per-solve fields (ev); core's solve arguments, layout and results (ev, res); `net_revenues`, `premiums`, `f`, `Q` stay on the model (Q8) | idem | B4 |
| S9 | the regional models' inputs | seen: what SupplyModule sets in `_solve_region_impl` (2975-3008) and model.py's nlp_cal_check; `env_for_surplus` still removed before pickling | idem | B4 |
| S10a | SupplyModule par, sv, res | _PAR_STATE and _PAR_CACHES as declared fields; `_par_solve_region` and the parent's merge (3195-3207) on the objects; `run()`'s `hasattr` (2776) on `sv` | the workers test of S0a | B4 |
| S10b | SupplyModule seen | CAPRIModel's 15 inputs and the Hessian's switches; readers in model.py, coupling/feed.py, manure.py, young_animals.py, hessian.py | idem | B4 |
| S11 | documentation | ARCHITECTURE_REFACTOR stage table, the inventory as docs/design/SUPPLY_STATE_INVENTORY.md, CHANGELOG | - | B4 |

Numbers and code tables (each also a pure move, checked identical; after the state moves, because the values go into
`par`):

| # | commit | content | batch |
|---|---|---|---|
| N1 | parameters through the adapter | RunInputs reads `<data_dir>/shared/model_parameters.csv`; params.py delegates to the current inputs; the supply's 11 `param()` constants read when SupplyModule builds its parameters (Q6) | B5 |
| N2 | supply's CAPRI constants | the 22 census rows and those of 2.2 confirmed in the GAMS, merged by concept (2.1), as rows of model_parameters.csv with the citation from 04; the code reads them from `par` | B5 |
| N3 | literature and scenario rule numbers | JRC121368's tiered rule (0.25, 0.50, 0.75, 50, 100, 150), the default surplus cut 0.5 (kind jrc121368), unless Q10 sends them to stage 5 | B5 |
| N4 | physical constants | 44/28 and 4.1868 (Q5) | B5 |
| N5 | numerical and technical to settings | CAL_RIDGE (also in the Hessian key), the IPOPT start shrink 0.95, the support margin 0.999, lsq_linear's 5000, the fertilisation sub-solve's 3000 (reads supply.nlp_max_iter), the two cache sizes 16, ABSENT_LEVEL 1e-8, the organic share cap 0.99, the bisections' 60, the progress print 50; the tests-only threshold 30 (capri_pmp.py:95) into its test; the 2017/2030 market-year selectors kept | B6 |
| N6 | code tables | the supply's tables of 2.4 as declared CSVs in capri_data/codes (H2) or read from CAPRI's sets (H3, needs the sets builder); possibly two commits (H2, then H3) | B6 |

That is 15 commits for the state (S0a-S11, S10 in two) and 7 for numbers and tables (N6 in two): 22 commits, 6 gates.

### 4.3 Risks and how each step guards them

| # | risk | where it can happen | guard |
|---|---|---|---|
| R1 | state not carried across the fork: a SupplyModule field written in a worker and not returned is lost, so results depend on the worker count | S10a, any later field on SupplyModule's `sv`/`par` | worker-returned fields declared in one place (field metadata), `_PAR_STATE` derived from it; S0a's 3-region test with 1 and 2 workers comparing results and state (today's test does not fork, finding 1.3-5); the mini-EU gate forks |
| R2 | state not restored, or restored differently, by the Hessian | S0b, S2-S9 | the restore list equal to today's set, per-field copies with today's copy functions (3.4); S0b's prefix test; S0a's round-trip test; each gate re-measures the Hessian (code fingerprint) |
| R3 | an attribute set in one block and read in another left on the old name | every move | the cross-block reads are listed (Appendix A, "reads" and "other" columns); one commit moves all sites of a field; the runtime guard raises on any read or write of an old name, getattr with a default included; the static scan finds `__dict__` and string uses the guard cannot see |
| R4 | getattr defaults hiding missing state (a moved name read with a default returns the default silently) | every move | the guard raises RuntimeError, not AttributeError, so a default cannot apply (as 2b); slot objects keep "absent" distinct from None (3.2); the phantom reads removed in S1 |
| R5 | behaviour change from None defaults: `hasattr` (2776), readers' own defaults, AttributeError handlers | if dataclasses were used | slot objects (3.2); otherwise each field's default checked against every reader |
| R6 | identity: `_ghg_nr_obj is self.net_revenues`, `id()`-keyed `_base_levels_cache`, the feed block cache keyed on the rations dicts | S4, S7, S8, S9 | fields hold the same objects (no copies in the moves); a test of the GHG tax's undo; the identical run |
| R7 | deepcopy of whole objects aliasing fields that are copied apart today | S2-S9 if the restore copied objects | the restore copies fields (3.4-2); whole-object restore only as a separate behaviour change (Q2) |
| R8 | the guard's `__setattr__` interfering with the `setting` descriptors or with pickling | S0c | `object.__setattr__` path; a test that pickles and deep-copies a solved regional model and gets equal state back; the market's mixin already pickles |
| R9 | tests and tools on old names | every move | updated in the same commit; the guard makes a leftover fail loudly; the static scan covers tools/ (run_f2f_2030.py:456's dump, check_regression.py:83-91) |
| R10 | a gate that is not reproducible for reasons outside the move (CPU-time guard under load, the solver cache, a Hessian read from cache) | every gate | the conditions of 4.1 |
| R11 | a "pure" move that is not: e.g. the instance toggle of use_fert_allocation (1.3-9), the restore set (1.3-1), the class-level run state | S5, S2, S9 | left as they are in the moves and listed as separate behaviour changes (Q11), each with its own run |

## 5. Effort and open questions

### 5.1 Effort (an estimate)

Stage 2b moved about 49 market attributes in 6 commits; its commits are dated 27 October 17:50 to 28 October 21:09,
after an inventory on 26 October. The supply has about 186 attributes, the fork and the Hessian restore to keep exact,
and the number and table moves. My estimate: the state moves 4-6 working days, the numbers and tables 2-3 (more if H3's
sets builder is needed for many tables), plus the six gates, whose duration I do not know (the reference run's time
gives it). In total roughly 7-10 working days. The largest uncertainty is how many leftover uses the gates reveal (2b
found 13 after its rebase).

### 5.2 Open questions for the project lead

- **Q1** Slot classes for the supply's state objects (absent stays absent, 3.2) instead of the market's dataclasses with
  None defaults: I think it is the better choice here because it makes each move mechanical and exact; it differs from
  stage 2b. Agree?
- **Q2** The Hessian's restore: keep today's set during the moves (it restores the NLP calibration and diagnostics and
  misses `n_relax_sticky` and `ghg_applied`), and afterwards, as its own behaviour change, restore `sv` and `ev` whole?
- **Q3** Five objects per regional model (`par`, `sv`, `ev`, `res`, `seen`), one more than the market (`res`), or fold
  the results into `ev`?
- **Q4** Gates per batch (six mini-EU runs, 4.2) rather than per commit; a full Farm-to-Fork run only at the end?
- **Q5** The physical constants (44/28, 4.1868) into model_parameters.csv as agreed on 31 October, or kept as named
  code constants? In the project's terminology a parameter is a value one can change to make a different run; these
  cannot be changed meaningfully. The agreement stands unless you change it.
- **Q6** Parameters read from the run's data directory (`<data_dir>/shared/model_parameters.csv`): the same values for
  capri_data, a behaviour change for another data directory (today the package's copy is read whatever the data
  directory). Agree?
- **Q7** A one-off census of the supply files without the small-number filter (2.2), classified by hand, before N2?
- **Q8** `net_revenues`, `premiums`, `f`, `Q` into `par` (with the solve's working copy of the net revenues in `ev`):
  in this stage or later? It is not a rename (the in-place mutation and the restore at the end of `_solve_once` would
  become an explicit copy), so I left it out of the moves.
- **Q9** The workers test: three regions (more time per suite run) so that it forks?
- **Q10** JRC121368's tiered rule and the default surplus cut: into model_parameters.csv now, or into the scenario's
  files in stage 5 (they belong to the scenario)?
- **Q11** The hazards found (1.3-1, -9, -10 and the class-level run state): fix each after the moves as its own
  behaviour change with its own run, or leave them?


## Appendix A. The attributes, block by block

Columns: class (1.1); tags: SS = in SOLVE_STATE, nlp* = restored by the Hessian's prefix rule, ext = written by
SupplyModule or the coupling on the regional model; writes and reads within the class, as file:lines (all writes,
mutations and deletions outside `__init__`; `__init__` writes included where the attribute also has later writes);
other = readers and writers in SupplyModule after the solve, in the rest of capri_mod (w: = a write) and the number of
uses in the tests. Generated by an AST scan (section 0), classified by hand.

### A.1 core

| attribute | class | tags | writes | reads (own class) | other readers/writers | note |
|---|---|---|---|---|---|---|
| `_base_cal_shift` | a | ext | (after the solve: SupplyModule or module helpers) SupplyModule.calibrate_to_base 2519 |  |  |  |
| `_base_levels_cache` | a |  | supply_module.py:683 | supply_module.py:678 |  | memo keyed on id() of data.base_areas / base_animals |
| `f` | a | ext | (after the solve: SupplyModule or module helpers) __init__; shifted by SupplyModule.calibrate_to_base 2518 | supply_module.py:665,1672 |  |  |
| `net_revenues` | a |  | policy.py:191,248,386,425,533; supply_module.py:850,1525; abatement.py:318,356,494,504; fertilisation.py:748; livestock.py:82 | abatement.py:317,318,353,356,492,494,496,502,504; fertilisation.py:746,748; livestock.py:80,82; policy.py:155,229,365,422,482; supply_module.py:656,1494,1672,1884 | tests: 12 | built in __init__; rebuilt under a shock and mutated by the blocks within a solve, restored at the end of _solve_once (supply_module.py:1494, 1525); not in the Hessian's restore |
| `premiums` | a |  | supply_module.py:852 |  | income/income_module.py:106 | __init__; rewritten by a shocked _compute_net_revenues; read by income/income_module.py:106 |
| `_fall_floor` | b2 |  | supply_module.py:1026,1102 | abatement.py:77; policy.py:97; supply_module.py:1350 | tests: 1 |  |
| `_mineral_cap` | b2 |  | supply_module.py:1429,1451 | fertilisation.py:435,688; supply_module.py:1301 |  | solve argument held for this solve |
| `_mineral_row` | b2 |  | supply_module.py:1209,1245,1274 | supply_module.py:1245,1274 |  |  |
| `_nbal_price` | b2 |  | supply_module.py:1434,1452 | supply_module.py:1656,1657 |  | solve argument held for this solve |
| `_price_shock_now` | b2 | SS | supply_module.py:702,1445 | livestock.py:236,395,515 |  | reset per solve (1445); listed in SOLVE_STATE |
| `_row_labels` | b2 |  | supply_module.py:1029,1056,1106,1116,1148,1183,1286,1332,1352,1368,1391,1398,1400 | fertilisation.py:794; land.py:38; nlp.py:113,608; supply_module.py:1056,1106,1116,1148,1183,1286,1332,1352,1368,1391,1398,1400,1754,1915 | tests: 7 | rebuilt by _build_constraints every solve |
| `_surplus_row` | b2 |  | supply_module.py:1428,1450 | fertilisation.py:17,687,795,824; land.py:128; supply_module.py:1200 |  | solve argument held for this solve (1428, reset 1450) |
| `_yields_solve0` | b2 |  | supply_module.py:1519,1524 | policy.py:400 | tests: 2 | set/cleared in _solve_once |
| `_land_solution` | c | SS | supply_module.py:1437,1742 |  | supply_module.py:3030,3083 (after the solve: SupplyModule or module helpers) | SupplyModule reads it after the solve (3030) |
| `_last_aug` | c | SS | supply_module.py:1726 |  | coupling/manure.py:87 ; tests: 2 | coupling/manure.py:87; tests |
| `_last_grass_z` | c | SS | supply_module.py:1728,1745,1771 |  | supply_module.py:3024,3077 (after the solve: SupplyModule or module helpers) | SupplyModule 3024 |
| `_last_hist_fallow` | c | SS | supply_module.py:1734,1760,1778 |  | supply_module.py:3029,3082 (after the solve: SupplyModule or module helpers) | SupplyModule 3029 |
| `_last_land` | c | SS | supply_module.py:1719 |  |  | write-only |
| `_last_manure_trade` | c |  | supply_module.py:1431,1722 |  | supply_module.py:3013,3066 (after the solve: SupplyModule or module helpers) | SupplyModule 3013 |
| `_last_manure_trade_pk` | c |  | supply_module.py:1432,1723 |  | supply_module.py:3014,3067 (after the solve: SupplyModule or module helpers) | SupplyModule 3014 |
| `_last_mineral_n` | c |  | supply_module.py:1433,1720 |  | supply_module.py:3320 (after the solve: SupplyModule or module helpers) | _mineral_n_for_accounts (3320) |
| `_last_plain` | c |  | supply_module.py:1795 |  |  | write-only (read only by run_f2f_2030.py's optional CAPRI_DUMP_REGIONS dump, l. 456) |
| `_mineral_row_m` | c |  | supply_module.py:1334,1430 |  |  | write-only |
| `balance_shortfall` | c |  | fertilisation.py:816; supply_module.py:1427,1470,1710 | supply_module.py:1469 | tests: 1 | copied to the result (1469) |

### A.2 livestock

| attribute | class | tags | writes | reads (own class) | other readers/writers | note |
|---|---|---|---|---|---|---|
| `_cattle_cz` | a |  | livestock.py:366 | livestock.py:229,358 | tests: 1 | linear terms calibrated from the duals of the first solves |
| `_cattle_pending` | a |  | livestock.py:323,367 | livestock.py:205,354 |  | calibration pending flag |
| `_dairy_cz` | a |  | livestock.py:540 | livestock.py:503 | tests: 1 | calibrated from duals |
| `_dairy_pending` | a |  | livestock.py:505,507,542 | livestock.py:205,533 |  | calibration pending flag |
| `_genet_cz` | a |  | livestock.py:467 | livestock.py:388,460 |  | per genomics settings; also written by SupplyModule.set_genetics_effects (2114) |
| `_genet_cz_store` | a | ext | (after the solve: SupplyModule or module helpers) SupplyModule 2099 |  |  |  |
| `_genet_key` | a | ext | (after the solve: SupplyModule or module helpers) SupplyModule 2117, 2195 |  |  |  |
| `_genet_pending` | a |  | livestock.py:451,468 | livestock.py:206,456 |  | also SupplyModule 2115 |
| `_genet_rows_memo` | a |  | livestock.py:402 | livestock.py:399 |  | memo |
| `_grass_cz` | a |  | livestock.py:550 | livestock.py:179 |  | calibrated from duals |
| `_grass_pending_col` | a |  | livestock.py:181,184,551 | livestock.py:546; supply_module.py:1730,1774,1787 |  | calibration pending flag |
| `_cattle_cols` | b2 |  | livestock.py:225,294 | livestock.py:94,212,294; nlp.py:34; supply_module.py:1763 | tests: 1 |  |
| `_dairy_col` | b2 |  | livestock.py:481,524 | livestock.py:89,210,525; nlp.py:32,33; supply_module.py:1762 | tests: 1 |  |
| `_dairy_req_extra` | b2 |  | livestock.py:297,450,482,525; supply_module.py:1782 | livestock.py:295,448; nlp.py:124 |  |  |
| `_genet_cols` | b2 |  | livestock.py:384,447 | livestock.py:99,213,447; nlp.py:36 |  |  |
| `_grass_col` | b2 |  | livestock.py:149,182,194 | fertilisation.py:500; nlp.py:30,31; supply_module.py:1727,1762,1770,1771 |  |  |
| `_last_cattle_z` | c | SS | livestock.py:212; supply_module.py:1439,1747 | supply_module.py:1864 | supply_module.py:3026,3079 (after the solve: SupplyModule or module helpers) ; tests: 4 | SupplyModule 3026; tests |
| `_last_dairy_z` | c | SS | livestock.py:211; supply_module.py:1746 | supply_module.py:1858 | supply_module.py:3025,3078 (after the solve: SupplyModule or module helpers) ; tests: 1 | SupplyModule 3025 |
| `_last_genet_z` | c | SS | livestock.py:213; supply_module.py:1748 | supply_module.py:1871 | supply_module.py:3028,3081 (after the solve: SupplyModule or module helpers) | SupplyModule 3028; also written by set_genetics_effects (2116) |
| `feed_bulk_ratio` | e | ext | (after the solve: SupplyModule or module helpers) SupplyModule 2989 | supply_module.py:827 | w:coupling/feed.py:48, coupling/hessian.py:176, w:coupling/hessian.py:305, w:coupling/hessian.py:224, w:coupling/hessian.py:273 |  |
| `feed_prices` | e | ext | (after the solve: SupplyModule or module helpers) SupplyModule 2986 | nlp.py:148 | w:coupling/feed.py:77 |  |
| `feed_rations` | e | SS ext | (after the solve: SupplyModule or module helpers) SupplyModule 2985 per solve; in SOLVE_STATE | abatement.py:15; livestock.py:247,406,486,568; nlp.py:111; supply_module.py:804 | w:coupling/feed.py:76, model.py:233 ; tests: 1 |  |
| `ration_state` | e | ext | (after the solve: SupplyModule or module helpers) SupplyModule 2975 | fertilisation.py:636; livestock.py:567 | w:coupling/feed.py:68 |  |
| `yani_price_ratio` | e | ext | (after the solve: SupplyModule or module helpers) SupplyModule 2979/2984 (class default None, supply_module.py:559) | livestock.py:71,238; nlp.py:505 | coupling/hessian.py:213, w:coupling/hessian.py:304, w:coupling/hessian.py:256, w:coupling/hessian.py:271, coupling/hessian.py:151, w:coupling/young_animals.py:278 (+3) |  |

### A.3 fertilisation

| attribute | class | tags | writes | reads (own class) | other readers/writers | note |
|---|---|---|---|---|---|---|
| `_ef_lea_cache` | a |  | fertilisation.py:68 | fertilisation.py:55 |  | memo |
| `_ef_min_n2o_cache` | a |  | fertilisation.py:32 | fertilisation.py:29 |  | memo |
| `_min_n2o_parts_cache` | a |  | fertilisation.py:47 | fertilisation.py:40 |  | memo |
| `_npk_kappa` | a |  | fertilisation.py:240 |  |  | memo (__dict__.setdefault, fertilisation.py:240) |
| `_npk_prior_override` | a |  | fertilisation.py:561 | fertilisation.py:304,554 |  | set when the calibration recalibrates CAPRI's priors (first solve) |
| `_npk_prior_recalibrated` | a |  | fertilisation.py:562 | fertilisation.py:562 |  | idem |
| `_n_relax_sticky` | b1 |  | fertilisation.py:818; supply_module.py:1709 | supply_module.py:1683 |  | carried across solves (read at 1683 before any write); NOT in SOLVE_STATE, not _nlp*: not restored by the Hessian |
| `_n_intensity` | b2 |  | fertilisation.py:677,745,750; policy.py:522,523; supply_module.py:1435,1467 | fertilisation.py:101,228,485,677,745,750,754; land.py:136,312; policy.py:522,523; supply_module.py:1206,1304,1453 |  | reset at solve start and end; copied to the result |
| `_nlp_mine_small` | b2 | nlp* | fertilisation.py:449; nlp.py:242 | nlp.py:253 |  |  |
| `_fert_tech_shares` | c |  | fertilisation.py:684,753; nlp.py:551,559,570,571; supply_module.py:1468 | fertilisation.py:753; nlp.py:570,571; supply_module.py:1457 | supply_module.py:3104 (after the solve: SupplyModule or module helpers) | copied to the result (1457), SupplyModule 3104 |
| `_n_target_relaxed` | c |  | fertilisation.py:817; supply_module.py:1438,1708 |  | supply_module.py:3033,3086 (after the solve: SupplyModule or module helpers) ; tests: 1 | SupplyModule 3033 |
| `_nlp_group_caps` | c | nlp* | fertilisation.py:457 |  |  | write-only |
| `_npk_cov` | c | SS | fertilisation.py:328 |  |  | write-only; in SOLVE_STATE |
| `use_fert_allocation` | d |  | fertilisation.py:760,763 | fertilisation.py:758,768 | w:model.py:590 | class attribute set by model.py:590; fertilisation.py:760/763 leaves an instance copy that shadows later class-level changes |

### A.4 land

| attribute | class | tags | writes | reads (own class) | other readers/writers | note |
|---|---|---|---|---|---|---|
| `_alloc_cols` | b2 |  | land.py:175; supply_module.py:1753 | livestock.py:234,393,495; nlp.py:22,151; supply_module.py:1720 |  |  |
| `_alloc_m0` | b2 |  | land.py:164 | land.py:378 |  |  |
| `_alloc_row` | b2 |  | land.py:165 | land.py:172 |  |  |
| `_aug_labels` | b2 |  | land.py:383; supply_module.py:1759 | nlp.py:114 | tests: 1 |  |
| `_cover_dbf_nb` | b2 |  | land.py:126,173 | nlp.py:261 |  |  |
| `_land_rent_rows` | b2 |  | land.py:83,87 | land.py:87; nlp.py:150 | tests: 1 |  |
| `_land_types_used` | b2 |  | land.py:377 | fertilisation.py:234; nlp.py:18,152; supply_module.py:1718,1719,1742 | supply_module.py:3031,3084 (after the solve: SupplyModule or module helpers) | also read after the solve (SupplyModule 3031) |
| `_need_row` | b2 |  | land.py:33,336; supply_module.py:1752 | livestock.py:168 | tests: 1 |  |
| `_nrow_land` | b2 |  | land.py:34,113 | fertilisation.py:804 |  |  |
| `_pool_avail` | b2 |  | land.py:255 | abatement.py:149; fertilisation.py:495 | supply_module.py:3017,3070 (after the solve: SupplyModule or module helpers) | also SupplyModule 3017 |
| `_pool_cols` | b2 |  | land.py:176,252 | abatement.py:147; fertilisation.py:233,493; land.py:329; nlp.py:24; supply_module.py:1721 | coupling/manure.py:82 ; tests: 2 | also coupling/manure.py:82 |
| `_pool_cols_pk` | b2 |  | land.py:177,287 | fertilisation.py:338; nlp.py:27; supply_module.py:1724 | coupling/manure.py:85, coupling/manure.py:27 ; tests: 1 | also coupling/manure.py:85 |
| `_last_aug_A` | c | SS | land.py:384 |  | tests: 1 | write-only in the model (tests read it, test_capri.py:3623) |
| `_last_aug_b` | c | SS | land.py:384 |  | tests: 1 | idem |
| `_manure_supply0` | c |  | land.py:253 |  | coupling/manure.py:83 | coupling/manure.py:83 |
| `_manure_supply0_pk` | c |  | land.py:288 |  | coupling/manure.py:86 | coupling/manure.py:86 |
| `_pool_manure_vec` | c |  | land.py:254 |  | coupling/manure.py:135 | coupling/manure.py:135 |
| `_pool_manure_vec_pk` | c |  | land.py:289 |  | coupling/manure.py:136 | coupling/manure.py:136 |
| `manure_pool_price` | e | ext | (after the solve: SupplyModule or module helpers) SupplyModule 2976 | land.py:228 | w:coupling/manure.py:264, coupling/manure.py:69, coupling/manure.py:114, w:model.py:592 ; tests: 1 |  |
| `manure_pool_price_pk` | e | ext | (after the solve: SupplyModule or module helpers) SupplyModule 2977 | land.py:275 | w:coupling/manure.py:266, coupling/manure.py:70, coupling/manure.py:115, w:model.py:593 ; tests: 1 |  |

### A.5 abatement

| attribute | class | tags | writes | reads (own class) | other readers/writers | note |
|---|---|---|---|---|---|---|
| `_hist_cal` | a |  | abatement.py:575 | abatement.py:533,570 |  | calibrated from duals |
| `_hist_pending` | a |  | abatement.py:563,576 | abatement.py:567; supply_module.py:1735,1779,1791 |  | calibration pending flag |
| `_amm_last` | b1 | SS | abatement.py:288 | abatement.py:426; fertilisation.py:151 |  | the ammonia options' linearisation point (hessian.py:184): read by _manure_inhibitor_params from the previous solve on the N-price path (fertilisation.py:682 before 685) |
| `_amm_cost` | b2 | SS | abatement.py:253,287 | abatement.py:287,316 |  | reset and refilled by _amm_record before its read |
| `_animal_n_relief` | b2 | SS | abatement.py:251,284 | abatement.py:284; supply_module.py:1214 | supply_module.py:3325 (after the solve: SupplyModule or module helpers) | read by _build_constraints (1214) and the accounts (3325) |
| `_cover` | b2 |  | abatement.py:205; supply_module.py:1536 | abatement.py:166,242; nlp.py:229; supply_module.py:1344 | supply_module.py:3020,3073 (after the solve: SupplyModule or module helpers) ; tests: 2 | reset per solve (1536); SupplyModule 3020 |
| `_ghg_applied` | b2 |  | abatement.py:495,505 | abatement.py:491,505 |  | undo record of the tax; acts only within one solve (net_revenues is a new object each solve); NOT in SOLVE_STATE |
| `_ghg_nr_obj` | b2 | SS | abatement.py:496 | abatement.py:492 |  | identity check `is self.net_revenues` (abatement.py:492); in SOLVE_STATE (its deepcopy can never be `is`) |
| `_hist_cols` | b2 |  | abatement.py:529,562 | abatement.py:562; nlp.py:38; supply_module.py:1734,1763,1778 | tests: 1 |  |
| `_manure_ni_nh3` | b2 | SS | abatement.py:331,358; nlp.py:548,568; supply_module.py:1655 | abatement.py:358; nlp.py:568 |  | reset per solve (1655) |
| `_manure_ni_relief` | b2 | SS | abatement.py:331,352; nlp.py:548,566; supply_module.py:1655 | abatement.py:352; nlp.py:566; supply_module.py:1215 | supply_module.py:3326 (after the solve: SupplyModule or module helpers) | reset per solve; read 1215, 3326 |
| `_nlp_nip` | b2 | nlp* | abatement.py:117 | abatement.py:157; nlp.py:560,561 |  |  |
| `_animal_n_kept` | c | SS | abatement.py:252,285 | abatement.py:285 | supply_module.py:3022,3075 (after the solve: SupplyModule or module helpers) | SupplyModule 3022 |
| `_animal_nh3_saved` | c | SS | abatement.py:251,286 | abatement.py:286 |  |  |
| `_manure_ni_share` | c | SS | abatement.py:331,359; nlp.py:548,569; supply_module.py:1655 |  |  | write-only; in SOLVE_STATE |
| `_manure_tech_shares` | c | SS | abatement.py:251,261,282 | abatement.py:261,282 | supply_module.py:3023,3076 (after the solve: SupplyModule or module helpers) | SupplyModule 3023 |
| `_env_for_surplus` | e | ext | (after the solve: SupplyModule or module helpers) shared EnvironmentalModule, SupplyModule 3002/3198; popped before pickling (3286) | abatement.py:22,449; fertilisation.py:203,274,443,478,571,613,645; land.py:213,303; livestock.py:153; policy.py:55; supply_module.py:1210,1302 | model.py:329, model.py:330 ; tests: 2 |  |
| `_fert_techs_all` | e | ext | (after the solve: SupplyModule or module helpers) SupplyModule 3006/3008 | abatement.py:102 |  |  |
| `_manure_ctx` | e | ext | (after the solve: SupplyModule or module helpers) SupplyModule 3004 (class default None, 951) | fertilisation.py:22 | tests: 1 |  |
| `ghg_coef` | e | ext | (after the solve: SupplyModule or module helpers) SupplyModule 2993 | abatement.py:480,498,510; fertilisation.py:157 | w:model.py:468, w:model.py:470 |  |
| `ghg_tax` | e | ext | (after the solve: SupplyModule or module helpers) SupplyModule 2992 | abatement.py:50,334,369,479,497,509; fertilisation.py:127,156; land.py:236; nlp.py:143 | w:model.py:467, w:model.py:471, model.py:1296, model.py:1295 ; tests: 1 |  |

### A.6 policy

| attribute | class | tags | writes | reads (own class) | other readers/writers | note |
|---|---|---|---|---|---|---|
| `_input_cost_memo` | a |  | policy.py:124 | policy.py:120 |  | memo |
| `_oyg_memo` | a |  | policy.py:260 | policy.py:257 |  | memo |
| `_greendeal_inputs` | b2 |  | policy.py:366; supply_module.py:1520 | policy.py:404 | tests: 3 | reset in _solve_once (1520) |
| `_organic_conv` | b2 |  | policy.py:525,526; supply_module.py:1436 | fertilisation.py:379; nlp.py:133; policy.py:525,526; supply_module.py:1456 |  | reset per solve; copied to the result |
| `_yield_price_factor` | b2 |  | policy.py:249; supply_module.py:1446,1455 | fertilisation.py:82,89; supply_module.py:1454 |  | reset per solve; copied to the result |

### A.7 nlp

| attribute | class | tags | writes | reads (own class) | other readers/writers | note |
|---|---|---|---|---|---|---|
| `_nlp_base_alloc` | a | nlp* | nlp.py:217 | fertilisation.py:380,437; nlp.py:63 |  | from the calibration; per genomics settings via _nlp_cal_store |
| `_nlp_cal` | a | nlp* | nlp.py:216 | nlp.py:159 | tests: 1 | CAPRI's calibration of the NLP form, at the first solve; recalibrated when late columns appear; per genomics settings |
| `_nlp_cal_store` | a | nlp* ext | (after the solve: SupplyModule or module helpers) SupplyModule 2110 |  |  |  |
| `_npk_dual_bound` | a |  | nlp.py:199 | fertilisation.py:347 |  | widened dual bound set at calibration (nlp.py:199); getattr default 10.0 (fertilisation.py:347) is CAPRI's bound |
| `_kkt_base` | b1 |  | nlp.py:327 |  | w:coupling/hessian.py:302, w:coupling/hessian.py:230 | market.hessian_method = kkt only; popped by hessian.py:230, 302 |
| `_nlp_cols` | b1 | nlp* | nlp.py:499 | nlp.py:368 | coupling/reporting.py:39 | jump check against the previous outer iteration (read 368 before write 499) |
| `_nlp_prev` | b1 | nlp* | nlp.py:484 | nlp.py:285,305 | tests: 1 | warm start: IPOPT's last point and multipliers |
| `_nlp_prev_f` | b1 | nlp* | nlp.py:485 | nlp.py:286,347 | model.py:1092 ; tests: 1 | warm start: last objective (warm check, K75) |
| `_nlp_relax_keep` | b1 | nlp* | nlp.py:463 | nlp.py:271 |  | the relaxation kept for the next solve (read 271 before write 463) |
| `_nlp_y` | b1 | nlp* | nlp.py:498 | nlp.py:365 | coupling/reporting.py:19 | jump check (read 365 before write 498) |
| `_wc_solved` | b1 | SS | nlp.py:108,518 | abatement.py:240,241; nlp.py:519,520,521 |  | the winter-cover share of the previous solve, read by _winter_cover_shares (abatement.py:240) in the next solve's ammonia accounts (supply_module.py:1661) before the NLP resets it (nlp.py:108) |
| `_last_duals` | b2 | SS | fertilisation.py:812; nlp.py:534; supply_module.py:1677,1744 | supply_module.py:1731,1733,1736,1775,1777,1780,1788,1790,1792,1911 | supply_module.py:3092,3094,3098 (after the solve: SupplyModule or module helpers); coupling/manure.py:96 | read in the same solve; also SupplyModule 3092, coupling/manure.py:96 |
| `_last_req_duals` | b2 | SS | nlp.py:547 | livestock.py:357,459,537 |  | read by the split calibrations after the NLP |
| `_nlp_accept_last` | b2 | nlp* | nlp.py:622,626 | nlp.py:474 |  | flag around the last attempt (_nlp_last_point) |
| `_nlp_failed` | b2 | nlp* | nlp.py:473,541; supply_module.py:1440 | nlp.py:629; supply_module.py:1685,1696 |  | reset per solve; read by _nlp_last_point and _solve_inner |
| `_nlp_fb_last` | b2 | nlp* | nlp.py:596,599 | supply_module.py:1695 | tests: 2 |  |
| `_nlp_n_target_cause` | b2 | nlp* | nlp.py:107,418; supply_module.py:1697 |  |  |  |
| `_nlp_try_n_relax` | b2 | nlp* | supply_module.py:1690,1694 | nlp.py:406,598 |  | flag around a call |
| `_cover_solved` | c | SS | nlp.py:108,519 |  | supply_module.py:3020,3073 (after the solve: SupplyModule or module helpers) ; tests: 2 | SupplyModule 3020 |
| `_fd_model` | c | SS | nlp.py:112,531 | supply_module.py:1461 |  | copied to the result (1461) |
| `_fert_inside_factor` | c |  | nlp.py:549 |  | supply_module.py:3097 (after the solve: SupplyModule or module helpers) | SupplyModule 3097 |
| `_fert_inside_weight` | c |  | nlp.py:550 |  |  | write-only |
| `_kkt_ipopt` | c |  | nlp.py:337 | nlp.py:337 | w:coupling/hessian.py:231, w:coupling/hessian.py:301 | counter popped by hessian.py:301 |
| `_last_feed` | c | SS | nlp.py:533 |  |  | write-only |
| `_last_feed_dm` | c | SS | nlp.py:153,582,593 |  | supply_module.py:3091 (after the solve: SupplyModule or module helpers) | SupplyModule 3091 |
| `_last_feed_t` | c | SS | nlp.py:154,583,594 |  | supply_module.py:3093 (after the solve: SupplyModule or module helpers) | SupplyModule 3093 |
| `_last_npk` | c | SS | nlp.py:512,591 | nlp.py:524,525,529,531,532 | supply_module.py:3016,3069,3317 (after the solve: SupplyModule or module helpers) | SupplyModule 3016, 3317 |
| `_n_solves` | c |  | nlp.py:106 | nlp.py:106 |  | counter (diagnostics) |
| `_nlp_abatement` | c | nlp* | nlp.py:514 |  |  | write-only |
| `_nlp_fallback_log` | c | nlp* | nlp.py:544,545,611,615; supply_module.py:1700,1703 | nlp.py:543,545,610,614,615; supply_module.py:1699,1703 | w:model.py:389, w:model.py:438, model.py:1387, model.py:1388 ; tests: 4 | run diagnostic; reset per run by model.py:389, 438 |
| `_nlp_jump` | c | nlp* | nlp.py:364,390 |  | model.py:1080, model.py:1082 | model.py:1080 |
| `_nlp_nonoptimal` | c | nlp* | nlp.py:479; supply_module.py:1442 | supply_module.py:1459,1798 |  | copied to the result (1459) |
| `_nlp_ok` | c | nlp* | nlp.py:155,539,595 |  | supply_module.py:3034 (after the solve: SupplyModule or module helpers) | SupplyModule 3034 |
| `_nlp_path` | c | nlp* | nlp.py:487 |  | coupling/reporting.py:23, model.py:1092 | model.py:1092, coupling/reporting.py:23 |
| `_nlp_rc` | c | nlp* | nlp.py:538,592 |  | coupling/manure.py:118 | coupling/manure.py:118 |
| `_nlp_relaxed` | c | nlp* | nlp.py:395,464 | nlp.py:465 | model.py:1390, model.py:1391, model.py:1093 | model.py:1093, 1390 |
| `_nlp_status` | c | nlp* | nlp.py:546; supply_module.py:1441 | supply_module.py:1799 |  |  |
| `_nlp_times` | c | nlp* | nlp.py:467 |  |  | write-only (the Hessian's skip mode excludes it from the restore by name) |
| `_yani_dnet` | c |  | nlp.py:109,501,507,511 |  | supply_module.py:3027,3080 (after the solve: SupplyModule or module helpers) | SupplyModule 3027 |
| `_nlp_cal_check` | e | nlp* | nlp.py:176 |  | w:model.py:602 | flag set by model.py:602 at a baseline, popped by nlp.py:176 |

### A.8 Read but never written (getattr defaults that always apply)

| attribute | read at | note |
|---|---|---|
| `_dairy_yield_base` | supply_module.py:1846 | no writer anywhere in capri_mod or tools (grep); the getattr default always applies |
| `_last_aug_cols` | nlp.py:19 | no writer anywhere in capri_mod or tools (grep); the getattr default always applies |
| `region` | policy.py:270 | no writer anywhere in capri_mod or tools (grep); the getattr default always applies |

### A.9 SupplyModule

| attribute | class | tags | writes | reads (own class) | other readers | note |
|---|---|---|---|---|---|---|
| `_balance_cache` | a | _PAR_CACHES | supply_module.py:2576 | supply_module.py:2563 |  | per region; _PAR_CACHES |
| `_env_for_surplus` | a |  | supply_module.py:2451,2561,2586,2618,3000,3176 | supply_module.py:2449,2452,2458,2560,2562,2570,2585,2587,2590,2617,2619,2620,2998,3001,3002,3174,3177,3198 | model.py:329, model.py:330 ; tests: 2 | shared EnvironmentalModule, built lazily (2998-3001, 3174-3177) before the fork |
| `_inner_fert` | a |  | supply_module.py:2635 | supply_module.py:2633 | environmental/nitrogen.py:594, environmental/phosphorus.py:13 | lazy InnerFertDist (2633-2635); built in a worker it is not sent back |
| `_jrc_capped_cache` | a |  | supply_module.py:2057 | supply_module.py:2044 | w:model.py:586 ; tests: 2 | from data and a setting; popped by model.py:586 every outer iteration |
| `_mcap_cache` | a | _PAR_CACHES | supply_module.py:2610 |  |  | per region; _PAR_CACHES |
| `_mctx_cache` | a | _PAR_CACHES | supply_module.py:2534 |  |  | per region; _PAR_CACHES |
| `_models` | a |  | supply_module.py:2090,2194,3199 | supply_module.py:2098,2185,2194,2195,2196,2488,2845,2850,3199 | coupling/feed.py:110, coupling/hessian.py:300, coupling/hessian.py:201, coupling/hessian.py:229, coupling/hessian.py:195, coupling/manure.py:259 (+6) ; tests: 12 | the regional models (each holds its own state) |
| `data` | a |  | supply_module.py:2063,2096 | supply_module.py:2096,2200,2451,2453,2540,2561,2567,2586,2589,2592,2618,2622,2743,2894,2908,2932,3000,3176,3178 | (the name is generic: other readers not separated from other objects' `data`) | __init__; set_genetics_effects writes data['genetics_effects'] (2096) |
| `genetics_key` | a |  | supply_module.py:2097 | supply_module.py:2195 |  | settings key of the genomics calibration |
| `_base_cal_prev` | b1 |  | supply_module.py:2477,2522 | supply_module.py:2483 |  |  |
| `_base_cal_round` | b1 |  | supply_module.py:2476,2521 | supply_module.py:2479 |  | base calibration rounds across the baseline's iterations |
| `_base_cal_stalled` | b1 |  | supply_module.py:2478,2522 | supply_module.py:2484 |  |  |
| `_nbal_bracket` | b1 | _PAR_STATE | supply_module.py:2711,2777,3044 | supply_module.py:2682,3044,3057 |  | _PAR_STATE |
| `_nbal_prev` | b1 | _PAR_STATE | supply_module.py:2708,2709,2777,3045 | supply_module.py:2699,2708,2709,3045 |  | _PAR_STATE |
| `_nbal_state` | b1 | _PAR_STATE | supply_module.py:2777,3040,3053 | supply_module.py:2776,2944,3040,3053 | tests: 1 | N-balance price per region; _PAR_STATE |
| `_base_cal_drift` | c |  | supply_module.py:2523 |  |  | write-only |
| `_hess_fp` | c | _PAR_CACHES | supply_module.py:2821 | supply_module.py:2822,2835 | w:coupling/hessian.py:315, w:coupling/hessian.py:226 | Hessian skip probe's digests; _PAR_CACHES; set/popped by hessian.py:226, 315 |
| `_hess_verify` | c | _PAR_CACHES | supply_module.py:2839 |  | w:coupling/hessian.py:316, w:coupling/hessian.py:226, coupling/hessian.py:314, coupling/hessian.py:313 | idem, verify mode; hessian.py:313-316 |
| `max_nbal_region` | c |  | supply_module.py:2791 |  | model.py:1111 | model.py:1111 |
| `max_nbal_update` | c |  | supply_module.py:2772,2792 | supply_module.py:2790,2792 | model.py:1165, model.py:1108 | model.py:1108, 1165 |
| `worker_failures` | c |  | supply_module.py:3218 | supply_module.py:3218 |  |  |
| `feed_prices` | e |  | supply_module.py:2746 | supply_module.py:2986 | w:coupling/feed.py:77 | coupling/feed.py:77 |
| `feed_rations` | e |  | supply_module.py:2745 | supply_module.py:2766,2985 | w:coupling/feed.py:76, model.py:233 ; tests: 1 | also set by CAPRIModel (coupling/feed.py:76); _base_rations fallback |
| `feed_bulk_ratio` | e | set from outside | coupling/feed.py:48; hessian.py:224, 273, 305 | supply_module.py:2989 | w:coupling/feed.py:48, coupling/hessian.py:176, w:coupling/hessian.py:305, w:coupling/hessian.py:224, w:coupling/hessian.py:273 | |
| `ghg_tax` | e | set from outside | model.py:467, 471 | supply_module.py:2544,2992 |  | |
| `ghg_coef` | e | set from outside | model.py:468, 470 | supply_module.py:2993 | w:model.py:468, w:model.py:470 | |
| `manure_pool_price` | e | set from outside | model.py:592; coupling/manure.py:264 | supply_module.py:2976 | w:coupling/manure.py:264, coupling/manure.py:69, coupling/manure.py:114, w:model.py:592 ; tests: 1 | |
| `manure_pool_price_pk` | e | set from outside | model.py:593; coupling/manure.py:266 | supply_module.py:2977 | w:coupling/manure.py:266, coupling/manure.py:70, coupling/manure.py:115, w:model.py:593 ; tests: 1 | |
| `manure_trade_on` | e | set from outside | model.py:328 (read with getattr default True at 9 sites) | supply_module.py:2452,2535,2562,2564,2587,2619,2636,3001,3177 | w:model.py:328 | |
| `yani_price_ratio` | e | set from outside | model.py:538, 548; coupling/young_animals.py:278; hessian.py | supply_module.py:2979 | coupling/hessian.py:213, w:coupling/hessian.py:304, w:coupling/hessian.py:256, w:coupling/hessian.py:271, coupling/hessian.py:151, w:coupling/young_animals.py:278 (+3) | |
| `yani_price_ratio_ms` | e | set from outside | model.py:539; coupling/young_animals.py:263, 268; hessian.py | supply_module.py:2980 | coupling/hessian.py:213, w:coupling/hessian.py:304, w:coupling/hessian.py:258, w:coupling/hessian.py:271, w:coupling/hessian.py:262, coupling/hessian.py:152 (+4) | |
| `yani_price_ratio_m` | e | set from outside | model.py:540; coupling/young_animals.py:260; hessian.py (not read by SupplyModule: the coupling's own storage) |  | coupling/hessian.py:214, w:coupling/hessian.py:304, w:coupling/hessian.py:263, w:coupling/hessian.py:271, w:coupling/young_animals.py:260, coupling/young_animals.py:90 (+4) | |
| `milk_price_dev_ms` | e | set from outside | model.py:611 | supply_module.py:2959 | coupling/hessian.py:153, w:model.py:611, model.py:618 | |
| `price_dev_ms` | e | set from outside | model.py:627, 634, 645 | supply_module.py:2952 | w:model.py:627, w:model.py:634, w:model.py:645, model.py:634, model.py:639 ; tests: 1 | |
| `ration_state` | e | set from outside | coupling/feed.py:68 | supply_module.py:2975 | w:coupling/feed.py:68 | |
| `_hess_probe` | e | set from outside | hessian.py:227, 236, 276, 282, 295 | supply_module.py:2810 | w:coupling/hessian.py:227, w:coupling/hessian.py:295, w:coupling/hessian.py:236, w:coupling/hessian.py:282, w:coupling/hessian.py:276 | |
| `_hess_shock` | e | set from outside | hessian.py:276 | supply_module.py:2839 | w:coupling/hessian.py:276 | |
| `_hess_base_res` | e | set from outside | hessian.py:239, 297 | supply_module.py:2829,2836 | w:coupling/hessian.py:239, w:coupling/hessian.py:297 | |

## Decisions (2 November 2026, the project lead)

The project lead agreed with the recommendations given with this plan:
1. Q1: slot classes (an unset field is absent, as an unset attribute is today), not stage 2b's dataclasses with None
   defaults.
2. Q2: the Hessian's save and restore keep today's set during the moves (explicit lists equal to it); restoring whole
   objects comes later, as its own behaviour change.
3. Q3: a fifth object, `res`, for the last solve's results and diagnostics.
4. Q4: one gate per batch (six batches).
5. Q5: physical constants (e.g. 44/28, 4.1868) stay named constants in one module with their citation; CAPRI's
   constants and the literature values go to the parameters file.
6. Q6: the parameters file read through the run's data directory (the data adapter), as its own commit.
7. Q7: a full census of the numbers in the supply files, without the small-number filter.
8. Q8: `net_revenues`, `Q`, `f` into `par` later, after the moves.
9. Q9: the parallel-vs-serial test fixed so that it forks (three regions), as the first commit.
10. Q10: JRC121368's rule numbers with the scenarios, in stage 5.
11. Q11: the hazards found (the two carried values not restored, `_n_relax_sticky` and `_ghg_applied`; the instance
    copy of `use_fert_allocation`) fixed after the moves, each as a separate behaviour change.
