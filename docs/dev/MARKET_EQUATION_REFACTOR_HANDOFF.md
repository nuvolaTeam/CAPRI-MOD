# Handoff: the refactor of CAPRI's market equations (branch `refactor/market-equations`)

Written 20 November 2026 for the session that continues the second phase (Claude Code in the cloud). The plan is
docs/dev/MARKET_EQUATION_REFACTOR_PLAN.md (the project lead's, 20 November 2026); the rules are those of
docs/dev/EQUATION_REFACTOR_BRIEF.md and docs/dev/EQUATION_REFACTOR_HANDOFF.md section 7. The branch started from dev at
aa91c1c (the supply phase merged, 19e7679; the checks against star 3.0, aa91c1c).

## 1. Setting up

- CAPRI star 3.0 (the project lead's gams.zip of 17 June 2026: supply/supply_model.gms 5,557 lines,
  arm/market_model.gms 4,607) outside the repository, linked as capri_sources/gams (not versioned; the checks' test,
  capri_mod/tests/test_refactor_checks.py, finds it there).
- Before a block: `python tools/refactor/check_gams_quotes.py capri_sources/gams --expect supply/supply_model.gms=5557
  --expect arm/market_model.gms=4607` and `python tools/refactor/check_gams_citations.py capri_sources/gams`.

## 2. State

| block | what | check |
|---|---|---|
| M0 | the inventory of CAPRI's market-model equations (docs/dev/market_equations_inventory.csv; tools/refactor/market_equations_inventory.py, the supply tool's sibling for MODEL statements) and the Green Deal step's switches (docs/dev/market_equations_gd_switches.csv, each with its source); the rows empty in the step classified | docs and a tool; the quote and citation checks |
| M1 | the demand system: GLDemandFS_, GLDemandGS_, GLDemandGis_, XiS_ (market_model/demand.py) and CPri_ (prices.py), called by capri_mod/market/demand_ad.py; consFudge_ not written (the model's floor at 0) | the GL functions identical bit for bit (15 region sizes and the block's 2,035 cells: serialised algorithms, values, Jacobians); the captured market solves replayed bit for bit (the capture test's 2, the five-unit run's 21); the five-unit Green Deal run identical (15 lines of `$.meta.`, the reference's capture setting among them) |
| M2 | processing, feed, dairy and biofuels: ProcMargO_, ProcNQ_ (ProcNQ_margin, ProcNQ_price), ProcFudge_, ProcO_, procYield_, MaprFeed_ (market_model/processing.py); feedBlkPrice_, feedBlk_, FeedShareEqu_, FeedNQ_, FeedBal_ (feed.py); ProcMargM_, DairyNQ_, FatsProtBal_ (dairy.py); BiofFeedCost_, BiofFeedCostAgg_, Biof_, ProdBiof_, BiofPriceRel_, SupplyBiof_, biofDemshare_, biofDem_ (biofuels.py); called by processing_ad.py, feed.py, feed_ad.py, use_ad.py, dairy.py, dairy_ad.py, biofuel_ad.py. MaprBiof_ and prodQuantBiofBy_ stay running sums (ported as terms); CSugarPrice_ empty in the step; FeedFudge_ goes with ProdFudge_ to M3 (supply_system_ad.prod_fudge) | the CasADi functions a cold market solve builds (486) serialised and compared, the old code against the new: 484 identical, the other 2 differ between two runs of the same code (section 5); the captured solves replayed bit for bit (2 and 21); the five-unit Green Deal run identical; the full-EU run moved to the phase's end (section 3) |
| M3 | supply in the market, fudging and land: ProdNQ_ (ProdNQ_hess), yaniMarket_ (market_model/supply.py); ProdFudge_ (fudging.py; FeedFudge_ in its form); rentFromProdpriceLand_, LandSupplyMNL_, LndSupplyEqualsDemand_, LinkLuWithShares_, luClassFinal_ and luClassInitial_, FocLUC_ with derivativeOfGammaLUC_ (land.py); called by supply_ad.py, supply_system_ad.py, luc.py. ProdA_ ported as terms (eu_rows); NumeraireLand_ and LandSupplyRatio_ as LandSupplyMNL_; rmsYaniMarket_, derivativeOfNormalLUC_, derivativeOfSpikeLUC_ empty in the step; Yield_, LandAgrFromYld_, ScaleLandAgr_ and ProdPriceFudge_ not in the model (a recursive block); PPri_ moved to M4 (the price chain) | the module's CasADi functions after a cold solve (486) identical, the hash seed fixed; the assembled market system (plain and lifted with the fudge modes and the lifted use cells; the GD runs do not build it, market.bounds none) identical: its serialised functions, F and its Jacobian at the start for the three fudge modes; the captured solves replayed bit for bit (2 and 21); the five-unit Green Deal run identical |
| M4 | trade and prices: SupBalM_, arm2QuantShares_, domSalesShares_, importShares_ (market_model/armington.py); impPrice_ (its exporter-price part), arm2PriceAgg_ and arm1PriceAgg_ (with their terms), PMrk_, MarketPriceAgg_'s weights (prices.py); called by the trade blocks' three forms (bilateral.py, trade_ad.py, trade_system_ad.py), import_prices_ad.py and market_system_ad.py. ArmBal1_, expQuant_, TradeFlowsAgg_ and PPri_ ported as terms; tradeFlowFudge_ and HicksNeutral_ empty in the step (modArmington off); FlipFlop_ CAPRI's solver device; nonDoubleZeroExports_ moved to M5 (the export subsidies) | the module's 486 CasADi functions and the assembled market system identical to M3's (PYTHONHASHSEED=0); the captured solves replayed bit for bit (2 and 21), which run the trade blocks' NumPy form; the five-unit Green Deal run identical |
| M5 | the border measures: trqSigmoidFunc_ (with its NumPy twin), tarAdVal_, tarSpec_ (with the smaller of the bilateral and the global rate), tarAdValW_, tarSpecW_, prefTriggerPrice_, EntryPriceDriver_, tarSpecIfEntryPrice_ (with its NumPy twin), FlexLevyNotCut_, FlexLevy_ (market_model/border.py); called by bilateral.py (_sig, _trq_rates, border_spec, _TrqCells), import_prices_ad.py, trade_ad.py, trade_system_ad.py. TRQImports_ ported as terms; the 17 rows of the intervention stocks and the subsidised exports (nonDoubleZeroExports_ among them) empty in the step (no INTM, STKS, FEOE_max in CAPRI's 2030 data) and not in the model | the module's 486 CasADi functions and the assembled market system identical to M4's (PYTHONHASHSEED=0); the captured solves replayed bit for bit (2 and 21); the five-unit Green Deal run identical |
| C0 | the inventory of CAPRI's calibration systems (docs/dev/calibration_equations_inventory.csv; tools/refactor/calibration_equations_inventory.py: the MODEL statements of the fertiliser priors m_fertDist and m_dualFertDist, the land supply estimation, the land-use change estimation and m_calibKVT, nested models and $include files followed, plus the PMP terms and the Armington shares, which CAPRI writes as assignments); 89 rows, each with where CAPRI runs it and what the model does | docs and a tool; the quote and citation checks |
| C1 | the Armington calibration: v_arm2Price, arm1Price_, p_dpCESTrade_bilateral, p_dpCESTrade_domestic, p_dpCESTrade_RW (capri_mod/market/equations/cal_armington.py, CAPRI's arm/cal_armington.gms l. 39-64 and arm1Price_), called by bilateral.py BilateralCommodity.calibrate | the calibrated arrays of the 57 bilateral commodities (beta, dd, dm, PM0, PA0, S0, D0, X0: 456) identical bit for bit; the captured solves replayed bit for bit (2 and 21); the five-unit Green Deal run identical |
| P | the manure pool market: e_mPoolSurplus and p_mTradeAddCost (market/equations/manuremarket/declare_manure_market.py), p_mPoolSupConst and p_stepWeights_average (simu_manure_market.py), called by coupling/manure.py (_clear_pool_capri, _clear_pool); the pool balances and the QP's objective ported as terms; m_mPoolMarketCal not needed in the model's form (section 10) | the pool market's clearings on synthetic inputs (N, P, K x 4 seeds x 3 steps: prices, shipments, the kept state) identical bit for bit; the captured solves replayed bit for bit (2 and 21); the five-unit Green Deal run identical (the manure trade on) |

## 3. The gate's references (at the phase's starting commit 444a47f, worktree outside the repository)

- runs/mkt/cap_test_ref: the capture test's two solves (a cold one at CAPRI's base supply rows, a warm one with FR's
  soft wheat x 1.1; capri_mod/tests/test_market_capture.py), replayed with tools/check/replay_market.py;
- runs/mkt/gd5_ref.pkl with its market solves (runs/mkt/cap_gd5_ref): the five-unit Green Deal run (DE21, IT32,
  PL51, PL61, PT18; capri_mod/settings/capri_comparison.toml);
- the full-EU Green Deal run with the same settings: at the phase's end, at 444a47f and at the final code, compared once
  (the project lead, 20 November 2026: no full-EU run before the end; it replaces the plan's runs after M2, M4 and M5).

## 4. What M0 found

- m_globMarket (arm/market_model.gms l. 4243) lists 123 equations, 47 of them in the nested m_bevFunctionsMarket
  (l. 4150); m_netTrade (l. 4218) adds 5 of its own to the nested model (stockChg_, mrkBal_, arm1PNetTrade_, wldMarket_,
  ntrd_) and shares 6 with m_globMarket. 112 of m_globMarket's rows are listed under switches that hold in the step.
- **m_netTrade's place**: CAPRI solves it only in arm/ini_netTradeModel.gms, which no file of star 3.0 includes: not in
  the step; its five own rows are classified empty.
- **supremaMrk is on** in star 3.0 (capmod/set_global_variables.gms l. 386, unconditional): the land rows the plan lists
  for M3 (LandSupply_, LandAgrFromXX_, LandAgrTmp_, LandAgr_, LandNagr_, LandTypesNagrTmp_, LandTypesNagr_) are not in
  the step, the SUPREMA land rows are (LandSupplyMNL_, LandSupplyRatio_, NumeraireLand_, LandAgrFromYld_,
  ScaleLandAgr_, LndSupplyEqualsDemand_, rentFromProdpriceLand_; capri_mod/market/luc.py already names
  LandSupplyMNL_). M3's list follows the inventory.
- **luc_market and lulucf_market are on** (l. 395, 406: supremaMrk, MARKET_M and REPORTS_ENV on). The market's LUC rows
  (LinkLuWithShares_, luClassInitial_, luClassFinal_, FocLUC_ and the density rows, non-EU regions) are in the step
  (capri_mod/market/luc.py); the 15 LULUCF rows are empty: no LULUCF carbon tax in the step (oth00: oth_pol.gms not
  included, greendeal_scenarios.gms l. 184), so v_glucCostPerHa is fixed (arm/set_prestep_bounds.gms l. 51).
- crpInputInMrk, modArmington (extendedKVT) and capri_sr are off: inputMarket_, InpPriceFudge_, transition_ and
  privStockFin_ are not in the step. The META of CAPRI's Green Deal result (not at hand in this session) is to
  confirm crpInputInMrk and modArmington, which star 3.0 leaves at their defaults.
- Left for M1-M5: 97 rows of the step without a status (the inventory's planned_module: demand 5, feed 6, dairy 3,
  processing 6, biofuels 11, supply 3, land 15, fudging 2, aggregation 1, armington 7, prices 8, border 11,
  intervention 18, objective 1).

## 5. What M2 found (for the main line; nothing fixed)

- **Nondeterministic ProdNQ_ rows of the EU regions**: of the CasADi functions a cold market solve builds, the two of
  `_nq_rows_cache[('eu', 'EU_WEST')]` and `[('eu', 'EU_EAST')]` (capri_mod/market/supply.py _nq_rows,
  supply_ad.build_rows) serialise differently between two processes running the same code (the other 484 do not).
  The cause: their rows follow MarketModule.EU_MARKET_SUPPLY (market_module.py l. 365, a frozenset of strings), whose
  order changes with Python's hash seed. Each row is its own dot product and the caller takes the rows' order from the
  same function, so the values do not change (the solves replay bit for bit); only the layout does. sorted() would
  fix the order; left for M3, which moves ProdNQ_.
- **Two forms of CAPRI's smooth max (ncpcm)**: ProcFudge_ (processing_ad.py, dairy_ad.py) writes
  max(0, u) + log1p(exp(-|u|)); the assembled system's lifted cells take supply_system_ad.prod_fudge's
  fmax(q, 0) + z log1p(exp(-|q| / z)). Equal in exact arithmetic, they round differently. M3 (ProdFudge_, FeedFudge_)
  is to keep both as they are and say which system uses which.
- **A second form of CPri_**: biofuel_ad.py demand_function writes the biofuel consumer price with the factors in the
  other order and a floor of 1e-6 (biofDemshare_'s docstring); M1's CPri_ is not called there, as the order changes
  the rounding.
- **A third form of ProcNQ_'s own-price term**: biofuel_ad.py proc_function (the non-fuel processing of the biofuel
  feedstocks) writes it apart from ProcNQ_price.
- **prodQuantBiofBy_ in two forms**: the DDGS sum is a NumPy sum in biofuel.py biofuel_state and a CasADi dot in
  supply_system_ad.py; they round differently. MaprBiof_ likewise stays a running sum in both.
- **CSugarPrice_ is empty**: its domain needs DATA(QUTS, SUGA) > eps; CAPMOD sets the sugar quotas to 0 + eps from 2017
  (policy/reformsugarquotas.gms l. 136-142).
- Left for M3-M5: 66 rows of the step without a status.

## 6. What M3 found (for the main line; nothing fixed)

- **CAPRI's step solves the asymmetric land supply**: p_useSymmetricMNL = 0 outside the baseline (arm/market_model.gms
  l. 216-218), so the step has NumeraireLand_ and LandSupplyRatio_ (l. 1758-1790, the numeraire chosen at the start
  values, arm/set_start_val.gms l. 617-621), not LandSupplyMNL_, which the model writes (with the exponents shifted by
  their largest at the current rents). Equal in exact arithmetic where the commitment term DATA LEVL_1 is 0: to
  confirm on the step's data. The inventory's in_gd2030_step follows the $if switches only, so it counts all three
  rows (a parameter condition, not a switch).
- **A recursive block not in the model**: Yield_, LandAgrFromYld_, ScaleLandAgr_ (l. 1795-1861) with ProdPriceFudge_
  (l. 2378-2392) give the yields and land use per product outside the EU; v_yield, v_landAgrTmp, v_landAgr and
  v_prodPricePos enter no other row of the step. No feedback on the market; a report the model does not have.
- **The crude oil cost term of ProdNQ_** (p_oilCostShare x DATA UVAG CRDO PercentageChange, l. 1555) is not in the
  model; the step sets no oil price change (only pol_input/liaise/liaise_scen.gms l. 464-465 and
  scen/macro_environment/oil_price_50.gms l. 21 do), so it vanishes there; a scenario with an oil price change needs it.
- **ProdNQ_ at the EU market region's level**: one measured Hessian per EU market region (the sum of its member
  states'), CAPRI's ProdNQ_ per member state summed by ProdA_; known (the market audit), listed for completeness.
- **Two forms each** (kept, each where it is): LandSupplyMNL_ in CasADi (the land market) and NumPy (luc.py's report);
  the land demand's base in supply.py noneu_land_solve (NumPy) and market_system_ad.py (CasADi); ProdNQ_'s milk terms
  in NumPy in supply.py and the K83 units' rows inline in supply_system_ad.py.
- **The EU ProdNQ_ rows' order** (section 5) confirmed: with Python's hash seed fixed (PYTHONHASHSEED=0) the 486
  functions are identical old against new, the EU rows included.
- **PPri_** moved to M4: the producer price equals the market price ratio times the base (bilateral.py prices, Pd =
  Pd0 r) and the support terms are in ProdNQ_'s parameters; it belongs with PMrk_ and MarketPriceAgg_.
- Left for M4-M5: 44 rows of the step without a status.

## 7. What M4 found (for the main line; nothing fixed)

- **The trade blocks in three forms**: the Armington nests and the supply balance are written in NumPy (bilateral.py,
  the default solve), CasADi per region (trade_ad.py, the trade function with its exact Jacobian) and CasADi per cell
  (trade_system_ad.py, the assembled system). They now call the same elementwise functions; the sums over the flows
  stay each form's (NumPy's sum, CasADi's sum1, a running sum), so the forms round differently. A single form would
  need a decision of the main line (the default solve's speed against one code path).
- **MarketPriceAgg_'s average in two forms** (bilateral.py border_spec, NumPy; import_prices_ad.py, CasADi): the same
  weights (mpagg_weights, now MarketPriceAgg_weights), two sums.
- **PMrk_'s floor**: the default solve floors the market price ratio of a region without production at 1e-3
  (bilateral.py pmrk_ratios); the assembled system's PMrk_ row does not (market_system_ad.py, as its comment says).
- **PPri_ held in ProdNQ_'s parameters**: with the support per tonne fixed and the margin relative (additivePPriMargin
  off), the producer price's change is the market price's times the margin; the model folds it into ProdNQ_'s h. A
  scenario that changes the support (PSEi, PSEd, AREP) would need PPri_ written out.
- **The modified Armington system is off in the step**: v_gammaCES, v_Hicks and pv_theta fixed at 1 and
  p_arm2Commit 0 (arm/cal_armington.gms l. 82-89, market_model.gms l. 225), so HicksNeutral_ and tradeFlowFudge_ are
  empty and importShares_ and arm2PriceAgg_ are the standard CES forms the model writes.
- **FlipFlop_** (v_dummy =E= 10) is CAPRI's device to solve its square system as an NLP; the model solves the square
  system (no row).
- Left for M5: 28 rows of the step without a status (border 11, intervention 17, nonDoubleZeroExports_ among them).

## 8. What M5 found (for the main line; nothing fixed)

- **Every row of the step classified**: of the 112 rows m_globMarket lists under the step's switches, 57 ported as
  functions, 8 as terms of their callers, 3 in another row's form (NumeraireLand_ and LandSupplyRatio_ as
  LandSupplyMNL_, FeedFudge_ as ProdFudge_), 38 empty in the step, 4 not in the model (the recursive yields block), 1
  CAPRI's solver device (FlipFlop_), 1 not written (consFudge_, M1).
- **The intervention stocks and subsidised exports are empty in the step** (17 rows): their domains need INTM, STKS or
  FEOE_max, which CAPRI's 2030 data do not have at the calibration point (MARKET_EQUATIONS_INVENTORY.md, checked
  1 November 2026 in data_market_1730defaulta.csv and the result's dataOut; the Green Deal policy files set none);
  capri_mod/policy/policy_module.py l. 264 notes them as to be ported. A scenario with intervention would need them;
  this session could not check the step's data itself (no copy of sim_ini_21730 here).
- **The border measures in two forms**: NumPy (bilateral.py; the default solve, with the quotas' trials of
  _TrqCells) and CasADi (import_prices_ad.py, trade_ad.py, trade_system_ad.py). The rates, the entry prices' driver and
  the levies are now one function each; the sigmoid and tarSpecIfEntryPrice_ have a NumPy twin (np.exp, np.clip
  against CasADi's exp, fmin, fmax), and CAPRI's ncpcm has two forms (NumPy's logaddexp, CasADi's fmax and log1p),
  passed to the functions as an argument. The quotas' diagnostics (trq_arguments, trq_equation_gap) write the sigmoid
  a third time.
- **The sigmoid's argument arranged otherwise than CAPRI's**: slope (fill / Q - 0.97) against CAPRI's slope / Q (fill -
  0.97 Q) (equal in exact arithmetic), clipped at +-60.
- **The quotas solved by bisection in the default solve** (bilateral.py trq_solve, an outer fixed point with the
  market); the assembled system has them as equations (trade_system_ad.py). Known (MARKET_TRQ_PORT.md).

## 9. What C0 found (the calibration systems; for the main line, nothing fixed)

- **None of CAPRI's calibration systems runs in the Green Deal step.** The supply calibration (the PMP terms, the
  land supply estimation; supply/calibrate_supply.gms) runs with BASELINE on (capmod.gms l. 1416-1424); the
  fertiliser calibration m_fertDist with BASELINE on too (capmod/def_fert_and_requirements.gms exits for a scenario at
  l. 173, before l. 903); the Armington shares when the simulation's start point sim_ini is generated
  (arm/market1.gms l. 625, from capmod/create_sim_ini_gdx.gms l. 266, capmod.gms l. 646, generateSimIni). The step
  starts from their results.
- **What the model does with each** (the inventory's status): 47 rows are equations of the simulation model as well
  (the supply phase's: m_fertDist and m_dualFertDist share the nutrient rows, m_LandSupply the land rows, the LUC
  estimation N14b's); 32 rows' results are read from CAPRI (the fertiliser priors' posterior modes,
  tools/build/build_fert_dist_priors.py; the land supply's estimated terms p_pmpQuadLandTypes,
  tools/build/build_land_market.py); the PMP's quadratic terms are read from the baseline's pmppar files (pmp_source
  capri2030, the default; build_pmp_recipe.py ports CAPRI's recipe as the option pmp_source recipe) and the linear
  terms recalibrated by the model's own method (CapriRegionalNLP.calibrate: a least-squares fit of the multipliers
  at the base, not CAPRI's duals of the baseline LP); the Armington shares are recomputed by the model at the start
  of every run (BilateralCommodity.calibrate, CAPRI's arm/cal_armington.gms l. 40-50: C1).
- **m_dualFertDist is not solved in star 3.0**: its includes (fert/solve_only_inner_fertdist_model.gms) are commented
  out in supply/pmp.gms l. 256 and 273; its inner model's equations are the simulation model's (inner_fert.py).
- **m_calibKVT is off** in the configuration (modArmington off: arm/cal_armington.gms exits at l. 89).
- **The LUC estimation in another form**: CAPRI's start maximises the log posterior density (m_estLUCfromMaxDens,
  supply/prep_sim_luc.gms l. 472-568); the model (environmental/luc.py, N14b) solves its first-order conditions,
  CAPRI's test model m_estLUCfromFOC: the same optimum where the bounds do not bind (to confirm where they do).
- **C1 moved the one calibration the model recomputes in every run** (the Armington shares); the other systems'
  results are data the model reads (tools/build), and CapriRegionalNLP.calibrate's least-squares multipliers are the
  model's own method, with no CAPRI equation to name. The PMP recipe (build_pmp_recipe.py, capri_pmp.py, the option
  pmp_source recipe) ports CAPRI's assignments (supply/define_pmp_terms.gms, supply/pmp_terms/*.gms) in a builder;
  its steps could be named after CAPRI's files in a later block if the main line uses it.
- **Not in this inventory** (CAPRI's other calibration models, outside the plan's list): the market data's
  calibration m_calMarketBas, m_calMarketFin (arm/cal_models.gms), m_calMarketLnd(2) (arm/define_land_params.gms),
  the trimming of the market's elasticities m_trimLU, m_trimElas, m_trimDem (arm/trim_elas_decl.gms), the TRQ and
  intervention trimming (m_fitTrq, m_trimInterv); the model reads their results with CAPRI's market data.

## 10. What P found (the manure pool market; for the main line, nothing fixed)

CAPRI solves both pool models in the Green Deal step (ManureTradeNEW on, the META of the Green Deal result;
manuremarket/declare_manure_market.gms exits only with BASELINE on, l. 19): m_mPoolMarketCal once at the step's start
(l. 344-451, the price wedges that make the baseline trade an equilibrium), m_mPoolMarket in every iteration
(simu_manure_market.gms l. 160, from capmod.gms l. 1496). The model (coupling/manure.py, docs/MANURE_MARKET.md,
docs/dev/MANURE_POOL_PORT.md; outer_loop.manure_pool_form "capri", the default):

| CAPRI's row | model | status |
|---|---|---|
| e_mPoolSurplus (l. 114-127) | declare_manure_market.e_mPoolSurplus: the QP's coefficients of minus the surplus | ported |
| e_mPoolExcessSupply (l. 99-104), e_mPoolClear (l. 130-140) | one balance row per pool (the excess supply substituted); the pool price its dual | ported (terms) |
| e_mPoolBenefits (l. 153-157) | the QP's objective: the surplus less the trade costs between the pools (Clarabel) | ported (terms) |
| e_mPoolPriceCal, e_mPoolPriceEq, e_mPoolCSCal, e_mPoolObjeCal (m_mPoolMarketCal, l. 168-196) | none | not in the model (not needed in its form) |
| p_mPoolSupConst (simu_manure_market.gms l. 87-89) | simu_manure_market.p_mPoolSupConst | ported |
| the step-weighted prices (l. 76-78, 222-227; capmod/define_stepWeights.gms l. 40-41) | simu_manure_market.p_stepWeights_average | ported |
| p_mTradeAddCost (l. 427-431) | declare_manure_market.p_mTradeAddCost | ported (the price gap term zero) |

- **No calibration of the pool market**: the model's net exports and pool prices are the deviations from CAPRI's base
  trade, zero at the base, which is an equilibrium; CAPRI's calibration wedges (v_mPoolPriceCal) and the fixed
  third-country exports drop out. Equal to CAPRI's form where CAPRI's calibration reproduces its baseline exactly
  (its objective, the wedges' squares plus a penalty on the complementarity gap, is zero there).
- **The trade cost constants are the model's own calibration**: from the reduced costs of each region's trade columns
  at its solution (CAPRI: calibrated at the base, supply/define_manure_trade_costs.gms), so the market's first-order
  conditions hold at the regions' solutions.
- **A QP (Clarabel) for CAPRI's NLP (CONOPT)**: the same problem, convex where the excess-supply slopes are positive or
  outweighed by the trade cost slopes (the run stops otherwise); one region and nutrient of CAPRI's 2030 data (manure_pool_market_2030.csv) has a negative slope.
- **The excess supply's slope in two unit conventions** (outer_loop.manure_pool_es_slope: "capri_code", CAPRI's code
  with trade in kt and supply in t, the default; "capri_doc", one unit): a setting the main line chose, kept.
