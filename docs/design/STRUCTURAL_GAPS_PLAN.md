# The structural differences from CAPRI's regional supply model: what to assess and in which order

Written 31 October 2026, after the K77 decision (KNOWN_ISSUES K77, CAPRI_DEPARTURES_REGISTER DEP-30). The model's 2030
baseline reproduces CAPRI's reference levels by calibration; its marginal values (the value of N, land and feed in a
region) come from its own structure and are not calibrated. Where that structure differs from CAPRI's, the marginal
values differ, and options with flat cost curves (the fertiliser options of K77) turn small differences into large
ones. This plan lists those structural differences, what each would take, and how to check it. Effects are stated as
expected where they were not measured. Nothing here is decided: the project lead marks what is unwanted, and the work
goes gate by gate.

## 1. The list

| # | Difference | CAPRI | capri-mod now | Expected effect | Effort | How to check |
|---|---|---|---|---|---|---|
| S1 | One activity per crop | two technologies per crop (T1 high yield, T2 low yield, capmod.gms l. 246), each with its own yield, inputs and PMP terms | one activity; CAPRI's T1/T2 PMP block collapsed exactly per crop (build_pmp_capri_2030.py); DEP-9 | intensity responses (yield, N per ha) to prices and N targets; the crop groups' marginal N need | large: activities, yields and inputs per technology, fertilisation per technology, PMP without the collapse, reports; a design document first | base reproduction exact; crop supply elasticities against CAPRI's own (supply_elas files); F2F/GD gate |
| S2 | Aggregated activities | GRAE, GRAI; OFAR, ROOF; VSET, FALL as activities | GRAS, OFOD, SETA (grassland intensity split exists; set-aside split for reports only) | grassland and fodder N need; set-aside premiums | medium per activity; part of S1's design | as S1 |
| S3 | The fertilisation block's scaling (kappa) | the multiplier on the need alone | on the need net of the permanent crops' own residues (registered: CAPRI's form had no solution with positive flows in some regions) | the block's balance in permanent-crop regions | first a diagnosis: why CAPRI's form fails there (a symptom of S1/S2 or of the data?) | the regions where it fails; with the cause removed, CAPRI's form back and the base exact |
| S4 | Manure P and K trade | MANP and MANK traded as products of their own | P and K carried in the region's manure proportions with the traded N (DEP-10) | P and K balances in manure-trading regions; little on N | small to medium: CAPRI's two products in the manure market | the manure market's P/K flows against CAPRI's 2030 reference |
| S5 | Ammonia options at base without an N incentive | in the model, the base a first-order point | held at base shares (DEP-15, K63) | the N kept in manure, so the value of mineral N | medium: they are in the NLP already; the hold is a switch | adoption against CAPRI's reference; the gate |
| S6 | The other regional NLP departures | — | DEP-10's list: need multipliers, fertiliser calibration in RO21, RO22, RO31, RO41, RO42, ES62, HU11, the inner dual bound, mineral caps exempted by solving, others | regional; the seven calibration regions most | one at a time; each has its reason recorded | per item |
| S7 | Market demand calibration | market and supply models calibrated to the same baseline before the run | demand recalibrated to supply in every baseline iteration, frozen in scenarios (DEP-5) | prices, so the value of everything; small at base by construction | medium | the baseline's market against CAPRI's reference market |
| S8 | One EU trade block | EU_WEST and EU_EAST | one EU27 block (DEP-3); tried 18 October, F2F deviation 4.22 -> 4.65 | regional prices between east and west | medium (the market supply Hessian per block) | the gate |
| S9 | Cattle member splits off | HEIR and calf activities, young animals per sex | pooled young-animal markets (DEP-4, K65: did not converge) | cattle herds and their manure | large (K65's convergence) | K65's test runs |
| S10 | Mitigation options not built | in the Green Deal technology list: NoTill, LegSh (the others not needed for F2F/GD, K93) | not built (DEP-8) | NoTill: yield, leaching, N2O; small initial shares | medium each | their scenario response once built |
| S11 | Quantities rebuilt from CAPRI's reported results | CAPRI's internal parameters | per activity, CAPRI's averages over T1/T2 (part of S1); where CAPRI reports nothing, rebuilt: the 2030 feed slopes with 2017 weights (DEP-22), the MITERRA fractions, the digestibility table | small each, documented per builder | per item; some close with more exports from the project lead's CAPRI | the rebuilt quantity against a CAPRI export, where one can be made |
| S12 | The solver | CONOPT | IPOPT (and the warm and jump checks, DEP-18) | which local optimum a non-convex region ends at (K79: FR820000, BG020000) | in development (Step G, linear solvers); K79's diagnostic first | tools/check/k79_multistart (scratchpad draft): the objectives of the two states |

## 2. Proposed order

1. **S3 diagnosis and S12's K79 check.** Both are cheap and tell where the larger items matter: S3 may point at S1/S2;
   the K79 check tells whether the regions that switch state have one better optimum.
2. **S4 and S5.** Contained ports, each with its own gate.
3. **S1/S2 design document.** The largest item: the design first, then a decision on whether and how.
4. **S6 item by item, S7, S8, S10, S11** as the project lead marks them.
5. **S9** with K65.

Each step: CAPRI's code read and cited, the base reproduced exactly, tests, and the F2F/GD gate compared with the
previous one, as for every gate. The measure of progress is limited to CAPRI's 2030 reference until CAPRI's own
Farm-to-Fork and Green Deal scenario results are in hand (K13, K29, K66, K78, K92).
