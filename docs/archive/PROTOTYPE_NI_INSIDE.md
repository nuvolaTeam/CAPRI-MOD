# capri-mod-proto: the nitrogen target as a plain constraint (October 2026)

*Prototype branch of capri-mod 9t (`capri-mod-9t.zip`). Question: would CAPRI's original, non-convex supply model gain
from IPOPT (handoff: docs/archive/HANDOFF_IPOPT_PROTOTYPE.md)? Answer found: not needed - the one block still decided outside
the solver can be written convexly, and with it the N-price search disappears.*

## What was still outside the solver

With the default settings (feeding, ammonia and fertiliser technologies inside the regional conic model), the
regional problem depended on the nitrogen-balance price through one thing only: CAPRI's nitrification inhibitor on
applied manure (`_apply_manure_inhibitor`, envind/ghgMiti.gms, NITR_INH on N2OMAN). Its share was set from the N price
given to the solve, so every region with the N-surplus target needed a fixed-point search on that price
(`SupplyModule._next_nbal`, bracket + secant, up to 16 solves per region and iteration). In IE05 the search
alternated between two branches (Sprint 9t).

## Formulation (`feed_conic.solve_regional_conic`, argument `mni`)

CAPRI: one regional share s of manure N treated, 0 <= s <= smax (manure N not dropped on pasture); manure N counts
x (1 + s NMAN) in the crop nutrient balance, i.e. the N balance falls by sub x NMAN x s per t of manure N; cost per t
of manure N S0 s + 0.5 slope s^2 (CAPRI's calibration of the options, relSubs 1.2 / 0.2); under the emission tax
the tax saved, vtax x s.

With W = sum_a mN_a x_a (t manure N, linear in the herds) and T = s W (t treated):

- T <= smax W;
- N row: - sub x NMAN x T;
- cost S0 T + 0.5 slope T^2 / W - vtax T. T^2 / W is the perspective of s^2 - convex, written as the rotated cone
  U W >= T^2 (same helper as the ammonia options).

This is CAPRI's own relation, not an approximation: at the optimum s = T / W satisfies the same first-order condition
as the external rule at the region's own N dual (S0 + slope s = 1000 x dual x sub x NMAN + vtax), and the herds see the
same marginal cost (envelope: c(s) - s c'(s)). The external decision is kept for the switch
`RegionalSupplyModel.ni_inside_model = False` (and for solves outside the conic model).

With nothing in the regional problem depending on the N price, `SupplyModule._solve_region` does one solve per land
step in N-target regions; the target is a plain constraint, as in CAPRI's NLP, and its dual is the N price reported.

## Solver stall

Under Farm-to-Fork IE05 holds the inhibitor at its maximum share at an N price of ~370 EUR/kg N, and Clarabel stopped
with InsufficientProgress (relative gap 1e-4, residuals 1e-11) in about one iteration in three. The region then fell back
to the problem without technologies, its dairy supply jumped, and Ireland's milk price never settled (run stopped
at 25 iterations). A stalled solve is now re-solved with more static regularisation of the KKT system (1e-7, then
1e-6; Clarabel's default 1e-8): AlmostSolved, same point. Regions solved at the first attempt are not touched.

## Results (full EU, 2 workers)

| | 9t | prototype |
|---|---|---|
| Farm-to-Fork: converged | 23 iterations, 756 s | 13 iterations, 353 s |
| Farm-to-Fork: gap to JRC121368 (20 indicators) | 4.26 | 4.29 |
| largest indicator difference | - | 0.4 points (pork price) |
| inhibitor on manure, EU adoption | 44.7% | 44.6% |
| Green Deal: converged | 18 iterations, 799 s | 20 iterations, 584 s |
| Green Deal: mean deviation from the JRC121368 column (indicative only) | 10.13 | 9.99 |
| largest indicator difference | - | 0.8 points (pork price) |

Seven-region check at identical settings (IE04-06, FRH0, NL22, DE94, BE21): baseline identical; inhibitor shares the
same to three decimals; N prices within 0-3% (9t's search stops within its tolerance); regional solve time -40 to
-60%.

## Check against CAPRI's original form (IPOPT)

`tools/nlp_check` (docs/archive/NLP_CHECK.md) writes captured regional problems in CAPRI's own, non-convex form and solves them
with IPOPT. It found two bugs present in 9t as well (docs/KNOWN_ISSUES.md K1, K2: the ammonia loss cascade linearised
without its value, and the options' quadratic cost w times too small). With both fixed the conic model reaches
CAPRI's exact optimum in the five regions checked. Full runs after the fixes: Farm-to-Fork converged in 13
iterations, 349 s, gap 4.28; Green Deal 20 iterations, 544 s, within 0.5 points of 9t; 92 tests pass without warnings.

## IPOPT in the model

Not as the solver: the supply model with feeding, technologies and the inhibitor inside is one convex conic program,
which Clarabel solves to optimality. IPOPT has two jobs: the NLP check (docs/archive/NLP_CHECK.md) and finishing the few
regional solves Clarabel leaves AlmostSolved or stalled (K4, `feed_conic._ipopt_polish`; Farm-to-Fork: 63 calls in a
run, EU indicators unchanged, ~2 minutes). It would become the solver only for CAPRI blocks that are genuinely
non-convex.
