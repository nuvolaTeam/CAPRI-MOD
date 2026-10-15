# Oilseed crushing — design

Status: **Stages 1–4 done** — crushing live in all regions; cakes are feed and price livestock protein feed (soybean-meal proxy removed); biofuel feedstock demand (oils, cereals, sugar, wine) is inside the market (Stage 4, October 2026) and the post-solve biofuel module is retired.
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
| Cake prices → livestock costs | outer loop, via the price signal | protein-feed cost per head follows the cake price index — **removes the soybean-meal proxy**; since Sprint 9d CAPRI's FPRO bulk price per member state (docs/BIOFUEL_MARKET.md) |
| Oil and feedstock markets ↔ biofuels | inside the market (Stage 4) | EU biofuel feedstock use per member state from CAPRI's CES at fixed biofuel output (`biofFeedCost_`, `biofFeedCostAgg_`, `Biof_`, `prodBiof_`) |
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

**Stage 4 — oils and biofuels (done, October 2026).** CAPRI's biofuel block in the market model
(`arm/market_model.gms`), as CAPRI runs it in a scenario without endogenous biofuel markets
(`arm/prep_market.gms`: `p_endoBioMarket = 0` unless `BIOF_M=ON`; `arm/fix_biofuel_market_vars.gms`
then fixes biofuel output and biofuel prices, while the feedstock mix stays free):

- `biofFeedCost_`: net cost per t of feedstock = feedstock price − by-product yield × by-product price
  (DDGS for cereals at CAPRI's 2030 producer price; glycerine for oils at CAPRI's fixed 600 €/t,
  `arm/store_prices.gms`);
- `biofFeedCostAgg_`: CES aggregate per biofuel, substitution elasticity 4 (`arm/market1.gms`
  `p_rhoBioFuel`), share parameters as `biofuel/def_biofuel_params.gms` calibrates them;
- `Biof_`: feedstock use = share × output × (aggregate cost / own cost)^4, for all but the numeraire
  (the largest feedstock); `prodBiof_`: output = Σ feedstock × PRCB fixes the numeraire.

Per member state, from CAPRI's 2030 Green Deal reference market results
(`tools/build_biofuel_market.py`, formerly `build_biofuel_feedstock.py` → `market/biofuel_feedstock.csv`, `biofuel_use_share.csv`). The
builder reproduces CAPRI's own `BiofFeedCost` exactly in every member state. EU feedstock use (kt):
rapeseed oil 6,243, palm oil 2,166, sunflower oil 535, soybean oil 549; wheat 4,058, maize 3,107,
barley 2,655, rye/oats/other cereals 1,723, sugar 2,275, wine 1,254. In the market the biofuel part of
EU use (52% of rapeseed oil, 23% of soybean oil, 12% of sugar, 4–7% of cereals) follows the CES at
fixed output; the rest keeps its food response. Palm oil and other oils have no model market (price at
the 2030 reference); DDGS is not a model market either (CAPRI: endogenous feed price) — REGISTERED.
`run(biofuel_output_scale={"BIOD": x})` sets a mandate scenario. Farm-to-Fork 2030: gap 4.64 → 4.62
(small, as expected: biofuel output is fixed and feedstock prices move ≤ 20%).

**Since Sprint 9c** the biofuel output is endogenous as well (CAPRI's `BIOF_M`, star 3.0's default): biofuel
supply on the processing margin, use against fossil fuel and bilateral trade, in every CAPRI market region; the
feedstock CES above then runs at that output, in non-EU regions too (docs/BIOFUEL_MARKET.md).

**Data needed from the project lead:** CAPRI's calibrated market elasticities,
`%results_in%\arm\elas<BAS><SIM><reg_agg>…gdx` (read by `arm/trim_elas.gms`):
`p_elasProc` (crushing response — Stage 2), `p_ElasFeed` (feed demand — makes the
feed mix endogenous, retiring the fixed feed shares), `p_elasDem` (food demand).
Without `p_elasProc`, Stage 2 would need a registered simplification.

**Validation:** EU balances of oils and cakes against the table; Farm-to-Fork
oilseed, cake and livestock results against JRC121368.
