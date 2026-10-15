# Baseline reproduction: the model's 2030 baseline against CAPRI star 3.0's own 2030 reference

Status (October 2026): **check in place** (`tools/compare_baseline_capri.py`); after Sprint 8m the 2030 baseline
is within 4% of CAPRI star 3.0's own 2030 reference for the median activity level and market quantity.

## Why

The Farm-to-Fork comparison with JRC121368 measures two things at once: the model's departures from CAPRI and the
difference between the CAPRI that produced the report (2020 version, base 2012, baseline on the OECD-FAO Outlook
2017–2026, milk-yield genomics on) and the CAPRI star 3.0 code and data the model is built from (base 2017,
Green Deal reference 2030). CAPRI's 2030 Green Deal reference of our own version (`res_2_1730greendeal_ref`,
`markmarket_greendeal_1730et_base_1717`) has no version gap: with no policy shock the model should land on it.
What it misses there is the model's own doing.

## What is compared

EU27, the model's 2030 baseline (projection run of `tools/run_f2f_2030.py`, saved `base_market` block) against:

| Block | CAPRI source |
|---|---|
| activity levels (1000 ha, 1000 heads) | `capri_eu27_levels_2030_ref.csv`: EU27yr19 LEVL, 2030 |
| market production (kt) | `capri_eu27_market_balance_2030_ref.json`: MAPR (GROF where no MAPR) |
| market domestic use (kt) | HCOM + FEDM + INDM + BIOF + LOSM + PRCM |
| producer prices | UVAP; the model's prices are CAPRI's 2030 prices in 2017 money, so the comparison is of the relative price structure (each ratio against the median ratio) |

`python tools/compare_baseline_capri.py RUN.pkl [--csv ...]`; the latest table is
`capri_data/validation/baseline_reproduction_2030.csv`.

## Sprint 9q: CAPRI's 2030 rations and fodder

The fodder crops were what the calibration could not reach (other fodder −13 to −28% in some regions, silage maize
−2 to −6%): the 2030 rations were the 2017 rations scaled by one factor, and the fodder balance's usable fodder per ha
stayed at 2017. CAPRI's 2030 reference has its own rations (Upper Bavaria's dairy cows: grass +6%, silage maize −12%,
other fodder +29% per head) and its own fodder use per ha (silage maize: in Germany more than half goes to biogas,
INDM, by 2030). Now (`tools/build_ration_trajectory_2030.py`):

- **rations and requirements**: per region group and model animal, each feed and requirement by CAPRI's 2030/2017
  per-head factor (`capri_ref_ration_2030.csv`; LEVL-weighted over CAPRI's activities; member state where no
  regional rows); the ration is lifted uniformly only where it would fall short of the energy or protein requirement;
- **usable fodder per ha** of the fodder balances: CAPRI's FEDM / LEVL of grass, silage maize and other fodder, 2030
  over 2017 (`capri_ref_fodder_2030.csv`; median: grass 0.91, silage maize 0.98, other fodder 0.94).

Regional drift of the 2030 baseline from its projected levels: median 0.13% → 0.01%, 90th percentile 3.9% → 0.36%;
fodder crops 90th percentile 17% → 1.1%. Against CAPRI's 2030 reference (s94): activities median 2.6% → 1.3%,
production 1.4% → 1.1%, domestic use 1.7% → 1.6%. The calibration now needs fewer rounds (Farm-to-Fork 984 → 799 s).

## Sprint 9p: the baseline starts from CAPRI's reference and is calibrated as CAPRI's

Three changes to the projection layer, each what CAPRI does:

1. **CAPRI's 2030 reference as the trajectory** (`capri_data/trajectories/capri_ref_2030.json`,
   `tools/build_trajectory_capri_ref.py`). CAPRI simulates from CAPMOD's calibrated reference run, not from its trend
   projection (CAPTRD), which is that calibration's input. The trajectory is now the reference's levels and yields over
   CAPRI's 2017 results, per region and activity (sheep and goats, calves as CAPRI's totals), plus the land types
   (ARAC, FRUN, GRAS, FALL): CAPRI's 2030 UAA is 2.1% below 2017, and the projection had kept 2017 land, so the
   reconciliation put every crop ~2% high. Projected data against the reference: median 2.7% → 1.0% (EU, activities);
   the remaining gaps are base-data differences (sheep and goats −18%, calves, olives, laying hens' units).
   `tools/run_f2f_2030.py --trajectory captrd` keeps the trend projection.
2. **Baseline calibration** (`SupplyModule.calibrate_to_base`, `CAPRIModel.calibrate_baseline`): CAPMOD calibrates
   its supply models so that the simulation year's baseline reproduces the projected levels. In the baseline of a
   projected year the regional models' linear terms now move by Q (x − x_target) until the solution is the projected
   level (rounds until the largest drift stops falling; fodder crops excepted, held by the fodder balances). Regional
   drift of the 2030 baseline from its projected levels: median 0.73% → 0.13%, 90th percentile 12.6% → 3.9%
   (broilers +7% → 0 in Brittany). The scenario starts from that calibrated baseline.
3. **Purchased feed at CAPRI's 2030 bulk prices** (`projection/prices.py`): the rations' FCER, FPRO, FOTH prices take
   CAPRI's feedBlkPrice_ CES index of the member state's feed products at their 2030 prices (DE: cereals 0.93,
   protein feed 1.02, other 1.10); FENE and FMIL at 1 (their products have no CAPRI unit value: registered).

Against CAPRI's 2030 reference (s91): activity levels median 3.8% → 2.6% (94% within 10%), market production
3.4% → 1.4% (95%), domestic use 2.8% → 1.7% (89%). Open: fodder crops (other fodder −13 to −28% in some regions,
silage maize −2 to −6%) - the projected rations (2017 rations scaled with the requirements) do not match the
projected fodder output; CAPRI's 2030 reference rations would close it (closed in Sprint 9q).

**Price levels** (the 25% "relative price" row): the model's market prices enter the supply side and the market's
behaviour only as ratios to their base; farm revenues use CAPRI's 2030 unit values. The row compares market prices
with CAPRI's producer unit values (UVAP), which differ by definition (cakes: world price 213 against a unit value of
483); it is a reporting difference, not a cost or revenue in the model.

## Results

| Block | first check (s46) | now (s59) | within 10% now |
|---|---|---|---|
| Activity levels (median abs. deviation) | 9.5% | **3.8%** | 83% |
| Market production | 9.4% | **3.5%** | 82% |
| Market domestic use | 11.3% | **3.7%** | 76% |
| Relative producer prices | 27.9% | 24.9% | 13% |

(Columns "now" and "within 10%": run s59, Sprint 9d, with the biofuel markets, DDGS and CAPRI's feed bulks; BIOE,
BIOD and DDGS are compared too: biofuel output and use within 0.1% of CAPRI's, DDGS within 2.3%. s50 had 3.8 / 4.8%
for production and use, s57 3.5 / 4.1%.)

What closed the gap (October 2026, Sprint 8m):

1. **The projection read CAPRI's trend projection by the wrong names.** `captrd_2030.json` is keyed by CAPRI
   codes (MAIZ, TWIN, BULF, SOWS, POUF ...) and CAPRI regions (DE11, FR24 ...); the projection asked for the
   model's names (CORN, WINE, BULL, PIGS, BROI ...) and NUTS 2021 regions, so those activities took the activity
   default and 246 of 248 regions the EU median. `tools/build_trajectory_model_keys.py` adds model-keyed entries.
2. **Livestock output per head stayed at 2017.** The yields table was projected but output per head came from
   the 2017 coefficients (a 2030 cow gave 2017 milk: EU farm milk 10% below CAPRI). Output and revenue per head
   now follow the projected yield (dairy cows: the milk part) and so do the requirements (dairy cows: energy,
   protein and dry matter from breeding.gms's functions, manure N per kg milk) - `ProjectionModule.
   _project_livestock`, `RationModel(scale=...)`. Farm milk now +3.5% against CAPRI's cow + sheep and goat milk.
3. **Crop areas did not follow CAPRI's trend levels.** CAPRI's trend projection carries activity levels for
   crops too (in the trajectory's herds block); the projection moved all crop areas with the land only. Now each
   crop's area follows its CAPRI trend factor and the reconciliation restores the region's cropped-area-to-land
   ratio: potatoes +38% -> +3%, pulses +29% -> +11%, tobacco +93% -> +26%.
4. **The market's EU use and the non-EU world are CAPRI's 2030** (bilateral market with CAPRI's 2030 flows,
   docs/ARMINGTON_MARKET.md): EU domestic use within 10% for 74% of the products (35% before).

Settled findings:

- **Fattening cattle are a unit difference, not an error.** The model's BULL counts CAPRI's low-intensity bull
  HERD (CAPREG, 2.1 M), its HFRS the fattening heifers' herd (2.35 M), while CAPRI's 2030 levels are activity
  levels of all fattening bulls (BULF) and heifers (HEIF + HEIR). The per-head coefficients are CAPRI's totals
  over the model's heads, so totals and relative changes are right. The check compares growth 2017-2030
  instead: bulls +15 points above CAPRI's (the trend factor 0.93 against CAPRI's reference 0.83), heifers +10,
  fattened pigs and broilers within 2.
- **Fruit, vegetable and wine price levels** in the market come from the world price table and only enter as
  ratios; farm prices are CAPRI's 2030 unit values (`capri_mod/projection/prices.py`). No effect on results.

Still off: apples' production +31% (yield), pulses' use +34%, other oilseeds +24%, olive oil +18%, sheep meat +20%.

Fattened pigs and broilers are compared as growth rates: CAPRI counts animals produced a year, the model places.
