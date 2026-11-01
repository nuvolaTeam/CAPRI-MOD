# G3: CAPRI's market model m_globMarket, equation by equation (1 November 2026)

The inventory section 3.1 of MARKET_IPOPT_DESIGN.md asks for before G3 is assembled in CAPRI's own form. Source: CAPRI's arm/market_model.gms (capri_sources/gams, docs/EXTERNAL_SOURCES.md): the equation lists of m_globMarket (l. 4243) and of m_bevFunctionsMarket (l. 4150) that it includes, each equation's definition (line given), its domain and the conditional blocks around it ($ifi/$iftheni with CAPRI's defaults from capmod/set_global_variables.gms). The counterpart in capri-mod is found by the equation's name cited in our code and by reading the blocks; 'to check' marks those not yet matched equation by equation. Corrected on 1 November 2026 after the independent review of step G (docs/design/G_REVIEW_2026-11-01.md, Q4).

123 equations listed in the model; 20 ported, 14 ported in another form, 3 departure, 15 to check, 59 not ported, 11 off by CAPRI's default switches, 1 replaced. The definitions use 111 distinct variables (v_*).

Status: **ported** the same equation; **ported, other form** the same relation written otherwise (a substitution, a ratio form); **departure** different from CAPRI's (registered or to be); **to check** a counterpart exists or may exist, not yet matched equation by equation; **not ported** no counterpart; **off** switched off by CAPRI's default settings (the switch named); **replaced** the formal objective.

## Findings for G3

- **Not ported, and on in CAPRI's default runs:** the market's land and yield block (supremaMrk on: land supply as a multinomial logit, yields responding to producer prices, land demand scaled to supply, land rents) for the market's behavioural regions; the land-use-change estimation (luc_market, on with the environmental reports); the intervention stocks, subsidised exports, flexible cereal levies and entry prices where CAPRI's 2030 data have them (to be checked in the data before deciding).

- **Positivity and bounds:** CAPRI keeps quantities positive by their lower bounds; its ncpcm 'fudge' equations (consFudge_, ProdFudge_, FeedFudge_, ProcFudge_, tradeFlowFudge_) act only where a lower bound is 0 or below, which in a default simulation happens only after widen_bounds has widened it (consFudge_ not even then: consumption is fixed near 0 instead). Our hard floors (fmax) are therefore capri-mod's, not CAPRI's, and G3 needs an explicit bound policy (review Q2): CAPRI re-solves with widened bounds and accepts a sum of infeasibilities up to 0.1 in the last iteration (simu_market.gms l. 95-145, 289-300).

- **Scaling:** every CAPRI equation is divided by its base value (e.g. ArmBal1_ by DATA(RM,'arm1',XXX) + 0.1): G3 takes CAPRI's scaling.

- **The Armington commitments** (p_arm2Commit, the augmented CES) remain a registered departure; with them would come tradeFlowFudge_ and the Hicks-neutral shift.


## What CAPRI's 2030 data activate (checked 1 November 2026)

The policy and land equations act only where their data are nonzero. Checked in CAPRI's 2030 market data
(data_market_1730defaulta.csv, the calibrated 'CAL' values the simulation's 'CUR' starts from) and in the 2030
market results (markmarket_greendeal_1730et_base_1717.txt, dataOut), against each equation's $-condition:

| Block | Condition (market_model.gms) | 2030 data | Active |
|---|---|---|---|
| Intervention buying, probability under the safety net | PADM > 0 and INTM > 0 (l. 3492, 3507) | PADM for the EU blocks' cereals (45 entries), INTM none in CAL (2 in BAS) | **no** |
| Intervention stocks, releases, stock change | PADM > 0 and STKS > 0 (l. 3605, 3617) | STKS none in CAL (2 in BAS) | **no** |
| Subsidised exports | FEOE_max > 0 and PADM > 0 (l. 3724) | FEOE_max none | **no** |
| Flexible cereal levies | MinBordP > 0 (l. 3236, 3258) | the EU blocks' cereals, 30 entries (e.g. 153.1 EUR/t) | **yes** (where the levy's variable is free) |
| Entry prices of fruit and vegetables | TriggerP > 0 (l. 3176, 3204) | the EU and the UK, 8 entries in CAL (16 in 2030) | **yes** |
| Global (erga omnes) TRQs | p_trqGlobl TrqNT > 0 (l. 3142, 3399, 3475) | quotas against 'World' for the EU (18 products, e.g. maize 2,778 kt, wheat 2,851 kt) and for China, Japan, the USA, Canada, Russia, India, Switzerland, Norway, Taiwan, New Zealand and the aggregates | **yes** |
| Bilateral TRQs outside the EU | trqSigmoidFunc_ per importer | TrqNT of 2030 for about 20 importers besides the EU blocks | **yes** |
| Market land and yields | Yield_, LandSupplyMNL_ where land levels and yields exist (l. 1737, 1795) | 45 behavioural regions with yields, land levels and ARTO | **yes** |

So, of the "not ported" blocks, the intervention and subsidised-export rules are inactive in the 2030 runs, while
the global and non-EU TRQs, the flexible cereal levies, the entry prices and the market's land and yield block act in
CAPRI's 2030 market and are to be ported (DEP-33, DEP-34 are active departures).

## Human consumption (GL)

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| GLDemandFS_ | (RMS) | 826 | ported, other form | market/demand_ad.py (G2c) | CAPRI's intermediate terms (F, G, G_i) are folded into one expression per good |
| GLDemandGS_ | (RMS) | 845 | ported, other form | market/demand_ad.py (G2c) | CAPRI's intermediate terms (F, G, G_i) are folded into one expression per good |
| GLDemandGis_ | (RMS,XXX) | 860 | ported, other form | market/demand_ad.py (G2c) | CAPRI's intermediate terms (F, G, G_i) are folded into one expression per good |
| XiS_ | (RMS,XXX) | 891 | ported, other form | market/demand_ad.py (G2c) | CAPRI's intermediate terms (F, G, G_i) are folded into one expression per good |
| consFudge_ | (RMS,XXX) | 905 | departure | none (demand_ad.py floors x >= 0 and p >= 0.05 p0) | dormant in CAPRI's default simulation: consumption keeps a positive lower bound (set_start_val.gms l. 173) and widen_bounds fixes it near 0 rather than freeing the twin variable (widen_bounds.gms l. 88-123); our floors are capri-mod's (DEP-38) |
| CPri_ | (RMS,XXX) | 3032 | ported, other form | market/demand.py gl_food_ratio | consumer price = Armington price + margin, written on the price ratio; valid with fixed margins |

## Market supply

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| ProdNQ_ | (RMS,XX1) | 1529 | ported | market/supply.py (EU through the measured Hessian; non-EU ProdNQ_) | G2b; in G3 written as ProdNQ_ itself (PSE/AREP terms of MILK, CRDO oil cost, feed-bulk prices, l. 1546-1572) |
| ProdFudge_ | (RMS,XX1) | 2420 | not ported | none | active only where widen_bounds has pushed a production lower bound to 0 or below (widen_bounds.gms l. 33-62); ours: max(q0 + dq, 0) (supply.py, DEP-39) |
| ProdA_ | (RM,XXX) | 2438 | ported | market/supply.py (sums per market region) | an aggregation |

## Land (supremaMrk off)

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| LandSupply_ | (RMS,xx1LAND) | 1661 | off | - | the alternative land block, used only with supremaMrk off |
| LandAgrFromXX_ | (RMS,luAgrMrk) | 1678 | off | - | the alternative land block, used only with supremaMrk off |
| LandAgrTmp_ | (RMS,xxUsingLand) | 1817 | off | - | the alternative land block, used only with supremaMrk off |
| LandAgr_ | (RMS,xxUsingLand) | 1865 | off | - | the alternative land block, used only with supremaMrk off |
| LandNagr_ | (RMS) | 1879 | off | - | the alternative land block, used only with supremaMrk off |
| LandTypesNagrTmp_ | (RMS,foreOlndArtif) | 1895 | off | - | the alternative land block, used only with supremaMrk off |
| LandTypesNagr_ | (RMS,foreOlndArtif) | 1909 | off | - | the alternative land block, used only with supremaMrk off |

## Land (supremaMrk on)

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| LandSupplyMNL_ | (RMS,luEla) | 1737 | not ported | none in the market (EU land in the supply models) | CAPRI's land supply as a multinomial logit, land demand scaled to supply, land rents, for the market's behavioural regions; supremaMrk on by default (set_global_variables.gms l. 386) |
| LandSupplyRatio_ | (RMS,luEla2) | 1779 | not ported | none | in the model only when not BASELINE (l. 4165-4168) |
| NumeraireLand_ | (RMS,luEla) | 1758 | not ported | none | in the model only when not BASELINE (l. 4165-4168) |
| LandAgrFromYld_ | (RMS,xxUsingLand) | 1812 | not ported | none in the market (EU land in the supply models) | CAPRI's land supply as a multinomial logit, land demand scaled to supply, land rents, for the market's behavioural regions; supremaMrk on by default (set_global_variables.gms l. 386) |
| ScaleLandAgr_ | (RMS,xxUsingLand) | 1837 | not ported | none in the market (EU land in the supply models) | CAPRI's land supply as a multinomial logit, land demand scaled to supply, land rents, for the market's behavioural regions; supremaMrk on by default (set_global_variables.gms l. 386) |
| LndSupplyEqualsDemand_ | (RMS,luAgrMrk) | 1698 | not ported | none in the market (EU land in the supply models) | CAPRI's land supply as a multinomial logit, land demand scaled to supply, land rents, for the market's behavioural regions; supremaMrk on by default (set_global_variables.gms l. 386) |
| rentFromProdpriceLand_ | (RMS,luAgrMrk) | 1707 | not ported | none in the market (EU land in the supply models) | CAPRI's land supply as a multinomial logit, land demand scaled to supply, land rents, for the market's behavioural regions; supremaMrk on by default (set_global_variables.gms l. 386) |

## Yields (unconditional)

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| Yield_ | (RMS,xxUsingLand) | 1795 | not ported | none in the market (EU yields in the supply models) | in the model whatever supremaMrk (m_bevFunctionsMarket l. 4170; m_globMarket l. 4268); ProdPriceFudge_ only where a producer price's lower bound is 0 or below |
| ProdPriceFudge_ | (RMS,xx1LandOrUsingLand) | 2378 | not ported | none in the market (EU yields in the supply models) | in the model whatever supremaMrk (m_bevFunctionsMarket l. 4170; m_globMarket l. 4268); ProdPriceFudge_ only where a producer price's lower bound is 0 or below |

## Young animals

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| yaniMarket_ | (RM,xxOmYani) | 1579 | ported | coupling/young_animals.py, market/supply.py | solved in an inner loop now; lifted in G2g (not re-verified by the review) |
| rmsYaniMarket_ | (RMSSUP,xxOmYani) | 1613 | ported | coupling/young_animals.py, market/supply.py | solved in an inner loop now; lifted in G2g (not re-verified by the review) |

## Crop inputs in the market

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| inputMarket_ | (RMS,xx1CrpInput) | 1643 | off | - | crpInputInMrk off by default |
| InpPriceFudge_ | (RMS,xx1CrpInput) | 2397 | off | - | crpInputInMrk off by default |

## Processing

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| ProcO_ | (RMS,XXX) | 1168 | ported | market/processing_ad.py (G2e) | checked by the review (procYield_ closed form solves CAPRI's implicit mass correction exactly) |
| MaprFeed_ | (RMSSUP,RESIMPX) | 1442 | ported | market/feed.py (_apply_feed_byproduct_supply) | feed by-products of milling and processing |
| ProcMargO_ | (RMS,SED) | 1118 | ported | market/processing_ad.py (G2e) | checked by the review (procYield_ closed form solves CAPRI's implicit mass correction exactly) |
| ProcNQ_ | (RMS,XXX) | 1140 | ported | market/processing_ad.py (G2e) | checked by the review (procYield_ closed form solves CAPRI's implicit mass correction exactly) |
| ProcFudge_ | (RMS,XXX) | 1158 | ported, other form | market/processing_ad.py (G2e) | always on and at the model region's level, z from the scaled base (CAPRI: per behavioural region, where the bounds allow); DEP-37 |
| procYield_ | (RMS,XXX) | 1480 | ported | market/processing_ad.py (G2e) | checked by the review (procYield_ closed form solves CAPRI's implicit mass correction exactly) |

## Feed (non-EU)

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| FeedNQ_ | (RMS,XX) | 1033 | ported | market/feed.py (noneu_feed_change) | FeedBal_ evaluated with a lag on the dairy price now; lifted in G2d |
| FeedFudge_ | (RMS,XX) | 1054 | not ported | none | active only where widen_bounds has pushed a feed lower bound to 0 or below |
| FeedBal_ | (RMS) | 1018 | ported | market/feed.py (noneu_feed_change) | FeedBal_ evaluated with a lag on the dairy price now; lifted in G2d |

## Feed (EU bulks)

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| feedBlkPrice_ | (RMSSUP,FEED_TRD) | 951 | ported | market/feed.py (eu_feed_use, feed_bulk_market_factor) | G2d |
| feedBlk_ | (RMSSUP,FEED_TRD) | 972 | ported | market/feed.py (eu_feed_use, feed_bulk_market_factor) | G2d |
| FeedShareEqu_ | (RMSSUP,XXX) | 999 | ported | market/feed.py (eu_feed_use, feed_bulk_market_factor) | G2d |

## Dairy

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| DairyNQ_ | (RMS,MLK) | 1069 | ported | market/dairy.py | a Newton solve inside the response now; lifted in G2f |
| ProcMargM_ | (RMS,MLK) | 1089 | ported | market/dairy.py | a Newton solve inside the response now; lifted in G2f |
| FatsProtBal_ | (RMS,FatsProt) | 1103 | ported | market/dairy.py | a Newton solve inside the response now; lifted in G2f |

## Biofuels

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| Biof_ | (RMS,XX) | 1341 | to check | market/biofuel.py | the block is ported (biofuel_state); the equation-by-equation match is G2g's |
| CSugarPrice_ | (RMS) | 1253 | to check | market/biofuel.py | the block is ported (biofuel_state); the equation-by-equation match is G2g's |
| prodQuantBiofBy_ | (RMS,bio_by) | 1267 | to check | market/biofuel.py | the block is ported (biofuel_state); the equation-by-equation match is G2g's |
| ProdBiof_ | (RMS,XXBioF) | 1233 | to check | market/biofuel.py | the block is ported (biofuel_state); the equation-by-equation match is G2g's |
| MaprBiof_ | (RMS,XXBioF) | 1214 | to check | market/biofuel.py | the block is ported (biofuel_state); the equation-by-equation match is G2g's |
| SupplyBiof_ | (RMS,XXBIOF) | 1186 | to check | market/biofuel.py | the block is ported (biofuel_state); the equation-by-equation match is G2g's |
| BiofPriceRel_ | (RMS,XXBIOF) | 1384 | to check | market/biofuel.py | the block is ported (biofuel_state); the equation-by-equation match is G2g's |
| BiofFeedCost_ | (RMS,XBioStock) | 1283 | to check | market/biofuel.py | the block is ported (biofuel_state); the equation-by-equation match is G2g's |
| BiofFeedCostAgg_ | (RMS,XXBIOF) | 1313 | to check | market/biofuel.py | the block is ported (biofuel_state); the equation-by-equation match is G2g's |
| biofDemshare_ | (RMS,XXBIOF) | 1393 | to check | market/biofuel.py | the block is ported (biofuel_state); the equation-by-equation match is G2g's |
| biofDem_ | (RMS,XXBioF) | 1421 | to check | market/biofuel.py | the block is ported (biofuel_state); the equation-by-equation match is G2g's |

## Armington trade

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| arm2QuantShares_ | (RM,XXX) | 2706 | ported, other form | market/bilateral.py, trade_ad.py (G2a) | plain CES (CAPRI with p_arm2Commit = 0, a registered departure); one Armington elasticity per commodity, CAPRI's per market region (DEP-40) |
| domSalesShares_ | (RM,XXX) | 2721 | ported, other form | market/bilateral.py, trade_ad.py (G2a) | plain CES (CAPRI with p_arm2Commit = 0, a registered departure); one Armington elasticity per commodity, CAPRI's per market region (DEP-40) |
| importShares_ | (RM,RM1,XXX) | 2749 | ported, other form | market/bilateral.py, trade_ad.py (G2a) | plain CES (CAPRI with p_arm2Commit = 0, a registered departure); one Armington elasticity per commodity, CAPRI's per market region (DEP-40) |
| tradeFlowFudge_ | (RM,RM1,XXX) | 2784 | not ported | - | negative flows under commitment terms (with the departure above) |
| HicksNeutral_ | (rm, xxx) | 2799 | to check | none found | Hicks-neutral preference shift (v_gammaCES), active where v_gammaCES is free |
| transition_ | (rm, rm1, xxx) | 2809 | off | - | modArmington off by default (extended KVT) |
| arm1PriceAgg_ | (RM,XXX) | 2950 | ported, other form | market/bilateral.py, trade_ad.py (G2a) | plain CES (CAPRI with p_arm2Commit = 0, a registered departure); one Armington elasticity per commodity, CAPRI's per market region (DEP-40) |
| arm2PriceAgg_ | (RM,XXX) | 3004 | ported, other form | market/bilateral.py, trade_ad.py (G2a) | plain CES (CAPRI with p_arm2Commit = 0, a registered departure); one Armington elasticity per commodity, CAPRI's per market region (DEP-40) |
| impPrice_ | (RM,RM1,XXX) | 2849 | ported, other form | market/bilateral.py, trade_ad.py (G2a) | endogenous tariffs only for the EU bilateral TRQs; no export subsidies or flexible levies |

## Prices

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| PMrk_ | (RM,XXX) | 3074 | departure | none (trade_ad.py holds non-supplying regions at their current price ratio) | CAPRI: the market price of a region without production follows its Armington price (l. 3074-3080); DEP-32 |
| PPri_ | (RMS,XXX) | 3046 | to check | market/bilateral_solve.py | producer price inside the aggregates; the trade system's ratio is the market price ratio, CAPRI's producer price adds per-tonne support (review Q3.a3), to settle in G2b |

## Policy-block aggregates

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| MarketPriceAgg_ | (RMTP,XXX) | 3088 | to check | market/bilateral.py (EU blocks) | prices and flows aggregated to the policy blocks (RMTP) the tariffs and TRQs apply to |
| TradeFlowsAgg_ | (RMTP,RMTP1,XXX) | 3106 | to check | market/bilateral.py (EU blocks) | prices and flows aggregated to the policy blocks (RMTP) the tariffs and TRQs apply to |

## Balances

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| SupBalM_ | (RM,XXX) | 2632 | ported | market/bilateral.py, demand.py, trade_ad.py | without the intervention stock change and the C-sugar terms (not ported) |
| ArmBal1_ | (RM,XXX) | 2602 | ported | market/bilateral.py, demand.py, trade_ad.py | without the intervention stock change and the C-sugar terms (not ported) |
| expQuant_ | (RM,XXX) | 3648 | ported | market/bilateral.py, demand.py, trade_ad.py | without the intervention stock change and the C-sugar terms (not ported) |

## Intervention stocks and subsidised exports

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| nonDoubleZeroExports_ | (RMTP,XXX) | 3684 | not ported | - | active where CAPRI's data have subsidised exports (FEOE_max) or intervention (nonDoubleZeroExports_'s domain) |
| buyingToIntervStock_ | (RMTP,XXX) | 3507 | not ported | - | policy/policy_module.py notes them as to be ported; active where CAPRI's data have administrative prices and stocks (PADM with STKS) |
| probMarketPriceUnderSafetyNet_ | (RMTP,XXX) | 3492 | not ported | - | policy/policy_module.py notes them as to be ported; active where CAPRI's data have administrative prices and stocks (PADM with STKS) |
| releaseFromIntervStock_ | (RMTP,XXX) | 3617 | not ported | - | policy/policy_module.py notes them as to be ported; active where CAPRI's data have administrative prices and stocks (PADM with STKS) |
| releaseFromIntervStock1_ | (RMTP,XXX) | 3633 | not ported | - | policy/policy_module.py notes them as to be ported; active where CAPRI's data have administrative prices and stocks (PADM with STKS) |
| intervStockLevel_ | (RMTP,XXX) | 3596 | not ported | - | policy/policy_module.py notes them as to be ported; active where CAPRI's data have administrative prices and stocks (PADM with STKS) |
| intervStockChange_ | (RMTP,XXX) | 3605 | not ported | - | policy/policy_module.py notes them as to be ported; active where CAPRI's data have administrative prices and stocks (PADM with STKS) |
| unitValueExports_ | (RMTP,XXX) | 3703 | not ported | - | active where CAPRI's data have subsidised exports (FEOE_max) or intervention (nonDoubleZeroExports_'s domain) |
| buyingRM_ | (RM_not_RMTP,XXX) | 3520 | not ported | - | policy/policy_module.py notes them as to be ported; active where CAPRI's data have administrative prices and stocks (PADM with STKS) |
| buyingRMNum_ | (RM_not_RMTP,XXX) | 3528 | not ported | - | policy/policy_module.py notes them as to be ported; active where CAPRI's data have administrative prices and stocks (PADM with STKS) |
| releaseRM_ | (RM_not_RMTP,XXX) | 3553 | not ported | - | policy/policy_module.py notes them as to be ported; active where CAPRI's data have administrative prices and stocks (PADM with STKS) |
| releaseRMNum_ | (RM_not_RMTP,XXX) | 3561 | not ported | - | policy/policy_module.py notes them as to be ported; active where CAPRI's data have administrative prices and stocks (PADM with STKS) |
| buyingShares_ | (RM_not_RMTP,XXX) | 3539 | not ported | - | policy/policy_module.py notes them as to be ported; active where CAPRI's data have administrative prices and stocks (PADM with STKS) |
| releaseShares_ | (RM_not_RMTP,XXX) | 3572 | not ported | - | policy/policy_module.py notes them as to be ported; active where CAPRI's data have administrative prices and stocks (PADM with STKS) |
| stockChangeRM_ | (RM_not_RMTP,XXX) | 3584 | not ported | - | policy/policy_module.py notes them as to be ported; active where CAPRI's data have administrative prices and stocks (PADM with STKS) |
| EXPs_ | (RMTP,XXX) | 3724 | not ported | - | active where CAPRI's data have subsidised exports (FEOE_max) or intervention (nonDoubleZeroExports_'s domain) |
| valSubsExports_ | (RMTP,XXX) | 3716 | not ported | - | active where CAPRI's data have subsidised exports (FEOE_max) or intervention (nonDoubleZeroExports_'s domain) |

## Private stocks

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| privStockFin_ | (RM,XXX) | 2656 | off | - | capri_sr off (short-run version) |

## Land-use change (luc_market)

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| LinkLuWithShares_ | (RMS,luMrkMod) | 1923 | not ported | environmental/luc.py (supply side) | on with REPORTS_ENV (set_global_variables.gms l. 395): the market's LUC estimation |
| luClassInitial_ | (rms,LUclass) | 1950 | not ported | environmental/luc.py (supply side) | on with REPORTS_ENV (set_global_variables.gms l. 395): the market's LUC estimation |
| luClassFinal_ | (rms,LUclass1) | 1938 | not ported | environmental/luc.py (supply side) | on with REPORTS_ENV (set_global_variables.gms l. 395): the market's LUC estimation |
| FocLUC_ | (rms,LUCpos) | 1960 | not ported | environmental/luc.py (supply side) | on with REPORTS_ENV (set_global_variables.gms l. 395): the market's LUC estimation |
| derivativeOfNormalLUC_ | (rms,LUCpos) | 1970 | not ported | environmental/luc.py (supply side) | on with REPORTS_ENV (set_global_variables.gms l. 395): the market's LUC estimation |
| derivativeOfGammaLUC_ | (rms,LUCpos) | 1980 | not ported | environmental/luc.py (supply side) | on with REPORTS_ENV (set_global_variables.gms l. 395): the market's LUC estimation |
| derivativeOfSpikeLUC_ | (rms,LUCpos) | 1987 | not ported | environmental/luc.py (supply side) | on with REPORTS_ENV (set_global_variables.gms l. 395): the market's LUC estimation |

## LULUCF emissions (lulucf_market)

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| LandshareMrk_ | (rms,cols) | 2006 | not ported | - | active only with a carbon price on land-use change (domains need v_glucCostPerHa free; where its bounds are set not verified) |
| bioMassPerHaMrk_ | (rms,luclass) | 2023 | not ported | - | active only with a carbon price on land-use change (domains need v_glucCostPerHa free; where its bounds are set not verified) |
| socGrslndMrk_ | (RMS,climzone) | 2089 | not ported | - | active only with a carbon price on land-use change (domains need v_glucCostPerHa free; where its bounds are set not verified) |
| SOCFactorMrk_ | (RMS,luclass,climzone) | 2103 | not ported | - | active only with a carbon price on land-use change (domains need v_glucCostPerHa free; where its bounds are set not verified) |
| GWPCO2BIOMrkLu_ | (RMS,luClass1) | 2049 | not ported | - | active only with a carbon price on land-use change (domains need v_glucCostPerHa free; where its bounds are set not verified) |
| GWPCO2SOIMrkLu_ | (RMS,luClass1) | 2139 | not ported | - | active only with a carbon price on land-use change (domains need v_glucCostPerHa free; where its bounds are set not verified) |
| GWPN2OSOIMrkLu_ | (RMS,luclass1) | 2218 | not ported | - | active only with a carbon price on land-use change (domains need v_glucCostPerHa free; where its bounds are set not verified) |
| GWPCO2BURMrkLu_ | (RMS,luClass1) | 2236 | not ported | - | active only with a carbon price on land-use change (domains need v_glucCostPerHa free; where its bounds are set not verified) |
| GWPCH4BURMrkLu_ | (RMS,luClass1) | 2257 | not ported | - | active only with a carbon price on land-use change (domains need v_glucCostPerHa free; where its bounds are set not verified) |
| GWPN2OBURMrkLu_ | (RMS,luclass1) | 2278 | not ported | - | active only with a carbon price on land-use change (domains need v_glucCostPerHa free; where its bounds are set not verified) |
| GWPCO2HISMrkLu_ | (RMS,luClass1) | 2303 | not ported | - | active only with a carbon price on land-use change (domains need v_glucCostPerHa free; where its bounds are set not verified) |
| GWPCH4HISMrkLu_ | (RMS,luClass1) | 2324 | not ported | - | active only with a carbon price on land-use change (domains need v_glucCostPerHa free; where its bounds are set not verified) |
| GWPglucMrkLu_ | (RMS,luClass1) | 2345 | not ported | - | active only with a carbon price on land-use change (domains need v_glucCostPerHa free; where its bounds are set not verified) |
| glucCostPerHa_ | (RMS,luClass1) | 2357 | not ported | - | active only with a carbon price on land-use change (domains need v_glucCostPerHa free; where its bounds are set not verified) |
| rentForForeOlndArtif_ | (RMS,ForeOlndArtif) | 1725 | not ported | - | active only with a carbon price on land-use change (domains need v_glucCostPerHa free; where its bounds are set not verified) |

## Objective

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| FlipFlop_ |  | 3771 | replaced | ½‖z − z₀‖² (section 7; under review) | CAPRI's formal objective of a square system; the review (Q2) finds IPOPT ignores an objective on a square problem |

## Tariffs and TRQs

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| TRQImports_ | (RMTP,XXX) | 3142 | not ported | none | imports under a global (erga omnes) TRQ: absent (DEP-33) |
| trqSigmoidFunc_ | (RMTP,RMTP1,XXX) | 3275 | ported, other form | market/bilateral.py, trade_ad.py (G2a) | quotas summed per model exporter, one sigmoid on the sum, the fill scaled by an import share; EU quotas only (DEP-34, DEP-35) |
| tarSpec_ | (RMTP,RMTP1,XXX) | 3292 | ported, other form | market/bilateral.py, trade_ad.py (G2a) | only the branch of a bilateral TRQ without a global one |
| tarSpecW_ | (RMTP,"Rw",XXX) | 3399 | not ported | - | tariffs against the rest of the world under global TRQs (with DEP-33) |
| tarAdVal_ | (RMTP,RMTP1,XXX) | 3417 | departure | tools/build/build_bilateral_market.py (gap at base) | the out-of-quota ad valorem rate frozen into a EUR/t gap at base FOB prices (DEP-36) |
| tarAdValW_ | (RMTP,"Rw",XXX) | 3475 | not ported | - | tariffs against the rest of the world under global TRQs (with DEP-33) |

## Flexible levies and entry prices

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| prefTriggerPrice_ | (RMTP,RMTP1,XXX) | 3369 | not ported | - | the EU's flexible cereal tariffs (MinBordP) and the entry prices of fruit and vegetables (TriggerP) |
| FlexLevyNotCut_ | (RMTP,RMTP1,XXX) | 3236 | not ported | - | the EU's flexible cereal tariffs (MinBordP) and the entry prices of fruit and vegetables (TriggerP) |
| FlexLevy_ | (RMTP,RMTP1,XXX) | 3258 | not ported | - | the EU's flexible cereal tariffs (MinBordP) and the entry prices of fruit and vegetables (TriggerP) |
| tarSpecIfEntryPrice_ | (RMTP,RMTP1,XXX) | 3204 | not ported | - | the EU's flexible cereal tariffs (MinBordP) and the entry prices of fruit and vegetables (TriggerP) |
| EntryPriceDriver_ | (RMTP,RMTP1,XXX) | 3176 | not ported | - | the EU's flexible cereal tariffs (MinBordP) and the entry prices of fruit and vegetables (TriggerP) |
