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
| Water demand | Known EU irrigation geography | Mediterranean 79%, correct hotspots |
| Biofuel | CAPRI 2030 reference (BiofFeedCost, biofuel output and use per CAPRI market region) | exact; feedstock use and biofuel markets inside the market |
| **Total cereal output** | **EU Agricultural Outlook 2017-2030 (DG AGRI/JRC)** | **297.2 Mt vs ~300 Mt — ratio 0.99** |
| **Farm-to-Fork scenarios** | Published CAPRI (JRC121368) | reported as a range; CAPRI's figure falls inside it for oilseeds |

---

## capri-mod-proto (from Sprint 9t): the nitrogen target as a plain constraint (October 2026)

Prototype branch; 9t is kept as `capri-mod-9t.zip`. Details: docs/PROTOTYPE_NI_INSIDE.md.

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
- NLP check (`tools/nlp_check`, docs/NLP_CHECK.md): captured regional problems in CAPRI's original form (feeding per
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
  capri_data/validation/eu_outlook_2020_2030.csv, tools/compare_outlook_2030.py. It found K12: since Sprint 9p the
  model's dairy cows, heifers, bulls, calves and sheep/goats had no 2030 yield factor (CAPRI's reference reports only
  their intensity variants) and gave 2017 output per head - EU cow milk 139.6 Mt against CAPRI's 154.3. Fixed in
  tools/build_trajectory_capri_ref.py (components' level-weighted yields; sheep and goats' milk and meat separately,
  ProjectionModule._project_livestock) and herd aliases in tools/build_trajectory_model_keys.py. Baseline cow milk
  157.2 Mt (CAPRI +1.9%). Farm-to-Fork gap 4.28 -> 4.43: the milk price rises more (+32.3, CAPRI +1.5; K13).
- K14: a Clarabel solve declared infeasible (PrimalInfeasible / DualInfeasible) is re-checked with infeasibility
  tolerances 1e-12 before falling back: FI1C under the Green Deal was wrongly declared DualInfeasible (finite optimum,
  IPOPT agrees) and the run did not converge in 60 iterations. Green Deal now: 20 iterations, no fallbacks.
- The same fixes, without the prototype's model change, are tagged 9t.1 (capri-mod-9t1.zip). Comparison of 9t, 9t.1
  and the prototype in three scenarios: docs/COMPARISON_9t1_PROTO.md.

## Sprint 9t: one parameter file; land supply of combined CAPRI regions (October 2026)

- **`capri_data/shared/model_parameters.csv`** holds every constant the economics and accounts rest on (55 rows:
  CAPRI's parameters, IPCC factors as CAPRI uses them, JRC121368's assumptions, the Nitrates Directive limit, two
  literature values for the nitrate-limit option, the outer loop's damping and the land-rent rule as model settings),
  each with unit, kind and source; `capri_mod/params.py` reads it. Numerical tolerances stay in code. A test keeps
  file and code in step (no row unused, no parameter missing). Orphans removed on the way (an unused Nitrates
  Directive constant, an unused nitrate CH4 factor, an unused organic-gap share). Results identical: a 6-region
  Farm-to-Fork and carbon-tax run compared value for value before and after.
- **Land supply of combined CAPRI regions** (`tools/build_land_market.py`): the land owners of several CAPRI regions
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
- **Crop premiums, costs, prices, yields from CAPRI for every region** (`tools/build_crop_economics_2017.py`):
  1,957 region x crop cells had taken their premium from `cap_payments.csv` - the loader's random generator written
  to disk - because the premium file covered 192 regions in CAPRI's codes (fodder, set-aside, wine, fibre never
  matched); wine and fibre costs were template fills, fibre yields a lognormal draw, wine prices national fills in
  36 regions. The loader's cap on horticultural costs (2x the EU median: other fruit in Austria 8,747 EUR/ha against
  CAPRI's 27,000-37,000) is removed. `cap_payments.csv` now holds CAPRI's premium per ha of UAA (budget report only).
- **Methane and CO2 as CAPRI accounts them** (`tools/build_ghg_coefs_2017.py`): manure and enteric CH4 per head
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
  `tools/build_tariffs_2017.py` gives every region CAPRI's own measure, as the EU row: total protection on its imports
  from outside the region, ImportP / (Fob + TCost) − 1 over CAPRI's 2017 bilateral flows (the EU row recomputed this
  way from the member states agrees to 0.1 point). Farm-to-Fork: no indicator moves by more than 0.1 point, gap 4.31
  (4.30); Green Deal unchanged. The loader no longer generates tariffs (EU row only, with a warning, without the file).
- 88 tests (new: parallel and one-process solves equal).

## Sprint 9q: CAPRI's 2030 rations and fodder in the projected baseline (October 2026)

- The 2030 rations and requirements are CAPRI's 2030 reference's per head (factors per region, animal and feed on the
  2017 rations; `tools/build_ration_trajectory_2030.py` → `capri_ref_ration_2030.csv`), and the fodder balances'
  usable fodder per ha follows CAPRI's FEDM / LEVL of the fodder crops (`capri_ref_fodder_2030.csv`; silage maize for
  biogas in Germany). Before, the 2017 mix scaled by one factor did not match the projected fodder output.
- Regional drift of the baseline from its projected levels: median 0.01%, 90th percentile 0.36% (fodder crops 1.1%,
  was 17%). Against CAPRI's 2030 reference: activities 1.3%, production 1.1%, domestic use 1.6% (medians). Farm-to-Fork
  799 s (fewer calibration rounds); gap 4.30.

## Sprint 9p: projection layer - CAPRI's reference as the baseline, baseline calibration (October 2026)

- **Trajectory**: CAPRI's 2030 reference (CAPMOD's reference run over CAPRI's 2017 results: levels, yields, land
  types per region; `tools/build_trajectory_capri_ref.py` → `capri_ref_2030.json`, default in
  `tools/run_f2f_2030.py`; `--trajectory captrd` for the trend projection). Land now follows CAPRI's 2030 land types
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
  `tools/run_f2f_2030.py` and `tools/run_vcs_2030.py` fix `PYTHONHASHSEED=0` (re-exec), the Dockerfile sets it; with
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
  extracts that the model does not read (its trade and balances are CAPRI's); `tools/recalibrate_trade_2017.py`
  reads the CSV from there. 87 declared inputs.
- README: chapter "Contributors" removed; manure market default and install instructions corrected.

## Sprint 9j: manure trade checked against CAPRI (October 2026)

- **Base manure trade rebuilt** from CAPRI's 2030 Green Deal reference with endogenous technologies (MTRADE.NITF,
  EXCRET.NITF per CAPRI region, per group of CAPRI and model regions; `tools/build_manure_trade_base.py`). The old
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
  CAPRI's `MaprFeed_` from cereals' and sugar's food, processing and biofuel use (`tools/build_feed_byproducts.py`,
  `feed_byproducts.csv`); non-EU p_elasSupp and p_ElasFeed (`build_feed_demand_nonEU.py`). Baseline exactly
  CAPRI's 2030 EU output and use. docs/FEED_MARKETS.md.
- Farm-to-Fork 2030: gap 4.59 → 4.53; FENI and FPRI prices −10%. 87 tests, 91 declared inputs.

## Sprint 9g: CAPRI's feed options on, as star 3.0 runs them (October 2026)

- **Low-nitrogen feeding** (`envind/low_n_feed.gms`, `ghgTechLowNFeed 1`): per region and animal from CAPRI's
  requirement corrections p_animReqCorrFac and res_17 manure N (`tools/build_lownfeed_effects.py`,
  `lownfeed_effects.csv`); a column of the regional models; curvature per unit of the eligible share (also fixes the
  breeding options where the eligible share is below 1).
- **Linseed and nitrate** (`envind/line_nitr.gms`, `ghgTechLineNitr 1`, a switch): requirement effects as
  supply_model.gms REQSE_/REQSN_, maximum shares from CAPRI's max calibration run (LINE_Tot, Nitr_Tot now extracted
  by `tools/extract_capri_costsavings.py`), CAPRI's costs halved, CH4ENT in the emission accounts
  (`tools/build_supplement_effects.py`, `supplement_effects.csv`). 3-NOP registered. The ration model's early
  nitrate ingredient is ignored when these columns exist.
- Farm-to-Fork 2030: gap 5.15 → 4.59; low-N feed 42% of manure N (Table 17: 0%), linseed 0.8%, nitrate 0.2% (7%).
- `tools/run_tests.py` uses its own fixtures even with pytest installed. 86 tests, 90 declared inputs.

## Sprint 9f: CAPRI's dairy block on, as star 3.0 runs it (October 2026)

- Rule: a block star 3.0 runs is on and judged against its own CAPRI reference; the Farm-to-Fork gap is recorded.
- **Nine dairy products traded**: FRMI, CREM, COCM, WMIO, CASE become market commodities (43) with CAPRI's bilateral
  flows, FAO_agg world prices and balances, Armington and p_ElasDem elasticities (`tools/build_dairy_trade_params.py`;
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
  (`tools/build_fert_dist_priors.py`: crop-level dump flows summed to the groups; postModePerHa reproduced to 4e-5
  against CAPRI's priFertDist results; 250 CAPRI regions + country fallback). Returns CAPRI's priors exactly at the
  baseline's totals in every region (tested). Reported per run as `results["fert_dist"]`. With all flows positive
  it leaves the regional totals as they were (the sum of `NUTNED_` is the balance's identity), so it changes no
  result by itself; Farm-to-Fork with it and the old technology base: gap 3.31, every indicator within 0.1 point.
- **Mineral fertiliser reduction, `mineRedu`** (Green Deal; scenario shock, EU27): "20" as `minfert_redu_uaa.gms`
  (mineral N per ha of land <= baseline x 0.8), "10/13/17/20crp" as `minfert_redu_by_crop.gms` (caps per crop group
  from the baseline's allocation, groups below 30 kg/ha and CAPRI's listed pairs held at baseline - read from the
  GAMS file by year, `tools/build_mineral_redu_rules.py` - the "f2f" and "limCres" regulations in the inner model).
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
- **CAPRI's feed bulks** (`feedBlkPrice_`, `feedShareEqu_`; `tools/build_feed_bulks.py`): per member state cereals
  (FCER) and protein-rich feed (FPRO, with DDGS) are split into products by a CES (rho 6) on their prices; the
  bulk follows the member state's herds and rations, its price index goes to the rations and per-head feed costs.
  Replaces the single EU cereal index and cake index (`CAPRIModel._feed_shares`, `_cake_feed_shares`,
  `FEED_DEMAND_COMMODITIES` removed).
- **Non-EU DDGS feed** from CAPRI's p_ElasFeed; `feed_demand_nonEU.json` now built by
  `tools/build_feed_demand_nonEU.py` (reproduces the earlier 125 entries exactly; adds DDGS and Ethiopia).
- **Non-fuel ethanol processing** from CAPRI's `ProcNQ_` (own-price Hessian `p_hessNQProc`).
- **Mandate shock** `PolicyScenario.biofuel_mandate` (`change_biof_mandate.gms`), `run_f2f_2030.py --biofuel-mandate`.
- Farm-to-Fork 2030: gap 3.31; beef/pork/poultry prices +0.4–0.6 points; EU DDGS −7%, price −3.8%. Baseline:
  DDGS within 2.3% of CAPRI, domestic-use median deviation 3.7%. 81 tests. docs/BIOFUEL_MARKET.md.

## Sprint 9c: endogenous biofuel markets, CAPRI's BIOF_M (October 2026)

- **Bio-ethanol and bio-diesel are market commodities** (37 now) with CAPRI's equations per CAPRI market region:
  supply on the processing margin (`SupplyBiof_`; non-agricultural, second-generation and exogenous output fixed),
  use from the mandate plus a sigmoid in the price against fossil fuel (`biofDemShare_`, `biofDem_`, `Cpri_`),
  bilateral trade with CAPRI's 2030 flows and Armington elasticities (rho1 2.2, rho2 4.5). Calibrated as
  `biofuel/def_biofuel_params.gms` to CAPRI's 2030 reference (`tools/build_biofuel_market.py`, replacing
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
  results of the run's year (`tools/build_bilateral_market.py`: 2017 base market, 2030 Green Deal reference);
  CAPRI's flows kept at calibration with domestic sales absorbing the model's production; baseline runs
  recalibrate at each outer iteration (reference prices); successive linearisation with an exact Newton solve
  per product. Replaces one world price per commodity and the EU premium (kept as `"premium"`).
- **EU tariff-rate quotas** with CAPRI's sigmoid (slope 200 around 97% of the quota), solved per quota with its
  flow. In CAPRI's 2030 reference the EU's meat quotas are far from filled: no effect under Farm-to-Fork.
- **Market products as CAPRI trades them**: wheat = soft + durum (durum price follows), olive oil and milled rice
  at CAPRI's processing yields (`tools/build_processing_yields.py`); the invented durum world market removed.
- **Projection fixes**: CAPRI's trend projection read by the model's names and regions
  (`tools/build_trajectory_model_keys.py`: 246 of 248 regions had fallen back to EU medians); livestock output
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
- **World market base from CAPRI** (`tools/build_world_market_baseline.py`, `world_market_baseline.json`): every
  region's base balance of 32 market commodities from CAPRI's FAO_agg (base period), and the EU's base
  self-sufficiency from it. Before: world sugar was sugar cane (1,768 Mt vs 168), pork 171 Mt (120), eggs 126 (84),
  maize 1,591 (1,136), wine 70 (27) from an extract and invented allocations.
- **Sugar as CAPRI makes it** (`tools/build_sugar_processing.py`, `sugar_processing.csv`): sugar = beet x the
  member state's sugar per beet (CAPRI 2030 reference; EU 0.156, not the fixed 0.135); beet's price follows the
  sugar price (`arm/set_prices.gms`); the world sugar-beet market removed.
- **Placeholders removed**: FATS and OFOD_M markets (no supply, no use, invented data). **Rye and oats** reach the
  other-cereals market (they reached none). **Dairy products** without the dairy block at CAPRI's member-state
  yields (cheese 0.068 t per t of milk, was 0.0456).
- **Baseline reproduction check** (`tools/compare_baseline_capri.py`, docs/BASELINE_REPRODUCTION.md): the 2030
  baseline against CAPRI star 3.0's own 2030 reference, no version gap. Median deviation: activity levels 9.5%,
  production 9.4%, domestic use 11.3%, relative prices 28%. Findings: fattening bulls and heifers, fruit and
  vegetable prices, 2030 self-sufficiency, milk yield. `capri_eu27_levels_2030_ref.csv` (EU levels) replaces the
  file the projection test used, which held France's levels.
- Farm-to-Fork 2030 gap 4.36 -> 4.51: beef price +9% (+12.8 before; CAPRI +24), poultry +16% (+20.6; +18), pork
  +21% (+19.6; +43). The EU premium approximation responds to CAPRI's world size by lowering the beef premium; the
  full bilateral market is planned (docs/ARMINGTON_MARKET.md, Sprint 8).

## Dairy Stage 4: CAPRI's dairy block outside the EU (October 2026)

- CAPRI solves its dairy block in every market region, with raw milk from its own supply function outside the
  EU. `tools/build_dairy_world_blocks.py` (53 non-EU market regions -> 24 trade regions) and
  `MarketModule._dairy_world_params` / `_dairy_solve`: each region's butter, SMP, cheese and whey now respond
  through its raw milk supply (CAPRI elasticities 0.7-1.0) and its dairies' product choice, instead of a flat
  0.2-0.3 elasticity per product. The EU and non-EU blocks share one solver (`_dairy_algebra`).
- Farm-to-Fork with the blocks: world dairy prices +2.6-3.5% (before 5-8%), raw milk +28% (+30%), gap 5.35. The
  rest of the milk price comes from inside the EU: the products that clear in the EU (fresh milk products about
  half of the milk) have inelastic demand and fixed trade. The blocks stay opt-in (`--dairy-block`).

## Cattle genomics in the supply model; dairy Stage 3 (October 2026)

- **Cattle genomics** (`envind/breeding.gms`; `tools/build_genetics_effects.py`, `genetics_effects.csv`;
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
- **Livestock output by CAPRI final product** (`tools/build_livestock_products.py`,
  `livestock_output_by_product_coef.csv`): the market bridge splits each animal's output at the region's own
  composition - dairy cows into milk and cull-cow beef (now in the beef market), sheep and goats into meat and milk
  (5.3 Mt of sheep "meat" was mostly milk; sheep milk is now raw milk and its value moves with the milk price,
  `SHGP.MILK`), laying hens into eggs and hen meat. Replaces milk = dairy-cow output x 0.9575. Sheep and goats
  -12.8% (CAPRI -9.5; -14.9 before).
- **World dairy-product balances from CAPRI's FAO_agg** (`tools/build_dairy_world_markets.py`): CAPRI's codes BUTT,
  SMIP, WHEP never matched the market's BUTR, SKIM, WHEY (every region got an invented share of a hard-coded world
  total) and the primary cheese item was not cheese (USA 28 kt against CAPRI's 5,889).
- **CAPRI's dairy processing** (`MarketModule.dairy_block`, `tools/build_dairy_processing.py`,
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
  `tools/build_manure_n2o.py` now keeps housing effects for HOUSN_'s options only.
- Farm-to-Fork 2030: manure N2O -28.8% -> **-21.5%** (CAPRI -3.2%); gap 4.71 -> 4.64. The technologies' share is now
  reported (`ghg_manure_n2o_tech`): -1.8 Mt CO2eq, against +6.2 Mt for CAPRI's ammonia technologies (JRC121368
  Table 18: housing and storage +0.9, application +5.2). Of the model's -1.8 Mt, nitrification inhibitors on manure are
  -4.8 Mt (43.7% adoption, -36% application N2O) - more than CAPRI's -1.8 Mt for ALL inhibitors, mineral included; the
  ammonia options alone add +2.9 Mt. The open part is the manure inhibitors' adoption: CAPRI's own cost terms for
  that option (target N2OMAN) are not in the data received; the model uses the mineral option's (86 EUR/t N) with
  CAPRI's default calibration.

## CAPRI's bull and heifer splits (Sprint 7c); Friesland (October 2026)

- **Bulls and heifers at two intensities**, as CAPRI (BULL/BULH, HEIL/HEIH; `tools/build_cattle_intensity.py`,
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
  `tools/_model_regions.py` now holds the NUTS splits and merges and builds region groups: per-head tables divide a
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
  `tools/build_capri_baseline_surplus.py` through the NUTS correspondence plus NUTS splits and merges (FI1D = FI13 +
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
  (`tools/build_manure_n2o.py`).
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
- **Histosols** (`histosol.csv`, `tools/build_histosol.py`): organic-soil shares (p_OrgSoilOri), climate-weighted IPCC
  2013 factors (FAO land use 2000 by climate zone), and CAPRI's fallowing option (no_histosols.gms: idled histosol
  area still occupies its land; CAPRI's curvature from its calibration runs; linear term from the model's own base
  land dual). Fallowing stays ~0 under Farm-to-Fork (Table 17: 2% -> 9%): the model's land rents at base are a few
  EUR/ha (CAPRI's ~100), so the rent fall that drives CAPRI's adoption is absent.
- 2030 Farm-to-Fork: GHG total (now every source) 401 Mt in the baseline (CAPRI 372), -20.4% (CAPRI -14.8; -17.0
  before, without soil N2O); gap 5.73 -> 5.81. Manure N2O -18.4% against CAPRI's -3.2% is the largest source gap,
  now visible in `tools/compare_runs.py`. Tests 65/65.

## Sprint 7b - CAPRI's two dairy activities, DCOL and DCOH (October 2026)

- CAPRI models dairy cows as a low-yield (DCOL) and a high-yield (DCOH) activity, half the herd each at base, with
  their own milk, feed requirements, manure N, costs and PMP terms (Brittany: 5,357 vs 8,927 kg milk, 126 vs 212 kg
  N per cow). As for the grassland split, the model keeps DCOW and adds the cows moved from DCOH to DCOL as one column:
  manure rows (N balance, manure application, crop-need limit, mineral-N allocation) by the manure-N change, the
  cows' energy, protein and dry-matter rows in the conic feed block by the requirement changes, CAPRI's PMP terms
  (p_pmpQuadTechn), linear term calibrated on the base duals (the requirement rows' included), milk revenue under the
  current milk price; milk output, manure N2O and ammonia follow it. Data `dairy_intensity.csv`
  (`tools/build_dairy_intensity.py`).
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
  `cover_crops.csv`, `winter_cover_share.csv` (`tools/build_cover_crops.py`). REGISTERED: CAPRI subtracts winter
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
- Sensitivity option `tools/run_f2f_2030.py --capped-regions` (model setting `jrc_capped_override`, carried to the
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
  calibrated on base duals. Data `grass_intensity.csv` (`tools/build_grass_intensity.py`).
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
  `tools/compare_qp_solvers.py`). Regional models with feeding inside were already conic and solved by Clarabel.
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
  feed cereals; CAPRI's 2030 PRME for premiums (`tools/build_price_trajectory_2030.py`,
  `capri_mod/projection/prices.py`; `--base-prices` restores 2017 prices).
- CAPRI's Farm-to-Fork reference (`refpol_endotech_all_ini`, `_max`) extracted: per-activity marginal terms and
  2030 unit values (`tools/extract_capri_marginal_terms.py`, validation only).
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

- `tools/validate_gnb_eurostat.py`: base balance against Eurostat's gross nutrient balance by member state
  (mineral 0.99, manure 1.14, pig manure 1.76 — CAPRI's own pig coefficients, as JRC96482 found).

- `use_feed_in_supply = True` (model and supply module); `run_f2f_2030.py --no-feed-in-supply` for the old path.
  Farm-to-Fork average gap 7.69 → 6.73, converged in 12 iterations; anchors and tests unchanged.

## Sprint 2 (in progress) — manure value (October 2026)

- `EnvironmentalModule._manure_marginal_factor`: mineral N replaced per unit of manure N at CAPRI's marginal
  availability under `endoManAvFact` ((g0 + b m0) / mineral efficiency, b = −0.0015 flattened as in
  `fert/endoManAvail.gms`), from the reference run's per-region deliveries; the minimum-floor reduction removed.
- `tools/build_capri_gnb_components.py`: also extracts `fertDist_excr/mine_perha`,
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
| **EU ration data built; impossible rice data removed** | `tools/build_feed_ration.py` builds base rations, nutrient requirements, contents and feed prices for every EU region and animal from CAPRI's 2017 results (235 regions, 2,084 entries, energy and protein closing exactly). `pari_activity.json` turned out to be an undeclared source extract no longer read at run time and was removed; La Rioja's rice (81 ha at an impossible 25.4 t/ha) was removed from the live tables |
| **EU tariffs set to CAPRI's** | EU tariffs now equal CAPRI's 2017 total protection on EU imports (ad valorem, specific duties and quota effects together). Several were far off — sheep meat 52% vs 0.1%, cheese 40% vs 6%, butter 82% vs 38%, whey 12% vs 66% — while beef was already close (65% vs 58%). The effect on Farm-to-Fork meat prices is tiny, which shows the meat-price gap comes from market structure, not tariff levels |
| **Loose ends closed** | Olive world price per tonne of olives from CAPRI's olive-oil price and EU oil yield (21.3%); whole milk powder mapped; other oilseeds confirmed to have no CAPRI world price; the sheep 'arbitrage' anomaly traced to a code collision (CAPRI's SHGM is the dairy-sheep activity), correcting an earlier explanation; German land rents now official Destatis 2016 values by federal state (mean €304/ha, was a uniform derived €172). The EU oilseed seed balances now use CAPRI's data (EU rapeseed crush within 1.3% of CAPRI's, was +10%), which also exposed and fixed a latent crushing bug: the EU base crush read a value that calibration later rescales |
| **Comparison with CAPRI: modules and coupling** | `docs/CAPRI_COMPARISON.md`: every capri-mod module against its CAPRI counterpart, a link-by-link coupling scorecard, the Farm-to-Fork validation read against it, and the remaining gaps in order of effect |
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
| **Farm-to-Fork figures were a 30-region subset** | Every F2F number reported here had been computed on the first 30 regions in index order — all German and Austrian, containing almost no permanent crops. EU-wide over all 248 regions the model under-responds: cereals 0.44x of CAPRI, oilseeds 0.73x, permanent crops 0.40x, where the subset showed 1.22x, 1.25x and 0.72x. The claim "all three within ±25%" was false. Same failure as `max_outer_iter=1`: a convenience setting became a published result. Comparison now lives in `tools/run_policy_comparison.py`, EU-wide and converged by default |
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

`tools/check_doc_coverage.py` asserts that every registry entry recorded as a new
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

`capri_data/validation/REGRESSION_ANCHORS.json` + `tools/check_regression.py`.

A machine-checkable snapshot of the numbers that **external references**
validated. It reports *which validation broke*, not merely that a number moved —
each anchor names the reference it was checked against, so a failure points at a
source you can go and re-read.

```bash
python tools/check_regression.py            # exit 1 on breach
python tools/check_regression.py --update   # accept an intended change
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
