# World market base and the market placeholders

Status (October 2026): **done, default; for traded products superseded by CAPRI's bilateral market** (Sprint 8m,
[ARMINGTON_MARKET.md](ARMINGTON_MARKET.md)), which takes every region's balance and trade from CAPRI's market results of
the run's year. The FAO_agg base below still serves the pooled markets (raw milk) and the `premium` structure.
Durum wheat, olives and paddy rice now reach the market as CAPRI's wheat, olive oil and milled rice.

Earlier status: **done, default.** Every region's base balance comes from CAPRI's own database; sugar is
made from beet the way CAPRI makes it; the two placeholder markets are gone; rye and oats reach a market; without
the dairy block, dairy products leave the dairy at CAPRI's own yields.

## What was wrong

The market builds each region's base production and use before it calibrates its demand (`MarketModule.
_calibrate_baseline`). That base came from three sources stacked on each other: a FAO extract
(`fao_market_baseline.json`), CAPRI's FAO_agg extended SUA where the extract had nothing, and, for whatever
neither had under the model's code, a hard-coded world total split by fixed regional shares. Checked against
CAPRI's FAO_agg (base period), the result was not CAPRI's world and in places not even the right product:

| Commodity | model world (kt) | CAPRI FAO_agg (kt) | cause |
|---|---|---|---|
| Sugar | 1,767,711 | 167,924 | the extract's "SUGR" is sugar cane (Brazil 715 Mt) |
| Pork | 171,016 | 120,000 | invented allocation |
| Eggs | 126,061 | 83,925 | invented allocation |
| Maize | 1,590,721 | 1,135,640 | extract |
| Wine | 70,000 | 27,259 | invented total (CAPRI code TWIN never matched) |
| Other cereals | 83,625 | 155,507 | rye and oats missing |

The world total decides how far an EU supply change moves the world price: with a world pork market 43% too
large, the EU (23 Mt) weighed 13% instead of 19%; in sugar it weighed 1% instead of 10%.

Further placeholders in the market:

- **Sugar beet** had its own world market (an invented 1,900 Mt) and every tonne of beet also became 0.135 t of
  sugar. CAPRI has no beet market: member states process beet into white sugar at their own yield (PRCY, 0.13
  to 0.19) and the beet price follows the sugar price.
- **FATS and OFOD_M** ("fats", "other food") were markets with no supply, no use, invented world totals and
  literature elasticities. CAPRI has no such products; its FATS and PROT are the dairy block's milk fat and
  protein.
- **Rye and oats** were supply activities whose output reached no market (their price came from OCER). EU
  other cereals in the market: 15 Mt against CAPRI's 36 Mt.
- **Dairy products without the dairy block** were fixed FAO EU-average ratios of milk (cheese 0.0456 t per t;
  CAPRI's 2030 yield 0.068).

## What the model does now

- **`tools/build_world_market_baseline.py`** → `capri_data/2017/market/world_market_baseline.json`: CAPRI's
  FAO_agg base-period balances (MAPR, DOMM, IMPT, EXPT) of every CAPRI behavioural region, mapped to the model's
  trade regions (concordance of `tools/recalibrate_trade_2017.py`), for 32 market commodities (SWHE ← WHEA,
  CORN ← MAIZ, OCER ← OCER + RYEM + OATS, SUGR ← SUGA, POUL ← POUM, SHGM ← SGMT, WINE ← TWIN, BUTR ← BUTT,
  SKIM ← SMIP, WHEY ← WHEP, the rest by name). The market takes every region's production from it, and the EU's
  base self-sufficiency (domestic use / production) from its EU row.
- **`tools/build_sugar_processing.py`** → `sugar_processing.csv`: per member state CAPRI's beet harvest and
  processing, sugar produced and PRCY (2030 reference). The supply bridge makes sugar = beet × sugar per beet
  of the member state (EU 0.156); beet's price signal is the sugar price change (CAPRI `arm/set_prices.gms`).
- FATS, OFOD_M and SUGB removed from `MARKET_COMMODITIES`.
- OCER market supply = OCER + RYEM + OATS.
- Dairy products without the block: output less processing per tonne of raw milk at CAPRI's member-state 2030
  yields (`dairy_processing.csv`).

REGISTERED: durum wheat, paddy rice, other oilseeds and olives have no CAPRI world balance under a matching
product (CAPRI's world markets are wheat, milled rice, and olive oil) and keep the previous base; SWHE's world
market is CAPRI's wheat, so durum is counted in both (about 5% of world wheat).

## Effect

Farm-to-Fork 2030 (default model): 20-indicator gap 4.36 → 4.51. Pork price +19.6 → +21.1% (CAPRI +43), beef
+12.8 → +9.0% (+24), poultry +20.6 → +16.4% (+18), other cereals +19.6 → +3.3% (the market now has rye and oats
and its EU share is 20% of a 156 Mt world). The beef and poultry prices move away from CAPRI: their EU Armington
premium falls (beef 1.115 → 1.077) once the EU's trade sits in a world of CAPRI's size. This is the premium
approximation's response, not CAPRI's; the full bilateral market is the next step
([ARMINGTON_MARKET.md](ARMINGTON_MARKET.md)). The data change is kept: it is CAPRI's data, and tuning the
world back to a size CAPRI does not have would hide the structural gap.

Baseline reproduction against CAPRI's own 2030 reference ([BASELINE_REPRODUCTION.md](BASELINE_REPRODUCTION.md)):
EU sugar production −8% → +7% (beet area +11%), other cereals −58% → −2%, cheese −39% → −12%.
