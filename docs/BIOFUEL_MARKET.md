# Endogenous biofuel markets (CAPRI `BIOF_M`)

Status: revised 20 October 2026 against the code. On by default, as star 3.0's GUI sets "Endogenous bio-fuel markets"
(`BIOF_M`) to true. Run results of Sprints 9c and 9d (October 2026) are no longer current and are left to
CHANGELOG.md; current results: README section 9 (Validation).

Switches: `CAPRIModel.biofuel_markets` (True), `PolicyScenario.biofuel_markets`, `CAPRIModel.run(biofuel_markets=)`,
`run_f2f_2030.py --no-biofuel-markets`; the setting holds for the scenario and its baseline.
`MarketModule.biofuel_endogenous()` is true when the switch is on, the market is the bilateral one, both biofuels
are market commodities and the data are present.

## What CAPRI does

`arm/prep_market.gms` sets `p_endoBioMarket = 1` when `BIOF_M = ON` (l. 24-25). Bio-ethanol (BIOE) and bio-diesel
(BIOD) are then market products of `arm/market_model.gms` like any other: produced per market region (RMS) from
feedstocks, used per region against fossil fuel, traded bilaterally with Armington (`special_ch/market1_ch.gms`
l. 36-40: rho1 2.2, rho2 4.5). Without `BIOF_M`, `arm/fix_biofuel_market_vars.gms` fixes biofuel output, prices,
use and trade flows, and only the feedstock mix responds.

| Equation | CAPRI | capri-mod (`MarketModule.biofuel_state`, `_biofuel_feed_group`) |
|---|---|---|
| `biofFeedCost_` | per t of feedstock: Arm1 price − PRCBY × by-product price | same; DDGS at its market price, glycerine fixed at 600 EUR/t as in CAPRI (`arm/store_prices.gms` l. 45) |
| `biofFeedCostAgg_` | CES aggregate of the feedstock costs, p_rhoBioFuel 4 (`arm/market1.gms` l. 68) | same |
| `biofPriceRel_` | PR = producer price / aggregate feedstock cost | same; the producer price moves with the region's market price (multiplicative margin, `PPri_`) |
| `SupplyBiof_` | X = scale·PR + exp(alfa + beta·log(PR + 0.01))·SIGMOID(slope·(PR − turn)) | same, per CAPRI market region |
| `MaprBiof_` | output = X + NAGR + SECG + EXOG | same; non-agricultural, second-generation and exogenous output fixed |
| `Biof_`, `prodBiof_` | feedstock CES at output X; the numeraire feedstock closes output = Σ feedstock × PRCB | same, in every region |
| `prodQuantBiofBy_` | DDGS output = Σ cereal feedstock × PRCBY | same |
| `Cpri_` | consumer price = Arm1 price + CTAX + CMrg − CSE | same (additive tax and margin) |
| `biofDemShare_` | share = QUTS + MAX·SIGMOID(Slope·(consumer price / fossil price − Turn)) | same |
| `biofDem_` | BIOF = share × fossil-equivalent fuel use / oil equivalent of the biofuel | same; total fuel use and fossil prices fixed |
| `ProcNQ_` (non-fuel processing of ethanol) | PROC = PROC0 − hess × Δ Arm1 price / INPE, own term only | same (INPE 1.277; about −0.04 elasticity) |

## Calibration and data

As `biofuel/def_biofuel_params.gms` calibrates, at CAPRI's 2030 Green Deal reference (`tools/build/build_biofuel_market.py`
→ `biofuel_market.csv`, 130 region-biofuel rows; `biofuel_feedstock.csv`, `biofuel_use_share.csv`):

- Supply: turn = 0.9·PR0 (l. 344); slope 8/PR0 for the countries with a supply model (EU, UK, Norway, Western
  Balkans, Turkey), 5/PR0 elsewhere, below 50 kt and for German biodiesel, 1/PR0 for Japanese ethanol; beta = 0.5
  (l. 370); scale = min(0.1, 0.1·X0/PR0); alfa so that X(PR0) = X0. 97 supply functions.
- Demand: observed share = BIOF·oilEqu_b / (HCON·oilEqu_f); the share above the mandate QUTS has a ceiling
  MAX = min(1, max(0.02 + share − QUTS, 1.1·(share − QUTS))) (Brazilian ethanol: 1 − QUTS) and reaches 90% of it at a
  price relation of min(0.5, 0.5·PriceRel) (biodiesel: min(0.3, 0.3·PriceRel)). 128 demand functions. CAPRI's HCON
  is total fuel (fossil + biofuel in fossil equivalents); the dump's HCOM of gasoline and diesel is the fossil part.
  This reproduces CAPRI's `data_market_1730defaulta` HCON and its HCOS share (Germany 11.33%) and gives
  QUTS = 0.9 × observed share in the member states, as `def_biofuel_params.gms` sets it.
- Data (`markmarket_greendeal_1730et_base_1717`, every CAPRI market region): PROD, NAGR, SECG, EXOG, BIOF, PPRI,
  CPRI, ARM1P, QUTS, BiofFeedCost; gasoline and diesel HCOM and CPRI.

Builder checks: the aggregate feedstock cost reproduces CAPRI's `BiofFeedCost` in every region; output,
first-generation output and use at the reference prices are CAPRI's; production = Σ feedstock × PRCB + NAGR + SECG +
EXOG holds in all CAPRI market regions.

EU 2030 reference (`biofuel_market.csv`): bio-ethanol 6,904 kt produced (first generation 4,599), bio-diesel 19,063 kt
(first generation 9,074).

## In the market

- BIOE, BIOD and DDGS are market commodities traded in the bilateral market with CAPRI's 2030 flows
  (`tools/build/build_bilateral_market.py`); world prices FAO_agg World PMRK (747, 952 and 120 EUR/t); DDGS rho1 1.2,
  rho2 2.4 (`special_ch/market1_ch.gms` l. 66-67).
- Each model trade region's output and use are the sums over its CAPRI market regions (EU27: the member states of
  CAPRI's trade block EU27yr19, or each EU trade block with `eu_blocks`; non-EU regions by `REGION_MAP`; the rest ROW),
  cleared at the region's market price.
- Feedstock use for biofuels follows the CES at the endogenous output in every region. In the EU the biofuel part of
  each feedstock's use is CAPRI's 2030 biofuel share of EU use (`biofuel_use_share.csv`: rapeseed oil 52%, palm oil
  29%, soybean oil 23%, sugar 12%, sunflower oil 12%, wine 10%, cereals 2.5-9%); the rest of the row keeps its own
  response. Non-EU: the region's use holds CAPRI's feedstock quantity, which moves with the CES.
- DDGS: output from the ethanol plants' cereal feedstocks (reproduces CAPRI's 2030 DDGS output); its market price
  enters the ethanol plants' feedstock cost, so DDGS revenue feeds back into ethanol supply. DDGS stays a market
  product with the biofuel markets off, as in CAPRI (only BIOE and BIOD leave the market without `BIOF_M`). As feed:
  EU through CAPRI's FPRO bulk ([FEED_MARKETS.md](FEED_MARKETS.md)); non-EU with CAPRI's p_ElasFeed
  (`feed_demand_nonEU.json`, `tools/build/build_feed_demand_nonEU.py`, CAPRI's 2030 calibration; e.g. USA own −1.12, to
  soybean cake +1.19); regions without a CAPRI feed function keep the generic own-price response (armington eta,
  −2.14 for DDGS; KNOWN_ISSUES K43, K44).
- Mandates are a scenario shock as in CAPRI's `scen/bio_fuels/change_biof_mandate.gms`: `PolicyScenario.biofuel_mandate`
  (`run_f2f_2030.py --biofuel-mandate`) multiplies the QUTS of the EU member states and the UK.
- With the markets off, biofuel output and use stay at the reference (first generation × `biofuel_output_scale`, set
  through `run(biofuel_output_scale=...)`), only the feedstock mix and DDGS respond, and the bilateral system clears
  at the reference price.

Results: `results["market"].biofuel` (EU feedstock use, DDGS, output, use and price ratios per region, the member
states' first-generation output and processing margin); `results["biofuel"]` with `run_biofuel=True`.

## Not modelled (REGISTERED)

- Fossil fuel prices and total fuel use are fixed, as in CAPRI (exogenous data).
- The functions are calibrated at CAPRI's 2030 reference; a 2017 market uses them too.
- Norway's feed bulks are not split (the bulk table covers the EU member states; Norway's supply models feed the EU
  market, while CAPRI treats Norway as its own market region).
