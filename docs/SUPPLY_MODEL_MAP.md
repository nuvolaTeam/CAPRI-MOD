# CAPRI star 3.0 regional supply model, equation by equation, against capri-mod

Status: revised 20 October 2026 against the code. Sections 1-3 map CAPRI's model; the capri-mod column describes the
NLP form (`capri_mod/supply/capri_regional_nlp.py`); notes on the conic form (Clarabel, removed 26 October 2026)
are history. Section 5 is the record of the decisions taken before the port (historical).

This map was step 1 of the rewrite of the regional model in CAPRI's NLP form (docs/archive/HANDOFF_NLP_PORT.md); the
design and the registered departures of the port are in `docs/NLP_PORT_DESIGN.md` and `docs/KNOWN_ISSUES.md` (K50,
K51). File:line references are to the star 3.0 source (`gams/`) unless they name a Python file. Points not verified are
marked "unsure".

## 1. What is solved, and with which switches

A CAPRI simulation solves `m_capModQ` with an NLP solver (CONOPT): `m_capMod` (supply/supply_model_e_list_linear.gms)
plus the quadratic list (supply_model_e_list_quatratic.gms) (supply_model.gms:5447-5469; supply_model_thread.gms:301).
The inner fertiliser model's equations are part of the same model (e_list_linear:233).

Which equations are live depends on switches. Two configurations matter:

| Switch | star 3.0 scenario run, default | Green Deal production batch (greendeal_scen2.txt -> greendeal_scenarios.gms) |
|---|---|---|
| Trustee land supply | on (GUI) | on |
| Inner fertiliser distribution model | on (GUI); NUTMIN_ then off (e_list_linear:61) | on |
| Manure trade (new module) | on (GUI) | on |
| Endogenous manure availability (`endoManAvFact`) | on (capmod/set_global_variables.gms:52; the comment above it says "off") | on |
| `ghgAbatement` (emission accounting, abatement options, endogenous N losses `v_emiLoss`) | off (set_global_variables.gms:215): the emission and abatement block is out, `v_emiLoss` fixed at parameters | on (pol_input/greendeal/refpol_endotech_all_sup.gms:36), with restMitFert on, winter cover and histosol options on, no emission tax (othPol 00) |
| `endoLeach` | on (set_global_variables.gms:55) | on |
| `lulucf_supply` | off | on (follows ghgAbatement) |
| LUC equations (land transitions) | on (task with market model and environmental reports) | on |
| Feed version | `_pw`: only REQSE_ (energy, protein) as requirement constraints | same |
| `PEST_DISAGG` (pesticide yield response) | off | off |
| `envConst`, `NMINREST`, BFP, water | off | off |
| CAP policy chain | the policy file decides (GUI default `mtr_rd_ref` looks legacy; CAP 2023-27 reference turns on the GAECs) | cap_after_2014 greening chain (permanent grassland, 5% ecological set-aside, crop diversification) |

capri-mod has no switch named ghgAbatement. Its abatement options are inside the regional model whenever
`use_manure_techs` is on (default True; feeding is always inside the models), baseline
included, so in this respect every default run is in the Green Deal configuration. Decision 5a.1 (off by default) was
not implemented that way.

## 2. Equations, by block

Status: same (CAPRI's form) / reformulated (same feasible set, other form) / approximated (different relation) /
missing / not needed (inactive in both configurations, or reporting only). GD = Green Deal.

### 2.1 Objective, costs, land

| Equation | Active | Form | capri-mod (NLP form) |
|---|---|---|---|
| LINEAR_, OBJEQF_ (objective) | yes | linear; with GD a tax term v_netPutQuant x v_emiLoss (bilinear, but the tax is 0) | approximated: net revenue per activity at current prices, no net-sales variables, premiums per unit; mineral N, P2O5 and K2O bought at CAPRI's unit values (the purchases of the fertilisation block). Emission tax: coefficients at the baseline solution (REGISTERED) |
| SUPBAL_ (output balances) | yes | linear; GD: x v_yldMit, x (1+v_Miti) bilinear | approximated: tradables folded into revenue; non-tradable fodder an equality (conic form: a band of 0.1% of base use) |
| INPANI_ (young-animal use) | yes | linear; GD bilinear with v_Miti | approximated: young animals valued per head at the young-animal market prices; no regional balance |
| GRPLEVL_, QUADRA_ (PMP cost) | yes | convex quadratic (technology matrix forced PD; group matrix PSD unsure) | approximated: capri-mod's PMPCalibrator (decision 5a.5): diagonal from CAPRI's elasticities with CAPRI's dampening and share term, off-diagonals from CAPRI's PELA cross-price elasticities or p_pmpQuadPact group terms (capped), a small uniform term elsewhere, clamps and diagonal dominance (`docs/PMP_ELASTICITY_WIRING.md`) |
| QUADRF_, QUADRF1_ (feed PMP) | yes | herd x per-head cost (bilinear) | same form; SLOP CAPRI's p_pmpFeedInpCoeff where available, CNST recalibrated so the base ration is optimal under REQSE_ (`calibrate_feed_terms`). Conic form: rotated cone in total feed |
| LandMarket_ (trustee land owner cost) | yes | convex quadratic | CAPRI's p_pmpQuadLandTypes, constants from the model's base; ARTIF fixed (`docs/LAND_USE_FLEXIBILITY.md`) |
| LandBalNoSlak_, e_artoBal, e_exogenousLand | yes | linear | same in substance: equality on changes from the base use, because the model's land data carry idle land |
| LandBalSlak_ (annual crops, ANNC) | yes | linear | not written: cropDivGreening_ takes the annual crops' sum directly |
| LUC block: e_landTypes_to_LUclass, e_FocLUC, e_derivativeOfGammaLUC, bounds, e_luClassInitial/Final | yes | non-convex (FOC system of the land-transition model, (alpha-1)/x terms) | CAPRI's transition model with its gamma priors, solved after each regional solve (`capri_mod/environmental/luc.py`); without a LULUCF price the block enters no other equation, so the result is the same (REGISTERED) |
| Greening: permGrasGreening_, ecoSetAside_, cropDivGreening_, winterCover_ | yes in the CAP 2023-27 reference and in the GD chain | linear; cropDiv log form (feasible set convex) | permGras: grassland >= base area; ecoSetAside: 5%, weights of cap_2013_2020_greening.gms, held at the base's own value where the model's base does not meet it (REGISTERED); cropDiv: Shannon index of the annual crop groups >= base, +1e-6 kha instead of 1e-10 (REGISTERED); winterCover_ as a row under the catch-crop requirement. Conic form: no permGras, ecoSetAside or cropDiv rows (the land market's grassland floor only) |
| e_setaLandscape, LscpFeatArea_ (landscape) | GD with lndscpTarg; CAP 2023-27 landscape floor | linear (GD: v_miti x uaa bilinear) | landscape floor: same rule; LscpFeatArea_ missing |
| sumEntl_, overShotEntl_ (entitlement ceilings) | GD chain yes (BPS ceilings); CAP 2023-27 unsure | linear | missing (premiums fixed per unit) |
| Set-aside (SETA_, SETAN_, MXSETA_, NONF_), sugar quota block, e_max/minLevl, BFP, fixTechfShares_, FixCosts_ | inactive (expected; sugar and set-aside data not inspected) | - | not needed |

CAPRI's activity bounds (supply/set_supply_bounds.gms: 0.1 to max(10 x, + 100) the data level) are variable bounds in
both forms (`RegionalSupplyModel.use_capri_activity_bounds`, K27); CAPRI's fixed activities are fixed.

### 2.2 Feeding

| Equation | Active | Form | capri-mod (NLP form) |
|---|---|---|---|
| REQSE_ (energy and protein need = feed x content) | yes, equality | linear; GD: products of two v_Miti (low-N feed x feed efficiency) | same: equality per head for energy and crude protein, requirement = the base ration's supply (CAPRI's trimmed p_animReq); split and option columns change the requirement in total form. Conic form: inequality (need <= supply) |
| REQSN_, MAXSHR_, MINSHR_ (dry matter, fibre, feed shares) | no under `_pw` | - | NLP form: none. The conic form keeps dry-matter and share rows (`feed_conic.py`), which CAPRI's simulation does not have; `feed/ration.py` uses them to calibrate the rations |
| FEDUSE_ (feed use = per-head x herd) | yes | non-convex (bilinear) | same (per-head feed x herd, entering the fodder balances). Conic form: total feed as the variable (same set) |
| SupplementPerc_ (fat share with linseed) | GD | linear | missing (REGISTERED; its effect on linseed's maximum share is in CAPRI's max-run caps) |
| FRMI, FPRI, FENI held at base per head | capri-mod only (no feed elasticity for them in pmp_elas.gms) | - | held at base per head; whether CAPRI fixes them is unsure |

Feed bounds: 0 <= per-head feed <= 10 x DRMX / dry-matter content (set_supply_bounds.gms), in the NLP form.

### 2.3 Fertilisation and nitrogen

| Equation | Active | Form | capri-mod (NLP form) |
|---|---|---|---|
| NUTNED_ (crop need per group and nutrient) | yes, equality per crop group and nutrient (N, P2O5, K2O) | non-convex for N: manure flow x v_ManureNPK / land (endogenous availability); GD adds v_emiLoss, v_Miti, v_yldMit products | same: equality per crop group and nutrient; need per ha = CAPRI's 2030 need x sqrt(yield / base yield) x a need multiplier per region and nutrient, calibrated at the base and fixed (REGISTERED, CAPRI's v_cropNutNeedMultFact is per crop group); mineral N x (1 + sum share NMIN) for the fertiliser options, manure N x (1 + share NMAN) for the inhibitor on manure. Conic form: one regional N row |
| Mineral purchases | v_netPutQuant(FNUT) <= 0 (purchase >= 0); each group's flow >= 0.001 x prior mode | - | same: purchases >= 0, flows within 0.001-1000 x their prior mode |
| Over-fertilisation | fixed at the base (v_cropNutNeedMultFact, prep_sim.gms:30); no free over-application in simulation | - | same in substance (the need multiplier is fixed) |
| NUTMIN_ | no with the inner model on | - | same (K40). In the NLP form the inner model is always inside |
| fertDistExcr_/Mine_/Cres_, ManureNPK_, manExportOrAppl_ | yes | linear (GD: v_emiLoss, v_Miti products) | same for N, P2O5, K2O: manure applied = excretion less CAPRI's housing and storage loss shares, net of trade, plus the N the ammonia options keep through the cascade; permanent groups take no residues from the pool |
| Inner model: e_fertDistPartial, e_focFertDist, e_fertDistPerHa | yes, part of every solve | non-convex (FOC system, bilinear) | same, inside every solve; duals within +-10, widened to +-1000 where a tiny group needs more (REGISTERED); where CAPRI's 2030 posterior admits no allocation at the model's base, CAPRI's fertiliser calibration (blanket priors) at that base (REGISTERED) |
| e_fertDistReguMax, e_fertDistPartialRegu (regulations: GD mineral caps by crop group, residue limits, organic) | GD | linear / non-convex | same: "f2f" caps on each group's mineral flow, "limCres" on residues (N, P2O5, K2O), caps from the model's own base allocation; the organic target's caps (organic_minfert_redu.gms) with capri-mod's conversion shares (REGISTERED); where the caps leave a group's need unmet, duals widened, then the groups concerned exempted one at a time at their baseline, CAPRI's p_checkSmallMine (REGISTERED, kept for the scenario, recorded as `nlp_relaxed`, e.g. `caps:PERM`). Conic form: their sum on one row (K49) |
| e_manureLimit_ | in the list with manure trade (e_list_linear:69), active only where p_manure_limit is set (supply_model.gms:1245; pol_input/manure/ManureNLimit*.gms): not by default, not in GD | linear | NLP form: none. The conic form adds a manure N limit (170 kg/ha or the base level) where an N target applies: not CAPRI's |
| e_netMTrade, e_costMTrade (manure trade) | yes | quadratic cost | same in substance: export and import columns with CAPRI's quadratic cost, CAPRI's country pools cleared between solves (`docs/MANURE_MARKET.md`); P and K follow N in the region's proportions (REGISTERED) |
| SURTOT_REST_ (GD surplus cap) | GD | linear in the surplus | same: the regional N-balance row with its mineral parts replaced by the purchases (e_SURTOTHa per ha of current land with `surplus_per_current_ha`) |
| e_synNMax (mineral cap per ha of land) | GD only with mineRedu "20", not with "NNcrp" | linear | same |
| e_minCoverCrops (cover crops) | GD (organic and pesticide targets) | linear | approximated: catch-crop area set at the requirement (no variable); its N enters as fixation |
| N-balance items e_EXCRET ... e_SURSOIkt | listed; bind via SURTOT_REST_ | per-ha x land, bilinear as written | approximated: linear accounts after the solve; the target row as above |
| InclEmiAppl_, nGrpLevl_, nMax_, lsDensMax_, nMin*, e_normalizeFertDist, NUTMAX_ | inactive or reporting | - | not needed |

### 2.4 Emissions, losses and abatement (only with ghgAbatement: the Green Deal configuration)

| Group | Decision-relevant? | Form | capri-mod (NLP form) |
|---|---|---|---|
| Loss cascade: GRAZN_, HOUSN_, STORN_, APPLN_, RUNHOUSN_, RUNSURFN_, RUNTOTN_, GASRUNTOTN_ (manure); RUNTOTNETF_, GASTOTNETF_, GASRUNTOTNETF_ (mineral) | yes: feeds ManureNPK_ and NUTNED_ | non-convex (v_emiLoss x v_Miti x v_Miti) | same (`capri_mod/supply/n_cascade.py`, p_Nemidat from the MITERRA tables; `docs/N_CASCADE_SPEC.md`), in both forms (the conic form takes its tangent at the previous solve); the N kept enters ManureNPK_. The fertiliser options' N2OSYN/N2OMAN terms of APPLN_ and GASTOTNETF_ act outside the cascade (REGISTERED) |
| GHG_Mit_Cost_, TotMit_, TotMitFertMin_/Man_, Tot_MitFert_, Tot_LineNitr_ | yes (objective, share limits) | non-convex (v_Miti x levels, squares) | same for the options built: ammonia options (housing and storage group, application group), anaerobic digestion, fertiliser options PRECFARM, VRT_SRUC, FERTTIME, NITR_INH (one regional share each; the conic form: one share per crop, REGISTERED), inhibitor on manure, breeding, low-N feed, linseed and nitrate. Missing: legume share, tillage (ConsTill, NoTill), urea substitution, 3-NOP, buffer strips, biodiversity options, biochar |
| catcMiti_, idleHisto_, ADMax_, SupplementPerc_, LANDSHARE_ | yes | non-convex (shares x levels, ratios) | winter cover: the share is the catch-crop share (CAPRI's 2030 value, or the requirement's), not a choice; histosol fallowing: a linear column (approximated); AD: CAPRI's maximum shares; SupplementPerc_ and LANDSHARE_ missing |
| Emission totals (GWP*, NH3*, NOX*, NO3*, LEACHN_, nmin/nmanInputSh_, AMMOAGG_, CO2SEQ, CARBERO_, LULUCF) | accounting only (no tax in GD) | non-convex products | computed after the solve. LEACHN_ in CAPRI's form in the accounts (`n_leaching.py`), with the sign of the application options changed (the user's decision, README 5.2); tillage, buffer-strip, biodiversity and biochar terms held at CAPRI's reference. Under an emission tax the purchases carry the indirect N2O of their runoff and leaching at the reference leaching share |
| envConst, FxAct*, CAP-linked technologies, pesticide disaggregation | off | - | not needed. The Nitrates Directive minimum shares are built from CAPRI's nvz.gdx but not applied (K51) |

## 3. Non-convex terms in CAPRI's model

Default configuration: FEDUSE_ (removable exactly), QUADRF_ (perspective, removable), NUTNED_ for N (manure x
endogenous availability), the inner fertiliser model's FOC system, the LUC FOC system, crop diversification (log form;
its set is convex), the N-balance per-ha definitions (bilinear as written).

Green Deal configuration adds: the loss cascade (v_emiLoss x v_Miti products), the abatement cost terms (v_Miti x
levels), v_yldMit x levels, v_Miti products in REQSE_ and NUTNED_, the regulations' beta terms, winter cover and histosol
shares x levels.

CAPRI's model is a non-convex NLP in both configurations; capri-mod's default form solves it as such (IPOPT from the
region's previous solution, as CAPRI's CONOPT restarts from the last solution).

## 4. Departures that remain

The registered departures of the NLP form are listed in KNOWN_ISSUES K50 (14 items) and K51; the user's two decisions
against CAPRI's code are in README section 10.2c. In terms of this map, the ones that change the equations rather than
their data:
1. PMP and land-market matrices: capri-mod's calibration, not CAPRI's p_pmpQuad* values (decision 5a.5).
2. SUPBAL_/INPANI_: no balances for sales and young animals in the regional problem (values per unit).
3. One need multiplier per region and nutrient in NUTNED_.
4. LUC solved after the regional model.
5. Options not built (2.4), SupplementPerc_, LscpFeatArea_, entitlement ceilings; winter cover not a choice.
6. Emission tax with coefficients at the baseline solution.

## 5. Decisions taken before the port (historical record, project lead, 20 October 2026)

Questions raised by the map, and the decisions:

1. Emissions and abatement block (`ghgAbatement`): as CAPRI, off by default, on in the Green Deal configuration.
   In the code (20 October 2026) the options are on by default (section 1).
2. Scope: the default configuration and the Green Deal block together in the first version. Done.
3. P and K: in the crop need (NUTNED_ per nutrient), as CAPRI. Done (`tools/build/build_npk_balance_2030.py`, CAPRI's 2030
   reference).
4. LUC transition model, ecological set-aside and crop diversification: in the first version. Done in the NLP form
   (`tools/build/build_luc_2030.py`, `tools/build/build_cap_greening.py`).
5. PMP and land-market matrices: capri-mod's own calibration for now. As decided.

The data the map listed as needed (P and K needs and excretion, LUC transition matrix, greening limits, the Green Deal
abatement block's inputs) were supplied from the CAPRI installation; each builder in `tools/` names its source.

## 6. Documentation corrections found while mapping

- KNOWN_ISSUES K49: "CAPRI allows manure beyond the need" was wrong (over-fertilisation fixed at the base); corrected
  in K49.
- docs/archive/FEED_IN_SUPPLY.md: its share and dry-matter rows are not in CAPRI's `_pw` simulation (the document is
  archived; the NLP form has none).
- docs/FERTILISER_ALLOCATION.md: NUTMAX_ is in no equation list; corrected there.

## 7. Not determined

Policy file of a "default" star 3.0 scenario; whether set-aside, sugar quota and entitlement data are zero in 2030;
whether the LUC FOC system binds land without a carbon price; PSD of CAPRI's group PMP matrix; whether the fertiliser
prior modes are reset each market iteration; how far the Green Deal fixings (FixMiti, set_miti_bounds) leave the
non-convex abatement terms live; whether CAPRI fixes FRMI/FPRI/FENI and how it treats straw and COMF feed losses.
