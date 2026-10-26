# Market state inventory (for refactor stage 2b, 26 October 2026)

Read-only survey of the mutable state of `MarketModule` (capri_mod/market/) and of what `model.py` sets on it: the map
for stage 2b, which moves (a) what each block builds once per base or calibration into a parameters object and (b) what
one market evaluation passes between blocks into an explicit state object (docs/design/ARCHITECTURE_REFACTOR.md
section 3). Line numbers are those of 26 October 2026 and will move. Findings marked "checked" were confirmed by grep.

## 1. Kinds of state

**Parameters (per base or calibration).** base_production, base_consumption (and their pristine copies),
_base_net_exports_eu, _capri_world_balance, _eu_aligned_use, _dairy_S0 / _dairy_S0_ms / _dairy_S0_reg, _sup_milk0,
_crush_q0_override, _demand_cal (working copy) and _demand_cal_frozen (also the "recalibrate" flag when None), _bilat
(the calibrated trade systems; their objects carry mutable trq_offset, trq_Q, trq_Q0), _bilat_local_el (measured at the
first scenario solve), supply_hessian; file-derived caches (_fao_eu_cache, _biof_cache, _biofm_cache, _dairy_cache,
_dairy_world_cache, _fbulk_cache, _fbyp_cache, _fdp_cache, _usecomp_cache, _procnq_cache, _real_supply_elas, _gl_cache
with in-place refits, _crush_cache, _reg_elas_cache).

**Per-evaluation carriers (one `_bilateral_eval`).** _bilat_ratio_now (r to the dairy block), _crush_prices_now,
_sup_active, _dairy_m5_now, _milk_dq_now, _eu_milk_supply_now, _dairy_last, _sup_milk_now, _world_milk_now,
_dairy_world_last, _biof_state, _yani_market_now, _eu_feed_now_reg / _sup_feed_now, _eu_biof_ratio, _eu_food_ratio.

**Per-solve / across outer iterations.** _bilat_last_r (warm start), trq_offset (lagged quota regime), _dairy_u_all,
_bilat_local_el; solve outputs sup_price_ratio, eu_premium_reg, eu_premium.

**Inputs set by model.py.** world_prices_base (rebound per run), _eu_price_seen, _sup_price_seen, _milk_seen_ms,
_yani_state, _feed_bulk_index, _fmil_index, _fmil_index_sup, biofuel_markets, biofuel_output_scale, biofuel_mandate,
trq_volume_changes, _eu_base_supply (in practice a baseline/scenario flag).

**Diagnostics or unused.** calibration_bound_hits, _bilat_errs, _bilat_err, _bilat_base_resid, _gl_last (tests);
unused: _prem_prev, _prem_w, _prem_d, _eu_base_demand, _eu_feed_now, _milk_dL_now, _wedge_eu_last, last_market_solver,
_eu_aggregate_reported, _rest_share, _bilat_converged, _bilat_unconverged; probably inert: _dairy_u.

## 2. Call order inside one evaluation (`_bilateral_eval`)

1. import prices (with each quota's current offset) and Armington prices per commodity; dom0 x PA; world price index.
2. `_bilat_ratio_now = r` (read by the dairy block); `_crush_prices_now` set.
3. `supply_response`: market supply functions and the young-animal and raw-milk clearing (writes _dairy_m5_now,
   _milk_dq_now, _yani_market_now), crushing, EU dairy (writes _eu_milk_supply_now, _dairy_last), non-EU dairy
   (_sup_milk_now, _world_milk_now, _dairy_world_last), biofuels (_biof_state).
4. `demand_response`: GL demand, feed (reads _feed_bulk_index, _sup_active, _dairy_last), crushing, ProcNQ_, biofuel
   feedstocks (reads _biof_state, writes _eu_biof_ratio), _eu_food_ratio, raw milk (reads the milk carriers).
5. `_crush_prices_now = None`; `_apply_feed_byproduct_supply` (reads _eu_food_ratio, _eu_biof_ratio); residuals.

Between evaluations: `trq_solve` moves each quota's offset (lagged one step, damped). The calibration path calls
supply_response and demand_response directly, without step 2's carriers.

## 3. Risks found (to fix as behaviour changes, each with its own run, not inside a move)

1. `_bilat_ratio_now` is never reset (checked): a baseline on an instance that has run before starts its first
   calibration's dairy block at the last run's dairy-product ratios.
2. `_dom0_cache` is reset only in baseline runs: in a world-price-shock scenario `world_prices_base` is rebound while
   dom0 keeps the unshocked prices, and `_crush_cache` (keyed on world_prices_base) recomputes at the shocked ones.
   Whether intended: to check.
3. `supply_hessian` and `_dairy_S0*` are not in the baseline cache `_eu_base_cache` (checked), unlike `_sup_milk0`: with
   several baselines cached under different keys, a scenario uses the last calibrated one.
4. `_bilat` is cached by reference: scenario changes to its objects (trq_offset, trq_Q) leak back unless reset
   (today covered by explicit resets).
5. `_yani_market_now` is not reset at run start (checked: reset only where the young-animal markets clear in the
   market); read by the stop rule and the outer history.
6. `_hess_cache`, `_milk_terms_cache`, `_yani_hcache` are keyed on `id()` of Hessian frames: a replaced frame's id can
   be reused (possible, not observed).
7. `_fmil_index` / `_fmil_index_sup` are not reset on the early-return paths of `_set_feed_demand`.
8. `_dairy_last`, `_dairy_world_last`, `_biof_state`, `_eu_milk_supply_now` survive across runs; always rewritten before
   being read in a normal solve.
9. External per-iteration inputs are never cleared: a direct `MarketModule.solve` call sees the last run's values.
10. After a non-converged market solve, the reported r is the last step's while S, D and the carriers are from the
    evaluation before it.

## 4. Proposed split

- `MarketParameters`: group "parameters" plus world_prices_base and supply_hessian, built by the calibration layer,
  cached per baseline as one object (fixes risks 3 and 4).
- `MarketEvalState`: the per-evaluation carriers, created fresh for each evaluation and passed explicitly
  supply -> demand -> by-products (fixes 1, 5, 8, 9).
- `MarketSolveState`: warm start, quota offsets, local elasticities, created per solve or per run.
- Inputs from model.py passed as arguments of `solve` instead of attributes (fixes 9).
- Unused attributes removed; id()-keyed caches keyed on the parameters object (fixes 6).

The moves are mechanical and gated by the frozen reference run (identical within 1e-10); the risk fixes above change
behaviour and come afterwards, one at a time.
