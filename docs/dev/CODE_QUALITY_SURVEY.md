# Code quality plan: the parts that change no code (24 November 2026)

The survey the code quality plan (docs/dev/CODE_QUALITY_PLAN.md, section 10) gives a separate session before the
assignments refactor is in dev: step 1's search for where results depend on the hash order, step 4's list of the
former-form settings, step 5's classification of the broad `except` paths, and the syntax-tree check tool. Measured on
dev at 3dad0e7 (branch quality/no-code-steps). Nothing here changes the model's code; the fixes are the plan's later
batches, the lists the project lead's to decide.

## 1. Step 1: where results depend on the hash order

### The scan

Every place in capri_mod (tests left out) where code iterates in a set's order: a loop or comprehension over a set
expression (set(...), a set literal or comprehension, a union, difference or intersection of sets) or over a name
assigned one in the same function, and a set handed to list, tuple, dict, sum, np.array, enumerate, zip, join or
the like. Not counted: sorted(...) of a set, membership tests, len, set-to-set operations, any/all. A set of strings
iterates in the hash order, which PYTHONHASHSEED changes; whether the order matters depends on what the loop does
(a float sum, a dictionary's order read later, a first match), which the scan cannot tell.

- **130 places in 34 modules**; 81 of them in capri_mod/pipeline/captrd (the CAPTRD pipeline, which builds the trends offline and is not part of a model run; its estimation already sorts its sets, CHANGELOG, but its other modules iterate sets too: globiom.py 19, national_supports.py 13, prepare.py 8, aglink.py 7, longrun_supports.py 7 and others; a pass of their own, with the pipeline's parity tests), **49 in the model's own modules**:

| module | places | what the loops do (by reading) |
|---|---|---|
| policy/rd.py | 13 | regions, measures and land covers of the RD chain; its whole output was equal under seeds 0 and 7 (the assignments refactor, A6) |
| policy/mtr.py | 12 | schemes, member states and years of the MTR chain |
| supply/ghg_tax.py | 3 | activities and technologies of the emission tax's coefficients |
| environmental/ghg.py | 2 | the manure N2O technologies' shares (a dict built in the set's order) |
| feed/equations/req_or_man_fnc.py | 2 | the main session's open port (not touched) |
| policy/premium_response.py | 2 | units; the weighted levels by key |
| run_manifest.py | 2 | the manifest's software list and the paths left out (no numbers) |
| policy/premium_cut.py | 2 | units and schemes of the premium cut |
| market/welfare.py | 2 | the processing products and regions of the welfare terms |
| supply/livestock.py | 2 | the young animals' goods |
| policy/declared.py | 1 | a float sum over the units below a region: `sum(... for u in set(below))` |
| feed/equations/fedtrm_cal_pw.py | 1 | the main session's open port (not touched) |
| feed/equations/req_or_man_fnc_req.py | 1 | the main session's open port (not touched) |
| policy/cap14_premiums.py | 1 | the domains of the CAP 2014 edits (sets of codes) |
| projection/prices.py | 1 | the activities of the 2030 price file |
| supply/capri_pmp.py | 1 | the activities of the elasticity table |
| utils/capri_stop.py | 1 | the aggregates' rows of the stop rule's prices |

A float accumulated in a set's order changes in its last digits between seeds; a dictionary built in a set's order and
read later in its order (a matrix's columns, a sum over the dictionary) carries the order on; a non-convex regional
solve can turn the last digits into another local optimum (the 0.2% and the Dutch laying hens' 10-20% between seeds in
CHANGELOG). The list of the places with the code: section 5 below (the scan's file).

### The mini-EU runs under two seeds

tools/run/run_mini_eu.py's 20 units, the Farm-to-Fork scenario, on dev at 3dad0e7, under PYTHONHASHSEED 0 and 1, one
after the other and alone on the machine (run_f2f_2030.py re-starts itself with seed 0 unless the variable reads "0",
so the runs were started by a wrapper that keeps the interpreter's seed and sets the variable to "0" in the process;
the wrapper is not in the repository). Both converged in 8 iterations (the baseline in 2).

- **Not identical:** 2,974 values differ at `--rtol 0` (compare_pickles_exact.py), 669 at 1e-12. Small here: at most
  about 2e-7 relative in the results (PT18's manure options' shares, NO08's duals, the young-animal imbalance), prices
  in the 14th digit; the largest relative figure, 2.9% in the scenario's environmental table, is a manure net export
  of +-1.5e-11 (zero). The full EU's 0.2% (CHANGELOG) comes from regions that turn a last digit into another local
  optimum, which these 20 units do not.
- **The baseline's results are identical** (activity levels, the environmental table): only four adoption shares of
  its report differ (NITR_INH, PRECFARM, NITR_INH_MAN, VRT_SRUC), a report's sum in a set's order.
- **The scenario's first iteration is identical**, its market result too. **The first difference is in the second
  iteration's regional supply solves**: their inputs as recorded (the price signal, the first iteration's market
  result) are equal to the bit, their results are not (the EU herds of outer_history, 1e-15 relative; the regional
  herds there are rounded to 4 decimals, model.py, so they cannot name the region). The place therefore acts inside
  the regional solves from the second iteration on. Of the scan's places, those that act from then: the young
  animals' price ratios (supply/livestock.py l. 79, a loop over a union of sets), CAPRI's premium response
  (policy/premium_cut.py l. 117-118, policy/premium_response.py l. 112 and 151, sets of units and schemes) and the
  member states' milk signal.
- **Next (batch A, a code change):** the second iteration's regional results compared exactly, region by region (an
  unrounded record), to name the region and the step; then the fix in the plan's form (a fixed order) and the three
  seeds.

## 2. Step 4: the former-form settings

From capri_mod/settings/defaults.toml (248 keys, each with its comment) and docs/dev/SETTINGS_INVENTORY.csv: the
settings whose other value is a form the model had before a fix ("capri-mod's form until then", "the default before",
"the former default"). Their uses: a search of the tests, tools, scenarios, settings files and docs for the key with
the former value. For the project lead to decide (the plan: no removal before).

| setting | default | former form | since | still set by |
|---|---|---|---|---|
| outer_loop.price_update | capri | "adaptive" (the model's step) | 26 October 2026; DEPARTURES "Switched to CAPRI's setting" | none ("kept as an option", the user's decision of 26 October) |
| outer_loop.stop_rule | capri | "capri-mod" (the model's tests) | 28 October 2026 (K79); DEPARTURES "Switched" | none |
| outer_loop.manure_pool_price_update | capri | "damped" (the default 11-12 November) | 12 November 2026 | none |
| outer_loop.manure_pool_form | capri | "schedules" (the default before; DEP-17) | 12 November 2026 | none; needs supply.manure_trade_form "net" |
| supply.manure_trade_form | capri | "net" (until 17 November) | 17 November 2026 | none; the "schedules" pool form needs it |
| supply.manure_base_trade | capri | "shares" (until 17 November; K167) | 17 November 2026 | none |
| supply.price_transmission | capri | "relative" (until 17 November; K169) | 17 November 2026 | none |
| supply.cover_crop_requirement_area | capri | "filled" (until 18 November; K170) | 18 November 2026 | **test_capri.py:3053** (test_cover_crop_requirement_and_winter_cover_row) |
| supply.greendeal_winter_cover | capri | "option" (until 18 November; K170) | 18 November 2026 | none |
| supply.reference_winter_cover | capri | "option" (until 20 November; K188) | 20 November 2026 | none |
| supply.catch_crop_biofix_area | capri | "increment" (until 24 November; K204) | 24 November 2026 | none |
| supply.use_cattle_member_splits | true | false ("the former default, kept to compare") | 17 November 2026 (K65, DEP-4); DEPARTURES "Switched" | none |
| market.hessian_skip_unchanged | true | false (every region re-solved; "cached Hessians keep their keys") | 27 October 2026 | none (docs/dev/REFACTOR_SUPPLY_PARAMETERS_PLAN.md describes it) |

Not listed, with the reason:

| setting | why not a former form |
|---|---|
| outer_loop.manure_pool_trade_consts ("solution" / "capri") | the default is the departure (DEP-17), "capri" CAPRI's form |
| outer_loop.manure_pool_es_slope ("capri_code" / "capri_doc") | two readings of CAPRI's own parameter (its code and its documentation) |
| supply.pmp_source ("capri2030" / "recipe") | an option (the model's PMP terms by CAPRI's recipe); the settings module's docstring uses it as its example |
| supply.pmp_cross_terms ("capri" / "none") | an option (the diagonal only); not described as a former form |
| supply.premium_response ("capri" / "off") | an option (premiums fixed) |
| supply.fert_slope_with_saving (false) | a departure (DEPARTURES, "to be removed"; K77 open): the default is the former form, CAPRI's is the other value |
| environment.ammapp_sign, environment.ad_dairy_ch4, supply.organic_topup_at_fuel_cost, supply.greendeal_inputs_keep_tech_change, the captrd.*_as_coded switches and the other CAPRI-ERROR-FIX settings | documented departures (CAPRI-ERROR-FIX), kept by the plan |
| market.hessian_method ("kkt"), market.bounds, market.solver and the solver options | options beyond CAPRI or solver choices, not former forms |
| supply.greendeal_plap_crop_level_capri_step, supply.greendeal_plap_mix_capri_step | comparison switches of the project lead's decisions (DEP-51) |

Removing a listed setting removes its other branch from the code and the tests of that branch; supply.manure_trade_form
"net" and outer_loop.manure_pool_form "schedules" go together. The default runs do not change.

## 3. Step 5: the broad `except` paths

Every `except Exception`, `except BaseException` and bare `except` in capri_mod outside the tests, found by the syntax
tree: **65** (the plan's count, 66, came from a text search; the syntax tree finds 65, the difference not
looked into), each read with its try body and what follows it, and classed as the plan's step 5 says:

- **kept (24)**: it re-raises with what failed (11), or guards a diagnostic, a trace, an optional report or
  tool, the run manifest's audit hook (which must never raise), a cache, or it already warns and records the failure in
  the run's metadata (the market supply Hessian's two);
- **narrow (12)**: the handler is for a known exception (an import, a parse, a missing file of a partial copy, a cache key,
  a report field); naming it keeps the behaviour and lets the others through;
- **for the project lead (29)**: a fallback in a numerical path, a hidden proxy under the project's rule: 19
  silent (a value set to 0, None or empty with no warning: substitution factors, mineral rates, fertiliser options,
  duals, the capped regions, the young animals' response) and 10 that warn but leave no record in the run's
  metadata (a model element skipped: the manure technologies, the mineral fertiliser cap, the crop-need limit, a
  region's tax coefficients, CAPRI's stop rule's verdict). Each would raise, or warn and be recorded.

Whether a fallback fires in a run (the plan's temporary counter, from one mini-EU run) is batch B's, before a change.

| place | function | body | class | what it guards |
|---|---|---|---|---|
| coupling/feed.py:190 | _set_feed_demand | fallback | lead | the feed bulk price index set to None silently: the market's feed bulk prices |
| environmental/environmental_module.py:291 | compute_indicators | silent | lead | the accounts keep the base yields silently where the realised ones fail |
| environmental/environmental_module.py:448 | compute_indicators | warns | lead | warns; the inner fertiliser distribution left out of the accounts, not recorded |
| environmental/environmental_module.py:729 | run_all_regions | warns | lead | warns; the region left out of the indicator table, not recorded |
| environmental/nitrogen.py:340 | _residue_availability | fallback | lead | the residues' availability 0 silently |
| environmental/nitrogen.py:50 | _substitution | fallback | lead | the substitution factor None silently (read by the supply models' land, abatement and fertilisation) |
| feed/ration.py:302 | _contexts | fallback | lead | the rations' contexts empty when animal_numbers.csv is not read |
| model.py:1254 | _run_scenario | warns | lead | warns; CAPRI's stop rule not evaluated in an iteration, not recorded |
| model.py:253 | _ghg_coefficients | warns | lead | warns; a region's emission-tax coefficients missing, not recorded |
| supply/abatement.py:29 | _amm_context | warns | lead | warns; the manure technologies skipped for the region, not recorded |
| supply/abatement.py:659 | _manure_inhibitor_tax_value | fallback | lead | the inhibitor's manure N2O factor None silently (the tax value) |
| supply/fertilisation.py:759 | _crop_mineral_rate | fallback | lead | a crop's base mineral N rate 0 silently |
| supply/fertilisation.py:789 | _nitrate_row_term | fallback | lead | the nitrate row's substitution 0 silently |
| supply/ghg_tax.py:115 | ghg_coefficients | fallback | lead | the manure N2O technologies empty silently (the tax coefficients) |
| supply/land.py:322 | _land_augment | warns | lead | warns; the manure market's substitution replaced by the availability, not recorded |
| supply/land.py:425 | _land_augment | warns | lead | warns; the crop-need limit skipped, not recorded |
| supply/nlp.py:360 | _capri_nlp_solve | warns | lead | warns; the NLP not built, the caller's fallback solve |
| supply/nlp.py:597 | _capri_nlp_solve | fallback | lead | the young animals' exact response replaced by the PMP terms' silently |
| supply/supply_module.py:1327 | _build_constraints | fallback | lead | the exact N surplus replaced by the coefficient silently |
| supply/supply_module.py:1430 | _build_constraints | fallback | lead | an animal's N surplus term 0 silently |
| supply/supply_module.py:2062 | _solve_inner | fallback | lead | the inner solve's duals zero silently |
| supply/supply_module.py:2201 | _jrc_capped_regions | fallback | lead | the JRC capped regions empty silently |
| supply/supply_module.py:2765 | _manure_context | fallback | lead | the fertiliser options empty silently under an emission tax |
| supply/supply_module.py:2798 | _balance_coefs | fallback | lead | the balance coefficients None silently |
| supply/supply_module.py:2814 | _surplus_per_ha | fallback | lead | the surplus per ha None silently |
| supply/supply_module.py:2871 | _mineral_cap_spec | warns | lead | warns; the mineral fertiliser cap skipped, not recorded |
| supply/supply_module.py:3222 | _solve_region_impl | fallback | lead | the fertiliser options empty silently |
| supply/supply_module.py:3339 | _solve_region_impl | fallback | lead | the result's N substitution 0 silently |
| supply/supply_module.py:3524 | _luc_of | warns | lead | warns; the LUC model's result missing, not recorded |
| data/validate_data.py:245 | catalogue_files | fallback | narrow | a data check on a partial copy: the catalogue query's error |
| data/validate_data.py:279 | margins | fallback | narrow | a data check on a partial copy: the missing file |
| environmental/nitrogen.py:116 | _manure_marginal_factor | silent | narrow | a number parsed from a table row (ValueError, TypeError) |
| io_results.py:312 | _write_market | silent | narrow | a market table not written (its conversion) |
| io_results.py:801 | short_name | fallback | narrow | a scenario's short name (the import) |
| market/processing.py:133 | _crush_params | fallback | narrow | only the crushing parameters' cache key |
| model.py:1195 | _run_scenario | silent | narrow | a trace's price gap (diagnostics) |
| model.py:1265 | _run_scenario | silent | narrow | the outer history's entry (diagnostics) |
| scenarios/definition.py:46 | roots | fallback | narrow | the settings' import (the user's scenarios folder) |
| supply/nlp.py:474 | _try | fallback | narrow | a relaxation variant that fails to build or solve is not taken (the solver's and the build's errors) |
| supply/supply_module.py:1605 | solve | fallback | narrow | a report field (the crops of the fertiliser distribution) |
| supply/supply_module.py:3329 | _solve_region_impl | fallback | narrow | a report field (the fertiliser options' N) |
| coupling/hessian.py:74 | _measure_pending_hessian | warns | kept | warns and records source "failed" in the run's metadata |
| coupling/reporting.py:75 | _welfare_supply | warns | kept | the welfare report's supply part (warns) |
| data/find_symbol.py:66 | list_gdx | other (print) | kept | a tool's message (GDX not readable) |
| environmental/environmental_module.py:639 | compute_indicators | warns | kept | warns; the P balance NaN (visible) |
| market/biofuel.py:105 | _biofuel_params | re-raises | kept | re-raises with what failed |
| market/biofuel.py:144 | _biofuel_market_params | re-raises | kept | re-raises with what failed |
| market/dairy.py:154 | _dairy_params | re-raises | kept | re-raises with what failed |
| market/dairy.py:202 | _dairy_world_params | re-raises | kept | re-raises with what failed |
| market/demand.py:94 | _gl_params | re-raises | kept | re-raises with what failed |
| market/feed.py:210 | _feed_bulk_params | re-raises | kept | re-raises with what failed |
| market/feed.py:322 | _feed_byproduct_params | re-raises | kept | re-raises with what failed |
| market/feed.py:486 | _feed_demand_params | re-raises | kept | re-raises with what failed |
| market/market_module.py:277 | _eu_ms_balance | re-raises | kept | re-raises with what failed |
| market/processing.py:104 | _proc_nq_params | re-raises | kept | re-raises with what failed |
| model.py:1173 | _run_scenario | warns | kept | the outer history (diagnostics; warns) |
| model.py:1229 | _run_scenario | other (print) | kept | a trace (diagnostics) |
| model.py:1233 | _run_scenario | silent | kept | a trace (diagnostics) |
| model.py:1426 | _run_scenario | warns | kept | the baseline market state's cache (performance; warns) |
| model.py:797 | _run_scenario | warns | kept | warns and records the scenario Hessian's failure |
| run_manifest.py:61 | _hook | silent | kept | an audit hook must never raise |
| run_manifest.py:86 | _git | fallback | kept | git absent or failing: the manifest without it |
| scenarios/__main__.py:103 | _check | fallback | kept | the command line's message and exit status |
| supply/supply_module.py:3344 | _solve_region_impl | re-raises | kept | re-raises with the region (a fault of the code or the data stops the run) |
| supply/supply_module.py:3482 | _kill_pool_workers | silent | kept | a worker already gone |

## 4. The syntax-tree check tool

tools/check/compare_syntax_trees.py compares the syntax tree of every .py file that differs between two revisions (or
a revision and the working tree): a change of comments or layout leaves the tree as it was, a change of code does
not. Docstrings exact (the default: a docstring is a string constant), normalised (each line stripped, blank lines
dropped: a formatter's re-indentation passes, a changed word does not) or ignored (a change of docstrings and
comments). Steps 6 and 8 use it in place of runs.

    python tools/check/compare_syntax_trees.py REV_A [REV_B] [--docstrings exact|normalised|ignored] [--paths P ...]

Checked (capri_mod/tests/test_compare_syntax_trees.py, 4 tests) and on two of the assignments refactor's commits:
the citations' correction (8e6a5dc3: comments and docstrings only) passes with docstrings ignored (6 files, 0
trees differ) and fails with them exact (5 docstrings changed); the thread limits (2d8d0fcd: code) fail (7 of 8
files, the eighth a comment only).

## 5. The places the step 1 scan found (outside the CAPTRD pipeline)

| place | function | code |
|---|---|---|
| environmental/ghg.py:239 | _manure_n2o_cascade | `full1 = {t: sh.get(t, s0.get(t, 0.0)) for t in set(s0) \| set(sh)}` |
| environmental/ghg.py:273 | _manure_n2o_full | `full1 = {t: sh.get(t, s0.get(t, 0.0)) for t in set(s0) \| set(sh)}` |
| feed/equations/fedtrm_cal_pw.py:107 | v_animReq_from_ration | `for (r, a, t) in keys:` |
| feed/equations/req_or_man_fnc.py:1766 | p_crprReq_SHGM | `for t in {k[2] for k in st.p_crprReq if k[0] == r and k[1] in ("EWES", "GOAT")}:` |
| feed/equations/req_or_man_fnc.py:1887 | DATA_MANN | `for r, a in acts:` |
| feed/equations/req_or_man_fnc_req.py:2228 | p_animReq_DRMA | `for r, a, t in {(k[0], k[1], k[2]) for k in st.p_animReq}:` |
| market/welfare.py:169 | _welfare_proc_nq | `for x in {x for (x, _) in Hr}:` |
| market/welfare.py:345 | _welfare_agr_feed | `for reg in covered:` |
| policy/cap14_premiums.py:31 | _load | `domain = {d: set(inp.csv(f"capri/{d}.csv", "codes", keep_default_na=False).code) for d in set(edits["domain"])` |
| policy/declared.py:115 | _levels | `v = sum(levels.get((u, a), 0.0) for u in set(below))` |
| policy/mtr.py:244 | _rules | `for i in {k[3] for k in P.keys_of(s=s, r=r) if nonzero(P.v[k])}:` |
| policy/mtr.py:244 | eps_in_year | `for i in {k[3] for k in P.keys_of(s=s, r=r) if nonzero(P.v[k])}:` |
| policy/mtr.py:265 | _rules | `for r in d["members"].get(m, set()) \| {m}:` |
| policy/mtr.py:265 | dcow_ceiling | `for r in d["members"].get(m, set()) \| {m}:` |
| policy/mtr.py:361 | declarations_of_year | `for s in schemes:` |
| policy/mtr.py:376 | declarations_of_year | `for s in schemes:` |
| policy/mtr.py:383 | declarations_of_year | `for s in schemes:` |
| policy/mtr.py:391 | declarations_of_year | `for m in eu10:` |
| policy/mtr.py:559 | coupling | `for s in schemes:` |
| policy/mtr.py:560 | coupling | `for m in ms:` |
| policy/mtr.py:563 | coupling | `for m in eu11 \| bur:` |
| policy/mtr.py:582 | dd_targets | `for (r, s, g) in keys:` |
| policy/premium_cut.py:117 | premiums | `for u in units:` |
| policy/premium_cut.py:118 | premiums | `for s in schemes:` |
| policy/premium_response.py:112 | __init__ | `for u in units:` |
| policy/premium_response.py:151 | factors | `lev = {k: sum(wi * h.get(k, 0.0) for wi, (_, h) in zip(w, hist)) / tot for k in keys}` |
| policy/rd.py:137 | extend_budget | `for r in runr:` |
| policy/rd.py:144 | extend_budget | `for r in runr:` |
| policy/rd.py:187 | extend_budget | `for m in old & set(measures):` |
| policy/rd.py:344 | rd_declarations | `for m, ps in keys:` |
| policy/rd.py:351 | rd_declarations | `for m, ps in keys:` |
| policy/rd.py:364 | rd_declarations | `for lc, t in lcs:` |
| policy/rd.py:383 | rd_declarations | `for a in acts:` |
| policy/rd.py:399 | rd_declarations | `for r in regions_f:` |
| policy/rd.py:441 | rd_declarations | `for r in runr:` |
| policy/rd.py:484 | rd_declarations | `for r in runr:` |
| policy/rd.py:516 | rd_declarations | `for r in runr:` |
| policy/rd.py:527 | rd_declarations | `for r in set(d["ms"]) \| d["srnuts2"]:` |
| policy/rd.py:591 | rd_declarations | `for r in se_regions:` |
| projection/prices.py:199 | apply_capri_prices_2030 | `for act in set(c1) \| set(c0):` |
| run_manifest.py:31 | <module> | `_SKIP_PREFIX = tuple(str(Path(p)) for p in {sys.prefix, sys.base_prefix, sys.exec_prefix}) + (` |
| run_manifest.py:148 | compare | `for k in set(a.get("software", {})) \| set(b.get("software", {}))` |
| supply/capri_pmp.py:169 | build_elasticity_table | `for a in set(df.activity):` |
| supply/ghg_tax.py:102 | ghg_coefficients | `for k in keys:` |
| supply/ghg_tax.py:118 | ghg_coefficients | `for a in set(eff or {}) \| set(s0 or {}):` |
| supply/ghg_tax.py:122 | ghg_coefficients | `for t in set((eff or {}).get(a) or {}) \| set((s0 or {}).get(a) or {}):` |
| supply/livestock.py:38 | young_animal_columns | `for a in set(pr) \| set(us):` |
| supply/livestock.py:79 | _apply_young_animal_prices | `for a in set(rec.get("produce", {})) \| set(rec.get("use", {})):` |
| utils/capri_stop.py:71 | _agg_prices | `for r in rows:` |
