# Departures from CAPRI's settings

The project lead's rule (23 October 2026): **follow CAPRI, except where CAPRI's code is in error, and describe every
difference.** This file lists the settings whose default in `capri_mod/settings/defaults.toml` is not CAPRI star 3.0's.
It covers settings only. Method choices registered elsewhere (KNOWN_ISSUES, MITIGATION_IN_SUPPLY, NLP_PORT_DESIGN)
are not repeated here.

Two kinds of entry:

- **CAPRI-ERROR-FIX:** CAPRI's code is kept apart on purpose, because its effect contradicts CAPRI's own data or its other
  equations. The setting can reproduce CAPRI as coded.
- **DEPARTURE (to be removed):** the default differs from CAPRI's for a practical reason recorded at the time. The
  project lead decided on 23 October 2026 that each one goes to CAPRI's setting. They change one at a time, with a
  full Farm-to-Fork run after each.

## CAPRI-ERROR-FIX

### `environment.ad_dairy_ch4 = "fix"` (CAPRI as coded: `"capri"`)

**What CAPRI's code does.** Anaerobic digestion (AD_AnCh) on dairy cows' manure has no CH4 effect. The dairy macro
`MC_GHG_Miti_DCow` needs the factor `p_ghgMiti(MS,DCOL,"NOC","CH4MAN_3k","QEmitt")`. `ad_data_and_cali.gms` l. 588
sets every GainsTech's CH4MAN_3k entry to zero, NOC included.

**Evidence.**
- DE110000 DCOL CH4MAN per head: 54.709 at the ini run (share 0.054) and 53.922 at the max run (0.739). The
  non-dairy logic predicts ×0.575.
- CAPRI's own report (`reports/miti_report.gms` l. 1084-1100) still shows a dairy CH4 reduction, from a closed
  formula.

**What capri-mod does.** It applies CAPRI's CH4 factor to dairy cows as it does to the other animals. This was the
project lead's decision of 20 October 2026; details are in docs/AD_SPEC.md.

### `environment.ammapp_sign = "consistent"` (CAPRI as coded: `"capri"`)

**What CAPRI's code does.** It adds the low-emission application options' leaching effect in LEACHN_
(`+ v_ammoAppLeaAgg`, supply_model.gms l. 3413). Yet it subtracts the same options' runoff effect in RUNSURFN_, and
the fertiliser options' leaching effects in LEACHN_.

**Why that looks wrong.** The literature table gives reductions, with positive meaning less loss
(`prep_data_LitRev.gms` p_reducGains; LNA_low liquid: NH3 0.51, RunSurf −0.24, Leach −0.24). These are copied
unchanged to `no3mlea` (ammo_tech.gms l. 2293). With the "+", low-emission application lowers the leaching share
where CAPRI's data say it raises it.

**What capri-mod does.** It subtracts the effect, consistently with RUNSURFN_. This was the project lead's decision
of 20 October 2026; details are in capri_mod/supply/n_leaching.py.

**Scope of the effect.** The base is calibrated to CAPRI's realised leaching share either way, so the sign acts only
through changes in the options' adoption.

### `captrd.short_series_grid_as_coded = false` (CAPRI as coded: `true`) — CAPTRD-MOD, Step 1

**What CAPRI's code does.** CAPTRD's trend fit `x = a + b·t^c` searches 30 values of c. For a series with 3 or 4
observations it fixes c = 1, and with 1 or 2 it sets b = 0. Only the first grid point is computed, and the code
states that "only C1 entry is relevant" (`captrd/estimate_trends.gms` l. 158). The other 29 points are set to zero
(l. 160), and the minimum of the weighted error sum of squares is then taken over all 30 points (l. 166). A GAMS
`SMIN` counts the zeroed entries, so the minimum is 0 and the second grid point is chosen, with a = b = c = 0. This
happens unless the first point fits exactly.

**Evidence.** CAPRI's own CAPTRD results, `results_1770.gdx` (base 2017, uploaded 23 October 2026), have 93 series
with 2–4 observations.
- 92 of them have Step1 = 0 in every year.
- With 3–4 observations, wR2 = 0, so the support is the base value and the trend is ignored.
- With 2 observations, wR2 = 1 (wVar is not defined), so the support is 0.001 × base. Examples:
  - CS FEDM OCER: support 0.077 against a base of 77.4, and a 2030 result of 4.4;
  - AL LOSF ROOF: support 0.0047 against a base of 4.72.
- The one exception (BA NTRD DDGS) was not traced.

The same port reproduces CAPRI's Step 1 for 99.78% of the 96,478 comparable series, so this is the code as it runs,
not a porting artefact (test `capri_mod/pipeline/tests/test_captrd_step1.py::test_parity_with_captrd_step1`).

**What capri-mod does.** It takes the minimum over the first grid point only, as CAPRI's comment intends:
- 1–2 observations: a is the weighted mean and b = 0;
- 3–4 observations: a linear weighted fit.

This is the default under the rule of 23 October 2026 for corrections of CAPRI code errors, pending the project
lead's confirmation. `true` reproduces CAPRI for the parity runs.

**Scope.** 93 of about 100,000 estimated series, mostly minor positions (DDGS, losses, a few NUTS2 crops). The fix
changes their supports directly; other series can change only through the consistency equations of CAPTRD's Step 2.

## Switched to CAPRI's setting

### `supply.absent_activities_fixed = true` (23 October 2026)

An activity without a level at the calibration point has no variable in CAPRI. Since 23 October 2026 the bounds hold
it at zero, and the greening rules leave it out.

The departure had been kept because the NLP failed in Greek and Bulgarian regions. Once the literature elasticities
were removed it became urgent: zero-level activities entered freely, and the Farm-to-Fork run cycled (KNOWN_ISSUES
K69). Two inconsistencies caused the failures, and both are fixed:
- the crop-diversification index took the logarithm of fixed columns;
- the permanent-grassland rule applied to a grassland of 3.5e-11 kha.

Reference run r110 has CAPRI's setting as the default.

## DEPARTURE (to be removed)

| Setting | CAPRI star 3.0 | Default now | Why it differs (recorded at the time) | What switching needs |
|---|---|---|---|---|
| `market.eu_blocks` | two EU trade blocks, EU_WEST and EU_EAST (aggregation/defaultA.agg) | false (one EU27 block) | built 18 October 2026 as an option; Farm-to-Fork deviation 4.22 → 4.65 when tried | a run; the market supply Hessian (below) is not built for the blocks yet |
| `market.market_supply_nq` | the market's supply functions calibrated to the supply models (supply/calibrate_supply.gms, arm/simu_calibration_to_supply.gms) | false (the market's own-price anticipation) | tested 18 October 2026: 13 iterations against 12, results within tolerance, about 9 min once to build the Hessian | the Hessian per trade block, for use with `eu_blocks` |
| `supply.fodder_at_shadow_price` | home-grown fodder valued in the rations at its fodder-balance dual | false (base value) | the first Farm-to-Fork run with it did not converge (ration ↔ fodder dual feedback) | retest in the NLP form; damping if needed |
| `supply.use_cattle_member_splits` | replacement heifers (HEIR) and the four calf activities with their own levels; young animals cleared per sex (INPANI_) | false (the model's animals with CAPRI's intensity pairs; pooled young-animal markets) | K65: with them on, the Farm-to-Fork run does not converge (male calves' price above 6 x base, female below zero, r96); no CAPRI per-sex Farm-to-Fork result exists to check against | find why the per-sex prices diverge (calf activities at their zero bounds) |
