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
  domain conditions and the loops.
- **Checked:** exactly (hex floats and CasADi text) against the starting commit 9c69ab7b, with
  tools/check/captrd_parity_dump.py on CAPTRD's own Step 2 points; the pipeline tests unchanged; the static checks.
- **Not checked here, and why:** a full CAPTRD run's outputs. The published raw set has no capreg_base (CAPREG's base
  year for the EU's countries), which the estimation's bounds, the NLP and the NUTS 2 solves read: those 14 pipeline
  tests fail or error here, before and after the refactor alike. The main session's environment has it: run the
  pipeline's outputs bit for bit there against 9c69ab7b before the merge (section 4).
- **Next:** C4 the bounds (fix_est.gms and the other bound files), C5 the supports and trends modules (an inventory
  first), then C6, the sort of the 81 hash-order places, **a commit of its own** (it changes last digits).
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
| (this commit) | tools | tools/check/captrd_parity_dump.py (the check), tools/build/build_reference_from_raw.py (the reference from the published Parquet), tools/check/scan_set_order.py (step 1's scan) and docs/dev/captrd_set_order_places.csv (its 81 CAPTRD places), this handoff | the parity tool reproduces the dumps of C1-C3; the builder reproduces the reference built for them (section 3) |

The pipeline tests (`python -m pytest -q -p no:randomly -n 0 capri_mod/pipeline/tests`, about 4.5 minutes here):
at edb882ca **51 passed, 21 skipped, 7 failed, 7 errors**; at 9c69ab7b 43 passed of 78, the same skips, failures and
errors (C1 added 5 tests, C2 1, C3 2, in capri_mod/pipeline/tests/test_captrd_equations.py). Every failure and error is
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
   `python tools/check/captrd_parity_dump.py --compare ref.pkl new.pkl`: IDENTICAL, 12 parts. About a minute and 2 GB
   each.
4. The pipeline tests one at a time (`-n 0`), the counts of section 1 plus the block's new tests.
5. The static checks: tools/check/check_gams_quotes.py with `--expect supply/supply_model.gms=5557 --expect
   arm/market_model.gms=4607` on the changed modules (the default scope is supply and market), check_gams_citations.py,
   make_code_data.py --check, validate_data.py, make_provenance.py / make_schema_json.py / make_manifest_json.py
   --check, check_doc_coverage.py, flake8 --select=E9,F63,F7,F82.

For a block outside the estimation (C4, C5) the parity tool must first be extended with that block's functions at
the reference's points (estimate_bounds.bounds needs capreg_base: see section 4).

## 4. What this container cannot check

- **The pipeline's outputs bit for bit** (the main session's first note). A CAPTRD-MOD run needs CAPREG's base data
  for the EU's countries (capreg_base/17), which the published set does not hold. Before the merge, in an environment
  with it: run the pipeline at 9c69ab7b and at the branch's head with the same PYTHONHASHSEED and compare the outputs
  with tools/check/compare_pickles_exact.py (`--rtol 0`) or byte for byte. C1-C3 change no arithmetic and no order of
  evaluation, so the outputs should be identical under any one seed.
- The 14 pipeline tests of section 1 (the same reason), and the FAO aggregates' parts (FAO_agg not published).

## 5. Next blocks

- **C4: the bounds.** estimate_bounds.py (770 lines; fix_est.gms 9 citations, estimate_ms.gms, comi_bounds.gms) and
  estimate_nuts2.bounds / _open_bounds / _grid_again (estimate_nuts2.gms, est_nuts2_grid.gms,
  est_Nuts2_grid_openbound.gms): assignments, so the assignments refactor's style (one function per GAMS statement,
  named after the symbol assigned). Its check needs the bounds at given points: the tests that compare them with
  CAPTRD's (test_captrd_estimate_bounds) need capreg_base, so in this container the check is the parity tool extended
  with synthetic BoundData built from the stored points.
- **C5: the supports and trends.** biofuel_trends (778 lines), national_supports (695), globiom (696), aglink (845),
  eu_supports (539), prepare (679), longrun_supports, dairy_supports, final_supports and the rest (the GAMS file each
  cites is in its docstring). Start with an inventory of their GAMS statements (as docs/dev/assignments_inventory.csv),
  then a block per GAMS file.
- **C6: the hash order.** docs/dev/captrd_set_order_places.csv: 81 places in 17 modules (globiom 19,
  national_supports 13, prepare 8, aglink 7, longrun_supports 7, policy 5, biofuel_trends 4, scale_dgagri 4, coco 3,
  expert_support 2, macro 2, requirements 2, dairy_supports, estimate_nuts2, eu_supports, statistics, timesets 1 each;
  `python tools/check/scan_set_order.py capri_mod` again after C4-C5, the lines move). Some are harmless (the
  estimate_nuts2 one is a list sorted on the next line); the rest are sorted with `sorted(...)`. **A commit of its own,
  after the moves**, since it changes last digits; its check is the pipeline under two seeds giving the same outputs.
- **The citations.** check_gams_citations.py checks only an equation's name next to its lines; the citations of the
  assignment modules (gams files other than equations.gms) are not checked by a tool yet: a block's own.

## 6. Rules kept

No merge into dev, no push to dev or main, no rebase or force push; refactor/assignments and its handoff untouched;
capri_mod/feed/equations not touched (the main session's open port); no CAPRI runs; nothing licensed or secret in the
repository (capri_sources/ is gitignored); commits with TZ=Europe/Rome and the session's attribution lines; a block
pushed only after its check passes.
