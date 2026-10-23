# Handoff: IPOPT prototype for the nitrogen-target regions (October 2026)

State of the model at handoff: Sprint 9t (capri-mod.zip of 14 October 2026, 92 tests passing). Farm-to-Fork gap
4.26 to JRC121368, converged in 23 iterations (756 s on 2 cores); Green Deal converged in 18 (799 s).

## Why

The regional supply models are one convex conic program each (Clarabel). Feeding inside supply is an EXACT
reformulation of CAPRI's model (total feed F = feed per head x herd turns CAPRI's bilinear feed-PMP term into a
perspective function, docs/archive/FEED_IN_SUPPLY.md), so IPOPT would bring nothing there.

What is still iterated outside the solver, because it is non-convex, is the nitrogen-balance block:
- fertiliser technologies: CAPRI's mineral N x (1 + E) is linearised at the previous outer iteration's point;
- inhibitors on manure: decided outside at the current N price (`_apply_manure_inhibitor`);
- hence a per-region fixed-point search on the N-balance price (`SupplyModule._next_nbal`, bracket + secant,
  `NBAL_INNER_MAX` = 16 solves per region and iteration).

In Sprint 9t that search failed in IE05: the reported dual jumped between ~0 (balance slack from ~10 EUR/kg N) and
~335 EUR/kg N (only herd cuts left), and the run alternated between the two branches until the inner limit was raised
from 8 to 16. CAPRI has no such search: the surplus target is a constraint of its NLP (CONOPT).

## Plan (agreed with the user)

1. Keep Clarabel as the default path.
2. Prototype an NLP path, only for regions with the nitrogen surplus target: technologies and manure inhibitors
   inside, CAPRI's exact (1 + E) relation, the surplus target as a plain constraint, no N-price search.
   Tooling: CasADi (pip install casadi; bundles IPOPT with automatic derivatives; Python callbacks to cyipopt
   would be too slow for 248 regions x ~20 iterations). Warm start from the previous solution, as CAPRI does.
3. Check on a handful of regions (IE05, NL22, FRH0, DE94, BE21):
   - same solution as today's fixed point where that point is unique;
   - behaviour where today's search had two branches (IE05);
   - speed per solve, and in a full Farm-to-Fork run.
4. If it holds: wire it behind a switch, full F2F and Green Deal runs, tests, docs, package as usual.
   If not: document and keep the current path.

## Where things are

- `capri_mod/supply/supply_module.py`: `RegionalSupplyModel.solve` / `_solve_once` (conic path via
  `_feed_conic_solve`, `feed_conic.py`), `_apply_balance_price`, `_apply_manure_inhibitor`, `_techs_inside`;
  `SupplyModule._solve_region` (land and N-price inner loops), `_next_nbal`.
- Debug harness used for IE05 (rebuild if needed): run tools/run_f2f_2030.py through runpy with
  `ProjectionModule.run` patched to `regions=[IE04, IE05, IE06, FRH0, NL22, DE94]` and `SupplyModule._next_nbal`
  wrapped to log (used, dual, next, bracket).
- Runs: PYTHONHASHSEED=0 (the runners re-exec with it); CAPRI_WORKERS sets the worker processes.
