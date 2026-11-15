# Validation plan

**Codes used in this document.** The plan's internal codes are kept here as written; what they stand for:

- **G1-G3.4**, the market programme (MARKET_IPOPT_DESIGN.md section 6, MARKET_SYSTEM.md): G1 the trade systems' exact Jacobian in CasADi; G2 the Newton-Krylov solve of the same equations, with G2a-G2g the market's blocks written in CasADi (a the quotas' sigmoid in the trade system, b market supply ProdNQ_ and the pooled commodities, c human consumption GL, d feed FeedNQ_ and FeedBal_, e processing and crushing, f the dairy blocks, g biofuels, young animals and raw milk); G3 the whole market as one system of equations in CAPRI's form (capri_mod/market/market_system_ad.py, market_chain.py); G3.0 the refresh of MARKET_EQUATIONS_INVENTORY.md (13 November 2026); G3.1 the capture and replay of market solves; G3.2a-e the system's blocks (import prices, the trade system, the supply side, the use side, the assembled system); G3.3 the choice of solver (the trials and the solver battery); G3.4 CAPRI's bounds, their widening and the fudge equations (MARKET_BOUNDS_PLAN.md); G3-R the regression check (the system reproduces the default solve's equilibrium); G3-C each change to CAPRI's form checked against CAPRI.
- **S1-S13**, the structural gaps (STRUCTURAL_GAPS_PLAN.md): S1 CAPRI's two crop technologies T1/T2; S2 CAPRI's split activities (GRAE/GRAI, OFAR/ROOF, VSET/FALL); S3 the fertilisation block's scaling; S4 manure P and K trade; S5 the ammonia options without an N incentive; S6 the other regional NLP departures; S7 CAPRI's market calibration; S8 one EU trade block; S9 the cattle member splits; S10 the mitigation options not built; S11 the quantities rebuilt from CAPRI's reported results; S12 the solver; S13 LULUCF carbon and the carbon price on land-use change.
- **P1, P2** (MODEL_CONTENT_PLAN.md section 12a): P1 the obligatory set-aside; P2 the port of CAPRI's premium module (P2a the premium cut, prmcut.gms; P2b the declared premiums, policy.gms; P2c the basic payment scheme, the rural development payments, the Nordic aid and the 2004-2013 regime; P2 step 2 the 2030 baseline premiums from the ports).
- **D2** (MODEL_CONTENT_PLAN.md): CAPRI's full list of non-EU supply countries as the default.
- **Refactor stages 1-5** (ARCHITECTURE_REFACTOR.md section 3): 1 the market split by block; 2a the market's data adapter; 2b the market's parameters and state; 3 the supply (3a its methods into block mixins, 3b its data adapter, the second half its parameters and state); 4 the environment and the coupling (4a and 4c their methods into block mixins, 4b the run's data adapter, the second half their state); 5 the scenario and reporting layers.
- **Short names of documents:** MID MARKET_IPOPT_DESIGN.md; G3I MARKET_EQUATIONS_INVENTORY.md; GR and G_REVIEW MARKET_NLP_REVIEW_2026-11-01.md; SGP STRUCTURAL_GAPS_PLAN.md; KI KNOWN_ISSUES.md; REG CAPRI_DEPARTURES_REGISTER.md.

Status: 5 November 2026, written at the project lead's request. The validation runs in five stages: the reference
material, internal validation with its fixes until the model is complete, a first external phase with the University
of Bonn, the fixes it brings, and the final external validation. One expert contract covers both external phases.
What stands today is in README section 9 (Validation) and capri_data/validation/VALIDATION.md; this file is the plan.

| Stage | What | Who | Ends when |
|---|---|---|---|
| 1 | Reference material: what is held, what is trusted, what is missing | CC-MOD | the missing files are requested |
| 2 | Internal validation against CAPRI's files, with fixes, until CAPRI-MOD is complete | CC-MOD | the completion gate (stage 4) |
| 3 | External phase 1: reference runs and a reaction to the scope and the departures | Bonn, CC-MOD | the protocol is agreed and the first two runs are delivered |
| 4 | Fixes from phase 1; completion gate | CC-MOD | CAPRI-MOD complete (list in stage 4) |
| 5 | External phase 2 and final validation | Bonn, second reviewer, CC-MOD | the written assessment and the tagged release |

Every finding, at any stage, is classified once: an **error** (CAPRI-MOD differs where it claims not to: fixed, tested,
run), a **departure** (deliberate: registered in docs/CAPRI_DEPARTURES_REGISTER.md with its reason and effect), or a
**CAPRI anomaly** (a defect in CAPRI's own code: the register's FIX or KEPT sections).

## 1. Reference material

### 1.1 Held: CAPRI's own files (trusted)

Each file's origin and the builders that read it are in docs/EXTERNAL_SOURCES.md.

| File | What it is | Validates |
|---|---|---|
| CAPRI's GAMS code (gams.zip) | star 3.0 source tree | the equations (each port cites its lines) |
| res_17<MS> (res_17zip.zip, capreg.zip), capri_export DATA2 | CAPREG's 2017 results | the base year's reproduction |
| coco2.zip | COCO's output, 1984-2019 | the data pipeline's COCO step |
| Capreg_tseries.zip | CAPREG's time series | CAPTRD's inputs |
| results_1770.gdx, trends_1730.csv | CAPTRD, base 2017, to 2070 | CAPTRD-MOD in parity mode |
| res_2_1730greendeal_refpol_endotech_all_ini and _max | CAPRI's 2030 reference with endogenous technologies (calibration runs) | the 2030 baseline; the CAPRI-reference trajectory (K116); the technologies' shares |
| res_2_1730greendeal_ref | CAPRI's 2030 Green Deal reference | the 2030 baseline |
| res_2_1730cap_after_2014_ref and _without_voluntary_coupled_support | a CAPRI scenario pair | supply response to payments (tools/run/run_vcs_2030.py) |
| markmarket_greendeal_1730et_base_1717.txt, data_market_1730, elas_2_1730, elas_2_1717, supply_elas_2_1720<MS> | market dump, market data, elasticities | the market's parameters |
| pmppar_21730<CC> (tools/gams/export_pmp_2030.gms), estnlp | CAPRI's 2030 PMP terms and estimates | the supply models' calibration |
| costsavings_ini_21730_jul15, priFertDist_1730 | mitigation calibration, fertiliser distribution | the mitigation options and the inner fertiliser model |
| scen_greendeal_2030 | CAPRI's maximum-mitigation run (K38) | mechanisms only: it is not a Green Deal scenario result |
| JRC121368 (published), the EU agricultural outlook 2020-2030 | CAPRI's Farm-to-Fork figures (another CAPRI version); DG AGRI's outlook | Farm-to-Fork, with known version gaps; the 2030 levels |

### 1.2 From the project lead's own runs

- **sim_ini_21730.gdx: used.** Written during data preparation, before any simulation solve. The one NLP on that path
  (the modified Armington calibration) is verified by CAPRI's own CNS check, which aborts the run if it fails. Read for
  CAPRI's code lists, the border measures, the non-EU land market and the calibration-point market state (test A).
- **Not used:** data_cur, market_model, cur_step, iy and supply_model GDX files (runs with IPOPT forced on CAPRI's
  NLPs; the 2030 endotech run of 4 November 2026 left about 97,000 market infeasibilities in every loop).
- **Kept for later:** capri_sources/datam_mirror_2040 (the JRC DataM 2040 extracts, a future CAPTRD-MOD check).

### 1.3 Missing: to request

| What | Why | Settles | From |
|---|---|---|---|
| CAPRI's Farm-to-Fork and Green Deal 2030 results (GDX) | the scenario targets against CAPRI itself, not a report of another version | K13, K29, K66, K78, K92 | Bonn |
| A market-only shock run (e.g. an EU tariff cut on one product group) | the market alone | test B; the beef and poultry price gap | Bonn |
| A livestock or feed scenario | herds, rations, young animals | K47, K48, K65 | Bonn |
| CAPRI's market state at a solved simulation step | test B from CAPRI's own state | test B | Bonn (CAPRI's debug_store_market_data, or one dump line after the market solve) |
| Settings and convergence logs of the CAPRI runs held (refpol endotech, the VCS pair, CAPTRD 1770) | to document them as references | the references' status | Bonn or the CAPRI team |
| A CONOPT licence | CAPRI runs repeated in-house | independence from Bonn for reruns | CC-MOD |

## 2. Internal validation and fixes (now until the model is complete)

The loop for every gap: compare, open a KNOWN_ISSUES entry, diagnose, fix or register a departure, then a mini-EU run,
a full Farm-to-Fork run and the test suite before the change reaches dev.

| Check | Reference | Tool | State on 5 November 2026 |
|---|---|---|---|
| Inputs reproduce CAPRI's symbols; mechanisms reproduce CAPRI's per-unit results | CAPRI's files and code | capri_mod/tests/test_capri.py | in the suite |
| Base year 2017 | CAPREG | the base reproduction tests | in the suite |
| 2030 baseline | CAPRI's 2030 reference | tools/check/compare_baseline_capri.py | K116 (trajectory) waiting for its full run |
| Market at the calibration point | sim_ini_21730 | tools/check/check_market_base.py; test A with G3 | test A to build with G3 |
| Supply response to payments | the VCS pair | tools/run/run_vcs_2030.py | to rerun after the market move |
| Farm-to-Fork 2030 | JRC121368 | tools/check/compare_runs.py --capri | r213: deviation 4.59 over 20 indicators (gate 16: 4.18) |
| Green Deal 2030 | none yet | the gate run | not run since the market move |
| 2030 levels | the EU outlook | docs/OUTLOOK_2030_CHECK.md | to rerun |

What the model needs before the completion gate, in the agreed order (MODEL_CONTENT_PLAN §14, decision log of
5 November 2026):

1. The market: the quotas inside the price solve; the baseline demand recalibration removed (S7).
2. The model's content: the activity gap (S1/S2, done), the market's land-use change (luc_market, done 9 November
   2026), the regional NLP departures one by one (S6), S11 and K65. No-till and legume share (S10) and the LULUCF carbon
   (S13) with the carbon-tax scenarios (the project lead, 9 November 2026).
3. Before CAPTRD-MOD: the premium module (P2) with obligatory set-aside (P1); the data layout by role; G3, the whole
   market as one IPOPT system, as decided (MARKET_IPOPT_DESIGN §7.2; before CAPTRD-MOD, the project lead's correction of
   6 November 2026); then CAPRI's full list of non-EU supply countries as the default (D2; moved before CAPTRD-MOD by
   the project lead, 9 November 2026).
4. CAPTRD-MOD with its parity mode, then the projection layer.

## 3. External phase 1 (University of Bonn)

| We provide | We need |
|---|---|
| A scope note: what is built, what is simplified, the intended applications | The 2030 reference run (refpol_endotech_all, ini, max and sup) with its settings and log |
| The departures register, KNOWN_ISSUES, the decision log | The market-only shock run, and the market state at a solved step |
| A draft benchmark protocol (stage 5's tests, tolerances, pass criteria) | Their reaction to the scope and the departures: which they find material |
| The repository at a tagged version | The protocol agreed |

Preconditions before signing: CAPRI's licence and data rights for an open GPLv3 package; the CAPRI network's view of an
open Python port; the contract's scope and its day split between the phases.

## 4. Fixes from phase 1; completion gate

Each finding of phase 1 goes through stage 2's loop. The gate to phase 2: the items of section 2 built and tested,
the open issues listed with their status, and the reviewer's guide written (where each mechanism lives, CAPRI's file
next to the Python module).

## 5. External phase 2 and final validation

| Test | Question | Pass criterion |
|---|---|---|
| A. Equation-level replication | are the market equations CAPRI's, at CAPRI's solved state? | scaled residual at most 1e-5, 5e-4 as a ceiling (G_REVIEW Q5.2) |
| B. Solve replication | does a shock reach CAPRI's equilibrium? | to agree with Bonn |
| C. Supply-model replication | do the regional models give CAPRI's response at CAPRI's prices? | to agree with Bonn |
| D. Full runs | do the reference scenarios reproduce CAPRI's changes? | per-indicator threshold to agree; each gap above it explained |
| E. CAPTRD parity | does CAPTRD-MOD reproduce CAPTRD as coded? | CAPTRD's results to the precision of its files |
| F. CAPTRD-MOD improvements | are the fixes and ML additions improvements? | assessed separately, each switchable, against parity mode |

| We provide | We need |
|---|---|
| The complete model, the reviewer's guide, the benchmark results of tests A to F | The CAP payment, livestock or feed, Farm-to-Fork or Green Deal, and CAPTRD reference runs |
| Our classification of every finding | Bonn's written assessment; a second reviewer's assessment of credibility |

The final validation ends with: a validation report (the protocol, each test's result, each finding and how it was
closed); README section 9 and FITNESS_FOR_USE.json updated; a tagged release that the report cites.

## 6. Open questions

- A second reviewer outside the CAPRI network: possible, and under which arrangement?
- Does the contract cover producing the reference runs, or only the review?
- The day split between phase 1 and phase 2.
- Is the recursive-dynamic mode (CAPSIM-DYN) in this validation or a later one?
- Which intended applications define a material difference?
- Who approaches the CAPRI network on the licence and the open port, and when?
