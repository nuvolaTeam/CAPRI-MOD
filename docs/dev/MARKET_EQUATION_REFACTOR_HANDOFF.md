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

## 3. The gate's references (at the phase's starting commit 444a47f, worktree outside the repository)

- runs/mkt/cap_test_ref: the capture test's two solves (a cold one at CAPRI's base supply rows, a warm one with FR's
  soft wheat x 1.1; capri_mod/tests/test_market_capture.py), replayed with tools/check/replay_market.py;
- runs/mkt/gd5_ref.pkl with its market solves (runs/mkt/cap_gd5_ref): the five-unit Green Deal run (DE21, IT32,
  PL51, PL61, PT18; capri_mod/settings/capri_comparison.toml);
- the full-EU Green Deal run with the same settings and its captured solves: the reference of M2, M4 and M5 and the
  captures every block replays.

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
