# capri_data/fao_2021 — 2021-vintage FAO data

Base data is 2017 (FAO_agg_17) with real CAPRI producer prices. This folder holds
2021-vintage FAOSTAT data. Status of each piece:

## APPLIED to the model (an improvement, validated)
- `fao_bilateral_trade_2021.json` — real bilateral trade flows for 2021 (2,628 cells,
  15 primary commodities). Direction verified (uni_1=exporter). Validates against reality:
  Australia/USA/Canada top wheat exporters; Brazil #1 soybean exporter (overtook USA);
  USA/Ukraine top maize exporters. **This replaced the older 2005 trade flows** in
  `../trade_flows.csv`. Model result unchanged at 12/12 commodities @ 0% vs CAPRI, market
  converges — but the Armington import structure is now current and more accurate.
  (Previous 2005 flows backed up at `../trade_flows_2005_backup.csv`.)
- `fao_trade_dictionary_2021.json` — region + commodity code→label maps used.

## STORED but NOT applied (would be a regression as-is)
- `fao_market_baseline_2021.json` — 2021 production/consumption/trade quantities.
  NOT wired in: the 2021 commodity-balance file has duplicate milk codes (2848 & 2948,
  identical values) and coarser coverage (328 vs 465 cells), which double-count/miscount
  EU milk (came out -22%, spurious). Applying it would degrade the baseline. The validated
  2017 quantity baseline (`../fao_market_baseline.json`) is retained.
- `fao_2021_dictionaries.json` — code maps for the 2021 commodity-balance/land-use file.

## What is still missing for a full 2021 refresh
Producer PRICES for 2021. The files provided are FAOSTAT quantities + trade; they contain
no PPRI/PMRK. Prices still come from the 2017 CAPRI SUA. A 2021-vintage CAPRI `fao_agg`
GDX (the SUA *with* prices, from results/global/) would complete the refresh.

## STORED but NOT applied — FAOSTAT producer prices 2024 (prices/ subfolder)
- `prices/faostat_producer_prices_eu.json` — EU producer prices (USD/t and EUR/t),
  12 commodities, latest year ~2024, from FAOSTAT Prices_E_All_Data (1.3M rows).
  NOT wired in: these are 2024 prices, but the model is calibrated as a 2017 system
  (2017 quantities, trade, elasticities). Mixing 2024 prices with a 2017 baseline
  breaks vintage consistency. Also FAOSTAT USD producer prices differ in methodology
  from CAPRI's EUR SUA prices, so adopting them means the model no longer validates
  against CAPRI's own reference. Useful only for a *full* re-base to ~2024 (prices +
  quantities + trade + re-estimated elasticities), not a piecemeal price swap.
