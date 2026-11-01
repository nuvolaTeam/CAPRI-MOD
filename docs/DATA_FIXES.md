# Data extraction fixes

Status: revised 20 October 2026 against the code. This is a record of data-level faults found and fixed during the
project, kept for their causes and the guards they left behind. All of it is historical: several fixes were later
superseded by rebuilding the data from CAPRI's 2017 results (Sprint 9s; docs/SYNTHETIC_DATA_AUDIT.md), as noted per
item. Provenance of each data file: `capri_data/schema/01_provenance.sql` and `02_provenance_notes.sql`; the record
of each fix: `docs/KNOWN_ISSUES_REGISTRY_LOG.md`; effect on results: CHANGELOG.md.

Current data checks (20 October 2026): `python -m capri_mod.data.validate_data capri_data` gives 12 pass, 1 warning
(a stale row count in MANIFEST.json for `fert_side_effects.csv`), 0 fail; `python tools/check/verify_schema.py`;
`python tools/check/check_regression.py`.

## Activity-code corruption (OANI)

Four spellings of CAPRI's `OANI` ("other animals", `capreg/regio_sets.gms`) were in circulation: the ASCII code,
a form with Cyrillic homoglyphs (`OАНИ`, in `definitions.py`, `loaders.py`, `model.py`, `utils.py` and four data
files), a doubled-I form (`OANII`, feed module and `producer_prices.csv`) and both together (environmental module).
The canonical activity list used one spelling and the feed and environmental modules others, so every "other animals"
feed requirement and emission coefficient silently fell through to a default, without an error.

Fixed by `tools/normalize_activity_codes.py` (25 occurrences in 12 files, idempotent). Guards:
`test_no_corrupted_activity_codes`, `test_data_headers_are_ascii`. Still valid.

`cons_levls.gms` rescales `OANI` by 1000 and reverses it later in the same file: an internal transform around CAPRI's
own bounds, not a property of the delivered data; no unit correction was needed.

## Crop yields: from synthetic values to CAPRI's (superseded)

`yields.csv` was labelled `REAL_CAPRI` in the registry, but sixteen of its forty columns carried a synthetic
fingerprint (a constant times lognormal noise at sigma 0.10: a coefficient of variation of 0.089-0.101 across all
regions, where real regional yields scatter at 0.2-0.5). Every livestock yield and grass were generated; the +388%
grass deviation recorded at the time was a synthetic value, not a fresh-versus-dry-matter unit problem.

Steps, in order (tools kept in `tools/`):

1. COCO yields merged where the region code matched (`tools/merge_coco_yields.py`; `NUTS2 + "0000"` validated
   against `capreg/regio_sets.gms`; 160 of 248 regions; 1,026 cells). Against an independent COCO2 2017 national
   benchmark the merge brought no measurable gain (median error 20.1% before, 20.9% after), plausibly because the
   COCO export was "latest year per region/crop", a vintage mix (1988-2020 in its sibling price file).
2. capreg DATA2 yields (`res_17<MS>`, base year 2017) for crops and livestock (per head; registry entries
   `yields.csv` and `yields.csv_livestock`).
3. Sprint 9s: every crop column rebuilt for all 248 regions from the 27 member-state dumps
   (`tools/build/build_crop_economics_2017.py`), together with prices, costs and premiums.

The pre-merge backup `yields.csv.pre_coco_merge` and its revert instruction no longer apply (the file is gone). The
`detect_synthetic_columns.py` fingerprint audit remains available (`python tools/check/detect_synthetic_columns.py
capri_data`).

## Solver budget of the regional QP (historical)

After the COCO merge DE11 stopped converging: the general solver ("maximum number of function evaluations is
exceeded") had run out of iterations within 8% of base, not diverged. `SOLVER_MAXITER` was raised from 1,000 to 3,000
(`capri_mod/supply/supply_module.py`; 3,000 and 6,000 iterations gave the same activity levels). It concerns the
general-solver fallback of the conic/QP form only; the default NLP form is solved by IPOPT (README 5.3).

## Policy validation and base-year repair

Data-level fixes made while validating against CAPRI:

- **Livestock yields unit-inconsistent across regions**: about 56 regions carried animal yields in tonnes per head,
  about 192 in kg per head; reconciled at load time (`_reconcile_animal_yield_units` in
  `capri_mod/data/loaders.py`). The thin or negative livestock margins this produced had distorted the carbon MACC
  then in use (since retired).
- **Nitrogen balance**: two unit errors. Grass yield (fresh matter, kg/ha) supplied 99.3% of total N uptake, and
  manure N was divided by a further 1,000. The balance was later rebuilt on CAPRI's definition and items
  (e_SURTOTHa; README 7.5).
- **Permanent land bound**: the `PERMANENT` land figure and the crop areas disagreed in 56 of 248 regions
  (4,640 kha), so the base year violated its own constraint and the solver cut olives by 78%. The bound became
  `max(land figure, observed area)`; land is now CAPRI's land market with land types as variables.
- **Market base production**: SUA overrides had pushed world totals about 27% above the reference, and a clamp
  fabricated consumption where net exports exceeded production. World supply and demand were rebalanced; the market
  now uses CAPRI's bilateral flows and balances (README 6).
- **Permanent-crop elasticities**: literature priors made permanent crops about 10 times less elastic than annual
  crops, while CAPRI's own `p_elasSupp` has them 2.47 times more elastic; rescaled to CAPRI's structure, and since
  replaced by CAPRI's per-country values (KNOWN_ISSUES K30).

Other entries of the same period (registry names in brackets; details in the registry and CHANGELOG.md):

- fixed nitrogen coefficients per activity, so an N constraint could be met only by cutting area: a nitrogen
  intensity margin was added (`nitrogen_intensity_margin`; the N target now acts through CAPRI's fertilisation
  block), and likewise a livestock intensity margin, an identity at base (`livestock_intensity_margin`);
- yields that did not respond to price, as CAPRI's do (`yield_price_response`; now CAPRI's yield elasticities);
- state leaking from one solve into the next (`solve_state_leaks_fixed`);
- grass yield in fresh matter (kg/ha) among crops in t/ha, the cause of five separate defects; the grass unit fixed
  at its source (`grass_unit_fixed_at_source`);
- Ireland's livestock missing (245 regions instead of 248; `ireland_livestock_missing`);
- poultry head count units (million head; `poultry_head_count_units`);
- NUTS transition regions carrying synthetic-looking values (`nuts_transition_synthetic_regions`);
- a post-solve safety rail that pushed solutions off the policy constraints (`rail_overrode_policy_constraints`);
- pesticide and organic yield shocks missing from the output (`yield_shocks_missing_from_output`);
- the regional wine price dropped silently because of CAPRI's TWIN code (`wine_price_silent_drop`);
- meat prices that never moved because the livestock market bridge passed no output (`livestock_market_bridge`);
- the environmental table left empty by a swallowed error (`environmental_table_empty`);
- the nitrogen balance's two offsetting errors (`nitrogen_balance_rebuilt`).

## October 2026: correspondence, demand, reporting, environment

- **Estonian sugar beet yield (23 October 2026)**: `yields.csv` carried 500 t/ha for EE00 SUGB. Neither CAPRI nor
  CAPREG has a sugar beet activity or yield in Estonia (CAPRI's Estonian SUGB rows are trade and use only), and the EU
  median is 65 t/ha. The value has no source. It is set to 0, since the activity has no level. With zero-level
  activities free to enter (KNOWN_ISSUES K69) it produced 80 Mt of beet on 171 kha and the EU sugar price cycle of
  the Farm-to-Fork 2030 runs. The other 64 regions without sugar beet area carry yields filled from elsewhere; those
  are inert once zero-level activities are held at zero as in CAPRI (K69).
- **NUTS correspondence**: CAPRI's regional rows for 73 regions (all of France, several German states, Bulgaria,
  Greece, Italy, Sweden, Norway, part of Poland) never reached the model, which gave them national averages for
  revenue, manure and feed per head. Pairs were added only when CAPRI's agricultural area matched the model's (exact
  to 0.2%, or within 1% and unambiguous) and dairy herds (or wheat + barley area) matched within 3%; the second test
  rejected three coincidental matches. Bulgaria uses CAPRI's own region order. The runtime map is now
  `capri_data/shared/region_capri_map.csv` (`tools/build/build_region_map.py`).
- **Demand price reference**: demand measured price changes against the base world price instead of the base
  domestic price, cutting every tariff-protected region's base demand by (1 + tariff)^elasticity (EU beef 17% too
  low). Fixed; base results unchanged. Food demand is now CAPRI's Generalised Leontief system.
- **EU price reporting**: reported EU prices omitted the Armington premium farmers respond to; `domestic_prices` now
  carries the producer price (`wedge_prices` keeps the old value).
- **Ammonia**: a housing-only factor plus a "soils = 10% of livestock" proxy replaced by CAPRI's factors per region
  and animal (`nh3_factors_capri.json`, from the 2030 reference run); ammonia now follows CAPRI's N loss cascade
  (docs/N_CASCADE_SPEC.md).
- **Land-market units**: CAPRI's land-market terms are per hectare, the model's land in 1000 ha (factor 1,000).
- **Environmental module in the regional models**: the regional models had no access to it, so two calculations
  fell back silently to cruder values; it is now passed to every regional model and fallbacks warn.

## Open from this record

- **Trade-flow vintage**: `capri_data/shared/trade_flows_2017.csv` (read as `trade_flows.csv`) is, per MANIFEST.json,
  recalibrated from CAPRI's 2017 market results, while the registry entry `trade_flows.csv` still says FAO 2021. The
  bilateral market itself reads CAPRI's `bilateral_flows_<year>.csv`. The registry entry should be brought in line.
