# The bilateral Armington market

Status: revised 21 October 2026 against the code (Norway as its own market region, K56). The last section ("Before the bilateral market") is historical.

The market is CAPRI's market model (`arm/market_model.gms`, simulation model m_globmarket) for every traded product:
a market price per region, total use an Armington aggregate of domestic sales and imports, imports a CES over
origins, bilateral flows priced at the exporter's price plus transport costs and tariffs. It is the only market
structure used by `CAPRIModel.run` (`MarketModule.market_structure = "bilateral"`, the default).

Code: `capri_mod/market/bilateral.py` (`BilateralCommodity`: one product's trade system, its calibration, TRQs) and
`MarketModule._bilateral_raw`, `_bilateral_calibrate`, `_bilateral_eval`, `_solve_bilateral`,
`_solve_bilateral_equilibrium` in `capri_mod/market/market_module.py`. How the system is solved:
[MARKET_SOLVE_CHECK.md](MARKET_SOLVE_CHECK.md).

## Regions and products

- 26 trade regions (`definitions.ALL_TRADE_REGIONS`): EU27, 24 non-EU countries and ROW (Egypt, Algeria, Saudi
  Arabia and Iran, regions without data, removed on 29 October 2026: KNOWN_ISSUES K45). One of them is Norway (NOR,
  since 21 October 2026, KNOWN_ISSUES K56): CAPRI's market region NO000000, its own market region in
  `gams/aggregation/defaultA.agg` and linked to supply models (RMSSUP); before, CAPRI's bilateral data folded it into
  ROW while its supply regions NO01-NO07 fed the EU's market supply.
- The EU is one market region by default. With `MarketModule.eu_blocks = True` (`run_f2f_2030.py --eu-blocks`) it is
  CAPRI's two trade blocks of `gams/aggregation/defaultA.agg`, EU_WEST (EU-14, with Belgium and Luxembourg as CAPRI's
  BL) and EU_EAST (EU-13), each with its own market prices and bilateral trade between them
  (`capri_data/shared/eu_market_blocks.csv`, data files `*_eu2.csv`). The EU's common external tariff and the EU's
  tariff-rate quotas apply to both blocks; an `EU27` row (quantities summed, prices production-weighted) is added to
  the results for reporting (`_with_eu_aggregate`). Norway is its own market region NOR in both settings, as in
  CAPRI.
- 58 market commodities (`definitions.MARKET_COMMODITIES`). 57 have CAPRI bilateral flows; raw milk (MILK) has none
  and clears as a pooled market (one price ratio for the non-EU regions); the EU's raw milk is priced by the dairy
  block ([DAIRY_PROCESSING.md](DAIRY_PROCESSING.md)).
- Products follow CAPRI's market products: wheat is soft plus durum wheat (durum's price signal follows wheat's,
  `model.py`), olives reach the market as olive oil and paddy rice as milled rice at CAPRI's member-state processing
  yields (`processing_yields.csv`, `tools/build/build_processing_yields.py`), sugar beet as white sugar
  ([WORLD_MARKET_BASELINE.md](WORLD_MARKET_BASELINE.md)); rye and oats are markets of their own.

## Equations

Per product and region i (`bilateral.py` docstring); Pd_i = Pd0_i r_i is the region's market price, r_i its ratio to
the reference:

| CAPRI equation (`arm/market_model.gms`) | Content | capri-mod |
|---|---|---|
| `SupBalM_` (l. 2632) | own good: production = domestic sales + exports | `BilateralCommodity.residual`; the unknowns are the r_i |
| `ArmBal1_` (l. 2602) | total use D_i at the consumer (Armington) price PA_i | the demand blocks of `demand_response` at PA_i |
| `arm2QuantShares_` (l. 2706), first nest | DS_i = D_i dd_i (PA_i/Pd_i)^s1, M_i = D_i dm_i (PA_i/PM_i)^s1 | `flows` |
| second nest | PM_i = [Σ_j beta_ij p_ij^(1−s2)]^(1/(1−s2)), X_ij = M_i beta_ij (PM_i/p_ij)^s2 | `prices`, `flows` |
| `impPrice_` (l. 2849) | import price = exporter's price + transport cost, with ad valorem and specific tariffs | p_ij = a_ij r_j + b_ij (below) |
| `trqSigmoidFunc_` (l. 3275) | tariff under a TRQ as a sigmoid of the quota fill | `trq_solve` (below) |

Import prices: per (importer, exporter) CAPRI's base import price is split into the part that moves with the
exporter's market price, a = Fob (1 + ad valorem), and a fixed part, b = TCost (1 + ad valorem) + specific tariffs
and TRQ effects (ImportP minus the rest): CAPRI's `impPrice_` aggregated exactly at the base composition of the
model's trade regions. a0 (Fob without the ad valorem tariff) carries a tariff change: `PolicyScenario.tariff_changes`
adds points of ad valorem tariff to the EU's imports (`import_prices`; flows between the EU blocks carry none).

## Data

`tools/build/build_bilateral_market.py`, from CAPRI's market results: the base market (`market_base_1717`) for 2017 and the
2030 Green Deal reference (`markmarket_greendeal_1730et_base_1717`) for 2030, aggregated to the model's trade regions:

- `bilateral_flows_<year>[_eu2].csv`: per importer, exporter and product the flow (ImportQ) and a, b, a0;
- `bilateral_regions_<year>[_eu2].csv`: market prices (PMRK) and production per region;
- `bilateral_trq_<year>.csv`: the EU's bilateral TRQs (below);
- `armington_rho.csv`: s1 (rho1) and s2 (rho2) per product. CAPRI's defaults are 8 and 10 (`arm/market1.gms`
  l. 108-109; 3 and 5 for biofuels, l. 119-120), overridden by `special_ch/market1_ch.gms` (CEPII; Fontagné,
  Guimbard and Orefice 2019) as CAPRI includes it, e.g. wheat 3.9 / 7.8, beef 3.5 / 7.1, pork 6.7 / 13.4, butter
  2.1 / 4.3, biofuels 2.2 / 4.5, DDGS 1.2 / 2.4. A product missing from the file would take 8 / 10 (code default).

The market year follows the run (`data["market_year"]`, else 2017): a 2030 projection uses CAPRI's 2030 flows, so the
non-EU world is CAPRI's 2030 world.

## Supply and use at regional prices

Supply (`supply_response`, region_ratio given):

- Non-EU regions: CAPRI's market supply function (ProdNQ_, arm/market_model.gms l. 1529-1572; since 29 October 2026,
  `market.noneu_supply_nq`): base production + Σ_y h_xy (r_y − 1), summed over the region's CAPRI regions, with h_xy
  = p_hessNQSupp × PPRI0_y / INPE at CAPRI's 2030 calibration point, the Hessian completed as CAPRI's market model
  completes it (symmetric; tiny terms and products without ProdNQ_ deleted; `tools/lib/_capri_nq.py`), the own and
  cross-price terms over the market products and raw milk (the region's dairy block's price); raw milk's own supply
  function in the dairy block takes its cross-price terms as a shift (`noneu_market_supply_nq.csv`,
  `tools/build/build_noneu_market_supply_nq.py`; KNOWN_ISSUES K54-3). The feed energy price FEDE moves with CAPRI's
  FeedBal_ ([FEED_MARKETS.md](FEED_MARKETS.md), audit M3, since 29 October 2026). Held at the calibration point: the rents of CAPRI's land inputs (TCRP, FRUN, FODFAL: CAPRI's market land use,
  which the model does not have outside the EU; 4.4% of the terms' absolute size). `market.noneu_supply_nq = false`: one own-price constant elasticity per region and
  product, CAPRI's 2017 p_elasSupp (`supply_elas_region.csv`), the form from 20 to 29 October 2026. Crushing, the non-EU dairy blocks and the biofuel markets set their products' supply at
  the regional prices ([OILSEED_CRUSHING.md](OILSEED_CRUSHING.md), [DAIRY_PROCESSING.md](DAIRY_PROCESSING.md),
  [BIOFUEL_MARKET.md](BIOFUEL_MARKET.md)).
- EU: the supply models' output, anticipated against the price the supply models last saw:
  S = S_seen (r / r_seen)^ε (`_eu_price_seen`, set by `model.py`); at a converged point r = r_seen and the
  anticipation vanishes. Other vegetable oils and fish (`EU_MARKET_SUPPLY`: OTHO, FFIS, SFIS, OAQU), which have no
  supply-model activity, respond to the price against base. With `CAPRIModel.market_supply_nq` (off by default) CAPRI's
  market supply function, its Hessian measured on the supply models at the baseline, replaces the anticipation for
  the supply models' products (`model._market_supply_hessian`).
- Norway (`MarketModule.SUP_NONEU_REGIONS`, CAPRI's RMSSUP outside the EU): as the EU, its market supply is its supply
  models' output (country NO of the bridged supply, `_split_supply`), fixed within one market solve and anticipated
  against the prices its models last saw (`_sup_price_seen`) with Norway's own CAPRI elasticity (p_elasSupp of
  NO000000, `supply_elas_region.csv`); products without a supply-model activity in Norway (fish) keep CAPRI's market
  supply function at Norway's price against base (pork did until Norway's regions got CAPRI's pig herds, 21 October
  2026: the switch is per product, by the supply models' output). Its raw milk goes to
  its own dairy block (CAPRI's NO000000 block in `dairy_world_processing.csv`, raw milk delivered from its supply
  models instead of the raw milk supply function: `market_model.gms` ProdNQ_ note 2). With `market_supply_nq` Norway
  has its own Hessian (`model._split_hessian`).
- The supply models of Norway see Norway's prices: `model.py` relaxes Norway's departure from the EU signal
  (`_sup_dev`: its producer price ratios, raw milk its dairy block's) as it does the EU trade blocks', and hands it to
  the supply module as a member-state departure (`price_dev_ms["NO000000"]`), to Norway's feed bulk price indices
  (`feed_bulk_price_ratios`) and to its young-animal market (yaniMarket_ per market region: NOR).

Use (`demand_response`, at the consumer price PA_i): CAPRI's GL food demand on the human-consumption share of use;
feed (EU and Norway: CAPRI's feed bulks following the supply models' herds, [FEED_MARKETS.md](FEED_MARKETS.md),
Norway's from `feed_bulks_no.csv` on CAPRI's feed share of its use; other non-EU regions: p_ElasFeed, which CAPRI
has only outside RMSSUP); processing (ProcNQ_);
crushing; biofuel feedstocks and biofuel use; dairy products; the remaining share of use keeps an own-price response
QD0 (P/P0)^eta.

## Calibration (`_bilateral_calibrate`, `BilateralCommodity.calibrate`)

CAPRI's flows are kept and each region's domestic sales absorb the difference between the model's own production and
CAPRI's (DS0 = S0 − exports; exports are scaled down where they would exceed 98% of production). Share parameters
(beta, dd, dm) are calibrated so that base flows and base prices are reproduced exactly. The demand functions are
then rescaled so that use at the reference prices is exactly the closure's D0. For the pooled product (raw milk)
the demand of the regions without supply models is scaled so that the world clears at base (the EU's and Norway's
raw milk use is their supply models' milk delivered to their own dairies). Norway's base is taken at its supply
models' output as the EU's (`_align_sup_base`; the closure's domestic sales absorb the difference to CAPRI's
flows).

In a baseline run the market is recalibrated at every outer iteration at the current supply, and prices stay at the
reference (CAPRI's reference run is a calibrated equilibrium at its reference prices); the calibration at the
converged baseline supply is frozen and inherited by the scenario (cached with the baseline).

## Tariff-rate quotas

CAPRI's EU bilateral TRQs (`TrqNT` of the EU policy block; `build_trq` → `bilateral_trq_<year>.csv`): per model
exporter the quota, the gap between the out-of-quota (MFN: TAMFN, TSMFN) and the in-quota price, and the share of the
flow under the quota regime. The specific tariff on the flow moves with CAPRI's sigmoid, slope 200 on
(fill − 0.97) (p_trqSigmoidSlope, `arm/market_model.gms` l. 339; `TRQ_SLOPE` in `model_parameters.csv`), relative to the
base fill so that the base is reproduced. Each quota's tariff is solved by bisection consistently with its own flow
at every market step (`trq_solve`); the market solve stops only when the tariffs have stopped moving. Always on (the switch `MarketModule.use_trq` was removed on 27 October
2026).

In CAPRI's 2030 reference (`bilateral_trq_2030.csv`) the EU's meat quotas are far from filled: beef 13 of 157 kt,
poultry 108 of 422 kt from the exporters with bilateral quotas. In the Farm-to-Fork runs of Sprint 8m (October 2026)
they did not bind.

REGISTERED: global (erga omnes) quotas, in-quota specific tariffs other than CAPRI's applied ones, and CAPRI's
augmented-CES commitment terms of the second nest (p_arm2Commit) are not represented.

## Reported prices and the price signal

`MarketEquilibrium.domestic_prices` holds each region's market price (reference × r_i); `world_prices` a world index
per product (the reference world price × the exporters' price ratios weighted by their base exports;
`_bilateral_world_index`); `wedge_prices` the reference domestic price × that index. `eu_premium` (per EU market
region, `eu_premium_reg`) is the EU's price ratio over the world index; `model.py` forms the farmers' price signal as
world ratio × premium, i.e. the EU market price ratio. "Premium" is only this bookkeeping; no premium is solved.

## Differences from CAPRI

- EU market regions: one region by default (CAPRI's member states inside its trade blocks are available as
  `eu_blocks`); member states are not market regions (raw milk, fat and protein are priced per member state in the
  dairy block, young animals per EU market region).
- Non-EU supply: CAPRI's market supply functions at its 2030 calibration point, with the feed energy price of CAPRI's
  FeedBal_ (M3) and the land rents held; for the UK, Turkey and the Western Balkans CAPRI has supply models (RMSSUP) and recalibrates the
  function to them every iteration, the model has none there, so the function stays at the calibration point.
- EU market supply between iterations: CAPRI's market supply elasticities as given; CAPRI recalibrates its supply
  approximation to the supply models (available as `market_supply_nq`, off).
- No p_arm2Commit, no global TRQs (above).
- Solver: Newton per product with Anderson acceleration instead of CONOPT ([MARKET_SOLVE_CHECK.md](MARKET_SOLVE_CHECK.md)).

## Before the bilateral market (historical)

Until Sprint 8m (October 2026) the market had one world price per commodity, each region's price was world price ×
(1 + tariff), and the EU alone had an Armington premium cleared on its gross extra-EU trade. That structure was
removed from the code on 20 October 2026 (no run path used it; KNOWN_ISSUES K54-2). Its development and the results of that period (including the fixes to the
reported EU price and to the demand reference price) are recorded in CHANGELOG.md (sections up to "Sprint 8m") and
`docs/archive/MARKET_STRUCTURE_PLAN.md`. Current results: README section 9 (Validation).
