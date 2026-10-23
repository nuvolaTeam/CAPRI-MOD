# Market structure as CAPRI: member states, GL demand, supply recalibration, farm types (plan, 18 October 2026)

Four remaining structural differences from CAPRI star 3.0 (docs/archive/CAPRI_COMPARISON.md), studied in CAPRI's GAMS source
(gams/arm, capmod, supply, farmtype; file:line references in the study notes below). Nothing here is implemented yet.

## 1. Market supply functions calibrated to the regional models (CAPRI: calibrate_supply.gms, simu_calibration_to_supply.gms)

What CAPRI does:
- Baseline, once: each product's supply-model price is raised by 1% (one scenario per product,
  supply/calibrate_supply.gms:193-274); the member-state responses give the Hessian of a normalised-quadratic supply
  function per member state, own- and cross-price, feed-bulk columns included
  (p_hessNQSupp = dQ/(0.01 P) x inflation factor, :446-455; negative diagonals abort, :484-491).
- Simulation: the Hessian stays fixed (arm/market1.gms:505-674). Each iteration only the constants move, so the
  function passes through the supply models' latest member-state output at the market's last prices
  (arm/simu_calibration_to_supply.gms:360-368): Q = c + H p / p_INPE.
- Prices passed to the supply models: an additive price gap on the trend price, averaged over the last iterations
  with weights 0.55 / 0.30 / 0.15 (0.4 / 0.3 / 0.2 / 0.1 from iteration 20) (capmod/define_stepWeights.gms:28-41,
  capmod/price_forecast.gms:376-383).

capri-mod now: EU-median own-price elasticities from CAPRI's market file, constant-elasticity form, and an
anticipation of the supply response relative to the price the supply models last saw; its own damping rule.

Plan: perturb capri-mod's own regional models once per baseline (about 50 products x 248 regions, warm-started,
cached), aggregate to member states, build H per member state; shift the constants every outer iteration; adopt
CAPRI's step weights. Data: none needed. Validation: the NQ function reproduces the supply models' output at the
anchor; a +5% out-of-sample shock against a fresh regional solve; positive diagonals; same equilibrium, fewer outer
iterations. Prerequisite for section 3 (member-state supply functions).

Done (18 October 2026), as an option, off by default: measured cost about 9 minutes once (cached), and on
Farm-to-Fork 13 outer iterations against 12 (493 s against 432 s) with results moved within the outer loop's tolerance
(beef price +1.7 points). No speed gain; the equilibrium is the supply models' with or without it.

## 2. Food demand: CAPRI's Generalised Leontief with cross-price terms (arm/market_model.gms:826-916)

What CAPRI does: per region, per head, x_i = [G_i/G (Y - F) + d_i] INHA, with F = sum d_i p_i,
G = sum b_ij sqrt(p_i p_j), G_i = sum_j b_ij sqrt(p_j / p_i); the non-agricultural good INPE at a fixed price
closes the budget. Parameters p_pdGL (d) and p_pbGL (b, upper triangle, symmetrised) come from trimming prior
elasticities under homogeneity, adding-up and curvature (arm/trim_elas.gms:543-852). Processing demand is
normalised-quadratic with cross terms only among crushed oilseeds and among vegetable oils; non-EU feed is
normalised-quadratic with a full Hessian; EU feed goes through the feed-bulk system (already in capri-mod).

Data: p_pdGL, p_pbGL, p_ElasDem for EU member states and non-EU regions are in elas_2_1730defaulta (and 1717); the
base data (HCON, CPRI incl. INPE, INCE, INHA) in data_market_1730defaulta. Checked: the stored parameters reproduce
CAPRI's demand and its full elasticity matrix for DE, FR and USA to about 1e-14.

Plan: extract to CSV; replace the own-price demand with the GL closed form where parameters exist; re-fit the
commitments d to the model's base quantities as CAPRI does (recalibrate_commitments.gms), keeping b; joint Newton
over the commodities with the analytic Jacobian; move the dairy block's own cross-price demand onto the GL so it is
not counted twice; processing cross terms among oilseeds and oils. Validation: base demand and the elasticity
matrix reproduced; homogeneity, adding-up, symmetry.

Done (18 October 2026), on by default (`food_demand_gl`; `gl_refit_commitments`):
- tools/build_gl_demand.py extracts p_pdGL, p_pbGL and the calibration point (CAL of elas_2_1730defaulta and
  data_market_1730defaulta) for 80 behavioural regions (26 EU member states, non-EU countries, the rest of the world);
  the stored parameters reproduce CAPRI's human consumption at CAL to 1e-7; elasticities equal p_ElasDem (DE, own and
  cross) to the finite-difference accuracy (5e-6); homogeneous of degree zero in prices and income (1e-15).
- MarketModule.gl_food_ratio: consumer prices move additively with the market's domestic price (Cpri_: Armington
  price + margin); the GL applies to CAPRI's human-consumption share of each region's use; feed, crushing and biofuel
  parts keep their own CAPRI functions, processing, industrial use and losses their own-price elasticities.
- Commitments re-fitted to the model's base as CAPRI does (trim_gl_commits.gms: least-squares change of d so the system
  reproduces the base human consumption at the calibration prices; exact, linear constraints). Only 0.5% of world
  human consumption lies in cells where the model's base use differs from CAPRI's by more than a factor 2.
- Farm-to-Fork: gap 4.58 -> 4.22 (beef price +17.6 -> +23.3%, CAPRI +24; pork +35.0 -> +40.7%, +43; vegetables and
  permanent crops +12.4 -> +15.7%, +15; poultry +24.3 -> +29.4%, +18; milk +35.5 -> +41.1%, +1.5); 17 outer iterations
  (12 before), 565 s. Re-fit against ratio form: the same within 0.2 points.
- Green Deal: unconverged at 60 outer iterations (K37: the young-animal price bound).
- Not yet: processing with cross terms among oilseeds and oils (ProcNQ_); fish, coffee, tea, cocoa are not markets
  (their prices stay at CAPRI's in the GL).

## 3. EU member states in the market (sets.gms:8235-8339, arm/market_model.gms)

What CAPRI does: the EU is two trade blocks, A_EU_WEST (EU-15) and A_EU_EAST (EU-13) (aggregation/defaultA.agg),
each with one market price and Armington prices; bilateral Armington trade between blocks (including West-East), none
between member states. The member states are behavioural regions inside their block: supply (NQ, section 1), food
demand (GL, section 2), feed, processing, biofuels, dairy per member state; producer price = block market price x a
calibrated relative margin plus premiums (PPri_, :3046), consumer price = block Armington price + an additive margin
and taxes (Cpri_, :3032). Raw milk, feed energy, land and young animals clear per member state. EU27yr19 is a
reporting aggregate only.

Data: member-state PROD, HCON, FEED, PROC, BIOF, PPRI, CPRI, PMrg, CMrg, CTAX, FATS, PROT, INHA, INCE in
data_market_1730defaulta (CAL); bilateral flows between the blocks in the market dumps; RMS -> RM from
gams/aggregation/defaultA.agg. Not in our files: premium wedges PSE/CSE per member state (to check).

Plan: replace the region EU27 by the two blocks (bilateral data rebuilt with West-East flows), member states as
behavioural regions with their margins, block-level clearing and Armington; the supply models' output per member
state into the NQ supply functions; the existing dairy and feed-bulk blocks per member state (they are already per
member state in parts). Also retires the market's legacy fallbacks for the EU base (hard-coded world totals and
shares in MarketModule.__init__, overwritten for every commodity CAPRI's world balance covers). Validation:
calibration point reproduced (zero residuals), member-state PPRI/CPRI and HCON against CAPRI, West-East flows, then
the Farm-to-Fork and Green Deal runs. The largest of the four; after sections 1 and 2.

Done (18 October 2026), as an option (`MarketModule.eu_blocks`, run_f2f_2030.py --eu-blocks; off by default until
the Green Deal runs and the remaining items below are settled):
- Data: tools/build_bilateral_market.py --eu-blocks keeps CAPRI's A_EU_WEST and A_EU_EAST (bilateral_*_<year>_eu2.csv;
  the extra-EU flows equal the one-region data; 2030 West-East flows, e.g. 15.0 Mt of maize from East to West);
  capri_data/shared/eu_market_blocks.csv (member state -> block, defaultA.agg); tools/build_eu_ms_balance.py (CAPRI's
  2030 member-state balance, used only to split the EU-level data that have no member-state detail: feed and
  biofuel shares of use, residual feed output, crushing share of seed use, dairy food and feed use).
- Market: each block a region of the bilateral market with its own market and Armington prices; the EU's quotas
  filled by both blocks' imports; the EU's external tariff on both; supply per block from its member states' supply
  models; GL demand, feed bulks, dairy blocks, biofuel feedstocks per member state at their block's prices; crushing
  per block; an EU27 reporting row (sums, production-weighted prices; CAPRI's EU27yr19 aggregate).
- Supply models: each member state's models see their block's prices (EU signal + the block's departure, relaxed
  with the same step); raw milk per member state as before.
- Checks: the calibration point is reproduced (base residual 1.6e-9), the one-region run is unchanged (Farm-to-Fork
  identical to the earlier run), a test of the data and splits (test_eu_trade_blocks_data_and_split).
- Farm-to-Fork with the blocks: converged in 13 outer iterations (467 s); gap 4.22 -> 4.65: beef price +23.3 ->
  +27.6% (West +29.1, East +11.2), poultry +29.4 -> +36.2% (West +43.9, East +13.6), pork +40.7 -> +41.5%; other
  indicators within 1 point.
- Registered departures: Norway's supply models feed EU_WEST (as they fed the one-region EU; CAPRI: its own market
  region); member-state producer margins are relative (CAPRI PPri_), so price ratios equal the block's (premiums per
  member state not modelled); the market supply Hessian (option, section 1) is not available with the blocks.
- 19 October 2026: young animals clear per block as CAPRI's yaniMarket_ (each block's net balance at its baseline
  level), with CAPRI's price bounds (negative prices allowed, set_start_val.gms, widen_bounds.gms); the legacy world
  base in MarketModule._calibrate_baseline retired (base production and use from CAPRI's bilateral market data, raw
  milk from CAPRI's FAO_agg balance). Green Deal with the blocks converges (42 iterations); the East block's calf
  price falls below zero (-0.64 x base: its calf surplus cannot leave the block, CAPRI fixes the blocks' net
  young-animal trade).

## 4. Farm types (farmtype/*, capmod/set_globals_for_farm_types_on.gms)

What CAPRI does: optional regional level (GUI "Regional breakdown": countries / NUTS2 / farm types; default NUTS2;
the Green Deal reference we compare with is a NUTS2 run, res_2_...). Farm types are FSS groups (type of farming x
economic size, up to 30 per NUTS2 region, 2,449 in 225 regions), each with its own supply model, summed to NUTS2;
data from FSS and FADN through CAPREG's farm module and a separate baseline task.

Data: none of it is in the project (no FSS farm-group tables, no FADN extracts, no CAPRI farm-type results to
validate against). Effort about 4-6 weeks after the data.

Recommendation: not now (off by default in CAPRI, not used in the runs we compare with, nothing to validate
against). An option beyond CAPRI: farm types from the Farm Structure Survey / IFS 2020 and public FADN tables.

## Order

1 (supply recalibration) -> 2 (GL demand) -> 3 (member states). Each ends with the batch tests and the Farm-to-Fork
and Green Deal runs; the comparative-static default is unchanged until each step is validated.
