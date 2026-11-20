# Plan for the rest of the supply-equation refactor (after N5)

For the Claude Code session on branch `refactor/supply-equations`. Written on 19 November 2026 from the branch at
d1fd725 (N5 not yet visible on GitHub) and the inventory there. It extends section 5 of
docs/dev/EQUATION_REFACTOR_HANDOFF.md; sections 4 (procedure), 6 (found on the way) and 7 (rules) still apply.

State: of CAPRI's 173 equations in the 2030 Green Deal step, 33 have a status in the inventory, 140 have none (before
N5's rows). Line numbers below are from the July 2026 release copy (supply/supply_model.gms, 5,631 lines; the note below). Code locations are
from d1fd725. Check them before editing; N5 may have moved some.

**Note of 20 November 2026:** the line numbers and counts in this document are those of CAPRI's July 2026 release (course_capri_git/gams, the Docker image caprithuenen/capri:latest; supply_model.gms 5,631 lines, 232 equations), read as star 3.0 until the correction of 20 November 2026 (docs/dev/EQUATION_REFACTOR_HANDOFF.md). CAPRI star 3.0, the code of the project lead's runs, has 228 equations, 162 of them in the Green Deal step; its lines are in the inventory and in the code's docstrings. This plan is kept as written.

## 0. Before N6

1. **Close N5.** Push it with the inventory's status, model_location and notes filled for its equations. Put its
   porting differences in section 6 of the handoff:
   - catcMiti_ scales with the current land in CAPRI and with the fixed base UAA in the model;
   - the winter-cover row's rhs has a max() guard that CAPRI does not have.

   Do not fix them in the refactor. The main line has them as K186.
2. **Full suite now**, if it has not run since N4 (it was due after N4). test_capri.py alone runs for more than an
   hour. Run it in chunks (by test ids or `-k`) as background jobs with a timeout, never more than two heavy jobs
   at once.
3. **Merge `origin/dev` when K185 lands there.** I will tell the project lead when. Use a merge, never a rebase. The
   conflicts to expect:
   - `capri_mod/supply/equations/ghg_mit_cost.py` and `idled_histosols.py`: modify/delete. K185 corrects CAPRI line
     citations in them. Keep the deletion and carry the corrected citations into the moved functions
     (supply_model/mitigation.py, nutrients.py `fertDistCres_idlHis`, n_surplus.py `SURTOT_idlHis`).
   - `capri_mod/supply/fertilisation.py`: the need line (`DATA_FNUT` from `capri_mod/supply/equations/fertned.py`,
     new) and the imports (`fertDistCres_idlHis` now comes from `supply_model.nutrients`).
   - `capri_mod/environmental/phosphorus.py` (DATA_FNUT in the P accounts); CHANGELOG, KNOWN_ISSUES, the register.

   **K185 changes results.** The next block's "ref" run must therefore be made at the merge commit. It cannot reuse
   the previous block's "after" run. Run the K185 tests after the merge
   (`test_fallow_and_set_aside_have_no_nutrient_need`, test_p_balance).

## 1. How each equation is closed (the inventory's status column)

A move never changes results. Anything that would change them is listed for the main line, never done here. Each of
the 140 equations ends with one of these statuses:

| status | when | what to write in notes |
|---|---|---|
| `ported` | the model writes it; now a function named after CAPRI's equation, gate identical | the function; porting differences, if any |
| `ported (bound)` | the model writes it as a variable bound (lbx/ubx), not a row | where the bound is set; the function returns the bound |
| `ported (accounts)` | an emission or LUC equation the accounts compute after the solve; now a supply_model/ function the accounts call (N14) | the function and its callers |
| `empty in the GD step` | CAPRI's domain condition is false with the Green Deal step's switches and data | the evidence: where CAPRI sets the parameter, and the switch or include that keeps it out |
| `not in the model` | CAPRI's rows are non-empty in the step, and the model has no counterpart | the evidence (the parameter, where CAPRI sets it, which regions), for the main line |
| `not written (documented)` | known and recorded, like e_nitrBal_ | the reason |

For every equation that no file in the model cites, first search the code for CAPRI's parameter and variable names
(not only the equation's name), then the GAMS (`pol_input/greendeal/`, `envind/`, `capmod.gms` includes) for where
the domain's parameter is set. A `not in the model` row is a finding for the main line. Say so in the commit
message and the handoff. Do not add it.

## 2. The blocks, in order

Each block follows section 4 of the handoff (three-region gate, the block's tests, the pre-commit checks). The full
suite runs after N8, N10, N11 and N12, and at the end.

### N6: the N cascade's remaining terms (n_flow.py), if N5 did not take them
- `CapriRegionalNLP._netf_eff` (capri_regional_nlp.py about l. 851): the options' terms of GASTOTNETF_ and
  RUNTOTNETF_. They are written as the base efficiencies plus the change from the base point, with ghgMiti.gms's
  othImpact 1 - (1 - lit)(1 + NMIN).
- Gate: CasADi `str()` equal for every region, plus the three-region run.

### N7: mitigation, the rest (mitigation.py)
Equations: Tot_soilCov_ (4146-4148), Tot_LineNitr_ (4152-4158), ADMax_ (4189-4196), e_yldMit_ (4200-4213),
buffer_ (4252-4254), LscpFeatWood_ / LscpFeatGrsy_ / LscpFeatAll_ (4259-4290) and the envConst rows (4297-4384):
ND_buffRest_, IED_AmmRest_, ND_ManStor_, ND_ManCov_, ND_AmmAppLE_, ND_AmmAppHE_, GAEC_coverCrops_,
GAEC_soilCover_, GAEC_lscpFeat_, NH3Target_.

None of these names appears in capri_mod/. Classify them first:
- **Corrected (19 November 2026, the cloud session's check, confirmed): envConst is OFF in the Green Deal step.**
  pol_input/greendeal/refpol_endotech_all_sup.gms has an active `$exit` at l. 398. It stops reading the file before
  `$setglobal envConst on` at l. 408, so CAPRI keeps its default, `$setGlobal envConst off`
  (capmod/set_global_variables.gms l. 244, included at capmod.gms l. 105, before the policy file at l. 748).
  - The ten envConst rows (ND_buffRest_, IED_AmmRest_, ND_ManStor_, ND_ManCov_, ND_AmmAppLE_, ND_AmmAppHE_,
    GAEC_coverCrops_, GAEC_soilCover_, GAEC_lscpFeat_, NH3Target_; supply_model_e_list_linear.gms l. 186-195) are
    `empty in the GD step`.
  - So are ecoSetAside_ and cropDivGreening_ (e_list_linear l. 235-236, `$ifi %envConst%==on`): move them to `empty in
    the GD step` as well (N10). The model writes both rows in its Green Deal runs; that is a porting gap for the main
    line (K187), not for the refactor.
  - Two terms inside other equations drop out too: e_LscpFeatArea_'s GAEC8Nopuls term (l. 2346) and nMax_'s
    (1 + v_incEmiAppl) factor on excretion (l. 4530).
  - The other settings after the `$exit` (l. 399 to the end) are not set by that file either: check each against its
    default in capmod/set_global_variables.gms before relying on the switch table. endoManAvFact stays on, its default
    (l. 52).
- e_yldMit_ has no condition (4200). Check what the model does with the options' yield effects (`cropyld`
  othImpact) before calling it missing.

### N8: land (land.py)
- LandBalSlak_ (2382-2395), LandBalNoSlak_ (2399-2403), e_UaaNoSlak (2430-2433), e_artoBal (2440-2443; Trustee_land
  ON and lucequations off), e_exogenousLand (4916-4918; it is in objective.py's list but is a land row).
- Code: supply_module._build_constraints rows "arable_land" (about l. 1127), "permanent_land" (about l. 1195),
  "grassland" (about l. 1227); supply/land.py l. 68, 139, 167.
- LandMarket_ (4903-4914): land.py l. 111.
- **The QP rows**: keep the order of the `row_labels` appends and of the columns, and keep the labels. supply/nlp.py
  (about l. 190) takes the rows over by label.
- The LUC estimation (luc_supply ON: e_landTypes_to_LUclass, e_luClassFinal, e_luClassInitial, e_FocLUC,
  e_derivativeOfNormalLUC, e_derivativeOfGammaLUC, e_lowerBoundLUC, e_upperBoundLUC; 2448-2497) is in
  environmental/luc.py.
  - Check whether luc.py runs inside the regional solve or after it.
  - Either way, the project lead's decision for N14 applies: CAPRI's functions go in land.py, called by luc.py.

### N9: set-aside and activity limits (set_aside.py)
- SETA_ (2230-2252), NONF_ (2254-2258), SETAN_ (2262-2269), MXSETA_ (2311-2321): the obligatory set-aside.
  - model.py l. 1617-1637 says ISET is 0 without a scenario's rates.
  - Check DATA(…, "SETR") and DATA(…, "OSET", "FLOOR") in the step: SETA_, SETAN_ and MXSETA_ are probably empty.
  - NONF_ has no condition: check the NONS data and the NONF activity (it may reduce to 0 = slack).
- e_maxPerUaar, e_maxLevl, e_minLevl (2274-2285).
  - In star 3.0 their data are set only in pol_input/agora/main.gms and capmod/falladjustment.gms l. 154-155.
    falladjustment.gms is included only when `%AgoraversionV8_4%_%WoddyBioMass% == on_on` (capmod.gms l. 1516-1519).
  - So they are probably empty. Confirm the switches in the Green Deal result's META.
- e_setaLandscape (2326-2332): the "landscape_floor" row (supply_module about l. 1185; abatement.py l. 601).
- e_LscpFeatArea_ (2337-2360): classify first.
- e_minCoverCrops (2368-2370): abatement.py l. 186; nlp.py l. 255.
- idleHisto_ (2295-2306): abatement.py l. 561.
- Gate: the three gate regions may have no histosols or floors. Count the old code's calls in the gate run. Where a
  row is empty in all three, add a region where it is not, or compare the functions' values for every region (as in
  N3).

### N10: premiums (premiums.py)
- sumEntl_ (1893-1897), overShotEntl_ (1899-1900): supply/entitlements.py; policy.py l. 15-62.
- greenOverShot_ (1902-1907): needs p_entlLimit(…, "DPGREEN", "DDGreen", "Limit"); classify first.
- permGrasGreening_ (1910-1912): capri_regional_nlp.py about l. 545 ("CAP greening"); supply_module; policy.py.
- cropDivGreening_ (1916-1933) and ecoSetAside_ (1948-1984): `empty in the GD step` (envConst off, see N7). The model's
  rows stay on the branch as they are; the main line removes them in the Green Deal step (K187) and the branch takes
  that with the next merge of dev.
- winterCover_ (1990-2003): the "winter_cover" row (supply_module about l. 1445); abatement.py.
- catcMiti_ (2016-2021), if not done in N5.
- Full suite after N10.

### N11: the N surplus's coefficients and the fertiliser limits (n_surplus.py, fert_limits.py, nutrients.py)
- e_SURSOIkt (1285-1287), e_MINFERT (1295-1298), e_MTRADEHa (1302-1310), e_EXCRET (1313-1325), e_GASRUNANI
  (1330-1351), e_GASRUNMIN (1354-1363), e_GASRES (1366-1385), e_ATMOSD (1389-1397), e_CRESID (1401-1422), e_EXPPRD
  (1425-1442), e_BIOFIX (1446-1469), e_SURSOIHa (1486-1495), nminInputSh_ (1797-1827), nmanInputSh_ (1829-1859),
  SURSOI_REST_ (1866-1870).
- Code: the "N_balance" row (supply_module._build_constraints); fertilisation.py about l. 564 and l. 870
  (`_n_row_mineral_parts`); abatement.py l. 605-609 (SURTOT_idlHis); supply/land.py (the form per ha of current
  land).
- The accounts (environmental/nitrogen.py, phosphorus.py) also use e_EXPPRD, e_CRESID and e_BIOFIX. Use one function
  for the row and the accounts only where both compute the same expression today. Where they differ, write that
  down as a porting difference and keep both.
- e_ATMOSD and e_CRESID are partly in n_surplus.py already (K184). Complete them; do not duplicate them.
- nGrpLevl_ (4507-4513) and nMax_ (4518-4531): supply_module about l. 1384 ("NNcrp"); policy_module l. 136.
- LsDensMax_ (4544-4559): its data p_maxLUperha are set only in envind/RedLvst.gms, which is included only with
  ghgTechLsu = 1 (capmod.gms l. 1159). The Green Deal reference's default is 0 (refpol_endotech_all_sup.gms l. 172),
  so it is probably empty. Confirm in the META.
- e_manureLimit_ (1253-1255; ManureTradeNEW ON): docs/SUPPLY_MODEL_MAP.md l. 89 already says it is active only where
  p_manure_limit is set (pol_input/manure/ManureNLimit*.gms), so not in the Green Deal step. Confirm, then mark it
  `empty in the GD step`. The same map's l. 95 calls nGrpLevl_, nMax_ and lsDensMax_ "inactive or reporting": check
  that claim against the Green Deal step's data (mineRedu "NNcrp" uses nMax_) before relying on it.
- Full suite after N11.

### N12: feeding, fodder balances, young animals (feeding.py, markets.py, young_animals.py)
The largest NLP block. Split it in two commits.
- **N12a**: REQSE_ (569-610), SupplementPerc_ (616-641; K93), FEDUSE_ (797-811), QUADRF_ (4949-4951), QUADRF1_
  (4955-4962).
  - Code: capri_regional_nlp.py about l. 242-520 (the feed calibration about l. 371, the fodder balances about
    l. 412); feed/ration.py.
  - The `pv()` order matters most here.
  - Register what differs from CAPRI's `_pw` feed version: the model writes MAXSHR_ and MINSHR_ terms, which `_pw`
    switches off (handoff section 5).
- **N12b**: SUPBAL_ (4610-4670): capri_regional_nlp.py about l. 499; supply_module about l. 1264; livestock.py
  about l. 490. INPANI_ (847-865): supply_module about l. 1775.
- Full suite after N12.

### N13: the objective (objective.py)
- The rest of LINEAR_: supply_module._compute_net_revenues (l. 769). The parts done in N4 stay where they are.
- QUADRA_ (5358-5428) with GRPLEVL_ (4965-4968): the PMP matrix, supply_module about l. 478-491.
- labCap_ (4881-4883): v_labCap = the PMP terms (plus the land market's, minus the feed's). In CAPRI it enters
  OBJEQF_'s scaling (l. 4850-4869). Check whether the model has a counterpart; probably `not written (documented)`.
- fixTechfShares_ (4886-4890): **empty in the GD step**. Its domain needs p_fixTechfShares, which is set only in
  sens/sens.gms (l. 151, 305).
- OBJEQF_ (4846-4879) comes last: one function composing the terms in the model's current order.

### N14: the emission blocks
methane (6), n2o (10), air_water (10), gwp (4) and lulucf (17): 47 equations, plus the LUC estimation (N8).

In CAPRI they are definitional rows of the supply model, binding only under an emission price or cap. The model
computes them after the solve (capri_mod/environmental/) and, in the regional NLP, only where a price acts
(supply/ghg_tax.py). There are two options:
- (A) functions in supply_model/<block>.py, called by the accounts and by ghg_tax.py;
- (B) CAPRI's names kept in environmental/.

**Decided (the project lead, 19 November 2026): option A.** Write each equation as a function in
supply_model/<block>.py (methane.py, n2o.py, air_water.py, gwp.py, lulucf.py) and call it from the accounts
(capri_mod/environmental/) and from supply/ghg_tax.py. This follows CAPRI, where these rows belong to the supply
model.
- The same applies to the LUC estimation (N8): its functions go in land.py and environmental/luc.py calls them.
- The move stays identical. Where the accounts and ghg_tax.py compute the same quantity in two different ways
  today, keep both calls as they are and list the difference for the main line; do not unify them in a move.
- Gate: the accounts are in the run's pickle, so the three-region comparison covers them. Add a run with an emission
  price where ghg_tax.py's terms must be exercised.

### N15: sugar (sugar.py)
- netPutQuantSugb_, SalesSugb_, SIGMSugb_, cdfSugb_, pdfSugb_, SugbRev_ (5434-5494).
- The domain needs p_technFact(SUGB, "VCOF", A). Check the 2030 data. If no region has it: `empty in the GD step`,
  no code.

### Last
- All 173 equations carry a status.
- Final full suite; the handoff updated.
- One list for the main line: the porting differences and the `not in the model` rows, with their evidence.
- Merging the branch into dev is the project lead's decision.

## 3. Rules for the gate (in addition to section 4)
- Before a move, count how often the old code runs in the gate's three regions (ES42, FR52, DE21). A gate where the
  moved code never runs proves nothing. Then add a region where it runs, or compare the function against the old
  code for every region (CasADi `str()` equality, or bitwise values, as in N2 and N3).
- QP rows: keep the order of rows, columns and labels. NLP rows: keep the operands, the expression tree and the
  `pv()` order.
- Identical means only `$.meta.` differs (11 lines so far).

## 4. Not in this branch
- No change of results, data or settings. No fixes, including the porting differences: the main line takes them
  (K186 for catcMiti_).
- docs/equations/ is on the branch since 0eb0259 (the project lead's decision of 19 November 2026). Page 1 cites
  code at d1fd725. When a block moves code that a page cites, update the page's line numbers in the same commit.
- No push to dev or main. Never rebase or force; the branch is public.
- No CAPRI runs. CAPRI's results and the Green Deal parquets are only for checks. Do not use data_cur.gdx,
  market_model.gdx, cur_step.gdx, iy.gdx or supply_model.gdx.
