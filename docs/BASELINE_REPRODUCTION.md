# Baseline reproduction: the 2030 baseline against CAPRI star 3.0's own 2030 reference

Status: revised 20 October 2026 against the code. The current result is that of run r48 (README section 9 (Validation)); the
section "How the 2030 baseline is built" describes the code as it is; "Findings" are kept from the October 2026
checks and dated where they carry numbers. The development history is in CHANGELOG.md and docs/COUPLING_SPRINTS.md.

## Why

The Farm-to-Fork comparison with JRC121368 measures two things at once: capri-mod's departures from CAPRI, and the
difference between the CAPRI that produced the report (2020 version, base 2012, baseline on the OECD-FAO Outlook
2017-2026) and the CAPRI star 3.0 code and data capri-mod is built from (base 2017, Green Deal reference 2030).
CAPRI's 2030 Green Deal reference of star 3.0 (`res_2_1730greendeal_ref`, `markmarket_greendeal_1730et_base_1717`)
has no version gap: with no policy shock the model should land on it, and what it misses there is the model's own
doing.

## What is compared

EU27, the 2030 baseline of a run saved by `tools/run/run_f2f_2030.py` (projection with the `capri_ref_2030` trajectory),
against:

| Block | CAPRI source (`capri_data/validation/`) |
|---|---|
| activity levels (1000 ha, 1000 heads) | `capri_eu27_levels_2030_ref.csv`: EU27yr19 LEVL, 2030; fattened pigs and broilers compared as growth 2017-2030 (CAPRI counts animals produced a year, the model places) |
| market production (kt) | `capri_eu27_market_balance_2030_ref.json`: MAPR (GROF where no MAPR) |
| market domestic use (kt) | HCOM + FEDM + INDM + BIOF + LOSM + PRCM |
| producer prices | UVAP; the model's prices are CAPRI's 2030 prices in 2017 money, so the price block compares the relative price structure (each ratio against the median ratio) |

```shell
python tools/check/compare_baseline_capri.py RUN.pkl [--csv OUT.csv]
```

## Current result

Run r48 (20 October 2026, NLP form), median absolute deviation (share within 10%): activity levels 1.0% (95% of 39),
market production 1.1% (98% of 49), domestic use 1.7% (87% of 52); relative producer prices 26.7% (26% of 38 within
10%). The price structure of the 2030 baseline is not yet CAPRI's: oilseed cakes, eggs, sheep and goat meat and
tobacco are among the largest gaps (README 11.2).

The table stored in `capri_data/validation/baseline_reproduction_2030.csv` is older: it is the run of 13 October 2026
(Sprint 9p; activities 2.6%, production 1.4%, use 1.7%, relative prices 24.9% median), not r48. Regenerate it with
`--csv` from a current run before quoting rows from it.

## How the 2030 baseline is built

Each step is what CAPRI does; the code is in `capri_mod/projection/` and `capri_mod/supply/supply_module.py`.

1. **CAPRI's 2030 reference as the trajectory** (`capri_data/trajectories/capri_ref_2030.json`,
   `tools/build/build_trajectory_capri_ref.py`). CAPRI simulates from CAPMOD's calibrated reference run, not from its trend
   projection (CAPTRD), which is that calibration's input. The trajectory carries the reference's levels and yields
   over CAPRI's 2017 results, per region and activity (sheep and goats, calves as CAPRI's totals), and the land types
   (ARAC, FRUN, GRAS, FALL; CAPRI's 2030 UAA is 2.1% below 2017). The trend projection stays available
   (`captrd_2030.json`, `run_f2f_2030.py --trajectory captrd`); it is keyed by CAPRI codes and regions, and
   `tools/build/build_trajectory_model_keys.py` adds model-keyed entries.
2. **Livestock output per head follows the projected yield** (`ProjectionModule._project_livestock`), and so do the
   requirements (dairy cows: energy, protein and dry matter from `breeding.gms`'s functions, manure N per kg milk;
   `RationModel(scale=...)`).
3. **Crop areas follow their trajectory factor**; the reconciliation restores each region's cropped-area-to-land
   ratio.
4. **CAPRI's 2030 market**: bilateral market with CAPRI's 2030 flows and the non-EU world of CAPRI's 2030 reference
   (docs/ARMINGTON_MARKET.md); CAPRI's 2030 prices and premiums in 2017 money (`capri_mod/projection/prices.py`).
5. **Purchased feed at CAPRI's 2030 bulk prices** (`projection/prices.py`): the rations' FCER, FPRO and FOTH prices
   take CAPRI's feedBlkPrice_ CES index of the member state's feed products at their 2030 prices; FENE and FMIL at 1
   (their products have no CAPRI unit value: registered).
6. **CAPRI's 2030 rations and fodder** (`tools/build/build_ration_trajectory_2030.py`): rations and requirements per
   region group and model animal by CAPRI's 2030/2017 per-head factor (`capri_ref_ration_2030.csv`; LEVL-weighted
   over CAPRI's activities; member state where there are no regional rows; the ration is lifted uniformly only where
   it would fall short of the energy or protein requirement), and the fodder balances' usable fodder per ha by
   CAPRI's FEDM / LEVL of grass, silage maize and other fodder, 2030 over 2017 (`capri_ref_fodder_2030.csv`).
7. **Baseline calibration** (`SupplyModule.calibrate_to_base`, switch `CAPRIModel.calibrate_baseline`): CAPMOD
   calibrates its supply models so that the simulation year's baseline reproduces the projected levels. In the
   baseline of a projected year the regional models' linear cost terms move by Q (x − x_target) round by round until
   the largest drift stops falling; fodder crops are excepted (held by the fodder balances). The outer loop counts
   the baseline as converged when the largest remaining drift is within 0.2% (`CAPRIModel.BASE_CAL_TOL`). The
   scenario starts from that calibrated baseline.

## Findings (October 2026)

- **Fattening cattle are a unit difference, not an error.** The model's BULL counts CAPRI's low-intensity bull herd
  (CAPREG), its HFRS the fattening heifers' herd, while CAPRI's 2030 levels are activity levels of all fattening
  bulls (BULF) and heifers (HEIF + HEIR). The per-head coefficients are CAPRI's totals over the model's heads, so
  totals and relative changes are consistent. The check therefore compares growth 2017-2030; in the 13 October table
  bulls grow 13.8 points and heifers 8.7 points more than in CAPRI, fattened pigs and broilers within 5.
- **Prices.** The model's market prices enter the supply side and the market's behaviour only as ratios to their
  base; farm revenues use CAPRI's 2030 unit values (`capri_mod/projection/prices.py`). The price row compares market
  prices with CAPRI's producer unit values (UVAP), which differ by definition (cakes: world price 213 against a unit
  value of 483 EUR/t), so part of the deviation is a reporting difference. Whether all of the 26.7% is of that kind
  is not established (README 11.2 calls the price structure "not yet CAPRI's").
- **Biofuels** (run s59, Sprint 9d, October 2026; not re-checked since): biofuel output and use within 0.1% of CAPRI's, DDGS
  within 2.3%.
- **Remaining gaps by product**: see the latest `compare_baseline_capri.py` output; the 13 October table's largest
  were sheep and goats (−16% activity level, base-data difference), calves (−13%), pulses' use (+22%), rapeseed cake
  (production −11%, use −17%) and raw milk production (−10%).
