# Young-animal markets and livestock supply elasticities

Status (October 2026): **both on by default** (`CAPRIModel.use_young_animal_market`; livestock
elasticities in `capri_pmp.build_elasticity_table`).

## Young animals, as CAPRI

CAPRI's cattle activities are linked through young animals: cows produce calves (YCAM, YCAF), calf
activities produce young bulls and heifers (YBUL, YHEI), heifers produce replacement cows (YCOW); the
fattening, rearing and dairy activities use them as inputs (ICAM, ICAF, IBUL, IHEI, ICOW). In the supply
model they enter the balance of each region (`INPANI_`, `SUPBAL_`) and are bought or sold; their prices
come from the market model, where young animals clear at market-region level with net trade fixed
(`arm/market_model.gms`, `yaniMarket_`; `rmsYaniMarket_` per member state as an option).

capri-mod:

| | CAPRI | capri-mod |
|---|---|---|
| Goods | YCAM, YCAF, YBUL, YHEI, YCOW (and lambs, piglets) | calves (YCAM + YCAF), young cattle (YBUL + YHEI), cows (YCOW) |
| Coefficients | per activity level | per model head: CAPRI's regional flow / model head count (`tools/build_young_animals.py`) |
| Supply side | young animals in the supply balance, valued at their price | margins change by (price ratio − 1) × CAPRI base value × (output − input) per head |
| Market | EU (market region) price, net trade fixed | one EU price ratio per good; EU net balance held at the baseline run's level |
| Price update | market model with normalised-quadratic supply approximations | damped Newton step; supply response from each region's PMP matrix (dx = Q⁻¹ dc), renewed every outer iteration |

Coefficients per model head matter: the model's cattle head counts are census stocks and differ from
CAPRI's activity levels (Düsseldorf fattening bulls: 5.2 thousand model heads, 13.1 thousand CAPRI
activity units), so per-CAPRI-head coefficients gave base balances far from CAPRI's (EU young cattle
produced 17.4 m, used 5.5 m). Per model head, each region's base flows are CAPRI's own (EU base: calves
24.7 m produced, 24.9 m used; young cattle 17.9 / 20.2 m; cows 7.2 / 7.0 m).

REGISTERED: male and female calves and young cattle are aggregated, as are the model's calf
activities; Spain has no 2017 regional dump in the project (CAPRI 2030 levels used for its scaling,
young-animal values = median of the other countries); lambs and piglets are not linked.

## Livestock supply elasticities

Every livestock activity was calibrated to a hard-coded literature elasticity (dairy cows 0.15, bulls
0.18, calves 0.10, pigs 0.20, broilers 0.25), in all 248 regions. CAPRI's own calibrated supply
elasticities of the animal products are in the project (`sources/arm/capri_supply_elas_market_1717.csv`,
`elas_2_1717` `p_elasSupp`, level CAL, per member state): milk 0.47–0.58, beef 0.65–0.70, pork 0.57–0.72,
eggs 0.74–0.79, poultry meat 0.71–0.76, sheep and goat meat 0.82. Each animal activity now takes its
product's value for its member state (dairy cows: milk; suckler cows, bulls, heifers, calves: beef;
pigs: pork; hens: eggs; broilers: poultry meat; sheep and goats: sheep and goat meat). Response to a
10% price rise, before → after: bulls +1.7 → +4–7%, dairy cows +1.5–1.8 → +4–7%, pigs +6–8%.

REGISTERED: the product elasticity is used as each activity's own-price elasticity; CAPRI calibrates
its PMP terms so that the whole supply model reproduces the product elasticity.

## Curvature basis

Livestock margins use CAPRI's total output value per head (TOOU), which includes young animals; the PMP
curvature used market revenue (MREV). For suckler cows (MREV €68, TOOU €620 per head in Düsseldorf) that
made any change in their margin act nine times too strongly: with the calf price up 35%, suckler cows grew
+40% in low-nitrogen-price regions. The curvature now uses TOOU; a commodity price moves the market part
(MREV) only, young animals moving with their own prices; and each cattle activity's elasticity is the
value-weighted mean of its product's and its young animals' (CAPRI's calibrated 2020 values,
`tools/build_young_animal_elasticities.py`; the 2017 file has dummies of 1 for young animals).

## Results (full EU, 2030 Farm-to-Fork)

See README and docs/MODULE_COUPLING_REVIEW.md for the current table. With the literature elasticities
the young-animal markets made cattle fall less and the calf price nearly tripled (calf rearing barely
reacted to its cost); with CAPRI's elasticities the calf price rises 35% and the run converges in 10
iterations. After the curvature fix: beef price +12.7% (CAPRI +24%), beef production −7.6% (−14%), beef animals
−8.4% (−18%), calf price +56%. Regions where the nitrogen price stays below €1/kg grow herds by 3–5%;
where it exceeds €20/kg herds fall 19–36% and pigs 50%.
