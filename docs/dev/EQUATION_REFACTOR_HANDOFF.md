# Handoff: the refactor of CAPRI's supply equations (branch `refactor/supply-equations`)

Written 19 November 2026 for the session that continues the refactor (Claude Code in the cloud). The rules of the work
are in docs/dev/EQUATION_REFACTOR_BRIEF.md (conventions, the gate, what not to do, commits, hand-over); this file says
where the work stands, how to set up, and what comes next. The project lead decides each block's merge.

## 1. What the refactor is

Each CAPRI equation the model ports becomes a named function, CAPRI's name, in
`capri_mod/supply/equations/supply_model/<block>.py`, one module per block of CAPRI's supply/supply_model.gms (the
file's own banners). Each function's docstring quotes CAPRI's GAMS statement of the equation it writes (the project
lead, 19 November 2026: GAMS text in the code is no problem; in the function, not gathered at the module's top),
gives CAPRI's file and lines, the equation in this project's
notation and the departures. The builders (capri_regional_nlp.py, supply_module.py, fertilisation.py, ...) call the
functions. **A move, not a change: results identical to 1e-10**, checked by a gate run for every block.

## 2. State at handoff

| commit | what | check |
|---|---|---|
| 8c4bde1 | the inventory of CAPRI's supply-model equations (docs/dev/supply_equations_inventory.csv, 232 equations of m_capModQ, 173 in CAPRI's 2030 Green Deal step; tools/refactor/supply_equations_inventory.py; the switches of the Green Deal step, docs/dev/supply_equations_gd_switches.csv); the brief updated | docs only |
| d20b652 | the layout: equations/supply_model/ with nutrients.py, n_surplus.py, mitigation.py (K183's and K184's functions moved, unchanged) | gate identical; tests |
| N1 | the fertilisation block of the regional NLP (CapriRegionalNLP._fert_block): NUTNED_, the pools, ManureNPK_'s terms, the inner fertiliser model (inner_fert.py), e_synNMax (fert_limits.py), SURTOT_REST_ | gate identical (see the branch's log for the commit) |
| N2 | CAPRI's N loss cascade (GRAZN_ ... GASRUNTOTNETF_) from capri_mod/supply/n_cascade.py into n_flow.py | gate identical (against a run at 80795e0); the cascade's expressions identical for every region and activity |
| N3 | the leaching: LEACHN_ (with its first factor LEACHN_B1) and AMMOAGG_ into n_flow.py, from supply/n_leaching.py and the accounts (environmental/nitrogen.py) | gate identical (one run with N4, against the run at N2); the functions' values bitwise equal for every CAPRI region and both signs of FIX-2 |
| N4 | the fertilisation block's objective terms: LINEAR_'s purchases and carbon tax on mineral N (objective.py), GHG_Mit_Cost_'s targFertSyn base (mitigation.py) | gate identical (one run with N3); the NLPs identical with and without an emission tax |
| N5a | the options' bounds: CAPRI's TotMitFertMin_, TotMitFertMan_, Tot_soilCov_ (mitigation.py's docstring) | docstrings only |
| N5b | the ammonia options (CapriRegionalNLP._abatement_block): TotMit_, GHG_Mit_Cost_ on the herd, manExportOrAppl_'s N kept, the emission tax | one gate with N5c; the NLPs identical, also with the taxes, free shares and no N block |
| N5c | the fertiliser options and the inhibitor on manure: Tot_MitFert_, TotMit_, GHG_Mit_Cost_'s parts, NUTNED_'s NMAN term, the tax | gate at N5c (with N5b); the NLPs identical |
| N5d | the catch crops: winterCover_, catcMiti_, ecoSetAside_'s term (premiums.py), GHG_Mit_Cost_ on the UAA, the BioFix N, the tax | gate at N5d; the NLPs identical; K186's two porting differences kept and listed (section 6) |
| N6 | the options' terms of GASTOTNETF_ and RUNTOTNETF_, NUTNED_'s factors at the options' shares (CapriRegionalNLP._netf_eff) | _netf_eff identical for every region (229 regions, 3 winter-cover cases); the NLPs identical; gate with N8 |
| N7 | the mitigation block's other rows classified (inventory statuses with evidence); the switch table's envConst corrected to OFF, the inventory rebuilt (161 equations in the step) | docs only |
| N8a | the base QP's land balances (arable_land, permanent_land, grassland) as LandBalNoSlak_ (supply_model/land.py) | 442 QPs identical bit for bit (221 regions, with and without a set-aside floor); gate with N8b |
| N8b | the land market (supply/land.py _land_augment): LandMarket_, LandBalNoSlak_ on the land columns and at the base use, e_artoBal, the grassland floor | the functions identical bit for bit to the old code (2,000 random cases); gate at N8b (one run for N6-N8b) |
| N9a | the landscape floor as e_setaLandscape (supply_model/set_aside.py) | 442 QPs identical bit for bit (221 with the floor row); gate with N10 |
| N9b | the idled histosols' bound as idleHisto_ (set_aside.py) | identical bit for bit to the old code (3,000 random cases); gate with N10 |
| N9c | the set-aside block and greenOverShot_ classified (inventory statuses with evidence) | docs only |
| N10 | the entitlement limit (overShotEntl_ with sumEntl_) and the permanent grassland rule (permGrasGreening_) in premiums.py | identical bit for bit to the old code (3,000 random cases); gate at N10 (one run for N9a-N10) |
| N11a | the N surplus's terms in the accounts and, through them, the QP's N-surplus row (e_EXCRET, e_GASRUNANI, e_ATMOSD, e_CRESID, e_EXPPRD, e_BIOFIX; environmental/nitrogen.py, phosphorus.py) and the leaching's input shares (nminInputSh_, nmanInputSh_) in n_surplus.py; SURTOT_idlHis on e_ATMOSD and e_CRESID | the N and P accounts, every activity's unit balance and the leaching identical bit for bit for the 221 regions (base and scaled yields, with intensity factors); gate with N11b |
| N11b | the surplus block's and the fertiliser limits' other rows classified (inventory statuses with evidence): SURSOI_REST_, nGrpLevl_, nMax_, lsDensMax_ and e_manureLimit_ empty in the step; e_SURSOIkt, e_SURSOIHa, e_GASRUNMIN and e_GASRES not written (the soil surplus, read by NO3LEA_: N14) | docs only |
| N12a | the feeding rows of the regional NLP: REQSE_ (with its total form for the split and option columns) and FEDUSE_ in supply_model/feeding.py, QUADRF_ with QUADRF1_ in objective.py; SupplementPerc_ classified (K93) | the NLPs identical (3 regions x 6 variants: expressions and parameter vectors bit for bit); gate with N12b |
| N12b | SUPBAL_ for the non-tradable fodder (supply_model/markets.py: the QP's fodder rows, supply/livestock.py _fodder_rows, and the NLP's equalities); INPANI_ classified (its use per head in the net revenues) | 221 x 2 QPs identical bit for bit; the NLPs identical (3 regions x 6 variants); gate at N12b (one run for N11a-N12b) |
| N13 | the objective: LINEAR_'s activity terms (LINEAR_netRevenue, supply_module._compute_net_revenues), QUADRA_ with GRPLEVL_ (QUADRA_lin, QUADRA_), OBJEQF_ in objective.py; labCap_ not written, fixTechfShares_ empty in the step, e_exogenousLand classified | the NLPs identical (3 regions x 6 variants); the net revenues and linear coefficients identical bit for bit for the 221 regions (base and a price shock); gate with the next batch |

Not on the branch (on purpose):
- `docs/equations/` (the equation book, page 01 the regional N balance) and its README paragraph: waiting for the
  project lead's decision on publishing.

The main line goes on in the other session (branch yani-rounds, pushed to `dev`). At handoff its next commit is K185
(fallow and set-aside without a nutrient need, as CAPRI's fert/fertned.gms; capri_mod/supply/equations/fertned.py)
with capri_mod/settings/capri_comparison.toml; it touches fertilisation.py (_npk_spec's need), environmental/
phosphorus.py and the tests. **Merge `origin/dev` into this branch after each push to dev** (a merge, never a rebase
or a force-push: the branch is public); the conflicts to expect are small (fertilisation.py's need line and its
imports).

## 3. Setting up

- Repository: github.com/nuvolaTeam/CAPRI-MOD (public), branch `refactor/supply-equations`. Python >= 3.11,
  `pip install -e ".[dev]"` (casadi bundles IPOPT; the default linear solver is MUMPS,
  `supply.nlp_linear_solver = "mumps"`: no HSL, no GAMS, no CONOPT needed).
- The model's data are in the repository (capri_data/, 806 declared files). A run needs nothing else; it writes the
  market supply Hessian cache to .cache/ (keyed by the code's fingerprint, so a move gives a new cache file: the gate's
  metadata differences).
- **CAPRI's GAMS sources are needed** to quote each equation and to rebuild the inventory, and they are not in the
  repository or on Hugging Face: the project lead provides CAPRI star 3.0's `gams/` folder (the copy used here:
  course_capri_git/gams). Files used so far: supply/supply_model.gms, supply/supply_model_e_list_linear.gms,
  _quatratic.gms, _FOCfert.gms, supply/set_fert_priors.gms, fert/fertned.gms, capmod/def_fert_and_requirements.gms,
  sets.gms, pol_input/greendeal/*.gms. The right copy: supply/supply_model.gms has 5,631 lines and names
  GAEC_soilCover_, and the inventory rebuilt from it reproduces docs/dev/supply_equations_inventory.csv byte for byte
  (an older copy, 5,557 lines, 228 equations, does not). Keep it outside the repository.
- Machine: a three-unit Green Deal run takes about 1.5 GB and 13-20 minutes on two cores (22-24 minutes in a cloud
  session); a run from a separate checkout pinned at the block's commit (git worktree) leaves the main tree free
  for the next block; the full suite about 3
  hours (test_capri.py alone about 85 minutes).

## 4. The procedure for a block (the brief, section 4)

```bash
# at the block's starting commit (or reuse the previous block's "after" run: same code)
python tools/run/run_f2f_2030.py runs/<B>_ref.pkl --scenario greendeal2030 --regions ES420000,FR520000,DE210000 --label ref
# after the move
python tools/run/run_f2f_2030.py runs/<B>_new.pkl --scenario greendeal2030 --regions ES420000,FR520000,DE210000 --label new
python tools/check/compare_pickles_exact.py runs/<B>_ref.pkl runs/<B>_new.pkl --rtol 1e-10 --ignore meta.time_s
```

Identical means only `$.meta.` lines differ (11 so far: names, times, the Hessian cache file). Run with
PYTHONHASHSEED=0 (the run script sets it itself). Then the block's tests; the full suite after N1 and then every two
or three blocks. Before each commit: make_code_data, make_provenance, make_schema_json, make_manifest_json with
--check; validate_data (0 violations); check_doc_coverage; `flake8 . --select=E9,F63,F7,F82`; test_portable_paths,
test_run_manifest. Commit messages in the project's style (the branch's log has examples), ending with the
attribution lines the session gives. Push only this branch.

**Keeping a move identical.** Keep the operands, the expression tree and the order of the parameter calls (the
regional NLP's `pv()` appends to the parameter vector in call order): pass `pv(...)` as arguments in the order the
old expression called them, and build the same left-to-right expression inside the function. Check a moved function
against the old one with CasADi SX (`str(expr)` equal) before the gate; for pure-Python code, compare the syntax trees.

## 5. What comes next

**The plan for everything after N5 is docs/dev/EQUATION_REFACTOR_PLAN_REST.md** (the project lead, 19 November 2026:
N6-N15, the statuses each equation ends with, the merge of K185, the gate's rules). The list below is the earlier
plan, kept for its notes on where the code lives.

The inventory (planned_module, in_gd2030_step, model_files_citing; the status columns filled for the blocks done)
is the list. In CAPRI's 2030 Green Deal step, by module: mitigation 23, lulucf 17, n_surplus 17, n_flow 14, land 12,
set_aside 11, objective 10, nutrients 10, n2o 10, air_water 10, premiums 8, methane 6, sugar 6, inner_fert 6,
fert_limits 4, gwp 4, feeding 3, markets 1, young_animals 1. Proposed order:

1. **N2, n_flow.py**: capri_mod/supply/n_cascade.py's `losses()` and `netf()` split into GRAZN_,
   HOUSN_, STORN_, RUNHOUSN_, RUNSURFN_, APPLN_, RUNTOTN_, GASRUNTOTN_, GASTOTNETF_, RUNTOTNETF_, GASRUNTOTNETF_ (each
   writing its entries of v_emiLoss in the old order), `losses()` and `netf()` their compositions; n_cascade.py keeps
   load(), activity_losses(), mineral_n2o_n(); the seven callers (environmental/nitrogen.py, phosphorus.py,
   supply/capri_regional_nlp.py, supply_module.py, ammonia_techs.py, fertilisation.py,
   tests/test_mineral_n_losses.py) import the equations from n_flow; tools/build/build_code_lists.py reads the
   technology lists from n_flow.py. Tried on a scratch copy before the handoff: the split functions give the same CasADi
   expressions as the old losses() and netf() (str() equal, the entries in the same order) and the callers import
   cleanly; an import of n_cascade or n_flow belongs only in the scopes that use it (flake8 F401). The drafts are in the
   claude.ai Project CAPRI+ (claude/refactor_n2/n_flow_draft.py, the module with CAPRI's GAMS text; n2_apply_draft.py,
   the edit script, which expects the module next to it as n2_n_flow.py). Done (N2); LEACHN_ and AMMOAGG_ done (N3);
   left: CapriRegionalNLP._netf_eff (the options' terms of GASTOTNETF_ / RUNTOTNETF_, written as the base efficiencies
   plus the change from the base point, so the base is CAPRI's reported one: the model's composition around
   n_flow.netf, with the options' othImpact 1 - (1 - lit)(1 + NMIN) of ghgMiti.gms; a block of its own with the
   mitigation block).
2. **The fertilisation block's objective terms**: done (N4).
3. **mitigation.py**: CapriRegionalNLP._abatement_block (capri_regional_nlp.py, about 180 lines): TotMit_,
   TotMitFertMin_, TotMitFertMan_, Tot_MitFert_ (restMitFert), catcMiti_, the ammonia options' cost and the manure N
   they keep, the inhibitor on manure; with supply/abatement.py (the histosol columns, idleHisto_).
4. **n_surplus.py, the rest**: e_EXCRET, e_EXPPRD, e_BIOFIX, e_MINFERT, e_MTRADEHa, e_GASRUNANI, e_GASRUNMIN,
   e_GASRES, e_SURSOIHa, nminInputSh_, nmanInputSh_: the coefficients of the regional N-surplus row
   (supply_module.RegionalSupplyModel._build_constraints "N_balance", fertilisation._n_row_mineral_parts, supply/
   land.py's form per ha of current land).
5. **premiums.py, set_aside.py, land.py**: sumEntl_, overShotEntl_ (supply/entitlements.py, policy.py); the greening
   rows permGrasGreening_, ecoSetAside_, cropDivGreening_ (capri_regional_nlp.py "CAP greening"); winterCover_,
   e_minCoverCrops (abatement.py); e_setaLandscape (supply_module "landscape_floor"); e_maxLevl / e_minLevl (the
   bounds rows); LandBalNoSlak_, LandBalSlak_, e_UaaNoSlak, e_artoBal, LandMarket_, e_exogenousLand
   (_build_constraints "arable_land", "grassland", "permanent_land"; supply/land.py).
6. **feeding.py, markets.py, young_animals.py, objective.py**: REQSE_, FEDUSE_, SupplementPerc_ (capri_regional_nlp.py
   REQSE_ and the fodder rows; feed/ration.py); SUPBAL_ (the fodder balances); INPANI_; LINEAR_
   (supply_module._compute_net_revenues), QUADRA_ (the PMP matrix), QUADRF_ / QUADRF1_ (the feed terms), GRPLEVL_,
   labCap_, fixTechfShares_.
7. **The emission blocks** (methane, n2o, air_water, gwp, lulucf: 47 equations in the Green Deal step): in CAPRI's
   supply model they are definitional rows (v_GWP..., v_emiLoss totals), binding only under an emission price or cap;
   the model computes them in the accounts after the solve (capri_mod/environmental/), and in the regional NLP only
   where a price acts (supply/ghg_tax.py). **To decide with the project lead** before moving: functions in
   supply_model/ used by the accounts, or CAPRI's names kept in environmental/.
8. **sugar.py** (6): CAPRI's sugar quota equations; check first whether CAPRI's 2030 data activate them
   (p_technFact(SUGB, VCOF)); without quotas after 2017 they may be empty.

Off in CAPRI's 2030 Green Deal step (not to port now): the BFP indicators, the water block, the pesticide
disaggregation, REQSN_ / MAXSHR_ / MINSHR_ (feedVersion _pw), NUTMIN_, e_uaar / e_asym / e_landSupCost (Trustee land
supply on). The model writes MAXSHR_ and MINSHR_ terms (capri_regional_nlp.py, feed/ration.py): when the feeding block
comes, check against CAPRI's _pw feed version and register what differs.

## 6. Found on the way (to list in the hand-over, not to fix in a move)

- CAPRI line citations corrected so far (the code cited an older supply_model.gms, typically 8 lines early): K184's
  fertDistCres_, e_ATMOSD, e_CRESID, e_SURTOTHa; GHG_Mit_Cost_ (5057-5190), InclEmiAppl_ (984-1044), ManureNPK_
  (935-955), manExportOrAppl_ (962-978); NUTNED_'s losses (1151, 1204, 1219), e_focFertDist (1629-1642), the mineral N
  loss equations (3352-3411). The gamma prior is set_fert_priors.gms l. 230-237 (the code's l. 668-785 is the
  partial derivative's slack).
- tools/build/build_n_cascade.py imports `write_source` unused (flake8 F401; not in the selected checks).
- **Porting differences of N5 (KNOWN_ISSUES K186, the main line's fix; kept identical in the move):** (1) CAPRI's
  catcMiti_ scales the catch crop area with the current land (sum over landTypesNoSlak of v_actLevl), and
  GHG_Mit_Cost_ charges winter cover on v_actLevl(uaaEqu); the model takes the fixed base UAA (supply/abatement.py
  l. 84, the base crop levels' sum) in the area of winterCover_, the cost, the ecoSetAside_ term and fertDistCres_'s
  BioFix N. (2) winterCover_'s right-hand side: CAPRI's DATA(UAAR) plus the fallow floor; the model's
  max(uaa + floor, cov0 + m0 x uaa) (abatement.py l. 92), whose max() is not in CAPRI.
- **envConst is off in CAPRI's Green Deal step** (the switch table, docs/dev/supply_equations_gd_switches.csv, had it
  on): pol_input/greendeal/refpol_endotech_all_sup.gms's `$exit` at l. 398 comes before its `$setglobal envConst on`
  (l. 408); the default, capmod/set_global_variables.gms l. 244. So the ten envConst rows of the mitigation block and
  ecoSetAside_ and cropDivGreening_ (supply_model_e_list_linear.gms l. 235-236) are empty in the step; the model
  writes ecoSetAside_ and cropDivGreening_ in its Green Deal runs and the 2030 reference: KNOWN_ISSUES K187 (the main
  line). Every other switch set after that `$exit` is to be checked against its default (endoManAvFact: on, l. 52).
- **Porting differences of N8 (for the main line; kept in the move):** the base QP's land rows' right-hand side is
  max(the land data, the base area) (supply_model/land.py LandBal_rhs; CAPRI: the land type's level); the land
  market's Q has a 1e-9 I regularisation; LandBalNoSlak_ holds at the base use (crops - land = base crops - base
  land; the model's land data carry idle land) with tolerances of 1e-7 and 1e-9; e_artoBal's total is the base land
  types' sum (CAPRI: ARTO - INLW); the grassland floor on the GRAS column duplicates permGrasGreening_, which the
  model also writes as its "CAP greening" row (N10).
- **Porting differences of N9 and N10 (kept in the move):** e_setaLandscape's row is written whenever a set-aside
  requirement is set, also with a zero floor (CAPRI: only where the floor exceeds eps); permGrasGreening_ has a
  (1 - 1e-9) tolerance, is skipped where grass is below supply.absent_level, and is written twice (the cap rule and
  the land market's grassland floor).
- **Porting differences of N11 (for the main line; kept in the move):** the accounts' e_GASRUNANI share is CAPRI's
  2030 reference (manure_housing_losses_2030.csv) without the options' factors (lowNFeed, rumFedEff, mlkYld; the NLP's
  ManureNPK_ has them); e_CRESID, e_EXPPRD and e_BIOFIX move CAPRI's 2030 reference coefficients with the yield ratio
  (CAPRI: v_yldMit and v_yldPestFac, for e_CRESID on the part above deposition and mineralisation); the LegSh
  option's factor on OFAR's fixation is not in the model; the input sum of nminInputSh_ and nmanInputSh_ leaves out
  the catch crops' BioFix (environmental/nitrogen.py leaching).
- **nMax_ is off in CAPRI's Green Deal step:** pol_input/greendeal/greendeal_scenarios.gms l. 200-204 sets
  p_nMaxPerHa(MIN) = 0 after the shocks ("do not activate equ nmax_"), so the crop groups' mineral caps are the inner
  model's f2f regulation alone, as the model's NLP writes them (inner_fert.py e_fertDistReguMax). The comments that
  name nMax_ for "NNcrp" (supply_module.py l. 1376, policy_module.py l. 136) are to be corrected on the main line; the
  QP's mineral_N row is the model's own sum over the groups. docs/SUPPLY_MODEL_MAP.md l. 95's "inactive or reporting"
  for nGrpLevl_, nMax_ and lsDensMax_ holds: all three are empty in the step.
- CAPRI's soil surplus (e_SURSOIkt, e_SURSOIHa, e_GASRUNMIN, e_GASRES) is read by NO3LEA_ (l. 3609-3613): for N14,
  set it against the model's leached N by source (supply/n_leaching.py crop_n, envind/gases.gms l. 696-745).
- **Feeding (N12a):** the NLP writes REQSE_ alone of the requirement rows, as CAPRI's feed version _pw; REQSN_,
  MAXSHR_ and MINSHR_ appear only in feed/ration.py's calibration of the base rations (section 5's note settled).
  Porting differences (kept): the feeds outside ration.py's FEED_ELAS are held at their base amount per head;
  FEDUSE_'s sum leaves out v_lossQuant's straw and COMF terms; QUADRF_'s linear coefficient adds the tradable feed's
  price (CAPRI: its market balance, valued through v_netPutQuant x UVAG) and the emission tax per kg of feed to CNST.
  SupplementPerc_ (the linseed's fat limit) is not written (K93).
- **Market balances (N12b):** SUPBAL_ is written for the non-tradable fodder only; for the tradables CAPRI's
  v_netPutQuant is substituted into the objective (the activities' net revenues, QUADRF_'s feed prices, the young
  animals at their price change, INPANI_). Porting differences (kept): the usable fodder per ha is CAPRI's base use
  over the base area (docs/FODDER_BALANCE.md), the base gap is held as a constant (K36, K46), a 1e-9 tolerance on the
  QP's row; CAPRI's genet_rep option (its factor on ICOW use in INPANI_ and on BEEF in SUPBAL_) is not in the model.
- **The objective (N13):** CAPRI's v_labCap is free in the step (p_fixLabCapViaPMP = 0, capmod.gms l. 557) and its
  scale is 1 (set only in sens/sens.gms), so labCap_ defines an unused variable and OBJEQF_'s PMP terms carry factor
  1; fixTechfShares_ needs p_fixTechfShares, set only in sens/sens.gms. e_exogenousLand fixes CAPRI's non-market land
  types at their data level (supply/cal_land_nests.gms l. 687-689); the model has no column for them. ARTIF is a market
  land type in CAPRI and held at its level in the model (capri_data/codes/model_land_types.csv): a porting difference
  already recorded there.
- **A run that loads the market supply Hessian from the cache** (.cache/market_supply_hessian, keyed by the code's
  fingerprint) differs from one that measures it at about 1e-8 relative (46 against 51 products recorded): a
  reference and its comparison run must both measure it (after a restart, clear the cache of a killed run).
- CAPRI's sugar quota equations (sugar.py's block) are empty in the 2030 step: their condition
  p_technFact(SUGB, VCOF) is set to 0 where DATA(QUTS, SUGB) <= eps (supply/prep_sim.gms l. 171), and the quotas
  ended in 2017; to confirm from CAPRI's 2030 DATA (N15).
- e_nitrBal_ (l. 3464-3466) is not written: the model computes no accumulation (v_nitrBalance(Accumul)).
- n_leaching.py cited "supply_model.gms l. 3413" for LEACHN_'s "+ v_ammoAppLeaAgg": l. 3430 in star 3.0 (the
  moved text in n_flow.py cites l. 3430).
- CAPRI's gamma prior is computed twice: inner_fert.gamma_prior (the NLP's normalised form, var = 1 / accuracy^2) and
  fert/inner_fert_dist.gamma_params (var = (mode / accuracy)^2, which can differ in the last digit at mode 1).
- The full suite after N1 (section 4) had not been run when N2-N4 started. After N4: its first chunk (the first 33 of
  the 66 slow tests) passed, 33 of 33; the other 33 slow tests and the 376 fast ones run at the next checkpoint, after
  N8 (the project lead, 19 November 2026: fewer test runs, one gate per batch of blocks with each block's exact
  expression or value check).
- The GAMS quotes, gathered in each module's docstring through N4, moved to the functions that write the equations
  (the project lead's decision; the commit after N4, docstrings only).

## 7. Rules that carry over (the project's instructions and the project lead's standing rules)

- Follow CAPRI's method and code; use CAPRI's results only to check, never to steer; no proxies, synthetic or hardcoded
  data unless necessary; say explicitly where something is done differently from CAPRI and why, and propose what goes
  beyond CAPRI for the project lead to decide.
- Equations in their own function or block, CAPRI's GAMS formulation at the top, CAPRI's names (variables first).
- Data trust: CAPRI's runs and the Green Deal parquets are for checks only; data_cur.gdx, market_model.gdx,
  cur_step.gdx, iy.gdx, supply_model.gdx are not used. No CAPRI runs (no CONOPT licence).
- Git: no push to dev or main from this branch; fetch before pushing; never force; the proxy refuses branch deletion.
- Never commit, print or write a token (the Hugging Face token lives in ~/.cache/huggingface/token); no licence files;
  Coin-HSL is never committed or redistributed (not needed: MUMPS is the default).
- One big job at a time on a small machine; background runs with an explicit timeout.
