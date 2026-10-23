# Coupling sprints — putting the puzzle together

*October 2026. Plan for closing the remaining gaps to CAPRI's 2030 Farm-to-Fork results (JRC121368)
by fixing module coupling, one CAPRI equation block at a time.*

## Why sprints, and what a sprint is

The largest remaining errors are all in livestock (beef production −7% vs CAPRI −14%, pigs −21% vs
−14.5%), and they share one pattern: herds respond to the regional nitrogen price in two extremes — they
grow where the price stays below €1/kg N and collapse (pigs −50%) where it exceeds €20/kg. Every recent
fix of a single parameter moved errors between indicators instead of shrinking them, because the
nitrogen target, the fertiliser balance, land, feed and markets are solved jointly in CAPRI and only partly
jointly here. So each sprint takes one CAPRI equation block and makes the model's version of it CAPRI's,
end to end (data, equations, coupling, reporting), before judging results.

Each sprint follows the same steps:

1. **Read CAPRI**: the GAMS equations and the data they use; write down every term.
2. **Compare item by item** with the model, using CAPRI's own regional results where they exist
   (`res_2_1730greendeal_ref`, `res_17*`, `elas_*`, `miti_data_jul15`).
3. **Replace** hard-coded or proxy terms with CAPRI's data; couple the block the way CAPRI does.
4. **Test**: base reproduced (anchors), unit tests, full-EU 2030 Farm-to-Fork.
5. **Judge** against JRC121368 *and* against the block's own CAPRI quantity (e.g. the regional balance
   items), then document (README, coupling review, changelog, registry).

A sprint is finished when the block matches CAPRI's structure; a result that moves away from CAPRI is
then a pointer to the next block, not a reason to undo a faithful change.

## Sprint plan (ordered by expected effect on the main failure)

| # | Block (CAPRI) | What differs today | CAPRI data in hand |
|---|---|---|---|
| 1 | **Gross N balance** (`e_SURTOTHa`, `e_EXPPRD`, `e_CRESID`, `e_BIOFIX`, `e_ATMOSD`; `SURTOT_REST_`) | crop removal from hard-coded N contents per tonne (wheat 20 kg/t, default 10); no crop-residue input; fixation from fixed rates; surplus per *base* hectare (CAPRI: current hectares). EU: removal 93 vs CAPRI 67 kg/ha net of residues, fixation 13 vs 10, mineral 65 vs 58; high-surplus Dutch regions 1.5–2.3× CAPRI's removal | CAPRI 2030 regional balance items and per-crop NITF, NCRD, biofix, levels (`res_2_1730greendeal_ref`) |
| 2 | **Fertiliser distribution** (`NUTNED_`, `fertDistExcr_`, availability `v_nutAvailFactExcr`, over-fertilisation `v_cropNutNeedMultFact`) | mineral N follows need through a linearised substitution factor; crop-need floor; CAPRI allocates manure and mineral N per crop with losses and availability | `res_2_1730…` nutNed_* and fertDist_* per crop |
| 3 | **Land** (`LandBalNoSlak_`, set-aside, grassland, winter cover crops `WinterCov` with N and biofix effects) | land slack allowed; cover crops (Table 18's largest item) not modelled | land-market data, `wintercovershare.gms`, `tillageCover`, `ccEfa` |
| 4 | **Feeding inside supply** (`REQSN_`, `FEDUSE_`, fodder at shadow value) | feed rations solved apart (inside version built, gap 4.7 vs 4.5); fodder priced at base value | rations, CAPRI feed PMP |
| 5 | **Livestock activities** (SOWS/PIGF done with the piglet market; DCOL/DCOH, BULL/BULH, HEIL/HEIH/HEIR, four calf activities open) | 10 animal activities; census heads, not CAPRI activity levels | `res_17*` levels and coefficients |
| 6a | **2030 prices** (CAPRI's 2030 reference unit values and premiums) | done: baseline at CAPRI's 2030 prices in 2017 money | `res_2_1730greendeal_refpol_endotech_all_ini` |
| 6 | **Markets** (beef TRQs, pork Armington, dairy processing, young-animal markets per member state) | biofuels in the market (done); dairy block built, opt-in (Stage 3 open); EU prices now reported with one premium: pork +20% vs +43%, beef +14% vs +24% | `elas_*`, market base data |
| 7a | **Grassland intensity** (`GRAE`/`GRAI`) | done: CAPRI's split as an extensification column (Sprint 7a) | res_17 GRAE/GRAI, p_pmpQuadTechn |
| 7 | **Remaining mitigation** (fertiliser side effects `LitRevFertTech`, fallowing, tillage, genetics) | side effects not passed to emissions | `LitRevFertTech`, `miti_data_jul15` |

Already done and kept: rye and oats priced through the other-cereals market; feed demand from herds;
oilseed crushing; land market; fodder balance; CAPRI's ammonia and fertiliser options (active set, groups,
calibration, cascade, over-fertilisation limit, jul15 data); livestock elasticities; young-animal markets.

## Sprint 1 — gross nitrogen balance (done)

**CAPRI's block.** `e_EXPPRD`, `e_CRESID`, `e_BIOFIX`, `e_ATMOSD`, `e_SURTOTHa` (`supply/supply_model.gms`):
removal = Σ level × NITF export coefficient × yield factor; residues + deposition = Σ level × NCRD; fixation =
NITF × biofix factor (pulses and soya fix 2.4–2.9× what they export); fertiliser distribution (doc. eq. 5.10):
crop need (net of fixation) is met by mineral N, manure and crop residues, each at its availability; "crop
residues can be re-distributed among crop groups for annual arable crops but not for grassland and permanent
crops"; organic farming caps *mineral* N per ha (`organic_minfert_redu.gms`).

**Before.** Removal from hard-coded N contents per tonne; no residues; fixed fixation rates; mineral N, manure
cover and the fertiliser-technology and organic factors all scaled the crop's *whole* need; the N row's
yield terms covered removal and mineral need only.

**Now** (`environmental_module.compute_nitrogen_balance`, `supply_module` N row):

| Item | Model, base data (EU, kg N/ha) | CAPRI 2030 |
|---|---|---|
| Removal (EXPPRD) | 125.4 | 118.5 |
| Crop residues (CRESID) | 57.1 | 54.8 |
| Fixation (BIOFIX) | 10.4 | 8.2 |
| Deposition (ATMOSD) | 11.2 | 11.3 |
| Mineral (MINFER) | 63.0 | 56.9 |
| Manure (EXCRET) | 54.1 | 53.2 |
| Surplus (SURTOT) | 74.6 | 66.0 |

Regional surplus per ha, 235 regions: correlation with CAPRI 0.92 (was 0.89), median 75.1 vs 65.3; the gap is
on the input side (2017 mineral rates and herds against CAPRI's 2030 projection — Germany: removal, residues,
fixation and deposition within 2–7% of CAPRI, mineral +15 and manure +13 kg/ha).

1. Per-crop removal, residues (NCRD net of deposition) and fixation from CAPRI's 2030 coefficients, scaled to
   each region's EXPPRD and CRESID, moving with yield.
2. Residue N displaces mineral N at CAPRI's availability (1 − unavailable/(CRESID + ATMOSD), 0.75–0.92).
   Arable residues are pooled and credited to arable crops **by need**; grassland and permanent crops keep
   their own.
3. Manure-covered need is also spread **by need** (removal net of fixation), not per hectare — a hectare of
   fallow had been credited with average manure and residue cover, so set-aside raised the reported surplus
   behind the constraint's back.
4. Fertiliser technologies scale mineral N *net* of the manure and residue credits (`__credit__` factor);
   organic land loses its *mineral* rate only. Scaling the whole need had cut mineral N by up to twice what
   was applied where manure covers most need.
5. The N row uses each crop's own balance at the solve's yields and fertiliser factors — the same function
   as the accounts — so constraint and report agree (target −35.8%, achieved −36.5%; before: −27.6%).
6. Outer loop: per-commodity adaptive price damping (step halved when the gap changes sign); eggs had
   cycled between four premium values and blocked convergence.

**Results (full EU, 2030 Farm-to-Fork, converged; CAPRI in brackets).** N surplus −36.5 (−33.5); fertiliser
N2O −39.4 (−40.4, was −37.8); beef animals −16.4 (−18, was −8.0); beef production −14.1 (−14, was −7.1);
beef price +29 (+24). But herds now fall too far elsewhere: dairy −14.8 (−10), sheep −20 (−9.5), pigs
−28.7 (−14.5), pork price +63.5 (+43), poultry price +43.5 (+18); oilseed price +32 (+11), soya −50%.
Mean absolute deviation 4.60 → 7.66 (price indices now value-weighted; the unweighted mean let soya, 9% of
EU oilseed output, carry a third of the oilseed index).

**Reading.** The old fit rested on two errors that pointed the same way: organic land and fertiliser
technologies cut mineral N far below what farmers applied, and the constraint saw a looser balance than the
accounts. Both made crop-side abatement too cheap and spared herds. With them gone the nitrogen price
falls on livestock as CAPRI's balance says it should, but CAPRI has channels that spare herds which the
model still lacks — the pointer to Sprint 2:

- **manure's value under a mineral cap**: CAPRI meets need on organic land (mineral capped) with manure, so
  manure gains value; here manure displaces mineral N at a fixed linear factor;
- **over-fertilisation** (`v_cropNutNeedMultFact`): crops can trim need, cheaply, before herds move;
- **grassland and fodder** valued at shadow prices in the feed block (Sprint 4);
- the N target alone (no organic, landscape or pesticide targets) already gives dairy −15.5, beef animals
  −19.4, pigs −28.4, sheep −23.9 and mineral N −29%: the herd overshoot lies inside the nitrogen mechanism,
  where crops have too few cheap ways to cut the balance;
- soya: CAPRI's biofix makes soya a high-surplus crop (≈160 kg N/ha fixed, 37 exported); its 50% fall is
  the balance's arithmetic, and the EU soya price follows through the Armington premium (+47%).

## Sprint 2 — fertiliser distribution and manure value (in progress)

**CAPRI's block.** `NUTNED_` is an *equality* per crop group: need = mineral × (1 − losses) × (1 + E) +
manure × availability + residues; `fertDistExcr_` makes all manure applied, its split across groups free;
`NUTMIN_`/`NUTMAX_` bound each group's mineral share. In simulation the over-fertilisation factors, minimum-share
corrections and availabilities are fixed at their calibrated values (`set_miti_bounds.gms`, `aggreg.gms`) —
crops cannot trim over-fertilisation by choice; the endogenous-yield step responds to output prices only
(`endog_yields.gms`, the fertiliser-price channel is commented out). The Green Deal runs switch on
`endoManAvFact` (`fert/endoManAvail.gms`): manure availability falls with manure per ha, g = g0 + b (m − m0),
b = −0.0015 per kg N/ha, flattened so g stays within [min(0.2, g0), max(0.999, g0)] between 0 and 300 kg/ha.

**Done.** Manure now replaces mineral N at CAPRI's *marginal* rate, (g0 + b m0) / mineral efficiency, from the
reference run's own per-region deliveries (`fertDist_excr`, `nutNed_excr_unavailable`, `fertDist_mine`,
`nutNed_mine_loss`, added to `capri_gnb_components_2030.csv`; national values where CAPRI has no NUTS-2 region,
replacing the EU-median proxy used for Belgium, Denmark and others). The earlier factor also multiplied by
(1 − share of need at the minimum-mineral floor), on the reasoning that manure at the floor is unused; under
`NUTNED_` as an equality with a free split across groups the floors bind only when manure *grows*, so when herds
shrink mineral N rises at the full availability. Weser-Ems: 0.26 → 0.61; Brittany 0.07 → 0.37; North Brabant
0.03 → 0 (CAPRI's slope makes its marginal negative at 400 kg/ha; clamped at zero). Farm-to-Fork: average gap
7.66 → 6.77 (pork price +63.5 → +54.6, poultry price +43.5 → +38.0, dairy −14.8 → −13.5); herds still fall too
far (pigs −27.8 vs −14.5).

**Found: farmland in use.** The area farmed falls 14% in the scenario (CAPRI's farmland +3%; Brittany −52%, Lombardy
−42%), mostly as idle land the default allows: idling or releasing a hectare removes its mineral N, residues and deposition from a balance capped per *base* hectare,
worth €1,000–2,000/ha at the regional nitrogen prices (median €9/kg N, a quarter above €21). CAPRI's two land
rules were tested together and apart:

| Run | Area farmed | Pigs | Sheep | Pork price | Converged | Gap |
|---|---|---|---|---|---|---|
| default (slack, base ha) | −14.1% | −27.8 | −19.5 | +54.6 | yes | 6.77 |
| per current ha | −17.3% | −28.2 | −21.2 | +58.5 | no (land) | — |
| no idle land (`LandBalNoSlak_`) | −15.5% | −48.0 | −8.4 | +140 | no | — |
| both, as CAPRI | +12.9% | −80.9 | +52.1 | +151 | no (young animals) | — |

With both rules, as CAPRI has them, every hectare brings its share of the allowance (target × €/kg N) and land
supply and grazing animals jump while pigs and poultry collapse. CAPRI gets +3% farmland under the same rules,
so its nitrogen shadow prices must be far lower than the model's. That is the real failure: **the regional
targets cost the model several times what they cost CAPRI.** Next steps, in order: (1) the regional cut is
CAPRI's tiered rule on the *2023 CAPRI* 2030 reference surplus, while JRC121368 used its own (older) baseline —
Brittany faces a 57% cut, Lombardy 65%, Denmark 53%; check the per-region cuts against the report's EU figure
and, where available, its baseline; (2) decompose a high-price region's marginal abatement cost by channel
(herds, crop mix, technologies, land) against CAPRI's options; (3) then CAPRI's land rules (Sprint 3).

### Sprint 2 — diagnosis of the nitrogen price (step 2 of the plan)

`tools/diag_n_abatement.py` solves one region at base prices with only the nitrogen target, at rising cuts, and
splits the reduction by channel. Brittany (base surplus 334 kt N):

| Cut | N price €/kg | Herds | Crop area | Technologies | Pigs | Dairy | Area farmed |
|---|---|---|---|---|---|---|---|
| 10% | 1.4 | 17% | 13% | 70% | −5.6% | −1.7% | −2.8% |
| 30% | 8.9 | 43% | 31% | 26% | −31% | −11% | −20% |
| 57% (target) | 22.5 | 54% | 39% | 7% | −72% | −28% | −49% |

The technologies (ammonia options, inhibitors on manure, precision farming) cover the first tenth of the cut and
then saturate; beyond, the surplus can only fall by removing animals or farmed land.

Checks that rule out other explanations:

- **Supply response**: a 5% producer-price rise gives pig elasticities of 0.42–0.67 in Brittany, Denmark,
  Weser-Ems and Catalonia (CAPRI's calibrated 0.57–0.72), milk 0.27–0.46, beef 0.39–0.52, poultry 0.69. Herds
  respond to a given cost as CAPRI's do.
- **Size of the targets**: JRC121368 states the EU-average reduction target was 36%; the model's regional
  targets add up to 35.8%.
- **CAPRI's technical potential**: in CAPRI's own maximum-mitigation run (`…endotech_all_max`, every option at
  its maximum share at near-zero cost) EU mineral N falls 15% (Brittany 33%, Weser-Ems 57%), manure delivered
  to crops rises 12% and crop-residue N 17% (winter cover). Mineral N is about a third of the inputs, so even
  at maximum the options remove roughly a tenth of a livestock region's surplus.

So, with the same targets, elasticities and options, the model needs nitrogen prices of €20+/kg in Brittany and
Denmark, and pigs there fall by half or more. CAPRI's −14.5% for EU pigs implies either much lower prices or
smaller cuts in the main pig regions. The model cannot tell which without CAPRI's own Farm-to-Fork run: its
regional surplus, herd levels and the dual of the surplus constraint (`SURTOT_REST_`; dataOut carries duals,
e.g. `D_NUTNED`). The uploads hold the 2030 reference and the minimum/maximum-mitigation runs only
(`scen_greendeal_2030.txt` is the maximum run). **Data needed:** a CAPRI Green Deal scenario result with the
surplus target active (e.g. `res_2_1730greendeal_<scenario>.gdx`/csv dump), ideally the JRC121368 run.

### Sprint 2 — legumes' removal, and convergence (JRC96482)

The project lead supplied JRC96482 (*Regional nitrogen balances*, CAPRI vs national methods) and Leip's 2012
slides on the CAPRI balance. Neither contains scenario results, but JRC96482 defines CAPRI's terms: NITF is the
N need of above-ground biomass (harvest and residues) and biological fixation is a fixed share of it,
Nbiofix = NITF × LEVL × fBNF, fBNF 75% for soya and pulses, 5–17% for grass (eq. 1). The NITF in CAPRI's results
is the need *net* of that share (NUTNED_), which is why fixation came out at 2.4–2.9 times NITF for legumes
(0.75 / 0.25 = 3). Removal per crop was keyed on the net figure, so pulses and soya removed a quarter of their N
and showed surpluses of ~140 kg/ha. The key is now the gross need, NITF + fixation (still scaled to each
region's EXPPRD): pulses in Saxony-Anhalt 141 → 2 kg N/ha surplus; EU totals unchanged. Farm-to-Fork: soya
output −66 → −33%, EU soya price +96 → +29%, rapeseed price +33%.

Two path-only fixes to the outer loop, needed once the legumes moved: the EU egg premium is steep (the EU
imports 0.07% of its egg use and exports a tenth of output; a 10% fall in output takes the premium to its
bound) and solver noise of 0.2% in egg output made it cycle for 25 iterations; it now takes an adaptive step
toward each newly cleared premium (halved when the direction flips). Converged in 23 iterations.

Average gap 6.77 → 7.69: the oilseed index improves, but cereal (+25%), pork (+60%) and poultry (+43%) prices
rise — the herd and land response to the high nitrogen prices is unchanged and remains the open problem.

## Sprint 9e — CAPRI's inner fertiliser model and `mineRedu` (October 2026: done, default)

The last star 3.0 default of the scenario run: **the inner fertiliser distribution model** (CAPRI's statistical
allocation of mineral, manure and residue N over 17 crop groups, `supply/set_fert_priors.gms`, `e_focFertDist`),
on CAPRI's 2030 priors, solved per region (`capri_mod/fert/inner_fert_dist.py`). Its sum over groups is the
regional identity the balance already used, so it reports the allocation (`results["fert_dist"]`) and carries the
crop-specific caps; it does not move regional totals. **`mineRedu`** as CAPRI's two files (UAA-wide `e_synNMax`;
by crop group with CAPRI's exemptions and regulations), a mineral-N row in the regional models.

Checks: priors = CAPRI's priFertDist posterior modes (4e-5); the model returns them at the baseline's totals in
all 250 CAPRI regions; Farm-to-Fork with the inner model alone unchanged (gap 3.31).

Found on the way: the fertiliser technologies inside the conic model acted on each crop's whole unit coefficient
(mineral rate + its share of the manure-covered need) while the accounts scaled the rate; the N row counted ~40%
more mineral N saved than the balance reported. Fixed (technologies on the mineral rate, as CAPRI's mineral x
(1 + E)). Farm-to-Fork: N surplus −34.3% (CAPRI −33.5), herds 1–3 points further down; **gap 3.31 → 3.77**. The
previous gap rested partly on that overcount: the herd overshoot (pigs −23%, sheep −15.5%, dairy −13.7%) is now
the clearest open item.

Green Deal 2030 (star 3.0 rule) with `mineRedu=20crp`: binding in 49 regions where the surplus target had not
already cut a group's mineral N by a fifth; cereal price +1.7 points, cereal output −1.1, fertiliser N2O −0.8.
REGISTERED: per-group caps through their sum; manure-saturated regions (mineral N near zero; 8 in Farm-to-Fork,
~60 in the Green Deal) have group needs the allowed sources cannot meet - CAPRI's over-fertilisation factor
(`v_cropNutNeedMultFact`) would absorb it; they are reported unconverged.

## capri-mod-proto — the nitrogen target as a plain constraint (October 2026: prototype branch)

Question asked: would CAPRI's non-convex supply model gain from IPOPT? With feeding and technologies already exact
inside Clarabel, the only part set outside the solver was CAPRI's nitrification inhibitor on manure (at the N price
of a per-region fixed-point search). It is now inside the conic model - one regional share, CAPRI's cost curve, its
maximum share and tax value, convex through the perspective T^2 / W - so N-target regions need one solve, with the
surplus target as a plain constraint and its dual as N price. A stalled Clarabel solve in IE05 (the inhibitor at its
maximum) is re-solved with more regularisation instead of falling back to the problem without technologies.
Farm-to-Fork: 13 iterations, 353 s (9t 23, 756 s), gap 4.29 (4.26); Green Deal: 20 iterations, 584 s (18, 799 s);
indicators within 0.4 / 0.8 points. IPOPT not needed (docs/archive/PROTOTYPE_NI_INSIDE.md).

## Sprint 9t — one parameter file; land supply of combined CAPRI regions (October 2026: done, default)

All constants of the economics and accounts in `capri_data/shared/model_parameters.csv` (55 rows with unit, kind,
source; results identical). Combined CAPRI regions' land supply as the sum of their land owners' responses
((sum Q^-1)^-1) instead of an area-weighted matrix; Ireland's regions from their own shares of the NUTS-2013
regions. IE05's nitrogen price then showed two branches and the run did not settle in 8 inner solves; 16 close it.
Farm-to-Fork gap 4.26, converged in 23 iterations.

## Sprint 9s — synthetic data removed (October 2026: done, default)

Audit (docs/SYNTHETIC_DATA_AUDIT.md), then every finding that reached the results fixed with CAPRI's data: crop
premiums, costs, prices and yields for all 248 regions from the 27 dumps (1,957 premium cells had come from a random
file; wine and fibre costs, fibre yields and 36 wine prices were fills; a cap on horticultural costs inflated their
margins); manure and enteric CH4 per head, liming and urea CO2 as CAPRI accounts them (manure CH4 EU 2017 1,072 kt
flat against CAPRI's 1,396), GHG split into non-CO2 (the JRC comparison) and CAPRI's GGWP (the tax base); CAPRI's
yield elasticities (cereals 0.3, oilseeds and potatoes 0.2, others 0; was 0.15 everywhere). Generators and generic
fallbacks removed: a gap now raises. Baseline against CAPRI's reference unchanged; Farm-to-Fork gap 4.31 → 4.06
(cereal production -15.0 = CAPRI, veg+perm price +13.5 against +15); Green Deal prices 1-3 points lower. Open: land
supply elasticity, the other-oilseed world market, the grass dry-matter share - then done too: CAPRI's fixed
activities (OOIL, OIND, OANI) and no other-oilseed market, CAPRI's grass dry matter and fresh yields everywhere,
CAPRI's land market for Ireland. Gap 4.06 → 4.27: Ireland's grassland now expands as CAPRI's land owner allows
(+750 kha under the per-hectare surplus target), lifting suckler cows, sheep and the milk price.

## Sprint 9r — regional solves in parallel; CAPRI's tariffs for every trade region (October 2026: done, default)

Speed without changing results. The regional supply models are independent at given market prices (CAPRI solves
them in sequence, or as parallel grid jobs), so `SupplyModule.run` forks one worker per core for each supply call
(`CAPRI_WORKERS` / `SupplyModule.n_workers`; 1 = one process). Workers start from the module's current state and
return each region's result, model, land and N-price state and cache entries, merged in the regions' order. Full
Farm-to-Fork and Green Deal runs reproduce the one-process runs exactly (every saved figure equal). On 2 cores:
Farm-to-Fork 799 → 463 s, Green Deal 1537 → 881 s; supply is ~60% of a run, the market and the tax coefficients stay
one process (the next lever if more speed is needed; more cores cut the supply share further).

Found on the way: the non-EU tariffs (domestic price levels; the oilseed crushing parameters use them) had no data
file and were drawn at random by the loader, differently for each model built in a process. Now CAPRI's total
protection, ImportP / (Fob + TCost) − 1 over its 2017 bilateral flows, for every trade region
(`tools/build/build_tariffs_2017.py`; the EU row recomputed this way agrees with its documented values to 0.1 point).
Farm-to-Fork: indicators within 0.1 point, gap 4.31; Green Deal unchanged. It also explains why two runs of one
scenario in one process could differ slightly (the 1e-5 tolerance of the organic no-op test).

## Sprint 9q — CAPRI's 2030 rations and fodder (October 2026: done, default)

What 9p left: the fodder crops, held by the fodder balances, drifted up to 28% from their projected areas because the
2030 rations were the 2017 mix scaled by one factor and usable fodder per ha stayed at 2017. Now both come from CAPRI's
2030 reference (per-head feeds and requirements; FEDM / LEVL of the fodder crops, which carries silage maize going to
biogas in Germany). A 4-region check: largest drift 0.3% after calibration (was 28%). Full EU (s94): regional drift
median 0.01%, 90th percentile 0.36%; against CAPRI's reference activities 1.3%, production 1.1%, use 1.6%. Farm-to-Fork
gap 4.30 (4.23 in 9p: milk +29.5%, sheep −6.9%); 799 s. The 2030 baseline now reproduces CAPRI's 2030 reference
region by region; the remaining EU differences are 2017 base-data differences (sheep and goats, calves, olives) and
unit definitions (laying hens, fattening cattle).

## Sprint 9p — projection layer: CAPRI's reference as the baseline, calibrated (October 2026: done, default)

The 2030 baseline against CAPRI star 3.0's own 2030 reference: activities median 3.8%, production 3.4%. Most of the
gap was in the projected DATA, before any solve: (1) the trajectory was CAPTRD's trend projection, the input of
CAPRI's baseline calibration, not its result; (2) the projection read no land block, so 2017 land was kept and the
reconciliation lifted every crop by CAPRI's 2.1% UAA decline. The rest was regional drift in the solve (broilers +7%,
layers +2-4%, cattle in some regions +3-10%), which CAPRI removes by calibrating its supply models to the baseline.

Done: the reference as trajectory (levels, yields, land types per region; `capri_ref_2030.json`), CAPRI's baseline
calibration (`calibrate_to_base`: linear terms shifted by Q (x − target), rounds until the largest drift stops
falling, fodder crops excepted), CAPRI's 2030 feed bulk prices in the rations. Result (s91): activities 2.6%,
production 1.4%, domestic use 1.7% against the reference; regional drift median 0.13% (90th percentile 3.9%).
Farm-to-Fork gap 4.37 → 4.23. Cost: two more baseline iterations (785 → 984 s). Open: fodder crops (2017 rations
scaled to 2030 requirements do not match CAPRI's 2030 fodder output; CAPRI's reference rations would close it);
base-data differences (sheep and goats −18%, calves) are the 2017 data, not the projection. The 25% relative price
gap is a reporting comparison (market prices against producer unit values; only ratios enter the model).

## Sprint 9o — pigs, manure N2O, ammonia; market speed (October 2026: done)

**Pigs.** Farm-to-Fork s86: EU pigs −21.9% (CAPRI −14.5%). Brittany (FRH0) and Lombardy (ITC4) go to zero (11.2 of the
28.0 M places lost); without them the EU loses 14.4%. Both carry the tiered rule's steepest cuts outside the relaxed
nine: CAPRI's baseline surplus 176 and 217 kg N/ha → targets 75 kg/ha, cuts of 57% and 65% (applied to the model's own
no-trade baseline, 247 → 114 and 228 → 82 kg/ha). With the cheap options used, the N price rises to EUR 63-71/kg N, and
pigs (23-29 kg N excreted per place, CAPRI's MANN), broilers and most laying hens leave. The JRC121368 relaxation (36%
for "nine regions with high GNB values in the baseline associated with high animal numbers [that] generated
infeasibilities") is applied to the nine highest surpluses per ha - NL41, BE25, NL21, BE21, NL22, NL31, BE23, NL42,
MT00. Another reading - surplus above 150 kg/ha and the most manure N - gives FRH0, IE05, ITC4, NL41, DK03, BE25, DK04,
ITH3, DK05. Sensitivity s87 (that set): pigs −18.8%, poultry −17.2%, gap 4.36 → 4.15; Brittany −37% at EUR 24/kg N,
Lombardy −24%; but the pork price +27% (CAPRI +43) and beef +15% (+24). The report does not name its nine regions, so
the default stays; the choice is the main lever on the herd results and is recorded as such.

**Manure N2O and ammonia.** Manure N falls 21% (herds; Brittany and Lombardy a quarter of it), CAPRI's herds imply
about 12%. Technologies: −2.2 Mt CO2-eq net in the model; CAPRI's Table 18 has the ammonia options +6.2 Mt and all
inhibitors −1.8 Mt. Inhibitors on manure reach 49% of manure N: with CAPRI's own calibration (ghgMiti.gms, N2OMAN:
relSubs0 0.2, p_manureShadVal in the linear term) a region adopts once its N price exceeds ~EUR 0.4/kg N, and the
binding regions here are at EUR 5-70. Both gaps follow the regional N price level, the same lever as the pigs; the
accounts were re-checked against CAPRI's equations and are unchanged.

**Market speed.** Profile: every market solve ran to its 60-step limit, the error falling ~13% per step on whey and
the other dairy products after the damping was halved once (it never recovered). Now the damping lengthens again after
progress (×1.5 when the error falls 5%): ~40 steps. Also: the trade system's prices computed once per evaluation (the
flows recomputed them), supply and demand arithmetic in arrays. Exactly equal on a 6-region check; full Farm-to-Fork
within 0.1 point, 865 → 747 s.

## Sprint 9n — milk price re-checked; speed and reproducibility (October 2026: done)

**Milk price.** Farm-to-Fork (s80): EU milk delivered −6.5%, raw milk +28.9% (CAPRI +1.5%). Decomposition: dairy
product prices +5 to +21% (butter +21, cream +10, cheese +8.5, SMP +5%), fat +30%, protein +16%. That is star 3.0's
block at work - a product's price is its fat and protein value plus a processing margin that falls with throughput,
and raw milk is almost all fat and protein value - so product price changes reach milk about two-fold, and each
member state's milk price follows its own milk (NL −17% milk, +44%; IT −15%, +47%; DE +1%, +16%). Nothing in the
implementation departs from CAPRI's equations or coefficients (checked in Sprints 9f and the Figure 7 read).
JRC121368's +1.2% with milk −10% is not reachable with star 3.0's coefficients; the gap stays recorded as a version
difference. What would settle it: a star 3.0 scenario result with a dairy shock (any Green Deal or tax run in CAPRI's
results folder: raw milk, fat, protein and product prices with production per member state).

**Speed.** Profile of a full Farm-to-Fork run (cProfile): conic solves (Clarabel) ~25%, market evaluation ~25%,
regional problem building ~30%, of which most was pandas scalar access (`.at` / Series.get: ~5 M calls in the organic
and pesticide cost terms, the breeding columns, the biofuel state), the unit N balances of `_build_constraints`
(~240 k calls), and cell-by-cell sparse assembly of the conic problems. Fixed without changing behaviour: dict and
array lookups, a memo of the unit N balance (it reads only the activity's own yield and factors and the trade
setting), sparse block assembly, the biofuel feedstock loop skipped for biofuel use, static demand frames built once.
84 → 67 s per outer iteration (−21%), 1006 → 865 s per Farm-to-Fork run. Left: Clarabel itself and the market's
DataFrame arithmetic (would need a NumPy rewrite of supply_response/demand_response: not "effortless").

**Reproducibility.** Before vs after the speed changes differed by up to 20% for laying hens in one Dutch region -
the same as two runs of unchanged code (s80 vs s85old: 10%). Cause: Python's per-process string hash seed (tested:
same seed 0.0 difference, different seeds 0.25%). The runners now fix PYTHONHASHSEED=0; runs repeat exactly.

## Sprint 9m — inhibitors on manure under the emission tax (October 2026: done, default)

The last option outside the tax. Inhibitors on manure (NITR_INH_MAN, CAPRI target N2OMAN) keep their closed-form share
(cost S0 + slope x share per t of manure N, CAPRI's calibration); their value per t now adds the tax on the emissions
they save as the accounts count them: mineral N displaced (sub x NMAN) at the soil N2O factor, application N2O x
N2OAPP, less the indirect N2O of the extra application NH3 (NH3APP); weighted over the region's animals by base
manure N (registered). The animals' margins carry the tax saved at the adopted share (their own coefficients are at
no adoption). EUR 50/t (s84): 34% of manure N treated; GHG −10.5%, manure N2O −15.9%, ammonia +1.9% (s83 −2.5%).
At EUR 100/t the share reaches its maximum in livestock regions: the N2O value (~EUR 150 per t N) is well above
CAPRI's cost (EUR 86 per t N). Every CAPRI option is now priced by the tax.

## Sprint 9l — fertiliser options under the emission tax (October 2026: done, default)

The last open item of 9k. Without a nitrogen row the crops' mineral N was not a variable of the regional model, so the
fertiliser options had nothing to act on under a tax alone. Now, under the tax, the conic model carries each crop's
mineral N m_c (CAPRI's mineral x (1 + E) = need, the same cone as with a nitrogen row), taxed at the accounts' soil N2O
factor; the crop column gives back the base part its own emission coefficient carries. Nitrification inhibitors carry
their literature side effects (lit_N2O 0.19, lit_NH3 −0.12 in Upper Bavaria) instead of their N saving, because the
accounts count N under them at (1 − lit) x (1 + NMIN) of the plain factor (linearised at no adoption: registered).
EUR 50/t (s83): GHG −9.5% (s82 −8.0%), fertiliser N2O −13.3% (−2.3%), N surplus −10.8%, ammonia −2.5%; inhibitors
15%, precision farming 20%. Open: inhibitors on manure respond to the nitrogen price only (closed in 9m).

## Sprint 9k — manure and ammonia in every EU solve (October 2026: done, default)

Three items left open by 9i and 9j, all from the same cause: the crop-need row, the manure trade columns and the
ammonia options were built only when the region had a nitrogen row (a surplus target or the mineral fertiliser cap).
CAPRI has NUTNED_ and its manure market in every run, and prices the options' emissions under ghgTax.

- Crop-need row in every EU solve (`SupplyModule._manure_context`, `RegionalSupplyModel._mctx`; switch
  `use_nutned_always`).
- Manure trade columns in every EU solve with trade on; cost = pool price only. CAPRI's trade-cost constants are
  calibrated from the base duals (FINALIZE), which with a fixed fertiliser price absorbs the fertiliser bought or
  saved per t traded; the earlier `sub x p_f` terms were also read back as part of the pool price in the clearing
  (`_update_manure_pools` now takes the price the region was solved at). The baseline reproduces the base trade
  (deviation 0.1 kt N).
- Under the emission tax: the ammonia options are in the regional conic model without a nitrogen row, priced by
  their emissions per unit of share (manure N2O through the cascade, `ghg_tax.ghg_coefficients` "mtech"; indirect
  N2O of the NH3 kept; soil N2O of the mineral N displaced); manure trade by the soil N2O of the mineral N bought or
  saved.

Results, full EU 2030 (s80-s82): Farm-to-Fork unchanged (no trade in it; it had the N row already): gap 4.37.
Green Deal: within 0.8 points of s79 on every indicator; 1.1 Mt N moved; pool prices EUR 25-28/kg N in the livestock
pools. EUR 50/t tax: GHG −8.0% (s76 −6.8%), manure N2O −10.3% (−3.2%), ammonia −0.9% (−2.5%). The tax moves the
options by their N2O: low-emission spreading 40.8% → 32.5% (the NH3 it keeps raises application N2O in the cascade,
JRC121368 Table 18), covered storage 15% → 28%, air purification 6%, acidification 1.4%; NH3 rises against s76
(pollution swapping, as CAPRI's accounts imply). Open: the fertiliser options under a tax alone (they need a mineral
N variable outside the N row; closed in 9l); no CAPRI tax or Green Deal scenario run to compare with. Test noise: two
runs of the same scenario can differ by ~1e-6 relative where the CAPRI columns calibrated from base duals enter after
another test's first solve (the crop-need row is often tight at base); the organic no-op test now uses 1e-5.

## Sprint 9j — manure trade against CAPRI's reference (October 2026: done)

CAPRI's 2030 Green Deal reference (endogenous technologies, trade on) carries each region's net manure N trade
(MTRADE) and excretion. Against it the model's base trade data was incomplete: written without a builder and matched
by CAPRI code, it had no trade for Belgium, Italy, Poland, Sweden, Romania (125 kt), Ireland (30 kt) and others. Now
built per group of CAPRI and model regions (`tools/build/build_manure_trade_base.py`): 113 exporting and 111 importing
regions, 1.2 Mt N. The base trade also counted in runs without trade; CAPRI's no-trade configuration (JRC121368)
keeps all manure in its region in scenario and baseline alike, so now does the model: F2F gap 4.53 → 4.36. Green Deal
(s79, star 3.0 settings): the market moves 1.1 Mt N against the base pattern (Brittany and Pays de la Loire export
more, base importers with binding targets take less, base exporters with low nitrogen prices keep more); the
importing regions' crops fall less than elsewhere (−4.2% vs −5.4%), so the old "importers give up crops" finding is
gone. Open: no CAPRI Green Deal scenario to compare with; trade columns only where a nitrogen target applies
(closed in 9k).

## Sprint 9i — no post-solve modules; CAPRI's emission tax in the supply models (October 2026: done)

The project rule is no post-solve modules unless CAPRI has them. The feed module (post-solve, off, superseded by
feeding inside the supply models) and the abatement layers applied after the solve (a net-revenue MACC, EcAMPA
measures at full uptake, CAPRI's p_ghgMiti portfolio) are retired with their data. CAPRI's own route to abatement
under a carbon price is its emission tax inside the supply model (ghgTax, `carbtax50_endotech_*.gms`); the model now
has it: each column of the regional problem carries tax x its emission per unit at the baseline solution (the
accounts' finite differences; cattle enteric CH4 on the feed fed). EUR 50/t, full EU 2030: GHG −6.8%, enteric CH4
−10%, histosol fallowing 36%, nitrate on 12% of cattle. Open: the ammonia and fertiliser options enter the regional
problem only with a nitrogen row, so under a tax alone they are not adopted (ammonia options: closed in 9k); no CAPRI
tax run to compare with.
docs/MITIGATION_IN_SUPPLY.md.

## Sprint 9h — CAPRI's feed bulks complete; residual feed markets (October 2026: done, default)

Audit of the open items (project lead's list): the feed-cereal price mix and EU feed demand for cereals and protein
feed were already CAPRI's (bulks FCER/FPRO, Sprint 9d); energy-rich, other and milk feeds were neither priced nor
split, and CAPRI's residual feeds FENI and FPRI had no market. Now all five bulks per member state price the
rations and split feed use (`feedBlkPrice_`, `feedShareEqu_`, p_rhoFeed from `arm/market1.gms`), and FENI and FPRI
are traded markets whose EU output comes from milling and sugar processing (`MaprFeed_`). Baseline: EU output and use
exactly CAPRI's 2030. Farm-to-Fork (s75): FENI and FPRI −10%, gap 4.59 → 4.53. docs/FEED_MARKETS.md. Next: the
post-solve modules (9i) and manure trade against CAPRI's endotech reference (9j).

## Sprint 9g — CAPRI's feed options as star 3.0 runs them (October 2026: done, default)

star 3.0's technology file (`refpol_endotech_all_sup.gms`) activates low-nitrogen feeding (`ghgTechLowNFeed 1`) and
the supplements (`ghgTechLineNitr 1`; active LINE, NITR, AComLN, 3NOP, LowNFeed). Both are now columns of the regional
models in the breeding framework, with CAPRI's effects, maximum shares (its max calibration run) and calibration:
- **Low-N feed** (`envind/low_n_feed.gms`): protein requirement cut 0.15 x excess / (1 + 0.5 x energy excess) from
  CAPRI's p_animReqCorrFac, manure N via (MANN + CRPR_EXPT) / MANN; `lownfeed_effects.csv`.
- **Linseed and nitrate** (`envind/line_nitr.gms`): linseed fed as the OOIL row per kg fat (energy, protein, dry
  matter), nitrate replacing crude protein (1.54 x dosage), CH4ENT −25% / −15% (multiplying when combined), cost
  half of costParLin x DM intake x dosage; `supplement_effects.csv`. 3-NOP, CH4 only, registered (zero without an
  emission price).

**Farm-to-Fork 2030** (s73 low-N feed, s74 + supplements, JRC121368 settings): low-N feed on 42% of manure N (Table 17:
0%, the option's potential 56%), linseed 0.8% and nitrate 0.2% of cattle (0% and 7%); milk price +30% (+1.5), pork
+38% (+43), poultry +26% (+18), pigs −22% (−14.5), enteric CH4 −16.4% (−14.6). 20-indicator gap 5.15 → 4.59. Nitrate
competes with low-N feed for the same protein saving; CAPRI's JRC-era run had no low-N feed adoption, so nitrate took
it there. JRC121368's Figure 7 checked: raw milk +1.2%; with star 3.0's block coefficients a 10% milk cut lifts the
milk price ~19% at fixed product prices, so the JRC-era dairy block differed (docs/DAIRY_PROCESSING.md).
docs/MITIGATION_IN_SUPPLY.md.

## Sprint 9f — CAPRI's dairy block on, as star 3.0 runs it (October 2026: done, default)

New rule (project lead): a block CAPRI star 3.0 runs is switched on and judged against its own CAPRI reference; the
Farm-to-Fork gap is recorded, not used to keep blocks off. The dairy block was the largest such block left off. Two
registered departures closed: all nine products traded bilaterally (five had cleared inside the block with fixed
extra-EU trade), and raw milk, fat and protein priced per member state (one EU ratio before). Against CAPRI's 2030
reference every dairy product's EU production and use is within 3.6%; domestic-use median 3.7 → 3.0%. Farm-to-Fork:
raw milk +34% against CAPRI's +1.5%, dairy cows −7.8% (−10), sheep −12.2% (−9.5); gap 3.77 → 5.15, the milk price
alone 1.6 points. Open: CAPRI's milk supply in its run (genomics adoption 15% against 3.8% here) and the figure's
value. Cyprus's milk price does not settle (0.2% of EU milk; reported). docs/DAIRY_PROCESSING.md.

## Diagnosis after Sprint 9e: where the herd overshoot sits (October 2026)

Farm-to-Fork 2030 (s60, gap 3.77): pigs −23.1% (CAPRI −14.5), dairy cows −13.7% (−10), sheep −15.5% (−9.5).

- **Pigs.** Brittany and Lombardy lose all their pigs (10.5 of the 26.9 M places lost in the EU); the rest of the EU
  falls 15.4%. The pig regions' N prices: Brittany €86/kg N, Weser-Ems 78, Münster 64, Lombardy 64, Catalonia 51.
  A fattening pig in Brittany excretes 23.1 kg N, of which 37% displaces mineral N (the marginal availability), so
  it carries 14.6 kg N net: €480 a year at €33/kg, far beyond its margin; above roughly €5–10/kg N a pig region
  cuts pigs first. Neither pig structure nor supply curvature differs from CAPRI's (Sprint 5, the `_ini`/`_max`
  check): the gap is the level of the regional N price.
- **Sensitivity** (s64, `--capped-regions=+FRH0,ITC4`: Brittany and Lombardy among JRC121368's relaxed regions,
  36% cut): gap 3.77 → 3.47, pigs −20.8%, dairy −12.2%; but the pork price falls to +32% (CAPRI +43), and Brittany
  still loses 46% of its pigs at €33/kg N. Relaxing two regions moves the EU numbers but does not bring the N
  prices of the pig regions down to where CAPRI's herds imply they were.
- **Dairy**: Italy −26%, Ireland −24%, the Netherlands −21%, France −16% (Germany −3%). **Sheep**: Ireland −50%,
  Romania −20%, Greece −17%, at N prices of €15–30/kg.

What would settle it is CAPRI's own Farm-to-Fork output by region - the surplus constraint's duals and herds - which
the project lead's installation does not hold (only the reference and the endotech runs). JRC121368 itself says
regional surpluses *rose* in "a few regions characterised by increased pig and cattle herds" (sect. 5.1.2), i.e. CAPRI
relaxed or did not bind the target there; capri-mod binds every EU region. No CAPRI equation found missing in
this pass: the over-fertilisation factor is fixed in simulations (`supply/prep_sim.gms`), low-N feeding had zero
adoption (Table 17), the technologies' cap (`Tot_MitFert_`) is CAPRI's.

## Sprint 9d — the biofuel loop closed (October 2026: done, default)

What Sprint 9c left open, now as CAPRI does it: **DDGS** a market commodity (output from the ethanol plants'
cereal feedstocks, `prodQuantBiofBy_`; trade; its price in the plants' feedstock cost, `biofFeedCost_`);
**CAPRI's feed bulks** for the member states (`feedBlkPrice_`, `feedShareEqu_`: FCER and FPRO split into products
by a CES, rho 6, bulk from the herds and rations, bulk price to the rations) replacing the single EU cereal and
cake indices; **non-EU DDGS feed** from p_ElasFeed (`tools/build/build_feed_demand_nonEU.py`, which reproduces the old
file); **non-fuel ethanol processing** (`ProcNQ_`); **mandate shocks** (`change_biof_mandate.gms`).

Checks: DDGS output = CAPRI's in every region; bulk products = CAPRI's bulk totals in every member state; CAPRI's EU
feed use reproduced at reference prices. Farm-to-Fork: gap 3.32 → 3.31, livestock prices +0.4–0.6 points (toward
CAPRI), beef animals −0.5 points; EU DDGS −7%, price −3.8%. Baseline: domestic-use median deviation 4.1 → 3.7%.
Remaining REGISTERED: milling by-products and fish meals in FPRO at reference prices; Norway's bulks not split.
Next star 3.0 default: the inner fertilizer model (Sprint 9e).

## Sprint 9c — endogenous biofuel markets, CAPRI's `BIOF_M` (October 2026: done, default)

Star 3.0's GUI default "Endogenous bio-fuel markets" (`BIOF_M = true`) was the first of the two star 3.0 defaults
capri-mod lacked. CAPRI then makes bio-ethanol and bio-diesel market products (`arm/market_model.gms`):
`SupplyBiof_` (output on the processing margin = producer price / CES feedstock cost, sigmoid × double log),
`MaprBiof_` (+ fixed non-agricultural, second-generation, exogenous output), `biofDemShare_` / `biofDem_` (share of
fuel use = mandate QUTS + sigmoid in consumer price / fossil price), `Cpri_` (additive tax), bilateral trade.

**Done.** All of it per CAPRI market region, summed to the model's trade regions (the EU's member states clear at
one EU price, as CAPRI's EU27yr19 block), calibrated as `def_biofuel_params.gms` to CAPRI's 2030 reference
(`tools/build/build_biofuel_market.py`). Checked: feedstock cost = CAPRI's BiofFeedCost in every region; output, first-
generation output and use reproduced in every region; production identity holds; the HCON CAPRI calibrates on is
total fuel (dump HCOM is fossil only), which reproduces CAPRI's HCOS shares and QUTS = 0.9 × share. Feedstock use
follows the output in every region. A scenario setting (default on), held for the baseline.

**Result.** Farm-to-Fork: EU ethanol −4.3%, biodiesel −1.4% (dearer feedstock cuts the margin), ethanol price
+8.6%, diesel +2.2%; feedstock use for biofuels: other cereals and wine −24%, rapeseed oil −7%. Gap 3.29 → 3.32
(cereal and oilseed prices −0.3 points). Baseline: production median deviation 3.8 → 3.5%, use 4.8 → 4.1%.
REGISTERED then (closed in Sprint 9d): DDGS and glycerine at reference prices, DDGS not in rations; non-fuel ethanol use fixed.
The loop (DDGS, feed bulks, processing, mandates) was closed in Sprint 9d. docs/BIOFUEL_MARKET.md.

## Sprint 9b — scenario settings as star 3.0 does (October 2026)

Rule agreed with the project lead: capri-mod is built as star 3.0; each scenario has its own settings; what a
scenario does not state takes capri-mod's (star 3.0's) default. The installation's GUI (`capri_gui_definition.xml`)
gives star 3.0's defaults (docs/SCENARIO_SETTINGS.md): manure trade ON (`New_Manure_Trade_fromGUI = true`) is now
capri-mod's default; the Green Deal group (`greendeal_scenario`) follows star 3.0's files (surptot.gms surplus rule,
manure trade on, genomics 0); Farm-to-Fork (`farm_to_fork_scenario`, the runner's default) carries JRC121368's own
settings (tiered rule with the 36% cap, manure trade off, milk-yield genomics 0.2). Manure trade is a scenario
setting like the technologies: it holds for the scenario and its baseline. Green Deal switches accept CAPRI's GUI
values only. Farm-to-Fork gap 3.29 (unchanged: the settings were already those of the `jrc121368` configuration).
Star 3.0 defaults capri-mod lacks: endogenous biofuel markets (`BIOF_M = true`) and the inner fertilizer model.

## Sprint 9a — Farm-to-Fork as star 3.0 configures it; pigs (October 2026)

**Star 3.0's surplus target is not JRC121368's.** CAPRI star 3.0's `pol_input/greendeal/surptot.gms` sets every EU
NUTS2 region's surplus limit to its baseline surplus per hectare x (1 - surpRedu/100): a homogeneous 50% cut, no
tiers, no cap (relaxations only from 2090). JRC121368 used a tiered rule (25/50/75/100% by 50 kg N/ha band) with
nine regions capped at the EU average 36%, and reports the EU surplus -33.5%. Both are now scenario settings
(`PolicyScenario.surplus_rule` "jrc121368" | "star3", `surplus_cut`; `greendeal_scenario(..., surplus_rule=)`), and
`run_f2f_2030.py --config` set a whole configuration (now `--scenario f2f|greendeal`, Sprint 9b):

| Configuration | Surplus rule | Manure trade | Milk-yield genomics | EU surplus | Pigs | Beef / pork / poultry price | Gap |
|---|---|---|---|---|---|---|---|
| `jrc121368` (the report's run) | tiered, 36% cap | off (report p. 24) | 0.2 | -32.1% | -21.1% | +17 / +34 / +23% | **3.29** |
| star 3.0 surplus rule only | homogeneous -50% | off | 0 | -45.4% | -30.4% | +42 / +103 / +80% | 15.8 |
| `star3` (star 3.0's files, the installation's GD reference) | homogeneous -50% | on (`manureTradeNew`) | 0 | -45.9% | -23.3% | +35 / +42 / +36% | 8.1 |
| CAPRI (JRC121368) | | | | -33.5% | -14.5% | +24 / +43 / +18% | |

So JRC121368's numbers are only comparable with the `jrc121368` configuration; star 3.0's own Farm-to-Fork is a
stronger scenario (the EU surplus falls by almost half). The default of the model's genomics stays star 3.0's (0);
in the `jrc121368` configuration it is 0.2 and changes the gap by 0.01.

**Pigs (-21% against -14.5%).** The cut concentrates in two regions: Brittany (target -55% of 328 kt; N price
EUR 68/kg; pigs -100%, area in use -8%, manure -238 kt against a surplus cut of -182) and Lombardy (-63%; EUR 55/kg;
pigs -99%). Without manure leaving the region (the report's rule) only animals can carry the cut there. With star
3.0's manure trade the same regions export manure and keep most pigs (Brittany -28 / -36%, EUR 32/kg), but star
3.0's 50% target is larger. The regional data of CAPRI's own Farm-to-Fork run (surplus dual, herds per region) would
settle which mechanism CAPRI used; the received results hold only the reference and the endotech runs.

**Dairy block with the bilateral market.** The EU raw milk price now comes from the block in the bilateral market
too (it had been dropped: the pooled milk market set it). With the block the EU's product prices rise 28-63% (butter:
exports are 12% of production, imports nil, so a 13% supply fall must be absorbed by EU use) and raw milk +86%: still
opt-in. CAPRI's +1.5% milk price implies EU milk supply barely fell in its run (cows -10%, yields up).

## Sprint 8m — CAPRI's bilateral market and the 2030 baseline (October 2026: done, default)

**Market.** CAPRI's market model replaces the world price with the EU premium: a market price per region, total
use the Armington aggregate of domestic sales and imports, imports a CES over origins, every bilateral flow priced
at the exporter's price + CAPRI's transport cost and tariffs, from CAPRI's own market results of the run's year
(2017 base market, 2030 reference), substitution elasticities from market1.gms / market1_ch.gms. EU tariff-rate
quotas with CAPRI's sigmoid (not binding under Farm-to-Fork: the meat quotas are far from filled in the 2030
reference). Wheat includes durum, olives and paddy reach the market as olive oil and milled rice. Gap 4.51 -> 3.48:
cereals +8.2% (CAPRI +8), beef +16.7% (+24), pork +31.7% (+43), poultry +22.9% (+18), pigs -21.4%.

**Baseline.** Three projection gaps closed: CAPRI's trend projection read by the model's names and regions (246
of 248 regions had used EU medians), livestock output per head and requirements following the projected yields,
crop areas following CAPRI's trend levels. Median deviation from star 3.0's 2030 reference 9.5% -> 3.8% (activity
levels), 9.4% -> 3.8% (production). Gap 3.30.

**Open.** Pigs (the regional nitrogen price), beef and pork prices (+17 and +34 against +24 and +43), manure CH4 and
N2O; dairy product prices without the dairy block (they move with EU milk but do not reach the milk price); the
dairy block with the new market not yet re-run; global (erga omnes) quotas; the model's bull and heifer head units.

## Sprint 6c — star 3.0 as the reference: settings, world market base, placeholders (October 2026)

**Reference.** The model is built on CAPRI star 3.0 (base 2017, Green Deal reference 2030); JRC121368 was produced
with the 2020 CAPRI (base 2012, OECD-FAO 2017–2026 baseline, milk-yield genomics on). Star 3.0 is the reference;
the Farm-to-Fork comparison stays as a check on signs and magnitudes, with a version gap expected; parameters are
not tuned to it. The like-for-like check is the 2030 baseline against star 3.0's own 2030 reference
(`tools/check/compare_baseline_capri.py`, docs/BASELINE_REPRODUCTION.md).

**Technology settings are scenario configuration (done).** `ghgTechMYld`, `ghgTechFEff` as CAPRI's
`refpol_endotech_all_sup` sets them (launch value wins, same in reference and policy run):
`PolicyScenario.endotech`, `run(endotech=...)`, `--endotech`; baseline cache and genomics calibration per
setting. Default star 3.0 (milk yield 0); gap 4.36 either way.

**World market base and placeholders (done, default).** Every region's base balance from CAPRI's FAO_agg (world
sugar had been sugar cane, pork and eggs 40–50% too large); sugar from beet at CAPRI's member-state yields and the
beet price following sugar; FATS, OFOD_M and the beet world market removed; rye and oats in the other-cereals
market; dairy products at CAPRI's yields without the block (docs/WORLD_MARKET_BASELINE.md). Gap 4.36 → **4.51**:
beef +9% (CAPRI +24), poultry +16% (+18), pork +21% (+43). With CAPRI's world sizes the EU premium approximation
lowers the beef premium: the meat-price gap now runs through the market structure itself.

**Baseline check (first results).** Median deviation from star 3.0's 2030 reference: activity levels 9.5%, market
production 9.4%, domestic use 11.3%, relative prices 28%. To settle: fattening bull and heifer levels (model
1.7 M and 2.4 M against CAPRI 4.6 M and 8.7 M; unit convention or projection), fruit, vegetable and wine prices,
2030 self-sufficiency in the market, farm milk −10%.

**Next: Sprint 8m — CAPRI's full market** (docs/ARMINGTON_MARKET.md): producer price per region, two Armington
nests over bilateral flows, transport costs and tariffs, then TRQs; replaces the world price and the EU premium.

## Sprint 6b — biofuels and dairy in the market (October 2026)

**Biofuels (crushing stage 4, done, default).** CAPRI's `biofFeedCost_` / `biofFeedCostAgg_` / `Biof_` /
`prodBiof_` per member state at fixed biofuel output (CAPRI's scenario setting without `BIOF_M`). The
builder reproduces CAPRI's `BiofFeedCost` exactly; the post-solve module is retired. Gap 4.64 -> 4.62.

**Reported EU prices.** The report multiplied the EU price by the Armington premium twice (supply saw it once).
Corrected, the Farm-to-Fork price changes are: cereals +5.7% (CAPRI +8), oilseeds +11.8% (+11), vegetables
and permanent crops +9.7% (+15), beef +13.7% (+24), pork +20.2% (+43), poultry +21.1% (+18), milk +3.6% (+1.5).
The earlier sections' price comparisons used the inflated report. What this changes in the diagnosis: the
model's meat prices are BELOW CAPRI's, not above, while pigs fall more (-25% vs -14.5%) — the pig cut is
not price-driven; it is the regional nitrogen price (Sprint 2 diagnosis stands).

**Livestock products and world dairy data (done, default).** Animal output split by CAPRI final product
(cull-cow beef to beef, sheep and goat milk to raw milk, hen meat to poultry); world dairy-product balances
from CAPRI's FAO_agg. Sheep and goats -14.9 -> -12.8% (CAPRI -9.5). Default gap **4.30**.

**Dairy processing (Stage 1 built, opt-in).** CAPRI's `DairyNQ_` / `ProcMargM_` / `FatsProtBal_` per member
state (docs/DAIRY_PROCESSING.md). Faithful to CAPRI's equations and data (Hessian reproduces `p_ElasDair`;
fat and protein balances close), but Farm-to-Fork raw milk +34% against CAPRI's +1.5%: the block passes
product price changes to milk about 2.5-fold and the model's dairy-product prices rise 11-19%. CAPRI's
small milk price implies flat dairy-product prices; the missing pieces are EU feed demand for whey and SMP
falling with pigs and calves (JRC121368: dairy net exports +5% from whey) and CAPRI's cross-price food
demand. Gap with the block 5.63. Stage 3: those two, then the block on by default.

## Sprint 7d — cattle genomics, and dairy Stage 3 (October 2026)

**Genomics (done, default).** breeding.gms's genet_yld and genet_eff as columns of the regional models (manure
rows, feed requirement rows, milk revenue, CAPRI's calibration). Adoption: milk yield 3.3% (Table 17: 15%),
ruminant efficiency 33% (9%). Gap 4.30 -> 4.36. The departures follow the nitrogen price: an option that cuts
manure N per head (efficiency, −5% for ~EUR 2.4) is worth far more at the model's ~EUR 9/kg N than in CAPRI,
one that adds it (milk yield, +1.7%) far less. With the dairy block on, milk-yield adoption rises to 31%
(milk price +30%).

**Dairy Stage 4 (done, opt-in).** CAPRI's dairy block for the 53 non-EU market regions with CAPRI's raw milk
supply functions: world dairy prices +2.6-3.5% instead of 5-8%; raw milk +30 -> +28%; gap with the blocks 5.35.
What remains is inside the EU (fresh milk products and cream clear in the EU with inelastic demand).

**Dairy Stage 3 (done, opt-in).** FMIL feed demand from calves (CES 0.5) and CAPRI's cross-price food demand
for the nine products. Raw milk +34 -> +30% (CAPRI +1.5%); gap with the block 5.44. The block stays off by
default: the remaining departure is in the dairy-product prices (+9-16%), which CAPRI's milk price says barely
moved; checking them needs CAPRI's Farm-to-Fork market results.

## Manure N2O by stage (October 2026)

CAPRI's gases.gms: manure N2O per activity = manure N × loss shares by stage (housing+storage N2OMAN, application
N2OAPP, grazing N2OGRA, leaching N2OLEA) + indirect N2O from volatilised NH3 (N2OAMM); the loss shares move with the
ammonia technologies (ammo_tech.gms applies storage effects at housing level). Now in the model from CAPRI's 2017
results per region and animal (1.6% of manure N in all, median) and CAPRI's technology effects (covers −55 to −91%
on housing/storage N2O, low-emission spreading +44% on application N2O, inhibitors on manure −36% on application).

| Stage (kt N2O-N, EU) | 2030 baseline | Farm-to-Fork | Change |
|---|---|---|---|
| housing and storage | 38.3 | 24.3 | −36.5% |
| application | 57.3 | 40.1 | −30.0% |
| grazing | 50.1 | 41.8 | −16.7% |
| leaching | 1.4 | 1.2 | −16.2% |
| **all** | 147.1 | 107.4 | **−27.0%** (CAPRI −3.2%) |

GHG total 391 Mt in the baseline (CAPRI 372), −22.5% (CAPRI −14.8); gap 5.89. With CAPRI's own structure the model
moves further from JRC121368: its herds fall more than CAPRI's (pigs −22% vs −14.5%, sheep −17% vs −9.5%) and it
adopts inhibitors on 41% of manure N. JRC121368's −3.2% is hard to reach with these stages unless application N2O
rises (more N reaching the field once NH3 is retained - CAPRI's emission cascade - is not yet in the model's
N2O). CAPRI's emissions by source in the Farm-to-Fork run would locate the difference.

## GHG accounts by source and histosols (October 2026)

**Bug.** Soil N2O, liming and urea CO2 were computed in Mt while every other gas is in kt (1000 ha × kg/ha divided by
1e6), so the GHG total omitted them (EU soil N2O 83 kt instead of 83 Mt). The fertiliser-N2O indicator, a ratio,
was right; the GHG total was not.

**Soil N2O by source, as CAPRI's gases.gms.** Mineral N (N2OSYN) from the balance's own mineral N (52.9 Mt CO2-eq),
crop residues (N2OCRO, 43.9 Mt), histosols (N2OHIS, 13.2 Mt), manure (N2O_MAN, 87.3 Mt), liming 7.7 Mt. Baseline
total 401 Mt against CAPRI's 372.

**Histosols.** Organic-soil shares from p_OrgSoilOri, IPCC 2013 wetlands factors weighted by FAO climate zones; the
fallowing option of no_histosols.gms (idled histosol area keeps its land, its emissions stop; CAPRI's curvature from
its calibration runs; linear term from the base land dual). Under Farm-to-Fork fallowing stays near zero (Table 17:
2% → 9%): CAPRI adopts because its land rent (~100 EUR/ha, costsaving0) falls; the model's land-row duals are a few
EUR/ha, so there is little rent to lose.

**Result.** GHG total −20.4% (CAPRI −14.8; −17.0 before, without soil N2O); gap 5.81. By source: mineral N2O −44.5%
(−40.4), manure N2O −18.4% (−3.2), enteric CH4 −16.3% (−14.6), manure CH4 −17.3% (−12.2). Manure N2O is the next
item: CAPRI splits it into housing/storage by system (N2OMAN), application (N2OAPP) and grazing (N2OGRA), with the
ammonia technologies and inhibitors acting on them.

## Sprint 7b — CAPRI's two dairy activities (done, default)

**CAPRI's block.** Dairy cows are two activities, low-yield DCOL and high-yield DCOH, half the herd each at base
(res_17), with their own milk yield, requirements, manure N, costs and PMP terms. Per cow moved from DCOH to DCOL
(EU medians relative to the average cow): milk −50%, manure N −31%, energy −30%, protein −35%, dry-matter limits −17%;
calves, cull-cow beef and replacements are the same. Per kg of milk the low-yield cow excretes about as much N, per
head 31% less: the split lets a region keep cows (and the grass they eat) while cutting manure N.

**Now.** One column z (1000 cows moved from DCOH to DCOL; DCOL = ½ DCOW + z), as the grassland split: DCOW's own
coefficient in every manure-driven row × the manure-N change; the cows' energy, protein and dry-matter rows in the
conic feed block × the requirement changes (`solve_regional_conic(req_extra=...)`); 0 ≤ DCOL, DCOH; CAPRI's PMP terms
(q_DCOL + q_DCOH) z²/2; linear term calibrated on the first baseline solve from the duals of every row z enters
(the feed block now returns its requirement rows' duals), plus the milk revenue of z at the current milk price.
Milk output, manure N2O and ammonia follow z; enteric CH4 follows the cows' feed.

**Result.** 2030 Farm-to-Fork: low-yield cows 50% → 51.8% of the herd; dairy cows −12.0 → −11.7% (CAPRI −10); gap
5.72 → 5.73. Small: at CAPRI's PMP terms the shift costs about as much as the N it saves. Bulls (BULL/BULH) and heifers
(HEIL/HEIH) are not split: their pairs differ in fattening length (France: bulls 164 vs 388 days) and slaughter
weight, which ties them to the young-animal markets, not only intensity.

## Items not yet modelled: first pass (October 2026)

| Item | CAPRI | Status | F2F gap |
|---|---|---|---|
| Fertiliser side effects, mineral N | `p_litRevFertTechs` N2OSYN, NH3SYN (ghgMiti.gms l. 552-555) | done | 6.13 -> 6.29 with fodder |
| Fodder values in 2030 | fodder unit values = fodder-balance shadow prices, 2030/2017 | done | (above) |
| Pesticide target on regional costs | conventional_io.gms: PLAP -target, INPO +50% per region and crop | done (res_17 PLAP x UVAG, INPO, FERT) | 6.29 -> 6.41 |
| **Inhibitors on manure** | N2OMAN option, NMAN credit, NH3APP side effect (ghgMiti.gms l. 557-563) | **done**: decided at the N price also with technologies inside | **6.41 -> 5.70** |
| Coupled-support response | cap_after_2014 ref vs without VCS | test done: MAD 1.23 points (29 indicators), r = +0.81 | - |
| Genetics | breeding.gms, calibrated on costsavings ini/max | **done (October 2026)**: genet_yld (0.2, as JRC121368's era) and genet_eff as supply-model columns with CAPRI's calibration; adoption 3.3% / 33% (Table 17: 15% / 9%) | 4.30 -> 4.36 |
| Low-N feed | low_n_feed.gms | not built: 0 adoption in JRC121368's Farm-to-Fork (Table 17) | - |
| Tillage | tillage.gms | not built: soil carbon only (not in the 20 indicators) | - |
| Histosols | no_histosols.gms, calc_lulucf_carbon.gms (N2OHIS) | **done**: N2OHIS 13.2 Mt in the GHG total; fallowing built and calibrated, ~0 under Farm-to-Fork (Table 17: 2% -> 9%) because the model's land rents are a few EUR/ha | with the GHG fix: 5.73 -> 5.81 |
| Winter cover crops | cover_crops.gms; Green Deal minimum catch crops (organic_io.gms 50% x organic, conventional_io.gms pesticide cut / 2; e_minCoverCrops, winterCover_) | **done**: requirement, winterCover_ row, BioFix from p_cInput (def_cbalance.gms) in balance, allocation and need rows, residue N2O. Adoption 16% -> 41% of eligible area (Table 17: 23% -> 32%) | 5.70 -> 5.72 |
| Cattle intensity split | DCOL/DCOH, BULL/BULH, HEIL/HEIH: at base each pair splits the herd in half (res_17 Brittany: DCOL 5,357 kg milk and 126 kg N per cow, DCOH 8,927 and 212) | **dairy done (Sprint 7b)**: low-yield cows 50% -> 51.8%, dairy cows -11.7% (CAPRI -10). Bulls and heifers open: their pairs differ in fattening length and slaughter weight | 5.72 -> 5.73 |
| Dairy processing | fat and protein balances, raw milk value; sheep and goat milk into the same balance | sprint to plan | - |
| Crushing stage 4 | biofuel demand for oils inside the market | needs p_biofuelData | - |

**Inhibitors on manure.** CAPRI's option was in the model but skipped whenever the ammonia technologies were decided
inside the regional conic model (the default), so its adoption was always zero. It is now decided at the region's N
price in both setups: manure N counts × (1 + share × NMAN) toward crop need, at CAPRI's calibrated cost per tonne of
manure N; its maximum share is the manure not dropped on pasture. CAPRI's side effect raises application NH3 on
treated manure by (1 − lit)(1 + NMAN) − 1 (lit = −0.25 everywhere), applied to the loss cascade's application stage
at the current ammonia-option shares. F2F: adoption 41%, pork price +29.5% (CAPRI +43), poultry price +32% (+18),
ammonia −38.5% (−33), gap 5.70. The decision uses the previous solve's N price, like the external rule did; the run
needs 19 iterations instead of 11.

**Winter cover crops.** CAPRI's Green Deal files require a minimum catch-crop area: 50% × the organic target
(organic_io.gms) plus the pesticide cut / 2 on the remaining target (conventional_io.gms), each times the area
without winter cover, plus the baseline catch crops. With o = 25% and a 50% cut that is a quarter of the area without
winter cover. The catch crops need land not already under winter cover (CAPRI's winterCover_ row, now in the model);
their N (fixation and residues, BioFix = p_cInput / 24 × 0.75 × 0.5) supplies crop need and enters the balance as
fixation, so the surplus is unchanged while mineral N falls; their residues emit N2O. One deviation (registered):
CAPRI subtracts the area under winter cover with p_winterCoverShare0, the shares as given, which exist at NUTS2 only
for Austria and a few German regions; elsewhere nothing is subtracted and the requirement exceeds the land that can
carry a catch crop in 100 regions (CAPRI's own winterCover_ row uses the filled shares). The filled shares are used in
both. Result: catch crops 16% → 41% of the eligible area, against JRC121368 Table 17's 23% → 32% (the report
describes an earlier rule, "25% more cover crops"); fertiliser N2O −46.1% (CAPRI −40.4); gap 5.72.

**Coupled-support test** (`tools/run/run_vcs_2030.py`): CAPRI's premium change per region and activity applied to the
model's 2030 baseline. Herds, areas and prices follow CAPRI closely (sugar beet, soybeans, sheep, beef price), with
three gaps: suckler cows −2.1% against −7.4% (82% of their premium removed), durum wheat area +0.2% against −6.8%
(Italy −10.6%) and the pulses price +7.4% against +2.8%.

## Manure N2O against JRC121368 Table 18 (October 2026)

JRC121368 reports manure N2O -3.2% and, in Table 18, what CAPRI's ammonia technologies did to GHG: housing and
storage +0.9 Mt CO2eq, application +5.2 Mt - the technologies RAISE manure N2O, which offsets most of the herd cuts.
Two CAPRI mechanisms were missing or misread:

1. **Loss cascade** (HOUSN_, APPLN_): N2O factors apply to the N left after NH3 at the same stage, so NH3 kept upstream
   adds application N2O. Now in (`ammonia_techs.stage_n`).
2. **HOUSN_ sums only housing and combined options**: ammo_tech.gms moves the storage options' N2O effects to N2OHOU,
   but the equation never applies the plain covers' - in CAPRI a cover does not cut manure N2O. The model did.

| 2030 Farm-to-Fork | Manure N2O | of which technologies | Gap |
|---|---|---|---|
| before | -28.8% | | 4.71 |
| + loss cascade | -25.1% | -4.3 Mt | 4.68 |
| + CAPRI's housing equation | **-21.5%** | -1.8 Mt | **4.64** |
| CAPRI | -3.2% | +6.2 Mt (ammonia options) | |

The rest: nitrification inhibitors on manure give -4.8 Mt in the model (43.7% adoption x -36% application N2O),
more than CAPRI's -1.8 Mt for all inhibitors; without them the ammonia options add +2.9 Mt. CAPRI's cost terms for the
manure option (target N2OMAN) are not in the data received - its reference run shows the option unused (marginal
-8,800 in Denmark) - so the model's adoption, built on the mineral option's cost, is the likely remaining error.

## Sprint 7c — CAPRI's bull and heifer splits (October 2026: done, default)

CAPRI fattens young bulls (BULL low, BULH high) and heifers (HEIL, HEIH) at two intensities, equal numbers at base.
Unlike the dairy split they differ mostly in fattening LENGTH (DE94: bulls 173 vs 270 days, heifers 78 vs 223) and
slaughter weight (bulls 281 vs 422 kg), and each animal takes one young animal (IBUL, IHEI). The model's BULL and HFRS
are census heads - stalls over the year - so `tools/build/build_cattle_intensity.py` turns CAPRI's per-animal items into
per-stall ones (x 365 / days for manure N, beef and young animals; daily for energy, protein, dry matter) and
expresses low minus high relative to the animal's average stall (HFRS includes the replacement heifers HEIR, which
do not move). Median per stall: bulls +40% beef, +86% young animals, -10% manure N, -14% energy; the PMP curvature
of the shift comes from CAPRI's own terms converted to stalls (q (365 / (rho days))^2).

In the supply model one column per animal (`_cattle_columns`, beside the dairy column) enters the manure rows, the
feed requirement rows and the bounds from the stall shares, is calibrated on the base duals, and carries the
scenario's beef price and young-animal price changes; the accounts take its manure N, beef output and young-animal
demand (`CAPRIModel._young_animal_balance`).

| 2030 Farm-to-Fork | Low-intensity share | Gap |
|---|---|---|
| bulls (stalls) | 33.6% -> 34.1% | |
| heifers (stalls) | 7.2% -> 6.5% | |
| EU aggregates | within 0.2 points | 4.70 -> 4.71 |

As with the dairy split, CAPRI's curvature keeps the shift small; whether CAPRI's own run moves more needs its
Farm-to-Fork output by activity.

## Sprint 8 — CAPRI's land rules as default (October 2026: done)

### Follow-up: split regions, Dutch importers, poultry (October 2026)

| Run (2030 Farm-to-Fork, land rules default) | Gap | Regions above EUR 100/kg N | Land-market fallbacks |
|---|---|---|---|
| grassland balance fixed | 4.85 | 4 | 5 (Dutch importers) |
| + split/merged NUTS regions from their CAPRI group | 4.92 | 4 | 5 |
| + JRC121368's 36% rule for infeasible targets (default) | **4.70** | 6 | 0 |
| same, with the manure market | 4.77 | 3 | 0 |

- **Split and merged regions.** A first-candidate mapping had put CAPRI parents whole on one part (Finland FI1B: 990
  kg manure N per dairy cow, arable land 709 kha on 121 kha of crops) and left renamed or split regions on national
  averages. `tools/lib/_model_regions.py` (SPLITS_MERGES, capri_groups, region_to_capri) and `shared/region_capri_map.csv`
  now map them for all builders and the runtime.
- **Dutch importers.** Their CAPRI-reference manure imports (52-123 kg N/ha) stay fixed without the manure market and
  made the tiered target infeasible. JRC121368's own rule for infeasible regions (the EU-average 36% cut) now applies
  to them too. A capped manure trade (flows may only shrink) was built and dropped: the Dutch exporters would have to
  take back 52 kt N under their own targets and the pool never cleared (imbalance 11%).
- **Poultry.** The N row charges N price x N surplus per animal; Swedish broilers produce EUR 29 of output per kg of
  N in the balance, so at EUR 70/kg they go. CAPRI's equation does the same; the open question is the regional N price.
- **Friesland (NL12)** at EUR 16,000/kg N: its baseline matches CAPRI's item by item; the tiered rule asks a 70% cut.
  Relaxed as well: gap 4.58. With no regions capped up front the infeasibility rule relaxes nine Dutch regions but
  leaves BE21/BE23/BE25 at EUR 28,000-145,000/kg (gap 5.26). Kept as a sensitivity.

### Done: the grassland balance, and the land rules become the default (October 2026)

**The cause of the runaway regions.** Run separately, the no-idle-land rule alone gave 9 regions above EUR 100/kg N
(the per-hectare target only adds the land-from-forest incentive). The regional problem of Ostra Mellansverige (SE32)
at the end of a land-rules run showed why: 69 kha of fodder leys (OFOD, 49 kg N/ha surplus) unchanged at an N price
of EUR 332/kg. The model's "grassland" row - GRAS + MAIF + OFOD <= grassland + 0.2 x arable land, its own soft limit
- became an equality under LandBalNoSlak_ and pinned arable fodder to its base area, so the fodder stayed and the
cattle had to eat it; the N cut fell on poultry and pigs. CAPRI's LandBalNoSlak_(GRAS) is GRAE + GRAI = grassland;
fodder maize (MAIF) and other fodder (OFAR, ROOF) are arable crops in the arable balance. The row now follows CAPRI
under the land rules.

| Run (2030 Farm-to-Fork) | Gap | Cereal / pork / poultry price | Dairy | Beef animals | Pigs | Poultry | EU farmland | N price > EUR 100/kg |
|---|---|---|---|---|---|---|---|---|
| old default (idle land, base-farmland target) | 5.81 | +22 / +28 / +32 | −11.8 | −15.5 | −22.1 | −15.0 | −1.9% | 1 |
| no idle land only | 6.81 | | −11.6 | | −27.3 | −17.5 | | 9 |
| land rules, old grassland row | 6.09 | +13 / +52 / +59 | −10.5 | −10.4 | −27.5 | −20.7 | | 11 |
| **land rules, CAPRI's grassland balance (default)** | **4.85** | +10 / +40 / +47 | −13.1 | −14.8 | −25.3 | −16.8 | +1.8% | 4 |
| + manure market | 4.68 | +17 / +12 / +18 | −7.5 | −12.8 | −13.3 | −10.1 | +1.9% | 3 |
| CAPRI | | +8 / +43 / +18 | −10 | −18 | −14.5 | −16.5 | +3% | |

**Dutch importing regions.** NL11, NL12, NL13, NL23, NL32 and NL34 import manure in CAPRI's 2030 reference (52-123 kg
N/ha). With the manure market off these imports are held per hectare of cropland - set-aside included (NL34 fallow:
31 kg deposition + 86 kg imported manure = 114 kg N/ha surplus) - so their 61-70% cut is out of reach and the solve
falls back to the plain problem (NL12: EUR 17,000/kg). JRC121368's CAPRI had no manure trade at all; the newer CAPRI
trades manure endogenously, and with the manure market the land market solves in every region. Open.

### Update: the land block re-examined (October 2026)

**Land rents are not the cause.** CAPRI's 2030 land duals (D_AREA) are about EUR 366/ha arable, 245 grassland and
1,662 permanent crops; the model's are a few EUR/ha because PMP calibration folds the rent into each activity's
terms. Under CAPRI's land rules the land rows are equalities and land supply comes from the land market, whose slope
is CAPRI's; moving the rent level into the rows (f - A'mu0) leaves the solution unchanged. The level would matter
only for idle land in the default rows and for the histosol fallowing column.

**Three defects found while chasing the runaway regions:**
1. *Proxy targets.* 82 regions took their N target from their own surplus pattern scaled to CAPRI's national value,
   because the builder missed CAPRI's regional values under old NUTS codes. Rebuilt from CAPRI's regional SURTOT
   (`tools/build/build_capri_baseline_surplus.py`): Valle d'Aosta 250 -> 48.5 kg N/ha (cut 70% -> 26%), Luxembourg
   235 -> 157 (68% -> 49%), Swedish regions ~100 -> 70-79.
2. *Catch crops against the landscape floor.* CAPRI's winterCover_ adds FALL.FLOOR to the catch-crop area; the model
   did not, so in alpine regions (Tyrol: floor 22 kha on 14 kha of arable land) the two rows could not both hold,
   the land-market solve failed and the fallback emptied grassland and herds (Tyrol dairy 68 -> 3).
3. *Silent fallback.* A failed land-market solve dropped to the plain problem (land may idle). The landscape floor is
   now relaxed inside the land market; an unreachable N target still falls back, reported as `land_market_failed`.

**Runs (2030 Farm-to-Fork, all fixes):**

| Run | Gap | Dairy | Beef animals | Pigs | Poultry | Pork / poultry price | EU farmland | N price > EUR 100/kg | Land market failed |
|---|---|---|---|---|---|---|---|---|---|
| default | **5.81** | −11.8 | −15.5 | −22.1 | −15.0 | +28 / +32 | −1.9% | 1 | 0 |
| land rules | 6.09 | −10.5 | −10.4 | −27.5 | −20.7 | +52 / +59 | | 11 | 6 (Dutch) |
| land rules + manure market | 5.28 | −6.1 | −10.9 | −14.2 | −10.9 | +13 / +20 | +2.7% | 3 | 0 |
| CAPRI | | −10 | −18 | −14.5 | −16.5 | +43 / +18 | +3% | | |

**Decision: defaults unchanged.** The land rules alone are still worse than the default (6.09 vs 5.81), and the
manure market is off because JRC121368's CAPRI kept manure in its region. What remains under the land rules without
trade: with the target per hectare of current farmland, each hectare added from forest is worth target x N price;
the land market adds grassland, the grass must be grazed, so cattle rise and poultry and pigs go (SE32: grassland
+70%, beef cows +63%, poultry −100%, N price EUR 332/kg). The model meets the target only through fertiliser
technologies and herd changes; CAPRI's grass yields also move with fertiliser. Next: whether CAPRI lets grass output
fall without feeding it (fodder balance as an inequality or grass yield response), and which nine regions CAPRI
relaxed (needs CAPRI's Farm-to-Fork output).


Runs on the current code (2030 Farm-to-Fork; land rules = `--land-no-slack --surplus-current-ha`):

| Run | Manure trade | Capped regions (36% cut) | Gap | Pork / poultry price | Pigs | Regions with N price > €100/kg | Converged |
|---|---|---|---|---|---|---|---|
| default | off | the nine | 6.13 | +35 / +37 | −24.0 | 4 | 11 it. |
| land rules | off | the nine | 7.52 | +68 / +72 | −29.7 | 15 | 14 it. |
| land rules | off | none | 10.44 | +99 / +84 | −34.0 | | 12 it. |
| land rules | off | nine + Brittany, Lombardy | 5.34 | +51 / +58 | −27.4 | 13 | 14 it. |
| default | off | nine + Brittany, Lombardy | 5.53 | +28 / +32 | −21.9 | | 9 it. |
| manure market | on | the nine | 5.23 | +13 / +20 | −13.7 | 1 | 10 it. |
| **land rules + manure market** | on | the nine | **5.03** | +16 / +24 | −15.9 | 5 | 9 it. |
| CAPRI | | | | +43 / +18 | −14.5 | | |

**Manure pools under the land rules (fixed).** The Latvian pool's "imbalance 1.0" was not Latvia: the pool
equilibrium QP failed in Clarabel (unscaled; pool prices of hundreds of EUR/kg N, slopes differing by orders of
magnitude after the response-factor correction), the failure set the imbalance to 1.0 and kept the old prices, and
the worst-pool label pointed at whichever pool was last worst. Scaled, with AlmostSolved accepted, the run converges in
9 iterations. A failed pool solve now shows its status in the trace.

**Why the land rules stay off for the JRC121368 setup.** Without manure trade, 15 regions reach N prices above
€100/kg. Two kinds:
- *High-surplus livestock regions* — Brittany (€295/kg; pigs and poultry −100%, suckler cows +193%), Lombardy (€130),
  NL32 (Noord-Holland), the Azores (PT20). These fit the report's description of its nine relaxed regions ("high GNB values in the baseline
  associated with high animal numbers"), but the model's nine are chosen by the highest CAPRI baseline surplus per ha
  (Belgian and Dutch regions, Malta) and Brittany (rank 24) and Lombardy (rank 20) are not among them. Adding them
  brings the land-rules gap from 7.52 to 5.34. The report does not name its nine, so this stays a sensitivity
  (`--capped-regions=+FRH0,ITC4`) until CAPRI's Farm-to-Fork output shows which regions were relaxed.
- *Regions that are not high-surplus* — Luxembourg (€145,000/kg), Valle d'Aosta, three Swedish regions,
  Pohjois- ja Itä-Suomi (FI1D), Madeira (PT30). Farmland grows 30–45% out of forest and other land: with the target per hectare of current
  land each added hectare is worth target × N price, which at these prices beats CAPRI's land-transformation costs;
  the added grassland must be eaten, and herds swing to sheep (Luxembourg: all cattle and pigs −100%, sheep ×90).
  This is a defect of the model, not CAPRI's infeasibility: none of these regions has a high surplus. Next: why the
  N price runs away there — candidates are the fodder balance (all grass produced must be fed; CAPRI can also move
  grass yields with fertiliser) and the land-market terms at these regions.

With manure trade the land rules help (5.23 → 5.03) and the runaway regions mostly disappear (5 above €100/kg): manure
leaving the region is the relief valve the report names for its infeasible regions.

## Finding: CAPRI's Green Deal runs trade manure (October 2026)

Looking at Brittany and Lombardy under CAPRI's land rules: with farmland held and a 59% cut (Brittany's tiered
target), mineral N can supply at most 78 of the 179 kt to be cut; the rest must come from manure, so pigs and
poultry go and the region keeps its fodder land busy with suckler cows and sheep (pulses 9 → 300 kha). That is
what CAPRI's rules imply **if manure cannot leave the region**. But CAPRI's own Green Deal reference in the project
lead's installation (`res_2_1730greendeal_refpol_endotech_all_ini`, META) runs with **"New Manure Trade Module: On"**
and "Manure trade is relevant for convergence: true", and its 2030 baseline already exports manure (Brittany 90 kt
N, Weser-Ems 68 kt; `priFertDist_*1730`: `p_manureExports`, sell/buy costs). The model's manure market
(`use_manure_market`, CAPRI's `manureTradeNew`) had been kept off on the strength of JRC121368's sentence that
"all manure generated in a region has to be used within that region" (p. 24).

**Two fixes on the way.** (1) The manure pools no longer cleared (imbalance 0.26–0.29 of supply for 60 iterations):
the regions' trade schedules were read from the stored QP by recovering its duals, but regions are solved with the
conic feed block, which is not in that QP; the schedules now use the conic solve's own multipliers
(`CAPRIModel._update_manure_pools`) and the pools clear in 10 iterations. (2) Norway is a supply region but not in
the EU: CAPRI's Green Deal files apply the surplus target, organic targets and pesticide cuts to `EU27yr19` only
(`surptot.gms`, `organic_area.gms`, `conventional_io.gms`), and landscape targets come for EU regions; the model
applied all four to Norway too (Norwegian regions then dumped 40–70% of their manure into a pool with no buyers).
EU policy instruments now skip non-EU regions (`SupplyModule.NON_EU_PREFIXES`).

**Runs (2030 Farm-to-Fork, grassland split on, both fixes):**

| Run | Gap | Pigs | Poultry | Dairy | Pork / poultry / beef price | Manure CH₄ | Enteric CH₄ | Converged |
|---|---|---|---|---|---|---|---|---|
| default (no manure trade) | 6.13 | −24.0 | −13.8 | −12.7 | +35 / +37 / +33 | −18.5 | −17.2 | 11 it. |
| **+ manure market** | **5.23** | **−13.7** | −10.6 | −8.1 | +13 / +20 / **+24** | **−11.8** | −13.5 | 10 it. |
| CAPRI | | −14.5 | −16.5 | −10 | +43 / +18 / +24 | −12.2 | −14.6 | |

With manure trade the regional nitrogen prices fall (Brittany €10, Weser-Ems €12/kg N; it exports manure instead of
cutting pigs), and pigs, beef price, manure and enteric CH₄ come to CAPRI's figures; the pork price falls short.
With CAPRI's land rules as well, the earlier (unconverged) run gave a gap of 5.13 and farmland held; with the fixes
the pools did not clear there (the Latvian pool's imbalance stayed at 1.0 of its supply on the full EU) — fixed in
Sprint 8: the pool QP failed silently; with the land rules and manure trade the gap is 5.03.

**Decision: no manure trade for JRC121368 (resolved from the report).** The report (now in
`capri_data/sources/jrc121368/jrc121368_report_text.txt`) states it as a limitation of the CAPRI version used:
"the model assumes that all manure generated in a region has to be used within that region. There is evidence that
livestock-intensive regions process and/or export their manure to neighbouring regions with lower nitrogen loads.
Therefore, the GNB for these regions is overestimated and impacts on animal numbers would be lower for them were we
able to capture the trade in manure" (sect. 4.3.4); the regions relaxed to the EU-average cut were infeasible
"mainly due to the fact that those regions could export manure to neighbouring regions and the model cannot capture
this" (Table 7, note 3); capturing regional manure exports is listed as a future improvement (sect. 6), and CAPRI's
balance then lacked "data on manure imports and exports" (sect. 3). The manure trade module in the installation came
later. So the default stays without manure trade when validating against JRC121368; the market remains available
for runs with today's CAPRI.

**Baseline manure exports (settled, no change).** The baseline balance subtracts the export shares of CAPRI's
current 2030 reference (`manure_trade`: Brittany 23% of its manure, Weser-Ems 31%). With the market off they stay
fixed in baseline and scenario alike (`EnvironmentalModule`, export share applied to both), so the setup is
consistent: one baseline, and the scenario run with manure trade off (fixed shares, as JRC121368's CAPRI could not
adjust trade) or on (endogenous trade, today's CAPRI). Remaining difference from the report: tier bands are set on
a baseline surplus net of exports, so an exporting region near a band edge may sit one band lower than in JRC121368.

## Sprint 7a — CAPRI's two grassland activities (done, default)

**CAPRI's block.** Permanent grassland is two activities with their own yields, nutrient needs, costs and PMP
terms: extensive `GRAE` and intensive `GRAI` (2017 and 2030: half the grassland each, extensive yield 0.43 of the
intensive; Brittany 2030: 11.6 vs 26.8 t/ha, need 51 vs 139 kg N/ha).

**Now.** The model keeps one `GRAS` (their sum) and adds CAPRI's split as the area moved from intensive to extensive
grassland, z (`RegionalSupplyModel._grass_intensity_column`; GRAE = ½ GRAS + z): it enters the nitrogen balance
by the balance of a GRAE hectare minus a GRAI hectare, each with its own CAPRI removal, residues, fixation and its
share of the GRAS mineral rate by need (`EnvironmentalModule.grass_intensity_delta`, also used for the accounts, so
constraint and report agree: −69 kg N/ha in Brittany, −112 in Weser-Ems, −44 in Ireland); the grass fodder balance
by the yield difference; the manure-within-need row by the mineral-rate difference; 0 ≤ GRAE, GRAI; PMP cost
(q_GRAE + q_GRAI) z²/2 from CAPRI's own `p_pmpQuadTechn` (183 regions; the rest, country median of q × area —
REGISTERED), linear term calibrated on the base duals so the base split is optimal (base z ≤ 0.02 kha). Data:
`capri_data/2017/supply/grass_intensity.csv` (`tools/build/build_grass_intensity.py`). The parametrisation keeps GRAS as
the land and fodder activity everywhere else (feed, land types, prices, premiums); it is CAPRI's two activities
with grassland area held, which is the margin that matters. Fertiliser N₂O follows the shift.

**Results (2030 Farm-to-Fork):**

| Run | Gap | Area in use | Grassland | N price median / p75 / p90 (€/kg) | Pigs | Pork / poultry price | Converged |
|---|---|---|---|---|---|---|---|
| default, before | 6.71 | −7.5% | −17.3% | 10.5 / 20.8 / 33.9 | −26.7 | +47.5 / +49.0 | 12 it. |
| **default, with GRAE/GRAI** | **6.33** | −2.9% | −5.1% | 6.1 / 16.6 / 27.9 | −24.1 | +35.0 / +37.8 | 10 it. |
| CAPRI's land rules, before | 21.50 | — | — | — | −41.1 | +138 / +133 | no |
| CAPRI's land rules, with GRAE/GRAI | 7.66 | +3.9% | +4.6% | 10.2 / 30.4 / 89.1 | −29.9 | +68.5 / +74.9 | 12 it. |
| CAPRI | | +3% | | | −14.5 | +43 / +18 | |

Extensification is taken up to its bound wherever the nitrogen price is high (Weser-Ems, Ireland: all grassland
extensive). With it the default idles far less land and Weser-Ems' price falls from €36 to €22/kg (pigs −28 → −15%).
With CAPRI's land rules the model now converges, holds farmland (+3.9% against CAPRI's +3%) and matches the N
surplus (−33.0), fertiliser N₂O (−39.6), enteric CH₄ (−14.3) and vegetables (−12.0); two regions remain extreme —
Brittany (€298/kg) and Lombardy (€130/kg), where pigs and poultry disappear and suckler cows rise — and they carry
the pork and poultry prices. Their farmland is mostly arable fodder (temporary grass `OFOD`, silage maize), which
has no intensity choice in CAPRI either. Land rules stay off by default until those two regions are understood.

## Diagnosis: where the regional cut comes from (October 2026)

`tools/check/diag_region_balance.py RUN.pkl` splits each region's surplus change into its balance items. 2030
Farm-to-Fork, default model (kt N, scenario − baseline):

| Region | N price €/kg | Area in use (kha) | Mineral | Manure | Fixation | Deposition | Uptake | Surplus | Dairy | Pigs (fattening) |
|---|---|---|---|---|---|---|---|---|---|---|
| Brittany (FRH0) | 32 | 1,687 → 769 | −70 | −153 | −19 | −22 | **−176** | −172 | −30% | −65% |
| Weser-Ems (DE94) | 36 | 898 → 647 | −42 | −35 | −3 | −2 | −59 | −51 | −3% | −28% |
| Lombardy (ITC4) | 35 | 992 → 513 | −16 | −153 | −9 | −5 | −79 | −137 | −51% | −86% |

**Idling land works against the target.** Brittany's base balance matches CAPRI's (surplus 304 vs 302 kt; mineral
71 vs 78; removal 297 vs 294). Under the target the model idles 54% of Brittany's farmland, mostly grassland
(EU: grassland −8.7 Mha, −17%; other fodder −3 Mha). Each idled hectare takes its N removal with it: uptake falls by
176 kt, as much as the whole surplus cut, so inputs must fall by 264 kt — half of it only to replace lost removal.
That is what drives herds and the nitrogen price up. In the linear balance every crop hectare carries a positive
unit surplus (wheat 98, grass 88 kg N/ha in Brittany: its need-based mineral, deposition and residues over its
removal), so idling looks like abatement at the margin; it is, as long as the mineral-N floor does not bind, and it
removes deposition that in reality still falls on idle land.

**With CAPRI's land rules the model breaks the other way** (`--land-no-slack --surplus-current-ha`, not converged in
25 iterations): grassland must stay in use and its fixed grass yield must be eaten, so in Brittany suckler cows rise
+306% and sheep +197% while dairy falls 92% and all pigs and poultry disappear, at €430/kg N; EU beef animals −1%
(CAPRI −18%), sheep +22% (−9.5%), pork price +138% (+43%); gap 21.5.

**What CAPRI has that the model lacks: two grassland intensities.** CAPRI's grass is two activities with their own
PMP terms, extensive `GRAE` and intensive `GRAI` (Brittany, 2030 reference: 65 kha each; yield 11.6 vs 26.8 t,
mineral need 51 vs 139 kg N/ha, output €67 vs €157 per ha). Under a nitrogen price CAPRI can move grassland to the
extensive activity: less N per hectare, less fodder to be eaten (so ruminants can fall), land and removal kept. The
model has one `GRAS` with a fixed yield, so its only margins are idling grassland (default) or feeding it to more
ruminants (CAPRI's land rules). Earlier the split was judged minor because moving a hectare lowers mineral N and
removal by about the same amount; that missed its role in the fodder balance and the land balance. Data: res_17
(GRAE/GRAI LEVL, YILD, NITF, TOIN, MREV, PRME per region), the 2030 reference, CAPRI's elasticities.
**Done as Sprint 7a** (above); CAPRI's land rules now converge with it.

## Sprint 6a — CAPRI's 2030 prices in the baseline (done, default)

**CAPRI's block.** CAPRI's 2030 reference is in current prices: every non-agricultural input (fuel, electricity,
fertilisers, seed, plant protection, repairs, services) moves by one index, 1.277 in every member state;
agricultural outputs move by their own projected prices; CAP payments are nominal (and fall: soft wheat in
Brittany €288 → €226 per ha, grass €381 → €232).

**Before.** The 2030 trajectory scaled yields and herds only: the baseline ran at 2017 prices and premiums.

**Now** (`tools/build/build_price_trajectory_2030.py` → `capri_data/trajectories/capri_price_ratios_2030.csv`,
`capri_cap_premium_2030.csv`, `capri_livestock_premium_ratio_2030.csv`; applied by
`capri_mod/projection/prices.py`, on in `tools/run/run_f2f_2030.py`, `--base-prices` to switch off). The model stays in
2017 money: each product's CAPRI 2030/2017 unit-value ratio over the input index (median member state: pork 1.19,
cow milk 1.19, beef 1.03, eggs 0.97, poultry 0.85, sheep meat 1.00, piglets 1.16, wheat 1.07, maize 0.95, barley 0.96,
rapeseed 1.12, pulses 1.10, sugar beet 0.81) applied to crop producer prices, to livestock final-product values by
market (and sheep milk), to young animals sold and bought (and the young-animal market values), and to purchased
feed cereals; premiums are CAPRI's 2030 PRME in 2017 money. Input costs stay at 2017 values, as CAPRI moves them
with the index only.

**Not covered.** Fodder values (not marketed; shadow prices) and oilcake prices (CAPRI's 2017 results carry no
oilcake unit value comparable with 2030) stay at base; the market module keeps its 2017 base levels and passes
relative price changes, as before; the elasticity product-share weighting still reads 2017 values.

**Results (full EU, 2030 Farm-to-Fork, converged in 11 iterations):** average gap 6.91 → 6.66. Pork price +58.4 →
+47.3% (CAPRI +43), pigs −28.5 → −26.8% (−14.5), oilseed production −22.0 → −21.2%; poultry price +37.7 → +48.8%
(CAPRI +18) — poultry's real price falls 15% in CAPRI's 2030, so the same cost increase is a larger share of it,
and poultry was already the furthest from CAPRI. **Nitrogen prices do not move** (median €10.5/kg N, a quarter
of regions above €21; Brittany €32, Weser-Ems €42) and the area farmed still falls 14.4%. The price level explains
part of the pork gap, not the nitrogen-price failure: that needs the term-by-term check of nitrogen costs against
CAPRI's reference (next).

**Source check (CAPRI's own 2030 baseline, `results/baseline`).** The reference run's 2030 output prices equal the
unit values CAPRI's market model is calibrated to for 2030 (`data_uvag1730defaulta`, `p_uvagStore`): ratio 1.000
for every traded product, member state by member state; only inputs differ, by exactly the 1.277 index CAPRI applies
in the supply models. So the prices are CAPRI's baseline, whichever file they are read from. Premiums are not in the
trend projection (`trends_1730`, DATA2); CAPRI sets them in its policy module, so the reference run is their source.
Oilcake prices now follow the market baseline's producer prices at its 2017 and 2030 points (`data_market_1730defaulta`,
PPRI BAS/CAL; median real ratio soya cake 1.15, rape cake 1.20, sunflower cake 0.91): gap 6.66 → 6.68, no visible effect.
Extracts: `capri_data/sources/capri_baseline/capri_uvag_store_1730.csv`, `capri_market_prices_1730.csv`.

**Technologies in CAPRI cut the surplus little.** With every technology at its maximum (`_max` against `_ini`), CAPRI's
gross N surplus falls 4.1% in the EU (Brittany 14%, Weser-Ems 18%, Denmark 5%, Dutch regions 1–2%): mineral N −15%,
gaseous losses −32%, but ammonia kept in the manure stays in the soil balance. So technologies are not what makes
the −33.5% target cheap in CAPRI either; the difference with the model must be on the crop and land side (CAPRI keeps
its land farmed — +3% — and its crop production falls 15%; the model idles 14% of its land and crops fall 21–23%).

## Evidence from CAPRI's Farm-to-Fork reference (`refpol_endotech_all_ini` and `_max`)

CAPRI's Farm-to-Fork run itself is not in the project lead's installation; its reference is. `…endotech_all_ini`
is the Green Deal reference with mitigation technologies at their calibrated shares (the reference JRC121368's
scenarios start from), `…_max` the same with every technology at its maximum. Both are full regional result sets
including CAPRI's per-activity marginal decomposition (`reports/margcr.gms`: D_O, D_FEED, D_YANI, D_NUTNED,
D_OBJC, D_PREM, D_PMPL, D_PMPF, summing to D_PROV ≈ 0). Extracted by `tools/build/extract_capri_marginal_terms.py` to
`capri_data/validation/greendeal_2030/capri_marginal_terms_{ini,max}_2030.csv` and `capri_unit_values_{ini,max}_2030.csv`.

**A fattening pig in Brittany, CAPRI 2030 reference (€ per head):** output 200.3, feed −85.4, piglet −34.8, fixed
costs −9.8, manure nutrients +8.3, PMP −86.7 / +9.1 (feed), premium 0.1; sum 0.97.

**Pig supply curvature is not the cause.** From `_ini` to `_max` Brittany's fattening pigs rise 3.3% while their
PMP term moves by €7.0 per head: CAPRI's slope is about €2.2 per head per 1% of the herd (2030 prices). The model's
own slope is about €1.9 per CAPRI head (3.8 per model place, 2017 prices) — the same order, slightly stiffer in
real terms. So the same nitrogen cost per pig moves the herd about as much in both models; the pig overshoot comes
from the nitrogen price the model reaches, as diagnosed above.

**Found: the model's 2030 baseline keeps 2017 prices.** The 2030 trajectory (`captrd_2030.json`) scales yields and
herds only. CAPRI's 2030 reference is in current prices with relative changes (median member state, 2030/2017
`UVAG`): pork 1.51, cow milk 1.52, beef 1.31, eggs 1.24, poultry 1.09, wheat 1.37, barley 1.23, maize 1.22, rapeseed
1.43, pulses 1.41, sugar beet 1.04, mineral N 1.28, piglets 1.48. Against mineral fertiliser, pork and milk are
about 18% dearer in CAPRI's 2030 than in the model's, poultry and sugar beet cheaper. A pig earns more per kg of N in
CAPRI, so pigs are a dearer way to meet a nitrogen target there. This is part of the pig gap, not all of it (a
fattening pig's margin before PMP is €70 per head in CAPRI 2030 against about €20 in the model). CAPRI's own
baseline carries these prices; the model now does too (Sprint 6a above).

## Sprint 5 — CAPRI's pig activities and the piglet market (done, default)

**CAPRI's block.** Two pig activities: sows (`SOWS`, 43 kg N, 24 piglets out) and fattening pigs (`PIGF`, 8 kg
N, one piglet in), linked by the young-animal balance `INPANI_` for piglets (`YPIG` out, `IPIG` in) cleared on a
market, as for calves and young cattle.

**Before.** One `PIGS` activity per region (all pigs); a high nitrogen price could only cut whole pig chains.

**Now.** `PIGS` = sows (Eurostat breeding sows), `PIGF` = all other pigs. Every pig coefficient — output, market
revenue, total inputs and output, manure N, feed (cereals, protein, energy), premiums, rations, NH₃ factors,
ammonia technologies, young animals, fodder — is rebuilt from CAPRI's `res_17*` per activity
(`tools/build_pig_split.py`); piglets clear on the young-animal market; CAPRI's sow/fattener supply elasticities
and the piglet elasticity (`YPIG`) are wired; sows may feed up to 30% protein feed (CAPRI), other monogastrics 20%.

**Found on the way: what a meat price moves.** The model moved CAPRI's market revenue `MREV` with the product
price. `MREV`'s content differs by activity in CAPRI: for sows it is piglet sales (DE94: 24.0 × €25.43 = €610.9 =
`MREV`), for raised calves (`CAMR`, `CAFR`) and replacement heifers (`HEIR`) it is their young-animal sales (DEA2:
623.7 and 1,071.4, each equal to the young animal's `UVAG`), for suckler cows a quarter of their beef value. So a
pork price moved sows like fatteners (elasticity 0.55–0.63; now 0.10–0.12), the beef price moved calves' and
heifers' young-animal sales a second time (they are also priced by the young-animal markets), and suckler cows
saw a third of their beef price change. Now a price change moves revenue by quantity × price change, product by
product, from CAPRI's final-product quantities × `UVAG` (`livestock_product_value_by_market_coef.csv`: a dairy
cow's milk with the milk price, her cull-cow beef with the beef price). The same value share replaces `MREV` in
the livestock elasticity weighting. Sheep and goat milk (42% of the median sheep product value) has no market in
the model and its value does not move.

**Results (full EU, 2030 Farm-to-Fork; all converged in 12 iterations):**

| Run | Pigs | Pork price | Beef animals | Beef production | Beef price | Sheep | Gap |
|---|---|---|---|---|---|---|---|
| before (one pig activity) | −27.9 | +55.6 | −14.0 | −12.5 | +24.3 | −16.9 | 6.75 |
| pig split | −28.9 | +60.9 | −13.1 | −13.3 | +26.3 | −16.9 | 7.02 |
| + product values (default) | −28.5 | +58.4 | −14.5 | −14.4 | +29.5 | −16.0 | 6.91 |
| CAPRI | −14.5 | +43 | −18 | −14 | +24 | −9.5 | |

**What the split shows.** The hoped-for channel — high-price regions shed sows and buy piglets — does not occur:
sows and fatteners fall together (EU −29.7% and −28.8%; Brittany −70% and −72%, Lombardy −71% and −95%, Weser-Ems
−36% and −31%), and the piglet price rises 37%. A fattening place carries about 8 kg N a year, so at Brittany's
€20/kg N it costs more in nitrogen than its margin even with cheap piglets. The split is faithful and stays; it
confirms that the pig gap is the level of the regional nitrogen prices, not the pig structure.

## Sprint 4 — feeding inside the supply models (switched on)

The conic regional model with CAPRI's feed block (`REQSN_`, `FEDUSE_`, feed PMP, fodder at its shadow value,
enteric methane from the feed mix) was built in October and left off. With Sprints 1–2 in place it now
converges and fits better than the separate ration model: 12 iterations, average gap 7.69 → 6.73 (sheep −16.7%
vs −20.7%, pork price +55.6 vs +60.3%, beef price +24.4% vs +26.9%; CAPRI −9.5, +43, +24). It is the default.

## Channels examined while waiting for CAPRI's Farm-to-Fork results

- **Intensive vs extensive grassland (GRAI/GRAE).** CAPRI's 2030 reference splits every region's grass 50/50
  (JRC96482: "arbitrarily set at 50%"). Moving a hectare from intensive to extensive lowers mineral N and
  removal by about the same amount (Ireland: need 345 vs 122 kg N/ha), so it barely moves the gross balance:
  not a cheap channel for the surplus target. Not pursued.
- **Low-protein feeding (`LowNFeed`, active in CAPRI's Green Deal runs).** CAPRI's own maximum run cuts
  excretion by 3% for fattening pigs in Düsseldorf (`p_animReqCorrFac1`: protein 15% above requirement) and
  0.5% for dairy cows. Data exist (the uploaded `animReq_*` files, the maximum run); the effect on herds is
  small. Kept for Sprint 7.
- **Fertiliser technologies.** Adoption (precision farming 26% vs CAPRI's 35%, inhibitors 6% vs 18%) stops
  at CAPRI's over-fertilisation limit (`Tot_MitFert_`), not at cost: at €20/kg N an option is worth far more
  than its €300 per tonne of need. Faithful; the gap with Table 17 depends on CAPRI's regional factors.
- **Pig activities and the piglet market.** Done as Sprint 5 (above): faithful, but sows and fatteners fall
  together, so it does not relieve the pig regions.

## External check: the base balance against Eurostat (aei_pr_gnb, 2017)

`tools/check/validate_gnb_eurostat.py` (data: `capri_data/sources/eurostat/aei_pr_gnb_nitrogen.csv`, supplied by the
project lead) compares the model's base-year balance with Eurostat's by member state, 20 countries:

| Component | Model | Eurostat | Ratio |
|---|---|---|---|
| Mineral fertiliser | 9,684 kt | 9,824 kt | 0.99 |
| Manure | 8,669 kt | 7,631 kt | 1.14 |
| of which pigs | 2,180 kt | 1,241 kt | 1.76 |
| Biological fixation | 1,514 kt | 1,256 kt | 1.20 |
| Deposition | 1,687 kt | 1,458 kt | 1.16 |

Surplus per ha across countries: correlation 0.85, the model higher (France 90 vs 35, Ireland 142 vs 48,
Netherlands 352 vs 184 kg/ha) because CAPRI's balance counts crop residues on both sides and uses its own
coefficients. Pig manure is CAPRI's: the model reproduces CAPRI's 2017 regional totals (Germany 470 vs 471 kt,
France 268 vs 268, the Netherlands 168 vs 168). JRC96482 found the same (Table 4.5, Annexes 5–9): "the CAPRI
coefficient for N excretion by fattening pigs was higher than the coefficient values of the country and those
found in the literature" (Germany: +63% for fattening pigs). CAPRI's Farm-to-Fork run used the same
coefficients, so this does not explain the gap to JRC121368's pig result; it does mean that pigs carry more of
any nitrogen target in CAPRI-based models than national inventories would put on them. Kept as CAPRI has it.

## Sprint 3 — CAPRI's land rules (implemented, not default)

**CAPRI's block.** `LandBalNoSlak_`: the crops on each land type equal the land type's area (no idle land);
the land market moves land between agriculture, forest and other land at CAPRI's transformation costs with the
region's total area fixed; `e_SURTOTHa`: the surplus target is per hectare of land in use.

**Three defects found and fixed in the model's land block:**

1. *No-idle-land rows held at the wrong level.* The equality was set at land *availability*, but the model's
   land data carry idle land at base (CAPRI's do not), so the base itself had to fill or release it and the 2030
   baseline never settled. Now: crops − land = base crops − base land (capped at the row's limit — base crops
   exceed Brittany's land data by 0.002 kha of rounding, which made the pair of rows infeasible and sent every
   solve to a fallback without the land market).
2. *Land could vanish.* Total land was an upper bound, so under the nitrogen target Brittany's land types fell
   from 2,328 to 1,495 kha, forest included. Total land is now conserved: land leaving farming goes to forest
   and other land. (Default results unchanged: gap 6.73 → 6.75.)
3. *Two land-supply mechanisms.* The rent-elasticity expansion ran on top of the land market. With no idle land
   it no longer moved the solution while its target kept moving (land updates of 0.3–0.6 for 25 iterations);
   with the land market solving a region it is now switched off there.

**Results (full EU, 2030 Farm-to-Fork):**

| Run | Area farmed | N price median / p75 (€/kg) | Pigs | Beef animals | Sheep | Pork price | Converged |
|---|---|---|---|---|---|---|---|
| default (idle land allowed, base ha) | −14.4% | 8.5 / 21 | −27.9 | −14.0 | −16.9 | +56% | yes |
| no idle land | −14.4% | 19.8 / 51 | −40.0 | −1.6 | +8.5 | +138% | yes |
| no idle land + per current ha (CAPRI) | +0.1% | 27.9 / 102 | −43.0 | +12.5 | +4.4 | — | no |

With CAPRI's rules the area farmed holds (+0.1%, CAPRI +3%), but the nitrogen price doubles to quadruples:
grassland cannot be released (no idle land, no grassland conversion), so ruminants keep grazing it and the cut
falls on pigs and poultry, which use no land. CAPRI meets the same targets under the same rules with pigs −14.5%
and beef −18%, so the model still lacks whatever makes abatement cheap in CAPRI's livestock regions; adding
CAPRI's land rules makes that gap larger, not smaller. The rules stay available (`--land-no-slack`,
`--surplus-current-ha`) and off by default until that is found — which needs CAPRI's own Farm-to-Fork results.

## Market structure steps (18 October 2026, docs/archive/MARKET_STRUCTURE_PLAN.md)

| Step | Status | Farm-to-Fork gap | Green Deal |
|---|---|---|---|
| 1 market supply recalibration (Hessian) | option, off (no speed gain) | 4.58 -> 4.48 with it | not run |
| 2 CAPRI's GL food demand, commitments re-fitted | on | 4.58 -> 4.22 | unconverged (K37, fixed 19 Oct) |
| 3 CAPRI's two EU trade blocks | option, off | 4.22 -> 4.65 | unconverged (K37), gap 22.98 -> 22.17 |
| 19 Oct: K37, processing (ProcNQ_), fish/coffee/tea/cocoa, legacy base retired | on | 4.22 -> 4.44 (blocks 4.91) | converged 30 it., gap 22.48 (blocks 42 it., 22.13) |

## The regional supply model in CAPRI's own NLP form (20 October 2026: option, not default)

The regional supply models written in CAPRI's equations block by block and solved with IPOPT
(`CAPRIModel.supply_form = "nlp"`, `run_f2f_2030.py --supply-form nlp`; docs/NLP_PORT_DESIGN.md, KNOWN_ISSUES K50):
feeding, NUTNED_ for N, P2O5, K2O with the inner fertiliser model inside, CAP greening, the Green Deal's caps and
organic target as CAPRI's regulations, the options with the loss cascade, the emission tax, LUC transitions.
Calibrated so the base is a first-order point; the baseline reproduces the base exactly.

What the coupling exercise taught: the first Farm-to-Fork runs (deviation 15.4) looked like a nitrogen target that
CAPRI's equations make far costlier; three port errors were behind it (crop need = the group's need spread by area,
the grassland split column outside NUTNED_, split columns uncalibrated). Fixed, Farm-to-Fork converges in 12
iterations, 22 min, deviation 5.6 (conic 4.4): herds fall a little more, crops a little less, fertiliser N2O
-34% instead of -40% - NUTNED_ makes every crop group's need be met, where the conic form lets mineral N fall with the need met at a
fixed substitution rate. The Green Deal 2030 run does not settle yet (Finland's manure pool); the default stays conic.

## N loss cascade and storage options (20 October 2026)

- The ammonia options are coupled to the rest of the model through CAPRI's full N loss cascade (n_cascade.py): manure
  N kept (GasRunTot) in ManureNPK_ / the manure applied of both forms, NH3 in the ammonia accounts, N2O by stage in
  manure N2O. Checked against CAPRI's Green Deal reference run per head (1e-6). K51.
- endoLeach's concrete-storage options in the option set (ManStorCon, CovStorLowCon, AirPurCovLowC).
- NLP form: relaxations kept per scenario, warm starts capped; Green Deal 2030 converges (r43, 1,771 s).
- Next in the Green Deal block: anaerobic digestion (docs/AD_SPEC.md), the crop options' cascade terms (winter cover,
  tillage, fertiliser techniques), leaching, the Nitrates Directive minimum shares (nvz data in hand), then legume
  share, urea substitution, 3-NOP, linseed, SupplementPerc_.

## Couplings added on 20-21 October 2026 (the user's decisions on the review findings)

- **Winter cover with the supply model (NLP form):** the catch-crop share is a choice of the regional model
  (v_Miti(CATC, WinterCov) with CAPRI's cost curve). It is coupled to:
  - land, through the winterCover_ row;
  - the fertilisation block, through BioFix N in the residue pool (fertDistCres_);
  - the N-surplus row (e_BIOFIX);
  - the loss cascade's runoff, and so the manure N kept;
  - the emission tax (N2OCRO);
  - the accounts.
  See docs/WINTER_COVER.md.
- **Leaching:** coupled to the accounts and to the emission tax on mineral N (docs/N_CASCADE_SPEC.md).
- **Phosphate balance:** fed by the NLP form's P purchases and manure flows. In the conic form it is evaluated after
  the solve (docs/P_BALANCE.md).
- **Market:**
  - non-EU supply responds with CAPRI's region-specific own-price elasticities;
  - the crushing margin uses CAPRI's prices (seed at Armington, oil and cake at producer prices);
  - EU tariff-rate quota volumes are a scenario instrument on the bilateral market.
- **Norway as its own market region (NOR), as in CAPRI (RMSSUP):**
  - its supply models feed it and see its prices;
  - its feed bulks, young animals and dairy block are its own;
  - it is out of the EU aggregates and out of ROW (K56);
  - its prices are relaxed as a level of their own (not as a departure from the EU signal, which dragged them with
    every move of the EU signal), and the outer loop tests them with CAPRI's thresholds (products above 5 kt) and
    leaves Norway out from iteration 15, as CAPRI's price_forecast.gms does.
- **Supply/market fallback:** where IPOPT fails at the tiered N target, CAPRI's form is solved at JRC121368's relaxed
  target (36%, K57); where it fails otherwise, the region's solve is done in the conic form (feeding inside). Both are
  recorded. Farm-to-Fork 2030 (r65): every region in CAPRI's form, converged in 12 iterations, 30.5 min.
- **Not coupled, following CAPRI's settings:** the Nitrates Directive minimum shares (NDtech off in CAPRI's Green
  Deal runs).

## CAPRI's 2030 PMP terms, Norway's pigs, ammonia option costs (21 October 2026, night)

- **CAPRI's 2030 PMP terms** (K61, docs/PMP_CAPRI_2030.md): exported from the project lead's CAPRI installation
  (35 countries), converted with `tools/build/build_pmp_2030.py`, transferred to the model's crops and regions with
  `tools/build/build_pmp_capri_2030.py`; an option (`--pmp capri2030`), the default left to the project lead.
- **Norway's pigs** (K56): CAPRI's sow and fattening-pig herds of res_17NO, every per-head file rebuilt by its builder
  (`tools/build/build_norway_pigs.py`); Norway's base totals equal CAPRI's (pork 139.8 kt, manure N 9.18 kt).
- **Ammonia options' cost basis** (K63): per place of the model's heads (stock_factor / capri_level_ratio) and
  CAPRI's x 1000 for poultry's housing and air purification; at the baseline every non-poultry option within 0.04 of
  CAPRI's initial share (before up to 0.37).
- **Milk price step** (K62): CAPRI's step weights tried for the member states' milk prices and not kept.
- Results: CHANGELOG, 21 October 2026 (night).


## The recipe's land nest, Norway's pig census, ammonia options at base, 2030 curvature of the splits, absent activities (22 October 2026, afternoon)

- **Land-nest adjustment** (K61): CAPRI's p_landNestElasContrib in capri-mod's own PMP terms (`tools/build/build_pmp_recipe.py`
  step 2b), the land types' posterior elasticities from CAPRI's land matrices; with the 2017 inflation year found on
  the way, the recipe's terms within 5% of CAPRI's in 80.5% (2030) and 89.6% (2017) of pairs.
- **Norway's pigs** (K56): split of NO08 + NO09 + NO0A's herds into NO01, NO03, NO04, NO05 by Statistics Norway's 2017
  county census (the cattle-share proxy gone); the project lead's 2020 file as check.
- **Ammonia options** (K63): held at their base shares without a policy incentive on N, as CONOPT stays at CAPRI's
  calibrated point (costsavings0); every option at its initial share at the 2030 baseline.
- **Intensity splits** (K61): CAPRI's 2030 curvature of DCOL/DCOH, BULL/BULH, HEIL/HEIH, GRAE/GRAI at the 2030 market
  year with CAPRI's or the recipe's terms.
- **Activities without a base level produce nothing** (K64), as CAPRI has no variable for them: the solver's residue on
  them (|level| <= 1e-4) is reported as zero. Norway's regions had produced 6e-6 kt of tobacco from the solver's
  interior, which no trade flow could take; the market's residual had stalled at 3e-6 there. A bound row holding them
  at zero was tried first and dropped: it made the NLP fail or relax mineral caps in Greek and Bulgarian regions under
  Farm-to-Fork (82 minutes instead of 36).
- **K13**: `tools/gams/export_capmod_results.gms` for the project lead (CAPRI's Farm-to-Fork dairy market results).
- Results: CHANGELOG, 22 October 2026 (afternoon).


## Labour accounts, CAPRI's set-aside split, CAPRI's cattle activities (off: K65) (22 October 2026, evening)

- **Labour** as CAPRI's GROF LABT / LABF / LABP: an account after the solve. The base points match CAPRI's regional
  totals within 2%.
- **Set-aside**: the model's SETA reported as CAPRI's VSET and FALL. A common change is split by CAPRI's own PMP
  terms; premiums and labour follow per activity.
- **CAPRI's replacement heifers and calf activities with their own levels, and the young-animal markets per sex**:
  built, but in the Farm-to-Fork run the young-animal markets did not converge (four attempts, r89-r92). Switched off
  (`RegionalSupplyModel.use_cattle_member_splits`), with the per-sex data kept beside the default files.
  - Next (K65): take the supply response for the price update from each solved regional model, including its
    binding constraints, instead of from the PMP terms alone.
- **Exact switch**: with the splits off, the model gives the afternoon's results to the last digit. One leak was
  found and closed on the way: the greenhouse-gas cost derivatives looped over every split key.
- Results: CHANGELOG, 22 October 2026 (evening).


## Breeding cap, oilseed codes, young-animal response, tolerances (23 October 2026, night)

- **Breeding options** (K67): CAPRI's MaxShare 0.002 (breeding.gms l. 65-77) applied through the endotech setting
  fixGenetToIni. Higher ruminant efficiency falls from 79% to 0.2%, and higher milk yield to 0. Mean deviation from
  JRC121368: 4.97 (was 4.62); Table 17's genomics shares came from an earlier CAPRI version.
- **Farmland under the per-hectare N target** (K66, open): CAPRI's own mechanism; EU UAA +5.5% against CAPRI's +3%.
  Forest is converted where the target binds at extreme prices.
- **Young-animal markets per sex** (K65): each region's response from its solved NLP (KKT sensitivity). Validated, but
  the Farm-to-Fork run with the member splits still does not converge (male calves above 6 x base, female below
  zero). Off by default.
- **Oilseed codes** aligned with CAPRI's (RAPC/SUNC/SOYC, RAPO/SUNO/SOYO); **convergence tolerances** in the parameter
  file.
- Results: CHANGELOG, 23 October 2026 (night).


## Breeding calibration as CAPRI's, one settings file (23 October 2026, afternoon)

- **Animal options** (K67 F2-F4):
  - the PMP slope nets CAPRI's cost-saving drop between its ini and max calibration runs;
  - the cost floors are per animal place;
  - adoption is reported per eligible herd in livestock units.
  - Farm-to-Fork deviation from JRC121368: 4.89 (r99, CAPRI's terms) and 5.03 (r100, recipe).
- **Settings**: every coupling switch in one file, capri_mod/settings/defaults.toml. The projected 2030 model reads the
  same settings as the outer one, so nothing is carried by hand. The list CARRIED_SETTINGS that did it, and missed
  `food_demand_gl`, is gone.
- **Defaults that differ from CAPRI's**, to be switched one at a time (docs/DEPARTURES_FROM_CAPRI.md):
  - the EU trade blocks;
  - the market supply calibrated on the supply models;
  - fodder at its shadow price;
  - absent activities without a variable;
  - the cattle member splits.
- Results: CHANGELOG, 23 October 2026 (afternoon).

