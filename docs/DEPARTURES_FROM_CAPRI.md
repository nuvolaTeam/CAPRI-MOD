# Departures from CAPRI's settings

The project lead's rule (23 October 2026): **follow CAPRI, except where CAPRI's code is in error, and describe every
difference.** This file lists the settings whose default in `capri_mod/settings/defaults.toml` is not CAPRI star 3.0's.
It covers settings only. Method choices registered elsewhere (KNOWN_ISSUES, MITIGATION_IN_SUPPLY, NLP_PORT_DESIGN)
are not repeated here.

Two kinds of entry:

- **CAPRI-ERROR-FIX:** CAPRI's code is kept apart on purpose, because its effect contradicts CAPRI's own data or its other
  equations. The setting can reproduce CAPRI as coded.
- **DEPARTURE (to be removed):** the default differs from CAPRI's for a practical reason recorded at the time. The
  project lead decided on 23 October 2026 that each one goes to CAPRI's setting. They change one at a time, with a
  full Farm-to-Fork run after each.

## CAPRI-ERROR-FIX

### `environment.ad_dairy_ch4 = "fix"` (CAPRI as coded: `"capri"`)

**What CAPRI's code does.** Anaerobic digestion (AD_AnCh) on dairy cows' manure has no CH4 effect. The dairy macro
`MC_GHG_Miti_DCow` needs the factor `p_ghgMiti(MS,DCOL,"NOC","CH4MAN_3k","QEmitt")`. `ad_data_and_cali.gms` l. 588
sets every GainsTech's CH4MAN_3k entry to zero, NOC included.

**Evidence.**
- DE110000 DCOL CH4MAN per head: 54.709 at the ini run (share 0.054) and 53.922 at the max run (0.739). The
  non-dairy logic predicts ×0.575.
- CAPRI's own report (`reports/miti_report.gms` l. 1084-1100) still shows a dairy CH4 reduction, from a closed
  formula.

**What capri-mod does.** It applies CAPRI's CH4 factor to dairy cows as it does to the other animals. This was the
project lead's decision of 20 October 2026; details are in docs/AD_SPEC.md.

### `environment.ammapp_sign = "consistent"` (CAPRI as coded: `"capri"`)

**What CAPRI's code does.** It adds the low-emission application options' leaching effect in LEACHN_
(`+ v_ammoAppLeaAgg`, supply_model.gms l. 3413). Yet it subtracts the same options' runoff effect in RUNSURFN_, and
the fertiliser options' leaching effects in LEACHN_.

**Why that looks wrong.** The literature table gives reductions, with positive meaning less loss
(`prep_data_LitRev.gms` p_reducGains; LNA_low liquid: NH3 0.51, RunSurf −0.24, Leach −0.24). These are copied
unchanged to `no3mlea` (ammo_tech.gms l. 2293). With the "+", low-emission application lowers the leaching share
where CAPRI's data say it raises it.

**What capri-mod does.** It subtracts the effect, consistently with RUNSURFN_. This was the project lead's decision
of 20 October 2026; details are in capri_mod/supply/n_leaching.py.

**Scope of the effect.** The base is calibrated to CAPRI's realised leaching share either way, so the sign acts only
through changes in the options' adoption.

### `captrd.short_series_grid_as_coded = false` (CAPRI as coded: `true`) — CAPTRD-MOD, Step 1

**What CAPRI's code does.** CAPTRD's trend fit `x = a + b·t^c` searches 30 values of c. For a series with 3 or 4
observations it fixes c = 1, and with 1 or 2 it sets b = 0. Only the first grid point is computed, and the code
states that "only C1 entry is relevant" (`captrd/estimate_trends.gms` l. 158). The other 29 points are set to zero
(l. 160), and the minimum of the weighted error sum of squares is then taken over all 30 points (l. 166). A GAMS
`SMIN` counts the zeroed entries, so the minimum is 0 and the second grid point is chosen, with a = b = c = 0. This
happens unless the first point fits exactly.

**Evidence.** CAPRI's own CAPTRD results, `results_1770.gdx` (base 2017, uploaded 23 October 2026), have 93 series
with 2–4 observations.
- 92 of them have Step1 = 0 in every year.
- With 3–4 observations, wR2 = 0, so the support is the base value and the trend is ignored.
- With 2 observations, wR2 = 1 (wVar is not defined), so the support is 0.001 × base. Examples:
  - CS FEDM OCER: support 0.077 against a base of 77.4, and a 2030 result of 4.4;
  - AL LOSF ROOF: support 0.0047 against a base of 4.72.
- The one exception (BA NTRD DDGS) was not traced.

The same port reproduces CAPRI's Step 1 for 99.78% of the 96,478 comparable series, so this is the code as it runs,
not a porting artefact (test `capri_mod/pipeline/tests/test_captrd_step1.py::test_parity_with_captrd_step1`).

**What capri-mod does.** It takes the minimum over the first grid point only, as CAPRI's comment intends:
- 1–2 observations: a is the weighted mean and b = 0;
- 3–4 observations: a linear weighted fit.

This is the default under the rule of 23 October 2026 for corrections of CAPRI code errors, pending the project
lead's confirmation. `true` reproduces CAPRI for the parity runs.

**Scope.** 93 of about 100,000 estimated series, mostly minor positions (DDGS, losses, a few NUTS2 crops). The fix
changes their supports directly; other series can change only through the consistency equations of CAPTRD's Step 2.

### `captrd.variance_floor_squared = true` (CAPRI as coded: `false`) — CAPTRD-MOD, supports

**What CAPRI's code does.** The stored error variance of each series gets a floor: wVarErr = max(0.05 × |wAve|,
wVarErr) (`captrd/define_stats_and_supports.gms` l. 327-329). The floor is a level, while wVarErr is a variance.

**Evidence that it is an error.** wVarErr is a variance everywhere else in CAPRI's code:
- its definition is a weighted sum of squared residuals (l. 118-123);
- its fall-back for 1-2 observations is SQR(wAve) × 0.25 (l. 130);
- it is later used as a variance: sqrt(wVarErr) serves as a standard deviation (`define_eu_supports.gms` l. 693, 705).
The floor binds in 19.5% of the comparable series of CAPRI's own output (results_1770.gdx). Its weight depends on the
series' unit: a level of 100 gives a floor of 5, a level of 0.01 a floor of 0.0005.

**What capri-mod does.** The floor is (0.05 × |wAve|)², a 5% coefficient of variation. The intended form is not stated
in CAPRI's code; this reading keeps CAPRI's 5% and makes it a variance. `false` reproduces CAPRI.

**Scope.** No effect on results yet: the stored variance weights the penalty terms of CAPTRD's Steps 2-3, which are
not ported. Decided on 24 October 2026 under the rule for CAPRI code errors ("fix the still open").

### `supply.greendeal_inputs_keep_tech_change = true` (CAPRI as coded: `false`) — Green Deal input changes

**What CAPRI's code does.** A scenario's regional input change DATA(RS, "GROF", I, "percentageChange") enters the
input coefficients as TF_I = 1 + change when the global scenAugmentsTechChange is off, and as (1 + change) x the
input-saving progress (1 - 0.005 per year from the base year, 0.935 in 2030) when it is on
(`capmod/define_inputs.gms` l. 66-73). `organic_io.gms` l. 94 and `conventional_io.gms` l. 171 set it on;
`conventional_io.gms` l. 361 sets it off in the file's other branch. $setglobal acts at compile time, whatever the run
time if() selects, and l. 361 comes last, so the Green Deal runs compile with it off.

**Evidence that it is an error.** CAPRI's comments state the intent and call the off setting a mistake:
- "Note3: The global was set ==off in the runs of July 2023, presumably by oversight after testing." (`organic_io.gms`
  l. 98, `conventional_io.gms` l. 176 and l. 367);
- "The gdversion global variable was used in Catalyse to activate scenAugmentsTechChange==on ... This has been
  rendered default now" (`greendeal_scenarios.gms` l. 137-138).
With it off, plant protection and other inputs lose the 2017-2030 progress in every EU region with a Green Deal input
change: in 2030 their coefficients are 1/0.935 = 7% higher than intended, on top of the scenario's change.

**What capri-mod does.** (1 + change) x the progress. `false` reproduces CAPRI's code.

**Scope.** Farm-to-Fork runs with the organic or pesticide target. Decided on 24 October 2026 under the rule for CAPRI
code errors (S3/S4 of the supply audit).

### `supply.organic_topup_at_fuel_cost = true` (CAPRI as coded: `false`) — organic other-input top-up

**What CAPRI's code does.** For each organic crop, `organic_io.gms` l. 111-115 adds EFUL x 2 x the crop's organic
target to the INPO coefficient (and SERI likewise, which has no activity rows in the 2017 data). An input coefficient is
valued at its own unit value (cost = coefficient x UVAG / 1000; the inputs of Belgian soft wheat sum to its TOIN, 1139
against 1140 EUR/ha), so the fuel quantity added to INPO is valued at INPO's unit value.

**Evidence that it is an error.** The comment above it (l. 107) gives the intent: "The top up assumes that costs for
EFUL+SERI would double, but the assignment occurs to INPO to have the effect on one position". The two unit values
differ by region: Belgium values EFUL at 472 and INPO at 1212 per 1000 units, France 1828 and 1208. Belgian soft
wheat's fuel costs 331 EUR/ha but its top-up as coded is 2 x 848 EUR/ha per unit of target (699.9 x 1212 / 1000).

**What capri-mod does.** The top-up is 2 x the target x the crop's fuel cost (EFUL x UVAG.EFUL / 1000), CAPRI's factor 2
kept. `false` reproduces CAPRI's code (plant_protection_cost.csv carries both values).

**Scope.** Farm-to-Fork runs with the organic target. Decided on 24 October 2026 under the rule for CAPRI code errors.

## Switched to CAPRI's setting

### `supply.absent_activities_fixed = true` (23 October 2026)

An activity without a level at the calibration point has no variable in CAPRI. Since 23 October 2026 the bounds hold
it at zero, and the greening rules leave it out.

The departure had been kept because the NLP failed in Greek and Bulgarian regions. Once the literature elasticities
were removed it became urgent: zero-level activities entered freely, and the Farm-to-Fork run cycled (KNOWN_ISSUES
K69). Two inconsistencies caused the failures, and both are fixed:
- the crop-diversification index took the logarithm of fixed columns;
- the permanent-grassland rule applied to a grassland of 3.5e-11 kha.

Reference run r110 has CAPRI's setting as the default.

### `market.market_supply_nq = true` and the young-animal markets inside the market (24 October 2026; K75)

CAPRI's market supply functions (ProdNQ_, p_hessNQSupp measured by price shocks on the supply models,
supply/calibrate_supply.gms, recalibrated to the supply models every iteration, arm/simu_calibration_to_supply.gms)
and its young-animal markets inside the market model (yaniMarket_, arm/market_model.gms l. 1579-1603). Before, the
market anticipated the EU supply response with its own-price elasticities and the young-animal prices were updated
between market solves; the Farm-to-Fork runs then left a slow beef / calf price mode (calf price ratio still rising at
the 25th iteration, the stopping rule reached 1.5-2 points of beef price short of the fixed point). Remaining
differences: with CAPRI's EU trade blocks (`market.eu_blocks`) the Hessian is summed per block
(`CAPRIModel._split_hessian`), but the young-animal markets keep the update between market solves. Raw milk:
since 24 October 2026 (audit M5) each member state's raw milk follows its own milk
price inside the market, through the Hessian's member-state rows and columns.

### Supply audit S5-S10 (24 October 2026)

All of the following are CAPRI's rules (their switches back to the previous model were removed on 27 October 2026,
with the other switches whose alternative was never run; docs/design/SETTINGS_INVENTORY.md):
- crop need follows yield as in fertned.gms, not the square root;
- input costs follow yields, as in define_inputs.gms;
- the grassland rule's calibration dual from prep_cal.gms;
- the options' cost charged on N purchases, as in GHG_Mit_Cost_;
- catch crops count on the ecoSetAside_ row.
- Idled histosols count on the landscape floor, and the diversification limit is lowered as in landscape.gms; these
  two have no switch.

### `outer_loop.price_update = "capri"` (26 October 2026)

CAPRI's price forecast for every price passed to the supply models (EU signal, member-state milk, EU blocks, Norway,
young animals): the weighted average of the market's prices of the last steps, 0.55 / 0.30 / 0.15, from the 20th step
0.4 / 0.3 / 0.2 / 0.1 (capmod/define_stepWeights.gms, price_forecast.gms l. 376-397). Before: an adaptive step per
price, halved when its gap changed sign (K62: CAPRI's weights on the member-state milk prices cycled in a Green Deal
run, r73, 21 October 2026). With the K75 fix, CAPRI's forecast converges in Farm-to-Fork in 9 iterations (r140; the
adaptive step 12, r139) and in Green Deal 2030 in 13 (r142; adaptive 11, r141), to the same equilibrium (indicators
within 0.1 point, prices within 0.6). User's decision. `"adaptive"` stays as an option.

### `outer_loop.stop_rule = "capri"` (28 October 2026; K79)

CAPRI's stop rule (capmod/price_forecast.gms l. 96-371: the loop goes on while more than two items change by more than
0.05% between iterations), with the model's inner balances settled as well. Made the default on 27 October 2026 and set
back the same evening when the Green Deal 2030 run (r165) did not stop by iteration 20; it was stopped by hand there, before its two-hour
limit (r168 too had 14 rows above 0.05% at iteration 20). The same scenario stops by CAPRI's rule after 30 iterations
(r168, 1 h 36 min including the 38 min of its Hessian's measurement), Farm-to-Fork after 12 (r164); EU indicators within 0.4 points of the model's
rule (r166). The model's rule stays as `"capri-mod"`.

### `supply.fodder_at_shadow_price` removed (26 October 2026, with the conic form)

The setting priced home-grown fodder at its fodder-balance dual in the ration chosen OUTSIDE the supply models, the
path used before rations were chosen inside them (K42). Since then it acted on nothing. In the regional models in
CAPRI's form, home-grown fodder carries no purchase price and enters through its balance SUPBAL_, an equality with the
feed use (capri_regional_nlp.py QUADRF_ and the fodder rows), so its value is that equality's dual, as in CAPRI. The
setting, its ratio bounds and damping, and the outside ration solve were removed with the conic form.

## Switches of CAPRI's policy files (28 October 2026)

CAPRI's scenario files set a few market-loop switches of their own. Two were found in its Green Deal scenarios
(pol_input/greendeal/greendeal_scenarios.gms):

- **Slower price smoothing for problem products** (`p_stepWgtSpecial(ms, product, "srt")`, define_stepWeights.gms
  l. 41-50, price_forecast.gms l. 384-386): for the products listed, the price passed to the supply models averages
  the baseline price and every step's market price, step j of k weighted max(0, 1 - srt (k + 1 - j)), instead of the
  last three or four steps. The Green Deal file lists none (its one entry, Malta's milk at 0.15, is commented out).
  capri-mod: `outer_loop.capri_step_special` (entries [member state, product, srt]; empty by default, as CAPRI's Green
  Deal runs). As in CAPRI the smoothed price is the one passed to that member state's supply models: CAPRI's member-state
  producer price is its block's market price times a fixed margin (arm/market_model.gms PPri_, price transmission
  elasticity one), as here, and CAPRI smooths what it hands to the member state's models; here those models get the
  smoothed price as a departure from the price the rest of the market sees (raw milk: the member state's own price).
- **Negative raw milk producer prices** (`negProdPriceAllowed(rms, "MILK")` and `negProdPriceAllowedFromStart(rmssup,
  "MILK")` for every market region, greendeal_scenarios.gms l. 66-67; arm/set_start_val.gms l. 565, widen_bounds.gms
  l. 452-457): the Green Deal runs let the milk price go below zero (lower bound -max(100, price)). Without the switch
  CAPRI's lower bound on a producer price (0.1 x the price) is lowered tenfold each time it binds but stays positive.
  capri-mod as CAPRI since 28 October 2026: `PolicyScenario.negative_milk_price`, set by the Green Deal group
  (greendeal_scenario, so Farm-to-Fork and Green Deal 2030 too); without it a member state's raw milk price is held at
  1e-7 of its base (MarketModule.MILK_PRICE_FLOOR), its fat and protein prices still clearing, and the member state is
  recorded (metadata "milk_price_floor", a warning) as its milk market does not clear there. Before, the price had no
  lower bound in any scenario; never active (lowest member-state raw milk price at the end of r163 Farm-to-Fork 1.10 of
  base, r166 Green Deal 1.05).

## Beyond CAPRI: reports only (results unchanged)

### `outer_loop.drift_report_steps = 3` (28 October 2026; the project lead's decision)

CAPRI's stop rule (price_forecast.gms l. 345-371) counts rows (products, each at its largest change over the trade
blocks) and stops when two or fewer change by more than 0.05%. It can therefore stop while one or two products still
move one way, iteration after iteration: Farm-to-Fork r170 stopped with the tomato price rising 0.36% per iteration
(a market supply Hessian far more price-responsive than the supply models, CHANGELOG 28 October 2026), its supply
models' tomato output 6% below the market's. capri-mod keeps CAPRI's rule and reports, when the loop ends, the items of
the rule (trade-block prices, member-state production and feed, after the rule's filters) whose last n changes had one
sign, the last above 0.05%: their changes, the rate they shrink at and a rough estimate of the movement still to come
(metadata capri_stop drift; a warning when the loop stopped). It decides nothing; 0 turns it off.

## DEPARTURE (to be removed)

| Setting | CAPRI star 3.0 | Default now | Why it differs (recorded at the time) | What switching needs |
|---|---|---|---|---|
| `outer_loop.max_outer_iter` | 99 (the GUI's number of iterations for a scenario run, %STEPS%) | 60 | the project lead's choice (28 October 2026): CAPRI's stop rule needs 30 iterations in the Green Deal 2030 scenario (r168), 12 in Farm-to-Fork; 60 keeps a run within the run time | none; a run that does not converge in 60 is reported as such |
| `supply.fert_slope_with_saving` | the fertiliser options' pmpParSqr with the fertiliser-saving term (envind/ghgMiti.gms l. 1016-1035), and the inhibitor on manure's with the manure-saving term at p_manureShadVal (l. 1036-1050; with this switch since 28 October 2026) | false (the curvature without it) | K77, 25 October 2026: with it and the cost on the N purchases, the 2030 baseline leaves the options' initial shares (FR10 precision farming 0.44; EU 9.6%, run r128); the saving runs through the NLP's fertilisation block, so the base becomes a saddle | the curvature of the saving in the NLP's terms (the fertilisation block's response), or CAPRI's N(m) = N0/(1 + nmE m) made explicit |
| `market.eu_blocks` | two EU trade blocks, EU_WEST and EU_EAST (aggregation/defaultA.agg) | false (one EU27 block) | built 18 October 2026 as an option; Farm-to-Fork deviation 4.22 → 4.65 when tried | a run; the market supply Hessian (below) is not built for the blocks yet |
| `supply.use_cattle_member_splits` | replacement heifers (HEIR) and the four calf activities with their own levels; young animals cleared per sex (INPANI_) | false (the model's animals with CAPRI's intensity pairs; pooled young-animal markets) | K65: with them on, the Farm-to-Fork run does not converge (male calves' price above 6 x base, female below zero, r96); no CAPRI per-sex Farm-to-Fork result exists to check against | find why the per-sex prices diverge (calf activities at their zero bounds) |
| (no setting yet) non-EU feed demand, M3 | FeedNQ_ (normalised quadratic, p_hessNQFeed derived from p_elasFeed in arm/trim_elas.gms l. 1975-2135) with the feed-energy balance FeedBal_ (arm/market_model.gms l. 1018-1048): non-EU feed use follows non-EU livestock output | constant elasticities p_ElasFeed (capri_mod/market/feed.py) | market audit M3 (K73), 24 October 2026; the user decided on 25 October 2026 to port it at the refactor's market feed block step, after that block reproduces the frozen reference, as its own step | CAPRI's own p_hessNQFeed (elas_2_1730defaulta, in hand), else derived from p_elasFeed as CAPRI's trim_elas; p_calContent and pv_feedConv rebuilt from CAPRI's code (arm/feed_conv.gms) and CSV data; one full run |
| (no setting) irrigated shares of the water indicator (capri_mod/water, tools/build/build_irrigation_2017.py) | crop-specific irrigated areas per EU region from a highest-posterior-density fit to the FSS crop data (p_wdata_fss) and the regional irrigated area IRR2, survey gaps filled by trend estimates (water_database.gms l. 325-640) | the region's IRR2 irrigated area (latest survey up to 2017, the member state's where no regional value) on its irrigable crops: rice entirely, one share for the others; Ireland none (no share in CAPRI's data) | the FSS crop-specific irrigated areas and the CAPREG time series for the trends are not among our sources; 27 October 2026. The adding-up to IRR2 is kept from CAPRI's fit; CAPRI's own rule where crop data are missing (Turkey, Western Balkans) puts the IRR2 share on every crop without it, which leaves about a third of the FSS irrigated area out (7.0 against 11.2 Mha) | the FSS irrigated areas by crop (Eurostat ef_poirrig / ef_mp_irri, as CSV) and CAPRI's HPD fit; CAPRI's water module in supply (irrigated and rainfed activities) is a further step |
| (no setting) mitigation options not built (KNOWN_ISSUES K93) | 3-NOP, legume share (LegSh), tillage (ConsTill, NoTill), urea substitution (UreaSubst), buffer strips, biodiversity options and biochar as options of the supply model (envind/, ghgMiti.gms), and the ration-fat constraint SupplementPerc_ | not built: their leaching and runoff terms are held at CAPRI's reference; linseed and nitrate are in | not built yet (registered 29 October 2026 in the registry migration; before, recorded only in K50 and K51) | each option's data (CAPRI's miti_data and envind files) and its columns in the regional model, one gate |
