# Brief: CAPRI's equations as named functions (refactor of the supply side, block N1 first)

For the work on the branch `refactor/supply-equations`. The project lead decides each block's start and its merge.
Scope (decided 19 November 2026): the whole supply side, block by block; the inventory of CAPRI's supply-model
equations, `docs/dev/supply_equations_inventory.csv` (built by `tools/refactor/supply_equations_inventory.py`), lists
them all with the module each goes to and whether CAPRI's 2030 Green Deal step has it (173 of the 232 equations of
CAPRI's simulation model m_capModQ). Its status and model_location columns are written by hand as each block is done; N1's rows
carry the mapping of section 3's table, to be checked when N1 moves the code.

**Note of 20 November 2026:** the line numbers and counts in this document are those of CAPRI's July 2026 release (course_capri_git/gams, the Docker image caprithuenen/capri:latest; supply_model.gms 5,631 lines, 232 equations), read as star 3.0 until the correction of 20 November 2026 (docs/dev/EQUATION_REFACTOR_HANDOFF.md). CAPRI star 3.0, the code of the project lead's runs, has 228 equations, 162 of them in the Green Deal step; its lines are in the inventory and in the code's docstrings. This plan is kept as written.

## 1. Goal

Each CAPRI equation the model ports becomes a named function, so one can read the equation and find it in the code
without reconstructing it from a long builder. Today the regional NLP's fertilisation block is one method,
`CapriRegionalNLP._fert_block` (capri_mod/supply/capri_regional_nlp.py, about 215 lines), that writes NUTNED_, the
three pools, the inner model's first-order conditions, the regulations, the purchases' costs and the N-surplus rows
in one loop. After the refactor `_fert_block` is a short composition of calls, one per CAPRI equation.

This is a move, not a change: the model must give the same results to 1e-10 (section 4). The rule of
docs/dev/ARCHITECTURE_REFACTOR.md section 2 holds: moves and behaviour changes never share a commit.

## 2. Conventions

- **One function per CAPRI equation** (or equation family over its sets), named as CAPRI's equation: `NUTNED_`,
  `fertDistCres_`, `fertDistExcr_`, `e_fertDistPartial`, `e_fertDistReguMax`, `e_fertDistPartialRegu`,
  `e_focFertDist`, `e_synNMax`, `SURTOT_REST_`; where a function writes one term of CAPRI's equation, the term is
  added to the name (`fertDistCres_idlHis`). Pure functions, taking the symbols they need and returning the row
  expressions (and their bounds); the NLP builder calls them and keeps the bookkeeping (row indices, scales).
- **Layout: one module per CAPRI source file, and for a large file one module per block of the file.** CAPRI's
  supply/supply_model.gms becomes the sub-package `capri_mod/supply/equations/supply_model/`, one module per block of
  the file as its own banners divide it (`nutrients.py`, `n_surplus.py`, `inner_fert.py`, `premiums.py`,
  `set_aside.py`, `land.py`, `feeding.py`, `objective.py`, `mitigation.py`, ...; the inventory's planned_module);
  another CAPRI file gets a module named after it (`fertned.py` for fert/fertned.gms). The sub-package's
  `__init__` maps each module to its CAPRI block and lines.
- **Arguments and locals named as CAPRI's symbols** where the correspondence is one to one (`v_fertDist`,
  `v_dualNutNed`, `v_dualNutSup`, `p_priFertDist`, `p_priFertDistRegu`, `v_fertDistReguSlack`). Where the model's
  quantity differs (flows in t scaled by their prior mode, rows scaled by `sc_`, the technology mix columns z), the
  docstring says how it maps to CAPRI's.
- **Docstring of each function**, in this order:
  1. the CAPRI equation's name and its domain (e.g. `NUTNED_(r, ngrp, fnut)`);
  2. the source: file and lines of CAPRI star 3.0 (e.g. `supply/supply_model.gms l. 1103-1220`);
  3. CAPRI's GAMS statement of the equation (above), then the equation in our own notation (LaTeX-like plain text
     or the notation of docs/equations/), with how the model's quantities map to CAPRI's symbols;
  4. the differences from CAPRI's equation, each with its register entry (DEPARTURES_FROM_CAPRI.md, KNOWN_ISSUES K
     numbers, the settings that switch it).
- **CAPRI's GAMS statement of the equation** heads its block (decided 19 November 2026): the equation as CAPRI
  writes it in GAMS, quoted in the docstring of the function that writes the equation (the project lead, later on
  19 November 2026: in the function, not gathered in the module's docstring; a function writing one term of an
  equation names the function that holds its GAMS), followed by the equation in our notation. The module's
  docstring keeps the block's overview, the notation its functions share and the departures.
  It is the equation's text for the reader, not GAMS code to run; quote the equation only, not the surrounding code.
- Most of the code already cites CAPRI's lines in its comments; keep and move every citation and every departure
  note with the code it belongs to. Verify a citation against CAPRI's GAMS sources where they are available; if a
  citation looks wrong, list it (section 5), do not change the code.

## 3. Block N1: the fertilisation block of the regional NLP

| CAPRI equation | CAPRI source (star 3.0) | the model's code now |
|---|---|---|
| fertDistCres_ (the residue pool) | supply/supply_model.gms l. 1049-1088 | `_fert_block` (pool rows, "C"); spec: fertilisation.py `_npk_spec` ("C", K181's mix term) |
| fertDistExcr_ (the manure pool), ManureNPK_, manExportOrAppl_, InclEmiAppl_, e_netMTrade, e_costMTrade | supply/supply_model.gms l. 878-890, 935-955, 962-978, 984-1044, 900-909, 913-925 | `_fert_block` (pool rows, "E", `E_const`, `amm_kept`); `self.excr_rows` |
| fertDistMine_ (the mineral pool: v_fertDist mine against the purchases v_netPutQuant) | supply/supply_model.gms l. 1093-1099 | `_fert_block` (`pool_sum("MINE") - P`) |
| NUTNED_ (the crop groups' need balance), the permanent crops' own residues | supply/supply_model.gms l. 1103-1220 | `_fert_block` (NUTNED_ loop); spec: `_npk_spec` ("need", "own") |
| GASTOTNETF_, RUNTOTNETF_, GASRUNTOTNETF_ (NUTNED_'s mineral and residue efficiencies) | supply/supply_model.gms l. 3352-3411 (n_flow.py's block; written with N1 because NUTNED_ uses them) | `CapriRegionalNLP._netf_eff` |
| e_fertDistPartial (the gamma prior's derivative) and its slack v_fertDistPartialSlack | supply/supply_model.gms l. 1543-1561; supply/set_fert_priors.gms l. 668-785 | `_fert_block` (first-order conditions, `sl_`) |
| e_fertDistReguMax, e_fertDistPartialRegu (the regulations' beta density) | supply/supply_model.gms l. 1579-1606 (and the alternative form, l. 1668-1691); supply/set_fert_priors.gms l. 260-345, 570-610 | `_fert_block` (`regs`, `support_margin`); fert/inner_fert_dist.py `beta_regulation` |
| e_focFertDist (the inner model's first-order conditions), with DEP K159's complementarity form | supply/supply_model.gms l. 1613-1649 (and l. 1698-1733) | `_fert_block` (the `term` and the Fischer-Burmeister row) |
| e_fertDistPerHa | supply/supply_model.gms l. 1740-1745 | the regulations' support Y (area x max per ha) |
| e_synNMax (minfert_redu_uaa), nGrpLevl_, nMax_ | supply/supply_model.gms l. 4537-4539, 4507-4513, 4518-4531 (fert_limits.py's block); pol_input/greendeal/minfert_redu_uaa.gms | `_fert_block` (`synNMax`) |
| the caps by crop group (f2f, limCres; small groups; organic target's) | pol_input/greendeal/minfert_redu_by_crop.gms, organic_minfert_redu.gms | fertilisation.py `_npk_mineral_cap`, `_npk_organic_cap`, `_merge_organic_regs`; inner_fert_dist.py `mineral_caps`, `small_mine_groups`, `limcres_caps` |
| the purchases' cost, the fertiliser options' cost on them (GHG_Mit_Cost_), the N2OSYN tax | supply/supply_model.gms (objective, GHG_Mit_Cost_) | `_fert_block` (the `obj` terms, `_fert_tech_pending`, `ghg_min`) |
| SURTOT_REST_ with e_SURTOTHa in the NLP form (the mineral parts replaced by the purchases) | supply/supply_model.gms l. 1875-1879, 1471-1483 (n_surplus.py); pol_input/greendeal/surptot.gms | `_fert_block` (`n_rows`); fertilisation.py `_n_row_mineral_parts` |

The lines are the definitions' as the inventory finds them; the function's docstring gives the exact ones of the
term it writes.

Out of N1 (later blocks, each its own decision): the accounts' N balance (environmental/nitrogen.py; its map is
docs/equations/01_regional_n_balance.md), the technology mix (supply/techn_mix.py), the abatement block
(`_abatement_block`), livestock and feed, land, the market.

**Things to keep exactly** (the NLP must stay the same problem):
- the order of the variables and of the rows in `g_rows`, `lbg`, `ubg`, `lbx`, `ubx`, and every scale
  (`pv(1.0 / sc_)`, `Pscale`, `T`, the modes `m`);
- the bookkeeping other methods read: `self.fert[nut]` (rows, flows, groups, pools, offsets, `regs`),
  `self.excr_rows`, `self.synN_row`, `self.n_rows_g`, `self.fert_rows`, `self.fert_x0`, `self._fert_tech_P`;
- the order of floating-point operations where it is cheap to keep (a different association can move results in
  the last digits; the gate's tolerance is 1e-10);
- the block-mixin pattern: methods of `FertilisationBlock` and the other blocks use module-level names injected from
  supply_module (`capri_mod.utils.mixins.inject_names`); a function moved to a new module imports what it uses.

## 4. The gate for each block (before, after, compare)

At the block's starting commit, record a reference; after the refactor, the same run must reproduce it.

```bash
# reference, at the starting commit: CAPRI's 2030 Green Deal step (lnds8 org18 pest20 mine13crp surp30),
# three units of the N-surplus diagnosis (Spain, France, Germany); runs/ is not tracked by git; the run script
# fixes Python's hash seed itself, so a run repeats exactly
python tools/run/run_f2f_2030.py runs/N1_ref.pkl --scenario greendeal2030 --regions ES420000,FR520000,DE210000
# after the refactor, the same command
python tools/run/run_f2f_2030.py runs/N1_new.pkl --scenario greendeal2030 --regions ES420000,FR520000,DE210000
python tools/check/compare_pickles_exact.py runs/N1_ref.pkl runs/N1_new.pkl --rtol 1e-10 --ignore meta.time_s
```

Then the block's tests (capri_mod/tests/test_techn_mix.py, test_fert_option_cost.py, test_mineral_n_losses.py,
test_manure_applied_share.py, and `python -m pytest capri_mod/tests/test_capri.py -k "fert or npk or mineral or
nlp"`). The gate runs for every block; the full suite is batched (decided 19 November 2026): after N1, then after
every two or three blocks. Before blocks are handed over for merging: the full suite (`python -m pytest -q -p no:cacheprovider
capri_mod/tests`; a few hours), the pre-commit checks (section 6) and, once per merge, the full-EU Green Deal run
against a reference run made at the starting commit (the project lead or the diagnosis session provides it).

A difference at the gate means the move changed something: find it and undo it; do not adjust the reference.

## 5. What not to do

- No fix of a defect found on the way, even an obvious one: write it in the hand-over (section 7) with file, line
  and why; it becomes a KNOWN_ISSUES entry and its own commit later.
- No change of data, settings, defaults or tests' expected values. New tests are welcome (a pure function tested
  alone), as long as the old ones are untouched.
- No new hardcoded numbers (parameters belong in capri_data/codes/model_parameters.csv or the settings).
- Nothing licensed or secret in the repository (no licence files, tokens or third-party solver libraries).
- No push to `dev` or `main`; work on the branch `refactor/supply-equations` and push only that branch to GitHub
  (the project lead, 19 November 2026, 18:44: CAPRI's GAMS text in the code is no problem). `yani-rounds` is merged
  into the branch after every commit there (a merge, not a rebase: the branch is pushed and is never force-pushed),
  so each block starts from the latest results.

## 6. Commits

One commit per equation family or per coherent step (each passing the gate), message in the project's style: a
first line naming the step, a body saying what moved where and that the gate passed (the compared run and the
tests). Before each commit:

```bash
python tools/check/make_code_data.py --check
python tools/check/make_provenance.py --check
python tools/check/make_schema_json.py --check
python tools/check/make_manifest_json.py --check
python tools/check/validate_data.py          # 0 violations
python tools/check/check_doc_coverage.py
flake8 . --select=E9,F63,F7,F82
```

The code-data registry (03_code_data.sql) records line numbers of the code that reads data; regenerate it with
`make_code_data.py` when lines move, as part of the same commit.

## 7. Hand-over

At the end of the block: the branch, the list of commits, the gate's results (the comparison's output, the tests,
the full suite), a table of the new functions (CAPRI equation, function, file), the citations found wrong, the
defects noted, and any place where a one-to-one naming with CAPRI was not possible and why. Update
docs/equations/README.md's table of pages with a new page for the block (docs/equations/02_fertilisation.md, in the
format of page 01), citing functions, not line numbers.
