# Land market and land-use flexibility (arable, grassland, permanent crops, forest, other land)

Status: revised 20 October 2026 against the code. The land market is on by default, as in CAPRI
(`CAPRIModel.use_land_market = True`; `p_landIsFixedinScenario = 0`). Run timings and results of the step in which it
was built were removed; the checks made when the data were built are kept with that qualification.

## Why it was needed

CAPRI's landscape rule (`pol_input/greendeal/landscape.gms`) sets a fallow floor = (requested share / 10%) x the member
state's net target `p_setAsideTarget` x the region's total UAA + existing set-aside. It applies to total UAA, while
set-aside can only use arable land. With arable land fixed, regions with little arable land could not meet it (model
base data, when built):

| Region | Arable | Grassland | Other agric. land | Landscape floor |
|---|---|---|---|---|
| Trento (ITH2) | 1.33 kha | 61.3 kha | 3.3 kha | 3.94 kha |
| Epirus (EL54) | 18.8 kha | 408.6 kha | 461.9 kha | 35.3 kha |
| Duesseldorf (DE11), reference | 306.9 kha | 140.7 kha | 470.9 kha | 46.6 kha |

## What CAPRI does

- Land-type totals are variables when land is not fixed (`p_landIsFixed = 0`): `LandBalNoSlak_` / `LandBalSlak_`
  balance the activities of each land type against `v_actLevl(RUNR, landType, "T")`, linked to the land market and a
  total land balance including forest, other land and artificial areas.
- Land market (`LandMarket_`, supply_model.gms:4830, trustee-land variant): a cost on each land type's area,
  sum p_pmpCnstLandTypes(r, LT) L_LT + 1/2 p_pmpQuadLandTypes(r, LT, LT') L_LT L_LT' (per ha), calibrated like crop PMP;
  CAPRI writes the terms to `pmppar_17XX.gdx` (`supply/pmp.gms`).
- Permanent grassland: `permGrasGreening_` in the CAP greening chain; under the Green Deal
  (`pol_input/greendeal/oth_pol.gms`) minimum grassland = (1 - permitedReduGras/100) x base grassland, permitedReduGras
  0 by default and 10 or 20 only in the othPol variants 10g, 20g, 20gs, 20gsf.
- Arable land can also come from forest and other land, so the floor can be met without touching grassland where other
  land exists.

## capri-mod (`RegionalSupplyModel._land_augment`)

- Land-type areas as variables in each regional model: ARAC, GRAS, FRUN, FORE, OLND; ARTIF fixed (left out).
- Cost 1/2 L' Q L with Q = 1000 x CAPRI's p_pmpQuadLandTypes (CAPRI's terms are per ha, the model's land in 1000 ha);
  the constants are not CAPRI's p_pmpCnstLandTypes but set so the base land use is optimal given the land rents:
  at the 2030 market year CAPRI's own rents at its calibration point (D_AREA of ARAC, FRUN and grassland,
  `land_rents_2030.csv`, tools/build/build_land_rents.py; CAPRI takes them as given in its calibration, cal_land_nests.gms,
  prep_cal.gms), else (2017 base) the shadow prices of the land rows recovered once from the region's ordinary QP
  solution (REGISTERED: no CAPRI EU rents for 2017 in hand). The NLP form's calibration fixes the land balances'
  multipliers at the same rents (docs/LAND_RENT_CALIBRATION_PLAN.md).
- Land rows: arable crops against ARAC, grassland crops against GRAS, permanent crops against FRUN, as
  activities - land = base crops - base land (the grassland row too since 21 October 2026: it kept the land data's
  headroom above the base use, IE04 173 kha, on which grass could grow at no land cost; KNOWN_ISSUES K60). Idled
  histosol area stays in its land type (crops + idled area = land; KNOWN_ISSUES K59). With `land_no_slack` (default True, CAPRI's LandBalNoSlak_) these are
  equalities on changes from the base use, because the model's land data carry idle land that CAPRI's data do not; land
  leaves farming only through the land market's costs. Arable fodder (MAIF, OFOD) sits on arable land.
- Total land conserved (the land types add up to the region's base total): land leaving farming goes to forest and
  other land at the land market's costs.
- Grassland land type >= (1 - `grassland_allowance`) x base (`CAPRIModel.grassland_allowance`, default 0, CAPRI's
  permitedReduGras default). The NLP form also writes CAPRI's permGrasGreening_ on the grassland activity
  (`docs/SUPPLY_MODEL_MAP.md`).
- CAPRI's land-use change transition model (`capri_mod/environmental/luc.py`) is solved after each regional solve on
  its land-type changes (REGISTERED: identical to solving it inside without a LULUCF price).

Data: `tools/build/build_land_market.py` -> `capri_data/2017/supply/land_market_2017.csv`: base areas of CAPRI's land types
(res_17*, LEVL) and p_pmpQuadLandTypes for six land types with cross-terms, regional where CAPRI has the region, else
national. 235 of the 248 model regions have an entry; the other 13 (AT13, BE10, DE30, DE50, DE60, ES63, ES64, HR05,
HR06, PL31, PL32, PL33, PL34) have no crop area in the model's base data (checked 20 October 2026). A region without
land-market data would be solved without it, with arable land scaled by a market-driven land-expansion factor
(`_next_land`), and without manure trade columns.

Split regions and national fallback: a CAPRI region that maps to no model region but whose agricultural area equals
the sum of unmapped model regions (within 0.5%) is their parent (Saxony DED00000 -> DED2, DED4, DED5; Budapest-Pest
HU100000 -> HU11, HU12; Trentino-Alto Adige IT310000 -> ITH1, ITH2; Polish and Finnish regions). Each part takes arable,
grassland and permanent land from the model's own base areas, forest, other and artificial land as the parent's x its
share, and the parent's matrix divided by that share (same relative responsiveness on a smaller area; REGISTERED).
Regions without a parent use their national matrix, scaled the same way. Three matrices are near singular (smallest
eigenvalue about 1e-16: ITF5, EL62, EL63); a ridge of 1e-9 is added to every matrix.

Checks made when the data were built: grassland equals the model's (median ratio 1.000); with observed land rents the
scaled matrices imply an arable land-supply elasticity of median 0.062 (10th percentile 0.010, 90th 0.334), within
CAPRI's priors (unscaled the median was 62); base reproduced with the land market on (4.9e-12 kha); under Farm-to-Fork
Trento met its fallow floor exactly (3.94 kha) and kept its arable crops.
