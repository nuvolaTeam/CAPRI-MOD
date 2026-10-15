# Mitigation technologies inside the supply model — design and status

Status: **ammonia, fertiliser and cattle genomics options on CAPRI's structure and ON by default**
(`CAPRIModel.use_manure_techs`). Full-EU 2030 Farm-to-Fork: ammonia −34.9% (CAPRI −33%); adoption of
housing, covers and air purification within 2–7 points of JRC121368 Table 17. Cattle genomics
(October 2026) built inside the supply model, see "Genetics — implementation". Livestock-feed and soil
options still to come.

## Why

JRC121368's Farm-to-Fork run had CAPRI's mitigation technologies active (report Table 17):
manure storage covers 14 → 34%, precision farming 0 → 35%, air purification 0 → 10%, higher
milk yield 0 → 15%. There was no carbon price: farmers adopted them because the scenario's
nitrogen target and prices made them pay. In capri-mod only the fertiliser-efficiency
technologies respond inside the supply loop; the rest sit in a post-solve module driven by a
carbon price (zero in Farm-to-Fork), so they cannot move. This is the most likely cause of the
remaining gaps in ammonia (−19% vs −33%), enteric methane and part of the livestock results.

## CAPRI's formulation

**Technology table** (`p_ghgMiti`; ammonia options computed at run time by
`envind/ammo_tech.gms`): per region, animal activity and option — linear and quadratic costs
(κ₁, κ₂, from GAINS-style cost curves by farm size), initial and maximum shares, remaining
emissions (`qemitt`, no technology = 1) and side effects (`othImpact`).

**Bounds** (`supply/set_miti_bounds.gms`): 0 ≤ share ≤ MaxShare; "no technology" up to 1.

**Cost** (`supply/supply_model.gms`, `GHG_Mit_Cost_`), per option and multiplied by the
animal **stock** (activity level × production days / 365, since costs are per animal place):

    (κ₁ + β) s + ½ (κ₂ + γ) s² − revenue · s − subsidy · s

**Calibration** (end of `ammo_tech.gms`): γ = 0 for manure measures; β solved from the
first-order condition at the initial share m₀,

    κ₁ + β + κ₂ m₀ − subsidy − revenue = 0,

then corrected by `costsavings0`, the marginal value of the share in a base calibration run
(chiefly the mineral fertiliser that retained manure nitrogen replaces). So base shares are
optimal with their fertiliser savings counted; a binding nitrogen target adds its shadow price.

**Effects** in the supply model's emission equations: emissions × (1 − Σ othImpact × share) for
side effects, and `qemitt` for the main ammonia effect.

## capri-mod implementation (CAPRI's structure, October 2026)

Data: `tools/build_ammonia_tech_model.py` → `ammonia_tech_model.csv`, one row per model region, animal,
CAPRI sub-activity (DCOL/DCOH, BULL/BULH, PIGF/SOWS, …, weighted by heads) and option. Choice and
accounts: `capri_mod/supply/ammonia_techs.py`, used by the external rule
(`RegionalSupplyModel._apply_manure_techs`) and, linearised, by the conic model (`_tech_list`).

1. **Groups (`TotMit_`)**: housing, storage covers, air purification, acidification and the combinations
   AirPurCovHigh (pigs, poultry) and AirPurCovLow (pigs) are alternative manure systems of one target,
   NH3MAN; with "no control" their shares sum to 1. Application options form NH3APP. (Before: housing
   and storage were separate stages, so both could reach their maximum on the same animals.)
2. **Calibration (`ammo_tech.gms` l. 2860-3340)**: marginal cost of share s per animal place =
   S0 + (κ₂ + γ)(s − s0). Relative subsidies for the maximum and for early adopters: m0 > 0: 0.8 ×
   MaxIncrease and 0; m0 = 0: 1.2 and 0.2. Application, acidification and poultry/sheep options:
   γ = (S1 − S0)/(m1 − m0) − κ₂; options with farm-size cost curves: CAPRI's "VERSION B" bounds the
   share that S1 reaches to [max(0.5 m1, 1.1 m0), min(1.5 m1, 1)]. (Before: γ = 0, so application and
   acidification jumped to their maximum at any benefit and housing had a curvature of €0.004.)
3. **Effects (`HOUSN_`, `STORN_`, application)**: losses cascade - N kept in the house reaches storage
   and the field; low-emission housing also cuts storage NH3 by 80%; acidification by CAPRI's
   literature value. N saved per unit of share follows from the cascade at the current shares.
4. **Benefit**: N-balance price × substitution factor × N saved (base savings netted out, as CAPRI's
   `costsavings0`); scaled so the base loss equals CAPRI's 2030 NH3 share of excreted N.
5. **Reporting** (Table 17): the report's baseline column equals CAPRI's initial shares as shares of all
   animal units weighted by excreted N (housing 17 vs 12, covers 13 vs 14, air purification 0 vs 0), not
   as shares of eligible units (38, 33); the model reports on that basis.

Full EU, 2030 Farm-to-Fork (default model): ammonia −34.9% (CAPRI −33%); adoption, baseline → scenario:
low-emission housing 16 → 19% (CAPRI 12 → 12), covered storage 15 → 36% (14 → 34), air purification
0 → 14% (0 → 10), acidification 0 → 1%, low-emission spreading 41 → 73% (not in Table 17). Before:
housing 66%, covers 61%, air purification 31%, acidification 46%, spreading above 100%.

REGISTERED: other N gases are not subtracted in the cascade; concrete-basin options need CAPRI's
endoLeach (off); urea substitution is not built.

### Fertiliser options (target N2OSYN)

- **Active set**: CAPRI's Green Deal runs include `pol_input/greendeal/refpol_endotech_all_sup.gms`,
  whose `ghgTechActiveFert` list is PRECFARM, VRT_SRUC, FERTTIME, NITR_INH
  (`active_technologies.csv`). The GAINS combinations (GComTN, GComVN) and VRT_L/M/H were not active
  there; offered here, they took the over-fertilisation room and left precision farming at 1.5%.
  VRT_SRUC (farm-size cost curve, regional QEmitt) now comes from CAPRI's `miti_data_jul15` (the data the
  Green Deal runs use), as do all fertiliser options; nitrification inhibitors as CAPRI sets them
  (QEmitt = 0.9 × no control, NMIN 0.09, capped by over-fertilisation) and also on applied manure (N2OMAN).
- **Cost basis**: per tonne of crop N need (`GHG_Mit_Cost_` multiplies by mineral N × (1 + E)), not
  per hectare - the model had charged about ten times too much.
- **Calibration** (`ghgMiti.gms`): relSubs1/relSubs0 = 1.2/0.2, or 0.8/0 where the regional maximum
  share is below 1 ("already adopted"); S0 = relSubs0 κ₁, slope = κ₁ (relSubs1 − relSubs0)/(m1 − m0).
- **Choice**: first-order conditions per tonne of need, value λ NMIN/(1 + E)², with `TotMit_` and
  `Tot_MitFert_` multipliers.

## Remaining options (Table 17) — sources and data

| Options | CAPRI file | Data needed | Status |
|---|---|---|---|
| Nitrate, 3-NOP, linseed feed additives | `envind/line_nitr.gms` | `dat\feed\fedcof.gms`, costsavings max run | linseed and nitrate in the supply model (Sprint 9g); 3-NOP registered |
| Higher milk yield, feed efficiency, reproduction (genetics) | `envind/breeding.gms` | `results\baseline\trends_*.gdx`; feed-requirement functions (code) | data in hand |
| Winter cover crops | `envind/cover_crops.gms` | `dat\policy\wintercovershare.gms`, `dat\envind\tillageCover.gdx`, `dat\envind\ccEfa.gdx` | data in hand |
| Conservation and no-till | `envind/tillage.gms` | `dat\envind\tillageCover.gdx` | data in hand |
| Peatland fallowing | `envind/no_histosols.gms` | peat shares (converted) | data in hand |
| Low-protein feed | `envind/low_n_feed.gms` | p_animReqCorrFac (reqrel) | in the supply model (Sprint 9g); Table 17: not adopted |
| Vaccines, propionate precursors, legumes in grassland, digestion, fertiliser options | `p_ghgMiti` (public table) | in the project | data in hand |

## Feed additives (CAPRI `envind/line_nitr.gms`)

| | Linseed (LINE) | Nitrate (Nitr) | 3-NOP (Bovaer10) |
|---|---|---|---|
| Animals and maximum share | stable time: dairy 100%, other cattle 50% | dairy 10/12 of stable time; bulls and replacement heifers 50%; never calves or suckler cows | dairy (and suckler cows) 305/365 of stable time |
| Maximum dosage (share of dry matter) | 5% fat | 1.5% (heifers 1%) | 0.09% product |
| Enteric CH₄ | −5% per point of fat (−25% at max) | −10% per point (−15% at max) | regression on dosage, ration NDF and fat (about −30%) |
| Price (base year, inflated) | €674/t fresh → per t fat (89.9% DM, 40.5% fat) | €873/t | €17,500/t product (2022, deflated) |
| Feed interaction | adds energy (`OOIL` nutrient row) and fat; ration fat capped | replaces crude protein (1% → 1.54% CP of DM); N excretion +0.42% of DM intake | none |

Combined linseed and nitrate: effects multiply. Cost = share × dosage × dry-matter intake × price.
In CAPRI these are **ration ingredients**: a nitrate is adopted when protein feed is expensive, and its
extra nitrogen counts against a nitrogen target. Design consequence for capri-mod: add them to the EU
feed ration (`capri_mod/feed/ration.py`) with their dosage limits, nutrient contributions, prices and
methane effects, rather than as stand-alone shares like the ammonia measures.

**Status (nitrate), superseded by Sprint 9g below:** added to the EU feed ration as an ingredient (`RationModel.use_nitrate`, off).
Base rations unchanged (zero nitrate everywhere); with protein cake 20–100% dearer, nitrate enters
about a third of the 679 eligible rations at 26–47% of its limit. Before switching it on: pass its
methane cut and extra nitrogen excretion to the accounts and the nitrogen balance, and examine the
few rations that fail to solve at high protein prices. Linseed and 3-NOP are left out for now: they
only cut methane, which has no value without a carbon price (Table 17 lists neither).

**Update:** nitrate's effects are wired (`CAPRIModel.use_nitrate`, off): extra nitrogen excretion in
the regional nitrogen row and the accounts, extra ammonia, and enteric methane × (1 − 10 × nitrate
share). The Berlin failure is fixed (a region without substitution data). With the nitrogen target alone,
no ration adopts nitrate at the final iteration, but the run fails to converge: without curvature,
rations can jump between zero and the limit. Next: full Farm-to-Fork and a convergence safeguard.

## Status after the full Farm-to-Fork test (nitrate) and next step (genetics)

- **Nitrate**: with nitrate on, the 2030 Farm-to-Fork run converges and nothing changes (23 rations
  use negligible amounts). Its value is each ration's protein shadow price, which the ration
  calibration often puts near zero; nitrate stays off until that valuation is examined.
- **Genetics** (`envind/breeding.gms`), set in CAPRI's endotech reference: milk-yield potential 0.2
  (toward Denmark, Portugal, Sweden and Finland's projected yields), feed efficiency of non-dairy
  ruminants 0.1, cow longevity off. Table 17: higher milk yield 0 → 15%, ruminant efficiency 5 → 9%.
  Next to implement.
- **Note**: the supplied copy of that reference switches ammonia technologies off, but the report's
  Table 17 shows them adopted in the Farm-to-Fork run; the model follows the report.

### Genetics — CAPRI's definitions (`envind/breeding.gms`)

- **Higher milk yield** (dairy): target = mean 2030 projected yield of Denmark, Portugal, Sweden and
  Finland; gain at full adoption = 0.2 × min(own yield × (1 − curb), gap to the target), with curbs
  for Croatia, Lithuania, Kosovo (0.6), Slovenia and Poland (0.2). Feed requirements and manure are
  recomputed for the higher yield; cost max(€20, 10% of the extra milk revenue) per cow; net benefit
  calibrated to zero at base. Regional gains (`genetics_milk_yield.csv`): median 3.4%, up to 20%.
- **Feed efficiency** (non-dairy ruminants): energy requirement −10%, protein −5%, manure N
  accordingly; cost max(€2, 5% of feed cost per head), calibrated likewise.

### Genetics — calibration (decisive for the design)

CAPRI calibrates genetics adoption with **two calibration runs of the full model** (costs set to
~0): the marginal saving of each option at the initial share (`ini` run) and at the maximum share
(`max` run). The difference between them gives a quadratic cost term, γ = [sav₁ − sav₀ + …] / (m₁ − m₀),
so adoption slows as it spreads, by an amount measured in the model itself. With linear costs alone,
adoption would be all-or-nothing. Plan: compute the effects per region and animal; run the two
calibration runs in capri-mod (shares fixed at zero and at the maximum, marginal savings by finite
differences of each regional objective); derive γ and β as CAPRI does; then validate against
Table 17. Open: whether the cap on feed-efficiency adoption (`fixGenet_eff_to_iniValues`) was on in
the Farm-to-Fork run.

### Genetics — implementation (October 2026, default on: `RegionalSupplyModel.use_genetics`)

Data `tools/build_genetics_effects.py` → `abatement/mitigation/genetics_effects.csv`, per model region:

- **genet_yld** (dairy cows): CAPRI's yield gain (`ghgTechMYld` x the gap to DK/PT/SE/FI, curbs as breeding.gms);
  requirements recomputed with
  breeding.gms's own functions (energy NEL+NEM+NEP+NEA, protein, dry-matter limits), manure N from protein
  intake / 6 less milk N; cost max(EUR 20, 10% of the extra milk revenue). Median: milk +3.1% (up to 20%),
  energy +1.7%, protein +2.3%, manure N +1.7%; 72% of regions at the EUR 20 floor.
- **genet_eff** (bulls, suckler cows, calves, fattening heifers HEIF, fattening sheep SHGF — not HEIR, not
  milk sheep, as breeding.gms): energy −10%, protein −5%, manure N = protein change x (MANN + N in meat) / MANN
  (median −5.3%); cost max(EUR 2, 0.5% of annual feed cost).

**Technology settings are scenario configuration (October 2026).** In CAPRI `ghgTechMYld` and `ghgTechFEff` are set
in the reference technology file the scenario file loads (`greendeal_scenarios.gms` → `refpol_endotech_all_sup`:
`$if not SETGLOBAL ghgTechMYld $SETGLOBAL ghgTechMYld 0`, `ghgTechFEff` 0.1); a value given at launch wins, and the
same value holds in the reference and the policy run. The model does the same: the table is written per unit of
the parameter (every effect is linear in it, the cost is max(floor, linear term)), `PolicyScenario.endotech` or
`CAPRIModel.run(endotech=...)` sets the values (`capri_mod/policy/endotech.py`; default star 3.0: milk yield 0,
so the option does not exist, as breeding.gms defines it only `$ p_ghgTechMYld`), and they apply to the scenario
and the baseline it is compared with (the baseline cache and the genomics calibration are kept per setting).
`run_f2f_2030.py --endotech jrc121368` reproduces the JRC121368-era setting (milk yield 0.2, from CAPRI's ecampa
references `refpol_endotech_set14_ini.gms`).

Supply model (`_genetics_columns`): one column per animal and option, heads adopting g ≤ eligible share x
level; effects on the manure-driven rows and the animal's requirement rows in the feed block; milk revenue of
the extra milk at the current milk price; cost CAPRI's `GHG_Mit_Cost_` with breeding.gms's calibration —
linear term from the base duals + relSubs0 x cost (0.01 milk yield, 0.10 efficiency), so nothing is adopted
at base (IniShare 0); curvature γ = max(0.2c, c (1.2 − relSubs0)) per adopting head on the base level.
REGISTERED: CAPRI subtracts the fall of the option's marginal value between its ini and max calibration runs
from γ; here that fall is the supply model's own curvature and is not subtracted again. Accounts: milk output,
manure N (balance, N2O, NH3 via manure-equivalent heads), enteric CH4 through the feed.

Farm-to-Fork 2030 (full EU) at the JRC121368 setting (milk yield 0.2): higher milk yield 0 → 3.3% of dairy cows (JRC121368 Table 17: 0 → 15%), higher
ruminant efficiency 0 → 33% (5 → 9%). Gap 4.30 → 4.36 (beef animals −14.5 → −13.5%, CAPRI −18). Both depart
the same way as the other nitrogen-driven options (manure inhibitors 44%, low-emission spreading 81%): the
model's regional nitrogen price (median ~EUR 9/kg N) values each kg of manure N a cow does not excrete far
above CAPRI's, so the efficiency option (−5% manure N for ~EUR 2.4) spreads, and the yield option (+1.7%
manure N per cow) is held back. The milk-yield option also lacks the larger milk price rise it would see with
CAPRI's dairy block. At star 3.0's default (milk yield 0) the 20-indicator gap is the same, 4.36: the option
was adopted on 3% of cows and moved nothing visible.

### What the report's Table 18 says about priorities

CAPRI's technology contributions in Farm-to-Fork (kt CO₂-eq): winter cover crops −16,097, peatland
fallowing −4,138, mineral-fertiliser application −3,568, nitrification inhibitors −1,771, feed additives
−1,462, anaerobic digestion −495; ammonia measures +922 and +5,240 (more N₂O); **no genetics line**.
Technologies give 38% of total mitigation, production changes the rest. Our effect calculation agrees
(milk-yield genetics: −1.7% methane per kg of milk at full adoption). So the genetics calibration is
not pursued for now: the enteric-methane gap is a cattle-response gap (dairy −3.7% vs −10%, beef
animals −9.6% vs −18%).

## Low-nitrogen feeding (Sprint 9g, default on as star 3.0)

star 3.0's Green Deal technology file sets `ghgTechLowNFeed = 1` (as the JRC121368-era references), so CAPRI's
`envind/low_n_feed.gms` option exists in every scenario run. The project had left it out because JRC121368's Table
17 lists 0% adoption; under the rule that a star 3.0 default is on and judged against its own CAPRI data, it is now
built (`tools/build_lownfeed_effects.py`, `abatement/mitigation/lownfeed_effects.csv`) and is a column of the
regional models in the same framework as the breeding options:

- **Effect** (CAPRI's own formulas, per CAPRI activity, aggregated to the model's animals by CAPRI's 2017 levels):
  protein requirement x (1 − cut), cut = 0.15 x protein excess / (1 + 0.5 x energy excess), the excesses being
  CAPRI's requirement corrections p_animReqCorrFac (the rations' protein above the requirement function: French
  dairy cows +36%, pigs +44% nationally); manure N x (1 − cut (MANN + CRPR_EXPT) / MANN) (CAPRI 2017 data, res_17).
  Medians at full adoption: manure N −2.4 to −3.3% (cattle, pigs, poultry), up to −12% for fattening pigs in
  Brittany.
- **Eligible shares** = CAPRI's max calibration run (monogastrics 100%, dairy cows 72% = stable time, other cattle
  27%, sheep and goats 14%).
- **Cost** = feed cost per head x 0.06 x cut / (protein excretion factor − 1 − cut), calibrated as CAPRI does
  (relSubs0 0.2, relSubs1 0.8, curvature floor 0.05 per unit of the eligible share); not adopted at base.
- **Fix in the framework**: the curvature is per unit of the share of the *eligible* heads, as CAPRI's s; the
  breeding options divided by all heads, which mattered only where the eligible share is below 1 (fattening heifers,
  fattening sheep).

REGISTERED: the cost is CAPRI's at ghgTechLowNFeed = 1 (it is not linear in the parameter); the drop of the
option's marginal value between CAPRI's ini and max calibration runs is left to the model's own curvature (as for
the breeding options); the excesses are CAPRI's 2017 (base) corrections; lysine (LISI) is not a model requirement.

## Linseed and nitrate (Sprint 9g, default on as star 3.0)

star 3.0's Green Deal technology file switches the supplements on (`ghgTechLineNitr = 1`, which makes capmod.gms
include `envind/line_nitr.gms`; `ghgTechActiveFeed` = LINE, NITR, AComLN, 3NOP, LowNFeed), as did the JRC121368-era
references. They are now columns of the regional models with feeding inside, in the framework of the breeding
options and low-N feed (`tools/build_supplement_effects.py`, `abatement/mitigation/supplement_effects.csv`), one per
region, cattle animal and total (CAPRI's `LINE_Tot`, `Nitr_Tot`, which carry the costs and the feed effects):

- **Feed effects, as `supply_model.gms` REQSE_ / REQSN_.** Nitrate replaces crude protein: requirement − DRMA × 0.0154
  × dosage × 100 per head adopting (dosage 1.5% of DM, replacement heifers 1%). Linseed is fed: fresh matter = DRMA ×
  5% / (rapeseed fat × dry matter, 40.5% × 89.9%, fedcof.dat as line_nitr.gms names it), supplying the OOIL row of
  p_nutCont (energy 5.89, crude protein 0.22, dry matter 0.9 per kg), which lowers the energy and protein still to be
  fed and counts against the minimum and maximum dry-matter intake. CAPRI's MANN entry for nitrate (0.42) is defined
  but never used by the supply model or the emission accounts, so nitrate does not change manure N here either.
- **Enteric CH4** (emission accounts): −5% per point of fat (−25%) and −10% per point of nitrate (−15%, heifers
  −10%), p_mitiEffFac(2030) = 1; on the same animals (AComLN) the factors multiply, the overlap taken as large as the
  shares allow (CAPRI's maximum run puts all linseed on nitrate-fed cows).
- **Maximum shares** = the level of CAPRI's maximum calibration run + 2e-6 (line_nitr.gms caps MaxShare there). That
  run carries the definitions (dairy 100% / 10/12 of stable time, other cattle 50% of stable time, nitrate never for
  suckler cows or rearing calves) and the fat-balance correction of linseed. Median eligible share of dairy cows:
  linseed 29%, nitrate 66%.
- **Cost** = costParLin × DRMA / 1000 × dosage per head, costParLin €674 × 89.9 / 40.5 per t fat and €873 per t
  nitrate in 2017 money (CAPRI inflates them from the base year), halved for the cost savings (line_nitr.gms l. 357):
  about €250 (linseed) and €45 (nitrate) per dairy cow. Calibration as line_nitr.gms: zero at base, relSubs0 0.05,
  relSubs1 1.2, curvature floor 0.1 per unit of the eligible share.
- `ghgTechLineNitr` is a switch (0 = off, anything else on), not a scale (`param_switch` in the table). The ration
  model's early nitrate ingredient (`CAPRIModel.use_nitrate`) is ignored when these columns exist.

REGISTERED: DRMA (the requirement functions' dry-matter intake, not in CAPRI's results) is CAPRI's own estimate from
breeding.gms, DRMN + (|DRMX| − DRMN) / 4, from the rations' minimum and maximum dry matter; CAPRI's soft constraint on
total ration fat (SupplementPerc_, 5% of DM) needs every feed's fat (p_digestPar, not among the inputs) and is not
carried - its effect on the maximum shares is in the max-run caps; 3-NOP is left out: its only effect is enteric
CH4, it has no cost saving (Eps marginals in the calibration runs, 1e-6 in CAPRI's maximum run) and without an
emission price in the supply model its calibrated optimum is zero; the drop of the marginal value between CAPRI's
ini and max runs is left to the model's curvature, as for the other options.

## CAPRI's emission tax in the supply models (Sprint 9i)

CAPRI prices emissions inside the supply model when a scenario switches `ghgTax` on (pol_input/ecampa/
carbtax50_endotech_set12.gms: p_carbonTax(ru, "GGWP") = p_ghgEmisTax on the EU regions; supply_model.gms objective
− p_carbonTax x (v_CO2EquEmis(GGWP) − reference)). The model does the same with its own accounts
(`capri_mod/supply/ghg_tax.py`): each column of the regional problem carries tax x its emission per unit at the
baseline solution:

- activities, the grassland, dairy, bull and heifer splits, the breeding / low-N feed / supplement options and
  histosol fallowing: the change of the region's GHG total (EnvironmentalModule.compute_indicators) per unit of
  the column, by finite differences at the baseline (t CO2-eq per ha or head; e.g. Weser-Ems: a dairy cow 1.05 t
  without enteric CH4, wheat 1.4 t/ha, a hectare of histosol grassland fallowed −2.2 t, a cow fed nitrate −0.65 t);
- cattle feeding (CAPRI's feed-based CH4ENT): each flexible feed per t fed, dry matter x GE x 4.1868 x Ym / 55.65
  x GWP(CH4) (grass 0.11 t CO2-eq per t fresh, maize silage 0.15), fodder included; the fixed feeds' CH4 per head
  on the animal;
- Norway is not taxed (CAPRI: EU regions); the reference emissions (a constant) are left out.

`PolicyScenario.carbon_tax` (a policy shock of the scenario), `carbon_tax_scenario(price)` (CAPRI's file: the tax as
the only shock; the earlier proxy of agri-environment payments, nitrate limit and eco-scheme budget is gone),
`CAPRIModel.run(carbon_price=)`, `tools/run_f2f_2030.py --scenario carbontax --carbon-tax 50`.

Three regions at EUR 100/t, two outer iterations: emissions −11% (Weser-Ems), −9.5% (Brittany), −24% (Irish
Border-Midlands-West, mostly histosol grassland fallowed); suckler cows −13 to −17%, dairy cows −3 to −5%; nitrate
on 25-60% of dairy cows, linseed on 9-15%.

**Full EU, EUR 50/t, 2030, star 3.0 settings (s76, converged in 5 iterations):** agricultural GHG −6.8%: enteric
CH4 −10.0%, manure CH4 −1.6%, manure N2O −3.2%, fertiliser N2O −2.2%; beef animals −4.2%, dairy cows −1.1%, sheep
and goats −2.5%; beef price +2.8%, milk +4.8%. Adoption: histosol fallowing 36% of the histosol area, nitrate on
12% and linseed on 4% of cattle, ruminant feed efficiency on 23% of non-dairy ruminants, low-N feed 2.8% of
manure N.

**Sprint 9k: the ammonia options and manure trade under the tax.** CAPRI's v_CO2EquEmis follows its v_Miti, so the tax
prices the ammonia options' emissions. They are now in the regional conic model under the tax without a nitrogen row,
each with tax x its emission per unit of share (per unit of M, share x sub-activity units): the manure N2O change
through the accounts' loss cascade (finite difference over the animal's option share, `ghg_tax.ghg_coefficients`
"mtech", per head), less the indirect N2O of the NH3 kept (ret x EF4) and the soil N2O of the mineral N it displaces
(sub x ret x the accounts' mineral factor); the activity carries − that x s0 x w, so the base shares cost nothing.
Traded manure carries the soil N2O of the mineral N the exporter buys and the importer saves. Full EU, EUR 50/t (s82):
GHG −8.0% (s76 −6.8%), manure N2O −10.3% (−3.2%), ammonia −0.9% (−2.5%): low-emission spreading 40.8% → 32.5% (the NH3
it keeps raises application N2O, JRC121368 Table 18), covered storage 15% → 28%, air purification 0 → 6%,
acidification 0 → 1.4%, low-emission housing 16% → 13.5%. A tax on GHG alone trades ammonia for nitrous oxide, as
CAPRI's accounts imply.

**Sprint 9l: the fertiliser options under the tax.** Under the tax the crops' mineral N is a variable of the conic
model without a nitrogen row (CAPRI's mineral x (1 + E) = need), taxed at the accounts' soil N2O factor per t (the
crop column gives back the base part of its own coefficient); nitrification inhibitors carry CAPRI's literature side
effects (p_litRevFertTechs: − ef_dir x lit_N2O − ef_vol x lit_NH3 per t of N under them) instead of their N saving,
as the accounts count them. EUR 50/t (s83): GHG −9.5%, fertiliser N2O −13.3%, N surplus −10.8%, ammonia −2.5%;
inhibitors on 15% and precision farming on 20% of the area.

**Sprint 9m: inhibitors on manure under the tax.** Their value per t of manure N adds the tax on the mineral N they
displace, on application N2O x CAPRI's N2OAPP, less the indirect N2O of the extra application NH3 (NH3APP); the
animals' margins carry the tax saved at the adopted share. EUR 50/t (s84): 34% of manure N treated; GHG −10.5%,
manure N2O −15.9%, ammonia +1.9%.

REGISTERED: the coefficients are held at the baseline solution (the accounts are close to linear); the inhibitors'
side effects linearised at no adoption; the manure inhibitors' tax value weighted over animals by base manure N; the land-market
columns carry no coefficient of their own; no CAPRI tax run is in hand to compare with (EcAMPA 2's scenarios are emission targets
and subsidies, not taxes).
