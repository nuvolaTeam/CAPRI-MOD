# G3: CAPRI's market model m_globMarket, equation by equation (1 November 2026; refreshed 13 November 2026, G3.0)

The inventory section 3.1 of MARKET_IPOPT_DESIGN.md asks for before G3 is assembled in CAPRI's own form. Source: CAPRI's arm/market_model.gms (capri_sources/gams, docs/EXTERNAL_SOURCES.md): the equation lists of m_globMarket (l. 4243) and of m_bevFunctionsMarket (l. 4150) that it includes, each equation's definition (line given), its domain and the conditional blocks around it ($ifi/$iftheni with CAPRI's defaults from capmod/set_global_variables.gms). The counterpart in capri-mod is found by the equation's name cited in our code and by reading the blocks; 'to check' marks those not yet matched equation by equation. Corrected on 1 November 2026 after the independent review of step G (docs/design/G_REVIEW_2026-11-01.md, Q4).

123 equations listed in the model. At the G3.0 refresh (13 November 2026, against the code on dev and branch p2-step2): 26 ported (21 + the 5 of luc_market), 39 ported in another form (PPri_ since K146, fixed on the way), 2 departures (PMrk_ DEP-32, consFudge_ DEP-38), 1 to check (MarketPriceAgg_), 39 not ported (17 intervention and subsidised-export equations and 15 LULUCF equations, inactive in CAPRI's 2030 runs; the fudge equations ProdFudge_, FeedFudge_, tradeFlowFudge_, ProdPriceFudge_, active only after widen_bounds; the market regions' crop areas and yields, no feedback), 13 off by CAPRI's default switches or data, 2 not needed (luc priors), 1 replaced (the objective). The definitions use 111 distinct variables (v_*). (1 November: 20 ported, 14 other form, 3 departures, 15 to check, 59 not ported, 11 off, 1 replaced.)

Status: **ported** the same equation; **ported, other form** the same relation written otherwise (a substitution, a ratio form); **departure** different from CAPRI's (registered or to be); **to check** a counterpart exists or may exist, not yet matched equation by equation; **not ported** no counterpart; **off** switched off by CAPRI's default settings (the switch named); **replaced** the formal objective.

## Findings for G3 (refreshed 13 November 2026)

- **Ported since 1 November:** the global and bilateral TRQs of every importer, the ad valorem tariffs on current
  prices, the entry prices and flexible levies (stages 4-6, DEP-33-36 and DEP-41 removed), the non-EU market land
  block (stage 7), luc_market (9 November), every G2 block in CasADi (G2a-G2g). The policy blocks are ported in shift
  form: CAPRI's base import price plus the change of the rates from their value at the base flows, so the base is
  CAPRI's exactly and the response is CAPRI's equations' (PORTS_STAGE4.md); G3.2 writes them as CAPRI's equations, the
  base reproduction to be shown there.
- **Not ported and inactive in CAPRI's 2030 runs:** intervention stocks and subsidised exports (no INTM, STKS, FEOE_max
  at CAL), the LULUCF block (no carbon price on land-use change), the C-sugar market (no sugar quota), the
  Hicks-neutral shift (v_gammaCES fixed at 1).
- **Found and fixed, K146:** CAPRI's producer price carries per-tonne support (PPri_: PSEi, PSEd, AREP); its 2030 market data have
  it for Switzerland only (PSEd on 25 products, 50 entries at CAL in data_market_1730defaulta.csv), against
  build_noneu_market_supply_nq.py's statement that none of the non-EU regions have it. The model moves Switzerland's
  producer prices with the market price ratio, so its supply terms in the product prices are too large by
  PPRI0 / (PPRI0 - PSEd): soya x1.83, pulses x1.35, sugar x1.25, sunflower x1.17, rape x1.17, beef x1.12, sheep and
  goat meat x1.11 (22 products, 528 terms). The land rents and raw milk (the dairy block's own price, no PPri_) were right. Fixed
  in the builder: each term h_xy x (PPRI0_y - support_y) / INPE (KNOWN_ISSUES K146).
- **Positivity and bounds:** CAPRI keeps quantities positive by their lower bounds; its ncpcm 'fudge' equations
  (consFudge_, ProdFudge_, FeedFudge_, ProcFudge_, tradeFlowFudge_) act only where a lower bound is 0 or below, which in
  a default simulation happens only after widen_bounds has widened it (consFudge_ not even then: consumption is fixed
  near 0 instead). Our hard floors (fmax) are capri-mod's (DEP-38, DEP-39, and the biofuel block's), so G3 needs
  CAPRI's bound policy (G3.4; the bounds below).
- **Scaling:** every CAPRI equation is divided by its base value (e.g. ArmBal1_ by DATA(RM,'arm1',XXX) + 0.1): G3 takes
  CAPRI's scaling.
- **The Armington commitments** (p_arm2Commit, the augmented CES) remain a registered departure; with them would come
  tradeFlowFudge_ and the Hicks-neutral shift (no p_arm2Commit in the sim_ini_21730 export).

## The default solve today: the fixed points G3 removes and the glue (G3.0, 13 November 2026)

market.solver = "fixed_point" (capri_mod/market/bilateral_solve.py `_solve_bilateral`), market.tol 1e-7 on the largest
residual scaled by S0 + D0, at most market.max_iter = 100 outer steps, Anderson acceleration (market.acceleration),
step clip market.step_clip. One outer step:

1. **Evaluation** `_bilateral_eval(r)` at the producer price ratios r (region x commodity):
   - import prices per commodity (`BilateralCommodity.import_prices`, with the quotas', levies' and entry prices'
     rates) and the Armington prices PA;
   - non-EU FeedBal_ (`noneu_fede`) at the dairy blocks' raw milk price **of the previous evaluation** (a lag);
   - non-EU land markets (`noneu_land_solve`: Newton per region on supply_ad.land_residual_function, up to 100 steps,
     1e-13) and FeedBal_ **solved in turn**, up to 50 rounds until both settle (gap 1e-10 and 1e-13);
   - market supply (`supply_response`): the EU's from the measured Hessian (coupling/hessian.py), the non-EU ProdNQ_,
     with inside it the **young-animal markets and the member states' raw milk cleared in up to 4 alternating
     rounds** (`_milk_and_yani_clear_all`; the dairy block solved once per round, linear) and the TRQ volumes;
   - demand (`demand_response`): human consumption (demand_ad.py), feed (FeedNQ_, the EU's feed bulks), processing and
     crushing at CAPRI's crushing margin (oil and cake at their producer prices), biofuels;
   - feed by-products (MaprFeed_, `_apply_feed_byproduct_supply`);
   - residuals: per bilateral commodity `sc.residual` (SupBalM_, ArmBal1_ and the trade system), per pooled commodity
     the world balance (supply_ad.pooled_residual_function, DEP-31).
2. **TRQs:** with market.trq_joint (default) the quotas' sigmoid is solved with each commodity's prices
   (`_bilateral_inner_trq`) and its residual is a convergence measure; without it, a lagged, damped update.
3. **Per commodity, the trade solve** around the current point (`_bilateral_inner`, `_bilateral_inner_trq`): supply
   and use log-linear in the commodity's own price (`_bilateral_local_el`: elasticities measured once per run by a 1%
   price change, clipped to [-0.5, 5] and [-5, 0.5]), the trade system solved exactly by Newton (finite-difference or
   chord Jacobian, up to 60 steps with backtracking). Pooled commodities: one ratio from the world balance with the
   same elasticities.
4. **Update** r (Anderson on log r, restart when the residual does not fall; damping otherwise).

Inner fixed points and lags G3 replaces by one simultaneous system: (a) the commodity-by-commodity trade solves on
local elasticities (cross-commodity effects only through the outer step); (b) the land-FEDE rounds; (c) FeedBal_ on
the previous evaluation's milk price (also DEP-29 for Norway); (d) the young-animal / raw-milk rounds; (e) the dairy
blocks' Newton step; (f) the TRQ sigmoid when trq_joint is off. At the default solve's equilibria (G3_SYSTEM.md, G3.2c): (b) and (c) leave at most 5.4e-7 EUR/ha and 5.3e-10; (d) leaves the
young-animal markets within 8.0e-7 of their net supply (the 4-round cap). luc_market is solved after the market solve (DEP-44,
equivalent without lulucf_market).

The glue (pandas, to become index maps in G3.2): `_bilateral_eval`'s frames (r, PAr, dom0, world), `supply_response`
and `demand_response` (region x commodity frames, the EU aggregate `_with_eu_aggregate`), the feed by-products, the
crushing price frame, the dairy block's per-member-state dictionaries (ev.dairy_m5_now, ev.milk_dq_now), the
young-animal prices (ev.yani_market_now), the land and FEDE dictionaries (ev.land_now, ev.fede_now). The alternative
market.solver = "newton_krylov" (market_nk.py) solves the same equations at once without derivatives (G2).

## Variables and CAPRI's bounds (arm/set_start_val.gms, widen_bounds.gms; G3.4)

Factors (arm/market_model.gms l. 322-326): P_lowLimitFactQuant 1e-5, p_uppLimitFactQuant 1e3, P_lowLimitFactPrice
0.1, p_uppLimitFactPrice 10. A variable is fixed at its level where its data are zero or small (the .FX lines), which
also decides the system's square shape (the equations' $-conditions test .range).

| Variable | Lower bound | Upper bound | Fixed where | set_start_val.gms |
|---|---|---|---|---|
| v_prodQuant (RMS, XX1) | max(1e-8, min(1e-6, 1e-5 L)); negative allowed where L < 0 or flagged | max(1, L) x 1e3; young animals +-max(100, L) x 1e3 | PROD <= 0.1 (MILK <= 0.01), no ProdNQ_ equation, oil/cake without crushing, biofuels without production | l. 101-169 |
| v_consQuant | HCON x 1e-6 | HCON x 1e3 | no GL terms, HCON <= 0.1 | l. 173-177 |
| v_feedQuant | max(1e-10, min(1e-8, 1e-5 FEED)) | max(1, FEED) x 1e3 | (RM sums of RMS) | l. 181-200 |
| v_feedBlk | L x 1e-10 | max(1, L) x 1e3 | | l. 203-204 |
| v_procQuant | PROC x 1e-5 | max(1, PROC) x 1e3 | no processing Hessian terms, PROC <= 0.1, biofuel and DDGS processing | l. 34-37, 89-90 |
| v_procYield (oil, cake) | Prcy x 1e-3 | Prcy x 1e3 | no production | l. 43-50 |
| v_arm1Quant, v_arm2Quant | min(1e-6, 1e-5 L); arm2 at least 1e-11 | max(1, L) x 1e3 | zero level | l. 408-427 |
| v_tradeFlows | max(1e-10, min(1e-9, 1e-5 L)) | max(1, base flow) x 1e4 | zero flow; aggregates' rows | l. 429-452 |
| v_domSales | max(1e-6 + 1e-8, min(1e-3, 1e-5 L)) | max(1, L) x 1e3 | | l. 455-460 |
| v_impQuant, v_expQuant | 0 | arm2 / production upper bound | | l. 463-468 |
| v_TRQImports | 0 | sum of the imports' upper bounds | | l. 485-487 |
| v_marketPrice | PMrk x 0.1 | PMrk x 10 (young animals +-(L + 10) x 100) | aggregates without supply or use | l. 525-558 |
| v_prodPrice | L x 0.1; land and (flagged) milk down to -max(100, PPri) | L x 10 | no production; INPE, GLYC | l. 560-595 |
| v_rentPerHa (agricultural land) | 1e-3 L | 100 L | FORE, OLND, ARTIF at D_AREA without a LULUCF carbon price | l. 601-607 |
| v_land (luEla) | 1e-6 | ARTO - 1e-6 | INLW | l. 224-230 |
| v_consPrice | 0.1 L (milk products: 0.1 EUR/t) | max(100, L) x 10 (milk products: that x 10) | no consumption or biofuel use | l. 731-744 |
| v_arm1Price | 0.1 L | max(1000, L) x 10 | zero Armington quantity (at arm1P) | l. 752-766 |
| v_arm2Price | max(1e-3 + 1e-5, 0.1 L) | max(100, L) x 10 | zero arm2 quantity | l. 768-772 |
| v_impPrice | max(1e-3 + 1e-5, 0.1 L) | 100 L | no p_impPrice | l. 516-519 |
| v_procMarg (milk / seeds) | -(abs(L) + 100) x 50 / -(abs(L + 10)) x 10 | the same, positive | no dairy Hessian terms / no processing | l. 784-794 |
| v_priceFatProt | -(abs(L) + 10) x 10 | (abs(L) + 10) x 10 | | l. 746-747 |
| v_biofFeedCost, v_biofPriceRel | 0.01 x data | 100 x data | | l. 833-842 |
| v_prodBiof | 0.01 L | 10 L | L <= 0.5; absolute levels | l. 81-84 |
| v_consShareBioF | 0 | 1 | zero share | l. 887-889 |

(L the variable's starting level, from CAPRI's data "CUR". Line numbers of set_start_val.gms in capri_sources; the
young-animal, milk-product and processing-margin rows simplified, see the file.)

widen_bounds.gms (called by simu_market.gms l. 141 after an infeasible solve, at most twice; process_solution.gms
l. 62 in the pre-step): a variable at a bound with a nonzero marginal (reported by the solver as responsible for the
infeasibility) gets that bound widened: a quantity's lower bound to its level minus 10 x max(10, base, |level|) (land:
the same), which can make it negative and so activates the fudge equation and its v_*Neg twin; a quantity's upper bound
x 1000; prices and margins in the same pattern (factors 0.1 / 10, milk's producer price allowed to fall to 10% of its
lower bound), consumption fixed near 0 rather than freed. G3.4 ports these rules with simu_market.gms's acceptance
(numinfes, suminfes up to 0.1 in the last iteration, l. 95-145, 289-300).

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
| Bilateral TRQs outside the EU | trqSigmoidFunc_ per importer | p_trqBilat at 'CAL' in sim_ini_21730 (the state the simulation starts from): five importers besides the EU, MED, MOR, NO000000, RUS and TUR (corrected 1 November 2026: the earlier "about 20" counted dataOut's 2030 TrqNT rows, which include reporting aggregates such as World, HI_INC, NONEU_EU and the global quotas' rows; MARKET_REGIONS_INVENTORY.md) | **yes** |
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
| LandSupplyMNL_ | (RMS,luEla) | 1737 | ported, other form | market/supply.py noneu_land_solve, supply_ad.land_residual_function (stage 7) | the MNL with v_aLU fixed at p_aLU (set_start_val.gms l. 237); NumeraireLand_ / LandSupplyRatio_ (the simulation's asymmetric form) give the same function without LEVL_1 commitments (none in sim_ini_21730); solved by Newton per region inside each evaluation (G3: the rents become unknowns) |
| LandSupplyRatio_ | (RMS,luEla2) | 1779 | ported, other form | market/supply.py noneu_land_solve, supply_ad.land_residual_function (stage 7) | the MNL with v_aLU fixed at p_aLU (set_start_val.gms l. 237); NumeraireLand_ / LandSupplyRatio_ (the simulation's asymmetric form) give the same function without LEVL_1 commitments (none in sim_ini_21730); solved by Newton per region inside each evaluation (G3: the rents become unknowns) |
| NumeraireLand_ | (RMS,luEla) | 1758 | ported, other form | market/supply.py noneu_land_solve, supply_ad.land_residual_function (stage 7) | the MNL with v_aLU fixed at p_aLU (set_start_val.gms l. 237); NumeraireLand_ / LandSupplyRatio_ (the simulation's asymmetric form) give the same function without LEVL_1 commitments (none in sim_ini_21730); solved by Newton per region inside each evaluation (G3: the rents become unknowns) |
| LandAgrFromYld_ | (RMS,xxUsingLand) | 1812 | not ported | none | no feedback on quantities or prices in CAPRI's default (crop areas and yields of the market regions, reporting); registered as not reported (PORTS_STAGE4.md stage 7). ProdPriceFudge_ only where a producer price's lower bound is 0 or below |
| ScaleLandAgr_ | (RMS,xxUsingLand) | 1837 | not ported | none | no feedback on quantities or prices in CAPRI's default (crop areas and yields of the market regions, reporting); registered as not reported (PORTS_STAGE4.md stage 7). ProdPriceFudge_ only where a producer price's lower bound is 0 or below |
| LndSupplyEqualsDemand_ | (RMS,luAgrMrk) | 1698 | ported, other form | market/supply.py, supply_ad.py (stage 7) | the land rows of ProdNQ_ (sign turned, arm/market1.gms l. 593) equal the MNL supply; regions with CAPRI supply models (NO, UK, TR, WB) have no land market, as in CAPRI |
| rentFromProdpriceLand_ | (RMS,luAgrMrk) | 1707 | ported, other form | market/supply.py (stage 7) | rent = producer price + PSEd; in the change form PSEd (Switzerland's 1116.43 EUR/ha) drops out |

## Yields (unconditional)

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| Yield_ | (RMS,xxUsingLand) | 1795 | not ported | none | no feedback on quantities or prices in CAPRI's default (crop areas and yields of the market regions, reporting); registered as not reported (PORTS_STAGE4.md stage 7). ProdPriceFudge_ only where a producer price's lower bound is 0 or below |
| ProdPriceFudge_ | (RMS,xx1LandOrUsingLand) | 2378 | not ported | none | no feedback on quantities or prices in CAPRI's default (crop areas and yields of the market regions, reporting); registered as not reported (PORTS_STAGE4.md stage 7). ProdPriceFudge_ only where a producer price's lower bound is 0 or below |

## Young animals

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| yaniMarket_ | (RM,xxOmYani) | 1579 | ported | market/supply.py _yani_clear, _milk_and_yani_clear_all; coupling/young_animals.py | cleared in up to 4 alternating rounds with the member states' raw milk (dairy block) inside each evaluation; per-sex goods YCAM/YCAF/YBUL/YHEI with supply.use_cattle_member_splits (K65) |
| rmsYaniMarket_ | (RMSSUP,xxOmYani) | 1613 | ported | market/supply.py _yani_clear | as yaniMarket_, per behavioural region |

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
| Biof_ | (RMS,XX) | 1341 | ported, other form | market/biofuel_ad.py (G2g), evaluated by biofuel.py | written once in CasADi (biofuel_ad.py's docstring lists the equations); its max(0, .) and max(1e-6, .) floors are the model's (DEP-39 family), to go to CAPRI's bounds in G3.4 |
| CSugarPrice_ | (RMS) | 1253 | off (data) | - | needs DATA(RMS,'QUTS','SUGA','CUR') > 0: zero in every region of sim_ini_21730 (no sugar quota in 2030) |
| prodQuantBiofBy_ | (RMS,bio_by) | 1267 | ported, other form | market/biofuel_ad.py (G2g), evaluated by biofuel.py | written once in CasADi (biofuel_ad.py's docstring lists the equations); its max(0, .) and max(1e-6, .) floors are the model's (DEP-39 family), to go to CAPRI's bounds in G3.4 |
| ProdBiof_ | (RMS,XXBioF) | 1233 | ported, other form | market/biofuel_ad.py (G2g), evaluated by biofuel.py | written once in CasADi (biofuel_ad.py's docstring lists the equations); its max(0, .) and max(1e-6, .) floors are the model's (DEP-39 family), to go to CAPRI's bounds in G3.4 |
| MaprBiof_ | (RMS,XXBioF) | 1214 | ported, other form | market/biofuel_ad.py (G2g), evaluated by biofuel.py | written once in CasADi (biofuel_ad.py's docstring lists the equations); its max(0, .) and max(1e-6, .) floors are the model's (DEP-39 family), to go to CAPRI's bounds in G3.4 |
| SupplyBiof_ | (RMS,XXBIOF) | 1186 | ported, other form | market/biofuel_ad.py (G2g), evaluated by biofuel.py | written once in CasADi (biofuel_ad.py's docstring lists the equations); its max(0, .) and max(1e-6, .) floors are the model's (DEP-39 family), to go to CAPRI's bounds in G3.4 |
| BiofPriceRel_ | (RMS,XXBIOF) | 1384 | ported, other form | market/biofuel_ad.py (G2g), evaluated by biofuel.py | written once in CasADi (biofuel_ad.py's docstring lists the equations); its max(0, .) and max(1e-6, .) floors are the model's (DEP-39 family), to go to CAPRI's bounds in G3.4 |
| BiofFeedCost_ | (RMS,XBioStock) | 1283 | ported, other form | market/biofuel_ad.py (G2g), evaluated by biofuel.py | written once in CasADi (biofuel_ad.py's docstring lists the equations); its max(0, .) and max(1e-6, .) floors are the model's (DEP-39 family), to go to CAPRI's bounds in G3.4 |
| BiofFeedCostAgg_ | (RMS,XXBIOF) | 1313 | ported, other form | market/biofuel_ad.py (G2g), evaluated by biofuel.py | written once in CasADi (biofuel_ad.py's docstring lists the equations); its max(0, .) and max(1e-6, .) floors are the model's (DEP-39 family), to go to CAPRI's bounds in G3.4 |
| biofDemshare_ | (RMS,XXBIOF) | 1393 | ported, other form | market/biofuel_ad.py (G2g), evaluated by biofuel.py | written once in CasADi (biofuel_ad.py's docstring lists the equations); its max(0, .) and max(1e-6, .) floors are the model's (DEP-39 family), to go to CAPRI's bounds in G3.4 |
| biofDem_ | (RMS,XXBioF) | 1421 | ported, other form | market/biofuel_ad.py (G2g), evaluated by biofuel.py | written once in CasADi (biofuel_ad.py's docstring lists the equations); its max(0, .) and max(1e-6, .) floors are the model's (DEP-39 family), to go to CAPRI's bounds in G3.4 |

## Armington trade

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| arm2QuantShares_ | (RM,XXX) | 2706 | ported, other form | market/bilateral.py, trade_ad.py (G2a) | plain CES (CAPRI with p_arm2Commit = 0, a registered departure); one Armington elasticity per commodity, CAPRI's per market region (DEP-40) |
| domSalesShares_ | (RM,XXX) | 2721 | ported, other form | market/bilateral.py, trade_ad.py (G2a) | plain CES (CAPRI with p_arm2Commit = 0, a registered departure); one Armington elasticity per commodity, CAPRI's per market region (DEP-40) |
| importShares_ | (RM,RM1,XXX) | 2749 | ported, other form | market/bilateral.py, trade_ad.py (G2a) | plain CES (CAPRI with p_arm2Commit = 0, a registered departure); one Armington elasticity per commodity, CAPRI's per market region (DEP-40) |
| tradeFlowFudge_ | (RM,RM1,XXX) | 2784 | not ported | - | negative flows under commitment terms (with the departure above) |
| HicksNeutral_ | (rm, xxx) | 2799 | off | - | modArmington off by default: cal_armington.gms l. 82-83 fixes v_gammaCES and v_Hicks at 1, so the equation drops out (its $-condition needs v_gammaCES.range) |
| transition_ | (rm, rm1, xxx) | 2809 | off | - | modArmington off by default (extended KVT) |
| arm1PriceAgg_ | (RM,XXX) | 2950 | ported, other form | market/bilateral.py, trade_ad.py (G2a) | plain CES (CAPRI with p_arm2Commit = 0, a registered departure); one Armington elasticity per commodity, CAPRI's per market region (DEP-40) |
| arm2PriceAgg_ | (RM,XXX) | 3004 | ported, other form | market/bilateral.py, trade_ad.py (G2a) | plain CES (CAPRI with p_arm2Commit = 0, a registered departure); one Armington elasticity per commodity, CAPRI's per market region (DEP-40) |
| impPrice_ | (RM,RM1,XXX) | 2849 | ported, other form | market/bilateral.py, trade_ad.py (G2a, stages 4-6) | (Pd0_j r_j + TC_ij)(1 + tav/100) + ts with the quotas', levies' and entry prices' rates; export subsidies not ported (inactive in 2030) |

## Prices

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| PMrk_ | (RM,XXX) | 3074 | departure | none (trade_ad.py holds non-supplying regions at their current price ratio) | CAPRI: the market price of a region without production follows its Armington price (l. 3074-3080); DEP-32 |
| PPri_ | (RMS,XXX) | 3046 | ported, other form | market price ratio with CAPRI's support per tonne (build_noneu_market_supply_nq.py support_y) | CAPRI: v_prodPrice = v_marketPrice x margin + PSEi + PSEd + AREP (1 - DECP), relative margin by default (prep_market.gms l. 258); the model's supply terms per unit change of the market price ratio are h x (PPRI0 - support) / INPE, which is PPri_ in change form. Support in CAPRI's 2030 data: Switzerland only (PSEd); until K146 (fixed 13 November 2026) the builder took none |

## Policy-block aggregates

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| MarketPriceAgg_ | (RMTP,XXX) | 3088 | to check | none found by name | the average market price of a true aggregate policy block (RMTPagg); the border measures use the pair's base-flow weighted CIF price instead (TransportCostsAgg_, stage 6); where CAPRI's equations read v_marketPrice of an aggregate is to be traced in G3.2 |
| TradeFlowsAgg_ | (RMTP,RMTP1,XXX) | 3106 | ported | market/bilateral.py, trade_ad.py (stage 4) | flows summed per pair of policy blocks for the quotas |

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
| LinkLuWithShares_ | (RMS,luMrkMod) | 1923 | ported 9 November 2026 | capri_mod/market/luc.py | luc_market (setting market.luc_market): solved after each market solve (no feedback without lulucf_market, DEP-44); reproduces CAPRI's CAL transitions in the 45 regions within 1.2e-8 |
| luClassInitial_ | (rms,LUclass) | 1950 | ported 9 November 2026 | capri_mod/market/luc.py | luc_market (setting market.luc_market): solved after each market solve (no feedback without lulucf_market, DEP-44); reproduces CAPRI's CAL transitions in the 45 regions within 1.2e-8 |
| luClassFinal_ | (rms,LUclass1) | 1938 | ported 9 November 2026 | capri_mod/market/luc.py | luc_market (setting market.luc_market): solved after each market solve (no feedback without lulucf_market, DEP-44); reproduces CAPRI's CAL transitions in the 45 regions within 1.2e-8 |
| FocLUC_ | (rms,LUCpos) | 1960 | ported 9 November 2026 | capri_mod/market/luc.py | luc_market (setting market.luc_market): solved after each market solve (no feedback without lulucf_market, DEP-44); reproduces CAPRI's CAL transitions in the 45 regions within 1.2e-8 |
| derivativeOfNormalLUC_ | (rms,LUCpos) | 1970 | not needed | capri_mod/market/luc.py | no transition of sim_ini_21730 has a normal or spike prior (all gamma); the build stops otherwise (tools/build/build_luc_market.py) |
| derivativeOfGammaLUC_ | (rms,LUCpos) | 1980 | ported 9 November 2026 | capri_mod/market/luc.py | luc_market (setting market.luc_market): solved after each market solve (no feedback without lulucf_market, DEP-44); reproduces CAPRI's CAL transitions in the 45 regions within 1.2e-8 |
| derivativeOfSpikeLUC_ | (rms,LUCpos) | 1987 | not needed | capri_mod/market/luc.py | no transition of sim_ini_21730 has a normal or spike prior (all gamma); the build stops otherwise (tools/build/build_luc_market.py) |

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
| FlipFlop_ |  | 3771 | replaced | zero objective (MARKET_IPOPT_DESIGN.md §7.2, decided) | CAPRI's formal objective of a square system; IPOPT as a feasibility solver, as CONOPT in CAPRI |

## Tariffs and TRQs

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| TRQImports_ | (RMTP,XXX) | 3142 | ported, other form | market/bilateral.py, trade_ad.py (stages 4-5) | CAPRI's 70 global quotas; flows from blocks without a bilateral quota plus the bilateral quotas' overfill (ncpcm); shift form: CAPRI's base import price plus the change of the rates (PORTS_STAGE4.md); DEP-33 removed 4 November 2026 |
| trqSigmoidFunc_ | (RMTP,RMTP1,XXX) | 3275 | ported, other form | market/bilateral.py, trade_ad.py (stage 4) | one sigmoid per pair of policy blocks on TradeFlowsAgg_, 130 bilateral quotas of every importer (EU 81, MOR 16, TUR 15, MED 11, NO 5, RUS 2); shift form; DEP-34, DEP-35, DEP-41 removed 4 November 2026 |
| tarSpec_ | (RMTP,RMTP1,XXX) | 3292 | ported, other form | market/bilateral.py, trade_ad.py (stage 4) | shift form; the smaller of the global and bilateral rate by ncpcm (stage 5) |
| tarSpecW_ | (RMTP,"Rw",XXX) | 3399 | ported, other form | market/bilateral.py, bilateral_solve.py (stage 5) | the global rates from the global sigmoid on TRQImports_; shift form |
| tarAdVal_ | (RMTP,RMTP1,XXX) | 3417 | ported, other form | market/bilateral.py (stage 4) | the ad valorem rate on the exporter's current price plus transport (impPrice_); DEP-36 removed 4 November 2026 |
| tarAdValW_ | (RMTP,"Rw",XXX) | 3475 | ported, other form | market/bilateral.py, bilateral_solve.py (stage 5) | as tarSpecW_ |

## Flexible levies and entry prices

| Equation | Domain | Line | Status | capri-mod | Note |
|---|---|---|---|---|---|
| prefTriggerPrice_ | (RMTP,RMTP1,XXX) | 3369 | ported, other form | market/bilateral.py BilateralCommodity.border_spec (stage 6) | the EU's and the UK's entry prices (APPL, CITR, TAGR, TOMA) and the EU's flexible levies (8 cereals and sugar) per pair of policy blocks at the pair's base-flow weighted CIF price; shift form; against p_flexLevy 'CAL' within 1.3 EUR/t (48 EU flows). Not in G1/G2a's CasADi systems yet (the default solve does not take the exact path for these commodities) |
| FlexLevyNotCut_ | (RMTP,RMTP1,XXX) | 3236 | ported, other form | market/bilateral.py BilateralCommodity.border_spec (stage 6) | the EU's and the UK's entry prices (APPL, CITR, TAGR, TOMA) and the EU's flexible levies (8 cereals and sugar) per pair of policy blocks at the pair's base-flow weighted CIF price; shift form; against p_flexLevy 'CAL' within 1.3 EUR/t (48 EU flows). Not in G1/G2a's CasADi systems yet (the default solve does not take the exact path for these commodities) |
| FlexLevy_ | (RMTP,RMTP1,XXX) | 3258 | ported, other form | market/bilateral.py BilateralCommodity.border_spec (stage 6) | the EU's and the UK's entry prices (APPL, CITR, TAGR, TOMA) and the EU's flexible levies (8 cereals and sugar) per pair of policy blocks at the pair's base-flow weighted CIF price; shift form; against p_flexLevy 'CAL' within 1.3 EUR/t (48 EU flows). Not in G1/G2a's CasADi systems yet (the default solve does not take the exact path for these commodities) |
| tarSpecIfEntryPrice_ | (RMTP,RMTP1,XXX) | 3204 | ported, other form | market/bilateral.py BilateralCommodity.border_spec (stage 6) | the EU's and the UK's entry prices (APPL, CITR, TAGR, TOMA) and the EU's flexible levies (8 cereals and sugar) per pair of policy blocks at the pair's base-flow weighted CIF price; shift form; against p_flexLevy 'CAL' within 1.3 EUR/t (48 EU flows). Not in G1/G2a's CasADi systems yet (the default solve does not take the exact path for these commodities) |
| EntryPriceDriver_ | (RMTP,RMTP1,XXX) | 3176 | ported, other form | market/bilateral.py BilateralCommodity.border_spec (stage 6) | the EU's and the UK's entry prices (APPL, CITR, TAGR, TOMA) and the EU's flexible levies (8 cereals and sugar) per pair of policy blocks at the pair's base-flow weighted CIF price; shift form; against p_flexLevy 'CAL' within 1.3 EUR/t (48 EU flows). Not in G1/G2a's CasADi systems yet (the default solve does not take the exact path for these commodities) |
