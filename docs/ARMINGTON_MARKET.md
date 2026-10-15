# Market structure: regional producer prices with Armington trade — design

Status (October 2026): **CAPRI's bilateral market built and default** (Sprint 8m, below). The earlier
resolution - the EU Armington premium with reporting and demand fixes - is kept as `market_structure = "premium"`.

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
  biofuels (subject to its Armington calibration); `special_ch/market1_ch.gms` sets 2.2 (ρ₂ 4.5), which capri-mod
  uses since biofuels are traded (Sprint 9c, docs/BIOFUEL_MARKET.md).

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

## Revision: the mechanism exists; the gap was mostly reporting

`MarketModule.eu_armington_premium` already implements CAPRI's first-stage
clearing for the EU (gross extra-EU trade, σ for domestic sales against
imports, ρ₂ for exports), and farmers respond to (world × tariff) × premium.
Results, however, report the EU price **without** the premium, and all
Farm-to-Fork comparisons used it. With the premium (2017 base): poultry +19.5%
(CAPRI +18%), wheat +9.5% (+8%), milk +1.7% (+1.5%), pork +25.5% (+43%),
rapeseed +24.1% (+11%, overshoot), beef +5.4% (+24%). Elasticities confirmed as
CAPRI's effective values (`special_ch/market1_ch.gms`, Fontagné, Guimbard &
Orefice 2019). Next: report producer prices with the premium; then beef and the
rapeseed overshoot.

## Outcome (October 2026)

- **Reporting**: `MarketEquilibrium.domestic_prices` now carries the EU producer price
  (world price × tariff × Armington premium); the old value is kept as `wedge_prices`.
- **Demand bug**: `demand_response` measured prices against the base world price
  instead of the base domestic price, cutting every tariff-protected region's base
  demand by (1 + tariff)^elasticity (EU beef 17% too low). Fixed; base unchanged.
- **Beef**: with CAPRI's 18% beef supply cut the model's own market gives about +28%,
  CAPRI's range; the remaining beef gap is on the supply side, not in the market.
  Tariff-rate quotas were checked: the model's tariff already equals CAPRI's
  out-of-quota cost at the margin.
- Bilateral flows and quotas were therefore not built.

## Sprint 8m (done, October 2026): CAPRI's bilateral market, default

The planned structure below is built and is the default (`MarketModule.market_structure = "bilateral"`;
`"premium"` keeps the earlier approximation). Code: `capri_mod/market/bilateral.py` (one commodity's system),
`MarketModule._solve_bilateral*` (calibration, solve, reporting).

**Data** (`tools/build_bilateral_market.py`, from CAPRI's own market results): every bilateral flow with its
price components - ImportQ, ImportP, Fob, TCost, TaAppl - of CAPRI's base market (`market_base_1717`, 2017) and
of its 2030 Green Deal reference (`markmarket_greendeal_1730et_base_1717`), aggregated to the model's 29 trade
regions as `bilateral_flows_<year>.csv`: per (importer, exporter) the quantity and the import price split into
the part that moves with the exporter's market price, a = Fob (1 + ad valorem), and the fixed part, b = TCost
(1 + ad valorem) + specific tariffs and TRQ effects (ImportP minus the rest) - CAPRI's `impPrice_` aggregated
exactly at the base composition. Market prices (PMRK) and production per region: `bilateral_regions_<year>.csv`.
Substitution elasticities rho1, rho2 per product: `armington_rho.csv` from `arm/market1.gms` (8 / 10) with
`special_ch/market1_ch.gms` (CEPII, Fontagne, Guimbard & Orefice 2019) as CAPRI includes it: beef 3.5 / 7.1,
pork 6.7 / 13.4, wheat 3.9 / 7.8. The market year follows the run: a 2030 projection uses CAPRI's 2030 flows
(`data["market_year"]`), so the non-EU world is CAPRI's 2030 world, not the base period's.

**Products.** The market's products are now CAPRI's traded ones: wheat (soft + durum; durum's price follows
it), other cereals with rye and oats, milled rice (paddy x CAPRI's EU ratio 0.40), olive oil (olives x CAPRI's
member-state yield, EU 0.20), white sugar. `tools/build_processing_yields.py`. Raw milk and other oilseeds have
no CAPRI bilateral trade and clear as pooled markets (one price ratio for all regions).

**Equations** (per traded product and region): own good S = domestic sales + sum of exports; total use D at the
consumer price PA, the CES aggregate of the region's market price and the import aggregate PM; imports by origin
from a CES over import prices a r + b. Supply at the region's own market price (non-EU: CAPRI's market supply
elasticities; EU: the supply models' output, anticipated against the price farmers last saw; crushing and the
dairy blocks at regional prices); use from the existing demand functions at the consumer price.

**Calibration.** CAPRI's flows are kept and each region's domestic sales absorb the difference between the
model's own production and CAPRI's (exports capped at 98% of production); use at the reference prices is
exactly the closure's. In a BASELINE run the market is recalibrated at each outer iteration, so the baseline
sits at the reference prices (as CAPRI's calibrated reference does) and a scenario inherits the calibration
at the converged baseline supply (cached with the baseline).

**Solver.** Successive linearisation: the full model response (supply anticipation, crushing, dairy, feed and
biofuel demand) is evaluated, each product's trade system is then solved exactly (Newton) with supply and use
log-linear around that point (own-price responses measured once per calibration), and the step repeats until the
largest relative supply-balance residual is below 1e-7 (about 0.07 s per evaluation, 40-60 evaluations).

**Tariff-rate quotas.** CAPRI's EU bilateral TRQs (`TrqNT` of the policy block EU; `build_trq`,
`bilateral_trq_<year>.csv`): per model exporter the quota, the gap between out-of-quota (MFN: TAMFN, TSMFN) and
in-quota price, and the share of the flow under the quota regime. The specific tariff on the flow moves with
CAPRI's sigmoid (`trqSigmoidFunc_`: slope 200 on (imports - 0.97 quota) / quota), relative to the base fill so
the base is reproduced; each quota's tariff is solved consistently with its own flow (bisection) at every step.
In CAPRI's 2030 reference the EU's meat quotas are far from filled (beef 13 of 157 kt from the exporters with
bilateral quotas, poultry 108 of 422), so under Farm-to-Fork they do not bind: results are unchanged by them.
REGISTERED: global (erga omnes) quotas, in-quota specific tariffs other than CAPRI's applied ones, and CAPRI's
augmented-CES commitment terms (p_arm2Commit) are not represented.

**Farm-to-Fork 2030** (default model): 20-indicator gap 4.51 -> **3.48** with the bilateral market; with the
projection fixes of the same sprint (docs/BASELINE_REPRODUCTION.md) **3.30**. Prices against CAPRI (JRC121368):
cereals +8.0% (+8), oilseeds +16.0% (+11), vegetables and permanent crops +12.3% (+15), beef +17.1% (+24), pork
+33.8% (+43), poultry +22.7% (+18), milk +4.6% (+1.5). Pigs -21.1% (-14.5). Without the dairy block the EU's
dairy products clear on their own markets while raw milk follows the pooled milk market: butter, cheese and
whey prices rise 35-60% with EU milk supply and do not reach the milk price (with the block they would; the
opt-in block was not re-run with the new market).

## Sprint 8 (planned, October 2026): CAPRI's full market, region by region

The decision above was taken before the world base was CAPRI's. With CAPRI's FAO_agg balances in every region
([WORLD_MARKET_BASELINE.md](WORLD_MARKET_BASELINE.md)) the EU premium approximation gives Farm-to-Fork beef +9%
(CAPRI +24) and pork +21% (+43), and the EU premium for beef fell when the EU's trade was put in a world of
CAPRI's size. Every remaining meat-price gap now runs through the one piece of the market that is not CAPRI's:
one world price per commodity, with the EU alone given an Armington premium. The plan is CAPRI's structure for
every region (`arm/market_model.gms`, simulation model m_globmarket):

| CAPRI equation | Content | Model |
|---|---|---|
| `SupBalM_` | domestic sales = production − exports (− stock changes) | per region, own producer price `v_marketPrice` |
| `ArmBal1_` | Armington aggregate = food + feed + processing + biofuel use | demand blocks as now, at the region's consumer price |
| `arm1PriceAgg_`, `arm2QuantShares_` | first CES nest: domestic sales against the import aggregate, ρ₁ (`p_rhoArm1`), shares `p_dpCESTrade` calibrated to base flows | new |
| second nest (`arm2Price_`, `ArmFit2_`) | import aggregate over origins, ρ₂, base bilateral flows `p_tradeFlows` | new; flows from CAPRI res_0_1717 (already in `trade_flows_2017.csv`) |
| `impPrice_` | import price = exporter's market price + transport cost, × (1 + ad valorem) + specific tariff | transport costs and tariffs from CAPRI (`p_transpCost`, `p_tarAdVal`, `p_tarSpec`) |
| `TRQImports_` / TRQ equations | in-quota and out-of-quota tariff, quota rent | EU beef, poultry, dairy, sugar first; CAPRI's `p_trqBilat` |
| `expQuant_` | exports = Σ bilateral flows from the region | identity |

Unknowns per traded commodity: one producer price per region (29). Equations: each region's supply balance.
Everything else (consumer prices, flows, imports) is explicit given the prices, so the system is 29 × 32 equations
in prices, block-diagonal by commodity except for the cross-price, feed, crushing, dairy and biofuel links that
already exist; Newton per commodity inside the existing Gauss-Seidel over commodities, as the dairy blocks are
solved now. Calibration: CES share parameters so that base flows and base prices are reproduced exactly; check
that a no-shock run returns every base flow.

Stages: (1) data — CAPRI's bilateral flows, transport costs, tariffs and TRQs for the model's trade regions,
with ρ₁, ρ₂ from `market1.gms` / `market1_ch.gms`; (2) the two-nest system without TRQs, replacing the world
price and the EU premium, validated by base reproduction and the baseline check; (3) TRQs; (4) Farm-to-Fork.
The EU block stays one region (CAPRI's EU trade block), as now.
