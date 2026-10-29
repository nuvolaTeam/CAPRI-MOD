# PMP supply elasticities and the PMP matrix

Status: revised 20 October 2026 against the code. This file was a sprint report (coverage counts, test counts and a
shock test of that time); those figures were superseded by K30 and K32 (KNOWN_ISSUES) and were removed. What follows
describes `capri_mod/supply/capri_pmp.py` and `PMPCalibrator` in `capri_mod/supply/supply_module.py` as they are.

capri-mod calibrates its own PMP matrix from CAPRI's elasticities (decision 5a.5 of `docs/SUPPLY_MODEL_MAP.md`); it
does not use CAPRI's calibrated p_pmpQuad* values. The matrix is the same in the NLP and the conic form.

## Elasticity table and its provenance (`capri_pmp.build_elasticity_table`)

Every region x activity elasticity is recorded with its source (`SupplyModule.elasticity_provenance`;
`test_elasticity_provenance_is_complete`). Precedence, highest first:

| Provenance | Source | Scope |
|---|---|---|
| `REGIONAL_CAPRI` | `supply_elasticities_regional.csv` (bounded at 4.5 upstream) | model regions in the file |
| `PMP_CAPRI` | `pmp_own_price_elasticities.csv` (CAPRI region codes, raw, dampened on load) | mapped through `shared/region_capri_map.csv`, else the NUTS crosswalk; a region without a row takes its member state's national row (K32); CAPRI's OFAR is the model's OFOD, MAIZ its CORN |
| `CAPRI_COUNTRY` | `capri_own_price_elasticities.csv` (CAPRI's calibrated p_ElasSupp per member state) | only activities neither regional source covers in any region: permanent crops, vegetables, tobacco, textile crops, table olives (K30) |
| `CAPRI_CAL_PRODUCT` | `sources/arm/capri_supply_elas_market_1717.csv` (p_elasSupp of the animal products per member state), weighted with the young animals' elasticities (`capri_supply_elas_young_1720.csv`) by their share of output value | animal activities |
| `LITERATURE_DEFAULT` | EU-wide defaults (`utils.calibrate_supply_elasticities`) | the rest: grass, set-aside, olives for oil, minor crops CAPRI has no elasticity for, Norway (K32) |

(The legacy mode `SupplyModule(data, eps, use_capri_elasticities=False)`, EU-wide defaults everywhere and no share
term, was removed on 27 October 2026.)

## CAPRI's rules ported

1. Dampening (`gams/supply/pmp_terms/impose_upper_bound_on_elasticity.gms`). CAPRI does not truncate high
   elasticities: above `p_elasHigh = 4.5` it inflates the PMP slope so that the effective elasticity becomes
   min(8, sqrt(e) + 4.5 - sqrt(4.5)); the source comment gives 10 -> 5.6, 20 -> 7.0, 40 -> 8. `dampen_elasticity`;
   `test_capri_dampening_matches_gams_reference`. (An earlier truncation at 2.25 cut values CAPRI leaves alone.)
2. Share term. CAPRI scales crop curvature by 1 - 0.2 sqrt(LEVL / arable total), so a crop with a large share of the
   region's arable land responds less. `share_term` (floor 0.1); CAPRI's
   elas = revenue / (LEVL x shareTerm x (pmpQuadTechn + pmpQuadPact)) rearranged gives the diagonal below. Constants
   ELAS_HIGH, ELAS_CAP, SHARE_COEF in `capri_data/shared/model_parameters.csv`.
3. Crop groups (`EPRD_TO_GRP`, `gams/sets.gms:2918`, the ESTNLP mapping): (SWHE, DWHE, RYEM, BARL, OATS) CERE;
   (MAIZ, OCER, PARI) CER2; (RAPE, SUNF, SOYA) OILS; (PULS, POTA, SUGB) OARA; (MAIF, ROOF, OFAR) FARA. The variant in
   `gams/capdis/sets.gms` uses another group set and is not used.

## The matrix (`PMPCalibrator.calibrate`)

- Diagonal: Q_ii = p_i / (eps_i x0_i shareTerm_i), with p the gross revenue per unit (a price shock moves gross
  revenue, so this makes the realised own-price response match eps), eps clipped to [1e-4, 8], x0 at least 0.001;
  then clamped to [1e-7, 1e4] x the median positive Q_ii (capri-mod's guard against near-zero bases).
- Off-diagonals: since 29 October 2026 (KNOWN_ISSUES K105) only CAPRI's own, with its PMP terms (pmp_source capri2030
  or recipe: QUADRA_ with GRPLEVL_, only between crops of CAPRI's crop groups); a crop without CAPRI terms in the region
  has a diagonal row, as in CAPRI's QUADRA_. `CROSS_TERMS = "none"` drops CAPRI's off-diagonals too (diagonal only).
  Until then, crops without CAPRI terms (and every crop when `pmp_capri_parts` left out "crops") could take a PELA
  activity-level cross-price elasticity (`sources/estnlp/pela_cross_by_region.json`) or CAPRI's group term
  p_pmpQuadPact (`sources/capreg/pmp_quad_pact.csv`), each as sign x min(|value|, 0.05) x sqrt(Q_ii Q_jj): capri-mod's
  caps (PROXY_AUDIT S065), then each row's off-diagonal sum scaled down to at most half its diagonal; removed with the
  JSON file (CAPRI's terms, set after, were never scaled); and "none" did not act on CAPRI's terms.
- What the structure changes (tools/check/pmp_cross_term_check.py, CAPRI's decomposition experiment, 2008 documentation
  sect. 7.3): the six regions DE11, FRH0, ITC4, PL41, ES41, IE04 at +20% on the cereal prices, regional models alone:
  every group's response within 0.06 points across the three structures (cereals +8.90 / +8.88 / +8.88%, oilseeds
  -5.83 / -5.81 / -5.81%). With the caps, the cross terms are too small to matter; CAPRI's own group curvature
  (p_pmpQuadPact on the groups' levels, e.g. AT11 CERE-CERE 137 against SWHE's own term 52) is not represented at its
  size. Doing that needs CAPRI's PMP terms of its 2030 calibration (p_pmpQuadTechn and p_pmpQuadPact as CAPMOD
  simulates with them), not in hand (KNOWN_ISSUES K61).
- Linear term f = r - Q x0 - lambda (net revenue r), so the base is optimal; in the NLP form the regional calibration
  then makes the base a first-order point of the full model (`CapriRegionalNLP.calibrate`).

## Synthetic-base guard

`detect_synthetic_base_activities` blocks real elasticities for activities whose base level is the same constant in
every region (PMP curvature scales as 1 / (eps x0), so a real elasticity on an invented base level gives large
responses). It was added when `base_areas.csv` held constant placeholders for COTT, OFIB, OFOD and SETA. With the
current file it finds none (checked 20 October 2026: OFOD and SETA vary by region, COTT and OFIB are merged into TEXT,
K35). `tools/check/detect_synthetic_columns.py` reports constant columns as well as lognormal fingerprints.
(`tools/check/scenario_elasticity_check.py`, which compared the response to a cereal price shock with and without
CAPRI's elasticities, was removed with the legacy elasticity mode on 27 October 2026.)

## Open

- Realised against target elasticities: `capri_data/validation/capri_pela_own_elasticities.csv` is not used by any test
  or tool.
- The literature defaults that remain (above), in particular grass (no CAPRI grass elasticity in either regional
  source).
