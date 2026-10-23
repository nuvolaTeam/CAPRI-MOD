# Land rents in the NLP form's calibration, as CAPRI (plan, 21 October 2026)

Status: implemented 21 October 2026 (agreed with the project lead as the follow-up to KNOWN_ISSUES K58); see 'Done' at
the end.

## Why

The NLP form calibrates the regional models so that the base is a first-order point. It fits the multipliers of the
active rows and bounds by least squares, and puts what remains in the activities' linear terms
(`CapriRegionalNLP.calibrate`).

Where the fit cannot determine a multiplier, the choice is arbitrary. For example, `grassland_lo` ties grass area to
the grassland land type, while the land type sits at its own lower bound. Until K58 the fit then returned
multipliers of 6e13. Since K58, a ridge term picks the least-norm multipliers. That makes the fit determinate, but
the land multiplier it picks is a mathematical choice, not an economic one.

## What CAPRI does (star 3.0)

CAPRI does not fit land duals; it sets them from data.

- `supply/cal_land_nests.gms` sets a land rent for every land type, `DATA(r, landType, "d_area", "Y")`:
  - **arable land types:** from data where available, else `p_landRentIntercept + p_landRentCoefToou x TOOU +
    p_landRentCoefPrme x PRME`, at least 1.25 x PRME;
  - **grassland:** residually, so that the land types add up to UAAR's rent (at least min(1, 0.2 x TOOU));
  - **ARAB's rent:** the area-weighted rent of ARAC and FRUN;
  - **non-agricultural types:** ARTIF and FORE relative to the agricultural rents.
- `supply/prep_cal.gms` l. 125-156 subtracts the "assumed land rent for arable and grass land" (the rent of each
  activity's land type), the milk quota rent and the set-aside costs from the activities' linear terms. The matching
  restrictions are removed for the calibration.
- `supply/pmp_terms/define_const_pmp_param.gms` l. 20-60 adds those rents back after the PMP terms are set.
- The 2008 documentation (sect. 4.2.3) gives the reason. Duals from a model that is not at its calibration point are
  unreliable, so the opportunity costs of land and the milk quota are defined exogenously.

## Plan

1. **Data.** Extract CAPRI's land rents, `d_area` by region and land type (ARAC, FRUN, GRAS types, UAAR, ARAB, ARTIF,
   FORE), from CAPRI's 2030 reference results (the res_2_1730 files already used for the 2030 baseline).
   - Write them to `capri_data/2017/supply/land_rents_2030.csv` with a builder, `tools/build/build_land_rents.py`.
   - Register the file in MANIFEST, INPUT_MANIFEST, INPUT_SCHEMA and DATA_SOURCING_REGISTRY.
   - If `d_area` is missing for some regions, apply CAPRI's own rent function from cal_land_nests.gms, with its
     parameters read from the GAMS source. Proxies such as Eurostat `apri_lrnt` stay for validation only.
2. **Calibration.** In `CapriRegionalNLP.calibrate`, fix the multipliers of the land rows at the region's land rents
   before the fit, in model units: the land-type balance rows, `grassland_lo`, the land-market rows, and the arable,
   permanent and grassland totals. Fit only the remaining multipliers. The ridge term stays for any other degenerate
   pair.
3. **Checks.**
   - The base reproduces exactly (drift below `BASE_CAL_TOL`).
   - IE04's carbon-tax response equals K58's (315 kha suckler cows), or the difference is explained.
   - The land multipliers at the baseline solution are compared with CAPRI's rents region by region.
   - Farm-to-Fork and Green Deal 2030 are rerun, and every indicator change is explained against r67 and r68.
4. **Documentation.** Update KNOWN_ISSUES (K58 superseded, or narrowed to the remaining degenerate pairs), CHANGELOG,
   NLP_PORT_DESIGN (Calibration section) and LAND_USE_FLEXIBILITY.

## Related

- The PMP matrix itself (decision 5a.5) is a separate question. Its first step is the decomposition diagnostic CAPRI
  runs (2008 documentation, sect. 7.3): re-solve at the final prices with the PMP cross terms between crop groups
  removed and the linear terms recalibrated. Its second step is CAPRI's 2030 `p_pmpQuad*` terms, if they can be
  exported from the project lead's installation.

## Done (21 October 2026)

- `tools/build/build_land_rents.py` -> `capri_data/2017/supply/land_rents_2030.csv`: D_AREA of ARAC, FRUN and of the grassland
  activity GRAS (sign turned) at CAPRI's 2030 reference, by CAPRI region group (area-weighted), else the member state.
  CAPRI's calibration rents are positive (cal_land_nests.gms: arable at least 1.25 x premiums, grassland at least
  min(1, 0.2 x revenue)); where the reported D_AREA is not positive (grassland in 10 regions, all of PT20's land types,
  arable -10,064 EUR/ha) it is not such a rent, and the land type keeps the model's own base dual (REGISTERED). A first
  full Green Deal 2030 run that took the negative values as they were did not converge (Portugal's milk price swung
  0.01-0.03 for 19 iterations).
- The land market's constants are set at these rents (`_land_augment`), and `CapriRegionalNLP.calibrate` fixes the
  land balances' multipliers at them (the upper row takes a positive rent, its mirrored lower row a negative one) and
  fits the rest; the ridge (K58) stays for other degenerate pairs. Only at the 2030 market year; the 2017 base keeps the
  rents recovered from its own base solution (no CAPRI EU rents for 2017 in hand).
- Found on the way and fixed: the grassland row was not an equality (K60), and idled histosol area was held at zero
  wherever a land row was tight (K59).
- Checks: base drift 0.0002-0.0008 (tolerance 0.002) on IE04, DE11, FRH0, NL13 and NO01; calibration residuals below
  1e-9; full-run results in CHANGELOG.
