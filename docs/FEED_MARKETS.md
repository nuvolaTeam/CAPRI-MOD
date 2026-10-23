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
  Arm1 price ratios. The feed part of the EU's use of a product is CAPRI's 2030 feed share of use
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
  CAPRI's 2017 market, export-weighted market prices; 252.66 before Norway's exports counted as such, K56). Non-EU supply: one own-price elasticity per product
  (`armington_params.csv` eps: FENI 0.44, FPRI 0.98, CAPRI's p_elasSupp weighted by production). Non-EU feed demand:
  CAPRI's p_ElasFeed (`feed_demand_nonEU.json`); regions without a CAPRI feed function keep the generic own-price
  response (`armington_params.csv` eta: FENI −1.56, FPRI −2.42).
- EU output, `MaprFeed_` (`MarketModule.eu_feed_byproduct_output`, `feed_byproducts.csv`): prod0 × Σ weight × the
  parent's current food response (human consumption and processing) or sugar's biofuel feedstock use relative to the
  reference; prod0 is CAPRI's 2030 EU output: FPRI 26.8 Mt from 72.7 Mt of cereals eaten or processed (wheat 73% of
  the weight), FENI 5.5 Mt from 18.2 Mt of sugar (12.5% of the weight from biofuel processing). With `eu_blocks` the
  output and the parents' weights are split by CAPRI's member-state data.

REGISTERED: one EU share for MaprFeed_ (CAPRI's is per member state); the parents' food response stands for their
human consumption plus processing; one non-EU supply elasticity per product (as for the other commodities).
