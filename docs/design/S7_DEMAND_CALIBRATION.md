# S7: the market's demand calibration in CAPRI's form (design)

Status (9 November 2026): built and the model's only form (KNOWN_ISSUES K120, K125): build steps 1-4 done, the "supply" form and its setting removed; step 5, the scenario-shifter layer, not built. Written as a design on 5 November 2026: Section 1 completed 6 November 2026 (arm/prep_market.gms,
CAPRI's online documentation, checked against the code). Decided by the project lead the same day: the baseline demand
recalibration (register DEP-5) is removed, soon (MODEL_CONTENT_PLAN §14 item 12, decision log). This note says what
CAPRI does, what capri-mod does instead, what the change touches, how it is checked, and the questions left.

## 1. CAPRI's form

Two separate steps, in CAPRI star 3.0 (`gams/` of allgms):

1. **Once, before the simulation steps: the market calibrated at the calibration point.** arm/market1.gms: in the
   baseline-calibration run (%BASELINE%==ON) arm/data_cal.gms calibrates the market model's behavioural functions
   (l. 275); in a simulation run arm/load_cal.gms loads that calibration (l. 248), and arm/cal_Armington.gms and
   arm/modArmington.gms calibrate the Armington system at the calibration point (l. 617-642). load_cal.gms (read in
   full) loads the calibration point from baseline\data_market_<bas><sim>...gdx: DATA_CAL at "CAL", the trade flows,
   import prices, quotas, transport costs and the behavioural functions' correction factors, and sets the current
   state to it (DATA(...,COL_STORE,...,"CUR") = "CAL"; the feed at "Y" and "TRD" = "CAL"). The file held for 2030 is
   data_market_1730 (docs/EXTERNAL_SOURCES.md). It is written by arm/define_land_params.gms l. 1424 with the content
   data_cal.gms prepares. Not yet read line by line: data_cal.gms (to do before building, section 4.1).

   **Then, once per run (baseline reproduction and scenarios alike), before the iterations** (arm/prep_market.gms, read
   6 November 2026): the scenario's shifters are applied to the calibration point (l. 437-627: demand shifts and the
   like), and at that shifted point, at the calibration prices, the behavioural functions' constants are set again
   (l. 635, arm/cal_cnst_terms.gms, read in full): the supply functions' p_cnstNQSupp for every RMS, the processing
   functions' p_cnstNQProc, the feed demand p_cnstNQFeed of the regions without supply models (not rmssup), the dairy
   processing p_cnstNQDairy; and the Generalized Leontief demand's commitment terms are solved again so that the
   demand system returns the shifted quantities at those prices (l. 749, arm/recalibrate_commitments.gms,
   m_trimGLCommits). The market is then solved at that point as a test (l. 917-1201). So a scenario's demand shift
   enters by moving the point the demand system is calibrated to, every run.
2. **Every simulation step: only the supply side recalibrated to the supply models** (arm/simu_calibration_to_supply.gms,
   included by arm/simu_market.gms l. 39 when the supply models are on), for every country with supply models: RMSSUP,
   the EU member states, Norway, Turkey and the five Western Balkan units (sets of sim_ini_21730; CAPRI's documentation,
   "Linking the different modules", says the same). Read in full, the file shifts:
   - the supply functions' constants, p_cnstNQSupp, so that at the current prices the market supply function returns
     the supply models' production aggregated to member states (l. 360-368, from DATA(RMSSUP,"Prod",XX,"CUR") set
     l. 166-203 or 208-255);
   - the feed bulks' constants, p_feedBlkCnst, so that the feed demand returns the supply models' feed use
     (l. 264-275; log-linear: log of the bulk minus the elasticities times the log of the bulk prices and of the supply
     products' prices), each single feed first shifted by its bulk's change in the supply models over the bulk's change
     in the market's last solve (l. 54-88);
   - C-sugar's biofuel use where the sugar quotas apply (p_cSugarCalPar, l. 335-349);
   - bounds and starting values only (l. 94-147, 374-438).

   Nothing else is recalibrated in this file: human consumption, processing, biofuel feedstocks other than C-sugar,
   and the behaviour of the regions without supply models keep the run's calibration (step 1). (Other per-step updates outside this file, if
   any, to be listed when data_cal.gms and simu_market.gms are read in full.)

CAPRI's online documentation (bw-pages.thuenen.de/capri/capri, "Baseline generation" 4.4-4.6 and "Scenario
simulation" 5.4-5.6, read 6 November 2026; it describes an older version, base year 2012) agrees: the market calibrated
against the simulation year only; in the iterations only the supply and feed demand constants shifted to the supply
models' results; the baseline reproduced by an ordinary simulation run of the same scenario. It does not describe
prep_market's per-run calibration (read in the code only). Its release notes stop at STAR 2.8; STAR 2.0 lists
"occasional problems to reproduce the baseline in 2030 when market and supply are allowed to interact".

Consequence: in CAPRI's baseline simulation the prices are those that clear the market with the supply models'
production and feed use against the baseline's other uses and the rest of the world. They equal the baseline prices
only as far as the supply models reproduce the baseline quantities, which CAPRI's PMP calibration to 2030 is built to
do.

## 2. capri-mod today (DEP-5)

The baseline run calibrates the market's demand to the supply models' supply in every outer iteration
(`BilateralSolveMixin._bilateral_calibrate`, called from the bilateral solve while no EU base is recorded), and the
scenario runs inherit that calibration frozen (`demand_cal_frozen`):

- each bilateral commodity is closed at the supply models' base supply: CAPRI's trade flows kept, domestic sales take
  the difference (`BilateralCommodity.calibrate`); where CAPRI's exports exceed the model's supply they are scaled down
  (`export_cap_hits`);
- the EU's base use is the supply models' production times CAPRI's use over production per member state
  (`MarketCalibrationMixin._align_eu_base_balance`), the crushing chains aligned the same way
  (`_align_eu_crush_products`);
- base consumption is rescaled so that use at the reference prices equals that closure;
- for the pooled commodities the non-EU use is scaled so that the world clears, the factor bounded to [0.2, 5]
  (PROXY_AUDIT S185).

So the baseline's prices are the reference prices by construction, and any gap between the supply models and CAPRI's
baseline goes into demand instead of prices.

## 3. The gap the change will expose (measured)

`tools/check/compare_baseline_capri.py` on the K116 full run (full_k116c, 5 November 2026), the baseline against
CAPRI's 2030 reference:

| Block | n | median abs. dev. | size-weighted | within 10% |
|---|---|---|---|---|
| production | 49 | 0.2% | 0.4% | 100% |
| domestic use | 52 | 0.4% | 4.1% | 88% |
| activities | 39 | 0.2% | 6.9% | 95% |

Production meets DFC's removal condition ("supply models that reproduce CAPRI's 2030 market baseline quantities at its
prices"). The domestic-use row first read as a gap (oats +16.5%, pulses +13.2%, rye +12.5%, other cereals +11.5%,
barley +11.3%, wheat +9.0%, potatoes +8.6%, maize +7.8%, other oils -28.0%), but measured again (5 November 2026,
evening; run full_tj, the same baseline) it is mostly the check's own definition: the tool sums CAPRI's use components
HCOM + FEDM + INDM + BIOF + LOSM + PRCM, and for cereals these fall 8-10% short of CAPRI's own balance (GROF + IMPT -
EXPT). The rest of the balance is in positions that capri_eu27_market_balance_2030_ref.json does not hold (seed use
and the like; which ones not yet checked). Against CAPRI's balance the model's EU use is within 2.4% for every product
listed above (wheat +0.0%, barley +0.5%, maize -0.1%, rye +0.9%, oats +2.3%, other cereals +0.5%, potatoes +0.1%,
pulses -2.4%, raw milk -0.1%) except other oils (-22.1%) and cheese (-4.5%). The supply models' cereal feed (the FCER
bulk summed over the EU, 145,645 kt) is CAPRI's cereal FEDM (144,891 kt) within 0.5%. So the baseline price changes to
expect under CAPRI's form are small for cereals; other oils and cheese are the cases to look at first.

The missing positions, read in CAPRI's result file (res_2_1730greendeal_refdefaulta, dataOut, EU27yr19, barley): CAPRI's
market use DOMM (41,256 kt) is HCOM + FEDM + SEDM + INDM + PRCM + BIOF + LOSM, seed use SEDM (944 kt) being the one the
tool left out; and DOMM = MAPR + IMPT - EXPT with MAPR = GROF - on-farm seed SEDF (1,228 kt) - on-farm losses LOSF
(2,169 kt). The model's market works with gross production, so its use holds SEDF and LOSF too: DOMM + SEDF + LOSF =
44,653 kt against the model's 44,859 kt. The tool now takes GROF + IMPT - EXPT as CAPRI's use (5 November 2026); on
full_tj: domestic use median deviation 0.2%, size-weighted 0.5%, 98% within 10%; the gaps left: other oils -22.1%,
cheese -4.5%, casein -4.1%, every other product within 2.4%.

Where CAPRI's seed use and losses sit (read 5 November 2026, late evening). CAPRI's default
`$setglobal grofNEprod on` (capmod/set_global_variables.gms l. 144-148: "PROD does not include seed use and losses")
gives the market each supply product's production as the supply models' gross production times CAPRI's PROD/GROF at
the calibration point (arm/simu_calibration_to_supply.gms l. 219-226): the market's supply is net of seed and losses,
which follow production in proportion. ArmBal1_ then has four uses only (HCON, FEED, PROC, BIOF). In capri-mod the
market's supply is the gross production (the check above: production within 0.2% of GROF), and seed and losses sit in
the market's use, spread over the four components by CAPRI's shares, so they respond to prices like the component they
fall in instead of following production. Not registered as a departure so far; it is part of S7: the supply
recalibration (section 4 item 2) takes the supply models' gross production times CAPRI's PROD/GROF at the calibration
point, as CAPRI, and the use calibrated to CAPRI's four components without seed and on-farm losses. Size for barley:
SEDM + SEDF + LOSF 4.3 Mt of 44.7 Mt (about 10%). CAPRI's market use (arm/data_prep.gms l. 834-857, read 6 November 2026): HCON = HCOM + LOSM (+ INDM for oilseeds, milk and barley), FEED = FEDM, PROC = PRCM + INDM (other products), BIOF = BIOF; seed use (SEDM) is in none of them, so with SEDF and LOSF it is the part of gross production the market never sees (PROD, the grofNEprod note).

## 4. Design

1. **Calibration once per run, to CAPRI's 2030 market data with the scenario's shifters** (prep_market's
   cal_cnst_terms and recalibrate_commitments, section 1). Each bilateral commodity calibrated at CAPRI's own base
   supply, use and flows (no closure at the model's supply, so no export scaling); every demand component at CAPRI's
   2030 shares; no non-EU use factor. A scenario that shifts demand moves that point before the calibration, as in
   CAPRI, instead of shifting a demand frozen in the baseline (`demand_cal_frozen`); which of capri-mod's scenario
   inputs are such shifters is to be listed before building. This replaces `_bilateral_calibrate`'s per-iteration
   call and `_align_eu_base_balance`'s self-sufficiency rule.
2. **Every iteration, baseline and scenario alike: the supply side only.**
   - EU supply: the market supply functions recalibrated to the supply models (market.market_supply_nq, CAPRI's
     ProdNQ_ with p_hessNQSupp). To verify against l. 360-368: the constant shift at the current prices, the young
     animals net of their use, sugar, rice from paddy, olive oil from olives and raw milk from COMI+SGMI.
   - The same for every region with supply models (CAPRI's RMSSUP: Norway, Turkey, the Western Balkans as their
     supply models are switched on), not the EU only.
   - EU feed: the feed bulks follow the supply models' feed use. capri-mod already has CAPRI's feedBlk_ in the market
     (capri_mod/market/feed.py); to verify against l. 54-88 and l. 264-275 that its constant is shifted as CAPRI's
     (log-linear, at the current bulk prices and supply prices).
   - To check before porting: at which prices the constants are shifted (CAPRI's last market solve, arm/set_prices.gms
     l. 29, as read so far) against the averaged prices the supply models receive (0.55/0.3/0.15, from step 20
     0.4/0.3/0.2/0.1); the load_cur/unload_cur step not yet traced.
   - C-sugar's biofuel use (l. 335-349): to check whether it is ported.
3. **The baseline becomes a market solution.** The baseline run solves the market at the supply models' supply, with
   the outer loop as in a scenario. Scenarios start from the baseline's solution and are reported against it, as now.
4. **Setting.** `market.demand_calibration`: "capri" (the new default) or "supply" (today's form, kept only until the
   full Farm-to-Fork run validates the new one, then removed with its code so it does not become an orphan). DEP-5
   moves to the register's history; PROXY_AUDIT S185 closes.
5. **What assumes the baseline prices equal the reference, to check one by one:** the market supply Hessian measured
   at the baseline's state; the dairy blocks' and the young animals' base prices; the K116 trajectory's reference
   prices; CAPRI's stop rule in the baseline; `compare_baseline_capri.py`'s price block, which becomes a real check
   (today the model's prices are the reference by construction).

6. **CAPRI's scenario shifters** (the layer the course ladder needs; arm/prep_market.gms l. 437-627, read 6 November
   2026). A scenario file writes DATA(region, item, product, position) with position one of ScenShifterPos
   (ChangeFactor, PercentageChange, AbsoluteLevel, AbsoluteChange; also ChangeFactorShareFeedMax/Min, MaxFactor,
   MinFactor). For the market, before the per-run calibration (item 1):
   - the general case: DATA(RMS, ScenItems, XX1, "CUR") shifted (AbsoluteLevel replaces, AbsoluteChange adds,
     ChangeFactor multiplies, PercentageChange multiplies by 1 + p/100), ScenItems = FORE ARTIF OLND HCON PROC TCost
     NAGR SECG EXOG UVAG QUTS CTAX PROD LEVL FEED (sets of sim_ini_21730);
   - production shifters of regions without supply models become yield shifters first (l. 542-553);
   - the shares in human consumption (LOSMsh, INDMsh, LOSCsh) and the transport costs (DATAOUT tCost) shifted the
     same way;
   - aborts: a shifter on PROD or FEED of a country with supply models (those come from the supply models), on a
     market LEVL other than other crops and new energy crops, on land rents or areas other than forest, other land
     and artificial land;
   - income (DATA(RMS, "INCE", "LEVL", "PercentageChange"), the GDP exercise) applied after the calibration
     (l. 902-906), so it moves demand through the income elasticities instead of being calibrated away.
   The supply models' shifters (read 6 November 2026): yields per region and activity, DATA(RU, MPACT, "Yild", pos)
   on the output coefficients at "Y", input demand per ha following (capmod/shift_yields.gms, capmod.gms l. 757;
   capmod/define_inputs.gms l. 772); prices DATA(MS, "UVAG", IO, pos) at "Y" for the products whose prices are not
   endogenous (capmod/inflation_and_trend_interpolation.gms l. 90-104): a shifter on a price in IOE (the market's
   products, e.g. SWHE, COMI; with the market model off, COMI, the feeds, olives, paddy and sugar beet leave IOE)
   aborts the run, so a milk price shock is a supply-only scenario; fertilisers (NITF, PHOF, POTF) are not in IOE.
   Levels of fixed factors and land types: capmod/change_fact_levls.gms (capmod.gms l. 1029); non-policy shocks:
   shock/shift_exog.gms (capmod.gms l. 1413, with non_policy_shocks on). capri-mod has no general shifter layer today;
   S7 adds it for the market, read from the scenario's own table (one row per DATA cell and position), and the supply
   side's shifters with it, so the ladder's rungs run.

7. **Build steps** (6 November 2026, after mapping capri-mod's code: the baseline never solves the market today,
   bilateral_solve.py returns r = 1 after `_bilateral_calibrate`, which runs in every baseline iteration at the
   supply models' output; scenarios restore that calibration from the baseline cache, model.py l. 450-473):
   1. Setting `market.demand_calibration` ("supply", today's form, stays the default until the full Farm-to-Fork run
      validates "capri"; then "capri" becomes the default and "supply" is deleted).
   2. Data: CAPRI's marketed over gross production per country with supply models and market product,
      DATA(RMSSUP, "Prod", XX, "CAL") over the sum of DATA(RMSSUP, "GROF", rows, "TRD") mapped to XX (CAP_TO_TRD), as
      prep_market l. 1290-1300 sets them; from sim_ini_21730's DATA, by a builder. The bridge multiplies the supply
      models' gross output by it in "capri" (simu_calibration_to_supply l. 219-226; rice from paddy and olive oil from
      olives the same way; raw milk in proportion to COMI + SGMI; sugar beet unchanged).
   3. "capri": `_bilateral_calibrate` once per run at CAPRI's own supply (base_production as read from CAPRI's 2030
      flows and regions, all regions, the EU blocks included), without `_align_eu_base_balance`, `_align_sup_base` and
      the export scaling; the crush chains at CAPRI's seed use. The one pooled commodity, raw milk (every other
      market product has CAPRI's bilateral flows, other oils included), keeps its world-clearing factor for now: the
      non-EU regions' raw milk base is FAO's base period (world_market_baseline.csv, dairy_world_baseline.csv), not
      2030, so the pool does not close at the calibration point (PROXY_AUDIT S185 stays open for raw milk). CAPRI does
      not trade raw milk: each region's milk goes to its own dairies. The fix in CAPRI's form, a separate item after
      Milestone A (with G3): each non-EU region's raw milk cleared in its own dairy block, as the EU's and Norway's
      already are, at CAPRI's 2030 calibration point; the pool and the factor then go.
   4. "capri": the baseline solves the market like a scenario (no early return with r = 1), its prices feeding the
      supply models through the outer loop; scenarios inherit the calibration (identical to the baseline's while no
      market shifter is set) and start from the baseline's solution.
   5. The scenario shifter layer (item 6), the market's part applied before the per-run calibration, then recalibrated
      per run when a shifter is present.
   6. Each step checked on the mini-EU (with "supply" bit-identical to dev; with "capri" the baseline's price moves
      traced to quantity gaps), then the tests of section 5.

## 5. Checks

1. A test: with the supply fixed at CAPRI's 2030 production (no supply models), the calibrated market clears at the
   reference prices to the solve tolerance (CAPRI's own test solve after the calibration, prep_market l. 917-1201).
2. Mini-EU baseline: the price changes from the reference, each traced to a quantity gap of section 3.
3. Full baseline against CAPRI's 2030 reference: production, use and prices (compare_baseline_capri.py). In "capri"
   the tool compares the products the supply models hand over with CAPRI's marketed production (PROD at the
   calibration point, sim_ini_21730) and their use with PROD + IMPT - EXPT, since the market no longer holds seed and
   losses (7 November 2026). full_s7 (Farm-to-Fork's baseline, full EU): production median 0.2%, all 29 products
   within 2.2% (pulses -2.2%, oats +1.7%, other cereals +1.4%, beef +1.2%); use median 0.1%, all within 1.8%; the
   processed products against GROF as before (cheese -4.0%, casein -2.6%).
4. Full Farm-to-Fork against the run before the change (compare_runs.py --capri): the deviation from JRC121368 and
   each indicator that moves by more than one point explained.
5. The test suite.

## 6. Questions for the project lead

Answered 5 November 2026: all three as proposed. DEP-22 first, then the gap's split, then S7; the "supply" form kept
only until the full Farm-to-Fork run validates "capri", then deleted; each baseline price move above 5% reported before
deciding between a supply-side fix and a registered departure.

1. **Order with DEP-22.** The domestic-use gap is mostly cereals, i.e. likely feed, and DEP-22 changes the feed slopes.
   Proposed: commit DEP-22 first, then measure the gap's split (feed against the other uses) on its run, then build S7.
   (Measured the same evening on full_tj, section 3: the cereal gap was the check's definition, and cereal feed matches
   CAPRI's within 0.5%; DEP-22 first still holds, since it changes the feed slopes S7's baseline will run on.)
2. **The old form.** Proposed: keep "supply" as a switch only until the full Farm-to-Fork run validates "capri", then
   delete its code (no orphan). Or keep it permanently as a diagnostic?
3. **If a baseline price moves a lot** (say above 5%) because a supply model's feed or production misses CAPRI's: fix
   the cause on the supply side, or accept it and register it? Proposed: report each such case before deciding,
   since CAPRI itself would show the same price change if its supply models missed its baseline.
