# Module coupling and commodity coverage

Status: revised 29 October 2026 against the code. The coupling table, the product table and the register describe the
code on that date. The review this document started as (October 2026: market prices not reaching livestock, feed
demand not linked to herds, no oilseed crushing) is historical; every gap it found has been closed, see "History"
below. The sprint-by-sprint record with intermediate results is docs/COUPLING_SPRINTS.md and CHANGELOG.md; current
results are in README section 8 (Validation).

Project rule: no fixed coefficients, proxy prices or post-solve modules unless CAPRI does the same.

## How the modules are coupled

A run is a fixed point of the outer loop between the regional supply models and the market (README 5.1).

| From → to | What passes | Where it is solved |
|---|---|---|
| Supply → market | regional gross output of CAPRI's 221 regional units (EU27 215, Norway 6; `capri_data/shared/regional_units.csv`, since 27 October 2026), mapped to market commodities (`CAPRIModel._bridge_supply_to_market`; animal output by product with `livestock_output_by_product_coef.csv`: cull-cow beef to beef, sheep and goat milk to raw milk, hen meat to poultry), summed per trade region (the EU, or CAPRI's two EU blocks with `MarketModule.eu_blocks`) | outer loop |
| Supply → market supply functions | CAPRI's ProdNQ_ for the supply models' products (`market.market_supply_nq = true`): p_hessNQSupp measured by 1% price shocks on the regional models (supply/calibrate_supply.gms; `CAPRIModel._market_supply_hessian`), per member state, with young-animal rows and columns; once per baseline, from the state the baseline left when the scenario on it starts, cached on disk; shifted through the supply models' latest output at the prices they saw in every market evaluation (arm/simu_calibration_to_supply.gms) | inside the market |
| Market → supply | price ratio per commodity as CAPRI's price forecast (`outer_loop.price_update = "capri"`, the default since 26 October 2026): the weighted average of the market's prices of the last steps, 0.55 / 0.30 / 0.15, from the 20th iteration 0.4 / 0.3 / 0.2 / 0.1 (capmod/define_stepWeights.gms, price_forecast.gms; `CAPRIModel._capri_forecast`), for the EU signal, the EU blocks, Norway's prices, each member state's milk price and the young animals; CAPRI's slower smoothing of listed products (`outer_loop.capri_step_special`, empty by default as in CAPRI's Green Deal runs); the adaptive step per commodity stays as the option `"adaptive"`. Animals through `SupplyModule.ACTIVITY_PRICE_SOURCE` and product by product (`livestock_product_value_by_market_coef.csv`); each region's member-state milk price from the dairy block | outer loop; it stops by CAPRI's rule (`outer_loop.stop_rule = "capri"`, the default since 28 October 2026; `capri_mod/utils/capri_stop.py`: no more than two items changing by more than 0.05% between iterations) with the model's inner balances settled, at most 60 iterations (`outer_loop.max_outer_iter`) |
| Feed | rations chosen inside the regional models (CAPRI's requirement equalities, fodder balances); purchased feed priced by CAPRI's feed bulks per member state (FCER, FPRO, FENE, FOTH, FMIL; feedBlkPrice_ CES), the bulks' demand split into products in the market (feedShareEqu_) | regional model and market, outer loop |
| Young animals | calves, young cattle, replacement cows, piglets and lambs: outputs of some animal activities, inputs of others; prices cleared so that each market's net balance stays at its baseline (CAPRI's yaniMarket_; EU-wide or per EU block). With CAPRI's market supply functions and one EU market they clear inside the market with the products, through the Hessian's young-animal rows and columns (`MarketModule._yani_clear`; `CAPRIModel._yani_in_market_now`); with the EU blocks, by a price update between market solves (`CAPRIModel._update_young_animal_prices`: the supply response from the PMP terms; with the member splits, from each solved regional model, `CapriRegionalNLP.response`). Calves and young cattle pooled across the sexes; CAPRI's per-sex markets with its replacement heifers and calf activities as own levels are built but off (setting `supply.use_cattle_member_splits`; KNOWN_ISSUES K65: not converging yet; a DEPARTURE from CAPRI's setting, docs/DEPARTURES_FROM_CAPRI.md) | inside the market; between market solves with the EU blocks |
| Manure | trade columns and CAPRI's crop-need row (NUTNED_) in every EU regional model; pools between regions cleared with CAPRI's manureTradeNew costs (Takayama-Judge, solved in its primal form) | regional model and outer loop; off in Farm-to-Fork as JRC121368 |
| Land | CAPRI's land market with land types as variables and no idle farmland (LandBalNoSlak_) | inside each regional model |
| Nitrogen target, mineral fertiliser caps | CAPRI's N-surplus row (e_SURTOTHa) and the inner fertiliser distribution model with its regulations | inside each regional model (constraints) |
| Mitigation options, emission tax | CAPRI's options as columns (ammonia options through the N loss cascade, AD, fertiliser techniques, breeding, low-N feed, supplements, cover crops, histosol fallowing); the tax on each column's emissions per unit at the baseline solution | inside each regional model |
| Biofuels | feedstock demand (CAPRI's Biof_ CES), biofuel supply, demand and bilateral trade (BIOF_M), DDGS | inside the market |
| Labour, set-aside | CAPRI's labour accounts (LABT, LABF, LABP per activity unit; GROF = sum of level x labour) and CAPRI's VSET / FALL inside the model's SETA, with their premiums and labour | after the solve, as CAPRI (labour is an indicator there, not a constraint of the supply model; `results["labour"]`, `results["set_aside"]`) |
| Processing, dairy | ProcNQ_ (crushing, other processing, and the processing of the dairy products per member state, its change entering FatsProtBal_: audit M9, `MarketModule._dairy_proc_change`); CAPRI's dairy block per member state (nine products, fat and protein balances); with one EU market each member state's raw milk supply follows its own milk price inside the market (ProdNQ_ MILK through the Hessian's member-state terms, audit M5, `MarketModule._milk_and_yani_clear`) and is cleared against its dairies (DairyNQ_); the non-EU regions with a dairy block clear their raw milk inside the block (audit M11) | inside the market |
| Food demand | CAPRI's Generalised Leontief system per behavioural region | inside the market |
| Environment → supply | each activity's N balance coefficients, from the same functions as the accounts | inside each regional model |
| Supply → environment | activity levels, yields, feed, fertiliser allocation, option shares, manure trade | accounts after the loop |
| Land-use change | CAPRI's LUC model (gamma priors) | after each regional solve |
| Winter cover (NLP form) | the catch-crop share as an option: land (winterCover_), BioFix N to the residue pool and the N-surplus row, runoff in the loss cascade, N2OCRO under the tax (docs/WINTER_COVER.md) | inside each regional model |
| Phosphate balance | the NLP form's P purchases and manure flows; CAPRI's gross P balance (docs/P_BALANCE.md) | accounts after the loop |
| Welfare | CAPRI's welfare report as levels (reports/welfare.gms; `capri_mod/market/welfare.py`, docs/WELFARE.md): the market's components per market region at its solution; for the regions with supply models their MGVA, land rents and the premiums' budget cost (`results["welfare_supply"]`) | report: after the market solve and after the loop |
| Supply → water, income | the irrigation water requirement (`capri_mod/water`) and farm income in CAPRI's ProfitAgr form (`capri_mod/income`) from the solved regional units | reports outside the run (the income parts also feed `results["welfare_supply"]`) |
| Results → NUTS 2024 | unit results mapped to the NUTS-2024 regions (`capri_mod/nuts_reporting.to_nuts2024`, `capri_data/shared/capri_units_nuts2024.csv`) | reporting only |

Every coupling switch above is a key of capri_mod/settings/defaults.toml, read by every module from the one active
set of settings: the 2030 model the projection builds sees the same values as the outer model. Where a default differs
from CAPRI's, docs/DEPARTURES_FROM_CAPRI.md says so.

## Product concepts and their status

The model has 46 activities (34 in the crop list, fodder and set-aside included, and 12 animal activities), 58 market
commodities and 26 trade regions (27 with CAPRI's two EU blocks), counted from the lists `CROPS`, `ANIMALS`,
`MARKET_COMMODITIES` and `TRADE_REGIONS` of `capri_mod/data/definitions.py`; 57 of the 58 commodities have CAPRI's
bilateral flows in the market data (`capri_data/2017/market/bilateral_flows_2017.csv`), raw milk has none. Norway
(NOR) is its own trade region since 21 October 2026 (KNOWN_ISSUES K56).

| Concept | In the model as | Clears a market? |
|---|---|---|
| Cereals (wheat with durum, barley, maize, rye, oats, other cereals, rice as milled rice), oilseeds (rapeseed, sunflower, soya), sugar (from beet), potatoes, pulses, tomatoes, other vegetables, apples, other fruit, citrus, table grapes, tobacco, table olives, textile crops, wine, olive oil | activities mapped to CAPRI's market products | yes (bilateral) |
| Other oilseeds, other industrial crops, nursery, flowers, other crops (OOIL, OIND, NURS, FLOW, OCRO) | activities fixed at their data level as CAPRI's FACT, with other animals OANI (`supply_module.FIXED_ACTIVITIES`; supply/prep_sim.gms l. 250) | no, as in CAPRI (`arm/arm_sets.gms` nonXX_CROPS) |
| Fodder (GRAS, MAIF, OFOD) | activities and feed, priced through the fodder balances | no, non-tradable as in CAPRI |
| Raw milk and nine dairy products | CAPRI's dairy block per member state: raw milk priced by fat and protein; butter, SMP, cheese, whey and the other products traded; their processing by ProcNQ_ (M9); each member state's raw milk supply responding to its milk price inside the market (M5, one EU market) | dairy products yes; raw milk not traded, as in CAPRI: cleared per member state in the dairy block, and per region in the non-EU regions with a dairy block (M11); other regions' raw milk at base |
| Beef, pork, poultry, sheep and goat meat, eggs | animal outputs by product | yes |
| Oils and cakes (rapeseed, sunflower, soya), palm oil, other vegetable oils | crushing in the market (ProcNQ_); palm and other oils without a supply-model activity: the EU's other vegetable oils by CAPRI's ProdNQ_ per member state (p_hessNQSupp in price ratios, `eu_market_supply_nq.csv`, tools/build/build_eu_market_supply_nq.py; since 28-29 October 2026), non-EU supply by CAPRI's own-price p_elasSupp per region | yes |
| Fish, aquaculture, coffee, tea, cocoa | market products without a supply-model activity; the EU's fish products (FFIS, SFIS, OAQU) by CAPRI's ProdNQ_ per member state (as other vegetable oils), non-EU supply by CAPRI's own-price p_elasSupp per region | yes |
| Bio-ethanol, bio-diesel, DDGS; residual feeds FENI, FPRI | BIOF_M and MaprFeed_ | yes |
| Mineral fertiliser N, P2O5, K2O | purchases in the regional model at CAPRI's unit values | no (exogenous input price) |
| Manure | regional supply, traded between pools | pool market (manureTradeNew) |
| Land | land types per region | regional land market |

## Departures and registered simplifications in the coupling

What remains different from CAPRI (README §10; docs/DEPARTURES_FROM_CAPRI.md; `docs/KNOWN_ISSUES.md`):

| Item | capri-mod | CAPRI |
|---|---|---|
| EU in the market | one region by default; two blocks as an option (`market.eu_blocks`) | member states inside two trade blocks |
| Market supply functions with the EU blocks | the Hessian is split per block, but the young-animal markets are updated between market solves and the member states' raw milk does not respond inside the market | ProdNQ_ and yaniMarket_ per market region inside the market model |
| Non-EU supply | own-price constant elasticity with CAPRI's p_elasSupp per region, none where CAPRI has none (`MarketModule._region_supply_elas`; registered, KNOWN_ISSUES K54-3) | ProdNQ_ with own- and cross-price terms |
| Non-EU feed demand | constant elasticities p_ElasFeed (`capri_mod/market/feed.py`); audit M3, to be ported | FeedNQ_ with FeedBal_ |
| Young animals by sex | pooled across the sexes; the cattle member splits off (`supply.use_cattle_member_splits`, K65) | per-sex markets, replacement heifers and calf activities with own levels |
| Supply-market iteration | CAPRI's price forecast and stop rule; the stop also waits for the model's inner balances (N-balance price, manure pools, young-animal balance, baseline calibration); at most 60 iterations; when the loop ends, a report of the items still moving one way (`outer_loop.drift_report_steps`, beyond CAPRI, decides nothing) | price forecast (define_stepWeights.gms) and stop rule (price_forecast.gms); 99 steps in its GUI |
| Regional solves between iterations | IPOPT from the previous solution; where a warm result is more than 1% worse than the last iteration's objective (`supply.nlp_warm_check`, K75) or the levels move by more than 10% (`supply.nlp_jump_check`, K79), the other starts are solved too and the lowest objective kept (beyond CAPRI's practice) | CONOPT from the previous solution |
| Tiered N target infeasible in CAPRI's form | JRC121368's EU-average cut (36%) in CAPRI's form, recorded (K57) | JRC121368: nine regions set at 36% up front |
| Market solve | Newton per commodity with cross effects, Anderson acceleration | CONOPT per commodity, groups, full system (same equilibrium: docs/MARKET_SOLVE_CHECK.md) |
| Manure pools | Takayama-Judge in its primal form (shipments), solved with Clarabel | CONOPT (same function) |
| Trade-policy detail | registered (Sprint 8m): global quotas, CAPRI's augmented-CES commitment terms | in the model |
| Emission tax | coefficients at the baseline solution (registered linearisation) | inside the supply model |
| Land-use change | solved after each regional solve (registered; identical without a LULUCF price) | LUC model |
| Livestock coefficients | CAPRI's 2017 totals over CAPRI's herd sizes (DATA2 HERD), not its activity levels | per-unit coefficients on CAPRI's units (totals match) |
| Purchased feed FENE, FMIL in projected years | price index 1 (no CAPRI unit value; registered) | feedBlkPrice_ |
| PMP terms at 2030 | CAPRI's own 2030 terms for crops, animals (herds and intensity splits), feed and land (default since 22 October 2026, `pmp_source = "capri2030"`; technologies collapsed per activity, group terms at full size); capri-mod's own terms by CAPRI's recipe with the land-nest adjustment (`"recipe"`); an activity without a positive own PMP term is held at its level, as CAPRI (the elasticity calibration was removed on 28 October 2026, audit S13) (K61, docs/PMP_CAPRI_2030.md) | p_pmpQuadTechn, p_pmpQuadPact, p_pmpQuadLandTypes, p_pmpFeedInpCoeff of its 2030 calibration |
| Ammonia options without a policy incentive on N | held at their base shares in the regional NLP (no N-surplus row, mineral cap or emission tax; re-solved so where the N-surplus row is slack; `RegionalSupplyModel._amm_incentive`, K63) | in the model; costsavings0 makes the base a first-order point and CONOPT stays there |

Rows of the 22 October register that now follow CAPRI and were removed: the market supply between iterations
(CAPRI's market supply functions on by default since 24 October 2026), Norway's prices in the iteration (CAPRI's price
forecast on its own market prices, and CAPRI's stop rule with Norway out from the 15th step), raw milk (per member
state inside the market, M5, and per region in the non-EU dairy blocks, M11) and the member states' milk price step
(CAPRI's step weights with the price forecast; K62 superseded).

The `FATS` and `OFOD_M` rows of `world_prices.csv` (markets removed earlier: no supply, no use, invented totals) were
removed on 29 October 2026 when the file got its one builder (`tools/build/build_world_prices.py`). The file also
carries `DWHE` and `SUGB` rows, which are price-only rows (durum is traded within wheat; beet has no market, as in
CAPRI): the outer loop's price signal takes its index from the table and sets them from soft wheat and sugar.

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
