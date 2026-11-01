# G3: CAPRI's market model m_globMarket, equation by equation (1 November 2026)

The inventory section 3.1 of MARKET_IPOPT_DESIGN.md asks for before G3 is assembled in CAPRI's own form. Source: CAPRI's arm/market_model.gms (capri_sources/gams, docs/EXTERNAL_SOURCES.md): the equation lists of m_globMarket (l. 4243) and of m_bevFunctionsMarket (l. 4150) that it includes, each equation's definition (line given), its domain and the conditional blocks around it ($ifi/$iftheni with CAPRI's defaults from capmod/set_global_variables.gms). The counterpart in capri-mod is found by the equation's name cited in our code and by reading the blocks; 'to check' marks those not yet matched equation by equation.

123 equations listed in the model; 24 ported, 11 ported in another form, 1 departure, 22 to check, 53 not ported, 11 off by CAPRI's default switches, 1 replaced. The definitions use 111 distinct variables (v_*).

Status: **ported** the same equation; **ported, other form** the same relation written otherwise (a substitution, a ratio form); **departure** different from CAPRI's (registered or to be); **to check** a counterpart exists or may exist, not yet matched equation by equation; **not ported** no counterpart; **off** switched off by CAPRI's default settings (the switch named); **replaced** the formal objective.

## Findings for G3

- **Not ported, and on in CAPRI's default runs:** the market's land and yield block (supremaMrk on: land supply as a multinomial logit, yields responding to producer prices, land demand scaled to supply, land rents) for the market's behavioural regions; the land-use-change estimation (luc_market, on with the environmental reports); the intervention stocks, subsidised exports, flexible cereal levies and entry prices where CAPRI's 2030 data have them (to be checked in the data before deciding).

- **Smooth positivity:** CAPRI keeps quantities positive with ncpcm 'fudge' equations (consFudge_, ProdFudge_, FeedFudge_, ProcFudge_, tradeFlowFudge_; Fisher-Burmeister smoothing), each active only where the quantity's lower bound is not positive (e.g. consFudge_ l. 905: v_consQuant.lo LE 0), the quantity then written through a free twin variable (v_consQuantNeg). Ours has hard floors in some places (human consumption: fmax at 0). In G3 CAPRI's bounds and smooth forms replace the floors (no kinks for IPOPT).

- **Scaling:** every CAPRI equation is divided by its base value (e.g. ArmBal1_ by DATA(RM,'arm1',XXX) + 0.1): G3 takes CAPRI's scaling.

- **The Armington commitments** (p_arm2Commit, the augmented CES) remain a registered departure; with them would come tradeFlowFudge_ and the Hicks-neutral shift.


## Human consumption (GL)

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| GLDemandFS_ | (RMS) | 826 | ported, other form | market/demand_ad.py (G2c) | CAPRI's intermediate terms (F, G, G_i) are folded into one expression per good |
| GLDemandGS_ | (RMS) | 845 | ported, other form | market/demand_ad.py (G2c) | CAPRI's intermediate terms (F, G, G_i) are folded into one expression per good |
| GLDemandGis_ | (RMS,XXX) | 860 | ported, other form | market/demand_ad.py (G2c) | CAPRI's intermediate terms (F, G, G_i) are folded into one expression per good |
| XiS_ | (RMS,XXX) | 891 | ported, other form | market/demand_ad.py (G2c) | CAPRI's intermediate terms (F, G, G_i) are folded into one expression per good |
| consFudge_ | (RMS,XXX) | 905 | departure | market/demand_ad.py (G2c) | CAPRI's smooth positivity (ncpcm); ours a hard floor at 0 (fmax): to take CAPRI's in G3 |
| CPri_ | (RMS,XXX) | 3032 | ported, other form | market/demand.py gl_food_ratio | consumer price = Armington price + margin, written on the price ratio |

## Market supply

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| ProdNQ_ | (RMS,XX1) | 1529 | ported | market/supply.py (EU through the measured Hessian; non-EU ProdNQ_) | G2b |
| ProdFudge_ | (RMS,XX1) | 2420 | to check | none found | CAPRI's smooth positivity of production |
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

## Land and yields (supremaMrk on)

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| LandSupplyMNL_ | (RMS,luEla) | 1737 | not ported | none in the market (EU land in the supply models) | CAPRI's land supply and yield response in the market's behavioural regions; on by default (set_global_variables.gms l. 386) |
| LandSupplyRatio_ | (RMS,luEla2) | 1779 | not ported | none in the market (EU land in the supply models) | CAPRI's land supply and yield response in the market's behavioural regions; on by default (set_global_variables.gms l. 386) |
| NumeraireLand_ | (RMS,luEla) | 1758 | not ported | none in the market (EU land in the supply models) | CAPRI's land supply and yield response in the market's behavioural regions; on by default (set_global_variables.gms l. 386) |
| Yield_ | (RMS,xxUsingLand) | 1795 | not ported | none in the market (EU land in the supply models) | CAPRI's land supply and yield response in the market's behavioural regions; on by default (set_global_variables.gms l. 386) |
| ProdPriceFudge_ | (RMS,xx1LandOrUsingLand) | 2378 | not ported | none in the market (EU land in the supply models) | CAPRI's land supply and yield response in the market's behavioural regions; on by default (set_global_variables.gms l. 386) |
| LandAgrFromYld_ | (RMS,xxUsingLand) | 1812 | not ported | none in the market (EU land in the supply models) | CAPRI's land supply and yield response in the market's behavioural regions; on by default (set_global_variables.gms l. 386) |
| ScaleLandAgr_ | (RMS,xxUsingLand) | 1837 | not ported | none in the market (EU land in the supply models) | CAPRI's land supply and yield response in the market's behavioural regions; on by default (set_global_variables.gms l. 386) |
| LndSupplyEqualsDemand_ | (RMS,luAgrMrk) | 1698 | not ported | none in the market (EU land in the supply models) | CAPRI's land supply and yield response in the market's behavioural regions; on by default (set_global_variables.gms l. 386) |
| rentFromProdpriceLand_ | (RMS,luAgrMrk) | 1707 | not ported | none in the market (EU land in the supply models) | CAPRI's land supply and yield response in the market's behavioural regions; on by default (set_global_variables.gms l. 386) |

## Young animals

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| yaniMarket_ | (RM,xxOmYani) | 1579 | ported | coupling/young_animals.py, market/supply.py | solved in an inner loop now; lifted in G2g |
| rmsYaniMarket_ | (RMSSUP,xxOmYani) | 1613 | ported | coupling/young_animals.py, market/supply.py | solved in an inner loop now; lifted in G2g |

## Crop inputs in the market

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| inputMarket_ | (RMS,xx1CrpInput) | 1643 | off | - | crpInputInMrk off by default |
| InpPriceFudge_ | (RMS,xx1CrpInput) | 2397 | off | - | crpInputInMrk off by default |

## Processing

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| ProcO_ | (RMS,XXX) | 1168 | ported | market/processing_ad.py (G2e) |  |
| MaprFeed_ | (RMSSUP,RESIMPX) | 1442 | ported | market/feed.py (_apply_feed_byproduct_supply) | feed by-products of milling and processing |
| ProcMargO_ | (RMS,SED) | 1118 | ported | market/processing_ad.py (G2e) |  |
| ProcNQ_ | (RMS,XXX) | 1140 | ported | market/processing_ad.py (G2e) |  |
| ProcFudge_ | (RMS,XXX) | 1158 | ported | market/processing_ad.py (G2e) |  |
| procYield_ | (RMS,XXX) | 1480 | ported | market/processing_ad.py (G2e) |  |

## Feed (non-EU)

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| FeedNQ_ | (RMS,XX) | 1033 | ported | market/feed.py (noneu_feed_change) | FeedBal_ evaluated with a lag on the dairy price now; lifted in G2d |
| FeedFudge_ | (RMS,XX) | 1054 | to check | none found | CAPRI's smooth positivity of feed demand |
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
| arm2QuantShares_ | (RM,XXX) | 2706 | ported, other form | market/bilateral.py, trade_ad.py (G2a) | plain CES; CAPRI's augmented CES with commitment terms (p_arm2Commit) is a registered departure |
| domSalesShares_ | (RM,XXX) | 2721 | ported, other form | market/bilateral.py, trade_ad.py (G2a) | plain CES; CAPRI's augmented CES with commitment terms (p_arm2Commit) is a registered departure |
| importShares_ | (RM,RM1,XXX) | 2749 | ported, other form | market/bilateral.py, trade_ad.py (G2a) | plain CES; CAPRI's augmented CES with commitment terms (p_arm2Commit) is a registered departure |
| tradeFlowFudge_ | (RM,RM1,XXX) | 2784 | not ported | - | negative flows under commitment terms (with the departure above) |
| HicksNeutral_ | (rm, xxx) | 2799 | to check | none found | Hicks-neutral preference shift (v_gammaCES), active where v_gammaCES is free |
| transition_ | (rm, rm1, xxx) | 2809 | off | - | modArmington off by default (extended KVT) |
| arm1PriceAgg_ | (RM,XXX) | 2950 | ported, other form | market/bilateral.py, trade_ad.py (G2a) | plain CES; CAPRI's augmented CES with commitment terms (p_arm2Commit) is a registered departure |
| arm2PriceAgg_ | (RM,XXX) | 3004 | ported, other form | market/bilateral.py, trade_ad.py (G2a) | plain CES; CAPRI's augmented CES with commitment terms (p_arm2Commit) is a registered departure |
| impPrice_ | (RM,RM1,XXX) | 2849 | ported, other form | market/bilateral.py, trade_ad.py (G2a) | plain CES; CAPRI's augmented CES with commitment terms (p_arm2Commit) is a registered departure |

## Prices

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| PMrk_ | (RM,XXX) | 3074 | to check | market/bilateral_solve.py | market price without production; producer prices of the member states inside a block |
| PPri_ | (RMS,XXX) | 3046 | to check | market/bilateral_solve.py | market price without production; producer prices of the member states inside a block |

## Policy-block aggregates

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| MarketPriceAgg_ | (RMTP,XXX) | 3088 | to check | market/bilateral.py (EU blocks) | prices and flows aggregated to the policy blocks (RMTP) the tariffs and TRQs apply to |
| nonDoubleZeroExports_ | (RMTP,XXX) | 3684 | to check | market/bilateral.py (EU blocks) | prices and flows aggregated to the policy blocks (RMTP) the tariffs and TRQs apply to |
| TradeFlowsAgg_ | (RMTP,RMTP1,XXX) | 3106 | to check | market/bilateral.py (EU blocks) | prices and flows aggregated to the policy blocks (RMTP) the tariffs and TRQs apply to |

## Balances

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| SupBalM_ | (RM,XXX) | 2632 | ported | market/bilateral.py, demand.py, trade_ad.py |  |
| ArmBal1_ | (RM,XXX) | 2602 | ported | market/bilateral.py, demand.py, trade_ad.py |  |
| expQuant_ | (RM,XXX) | 3648 | ported | market/bilateral.py, demand.py, trade_ad.py |  |

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
| LandshareMrk_ | (rms,cols) | 2006 | not ported | - | active only with a carbon price on land-use change (p_carbonTax GLUC > 0) |
| bioMassPerHaMrk_ | (rms,luclass) | 2023 | not ported | - | active only with a carbon price on land-use change (p_carbonTax GLUC > 0) |
| socGrslndMrk_ | (RMS,climzone) | 2089 | not ported | - | active only with a carbon price on land-use change (p_carbonTax GLUC > 0) |
| SOCFactorMrk_ | (RMS,luclass,climzone) | 2103 | not ported | - | active only with a carbon price on land-use change (p_carbonTax GLUC > 0) |
| GWPCO2BIOMrkLu_ | (RMS,luClass1) | 2049 | not ported | - | active only with a carbon price on land-use change (p_carbonTax GLUC > 0) |
| GWPCO2SOIMrkLu_ | (RMS,luClass1) | 2139 | not ported | - | active only with a carbon price on land-use change (p_carbonTax GLUC > 0) |
| GWPN2OSOIMrkLu_ | (RMS,luclass1) | 2218 | not ported | - | active only with a carbon price on land-use change (p_carbonTax GLUC > 0) |
| GWPCO2BURMrkLu_ | (RMS,luClass1) | 2236 | not ported | - | active only with a carbon price on land-use change (p_carbonTax GLUC > 0) |
| GWPCH4BURMrkLu_ | (RMS,luClass1) | 2257 | not ported | - | active only with a carbon price on land-use change (p_carbonTax GLUC > 0) |
| GWPN2OBURMrkLu_ | (RMS,luclass1) | 2278 | not ported | - | active only with a carbon price on land-use change (p_carbonTax GLUC > 0) |
| GWPCO2HISMrkLu_ | (RMS,luClass1) | 2303 | not ported | - | active only with a carbon price on land-use change (p_carbonTax GLUC > 0) |
| GWPCH4HISMrkLu_ | (RMS,luClass1) | 2324 | not ported | - | active only with a carbon price on land-use change (p_carbonTax GLUC > 0) |
| GWPglucMrkLu_ | (RMS,luClass1) | 2345 | not ported | - | active only with a carbon price on land-use change (p_carbonTax GLUC > 0) |
| glucCostPerHa_ | (RMS,luClass1) | 2357 | not ported | - | active only with a carbon price on land-use change (p_carbonTax GLUC > 0) |
| rentForForeOlndArtif_ | (RMS,ForeOlndArtif) | 1725 | not ported | - | active only with a carbon price on land-use change (p_carbonTax GLUC > 0) |

## Objective

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| FlipFlop_ |  | 3771 | replaced | ½‖z − z₀‖² (section 7) | CAPRI's formal objective of a square system |

## Intervention stocks

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| buyingToIntervStock_ | (RMTP,XXX) | 3507 | not ported | - | policy/policy_module.py notes it as to be ported; active where CAPRI's data have administrative prices and stocks |
| probMarketPriceUnderSafetyNet_ | (RMTP,XXX) | 3492 | not ported | - | policy/policy_module.py notes it as to be ported; active where CAPRI's data have administrative prices and stocks |
| releaseFromIntervStock_ | (RMTP,XXX) | 3617 | not ported | - | policy/policy_module.py notes it as to be ported; active where CAPRI's data have administrative prices and stocks |
| releaseFromIntervStock1_ | (RMTP,XXX) | 3633 | not ported | - | policy/policy_module.py notes it as to be ported; active where CAPRI's data have administrative prices and stocks |
| intervStockLevel_ | (RMTP,XXX) | 3596 | not ported | - | policy/policy_module.py notes it as to be ported; active where CAPRI's data have administrative prices and stocks |
| intervStockChange_ | (RMTP,XXX) | 3605 | not ported | - | policy/policy_module.py notes it as to be ported; active where CAPRI's data have administrative prices and stocks |
| buyingRM_ | (RM_not_RMTP,XXX) | 3520 | not ported | - | policy/policy_module.py notes it as to be ported; active where CAPRI's data have administrative prices and stocks |
| buyingRMNum_ | (RM_not_RMTP,XXX) | 3528 | not ported | - | policy/policy_module.py notes it as to be ported; active where CAPRI's data have administrative prices and stocks |
| releaseRM_ | (RM_not_RMTP,XXX) | 3553 | not ported | - | policy/policy_module.py notes it as to be ported; active where CAPRI's data have administrative prices and stocks |
| releaseRMNum_ | (RM_not_RMTP,XXX) | 3561 | not ported | - | policy/policy_module.py notes it as to be ported; active where CAPRI's data have administrative prices and stocks |
| buyingShares_ | (RM_not_RMTP,XXX) | 3539 | not ported | - | policy/policy_module.py notes it as to be ported; active where CAPRI's data have administrative prices and stocks |
| releaseShares_ | (RM_not_RMTP,XXX) | 3572 | not ported | - | policy/policy_module.py notes it as to be ported; active where CAPRI's data have administrative prices and stocks |
| stockChangeRM_ | (RM_not_RMTP,XXX) | 3584 | not ported | - | policy/policy_module.py notes it as to be ported; active where CAPRI's data have administrative prices and stocks |

## Subsidised exports

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| unitValueExports_ | (RMTP,XXX) | 3703 | not ported | - | active where CAPRI's data have subsidised exports |
| EXPs_ | (RMTP,XXX) | 3724 | not ported | - | active where CAPRI's data have subsidised exports |
| valSubsExports_ | (RMTP,XXX) | 3716 | not ported | - | active where CAPRI's data have subsidised exports |

## Tariffs and TRQs

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| TRQImports_ | (RMTP,XXX) | 3142 | ported | market/bilateral.py, trade_ad.py (G2a) |  |
| trqSigmoidFunc_ | (RMTP,RMTP1,XXX) | 3275 | ported | market/bilateral.py, trade_ad.py (G2a) |  |
| tarSpec_ | (RMTP,RMTP1,XXX) | 3292 | ported | market/bilateral.py, trade_ad.py (G2a) |  |
| tarSpecW_ | (RMTP,"Rw",XXX) | 3399 | to check | market/trade_ad.py import_price_matrices (fixed ad valorem) | tariffs as functions of imports and TRQ in CAPRI; fixed rates in ours outside the TRQs |
| tarAdVal_ | (RMTP,RMTP1,XXX) | 3417 | to check | market/trade_ad.py import_price_matrices (fixed ad valorem) | tariffs as functions of imports and TRQ in CAPRI; fixed rates in ours outside the TRQs |
| tarAdValW_ | (RMTP,"Rw",XXX) | 3475 | to check | market/trade_ad.py import_price_matrices (fixed ad valorem) | tariffs as functions of imports and TRQ in CAPRI; fixed rates in ours outside the TRQs |

## Flexible levies and entry prices

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| prefTriggerPrice_ | (RMTP,RMTP1,XXX) | 3369 | not ported | - | the EU's flexible cereal tariffs and the entry prices of fruit and vegetables (CAPRI documentation 5.4.1) |
| FlexLevyNotCut_ | (RMTP,RMTP1,XXX) | 3236 | not ported | - | the EU's flexible cereal tariffs and the entry prices of fruit and vegetables (CAPRI documentation 5.4.1) |
| FlexLevy_ | (RMTP,RMTP1,XXX) | 3258 | not ported | - | the EU's flexible cereal tariffs and the entry prices of fruit and vegetables (CAPRI documentation 5.4.1) |
| tarSpecIfEntryPrice_ | (RMTP,RMTP1,XXX) | 3204 | not ported | - | the EU's flexible cereal tariffs and the entry prices of fruit and vegetables (CAPRI documentation 5.4.1) |
| EntryPriceDriver_ | (RMTP,RMTP1,XXX) | 3176 | not ported | - | the EU's flexible cereal tariffs and the entry prices of fruit and vegetables (CAPRI documentation 5.4.1) |
