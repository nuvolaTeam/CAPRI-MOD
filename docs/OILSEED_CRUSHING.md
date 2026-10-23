# Oilseed crushing, oils and cakes

Status: revised 20 October 2026 against the code. Crushing, the oil and cake markets, cakes as feed and the biofuel
feedstock demand are all inside the market (built in four stages in October 2026, then moved onto CAPRI's processing
functions; the staging is summarised under "History"). There is no proxy price: oil and cake prices are formed in
their own markets, as in CAPRI (the earlier soybean-meal proxy, 0.89 × the soybean price, is gone).

## CAPRI's mechanism (`arm/market_model.gms`)

- Crushing margin per tonne of seed (`ProcMargO_`, l. 1118): oil and cake producer prices × yields − the seed's
  Arm1 price.
- Crushing quantity (`ProcNQ_`, l. 1140): normalised quadratic in the margins, Hessian `p_hessNQProc` with cross terms
  among the oilseeds, divided by the price of the non-agricultural good (INPE).
- Oil and cake output = crushed seed × yields (`ProcO_`, l. 1168).
- Oils and cakes are full market products: food, feed, processing, biofuel use, bilateral trade.

## The model (`MarketModule._crush_params`, `crush_quantities`, `_align_eu_crush_products`)

Market commodities: the seeds RAPE, SUNF, SOYA; the oils RAPO, SUNO, SOYO; the cakes RAPC, SUNC, SOYC (all traded
bilaterally; [ARMINGTON_MARKET.md](ARMINGTON_MARKET.md)). Palm oil (PLMO) and other vegetable oils (OTHO) are market
commodities too, without crushing in the model.

Parameters (`crushing_parameters.csv`, `tools/build/build_crushing_parameters.py`, from CAPRI's FAO_agg base period): per
(region, seed) the crush (the seed's industrial use), oil and cake yields (production / crush), the share of crush in
seed use, and p_ElasProc (EU: median of the member states; rapeseed 0.456, sunflower 0.869, soybeans 0.856; ROW: the
crush-weighted mean of its CAPRI regions; a pair without p_ElasProc in CAPRI has its crush fixed at base). 64 pairs, every
trade region with CAPRI crushing data, CAPRI's yields as they are. Until 23 October 2026: JSON, 20 non-EU regions, pairs
with yields outside a plausibility band left out, and those regions' oil and cake supply at a flat elasticity of 0.10.

- Base crush: EU = CAPRI's crush share of seed use × the market's EU base seed use after the bilateral closure (with
  `eu_blocks`, per block from CAPRI's member-state processing share); non-EU = CAPRI's cake production of the market
  year / cake yield. EU oil and cake base production = base crush × yields, so the base is reproduced.
- Response: where CAPRI's processing Hessian has the seed (`processing_nq_hessian.csv`,
  `tools/build/build_processing_nq.py`), crush = q0 + Σ_y H_sy Δmargin_y with H divided by INPE (1.277 in 2030, KNOWN_ISSUES
  K39); otherwise crush = q0 [1 + ε (margin − margin0) / gross value0] with ε = p_ElasProc. Crush is floored at 1% of
  base (CAPRI's `ProcFudge_` keeps processing positive).
- Oil and cake supply = crush × yields (`supply_response`); crush is part of seed use (`demand_response`).

Links to the rest of the model:

| Link | What passes |
|---|---|
| supply models → seed markets | rapeseed, sunflower and soybean output (`model._bridge_supply_to_market`) |
| seed, oil and cake prices → crushing | inside the market, at every evaluation |
| cakes → feed | EU: CAPRI's FPRO feed bulk per member state, following the supply models' feeding ([FEED_MARKETS.md](FEED_MARKETS.md)); non-EU: CAPRI's p_ElasFeed |
| cake prices → livestock costs | the FPRO bulk price index per member state goes to the supply models' feed prices |
| oils → biofuels | the biofuel part of oil use follows CAPRI's feedstock CES at the endogenous biofuel output ([BIOFUEL_MARKET.md](BIOFUEL_MARKET.md)) |
| oils → processing | the processing part of oil use follows CAPRI's ProcNQ_ with cross terms among the vegetable oils |
| seed prices → supply models | the price signal, as for every product |

Difference from CAPRI (not registered elsewhere): the model evaluates the crushing margin at the regions' Armington
(consumer) price ratios for seed, oil and cake alike (`crush_dom`); CAPRI's `ProcMargO_` takes the oil and cake at
their producer prices and the seed at its Arm1 price.

## Data: CAPRI's 2030 reference balance, EU27 (kt)

| | Production | Feed | Food | Industry | Biofuel | Imports | Exports | Unit value EUR/t |
|---|---|---|---|---|---|---|---|---|
| Rapeseed oil | 12,008 | 272 | 2,260 | 3,163 | 6,243 | 3,268 | 3,213 | 949 |
| Sunflower oil | 3,744 | 203 | 2,812 | 916 | 535 | 3,539 | 2,748 | 1,197 |
| Soybean oil | 2,574 | 280 | 1,134 | 356 | 549 | 988 | 1,190 | 683 |
| Rapeseed cake | 16,580 | 10,914 | | 113 | | 6,864 | 12,311 | 483 |
| Sunflower cake | 4,546 | 9,832 | | 36 | | 9,312 | 3,960 | 466 |
| Soybean cake | 11,185 | 39,542 | | 159 | | 43,727 | 15,124 | 468 |

FAO_agg base period (`crushing_parameters.csv`, `world_prices.csv`): EU crush rapeseed 21.0 Mt, sunflower 8.3 Mt,
soybeans 14.7 Mt; world prices (EUR/t) rapeseed oil 737, sunflower oil 665, soybean oil 700, rapeseed cake 213,
sunflower cake 204, soybean cake 354.

## History (October 2026)

1. Six oil and cake market commodities with CAPRI's base balances.
2. Crushing on the margin with p_ElasProc; oil and cake supply from crush.
3. Cakes as feed; the soybean-meal proxy removed.
4. Biofuel feedstock demand inside the market (CAPRI's CES at fixed biofuel output, as CAPRI runs without
   `BIOF_M`); since Sprint 9c the biofuel output is endogenous ([BIOFUEL_MARKET.md](BIOFUEL_MARKET.md)).

Later: CAPRI's processing Hessian (ProcNQ_) for crushing and oil processing, with the INPE correction of K39
(19 October 2026); the cake feed demand through CAPRI's feed bulks (Sprints 9d, 9h). The results of each stage are in
CHANGELOG.md and are not current.
