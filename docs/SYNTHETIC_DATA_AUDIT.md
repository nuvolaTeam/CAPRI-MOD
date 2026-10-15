# Synthetic, proxy and hard-coded data — audit (October 2026)

*What in the model is not CAPRI's data, whether it reaches the results, and why it is there. Checked by running
the code, not by reading the registry: a full Farm-to-Fork 2030 run under line coverage (every numeric table and
constant in `capri_mod` classified as read or not), the fallback conditions evaluated for all 248 regions, and the
2017 input files compared cell by cell with CAPRI's 2017 regional results (`res_17<MS>`, all 27 member states,
NUTS groups as in `tools/_model_regions.capri_groups`).*

## Why there is synthetic data at all

1. **The project began as a synthetic prototype.** Every loader in `capri_mod/data/loaders.py` still carries a
   generator ("structure + noise") for when its file is missing; `CAPRIModel`'s docstring still says "if None,
   synthetic baseline data is used". Real files replaced the generators one by one. All 47 files the loaders ask for
   now exist, so these generators no longer run — except the tariffs, which had no file until Sprint 9r.
2. **Some files on disk *are* generator output.** `policy/cap_payments.csv` is the loader's random draw written
   out (ANC = 85 × U(0.5, 1.5), AES = 50 × U(0, 2), organic = 180 × U(0, 1.5) — the ratios fill exactly those
   intervals). The registry calls its successor REAL_CAPRI, but the old file stayed as a fallback.
3. **The first CAPRI extraction covered 192 regions.** Premiums (`capreg_cap_premium.csv`), variable costs and some
   yield columns were built from it; the other 56 regions (Denmark, Croatia, Slovenia, Lithuania, Bulgaria's
   NUTS-2016 regions, Ireland, Polish and Italian renamed regions, city states...) were filled with national or
   group values or fell back. Later all 27 member-state dumps arrived and the herd, manure, feed and land builders
   were redone with them; these three were not.
4. **CAPRI codes not mapped.** The premium file keeps CAPRI's codes (OFAR, TWIN, TEXT), so the model's OFOD,
   WINE, OFIB and COTT never find their premium, in any region.
5. **The environmental accounts started from IPCC Tier 1 / literature defaults.** They were replaced block by block
   with CAPRI's factors (manure N, manure N2O, ammonia, enteric CH4 of cattle from the feed mix, deposition, crop N);
   manure CH4 and the CO2 from liming and urea were never replaced.
6. **Explicit assumptions written where no CAPRI value was looked for** (yield response to price, land supply).

## A. Synthetic values that reach the results now

| # | What | Where it acts | Size | CAPRI source to use |
|---|---|---|---|---|
| A1 | **Crop CAP premiums** fall back to `cap_payments.csv` BPS (random generator output) | net revenue of crops → PMP calibration, land shadow price, margins, income | **1,957 region × crop cells**: OFOD, SETA, WINE, OFIB in every region; all crops in ~50 regions | DATA2 PRME per activity, all 27 dumps, NUTS groups; code map OFAR/TWIN/TEXT |
| A2 | **Crop variable costs** filled, not CAPRI's | net revenue of crops | **698 region × crop cells** (wine, other fibre, other fruit, table grapes, tomatoes, apples...): e.g. other fruit 8,747 €/ha in every Austrian region against CAPRI's 27,000–37,000; wine 1,313 against 6,700–8,000 | DATA2 TOIN, all 27 dumps |
| A3 | **Other-fibre yield** (OFIB) lognormal draw | production, revenue of OFIB | 139 regions; 1.5 t/ha against CAPRI's TEXT 3.8 | DATA2 TEXT YILD |
| A4 | Non-EU tariffs (random per load) | domestic price levels, crushing | fixed in Sprint 9r | — |
| A5 | **Wine producer price** filled in 36 regions (e.g. Galicia 1,362 €/t against CAPRI's 403) | revenue of wine | 36 regions | DATA2 MPRI of TWIN |


All other 2017 supply inputs match CAPRI: crop areas 5,901 of 6,113 group cells within 1% (the rest are code
definitions: fodder = OFAR + fodder roots, Greek and Spanish TEXT = cotton); crop yields 5,331 of 5,688 (the rest:
grass, a unit definition, and A3); producer prices 5,525 of 5,784 (the rest: A5, and grass, whose 1,000 €/t is a
placeholder in CAPRI itself). Herds are Eurostat census heads by design (registered), with every per-head coefficient
built as CAPRI total / census heads.

## B. Hard-coded coefficients where CAPRI's own values exist

| # | What | Model now | CAPRI | Effect |
|---|---|---|---|---|
| B1 | **Manure CH4** per head | IPCC flat, same in every region (dairy 16, fattening pigs 3.5, sows 4.2 kg) | CH4MAN per activity and region (dairy: DE 42.8, FR 10.9, ES 15.6 kg) | EU 2017 on the model's herds: 1,072 kt against CAPRI's 1,396; reported manure CH4, GHG total and the emission-tax coefficients |
| B2 | **CO2 from liming** | 600 kg limestone × 0.12 on every arable ha (72 kg CO2/ha) | CO2LIM per crop and region (wheat DE11 116 kg/ha) | GHG total, tax |
| B3 | **CO2 from urea** | 30% of mineral N as urea | CO2UREA per crop and region | GHG total, tax |
| B4 | **Yield response to price** | elasticity 0.15 for every crop (literature) | `supply/yield_elas.gms`: cereals 0.3, oilseeds 0.2, potatoes 0.2, others 0, on the member state's unit value | crop supply in every scenario |
| B5 | Enteric CH4, non-cattle | IPCC table per census head | CH4ENT per CAPRI unit (same Tier 1 values, different unit base: pigs per pig produced) | small |
| B6 | Grass dry-matter share | 0.20 | to check against CAPRI's grass DM content | grass tonnage, N removal |

The model's "GHG total" also includes CO2 (liming, urea) while JRC121368's comparison figure is non-CO2 — to align
when B2/B3 are replaced.

## C. Assumptions with no CAPRI counterpart found yet

- Land supply elasticity 0.15 and expansion cap 0.15 (`RegionalSupplyModel`): an approximation of CAPRI's land
  nest with indicative rent shares (stated in the code).
- Other oilseeds (OOIL) world market: CAPRI has none; the model pools one with an invented world total (20,000 kt)
  and fixed production shares for non-EU regions.
- CAPRI's numbers kept in code rather than CSV (project rule: inputs in CSV): feed-cereal weights
  (`FEED_CEREAL_MIX`, CAPRI 2030 FEDM), broiler rounds per place (4.35), cost shares (`OTHER_COST_SHARE`,
  `FERT_COST_SHARE`, `PPP_COST_SHARE`, from the 27 dumps), JRC121368 assumptions (pesticide yield loss 10%,
  other-cost rises), CAPRI calibration constants (p_elasHigh, share term 0.2, relSubs 1.2 / 0.2, TRQ sigmoid 200).
  These are CAPRI's values; only their location breaks the rule.

## D. Present but not reaching the results

- Loader generators for areas, yields, herds, land, costs, payments (files exist); generic N excretion, N fixation
  and N content tables, flat manure N2O 2%, IPCC ammonia path, literature supply elasticities: each is a fallback
  that no region triggers (the ammonia one only Brussels, BE10). They would silently switch on if a file or a row
  went missing — better to fail loudly.
- `NATIONAL_ENVELOPES` ("approximate 2023-2027") and the payment engine fed by `cap_payments.csv`: the policy
  summary's budget report only (wrong numbers in a report, not in the model). `INTERVENTION_PRICES`: not applied.
- The scenario library in `capri_mod/scenarios/scenarios.py` (invented policy packages); the runs use
  `policy/greendeal.py`, CAPRI's settings.

## Status after Sprint 9s (October 2026)

Done:
- **A1-A3, A5**: crop yields, prices, input costs and premiums rebuilt for all 248 regions from the 27 member-state
  dumps (`tools/build_crop_economics_2017.py`); the loader's cap on horticultural costs removed (CAPRI's costs as
  they are); `cap_payments.csv` is CAPRI's premium per ha of UAA (budget report only) and no longer a fallback.
- **B1-B3, B5**: manure and enteric CH4 per head, CO2 from liming and urea are CAPRI's (`tools/build_ghg_coefs_2017.py`;
  2030 by CAPRI's reference factors). The GHG total is reported as all items, non-CO2 (compared with JRC121368) and
  CAPRI's GGWP (non-CO2 + liming), the emission tax's base.
- **B4**: CAPRI's yield elasticities (cereals 0.3, oilseeds and potatoes 0.2, others 0).
- **D**: the loader generators and the generic environmental fallbacks are gone; a missing file or a region without
  CAPRI's coefficients raises; a test checks every region with a herd or crops has them. CAPRI tables kept in code
  (cost shares, feed-cereal weights) moved to CSV.

Effect: the 2030 baseline against CAPRI's reference is unchanged (calibration absorbs the margins: activities 1.3%,
production 1.1%); Farm-to-Fork gap 4.31 → 4.06 (cereal price +8.8% against CAPRI's +8, veg+perm price +13.5 against
+15, cereal production −15.0 = CAPRI); EU baseline manure CH4 24.7 → 33.4 Mt CO2-eq.

Then the open items (Sprint 9s, second part):
- **Other oilseeds** (C): CAPRI has no market for them (arm_sets.gms nonXX_CROPS) and holds OOIL, OIND and OANI
  fixed at their data level (sets.gms FACT, supply/prep_sim.gms v_actLevl.FX). Done the same here; the pooled world
  market with its invented 20,000 kt world total is removed (also from world_prices.csv, armington_params.csv).
- **Grass** (B6): CAPRI's dry-matter content (DRMA of GRAS, 0.22 in every region) instead of 0.20, and CAPRI's fresh
  grass yield (the GRAS output of the GRAS activity) in every region - 56 regions (Denmark, Ireland, the split and
  renamed regions) had carried template yields of ~5 t/ha; the grass price is rebuilt on that basis (revenue =
  CAPRI's MREV), which also corrects split regions whose price had been scaled by their cattle share.
- **Land supply** (C): CAPRI's land market (p_pmpQuadLandTypes) now covers every region with farmland - Ireland's
  three NUTS-2016 regions take IE01 + IE02's matrices (tools/build_land_market.py), FI1D its own two CAPRI regions
  instead of the national matrix. The rent-elasticity rule (0.15) serves only a land market switched off.

Effect of the second part: Farm-to-Fork gap 4.06 → 4.27, all of it Ireland's land market: grassland can now expand
from other land and forest as CAPRI's land owner allows, and under the per-hectare surplus target Irish grassland
grows ~750 kha, suckler cows and sheep with it (beef animals −15.8% against −16.9%, sheep −6.2% against −7.4%, milk
price +30.8%). The response is CAPRI's own land-supply curvature (per hectare comparable to Midi-Pyrénées); JRC121368
does not report Ireland. Green Deal: within 2.6 points. Both items left then were closed in Sprint 9t: the
constants are in `capri_data/shared/model_parameters.csv` (unit, kind, source; a test keeps file and code in step),
and combined CAPRI regions' land supply is the sum of their land owners' responses.

## Fix as proposed

1. Rebuild premiums, crop variable costs and OFIB yields from the 27 dumps for all 248 regions, codes mapped;
   delete `cap_payments.csv` as a model input (budget report from CAPRI's PRME).
2. Manure CH4 and non-cattle enteric CH4 as CAPRI total / model heads per region (as manure N); CO2LIM and CO2UREA
   per crop and region; GHG total split CO2 / non-CO2 for the comparison.
3. CAPRI's yield elasticities by crop group.
4. Fallbacks that no region uses raise instead of returning a default; CAPRI's in-code tables moved to CSV;
   `tools/detect_synthetic_columns.py` and this audit's checks into the test suite.

Expected effect: 2017 margins of permanent and specialty crops (A1, A2) and every manure-CH4 and GHG figure (B1-B3)
move; scenario responses of cereals and oilseeds (B4). Each step re-run against CAPRI's reference and JRC121368.
