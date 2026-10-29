# The market solve against CAPRI's

Status: revised 20 October 2026 against the code. The step counts and timings quoted are from October 2026 runs, as
stated; current run times are in README sections 1 and 11.

Question: is the market solved with the right method? `MarketModule._solve_bilateral` against CAPRI's market solve
(CAPRI documentation, January 2022, sections 5.5-5.6; GUI documentation 2014; `arm/simu_prestep.gms`,
`arm/simu_market.gms`, `arm/widen_bounds.gms`). The market's equations: [ARMINGTON_MARKET.md](ARMINGTON_MARKET.md).

## The problem

CAPRI's market model is a square system of non-linear equations: market balances per region and product, Armington
aggregates and shares, bilateral price links with transport costs and tariffs, TRQs, the dairy fat and protein
balances, processing. CAPRI solves it with CONOPT. capri-mod's market is the same kind of system, and a square system
calls for a Newton-type method, not an optimiser.

## How each solves it

| | CAPRI (`arm/simu_prestep.gms`, capmod) | capri-mod (`_solve_bilateral`) |
|---|---|---|
| single products, cross prices fixed | solved in parallel, repeated with updated cross prices | `_bilateral_inner`: Newton per product on log price ratios (finite-difference Jacobian, kept as a chord while the residual falls fast; step clipped to ±0.5 in log; line search), with supply and use log-linear around the current point; the full model response (supply anticipation, crushing, dairy blocks, feed, biofuels) is re-evaluated after every step (`_bilateral_eval`) |
| groups with strong cross effects | solved together, repeated | Anderson acceleration of the product-by-product steps (`market_acceleration = "anderson"`, memory 5 (`MARKET_AA_MEMORY`), restarted from a damped step when the residual does not fall): the last steps estimate the cross-product response |
| full system | solved at the end | not done as a separate stage: the loop stops when every product's largest relative supply-balance residual is below 1e-7 and the TRQ tariffs have stopped moving, with all cross effects re-evaluated, so it ends at a solution of the full system |
| infeasibility | `widen_bounds.gms`: bounds carrying duals widened stepwise | no bounds; the outer step is clipped to a factor 0.2-5 and damped (halved, floor 0.25, when the residual does not fall) |
| not converged | – | after `run(market_max_iter=...)` steps (default 100 since 21 October 2026, 60 before) the solution is returned with `converged=False`, a RuntimeWarning names the product with the largest residual, and the run metadata record it (`metadata["market_converged"]`) |

The own-price responses of supply and use used inside each product's Newton step are measured once per calibration
(`_bilateral_local_el`, a 1% price change per product); they shape the path, not the solution, which is set by the
full re-evaluated residuals.

So the method is CAPRI's first stage carried to convergence, accelerated. At convergence the equilibrium is the same;
what the missing group and full-system stages would change is the number of steps.

Switches: the setting `market.acceleration` ("anderson" or none) turns the
acceleration off (damped steps alone, same equations and stopping rule).

## Measured (October 2026, Farm-to-Fork 2030, full EU, 2 workers, before the NLP supply form)

- Every market solve converged, largest relative residual 8e-8 to 1e-7.
- The last residual to close was DDGS or casein, products tied to others through blocks rather than through their
  own market (DDGS through the ethanol plants' cereal feedstocks; casein through the dairy fat and protein
  balances): the case CAPRI's group stage exists for.
- Anderson acceleration, when introduced: market time 101 → 71 s per run, steps per scenario solve 23-54 → 15-49;
  every indicator identical within 0.05 points, outer iterations unchanged.
- The market was about 30% of the run time then. With the NLP supply form the regional solves dominate (README
  section 1).

## The supply-market loop

| | CAPRI | capri-mod |
|---|---|---|
| market supply between supply solves | the market's supply functions are recalibrated to the supply models' output each iteration (`arm/simu_calibration_to_supply.gms`) | EU supply anticipated as output × (price / price seen)^ε (`_eu_price_seen`), exact at a converged point |
| supply elasticities in the market | measured on the regional programming models at the baseline (`supply/calibrate_supply.gms`) | CAPRI's own market-model elasticities (p_elasSupp, `supply_elas_eu.csv`, the EU rows only), fixed. CAPRI's measured Hessian is available as `CAPRIModel.market_supply_nq` (off: tested on Farm-to-Fork, 18 October 2026, it gave no gain in speed and moved results only within the outer loop's tolerance; `docs/archive/MARKET_STRUCTURE_PLAN.md` section 1) |
| price passed to supply | weighted average of the last iterations (0.55 / 0.30 / 0.15; `capmod/define_stepWeights.gms`) | damped per product: step 0.5 (`PRICE_SIGNAL_RELAXATION`), halved where the gap changes sign (floor 0.1), raised by 1.25 otherwise; member-state milk prices likewise (floor 0.02) |
| iterations | "usually 5-20" | README section 9 (Validation) (Farm-to-Fork 12, Green Deal 2030 15 outer iterations in runs r48 and r47, 20 October 2026) |

Departure, kept: the market's EU supply elasticities are CAPRI's market-model values, not measured on capri-mod's own
regional models (the option exists, see above). Results at convergence do not depend on them; the path does.

## Conclusions

1. The method class is right (Newton on a square system) and every full-run solve checked converged to 1e-7: the
   market solve is not the cause of the Farm-to-Fork milk-price gap (KNOWN_ISSUES K13), which is the dairy block's
   response, not its solution.
2. CAPRI's missing stages (a joint Newton step over linked blocks, or the full system at the end) would bring speed,
   not different results.
3. A market solve that does not converge is warned about and recorded in the run metadata.
