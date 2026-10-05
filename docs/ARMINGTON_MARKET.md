# Market structure: regional producer prices with Armington trade — design

Status: **design** (item 1 of the open list: meat and dairy market structure).

## The gap

Farm-to-Fork 2030 against JRC121368: beef price +2.6% (CAPRI +24%), pork +12.5%
(+43%), poultry +8.7% (+18%). Cause: in `MarketModule.domestic_prices`, every
region's price is the **world price × (1 + tariff)** — perfect transmission, one
world price per commodity cleared by tatonnement. An EU supply cut can only move
the EU price as far as it moves the world price. An Armington class exists and is
calibrated at start-up but never sets prices.

## CAPRI's structure (`arm/market_model.gms`)

- `SupBalM_`: each region's own good — domestic sales = production − exports
  (− intervention and private stock changes).
- `ArmFit1_`: total domestic use (first Armington aggregate) = imports aggregate
  + domestic sales.
- `arm2QuantShares_`: imports = use × δ × (composite price ÷ import price)^ρ₁;
  domestic sales likewise against the producer price.
- `ArmFit2_`, `impQuant_`, `impPrice_`: imports are bilateral flows; each import
  price = exporter's producer price + transport cost + tariff (`TRQImports_` for
  tariff-rate quotas).
- `wldMarket_`, `PPri_`: producer prices per region; no single world price.
- ρ₁ (`p_rhoArm1`, `arm/market1.gms`): 8.0 for agricultural products, 3.0 for
  biofuels (subject to its Armington calibration).

## Plan

Step 1 — CAPRI's first stage, pooled second stage:
1. Own producer price per region and commodity; supply and feed respond to it.
2. Domestic use = CES composite of domestic sales and imports, ρ₁ per
   commodity; shares calibrated so base flows and prices are reproduced exactly.
3. Imports come from a world pool at pool price × (1 + tariff); exports go to
   the pool with a CES export demand; the pool clears Σ exports = Σ imports.
4. Region clears its own good: production = domestic sales + exports.
5. Validation: base exact; anchors; Farm-to-Fork meat prices against CAPRI.

Step 2 — bilateral flows and tariff-rate quotas (beef, poultry, dairy), using
CAPRI's trade flows already partitioned in `capri_trade_regions_2017.json`.

Open data check: `armington_params.csv` gives ρ₁ of 3.5 (beef), 6.7 (pork),
labelled "CAPRI", while CAPRI's code sets 8.0 by default — provenance to resolve
before step 1 uses them.
