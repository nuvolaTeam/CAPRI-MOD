# The structural differences from CAPRI's regional supply model: what to assess and in which order

Written 31 October 2026, after the K77 decision (KNOWN_ISSUES K77, CAPRI_DEPARTURES_REGISTER DEP-30). The model's 2030
baseline reproduces CAPRI's reference levels by calibration; its marginal values (the value of N, land and feed in a
region) come from its own structure and are not calibrated. Where that structure differs from CAPRI's, the marginal
values differ, and options with flat cost curves (the fertiliser options of K77) turn small differences into large
ones. This plan lists those structural differences, what each would take, and how to check it. Effects are stated as
expected where they were not measured. Nothing here is decided: the project lead marks what is unwanted, and the work
goes gate by gate.

## 1. The list

### S1. One activity per crop

- **CAPRI:** two technologies per crop (T1 high yield, T2 low yield; capmod.gms l. 247-249), each with its own yield, inputs and PMP terms.
- **capri-mod now:** one activity; CAPRI's T1/T2 PMP block collapsed exactly per crop (build_pmp_capri_2030.py); DEP-9.
- **Expected effect:** intensity responses (yield, N per ha) to prices and N targets; the crop groups' marginal N need.
- **Effort:** large: activities, yields and inputs per technology, fertilisation per technology, the PMP block without the collapse, reports. A design document first.
- **How to check:** base reproduced exactly; crop supply elasticities against CAPRI's own (supply_elas files); the F2F/GD gate.
- **Decided (1 November 2026):** option (c), one mix column per crop, CAPRI's T1/T2 model in other coordinates
  (docs/design/S1_S2_DESIGN.md section 5); after refactor stages 3-5.

### S2. Aggregated activities

- **CAPRI:** GRAE and GRAI, OFAR and ROOF, VSET and FALL as activities of their own.
- **capri-mod now:** GRAS, OFOD and SETA (the grassland intensity split exists; the set-aside split is for reports only).
- **Expected effect:** grassland and fodder N need; set-aside premiums.
- **Effort:** medium per activity; part of S1's design.
- **How to check:** as S1.
- **Decided (1 November 2026):** the three pairs as activities of their own, as CAPRI (S1_S2_DESIGN.md section 5).

### S3. The fertilisation block's scaling (kappa)

- **CAPRI:** the multiplier on the need alone.
- **capri-mod now:** on the need net of the permanent crops' own residues (registered: CAPRI's form had no solution with positive flows in some regions).
- **Expected effect:** the block's balance in permanent-crop regions.
- **Effort:** first a diagnosis: why CAPRI's form fails there, a symptom of S1/S2 or of the data.
- **How to check:** the regions where it fails; with the cause removed, CAPRI's form back and the base exact.
- **Diagnosis (31 October 2026).** CAPRI's form (the multiplier on the need alone, closing each region's balance
  at the model's base) fails where a permanent group's own residues (with deposition for N) exceed its scaled need.
  The grassland group is the one that fails: its own residues cover 92-96% of its need per ha in CAPRI's 2030 data
  (RO03 N: 155.7 of 162.3 kg/ha), so a multiplier below that share leaves it no room. Needs and areas at the model's
  base match CAPRI's 2030 closely (RO03 N: 327 against 329 kt, 2,363 against 2,368 kha); the supply decides.
  - With manure trade off (Farm-to-Fork, as JRC121368): 10 of 663 region-nutrients fail (BG03 K; BL32, NL23, NL34
    P; RO01, RO03, RO04, RO05 N; RO03 P and K). Most of it is the trade: CAPRI's 2030 values include it (RO03
    imports 62.7 kt N, NL34 11.1 kt), and without it the model's manure applied spans 0.30-67 times CAPRI's by
    region.
  - With manure trade on (the baseline default): 5 fail, all Romanian N (RO01-RO05, multipliers 0.85-0.91); the
    manure applied is 0.99-1.19 times CAPRI's (10-90%). What is left is Romania's mineral N: the model's 2017 base
    is about half of CAPRI's 2030 in RO01, RO03 and RO04 (0.48-0.52), a vintage difference.
  - CAPRI's additive term (v_cropNutNeedAddFact, 1-5 kg/ha in its 2030 export for the six member states it covers)
    does not repair it: with the multiplier closing the balance, the term needed is 8-21 kg/ha or has no solution.
  - capri-mod's form changes the multiplier in every region, not only where CAPRI's fails: median difference 0.008
    for N, under 0.001 for P and K (these figures from the trade-off run).
  - A first version of this diagnosis (same day) took the trade-off run's mismatch for a data fault in the regions'
    manure; it was the trade setting.
- **Decision (31 October 2026, the project lead): narrow it.** CAPRI's form wherever it leaves every permanent
  group a positive need for its flows; capri-mod's form only where it does not (capri_mod.fert.npk.need_multiplier,
  used by the fertilisation block and the P accounts alike). Checked at the base: RO03 (N scaled, P and K CAPRI's
  form with manure trade; all three scaled without), RO04, NL34; the base reproduced (activities within 8e-6).

### S4. Manure P and K trade

- **CAPRI:** MANP and MANK traded as products of their own.
- **capri-mod now:** P and K carried in the region's manure proportions with the traded N (DEP-10).
- **Expected effect:** P and K balances in manure-trading regions; little on N.
- **Effort:** small to medium: CAPRI's two products in the manure market.
- **How to check:** the manure market's P and K flows against CAPRI's 2030 reference.
- **Decision (31 October 2026, the project lead):** port CAPRI's three markets, as a general improvement of the model
  and not for one scenario. CAPRI's 2030 reference shows why the proportional rule was not close: of 235 regions with
  N trade, the P and K trade often has another size or another sign (DE80 exports 10.2 kt N and imports 20.9 kt P2O5;
  FR51 exports 8.2 kt N and 32.2 kt P2O5, where the proportional rule gives 4.2).
- **Done (31 October 2026):** MANP and MANK columns per region (supply/land.py), in the block's P and K balances
  (supply/fertilisation.py), their own pools cleared one by one (coupling/manure.py), the P accounts from the P
  market's trade. Base exact (Belgium: activities within 7e-6 of base, as before); under a carbon tax N trade moves
  and P and K stay (the tax has no P or K term in CAPRI's structure). Next: the gate.

### S5. Ammonia options held without an N incentive

- **CAPRI:** in the model, the base a first-order point.
- **capri-mod now:** held at their base shares (DEP-15, K63).
- **Expected effect:** the N kept in manure, so the value of mineral N.
- **Effort:** medium: they are in the NLP already; the hold is a switch.
- **How to check:** adoption against CAPRI's reference; the gate.
- **First check (31 October 2026):** the hold switched off in a baseline (DE94, NL22; the N incentive test forced
  true). NL22: nothing moves. DE94: ten options leave their base shares with no policy at all (broilers' low-emission
  storage cover 0 to 0.27, laying hens' 0 to 0.20), activities 2e-4 off the base. This is K63's saddle: the base is
  a first-order point (the calibration holds it), but along the options' joint direction (storage cover x spreading,
  multiplied in the loss cascade) the objective curves downward, and IPOPT leaves it; CONOPT, starting at the
  calibrated point, stays. So S5 is not a switch: the hold can go only once the curvature is understood. Next: the
  Hessian of the options block at the base, its negative direction, and the terms behind it against CAPRI's
  (ammo_tech.gms: the options' quadratic cost and the cascade), to see whether CAPRI's own model has the same saddle.
- **The curvature (31 October 2026, DE94 at its base, the Hessian of the Lagrangian on the 157 options):** three
  negative directions: broilers' storage covers with their application techniques together (-802), laying hens'
  (-81), bulls' low-emission storage cover (-3.9). Two options curve downward on their own (broilers' and laying
  hens' low-emission cover, -11.5 and -4.0): their cost term (slope 12.4 x stock 0.0007 per head for broilers' high
  cover) is small against the value of the N they keep. The next question is whether those cost terms are CAPRI's:
  the poultry options' cost basis was wrong once already (K63, a factor 1000). To check: CAPRI's cost per place of
  these options for DE94 (ammo_tech.gms, its quadratic term) against the model's slope x stock.
- **CAPRI's structure (ammo_tech.gms, read 31 October 2026):** for the manure-management ammonia options CAPRI sets
  the unobserved quadratic term to zero (l. 3121, pmpParSqr = 0) and calibrates only the linear term from the
  first-order condition at the initial shares (l. 3126-3133); the only curvature is the observed cost slope
  (costParSqr = 2 x v_beta, from its farm-size cost curves, l. 1972-1980), which capri-mod's slope reproduces
  (tools/build/build_ammonia_tech_model.py). The N kept enters CAPRI's cascade multiplicatively as in capri-mod. So
  the saddle is very probably CAPRI's own: its base is a first-order point that is not a minimum along the poultry
  options, and CAPRI stays there because CONOPT starts at the calibrated point; with a shock it moves wherever its
  path leads. Not yet checked: CAPRI's costParSqr values for DE94 against the model's slope (a GAMS run or CAPRI's
  p_ghgMiti for the region would show it).
- **Options:** (a) keep the hold (DEP-15): deterministic; departs from CAPRI only in runs without an N incentive;
  (b) free the options as CAPRI, accepting that a solver leaves a saddle by its own path (IPOPT left it at the base
  itself, so the baseline would not be reproduced); (c) beyond CAPRI: a calibrated quadratic term for the options
  where the base is a saddle, the smallest that makes it a local minimum (CAPRI does calibrate such terms for its
  other options: pmpParSqr in RedFert, tillage, cover crops), then free them.
- **Decision (31 October 2026, the project lead): (a), keep the hold (DEP-15).** S5 closed.

### S6. The other regional NLP departures

- **CAPRI:** —.
- **capri-mod now:** DEP-10's list: need multipliers; fertiliser calibration in RO21, RO22, RO31, RO41, RO42, ES62, HU11; the inner dual bound; mineral caps exempted by solving; others.
- **Expected effect:** regional; the seven calibration regions most.
- **Effort:** one at a time; each has its reason recorded.
- **How to check:** per item.

### S7. Market demand calibration

- **CAPRI:** market and supply models calibrated to the same baseline before the run.
- **capri-mod now:** demand recalibrated to supply in every baseline iteration, frozen in scenarios (DEP-5).
- **Expected effect:** prices, so the value of everything; small at base by construction.
- **Effort:** medium.
- **How to check:** the baseline's market against CAPRI's reference market.

### S8. One EU trade block

- **CAPRI:** EU_WEST and EU_EAST.
- **capri-mod now:** one EU27 block (DEP-3); tried 18 October 2026, F2F deviation 4.22 -> 4.65.
- **Expected effect:** regional prices between east and west.
- **Effort:** medium (the market supply Hessian per block).
- **How to check:** the gate.

### S9. Cattle member splits off

- **CAPRI:** HEIR and the calf activities; young animals cleared per sex.
- **capri-mod now:** pooled young-animal markets (DEP-4; K65: did not converge).
- **Expected effect:** cattle herds and their manure.
- **Effort:** large (K65's convergence).
- **How to check:** K65's test runs.

### S10. Mitigation options not built

- **CAPRI:** in the Green Deal technology list: NoTill and LegSh (the others are not needed for F2F/GD, K93).
- **capri-mod now:** not built (DEP-8).
- **Expected effect:** NoTill: yield, leaching, N2O, from small initial shares.
- **Effort:** medium each.
- **How to check:** their scenario response once built.

### S11. Quantities rebuilt from CAPRI's reported results

- **CAPRI:** CAPRI's internal parameters.
- **capri-mod now:** per activity, CAPRI's averages over T1/T2 (part of S1); where CAPRI reports nothing, rebuilt: the 2030 feed slopes with 2017 weights (DEP-22), the MITERRA fractions, the digestibility table.
- **Expected effect:** small each, documented per builder.
- **Effort:** per item; some close with more exports from the project lead's CAPRI.
- **How to check:** the rebuilt quantity against a CAPRI export, where one can be made.
- **Status (10 November 2026): closed, one check left.** The 2030 feed slopes: CAPRI's 2030 SLOP with CAPRI's 2030
  weights (DEP-22 fixed). The 2030 rations per activity: CAPRI's own (DATA at the 2030 point, since 10 November 2026
  its Green Deal baseline; not rebuilt). The digestibility table: CAPRI's code (envind/def_digestibility.gms,
  tools/build/build_digestibility_table.py; not rebuilt). The MITERRA fractions: the shares of liquid and solid
  manure, grazing and housing (p_Nemidat TypeShare) checked against sim_ini_21730 and found equal; the storage and
  application loss factors cannot be checked against an export of CAPRI (they are computed inside ammo_tech.gms from
  the LitRev inputs, docs: claude/n_cascade_spec.md) and stay as built, unverified against a CAPRI number. K65 (S9)
  needs CAPRI's per-sex young-animal results, not available now.

### S12. The solver

- **CAPRI:** CONOPT.
- **capri-mod now:** IPOPT, with the warm and jump checks (DEP-18).
- **Expected effect:** which local optimum a non-convex region ends at (K79: FR820000, BG020000).
- **Effort:** in development (Step G, linear solvers); K79's diagnostic first.
- **How to check:** the K79 diagnostic (tools/check/k79_multistart, draft): the objectives of the two states.

### S13. LULUCF carbon: accounting and the carbon price on land-use change (added 9 November 2026)

- **CAPRI:** the land-use-change transitions carry carbon effects (biomass, soil carbon, burning, histosols; the GWP of
  each transition per climate zone) and, under a carbon price on LULUCF (p_carbonTax(..., "GLUC")), their cost per
  hectare enters the land rents and the objectives:
  - market, non-EU regions: lulucf_market (arm/market_model.gms from l. 1995: landshareMrk_, the GWP*MrkLu_
    equations, glucCostPerHa_; v_glucCostPerHa in the rents, l. 1717), on with REPORTS_ENV, its equations active only
    where p_carbonTax(RMS, "GLUC") > 0 (capmod/set_global_variables.gms l. 399-410);
  - supply, EU regions: lulucf_supply with ghgabatement (the supply model's LULUCF equations; post-model reporting in
    reports/sol_simy.gms otherwise);
  - without a price, LULUCF emissions are reported after the solves (sol_market, sol_simy).
- **capri-mod now:** the transitions are ported on both sides (supply: capri_mod/environmental/luc.py; market:
  capri_mod/market/luc.py, luc_market, 9 November 2026); no carbon accounting of the transitions, no LULUCF price
  (DEP-44 for the market's recursive solve).
- **Where CAPRI uses the price:** not in the scenarios run now. ecampa/carbtax50_endotech_set14.gms taxes GGWP in the
  EU supply regions only; greendeal/oth_pol.gms has GWPA and GLUC taxes on the supply regions (0 in the Green Deal
  2030 run, oth00); the market regions' GLUC price is set in the global mitigation scenarios (agmip/agclim50_*,
  afolu_ets).
- **Expected effect:** none on Farm-to-Fork, the Green Deal and the carbon tax at 50; the LULUCF emissions and, with
  a GLUC price, land use and prices in the mitigation scenarios.
- **Effort:** large: CAPRI's carbon-stock data (p_biomassJrc, p_soilCarbon, p_SOCfactorJRC, the burning and histosol
  factors per climate zone) extracted and built, the accounting per transition, then the cost in the rents (market)
  and in the regional models (supply). Two steps: (a) post-model reporting as sol_market and sol_simy; (b) the price.
- **How to check:** (a) CAPRI's LULUCF emissions at its 2030 calibration point (DATA GLUC and the gas items per
  region in sim_ini_21730 and the reference results); (b) a CAPRI run with a GLUC price (to request: none in hand).
- **When:** with the carbon-tax scenarios, together with S10 (the project lead's decision of 9 November 2026 for S10;
  S13's timing to be confirmed).

## 2. Order (agreed with the project lead, 31 October 2026)

1. **S3 diagnosis and S12's K79 check.** Both are cheap and tell where the larger items matter: S3 may point at S1/S2;
   the K79 check tells whether the regions that switch state have one better optimum.
2. **S4 and S5.** Contained ports, each with its own gate.
3. **S1/S2 design document.** The largest item: the design first, then a decision on whether and how.
4. **S6 item by item, S7, S8, S10, S11** as the project lead marks them; S10 and S13 together with the carbon-tax
   scenarios (9 November 2026).
5. **S9** with K65.

Each step: CAPRI's code read and cited, the base reproduced exactly, tests, and the F2F/GD gate compared with the
previous one, as for every gate. The measure of progress is limited to CAPRI's 2030 reference until CAPRI's own
Farm-to-Fork and Green Deal scenario results are in hand (K13, K29, K66, K78, K92).
