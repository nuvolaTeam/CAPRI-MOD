# CAPRI AD_AnCh (anaerobic digestion, `%ad_type% = anch`): specification for the port

Status: read-only research. CAPRI source is `/home/claude/work/allgms/gams` (all paths below are relative to it).
Line numbers were checked against that tree. Reproduction script:
`/tmp/claude-0/-home-claude/d5c56fed-b04a-5752-ba56-1dd3c6831b93/scratchpad/ad/ad_check.py`.

Labels: **[V]** checked numerically against CAPRI output; **[S]** read from source, not checked numerically; **[U]** uncertain or inferred.

---------------------------------------------------------------------------------------------------

## 0. Key findings

1. **`res2_sample.txt` comes from the *ini* calibration run, not from a simulation run.** It is byte-identical to
   `/mnt/user-data/uploads/res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv` (policy file
   `pol_input/greendeal/refpol_endotech_all_ini.gms`, which sets `ghgTechCali ini`, l.45). In that run:
   - the AD share is fixed at `IniShare − 1e-6` (`supply/set_miti_bounds.gms:176-192`);
   - `costParLin` is overwritten with 1e-10 (`envind/ad_data_and_cali.gms:802-805`);
   - the calibration block (`pmpParLin`/`pmpParSqr`/`Subs0`/`Subs1`, l.816-1170) is **not executed**.

   The AD rows in res2 therefore test the data side (IniShare, MaxShare, revenue, `costParSqr`, CH4 ratio), not the
   behavioural calibration. No simulation run (`ghgTechCali off`, e.g. `refpol_endotech_all_sup.gms`) is available
   in the uploads. The only other run is *max* (`costsavings_max…csv` and `res_2_…_maxdefaulta`). `greendeal_ref` has no AD rows.
2. **All AD data items reproduce to 7 significant digits from the CSVs [V]** for DE110000, NL220000, PL220000 and DK000000
   (DCOL, BULL, PIGF, SOWS). The checked items are the reported SHARE, MaxShare, revenue and cost. For cattle, VSER is endogenous
   and is not in the CSVs (see §3).
3. **The discount rate actually used for the AD cost curve is 0.035, not the 0.05 declared at `ad_data_and_cali.gms:397`
   [V].** `envind/ammo_tech.gms:1203` re-declares `Scalar p_r /0.035/`. GAMS applies compile-time data in source order,
   so the later value is already in force when `ad_data_and_cali.gms:468` executes. With r=0.05 every AD cost is too high by
   exactly ×1.069557. With r=0.035 the ratio is 1.0000000.
4. **The reported AD SHARE is not `v_Miti`. It is `v_Miti × Liquid × (1 − Graz)`** (`reports/sol_simy.gms:976-992`) [V].
   This answers Q5: see §5.
5. **In CAPRI as coded, AD does not reduce CH4MAN for DCOL/DCOH [V, mechanism S].** The dairy macro
   `MC_GHG_Miti_DCow` needs `p_ghgMiti(MS,DCOL,"NOC","CH4MAN_3k","QEmitt")`. `ad_data_and_cali.gms:588` sets that to zero
   (NOC is in `GainsTech`), so the AD term drops out and the factor is 1. Between the ini and max runs, PIGF CH4MAN/head
   changes by exactly the predicted factor (0.6703 vs 0.6703) and BULL by nearly the predicted factor (0.8754 vs 0.8809).
   DCOL changes by only 0.9856, where 0.5748 is predicted. Costs, revenues and N side effects of dairy AD still apply, and
   `reports/miti_report.gms:1084` still reports a dairy CH4 reduction. **This looks like a CAPRI bug.** The port has to choose
   between replicating it and fixing it. See §1.3.

---------------------------------------------------------------------------------------------------

## 1. How AD enters the supply model (simulation)

Activation:
- `capmod.gms:1110-1113`: `prep_farm_size_data_for_miti.gms`, then `$ifi not %ad_type%==0 $include 'envind\ad_data_and_cali.gms'`,
  then `envind\ammo_tech.gms`. All three sit inside `%ghgAbatement% == on`.
- The policy file sets `ad_type anch` (l.154), `ghgTechActiveOther …,AD_AnCh` (l.222) and `sensfac 1` for 2030 (l.243).
  It also sets `ghgTechAmmEndog 1` (l.93) and `p_mitiEffFac("AD_anch",simy)=0` (l.274), which means no efficiency factor.
- `AD_AnCh` belongs to `OthMitiTech` (`sets.gms:4077`), not to `GainsTech` and not to `GainsTechAD` (`sets.gms:9057`).
  So `ADMax_` (`supply_model.gms:4165`) **does not** apply. AD is not a `SupplTech`, so the generic per-head scaling
  `p_animProdDays/365` applies.
- Only the target `CH4MAN` is mapped. `mitiTech_map(rs,maact,"AD_Anch","CH4MAN") = yes $ costParLin` (`ad_data_and_cali.gms:795-797`).
  The CH4MAN_3k and CH4ENT_3k mappings are removed (l.799-800). NOC is mapped for CH4MAN (l.1179).
- The supply model tests `mitiTech_map(MSACT,…)` at **member-state level** (`R_RAGG(RUNR,MSACT)`). This works because
  `MAP_RR(NUTS0,NUTS0)=YES` (`sets.gms:7917`), so l.610-620 and l.747-765 also produce MS-level values.

### 1.1 Variable and units
- `v_Miti(RUNR,MAACT,"AD_AnCh","CH4MAN")` is a dimensionless share with bounds `0 ≤ v ≤ MaxShare`
  (`set_miti_bounds.gms:23-36`; MaxShare at RU level, falling back to NUTS0). NOC has an upper bound of 1.
- `TotMit_` (`supply_model.gms:4116-4125`): `v(NOC,CH4MAN) + v(AD_AnCh,CH4MAN) = 1`. These are the only CH4MAN techs left
  after `ad_data_and_cali.gms:587-591`.
- **Meaning:** v is the share of the AD-eligible manure that is digested. AD-eligible manure is the housed, liquid
  manure, i.e. a fraction `L·(1−G)` of the herd's manure, with `L = p_Nemidat(MS,a,"N","TypeShare","Liquid")` and
  `G = p_Nemidat(MS,a,"N","TypeShare","Graz")`. Equivalently, v is the share of animals, ranked by farm size, whose housed
  liquid manure goes to a digester. Evidence:
  - v=1 corresponds to `QEmitt(AD)`, which is defined as "all liquid manure digested" (`ad_data_and_cali.gms:719-737`).
  - All per-head money and impact parameters are multiplied by `L(1−G)` (l.747-765; `ammo_tech.gms:2330-2344`).
  - The upper bound is `MaxShare`, the share of heads in farms ≥200 LSU, which is *not* scaled by L(1−G).
  - `sol_simy.gms:976-985` says so in a comment and rescales the reported share accordingly.
  - The comment at `ammo_tech.gms:2327` ("v_miti in AD refers to total animals") describes the same algebra from the other side.
    The parameters are expressed per total animal, which is why they carry the `L(1−G)` factor.
  - The ini run gives v_Miti.L(DE110000,DCOL) = 0.0543637 = IniShare − 1e-6. The reported SHARE is 0.0467259 = 0.0543637 × 0.859507 [V].

### 1.2 Cost and revenue: `GHG_Mit_Cost_` (`supply_model.gms:4984-5040`; debug variant at 5122ff)

For AD the generic term reduces to the following, with `p(RUNR)` falling back to `p(MSACT)` when zero:

```
v_GHG_Mit_Cost(r) += Σ_maact  [ costParLin·v + ½·costParSqr·v² − revenue·v + pmpParLin·v + ½·pmpParSqr·v² − subsidy·v ]
                              × Σ_A v_actLevl(r,maact,A) · p_animProdDays(r,maact,"T")/365
```

- The comments at l.5000 and l.5006 say explicitly that the quadratic observed term and the revenue term exist for AD_AnCh.
- `v_GHG_Mit_Cost` is subtracted in the objective (`supply_model.gms:4786`). Units are € per head per year × 1000 heads, i.e. k€.
- `subsidy` is set only in subsidy scenarios (`envind/miti_subsidy.gms:242ff`, `ghgMitiSubsidy ON` in `refpol_endotech_all_sup.gms:288`).
  It is a policy layer and is not specified further here.
- **CO2FES** (fossil-energy CO2 saved) is **not** in the supply model. A grep of `supply/` finds nothing. It is reporting only
  (`envind/gases.gms:956-977`).

### 1.3 CH4MAN: `GWPCH4MAN_` (`supply_model.gms:3111-3127`) and macros (`supply/ghg_miti_macros.gms:28-52`)

Non-dairy activities use `MC_GHG_Miti_Factor`:
```
CH4MAN(r,a) = levl · EMISCALC(r,a,A,"CH4MAN","Y") · [ Σ_tech v(tech)·QEmitt(MS,a,tech)/QEmitt(MS,a,NOC) ] · (1 − Σ_amm othImpact_CH4MAN·v_amm)
            = … · [ (1−v_AD) + v_AD · QE_AD/QE_NOC ] · (…)
```
- `QEmitt` is taken at **MS level** (MSACT), not at NUTS2. Units are kg CH4/head/yr, but only the ratio matters.
- `QE_AD/QE_NOC` does not depend on VSER or B0, which cancel. With `X = tVS·B0`, climate-weighted `MCF_nc`, `MCF_s`, `MCF_p`,
  and `S = 1−L` (Solid TypeShare):
  ```
  QE_NOC ∝ MCF_nc·(1−G)·L + MCF_s·(1−G)·S + MCF_p·G                                   (ad l.710-715)
  QE_AD  ∝ [0.25·MCF_nc + 0.03·0.85·(0.98 − 0.25·MCF_nc)]·(1−G)·L + MCF_s·(1−G)·S + MCF_p·G   (ad l.687-701, 725-737)
  ```
  Example for DE DCOL (MCF_nc=0.17, cell "10"): r = 0.3995. For DE PIGF: 0.3946. For DE BULL: 0.4483.
  - Check [V]: PIGF CH4MAN/head max/ini = 0.67030 observed vs 0.67030 predicted. The prediction uses v_ini=0.05547 and
    v_max=0.59799, plus the LowEmHous CH4 side effect 0.1 × 0.1516 in ini.
  - Check [V]: BULL 0.8754 observed vs 0.8809 predicted. The residual is attributed to the EMISCALC/feed change between
    the runs **[U]**.
- **Dairy (DCOL, DCOH) use `MC_GHG_Miti_DCow(a,"CH4MAN_3k","CH4MAN")`.** The sum is restricted by
  `$ (p_ghgMiti(MS,a,"NOC","CH4MAN_3k","QEmitt") and p_ghgMiti(MS,a,tech,"CH4MAN_3k","QEmitt"))`.
  - `ad_data_and_cali.gms:588` sets `p_ghgMiti(rs,maact,gainsTech,"CH4MAN_3K",mitiinfo)=0` for all GainsTech, including NOC (`sets.gms:4043`).
  - l.717 assigns EPS only where the value is already nonzero, so it changes nothing.
  - The NOC/AD terms therefore vanish and the bracket becomes `1 $ (not Σ QE_NOC·QE_NOC_3k=0) = 1`.
  - Result: no AD CH4 effect for dairy. This is confirmed [V]: DE110000 DCOL CH4MAN/head is 54.709 (ini, v=0.054) and
    53.922 (max, v=0.739). The non-dairy logic would predict ×0.575.
  - The post-model `DATA(...,"CH4MAN")` (`gases.gms:902-910`) uses the same macro, so it agrees with the supply model.
    `miti_report.gms:1084-1100` uses its own closed formula and therefore reports dairy AD reductions that do not appear in the emissions.
  - **Decision needed:** replicate CAPRI (no dairy CH4 effect), or apply the non-dairy ratio to dairy, which is my
    recommended fix since it is clearly the intent of l.717/l.739.
- Rows labelled `GWP*` have the same structure for the debug/aact variants (l.3134-3148).

### 1.4 N side effects (cascade)

These are all at **RUNR level, with no MS fallback**. Parameters are set in `ammo_tech.gms:2313-2348`:

| Equation (supply_model.gms) | Term | Item |
|---|---|---|
| `HOUSN_` l.3200-3218 | `× (1 − (v_AD · p(AD,"OthImpact","N2OHOU")) $ N2O)` | N2O from housing ("LossHous av") |
| `STORN_` l.3222-3242 | `× (1 − v_AD · (p(NH3STO)$NH3 + p(NOXSTO)$NOX))` | NH3 and NOX from storage (not N2) |
| `APPLN_` l.3295-3327 | inside `(1 − Σ … − p(N2OAPP)·v_AD $ n2o)` | N2O from application |

- The cascade runs through the N pools. Lower or higher housing and storage losses change the N passed to `RUNHOUSN_` (l.3246),
  to `APPLN_` (all gases) and to runoff/leaching. In turn they change manure N available as fertiliser.
  - Note that for DE DCOL `NH3STO` is −0.404, an *increase* in storage NH3 for digested manure.
- Parameters (`ammo_tech.gms:2318-2344`): `p_ghgMiti(rs,a,AD,"OthImpact",X) = p_litRevAmmoTechsAdd(rs,"AD_Anch",a,"liquid",X) × L(nuts0,a)·(1−G(nuts0,a))`
  for X ∈ {N2OHOU, NH3STO, NOXSTO, N2OAPP}. The values themselves come from `prep_data_LitRev.gms:936-940`.
  - They are set only where `mitiTech_map(rs,a,"AD_Anch","CH4MAN")`. That mapping already exists at this point (ad file l.795 runs before ammo_tech).
  - l.2346 zeroes them where AD QEmitt = 0.
  - The litRev `CH4MAN` entry (0.77) is **not used** for AD.
- Old N2OMAN code (`ad_data_and_cali.gms:773-788`, `gases.gms:949-951`) is commented out.

### 1.5 Bounds and calibration-mode specifics
- **ini** (`set_miti_bounds.gms:176-192`, inside `if(p_ghgTechAmmEndog, …)`):
  - `v.up = max(2e-6, IniShare − 1e-6)`, `v.lo = v.up − 1e-6`.
  - If IniShare = 0, then `v.lo = 0`.
  - Plus `costParLin := 1e-10` for RU (ad l.802-805).
- **max**: `costParLin := 1e-10` (l.806-809). No AD-specific bounds, so v is free in [0, MaxShare]. Observed: v reaches MaxShare (DE110000 DCOL 0.739236).
- **off (simulation)**: generic bounds only. AD is not fixed even if Max = Ini, unlike the ammonia techs.
  - `ghgMitiTechMax=1` (not active here) would set `v.lo = min(p_accumShar(h500), v.up)` (`set_miti_bounds.gms:547-548`).
  - The ini-run marginal `costsavings0` correction for AD is **commented out** (`ammo_tech.gms:3384-3393`, `$ontext`).
    AD calibration is therefore self-contained in `ad_data_and_cali.gms`.

---------------------------------------------------------------------------------------------------

## 2. How each AD item is computed (`envind/ad_data_and_cali.gms`, `%ad_type%==anch`, l.123-1188)

### 2.1 Inputs loaded
- l.239-242 `$gdxin dat\scen\ghgtech\AD_basedata.gdx`: `ManSys`, `p_B0`, `p_VSER`, `p_MitiShar0`, `p_HousShar`, `p_SharLiq`.
- l.265-268 `gains_ad.gdx`: `gainsinfo`, `p_gainsdata`. Only `eprice_ind` and `eprice_agr` are used by anch.
- `prep_farm_size_data_for_miti.gms:50-53` (same AD_basedata.gdx): `Allanimals`, `AD_Activity`, `fsclass`, `p_Heads`, `p_sf`.
- Optional, off by default: `%storgrazInv%==on` replaces MitiShar0 with `ghgInvData.gdx p_shareADInv` (l.245-255).
  The default `STORGRAZINV OFF` is set in `capreg/set_global_variables.gms:120`.
- Hard-coded in code:
  - `p_MCF` table (l.324-348). The `p_MCF` in AD_basedata is **not** loaded.
  - Scalars l.381-402: ManStor 1, PreDigCO2 0.02, PreDigCH4 0.25, MCFDig 0.85, CH4leak 0.03, DensCH4 0.6557, EContCH4 55,
    EConvCH4 277.8, EfHeat 0.4, EHsold 0.3, prheat 0.03, EfElec 0.36, ELused 0.12, prelec 0.10, SubsAD 0, r 0.05 (**effectively 0.035**, see §0.3),
    t 15, alpha −1009.332, beta 10381.16, COp 0.05, engh 7000.
  - `p_sizeControl` (prep l.85-96).
  - Mappings `map_animals` (l.282-300), `map_gainsCount` (l.157-189; **no LUXE entry**, so LU uses the 0.10/0.03 defaults) and `map_gainsact1` (l.202-219).
- From CAPRI elsewhere:
  - `EMISCALC(DE,GE,ASH,YM)`, `p_animReqSubEne` (`%scrdir%\animReqSubEne.gdx`, l.78), `p_technFact` and `data(levl)`.
  - `p_Nemidat` TypeShare Liquid/Graz/Solid.
  - `p_shareClimZone` (`dat\envind\climdat_gascoeff.gdx`, `envind/gascoeff.gms:522-544`; "10"=100 where no cells).
  - `p_infl` (1.019, `captrd.gms:327`), `CALYEA`.

### 2.2 Volatile solids VSER (l.49-116, 424-430) [S; cattle values implied V]
- `NEG = 1.164 − 0.00516·DE + 1.308e-5·DE² − 37.4/DE` and `GENE = 1.123 − 0.004092·DE + 1.126e-5·DE² − 25.4/DE`, with DE in % (EU000000 fallback).
- `GE_intake = Σ_SUBENE p_animReqSubEne / (NEG if SUBENE=NEG else GENE) / (DE/100)`, only for animals with YM.
- `VSER [kg VS/hd/d] = GE_intake / (GE·4.184 or 18.45) · (1 − DE/100 + 0.04) · (1 − ASH/100)` (l.100-107, IPCC 10.24).
- MS value = levl-weighted mean of RU values (l.112-115). RU gaps are filled from MS (l.116). Anything still missing comes from
  table `p_VSER` via `map_animals` (l.424-430).
- Pigs end up on the table value (DE/NL/DK SWIN 0.38, PL 0.40), reproduced exactly [V]. Cattle are endogenous.
  Implied values from res2 [V-derived]:

  | Region | DCOL | BULL |
  |---|---|---|
  | DE110000 | 6.3744 | 2.8862 |
  | NL220000 | 4.6941 | 2.3657 |
  | PL220000 | 4.3148 | 2.6744 |
  | DK000000 | 5.6920 | 2.1166 |

  Table values are DAIRY 5.1 and NDAIRY 2.6.

### 2.3 Energy, cost per size class, cost curve (l.404-571)
1. `p_Heads(srnuts2,ad,fs)`, used only if the region has no heads for that animal:
   - Taken **per class** from NUTS1 if NUTS1 has that class, else from NUTS0 (l.405-409).
   - Example: DE110000 DAIRY takes DE100000 classes 0_5..200_500 and DE000000 h500. This reproduces MaxShare exactly [V].
   - Translated to `maact` by levl × class shares of the AD_Activity (l.412-415).
2. `p_sf`:
   - Values outside `p_sizeControl` are zeroed (upper bound except h500, l.417; lower bound, l.418).
   - Then filled per class from NUTS1, else NUTS0 (l.420-422).
3. Volatile solids and climate (l.423-430, 456):
   - `p_VSER` is copied down to NUTS1/NUTS2 and to maact (l.423-430).
   - `p_shareClimZone` RU gaps are filled from MS (l.456).
4. `ECH4 [kWh/hd/yr] = VSER·365·1·B0(EU,a)·Σ_c sh_c/100·(1−0.02−MCF_nc(c)·0.25)·0.85·0.97·0.6557·55·277.8/1000` (l.459-463).
5. `CAD(fs) [€/hd/yr] = kW·(α·ln(kW·sf(fs)) + β)·(CRF(r,15)+0.05)`, with `kW = ECH4·0.36/7000` (l.465-468), `CRF = r/(1−(1+r)^−15)`, **r=0.035**.
   Note that `sf` is in LSU per farm while kW is per head.
6. Cumulative shares and costs:
   - `accumShar(fs)` = heads in classes ≥ fs / total heads.
   - `accumCost(fs)` = head-weighted mean CAD over classes ≥ fs (l.479-487).
   - Classes without sf have CAD = 0 but their heads still count in the denominator.
7. `MaxShare = p_MitiSharMx` = heads in {200_500, h500} / total heads (l.490-491).
8. Two-point fit:
   - `accumShar1/accumCost1` use {h500, 200_500} if h500 has heads, else {200_500, 100_200} (l.497-507).
   - RU without heads in either class falls back to MS (l.510-517).
   - Model `ADCali` (l.520-562) is two equalities with SLOPE, INDEP ≥ 0, which gives the line through the two points:
     `SLOPE = (C₂−C₁)/(S₂−S₁)`, `INDEP = C₁ − SLOPE·S₁` [V].
   - Edge case: h500 heads present but 200_500 zero gives `INDEP = 0` (second equation 0 = 0·S + I) **[U, untested]**.
9. `p_ghgAD`: SLOPE, INDEP, IniShare = MitiShar0 and MaxShare = MitiSharMx (l.565-572).

### 2.4 Mapping into p_ghgMiti(rs,maact,"AD_AnCh","CH4MAN",·) (l.587-640)
- First clear `gainsTech` CH4MAN and CH4MAN_3K (this includes NOC, the cause of §1.3) and AD (l.587-591).
- Then `IniShare←IniShare`, `MaxShare←MaxShare`, `costParSqr←SLOPE`, `costParLin←INDEP` (l.598-600, map l.315-321).
- **IniShare**:
  - `p_MitiShar0` = 0 is flagged as 0.001 (l.440). It is copied NUTS0 → NUTS1 → NUTS2 → maact (l.440-446) and reset to 0 (l.603-605).
  - Then `IniShare := IniShare · SharLiq(ms,a)·HousShar(ms,a) / (L(ms,a)·(1−G(ms,a)))` (l.610-613).
  - `SharLiq` and `HousShar` are mapped to maact at NUTS0 (l.449-450). HousShar is set to 1 for PIGF, SOWS, POUF and HENS if missing (l.451-454).
  - Net effect: **reported SHARE (ini) = MitiShar0·SharLiq·HousShar − 1e-6·L(1−G)**, verified for all 16 cases [V].
- `IniShare` and `MaxShare` are set to 0 where `L(1−G)` = 0 (l.615-620).
- `costParSqr := 2·costParSqr` (l.629-630; cost model `κ1 + ½κ2·m`).
- NOC: `MaxShare = 1`, `IniShare = 1 − IniShare_AD` (l.634-640).

### 2.5 Revenue and CO2FES (l.642-670)
- Electricity price: `eprice_ind`. Heat price: `0.5·eprice_agr`. Both come from `p_gainsdata` via `map_gainsCount` and
  `map_gainsact1` (DL_L, OL_L, PL_L); the defaults are 0.10 and 0.03 (l.645-650).
- `revenue = ECH4_gross · (0.4·0.3·P_heat + 0.36·(1−0.12)·P_elec) + SubsAD(=0)` (l.655-661).
  `ECH4_gross` is the same expression as ECH4 above. The prices are base-year-ish, "primes estimates for 2030 in base-year prices".
- `CO2FES = ECH4_gross · (0.4·0.3·0.26 + 0.36·0.88·0.33)` in kg CO2eq/hd/yr (l.664-670).

### 2.6 QEmitt (l.676-739)
- Formulas as in §1.3:
  - NOC l.710-715.
  - AD l.725-737, with the condition that Liquid exists and (Slope or Indep) ≠ 0.
  - `p_adEmis` l.676-701.
- `CH4MAN_3k` QEmitt for AD is set to EPS (l.739).
- NOC CH4MAN_3K is set to EPS only where it is already nonzero (l.717), which makes it ineffective after l.588.

### 2.7 Scaling by L(1−G) (l.747-765)
`costParLin`, `costParSqr`, `revenue` and `CO2FES` are each multiplied by `L(ms,a)·(1−G(ms,a))`.

### 2.8 Final steps (l.793-809)
- Remaining othImpact entries are zeroed where QEmitt = 0 (l.793).
- `mitiTech_map` is set where `costParLin` ≠ 0 (l.795).
- In ini and max runs, `costParLin` is set to 1e-10 for RU (l.802-809).

### 2.9 Calibration (`ghgTechCali off` only, l.816-1170) [S, not checkable: no simulation-run output available]
1. `MaxIncrease = max(1e-4, (Max−Ini)/Max)` (l.824-827).
2. Relative subsidies are assigned case by case. Cases apply only where `mitiTech_map(·,adImpact)`, i.e. CH4MAN, and later assignments win:
   - Case 1 (l.837-844): `costParLin>0`, `revenue=0`, `Ini>0`. `relSubs1 = 0.8·sensFac·MaxIncrease`. Does not occur when revenue > 0.
   - Case 2 (l.852-862): (`cpl<0` or `rev>0`) and `Ini>0`. `relSubs1 = (−0.2$cpl<0 + 0.2$(rev·cpl>0))·sensFac·MaxIncrease`.
     **This is the usual AD case and gives 0.2·MaxIncrease. relSubs0 is not set, so it stays 0.**
   - Case 3 (l.869-883): `cpl>0`, `Ini=0`. `relSubs1 = 1.2·sensFac`, `relSubs0 = 0.2·sensFac`.
   - Case 4 (l.891-915): (`cpl<0` or `rev>0`) and `Ini=0`. `relSubs1 = ±0.5·sensFac`, `relSubs0 = ±0.1·sensFac`.
     It overwrites case 3 when rev > 0.
   - Then `Subs1 = relSubs1·costParLin` and `Subs0 = relSubs0·costParLin` (l.921-925).
3. Initial pmp terms: `pmpParSqr = 0` (l.939), then `pmpParLin = −costParLin + revenue + Subs0 − costParSqr·IniShare` (l.946-954; FOC at m0).
4. `RespShareVersion` is set to `yes` at l.126, so **Version B** applies (l.1105-1160):
   - `m_zero = (Subs1−Subs0)/costParSqr + Ini`
   - `mup = min(1.5·Max, 1)`, `mlo = max(0.5·Max, 1.1·Ini)`
   - If `m_zero > mup`: `pmpParSqr = (Subs1−Subs0)/(mup−Ini) − costParSqr`.
   - If `m_zero < mlo`: `pmpParSqr = (Subs1−Subs0)/(mlo−Ini) − costParSqr`. This can be negative.
   - `pmpParLin = −costParLin + revenue + Subs0 − (costParSqr + pmpParSqr)·Ini` (l.1151-1160).
   - Version A (l.966-1101) is inactive.
5. l.1172 zeroes all AD items where QEmitt = 0.
6. Inflation (l.1175-1177): `mitiCostfPars` = {costParLin, costParSqr, pmpParLin, pmpParSqr, revenue, subs0, subs1} (`sets.gms:9485-9493`)
   are multiplied by `p_infl^(2030−BAS)` = **1.019^13** where mapped [V]. CO2FES and othImpact are not inflated.
   Because every term is scaled by the same factor, the FOC still holds.
7. Edge case **[U]**: if `IniShare > MaxShare`, the calibrated FOC point lies outside `[0, MaxShare]` in the off run.

---------------------------------------------------------------------------------------------------

## 3. Inputs vs available CSVs

`capri_data/sources/capri_dat/ghgtech/` (format `dim1,…,level,marginal`):

| GAMS symbol (source) | CSV | Used by anch? | Notes |
|---|---|---|---|
| `p_B0` (AD_basedata) | `AD_basedata_p_B0.csv` (EU000000 × DAIRY/NDAIRY/SWIN/HENS/POUF/SHEEP) | yes | m³ CH4/kg VS |
| `p_VSER` | `AD_basedata_p_VSER.csv` (NUTS0 × AD_Activity) | fallback only (pigs) | kg VS/hd/d |
| `p_MitiShar0` | `AD_basedata_p_MitiShar0.csv` (NUTS0 × DAIRY/NDAIRY/SWIN) | yes | |
| `p_HousShar` | `AD_basedata_p_HousShar.csv` (NUTS0 × DAIRY/NDAIRY/SHEEP) | yes | pigs default to 1 |
| `p_SharLiq` | `AD_basedata_p_SharLiq.csv` | yes | |
| `p_Heads` (prep_farm_size) | `AD_basedata_p_Heads.csv` (NUTS0/1/2 × AD_Activity × fsclass) | yes | also copied to `2017/abatement/ammonia/p_Heads.csv` |
| `p_sf` | `AD_basedata_p_sf.csv` (region × fsclass) | yes | LSU per farm |
| `Allanimals`, `AD_Activity`, `fsclass`, `ManSys` | `AD_basedata_*.csv` | sets | |
| `p_MCF`, `p_Clima`, `p_CorrFac`, `Temp`, `Dairys`, `Nondairy`, `Pigs` | `AD_basedata_*.csv` | **not loaded** by anch | p_MCF is hard-coded l.324 |
| `p_gainsdata`, `gainsinfo` | `gains_ad_p_gainsdata.csv`, `gains_ad_gainsinfo.csv` | `eprice_ind`, `eprice_agr` only | €/kWh |

Inputs not in these CSVs:

| Input | Where it is | Status |
|---|---|---|
| `p_Nemidat` TypeShare Liquid/Graz (Solid = 1−Liquid) | `capri_data/2017/abatement/ammonia/n_cascade_factors.csv` (`tsl`, `tsg`) | available, reproduces [V] |
| `p_litRevAmmoTechsAdd(·,"AD_AnCh",·,LIQUID,·)` | `capri_data/2017/abatement/ammonia/p_litRevAmmoTechsAdd.csv` | available |
| `p_shareClimZone` (climcels 10..28 %) | `capri_data/2017/environment/climate_zones.csv` (same 522 rows as CAPRI's AD_basedata p_Clima; the copy under capri_data/sources, read by no code, removed 29 October 2026, K102) | available. Gascoeff rule "10"=100 where no cell rows (`gascoeff.gms:543-544`) must be applied. DE/NL/PL/DK only have "Cool", so cell 10 applies (MCF 0.17) [V] |
| `EMISCALC(r,a,"T","DE"/"GE"/"ASH"/"YM","Y")`, `p_animReqSubEne` (`%scrdir%\animReqSubEne.gdx`) | not in capri_data | **missing**. Needed for cattle VSER. The port has partial GE pieces (`tools/build/build_enteric_feed_factors.py`) but no DE/ASH/sub-energy requirements |
| `EMISCALC(r,a,A,"CH4MAN","Y")` (baseline CH4MAN EF) | not found as such | **missing** for exact CH4MAN; the per-head ratio QE_AD/QE_NOC is computable |
| `p_animProdDays`, `DATA DAYS`, `v_actLevl` | port | available |
| `p_infl` = 1.019, BAS = 2017 | port applies 1.019^13 and divides by the model's deflator to 2030 (the same index): the terms in 2017 money (KNOWN_ISSUES K108, 31 October 2026) | available [V] |
| NUTS1→NUTS2 map (`map_rr(srnuts1,srnuts2)`) for the per-class fallback | **[U]** check that the port has it | DE110000 → DE100000 assumed and verified via MaxShare |
| `fallback_Balkan`, `p_farmsTotal`, `p_LUUnits`, `data levl/days` for non-EU NLP `m_fsclass` (prep l.439-495) | prep file, `dat\policy\livestock_units.gms` | needed only for MSnoEU/Turkey |
| `ghgInvData.gdx p_shareADInv` | not present | needed only if `storgrazInv on` (default off) |

Nothing in `/mnt/user-data/uploads` adds AD inputs beyond the above:
- `scen.zip` contains the same AD_basedata symbols.
- `costsavings_ini/max_21730_jul15.csv` contain `v_Miti` levels and bounds. These are useful for validation, not as inputs.

---------------------------------------------------------------------------------------------------

## 4. Check against CAPRI output (ini run)

Relevant keys in res2:
- `'R'.''.a.'AD_AnCh'` and `'R'.'SHARE'.a.'AD_AnCh'`: reported share.
- `'R'.'MaxShare'.a.'AD_AnCh'`.
- `'R'.'cost'.a.'AD_AnCh'` and `'R'.'revenue'.a.'AD_AnCh'`: € per head at 2030 prices. These equal `mitiRev` and part of `mitiCost`.
- `'R'.''.a.'CO2FES'`.
- Regional rows `'R'.''.'CH4MAN'|'N2OMAN'|'NH3MAN'|…|'GWPT'|'mitiNetC'|'mitiEff'|'SHARE'.'AD_AnCh'`.
- Activity aggregates (DCOW, RUMI, AGGT, …) are weighted by `p_mitiWeight` (`sol_simy.gms:1583-1600`).

Results (script above). All 16 cases are DE110000, NL220000, PL220000 and DK000000 × DCOL, BULL, PIGF, SOWS:

| Item | Formula (ini) | Result |
|---|---|---|
| SHARE | `MitiShar0·SharLiq·HousShar − 1e-6·L(1−G)` | exact (diff/L(1−G) = 1.00e-06 in all 16) |
| MaxShare | `heads(200_500+h500)/total · L(1−G)` (per-class NUTS1/NUTS0 fallback) | exact, e.g. DE110000 DCOL 0.635378 |
| revenue | `REV/hd · infl · SHARE · DAYS/365`, `REV/hd = ECH4(VSER)·(0.12·P_heat + 0.3168·P_elec)` | pigs: implied VSER = 0.3800000 / 0.4000000 = table value, exact; cattle: implied VSER as in §2.2 |
| cost | `(1e-10·v + ½·costParSqr·v²)·DAYS/365`, `costParSqr = 2·SLOPE·L(1−G)·1.019^13` | ratio model/CAPRI 1.0000000 in all 16 cases with **r = 0.035** (1.069557 with r = 0.05) |
| CO2FES (pigs) | `−CO2FES(MS)·v·days/365` (`gases.gms:976-977`) | DE PIGF 1.06149 vs 1.06150; DK PIGF 1.5610 vs 1.56096 |
| CO2FES (cattle) | first formula `gases.gms:956-974` (EMISCALC VSER, density 0.67, odd `EMISCALC(…,"CO2FES")·0.25` term) | not reproduced, DK DCOL off by about 0.7%. Reporting only **[U]** |
| CH4MAN per head, ini vs max ratio | `(1−v(1−r))` ratio | PIGF exact; BULL within 0.6%; **DCOL: no AD effect** (§1.3) |
| Regional `'CH4MAN'.'AD_AnCh'` (`miti_report.gms:1084`) | needs EMISCALC CH4MAN | **not reproduced** (missing EF0) |

Example, DE110000 DCOL:
- L(1−G) = 0.919999·(1−0.065753) = 0.859507.
- v = 0.0543637 (costsavings_ini v_Miti.L). IniShare = 0.0543647.
- MaxShare (raw) = 683350/924400 = 0.739236 (v.UP in the max run = 0.739236 [V]).
- SLOPE = 26.700 and INDEP = 145.826 €/hd/yr (before L(1−G) and inflation), so costParSqr(2030) = 2·26.700·0.859507·1.27722 = 58.62.

---------------------------------------------------------------------------------------------------

## 5. Reported AD share vs v_Miti (the NH3STO/NOXSTO/N2OHOU/N2OAPP puzzle)

The reported SHARE is not v_Miti:
```
sol_simy.gms:959       p_ghgMiti(RU,PACT,tech,target,"share") = v_Miti.l
sol_simy.gms:965-968   p_ghgMiti(RU,MPACT,tech,"emisAll","share") = Σ_target share
sol_simy.gms:990-992   p_ghgMiti(RU,MPACT,"ad_anch","emisAll",mitiRepSh)   (mitiRepSh = {share, MaxShare}, sets.gms:9377)
                         = Σ_{MAP_RR(MSAGG,RU)} … · (1 − Nemidat(MSAGG,"Graz")) · Nemidat(MSAGG,"Liquid")
sol_simy.gms:1428      DATA(RU,MPACT,tech,SIMY) = p_ghgMiti(RU,MPACT,tech,"emisAll","share")   (MSAGG: l.1556; the ''/'SHARE' rows)
```

So `SHARE_reported = v·L(1−G)`, and `MaxShare_reported = MaxShare·L(1−G)`. Both are verified [V].

The supply model applies `v · p_ghgMiti(AD,"OthImpact",X)`, and `ammo_tech.gms:2330-2344` already multiplied that parameter by `L(1−G)`. The per-head effect is therefore:
```
v · litRev_X · L(1−G) = litRev_X · SHARE_reported
```
This is exactly what the earlier check found. There is no ordering problem:
- `mitiTech_map(rs,a,"AD_Anch","CH4MAN")` is set at `ad_data_and_cali.gms:795`.
- `capmod.gms:1112` includes that file before `ammo_tech.gms` (l.1113), so the l.2318-2344 assignments and the rescaling do execute.
- They use `p_Nemidat(nuts0,…)`, the same values as the report's `MSAGG` = NUTS0. Only one aggregate maps to each RU, as the exact SHARE match shows.

The same identity holds for costs and revenue: `€/avg head = revenue_per_digested_head · SHARE_reported`.

---------------------------------------------------------------------------------------------------

## 6. Points where the port may deviate from CAPRI (for the user to decide)

1. **Dairy CH4 effect (§1.3).**
   - CAPRI: none, because of l.588.
   - My view: a fix is better. Apply `(1−v) + v·QE_AD/QE_NOC` to DCOL/DCOH as well (the CH4MAN_3k terms are EPS/0 anyway).
     The intent is evident from l.717/l.739, and `miti_report` already reports dairy reductions.
   - For CAPRI-reproduction runs, replicate the CAPRI behaviour behind a switch.
2. **Discount rate.** CAPRI effectively uses 0.035 through compile-time override, against the 0.05 written in the AD file.
   Use 0.035 to reproduce CAPRI and flag the issue.
3. **MS-level QEmitt** in the supply model vs **RU-level** in `miti_report`. The ratio does not depend on VSER, so they differ
   only if RU climate cells differ from MS. Follow the supply model (MS).
4. **Unit mismatch.** `p_CAD` uses kW per head × farm size in LSU. This is CAPRI as coded; replicate it.
5. **Prices.** The cattle VSER used for cost and revenue comes from base-year feed (comment l.96-98). Revenue uses GAINS prices,
   not CAPRI energy prices. Replicate both.
6. **Existing ammonia builder.** It falls back to national heads, a registered simplification. AD needs CAPRI's per-class
   NUTS1→NUTS0 fallback to reproduce MaxShare and the cost curve (DE110000 depends on it).
