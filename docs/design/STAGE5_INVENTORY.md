# Refactor stage 5: inventory and plan (read only)

Drafted 2 November 2026 (night) by a read-only pass; checked on three points (the Delta test at
test_market_layers.py:33-41, io_results.py's Experiment and save_results without callers, set_aside_10.gms's
SETR 10 on CAPRI's grandes cultures GRCU against the model's floor on all arable land). The questions in section 5
are the project lead's to decide before the moves start.


Branch manifest-sql, HEAD 7ffa68b. Nothing was run except AST scans, greps and
`import deltalake` / `import pydantic`. Line numbers are of this checkout. "Not determined" = not verified.

Scope source: docs/design/ARCHITECTURE_REFACTOR.md l. 84-99 (stage 5's scope); table row l. 65 ("not started").

Branch json-csv: `git log json-csv -5` tops at 289f71e; `git merge-base --is-ancestor json-csv HEAD` succeeds, so it
is **merged** into manifest-sql. Its commit 70b7e12 moved the three trajectories to capri_data/scenarios/.

---

## 1. Scenario definitions today

### 1.1 Existing capri_data/scenarios/ (trajectories only; reader capri_mod/projection/scenario_io.py l. 1-11, 32-54)

| Folder | Files (data rows) | settings.toml `name` | Note |
|---|---|---|---|
| capri_ref_2030 | settings.toml, growth.csv (138), regional.csv (45641) | `capri_ref_2030` | CAPRI 2030 Green Deal reference, endotech (res_2_1730greendeal_refpol_endotech_all_ini) |
| captrd_2030 | settings.toml, growth.csv (185), regional.csv (67295) | **`captrd_baseline`** | name differs from folder: a check to add |
| null | settings.toml only | `null` | identity trajectory |

Columns: growth.csv `block,item,year,factor`; regional.csv `block,region,item,year,factor` (scenario_io.py l. 21-22).
No policy scenario is stored as data yet.

### 1.2 Python objects that define a scenario or its numbers

Counted: **24** objects (rows below; rows 20-24 are data or settings already outside Python but scenario-specific).

| # | Object | file:line | Holds | CAPRI's part (GAMS cited by the code) | Model's part |
|---|---|---|---|---|---|
| 1 | `PolicyScenario` dataclass | capri_mod/policy/policy_module.py:48-158 | the schema: 27 fields. Settings (manure_trade, biofuel_markets, negative_milk_price, surplus_rule, pesticide_rule, endotech), numbers (biss_rate_change, lfa/ae/n2k_budget_change, set_aside_requirement, organic_area_target, surplus_cut, pesticide_reduction, carbon_tax, biofuel_mandate, eco_scheme_budget_pct, milk_quota, sugar_quota), codes/maps (coupled_support, premium_factor_regional, tariff_changes, trq_volume_changes, mineral_redu) | greendeal_scenarios.gms l. 66-67 (negative milk), minfert_redu_*.gms (mineral_redu), ghgTax/carbtax50 (carbon_tax), change_biof_mandate.gms, rd_logic.gms (RD budgets), organic_io.gms, pesticides.gms/conventional_io.gms | `pesticide_rule` default "jrc121368" (l. 146) differs from `surplus_rule` default "star3" (l. 108); eco_scheme 0.25 (reporting); milk/sugar quota fields (no caller found) |
| 2 | `_SUPPORTED` | capri_mod/policy/greendeal.py:44-50 | allowed values of lndscpTarg, orgTarg, pestRedu, surpRedu | GUI capri_gui_definition.xml (cited l. 45) | - |
| 3 | `_MINE_REDU`, `_NOT_IMPLEMENTED` | greendeal.py:52-53 | mineRedu codes; dietShift, othPol refused | GUI (l. 51) | refusal is the model's |
| 4 | `scenario_name()` | greendeal.py:61-71 | CAPRI result name | greendeal_scenarios.gms l. 191-193 (scenNameFromGroup, `greendeal_reference` for all zeros) | - |
| 5 | `greendeal_scenario()` | greendeal.py:74-121 | maps the 7 switches + surplus_rule, pesticide_rule, manure_trade, endotech to PolicyScenario; cross-checks l. 87-103 | landscape.gms, organic_area.gms, pesticides.gms, surptot.gms, minfert_*.gms (docstring l. 14-33) | the check "jrc121368 only with surpRedu 0/50" (l. 102-103) |
| 6 | `farm_to_fork_scenario()` | greendeal.py:124-137 | F2F as JRC121368: lnds10 org25 pest50 surp50, surplus/pesticide rule jrc121368, manure_trade False, endotech JRC121368; name `farm_to_fork_jrc121368` | Green Deal group switches | JRC121368 report settings (not CAPRI star 3.0 files) |
| 7 | `GREENDEAL_2030_TARGETS` | greendeal.py:145 | lnds8 org18 pest20 mine13crp surp30 | P. Witzke's batch, res_..._lnds8_org18_pest20_mine13crp_surp30 (comment l. 140-144; file not cited) | - |
| 8 | `GREENDEAL_2040_TARGETS` | greendeal.py:147 | lnds10 org25 pest32 20crp surp50 | same batch | no caller found (grep) |
| 9 | `greendeal_2030_scenario()` | greendeal.py:150-155 | #7 + manure_trade True | batch settings (l. 143-144) | - |
| 10 | `STAR3_DEFAULTS` | capri_mod/policy/endotech.py:36-37 | 5 endotech settings | refpol_endotech_all_sup.gms l. 109, 130, 137, 143 (verified); fixGenetToIni from breeding.gms l. 65-77 (cited) | duplicate of defaults.toml [endotech] (#21) |
| 11 | `JRC121368_ENDOTECH` | endotech.py:39-40 | ghgTechMYld 0.2, rest as #10 | ecampa/refpol_endotech_set14_ini.gms (cited) | - |
| 12 | `effective()` | endotech.py:45-55 | precedence: settings [endotech], then overrides | mirrors `$if not SETGLOBAL` | - |
| 13 | `baseline_scenario()` | capri_mod/scenarios/scenarios.py:39-44 | empty PolicyScenario "BASELINE" | - | model's |
| 14 | `climate_policy_scenario()` | scenarios.py:47-49 | alias of #16 | - | no caller found |
| 15 | `set_aside_10_scenario()` | scenarios.py:63-72 | set_aside_requirement 0.10 | cites scen/set_aside/set_aside_10.gms, which sets `DATA(RUNR,GRCU,"SETR",SIMY)=10` (l. 16: 10% set-aside of grandes cultures). The field is used as the landscape floor `(set_aside_requirement/0.10) x landscape_target_pp x UAA` (supply_module.py:1092). **Equivalence not determined; looks like a different instrument.** | used by test_capri.py:1415 |
| 16 | `carbon_tax_scenario()` | scenarios.py:75-85 | carbon_tax EUR/t | ecampa/carbtax50_endotech_set12.gms l. 70 (ghgTax on), l. 214-226 (p_carbonTax = 50 x shift 1); that file includes pol_input\mtr_rd.gms (l. 57), not the Green Deal reference | the model runs it on the Green Deal reference trajectory |
| 17 | `SCENARIO_REGISTRY`, `get_scenario`, `list_scenarios` | scenarios.py:56-58, 88-98, 101-105 | name -> factory: BASELINE, SET_ASIDE_10PCT, CARBON_TAX_100, CARBON_TAX_50 | - | CARBON_TAX_100 has no CAPRI file cited |
| 18 | run_f2f_2030.py scenario assembly + CLI overrides | tools/run/run_f2f_2030.py:141-176 | `--scenario` f2f/greendeal/greendeal2030/carbontax; `--targets`; "f2f with other targets" splices 6 fields of a greendeal scenario into F2F (l. 151-157); flags override fields (l. 159-176) and rename (l. 169-172) | - | all model's |
| 19 | ad hoc scenarios in scripts | tools/run/run_vcs_2030.py:117-118 (WITHOUT_VCS, premium factors computed at run time from CAPRI files, l. 49-86); tools/run/run_policy_comparison.py:82-86 ("F2F" from CLI floats 0.5/0.25/0.10, l. 61-63; CAPRI_F2F targets l. 40); tools/check/milk_shock_check.py:25 (carbon tax 0); tools/check/check_regression.py:134 | VCS: cap_after_2014 without VCS (CAPRI results capri_vcs_effect.csv.xz) | run_policy_comparison's F2F is the old proxy shape |
| 20 | defaults.toml scenario settings | capri_mod/settings/defaults.toml:11-12 (run.manure_trade), 142 (supply.jrc_capped_override), 261 (market.biofuel_markets), 355-363 ([endotech]) | settings that "hold for a scenario and its baseline" | refpol_endotech_all_sup.gms | - |
| 21 | jrc121368 parameters | capri_data/codes/model_parameters.csv:32-34 (PESTICIDE_YIELD_LOSS_AT_50PCT 0.1, JRC_CAPPED_N_REGIONS 9, JRC_CAPPED_CUT 0.36) | numbers of one scenario variant | - | JRC121368 report |
| 22 | Green Deal CAPRI parameters | model_parameters.csv:49-55 (ORGANIC_TARGET_REF_PCT, ORGANIC_OUTLOOK_PCT, ORGANIC_SMALL_MINE_KG_HA, ORGANIC_LIMCRES_FACTOR, ...) | numbers of the Green Deal group files | load_organic_targets.gms l. 174-183, organic_minfert_redu.gms l. 51, 115-116 (cited) | - |
| 23 | Green Deal datasets | capri_data/2017/policy/landscape_targets_ms.csv, organic_targets_ms.csv, capri_baseline_surplus_2030.csv; capri_data/sources/raw/capri/dat/policy/minfert_redu_by_crop_*.csv | per-member-state targets, baseline surplus | landscape_targets.gdx, organic_targets*.gdx (pol_input/greendeal) | - |
| 24 | `CAPRIModel.run` scenario arguments | capri_mod/model.py:263-278 | `scenario` (registry name), `custom_scenario`, `world_price_shock`, `carbon_price` (added to scenario's, l. 476), `biofuel_output_scale`, `endotech`, `manure_trade`, `biofuel_markets` | - | shocks given as call arguments, not in the scenario object |

### 1.3 How a run selects a scenario

| Layer | Mechanism | file:line |
|---|---|---|
| run_mini_eu.py | `--scenario` (default f2f) passed through to run_f2f_2030.py with `--regions` (20 units) | tools/run/run_mini_eu.py:52, 56-57 |
| run_f2f_2030.py | `--scenario {f2f,greendeal,greendeal2030,carbontax}`, `--targets k=v,...`, `--trajectory` (capri_ref/captrd/folder), `--endotech`, `--carbon-tax`, `--surplus-rule`, `--pesticide-rule`, `--mine-redu`, `--(no-)manure-market`, `--(no-)biofuel-markets`, `--biofuel-mandate`, `--capped-regions`, `--settings`, `--set`, `--base-prices` | run_f2f_2030.py:41-85; trajectory folder l. 127-128; scenario l. 141-176 |
| ProjectionModule.run | `policy_scenario` object: copies its endotech, manure_trade, biofuel_markets into the **baseline's** run kwargs, runs `pm.run(scenario="BASELINE")` then `pm.run(custom_scenario=...)` | capri_mod/projection/projection_module.py:392-438 |
| CAPRIModel.run | `custom_scenario` wins over `scenario` name (registry) | model.py:316-320; manure/biofuel precedence l. 321-331 |

So today the "reference" of a run is not a named object: it is BASELINE plus whatever reference-level settings the
scenario object carries (projection_module.py:424-434).

---

## 2. Proposed capri_data/scenarios/<name>/

### 2.1 CAPRI's inheritance (pol_input/greendeal)

| Step | GAMS | Line |
|---|---|---|
| scenario file names its reference and includes it | greendeal_scenarios.gms | l. 58 `$setglobal refScenMain pol_input\greendeal\refpol_endotech_all_sup`, l. 60 `$include %refScenMain%.gms` |
| reference: defaults that launch-time values override | refpol_endotech_all_sup.gms | l. 97, 109, 130, 137, 143 (`$if not SETGLOBAL x $SETGLOBAL x default`) |
| reference includes the policy file | refpol_endotech_all_sup.gms -> greendeal/ref.gms -> cap_after_2014/ref.gms | l. 396; ref.gms l. 23 |
| alternative reference | greendeal/baseline.gms | l. 24 (includes refpol_endotech_all_sup) |
| scenario shocks read the reference's **results** | greendeal_scenarios.gms | l. 108-123 (`p_baselineDataout` from `res_..greendeal_ref`) |
| switch -> file | greendeal_scenarios.gms | l. 132, 140, 145, 150-164, 171, 179, 184 |
| other group with its own reference chain | ecampa/carbtax50_endotech_set12.gms | l. 57 (`$include pol_input\mtr_rd.gms`), l. 70, 214-226 |

So CAPRI inherits by include (scenario > reference > policy baseline), with launch-time settings winning. Proposed
resolution order: defaults.toml < reference settings.toml < scenario settings.toml < run's `--settings`/`--set`.

### 2.2 Layout

```
capri_data/scenarios/
  <reference>/            kind = "reference" (e.g. ref_greendeal_star3, ref_jrc121368)
    settings.toml          [scenario] [settings] [endotech]; trajectory = "capri_ref_2030"
  <scenario>/             kind = "scenario" (e.g. farm_to_fork_jrc121368, greendeal_lnds8_..., carbontax_50)
    settings.toml          [scenario] reference = "<reference>"; [greendeal] / [shocks]; [settings]
    premium_factors.csv    region,activity,factor             (premium_factor_regional; VCS)
    coupled_support.csv    activity,value                     (unit not determined: policy_module.py:347-350)
    tariff_changes.csv     region,commodity,change_pct
    trq_volume_changes.csv commodity,change_kt
    world_price_shock.csv  commodity,relative_change          (today a run() argument)
    biofuel_output_scale.csv biofuel,factor                   (today a run() argument)
  capri_ref_2030/, captrd_2030/, null/   trajectories as now (kind = "trajectory")
```
A CSV is written only when the scenario has rows. Percentages stay CAPRI's integers in TOML (lndscpTarg = 10); the
model divides by 100 as greendeal.py:109-114 does (exact: x/100 is correctly rounded, same double as the literal).
Group datasets (#22, #23) placement: open question Q4.

### 2.3 pydantic models (decided 2 November 2026; scope ARCHITECTURE_REFACTOR.md l. 96-99)

| Model | Fields | Cross-field checks |
|---|---|---|
| `Endotech` | ghgTechMYld, ghgTechFEff, ghgTechLowNFeed, ghgTechLineNitr, fixGenetToIni: float \| None (extra forbidden) | keys = STAR3_DEFAULTS (endotech.py:312-313 today) |
| `GreenDeal` | lndscpTarg, orgTarg, pestRedu, surpRedu: Literal of `_SUPPORTED`; mineRedu: Literal of `_MINE_REDU`; dietShift, othPol: Literal[0]; surplus_rule, pesticide_rule: Literal["star3","jrc121368"]; negative_milk_price: bool = True | jrc121368 surplus rule => surpRedu in {0,50} (greendeal.py:102); dietShift/othPol != 0 refused |
| `Shocks` | carbon_tax >= 0, biofuel_mandate: float \| None, biss_rate_change, lfa/ae/n2k_budget_change (> -1), eco_scheme_budget_pct in [0,1], milk_quota, sugar_quota | biofuel_mandate set => effective biofuel_markets true (policy_module.py:116-118 "acts with endogenous biofuel markets") |
| `ScenarioDef` | name, kind: Literal["reference","scenario"], description, reference: str \| None, trajectory: str \| None, capri_files: list[str], manure_trade, biofuel_markets: bool \| None, endotech: Endotech, greendeal: GreenDeal \| None, shocks: Shocks, settings: dict (overlay) , files: names of the CSVs present | name == folder name; kind=scenario => reference given, exists and is kind=reference; kind=reference => no shocks, trajectory exists; greendeal given and name not overridden => name == scenario_name(...); settings keys exist in defaults.toml (delegated to the settings layer, which already checks); CSV region/activity/commodity codes in the model's sets (needs the data: checked at load, before the run) |
| `HessianRecord` | source: Literal["cache","computed","failed"], file, products, prices_shocked, columns_with_response, seconds, base_resolve_max_dev_kt, method, kkt_ipopt_solves, regions_skipped, regions_shocked, at_iteration, error | source=failed <=> error set (keys from coupling/hessian.py:56, 170-171, 337-345; model.py:730-735) |
| `RunManifest` | created, seconds_recorded, git{commit,branch,data_tree,changed_files}, software, environment, command, inputs{path:{sha256,bytes}}, external_inputs | (capri_mod/run_manifest.py:126-137) |
| `ResultsMeta` | scenario, reference, run_id, trajectory, years, regions subset, conv, it, base_iterations, market_converged, nlp_nonoptimal, nlp_fallback, nlp_relaxed, capri_stop, pmp_source, settings_changed, hessian: list[HessianRecord] | regions subset => flag "not comparable with a full run" (compare_runs.py:96-103) |

pydantic is installed (2.13.5) but **not declared** in pyproject.toml (no match).

---

## 3. Results today

### 3.1 The run pickle (tools/run/run_f2f_2030.py; run_mini_eu.py writes none itself, it calls run_f2f_2030.py, l. 56-58)

Written at l. 469 (`pickle.dump(out, ...)`), with OUT.settings.toml (l. 470) and OUT.manifest.json (l. 471-472) beside;
OUT_dump.pkl only with CAPRI_DUMP_REGIONS (l. 447-467, diagnostics).

Top-level keys: dict literal l. 255-443 has 36 keys of which `biofuel` (l. 264, 296) and `fert_dist` (l. 266, 298) are
written twice with the same expression (the later wins); plus `eu_premium` (l. 445): **35 distinct blocks**; `meta` has
22 keys (l. 408-443) plus `run_manifest` (l. 468).

| Block | line | Content | Long-table mapping (region, dim5, cols, rows, point) | Fits |
|---|---|---|---|---|
| prices | 255 | EU27 domestic price ratio s/b - 1 | derived: store domestic prices per region (eu_regions) | derived |
| act | 256 | EU27 sums of activity levels (b, s) | derived from act_regional | derived |
| out | 257 | EU27 gross output sums | region, -, activity, gross_output item | yes (store regional) |
| prod | 259 | EU27 production of 6 commodities | EU27, -, product, PROD | yes |
| environmental | 261 | env DataFrame per region (b, s) | region, -, -, indicator | yes |
| biofuel | 264/296 | MarketEquilibrium.biofuel object | structure not determined | partly |
| fert_dist | 266/298 | records list | region, source, crop group, item | yes |
| dairy | 269 | EU27 dairy production | EU27, -, product, PROD | yes |
| dairy_block | 275 | market.dairy object | not determined | partly |
| adoption, adoption_base | 276 | EU shares by technology | EU27, -, tech, SHARE | yes |
| histosol | 281 | two scalars | EU27, -, FALLOW, fallow/eligible | yes |
| endotech | 288 | settings | -> ResultsMeta / settings.toml | **no** |
| scenario_settings | 289 | settings | -> ResultsMeta | **no** |
| base_market, scen_market | 301, 308 | EU27 prod/cons/net_exports/price/world | EU27 or WORLD, -, product, item | yes |
| welfare | 317 | market and supply welfare tables | region, -, component, item | yes |
| outer_history | 323 | per-iteration records | iteration series | **no** (separate table) |
| raw_milk | 326 | per member state MILK prod, price | region, -, MILK, item | yes |
| eu_regions | 333 | per EU region prod/cons/price | region, -, product, item | yes |
| eu_block_flows | 338 | bilateral flows inside the EU | needs a partner region (dim5) | yes with dim5 |
| adoption_lu, genetics, lownfeed, supplements, dairy_split, cattle_split | 341-380 | EU aggregates by option | EU27, -, option, item | yes |
| labour, set_aside | 381, 383 | EU totals | EU27, -, -, item | yes |
| cover_crops | 385 | EU totals | EU27, -, crop, item | yes |
| act_regional | 389 | region x activity levels (b, s) | region, -, activity, LEVL | yes |
| regional | 391-405 | per region: lam, fert shares, amm tech shares, duals, manure_trade tuple, land_types, n_target_relaxed (bool), shortfall tuple, manure_pool_price | region, tech/dual, activity, item | mostly (bools as 0/1; tuple positions not determined) |
| manure_trade_base | 406 | per region tuple | region, -, -, item | yes |
| meta | 408-443 | convergence, options, settings, Hessian record and log, stop rule, fallbacks | -> ResultsMeta JSON | **no** |
| meta.market_supply_hessian(_log) | 414-417 | Hessian record(s) | -> HessianRecord | **no** |
| meta.run_manifest | 468 | manifest | -> manifest.json | **no** |
| eu_premium | 445 | EU premium by product | EU27, -, product, premium item | yes |

Row/column codes: the pickle uses the model's names; whether to translate to CAPRI codes is Q3.

### 3.2 capri_mod/io_results.py today

`flatten_outputs` (l. 49) gives one flat record per run (prices, production, env totals); `Experiment` (l. 167-264)
writes outputs/<experiment>/runs/<run_id>/*.csv + summary.json + batch_summary.csv; `load_experiment` (l. 267),
`save_results` (l. 285), `_write_market` (l. 297), `_write_supply` (l. 314). Callers: `flatten_outputs` in
projection_module.py:543 and tests test_p_balance.py:180, test_norway_market.py:255. **No caller of Experiment or
save_results found** in capri_mod/ or tools/. Not used by run_f2f_2030.py, run_mini_eu.py or compare_runs.py.
.gitignore has no entry for results/ or outputs/.

### 3.3 Readers of run pickles

| Reader | line | Keys used |
|---|---|---|
| tools/check/compare_runs.py | 83 | act, out, prod, prices, environmental, adoption*, genetics, lownfeed, supplements, dairy_split, cattle_split, labour, set_aside, cover_crops, histosol, meta (options, run_manifest) |
| tools/check/compare_pickles_exact.py | 81 | every path (the refactor gate) |
| tools/check/compare_outlook_2030.py | 95 | act, out, prod, base_market |
| tools/check/compare_baseline_capri.py | 115 | act, base_market |
| tools/check/diag_region_balance.py | 21 | act_regional, environmental, regional |
| tools/check/k79_trace.py | 56 | act_regional, outer_history, meta |
| tools/check/k79_multistart.py | 42 | act_regional (l. 36 reads a dump) |
| tools/run/run_mini_eu.py | 64 | act_regional |

Not run pickles: diagnose_fert_dist.py:122 (fert-dist dumps); test_capri.py:3384, 4136, 4176, 4202 (NLP dumps,
CAPRI_NLP_DUMP); test_supply_state.py:52, test_env_coupling_state.py:61 (in-memory round trips). **No test reads a run
pickle.**

### 3.4 Proposed long table (CAPRI's DATAOUT(rall, dim5, cols, rows, year): capmod/set_and_store_dataout.gms l. 53-64; CAPRIunits.gms l. 420)

| Column | Type | Note |
|---|---|---|
| scenario | string | partition |
| run_id | string | partition (e.g. timestamp + short commit) |
| region | string | CAPRI region code or EU27/WORLD |
| dim5 | string | "" by default (CAPRI's empty); tech, source or partner region where needed |
| cols | string | activity, product or option |
| rows | string | item |
| year | int16 | 2017 base, 2030 ... |
| point | string | "base" (the reference solved in this run) or "scen" (Q1) |
| value | float64 | |

Not in the table: outer_history (own table `iterations`: scenario, run_id, point, iteration, key, value),
meta, Hessian records, run manifest (JSON beside, pydantic). Beside each partition: settings.toml, manifest.json,
meta.json.

### 3.5 deltalake

Installed: deltalake 1.6.6. Declared only in the `pipeline` extra: pyproject.toml:27 (`deltalake>=0.18`); not in
`dependencies` (l. 12-19). Existing writer to reuse: capri_mod/pipeline/store.py:32-42 (`write_deltalake`, mode append).
**Conflict:** capri_mod/tests/test_market_layers.py:35-41 fails if any non-pipeline module imports deltalake; it must be
reworded (writing results allowed, reading inputs not) when io_results.py starts writing Delta.

---

## 4. Proposed order (each pure move checked by an exact mini-EU run: compare_pickles_exact.py against the reference pickle, ignoring meta.seconds, meta.options, meta.run_manifest)

| Step | What | Kind | Check |
|---|---|---|---|
| 0 | Mini-EU reference pickle of HEAD (f2f and greendeal2030) | - | baseline for every step |
| 1 | Declare pydantic and deltalake in `dependencies`; amend test_market_layers.py:35; .gitignore results/ | none | test suite |
| 2 | pydantic `ScenarioDef` etc. in code; a test that builds today's 6 objects (#5, #6, #9, #13, #15, #16) through them and compares PolicyScenario field by field | pure | unit test, no run |
| 3 | Write the scenario folders (references + f2f, greendeal default, greendeal2030, carbontax_50/100, set_aside_10, baseline); loader `scenarios.load(name) -> PolicyScenario`; registry reads folders | pure | unit test: loader == factory |
| 4 | run_f2f_2030.py `--scenario <folder>` (old names mapped); flags become a settings overlay of the scenario | pure | mini-EU exact (f2f, greendeal2030) |
| 5 | Reference-level settings (endotech, manure_trade, biofuel_markets) read from the reference folder instead of copied from the scenario (projection_module.py:424-434) | pure if values equal | mini-EU exact |
| 6 | Remove factories #5-#9, #13-#17 (keep scenario_name for naming); update 42 test references (grep count of factory names in capri_mod/tests) | pure | suite |
| 7 | Run-time shocks (world_price_shock, biofuel_output_scale, carbon_price) as scenario CSV/fields | pure | mini-EU exact + unit tests |
| 8 | `ResultsMeta`, `HessianRecord`, `RunManifest` validate what is written today | pure | mini-EU exact |
| 9 | io_results.to_long(out) from the pickle dict; inverse check: compare_runs indicators from the long table == from the pickle | pure | on an existing mini-EU pickle, no run |
| 10 | Delta writer (results/, partition scenario/run_id) + settings.toml, manifest.json, meta.json beside; run_f2f writes both | additive | mini-EU: Delta rows == pickle values |
| 11 | compare_runs.py, run_mini_eu.py, compare_pickles_exact equivalent read Delta; pickle behind `--pickle` (cache) | pure | gate compare on Delta = on pickle |
| B1.. | Behaviour changes, each separate and gated: SET_ASIDE_10PCT semantics; carbon tax on its own reference; captrd name fix; group data move if it changes reads; run_policy_comparison F2F removed or redirected; storing regional instead of EU aggregates if any sum changes | behaviour | own gate run |

---

## 5. Risks and open questions

Risks
- Exactness: EU aggregates (act, out, adoption) summed in a different order from a long table can differ in the last
  bit; keep the pickle-derived aggregates until step 11 compares them.
- Dict order: premium_factor_regional, tariff_changes and endotech are iterated; CSV order must reproduce the
  insertion order the factories give (affects exactness only where order matters; not determined where it does).
- Reference cache: the baseline cache is keyed by endotech settings (endotech.py docstring l. 10-12); moving those
  settings to reference folders must keep the key.
- CLI flags rename the scenario (run_f2f_2030.py:169-172); with folders, an overridden scenario no longer equals its
  folder: the partition name must then carry the override (or overrides be refused).
- `pesticide_rule` default "jrc121368" in the dataclass (policy_module.py:146) while greendeal_scenario's is "star3"
  (greendeal.py:78): a folder without the field would silently change PolicyScenario-built scenarios (VCS, carbon tax:
  pesticide_reduction 0 there, so no effect; not determined for others).
- test_market_layers.py:35 blocks deltalake outside the pipeline (3.5).
- Delta partitions are append-only; a re-run with the same run_id needs a rule (overwrite partition or refuse).

Open questions for the project lead
1. Point encoding: one partition per run holding base and scen (point column), or CAPRI's way, the reference stored
   as its own scenario partition and scenarios carrying only their own solution (greendeal_scenarios.gms l. 108-123
   reads the reference's results file)? The second avoids duplicating the reference across scenarios.
2. References: F2F (JRC121368 endotech, no manure trade), the star 3.0 Green Deal group and the carbon tax
   (ecampa chain, carbtax50_endotech_set12.gms l. 57) have different CAPRI references. One reference folder per chain,
   or one reference for all (today's practice: one trajectory, capri_ref_2030)?
3. Codes in the long table: CAPRI's row/column codes (LEVL, PROD, ...) with a mapping table, or the model's names now?
   And are EU aggregates stored, or recomputed by the readers from regional rows?
4. Where do the Green Deal group's data live (landscape_targets_ms.csv, organic_targets_ms.csv,
   capri_baseline_surplus_2030.csv, minfert sources, model_parameters.csv rows 32-34 and 49-55): a group folder
   (capri_data/scenarios/_groups/greendeal/), each scenario folder, or where they are?
5. Fate of the non-CAPRI or unclear definitions: SET_ASIDE_10PCT (cites set_aside_10.gms but applies the landscape
   floor), CARBON_TAX_100 (no file), run_policy_comparison.py's F2F proxy, WITHOUT_VCS (store its computed factors as
   premium_factors.csv or keep computing them), GREENDEAL_2040_TARGETS (unused), and whether CLI overrides of a
   scenario stay allowed.

## Decisions (the project lead, 3 November 2026)

1. **Base and scenario storage**: CAPRI's way. The reference run is stored once, as its own partition; a scenario's
   rows point to it by run id. A run whose reference has the fingerprint (settings, data, code) of a stored one is
   checked identical to it and points to it; a different fingerprint stores a new reference partition.
2. **References**: one folder per CAPRI reference (Farm-to-Fork as JRC121368 ran it, the Green Deal group, the carbon
   tax), each scenario naming its own; starting with those whose data are in hand (the Green Deal's capri_ref_2030).
   Whether the carbon tax's reference (CAPRI's mtr_rd.gms policy file) can be built is to be checked; until then that
   scenario is marked as running on another reference.
3. **The long table**: both codes, CAPRI's (LEVL, PROD, ...) and the model's, from the crosswalk tables; the EU totals
   the model computes are stored, not recomputed by the readers.
4. **Green Deal data**: in each scenario's folder; refined the same day: once per group or reference (capri_data/scenarios/greendeal_group/, the 2030 baseline surplus beside its trajectory in capri_ref_2030/), as CAPRI's group files are included by every scenario of the group (step 4, commit c799397).
5. **Uncertain definitions**: the 10% set-aside as CAPRI's rule, 10% of the grandes cultures area (GRCU), a behaviour
   change in its own commit and run; the EUR 100 carbon tax removed, CAPRI's carbtax50_endotech_set12.gms with its
   reference to replace it once its data are confirmed; the ad hoc Farm-to-Fork of run_policy_comparison.py removed (the
   script uses the scenario folder); WITHOUT_VCS as a rule in its folder (the premium types set to zero, as CAPRI's
   scenario file), its factors computed at run time; GREENDEAL_2040_TARGETS removed; command-line flags still allowed
   but no longer renaming the scenario, each override recorded in the run's metadata and settings file and part of the
   run id.

## Status (3 November 2026, night)

Done (each mini-EU run identical to the one before, meta apart):
- Steps 1-5: dependencies; scenario folders and their pydantic definitions; the run script reads folders; the Green
  Deal group's data held once; users' own scenarios (python -m capri_mod.scenarios new / check; README 6.4).
- The long results table (capri_mod/io_results.py): to_long, with_capri_codes, write_run, read_run; the run script
  writes it after the pickle and checks the pickle's blocks against it (exact). Layout and storage as decided (CAPRI's
  DATAOUT dimensions; the model's and CAPRI's codes; the reference stored once, reused on the same fingerprint and
  rows; the EU totals the run script computes stored).
- CAPRI's codes (capri_data/codes/results_items.csv: every item declared; a CAPRI code only where checked against
  CAPRI's code and its 2030 results, with the source): activity levels (LEVL), crops' gross output (GROF of the
  product; not GRAS, another measure; not the animals), market production (PROD), market price (PMRK), bilateral
  flows (ImportQ), labour (GROF.LABT/LABF/LABP), set-aside VSET and FALL (LEVL), the market welfare totals (EAAG.CSSP,
  PROFITPROC, PROFITDAIRY, PROFITFEED, TARIFFREV, TRQRents), enteric and manure CH4, crop residue and histosol N2O,
  liming CO2 (ImpactGwp), the 36 land-use transitions (LEVL).
- Not mapped, with the reason: manure and soil N2O, indirect N2O and the GHG totals (they group CAPRI's positions
  otherwise: the model's manure N2O is N2OMAN + N2OAPP), leaching N2O (the housing runoff is not in it), NH3 (scope
  and unit not confirmed), feed (a total per model animal, CAPRI's per head of its own activities), the market's
  consumption and net exports and the supply models' welfare (the CAPRI results file at hand, res_2_1730greendeal_
  refpol_endotech_all_inidefaulta, has no market regions nor regional welfare totals), the model's own diagnostics.
- The run's metadata declared (capri_mod/run_meta.py: ResultsMeta, HessianRecord, RunManifest; extra keys refused),
  validated by the run script after the pickle is saved; accepts every mini-EU run since stage 4 and gate runs 15.
- The run script's EU summaries and both outer-iteration records stored beside the long table as exact records
  (root/summary, root/iterations); load_store rebuilds the whole pickle (metadata apart) and the run script checks it
  against the pickle at tolerance zero; the check tools read store:ROOT:SCENARIO[:RUN_ID]. The pickle stays the run's
  file until the gate has run on the store.
- Decision 5, part: CARBON_TAX_100 and GREENDEAL_2040_TARGETS removed; run_policy_comparison.py runs a folder;
  command-line overrides recorded (meta.scenario_overrides, run id -ov<hash>), no longer renaming the scenario.

Decided by the project lead the same night (both ports in MODEL_CONTENT_PLAN.md §12a, to schedule): SET_ASIDE_10PCT
removed (commit 3120071); WITHOUT_VCS not a scenario folder, tools/run/run_vcs_2030.py kept as a validation test.
The analysis:
1. **The 10% set-aside as CAPRI's rule.** CAPRI's SETA_ (supply/supply_model.gms l. 2219-2241): sum of the arable
   activities' levels x (1 - NONS) x r / (1 - r) = the obligatory set-aside activities (setaPact: ISET, GSET, TSET and
   NONF); set_aside_10.gms sets r = 10 on GRCU (cereals, oilseeds, MAIF, pulses) and eps on VSET, so voluntary
   set-aside and fallow do not count. The model has no obligatory set-aside activity (its SETA is VSET + FALL), so
   CAPRI's rule needs a new supply activity with its premium and costs (and CAPRI's PMP terms of define_const_pmp_
   param.gms l. 44-76 when the obligation binds at calibration).
2. **WITHOUT_VCS as a rule.** CAPRI's scenario sets the coupled-support premium types to zero and its premium module
   moves the envelope into the decoupled payment (cereal premiums +9 to +11%). The model's premium data hold Pillar I
   as one share (premium_scheme_shares_2030.csv DPPIL1, no coupled-support part), so the rule needs CAPRI's
   coupled-support part of each premium and the redistribution.
