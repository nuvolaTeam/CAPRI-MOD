# capri-mod compared with CAPRI — modules and coupling

*October 2026. Every statement about capri-mod is read from its code; every
statement about CAPRI is read from CAPRI's GAMS code (star 3.0) or from CAPRI's
own data and results supplied by the project lead. Where something was found by
searching rather than by a full review, the text says so.*

## Summary

capri-mod reproduces CAPRI's **core loop** — regional PMP supply models iterating
with a global market model — and, after the work of the last weeks, the links
inside that loop are mostly two-way and mostly use CAPRI's own parameters. The
coupling is weakest exactly where CAPRI puts behaviour **inside** its supply models
or **inside** its market model and capri-mod still uses a fixed coefficient or a
module that runs after the solve: the EU feed ration, manure trade, mitigation
technologies, dairy processing and biofuels. Herd linkages between animal
activities and a full bilateral Armington market are the two structural
differences outside that list.

A fair one-line verdict: **the crop–market–nitrogen–oilseed system is coupled as in
CAPRI; the livestock–feed–processing system is coupled in direction but not yet
in mechanism.** The Farm-to-Fork validation shows the same split: crops, oilseed
prices, pigs, manure methane and milk prices match CAPRI; beef, poultry and meat
prices do not.

## 1. Modules side by side

| CAPRI component | Role in CAPRI | capri-mod counterpart | Status |
|---|---|---|---|
| COCO / CAPREG | consistent national and regional database | data taken directly from CAPRI's outputs (`res_17*`, `FAO_agg`, `res_0_1717`); `reconcile_base.py`, `rebase.py` as standalone tools | **uses CAPRI's data**, does not rebuild it |
| CAPTRD | baseline projection | `projection/` (recursive time loop, trajectories, `captrd_import.py`); passes the null-trajectory identity test | **partial** — trajectory imported, not estimated |
| CAPMOD supply models | regional (and farm-type) PMP models: crops, animals, land, feed, fertiliser, emissions, mitigation, policy | `supply/supply_module.py` (248 NUTS-2 QPs), `capri_pmp.py`, `intensity.py`, `qp_solver.py` | **core equivalent at NUTS-2**; no farm types; feed ration, mitigation and herd linkages missing (§3) |
| CAPMOD market model | spatial multi-commodity model, two-stage Armington, processing (dairy, oilseeds, biofuels), non-EU feed demand, tariffs and TRQs | `market/market_module.py` (39 commodities, 21 trade regions) | **partial** — oilseed crushing and non-EU feed demand as CAPRI; dairy and biofuels not; simplified Armington (§3) |
| Nutrient balances and fertiliser allocation (inside supply) | crop need, manure, mineral fertiliser with minimum shares, manure trade | `environmental/environmental_module.py` (stages 1–2 of `docs/FERTILISER_ALLOCATION.md`) | **partial** — manure trade at fixed base shares; mineral N linearised around base |
| GHG and ammonia accounting | emissions per activity and region | `environmental/environmental_module.py` | **equivalent in structure**; ammonia mitigation incomplete |
| Mitigation technologies ("endotech", inside supply) | adoption chosen with production | `abatement/capri_mitigation.py`, `technological.py`, `abatement_module.py` | **post-solve** — adoption does not change production |
| Feed (inside supply for the EU; market functions outside) | ration choice under nutrient requirements; non-EU feed elasticities | `feed/feed_module.py` (post-solve, off by default), feed coefficients in supply, non-EU feed demand in the market | **partial** — EU ration fixed per head; designed in `docs/FEED_RATION.md` |
| Biofuels (inside the market) | biofuel supply and feedstock demand | `biofuel/biofuel_module.py` | **post-solve, off by default** |
| Policy | CAP premiums, coupled support, Green Deal targets, trade policy | `policy/policy_module.py`, `greendeal.py`, `scenarios/` | **largely equivalent for CAP**; EU tariffs set to CAPRI's total protection |
| CAPDIS | spatial disaggregation to the 1 km grid | — | **missing** |
| CGE link | economy-wide feedback | — | **missing** (a documented limit) |
| Indicators | income, welfare, environment | `income/` (standalone), market welfare, `water/` (standalone) | **post-processing** |

The fertiliser module `fert/fert_module.py` is not called anywhere in a run;
fertiliser allocation lives in the environmental module.

## 2. How CAPRI couples its parts, and how capri-mod does

**CAPRI.** The regional supply models are solved at given prices; each one
optimises crops, animals, the feed ration, fertiliser use and mitigation
**simultaneously**, under land, nutrient-requirement, nutrient-balance and policy
constraints. The market model is solved with the supply side approximated by
behavioural functions, and contains processing (dairy, crushing, biofuels) and
non-EU feed demand. The two are iterated to convergence.

**capri-mod.** The same outer loop — supply models at given prices, market at
given supply, a damped price signal back — converging in 7 iterations for
Farm-to-Fork 2030. Inside the loop:

- **Supply ↔ market, two-way.** Farm outputs reach the market through a bridge;
  market prices reach every activity through an activity-to-market price map
  (until recently meat, milk and egg prices reached no animal at all).
- **Inside each regional supply model:** crops and animals with PMP calibrated
  on CAPRI's market revenue per head; the land market; the nitrogen-balance
  constraint, using the environmental module's own coefficients; organic farming;
  the nitrogen intensity margin; CAP premiums; feed costs from cereal and cake
  prices.
- **Inside the market:** 39 commodities; oilseed crushing in 44 region–seed
  pairs, linking seed, oil and cake markets both ways; EU cereal and cake feed
  demand following herds; non-EU feed demand responding to feed prices with
  CAPRI's elasticities, own and cross.
- **After the solve:** emissions accounting (consistent with the constraint used
  inside the solve), mitigation adoption, and — switched off by default — the
  feed and biofuel modules. Income and water indicators are standalone.

## 3. Coupling scorecard

| Link | CAPRI | capri-mod | Rating |
|---|---|---|---|
| Market prices → farm margins | all activities | all activities, via the activity price map | **equivalent** |
| Farm supply → market | all products | crops, meat, milk, eggs; oils and cakes via crushing | **equivalent** |
| Land competition | land supply and market in supply models | regional land market inside the supply model | **equivalent in mechanism** (Germany's land rent is a flagged fallback) |
| Nitrogen balance ↔ production | constraint and allocation inside supply | constraint inside supply on CAPRI's balance; allocation linearised | **largely equivalent** |
| Manure → crops (fertiliser substitution) | endogenous, with minimum mineral shares | as CAPRI, linearised around base | **equivalent at the margin** |
| Manure trade between regions | endogenous, with a cost | fixed base shares | **missing** |
| Herds → feed demand (EU) | ration × herds | herds × fixed ration per head | **partial** (direction right, no substitution) |
| Herds ↔ fodder ↔ land (fodder balance) | regional fodder use = regional fodder production (non-tradable) | **none** — only a grassland area limit; found while building the ration | **missing** |
| Feed prices → EU ration | ration chosen in supply models | none | **missing** — designed |
| Feed prices → non-EU feed demand | `p_ElasFeed` | `p_ElasFeed`, own and cross | **equivalent** |
| Feed prices → livestock costs | through the ration | cereal mix and cake index on fixed rations | **partial** |
| Seed ↔ oil ↔ cake prices (crushing) | margin-driven crushing | as CAPRI, CAPRI's elasticities | **equivalent** |
| Milk ↔ dairy products | processing with fat and protein balance | fixed FAO split | **missing** |
| Oils, cereals, sugar ↔ biofuels | biofuel functions in the market | post-solve module, off | **missing** |
| Mitigation ↔ production | adoption inside supply | post-solve | **missing** |
| Calves ↔ heifers ↔ cows (herd linkages) | young-animal and replacement balances | none found in the supply module (searched, not fully reviewed) | **missing** |
| Trade between regions | bilateral two-stage Armington, tariffs, TRQs | world price with tariff wedges, an EU Armington premium, CAPRI's trade matrix and Armington parameters | **partial** |

## 4. What the validation says about the coupling

Farm-to-Fork 2030 against CAPRI (JRC121368), current model:

| | capri-mod | CAPRI |
|---|---|---|
| Cereal / oilseed / vegetables-and-permanent price | +11.6 / +10.7 / +8.1% | +8 / +11 / +15% |
| Beef / pork / poultry / milk price | +2.2 / +6.5 / +3.8 / +1.7% | +24 / +43 / +18 / +1.5% |
| Dairy cows / beef animals / pigs / poultry / sheep | −7.4 / −9.8 / −14.3 / −7.4 / −4.1% | −10 / −18 / −14.5 / −16.5 / −9.5% |
| Cereal / oilseed / vegetables-and-permanent production | −13.9 / −18.1 / −13.4% | −15 / −15.5 / −12% |
| Nitrogen surplus / fertiliser N₂O | −40.2 / −35.6% | −33.5 / −40.4% |
| Enteric / manure methane | −9.8 / −11.2% | −14.6 / −12.2% |
| Ammonia / non-CO₂ GHG | −12.0 / −10.4% | −33.0 / −14.8% |

Read against the scorecard: where the links are equivalent — crops, nitrogen,
oilseeds, pigs, milk — results are close. Where they are missing, results
diverge in the direction the missing link predicts: **meat prices** rise far less
than in CAPRI (simplified Armington and tariff wedges, no dairy processing, and
EU tariffs that differ from CAPRI's applied rates); **beef and poultry herds** fall
about half as much (no herd linkages, fixed rations); **ammonia** falls a third as
much (mitigation after the solve, ammonia measures incomplete).

## 5. Coupling defects found and fixed recently

The current state follows a series of coupling repairs, each found by comparing
with CAPRI rather than by internal checks: market prices did not reach livestock;
feed demand ignored herd sizes; manure and feed per head used CAPRI's per-unit
values on census herds; livestock price responses were damped by inflated revenue;
the world prices held cake prices under the oilseeds; the trade matrix
double-counted EU trade and dropped eleven trading regions; the market carried
state between runs. Details are in `CHANGELOG.md` and the data sourcing registry.

## 6. Remaining gaps, in order of effect

1. **EU ration choice** (designed, data verified) — feed substitution, feed costs,
   and cereal and cake prices.
2. **Herd linkages** between animal activities — beef and dairy responses.
3. **Market structure for meat and dairy** — bilateral Armington and TRQs, CAPRI's
   applied tariffs, and dairy processing; the meat price gap is the largest
   single divergence.
4. **Mitigation inside the supply model** — ammonia, enteric methane, and the
   ration (CAPRI's requirements respond to mitigation options).
5. **Biofuels in the market** (oilseed crushing Stage 4).
6. **Endogenous manure trade.**
7. CAPDIS and the CGE link — outside the current scope.
