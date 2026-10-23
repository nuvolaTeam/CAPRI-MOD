# CAPTRD (CAPRI star 3.0) — code map for the capri-mod design spec

Source tree: `/home/claude/work/allgms/gams` (all paths below relative to it; `captrd/x.gms:N` = file:line).
Entry point: `captrd.gms` (1437 lines). Farm-type disaggregation is a **separate entry point** `captrdfrm.gms` (869 lines).
Doc cross-check: `caprijan2022.pdf` §4.3 (pp.148–166) was available (`/mnt/user-data/uploads/caprijan2022.pdf`); where doc and code differ, the code is reported and the difference flagged.
Conventions: `p_data(r,col,row,t)` = input/statistics cube; `p_result(r,col,row,t,respos)` = result cube; `V_EstV(r,col,row,t)` = the single estimated variable family; `exAnteY` = the one year being solved.

---------------------------------------------------------------------------------------------------

## 1. Control flow

### 1.1 Include / execution order of `captrd.gms`

| # | Line(s) | What |
|---|---|---|
| 1 | 40 | `util\global_settings.gms` (sets `%NoProc%`=2 at util/global_settings.gms:21) |
| 2 | 60 | `fortrd.gms` — GUI-generated settings file. **Not present in the tree** (not found); defines `%RESDIR%`, `%FirstYear%`, `%BaseYear%`, `%lastSimulationYear%`, `%TASK%`, `%regLevel%`, `%AGLINK%`, `%SelecLongRunScen%`, `%ScaleToDGAGRI%`, `%RUNSTEP3%` etc. (inferred from use, values unknown) |
| 3 | 71–81 | GUI branch (`%ggig%`=on): `%sim%`, `%ntslvl%` 0 (countries) / 2 (NUTS2) |
| 4 | 86–177 | hard-coded `$setglobal` switches (table 1.3) |
| 5 | 120, 128 | `global\set_base_longrun_scen.gms`, `baseline\aglink_versions.gms` |
| 6 | 184, 186 | `sets.gms`, `reports\aggreg_sets.gms` |
| 7 | 194–224 | `YEARS = %FirstYear%*%lastSimulationYear%` (203); `RESY = simulationYear` (211); `MSINCL = countries` (217) |
| 8 | 240 | `captrd\sets_captrd.gms` |
| 9 | 245–255 | `%lst_dgagri%` (2030; 2040 for aglink2022/23/24dgAgri); `exAnte(RESY)=YES` (255) |
| 10 | 265–272 | `OrdT(t)=calendar year`; **trend variable `p_trend(YEARS)=ORD(YEARS)/10`** (271) |
| 11 | 297–301 | declare `p_data`, `p_result` |
| 12 | 312–319 | optional GLOBIOM tight-link load |
| 13 | 327–336 | `p_infl`=1.019, `p_extrapMinMax` min .75 / max 1.25 |
| 14 | 341/343, 349, 369 | biofuel technology params, livestock units, `feed\feed_decl.gms` (only `p_reqfcnlim`, `p_carcassShare`, `p_startWgt` kept, 371–405) |
| 15 | 419–519 | load CAPREG time series per MS, column/row filters |
| 16 | 525–581 | load CAPREG base-year data (→ `"BASM"`) |
| 17 | 590–632 | agmip (opt.), **Aglink loader `baseline\load_%AGLINK%.gms`** (606), population, nutrient contents |
| 18 | 642–661 | current EU aggregate sets |
| 19 | 667–705 | time sets I: ExPost, Lst_Expost, Lst_DGAgri, Lst_exAnte, BASYRS5, BASYRSM, EIGHTLST |
| 20 | 714–715 | `captrd\load_coco1_data.gms` (switch `%COCO1%`) |
| 21 | 721–813 | time sets II: ExPostT, Fst/Sec_exAnte, ExAnteD/T, BAST, BASYRST, Before, YearsCur, YearsEst |
| 22 | 819 | `captrd\load_eurostat_milk_data.gms` (switch `%milk_RegioData%`) |
| 23 | 828 | `captrd\check_and_cor_capreg.gms` |
| 24 | 833–898 | data cleaning (drop non-estimated series, EU-10 <1992, BUR/WBA <1995, DE <1992, UVAD fill-ins, labour LABH=LABO−LABN) |
| 25 | 902 | `baseline\labour_ageline.gms` |
| 26 | 906 | `captrd\captrd_policy.gms` (milk & sugar quotas, set-aside) |
| 27 | 934 | `captrd\equations.gms` (models m_trendMS, m_trendNT2) |
| 28 | 937 | `captrd\prep_data_for_estimation.gms` (nObs, nW, wAve, wVar, BAS, BSY …) |
| 29 | 943 | `captrd\prep_requirement_estimation.gms` (linear feed-requirement regressions) |
| 30 | 953 | `captrd\scale_DG_AGRI_baseline.gms` (BAST; DGAgri → DGAgri1) |
| 31 | 964 | **Step 1** `captrd\estimate_trends.gms` (only if `%FARM_B%`=off; it is OFF at 86) |
| 32 | 967 | `captrd\define_stats_and_supports.gms` (→ includes expert_support → agriprod/national/longrun supports) |
| 33 | 1011 | `$IF %RUNSTEP3% == OFF $exit` |
| 34 | 1024–1153 | **year loop** `LOOP(exAnte, LOOP(iSolve $ p_activateStep(iSolve), …))` |
| 35 | 1250 | `captrd\aggreg_and_report.gms` |
| 36 | 1256 | `captrd\estimate_eu_trade.gms` (writes Aglink_for_capmod) |
| 37 | 1269–1320 | labour post-processing, fossil fuels, INHA, SERIES |
| 38 | 1325–1383 | merge with existing results file, write `results_…gdx` |
| 39 | 1393–1417 | write one `trends_<BAS><YY>…gdx` per RESY year |

### 1.2 The steps in the code (vs. the doc’s Step 1–4)

Inside the year loop (captrd.gms:1024–1153), each `exAnte` year is processed **sequentially, in ORD order**, with two solves:

| Doc step | Code | Where |
|---|---|---|
| Step 1 – independent trends | closed-form WLS + grid on c, all years at once | estimate_trends.gms (captrd.gms:964) |
| Step 2.1/2.2 – consistency + MS expert supports | `iSolve="Solve1"`: m_trendMS per MS with supports from define_stats_and_supports (trend/R², COCO "nowcast", expert, national, AgriProd, long-run, **plus DGAgri1 prices already**, define_stats_and_supports.gms:355–359) | captrd.gms:1041–1060 → estimate_ms.gms; results → `p_result(…,"Step2")` (define_eu_supports.gms:43–45; or captrd.gms:1141 for MSEXCL) |
| Step 3 – EU-level supports (Aglink / long run) | `define_EU_supports.gms` after Solve1, then `iSolve="Solve2"`: same m_trendMS with new supports/trust levels | captrd.gms:1063–1072, 1060; results → `p_result(MS,…,"Step3")` (1085–1088) |
| Step 4 – MS → NUTS2 | inside Solve2 branch, `estimate_NUTS2.gms` if `%NTSLVL%` ≠ 0 | captrd.gms:1101 |
| Step 4 – NUTS2 → farm types | **not in captrd.gms** (`%FARM_B%` OFF, 86); separate task `captrdfrm.gms` (FARM_B/FARM_M ON, captrdfrm.gms:47–48) reading CAPTRD output | captrdfrm.gms:243, 337 |

Debug variants: `p_activateStep("Solve2")=0` runs only Solve1 (captrd.gms:993–996; estimate_ms.gms:516–523 then stores Step2); `p_estimate_MSnogrid=1` runs `estimate_MSnogrid.gms` for `MSnoGrid` (SI) (captrd.gms:1000–1004, 1057–1059).

### 1.3 Switches (`$setglobal` hard-coded in captrd.gms unless noted “GUI”)

| Flag | Default | Line | Effect |
|---|---|---|---|
| `%ggig%` | GUI | 71, 194 | GUI-driven sets and globals |
| `%regLevel%` → `%ntslvl%` | GUI | 78–79, 197–198 | 0 = countries only; 2 = NUTS2 step (1101) |
| `%RUNSTEP3%` | GUI | 1011 | OFF: stop after Step 1 + supports |
| `%FARM_B%` | OFF | 86 | farm-type mode (only captrdfrm) |
| `%agmip%` / `%WaterModule%` | off | 89–92, 590 | IMPACT yields |
| `%constBionergy%` | on if SelecScen=brightspace | 97 | biofuel_trends.gms:1299 |
| `%IntegrateCapregFiles%` | off | 101, 518, 545–546 | only merge CAPREG files and exit |
| `%NewBiofuelModule%` | ON | 107 | biofuel params, biofuel_trends.gms, p_biofuelData |
| `%Beet_RegioData%` | off | 110, 507 | regional sugar beet data |
| `%milk_RegioData%` | Off | 113, 819 | Eurostat regional milk |
| `%mlkQutExpiry%` | 2009 | 116; captrd_policy.gms (`$if setglobal mlkQutExpiry`) | milk quotas zeroed after this year |
| `%SelecScen%` | = GUI `%SelecLongRunScen%` | 124 | long-run source (GLOBIOM scenario) |
| `%FAOstatUpdate%` | ON | 137 | FAO code system |
| `%GlobiomAact%` | off | 140 | use GLOBIOM herd info |
| `%stronglycutNECR%` | off | 143 | |
| `%aglinkTightLink%` | off | 146 | tighter DGAgri bounds/trust (estimate_ms.gms:127–154; define_eu_supports.gms:413–469, 730, 748, 758, 782) |
| `%consBioTrends%` | Off | 152–154 | conservative EU biofuel trends (POTENCIA); incompatible with `%scaleToDGAGRI%` (GUI) |
| `%FixExogenFactGlobiom%` | ON only for 3 SSP scenarios | 157–161 | fixes yields/feed efficiency to GLOBIOM |
| `%phaseInYr%` | 2025 (2030 for aglink2022dgAgri or tight link; 2010 if FixExogenFactGlobiom) | 166–169 | start of long-run phase-in |
| `%use_KWS_supports%` | off | 173 | |
| `%sugar_quotas%` | on | 177 | |
| `%lst_dgagri%` | 2030 / 2040 | 245–248 | last year with Aglink supports |
| `%lst_daitar%` | 2020 | 260 | last year of DG AGRI dairy targets |
| `%AGLINK%`, `%AGLINK_scen%` | GUI (fallback aglink2012dgAgri) | 597, 602, 606 | Aglink loader version |
| `%COCO1%` | ON | 714–715 | load COCO data for recent years |
| `%useAgriInfo%` | ON for tight link and listed scenarios | expert_support.gms:351–363 | DG AGRI dairy targets |
| `%correctdairyaglink%` | on | expert_support.gms:490 | rescale dairy growth to Aglink |
| `%scaleToDGAGRI%` | GUI | biofuel/biofuel_trends.gms:637 | scale biofuels to DG AGRI |
| `p_activateStep`, `p_estimate_MSnogrid` | 1/1, 0 | 993–1000 | scalars, not $setglobal |

---------------------------------------------------------------------------------------------------

## 2. Inputs (data shopping list)

`%results_in%` = output tree of earlier CAPRI tasks; `..\dat` / `%datdir%` = static data folder.

### 2.1 Core, always loaded

| # | File | Symbol(s) read → target | Dim | Where |
|---|---|---|---|---|
| 1 | `%results_in%\capreg\res_time_series_%BAS%<MS>.gdx` (one per MS, loop over **all** MS) | `DATA1` | (NUTS0_and_2ext, db_cols, db_rows, Years) | captrd.gms:486, 497–501; copied to `p_data(r,COLS_LOAD,ROWS_LOAD,Years)` 504 (COLS_LOAD/ROWS_LOAD filters 419–481) |
| 2 | `%results_in%\capreg\res_%BAS%<MS>%addfile%.gdx` (per MS) | `DATA2` | (rall, cols, rows, Y) | 528–537 → `p_data(…,"BASM")` for S_ColsEst/REQSC × S_RowsEst (554–555) + N_EXPT, SETR, STCM.OYANI, EDAYS, DRMN·DAYS, DRMX·DAYS (574–580) |
| 3 | `%results_in%\coco\coco2_output.gdx` (**note: COCO2 output file, despite the include name**) | `DATA2` → `dataMS` | (MS, cocoItem∈{ini,coco1,coco2}, cols, rows, years) | load_coco1_data.gms:19–26; only item `'COCO1'` used |
| 4 | Aglink: `baseline\load_%AGLINK%.gms`; e.g. for aglink2024dgAgri: `..\dat\baseline\aglink2024dgAgri_oriEUdata.gdx` | `c, c_eq, m, m_eq, p, p_eq, p_dbvar` (compile-time `$load`) | — | baseline/load_aglink2024dgAgri.gms:54–61 |
|   | same loader: `..\dat\baseline\AGLINK2019dgagri_oridata.gdx` | `p_fish` | 4-dim | :202 |
|   | `%DatDir%\baseline\ctrcode.gdx`, `aglink2024macro.gdx` (`p_aglinkMacroEU`), `..\dat\global\GlobiomCountry.gdx`, `GlobiomCountry_FAOreg.gdx`, `FAOreg_AGLINKregions.gdx`, `..\dat\baseline\data_SSPV3_update.gdx` (`SSP_data`), `%results_in%\global\fao_agg_%BAS%_%reg_agg%%ResId%.gdx` (`p_mediumTermData`) | | | :910–969 |
|   | **result**: `p_result(EuropReg,cols,rows,years,'DGAgri')` (EU aggregates/EuropReg, not MS); EXPT/IMPT of EU regs set 0; negatives→0 except NTRD | | | :1432–1443 |
| 5 | `..\dat\arm\allpop.gdx` | `WorldPop` | (Years, MS) | captrd.gms:611–616 (fallback population) |
| 6 | `%datdir%\arm\nutrient_cont_usda.gdx` | `p_nutrientCont` → `p_NCNC_CONT(rows,ncnc)` | (rows, usda_cont) | 621–632 |
| 7 | `%results_in%\global\fao_agg_%BAS%_%reg_agg%%inputDataId%.gdx` | `p_biofuelData`, `p_aglinkGrowthFactor` | 4-dim each | load_coco1_data.gms:356–360 (if NewBiofuelModule) |
| 8 | `%results_in%\global\longrun_info_fac_%reg_agg%.gdx` | `p_longRunInfoAll` | (RMALL, cols, rows, info, longScen, *) | longrun_supports.gms:105 (only if `OrdT(lst_exAnte) ≥ lst_dgagri`, :100) |
| 9 | `..\dat\baseline\ageline.gdx` | `AGELINE` | — | baseline/labour_ageline.gms:26 |
| 10 | `..\dat\coco\Agri_Prod.gdx` | `p_agriProd` | (msAgriprod, agriprod, itemAgriProd, simyy) | agriprod_supports.gms:216, 229 |
| 11 | `%datdir%\baseline\recent_mlk_yld.gdx` | `p_recentMlkYld(rAll,simyy_ybas)` | 2-dim | read expert_support.gms:478; **written in the same run** by agriprod_supports.gms:322 (order: expert_support includes agriprod later at :771, so the file read at :478 is the one from a previous run unless present) |

### 2.2 Policy, technical coefficients (GAMS include data)

| File | Content | Where |
|---|---|---|
| `..\dat\biofuel\biofuel_technology_params.gms` (or `processing_coeff.gms`) | biofuel processing coefficients | captrd.gms:340–344 |
| `..\dat\policy\livestock_units.gms` | `p_LUUnits` | 349 |
| `feed\feed_decl.gms` | `p_reqfcnlim`, `p_carcassShare`, `p_startWgt` | 369 |
| `pol_input\mquota_update.gms` → `%datdir%\coco\milk_quota_dat.gms` | milk quotas → `p_data(MS,Quotas,"COMI",t)` | captrd_policy.gms:40; pol_input/mquota_update.gms:29 |
| `sugar\load_quotas.gms` → `%datDir%\sugar\squotas.gms, sqrenounce.gms, sqcbuyback.gms, sqwithdraw.gms`; `policy\reformsugarquotas.gms` | sugar quotas → `p_data(MS,"QUTS","SUGA",t)`; SUGB quotas derived; NUTS2 split by base-year shares | captrd_policy.gms:51–52, 60–>; sugar/load_quotas.gms:24–27 |
| `..\dat\policy\smal_pshar.gms` | small producer shares (set-aside) | captrd_policy.gms:168 |
| hard-coded `Proc_Yields` (soy/rape/sun cake & oil) | ±5% prior for processing yields | captrd.gms:355–361 |
| hard-coded `p_coefHFCS` SUGA .92, MAIZ .60 | isoglucose | baseline/load_aglink2024dgAgri.gms:43–46 |

### 2.3 Expert / long-run / biofuel (all via define_stats_and_supports → expert_support.gms)

| File | Symbol | Where | Switch |
|---|---|---|---|
| `..\dat\baseline\dairy_targets_agri.gms` | `p_nrCows, p_CowMilkProd, p_milkDeliveries, p_dairyCowYield` (ms_agri, years) | expert_support.gms:370 | `%useAgriInfo%` |
| `..\dat\baseline\necp_expert.gms` | `p_fromNECP(NUTS0,xpCols,simyy)` → `p_natExpert` | national_supports.gms:149–150 | not tight link |
| `biofuel\biofuel_trends.gms` | — | expert_support.gms:114 | NewBiofuelModule ON (else `Bio_trends_%Aglink%.gms`, :111) |
|  → `%datdir%\biofuel\%primesBiofuelFile%.gdx` | `p_primeswithunits` | biofuel/biofuel_trends.gms:240–243 | |
|  → `..\dat\bioFuel\fossilFuel.gdx` | `p_fossilFuel` | :413 | |
|  → `..\dat\biofuel\biofuel_data.gms` | | :1344 | |
|  → `%datdir%\biofuel\POTENCIA_processing\POTENCIA_transport_energy_outlook.gdx` | `countriesPOT, countriesPOT_to_ms, bfuels, yearsPOT, ffuels, p_biofTrans, p_nagrShare, p_secgShare, p_transportFuels, p_shareInTransportFuels` | captrd/load_potencia_biofshares.gms:26–45 (via conservative_biofuel_trends_EU.gms:28, biofuel_trends.gms:736) | `%consBioTrends%` on |
| `%results_in%\global\globiom_GL_GlobiomTightLink.gdx` | `p_globiomTightLink(Rall,COLS,ROWS,longScen,*)` | captrd.gms:310–313 | `%FixExogenFactGlobiom%` |
| `..\dat\capreg\regional_mlk_prod.gms` | `p_mlkProdRegio(NT2,nuts2_2010,t)` | load_eurostat_milk_data.gms:20 | `%milk_RegioData%` |
| `sugar\extract_regio_SUGB_data.gms` | regional SUGB | captrd.gms:507 | `%Beet_RegioData%` |
| `global\agmip_yields.gms` | IMPACT yields | captrd.gms:590 | `%agmip%` |
| in-code `TABLE p_ExpertSupprt` | one dummy row (FI OLIV) + NTRD.FRMI=0.1 @trust 10, sugar prices (631/541.5/404.4), beet prices, beet/sugar balance positions @8 | expert_support.gms:28–104 | — |

### 2.4 Restart / merge files (optional)

| File | Symbol | Where |
|---|---|---|
| `%restart_in%\captrd\trdfst_%BAS%%SIM%%addfile%.gdx`, `trdsnd_…gdx` | `estP` (starting values for Solve1 / Solve2) | captrd.gms:1045–1051 (`$if exist`, compile time) |
| `%results_out%\baseline\results_%BAS%%SIM%%addfile%%ResId%.gdx` | `p_result`, `meta` (results of countries not in this run are kept) | 1325–1359 |

Note on missing/zero values: throughout, a zero in `p_data` is treated as “not observed” (all sums carry `$ p_data(…)`), e.g. estimate_trends.gms:107–123, prep_data_for_estimation.gms:209. COCO nowcast data use 1E-13 as an explicit “observed zero” flag (load_coco1_data.gms:123–139, 278–283).

---------------------------------------------------------------------------------------------------

## 3. Step 1 estimator and statistics → supports

### 3.1 Time sets (captrd.gms unless noted)
- `p_trend(t) = ORD(t)/10` over `YEARS = %FirstYear%..%lastSimulationYear%` (203, 271). The doc says t₁₉₈₄=0.1 (p.149); that holds only if `%FirstYear%`=1984 (GUI value not found in the tree).
- `ExPost` = years with UAAR in any MS (673); `ExAnteD` = non-ExPost years with COCO UAAR (load_coco1_data.gms:54); `ExPostT = ExPost ∪ ExAnteD` (load_coco1_data.gms:58–59; re-derived captrd.gms:721–722).
- `BAS` = base year; `BASYRS5 = {|t−BAS| ≤ 3}` (7 years, despite the name) (703); `BASYRSM = {|t−BAS| ≤ 1}` (704); `EIGHTLST` = last 8 ExPost years (705).
- `BAST`: `OrdT("BAST") = OrdT(Lst_exPostT) − 1`, `BASYRST = {|t−BAST| ≤ 1}` = last 3 ExPostT years (764–768).
- `YearsEst = {1985,1990,1995,2000} ∪ ExAnte` (806–810) — years for which Step1 is evaluated.
- `Fst_exAnte`, `Sec_exAnte` (needed for extrapolation past `%lst_dgagri%`) 733–757; `Before(t,t−1)` ordering over ExAnte plus `All_Last_Expost` 787–795.

### 3.2 Pre-statistics (prep_data_for_estimation.gms)
- `nObs = #{t∈ExPostT: x_t≠0}` (209); `nW = Σ_{x_t≠0} t_t` (210); both set 0 if BASM=0 (except biofuel cols/rows) (215–218), for INHA.LEVL (221–222) and DOMM.OYANI (226–227).
- `wAve = Σ x_t·t_t / nW` (233–234).
- `wVar = Σ_{x_t≠0}(x_t−wAve)²·t_t / (nW−1)` if nObs>2; set 0 if |wVar|≤1E-20 (241–246).
- `BAS = mean_{t∈BASYRS5, x_t≠0} x_t`; I/O coefficients of activities: level-weighted mean (255–264).
- `BSY` (yields only) = max(mean of 3 highest yields in EIGHTLST, BAS) (305–317).
- Feed coefficients: nObs=1, BAS=BASM; missing BASM filled with 0.001×MS value (275–291).

### 3.3 Trend form and estimator (estimate_trends.gms)
Model: `x_t = a + b·t^c` (header :8; Step1 evaluation define_stats_and_supports.gms:47–49).
Domain: `RALLEst = MSINCL ∪ NT2 under MSINCL (if NTSLVL≠0)` (:60–63), all `S_ColsEst × S_RowsEst`.
Grid on c: 30 points `c_k = 0.02 + (k−1)·(1.2−0.02)/29` (step ≈ 0.0407) when nObs>4 (:28, 57–58, 80–82); `c=1` (single grid point) when nObs∈{3,4} (:83–85; other points zeroed :160).
For each c, closed-form WLS with weights t (sums over t∈ExPostT, x_t≠0):
- `S_ty = Σ t^(c+1)·y`, `S_1y = Σ t·y`, `S_t = Σ t^(c+1)`, `S_1 = Σ t`, `S_tt = Σ t^(2c+1)` (:94–123)
- `b = (S_ty·S_1 − S_1y·S_t)/(S_1·S_tt − S_t²)`, `a = (S_1y·S_tt − S_ty·S_t)/(S_1·S_tt − S_t²)` if denominator>0 (:128–142)
- `wESS(c) = Σ (y − a − b·t^c)²·t` (:146–155)
- `c* = argmin wESS`; ties → lowest k (:166–171); a,b,c stored to `p_aTrend/p_bTrend/p_cTrend` (:188–190).
- nObs ≤ 2: S_ty and S_t are not assigned and c=0, so algebraically b=0 and a = weighted mean (follows from :94–142; slope/c only copied for nObs>2, :173, 181). Comment :158 states the intent.
- No bound on a, b; c bounded only by the grid [0.02, 1.2]. Doc (p.149) states c<1.2.

### 3.4 Statistics (define_stats_and_supports.gms)
- `wVarErr = Σ_{x_t≠0} (x_t − a − b t^c)²·t / (nW−1)` for nObs>2 (:118–123); for nObs ∈{1,2}: `wVarErr = 0.25·wAve²` (:129–132).
- `wR2 = max(0, 1 − (wVarErr/wVar)$wVar)` (:177–179); because the `$wVar` applies to the ratio only, wR2 = 1 when wVar = 0 (e.g. constant series or nObs ≤ 2).
- Step1 for animal requirements: `(Const + Slope·yield_Step1)·0.998^(t−2000)` (:89–93); Const/Slope from OLS of requirement on main yield per MS, slope ≥ 0 (prep_requirement_estimation.gms:33–55), scaled so BASM requirement = feed-based delivery (:92–104).

### 3.5 Supports (“priors”) from Step 1 (define_stats_and_supports.gms)
Let `B = BAST if available else BASM` (BAST = mean of last 3 ExPostT years incl. COCO, scale_DG_AGRI_baseline.gms:53–57; BASM = CAPREG base year).
- NTRD: `S = B·(1−wR2) + Step1·wR2` (:195–199).
- All other series: `S = max(f·B, B·(1−wR2) + Step1·wR2)`, f=0.001 (f=1.0 for CSSP with negative BASM) (:203–212).
- Crop yields: `S = max(0.001·B, BSY·(1−√wR2) + Step1·√wR2)` (:217–221) — uses BSY (best-3-of-8 yields) and √R², not B and R².
- All yields clipped: `B·0.975^(t−t_B) ≤ S ≤ B·1.025^(t−t_B)` (:226–238); NoYieldDrop crops `S ≥ B` (:242–246).
- Breeding-animal SLGW: `BASM·0.998^Δt ≤ S ≤ BASM·1.002^Δt` (:252–266, p_useBAST=0).
- UAAR: `B·0.998^(t−t_BAST) ≤ S ≤ B` (:272–281); grassland `S ≥ 0.9·BASM` (:285–286); DAYS/DAILY within 0.99·lo / 1.01·up of `p_reqfcnlim` (:290–293).
- Feed I/O: `S = BASM` (else 0.1×MS BASM); `wVarErr = (max((DRMN−DRMX)/2·0.1, 10, BASM))²` (×10 if no BASM) (:298–308). Requirement scalers ReqsT: S=1, wVarErr 0.1 (0.01 for ENNE, CRPR) (:318–323).
- Stored error variance: `wVarErr_result = max(|wAve|·0.05 [not ReqsT/Feed], wVarErr)` (:327–329). **As coded this compares a level (|wAve|·0.05) with a variance**; flag for the design spec.
- DGAgri1 prices already enter here: `S(UVAG)=DGAgri1`, `wVarErr=|S|·1E-4`; TOOU wVarErr ×100 where UVAG has DGAgri1 (:355–365).

### 3.6 External supports in Step 2 (same file)
- COCO nowcast supports for ExAnteD (`"coco"`): taken if not in colsNoCoco {LOSF,LOSM,SEDM,SEDF} / rowsNoCoco {REQST, IPIG, ICHI} (load_coco1_data.gms:32–37) and relative deviation from BASM < 1.2 (:395–419); trust 7, 0.5 for EAAG/TOOU, 10 for LEVL and yields (:437–456).
- `expert_support.gms` (included :460) builds `p_ExpertSupprt(r,col,row,t,{Absolute|PercentChange|TrustLevl})`; mapping to `p_result(…,"Expert")` = Absolute or `(1+PC/100)·BASM` (:490–507); COCO overrides expert for ExAnteD (:530–540).
- Expert bounds: MrkKeyPos with DGAgri and coco: `expertLo/Up = 0.99/1.01·coco`, trust 9 (:546–560); herds and young-animal coefficients likewise if `%phaseInYr% < %lst_dgagri%` (:562–589).
- `Support := Expert` where an expert value exists (:604–606).
- Crop area supports rescaled: `S_i ← S_i·(0.67·S_UAAR + 0.33·ΣS_j)/ΣS_j` (:618–622).
- Trust level → error variance (the key formula, doc eq. 4.38):
  `TrustLevl = coco trust, else expert trust, else 10` (:637–645);
  `wVarErr = ( max(0.1, |Expert|) · 0.05/3 · 10/TrustLevl )²` (:647–650).
- DOMM components without external info: wVarErr ×10, bounded to trust levels ∈ [1E-4, 1] equivalent (:655–663).
- `Support1 := Support` (copy for later checking) (:675–676).

### 3.7 Expert sources summary (expert_support.gms)
- Per-capita nutrient intake (kcal/protein/fat) per MS: `BASM + ΔEU·(min(2050,t)−BAS)·(1−0.5·(t−BAS)/(2050−BAS))·(1 + 4·(EU_mean10 − BASM)/EU_mean10)`, trust 10 (7 for fat), bounds ±1% for ExAnteT (:164–198).
- Isoglucose PRCI.MAIZ from Aglink HCOM.SUGA × HFCS share, allocated 50% by maize production / 50% by sugar consumption shares, trust 9; INDM.MAIZ = 1.05×PRCI, trust 5 (:208–266).
- UAAR expert = UAAR support, trust 10; breeding SLGW trust 8; SHGM.SGMI trust 5 (:310–338).
- DG AGRI dairy targets with logistic extension and correction to Aglink (:367–760) (only `%useAgriInfo%`).
- `agriprod_supports.gms` (recent Eurostat herds/yields for 2018–2020) (:771); `national_supports.gms` (NECP etc.) (:779); `longrun_supports.gms` (:786).
- Herd/level support floor: max(…, B·0.9^Δt, B·(1−0.8·Δt/(t_last−t_B))) (:794–808).
- TOOU made “expert” with trust 0.5·min(1, S/BASM) where UVAG has expert info (:817–834).

---------------------------------------------------------------------------------------------------

## 4. Step 2/3 estimation model (equations.gms, estimate_ms.gms)

### 4.1 Variables
`SSQ` (objective), `V_EstV(rall,COLS,ROWS,*)` (all estimated items), `sV_EstV`, `sV_EstVCopy` (storage) (equations.gms:28–35). One NLP per MS and year: `Rest={MS}`, `MSEst={MS}`, `exAnteY={t}` (estimate_ms.gms:42–46; captrd.gms:1029–1030).

### 4.2 Equations of m_trendMS (equations.gms:885–890). Notation: V(col,row) = V_EstV(r,col,row,t); all equations exist only where the involved series have nObs>0.

| Equation | Algebra | Line |
|---|---|---|
| AREAB_ | Σ_{MCACT} V(c,LEVL) = V(UAAR,LEVL) | 107–112 |
| LANDUSEB_ | Σ_{LandUseARTO} V(l,LEVL) = V(ARTO,LEVL) | 116–121 |
| STRA_ | V(c,STRA) = Σ_{main o} V(c,o)·BAS(c,STRA)/BAS(c,o) (cereals) | 125–133 |
| OSET_ | Σ_{arbAct} V(a,LEVL)·0.01·SETR/(1−0.01·SETR) = Σ_{RSET} V(s,LEVL) | 141–147 |
| GROF_ | 0.001·Σ_{MPACT} V(a,row)·V(a,LEVL) = V(GROF,row) | 151–167 |
| LABO_ | V(GROF,LABH)+V(GROF,LABN) = V(GROF,LABO) | 172–176 |
| MAPR_ | V(MAPR,s) = Σ_{PRCD(s,p)} V(PRCM,p)·V(PRCY,s) − [MOLA: 0.9·V(BIOF,SUGA)/V(PRCY,SUGA)·V(PRCY,MOLA)] | 286–307 |
| MaprByFeed_ | V(MAPR,res) = BAS(MAPR,res)·Σ(V(HCOM)+V(PRCM)+V(INDM)+V(BIOF,SUGA))/Σ BAS(same) | 346–367 |
| BIOF_ | V(MAPR,f) − V(NAGR,f) − V(SECG,f) = Σ_{stock} V(BIOF,stock)·V(PRCB,stock) | 463–470 |
| DDGS_ | V(MAPR,DDGS) = Σ V(BIOF,stock)·V(PRCBY,stock) | 454–458 |
| SugaQuot_ | V(MAPR,SUGA) ≤ QUTS + V(INDM,SUGA)+V(BIOF,SUGA)+V(LOSM,SUGA) (no coco) | 311–321 |
| SugaMinBiof_ | V(MAPR,SUGA) ≥ V(BIOF,SUGA) | 326–331 |
| MaizMinIndm_ | V(INDM,MAIZ) ≥ V(PRCI,MAIZ) | 337–341 |
| MLKCNT_ (FATS,PROT) | V(PRCM,MILK)·V(k,MILK) = Σ_{mlkSeco}(V(MAPR,s) − V(PRCM,s))·V(k,s) | 373–381 |
| EAAG_ | V(EAAG,o) = 0.001·V(UVAG,o)·V(GROF,o) | 385–390 |
| REVE_ | V(a,TOOU) = 0.001·Σ_o V(a,o)·V(UVAG,o) | 394–402 |
| UVAD_ | V(UVAD,o) = V(UVAG,o)+V(CSSP,o) | 406–411 |
| UVADfuel_ | V(UVAD,o) = V(UVAG,o)+V(CTAX,o) | 415–420 |
| EXPE_ | V(EXPE,o) = V(UVAD,o)·V(HCOM,o)/INHA_pop | 425–432 |
| EXPETOT_ | V(EXPE,LEVL) = Σ_o V(EXPE,o) | 437–441 |
| FEED_ | V(GROF,feed) = Σ_{FEED_TO_O} V(FEDM,o) | 445–450 |
| REQS_ | (Const + Slope·V(a,yield))·eff_t·V(a,req) = Σ_feed V(a,feed)·content_MS,BASM(req,feed); eff_t = 0.998^(t−2000) or 1/GLOBIOM factor | 514–535 |
| LU_ | V(LU,LEVL) = Σ_{MAACT} V(a,LEVL)·p_LUUnits(a)/V(UAAR,LEVL) | 540–544 |
| OYANI_ | V(GROF,y) − V(STCM,y)[not YCAM/YCAF] = Σ_{O_TO_YANI} V(GROF,i) | 548–555 |
| SlgwFem_ | V(a,SLGW)·Σ_{IYANI} V(a,i) = 1000·Σ_{MEAT} V(a,meat) | 561–565 |
| FinalWgt_ | Σ V(a,meat)/carcassShare = startWgt + V(a,DAILY)·(1 or 0.001)·(V(a,DAYS) − EDAYS_BASM) | 572–582 |
| Dailyup_ | V(BULF,DAILY)/1000 ≤ 0.4 + 0.0016·V(BULF,BEEF)/carcassShare | 587–591 |
| HERD_ | V(a,HERD) = V(a,LEVL)·V(a,DAYS)/365 | 599–604 |
| SplitFix_ | V(lo-yield act,LEVL) = V(hi-yield act,LEVL) (GRAE/GRAI, BULL/BULH, HEIL/HEIH, DCOL/DCOH) | 609–613 |
| SEED_ | 0.95·V(GROF,o) ≥ V(SEDM,o)+V(SEDF,o)+V(LOSF,o) | 618–630 |
| PosUp_ (named so, it is a ≥) | V(k,o) ≥ base·(BAS ratio)·0.8 − 0.1, base = GROF (SEDM/SEDF/LOSF) or GROF/MAPR+IMPT (LOSM) | 637–670 |
| PosLo_ (≤) | V(k,o) ≤ base·(BAS ratio)·1.2 + 0.1 | 672–710 |
| MBAL_ | V(GROF)[or V(MAPR)] + V(IMPT) = V(FEDM)+V(SEDM)+V(SEDF)+V(INDM)+V(PRCM)+V(BIOF)+V(HCOM)+V(LOSM)+V(LOSF)+V(EXPT)+V(INTP) | 715–737 |
| NUTBAL_ | 365·V(n,INCE) = Σ_o V(INHA,o)·p_NCNC_CONT(o,n) | 741–746 |
| HCOM_ | (V(HCOM,o)+V(LOSF,o)[mlkO])·V(foodSh,o) = 0.001·V(INHA,o)·INHA_pop | 751–756 |
| DOMM_ | V(DOMM,o) = Σ_{DOMPOS} V(d,o) (not fuels) | 760–766 |
| NTRD_ | V(NTRD,o) = V(EXPT,o) − V(IMPT,o) (if NTRD support) | 770–777 |
| MBALGRP_ | V(k,grp) = Σ_{o∈grp} V(k,o) | 781–786 |
| GRPLVL_ | V(grp,LEVL) = Σ_{c∈grp} V(c,LEVL) | 790–795 |
| SSQS_ | objective (4.3) | 803–875 |
Note: `INHA_pop = p_result(r,"INHA","LEVL",t,"p_data")` is a parameter; `V(INHA,LEVL)` is fixed to it (estimate_ms.gms:114). V(INHA,o) for products = per-capita consumption.

### 4.3 Objective (equations.gms:801–875)
With S = Support, σ = max(√wVarErr, 0.005·S) + 1E-5 (`p_weightStdErr`=0.005, :801), over free variables (lo≠up) having S≠0 and wVarErr≠0:

```
SSQ = { 1000·Σ_{r,col,row} ((V − S)/σ)² · w_r,col,row
      + 1000·Σ_{r,y∈OYANI, t∈ExAnteT} ( V(STCM,y) / max(0.05·S(GROF,y), 1E-5) )² }
      / { Σ_{same set} (0.10·S/σ)² · w_r,col,row  + 1 }
```
`w = 1` when |Rest|=1 (MS models); in multi-region models (NUTS2): for activity columns `w = max(0.001, (LEVL_BASM(r,col)+1E-5)/Σ_r'(LEVL_BASM(r',col)+1E-5))`, for other columns `w = max(0.001, (Σ_{a producing row} LEVL_BASM(r,a) + 1E-5)/Σ_r'(…+1E-5))` (:819–835). The denominator is a constant (parameters only), i.e. the objective is normalised so that a uniform 10% deviation from all supports gives ≈1000. `TestFeasible`=0 (:93–94). The doc (eq. 4.7) shows only the core term (V−S)²/varErr; σ-floor, region weights, STCM term and normalisation are code-only.

### 4.4 Bounds (estimate_ms.gms + fix_est.gms)
- Default: up = 1E+9 (estimate_ms.gms:55); lo = max(0.01·S, negative BASM for CSSP/OCRO/OANI) (:60–68); MS LEVL lo ≥ 1E-5·#NUTS2, up ≥ 1.1·lo (:78–82); start values = Support or previous estP (:87–101); INHA.LEVL fixed (:114); sugar zero-quota fixes (:120–125); tight-link ±10% around DGAgri1 (:127–154); expertLo/Up (:159–162).
- fix_est.gms (included estimate_ms.gms:74):
  - I/O coefficients (ExAnteT, no coco): `B·max(0.975^Δt, 1 − 0.3·Δt/Δt_last) ≤ V ≤ B·min(1.025^Δt, 1 + 0.3·Δt/Δt_last)` (0.1 instead of 0.3 for YCAM/YCAF; upper second bound off for crops/YCHI/SGMI) (:22–64).
  - feed mix ±10%/yr, fodder ±5%/yr (:99–142); requirement scalers (:144–167).
  - NoYieldDrop: lo = BASM·(1.0025 [1.0005 grass])^(t−BAS), and lo ≥ previous year’s estP (Before) (:169–191).
  - UVAG ±2%/yr from max/min(BASM,BAS) (±5% for OCRO, OANI, MILK) (:236–258); per-capita food ±2%/yr (:267–280); foodSh range (:282–292).
  - Crop LEVL: BASM ± (share)^0.25/4·(UAAR−GRAS)·max(0.2, Δt/Δt_last) (:341–381); grassland ≥ 0.98·B (EU28) (:390–404).
  - Herds: lo = 0.2·BASM, yearly factors 0.9/1.05 (PIGF EU-West 0.98) (:406–490).
  - Max yields per crop (e.g. cereals 15000, MAIF 90000, POTA 55000 …) (:550–652).
  - UAAR: `BASM·0.998^(t−BAS) ≤ V ≤ BASM` (no coco) (:785–795); ARTIF ≥ Σ regional BASM; ARTO, INLW (and KITC) fixed at BASM (:801–815).
  - Observation: fix_est.gms:810 reads `LO * 1.02**(OrdT(ExAnte)) - OrdT("BAS")` — parenthesis placement makes the ARTIF upper bound effectively unbounded (as coded).
  - comi_bounds.gms (:840) and biofuel_bounds.gms (:845).
- Infeasibility handling (estimate_ms.gms:198–465): up to 5 tries widen LEVL bounds ×2 / ×0.5 where binding; then all binding bounds widened by 90% (1% for PRCY of secondary products), STCM admitted; >25 tries OIND/OCRO LEVL lo→0; >50 tries: listing and flag `isInfes` (abort at captrd.gms:1115–1126 / estimate_ms.gms:568–570). Re-application of land/UAAR/ARTO, comi, biofuel bounds on each retry (:362–418).
- Solve2 only: `clean_tiny.gms` (estimate_ms.gms:442–447) re-solves m_trendMS with Support := Step3 result, bounds ±0.5% (or ±3·p_tiny) around it, wVarErr of trust level 2, and for ColsTiny (market balance positions, DOMM) Support = −1 if result < p_tiny/2 (pull to zero) or +1 with up = p_tiny if in [p_tiny/2, p_tiny] (clean_tiny.gms:21–31, 60–140; p_tiny = 0.1, sets_captrd.gms:471–479).

### 4.5 Solver
- `SOLVE m_trendMS USING NLP MINIMIZING SSQ` (estimate_ms.gms:192, 228, 243, 433), asynchronous grid (`SolveLink=3`, handles, at most `%NoProc%`=2 parallel; :176, 184, 194, 198–465). `optfile=1` (op2 file when retrying with no iterations, :240), `holdfixed=1`, `HoldFixedAsync=1` for GAMS>36.1 (:181), reslim 900 s, iterlim 100000, tolinfeas 1E-5 (equations.gms:891–905).
- The NLP solver is **not set in captrd** (no `option nlp=` in captrd.gms or captrd/*.gms); it is the installation/GUI default. CONOPT option files `conopt.op2`, `conopt3.op2`, `conopt4.op2` exist in the gams folder; `conopt.opt` was not found there.
- EU extra-trade model: DNLP (estimate_eu_trade.gms:122, 128).

### 4.6 Step 3: building supports from Aglink and long-run sources (define_eu_supports.gms; called after Solve1, captrd.gms:1070)
1. Store Solve1 → `"Step2"` (:43–45).
2. Scaling Aglink to CAPRI (earlier, scale_DG_AGRI_baseline.gms): `DGAgri1(t) = DGAgri(t)·BAST_CAPRI/BAST_Aglink` for prices (MS → sub-aggregate → EU-top fallbacks, :98–129), yields (:135–151), market balances (aggregate “BAST2” excluding MS with own data, :208–257; MS :279–286), levels (:302–350); biofuels: ratio if ratio<2, else additive difference (:364–420); DOMM recomputed (:429–432); SEDF/SEDM/LOSF/LOSM DGAgri1 = 0 (:443–446); EU-top DGAgri1 = 0 (:464).
3. Beyond `%lst_dgagri%` (t > lst): logistic extrapolation of the **Step3** result (:63–191):
   `g = (Step3(lst)/Step3(start))^(1/(t_lst − t_start)) − 1`, start = mean of Fst/Sec_exAnte (:67–81, 149–156);
   `γ = g/(1−min)/(1−(1−min)/(max−min))` (= 8g with min=.75, max=1.25) (:161–165);
   `DGAgri1(t) = Step3(lst)·[min + (max−min)·sigmoid(γ·(t − t_lst))]` (:170–184); copied to `"Extrap"` (:189).
4. Disaggregation of aggregate DGAgri1 to MS (MS without own DGAgri1):
   `DGAgri1_MS = Step2_MS · DGAgri1_agg / Σ_{MS∈agg, no own DGAgri1} Step2_MS` for market balances and LEVL (:214–255); HERD = LEVL for 365-day animals (:259–262).
5. Long-run merge for t > `%phaseInYr%` (if horizon > lst_dgagri): `Longrun1 = Longrun·w + DGAgri1·(1−w)`, `w = ((min(2050,t) − phaseInYr)/(2050 − phaseInYr))^p_longExp · p_longWgt` (:271–343); `p_longWgt`=0.9, `p_longExp`=0.7 (0.99/0.7 for faoIfpri2009; p_longExp=0.01 with FixExogenFactGlobiom) (longrun_supports.gms:78–94). Longrun values = GLOBIOM change factors × B2000 (3-yr mean 1999–2001) (longrun_supports.gms:39–64, 196–…); then `DGAgri1 := Longrun1` (:335–341).
6. `Support := DGAgri1` for MrkBalee (not NTRD), PRCI, LEVL, HERD, prices, TOOU, yields, **unless an Expert support exists** (:400–500); EAAG support removed if UVAG & GROF have DGAgri1 (:505–508).
7. Implied NTRD support = GROF/MAPR − DOMM (or − ΣDOMPOS) (:518–536); DDGS net trade squeezed (:540–558); IMPT/EXPT supports adjusted so that their difference matches NTRD, shift split by gross-trade shares (:565–604).
8. Area supports rescaled to UAAR (67/33 rule) (:624–629); young animals from herds × coefficients (:641–684); non-negativity (:710–711).
9. Trust levels for DGAgri1 (:719–864): 5 (+1 GROF/MAPR/DOMM/HCOM, +2 meats, −2 SGMI) if MS has own DGAgri; 3 (+1, −2 SGMI) if only from aggregates; 5 for IMPT/EXPT/NTRD/LEVL; 1 for CERE/OILS LEVL; animals LEVL 5−3(−1.5) when extrapolated; yields 3 (COMI 7); EXPE /5 and GROF /5 under quotas; ×(1+0.8·frac to 2050) after lst_dgagri, cap 10; UVAG 3 (0.5 from aggregates); UVAD 0.3.
10. `wVarErr = (max(0.1,|S|)·0.05/3·10/TrustLevl)²` for non-expert supports with trust (:883–886); IMPT/EXPT wVarErr ×25 if NTRD has a support (:891–895).
11. DGAgri/DGAgri1 entries beyond lst_dgagri and not truly from Aglink are deleted (:869–881).

### 4.7 EU extra-trade adjustment (estimate_eu_trade.gms, after the loop)
`min Σ ((T − T_Aglink)/(T_CAPTRD + T_Aglink + 1E-3)·2)²·T_Aglink / Σ T_Aglink` s.t. `NTRD_CAPTRD(EU) = T_EXPT − T_IMPT` (:59–70), bounds lo = min(0.1·T_CAPTRD, 0.5·T_Aglink), up = T_CAPTRD·(1+1E-6) (:104–111); EU result split to RMEU by Step3 MS gross trade shares (:139–147).

---------------------------------------------------------------------------------------------------

## 5. Step 4: MS → NUTS2 (estimate_nuts2.gms, est_nuts2_grid.gms)

- Called inside Solve2 after MS results are stored as Step3 and cleaned (`rem_tiny.gms`) (captrd.gms:1085–1101).
- MS variables **fixed** to MS Step3: `V_EstV.FX(MS,…) = p_result(MS,…,"Step3")` (estimate_nuts2.gms:28).
- Estimated items narrowed to activities, crop groups, land use, GROF, LU, UAAR, ARTO, LOSF (+INDM for DE) × outputs, young-animal inputs, FEED, REQST, LEVL (:32–51, 60).
- One model per MS with >1 NUTS2 region (`CARD(Rest)>1`, :79); single-region countries are not estimated (title “no NUTS 2 regions found”, :435). How their NUTS2 result is filled is not explicit (in captrd.gms:874/878 such regions share the MS code; explicit copy not found).
- Supports: NUTS2 series get their own Step1 trends and supports from define_stats_and_supports.gms (Rest = MS ∪ NT2ext, :33–35; estimate_trends.gms:63); ReqsT support := MS Step3 (estimate_nuts2.gms:87–88). Expert/Aglink supports are MS-level only (expert overrides on NUTS2 exist only if p_ExpertSupprt is regional).
- Bounds: `fix_est.gms` (:90); LEVL within the MS relative change × BASM_r × 1.015^(t−BAS) / 0.985^(t−BAS) (:95–129, with ±0.01 and expert widening); I/O coefficients within MS change ±2%/yr (:131–157), lower limit −20% of national growth (:158); meat/egg coefficients almost fixed (:190); bounds on production from level×yield bounds (:232); fodder production/use linked (:257); LOSF of fodder via MS ratio (:271); sugar GROF/quota share ±5% around MS (or ±10% around regional expert GROF) (:288–315); expert bounds (:375); start values = supports (:382).
- Model m_trendNT2 (equations.gms:909–913): AREAB_, LANDUSEB_, OSET_, GROF_, REQS_, GRPLVL_, EFED_, STRA_, LU_, SplitFix_ plus the **adding-up constraints to the fixed MS values**:
  - MSGROF_: Σ_r V(r,GROF,o) = V(MS,GROF,o) (equations.gms:182–195)
  - MSLEVL_: Σ_r V(r,a,LEVL) = V(MS,a,LEVL) (not RSET, not SplitActsLo) (:199–210)
  - MSLANDUSE_: FORE, ARTIF (:218–224)
  - MSFEEDI_: Σ_r V(r,a,LEVL)·(V(r,a,feed)+10)/1000 = V(MS,a,LEVL)·(V(MS,a,feed)+10)/1000 (non-fodder feeds) (:230–240)
  - MSlosfFoddo_: V(r,LOSF,fodder) = V(r,GROF,fodder)·(LOSF/GROF ratio of MS, from estP) (:474–485)
  - MSindmMaif_: Σ_r V(r,INDM,MAIF) = V(MS,INDM,MAIF) (:490–495)
  - EFED_: V(GROF,fodder) − V(LOSF) − V(INDM) = Σ V(GROF,feed) (:500–508)
- Objective: SSQS_ with region weights w (section 4.3).
- Solve: asynchronous grid, `est_nuts2_grid.gms` widens bounds (`est_Nuts2_grid_openbound.gms`) up to 75 tries / 10 non-optimal retries, aborts if infeasible or if SplitActsLo do not add up (|rel. diff| > 1E-7) (est_nuts2_grid.gms:35–44, 222, 256–300).
- Results: `p_result(NT2,…,"Step3") = V.L`, plus `lo`, `up`, `penalty` (estimate_nuts2.gms:499–523); then `rem_tiny.gms` (:528): LEVL ≤ 1E-6 → 0, coefficients deleted, GROF recomputed (rem_tiny.gms:20–60).

### Farm types (separate task `captrdfrm.gms`)
- `$setglobal FARM_B ON, FARM_M ON, ntslvl 999, STRCHA_Version 1` (captrdfrm.gms:45–50); reads CAPTRD `results_%BAS%…gdx` (`p_result`, :243, 337), CAPREG `res_%BAS%<country>%addfile%.gdx` (:291–292), structural change data (`%datdir%\farmtype\Structural_change_Markov.gms`, `captrd\data_structural_change.gms` → `%results_in%\farmtype\1_conslevel_Nsel\%MS%_DATA.gdx` `p_indSGM`, `RMAp_TSGM_POS_FSSV` (data_structural_change.gms:25–27)).
- Model `m_trendFarm` (equations_farm.gms:304–345): SSQS_, AREAB_, OSET_, GROF_, LU_, GRPLVL_, REQS_, MSlosfFoddo_, EFED_, STRA_ + NT2GROF_, NT2LEVL_, NT2FEEDI_ (adding up to fixed NUTS2) (equations.gms:246–281); structural-change equations only for STRCHA_Version ≠ 1.
- Writes `%results_out%\baseline\results_%BAS%%SIM%<country>%addfile%_new.gdx` and `trends_%BAS%<YY><country>%addfile%%ResId%_new.gdx` (captrdfrm.gms:840, 857–860); restart `%results_out%\captrdfrm\chk_farmrestart…gdx` (save_results_captrd.gms:28).
- Not included anywhere (dead code): `farms_loop.gms`, `estimate_farm.gms` (only via farms_loop), `estimate_labour.gms`, `load_combal.gms`, `est_nuts2_grid_beforeFTswereRemoved.gms` (include search over the tree).

---------------------------------------------------------------------------------------------------

## 6. Outputs

| File | Symbols | Where |
|---|---|---|
| `%results_out%\baseline\results_%BAS%%SIM%%addfile%%ResId%.gdx` | `p_result(rall,cols,rows,t|stat,respos)`, `RALL, COLS, ROWS, META, SETTINGS` (merged with existing results for countries not in run) | captrd.gms:1325–1383 |
| `%results_out%\baseline\trends_%BAS%<YY>%addfile%%ResId%.gdx`, one per RESY year (YY two-digit) | `data2(rall,cols,rows,"y") = p_result(…,resy,"step3")`, `rall, cols, rows, META, SETTINGS` | 1393–1417 |
| `%results_out%\baseline\Aglink_for_capmod_%BAS%.gdx` | `p_AglinkUVAG`, `p_AglinkTrade(rall,cols,rows,t)`, `p_AglinkMacro` | estimate_eu_trade.gms:159 |
| `%restart_out%\captrd\trdfst_…gdx`, `trdsnd_…gdx` | `estP`, `isInfes` | captrd.gms:1113, 1122 |
| `%datdir%\baseline\recent_mlk_yld.gdx` | `p_recentMlkYld` | agriprod_supports.gms:322 |
| debug | `error_stats_and_supports.gdx`, `debugestimate_MS.gdx`, `abort…gdx`, `chk_%AGLINK%_EUdata.gdx` | define_stats_and_supports.gms:25, 427; estimate_ms.gms:569; load_aglink2024dgAgri.gms:853 |

`respos` elements in p_result (sets_captrd.gms:493–531): DGAgri, DGAgri1, Expert, TrustLevl, data, BASM, BAST, B2000, support, support1, coco, step1, step2, step3, wVarErr, CoefVarErr, penalty, Extrap, Longrun, Longrun1, P_Data, nObs, series, lo, up, expertLo, expertUp, Step3Tiny, SupportTiny, wVarErrTiny, loTiny, upTiny, BSY. 4th dim also carries statistics `wAve,nObs,Bas,Basy,WR2,wVar,nW,BAST,BAST2,slope,const` under respos `"DATA"` (captrd.gms:1175–1185).
Post-processing before writing: requirements converted to absolute values (1206–1217), CoefVarErr (1223–1232), aggregation to REGAGG (EU aggregates complete in the run) (aggreg_and_report.gms:44–55, 111–…), labour LABP/LABT/LABF and per-activity labour scaling (1269–1300), fossil fuels from Expert (1304–1305), INHA from p_data (1309–1310), SERIES (1314–1315), breedAct SLGW zeroed (1320).

### Consumers
- CAPMOD baseline: `capmod/load_base_data_and_trends.gms` loads `trends_%BAS%%SIM%%addFile%%VersionCapTrdFarm%%inputDataId%.gdx` (`DATA2`, `settings`) (:212, 236–237, 262), checks that the long-run scenario in `settings` matches the GUI choice (:270–280), reads Aglink version from settings (:287–289) and sets `DATA(RS,ColsRead,RowsRead,"TRD") = DATA2(RS,…,"Y")` (:326). Farm-type runs load the per-country files (:240–255). The `%ResId%` (writer) vs `%inputDataId%` (reader) suffixes are both GUI globals (from_gui_for_create_result_and_restart_directory_structure.gms:152–153); equality not verified.
- `DATA(…,"TRD")` is then used by market-model calibration (`arm/data_prep.gms`, `arm/prepare_market_data.gms`, `arm/calibrate_market_data.gms`, `arm/shift_quantities.gms`, `arm/simu_calibration_to_supply.gms`, …) and supply side (`supply/def_start_value_and_data.gms`, `supply/endog_yields.gms`, `supply/prep_milk_quota_rents.gms`) (grep for `"TRD"`; detailed use not mapped here).
- `arm/data_prep.gms:1956–1957` loads `Aglink_for_capmod_%BAS%.gdx` (`p_AglinkUVAG`, `p_AglinkTrade`).
- Other readers of trends/results: `policy/implement_bps.gms:125`, `envind/envConstraints.gms:218`, `envind/breeding.gms:101`, `water_database.gms:1190`, `captrdfrm.gms:243, 337`.

---------------------------------------------------------------------------------------------------

## 7. Recursive-dynamic mode

Search (`rec_?dyn|recursiv`, case-insensitive, whole gams tree):
- `capreg/set_global_variables.gms:107–108`: `$SETGLOBAL RECDYN OFF` with comment “Only used in gams\seamcap\gtaplink\shift_exog_main.gms => obsolete”.
- `seamcap/gtaplink/shift_exog_main.gms:94`: `$IFI %recdyn%==off $INCLUDE 'supply\load_iy.gms'`.
- `seamcap/units/make_units*.gms:187/200`: label `REC_DYN 'Recursive dynamic mode'`.
- `capmod/create_sim_ini_gdx.gms:68–71`: comment only (“Recursive dynamic mode: … expost calibration … policy shift”), no code bound to a flag.
- **No recursive-dynamic code in CAPTRD** (no hit in captrd.gms or captrd/*.gms). The doc calls CAPRI comparative-static (§4.4.1, p.167).

What CAPTRD does carry between years (sequential year loop, not a dynamic model):
- NoYieldDrop lower bound ≥ previous ex-ante year’s estimate `estP` via `Before` (fix_est.gms:179–185).
- Dairy yield (COMI) lower bound ≥ previous year’s Step3 ×1.0025^Δt (comi_bounds.gms:270–281; same in long-run supports define_eu_supports.gms:314–318).
- Extrapolation beyond `%lst_dgagri%` uses Step3 of Fst/Sec_exAnte and of `%lst_dgagri%`, which must have been solved earlier in the loop (define_eu_supports.gms:63–189; captrd.gms:252–254 forces `%lst_dgagri%` into RESY).
- First ex-ante herd stock change: `estP(MS,MAACT,"LEVL",All_Last_Expost)` initialised from data (estimate_ms.gms:38) — but OYANI_ does not reference lagged herds (equations.gms:548–555), so no herd dynamics are imposed.
- `estP` from previous runs (restart gdx) as starting values only (captrd.gms:1045–1051).

---------------------------------------------------------------------------------------------------

## 8. Main parameters / constants

| Parameter | Value | File:line |
|---|---|---|
| trend variable | `ORD(YEARS)/10` | captrd.gms:271 |
| c grid | 30 points, 0.02 … 1.2 | estimate_trends.gms:28, 57–58, 80–82 |
| c for 3–4 obs | 1.0 | estimate_trends.gms:83–85 |
| min obs for free c | >4 | estimate_trends.gms:80 |
| wVarErr fallback (1–2 obs) | 0.25·wAve² | define_stats_and_supports.gms:129–132 |
| min support factor | 0.001·B | define_stats_and_supports.gms:207 |
| yield support band | 0.975 … 1.025 per yr | define_stats_and_supports.gms:226–238 |
| wVarErr floor | max(|wAve|·0.05, wVarErr) | define_stats_and_supports.gms:327–329 |
| trust→variance | (max(.1,|S|)·0.05/3·10/trust)² | define_stats_and_supports.gms:647–650; define_eu_supports.gms:883–886 |
| `p_weightStdErr` | 0.005 | equations.gms:801 |
| objective scale | ×1000, normaliser 0.10·S | equations.gms:835, 854 |
| `p_infl` | 1.019 (used only in longrun price supports) | captrd.gms:327; longrun_supports.gms:283, 286 |
| `p_extrapMinMax` | min 0.75, max 1.25 | captrd.gms:335–336 |
| `p_longWgt`, `p_longExp` | 0.9 (0.99 faoIfpri), 0.7 (0.01 GLOBIOM-fixed) | longrun_supports.gms:78–94 |
| `%phaseInYr%` | 2025 (2030 / 2010 variants) | captrd.gms:166–169 |
| `%lst_dgagri%` | 2030 / 2040 | captrd.gms:245–248 |
| `%lst_daitar%` | 2020 | captrd.gms:260 |
| feed-efficiency gain | 0.998^(t−2000) | equations.gms:525; define_stats_and_supports.gms:93 |
| UAAR decline | 0.998/yr max | fix_est.gms:792–795 |
| I/O coefficient corridor | 2.5%/yr, ±30% to last year | fix_est.gms:22–64 |
| producer price corridor | ±2%/yr (±5% OCRO/OANI/MILK) | fix_est.gms:236–258 |
| NUTS2 LEVL corridor vs MS | ±1.5%/yr | estimate_nuts2.gms:95–129 |
| `p_refmlkyld` | 7000 | captrd.gms:288 |
| `p_tiny` | 0.1 (p_tinyR = 0.1·√#NUTS2) | sets_captrd.gms:471; clean_tiny.gms:21 |
| seed/loss band | ×0.8−0.1 … ×1.2+0.1 of BAS ratio | equations.gms:670, 710 |
| SEED_ | 0.95·GROF | equations.gms:624 |
| MSFEEDI_ scaling offset | +10 kg/head | equations.gms:238–240 |
| Proc_Yields | SOYC .80 SOYO .18 RAPC .60 RAPO .40 SUNC .55 SUNO .45 | captrd.gms:355–361 |
| solve limits | reslim 900 s, iterlim 1e5, tolinfeas 1e-5; ≤2 parallel | equations.gms:901–903; util/global_settings.gms:21 |
| bound-opening tries | MS: 5 / 25 / 50; NUTS2: 75 (10 non-optimal) | estimate_ms.gms:221, 256, 335; est_nuts2_grid.gms:35, 222 |

---------------------------------------------------------------------------------------------------

## 9. Points to flag for the Python design (observations, not proposals)

1. Zeros are treated as missing in all statistics; COCO uses 1E-13 as an “observed zero” marker. A Python port needs an explicit missing/zero distinction to reproduce this.
2. Step 2 (“Solve1”) already uses DGAgri1 prices (define_stats_and_supports.gms:355–365), so Step 2 is not purely trend + MS expert.
3. The stored error variance floor mixes a level with a variance (define_stats_and_supports.gms:328).
4. fix_est.gms:810 ARTIF upper bound has a parenthesis that makes it non-binding.
5. `BASYRS5` spans 7 years (|t−BAS|≤3), not 5 (captrd.gms:703).
6. `expert_support.gms:478` reads `recent_mlk_yld.gdx` before `agriprod_supports.gms:322` rewrites it in the same run (only with `%useAgriInfo%`).
7. The NLP solver is not fixed in code; results depend on the default NLP solver and its option file.
8. The per-year problem is solved country-by-country (|Rest|=1, weight 1), so Aglink aggregate information reaches MS only through the proportional disaggregation in define_eu_supports.gms:238–255, not through a joint multi-country solve (the doc, p.148, says several countries “must be simultaneously estimated”; the code solves them separately).
