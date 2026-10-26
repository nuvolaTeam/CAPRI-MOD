# Architecture refactor and CAPRI-claim audit (started 24 October 2026)

Project lead, 23 October 2026: the modules are too large (market_module.py 3,243 lines, supply_module.py 7,542), and
many comments say "CAPRI does X" and then implement something else. Agreed: reorganise in stages, and check every
CAPRI claim against the GAMS code.

## 1. Target

Two axes.

**Layers** (one direction of dependency, top to bottom):

| Layer | Holds | Rule |
|---|---|---|
| data adapters | the CSV inputs as typed parameter objects | the only code that reads files |
| calibration | calibrated parameters from the parameters and the base point (PMP, demand system, Armington shares, the supply Hessian) | no file access; no solve of the scenario |
| equations and solve | the supply models, the market, the environmental accounts and their coupling loop | pure functions of calibrated parameters and prices/quantities |
| scenarios | shocks as data (policy targets, tariffs, mandates), applied to parameters | no model code |
| reporting and validation | tables, comparisons with CAPRI's results | reads results only |

**Data formats** (agreed 22 October 2026, docs/design/CAPTRD_MOD.md section 7; confirmed 24 October 2026 after
weighing Dolt, DVC + Frictionless and Apache Iceberg):
- The model's inputs stay CSV. The data adapters read CSV only.
- The data pipeline (raw → harmonised → coco → capreg → captrd) works on Delta Lake tables. Each stage can export
  to CSV, and the last stage writes the model's CSV inputs.
- The model never reads Delta tables.

CAPRI has the same separation in its files: data preparation (CAPREG, COCO, CAPTRD), calibration (cal_*.gms, pmp,
calibrate_supply), equations (supply_model.gms, arm/market_model.gms), scenarios (pol_input/), reports (reports/).

**Blocks** inside the equation layer, following CAPRI's equation blocks, each with a citation of the GAMS lines it
ports: supply (feed, fertiliser distribution, land, policy rules, abatement, PMP terms), market (Armington and
bilateral trade, food demand, processing and crushing, dairy, biofuels, feed demand, non-EU supply), environment.

The economic coupling stays as in CAPRI (the supply–market iteration, the shared prices; project rule: modules as
coupled as CAPRI's). Layering separates concerns, not the economics.

Reason beyond readability: CAPTRD-MOD and the data pipeline will produce other base years and other data. A data
adapter layer is the interface they need.

## 2. Rules for every stage

- Moves and behaviour changes never share a commit.
- A move must reproduce the reference run exactly: Farm-to-Fork 2030 with default settings (PYTHONHASHSEED = 0, so a
  run repeats exactly), compared result by result with the reference pickle, plus the test suite.
- Findings of the claim audit are fixed one at a time, each with its own full run, under the rule "follow CAPRI unless
  CAPRI's code is in error" (DEPARTURES_FROM_CAPRI.md).

## 3. Stages

| Stage | Content | Status |
|---|---|---|
| 1 | Market split by block: `capri_mod/market/` core (`market_module.py`) plus `calibration.py`, `biofuel.py`, `dairy.py`, `feed.py`, `demand.py`, `processing.py`, `supply.py`, `bilateral_solve.py`, `equilibrium.py`; the blocks are mixins of `MarketModule`, code unchanged | done 24 Oct: Farm-to-Fork 2030 run r111s identical to r111 within 1e-10 (tools/check/compare_pickles_exact.py) |
| 2a | Market data adapter: `capri_mod/market/inputs.py` (MarketInputs) is the only market code that reads files; it takes the model's data directory and base year (the blocks read a fixed capri_data/2017 path before); the eleven loaders that silently switched a block off on any error now stop the run; test `capri_mod/tests/test_market_layers.py` enforces the rule | done 24 Oct: run r111a identical to r111 within 1e-10 |
| 2b | Market calibration and state: the parameters each block builds once per base (now ~25 hand-written caches on the module) into a parameters object; the per-evaluation state (~20 attributes passed between supply_response, demand_response and the by-product blocks) into a state object. Blocks that the conformity programme rewrites (section 6) are written in this form directly; the others are moved mechanically with a gate | next |
| 3 | Supply (`supply_module.py`): the same two steps, block by block (feed, fertiliser, land, policy rules, abatement, PMP) | planned |
| 4 | Environment and `model.py` (the coupling loop) | planned |
| 5 | Scenario and reporting layers | planned |

## 4. CAPRI-claim audit

Each claim that the code follows CAPRI is classified against the GAMS source:
verified (GAMS lines cited), registered (a documented departure), unregistered difference, unsourced (a constant or
rule with no CAPRI or documented source), unverifiable (source not in hand). Done by a reviewer that did not write the
code. Market module first; results in section 5 when available.

## 5. Findings

### 5.1 Market module (audit of 24 October 2026; table: docs/design/audit/market_claims.csv)

75 claims or constants classified: 23 verified, 16 registered (4 of them only in module docs: ARMINGTON_MARKET.md,
DAIRY_PROCESSING.md, FEED_MARKETS.md), 15 unregistered differences (4 documentation-only), 17 unsourced (mostly
numerical guards; 3 dead code), 4 unverifiable. Line numbers refer to market_module.py before the split.

Unregistered differences that can change results, by likely size. "Checked" marks what was re-read in the code and
the GAMS after the audit; the rest is the auditor's reading, to be confirmed when each is fixed.

| # | Where | Difference | Checked |
|---|---|---|---|
| M1 | gl_food_ratio, ProcNQ_ part of demand_response, crushing margins | CAPRI moves consumer, processing and margin prices by Arm1P0 / PPRI0 x (ratio - 1) (market_model.gms Cpri_ l. 3032-3039, ProcNQ_ l. 1140-1152, ProcMargO_ l. 1118-1136); the code uses dom0 = FAO_agg base world price x (1 + AVE). Auditor: dom0 / Arm1P0 has a value-weighted median of 0.84, more than 25% off for 35% of use value (EU cheese 0.48, fresh milk products 0.35) | code path and Cpri_ checked; the ratios not yet |
| M2 | demand_response | EU-average FAO_agg own-price elasticities (fao_demand_own_elas_eu.json, no builder) replace eta in every region, including the non-EU p_ElasDem values of K24 (wheat -0.09 for -0.36) | checked |
| M3 | non-EU feed demand | constant elasticity in p_ElasFeed; CAPRI has FeedNQ_ with the energy balance FeedBal_ (l. 1018-1048), so non-EU feed use does not follow non-EU livestock output | not yet; decided 25 October 2026 (user): ported when the refactor reaches the market feed block, after the refactor of that block reproduces the frozen reference, as its own step with its own run. The Hessian is CAPRI's own p_hessNQFeed (elas_2_1730defaulta, in hand per section 6.2; else derived from p_elasFeed as arm/trim_elas.gms l. 1975-2135); p_calContent and pv_feedConv are not in the exports at hand: rebuilt from CAPRI's code (arm/feed_conv.gms) and CSV data, no proxy |
| M4 | eu_feed_use | EU feed bulk quantity fixed within a market solve; CAPRI's feedBlk_ responds (simu_calibration_to_supply.gms l. 264-275); same fixed point, different path | not yet |
| M5 | supply_response (dairy) | EU raw milk fixed within the market solve even with market_supply_nq; CAPRI's ProdNQ_ includes MILK; path only | **implemented 24 Oct** (market.milk_in_market): each member state's raw milk follows its own milk price inside the market (the measured Hessian per member state: own response, MILK's row on the products' and young animals' prices, MILK's column on theirs), cleared against its dairies in the dairy block (_dairy_solve_ms_resp) jointly with the young-animal markets (_milk_and_yani_clear); test_member_state_milk_responds_to_its_price_in_the_dairy_block; run pending |
| M6 | feed bulks, Norway | rho 6/6/5 where market1.gms l. 98 caps NO000000 at 2.0 (the builder's pattern misses the line) | **fixed 24 Oct**: feed_bulks_no.csv rebuilt (FCER, FPRO 6 -> 2, FENE 5 -> 2), run r117 |
| M7 | _compute_welfare | base consumer price = world price everywhere; values in EUR million labelled billion (also model.py welfare_EUR_billion_change); reporting only | label (welfare_EUR_million_change) and base domestic price fixed 24 Oct; CAPRI's money-metric welfare (reports/welfare.gms) not ported yet |
| M8 | crush_quantities | the 1%-of-base floor is called CAPRI's ProcFudge_, which is a smoothed max(0, x) (l. 1158-1163) | not yet |
| M9 | processing | dairy processing held fixed (CAPRI's ProcNQ_ has 37 dairy terms, about 530 kt); fixed oil and cake yields (CAPRI: CET with rho 0.01, negligible) | not yet |
| M10 | bilateral.py | a tariff change applied to the exporter price only, not to price + transport as impPrice_ (l. 2858-2882); model.py drops the region key, so all changes land on the EU rows | **fixed 24 Oct**: the change on price + transport cost of the importer's external flows (BilateralCommodity.tc, CAPRI's q-weighted TCost; tc column added to bilateral_flows_*.csv by build_bilateral_market.py, every other column identical), per importer region (the region key kept; EU, EU27 or an EU region map to the EU rows); test_tariff_change_applies_to_price_plus_transport_of_the_importer |
| M11 | raw milk outside the EU | a pooled world market (one world price, non-EU supply against non-EU use); CAPRI does not trade raw milk: it is cleared regionally by the dairies' demand (DairyNQ_) against ProdNQ_ supply | **fixed 24 Oct**: each region's dairy block clears its raw milk (run r115; the EU results are unchanged to 1e-10: the pooled raw-milk market fed nothing else), and the region's reported raw-milk price is its block's (from run r116) |

Documentation-only: the module header still described the removed constant-elasticity market (corrected 24 October);
the domestic_prices docstring mentions an exchange rate the code does not apply; OILSEED_CRUSHING.md l. 51 describes a
margin difference K54-4 fixed. Dead code: the DAIRY_DOMESTIC branch, excess_demand, bilateral.trq_target.

Verified (among others): the GL demand system and its refit (trim_gl_commits.gms); the biofuel block (all equations,
glycerine price 600, the CES calibration reproducing BiofFeedCost within 4e-8 in all 97 groups); the dairy block
(DairyNQ_, ProcMargM_, FatsProtBal_), RHO_FMIL 0.5; ProcNQ_ scaling by INPE; TRQ slope; the bilateral equations.

Order of the fixes: one at a time, each with a full run (section 2). Status 24 October: M1 and M8 done (run r112,
with the crushing CET yields); M2 done by the Armington balance (run r113: no generic elasticity is left); M11 done
(run r115); M6 data rebuilt (run r117); M3-M5, M7, M9, M10 open.

### 5.1b Supply module (audit of 24 October 2026; table: docs/design/audit/supply_claims.csv)

145 claims or constants: 48 verified (3 partly registered), 60 registered, 17 unregistered differences, 13 unsourced,
7 unverifiable. Not covered in depth: the conic form (feed_conic.py, capri_nlp.py), ammonia_techs.py's cascade algebra,
intensity.py, most builders, and fert/npk.py beyond the cap functions.

Unregistered differences, by likely effect (auditor's reading; "checked" = re-read in code and GAMS since):

| # | Where | Difference | Checked |
|---|---|---|---|
| S1 | supply_module.py _compute_net_revenues (feed costs) | with feeding inside the model, the animals' net revenue still gets the change of the cereal and protein bulk prices, while the NLP (capri_regional_nlp.py objective) also charges every feed at its current price; CAPRI costs feed once (QUADRF_) - a double count in every livestock scenario | code path checked: the branch is active (price_shock passed, use_feed_in_supply on) and the NLP prices feeds at the coordinator's current prices; size to be measured |
| S2 | mineral and organic caps merged by min() | CAPRI's minfert_redu_by_crop.gms resets groups below 30 kg N/ha and its listed pairs to 1.0-1.2 x baseline, overriding a lower organic cap; applies only where the mineral reduction is crop-specific (mineRedu "crp"), not in the JRC121368 Farm-to-Fork (no mineRedu) | checked |
| S3 | organic other-input cost | +100% other inputs on converted land (JRC121368) where star 3.0's organic_io('100','off','off','50') raises them by (fuel + services) x 2 x the target | **fixed 24 Oct** (see below) |
| S4 | pesticide other-input cost | INPO x r(1 - o) where conventional_io.gms gives INPO x (r - o) | **fixed 24 Oct** (see below) |
| S5 | fertiliser options' cost base and slope; inhibitor slope | base mineral rate x area where GHG_Mit_Cost_ uses purchases; slopes without the fertiliser-price / manure-value terms of ghgMiti.gms | fixed 24 Oct: NLP form: cost on the fertilisation block's N purchases (- cost x v_netPutQuant(NITF)), calibration on the base purchases; curvature CAPRI's pmpParSqr with the saving term nmE x p_NITF x ((1+nmE m1)^-2 - (1+nmE m0)^-2)/(m1-m0), nmE = NMIN + EmiCalmin (96 region-options non-positive, kept in the NLP form as CAPRI, left out of the conic form); supply.fert_slope_with_saving OFF by default: with the purchase-based cost it moved the baseline off its shares (K77). The manure inhibitor (N2OMAN, p_manureShadVal) not reviewed |
| S6 | crop N need x sqrt(yield/base) | CAPRI's sqrt acts on the technology yield factor; price-driven yields enter need linearly (endog_yields.gms, fertned.gms) | fixed 24 Oct: need_yield_factor (capri_mod/fert/npk.py) at every site (NLP block per nutrient, N row, mineral caps, accounts, inner distribution, P balance): main-output part linear, straw part with the scenario's shifts only, crops at fertned's floor/cap fixed; shares from CAPRI's 2030 dump (build_npk_balance_2030.py); setting fertiliser.need_yield_rule ("sqrt" = before) |
| S7 | yield response | revenue only; CAPRI re-runs define_inputs, fertned, define_objc | fixed 24 Oct: _apply_yield_input_costs (CAPRI's IY inputs: f_i x cost_i x G x TF_I x (rho - 1), PLAP/INPO at their Green Deal TF_I, G bounded 0.5-1.5) for the scenario's yield shifts and the price response; fertned through S6; setting supply.yield_dependent_inputs |
| S8 | permanent-grassland rule at calibration | zero multiplier where CAPRI sets -abs(arable rent - grassland rent) (prep_cal.gms l. 118-134) | fixed 24 Oct: the permGras row's multiplier fixed at abs(rent ARAC - rent GRAS) in CapriRegionalNLP.calibrate; setting supply.perm_gras_cal_dual |
| S9 | ecological set-aside row | no winter cover (CAPRI weight 0.3, calibrated to the gap) and ISET at weight 1 (CAPRI 0) | fixed 24 Oct: catch crops on the row at 0.3 where the NLP's winter cover option exists (base gap with CAPRI's 2030 share); ISET/GSET/TSET have no area in CAPRI's 2017 or 2030 data, so SETA = FALL + VSET at weight 1 is CAPRI's (no change needed) |
| S10 | landscape floor; diversification limit | the floor counts set-aside only (CAPRI also idled histosols); the diversification limit is not relaxed (landscape.gms l. 74-88) | fixed 24 Oct: idled histosol columns count on the landscape_floor row (setaFallow); cropDiv H0 = min(H0, CAPRI's formula with F added) under the floor. The floor's SETF = FALL + VSET = the model's SETA (checked in CAPRI's 2030 dump) |
| S11 | pesticide target | a 23-crop list where CAPRI applies it to every crop | plant protection and other inputs fixed 24 Oct (every activity); the yield loss keeps the list (jrc121368 rule only; star 3.0 runs it off) |
| S12 | emission tax on mineral N | IPCC factors where CAPRI uses its cascade losses | not yet |
| S13 | non-default PMP elasticity path | clip at 8, share term for some crops | not yet |

**S3/S4 fix (24 October 2026).** SupplyModule._apply_greendeal_input_changes applies CAPRI's form (organic_io.gms,
conventional_io.gms, define_inputs.gms l. 66-73): one regional change per input on the coefficient of every activity,
PLAP -o_R with the organic target alone and -r overall with the pesticide target (o_R < r), INPO +(r - o_R) on every
activity including the animals' other inputs, and the organic crops' top-up of other inputs by 2 x their crop target x
their fuel cost. Also: CAPRI's organic crop set and crop targets (load_organic_targets.gms; grassland, fodder, other
oilseeds and the minor crops are not organic crops; Portugal has no arable or permanent-crop target in CAPRI's data),
and the organic yield gap only on the grouped organic crops with a gap estimate. Found on the way: the other-input
cost per ha was CAPRI's bare coefficient without its unit value (about 20% low; builder fixed), and two CAPRI code
errors, both corrected by default with a parity switch (DEPARTURES_FROM_CAPRI): the compile-time
scenAugmentsTechChange off (the change replaces the 2017-2030 input-saving progress) and the top-up valued at INPO's
unit value instead of fuel's. Registered: the changes act on CAPRI's 2017 coefficients (CAPRI's simulation-year
coefficients also carry the yield-dependent input adjustment, not held); the fertiliser part of the organic target
keeps the model's own crop mapping (_organic_converted; CAPRI uses the NGRP groups, with the vegetables at the UAA
target and Portugal's missing entries at 0) - not changed here.

Unsourced: the inhibitor's maximum share (1 - grazing share), accepting IPOPT's "acceptable" solutions (tol 1e-6),
land rows at max(land data, base area), the PMP diagonal clamp, and fallbacks reached only when data are missing.
Docs that contradict the code: SUPPLY_MODEL_MAP 2.1 (PMP calibration) and its "same" for the landscape floor and the
sqrt-yield need.

### 5.2 What the split needs next (stage 2)

State passes between the blocks through about 15 instance attributes and hand-written caches (e.g. supply_response
writes the biofuel and dairy state that demand_response reads; model.py writes world_prices_base, _dom0_cache,
_feed_bulk_index, supply_hessian, trq_volume_changes and resets only two caches). Stage 2 therefore introduces, besides
the data adapter, an explicit per-evaluation state object, so the call order supply -> demand -> by-products is visible
in the code. The auditor's mapping to CAPRI's files: sets (arm_sets.gms), parameters (market1.gms), calibration
(cal_armington, calibrate_market_data, simu_calibration_to_supply, trim_gl_commits), solve (simu_market.gms),
reporting (process_solution.gms, store_prices.gms).

## 6. Market conformity programme (project lead, 24 October 2026)

Decision: every audited item that is not a verified port is brought to CAPRI's equations; registered departures
included. Numerical devices of the solver that do not change the equations (Anderson acceleration, damping, inner
Newton steps, finite-difference local elasticities) stay, because CAPRI's own solve uses a different solver (CONOPT);
they are documented as solver mechanics, made settings where they are not, and checked not to bind at the solution.
A guard that binds at a solution is a difference and is treated as one.

| Step | Items | Effect on results | Gate |
|---|---|---|---|
| A | documentation and dead code: module header, domestic_prices docstring, the processed-products comment, OILSEED_CRUSHING.md l. 51, excess_demand and bilateral.trq_target removed, the CAPRI_MARKET_AA environment switch removed (the setting market.acceleration decides); the DAIRY_DOMESTIC algebra kept (CAPRI's general block, an empty set in the data) with its docstring corrected | none | done 24 Oct, code; run identical to be confirmed with B |
| B | reporting as CAPRI's: welfare (reports/welfare.gms: money metric from the GL system, processing, dairy and agricultural profits), the world price (wldPrice_: production + Arm1 weights), the EU27 aggregate prices | reports only | run identical except the reports |
| C | data as CAPRI's: M2 (CAPRI's p_ElasDem per region instead of FAO EU averages), M6 (Norway's feed rho capped at 2.0, market1.gms l. 98), K72 (Armington table rebuilt from CAPRI: rho, eta, eps) | yes | one full run each |
| D | equations as CAPRI's: M1 (price changes on Arm1P0 / PPRI0), M3 (non-EU FeedNQ_ with FeedBal_), M4 (feedBlk_ inside the market), M5 and market_supply_nq (ProdNQ_ including MILK), non-EU supply in CAPRI's NQ form (K54-3), EU fish/OTHO NQ per member state, dairy processing in ProcNQ_, crushing CET and ProcFudge_, tariff changes on price + transport (impPrice_), TRQ changes per pair, the 0.98 export-share cap (S192) and the [0.2, 5] use factor (S185) | yes | one full run each |
| E | structure as CAPRI's: eu_blocks (two EU trade blocks), the Armington commitment terms p_arm2Commit | yes | one full run each |
| F | the unverifiable items: the BIOF_M default, Norway's milk (ProdNQ_ NOTE2), the baseline calibration claim, checked in the GAMS and either confirmed or changed | depends | as found |
| G | solver (26 October 2026: the user asked for it; G1 done - each commodity's trade system with CasADi's exact Jacobian, `market.exact_jacobian`, capri_mod/market/trade_ad.py, equal to the numeric residual to 1e-9 and its Jacobian to finite differences (test_trade_ad.py); on a 5-region Farm-to-Fork the market reaches the same prices (|log r| below 1e-4) except a 29-tonne market (Japan's sunflower cake) whose price is not determined within the tolerance, and takes the same number of rounds: the rounds come from the outer linearisation across commodities, which G2+ replaces): every square non-linear system of the market (bilateral trade per commodity, processing, dairy block, biofuel markets, feed bulks, young-animal markets, the market supply functions) solved by one joint Newton, on the whole system or on its linked blocks, with the exact sparse Jacobian from CasADi (CAPRI's full-system stage after its per-commodity and group stages); line search on the step, the current per-commodity Newton/Anderson kept as start and fallback. The TRQ regime stays CAPRI's sigmoid (trqSigmoidFunc_, p_trqSigmoidSlope 200), already smooth, so no complementarity solver (PATH) is needed; remaining guards (step clip, [0.2, 5] bounds) checked not to bind. Written block by block as each block takes the layered form (6.1) | none at convergence | the equilibrium of the per-commodity solve reproduced to 1e-7 on the 2030 baseline and the Farm-to-Fork scenario; then time and steps per solve measured |

Order: A and B first (no results effect), then C, D, E one item at a time; G with each block's layered rewrite. Decided 26 October 2026 (user): the refactor first; G2 onward (the joint Newton over all market blocks) inside the refactor's market stage, after the reference run is frozen. Each step is recorded in CHANGELOG and
the audit table's status column is updated.

### 6.0b The supply-market fixed point (tried and removed, 26 October 2026)

An Anderson (secant) update of the supply-market fixed point was tried at the user's request, as
`outer_loop.price_update = "anderson"`, beyond CAPRI. Run r143 (Farm-to-Fork, with the K75 fix): 12 iterations, as the
adaptive step (r139), against 9 with CAPRI's price averaging (r140), and a gap path that rose twice. It saved no
iterations once K75 (a model error, not the update) was fixed; removed at the user's decision ("if not useful remove
it"), code, settings and tests.

### 6.1 How the rewrites fit the layers

A block that section 6 rewrites (its equations change) is written directly in the layered form, in the same step:
its inputs through the data adapter, its parameters built in the calibration layer, its equations as functions of
parameters, prices and quantities. Its check is the full run against expectations (CAPRI's equations and results),
not bit-identity, since the results change on purpose. Blocks that stay as they are move mechanically, gated by an
identical run.

### 6.2 Data the rewrites need

| Rewrite | CAPRI data | In hand |
|---|---|---|
| Arm1 = HCON + FEED + PROC + BIOF (ArmBal1_); price changes on ARM1P / PPRI (M1) | Data_CAL items ARM1, HCON, FEED, PROC, BIOF, ARM1P, PPRI, CPRI per region (data_market_1730defaulta) | yes; ARM1P already added to gl_demand_goods.csv and processing_nq_hessian.csv (builders rerun, existing values unchanged) |
| non-EU supply and feed: ProdNQ_, FeedNQ_, FeedBal_ with the feed-energy price FEDE | p_hessNQSupp, p_hessNQFeed (elas_2_1730defaulta); pv_feedConv (feed energy per unit of animal output, estimated by arm/feed_conv.gms) and p_calContent (energy content per product) | Hessians yes; pv_feedConv and p_calContent not in the exports at hand: either port arm/feed_conv.gms (an estimation) or an export from CAPRI's market GDX |
| welfare (reports/welfare.gms) | p_pbGL, p_pdGL, the NQ Hessians and constants, INHA, INCE, land supply parameters | mostly yes; constants are recalibrated in CAPRI's run |
