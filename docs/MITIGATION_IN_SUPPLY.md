# Mitigation options inside the supply model

Status: revised 20 October 2026 against the code. Run results of the sprints in which the options were built were
removed (they predate the NLP form, the N loss cascade and anaerobic digestion); current results are in README section
11, adoption against JRC121368 Table 17 is printed by `tools/check/compare_runs.py --capri`, changes are in CHANGELOG.md.

CAPRI chooses its mitigation options inside the regional supply model (supply/supply_model.gms, ghgAbatement block):
in JRC121368's Farm-to-Fork run they were adopted without a carbon price, because the nitrogen target and the prices
made them pay (report Table 17: storage covers 14 -> 34%, precision farming 0 -> 35%, air purification 0 -> 10%,
higher milk yield 0 -> 15%). capri-mod does the same: the options are columns of each regional model (always: the switch
`use_manure_techs` was removed on 27 October 2026; feeding is always inside the models),
the baseline included. In the default NLP form they are written in `capri_regional_nlp.CapriRegionalNLP._abatement_block`
(ammonia options, AD, fertiliser options, inhibitor on manure, winter cover) and as linear columns the supply module
adds to the regional model (breeding, low-N feed, linseed and nitrate, histosol fallowing; until 26 October 2026
columns of the regional QP).

| Option (CAPRI) | CAPRI file | capri-mod | Data |
|---|---|---|---|
| Ammonia options: LowEmHous, CovStorLow, CovStorLowCon, CovStorHigh, ManStorCon, AirPur, AirPurCovLow, AirPurCovLowC, AirPurCovHigh, ManAcid, AmmAppLE, AmmAppHE | envind/ammo_tech.gms | in, with CAPRI's N loss cascade (`n_cascade.py`, K51) | `tools/build/build_ammonia_tech_model.py` |
| Anaerobic digestion (AD_AnCh) | envind/ad_data_and_cali.gms | in (`docs/AD_SPEC.md`); CH4 effect also for dairy cows (the user's decision, README 5.2) | `tools/build/build_ad_option.py` |
| Fertiliser options PRECFARM, VRT_SRUC, FERTTIME, NITR_INH; inhibitor on manure | ghgMiti.gms, miti_data | in | `fert_options_jul15.csv` (`tools/build/build_fert_options_jul15.py`, CAPRI's miti_data_jul15) |
| Breeding: milk yield (genet_yld), feed efficiency (genet_eff) | envind/breeding.gms | in | `tools/build/build_genetics_effects.py` |
| Low-N feed (LowNFeed) | envind/low_n_feed.gms | in | `tools/build/build_lownfeed_effects.py` |
| Linseed (LINE), nitrate (NITR), their combination (AComLN) | envind/line_nitr.gms | in | `tools/build/build_supplement_effects.py` |
| Winter cover (WinterCov) | envind/cover_crops.gms | a choice of the regional model with CAPRI's cost curve, the Farm-to-Fork requirement as its floor (`capri_regional_nlp.py`, catcMiti_; docs/WINTER_COVER.md); it acts in the cascade and in leaching | `cover_crops.csv`, `p_winterCoverShare0.csv` |
| Histosol fallowing (FALLOW) | envind/no_histosols.gms | in, as a linear column (approximated) | `histosol.csv` |
| Legume share (LegSh), tillage (ConsTill, NoTill), urea substitution (UreaSubst), buffer strips, biodiversity options, biochar | various | not built; their LEACHN_/RUNSURFN_ terms held at CAPRI's reference | - |

The active set is CAPRI's Green Deal reference (`pol_input/greendeal/refpol_endotech_all_sup.gms`, activeTech;
`capri_data/2017/abatement/active_technologies.csv`). The copy of the JRC121368-era reference supplied with CAPRI
switches the ammonia options off, while the report's Table 17 shows them adopted; capri-mod follows the report.

## CAPRI's formulation

Technology table (`p_ghgMiti`; ammonia options computed at run time by `envind/ammo_tech.gms`): per region, animal
activity and option, linear and quadratic costs (kappa1, kappa2, from GAINS-type cost curves by farm size), initial and
maximum shares, remaining emissions (`qemitt`, no technology = 1) and side effects (`othImpact`).

Bounds (`supply/set_miti_bounds.gms`): 0 <= share <= MaxShare; "no technology" up to 1.

Cost (`supply/supply_model.gms`, `GHG_Mit_Cost_`), per option, multiplied by the animal stock (activity level x
production days / 365, since costs are per animal place):

    (kappa1 + beta) s + 1/2 (kappa2 + gamma) s^2 - revenue s - subsidy s

Calibration (end of `ammo_tech.gms`): beta from the first-order condition at the initial share m0,
kappa1 + beta + kappa2 m0 - subsidy - revenue = 0, corrected by `costsavings0`, the marginal value of the share in a
base calibration run (chiefly the mineral fertiliser that retained manure N replaces). Base shares are optimal with
their fertiliser savings counted; a binding N target adds its shadow price.

## Ammonia options

Data: `tools/build/build_ammonia_tech_model.py` -> `ammonia_tech_model.csv`, one row per model region, animal, CAPRI
sub-activity (DCOL/DCOH, BULL/BULH, PIGF/SOWS, ..., weighted by heads) and option; `capri_mod/supply/ammonia_techs.py`.

1. Groups (`TotMit_`): housing, storage covers, concrete basins, air purification, acidification and their
   combinations are alternatives of one target (NH3MAN, group MAN); with "no control" their shares sum to at most 1.
   Application options form NH3APP (group APP). AD is a group of its own.
2. Calibration (`ammo_tech.gms` l. 2860-3340): marginal cost of share s per animal place S0 + (kappa2 + gamma)(s - s0).
   Relative subsidies for the maximum and for early adopters: m0 > 0: 0.8 x MaxIncrease and 0; m0 = 0: 1.2 and 0.2.
   Application, acidification and poultry/sheep options: gamma = (S1 - S0)/(m1 - m0) - kappa2; options with farm-size
   cost curves: CAPRI's "VERSION B" bounds the share that S1 reaches to [max(0.5 m1, 1.1 m0), min(1.5 m1, 1)]. In the
   NLP form the calibration of the regional model then sets each option's linear term so that its base share is a
   first-order point.
3. Effects: CAPRI's loss cascade (GRAZN_ ... GASRUNTOTN_; `docs/N_CASCADE_SPEC.md`). The N the options keep from
   losses enters the manure applied (ManureNPK_) and so displaces purchased mineral N in NUTNED_; the NH3 part goes to
   the ammonia accounts, the N2O by stage to manure N2O. In the conic form the cascade enters as its tangent at the
   previous solve (K1). Where a region has no cascade factors, `ammonia_techs` falls back to an NH3-only cascade.
4. Reporting: Table 17's baseline column equals CAPRI's initial shares as shares of all animal units weighted by
   excreted N, not of eligible units; the model reports on that basis.

REGISTERED: urea substitution is not built; the Nitrates Directive minimum shares are built but not applied (K51).

## Fertiliser options (target N2OSYN)

- Active set: `ghgTechActiveFert` of `refpol_endotech_all_sup.gms`: PRECFARM, VRT_SRUC, FERTTIME, NITR_INH. The GAINS
  combinations (GComTN, GComVN) and VRT_L/M/H are not active there and not offered (`_fert_techs` keeps the active
  options only). Data from CAPRI's `miti_data_jul15` (the data the Green Deal runs use); nitrification inhibitors as CAPRI sets them (QEmitt = 0.9 x no control, NMIN
  0.09, capped by over-fertilisation), also on applied manure (N2OMAN).
- Form: one regional share per option (CAPRI's v_Miti(cropMiti, tech)); mineral N x (1 + sum share NMIN) in NUTNED_;
  shares sum to at most 1 and 1 + sum share NMIN <= max(over-fertilisation factor + 0.1, 1) (`Tot_MitFert_`). The
  conic form uses one share per crop (REGISTERED; the NLP check found the same optimum in five regions).
- Cost: per tonne of crop mineral N (`GHG_Mit_Cost_` multiplies by mineral N x (1 + E)), not per hectare.
- Calibration (`ghgMiti.gms`): relSubs1/relSubs0 = 1.2/0.2, or 0.8/0 where the regional maximum share is below 1
  ("already adopted"); S0 = relSubs0 kappa1, slope = kappa1 (relSubs1 - relSubs0)/(m1 - m0).
- Inhibitor on manure: one regional share, manure N x (1 + share NMAN) in NUTNED_, cost per t of manure N treated.

## Breeding (`envind/breeding.gms`)

Data `tools/build/build_genetics_effects.py` -> `abatement/mitigation/genetics_effects.csv`, per model region:

- genet_yld (dairy cows): CAPRI's yield gain, `ghgTechMYld` x the gap to the mean 2030 yield of Denmark, Portugal,
  Sweden and Finland, with breeding.gms's curbs (Croatia, Lithuania, Kosovo 0.6; Slovenia, Poland 0.2); requirements
  recomputed with breeding.gms's functions (energy NEL+NEM+NEP+NEA, protein, dry-matter limits), manure N from protein
  intake / 6 less milk N; cost max(EUR 20, 10% of the extra milk revenue) per cow.
- genet_eff (bulls, suckler cows, calves, fattening heifers HEIF, fattening sheep SHGF; not HEIR, not milk sheep, as
  breeding.gms): energy -10%, protein -5%, manure N = protein change x (MANN + N in meat) / MANN; cost max(EUR 2, 0.5%
  of annual feed cost).

Settings are scenario configuration, as in CAPRI: `ghgTechMYld` and `ghgTechFEff` are set in the reference technology
file the scenario loads (`greendeal_scenarios.gms` -> `refpol_endotech_all_sup`: ghgTechMYld 0, ghgTechFEff 0.1); a
value given at launch wins, and the same value holds in the reference and the policy run. capri-mod:
`capri_mod/policy/endotech.py` (star 3.0 defaults ghgTechMYld 0, so the milk-yield option does not exist, as
breeding.gms defines it only `$ p_ghgTechMYld`; ghgTechFEff 0.1), set through `run(endotech=...)` or
`PolicyScenario.endotech`; the table is written per unit of the parameter; the setting holds for the scenario and its
baseline (baseline cache and calibration kept per setting, K53). `run_f2f_2030.py --endotech jrc121368` gives the
JRC121368-era setting (milk yield 0.2, from CAPRI's ecampa reference `refpol_endotech_set14_ini.gms`).

Regional model (`_genetics_columns`, always on): one column per animal and
option, heads adopting g <= eligible share x level; effects on the manure rows and the animal's requirement rows;
extra milk at the current milk price; cost CAPRI's `GHG_Mit_Cost_` with breeding.gms's calibration: linear term from
the base duals plus relSubs0 x cost, so nothing is adopted at base (IniShare 0); curvature max(floor x c,
c (relSubs1 - relSubs0) - (costsaving0 - costsaving1)) per unit of the share of the eligible heads (floor 0.2), the
maximum share CAPRI's MaxShare (0.002 with fixGenet_eff_to_iniValues on, K67).

CAPRI calibrates breeding with two calibration runs of its supply model (the options' marginal value at the initial
shares and with every breeding, supplement and low-N feed option at its maximum share at once, supply/
set_miti_bounds.gms) and subtracts the fall of the marginal value between them from the planned slope: the planned
slope c (relSubs1 - relSubs0) is the total curvature of the option's net marginal cost, of which the model's own fall
is a part. Since 23 October 2026 (K67 F2) the model takes the fall from CAPRI's two runs
(capri_costsavings_2030.csv), per model head adopting (column dsav, tools/lib/_capri_costsavings.py); before, it was left
out under a registered deviation whose reasoning was reversed (leaving it out counts the model's own curvature on top
of the planned slope rather than avoiding a double count). Median fall per model head: genet_eff -1.7 EUR (the marginal
value rises towards the max run, so the slope is steeper than the planned one), nitrate +15, linseed +5.5, low-N feed
+0.1. NOTE: the fall is CAPRI's model's, not capri-mod's; capri-mod's own max run (an extra calibration solve per
region with the options held at their maximum shares) would be the self-consistent alternative, not built.

## Low-N feeding (`envind/low_n_feed.gms`)

star 3.0's Green Deal technology file sets `ghgTechLowNFeed = 1`; the option is a column of the regional models in the
breeding framework (`tools/build/build_lownfeed_effects.py`, `abatement/mitigation/lownfeed_effects.csv`):

- Effect (CAPRI's formulas per CAPRI activity, aggregated to the model's animals by CAPRI's 2017 levels): protein
  requirement x (1 - cut), cut = 0.15 x protein excess / (1 + 0.5 x energy excess), the excesses being CAPRI's
  requirement corrections p_animReqCorrFac; manure N x (1 - cut (MANN + CRPR_EXPT) / MANN).
- Eligible shares = CAPRI's max calibration run (monogastrics 100%, dairy cows 72% = stable time, other cattle 27%,
  sheep and goats 14%).
- Cost = feed cost per head x 0.06 x cut / (protein excretion factor - 1 - cut), calibrated as CAPRI (relSubs0 0.2,
  relSubs1 0.8, curvature floor 0.05 per unit of the eligible share); not adopted at base.

REGISTERED: the cost is CAPRI's at ghgTechLowNFeed = 1 (it is not linear in the parameter); the excesses are CAPRI's
2017 corrections; lysine is not a model requirement. The fall of the marginal value between CAPRI's ini and max runs
is netted from the slope as CAPRI (dsav, as for breeding; since 23 October 2026).

## Linseed, nitrate and 3-NOP (`envind/line_nitr.gms`)

star 3.0's Green Deal technology file switches the supplements on (`ghgTechLineNitr = 1`; `ghgTechActiveFeed` = LINE,
NITR, AComLN, 3NOP, LowNFeed). They are columns of the regional models with feeding inside, one per region, cattle
animal and total (CAPRI's `LINE_Tot`, `Nitr_Tot`, `3NOP_Tot`) (`tools/build/build_supplement_effects.py`,
`abatement/mitigation/supplement_effects.csv`):

| | Linseed (LINE) | Nitrate (NITR) | 3-NOP (since 29 October 2026) |
|---|---|---|---|
| Animals | dairy 100% of stable time, other cattle 50% | dairy 10/12 of stable time; bulls and replacement heifers 50%; never calves or suckler cows | dairy and suckler cows, stable time x 305/365 (the member state's (1 - grazing share)) |
| Maximum dosage (share of dry matter) | 5% fat | 1.5% (heifers 1%) | 0.09% (Bovaer10; 90 mg of active substance per kg DM) |
| Feed effect (REQSE_) | fed: fresh matter = DRMA x 5% / (40.5% fat x 89.9% DM), supplying the OOIL row of p_nutCont (energy 5.89, crude protein 0.22, DM 0.9 per kg) | replaces crude protein: requirement - DRMA x 0.0154 x dosage x 100 per head | none |
| Enteric CH4 (accounts) | -5% per point of fat (-25% at maximum) | -10% per point (-15%; heifers -10%) | -(32.36 + 0.282 (dose - 70.5) - 0.915 (NDF - 32.9) - 3.08 (FAT - 4.2)) %, the member state's ration NDF and fat (CAPRI's digestibility table and data, `tools/lib/_capri_digest.py`): -25% to -57%, median -35% (the most in the concentrate-rich rations of Croatia, Cyprus, Malta) |
| Cost | EUR 674/t x 89.9 / 40.5 per t fat | EUR 873/t | EUR 17,500/t of Bovaer10 (2022 money; deflated to 2017 with 1.019), not halved: about EUR 95 per dairy cow and year |

- On the same animals (AComLN) the CH4 factors of linseed and nitrate multiply, the overlap as large as the shares
  allow; 3-NOP adds (CAPRI's MC_GHG_Miti_Factor sums the options' shares times their QEmitt ratios).
- Maximum shares = the level of CAPRI's maximum calibration run + 2e-6 (line_nitr.gms caps MaxShare there); 3-NOP's
  CAPRI's formula, not capped by the maximum run (l. 340-343).
- Cost per head = costParLin x DRMA / 1000 x dosage, in 2017 money, halved for the cost savings (line_nitr.gms
  l. 357). Calibration as line_nitr.gms: zero at base, relSubs0 0.05, relSubs1 1.2, curvature floor 0.1 per unit of
  the eligible share, the fall of the marginal value between CAPRI's ini and max runs netted (dsav, as for breeding).
- CAPRI's MANN entry for nitrate (0.42) is defined but used by neither the supply model nor the accounts, so nitrate
  does not change manure N here either.
- `ghgTechLineNitr` is a switch (0 off, anything else on), not a scale. The older path with nitrate as an
  ingredient of the EU ration (`CAPRIModel.use_nitrate`, off) was removed on 27 October 2026.

REGISTERED: DRMA is CAPRI's own estimate from breeding.gms, DRMN + (|DRMX| - DRMN) / 4; CAPRI's soft constraint on
total ration fat (SupplementPerc_, 5% of DM) needs every feed's fat in the ration as it changes and is not carried,
its effect on the maximum shares being in the max-run caps. 3-NOP has no cost saving in CAPRI's calibration runs, so
without an emission price its share stays zero; it acts under the emission tax. Its CH4 effect takes the 2017 rations
(CAPRI's data(ru, act, feed, "Y")), summed per head over the member state's units as line_nitr.gms writes it.

## CAPRI's emission tax in the supply models

CAPRI prices emissions inside the supply model when a scenario switches `ghgTax` on (pol_input/ecampa/
carbtax50_endotech_set12.gms: p_carbonTax(ru, "GGWP") on the EU regions; supply_model.gms objective
- p_carbonTax x (v_CO2EquEmis(GGWP) - reference)). capri-mod (`capri_mod/supply/ghg_tax.py`) gives each column of the
regional problem tax x its emission per unit, taken at the baseline solution:

- activities, the grassland, dairy, bull and heifer splits, the breeding, low-N feed and supplement options and
  histosol fallowing: the change of the region's GHG total (`EnvironmentalModule.compute_indicators`) per unit of the
  column, by finite differences at the baseline;
- cattle feeding (CAPRI's feed-based CH4ENT): each flexible feed per t fed, dry matter x GE x 4.1868 x Ym / 55.65 x
  GWP(CH4); the fixed feeds' CH4 per head on the animal;
- ammonia options: their manure N2O through the cascade per unit of share, and the indirect N2O of the NH3 they keep;
- NLP form (`_nlp_tax_terms`): mineral N is the fertilisation block's purchases, taxed at the soil N2O factor (direct
  plus volatilised x indirect, with the nitrification inhibitor's side-effect factor on its share) and the indirect N2O
  of their runoff and leaching at the reference leaching share; the conic form's fixed-substitution terms on mineral
  N (manure trade, inhibitor on manure, N kept) are taken out. Conic form: those terms priced at the balance's
  substitution factor;
- Norway is not taxed (CAPRI: EU regions); the reference emissions (a constant) are left out.

Interface: `PolicyScenario.carbon_tax`, `carbon_tax_scenario(price)` (the tax as the only shock),
`CAPRIModel.run(carbon_price=)`, `tools/run/run_f2f_2030.py --scenario carbontax --carbon-tax 50`.

REGISTERED: the coefficients are held at the baseline solution; in the conic form the inhibitors' side effects are
linearised at no adoption and the manure inhibitors' tax value is weighted over animals by base manure N; the
land-market columns carry no coefficient of their own; no CAPRI tax run is in hand to compare with.

## JRC121368 Table 18 (for priorities)

CAPRI's technology contributions in Farm-to-Fork (kt CO2-eq, as reported): winter cover crops -16,097, peatland
fallowing -4,138, mineral-fertiliser application -3,568, nitrification inhibitors -1,771, feed additives -1,462,
anaerobic digestion -495; ammonia measures +922 and +5,240 (more N2O); no genetics line. Technologies give 38% of total
mitigation there, production changes the rest. Winter cover, the largest item, is a choice of the regional models (table above).
