# The supply's state objects (refactor stage 3, second half)

Where each regional model (RegionalSupplyModel) and the supply module (SupplyModule) keep what they hold between calls,
after the moves S0b-S10b of docs/design/STAGE3B_PLAN.md (2 November 2026). The declarations are in
capri_mod/supply/state.py; this list is taken from them. A former attribute name raises RuntimeError on the model
(state.MOVED_REGIONAL, MOVED_MODULE); capri_mod/tests/test_supply_state.py scans the code for the private ones used
as strings.

Objects: `par` parameters built once per base; `sv` state carried from one solve (or pass) to the next; `ev` the
working values of one solve; `seen` what the caller sets before a solve; `res` the last solve's results and
diagnostics. They are slot classes: a field never set is absent, so `getattr(obj.sv, name, default)` behaves as the
attribute's getattr did.

## Regional model: par (RegionalParameters)

- `nlp_cal`: the NLP's calibration (CAPRI's PMP terms in the NLP form) for the current settings
- `nlp_base_alloc`: the fertiliser allocation at the calibration point (nlp_cal's base_alloc)
- `nlp_cal_store`: the calibrations by settings key, so a switch of settings and back keeps both
- `npk_dual_bound`: the fertiliser distribution's dual bound where it was widened for the region
*livestock (S4): the split columns' linear terms, calibrated from the duals of the first solves, and the*
*calibrations still pending*
- `cattle_cz`: the cattle splits' terms by split
- `cattle_pending`: the cattle splits whose terms wait for the duals
- `dairy_cz`: the low-yield dairy split's term
- `dairy_pending`: the dairy split's column and requirement waiting for the duals
- `genet_cz`: the genetics options' terms, for the current genetics settings
- `genet_cz_store`: genet_cz by genetics settings key
- `genet_key`: the genetics settings key genet_cz belongs to
- `genet_pending`: the genetics options whose terms wait for the duals
- `genet_rows_memo`: the genetics options' rows (a memo)
- `grass_cz`: the grass split's term
- `grass_pending_col`: the grass split's column waiting for the duals
*fertilisation (S5): memos of the base and CAPRI's priors recalibrated at the first solve*
- `ef_lea_cache`: the leaching emission factor (a memo)
- `ef_min_n2o_cache`: mineral fertiliser's N2O per kg N, CO2 equivalent (a memo)
- `min_n2o_parts_cache`: its parts (a memo)
- `npk_kappa`: the fertiliser distribution's kappa by nutrient (a memo)
- `npk_prior_override`: CAPRI's priors where the calibration recalibrated them
- `npk_prior_recalibrated`: the nutrients whose priors were recalibrated
*abatement (S7): the histosol fallowing's terms, calibrated from the duals*
- `hist_cal`: the terms by histosol class
- `hist_pending`: the classes whose terms wait for the duals
*core and policy (S8)*
- `base_cal_shift`: the linear terms' shift from SupplyModule.calibrate_to_base
- `base_levels_cache`: the base levels (a memo keyed on the base data's identity)
- `input_cost_memo`: the input costs (a memo)
- `oyg_memo`: the organic yield gaps (a memo)

## Regional model: sv (RegionalSolveState)

- `nlp_prev`: the last solution (graph key, x, shape, multipliers): the next solve's warm start
- `nlp_prev_f`: its objective: the warm check's reference
- `nlp_y`: its activity levels: the jump check's reference
- `nlp_cols`: the columns of nlp_y
- `nlp_relax_keep`: the mineral-cap exemption kept from the first solve of a problem (its fingerprint)
- `kkt_base`: the base solve's KKT records by graph key (the Hessian's KKT mode)
- `wc_solved`: the winter cover share chosen by the last solve (None where not endogenous)
*fertilisation (S5)*
- `n_relax_sticky`: the N-target relaxation kept from one solve to the next (not restored by the Hessian)
*abatement (S7)*
- `amm_last`: the ammonia options' linearisation point, from the previous solve

## Regional model: ev (RegionalEvalState)

- `last_duals`: the NLP's duals of the solve's rows (feed, land, ...), read by the calibrations after it
- `last_req_duals`: the requirement rows' duals, read by the split calibrations after the NLP
- `nlp_accept_last`: set around the last attempt: IPOPT's last point is kept (as CAPRI)
- `nlp_failed`: why the NLP form failed in this solve (None where it did not)
- `nlp_fb_last`: how the last fallback ended (False, or "n_target")
- `nlp_n_target_cause`: the tiered N target was the cause of a failure
- `nlp_try_n_relax`: set around a call: the N-target relaxation may be tried
*livestock (S4): the split columns of this solve's problem*
- `cattle_cols`: the cattle splits' columns
- `dairy_col`: the low-yield dairy split's column
- `dairy_req_extra`: the splits' extra requirement entries by animal
- `genet_cols`: the genetics options' columns
- `grass_col`: the grass split's column
*fertilisation (S5)*
- `n_intensity`: the mineral N intensity factors of the solve, by crop and the manure credit
- `nlp_mine_small`: the fertiliser groups too small for the mineral-N row
*land (S6): the land market's layout in the augmented problem and the manure pools*
- `alloc_cols`: the mineral-N allocation columns (0 or 1)
- `alloc_m0`: the allocation's start
- `alloc_row`: the allocation's row
- `aug_labels`: one label per row of the augmented problem
- `cover_dbf_nb`: the catch crops' N-balance term on the allocation row
- `land_rent_rows`: the land rent rows by label
- `land_types_used`: the land types of the problem
- `need_row`: the feed need row
- `nrow_land`: the land rows of the N row (columns, base land, target)
- `pool_avail`: the manure available to the pool
- `pool_cols`: the manure pool's export and import columns (N)
- `pool_cols_pk`: idem for P and K
*abatement (S7): the ammonia and inhibitor accounts of the solve, the catch-crop requirement, histosols, the*
*emission tax's undo record*
- `amm_cost`: the ammonia options' cost by animal
- `animal_n_relief`: the manure N the ammonia options keep, by animal (the N row's relief)
- `cover`: the catch-crop requirement and increment (1000 ha)
- `ghg_applied`: the emission tax added to the net revenues, by activity (its undo record)
- `ghg_nr_obj`: the net revenues object the tax was added to (an identity check, never a copy)
- `hist_cols`: the histosol fallowing's columns
- `manure_ni_nh3`: NH3 of the manure inhibitors, by activity
- `manure_ni_relief`: the manure N the inhibitors keep, by activity
- `nlp_nip`: the manure inhibitors' parameters
*core and policy (S8): the solve's arguments, the problem's rows, the scenario's per-solve terms*
- `fall_floor`: the landscape (fallow) floor
- `mineral_cap`: the mineral fertiliser caps of this solve
- `mineral_row`: the mineral-N row's terms
- `nbal_price`: the N-balance price of this solve
- `price_shock_now`: the price shock of this solve (the Hessian's)
- `row_labels`: one label per row of the problem
- `surplus_row`: the N-surplus row of this solve
- `yields_solve0`: the yields at the start of the solve (restored at its end)
- `greendeal_inputs`: the Green Deal's input reductions of this solve
- `organic_conv`: the organic conversion shares by crop
- `yield_price_factor`: the yields' price factors

## Regional model: seen (RegionalSeen)

- `ration_state`: the feed block's ration state of the region
- `manure_pool_price`: the manure pool's N price of the member state
- `manure_pool_price_pk`: its P and K prices
- `yani_price_ratio`: the young-animal price ratios {good: price / base price}
- `feed_rations`: the rations by animal
- `feed_prices`: the feed prices
- `feed_bulk_ratio`: the bulk feeds' price ratios
- `ghg_tax`: the emission tax (EUR per t CO2-eq; 0 outside the EU)
- `ghg_coef`: the emission coefficients of the region
- `env_for_surplus`: the supply module's shared EnvironmentalModule (removed before pickling, re-attached)
- `manure_ctx`: CAPRI's crop nutrient balance terms (Sprint 9k; None outside the EU)
- `fert_techs_all`: CAPRI's fertiliser options (NLP form)
- `nlp_cal_check`: set by CAPRIModel at a baseline: check the NLP calibration at the next solve

## Regional model: res (RegionalResults)

- `cover_solved`: the winter cover chosen in the NLP form (the supply result's cover_crops)
- `fd_model`: the fertiliser distribution's flows and areas (the supply result's fert_dist_model)
- `fert_inside_factor`: the fertiliser accounts' factors inside the NLP
- `kkt_ipopt`: IPOPT solves in the Hessian's KKT mode (a counter)
- `last_feed_dm`: the feed used, dry matter
- `last_feed_t`: the feed used, tonnes
- `last_npk`: the fertiliser outputs by nutrient
- `n_solves`: solves of the region (a counter)
- `nlp_fallback_log`: the NLP form's fallbacks of the run (metadata nlp_fallback)
- `nlp_jump`: the jump check's record (outer history's jump_check)
- `nlp_nonoptimal`: IPOPT's status where its last point was kept (non-optimal, as CAPRI)
- `nlp_ok`: the last solve was CAPRI's form, accepted
- `nlp_path`: the starts tried and the last one's IPOPT iterations
- `nlp_rc`: the activities' reduced costs
- `nlp_relaxed`: the mineral-cap exemption applied
- `nlp_status`: IPOPT's status
- `yani_dnet`: the solution's response to the young-animal prices (K65)
*livestock (S4): the split columns' levels in the last solution*
- `last_cattle_z`
- `last_dairy_z`
- `last_genet_z`
*fertilisation (S5)*
- `fert_tech_shares`: the fertiliser technologies' shares
- `n_target_relaxed`: the solve ended at JRC121368's relaxed N target
*land (S6): the manure pools, read by the manure market (coupling/manure.py)*
- `manure_supply0`: the region's manure N supply at the start
- `manure_supply0_pk`: idem for P and K
- `pool_manure_vec`: the manure N by column
- `pool_manure_vec_pk`: idem for P and K
*abatement (S7)*
- `animal_n_kept`: the manure N kept by the ammonia options, by animal
- `animal_nh3_saved`: the NH3 they save, by animal
- `manure_tech_shares`: the manure technologies' shares
*core (S8)*
- `land_solution`: the land types' levels
- `last_aug`: the augmented problem the land-market solve used (Q, c, A, b, y)
- `last_grass_z`: the grass split's level
- `last_hist_fallow`: the histosol fallowing by class
- `last_manure_trade`: the manure trade (N)
- `last_manure_trade_pk`: idem for P and K
- `last_mineral_n`: the mineral N bought
- `last_plain`: the plain problem (no land market), as last_aug

## Supply module: par (ModuleParameters)

*S10a; the per-region caches returned by the workers (_PAR_CACHES) are merged into the parent's*
- `balance_cache`: the N-balance coefficients by region
- `env_for_surplus`: the EnvironmentalModule shared with the regional models (seen.env_for_surplus)
- `jrc_capped_cache`: JRC121368's capped regions (popped by CAPRIModel every outer iteration)
- `mcap_cache`: the mineral caps by region
- `mctx_cache`: CAPRI's crop nutrient balance terms by region
- `genetics_key`: the settings key of the genomics calibration

## Supply module: sv (ModuleSolveState)

*S10a; the N-balance price state is per region and returned by the workers (_PAR_STATE)*
- `base_cal_prev`: the base calibration's previous round
- `base_cal_round`: its rounds across the baseline's iterations
- `base_cal_stalled`: the regions where it stalled
- `nbal_bracket`: the N-balance price bracket by region
- `nbal_prev`: the previous N-balance prices by region
- `nbal_state`: the N-balance price by region

## Supply module: seen (ModuleSeen)

- `feed_prices`: the feed prices by region (also set by the supply module's base rations)
- `feed_rations`: the rations by region (idem)
- `feed_bulk_ratio`: the bulk feeds' price ratios {(member state, bulk): ratio}
- `ghg_tax`: the emission tax (EUR per t CO2-eq)
- `ghg_coef`: the emission coefficients by region
- `manure_pool_price`: the manure pools' N prices by member state
- `manure_pool_price_pk`: their P and K prices
- `manure_trade_on`: manure trade between regions (read with the default True)
- `yani_price_ratio`: the young-animal price ratios, EU
- `yani_price_ratio_ms`: idem by member state
- `yani_price_ratio_m`: idem by market region (the coupling's own storage)
- `milk_price_dev_ms`: the member states' milk price deviations
- `price_dev_ms`: the member states' price deviations
- `ration_state`: the feed block's ration state by region
- `hess_probe`: the Hessian's skip probe mode ("record", "compare", "verify" or None)
- `hess_shock`: the shock being measured
- `hess_base_res`: the base re-solve's results by region

## Supply module: res (ModuleResults)

*S10a*
- `hess_fp`: the Hessian's skip probe: the regions' first-solve digests (set and popped by it)
- `hess_verify`: idem, verify mode
- `max_nbal_region`: the region of the largest N-balance price update
- `max_nbal_update`: the largest N-balance price update of the pass
- `worker_failures`: the regions a worker failed on
*S2: the NLP block's carried state and calibration*
*S3: the NLP block's working state and results*
*S4: livestock and feed*
*S5: fertilisation*
*S6: land*
*S7: abatement*
*S8: core and policy (net_revenues, premiums, f, Q and balance_shortfall stay on the model, plan Q8)*
*S9: the regional models' inputs*
*S10a: the supply module's parameters, carried state and results*
*S10b: what CAPRIModel and the coupling set on the supply module*

## Removed (S1 and after)

Written and never read, or read and never written: `_last_land`, `_last_aug_A`, `_last_aug_b`, `_mineral_row_m`, `_fert_inside_weight`, `_nlp_abatement`, `_npk_cov`, `_nlp_group_caps`, `_manure_ni_share`, `_last_feed`, `_nlp_times`, `_last_aug_cols`, `_base_cal_drift` (and `_dairy_yield_base`, whose writer went in 3a264a2).

## Kept on the models

- RegionalSupplyModel: `net_revenues`, `premiums`, `f`, `Q` (plan Q8), `balance_shortfall` (also the supply result's
  field), `data`, `acts` and the other attributes set by `__init__`; the class-level settings and run state (plan 1.4).
- SupplyModule: `_models`, `data`, `_inner_fert` (the environmental module has its own attribute of that name), the
  class-level settings.

## The Hessian's restore and the workers

RegionalSupplyModel.NLP_STATE and SOLVE_STATE list the fields the market supply Hessian saves and restores, by
attribute name or path (`sv.nlp_prev`); SupplyModule._PAR_STATE and _PAR_CACHES the per-region fields the workers
return, as paths. The sets are those before the moves (plan Q2); each field is copied on its own.

## Behaviour changes left for their own runs (plan Q11)

- `sv.n_relax_sticky` and `ev.ghg_applied` are not restored by the Hessian (as before the moves);
- `use_fert_allocation`: an instance copy shadows the class-level setting (finding 1.3-9);
- restoring `sv` (and `ev`) whole instead of field by field (plan Q2, 3.4-3).
