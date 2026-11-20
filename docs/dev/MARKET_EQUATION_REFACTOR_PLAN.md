# Plan: CAPRI's market equations as named functions (the refactor's second phase)

Written 20 November 2026 for the session that continues the equation refactor (Claude Code in the cloud), after the
supply side's phase (blocks N1-N15) was merged into dev. The rules of the work are those of
docs/dev/EQUATION_REFACTOR_BRIEF.md and docs/dev/EQUATION_REFACTOR_HANDOFF.md section 7 (the project's instructions
and the project lead's standing rules); this file says what the second phase covers, in which order, and what changed
from the first.

## 1. Decisions (the project lead, 20 November 2026, 13:23)

- Scope and order: CAPRI's market model first (blocks M0-M5 below), then CAPRI's calibration systems (C), then the
  manure pool market (P). CAPTRD's equations wait until CAPTRD-MOD stands (the plan's step 8); CAPREG is not in scope.
- Timing: now, in parallel with the main line, on a branch of its own, `refactor/market-equations`, started from dev at
  the merge of the supply phase. dev is merged into it after each push to dev (a merge, never a rebase or a
  force-push: the branch is public); the project lead decides its merge into dev.
- The quote and citation checks are repository tools (section 4), run at every block.

## 2. The CAPRI copy: star 3.0, checked before anything else

The first phase quoted and cited CAPRI from course_capri_git/gams, which is CAPRI's July 2026 release (the Docker image
caprithuenen/capri:latest of 30 July 2026), not star 3.0; it was found and corrected at the merge
(docs/dev/EQUATION_REFACTOR_HANDOFF.md, the correction at its top). This phase reads **CAPRI star 3.0 only**: the
project lead's gams.zip of 17 June 2026 (the code of the project lead's runs; gams__3_.zip differs from it only by the
CONOPT -> IPOPT edits). The project lead provides it; it is not in the repository or on Hugging Face (the raw dataset
holds CAPRI's data as Parquet, not its code). Before the first block:

    python tools/refactor/check_gams_quotes.py GAMS_DIR --expect supply/supply_model.gms=5557 --expect arm/market_model.gms=4607

stops unless the copy's files have star 3.0's line counts. The newer releases (5,631 lines in supply_model.gms) are not
to be used, not even for a comparison: the move to a newer CAPRI is a project of its own, after the model is validated
(the project lead, 20 November 2026).

## 3. What the market model is

CAPRI's market simulation solves `m_globMarket` (arm/market_model.gms l. 4243), which nests `m_bevFunctionsMarket`
(l. 4150): 123 equations in star 3.0, 47 in the nested model and 76 more. About 33 are listed only under switches
that may be off in the 2030 Green Deal step (%supremaMrk%, %luc_market%, %lulucf_market%, %crpInputInMrk%,
%capri_sr%, %modArmington% == extendedKVT); M0 settles each from the step's own records (the META of the Green Deal
result, capmod/set_global_variables.gms, the policy files), as the first phase's switch table did, not by assumption.
`m_netTrade` (l. 4218, 11 equations) is a separate model; M0 says where CAPRI solves it and whether the model ports it.

The model's market is capri_mod/market/ (about 10,100 lines): the CasADi systems (*_ad.py: demand, processing, feed,
dairy, biofuel, supply, trade, import prices, use, market_system_ad.py, trade_system_ad.py, supply_system_ad.py), the
bilateral trade (bilateral.py, bilateral_solve.py), the market chain and its Newton-Krylov solver (market_chain.py,
market_nk.py), the bounds (market_bounds.py, DEP-50) and the calibration (calibration.py). 47 of the 90 equations that
are not tied to those switches are named somewhere in that code; not named yet: the demand system (GLDemandFS_,
GLDemandGS_, GLDemandGis_, XiS_, consFudge_), the Armington shares and price aggregates (arm2QuantShares_,
domSalesShares_, importShares_, tradeFlowFudge_, HicksNeutral_, arm1PriceAgg_, arm2PriceAgg_, ProdPriceFudge_,
expQuant_, nonDoubleZeroExports_, FlipFlop_), ProdA_, Yield_, rmsYaniMarket_, CSugarPrice_, the market's land rows
(LandSupply_, LandAgr_ and the others) and the intervention stocks and export subsidies (buyingToIntervStock_ to
releaseShares_, stockChangeRM_, EXPs_, valSubsExports_).

## 4. The checks at every block

1. The gate (a move, not a change):
   - the market's solves bit-identical: captured market solves (MarketModule._solve_captured; a cold first solve and
     a warm one at a changed supply, as capri_mod/tests/test_market_capture.py does, and solves captured in a full-EU
     Green Deal run at the block's starting commit) replayed on the moved code with tools/check/replay_market.py, bit
     for bit; and for each system a block touches, its residual vector and Jacobian at those states;
   - one five-unit Green Deal run (tools/run/run_f2f_2030.py --scenario greendeal2030 --regions ...) identical to the
     run at the block's starting commit, apart from the run's metadata (tools/check/compare_pickles_exact.py);
   - at the end of M2, M4 and M5 the full-EU Green Deal run with capri_mod/settings/capri_comparison.toml identical to
     the one at the phase's starting commit (metadata aside).
2. The quotes: `python tools/refactor/check_gams_quotes.py GAMS_DIR FILES --expect ...` (section 2): every quoted GAMS
   block in the changed files appears in star 3.0's text, its first cited line within 3 lines of the quote; every
   GAMS-like line outside a block appears in the copy. Add capri_mod/market/equations/ to its default files (the tool
   already maps market/equations/ to arm/market_model.gms).
3. The citations: `python tools/refactor/check_gams_citations.py GAMS_DIR`: every line citation next to an equation's
   name holds that equation's definition in star 3.0 or lies within it.
4. The full suite after M2, after M5 and before the phase's merge (test_capri.py in three parts, the other files one by
   one, as the main line runs it); the pre-commit checks of the main line (tools/check/make_*.py --check,
   validate_data.py, check_doc_coverage.py, flake8 E9/F63/F7/F82, test_portable_paths.py, test_run_manifest.py) at
   every commit.

## 5. The blocks

The layout follows the first phase: capri_mod/market/equations/market_model/<block>.py, one module per block of
arm/market_model.gms (the file's own banners), each equation a function with CAPRI's name, its GAMS statement in the
docstring (with file and star 3.0's lines), this project's notation and the departures; the systems (*_ad.py,
bilateral.py, ...) call the functions.

| Block | CAPRI's equations | The model's code now |
|---|---|---|
| M0 | the inventory: docs/dev/market_equations_inventory.csv, built by tools/refactor/supply_equations_inventory.py extended to a MODEL statement (or a sibling tool), with the Green Deal step's switches (docs/dev/market_equations_gd_switches.csv, each with its source); m_netTrade's place | docs only |
| M1 | the demand system: GLDemandFS_, GLDemandGS_, GLDemandGis_, XiS_, consFudge_, CPri_ | demand.py, demand_ad.py |
| M2 | processing, feed and biofuels: ProcO_, MaprFeed_, ProcMargO_, ProcNQ_, ProcFudge_, procYield_, ProcMargM_, CSugarPrice_, FeedNQ_, FeedFudge_, FeedBal_, feedBlkPrice_, feedBlk_, FeedShareEqu_, DairyNQ_, FatsProtBal_, Biof_, prodQuantBiofBy_, ProdBiof_, MaprBiof_, SupplyBiof_, BiofPriceRel_, BiofFeedCost_, BiofFeedCostAgg_, biofDemshare_, biofDem_ | processing_ad.py, feed.py, feed_ad.py, dairy_ad.py, biofuel.py, biofuel_ad.py |
| M3 | supply in the market and land: ProdNQ_, ProdA_, ProdFudge_, yaniMarket_, rmsYaniMarket_, Yield_, PPri_, LandSupply_, LandAgrFromXX_, LandAgrTmp_, LandAgr_, LandNagr_, LandTypesNagrTmp_, LandTypesNagr_ (and the SUPREMA land rows if M0 finds them in the step) | supply.py, supply_ad.py, supply_system_ad.py, luc.py |
| M4 | trade and prices: arm2QuantShares_, domSalesShares_, importShares_, tradeFlowFudge_, HicksNeutral_, arm1PriceAgg_, arm2PriceAgg_, impPrice_, PMrk_, ProdPriceFudge_, MarketPriceAgg_, SupBalM_, ArmBal1_, expQuant_, nonDoubleZeroExports_, TradeFlowsAgg_, FlipFlop_ | bilateral.py, bilateral_solve.py, trade_ad.py, trade_system_ad.py, market_system_ad.py, use_ad.py |
| M5 | border measures, intervention stocks, export subsidies: TRQImports_, trqSigmoidFunc_, tarSpec_, prefTriggerPrice_, FlexLevyNotCut_, FlexLevy_, tarSpecIfEntryPrice_, EntryPriceDriver_, tarSpecW_, tarAdVal_, tarAdValW_; buyingToIntervStock_, probMarketPriceUnderSafetyNet_, releaseFromIntervStock_, releaseFromIntervStock1_, intervStockLevel_, intervStockChange_, unitValueExports_, buyingRM_, buyingRMNum_, releaseRM_, releaseRMNum_, buyingShares_, releaseShares_, stockChangeRM_, EXPs_, valSubsExports_ | import_prices_ad.py, trade_ad.py, bilateral.py; the stocks and subsidies: M0 says whether they are in the step and ported |
| C | CAPRI's calibration systems: the PMP (supply/pmp.gms, m_pmp), the fertiliser priors (m_dualFertDist, m_dualFertDistFOC), the land supply estimation (supply/declare_calibration_models_for_land_supply.gms; N14b did the LUC estimation's own rows), the market calibration (m_calibKVT, arm/market_model.gms l. 4593) | capri_regional_nlp.calibrate, the builders of the PMP and priors (tools/build), calibration.py, environmental/luc.py |
| P | the manure pool market: m_mPoolMarket, m_mPoolMarketCal (manuremarket/declare_manure_market.gms l. 198-207) | the manure trade (K164, K167): supply and market code to locate in M0 |

The order inside a phase may change where a block's code is shared (the systems call each other); each block's
commit says which functions moved and which gate it passed.

## 6. What each block hands to the main line

As in the first phase (KNOWN_ISSUES K189 is its list): the block fixes nothing; it lists in the inventory's notes,
with their evidence, the rows not in the model, the rows the model writes that CAPRI's step has not, and the porting
differences, and the handoff collects them for the main line to measure and rank. A difference that looks large (a
price or a balance of the Green Deal step) is reported when found, not at the end.

## 7. Not in scope

The supply side (done, N1-N15); CAPTRD (after CAPTRD-MOD); CAPREG; changes of results; a newer CAPRI release.

A rule for later (the project lead, 20 November 2026): the CAPRI logic ported as GAMS assignments, not equations (the
emission accounts of envind/gases.gms, the premium rules, the nutrient-need updates of fert/fertned.gms, the baseline
projection rules), gets the same treatment: one named function per CAPRI statement block, its GAMS text quoted, with
CAPRI's names, file and lines, so that tools/refactor/check_gams_quotes.py and check_gams_citations.py check it against
star 3.0 as they check the equations. New code follows it from now on; the assignments already ported are a phase of
their own, after this one.
