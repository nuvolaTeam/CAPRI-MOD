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
   capri_data/2017/market/bilateral_trq_2030.csv.
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
