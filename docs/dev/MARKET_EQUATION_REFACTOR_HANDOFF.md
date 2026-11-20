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
