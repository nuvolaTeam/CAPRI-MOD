# Dairy processing — CAPRI's fat and protein block in the market

Status (October 2026, Sprint 9f): **on by default, as in CAPRI** (the dairy block is part of CAPRI's market model,
not an option): all nine dairy products traded bilaterally, raw milk, fat and protein priced per member state
(see "Sprint 9f" at the end; `MarketModule.use_dairy_block = False` or `run_f2f_2030.py --no-dairy-block` for the
old fixed-yield products). Earlier: **Stage 1 built, opt-in** (`MarketModule.use_dairy_block = True`,
`run_f2f_2030.py --dairy-block`) — dairy products from CAPRI's dairy processing block inside the market,
raw milk priced by the fat and protein it carries. **Stage 2 done, default**: sheep and goat milk is raw
milk, livestock output split by CAPRI final product, world dairy-product balances from CAPRI's FAO_agg.
**Stage 4 done (October 2026)**: CAPRI's dairy block also for the non-EU regions, with CAPRI's raw milk
supply functions. **Stage 3 done, still opt-in**: EU feed use of the dairy products follows the calves' milk
feed (CAPRI's FMIL feed block, CES 0.5) and EU food use has CAPRI's own and cross-price elasticities among the
nine products; Farm-to-Fork raw milk is still +30% against CAPRI's +1.5% (see below).

Without the block (the default) the market's EU butter, SMP, cheese and whey supply is raw milk × CAPRI's own
member-state 2030 yields (output less processing per tonne of raw milk, `dairy_processing.csv`; cheese 0.068) since
October 2026, no longer FAO EU-average ratios.

## What it replaces

Dairy products were fixed ratios of milk (`model._bridge_supply_to_market`: butter = milk × 0.0116,
skimmed milk powder × 0.013, cheese × 0.0456), milk itself was dairy-cow output × 0.9575, and the raw
milk price came from a world raw-milk market with an EU Armington premium. Product prices therefore never
reached the milk price: under Farm-to-Fork butter rises 19% and cheese 27% while raw milk moves +3.6% on
its own market. Sheep and goat milk was counted as sheep MEAT (the animal's whole output
went to `SHGM`, 5.3 Mt against ~0.7 Mt of meat) and its value never moved with any price.

## CAPRI's block (`arm/market_model.gms`)

Per member state, nine products k — butter BUTT, skimmed milk powder SMIP, cheese CHES, fresh milk
products FRMI, cream CREM, concentrated milk COCM, whole milk powder WMIO, casein CASE, whey powder WHEP —
and raw milk MILK at dairy (= cow milk COMI + sheep and goat milk SGMI, `sets.gms` PRCD MILK.(COMI,SGMI)):

| Equation | Content |
|---|---|
| `ProcMargM_` | margin m_k = p_k − FATS_k × p_fat − PROT_k × p_prot (raw milk also nets the dairy-level tax CSEI) |
| `DairyNQ_` | Q_k = c_k + Σ_j H_kj m_j / p_INPE — normalised quadratic, H = `p_hessNQDairy` (CAL), symmetric, MILK row reversed (milk is the input), `arm/market1.gms`; in simulation CUR = CAL |
| `FatsProtBal_` | Q_MILK × FATS_MILK = Σ_k (Q_k − PROC_k) × FATS_k, and the same for protein |

Raw milk is not traded with third countries; its price follows the fat and protein values of the
products less processing margins (CAPRI documentation 5.4.5).

## The model's version

- **Data** (`tools/build_dairy_processing.py`, CAPRI 2030 Green Deal reference, member states):
  `market/dairy_processing.csv` (quantities, processing, fat and protein contents in %, prices, CSEI,
  INPE, p_fat, p_prot), `dairy_hessian.csv` (2,262 entries), `dairy_eu_balance.csv` (EU use by
  component, extra-EU net imports, HCOM-weighted own-price `p_ElasDem`). Checks in the builder: the
  fat and protein balances close in every member state (< 0.01%); the Hessian reproduces CAPRI's
  `p_ElasDair` own-price elasticities (max difference 7e-5 over 79 checks); EU net imports from the member
  states match CAPRI's extra-EU trade within 1–2%.
- **Block** (`MarketModule.dairy_block`): per member state CAPRI's three equations, linear in prices;
  unknowns are EU-wide RATIOS (applied to each member state's own 2030 level) of the fat, protein and raw
  milk prices and of the prices of the five products that clear inside the EU (FRMI, CREM, COCM, WMIO,
  CASE). Equations: the two balances, dairies' milk demand = milk delivered (moves with EU raw milk
  supply), and for the five: supply − fixed uses + fixed extra-EU net imports = food demand at CAPRI's
  own-price elasticity. Newton, residual < 1e-9.
- **Market coupling**: the EU supply of butter, skimmed milk powder, cheese and whey (the market's BUTR,
  SKIM, CHES, WHEY, which trade with the world through Armington) is the block's output at the EU price
  (wedge × premium); raw milk is all used in the EU (EU demand = EU supply in the world milk market) and
  its EU price is the block's — it reaches farms through the price signal as before.
- **Supply bridge** (`tools/build_livestock_products.py`, `livestock_output_by_product_coef.csv`): each
  animal's output split into CAPRI's final products at the region's own composition — dairy cows into
  milk and cull-cow beef (now in the beef market), sheep and goats into meat and milk (milk now raw
  milk), laying hens into eggs and poultry meat. `livestock_product_value_by_market_coef.csv` gains
  `SHGP.MILK`: sheep and goat milk revenue moves with the milk price.

REGISTERED simplifications: one EU fat, protein and raw milk price ratio (CAPRI: per member state, with
raw milk traded between them); the five EU-cleared products keep their extra-EU trade, feed and
industrial use at the 2030 reference and their food demand has no income or cross-price terms; on-farm
use and losses of raw milk move with deliveries.

## Found on the way: the EU price carried the premium twice

`MarketModule.solve` wrote wedge × premium into the EU row of the domestic prices for the demand
calculation and the reported EU price then multiplied by the premium again. The supply side was always
shown world × premium (once), so no supply result changes; the REPORTED EU price changes of every
commodity with an Armington premium (meats, eggs, dairy products) were inflated — under Farm-to-Fork
butter +32% reported against +18% paid. Fixed; `wedge_prices` is now the pure wedge.

## Farm-to-Fork 2030 (full EU, converged)

| | without the block (default) | with the block | CAPRI |
|---|---|---|---|
| Raw milk price | +3.6% | +34.2% | +1.5% |
| Butter / SMP / cheese / whey price | +19 / +15 / +27 / 0% | +16 / +17 / +11 / +19% | — |
| Butter / SMP / cheese / whey output | −13 / −12 / −12 / 0% | −9 / −15 / −6 / −6% | — |
| Dairy cows | −12.9% | −5.9% | −10% |
| Sheep and goats | −12.8% | −10.4% | −9.5% |
| Beef animals | −14.5% | −17.1% | −18% |
| Enteric CH4 | −15.8% | −13.7% | −14.6% |
| 20-indicator gap | **4.30** | 5.63 | |

Inside the block (with it): fat +24%, protein +28%, raw milk delivered −6.8%; fresh milk products +11%,
cream +10%, whole milk powder +17%, casein +22%.

**Why the milk price runs away.** In CAPRI's block a product's price is the value of its fat and protein
plus a processing margin that is about half the price (cheese: margin 3,273 of 6,247 EUR/t in DE), and raw
milk is almost entirely fat and protein value (its own margin is −61 EUR/t). So a product price change
reaches raw milk about 2.5-fold: products +11-19% give fat and protein +24-28% and milk +34%. With product
prices held at base, the block alone gives milk +14% for the −6.8% of milk delivered. CAPRI's +1.5% with
raw milk −10% (JRC121368 p. 41) therefore means CAPRI's EU dairy-product prices hardly moved, while the
model's rise 11-19%: the world price of skimmed milk powder +12% and whey +17% (the EU is 37% and 63% of
world output), with an EU premium of 2-10% on top. Two things CAPRI has and the model's dairy-product markets
do not: EU feed demand for whey and SMP that falls with pig and calf numbers (JRC121368: "the feed demand for
whey is decreasing more than its supply, leading to a small increase in exports" — EU dairy net trade +5%),
and EU food demand with cross-price effects (CAPRI's GL system). Until those are in (Stage 3) the block
stays opt-in. No CAPRI Farm-to-Fork market results for dairy products are in the data received, so the
product prices cannot be checked directly.

## Stage 3 (October 2026): dairy feed and food demand

- **Feed (CAPRI FMIL block).** In CAPRI the products fed (SMIP, WMIO, CASE, WHEP, BUTT, CREM, COCM, CHES, FRMI)
  form the feed block FMIL, used by calves (res_17: CAMF, CAFF, CAMR, CAFR), split into products by a CES with
  elasticity 0.5 (`arm/market1.gms` p_rhoFeed). The model: FMIL index = calves' milk feed now / base
  (`model._set_feed_demand`, from the rations inside the supply models), EU feed use of each product = CAPRI's
  2030 feed use x index x (CES price index / own price)^0.5, value shares at CAPRI's 2030 prices. Feed is 87% of
  EU whey use and 31% of skimmed milk powder use.
- **Food (CAPRI p_ElasDem).** EU food use of each product = base x prod_j price_j^e_kj over the nine products,
  own and cross elasticities from CAPRI's member-state p_ElasDem weighted by food use
  (`dairy_eu_demand_elas.csv`; cheese −0.35 own, +0.03 to fresh milk products; concentrated milk +0.16 to
  cheese). For the four traded products this replaces the own-price-only demand; the five EU-cleared ones use
  it inside the block (Newton with a numerical Jacobian, residual < 1e-9).

Farm-to-Fork 2030 with the block (and cattle genomics): FMIL −15%, whey use −21% against output −13% (EU whey
exports rise, as JRC121368 reports), product prices butter +16, SMP +11, cheese +9, whey +9%; raw milk +30%
(+34% before Stage 3), dairy cows −7.0% (CAPRI −10), milk-yield genomics adopted on 31% of cows (CAPRI 15%).
Gap 5.44 with the block, 4.36 without.

**What is left.** The product prices: CAPRI's +1.5% for raw milk requires dairy-product prices that barely
move (the block passes them on about 2.5-fold); the model's rise 9-16%, about half from world prices (the EU is
a large share of world butter, SMP and whey trade) and half from the EU premium. Without CAPRI's Farm-to-Fork
market results for dairy products (not in the data received) this cannot be checked further; the block stays
opt-in.

## Stage 4 (October 2026): the dairy block outside the EU

CAPRI solves its dairy block in every market region, and outside the EU raw milk comes from the market model's
own supply function (`p_hessNQSupp` MILK). The model's non-EU dairy products had a flat supply elasticity of
0.2-0.3 each (`armington_params` eps), against CAPRI's raw milk supply elasticities of 0.7-1.0 (USA 0.92, NZL
0.72, IND 0.86) and dairy own-price elasticities around 1.5. `tools/build_dairy_world_blocks.py` takes CAPRI's
data for the 53 non-EU market regions with a dairy Hessian (quantities, contents, prices, food and feed use,
trade, Hessians, raw milk supply slopes, demand elasticities) and maps them to the 24 model trade regions with
dairy (`dairy_world_*.csv`). In the market each region's block is solved at its domestic prices (raw milk
endogenous through CAPRI's supply function; the five non-traded products clear in the region with fixed
extra-regional trade) and the region's butter, SMP, cheese and whey move with the block's relative change.
With all four traded products 10% dearer, the blocks give butter +1 to +11%, SMP +5 to +29%, cheese +6 to +16%,
raw milk +0.2 to +5.6% (USA +5.6%): several times the old response.

Farm-to-Fork 2030 with the EU and world blocks (and genomics): world prices of SMP, cheese and whey rise 2.6-3.5%
(before 5-8%); EU producer prices: butter +17, SMP +6, cheese +8, whey +5%; raw milk +28% (+30% after Stage 3);
dairy cows −7.3%; gap 5.35 (4.36 without the blocks).

**Where the milk price comes from now.** EU raw milk delivered −6.8%. The five products that clear inside the
EU — fresh milk products alone use about half of the EU's milk — have inelastic food demand (−0.36) and fixed
extra-EU trade, so their prices must rise ~9-15% to give up milk solids; the fat price rises 27%, protein 17%,
and raw milk, almost entirely fat and protein value, follows. CAPRI's +1.5% (JRC121368 Figure 7, read from the
chart) with raw milk −10% is hard to reproduce with CAPRI's own block structure and elasticities, which is now
what the model uses. Two things to check before going further: the figure itself (its value for milk), and
CAPRI's Farm-to-Fork market results for dairy products if they can be exported.

## Sprint 9f (October 2026): CAPRI's dairy block as star 3.0 runs it - on by default

Rule since this sprint: a block CAPRI star 3.0 runs is on, and judged against its own CAPRI reference, not against
the Farm-to-Fork gap. Two registered departures from CAPRI's block are closed:

- **All nine products traded.** CAPRI trades every product of the block bilaterally with Armington (its 2030 market
  results carry flows, import prices and tariffs for fresh milk products, cream, concentrated milk, whole milk powder
  and casein as for butter or cheese). They were cleared inside the block with fixed extra-EU trade. Now FRMI, CREM,
  COCM, WMIO and CASE are market commodities (43 in all): CAPRI's bilateral flows 2017 and 2030
  (`tools/build_bilateral_market.py`; every existing flow unchanged), world prices FAO_agg World PMRK, world
  balances from FAO_agg (`tools/build_dairy_world_markets.py`), Armington elasticities from market1_ch.gms and
  CAPRI's own-price p_ElasDem weighted by food use (`tools/build_dairy_trade_params.py`, also for the four traded
  before: butter −0.28, SMP −0.29, cheese −0.32, whey −0.36). Demand of all nine follows CAPRI's own and cross
  p_ElasDem and the FMIL feed block in the EU and, now also, in every non-EU region with a dairy block.
- **Raw milk, fat and protein priced per member state.** CAPRI's FatsProtBal_, ProcMargM_ and DairyNQ_ are per RMS
  and raw milk is not traded: each member state's dairies process its own milk. The model had one EU price ratio
  for all three. Now each member state's block gives its own fat, protein and raw milk prices from its milk
  delivered (the supply models of its regions) at the EU product prices; the regional models get their member
  state's milk price (the EU signal plus the member state's departure, relaxed like every price signal). Less milk
  in one member state raises its own milk price only (Germany −10% milk: +19%; tested).

**Convergence.** The member-state milk prices are relaxed per member state (floor 0.02). Cyprus (0.2% of EU milk)
does not settle: under its binding N target its herd's response is discontinuous and its milk price circles in a
band (×2.1–2.3, milk delivered 0.33–0.52); the run's convergence test covers the member states with at least 1% of
EU milk, and Cyprus's remaining gap is reported (`metadata["milk_small_ms_gap"]`).

**Against CAPRI's own 2030 reference** (`tools/compare_baseline_capri.py`): every dairy product's EU production and
use within 3.6% (cheese −3.1/−3.6%, casein −1.7/−2.7%, the others within 2%); EU domestic-use median deviation
3.7 → 3.0% over 42 products; production 3.5 → 3.4%.

**Farm-to-Fork 2030 (s72, JRC121368 settings)**: raw milk +34% (EU average; member states from +8% in Bulgaria to
+71% in Portugal, Cyprus +128%), butter +24%, fresh milk products, cheese, whole milk powder, casein +10%, SMP and whey +8%; dairy
cows −7.8% (CAPRI −10), sheep and goats −12.2% (−9.5), beef animals −20.3% (−18), enteric CH4 −16.8% (−14.6); pork
+46%, poultry +31%. 20-indicator gap 3.77 → 5.15, of which the milk price alone is 1.6 points (+34% against
+1.5%). The other 19 indicators move toward CAPRI on balance (dairy cows, sheep, enteric and manure CH4, GHG) and away
on beef animals and the pork and poultry prices.

**Why the milk price stays high - open.** The block passes product prices to milk about 2-fold (raw milk is almost
all fat and protein value: the milk margin is −61 EUR/t in Germany of 429) and dairies' milk demand at given product
prices has an elasticity of about −0.5 (a 10% milk cut raises the member state's milk price 17-33%), both CAPRI's
own coefficients. CAPRI's +1.5% (JRC121368 Figure 7, read from the chart) with dairy cows −10% then needs EU milk
supply to fall far less than the herd: milk-yield genomics adopted on 15% of cows in CAPRI's run (Table 17) against
3.8% here. Checking that, and the figure itself, is the next dairy item; the block stays on.

**Figure 7 checked (page 46 rendered).** JRC121368's Figure 7 bar "Cow and buffalo milk" reads about +1.2%
(producer price, Farm-to-Fork, 2030) - the +1.2-1.5% used above stands; the report gives raw milk supply about −10%.
With star 3.0's block coefficients a 10% cut in EU milk raises the raw milk price by about 19% at fixed product
prices, so CAPRI's JRC-era dairy block cannot have had the same pass-through (that era's market model differs from
star 3.0's; its coefficients are not in the installation). The block stays as star 3.0 runs it; the milk price gap
is recorded as a difference between the CAPRI versions, not a model defect. Since then the herd's response is closer
(dairy cows −7.1%, s73) and milk yield genomics are adopted on 25% of cows (Table 17: 15%).
