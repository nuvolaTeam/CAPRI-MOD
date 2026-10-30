# Register of departures from CAPRI and of CAPRI code errors

This is the single list of every place where capri-mod does not do what CAPRI star 3.0 does, and of every error found
in CAPRI's own code, fixed or kept. It was started on 30 October 2026 at the project lead's request, from a sweep of the
code, the settings and the documents. Details stay in the documents named in each row; this file is the index that must
be complete.

**Rule.** A new departure, or a CAPRI code error found while porting, gets a row here in the same commit that
introduces it. A row is removed when the departure is removed, and moves to the short history at the end. Our own
extraction or porting errors are not departures: they are fixed and go in KNOWN_ISSUES or the CHANGELOG, not here.

**References.** CAPRI files are GAMS files under `gams/` of CAPRI star 3.0 (the copy in `allgms/gams`). "Verified" means
the cited CAPRI line was read and says what the row claims. capri-mod code is cited by module and function, because
line numbers move.

Kinds of row:

| Kind | Meaning |
|---|---|
| **FIX** | CAPRI's code is in error; capri-mod's default corrects it. A setting reproduces CAPRI as coded (the parity switch). |
| **KEPT** | An error or anomaly found in CAPRI's code, reproduced as coded on purpose. |
| **DEP** | A departure in force by default that is not a bug fix: a simplification, a part not built yet, or a choice. |
| **BEYOND** | An addition beyond CAPRI. It is off by default, or it only reports and leaves the results unchanged. |

## 1. CAPRI code errors fixed (FIX)

| ID | What | CAPRI | capri-mod | Setting (default; CAPRI as coded) | Status | Details |
|---|---|---|---|---|---|---|
| FIX-1 | Anaerobic digestion on dairy cows has no effect on manure CH4: the dairy rows are zeroed. | envind/ad_data_and_cali.gms l. 588 (verified) | environmental module, AD effects | `environment.ad_dairy_ch4 = "fix"`; `"capri"` | in force since 20 Oct 2026 (project lead) | DEPARTURES_FROM_CAPRI.md; AD_SPEC.md §0.5 |
| FIX-2 | Low-emission manure application *raises* the leaching share in LEACHN_ (`+ v_ammoAppLeaAgg`), against CAPRI's own literature table and against the same options' runoff term. | supply/supply_model.gms l. 3413 (verified); ammo_tech.gms l. 2293; prep_data_LitRev p_reducGains | supply/n_leaching.py | `environment.ammapp_sign = "consistent"`; `"capri"` | in force since 20 Oct 2026 (project lead) | DEPARTURES_FROM_CAPRI.md; N_CASCADE_SPEC.md |
| FIX-3 | CAPTRD Step 1: series with 2–4 observations get Step1 = 0, because the minimum over the trend grid counts the 29 zeroed grid points. Confirmed in CAPRI's output: 92 of 93 such series have Step1 = 0. | captrd/estimate_trends.gms l. 158-171 (verified) | pipeline/captrd/step1.py | `captrd.short_series_grid_as_coded = false`; `true` | default since 23 Oct 2026, **awaiting the project lead's confirmation** | DEPARTURES_FROM_CAPRI.md; CAPTRD_MOD.md §12.4 |
| FIX-4 | CAPTRD error-variance floor compares a level with a variance: max(0.05·\|wAve\|, wVarErr). The fix squares the level term. | captrd/define_stats_and_supports.gms l. 327-329 (verified) | pipeline/captrd/supports.py | `captrd.variance_floor_squared = true`; `false` | in force since 24 Oct 2026. No effect on results until CAPTRD Steps 2–3 are ported | DEPARTURES_FROM_CAPRI.md; CAPTRD_MOD.md §12.4 |
| FIX-5 | Green Deal input changes replace the technical-change factor TF_I instead of adding to it: `scenAugmentsTechChange` stays off because `gdversion` is empty. CAPRI's own note calls it "presumably by oversight". | capmod/define_inputs.gms l. 66-73; pol_input/greendeal/conventional_io.gms l. 361-362; greendeal_scenarios.gms l. 139; organic_io.gms l. 98 (verified) | supply module, Green Deal input changes | `supply.greendeal_inputs_keep_tech_change = true`; `false` | in force since 24 Oct 2026 | DEPARTURES_FROM_CAPRI.md |
| FIX-6 | Organic top-up of fuel and services is valued at INPO's unit value; CAPRI's comment says the cost should double on EFUL+SERI. | pol_input/greendeal/organic_io.gms l. 107-115 (verified) | supply module, Green Deal input changes | `supply.organic_topup_at_fuel_cost = true`; `false` | in force since 24 Oct 2026 | DEPARTURES_FROM_CAPRI.md |
| FIX-7 | CAPTRD's upper bound on artificial land (ARTIF) never binds because of a misplaced parenthesis. | captrd/fix_est.gms l. 810 (verified) | not built: CAPTRD Steps 2–3 are not ported | to come, with a parity switch | **decided 22 Oct 2026, not implemented** | CAPTRD_MOD.md §8.3; CAPTRD_MAP.md |
| FIX-8 | CAPTRD treats a zero as a missing observation. | CAPTRD convention (CAPTRD_MAP.md §9 point 1) | pipeline/captrd/step1.py **keeps CAPRI's convention** | none | **listed as fixed in CAPTRD_MOD.md §8.3, but not fixed in the estimator.** To be settled when the data layer separates zeros from missing values | CAPTRD_MOD.md §6, §8.3 |

## 2. CAPRI code errors or anomalies kept as coded (KEPT)

| ID | What | CAPRI | Why kept | Details |
|---|---|---|---|---|
| KEPT-1 | CAPTRD's error variance divides by nW − 1, which can be ≤ 0 for a series observed only in the earliest years. | captrd/define_stats_and_supports.gms l. 118-123 (verified) | No such series in the reference run: 0 of 143,226 with more than 2 observations. | CAPTRD_MOD.md §12.4 |
| KEPT-2 | CAPTRD's NUTS-2 column filter deletes nothing: NT2 is not controlled inside the SUM. | captrd.gms l. 872-876 (verified) | Ported as coded (pipeline/captrd/prepare.py, clean_regions). **A fix is for the project lead to decide.** | CAPTRD_MOD.md §12.4 |
| KEPT-3 | AD cost curve discount rate: ammo_tech.gms re-declares 0.035, overriding the 0.05 set in the AD file. | envind/ammo_tech.gms l. 1203; envind/ad_data_and_cali.gms l. 397 (verified) | Reproduces CAPRI's results (tools/build/build_ad_option.py). | AD_SPEC.md §1.3 |
| KEPT-4 | AD investment cost p_CAD multiplies kW per head by farm size in LSU, a unit mismatch. | envind/ad_data_and_cali.gms l. 465-468 (cited in AD_SPEC, not re-read) | "CAPRI as coded; replicate it." | AD_SPEC.md |
| KEPT-5 | COCO's zero-flag removal: the inner SUM tests the outer position, not MrkBaleE1. This is our reading; no CAPRI document calls it an error. | captrd/load_coco1_data.gms l. 239-247 (verified) | Ported as coded (pipeline/captrd/coco.py). | coco.py comment |
| KEPT-6 | CAPRI's code raises the initial covered-storage shares to the Nitrates Directive minimum; its reference run does not. | ammo_tech.gms p_helpManStor l. 2676-2709 (cited, not re-read) | capri-mod follows CAPRI's results, not the code text (APPLY_ENV_COVER off). | N_CASCADE_SPEC.md |
| KEPT-7 | The Green Deal policy file sets the Nitrates Directive switch NDman only after an `$exit`, so the 170 kg N/ha manure cap is off in Green Deal runs. | envind/envConstraints.gms l. 2876-2933 (cited, not re-read) | capri-mod follows CAPRI's effective behaviour: no manure-application row. | KNOWN_ISSUES K105 |
| KEPT-8 | CAPRI's N excretion of fattening pigs is above national and literature values. This is data, not code. | JRC96482 Table 4.5 | Kept as CAPRI has it. | COUPLING_SPRINTS.md |

The CAPTRD base-year window BASYRS5 ("5 years" written as \|t − BAS\| ≤ 3) was listed as a defect, but it is not one
when the ex-post data end at BAS + 1, as in the reference run (`captrd.basyrs5_halfwidth = 3`, CAPRI's value;
CAPTRD_MOD.md §12.4).

## 3. Departures in force by default (DEP)

### 3.1 Settings whose default is not CAPRI's (DEPARTURES_FROM_CAPRI.md, "DEPARTURE")

| ID | What | CAPRI | Setting (default; CAPRI) | Status | Details |
|---|---|---|---|---|---|
| DEP-1 | Outer-loop iteration cap of 60. | GUI STEPS 99 (gui/capri_gui_definition.xml l. 2891-2897, verified) | `outer_loop.max_outer_iter = 60`; 99 | the project lead's choice, 28 Oct 2026 | DEPARTURES_FROM_CAPRI.md |
| DEP-2 | Fertiliser-option curvature without the saving term. | envind/ghgMiti.gms l. 1016-1050 | `supply.fert_slope_with_saving = false`; `true` | K77 open | DEPARTURES_FROM_CAPRI.md; KNOWN_ISSUES K77 |
| DEP-3 | One EU27 trade block instead of CAPRI's EU_WEST and EU_EAST. | aggregation/defaultA.agg | `market.eu_blocks = false`; `true` | option since 18 Oct 2026 | DEPARTURES_FROM_CAPRI.md |
| DEP-4 | Cattle member splits off: young animals pooled across sexes. | INPANI_ per sex; HEIR and calf activities | `supply.use_cattle_member_splits = false`; `true` | K65 open | DEPARTURES_FROM_CAPRI.md; KNOWN_ISSUES K65 |

### 3.2 Departures without a setting (parts not built, or a different form)

| ID | What | CAPRI | capri-mod | Status | Details |
|---|---|---|---|---|---|
| DEP-5 | The baseline run recalibrates market demand to the supply models' supply in every iteration, and scenarios inherit it frozen. The non-EU use factor is bounded to [0.2, 5]. | arm/market1.gms; simu_calibration_to_supply.gms | market/bilateral_solve.py, bilateral.py | in force (04_code_data_status: capri-mod) | DEPARTURES_FROM_CAPRI.md; PROXY_AUDIT S185 |
| DEP-6 | The water indicator's irrigated shares come from the regional irrigated area (IRR2), not from CAPRI's HPD fit to FSS crop data. | water_database.gms l. 325-640 (cited) | tools/build/build_irrigation_2017.py; water module | in force (indicator) | DEPARTURES_FROM_CAPRI.md |
| DEP-7 | Non-EU supply: ProdNQ_ at CAPRI's 2030 point with land rents held and no recalibration. The UK, Turkey and the Western Balkans (29 units) have no supply models. | arm/market_model.gms ProdNQ_; simu_calibration_to_supply.gms | market/supply.py, `_noneu_market_supply_nq` | in force | DEPARTURES_FROM_CAPRI.md; README §10.4 |
| DEP-8 | Mitigation options not built: LegSh, ConsTill, NoTill, UreaSubst, buffer strips, biodiversity, biochar, SupplementPerc_. Their leaching and runoff terms are held at CAPRI's reference. | envind/; ghgMiti.gms; supply_model.gms | supply/n_leaching.py | K93 open (3-NOP built; UreaSubst port started) | KNOWN_ISSUES K93 |
| DEP-9 | Activity set: 46 activities plus the dairy, grassland, bull and heifer splits, not CAPRI's full list. CAPRI's technologies are collapsed per activity in the PMP terms. | supply_model.gms | supply module | in force | NLP_PORT_DESIGN.md; MODULE_COUPLING_REVIEW.md |
| DEP-10 | The 14 registered departures of the regional NLP form: need multipliers; fertiliser calibration in RO21, RO22, RO31, RO41, RO42, ES62, HU11; the inner dual bound ±1000 (`fertiliser.npk_dual_bound_wide`); P and K manure trade following N; the Shannon term +1e-6; ecoSetAside held; LUC after the regional model; organic conversion per member state and crop class; Green Deal mineral caps exempted by solving (`fertiliser.exempt_cap_factor`); manure of the split columns; relaxation kept for the scenario; warm start cut at 200 IPOPT iterations. | supply_model.gms | supply/capri_regional_nlp.py; supply module | in force. Item (9) of K50 concerns the conic form, since removed | KNOWN_ISSUES K50 |
| DEP-11 | Emission-tax coefficients held at the baseline solution (a linearisation). | ghg tax in supply_model.gms | supply module | in force | MODULE_COUPLING_REVIEW.md; MITIGATION_IN_SUPPLY.md |
| DEP-12 | Plain CES second Armington nest: CAPRI's commitment terms p_arm2Commit are not represented. | arm/market_model.gms | market/bilateral.py | in force (registered in the code) | MODULE_COUPLING_REVIEW.md |
| DEP-13 | Livestock coefficients: CAPRI's 2017 totals divided by CAPRI's herd sizes (DATA2 HERD). | CAPREG data | builders | in force | MODULE_COUPLING_REVIEW.md |
| DEP-14 | Purchased feeds FENE and FMIL: price index 1 in projected years (no CAPRI unit value in hand). | — | — | in force | MODULE_COUPLING_REVIEW.md |
| DEP-15 | Ammonia options held at base shares without an N incentive. In CAPRI they are in the model, with the base as a first-order point. | ammo_tech.gms; supply_model.gms | supply module, `SupplyModule._amm_incentive` | in force | MODULE_COUPLING_REVIEW.md; KNOWN_ISSUES K63 |
| DEP-16 | Market solve: per-commodity Newton with Anderson acceleration (a fixed point) instead of CAPRI's one simultaneous CONOPT solve. MODULE_COUPLING_REVIEW.md states that it reaches the same equilibrium. The Newton–Krylov option is BEYOND-4; the planned IPOPT solve is step G. | arm/market_model.gms (solve) | market module | in force (numerical) | MODULE_COUPLING_REVIEW.md; MARKET_SOLVE_CHECK.md |
| DEP-17 | Manure pools: a Takayama–Judge primal solved with Clarabel and cleared between solves. | supply_model.gms (manure trade) | model, manure pools | in force (numerical) | MODULE_COUPLING_REVIEW.md; MANURE_MARKET.md |
| DEP-18 | Regional NLP warm and jump checks: re-solves from other starts and keeps the lowest objective. This can change which local optimum is kept. | — (beyond CAPRI's practice) | `supply.nlp_warm_check`, `nlp_jump_check`, `nlp_jump_gain` (on) | in force | CHANGELOG; KNOWN_ISSUES K75, K79 |
| DEP-19 | Farm-to-Fork follows JRC121368, not a star 3.0 file: manure trade off; tiered surplus rule with nine capped regions; the tiered N target replaced by JRC121368's EU-average cut (36%); pesticide yield loss 10% at a 50% cut; ghgTechMYld 0.2. A hand-built scenario also gets JRC121368's pesticide rule (`PolicyScenario.pesticide_rule = "jrc121368"`). | policy files of star 3.0 | policy/greendeal.py; policy/policy_module.py | in force | SCENARIO_SETTINGS.md; KNOWN_ISSUES K57 |
| DEP-20 | Green Deal 2030 targets and 2040 end points taken from a named batch that is not in the workspace (source open). | greendeal_scenarios.gms | policy/greendeal.py | in force; source open (04_code_data_status: open) | 04_code_data_status.sql |
| DEP-21 | Green Deal input changes act on CAPRI's 2017 coefficients (simulation-year coefficients not held). The organic target's fertiliser part keeps the model's crop mapping instead of CAPRI's NGRP groups. | pol_input/greendeal/*.gms | supply module | in force (registered) | ARCHITECTURE_REFACTOR.md |
| DEP-22 | Feed PMP slopes: CAPRI's 2030 SLOP aggregated with 2017 weights. | — | tools/build/build_feed_ration.py | in force (registered) | PMP_CAPRI_2030.md |
| DEP-23 | Activities of a calibrated part without a positive CAPRI own PMP term are held at their level: 71 cells at 2030, at most 2% of an activity's EU level. **Whether this is a departure is unresolved:** MODULE_COUPLING_REVIEW.md calls it "as CAPRI". | — | supply module, `_uncalibrated` | in force | PMP_CAPRI_2030.md |
| DEP-24 | P balance: removal and residues follow the realised yield; manure P2O5 per head is unchanged by split or option columns; the runoff share is weighted by manure N. | envind P balance | environmental / NLP | in force | P_BALANCE.md |
| DEP-25 | Winter cover: the row's right-hand side is at least the base point's, and under the tax the purchases' leaching stays at the reference share. | — | supply/capri_regional_nlp.py | in force (registered) | WINTER_COVER.md |
| DEP-26 | Young-animal price-ratio bounds of ±50 × base (CAPRI: ±10 × (\|level\| + 10)); Newton step at most 30%. | arm/market_model.gms (young animals) | market/supply.py, `_yani_clear` | in force (numerical guard) | KNOWN_ISSUES K37; 04_code_data_status.sql |
| DEP-27 | Stop rule: CAPRI's rule, plus the model's inner balances must settle (N-balance price, manure pools, young-animal balance, base calibration). | CAPRI's convergence test | utils/capri_stop.py | in force | DEPARTURES_FROM_CAPRI.md |
| DEP-28 | Where negative milk prices are not allowed (outside the Green Deal group), the member-state raw milk price is held at 1e-7 of base. CAPRI lowers a positive bound tenfold each time it binds. It never bound in runs r163 and r166. | arm/market_model.gms (dairy) | market/dairy.py | in force | DEPARTURES_FROM_CAPRI.md |
| DEP-29 | Norway's dairy products take the dairy block's milk price of the previous evaluation; the two are equal at a converged market solve. | arm/market_model.gms | market (`market.sup_milk_in_market`) | in force (solution path only) | DEPARTURES_FROM_CAPRI.md |

Two more differences apply only with non-default settings:
- With `market.eu_blocks = true`, the young-animal markets are updated between market solves instead of inside them.
- `outer_loop.capri_step_special` passes a smoothed price to the member state's models as a departure from its
  market's price. It is empty by default.

**Long tail.** Fallbacks, guards and solver devices registered one by one live in docs/design/audit/supply_claims.csv
(74 "registered" rows) and market_claims.csv (30 rows), and in the 'numerical' and 'capri-mod' rows of
capri_data/schema/04_code_data_status.sql. Most are guards, or apply only where data are missing. Section 6 lists the
ones known to be stale.

**Scope not yet built.** These are not departures in the model as it runs; they are recorded here for completeness.
- CAPTRD-MOD: Steps 2–3, the requirement functions and the farm types are not ported (CAPTRD_MOD.md §12.2).
- CAPRI's intervention stocks and Pillar II budgets are to be ported (PROXY_AUDIT).

## 4. Beyond CAPRI (BEYOND)

| ID | What | Setting (default) | Status | Details |
|---|---|---|---|---|
| BEYOND-1 | Run manifest: git state, versions, SHA-256 of every input read. | always on | report only | DEPARTURES_FROM_CAPRI.md |
| BEYOND-2 | Drift report of stop-rule items still moving in one direction. | `outer_loop.drift_report_steps = 3` | report only | DEPARTURES_FROM_CAPRI.md |
| BEYOND-3 | Market supply Hessian from the KKT first-order step (implicit function theorem). | `market.hessian_method = "capri"` (option `"kkt"`) | off | DEPARTURES_FROM_CAPRI.md |
| BEYOND-4 | Newton–Krylov market solve. | `market.solver = "fixed_point"` (option `"newton_krylov"`) | off; the default changes only after a full-run comparison. One market, Japan's sunflower cake (30 t, autarkic), has a flat family of equilibria that Newton–Krylov cannot select from | DEPARTURES_FROM_CAPRI.md |
| BEYOND-5 | Exact CasADi Jacobian of the trade systems. | `market.exact_jacobian = false` | off | ARCHITECTURE_REFACTOR.md §6 |
| BEYOND-6 | Former capri-mod options kept as alternatives: adaptive price step, capri-mod stop rule, PMP recipe terms, PMP cross terms "none". | `price_update = "capri"`, `stop_rule = "capri"`, `pmp_source = "capri2030"`, `pmp_cross_terms = "capri"` | off | defaults.toml |
| BEYOND-7 | Base-year comparative-static mode and the projection layer. | — | scope addition | README §10 |
| BEYOND-8 | NUTS-2024 reporting of results. | — | report only | MODULE_COUPLING_REVIEW.md |
| BEYOND-9 | The data schema: declared types, keys, ranges and rules checked on every data change. | — | data layer | DATA_SCHEMA_DUCKDB.md |
| BEYOND-10 | CAPTRD-MOD plans approved but not built: ML candidates for Step 1 (§8.2), the FAOSTAT bias correction (§8.1), CAPSIM-DYN recursive dynamics (§8.4). The §8.5 options are undecided. | — | design only | CAPTRD_MOD.md §8 |

## 5. History: departures removed or switched back to CAPRI

The settings switched to CAPRI's form are described in DEPARTURES_FROM_CAPRI.md, "Switched to CAPRI's setting". Also
switched to CAPRI's form:
- `market.noneu_supply_nq` and `market.feed_bulk_in_market` (29 October 2026);
- `market.hessian_scenario_iter` 8 → 0 (25–26 October; K75).

Removed:
- the manure-application row (170 kg N/ha; K105, 29 October);
- the bilateral export cap at 0.98 of S0 (K106, 30 October);
- the 0.05 cap on the PELA/p_pmpQuadPact cross terms (K105);
- the PMP elasticity calibration path (K61);
- the Anderson update of the supply–market loop (26 October);
- the conic form (26 October; K50).

Closures toward CAPRI recorded in KNOWN_ISSUES: K33, K37, K38, K40, K61, K62, K67, K73.

## 6. Documents to align with this register (found 30 October 2026)

- `ammapp_sign` and `ad_dairy_ch4` (FIX-1, FIX-2) are labelled "DEPARTURE FROM CAPRI" in supply/n_leaching.py,
  N_CASCADE_SPEC.md and SETTINGS_INVENTORY.csv (S201, S222). They are CAPRI-ERROR-FIX.
- NLP_PORT_DESIGN.md and SUPPLY_MODEL_MAP.md describe the PMP terms as capri-mod's own calibration. The default since
  22 October is CAPRI's 2030 terms.
- KNOWN_ISSUES K105 still counts the export cap as open; K106 removed it. market_claims.csv row 73 still says
  "registered".
- supply_claims.csv has stale rows: the manure-application row, the 0.05 cross-term cap, the legacy nitrate limit, and
  the rows of the removed modules feed_conic.py and intensity.py.
- PROXY_AUDIT.md gives the census counts as of 29 October. 04_code_data_status.sql has grown with the CAPTRD and
  Newton–Krylov numbers.
- SETTINGS_INVENTORY.md and .csv, and SCENARIO_SETTINGS.md, describe superseded defaults (market_supply_nq,
  absent_activities_fixed, max_outer_iter 25, adaptive damping).
- DEPARTURES_FROM_CAPRI.md, "Switched": add noneu_supply_nq and feed_bulk_in_market.
- CAPTRD_MOD.md: FIX-8 (zeros as missing) is listed as fixed, and FIX-7 as decided; neither is built. It names
  `capri_mod/projection/capsim_dyn/`, which does not exist yet.
