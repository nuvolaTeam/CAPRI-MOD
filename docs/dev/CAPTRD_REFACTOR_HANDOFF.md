# Handoff: the refactor of the CAPTRD pipeline's equations (branch `quality/no-code-steps`)

Written 24 November 2026 for the session that continues it, and for the main session that holds the merges. The
refactor applies the equation style of the supply, market and assignments refactors (docs/dev/EQUATION_REFACTOR_BRIEF.md,
docs/dev/ASSIGNMENTS_REFACTOR_HANDOFF.md) to capri_mod/pipeline/captrd, CAPTRD-MOD's port of CAPRI's trend module
(gams/captrd). **A move, not a change: every value and every expression identical**, checked exactly for every block.
Nothing is merged into dev; the main session decides the merge.

## 0. In short

- **Done, pushed:** C1, C2, C3: all of captrd/equations.gms that CAPTRD-MOD ports (m_trendMS's 39 equations,
  m_trendNT2's own 7, the objective SSQS_) are named functions with their GAMS statements quoted, in
  capri_mod/pipeline/captrd/equations/ (equations.py, nuts2.py). The callers (estimate_ms, estimate_nuts2) keep the
  domain conditions and the loops. C4: the member-state estimation's bounds (estimate_bounds.bounds: estimate_ms.gms,
  fix_est.gms, comi_bounds.gms, biofuel_bounds.gms), 81 functions in equations/fix_est.py, comi_bounds.py,
  biofuel_bounds.py, estimate_ms.py. C4b: the NUTS 2 estimation's bounds and its retries' (estimate_nuts2.bounds,
  _open_bounds, _grid_again), 54 functions in equations/estimate_nuts2.py, est_nuts2_grid_openbound.py,
  est_nuts2_grid.py. C4c: the member state's bound-widening after an infeasible solve (estimate_nlp._widen,
  _oind_ocro, _again, _release_comi), 22 functions in equations/estimate_ms.py and release_comi_yields.py. The
  bound statements of estimate_bounds, estimate_nuts2 and estimate_nlp are now all named functions. C5 (C5.1-C5.18):
  the supports and trends modules, every assignment with arithmetic of the CAPRI files they port: 832 functions in
  36 modules of capri_mod/pipeline/captrd/equations/ altogether (section 1's C5 rows); what is left in the callers is
  listed in section 5.
- **Checked:** exactly (hex floats and CasADi text) against the starting commit 9c69ab7b, with
  tools/check/captrd_parity_dump.py on CAPTRD's own Step 2 points; the pipeline tests unchanged; the static checks.
- **Not checked here, and why:** a full CAPTRD run's outputs. The published raw set has no capreg_base (CAPREG's base
  year for the EU's countries), which the estimation's bounds, the NLP and the NUTS 2 solves read: those 14 pipeline
  tests fail or error here, before and after the refactor alike. The main session's environment has it: run the
  pipeline's outputs bit for bit there against 9c69ab7b before the merge (section 4).
- **C6, done:** the hash-order places sorted, a commit of its own (cbfc688e): the pipeline's parts are the same
  under PYTHONHASHSEED 0 and 1 (section 1's C6 row). **Next:** the main session's merge decision and its bit-for-bit
  run of the pipeline's outputs against 9c69ab7b (section 4); the C6 commit's last-digit changes are expected there.
- **The main session's check before the merge (25 November 2026), with CAPREG's base data:** the pipeline's 15 test
  files run at the starting commit 9c69ab7b, at C5's head 255f7b2 and at C6's head c5b2212 under PYTHONHASHSEED 0 and
  1, every call of the stages' functions (step1.run, statistics, supports, prepare, estimate_bounds.bounds,
  estimate_nlp.solve, clean_tiny.clean, step3_copies.copy, estimate_nuts2's bounds, solve and rem_tiny) hashed
  exactly (floats as hex, data frames with their index and order):
  - 9c69ab7b and C5: every output identical;
  - C6 against C5: one value, Austria's ARTIF LEVL at BASM (check_and_cor's sum over its regions, now in sorted
    order), 1.4e-16 relative, and with it the two ARTIF LEVL entries of Austria's 2030 bounds; nothing else;
  - C6 under seeds 0 and 1: the prepared data and the statistics (prepare.prep_for_estimation, statistics.statistics)
    differ in their rows' order only (equal when sorted); 9c69ab7b has the same order dependence (the same two
    hashes). Everything computed from them is identical under both seeds.
- **Findings (listed, not fixed: a move changes nothing):** est_nuts2_grid.gms l. 121 (the set-aside levels' floor) is
  inside `if (p_farmModelisRunning eq 1, ...)`: CAPRI applies it to the farm types only, the port to the NUTS 2 regions
  too; CAPRI's `/ 1000` is the port's `x 0.001` in the NUTS 2 production and area bounds (may differ in the last
  digit); CAPRI's statements on ARTIF divide by the member state's base unconditionally, the port only where it is
  nonzero; estimate_ms.gms l. 302, 315's share for the secondary products' processing yields is CAPRI's 0.9 - .89
  (0.010000000000000009 in floating point), the port's 0.01. C5's findings: section 5, "C5's findings".
- **The main session's notes (24 November):** moves must leave results identical, and the pipeline's outputs are to be
  compared bit for bit against the starting commit; the 81 places' sort is a separate commit, not mixed with moves; the
  heavy pipeline tests reach about 5.4 GB each, run them one at a time on a small container; the CAPTRD-MOD stage 2e
  all-countries run before Bonn runs after this refactor is merged, on its final version.

## 1. State

| commit | block | what | check |
|---|---|---|---|
| 1d6172ed | C1 | m_trendMS's equations (equations.gms l. 107-795): AREAB_ ... GRPLVL_, 39 functions in equations/equations.py; estimate_ms.residuals calls them. Its constants SEED_SHARE, POS_*, DAILY_*, MOLA_VINASSE, DAYS_YEAR became the functions' literals; REQS_EFF and REQS_YEAR0 stay (estimate_bounds and tests use them) | 282,007 residuals at 340 points, 3,444 expressions: identical |
| 3da68403 | C2 | SSQS_ (l. 801-875) in equations.py for both objectives: estimate_ms.objective (CARD(Rest) = 1, no weight factor, so the graph has no `* 1`) and estimate_nuts2.objective (the regions' weights). The five SSQS_ constants became its literals | 340 objectives, 3 NUTS 2 ones, their expressions, and the same with STCM data added (the pull is otherwise not reached): identical |
| edb882ca | C3 | m_trendNT2's own equations: MSGROF_, MSLEVL_, MSLANDUSE_, MSFEEDI_, MSlosfFoddo_, MSindmMaif_, EFED_ in equations/nuts2.py; estimate_nuts2.residuals calls them. FEED_SCALE became MSFEEDI_'s literal; PER_1000 stays (the bounds) | 8,964 residuals (AT, DE, DK, NL as regions, six years, with and without EX_FEED, every block reached), 1,496 expressions: identical |
| 0132882e | tools | tools/check/captrd_parity_dump.py (the check), tools/build/build_reference_from_raw.py (the reference from the published Parquet), tools/check/scan_set_order.py (step 1's scan) and docs/dev/captrd_set_order_places.csv (its 81 CAPTRD places), this handoff | the parity tool reproduces the dumps of C1-C3; the builder reproduces the reference built for them (section 3) |
| f0942fc1 | C4 | estimate_bounds.bounds, _comi, _biofuel: every statement's arithmetic a function named after the bounded symbol (V_EstV_IO, V_EstV_NoYieldDrop, p_data_LEVL_facs, V_EstV_COMI, ...) quoting its lines; bounds() keeps the domains, the loops and the statements' order. The constants STD_UP, LO_SUPPORT_SHARE, WINE_PLANTING, MAX_YIELDS, CERE_MAX_YIELD, GRAS_MAX(_NL), STRA_MAX and _phys went into the functions; REF_MILK_YIELD and PROC_YIELDS (captrd.gms's parameters) stay. The expert bounds' citation corrected: estimate_ms.gms l. 159-162 (the port's l. 146-151 is the aglinkTightLink block, off); the member state's own bounds l. 78-162 | the bounds at every member state and year with both readings of ARTIF's bound (680 cases), at three member states with synthetic data reaching the branches the reference does not (6), and at the NUTS 2 regions of AT, DE, ES, IR (198): 2.2 million bounds, identical in value and order; 99% of the bound code reached |
| 8480e8cc | C4b | estimate_nuts2.bounds (estimate_nuts2.gms l. 92-400), _open_bounds (est_Nuts2_grid_openbound.gms l. 40-292) and _grid_again (est_nuts2_grid.gms l. 53-121): each statement's arithmetic a function (V_EstV_up_LEVL, V_EstV_GROF with the shared _grof_sums and _gmul, V_EstV_lo_coef, V_EstV_SUGB_LEVL, ...); the callers keep the domains, the loops and the order. Constants that were arithmetic went into the functions; those that are conditions (FEED_FIX_TRIES, NYD_OPEN_TRIES, REQS_TRIES, LEVL_TRIES_OPEN, UAAR_TRIES_OPEN, LEVL_OPEN_FLOOR, PROD_OPEN_TRIES, RSET_LO_MIN, SUGB_FROM, SUGB_TRUST) and the sets (MEAT_EGGS, LOSF_EXTRA) stay. The openbound citations corrected (the port's l. 40-50, 53-61, ... 202-210 were another version's; the true lines in each function) | estimate_nuts2.bounds at the regions of AT, DE, ES, IR in three years, with and without a sugar quota, regional experts and a milk quota (24 cases), and _open_bounds + _grid_again from those bounds at a synthetic solve state for five try counts (84 cases, every threshold crossed): identical (SHA-256 of the exact bounds and levels); 99% of the new modules reached |
| fd0a4801 | C4c | estimate_nlp._widen (estimate_ms.gms l. 256-321), _oind_ocro (l. 335-346), _again (l. 328-418) and _release_comi (release_comi_yields.gms l. 24-45): 19 functions appended to equations/estimate_ms.py (V_EstV_lo_widen, V_EstV_lo_INCE_try, V_EstV_UAAR_again, ...) and 3 in equations/release_comi_yields.py; the callers keep the binding bounds, the conditions and the order. LEVL_UP_FAC, LEVL_LO_FAC, WIDEN_*, PRCY_FLOOR, PRCY_RANGE, INCE_STEP, COMI_STEP, LOSF_UP / LOSF_LO and EB_* went into the functions; the try thresholds (LEVL_TRIES, OIND_OCRO_TRIES, BIOFUEL_TRIES) stay; their citations corrected (l. 256, 335, 376-378) | the four functions from estimate_bounds.bounds' bounds at a synthetic solve state (every third bounded position at its lower bound, the next at its upper, OIND and OCRO at theirs without production, expert calorie bounds) for six try counts around 5, 25 and 30, at six member states in three years, plain and with bounds_cases' extra inputs (216 cases): identical; 99% of the new functions reached (the one line left a bound kind no caller passes) |

| c72430bf, 0b54ebf8 | C5.0 | the handoff's C4c row; the inventory docs/dev/captrd_inventory.csv and its builder tools/check/captrd_inventory.py (section 5) | - |
| 1a18795c | C5.1 | copy_labour_biofuel_on_presult.gms: 10 functions (step3_copies.copy) | part step3_copies (340 cases) |
| 08b06cb6 | C5.2 | labour_ageline.gms: 12 functions (labour.ageline_bounds, labour_bounds) | part labour (35 cases) |
| affe5bbe | C5.3 | mquota_update, load_quotas, reformsugarquotas, captrd_policy.gms: 29 functions (policy.apply); the tool's `--parts` | part policy |
| 1de49137 | C5.4 | estimate_trends.gms (7) and Step 1's statistics of define_stats_and_supports.gms (3) and prep_data_for_estimation.gms (3) (step1) | light part step1 (3,000 synthetic series) |
| abb29618 | C5.5 | clean_tiny.gms: 16 functions (clean_tiny.clean, the solve stubbed) | part clean_tiny (16 cases) |
| 68cd6e0d | C5.6 | scale_DG_AGRI_baseline.gms: 18 functions (scale_dgagri.scale) | light part scale_dgagri |
| bff808fd | C5.7 | adjust_to_biof_supports.gms (25), adjust_trade_supports.gms (9) (final_supports) | light part final_supports |
| d2226295 | C5.8 | agriprod_supports.gms: 22 functions | light part agriprod (reference data) |
| d64e6aef | C5.9 | longrun_supports.gms: 26 functions (longrun_supports, macro.inha_pdata) | light part longrun (a synthetic long-run scenario) |
| 665bb5d8 | C5.10 | define_eu_supports.gms: 49 functions (eu_supports) | light part eu_supports |
| 893afa25, 1b360331, 2fcc0a18 | C5.11 | expert_support.gms (58: expert_rules, dairy_supports, expert_support), national_supports.gms (16 general, 38 country rules) | light parts expert_support, national |
| a13835f9 | C5.12 | define_stats_and_supports.gms: 33 functions in all (supports, coco_supports, expert_support, dairy_supports, final_supports) | light part stats |
| 5ce1ec05 | C5.13 | prep_data_for_estimation.gms: 33 in all (prepare.prep_for_estimation, statistics) | light part prep |
| 50a6340a | C5.14 | load_coco1_data.gms: 27 functions (coco) | light part coco |
| e72a8f61 | C5.15 | captrd.gms's 3 data statements with arithmetic (prepare.load_fixes, load_basm, labour_household) | light part captrd_gms |
| 3e076e53 | C5.16 | biofuel_trends.gms: 92 functions (biofuel_trends.trends) | light part biofuel |
| 5310df2c | C5.17 | convert_globiom.gms (33) and create_longrun_info.gms (3) (globiom) | light part globiom (synthetic GLOBIOM tables) |
| 3d24e884 | C5.18 | load_aglink2023dgAgri.gms: 60 functions (aglink, macro.inha) | light part aglink (a synthetic Aglink cube) |
| cbfc688e | C6 | the hash order: of the scan's 81 places (docs/dev/captrd_set_order_places.csv now lists the 6 left, each order free, with a note) 75 iterate sorted; 19 more the scan cannot see, sets of CaptrdSets, aglink.Sets and globiom.Sets iterated under other names (coco's DOMM sums and mappings, globiom.mapped's region lists, aglink's mapped columns and rows, eu_supports.est_sets, eu_supports' and final_supports' pact_to_y and maact), sorted where iterated. The parity tool: --compare reports digest parts; its inputs built from sets are sorted | the full dump under PYTHONHASHSEED 0 and 1: IDENTICAL (before: 12 parts differed: coco, eu_supports, globiom's collect, mapped, factors, base_factors). Against 9c69ab7b at seed 0: those 12 parts differ, every other identical; coco 28 of 160,451 values (at most 2.1e-16 relative), globiom 17,331 of 2.4 million records (at most 6.7e-16), eu_supports' inputs reordered (est_sets sorted). Pipeline tests 56 passed, the same 14 capreg_base failures and errors |

Every C5 block: identical to 9c69ab7b on its part, with the light checks of section 3; the full dump and the pipeline
tests once, at the end of C5. **The end-of-C5 gate** (25 November, at 3d24e884, PYTHONHASHSEED=0 on both sides): the
full dump IDENTICAL to 9c69ab7b, every part (the 340 points' residuals, objectives, bounds and retries, and all C5
parts); the pipeline tests 55 passed, 21 skipped, 8 failed, 7 errors: the same 14 capreg_base tests as at C4, and one
new failure, test_captrd_coco_supports.py's use of coco_supports.TRUST_COCO, a constant C5.12 had made the literal of
DS.p_cocoSupport_TrustLevl (the test now reads it there; 56 passed, as at C4c). A scan of every `X.NAME` and import
of the captrd modules' names removed since 9c69ab7b found no other use (tests that skip here included).

The pipeline tests (`python -m pytest -q -p no:randomly -n 0 capri_mod/pipeline/tests`, about 4.5 minutes here):
at edb882ca **51 passed, 21 skipped, 7 failed, 7 errors**, at C4 **53 passed**, at C4b **55 passed**, at C4c **56
passed**, and the rest the same; at 9c69ab7b 43 passed of 78, the same skips, failures and errors (C1 added 5 tests, C2 1,
C3 2, C4 2, C4b 2, C4c 1, in
capri_mod/pipeline/tests/test_captrd_equations.py). Every failure and error is
`capreg_base/17/<CC>.csv.gz missing` (test_captrd_estimate_ms's step2 checks for DK, AT, ES, IT, NL, PL, NO;
estimate_bounds, estimate_nlp and estimate_nuts2's solves).

## 2. The style, as applied here

- One function per GAMS equation, CAPRI's name; the docstring: what it says, the arguments in this project's
  notation (V(c, w) = V_EstV(Rest, c, w, exAnteY), n(c, w) = nObs nonzero, M(c, w) the member state's fixed value in
  NUTS 2), then `CAPRI's GAMS, NAME (captrd/equations.gms l. a-b):` with the statement verbatim (column-1 `*` lines
  kept), then "Departures from CAPRI".
- The function returns the residual lhs - rhs; the caller holds the domain condition, the loops over the sets, the
  sense (E, L, G) and the names and indices of the rows.
- **Exactness.** The same operations in the same order, the literal values written as the port had them (`x * 0.8 +
  (-0.1)` and `x * 0.8 - 0.1` give the same float but different CasADi graphs: keep the form). The caller passes the
  terms as generators where the port summed in a loop, so `sum()` runs over the same sequence and V's symbols are
  created in the same order. A weight of 1 is not multiplied in (SSQS_ takes `g = None` for the member state).
- The line ranges: from the equation's name to the statement's closing `;`, `*` a comment only in column 1 (an
  indented `* V_EstV...` is a multiplication). Several citations of the port were off and are corrected: SSQS_
  803-878 -> 801-875 (with the p_weightStdErr scalar at l. 801), its STCM pull 838-841, EFED_ ends at 508, PosLo_ and
  the others of C1 at the ranges in the functions' docstrings.
- **Code data.** tools/check/make_code_data.py scans the literals by function. When a constant becomes a function's
  literal, its row in capri_data/schema/04_code_data_status.sql is re-keyed to (equations/equations.py or nuts2.py,
  the function, the value) with the same status and its corrected source lines; a value the scan does not list (0.1,
  1e-5, 1000, 10: round numbers it leaves out) loses its row. A constant that comes to stand alone in an assignment
  (PER_1000 in C3) gets a row. Then make_code_data.py, make_schema_json.py, and their --check.

## 3. The check (the gate of every block)

1. The reference data, once per container: capri_sources/reference (gitignored) needs captrd_results/1770,
   capreg_tseries/17 and sets/simini_21730. Without CAPRI's GDX files, build it from the published raw set
   (nuvolaTeam/capri-mod-raw, gated; the token through the environment's secret store, never in the repository):
   `python tools/build/build_reference_from_raw.py --list RAW` lists the files to fetch at the manifest's revision
   (two passes: the sets' list comes with the first), the curl line is in its docstring; then
   `python tools/build/build_reference_from_raw.py RAW` (10 minutes, about 1 GB of memory: p_result's 33 million
   records are streamed). 750 MB written.
2. A worktree at the starting commit, `git worktree add ../captrd_ref 9c69ab7b`, and in it a link
   capri_sources/reference to the checkout's (the package finds its reference next to itself).
3. `PYTHONPATH=../captrd_ref python tools/check/captrd_parity_dump.py ref.pkl` (the checkout's tool, the worktree's
   package: the tool is not in 9c69ab7b), `PYTHONPATH=. python tools/check/captrd_parity_dump.py new.pkl`, then
   `python tools/check/captrd_parity_dump.py --compare ref.pkl new.pkl`: IDENTICAL, 17 parts. About five minutes
   each: run the two dumps one after the other (two at once ran out of memory here).
4. The pipeline tests one at a time (`-n 0`), the counts of section 1 plus the block's new tests.
5. The static checks: tools/check/check_gams_quotes.py with `--expect supply/supply_model.gms=5557 --expect
   arm/market_model.gms=4607` on the changed modules (the default scope is supply and market), check_gams_citations.py,
   make_code_data.py --check, validate_data.py, make_provenance.py / make_schema_json.py / make_manifest_json.py
   --check, check_doc_coverage.py, flake8 --select=E9,F63,F7,F82.

The bounds part (bounds_cases) builds each BoundData from data.csv and the stored result positions; where the
reference has no statistic (BASM and BSY come from capreg_base, section 4) it is synthetic: BASM data's BASM, else
its BAS; BSY BAS x 1.05; EXTRA_DATA / EXTRA_RES add, at three member states, the inputs the reference does not reach
(negative OCRO and OANI bases, POUF, INTP, the quotas). A NUTS 2 region's BoundData carries the region's own code, as
the tests pass it. The NUTS 2 part (nuts2_bounds_cases) runs estimate_nuts2.bounds for those regions, the member
state's result its stored step3, and then the retries at a synthetic solve state (the bounds' midpoints as levels,
every third bounded position at its lower bound, the next at its upper, every fifth with a multiplier); it keeps the
SHA-256 of each region's exact bounds (the whole would be 570 MB). The member state's retries (ms_retries_cases) do
the same from estimate_bounds.bounds' bounds. For a block outside these (C5) the tool is extended first with that block's functions at given points; coverage (`python -m coverage run ...`) shows what the
inputs reach.

**C5's light checks.** A C5 block is checked on its own part only: `--parts NAME` dumps that part alone (tools/check/
captrd_parity_dump.py: LIGHT and LIGHT_CASES name the parts that read no estimation inputs; 2-40 seconds each), at the
reference worktree and at the checkout, then `--compare`. **Both sides with PYTHONHASHSEED=0**: some sums run in set
order (C6) and would differ between two processes. Most parts run the block's functions on seeded random inputs over
CAPRI's real sets (with the divisors nonzero where real data have them so); agriprod, prep, coco and biofuel read one or
two reference tables. The GLOBIOM and Aglink source files are not in this copy (their slow tests skip): globiom's and
aglink's parts are synthetic cubes written as Parquet over the real sets. Then the static checks of step 5, the
inventory rebuilt, and test_captrd_equations.py. The full dump and the pipeline tests run once, at the end of C5.

Two traps met in C5: a function that replaces a `+=` accumulation adds its values one at a time (Python's `sum()` of
floats is compensated since 3.12 and changes last digits); and GAMS evaluates an assignment's right side on the values
from before the statement, so a caller that loops keeps the old values where the port did.

## 4. What this container cannot check

- **The pipeline's outputs bit for bit** (the main session's first note). A CAPTRD-MOD run needs CAPREG's base data
  for the EU's countries (capreg_base/17), which the published set does not hold. Before the merge, in an environment
  with it: run the pipeline at 9c69ab7b and at the branch's head with the same PYTHONHASHSEED and compare the outputs
  with tools/check/compare_pickles_exact.py (`--rtol 0`) or byte for byte. C1-C4c change no arithmetic and no order of
  evaluation, so the outputs should be identical under any one seed.
- The 14 pipeline tests of section 1 (the same reason), and the FAO aggregates' parts (FAO_agg not published).

## 5. Next blocks

- **C5, done.** The inventory, docs/dev/captrd_inventory.csv (`python tools/check/captrd_inventory.py GAMS_DIR --out
  docs/dev/captrd_inventory.csv`, rebuilt after each block): at C5.0 1,725 citations, 658 statements to move; after
  C5.18 2,905 citations: 1,433 in the style (an equations module quoting the lines), 808 the callers' citations of
  moved statements, 562 context, 7 to check (data files outside the GAMS copy), **95 still "to move"**, none an
  assignment with arithmetic left in a caller:
  - set and time-set definitions, left as code (about 70): captrd.gms (38: timesets.py, prepare.py, prepare_run),
    convert_globiom.gms's region mapping and years kept and fao_codes_new.gms l. 559 (9), load_aglink2023dgAgri.gms's
    BasYrsT and FAOreg_AGMacroreg (6), and the S_ColsEst / S_RowsEst, Rest, RaggEst, rmAggSup, ROWS_LOAD and
    yrAgriProd sets of sets_captrd, estimate_ms, estimate_nuts2, define_eu_supports, prep_data_for_estimation,
    scale_DG_AGRI_baseline, load_coco1_data, agriprod_supports and the mappings;
  - the solves' side: solver options (equations.gms l. 896-902, estimate_ms.gms l. 222-229, estimate_nuts2.gms
    l. 404-430, clean_tiny.gms l. 270-284), the tries' count (estimate_ms.gms l. 452-456), the results' copies after a
    solve (clean_tiny.gms l. 296-327, rem_tiny.gms l. 35-53, estimate_nuts2.gms l. 500-508, aggreg_and_report.gms
    l. 293-294), fix_est.gms l. 196-200 and prep_requirement_estimation.gms l. 44-49: they need the heavy estimation
    parity, not a light part;
  - deletions and checks kept as such: agriprod's PercentChange deletions (Result.no_percent, l. 420-421, 486),
    captrd_policy l. 195-200, check_and_cor_capreg l. 27-28, expert_support's check_duplicates (l. 841-848),
    define_eu_supports l. 693 and 838-843 (single citations beside moved statements), labour_ageline l. 180;
  - not ported (findings below): national_supports l. 1481-1484 and 1569-1572, define_stats_and_supports' Support1
    (l. 673-675).
  `python - ` over the CSV with status == "to move" lists them with their module, function and line.
- **C5's findings** (listed, not fixed; each in its function's "Departures from CAPRI" where it is arithmetic):
  - the order of operations differs (the last digit may differ): labour_ageline l. 177 (0.995 raised to a power,
    CAPRI once a year); estimate_trends' t^(c+1) as t^c x t; clean_tiny's support x (0.05 / 3) x 10 / 2;
    adjust_to_biof_supports' DOMM additions before the subtractions (l. 86-91, 127-131, 221-225); national_supports'
    factor x ((1 + p/100) x BASM) (12 statements); the crop areas' scaling with 1 - 0.67 for 0.33 (define_eu_supports
    l. 628, final_supports.mcact_scale) and multiplied where CAPRI multiplies then divides; load_coco1_data's FEDM less
    the uses' sum and the split activities' 2 x the sum; captrd.gms's land uses by ARTO's share;
  - a division GAMS makes unguarded is guarded (0 where the divisor is 0): expert_support's nutrient means and
    isoglucose shares, biofuel_trends' UVAG ratio, load_aglink's parts' OU (l. 747-748);
  - not ported, no effect in the reference run: longrun_supports' B2000 HCOM condition (l. 53-54, taken for every
    scenario) and Longrun population (l. 362-366); national_supports' TUR trust (l. 1481-1484) and 2015/2020 resets
    (l. 1569-1572); define_stats_and_supports l. 301-323, 358-365 (the estimation's); load_coco1_data's
    p_result_MSnoEU, the aggregates, BAS and NT2excl; biofuel_trends l. 248-252, 464, 468, 1077-1103 (KWS, the port
    raises), 1269; convert_globiom's Q (l. 1613-1618); load_aglink's WORLD prices, p_aglinkUVAG and checks, macro GDP;
  - other: biofuel_trends' nObs of PRCB / PRCBY needs a PRCB support (CAPRI the feedstock use's); convert_globiom adds
    the perennial area where CAPRI assigns it (none in GLOBIOM-EU's files); supports.best_three_yields differs from
    statistics.bsy for fewer than three distinct yields; Support1 (define_stats_and_supports l. 673-675) is the tests'
    copy; several modules' citations were 1-40 lines off this GAMS copy and are re-cited (policy, biofuel_trends,
    aglink, create_longrun_info: l. 91-102, not 74-90).
- **C6, done** (section 1). A new set iteration in capri_mod/pipeline/captrd should be sorted, or written order free;
  `python tools/check/scan_set_order.py capri_mod` finds the plain ones, not those of sets passed to other functions:
  the check that finds those is the parity tool's dump under two seeds (`PYTHONHASHSEED=0` and `=1`, `--compare`).
  prepare.read_sets returns Python sets; estimate_ms.read_sets returns OSet (sorted iteration), which is why the
  estimation was seed-free before C6. Two lint findings in policy.py (an unused import, an unused local) date from
  9c69ab7b and are left.
- **The citations.** check_gams_citations.py checks only an equation's name next to its lines; the citations of the
  assignment modules (gams files other than equations.gms) are not checked by a tool yet: a block's own.

## 6. Rules kept

No merge into dev, no push to dev or main, no rebase or force push; refactor/assignments and its handoff untouched;
capri_mod/feed/equations not touched (the main session's open port); no CAPRI runs; nothing licensed or secret in the
repository (capri_sources/ is gitignored); commits with TZ=Europe/Rome and the session's attribution lines; a block
pushed only after its check passes.
