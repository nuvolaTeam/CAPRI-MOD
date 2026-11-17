# Refactor stage 3: the three changes left out of the moves (plan Q11)

**Codes used in this document.** The plan's internal codes are kept here as written; what they stand for:

- **Refactor stages 1-5** (ARCHITECTURE_REFACTOR.md section 3): 1 the market split by block; 2a the market's data adapter; 2b the market's parameters and state; 3 the supply (3a its methods into block mixins, 3b its data adapter, the second half its parameters and state); 4 the environment and the coupling (4a and 4c their methods into block mixins, 4b the run's data adapter, the second half their state); 5 the scenario and reporting layers.
- **S0a-S11 and N1-N6**, the refactor of the supply's parameters and state (REFACTOR_SUPPLY_PARAMETERS_PLAN.md section 4): S0a the tests before the moves, S0b the Hessian's restore by declared lists, S0c the state module, S1 the write-only names removed, S2-S3 the NLP block, S4 livestock and feed, S5 fertilisation, S6 land, S7 abatement, S8 policy and core, S9 the regional models' inputs, S10a/b the supply module, S11 the documentation; N1 the parameters through the data adapter, N2 CAPRI's constants, N3 the literature and scenario rules, N4 the physical constants, N5 the numerical numbers as settings, N6 the code tables as data.

The moves of stage 3 (docs/dev/REFACTOR_SUPPLY_PARAMETERS_PLAN.md, S0b-S10b) kept three behaviours as they were, because changing them
is not a pure move. This note says what each does today, when it can change a result, and what I propose. Read from the
code on 2 November 2026 (stage3b at 6ed4a05); nothing here is changed yet.

## 1. `sv.n_relax_sticky` is not restored by the market supply Hessian

**Today.** Where the tiered N target is infeasible, the regional model solves at JRC121368's relaxed target (the EU
average cut, 36%) and remembers it for the same target (`sv.n_relax_sticky`, fertilisation.py `_relax_n_target`), so
the next solve starts from the relaxed target instead of failing the tiered one again (supply_module.py
`_solve_inner`). The Hessian's restore lists (NLP_STATE, SOLVE_STATE) do not contain it: a price shock that relaxes a
region leaves the field set for the next shock.

**When it can change a result.** The key is the scenario's N target (`_n_relax_key`: the tiered target and the base
surplus); without an N target it is None and the field is never set. The Hessian is measured at the baseline, which
has no N target, unless `market.hessian_scenario_iter` > 0 (default 0: CAPRI measures once per baseline). So in the
default runs the field is never set during a measurement and the gap has no effect.

**Proposal.** Add `sv.n_relax_sticky` to SOLVE_STATE, so the restore is complete for the non-default case. Expected:
results identical in the default runs (check: mini-EU run identical at 1e-12).

## 2. `ev.ghg_applied` and `ev.ghg_nr_obj` (the emission tax's undo record)

**Today.** `_apply_ghg_tax` subtracts tax x emission from the activities' net revenues and keeps what it subtracted
(`ev.ghg_applied`) with the object it subtracted it from (`ev.ghg_nr_obj`). Called again on the same object, it adds
the previous tax back first, so the tax is never counted twice (capri_mod/tests/test_supply_state.py checks this).
`ev.ghg_nr_obj` is in SOLVE_STATE, so the Hessian's restore deep-copies it; a copy can never be the same object, so
after a restore the undo cannot act. `ev.ghg_applied` is not in the lists.

**When it can change a result.** Never in a run, as far as I can read the code: `_apply_ghg_tax` is called once per
solve (`_solve_inner`), and `_solve_once` sets the net revenues back to a copy taken at its start when it ends, so the
next solve's net revenues are always another object than the one the previous tax went to. The undo acts only when the
method is called twice within a solve on the same object (today: only in the test).

**Proposal.** Take `ev.ghg_nr_obj` out of SOLVE_STATE (restoring a deep copy of an identity reference is meaningless;
plan 3.4 already says it should never be copied). Expected: results identical (check as above).

## 3. `use_fert_allocation`: an instance copy shadows the class setting

**Today.** `use_fert_allocation` is a class attribute of RegionalSupplyModel, set by CAPRIModel at the first outer
iteration of every run (model.py, always False: "substitution already in the balance"). `_fert_params_raw`
(fertilisation.py) sets it to True on the instance around a call and then sets the instance attribute back to the value
it read, so every model that went through `_fert_params_raw` keeps an instance attribute that hides any later change of
the class attribute.

**When it can change a result.** Only if the class attribute is changed after a model went through
`_fert_params_raw` in the same process: CAPRIModel sets it to False and the instance copies are False, so today the
copy and the class agree and nothing changes.

**Proposal.** Restore the attribute as it was found: delete the instance attribute after the call if there was none
before (or pass the switch as an argument to `_fert_alloc_params`, the cleaner form). Expected: results identical.

## Summary

| change | effect in the default runs | check | proposal |
|---|---|---|---|
| 1. n_relax_sticky restored by the Hessian | none (set only with an N target; the Hessian is measured at the baseline) | mini-EU identical | add to SOLVE_STATE |
| 2. ghg_nr_obj out of the restore | none (the undo never acts across solves) | mini-EU identical | remove from SOLVE_STATE |
| 3. use_fert_allocation restored as found | none (class and copies are False) | mini-EU identical | delete the copy, or an argument |

All three make the code do what it says without changing today's results; each would be its own commit with its own
mini-EU check, after the numbers' steps (N1-N6). For the project lead's decision.
