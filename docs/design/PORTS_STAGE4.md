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
