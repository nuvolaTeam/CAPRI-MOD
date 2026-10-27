# CAPRI's own 2030 PMP terms for the crops (KNOWN_ISSUES K61, decision 5a.5)

Status: implemented 21 October 2026 as `SupplyModule.pmp_source = "capri2030"` (run script: `--pmp capri2030`); the
elasticity calibration stays available (`"elasticity"`). Results: CHANGELOG, 21-22 October 2026 (night), and below.

## Why

Until now capri-mod calibrated its own PMP matrix (PMPCalibrator, Howitt 1995): each crop's diagonal term from a
target elasticity, Q_ii = revenue / (elasticity x level x CAPRI's share term), the target being CAPRI's estimated
elasticity (estnlp PELA, around 2004) or the member state's value; small cross terms, only within CAPRI's crop groups
(K61); the linear terms set so that the base is reproduced. CAPRI's terms were not in hand.

CAPRI's matrix is different in kind (supply/define_pmp_terms.gms, supply/pmp_terms/*): technology terms per crop (T1
high-yield, T2 low-yield), large terms on the crop groups' levels (VB, estimated), both projected to the simulation year
(forecast_group_pmp_matrix_from_estimates.gms, forecast_activity_slopes.gms) and fitted (compute_technology_pmp_matrix.gms,
impose_upper_bound_on_elasticity.gms). The responses differ: Austria's crops, own-price supply elasticities of the
regional supply models at the 2030 baseline (tools/check/pmp_supply_elas_check.py), against CAPRI's own supply-model
elasticities (supply_elas_2_1720ATdefaulta, 2020: a guide to magnitudes, not a 2030 target):

| crop | elasticity calibration | CAPRI's 2030 terms | CAPRI (2020) |
|---|---|---|---|
| barley | 0.92 | 2.95 | 3.40 |
| rye | 1.75 | 3.91 | 6.42 |
| grain maize | 1.35 | 1.82 | 1.43 |
| rapeseed | 2.61 | 9.65 | 12.45 |
| potatoes | 0.90 | 2.01 | 2.07 |

## Data

- Export: `tools/gams/export_pmp_2030.gms` (GAMS, plain gdxdump) dumps every `output\results\baseline\pmppar_21730*.gdx` of
  the CAPRI installation (35 countries) and `dat\estnlp\results.gdx` (VB, VD, PELA).
- `tools/build/build_pmp_2030.py` writes the symbols unchanged as CSV, CAPRI codes: `capri_data/sources/baseline_pmp/`
  (p_pmpQuadTechn, p_pmpQuadPact, p_pmpCnst, p_pmpQuadLandTypes, p_pmpCnstLandTypes, VB and VD levels).
- `tools/build/build_pmp_capri_2030.py` derives the model's matrix: `capri_data/2017/supply/pmp_capri_2030.csv`.

## From CAPRI's terms to the model's matrix

CAPRI's PMP cost (QUADRA_, p_useCropSpecificQMatrix = 0):
1/2 sum_crop x_crop' Qt_crop x_crop + 1/2 sum_grp,grp1 L_grp L_grp1 P(grp, grp1), x_crop the levels of the crop's
technologies, L_grp the summed levels of a group's crops (GRPLEVL_). The model has one activity per crop. For a
quadratic cost whose linear terms adjust (the calibration), each step below is exact for the area response:

1. technologies: the cost of a crop's level X split optimally over T1 / T2 is 1/2 c X^2, c = 1 / (1' Qt^-1 1);
2. the CAPRI region's Hessian on its crops: H = diag(c) + E P E' (E: the crops' group indicators; P symmetric from
   CAPRI's upper-triangular storage);
3. aggregation to model activities (OFOD = OFAR + ROOF, GRAS = GRAE + GRAI, SETA = VSET + FALL) and to territories
   (tools/lib/_model_regions.capri_groups; Norway's NO01/03/04/05 = NO08 + NO09 + NO0A as build_capri_base): the response
   of a sum is the sum of the responses, H_model = (sum over CAPRI regions of A H^-1 A')^-1;
4. stored as g_ij = H_model,ij sqrt(X_i X_j) (X: the territory's CAPRI 2030 levels); at runtime
   Q_ij = g_ij / sqrt(x_i x_j) with the model region's base levels, so a region that is part of a CAPRI territory
   responds, in relative terms, as that territory.

In `PMPCalibrator.calibrate` the block replaces the elasticity-calibrated terms of the crops it covers (cross terms
included); the linear terms are recalibrated, so the base is reproduced.

## Animals, feed and land (21 October 2026, night: items 1 and 3 of the follow-up)

Under the same switch, at the 2030 market year:
- **Animals' herd terms** (`tools/build/build_animal_pmp_capri_2030.py` -> `pmp_capri_2030_animals.csv`): CAPRI's
  p_pmpQuadTechn('T','T') of its animal activities, per model animal: an intensity pair whose split the model carries
  (DCOL/DCOH, BULL/BULH, HEIL/HEIH) by its Schur complement q_low q_high / (q_low + q_high), the other members in fixed
  proportions (sum q_j s_j^2); territories by the inverse of the summed inverses; Q = g / x^2 at the model's herd.
  Diagonal only, as QUADRA_ (no cross terms between animals or with crops). The intensity splits' own curvature
  (22 October 2026): CAPRI's 2030 p_pmpQuadTechn of the two variants (tools/build/build_intensity_q_2030.py ->
  sources/baseline_pmp/intensity_q_capri2030.csv and _recipe2030.csv; the builders of the dairy, cattle and grassland
  splits add q_<x>_capri2030 and q_<x>_recipe2030 beside the base year's columns, same fallback rule), taken at the
  2030 market year with pmp_source capri2030 / recipe (animals: DCOL/DCOH, BULL/BULH, HEIL/HEIH with "animals" in
  pmp_capri_parts; grassland GRAE/GRAI with "crops"). Medians 2030 over 2017: dairy 1.8, bulls 1.4, heifers 1.3,
  intensive grassland 1.2, extensive 0.9.
- **Feed PMP slopes** (`tools/build/build_feed_ration.py`: `capri_slope_2030` beside `capri_slope` in feed_ration_2017.json):
  CAPRI's 2030 p_pmpFeedInpCoeff SLOP, aggregated as the 2017 ones (2017 weights, registered); the ration model takes
  them (`RationModel(slope_key="capri_slope_2030")`).
- **Land market** (`tools/build/build_land_market.py --year 2030` -> `land_market_2030.csv`): CAPRI's 2030 land-type
  levels and p_pmpQuadLandTypes, with the 2017 file's territory rules (Norway's split regions from NO08 + NO09 + NO0A:
  NO000000's 2030 matrix has no diagonal). The 2017 mode of the builder reproduces land_market_2017.csv exactly.
- Base reproduced with all of them (DE11, FRH0, NL22: every herd at its base level).

**Item 2 (the market's supply anticipation), on reflection**: between two supply solves the market anticipates the
supply models' response with CAPRI's market-level elasticities; at a converged point the anticipation vanishes, so the
results do not depend on it, only the path (docs/MARKET_SOLVE_CHECK.md; CAPRI's measured Hessian, `market_supply_nq`,
gave no gain in speed when tested on 18 October). With CAPRI's crop terms Farm-to-Fork converged in 11 iterations
(12 with the elasticity calibration), so the mismatch did not slow it. Not changed.

## Full runs (21-22 October 2026)

Farm-to-Fork 2030, mean absolute deviation from JRC121368 over 20 indicators: our terms 5.30 (12 iterations), CAPRI's
crop terms 5.11 (11), all CAPRI terms 4.62 (14). Green Deal 2030: our terms 14 iterations / 32 min, all CAPRI terms
16 / 39 min, results within about 1.5 points except the milk price (+8.2 against +12.2%) and sheep and goats (-4.1
against -6.6%). Details: CHANGELOG. At DE11 and FRH0 CAPRI's 2030 animal terms are 2 to 9 times flatter than the
elasticity calibration (fattening pigs: 420 against 1,480 EUR per head for a 100% herd change).

## capri-mod's own terms with CAPRI's recipe (22 October 2026: `--pmp recipe`)

The project lead's decision: CAPRI's exported 2030 terms are the default for now, and capri-mod needs its own
calibration. The elasticity calibration (Howitt-type, each activity's term from a target elasticity) was internally
right - tools/check/pmp_elasticity_target_check.py, removed with it on 28 October 2026 (Austria, 2030): the realised elasticities equal their targets for almost
every activity - but its targets (CAPRI's estimated elasticities) and its nearly diagonal structure (cross terms capped at
5% of the diagonal) left out CAPRI's within-group substitution (rapeseed 2.4 against 9.4 with CAPRI's terms).

`tools/build/build_pmp_recipe.py --year 2030|2017` computes the terms as CAPRI does (supply/define_pmp_terms.gms,
pmp_terms/*), from CAPRI's estimates (estnlp VB, VD, PELA; exported with the 2030 terms) and the calibration point's
data: group terms VB scaled by the groups' levels and CAPRI's inflation (p_infl 1.019 per year since 2004); activity
slopes VD scaled the same way, else CAPRI's assumed elasticities (supply/pmp_elas.gms) on max(revenue, |linear objective
contribution| + rent, rent) per unit (D_OBJC and the activity's D_AREA of CAPRI's results); quota activities (sugar
beet, dairy cows) without estimates as CAPRI; the T1/T2 technology fit in its closed form (b = (slope - own) / 3);
fallow's single premium-eligible technology; the cap on elasticities above 4.5; and (22 October 2026, afternoon)
CAPRI's land-nest adjustment (forecast_activity_slopes.gms l. 103-141, crops other than grass): slope + (1/e_b -
1/(e_b + c)) x M / L with e_b the slope's myopic elasticity and c = p_landNestElasContrib (cal_land_nests.gms l. 729,
trustee land market: the activity's level over the summed levels of the agricultural land types it belongs to -
ARAB, ANNC, ARAC for annual crops, ARAB and FRUN for permanent ones - times those land types' posterior own-rent
elasticities, which exist for ARAC and FRUN). The posterior elasticities are recomputed from CAPRI's exported land
matrix (2030: pmp_quad_landtypes_2030.csv; 2017: sources/capreg/pmp_quad_landtypes_2017.csv), levels and rents with
the land owner's bordered Hessian of declare_calibration_models_for_land_supply.gms (p_landMarketScale 1000): CAPRI's
estimation makes v_posterior_elasticity an exact function of the same matrix, but does not export it. The literal
denominator (the sum over ARAB, ANNC and ARAC, about three times the arable area) was kept because it reproduces
CAPRI's terms: crops within 1% of CAPRI's in 78% of pairs at 2017 (68% without the adjustment, 63% with the share
in ARAC alone), 62% at 2030 (49%, 42%). The model form is built by the same transfer tools as for the exported terms
(`--techn ... --out pmp_recipe_<year>.csv`, animals likewise).

Inflation at 2017: the recipe's 2017 terms take 14 years of p_infl (CALYEA 2018), not 13. Inferred from CAPRI's
CAPREG terms, not from code (simulationYear comes from the GUI): with 14 years the group terms match CAPRI's within 1%
in all 1,447 pairs, with 13 years in 3% (every one 1/1.019 off).

Check against CAPRI (`tools/check/pmp_recipe_check.py`):

| | activity terms within 5% | within 20% | group terms within 5% |
|---|---|---|---|
| 2030 against CAPRI's exported 2030 terms | 80.5% of 11,694 (before the land nest: 76.8%) | 89.8% | 88.6% of the diagonals |
| 2017 against CAPRI's CAPREG terms | 89.6% of 5,718 (87.1%) | 97.4% | 100% of 1,447 (within 1%: 100%) |

Exact or nearly: the animals, vegetables, tobacco, flowers, olives and fruit, grassland in 2017 (|D_OBJC| + rent
reproduces CAPRI's terms to four digits); the main cereals and oilseeds at medians 1.00. Still off: a tail of regions
in the estimated crops (barley, oats, rye, potatoes, fodder maize: 10th percentiles 0.84 to 0.89 in 2017; some
regions 0.3 to 0.7), which neither the land nest nor the inflation year explains - candidates are CAPRI's L_BAS (a
three-year average where the recipe has the single year's level) and the regions whose model and CAPRI codes differ;
grassland at 2030 (CAPRI's calibration rent is not in its results: ratios 0.6 to 1.5); other oilseeds (1.2); set-aside
(VSET) and energy crops (NECR, not a model activity). At 2030 the recipe uses CAPRI's 2030 feed slopes and land-type
terms (their calibrations are not ported); at 2017 the 2017 ones.

## Limits

- **Technologies**: CAPRI's shift between T1 and T2 (its yield response through technology choice) is not carried;
  the model's own yield response stays.
- **Year**: the terms belong to CAPRI's 2030 calibration point; used only at the 2030 market year. The 2017 base and
  other years keep the elasticity calibration (CAPRI's 2017 terms from capreg are in `sources/capreg`).
- **Animals**: herd terms, feed slopes and the intensity splits' curvature covered (above).
- **Regions without terms**: DE30, DE50, DE60 (city states), ES63, ES64, BE10: elasticity calibration.

## Regenerating

Both matrices are computed from the data at every run; nothing is overwritten. CAPRI's terms are rebuilt from a CAPRI
installation with the export script and the two builders.

## The elasticity calibration removed (28 October 2026, audit S13)

`supply.pmp_source = "elasticity"` is gone. With CAPRI's terms (or the recipe's), an activity of a calibrated part
(crops, animals) without a positive own term is held at its level (SupplyModule._uncalibrated), as the activities
without any CAPRI value already were. At the 2030 baseline (r166) that is 71 region-activity cells in 63 regions, at
most 2% of an activity's EU level: tobacco 0.76 of 38 kha, pulses 23 of 1,809 kha (mostly Dutch regions), durum wheat
3.5 of 2,115 kha; everything else 0.07% or less. Until then they took a curvature from their CAPRI elasticity (capped at
8, with CAPRI's share term). At the 2017 market year the recipe has no term for nurseries (NURS, 181 kha in 213
regions), which are now held there too; CAPRI's 2030 terms do cover NURS (the recipe builder's gap, to look at).

