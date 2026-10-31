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

- **CAPRI:** two technologies per crop (T1 high yield, T2 low yield; capmod.gms l. 246), each with its own yield, inputs and PMP terms.
- **capri-mod now:** one activity; CAPRI's T1/T2 PMP block collapsed exactly per crop (build_pmp_capri_2030.py); DEP-9.
- **Expected effect:** intensity responses (yield, N per ha) to prices and N targets; the crop groups' marginal N need.
- **Effort:** large: activities, yields and inputs per technology, fertilisation per technology, the PMP block without the collapse, reports. A design document first.
- **How to check:** base reproduced exactly; crop supply elasticities against CAPRI's own (supply_elas files); the F2F/GD gate.

### S2. Aggregated activities

- **CAPRI:** GRAE and GRAI, OFAR and ROOF, VSET and FALL as activities of their own.
- **capri-mod now:** GRAS, OFOD and SETA (the grassland intensity split exists; the set-aside split is for reports only).
- **Expected effect:** grassland and fodder N need; set-aside premiums.
- **Effort:** medium per activity; part of S1's design.
- **How to check:** as S1.

### S3. The fertilisation block's scaling (kappa)

- **CAPRI:** the multiplier on the need alone.
- **capri-mod now:** on the need net of the permanent crops' own residues (registered: CAPRI's form had no solution with positive flows in some regions).
- **Expected effect:** the block's balance in permanent-crop regions.
- **Effort:** first a diagnosis: why CAPRI's form fails there, a symptom of S1/S2 or of the data.
- **How to check:** the regions where it fails; with the cause removed, CAPRI's form back and the base exact.
- **Diagnosis (31 October 2026; F2F run r200's regional NLP dumps, 221 regions x N, P, K):**
  - CAPRI's form (the multiplier on the need alone, closing the balance at the model's base) fails in 10 of 663
    region-nutrients: BG01 and BG03 (K), BL32, NL23 and NL34 (P), RO01, RO03, RO04 and RO05 (N), RO03 (P). In each,
    the grassland group's own residues (with deposition for N) exceed its scaled need: they cover 92-96% of the
    group's need per ha in CAPRI's 2030 data already (RO03 N: 155.7 of 162.3 kg/ha), and the model's base gives a
    multiplier below that share (RO03 N 0.69, the others 0.83-0.94).
  - The cause is the base, not CAPRI's form: the crop coefficients are CAPRI's 2030 need per crop (its NUTNED_
    left-hand side, with its own multiplier and additive term in it, which close CAPRI's 2030 balance exactly), and
    the model's 2017 levels and supply give less supply relative to need in these regions. Not S1 or S2.
  - CAPRI's additive term (v_cropNutNeedAddFact, 1-5 kg/ha in its 2030 export for the six member states it covers)
    does not repair it: with the multiplier closing the balance, the term needed is 8-21 kg/ha in five cases and has
    no solution in the other five (grass needs more per ha than the region's average).
  - capri-mod's form changes the multiplier in every region, not only in the ten: median difference 0.008 for N
    (largest 0.67), under 0.001 for P and K (largest 0.95 P).
- **Options:** (a) CAPRI's form in the 653 region-nutrients where it has a solution, capri-mod's form only in the ten
  (the departure narrowed to where it is needed); (b) as now, until a new base year brings CAPRI's own fertiliser
  calibration (fert/ferttrm_*.gms) at the model's base, where CAPRI recalibrates the multiplier and the additive term
  with its priors.

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

### S12. The solver

- **CAPRI:** CONOPT.
- **capri-mod now:** IPOPT, with the warm and jump checks (DEP-18).
- **Expected effect:** which local optimum a non-convex region ends at (K79: FR820000, BG020000).
- **Effort:** in development (Step G, linear solvers); K79's diagnostic first.
- **How to check:** the K79 diagnostic (tools/check/k79_multistart, draft): the objectives of the two states.

## 2. Order (agreed with the project lead, 31 October 2026)

1. **S3 diagnosis and S12's K79 check.** Both are cheap and tell where the larger items matter: S3 may point at S1/S2;
   the K79 check tells whether the regions that switch state have one better optimum.
2. **S4 and S5.** Contained ports, each with its own gate.
3. **S1/S2 design document.** The largest item: the design first, then a decision on whether and how.
4. **S6 item by item, S7, S8, S10, S11** as the project lead marks them.
5. **S9** with K65.

Each step: CAPRI's code read and cited, the base reproduced exactly, tests, and the F2F/GD gate compared with the
previous one, as for every gate. The measure of progress is limited to CAPRI's 2030 reference until CAPRI's own
Farm-to-Fork and Green Deal scenario results are in hand (K13, K29, K66, K78, K92).
