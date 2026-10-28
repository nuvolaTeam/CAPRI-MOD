# Changelog

Recorded because the project's documentation had drifted in **both** directions:
claims of validation outlived their truth (the CAP policy layer was inert while
documented as validated), and claims of failure outlived their fix (the pulse
elasticity sign error and the DE60 non-convergence had both been resolved long
before anyone retired the note). Limitations should be re-measured, not
inherited.

Full provenance for every entry is in `capri_data/DATA_SOURCING_REGISTRY.json`.

---

## Validation status

| Component | Reference | Result |
|---|---|---|
| Market prices | CAPRI `PMRK` | 12/12 within 15% |
| 2030 projection | CAPRI 2030 reference run | correlation **+0.997**, total area within 2% |
| Emission tax | CAPRI's ghgTax inside the supply models (Sprint 9i) | no CAPRI tax result in hand; the earlier post-solve MACC check against EcAMPA 2 was retired with the module |
| Fertiliser | CAPRI `p_FertPerHa` | ~10% |
| Feed, monogastrics | CAPRI capreg reference | within ~5% |
| CAP budget | Real EU CAP | €54.0bn vs ~€55–58bn |
| Nitrogen balance | CAPRI 2030 reference, item by item | EU items within 1–7 kg N/ha; regional correlation 0.92 |
| Phosphate balance (P2O5) | CAPRI 2030 reference, item by item | with CAPRI's own levels the formulas give its items (within 1e-6; removal 0.02%); at the model's base data (not a solved 2030 run) EU items within 0.5 kg P2O5/ha (surplus 14.4 vs 13.9), regional surplus correlation 0.99 |
| Water demand | Known EU irrigation geography | restored 27 October 2026 on CAPRI's units: 11.2 Mha irrigated (FSS), 32 km3 net requirement, 83% of it in ES, IT, EL, PT |
| Biofuel | CAPRI 2030 reference (BiofFeedCost, biofuel output and use per CAPRI market region) | exact; feedstock use and biofuel markets inside the market |
| **Total cereal output** | **EU Agricultural Outlook 2017-2030 (DG AGRI/JRC)** | **297.2 Mt vs ~300 Mt — ratio 0.99** |
| **Farm-to-Fork scenarios** | Published CAPRI (JRC121368) | reported as a range; CAPRI's figure falls inside it for oilseeds |

---

## 28 October 2026: CAPRI's stop rule the default (K79)

- `outer_loop.stop_rule = "capri"` (the project lead's decision): CAPRI's rule (capmod/price_forecast.gms: the loop goes
  on while more than two items change by more than 0.05% between iterations), with the model's inner balances settled.
  Set back on 27 October because the Green Deal 2030 run r165 had not stopped by iteration 20; r165 had been cut by the
  run time limit, its Hessian measured inside the run.
- r168 (Green Deal 2030 under CAPRI's rule, the Hessian from the cache, every region's levels recorded per iteration,
  diagnostics.record_regional_levels): stops after 30 iterations (5,761 s), 0 rows above 0.05% at the last. EU
  indicators within 0.4 points of r166 (the model's rule, 9 iterations). The large swings were single regions jumping
  between two states (BG010000 maize +-115 to 131 kha, iterations 3-10; HU230000 and HU330000 fodder and maize,
  iterations 4-16; Swedish tomatoes, 17-20), then a geometric tail (KNOWN_ISSUES K79, open for the jumps).
- Farm-to-Fork under CAPRI's rule: r164, 12 iterations.
- Test suite: 189 passed (20 min, the stored Hessians of the dev worktree: no Hessian measured).

## 27 October 2026 (night): builder reproduction audit (K86, K87), CAPRI's stop rule the default (K79), the legacy nitrate limit retired (K33), orphans removed, CAPRI's welfare report (M7)

- **Builder reproduction audit** (tools/check/reproduce_builders.py, which also records every builder's command): each
  of the 117 builder invocations run on the committed inputs and its outputs compared with the committed files; files
  several builders write in turn checked as a chain (`--chain`). Found and fixed:
  - **K86:** the ammonia cost curves left out Denmark, Lithuania and Croatia (a fixed list of an older CAPRI's member
    states without regional detail), and build_ammonia_technologies took the missing curves as 0: their housing,
    storage and air-purification options had no farm-size cost terms and no curvature (air purification for pigs 0 EUR
    against 7.9 in DE110000). Now every regional unit, as CAPRI (ammo_tech.gms); the builder lists the units left
    without a curve (Prague: no holdings per farm-size class in the data; Norway: no ammonia options, registered). The
    AD option and the Nitrates Directive tables had the same list; their outputs are unchanged (Croatia is not in
    CAPRI's AD base data).
  - **K87:** crop_cost_shares.csv rounded to 3 decimals and without the single-unit member states; the max-mitigation
    unit values without TABO; files written before the full-precision decision (market, fertiliser distribution, land-use
    change, greening, cost savings: 3e-10 to 5e-6) rebuilt, and the files built on the cost savings with them
    (genetics, low-N feed and supplement effects, histosols). Two builders no longer write stray files (an uncommitted
    pela_cross_price.csv; a backup copy of the trade flows). Re-audit: every rebuilt builder reproduces its files; the
    base-table chain (extract_all_from_data2 ... build_eu_producer_prices) reproduces yields, variable costs and
    CAPREG producer prices.
- **CAPRI's stop rule made the default and set back the same evening** (outer_loop.stop_rule; the project lead's
  decisions, K79, DEPARTURES_FROM_CAPRI). With it the loop stops
  when no more than two items (member-state production and feed, trade-block prices) change by more than 0.05% between
  iterations (capmod/price_forecast.gms), with the model's inner balances settled as well (N-balance price, manure
  pools, young animals, base calibration). The model's own rule (prices within 0.5%) ended Farm-to-Fork with 14
  production rows still above CAPRI's threshold (r161, r163: largest Latvian oats 1.1%, halving each iteration: slow
  convergence of the price forecast, not solver creep). Farm-to-Fork with it (r164): CAPRI's rule stopped the loop after 12
  iterations (r163: 9 under the model's rule) with two rows above the threshold (Portuguese potatoes 0.93%, tomatoes
  0.36%), which CAPRI's rule allows. The Green Deal 2030 scenario did not converge under it (r165: at iteration 20 of
  the scenario 28 rows above 0.05%, the largest about 50%, an oscillation; stopped before its two-hour limit), so the
  default is the model's rule again until that is found and fixed; CAPRI's verdict is still recorded every iteration.
- **K33 retired** (the project lead's decision): the legacy nitrate_limit instrument (not CAPRI's; used by no CAPRI
  scenario), its constraint row, the Mitscherlich intensity margin it drove (supply/intensity.py), the livestock
  intensity bounds only it read (and their builder), and the unsourced per-head animal rows of nutrient_coefs.csv
  (they also entered each region's reported nutrient_balance). Two tests that exercised only the instrument removed
  (182 tests with the two guards below).
- **Orphans removed** (the project lead's decision): input_requirements, pmp_diagonal_terms, pmp_crossgroup_terms
  (2017/supply) and manure_ch4_ef_regional: no builder, read by nothing; their two loaders and metadata entries.
  INPUT_MANIFEST.json: 93 declared inputs (also two entries of files removed earlier).
- **OANI**: gross output 0 where the activity's level is 0 (it read NaN; no output coefficient).
- **Exact-I/O guards** (capri_mod/tests/test_exact_io.py, static, seconds): every pandas CSV read of the model, builders
  and checks parses floats exactly (the last three inexact reads fixed); no builder adds a rounding of the values it
  writes. 72 roundings in 20 builders remain from before the exact-I/O decision (K88): listed, may only shrink, to be
  removed with a rebuild. Delta Lake for the model's inputs considered and not taken (the format would not undo a value
  rounded before it is written); the project lead decided that the builder-written inputs move to plain Parquet (a
  separate step), sources and hand-maintained tables stay CSV.
- **CAPRI's welfare report (M7)** replaces the first-order consumer and producer surplus (reporting only;
  docs/WELFARE.md): per market region, the consumers' money metric of the GL demand system in CAPRI's sequence; the
  profits of processors (ProcNQ_), crushers (in the margins), biofuel plants and dairies (DairyNQ_ in the margins,
  raw milk an input) from their own functions; the farms and feed users of the regions without supply models (the
  model's supply and feed functions, the dairy blocks' raw milk supply); tariff revenues and quota rents per flow;
  for the regions with supply models their MGVA, land rents and the premiums' budget cost (results["welfare_supply"]).
  CAPRIModel.compare sums them to CAPRI's total change. The market's components are changes against the calibration
  point (CAPRI's levels add base values set by convention; to be decided). CAPRI's 2030 reference welfare levels
  stored as a source (capri_res/ref2030_welfare.csv, from scen_ref_2030); its land accounts (CAPRI's land market:
  the farms' profit MGVA less the land rents, the rents the land owners') are the model's too, the rent at the
  solution from the supply models' land rows. Tests: test_welfare.py.
- **Docs**: DATA_DICTIONARY's core tables on the 221 units; README (NUTS 2024 reporting in place; nitrogen instruments);
  KNOWN_ISSUES K79 diagnosis, K86, K87.
- **Reference runs.** r163 (the evening entry's Hessian change and the K82 ammonia rebuild, before this entry's
  changes; Farm-to-Fork): 9 iterations, mean absolute deviation from CAPRI 4.34 as r161, every indicator within 0.1
  point; the Hessian skipped 4,169 of 15,219 regional re-solves (its time, 76 min, is not a clean measure: a builder
  audit ran beside it). The French olive and table-grape jumps of r161 (K79) did not recur.
  r164 (this entry's changes, Farm-to-Fork, CAPRI's stop rule): 12 iterations, CAPRI's rule satisfied (two rows above
  0.05%), mean absolute deviation from CAPRI 4.33 (r163 4.34), every indicator within 0.2 point of r163; the Hessian
  43 min (r161 67 min); no non-optimal regional solve; IPOPT met NaN at trial points of one region (ES240000, a linear
  row) and recovered (all solves optimal). r165 (Green Deal 2030, CAPRI's rule): no stop by the scenario's iteration 20
  (28 rows above 0.05%), stopped by hand. r166 (Green Deal 2030, the model's rule, with the welfare report and the
  progress lines): 9 iterations (r162: 8), 36 min; every indicator within 0.2 point of r162, mean absolute deviation
  from CAPRI 8.58 (r162 8.55); no non-optimal regional solve; CAPRI's rule at the last iteration: 30 rows above 0.05%,
  largest 2.8% (Norwegian pulses), the largest swing by iteration Bulgarian soybeans 133%, Bulgarian maize 54%, Spanish
  maize 26%, Slovak pulses 19%, Slovak other cereals 26%, Cypriot wheat 9.9% and 4.6%. Market check of the welfare
  merge: a market solve at base EU supply and with 10% less EU beef and 5% less wheat gives identical prices,
  quantities and trade flows before and after it. Test suite (28 October 2026, 189 tests): 188 passed in two runs (the 14 longest, then the rest); test_parameter_file_and_code_agree failed on two parameters left by the K33 removal (INTENSITY_K, INTENSITY_M_MIN), removed in 7021a20, then passed. The tests' time is mostly the market supply Hessian, measured at the end of every baseline run and stored per worktree (the projection test: 1,449 s measuring, 61 s from the store).

## 27 October 2026 (evening): market supply Hessian, regions a shock does not reach not re-solved; option 4 tried and dropped

- **The market supply Hessian from the baseline's full state** (market.hessian_skip_unchanged, default true): the base is
  re-solved first and every shock starts from the same state (the regional models' whole solve state, not only the
  warm starts: RegionalSupplyModel.SOLVE_STATE); a region whose shocked problem, start and warm-start state equal the
  base's (the price does not reach it) is not built or solved again, as its solve would repeat the base's exactly. The
  same Hessian as re-solving every region from that state, entry by entry (five-region check, 5,183 entries); 111 of
  250 regional solves skipped, measurement 80 s -> 59 s. With the switch off, the measurement as before.
- **Faster regional build, results bit-identical**: the ammonia N cascade skips options without effect; crop nutrient
  coefficients from a dictionary instead of a pandas lookup per call. A regional solve that raises is now always
  warned about (before only with verbose).
- **Option 4 (exact first-order response from the optimality conditions, sIPOPT-style) tried and removed** (the project
  lead's decision): own-price responses agreed with re-solving (97% of entries within 1%), cross-price responses did not
  (45%). Re-solving with shocks of -1%, +0.5%, +1%, +2% showed why: the re-solves are deterministic and linear for
  upward shocks (Irish barley against the beef price -204.9, -205.3, -205.1), but the regional supply responses have
  kinks at the baseline (Irish wheat against the beef price -51.5 for a fall, +3.4 for a rise; German wheat against the
  sugar price +12.2 / -23.6): a constraint switches at the base point. The derivative at the base active set matches
  neither side; CAPRI's measurement (calibrate_supply.gms, +1%) takes the upward side, as the re-solve does. No speed
  gain either: building the regional problem, not IPOPT, is the cost. tools/check/compare_hessians.py kept.

## 27 October 2026 (afternoon): the model on CAPRI's regional units; results on NUTS 2024; water and income reports

- **The model's regions are CAPRI's 221 regional units** (EU27 215, Norway 6) under CAPRI's 8-character codes
  (`capri_data/shared/regional_units.csv`), as decided on 27 October: every region-keyed file rebuilt by its builder from
  CAPRI's own row of the unit; the NUTS-2016 crosswalk, the region map and the splits, merges, national copies and
  re-splits that stood between CAPRI's data and the 248 NUTS-2016 regions removed (with their sources: SSB, p_REGIO,
  Eurostat cattle). On the 196 units that were one NUTS-2016 region each, the rebuilt files equal the old ones except
  where the old value was a proxy or a stale fill; each difference and its cause is in
  docs/design/REGIONAL_UNITS_REBUILD_LOG.md (Italy's regional N deposition instead of the national value; CAPRI's own
  fertiliser substitution, grass and cattle intensity and set-aside terms instead of medians; crops absent from a member
  state at 0 instead of a template; fattening pigs where CAPRI has them). Builders written for files that had none
  (N deposition and substitution, livestock intensity bounds, PELA cross-price by region).
- **The fodder band rows removed** (kept until the move, 27 October morning): the units' NLP form has CAPRI's fodder
  equality only; bit-identical results in six regions, baseline and Farm-to-Fork.
- **K85 (fixed)**: animals a region does not have read a NaN input cost once the unsourced per-head columns of
  variable_costs.csv were emptied; 16 regions stopped at IPOPT's Invalid_Number_Detected in the first run on the units
  (r160, not used). Such an activity (fixed at 0) now costs 0, one with a base level without CAPRI cost raises, and the
  regional NLP refuses non-finite inputs.
- **Farm-to-Fork 2030 on the units (r161)**: converges in 9 iterations (r156 on NUTS 2016: 10), every regional solve
  optimal; the 20 indicators' mean absolute deviation from JRC121368 4.34 (r156: 4.44); indicators within 0.7 points of
  r156 (pork price +18.7 against +18.0, sheep and goats -10.1 against -10.7). The market supply Hessian measured again
  for the units (67 min); the run itself 36 min. Mineral fertiliser caps relaxed in BG020000-BG060000 (PERM), HR000000
  (ROOF), duals in HU220000 (r156: the same Bulgarian and Croatian regions under NUTS-2016 codes, DEA1, LT01).
- **Green Deal 2030 on the units (r162)**: converges in 8 iterations (r157 on NUTS 2016: 9), every regional solve
  optimal; every indicator within 0.3 points of r157 (cereal production -7.3% against -7.5, sheep and goats -8.0
  against -8.4, N surplus -27.1 and GHG -14.4 in both). Its own Hessian (the first attempt ran into the 2-hour limit
  with the Hessian measured; the rerun read it from the cache: 37 min). Mineral caps relaxed in the same regions as r157
  under CAPRI's codes (Bulgaria, Hungary, Ireland, Portugal's North and Azores).
- **K84 fixed as CAPRI**: an unreachable landscape floor is no longer lowered. CAPRI keeps it (supply_model.gms
  e_setaLandscape; widen_bounds.gms widens feeding, nutrient, land-use-change and fertiliser bounds, never the floor)
  and carries on with the solver's last point; so does the model, recorded in nlp_fallback with the note that CAPRI's
  Green Deal runs have the land market on. Only runs without the land market are concerned (the reference runs meet
  every floor). `landscape_shortfall` removed with the fit; the landscape test runs in 16 s instead of 80.
- **Hessian cache Parquet only**: the 205 market supply Hessians cached as CSV were converted to Parquet (each read to
  the last digit and checked equal after the conversion) and the CSV reader removed. Caches are Parquet, the pipeline
  store Delta, model inputs CSV, as decided on 27 October.
- **Builder intermediates as Parquet**: the two tables our builders compute and only other builders read,
  `abatement/ammonia/ammonia_cost_curves` and `ammonia_technology_effects`, are Parquet (each equal to the exact CSV
  read; the downstream builders' outputs unchanged to the last digit). Extracts of CAPRI, Eurostat and Outlook data stay
  CSV (input data; for about 25 the repository's only copy). The ASCII-header test covers Parquet columns too. Found on
  the way (K82 follow-up): the ammonia cost curves, technologies and technology model had not been rebuilt with exact
  CSV reads (up to 2.6e-14 relative in the model's ammonia_tech_model.csv); rebuilt.
- **Results on current NUTS (task 237)**: `capri_mod/nuts_reporting.to_nuts2024` maps unit results to the NUTS-2024
  regions (`capri_data/shared/capri_units_nuts2024.csv`, `tools/build/build_nuts2024_reporting.py`): unit -> NUTS 2016
  with CAPRI's correspondence and its splits and merges, then Eurostat's 2016-2021 and 2021-2024 changes (Croatia,
  Norway, NL31/NL33 -> NL35/NL36, Portugal's PT16-PT18). 202 of 217 groups are one unit to one region; the others are
  split by the regions' UAA (Eurostat ef_lus_main 2023; the 2020 census for BG, EL, ES, IT, LT, PL, SI, which have no
  NUTS-2 data for 2023 yet). Extensive values are split, intensive ones reported as the group's basis-weighted mean: a
  region of a multi-region group gets an area share of the group's result, not a result of its own. CAPRI has no unit
  for Brussels, Berlin, Bremen, Hamburg, Ceuta, Melilla, the French outermost regions and Svalbard.
- **Water and income reports restored on the units (task 236)**, outside the run as before:
  - water (`capri_mod/water`): irrigated areas from the FSS irrigated share (IRR2; the old module read the irrigable
    share IRRI) of each unit times its UAA, rice entirely and one share for the other crops CAPRI's water module
    irrigates (CAPRI fits crop shares to FSS crop data not among our sources: a departure, DEPARTURES_FROM_CAPRI.md);
    maize and wine, missed before (CAPRI's MAIZ, TWIN), included; CROPWAT's net irrigation requirement. Base 2017:
    11.2 Mha irrigated, 32 km3 net requirement; Ireland has no share in CAPRI's data, Norway no CROPWAT requirement;
  - income (`capri_mod/income`): CAPRI's ProfitAgr form, the sum over activities of (revenue - input cost + premium) x
    level; before, the policy module's CAP payments were added to net revenues that already held CAPRI's premiums
    (counted twice) and grassland was left out. The supply models keep the premium part of each net revenue
    (`premiums`; results unchanged).
- Tests: NUTS 2024 mapping and reporting (5), water and income (3), the own-price response in five contrasting units
  (arable, eastern arable, Mediterranean permanent crop, grassland cattle, intensive pigs). `tools/run/run_mini_eu.py`:
  the Farm-to-Fork run on 20 units covering the model's structures, against an earlier mini-EU run (task 239).
- Verification: full test suite 205 passed, 1 skipped (the live Eurostat query); the five new response tests failed
  at first with responses of 1e-6: their shock fell on a region's second solve, where the late split and histosol
  columns are calibrated (at that solve's prices), so the calibration took the shock up. The tests now solve the base
  twice, as a run's baseline does (wheat +15.0% in FR240000 for a 20% price, rye +39.1% in PL120000, bulls +17.0% in
  IR010000, fattening pigs +18.7% in NL220000, olives +2.5% in ES610000); the DE110000 test, whose weak check (no fall)
  had hidden the same effect, too. Reference runs on the units: r161 (Farm-to-Fork), r162 (Green Deal 2030).

## 27 October 2026 (morning): the test suite in half the time; two model issues found by its timing (K83, K84)

- **Every test gets a model as just built** (a copy, 0.7 s): the tests shared one model, so each started from the state
  the tests before it left (warm starts, calibrations taken at another test's point, the market's state). Results and run
  time depended on the order, and so did the market supply Hessian's cache key (the baseline solution): each suite run
  measured its Hessians again (the CAP-support test 429 s measuring, 18 s from the cache). The cache file is now written
  whole and renamed, so parallel test processes read a complete file or none (no change to any result: the Farm-to-Fork
  and Green Deal 2030 reference runs equal r155 and r154 exactly).
- **K83 (open)**: a one-region Farm-to-Fork run (DE11) with two supply-market iterations: the market diverged in both
  scenario steps (2 x 100 steps, 550 of the winter-cover test's 590 s); with one iteration it converges in 27 steps. Full-EU
  runs not affected. The winter-cover test runs one iteration.
- **K84 (open)**: the landscape floor's fit (land market off) ends on its last margin step in the regions examined (EL65,
  ITH1: 11 failed IPOPT solves; FRM0 ~580 s), so the recorded shortfall is mostly that margin. The test takes EL65 first.
- The organic no-op test at IPOPT's tolerance between two solves (K80), 1e-4 as the pesticide no-op test (1e-5 was
  exceeded by 1.08e-5).
- Tests handed out longest first, one at a time (pytest-xdist maxschedchunk 1; durations in capri_mod/tests/durations.json,
  refreshed by tools/check/test_durations.py). Full suite on 2 processes: 56 min -> 31 min (198 passed, 1 skipped).

## 27 October 2026: the switches whose alternative never ran removed; run options that mirrored a setting; water and income modules

A review of the reference runs (r150 Farm-to-Fork, r151 Green Deal 2030; recorded runs since about r100) found no
non-default value for any of the 79 switch or choice settings. The project lead's decision (docs/design/
SETTINGS_INVENTORY.md, update of 27 October; the CSV's column `status_27oct`):
- removed with the code of their unused value, the value every run used now built in: the earlier capri-mod forms
  (the supply audit's "before 24 October" branches, the square-root need rule, the staged NLP tolerance, the secant
  young-animal update, the legacy elasticity mode, the ration's own nitrate ingredient, the grassland row with a fifth
  of arable land, PMP cross terms "previous", ...) and the "model without this block" switches of blocks CAPRI always
  has (manure techniques, intensities, genetics, histosols, activity bounds, LUC, dairy block, GL demand, processing
  functions, TRQs, young-animal markets, baseline calibration, ...): 49 keys of defaults.toml;
- kept: CAPRI's own options, the CAPRI-ERROR-FIX parity switches, the numerical and comparison options,
  `market.market_supply_nq` (the fast tests run without the Hessian), the fodder band rows (to go with the regional
  units, which recompute the Hessian), and two departures still to be brought to CAPRI's setting (K65, K77);
- 19 options of tools/run/run_f2f_2030.py that only set a setting (use `--set section.key=value`; `--verbose` is
  `--set diagnostics.trace_outer=true`); the scenario overrides stay;
- the water and income modules (no run called them; each had only its own test), to be restored on CAPRI's regional
  units; tools/check/scenario_elasticity_check.py (it compared the removed legacy elasticity mode).
The market supply Hessian's cache key keeps the removed rules' values, so the cached Hessians stay valid.
Verification (with the calibration check of c4271af and the exact Hessian read of K82, e26234c): the full tests pass
(198; the live Eurostat query skipped); Farm-to-Fork 2030 (r155) and Green Deal 2030 (r154), reading the Hessians from
the cache, equal r150 and r151 to the last digit in every result (metadata only differ). Pushed to dev on 27 October
2026. r150 (Farm-to-Fork) and r151 (Green Deal 2030) are the reference runs.

## 26 October 2026: the conic form removed; a failed regional solve kept as CAPRI keeps it

- **Conic form removed** (the user's decision). No run had used it since r110 (no conic fallback in any run's
  metadata). The plain QP (`qp_solver.solve_qp`, Clarabel) did run in r146/r147, for the 13 regions without any
  agriculture in the data (zero areas and herds, no rations: PL31-PL34 and HR05-HR06, codes of a NUTS version the data
  fill under PL7x/PL8x and HR02-HR04, and the city regions DE30, DE50, DE60, BE10, AT13, ES63, ES64); they now go
  through the NLP with the same (zero) levels. A first coverage listing by function had missed this (it tested one line
  per function; corrected to statement level, which also changes 11 other entries of the list of never-run functions). Removed: `capri_mod/supply/feed_conic.py`,
  `capri_nlp.py` (its cascade-loss helper moved into `capri_regional_nlp.py`), `qp_solver.py`, the built-in
  interior-point fallback of `convex_qp.py` (Clarabel is required and stays for the manure-market pools), the plain QP
  path without feeding inside and its fallbacks (landscape-floor and balance-target fits on the QP, least-distance QP,
  SciPy trust-constr), the conic form's crop-group allocation check (`fert_dist_inside`), CAPRI's NUTMIN_ floor of the
  conic form (`use_min_mineral_share`, off in star 3.0 with the inner fertiliser model), the EU ration chosen outside
  the supply models (`Ration.solve`; with it `supply.fodder_at_shadow_price` and the ration and fodder dampings, which
  acted only there: DEPARTURES_FROM_CAPRI), `tools/check/nlp_check` and `tools/check/compare_qp_solvers.py`; settings
  `supply.supply_form`, `supply.use_feed_in_supply`, `supply.qp_solver`, `supply.trust_constr_maxiter`,
  `supply.conic_*`, `fertiliser.fd_nlp_max_iter`, `outer_loop.manure_pool_qp_max_iter`; run options `--supply-form`,
  `--qp-solver`, `--feed-in-supply`, `--no-feed-in-supply`, `--nutmin`.
- **Failed regional solve** (K55, the user's decision): where IPOPT fails from every start and JRC121368's N-target
  relaxation and the landscape-floor fit do not help, the region's last IPOPT point is kept, warned about and recorded
  (`result.nlp_nonoptimal`, `converged = False`, `metadata["nlp_fallback"]`, the run's `nlp_nonoptimal`), as CAPRI
  re-solves with widened bounds and carries on with a non-optimal solve (supply/simu_supply.gms, widen_bounds.gms:
  p_INFES); a regional model that cannot be built stops the run, as CAPRI aborts on an execution error.
- Renamed with the form: `_last_conic_duals` -> `_last_duals`, `_conic_ok` / `_conic_failed` / `_conic_status` ->
  `_nlp_ok` / `_nlp_failed` / `_nlp_status`; `result.conic_failed`, `conic_status`, `land_market_failed`,
  `fert_dist_status`, `fert_dist_priors` and the run's `conic_fallbacks`, `ipopt_polished`, `fert_dist_nlp`,
  `fert_dist_open` removed (always empty in the NLP form).
- Tests: the conic-only tests removed (the emission-tax test of the conic model, IPOPT polish, NUTMIN_, fertiliser
  distribution inside, the conic P accounts); the NLP failure test rewritten for CAPRI's handling.
- Gate: r149 (these changes without K81) reproduces the reference r145 exactly: same converged prices and quantities,
  same market supply Hessian (cache hit); differences only in metadata and in the duals of the 13 empty regions (zero
  before, the NLP's now). r150 (with K81) moves the 2030 baseline slightly at member-state level (new Hessian),
  converges in 10 iterations instead of 9, deviation from JRC121368 4.44 as before, indicators within 0.1 point.

## 26 October 2026: K75 found and fixed (a lagged fodder constraint in the NLP form); CAPRI's stop rule and price forecast as options

- **K75 fixed.** In the NLP form CAPRI's fodder balance SUPBAL_ is the equality with the feed columns; the conic form's
  band row stayed in the problem with the animals' fodder per head from the previous solve, binding, so each iteration's
  feeding tightened the next iteration's fodder constraint. Found by re-solving FRD1's traced problems of iterations 12
  and 25 with one part of the problem swapped at a time (the band rows alone moved its suckler cows by 36 thousand
  head). `supply.nlp_fodder_band_dropped = true` drops them (false restores them); the market supply Hessian's cache
  key carries the setting. Run r139: Farm-to-Fork converged in 12 iterations (before: not in 25), deviation from
  JRC121368 4.44 (before 4.83). Test: test_nlp_form_has_capri_fodder_equality_without_lagged_band.
- `market.hessian_scenario_iter` back to 0 (CAPRI's): re-measuring the Hessian at the scenario's state did not help (r132).
- CAPRI's stop rule (capmod/price_forecast.gms) in `capri_mod/utils/capri_stop.py`: its verdict is recorded every
  iteration (`outer_history[...]["conv"]["capri"]`, metadata `capri_stop`); `outer_loop.stop_rule = "capri"` lets it
  decide. CAPRI's price forecast (weighted average of the market's last prices) for every price as an option,
  `outer_loop.price_update = "capri"`. Tests: capri_mod/tests/test_capri_stop.py. Registered in DEPARTURES_FROM_CAPRI
  (the defaults stay the model's own until the comparison runs decide).
- Regional solves: a worker process that dies no longer hangs the run (concurrent.futures instead of
  multiprocessing.Pool; the regions left are solved in the parent, with a warning). Two runs with two workers each on
  8 GB had hung for an hour and a half. Test: test_dead_worker_does_not_hang_the_regional_solves.
- K79 opened: a few member states' production keeps moving between iterations by more than CAPRI's 0.05%.
- Tried and removed: an Anderson (secant) update of the supply-market loop (r143: 12 iterations as the adaptive step,
  CAPRI's averaging 9). Kept off: the exact CasADi Jacobian of each commodity's trade system (`market.exact_jacobian`,
  step G1 of the market programme: same equilibrium, no speed gain on its own; the base of the joint Newton planned in
  the refactor's market stage).
- Runs: r133/r134 lost (hung); r135 = r130 again (the worker change does not alter results); r136 (CAPRI's price
  forecast, before the fix) met the model's tolerance in 9 iterations with the suckler cows still falling, results
  within 0.8 points of r135; r139 (the fix) converged in 12 iterations.
- README: AI readiness, reusability and reproducibility (chapter 9); scope paragraph; settings in 7.6; current results.

## 25 October 2026: K75 option 2(b), the market supply Hessian measured again at the scenario's state; M3 scheduled

- `market.hessian_scenario_iter = 8` (departure from CAPRI, chosen by the user for K75): in a scenario, at outer
  iteration 8, the market supply Hessian is measured again with the supply models at the scenario's state (its
  young-animal and member-state milk prices in the cache key); the baseline's Hessian is CAPRI's and unchanged.
  `market_supply_hessian_log` in the run metadata lists every measurement.
- Bug found in r131 and fixed: building the Hessian's cache key raised a TypeError (a string added to the key tuple
  inside `repr`), so r131 ran without CAPRI's market supply function at all (baseline and scenario: own-price
  anticipation). The exception was caught and its warning silenced by the run script. r131 is discarded. Now:
  a failure is recorded in `market_supply_hessian_info` (`source = "failed"`, or `scenario_error`), the run script
  shows both warnings, and test_market_layers.py::test_market_supply_hessian_measured_at_base_and_at_scenario_state
  checks both measurements on two regions (88 s).
- r132 (the fix; 6,764 s, of which 3,735 s the scenario's Hessian): option (b) does not fix K75. The run follows r130 within 0.003 of the calf ratio, the calf price still creeps, not converged (only Portugal's milk gap, 0.0053). The scenario's Hessian differs from the baseline's by -10% in the calves' own response. See KNOWN_ISSUES K75.
- M3 (non-EU FeedNQ_ with FeedBal_): the user decided to port it at the refactor's market feed block step, after
  that block reproduces the frozen reference; registered in DEPARTURES_FROM_CAPRI until then.

## 24 October 2026 (evening): supply audit S5-S10 as CAPRI; the tariff on price plus transport (M10); raw milk inside the market (M5); K75 narrowed

**K75.** The suckler-cow drift is not the regional solves: run r127 re-solved the drifting regions (FRK1, FRD1, IE04,
FRG0, BE33, PT20, PT11) six times at the final prices and got the same herds to 3 decimals. Run r126 (price relaxation
1.0) stopped as "converged" after 13 iterations while still drifting, so a looser step is not a fix. The drift is the
outer loop's own slow mode through the young-animal and member-state milk prices.

**Runs.**
- r128: every change of this section on, the saving curvature included. Not converged in 25 iterations. The baseline's
  precision farming moved off its initial shares (K77).
- r129: the same, with supply.fert_slope_with_saving off (the default). Not converged in 25 iterations (the run time
  includes the Hessian measured again: 50 min; base re-solve 0.08 kt off). Against r123:
  - prices lower: beef +14.5% (r123 +19.8%), milk +18.9% (+23.1%), pork +23.5% (+28.3%), poultry +20.1% (+24.7%),
    cereals +11.4% (+12.6%);
  - livestock falls less: beef animals -13.4% (-17.8%), pigs -16.7% (-18.4%);
  - EU N surplus -31.4% (-31.2%), GHG -17.5% (-18.2%);
  - nitrification inhibitors 16.2% (16.3%; JRC121368 Table 17: 18%), precision farming 24.6% (24.8%);
  - histosol fallowing 52.7% of the histosol area (r123 21.7%; CAPRI's Farm-to-Fork about 9%, K59). Idled histosols
    now count towards the landscape floor as in CAPRI, and fallowing them is cheap against set-aside here; to be
    checked against CAPRI's histosol costs.
  - Which change moves the prices is not decomposed. Candidates are the Hessian measured from the baseline's state
    (K76), M5, and S6/S7.
- Convergence improved but is still not reached. The member states' milk gaps are below the tolerance from the 13th
  iteration (Portugal 0.0026; r123 0.0053-0.0068) and the young-animal imbalance is 0.0017. The beef price still
  creeps (+0.0005 per iteration) and suckler cows still fall about 12 thousand per iteration.
- r130 (r129 again, with the convergence tests recorded per iteration in outer_history; 50 min with the cached
  Hessian; same results): from the 9th iteration only the member states' milk test fails, at 0.0052-0.0055 against
  0.005, and it is Portugal alone.
  - Portugal's delivered milk rises (0.905 -> 0.920 of base) while its price falls (1.434 -> 1.392).
  - The Azores (PT20) add dairy cows against the falling milk price (63.5 -> 68.6 thousand).
  - Read as the cattle sector's slow mode showing through a small dairy block (K75).

**K76: the market supply Hessian's measurement left the baseline's models in another state (found and fixed 24 October
2026).**
- The shocks ran in a chain. Each warm-started from the previous shock's solution, and so did the final base re-solve,
  which was meant to leave the models as they came.
- In DE11 the re-solve ended at another stationary point of the non-convex NLP: 12 kt off the baseline. The next
  baseline from that state had 2% less wheat.
- A scenario run right after a measured Hessian therefore started from a state the baseline never had. The cached
  Hessians used by runs r122-r127 did not re-run the shocks, so those runs' scenarios did not have this.
- The measured terms are affected too: each shock was taken from a drifted point.
- Found when the cache keys changed (the new rules above) and the tests measured the Hessian instead of reading it:
  test_mineral_fertiliser_cap_binds and test_cap_support_not_double_counted failed after another test's run. With all
  of today's rules switched off they still failed, so this predates them.
- Now every shock starts from the baseline's state. The regional NLPs' _nlp_* warm starts and path state, and the
  N-price loop's state, are restored before each shock and after the base re-solve.
- DE11's base re-solve now deviates by 0.0035 kt, and the next baseline equals the calibrated base.
- The Hessian cache key carries the measurement ("shocks-from-base"), so every Hessian is measured again.

**Supply audit (K74; docs/design/ARCHITECTURE_REFACTOR.md 5.1b):**
- S6: a crop's nutrient need per ha follows its yield as in CAPRI's fert/fertned.gms.
  - The main-output part is linear in the yield. The straw part follows the scenario's yield shifts only;
    supply/endog_yields.gms leaves straw unchanged.
  - Crops at fertned's floor (15 kg/ha) or cap stay fixed.
  - The model used sqrt(yield ratio) on the whole need. CAPRI's SQRT in NUTNED_ acts on the technology variants'
    yield factor, not on yield changes.
  - The shares per CAPRI region, crop and nutrient come from CAPRI's 2030 dump (straw yields, need, the bounds). Built
    by build_npk_balance_2030.py, with CAPRI's straw content and caps read from the vendored envind/gascoeff.gms and
    fert/fertpar.gms. Columns main_share and straw_share were added; every other column is unchanged.
  - One function, capri_mod.fert.npk.need_yield_factor, is used at every site: the NLP's NUTNED_ per nutrient, the N
    row, the mineral caps and floors, the accounts, the inner distribution and the P balance.
  - Setting fertiliser.need_yield_rule; "sqrt" restores the old rule.
- S7: the crops' input costs follow their yields as in CAPRI's capmod/define_inputs.gms.
  - For each directly yield-dependent input i: f_i x cost_i x G x TF_I x (rho - 1). f_i is from inputs/yieldIY.gms
    (vendored); G is CAPRI's 2030 / 2017 yield growth, bounded 0.5-1.5 as CAPRI.
  - PLAP and INPO use the Green Deal's TF_I.
  - It applies after the scenario's yield shifts and after the price response.
  - New columns yd_rest/yd_plap/yd_inpo_eur_ha and yield_growth in plant_protection_cost.csv. CAPRI's 2030 yields
    extracted to capri_data/sources/capri_res/yild_2030_ref.csv.xz. The other columns are unchanged.
  - Setting supply.yield_dependent_inputs.
- S8: the permanent-grassland rule's multiplier at calibration is CAPRI's assumed dual, |arable rent - grassland
  rent| (supply/prep_cal.gms l. 118-131), instead of zero. Setting supply.perm_gras_cal_dual.
- S9: catch crops count on the ecological set-aside row at CAPRI's weight 0.3 where the NLP's winter-cover option is
  present.
  - The base gap includes CAPRI's 2030 catch-crop share.
  - ISET, GSET and TSET have no area in CAPRI's 2017 or 2030 data, so SETA = FALL + VSET at weight 1 is CAPRI's own.
- S10, landscape floor: idled histosols count on the landscape floor (CAPRI's setaFallow). The floor's SETF is
  FALL + VSET, the model's SETA (checked in CAPRI's 2030 dump).
- S10, crop diversification: under the floor, the diversification limit is lowered by CAPRI's formula
  (pol_input/greendeal/landscape.gms l. 75-90).
- S5, cost base: in the NLP form, the fertiliser options' cost is charged on the fertilisation block's N purchases
  (CAPRI's GHG_Mit_Cost_: - cost x v_netPutQuant(NITF)). Their calibration uses the base purchases.
- S5, curvature: CAPRI's pmpParSqr (ghgMiti.gms l. 1016-1035).
  - The fertiliser saving, valued at the member state's NITF price, is in the curvature:
    + nmE x p x ((1 + nmE m1)^-2 - (1 + nmE m0)^-2) / (m1 - m0), with nmE = NMIN + EmiCalmin. EmiCalmin is the
    inhibitor's literature side effects on the base mineral losses.
  - The curvature turns non-positive in 96 region-options, mostly precision farming (NMIN about 0.5). CAPRI's total
    cost with the convex endogenous saving has its stationary points at both shares. The NLP form keeps these options
    as CAPRI does; the conic form leaves them out (registered).
  - Setting supply.fert_slope_with_saving, OFF by default since 25 October (K77): together with the cost on the purchases
    it moved the 2030 baseline off its initial shares (FR10 precision farming 0.44; run r128, EU 9.6%).
  - Switches for the parts without one: supply.fert_cost_on_purchases (cost base) and supply.eco_setaside_catch_crops (S9).
  - This replaces the registered note that the term "cancels": it does not. The NLP's fertilisation block carries the
    convex saving, and the curvature has to offset it.

**Market audit (K73):**
- M10: a tariff change applies to price plus transport cost of the importer's external flows (CAPRI impPrice_), per
  importer region.
  - tc column added to bilateral_flows_*.csv by its builder; every other column of every bilateral file is identical.
  - The EU, EU27 or an EU region maps to the EU rows.
- M7: welfare is labelled EUR million, with the base domestic price as base.
- M5 (implemented; its run is pending): each member state's raw milk follows its own milk price inside the market,
  through the measured Hessian per member state.
  - It is cleared against its dairies in the dairy block, jointly with the young-animal markets.
  - The member state's milk price moves the other products' and the young animals' supply.
  - Setting market.milk_in_market.
- The market supply Hessian's cache key now includes the rules above, so it is measured again.

**Tests:** fast suite 150 passed (53 min: the tests' Hessians are measured again under the new cache key).

## 24 October 2026: the mineral-cap exemptions found by cause (K71); every patched input rebuilt by its builders (K70); the CAPTRD variance floor; the market split by block

**K71, mineral caps.** The blanket fallback (every mineral cap of a failing region raised to 1.1 x base) is gone.
- Cause, traced in BG33: CAPRI's organic rule (organic_minfert_redu.gms) caps a group's mineral N at
  baseline x (1 - its conversion). Bulgaria's permanent-crop conversion is 79.5 points (organic_targets.gdx), so
  PERM's cap falls from 10.4 to 2.1 kg N/ha. Its need net of own residues is about 7 kg/ha of effective N, and its
  manure prior (0.002 kg/ha, bounded at 1000 x the mode as in CAPRI's prep_sim.gms) cannot supply it.
- r101 did not hit this because zero-level permanent crops could enter the group and enlarge its capped area. They
  can no longer do so (absent_activities_fixed, CAPRI's rule).
- Now: after the widened duals, only the groups concerned are exempted, one at a time, at their baseline
  (fertiliser.exempt_cap_factor = 1.0, CAPRI's p_checkSmallMine level). The set is pruned to the smallest that solves
  and recorded as nlp_relaxed ("caps:PERM").
- Single-region tests: PERM in BG32, BG33, BG34, BG41, BG42, FI19, FI1C; PERM+ROOF in HR04 and LT01; NL12 none.
- Also fixed on the way: after a relaxation, the ammonia-fixed re-solve used the strict spec.

**K70, inputs without a builder.**
- `tools/build/build_supply_elasticities_regional.py`: PELA 2005 own-price slice with CAPRI's upper-bound rule;
  reproduces the file.
- `tools/build/build_patched_inputs.py`: runs the seven builders that patch yields.csv, producer_prices.csv and
  armington_params.csv, in their order; `--check` reproduces all three and every other file they write.
- `manure_n2o_tech.csv` rebuilt by build_manure_n2o: 29 rows added (AirPurCovHigh for pigs in 15 EU regions, offered
  by ammonia_tech_model.csv, missing from the old file); all other rows unchanged.
- New open issue K72: 146 of the 248 cells of armington_params.csv have no builder (eta and eps of about 30 products
  are round numbers of unrecorded source).

**CAPTRD-MOD.** The stored error variance's floor is (0.05 x |wAve|)^2, a variance, instead of CAPRI's 0.05 x |wAve|
(CAPRI-ERROR-FIX; `captrd.variance_floor_squared`; no effect on results until Steps 2-3 are ported).

**Architecture (docs/design/ARCHITECTURE_REFACTOR.md).**
- Stage 1: `market_module.py` (3,243 lines) split by block into `calibration.py`, `biofuel.py`, `dairy.py`, `feed.py`,
  `demand.py`, `processing.py`, `supply.py`, `bilateral_solve.py` (mixins of MarketModule) and `equilibrium.py`; code
  unchanged. Gate: the Farm-to-Fork run r111s equals r111 within 1e-10 (`tools/check/compare_pickles_exact.py`).
- Stage 2a: `capri_mod/market/inputs.py` (MarketInputs), the market's data adapter, is the only market code that
  reads files; it uses the model's data directory and base year (the blocks read a fixed capri_data/2017 path
  before). Eleven loaders that silently switched a block off on any error now stop the run. Test
  `capri_mod/tests/test_market_layers.py`. Gate: run r111a equals r111 within 1e-10.

**CAPRI-claim audit of the market (docs/design/ARCHITECTURE_REFACTOR.md section 5.1; table
docs/design/audit/market_claims.csv).** 75 claims: 23 verified, 16 registered, 15 unregistered differences,
17 unsourced, 4 unverifiable (KNOWN_ISSUES K73). The project lead's decision: every item that is not a verified port
is brought to CAPRI's equations, inside the layered structure (section 6).

**Conformity step 1 (M1, M8, CET yields; run r112).**
- Food demand: consumer prices move with CAPRI's Armington price (Cpri_ = Arm1P + margins): ARM1P0 x (ratio - 1)
  instead of the model's base world price x (1 + AVE). ARM1P added to gl_demand_goods.csv (build_gl_demand.py;
  CAPRI's RMS_TO_RM now in capri_data/shared/rms_to_rm.csv).
- Processing (ProcNQ_): H x ARM1P0 x (ratio - 1) per behavioural region (processing_nq_hessian.csv gains arm1p_x,
  arm1p_y).
- Crushing per behavioural region (new processing_seeds.csv, build_processing_seeds.py): margin = - seed ARM1P +
  oil and cake PPRI x their CET yields (ProcMargO_, procYield_ with p_rhoProc 0.01); ProcFudge_ (a smooth max(q, 0))
  instead of the 1%-of-base floor; output = crush x CET yields. Exact at base (7.5e-12).
- Run r112 (Farm-to-Fork 2030, default settings): converged in 11 iterations, no conic fallbacks. Against r111: milk
  price +23.3% (r111 +24.6), oilseed price +13.9 (+14.5), vegetables and permanent crops +13.2 (+13.9), cereal
  +11.9 (+12.1), beef +18.0 (+17.5); herds and environmental aggregates within 0.5 points.

**Conformity step 2 (CAPRI's Armington balance ArmBal1_; run r113).** Use = HCON + FEED + PROC + BIOF per region,
split by CAPRI's 2030 components (new use_components.csv, build_use_components.py; HCON + FEED + PROC + BIOF
reproduces CAPRI's ARM1 within 1e-4). Each component has its own equation where CAPRI has one and is fixed where CAPRI
has none. The generic own-price response QD0 (P/P0)^eta on the rest of use is gone, and with it the use of the eta
column of armington_params.csv, the FAO_agg EU elasticities (audit M2) and the EU p_ElasDem medians. At base the
demand equals the old one within 8e-11. Raw milk outside the EU stays a pooled world market with fixed use (CAPRI:
not traded, cleared in its dairy blocks; recorded as M11).
- Run r113: converged in 12 iterations, no conic fallbacks; every EU aggregate within 0.2 points of r112 (beef price
  +18.2 against +18.0). PT30 needed the widened inner-model duals (new).
- Removed as unused (orphans under ArmBal1_): the eta, sigma and rho2 columns of armington_params.csv (the market
  reads CAPRI's p_rhoArm1/2 from armington_rho.csv; eps stays), eu_demand_elas_overrides.json,
  fao_demand_own_elas_eu.json and tools/build/build_demand_elas_capri.py; the builders no longer write those columns
  (build_patched_inputs.py --check reproduces the files); the tests of tobacco and textile crops check CAPRI's
  processing functions instead of the removed overrides.

**Supply audit (docs/design/ARCHITECTURE_REFACTOR.md 5.1b; docs/design/audit/supply_claims.csv; KNOWN_ISSUES K74).**
145 claims: 48 verified, 60 registered, 17 unregistered differences, 13 unsourced, 7 unverifiable.
- S1 fixed (run r114): with feeding inside the regional model the animals' net revenue no longer gets the feed-price
  change, which the model's feed purchases already carry (CAPRI costs feed once, QUADRF_). Run r114: converged in 11
  iterations; livestock prices 0.3-0.4 points lower (pork +29.5 against +29.9, beef +17.9 against +18.2), herds
  0.1-0.2 points higher; other aggregates unchanged. The double count was small in Farm-to-Fork because the EU feed
  bulk prices move little (cereal bulk 0.93-0.97 of base, protein bulk about 1.0).
- S3/S4 (and the plant-protection and other-input part of S11): CAPRI's form of the Green Deal input changes
  (SupplyModule._apply_greendeal_input_changes; organic_io.gms, conventional_io.gms, define_inputs.gms). One regional
  change per input on every activity: plant protection -o_R with the organic target alone, -r overall with the
  pesticide target; other inputs +(r - o_R), animals included; the organic crops' other inputs topped up by
  2 x their crop target x their fuel cost. CAPRI's organic crop set and crop targets (no grassland, fodder, other
  oilseeds or minor crops; Portugal has no arable or permanent-crop target in CAPRI's data), and the organic yield gap
  only on the grouped organic crops with a gap estimate, borrowing CAPRI's Central-European value where the region's
  macro-region has none (organic_area.gms l. 176-181; was a flat 20%, ORGANIC_YIELD_GAP, removed). Replaced: +100% other inputs on converted land, +50% x the
  conventional share, PLAP cut per crop, and the parameters ORGANIC_OTHER_COST_RISE, PESTICIDE_OTHER_COST_RISE and the
  fallback shares OTHER_COST_SHARE, PPP_COST_SHARE.
  - Data: plant_protection_cost.csv's other-input cost per ha now includes its unit value (it was CAPRI's bare
    coefficient, about 20% low; median ratio 1.25); new columns eful_eur_ha, eful_inpo_eur_ha and, for the animals,
    inpo_toin_share. crop_cost_shares.csv keeps only fert_cost_share (the other two columns had no use left).
  - Two CAPRI code errors corrected by default, each with a parity switch (DEPARTURES_FROM_CAPRI):
    supply.greendeal_inputs_keep_tech_change (the compile-time scenAugmentsTechChange off replaces the 2017-2030
    input-saving progress) and supply.organic_topup_at_fuel_cost (the top-up valued at INPO's unit value).
  - Registered: the changes act on CAPRI's 2017 coefficients (not its simulation-year ones, which also carry the
    yield-dependent input adjustment). The fertiliser side of the organic target keeps the model's crop mapping.
  - Runs: r116 (S3/S4) and r117 (S3/S4 + M6) do not converge in 25 iterations (KNOWN_ISSUES K75). Cause found: from the
    10th iteration Brittany's warm-started NLP ended at a worse stationary point (livestock at its lower bounds,
    objective 9% worse, reported as solved) and stayed there; a cold start finds the better optimum every time.
    Safeguard supply.nlp_warm_check (0.01): such a warm result is checked against the other starts and the lowest
    objective kept. Run r118 (S3/S4 + M6 + check): Brittany as in r115; against r115 crop prices +0.7-1.0 points,
    beef +1.9, pork -1.2, milk -0.3; crop production -0.5 to -0.9, beef -1.2. Still not converged: Portugal's
    member-state milk gap 0.0051-0.0065 from the 11th iteration, drifting with the beef premium (K75). Not accepted
    as results yet.

**Market, 24 October (continued).**
- K75, young-animal markets inside the market (CAPRI's yaniMarket_ with the market supply functions): the market supply
  Hessian gets young-animal rows and columns (calibrate_supply.gms l. 437-458), the market clears the young-animal
  prices with the products in every evaluation (MarketModule._yani_clear), the outer loop passes them on with the
  products' adaptive step; market.market_supply_nq switched to CAPRI's setting (true), young_animals.in_market = true.
  Raw milk enters the supply functions at the models' price (its trade-system ratio is the pooled world ratio).
  The Hessian is measured once per baseline (50 shocks, 49 min on 2 cores) and cached. Run r123: young-animal
  imbalance 0.0004 at the 15th iteration; 25th iteration equal to r119 within 0.1 point; still not converged
  (Portugal's milk gap 0.0053-0.0068, a late calf-price creep; K75).
- M11 fixed (run r115): raw milk outside the EU is no longer one pooled world market. Each region with a dairy block
  clears its raw milk inside the block (ProdNQ_ against DairyNQ_), supply and use carrying the block's quantity; a
  region without a block keeps its base. Run r115 equals r114 within 1e-10 in every stored result: the pooled
  raw-milk market fed nothing else (the EU and Norway take their blocks' prices; the dairy blocks see product prices).
  From run r116 the region's reported raw-milk price is its block's, and the run file stores raw milk per region.
- M6 fixed (run r117, not converged: K75): feed_bulks_no.csv rebuilt with Norway's feed rho capped at 2.0 (arm/market1.gms l. 98; FCER and FPRO 6 -> 2,
  FENE 5 -> 2); the other feed-bulk files are unchanged.

**Tests:** fast suite 136 passed; pipeline tests 23 passed, 1 skipped.

## 23 October 2026 (evening): the proxy removals; CAPRI's Pillar II budgets; CAPTRD-MOD Step 1

**Proxies removed (docs/design/PROXY_AUDIT.md, "Status after the removal").**
- **Land:** the land-supply fallback is gone, along with land_supply_elasticity, land_expansion_cap, land_inner_max
  and land_tol. Land moves only through CAPRI's land market, which is active in 235 of 248 regions; the other 13 have
  no farmland. The outer loop's land criterion became the regional N-balance price (outer_loop.nbal_update_tol).
- **Policy:**
  - the payments engine takes CAPRI's 2030 budgets per scheme (CEILVAL: DPPIL1, DPRD_LFA, DPRD_N2K, DPAE, DPNAT,
    DPTOTAL) and the per-activity premium split (PRME by scheme). Files: cap_ceilings_2030.csv,
    premium_scheme_shares_2030.csv;
  - Pillar II scenario changes act through per-region premium factors;
  - InterventionSystem, PaymentType, DirectPaymentScheme, EcoScheme and the participation-rate presets are deleted.
  - CAPRI's intervention stocks are not active in its 2030 data (PADM and INTM Eps), so nothing was ported.
- **Data:**
  - animal yields rebuilt per model head;
  - N exported in animal products: CAPRI's coefficients (livestock_n_export_coef.csv);
  - crushing: CAPRI's parameters (crushing_parameters.csv);
  - non-EU supply: CAPRI's elasticity where CAPRI has one, else none;
  - member-state codes in one CSV;
  - the land-market data moved from JSON to CSV;
  - the fertiliser module was deleted.
- **Tests:** the elasticity provenance test follows the "no literature defaults" rule. A cell without a CAPRI value
  is NaN and labelled NO_CAPRI_VALUE.

**CAPTRD-MOD started (docs/design/CAPTRD_MOD.md section 12).**
- New package `capri_mod/pipeline/captrd`:
  - `step1.py`: CAPTRD's trend estimator and statistics;
  - `timesets.py`: CAPTRD's time sets.
- Parity references in `capri_reference/`, built by two new tools:
  - CAPREG's time series (35 countries, 35.3 million records);
  - CAPTRD's own results, results_1770.gdx.
- On CAPTRD's own estimation data the port reproduces Step 1 for 99.78% of 96,478 comparable series.
- **CAPRI code error found and confirmed:** series with 2–4 observations get Step1 = 0 (estimate_trends.gms
  l. 160-171). It is corrected by default (CAPRI-ERROR-FIX, docs/DEPARTURES_FROM_CAPRI.md), with
  `captrd.short_series_grid_as_coded = true` for parity.
- The listed "BASYRS5 spans 7 years" defect is not one in the reference configuration: the window is five ex-post
  years.

**Tests:** six tests relied on behaviour removed with the proxies and were updated:
- the bare SupplyModule reference, now K68;
- the default elasticities;
- the feed share cap of 0.98;
- one supply solve per run, since the land loop is gone: the split columns enter from the second solve;
- the solver-scale reproducibility tolerance.

**Fixed after the package (23 October 2026, night):**
- **K68:** the activities' calibration now carries CAPRI's land rent, so the plain supply solve reproduces the base
  (within 0.01 kha on DE11, DE14, FRH0, ITC4).
- **EE00 SUGB yield:** the unsourced 500 t/ha is set to 0 (docs/DATA_FIXES.md).

- **K69 solver error:** the CAP crop-diversification index (a Shannon index with logarithms) left out the
  zero-level activities; with them fixed at zero, IPOPT's trial steps took the logarithm below its floor. With
  CAPRI's setting (`absent_activities_fixed = true`) a 2030 baseline then runs without invalid values (24 regions had
  them). Full run r109 under way.
- **tools/ reorganised** (tools/README.md):
  - new folders build/ run/ check/ gams/ lib/, with `tools/lib/paths.py` to find the repository root and tools by
    name;
  - 18 tools removed (superseded exports, report generators, broken diagnostics, applied one-off migrations,
    builders of unread files), together with 3 orphan data files;
  - every reference updated (218 files).
- **Data pipeline, step 2 of the CAPTRD-MOD plan** (docs/DATA_PIPELINE.md):
  - the Eurostat adapter (SDMX-CSV) and the FAOSTAT adapter (bulk files, chunked);
  - the store (raw files, Delta tables), the manifest with checksums, and the command line
    `python -m capri_mod.pipeline`;
  - the catalogue of COCO's inputs: 108 datasets mapped from CAPRI's code, checked live;
  - tests offline on real samples, plus live tests on request.

**K69 fixed:** absent activities are held at zero as in CAPRI (default `absent_activities_fixed = true`). The
permanent-grassland and crop-diversification rules leave them out. Reference run r110 converges in 11 iterations,
with no conic fallbacks, and every EU aggregate is within 0.8 points of r101. Open: more regions relax the mineral
caps (K71).

**Earlier state (before the fix):** the Farm-to-Fork 2030 runs (r103, r105) stop at 25 iterations unconverged.
- **The symptom:** the EU sugar price cycles with period three.
- **The cause:** zero-level activities enter freely once the literature elasticities are gone. Estonia's sugar beet
  jumps 0 → 171 kha on an unsourced yield of 500 t/ha; 88 zero-level activities enter in r105.
- **What was tried:** CAPRI's setting (absent_activities_fixed = true, r108) brought back the NLP degeneracy recorded
  for that departure (NaN in the constraint function), so the run was stopped.

## 23 October 2026 (afternoon): the breeding options' calibration as CAPRI's; one settings file; no presets without a source

The project lead's requests: "fix everything and go to next"; then, on the settings: "no proxies, find the data or get
my help" and "follow capri apart the errors and then we describe the difference".

- **K67 F2: the animal options' PMP slope nets CAPRI's cost-saving drop.**
  - CAPRI: pmpParsqr = max[floor x |c|, c (relSubs1 - relSubs0) - (costsaving0 - costsaving1)] / (MaxShare -
    IniShare) (breeding.gms l. 447-458; low_n_feed.gms l. 265-272; line_nitr.gms). costsaving0 and costsaving1 are
    the options' marginal values in CAPRI's two calibration runs (ini, and max with every breeding, supplement and
    low-N feed option at its maximum share).
  - capri-mod left the drop out, under a registered deviation whose reasoning was reversed: the planned slope is the
    total curvature of the option's net cost, of which the model's own fall is a part, so leaving it out counts that
    curvature twice.
  - Now column `dsav` of genetics_, lownfeed_ and supplement_effects.csv: CAPRI's drop from its runs
    (capri_costsavings_2030.csv), per model head adopting (tools/lib/_capri_costsavings.py: sum over the CAPRI members
    of MaxShare x (M0 - M1) / (capri_level_ratio x sum of MaxShare x LEVL)), per unit of the technology parameter.
  - Median effect on the planned slope: nitrate -24%, low-N feed -8%, linseed -2%, genet_eff +28% (its marginal value
    rises towards the max run).
  - The drop is CAPRI's model's, not capri-mod's: capri-mod's own max run would be the self-consistent alternative (not
    built; stated to the project lead).
- **K67 F3: the breeding options' cost floors per place.** CAPRI's floors (2 and 20 EUR) are per animal place; they
  are now converted per model head with the stock factor over capri_level_ratio, as the ammonia options' costs (K63).
- **K67 F4: adoption of the animal options as CAPRI reports herd shares.**
  - Share of the eligible herd in livestock units: results['adoption_lu'], with CAPRI's LEVW / LEVL per model head in
    the new capri_data/2017/supply/livestock_units.csv (tools/build/build_livestock_units.py).
  - The baseline is read from the baseline run, and the MaxShare ceiling is shown in brackets (tools/check/compare_runs.py).
- **Runs** (Farm-to-Fork 2030; mean absolute deviation from JRC121368, 20 indicators):

  | Run | PMP terms | Deviation | Iterations | Minutes |
  |---|---|---|---|---|
  | r99 | CAPRI's 2030 terms (default) | 4.89 (r97: 4.97) | 15 | 34 |
  | r100 | recipe | 5.03 (r98: 5.02) | 11 | 28 |

  - Every indicator moves by less than 0.7 points.
  - Low-N feed covers 42.7% of manure N (r97 42.5%), or 65.4% of the eligible herd in livestock units.
  - Breeding stays at its cap, 0.2% of the eligible herd.
- **K66 checked without CAPRI's regional results** (the project lead has no CAPRI Farm-to-Fork results to export).
  - The farmland expansion is broad: regions with N prices of 1-10 EUR/kg give +3.1 of the +6.0 points (r97, land
    types), regions above 100 EUR/kg 0.7.
  - Forest falls by 16.7 Mha, of which about 10 to farmland and 7 to other land, through the cross terms of CAPRI's
    own land-type matrix.
  - capri-mod's land market is CAPRI's Trustee_land form, with ARTIF fixed and the total-land row an inequality; both
    differences would make it expand less, not more.
- **One settings file** (the project lead's decision, 23 October 2026).
  - Every run switch, tolerance, iteration limit and algorithm choice is in capri_mod/settings/defaults.toml: 157
    keys in 10 sections, each commented with CAPRI's equivalent.
  - The code reads them through `setting(...)` class attributes, so assigning to one is an error. There is no
    second default: the class duplicates and getattr fallbacks that disagreed are gone. Nothing is carried by hand
    to a projected model: ProjectionModule.CARRIED_SETTINGS is removed.
  - This fixes a bug the inventory found: `--no-gl-demand` had no effect in 2030 runs.
  - The 14 model_setting rows left model_parameters.csv; the run tool takes --settings FILE and --set key=value, and
    writes the effective settings next to each result (<out>.settings.toml).
  - docs/design/SETTINGS_INVENTORY.md and .csv list every setting and constant with its home.
  - **Behaviour-neutral, checked**: 2030 Farm-to-Fork on four regions through the projection (CAPRI's terms and
    recipe) gives 0 differences against the code before; the full runs r101 / r102 reproduce r99 / r100 to the last
    digit (activities, prices, accounts, metadata).
  - One consequence for a SupplyModule built without CAPRIModel (tests, a few tools): it now runs with the model's
    settings (land market on, CAPRI's land rules, ammonia options); before, RegionalSupplyModel's own class defaults
    (off) held there until a CAPRIModel overwrote them. Two tests of the fallback land supply set the old values
    explicitly.
- **Tests**: 160, all pass (27 minutes). New: test_option_costsaving_drop_follows_capri,
  test_settings_layer_is_the_one_source_of_run_settings.
- **Departures from CAPRI's settings described** (docs/DEPARTURES_FROM_CAPRI.md).
  - Two corrections of CAPRI code errors kept (CAPRI-ERROR-FIX): AD on dairy cows' CH4, and the sign of the application
    options in LEACHN_.
  - Five defaults that differ from CAPRI's for practical reasons are marked DEPARTURE and are to be switched one at a
    time, with a full run after each: the EU trade blocks, the market supply calibrated to the supply models, fodder
    at its shadow price, absent activities without a variable, and the cattle member splits (K65).
- **Deleted** (the project lead's decision: no presets without a CAPRI source, no orphans).
  - Scenario presets: CAP_REFORM_2030, WTO_LIB, CAP_2023_2027, N_LIMITS_TIGHTER, WTO_FALCONER, GREEN_DEAL_F2F.
  - Unused or wrong code: capri_mod/data/capri_reference.py, definitions.BASE_YEAR (2012), PROJECTION_YEARS,
    PROCESSING_OUTPUTS, NTM_AVE_PCT, utils.calibrate_demand_elasticities, and the uncalled Armington premium with its
    three parameters.
- **Proxy audit** (docs/design/PROXY_AUDIT.md: 105 items):
  - 28 are never reached and go, with a loud failure in their place;
  - 4 are CAPRI's own numbers and get their citation;
  - 12 are to be replaced with CAPRI data already in the workspace;
  - the rest are CAPRI-form rewrites or the project lead's decisions.

## 23 October 2026 (night): CAPRI's cap on the breeding options; oilseed codes; the young-animal markets' exact response; tolerances as parameters

The project lead's request: "Fix tests, the still open issues and the cattle activities with their own levels and the
young-animal markets by sex".

- **Breeding options capped as CAPRI's** (K67).
  - CAPRI caps every breeding option at MaxShare 0.002 unless %fixGenet_eff_to_iniValues% is off (envind/breeding.gms
    l. 65-77; only its agora policy files set it off), lowered to its max calibration run's level where smaller
    (l. 375-379).
  - tools/build/build_genetics_effects.py used MaxShare 1: higher ruminant efficiency covered 79% of non-dairy ruminants
    under Farm-to-Fork.
  - Now column max_share in genetics_effects.csv, applied by the endotech setting fixGenetToIni: 1 in star 3.0's and
    the JRC121368-era settings, as CAPRI's default; 0 restores MaxShare 1.
  - The builder also read the cattle file's member-split rows for the heifers' eligible share (0.97 instead of 0.13);
    now it reads the intensity pair's row. The delivered file predates those rows, so no run was affected.
- **Low N feed** (42.5% of manure N against Table 17's 0%): checked against CAPRI's code (low_n_feed.gms). Its effects,
  costs, eligible shares and calibration are CAPRI's star 3.0. Its adoption follows from the N-surplus duals (K66).
  Table 17's 0 cannot be reproduced from star 3.0's code.
- **FRH0's set-aside and the farmland expansion** (K66, open).
  - The per-hectare N target is CAPRI's e_SURTOTHa (surplus over the current land types), so extra land dilutes the
    surplus and the land market supplies it.
  - EU UAA +5.5% against CAPRI's +3% (now reported by tools/check/compare_runs.py as "UAA", outside the 20-indicator mean).
  - Where the target binds at extreme prices, forest and other land convert (BE33 +71%; BE32, BE35, NL23).
  - Not changed: the rule for which regions get JRC121368's 36% cut waits for CAPRI's regional Farm-to-Fork results.
- **Young-animal markets per sex** (K65, narrowed, still off).
  - The price update can take each region's response from its solved NLP: `CapriRegionalNLP.response`, the KKT
    sensitivity in the active rows' null space, and `RegionalSupplyModel._yani_response`.
  - Checked against finite differences (FRH0, cattle goods within 1%) and on 12 regions (0.005 reached in 8
    iterations).
  - It is used only with the cattle member splits on, so default runs are unchanged.
  - The full Farm-to-Fork run (r96) still did not converge: the male calves' price rose above 6 x base, the female
    calves' below zero.
- **Oilseed product codes** (the project lead's question): PROCESSING_OUTPUTS and FEED_ITEMS (capri_mod/data/
  definitions.py) and the cake columns of feed_requirements.csv used RAPM, SUFO, SUFM, SOYM, codes of no market. They
  now use CAPRI's RAPO / SUNO / SOYO (oils) and RAPC / SUNC / SOYC (cakes), as the market and crushing do.
  - No results changed: the lists were read only by a test (which exempted those codes, now none) and by a fallback no
    region uses.
- **Convergence tolerances as parameters**: OUTER_TOLERANCE, SUPPLY_GAP_TOL, LAND_UPDATE_TOL, MANURE_POOL_TOL,
  YANI_TOL, BASE_CAL_TOL in model_parameters.csv (were constants in model.py); same values. Moving all settings into
  one settings file is agreed as the next step.
- **Full runs** (Farm-to-Fork 2030, two workers; mean absolute deviation from JRC121368, 20 indicators):

  | Run | PMP terms | Deviation | Iterations | Minutes | Breeding (milk yield / ruminant efficiency) |
  |---|---|---|---|---|---|
  | r97 | CAPRI's 2030 terms (default) | 4.97 (r94: 4.62) | 11 | 27 | 0.0% / 0.2% (r94: 15.5% / 78.7%) |
  | r98 | recipe | 5.02 (r95: 4.69) | 11 | 28 | 0.0% / 0.2% |

  The change in deviation is the breeding cap. The milk price rises more (+25.2 against +20.9; CAPRI +1.5) and enteric
  methane falls less (-10.6 against -11.9; CAPRI -14.6). Other indicators move by 1.3 points at most.
- **Tests**: all 158 pass (22 slow), 27 minutes. Test-time review (the project lead's request):
  - The slow tests take most of the time: the ten slowest about 800 s of the 1,600. Each checks a different mechanism
    (worker-process identity, the two N-target relaxations, set-aside, projection identity and 2030 reference,
    Norway, the fertiliser distribution, the P accounts, the organic and pesticide targets), so none is a duplicate to
    drop.
  - Two were trimmed without losing what they check: the parallel-solve identity on two regions instead of four
    (112 to 95 s), the set-aside requirement on two outer iterations (77 to 58 s).
  - The larger saving would come from sharing cached baseline runs between tests, a next step with the settings
    work.

## 22 October 2026 (evening): labour accounts; CAPRI's set-aside split; CAPRI's cattle activities and per-sex young-animal markets (built, off: K65); the CAPTRD-MOD design

The project lead's requests: "can you do both?" (labour accounts and the set-aside split), "ok proceed" (CAPRI's
endogenous cattle activities each with its own level), "ok" (young-animal markets per sex), then "Package now, fix
after" when those markets did not converge.

- **Labour accounts, as CAPRI's** (`results["labour"]`; tools/build/build_labour_setaside.py ->
  capri_data/2017/supply/labour_coef.csv).
  - CAPRI's GROF LABT = sum of LABT x LEVL / 1000 (million hours), with the family (LABF) and paid (LABP) parts.
  - Per model activity and region, from CAPRI's members (hours per CAPRI unit; animals per model head through
    capri_level_ratio). 2017 coefficients from the res_17 dumps; 2030 ones from CAPRI's 2030 reference, used at the
    2030 market year.
  - An account after the solve, as in CAPRI, where labour is an indicator, not a constraint of the supply model.
  - At the base points the regional totals are CAPRI's within 2%: 2017 DE11 20.60 against 20.66, FR52 115.1 against
    115.6, IT20 179.8 against 182.9; 2030 DE11 21.94 against 22.00, ES41 216.0 against 220.0.
- **CAPRI's two set-aside activities reported** (`results["set_aside"]`; set_aside_split.csv).
  - The model's SETA is CAPRI's VSET (voluntary set-aside) and FALL (fallow), which differ only in premium and
    labour.
  - Reported split: VSET = s X0 + w (X - X0), FALL = X - VSET. Here s is CAPRI's VSET share and w = q_FALL /
    (q_VSET + q_FALL), the share of a common change CAPRI's own PMP terms give VSET (technology blocks collapsed;
    2017: the recipe's 2017 terms, as CAPREG's file holds one technology's term).
  - Premiums and labour follow per activity.
- **CAPRI's cattle activities with their own levels, and the young-animal markets per sex: built, switched off**
  (KNOWN_ISSUES K65).
  - CAPRI optimises HEIR (replacement heifers) and CAMF, CAFF, CAMR, CAFR (calves) on their own, and clears young
    animals per sex (INPANI_).
  - Built:
    - split columns per CAPRI activity, each member bounded at zero, with PMP block E' diag(q) E
      (`RegionalSupplyModel.CATTLE_SPLIT_MEMBERS`, `cattle_split_hessian`);
    - the splits' rows in tools/build/build_cattle_intensity.py (young animals bought and sold per sex);
    - per-sex balances (young_animals_by_sex_2017.json);
    - the animals' herd terms grouped for the members (<stem>_animals_members.csv, tools/build/build_animal_pmp_capri_2030.py
      --splits);
    - the splits' response in the young-animal price update.
  - The Farm-to-Fork 2030 run did not converge with them:
    - r89 diverged (male calves x 8, female -1);
    - r90 (the splits' response added) fell only from 0.052 to 0.033 in six iterations;
    - r91 (Broyden update of the price Jacobian) oscillated in every good;
    - r92 (own-response scaling, kept as `CAPRIModel.use_yani_secant`, off) stayed at 0.035-0.05.

    Cause: the price update predicts the supply response from the PMP terms alone, which ignores binding constraints.
  - `RegionalSupplyModel.use_cattle_member_splits = False` keeps the validated state of r86 / r87: the intensity
    pairs only, pooled young-animal markets, and the default data files (unchanged, rebuilt identically by their
    builders).
  - Making the switch exact found one leak: the greenhouse-gas cost derivatives (supply/ghg_tax.py) looped over every
    split key in the data (a 1e-7 difference that, after four iterations, sent the non-convex supply models down
    another path). The switch now also covers that loop and the order of two sums and of the split's bound rows.
    Four regions, baseline plus three Farm-to-Fork iterations: identical to the last digit with the afternoon code.
- **CAPTRD-MOD design** (docs/design/): the agreed design of the data pipeline and baseline projection layer
  (CAPTRD_MOD.md, a living document), the map of CAPRI's CAPTRD code with file:line citations (CAPTRD_MAP.md) and four
  state-of-the-art reviews (sota/). No model code changed by it.
- **Full runs** (Farm-to-Fork 2030, two workers, defaults; mean absolute deviation from JRC121368 over 20 indicators):

  | Run | PMP terms | Deviation | Iterations | Minutes | Against the afternoon's run |
  |---|---|---|---|---|---|
  | r94 | CAPRI's 2030 terms (default) | 4.62 | 12 | 30 | r86: every indicator, the EU activity levels and the young-animal prices identical |
  | r95 | recipe | 4.69 | 11 | 26 | r87: identical in the same way |

  - New accounts in these runs (EU27, baseline to Farm-to-Fork, CAPRI's terms):
    - labour 13,305 to 12,750 million hours (-4.2%; family -2.1%, paid -5.8%);
    - voluntary set-aside 2,762 to 10,109 kha, fallow 5,029 to 10,306 kha;
    - their premiums 745 to 2,242 and 899 to 2,001 million EUR.
  - r93, run before the GHG-cost leak was closed, converged in 11 iterations with indicators within 0.2 points of r86
    (deviation 4.64).
- **Open findings, unchanged by this work:**
  - FRH0's set-aside grows from about 5 to about 708 kha under Farm-to-Fork (about 36% of its UAA), with an N-surplus
    dual of 29 EUR/kg and pigs -66%. Not yet investigated.
  - Two technologies are adopted far above CAPRI's rates: higher ruminant efficiency (79% against CAPRI's 9%) and low
    N feed (43% against 0%).
- **Tests**: two adapted to the switch (the bull and heifer split test now also runs with the member splits on; the
  per-sex data test reads the per-sex file and checks it adds up to the pooled one).
  test_data_headers_are_ascii now exempts a provider's file kept byte for byte (<name>_original.csv: Statistics
  Norway's table, added this afternoon, has a byte-order mark and Norwegian headers). All 158 pass (22 slow), 26
  minutes.

## 22 October 2026 (afternoon): the recipe's land nest; Norway's pig census; ammonia options at base; 2030 curvature of the intensity splits

The project lead's request: "fix the land and open items".

- **Land-nest adjustment in capri-mod's own PMP terms** (K61; tools/build/build_pmp_recipe.py step 2b): CAPRI's
  p_landNestElasContrib (cal_land_nests.gms l. 729, trustee land market) and its use in forecast_activity_slopes.gms
  (l. 103-141) ported. The land types' posterior own-rent elasticities are recomputed from CAPRI's exported land
  matrices with the land owner's bordered Hessian (declare_calibration_models_for_land_supply.gms; CAPRI's estimation
  makes them an exact function of that matrix but does not export them); CAPRI's 2017 land matrices stored as
  capri_data/sources/capreg/pmp_quad_landtypes_2017.csv. CAPRI's literal share (the crop's level over ARAB + ANNC +
  ARAC) kept: it reproduces CAPRI's terms better than the share in ARAC alone (crops within 1% of CAPRI's: 2017 78%
  against 63%, 2030 62% against 42%; without the adjustment 68% and 49%). Effect on the model-form terms: permanent
  crops steeper (medians: olives +13 to +17%, wine +5 to +8%, fruit +1 to +6%), arable crops unchanged at 2030 (medians within 0.1%).
- **Inflation year of the recipe's 2017 terms**: 14 years of p_infl (CALYEA 2018), inferred from CAPRI's CAPREG terms:
  the group terms within 1% of CAPRI's in all 1,447 pairs (3% with 13 years). Recipe against CAPRI: activity terms
  within 5% 80.5% at 2030, 89.6% at 2017 (76.8%, 87.1% before). Still off: a regional tail in the estimated crops
  (docs/PMP_CAPRI_2030.md).
- **Norway's pigs by Statistics Norway's census** (K56): NO01, NO03, NO04, NO05 share CAPRI's NO08 + NO09 + NO0A pig
  herds by SSB's 2017 county census (sows: breeding pigs; fattening pigs: pigs slaughtered or sold live) instead of
  Eurostat's cattle shares (SSB's file, downloaded by the project lead, read by tools/build/build_ssb_pigs.py; the earlier
  transcription from ssb.no matched it in every cell); the project lead's 2020 file of pig places (SSB) is the check (it cannot separate NO01
  from NO03). NO04 now 0.54-0.56 of the pool (cattle key 0.42), NO05 0.09-0.10 (0.36). Changed: the four regions'
  herds and piglet net exports only (per-head coefficients are per territory group; rebuild checked file by file).
- **Ammonia options at their base shares without a policy incentive** (K63, closed): the poultry storage and spreading
  options that left their initial shares at the 2030 baseline (ITC4 broilers' covered storage 0.43, CAPRI 0) did so
  because the calibrated base is a saddle along the options' joint direction and IPOPT's interior start left it;
  CAPRI's costsavings0 (ammo_tech.gms l. 3366-3379) makes its base a first-order point and CONOPT stays there.
  `RegionalSupplyModel.amm_fix_without_policy` (default on) holds them at their base shares without an N-surplus row,
  mineral cap or emission tax, and re-solves with them held where the N-surplus row is slack - the conic form's rule.
  At the 2030 baseline every option in ITC4, DE94, FRH0, NL22 is at its initial share.
- **Intensity splits at 2030** (K61): CAPRI's 2030 p_pmpQuadTechn of DCOL/DCOH, BULL/BULH, HEIL/HEIH, GRAE/GRAI
  (tools/build/build_intensity_q_2030.py; the three intensity builders add q_<x>_capri2030 / _recipe2030 beside the base
  year's columns, which are unchanged) taken at the 2030 market year with pmp_source capri2030 or recipe. Medians
  2030 / 2017: dairy 1.8, bulls 1.4, heifers 1.3.
- **K13 (milk price)**: tools/gams/export_capmod_results.gms for the project lead: dumps CAPRI's CAPMOD 2030 result files
  (Farm-to-Fork / Green Deal runs, if present in the installation) - the data K13 needs.
- **Market flag (K64), fixed**: traced to Norway's tobacco row - Norway's supply models returned 6.4e-6 kt of tobacco
  (solver residue on an activity without a base level), which no trade flow could take, as Norway has no base
  production. CAPRI has no variable for such an activity; `RegionalSupplyModel.absent_output_cleared` reports the
  residue (|level| <= 1e-4) as zero. A bound row holding those activities at zero was tried first and dropped: it
  degenerated the NLP form's fertiliser block (EL62 fell back to the conic form, eleven regions relaxed their mineral
  caps, 82 minutes).
- **Full runs** (Farm-to-Fork 2030, two workers, mean absolute deviation from JRC121368 over 20 indicators):

  | Run | PMP terms | Deviation | Iterations | Minutes | Market |
  |---|---|---|---|---|---|
  | r86 | CAPRI's 2030 terms (default) | 4.62 (r83: 4.62) | 12 (14) | 32 (36) | converged (r83: flag) |
  | r87 | recipe, with the land nest | 4.69 (r85: 4.75) | 11 (11) | 28 (58, one worker) | converged (r85: flag) |

  No conic fallbacks; mineral caps relaxed in HR03, HR04, LT01 as before (r83 also PT11). Ammonia adoption at the
  baseline now at CAPRI's initial shares (covered storage 9.1% against 12.7% in r83 - CAPRI reports 14% in JRC121368
  Table 17 with its own weights; low-emission spreading 41.2% against 43.0%); Farm-to-Fork adoption within 1 point of
  r83 (histosol fallowing 21.9 against 21.0, higher milk yield 15.5 against 16.2, the others within 0.6).
- **Tests**: five new (recipe against CAPRI's terms, the land-nest elasticities, the 2030 curvature of the splits,
  Norway's pig split, the ammonia options at base - slow); all 156 pass (22 slow), 24 minutes.

## 21-22 October 2026 (night): CAPRI's 2030 PMP terms; ammonia option costs; milk price step

- **CAPRI's own 2030 PMP terms, as an option** (`--pmp capri2030`, `SupplyModule.pmp_source`; KNOWN_ISSUES K61,
  docs/PMP_CAPRI_2030.md). Exported from the project lead's CAPRI installation (`tools/gams/export_pmp_2030.gms`, 35
  countries; `tools/build/build_pmp_2030.py`) and transferred to the model's activities and regions:
  - crops (`tools/build/build_pmp_capri_2030.py`): technology terms collapsed per crop, group terms on the groups' levels at
    full size, territories aggregated exactly for a quadratic cost; Austria's crop supply elasticities move close to
    CAPRI's own simulated ones (rapeseed 9.7 against CAPRI's 12.4, our calibration 2.6; barley 3.0 / 3.4 / 0.9);
  - animals' herd terms (`tools/build/build_animal_pmp_capri_2030.py`; the intensity splits' curvature stays 2017);
  - feed-PMP slopes of the 2030 calibration (`capri_slope_2030`, `tools/build/build_feed_ration.py`);
  - the land market's 2030 land-type terms (`tools/build/build_land_market.py --year 2030`, whose 2017 mode reproduces the
    2017 file exactly).
  The groups can be switched separately (`--pmp-parts crops,animals,feed,land`). Default unchanged (our elasticity
  calibration) until the project lead decides. A first version of the animals' terms had a scaling error (herds 100
  to 25,000 times too steep; Farm-to-Fork deviation 11.4); found from that run and fixed, with a test.
- **capri-mod's own PMP calibration with CAPRI's recipe** (`--pmp recipe`, the project lead's request): the terms
  computed from CAPRI's estimates (estnlp VB, VD, PELA) and the calibration point's data as supply/define_pmp_terms.gms
  does (`tools/build/build_pmp_recipe.py --year 2030|2017`; transfer as for the exported terms). Against CAPRI's own terms
  (`tools/check/pmp_recipe_check.py`): 2030 77% of 11,694 activity terms within 5% (89% within 20%), 2017 against CAPREG 87%
  (97%), group terms 89% / 100%. Farm-to-Fork with it (r85): mean deviation from JRC121368 4.75 (CAPRI's exported
  terms 4.62, the elasticity calibration 5.30), 11 iterations. Not ported yet: CAPRI's land-nest adjustment. Why the
  elasticity calibration differed (`tools/check/pmp_elasticity_target_check.py`): it delivers its own targets; its targets and
  its capped cross terms left out CAPRI's within-group substitution.
- **Default PMP terms at 2030: CAPRI's exported terms** (`SupplyModule.pmp_source = "capri2030"`, the project lead's
  decision of 22 October 2026); `--pmp elasticity` and `--pmp recipe` remain.
- **Slow tests** (three failures, no model error): the set-aside test counted cells below 1 ha (German paddy rice
  1.3e-6 -> 0.0017 kha, a relative change of 1,379); the relaxed-target test's region NL12 now meets the tiered target
  by itself (since K59/K60: dairy cows -80% at 2017 prices), so the test forces a target it cannot meet; the land-rent
  test read the base model because `ProjectionModule._solve` did not record its projected model (now it does).
  Rerun: 3 passed. Fast suite after the night's changes: two tests updated (the 2030 matrix test now expects the
  animals' herd terms, merged into pmp_capri_2030 by the loader; the coverage test leaves out inputs declared
  `alternative_to` another, i.e. the recipe terms, not read by the default run), 130 passed. All 151 tests pass.
- **Ammonia options' cost basis (K63)**: per place of the model's heads (stock_factor / capri_level_ratio) and CAPRI's
  x 1000 for poultry's housing and air purification (ammo_tech.gms l. 153-157, 640-643). At the 2030 baseline every
  non-poultry option is within 0.04 of CAPRI's initial share (before: up to 0.37); poultry's storage and spreading
  options open.
- **Member states' milk price step (K62)**: CAPRI's step weights tried as default and not kept (Spain's milk price
  swung, gap 0.34 at the 9th iteration); the adaptive step stays.
- **Market flag (K64)**: the market's 1e-6 residual reported, not loosened.
- **Full runs** (all with Norway's pigs and K63; one or two workers as noted):

  | | iterations | minutes | mean deviation from JRC121368 (20 indicators) |
  |---|---|---|---|
  | Farm-to-Fork, our terms (r77, 1 worker, two runs in parallel) | 12 | 56 | 5.30 |
  | Farm-to-Fork, CAPRI's crop terms (r78, idem) | 11 | 61 | 5.11 |
  | Farm-to-Fork, all CAPRI terms (r83, 2 workers) | 14 | 36 | **4.62** |
  | Green Deal 2030, our terms (r79, 2 workers) | 14 | 32 | (no CAPRI result in hand) |
  | Green Deal 2030, CAPRI's crop terms (r80, 2 workers) | 10 | 29 | |
  | Green Deal 2030, all CAPRI terms (r84) | 16 | 39 | |

  Farm-to-Fork with all CAPRI terms against our terms: pork price +28.7 against +38.9% (CAPRI +43), poultry price
  +24.4 / +32.7 (CAPRI +18), milk price +21.4 / +29.7 (CAPRI +1.5, K13), pigs -18.4 / -21.5 (CAPRI -14.5), poultry
  -16.8 / -20.7 (CAPRI -16.5), cereal production -14.1 / -12.3 (CAPRI -15), GHG -18.4 / -19.2 (CAPRI -14.8).
- Two runs in parallel with two workers each exceed the workspace's 8 GB (a worker was killed and the run hung): run
  them one at a time, or with `CAPRI_WORKERS=1`.

---

## 21 October 2026 (evening): Norway's pigs

- **Norway's supply regions have CAPRI's pig herds (KNOWN_ISSUES K56).** Norway's regions NO01-NO07 had PIGS = PIGF = 0:
  `tools/build/build_capri_base.py` read the census total 'PIGS'.'HERD' and `tools/build_pig_split.py` set PIGF = total -
  sows, and CAPRI's Norwegian data (res_17NO) have no census total, only SOWS and PIGF HERD. `tools/build/build_norway_pigs.py`
  sets PIGS := CAPRI's SOWS HERD and PIGF := CAPRI's PIGF HERD through build_capri_base's region spec (imported): NO02,
  NO06, NO07 their own CAPRI region; NO01, NO03, NO04, NO05 Eurostat cattle shares of NO08 + NO09 + NO0A, a proxy for
  pigs inherited from build_capri_base (all their other items use it). Totals: sows 49.8, fattening pigs 451.4 thousand
  head (= NO000000's HERD).
- **Head definition.** Norway's PIGF head is CAPRI's fattening place (HERD), the EU rows' the census stock of non-sow
  pigs (DE11: 953.6 census, CAPRI PIGF HERD 604.1). Every per-head coefficient is CAPRI's regional total over the
  model's heads, so Norway's base totals are CAPRI's whatever the head: pork 139.76 kt (LEVL x PORK of SOWS 3.98 +
  PIGF 135.78 = NO000000's GROF PORK), manure N 9.18 kt (1.66 + 7.53), manure P2O5 and K2O 4.58 kt each (CAPRI's MANP
  = MANK for pigs), CH4, feed (FCER 401, FPRO 757 kt), costs, revenue, premiums, piglets (3.61 per fattening place a
  year). Norway's per-head values are not comparable with the EU's (pork per PIGF head 0.30 t, DE11 0.16 t);
  capri_level_ratio (model heads per CAPRI LEVL) is 0.28 for Norway's PIGF, 1 for its sows.
- **Files rebuilt by their builders** (`build_norway_pigs.py --rebuild`: build_shg_split's coefficient tables and
  steps, then build_npk_balance_2030.py and build_capri_level_ratio.py): animal_numbers.csv; livestock_output,
  _output_by_product, _revenue, _cost, _output_value, _product_value, _product_value_by_market, _premium coefficients;
  livestock_feed_coef.csv, feed_ration_2017.json, young_animals_2017.json (piglets); livestock_manure_n/p/k_coef.csv,
  livestock_ch4ent/ch4man_coef.csv; capri_level_ratio.csv. Only Norway's pig cells changed (checked against a copy
  of capri_data, tolerance 1e-9). `tools/build/build_manure_n2o.py` no longer reproduces manure_n2o_tech.csv (it would add 29
  AirPurCovHigh pig rows in EU regions); that file is kept as it was (its Norwegian rows are the same either way).
  Already complete for Norway, unchanged: nh3_factors_capri.json, ammonia_tech_model.csv, manure_housing_losses_2030.csv,
  manure_n2o_factors.csv, the 2030 trajectories (ratios). Norway has no rows in lownfeed_effects.csv for any animal.
- **Market: no code change.** NOR's supply per product is its supply models' output where they produce it
  (`MarketModule.supply_response`, `_align_sup_base`), so pork moves from CAPRI's market supply function to the supply
  models by itself, its Hessian under `market_supply_nq` is measured on them, piglets clear in Norway's young-animal
  market and its feed bulks follow its herds with the pigs. test_norway_market.py checks the herds, the per-head pork
  and manure N against CAPRI's totals, and NOR's pork = its supply models' in a baseline with NO01.
- **Found on the way**: the ammonia options' cost per model head was CAPRI's cost per place x DAYS/365, a model head
  counted as one CAPRI LEVL unit (Norway's fattening pigs, 0.28 heads per LEVL: 0.28 of CAPRI's cost; EU PIGF median 0.52).
  Fixed the same evening, KNOWN_ISSUES K63 (see the next section).

---

## CAPRI's land rents in the calibration; histosol fallowing; PMP structure; Norway's crushing (21 October 2026, afternoon)

- **Land rents as CAPRI** (docs/LAND_RENT_CALIBRATION_PLAN.md, follow-up of K58). CAPRI takes the land rents as given
  in its calibration (supply/cal_land_nests.gms; prep_cal.gms l. 125-156 subtracts the "assumed land rent" from the
  activities' costs). `tools/build/build_land_rents.py` -> `land_rents_2030.csv`: D_AREA of ARAC, FRUN and grassland at CAPRI's
  2030 reference (248 regions; 27 take their member state's; non-positive values, not CAPRI calibration rents, are not
  used: grassland in 10 regions, PT20). At the 2030 market year the land market's constants are
  set at these rents (they were the model's own base duals) and the NLP calibration fixes the land balances'
  multipliers at them; the ridge stays for other undetermined pairs. The 2017 base keeps the model's own duals
  (no CAPRI EU rents for 2017 in hand; registered).
- **Grassland land row an equality (K60)**: it kept the land data's headroom (IE04 173 kha): grass could grow onto it at
  no land cost.
- **Histosol fallowing (K59)**: the idled area was on the upper land row only, so it was held at zero wherever the pair
  is tight; no histosol was ever fallowed (CAPRI's Farm-to-Fork: 2 -> 9%). Now on both rows.
- **PMP cross terms in CAPRI's structure (K61)**: only between crops of CAPRI's groups; no uniform term elsewhere.
  `tools/check/pmp_cross_term_check.py` (CAPRI's decomposition experiment): every group's response within 0.06 points across
  the structures - with capri-mod's caps the cross terms are small. CAPRI's group curvature at its size needs CAPRI's
  2030 PMP terms (open).
- **Norway's soya crushing** (405 kt, CAPRI's FAO_agg and p_ElasProc; `tools/build_crushing_nor.py`). Norway's pig
  activity stays open: its herd source has no Norwegian pigs (K56).
- **Docs corrected**: MANURE_MARKET.md (the manure columns' tax term is exact since K55(6)); P_BALANCE.md (open points 3
  and 4 were fixed on 20 October).
- **Full runs** (land rents in the calibration, K59, K60, ridge K58): Farm-to-Fork converged in 15 iterations, 32.8 min (r69), mean deviation from JRC121368 5.34 over 20 indicators, histosol fallowing 21.8% (CAPRI 9%); Green Deal 2030 converged in 21 iterations, 47 min (r71), Portugal's milk price in a two-cycle from the 10th iteration (gap 0.005 / 0.03 alternating, K62). The market's largest relative residual stayed about 1e-6 (TOBA, SUNF) after 100 rounds, reported as 'MARKET NOT CONVERGED' in the run summary (KNOWN_ISSUES K64).

---

## NLP calibration fixed (K58); three Dutch regions back in CAPRI's form (K57); Farm-to-Fork in 26.5 minutes (21 October 2026)

- **Found.** NL11, NL13 and NL32 (and NL34 once) failed in IPOPT at the tiered Farm-to-Fork N target in every scenario
  iteration, and the conic form stood in (r54-r63). It is not a regression: the pre-merge version fails on NL13 the
  same way, but recorded nothing (warning only); the fallback log (K55) made it visible. They rank 11th-14th by CAPRI's
  baseline N surplus, just below JRC121368's nine capped regions, and get the full tiered cut (NL13: 65.5 kg N/ha
  against 141.7 at 36%).
- **Fixed (agreed with the user).** In the NLP form, where CAPRI's form fails at the tiered target, JRC121368's rule
  for regions whose target "generated infeasibilities in the model" (sect. 4.3.4: the EU-average cut, 36%) is tried in
  CAPRI's form first, kept for the scenario and recorded in `metadata["nlp_fallback"]`. The model already applied this
  rule when the conic form failed. If CAPRI's form fails at the relaxed target too, the conic form at the tiered target
  stands in, as before. REGISTERED: IPOPT's infeasibility is local, not a proof; these regions now get a looser target
  than the conic form reaches.
- **Speed.** The failed attempts (up to three starts x 3,000 IPOPT iterations per region and iteration) were most of
  the NLP form's slowdown: supply time per iteration 165-185 s (r60, r63) -> 82-105 s (r65).
- **NLP calibration (K58).** The multiplier fit of `CapriRegionalNLP.calibrate` was degenerate where a row and a
  bound are active on the same variable (grassland_lo with land_GRAS at its bound): unregularised, it returned
  multipliers of 6e13 and grass's linear term took them (5e10 EUR/ha in IE04), an objective gradient of 1e14 that made
  IPOPT's tolerances meaningless and its solutions path-dependent (IE04's carbon-tax response: suckler cows 370 or
  315 kha by two equivalent code paths). A ridge term (CAL_RIDGE 1e-10) picks the least-norm multipliers; the fit's
  residual is unchanged. DEPARTURE (stated): CAPRI takes the duals of its calibration solve.
- **Farm-to-Fork 2030 (r67, with both fixes):** converged in 12 iterations, 1,587 s (26.5 min, 2 cores); every region
  in CAPRI's form (NL11, NL13, NL32, NL34 at JRC121368's relaxed target); mean absolute deviation from JRC121368 5.55
  on 20 indicators (r52, before the decisions of 20 October and Norway: 5.75). Largest moves against r52: N surplus
  -32.0% (r52 -29.5, CAPRI -33.5), fertiliser N2O -36.5 (-34.2, CAPRI -40.4), poultry price +34.7 (+33.3, CAPRI +18).
  Against r65 (K57 only, before K58) every indicator within 0.6 points. Norway's last price gap 0.0027 (beef).
- **Green Deal 2030 (r66, before K58):** converged in 14 iterations, 1,993 s (33 min); no region outside CAPRI's form;
  against r51 every indicator within 1.7 points; winter cover 32.2% of the eligible area (r51 26.1%: the share is now
  the regional model's choice).
- **Green Deal 2030 (r68, with both fixes):** converged in 13 iterations, 1,692 s (28.2 min); every region in
  CAPRI's form; against r66 every indicator within 0.3 points. No CAPRI result for these settings is at hand.
- **Phosphate accounts (conic form, or no fertilisation block):** CAPRI's need multiplier for P is calibrated at the
  base and fixed in simulation; the accounts recomputed it with the scenario's manure-trade setting (Farm-to-Fork: no
  trade after a baseline with trade), so their mineral P2O5 differed from the regional model's (DE11 6,464 against
  7,317 t). The base manure now follows the first setting seen for the region, as the regional model's block does.
  NLP-form runs (r67, r68) use the block's purchases and are unaffected.
- **Plan:** CAPRI's land rents in the calibration instead of fitted land multipliers (docs/LAND_RENT_CALIBRATION_PLAN.md).
- **Tests:** 143 (20 slow) pass, 25.8 min. New: test_nlp_form_takes_jrc121368_relaxation_where_the_tiered_n_target_fails;
  test_jrc_relaxed_n_target_is_kept checks the NLP form stays in CAPRI's form (it passed before while NL12 was in the
  conic form); test_emission_tax_in_supply_follows_capri and test_p_accounts_from_the_nlp_solution failed before K58 and
  the phosphate fix.
- **Orphan debugging switches** used to find this were not kept.

---

## Norway as its own market region, as CAPRI (KNOWN_ISSUES K56, 21 October 2026)

Norway's supply regions (NO01-NO07) fed the EU's market supply and EU totals while CAPRI's bilateral data counted
Norway (NO000000) in ROW: Norway was counted twice (about 1% of EU totals). The user's decision: as CAPRI, where
NO000000 is a market region of its own (aggregation/defaultA.agg) linked to supply models (RMSSUP).

- **Data.** Trade region NOR (`definitions.TRADE_REGIONS`, 30 regions; the EU27 block holds no Norwegian country);
  `tools/build/recalibrate_trade_2017.py` REGION_MAP maps NO000000 to NOR, and every per-region market file was rebuilt
  with its builder from CAPRI's own NO000000 data: bilateral flows, regions and TRQs (2017, 2030, `_eu2`), tariffs,
  world and dairy base balances, GL food demand, processing functions, non-EU feed demand (Norway has none: CAPRI's
  FeedBal_ is for non-RMSSUP regions), biofuel markets, regional supply elasticities, the dairy blocks (the EU's block
  and balance now hold the EU member states only; Norway's block is a non-EU one), `feed_bulks_no.csv` (+ Norway's use
  per product). ROW before = ROW + NOR now, to the files' rounding (largest difference 0.007 kt); every other region
  unchanged. Side effects: FPRI world price 252.66 -> 252.74 EUR/t (Norway's exports now count in the export-weighted
  price), dairy eta in armington_params.csv by at most 3e-4.
- **Market (CAPRI's RMSSUP treatment, `market_model.gms` ProdNQ_, feedBlkPrice_, feedShareEqu_, yaniMarket_).** NOR's
  supply is its supply models' output (fixed in a market solve; anticipated against the prices its models saw with
  CAPRI's p_elasSupp of NO000000; with `market_supply_nq`, its own Hessian); the base is calibrated at it; its raw milk
  goes to its own dairy block, delivered by its supply models; its feed follows its herds through its bulks on CAPRI's
  feed share of its use; its young animals clear in its own market. Its supply models see Norway's prices, also in
  their feed bulk and young-animal prices, in the outer loop's convergence test as CAPRI's (below).
- **Norway's price signal (convergence).** First passed as the EU signal plus a relaxed departure (as the EU trade
  blocks). Full Farm-to-Fork runs did not converge in 25 iterations (r54-r60), and the cause was this form. Every move
  of the EU signal moved Norway's prices too. On a subset run the EU's other-cereal and oat targets crept up 0.3% per
  iteration, and Norway's cereals lagged 1-2% behind their own, nearly flat, prices for ten iterations. Norway's price
  is now a level of its own, relaxed toward Norway's market price with its own adaptive step per product (halved on a
  direction flip, floor 0.1). This is the form already used for the member states' milk prices, and it matches
  CAPRI, which passes Norway's own market prices to its models. Also: the young-animal imbalance is scaled by at least
  10% of the product's total (Norway's thin markets gave relative noise, r54).
- **Norway in the convergence test, CAPRI's rule** (capmod/price_forecast.gms). A price change counts only where
  production exceeds 10 x p_minAbsProdIterChg (0.5 kt, capmod.gms l. 384), i.e. 5 kt (`SUP_GAP_MIN_PROD`). From the 15th
  iteration on, Norway's changes are set to zero: `p_iterChg("NO000000",ROWS,STEP) $ (ORD(step) ge 15) = 0`, with
  CAPRI's comment "Norway reacts very sensitive and seems to jump around" (`SUP_GAP_LAST_ITER`). Before this, Norway's
  prices of products it does not produce (maize, wine, olive oil, tobacco) swung 13-75% (r56-r58). Its other cereals
  (about 2.6 kt) moved 1-5% while every EU gap was below tolerance (r62, iterations 12-15). Norway's prices are still
  relaxed and reported after iteration 15, and its last gap is in the run metadata (`nor_price_gap`).
- **Reporting.** Norway is out of the EU27 market rows and `env_EU_*`; `flatten_outputs` adds `prod_NOR_*`,
  `price_NOR_*`, `env_NO_*`; tools/run/run_f2f_2030.py (activity and output totals) and tools/check/compare_runs.py (accounts)
  compare the EU27 without Norway with CAPRI.
- **Checks** (diagnostic runs on small region sets, which do not converge, K10). Baseline on DK01 + IE04 with and
  without NO01-NO07: EU27 production, use and prices identical (difference 0); NOR production = Norway's models' output
  (barley 550.1, milk 1597.5 kt), Norway counted once in world totals; base residual of the market 1e-9 with prices at
  the reference. Farm-to-Fork on the same regions, 4 outer iterations: Norway's prices move with its own market (barley
  +2.6%, beef -0.1%, raw milk +0.8%) while the EU's move by -4.1%, +2.7%, +4.5%. 9 tests in
  capri_mod/tests/test_norway_market.py.
- **Open.** The model's Norway has no pig activity (its pork is CAPRI's market supply function at Norway's price);
  Norway's oilseed crushing has no crushing function (as ROW's); a run without Norway's regions keeps NOR at CAPRI's
  base with its elasticities. Results of runs made before this change carry Norway in the EU totals.
- **Orphan removed.** `MarketModule` still built one CES import aggregator per region and product (`ArmingtonDemand`,
  `_build_armington_systems`) from `shared/trade_flows_2017.csv`, with a default sigma of 3 and uniform shares for
  small importers; nothing read them since the bilateral market replaced the old structure. Removed, with the model's
  load of `trade_flows.csv` (out of `INPUT_SCHEMA.json`; the file stays as an input of
  `tools/check/validate_world_prices.py` and `tools/build/recalibrate_trade_2017.py`). The start-up line now counts the bilateral
  market's trade regions (30; it printed the old file's 26).

---

## The user's decisions on the review findings (20 October 2026)

Details: KNOWN_ISSUES K51, K52, K54, K55, K56; docs/WINTER_COVER.md.

- **Interface (K52):** FARM_TO_FORK, FLAT_RATE_BPS, UKRAINE_SHOCK and the unused WORLD_PRICE_SHOCKS removed;
  `trq_volume_changes` on CAPRI's EU tariff-rate quotas in the bilateral market (the hand-entered TRQHandler removed);
  a world-price shock under `scenario="BASELINE"` is a scenario against the unshocked baseline; `surplus_cut=0` and
  `biofuel_mandate=0` read as given; the pesticide docstring corrected; a base year other than 2017 and a trajectory
  demand factor other than 1 raise an error (no consistent closure for a demand factor alone).
- **Market (K54):** non-EU supply with CAPRI's own-price p_elasSupp per region (`tools/build/build_supply_elas_nonEU.py`;
  cross-price terms REGISTERED); the crushing margin with oil and cake at producer prices (ProcMargO_); Norway's feed
  bulk price indices from CAPRI's Norwegian bulks; `market_max_iter` = the bilateral Newton rounds; the premium market
  structure, the inert FAO fallback and the unused oil-yield code removed (two data files archived).
- **Supply (K55):** where IPOPT fails the region's solve is done in the conic form (feeding inside), recorded in
  `metadata["nlp_fallback"]`; winter cover chosen in the NLP form with CAPRI's cost curve, the Farm-to-Fork requirement
  its floor, BioFix N in the residue pool and the surplus row, the catch crops' N2OCRO under the tax
  (`tools/build/build_winter_cover_option.py`); the cascade's losses bounded at zero in the NLP form, as CAPRI bounds
  v_emiLoss; with manure trade off, all manure P and K applied in the region (as N); warnings when conic-only switches
  are set in the NLP form; docstrings corrected.
- **Not applied, following CAPRI:** the Nitrates Directive minimum shares (CAPRI's Green Deal settings have NDtech off).
- **Speed (Farm-to-Fork 36 min against the 30-minute budget):** staged IPOPT tolerances added as an option
  (`CAPRIModel.nlp_staged_tol`, off: 275 s against 258 s on 40 regions). Persistent supply workers that keep each
  region's IPOPT solver between outer iterations were tried and removed: a region's problem keeps its structure from
  the third outer iteration, but the solvers of a worker's regions need about 3 GB per worker, and the run was killed
  for memory in this 8 GB container. About half of the regional solve time is building the CasADi graph (0.14-0.25 s)
  and the IPOPT solver (0.37 s) per region and outer iteration; IPOPT itself takes about 0.08 s.
- **Found:** Norway's supply regions are in the EU market and totals and Norway is in ROW too (K56; the user's
  decision: Norway as its own market region, as CAPRI, next).

## CAPRI's phosphate balance in the environmental accounts; organic area (20 October 2026)

Details: docs/P_BALANCE.md.

- **Gross phosphate balance in CAPRI's form** (reports/calc_nbalance.gms with FNUT = PHOF; capri_mod/environmental/
  p_balance.py, `EnvironmentalModule.compute_phosphorus_balance`), in P2O5 as CAPRI reports it, t P2O5 in the table:
  `p_input` (IMPORT), `p_uptake` (EXPPRD), `p_surplus` (SURTOT), filled for the first time, and `p_mineral_input`,
  `p_manure_excretion`, `p_manure_net_export`, `p_crop_residues`, `p_runoff` (RUNANI, CAPRI's N runoff share on manure
  P2O5 through the loss cascade), `p_surplus_soil` (SURSOI). Mineral P2O5 and manure applied are the NLP form's
  fertilisation block's; in the conic form, CAPRI's NUTNED_ for P summed over the crop groups with the block's data
  (equal to the block's purchases at NLP solutions). EU totals in `flatten_outputs` (`env_EU_p_*`).
- Data: `tools/build/build_p_balance.py` -> `p_balance_crop_coefs_2030.csv` (CAPRI's P2O5 retention PRET and residue output
  PCRD per ha of the model's crops) and the extracts of CAPRI's P balance items from the Green Deal 2030 reference
  and its "ini" run (`sources/capri_res/gd2030_*_pbalance.csv`).
- Check: with CAPRI's own levels the formulas give CAPRI's items (DE11, NL22, PL22, DK: EXCRET, CRESID, RUNANI,
  SURTOT, SURSOI exact or within 1e-6, EXPPRD within 0.02%). At the model's base data against CAPRI's 2030 reference
  (EU, kg P2O5/ha): excretion 27.8 / 27.6, mineral 15.6 / 15.6, residues 24.0 / 24.1, removal 53.1 / 53.4, surplus
  14.4 / 13.9; regionally the levels differ (DE11 excretion 19.3 kt against 15.7; 2017 herds against CAPRI's 2030).
- `organic_area`: the area converted by the organic target (crop area x converted share; `SupplyResult.organic_conv`,
  a one-line accessor in supply_module.py). 0 without a target: no baseline organic area in CAPRI's data.
- Open points found (docs/P_BALANCE.md): manure P2O5 does not follow the split columns; the block applies CAPRI's P
  net-export share with manure trade off; option shares that drive the cascade's housing runoff below zero (NL22's
  bulls and heifers at the NLP baseline), which CAPRI's bounds on v_emiLoss rule out. KNOWN_ISSUES K52 (l) closed.

## Documentation rewritten; interface fixes from the audit (20 October 2026)

- A README rewrite was drafted and, at the user's request, not adopted: the previous README is kept, with its stale
  counts and the sections touched by later changes corrected. The architecture and data-layer diagrams
  (`docs/architecture.svg`, `docs/data_layer.svg`) were redrawn. Superseded documents moved to `docs/archive/`. `SENSITIVITY_ANALYSIS.md` rewritten (its examples called `run()`
  arguments that do not exist).
- Fixed: the NLP calibration is kept per mitigation setting (K53); `ProjectionResult.increment` (always empty) now
  holds the % changes of the flat outputs; `flatten_outputs` adds the EU's market production and prices and the EU
  totals of the environmental accounts; `tools/run/run_tests.py` handles `pytest.mark`, `monkeypatch`, `tmp_path`; the
  N balance columns are documented in t N (they are), the run summary prints kt; requirements name CasADi/IPOPT as the
  default supply solver. Found and documented, behaviour unchanged pending a decision: KNOWN_ISSUES K52.

## Leaching and the indirect N2O of leached and run-off N; inhibitors' NO3 effects (20 October 2026)

Details: docs/N_CASCADE_SPEC.md ("Leaching"), KNOWN_ISSUES K51, README 10.2c.

- **Leaching share of the soil surplus** in CAPRI's form (LEACHN_; `capri_mod/supply/n_leaching.py`,
  `tools/build/build_n_leaching.py`): base share p_Nemidat, winter cover 0.35, nitrification inhibitors on mineral N and
  manure (NO3SLEA, NO3MLEA), low-emission application (v_ammoAppLeaAgg); tillage, buffer strips, biodiversity
  options and biochar held at CAPRI's Green Deal reference (REGISTERED). At the base, CAPRI's realised share.
- **Indirect N2O of leached and run-off N allocated to crops** (gases.gms N2OLEA) in the accounts
  (`ghg_leaching_n2o`, `leach_share`, `n_runoff_leached`); capri-mod had none before. From CAPRI's own regional items
  the formula gives CAPRI's crop N2OLEA within 6% (DE11, NL22, PL22, DK; `test_n_leaching_follows_capri`).
- **Emission tax**: mineral N carries the indirect N2O of its runoff and leaching (`SupplyModel._ef_mineral_lea`,
  both forms) at CAPRI's reference leaching share.
- **Inhibitors' NO3 effects** (NO3SLEA, NO3SRUN, NO3MLEA, NO3MRUN) from CAPRI's literature review, kept as endoLeach on
  keeps them, manure weighted as ghgMiti.gms l. 557-563 (`tools/build/build_fert_side_effects.py`).
- **DEPARTURE FROM CAPRI (the user's decision)**: CAPRI's LEACHN_ adds v_ammoAppLeaAgg, so adopting low-emission
  application lowers leaching, against CAPRI's own data (Leach -0.24 = +24%) and its runoff equation; capri-mod
  subtracts it (`n_leaching.AMMAPP_SIGN = "consistent"`; `"capri"` reproduces CAPRI).
- Tests under the NLP default: the conic-only tests pinned to the conic form, the no-op pesticide check at IPOPT's
  tolerance (1e-6) in the NLP form; the JRC121368 N-target relaxation is now keyed to the supply form (a relaxation the
  conic form found had carried over to NLP runs; the NLP form meets NL12's tiered target, as CAPRI did).
- Runs with leaching (NLP form): Farm-to-Fork r52 converged in 12 iterations (2,130 s), Green Deal 2030 r51 in 15
  (2,131 s). Leaching changes only the accounts here (no tax): every price, herd, production and adoption figure equals
  the runs without it (r48, r47). EU leaching N2O at the 2030 baseline 7.48 Mt CO2-eq (Farm-to-Fork settings) and 7.71 (Green Deal
  settings); Farm-to-Fork -27%, Green Deal -20%; GHG total -17.7% (before -17.5%; JRC121368 -14.8%) and -13.3% (before -13.1%); deviation from JRC121368
  5.77 (before 5.76). Full test suite: 120 passed.

## NLP form by default; anaerobic digestion; winter cover in the cascade; Nitrates Directive data (20 October 2026)

Details: docs/AD_SPEC.md, docs/N_CASCADE_SPEC.md, KNOWN_ISSUES K50 and K51.

- **Default supply form is CAPRI's NLP form** (`CAPRIModel.supply_form = "nlp"`; the user's decision, closer to CAPRI's
  own model). The conic form stays as `--supply-form conic`.
- **Anaerobic digestion** (`tools/build/build_ad_option.py` -> `ad_option.csv`): CAPRI's cost curve, initial and maximum
  shares and calibration (ad_data_and_cali.gms), shares as CAPRI reports them (v x L(1-G)); N effects through the
  cascade, CH4 effect 1 - v(1 - QE_AD/QE_NOC) in the manure CH4 account. Applied to dairy cows too, where CAPRI as
  coded has none (ad_data_and_cali.gms l. 588); `EnvironmentalModule.ad_dairy_ch4 = "capri"` reproduces CAPRI.
  Cattle volatile solids from CAPRI's table until the run's p_VSER is in hand (REGISTERED).
- **Winter cover in the cascade**: CAPRI's WinterCov share = the catch-crop share; 0.35 x share off the surface runoff.
- **Nitrates Directive minimum shares** built from CAPRI's nvz.gdx (`tools/build/build_nitrates_directive.py`), not applied
  (CAPRI's ini run shows no effect; a CAPRI simulation run is needed to see whether they bind).
- Results (NLP, against the runs before these changes): Green Deal 2030 r47 (r43): 15 iterations, 2,218 s; AD
  1.0 -> 2.2%; manure CH4 -7.4 (-5.9); GHG -13.2 (-13.0); sunflower price +3.0 (+5.4); other indicators within 0.5
  points. Farm-to-Fork r48 (r45): 12 iterations, 2,110 s (over the 30-minute budget); AD 1.0 -> 3.8%; manure CH4
  -17.0 (-13.6; CAPRI -12.2); GHG -17.5 (-17.1; CAPRI -14.8); deviation from JRC121368 5.76 (5.57).
- `tools/check/compare_runs.py`: adoption rows for the concrete-basin storage options and AD.

## CAPRI's N loss cascade; concrete storage options; the NLP form converges for the Green Deal (20 October 2026)

Details: docs/N_CASCADE_SPEC.md, docs/AD_SPEC.md, KNOWN_ISSUES K50 and K51, docs/NLP_PORT_DESIGN.md.

- **N loss cascade in CAPRI's form** (`capri_mod/supply/n_cascade.py`; factors `tools/build/build_n_cascade.py`): GRAZN_ to
  APPLN_, the runoff equations and GASTOTNETF_ with CAPRI's p_Nemidat built from the MITERRA CSVs. With CAPRI's own
  option shares it reproduces the per-head losses of CAPRI's Green Deal "ini" reference run to 1e-6 (712 values,
  DE11, NL22, PL22, DK; `test_n_cascade_reproduces_capri`). The ammonia options now act through it in both forms:
  the manure keeps the N of every loss they avoid (GasRunTot), the NH3 part goes to the ammonia accounts, the N2O
  by stage to manure N2O. It replaces capri-mod's NH3-only cascade, in which the manure-management options mixed
  as alternative systems.
- **endoLeach is on in capmod** (set_global_variables.gms l. 55), not off as the option data had assumed: the
  concrete basin ManStorCon, CovStorLowCon and the pigs' AirPurCovLowC are built with CAPRI's costs, initial shares
  and maxima, and LowEmHous and CovStorHigh carry the basin's cost (`build_ammonia_technologies.endo_leach`,
  `build_ammonia_tech_model.py`); 528 of 532 initial shares of the four regions within 2e-4 of CAPRI's run.
- **NLP form, Green Deal**: a relaxation of the mineral caps once needed is kept for the scenario (CAPRI sets its
  exemptions once); without it relaxed regions switched between the relaxed and strict problem every iteration and
  the run did not settle (r40). A warm start is cut at 200 IPOPT iterations, then a cold start from the same point.
  Outer-loop trace per iteration: time, IPOPT's starts, regions that moved most.
- Results (EU, % from the 2030 baseline; conic / NLP):
  - Green Deal 2030 (r44 / r43): converged in 17 / 10 iterations, 2,128 / 1,771 s; pork price +5.6 / +9.1, milk
    +10.2 / +11.9, poultry +5.7 / +10.2; pork production -5.2 / -8.3; cereals -6.1 / -4.3; mineral N -33.6 / -30.1;
    N surplus -28.3 / -26.7; GHG -11.9 / -13.0; NH3 -31.5 / -32.6 (before the cascade: -33.7 / -34.3).
  - Farm-to-Fork (r46 / r45): 11 / 12 iterations, 539 / 2,009 s; mean absolute deviation from JRC121368 4.38 / 5.57
    (unchanged); covered storage 9.1 -> 28.5 / 10.5 -> 30.9 % (CAPRI 14 -> 34; before 15 -> 41); ammonia -40.5 / -40.0
    (before -42.3 / -41.3; CAPRI -33.0).
  - Default stays conic: closer to CAPRI's published Farm-to-Fork result and four times faster there.
- Data from CAPRI: nvz.gdx (NVZ areas, slopes, soils), cost-savings ini/max (v_Miti, supplements, fertiliser
  distribution of CAPRI's calibration runs), soc_data, waterMetersPerHa, landscape_nuts2, Norway's MITERRA mirrors,
  converted to CSV (`tools/build/gdx_dump_symbol.py`, now with `--nonzero`). AD specification checked against CAPRI's run
  (docs/AD_SPEC.md); AD itself not yet in the model.

## The regional supply model in CAPRI's own NLP form (20 October 2026: option, not default)

Details: docs/NLP_PORT_DESIGN.md; KNOWN_ISSUES K50. `CAPRIModel.supply_form = "nlp"` or
`tools/run/run_f2f_2030.py --supply-form nlp`; the default stays `"conic"`.

- CAPRI's equations block by block, solved with IPOPT (CasADi): feeding (REQSE_ equalities per head, FEDUSE_,
  QUADRF_), fodder balances as equalities, NUTNED_ for N, P2O5 and K2O per crop group with the inner fertiliser model's
  first-order conditions inside, mineral purchases priced at CAPRI's unit values, endogenous manure availability
  (endoManAvail.gms), CAP greening (permGras, ecoSetAside, cropDiv), the N-surplus target with the purchases
  (e_SURTOTHa), CAPRI's mineral caps and organic area target as inner-model regulations, the ammonia, fertiliser and
  manure-inhibitor options with CAPRI's loss cascade, the emission tax (mineral N2O on the purchases, the
  inhibitor's side effects as the accounts count them). LUC transitions (CAPRI's gamma-prior model) after each
  regional solve. Data: tools/build/build_npk_balance_2030.py, build_cap_greening.py, build_luc_2030.py.
- Calibrated so the base is a first-order point (CAPRI's PMP logic): the baseline reproduces the base exactly (all
  cells within 0.1%; conic form 59%).
- Speed: the PMP quadratic's derivatives given to IPOPT directly (solver creation 0.35 s -> 0.12 s, same
  derivatives), data as CasADi parameters with solvers cached by structure within a process, IPOPT's warm start
  from the last primal-dual point. Sending workers' solvers back to the main process ran out of memory and was
  dropped.
- Farm-to-Fork (r38): converged in 12 iterations, 1,346 s; mean absolute deviation from JRC121368 5.6 (conic r37:
  4.4, identical to r27). Green Deal 2030 (r39): Finland's manure pool did not settle in 25 iterations (57 min).
  Hence the conic default. Details: docs/NLP_PORT_DESIGN.md "Scenario results".
- Fixes found on the way (the first runs, r35 and r36, deviated by 15.4): the crops' N need was their group's need
  spread by area (fallow 86 kg N/ha instead of CAPRI's 3.7; tools/build/build_npk_balance_2030.py now takes each crop's
  NITF/PHOF/POTF); the grassland split column did not move NUTNED_ and the animal split columns not ManureNPK_; the
  split columns entering after the first solve were left uncalibrated; the NLP form did not report the N-surplus and
  mineral-cap duals; a start with a regulated flow above its cap left IPOPT infeasible; the organic I/O change and
  the NLP form both removed the converted land's fertiliser cost. CAPRI's organic area target is now the inner
  model's regulations (organic_minfert_redu.gms); unmet group needs under the caps get CAPRI-style relaxations
  (duals, then caps at 1.1 x base), recorded as nlp_relaxed.

## capri-mod-proto (from Sprint 9t): the nitrogen target as a plain constraint (October 2026)

Prototype branch; 9t is kept as `capri-mod-9t.zip`. Details: docs/archive/PROTOTYPE_NI_INSIDE.md.

- CAPRI's nitrification inhibitor on applied manure (NITR_INH, N2OMAN) is a decision of the regional conic model:
  one regional share s = T / W (T manure N treated, W = the herds' manure N), T <= smax W, the N row relieved by
  sub x NMAN x T, cost S0 T + 0.5 slope T^2 / W (perspective, rotated cone) less the emission tax saved. CAPRI's own
  relation; the external rule at a given N price is kept behind `RegionalSupplyModel.ni_inside_model = False`.
- With it, nothing in the regional problem depends on the N-balance price: N-target regions are solved once per land
  step, the target is a plain constraint as in CAPRI's NLP, and its dual is the reported N price (the bracket +
  secant search `_next_nbal` serves only the switch off).
- A Clarabel solve that stalls (InsufficientProgress; IE05 under Farm-to-Fork, inhibitor at its maximum share) is
  re-solved with more static regularisation (1e-7, then 1e-6). Before, the region fell back to the problem without
  technologies, its dairy supply jumped and Ireland's milk price kept the run from converging.
- Farm-to-Fork: converged in 13 iterations, 353 s (9t: 23, 756 s); gap 4.29 (4.26), largest indicator difference
  0.4 points. Green Deal: 20 iterations, 584 s (18, 799 s), largest difference 0.8 points.
- Test: the inhibitor share decided inside equals CAPRI's first-order condition (DE21 under the emission tax).
- Test fix (also needed in 9t): the low-rent land check allowed successive runs to differ by 1e-4, the land loop's own
  stopping tolerance; after the whole suite in one process SK01 alternates 0.06606 / 0.06618 (9t identical). Now 5 x
  LAND_TOL; the swings it guards against were 0.045 / 0.09. 92 tests pass in one process (770 s).
- NLP check (`tools/nlp_check`, docs/archive/NLP_CHECK.md): captured regional problems in CAPRI's original form (feeding per
  head, CAPRI's exact ammonia loss cascade, one regional share per fertiliser technology, the inhibitor's share)
  solved with IPOPT (CasADi) from five starts. Found two bugs, both also in 9t (docs/KNOWN_ISSUES.md):
  - K1: the ammonia options' N saved was linearised as slope x (share - base share), losing the cross term of the
    manure-management and spreading options; CAPRI's N balance was violated by 8-365 t N. Now the tangent at the
    previous solve's shares (exact at a converged point).
  - K2: the options' quadratic cost lacked the sub-activity weight (w times too small; adoption too cheap in split
    activities). Fixed in the cost cone.
  After both: the conic optimum equals CAPRI's exact optimum (objective within 1e-8-6e-7, IE05 1e-5; N prices equal).
  Fertiliser shares per crop vs one regional share: same optimum (the registered departure costs nothing there). No
  local optima found. CAPRI's literal per-head feeding is hard for IPOPT (FRH0, IE05 infeasible from most starts).
- A failed conic solve now warns (region, status) instead of silently switching to the model without technologies.
- Test warnings: the expected "outer loop did NOT converge" of the deliberately short test runs is filtered; the suite
  runs without warnings.
- Runs after the fixes: Farm-to-Fork 13 iterations, 349 s, gap 4.28; Green Deal 20 iterations, 544 s.
- K3: the failed-solve warning is shown in run logs (the runner silenced all warnings) and the regions are listed in
  `meta['conic_fallbacks']`.
- K8: the emission tax on the N kept by the ammonia options priced on the cascade's tangent; NLP check under a
  50 EUR/t tax: conic = CAPRI's exact form within 1e-6.
- K11: K2's weight moved from the cone to the cost (U priced with 1 / w): written in the cone, Clarabel declared three
  Romanian regions PrimalInfeasible under the tax. Same optimum elsewhere (1e-8).
- IPOPT polish (K4): a regional solve Clarabel leaves AlmostSolved or stalled is completed by IPOPT (CasADi) on the same
  convex problem from Clarabel's point; kept only when feasible and at least as good. IE05's Farm-to-Fork solve is now
  CAPRI's exact optimum (was 1e-5-1.6e-3 short). EU indicators unchanged; Farm-to-Fork ~480 s (was 349 s). CasADi is a
  standard dependency (requirements.txt, pyproject.toml). Test: the polish returns Clarabel's optimum on a small
  problem (93 tests).
- EU agricultural outlook 2020-2030 as a check of the 2030 baseline (docs/OUTLOOK_2030_CHECK.md): annex balances in
  capri_data/validation/eu_outlook_2020_2030.csv, tools/check/compare_outlook_2030.py. It found K12: since Sprint 9p the
  model's dairy cows, heifers, bulls, calves and sheep/goats had no 2030 yield factor (CAPRI's reference reports only
  their intensity variants) and gave 2017 output per head - EU cow milk 139.6 Mt against CAPRI's 154.3. Fixed in
  tools/build/build_trajectory_capri_ref.py (components' level-weighted yields; sheep and goats' milk and meat separately,
  ProjectionModule._project_livestock) and herd aliases in tools/build/build_trajectory_model_keys.py. Baseline cow milk
  157.2 Mt (CAPRI +1.9%). Farm-to-Fork gap 4.28 -> 4.43: the milk price rises more (+32.3, CAPRI +1.5; K13).
- K14: a Clarabel solve declared infeasible (PrimalInfeasible / DualInfeasible) is re-checked with infeasibility
  tolerances 1e-12 before falling back: FI1C under the Green Deal was wrongly declared DualInfeasible (finite optimum,
  IPOPT agrees) and the run did not converge in 60 iterations. Green Deal now: 20 iterations, no fallbacks.
- K15 conditioning: the placeholder nitrate row (999999 kg N/ha x UAA) is added only with a nitrate limit, and
  activities absent from a region at base are fixed at zero (CAPRI's regional model has none). IPOPT completion calls
  per Farm-to-Fork run 63 -> 30-39, run ~420-440 s; results unchanged. Green Deal: 20 iterations, 699 s, no
  fallbacks, no IPOPT completion in the final results.
- K16: the market took the supply module's EU output for a product whenever it was positive, including solver noise.
  In a run on a subset of regions (the emission-tax test: IE04 and NO01) a product none of them grows came back as
  ~1e-15 kt after K15 and replaced the EU's base supply; the EU price ran to 1e7 and IE04's herds swung (dairy cows
  x4, suckler cows and sheep to zero). Supply below 1 kg (1e-6 kt) now counts as none. Full-EU runs unaffected (every
  such product has real EU supply).
- K13 (Farm-to-Fork milk price) diagnosed, not changed: the dairy block is CAPRI's (p_hessNQDairy reproduces p_ElasDair
  element by element; DairyNQ_ for raw milk active as in CAPRI); the market's derived demand for raw milk is about -0.2
  (tools/check/milk_shock_check.py: milk -10% -> price +55%), so JRC121368's -10% / +1.5% cannot come from CAPRI's own
  parameters. Needs CAPRI's Farm-to-Fork dairy market results. K17: the reported world raw milk price was the EU's.
- K9: CAPRI's minimum mineral share NUTMIN_ (p_minShareMinFert, fert/fertpar.gms) in the regional model, on the
  crop-need row with a base-calibrated correction; the row now carries every term that changes mineral N inside the
  conic model (ammonia options, inhibitor, fertiliser technologies, nitrate additive). K18: the inhibitor's relief on
  the mineral fertiliser cap row. K19: the grassland split's mineral N on the crop-need row (the unit balance's, as the
  accounts). Farm-to-Fork: allocation failures 8 -> 3, no region with negative mineral N; the N target cuts herds more
  (sheep -10.3%, CAPRI -9.5%; pigs -22.5%, CAPRI -14.5%; pork price +40.9%, CAPRI +43%); gap to JRC121368 4.5
  unchanged.
- K9, option 3: CAPRI's inner fertiliser distribution model (supply_model.gms, useInnerFertDistModel) inside the
  regional model. After each conic solve the inner model is checked at the solution's own totals (mineral N from
  the crop-need row, manure applied, residue pool); where it has no solution the region is solved in CAPRI's
  coupled, non-convex form with IPOPT (capri_mod/supply/capri_nlp.py: the regional problem as the conic model
  writes it, plus flows per crop group and source, NUTNED_, fertDistExcr_ and e_focFertDist), warm started from
  its previous coupled solution, two IPOPT settings per start (monotone barrier; adaptive on the scaled objective),
  1000 iterations each. The report shows the coupled allocation where the region was solved in that form, elsewhere
  the inner model's at the balance's own totals as before (the two mineral N totals differ by ~0.02%: K20).
  Applied only where the allocation exists at the calibrated base (CAPRI's base is consistent by construction):
  RO22 is flagged. Farm-to-Fork: FRI2 and IE05 coupled, allocation failures 3 -> 1 (RO22), EU indicators within
  0.3 points (FRI2 suckler cows -5%, IE05 calves -5%), 16 iterations, ~15 min. Green Deal: 30 iterations, 1792 s
  (was ~13 min), indicators as before; FRI2's coupled form not solved (KNOWN_ISSUES K9). K20 found on the way. NLP builder moved from
  tools/nlp_check into the package (the tool imports it); it now writes the crop-need row and K18 as the conic model.
- K9, CAPRI's priors (16 October 2026, later): the prior modes of the crop-group allocation are fixed once before
  the simulation, prior per ha x the group's area at the starting point (prep_sim.gms -> set_fert_priors.gms,
  UPDATE_FERTMAX_IN_STEPS off), and every flow lies within 0.001 and 1000 x its mode, as CAPRI bounds v_fertDist -
  in the coupled form, the existence check and the report. They followed the current areas, so shrinking groups
  (FRI2 pulses, rapeseed) made the first-order conditions singular: FRI2's coupled form failed at every Green Deal
  iteration, at ~8 s per failed attempt. Farm-to-Fork 891 -> 397 s, Green Deal 1792 -> 997 s, FRI2 solved; the
  indicators move by at most 0.3 points.
- K21: the manure spread over the crop groups is CAPRI's v_ManureNPK - excreted, less the losses in housing and
  storage (GASANI, RUNANI) and net exports; it was excreted after trade (49% too much in the median region; RO22
  14.7 kt against CAPRI's 0.44 kt). CAPRI's loss shares per region and animal from its 2030 reference
  (tools/build/build_manure_losses.py, which checks EXCRET - MTRADE - GASANI - RUNANI = fertDist_excr in all 268
  regions; capri_data/2017/environment/manure_housing_losses_2030.csv), plus the N the ammonia options keep. Green
  Deal: every allocation exists or is solved coupled (none open), 928 s, indicators unchanged. RO22 stays flagged
  in Farm-to-Fork, which trades no manure as JRC121368 while the priors come from a run that does.
- K21, RO22: where CAPRI's star 3.0 posterior has no crop-group allocation at the run's own base (RO22 in
  Farm-to-Fork, which trades no manure while the posterior was estimated with two thirds of RO22's manure exported),
  the priors are calibrated at that base as CAPRI calibrates them at its baseline (fert/ferttrm_years.gms blanket
  priors, posterior by the inner model, used as the simulation prior; InnerFertDist.calibrate, per manure-trade
  setting). No allocation is left open in either scenario.
- Projection layer: vineyards are carried between periods. The perennial list used CAPRI's code TWIN, which the
  model does not use (its vineyards are WINE), so vineyards were re-optimised every period; it now takes the
  supply model's PERMANENT_LAND_CROPS (one definition). No effect on single-year runs (all reported runs).
- README and capri_mod/projection: the model is comparative static per simulation year, as CAPRI; the projection
  layer is a multi-year loop carrying perennial areas along the baseline path only (it was called recursive-dynamic).
  CAPRI's own recursive-dynamic mode (RECDYN, off by default) is not implemented.
- K22: a region whose tiered N target had to be relaxed (JRC121368's 36%) starts from the relaxed target for the
  rest of the scenario instead of failing the tiered one at every iteration (NL12: ~12 failed solves per run); the
  warning says what follows.
- docs/archive/CAPRI_COMPARISON.md section 1 rewritten: CAPRI component, CAPRI behaviour, capri-mod behaviour, how to match.
- Market: Anderson acceleration of the bilateral market's steps (market_acceleration = "anderson", memory 5; the
  purpose of CAPRI's group and full-system stages): Farm-to-Fork market time 101 -> 71 s, steps per solve 23-54 ->
  15-49, results identical. A market solve that does not converge is now warned about and recorded
  (meta["market_converged"]).
- Market products: rye (RYEM) and oats (OATS) are separate markets, as in CAPRI (arm/arm_sets.gms CERE_DEF); before,
  their supply was added to the other-cereals market (OCER) and they earned OCER's price. Data rebuilt by the same
  builders with the split mapping (bilateral flows and regions, world market baseline, non-EU feed demand, EU feed
  bulks, biofuel feedstocks, feed by-products); only the OCER, RYEM and OATS rows changed. World prices from FAO_agg
  World PMRK (RYEM 156.85, OATS 144.67 EUR/t); Armington rho1 / rho2 CAPRI's (3.4 / 6.8, 2.2 / 4.4); EU tariff rows
  from CAPRI's import prices (K25); non-EU tariffs rebuilt (OCER's column changes since it no longer holds rye and
  oats). The non-EU food demand elasticity of RYEM and OATS stays at OCER's -0.2, the value they had inside OCER
  (not CAPRI's; K24, fixed below).
- feed_cereal_mix_2030.csv (weights of the feed-cereal price level in the supply models) is now written by
  tools/build/build_feed_bulks.py from CAPRI's 2030 FCER feed use per cereal; it was a hand-entered table with rye and oats
  inside OCER (and soft wheat only: wheat 39.9 -> 40.4 Mt, CAPRI's WHEA). Rice stays out (no model producer price).
- 2030 baseline against CAPRI's reference (EU27): production RYEM 9.10 Mt (CAPRI 8.99), OATS 13.12 (12.54), OCER
  14.79 (14.55); net exports RYEM -0.19 Mt (-0.19), OATS +0.85 (+0.85), OCER -5.79 (-5.80). Farm-to-Fork: EU
  price changes RYEM +7.9%, OATS +6.0%, OCER +12.1% (the joint OCER market before: +8.7%); EU indicators within 0.1
  point of the previous run (gap to CAPRI 4.51, before 4.50), 12 iterations, 391 s. Green Deal: RYEM -2.8%, OATS -3.0%, OCER +12.1% (joint
  OCER before: +1.3%); EU indicators within 0.1 point (gap 21.44, before 21.45), 29 iterations, 1024 s (928 s before,
  same iteration count). The split moves the separate cereal prices, not the EU aggregates.
  Test test_rye_and_oats_are_markets; 100 tests pass (804 s).
- K24 fixed: the cereals' food demand elasticities are CAPRI's p_ElasDem (elas_2_1717defaulta), the EU row the
  member-state median (eu_demand_elas_overrides.json; the method of the existing oil and cake entries, reproduced
  as a check), the non-EU regions the median over CAPRI's non-EU regions (armington_params.csv eta). Before: -0.2
  (OCER, CORN, PARI, RYEM, OATS), -0.205 (BARL), -0.039 (SWHE), source not recorded; now -0.47 to -0.51, wheat
  -0.22 (EU) and -0.36. tools/build/build_demand_elas_capri.py. Farm-to-Fork: cereal price index +6.5 -> +6.2% (CAPRI
  +8), every other indicator within 0.2 points, gap 4.50 -> 4.49 (14 iterations, 468 s). Green Deal: within 0.2
  points, gap 21.42 -> 21.40 (29 iterations, 988 s).
- Market products: table grapes (TAGR) and tobacco (TOBA) are markets, as in CAPRI (arm/arm_sets.gms CROPS_DEF);
  before, both were activities at the 2030 reference price. Same builders as rye and oats, with the two products
  added: CAPRI's bilateral flows and regions (2017, 2030), FAO_agg base balances, world prices (FAO_agg World PMRK:
  TAGR 1340.18, TOBA 3593.21 EUR/t), Armington rho1 / rho2 (market1_ch.gms: 3.7 / 7.4, 1.8 / 3.5), non-EU supply
  elasticities (CAPRI market regions, production-weighted), EU tariff rows from CAPRI's import prices (7.75%,
  5.8%) and non-EU tariffs. Demand: TAGR CAPRI's p_ElasDem (EU -0.49, non-EU -0.50). Tobacco has no human
  consumption in CAPRI's member states: its use is processing, priced by p_hessNQProc, which CAPRI sets
  (arm/trim_elas.gms) to an elasticity of -0.1 on a margin of 0.2 x price, i.e. -0.5 on the price; the EU row takes
  that value from CAPRI's 1730 calibration (-0.5 in all 26 member states); non-EU p_ElasDem (-0.78).
  tools/build/build_demand_elas_capri.py (renamed from build_cereal_demand_elas.py).
- 2030 baseline against CAPRI's reference (EU27): table grapes production 1.53 Mt (CAPRI 1.47), net trade -1.41 Mt
  (-1.41); tobacco 94 kt (96), net trade -333 kt (-333). Farm-to-Fork: table grapes price +7.2%, tobacco +1.5%;
  the vegetables-and-permanent-crops price index (unweighted, now with table grapes) +13.4 -> +12.6% (CAPRI +15);
  every other indicator within 0.1 point; gap 4.49 -> 4.53 (14 iterations, 451 s). Green Deal: table grapes +7.4%, tobacco +0.6%;
  vegetables-and-permanent-crops price index +12.5 -> +11.9%; every other indicator within 0.1 point; gap 21.40 ->
  21.43 (29 iterations, 1008 s). Test test_table_grapes_and_tobacco_are_markets; 101 tests pass (808 s).
- Sheep and goats: CAPRI's two activities, SHGM (milk) and SHGF (fattening), replace the model's SHGP
  (tools/build/build_shg_split.py, following the pig split). The meat market's model code SHGM, which collided with CAPRI's
  milk activity, is now CAPRI's SGMT (data files rebuilt; checked rename-only). Herds: the census SHGO split at
  CAPRI's 2017 HERD shares per region group (EU 60.0 and 19.0 million head; CAPRI's national HERD sums 60.0, 19.0).
  Every per-head table rebuilt by its builder with CAPRI's activities one to one; each builder was first checked to
  reproduce the current files with the old mapping. Yields, per-head costs and the producer price of the two from
  CAPRI's YILD, TOIN and CAPREG prices. Code: activity lists, ration rules (CAPRI's fibre-rich feed factors 0.8 and
  0.5 instead of their mean, 0.65), PMP elasticity product (SHGM: raw milk; SHGF: sheep and goat meat), price map,
  projection (SHGM's milk at its own CAPRI yield factor, its meat at SHGF's). CAPRI books no market revenue for milk
  sheep in Denmark, the Netherlands, Sweden and parts of Finland (no milk): GAMS reads the absent item as 0, so their
  revenue is total output (TOOU) with no market part; before, the missing value turned the margin into NaN.
  K26 fixed on the way (sheep milk value counted twice in the 2030 price projection).
- Results: base anchors unchanged. Farm-to-Fork 2030: milk sheep -17.3%, fattening +6.2% (SHGP before -10.8%; CAPRI
  sheep and goats -9.5%); milk price +33.2 -> +37.2%; gap 4.53 -> 4.82 (12 iterations, 402 s). Green Deal: milk sheep
  -51.6%, fattening -8.3%, sheep and goats -35.8 -> -41.2%; gap 21.43 -> 21.46 (29 iterations, 914 s). The Farm-to-Fork
  changes come mostly from the Dutch N-target regions (K27): fattening sheep expand far beyond their calibration
  there, EU sheep meat production rises 26% and its price falls 16.6%. This is open and not a defect of the split;
  the same mechanism moved SHGP before (NL32 x10).
- K27 fixed: CAPRI's bounds on endogenous activity levels in every regional model (supply/set_supply_bounds.gms:
  0.1 to max(10 x, + 100) the simulation's data level; set-aside and fixed activities exempt), which the model did
  not have: under Farm-to-Fork 923 region-activities fell below a tenth of their level and 13 rose above the upper
  bound, among them Dutch fattening sheep (NL12 10 -> 2,923 thousand head, its dairy cows to 0). NL12 and NL32 now
  prove infeasible at the tiered N target and take JRC121368's 36% relaxation. And CAPRI's lambs as a young-animal
  balance (SHGM produces YLAM; SHGF and SHGM's replacement use ILAM), missing since the sheep split. Farm-to-Fork:
  gap 4.82 -> 4.54 (14 iterations, 488 s); sheep and goats -9.5% (CAPRI -9.5%); EU sheep meat +2%, price -1.7%
  (before -16.6%); milk price +37.2 -> +34.8%. Green Deal: gap 21.46 -> 21.90 (30 iterations, 866 s): sheep and goats
  -41.2 -> -38.4%, meat prices 2-3 points higher (beef +50.2%, pork +124.6%, poultry +110.7%). Tests test_capri_activity_bounds,
  test_lamb_balance_links_sheep_activities; 103 tests pass (819 s).
- K27, bound units: CAPRI's additive 100 in the activity bounds is in its LEVL units; it is now converted to the
  model's herd units per region and animal (tools/build/build_capri_level_ratio.py, capri_level_ratio.csv: model herd per
  CAPRI LEVL in 2017; fattening sheep about 0.5, bulls 0.35, heifers 0.19, poultry 253-1,000), replacing a scaling
  of poultry only. Farm-to-Fork gap 4.54 (unchanged), sheep and goats -9.5%, sheep meat price -1.0%; Green Deal no
  indicator moves by more than 0.05. The Dutch corner solutions that remain are K29 (open).
- K28 fixed: tools/build/build_trajectory_capri_ref.py kept CAPRI's calves aggregate CACR out of its extract, so a rebuild
  changed 77 calves' yield factors (now kept: extract and trajectory equal the stored ones exactly);
  capri_cap_premium_2030.csv rebuilt by tools/build/build_price_trajectory_2030.py (the file was an older output: 192
  regions, CAPRI's codes only; the new one is identical on every old cell and adds 56 regions and WINE, COTT, OFIB,
  OFOD, SETA: 1,515 more 2030 premium cells; scenario changes move by less than 0.05 points). The fodder trajectory
  reproduces exactly on a clean rebuild.
- Table olives: CAPRI's TABO is an activity and a market product of its own (arm/arm_sets.gms), apart from olives for
  oil (OLIV, sold as olive oil OLIO). The model pooled both in OLIV (5,010 kha), with yield, cost and price of the
  pool, and sold the pool as olive oil through the oil yield of olives for oil only. tools/build_tabo_split.py:
  areas and nutrient needs from tools/build/build_capri_base.py with OLIV and TABO mapped one to one (on copies; only the
  two columns taken over; OLIV + TABO equal the old area in every member state, Croatia's placed 0.96 kha
  differently between HR03 and HR04), yields, costs, premiums and prices from tools/build/build_crop_economics_2017.py
  (first checked to reproduce the current files). EU 2017: OLIV 4,703 kha, TABO 307 kha (CAPRI 2030 reference
  306 kha); TABO median yield 2.38 t/ha, cost 8,132 EUR/ha, price 3,267 EUR/t; the olive-for-oil price median 772
  -> 545 EUR/t (no longer mixed with table olives). Where CAPRI has no table olives in the member state (161
  regions) TABO's yield and cost are 0 (GAMS reads the absent item as 0; NaN stopped the re-solve).
  Market data by the same builders as table grapes: bilateral flows and regions, FAO_agg base balance, world price
  (World PMRK 989.95 EUR/t), Armington rho1 / rho2 4.1 / 8.1 (market1_ch.gms), non-EU supply elasticity, EU tariff
  row from CAPRI's import prices (7.2%), non-EU tariffs, demand p_ElasDem (EU -0.50, non-EU -0.50). Every builder's
  other rows and columns are unchanged. 2030 trajectories: CAPRI's 2030 unit value of TABO added to the extract
  (tools/build/extract_capri_marginal_terms.py, rerun on res_2_1730greendeal_refpol_endotech_all_ini; every other value
  identical), TABO's price ratio and 2030 premium; capri_ref_2030.json gains TABO's level and yield factors (EU
  1.00 and 1.02; nothing else changed). Code: crop and market lists, permanent land crops, yield-gap group, residue
  and land-use lists, fertiliser groups, price map; the OLIV/TABO pooling in the supply and environment modules
  removed. Supply elasticity of TABO: the EU-wide value of OLIV, 0.197 (K30).
- Results: base anchors unchanged (olive base fidelity 0.15%). 2030 baseline against CAPRI's reference (EU27): olives
  for oil 4,899 kha (CAPRI 4,878; the pool before: 5,220, +7.0%), olive oil production 2,319 kt (2,328; before
  +7.2%), table olives 308 kha (306), production 976 kt (971), domestic use 895 kt (891). Table olives' market price
  is 66% below CAPRI's producer unit value (1,111 against 3,280 EUR/t), as for olive oil (-59%): the market level
  follows CAPRI's World PMRK (990 EUR/t), a reporting difference described in docs/BASELINE_REPRODUCTION.md.
  Farm-to-Fork: olive oil price +15.0 -> +13.2%, table olives +13.1%; every EU indicator within 0.1 point; gap
  4.54 -> 4.55 (14 iterations; 732 s, run in parallel with the Green Deal one). Green Deal: olive oil +4.4 -> +0.6%,
  table olives +15.7%; pork and poultry prices 0.8 and 0.6 points lower, the rest within 0.2; gap 21.90 -> 21.79
  (29 iterations; 1,435 s in parallel). Test test_table_olives_are_a_market_of_their_own; 104 tests pass (900 s).
- Found on the way: min_share_mineral_fert.csv had tobacco under table olives' code with VEGPERM's 0.5 (row
  'TOBA,TABO'); now TABO 0.5 (VEGPERM) and TOBA 0.4 (CAPRI's default, fert/fertpar.gms). crop_cost_shares.csv gains
  TABO (other inputs and fertiliser shares reproduce CAPRI's regional res_17 the way the existing rows do; plant
  protection see K31). tools/build/build_feed_bulks.py lacked table grapes (and table olives) in its product maps: no
  effect, CAPRI books no feed use of either (output files unchanged). captrd_2030.json (the alternative CAPTRD
  trajectory, not the default) re-keyed by tools/build/build_trajectory_model_keys.py: it still carried the retired
  SHGP/SHGO keys and lacked the herd aliases added for K12 (BCOW, HFRS, CALV, LAYS, BROI); CAPRI-keyed entries
  unchanged.
- K31 fixed: crop_cost_shares.csv (EU-wide input-cost shares, the fallback where CAPRI has no regional cost for a
  crop) is now written by tools/build/build_crop_cost_shares.py from CAPRI's 2017 results; it had no builder. Plant
  protection: olives for oil 0.249 -> 0.422, citrus 0.112 -> 0.126, grass 0.031 -> 0 (no plant protection on grass
  in CAPRI); every other value within 0.01 (the cotton row, CAPRI's TEXT over all member states, reproduces; it is
  the textile crops' row since the merge below). Flowers, nurseries, other marketable and other industrial crops gain rows. Base anchors
  unchanged; scenario runs at the end of the batch.
- Textile crops: CAPRI's one activity TEXT (cotton in Greece, Spain and Bulgaria; flax and hemp elsewhere) with its
  own market product (arm/arm_sets.gms CROPS_DEF) replaces the model's split of the same CAPRI data by country into
  cotton (COTT) and other fibre crops (OFIB), which had no CAPRI basis (tools/build_text_merge.py; areas unchanged,
  534.7 kha, each region held one or the other). Through the split, other fibre crops had no plant-protection cost
  row (the builder took cotton only; 144 kha on the EU-wide fallback share) and cotton found no fertiliser
  distribution prior (the priors were filed under OFIB). Regional data by the builders with TEXT one to one:
  areas, nutrient needs (nutrients_regional.csv gains TEXT), yields, costs, premiums, prices, plant-protection and
  input costs, fertiliser priors (rename only), crop cost shares. EU fallback rows from CAPRI's 2017 member-state
  data (production- or area-weighted): price 464.01 EUR/t (the file had cotton 43.6 and other fibre 200.0, source
  not recorded), mineral N/P/K 20.5 / 36.3 / 62.7 kg/ha (before 100/50/80 and 60/30/50); minimum mineral share 0.4
  (CAPRI's default, as before). Market: bilateral flows and regions, FAO_agg base balance (world 24,427 kt, EU 444
  kt), world price (World PMRK 1,261.81 EUR/t), Armington rho1 / rho2 8.2 / 16.5 (market1_ch.gms), EU tariff row
  from CAPRI's import prices (0.0%), non-EU tariffs. Demand: textile crops have processing use only in CAPRI;
  p_hessNQProc follows CAPRI's rule for other processing (arm/trim_elas.gms, "assume elasticity of 0.5": -0.5 on a
  margin of 0.2 x price), i.e. -2.5 in every region with textile processing (EU and non-EU; no p_ElasDem exists).
  Supply elasticity: CAPRI's per-member-state value (capri_own_price_elasticities.csv) weighted by textile area,
  0.394 (before cotton 0.20, other fibre 0.15, unsourced). Trajectories: textile premiums and the price map keyed
  by TEXT; the retired model keys (COTT, OFIB, and SHGP/SHGO left in entries whose model and CAPRI keys coincide)
  are dropped by tools/build/build_trajectory_model_keys.py; CAPRI-keyed entries unchanged.
- Results: base anchors unchanged. 2030 baseline against CAPRI's reference (EU27): textile area 555 kha (CAPRI 551),
  production 1,372 kt (1,353), domestic use 1,030 kt (1,011); the market price level is CAPRI's World PMRK (1,262
  EUR/t) against an EU producer unit value of 620 (the reporting difference of docs/BASELINE_REPRODUCTION.md).
  Farm-to-Fork: textile price -6.2%; sheep and goats -9.3 -> -10.1% (CAPRI -9.5), the IPOPT-polished regions now
  include NL11, NL13 and IE05 (K29's corner regions), every other indicator within 0.3 point; gap 4.55 -> 4.57 (12
  iterations, 427 s). Test test_textile_crops_are_one_activity_and_market.
- The environmental land-use indicators (arable land, permanent crops, grassland) follow CAPRI's aggregates
  (sets.gms landUse_TO_landUseAgg: ARAC, FRUN, GRAS): tobacco and textile crops were counted as permanent crops,
  silage maize and other fodder as grassland, nurseries in none of the three. Reporting only; total UAA unchanged.
- Palm oil (PLMO) and other vegetable oils (OTHO): CAPRI market products (arm/arm_sets.gms CROPS_DEF) without a
  supply-model activity, now markets. Data by the same builders: bilateral flows and regions, FAO_agg base balances
  (world 73,091 and 34,685 kt; EU production 105 and 2,575 kt), world prices (World PMRK 505.12 and 1,262.12 EUR/t),
  Armington rho1 / rho2 (palm oil 5.3 / 10.6, market1_ch.gms; other oils CAPRI's default 8 / 10, arm/market1.gms),
  non-EU supply elasticities (CAPRI market regions, production-weighted: 0.56, 0.39), EU tariff rows from CAPRI's import
  prices (5.5%, 5.9%), non-EU tariffs, demand p_ElasDem (EU -1.39, -1.28; non-EU -1.25, -1.12), the method of the
  other oils. Palm oil as a biodiesel feedstock is now priced by its market (tools/build/build_biofuel_market.py; before
  held at the 2030 reference price); the EU's biodiesel share of palm oil use is 28.6%.
  EU supply of other vegetable oils: CAPRI's market supply function (per member state PROD in data_market; own-price
  p_elasSupp, EU median 0.977), responding to the EU price against base (MarketModule.EU_MARKET_SUPPLY). The market's
  anticipation of the supply models' response (EU supply relative to the price they last saw) would hold a product
  without a supply model at its base at convergence. Palm oil has no EU supply in CAPRI's market model; FAO_agg's
  105 kt (Belgian refining) stay at base.
- Results (end of batch, textile crops and oils together; base anchors unchanged). 2030 baseline against CAPRI's
  reference: other vegetable oils production 2,575 kt (CAPRI 2,598), palm oil EU use 7,672 kt (7,567). The EU use of
  other vegetable oils, 4,086 kt, is CAPRI's bilateral 2030 market (EU own supply 2,000 + imports 2,108 = 4,108);
  the reference balance file reports 5,707 summed over member states, a difference not traced. Farm-to-Fork: palm oil
  +0.6%, other vegetable oils 0.0% (no shock reaches them: no feedstock use, no supply-model link; CAPRI links the
  oils through cross-price demand terms the model does not have, docs/archive/CAPRI_COMPARISON.md), rapeseed oil +3.1%;
  every EU indicator within 0.1 point of the textile run; gap 4.57 (12 iterations, 698 s, run in parallel with the
  Green Deal one). Green Deal against the run before the textile and oil changes: pork and poultry prices +2.3
  points, beef +0.4, milk +0.6, other indicators within 0.4; gap 21.79 -> 22.13 (30 iterations, 1,203 s); the two
  changes were not run separately in this scenario, so the shift is not attributed between them.
  Test test_palm_and_other_vegetable_oils_are_markets.
- K30 fixed: the crops neither regional CAPRI elasticity source covers (permanent crops, vegetables, tobacco, textile
  crops, table olives) take CAPRI's calibrated own-price supply elasticity of their member state
  (capri_own_price_elasticities.csv, read by no module before) instead of one EU-wide hand-entered value: 1,803
  region-crop cells. The hand-entered values matched CAPRI except tobacco (0.213; CAPRI 0.44 in every member state).
- K32 fixed: the PMP elasticity source reached model regions through the NUTS crosswalk alone (140 of 248); it now
  maps through the shared region map and falls back to the member state's national row, and CAPRI's fodder on arable
  land (OFAR) reaches the model's other fodder (OFOD; before 0.12 everywhere, CAPRI median 1.05). Grown arable area on
  literature elasticities 14.1 -> 1.1 Mha; all grown area 95.8 -> 69.6 Mha (grass 51.6 Mha and set-aside 8.1 Mha have
  no CAPRI elasticity in either source). Base anchors unchanged (base fidelity 0.24 -> 0.29%).
- producer_prices.csv (the EU-wide crop price, a fallback where a member state has no CAPRI price): crop rows
  rewritten as CAPRI's production-weighted EU price by tools/build/build_eu_producer_prices.py; they were of unrecorded source
  (other vegetables 30.8 EUR/t -> 509.1, tomatoes 33.5 -> 394.5, other fruit 24.4 -> 889.2, tobacco 43.8 -> 3,003.4,
  wine 95.5 -> 1,430.1; the textile row, set from member-state data, reproduces at 464.01); rice and table olives
  gain rows (other marketable and industrial crops, nurseries and flowers get none: CAPRI carries them as values). Base anchors unchanged (regions use CAPRI's regional or national prices).
- nutrient_coefs.csv: the retired SHGP row removed and a row name with stray bytes restored to OANI (K33).
- K25 explained, no change: CAPRI's bilateral rows carry the EU's specific duty on rye (TsAppl 94 EUR/t) for Russia
  and others, Ukraine enters without it; the 33.8% is that averaged over origins.
- Results of K30, K32 and K34 together (base anchors unchanged, base fidelity 0.29%): Farm-to-Fork gap 4.57 -> 4.54
  (12 iterations, 612 s, run in parallel with the Green Deal one): beef price +15.9 -> +17.1% (CAPRI +24), pork +38.9
  -> +36.2% (+43), poultry +26.0 -> +24.9% (+18), oilseed prices +15.0 -> +14.3% (+11), oilseed production -14.4 ->
  -13.2% (-15.5), beef animals -15.7 -> -17.0% (-18), sheep and goats -10.1 -> -11.4% (-9.5); others within 0.7.
  Green Deal gap 22.14 -> 20.79 (28 iterations, 1,141 s): pork price +126.2 -> +110.2% (CAPRI +43), poultry +112.3
  -> +99.2% (+18), beef +50.5 -> +53.2% (+24), oilseed production -12.2 -> -9.8% (-15.5), cereal price -0.9 -> -0.4%
  (+8). The three fixes were not run separately, so the shifts are not attributed between them.
- Tests: the 13 tests over 30 s (full-EU or multi-solve; 642 of the suite's 918 s) carry a `slow` marker (pyproject.toml);
  per step `pytest -m "not slow"` runs the other 94, the batch-end run takes all. No parallel test runs.
  test_elasticity_provenance_is_complete accepts the CAPRI_COUNTRY label (K30); the projection-calibration test bounds
  the fodder crops at 5% instead of 1.5% (they are not calibrated: the fodder balances hold them; IE04 silage maize
  -2.9% with CAPRI's fodder elasticities). New: test_supply_elasticities_reach_every_region_from_capri. K36 registered
  (baseline drift where projected fodder and herds' fodder use disagree).
- K36 fixed: the fodder balance rows are exact at the baseline in both directions. They were exact only when the herds'
  fodder use exceeded the fodder output (rhs = max(0, gap)); with use below output (projected 2030 data of FI1D,
  ITF4/5, ITG1, ITI1, LU00 ...) the band forced the fodder area down to the use, and the land went to cereals (FI1D
  barley 43 against a projected 33 kha). The baseline calibration now stops per region instead of stopping for all
  regions when the worst one stalls. FI1D, ITF5, ITG1, LU00 on their own: cereals within 0.3% of their projected
  levels. Base anchors unchanged (the 2017 base balances hold exactly). Full EU 2030 baseline: region-activities more
  than 5% off their projected level 61 -> 1 (fodder included; RO42 soybeans 5.9%), more than 1.5% 218 -> 4; EU
  aggregates against CAPRI's reference barely move (activity median 1.1 -> 1.0%, production 1.2 -> 1.1%).
  Farm-to-Fork gap 4.54 -> 4.58 (12 iterations, 733 s in parallel): cereal price +6.4 -> +7.1% (CAPRI +8), milk
  +34.3 -> +35.5% (+1.5), beef animals -17.0 -> -18.1% (-18), sheep and goats -11.4 -> -12.9% (-9.5), enteric CH4
  -14.4 -> -15.3% (-14.6). Green Deal gap 20.79 -> 19.99 (29 iterations, 1,263 s): pork price +110.2 -> +93.2%
  (+43), poultry +99.2 -> +84.5% (+18), beef +53.2 -> +61.3% (+24), beef animals -41.8 -> -45.7% (-18).
- CAPRI's market supply functions measured on the supply models (supply/calibrate_supply.gms,
  arm/simu_calibration_to_supply.gms), as an option (`market_supply_nq`, run_f2f_2030.py --market-nq; off by
  default): at the converged baseline each product's price is raised by 1% in every regional model (35 products), the
  member states' responses form the Hessian of the market's linear supply (own- and cross-price, feed columns), cached
  on disk (.cache/market_supply_hessian, about 9 min to build); in the market the EU supply of the supply models'
  products follows it through their latest output at the prices they saw. Every diagonal positive; EU own-price
  responses plausible (milk 0.54, wheat 1.4 relative to output). Tested on Farm-to-Fork against the same run without it:
  13 outer iterations against 12, 493 s against 432 s, and results moved within the outer loop's tolerance (beef price
  +17.6 -> +19.4%, beef production -15.4 -> -16.5%, the rest within 0.5; gap 4.58 -> 4.48). It does not speed the loop
  and, as in CAPRI, the equilibrium is the supply models'; kept off.
- CAPRI's food demand (step 2 of docs/archive/MARKET_STRUCTURE_PLAN.md): human consumption from CAPRI's Generalised Leontief
  system per behavioural region (arm/market_model.gms:826-916), with its cross-price and income terms, on by default
  (`food_demand_gl`). tools/build/build_gl_demand.py extracts p_pdGL, p_pbGL and the calibration point for 80 regions
  (gl_demand_*.csv; CAPRI's human consumption reproduced to 1e-7). Consumer prices move additively with the domestic
  price (Cpri_); the GL applies to CAPRI's human-consumption share of each region's use, the other uses keep their
  functions. The commitments are re-fitted to the model's base as CAPRI's trim_gl_commits.gms does
  (`gl_refit_commitments`, least-squares change of d, exact). Checks: elasticities = CAPRI's p_ElasDem (DE) to 5e-6,
  homogeneity 1e-15, demand unchanged at base. Farm-to-Fork gap 4.58 -> 4.22 (17 iterations, 565 s): beef price
  +17.6 -> +23.3% (CAPRI +24), pork +35.0 -> +40.7% (+43), vegetables and permanent crops +12.4 -> +15.7% (+15),
  poultry +24.3 -> +29.4% (+18), milk +35.5 -> +41.1% (+1.5). Green Deal does not converge (K37). New test:
  test_food_demand_is_capris_generalised_leontief. run_f2f_2030.py --no-gl-demand for the earlier demand.
- CAPRI's two EU trade blocks (step 3), as an option (`MarketModule.eu_blocks`, run_f2f_2030.py --eu-blocks): EU_WEST
  and EU_EAST (gams/aggregation/defaultA.agg), each a region of the bilateral market with CAPRI's West-East flows
  (tools/build/build_bilateral_market.py --eu-blocks), the member states inside: supply from their models, GL demand, feed
  bulks, dairy blocks and biofuel feedstocks per member state at their block's prices; the EU's quotas filled by both
  blocks; the supply models of each member state see their block's prices. EU-level data without member-state detail
  are split with CAPRI's 2030 member-state balance (tools/build/build_eu_ms_balance.py, eu_ms_balance_2030.csv). An EU27
  row in the market results reports the EU (sums; production-weighted prices). Base residual 1.6e-9; the one-region
  run is unchanged. Farm-to-Fork: 13 iterations, 467 s, gap 4.22 -> 4.65 (beef price +27.6%: West +29.1, East +11.2;
  poultry +36.2%: West +43.9, East +13.6). Green Deal: unconverged as without the blocks (K37), gap 22.98 -> 22.17.
  Registered: Norway's supply models feed EU_WEST (they fed the one-region EU); young animals clear EU-wide; the market
  supply Hessian is not available with the blocks. New test: test_eu_trade_blocks_data_and_split.
- K37 registered: Green Deal unconverged with the GL demand (young-animal prices at capri-mod's bound of 5 x base).
- bilateral.py: tariff-rate quotas and tariff changes act on one importer row or on the rows of the EU trade blocks.
- Batch of 19 October 2026 (K37, step 3 leftovers, processing, the last market products):
  - K37 fixed: young-animal prices bounded as CAPRI's (+-10 x level, negative allowed; set_start_val.gms,
    widen_bounds.gms) instead of 0.2 and 5 x base; Newton step limited to 30% of the current or the base price; young
    animals clear per market as CAPRI's yaniMarket_ (the EU, or each trade block). Green Deal converges.
  - CAPRI's processing functions (arm/market_model.gms ProcNQ_; tools/build/build_processing_nq.py, processing_nq_*.csv):
    oilseed crushing linear in the crushing margins with CAPRI's Hessian (cross terms among rapeseed, sunflower,
    soybeans), the processing part of the other products' use linear in their prices (cross terms among the
    vegetable oils), replacing the own-margin crushing elasticity and the own-price response of processing
    (`processing_nq`).
  - Fish (FFIS, SFIS, OAQU) and coffee, tea, cocoa (COFF, TEAS, COCO) are markets (58 market commodities): bilateral
    flows, world prices (CAPRI's FAO_agg World PMRK; the three fish share CAPRI's 2,617 EUR/t), Armington and supply
    elasticities, tariffs, demand elasticities by the same builders; GL food demand (their prices were held fixed);
    fish fed in CAPRI's FPRO bulk (other vegetable oils too, which had no feed mapping); EU fish supply from CAPRI's
    market supply functions (EU_MARKET_SUPPLY, p_elasSupp EU medians 0.95-0.98). Every earlier row of the rebuilt
    files unchanged (checked).
  - Legacy world base retired: MarketModule._calibrate_baseline takes production and use from CAPRI's bilateral
    market data of the market year (raw milk: CAPRI's FAO_agg balance), not from hard-coded world totals with fixed
    regional shares.
  - Results, one EU region: Farm-to-Fork gap 4.22 -> 4.44 (16 iterations, 501 s): vegetables and permanent crops
    price +15.7 -> +13.4% (CAPRI +15), pork +40.7 -> +38.7% (+43), cereals +7.9 -> +7.3% (+8), other indicators
    within 0.6. Green Deal converged in 30 iterations (997 s), gap 22.98 -> 22.48: pork price +112.2 -> +104.4%,
    poultry +103.7 -> +99.8%, milk +85.1 -> +81.6%, vegetables and permanent crops +16.2 -> +14.0%. Two trade blocks:
    Farm-to-Fork gap 4.91 (17 iterations, 552 s), Green Deal converged in 42 iterations (1,325 s), gap 22.13.
  - K13 (milk price) re-measured with tools/check/milk_shock_check.py: EU raw milk delivered -5% / -10%, all else at the
    baseline: milk price +31.9% / +67.7% (October: +26% / +55%), butter +38.8%, cheese +23.8% at -10%. CAPRI's GL
    makes the market's derived demand for raw milk even less elastic (consumer prices move additively with the
    market price); CAPRI's +1.5% under -10% milk is further from what star 3.0's coefficients give. Still open,
    waiting for CAPRI's Farm-to-Fork dairy market results.
  - Tests: test_fish_and_tropical_products_are_markets_and_processing_is_capris; 110 pass. One test's market solve
    on a region subset stopped 2.6e-7 short of the 1e-7 tolerance (SOYO, warned).
- Green Deal settings and the pesticide rule (19 October 2026, K38):
  - `greendeal_2030_scenario()` (capri_mod/policy/greendeal.py; `run_f2f_2030.py --scenario greendeal2030`): CAPRI's
    2030 settings from Witzke's production batch, lnds8 org18 pest20 mine13crp surp30, manure trade on;
    GREENDEAL_2030_TARGETS, GREENDEAL_2040_TARGETS. `--targets` reads mineRedu as CAPRI's string (e.g. 13crp).
  - `PolicyScenario.pesticide_rule`: `star3` (star 3.0 pesticides.gms -> conventional_io.gms with yield 'off': no
    yield loss) for the Green Deal group, `jrc121368` (10% yield loss at a 50% cut) for Farm-to-Fork as the report;
    `run_f2f_2030.py --pesticide-rule`. Scenario names print 00 for zero settings as CAPRI's.
  - Runs (one EU region): end-point targets with JRC121368's rule (r22) / with star 3.0's rule (r23_gd_star3pest) /
    CAPRI's 2030 settings (r23_gd2030): pork price +104.4 / +62.8 / +6.2%, milk +81.6 / +64.8 / +10.9%, beef
    +81.6 / +66.2 / +7.9%, cereals production -14.2 / -6.2 / -5.7%, EU N surplus -46.2 / -46.5 / -27.9%, GHG -32.2 /
    -29.6 / -12.2%. Most of the earlier Green Deal livestock price rise came from the settings. No CAPRI result for
    these settings is at hand.
  - Test: test_greendeal_2030_settings_and_pesticide_rule.
- The audit's model concerns (19 October 2026, K39-K48):
  - Oil processing: the audit compared the oils' processing Hessian with p_ElasDem (-0.72) instead of p_ElasProc
    (-1.88, what the Hessian gives): no mismatch. Found instead: CAPRI's ProcNQ_ divides by the 2030 INPE price
    (1.019^13 = 1.2772), the model by 1 (K39, fixed); with it the crushing elasticities equal p_ElasProc exactly.
  - Minimum mineral share: CAPRI has NUTMIN_ only without the inner fertiliser model, its default; the model had both
    (K40, fixed: as CAPRI by default, `--nutmin on` forces it). Its base allocation check ran under the Green Deal's
    mineral caps and called 11 regions data failures (K41, fixed); the coupled form now solves in more regions and
    fails in four to five (IPOPT iteration limit), retried every fourth iteration after two failures.
  - Rations: no ration is chosen outside the supply models any more (K42); the fodder balance's base gap is the
    base ration's, not the current one's (K46, found by decomposing this batch; it moved the cattle chain most).
  - Hard-coded values: non-EU feed functions rebuilt from CAPRI's 2030 calibration for every trade region (K43:
    world use on the generic own-price response 7.0% -> 1.3%); the inert Engel income term and the invented
    fallbacks (200 EUR/t, 100 kt, -0.25) removed (K44).
  - Young animals: checked against CAPRI's own market run without voluntary coupled support (tools/run/run_vcs_2030.py
    now compares them): CAPRI's calves move twelve times its beef price; the model's calves +15.0% (CAPRI +26.3%),
    lambs +17.0% (+10.7%), replacement cows -14.5% (-0.2%) (K48). The cattle chain's equilibrium shifts by several
    points with changes outside it (K47, open). Egypt's oilseed rows (K45, open).
  - Runs (one EU region; r27): Farm-to-Fork 11 iterations, 791 s, gap 4.44 -> 4.38 (cereal price +9.8%, beef +20.3%,
    pork +33.1%, poultry +25.3%, milk +37.5%; sheep and goats -6.8%). Green Deal end-point targets 25 iterations,
    1,298 s: beef price +41.7%, pork +39.0%, milk +46.7% (r23 star 3.0 pesticide rule: +66.2 / +62.8 / +64.8).
    Green Deal 2030 17 iterations, 3,546 s (other jobs on the 2 cores), pork price +5.6%, milk +10.5%, EU N surplus
    -28.0%. Run time then cut (K41): measured alone 2,539 s -> 1,692 s (16 iterations; the coupled fertiliser solves
    try what solved the region last first, the warm start with the adaptive barrier, the inner model's iterate before
    the generic start; a region failing twice is retried every fourth iteration); EU indicators within 0.15 points.
  - Tests: test_processing_inpe_and_nonEU_feed_are_capris_2030, test_rations_are_chosen_only_inside_the_supply_models;
    test_min_mineral_share_floor_follows_capri checks CAPRI's switch rule.
- Diagnosis of the crop-group allocation failures (20 October 2026, K49): tools/check/diagnose_fert_dist.py and the
  supply module's dump (env CAPRI_FD_DUMP, off by default); IPOPT's per-call log (env CAPRI_FD_LOG). The failures
  are not the solver: at the conic solution no allocation exists under CAPRI's constraints (mineral N above the sum
  of the per-group Green Deal caps; mineral N <= 0 in PT30). Next: the regional model in CAPRI's own NLP form.
- Package size: the 30 MB limit was lifted (19 October 2026); the zip carries every file again, including
  capri_data/validation/greendeal_2030/capri_marginal_terms_max_2030.csv.xz and
  capri_data/sources/capri_star/p_elasSupp_own_price.txt.xz (only __pycache__ and .pytest_cache are left out).
- tools/check/compare_runs.py: the cereal price index now includes rye, oats and other cereals (value-weighted, as
  before for wheat, barley and maize); the vegetables-and-permanent-crops index includes table grapes once they have a
  market. Indicators of earlier runs change accordingly (Farm-to-Fork cereal price +6.2 -> +6.5% for the run before K24).
- The same fixes, without the prototype's model change, are tagged 9t.1 (capri-mod-9t1.zip). Comparison of 9t, 9t.1
  and the prototype in three scenarios: docs/archive/COMPARISON_9t1_PROTO.md.

## Sprint 9t: one parameter file; land supply of combined CAPRI regions (October 2026)

- **`capri_data/shared/model_parameters.csv`** holds every constant the economics and accounts rest on (55 rows:
  CAPRI's parameters, IPCC factors as CAPRI uses them, JRC121368's assumptions, the Nitrates Directive limit, two
  literature values for the nitrate-limit option, the outer loop's damping and the land-rent rule as model settings),
  each with unit, kind and source; `capri_mod/params.py` reads it. Numerical tolerances stay in code. A test keeps
  file and code in step (no row unused, no parameter missing). Orphans removed on the way (an unused Nitrates
  Directive constant, an unused nitrate CH4 factor, an unused organic-gap share). Results identical: a 6-region
  Farm-to-Fork and carbon-tax run compared value for value before and after.
- **Land supply of combined CAPRI regions** (`tools/build/build_land_market.py`): the land owners of several CAPRI regions
  respond each to the same rents, so their combined supply is the sum of their responses - curvature
  (sum Q_c^-1)^-1, not the area-weighted average of the matrices, which overstated it (FI1D about twice). Ireland's
  NUTS-2016 regions take their own shares of the NUTS-2013 regions (IE04 = 65.4% of IE01, IE05 = 86.2% of IE02, IE06
  the rest of both) instead of one pooled matrix, which had spread IE01's flexible land onto IE05.
- With them, IE05's nitrogen-balance price had two branches (the balance slack from ~10 EUR/kg N up, ~335 when only
  herds can still cut it) and the search, reset each outer iteration, did not always close its bracket in 8 solves:
  the run alternated between the branches and stopped unconverged at 25 iterations. 16 solves per region and
  iteration close it (NBAL_INNER_MAX); converged in 23 iterations, 756 s.
- Farm-to-Fork: indicators within 0.1 point, gap 4.26 (4.27); Irish grassland +22 and +50 kha in IE04 and IE06.
  Green Deal: within 0.5 point (beef price +34.6%), 18 iterations, 799 s.
- 92 tests.

## Sprint 9s: synthetic data removed (October 2026)

Audit first (docs/SYNTHETIC_DATA_AUDIT.md: a full run under line coverage, every fallback evaluated for all 248
regions, the 2017 inputs compared cell by cell with CAPRI's 27 member-state results), then:
- **Crop premiums, costs, prices, yields from CAPRI for every region** (`tools/build/build_crop_economics_2017.py`):
  1,957 region x crop cells had taken their premium from `cap_payments.csv` - the loader's random generator written
  to disk - because the premium file covered 192 regions in CAPRI's codes (fodder, set-aside, wine, fibre never
  matched); wine and fibre costs were template fills, fibre yields a lognormal draw, wine prices national fills in
  36 regions. The loader's cap on horticultural costs (2x the EU median: other fruit in Austria 8,747 EUR/ha against
  CAPRI's 27,000-37,000) is removed. `cap_payments.csv` now holds CAPRI's premium per ha of UAA (budget report only).
- **Methane and CO2 as CAPRI accounts them** (`tools/build/build_ghg_coefs_2017.py`): manure and enteric CH4 per head
  from CAPRI's CH4MAN / CH4ENT (regional; 2030 by CAPRI's reference factors) instead of IPCC flat factors (EU 2017
  manure CH4 1,072 kt flat against CAPRI's 1,396); CO2 from liming per ha of every crop (CAPRI's UAAR CO2LIM, DE11
  116 kg/ha) instead of 600 kg limestone on arable land; CO2 from urea = mineral N x the member state's urea share x
  44/28 instead of 30% x 0.2. GHG reported as all items, **non-CO2** (compared with JRC121368) and CAPRI's **GGWP**
  (non-CO2 + liming), the emission tax's base (supply_model.gms GWPTOT_).
- **Yield response to price**: CAPRI's p_yieldElas (cereals 0.3, oilseeds and potatoes 0.2, others 0) instead of
  0.15 for every crop.
- **No generators, no generic fallbacks**: the loaders' synthetic branches and the environmental module's IPCC /
  literature fallback tables (N excretion, N fixation, N content, manure N2O 2%, ammonia, deposition) are removed;
  a missing file or region raises, and a test checks every region with a herd or crops has CAPRI's coefficients.
  CAPRI tables kept as dictionaries in code (cost shares, feed-cereal weights) moved to CSV.
- Results: the 2030 baseline against CAPRI's reference is unchanged (activities 1.3%, production 1.1%); Farm-to-Fork
  gap **4.31 → 4.06** (cereal price +8.8 against CAPRI's +8, veg+perm price +13.5 against +15, cereal production
  -15.0 = CAPRI, manure CH4 -14.6 against -12.2), 562 s; Green Deal 817 s, prices 1-3 points lower,
  manure CH4 -18.2% (was -20.6%), herds within 0.6 points.
- Then the open items: CAPRI's **fixed activities** (OOIL, OIND, OANI held at their data level, sets.gms FACT) and
  no other-oilseed market (CAPRI has none; the invented world total removed); CAPRI's **grass** dry matter (0.22) and
  fresh yields in every region (56 regions had template yields); CAPRI's **land market** for Ireland (IE01 + IE02)
  and FI1D. Farm-to-Fork gap 4.06 → 4.27, all of it Ireland's land response (grassland +750 kha under the
  per-hectare surplus target); Green Deal within 2.6 points; 531 / 836 s.
- 91 tests.

## Sprint 9r: regional solves in parallel; CAPRI's tariffs for every trade region (October 2026)

- **Parallel regional solves.** At given market prices the regional supply models are independent (CAPRI solves
  them one after another, or as parallel GAMS grid jobs), so `SupplyModule.run` now spreads them over worker
  processes, one per core (`CAPRI_WORKERS` or `SupplyModule.n_workers` to change it; 1 = in one process). The
  workers are forked for each supply call, so they start from the module's current state; each returns its region's
  result, regional model, land and N-price state and cache entries, merged in the regions' order. Results are
  identical to the last digit: full Farm-to-Fork and Green Deal runs compared with the one-process runs, every
  saved figure equal.
- Run times on 2 cores: Farm-to-Fork 799 → 463 s, Green Deal 1537 → 881 s; test suite 782 → 545 s. The supply
  share falls to about 60% of a run; the rest (market, emission-tax coefficients, reporting) is one process.
- **Tariffs.** The market's domestic price levels take a tariff per trade region and commodity. Only the EU row came
  from CAPRI; for the other 28 regions there was no data file and the loader drew them at random, from a module-level
  generator, so every model built in a process got different tariffs (and different oilseed-crushing parameters,
  which use the price levels): two models in one process differed by up to 1.3 kha in a region. Now
  `tools/build/build_tariffs_2017.py` gives every region CAPRI's own measure, as the EU row: total protection on its imports
  from outside the region, ImportP / (Fob + TCost) − 1 over CAPRI's 2017 bilateral flows (the EU row recomputed this
  way from the member states agrees to 0.1 point). Farm-to-Fork: no indicator moves by more than 0.1 point, gap 4.31
  (4.30); Green Deal unchanged. The loader no longer generates tariffs (EU row only, with a warning, without the file).
- 88 tests (new: parallel and one-process solves equal).

## Sprint 9q: CAPRI's 2030 rations and fodder in the projected baseline (October 2026)

- The 2030 rations and requirements are CAPRI's 2030 reference's per head (factors per region, animal and feed on the
  2017 rations; `tools/build/build_ration_trajectory_2030.py` → `capri_ref_ration_2030.csv`), and the fodder balances'
  usable fodder per ha follows CAPRI's FEDM / LEVL of the fodder crops (`capri_ref_fodder_2030.csv`; silage maize for
  biogas in Germany). Before, the 2017 mix scaled by one factor did not match the projected fodder output.
- Regional drift of the baseline from its projected levels: median 0.01%, 90th percentile 0.36% (fodder crops 1.1%,
  was 17%). Against CAPRI's 2030 reference: activities 1.3%, production 1.1%, domestic use 1.6% (medians). Farm-to-Fork
  799 s (fewer calibration rounds); gap 4.30.

## Sprint 9p: projection layer - CAPRI's reference as the baseline, baseline calibration (October 2026)

- **Trajectory**: CAPRI's 2030 reference (CAPMOD's reference run over CAPRI's 2017 results: levels, yields, land
  types per region; `tools/build/build_trajectory_capri_ref.py` → `capri_ref_2030.json`, default in
  `tools/run/run_f2f_2030.py`; `--trajectory captrd` for the trend projection). Land now follows CAPRI's 2030 land types
  per region (the projection read no land block and kept 2017 land). Projected data vs CAPRI's reference: median
  2.7% → 1.0%.
- **Baseline calibration** as CAPMOD's: the baseline of a projected year moves the regional models' linear terms by
  Q (x − target) until each region reproduces its projected levels (fodder crops excepted). Regional drift median
  0.73% → 0.13%, 90th percentile 12.6% → 3.9%; the scenario starts from the calibrated baseline. Baseline adds ~2
  outer iterations (Farm-to-Fork 785 → 984 s).
- **Feed bulk prices 2030** in the rations: CAPRI's feedBlkPrice_ CES of the 2030 product prices per member state.
- Against CAPRI's 2030 reference: activities 3.8 → 2.6%, production 3.4 → 1.4%, domestic use 2.8 → 1.7% (medians).
  Farm-to-Fork gap 4.37 → 4.23 (milk price +27.8%, pork +35%, sheep −8.7%).
- Open: fodder crops in the projected baseline (rations of 2017 scaled; CAPRI's 2030 reference rations would close
  it: closed in 9q). 87 tests.

## Sprint 9o: pigs, manure N2O and ammonia diagnosed; market speed (October 2026)

- **Pigs (−21.9% against CAPRI's −14.5%)**: the whole overshoot is two regions. Brittany and Lombardy lose all their
  pigs (11.2 of the 28.0 M places lost); the rest of the EU loses 14.4%, CAPRI's figure. Their N prices (EUR 63 and 71
  per kg N) come from the tiered target: CAPRI's baseline surplus of 176 and 217 kg N/ha gives cuts of 57% and 65%,
  against 36% for the nine regions JRC121368 relaxed - which the model takes as the nine highest surpluses per ha (all
  Dutch, Belgian and Maltese). The report names them only as "high GNB values associated with high animal numbers"
  that "generated infeasibilities". Sensitivity (s87: the nine with surplus above 150 kg/ha and the most manure N:
  Brittany, Lombardy, Ireland's IE05, Dutch, Belgian and Danish regions): pigs −18.8%, gap 4.36 → 4.15, but pork +27%
  (CAPRI +43). Default unchanged (the report does not name the regions); recorded.
- **Manure N2O (−23% against −3.2%) and ammonia (−44% against −33%)**: manure N falls 21% (herds, a quarter of it in
  Brittany and Lombardy); technologies −2.2 Mt CO2-eq net, where CAPRI's ammonia options add +6.2 Mt. Inhibitors on
  manure are adopted on 49% of manure N: with CAPRI's calibration any region whose N price exceeds ~EUR 0.4/kg N adopts
  them, and the model's binding regions are at EUR 5-70. Both follow the regional N prices; no defect in the accounts.
- **Market speed**: the trade system's prices computed once per evaluation instead of twice; supply and demand
  arithmetic in arrays; the market loop's damping now recovers after a damped step (a single halving had slowed every
  later step: market solves ran to their 60-step limit, now ~40). Farm-to-Fork: 865 → 747 s, results within 0.1 point.

## Sprint 9n: milk price re-checked; speed and reproducibility (October 2026)

- **Milk price (Farm-to-Fork +28.9% against CAPRI's +1.5%)**: re-examined, no defect found. EU milk delivered falls
  6.5%; product prices rise 5-21% (butter +21%, cheese +8.5%); fat +30%, protein +16%; raw milk +29%. Star 3.0's
  block passes this on as CAPRI's equations do (product price = fat and protein value + processing margin, margins
  falling with throughput, raw milk almost all fat and protein value); member states move with their own milk (the
  Netherlands −17% milk, +44% price; Germany +1%, +16%). JRC121368's +1.2% with milk −10% cannot come from star 3.0's
  coefficients; settling it needs a star 3.0 scenario result with a dairy shock.
- **Speed** (behaviour unchanged; profile of a full Farm-to-Fork run): scalar pandas lookups in the organic and
  pesticide cost terms, the breeding columns and the biofuel state replaced by dicts and arrays; the N balance of one
  unit of an activity memoised (it reads only the activity's own yield and factors); the conic regional problems
  assembled from sparse blocks instead of a cell-by-cell LIL matrix; the biofuel feedstock loop skipped where only
  biofuel use is needed; the demand reference frames built once. Farm-to-Fork 2030: 84 s → 67 s per outer
  iteration (−21%), 1006 → 865 s for the run.
- **Reproducible runs**: string hashing is randomised per Python process and the model iterates sets of names in a
  few places, so two runs of one scenario differed by up to ~0.2% (degenerate regions more: Dutch laying hens 10-20%).
  `tools/run/run_f2f_2030.py` and `tools/run/run_vcs_2030.py` fix `PYTHONHASHSEED=0` (re-exec), the Dockerfile sets it; with
  it a run repeats exactly. Farm-to-Fork gap 4.36.

## Sprint 9m: inhibitors on manure under the emission tax (October 2026)

- CAPRI's nitrification inhibitors on applied manure (NITR_INH_MAN) were decided at the nitrogen price only. Under
  the tax their value per t of manure N now adds the tax on what they save, as the accounts count it: the mineral N
  they displace (soil N2O), application N2O x CAPRI's literature effect N2OAPP (0.38 in Upper Bavaria), less the
  indirect N2O of the extra application NH3 (NH3APP −0.23); the animals get the tax saved at the adopted share.
- EUR 50/t, full EU 2030 (s84): adopted on 34% of manure N; GHG −10.5% (s83 −9.5%), manure N2O −15.9% (−10.3%),
  fertiliser N2O −14.4%, ammonia +1.9% (−2.5%): the tax trades ammonia for nitrous oxide, as CAPRI's literature
  factors imply.
- 86 tests.

## Sprint 9l: fertiliser options under the emission tax (October 2026)

- Under CAPRI's ghgTax the fertiliser-efficiency options are in the regional model without a nitrogen row: crops'
  mineral N becomes the conic model's variable (as with a nitrogen row), taxed at the accounts' soil N2O factor (the
  crops give back the part their own emission coefficient carries); options with CAPRI's literature side effects
  (nitrification inhibitors, p_litRevFertTechs) carry those instead of their N saving, as the accounts count them.
- EUR 50/t, full EU 2030 (s83): GHG −9.5% (s82 −8.0%), fertiliser N2O −13.3% (−2.3%), N surplus −10.8%, ammonia
  −2.5%; inhibitors on 15% and precision farming on 20% of the area.
- Still outside the tax: inhibitors on manure (decided at the nitrogen price only; closed in 9m).
- 86 tests.

## Sprint 9k: manure and ammonia in every EU solve (October 2026)

- **CAPRI's crop nutrient balance (NUTNED_) in every EU solve**: the crop-need row (all manure, imports included,
  within the crops' need at the manure's availability) was built only under a nitrogen target; CAPRI has it in every
  run. `SupplyModule._manure_context` hands each EU regional model its manure N per unit, crops' base mineral N and
  base yields (`use_nutned_always`, on); Norway is left out (msNoEU).
- **Manure trade in every EU solve with trade on**: the pool columns no longer need a nitrogen row. Their cost is
  the pool price alone: CAPRI calibrates its trade-cost constants from the base duals (define_manure_trade_costs.gms
  FINALIZE), which with a fixed fertiliser price absorbs the fertiliser bought or saved per t traded; the old
  `sub x p_f` terms also leaked into the pool clearing (the price was read back from the column's cost, so each pool's
  price carried its regions' own fertiliser terms). The pool clearing now reads the price the region was solved at.
  Baseline trade deviation: 0.1 kt N.
- **Emission tax on the ammonia options and manure trade**: under CAPRI's ghgTax the ammonia options are in the
  regional model without a nitrogen row, each with its emissions per unit of share (manure N2O through the loss
  cascade, a finite difference of the accounts; indirect N2O of the NH3 kept; soil N2O of the mineral N it displaces);
  traded manure carries the soil N2O of the mineral N bought or saved. Without a nitrogen row or a tax they stay at
  their base shares (CAPRI's thresh calibration), as before.
- Full EU 2030: Farm-to-Fork unchanged (gap 4.37); Green Deal unchanged within 0.8 points (pool prices now reported,
  EUR 25-28/kg N in the livestock pools); EUR 50/t tax: GHG −8.0% (−6.8% before), manure N2O −10.3% (−3.2%),
  ammonia −0.9% (−2.5%): low-emission spreading falls 40.8% → 32.5% (its NH3 kept raises application N2O), covered
  storage rises 15% → 28%, air purification to 6%, acidification to 1.4%.
- Fertiliser options under a tax alone: still only with a nitrogen or mineral-N row (closed in 9l).
- 85 tests.

## Housekeeping (October 2026)

- **Licence: GNU GPL version 3** (GPL-3.0-only): `LICENSE` holds the GPLv3 text, `NOTICE` the copyright and GPL
  notice; `pyproject.toml` and `CITATION.cff` updated (the citation file still said MIT).
- **Container**: `Dockerfile` (Debian bookworm-slim, Python 3.11 in a virtual environment, non-root user; default
  command the test suite) and `.dockerignore`. `requirements.txt` and `pyproject.toml` now list Clarabel as required
  (the regional problems with feeding inside use it) and name the package `capri_mod` (they still said
  `capri_python`).
- **`capri_data/fao_2021` moved to `capri_data/sources/fao_2021`**, with `shared/trade_flows_2021.csv`: FAOSTAT 2021
  extracts that the model does not read (its trade and balances are CAPRI's); `tools/build/recalibrate_trade_2017.py`
  reads the CSV from there. 87 declared inputs.
- README: chapter "Contributors" removed; manure market default and install instructions corrected.

## Sprint 9j: manure trade checked against CAPRI (October 2026)

- **Base manure trade rebuilt** from CAPRI's 2030 Green Deal reference with endogenous technologies (MTRADE.NITF,
  EXCRET.NITF per CAPRI region, per group of CAPRI and model regions; `tools/build/build_manure_trade_base.py`). The old
  file had no builder and matched by CAPRI code: Belgium, Italy, Poland, Sweden, Romania, Ireland and others had no
  trade (73 exporting and 76 importing regions; now 113 and 111; 1.2 Mt N between EU regions).
- **The base trade counts only where the run trades manure** (`EnvironmentalModule.set_manure_trade`, also in the
  supply models' balance): Farm-to-Fork as JRC121368 (no trade) keeps all manure in its region in the scenario and
  its baseline, as the report's CAPRI. F2F gap 4.53 → 4.36.
- Green Deal (star 3.0 settings, trade on): 1.1 Mt N of manure moves against the base pattern; the importing regions
  no longer give up crops (−4.2% crop area against −5.4% elsewhere). The runner reported pool prices from the
  unprojected model (0): fixed.
- 84 tests.

## Sprint 9i: no post-solve modules; CAPRI's emission tax inside the supply models (October 2026)

- **Feed module retired**: the post-solve requirement functions and feed balance (off by default, superseded by
  feeding inside the supply models since Sprint 4) are gone with their data (`coco_feed_availability_national.csv`,
  `capreg_feed_requirements.csv`); `results["feed"]` now reports the supply models' feed use per region, animal
  and bulk.
- **Post-solve abatement retired**: the net-revenue MACC, the EcAMPA measures at full uptake and CAPRI's portfolio
  applied after the solve (`capri_mod/abatement/`, `ecampa_measures.csv`, `capri_ghg_mitigation.csv`,
  `capri_mitigation_potential.csv`). CAPRI's options are endogenous in the supply models.
- **CAPRI's emission tax (ghgTax)** in the supply models (`capri_mod/supply/ghg_tax.py`): each column's emission per
  unit at the baseline solution (finite differences of the accounts; cattle enteric CH4 per t of feed fed), EU
  regions only; `PolicyScenario.carbon_tax`, `carbon_tax_scenario()` (the proxy payments it used are gone),
  `run(carbon_price=)`, `run_f2f_2030.py --scenario carbontax`. EUR 50/t: GHG −6.8%, enteric CH4 −10%.
- 83 tests, 88 declared inputs.

## Sprint 9h: CAPRI's feed bulks complete, residual feed markets (October 2026)

- **All five tradable feed bulks per member state** (FCER, FPRO, FENE, FOTH, FMIL; `feedBlkPrice_`, `feedShareEqu_`,
  p_rhoFeed 6/6/5/0.5/0.5): every ration's bulks priced at the member state's index (before: FCER and FPRO only,
  energy-rich, other and milk feeds at base prices); feed use of the FENE, FOTH and FMIL products from the supply
  models' bulks. Feed shares now of total use including processing; the feed correction is added to the row
  (crushing demand kept). Dairy feed per member state's FMIL bulk.
- **FENI and FPRI are market commodities** (45): CAPRI's bilateral flows, prices and elasticities; EU output by
  CAPRI's `MaprFeed_` from cereals' and sugar's food, processing and biofuel use (`tools/build/build_feed_byproducts.py`,
  `feed_byproducts.csv`); non-EU p_elasSupp and p_ElasFeed (`build_feed_demand_nonEU.py`). Baseline exactly
  CAPRI's 2030 EU output and use. docs/FEED_MARKETS.md.
- Farm-to-Fork 2030: gap 4.59 → 4.53; FENI and FPRI prices −10%. 87 tests, 91 declared inputs.

## Sprint 9g: CAPRI's feed options on, as star 3.0 runs them (October 2026)

- **Low-nitrogen feeding** (`envind/low_n_feed.gms`, `ghgTechLowNFeed 1`): per region and animal from CAPRI's
  requirement corrections p_animReqCorrFac and res_17 manure N (`tools/build/build_lownfeed_effects.py`,
  `lownfeed_effects.csv`); a column of the regional models; curvature per unit of the eligible share (also fixes the
  breeding options where the eligible share is below 1).
- **Linseed and nitrate** (`envind/line_nitr.gms`, `ghgTechLineNitr 1`, a switch): requirement effects as
  supply_model.gms REQSE_/REQSN_, maximum shares from CAPRI's max calibration run (LINE_Tot, Nitr_Tot now extracted
  by `tools/build/extract_capri_costsavings.py`), CAPRI's costs halved, CH4ENT in the emission accounts
  (`tools/build/build_supplement_effects.py`, `supplement_effects.csv`). 3-NOP registered. The ration model's early
  nitrate ingredient is ignored when these columns exist.
- Farm-to-Fork 2030: gap 5.15 → 4.59; low-N feed 42% of manure N (Table 17: 0%), linseed 0.8%, nitrate 0.2% (7%).
- `tools/run/run_tests.py` uses its own fixtures even with pytest installed. 86 tests, 90 declared inputs.

## Sprint 9f: CAPRI's dairy block on, as star 3.0 runs it (October 2026)

- Rule: a block star 3.0 runs is on and judged against its own CAPRI reference; the Farm-to-Fork gap is recorded.
- **Nine dairy products traded**: FRMI, CREM, COCM, WMIO, CASE become market commodities (43) with CAPRI's bilateral
  flows, FAO_agg world prices and balances, Armington and p_ElasDem elasticities (`tools/build/build_dairy_trade_params.py`;
  the four traded before get CAPRI's weighted p_ElasDem too). Non-EU dairy demand follows the regions' p_ElasDem.
- **Raw milk, fat and protein per member state** (FatsProtBal_, ProcMargM_, DairyNQ_ per RMS); regional models get
  their member state's milk price, relaxed per member state; convergence on member states >= 1% of EU milk (Cyprus
  circles; reported in `metadata["milk_small_ms_gap"]`).
- **Dairy block on by default** (`use_dairy_block = True`; `--no-dairy-block`).
- Baseline: dairy products within 3.6% of CAPRI's 2030 reference; domestic-use median 3.7 -> 3.0%.
  Farm-to-Fork: raw milk +34% (CAPRI +1.5), dairy cows -7.8% (-10), sheep -12.2% (-9.5); gap 3.77 -> 5.15 (milk
  price 1.6 points). Outer-loop trace names the region and loop that keep a run open. 84 tests. docs/DAIRY_PROCESSING.md.

## Sprint 9e: CAPRI's inner fertiliser model and the mineral fertiliser reduction (October 2026)

- **Inner fertiliser distribution model** (star 3.0 default `useInnerFertDistModel`; `capri_mod/fert/inner_fert_dist.py`):
  CAPRI's posterior-mode allocation of mineral, manure and residue N over its 17 crop groups (gamma priors,
  `NUTNED_`, `fertDistExcr_`, `fertDistCres_`, beta regulations), on CAPRI's 2030 priors
  (`tools/build/build_fert_dist_priors.py`: crop-level dump flows summed to the groups; postModePerHa reproduced to 4e-5
  against CAPRI's priFertDist results; 250 CAPRI regions + country fallback). Returns CAPRI's priors exactly at the
  baseline's totals in every region (tested). Reported per run as `results["fert_dist"]`. With all flows positive
  it leaves the regional totals as they were (the sum of `NUTNED_` is the balance's identity), so it changes no
  result by itself; Farm-to-Fork with it and the old technology base: gap 3.31, every indicator within 0.1 point.
- **Mineral fertiliser reduction, `mineRedu`** (Green Deal; scenario shock, EU27): "20" as `minfert_redu_uaa.gms`
  (mineral N per ha of land <= baseline x 0.8), "10/13/17/20crp" as `minfert_redu_by_crop.gms` (caps per crop group
  from the baseline's allocation, groups below 30 kg/ha and CAPRI's listed pairs held at baseline - read from the
  GAMS file by year, `tools/build/build_mineral_redu_rules.py` - the "f2f" and "limCres" regulations in the inner model).
  A mineral-N row in each regional model with the balance's own coefficients; fertiliser technologies act on it.
  The ammonia options' manure N kept from losses displaces mineral N on that row too.
  `greendeal_scenario(mineRedu=)`, `run_f2f_2030.py --mine-redu`. Green Deal 2030 with 20crp against mine00:
  cap binding in 49 regions (median 3.3 EUR/kg N), cereal price +1.7 points, cereal output -1.1, fertiliser N2O -0.8.
- **Fix: the fertiliser technologies' base.** Inside the conic model they scaled each crop's whole mineral
  coefficient, which includes its share of the manure-covered need; the accounts scaled the mineral rate only, so
  the nitrogen row counted ~40% more mineral N saved than the reported balance (Upper Bavaria wheat 108 against 77
  kg N/ha). They now act on the mineral rate in the rows and in the costs, as CAPRI's mineral x (1 + E). Farm-to-Fork:
  N surplus -32.1 -> -34.3% (CAPRI -33.5), herds -1 to -3 points more (pigs -23.1%, dairy cows -13.7%), fertiliser
  N2O -42.9%; **20-indicator gap 3.31 -> 3.77**, all of it from this fix (s63: old base, 3.31).
- `OWN_RESIDUE_CROPS` = CAPRI's permanent groups (GRAS, APPL, CITR, TAGR, WINE, OLIV); OFRU and NURS are arable
  groups in CAPRI (VEGE, OAFC). Star 3.0's "minimum shares of anorganic fertilizers" is false: no floor (doc fixed).
- Removed orphan `capri_fertiliser_allocation_2030.csv` (153 regions, unread). 83 tests; 88 declared inputs.
  docs/FERTILISER_ALLOCATION.md.

## Sprint 9d: the biofuel loop closed - DDGS, CAPRI's feed bulks, processing, mandates (October 2026)

- **DDGS** is a market commodity (38): output from the ethanol plants' cereal feedstocks (`prodQuantBiofBy_`,
  CAPRI's 72.3 Mt reproduced in every region), traded (rho1 1.2, rho2 2.4), its producer price in the plants'
  feedstock cost (`biofFeedCost_`). Stays a market without BIOF_M, as in CAPRI.
- **CAPRI's feed bulks** (`feedBlkPrice_`, `feedShareEqu_`; `tools/build/build_feed_bulks.py`): per member state cereals
  (FCER) and protein-rich feed (FPRO, with DDGS) are split into products by a CES (rho 6) on their prices; the
  bulk follows the member state's herds and rations, its price index goes to the rations and per-head feed costs.
  Replaces the single EU cereal index and cake index (`CAPRIModel._feed_shares`, `_cake_feed_shares`,
  `FEED_DEMAND_COMMODITIES` removed).
- **Non-EU DDGS feed** from CAPRI's p_ElasFeed; `feed_demand_nonEU.json` now built by
  `tools/build/build_feed_demand_nonEU.py` (reproduces the earlier 125 entries exactly; adds DDGS and Ethiopia).
- **Non-fuel ethanol processing** from CAPRI's `ProcNQ_` (own-price Hessian `p_hessNQProc`).
- **Mandate shock** `PolicyScenario.biofuel_mandate` (`change_biof_mandate.gms`), `run_f2f_2030.py --biofuel-mandate`.
- Farm-to-Fork 2030: gap 3.31; beef/pork/poultry prices +0.4–0.6 points; EU DDGS −7%, price −3.8%. Baseline:
  DDGS within 2.3% of CAPRI, domestic-use median deviation 3.7%. 81 tests. docs/BIOFUEL_MARKET.md.

## Sprint 9c: endogenous biofuel markets, CAPRI's BIOF_M (October 2026)

- **Bio-ethanol and bio-diesel are market commodities** (37 now) with CAPRI's equations per CAPRI market region:
  supply on the processing margin (`SupplyBiof_`; non-agricultural, second-generation and exogenous output fixed),
  use from the mandate plus a sigmoid in the price against fossil fuel (`biofDemShare_`, `biofDem_`, `Cpri_`),
  bilateral trade with CAPRI's 2030 flows and Armington elasticities (rho1 2.2, rho2 4.5). Calibrated as
  `biofuel/def_biofuel_params.gms` to CAPRI's 2030 reference (`tools/build/build_biofuel_market.py`, replacing
  `build_biofuel_feedstock.py`; `market/biofuel_market.csv`); every region's output and use reproduced.
- Feedstock use follows the biofuel output, now in every region (non-EU too).
- star 3.0's GUI default and capri-mod's: `CAPRIModel.biofuel_markets`, `PolicyScenario.biofuel_markets`,
  `run(biofuel_markets=)`, `run_f2f_2030.py --no-biofuel-markets`; held for the scenario and its baseline.
- Farm-to-Fork 2030: EU ethanol output −4.3%, biodiesel −1.4%, ethanol price +8.6%; feedstock use for biofuels down
  (other cereals and wine −24%); gap 3.29 → 3.32. Baseline: EU biofuel output and use within 0.1% of CAPRI.
- REGISTERED then, closed in Sprint 9d: DDGS and glycerine at reference prices (no DDGS market, DDGS not in rations); non-fuel ethanol use
  fixed. docs/BIOFUEL_MARKET.md. 80 tests.
- Orphans removed: `MarketModule._demand_response_ref` (a pre-vectorisation copy of `demand_response` with no
  caller), `tools/build_biofuel_feedstock.py` and its uncompressed extract (superseded by `build_biofuel_market.py`).

## Sprint 9b: scenario settings as star 3.0 does (October 2026)

- capri-mod's defaults are star 3.0's (installation GUI, docs/SCENARIO_SETTINGS.md): manure trade on by default.
- Each scenario carries its own settings (`PolicyScenario.manure_trade`, `surplus_rule`, `endotech`), applied to the
  scenario and its baseline: `greendeal_scenario()` = star 3.0's files (surptot.gms rule, manure trade on, genomics
  0); `farm_to_fork_scenario()` = JRC121368 (tiered rule, 36% cap, manure trade off, genomics 0.2).
- `run_f2f_2030.py --scenario f2f|greendeal` (default f2f) replaces `--config`. Green Deal switches accept CAPRI's GUI
  values only. Farm-to-Fork gap 3.29. 79 tests.

## Sprint 9a: scenario configurations - star 3.0's surplus rule; pig diagnosis (October 2026)

- **Surplus target as scenario configuration**: CAPRI star 3.0's `surptot.gms` cuts every EU NUTS2 region's baseline
  surplus per hectare by surpRedu% (homogeneous 50%); JRC121368's tiered rule with the nine-region 36% cap is kept.
  `PolicyScenario.surplus_rule` / `surplus_cut`, `greendeal_scenario(surplus_rule=)`, `run_f2f_2030.py --surplus-rule`
  and `--config jrc121368|star3` (whole configurations: surplus rule, manure trade, genomics).
- Farm-to-Fork under star 3.0's own configuration: EU surplus -46% (JRC121368 -33.5%), pigs -23%, gap 8.1 against the
  report; the report's configuration gives 3.29. JRC121368 is comparable only with its own configuration.
- Pigs: the overshoot sits in Brittany and Lombardy (N price EUR 68 and 55/kg, pigs -100%) where, without manure trade,
  only animals can carry the cut.
- Dairy block in the bilateral market: the EU raw milk price comes from the block (it had been dropped). Still opt-in
  (raw milk +86% with the block).

## Sprint 8m: CAPRI's bilateral market, TRQs, and a 2030 baseline on CAPRI's trend projection (October 2026)

- **CAPRI's market model** (`capri_mod/market/bilateral.py`, `MarketModule._solve_bilateral*`, default
  `market_structure = "bilateral"`): a market price per region, total use an Armington aggregate of domestic sales
  and imports (rho1), imports a CES over origins (rho2; CAPRI's `market1.gms` / `market1_ch.gms` values), bilateral
  flows priced at the exporter's price plus CAPRI's transport costs and tariffs. Data from CAPRI's own market
  results of the run's year (`tools/build/build_bilateral_market.py`: 2017 base market, 2030 Green Deal reference);
  CAPRI's flows kept at calibration with domestic sales absorbing the model's production; baseline runs
  recalibrate at each outer iteration (reference prices); successive linearisation with an exact Newton solve
  per product. Replaces one world price per commodity and the EU premium (kept as `"premium"`).
- **EU tariff-rate quotas** with CAPRI's sigmoid (slope 200 around 97% of the quota), solved per quota with its
  flow. In CAPRI's 2030 reference the EU's meat quotas are far from filled: no effect under Farm-to-Fork.
- **Market products as CAPRI trades them**: wheat = soft + durum (durum price follows), olive oil and milled rice
  at CAPRI's processing yields (`tools/build/build_processing_yields.py`); the invented durum world market removed.
- **Projection fixes**: CAPRI's trend projection read by the model's names and regions
  (`tools/build/build_trajectory_model_keys.py`: 246 of 248 regions had fallen back to EU medians); livestock output
  per head and requirements follow the projected yields (2030 cows gave 2017 milk); crop areas follow CAPRI's
  trend levels per activity.
- **Baseline reproduction** against star 3.0's 2030 reference: median deviation 9.5% -> 3.8% (activity levels),
  9.4% -> 3.8% (production), 11.3% -> 4.8% (domestic use). Fattening cattle settled as a unit difference.
- **Farm-to-Fork 2030 gap 4.51 -> 3.30** (3.48 with the market alone): cereals +8.0% (CAPRI +8), beef +17.1% (+24),
  pork +33.8% (+43), poultry +22.7% (+18), pigs -21.1% (-14.5). 78 tests.

## Star 3.0 as the reference: technology settings, world market base, placeholders, baseline check (October 2026)

- **Technology settings are scenario configuration** (`capri_mod/policy/endotech.py`): `ghgTechMYld` and
  `ghgTechFEff` as in CAPRI's `refpol_endotech_all_sup` (loaded by the Green Deal scenario file, launch value wins,
  same value in reference and policy run). `PolicyScenario.endotech`, `CAPRIModel.run(endotech=...)`,
  `run_f2f_2030.py --endotech`; the baseline a scenario is compared with uses the scenario's settings (cache and
  genomics calibration kept per setting). Default star 3.0: milk-yield genomics off (0), feed efficiency 0.1;
  `--endotech jrc121368` gives the JRC-era 0.2. `genetics_effects.csv` is now per unit of the parameter. Gap at
  the default: 4.36, unchanged.
- **World market base from CAPRI** (`tools/build/build_world_market_baseline.py`, `world_market_baseline.json`): every
  region's base balance of 32 market commodities from CAPRI's FAO_agg (base period), and the EU's base
  self-sufficiency from it. Before: world sugar was sugar cane (1,768 Mt vs 168), pork 171 Mt (120), eggs 126 (84),
  maize 1,591 (1,136), wine 70 (27) from an extract and invented allocations.
- **Sugar as CAPRI makes it** (`tools/build/build_sugar_processing.py`, `sugar_processing.csv`): sugar = beet x the
  member state's sugar per beet (CAPRI 2030 reference; EU 0.156, not the fixed 0.135); beet's price follows the
  sugar price (`arm/set_prices.gms`); the world sugar-beet market removed.
- **Placeholders removed**: FATS and OFOD_M markets (no supply, no use, invented data). **Rye and oats** reach the
  other-cereals market (they reached none). **Dairy products** without the dairy block at CAPRI's member-state
  yields (cheese 0.068 t per t of milk, was 0.0456).
- **Baseline reproduction check** (`tools/check/compare_baseline_capri.py`, docs/BASELINE_REPRODUCTION.md): the 2030
  baseline against CAPRI star 3.0's own 2030 reference, no version gap. Median deviation: activity levels 9.5%,
  production 9.4%, domestic use 11.3%, relative prices 28%. Findings: fattening bulls and heifers, fruit and
  vegetable prices, 2030 self-sufficiency, milk yield. `capri_eu27_levels_2030_ref.csv` (EU levels) replaces the
  file the projection test used, which held France's levels.
- Farm-to-Fork 2030 gap 4.36 -> 4.51: beef price +9% (+12.8 before; CAPRI +24), poultry +16% (+20.6; +18), pork
  +21% (+19.6; +43). The EU premium approximation responds to CAPRI's world size by lowering the beef premium; the
  full bilateral market is planned (docs/ARMINGTON_MARKET.md, Sprint 8).

## Dairy Stage 4: CAPRI's dairy block outside the EU (October 2026)

- CAPRI solves its dairy block in every market region, with raw milk from its own supply function outside the
  EU. `tools/build/build_dairy_world_blocks.py` (53 non-EU market regions -> 24 trade regions) and
  `MarketModule._dairy_world_params` / `_dairy_solve`: each region's butter, SMP, cheese and whey now respond
  through its raw milk supply (CAPRI elasticities 0.7-1.0) and its dairies' product choice, instead of a flat
  0.2-0.3 elasticity per product. The EU and non-EU blocks share one solver (`_dairy_algebra`).
- Farm-to-Fork with the blocks: world dairy prices +2.6-3.5% (before 5-8%), raw milk +28% (+30%), gap 5.35. The
  rest of the milk price comes from inside the EU: the products that clear in the EU (fresh milk products about
  half of the milk) have inelastic demand and fixed trade. The blocks stay opt-in (`--dairy-block`).

## Cattle genomics in the supply model; dairy Stage 3 (October 2026)

- **Cattle genomics** (`envind/breeding.gms`; `tools/build/build_genetics_effects.py`, `genetics_effects.csv`;
  `RegionalSupplyModel._genetics_columns`, default on): higher milk yield for dairy cows (gain toward the DK/PT/SE/FI
  2030 yields x 0.2, as the endotech references of JRC121368's era; requirements and manure N recomputed with
  breeding.gms's own functions; cost max(EUR 20, 10% of the extra milk revenue)) and lower energy need for
  non-dairy ruminants (energy -10%, protein -5%, manure N accordingly; not replacement heifers or milk sheep;
  cost max(EUR 2, 0.5% of feed cost)). Inside each regional model as columns on the manure rows and the feed
  requirement rows, with CAPRI's calibration (no adoption at base, relSubs0/relSubs1, curvature). Farm-to-Fork:
  higher milk yield 0 -> 3.3% of dairy cows (JRC121368 Table 17: 0 -> 15%), ruminant efficiency 0 -> 33% (5 -> 9%);
  beef animals -14.5 -> -13.5%; gap 4.30 -> 4.36. The efficiency option spreads and the yield option is held back
  for the same reason as the other nitrogen-driven options: the model's regional nitrogen price.
  Note: superseded - the milk-yield setting is now a scenario parameter, default star 3.0's 0 (see above).
- **Dairy Stage 3** (opt-in with the dairy block): EU feed use of dairy products follows the calves' milk feed
  (CAPRI's FMIL block, CES 0.5); EU food use has CAPRI's own and cross-price elasticities among the nine
  products. Farm-to-Fork with the block: whey use -21% (exports up, as the report says), raw milk +30% (+34%
  before), dairy cows -7.0%, gap 5.44. Still opt-in: product prices rise 9-16% where CAPRI's +1.5% for raw milk
  implies they barely moved.

## Biofuels and dairy into the market; the EU price reported with one premium (October 2026)

- **Biofuel feedstock demand inside the market (crushing stage 4).** CAPRI's biofuel block (`biofFeedCost_`,
  `biofFeedCostAgg_`, `Biof_`, `prodBiof_`) per member state, as CAPRI runs scenarios without endogenous biofuel
  markets (`p_endoBioMarket = 0`: biofuel output and prices fixed, feedstock mix free, CES elasticity 4). Data from
  CAPRI's 2030 reference market results (`tools/build_biofuel_feedstock.py`); the builder reproduces CAPRI's own
  `BiofFeedCost` exactly in every member state (glycerine at CAPRI's fixed 600 EUR/t). The biofuel part of EU use
  (rapeseed oil 52%, soybean oil 23%, sugar 12%, cereals 4-7%) follows the CES instead of the food response. The
  post-solve `BiofuelModule` (hard-coded yields, feedstock splits, a 6.5% blending share, a demand the market never
  saw) is retired; `run(biofuel_output_scale=...)` sets a mandate scenario. Farm-to-Fork gap 4.64 -> 4.62.
- **The reported EU price carried the Armington premium twice.** `MarketModule.solve` wrote wedge x premium into the
  domestic prices for the demand calculation and the report multiplied by the premium again. Supply was always shown
  world x premium once, so no quantity changes; every reported EU price change of a commodity with a premium was
  inflated. Farm-to-Fork, reported before -> paid: cereals +10.4 -> +5.7%, oilseeds +19.9 -> +11.8%, beef +28.6 ->
  +13.7%, pork +39.5 -> +20.2%, poultry +45.4 -> +21.1%. Pork and beef now fall short of CAPRI's (+43, +24), poultry
  is close (+18). Earlier comparisons of prices with CAPRI in this log and the sprint document used the inflated
  figures.
- **Livestock output by CAPRI final product** (`tools/build/build_livestock_products.py`,
  `livestock_output_by_product_coef.csv`): the market bridge splits each animal's output at the region's own
  composition - dairy cows into milk and cull-cow beef (now in the beef market), sheep and goats into meat and milk
  (5.3 Mt of sheep "meat" was mostly milk; sheep milk is now raw milk and its value moves with the milk price,
  `SHGP.MILK`), laying hens into eggs and hen meat. Replaces milk = dairy-cow output x 0.9575. Sheep and goats
  -12.8% (CAPRI -9.5; -14.9 before).
- **World dairy-product balances from CAPRI's FAO_agg** (`tools/build/build_dairy_world_markets.py`): CAPRI's codes BUTT,
  SMIP, WHEP never matched the market's BUTR, SKIM, WHEY (every region got an invented share of a hard-coded world
  total) and the primary cheese item was not cheese (USA 28 kt against CAPRI's 5,889).
- **CAPRI's dairy processing** (`MarketModule.dairy_block`, `tools/build/build_dairy_processing.py`,
  `docs/DAIRY_PROCESSING.md`), opt-in (`use_dairy_block`, `run_f2f_2030.py --dairy-block`): `DairyNQ_`,
  `ProcMargM_`, `FatsProtBal_` per member state with CAPRI's Hessian (reproduces `p_ElasDair` to 7e-5), nine
  products, raw milk priced by its fat and protein. With it the Farm-to-Fork milk price is +34% (CAPRI +1.5%) and
  dairy cows -5.9% (CAPRI -10): CAPRI's block passes product prices to raw milk at about 2.5x (processing margins
  are half the product price), and the model's dairy-product markets rise 11-19% where CAPRI's evidently barely
  move - they lack CAPRI's herd-driven feed demand for whey and skimmed milk powder (pigs and calves) and its
  cross-price food demand. Gap 5.63 with the block, 4.30 without; off by default until those are in (Stage 3).
- Farm-to-Fork 2030 default: gap **4.30** (4.64 before; mostly the corrected price report).

## Manure N2O: CAPRI's loss cascade and housing equation (October 2026)

- **Loss cascade.** CAPRI applies its N2O loss factors to the N LEFT after NH3 (and NOx) losses at the same stage
  (supply_model.gms HOUSN_, APPLN_: "the N2O loss factor is applied after the losses of NH3 and NOX"), so NH3 kept by
  a cover, low-emission housing or spreading reaches the field and raises application N2O. The model scaled its stage
  factors by excreted N only. Now housing and application N2O follow the N left at each stage at the regional option
  shares against the base shares (`ammonia_techs.stage_n`, `EnvironmentalModule._manure_n2o_cascade`).
- **CAPRI's housing equation.** CAPRI computes manure-management N2O at housing level and moves the storage options'
  N2OSTO effects to N2OHOU (ammo_tech.gms), but HOUSN_ sums only the housing options and the combined air
  purification + cover options: the plain covers' N2OHOU entries (-58 to -90% per adopting unit) are never used. The
  model applied them - covers then cut manure N2O instead of raising it through the cascade.
  `tools/build/build_manure_n2o.py` now keeps housing effects for HOUSN_'s options only.
- Farm-to-Fork 2030: manure N2O -28.8% -> **-21.5%** (CAPRI -3.2%); gap 4.71 -> 4.64. The technologies' share is now
  reported (`ghg_manure_n2o_tech`): -1.8 Mt CO2eq, against +6.2 Mt for CAPRI's ammonia technologies (JRC121368
  Table 18: housing and storage +0.9, application +5.2). Of the model's -1.8 Mt, nitrification inhibitors on manure are
  -4.8 Mt (43.7% adoption, -36% application N2O) - more than CAPRI's -1.8 Mt for ALL inhibitors, mineral included; the
  ammonia options alone add +2.9 Mt. The open part is the manure inhibitors' adoption: CAPRI's own cost terms for
  that option (target N2OMAN) are not in the data received; the model uses the mineral option's (86 EUR/t N) with
  CAPRI's default calibration.

## CAPRI's bull and heifer splits (Sprint 7c); Friesland (October 2026)

- **Bulls and heifers at two intensities**, as CAPRI (BULL/BULH, HEIL/HEIH; `tools/build/build_cattle_intensity.py`,
  `cattle_intensity.csv`). They differ in fattening length (DE94 bulls 173 vs 270 days, heifers 78 vs 223), slaughter
  weight, daily feed and manure; each animal takes one young animal. The model's bulls and heifers are census heads,
  i.e. stalls, so per stall-year the flow items scale with 365/days: a low-intensity bull stall turns over more animals
  (young animals bought +86% median), with 10% less manure N and 14% less energy per day than the average stall. One
  column per animal moves stalls from high to low, built like the dairy split (manure rows, feed requirement rows, PMP
  from CAPRI's own terms, calibrated at base on the duals) plus beef output, the young-animal balance and the
  young-animal price. Farm-to-Fork 2030: low-intensity bull stalls 33.6% -> 34.1%, heifers 7.2% -> 6.5%; EU aggregates
  move by at most 0.2 points (gap 4.71).
- **Friesland (NL12, EUR 16,000/kg N)**: its baseline balance matches CAPRI's item by item (surplus 246 vs 247 kg
  N/ha), so the price is the tiered rule itself: a 70% cut (to 75 kg N/ha) on a dairy region whose mineral fertiliser
  is 101 kg/ha. Sensitivities: with Friesland among the relaxed regions the gap is 4.58 and no region exceeds EUR
  2,300/kg; relying on the infeasibility rule alone (no regions capped up front) relaxes exactly nine regions, all
  Dutch, but leaves three Belgian ones feasible only at EUR 28,000-145,000/kg (gap 5.26). Kept: the nine highest
  baseline surpluses up front plus the infeasibility rule; Friesland stays a documented sensitivity
  (`--capped-regions=+NL12`) until CAPRI's Farm-to-Fork output shows which regions were relaxed.

## Split NUTS regions, the Dutch importing regions, poultry (October 2026)

- **CAPRI regions split or merged between NUTS versions.** Regional tables were mapped with a first-candidate rule,
  so a split parent landed whole on one part: Finland's FI1B (Helsinki-Uusimaa) carried all of Etelae-Suomi's
  manure, revenue, costs and land on its own herd and area (990 kg N per dairy cow, 4.8 kg N per laying hen, arable
  land 709 kha on 121 kha of crops); FI1C took Laensi-Suomi's values (a wrong correspondence entry); Poland's renamed
  and split regions, Saxony, Bolzano/Trento, Budapest, Ireland and the merged FI1D took national averages.
  `tools/lib/_model_regions.py` now holds the NUTS splits and merges and builds region groups: per-head tables divide a
  group's CAPRI total by the group's herd; ratio tables take the group's CAPRI region; `shared/region_capri_map.csv`
  carries the same map for the model's runtime lookups. 21 data files rebuilt; only the 19-24 affected regions
  changed in any of them; per-head manure-N outliers (beyond 3x the median) 79 -> 46, the rest bulls and heifers.
- **Dutch importing regions: JRC121368's rule for infeasible targets.** The report set the cut "at the EU average
  (36%)" where the tiered target "generated infeasibilities in the model". The model applied it only to the nine
  highest baseline surpluses; now any other region whose target proves infeasible in the land-market problem gets
  the same rule (`_relax_n_target`): NL11, NL13, NL23, NL32, NL34 - regions that import 52-123 kg N/ha of manure in
  CAPRI's 2030 reference, held fixed without the manure market. No region falls back to the plain problem any more.
  Tried first and dropped: manure trade allowed only to shrink from CAPRI's baseline flows (importers send back,
  exporters keep). The Dutch pool cannot clear - its exporters (NL41, NL22, the capped regions) would have to take
  back 52 kt N under their own targets - and the imbalance stayed at 11% of supply.
- **Poultry in small regions** (Swedish broilers -100%): not a curvature defect. The surplus row charges each animal
  N price x its N surplus; Swedish broilers earn EUR 29 of output per kg of N in the balance (layers 42, dairy 30),
  so at the Swedish N price (EUR 70/kg under the land rules) they cannot cover it - the same arithmetic as CAPRI's
  e_SURTOTHa. Dairy holds because grassland is conserved and its grass must be fed. FI1D's poultry looked similar for
  a different reason - per-head values 15x too low from the split mapping - fixed above.
- Farm-to-Fork 2030, gap to JRC121368: **4.85 -> 4.70** (data fixes 4.92, relaxation 4.70); with the manure market
  4.77. Remaining region above EUR 1,000/kg: Friesland (NL12, EUR 16,000/kg), feasible only by replacing dairy cows
  with suckler cows; it is the 15th-highest baseline surplus and may be among the report's unnamed nine
  (`--capped-regions=+NL12`).

## CAPRI's land rules are the default: the grassland balance fixed (October 2026)

- **Why the land rules ran away.** Under CAPRI's no-idle-land rule the model's grassland row became an equality. That
  row was the model's own soft limit - grass, fodder maize and other fodder together at most grassland plus a fifth of
  arable land - not CAPRI's balance. Held exactly, it fixed arable fodder at its base area plus a fifth of any arable
  change: Ostra Mellansverige kept 69 kha of fodder leys at 49 kg N/ha surplus at an N price of EUR 332/kg, and
  the cattle eating them, while poultry and pigs went. CAPRI's LandBalNoSlak_(GRAS) holds only the grassland
  activities (GRAE + GRAI) to the grassland area; fodder maize and other fodder are arable crops, already in the
  arable row. With CAPRI's balance (`_build_constraints`, `_land_augment`, under `land_no_slack`):
  Swedish N prices EUR 270-360 -> 50-70/kg, FI1D 852 -> 42, Luxembourg 117 -> 32; regions above EUR 100/kg 11 -> 4.
  The no-idle-land rule alone had shown it: 9 regions above EUR 100/kg without the per-hectare target.
- **Farm-to-Fork 2030, gap to JRC121368: 5.81 -> 4.85** (land rules, no manure trade, the JRC setup): cereal price
  +10.4% (CAPRI +8), pork +40 (+43), dairy cows -13.1 (-10), beef animals -14.8 (-18), poultry -16.8 (-16.5), EU
  farmland +1.8% (+3; the old default -1.9%). With the manure market as well: 4.68. Default since this entry;
  `--no-land-rules` restores the old setup.
- Still extreme: five Dutch regions (NL11, NL12, NL13, NL23, NL32/34) that IMPORT manure in CAPRI's 2030 reference
  (52-123 kg N/ha). With the manure market off those imports stay fixed per hectare - fallow land included (NL34
  set-aside: 31 kg deposition + 86 kg imported manure) - so the tiered target (61-70% cut) cannot be met and the
  solve falls back; with the manure market the imports respond and the land market solves everywhere.

## CAPRI's regional baseline surplus for the N target; catch crops and the landscape floor (October 2026)

- The tiered Farm-to-Fork N target starts from CAPRI's own baseline surplus per ha. The input file matched only CAPRI
  codes in the newest NUTS version and gave **82 regions** their own surplus pattern scaled to CAPRI's national value
  - a proxy, although CAPRI's regional values were already in `capri_gnb_components_2030.csv` under old NUTS codes
  (Italy, Belgium-Luxembourg, Sweden, Finland, Bulgaria, Romania, Poland, Hungary, Ireland). Rebuilt by
  `tools/build/build_capri_baseline_surplus.py` through the NUTS correspondence plus NUTS splits and merges (FI1D = FI13 +
  FI1A; ITH1/2 from IT31; Saxony; Mazowieckie; HU10; Ireland's 2016 regions): 221 regions from their CAPRI region,
  17 from member states CAPRI holds as one region, 10 city regions from the national value (REGISTERED).
  Examples: Valle d'Aosta 250 -> 48.5 kg N/ha (required cut 70% -> 26%), Piemonte 216 -> 97, Luxembourg 235 -> 157
  (68% -> 49%), Swedish regions ~100 -> 70-79, Romania RO31 -89 -> 27. The nine capped regions are unchanged.
- Catch crops: CAPRI's winterCover_ row adds the landscape rule's fallow floor to the area that can carry a catch
  crop (supply_model.gms: "in case fallow land is expanded only to meet the set aside target, take out from the
  calculation, otherwise we can easily end up with negative values and infeasibilities"); the model did not. Where the
  floor fills most of the arable land (Tyrol: 22 kha floor on 14 kha of arable land; Bolzano, Trento, Corsica,
  Salzburg) the floor and the catch-crop minimum could not both hold, the land-market solve failed and the fallback
  emptied the regions' grassland and herds (Tyrol dairy cows 68 -> 3, Bolzano 60 -> 0).
- An unreachable landscape floor is now relaxed inside the land-market problem (`_fit_aug_row`) instead of dropping
  to the plain problem, where land may idle. An unreachable N target still falls back (its least reachable surplus
  is an extreme corner); `land_market_failed`, the shortfalls and every constraint's dual are now in the run output.
- Farm-to-Fork 2030, gap to JRC121368 (20 indicators): default 5.89 -> **5.81**. CAPRI's land rules re-measured with
  the corrected targets: without manure trade 6.09 (11 regions above EUR 100/kg N: Swedish regions, FI1D, Madeira,
  Luxembourg, Brittany - farmland added from forest must be grazed, so cattle rise and poultry go); with the manure
  market 5.28, EU farmland +2.7% (CAPRI +3%; default -1.9%), no land-market failures. Defaults unchanged: JRC121368's
  CAPRI kept manure in its region, and the land rules alone are still worse than the default.

## Manure N2O by stage, with the technologies' effects (October 2026)

- Manure N2O follows CAPRI's gases.gms by stage: per t of manure N, housing and storage (N2OMAN), application
  (N2OAPP), grazing (N2OGRA) and leaching (N2OLEA) from CAPRI's 2017 results per region and animal (median 1.6% of
  manure N in all, against the flat 2% before), and indirect N2O from the manure NH3 (N2OAMM) as its own item. The
  ammonia technologies move them as in CAPRI (ammo_tech.gms: storage effects applied at housing level): covered
  storage cuts housing/storage N2O (-55 to -91% per adopting unit), low-emission spreading raises application N2O
  (+44%); inhibitors on manure cut application N2O (-36%). Data: `manure_n2o_factors.csv`, `manure_n2o_tech.csv`
  (`tools/build/build_manure_n2o.py`).
- 2030 Farm-to-Fork: manure N2O -27.1% (CAPRI -3.2; -18.4 with the flat factor); by stage housing/storage -36.5%,
  application -30.0%, grazing -16.7%. GHG total 391 Mt in the baseline (CAPRI 372), -22.5% (CAPRI -14.8); gap 5.81 ->
  5.89. CAPRI's own structure moves the model further from JRC121368 here: herds fall more than CAPRI's, inhibitors
  on manure are adopted on 41% of manure N, and without CAPRI's emissions by source the residual cannot be located
  further. Tests 66/66.

## GHG accounts: unit bug fixed, soil N2O by source, histosols (October 2026)

- **Bug fixed: soil N2O, liming and urea CO2 were 1000 times too small** (1000 ha x kg/ha divided by 1e6 gave Mt
  where every other gas is in kt), so the GHG total left them out: EU soil N2O 83 kt instead of 83 Mt. The
  "fertiliser N2O" indicator (a ratio) was not affected; the GHG total was.
- **Soil N2O by source, as CAPRI (gases.gms):** mineral N (N2OSYN: the balance's mineral N x direct + volatilised
  indirect factors; 52.9 Mt in the 2030 baseline), crop residues (N2OCRO: residue N x EF1; 43.9 Mt), histosols
  (N2OHIS; 13.2 Mt), manure (N2O_MAN, unchanged). Before, soil N2O was crops' total N need (16.6 Mt N, mineral and
  organic) rescaled by the mineral ratio.
- **Histosols** (`histosol.csv`, `tools/build/build_histosol.py`): organic-soil shares (p_OrgSoilOri), climate-weighted IPCC
  2013 factors (FAO land use 2000 by climate zone), and CAPRI's fallowing option (no_histosols.gms: idled histosol
  area still occupies its land; CAPRI's curvature from its calibration runs; linear term from the model's own base
  land dual). Fallowing stays ~0 under Farm-to-Fork (Table 17: 2% -> 9%): the model's land rents at base are a few
  EUR/ha (CAPRI's ~100), so the rent fall that drives CAPRI's adoption is absent.
- 2030 Farm-to-Fork: GHG total (now every source) 401 Mt in the baseline (CAPRI 372), -20.4% (CAPRI -14.8; -17.0
  before, without soil N2O); gap 5.73 -> 5.81. Manure N2O -18.4% against CAPRI's -3.2% is the largest source gap,
  now visible in `tools/check/compare_runs.py`. Tests 65/65.

## Sprint 7b - CAPRI's two dairy activities, DCOL and DCOH (October 2026)

- CAPRI models dairy cows as a low-yield (DCOL) and a high-yield (DCOH) activity, half the herd each at base, with
  their own milk, feed requirements, manure N, costs and PMP terms (Brittany: 5,357 vs 8,927 kg milk, 126 vs 212 kg
  N per cow). As for the grassland split, the model keeps DCOW and adds the cows moved from DCOH to DCOL as one column:
  manure rows (N balance, manure application, crop-need limit, mineral-N allocation) by the manure-N change, the
  cows' energy, protein and dry-matter rows in the conic feed block by the requirement changes, CAPRI's PMP terms
  (p_pmpQuadTechn), linear term calibrated on the base duals (the requirement rows' included), milk revenue under the
  current milk price; milk output, manure N2O and ammonia follow it. Data `dairy_intensity.csv`
  (`tools/build/build_dairy_intensity.py`).
- 2030 Farm-to-Fork: low-yield cows 50% -> 51.8% of the herd (321,000 cows); dairy cows -12.0 -> -11.7% (CAPRI -10);
  gap 5.72 -> 5.73 (5.68 in a first run that converged in 9 iterations instead of 13). Tests 64/64.

## Organic target: CAPRI's scaling; superseded country table removed (October 2026)

- The organic target already follows CAPRI: every EU member state takes CAPRI's percentage-point targets by crop
  group (organic_targets.gdx, organic_targets_UAA.gdx), which net out its existing organic area, applied uniformly to
  its regions as CAPRI does. A per-country table of 2018-2019 Eurostat organic shares, used before those targets were
  loaded, was no longer reached for any EU region: removed (the EU 10% remains as the only fallback).
- Scaling to a target other than 25% now uses CAPRI's (target - 12) / (25 - 12) instead of target / 25 (identical at
  25%, so the Farm-to-Fork results do not change).
- New sources, not yet used: `orgsoil_share` (p_OrgSoilOri, for histosol fallowing) and the Integrated Farm
  Statistics 2010/2020 by CAPRI region and activity, total/organic/conventional (`sources/ifs/`). The regional organic
  shares are not used for the target, because CAPRI does not use them.

## Items not yet modelled: first pass (October 2026)

- **Inhibitors on manure now work with the technologies inside.** CAPRI's nitrification inhibitors on applied manure
  (target N2OMAN) were applied only when the technologies were decided outside the regional model; with them inside
  (the default) they were skipped, so adoption was always 0. They are now decided at the region's N price in both
  cases (manure N counts x (1 + share x NMAN) toward crop need; cost per t of manure N as calibrated), with CAPRI's
  application NH3 side effect (p_litRevFertTechs NH3APP: +25% on treated manure, times (1 + NMAN), on the cascade's
  application loss). F2F: adoption 41% of fertilised area, **gap 6.41 -> 5.70**; ammonia -41.6 -> -38.5% (CAPRI -33),
  pork price +35 -> +29.5% (+43), poultry price +37.5 -> +32% (+18). Converges in 19 iterations (11 before).
- **Mineral-fertiliser side effects** of nitrification inhibitors (N2O -19%, NH3 +12% per kg N) in soil N2O and
  ammonia; GHG total now summed after the last soil-N2O adjustment (it missed the rescaling to the final mineral input).
- **Fodder values in 2030**: the fodder balance's base values take CAPRI's 2030/2017 fodder unit-value ratios (2017
  money; grass 0.43 in France). Together with the side effects: gap 6.13 -> 6.29.
- **Pesticide and organic targets on CAPRI's regional costs**: plant protection (PLAP x UVAG), other inputs and
  fertiliser per ha by region and crop replace EU-wide shares that rested on two member states. Gap 6.29 -> 6.41.
- **Coupled-support test**: CAPRI's 2030 pair (reference vs no voluntary coupled support) extracted; the model given
  CAPRI's premium changes reproduces CAPRI's response with a mean deviation of 1.23 points over 29 indicators
  (correlation +0.81). Largest gaps: suckler cows -2.1% (CAPRI -7.4), durum wheat area +0.2% (-6.8; Italy -10.6),
  pulses price +7.4% (+2.8).
- **CAPRI's mitigation calibration runs** (costsavings ini/max, v_Miti) extracted. Genetics: the ruminant-efficiency
  option is capped at ~0.2% in the installation's 2030 calibration and the milk-yield option is absent, so it is not
  built; low-N feed has 0 adoption in JRC121368's Farm-to-Fork; tillage acts on soil carbon only. Histosol fallowing
  needs p_shareOrganicSoil (requested). Winter cover crops: next.
- **Winter cover (catch) crops** under the Farm-to-Fork targets, as CAPRI's Green Deal files set them (organic_io.gms
  coverCrop 50% x organic target; conventional_io.gms pesticide cut / 2 on the remaining target): minimum catch-crop
  area = [0.5 o + 0.5 max(0, r - o)] x (UAAR - area under winter cover) + baseline catch crops; CAPRI's winterCover_
  row (winter-covering crops <= UAAR - catch crops); their N (BioFix = p_cInput / 24 x 0.75 x 0.5, 29 kg N/ha median)
  enters the balance as fixation and supplies crop need (mineral N falls by as much), with residue N2O. Data:
  `cover_crops.csv`, `winter_cover_share.csv` (`tools/build/build_cover_crops.py`). REGISTERED: CAPRI subtracts winter
  cover with the shares as given (NUTS2 entries for Austria and a few German regions only), which puts the
  requirement above the area that can carry a catch crop in 100 regions; the filled shares are used in both. F2F:
  catch crops 16% -> 41% of the eligible area (JRC121368 Table 17: 23% -> 32%), fertiliser N2O -44.4 -> -46.1%
  (CAPRI -40.4), gap 5.70 -> 5.72. Catch-crop costs are fixed per region and do not change decisions.
- Tests 63/63.

## CAPRI's land rules as default: not yet; manure pools fixed under them (October 2026)

- Fixed: with CAPRI's land rules and the manure market, the pools never cleared (Latvia "1.0"): the pool equilibrium
  QP failed silently in Clarabel (pool prices of hundreds of EUR/kg N against slopes differing by orders of
  magnitude), and a failed solve kept the old prices. The QP is now scaled, Clarabel's AlmostSolved is accepted (the
  realised clearing is tested anyway) and a failure shows in the trace. Land rules + manure market: converged in 9
  iterations, **gap 5.03** (best so far; manure market alone 5.23).
- Land rules without manure trade (the JRC121368 setup), current code: gap 7.52 against 6.13 by default. 15 regions
  reach nitrogen prices above EUR 100/kg (4 by default): Brittany and Lombardy (pigs and poultry vanish), and also
  Luxembourg, Valle d'Aosta, three Swedish regions, FI1D, Madeira, where farmland grows 30-45% from forest
  and other land (the per-current-hectare target makes each added hectare worth target x N price) and herds swing
  to sheep. Land rules stay off by default until these are understood. Details in docs/COUPLING_SPRINTS.md.
- Sensitivity option `tools/run/run_f2f_2030.py --capped-regions` (model setting `jrc_capped_override`, carried to the
  projected model): which regions get JRC121368's 36% cut. Brittany and Lombardy added to the nine: land rules 7.52
  -> 5.34, default 6.13 -> 5.53. No caps at all: land rules 10.44. Not a default: the report does not name the nine.
- Tests 62/62.

## Manure trade, Norway, pool convergence (October 2026)

- Fixed: EU policy instruments (surplus target, organic, pesticides, landscape, nitrate limits) were applied to Norway;
  CAPRI's Green Deal files restrict them to EU27yr19. Default gap 6.33 → 6.13.
- Fixed: manure pools stopped clearing once feeding moved inside the supply models (trade schedules from duals of a
  QP that lacks the feed block); they now use the conic solve's multipliers: pools clear in 10 iterations.
- Found: CAPRI's Green Deal reference in the installation runs with the new manure trade module on. With the manure
  market: gap 5.23, pigs −13.7% (CAPRI −14.5), beef price +24.0% (+24), manure CH4 −11.8% (−12.2). Off by default:
  JRC121368's CAPRI had no manure trade (report sect. 4.3.4, a stated limitation); the market is for today's CAPRI. With CAPRI's land rules too, the Latvian pool
  did not clear on the full EU (fixed in the entry above).
- Trace: pool imbalance, worst pool and EU conservation in the outer-loop trace. Tests 62/62, anchors 8/8.

## Sprint 7a — CAPRI's extensive and intensive grassland (October 2026)

- CAPRI's GRAE/GRAI split as the grassland area moved from intensive to extensive (one column per regional model):
  N balance by CAPRI's per-activity removal, residues, fixation and need-based mineral rate (the accounts use the same
  function), grass fodder by the yield difference, mineral need, CAPRI's own PMP terms (p_pmpQuadTechn), linear term
  calibrated on base duals. Data `grass_intensity.csv` (`tools/build/build_grass_intensity.py`).
- 2030 Farm-to-Fork: gap 6.71 → 6.33; idled area −7.5 → −2.9%, grassland −17 → −5%; N price median €10.5 → 6.1/kg;
  pork price +47.5 → +35.0% (CAPRI +43), poultry price +49 → +38% (+18). With CAPRI's land rules the model now
  converges (12 iterations; before: not converged, gap 21.5): gap 7.66, farmland +3.9% (CAPRI +3%); Brittany and
  Lombardy remain extreme (pigs and poultry vanish). Land rules stay off by default. Tests 62/62, anchors 8/8.

## World prices and Armington parameters: one commodity set (October 2026)

- `armington_params.csv` (39 rows) and `world_prices.csv` (43 rows) differed by four price-only rows: SOYA_OIL and
  SOYM, older names duplicating SOYO and SOYC at the same CAPRI prices, and WMLK, CREM (whole milk powder, cream),
  dairy products outside the market set. No module read them (the biofuel module used `SOYA_OIL` only as a key of
  its oil-yield table, now `SOYO`). Removed as orphans: both files now hold exactly the market module's 39 traded
  commodities (`definitions.MARKET_COMMODITIES`); provenance of the removed rows kept in
  `sources/world_price_provenance.json`. Data dictionary and manifests corrected (they gave 32 and 37 rows).
  Validator 12/0/0, anchors 8/8, tests 61/61.

## Supply QP solver: Clarabel leading (October 2026)

- `CAPRIModel.qp_solver` defaults to `"clarabel"`; the built-in active-set + least-distance chain stays as the
  automatic fallback (Clarabel missing or not solved) and as the comparison backend (`qp_solver = "builtin"`,
  `tools/check/compare_qp_solvers.py`). Regional models with feeding inside were already conic and solved by Clarabel.
- Comparison, full EU baseline + Farm-to-Fork (2017 base), each backend in its own process: world prices agree to
  5e-5, N surplus/NH3/enteric CH4 to 2e-5, 11,160 activity levels to a median 5e-6 (largest 3.4% on a 0.9 kha
  activity), same run time (681 vs 701 s). 2030 Farm-to-Fork: all indicators within 0.3 points, gap 6.68 → 6.71,
  converged in 14 iterations (12 with builtin).
- `test_projection_null_trajectory_reproduces_base` now builds a fresh model for its reference run: the session
  model's state from earlier tests let the outer loop converge from a different point (1e-6 apart under Clarabel);
  the 1e-9 identity holds from equal states. Tests 61/61, anchors 8/8.

## Sprint 6a — CAPRI's 2030 prices in the baseline (October 2026)

- The 2030 baseline takes CAPRI's 2030 reference prices and premiums in 2017 money: unit-value ratios over CAPRI's
  input index (1.277, all member states) for crop prices, livestock product values by market, young animals and
  feed cereals; CAPRI's 2030 PRME for premiums (`tools/build/build_price_trajectory_2030.py`,
  `capri_mod/projection/prices.py`; `--base-prices` restores 2017 prices).
- CAPRI's Farm-to-Fork reference (`refpol_endotech_all_ini`, `_max`) extracted: per-activity marginal terms and
  2030 unit values (`tools/build/extract_capri_marginal_terms.py`, validation only).
- Prices checked against CAPRI's own 2030 baseline (`p_uvagStore`: identical); oilcake prices from the market baseline.
- 2030 Farm-to-Fork: gap 6.91 → 6.68; pork price +47.4% (CAPRI +43); poultry price +48.9% (+18); nitrogen prices
  unchanged. Tests 61/61, anchors 8/8.

## Sprint 5 — pig activities and product values (October 2026)

- CAPRI's sows (`PIGS`) and fattening pigs (`PIGF`) replace the single pig activity; all pig coefficients rebuilt
  from `res_17*` (`tools/build_pig_split.py`); piglets clear on the young-animal market; `YPIG` elasticity wired;
  sows' protein-feed limit 30% (CAPRI).
- Defect fixed: a meat price moved CAPRI's `MREV`, which for sows, raised calves and replacement heifers is
  young-animal sales (double-counted with the young-animal markets) and for suckler cows a quarter of their beef.
  Revenue now moves by final-product quantity × price change, per market (`livestock_product_value_by_market_coef.csv`);
  the same value share weights livestock elasticities. Sow response to +5% pork: 0.55–0.63 → 0.10–0.12.
- 2030 Farm-to-Fork: gap 6.75 → 6.91; beef animals −14.5% (CAPRI −18), beef production −14.4% (−14), pigs −28.5%
  (−14.5). Tests 61/61, anchors 8/8.

## Sprint 3 — land rules (October 2026)

- Land market: total land conserved (equality); no-idle-land rows at base use, capped at the row limit; the
  rent-elasticity land expansion is off where the land market solves under no-idle-land. Default results
  unchanged (6.75); CAPRI's rules converge without the current-hectare target but raise nitrogen prices
  (docs/COUPLING_SPRINTS.md).

## Sprint 4 — feeding inside supply on by default (October 2026)

- `tools/check/validate_gnb_eurostat.py`: base balance against Eurostat's gross nutrient balance by member state
  (mineral 0.99, manure 1.14, pig manure 1.76 — CAPRI's own pig coefficients, as JRC96482 found).

- `use_feed_in_supply = True` (model and supply module); `run_f2f_2030.py --no-feed-in-supply` for the old path.
  Farm-to-Fork average gap 7.69 → 6.73, converged in 12 iterations; anchors and tests unchanged.

## Sprint 2 (in progress) — manure value (October 2026)

- `EnvironmentalModule._manure_marginal_factor`: mineral N replaced per unit of manure N at CAPRI's marginal
  availability under `endoManAvFact` ((g0 + b m0) / mineral efficiency, b = −0.0015 flattened as in
  `fert/endoManAvail.gms`), from the reference run's per-region deliveries; the minimum-floor reduction removed.
- `tools/build/build_capri_gnb_components.py`: also extracts `fertDist_excr/mine_perha`,
  `nutNed_excr_unavailable_perha`, `nutNed_mine_loss_gasRunTot_perha`.
- Farm-to-Fork average gap 7.66 → 6.77. Land rules tested (docs/COUPLING_SPRINTS.md): not adopted yet.
- Legume removal on CAPRI's gross need (NITF + fixation; JRC96482 eq. 1): soya −66 → −33%, soya price +96 → +29%.
- Market: adaptive damping of the EU Armington premium between outer iterations (eggs cycled).
- `tools/diag_n_abatement.py`: nitrogen-target abatement by channel and shadow price for one region. Diagnosis:
  supply elasticities and target sizes match CAPRI; CAPRI's own options remove about a tenth of a livestock
  region's surplus even at maximum; CAPRI's Farm-to-Fork scenario results (surplus-constraint duals) are needed
  to tell lower prices from smaller regional cuts.

## Sprint 1 — gross nitrogen balance on CAPRI's definition (October 2026)

- `environmental_module`: per-crop removal, residues and fixation from CAPRI's 2030 coefficients
  (`capri_crop_n_coefs_2030.csv`, `capri_gnb_components_2030.csv`); residue credit at CAPRI's availability,
  arable pool distributed by need, own residues for grassland and permanent crops; manure cover distributed by
  need (removal net of fixation); `__credit__` factor so fertiliser technologies scale mineral N net of credits;
  organic factor on the mineral rate only.
- `supply_module` N row: crop coefficients are the crop's own balance at current yields and factors (exact
  agreement with the accounts); animal coefficients at the technology factor.
- `model.py`: per-commodity adaptive price damping; `trace_outer` (carried to projected models) prints the
  outer-loop trace (`run_f2f_2030.py --verbose`).
- `compare_runs.py`: cereal and oilseed price indices weighted by base production value.
- Regression anchor `n_surplus_median_kg_ha` 60.9 → 87.6 (explained in the anchor file: output side now matches
  CAPRI, the gap is 2017 inputs against CAPRI's 2030 projection).
- Farm-to-Fork average gap 4.6 → 7.7 (see docs/COUPLING_SPRINTS.md for why, and Sprint 2).

## New capability

**Projection layer (`projection/`)** — versioned trajectory input with mandatory
provenance, weighted least-squares reconciliation, recursive loop, and baseline
drift reported separately from the policy increment. Driven by CAPRI's own
`captrd` baseline. Two correctness properties hold: a null trajectory reproduces
the comparative-static result **exactly**, and the projection reproduces CAPRI's
independent 2030 reference at +0.997.

This changes what the model *is*: it is no longer purely comparative-static, and
the README description was updated accordingly. Three caveats bound the claim —
validation covers a **single step** to 2030, not multi-period recursion; only
**perennial areas** are carried between periods, so herds are re-optimised each
period and livestock adjustment speed is overstated; and the trajectory is
**exogenous**, adopted rather than generated.

**Nitrogen intensity margin (`supply/intensity.py`)** — N per hectare is now a
decision variable with a Mitscherlich yield response, normalised so the base
year is reproduced exactly. Without it a nitrogen constraint could only cut
*area*, overstating the response roughly tenfold.

**Farm-to-Fork instruments** — all four CAPRI targets are now representable:
landscape elements (a fallow floor, as `landscape.gms` does it), organic area
share (I/O adjustment, as `organic_io.gms` does it), the tiered nutrient-surplus
rule, and the pesticide yield-loss channel.

**Base-year reconciliation (`data/reconcile_base.py`)** — reproduces CAPRI's
`coco`/`capreg` step: weighted least-squares projection onto accounting
identities, the same Highest Posterior Density family CAPRI uses. Reconciling
already-consistent data changes it by 9.09e-13 (machine precision), the gate that
catches a reconciler which rewrites rather than reconciles.

Tested against the three area vintages in `capri_data/archive/` — a Eurostat-derived
matrix (107,828 kha), COCO-reconciled (125,775), CAPRI final (144,719). It closes
**32%** of the distance. **That test is weaker than it first appears**: the
"Eurostat" file is already mapped to CAPRI activity codes, and 35% of its values
carry repeating decimals, so it is share-allocated rather than measured regional
data. It measures recovery of regional detail from allocated totals, *not* whether
raw Eurostat can be turned into CAPRI data — which remains untested. **The residual is definitional, not a
reconciliation failure**: GRAS alone is 18,393 kha of it (Eurostat 13,640 vs CAPRI
44,819 — different grassland definitions), OLIV 1,884 vs 4,808, and CORN runs the
other way because Eurostat's maize includes silage.

That splits a problem previously treated as one: **reconciliation** (making numbers
internally consistent) is now solved and ours; **concordance** (mapping external
statistical categories onto CAPRI activities) is separate and, on this evidence,
larger. Conflating them is why "just use Eurostat" looks easier than it is.

**Yield-price response** — yields now move with own price, as CAPRI's stage-one
decision does (*"updated depending on price changes against the baseline"*,
documentation ch. 5). Previously a price shock moved area only, a pure extensive
margin that understated supply response. `YIELD_PRICE_ELASTICITY = 0.15`, a
short-run literature value, exposed rather than buried. At an unchanged price the
factor is exactly 1.0, so base fidelity is untouched (0.47%, 248/248 converge).

**NUTS version correspondence** (`capri_data/shared/nuts_version_correspondence.json`)
— 184 CAPRI region codes mapped across NUTS scheme versions, extracted from
`build_general_set_structure.gms`. CAPRI's result files use *old numeric* codes
for member states that changed scheme (`IT110000` where NUTS-2016 says `ITC1`), so
every Italian validation lookup had been matching **zero** regions and silently
returning nothing. Spain was unaffected because its codes are numeric in both
schemes — which is why the gap survived until Italy was tried. Not in the
published documentation: the Annex Code Lists map items, not regions.

**Water demand (`water/`)** and **farm-income distribution (`income/`)**.

---

## Defects fixed

Every one was surfaced by an **external reference**, not by an internal
consistency check. That is the single most useful lesson in this log.

| Defect | Effect |
|---|---|
| **CAP support double-counted** | The calibrated net revenue already contained `cap_premium`, and the solve *added* the absolute payment on top — ~29% supply inflation in **every scenario ever run**. The same inflation sat in the baseline, so scenario-vs-baseline comparisons were measuring the double-count rather than the policy. Adders now pass as a delta, ending the double-counting |
| All policy instruments inert | Scenarios returned baseline numbers while reporting success — four separate causes |
| Nitrogen balance meaningless | Median −170,196 kg N/ha, from a grass fresh-matter artifact and a manure-N scale error |
| Permanent crops destroyed | Olives 78% error in every base solve; invisible to a fidelity measure that only checked annual crops |
| **Arable land bound cut the base year** | **Base fidelity 11.28% → 0.47%.** ARABLE land and crop areas disagreed in 54 of 248 regions by 9,960 kha (LT02 12.7x); the solver shed 9,976 kha, losing most cereals in those regions. Not solver noise — a data conflict, and fixable |
| Grain maize silently excluded | `MAIZ` (not an activity) listed instead of `CORN` in three modules — fertiliser group, pesticide target, abatement N₂O |
| **Grass unit fixed at source** | CAPRI reports grass yield as fresh matter in kg/ha; every other crop is t/ha. The raw value caused the same defect **five times** — 99.3% of nitrogen uptake, 99.9% of gross margin, 4.5 bn kt of grass output — each patched where it surfaced. Now converted once at load time, five patches removed, results identical. Exposed a sixth dependency: the fertiliser module's plausibility guard had been silently dropping grass *because* of the bug |
| **Livestock output was not a product** | `gross_output` used CAPRI's `YILD`, which for breeding and suckler activities measures offspring or liveweight, not a marketed product — one region reported 3.9 billion tonnes of pig. Now built from CAPRI's final-product items (milk, beef, pork, poultry, eggs, sheep and goat) for all 27 member states plus Norway; EU totals match real 2017 production within 0.94–1.08. Building it hit five traps, including a region pattern of mine that silently dropped every letter-coded region |
| **Ireland: no livestock, and placeholder land** | Herds were absent (CAPRI's two NUTS-2013 Irish regions don't map onto NUTS-2016's three), and adding them exposed that Irish crop areas, yields and costs were synthetic placeholders — maize, sunflower and sugar beet Ireland doesn't grow, on 15% of its real land. Rebuilt from CAPRI using a Eurostat table that lists Irish cattle under both region schemes, which fixes the split exactly. EU livestock output now equals CAPRI's EU27 total to the tonne. Irish grass yield is still a placeholder |
| **Base data rebuilt from CAPRI for every region** | It had been a template overwritten by CAPRI only where a code matched: ~3.5 Mha of placeholder crops, 100 of 248 regions with no CAPRI source (all of France, Greece, Sweden, much of Italy and Poland), and two whole categories missing — fodder on arable land (14.3 Mha) and fallow (5.5 Mha). Poland was counted twice (21 rows for 17 regions); Ceuta, Melilla and Brussels held 1.6 Mha of phantom farmland. Now one tool builds all 248 regions; every country within 0.93–1.03 of CAPRI's own agricultural area. EU wheat production 113.6 → 126.6 Mt (real ~130); grain maize 91.7 → 66.5 Mt (real ~65) |
| **Table olives mapped, grass yield resolved** | CAPRI separates olives for oil from table olives (307 kha); both are olive groves, so EU olive area now reads 5,010 kha against a real ~5,000. Separately, the model's grass yield had no verified basis against CAPRI — because CAPRI has none: its grass price is a dummy 1000 EUR/t and its grass "yield" equals revenue, so it is a value construct. The model's 4.64 t DM/ha median is plausible on its own terms |
| **Paddy rice added** | A documented CAPRI activity the model lacked: 427 kha EU-wide, concentrated in Lombardy, Piedmont and Andalucía. Now the 30th crop activity |
| **Fitness for use, in machine-readable form** | Every other data file records where an *input* came from; nothing recorded how far an *output* could be trusted except README prose. `FITNESS_FOR_USE.json` declares 19 outputs with a status (`validated`, `use_with_care`, `overstated`, `not_supported`), and `capri_mod/fitness.py` queries it with fallback from specific to general. An unrecorded key returns `unknown`, not `validated` — silence is not a clean bill of health. Writing it caught two stale README claims: farm income described as contaminated after being fixed, and permanent crops as under-responding when they now overshoot |
| **CAPRI's over-fertilisation limit on fertiliser technologies** | Fertiliser-efficiency technologies can now only remove over-fertilisation, as in CAPRI (`Tot_MitFert_` and the regional maximum shares of `envind/ghgMiti.gms`), using CAPRI's regional factors (`p_CropNutNeedMultFact`, 2030). Before, they could "save" any fertiliser, so moderate-surplus cattle regions met the nitrogen target almost for free and expanded their herds. 2030 Farm-to-Fork: dairy cows −5.4 → −8.4%, enteric methane −7.4 → −10.5%, beef price +6.1 → +11.1%; average gap from CAPRI 5.5 → 4.5 points |
| **Fertiliser options on CAPRI's jul15 data** | The Green Deal runs use `miti_data_jul15`; the model's table came from `tdev`. From jul15 (supplied by the project lead): VRT_SRUC added (regional cost curves), NITR_INH with CAPRI's QEmitt = 0.9 × no control (NMIN 0.09, not 0.48) and its over-fertilisation cap, maximum share 0.56–0.66; inhibitors on applied manure (N2OMAN) activated (wrong lookup key). Precision farming + VRT 9 → 22% (CAPRI 35%); average gap 4.31 → 4.46 |
| **Livestock curvature on the margin's basis** | Livestock margins use CAPRI's total output value (TOOU) but the PMP curvature still used market revenue (MREV); suckler cows (MREV €68, TOOU €620 per head, mostly calves) were about nine times too responsive, growing +22% where the nitrogen price stayed low. Curvature now on TOOU; commodity prices move only the market part of revenue; cattle elasticities value-weight product and young animals (CAPRI's 2020 calibrated YCAM…YCOW; the 2017 file holds dummies of 1). Ireland added to the young-animal data (national-code bug). Beef price +12.7% (CAPRI +24), beef production −7.6% (−14), average gap 4.31 |
| **Livestock supply elasticities from CAPRI** | Every animal activity was calibrated to a hard-coded literature elasticity (0.10–0.25) in all 248 regions; CAPRI's calibrated product supply elasticities per member state (elas_2_1717, already in the project: milk 0.47–0.58, beef 0.65–0.70, pork 0.57–0.72, poultry 0.71–0.79, sheep 0.82) now replace them. +10% beef price: bulls +1.7 → +4–7%. Pork price +21 → +32% (CAPRI +43), pigs −18.9 → −22.5% (−14.5) |
| **CAPRI's young-animal markets** | Calves, young cattle and replacement cows are bought and sold by the cattle activities at EU prices that keep each good's EU net balance at the baseline level (CAPRI `yaniMarket_`); damped Newton update from the regions' PMP matrices. Coefficients rebuilt per model head (CAPRI regional flow / model heads): per CAPRI head they gave EU base balances far from CAPRI's. On by default; calf price +35% under Farm-to-Fork; converges in 10 iterations |
| **Beef production reported** | EU beef production change added to the comparison (JRC121368: −14%); the model gives −5.5% |
| **Ammonia options on CAPRI's structure** | Housing, storage covers, air purification and acidification are alternative manure systems sharing one limit in CAPRI (`TotMit_`, NH3MAN); the model had treated housing and storage as separate stages, so both reached their maximum on the same animals. The cost curvature now follows CAPRI's calibration (`ammo_tech.gms`: relative subsidies, "VERSION B"); the model had none for application, acidification and poultry/sheep options, so they jumped to their maximum. Losses now cascade from house to storage to field, with CAPRI's combined pig/poultry options and the −80% storage effect of low-emission housing. Table 17 adoption: housing 66 → 19% (CAPRI 12), covers 61 → 36% (34), air purification 31 → 14% (10), acidification 46 → 1%, spreading above 100% → 73%; ammonia −37.7 → −34.9% (CAPRI −33) |
| **Fertiliser options: CAPRI's active set and cost basis** | CAPRI's Green Deal reference (`refpol_endotech_all_sup.gms`) activates precision farming, VRT_SRUC, timing and inhibitors only; the model also offered the GAINS combinations and VRT_L/M/H, which took the over-fertilisation room. Costs are per tonne of crop N need in CAPRI's cost equation; the model charged them per hectare (about ten times too much). Calibration as CAPRI (relative subsidies 1.2/0.2, or 0.8/0 where the regional maximum is below 1). Precision farming 1.5 → 9% (CAPRI 35%); VRT_SRUC not in the project's data |
| **Table 17 comparison basis** | CAPRI's baseline column matches its initial shares as shares of all animal units weighted by excreted N, not of eligible units; the old comparison multiplied CAPRI's figures by the eligible share. Reports now show baseline and scenario on that basis |
| **Land-convergence test assertion** | `test_land_supply_converges_resets_and_is_inert_at_base` failed whenever the first land update was exactly zero (hash-seed dependent, e.g. `PYTHONHASHSEED=3`), since land is now settled within each iteration; the assertion allows rounding noise |
| **Land market: CAPRI placeholder matrices ignored** | CAPRI's land-market data carries default values (100 / −5) for unused aggregate codes. One of them had been taken as the parent of four Polish NUTS 2021 regions, giving them land-market curvature 100,000 times their neighbours'. They now use Poland's national matrix scaled by their share |
| **Fodder balance includes all grass-eating animals** | The fodder-balance builder read the raw head counts, whose names for suckler cows, heifers and sheep (SCOW, HEIF, SHGO) differ from the model's, so those animals were silently left out of every fodder balance and their fodder tied to no land. Fixed with one shared name map. Under Farm-to-Fork, suckler cows are no longer cut disproportionately (−18.8% instead of −28.9%) and dairy cows fall more (−5.4%) |
| **Livestock margins on CAPRI's basis** | Livestock revenue and costs are now both CAPRI's regional totals (total output and total inputs) divided by the model's head counts. Costs used to be per-head values on CAPRI's own head basis, so bulls and heifers showed margins near 90% of revenue (CAPRI 10–34%). Base unchanged; Farm-to-Fork results move little, because in PMP the response depends on curvature, not on the base margin |
| **Ammonia technologies in all regions** | 33 regions whose NUTS 2021 codes have no regional CAPRI entry (Ireland, parts of Poland, Croatia, Lithuania and others) were missing from the technology table; they now take their country's national values, the model's registered rule for such regions |
| **Clarabel available for all quadratic programs** | `CAPRIModel.qp_solver = "clarabel"` makes the regional supply models and feed rations use Clarabel's interior-point method, with the built-in solver as fallback. Default stays `"builtin"`: in the full comparison Clarabel solved every problem but the model did not converge with it (25 iterations, 654 s vs 7 iterations, 242 s), because parts of the code re-detect binding constraints from the solution; switching them to Clarabel's own multipliers comes first |
| **Markets solved with a Newton-type method** | Market equilibrium prices are now found with SciPy's `root` solver on the same excess-demand equations, as CAPRI solves its market model as a system of equations. Markets now clear to 10⁻¹³ or better instead of 1%; the 2030 Farm-to-Fork run needs one outer iteration fewer and takes about 200 s instead of 250, with results unchanged within 0.2 points. The previous method stays as automatic fallback (`market_solver = "tatonnement"` to force it) |
| **`requirements.txt` restored** | The README's `pip install -r requirements.txt` pointed to a file that was not in the project. It now exists, matching `pyproject.toml` (pandas, NumPy, SciPy) plus Clarabel, the optional solver for the manure-market pool equilibrium |
| **CAPRI's ammonia technologies, on by default** | CAPRI's ammonia technology table rebuilt from its code and data (costs, initial and maximum shares matching CAPRI's own runs, emission effects); farmers adopt housing, storage and spreading measures under the nitrogen price, as in CAPRI's Farm-to-Fork run. 2030 Farm-to-Fork ammonia now falls 34.4% (CAPRI 33%) and pigs 14.4% (CAPRI 14.5%). Also fixed: a region whose environmental indicators failed was dropped silently; it now raises a warning |
| **Nitrogen target as CAPRI applied it** | JRC121368 states that for the nine regions with the highest nitrogen surplus the tiered target was infeasible and was set to the EU average cut (36%). The model now does the same (Belgian and Dutch livestock regions and Malta). Pigs now fall 15.7% under Farm-to-Fork (CAPRI 14.5%), the pork price rises less |
| **Two documents moved to `docs/`** | `DATA_FIXES.md` and `PMP_ELASTICITY_WIRING.md` now live in `docs/` with the other design and history notes; the documentation check follows the new path |
| **Documentation brought up to date** | All Markdown files reviewed: status lines and results updated in `docs/` and the README, a design note added for the manure market (`docs/MANURE_MARKET.md`), this period's fixes added to `docs/DATA_FIXES.md`, new data files to the data dictionary. `INIT_GIT.md` and `CAPRI_REFERENCE.md` removed |
| **Manure market finished; default stays off on evidence** | CAPRI's per-hectare-of-current-land surplus is now a setting (`surplus_per_current_ha`). Scored against twenty JRC121368 indicators, the default model (manure market off) is closest to CAPRI (mean deviation 4.4 points, against 6.5 with the market on, with or without the per-hectare form). The market improves herds and environmental results but overshoots crops, so it remains an option (`use_manure_market`), documented with that limitation |
| **Manure market converges fast (quasi-Newton)** | Each country pool's price response is corrected with what its regions actually did the previous iteration. The full 2030 Farm-to-Fork with the manure market now converges in 17 iterations, under 5 minutes in total. Sheep, pigs, the beef price and greenhouse gases are close to CAPRI; crop prices still overshoot. Off by default |
| **Silent fallback found and fixed; crop-need limit added** | Regional models had no access to the environmental module, so the manure market silently used a cruder substitution factor (North Brabant 0.20 instead of 0.03) and CAPRI's manure-within-crop-need limit, newly added, was skipped. The module is now passed to every regional model and fallbacks warn. Market results since the substitution fix need re-running. Off by default |
| **Full-EU manure market converges** | With adaptive price steps and up to 60 iterations for market runs, the full 2030 Farm-to-Fork with the manure market converges in about 10 minutes (every pool within 3%, 0.6% of EU manure unaccounted). Pigs, sheep, beef and poultry prices and greenhouse gases are close to CAPRI; crops overshoot. Off by default |
| **Full-EU manure market: faster, nearly converged** | A run may now stop only when every pool clears and no manure is unaccounted EU-wide. The full 2030 Farm-to-Fork with the market on takes 7.5 minutes (was 23) and ends within 4.3% of clearing after 40 iterations. Pig, sheep, beef-price and greenhouse-gas results move close to CAPRI's, but crop prices overshoot; provisional until it converges. Off by default |
| **Manure pool prices from the solver's shadow prices** | Each country's manure price is now the exact shadow price of its pool balance, so pools whose regions are not trading no longer keep stale prices. On the full EU, the worst pool imbalance falls to 6% within six iterations (Malta, Cyprus and the Baltic pools no longer lag) |
| **Interior-point solver for the manure market** | The country-pool equilibrium is now solved with a Newton-type interior-point method: Clarabel when installed (`pip install clarabel`, optional dependency `solvers`), otherwise a built-in equivalent. On the full EU it now solves at every iteration, and manure lost in uncleared pools fell from 2.4 million tonnes of nitrogen to 30 thousand. Small island and Baltic pools still lag. Off by default |
| **Manure market: exact substitution and fertiliser floor** | Traded manure now uses the balance's exact substitution factor, and counts in full where a region already uses no mineral fertiliser. With the market on, every region's reported surplus matches what it meets (all 105 test regions on target) |
| **Manure market rebuilt on the existing substitution** | The nitrogen balance already lets manure replace mineral fertiliser with CAPRI's availability factors; the separate fertiliser allocation counted that twice and has been removed. Traded manure now enters both the regional models and the reports the same way, and the reported surplus matches what each region meets (median ratio 1.000). Off by default until the full-EU run is validated |
| **First full-EU run with the manure market** | The 2030 projection now carries the market settings. The first full run took about 14 minutes and did not converge within 25 iterations; its results are not usable yet, and the reported nitrogen balance appears not to include the traded manure. Off by default |
| **Manure-market tolerance is a setting** | `CAPRIModel.manure_pool_tolerance` sets how closely each country's manure pool must clear before a run may stop, as a share of its manure supply; the default is 3%. It only applies when the manure market is on |
| **Manure market convergence tuned** | Longer price steps while far from clearing, damped steps once close: the pool imbalance falls below 10% in 7 iterations and keeps falling without oscillating (2.8% after 25). Results are already stable at that point (pigs −18%, cattle −19% across the six test countries) |
| **Manure market now clears steadily** | Solved on the shipment side with the model's own solver, the connected manure market converges steadily (pool imbalance 95% → 3% over 25 iterations) with prices moving together across countries. It needs more iterations to reach full clearing; off by default until then |
| **Manure market: exact clearing in progress** | The connected manure market now prices on each region's exact willingness to export or import, and two bugs found on the way were fixed. The price solve itself does not succeed yet, and the convergence check must require every country pool to clear. Off by default |
| **Manure market: imports do happen; price search still to fix** | Regions do import manure once the pool price covers their own nitrogen target and fertiliser saving (about €6–20 per kg of nitrogen, because the target binds everywhere); an earlier statement that none imported was wrong. The connected price search still does not converge, because regions switch abruptly between importing and exporting. Off by default |
| **Cross-border manure market built, not yet clearing** | CAPRI's 34 country pools are connected at its distance-based costs, and prices across countries now move together. But in testing no region imports manure, so the market does not clear and its results are not usable yet; the cause (importers' own nitrogen targets or the manure-application limit) is next. Off by default |
| **Cross-border manure: CAPRI's design found** | CAPRI's manure market has one pool per country, with every pair of countries connected at a transport cost (about €0.70 per kg of nitrogen for 300 km). That is how the Netherlands and Denmark place manure abroad. Distances come from a CAPRI data file, requested |
| **National manure market added (off by default)** | Regions can now trade manure within their country, with manure replacing fertiliser in importing regions. Tested on France, Italy, the Netherlands and Denmark: Brittany's pig cut under the nitrogen target falls from 49% to 5% and Lombardy's from 62% to 28%, as manure goes to regions that can use it. Dutch and Danish regions still cut heavily, because CAPRI's exports of manure out of the country are not yet modelled |
| **Fertiliser allocation implemented, off until the manure market joins it** | CAPRI's fertiliser allocation (manure replaces mineral fertiliser) is in the regional model behind a switch. Tested on its own it makes herd cuts less effective per head, so pig regions cut more — CAPRI's own economics; the relief in CAPRI comes from the manure market that substitution makes work. It stays off until that market is added; default results unchanged |
| **Fertiliser allocation: first attempt reverted** | The first implementation of CAPRI's fertiliser allocation moved results the wrong way (pig and cattle cuts became larger, not smaller), most likely because the nitrogen row's crop terms already include a fertiliser-intensity response that the allocation double-counts. Reverted; CAPRI's fertiliser prices kept for the redesign |
| **Root cause of the nitrogen-target problems found** | CAPRI allocates fertiliser inside its supply model: crops' nitrogen need is covered by manure first and mineral fertiliser makes up the rest, so manure replaces fertiliser. In the model, fertiliser per crop is fixed whatever manure is available. That is why manure trade cannot work, why shadow prices reach €30–80 per kg, and why pig regions abandon land or halve herds. Next: CAPRI's fertiliser allocation in the regional model |
| **Excretion per animal is fixed in CAPRI too** | CAPRI's manure nitrogen per animal is a fixed coefficient; feeding changes it only through optional mitigation technologies. So that is not why its pig regions cope better. Next check: CAPRI counts manure net of gaseous losses in the surplus, possibly unlike the model |
| **Nitrogen target: land abandonment found** | Brittany's fertiliser rise is land expansion, not a bug. But in Lombardy, North Brabant and Ireland farmland falls by 24–44% under the nitrogen target: capping the total surplus on base farmland makes abandoning land a way to comply. CAPRI's per-hectare form avoids that, but triggered the opposite extreme here earlier; both trace to the very high nitrogen shadow prices in livestock regions |
| **Nitrogen target: regional pattern** | Under the nitrogen target alone, cattle fall 30–40% in Ireland and around 20–27% in western France, while extensive central French grassland regions barely move, meeting their small cut through fertiliser alone. Half of the EU cattle cut comes from ten regions. One oddity (Brittany's mineral fertiliser rises) is flagged for checking |
| **Farm-to-Fork decomposed by instrument** | Run one at a time, only the nitrogen target moves livestock (beef cattle −12.8%, dairy −7%, pigs −22%); landscape, organic and pesticide targets raise cereal prices but change herds by under half a point. CAPRI's organic target excludes grassland and fodder too, so the cattle gap lies in how the nitrogen target acts on cattle regions |
| **Livestock responsiveness verified** | Every livestock activity responds to its own price at exactly the CAPRI elasticity it was calibrated to (cattle 0.09–0.17, pigs 0.20, poultry 0.18–0.24, sheep 0.12). An old note saying ruminants were damped is outdated. The beef gap therefore comes from how Farm-to-Fork's instruments act on cattle |
| **Herd links tested again, priced; not the beef lever** | Young animals traded within each country at national prices, as in CAPRI, changed German cattle numbers by under 2 points under Farm-to-Fork. Reverted; the beef supply gap lies elsewhere, most likely in the damped response of ruminants already noted in the records |
| **Herd links: first attempt reverted** | CAPRI's young-animal balances were built for 232 regions and tried as fixed regional balances. The base stayed exact, but Farm-to-Fork stopped converging and cattle fell less, because cows, calves and fattening had to shrink together. CAPRI lets regions trade young animals; that trade is needed first. Data kept, model unchanged |
| **Beef price: market verified, gap is on the supply side** | CAPRI's EU beef quota is 95% full, but the model's tariff already equals CAPRI's out-of-quota cost at the margin, so a quota cap would add nothing real. With CAPRI's 18% beef herd cut, the model's own market gives about +28%, CAPRI's range; the gap is that beef supply falls only 7% here. Next: herd links |
| **Base demand no longer cut by tariffs** | Demand measured price changes against the base world price instead of the base domestic price, so every tariff-protected market started with demand cut by its tariff. EU beef demand was 17% too low, making the EU look like a large beef exporter and damping its price. Fixed; base results unchanged. Farm-to-Fork beef price +10.3% (was +4.8%; CAPRI +24%), pork +26.4% (CAPRI +43%), poultry +19% (CAPRI +18%) |
| **EU prices reported as farmers receive them** | Market results now report the EU producer price including the Armington premium (world price × tariff kept as `wedge_prices`); model behaviour is unchanged. Under Farm-to-Fork 2030, poultry, milk and vegetable prices now match CAPRI. Beef stays low because the EU beef base balance shows far more net exports than FAO's — the next fix |
| **Meat prices: mostly a reporting error** | The model already clears the EU market with CAPRI's Armington structure, and farmers respond to it, but reported EU prices left out the Armington premium. With it, poultry, wheat and milk prices match CAPRI under Farm-to-Fork and pork comes much closer; beef remains too low and rapeseed too high |
| **Why meat prices barely move: diagnosed** | Every region's price is the world price plus tariff, so an EU supply cut moves EU prices only as far as world prices. CAPRI gives each region its own producer price, with imports as imperfect substitutes (Armington). Design for adopting CAPRI's structure in `docs/ARMINGTON_MARKET.md` |
| **Ammonia: CAPRI's accounting replaces a proxy** | Ammonia was housing emissions plus a flat 10% for soils, so it could only follow herd numbers. It now uses CAPRI's own factors per region — the share of excreted nitrogen lost from housing, storage, spreading and grazing for each animal, and the share of mineral fertiliser nitrogen — so fertiliser cuts reduce ammonia too. Base totals within 6% of CAPRI's |
| **Surplus rule checked against CAPRI** | The model applies JRC121368's tiered nitrogen-surplus rule; the current CAPRI code applies a flat 50%. Applied mechanically, the tiered rule implies an EU cut of −37.5% and the flat one −50%, against the study's −33.5%, so the tiered rule (the study's) stays. It requires the densest regions to cut 76–88% of their surplus, which drives the pig overshoot |
| **Manure pool tested and set aside** | A national manure pool as in CAPRI clears, but only at prices of €58–98 per kg of N, because the regional nitrogen targets bite extremely hard in pig regions; outcomes were absurd, so it was reverted. Settling this needs CAPRI's own Farm-to-Fork scenario output |
| **Why pigs fall 22%: diagnosed** | Without the fodder equality, pig regions grew silage maize that was never fed, purely to absorb manure nitrogen — a loophole that had made pigs match CAPRI for the wrong reason. CAPRI's valve is manure trade through a national pool that must clear; that is the next module |
| **EU ration on by default; fodder balance as CAPRI's equality** | The feed ration is now on by default, as in CAPRI; Farm-to-Fork still runs in about 3 minutes, and the cereal price and production now match CAPRI's. The fodder balance enforces CAPRI's equality (production may not exceed use), so fodder areas follow herds. Open: pigs now fall 22% against CAPRI's 14.5% |
| **Land market on by default, as in CAPRI** | CAPRI's land-market terms are per hectare, the model's land in thousand hectares; with that factor the land-supply elasticities fall in CAPRI's range. The land market is now on by default, as CAPRI's is: two regions that had no feasible solution under Farm-to-Fork now solve properly, results move by about one point, and the full 2030 run takes about 3 minutes instead of 10–12 |
| **Licence changed to Apache-2.0** | The project is now licensed under the Apache License, Version 2.0 (previously MIT): `LICENSE` holds the full Apache 2.0 text, a `NOTICE` file carries the copyright line, and `pyproject.toml` declares `Apache-2.0` |
| **Land market: all regions, and the run-time result** | Split regions (Trento and others) now have land-market data too. With the land market on, the full 2030 Farm-to-Fork runs in about 2 minutes instead of 10–12, with no slow solves; results shift because land demands can be met by converting forest and other land. Default stays off until the land-use change is checked against CAPRI |
| **Land market (switch, off by default)** | Land-type areas are now variables in each regional problem when `use_land_market` is on, with CAPRI's land-market costs; the base is identical. In Epirus, Farm-to-Fork's fallow floor is now met by converting other land, without the slow solver path, and cereals are no longer wiped out |
| **CAPRI land-market data built** | CAPRI's land-market matrices for six land types (arable, grassland, permanent crops, forest, other land, artificial) and their base areas, for 202 regions, from the files supplied. Ready for land-use flexibility |
| **Why two regions are infeasible under Farm-to-Fork** | CAPRI's landscape floor applies to total agricultural area, but the model keeps each region's arable land fixed; in Trento and Epirus, almost all grassland, the floor exceeds all arable land. CAPRI makes land types variable and converts grassland or other land to arable, within its permanent-grassland rule. Design in `docs/LAND_USE_FLEXIBILITY.md` |
| **Run-time overhead removed, results identical** | Profiling showed most market time in single-cell pandas operations inside loops added this month, and much supply time in re-reading fixed data. Both rewritten with the same arithmetic on arrays and cached values; each change verified to give identical results (differences 0 and 6×10⁻¹⁵) |
| **Faster, exact regional solves** | Farm-to-Fork run time is dominated by regional solves falling back to a slow general solver. On feasible problems an exact least-distance solver now runs first: it matches the old fallback's result in 29 of 30 captured cases and finds a 3.5% better optimum in the 30th (where the old solver stopped short), in about 0.5 ms instead of 1 s. Two mountain regions turned out to be genuinely infeasible under Farm-to-Fork (landscape floor vs arable land) and are unchanged for now |
| **EU ration wired in (switch, off by default)** | The ration now feeds livestock feed costs, the fodder balance and EU feed demand when `use_ration` is on; the baseline is unchanged. Testing found that the 2030 projection did not pass the switch to its model (fixed) and that undamped rations made the outer loop oscillate (ration updates now damped like prices) |
| **Fodder balance: first Farm-to-Fork result** | With herds tied to fodder, ruminant herds fall more, toward CAPRI (dairy −8.8% vs −10%), and manure methane now matches CAPRI (−12.5% vs −12.2%). Fodder areas do not yet follow herds down, because the balance allows unused fodder; CAPRI's is an equality, which comes with the ration wiring |
| **Fodder balance in the supply model** | Herds are now tied to the fodder they eat, as in CAPRI: regional fodder use must be met by regional fodder production. It replaces an older roughage constraint that never bound (it allowed generous "buy-in"). The balance is exact at base and carries CAPRI's fodder value as its shadow price, so fodder area follows herds in both directions |
| **73 regions now get CAPRI's regional livestock data** | The NUTS correspondence did not map CAPRI's codes for all of France and several German, Bulgarian, Greek, Italian, Swedish, Norwegian and Polish regions, so they received national averages for revenue, manure and feed per head. Pairs were found by matching agricultural areas and confirmed on dairy herds (which caught one coincidental match in Italy and two others); all livestock coefficients and the ration data were rebuilt. Brittany's dairy manure, for instance, rises from 141 to 169 kg N per head |
| **Fodder balance designed** | CAPRI's fodder balance read (use = production net of on-farm losses) and its regional data located; the design (`docs/FODDER_BALANCE.md`) fits the calibrator's existing treatment of binding constraints. One data check remains: our base fodder areas are smaller than CAPRI's in some regions |
| **All CAPRI ration rules in; a missing fodder balance found** | The ration model now has all of CAPRI's share rules, including the data-driven fodder ones, and a fallback solver (no failures). Building it revealed that the supply model has no fodder balance: herds are not tied to the fodder they eat. That link comes before the ration is wired in |
| **CAPRI's feed-share rules in the ration model** | CAPRI's minimum and maximum feed shares turned out to be rules in its code rather than stored data; the fixed rules are now in the ration model. Dairy and bull rations now respond plausibly (cereals −2% instead of −52% to −77% for a 10% cereal-price rise); suckler cows and heifers wait for CAPRI's data-driven fibre rules |
| **CAPRI's feed-PMP terms adopted in the ration model** | CAPRI's calibrated ration slopes (`pmppar`, sign convention verified against base optimality) now drive the ration model; the base stays exact. Responses barely change, which shows the reconstruction was faithful and that CAPRI's restraint on cattle rations comes from its feed-share constraints — still to be obtained |
| **EU ration programme built (not yet wired)** | `capri_mod/feed/ration.py` implements CAPRI's feed PMP per region and animal; all 2,084 base rations are reproduced exactly. Without CAPRI's minimum and maximum feed shares, cattle rations react far too strongly to prices, so wiring waits for those bounds (`Chk_feeddataTOP*.gdx`) |
| **EU ration data built; impossible rice data removed** | `tools/build/build_feed_ration.py` builds base rations, nutrient requirements, contents and feed prices for every EU region and animal from CAPRI's 2017 results (235 regions, 2,084 entries, energy and protein closing exactly). `pari_activity.json` turned out to be an undeclared source extract no longer read at run time and was removed; La Rioja's rice (81 ha at an impossible 25.4 t/ha) was removed from the live tables |
| **EU tariffs set to CAPRI's** | EU tariffs now equal CAPRI's 2017 total protection on EU imports (ad valorem, specific duties and quota effects together). Several were far off — sheep meat 52% vs 0.1%, cheese 40% vs 6%, butter 82% vs 38%, whey 12% vs 66% — while beef was already close (65% vs 58%). The effect on Farm-to-Fork meat prices is tiny, which shows the meat-price gap comes from market structure, not tariff levels |
| **Loose ends closed** | Olive world price per tonne of olives from CAPRI's olive-oil price and EU oil yield (21.3%); whole milk powder mapped; other oilseeds confirmed to have no CAPRI world price; the sheep 'arbitrage' anomaly traced to a code collision (CAPRI's SHGM is the dairy-sheep activity), correcting an earlier explanation; German land rents now official Destatis 2016 values by federal state (mean €304/ha, was a uniform derived €172). The EU oilseed seed balances now use CAPRI's data (EU rapeseed crush within 1.3% of CAPRI's, was +10%), which also exposed and fixed a latent crushing bug: the EU base crush read a value that calibration later rescales |
| **Comparison with CAPRI: modules and coupling** | `docs/archive/CAPRI_COMPARISON.md`: every capri-mod module against its CAPRI counterpart, a link-by-link coupling scorecard, the Farm-to-Fork validation read against it, and the remaining gaps in order of effect |
| **EU ration choice: design complete, data verified** | CAPRI's ration mechanism read in full: nutrient requirements per production day, feed PMP terms that make the observed ration optimal at base, assumed feed elasticities (cereals and fodder −10, protein −5, energy −0.5), requirements trimmed to the data at calibration, and links to mitigation options. The 2017 regional data close for all 4,518 region × animal cases (energy and protein to a median of 0.00%) |
| **Feed demand responds to feed prices outside the EU** | Non-EU feed demand for cereals and cakes now follows CAPRI's feed-price elasticities, own and cross. Under Farm-to-Fork the sunflower-cake price fall halves (−23% → −12%), the cereal price rise eases (+12.1% → +11.6%) and convergence returns to 7 iterations. The EU counterpart — CAPRI's ration choice in the supply models — is designed in `docs/FEED_RATION.md` |
| **Oilseed crushing (stage 3): cakes as feed, proxy removed** | Cake feed demand follows herds' protein-rich feed, and livestock protein-feed costs follow a cake price index weighted by CAPRI's EU feed use. The soybean-meal proxy price is gone. Under Farm-to-Fork cake prices fall as herds shrink; the size of the fall (sunflower cake −23%) shows that feed demand still lacks its own-price response, which is next |
| **Oilseed crushing (stage 2)** | Crushing runs inside the market in every region, as in CAPRI: crush responds to the crushing margin with CAPRI's calibrated response, oil and cake supply = crush × yields, crush is part of seed demand. Fixing the projection identity test also removed a pre-existing leak: the market's base tables are now restored at every baseline, so results no longer depend on a model's run history |
| **Six oil and cake markets added (crushing, stage 1)** | Rapeseed, sunflower and soybean oils and cakes are now market commodities (39 in total), with CAPRI's balances, world prices, trade, Armington, demand and tariff parameters; EU oil demand uses CAPRI's EU-specific elasticities. The base clears exactly at CAPRI's prices and all existing results are unchanged. EU supply is held at base until crushing (stage 2) makes it endogenous |
| **Trade table rebuilt on CAPRI's own trade partition** | The trade table double-counted EU trade (CAPRI reports the EU block under two codes), dropped eleven genuine trading regions as if they were reporting aggregates (including Uruguay–Paraguay, which supplies most EU soybean imports), merged another region into South Africa, and had no trade at all for sugar, wine, whey and sheep meat. CAPRI's trading regions were derived from its own numbers (they reproduce its world totals exactly for all 71 products) and the table rebuilt; EU imports now equal CAPRI's to the tonne (soybeans 14.6 Mt, was 26.4). Six oil and cake columns added for the crushing module |
| **World prices replaced with CAPRI's own** | The world price file differed from CAPRI's base-period world prices for most commodities, and its oilseed rows held cake prices (soybeans at a third of their value). Replaced from CAPRI's `FAO_agg` market data with an explicit code map; the reproduction anchor and test now read the file instead of hard-coding the old values. Base and Farm-to-Fork results unchanged (the model works on price ratios); correct levels are needed for crushing margins |
| **Oilseed crushing: base data from CAPRI's own market database** | Balances of the three seeds and their six oils and cakes for all 21 trade regions, from CAPRI's `FAO_agg` market data (base period); EU crush and yields derived (rapeseed 41.8% oil / 54.1% cake, sunflower 42.0 / 52.8, soybean 18.6 / 78.8). The crushing design now maps every coupling link the module creates |
| **Oilseed crushing designed** | CAPRI's crushing mechanism read from its market model (margin, crushing response, Leontief oil and cake output) and CAPRI's 2030 oil and cake balances identified; design in `docs/OILSEED_CRUSHING.md`. It will replace the soybean-meal proxy price. CAPRI's calibrated market elasticities (`results\arm\elas*.gdx`) requested |
| **Livestock unit audit: manure and feed per animal now match CAPRI** | Comparing EU totals per animal with CAPRI showed manure and feed per head had used CAPRI's per-unit values on census herds — bulls, heifers, calves and broilers carried 3–12× too little manure, pigs and sheep too much, nearly cancelling in the EU total. Rebuilt from CAPRI's 2017 totals as revenue already was. The nitrogen target now reaches beef and poultry: beef −10% (was −5%), poultry −8% (was −2%), manure methane −11.7% (CAPRI −12.2%). Simplification register added to the coupling review |
| **Feed demand follows herds** | Cereal feed demand in the market now follows herd sizes, at each cereal's feed share from CAPRI's 2030 balance — fewer animals, less feed demand. The cereal price rise under Farm-to-Fork falls from +13.8% to +10.2% (CAPRI +8%) and cereal production moves to 0.96× CAPRI |
| **Coupling review; prices now reach livestock** | A review of how the modules are coupled (`docs/MODULE_COUPLING_REVIEW.md`) found that market prices never reached livestock: the price signal was keyed by commodity and margins looked it up by activity. Fixed. The review also documents the open gaps — feed demand independent of herds (likely behind the cereal price overshoot), no oilseed crushing, side modules outside the loop |
| **Livestock respond to prices: pigs now match CAPRI** | Animals' price response was calibrated on an inflated revenue (price × yield, ~20× too high for pigs), damping every price and feed-cost change; it now uses CAPRI's market revenue per head, as the margins already did. A numerical floor that pinned poultry's curvature was relaxed. Feed costs now include soybean meal. Pigs −15.8% (CAPRI −14.5%), manure methane −10.6% (−12.2%). Livestock comparisons now use herd sizes (output is unverified for most animals) |
| **Fertiliser allocation, stage 2: fertiliser follows crop need** | Mineral fertiliser now covers what crops need beyond what manure supplies, with CAPRI's regional availability and its minimum-mineral floor (40% of an arable crop's need must be mineral) — so herds are a strong lever on the surplus where manure is saturated, a weak one where it is well used. Base year identical by construction, pinned by a new test. Fertiliser N₂O −32% (CAPRI −40%, was −28%); crops still match |
| **Fertiliser allocation, stage 1: manure trade** | CAPRI's fertiliser allocation read from its code and verified against its reference numbers; calibration data extracted (153 regions, 47 crops). Manure now moves between regions as in CAPRI (11% of EU manure N; Weser-Ems exports 31%), which brings regional surpluses closer to CAPRI's on every measure. Surplus anchor re-based with that evidence. Design for the remaining stages in `docs/FERTILISER_ALLOCATION.md` |
| **Organic land is fertiliser-free; poultry diagnosed** | Organic conversion now removes mineral nitrogen, not just its cost (CAPRI's `organic_minfert_redu.gms`): fertiliser N₂O −26% (CAPRI −40%). Poultry's non-response traced to its margin's unit chain, not the feed table, which matches CAPRI's per-bird figures |
| **Nitrogen balance aligned with CAPRI's reference run** | Using the full CAPRI 2030 reference results: the nitrogen target now starts from CAPRI's own baseline surplus per region, the balance no longer subtracts "animal products" (manure now counts in full), and deposition comes from CAPRI's regional values. Farm-to-Fork herds now nearly match CAPRI: dairy −9.3% (−10%), beef −12.8% (−14.5%), pigs −10.7% (−15.5%); methane and GHG move with them. Poultry, fertiliser N₂O and meat prices remain open |
| **Livestock fixes; gap narrowed down** | A post-solve "safety rail" overrode policy responses and corrupted shadow prices under the nitrogen target — skipped there now. Corrected the livestock-to-market codes (an earlier fix had used codes that don't exist here — beef came from bulls and calves only). Animal feed costs now follow cereal prices. EU herds still respond about half as much as CAPRI's; the cause is narrowed to the composition of the nitrogen balance, not prices |
| **CAPRI's fertiliser technologies; crops now match** | Fertiliser now falls as in CAPRI's code: efficiency technologies adopted under the nitrogen price, with CAPRI's own efficiency formula and cost terms, and no yield loss — replacing a yield-loss channel. A manure-application constraint (Nitrates Directive) stops regions keeping animals while abandoning fields. Farm-to-Fork 2030: cereals 0.97×, oilseeds 1.12×, vegetables and permanent crops 1.00× CAPRI. Remaining gap: herds respond about half as much as CAPRI's |
| **Nitrogen target: convergence, accounting and three bug fixes** | Farm-to-Fork now converges in 7–8 iterations (was not converging in 25): land and the nitrogen price are settled within each iteration. Fixed a fallback-solver crash, per-run resets that wiped other regions' land-market state, land expansion "diluting" the target (now a regional cap), and uptake accounted at base yields in both the constraint and the environmental report. N surplus −30.0% (CAPRI −33.5%), fertiliser N₂O −36.6% (−40.4%). Crops now carry too much of the adjustment: fertiliser falls through yield loss here, whereas CAPRI uses nitrogen mitigation technologies — the next change |
| **Environmental results restored; first Table 15 comparison** | Every run's environmental table had been empty: two bugs (an undefined name, a missing `@dataclass`) failed every region inside a loop that swallowed errors. Fixed and pinned by a test. Against CAPRI's Table 15: N surplus −29.8% (−33.5%), enteric methane −13.1% (−14.6%), GHG −12.4% (−14.8%); mineral fertiliser barely falls (N₂O −2% vs −40%) — next to reconnect |
| **Nitrogen target on the full balance; livestock reaches the market** | The nutrient target now binds the gross nitrogen balance, as JRC121368 specifies, instead of applied nitrogen — so manure counts and herds respond: Farm-to-Fork dairy −6.9% (CAPRI −10%), beef −12.7% (−14.5%), pigs −9.9% (−15.5%). And a broken bridge block, using activity codes that don't exist and arbitrary "market slot" factors, had kept meat markets disconnected from the herds in every scenario; meat prices now respond (pork +23% where supply falls 30%). EU meat prices still react far less than CAPRI's (pork +4% vs +43%) — recorded as the next market question |
| **CAPRI's Green Deal switchboard; Farm-to-Fork in 2030** | `greendeal_scenario()` mirrors `greendeal_scenarios.gms` — same settings, units and result names; unimplemented options refused. The projection now runs scenario objects, reusing each year's baseline. Run in 2030 as CAPRI does: farmland +3.6% (+3%), cereals 0.85× (0.77× on the 2017 base), oilseeds 1.04×, vegetables and permanent crops 1.14×. The 2030 scenario converges in exactly 25 iterations, the cap |
| **Organic yield gap in CAPRI's actual mode** | The organic gap was discounted by 0.45 whenever the pesticide instrument was active. CAPRI does that only in its endogenous-pesticide mode; the Farm-to-Fork study used an explicit 10% loss, in which the organic gap applies in full. Removed: wheat and barley yields now −11% as in CAPRI, cereals 0.67× → 0.77×. Oilseeds (1.09×) and vegetables and permanent crops (1.16×) now slightly overshoot — they had matched partly because of the discount; nothing re-tuned. Iteration cap 15 → 25 (this scenario converges in 16) |
| **Farm-to-Fork matches CAPRI's area split; five times faster** | 79% of scenario run time was a slow fallback solving 11 **infeasible** regional problems — mountain and island regions where the landscape floor cannot fit on their arable land — and returning constraint-violating answers the model used. The floor is now fitted exactly to what the land can hold and the unmet part reported (81.7 kha, 0.8%). All regions converge; a full comparison takes ~2 minutes instead of ~10. With a bracketed land update the scenario converges in 11 iterations: **farmland +3.7% (CAPRI +3%), cereal area −3.7% (−4%), oilseeds 0.97×, vegetables and permanent crops 0.97×**. Cereals 0.67× — now exposed as a weaker yield response |
| **Land rents from Eurostat; land market converges robustly** | Regional land rents now come from Eurostat (`apri_lrnt`, 2017): 209 of 248 regions published, Germany and Cyprus on a flagged fallback. The CAPRI accounts rents used before overstated land's value up to sevenfold in places (Slovakia 340 against 48 €/ha), suppressing the land response. With the steeper response, the land update oscillated in low-rent regions; a secant step now settles it in 3–4 iterations |
| **Faster solves; real shadow prices; land responds to rent** | A profile put half of run time in the nitrogen intensity routine and 11% in `_base_levels`; both rewritten with **zero difference** in results (binding-ceiling solves 3.8× faster). The reported shadow prices could only be non-zero for a violated constraint — now real duals, labelled per row, which withdraws an early finding that land never binds. Agricultural land now responds to the land rent (CAPRI's land market; elasticity 0.15 from its land-use nest, rents from its accounts), one solve per region per outer iteration, carried statelessly. Farm-to-Fork re-run against CAPRI's Figure 5 (farmland +3%, oilseed area −4%) pending. A remaining cost, solver cycling in 11 of 248 regions per scenario iteration, is diagnosed and recorded |
| **Sugar trade from CAPRI; source files checked; README counts gated** | Sugar now carries CAPRI's own extra-EU trade (imports 2,969 kt, exports 855 kt, from the bilateral 2030 reference), so its EU price can respond. Durum remains a documented gap: CAPRI trades wheat as one commodity, and the market's EU durum balance is near-even, so the first attempt made the premium so steep that Farm-to-Fork stopped converging — fixed by applying the traded-goods rule to the rebuilt flows; converges in 7. The source price tables and CAPRI's regional selection are now shape-checked (40/40 files, gzip included). The documentation gate checks README counts against the code — and caught a stale input count on its first run |
| **Trade check against CAPRI; abatement layers labelled** | Under Farm-to-Fork, EU cereal imports rise +40% (CAPRI +39%, durum excluded for lack of trade data) and exports fall −44% (CAPRI −38%), reported by a new `eu_gross_trade` from the market's own Armington clearing. CAPRI's mitigation portfolio is now the primary technological abatement (`abatement_capri`); the EcAMPA measures are kept as an independent literature comparison (`abatement`), with fitness-for-use entries for both |
| **Abatement from CAPRI's own mitigation portfolio** | Replaces reliance on a 10-row literature table with CAPRI's data: its technology table (20 options × 27 countries) and its full-potential run against the 2030 reference. The adoption rule is CAPRI's own and reproduces its calibration for all 245 options at zero price. At full potential, per source, on this model's emissions: enteric −10.8% (CAPRI −12.0%), manure methane −22.3% (−21.8%), manure N₂O −29.4% (−30.0%). Also corrected along the way: CAPRI's reductions had first been read per unit of an aggregate that grows 17%, overstating them twofold |
| **Oilseed seed quantities reach the market intact** | The bridge multiplied rapeseed and sunflower seed by the oil extraction yield (0.42) and handed the result to the seed market, so the market saw EU rapeseed at 7.4 Mt instead of ~19 (CAPRI's 2030 reference: 22.4). Found by comparing against CAPRI's own EU27 market balance, now stored as a validation reference — which also confirms the corrected EU balance (wheat self-sufficiency 1.27 against CAPRI's 1.31). Oilseeds under Farm-to-Fork 1.40× → 1.33× |
| **Pesticide target on conventional area only** | CAPRI treats the 50% pesticide cut as a total target: organic conversion already delivers part of it, and only the remainder falls on conventional land (`conventional_io.gms`). This model applied the full cut, the yield loss and the extra input costs to every hectare, double-counting wherever organic and pesticide instruments combine. Fixed: **vegetables and permanent crops 1.21× → 1.08×** CAPRI, oilseeds 1.48× → 1.40×. Run instrument by instrument, the landscape floor matches CAPRI's own attribution (cereal area −8.8% against −9%); the remaining oilseed excess sits in the pesticide cost channel |
| **Results no longer depend on a model's history** (run history dependence) | A run with a world price shock overwrote the market's base world prices and nothing restored them, so every later run on the same model inherited the shock — a baseline after a +20% wheat-price run gave DE11 wheat 111.2 instead of 91.2. This predates the current work. The market calibration also froze at an instance's first-ever solve. Now each run starts from the true base, each baseline recalibrates, and scenarios reuse their baseline's calibration. The null-trajectory projection test passes even after a deliberately shocked first run |
| **Consistent EU market; scenarios converge fast** | The market's EU production was the residual of a hard-coded world total (wheat 55.9 Mt against ~139), so EU consumption came out at 28.4 Mt of wheat. Now EU production is the model's own output and consumption keeps FAO's self-sufficiency — wheat 99.4 Mt; the baseline converges in 2 iterations instead of 11. The Armington premium now uses gross trade, applies only to traded goods (sugar beet was flipping between bounds every iteration), and the market anticipates the supply response. **Farm-to-Fork converges in 6 iterations; a full comparison takes ~10 min.** Cereals −15.0% against CAPRI's −15%. Also fixed: a world-price shock persisted into every later run on the same model |
| **Land conserved; CAPRI's own Green Deal targets** | The arable constraint left out set-aside and fodder, so a landscape floor grew set-aside out of nothing (DE40: +52 kha, cereals unchanged) and ~14 Mha of slack meant the constraint could never bind. Fixed, with one crop classification shared by the constraints and the land data — base fidelity improved 0.59% → 0.22%. CAPRI's per-member-state landscape and organic targets (from its own GDX files) replace flat 10% and 25%: organic conversion is burden-shared by member state and crop group. **Cereals −15.3% against CAPRI's −15%.** Diagnosing the remaining price overshoot found the market's EU base balance departs from FAO (wheat consumption 28.5 Mt vs 108.9) — recorded as the next fix |
| **EU prices now formed in an Armington market** | The oilseed and permanent-crop overshoot had a structural cause: every EU price was a fixed wedge on the world price, so the EU was a price-taker. The model held Armington parameters — CAPRI's own values — but they only split imports among supplier countries and never touched prices. And farmers responded to the world price, not the EU price. Under Farm-to-Fork, EU prices rose 1.6–3% against CAPRI's 8–15%. Fixed with an Armington premium from the standard first-order condition, with supply responding to the EU price; exactly 1 at base, all anchors unchanged. A cobweb oscillation followed and was damped. **Oilseeds 1.40× → 0.93×, vegetables and permanent crops 1.39× → 1.05×**, prices now +7.5–9.5%. Cereals fall to 0.65× with their price almost exactly CAPRI's — so the earlier cereal match was partly two errors cancelling. Rice also added to the supply-to-market bridge |
| **Three "Not sound for" items fixed** | **Wine**: only 11 of the "101 regions" actually grow wine; each now falls back to its country's own CAPRI price (Sicily 95.5 → 1,361.6 EUR/t) instead of the EU average. **Croatia**: split by crop from CAPRI's regional data instead of one cattle key, which had put 91% of the olives in continental Croatia — Adriatic olives now 18.0 kha, verified against CAPRI's national 18.6. **Saxony**: split by crop from the pre-2013 codes — maize in upland Chemnitz 7.1 → 0.9 kha, lowland Leipzig 2.4 → 7.8. National totals preserved exactly. Norway, Irish nitrogen, the overshoot, multi-period projections and economy-wide effects remain, each for a stated reason |
| **Livestock intensity margin** | CAPRI carries every dairy herd as a low- and a high-intensity variant (`DCOL`/`DCOH`) so it can extensify under a nutrient target instead of only shrinking. In the base year the split is mechanical — half the herd each, yields averaging to the one already used — so the value is the response channel. Bounds extracted per region (EU median 5.39 and 8.99 t milk/head); a nitrogen ceiling moves the dairy yield toward the low bound, carrying revenue and reported output with it. In `NL11` under a 100 kg N/ha ceiling the herd falls 1.6% while milk output falls 10.5%. Inert when no ceiling binds; base fidelity and all anchors unchanged |
| **Oilseed and permanent-crop overshoot documented** | Cereals land at 0.93× CAPRI but oilseeds and permanent crops at 1.40× and 1.39×. Six explanations tested and ruled out by measurement (yield channel, land pinning, price feedback, elasticities, uniform organic shock, catch crops). The residual is concentrated in vegetables (−9.3%), which CAPRI reports merged with permanent crops — so its reference cannot be split to check them. Recorded as a bounded limitation rather than left as an open question |
| **Rice given a market, and the last four activities mapped** | Paddy rice competed for land but had no market balance; CAPRI's own world price (411.42 EUR/t) and FAO data for 24 regions were already held, so `PARI` is now a market commodity — world rice balances at 386,384 kt with the real producers. The four activities left unmapped (other marketable crops, other industrial, nursery, flowers — 1,721 kha) are now activities in their own right. **The model's agricultural area now equals CAPRI's exactly: 166,690 kha, 100.0%.** The manifest caught the row-count changes from adding rice before anything absorbed them |
| **Five inputs were undeclared in both manifests** | `livestock_output_coef`, `livestock_revenue_coef`, `nutrients_regional`, `organic_yield_gap` and `capri_own_price_elasticities` were loaded and used but declared nowhere, so the validator's shape check skipped them — a truncated livestock coefficient file would have passed silently. Found while updating the README, whose claim that "every input is declared" turned out to be false. Now declared in both manifests with shapes; validator coverage 25 → 30 files, verified by truncating a file to 99 rows and confirming it is caught |
| **Wine's regional price was silently dropped** | The price file uses CAPRI's codes (`TWIN` for wine, `TEXT` for fibre, `OFAR` for fodder), so five crops fell back to the EU-wide price — the same silent-drop family as MAIZ/CORN. Wine was priced at 95.5 EUR/t against CAPRI's median 1,362, leaving it on a **negative margin** (Spain −712, Aquitaine −1,413 EUR/ha) where real margins are 2,000–6,000. Found by decomposing the permanent-crop group: olives (4.5 Mha) already matched CAPRI at −0.10%, and the contraction was wine alone. Fixed: wine −11.3% → −2.6%, permanent crops −4.1% → −1.7% area |
| **CAPRI's area/yield decomposition obtained** | The published report (user-supplied PDF; the online fetch truncated before the results) gives what every comparison here lacked: cereals area −4% and yields −11% for a −15% supply fall; vegetables and permanent crops **area stable at +0.1%** with the whole −12% coming from yields. Against this: our cereals are close (−13.9% production, −2.4% area), but our permanent crops lose 4.9% of area where CAPRI loses none. The open question is now why permanent-crop area moves at all. The annex also independently confirms the organic yield-gap table and PESETA region membership already wired in |
| **Organic target applied at double CAPRI's shock** | The 25% organic target was applied as if every hectare converted. CAPRI converts the *distance* to the target — `p_organicAreaTarget = 0.25 - 0.10` in its own code, a 15-point shock. Corrected: cereals now −13.8% against CAPRI's −15%, and our cereal *yield* effect is −11.6% against CAPRI's published −11%. The remaining overshoot (oilseeds 1.40×, permanents 1.44×) is now on the area side |
| **Yield shocks never reached reported output** | The pesticide yield loss and organic yield gap were applied to net revenue only, not to yields, so production was computed on unshocked yields. This **reverses** the long-standing "cereals under-respond" finding: CAPRI's −15% cereal figure decomposes into −11% yield and −4% area, and our *area* falls 5.9% — more than CAPRI's. We had been comparing our area against CAPRI's production, the fifth apples-to-oranges error in this project. Fixed, plus CAPRI's 0.45 double-counting factor (previously tested and rejected on the wrong metric): cereals now −13.5% against −15% |
| **Two "Validated" claims corrected by audit** | After two investigations found stale summary figures rather than live defects, the standing claims were re-checked. "Crop elasticities match CAPRI within ~10%" was false for annuals (barley 0.51×, rape 0.14×) — it had been measured against literature targets, not CAPRI's values. "N excretion matches CAPRI `MANN` within ~12%" is withdrawn rather than restated: it predates the poultry unit conversion and a re-measurement runs into the same unit ambiguity that has produced two false readings. What *is* verified is the absolute check — manure nitrogen 7.5 Mt against a real EU ~7 |
| **Scenario implementation verified against the published report** | JRC121368 fetched directly (it is public; no CAPRI installation needed). Every implemented channel matches its specification: −50% plant-protection expenditure, +50% other costs, 10% yield loss, and for organic zero fertiliser/pesticides, +100% other costs, FADN yield gaps. The 10% yield loss traces to Sánchez et al. (2019) — CAPRI's own reading of the literature, not a tunable parameter |
| **World production: 6.7% allocated, not 23.4%** | A figure quoted throughout this project was 3.5× too pessimistic — it predated the FAO_agg extension being counted against both real sources. 26 of 29 trade regions carry real data; of the rest, 5.9 points are `ROW` (a residual by construction), leaving Iran and Saudi Arabia at 0.8% combined. Also removed a seeded ±8% noise multiplier on the allocated regions: reproducible, but invented variation presented as data. All anchors unchanged |
| **A safety rail overrode policy constraints** | A post-solve clamp caps each activity at a multiple of its base; running after the optimisation, it pushed solutions off constraints the solver had satisfied. A 10% set-aside requirement was cut to 1.5× base (floor 56.2 kha → reported 24.7). Price shocks only arise from the second iteration, so single-iteration runs looked right while **every converged policy run quietly relaxed its land constraints** — EU-wide, set-aside delivered 9.9 Mha against 15.6 required. Constraints now win over the rail. It did *not* change the policy headline, so it was not the cause of the under-response |
| **CAPRI's own elasticities for all 26 countries** | Permanent crops, horticulture and livestock vary only 1.0–1.6× across member states (tomatoes 1.0×, pork 1.1×) — genuinely EU-wide constants. Annual crops vary by up to two orders of magnitude (barley 9.9×, rape 16×, other cereals 56×, sunflower 141×), so per-country targets are mandatory. Wheat is absent from the parameter entirely, and an earlier "CAPRI 2.00" for wheat in this project was an assumption of mine, not a CAPRI value |
| **Plant-protection costs from 2 countries, not 27** | Shares derived from Spain and Italy alone were understated ~3x (wheat 5.7% → 17.6%). The check is decisive: applied to the base year the old shares imply €3.6bn of EU pesticide spending against a real €11–12bn market; the new ones imply €10.8bn. Correcting it alone made scenarios *weaker* — a bigger share means banning half of it saves more — which exposed the missing other half below |
| **CAPRI's +50% other-cost shock was switched off** | `PESTICIDE_OTHER_COST_RISE` was zero, for a documented and sound reason: the model had no equivalent of CAPRI's `INPO` category, and using the plant-protection share instead cancels the saving exactly. That precondition changed once `OTHER_COST_SHARE` was derived from `INPO` across all 27 dumps; restored to CAPRI's 0.50. French wheat margin −13.6%, rape −31.6% at the 50% target |
| **Farm-to-Fork figures were a 30-region subset** | Every F2F number reported here had been computed on the first 30 regions in index order — all German and Austrian, containing almost no permanent crops. EU-wide over all 248 regions the model under-responds: cereals 0.44x of CAPRI, oilseeds 0.73x, permanent crops 0.40x, where the subset showed 1.22x, 1.25x and 0.72x. The claim "all three within ±25%" was false. Same failure as `max_outer_iter=1`: a convenience setting became a published result. Comparison now lives in `tools/run/run_policy_comparison.py`, EU-wide and converged by default |
| **Market module vectorised** | 2.3 million scalar pandas lookups per run, 137 of every 140 seconds. Vectorised with identical results (anchors unchanged, prices still 12/12): a converged 10-region run fell from 59s to 19s, and a full EU two-scenario comparison now takes 9 minutes — so there is no longer a reason to use a subset |
| **Organic yield gaps from CAPRI's own FADN data** | The flat 20% gap is replaced by CAPRI's estimates by macro-region and crop group (JRC Seville, SUPREMA project), which it loads from an external file rather than hard-coding: Southern Europe fruits 22.5% and olives 11.6%, Central Europe fruits 51.3% and cereals 42.9%. With this and the cost-channel fix, all three crop groups land within 25% of published CAPRI (cereals 1.22x, oilseeds 1.25x, permanents 0.72x, from 0.45x) |
| **Farm-to-Fork cost channels were wrong** | CAPRI's pesticide and organic scenarios raise the *other inputs* cost category by 50% and 100%; this model applied that rise to the plant-protection share, where it cancelled the expenditure saving exactly and left the cost channel a no-op. Organic used a flat 15% premium where CAPRI doubles other inputs and removes fertiliser and plant protection. Other inputs are 48% of cost for table grapes against 9% for wheat, so the shock should bite ~4x harder on permanents. Fixed from CAPRI's own cost structure across all 27 countries: oilseeds now match exactly (1.00x, was 0.87x), permanent crops 0.45x → 0.58x |
| **Permanent-crop policy gap localised** | Running the four Farm-to-Fork instruments separately shows no channel is missing — each is about a third as strong as CAPRI's on permanent crops. Points at three measurable parameters rather than a structural unknown |
| **Farm income was not a margin** | Livestock revenue came from `YILD` (not a marketed product for breeding and suckler activities), and `gross_margin` reported the PMP *calibration* terms rather than the margin — 55,531,046 against an actual 428,136 thousand EUR for one region. Also found: CAPRI's dummy grass price of exactly 1000 EUR/t (grass isn't traded) had been copied in, making grass the largest item in every regional margin. Income now responds: organic 25% costs −10.8% of income, the nutrient rule −5.3%, where all instruments previously read ~−0.1% |
| **Poultry counted in the wrong unit** | CAPRI reports poultry in million head, everything else in thousand; per-head coefficients understated poultry manure, feed and emissions a thousandfold. Converted at load |
| **Nitrogen balance had two errors that cancelled** | Manure was counted twice on the input side, and fodder crops were credited with ~double the nitrogen they remove (fresh-matter yields against a dry-matter coefficient). Together they produced a plausible-looking 54 kg N/ha. Mineral nitrogen now comes from CAPRI's own NMIN per region and crop: mineral 10.2 Mt (real ~10.8), manure 7.2 (real ~7), surplus 44.5 kg N/ha (real ~46) |
| **Poultry head counts in mixed units** *(found, not fixed)* | Most regions in CAPRI's million head, three (Lombardy, Campania, Helsinki) in thousands. Output unaffected; effect on nitrogen excretion and feed not yet measured |
| **Solve state leaked between runs** | The restore block *enumerated* fields; the list fell behind twice (`nutrient_coefs`, then `yields`). Altered values persisted into later solves, so results depended on what ran before them. Now snapshots every restorable attribute |
| Permanent-crop elasticities inverted | 10× *less* elastic than annuals, where CAPRI has them 2.47× *more* |
| Livestock yields unit-inconsistent | ~56 regions in tonnes, ~192 in kg; drove the MACC 2–3× too high |
| Consumption fabricated | A clamp invented supply where exports exceeded production |
| Set-aside mapped to the wrong instrument | Modelled as an arable cut; CAPRI uses a fallow floor |
| Market price test asserting stale values | Failed for the life of the project against deliberately-corrected data |
| Hard-coded 2017 paths | Re-basing would have silently fallen back to literature defaults |
| Organic target missing | Only a payment *rate* existed, not an area *target* |

---

## Farm-to-Fork comparison (JRC121368)

**Now a single estimate, not a range.** The plant-protection cost was derived
from CAPRI data (see below), which removed the reason for reporting bounds.

| | CAPRI-mod | CAPRI published (JRC121368) |
|---|---|---|
| Cereals | −18.5% | −15% |
| Oilseeds | −12.3% | −15% |
| Permanent / fruit & veg | −9.4% | −12% |

Oilseeds (1.07x) and permanent crops (0.86x) are close. **Cereals still
**All three land within ±25% of CAPRI, with errors in both directions** —
cereals 1.24x over, oilseeds 0.86x and permanent crops 0.78x under. Errors that
do not share a sign argue against a systematic bias.

A large part of the previously-reported cereals overshoot was **a measurement
error of mine, not a model defect**: every comparison had been run with
`max_outer_iter=1`, which executes one supply–market pass and so suppresses the
price feedback. When EU cereal supply falls, prices rise and cushion the area
response; CAPRI's published results include that, ours did not. Running to
convergence moved cereals from −22.6% to −18.5%, closing roughly half the gap.

A convenience setting chosen for speed while iterating became a published
result — the same class of mistake as the stale documentation found elsewhere
here: correct in its moment, wrong once the context changed.

**Fixed at the cause, not the symptom.** The old code printed the
non-convergence warning only when `verbose=True`, so every comparison — all run
with `verbose=False` — failed in silence. A non-converged run now always raises
a `RuntimeWarning` and records `metadata["outer_converged"] = False`, and
`test_unconverged_run_warns_and_is_recorded` pins both that it fires when it
should and stays quiet when it shouldn't.

**The pesticide cost is CAPRI-derived, not assumed.** Built as
`PESTOTAL (g a.i./ha, capreg) / 1000 x UVAB.PLAP (EUR/kg, coco)`. Two unit checks
were run rather than assumed: summing PESTOTAL x area over Spain gives 89,888 t
against a national quantity of 83,104 t (within 8%, fixing the unit as grams per
hectare), and `UVAB x NETF` reproduces `EAAB` exactly at EUR 1,110.7m — which is
Spain's real annual pesticide spend.

**Confirmed independently on a second country.** Both checks were re-run from
scratch on Italy and passed *better*: reconciliation within 2% (against Spain's
8%), and `UVAB x NETF` matching `EAAB` to the decimal (947.6 vs 947.59 m EUR).
Two countries agreeing on the unit interpretation is far stronger than one.

**Country variation is real**, which is why one country was not enough: Italian
costs run a median 1.15x Spanish, but from 0.95x for maize to ~1.7x for olives,
citrus and apples. Mediterranean permanent crops are where the two disagree most.
Shares are now the median across both countries.

---

## Known assumptions carrying weight

- **`PPP_COST_SHARE`** — now **CAPRI-derived** (from `PESTOTAL` x `UVAB.PLAP`,
  two member states, units verified independently in each), no longer assumed.
  The residual uncertainty is country coverage: ES and IT differ by a median
  1.15x, and by ~1.7x for Mediterranean permanent crops.
- **Permanent-crop elasticities** — CAPRI's *relative* structure (2.47× annuals),
  not its absolute levels, which are member-state market elasticities rather than
  regional PMP targets.
- **Organic yield gap 20%, cost premium 15%** — literature (Seufert 2012, Ponisio 2015).
- **Mitscherlich curvature k = 3.0** — agronomic literature; not tuned to fit CAPRI.

---

## Documentation coverage check

`tools/check/check_doc_coverage.py` asserts that every registry entry recorded as a new
capability or fixed bug is mentioned in a user-facing document. It exists because
the same failure recurred **five times**: the work went into the registry and the
README lagged, caught each time by a human asking rather than by anything
mechanical.

Its first tightened run found a real gap — the CAP double-counting bug, one of the
most significant defects in this log, was absent from both the README and the
CHANGELOG.

A first version was too loose to be useful: it matched substrings, so a
deliberately-undocumented probe entry *passed* because "deliberate" occurs inside
"deliberately". A checker that cannot fail is worse than none. It now matches on
word boundaries and requires either the full entry key, a file path the entry
names, or two distinctive words in the same document — and is verified to fail on
a probe.

## Regression anchors

`capri_data/validation/REGRESSION_ANCHORS.json` + `tools/check/check_regression.py`.

A machine-checkable snapshot of the numbers that **external references**
validated. It reports *which validation broke*, not merely that a number moved —
each anchor names the reference it was checked against, so a failure points at a
source you can go and re-read.

```bash
python tools/check/check_regression.py            # exit 1 on breach
python tools/check/check_regression.py --update   # accept an intended change
```

Eight cheap anchors run every time (regions, convergence, base fidelity, olive
fidelity, N surplus, world balance, price reproduction, CAP budget); two
expensive ones (MACC, projection correlation) are recorded but checked on demand.

Two design points worth keeping:

- **Olives have their own anchor.** The aggregate base-fidelity measure looks
  only at annual crops and did not see the permanent-crop collapse. An anchor
  that shares a blind spot with the bug it should catch is worthless.
- **`--update` is how an intended change is accepted, not how a failure is
  silenced.** Verified to exit 1 on a breach and 0 when clean, so it is usable
  in CI.

Run it before and after any base-year re-base — that is the situation this
exists for.

---

## Still open

Gap = mean absolute deviation from JRC121368's 20 indicators. Default (CAPRI's land rules, no manure trade, cattle
genomics) 4.36; 4.30 without genomics; 4.64 before the EU price was reported with one premium;
with the manure market 4.77 (measured before the manure N2O fixes); the old default (idle land allowed, target on base farmland) 5.81.

- **Friesland (NL12)**: N price EUR 16,000/kg - its baseline matches CAPRI's, the tiered rule asks a 70% cut; feasible
  only by replacing dairy cows with suckler cows. With it relaxed: gap 4.58 (`--capped-regions=+NL12`); needs CAPRI's
  Farm-to-Fork output to know whether it was one of the report's nine.
- **Dutch importing regions** (NL11, NL13, NL23, NL32, NL34) get JRC121368's 36% cut for infeasible targets; their
  N prices stay high (NL23 EUR 2,300/kg, NL34 940).
- **Which nine regions JRC121368 relaxed** to a 36% cut: not named in the report; the model takes the nine highest
  baseline surpluses per ha. Brittany and Lombardy fit the report's description (sensitivity `--capped-regions`:
  land rules 7.52 -> 5.34). Needs CAPRI's Farm-to-Fork output.
- **Prices** (one premium): pork +20% (CAPRI +43), beef +14% (+24), poultry +21% (+18), cereals +5.7% (+8), oilseeds
  +11.8% (+11), vegetables and permanent crops +9.7% (+15); pigs -25% (-14.5) without manure trade.
- **Nitrogen prices** still high in some livestock regions (Brittany ~EUR 30/kg by default).
- **Baseline manure exports**: kept — fixed export shares in baseline and scenario with the market off, endogenous with it on (see sprint doc); **poultry price** +37% against +18%; **manure CH₄** −20% against −12%; **ammonia** −42% against −33%;
  fertiliser technology adoption below Table 17 (inhibitors 6% vs 18%, precision farming 25% vs 35%).
- **Dairy block** (opt-in, EU and world): raw milk +28% against CAPRI's +1.5% (read from JRC121368 Figure 7);
  the EU-cleared products (fresh milk products, cream) carry it. Needs the figure checked and, ideally, CAPRI's
  Farm-to-Fork market results for dairy products.
- **Genomics adoption**: milk yield 3.3% (Table 17: 15%), ruminant efficiency 33% (9%) - the nitrogen price again.
- **Manure N2O**: -21.5% against JRC121368's -3.2% (cascade and housing equation in; the rest is the manure
  inhibitors' adoption, 43.7%, whose CAPRI cost terms (N2OMAN) and Farm-to-Fork N shadow prices are not in the data
  received). Genetics, low-N feed and tillage: not built, with CAPRI's own evidence (see the entry above).
- Biofuel output is fixed at the 2030 reference, as in CAPRI's scenarios without `BIOF_M`; CAPRI's endogenous
  biofuel supply and demand (sigmoid functions, fossil fuel prices) are not built.
- Coupled-support response: suckler cows and Italian durum wheat respond less than in CAPRI.
- Phase 2 (base-year update) not started; the base year remains 2017.
- Future (decided 15 October 2026, not scheduled): CAPRI's original NLP for the regional supply models, solved
  with IPOPT, as a switchable solver (`supply_solver`), Clarabel stays the default and the fallback. Literal CAPRI
  form: exact ammonia loss cascade, one regional share per fertiliser technology; feeding in total form (exact by
  algebra; IPOPT fails on the per-head form). The shadow trial found the same results as the conic model at ~7x the
  supply time (docs/archive/NLP_CHECK.md); needs a parametric CasADi build per region, warm starts and a fallback for the
  ~0.5% of solves IPOPT does not finish.
