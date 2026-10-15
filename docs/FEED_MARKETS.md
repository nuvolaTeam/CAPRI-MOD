# Feed bulks and residual feed markets (Sprint 9h)

## CAPRI's structure (`arm/market_model.gms`, `global/fromimpact/sets.gms`)

The supply models buy feed as **bulks**; the market splits each member state's bulk into market products and
prices it:

| Bulk | Products (FEED_TO_O) | p_rhoFeed (member states, `arm/market1.gms`) |
|---|---|---|
| FCER cereals | WHEA, DWHE, RYEM, BARL, OATS, MAIZ, OCER, PARI, RICE | 6 |
| FPRO protein-rich | PULS, oils (RAPO, SUNO, SOYO, OLIO, OTHO), cakes (RAPC, SUNC, SOYC, OLIC, OTHC), DDGS, FPRI, fish meals | 6 |
| FENE energy-rich | MOLA, STAR, FENI | 5 |
| FOTH other | POTA, whole oilseeds (RAPE, SUNF, SOYA), OLIV, OOIL, TEXT, TOMA, OVEG, APPL, OFRU, CITR, TAGR, TABO, TWIN, SUGA, EGGS, PORK, BEEF | 0.5 |
| FMIL milk products | SMIP, WMIO, CASE, WHEP, BUTT, CREM, COCM, CHES, FRMI | 0.5 |

- `feedBlkPrice_`: bulk price = CES index of the products' Arm1 prices → the supply models' feed prices.
- `feedShareEqu_`: product feed use = bulk use × (bulk price / product price)^rho, calibrated to the reference.
- The **residual feeds** FENI (sugar-beet by-products, manioc, roots) and FPRI (milling by-products) are traded
  market products whose only use is feed. Where there are supply models their output is a fixed share of the
  parents' processing (`MaprFeed_`): FPRI from the human consumption and processing of the cereals (WHEA, SWHE,
  DWHE, RYEM, BARL, OATS, MAIZ, OCER, PARI), FENI from sugar (human consumption, processing and biofuel
  processing). Elsewhere a supply function (`prodNQ_`).

## The model

- **All five bulks per member state** (`tools/build_feed_bulks.py`, `feed_bulks_eu.csv`; CAPRI's 2030 member-state
  feed use and Arm1 prices from `markmarket_greendeal_1730et_base_1717`). Each ration's FCER, FPRO, FENE, FOTH and
  FMIL is priced at its member state's bulk index (`RationModel.price_vector(bulk_ratio=)`; before Sprint 9h only
  FCER and FPRO, the others at base prices). The bulks' use per member state comes from the supply models'
  feeding (`CAPRIModel._set_feed_demand`, all five bulks).
- **EU feed use** of each product follows its bulks (`MarketModule.eu_feed_use`); the feed part of the EU's use
  of each product is CAPRI's 2030 feed share of use (`feed_bulks_eu_share.csv`, now including processing PRCM in
  the use, so the oilseeds fed whole - FOTH - get their feed share of total use, crushing included). The feed
  correction is now added to the row rather than replacing it, so crushing demand already in the row is kept.
  The dairy products' feed use comes from the FMIL bulks per member state (it was one EU FMIL index).
- **FENI and FPRI markets** (`tools/build_bilateral_market.py`, `tools/build_feed_byproducts.py`): CAPRI's bilateral
  flows, regional market prices and Armington elasticities (FENI 4 / 8 from `market1_ch.gms`, FPRI 8 / 10); world
  prices FENI 312.77 (FAO_agg World PMRK BAS), FPRI 252.66 (FAO_agg has none: CAPRI's 2017 market, export-weighted
  market prices); non-EU supply elasticity CAPRI's own-price p_elasSupp weighted by production (FENI 0.44, FPRI
  0.98); non-EU feed demand with CAPRI's p_ElasFeed (`feed_demand_nonEU.json`, now with FENI and FPRI rows and
  columns), own-price elasticity for the regions without a row the mean of CAPRI's (FENI −1.59, FPRI −2.41).
- **EU output, `MaprFeed_`**: prod0 × Σ weight × (parent's food and processing response, or sugar's biofuel
  feedstock use relative to the reference) (`MarketModule.eu_feed_byproduct_output`), prod0 CAPRI's 2030 EU output
  (FPRI 26.8 Mt = 0.369 × 72.7 Mt of cereals eaten or processed; FENI 5.5 Mt = 0.302 × 18.2 Mt of sugar).
  Baseline: EU production and use exactly CAPRI's 2030 reference.

REGISTERED: one EU share for MaprFeed_ (CAPRI's is per member state); the parents' food response stands for their
human consumption plus processing; MOLA, STAR, the fish meals and the FOTH products without a model market at
their reference price; one non-EU supply elasticity per product (as for the other commodities).

## Farm-to-Fork 2030 (s75)

FENI and FPRI prices −10% (feed use falls with the herds, as for cakes −10%); 20-indicator gap 4.59 → 4.53
(oilseed price +14.9% against +15.7%, beef animals −18.5% against −19.1%).
