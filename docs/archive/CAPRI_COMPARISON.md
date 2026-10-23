# capri-mod compared with CAPRI — modules and coupling

*October 2026 (sections 3, 4, 6 and the summary updated 17 October 2026). Every statement about capri-mod is read from its code; every
statement about CAPRI is read from CAPRI's GAMS code (star 3.0) or from CAPRI's
own data and results supplied by the project lead. Where something was found by
searching rather than by a full review, the text says so.*

## Current state (17 October 2026)

Since this comparison was written, the gaps it lists have largely been closed, each with CAPRI's own equations and
parameters: the EU feed ration is endogenous inside the regional models; the fodder balance is CAPRI's equality;
CAPRI's land market and land rules are on; CAPRI's ammonia, fertiliser and manure-inhibitor technologies are decided
inside the regional models (one convex conic program per region, checked against CAPRI's original non-convex form
with IPOPT: docs/archive/NLP_CHECK.md); CAPRI's inner fertiliser distribution model is on and, as in star 3.0, its minimum
mineral share (NUTMIN_) is then off (19 October 2026, K40: it enters CAPRI's model only without the inner model);
young-animal markets (yaniMarket_) are on; the market is CAPRI's bilateral Armington model (29 trade regions,
transport costs, tariffs, TRQs) with CAPRI's dairy block per member state, oilseed crushing, endogenous biofuel
markets and non-EU feed demand; an endogenous manure market is an option (off by default).

Remaining structural differences: the EU trades as one region (CAPRI's market resolves the member states); no farm
types, CAPDIS or CGE link; the database and the 2030 baseline are CAPRI's, imported, not rebuilt (no CoCo, CAPREG,
CAPTRD); CAPRI's market supply elasticities are used as given rather than measured from our regional models; the
market is solved by Newton per commodity with Anderson acceleration instead of CAPRI's group and full-system stages
(same equilibrium, docs/MARKET_SOLVE_CHECK.md). Open issues and their status: docs/KNOWN_ISSUES.md.

| 2030 Farm-to-Fork (JRC121368 targets), % change from baseline | capri-mod | CAPRI |
|---|---|---|
| Cereal / oilseed / vegetables-and-permanent-crops price | +7.1 / +14.6 / +12.4 | +8 / +11 / +15 |
| Beef / pork / poultry / milk price (EU producer prices) | +17.6 / +35.0 / +24.3 / +35.5 | +24 / +43 / +18 / +1.5 |
| Dairy cows / beef animals / pigs / poultry / sheep and goats | -8.2 / -18.1 / -21.2 / -19.4 / -12.9 | -10 / -18 / -14.5 / -16.5 / -9.5 |
| Cereal / oilseed / vegetables-and-permanent-crops production | -14.5 / -13.7 / -13.2 | -15 / -15.5 / -12 |
| Beef production | -15.4 | -14 |
| Nitrogen surplus / fertiliser N2O | -33.0 / -38.3 | -33.5 / -40.4 |
| Enteric / manure CH4 / GHG total | -15.3 / -15.6 / -19.6 | -14.6 / -12.2 / -14.8 |
| Ammonia | -42.7 | -33 |

Default model, full EU, converged in 12 iterations, about 10 minutes on 2 cores alongside the Green Deal run (18 October 2026: rye, oats, table grapes, tobacco, table olives, textile crops, palm and other vegetable oils as markets; CAPRI's cereal demand elasticities; sheep and goats split into CAPRI's SHGM and SHGF with the lamb balance; CAPRI's activity bounds; CAPRI's supply elasticities reaching every region, K30 and K32; the fodder balances exact at the baseline, K36). Green Deal (star 3.0 settings): mean absolute difference 20.0 points, 29 iterations. (19 October 2026, after K39-K48: Farm-to-Fork mean absolute difference 4.38 points over 20 indicators, 11 iterations; see CHANGELOG.) (19 October 2026, K38: that run used the end-point targets in 2030 with JRC121368's pesticide yield loss, and the difference is measured against the Farm-to-Fork table, not a Green Deal result; with CAPRI's 2030 settings pork price +6.2%, milk +10.9%, EU N surplus -27.9%, no CAPRI result to compare.) Mean absolute difference from CAPRI
over these 22 indicators: 4.6 points. The largest single gap, the milk price, is diagnosed in KNOWN_ISSUES K13: the
dairy block and market carry CAPRI's own parameters and give a derived demand for raw milk of about -0.2, with which
JRC121368's -10% milk at +1.5% price cannot be reproduced; it needs CAPRI's Farm-to-Fork dairy market results.

The summary and sections 1, 3, 4 and 6 below are up to date (17 October 2026); section 5 is a record of past fixes.

## Summary

*Rewritten 17 October 2026; the original summary described the model before the ration, mitigation, dairy,
biofuel and manure-market links were moved inside, as CAPRI has them.*

capri-mod reproduces CAPRI's core loop (regional supply models iterating with a global market model), and the links
inside that loop now use CAPRI's own equations and parameters: feeding, fodder, fertiliser and mitigation decisions
inside the regional models; dairy processing, crushing, biofuels and non-EU feed demand inside the market. The
structural differences left are on the market side (the EU as one trade region; CAPRI's market supply elasticities
used as given instead of recalibrated each iteration; own-price demand elasticities instead of CAPRI's full demand
system) and in coverage (no farm types, CAPDIS or CGE link; a few market products still missing). Matching links
do not by themselves give CAPRI's results: the remaining result gaps (section 4) are not yet located.

## 1. Modules side by side

*Updated 16 October 2026 from the code; this table supersedes the original one. "How to match" says what closing
the remaining difference would take; "matched" means CAPRI's equations and parameters are in place.*

| CAPRI component | CAPRI behaviour | capri-mod behaviour | How to match |
|---|---|---|---|
| CoCo / CAPREG (database) | builds a consistent national and regional database (activities, yields, input coefficients, prices) from Eurostat and other statistics | imports CAPRI's own database (2017 vintage: `res_17*`, `FAO_agg`, CAPREG coefficients) as CSV files, every input traced to its source | port CoCo / CAPREG, or import a newer CAPRI release (base-year update, Phase 2) |
| CAPTRD (baseline) | projects the baseline with trend estimation under expert and outlook constraints | adopts CAPRI's 2030 reference (levels, yields, prices); the projection loop reproduces it (correlation about 0.99) and was checked against the EU agricultural outlook | port CAPTRD's estimation; needed only for baselines CAPRI has not produced |
| Regional supply models | one non-convex NLP per region (and farm type): PMP, land, feeding, fertiliser, mitigation options, policy; solved as an NLP (CONOPT in practice; the simulation's solver option is left to the run default) | 248 NUTS-2 regions (EU27 + Norway; no UK, Western Balkans, Turkey, no farm types), each one convex conic program with the same blocks and CAPRI's parameters (Clarabel). Exact by algebra: feeding (total-feed form), inhibitor on manure. Departures: the ammonia loss cascade is linearised at the previous solve; fertiliser technology shares per crop instead of one regional share per technology (same optimum in the 5 regions tested); N2, N2O and NOx not subtracted in the cascade. IPOPT completes the solves Clarabel leaves unfinished. At the converged solution it equals CAPRI's exact NLP within 1.5e-4 of the objective (docs/archive/NLP_CHECK.md) | farm types need CAPRI's farm-type data; the exact cascade needs IPOPT on CAPRI's original NLP (switchable solver, future work) |
| Land | land supply and CAPRI's land rules inside the supply models | CAPRI's land market and land rules inside the regional models | matched |
| Feed | ration chosen inside the supply models under nutrient requirements; fodder not tradable (regional balance) | endogenous rations inside the regional models, CAPRI's fodder equality, feed bulk prices per member state | matched |
| Fertiliser and nutrient balance | need per crop group (NUTNED_), manure and residues spread by the inner fertiliser distribution model (star 3.0 default), its first-order conditions part of the supply model; the minimum mineral share per group (NUTMIN_) only without the inner model (supply_model_e_list_linear.gms; prep_sim.gms aborts on the combination); manure spread is v_ManureNPK (after housing and storage losses and trade) | one regional crop-need row (mineral N >= 0; CAPRI's minimum mineral share as an option, `use_min_mineral_share`, on by itself only without the inner model, K40); CAPRI's inner model checked at every solution and, where its allocation does not exist, the region solved in CAPRI's coupled non-convex form with IPOPT; priors fixed at the starting areas, flows bounded as CAPRI (prep_sim.gms); manure spread as CAPRI's v_ManureNPK (K21) | per-group need rows and per-group floor corrections (CAPRI's exact form; needs the coupled form in every region) |
| Manure trade between regions | endogenous manure market (manureTradeNew), a scenario setting | the same setting: CAPRI's manure market (Clarabel, Takayama-Judge dual) where the scenario trades manure (CAPRI star 3.0 settings), none in the Farm-to-Fork run as in JRC121368's CAPRI | matched; the fertiliser priors come from a star 3.0 run with manure trade: where a run without it falls outside them (RO22), they are recalibrated at the run's own base as CAPRI does (fert/ferttrm_years.gms) |
| Mitigation technologies (endotech) | adoption decided with production inside the supply models | inside the regional models with CAPRI's parameters: ammonia, fertiliser and manure-inhibitor options in the conic program; breeding, low-N feed, feed additives, low-intensity dairy, bull and heifer activities, catch crops, histosol fallowing | matched in mechanism; adoption of nitrification inhibitors and precision farming below CAPRI's (JRC121368 Table 17), not yet traced |
| GHG and ammonia accounting | emissions per activity and region with CAPRI's coefficients | CAPRI's coefficients: enteric CH4 from the feed, manure CH4, the N2O and NH3 cascades, mineral fertiliser N2O | matched in structure; Farm-to-Fork ammonia -42.6% against CAPRI's -33% open |
| Market model | spatial bilateral two-stage Armington model with transport costs, tariffs and TRQs; EU member states resolved; processing (dairy, oilseed crushing, biofuels); solved with CONOPT per commodity, in groups and as a full system | CAPRI's bilateral Armington market with 29 trade regions, transport costs, tariffs, TRQs, CAPRI's dairy block per member state, oilseed crushing, endogenous biofuel markets, non-EU feed demand; the EU trades as one region by default, or as CAPRI's two trade blocks with the member states inside (option `eu_blocks`; CAPRI has no trade between member states, only between the blocks); Newton per commodity with Anderson acceleration (same equilibrium) | young animals clear per block since 19 October 2026 (yaniMarket_); whether the blocks become the default is still to decide |
| Young animals | young-animal markets and replacement balances (yaniMarket_) | on, as CAPRI | matched |
| Supply-market iteration | market supply functions recalibrated to the regional models' responses; price averaging between iterations | adaptive relaxation; CAPRI's market supply elasticities used as given | measure the elasticities from our regional models each iteration (CAPRI's recalibration step) |
| Policy | CAP premiums and coupled support, Green Deal targets, trade policy, carbon tax | CAPRI's premiums (PRME), Green Deal switchboard with CAPRI's settings (CAPRI's 2030 settings as `greendeal_2030_scenario`; star 3.0's pesticide rule, no yield loss, for the Green Deal group, JRC121368's 10% at a 50% cut for Farm-to-Fork; K38), EU tariffs at CAPRI's total protection, CAPRI's ghgTax inside the regional models | matched for the instruments modelled |
| CAPDIS | spatial disaggregation to the 1 km grid | none | port CAPDIS (needs CAPRI's grid data) |
| CGE link | economy-wide feedback | none | link to a CGE model (outside the current scope) |
| Indicators | income, welfare, environment | farm income and market welfare in every run; nitrogen, GHG, ammonia and biodiversity indicators; water (`water/`) and detailed income (`income/`) run standalone | wire the standalone modules into the run |

The older fertiliser module `fert/fert_module.py` is not called in a run; CAPRI's inner fertiliser distribution
model is `fert/inner_fert_dist.py`, used by the regional models and the environmental report.

## 2. How CAPRI couples its parts, and how capri-mod does

**CAPRI.** The regional supply models are solved at given prices; each one
optimises crops, animals, the feed ration, fertiliser use and mitigation
**simultaneously**, under land, nutrient-requirement, nutrient-balance and policy
constraints. The market model is solved with the supply side approximated by
behavioural functions, and contains processing (dairy, crushing, biofuels) and
non-EU feed demand. The two are iterated to convergence.

**capri-mod.** The same outer loop — supply models at given prices, market at
given supply, a relaxed price signal back — converging in 12-14 iterations for
Farm-to-Fork 2030. Inside the loop:

- **Supply ↔ market, two-way.** Farm outputs reach the market through a bridge;
  market prices reach every activity through an activity-to-market price map
  (until recently meat, milk and egg prices reached no animal at all).
- **Inside each regional supply model:** crops and animals with PMP calibrated
  on CAPRI's market revenue per head; the land market and land rules; the feed ration under CAPRI's requirements at
  member-state feed bulk prices, with the fodder balance; the nitrogen balance with CAPRI's inner fertiliser
  distribution model (its minimum mineral share off, as star 3.0 with the inner model); mitigation technologies; organic farming; CAP premiums.
- **Inside the market:** 52 market commodities (rye and oats separate, table grapes, tobacco, table olives, textile crops, palm oil and other vegetable oils, as CAPRI); oilseed crushing in 44 region–seed
  pairs, linking seed, oil and cake markets both ways; EU cereal and cake feed
  demand following herds and rations; non-EU feed demand responding to feed prices with
  CAPRI's elasticities, own and cross; CAPRI's dairy block per member state; endogenous biofuel markets;
  young-animal markets.
- **After the solve:** emissions accounting with CAPRI's coefficients, consistent with the decisions taken inside
  the solve (mitigation adoption, rations and fertiliser use are decided inside the regional models; biofuels are in
  the market). Income and water indicators are standalone.

## 3. Coupling scorecard

*Updated 17 October 2026 from the code and the current runs (it had not been updated since the gaps were closed).
"Matched" means CAPRI's equations and parameters are in place for that link; it does not mean the results equal
CAPRI's (section 4).*

| Link | CAPRI | capri-mod | Rating |
|---|---|---|---|
| Market prices → farm margins | every activity earns its market product's price | every activity, via the activity-to-market price map; rye and oats their own markets (October 2026); animals through the value of their products per market | **matched** |
| Farm supply → market | all products | crops, meat, milk, eggs; oils and cakes via crushing; young animals via their markets. Every crop with a CAPRI market product now reaches it; the crops without one are those CAPRI has none for either (other oilseeds, other industrial, nurseries, flowers, other marketable crops: arm/arm_sets.gms nonXX_CROPS; fodder and set-aside). Table grapes and tobacco have markets since 17 October 2026, table olives (split from olives for oil) and textile crops (one activity TEXT, as CAPRI) since 18 October 2026 | **matched for the products modelled** |
| Land competition | land supply and land rules in the supply models | CAPRI's land market and land rules inside the regional models | **matched** (Germany's land rent is a flagged fallback) |
| Nitrogen balance ↔ production | need per crop group, inner fertiliser distribution model coupled to the supply model (the minimum mineral share only without it) | one regional crop-need row; CAPRI's inner model checked at every solution, the coupled non-convex form solved with IPOPT where its allocation does not exist | **matched in mechanism**; per-group need rows differ (KNOWN_ISSUES K20, 0.02%) |
| Manure → crops (fertiliser substitution) | endogenous, manure spread after housing and storage losses and trade | as CAPRI (v_ManureNPK, K21) | **matched** |
| Manure trade between regions | endogenous manure market, a scenario setting | CAPRI's manure market where the scenario trades manure (Green Deal), none in Farm-to-Fork as in JRC121368 | **matched** |
| Herds → feed demand (EU) | ration × herds, ration chosen in the supply models | ration chosen inside the regional models; member-state feed bulks follow herds and rations | **matched** |
| Herds ↔ fodder ↔ land | regional fodder balance (fodder not tradable) | CAPRI's fodder equality inside the regional models | **matched** |
| Feed prices → EU ration | ration responds to feed bulk prices | rations at CAPRI's feed bulk prices per member state (feedBlkPrice_, CES rho 6) | **matched** |
| Feed prices → non-EU feed demand | p_ElasFeed | p_ElasFeed, own and cross | **matched** |
| Seed ↔ oil ↔ cake prices (crushing) | margin-driven crushing | as CAPRI, CAPRI's elasticities | **matched** |
| Milk ↔ dairy products | dairy block: processing with fat and protein balance per member state | CAPRI's dairy block per member state (on by default) | **matched**; Farm-to-Fork milk price +33% against CAPRI's +1.5% open (K13) |
| Oils, cereals, sugar ↔ biofuels | endogenous biofuel markets (BIOF_M) | endogenous biofuel markets in the market (on by default, as star 3.0) | **matched** |
| Mitigation ↔ production | adoption decided with production inside the supply models | inside the regional models with CAPRI's parameters (ammonia, fertiliser and inhibitor options, breeding, feeding options, catch crops, histosols) | **matched in mechanism**; adoption of inhibitors and precision farming below CAPRI's, not yet traced |
| Calves ↔ heifers ↔ cows; ewes ↔ lambs ↔ fattening | young-animal markets and replacement balances (yaniMarket_), lambs included | on, as CAPRI; lambs since the sheep and goat split (October 2026) | **matched** |
| Trade between regions | bilateral two-stage Armington, transport costs, tariffs, TRQs; EU member states resolved | CAPRI's bilateral Armington market, 29 trade regions, CAPRI's flows, Armington parameters, tariffs and TRQs; the EU trades as one region | **partial**: the member states are not resolved in the market |
| Market supply side ↔ regional models | market supply functions recalibrated to the regional models' responses each iteration | CAPRI's market supply elasticities used as given; prices passed back with adaptive relaxation | **partial** |
| Demand | calibrated Generalised Leontief demand, own and cross p_ElasDem | human consumption: CAPRI's GL per behavioural region (26 EU member states, non-EU countries and groups; p_pdGL, p_pbGL, CAL point of elas_2_1730defaulta), consumer prices moving additively with the domestic price (Cpri_), elasticities equal to p_ElasDem at the calibration point; applied to CAPRI's HCON share of each region's use as a ratio to the base; feed, crushing, biofuel parts with their own CAPRI functions; processing, industrial use and losses own-price elasticities as before | **mostly**: food as CAPRI; commitments not re-fitted to the model's base; processing without cross terms |
| Activity ranges | every endogenous activity bounded at 0.1 to max(10 x, + 100) its data level (set_supply_bounds.gms) | the same bounds (October 2026, K27) | **matched** |
| Herd dynamics between years | comparative static per simulation year (RECDYN off and not implemented) | comparative static per simulation year; only perennial areas carried along the baseline path | **matched** |

## 4. What the validation says about the coupling

Current results are in "Current state" above (Farm-to-Fork, 22 indicators, mean absolute difference from CAPRI about
4.6 points). Read against the scorecard: the links are now mostly CAPRI's, so the remaining gaps are not explained by
missing links. The largest are the milk price (+36% against +1.5%; K13: with CAPRI's own dairy parameters the
derived demand for raw milk is about -0.2, which cannot reproduce JRC121368's -10% milk at +1.5% price), the
poultry price and herds (+26% and -20% against +18% and -16.5%), pigs (-22% against -14.5%) and ammonia
(-43% against -33%). Locating them needs CAPRI's Farm-to-Fork results per product and region, which are not at
hand; the published report gives aggregates only.

## 5. Coupling defects found and fixed recently

The current state follows a series of coupling repairs, each found by comparing
with CAPRI rather than by internal checks: market prices did not reach livestock;
feed demand ignored herd sizes; manure and feed per head used CAPRI's per-unit
values on census herds; livestock price responses were damped by inflated revenue;
the world prices held cake prices under the oilseeds; the trade matrix
double-counted EU trade and dropped eleven trading regions; the market carried
state between runs. Details are in `CHANGELOG.md` and the data sourcing registry.

## 6. Remaining gaps

*Updated 17 October 2026; the earlier list (EU ration, herd linkages, meat and dairy market structure, mitigation
inside supply, biofuels, manure trade) has been closed, see section 3.*

1. **EU member states in the market**: CAPRI's two EU trade blocks (EU_WEST, EU_EAST) with their West-East trade and the member states inside, as an option since 18 October 2026 (`eu_blocks`; Farm-to-Fork gap 4.22 -> 4.65); by default the EU trades as one region. Remaining: young animals per block, retiring the legacy world base.
2. **Market supply recalibration** to the regional models' responses: available since 18 October 2026 as an option
   (`market_supply_nq`, off by default: no speed gain on Farm-to-Fork, results within the outer loop's tolerance);
   by default capri-mod uses CAPRI's market supply elasticities as given. Affects the convergence path, not the
   equilibrium.
3. **Market products**: every product CAPRI trades bilaterally (its reporting aggregates aside) is a market in capri-mod since 18 October 2026 (fish FFIS, SFIS, OAQU and coffee, tea, cocoa the last; EU fish supply from CAPRI's market supply functions).
4. **Demand system**: closed (18 October 2026): CAPRI's GL food demand per behavioural region with the commitments re-fitted to the model's base, and CAPRI's processing functions (ProcNQ_: crushing with cross terms among the oilseeds' margins, processing with cross terms among the vegetable oils).
5. **Farm types, CAPDIS and the CGE link**: outside the current scope.
