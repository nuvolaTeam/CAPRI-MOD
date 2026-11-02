# Refactor stage 4, second half: the environment's and the coupling's state (inventory and plan)

Inventory drafted 2 November 2026 (evening) by a read-only pass over the code at manifest-sql dae44fa, in the style
of docs/design/SUPPLY_STATE_INVENTORY.md; the moves follow STAGE3B_PLAN.md's pattern (slot objects par, sv, ev, seen,
res; the old names raise through MOVED). Nothing was run for it.

## Decisions taken by precedent (2 November 2026; to be confirmed by the project lead if he objects)

The open questions of section 7.2 are answered as stage 3 answered the same questions, unless marked for the project
lead:
- Q1: the environment gets four objects (no sv: it carries nothing between iterations), the coupling five; as
  SupplyModule has no ev.
- Q2: `_last_spol` and `_last_supply_results` go to `seen` (recorded from the modules' last solve), as the supply's
  seen holds what it observed.
- Q3: the EnvironmentalModule class-level caches stay on the class in this stage (a pure move); keying them on the
  data adapter is a behaviour change, listed for the project lead.
- Q4: the six write-only coupling fields are removed, as stage 3 S1 removed the supply's (the project lead's decision
  of 2 November 2026 on write-only attributes).
- Q5: `use_manure_market` and `verbose` stay on the model, as the supply's class-level settings stayed.
- Q6: the nitrate factor 10.0 of ghg.py is CAPRI's: envind/line_nitr.gms l. 100-102, QEmitt = NOC x
  (1 - 0.1 x ShrOfDM x 100), so the reduction is 10 x the nitrate share of dry matter [own check]. It becomes a
  parameter with that citation.
- Q7: the coupling's writes on MarketModule go into the market's state objects (its owner's, stage 2b) and `_Q_inv`
  into the regional model's par, in this stage; each in its own step.

Behaviour changes found by the inventory, kept out of the moves and listed for the project lead's decision (each its
own commit and run): the young-animal trace reading `diagnostics.trace_outer`; an explicit loader for `_amm_tm`
(risk 7.1-5, the leaching step may run before the cascade data are loaded); the class caches keyed on the data
adapter; `sv` reset whole per run; the model.py:1551 fallback weight 0.5 for VSET (unsourced); the dead soil-N2O
branch of compute_ghg (overwritten by compute_indicators).

---

Inventory only, for the project lead's review; nothing in the repository was changed. Written 2 November 2026 on
branch manifest-sql at HEAD dae44fa (the checkout). Line numbers are those of that HEAD.

Sources read: capri_mod/supply/state.py, capri_mod/market/state.py, docs/design/STAGE3B_PLAN.md,
docs/design/SUPPLY_STATE_INVENTORY.md, docs/design/ARCHITECTURE_REFACTOR.md §3, docs/design/N6_CODE_TABLES.md,
docs/design/HARDCODED_TABLES.md, capri_mod/environmental/*.py, capri_mod/model.py, capri_mod/coupling/*.py,
capri_mod/units.py, capri_mod/settings/__init__.py (the `setting` descriptor), capri_data/shared/model_parameters.csv,
capri_mod/settings/defaults.toml, capri_data/schema/03_code_data.sql and 04_code_data_status.sql, and the readers in
capri_mod/supply, capri_mod/projection, capri_mod/tests and tools.

Method. An AST scan of the class bodies of EnvironmentalModule and its five mixins (GHGBlock, NitrogenBlock,
AmmoniaBlock, PhosphorusBlock, BiodiversityBlock) and of CAPRIModel and its seven mixins (HessianBlock, FeedBlock,
YoungAnimalBlock, PriceStepBlock, ManureBlock, BridgeBlock, ReportingBlock): every `self.X =`, `del self.X`,
in-place mutation (`self.X[k] =`, `self.X.append/update/setdefault/pop`), `getattr/setattr/hasattr(self, "X")`,
`self.__dict__[...]/.get/.setdefault/.pop("X")`, and every read. Then a grep of each name in capri_mod, tools and the
tests. Each attribute was classified by reading the code at its write and read sites. No model run, test or builder
was run.

Marking. **[verified]** = read in the code at the lines cited; **[inferred]** = my reading of lifetimes or effects,
not checked by running. "string" = reached through getattr/setattr/hasattr or `__dict__` with a string, or saved and
restored by name. "write-only" = no reader in capri_mod, tools or the tests (unless a test is named).

File abbreviations: em = capri_mod/environmental/environmental_module.py, g = environmental/ghg.py,
n = environmental/nitrogen.py, a = environmental/ammonia.py, p = environmental/phosphorus.py, m = capri_mod/model.py,
h = coupling/hessian.py, f = coupling/feed.py, ya = coupling/young_animals.py, ps = coupling/price_step.py,
mn = coupling/manure.py, b = coupling/bridge.py, rp = coupling/reporting.py, tc = capri_mod/tests/test_capri.py,
rs = tools/run/run_f2f_2030.py. W = written, R = read.

## 0. Summary

- **EnvironmentalModule: 28 instance attributes** set outside `__init__` (only `data` is set in `__init__`, em:155).
  Proposed: par 16, ev 9, seen 1, res 1, removed 1 (write-only). There is no state carried between iterations (no
  `sv`): every attribute is a memo of the base data, a value of one region's evaluation, the manure-trade switch, or
  the run's fertiliser-distribution table. 26 of the 28 are reached by string (`__dict__` or getattr). [verified]
- **CAPRIModel: 80 instance attributes** set outside `__init__`. Proposed: par 14, sv 29, seen 2, ev 6, res 21,
  removed 6 (write-only), kept on the model 2 (`use_manure_market`, a run-state setting descriptor; `verbose`). One
  more name, `trace_outer`, is read and never written (ya:284). [verified]
- **Class level**: 6 caches on EnvironmentalModule shared by all its instances (4 of them created on the class at run
  time, not declared in its body), 2 singleton caches elsewhere in the package; CAPRIModel has 19 setting descriptors,
  2 class attributes set as run state by the run script, 6 code tables. The mixins declare no class attributes.
- **Numbers**: 26 rows (13 environment, 13 coupling), unit conversions excluded. 4 rows are values that already have
  a declared home and are still written as literals (units.py's 44/28 and 4.1868, the parameter MJ_PER_KG_CH4,
  fert/npk.py's ENDO_MAN_AV_SLOPE).
- **Code tables**: 17 rows (7 environment, 10 coupling), several of them copies of one table.
- Proposed moves: 11 steps (E0-E10) in 6 batches, each gated by the mini-EU Farm-to-Fork run at 1e-12 (section 6).
- Main risks (section 7): the Hessian's cache key reads three coupling fields by getattr with defaults; the
  environmental module shared with the forked workers and reached by string from the supply code; the manure pools'
  nine fields swapped by name; the run script and two tools read fields by getattr with defaults; the class-level
  caches and an order dependency of `_amm_tm`.

## 1. EnvironmentalModule (and its mixins)

There are two instances in a run: CAPRIModel.env_module (m:197), for the accounts, and SupplyModule.par.env_for_surplus
(supply_module.py:2440, 2550, 2575, 2607, 2989, 3165), shared with every regional model as seen.env_for_surplus and
used inside the regional solves (unit_nitrogen_balance, _substitution, _residue_availability, `_inner_fert`). Tests
build more (tc:247, 1817, 2427, 2450, 2737, 2910; test_p_balance.py:148). [verified]

### 1.1 par (16): memos of the base data, built on first use

| name | W | R | holds | flags |
|---|---|---|---|---|
| `_mloss_cache` | g:14 (setdefault), g:20, 23 | g:15, 24 | manure N lost in housing and storage by region and animal | string |
| `_nexc_cache` | g:27 (setdefault), g:30 | g:29, 31 | manure N per head by (region, animal) | string |
| `_mn2o_cache` | g:205 | g:200 (`__dict__.get`) | manure N2O factors by (region, animal) | string |
| `_mn2o_tech_cache` | g:211 (setdefault), g:227 | g:212, 228 | technologies' N2O effects and base shares by region | string |
| `_mn2o_tech_tab` | g:215 | g:214 (`in __dict__`), g:218 | manure_n2o_tech.csv | string |
| `_amm_tm` | g:217 | g:223; getattr default {} at g:235, 250, 269, n:697, p:40 | CAPRI's ammonia sub-activities (ammonia_tech_model.csv) | string; tc:3503 writes it; loaded only by `_manure_n2o_tech` (risk 7.1-5) |
| `_nh3_fac_cache` | a:16 | a:12 (`__dict__.get`) | NH3 factors by region | string |
| `_sub_cache` | n:27 (setdefault), n:49 | n:28-29; popped n:15 on a manure-trade switch | manure substitution terms by region | string; depends on seen.manure_trade_on |
| `_row_cache` | n:113 (setdefault), n:117 | n:115, 119 | one region's row of a data table, by (table, region) | string |
| `_grass_delta_cache` | n:221 (setdefault), n:227, 248 | n:223-224 | grassland GRAI to GRAE balance change by (region, intensity) | string |
| `_need_base_cache` | n:267 (setdefault), n:281 | n:268-269 | base crop need weights by region | string |
| `_res_av_cache` | n:286 (setdefault), n:315 | n:287-288 | residue availability by region | string |
| `_unit_nb_memo` | n:329 (setdefault), n:333 | n:330 | unit N balances by (region, activity, yields, intensity, trade) | string; asked "hundreds of thousands of times per run" (n:323) |
| `_inner_fert` | n:596, p:16 | n:594, p:13 (`__dict__.get`); supply/fertilisation.py:207 (W :209), :440; supply/policy.py:58-59; supply/supply_module.py:3288 | the InnerFertDist object | string, also written from the supply code; mutable: `set_variant` (n:597) and `_pri_cal[...] =` (n:599) |
| `_min_n2o_cache` | n:725 (setdefault), n:730 | n:726, 731 | mineral N2O-N per N by region | string |
| `_p_ratio_base` | p:118 (`setdefault(cr, ratio)`) | p:118 | manure P applied ratio at the first call per CAPRI region | string; the first value seen, so it depends on the manure-trade setting of the instance's first run (documented p:115-117) |

Why par: each is built from the base data (or the run's fixed inputs) and reused; none changes in a solve except by
adding keys. They are the analogue of the supply's `ef_lea_cache`, `input_cost_memo` (SUPPLY_STATE_INVENTORY par).

### 1.2 ev (9): one region's evaluation (compute_indicators), passed between its blocks

| name | W | R | holds | flags |
|---|---|---|---|---|
| `_grass_override` | n:203, 207, 234, 237, 242, 246 (`__dict__[...]`) | n:183, 199 (`__dict__.get`) | which CAPRI grassland activity (GRAE/GRAI) stands for GRAS during a call | string; set and reset in try/finally |
| `_nitrate_share_now` | em:214, em:344 (the same value twice) | g:104 (getattr) | nitrate shares of the region's rations | string |
| `_supp_ch4` | em:239 (after `hasattr`, em:238), em:240 | g:107 (getattr) | feed supplements' enteric CH4 factor, by region | string; a dict by region never cleared, read by the current region only |
| `_feed_dm_now` | em:242 | g:112 (getattr) | feed dry matter per animal of the region | string |
| `_region_now` | em:243 | g:115-116 (getattr) | the region being evaluated | string |
| `_nh3_saved_last` | em:342, 366 | em:371, em:558 (getattr), n:618 (getattr) | NH3-N kept by the ammonia options | string |
| `_n_kept_last` | em:343, 370 | n:618 (getattr) | manure N kept by the options | string |
| `_nitrate_nh3_extra` | em:345, 358 | em:558 (getattr) | NH3 of the nitrate supplement's extra N | string |
| `_fert_dist_now` | em:399, 408, 416, 657 | em:660 | the region's fertiliser distribution rows | collected by run_all_regions |

Why ev: written at the start of compute_indicators (or reset there, em:342-345) and read later in the same call by
compute_ghg, fert_distribution or run_all_regions. compute_indicators is also called by supply/ghg_tax.py:48 on
CAPRIModel's instance; each call rewrites them. [verified]

### 1.3 seen (1), res (1), removed (1)

| name | W | R | holds | proposed |
|---|---|---|---|---|
| `manure_trade_on` | n:16 (`set_manure_trade`, called from m:331, m:334, supply_module.py:2441, 2551, 2576, 2608, 2990, 3166) | getattr default True: n:14, 39, 328, 445, 597, p:114 | the run's manure trade switch | seen: set by the caller before use |
| `last_fert_dist` | em:668 | m:1341 (getattr) | the run's fertiliser distribution table (results["fert_dist"]) | res |
| `_leaching_last` | em:529 | none | the last region's leaching result | write-only: remove (as stage 3's S1) |

## 2. CAPRIModel (and the coupling mixins)

Set in `__init__` only (not listed): `data_dir`, `regions`, `base_year`, `data`, `supply_elasticities`,
`supply_module`, `market_module`, `policy_module`, `env_module` (m:156-197). [verified]

### 2.1 par (14): parameters and caches built once per base, baseline or run

| name | W | R | holds | flags |
|---|---|---|---|---|
| `_eu_base_cache` | m:399 (`= getattr(...)`), m:1317 | m:398 (getattr), via `_cache` m:426, 443-465; tc:729, 3680-3682 | per baseline key (regions, endotech key, manure trade, biofuel markets): EU27 production and consumption, demand calibration, base tables, the bilateral systems (references), crush base, aligned use, Norway's milk | string; a positional tuple (lengths tested at m:445, 450, 464); holds `market.par.bilat` by reference (m:1324, restored m:452) |
| `_yani_ref` | m:1309-1310 | m:549 (getattr), m:1309 | young-animal net balances of each baseline key | string |
| `_base_supply_cache` | m:1312-1313 | m:236 (getattr) | the baseline's supply results per key (emission tax coefficients) | string |
| `_ghg_coef_cache` | m:233 | m:231, m:1314 (getattr, pop); tc:273, 353 | emission tax coefficients per baseline key | string |
| `_hessian_key` | m:406, h:47, h:53 | m:426 (getattr) | the baseline key the market's supply Hessian belongs to | string |
| `_endotech_key` | m:225 | m:219 (getattr), h:110 (getattr, in the Hessian's cache key); tc:730 | key of the applied endotech settings | string; cache key (risk 7.1-1) |
| `_dairy_yield_cache` | b:243 | b:216 (getattr) | dairy products per t raw milk by member state | string |
| `_proc_yield_cache` | b:258 | b:250 (getattr) | olive oil and milled rice yields | string |
| `_sugar_rate_cache` | b:275 | b:267 (getattr) | sugar per t beet by member state | string |
| `_pool_cost_cache` | mn:78 | mn:71 (getattr) | manure pools' trade costs | string |
| `_ration_model` | f:44 | f:39, 121, 152 (getattr); tc:3348 | CAPRI's ration model | string |
| `_feed_rations_stable` | f:73 | f:76 | rations by region, built once per ration model | identity matters: the supply's feed block caches on the dict's identity (f:70-71) |
| `_feed_rations_for` | f:74 | f:72 (getattr) | the ration model `_feed_rations_stable` was built for (identity) | string |
| `_excluded_units` | b:188 | f:153 (getattr) | the EU units outside a run on a subset (K83) | string; per run (part of the baseline key's region set) |

### 2.2 sv (29): state carried from one outer iteration (or run) to the next

| name | W | R | holds | flags |
|---|---|---|---|---|
| `_hessian_pending` | m:1263 | m:350, 437 (`__dict__.pop`) | what the next run needs to measure the baseline's Hessian | string; carried from a baseline run to the next run |
| `_relax_w` | m:829, 838 | m:820 (getattr) | adaptive step per product | string |
| `_relax_gprev` | m:829 | m:821 (getattr) | previous gaps per product | string |
| `_capri_target_hist` | m:834 | m:832 (getattr) | CAPRI price forecast's last targets | string |
| `_capri_blockdev_hist` | m:865 | m:863 (getattr) | the same for the trade blocks' departures | string |
| `_capri_special_hist` | m:897 | m:879 (getattr) | the same for capri_step_special | string |
| `_capri_sup_hist` | m:947 | m:945 (getattr) | the same for Norway | string |
| `_capri_sup_full` | m:952 | m:950 (getattr) | Norway's full price history | string |
| `_capri_yani_hist` | m:576, ya:247 (`__dict__.setdefault`) | ya:248 | young-animal price history | string |
| `_milk_ms_full` | m:1025 (`__dict__.setdefault`), m:1027-1028 | m:1031 | member states' milk price history | string; never reset as a whole (per member state at iteration 0, m:1026-1027) |
| `_eu_dev` | m:627, 870 | m:629, 762, 847, 883, f:18 (getattr) | trade blocks' price departures | string |
| `_sup_dev` | m:628, 971 | m:635, 768, 907, f:25 (getattr); test_norway_market.py:246 writes it on a stand-in | Norway's price departures | string |
| `_special_ms_dev` | m:651, 876, m:892 | m:641 (getattr) | special-smoothing departures by member state | string |
| `_sup_w` | m:970 | m:910 (getattr) | Norway's adaptive steps | string |
| `_sup_gprev` | m:912, m:941 | m:929 | Norway's previous steps | |
| `_milk_ms_signal` | m:1049 | m:614, 978, 1074 (getattr) | member states' milk price signals | string |
| `_milk_ms_w` | m:1049 | m:979 (getattr) | their adaptive steps | string |
| `_milk_ms_gprev` | m:1049 | m:980 (getattr) | their previous gaps | string |
| `_milk_ms_hist` | m:1050 | m:981 (getattr) | their forecast histories | string |
| `_yani_w` | m:547, ya:252 | ya:232 (getattr) | young-animal adaptive steps | string |
| `_yani_gprev` | m:547, ya:252 | ya:233 (getattr) | their previous gaps | string |
| `_pool_state` | m:607, mn:160, 226 | mn:128, 146 (getattr) | N manure market's plan, kappa, net exports | string; in `_POOL_STATE` (mn:11) |
| `_pool_accel` | m:608, mn:257 | mn:241 (getattr) | manure market's damping | string; in `_POOL_STATE` |
| `_pool_pk` | m:598, mn:25 (`__dict__.setdefault`) | mn:29-41 | the P and K markets' copies of the nine `_POOL_STATE` fields, by those names | string |
| `_capri_stop` | m:577, ps:34 | m:1238-1239 (getattr), ps:31 (getattr), ps:35; test_capri_stop.py:95, 102 | CAPRI's stop rule (accumulates steps) | string |
| `_trace_prev_prem` | m:1111 | m:1106 (getattr) | trace only: last premium | string |
| `_trace_go_prev` | m:1147 | m:1141 (getattr) | trace only: last gross output | string |
| `_trace_nlp_prev` | rp:31 | rp:16 (getattr) | trace only: last NLP levels | string |
| `_trace_nlp_t` | rp:35 | rp:34 (getattr) | trace only: last time | string |

Reset points today: most are reset at iteration 0 by the code that reads them (m:576-577, 598, 607-610, 627-628,
651, 822, 832, 863, 879, 911-912, 945, 950, 982-983; m:547 every run). Not reset per run: `_milk_ms_full` (per member
state only), the four traces, `_capri_*_hist` only through `if outer_iter > 0`. Resetting `sv` whole at the start of a
run would be a behaviour change (its own commit). [verified for the lines; effect inferred nil]

### 2.3 seen (2): what the coupling recorded from the modules' last solve and reads later

| name | W | R | holds | flags |
|---|---|---|---|---|
| `_last_spol` | m:702 | h:68 (getattr); tools/check/pmp_supply_elas_check.py:61, tools/check/pmp_cross_term_check.py:49 (getattr default None) | the policy dict of the last supply call (the Hessian re-solves with it) | string |
| `_last_supply_results` | m:703 | m:1138 (getattr), f:51 (getattr); tc:3352 | the last supply results (next iteration's ration state) | string |

(Alternative: `sv`. CAPRIModel has no caller that sets inputs before a solve, so `seen` here means "recorded from the
modules"; question Q2.)

### 2.4 ev (6): one outer iteration's working values, passed between the coupling's methods

| name | W | R | holds | flags |
|---|---|---|---|---|
| `_outer_iter_now` | m:572 | ya:249 (getattr) | the outer iteration | string |
| `_ls_by_country` | m:751, h:77, h:326, b:206, b:209 | b:89, b:204 (getattr) | livestock products by country: a hidden argument of `_bridge_supply_to_market` | string; the Hessian overwrites it (h:77) and recomputes it from the baseline's results (h:326); b:204-209 save and restore it |
| `_blockdev_target_now` | m:859 (`__dict__.setdefault`) | m:882 (getattr) | trade blocks' target departures of the iteration | string; never cleared |
| `_hessian_at_scenario` | m:723, 734 | h:154 (getattr, in the cache key) | flag around a scenario Hessian measurement | string |
| `_yani_np` | ya:221 | ya:253 (getattr) | young-animal (net, production) of the iteration | string |
| `_ration_state` | f:78 | f:120 (getattr); tc:3349-3351 | ration state of the iteration | string |

### 2.5 res (21): results and diagnostics read by the stop test, the metadata, the trace, the run script or tests

| name | W | R | flags |
|---|---|---|---|
| `_calib_drift` | m:709, 712 | m:714, 1121, 1173 (getattr) | string |
| `_calib_trace` | m:713, m:714 | m:1377 (metadata base_calibration_drift) | string; rounded to 5 decimals (m:714) |
| `_capri_stop_verdict` | m:1180 | m:1365, 1367 (getattr; metadata capri_stop) | string |
| `_capri_drift` | m:1236, 1239 | m:1240-1247, 1366 | string |
| `_eu_dev_gap` | m:843, 869 | m:869, 1167 (getattr) | string |
| `_sup_dev_gap` | m:904, 967 | m:966, 1120, 1165, 1370 (getattr) | string |
| `_sup_dev_worst` | m:967 | m:1120, 1371 (getattr) | string |
| `_sup_dev_gap_all` | m:969 | m:1120 (trace) | string |
| `_milk_ms_worst` | m:1044 | m:1118 (trace) | string |
| `_milk_ms_small_gap` | m:1051 | m:1397 (metadata) | string |
| `_nlp_tol_trace` | m:568, m:585 | m:1372 (metadata) | string |
| `_outer_history` | m:1099 | m:1061, 1183-1184, 1353, 1390 (getattr); test_capri_stop.py:93 | string; in the run pickle (rs:323) |
| `_yani_imbalance` | m:545, ya:185, 220 | m:1073, 1113, 1172, 1379 (getattr), ya:283, 286 | string |
| `_yani_detail` | ya:279 | ya:283, 286, m:1380 (getattr) | string |
| `_pool_imbalance` | m:610, mn:44, 144, 272 | m:1121, 1170 (getattr), mn:23 | string; `_POOL_STATE` |
| `_pool_worst_key` | mn:46, 163 | m:1121, mn:24 (getattr) | string; `_POOL_STATE` |
| `_pool_gaps` | mn:42 | tc:326 only | |
| `_pool_solver_status` | mn:207 | m:1121 (getattr) | string; `_POOL_STATE` |
| `_pool_eu_unaccounted` | mn:271 | m:1121 (getattr) | string; `_POOL_STATE` |
| `market_supply_hessian_info` | m:726, 731, h:55, 169, 336; h:341, 343, 347 | m:726, 731, h:171, 351; rs:414-415 (getattr default None) | string (run script) |
| `market_supply_hessian_log` | h:171, 351 (`__dict__.setdefault`), m:727 | test_market_layers.py:122-150; rs:416-417 (getattr default None) | string |

### 2.6 Removed, kept, read but never written

| name | W | R | proposal |
|---|---|---|---|
| `endotech` | m:224 | none (grep of `.endotech` outside scenario objects) | write-only: remove |
| `_ration_prev` | f:79 | none | write-only: remove |
| `_yani_trace` | m:546; appended ya:283 | none but its own append | write-only: remove |
| `_pool_trace` | m:609, mn:273 | its own append only (mn:273); swapped by `_POOL_STATE` | write-only: remove |
| `_pool_flows` | mn:225 | only swapped by `_POOL_STATE` | write-only: remove |
| `_pool_solver` | mn:206 | only swapped by `_POOL_STATE` | write-only: remove |
| `use_manure_market` | m:324, 434; `del` m:340; `__dict__.pop` m:320 | m:362, 593, 776, 1121 (getattr), h:110 (getattr, cache key); tc:345 | keep: a run-state setting descriptor (m:94; settings/__init__.py:252-288 stores the instance value in `__dict__`) |
| `verbose` | m:156 (`__init__`), m:430, 436 | 15 sites in m, ya:284, rp:144 | keep (a switch, set around the baseline sub-run) |
| `trace_outer` | never written (grep) | ya:284 (getattr default False) | the young-animal trace prints with `verbose` only, not with diagnostics.trace_outer: read the setting (an output change, its own commit) |

### 2.7 The coupling's writes on other objects (not CAPRIModel's state; for the market's and supply's owners)

| object | attribute | W | note |
|---|---|---|---|
| MarketModule | `biofuel_markets` | m:329, 435; `del` m:341 | run-state setting |
| MarketModule | `biofuel_output_scale`, `biofuel_mandate`, `negative_milk_price`, `trq_volume_changes` | m:370, 374, 376, 512 | scenario inputs, not in MarketSeen |
| MarketModule | `_milk_floor_hits` (reset), `_dom0_cache`, `_crush_cache` (reset to None) | m:377, 422, 461 | market caches outside market/state.py's objects |
| MarketModule | `_world_prices_base0`, `world_prices_base` | m:532, 538 | pristine copy and the run's base |
| RegionalSupplyModel (class) | `nlp_tol`, `use_fert_allocation`, `use_manure_pool` | m:584, 1251, h:41; m:594; m:595 | class-level run state (STAGE3B 1.4) |
| RegionalSupplyModel (instance) | `_Q_inv` | ya:125 (R ya:122, getattr) | a cache the coupling writes on the regional model; not in SUPPLY_STATE_INVENTORY nor its MOVED tables [verified by grep]; whether stage 3's inventory test allows it: not determined |
| RegionalSupplyModel | `seen.nlp_cal_check`, `res.nlp_fallback_log` | m:606; m:393, 442 | already declared (stage 3) |

## 3. Class-level attributes

| class | name | where | kind | note |
|---|---|---|---|---|
| EnvironmentalModule | `_ENT_CACHE` | declared em:181; W g:194 (`cls`); R g:183, 195 | cache (enteric_feed_factors.csv) | shared by every instance, built from `_inputs.current()`, never invalidated |
| EnvironmentalModule | `_CROP_N` | declared em:169; W n:127 (`cls`), n:176; R n:125, 179-182 | cache (capri_crop_n_coefs_2030.csv) | idem |
| EnvironmentalModule | `_CROP_N_MAP` | not declared; W n:132; R getattr default {} n:61, 177, 297 | cache (identity map) | created on the class at run time |
| EnvironmentalModule | `_GNB_TOT` | not declared; W n:59, 296 (`type(self)`); R getattr n:55, 292 | cache (capri_gnb_components_2030.csv) | idem; two writers |
| EnvironmentalModule | `_FERT_SIDE` | declared em:184; W n:668; R n:666, 669 | cache (fert_side_effects.csv) | shared |
| EnvironmentalModule | `_P_APPL` | not declared; W p:28; R getattr p:22 | cache (npk_dataout_2030.csv.xz) | idem |
| EnvironmentalModule | `ENDO_MAN_AV_SLOPE` | em:163 | CAPRI constant | section 4 |
| EnvironmentalModule | `_CAPRI_CROP`, `OWN_RESIDUE_CROPS` | em:167, em:178 | code tables | section 5 |
| EnvironmentalModule | `ad_dairy_ch4` | em:190 | setting descriptor (environment.ad_dairy_ch4) | live read |
| (module) | `EF_SOIL_N2O_DIRECT`, `EF_SOIL_N2O_INDIRECT`, `GWP_CH4`, `GWP_N2O` | em:42-46 | `param()` at import | read from params.py's fixed path, not the run's data directory (STAGE3B Q6) |
| LUCModel (environmental/luc.py) | `_inst` | luc.py:33, W :44 | singleton cache | outside EnvironmentalModule; not inventoried further |
| PCropCoefs (environmental/p_balance.py) | `_inst` | p_balance.py:39, W :51 | singleton cache | idem |
| CAPRIModel | 19 setting descriptors | m:87, 89, 94, 97, 104, 108, 115, 120, 127, 255, 1443, 1451, 1453, 1454, 1459, 1460, 1462, 1467, 1474 | settings (live reads) | `use_land_market` and `grassland_allowance` are not read through CAPRIModel in m or coupling [verified by grep] |
| CAPRIModel | `progress`, `progress_t0` | m:1415-1416 | run state on the class | set on the class by rs:123 |
| CAPRIModel | `MARKET_SUPPLY_FEED_COLS`, `FEED_BULKS`, `LIVESTOCK_PRODUCT_MARKET` | m:1445, 1478, 1481 | code tables (the last a mutable dict) | section 5 |
| CAPRIModel | `_MS_CODE`, `POOL_OF_PREFIX`, `_CAPRI_MS` | m:1435, 1448, 1486 | three names for definitions.MS_CODE (one object) | |
| (module) | `_POOL_STATE` | mn:11-12 | names swapped by setattr/`__dict__` (mn:30-39) | risk 7.1-3 |
| (module) | `supply_code_fingerprint` (lru_cache) | h:17-32 | process memo | part of the Hessian's cache key (h:155) |

The six mixins of EnvironmentalModule and the seven of CAPRIModel declare no class attributes (AST scan). [verified]

## 4. Numbers that look like constants or solver settings

Unit conversions (1000, 1e3, 1e6, 0.001 between kg, t, kt; x100 for percentages) are left out: em:380, 427-452, 481,
497, 509, 528, 539, 552, 560; g:106, 109, 119, 125-130, 150, 159, 171; n:146, 167, 175, 703; a:41; f:132-171; ps:53;
h:91; mn:77; rp:72-73, 100, 106-109, 140; m:1556-1595. Census columns: "03/04" = in capri_data/schema/03_code_data.sql
with its status in 04 (make_code_data.py drops 0.5, integers up to 12 and powers of ten, so the others are absent).

### 4.1 Environment (13)

| # | file:line | value | what | census | proposed home |
|---|---|---|---|---|---|
| E1 | em:163 | -0.0015 | slope of manure N availability on manure N per ha | 03/04: capri, endoManAvail.gms l. 61; "duplicate of fert/npk.py ENDO_MAN_AV_SLOPE" | parameters file, one row read by both (fert/npk.py:29 holds it as {"N": -0.0015, ...}) |
| E2 | n:104-105 | 0.999 | availability ceiling at zero application | 03/04: capri, endoManAvail.gms l. 72-73 | parameters; the same literals at fert/npk.py:34-35 |
| E3 | n:107-108 | 0.2 | availability floor | 03/04: capri, l. 79-81 | parameters; fert/npk.py:37-38 |
| E4 | n:106 | 300.0 | kg N/ha at which the floor holds | 03/04: capri, l. 79-81 | parameters; fert/npk.py:36 |
| E5 | g:108, g:120 | 10.0 | enteric CH4 reduced 10% per point of nitrate share of DM (comment g:103) | absent (filter) | parameters; source not cited in the code: not determined |
| E6 | g:120 | 4.1868 | MJ per Mcal | 03/04: physical | units.MJ_PER_MCAL (exists, units.py:14; Q5) |
| E7 | g:120 | 55.65 | MJ per kg CH4 | 03/04: capri, gases.gms l. 359, 371 | **already the parameter MJ_PER_KG_CH4** (model_parameters.csv; read by supply/ghg_tax.py:62): read it here |
| E8 | g:165; n:730 | 0.10 | IPCC's volatilised share of mineral N (FracGASF; em:41 cites gases.gms N2OSYN) | absent (power of ten) | parameters (kind ipcc). g:165 is dead in effect: compute_indicators overwrites N2O_SOIL and CO2_UREA (em:426-433) for the call at em:274 and uses only N2O_MAN of the call at em:338 [verified]; n:730 is live (fallback where CAPRI's fractions are missing) |
| E9 | g:139, 162, 166, 175; em:428, 430, 433, 448, 452, 499, 500, 528, 567 | 44/28 | N2O/N2O-N | 03/04: physical | units.M_N2O, M_N2O_N (exist; Q5) |
| E10 | a:44-45; em:552, 560, 567 | 17/14 | NH3/N | 03/04: physical | units.py (new M_NH3, M_NH3_N; Q5) |
| E11 | em:259 | 1e-9 | area above which a realised yield is taken | absent | keep as a guard, or settings (numerical) |
| E12 | n:638 | 0.998 | caps scaled to leave 0.2% room | 03/04: numerical | settings ([fertiliser] or [environment]) |
| E13 | em:654 | 50 | progress print every 50 regions | 03/04: technical | settings [diagnostics] |

Already parameters: EF_SOIL_N2O_DIRECT, EF_SOIL_N2O_INDIRECT, GWP_CH4, GWP_N2O (em:42-46, at import),
WINTERCOV_NO3_REDUCTION (n:712, 713, 760; p:56-57), EF5_LEACHING_N2O (n:785). Already a setting: ad_dairy_ch4 (em:190).

### 4.2 Coupling (13)

| # | file:line | value | what | census | proposed home |
|---|---|---|---|---|---|
| C1 | m:833, 864, 946, 1016; ya:248 | 4 (slice `[-4:]`) | price histories kept: the length of outer_loop.capri_step_weights_late (4 weights) | absent | derive from the setting's length |
| C2 | h:105 | 1e-6 | kt of base supply for a product to be shocked | absent | settings [market] (changes the shocked set) |
| C3 | h:301 | 1e-9 | Hessian entries below it dropped | absent | settings [market] |
| C4 | h:108-109 | round 3, 6 | rounding in the Hessian's cache key | absent | keep (a change invalidates every cached Hessian) |
| C5 | h:252 | 5 | progress line every 5 shocks | absent | settings [diagnostics] |
| C6 | mn:106 | 60 | NNLS iterations per column | 03/04: numerical | settings outer_loop.manure_pool_* |
| C7 | mn:100; mn:101 | 1e-6; 1e-9 | active-row and at-bound tolerances of the multiplier recovery | absent | settings outer_loop.manure_pool_* |
| C8 | mn:129; mn:177 | 1e-3; 1e-3 | kappa floor; ridge on the arcs (x min slope) | absent | settings; the floor cannot bind after the first update, kappa being clipped to manure_pool_kappa_bounds [0.05, 1.5] at mn:157-158 [inferred] |
| C9 | mn:105, 199, 244, 270; mn:225 | 1e-12, 1e-9; 1e-3 | division guards; flows reported above 1e-3 | absent | keep (guards); mn:225 goes with `_pool_flows` (write-only) |
| C10 | m:1115; m:1118 | 1e-3; 0.005 | trace display thresholds | absent | settings [diagnostics] |
| C11 | m:714; m:1079; ya:279-281 | round 5; 4; 4, 2 | rounding of metadata and history entries | absent | keep (reporting precision; a change alters the pickle) |
| C12 | m:1551 | 0.5 | default weight of VSET when the data has no w_vset | absent | a fallback with no source: remove (fail on missing data) or a parameter; reporting only |
| C13 | m:1503, 1538, 1571; m:445, 450, 464; rp:11, rp:28 | 2030; 2, 5, 6; 4; 0.01, 1e-6 | market-year selector (03/04: technical, keep); positional lengths of `_eu_base_cache` tuples; trace's top 4 and relative-move floor | 03/04 for 2030 only | keep the year selector; replace the tuple by a named record when `_eu_base_cache` moves; trace numbers to [diagnostics] |

Already settings: price_relaxation, relax_step_*, relax_floor, milk_ms_relax_floor, milk_ms_min_share,
capri_step_weights*, capri_step_special, drift_report_steps, sup_gap_min_prod, norway_gap_last_iter, manure_pool_*
(tol, kappa_bounds, min_plan, omega_*, qp_tol), young_animals.* (tol, relaxation, ratio_bounds, max_step,
small_market_scale), market.nq_price_shock, market.hessian_*.

## 5. Code tables

| # | table | where | possible CAPRI source (to check) |
|---|---|---|---|
| T1 | `_CAPRI_CROP` (CAPRI crop -> model crops) | em:167-168 | capri_data/codes/model_activities.csv: its SETA row is SETA;FALL (CAPRI) and VSET;FALL (CAPMOD); the table's SETA = SETA, FALL, VSET is their union; GRAS = GRAE, GRAI is the CAPMOD column |
| T2 | `OWN_RESIDUE_CROPS` | em:178 | PERM_NGRP and PERM (supply/define_ngrp_sets.gms, cited em:175-176) through crops_to_ngrp; fert/npk.py:26 has PERM_NGRP |
| T3 | ("GRAE", "GRAI") | n:171, 233, 241 | CAPMOD members of GRAS (model_activities.csv; SplitActs) |
| T4 | ("MINE", "EXCR", "CRES") | n:650 | a copy of fert/npk.py:25 SOURCES (HARDCODED_TABLES: about 10 copies) |
| T5 | ("DCOL", "DCOH") | g:260 | CAPRI's dairy split activities (SplitActs) |
| T6 | ("N2OSYN", "NH3SYN"); NO3SLEA, NO3SRUN, NO3MLEA, NO3MRUN | n:670; n:754-757 | items of p_litRevFertTechs (data keys of fert_side_effects.csv) |
| T7 | ("crop", "grass"); "PHOF", ["EXCRET", "MTRADE"] | em:445; p:25 | the model's histosol classes (supply's HISTOSOL_CLASSES, N6); calc_nbalance.gms rows |
| T8 | `FEED_BULKS` and `traded` | m:1478; ps:45 (same 5 codes, other order) | FEED_TRD (global/fromimpact/sets.gms, cited m:1477); HARDCODED_TABLES counts 3 copies |
| T9 | `MARKET_SUPPLY_FEED_COLS` | m:1445 | not determined (possibly FEED_TO_O, capri_data/codes/capri/FEED_TO_O.csv) |
| T10 | `LIVESTOCK_PRODUCT_MARKET` | m:1481-1482 | CAPRI final product -> market commodity (tools/build/build_livestock_products.py) |
| T11 | `livestock_maps` (market product -> animals) | b:81-87 | the inverse of the animal -> product table (N6_CODE_TABLES: three copies) |
| T12 | `direct_maps` (activity -> market commodity) | b:62-70 | model_activities.csv / model_commodities.csv: not determined |
| T13 | dairy pairs and the dairy items | b:154-155; b:227 and b:239 (same 9 codes twice) | DAIRY_DEF (HARDCODED_TABLES: 5 copies); ("COMI", "SGMI") b:225 |
| T14 | "price follows": SUGB -> SUGR, DWHE -> SWHE, DCOW -> MILK | m:803-807, 851-854, 894, 915-920, 964, 1128; h:276-279 | arm/set_prices.gms (cited m:801-802) and WHEA; 7 sites, one declared table |
| T15 | ("MILK", "DCOW") priced per member state | m:856 | raw milk (dairy blocks) |
| T16 | animal lists of the history | m:1067; m:1080 | definitions.ANIMALS subsets (diagnostics only) |
| T17 | land rows -> land types | rp:64 | landTypesMrk (capri_data/codes/capri/landTypesMrk.csv; model_land_types.csv) |

Also in the package, outside EnvironmentalModule: luc.py:29 `CLS`, luc.py:56 land types, p_balance.py:26 `ITEMS`.
feed.py:174 maps data-column suffixes to bulks (model data, not a CAPRI set). [verified that the literals stand there;
the sources are to be checked as N6 did]

## 6. Proposed order of moves

Each step is a pure move (old names in MOVED tables raising RuntimeError, as capri_mod/supply/state.py), checked by
the mini-EU Farm-to-Fork run (tools/run/run_mini_eu.py, PYTHONHASHSEED 0) against the previous batch with
tools/check/compare_pickles_exact.py at 1e-12. The pickle holds the environmental tables (rs:261), fert_dist (rs:266,
298), outer_history (rs:323), capri_stop and the Hessian's info and log (rs:414-420), so every field moved here that
reaches the results is compared. The Hessian's info carries its measuring time ("seconds", h:338), which the
comparison must ignore. Every edit outside market/, tests/ and pipeline/ changes supply_code_fingerprint (h:18-32,
155), so each gate measures the mini-EU Hessian again (time only, if the move is pure [inferred]).

| step | content | readers outside the moved class | batch |
|---|---|---|---|
| E0 | capri_mod/environmental/state.py (par, ev, seen, res; no sv) and capri_mod/coupling/state.py (par, sv, seen, ev, res), empty, with MOVED_ENV / MOVED_MODEL guards; a string-scan test as test_supply_state.py:76 extended to tools/ and to `_POOL_STATE`; an inventory test (after a short run the instance attributes are declared); a deepcopy test (tc:57-65 deep-copies the model) | - | B1 |
| E1 | remove the 7 write-only (`_leaching_last`; `endotech`, `_ration_prev`, `_yani_trace`, `_pool_trace`, `_pool_flows`, `_pool_solver`, the last three also from `_POOL_STATE`) | none | B1 |
| E2 | environment par (16); the class-level caches stay | supply/fertilisation.py:207-209, 440; supply/policy.py:58-59; supply/supply_module.py:3288 (`_inner_fert` by `__dict__`); tc:3503 (`_amm_tm`) | B2 |
| E3 | environment ev (9), seen (`manure_trade_on`), res (`last_fert_dist`) | m:1341 | B2 |
| E4 | coupling par (14), `_eu_base_cache` kept a tuple, references not copied | h:110 (cache key); tc:273, 353, 729-730, 3348, 3680-3682 | B3 |
| E5 | coupling sv without the pools (26: price-step state, histories, departures, milk, young animals, `_capri_stop`, `_hessian_pending`, traces) | f:18, 25; test_norway_market.py:246; test_capri_stop.py:95, 102 | B3 |
| E6 | manure pools: sv `_pool_state`, `_pool_accel`, `_pool_pk`; res `_pool_imbalance`, `_pool_worst_key`, `_pool_gaps`, `_pool_solver_status`, `_pool_eu_unaccounted`; `_POOL_STATE` as paths, swapped with the path helpers of supply/state.py | tc:326 | B4 |
| E7 | coupling seen (2), ev (6), the other res (16 incl. the Hessian's info and log) | rs:414-417; tools/check/pmp_supply_elas_check.py:61, pmp_cross_term_check.py:49; test_market_layers.py:122-150; test_capri_stop.py:93; tc:3349-3352 | B4 |
| E8 | numbers: (a) units (E6, E9, E10), pure; (b) parameters (E1-E4 merged with fert/npk.py, E7 read from the existing row, E8, E5 once its source is found); (c) settings (E11-E13, C1-C3, C5-C8, C10); (d) em:42-46 read through the run's data directory (Q6), its own commit | fert/npk.py | B5 |
| E9 | code tables T1-T17 as declared CSVs or CAPRI's sets; where a set differs from the table, the change is a separate behaviour change | bridge, price_step, supply (shared tables) | B6 |
| E10 | documentation: the inventory as docs/design/ENV_COUPLING_STATE_INVENTORY.md, ARCHITECTURE_REFACTOR's stage table, CHANGELOG | - | B6 |

Left for separate behaviour changes (each its own run): reading diagnostics.trace_outer at ya:284; an explicit
loader for `_amm_tm` (risk 7.1-5); `_p_ratio_base` keyed on the manure-trade setting; resetting `sv` whole per run;
removing the m:1551 fallback; the dead soil-N2O branch of compute_ghg (g:142-166, 173-175).

## 7. Risks and open questions

### 7.1 Risks

1. **The Hessian's cache key reads coupling fields by getattr with defaults.** h:110 reads `use_manure_market` and
   `_endotech_key` (default ""), h:154 `_hessian_at_scenario` (default False). If one of them moved without the
   guard raising, the default would silently enter the key: a stale cached Hessian could be reused, or a new one
   measured (49 min for the full Farm-to-Fork, m:102). The guard must raise RuntimeError on old names (as MOVED)
   so a getattr default cannot hide them; the key string should be checked unchanged across E4 and E7. [verified
   for the reads; the effect inferred]
2. **The environmental module crosses the fork and is reached by string from the supply code.** The workers are forked
   with SupplyModule as a module global (supply_module.py:3172); each regional model is pickled back without
   `seen.env_for_surplus` (popped at 3275, re-attached in the parent at 3187). What a worker writes on the shared
   EnvironmentalModule (the par memos of 1.1, `_inner_fert` written by supply/fertilisation.py:209, the
   InnerFertDist's `_pri_cal` at n:599, and the class-level caches of section 3) is lost when the worker ends; today
   that only costs rebuilding [inferred]. The supply code reads and writes `_inner_fert` through `__dict__`
   (fertilisation.py:207, 440; policy.py:58-59; supply_module.py:3288), which no `__getattr__` guard sees. The slot
   objects must survive pickling and deepcopy (tc:57-65 deep-copies CAPRIModel with both modules).
3. **The Hessian's save and restore do not cover this state.** hessian.py's `_snapshot`/`_restore` (h:199-220) save
   the regional models' NLP_STATE/SOLVE_STATE and SupplyModule._PAR_STATE only. During a measurement the Hessian
   changes CAPRIModel's `_ls_by_country` (h:77) and recomputes it from the baseline's results at the end (h:326), and
   reads `_last_spol` (h:68); the regional solves use env_for_surplus's memos, which are not restored (pure memos
   keyed on their inputs [inferred]). The manure pools' nine fields are swapped by name (mn:30-39) and `_pool_pk` stores
   them under those names: E6 must turn `_POOL_STATE` into paths across two objects (sv and res).
4. **The run script and tools read fields by getattr with defaults.** rs:414-417 (`market_supply_hessian_info`,
   `market_supply_hessian_log`, default None) and tools/check/pmp_supply_elas_check.py:61,
   pmp_cross_term_check.py:49 (`_last_spol`, default None): after a move without updating them they would record None
   silently. rs:123 sets `progress` and `progress_t0` on the class; rs:211-230 call `env._n_excretion` (a method,
   unaffected). The projection builds fresh models (projection_module.py:465-467, 484-490) and the run script reads
   the last one through `_last_projected_model`.
5. **Class-level caches and an order dependency.** The six EnvironmentalModule caches of section 3 are shared by every
   instance (both modules, test instances, the projection's fresh models), built from `_inputs.current()` and never
   keyed on the data directory or base year. Moving them into each instance's `par` would rebuild them per instance
   (time) and is not needed for a pure move. Separately, `_amm_tm` is loaded only by `_manure_n2o_tech` (g:214-217),
   while four readers take an empty default (g:235, 250, 269, n:697): in compute_indicators the leaching (em:526) runs
   before the phosphorus balance loads it (em:576 -> p:39), and `_manure_n2o_tech` runs earlier only where the region
   has manure technology shares (em:460-461). The first regions evaluated on an instance can therefore get leaching
   without the cascade data. Whether any result changes: not determined (none if those regions have no animals
   [inferred]).

Also: `_feed_rations_stable` and `_eu_base_cache` hold objects whose identity matters (f:70-71; m:1324, 452), so a
move must keep references, never copies; `_blockdev_target_now` and `_supp_ch4` are never cleared; `_Q_inv` (ya:125)
is an undeclared cache on the regional models.

### 7.2 Open questions

- **Q1** The environment without `sv` (four objects), and CAPRIModel with all five?
- **Q2** `_last_spol` and `_last_supply_results` in `seen` ("recorded from the modules"), or in `sv`?
- **Q3** The EnvironmentalModule class-level caches: kept on the class in this stage (pure), or moved to a registry
  keyed on the data adapter (a later change)?
- **Q4** The six write-only coupling fields: removed (as stage 3's S1), or kept in `res` as diagnostics?
- **Q5** `use_manure_market` and `verbose` kept on the model (proposed), as the supply kept its class-level settings?
- **Q6** The source of the nitrate factor 10.0 (g:108, 120) before it becomes a parameter.
- **Q7** The coupling's writes on MarketModule (section 2.7: `_dom0_cache`, `_crush_cache`, `_world_prices_base0`,
  `_milk_floor_hits`, the scenario inputs) and `_Q_inv` on the regional models: declared in their owners' objects as
  part of this stage, or left to the market and supply owners?
