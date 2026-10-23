# Handoff: the regional supply model in CAPRI's own NLP form

*Written 20 October 2026 at the end of the session that produced `capri-mod-proto.zip` (this package). The project
lead keeps that zip as the fallback version; the new line of development starts from it.*

## Decision

Rewrite the regional supply model from CAPRI star 3.0's `supply_model.gms`, equation by equation, as CAPRI's own
**non-convex NLP**, solved with **IPOPT** (CasADi; CAPRI uses CONOPT, also a local NLP solver). The current convex conic
form (Clarabel) stays only as an option for comparison and as a source of starting points. The data and calibration
already built (PMP terms, prices, rations, fertiliser priors, land market, market model) are kept: only the regional
problem changes.

Why: the conic form is a convex approximation of a non-convex model, and its departures from CAPRI's equations keep
surfacing as failures (K49). Known departures:

| Part | CAPRI (supply_model.gms) | conic form now |
|---|---|---|
| Ammonia loss cascade | bilinear in housing / storage / spreading shares | tangent at the previous solution (K1), exact only at convergence |
| Fertiliser technologies | one regional share per technology | one share per crop |
| Feeding | per-head feed x herd (FEDUSE_, bilinear) | total feed per animal (same feasible set: exact) |
| Crop need | NUTNED_ equality per crop group and nutrient (N, P2O5, K2O), mineral purchases >= 0, over-fertilisation fixed at the base | one regional N row; mineral N may go negative (PT30); no P and K |
| Green Deal mineral caps (mineRedu by crop) | per crop group | regional total only; per-group caps only inside the inner model |
| Inner fertiliser distribution model | its first-order conditions (e_focFertDist) inside the supply model, every solve | checked after the conic solve; the coupled NLP (capri_nlp.RegionNLP with fd=) only where the allocation fails |
| Minimum mineral share NUTMIN_ | only with the inner model off (default on) | as CAPRI since K40 |

## Where things stand (this package)

- Validation: Farm-to-Fork gap to JRC121368 4.38 (20 indicators); Green Deal runs have no CAPRI reference (K38).
- 113 tests pass (`python -m pytest -q capri_mod/tests`, ~13 min on 2 cores).
- Run times alone on 2 cores: Farm-to-Fork ~11-13 min, Green Deal end-point ~22 min, Green Deal 2030 ~28 min (K41).
- Open issues: K45 (Egypt's oilseed rows), K47 (cattle-chain equilibrium sensitive to unrelated changes), K48
  (replacement-cow price vs CAPRI), K13 (milk price), K20, K33, K29.
- The audit's documentation findings (README + all docs rewrite) are still pending: scratch notes were not kept; the
  CHANGELOG and KNOWN_ISSUES are current.

## Tools for the new work

- `capri_mod/supply/capri_nlp.py` - RegionNLP: CAPRI's relations built with CasADi from the conic model's captured
  inputs (exact cascade option, per-head feeding option, the inner fertiliser model's FOCs). Useful pieces, but it copies
  the conic model's single crop-need row: the port must write CAPRI's equations, not reuse this as is.
- `tools/nlp_check` - solves regional problems in CAPRI's form and compares with the conic solution (docs/archive/NLP_CHECK.md).
- `tools/diagnose_fert_dist.py` - exact feasibility test of CAPRI's crop-group allocation at a saved solution
  (`CAPRI_FD_DUMP=dir` saves failing regions during a run).
- `CAPRI_FD_LOG=file` - per-call IPOPT log of the coupled solves (tries, iterations, build / solve seconds).
- CAPRI star 3.0 GAMS source: `allgms/gams` in the original working copy (supply/supply_model.gms,
  supply/prep_sim.gms, fert/*, arm/*) - to be uploaded again in the new chat if needed.

Step 1 (the equation map) is done: docs/SUPPLY_MODEL_MAP.md, with the decisions it raises (section 5).

## Plan agreed

1. Map `supply_model.gms`: every equation and variable, the switches star 3.0 uses by default and in the Green Deal
   batch, and for each: in CAPRI's form already / approximated / missing.
2. Write the regional model in CAPRI's form (IPOPT, warm start from the region's previous solution as CAPRI does;
   first start: the calibrated base or the conic solution). Measure run time early: if 248 regions x 12-25 iterations
   does not fit 30-minute runs, report before going further.
3. Check against CAPRI's own numbers: the base reproduces CAPRI's 2030 reference region by region; feeding, nitrogen
   balance, crop-group allocation and ammonia options reproduce CAPRI's levels and shadow values where our data hold them.
4. Rerun Farm-to-Fork, Green Deal (end-point and 2030), the coupled-support check (tools/run_vcs_2030.py) and the tests;
   explain every change against the current results.

## Standing preferences (project lead)

Accuracy, no overstatement; CAPRI's methodology; CSV inputs; no proxies, synthetic data, orphans or hard-coded data
unless necessary; say when departing from CAPRI and why; offer beyond-CAPRI ideas for decision; runs under 30 min;
package with all files (zip + README + MODULE_COUPLING_REVIEW + COUPLING_SPRINTS); batch full tests and scenario runs
at the end; no pytest-xdist; market supply NQ off; recursive-dynamic as a parallel layer only.
