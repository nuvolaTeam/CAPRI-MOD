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
