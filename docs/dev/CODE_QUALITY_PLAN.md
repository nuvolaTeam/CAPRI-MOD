# Code quality plan (24 November 2026)

From the external code overview the project lead shared on 24 November 2026 (ratings: maintainability fair to poor,
refactoring risk high, scientific traceability and test emphasis excellent) and the order of work agreed after it.
Eight steps, in order. The figures below were measured on dev at 858070c (capri_mod without its tests unless said
otherwise; AST and grep counts, 24 November 2026).

## 0. What the code is today, and two corrections to the overview

| Item | Measured |
|---|---|
| Python in capri_mod and tools (tests excluded) | about 105,000 lines, 229 modules in capri_mod |
| Largest modules | supply/supply_module.py 3,566 lines; feed/equations/req_or_man_fnc_req.py 2,740; supply/capri_regional_nlp.py 2,010; feed/equations/req_or_man_fnc.py 1,947; model.py 1,675; io_results.py 1,358 |
| Longest functions | CAPRIModel._run_scenario 1,153 lines; market/supply_system_ad.py supply_system 603; supply/nlp.py _capri_nlp_solve 589; environmental_module.compute_indicators 484; supply_module._build_constraints 451 and _solve_inner 421. 17 functions above 300 lines, 48 above 150 (of 2,146) |
| Broad exception handlers | 66 `except Exception` or bare `except` in capri_mod (77 with tools); supply_module.py 16, model.py 9 |
| Settings | 248 keys in capri_mod/settings/defaults.toml; docs/dev/SETTINGS_INVENTORY.csv 517 rows; at least 15 string settings default to "capri" with a former form as the other value |
| Comments | 5,134 comment lines; at least 65 carry a former form's date on the same line ("until 18 November 2026 ..."), more across several lines; 376 lines cite a KNOWN_ISSUES number |
| Hash order | tools/run/run_f2f_2030.py and run_vcs_2030.py re-start themselves with PYTHONHASHSEED=0, the Dockerfile sets it; without it two runs of one scenario differed by up to about 0.2% (the Dutch laying hens 10-20%; CHANGELOG, "Reproducible runs"). CAPTRD's estimation already sorts its sets (CHANGELOG, the estimation's widening) |
| Lint | CI (.github/workflows/python-app.yml) and the pre-commit checks run flake8 with E9, F63, F7, F82 only; .flake8 ignores F821 in supply, environmental and coupling, because capri_mod/utils/mixins.inject_names (and capri_mod/coupling/__init__.py) give those block modules their parent module's names at import. Ruff 0.17.4 is installed in the work container; Black is not |

Two corrections, to the overview and to the first reply to it (24 November 2026):

- **The state containers are not loose.** Since the parameters and state refactor (docs/dev/REFACTOR_SUPPLY_PARAMETERS_PLAN.md,
  docs/dev/ARCHITECTURE_REFACTOR.md) the supply, market, environmental and coupling state lives in declared slot
  classes (`par`, `sv`, `ev`, `seen`, `res`: capri_mod/supply/state.py, market/state.py, environmental/state.py,
  coupling/state.py). They are slot classes rather than dataclasses by the project lead's decision of 2 November 2026,
  and a moved name raises on use. What is still loose is narrower (step 2).
- **`CAPRIModel.run()` is 85 lines.** The long one is `_run_scenario`, 1,153 lines.

## 1. Results independent of the hash order

Why first: every later step is checked by an exact comparison of two runs (section 9), which holds only if a run
does not depend on the process it runs in. It also removes the environment variable the project lead asked runs not
to need (11 November 2026).

- **Find:** the mini-EU baseline (tools/run/run_mini_eu.py) under two seeds (PYTHONHASHSEED 0 and 1), compared with
  tools/check/compare_pickles_exact.py; the first quantity that differs points to the place. Alongside, a scan of the
  numerical paths for iteration over sets of names: `for ... in set(...)`, set literals, set unions and differences
  turned into lists or arrays, dictionaries built in a set's order.
- **Fix:** iterate in a fixed order: the order of CAPRI's set where the code mirrors one (the sets' data files), else
  `sorted`. No other change in the same commits.
- **Done when:** the mini-EU run is identical under seeds 0, 1 and 2. The re-start in the two run tools and the
  Dockerfile line stay until a full-EU run without the seed matches one with it, at the next gate the project lead
  schedules; then they go.
- **Results change:** yes, once: the fixed order is not seed 0's order, so results move within the size seen between
  seeds (about 0.2%). Recorded in CHANGELOG with the mini-EU differences; the new mini-EU run becomes the reference of
  the steps after it.

## 2. Typed state, one module at a time

The slot classes stay (the decision of 2 November 2026). Three things remain:

1. **Dictionaries with string keys passed between blocks.** Example: the supply result's `cover_crops`
   (`res.cover_solved`) and the requirement's `ev.cover` both have a key "req", the solved area in one and the
   requirement in the other. The ones read in more than one module become typed records. My proposal is
   `typing.TypedDict`, because a TypedDict is still a dict at run time: the result files, io_results.py and the
   Hugging Face Space keep reading them unchanged. Keys are renamed only where one key has two meanings, and the
   rename is recorded.
2. **Type annotations on the slots and on the public methods** (the model's, the modules' run and solve methods, the
   equation functions). No annotation drive beyond that.
3. **The injected names** (inject_names): each block module imports what it uses, so the F821 exemption in .flake8
   can be dropped for supply, environmental and coupling, and flake8 or Ruff sees undefined names there again.

Order: environmental (smallest), coupling, supply (block by block), market. Pure moves: results identical.

## 3. Split `_run_scenario` and the largest modules

- `CAPRIModel._run_scenario` (1,153 lines) into the steps of CAPRI's simulation loop it follows (capmod: the supply
  side, the market, the price update, the convergence test, the reporting), named after CAPRI's files and
  statements where one exists, and no internal plan codes in names (the rule of 14 November 2026).
- supply_module.py: `_build_constraints` and `_solve_inner` into their blocks; the other functions above 300 lines
  after that, the same way.
- Not in this step: the equation modules (one function per CAPRI block already) and the CAPTRD pipeline's long
  functions, which follow CAPTRD's GAMS files.
- Pure moves: results identical. The assignments refactor (refactor/assignments, being merged) and the equation
  refactor already moved part of this; this step starts after that merge.

## 4. Remove the former-form settings

- **List:** from docs/dev/SETTINGS_INVENTORY.csv and defaults.toml, every setting whose other value is a form the
  model had before a fix (at least the 15 with the default "capri", from `outer_loop.price_update` to
  `supply.catch_crop_biofix_area`, plus the switches of the same kind among the booleans).
- **Not removed:** settings that are documented departures from CAPRI or options the project lead keeps on purpose
  (docs/DEPARTURES_FROM_CAPRI.md), and anything a comparison tool or document still runs.
- **The project lead decides the list** before any removal.
- The default runs do not change (the defaults are kept): results identical. The tests of the removed forms go with
  them. A settings file that still sets a removed key fails when loaded: the loader already refuses an unknown key
  (capri_mod/settings, SettingsError).

## 5. Audit the broad `except` paths

A first, rough reading of the lines after the 66 handlers in capri_mod: about 8 pass or continue silently, about 29
return or assign a fallback value, about 16 warn, about 10 re-raise (to confirm by reading each one).

- Each one classed: kept (it re-raises, or guards an optional report); narrowed to the exceptions it is for; or, in a
  numerical path, a silent fallback, which is a hidden proxy under the project's rule: it raises, or warns and is
  recorded in the run's metadata. The fallbacks of the third kind go to the project lead before they change.
- Before changing them: a temporary counter on every fallback, read from one mini-EU run. A fallback that never fires
  in it can change without moving results; one that fires is a result change and is reported.

## 6. Shorten the comments

- Keep in the code what a line does, its CAPRI source (file and lines) and a KNOWN_ISSUES or DEPARTURES reference.
  Move the history (former forms, dates, who decided) to CHANGELOG or KNOWN_ISSUES where it is not there already.
- The GAMS quotes in the docstrings (the equation style) are not touched.
- Only comments change. Checked by comparing each file's syntax tree before and after (a small check tool; comments
  are not in the tree), so this step needs no run.

## 7. Ruff with narrow rules

- Ruff in place of flake8 in CI and in the pre-commit checks, with: the current set (E9, F63, F7, F82), F401 unused
  imports (the project lead's "no import cleanup until the end" is this step), F811, F841, E722, BLE001 (after step
  5), F821 everywhere (after step 2), and a few bugbear rules (B006 mutable defaults, B023 loop variables in
  closures). No style or line-length rules.
- Re-exported names stay (`__all__` or `noqa` with the reason, as capri_mod/supply/state.py does).
- Removing an import can remove a side effect at import: targeted tests and one mini-EU run.

## 8. Formatting last

- One commit, after the open branches have merged, at line length 120, with the commit listed in
  .git-blame-ignore-revs so that blame skips it.
- **A different choice from the overview (the main session's proposal):** `ruff format` rather than Black. It follows Black's style, is
  already installed and is the same tool as step 7. Black would do the same job.
- Data tables whose layout carries meaning keep it (`# fmt: off`).
- Checked by the syntax-tree comparison of step 6 (a formatter must not change the tree), so no run.
  capri_data/schema/03_code_data.sql is regenerated (it records line numbers).

## 9. Checks, kept short

The rules of the project lead apply: gates per batch, not per change; a pure-refactor batch goes to dev once its
mini-EU run is identical and the suite passes; no full-EU run for changes of limited reach.

| Check | When | Cost |
|---|---|---|
| Static checks (lint, citations, GAMS quotes, doc coverage, make_code_data, make_provenance, schema, manifest) | every commit | seconds |
| The tests of the modules touched | every commit | minutes |
| Syntax-tree comparison | steps 6 and 8, instead of runs | seconds |
| Mini-EU run against the batch's reference, compare_pickles_exact.py at rtol 1e-12, both as fresh processes, alone on the machine (IPOPT's CPU-time guard) | once per batch; step 1 three times (three seeds) | about 16 minutes each (the last mini Green Deal runs: 952 and 990 s) |
| Full suite (pytest-xdist -n 2) | once per batch, before the push to dev | about 2 hours here. On 8 GB the CAPTRD pipeline tests crash their workers when two run together (24 November: 9 crashed workers); they run one at a time, and only in batches that touch capri_mod/pipeline or the modules it imports |
| Full-EU Farm-to-Fork and Green Deal runs | none for the pure steps; step 1's joins the next gate the project lead schedules | 1-2 hours each |

Batches, to keep the suites few:

| Batch | Steps | Results | Mini-EU runs | Suites |
|---|---|---|---|---|
| A | 1 | change once (recorded) | 3 | 1 |
| B | 4 and 5 (after the project lead's lists) | identical, except fallbacks that fire (reported) | 1-2 | 1 |
| C | 2 and 3, module by module, one commit per move | identical | one per module group (4) | 1, at the end |
| D | 6, 7 and 8 | identical | 1 (for step 7) | 1 |

In all: about 10 mini-EU runs (about 3 hours), 4 suites, no full-EU run of its own.

## 10. Hand-over to a Claude Code session

The steps suit a separate Claude Code session: they are mechanical, each has a check that says whether it is done,
and most need no CAPRI judgement. The conditions:

- **When:** steps 2, 3, 6, 7 and 8 start after the assignments refactor is in dev (it changes 124 files against dev and is
  being merged now). Before that the session can do what changes no code: step 1's search, step 4's list, step 5's
  classification and the syntax-tree check tool.
- **Not touched while open in the main session:** capri_mod/feed/equations (the baseline feed calibration port) and
  the files of a change not yet pushed; the session checks dev's log and the open branches before each batch.
- **Results:** a step that changes results stops and reports before it is committed (steps 1, 4 and 5 can).
- **Machine:** the session runs in its own cloud container (the project lead, 24 November 2026), so its runs do not
  compete with the main session's. It sizes its runs to its container: one heavy job at a time there too, and, if it
  has 8 GB like the main session's, the CAPTRD pipeline tests one at a time.
- **Branches:** its own branch from dev, never refactor/assignments or the main session's batch branch; the main
  session merges refactor/assignments into dev.
- **Style rules that stay:** the equation style (one function per CAPRI block, the GAMS text quoted), CAPRI's names,
  no internal plan codes in names, data read from data files, every check in section 9.
- **Out of scope:** behaviour changes, new tests beyond the ones the steps need, the data builders (tools/build).

## 11. Risks

| Risk | What guards it |
|---|---|
| A move changes results in the last digits (solver caches, warm starts, fork order) | fresh processes on both sides, the same worker count, the run alone on the machine; a batch that fails is bisected commit by commit |
| The result files change shape (io_results.py, the Hugging Face Space, stored runs) | records as TypedDicts, results written as dicts; an old run loaded in the suite |
| Conflicts with open branches | steps 2, 3, 6, 7 and 8 only after the merges; formatting last, in one commit |
| A removed setting is still set in a settings file or a document | the loader already refuses an unknown key; a search of runs, docs and tools |
| A narrowed `except` lets a run stop where it used to carry on | the counter of step 5 shows which fire in the mini-EU run; those go to the project lead |
