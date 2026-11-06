# S1 and S2: CAPRI's crop technologies and its split activities (design, 31 October 2026)

Status: **decided by the project lead on 1 November 2026: S1 option (c), one mix column per crop (CAPRI's T1/T2 model in
other coordinates); S2: GRAE/GRAI, OFAR/ROOF and VSET/FALL as activities of their own, as CAPRI** (section 5). Nothing implemented
yet; in the agreed order after refactor stages 3-5. Items S1 and S2 of docs/design/STRUCTURAL_GAPS_PLAN.md. CAPRI's
code: capri_sources/gams (docs/EXTERNAL_SOURCES.md); every statement cites it. Where a statement is derived rather
than read, it says so.

## 1. What CAPRI does

### 1.1 Two technologies per crop (S1)

- **The set.** A = {T, T1, T2}: T1 the high-yield variant with more inputs, T2 the low-yield variant with fewer
  (capmod.gms l. 247-249; intens/techf.gms l. 39-42).
- **Which activities.** Every crop activity except grassland (TACT = EACT and CACT, without GRSACT = GRAE, GRAI,
  IHISGR, FALLGR; techf.gms l. 58-65). ISET and VSET keep T1/T2 levels without factors (l. 77-78, 107-108).
  Animals have T only (l. 114-117).
- **The factors (p_technFact, a relative change on T's coefficient; fixed in the code).**
  - Levels: T1 and T2 half each at the calibration point (techf.gms l. 69-70).
  - Outputs: T1 +20%, T2 -20% (l. 84-85); the "yield" row their sum over the main outputs (l. 87).
  - Inputs: +-25% (l. 93-94); irrigation water 0 (l. 96-97); plant protection +-40% (l. 102-103).
  - Nutrient need: the yield factor, +-20% (fert/fertned.gms l. 206-207); nutrient deliveries likewise (l. 314-318),
    for MANN only on the part that is not deposition or mineralisation (l. 324-335).
  - Sugar beet: quota shares 0.6 / 0.4 and its own variance terms (sugar/techf.gms l. 94-95, 103).
- **Levels.** T1 and T2 are separate variables; the activity is their sum (reports/sol_simy.gms l. 160). Their
  shares are free in simulation (fixTechfShares_ exists, supply_model.gms l. 4813-4817, but its flag is 0 except in
  sensitivity runs, def_supply_model_par.gms l. 51, sens/sens.gms l. 151).
- **Calibration.** The 50/50 split is an assumption, made optimal by the PMP terms: linear terms per technology from
  each technology's duals (supply/pmp_terms/define_const_pmp_param.gms l. 154-155); the 2x2 quadratic block per crop
  fitted so that the base shares respond with the activity's own slope, plus a definiteness term
  (declare_model_for_technology_matrix.gms l. 3, 20-41; compute_technology_pmp_matrix.gms l. 22). With equal shares
  the two diagonal terms are equal (AT11 soft wheat: 75.77 on the diagonal, -61.81 off it).

### 1.2 Where the technology matters in the supply model

- PMP objective: linear and quadratic terms per technology (QUADRA_, supply_model.gms l. 5284-5320); group terms on
  the sum.
- Revenues and costs: outputs and inputs x (1 + factor) per technology (l. 4585-4595, 4757-4759).
- Fertilisation: NUTNED_ per technology, need x multiplier x SQRT(1 + yield factor) x (1 + need factor)
  (l. 1095-1137): T1 about 1.31 times T's need per ha, T2 about 0.72 (derived: 1.2^1.5, 0.8^1.5); the same form in
  NUTMIN_, the crop deliveries and the N balances.
- Land, labour, feed: land sums over technologies; labour only through the PMP terms; fodder crops produce per
  technology, animals use T.
- Set-aside obligation per technology (techf.gms l. 137-146; MXSETA_, SETA_), irrigation per technology (l. 2534-2536).
- Tillage's yield effect through the T1 share (e_t1Mit_, l. 4197-4210): most probably not active (not in the model's
  equation list, supply_model_e_list_linear.gms l. 125-175; the second version is commented out).
- Reports sum over the technologies and weight the coefficients by their levels (sol_simy.gms l. 160, 373-389); the
  2030 reference results (dataOut) carry no per-technology levels (no 'T1' row in
  res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv), only a decomposition of yields ('Start', 'Techf', ...).

### 1.3 The split activities (S2)

- **Grassland: GRAE and GRAI**, one technology each, with their own PMP diagonal (AT11: 1015.3 and 947.2), in no PMP
  group; their need factor -0.2 / +0.2 inside NUTNED_'s square root (l. 1129); their own nutrient groups under
  NMINREST, else GRAS (supply/define_ngrp_sets.gms l. 22-27, 63-87).
- **Other fodder on arable land and fodder root crops: OFAR and ROOF**, each with T1/T2, in PMP group FARA with fodder
  maize; their own nutrient groups; OFAR carries the legume share's N fixation and CO2 option (l. 1112, 4051-4053)
  and a weight in the ecological set-aside (FLEG, l. 1970).
- **Set-aside: VSET and FALL**, each with T1/T2 levels and terms; VSET in the set-aside limit (MXSETA_, l. 2306);
  both in the landscape fallow (e_setaLandscape, l. 2315-2321) and the crop diversity group (sets.gms l. 3010-3012);
  FALL gets no fertiliser (fertned.gms l. 233).

## 2. What capri-mod does now

- **S1, one activity per crop.** CAPRI's T1/T2 quadratic block collapsed per crop (tools/build/build_pmp_capri_2030.py
  l. 10-14, 93-122; DEP-9).
  - Kept: the base point (by calibration) and, without other constraints, the response of the crop's total area: with
    equal diagonals (1,1) is an eigenvector of the 2x2 block, so the collapsed curvature equals CAPRI's along the
    total (derived).
  - Lost: the direction that moves the mix, T1 against T2 (curvature d - c, AT11 soft wheat 137.6): yield per ha
    (+-20% x the shift), inputs (+-25%), plant protection (+-40%) and N need per ha in response to prices, the N
    price and N targets. In CAPRI the N and land rows also tie the mix to the total.
  - Partly stood in for: a yield-price elasticity (capri_mod/supply/policy.py l. 203-249, the counterpart of CAPRI's
    supply/endog_yields.gms, a separate mechanism); under N caps capri-mod responds through the fertiliser options
    with yields fixed (fertilisation.py l. 668-673).
- **S2.** GRAS with a grassland split column (grass_z: GRAE = base share x GRAS + z; its own N, fodder and mineral-need
  coefficients, PMP term and linear term from the base duals; capri_mod/supply/livestock.py l. 137-195,
  tools/build/build_grass_intensity.py). OFOD = OFAR + ROOF with fixed shares in the nutrient groups. SETA = VSET +
  FALL, split for reports only (tools/build/build_labour_setaside.py; model.py).

## 3. The data

- CAPRI's 2030 quadratic technology blocks are in the repository (capri_data/sources/intermediate/baseline_pmp/
  pmp_quad_techn_2030.csv: T1-T1 5,624 rows, T1-T2 and T2-T2 5,417 each, T-T 6,294).
- The linear terms per technology are in the PMP export (capri_sources/pmp2030/pmppar_21730<CC>defaulta.txt), not
  yet extracted.
- The factors (p_technFact) are not in any export; they are fixed rules in the code (section 1.1), which a builder can
  write as a table with its citations (the MANN factor also needs p_nitrBalance's deposition and mineralisation).
- No per-technology levels at all: the base split is 50/50 by construction; a 2030 mix could perhaps be read from the
  yield decomposition rows (Techf / Start = 1 + 0.2 (s1 - s2); BL soft wheat: s1 about 0.501; an inference, not
  checked).
- The split activities are in both CAPREG's 2017 results and the 2030 reference (levels, yields, N, premiums).

## 4. Options

S1:
- **(a) Keep the collapse**, recorded with what it loses (above).
- **(b) T1 and T2 as two columns per crop**: their quadratic blocks and linear terms, the factors on outputs, inputs
  and N need, the set-aside obligation per technology, reports weighted by technology. The NUTNED_ need per hectare,
  the yields and the inputs follow the mix.
- **(c) One mix column per crop** (x1 = X/2 + z, x2 = X/2 - z), the way grass_z is built: a change of variables, so
  the same model as (b) exactly (derived), with the bounds x1, x2 >= 0 written as |z| <= X/2. The PMP separates into
  the total and the mix (with equal diagonals: (d + c) X^2 / 4 + (d - c) z^2); every per-technology coefficient is
  linear in X and z. Fewer changes than (b): the activity list, the land, feed and market code keep one column per
  crop; the mix enters the rows that depend on it (outputs, inputs, N need, set-aside obligation).
- **(d) A reduced-form intensity response** calibrated to CAPRI's T1/T2 (not CAPRI's structure).

S2, per pair:
- Grassland: the split column exists (grass_z); what is left is to check it against CAPRI's two activities.
- OFAR / ROOF and VSET / FALL: explicit activities, a split column like grass_z, or as now. OFOD would need OFAR's
  legume terms; SETA would need FALL's zero fertiliser and VSET in the set-aside limit.

What each would show at the gate: crop supply elasticities against CAPRI's own (supply_elas files), the yield and N
per ha responses to the F2F and GD targets.

Effort (an estimate, to be refined with the design): (a) none; (c) the largest single item of the plan after the
refactor of the supply code (agreed order: refactor first); (b) more than (c), for the same model.

## 5. Decision (1 November 2026)

The project lead chose:
- **S1: option (c).** One mix column z per crop that CAPRI gives T1 and T2 (TACT: EACT and CACT without grassland;
  ISET and VSET with levels only): T1 = X/2 + z, T2 = X/2 - z, the bounds T1, T2 >= 0 as |z| <= X/2. CAPRI's
  quadratic blocks and linear PMP terms per technology carried over by this change of variables, the factors of
  section 1.1 on outputs, inputs, plant protection and nutrient need entering through z, the set-aside obligation per
  technology, and reports with the technology levels T1 and T2 recovered from (X, z) and weighted as CAPRI's
  (sol_simy.gms l. 160, 373-389). The same model as (b), CAPRI's two columns: the change of variables is linear, so
  the solutions correspond one to one (derived); the total area keeps one column in the land, feed and market code.
  A departure of form, not of model, to be registered (the variables differ from CAPRI's v_actLevl per technology).
- **S2: the split activities explicit.** GRAE and GRAI (replacing GRAS with its grass_z column), OFAR and ROOF
  (replacing OFOD's fixed shares; OFAR with T1/T2, the legume share's N fixation and CO2 option, its weight in the
  ecological set-aside), VSET and FALL (replacing SETA; FALL without fertiliser, VSET in the set-aside limit), each
  with its own PMP terms, nutrient groups and CAPRI's data.

Order: after refactor stages 3-5 (the agreed order of 31 October 2026). The checks of section 4: the base reproduced
exactly, crop supply elasticities against CAPRI's own (supply_elas files), the yield and N per ha responses at the
F2F and GD gates. To be built first: the data (the linear PMP terms per technology from the PMP export, the factor
table with its citations, CAPREG's 2017 levels of the split activities).
