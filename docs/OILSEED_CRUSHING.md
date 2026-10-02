# Oilseed crushing — design

Status: **Stages 1–3 done** — crushing live in all regions; cakes are feed and price livestock protein feed (soybean-meal proxy removed). Stage 4 (biofuels) open.
Replaces the soybean-meal **proxy price** (0.89 × soybean price), which breaks
the project rule: no proxy prices unless CAPRI uses them. CAPRI does not: it
forms oil and cake prices in their own markets.

## CAPRI's mechanism (`arm/market_model.gms`)

- **Crushing margin** per tonne of seed (`ProcMargO_`):
  `margin = cake price × cake yield + oil price × oil yield − seed price`.
- **Crushing quantity** responds to the margin through a calibrated
  normalised-quadratic profit function (`ProcNQ_`, Hessian `p_hessNQProc`).
- **Oil and cake output** = crushed seed × fixed yields (`ProcO_`, Leontief).
- Oils and cakes are **full market commodities**: human and feed demand,
  industrial and biofuel use, trade.

## Coupling — every link this module creates

The module sits between five existing parts of the model. Each link is
two-way and inside the outer loop; none is a fixed coefficient or a post-solve
step.

| Link | Direction | What passes |
|---|---|---|
| Farm supply → seed markets | existing bridge | rapeseed, sunflower and soybean output |
| Seed markets → crushing | inside the market | seed price enters the crushing margin; crush is a component of seed demand |
| Crushing → oil and cake markets | inside the market | oil and cake supply = crush × yields (rapeseed 0.418 / 0.541, sunflower 0.420 / 0.528, soybean 0.186 / 0.788) |
| Oil and cake markets → crushing | inside the market | oil and cake prices enter the margin, so crush responds to all three prices (CAPRI's `p_ElasProc`) |
| Herds → cake demand | outer loop | protein-rich feed per head (`FPRO`, CAPRI totals ÷ herds) × herds sets cake feed demand, as cereals' feed demand already does |
| Cake prices → livestock costs | outer loop, via the price signal | protein-feed cost per head follows the cake price index — **removes the soybean-meal proxy** |
| Oil markets ↔ biofuels | Stage 4 | biodiesel demand for oils inside the market (CAPRI `p_biofuelData`) |
| Seed prices → farm supply | existing price signal | unchanged path; now seed prices reflect oil and cake values |

## Base data (CAPRI FAO_agg, base period)

From `FAO_agg_17_defaulta` `p_dataMarket`, year `BAS`: balances for the six
products and three seeds in all 21 trade regions (EU = sum of member states;
crush = the seed's industrial use, confirmed in CAPRI's raw annual data). EU
crush: rapeseed 21.0 Mt, sunflower 8.3 Mt, soybean 14.7 Mt. World prices
(€/t): rapeseed oil 737, sunflower oil 665, soybean oil 699, rapeseed cake 213,
sunflower cake 204, soybean cake 354.

## Data (CAPRI 2030 reference balance, EU-27, kt)

| | Production | Feed | Food | Industry | Biofuel | Imports | Exports | Unit value €/t |
|---|---|---|---|---|---|---|---|---|
| Rapeseed oil | 12,008 | 272 | 2,260 | 3,163 | 6,243 | 3,268 | 3,213 | 949 |
| Sunflower oil | 3,744 | 203 | 2,812 | 916 | 535 | 3,539 | 2,748 | 1,197 |
| Soybean oil | 2,574 | 280 | 1,134 | 356 | 549 | 988 | 1,190 | 683 |
| Rapeseed cake | 16,580 | 10,914 | | 113 | | 6,864 | 12,311 | 483 |
| Sunflower cake | 4,546 | 9,832 | | 36 | | 9,312 | 3,960 | 466 |
| Soybean cake | 11,185 | 39,542 | | 159 | | 43,727 | 15,124 | 468 |

Oil and cake yields per tonne crushed follow from production ÷ crush
(`PrcY` in CAPRI's data).

## Model change, in stages

**Stage 1 — six new market commodities** (`RAPO`, `SUNO`, `SOYO`, `RAPC`,
`SUNC`, `SOYC`) with base balances from the table above and world prices; base
year must be unchanged for the existing 33 commodities.

**Stage 2 — crushing.** Crush per seed responds to the crushing margin;
oil and cake supply = crush × yields; seed demand includes crush. The crushing
response comes from CAPRI's `p_hessNQProc` if it can be found in the data,
otherwise it is a registered simplification.

**Stage 3 — cakes as feed.** Cake feed demand follows herds' protein-rich feed
(`FPRO` per head, CAPRI 2017 totals ÷ herds — already in
`livestock_feed_coef.csv`), at CAPRI's feed shares per cake; livestock
protein-feed cost follows the cake price index weighted by CAPRI's cake feed
use (soybean 39.5, rapeseed 10.9, sunflower 9.8 Mt). **The soybean-meal proxy is
then removed.**

**Stage 4 — oils and biofuels.** Biodiesel demand for oils inside the market,
retiring the post-solve biofuel module (CAPRI models biofuel demand in the
market).

**Data needed from the project lead:** CAPRI's calibrated market elasticities,
`%results_in%\arm\elas<BAS><SIM><reg_agg>…gdx` (read by `arm/trim_elas.gms`):
`p_elasProc` (crushing response — Stage 2), `p_ElasFeed` (feed demand — makes the
feed mix endogenous, retiring the fixed feed shares), `p_elasDem` (food demand).
Without `p_elasProc`, Stage 2 would need a registered simplification.

**Validation:** EU balances of oils and cakes against the table; Farm-to-Fork
oilseed, cake and livestock results against JRC121368.
