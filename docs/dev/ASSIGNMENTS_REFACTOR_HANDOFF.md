# Handoff: CAPRI's ported assignments as named functions (branch `refactor/assignments`)

Written 23 November 2026 for the session that continues the third phase (Claude Code in the cloud). The plan is
docs/dev/ASSIGNMENTS_REFACTOR_PLAN.md (the project lead's, 23 November 2026); the rules are those of
docs/dev/EQUATION_REFACTOR_BRIEF.md and docs/dev/EQUATION_REFACTOR_HANDOFF.md section 7, the checks those of
docs/dev/MARKET_EQUATION_REFACTOR_PLAN.md sections 2 and 4 with the plan's changes. The branch started from dev at
259edec (the plan's commit).

## 1. Setting up

- CAPRI star 3.0 (the project lead's gams.zip of 17 June 2026) outside the repository, linked as capri_sources/gams.
  Checked before anything else (23 November 2026): `python tools/refactor/check_gams_quotes.py capri_sources/gams
  --expect supply/supply_model.gms=5557 --expect arm/market_model.gms=4607`: 45 files checked, 0 problems
  (supply_model.gms 5,557 lines, market_model.gms 4,607).
- The inventory: `python tools/refactor/assignments_inventory.py capri_sources/gams` rebuilds
  docs/dev/assignments_inventory.csv (about a second); the hand columns (status, function, notes) are kept.

## 2. State

| block | what | check |
|---|---|---|
| A0 | the inventory (docs/dev/assignments_inventory.csv; tools/refactor/assignments_inventory.py), each row reviewed; the five units of each block (section 3) | docs and a tool; the quote and citation checks; the pre-commit checks |
| A1+A3 | the emission and nutrient accounts and the projection's livestock rules: environmental/equations/gases.py (EMISCALC_CO2UREA), calc_nbalance.py (DATA_RUNANI, DATA_IMPORT, DATA_SURTOT, DATA_SURSOI); projection/equations/breeding.py (p_animReqCopy_NEA_share, p_animReqCopy_ENNE_nonlact), calc_nexport.py (CRPR_EXPT_COMI); supply/equations/line_nitr.py (p_ghgMiti_AComLN), fertned.py (p_technFact_FNUT), set_supply_bounds.py (v_emiLoss_bounds); market/equations/welfare.py (p_welfareRes_ProfitAgr); called by environmental_module.py, nitrogen.py, phosphorus.py, p_balance.py, income/income_module.py, projection/projection_module.py. ghgMiti.gms l. 552-565 (n_leaching.fert_effect) left to A5 (its module supply/equations/ghgmiti.py is locked) | the functions' tests (capri_mod/tests/test_assignments_a1.py) and the moved modules' (test_p_balance.py, test_supplement_fat.py, test_urea_subst.py, test_water_income.py: 19 passed); the five-unit Green Deal run (FI1A0000, NL230000, BL340000, IT110000, NO020000) identical |
| A2 | the premium rules: capri_mod/policy/equations/, one module per CAPRI file (policy.py, prmcut.py, aggreg_ppepay.py, implement_bps.py, mtr_until2013.py, calc_mtr_top.py, calc_mtr.py, extend_rd_baseline.py, cap_2014_2020.py, cap_2013_2020_transfers.py, cap_2013_2020_vcs.py, cap_2013_2020_cndp.py, def_policy.py, def_endcut.py, def_no_policy.py, nordicaid.py; _gams.py: GAMS's EPS, NA, $-conditions), 104 functions; called by policy/declared.py, premium_cut.py, premiums.py, mtr.py, bps.py, rd.py, cap14_premiums.py, nordic_aid.py, norway.py and supply/entitlements.py. The literal values data read (section 8 of the plan); the 120 inventory rows "moved in A2" | the functions' tests (capri_mod/tests/test_assignments_a2.py) and the moved modules' (test_bps, test_declared, test_mtr, test_premiums, test_premium_cut, test_premium_baseline_2030, test_rd, test_nordic_aid, test_norway, test_entitlement_money); the premium chain's outputs for every EU unit identical, bit for bit and in order (section 7); the five-unit Green Deal run (NO060000, FI130000, FR720000, PL510000, DE210000) and the coupled-support check (tools/run/run_vcs_2030.py --regions, the same five) identical; the full suite at 24a69fd8 (section 7) |
| A4 | the coupling's and the market's assignments: capri_mod/coupling/equations/ (new: price_forecast.py, the stop rule; define_stepweights.py; simu_calibration_to_supply.py; sol_simy.py), capri_mod/market/equations/ (welfare.py extended: the GL money metric, the processing's and the feed industry's profits; new: sol_market.py, set_start_val.py, def_biofuel_params.py; manuremarket/simu_manure_market.py extended), capri_mod/supply/equations/impose_upper_bound_on_elasticity.py; called by utils/capri_stop.py, coupling/price_step.py, bridge.py, young_animals.py, manure.py, reporting.py, market/welfare.py, demand.py, market_bounds.py, biofuel.py and supply/capri_pmp.py. 35 inventory rows "moved in A4" | the functions' tests (capri_mod/tests/test_assignments_a4.py) and the moved modules' (test_capri_stop, test_welfare, test_manure_pool_nlp, test_norway_market, test_biofuel_ad, test_demand_ad, test_trade_ad, test_market_layers, test_capri.py's PMP tests); the stop rule old and new on random tables (300 runs of 20 steps: identical verdicts, changes and drift); the five-unit Green Deal run (NL230000, RO020000, NO060000, DE210000, ES420000) identical. No full suite (the project lead, 23 November 2026) |
| A5 | the supply side's assignments, after merging dev at 565669aa (K196, DEP-21 closed; DEP-10 item 1b): capri_mod/supply/equations/greendeal/ (new: conventional_io.py, organic_io.py, organic_area.py, load_organic_targets.py, landscape.py, minfert_redu_by_crop.py, surptot.py), supply/equations/ (new: set_fert_priors.py, define_objc.py, define_greening_limits.py, define_manure_trade_costs.py, define_const_pmp_param.py, prep_cal.py, prep_sim_luc.py; extended: ghgmiti.py, define_inputs.py, set_supply_bounds.py), projection/equations/breeding.py, market/equations/set_prices.py and welfare.py, coupling/equations/price_forecast.py, policy/equations/def_endcut.py and market/equations/manuremarket/simu_manure_market.py (the rows of two blocks); called by supply/policy.py, supply_module.py, fertilisation.py, abatement.py, livestock.py, land.py, entitlements.py, fert/inner_fert_dist.py, feed/ration.py, policy/endotech.py, environmental/nitrogen.py, coupling/price_step.py, manure.py, market/welfare.py and model.py. 92 rows "moved in A5"; rd_logic.gms left (section 9) | the functions' tests (capri_mod/tests/test_assignments_a5.py); the five-unit Green Deal run (DE210000, ES420000, FR520000, NL230000, IT120000) identical to the run at A5's start (8d5d2818, dev merged); the full-EU Green Deal run identical to dev's 565669aa (the phase's start with the main line's changes) at `--rtol 0` with the Hessian read from the cache in both (a measured Hessian moves the run's last digits: section 9); the full suite (section 9) |
| A6 | policy/rd_logic.gms (the project lead, 24 November 2026): capri_mod/policy/equations/rd_logic.py (new, 22 functions: the money summed up, the land partition and its shares, FADN completed, the ceilings and their split by farm type, the LFA, Natura 2000 and agri-environment rates, the heavy animals' weights, the scaling); called by policy/rd.py's rd_declarations, its comments citing rd_logic.gms by line. 42 rows "moved in A6" (section 10) | the functions' tests (capri_mod/tests/test_assignments_a6.py) and test_rd.py; rd_declarations' whole output equal to the unchanged code's at `--rtol 0`, in the same order and to the bit (section 10); the five-unit Green Deal run (NO060000, FI130000, FR720000, PL510000, DE210000) identical to the run at A6's start (aa274e10) at `--rtol 0` but for the run's metadata, both converged in 21 iterations, each measuring its Hessian |

A0 approved by the project lead (23 November 2026; the plan's section 8): A1 and A3 one block with A1's five units;
in A2 only the rules become functions, the literal values "data read: <the CSV and its builder>" (3 rows of
pol_input/mtr_until2013.gms; 8 blocks mixing rules and literals move their rules only); the wrong line citations
fixed in the files each block moves (comments only), the two in supply/policy.py left to the main session; the
porting differences collected here (section 5), for the main session's one KNOWN_ISSUES entry. The files of the
plan's section 3 that the main line is changing are left alone until the main session says A5 can start; the
inventory's `locked` column names them.

## 3. The inventory: how it is built

The model's code (capri_mod/, outside its equations/ packages, pipeline/ and tests/; 133 modules, 85 of them citing)
cites CAPRI's GAMS files 860 times (the plan's grep counted 872: the tool's pattern takes a file name with its
folders once; a few names are parts of longer names). Each citation is resolved against star 3.0:

- with lines ("file.gms l. a-b", "file.gms:a", "(l. a, b)"): the statements at those lines;
- with a numbered section ("gases.gms (16)"): the statements of the section's item (CO2LIME);
- with a CAPRI name on the same line ("p_yieldElas from supply/yield_elas.gms", "gases.gms N2OSYN"): the statements
  assigning that symbol or item;
- the file only: a row of its own, "(file)".

A statement block is one CAPRI assignment, or the consecutive assignments to one symbol and key (a value and its
fallback; a table of values written one region per line). Its symbol carries the key that identifies it
(EMISCALC("N2OSYN"), DATA("CH4ENT")); a region's code is not a key. One row per block cited, the citing places merged
(module:line function, and how each cites it). Equations, declarations, options, solves and control statements get
rows of their own kind. A block quoted already by a function of an equations/ package is marked (in_style).

The tool proposes a status (status_proposed); each row was then reviewed by reading the citing code and the GAMS
statement (status, takes: the block that moves it, function, notes). The statuses:

- to move: the model computes the statement in the citing function; the block that moves it;
- already in the style: an equations/ function writes it;
- equation (phases 1-2);
- citation for context only: a pointer, a data source, a setting's origin;
- not ported: the reason (the result read as data built by tools/build, not in the Green Deal step, the model's own
  rule, CAPRI's solver bookkeeping, ...);
- citation wrong: what the cited lines hold instead (listed, not fixed).

The blocks follow the plan's section 3. A0 assigns the citing modules outside its table:
income/income_module.py, water/water_module.py, supply/ghg_tax.py, supply/n_cascade.py to A1 (the accounts and the
indicators: gases.gms, the nitrogen cascade); scenarios/definition.py to A2; utils/capri_stop.py (the stop rule,
capmod/price_forecast.gms) and supply/capri_pmp.py (the PMP recipe) to A4; market/ outside the plan's list to A4;
data/definitions.py, supply/nlp.py, supply/capri_regional_nlp.py (locked), supply/ammonia_techs.py to A5;
runlog.py, io_results.py, units.py, the scenarios' command line: context only.

## 4. The five units of each block

The full-EU run comes once, after A5 (the plan). Each block's five-unit Green Deal run takes the units below,
chosen from the full-EU Green Deal run at the second phase's end (d9fb8467: its rows' duals per unit, the manure
trade) and CAPRI's data, so that between them they take the paths of the block's statements:

| block | units | the paths |
|---|---|---|
| A1 | FI1A0000, NL230000, BL340000, IT110000, NO020000 | organic soils (FI1A: 16% of cropland, 30% of grassland) and Nordic; a manure importer (NL23: 123 kg N/ha imported) and an exporter (BL34: 51% of its manure); rice (Piemonte); Norway's accounts |
| A2 | NO060000, FI130000, FR720000, PL510000, DE210000 | Norway's premiums (norw_pol); Nordic aid (FI13); coupled support (France's ceiling the largest, 1,116 MEUR; Auvergne's suckler cows); a SAPS member state; BPS with convergence. Also tools/run/run_vcs_2030.py on the same five (its premium paths) |
| A3 | (with A1: A1's five) | A3's statements are moved with A1's (the project lead, 23 November 2026) |
| A4 | NL230000, RO020000, NO060000, DE210000, ES420000 | the manure pools (an importer, the largest exporter, RO02 66%); Norway's supply models in the market; the outer loop's price step and stop rule (any unit); a unit without a binding landscape floor |
| A5 | DE210000, ES420000, FR520000, NL230000, IT120000 | the landscape floor binding (DE21, IT12; 164 of the 221 units) and not (ES42; 57 units); the N surplus target (FR52, the first phase's units); manure and the N target (NL23) |

In the Green Deal step no unit has the mineral-N cap or the winter cover's row binding (their duals are 0 in all 221
units): their paths cannot be taken by a choice of units; the moved functions' own tests cover them.

## 5. What A0 found (for the main line; nothing fixed)

1,083 rows (the tool's count; each reviewed by reading the citing code and the star 3.0 statement):

| block | to move | already in the style | equation (phases 1-2) | not ported | context only | citation wrong |
|---|---|---|---|---|---|---|
| A1 | 8 | 19 | 14 | 32 | 33 | 1 |
| A2 | 124 | 0 | 3 | 37 | 53 | 1 |
| A3 | 5 | 0 | 2 | 1 | 5 | 0 |
| A4 | 45 | 18 | 51 | 93 | 89 | 8 |
| A5 | 91 | 10 | 36 | 112 | 167 | 1 |
| context | 0 | 0 | 0 | 1 | 20 | 3 |

(a row to move is counted under the block that moves it, the others under the first block citing them.)

**For the project lead's review before A1:**

1. **A1 is much smaller than the plan's list**: the emission accounts of envind/gases.gms (N2OSYN, N2OCRO, N2OAPP,
   N2OGRA, N2OHIS, N2OLEA, CO2LIM, CH4ENT's feed coefficient) are already written as functions: the accounts call
   the supply model's equations of the first phase's N14a (supply/equations/supply_model/n2o.py, methane.py,
   air_water.py, gwp.py). Left to move: the urea substitution's CO2 and the linseed-nitrate overlap
   (environmental_module.compute_indicators), the fertiliser options' leaching effect (n_leaching.fert_effect), the
   crop N at yields (nitrogen._crop_n_at_yields), the phosphate runoff and balance (phosphorus.py, p_balance.balance),
   the income parts (income_module._income_parts). A3 has 5 rows (breeding.gms NEM/NEA/NEP/ENNE in
   projection_module, calc_nexport.gms's milk N). Decided: A1 and A3 one block.
2. **A2's literal values**: of A2's 124 rows, the pol_input/mtr_until2013.gms blocks mix rules (mtr.py _rules,
   declarations_of_year, set_from_year...) with literal values (p_premDataE(...) = 123) that reach the model as data
   (mtr_declarations.csv, tools/build/build_mtr_inputs.py, applied by mtr.py mtr_series at their line). The review
   marked both "to move"; the notes say which is which. To decide: literals as functions returning their value, or
   classified as data read (out of scope with the builders). Decided: the rules only; the literals "data read".
3. **Not ported, 276 rows**, mostly results the model reads as data built by tools/build (out of scope: the
   builders): the market's LUC priors and shares (arm/define_land_params.gms, prep_market.gms; build_luc_market.py),
   the non-EU Hessian's completion (arm/market1.gms; tools/lib/_capri_nq.py), the irrigation shares
   (water_database.gms), the genetics, 3-NOP, tillage, low-N feed and supplements' effects (build_*_effects.py), the
   2030 feed bulks' unit values, the LUC prior modes; then branches off in the step (CropResi_IDEAG_NG; crop inputs
   and water in the market; the conventional_io yield-loss rows under yildReduction; the grofNEprod-off branch), and
   CAPRI's solver bookkeeping (bounds, start values, the high-elasticity dampening recalibration of
   calibrate_supply.gms l. 298-403).

**Citations wrong (14 rows; listed, not fixed):**
- runlog.py l. 6-7, 152: capmod.gms l. 81, 229, 1276, 1427-1428, 1705 for the caplog lines (they are at l. 75, 203,
  1235, 1391-1392, 1664); capmod/report_supply_model.gms l. 302 ("properly solved" is at l. 304); arm/simu_market.gms
  l. 283-285 (l. 280-282).
- coupling/reporting.py l. 46 (_welfare_supply): reports/welfare.gms l. 360-380, 690-700, 800-806 for the supply
  models' welfare components (those lines are the land owners' surplus, the TRQ rents and the tariff revenues; the
  components are at l. 416-467).
- market/welfare.py l. 404: welfare.gms l. 614-620 for the 50/50 split of the TRQ rents (the split is at l. 646-659).
- policy/mtr.py l. 518 (base_payments): policy/aggreg_ppepay.gms l. 61, a blank line (the payments are at l. 109-110).
- supply/policy.py l. 117-118 (locked): sets.gms l. 2958 for GRSACT (l. 2940); policy/policy_sets.gms l. 2055 for
  DDREG_MPACT("DDGREEN", MCACT) (l. 2045).
- coupling/young_animals.py l. 202 and market/supply.py _sup_milk_terms: arm/simu_calibration_to_supply.gms l. 166-175
  and 198-201, the grofNEprod-off branch (star 3.0 sets grofNEprod on, capmod/set_global_variables.gms l. 148: l.
  210-219 and 237-241).
- supply/ghg_tax.py l. 18: "gases.gms GWPCH4ENT_" (an equation of supply/supply_model.gms, l. 3074).

**Porting differences the review saw (to measure and rank; the inventory's notes give the evidence):**
- Accounts: the volatilised mineral part added to GWPN2OSYN_ (CAPRI's N2OSYN direct only); CAPRI's (1 - CRBU - CRFU -
  CRFE) factor of the residue N2O (gases.gms l. 545-548) not seen at the citing code; the linseed-nitrate combination
  as a product on the overlap (CAPRI: an option of its own); the income's MGVA without FEED for animals (capinv.gms l.
  551-552) and without the outputs and inputs not assigned to activities (welfare.gms l. 451-456).
- Premiums: bps_rates gives a member state without an MTR key its entitlements as key (K142, Croatia);
  entitlements.region_limit divides the cut by the money deflator (K174); the set_from_year rule and the DCOW ceiling
  set the simulation year only (CAPRI every SIMY in its range); DPCN, DPADDSHGM, DPENERCRP, DPNONCAP not ported,
  DPSILA missing from mtr_declarations.csv; BL400000's modulation rate not ported (no effect: calc_mtr reads the
  member state's); mtr_series drops sim_ini's NA records (K142); the non-CAP payments and greening shares, the farm
  types, the Agenda 2000 set-aside (SETR, OSET) and the per-technology premiums of prmcut.gms not ported.
- Market and coupling: the market supply Hessian per unit of price ratio (CAPRI per EUR/t of UVAG), without the
  inflation factor and the yield elasticity's diagonal term, its feed columns the products' prices (CAPRI the feed
  bulks'), CAPRI's two abort checks and the raw milk column of the feed bulk elasticities not ported; the start bounds
  without CAPRI's fixing of processing cells of 0.1 kt or less and of the biofuel and DDGS processing, without the
  negative lower bound of the milk products' prices (set_start_val.gms l. 533); the stop rule without step 1's
  comparison with the trend and the filter on Prod > 10 x the feed threshold, and without the GWPA, manure trade and
  land class items; the welfare's consumer price CPRI0 + (PR - 1) ARM1P0 floored (CAPRI DATA Cpri), processing and
  feed profits as a one-step integral, RENT as the land duals times the areas, the non-agricultural ProfitLandUse
  not ported; the elasticity dampening on the elasticities (CAPRI inflates the PMP term), its share term floored at
  0.1 and on EPRD_TO_GRP's crops (CAPRI QCACT with DATA ARAB).
- A5 (locked files, for the main line): the price transmission (arm/set_prices.gms) moves UVAG only, not UVAP nor
  the chicks' and young animals' input prices; the pesticide crops without fodder and set-aside (CAPRI every MCACT
  but idled histosols; REGISTERED) and the pesticide yield loss linear on the conventional share (CAPRI scales by the
  remaining target and skips regions meeting it with organic; star 3.0 runs with the yield shock off); the
  young-animal price bounds a fixed guard (-50..50) never widened (CAPRI's set_start_val and widen_bounds); the
  baseline mineral N per ha the model's own calibration point (CAPRI p_baselineDataout); p_mitiEffFac not applied;
  p_fertCostGains replaced by the model's N value (DEP-30); catch crops at CAPRI's 2030 share with the rule held at
  the base (CAPRI sizes them to the ecological set-aside rule, prep_cal.gms l. 63-99).

**The tool's limits (the hand columns correct them; rebuilding keeps the reviewed rows):** a citation whose file
name or lines run across a line break is read as the file only or its first line; a $include line or a LOOP header
cited counts as "lines hold no statement"; a file name that is in several folders resolves to the first
(endotech.py's refpol_endotech, greendeal.py's landscape.gms, policy.py's techf.gms: the review names the right
file); a CAPRI name on a citing line can match a statement the code does not port (the review says so).

## 6. What A1+A3 found (for the main line; nothing fixed)

- **Moved**: 12 statement blocks (the inventory's status "moved in A1", with the function); ghgMiti.gms l. 552-565
  (the fertiliser options' leaching effect, n_leaching.fert_effect) waits for A5 with supply/equations/ghgmiti.py.
- **Porting differences** (in the functions' docstrings): NEM the parameter REQ_NEM of a fixed 600 kg cow (CAPRI
  p_meanLiveWgt per region and technology); the milk's N export added as 0.0054 x the yield's change to the base N
  export per head (the other outputs scaled linearly); p_technFact's SRNUTS1 fill (fertned.gms l. 213-214) not ported;
  RUNANI without CAPRI's p_emiLoss fallback (the cascade gives the share); ProfitAgr without the outputs and inputs no
  activity is assigned (welfare.gms l. 451-456); AComLN as a product on the two options' overlap (CAPRI an option of
  its own); the loss shares clipped at the solution (CAPRI bounds its NLP's variables).
- **Citations corrected in the moved code** (comments only): line_nitr.gms l. 107-121 to l. 110-122, fertned.gms
  l. 205-206 to l. 206-207, breeding.gms l. 188-191 to l. 190-192; calc_nexport.gms now cites l. 44. None of A0's 14
  wrong citations is in A1+A3's files.
- **The tools**: the inventory's parser reads a statement after an inline condition ($ifi %x% == y p(...) = ...;): 28
  rows re-keyed as 36 (8 statements more), their statuses carried over (20 classified anew by hand, the notes say so); check_gams_quotes.py
  checks every equations/ package by default; check_gams_citations.py checks a statement function's "CAPRI's GAMS
  (file l. a-b)" header against an assignment to its symbol (the longest prefix of the function's name the file
  assigns).

## 7. What A2 found (for the main line; nothing fixed)

- **Moved**: 120 inventory rows ("moved in A2", with their functions). Three of mtr_until2013.gms's rules are
  selections of records with no value to compute and stay in mtr.py's _rules: eps_in_year (l. 589-590, 635-636,
  677-678), delete_year (l. 594) and rdel (l. 741). The mixed block l. 607-628 (Greece) holds literal values only:
  "data read". Also moved, though the inventory had no row (premium_cut.py cited prmcut.gms as a file): the cut's
  CEILACL, CEILACV, CEILCUT and CUTT (prmcut.gms l. 66-269), the BPS's envelope, entitlements, average IUV and tunnel
  ordinal (implement_bps.gms l. 113-178).
- **The exact check**: besides the gate's runs, the premium chain's outputs for all 215 EU units (the MTR key with
  its series, year declarations, payments, budgets, decoupled declarations; the BPS rates and ceilings; PRMD, weights
  and ceilings of the year; PRME; the RD budget and declarations; the CAP 2014 ceilings of 2015, 2018, 2020 and 2030
  and the cuts; the coupled, area, Nordic and Norwegian declarations; the coupling degree of 2005-2018, the decoupling
  targets of 2008 and 2012, the series and declarations of 2012) were dumped at the block's starting commit and at its
  end and compared value by value and key order by key order: 0 differences. A first comparison found the BPS rates
  differing in the last digits: two functions had replaced a `+=` loop by `sum()`, which since Python 3.12 sums floats
  with compensation (a different last digit). The functions keep the caller's form: `sum()` where the code summed, a
  loop where it accumulated. A rule for A4 and A5.
- **Porting differences** (in the functions' docstrings, "Departures from CAPRI"):
  - prmcut.gms: CEILACV's x 0.001 on each term (CAPRI's on the sum); CEILACL and CEILACV computed for every region
    with a ceiling (CAPRI's only where the ceiling is above EPS); a unit's cut factor taken from the nearest level
    with one (CAPRI passes it down level by level, a sum over one parent each); the per-technology premiums (l.
    300-312) not ported.
  - aggreg_ppepay.gms: a member state's PRME its units' level-weighted average directly (CAPRI's through NUTS 1);
    the payments' x 0.001 on each term.
  - policy.gms: Norway's application types (noDirPay 6, noPriceSup 7) not in the numbers (norway.py pays Norway).
  - implement_bps.gms: the key summed over the schemes at once and DPSAPS's not computed (no BPS); rcur without the
    units without entitlements (they add nothing); the overshoot's unit bug kept (K141), Croatia's key fallback (K142).
  - calc_mtr.gms: the greening share's factor left out of the decoupled budget (p_dpGreeningShare killed, 0).
  - calc_mtr_top.gms: the modulated money with the payments factored out of the sum over the producer groups; the base
    data's columns from mtr_base_data.csv.
  - extend_rd_baseline.gms: the member state's rest to NUTS 2 (l. 254-257, R / (7 - n) x w / W) computed in the NUTS
    1 order (R w / W / (7 - n)); rule 3 with a member state's spend written EPS and a region's above it stops (CAPRI's
    EPS / EPS; not in the data).
  - CAP_2014_2020.gms: the area schemes' type where the ceiling is above 0 (CAPRI's nonzero), dpbps_SAPS's likewise
    (CAPRI's in every SAPS member state); the BPS ceiling with the three shares' ceilings summed first.
  - cap_2013_2020_transfers.gms: the fill from the first year of the transfers' table (CAPRI's from 2006); the
    transfer from pillar 2 left out (0).
  - def_endCut.gms: the cut schemes' ceilings summed before the division (the region's objective loses their sum).
  - nordicaid.gms: a ceiling's presence, not its value, in the type's condition; the amounts per LU and per ha summed
    by the caller.
  - def_policy.gms: the year's value taken directly (CAPRI's loop over the pairs of edited years); mtr.py and
    norway.py apply the rule in their own loops over the records.
- **Citations corrected** (comments only): aggreg_ppepay.gms l. 61 (a blank line, A0's list) to l. 109-110 in mtr.py
  base_payments. A0's other wrong citations are outside A2's files.
- **The tools**: tools/run/run_vcs_2030.py takes --regions (a subset solved on the whole data set, as
  run_f2f_2030.py does) and writes the regional levels to its pickle, for the gate (commit 4be78b88, the model
  unchanged).
- **The full suite at 24a69fd8** (capri_mod/tests and capri_mod/pipeline/tests, pytest-xdist -n 3, 1 h 26 min): 527
  passed, 56 skipped, 1 xpassed, 2 failed. Both failures are pre-existing (for the main line): they fail alike at the
  phase's starting commit 259edec and at A2's start 4be78b88, run alone:
  - test_capri.py::test_capri_land_rents_at_the_2030_calibration_point: the calibration NLP's residual
    4.7279502897182036e-4 (the test wants below 1e-6), the same number at the three commits;
  - test_exact_io.py::test_csv_float_reads_are_exact: tools/build/build_feed_bulk_grof.py:45 reads CSV floats without
    capri_mod.csvio.read_csv (the builder came with DEP-14, 98674110, on the main line).
  The known test-order failure (test_supply_system_ad.py, docs/dev/EQUATION_REFACTOR_HANDOFF.md) did not occur in
  this ordering.
- **The comparison tool**: tools/check/compare_pickles_exact.py reports a DataFrame with NaN cells as different even
  from itself (run_vcs_2030.py's table has two: indicators the five units do not have); the coupled-support gate was
  checked cell by cell with NaN equal to NaN (no difference) and on its levels and factors (equal).

## 8. What A4 found (for the main line; nothing fixed)

- **Moved**: 35 inventory rows ("moved in A4"). Five of them are copies with no value to compute, kept where they
  are with the status saying so: the raw milk handed to the market (simu_calibration_to_supply.gms l. 423, 424), DATA
  Prod CUR (l. 245-255, the bridge's return value), the manure pool's arcs (simu_manure_market.gms l. 94-95: only the
  links with a trade cost are variables) and its price (l. 217, the pool NLP's dual).
- **Reclassified**: supply/calibrate_supply.gms l. 540-541 and 545-547 (the feed bulks' elasticities) "not ported":
  the market supply Hessian measures the bulks' response per market product (coupling/hessian.py), there is no
  statement of CAPRI's form; arm/recalibrate_commitments.gms "citation for context only": a model's solve
  (m_trimGLCommits), solved exactly by least squares in market/demand.py _gl_refit.
- **Porting differences** (in the functions' docstrings):
  - price_forecast.gms: the change 200 a / b (CAPRI's 2 (a / b) x 100) and the absolute value of the sum for
    quantities too; the first step not compared with TRD; the aggregates' price condition without its "Prod above 10 x
    p_minAbsFeedIterChg" branch; the members with a price and production in both sums of the aggregate's price.
  - define_stepWeights.gms: the special weights' normalisation applied to the weighted average (sum w v / sum w).
  - simu_calibration_to_supply.gms: the young animals' net supply summed unit by unit, no EPS added.
  - welfare.gms: the consumer price the GL demand's own (with its 5% floor), G without CAPRI's x 1e-6; the
    processing's and the feed industry's profits as straight-path integrals (all prices at once; CAPRI's good by good,
    equal for its symmetric Hessians), without the normalisation and base margin of l. 193-196; the energy fed for
    CAPRI's FEDE row (registered); x 0.001 on the difference.
  - sol_market.gms: the TRQ rent from the flows' rates under the model's sigmoid regime, shared over a quota's flows,
    without the exchange rate change factor, NaN rates as 0; the biofuel's feedstock cost the CES cost of the model's
    biofuel state.
  - sol_simy.gms: the land rent per land type with its own dual (CAPRI's UAAR x one d_area); the non-agricultural
    part (INPE) not computed.
  - set_start_val.gms: the bounds per market region's cell; the small and NQ-less processing cells not fixed; the
    price bounds in ratios, cells without a price fixed at their level; the PMrk_ cells' 1e-3 floor.
  - def_biofuel_params.gms: the CES share written q / X (mu_x / mu_b)^rho.
  - impose_upper_bound_on_elasticity.gms: the elasticity dampened (CAPRI sets the PMP term from it); a negative
    elasticity's root taken at 0.
  - simu_manure_market.gms: the fall-back manure value decided by the region's price history (CAPRI's step number and
    lagged UVAG); the trade gap per pool.
- **Citations corrected** (comments only): coupling/reporting.py _welfare_supply cited welfare.gms l. 360-380,
  690-700, 800-806 (land-owner constants, TRQ rents, tariffs) for the supply models' components: now l. 416-467;
  market/welfare.py _welfare_trade cited l. 614-620 (tariffs on bilateral-TRQ flows) for the rents' 50/50 split: now
  l. 646-659.
- **No full suite** in A4 (the project lead, 23 November 2026): it runs once, before the phase's merge.

## 9. What A5 found (for the main line; nothing fixed)

- **dev merged** at A5's start (565669aa: DEP-10 item 1b, DEP-12, DEP-21 and K189 closed, K196's lead closed): a
  merge, no conflict; its 14 new inventory rows classified (capmod/define_inputs.gms "data read": the main line's
  input_coefs_2030.csv, its TF_I already in the style in supply/equations/define_inputs.py). A5's reference run is at
  the merge (8d5d2818); the full-EU run's reference is dev's 565669aa itself (the phase's start plus the main line's
  changes, without the refactor). DEP-13 (the livestock tables) had not landed on dev: A5 touched livestock.py at one
  line (the breeding options' curvature).
- **Moved**: 92 rows ("moved in A5"), 15 of them of two blocks ("A4; A5", "A2; A5", "A1; A5": the selection by
  one block left them out, so A5 took them: the price forecast, the manure market's fall-back and excess supply, the
  welfare total, the entitlement limit, the fertiliser slack's bounds, ghgMiti.gms l. 552-565 A1 deferred). 28 of them
  are copies, constant bounds, flags or sets kept where they are with the status saying so.
- **Left to move**: policy/rd_logic.gms (file row, "A2; context"): rd.py's rd_declarations ports its steps 5-10 in
  about 330 lines without line citations, so its statements need the file read against the code. Moved in A6 (the
  project lead, 24 November 2026; section 10).
- **Reclassified**: supply/prep_sim.gms l. 253-255 (ISET's technology factor) "not ported" (the ISET column is
  substituted by SETA_'s r / (1 - r)); supply/calibrate_supply.gms l. 446-478 (the market supply Hessian's rows)
  "not ported" (measured by finite differences); fert/ferttrm_years.gms l. 284-295 and set_fert_priors.gms l. 297-306
  "data read" (the accuracies and the mode share, parameters).
- **Porting differences** (in the functions' docstrings):
  - set_prices.gms: the unit values as relative changes with the trend point's factor; the chickens' and young
    animals' inputs not covered.
  - conventional_io.gms / organic_io.gms: the closed forms of the percentage changes (as shares); the yield loss scaled
    with the cut (the jrc121368 rule) without CAPRI's remainingTarget factor; the organic top-up without SERI, valued
    at the fuel cost (CAPRI-ERROR-FIX organic_topup_at_fuel_cost).
  - organic_area.gms: the gap's absolute value / 100; no 0.45 factor (pest_disagg off).
  - load_organic_targets.gms: the scale at least 0; the targets within 0 and 1; VEGE always the UAA target.
  - landscape.gms: UAAR and SETF the model's base; the Shannon floors the model's.
  - minfert_redu_by_crop.gms / organic_minfert_redu.gms: kg per ha; the baselines the model's own calibration point's.
  - surptot.gms: kg per ha, the model's own surplus, no 2090 relaxations.
  - define_objc.gms: PLAP only at the mean technology, a cost per ha.
  - set_fert_priors.gms: the gamma's beta as (m + sqrt) / (2 var) (CAPRI's 1 / (2 var) x (m + sqrt)); the
    regulations' mode / max given.
  - ghgMiti.gms: pmpParsqr's two terms each divided by (m1 - m0); the inhibitor's side effect as the accounts'
    multiplier 1 - w + w (1 - lit)(1 + NMIN); EmiCalmin with the cascade's losses.
  - breeding.gms: the breeding options' shares per eligible head; the effects linear in the parameter; the curvature's
    floor without abs, divided by the eligible heads.
  - prep_cal.gms: the greening dual's multiplier fixed in the calibration's fit.
  - prep_sim_luc.gms: the land classes' bounds (l. 578-584) not ported.
  - define_manure_trade_costs.gms: the supply net of the base trade where it is the region's (K167).
  - define_const_pmp_param.gms: the feeds' slope divided by the feeding itself; a fallback only.
  - price_forecast.gms l. 376-383: the weighted sum divided by the weights available.
  - welfare.gms l. 872-885: the market's agents' components (the supply models' added by coupling/reporting.py).
- **Citations**: the two A0 listed in supply/policy.py were corrected by the main line (merged); two stale "citation
  wrong" rows updated; the two in runlog.py (capmod.gms l. 81, 1425-1428) are in no block's files, left to the main
  session.
- **The full-EU Green Deal run** (the thread limits below; runs/asg/): dev's 565669aa (eu_ref, its Hessian read from
  the cache the run before the container's restart measured) against A5's head 27789968 (eu_new, its Hessian
  measured: the cache key holds the supply code, below) differed in 78,105 values at `--rtol 0` (75,608 at 1e-10;
  relative up to about 1e-5, e.g. OFAR 208,393.57 vs 208,395.31), both converged in 29 iterations. The iterations'
  change records (eu_*_iterchg.csv) differ from the baseline's iteration 2 on, by at most 2e-12 points, amplified in
  the scenario's iterations 2-3 (2.6 points) and back near 2e-5 at the end. The head's code again with its own
  measured Hessian read from the cache (eu_newc): the baseline's records equal the reference's (0.0), and the pickle
  equals eu_ref.pkl at `--rtol 0` but for the run's metadata (13: paths, label, times, commit, the cache file's name,
  the data tree's hash, which the re-keyed code-data status rows change). A5 is identical; the difference is the
  Hessian's source. **For the main line (pre-existing, nothing fixed):** a run that measures the market supply
  Hessian ends its baseline in the last digits away from a run that reads the same Hessian (byte-identical) from the
  cache: K76's restore of the regional models' state after the measurement leaves a trace (the regional NLPs' warm
  starts or another state the restore does not cover); the non-convex scenario amplifies it to 1e-5. So two runs
  compare exactly only with the Hessian from the same source; the plan's gates (section 4) should say so.
- **The full suite at 27789968** (capri_mod/tests and capri_mod/pipeline/tests, pytest-xdist -n 3, 2 h 21 min with
  a full-EU run alongside; runs/asg/a5_suite.log): 548 passed, 56 skipped, 1 xpassed, 3 failed. Two are A2's
  pre-existing failures (section 7: the land rents' residual 4.7279502897182036e-4, the same number;
  build_feed_bulk_grof.py:45). The third, test_supply_system_ad.py::
  test_the_market_solved_by_the_chain_is_the_fixed_points_equilibrium[ipopt-mumps], was no result: its worker was
  killed by the container's memory limit (the kernel's OOM log: a 3.2 GB Python process), with the full-EU run
  alongside; run alone it passed (5 min 40 s; runs/asg/a5_ad_alone.log). A suite and a full-EU run do not fit
  together in the container's memory, though `free` shows 16 GB.
- **To do: a more verbose market supply Hessian step** (coupling/hessian.py, HessianBlock; for the main session;
  nothing changed here). The step is the full-EU run's longest single step (1,351 s in A5's reference run with the
  thread limits below; 2,518 s in the market phase's, 4,689 s with the container shared), yet at the default log
  level it writes two lines: the title at its start and "measured: N s" at its end (runs/asg/eu_ref.log l. 19-20).
  The progress line every `diagnostics.hessian_progress_every` (5) shocks is the run log's level "detailed" and only
  with the model's `progress` on (model.py `_progress`), so a standard run shows nothing for 22 minutes and a stuck
  step cannot be told from a slow one. What the step should report, at the default level:
  - at its start: the cache key and whether the cache hit (the file read, or "measuring"); the products to shock
    (52 in the Green Deal run), the regional models (221) and the threads the BLAS and OpenMP libraries run with;
  - the base re-solve: its time and its largest deviation from the baseline's state (0.00625 kt in the market phase's
    run);
  - every few shocks: the shocks done of the total, the product shocked, the elapsed time and an estimated end, the
    regional solves done and skipped (11,492 shocked, 2,063 skipped in the market phase's run);
  - at its end: the columns with a response (51 of 52), the entries dropped below `market.hessian_entry_floor`, the
    warnings' counts (region solves with the base's inputs differing from the base), the time and the cache file
    written. Most of these figures are already in `market_supply_hessian_info` (the pickle's meta) but reach the log
    only after the run.
  The cache's key holds `supply_code_fingerprint()` (every .py file of capri_mod but the market's, the tests' and the
  pipeline's), so a block that edits the supply code cannot reuse the reference's Hessian: A5's head run measured its
  own (1,909 s; the reference read the one measured before the container's restart, 3 s). The plan's "measured once
  and reused" (section 4) holds only for blocks outside those files. The two Hessians are byte-identical
  (29f3a51fd796d345.parquet and 0975341680d48d0f.parquet, 49,370 entries): A5 left the price response unchanged.
- **Threads** (found during A5's full-EU run): OpenBLAS and OpenMP start one thread per core in each worker process;
  only OMP_NUM_THREADS is set, in capri_regional_nlp.py l. 173 (`os.environ.setdefault`), after NumPy is imported
  (too late for OpenBLAS), and OPENBLAS_NUM_THREADS is never set. On the 4-core container the workers ran 7-10 threads
  each (load 9.5-10, a worker's main thread at 37% CPU). With `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
  MKL_NUM_THREADS=1` exported before the run, the workers ran one thread at about 98% (load about 4): the first
  supply solve 82 s instead of 257 s (the market phase's run) and the Hessian 1,351 s instead of 2,518 s. Whether the
  results depend on the thread count is not checked here: both runs of A5's full-EU comparison ran with the limits. For the main session: set the three limits before NumPy
  is first imported (the entry points or capri_mod/__init__.py) and log them in the Hessian step's start line.

## 10. What A6 found (for the main line; nothing fixed)

- **Moved**: policy/rd_logic.gms, read against rd.py's rd_declarations: 22 functions in
  capri_mod/policy/equations/rd_logic.py, each quoting its statement; rd_declarations keeps its loops and calls
  them, its comments now citing rd_logic.gms by line (the file was cited without lines: 5 rows; now 57). The
  inventory: 42 rows "moved in A6", 18 of them kept in the caller's loop with the status saying so (the region and
  year sets, the application types perLevl, the default agri-environment rate, the livestock units' copies, Sweden's
  expert constants and copy); 8 "not ported" (the technology factors, l. 237-244, 330-334, 392-393: supply/techn_mix.py's
  prem_diff_share; article 68's 2010 payments, l. 413-425); 1 "data read" (rd_sweden_expert.csv); 6 context (a
  declaration, the loops' ends, the option kill). 1,158 rows in all, none without a status.
- **The gate**: rd_declarations' whole output (2,607 declarations and ceilings, 16,705 entitlement weights) at 2007,
  2010, 2013, 2014, 2017, 2020, 2025, 2030 and at 2030 with Praha's levels dropped, from the unchanged code (a worktree
  at aa274e10) and the moved one: equal at `--rtol 0`, every dict in the same order, the rates equal to the bit. The
  output does not depend on Python's hash seed (seeds 0 and 7 equal), though the measures of a scheme are a set.
- **Code data**: the literals of the moved statements (2000 EUR, 1.5) are the functions' own, as in A2; the status rows
  re-keyed: rd.py's AE_RATE_MAX to rd_logic.py's p_premDataE_ae (l. 270) and p_premDataE_scaled (l. 319),
  SCALE_OVER_CEILING to p_premDataE_scaled; EXTENSIVE_SHARE's row dropped (the scan does not list p_entlWght1_heavy's
  0.5). AE_DEFAULT_RATE and SE_EXPERT_RATE stay in rd.py (constants assigned in its loops).
- **Citation fixed** (comments only): rd.py's docstring cited the technology factors as "rd_logic l. 235-241,
  340-346"; they are l. 237-244, 330-334 and 392-393.
- **Porting differences** (in the functions' docstrings):
  - rd_logic.gms l. 99-100: a member state without levels at the call takes its NUTS 2 regions' sum too; the regions'
    types (l. 88-92) not ported.
  - l. 108-109: the shares kept apart from the areas (CAPRI overwrites the areas with them).
  - l. 155-159: the scheme's farm types' euros summed (CAPRI multiplies by each type's share in turn; one farm type per
    scheme in rd_sets.csv, so the same).
  - l. 255-256: p_aeLfa computed for "Tot" too (not used by the rates).
  - l. 315-316: the scaling factor 0 where the payment is not above 0 (CAPRI keeps the sum, then 0).
- **An error path moved** (not reached by the data): the share of FADN's hectares outside LFA (l. 166-172) is now
  divided inside the regions' loop, as the euros' share was; a member state with hectares only in its "Total" farm
  type would have raised a division by zero before even without a ceiling, now only with one.

