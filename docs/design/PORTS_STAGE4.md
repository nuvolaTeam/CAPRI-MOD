# Ports, stage 4: CAPRI's bilateral tariff-rate quotas on its market regions (4 November 2026)

Stage 4 of MARKET_REGIONS_INVENTORY §5 and MODEL_CONTENT_PLAN §2: CAPRI's bilateral TRQs for every importer with
quotas, on CAPRI's policy blocks (RMTP), with the ad valorem and specific tariffs switching between the preferential
and the MFN rate as CAPRI's sigmoid moves. Removes DEP-34 (the EU's TRQs only), DEP-35 (TRQs summed per model
exporter), DEP-36 (the quota's price gap frozen at the base FOB) and DEP-41 (EU quotas against MER). Written in the
current market code (capri_mod/market/bilateral.py), in CAPRI's form, so G3 can take the same expressions (the open
question of MODEL_CONTENT_PLAN §2, decided this way by Claude under the project lead's mandate of 3 November 2026 to go
on without asking where nothing is irreversible).

## CAPRI's equations (gams/arm/market_model.gms)

- impPrice_ (l. 2849-2909): p_ij = [Pmrk_j + TC_ij] (1 + tarAdVal(RMTP_i, RMTP_j)/100) + tarSpec(RMTP_i, RMTP_j)
  (or the flexible levy where a minimum border price exists: stage 6) + border carbon adjustment; no tariff between
  the market regions of one policy block (same_pblock; the EU's two blocks), none under p_doubleZero.
- TradeFlowsAgg_ (l. 3106): the quota's fill is the sum of the flows between the two policy blocks' market regions.
- trqSigmoidFunc_ (l. 3275): sigma = Sigmoid(p_trqSigmoidSlope / TrqNT x (flows - 0.97 TrqNT)).
- tarSpec_ (l. 3292), tarAdval_ (l. 3417), bilateral quota without a global one:
  tarSpec = TsPref + (TsMFN - TsPref) sigma; tarAdVal = TaPref + (TaMFN - TaPref) sigma. With a global TRQ too, the
  smaller of the two (ncpcm, smoothed min): stage 5.
- Quotas apply where TrqNT > eps, not 1E+10 (free access) and not "prohibitive".

## Data (CAPRI's 2030 calibrated market, sim_ini_21730)

p_trqBilat(RMTP, RMTP1, product, item, "CUR"): 130 quotas with a finite TrqNT: EU 81, MOR 16, TUR 15, MED 11,
NO000000 5, RUS 2 (capri_sources/reference/simini/simini_21730/p_trqBilat.csv.gz). p_trqSigmoidSlope per RMTP and
product. Market region -> policy block: capri_data/codes/capri/RM_TO_RMTP.csv (MER = ARG, BRA, URUPAR; EU =
A_EU_WEST, A_EU_EAST; the rest one to one).

## In the model

1. Builder tools/build/build_bilateral_trq.py (replaces build_bilateral_market's EU-only build_trq): every quota of
   p_trqBilat "CUR" with its rates and slope, keyed by importer and exporter policy block and model commodity:
   capri_data/baselines/capri_greendeal_ref/1730/market/bilateral_trq_2030.csv.
2. BilateralCommodity: per flow its ad valorem and specific parts at the base (TaAppl, ImportP - (Fob + TC)(1 + ta));
   per quota the flows it covers (importer rows in RMTP_i, exporter columns in RMTP_j). The import price of a flow
   under a quota: (Pd0_j r_j + TC_ij)(1 + tav(sigma)/100) + ts(sigma), sigma from the quota's fill at the current
   flows. Where the base rates differ from CAPRI's sigma at the base fill (data rounding), the difference is kept
   as a fixed part so the base import price is CAPRI's p_impPrice "CAL" (checked; any gap reported).
3. The fixed point: as trq_solve today (bisection on each quota with the flows' local response), now per policy-block
   pair and on the rates.

## Checks

- At the base: every pair's import price against p_impPrice "CAL"; every quota's sigma at the base fill against
  CAPRI's v_trqSigmoidFunc where stored, its fill against p_trqBilat ImportsR (tools/check/check_market_base.py).
- Equation-level unit tests: tav and ts against hand-computed values from market_model.gms l. 3275-3475, with fills in
  [0.9, 1.05] where the slope-200 sigmoid is steep (G_REVIEW Q5.2 test C).
- Mini-EU run with its deviation from CAPRI's Farm-to-Fork figures.

## Findings, 4 November 2026 (before the code)

- The 130 quotas of p_trqBilat "CUR" in the market dump equal sim_ini's to 1e-13 (TrqNT and the four rates).
- Against CAPRI's own calibrated state (p_trqBilat TaAppl, TsAppl "CAL", ImportsR "CAL"): 119 of 130 quotas have
  TaAppl = TaPref + (TaMFN - TaPref) Sigmoid(200 (ImportsR / TrqNT - 0.97)) within 0.5 points and the specific rate
  within 1 EUR/t. The 11 others are explained by the two regimes below: 7 where the importer has a global quota too
  (CAPRI's rate is the smaller of the two, ncpcm: Norway's beef from the EU, 12.7% instead of 222.5%; the EU's pork,
  sheep meat, butter), 4 under the entry price system (the EU's tomatoes and citrus from MOR and MED: TaAppl fixed at
  TARV, set_tariffs.gms l. 249).
- The market dump's per-pair TaAppl (dataOut) is not the quota's rate: for TUR <- EU it is 0 with the protection in
  the specific part; the import price itself (a + b) is CAPRI's p_impPrice "CAL" in every case checked.
- sim_ini holds no levels of v_tarAdVal, v_tarSpec, v_trqSigmoidFunc, v_tradeFlows (0 records: written before the
  market solve); the calibrated rates are p_trqBilat's TaAppl/TsAppl "CAL".
- Regimes per quota (bilateral_trq_2030.csv `regime`): bilateral 50, with_global 76, entry_price 4. So stage 5 (global
  quotas, TRQImports_, tarAdValW_, tarSpecW_, the ncpcm minimum) is written with stage 4: alone, stage 4 would move only
  50 quotas. The entry price quotas stay at their base tariffs until stage 6.

## Global quotas (stage 5, with stage 4)

- TRQImports_ (l. 3142): imports under the global quota = flows from exporter blocks without a bilateral quota +
  the overfill of the bilateral ones, -ncpcm(-(flow - TrqNT_b), 0, 1E-3 TrqNT_b) (a smoothed max(0, .)); pairs under
  p_doubleZero (free trade) excluded.
- tarAdValW_, tarSpecW_ (l. 3399, 3475): the global rates from the global sigmoid on TRQImports.
- Flows from exporters without a bilateral quota pay the global rates; flows under a bilateral quota pay
  ncpcm(global rate, bilateral rate, max(1E-2, 1E-3 |TaMFN - TaPref|)) (ad valorem; specific: max(1E-5, 1E-7 |.|)).
  ncpcm(x, y, Z) = x - Z ln(1 + exp((x - y) / Z)) (GAMS's Chen-Mangasarian smoothed minimum).
- In the model the base import prices stay CAPRI's (a + b); each regime adds the change of its rates from their value
  at the base flows (shift form), so the base is reproduced exactly and the response is CAPRI's equations'.

## Stage 6: entry prices and flexible levies (4 November 2026)

- Data (build_border_measures, from sim_ini_21730 "CUR"): the entry price system of the EU and the UK (APPL, CITR,
  TAGR, TOMA; DATA TriggerP), the EU's flexible levies (BARL, CORN, OATS, OCER, PARI, RYEM, SUGR, SWHE; DATA MinBordP),
  147 entry price pairs (p_entryPriceFac, 100 for all; PrefTrigPrice where the pair has one: the 4 entry price quotas,
  and MOR's table grapes with an unlimited preference). policy_blocks.csv: each market region's policy block.
- Model (BilateralCommodity.border_spec, inside import_prices): the measure replaces the flow's specific tariff;
  CAPRI's equations per pair of policy blocks, at the pair's CIF price weighted by its base flows (TransportCostsAgg_);
  the entry price under a quota moves with the quota's sigma (prefTriggerPrice_); the levy is cut at the flow's specific
  tariff, the quota's current rate where the flow has one (FlexLevy_ with v_tarSpec). The change from the base enters
  the import price, so the base is CAPRI's.
- Check against CAPRI's calibrated levies (p_flexLevy "CAL", 48 EU flows): largest gap 1.3 EUR/t (RSA sugar, 70 EUR/t).
- REGISTERED: the 2017 market year has no entry prices nor levies (p_entryPriceFac is only in the 2030 restart file).
  G1/G2a's CasADi systems have neither; the default solve's exact path is not taken for such a commodity.

## Stage 7: the market land block outside the EU (4 November 2026)

CAPRI's equations (gams/arm/market_model.gms, supremaMrk on, as capmod/set_global_variables.gms l. 386 sets it):

- ProdNQ_ (l. 1529-1572) has rows for the land types of the market (xx1Land: TCRP temporary crops, FODFAL fodder and
  fallow, FRUN fruit and nurseries), their land demand; arm/market1.gms l. 593 turns the sign of these rows after
  making the Hessian symmetric (they were netputs in the elasticity calibration). The products' rows have terms in the
  three rents. The land's price in ProdNQ_ is v_prodPrice - PSEd.
- LandSupplyMNL_ (l. 1737): v_land(l) = (ARTO - INLW) exp(aLU_l + sum_k bLu_lk rent_k) / sum_m exp(...), six land
  types (FORE, ARTIF, OLND fixed rents; the three agricultural ones free). In a simulation (not BASELINE) CAPRI uses
  the asymmetric form NumeraireLand_ / LandSupplyRatio_: the same function where no LEVL_1 commitment area is given
  (none in DATA; p_useSymmetricMNL has no records in sim_ini_21730). v_aLU is fixed at p_aLU "CUR"
  (capmod/set_start_val.gms l. 236).
- LndSupplyEqualsDemand_ (l. 1698): v_land = v_prodQuant(land); rentFromProdpriceLand_ (l. 1707): rent = producer
  price + PSEd (PSEd of the land types, else of LAND: arm/prep_market.gms l. 134; Switzerland 1116.43 EUR/ha).
- Yield_, LandAgrFromYld_, ScaleLandAgr_ (l. 1795-1860) split the land into crop areas and yields; they do not feed
  back on quantities or prices (registered as not reported: the model's non-EU crop areas and yields).

Data (tools/build/build_noneu_market_supply_nq.py, build_land_market): noneu_land_market.csv (45 CAPRI regions, 134
free rents), noneu_land_mnl.csv (p_bLu), and the land rows and rent columns in noneu_market_supply_nq.csv. Checks in
the builder: the land rows give CAPRI's p_elasSupp (with all other terms, worst 1.35e-14), the MNL at v_rentPerHa
gives v_land (4.7e-10), the agricultural land equals PROD at CAL (4e-15), the rents PPRI + PSEd at CAL (4e-15).

Model (capri_mod/market/supply.py, `noneu_land_solve`; setting market.noneu_land_market): per CAPRI region the three
rents solve MNL supply = ProdNQ_ land demand by Newton's method at the evaluation's prices, raw milk prices (the
latest dairy blocks') and FEDE; the land solve and FeedBal_ (noneu_fede, whose animal output now moves with the rents)
are solved in turn until both settle. The products' and raw milk's supply then add their terms in the rents. Regions
with supply models in CAPRI (Norway, the UK, Turkey, the Western Balkans) have no land market (v_prodQuant(land) fixed),
as in CAPRI.

Checks: tools/check/check_market_base.py (land on: largest change against land off 3.5e-10 of a production, CHN, from
the MNL data's rounding); unit test test_noneu_land_market_is_capris (the base rents, a 10% crop price rise in the
United States against the MNL and ProdNQ_ written out from the files). Registered: DEP-43 (the welfare report has no
land cost or land owner surplus yet).
