# Synthetic, proxy and hard-coded data: audit

Status: revised 20 October 2026 against the code. "Current state" is checked against the code and data on that date.
Sections A-C record the audit as it was made in October 2026, before the fixes of Sprints 9s and 9t; they are
historical (every item in them has since been fixed) and are kept for the reasons and CAPRI sources they give. The
effect of the fixes on results is in CHANGELOG.md.

## Current state (20 October 2026)

- **No generator or generic fallback is left in the data path.** The loaders raise when a file is missing
  (`capri_mod/data/loaders.py`); the validator reports "no live synthetic data" and "38 CAPRI, 4 FAO, 0 synthetic"
  datasets in the sourcing registry (`python -m capri_mod.data.validate_data capri_data`: 12 pass, 1 warning, the
  warning being a stale row count in MANIFEST.json for `fert_side_effects.csv`). Tests:
  `test_no_synthetic_inputs_reach_the_model`, `test_ghg_accounts_take_capris_methane_and_co2`,
  `test_fixed_activities_land_market_and_grass_as_capri`, `test_parameter_file_and_code_agree`.
- **Constants** the economics and accounts rest on are rows of `capri_data/shared/model_parameters.csv` (value, unit,
  kind, source), read through `capri_mod/params.py` (Sprint 9t).

What is still not CAPRI's data, and where it acts:

| Item | Where | Effect on results |
|---|---|---|
| ~~Land-rent elasticity 0.15 and expansion cap 0.15~~ | removed 23 October 2026: without CAPRI's land market (or where it fails) land is fixed | - |
| Per-head N coefficients of the legacy nitrate-limit instrument (`nutrient_coefs.csv` animal rows; `SupplyModule.base_n_intensity`) | `PolicyScenario.nitrate_limit_change` and the registry scenarios that use it | none in the CAPRI scenarios; open, KNOWN_ISSUES K33 |
| ~~`NATIONAL_ENVELOPES` ("approximate 2023-2027")~~ | replaced 23 October 2026 by CAPRI's 2030 budgets (CEILVAL, `cap_ceilings_2030.csv`) | - |
| `INTERVENTION_PRICES` | `capri_mod/policy/policy_module.py`; not called by `run()` | none |
| The registry scenarios (`capri_mod/scenarios/scenarios.py`) | `run(scenario=NAME)` | simplified policy packages, not CAPRI's settings (README 8.2, K52); CAPRI's settings are in `capri_mod/policy/greendeal.py` |
| Biodiversity indicator `shannon_crop_diversity` (the `hnv_farmland_pct` proxy removed 29 October 2026, K96) | environmental accounts | reporting only; not a CAPRI indicator (README 7.5) |
| Armington `eta` of products other than the cereals and DDGS/FENI/FPRI | market | unrecorded source, acts on 1.3% of world use (registered, K44) |

Registered on purpose (CAPRI's data, a different basis): herds are CAPRI's herd sizes (DATA2 HERD, census-based;
Eurostat cattle numbers only to split regions), not its activity levels, with every per-head coefficient built as
CAPRI's total over those heads (totals match CAPRI's).

The sourcing registry's `code_embedded_data` entries ("biofuel conversion coefficients" in `biofuel/biofuel_module.py`,
"environmental proxy factors (FRAC_GASF, HNV, NH3 shares)") moved to docs/design/PROXY_AUDIT.md on 29 October 2026:
the biofuel module no longer exists, FRAC_GASF is not in the code, the HNV proxy was removed (K96).

## How the audit was made (October 2026)

By running the code, not by reading the registry: a full Farm-to-Fork 2030 run under line coverage (every numeric
table and constant in `capri_mod` classified as read or not), the fallback conditions evaluated for all 248 regions,
and the 2017 input files compared cell by cell with CAPRI's 2017 regional results (`res_17<MS>`, all 27 member
states, NUTS groups as in `tools/lib/_model_regions.capri_groups`).

Why there was synthetic data at all:

1. The project began as a synthetic prototype: every loader carried a generator ("structure + noise") for a missing
   file, and real files replaced the generators one by one.
2. Some files on disk were generator output: `policy/cap_payments.csv` was the loader's random draw written out.
3. The first CAPRI extraction covered 192 regions. Premiums, variable costs and some yields were built from it; the
   other 56 regions (Denmark, Croatia, Slovenia, Lithuania, Bulgaria's NUTS-2016 regions, Ireland, renamed Polish and
   Italian regions, city states) were filled with national or group values. Later all 27 member-state dumps arrived
   and the herd, manure, feed and land builders were redone with them; premiums, costs and yields were not.
4. CAPRI codes not mapped: the premium file kept CAPRI's codes (OFAR, TWIN, TEXT), so OFOD, WINE and the fibre crops
   never found their premium.
5. The environmental accounts started from IPCC Tier 1 and literature defaults and were replaced block by block;
   manure CH4 and the CO2 from liming and urea had not been.
6. Explicit assumptions were written where no CAPRI value had been looked for (yield response to price, land supply).

## A. Synthetic values that reached the results (fixed in Sprint 9s)

| # | What | Size at the audit | CAPRI source now used |
|---|---|---|---|
| A1 | Crop CAP premiums fell back to `cap_payments.csv` BPS (random generator output) | 1,957 region × crop cells | DATA2 PRME per activity, all 27 dumps, codes mapped (`tools/build/build_crop_economics_2017.py` → `crop_premium.csv`) |
| A2 | Crop variable costs filled, not CAPRI's | 698 region × crop cells (e.g. other fruit 8,747 EUR/ha in every Austrian region against CAPRI's 27,000-37,000) | DATA2 TOIN, all 27 dumps |
| A3 | Other-fibre yield a lognormal draw | 139 regions; 1.5 t/ha against CAPRI's 3.8 | DATA2 TEXT YILD (textile crops are now one activity, TEXT, as in CAPRI) |
| A4 | Non-EU tariffs drawn at random per load | all non-EU regions | CAPRI's total protection from its 2017 bilateral flows (Sprint 9r) |
| A5 | Wine producer price filled in 36 regions (Galicia 1,362 EUR/t against CAPRI's 403) | 36 regions | DATA2 MPRI of TWIN |

`cap_payments.csv` is now CAPRI's premium per ha of UAA (BPS column; ANC, AES, ORGANIC, COUPLED are 0) and feeds the
budget report only.

## B. Hard-coded coefficients where CAPRI's values exist (fixed in Sprints 9s and 9t)

| # | What | Before | Now |
|---|---|---|---|
| B1 | Manure CH4 per head | IPCC flat values, the same in every region | CAPRI's CH4MAN per activity and region (`livestock_ch4man_coef.csv`, `tools/build/build_ghg_coefs_2017.py`) |
| B2 | CO2 from liming | 600 kg limestone × 0.12 on every arable ha | CAPRI's liming CO2 per ha, per region (`crop_co2_coef.csv`, column `co2lim_kg_ha`) |
| B3 | CO2 from urea | 30% of mineral N as urea | CAPRI's urea share of mineral N, per region (`crop_co2_coef.csv`, column `urea_share`) |
| B4 | Yield response to price | elasticity 0.15 for every crop | CAPRI's `supply/yield_elas.gms`: cereals 0.3, oilseeds and potatoes 0.2, others 0 |
| B5 | Enteric CH4 of non-cattle | IPCC table per census head | CAPRI's CH4ENT (`livestock_ch4ent_coef.csv`) |
| B6 | Grass dry-matter share | 0.20 | CAPRI's DRMA of GRAS (0.22; `grass_dm_content.csv`) and CAPRI's fresh grass yield in every region |

The GHG total is reported as all items, as non-CO2 (the figure compared with JRC121368) and as CAPRI's GGWP (the
emission tax's base) (README 7.5).

## C. Assumptions with no CAPRI counterpart at the audit (resolved)

- **Other oilseeds**: the model had pooled a world market with an invented world total (20,000 kt). CAPRI has no
  market for them (`arm_sets.gms` nonXX_CROPS) and holds OOIL, OIND and OANI fixed at their data level (`sets.gms`
  FACT, `supply/prep_sim.gms` v_actLevl.FX); capri-mod now does the same (`FIXED_ACTIVITIES`).
- **Land supply**: CAPRI's land market (`p_pmpQuadLandTypes`) now covers every region with farmland (Ireland's three
  NUTS-2016 regions from IE01 + IE02's matrices; combined CAPRI regions as the sum of their land owners' responses).
  Without the land market (switched off, or failed in a region) land is fixed (the rent-elasticity rule was removed
  on 23 October 2026).
- **CAPRI's numbers kept in code** (feed-cereal weights, cost shares, JRC121368 assumptions, CAPRI calibration
  constants): moved to CSV (`feed_cereal_mix_2030.csv`, `crop_cost_shares.csv`, `model_parameters.csv`).
