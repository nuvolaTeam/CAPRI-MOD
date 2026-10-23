# Module coupling and commodity coverage

Status: revised 22 October 2026 against the code. The coupling table, the product table and the register describe the
code on that date. The review this document started as (October 2026: market prices not reaching livestock, feed
demand not linked to herds, no oilseed crushing) is historical; every gap it found has been closed, see "History"
below. The sprint-by-sprint record with intermediate results is docs/COUPLING_SPRINTS.md and CHANGELOG.md; current
results are in README section 9 (Validation).

Project rule: no fixed coefficients, proxy prices or post-solve modules unless CAPRI does the same.

## How the modules are coupled

A run is a fixed point of the outer loop between the regional supply models and the market (README 4, 7.4).

| From → to | What passes | Where it is solved |
|---|---|---|
| Supply → market | regional gross output, mapped to market commodities (`CAPRIModel._bridge_supply_to_market`; animal output by product with `livestock_output_by_product_coef.csv`: cull-cow beef to beef, sheep and goat milk to raw milk, hen meat to poultry), summed per trade region (the EU, or CAPRI's two EU blocks with `MarketModule.eu_blocks`) | outer loop |
| Market → supply | price ratio per commodity, damped per commodity (adaptive step from 0.5); animals through `SupplyModule.ACTIVITY_PRICE_SOURCE` and product by product (`livestock_product_value_by_market_coef.csv`); each region's member-state milk price from the dairy block | outer loop |
| Feed | rations chosen inside the regional models (CAPRI's requirement equalities, fodder balances); purchased feed priced by CAPRI's feed bulks per member state (FCER, FPRO, FENE, FOTH, FMIL; feedBlkPrice_ CES), the bulks' demand split into products in the market (feedShareEqu_) | regional model and market, outer loop |
| Young animals | calves, young cattle, replacement cows, piglets and lambs: outputs of some animal activities, inputs of others; prices cleared so that each market's net balance stays at its baseline (CAPRI's yaniMarket_; EU-wide or per EU block). Calves and young cattle pooled across the sexes; CAPRI's per-sex markets with its replacement heifers and calf activities as own levels are built but off (setting `supply.use_cattle_member_splits`; KNOWN_ISSUES K65: not converging yet; a DEPARTURE from CAPRI's setting, docs/DEPARTURES_FROM_CAPRI.md). The price update takes the supply response from the PMP terms; with the member splits, from each solved regional model (`CapriRegionalNLP.response`) | outer loop (`CAPRIModel._update_young_animal_prices`) |
| Manure | trade columns and CAPRI's crop-need row (NUTNED_) in every EU regional model; pools between regions cleared with CAPRI's manureTradeNew costs (Takayama-Judge, solved in its primal form) | regional model and outer loop; off in Farm-to-Fork as JRC121368 |
| Land | CAPRI's land market with land types as variables and no idle farmland (LandBalNoSlak_) | inside each regional model |
| Nitrogen target, mineral fertiliser caps | CAPRI's N-surplus row (e_SURTOTHa) and the inner fertiliser distribution model with its regulations | inside each regional model (constraints) |
| Mitigation options, emission tax | CAPRI's options as columns (ammonia options through the N loss cascade, AD, fertiliser techniques, breeding, low-N feed, supplements, cover crops, histosol fallowing); the tax on each column's emissions per unit at the baseline solution | inside each regional model |
| Biofuels | feedstock demand (CAPRI's Biof_ CES), biofuel supply, demand and bilateral trade (BIOF_M), DDGS | inside the market |
| Labour, set-aside | CAPRI's labour accounts (LABT, LABF, LABP per activity unit; GROF = sum of level x labour) and CAPRI's VSET / FALL inside the model's SETA, with their premiums and labour | after the solve, as CAPRI (labour is an indicator there, not a constraint of the supply model; `results["labour"]`, `results["set_aside"]`) |
| Processing, dairy | ProcNQ_ (crushing, other processing), CAPRI's dairy block per member state (nine products, fat and protein balances) | inside the market |
| Food demand | CAPRI's Generalised Leontief system per behavioural region | inside the market |
| Environment → supply | each activity's N balance coefficients, from the same functions as the accounts | inside each regional model |
| Supply → environment | activity levels, yields, feed, fertiliser allocation, option shares, manure trade | accounts after the loop |
| Land-use change | CAPRI's LUC model (gamma priors) | after each regional solve |
| Winter cover (NLP form) | the catch-crop share as an option: land (winterCover_), BioFix N to the residue pool and the N-surplus row, runoff in the loss cascade, N2OCRO under the tax (docs/WINTER_COVER.md) | inside each regional model |
| Phosphate balance | the NLP form's P purchases and manure flows; CAPRI's gross P balance (docs/P_BALANCE.md) | accounts after the loop |

Every coupling switch above is a key of capri_mod/settings/defaults.toml, read by every module from the one active
set of settings: the 2030 model the projection builds sees the same values as the outer model. Where a default differs
from CAPRI's, docs/DEPARTURES_FROM_CAPRI.md says so.

## Product concepts and their status

The model has 46 activities (34 crops, 12 animal activities), 58 market commodities and 30 trade regions
(`capri_mod/data/definitions.py`; Norway, NOR, its own since 21 October 2026, KNOWN_ISSUES K56).

| Concept | In the model as | Clears a market? |
|---|---|---|
| Cereals (wheat with durum, barley, maize, rye, oats, other cereals, rice as milled rice), oilseeds (rapeseed, sunflower, soya), sugar (from beet), potatoes, pulses, tomatoes, other vegetables, apples, other fruit, citrus, table grapes, tobacco, table olives, textile crops, wine, olive oil | activities mapped to CAPRI's market products | yes (bilateral) |
| Other oilseeds, other industrial crops, nursery, flowers, other crops (OOIL, OIND, NURS, FLOW, OCRO) | activities; OOIL, OIND (and OANI) fixed at their data level as CAPRI's FACT | no, as in CAPRI (`arm/arm_sets.gms` nonXX_CROPS) |
| Fodder (GRAS, MAIF, OFOD) | activities and feed, priced through the fodder balances | no, non-tradable as in CAPRI |
| Raw milk and nine dairy products | CAPRI's dairy block per member state: raw milk priced by fat and protein; butter, SMP, cheese, whey and the other products traded | dairy products yes; raw milk no bilateral trade (pooled, registered) |
| Beef, pork, poultry, sheep and goat meat, eggs | animal outputs by product | yes |
| Oils and cakes (rapeseed, sunflower, soya), palm oil, other vegetable oils | crushing in the market (ProcNQ_); palm and other oils by market supply functions | yes |
| Fish, aquaculture, coffee, tea, cocoa | market products | yes |
| Bio-ethanol, bio-diesel, DDGS; residual feeds FENI, FPRI | BIOF_M and MaprFeed_ | yes |
| Mineral fertiliser N, P2O5, K2O | purchases in the regional model at CAPRI's unit values | no (exogenous input price) |
| Manure | regional supply, traded between pools | pool market (manureTradeNew) |
| Land | land types per region | regional land market |

## Departures and registered simplifications in the coupling

What remains different from CAPRI (README 5.1; `docs/KNOWN_ISSUES.md`):

| Item | capri-mod | CAPRI |
|---|---|---|
| EU in the market | one region by default; two blocks as an option | member states inside two trade blocks |
| Market supply between iterations | CAPRI's market supply elasticities as given (recalibration at the baseline optional, `market_supply_nq`) | supply approximation recalibrated to the supply models |
| Supply-market iteration | damped, adaptive per commodity | price averaging (same fixed point) |
| Norway's prices in the iteration | its own relaxed price level; convergence on products above 5 kt, Norway out of the test from iteration 15 | CAPRI's price averaging; the same thresholds and iteration-15 rule (price_forecast.gms) |
| Tiered N target infeasible in CAPRI's form | JRC121368's EU-average cut (36%) in CAPRI's form, recorded (K57) | JRC121368: nine regions set at 36% up front |
| Market solve | Newton per commodity with cross effects, Anderson acceleration | CONOPT per commodity, groups, full system (same equilibrium: docs/MARKET_SOLVE_CHECK.md) |
| Manure pools | Takayama-Judge in its primal form (shipments), solved with Clarabel | CONOPT (same function) |
| Raw milk | no bilateral trade; world index from CAPRI's FAO_agg balance | dairy block per member state |
| Trade-policy detail | registered (Sprint 8m): global quotas, CAPRI's augmented-CES commitment terms | in the model |
| Emission tax | coefficients at the baseline solution (registered linearisation) | inside the supply model |
| Land-use change | solved after each regional solve (registered; identical without a LULUCF price) | LUC model |
| Livestock coefficients | CAPRI's 2017 totals over CAPRI's herd sizes (DATA2 HERD), not its activity levels | per-unit coefficients on CAPRI's units (totals match) |
| Purchased feed FENE, FMIL in projected years | price index 1 (no CAPRI unit value; registered) | feedBlkPrice_ |
| PMP terms at 2030 | CAPRI's own 2030 terms for crops, animals (herds and intensity splits), feed and land (default since 22 October 2026, `pmp_source = "capri2030"`; technologies collapsed per activity, group terms at full size); capri-mod's own terms by CAPRI's recipe with the land-nest adjustment (`"recipe"`); the elasticity calibration (`"elasticity"`) (K61, docs/PMP_CAPRI_2030.md) | p_pmpQuadTechn, p_pmpQuadPact, p_pmpQuadLandTypes, p_pmpFeedInpCoeff of its 2030 calibration |
| Ammonia options without a policy incentive on N | held at their base shares in the regional NLP (no N-surplus row, mineral cap or emission tax; re-solved so where the N-surplus row is slack), as the conic form leaves them out (K63) | in the model; costsavings0 makes the base a first-order point and CONOPT stays there |
| Member states' milk price step | adaptive step (K62: CAPRI's step weights tried, Spain's milk price kept swinging) | weighted average of the last prices (define_stepWeights.gms) |

Data items in the market files that no module reads: the `FATS` and `OFOD_M` rows of `world_prices.csv` and
`armington_params.csv` (both markets were removed: no supply, no use, invented totals). The files also carry `DWHE`
and `SUGB` rows, which are price-only rows (durum is traded within wheat; beet has no market, as in CAPRI).

## History

The review was written when the market cleared 33 commodities and several modules ran after the solve. Its findings,
and what closed them (details and effects: docs/COUPLING_SPRINTS.md, CHANGELOG.md):

1. **Market prices did not reach livestock**: the price signal was keyed by market commodity, farm margins by
   activity; closed with `ACTIVITY_PRICE_SOURCE` and product-by-product revenue.
2. **Feed demand not linked to herds**: closed with feeding inside the regional models (Sprint 4) and CAPRI's feed
   bulks per member state (Sprints 9d, 9h); the post-solve feed module was retired (Sprint 9i).
3. **No oilseed crushing**: oils and cakes are markets, crushing inside the market; the soybean-meal price proxy
   (0.89 × the bean price) was removed.
4. **Side modules outside the loop**: the post-solve feed, abatement (MACC, EcAMPA measures) and biofuel modules were
   retired; their functions are CAPRI's, inside the supply models or the market.
5. **Minor crops without a market**: rye and oats (first pooled into other cereals, own markets since 17-18 October
   2026), table grapes, tobacco, table olives, textile crops, palm and other vegetable oils are markets as in CAPRI.
6. **Fixed processing coefficients**: replaced by CAPRI's dairy block and ProcNQ_.
7. **Units across module boundaries**: per-head coefficients are CAPRI's totals over the model's heads; tests check
   quantities computed in two places (e.g. `test_livestock_output_by_product_sums_to_total`,
   `test_livestock_gross_output_is_marketed_product`).

Earlier states of the supply side (the conic form, the N-price search per region, the QP solver comparison) are
described in docs/NLP_PORT_DESIGN.md and docs/archive/.
