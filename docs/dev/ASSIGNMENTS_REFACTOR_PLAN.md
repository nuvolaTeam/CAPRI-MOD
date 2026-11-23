# Plan: CAPRI's ported assignments as named functions (the refactor's third phase)

Written 23 November 2026 for a Claude Code cloud session, after the second phase (CAPRI's market, calibration and
manure pool equations, blocks M0-M5, C0-C1, P) was merged into dev (1d7a77b). The rules of the work are those of
docs/dev/EQUATION_REFACTOR_BRIEF.md and docs/dev/EQUATION_REFACTOR_HANDOFF.md section 7 (the project's instructions
and the project lead's standing rules); the checks are those of docs/dev/MARKET_EQUATION_REFACTOR_PLAN.md sections 2
and 4, with the changes below. This file says what the third phase covers, in which order, and how it is checked.

## 1. The rule this phase applies

The project lead, 20 November 2026 (docs/dev/MARKET_EQUATION_REFACTOR_PLAN.md section 7): the CAPRI logic ported as
GAMS assignments, not equations (the emission accounts of envind/gases.gms, the premium rules, the nutrient-need
updates of fert/fertned.gms, the baseline projection rules), gets the equations' treatment: one named function per
CAPRI statement block, its GAMS text quoted, with CAPRI's names, file and lines, so that
tools/refactor/check_gams_quotes.py and check_gams_citations.py check it against star 3.0 as they check the
equations. New code has followed it since that day (capri_mod/supply/equations/fertned.py, fertpar.py,
def_gascoeff.py, ghgmiti.py, tillage.py, leg_share.py, line_nitr.py; capri_mod/market/equations/set_prices.py); the
assignments ported before it are this phase.

**A statement block** is one CAPRI assignment, or the assignments to one symbol that belong together (the branches of
a `$if`, a value and its fallback, as DATA_UVAG_FEED_TRD_Y or O_HP do). Its function:
- is named after the assigned symbol, CAPRI's name (variables and parameters first), e.g. p_technFact_MANN,
  p_manureShadVal, DATA_FNUT;
- quotes the GAMS text in its docstring, under "CAPRI's GAMS (file l. a-b):", with star 3.0's lines;
- states the statement in this project's notation, what each argument is in the model's terms, and its departures
  from CAPRI ("Departures from CAPRI: none." where there are none);
- takes plain numbers or arrays and returns the assigned value; loops over regions, data reading and units stay in the
  callers, which call the function.

The layout follows the first two phases: one module per CAPRI source file, named after it, in an `equations/` package
of the area that uses it (capri_mod/environmental/equations/gases.py, capri_mod/policy/equations/prmcut.py,
capri_mod/projection/equations/load_base_data_and_trends.py, ...). A CAPRI file whose statements several areas use
gets one module, in the area that uses it most, imported by the others. The existing equations/ packages stay where
they are; a statement already there is not moved.

## 2. Scope

**In:** the model's code, capri_mod/ outside its equations/ packages, pipeline/ and tests/: 85 modules that cite
CAPRI's GAMS files 872 times (23 November 2026, a grep; a citation is not always a ported statement: block A0 sorts
them).

**Out:** CAPTRD's estimation (capri_mod/pipeline/captrd: after CAPTRD-MOD stands); the builders (tools/build: their
rework is planned at the end, the project lead, 21 November 2026); CAPREG; the tests (their imports only); any change
of results; a newer CAPRI release.

## 3. The blocks

| Block | What | The model's code now | CAPRI's files (the main ones) |
|---|---|---|---|
| A0 | The inventory: docs/dev/assignments_inventory.csv, one row per CAPRI statement block the model's code ports or cites, with its file and star 3.0 lines, the module and function that holds it, a status (to move / already in the style / a citation for context only / not ported, with the reason) and the block below that takes it. A tool of its own beside tools/refactor/supply_equations_inventory.py, so the inventory can be rebuilt. Docs and tools only | the citations in the 85 modules | all |
| A1 | The emission and nutrient accounts (with A3: one block, section 8) | environmental/ghg.py, environmental_module.py, nitrogen.py (its accounts; the coefficients' yield rules are already in supply/equations/fertned.py), phosphorus.py, p_balance.py, luc.py, ammonia.py, biodiversity.py; supply/n_leaching.py | envind/gases.gms, reports/calc_nbalance.gms, envind/ghgMiti.gms and cover_crops.gms (the leaching's option terms), supply/prep_sim_luc.gms |
| A2 | The premium rules | policy/mtr.py, bps.py, cap14_premiums.py, declared.py, premium_cut.py, premium_response.py, premiums.py, rd.py, nordic_aid.py, norway.py, policy_module.py; supply/entitlements.py | policy/policy.gms, calc_mtr*.gms, prmcut.gms, implement_bps.gms, bps_convergence.gms, rd_logic.gms, extend_rd_baseline.gms, def_policy.gms, nordicaid.gms, norw_pol.gms, capmod/calculate_premiums.gms |
| A3 | The baseline projection rules | projection/prices.py, projection_module.py, trajectory.py, reconcile.py, captrd_import.py | those A0 finds; the modules cite capmod/load_base_data_and_trends.gms, supply/prep_sim.gms, envind/breeding.gms, fert/calc_nexport.gms (the yield and input rules of capmod/define_inputs.gms and shift_yields.gms are partly in supply/equations/fertned.py already) |
| A4 | The coupling's and the market's assignments | coupling/price_step.py, hessian.py, bridge.py, young_animals.py, feed.py, manure.py (what the P block left), reporting.py; market/welfare.py, market_bounds.py, the assignments of market/supply.py, demand.py, feed.py, bilateral.py not moved in M1-M5 | capmod/define_stepWeights.gms, price_forecast.gms, supply/calibrate_supply.gms, arm/simu_calibration_to_supply.gms, arm/set_start_val.gms, widen_bounds.gms, reports/welfare.gms, reports/sol_simy.gms |
| A5 | The rest, after the main line's current fixes (K196, DEP-21, DEP-10, DEP-13; the main session says when) | policy/greendeal.py, supply/policy.py, policy/endotech.py, fert/inner_fert_dist.py, fert/npk.py, supply/abatement.py, supply/supply_module.py, supply/livestock.py, supply/land.py, supply/fertilisation.py, feed/ration.py, data/loaders.py, model.py | pol_input/greendeal/*.gms (conventional_io, organic_io, pesticides, landscape, minfert_redu_*), envind/ghgMiti.gms, cover_crops.gms, tillage.gms, ammo_tech.gms, low_n_feed.gms, fert/set_fert_priors.gms, fert/endoManAvail.gms, supply/prep_sim.gms, arm/set_prices.gms l. 43-89 |

The order inside the phase may change where code is shared; each block's commit says which statements moved and which
gate it passed. A0 may move a module from one block to another (it is the inventory that decides).

**The files the main line is changing now** (until A5 starts): supply/fertilisation.py, supply/abatement.py,
supply/capri_regional_nlp.py, supply/equations/ghgmiti.py, fert/npk.py, policy/greendeal.py, supply/policy.py,
supply/livestock.py and the livestock tables with their builders (DEP-13). Blocks A1-A4 leave them alone; where a block
needs a caller in one of them, the edit is the call line only.

## 4. The checks

At every block, as in the second phase (docs/dev/MARKET_EQUATION_REFACTOR_PLAN.md section 4), with these changes:
1. The gate (a move, not a change):
   - the moved functions' own tests (each function on CAPRI's numbers where the inventory gives a check, as
     test_bulk_prices.py does for DATA_UVAG_FEED_TRD_Y) and the moved modules' existing tests;
   - one five-unit Green Deal run identical to the run at the block's starting commit, apart from the run's metadata
     (tools/check/compare_pickles_exact.py); for A2 also a five-unit run of the coupled-support check
     (tools/run/run_vcs_2030.py), since its premium paths are not in the Green Deal's. Since the full-EU run comes
     only at the end (below), A0 chooses the five units so that between them they take the paths the block's
     statements have (a Norwegian unit, one with coupled support, one with manure trade, one where the landscape
     floor binds, ...), and each block names its five;
   - once, after A5 (the project lead, 23 November 2026), the full-EU Green Deal run with
     capri_mod/settings/capri_comparison.toml identical to the one at the phase's starting commit (metadata aside).
     If it differs, the blocks' commits are bisected (one full-EU run per step) to find the block, which is then
     corrected. The baseline's market supply Hessian is measured once in the session's own container (about 41 minutes
     on 2 cores here) and reused from its cache.
2. The quotes: tools/refactor/check_gams_quotes.py with the new equations/ packages added to its file map (each
   module to its CAPRI file) and `--expect supply/supply_model.gms=5557 --expect arm/market_model.gms=4607`.
3. The citations: tools/refactor/check_gams_citations.py extended to statement blocks: a line citation next to a
   statement function's name holds that statement (the assigned symbol on the cited lines) in star 3.0.
4. The full suite after A2, after A4 and before the phase's merge; the main line's pre-commit checks at every commit.

The CAPRI copy is star 3.0 only, checked as the second phase did (docs/dev/MARKET_EQUATION_REFACTOR_PLAN.md
section 2), before anything else.

## 5. What each block hands to the main line

As in the first two phases (KNOWN_ISSUES K189 is the first phase's list): the block fixes nothing. It lists, in the
inventory's notes with their evidence, the statements the model does not port, the rules the model applies that
CAPRI's code has not, and the porting differences; the handoff (docs/dev/ASSIGNMENTS_REFACTOR_HANDOFF.md) collects
them for the main line to measure and rank. A difference that looks large (a premium, a price, an emission total of
the Green Deal step) is reported when found, not at the end.

## 6. Branch and merge

A branch of its own, `refactor/assignments`, from dev at this file's commit. dev is merged into it after each push to
dev (a merge, never a rebase or a force-push: the repository is public). The main session merges it into dev after
the phase's gate and the full suite, with the project lead's go.

## 7. Not in scope

The supply side's and the market's equations (done); CAPTRD's estimation (after CAPTRD-MOD); the builders (their
rework at the end); CAPREG; changes of results; a newer CAPRI release.

## 8. The project lead's review of A0 (23 November 2026)

A0 approved (docs/dev/assignments_inventory.csv, docs/dev/ASSIGNMENTS_REFACTOR_HANDOFF.md), with these decisions:

1. **A1 and A3 are one block** (A1+A3), gated with A1's five units: the emission accounts were mostly written as
   functions in the first phase (N14a), so A1 has 8 statements to move and A3 5.
2. **In A2 only the rules become functions.** The literal values of pol_input/mtr_until2013.gms, and any other
   literal table, get the inventory's status "data read: <the CSV and its builder>": out of scope with the builders'
   rework, which will keep each value's CAPRI file and line. A statement block mixing rules and literals moves its
   rules only.
3. **The wrong line citations** the inventory lists are fixed in the files each block moves, as part of the block
   (comments only; results identical). The two in supply/policy.py are left to the main session.
4. **The porting differences** found are collected in the handoff (docs/dev/ASSIGNMENTS_REFACTOR_HANDOFF.md); the
   main session registers them as one KNOWN_ISSUES entry and ranks them.
