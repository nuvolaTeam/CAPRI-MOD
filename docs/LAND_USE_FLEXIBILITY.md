# Land-use flexibility (arable ↔ grassland ↔ other land) — design

Status: **on by default, as in CAPRI**; scale verified; base identical. Resolves the two regions that are infeasible under
Farm-to-Fork (Trento ITH2, Epirus EL54), which today end in an ill-defined
solver compromise and take about half of every supply pass.

## The conflict

CAPRI's landscape rule (`pol_input/greendeal/landscape.gms`), already used by
the model: fallow floor = (requested share ÷ 10%) × the member state's NET target
`p_setAsideTarget` × the region's total UAA + existing set-aside. It applies to
**total** UAA, while set-aside can only use **arable** land, which the model holds
fixed:

| Region | Arable | Grassland | Other agric. land | Landscape floor |
|---|---|---|---|---|
| Trento (ITH2) | 1.33 kha | 61.3 kha | 3.3 kha | 3.94 kha |
| Epirus (EL54) | 18.8 kha | 408.6 kha | 461.9 kha | 35.3 kha |
| Düsseldorf (DE11), reference | 306.9 kha | 140.7 kha | 470.9 kha | 46.6 kha |

## What CAPRI does

In CAPRI's supply model the land-type totals are **variables** when land is not
fixed (`p_landIsFixed = 0`): `LandBalSlak_` / `LandBalNoSlak_` balance the
activities of each land type (arable `ARAB`, usable grassland `UGAR`, …) against
`v_actLevl(RUNR, landType, "T")`, linked to a land market (`LandMarket_`) and a
total land balance including forest, other land and artificial areas. The
permanent-grassland greening rule (`permGrasGreening_`) bounds the loss of
grassland. So Farm-to-Fork's fallow floor is met by converting grassland or
other land into arable land.

The model instead scales arable land proportionally by a small market-driven
factor (`_land_expansion`); it cannot move land from grassland or other land.

## Plan

1. **Conversion variables** per region: grassland → arable and other
   agricultural land → arable (kha), raising the arable limit and lowering the
   grassland (or other-land) availability accordingly.
2. **Limits**: CAPRI's permanent-grassland rule (values of
   `p_DPGreeningLimits(…, "permGras")` to be obtained); other land bounded by
   what the region has.
3. **Costs**: quadratic, calibrated so conversion is zero at base (as for every
   PMP activity), with CAPRI's land-transformation behaviour where available.
4. **Validation**: base identical; Trento and Epirus feasible under
   Farm-to-Fork; their slow solver path gone; land-use change against CAPRI's
   reported land use.



## CAPRI's mechanism, located

- **Land market** (`supply_model.gms`, `LandMarket_`): a PMP cost on each land
  type's area, `Σ p_pmpCnst(r, LT)·L_LT + ½·p_pmpQuadLandTypes(r, LT, LT)/UAAR·L_LT²`,
  calibrated like crop PMP. CAPRI writes `p_pmpCnst`, `p_pmpQuadLandTypes` and
  `p_pmpLandSupplyTail` into `pmppar_17XX.gdx` (`supply/pmp.gms`).
- **Permanent-grassland rule under the Green Deal**
  (`pol_input/greendeal/oth_pol.gms`): minimum grassland = (1 − permitedReduGras/100)
  × base grassland. permitedReduGras **defaults to 0** and is 10 or 20 only in
  the scenario variants `othPol` = 10g, 20g, 20gs, 20gsf. Which variant
  JRC121368 used is not visible in the code.
- **Arable land also comes from other land**: CAPRI's total land balance includes
  forest and other land, so the floor can be met without touching grassland
  where other land exists (Epirus 461.9 kha; Trento only 3.3 kha).

## Data requested

From `results\capreg\pmppar_17XX.gdx`: `p_pmpCnst` (land-type entries),
`p_pmpQuadLandTypes`, `p_pmpLandSupplyTail`; and the `othPol` setting of the
Farm-to-Fork run being matched.

## Data received and built

`pmppar_17XX.gdx`: `p_pmpQuadLandTypes` for six land types (ARAC, GRAS, FRUN,
FORE, OLND, ARTIF), full matrices with cross-terms, regional for nearly all
regions. `p_pmpLandSupplyTail` does not exist, so the runs used CAPRI's
trustee-land variant, whose constants are `p_pmpCnstLandTypes` - not needed, the
model recalibrates constants so the base land use is optimal. Built for 202
regions: grassland equals the model's exactly (median ratio 1.000); Epirus has
355 kha of forest and 57 kha of other land beside 19 kha of arable; three
matrices are singular (eigenvalue ~1e-16: ITF5, EL62, EL63 - a tiny ridge);
Trento is missing (CAPRI's IT310000 is Trentino-Alto Adige, split in the model
into ITH1/ITH2).

## Implementation (next)

Land-type areas as variables in each regional QP, behind a switch first:
arable crops ≤ L_ARAC, grassland crops ≤ L_GRAS, permanent crops ≤ L_FRUN; total
land Σ L = Σ L₀; L_GRAS ≥ (1 − allowance) × base (CAPRI default 0%); artificial
land fixed; cost ½ Lᵀ Q L with constants calibrated so L₀ is optimal; replaces
the proportional land expansion where the data exist.

## Split regions and national fallback

A CAPRI regional code that maps to no model region but whose agricultural area
equals the sum of unmapped model regions (within 0.5%) is their parent:
Saxony (`DED00000` → DED2, DED4, DED5), Budapest–Pest (`HU100000` → HU11, HU12),
Trentino-Alto Adige (`IT310000` → ITH1, ITH2) and two Polish regions. Each part
takes arable, grassland and permanent land from the model's own base areas,
forest, other and artificial land as the parent's × its share, and the parent's
matrix divided by that share (same relative responsiveness on a smaller area —
registered). 21 regions without a parent use their national matrix, scaled the
same way. 236 regions in all.

Checks: base identical with the switch on (4.9e-12 kha); under Farm-to-Fork,
Trento meets its fallow floor exactly (3.94 kha) and keeps its arable crops, with
no slow fallback (seven test regions: 55 s → 6 s).

## Scale check (failed)

From CAPRI's matrix and the model's base arable shadow price, the implied
arable land supply elasticity is median 1.33 (10th 0.19, 90th 5.6) — several
times CAPRI-type land supply — and the base shadow price is ~1/50 of observed
land rents. Either the matrices and the model's objective are on different
scales, or the arable row's shadow price is not the land rent (land costs may
sit inside the calibrated PMP terms). Next: the units of CAPRI's trustee-land
`LandMarket_` terms and of the model's objective, and how land costs enter
the model's margins.

## Scale resolved; on by default

CAPRI's land-market terms are per hectare; the model's land variables are in
1000 ha, hence a factor of 1,000. With observed rents the matrix then implies an
arable land-supply elasticity of median 0.062 (10th 0.010, 90th 0.334), within
CAPRI's priors (unscaled: 62). Full 2030 Farm-to-Fork in 197 s (was 10–12 min),
results within about one point of land fixed. On by default, as CAPRI
(`p_landIsFixedinScenario = 0`); `grassland_allowance` defaults to CAPRI's 0%.
