# Endogenous biofuel markets (CAPRI `BIOF_M`)

Status (October 2026, Sprint 9c): **done, default** (star 3.0's GUI sets "Endogenous bio-fuel markets", `BIOF_M`,
to true). A scenario setting: `PolicyScenario.biofuel_markets`, `CAPRIModel.run(biofuel_markets=)`,
`run_f2f_2030.py --no-biofuel-markets`; it holds for the scenario and its baseline.

## What CAPRI does

`arm/prep_market.gms` sets `p_endoBioMarket = 1` when `BIOF_M = ON`. Bio-ethanol (BIOE) and bio-diesel (BIOD) are
then market products of `arm/market_model.gms` like any other: produced per market region (RMS) from feedstocks in
the market, used per region against fossil fuel, traded bilaterally with Armington (`special_ch/market1_ch.gms`:
rho1 2.2, rho2 4.5). Without `BIOF_M`, `arm/fix_biofuel_market_vars.gms` fixes biofuel output and prices and only
the feedstock mix responds (what capri-mod did since crushing stage 4, docs/OILSEED_CRUSHING.md).

| Equation | CAPRI | capri-mod (`MarketModule.biofuel_state`) |
|---|---|---|
| `biofFeedCost_` | per t of feedstock: Arm1 price − PRCBY × by-product price | same (DDGS and glycerine at the 2030 reference) |
| `biofFeedCostAgg_` | CES aggregate of the feedstock costs, rho 4 | same |
| `biofPriceRel_` | PR = producer price / aggregate feedstock cost | same; producer price moves with the region's market price (multiplicative margin, `PPri_`) |
| `SupplyBiof_` | X = scale·PR + exp(alfa + beta·log(PR + 0.01))·SIGMOID(slope·(PR − turn)) | same, per CAPRI market region |
| `MaprBiof_` | output = X + NAGR + SECG + EXOG | same; non-agricultural, second-generation and exogenous output fixed |
| `Biof_`, `prodBiof_` | feedstock CES at output X | same, in every region (non-EU feedstock use now follows it too) |
| `Cpri_` | consumer price = Arm1 price + CTAX + CMrg − CSE | same (additive tax and margin) |
| `biofDemShare_` | share = QUTS + MAX·SIGMOID(Slope·(consumer price / fossil price − Turn)) | same |
| `biofDem_` | BIOF = share / oilEqu_b × fossil fuel use (oil equivalents) | same; total fuel use and fossil prices fixed |

Calibration as `biofuel/def_biofuel_params.gms` does it, at CAPRI's 2030 Green Deal reference
(`tools/build_biofuel_market.py`, `capri_data/2017/market/biofuel_market.csv`):

- **Supply**: turn = 0.9·PR0; slope = 8/PR0 for the countries with a supply model (RMSSUP = NUTS0: EU, UK, Norway,
  Western Balkans, Turkey), 5/PR0 elsewhere, below 50 kt and for German biodiesel, 1/PR0 for Japanese ethanol;
  beta = 0.5; scale = min(0.1, 0.1·X0/PR0); alfa so that X(PR0) = X0.
- **Demand**: observed share = BIOF·oilEqu_b / (HCON·oilEqu_f); the share above the mandate QUTS has a ceiling
  MAX = min(1, max(0.02 + share − QUTS, 1.1·(share − QUTS))) (Brazilian ethanol: 1 − QUTS), and reaches 90% of it
  at a price relation of min(0.5, 0.5·PriceRel) (biodiesel: min(0.3, 0.3·PriceRel)).
- **Data** (`markmarket_greendeal_1730et_base_1717`, every CAPRI market region): PROD, NAGR, SECG, EXOG, BIOF,
  PPRI, CPRI, ARM1P, QUTS, BiofFeedCost; gasoline and diesel HCOM and CPRI. The dump's HCOM of gasoline and
  diesel is the fossil part; CAPRI's HCON is total fuel (fossil + biofuel in fossil equivalents), which
  reproduces CAPRI's own `data_market_1730defaulta` HCON (CAL) and its HCOS share (Germany 11.33%), and gives
  QUTS = 0.9 × observed share in the member states, as `def_biofuel_params.gms` sets it.

Checks: the aggregate feedstock cost reproduces CAPRI's `BiofFeedCost` in every region; output, first-generation
output and use at the reference prices are CAPRI's in every region (130 region-biofuel rows; 97 supply functions,
128 demand functions); production = Σ feedstock × PRCB + NAGR + SECG + EXOG holds in all CAPRI market regions.

## In the model

- `BIOE` and `BIOD` are market commodities (`definitions.MARKET_COMMODITIES`, 37), traded in the bilateral market
  with CAPRI's 2030 flows (`tools/build_bilateral_market.py`), world prices FAO_agg World PMRK (747 and 952 EUR/t).
- Each model trade region's output and use are the sums over its CAPRI market regions (EU27 = the 26 member-state
  codes, CAPRI's trade block EU27yr19; the CAPRI regions of `REGION_MAP` by name; the rest ROW), cleared at the
  region's market price, as CAPRI clears the member states at the EU27yr19 price.
- Feedstock use for biofuels follows the endogenous output in every region (EU as before through CAPRI's EU
  biofuel share of use; non-EU on CAPRI's quantity).
- With the switch off, biofuel output and use stay at the reference (first generation × `biofuel_output_scale`),
  and the bilateral system clears at the reference price.

## Effect

Farm-to-Fork 2030 (s57, endogenous; s58, switched off):

| | baseline → Farm-to-Fork |
|---|---|
| EU bio-ethanol output | 6,904 → 6,605 kt (−4.3%); first generation 4,599 → 4,300 |
| EU bio-diesel output | 19,063 → 18,806 kt (−1.4%); first generation 9,074 → 8,818 |
| EU biofuel use | ethanol −2.8%, diesel −0.5% |
| EU biofuel prices | ethanol +8.6%, diesel +2.2% |
| EU feedstock use for biofuels | other cereals −24%, wine −24%, sunflower oil −10%, sugar −7%, barley −7%, rapeseed oil −7%, wheat −2% |

Dearer feedstocks cut the processing margin, so first-generation output falls and imports and second-generation
output fill part of the use; less feedstock goes to biofuels.

| Farm-to-Fork, % change | markets off (s58) | markets on (s57) | CAPRI (JRC121368) |
|---|---|---|---|
| Cereal / oilseed price | +7.9 / +15.9 | +7.7 / +15.7 | +8 / +11 |
| Cereal / oilseed production | −15.5 / −14.0 | −15.6 / −14.1 | −15 / −15.5 |
| Herds, nitrogen, emissions | | unchanged within 0.2 points | |
| 20-indicator gap | 3.29 | 3.32 | |

With the markets off, biofuel output, use and prices stay exactly at the reference and the results equal the
previous model's (s56) within 0.1 point (the non-EU feedstock CES is the only difference). With them on, biofuel
demand for feedstocks gives way when feedstocks get dearer, which damps cereal and oilseed prices slightly.

Baseline reproduction (`tools/compare_baseline_capri.py`, now with BIOE and BIOD): EU biofuel output and use
within 0.1% of CAPRI's 2030 reference; production median deviation 3.8 → 3.5%, domestic use 4.8 → 4.1%.

## Closing the loop (Sprint 9d): DDGS, feed bulks, processing, mandates

The biofuel block now closes the way CAPRI's does.

- **DDGS** is a market commodity (38 in total): output = Σ cereal feedstock × PRCBY in every CAPRI market region
  (`prodQuantBiofBy_`; reproduces CAPRI's 2030 DDGS output exactly, 72.3 Mt, every region within 0.00%), traded
  with CAPRI's 2030 flows (`special_ch/market1_ch.gms` rho1 1.2, rho2 2.4), world price FAO_agg World PMRK
  (120 EUR/t). Its producer price enters the ethanol plants' feedstock cost (`biofFeedCost_`: Arm1 price −
  PRCBY × DDGS producer price), so DDGS revenue feeds back into ethanol supply. Glycerine stays at 600 EUR/t, fixed
  in CAPRI itself (`arm/store_prices.gms`). DDGS stays a market product with the biofuel markets switched off, as
  in CAPRI (only BIOE and BIOD leave the market without `BIOF_M`).
- **DDGS as feed, EU: CAPRI's feed bulks** (`feedBlkPrice_`, `feedShareEqu_`; `tools/build_feed_bulks.py`,
  `market/feed_bulks_eu.csv`). The supply models demand bulks; per member state the market splits cereals (FCER:
  wheat, rye, barley, oats, maize, other cereals, rice) and protein-rich feed (FPRO: pulses, oils, cakes, DDGS,
  milling by-products, fish meals) into products with a CES on their Arm1 prices, rho 6 (`arm/market1.gms`
  p_rhoFeed for the member states). The bulk follows the member state's herds and rations; the bulk price index
  goes back to the rations (and to the per-head feed costs when rations are off). This replaces the model's single
  EU cereal index and single cake index with fixed weights: wheat, maize and barley, and soybean, rapeseed and
  sunflower cake and DDGS now substitute within their bulk, member state by member state, as in CAPRI.
- **DDGS as feed, non-EU**: CAPRI's feed elasticities p_ElasFeed for DDGS (own and cross, e.g. USA −1.40 own,
  +1.68 to soybean cake, maize +0.12 to DDGS) in `feed_demand_nonEU.json`, now built by
  `tools/build_feed_demand_nonEU.py` (reproduces the earlier file exactly and adds DDGS; Ethiopia, left out
  before, gets CAPRI's elasticities). Regions without a CAPRI row use the mean own-price elasticity of the CAPRI
  regions without one (−2.42).
- **Non-fuel ethanol processing** follows CAPRI's `ProcNQ_`: PROC = PROC0 − hess × ΔArm1 price / INPE with
  CAPRI's own-price Hessian (`p_hessNQProc`, only own terms in CAPRI; INPE 1.277), about −0.04 elasticity.
- **Mandates** are a scenario shock as in CAPRI's `scen/bio_fuels/change_biof_mandate.gms`:
  `PolicyScenario.biofuel_mandate` (and `run_f2f_2030.py --biofuel-mandate`) multiplies the EU member states' and
  the UK's QUTS; with the markets off, `biofuel_output_scale` sets output instead.

**Effect** (Farm-to-Fork 2030, s59 against s57): 20-indicator gap 3.32 → 3.31; beef, pork and poultry prices
+0.6, +0.4, +0.6 points (toward CAPRI's), beef animals −0.5, beef production −0.4 points; EU DDGS output −6.8%
with the ethanol plants, its use −7.1% with the herds, its price −3.8%; EU ethanol −4.4%, biodiesel −1.1%; barley
for ethanol −12% (DDGS revenue falls, the cereal feedstocks' net cost rises). Baseline reproduction: EU DDGS output
−1.4%, use +2.3% against CAPRI's 2030 reference; domestic-use median deviation 4.1 → 3.7%.

## Not modelled (REGISTERED)

- **Feed bulks without a model market**: milling by-products (FPRI), fish meals, other oils and cakes keep their
  2030-reference prices inside the FPRO bulk.
- **Fossil fuel prices and use** are fixed, as in CAPRI (exogenous data).
- **Norway's** feed bulks are not split (CAPRI treats Norway as its own market region outside the EU block; the
  model's EU market covers EU27).
- The functions are calibrated at CAPRI's 2030 reference; a 2017 market uses them too (as the feedstock CES did).
