# CAPRI-mod validation: the early checks and where validation stands now

Status: revised 20 October 2026 against the code. The current validation is README section 9 (Validation) (mechanisms against
CAPRI, the 2030 baseline against CAPRI's 2030 reference, Farm-to-Fork against JRC121368, Green Deal 2030). This file
documents the three early checks (data files of 8 October 2026 in this folder) and corrects what they were said to
show; their numbers are historical.

## Current references (README section 9 (Validation))

1. CAPRI's own data and code: inputs reproduce CAPRI's symbols; mechanisms reproduce CAPRI's per-unit results from
   its own inputs (N loss cascade, ammonia options' initial shares, anaerobic digestion, leaching, fertiliser
   allocation, base reproduction, market parameters; tests in `capri_mod/tests/test_capri.py`).
2. CAPRI star 3.0's 2030 reference for the 2030 baseline (`tools/check/compare_baseline_capri.py`;
   docs/BASELINE_REPRODUCTION.md). Run r48 (20 October 2026): median deviation activities 1.0%, production 1.1%,
   domestic use 1.7%, relative producer prices 26.7%.
3. JRC121368 (CAPRI's published Farm-to-Fork results; not like-for-like, other CAPRI version) with
   `tools/check/compare_runs.py --capri`.
4. The EU agricultural outlook 2020-2030 (docs/OUTLOOK_2030_CHECK.md).
5. A CAPRI scenario pair: CAPRI's 2030 run without voluntary coupled support against its reference
   (`validation/coupled_support_2030/capri_vcs_effect.csv.xz`, `tools/run/run_vcs_2030.py`; KNOWN_ISSUES K48).

## The early checks (8 October 2026), and what they show

| Check | Data | What it was said to show | What it shows |
|---|---|---|---|
| Base-year prices | `test_market_module_reproduces_its_own_prices` | CAPRI's 2017 prices reproduced at 0% deviation | the market, given base-year supply, returns the world prices it was given (`world_prices.csv`) within 15% for 12 commodities: solver consistency, not price validation (the test's own docstring). The prices themselves are CAPRI's FAO_agg PMRK |
| Supply elasticities | `elasticity_comparison.csv`, `capri_pela_own_elasticities.csv` | major cereals within about 10% of CAPRI's PELA | a measurement from before CAPRI's elasticities were wired into the PMP calibration for every region (KNOWN_ISSUES K30, K32) and before the NLP form; out of date. Its pulse entry had the wrong sign; measured from solved levels the sign is positive, pinned by `test_no_negative_own_price_elasticities`. Current checks: `test_supply_elasticities_reach_every_region_from_capri`, `test_permanent_crop_elasticities_match_capri` |
| Price structure | `price_structure_vs_capri_scenario.csv`, `test_price_structure_vs_capri` | the model reproduces CAPRI's relative prices "very faithfully" (rank correlation 0.998) | the ratios to wheat of the input base world prices (2017) against CAPRI's 2030 producer prices (UVAG of the Green Deal reference) for 8-9 products; the test asserts a Pearson correlation above 0.95, which the large beef and pork ratios dominate. It is a check of input data, not of model results. The model's 2030 relative prices deviate from CAPRI's by 26.7% (median, r48; README 11.2) |

`VALIDATION_SUMMARY.json`, which recorded the same early checks with the same overstatement on price structure, was
removed 30 October 2026 (the project lead's decision, read by no code; in git history).

## Shock magnitudes

The early report called this check pending because the CAPRI Green Deal runs then in hand (reference, ini and max
variants) differ by less than 1%. A CAPRI scenario pair with a clear policy contrast is now in hand (item 5 above;
as recorded in K48, from a run before the K46 fix: 28 indicators, mean absolute deviation 1.24 points, correlation
+0.85; the replacement-cow price is far more responsive than CAPRI's), and JRC121368 gives a published
scenario. Still open: a CAPRI run of the Green Deal 2030 step (README 11.4) and CAPRI's Farm-to-Fork dairy market
results (K13). How to produce a CAPRI run for comparison: `HOW_TO_RUN_A_VALIDATION_SCENARIO.md`.
