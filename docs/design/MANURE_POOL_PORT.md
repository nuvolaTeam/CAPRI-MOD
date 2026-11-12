# CAPRI's manure pool market (m_mPoolMarket): the port (DEP-17)

Status: ported 11 November 2026 as `outer_loop.manure_pool_form = "capri"` (the project lead: "proceed with the fix");
inputs received the same day (priFertDist_<MS>1730defaulta.gdx, 26 EU files, NO000000 and the 8 non-EU; in the raw dataset
since 11 November 2026). The default since 12 November 2026, with CAPRI's price averaging (manure_pool_price_update "capri"),
after the checks of step 4.

## Why

capri-mod clears the manure pools on the regions' exact trade schedules (capri_mod/coupling/manure.py `_clear_pool`,
form "schedules": thresholds from the regional NLP's reduced costs, a Broyden-type response factor, a Takayama-Judge
primal). CAPRI solves its own pool market, m_mPoolMarket, on linear regional excess-supply functions and sends back the
averaged duals. With CAPRI's averaging on the schedules the regional responses kept swinging (full-EU Green Deal 2030
not converged after 36 iterations); with the damped step it converges in 16 (default since 11 November 2026, a
departure until this port).

## CAPRI's model, per nutrient FOUT (MANN, MANP, MANK)

Calibration (manuremarket/declare_manure_market.gms l. 466-510), once:
  b_r = p_manPointSupElas x supply_r / dual_r          p_manPointSupElas = 0.01 (l. 496)
  supply_r = sum over FNUT of FOUT, NGRP: p_priFertDist(r, "postMode", "excr", FNUT, NGRP, SIMY)
  dual_r   = p_dualValueManureCal(r, FOUT) = ManureNPK_.M (supply/define_manure_trade_costs.gms l. 140-146)
Each step (simu_manure_market.gms l. 34-89):
  p_r  = PSHW = ManureNPK_.M of the region's supply model; where it is EPS the fall-back (the previous step's UVAG,
         else dual_r); where it is at or below 1e-6, the step-weighted average
  ES_r = v_netPutQuant(r, FOUT): the region's net manure export
  a_r  = ES_r - b_r p_r
m_mPoolMarket (declare_manure_market.gms l. 99-204), maximise
  sum_r [ a_r/b_r (e_r - i_r) - (e_r - i_r)^2 / (2 b_r) - e_r (cs0_r + cs1_r e_r / 2) - i_r (cb0_r + cb1_r i_r / 2) ]
  - sum_kl T_kl c_kl - sum_k ES_k PriceCal_k
subject to, per pool k: sum_l (T_kl - T_lk) = sum_{r in k} (e_r - i_r) - X3_k (third-country exports, fixed)
  cs0, cs1, cb0, cb1: p_manureSellCostConst/Slope, p_manureBuyCostConst/Slope (the supply model's);
  c_kl: p_mPoolTradeCost (EUR per t: 0.23 EUR per t and km plus 1 EUR per t loading, the pools' centre distances) plus
  p_mTradeAddCost on unused links (the isolated pools of the Green Deal group: UK, CY, MT, NO, TUR and the Western
  Balkans, about 15,000-24,000 EUR per t, in effect closed); T_kl fixed at 0 where c_kl is 0 and on the diagonal;
  PriceCal_k: the calibration wedges (m_mPoolMarketCal, an MPEC with a complementarity penalty).
Price sent back (l. 214-226): the dual of e_mPoolExcessSupply (PMRK), then the weighted average over the last steps with
CAPRI's step weights (capmod/define_stepWeights.gms) = outer_loop.manure_pool_price_update "capri".

## Units (settled 11 November 2026, CAPRI's code and its listing capmod_1.lst of the same day)

- CAPRI's supply model keeps manure trade in kt: v_manureExports, v_manureImports "1000 t pure nutrient"
  (supply/def_supply_model_par.gms l. 501), e_netMTrade "the unit is 1000 tons"; v_ManureNPK in 1000 t, fertDistExcr_
  sum of v_fertDist (t) = v_ManureNPK x 1000; v_manExportOrAppl carries x 0.001. The trade cost slope
  50 / (GROF / 100), GROF in kt (supply/define_manure_trade_costs.gms l. 59-67): Denmark 13.76 EUR per t per kt.
  capri-mod's regional slope (supply.manure_pool_slope / (man0 / 100), man0 in t, 1.376e-5 EUR 1000 per t per t)
  equals it. At calibration NL120000 exports 16.0 kt N (27% of its excretion), ES240000 36.3 kt.
- CAPRI's pool model computes b with the supply from p_priFertDist, in t (v_fertDist), and uses it with the trade in kt
  and prices in EUR per t: its regional excess supply responds 1000 times more than the elasticity 0.01 written in its
  comments. outer_loop.manure_pool_es_slope "capri_code" (default) reproduces CAPRI's numbers; "capri_doc" takes the
  elasticity as written. The question is with the project lead.
- The model's money is 2017's (K108): the regional NLP's manure values are CAPRI's duals over the deflator 1.2772
  (measured: P and K exactly 0.783 of CAPRI's calibration duals, N 0.78-0.94 at the start of the Green Deal run), and
  the builder converts b and the dual: es_slope = slope_capri x 1000 x 1000 x deflator (t per EUR 1000 per t).

## Port (capri_mod/coupling/manure.py `_clear_pool_capri`)

1. Builder tools/build/build_manure_pool_market.py: supply_t, dual_cal_eur_t, CAPRI's slope and its value in the
   model's units, the dual in the model's units, per CAPRI region and FOUT (750 rows, 250 regions), as
   capri_data/baselines/capri_greendeal_ref/1730/environment/manure_pool_market_2030.csv, from the kept extract
   capri_data/sources/raw/capri/results/fert/manure_pool_inputs_2030.parquet (--parquet DIR or --download: the raw).
2. The region's PSHW: the multiplier of the fertilisation block's EXCR pool row of the regional NLP (fertDistExcr_
   with ManureNPK_ merged: the manure applied = excreted less losses less net exports), per nutrient, recorded with
   each solve (capri_regional_nlp.py `manure_values`, res.manure_value). Positive (a value) in every region of the
   four-country test.
3. The market model as a convex QP (Clarabel), its pool balance's dual the price. Differences from CAPRI, each needed
   by the model's form:
   - the trade quantities are the deviations from CAPRI's base trade (which the accounts hold, supply/land.py), so the
     base is an equilibrium at zero deviations and zero pool prices: no calibration wedges (PriceCal) and no fixed
     third-country exports in the balance (they are in the base trade; the files give none by region);
   - the trade cost constants cs0, cb0 are recomputed at each region's solution from its trade columns' reduced costs
     (CAPRI calibrates p_manureSell/BuyCostConst once so the base trade is optimal; the regional NLP holds the
     equivalent terms in the rows its trade columns enter), so the market model's first-order conditions hold at each
     region's last solution as in CAPRI's refit; the slopes are the regional NLP's;
   - the exports are bounded by the manure produced (the regional NLP's own row);
   - p_mTradeAddCost (the autarky buffers, l. 396-436) ported 12 November 2026: a link unused at the calibration point
     costs (buffer_k + buffer_l) / 2 more, CAPRI's 10 EUR per t, and in the Green Deal group 50,000 for its isolated
     pools (UK, MT, NO, CS, AL, MO, BA, MK, KO, TUR, CY), so these are closed there; the links CAPRI's calibration uses
     are taken as those from its exporting pools to its importing ones by p_priorMTrade (exempt in both directions; at
     the 2030 calibration point BL, DE and NL to FR for N and P, the flows the listing shows: BL 16.6, DE 10.8, NL 1.1 kt
     N), exact while one pool imports; CAPRI's term max(0, P_l - P_k - c) is zero at the model's equal base prices;
   - a negative b (one region-nutrient: NL410000 MANN, calibration dual -824 EUR per t) is kept as CAPRI's: the problem
     stays convex when the region's trade cost slopes outweigh it ((1/b + cs1)(1/b + cb1) >= 1/b^2; NL410000:
     |b| cs1 = 42 against 2); otherwise the run stops with the region named (none on the 2030 data).
4. Checks (11 November 2026, Green Deal 2030 greendeal_lnds8_org18_pest20_mine13crp_surp30, CAPRI's averaging):
   - Austria, Ireland, Spain, Slovakia (31 units): converged in 14 iterations, the worst pool's gap falling at every
     step (18.1%, 11.0, 7.8, 5.6, 3.9, 2.9, 2.2, 1.7, 1.2, 0.9, 0.7, 0.5, 0.4, 0.3%); schedules + CAPRI's averaging
     19 iterations oscillating, schedules + damped 8. Equilibrium equal to the damped run's within 0.1 points on every
     indicator of tools/check/compare_runs.py.
   - full EU (221 regional models, 12 November 2026): converged in 19 iterations, 5,259 s (the baseline's market Hessian
     recomputed: about 25 minutes of it); the worst pool's gap 24.3, 15.7, 12.6, 10.4, 8.2, 12.6, 5.3, 4.2, 3.4, 2.1,
     1.5, 1.2, 1.0, 0.8, 0.7, 0.5, 0.4, 0.4, 0.3%; schedules + damped 16 iterations, schedules + CAPRI's averaging not
     converged after 36. Equilibrium against the damped run: prices within 0.1 points (beef +13.3% against +13.4,
     milk +7.9 against +8.0, pork +7.7 against +7.9), herds and production within 0.1, GHG total -13.6% against -13.8,
     fertiliser N2O -32.6 against -33.0, ammonia -29.6 against -29.7.
   - with the autarky buffers (12 November 2026, same scenario): converged in 21 iterations, the worst pool's gap
     falling at every step (24.3, 15.7, 12.5, 10.1, 7.8, 6.0, 4.6, 3.6, 2.7, 2.0, 1.5, 1.2, 1.0, 0.8, 0.7, 0.5, 0.4,
     0.4, 0.3, 0.2, 0.2%); the equilibrium within 0.4 points of the run without them (beef +13.4% against +13.3, milk
     +8.0 against +7.9, GHG total -13.7 against -13.6, fertiliser N2O -33.0 against -32.6); Malta's N exports, 96 t
     without the buffers, are zero (its pool closed as in CAPRI's Green Deal group), Cyprus' stay zero.

## Open

- outer_loop.manure_pool_es_slope: CAPRI's code ("capri_code", the project lead's choice of 12 November 2026: "start
  with capri code and see what happens") against its documented elasticity ("capri_doc"), not yet compared.
- A per-step check against CAPRI's own chk_manure_trade_<BAS><SIM>*.gdx (p_mTradeReport) once a CAPRI scenario run
  completes (the project lead's Farm-to-Fork run of 11 November 2026 stopped in EL210000's supply model before the
  first manure market step: widen_bounds.gms l. 265-269 raised a zero lower bound of the idle histosol group's mineral
  N to 1e-6).
