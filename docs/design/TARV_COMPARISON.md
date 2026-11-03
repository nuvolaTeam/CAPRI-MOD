# CAPRI's TARV against capri-mod's tariffs.csv (task 301, 3 November 2026)

The comparison asked for before switching policy/tariffs.csv to CAPRI's DATA(RMTP, "TARV", XX, "CAL")
(MARKET_REGIONS_INVENTORY §7 item 6; MODEL_CONTENT_PLAN §1 item 8). Reproduced by
`python tools/check/compare_tarv.py [OUT.csv]`.

## What is compared

- **capri-mod** (capri_data/2017/policy/tariffs.csv, tools/build/build_tariffs_2017.py): per trade region and
  commodity, the total ad-valorem equivalent CAPRI's 2017 flows paid,
  100 x (sum ImportQ x ImportP / sum ImportQ x (Fob + TCost) - 1), over imports from outside the region. It includes
  ad-valorem and specific tariffs, preferences and in-/out-of-quota rates as they applied to the flows.
- **CAPRI** (capri_sources/exports/data_market_1730defaulta.csv, `'RMTP'.'TARV'.'XX'.'2017'` and `'CAL'`): the
  ad-valorem tariff of each trade-policy block (42 RMTP, the EU as one block "EU"); the specific tariff is a separate
  item, TARS (EUR/t). TARV 2017 = TARV CAL in every matched record.

Matching: the model region where its name is an RMTP code (EU27 -> EU, NOR -> NO000000, UK -> UK000000); products
through build_bilateral_market.MODEL (one CAPRI product per model commodity). 18 of 28 model regions, 704
region-commodity pairs. Not matched (no RMTP of that name): ARG, BRA, GBR, IDN, JPN, KOR, MAR, ROW, THA, VNM (inside
CAPRI's MER, ASOCE_*, MED and other blocks; stage 3 moves the model onto those).

## Result

| | pairs | mean absolute difference (pp) |
|---|---|---|
| all | 704 | 4.03 (median 0.0; 76% within 0.01 pp) |
| with a specific tariff TARS > 0 | 11 | 55.2 |
| without | 693 | 3.2 |

Mean absolute difference per region (pp): AUS, UKR, ZAF, WBA 0.0; NZL, ETH 0.1; CHN, RUS 1.3; NGA 2.2; IND, TUR, BGD
2.3; PAK 2.9; EU27 3.2; USA 3.6; MEX 11.8; NOR 12.6; CAN 29.4.

Largest gaps: CAN cheese 0.0 vs TARV 245.6, butter 112.9 vs 313.6, poultry 33.1 vs 178.2; NOR eggs 0.0 vs 219.6,
pork 0.0 vs 117.9; EU cheese 6.2 vs 33.1, sheep and goat meat 0.1 vs 12.8 (plus TARS 1060.85 EUR/t), tomatoes 20.0
vs 11.0.

## Reading

The two measure different things. TARV is the block's ad-valorem rate, before tariff-rate quotas, preferences and
specific tariffs; capri-mod's number is what the 2017 flows actually paid. Where they differ most, the trade enters
under quotas or preferences (Canada's and Norway's dairy, eggs and meat: high out-of-quota rates, imports in-quota),
or a specific tariff carries the protection (EU tomatoes, sheep meat).

In CAPRI the tariffs act bilaterally on the import price: TARV and TARS on each flow, with the bilateral TRQs and
preferences (arm/market_model.gms). capri-mod uses one number per region and commodity, only for the reference price
level p_world x (1 + t / 100) (MarketModule.domestic_prices) and for scenario tariff changes; the bilateral market
itself is calibrated on CAPRI's import prices.

## Recommendation (for the project lead's decision)

Putting TARV into tariffs.csv as it is would raise the protection of quota and preference trade by up to 245 pp
(Canada's cheese) and leave out specific tariffs, so it would move the reference price levels away from CAPRI's
market prices rather than closer. My suggestion, a departure from the plan of 2 November, not from CAPRI:

1. Keep tariffs.csv in stage 2.
2. Bring TARV, TARS, the bilateral TRQs and preferences in with the ports (stages 4-7), as CAPRI's bilateral wedges
   on the import price, and with them CAPRI's own prices (Armington and producer prices) as the reference price
   levels (ARCHITECTURE_REFACTOR 5.1, M1), which removes the need for one tariff per region.
