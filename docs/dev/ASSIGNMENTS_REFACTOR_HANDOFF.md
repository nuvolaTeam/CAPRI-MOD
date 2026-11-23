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
| A2 | the premium rules: capri_mod/policy/equations/, one module per CAPRI file (policy.py, prmcut.py, aggreg_ppepay.py, implement_bps.py, mtr_until2013.py, calc_mtr_top.py, calc_mtr.py, extend_rd_baseline.py, cap_2014_2020.py, cap_2013_2020_transfers.py, cap_2013_2020_vcs.py, cap_2013_2020_cndp.py, def_policy.py, def_endcut.py, def_no_policy.py, nordicaid.py; _gams.py: GAMS's EPS, NA, $-conditions), 104 functions; called by policy/declared.py, premium_cut.py, premiums.py, mtr.py, bps.py, rd.py, cap14_premiums.py, nordic_aid.py, norway.py and supply/entitlements.py. The literal values data read (section 8 of the plan); the 120 inventory rows "moved in A2" | the functions' tests (capri_mod/tests/test_assignments_a2.py) and the moved modules' (test_bps, test_declared, test_mtr, test_premiums, test_premium_cut, test_premium_baseline_2030, test_rd, test_nordic_aid, test_norway, test_entitlement_money); the premium chain's outputs for every EU unit identical, bit for bit and in order (section 7); the five-unit Green Deal run (NO060000, FI130000, FR720000, PL510000, DE210000) and the coupled-support check (tools/run/run_vcs_2030.py --regions, the same five) identical; the full suite |

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
