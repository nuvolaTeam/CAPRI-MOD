# Dairy processing: CAPRI's fat and protein block in the market

Status: revised 21 October 2026 against the code (Norway's block: K56). The block is on by default, as in CAPRI, where it is part of the
market model. The development stages (October 2026: Stages 1-4, Sprint 9f) and their run results are summarised in
"History" and recorded in CHANGELOG.md; current results are in README section 9 (Validation).

Always on (the switch `market.use_dairy_block` and the run option `--no-dairy-block` were removed on 27 October
2026). Without the block's data the dairy products are raw milk × CAPRI's member-state 2030 yields (output less
processing per tonne of raw milk, `dairy_processing.csv`, `model._dairy_yield`).

## CAPRI's block (`arm/market_model.gms`)

Per member state (RMS), nine products k (butter BUTT, skimmed milk powder SMIP, cheese CHES, fresh milk products
FRMI, cream CREM, concentrated milk COCM, whole milk powder WMIO, casein CASE, whey powder WHEP) and raw milk MILK at
dairy (cow milk COMI + sheep and goat milk SGMI, `sets.gms` PRCD MILK.(COMI,SGMI)):

| Equation | Content |
|---|---|
| `ProcMargM_` (l. 1089) | margin m_k = p_k − FATS_k p_fat − PROT_k p_prot (raw milk also nets the dairy-level tax CSEI) |
| `DairyNQ_` (l. 1069) | Q_k = c_k + Σ_j H_kj m_j / p_INPE: normalised quadratic, H = `p_hessNQDairy`, symmetric, the MILK row reversed (milk is the input) |
| `FatsProtBal_` (l. 1103) | Q_MILK FATS_MILK = Σ_k (Q_k − PROC_k) FATS_k, and the same for protein |

Raw milk is not traded with third countries nor between member states: each member state's dairies process its own
milk, and its price follows the fat and protein values of the products less processing margins (CAPRI documentation
5.4.5). All nine products are traded bilaterally with Armington, like any market product.

## The model's version

Data (`tools/build/build_dairy_processing.py`, CAPRI's 2030 Green Deal reference, EU member states; Norway, a market
region of its own since 21 October 2026 (KNOWN_ISSUES K56), is in the non-EU blocks below):
`dairy_processing.csv` (quantities, processing, fat and protein contents in %, prices, CSEI, INPE, p_fat, p_prot),
`dairy_hessian.csv` (2,162 entries; 2,262 with Norway before K56), `dairy_eu_balance.csv` (EU use by component, extra-EU net imports),
`dairy_eu_demand_elas.csv` (CAPRI's own and cross p_ElasDem among the nine products, member states weighted by food
use). Builder checks: the fat and protein balances close in every member state (< 0.01%); the Hessian reproduces
CAPRI's `p_ElasDair` own-price elasticities (largest difference 7e-5 over 79 checks).

EU block (`MarketModule.dairy_block`, `_dairy_solve_ms`), one per member state:

- unknowns: the member state's fat, protein and raw milk price ratios; the nine products are at their EU market
  prices (per trade block with `eu_blocks`);
- equations: the fat and protein balances, and dairies' milk demand (DairyNQ_ for MILK) = milk delivered by the
  member state's supply models; linear, solved exactly;
- output: Q = Q0 + G z per member state; the EU market supply of each product is Σ (Q − processing).

Each member state's milk price goes to its regions' supply models as the EU signal plus the member state's
departure, damped like every price signal (floor 0.02). The outer loop's convergence test covers the member states
with at least 1% of EU milk; the gap of the smaller ones is reported (`metadata["milk_small_ms_gap"]`). This was
added because Cyprus's milk price circled within a band under its binding N target (October 2026).

EU use of the nine products (`demand_response`):

- feed: CAPRI's FMIL bulk per member state (`feed_bulks_eu.csv`, CES 0.5, `arm/market1.gms` p_rhoFeed), following
  the calves' milk feed in the supply models; products without a bulk row (cream) follow the EU FMIL index
  (`_fmil_index`) with the same CES (`dairy_feed_factor`, `RHO_FMIL`);
- food: CAPRI's GL demand on CAPRI's human-consumption share of use (`food_demand_gl`, on by default); the rest of the
  food part with CAPRI's own and cross p_ElasDem among the nine products.

Non-EU blocks (`_dairy_world_params`, `tools/build/build_dairy_world_blocks.py`): CAPRI's block for the 54 non-EU CAPRI
market regions with a dairy Hessian, grouped into 25 model trade regions (`dairy_world_*.csv`; Norway, NO000000, is
trade region NOR). In each, raw milk comes from CAPRI's own supply function (`p_hessNQSupp` MILK), the block is
solved at the region's market prices of the nine products, and the region's supply of each product moves with the
block's relative change. Use: food as in the EU (GL share, p_ElasDem), feed with the FMIL CES at a fixed FMIL index
(the model has no non-EU herds). Norway, with supply models (CAPRI RMSSUP), differs as CAPRI's does: its raw milk is
the milk delivered by its supply models (`market_model.gms` ProdNQ_, note 2), its raw milk price goes to its supply
models (Norway's price signal, `model.py` `_sup_dev`), and its products fed follow its FMIL bulk
(`feed_bulks_no.csv`) and FMIL index from its herds.

Supply bridge (`tools/build/build_livestock_products.py`, `livestock_output_by_product_coef.csv`): each animal's output
is split into CAPRI's final products at the region's own composition: dairy cows into milk and cull-cow beef, sheep
and goats into meat and milk (raw milk), laying hens into eggs and poultry meat.

REGISTERED: on-farm use and losses of raw milk move with deliveries; the non-EU blocks' feed use has no herd link
(Norway's has).

## The block's pass-through to raw milk

From the block's own coefficients (`dairy_processing.csv`, Germany): a product's price is the value of its fat and
protein plus a processing margin (cheese: margin 3,273 of 6,247 EUR/t), while raw milk is almost entirely fat and
protein value (its margin is −61 of 429 EUR/t). Product price changes therefore reach the raw milk price amplified,
and dairies' milk demand at given product prices is inelastic: in the October 2026 checks a 10% cut in a member
state's milk raised its milk price by 17-33% at fixed product prices, and the market's derived demand for EU raw milk
was about −0.2 (KNOWN_ISSUES K13, `tools/check/milk_shock_check.py`).

This is why the Farm-to-Fork milk price differs from JRC121368's (README section 9 (Validation): +31.1% in run r48 against
CAPRI's +1.5%; JRC121368 Figure 7 reads about +1.2%). With star 3.0's coefficients a 10% fall in EU milk supply
cannot clear at +1.5%; JRC121368 was run with an older CAPRI whose dairy coefficients are not in the installation.
No bug was found in the block or the market; the gap is recorded as open in K13 (CAPRI's Farm-to-Fork dairy market
results would settle it). The model is not calibrated to the figure.

## History (October 2026)

- Stage 1: the block in the market, opt-in, one EU price ratio for fat, protein and raw milk; the four traded
  products (butter, SMP, cheese, whey) from the block. Found on the way: the reported EU price carried the Armington
  premium twice (fixed; CHANGELOG "Biofuels and dairy into the market").
- Stage 2: sheep and goat milk counted as raw milk instead of sheep meat; livestock output split by CAPRI final
  product.
- Stage 3: EU feed demand through FMIL and EU food demand with CAPRI's cross-price elasticities.
- Stage 4: CAPRI's block for the non-EU regions with CAPRI's raw milk supply functions (replacing a flat 0.2-0.3
  supply elasticity per product).
- Sprint 9f: on by default as star 3.0 runs it; all nine products traded bilaterally (they had cleared inside the
  block with fixed extra-EU trade); raw milk, fat and protein priced per member state. Against CAPRI's 2030 reference
  every dairy product's EU production and use was then within 3.6% (`tools/check/compare_baseline_capri.py`).
- 18 October 2026: CAPRI's GL food demand applies to the dairy products' human consumption.

The Farm-to-Fork results of each stage are in CHANGELOG.md; they are not current.
