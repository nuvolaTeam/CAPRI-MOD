# capri_data/sources/fao_2021 — FAOSTAT 2021 extracts (none kept)

Moved here from `capri_data/fao_2021/` (October 2026). Nothing in the model read these files, and none is left: five
removed 29 October 2026 (read by no code; KNOWN_ISSUES K102): `fao_bilateral_trade_2021.json`,
`fao_trade_dictionary_2021.json`, `fao_market_baseline_2021.json`, `fao_2021_dictionaries.json`,
`prices/faostat_producer_prices_eu.json`; `trade_flows_2021.csv` removed 3 November 2026. This note records them. What they were:

- `fao_bilateral_trade_2021.json`, `fao_trade_dictionary_2021.json`, `trade_flows_2021.csv` - FAOSTAT bilateral trade
  2021 (15 primary commodities) and its code maps. They once replaced the 2005 flows of the first market; the model
  uses CAPRI's own bilateral market (2017 and 2030 flows `2017/market/bilateral_flows_*.csv` from CAPRI's market
  results). `trade_flows_2021.csv` was read only by `tools/build/recalibrate_trade_2017.py`, as the comparison of its
  matrix `shared/trade_flows_2017.csv`, which no code read: both removed 3 November 2026 (the market's move onto
  CAPRI's regions, stage 1).
- `fao_market_baseline_2021.json`, `fao_2021_dictionaries.json` - 2021 production/consumption/trade quantities.
  Never applied (duplicate milk codes, coarser coverage); the market's balances are CAPRI's FAO_agg and market
  results.
- `prices/faostat_producer_prices_eu.json` - FAOSTAT producer prices (to 2024). Never applied: the model's prices
  are CAPRI's (2017 base, 2030 trajectory); mixing vintages would break its calibration.
