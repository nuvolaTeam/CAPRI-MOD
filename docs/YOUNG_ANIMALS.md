# Young-animal markets and livestock supply elasticities

Status: revised 20 October 2026 against the code. Both are always on (the young-animal markets' switch was removed on 27 October 2026;
livestock elasticities in `capri_pmp.build_elasticity_table`). Earlier run results (October 2026) are left to
CHANGELOG.md; current results: README section 9 (Validation) and KNOWN_ISSUES K47, K48.

## Young animals, as CAPRI

CAPRI's livestock activities are linked through young animals: cows produce calves (YCAM, YCAF), calf activities
produce young bulls and heifers (YBUL, YHEI), heifers produce replacement cows (YCOW), sows produce piglets (YPIG),
sheep and goats for milk produce lambs (YLAM); the fattening, rearing and breeding activities use them as inputs
(ICAM, ICAF, IBUL, IHEI, ICOW, IPIG, ILAM). In the supply model they enter each region's balance (`INPANI_`) and are
bought or sold; their prices come from the market model, where young animals clear per market region with net trade
fixed (`arm/market_model.gms` l. 1579, `yaniMarket_`; `rmsYaniMarket_` per member state as an option).

| | CAPRI | capri-mod |
|---|---|---|
| Goods | YCAM, YCAF, YBUL, YHEI, YCOW, YPIG, YLAM | calves (YCAM + YCAF), young cattle (YBUL + YHEI), cows (YCOW), piglets (YPIG), lambs (YLAM) |
| Coefficients | per activity level | per model head: CAPRI's regional flow / the model's head count (`tools/build/build_young_animals.py` → `capri_data/2017/supply/young_animals_2017.json`) |
| Supply side | young animals in the supply balance, valued at their price | each activity's margin changes by (price ratio − 1) × CAPRI's base value per head × (output − input) per head (`RegionalSupplyModel._apply_young_animal_prices`) |
| Market | per market region (RM), net trade fixed | per EU market region (the EU, or each EU trade block with `eu_blocks`); the net balance of each good held at the baseline run's level |
| Price update | inside the market model, with normalised-quadratic supply approximations | `CAPRIModel._update_young_animal_prices`, once per outer iteration of a scenario: a Newton step on the price ratios, the supply response approximated from each region's PMP matrix (dx = Q⁻¹ dc), renewed every iteration |
| Price bounds | ±10 × (abs(level) + 10), widened where binding; negative prices allowed (`arm/set_start_val.gms`, `arm/widen_bounds.gms`) | numeric guard of ±50 × base (`YANI_RATIO_BOUNDS`); negative ratios allowed |

The Newton step is damped (`YANI_RELAXATION` 0.7 in `model_parameters.csv`) and limited to 30% of the current or the
base price, whichever is larger. The outer loop counts as converged only when every young-animal balance is within
0.5% of production (`YANI_TOL`). In a baseline run the prices stay at base and the balance is recorded as the
reference for the scenario.

Coefficients per model head matter: the model's cattle head counts are census stocks and differ from CAPRI's activity
levels (DE11 fattening bulls: 5.2 thousand model heads against 13.1 thousand CAPRI activity units), so per-CAPRI-head
coefficients gave base balances far from CAPRI's. Per model head each region's base flows are CAPRI's own.

REGISTERED: male and female calves and young cattle are aggregated, as are the model's calf activities; Spain has no
2017 regional dump in the project (its coefficients are scaled with CAPRI's 2030 activity levels, its young-animal
values the median of the other countries).

The price responses are large in kind: CAPRI's own run without voluntary coupled support moves the calf price twelve
times as much as the beef price (KNOWN_ISSUES K48); the cattle chain's equilibrium is sensitive to changes outside it
(K47). The bounds 0.2 and 5 × base used before 19 October 2026 bound the Green Deal run's calf and lamb prices and left
their markets open (K37).

## Livestock supply elasticities

Each animal activity's PMP calibration takes CAPRI's own calibrated supply elasticity of its product for its member
state (`capri_data/sources/arm/capri_supply_elas_market_1717.csv`, `elas_2_1717` p_elasSupp, level CAL): dairy cows
milk; suckler cows, bulls, heifers and calves beef; pigs pork; laying hens eggs; broilers poultry meat; fattening sheep
and goats sheep and goat meat; sheep and goats for milk raw milk (CAPRI's MILK market holds cow and sheep-goat milk).
Medians over the 34 regions of the file: milk 0.59, beef 0.72, pork 0.70, eggs 0.76, poultry meat 0.76, sheep and goat
meat 0.81. These replaced literature values (0.10-0.25) used in all 248 regions.

Curvature basis: livestock margins use CAPRI's total output value per head (TOOU), which includes young animals; the
PMP curvature used market revenue (MREV) before. For suckler cows (DE11: MREV 68, TOOU 620 EUR per head) that made any
change in their margin act about nine times too strongly. The curvature now uses TOOU; a commodity price moves the
market part (MREV) only, young animals moving with their own prices; and the elasticity of each cattle activity and
of sows is the value-weighted mean of its product's and its young animals' (CAPRI's calibrated values,
`sources/arm/capri_supply_elas_young_1720.csv`, `tools/build/build_young_animal_elasticities.py`; the 2017 file has dummies
of 1 for young animals).

REGISTERED: the product elasticity is used as each activity's own-price elasticity; CAPRI calibrates its PMP terms so
that the whole supply model reproduces the product elasticity.
