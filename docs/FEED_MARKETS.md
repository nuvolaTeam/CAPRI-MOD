# Feed bulks and residual feed markets

Status: revised 21 October 2026 against the code (Norway's bulks: K56; built in Sprints 9d and 9h, October 2026). The Farm-to-Fork effect
reported at the time is in CHANGELOG.md ("Sprint 9h") and is not current; current results: README section 9 (Validation).

## CAPRI's structure (`arm/market_model.gms`, `global/fromimpact/sets.gms`)

The supply models buy feed as bulks; the market splits each member state's bulk into market products and prices it:

| Bulk | Products (FEED_TO_O) | p_rhoFeed, member states (`arm/market1.gms` l. 78-95) |
|---|---|---|
| FCER cereals | WHEA, DWHE, RYEM, BARL, OATS, MAIZ, OCER, PARI, RICE | 6 |
| FPRO protein-rich | PULS, oils (RAPO, SUNO, SOYO, OLIO, OTHO), cakes (RAPC, SUNC, SOYC, OLIC, OTHC), DDGS, FPRI, fish products | 6 |
| FENE energy-rich | MOLA, STAR, FENI | 5 |
| FOTH other | POTA, whole oilseeds (RAPE, SUNF, SOYA), OLIV, OOIL, TEXT, TOMA, OVEG, APPL, OFRU, CITR, TAGR, TABO, TWIN, SUGA, EGGS, PORK, BEEF | 0.5 |
| FMIL milk products | SMIP, WMIO, CASE, WHEP, BUTT, CREM, COCM, CHES, FRMI | 0.5 |

- `feedBlkPrice_` (l. 951): bulk price = CES index of the products' Arm1 prices → the supply models' feed prices.
- `feedShareEqu_` (l. 999): product feed use = bulk use × (bulk price / product price)^rho, calibrated to the
  reference.
- The residual feeds FENI (sugar-beet by-products, manioc, roots) and FPRI (milling by-products) are traded products
  used only as feed. Where there are supply models their output is a fixed share of the parents' processing
  (`MaprFeed_`, l. 1442): FPRI from the human consumption and processing of the cereals, FENI from sugar (human
  consumption, processing and biofuel processing). Elsewhere a supply function.

## The model

- Bulks per member state (`tools/build/build_feed_bulks.py` → `feed_bulks_eu.csv`: CAPRI's 2030 member-state feed use and
  the EU27yr19 Arm1 prices from `markmarket_greendeal_1730et_base_1717`, rho from `arm/market1.gms`). The table holds
  the products with CAPRI 2030 feed use in a member state; every one of them is a model market commodity (FCER: 7,
  FPRO: 13 including DDGS, FPRI, other vegetable oils and the fish products, FENE: FENI, FOTH: 11, FMIL: 8). Products in
  CAPRI's lists without a model market (OLIC, OTHC, MOLA, STAR) would stay at their reference price; none appears in
  the shipped table.
- Bulk prices to the supply models: `MarketModule.feed_bulk_price_ratio` per member state and bulk at the EU price
  signal (per trade block with `eu_blocks`), passed by `CAPRIModel.feed_bulk_price_ratios` as the supply models'
  `feed_bulk_ratio`.
- Bulk use from the supply models: `CAPRIModel._set_feed_demand` sums each member state's feed per bulk from the
  regional solutions (feeding inside the supply models, `feed_t`) against the base ration × base herds, and passes
  the ratio (`_feed_bulk_index`) to the market; the FMIL index likewise (`_fmil_index`).
- EU feed use of each product (`MarketModule.eu_feed_use`): q_i = q_i0 × (bulk / bulk0) × (P_B / p_i)^rho at the EU
  Arm1 price ratios. The bulk responds within the market solve as CAPRI's `feedBlk_` (l. 972-995; audit M4, since 29
  October 2026, `market.feed_bulk_in_market`): bulk = the supply models' bulk × exp(Σ_y e_y log(r_y / r_seen_y)), r
  the region's market price ratios and r_seen those the supply models saw (CAPRI's constant re-anchored to the supply
  models every iteration), e_y the supply models' bulk response measured with the market supply Hessian (its
  `FEEDBLK:<bulk>` rows per country, CAPRI's `p_feedBlkElas` from `calibrate_supply.gms` l. 521-560) over the bulk at
  base; in the products' prices, the bulk prices being functions of them (`feedBlkPrice_`); the young-animal and raw
  milk columns left out. The feed part of the EU's use of a product is CAPRI's 2030 feed share of use
  (`feed_bulks_eu_share.csv`, including processing in the use, so the oilseeds fed whole get their feed share of total
  use, crushing included); it is applied as a correction of the row, so crushing demand already in the row is kept.
  The dairy products' feed use comes from the FMIL bulks ([DAIRY_PROCESSING.md](DAIRY_PROCESSING.md)).
- Norway (its own market region NOR since 21 October 2026, KNOWN_ISSUES K56; CAPRI's RMSSUP, so `feedBlkPrice_` and
  `feedShareEqu_` hold for it, `FeedBal_` does not): its bulks (`feed_bulks_no.csv`: CAPRI's 2030 FEED and ARM1P of
  NO000000, and its use HCOM + FEDM + INDM + BIOF + LOSM + PRCM per product) give its supply models' bulk price
  indices at Norway's prices and its feed use per product at Norway's Arm1 price ratios (`MarketModule.sup_feed_use`),
  following its herds (`_feed_bulk_index` of NO000000, its own FMIL index `_fmil_index_sup`), on CAPRI's feed share of
  Norway's use; none of it is in the EU's feed demand.
- FENI and FPRI markets (`tools/build/build_bilateral_market.py`, `tools/build/build_feed_byproducts.py`): CAPRI's bilateral flows,
  regional market prices and Armington elasticities (FENI 4 / 8 from `special_ch/market1_ch.gms`, FPRI 8 / 10, CAPRI's
  default); world prices FENI 312.77 EUR/t (FAO_agg World PMRK, base period), FPRI 252.74 EUR/t (FAO_agg has none:
  CAPRI's 2017 market, export-weighted market prices; 252.66 before Norway's exports counted as such, K56). Non-EU supply: each region's own-price
  elasticity, CAPRI's p_elasSupp of its CAPRI regions (`supply_elas_region.csv`; until 23 October 2026 one value per
  product from `armington_params.csv`, removed on 29 October 2026, KNOWN_ISSUES K72). Non-EU feed demand (the trade
  regions without CAPRI's FeedNQ_ regions, `market.noneu_feed_nq` off, and the dairy products fed): CAPRI's
  p_ElasFeed (`feed_demand_nonEU.json`; the generic response of `armington_params.csv`'s eta column was removed on 24
  October 2026).
- EU output, `MaprFeed_` (`MarketModule.eu_feed_byproduct_output`, `feed_byproducts.csv`): prod0 × Σ weight × the
  parent's current food response (human consumption and processing) or sugar's biofuel feedstock use relative to the
  reference; prod0 is CAPRI's 2030 EU output: FPRI 26.8 Mt from 72.7 Mt of cereals eaten or processed (wheat 73% of
  the weight), FENI 5.5 Mt from 18.2 Mt of sugar (12.5% of the weight from biofuel processing). With `eu_blocks` the
  output and the parents' weights are split by CAPRI's member-state data.

REGISTERED: one EU share for MaprFeed_ (CAPRI's is per member state); the parents' food response stands for their
human consumption plus processing; one non-EU supply elasticity per product (as for the other commodities).

## Non-EU feed demand and the feed energy balance (audit M3, 29 October 2026)

CAPRI (`arm/market_model.gms` l. 1018-1047): each non-EU behavioural region without supply models feeds by its
normalised-quadratic feed function FeedNQ_ of the Arm1 prices and of its feed energy price FEDE; FEDE clears FeedBal_,
the energy of the feed used against the energy its animal output needs (output x pv_feedConv); FEDE is also a column of
the region's market supply functions (ProdNQ_), so dearer feed energy lowers animal output and raises feed crops'.

- Data (`tools/build/build_feed_energy.py`, `build_noneu_feed_nq.py`): calorie contents p_calContent (USDA Energ_cal of
  CAPRI's nutrient_cont_usda.gdx), the FEDE quantity and price at CAPRI's 2030 calibration (arm/market1.gms l. 402-408),
  the feed conversion factors pv_feedConv fitted as `arm/feed_conv.gms` (m_fitFeedConv; per region, solved exactly),
  CAPRI's p_hessNQFeed completed as on loading. Checks: CAPRI's p_ElasFeed and p_hessNQFeed imply the builder's FEDE
  price in all 45 regions (ratio 1.00000000); the feed terms reproduce p_ElasFeed (10,443 terms, 1e-14), the supply
  functions' FEDE terms p_elasSupp.
- Market (`MarketModule.noneu_fede`, `noneu_feed_change`, `demand_response`, `_noneu_market_supply_nq`): per behavioural
  region FEDE is solved in closed form at each evaluation's prices (both sides linear in FEDE); a trade region's feed of a
  product changes by the sum of its regions' changes over CAPRI's base feed of all its members (those with supply models
  in CAPRI, outside FeedBal_'s domain, held). The raw milk output in the balance is the dairy block's of the latest
  evaluation (the block is solved later in the same evaluation). The dairy products fed keep the FMIL block.
- REGISTERED: CAPRI's FeedFudge_ (non-negative feed) not ported (feed floored at 0); the share rule of the fit's
  feasibility loop read per region (`build_feed_energy.py`); CAPRI's FEDE elasticity calibration normalises FEDE by 1,
  its FeedNQ_ by the market's INPE: the market follows the equation.

