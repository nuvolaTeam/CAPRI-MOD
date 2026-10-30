# CAPRI's N loss cascade in capri-mod (20 October 2026)

## What is ported and how it was checked

* `tools/build/build_n_cascade.py` builds CAPRI's p_Nemidat (ghgAbatement on, endoLeach on, ammoLitRev on, ScenYear 2020)
  from the MITERRA / literature-review CSVs: `n_cascade_factors.csv` (per CAPRI region and animal activity),
  `n_cascade_region.csv` (runoff from the surface, leaching, mineral fertiliser; urea substitution's effect and
  maximum) and `n_cascade_effects.csv` (the options' othImpact on every gas and stage, runoff from housing no3runh,
  runoff from application no3mrun).
* `capri_mod/supply/n_cascade.py` writes GRAZN_, HOUSN_, STORN_, RUNHOUSN_, RUNSURFN_, APPLN_, RUNTOTN_, GASRUNTOTN_,
  GASTOTNETF_, RUNTOTNETF_ and GASRUNTOTNETF_ as they stand in supply_model.gms (plain arithmetic: floats and CasADi).
* Check (`test_n_cascade_reproduces_capri`, data `capri_data/validation/n_cascade_capri_gd2030.csv` from CAPRI's
  Green Deal reference run with endogenous technologies, `tools/build/build_n_cascade_validation.py`; that run is the "ini"
  calibration run, ghgTechCali ini, with the option shares at their initial values): with CAPRI's own
  option shares and winter cover share, NH3, NOx and N2O at grazing, in housing and storage (MAN) and at application,
  GASANI and RUNANI per head are reproduced to 1e-6 for the 18 animal activities of DE11, NL22, PL22 and DK (712
  values). Mineral fertiliser: NH3MIN, GASMIN, RUNMIN of DE11 exact; PL22 NH3MIN 1% off with the urea substitution
  share of one crop (CAPRI's regional v_Miti is not in the dump). Leaching (LEACHN_): see "Leaching" below.
* Found on the way, in CAPRI's results rather than its code text (REGISTERED):
  - anaerobic digestion: CAPRI's reported AD share is v_Miti x liquid share x (1 - grazing share) (sol_simy.gms
    l. 990-992), and its effects are rescaled by the same factor (ammo_tech.gms l. 2330-2345), so the literature-review
    value times the reported share is the effect per head (docs/AD_SPEC.md);
  - the application options' runoff effect no3mrun is weighted by applicability over manure systems (l. 2285-2291);
  - winter cover cuts the runoff share by 0.35 x its share (cover_crops.gms l. 400); tillage's runoff effects are
    commented out in CAPRI (tillage.gms l. 561-566);
  - CAPRI's code raises the initial covered-storage shares to the Nitrates Directive minimum (p_helpManStor,
    l. 2676-2709); its reference run does not show it (PL22 DCOL, NL22 PIGF), every other initial share of the four
    regions is reproduced (the run being the "ini" calibration run, whether a simulation run applies it is open;
    528 of 532 within 2e-4; DK dairy 4 off by CAPRI's group scaling to 1, done in
    build_ammonia_tech_model.py). Off as in CAPRI's results (`build_ammonia_technologies.APPLY_ENV_COVER`).
* endoLeach is on in capmod (capmod/set_global_variables.gms l. 55), not off as the ammonia builders had assumed:
  the concrete basin ManStorCon, the low cover on concrete CovStorLowCon and the pigs' AirPurCovLowC are now
  built (`tools/build/build_ammonia_technologies.endo_leach`, `tools/build/build_ammonia_tech_model.py`) with CAPRI's costs, initial
  shares and maxima (DE11 DCOL: ManStorCon 0.6052, CovStorHigh 0.2576, CovStorLowCon 0.0972, CovStorLow 0.0040 -
  CAPRI's reference run exactly).

## In the model

* `ammonia_techs.loss` is CAPRI's GasRunTot (all gases at all stages and the runoff) where the cascade has data, the
  NH3-only cascade elsewhere; `ammonia_techs.nh3` the NH3 part; `ammonia_techs.n2o` the N2O by stage.
* Manure N kept by the options (CAPRI's manExportOrAppl_: MANN x (1 - GasRunTot)) enters the manure applied in both
  forms (`_animal_n_kept`; NLP: `amm_kept` in ManureNPK_), NH3 kept the ammonia accounts (`_animal_nh3_saved`), and
  manure N2O follows the cascade's N2O by stage against the base shares (`_manure_n2o_full`).
* Anaerobic digestion: in the cascade and in the manure CH4 account (docs/AD_SPEC.md). Winter cover: in RUNSURFN_,
  APPLN_ and RUNTOTNETF_ (0.35 x share) and in LEACHN_.
* Not yet in capri-mod: tillage, buffer strips, biodiversity options and biochar (their LEACHN_ terms held at CAPRI's
  reference, below), the fertiliser techniques' N2OMAN/N2OSYN terms in APPLN_ and GASTOTNETF_ (the inhibitors' gas
  effects are applied in the accounts and the solve outside the cascade), urea substitution. Nitrates Directive
  minimum shares: not applied (KNOWN_ISSUES K51; CAPRI's NDtech is off in its Green Deal runs); the builder that built
  them from CAPRI's nvz.gdx was removed on 29 October 2026 with its data, read by no code (K102).

## Leaching and the indirect N2O of leached and run-off N (20 October 2026)

* `tools/build/build_n_leaching.py` -> `n_leaching_region.csv` per CAPRI region: leach_base (p_Nemidat(NITF, N, Leach,
  Surf) = rLFrest LFsoil; accumulation and mineralisation are 0 since MITERRA 120407, ammo.gms l. 664-669, so
  p_nitrBalance(Leach) is p_Nemidat itself), leach_ini (CAPRI's realised share LEACHI / SURSOI in its Green Deal
  reference with endogenous technologies: calc_nbalance.gms l. 290 reports LEACHI = SURSOI x v_nitrBalance.l), exp_imp
  (EXPPRD / IMPORT of CAPRI's 2030 reference). The run's regional N balance items are kept in
  `capri_data/sources/capri_res/gd2030_endotech_ini_nbalance.csv`.
* `capri_mod/supply/n_leaching.py`: LEACHN_ as L = leach_base x B1 x B2, B1 with the options capri-mod has (winter
  cover 0.35, nitrification inhibitors on mineral N and on manure through NO3SLEA / NO3MLEA x (1 - (1 - lit)(1 +
  NMIN)), the application options' v_ammoAppLeaAgg), B2 with those it has not (tillage, buffer strips, biodiversity,
  biochar) held at CAPRI's reference: L = leach_ini x B1 / B1_ini (REGISTERED). The fertiliser options' NO3 effects
  come from CAPRI's literature review (LitRevFertTech full dump; endoLeach on keeps them, ghgMiti.gms l. 568-573),
  weighted for manure as ghgMiti.gms l. 557-563 (`tools/build/build_fert_side_effects.py`).
* Accounts (`EnvironmentalModule.leaching`, `ghg_leaching_n2o`, `leach_share`, `n_runoff_leached`): gases.gms
  l. 696-745 allocated to crops - mineral runoff, manure surface runoff, leaching of mineral N, manure, deposition and
  residues, fixation - x EF5 (0.0075) x 44/28; the housing runoff stays with the animals (manure N2O factor f_lea).
  The inhibitor on manure's runoff effect (NO3MRUN) enters RUNSURFN_ there.
* Emission tax: the purchases carry the indirect N2O of their runoff and leaching at CAPRI's reference leaching share
  (`SupplyModel._ef_mineral_lea`, both forms; REGISTERED: the options' effect on the share is in the accounts only).
* Check (`test_n_leaching_follows_capri`): from CAPRI's own regional items, realised share and cascade, the formula
  gives CAPRI's crop N2OLEA within 6% for DE11, NL22, PL22, DK (-1.9%, +0.6%, -5.2%, +1.1%): CAPRI sums crop by crop
  (p_share_NMAN, crop MANN, NRET x BioFix), the check uses regional totals. At the base the share is CAPRI's (DE11
  0.1120, NL22 0.3220, PL22 0.1986, FRH0 0.2041); capri-mod's crop N2OLEA at its baseline is 10-40% above CAPRI's in
  DE11, NL22, PL22, FRH0 and 31% below in IE04, through its N balance items (mineral N: NL22 27.4 kt against CAPRI
  16.3, PL22 37.4 against 25.5).
* CAPRI-ERROR-FIX - sign of the application options in LEACHN_ (the project lead's decision, 20 October 2026; register FIX-2;
  `n_leaching.AMMAPP_SIGN`):
  - CAPRI's code: LEACHN_ (supply_model.gms l. 3413) ADDS v_ammoAppLeaAgg, the manure-weighted mean of the low-emission
    application options' no3mlea x share (AMMOAGG_, l. 3427). RUNSURFN_ SUBTRACTS the same options' runoff effect
    (no3mrun), and LEACHN_ itself subtracts the fertiliser options' leaching effects.
  - CAPRI's data: the literature table (prep_data_LitRev.gms, p_reducGains) gives reductions, positive = less loss:
    LNA_low liquid NH3 0.51, N2O -0.31, RunSurf -0.24, Leach -0.24; NI_min Leach 0.51. no3mlea is copied from it
    without a change of sign (ammo_tech.gms l. 2293), so v_ammoAppLeaAgg < 0 (DE11 -0.079, PL22 -0.033 at the initial
    shares; NL22 +0.004).
  - Consequence in CAPRI: adopting low-emission application LOWERS the leaching share, while its data (and its own
    runoff equation) say it raises it (N kept from volatilising stays in the soil).
  - capri-mod: subtracts it (AMMAPP_SIGN = "consistent", default); "capri" reproduces CAPRI's code. The base is
    calibrated to CAPRI's realised share (leach_ini) either way, so the sign acts only through changes in adoption
    (Farm-to-Fork: low-emission spreading about 42 -> 87% of manure N). We read CAPRI's '+' as a slip; nothing in
    the code documents it as intended.

---

# Spec: how CAPRI builds the p_Nemidat entries used by the supply-model N-loss cascade

GAMS root: `/home/claude/work/allgms/gams` (all paths below are relative to it unless stated).
CSV root: `/home/claude/work/capri-mod-proto/capri_data/2017/abatement/ammonia/` (called `AMM/` below).
This is a read-only investigation. Line numbers come from the files as they stand now.

---------------------------------------------------------------------------------------------------
## 0. Main finding: where the supply-model factors come from, and when the equations are used

1. **The equations only exist when `ghgAbatement = ON`.** GRAZN_ … LEACHN_ are listed in the model only inside
   `$iftheni.eqs %ghgAbatement%==ON` (`supply/supply_model_e_list_linear.gms:125-133`).
   * With `ghgAbatement = OFF` (the capmod default, `capmod/set_global_variables.gms:215`), CAPRI fixes
     `v_emiLoss = p_emiLoss` and `v_nitrBalance = p_nitrBalance` (`supply/set_supply_bounds.gms:217-219`). p_emiLoss is built in
     `envind/ammo.gms` Section C (lines 975-1096) from the **ManuType ("Liquid"/"Solid") p_Nemidat entries**.
     Those entries already include abatement through ControlStrategies.
   * With `ghgAbatement = ON` (e.g. `pol_input/greendeal/refpol_endotech_all_ini.gms:36`), the bounds are lo=0 and up=1
     (`set_supply_bounds.gms:240-247`). N2 is fixed to 0 except for "Stor" (line 244). The equations then use the **"av"/"AV"
     entries**, which are built in `envind/ammo_tech.gms:1911-1958`. That file is included only under
     `%ghgAbatement%==on` (`capmod.gms:1095,1113`). These AV factors are the *unabated* MITERRA/LitRev fractions. In the
     equations, abatement comes only through the `v_Miti × p_ghgMiti` terms.
   * p_Nemidat reaches the supply threads only when ghgAbatement is on
     (`supply/supply_model_thread_load_or_unload_values_constant_over_iter.gms:49`).
2. **Call order in capmod.** `capmod/create_sim_ini_gdx.gms:195` includes `envind/ammo.gms`, which produces the MS/RU
   p_Nemidat. The result is stored in sim_ini and reloaded by `capmod/load_sim_ini_gdx.gms:97`. Then `capmod.gms:1113`
   includes `envind/ammo_tech.gms`, which adds the AV entries plus the RU-level runoff entries for split activities.
3. **Globals in force in capmod (defaults):**

   | global | value | where set |
   |---|---|---|
   | endoLeach | on | `capmod/set_global_variables.gms:55` |
   | ammoLitRev | on | `capmod/set_global_variables.gms:58` |
   | storgrazInv | off | `capmod/set_global_variables.gms:61` |
   | leachIpcc | off | `envind/ammo.gms:25` (no other setter outside pol_input found) |
   | ScenYear | 2000, or **2020 if SIMY>2010** | `capmod/create_sim_ini_gdx.gms:176-178` |
   | ScenCAPRI | BA0AM0LN0, so ScenNVZ=cur and IPPCscenario=off | `envind/Miterra/scenario_settings.gms:73,95-96` |
   | ScenType | NN | `envind/Miterra/scenario_settings.gms:42` |

   For comparison, capreg uses ENDOLEACH OFF and ScenYear 2000 (`capreg/set_global_variables.gms:114`,
   `envind/Miterra/scenario_settings.gms:90`). So **CAPREG ex-post p_emiLoss is built with different factors** than capmod.
4. **Aggregation in the equations.** `R_RAGG(RALL,RALL1) $ MAP_RR(RALL1,RALL)` (`capmod/define_regional_sets.gms:306`). In the
   supply thread it is `R_RAGG(RU,MS)` (`supply/supply_model_thread.gms:321`). So for a NUTS2 region RUNR,
   `sum(R_RAGG(RUNR,MSACT), …)` picks the single parent member state. Entries indexed `(MSACT,…)` are therefore **MS-level
   values applied unchanged to every NUTS2 region of that MS**. Entries indexed `(RUNR,…)` are NUTS2-level.

---------------------------------------------------------------------------------------------------
## 1. Sets (file:line)

| set | definition | location |
|---|---|---|
| allmat | N,N2O,NOx,NH3,N2,NO3,CH4 | `envind/sets_ammo.gms:64-72` |
| NMAT (nmat) | N2O,NH3,NOx,N2 | `envind/sets_ammo.gms:74` |
| emmat_N (alias emmat_N1) | N2O,NOx,NH3 | `envind/sets_ammo.gms:76-83`; alias also in `ammo.gms:191` |
| map_gas_tag(allmat,mitiInfo) | NH3.(NH3HOU,NH3STO,NH3APP); NOX.(NOXHOU,NOXSTO,NOXAPP); N2O.(N2OHOU,N2OSTO,N2OAPP); N2.(N2HOU,N2STO,N2APP); CH4.CH4MAN | `envind/sets_ammo.gms:86-102` (a copy in `ammo_tech.gms:1759` is commented out with $ontext) |
| mitihous / mitistor / mitiappl | {NH3,NOX,N2,N2O}HOU / …STO / …APP | `sets.gms:9404-9429` |
| NemiFact | TypeShare, LossHous, LossStor, LossAppl, ReducFact, Runoff, Mineralis, Accumul, Leach, Denitri, BiofiltSh | `envind/sets_ammo.gms:32-45` |
| ALLTYPE | BIOFILT, LIQUID, SOLID, GRAZ, SURF, HIST, AV | `envind/sets_ammo.gms:48-57` (GAMS is case-insensitive, so "av"="AV", "Graz"="GRAZ", "Surf"="SURF") |
| ManuType | LIQUID, SOLID | `envind/sets_ammo.gms:59-62` |
| atModel | DAICOW_L/S, OCOW_L/S, PIGS_L/S, LAYHENS, OPOUL, SHEGOA, HORSES, FURANI, ORANI | `envind/sets_ammo.gms:115-129` |
| StorType | concrStor, fieldStor, othStor | `envind/sets_ammo.gms:131-135` |
| ft | Ureum, Other | `envind/sets_ammo.gms:104-108` |
| emmat / emmatNall / emmatN2 / emmatNH3NOx / emmatN2O | (N2O,NOx,NH3,N2,NO3,CH4) / (N2O,NOx,NH3,N2) / (N2) / (NH3,NOx) / (N2O) | `envind/Miterra/sets_miterra.gms:433-459` |
| ani_Liq(atModel) | DAICOW_L, OCOW_L, PIGS_L | `sets_miterra.gms:467-472` |
| atGrazingExtra(atModel) | DAICOW_L/S, OCOW_L/S, PIGS_L/S, HORSES, SHEGOA | `sets_miterra.gms:475-485` |
| ht / stt / ta | normal,HighEm,LowEm / Normal,HighEm,LowEm / Surface,HighEm,LowEm | `sets_miterra.gms:493-519` |
| ScenAppl | LNA_high, LNA_low | `sets_miterra.gms:544-547` |
| LFset | LFsurface, LFsoil, LFsoilRed, LFNmin, LFNacc | `sets_miterra.gms:549-555` |
| empl | HD, Ex, Et, Eh, Es, EaNH3, Eg, EaNOx, EaN2O | `sets_miterra.gms:572-582` |
| atModelMantype | ManType of each atModel (used for ReducEmAppl) | `sets_miterra.gms:594-606` |
| reg_to_RS(reg,*) | identity on SRNUTS2, plus CR000000→WBA regions, TK000000→TUR regions, ES700000→FR900000, DEE30000→DEE00000 | `sets_miterra.gms:387-395`; `rs_to_reg` is its transpose (`ammo.gms:205-206`) |
| **atModel_to_PACT(atModel,AACT)** (MITERRA→CAPRI) | DAICOW_L/S→DCOW; OCOW_L/S→SCOW,BULF,HEIF,HEIR,CAMF,CAFF,CAMR,CAFR; PIGS_L/S→PIGF,SOWS; OPOUL→POUF; LAYHENS→HENS; SHEGOA→SHGF,SHGM; HORSES→OANI | `sets_miterra.gms:920-948`; transposed as `pact_to_atModel` at `ammo.gms:197-198` |
| atModel_to_ManuType | *_L→Liquid; *_S, OPOUL, LAYHENS, SHEGOA, HORSES→Solid | `sets_miterra.gms:951-962`; transposed at `ammo.gms:202-203` |
| country_to_MS | identity on MS codes (BL000000 covers BE+LU, LU000000 commented out; NO000000 included) | `sets_miterra.gms:966-1013`; `ms_to_country` at `ammo.gms:194-195` |
| aniMitt(atModel) | DAICOW_S/L, OCOW_S/L, PIGS_S/L, LAYHENS, OPOUL, SHEGOA | `envind/ammo_tech.gms:1689-1701` |
| **map_ani_solid(atModel,cols)** (used by AV) | DAICOW_S→DCOL,DCOH,DCOW; OCOW_S→SCOW,BULL,BULH,BULF,HEIL,HEIH,HEIF,HEIR,CAMF,CAFF,CAMR,CAFR; PIGS_S→PIGF,SOWS; LAYHENS→HENS; OPOUL→POUF; SHEGOA→SHGF,SHGM | `ammo_tech.gms:1704-1728` |
| **map_ani_liquid(atModel,cols)** | DAICOW_L→DCOL,DCOH,DCOW; OCOW_L→(same cattle list); PIGS_L→PIGF,SOWS | `ammo_tech.gms:1730-1750` |
| gasCat | NH3,N2O,NOx,CH4,N2 | `ammo_tech.gms:1754` |
| MAACT | = MEAACT: DCOL,DCOH,BULL,BULH,HEIL,HEIH,SCOW,HEIR,CAMF,CAFF,CAMR,CAFR,PIGF,SOWS,SHGM,SHGF,HENS,POUF | `sets.gms:2274-2277`, MEAACT at `sets.gms:214-236` |
| DAACT | DCOW, BULF, HEIF | `sets.gms:249-254` |
| AACT | MAACT + OANI + DAACT | `sets.gms:2284-2290` |
| MACT | DCOL,DCOH,BULL,BULH,HEIL,HEIH | `sets.gms:2308` |
| MDACT | AACT minus MACT | `global/fromimpact/sets.gms:1015-1017` (same construction in sets.gms) |
| DACT_TO_PACT | DCOW.(DCOL,DCOH), BULF.(BULL,BULH), HEIF.(HEIL,HEIH), … | `sets.gms:3084-3090` |
| POULTRY(AACT) | HENS, POUF | `sets.gms:3113` |
| NUTS0 | member states | `sets.gms:7730` (ammo_tech's `nuts0` = MS level) |

---------------------------------------------------------------------------------------------------
## 2. Input parameters: GAMS source → CSV

Default (ammoLitRev = on) loads:
* `ammo.gms:241-248`: `%datDir%\miterra\LitRev_non_changeable_parameters.gdx` → RCEmissions, ControlStrategies,
  ReducControlStrategies, ControlStrat_TS, FracEmGrazing, FracNVZnuts2, FracNVZnuts2_full.
* `ammo.gms:285-292`: `LitRev_inputs.gdx` → ReducEmhouse, ReducEmStorage, ReducBio, FracEmHouse, FracEmStorage, EmFracFert,
  FracToepHouse, FracToepStorage, FracUseFert, FracEmAppl, NN_CorrFertFactDeviation, bNumAniRAINS, ScalarArray,
  rLFmanureBasis, rLFManureND, rLFrest, CorrND, rCorrND.
* `ammo.gms:253-264, 322-344`: Norway overrides from `mirror_non_changeable_parameters_norway.gdx` and
  `mirror_miterra_inputs_norway.gdx`.
* `ammo.gms:364` (endoLeach on): `input_manStor.gdx` → factRunStor, fracStorType. **This is the non-LitRev file.**
* `ammo.gms:367` (storgrazInv on only): `ghgInvData.gdx` → p_shareLiquidInv, p_shareGrazInv.
* `ammo_tech.gms:1873-1877` (ammoLitRev on): reloads `LitRev_inputs.gdx` as p_FracEmHouse, p_FracEmStorage, p_FracEmAppl,
  p_FracUseFert, p_EmFracFert, p_reducEm*. Also loads `LitRev_input_manStor.gdx` → p_factRunStor, p_fracStorType.

The CSVs were produced by `tools/build/build_ammonia_tech_inputs.py` from text dumps of the **LitRev** GDX files (docstring, lines
7-15). They are therefore the ammoLitRev = on data. The headers below were checked by opening each file.

| GAMS symbol (dims) | CSV | CSV columns → GAMS dims | units / notes |
|---|---|---|---|
| RCEmissions(country,atModel,empl) | `AMM/RCEmissions.csv` | region, animal_mitt, item(=empl), value | HD in days, Et in %. **Et is present for only ~55 regions** (e.g. none for DE, ES, IT, PL, PT); a missing Et counts as 0 |
| FracEmGrazing(country,atGrazingExtra,allMat) | `AMM/FracEmGrazing.csv` | region, animal_mitt, item(=gas), value | percent. N2O is *not* pre-adjusted; ammo.gms divides it by 0.8 (§3.2) |
| FracEmHouse(country,atModel,allMat) | `AMM/FracEmHouse.csv` | region, animal_mitt, gas, value | percent (/100 in code). N2O is already IPCC-adjusted in LitRev (`prep_data_LitRev.gms:311-319, 646-651`) |
| FracEmStorage(country,atModel,allMat) | `AMM/FracEmStorage.csv` | region, animal_mitt, gas, value | **fraction** (no /100 in code). Gases NOx, NH3, N2, CH4; **no N2O rows**, so storage N2O = 0 |
| FracEmAppl(country,atModel,allMat) | `AMM/FracEmAppl.csv` | region, animal_mitt, gas, value | fraction. N2O already pre-adjusted in LitRev (`prep_data_LitRev.gms:320`) |
| EmFracFert(country,allMat,ft) | `AMM/EmFracFert.csv` | region, gas, fertiliser, value | fraction. N2O already pre-adjusted (0.01/0.9 = 0.01111; `prep_data_LitRev.gms:321`) |
| FracUseFert(country,ft) | `AMM/FracUseFert.csv` | region, fertiliser, value | **overwritten before use** by NN_CorrFertFactDeviation(…,ScenYear) (`ammo.gms:531,535`) |
| NN_CorrFertFactDeviation(country,ft,ScenYear) | `AMM/NN_CorrFertFactDeviation.csv` | region, fertiliser, year, value | years 2000/2010/2020; capmod uses 2020 |
| bNumAniRAINS(country,atModel,ScenYear) | `AMM/bNumAniRAINS.csv` | region, animal_mitt, year, value | head counts; years 2000/2010/2020 |
| rLFrest(reg,LFset) | `AMM/rLFRest.csv` | region(=reg, NUTS2 8-char code), item, value | LFsurface in % (/100 in code); LFsoil is a decimal (no /100). Items present: LFsurface, LFsoil, LFNmin. LFsoilRed is computed in code |
| p_factRunStor(ManuType,stt,StorType) | `AMM/p_factRunStor.csv` | manure_system, tech_class, storage_type, value | percent. **LitRev variant** (see §5) |
| p_fracStorType(rall,ManuType,StorType) | `AMM/p_fracStorType.csv` | region, manure_system, storage_type, value | fraction (AV path does not use it) |
| ControlStrategies(country,atModel,ScenRains,ScenYear) | `AMM/ControlStrategies.csv` | region, animal_mitt, strategy, **item(=year)**, value | percent. ManuType path only |
| ReducControlStrategies(country,ManType,allMat,ta) | `AMM/reducControlStrategies.csv` | region, **animal_mitt(=ManType LIQUID/SOLID), strategy(=gas incl. "Leach"), item(=ta)**, value | fraction (negative = increase). Column names are mislabelled. ManuType path only |
| ReducEmhouse / ReducEmStorage / ReducBio | `AMM/reducEmHouse.csv`, `reducEmStorage.csv`, `reducBio.csv` | region, animal_mitt, gas, (tech_class), value | percent. ManuType path only |
| FracToepHouse / FracToepStorage | `AMM/FracToepHouse.csv`, `FracToepStorage.csv` | region, animal_mitt, tech_class, value | **overwritten** from ControlStrategies (`ammo.gms:514-527`). The CSV values (fractions) are never used |
| rLFManureBasis / rLFManureND / rCorrND / CorrND / FracNVZNuts2 / ScalarArray | same-name CSVs | as named | used only for LFsoilRed and rLFManure, i.e. endoLeach **off**. Not needed in capmod default |
| PercPeat | `AMM/PercPeat.csv` | region, value | not used by any p_Nemidat formula |

---------------------------------------------------------------------------------------------------
## 3. Formulas for every p_Nemidat entry the equations read

Notation: `TSL(ms,a)` = p_Nemidat(ms,a,"N","TypeShare","Liquid"); `TSG(ms,a)` = p_Nemidat(ms,a,"N","TypeShare","Graz");
c = country = ms (identity mapping); `S(a)` = the solid atGrazingExtra mapped to a, meaning atModel_to_PACT(at,a) and not
ani_Liq(at).

### 3.1 p_Nemidat(MS,MAACT,"N","TypeShare","Graz"): used by GRAZN_, HOUSN_, STORN_, RUNHOUSN_, RUNSURFN_, APPLN_
`envind/ammo.gms:604-613` (storgrazInv off):
```
TSG(ms,a) = Σ_{at∈atGrazingExtra, pact_to_atModel(a,at), not ani_Liq(at)} (1 − RCEmissions(c,at,'HD')/365) · (1 − RCEmissions(c,at,'Et')/100)
TSG(ms,a) = 0 for a ∈ POULTRY (HENS, POUF)
```
* The solid category is used: DCOW←DAICOW_S; cattle except dairy←OCOW_S; PIGF,SOWS←PIGS_S; SHGF,SHGM←SHEGOA; OANI←HORSES.
* The formula is set on DACT (DCOW, BULF, HEIF). It is copied to MACT (DCOL/DCOH/BULL/BULH/HEIL/HEIH) at `ammo.gms:1145`:
  `p_Nemidat(MS,MACT,*,*,*) = Σ_{DACT_TO_PACT(DACT,MACT)} p_Nemidat(MS,DACT,*,*,*)`.
* The storgrazInv=on branch (`ammo.gms:584-601`, from p_shareGrazInv 2017) is not the default.
* Inputs: RCEmissions (`AMM/RCEmissions.csv`).

### 3.2 p_Nemidat(MS,MAACT,emmat_N,"LossHous","Graz"): GRAZN_ (and RUNSURFN_ through v_emiloss Graz)
`ammo.gms:619-636`:
```
FracEmGrazing(c,at,'N2O') := FracEmGrazing(c,at,'N2O') / (1 − 0.2)          (line 619; applied in ALL settings, incl. LitRev)
LossHous_Graz(ms,a,NH3|NOX) = Σ_{at∈S(a)} FracEmGrazing(c,at,gas)/100                                    (621-625)
LossHous_Graz(ms,a,N2O)     = Σ_{at∈S(a)} FracEmGrazing(c,at,'N2O')/100 · (1 − LH_Graz(NH3) − LH_Graz(NOX)) (628-636)
```
Copied DACT→MACT at line 1145. Input: `AMM/FracEmGrazing.csv`.
Note: LitRev FracEmGrazing liquid ≠ solid (e.g. DE OCOW_L NH3 3.668 vs OCOW_S 14.046). The code comment "liquid = solid
here" (line 606/622) no longer holds, but CAPRI still uses the solid value.

### 3.3 p_Nemidat(MS,MAACT,"N","TypeShare","Liquid") (inside every AV factor) and "Solid"
`ammo.gms:710-737` (storgrazInv off). ScenYear = 2020 in capmod for SIMY > 2010:
```
TSL(ms,a) = bNumAniRAINS(c,X_L,ScenYear) / (bNumAniRAINS(c,X_L,ScenYear) + bNumAniRAINS(c,X_S,ScenYear))
    X = DAICOW for a mapped from DAICOW_L (DCOW); OCOW for OCOW_L (SCOW,BULF,HEIF,HEIR,CA**); PIGS for PIGS_L (PIGF,SOWS)
    (assigned only when the denominator ≠ 0; otherwise 0)
TS_Solid(ms,a) = 1 − TSL(ms,a)   for MDACT (line 736-737)
```
bNumAniRAINS(…,ScenYear) is first passed through the 2000/2010/2020 fill logic (`ammo.gms:453-470`), which is the identity
for ScenYear=2020. MACT is copied from DACT (lines 961-964 for MPACT where empty, then line 1145). Animals with no liquid
system (HENS, POUF, SHG*) have TSL=0. Input: `AMM/bNumAniRAINS.csv` (year column = 2020).

### 3.4 p_Nemidat(MS,MAACT,emmat_N,"LossHous","av"): HOUSN_
`ammo_tech.gms:1911-1913`:
```
LossHous_AV(ms,a,g) = Σ_{at: map_ani_liquid(at,a)} FracEmHouse(ms,at,g)/100 · TSL(ms,a)
                    + Σ_{at: map_ani_solid(at,a)}  FracEmHouse(ms,at,g)/100 · (1 − TSL(ms,a))
```
For g ∈ gasCat (NH3,N2O,NOx,CH4,N2). FracEmHouse has only N2O, NOx and NH3, so N2 and CH4 are 0.
* **N2O is not multiplied by (1−NH3−NOX) here.** HOUSN_ applies it to `(1−TSG) − (v_Hous(NH3)+v_Hous(NOX))` instead.
* The IPCC N2O re-scaling at `ammo_tech.gms:1895-1908` is skipped under ammoLitRev (the LitRev GDX is pre-adjusted).
* Input: `AMM/FracEmHouse.csv` (p_FracEmHouse, loaded at `ammo_tech.gms:1875`).

### 3.5 p_Nemidat(MS,MAACT,nmat,"LossStor","av"): STORN_
`ammo_tech.gms:1915-1917`:
```
LossStor_AV(ms,a,g) = Σ_liquid FracEmStorage(ms,at,g) · TSL + Σ_solid FracEmStorage(ms,at,g) · (1−TSL)     (no /100)
```
N2O = 0 (no data). N2 > 0 (0.01 liquid, 0.1 solid in DE). Input: `AMM/FracEmStorage.csv`.

### 3.6 p_Nemidat(RUNR,MAACT,"N","Runoff","av"): RUNHOUSN_ (NUTS2-level)
endoLeach on, `ammo_tech.gms:1937-1941`:
```
Runoff_AV(ms,a) = factRunStor('Liquid','normal','othStor')/100 · TSL(ms,a) + factRunStor('Solid','normal','othStor')/100 · (1 − TSL(ms,a))
Runoff_AV(RU,a) = Σ_{map_rr(ms,RU)} Runoff_AV(ms,a)          (= parent MS value)
```
With the CSV this is 0.20·TSL + 0.10·(1−TSL), so the only regional variation comes from TSL. It is defined for all AACT,
including MACT (TSL is already copied to MACT).
* CAPRI uses neither fracStorType nor storage technology shares here, unlike the ManuType runoff in `ammo.gms:879-885`.
* endoLeach off (capreg): `ammo_tech.gms:1946-1952` weights the RU ManuType runoff from `ammo.gms:891-904`
  (rLFManure) by TSL.
* Inputs: `AMM/p_factRunStor.csv` (only rows LIQUID/normal/othStor = 20 and SOLID/normal/othStor = 10; identical in the
  LitRev and original files) and TSL.

### 3.7 p_Nemidat(RUNR,MAACT,"N","Runoff","Surf"): RUNSURFN_, APPLN_ (NUTS2-level)
`ammo.gms:645-648`:
```
DATA(RS,DACT,"LEVL","Y") = Σ_{DACT_TO_PACT(DACT,MACT)} DATA(RS,MACT,"LEVL","Y")
RunoffSurf(RU,a∈MDACT) $ DATA(RU,a,"LEVL","Y") = Σ_{rs_to_reg(RU,reg)} rLFrest(reg,'LFsurface')/100
```
MACT at RU is filled in `ammo_tech.gms:1957-1958` from the DACT parent (only where it is still empty). The value does not
depend on the animal; it is conditional only on the activity having a base-year level. The MS-level version
(`ammo.gms:650-654`, unweighted mean over NUTS2) is only relevant when RUNR is an MS.

Hard-coded rLFrest fixes come before this step (`ammo.gms:310-316`):
* BL400000: LFsurface 6.850057, LFsoil 0.292021, LFNmin 8.237927
* DEE30000: LFsurface 2.214541, LFsoil 0.135434, LFNmin 7.714014. It reaches SRNUTS2 DEE00000 through
  `reg_to_RS("DEE30000","DEE00000")`.
* ES120000: mean of ES110000 and ES130000 where missing.

Input: `AMM/rLFRest.csv`.

### 3.8 p_Nemidat(MS,MAACT,emmat_N,"LossAppl","av"): APPLN_
`ammo_tech.gms:1925-1927` (the N2O /(1−0.2) at 1919-1922 is skipped under LitRev):
```
LossAppl_AV(ms,a,g) = Σ_liquid FracEmAppl(ms,at,g) · TSL + Σ_solid FracEmAppl(ms,at,g) · (1−TSL)
```
N2O is again "raw": APPLN_ subtracts v_Appl(NH3)+v_Appl(NOX) itself. Input: `AMM/FracEmAppl.csv`.

### 3.9 p_Nemidat(MS,"NETF",emmat_N,"LossAppl","AV"): GASTOTNETF_
Step 1, `ammo.gms:943-958`, with FracUseFert(c,ft) = NN_CorrFertFactDeviation(c,ft,ScenYear) (lines 531, 535):
```
Surf(ms,NETF,NH3|NOX) = Σ_ft FracUseFert(c,ft) · EmFracFert(c,gas,ft)
Surf(ms,NETF,N2O)     = Σ_ft FracUseFert(c,ft) · EmFracFert(c,'N2O',ft) · (1 − Surf(NH3) − Surf(NOX))
```
Step 2, `ammo_tech.gms:1930-1933`:
```
AV(ms,NETF,g)   = Surf(ms,NETF,g)
AV(ms,NETF,N2O) = Surf(N2O) / (1 − Surf(NH3) − Surf(NOX))   ( = Σ_ft FracUseFert·EmFracFert(N2O) )
```
GASTOTNETF_ then multiplies N2O by (1 − v_NH3 − v_NOX).

Inputs: `AMM/EmFracFert.csv` and **`AMM/NN_CorrFertFactDeviation.csv` (year 2020), not `AMM/FracUseFert.csv`**. This was
verified numerically in §6.

### 3.10 p_Nemidat(RUNR,"NETF","N","Runoff","Surf"): RUNTOTNETF_
`ammo.gms:657`: `= Σ_{rs_to_reg(RU,reg)} rLFrest(reg,'LFsurface')/100`. This one has no DATA condition. The MS mean is at
lines 659-662. Input: `AMM/rLFRest.csv`.

### 3.11 p_Nemidat(RUNR,"NITF","N","Leach","Surf"): LEACHN_
`ammo.gms:673-677`:
* endoLeach on (capmod): `= max(0, Σ_{rs_to_reg(RU,reg)} rLFrest(reg,'LFsoil'))`. **No /100.**
* endoLeach off (capreg): uses LFsoilRed = LFsoil·(1 − rCorrND(reg,'AFMAT')·NVZpart(reg)·ScalarArray('AFMATLFrest_'))
  (`ammo.gms:448, 473-477, 489-490`).

`envind/mod_leach.gms:327,333` overwrites it from p_LeachCapri only if leachIpcc=on (off by default). In
`ammo.gms:1105-1108`, p_nitrBalance(Leach) = min(L, L/(L+Accumul)), with Accumul unassigned (commented out at 669), so it
equals L for L ≤ 1. LEACHN_ uses p_Nemidat directly.

### 3.12 Other writers of p_Nemidat (none affect the capmod default)
* `fert/ferttrm_years.gms:95`, `envind/ammo_tseries.gms:190`, `capinv.gms:839-845`: time series and inventory
  (TypeShare overwrite from p_TypeShare).
* `envind/mod_leach.gms:327,333`: leachIpcc only.
* `capdis/disninput.gms:38`: CAPDIS zeroing.

Every other hit in the tree (gascoeff, gases, ghgMiti, ad_data_and_cali, line_nitr, digestibility, low_n_feed, grassMiti,
load_aes/cap_fp, bufferStrips, reports/miti_report, …) only reads p_Nemidat, mostly TypeShare and CH4 factors.

### 3.13 ManuType entries (p_emiLoss path / ghgAbatement off): for completeness
Hous `ammo.gms:770-804`; Stor `821-866`; Runoff ManuType `876-905`; Appl `918-939`; Section C p_emiLoss `975-1096`.
These use ControlStrategies(…,'SA'|'BF'|'CS_*'|'LNA_*',ScenYear), ReducEmHouse/Storage/Bio, ReducControlStrategies,
factRunStor×fracStorType×FracToepStorage. They are not read by the nine equations.

CAPRI quirk to know about: `ammo.gms:801` multiplies N2O housing by
`(1 − ReducFact_BIOFILT · p_Nemidat(MS,AACT,"N","TypeShare","BIOFILT"))`. That TypeShare/BIOFILT entry is never assigned
(probably meant to be "BiofiltSh"), so biofiltration never reduces housing N2O.

---------------------------------------------------------------------------------------------------
## 4. Quirks in how the equations consume the factors (replicate exactly)
* HOUSN_ N2O: `[(1−TSG) − v_Hous(NH3) − v_Hous(NOX)] · LossHous_AV(N2O) · …`. This is a product of animal-averaged factors,
  not the per-ManuType product used in ammo.gms.
* STORN_: the base is `1 − TSG − Σ_{emmat_N} v_Hous`. The NH3+NOX storage losses are subtracted only for **N2**, not N2O
  (storage N2O is 0 anyway).
* RUNHOUSN_: the base is `1 − TSG − Σ emmat_N v_Hous − Σ nmat v_Stor`.
* RUNSURFN_: `[TSG·(1 − Σ emmat_N v_Graz) + (1 − TSG − Σ nmat (v_Hous+v_Stor) − v_RunHous)] · RunoffSurf(RUNR) · (mitigation)`.
* APPLN_: for N2O, the NH3+NOX application losses are subtracted *inside* the bracket that is then multiplied by
  `(1 − RunoffSurf·…)`. So N2O_appl = (Rem − v_NH3a − v_NOXa)(1−ro)·f_N2O, where v_NH3a already carries (1−ro).
* GRAZN_ has no mitigation term. Its N2O factor already includes (1−NH3−NOX) (from §3.2).
* RUNTOTNETF_: `(1 − Σ emmat_N v_NETF_GasTot) · RunoffSurf_NETF(RUNR) · (mitigation)`.
* Units: all p_Nemidat are fractions of the N entering that stage. v_emiLoss are fractions of excreted N (MANN) or of
  mineral N. Reporting multiplies by MANN (kg N/head); N2O rows are then multiplied by 44/28.

---------------------------------------------------------------------------------------------------
## 5. Inputs missing or differing in the CSV data

The default ghgAbatement-on path (AV entries) has **no missing EU inputs**. All of FracEmHouse, FracEmStorage, FracEmAppl,
FracEmGrazing, RCEmissions, bNumAniRAINS, EmFracFert, NN_CorrFertFactDeviation, rLFRest and p_factRunStor are present.
These caveats remain:

1. **Norway (NO000000 and the NO NUTS2 regions).** CAPRI's ammo.gms loads these from `mirror_non_changeable_parameters_norway.gdx`
   and `mirror_miterra_inputs_norway.gdx` (`ammo.gms:253,322`). The data are absent from FracEmHouse, FracEmStorage,
   FracEmAppl, FracEmGrazing, RCEmissions, EmFracFert, FracUseFert, NN_Corr…, bNumAniRAINS, ControlStrategies and
   rLFRest. NO appears only in reducEmStorage, reducControlStrategies and p_fracStorType.
   *Uncertain:* ammo_tech.gms loads LitRev_inputs.gdx without the Norway mirror. If that GDX has no NO rows (as the CSV
   suggests), CAPRI's own AV factors for Norway would be 0.
2. **Hard-coded rLFrest rows** (BL400000, DEE30000→DEE00000, ES120000; `ammo.gms:310-316`) are in GAMS code, not in the CSV.
   They must be reproduced in code as CAPRI does. ES700000/FR900000, PT200000 and PT300000 get no rLFrest in CAPRI either.
   Turkey: the rLFRest keys are TR21…TRC3 and do not match CAPRI's TR100000… by `sameas`, so CAPRI also gets nothing
   unless `create_rawdat_miterra_gdx.gms` is run (not checked further).
3. **factRunStor variant.** `AMM/p_factRunStor.csv` is the LitRev file (`prep_data_LitRev.gms:940-958` rescaled the SOLID
   HighEm/LowEm rows to 3.68/7.36/7.36). `ammo.gms:364` (ManuType runoff, p_emiLoss path) reads the original
   `input_manStor.gdx` instead (SOLID HighEm/LowEm: fieldStor 10, othStor 2, no concrStor).
   * The original is **not in capri_data**. A raw GAMS text dump exists at `/mnt/user-data/uploads/input_manStor.csv`.
   * This does not matter for the AV path (it uses only the normal/othStor rows, which are identical). It matters only if
     the ghgAbatement-off p_emiLoss path is ported.
4. **p_shareLiquidInv / p_shareGrazInv** (`ghgInvData.gdx`): not in capri_data. They are needed only for storgrazInv=on
   (not the capmod default).
5. **The DATA(RU,MDACT,"LEVL","Y") condition** for RunoffSurf comes from the base-year activity levels (elsewhere in
   capri_data, not an ammonia input).
6. **CSV labelling traps:**
   * ControlStrategies.csv `item` = year.
   * reducControlStrategies.csv columns are (ManType, gas, ta), not (animal, strategy, item).
   * FracToepHouse/FracToepStorage CSV values are fractions but are overwritten anyway.
   * FracUseFert.csv is superseded by NN_CorrFertFactDeviation (2020).
   * Zero values are absent from the GDX dumps; for example FracEmStorage has 274 NH3 rows against 306 for the other gases.

Searched outside `AMM/` (grep -ril over capri_data for LitRev, miterra, ghgInvData, input_manStor, emiloss, nemidat): no
other copy of these inputs was found. There are only mentions in DATA_DICTIONARY.md, DATA_SOURCING_REGISTRY.json,
INPUT_MANIFEST.json and sources/gams/gams_extracted/*. Raw dumps also sit in `/mnt/user-data/uploads/` (LitRev_inputs.csv,
LitRev_non_changeable_parameters.csv, LitRev_input_manStor.csv, miterra_inputs.csv, non_changeable_parameters.csv,
input_manStor.csv), all GAMS text format. I found no Norway mirror files.

---------------------------------------------------------------------------------------------------
## 6. Validation targets and checks already done

### CAPRI's own regional totals (code)
* `reports/calc_nbalance.gms:69-139, 290-296` (simulation, uses v_emiLoss.l, falling back to p_emiLoss):
  * per activity: `DATA(RUNR,MAACT,"GASANI"|"RUNANI")`
  * per region (NITF, ×0.001): NH3ANI, NH3GRA, NH3HOU, NH3STO, NH3APP, GASANI, RUNANI, GASMIN, RUNMIN, NH3MIN, LEACHI = SURSOI·Leach
* `envind/gases.gms:244-289` (per head, MANN × share): NH3MAN = Hous+Stor, NH3GRA, NH3APP, NOXMAN, NOXGRA, NOXAPP. N2OMAN etc.
  are at lines 470ff (×44/28).
* `envind/calc_nbalance_cact.gms:157-190` is the CAPREG equivalent (p_emiLoss).
* For a ghgAbatement run, `capmod.gms:1642-1645` unloads p_nemidat, p_emiloss and v_emiloss.l to
  `%results_out%\permits\res_*.gdx`. That would allow a factor-by-factor check, but **no such GDX was found locally**.

### Result dumps in capri_data
* `capri_data/sources/capreg/capreg_nutrient_coefs.csv`: columns `model_region` (4-char, e.g. AT11), `activity`, `nutrient`
  (N/P2O5/K2O), `value`.
  * The "activity" column holds the balance rows NH3HOU, NH3STO, NH3GRA, NH3APP, NH3MIN, GASANI, GASMIN, RUNANI, RUNMIN,
    LEACHI, SURSOI, EXCRET, … for 186-192 regions. These are CAPREG 2017 DATA2 NITF rows.
  * They are **built with CAPREG settings** (ENDOLEACH OFF, ScenYear 2000, ManuType/p_emiLoss path), so they are *not* the
    capmod AV factors.
  * Units are presumably 1000 t N per region (calc_nbalance ×0.001). Not verified.
* `capri_data/validation/capri_eu27_refpol_endotech_{ini,max}_2030.txt` (ghgAbatement-on runs):
  * only the EU27yr19 aggregate is present
  * key `'EU27yr19'.'<''|perha|CUR>'.'<ROW>'.'NITF'.'2030'` for regional rows
  * key `'EU27yr19'.''.'<ACT>'.'<NH3MAN|NH3GRA|NH3APP|NOXMAN|N2OMAN|N2OAPP|…>'.'2030'` per head
  * **Caution:** the EU-level NH3APP NITF (5.89) and NH3GRA NITF (1.54) are implausibly small compared with the
    per-activity rows. Do not use those two aggregate rows without checking them.
* Derived ratio files from CAPRI 2030 results, `capri_data/2017/environment/`:
  * nh3_factors_capri.json (GNH3/MANN and NH3MIN/MINFER)
  * manure_housing_losses_2030.csv
  * manure_n2o_factors.csv (from res_17)
  * capri_gnb_components_2030.csv
  * capri_regional_n_balance_2030.csv

### Better dumps outside capri_data (NUTS2, includes the stage rows)
* `/mnt/user-data/uploads/res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv` (330 MB; the max run is in the
  matching zip). This is ghgAbatement ON (`pol_input/greendeal/refpol_endotech_all_ini.gms:36`), so it exercises exactly
  these equations.
  * layout `'REG8'.'<''|CUR|…>'.'<COL>'.'<ROW>'.'2030' value`
  * per-activity rows MANN, LEVL, NH3MAN, NOXMAN, N2OMAN, NH3GRA, NOXGRA, N2OGRA, NH3APP, NOXAPP, N2OAPP, GASANI, RUNANI
  * regional NITF rows NH3HOU, NH3STO, NH3GRA, NH3APP, NH3MIN, GASANI, GASMIN, RUNANI, RUNMIN, LEACHI, SURSOI, EXCRET
* `/mnt/user-data/uploads/res_2_1730greendeal_refdefaulta.zip` (ghgAbatement OFF, so the p_emiLoss path). Same layout.

### Checks done here (all exact to ~1e-13 against the CSVs)
* **GRAZN_ chain**, DE110000 endotech-ini 2030:
  * DCOL: MANN = 106.7653, TSG = 1−341/365, FracEmGrazing(DE,DAICOW_S) NH3 = 16.169, NOx = 0.3, N2O = 2.0/0.8. This
    reproduces NH3GRA 1.135093, NOXGRA 0.0210605 and N2OGRA 0.2303726 (= N-share × 44/28).
  * SCOW (OCOW_S, HD 314, NH3 14.046) reproduces 1.307239, 0.0279205 and 0.3131733.
  * This confirms HD/365, missing Et, solid-only selection, the N2O /0.8 and the (1−NH3−NOX) factor.
* **NETF gaseous loss and runoff**, refdefaulta DE110000:
  * NH3MIN/MINFER = 0.03632973. This equals 0.157998·0.15 + 0.842002·0.015 (NN_CorrFertFactDeviation 2020). FracUseFert.csv
    would give 0.036330.
  * FR10 in nh3_factors_capri.json = 0.047733154, matching NN (FracUseFert would give 0.046444).
  * GASMIN/MINFER = 0.05000384 = NH3 + NOx + 0.011111·(1−NH3−NOx).
  * RUNMIN/MINFER = (1−0.05000384)·LFsurface(DE110000)/100 = 0.03466217.
* **Leaching**, refdefaulta: LEACHI/SURSOI = 0.114217 (DE110000), 0.087275 (AT110000) and 0.132151 (FR100000). These are
  exactly rLFrest LFsoil, confirming endoLeach on → LFsoil with no /100.
* **Not verified exactly:** the housing, storage and application AV factors. In the endotech run the v_Miti initial shares
  modify them (e.g. DE11 DCOL NOXMAN/MANN = 0.0202 against an unabated estimate of about 0.0285). A permits GDX or
  v_Miti levels would be needed to close this.
