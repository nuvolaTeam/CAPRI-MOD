# World market base and the retired market placeholders

Status: revised 20 October 2026 against the code. Since the bilateral market (Sprint 8m, October 2026;
[ARMINGTON_MARKET.md](ARMINGTON_MARKET.md)) every traded product's regional balances and trade come from CAPRI's
market results of the run's year; the FAO_agg world base described here now serves only the product without
bilateral trade (raw milk) and the retired `premium` structure. The sections "What was wrong" and the placeholders
are historical; they are kept because they explain data choices still in the model.

## What the model uses now

Base production and use per market region are set in `MarketModule._calibrate_baseline`:

1. Products with CAPRI bilateral flows (57 of 58): production = the region's market production (PROD) of
   `bilateral_regions_<year>.csv`, use = domestic sales + imports of `bilateral_flows_<year>.csv`, for the market year
   of the run (2017, or CAPRI's 2030 reference in a projection). The EU's rows are then set from the supply models
   and the bilateral calibration closes every region (ARMINGTON_MARKET.md, "Calibration").
2. Products without bilateral flows (raw milk): CAPRI's FAO_agg base-period balance,
   `capri_data/2017/market/world_market_baseline.json` (`tools/build/build_world_market_baseline.py`), and
   `dairy_world_baseline.json` for the dairy products where needed. With CAPRI's two EU trade blocks the EU row is split
   by CAPRI's 2030 member-state production and use (`eu_ms_balance_2030.csv`).
3. Neither: zero (no invented totals; a product without a world price raises an error).

`world_market_baseline.json` holds CAPRI's FAO_agg base-period balances (MAPR, DOMM, IMPT, EXPT) of every CAPRI
behavioural region, mapped to the model's trade regions (concordance of `tools/build/recalibrate_trade_2017.py`), under the
model's codes (SWHE ← WHEA, CORN ← MAIZ, SUGR ← SUGA, POUL ← POUM, WINE ← TWIN, the rest by name; rye, oats and other
cereals separate as in CAPRI). Its EU row also gives the EU's self-sufficiency (use / production) applied to the
model's EU production in `_align_eu_base_balance` (where FAO_agg has no EU row, the older FAO extract
`fao_market_baseline.json` is still read, `_fao_eu_rows`) before the bilateral closure replaces the use of the
traded products.

## Sugar beet, sugar and the dairy products

- Sugar beet has no market, as in CAPRI: member states process beet into white sugar at their own yield
  (`sugar_processing.csv`, `tools/build/build_sugar_processing.py`: CAPRI's 2030 reference beet harvest and processing,
  sugar produced, PRCY 0.13-0.19, EU sugar per tonne of beet harvested 0.156). The supply bridge makes sugar = beet ×
  the member state's sugar per beet (`model._sugar_per_beet`); beet's price signal is the sugar price change
  (`model.py`, as CAPRI `arm/set_prices.gms`).
- Without the dairy block's data (its switch `market.use_dairy_block` was removed on 27 October 2026) the dairy products are raw milk × CAPRI's
  member-state 2030 yields (output less processing per tonne of raw milk, `dairy_processing.csv`;
  `model._dairy_yield`). With the block (the default) the market replaces them by the block's output.

## What was wrong (historical, before October 2026)

The market's base came from three sources stacked on each other: a FAO extract (`fao_market_baseline.json`),
CAPRI's FAO_agg where the extract had nothing, and a hard-coded world total split by fixed regional shares. Checked
against CAPRI's FAO_agg it was not CAPRI's world and in places not the right product: the extract's sugar was sugar
cane (model world 1,768 Mt against CAPRI's 168 Mt of sugar), pork and eggs carried invented allocations, wine an
invented total, and other cereals lacked rye and oats. The world total decides how far an EU supply change moves a
pooled world price, so these errors changed the EU's weight in world markets.

Placeholders removed at the same time:

- a world market for sugar beet (an invented 1,900 Mt) on top of sugar made from beet;
- FATS and OFOD_M ("fats", "other food"): markets with no supply, no use and invented totals (CAPRI's FATS and PROT
  are the dairy block's milk fat and protein);
- rye and oats without a market (their price came from other cereals);
- dairy products as fixed FAO EU-average ratios of milk (cheese 0.0456 t per t against CAPRI's 0.068).

The effect of the change on the results of that time is recorded in CHANGELOG.md ("Star 3.0 as the reference:
technology settings, world market base, placeholders, baseline check"). The registered gaps of that version (durum
wheat, paddy rice and olives without a matching CAPRI world product) are closed: durum is part of CAPRI's wheat
market, olives and paddy rice reach the market as olive oil and milled rice.
