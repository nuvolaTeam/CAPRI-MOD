# NLP check: the conic model against CAPRI's original form (IPOPT)

*Does the convex conic program solved for each region reach the same optimum as CAPRI's own, non-convex supply
model? `tools/nlp_check` answers it numerically, region by region.*

## How to run

    pip install -r requirements.txt         # includes casadi, which bundles IPOPT
    python tools/nlp_check/capture.py OUTDIR [run_f2f_2030.py options]   # NLP_REGIONS=IE05,NL22,... (default 5)
    python tools/nlp_check/nlp.py OUTDIR [REGION ...]

`capture.py` runs a full scenario and saves, for each chosen region, the last regional problem solved with CAPRI's
technologies (the converged scenario's final solve): the conic model's inputs, its solution and the region's ammonia
data. `nlp.py` rebuilds the same problem in CasADi and solves it with IPOPT from five starts (the conic solution, the
base point, three perturbed base points).

## What is written in CAPRI's form

| Block | CAPRI (supply_model.gms) | conic model |
|---|---|---|
| Feeding | feed per head x herd (v_feedingLevl, bilinear) | total feed and the perspective of the feed cost - exact by algebra |
| Ammonia options | shares per sub-activity; N saved through the loss cascade HOUSN_ -> STORN_ -> APPLN_ (bilinear) | N saved linearised at the previous solve's shares (tangent since K1) |
| Fertiliser options | one regional share per technology, mineral N = need / (1 + sum share x NMIN) | one share per crop (registered departure), mineral N exact per crop (rotated cone) |
| Inhibitor on manure | one regional share, relief bilinear in share x manure N | perspective in T = share x manure N - exact by algebra |

Everything else (PMP terms, land market, constraints, prices) is the captured problem itself. Four cases per region:
(1) the conic model's own relations - a check of the builder; (2) CAPRI's exact cascade; (3) plus one regional share
per fertiliser technology; (4) plus feeding per head (CAPRI's literal form).

## Results (Farm-to-Fork 2030, converged, October 2026)

| | before the fixes | after K1, K2 |
|---|---|---|
| CAPRI's N balance at the conic solution | violated by 8-365 t N | met (≤ 0.03 t N) |
| objective gap conic vs IPOPT, CAPRI's form | up to 1.6e-3 | 1e-8 - 6e-7 (IE05 1e-5) |
| N price conic / IPOPT | DE94 56.4 / 57.3 | equal to 0.01 EUR/kg |

- Fertiliser shares per crop vs one regional share: same optimum in all five regions (1e-10).
- Every start that converged reached the same optimum (spread ≤ 1e-8): no competing local optima found.
- CAPRI's per-head feeding is hard for IPOPT: in FRH0 and IE05 most starts end "infeasible", even from the conic
  solution; the total-feed form (same set, convex) solves from every start.

Under a 50 EUR/t emission tax (BE21, DE94, FRH0, NL22) the conic model equals CAPRI's exact form within 1e-6 (K8).

IPOPT is also used inside the model since the prototype's K4 fix: only to finish the few regional solves Clarabel
leaves AlmostSolved or stalled (`feed_conic._ipopt_polish`), on the same convex problem.

## Shadow trial: every regional solve of a full run (October 2026)

`tools/nlp_check/shadow.py`: a full Farm-to-Fork 2030 run (converged, 14 iterations, results unchanged) in which every
call of the conic model was also written in CAPRI's form - exact ammonia loss cascade, one regional share per
fertiliser technology, inhibitor share x manure N, feeding in total form - and solved with IPOPT. 4,243 solves in 235
regions (the regions with the feed block).

| | |
|---|---|
| IPOPT converged | 4,220 of 4,243 (99.5%); every region's final solve |
| failures | 23: 15 in NL12 at intermediate land steps where Clarabel also finds the problem infeasible; 8 where Clarabel solved (4 "infeasible detected": AT12, BG31, BG32, DE22; 6 iteration limit: DE22, DE72, DE73, DEB1, DEB3, BG31) |
| final solves, objective NLP optimum vs conic point (CAPRI's form) | median -3.5e-8, worst -1.5e-4 (PT30), -1.1e-4 (MT00), all others within 1.3e-5 |
| final solves, activities | median 6e-5 relative, 95% within 0.2%; largest PL62 maize 13% (objective gap 1.3e-5: flat optimum) |
| final solves, N price | median identical; largest 3% (HU31, 0.94 vs 0.90 EUR/kg N) |
| first solves (cascade linearised at base shares) | up to 2% of the objective (NL12), closed by the outer iterations |
| time, CPU | Clarabel 254 s; IPOPT 1,843 s (CasADi build 266 s, solve 1,577 s), ~7x; almost all IPOPT starts were cold (base point) |

At the converged solution the conic model is CAPRI's exact optimum to within 1.5e-4 of the objective: the linearised
cascade's error is closed by the outer iterations, as designed. IPOPT on CAPRI's NLP would give the same results with
a literal formulation; it would cost ~7x the supply solve time (a Farm-to-Fork run of ~23 min on 2 cores instead of
~8, before warm starts and a parametric build) and a fallback for ~0.5% of solves.

Decision (15 October 2026): Clarabel stays the default. IPOPT on CAPRI's NLP as a switchable supply solver is kept as
future work, not scheduled, alongside the base-year update (CHANGELOG, "Still open").
