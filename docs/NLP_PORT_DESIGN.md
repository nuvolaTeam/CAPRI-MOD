# The regional supply model in CAPRI's NLP form: design

*Status: revised 20 October 2026 against the code. The NLP form is the default since 20 October 2026 (the user's
decision: CAPRI's own form); the conic form stays as an option. The "Scenario results" section is a dated record of the
port; current results are in README section 9 (Validation). Equations from docs/SUPPLY_MODEL_MAP.md.*

## Principle

The regional problem is written with CAPRI's equations (supply/supply_model.gms) and solved as a non-convex NLP with
IPOPT (CasADi), as CAPRI solves m_capModQ with CONOPT. What capri-mod has already built as **data and calibration** is
kept: activity set and base levels, revenues and premiums per activity, the PMP quadratic terms (PMPCalibrator, decision
5a.5), the land-market matrix, rations (feeds, contents, requirements, prices), fertiliser priors and crop groups, manure
excretion and losses, manure-trade costs, abatement option data. What changes is the **constraint system and the
variables**: they are CAPRI's.

## Module layout

- `capri_mod/supply/capri_regional_nlp.py`: `CapriRegionalNLP(spec)` builds the model in blocks, each a method
  writing CAPRI's equations (one docstring per equation with its supply_model.gms line):
  `_objective`, `_land` (LandBalNoSlak_, Trustee land market, LandBalSlak_/ANNC, e_artoBal), `_feeding` (REQSE_,
  FEDUSE_, QUADRF_/QUADRF1_), `_fodder` (SUPBAL_ for non-tradable fodder), `_fertilisation` (NUTNED_ per crop group and
  nutrient N/P2O5/K2O, fertDistMine_/Excr_/Cres_, ManureNPK_, manExportOrAppl_, endogenous manure availability, manure
  trade), `_inner_fert` (e_fertDistPartial, e_focFertDist, regulations), `_cap_rules` (permGrasGreening_, ecoSetAside_,
  cropDivGreening_, winterCover_, e_setaLandscape), `_luc` (the transition system), `_policy_targets` (SURTOT_REST_,
  e_synNMax, e_minCoverCrops), `_abatement` (ghgAbatement block: v_Miti, v_emiLoss cascade, GHG_Mit_Cost_, TotMit_,
  option limits), each switched as CAPRI switches it.
- The spec (plain dicts and arrays) is assembled from the RegionalSupplyModel in `supply_module.py`
  (`_capri_nlp_solve`); no separate spec module was written.
- `RegionalSupplyModel.supply_form`: `"nlp"` (default) or `"conic"` (option) until 26 October 2026, when the conic form
  was removed and the setting with it. Results returned in
  the same SupplyResult fields (activities, outputs, feed, fertiliser, emissions, duals), so the market, manure market,
  young-animal markets and the environmental accounts keep working.
- Builders for the new data (all CSV, provenance in DATA_SOURCING_REGISTRY):
  `tools/build/build_fert_dist_priors.py` extended to P and K; `tools/build_nutrient_balance_pk.py` (crop P/K needs, P/K
  excretion, need multipliers and availability per nutrient, mineral P/K prices); `tools/build_luc_transitions.py`
  (p_luc_matrix, LU classes, initial areas); `tools/build_cap_rules.py` (greening limits from the base, IFM-CAP Shannon
  adjustment, winter-cover shares); `tools/build_abatement_options.py` (AD, legume share, winter cover, tillage, urea
  substitution, storage variants, 3-NOP, linseed penalty) from the uploaded CAPRI dat files.

## Calibration

CAPRI calibrates its PMP terms so that the base is optimal; with a new constraint system the base must again be a KKT
point. As CAPRI does with its calibration constraints: solve the NLP with the activity levels fixed at the base, take the
multipliers of the fixing, and add them to the linear PMP term (keeping capri-mod's quadratic matrix, decision 5a.5).
Check per region: the unconstrained solve at base prices returns the base levels (tolerance as CAPRI's calibration test).

As built (`CapriRegionalNLP.calibrate`): the multipliers of the rows and bounds active at base are fitted by least
squares on the first-order conditions of the non-activity variables, and what remains goes into the activities' linear
terms and the feeds' CNST. Since 21 October 2026 (KNOWN_ISSUES K58) the fit carries a small ridge term (CAL_RIDGE
1e-10), which picks the least-norm multipliers where a row and a bound active on the same variable leave them
undetermined. Without it the fit returned multipliers of 6e13, and IPOPT's results depended on the path. CAPRI instead
sets the land rents exogenously in its calibration (prep_cal.gms, cal_land_nests.gms); that is planned in
docs/LAND_RENT_CALIBRATION_PLAN.md.

## Solving

IPOPT (MUMPS), warm start from the region's previous solution (CAPRI's CONOPT starts from the previous solution); first
start the base. Regions in parallel as now. A region whose solve fails keeps its previous solution and is reported (no
silent fallback to another model). Run time measured early, on the base and one Farm-to-Fork iteration.

## Departures from CAPRI that stay (registered in docs/CAPRI_DEPARTURES_REGISTER.md)

- Activity set: capri-mod's (46 activities plus the dairy, grassland, bull and heifer splits), not CAPRI's full list
  (DEP-9).
- PMP and land-market matrices: capri-mod's calibration was decision 5a.5; superseded on 22 October 2026: the default
  is CAPRI's own 2030 terms (`supply.pmp_source = "capri2030"`, K61); capri-mod's recipe terms remain an option.
- LULUCF and emission totals: accounting after the solve where they do not enter decisions (no emission tax).

## Order of work

1. Spec and core (objective, PMP, land and land market, feeding in CAPRI's per-head form, fodder balance).
   Check: base reproduction region by region.
2. Fertilisation with N, P, K, the inner model inside, mineral purchases >= 0, manure trade and endogenous availability.
   Check: CAPRI's 2030 allocation by crop group and source reproduced at the base.
3. CAP rules and LUC. Check: base feasible, rules binding where CAPRI's are.
4. Abatement block (switch, off by default). Check against the conic model's technology results and CAPRI's 2030 adoption.
5. Integration, run time, Farm-to-Fork / Green Deal / Green Deal 2030 / coupled-support check, tests, documentation.

## Status (20 October 2026)

Implemented (`capri_mod/supply/capri_regional_nlp.py`; the default since 20 October 2026, the only form since
26 October 2026):

| Block | CAPRI equations | Notes |
|---|---|---|
| Feeding | REQSE_ (energy, protein; equalities per head, trimmed requirement = base supply), FEDUSE_, QUADRF_, feed bounds (set_supply_bounds.gms) | no dry-matter or share rows (`_pw`); calf/dairy/genetics split columns' requirement changes in total form |
| Fodder | SUPBAL_ for non-tradable fodder as equalities | base gap as constant (K36/K46) |
| Land | land rows, land market, LandBalNoSlak_ pairs as ranged rows, activity bounds as variable bounds | capri-mod's land-market matrix (decision 5a.5) |
| Fertilisation | NUTNED_ per crop group for N, P2O5, K2O; fertDistMine_/Excr_/Cres_; ManureNPK_; inner model FOCs (e_focFertDist with the inverse written directly; mu_MINE = 0; flows 0.001-1000 x mode; duals +-10); endogenous manure N availability (endoManAvail.gms); purchases >= 0 at CAPRI's unit value | data `tools/build/build_npk_balance_2030.py` (CAPRI 2030 reference; identities exact) |
| CAP greening | permGrasGreening_, ecoSetAside_ (5%, weights of cap_2013_2020_greening.gms, FLEG from CAPREG), cropDivGreening_ (Shannon >= base index) | `tools/build/build_cap_greening.py` |
| LUC | e_landTypes_to_LUclass, e_luClassInitial/Final, e_FocLUC with gamma priors | solved after each regional solve (`capri_mod/environmental/luc.py`): without a LULUCF price the block enters no other equation, so the result is the same as inside; `tools/build/build_luc_2030.py` |
| N-surplus target | SURTOT_REST_ with e_SURTOTHa: the regional row with the mineral parts replaced by the purchases | |
| Mineral caps | "crp": inner-model regulations (e_fertDistPartialRegu, e_fertDistReguMax; "f2f" on MINE, "limCres" on CRES for N, P2O5, K2O); "uaa": e_synNMax | caps from the model's own base allocation |
| Organic area target | organic_minfert_redu.gms ('region_and_crop'): "f2f" regulation per crop group at base mineral N per ha x (1 - the group's organic conversion), groups below 10 kg/ha at base; "limCres" 1.2 x base for every nutrient; with mineRedu the more stringent MINE cap (min), mineRedu's limCres | the conic form instead takes mineral N off converted land with no need to replace it; in the NLP form the organic I/O change no longer removes the converted land's fertiliser cost a second time (it is bought as purchases) |
| Abatement options | ammonia options with CAPRI's loss cascade (kept N into ManureNPK_), fertiliser options (one regional share each; mineral x (1 + sum share NMIN) in NUTNED_), inhibitor on manure (manure x (1 + share NMAN)) | inside whenever capri-mod's ghgAbatement proxy is on (`use_manure_techs` with feeding inside), baseline included |
| Emission tax | ghgTax on the activities and feeds (coefficients at the baseline, as the conic form), on mineral N through the purchases (soil N2O, direct + volatilised; the nitrification inhibitor's side-effect factor of the accounts, exact rather than linearised), on the ammonia options' manure N2O and the NH3 they keep | the conic form's fixed-substitution terms on mineral N (manure trade, inhibitor on manure, N kept) are taken out: mineral N is endogenous here |
| Calibration | the base is a first-order point: multipliers by least squares on the non-activity variables (the fertilisation block's from its own square system), residuals into the activities' linear terms, the feeds' CNST, the options' cost constants | exact base reproduction (all cells within 0.1%) |

Every block is written in the NLP form. Where IPOPT fails from every start (warm, previous point, cold), that solve
of the region is done in the conic form (feeding inside) and recorded per region in `metadata["nlp_fallback"]`
(KNOWN_ISSUES K55-1); before 20 October 2026 such a region fell to the regional QP without feeding.

Speed. Creating an IPOPT solver (CasADi's symbolic derivatives) cost about 0.35 s per regional solve, several times
the solve itself; the full Farm-to-Fork run went past 30 minutes. Three changes:
- the PMP quadratic's gradient and Hessian are given to IPOPT directly (Q y and Q, scaled), the rest by automatic
  differentiation: identical derivatives, solver creation 0.35 s -> 0.12 s (the dense quadratic dominated the
  colouring of the Hessian);
- every data value enters the CasADi graph as a parameter and solvers are cached by the graph's serialisation (the
  structure) within a process: a value left as a constant only costs a cache miss, not a wrong solve. The workers are
  forked per round of regional solves, so the cache serves a region's solves within a round (and every solve when run
  in one process). Sending the workers' solvers back to the main process was tried and ran out of memory (about 6 MB
  per solver);
- IPOPT's warm start from the region's last primal-dual point when the structure is the same (CAPRI's CONOPT also
  restarts from the last solution): 14-19 iterations instead of 26-242 on the regions tried; a cold start from the
  same point, then from the default start, follow if it fails. A warm start is cut at 200 IPOPT iterations
  (`WARM_MAX_ITER`): from a point whose active set no longer fits it can take over a thousand (DEB2: 1,252 in the
  Green Deal baseline) where the cold start takes a few hundred at most. With it a Green Deal outer iteration takes
  80-120 s on the two cores here (r41), against about 4.5 min on average before (r40);
- the outer loop's trace (`--verbose`) gives per iteration the time, the starts IPOPT used (warm / prev / start, then
  a relaxation) and the regions whose levels moved most (`CAPRIModel._trace_nlp_regions`).

Starting points inside the regulations: a start with a regulated flow at or above its maximum (the prior mode above a
Green Deal cap) leaves IPOPT on the wrong side of the beta density's pole (Brittany: "infeasible"); every start
(default, warm, previous solution) moves regulated flows to at most 95% of their maximum at the start's own areas.

Relaxations kept. Where the Green Deal's mineral caps leave a group's need unmet the duals are widened, then the
caps raised (departure 11). A relaxation once needed is kept for the rest of the scenario (keyed to the caps, so a new
scenario starts strict): CAPRI sets its exemptions once, before its solves. Without it BG32/33/42 and HU21-23
alternated between the relaxed and the strict problem from one outer iteration to the next and the Green Deal run
did not settle (r40: sunflower and Bulgaria's manure pool swinging for 21 iterations).

N loss cascade: CAPRI's (KNOWN_ISSUES K51, docs/N_CASCADE_SPEC.md), in both forms.

Added since (KNOWN_ISSUES K51; docs/N_CASCADE_SPEC.md, docs/AD_SPEC.md): CAPRI's full N loss cascade, anaerobic
digestion, winter cover in the cascade, leaching (LEACHN_) and the indirect N2O of leached and run-off N.
Not yet in CAPRI's form (Green Deal block, decision 5a.1): legume share, tillage, buffer strips, biodiversity options,
biochar, urea substitution, 3-NOP cost, linseed fat penalty, SupplementPerc_.


## Scenario results (20 October 2026)

First Farm-to-Fork runs in the NLP form (r35, r36): mean absolute deviation from JRC121368 15.4 against the conic
form's 4.4, herds cut too far, arable land into forest; the N-surplus target cost the NLP form several times what it
cost the conic form (DE21, N target only, base prices: N price 152 against 7.6 thousand EUR per t N). Three errors of
the port were behind it, not CAPRI's equations:
- the crops' N need was their group's need spread by area (CAPRI's nutNed_lhs per crop): fallow and set-aside 86 kg
  N/ha instead of CAPRI's 3.7 (NITF), intensive and extensive grassland alike. The builder now takes each crop's own
  NITF/PHOF/POTF (the group sums match CAPRI's group need, median 0.1%);
- the grassland split column (GRAI -> GRAE) had no effect on NUTNED_ (now z x (need GRAE - need GRAI) in the GRAS
  groups), and the animal split columns none on ManureNPK_ (now their manure, in proportion to their animal's);
- those columns enter after a region's first solve and were left uncalibrated (now the calibration runs again when
  they appear; the baseline drift is 0.0015 as before).
With these the same test gives DE21 33 (conic 7.6), DE11 8.3 (16.7), FRI1 46 (55).

Farm-to-Fork, NLP form (r38): converged in 12 iterations, 1,346 s; deviation from JRC121368 5.6 (conic r37: 4.4).
| indicator | NLP | conic | CAPRI |
|---|---|---|---|
| pork price | +40.3 | +33.1 | +43 |
| milk price | +31.0 | +37.5 | +1.5 |
| poultry price | +34.8 | +25.3 | +18 |
| pigs | -21.7 | -19.3 | -14.5 |
| dairy cows | -4.6 | -7.1 | -10 |
| cereals production | -11.6 | -14.9 | -15 |
| N surplus | -29.1 | -33.1 | -33.5 |
| fertiliser N2O | -33.6 | -40.2 | -40.4 |
The conic form lets mineral N fall with the crop need met at a fixed substitution rate and takes converted organic
land off mineral N with nothing to replace it; NUTNED_ requires every group's need to be met, so the NLP form cuts
mineral N less and herds more. Where the Green Deal's caps leave a group's need unmet (HR03, HR04, LT01 in Farm-to-
Fork) the duals are widened, then the groups concerned exempted one at a time at their baseline (CAPRI's
p_checkSmallMine), recorded as nlp_relaxed, e.g. "caps:PERM" (K71, 24 October 2026; until then every cap was raised
to 1.1 x base).

Green Deal 2030, NLP form (r39): stopped after 25 iterations (57 min); Finland's manure pool stayed 3.7% out of
balance from iteration 6 (conic r32: 16 iterations, 1,692 s). Price changes stay within about 6%. With IPOPT's reduced
costs in the pools' schedules (r40) the pools cleared but relaxed regions switched (above); with the relaxations kept
(r41) the run converged in 10 iterations, 1,395 s (before K51's cascade and storage options):
| indicator (% from the 2030 baseline) | NLP r41 | conic r32 |
|---|---|---|
| pork / milk / poultry price | +9.5 / +11.9 / +10.6 | +5.6 / +10.4 / +5.8 |
| pork / poultry production | -8.5 / -9.5 | -5.3 / -5.4 |
| cereals production | -3.9 | -6.0 |
| mineral N | -29.8 | -33.6 |
| N surplus | -26.6 | -28.3 |
| GHG / NH3 | -12.9 / -34.3 | -12.0 / -33.7 |
No CAPRI Green Deal result is in hand to compare with (scen_greendeal_2030 is the maximum-mitigation run).

Default since 20 October 2026: the NLP form (the user's decision; the Green Deal run converged, r41 and later r47).
Farm-to-Fork in the NLP form takes about 35 minutes on 2 cores, over the 30-minute budget (open).
