# Known issues and bugs (from October 2026)

Found by running the model, its tests and the NLP check (`tools/nlp_check`: the regional problems in CAPRI's original
form, solved with IPOPT). The tables give one line per issue; the details follow below, one section per issue: what
was found, where it acts, whether the tagged release 9t (`capri-mod-9t.zip`) carries it, and its status. 9t.1 is 9t
with every fix below except K5, which needs the prototype's model change.

The data sourcing registry's log of checks, fixes and decisions (201 entries, moved 29 October 2026) is in
[KNOWN_ISSUES_REGISTRY_LOG.md](KNOWN_ISSUES_REGISTRY_LOG.md), verbatim, with the triage of its open entries against
the code: they became K92-K96, joined K73, K80, K91, or were closed or historical.

## Open (12)

| # | Issue | Status |
|---|---|---|
| [K108](#k108) | Inputs from CAPRI's 2030 results in 2030 money in a model working in 2017 money | open: audit running (gate 11) |
| [K13](#k13) | Farm-to-Fork milk price | open: waiting for CAPRI's scenario results |
| [K29](#k29) | NL11 and NL13 meet the tiered N target only at corner solutions (Farm-to-Fork) | open: waiting for CAPRI's scenario results |
| [K47](#k47) | The cattle chain's equilibrium is sensitive to changes outside it | open |
| [K48](#k48) | Young-animal prices against CAPRI's own market run | open |
| [K65](#k65) | Cattle member splits and per-sex young-animal markets do not converge yet | open |
| [K66](#k66) | Farmland expands under the per-hectare N target more than in CAPRI | open: waiting for CAPRI's scenario results |
| [K77](#k77) | CAPRI's fertiliser-option curvature (S5) leaves the baseline's base shares | open |
| [K78](#k78) | Histosol fallowing under Farm-to-Fork far above JRC121368's figure | open: waiting for CAPRI's scenario results |
| [K79](#k79) | Member-state production that keeps moving between iterations | open |
| [K92](#k92) | Farm-to-Fork changes furthest from JRC121368, besides the milk price | open: waiting for CAPRI's scenario results |
| [K93](#k93) | CAPRI mitigation options not built; documents disagree on which are in | open |

## Resolved (96)

| # | Issue | Status |
|---|---|---|
| [K107](#k107) | The regional model's tax on mineral N took IPCC's factors, the accounts CAPRI's MITERRA fractions | fixed (31 October 2026) |
| [K10](#k10) | Sub-sets of regions do not converge | resolved by K83 (31 October 2026) |
| [K83](#k83) | A one-region Farm-to-Fork run's market diverges in its second step | fixed (31 October 2026; gate pending) |
| [K80](#k80) | The same run repeated from a warm start differs by up to 3e-5 relative in small cereal activities | fixed (30 October 2026; gate pending) |
| [K89](#k89) | Failing regional solves take most of IPOPT's time | fixed (measured 30 October 2026) |
| [K74](#k74) | Supply: differences from CAPRI that no register listed | fixed (batch 8 gate) |
| [K105](#k105) | Numbers in the model's code to check, register or move to the settings | fixed (batch 8 gate) |
| [K106](#k106) | The market's base supply of crushed and biofuel products was not CAPRI's production of the market year | fixed |
| [K103](#k103) | Data files without a known origin or read by no code (data declarations) | fixed: removed, or given a builder |
| [K104](#k104) | The payments report's area left fallow out of CAPRI's UAAR | fixed |
| [K73](#k73) | Market: differences from CAPRI that no register listed | fixed (batch 6 gate) |
| [K101](#k101) | Model inputs without a builder (census of a run's reads) | fixed (batch 6 gate) |
| [K1](#k1) | Ammonia loss cascade linearised without its value | fixed |
| [K2](#k2) | Quadratic cost of ammonia options w times too small | fixed |
| [K3](#k3) | Silent fallback when the conic solve fails | fixed |
| [K4](#k4) | Clarabel cannot always finish a regional solve | fixed |
| [K5](#k5) | N-price fixed-point search alternates in IE05 | removed in the prototype; 9t.1 open |
| [K6](#k6) | Land-supply test too strict | fixed |
| [K7](#k7) | Expected warning flooded the test summary | fixed |
| [K8](#k8) | Emission-tax term of ammonia options | fixed |
| [K9](#k9) | Fertiliser allocation over crop groups had no solution in manure-saturated regions | fixed (floor) |
| [K11](#k11) | Three Romanian regions fell back under the emission tax | fixed |
| [K12](#k12) | 2030 livestock output per head stayed at 2017 | fixed |
| [K14](#k14) | Clarabel declares infeasibility that is not there | fixed |
| [K15](#k15) | Ill-conditioned regional problems | fixed |
| [K16](#k16) | Solver noise taken as EU supply | fixed |
| [K17](#k17) | Reported world raw milk price was the EU's | fixed |
| [K18](#k18) | Inhibitor relief missing on the mineral fertiliser cap row | fixed |
| [K19](#k19) | Grassland split counted with the wrong mineral N on the crop-need row | fixed |
| [K20](#k20) | The crop-need row's mineral N and the balance's differ slightly | no longer applies |
| [K21](#k21) | The manure spread over the crop groups missed CAPRI's housing and storage losses | fixed |
| [K22](#k22) | NL12's regional model has no solution at JRC121368's tiered N target; the warning said the wrong thing | fixed |
| [K23](#k23) | Vineyards were not carried between projection periods | fixed |
| [K24](#k24) | Food demand elasticities of the cereals were not CAPRI's | fixed |
| [K25](#k25) | EU import protection on rye, as measured from CAPRI, is 33.8% | explained (october 2026), no change |
| [K26](#k26) | Sheep and goat milk value counted twice in the 2030 price projection | fixed |
| [K27](#k27) | Activities could leave their calibration range entirely; Dutch N-target regions forced the least N-intensive grazer up (Farm-to-Fork) | fixed |
| [K28](#k28) | Three trajectory files were not reproduced by their builders | fixed |
| [K30](#k30) | Supply elasticities of permanent crops, vegetables, tobacco, textile crops and table olives were one EU-wide value per crop, while CAPRI's per-country values were in the data unused | fixed |
| [K31](#k31) | crop_cost_shares.csv: the plant-protection share did not follow its stated method for every crop, and the file had no builder | fixed |
| [K32](#k32) | Arable crops in many regions and the 14 Mha of other fodder were on literature elasticities although CAPRI's are in the data | fixed |
| [K33](#k33) | The legacy nitrate-limit instrument reads unsourced per-head N coefficients | retired |
| [K34](#k34) | The EU-wide crop producer prices (fallback) were of unrecorded source and far from CAPRI's | fixed |
| [K35](#k35) | Splitting CAPRI's textile crops by country left gaps | fixed |
| [K36](#k36) | Where the projected herds' fodder use was below the projected fodder output, the baseline missed the projected crop levels, and the difference fell on the most elastic crops | fixed |
| [K37](#k37) | Green Deal does not converge with CAPRI's GL food demand: the young-animal markets hit capri-mod's price bound | fixed |
| [K38](#k38) | The Green Deal runs used end-point targets in 2030 and a pesticide yield loss star 3.0 does not have | fixed (settings) |
| [K39](#k39) | CAPRI's processing functions divided by the wrong price of the non-agricultural good | fixed |
| [K40](#k40) | CAPRI's minimum mineral share (NUTMIN_) on together with the inner fertiliser distribution model | fixed |
| [K41](#k41) | The base check of CAPRI's crop-group allocation ran under the scenario's mineral fertiliser caps | fixed |
| [K42](#k42) | An EU ration was still chosen outside the supply models every iteration although feeding is inside them | fixed |
| [K43](#k43) | Non-EU feed demand: other vintage than the other use blocks, and no feed function for ROW, Korea, Morocco, New Zealand | fixed |
| [K44](#k44) | An inert income term and invented fallbacks in the market | fixed |
| [K46](#k46) | The fodder balance's right-hand side moved with the rations | fixed |
| [K49](#k49) | Diagnosis of the regions where CAPRI's crop-group allocation fails (20 October 2026): not the solver | resolved (NLP port) |
| [K50](#k50) | The regional supply model in CAPRI's own NLP form | default |
| [K51](#k51) | CAPRI's N loss cascade and the storage options of endoLeach | fixed |
| [K52](#k52) | Interface audit for the README rewrite | fixed |
| [K53](#k53) | NLP calibration carried across technology settings | fixed |
| [K54](#k54) | Market-side findings of the documentation review | fixed |
| [K55](#k55) | Supply-side findings of the documentation review | fixed |
| [K56](#k56) | Norway in the EU's market and totals | fixed |
| [K57](#k57) | Three Dutch regions not in CAPRI's form under Farm-to-Fork | fixed |
| [K58](#k58) | NLP form: degenerate multipliers in the calibration made the problem badly scaled and its solutions path-dependent | fixed |
| [K59](#k59) | Histosol fallowing never happened | fixed |
| [K60](#k60) | The grassland land row was not an equality | fixed |
| [K61](#k61) | PMP cross terms: structure not CAPRI's, and CAPRI's group curvature not at its size | structure fixed |
| [K62](#k62) | Member states' milk price step: CAPRI's step weights tried and not kept | superseded |
| [K63](#k63) | Ammonia options: costs per model head instead of per animal place, and poultry's costs per animal instead of per 1000 animals | fixed |
| [K64](#k64) | Market reported 'not converged' at a residual of about 1e-6 | fixed |
| [K67](#k67) | Breeding options without CAPRI's maximum share | fixed |
| [K68](#k68) | A bare SupplyModule.run did not reproduce the base | fixed |
| [K69](#k69) | Activities with no base level entered freely, and the Farm-to-Fork 2030 runs stopped converging | fixed |
| [K70](#k70) | Data files that no builder reproduces as they are | fixed |
| [K71](#k71) | More regions needed the Green Deal mineral-fertiliser caps relaxed | fixed |
| [K75](#k75) | The Farm-to-Fork runs with CAPRI's Green Deal input changes (S3/S4) did not converge: a warm-started NLP stuck at a worse point | fixed |
| [K76](#k76) | The market supply Hessian's measurement left the baseline's regional models in another state | fixed |
| [K81](#k81) | A plain regional solve after a shocked one kept the old price shock in the split and genetics columns | fixed |
| [K82](#k82) | The market supply Hessian read from its cache differed from the measured one by an ulp | fixed |
| [K84](#k84) | The landscape floor's fit ends on its last step | fixed (capri's form) |
| [K85](#k85) | Input costs of animals a region does not have were NaN in its net revenues | fixed |
| [K86](#k86) | Ammonia housing and storage options without their farm-size cost curves in Denmark, Lithuania and Croatia | fixed |
| [K87](#k87) | Builder outputs that do not follow from their builders (reproduction audit) | fixed |
| [K88](#k88) | Builders that still round the values they write | fixed |
| [K45](#k45) | Egypt's oilseed rows | fixed |
| [K94](#k94) | reconcile_base.py orphan; README's re-basing note points at a removed concordance | fixed |
| [K95](#k95) | The "12/12 against PMRK" market-price validation is a solver-consistency check | fixed |
| [K96](#k96) | Documents and one constant still describe removed mechanisms | fixed |
| [K91](#k91) | CAPRI's trend projection (captrd_2030.json) had no builder | fixed |
| [K90](#k90) | The wheat market's world price was CAPRI's soft-wheat price, not its wheat product's | fixed |
| [K72](#k72) | Inputs without a builder (armington_params.csv and the livestock producer prices removed) | fixed |
| [K97](#k97) | NaN in the crop-diversification row during Green Deal solves | fixed |
| [K98](#k98) | CAPRI's supply Hessian read as stored: half of the cross terms missed | fixed |
| [K99](#k99) | A feed table without builder (feed_requirements.csv) as the fallback of the feed costs and bulks | fixed |
| [K100](#k100) | A national nutrient table without builder (nutrient_coefs.csv) filled three crops' coefficients and fallow's mineral N | fixed |
| [K102](#k102) | Data files that no run and no builder reads (census) | fixed |

## Details

<a id="k1"></a>
### K1: Ammonia loss cascade linearised without its value

The N saved by housing / storage / spreading options entered the conic model as slope x (share − base share), slope at the previous solve's shares. CAPRI's cascade is bilinear in the manure-management and spreading shares (HOUSN_ → STORN_ → APPLN_), so the cross term was lost and the N saved overstated: at a converged Farm-to-Fork point CAPRI's exact N balance was violated by 8–365 t N (BE21, NL22, FRH0, IE05, DE94).

- **Effect:** DE94 pigs −2.2%, broilers −2.1%, N price 56.4 → 57.3 EUR/kg at CAPRI's exact optimum; EU indicators ≤ 0.3 points
- **In 9t:** yes
- **Status:** **fixed**: tangent at the previous solve's shares (value + slope), exact at a converged point; NLP check: violation → 0

<a id="k2"></a>
### K2: Quadratic cost of ammonia options w times too small

The cone giving the cost 0.5 slope M² / (w x) per place lacked the sub-activity weight w (U x / XM instead of U w x / XM), so in split activities (dairy DCOL/DCOH, pigs, poultry, w 0.05–0.8) adoption was too cheap.

- **Effect:** adoption of ammonia options too high where w < 1; NLP check: objective gap 1e-5–2e-4 to CAPRI's form, disappears with the fix
- **In 9t:** yes
- **Status:** **fixed** (feed_conic: U priced with 1 / w, see K11)

<a id="k3"></a>
### K3: Silent fallback when the conic solve fails

If Clarabel returns no solution, the region is solved again WITHOUT feeding inside and without technologies (a different model), with no warning and no count in the run's metadata.

- **Effect:** the region's result jumps between two models; found only through IE05 (K4)
- **In 9t:** yes
- **Status:** **fixed**: RuntimeWarning (region, status, iterations; shown in run logs, the runner silenced all warnings), `result.conic_failed`, and the run's `meta['conic_fallbacks']` lists the regions; Farm-to-Fork and Green Deal: none Superseded 26 October 2026: the conic form and its fallbacks were removed; where IPOPT still fails after the relaxations, the region's last IPOPT point is kept and recorded (`result.nlp_nonoptimal`, `metadata["nlp_fallback"]`, the run's `nlp_nonoptimal`), as CAPRI keeps a non-optimal solve (supply/simu_supply.gms, p_INFES).

<a id="k4"></a>
### K4: Clarabel cannot always finish a regional solve

to its tolerances: it stalls (InsufficientProgress) or stops at AlmostSolved, e.g. IE05 under Farm-to-Fork with the inhibitor on manure at its maximum and an N price ~330 EUR/kg. AlmostSolved points were up to 1.6e-3 (objective) short of the optimum in IE05, 1e-5–1e-4 in BE33, NL34, NL23, NL32, CY00 - enough to move IE05's herds ~0.5%.

- **Effect:** regional accuracy in a handful of manure-heavy regions with a binding N target; via K3, before, non-convergence
- **In 9t:** possible
- **Status:** **fixed**: (1) a stall is re-solved with more static regularisation; (2) prototype: what Clarabel still leaves unfinished is completed by IPOPT (CasADi) on the same convex problem from Clarabel's point, kept only if feasible and at least as good (`feed_conic._ipopt_polish`). Farm-to-Fork: 63 calls, 41 kept; EU indicators unchanged (< 0.05 points); run 349 → ~480 s. Green Deal: 9 calls, 7 kept. `CAPRI_POLISH_LOG=1` logs each call Superseded 26 October 2026: the conic form (Clarabel) was removed; Clarabel is used only for the manure-market pools.

<a id="k5"></a>
### K5: N-price fixed-point search alternates in IE05

between ~0 and ~335 EUR/kg N (two branches).

- **Effect:** Farm-to-Fork unconverged at 8 inner steps; raised to 16
- **In 9t:** yes
- **Status:** prototype: **removed** (the inhibitor is inside the model, no N-price search; docs/archive/PROTOTYPE_NI_INSIDE.md). 9t.1: still present (16 inner steps)

<a id="k6"></a>
### K6: Land-supply test too strict

`test_land_supply_converges_resets_and_is_inert_at_base` required successive runs to differ by < 1e-4, the land loop's own stopping tolerance; in one process after the whole suite SK01 alternates 0.06606 / 0.06618 (identical in 9t). 9t's "92 passing" came from the suite split in two parallel parts.

- **Effect:** test failure only
- **In 9t:** yes
- **Status:** **fixed** (5 x LAND_TOL; the swings it guards against were 0.045 / 0.09)

<a id="k7"></a>
### K7: Expected warning flooded the test summary

: 21 of 21 warnings were the model's "outer loop did NOT converge" from tests that run 1–2 market iterations on purpose.

- **Effect:** real warnings would have been hidden
- **In 9t:** yes
- **Status:** **fixed**: filtered for that message only (pyproject.toml)

<a id="k8"></a>
### K8: Emission-tax term of ammonia options

: the tax on the N they keep (indirect N2O of the NH3, soil N2O of the mineral N displaced) was priced as ret x (share − base share), K1's error.

- **Effect:** carbon-tax runs (the Green Deal has no emission tax)
- **In 9t:** yes
- **Status:** **fixed**: priced on the cascade's tangent, as the N row. NLP check under a 50 EUR/t tax (BE21, DE94, FRH0, NL22): conic = CAPRI's exact form within 1e-6. REGISTERED (not a bug): the options' manure N2O slope is taken at the base shares, like every emission coefficient of the tax (ghg_tax.ghg_coefficients)

<a id="k9"></a>
### K9: Fertiliser allocation over crop groups had no solution in manure-saturated regions

(8 in Farm-to-Fork). Cause found (October 2026): under the N target the regional model cut MINERAL N to zero and kept the manure - CAPRI forbids it: NUTMIN_ holds mineral N at p_minShareMinFert x each crop group's need (fert/fertpar.gms: 0.4; vegetables and perennials 0.5; maize 0.3; fodder maize 0.2; grass, other fodder 0.05; pulses 0; organic land 0), with a calibrated correction v_minShareMinFertCorr fixed in simulation. Since manure can be placed freely over the groups, the per-group floors add up to one regional condition on the crop-need row. Also found on the way: the row missed what else displaces mineral N inside the conic model (the ammonia options' N kept, the inhibitor's relief, the fertiliser technologies' mineral N, the nitrate additive's manure) and K19.

- **Effect:** herds (the N target now cuts more stock: sheep -10.3% vs -4.9%, CAPRI -9.5%), the fertiliser-distribution report
- **In 9t:** yes
- **Status:** **fixed (floor)**: CAPRI's floor on the crop-need row (capri_data/2017/environment/min_share_mineral_fert.csv), correction from the base alone (REGISTERED: one per region, CAPRI's is per crop group); every term that changes mineral N on the row. Allocation failures 8 -> 3. **Then (option 3, 16 October 2026): CAPRI's inner fertiliser distribution model inside the regional model** - where its crop-group allocation does not exist at the conic solution, the region is solved in CAPRI's coupled form (flows per group and source, NUTNED_, fertDistExcr_ and the inner model's first-order conditions e_focFertDist with CAPRI's gamma priors on the current group areas; capri_mod/supply/capri_nlp.py) with IPOPT, warm started from its previous coupled solution; elsewhere the conic solution already is CAPRI's optimum. Farm-to-Fork: FRI2 and IE05 solved in the coupled form, failures 3 -> 1. RO22 failed at its calibrated BASE - not a data mismatch, as first labelled, but K21. **Fixed (16 October 2026, later): CAPRI's priors.** FRI2's coupled form failed at every Green Deal iteration (Green Deal 30 min): the prior modes followed the CURRENT group areas, so groups shrinking to a few hectares (pulses, rapeseed) took their modes to zero and their first-order conditions became singular. CAPRI sets the modes once before the simulation (prep_sim.gms -> set_fert_priors.gms: prior per ha x the group's area at the starting point, fixed with UPDATE_FERTMAX_IN_STEPS off, the default) and bounds every flow within 0.001 and 1000 x its mode; now the same, in the coupled form, the existence check and the report. The regulations (beta densities) stay per ha of the current area (priModePerHa on, as CAPRI) Superseded 26 October 2026: the floor (NUTMIN_) and the conic form's crop-group check were removed with the conic form; the NLP form carries CAPRI's inner fertiliser model (K50), with NUTMIN_ off as in star 3.0 with that model.

<a id="k10"></a>
### K10: Sub-sets of regions do not converge

(young-animal markets thin with a handful of regions).

- **Effect:** diagnostic runs only
- **In 9t:** yes
- **Status:** **resolved by K83** (31 October 2026): a run on a subset now has the EU's other units in its market,
  supplied through their member states' market supply functions, so its markets clear: DE110000 alone converges
  (market in 15 and 8 steps, young-animal imbalance 0.0013), the mini-EU Farm-to-Fork run in 5 iterations. A subset run
  still simulates the policy in its own units only (as CAPRI with countries switched off), so its EU figures are not
  a full run's; tools/check/compare_runs.py says so for a subset run (K83)

<a id="k11"></a>
### K11: Three Romanian regions fell back under the emission tax

(RO12, RO22, RO42; carbon-tax scenario), found by K3's report: Clarabel declared their problem PrimalInfeasible after one iteration in every iteration of the scenario. Cause: K2's fix written as U w x / XM ≥ M² in the cone; the same problem with the weight on the cost (U priced with 1 / w) solves.

- **Effect:** those regions solved without feeding inside and technologies
- **In 9t:** no (K2's fix)
- **Status:** **fixed**: weight on the cost; same optimum as the cone form elsewhere (objective within 1e-8; FRH0, NL22, DE94)

<a id="k12"></a>
### K12: 2030 livestock output per head stayed at 2017

(found against the EU agricultural outlook 2020-2030). Since Sprint 9p the projection follows CAPRI's 2030 reference (capri_ref_2030.json), which reports dairy cows, heifers, bulls and calves per region only as intensity variants (DCOL/DCOH, HEIL/HEIH, BULL/BULH, CAMF/CAFF) and sheep and goats as milk (SHGM) and fattening (SHGF) activities: the model's DCOW, HFRS, BULL, CALV, SHGP got no yield factor, and suckler cows, heifers, laying hens, broilers, calves and sheep/goats no herd factor. 2030 dairy cows gave 2017 milk: 6.97 t/cow (CAPRI 7.79, outlook 8.30), EU cow milk 139.6 Mt (CAPRI 154.3, outlook 159.6); every run since 13 October. The baseline check compared herds, not output per head.

- **Effect:** baseline milk −10% against CAPRI; poultry −4.7%; Farm-to-Fork milk price +30.7 → +32.3 (CAPRI +1.5) once fixed
- **In 9t:** yes (and 9t.1)
- **Status:** **fixed** (prototype): yield factors from CAPRI's components, level-weighted, the same components in both years (dairy cows always: CAPRI's own DCOW YILD is beef per cow); sheep and goats' milk and meat each follow their own CAPRI yield (SHGP_MILK, SHGP_MEAT); herd aliases for the model's animal names. 2030 baseline: cow milk 157.2 Mt (CAPRI +1.9%), poultry +1.3%, eggs +2.0%, suckler cows +1.0%, sheep and goat meat +4.6% against CAPRI. Test: every livestock yield has a 2030 factor

<a id="k13"></a>
### K13: Farm-to-Fork milk price

+32% against CAPRI's +1.5% (JRC121368 Figure 7, raw milk supply -10%). Diagnosed (October 2026): the dairy block is CAPRI's - DairyNQ_, ProcMargM_, FatsProtBal_ per member state with the raw milk row active (YYY = the products solved), and p_hessNQDairy reproduces p_ElasDair element by element (DE, FR, IE, NL); food demand p_ElasDem, Armington rho1/rho2 and the extra-EU trade are CAPRI's. The market's derived demand for raw milk (tools/check/milk_shock_check.py: milk delivered -5% / -10%, all else at the baseline) is about -0.2: milk price +26% / +55%, butter +32%, whey +24%, cheese +17% at -10%. With CAPRI's own parameters a -10% milk supply cannot clear at +1.5%; the same holds in reverse for JRC121368's dairy net trade (+5% there, -36% here). No bug found in the block or the market; what differs in CAPRI's Farm-to-Fork run cannot be seen without its market results for dairy products (prices, balances). The CAPRI runs at hand (refpol endotech ini/max) were solved with the market fixed (identical dairy trade) and cannot show it. Also found: K17.

- **Effect:** Farm-to-Fork milk and dairy prices; the largest single gap to JRC121368
- **In 9t:** yes
- **Status:** **open, waiting for CAPRI's scenario results** (the project lead's decision, 29 October 2026: kept open with its reference). Needed: CAPRI's Farm-to-Fork 2030 market results for the dairy chain: per member state and EU the raw milk delivery and price, the fat and protein values, production, processing, food use, trade and Arm1 prices of butter, SMP, cheese, WMP, fresh milk products and whey (DATA rows PROD, PROC, HCON, IMPT, EXPT, PPRI, ARM1P of the CAPMOD result file); to be exported with tools/gams/export_capmod_results.gms (run on a CAPRI installation where the scenario was solved); the project lead's installation has none of them so far. Before: open: needs CAPRI's Farm-to-Fork dairy market results; model unchanged (no calibration to the figure). 18 October 2026: with CAPRI's GL food demand and processing functions +40.3% (r19). 22 October 2026: tools/gams/export_capmod_results.gms dumps every CAPMOD 2030 result file of a CAPRI installation (except the reference already in hand) for the project lead to run, if the Farm-to-Fork or Green Deal scenarios were run there

<a id="k14"></a>
### K14: Clarabel declares infeasibility that is not there

FI1C under the Green Deal (after K12): DualInfeasible after 5 iterations in every iteration of the scenario, so the region fell back to the model without technologies and the Green Deal run did not converge in 60 iterations. The same problem solves to a finite optimum with tighter infeasibility tolerances (1e-12), and IPOPT finds the same objective (−2.924756e8). K11's Romanian case solves the same way.

- **Effect:** non-convergence; one region on the fallback model
- **In 9t:** possible
- **Status:** **fixed**: a declared infeasibility is re-checked with tol_infeas 1e-12 before the fallback

<a id="k15"></a>
### K15: Ill-conditioned regional problems

(why Clarabel left solves AlmostSolved and IPOPT had to finish them, K4). Two causes found: (1) a placeholder nitrate row (999999 kg N/ha x UAA, right-hand side ~2e9 against ~3e5 at base) in every regional problem without a nitrate limit; (2) activities absent from the region at base (citrus, wine, maize ... in IE05) held at zero by PMP curvatures up to ~2e8 against a median ~1e3.

- **Effect:** IPOPT completion calls per Farm-to-Fork run 63 -> 30-39; run 525 -> ~420-440 s; results unchanged (indicators within 0.05)
- **In 9t:** yes (1); (2) not CAPRI's form
- **Status:** **fixed**: the nitrate row only with a nitrate limit; absent activities fixed at zero, as CAPRI's regional model has none (their levels were ~1e-6). Tried and dropped: objective scaling (worse), curvature-capped variable scaling (no gain). Remaining AlmostSolved solves are fewer and about half need nothing (IPOPT finds no better point)

<a id="k16"></a>
### K16: Solver noise taken as EU supply

`MarketModule.supply_response` replaced the EU's base supply of a product with the supply module's output whenever it was > 0. In a run on a subset of regions, a product none of them grows comes back as solver noise (~1e-15 kt after K15, ~1e-6 before) and wiped out the EU's supply: the market did not clear in 60 steps, EU prices ran to 1e7 and the next supply solve swung (emission-tax test, IE04: dairy cows 184 -> 715, suckler cows and sheep to zero). Found by the test suite after K15.

- **Effect:** subset runs (tests, regional studies); full-EU runs not affected
- **In 9t:** yes (same rule)
- **Status:** **fixed**: supply below 1 kg (1e-6 kt) counts as none

<a id="k17"></a>
### K17: Reported world raw milk price was the EU's

The world index of a product without bilateral trade is the first region's price ratio, and EU27 is the first region; the EU raw milk ratio was replaced by the dairy block's before the index was taken, so the reported world MILK price moved with the EU's (+32% in Farm-to-Fork). Reporting only: the price signal to farmers is premium x world = the dairy block's price either way.

- **Effect:** reported world MILK price
- **In 9t:** yes
- **Status:** **fixed**: world index taken before the EU's raw milk price is set

<a id="k18"></a>
### K18: Inhibitor relief missing on the mineral fertiliser cap row

The inhibitor on manure (NITR_INH) raises manure N's availability and so displaces mineral N (CAPRI NUTNED_: manure x (1 + share x NMAN)); in the conic model its relief was on the N balance row only, not on CAPRI's mineral fertiliser cap (mineRedu, Green Deal).

- **Effect:** Green Deal mineral N cap
- **In 9t:** no (prototype only: the inhibitor is inside the model since the prototype)
- **Status:** **fixed**

<a id="k19"></a>
### K19: Grassland split counted with the wrong mineral N on the crop-need row

Moving grassland from GRAI to GRAE changes the unit balance's mineral N by -39.9 t per 1000 ha in AT32 (the quantity every crop carries on the row and the accounts apply), the row took the plain fertiliser rate (-3.65). Under Farm-to-Fork AT32 moved 53 kha: the model saw mineral N at 805 t, the accounts -461 t (also PT30 -45, BE34 0).

- **Effect:** crop-need row, mineral N in manure-heavy grassland regions
- **In 9t:** yes
- **Status:** **fixed**

<a id="k20"></a>
### K20: The crop-need row's mineral N and the balance's differ slightly

DE11 under the Green Deal mineral reduction: mineral N read off the regional model's crop-need row (floor x areas - row) is 24,327 t, the reported balance's 24,322 t (+0.02%). Found when the coupled crop-group allocation (K9, option 3) first reported the allocation at the row's totals. Some adjustment the balance applies after the solve (manure-equivalent animal splits, relief, cover crops) enters the row with a slightly different coefficient - not yet traced.

- **Effect:** the crop-group allocation's existence check (made at the row's totals); not the reported indicators
- **In 9t:** yes (small)
- **Status:** **no longer applies** (checked 27 October 2026): in every EU solve the regional NLP drops the crop-need row and solves CAPRI's fertilisation block (NUTNED_, CapriRegionalNLP._fert_block; supply_module `drop = ["crop_need"]` wherever the region has CAPRI's EU fertilisation data), and the conic form with its crop-group allocation check was removed (26 October 2026); mineral N is reported from that block. The row remains only where CAPRI's fertilisation data are missing (outside the EU data), where no allocation is made

<a id="k21"></a>
### K21: The manure spread over the crop groups missed CAPRI's housing and storage losses

CAPRI's fertDistExcr_ distributes v_ManureNPK, the manure N left after the losses in housing and storage and net exports: EXCRET - MTRADE - GASANI - RUNANI, exact in all 268 regions of CAPRI's 2030 reference. The model took excreted N after trade (right for the gross balance, wrong here): 49% too much in the median region; RO22 14.7 kt against CAPRI's 0.44 kt (it exports two thirds and loses most of the rest), DE11 +54%, FRI2 +79%. Hence RO22's allocation failing at its base and, under the Farm-to-Fork N cut, the allocation not existing in FRI2 and IE05.

- **Effect:** crop-group allocation (existence, coupled form, report), the Green Deal mineral cap by crop group (set from the baseline allocation); not the balance
- **In 9t:** yes
- **Status:** **fixed**: n_manure_applied = excreted after trade - CAPRI's loss share per region and animal ((GASANI + RUNANI) / MANN, capri_data/2017/environment/manure_housing_losses_2030.csv, tools/build/build_manure_losses.py, which checks CAPRI's identity) x excretion, plus the N the ammonia options keep (per head at the last recorded solution). RO22 at base: 0.28 kt (CAPRI 0.53 kt at our areas); DE11, FRI2, IE05 within -13 to +14% of CAPRI's priors (our 2030 herds, not CAPRI's). REGISTERED: manure-equivalent animal shifts and endogenous manure trade change the manure spread without the loss share; the nitrate additive's extra excretion likewise **RO22 without manure trade (16-17 October 2026): fixed.** CAPRI's posterior comes from a run where RO22 exports two thirds of its manure and gives manure priors to 7 crop groups; the Farm-to-Fork run trades none (as JRC121368), so no allocation existed at its base. CAPRI recalibrates its priors at its baseline (fert/ferttrm_years.gms: blanket priors of a third of each group's need per source, at least 10% from manure and mineral for the permanent groups, half of grassland's mineral prior moved to manure, accuracy 2, residues 5; the posterior at the baseline's totals is the simulation prior, prep_sim.gms). The model now does the same where CAPRI's posterior has no allocation at the run's own base (InnerFertDist.calibrate; crop need per ha from CAPREG NITF; constants in model_parameters.csv), per manure-trade setting; RO22 then spreads manure on all 17 groups and its allocation exists in baseline and scenario. With manure trade CAPRI's posterior holds unchanged

<a id="k22"></a>
### K22: NL12's regional model has no solution at JRC121368's tiered N target; the warning said the wrong thing

Under Farm-to-Fork the full regional model (feeding, technologies, land rules) cannot reach NL12's tiered surplus target: removing the N row, or lifting any cap on the technology variables, makes it feasible - the target is beyond what every option at its maximum delivers with all land farmed. JRC121368 (sect. 4.3.4) set such regions' cut to the EU average, 36%, and the model does: the target is relaxed and the FULL model solved (shortfall 109 kg N/ha). But the tiered target was tried again at every iteration (about 12 failed solves per run since at least x13), each time warning 'region solved without feeding inside and technologies' - which was not what happened.

- **Effect:** run time, log
- **In 9t:** no (results were right)
- **Status:** **fixed**: once relaxed in a scenario (same target), the region starts from the relaxed target; the warning says what follows (relaxation or, failing it, the reduced model) and the run records which (n_target_relaxed, conic_failed). One warning per run instead of ~12

<a id="k23"></a>
### K23: Vineyards were not carried between projection periods

The projection layer's perennial list used CAPRI's vineyard code TWIN; the model's is WINE.

- **Effect:** multi-year projections only (vineyard area re-optimised each period); no single-year run
- **In 9t:** no
- **Status:** **fixed**: the list is the supply model's PERMANENT_LAND_CROPS; test test_projection_carries_permanent_crops

<a id="k24"></a>
### K24: Food demand elasticities of the cereals were not CAPRI's

The `eta` column of armington_params.csv (non-EU regions, and the EU row where no other source applied) was -0.2 for OCER, CORN, PARI, RYEM, OATS, -0.205 for BARL and -0.039 for SWHE, of unrecorded source; CAPRI's calibrated p_ElasDem (elas_2_1717defaulta) is about -0.5 for these cereals (wheat about -0.2 in the EU, -0.36 elsewhere).

- **Effect:** food part of cereal use responded less to price than in CAPRI; feed use (most of EU cereal use) goes through CAPRI's feed bulks and was not affected
- **In 9t:** yes
- **Status:** **fixed**: tools/build/build_demand_elas_capri.py writes CAPRI's p_ElasDem medians (EU member states for the EU row, the method of the existing oil and cake entries, reproduced as a check; CAPRI's non-EU regions for the others). Farm-to-Fork cereal price index +6.5 -> +6.2% (CAPRI +8), gap 4.50 -> 4.49; Green Deal within 0.2 points  Superseded 24 October 2026: the eta column and the EU override file are gone; demand follows CAPRI's Armington balance (K72, audit M2)

<a id="k25"></a>
### K25: EU import protection on rye, as measured from CAPRI, is 33.8%

The EU row of tariffs.csv is CAPRI's total ad-valorem equivalent ImportP / (Fob + TCost) - 1 (EU27yr19 <- NONEU, 2017). For rye CAPRI reports no applied tariff (TaAppl and TsAppl ~0) but an import price 34% above fob + transport; for oats 1.4%; for OCER 0. Kept as computed, with the same formula as every other EU row.

- **Effect:** EU base price level of rye 210 EUR/t (world 156.9 x 1.338); responses use price ratios, so the level acts through value weights and the EU Armington premium only. CAPRI's own 2030 EU rye market price is 104.9 EUR/t
- **In 9t:** n/a (new market)
- **Status:** **explained (October 2026), no change**: the aggregates' TsAppl is 0, but CAPRI's bilateral rows carry the EU's specific duty on rye, 94 EUR/t (TsAppl, the EU's MFN rye duty is 93 EUR/t), on Russia (320 kt; import price 53 EUR/t above fob plus transport) and other origins, while Ukraine (97 kt) enters at no wedge (preferential access). The 33.8% is that protection averaged over origins, not a calibration term. The model's bilateral flows carry it pair by pair in the per-tonne margin over fob (rye from Russia 58.9 EUR/t: transport 5.5 plus the duty's wedge 53.3); the EU row of tariffs.csv is the aggregate

<a id="k26"></a>
### K26: Sheep and goat milk value counted twice in the 2030 price projection

projection/prices.py moved each livestock product's value by its CAPRI price ratio per market column (sheep milk SHGP.MILK at the cow-milk ratio COMI), then added sheep milk again at the SGMI ratio (a term written before the market column existed).

- **Effect:** 2030 baseline output value of sheep and goats only (median change -2.8 EUR/head)
- **In 9t:** yes
- **Status:** **fixed** with the sheep and goat split: the market column SHGM.MILK takes the SGMI ratio, the second term is removed

<a id="k27"></a>
### K27: Activities could leave their calibration range entirely; Dutch N-target regions forced the least N-intensive grazer up (Farm-to-Fork)

In NL11, NL12, NL13, NL32 the tiered N target is near-infeasible; with CAPRI's fodder equality the grass still has to be eaten, so dairy cows were cut and the grazer with the least N per tonne of grass expanded far beyond its calibration: SHGP before the sheep split (NL32 71 -> 756 thousand head), SHGF after it (NL12 10 -> 2,923, dairy cows to 0; NL32 8 -> 889), about 260 kt more sheep meat, EU sheep meat price -16.6%. Cause: CAPRI bounds every endogenous activity at 0.1 to max(10 x, + 100) its simulation data level (supply/set_supply_bounds.gms, applied by prep_sim.gms); the model had no such bounds (923 region-activities fell below 0.1 x and 13 rose above the upper bound in that run).

- **Effect:** Farm-to-Fork: sheep and goat meat market, milk price, gap 4.53 -> 4.82; Green Deal less affected
- **In 9t:** yes
- **Status:** **fixed**: CAPRI's bounds in every regional model (RegionalSupplyModel.use_capri_activity_bounds; set-aside and fixed activities exempt as in CAPRI; the additive 100 converted from CAPRI's LEVL units to the model's herd units per region and animal, capri_level_ratio.csv: poultry, fattening sheep, bulls, heifers, calves and fattening pigs are counted differently in the two). NL12 and NL32 now prove infeasible at the tiered target and take JRC121368's relaxation (36%); NL12 keeps 268 of 300 thousand dairy cows. Second missing link found with it: CAPRI's lambs (YLAM from SHGM, ILAM into SHGF and SHGM's replacement), now a young-animal balance (tools/build/build_young_animals.py), so fattening sheep need lambs from breeding flocks. Farm-to-Fork: gap 4.82 -> 4.54, sheep and goats -9.5% (CAPRI -9.5%), EU sheep meat +2% and price -1.7% (before: +26%, -16.6%); Green Deal: gap 21.46 -> 21.90, sheep and goats -38.4%, meat prices 2-3 points higher. The remaining corner solutions in NL11, NL13 and IE05 are K29

<a id="k28"></a>
### K28: Three trajectory files were not reproduced by their builders

(1) tools/build/build_trajectory_capri_ref.py re-extracting its source dropped CAPRI's calves aggregate CACR (not in its keep list), so the calves' 2030 yield factor fell back to the components (77 regional entries); (2) capri_cap_premium_2030.csv was an older output of tools/build/build_price_trajectory_2030.py (192 regions, CAPRI's crop codes only), so 56 regions and the model's WINE, COTT, OFIB, OFOD, SETA kept their 2017 premiums in the 2030 baseline; (3) capri_ref_fodder_2030.csv: reported as differing, but the builder reproduces it exactly on a clean rerun (the earlier comparison was made while files were being rewritten).

- **Effect:** (1) none while the stored extract was kept; (2) 2030 baseline premiums of 56 regions and five crops (scenario changes moved by less than 0.05 points)
- **In 9t:** yes
- **Status:** **fixed**: CACR added to the keep list (the rebuilt extract and capri_ref_2030.json equal the stored ones exactly); the CAP premium file rebuilt (identical on every cell the old one had; 1,515 more premium cells applied)

<a id="k29"></a>
### K29: NL11 and NL13 meet the tiered N target only at corner solutions (Farm-to-Fork)

Both are feasible at JRC121368's tiered target (a 69-70% cut of CAPRI's baseline surplus, applied as a percentage to the model's own), so they are not relaxed, but only with N shadow prices of 0.2-2 million EUR per t N (elsewhere 10-50): in NL11 dairy cows, wheat, potatoes, sugar beet, pigs and poultry sit at CAPRI's lower bound (0.1 x), 113 of 163 thousand ha go to set-aside, bulls and fattening sheep at the upper bound; in NL13 milk sheep at the upper bound (x10), potatoes x5. IE05 (N price about 3,000) has its milk sheep at the lower bound and fattening sheep x8.2. JRC121368 relaxed the target "in a limited number of regions where the model is infeasible"; whether CAPRI found these two feasible, and how, cannot be checked without CAPRI's regional Farm-to-Fork results.

- **Effect:** Farm-to-Fork: Dutch and Irish livestock and crop mix; EU aggregates little (NL11 and NL13 hold 0.2% of EU farmland, with IE05 1.6%)
- **In 9t:** yes
- **Status:** **open, waiting for CAPRI's scenario results** (the project lead's decision, 29 October 2026: kept open with its reference). Needed: CAPRI's Farm-to-Fork 2030 regional results for NL11, NL13 and IE05: activity levels, the N surplus (SURTOT) and whether CAPRI's solve there was optimal (p_INFES); to be exported with tools/gams/export_capmod_results.gms (run on a CAPRI installation where the scenario was solved); the project lead's installation has none of them so far. Before: **open**: options (a) CAPRI's regional Farm-to-Fork results for NL11, NL13, IE05 to compare; (b) treat a region whose solution needs activities at CAPRI's bounds as infeasible and relax it (a departure: CAPRI's criterion is the solver's infeasibility)

<a id="k30"></a>
### K30: Supply elasticities of permanent crops, vegetables, tobacco, textile crops and table olives were one EU-wide value per crop, while CAPRI's per-country values were in the data unused

utils.calibrate_supply_elasticities held APPL 0.218, OFRU 0.189, CITR 0.184, TAGR 0.216, WINE 0.176, TOMA 0.668, OVEG 0.663 (CAPRI's calibrated values for Spain and Italy, per its comments), TOBA 0.213, OLIV 0.197; these crops are absent from both regional CAPRI sources the PMP reads. capri_own_price_elasticities.csv (CAPRI's calibrated p_ElasSupp per member state, 26 country groups) was loaded but read by no module. The hand-entered values match CAPRI except tobacco (CAPRI 0.44 in every member state).

- **Effect:** supply response of these crops; tobacco half CAPRI's
- **In 9t:** yes (tobacco)
- **Status:** **fixed**: capri_pmp.build_elasticity_table takes the member state's value (provenance CAPRI_COUNTRY) for activities neither regional source covers anywhere: 1,803 region-crop cells (tomatoes, other vegetables, apples, other fruit 241 regions each, textile crops 193, wine 183, tobacco 165, table grapes 145, citrus 88, table olives 65). Olives for oil stay at 0.197: CAPRI's matrix has no olives for oil (calibrate_supply.gms disables OLIV -> OLIO). Norway has no CAPRI elasticities in any source and keeps the defaults

<a id="k31"></a>
### K31: crop_cost_shares.csv: the plant-protection share did not follow its stated method for every crop, and the file had no builder

The method in supply_module (CAPRI's PLAP x UVAG.PLAP over TOIN, area-weighted over the member states) gives olives for oil 0.422 against the file's 0.249, citrus 0.126 against 0.112, grass 0 (CAPRI books no plant protection on grass) against 0.031.

- **Effect:** fallback only: the pesticide and organic instruments use CAPRI's regional PLAP, INPO and FERT per ha (plant_protection_cost.csv); the shares serve 264 region-crops (1,087 kha: Norway's crops, 943 kha, outside the EU instruments' cost file, and other fibre crops, 144 kha, which have no share row)
- **In 9t:** small
- **Status:** **fixed**: tools/build/build_crop_cost_shares.py writes the file from CAPRI's 2017 results (levels as weights, CAPRI's TOIN); other-input and fertiliser shares of every crop reproduce within 0.003 (cotton's row, now textile crops TEXT, is CAPRI's TEXT over all member states and reproduces too), plant protection within 0.01 except olives for oil, citrus, pulses (0.281 -> 0.271) and grass; flowers, nurseries, other marketable and other industrial crops gain CAPRI values (before the supply module's default)

<a id="k32"></a>
### K32: Arable crops in many regions and the 14 Mha of other fodder were on literature elasticities although CAPRI's are in the data

The PMP elasticity source (pmp_own_price_elasticities.csv, CAPRI codes) was mapped to model regions through nuts_crosswalk.json alone, which reaches 140 of 248 regions; the regional PELA file covers 173. Regions in neither (Denmark, Berlin, Saxony, Poland's renamed regions, Finland's, Croatia, Slovenia, the Baltic and island states, among others) or a crop missing from both for a region stayed on the literature defaults: 14.1 Mha of grown arable crops (soft wheat 3.7 Mha, barley 2.0 Mha, grain maize 1.2 Mha). And CAPRI's code for fodder on arable land, OFAR, was not aliased to the model's OFOD, so other fodder stayed at 0.12 everywhere (CAPRI median 1.05).

- **Effect:** arable and fodder supply response in those regions
- **In 9t:** yes
- **Status:** **fixed**: the PMP source maps through the shared region map (region_capri_map.csv: correspondence, fixes, splits and merges), then the member state's national row; OFAR -> OFOD aliased. Grown area on literature defaults: 95.8 -> 69.6 Mha (arable crops 14.1 -> 1.1 Mha), of which grass 51.6 Mha (no CAPRI grass elasticity in either source), set-aside 8.1 Mha (0 by construction), olives for oil 4.7 Mha, minor crops CAPRI has no elasticity for (other marketable and industrial crops, other oilseeds, nurseries, flowers, rice) and Norway

<a id="k33"></a>
### K33: The legacy nitrate-limit instrument reads unsourced per-head N coefficients

SupplyModule.base_n_intensity (the anchor of `nitrate_limit` and `nitrate_limit_delta`, used by the example scenarios in capri_mod/scenarios, not by the Farm-to-Fork or Green Deal runs, which use CAPRI's N-balance target) sums nutrient_coefs.csv's N over all activities, animals included (dairy cows 85, pigs 22 kg per head: no source recorded). The file also held a row for the retired SHGP and a row whose name was garbled (OANI with stray bytes).

- **Effect:** only scenarios using nitrate_limit
- **In 9t:** yes (same rows), not for the CAPRI scenarios
- **Status:** **retired** (27 October 2026, the project lead's decision): the instrument (`nitrate_limit`, `nitrate_limit_delta`, PolicyScenario.nitrate_limit_change), its N_limit row, the Mitscherlich intensity margin it drove (capri_mod/supply/intensity.py, SupplyModel._apply_intensity_margin, base_n_intensity) and the livestock intensity bounds only it read (livestock_intensity_bounds.csv and its builder) removed; nitrogen limits are CAPRI's N-balance target. nutrient_coefs.csv keeps its crop rows (other readers); its animal rows removed (they also entered the supply result's reported nutrient_balance)

<a id="k34"></a>
### K34: The EU-wide crop producer prices (fallback) were of unrecorded source and far from CAPRI's

producer_prices.csv: other vegetables 30.8 EUR/t (CAPRI EU 509), tomatoes 33.5 (394), other fruit 24.4 (889), tobacco 43.8 (3,003), wine 95.5 (1,430), olives 49.5.

- **Effect:** only where a member state has no CAPRI price for a crop (regions use CAPRI's regional or national MPRI); base anchors unchanged by the fix
- **In 9t:** yes
- **Status:** **fixed**: tools/build/build_eu_producer_prices.py, CAPRI's production-weighted EU price

<a id="k35"></a>
### K35: Splitting CAPRI's textile crops by country left gaps

The model's cotton (COTT) and other fibre (OFIB), both CAPRI's TEXT: other fibre crops had no plant-protection cost row (the builder took cotton only; 144 kha on the EU-wide share) and cotton found no fertiliser-distribution prior (the priors were filed under OFIB).

- **Effect:** other fibre crops' pesticide and organic instruments; cotton's crop-group fertiliser allocation (Greece, Spain, Bulgaria)
- **In 9t:** yes
- **Status:** **fixed**: one activity TEXT as CAPRI (tools/build_text_merge.py)

<a id="k36"></a>
### K36: Where the projected herds' fodder use was below the projected fodder output, the baseline missed the projected crop levels, and the difference fell on the most elastic crops

The fodder balance row (CAPRI's SUPBAL_, an equality kept as a narrow band) was made exact at base only when use exceeded output (rhs = max(0, use - output)); with use below output the band forced the fodder area down to the use, and the no-idle-land rule put the freed land on cereals: FI1D other fodder 228 against a projected 258 kha, barley 43 against 33, oats 61 against 48. The baseline calibration then stalled after one round, and its global stop rule (worst drift not falling by 5%) ended the calibration for every region. 43 region-activities ended more than 5% off their projected level (excluding fodder). Made more uneven by K32.

- **Effect:** 2030 baseline of the regions concerned (FI1D, ITF4, ITF5, ITG1, ITI1, LU00 ...); scenario changes are measured from the model's own baseline
- **In 9t:** yes
- **Status:** **fixed**: the fodder row is exact at base in both directions (the projected gap is carried as a constant, as CAPRI's baseline holds its balances); the calibration stops per region, not globally. FI1D, ITF5, ITG1, LU00: every cereal within 0.3% of its projected level after 4 rounds (barley 33.19 against 33.23). Full EU baseline: region-activities more than 5% off their projected level 61 -> 1, more than 1.5% 218 -> 4

<a id="k37"></a>
### K37: Green Deal does not converge with CAPRI's GL food demand: the young-animal markets hit capri-mod's price bound

With the GL (step 2 of docs/archive/MARKET_STRUCTURE_PLAN.md) EU meat prices rise further (beef +82%, pork +112%); the calf and lamb price ratios reach the bound of 5 x base in `_update_young_animal_prices` (capri-mod's guard, not CAPRI's: CAPRI clears young animals inside its market model, yaniMarket_ per trade block) and 16.5% of the young-animal balance stays open, so the outer loop stops at 60 iterations with every other criterion met from iteration ~45.

- **Effect:** Green Deal run unconverged (r15, r16); Farm-to-Fork converges (17 iterations)
- **In 9t:** no (no GL in 9t; the bound is in 9t, not binding there)
- **Status:** **fixed** (19 October 2026): CAPRI bounds young-animal prices at +-10 x (|level| + 10) and allows negative prices (arm/set_start_val.gms, widen_bounds.gms): the bounds 0.2 and 5 x base became a numeric guard of +-50 x base; the Newton step is limited to 30% of the current or the base price, whichever is larger; young animals clear per market as CAPRI's yaniMarket_ (the EU, or each trade block). Green Deal converges: one EU region 30 iterations (997 s; lambs 6.1 x base, calves 5.3 x), two blocks 42 iterations (1,325 s; the East block's calves -0.64 x base, its surplus cannot leave the block). Results within 1 point of the unconverged run except pork price -7.9, poultry -3.9, milk -3.4 points

<a id="k38"></a>
### K38: The Green Deal runs used end-point targets in 2030 and a pesticide yield loss star 3.0 does not have

`--scenario greendeal` ran lnds10 org25 pest50 surp50 (mine00) in 2030; CAPRI's production batch phases the targets (2030: lnds8 org18 pest20 mine13crp surp30; pestRedu reaches 32 only from 2040). And the pesticide cut carried JRC121368's yield loss (10% at a 50% cut), while star 3.0's pesticides.gms calls conventional_io.gms with yield 'off' (PLAP -pestRedu%, INPO +pestRedu%, cover crops pestRedu/2; pestDisaggStage none, so no yield loss and the organic yield gap unscaled). Found when Witzke's batch and the star 3.0 code were read against the runs (19 October 2026).

- **Effect:** Green Deal results: pork price +104.4% (r22) -> +62.8% with star 3.0's pesticide rule (r23_gd_star3pest, 27 iterations) -> +6.2% with CAPRI's 2030 settings (r23_gd2030, 11 iterations, 1,127 s); milk +81.6 -> +64.8 -> +10.9; beef +81.6 -> +66.2 -> +7.9; cereals production -14.2 -> -6.2 -> -5.7; EU N surplus -46.2 -> -46.5 -> -27.9; GHG -32.2 -> -29.6 -> -12.2
- **In 9t:** yes (same settings)
- **Status:** **fixed (settings)**: `PolicyScenario.pesticide_rule` (`star3` for the Green Deal group, `jrc121368` for Farm-to-Fork as the report); `greendeal_2030_scenario()` / `--scenario greendeal2030`; `--scenario greendeal` kept as end-point targets in 2030. Still no CAPRI Green Deal result to validate against (the run at hand, scen_greendeal_2030, is the maximum-mitigation run; capri_data/validation/greendeal_2030/ holds that run despite its name). r23_gd2030: ITC4, AT22, RO41 kept the conic solution where the coupled fertiliser NLP hit its iteration limit

<a id="k39"></a>
### K39: CAPRI's processing functions divided by the wrong price of the non-agricultural good

ProcNQ_ divides its Hessian by DATA(RMS,"PPri","Inpe","CUR"), which CAPRI's market sets to the inflation factor before a simulation (arm/market1.gms: p_infl^(Y-BAS) = 1.019^13 = 1.2772 in 2030); the calibration file stores 1, and tools/build/build_processing_nq.py took that 1 (the dairy and biofuel blocks used 1.2772 from the market dump). With 1.2772 the implied crushing elasticities equal CAPRI's p_ElasProc exactly (DE rapeseed 0.39, soybeans 0.81; FR rapeseed 0.49). The audit's "oil processing does not reproduce p_ElasProc (rapeseed oil -1.9 against -0.72)" was a false alarm: -0.72 is p_ElasDem; p_ElasProc of rapeseed oil is -1.88, what the Hessian gives at the calibration prices (CAPRI calibrates the oils on undeflated PPRI and simulates with INPE: -1.47 in its own simulation, as here)

- **Effect:** crushing and processing responses 1.277 x too strong
- **In 9t:** no (ProcNQ_ came later)
- **Status:** **fixed** (19 October 2026): INPE from CAPRI's 2030 market dump (processing_nq_base.csv), applied to every Hessian term; test_processing_inpe_and_nonEU_feed_are_capris_2030

<a id="k40"></a>
### K40: CAPRI's minimum mineral share (NUTMIN_) on together with the inner fertiliser distribution model

- a combination star 3.0 does not allow: NUTMIN_ enters the regional model only with the inner model off (supply_model_e_list_linear.gms), and prep_sim.gms aborts if the minimum shares are combined with it. The inner model is star 3.0's default (GUI true; Witzke's Green Deal production batch on). K9 had put the floor in with the inner model (option 3) added later

- **Effect:** Farm-to-Fork (all other fixes in, r27): pork price +38.2 -> +33.1%, poultry +28.3 -> +25.3%, sheep and goats -10.8 -> -6.8%, cereal price +7.9 -> +9.8%; gap 4.39 -> 4.38. Green Deal 2030: CAPRI's coupled form needed in more regions (K41)
- **In 9t:** yes (K9)
- **Status:** **fixed**: `RegionalSupplyModel.use_min_mineral_share = None` = as CAPRI (on only with `fert_dist_inside` off); `run_f2f_2030.py --nutmin on/off` forces it; the baseline cache and the run metadata carry the setting Superseded 26 October 2026: `use_min_mineral_share`, `fert_dist_inside` and `--nutmin` were removed with the conic form, the only form where they acted; NUTMIN_ is off, as in star 3.0 with the inner fertiliser model.

<a id="k41"></a>
### K41: The base check of CAPRI's crop-group allocation ran under the scenario's mineral fertiliser caps

Where the allocation does not exist at a scenario solution, the region's base is checked (and its priors calibrated, K21) before CAPRI's coupled form is solved; that check applied the Green Deal's mineral caps by crop group (mineRedu 13crp, set from the baseline allocation at 87% of it), under which the base's own mineral N cannot be placed, and the region was reported "base allocation infeasible (data)" (11 regions in Green Deal 2030 once K40 was fixed: DE91, RO12, RO22, RO42, SE12, SE21-23, SK02, SK04, PT30). Found with SE12: allocation at the base totals exists without the caps, not with them

- **Effect:** those regions kept the conic solution with no CAPRI allocation
- **In 9t:** no (mineRedu is the prototype's)
- **Status:** **fixed**: the base check without the scenario's caps, as CAPRI calibrates at its baseline. Then the coupled NLP solves in ES12, RO12, SE12; IPOPT reaches its iteration limit in PT30, RO42, SE22, SE23, SK02 (conic solution stands, reported). RUN TIME (measured alone on the 2 cores, per-call IPOPT log `CAPRI_FD_LOG`): the coupled solves took ~70% of Green Deal 2030 (r28: 2,539 s; 119 calls, 3,540 s of worker time, half of it in calls that failed after 4-6 tries of 1,000 iterations). Changes: a region whose coupled form failed twice in a row is retried every fourth iteration only; the tries start with what solved the region last time, else the warm start with the adaptive barrier (18-50 iterations where the monotone one ran its 1,000), then the inner model's iterate (every cold success), the generic start last. r32: 1,692 s (-33%), 103 calls; coupled form solved in PT30, RO12, RO22, RO42, SE12; open: ES12, SE22, SE23, SK02 (r28: open PT30, SE12, SE22, SE23); EU indicators within 0.15 points of r28. Tried and dropped: two tries only after a failure (1,623 s, but ES12, RO22, SK02 left open). The failing calls are most of what remains (1,617 of 1,994 s)

<a id="k42"></a>
### K42: An EU ration was still chosen outside the supply models every iteration although feeding is inside them

`_update_rations` solved the external ration QP per region and animal at current feed prices (damped), and its result reached the regional models through the fodder rows (K46)

- **Effect:** see K46
- **In 9t:** yes
- **Status:** **fixed**: with `use_feed_in_supply` (default) no outside choice; the ration state is the last regional solution's feed per head (base ration before the first); `use_ration` still supplies the rations' data; test_rations_are_chosen_only_inside_the_supply_models

<a id="k43"></a>
### K43: Non-EU feed demand: other vintage than the other use blocks, and no feed function for ROW, Korea, Morocco, New Zealand

feed_demand_nonEU.json took FAO_agg 2017 FEDM/DOMM shares and elas_2_1717, only for trade regions identical to one CAPRI region, while GL food demand, processing and biofuels use CAPRI's 2030 calibration; ROW's feed (96% of its soybean cake use) fell on the generic own-price response (armington eta, of partly unrecorded source)

- **Effect:** 7.0% of world use (biofuels and raw milk aside) on that response; EU indicators within 0.3 points (r26_dec_feed)
- **In 9t:** yes
- **Status:** **fixed**: tools/build/build_feed_demand_nonEU.py from data_market_1730defaulta CAL (feed share = FEED / (HCON+FEED+PROC+BIOF)) and elas_2_1730 p_ElasFeed, aggregated from CAPRI's 80 behavioural regions to every trade region, every product with a CAPRI feed function (494 entries, 23 regions): 1.3% left. REGISTERED: Turkey (a CAPRI supply-model region, no p_ElasFeed), Egypt, Algeria, Iran, Saudi Arabia (not CAPRI behavioural regions, K45) keep the generic response (corrected 29 October 2026, K45: EGY and ALG are CAPRI behavioural regions, mapped into ROW with their p_ElasFeed; the four model regions had no data and were removed)

<a id="k44"></a>
### K44: An inert income term and invented fallbacks in the market

Engel elasticities 0.1 / 0.5 / 0.3 multiplied demand by a GDP index nothing ever set (no effect); world price 200 EUR/t, base use 100 kt and demand elasticity -0.25 filled missing data (never hit with CAPRI's data)

- **Effect:** none on results
- **In 9t:** yes
- **Status:** **fixed**: income term removed; missing world prices or elasticities raise an error; a missing base use is zero. REGISTERED: armington eta for products other than the cereals and DDGS/FENI/FPRI is of unrecorded source; it acts on 1.3% of world use (K43)

<a id="k45"></a>
### K45: Egypt's oilseed rows

The market has rows for Egypt (EGY) only for SOYC, SOYO, SUNC, SUNO (1.7 Mt of soybean cake), from capri_oilseed_products_baseline.json, while CAPRI's Egypt is in ROW in every builder of CAPRI's 2030 market (tools/build/recalibrate_trade_2017.py REGION_MAP); DZA, IRN, SAU have no use at all

- **Effect:** possible double count of Egypt's oilseed products; not checked
- **In 9t:** ?
- **Status:** **fixed** (29 October 2026). No double count: every market file maps CAPRI's behavioural region EGY (and
  ALG, both in CAPRI's market region MED) into the model's ROW (food demand, processing, crushing, dairy, biofuels,
  supply elasticities, welfare base); the EGY rows left in capri_oilseed_products_baseline.json are read by nothing
  (its one reader, SupplyModule._cake_index, takes the EU27's cake feed use). Found instead: the model declared EGY,
  DZA, SAU and IRN as trade regions (definitions.TRADE_REGIONS) without any data (no bilateral flows, no use, supply
  or processing; tariff rows of zeros), carried through the market as empty regions; Saudi Arabia and Iran are not
  behavioural regions of CAPRI's (capri_data/shared/rms.csv). Removed with their zero tariff rows: 26 trade regions (27
  with CAPRI's EU blocks); the documents' counts corrected. Results unchanged (to be confirmed by the batch's runs)

<a id="k46"></a>
### K46: The fodder balance's right-hand side moved with the rations

`_fodder_rows` holds the base gap (fodder use - output at the base levels, K36) as a constant, but computed it with the CURRENT ration state: before K42 with the ration chosen outside the models at current prices, after K42 with the models' last feeding. CAPRI's balance (SUPBAL_) carries its baseline. Found by decomposing the Farm-to-Fork change of this batch (K42 alone: beef price +22.9 -> +27.9%, beef animals -17.8 -> -22.2%)

- **Effect:** cattle chain in every livestock scenario
- **In 9t:** yes
- **Status:** **fixed**: the gap from the base ration x base herds. Farm-to-Fork (floor on, r25 -> r27_nutmin): beef price +27.9 -> +21.7%, beef animals -22.2 -> -17.5%, milk +45.0 -> +39.4%, gap 5.47 -> 4.39. Green Deal end-point targets (r24 -> r27): beef price +64.4 -> +41.7%, beef animals -43.6 -> -32.2%, milk +61.4 -> +46.7%

<a id="k47"></a>
### K47: The cattle chain's equilibrium is sensitive to changes outside it

Farm-to-Fork runs that differ only in this batch's processing change (K39) give beef price +21.6 / +27.9% and calves x2.26 / x2.72 (r26_dec_inpe, r25_f2f_nutmin); the beef price follows the calf price. The outer loop stops at the first point within its tolerances (young animals 0.5% of production)

- **Effect:** beef price, herds and milk price in livestock scenarios uncertain by several points
- **In 9t:** ?
- **Status:** **open**: check with tighter young-animal tolerance and other starting points; until then beef and milk figures carry this uncertainty

<a id="k48"></a>
### K48: Young-animal prices against CAPRI's own market run

Check against CAPRI's cap_after_2014 run without voluntary coupled support (tools/run/run_vcs_2030.py; before K46): calves +15.0% (CAPRI +26.3%), young cattle +3.6 (+4.0), replacement cows -14.5 (-0.2), piglets -0.1 (-0.05), lambs +17.0 (+10.7), beef price +0.4 (+2.2). CAPRI's calf price moves twelve times its beef price there: large young-animal price changes (Farm-to-Fork calves x2.2-2.7, Green Deal x5) are CAPRI's behaviour in kind, not a model artefact by themselves

- **Effect:** young-animal prices; the replacement-cow price far more responsive than CAPRI's
- **In 9t:** yes
- **Status:** **open** (replacement cows); registered (the rest). Other indicators of the test: 28, mean absolute deviation 1.24 points, correlation +0.85

<a id="k49"></a>
### K49: Diagnosis of the regions where CAPRI's crop-group allocation fails (20 October 2026): not the solver

tools/check/diagnose_fert_dist.py (exact linear feasibility test of CAPRI's inner fertiliser model at the region's solution; dumps with env CAPRI_FD_DUMP) shows that at the conic solution NO allocation exists under CAPRI's constraints, so any solver fails: (1) Green Deal 2030, 7 of 8 failures (SE23, PL41, SK02, ITH5, BG33, BG32, DED5): the conic model's mineral N exceeds the sum of the Green Deal's mineral caps per crop group at the current areas by 0.0-4.1% - the conic model carries only the regional cap; (2) PT30 (Farm-to-Fork base, Green Deal 2030): mineral N <= 0 (-127 t at the Farm-to-Fork base) - the conic crop-need row lets mineral N go negative where manure exceeds need, CAPRI keeps purchases >= 0 (v_netPutQuant <= 0) and each group's mineral flow >= 0.001 x its prior mode; its NUTNED_ is an equality per crop group and nutrient with the over-fertilisation factor fixed at the base, so manure beyond the need is not free in a simulation (corrected 20 October 2026, docs/SUPPLY_MODEL_MAP.md). Both are departures of the conic form from CAPRI's equations

- **Effect:** the regions IPOPT 'fails' in (K41)
- **In 9t:** yes
- **Status:** **resolved by the NLP port**: the regional supply model is CAPRI's own NLP (supply_model.gms) with its fertilisation block inside (NUTNED_ per crop group, purchases >= 0, the over-fertilisation factor fixed), solved by IPOPT; the conic form was removed on 26 October 2026, so the allocation is no longer made after a solve that did not contain it. r164 (Farm-to-Fork, 27 October 2026): no regional solve non-optimal (NL320000 at JRC121368's relaxed target, as the report)

<a id="k50"></a>
### K50: The regional supply model in CAPRI's own NLP form (20 October 2026; docs/NLP_PORT_DESIGN.md)

`CAPRIModel.supply_form = "nlp"` (the default since 20 October 2026, see Status): feeding (REQSE_ equalities, FEDUSE_, QUADRF_), fodder balances as equalities, NUTNED_ for N, P2O5 and K2O per crop group with the inner fertiliser model's FOCs inside, mineral purchases priced at CAPRI's unit values, endogenous manure availability, CAP greening (permGras, ecoSetAside 5%, cropDiv Shannon), the N-surplus target with the purchases, the mineral caps and the organic area target as CAPRI's regulations, ammonia/fertiliser/inhibitor options with CAPRI's loss cascade, the emission tax; LUC transitions after each solve. Calibrated so the base is a first-order point. REGISTERED departures: (1) need multiplier per region and nutrient, on need net of the permanent crops' own residues (model base levels with CAPRI's 2030 coefficients); (2) CAPRI's fertiliser calibration (blanket priors, posterior at the model's base) where CAPRI's 2030 posterior admits no allocation at the model's base (RO21, RO22, RO31, RO41, RO42, ES62, HU11 in the 2017 baseline); (3) inner-model dual bound +-1000 instead of +-10 where a tiny crop group needs more (HU11; CAPRI's own workaround is v_fertDistPartialSlack); (4) P and K manure trade follows N trade in the region's proportions; (5) one need multiplier per region instead of per technology; (6) Shannon term + 1e-6 kha instead of 1e-10 (IPOPT's bound relaxation); (7) the ecological set-aside rule held at the base where the model's base data do not meet it; (8) LUC solved after the regional model (identical without a LULUCF price); (9) the conic form's manure-application limit and mineral-N allocation column dropped (not CAPRI's); (10) the group's organic conversion for CAPRI's organic caps is capri-mod's per member state and crop class (the shares of the organic I/O change), weighted by base area; (11) where the Green Deal's mineral caps leave a group's need unmet (IPOPT infeasible), the inner model's duals are widened to +-1000; if that is not enough, the groups concerned are exempted one at a time, those whose need is out of reach under their cap first, with their cap at the baseline mineral N per ha (CAPRI's p_checkSmallMine in minfert_redu_by_crop.gms; CAPRI lists its exempted region x group pairs by hand, capri-mod finds them by solving; K71); recorded as nlp_relaxed ("caps:PERM"); (12) the split columns' manure (dairy, cattle, genetics) reaches ManureNPK_ in the proportion of their manure-application coefficient to their animal's

- **Effect:** baseline reproduces the base exactly (drift 0.0015 as the conic form). Farm-to-Fork (r38, NLP form): converged in 12 iterations, 1,346 s; mean absolute deviation from JRC121368 5.6 (conic r37: 4.4); pork price +40 (conic +33, CAPRI +43), milk +31 (+38, 1.5), poultry +35 (+25, 18), pigs -22 (-19, -14.5), dairy cows -5 (-7, -10), cereals production -12 (-15, -15), N surplus -29 (-33, -33.5), fertiliser N2O -34 (-40, -40). Green Deal 2030 (r39, NLP form): stopped after 25 iterations, 57 min: Finland's manure pool stays 3.7% out of balance from iteration 6 (conic r32: 16 iterations, 1,692 s); with the pools priced at IPOPT's reduced costs (r40) the pools cleared but the run switched between states for 21 iterations (95 min): BG32/33/42 and HU21-23 alternated between the relaxed and the strict problem from one outer iteration to the next; with a relaxation kept for the rest of the scenario once needed (CAPRI sets its exemptions once, before its solves) r41 converged in 10 iterations, 1,395 s (pork price +9.5 against conic +5.6, milk +11.9 / +10.4, poultry +10.6 / +5.8, pork production -8.5 / -5.3, cereals -3.9 / -6.0, mineral N -29.8 / -33.6, N surplus -26.6 / -28.3, GHG -12.9 / -12.0, NH3 -34.3 / -33.7). Found and fixed on the way (r35, r36: deviation 15.4): the crops' N need was their group's need spread by area (fallow 86 kg N/ha instead of CAPRI's 3.7; GRAE and GRAI alike), the grassland split column had no effect on NUTNED_, and the split columns entering after the first solve were left uncalibrated
- **In 9t:** yes (conic)
- **Status:** **default** (20 October 2026, the user's decision: CAPRI's own form; conic kept as `--supply-form conic`, a cross-check): the NLP form converges for Farm-to-Fork and the Green Deal; it is further from JRC121368's Farm-to-Fork (5.6 against conic 4.4), whose CAPRI version is older than star 3.0, and Farm-to-Fork takes 33 min against the 30-minute budget; (13) a relaxation once needed is kept for the scenario; (14) a warm start is cut at 200 IPOPT iterations and followed by a cold start from the same point. N loss cascade: K51. AD and winter cover in the cascade: K51. Not yet in CAPRI's form: legume share, tillage, urea substitution, 3-NOP, linseed, SupplementPerc_. Under the emission tax the NLP form adopts no nitrate supplement for IE04's dairy cows (conic: 29 kheads): REQSE_ holds crude protein as an equality (CAPRI's simulation model), so nitrate's lower protein requirement pushes grass out of a grass-based ration (the requirement row's dual +200 EUR per unit against the tax gain) 26 October 2026: the conic form was removed (no run had used it since r110; the user's decision); `supply_form` and `--supply-form` are gone.

<a id="k51"></a>
### K51: CAPRI's N loss cascade and the storage options of endoLeach (20 October 2026; docs/N_CASCADE_SPEC.md)

capri-mod's ammonia options worked with an NH3-only cascade in which the manure-management options mixed as alternative systems, and the option set had been built for endoLeach off, which capmod has on (capmod/set_global_variables.gms l. 55): the concrete basin (ManStorCon), the low cover on concrete (CovStorLowCon) and the pigs' AirPurCovLowC were missing, and LowEmHous and CovStorHigh lacked the basin's cost. Now: CAPRI's cascade (GRAZN_ ... GASRUNTOTNETF_, capri_mod/supply/n_cascade.py) with its p_Nemidat built from the MITERRA CSVs (tools/build/build_n_cascade.py) drives the options in both forms: the N they keep (GasRunTot) enters the manure applied, the NH3 part the ammonia accounts, the N2O by stage the manure N2O; the endoLeach options with CAPRI's costs, initial shares and maxima. REGISTERED: the initial covered-storage shares not raised to the Nitrates Directive minimum (CAPRI's code does it, its 'ini' reference run does not show it); the Nitrates Directive minimum shares (p_envConst CovStorLow, AmmAppLE/HE) built from CAPRI's nvz.gdx and not applied, as CAPRI's Green Deal settings have NDtech off (below); tillage, buffer strips, biodiversity options and biochar not in capri-mod (their LEACHN_ terms held at CAPRI's reference); the fertiliser techniques' N2OMAN/N2OSYN terms of APPLN_ and GASTOTNETF_ applied outside the cascade; leaching (LEACHN_) and the indirect N2O of leached and run-off N in the accounts, the purchases' part under the tax at the reference leaching share; DEPARTURE (the user's decision): CAPRI's '+ v_ammoAppLeaAgg' in LEACHN_ lowers leaching when low-emission application is adopted, against its own data (p_reducGains LNA Leach -0.24) and its runoff equation; capri-mod subtracts it (n_leaching.AMMAPP_SIGN = "consistent"; "capri" reproduces CAPRI; docs/N_CASCADE_SPEC.md 'Leaching')

- **Effect:** per-head losses of CAPRI's Green Deal reference run with endogenous technologies reproduced to 1e-6 with CAPRI's shares (712 values, DE11 NL22 PL22 DK; test_n_cascade_reproduces_capri); 528 of 532 initial shares of the options within 2e-4 of that run (the other 4: DK dairy, CAPRI's group scaling, applied in build_ammonia_tech_model.py). Farm-to-Fork conic r46 / NLP r45: deviation from JRC121368 4.38 / 5.57 (unchanged), covered storage 9.1 -> 28.5 / 10.5 -> 30.9 % (CAPRI 14 -> 34; before 15 -> 41), ammonia -40.5 / -40.0 (before -42.3 / -41.3; CAPRI -33.0). Green Deal 2030 conic r44 / NLP r43: NH3 -31.5 / -32.6 (before -33.7 / -34.3), other indicators within 0.5 points. With AD and winter cover (NLP, r47 Green Deal 2030 / r48 Farm-to-Fork, against r43 / r45): AD 1.0 -> 2.2 / 3.8% (share weighted by excreted N of the animals with ammonia options); manure CH4 -5.9 -> -7.4 / -13.6 -> -17.0% (CAPRI's Farm-to-Fork -12.2); GHG -13.0 -> -13.2 / -17.1 -> -17.5 (CAPRI -14.8); deviation from JRC121368 5.57 -> 5.76, most of it manure CH4; other indicators within 0.5 points except the Green Deal's sunflower (price +5.4 -> +3.0, production -3.5 -> -2.1); r47 15 iterations, 2,218 s; r48 12 iterations, 2,110 s
- **In 9t:** yes
- **Status:** **fixed** (cascade and storage options; leaching added 20 October, docs/N_CASCADE_SPEC.md 'Leaching'); open: tillage, buffer strips, biodiversity options, biochar. Added later on 20 October: anaerobic digestion (tools/build/build_ad_option.py: CAPRI's cost curve, initial and maximum shares, calibration, CH4 factor QE_AD/QE_NOC; shares as CAPRI reports them, v L(1-G); initial and maximum shares of the four regions and the pigs' cost exactly as CAPRI's run, test_ad_option_reproduces_capri; cattle volatile solids from CAPRI's table, REGISTERED until the run's p_VSER is in hand, cattle costs then -20 to +23% off) with its N effects through the cascade and its CH4 effect in the accounts, applied to dairy cows too (CAPRI as coded has none for them, ad_data_and_cali.gms l. 588: switch `EnvironmentalModule.ad_dairy_ch4 = "capri"`); winter cover in the cascade (CAPRI's v_Miti(CATC, WinterCov) = the catch-crop share, base and under the requirement: 0.35 x share off the runoff from the surface, so it keeps manure N); the Nitrates Directive minimum shares built from nvz.gdx (tools/build/build_nitrates_directive.py, nitrates_directive_min_shares.csv) and not applied, as in CAPRI's Green Deal runs: the minima (p_envConst CovStorLow, AmmAppLE/HE, ManStorCon; ammo_tech.gms l. 2396-2740) and their constraints (ND_ManStor_, ND_ManCov_, ND_AmmAppLE_, ND_AmmAppHE_, supply_model.gms l. 4300-4325) exist only with %NDtech% on, and CAPRI's settings for those runs set it off (pol_input/cap_after_2023/refpol_endotech_all_sup.gms l. 401, refpol_endotech_all.gms l. 402); with ghgTechCali=ini they are zeroed as well. An NDtech switch for other settings is not implemented (the user's decision); winter cover chosen by the regional model in the NLP form (20 October 2026): CAPRI's v_Miti(CATC, WinterCov) with its cost curve (cover_crops.gms l. 336-700: MaxShare from p_coverMax, relSubs case 1, pmpParSqr, pmpParLin; tools/build/build_winter_cover_option.py), the winterCover_ row, the Farm-to-Fork requirement as its lower bound, its BioFix N in the arable residue pool (fertDistCres_) and in the N-surplus row (e_BIOFIX), its share in the cascade's runoff, its crop-residue N2O under the tax (N2OCRO; CO2SEQ is not in CAPRI's taxed GGWP); calibrated so the base share is a first-order point; REGISTERED: the purchases' leaching under the tax stays at the reference leaching share (the share's effect on it is not priced), the winterCover_ row's right-hand side at least the base point's; the conic form keeps the requirement

<a id="k52"></a>
### K52: Interface audit for the README rewrite (20 October 2026)

: things the code does differently from what its names, docstrings or the old README said. (a) Registry scenarios (`run(scenario=NAME)`, capri_mod/scenarios/scenarios.py): `FARM_TO_FORK` is a payment-rate proxy, not CAPRI's Farm-to-Fork (that is `policy.greendeal.farm_to_fork_scenario()`); `FLAT_RATE_BPS` sets nothing different from the baseline; `UKRAINE_SHOCK` applies no price shock (`WORLD_PRICE_SHOCKS` is never read by `run()`). (b) `PolicyScenario.trq_volume_changes` has no effect on results (it changes a handler whose tariffs are not used; the bilateral market's quotas are untouched) and accumulates across runs. (c) A `world_price_shock` run under `scenario="BASELINE"` becomes the cached baseline. (d) `surplus_cut=0` and `biofuel_mandate=0` are read as 0.5 and 1.0 (`x or default`). (e) `pesticide_rule`'s docstring claims a 0.45 factor on the organic yield gap the code does not apply. (f) `CAPRIModel(base_year=...)` does not switch every file (a default bound at definition time; files read from capri_data/2017 directly). (g) `ProjectionResult.increment` was always empty: **fixed** (scenario against baseline of the flat outputs). (h) `flatten_outputs` skipped production and the environmental accounts: **fixed** (EU production and prices, EU environmental totals). (i) `tools/run/run_tests.py` failed on `pytest.mark` and lacked `monkeypatch`/`tmp_path`: **fixed**. (j) `run_all_regions` printed an undefined name on a failed region (verbose): **fixed**. (k) N balance columns are t N, not kt as the dataclass comment and the run summary said: **fixed** (comment, summary). (l) P columns and `organic_area` of the environmental table are never filled. (m) the trajectory's `demand` block is accepted but not applied.

- **Effect:** (a)-(f), (l), (m): interface
- **In 9t:** –
- **Status:** **fixed** 20 October 2026 (the user's decisions): (a) FARM_TO_FORK, FLAT_RATE_BPS, UKRAINE_SHOCK and the unused WORLD_PRICE_SHOCKS removed (CAPRI's Farm-to-Fork: `policy.greendeal.farm_to_fork_scenario()`); (b) `trq_volume_changes` acts on CAPRI's EU tariff-rate quotas in the bilateral market (1000 t per commodity, spread over the exporters' quotas by base volume, base fill kept at the base quotas; `MarketModule._apply_trq_volumes`), a commodity without a CAPRI quota raises an error; the TRQHandler with its hand-entered quotas removed; (c) a shocked run is a scenario against the unshocked baseline; (d) 0 read as given; (e) docstring corrected (the organic yield gap applies in full; CAPRI's 0.45 only with pest_disagg on); (f) a base year other than 2017 raises an error; (g)-(k) fixed before; (l) CAPRI's gross phosphate balance (calc_nbalance.gms with PHOF, in P2O5) fills the P columns, and `organic_area` is the area the organic target converts (docs/P_BALANCE.md); (m) a trajectory `demand` factor other than 1 raises an error: the market's demand of a target year is CAPRI's market data of that year, and a demand factor alone has no consistent closure in the calibrated bilateral market (flows and supply fixed)

<a id="k53"></a>
### K53: NLP calibration carried across technology settings

The NLP form calibrates each region once (the base a first-order point) and again only when new columns appear. After a run at other mitigation settings (`endotech`, e.g. ghgTechMYld 0.2, which adds the genet_yld columns) the default baseline kept the other settings' calibration: IE04's baseline adopted genet_eff for the whole herd (found by `test_genetics_not_adopted_at_base` failing only after the emission-tax and endotech tests).

- **Effect:** runs in one process that switch `endotech` settings (tests, batch runs); not the 2030 runs of tools/run/run_f2f_2030.py (one setting per model)
- **In 9t:** –
- **Status:** **fixed** 20 October 2026: the calibration is kept per settings and restored with them (`SupplyModule.set_genetics_effects`)

<a id="k54"></a>
### K54: Market-side findings of the documentation review (20 October 2026)

: (1) `run(market_max_iter=...)` has no effect with the bilateral market (fixed 60 Newton rounds in `_solve_bilateral`); (2) the old premium market structure (`market_structure = "premium"`: SciPy root, tatonnement fallback, EU Armington premium) is still in the code, reached by no run path; stale docstrings (MarketModule, solve(), _dairy_params, DAIRY_TRADED) describe it or older states; (3) every non-EU region's supply uses one own-price elasticity per product (CAPRI's EU median p_elasSupp, else the Armington eps), not region-specific; (4) the crushing margin is evaluated at Armington price ratios for seed, oil and cake, where CAPRI's ProcMargO_ (market_model.gms l. 1118) uses producer prices for oil and cake; (5) Norway's feed bulk prices stay at base (the bulk table covers EU member states only); (6) `fao_market_baseline.json` still read as a fallback for EU self-sufficiency (inert for the traded products); (7) dead code in `_bridge_supply_to_market` (oil yields computed, unused).

- **Effect:** (3)-(5): results; (1), (2), (6), (7): interface and maintenance
- **In 9t:** –
- **Status:** **fixed** 20 October 2026 (the user's decisions): (1) `market_max_iter` is the bilateral solve's Newton rounds (default 60, unchanged behaviour); (2) the premium structure removed (`solve()` is bilateral only; eu_armington_premium, compute_trade_flows, _calibrate_demand_to_supply, _exempt_eu_from_world_calibration, eu_gross_trade removed; eu_gross_trade_supplement.csv archived); (3) each non-EU trade region's own-price elasticity is CAPRI's p_elasSupp ('CAL', elas_2_1717) of its CAPRI regions, weighted by CAPRI's 2017 production (tools/build/build_supply_elas_nonEU.py, supply_elas_region.csv: 772 region-commodity pairs; processed products keep the product value); REGISTERED: own-price terms only (CAPRI's non-EU supply has cross-price terms, p_hessNQSupp) - replaced 29 October 2026 by CAPRI's market supply functions with the cross-price terms (market.noneu_supply_nq, build_noneu_market_supply_nq.py; K98); (4) the crushing margin with the seed at its Armington price and oil and cake at their producer prices (ProcMargO_); biofuel feedstock prices unchanged; (5) Norway's supply models get feed bulk price indices from CAPRI's Norwegian bulks (FEED, ARM1P of NO000000; feed_bulks_no.csv), at the price signal they see; Norway's feed is not in the EU's feed demand; (6) the FAO fallback removed (CAPRI's EU balance covered every commodity it had); (7) the unused oil-yield code removed, fao_processing_splits.json archived

<a id="k55"></a>
### K55: Supply-side findings of the documentation review (20 October 2026)

: (1) when the NLP solve of a region fails, the region falls back to the regional QP without the feeding block (supply_module.py, after `_capri_nlp_solve` returns None), warned and recorded only as `SupplyResult.conic_failed = "nlp:..."`; `metadata["nlp_fallback"]` is always empty (`_nlp_blocks_missing` returns []); (2) `RegionalSupplyModel.fert_dist_inside` and `use_min_mineral_share` (NUTMIN_) act only in the conic form (the NLP form always has the inner model); (3) winter cover is not a choice variable: its share is CAPRI's 2030 catch-crop share or the requirement; (4) the manure pools are cleared as a primal spatial equilibrium (docstring says the dual); (5) stale docstrings (capri_regional_nlp module, capri_nlp.py, model.py qp_solver comment, ammonia_techs REGISTERED note, capri_pmp provenance name, feed/ration NOT YET note); (6) fixed: the manure-trade columns' emission-tax term now carries the indirect N2O of runoff and leaching in the conic form too, so the NLP form takes out exactly what was added (it had left a spurious credit on exports with a tax and manure trade).

- **Effect:** (1): results of regions where IPOPT fails (none in the r47/r48 runs); others: interface
- **In 9t:** –
- **Status:** **fixed** 20 October 2026: (1) where IPOPT fails from every start (warm, previous, cold) the region's solve is done in the conic form (feeding inside) and recorded per region in `metadata["nlp_fallback"]`; only if the conic form fails too does the existing chain follow (JRC121368's N-target relaxation, then the QP without feeding), recorded the same way; (2) a warning when these switches are set in the NLP form; (3) winter cover is chosen in the NLP form (below, K51); (4), (5) docstrings corrected; (6) fixed before 26 October 2026, (1) changed with the conic form's removal: where IPOPT fails from every start and the relaxations (JRC121368's N target, the landscape floor) do not help, IPOPT's last point is kept, warned about and recorded, as CAPRI keeps a non-optimal solve (the user's decision; test_nlp_failure_keeps_ipopts_last_point_as_capri); where the NLP cannot be built at all, the run stops.

<a id="k56"></a>
### K56: Norway in the EU's market and totals (found 20 October 2026)

Norway's seven supply regions (NO01-NO07) were solved with the EU's price signal, and their output was summed into the EU27 market supply (one EU market region: `MarketModule.supply_response` summed every supply-model country) and into the EU totals of the accounts (`env_EU_*`). CAPRI's bilateral data put Norway (NO000000) in the model's ROW, so Norway's base production was in both EU27 and ROW. Size at the 2030 baseline (r52): 0.6% of the model's UAA, 1.0% of GHG, 0.8% of the N surplus. In CAPRI, Norway is its own supply region (msNoEU: no EU policies, no mitigation options) with its own market region

- **Effect:** EU totals and EU market by about 1%; Norway's prices
- **In 9t:** –
- **Status:** **fixed** 21 October 2026 (the user's decision: as CAPRI): Norway is the 30th trade region NOR (CAPRI's market region NO000000, aggregation/defaultA.agg l. 48, 89; RMSSUP = NUTS0, global/fromimpact/sets.gms l. 4355), every per-region market file rebuilt with its builder (ROW loses Norway: ROW before = ROW + NOR now, to the files' rounding); the EU's dairy block and balances hold the EU member states only. Market (CAPRI's RMSSUP treatment): NOR's supply is its supply models' output (fixed within a market solve, anticipated against the prices they saw with CAPRI's p_elasSupp of NO000000, or CAPRI's market supply function with its own Hessian under `market_supply_nq`; ProdNQ_, market_model.gms l. 1529), the base calibrated at it (`_align_sup_base`); its raw milk to its own dairy block, delivered by its supply models (ProdNQ_ note 2, l. 1552); its feed from its bulks following its herds (feedBlkPrice_ l. 951, feedShareEqu_ l. 999; FeedBal_ l. 1018 is for non-RMSSUP only); its young animals in its own market (yaniMarket_ l. 1579). Its supply models see Norway's prices (`price_dev_ms["NO000000"]`, its feed bulk prices, its young-animal prices): a price level of their own relaxed toward Norway's market price with its own adaptive step (as the member states' milk prices; a departure from the EU signal, the first form, dragged Norway's prices with every move of the EU signal and kept full Farm-to-Fork runs from converging, r54-r60), in the outer loop's convergence test with CAPRI's filters (capmod/price_forecast.gms: only products above 10 x p_minAbsProdIterChg = 5 kt; Norway's changes zeroed from the 15th iteration, CAPRI's comment: "Norway reacts very sensitive and seems to jump around"); its last gap is reported (`metadata["nor_price_gap"]`). Norway is out of the EU's market rows and of `env_EU_*` (reported as `prod_NOR_*`, `price_NOR_*`, `env_NO_*`); tools/run/run_f2f_2030.py and tools/check/compare_runs.py sum the EU27 without it. Norway's soya crushing (CAPRI's 405 kt, p_ElasProc 0.582) added 21 October 2026 (tools/build_crushing_nor.py; its rapeseed crushing, 7.6 kt with oil and cake at 1.43 t per t of seed in CAPRI's data, left out); the anticipation elasticity is CAPRI's p_elasSupp of NO000000, as CAPRI's RMSSUP treatment. Norway's pigs fixed 21 October 2026 (evening; tools/build/build_norway_pigs.py): Norway's regions had no pigs because the herd source item is missing, not the data - CAPRI's Norwegian data (res_17NO) have no census total 'PIGS'.'HERD', only SOWS and PIGF HERD, so the EU rule (PIGF = census total - sows, tools/build_pig_split.py) gave zero. Now PIGS := CAPRI's SOWS HERD, PIGF := CAPRI's PIGF HERD (49.8 and 451.4 thousand head, NO000000's totals), through tools/build/build_capri_base.py's region spec (NO01, NO03, NO04, NO05: Eurostat cattle shares of NO08 + NO09 + NO0A, a proxy for pigs, as for all their other items). Norway's PIGF head is therefore CAPRI's fattening place, the EU rows' the census stock of non-sow pigs (DE11: 953.6 census against CAPRI's PIGF HERD 604.1); the per-head coefficients are CAPRI's regional totals over the model's heads, so Norway's base totals are CAPRI's (pork 139.76 kt = GROF PORK of NO000000; manure N 9.18 kt; feed, costs, revenue, premiums, CH4, manure P and K, piglets) and its per-head values are not comparable with the EU's. Every per-head file rebuilt by its builder; EU rows unchanged (tools/build/build_manure_n2o.py would add 29 EU pig rows that manure_n2o_tech.csv does not hold: that file keeps its rows, Norway's unchanged). The market needs no change: per product, NOR's supply is its supply models' output where they produce it (`supply_response`, `_align_sup_base`), so pork switched from CAPRI's market supply function to the supply models by itself; piglets clear in Norway's young-animal market (yaniMarket_ per RM); its feed bulks follow its herds with the pigs. The ammonia options' cost basis found on the way is K63 (fixed the same day). Norway's pig census (22 October 2026, afternoon; the project lead's request, with SSB's 2020 county file of pig places): NO01, NO03, NO04, NO05 now share NO08 + NO09 + NO0A's sows and fattening pigs by Statistics Norway's county census of 1 January 2017 (capri_data/sources/ssb/ssb_pigs_county_2017.csv, from SSB's own file ssb_husdyr_fylke_2017_original.csv downloaded by the project lead - tables 03710 / 03791 - by tools/build/build_ssb_pigs.py: breeding pigs, fattening pigs; county sums = SSB's national totals; the earlier transcription from ssb.no matched it in every cell) instead of Eurostat's cattle shares (NO05 0.36 of the pool's pigs against SSB's 0.09-0.10, NO04 0.42 against 0.54-0.56); the 2020 file (places by 2020 county) agrees (NO04 0.537, NO05 0.091, NO01 + NO03 0.372) but cannot separate NO01 from NO03, so the 2017 table is the source and the 2020 one the check. Per-head coefficients are per territory group, so only the four regions' herds and piglet net exports changed (the rebuild checked file by file); test_norway_pig_split_follows_statistics_norway. Without Norway's regions in a run NOR is an ordinary region at CAPRI's base. Tests: capri_mod/tests/test_norway_market.py

<a id="k57"></a>
### K57: Three Dutch regions not in CAPRI's form under Farm-to-Fork (found 21 October 2026)

NL11, NL13 and NL32 (ranked 11th-14th by CAPRI's baseline N surplus, just below JRC121368's nine capped regions) get the full tiered N target (NL13: 65.5 kg N/ha against 141.7 at the 36% cut). IPOPT finds no point of CAPRI's form at it (Infeasible_Problem_Detected or Maximum_Iterations_Exceeded at 3,000 iterations, from every start) in every scenario iteration, and the conic form (a convex approximation, which meets the target) stood in. Present since the NLP form became the default: the pre-merge version (r52) fails on NL13 the same way but did not record it (warning only); the fallback log (K55) made it visible (r54-r63: 12-25 fallbacks per region per run). Each failed attempt also cost up to 3 x 3,000 IPOPT iterations per iteration.

- **Effect:** three regions' results in the conic form; run time
- **In 9t:** –
- **Status:** **fixed** 21 October 2026: in the NLP form, where CAPRI's form fails at the tiered target, JRC121368's rule for regions whose target "generated infeasibilities in the model" (sect. 4.3.4: the EU-average cut, 36%), which the model already applied when the conic form failed, is tried in CAPRI's form first; kept for the scenario (sticky, as before); recorded in `metadata["nlp_fallback"]` ("... -> CAPRI's form at JRC121368's relaxed target"); if CAPRI's form fails at the relaxed target too, the conic form at the tiered target as before. REGISTERED: IPOPT's infeasibility is local, not a proof; these regions now get a looser target than the conic form reaches. Test: test_nlp_form_takes_jrc121368_relaxation_where_the_tiered_n_target_fails

<a id="k58"></a>
### K58: NLP form: degenerate multipliers in the calibration made the problem badly scaled and its solutions path-dependent (found 21 October 2026)

The calibration (`CapriRegionalNLP.calibrate`) fits the multipliers of the rows and bounds active at base by least squares and puts what remains in the activities' linear terms. Where a row and a bound are active on the same variable with opposite signs (grassland_lo: land_GRAS - GRAS <= 0, with land_GRAS at its lower bound) any pair (lam, -lam) fits; the unregularised fit returned 6e13 for IE04, and grass's linear term took it (GRAS 5e10 EUR/ha in IE04, 8e16 in NL13 in the pre-merge version): an objective gradient of 1e14, IPOPT's scaled tolerances meaningless, and solutions that depended on the path. Found when a mathematically equivalent rewrite of the loss cascade changed IE04's carbon-tax response (suckler cows 370 against 315 kha).

- **Effect:** every NLP-form run before the fix (how much each region moved depends on the path; Farm-to-Fork r65 -> r67 in CHANGELOG)
- **In 9t:** –
- **Status:** **fixed** 21 October 2026, in two steps: CAPRI's land rents fixed as the land balances' multipliers at the 2030 market year (docs/LAND_RENT_CALIBRATION_PLAN.md: D_AREA of CAPRI's 2030 reference, land_rents_2030.csv), as CAPRI's calibration takes them (cal_land_nests.gms, prep_cal.gms), and for any other undetermined pair a ridge term (CAL_RIDGE 1e-10 on the scaled multipliers) picks the least-norm multipliers where the fit leaves them undetermined; the fit's residual is unchanged (IE04 7e-10), GRAS's term 604 EUR/ha, both cascade forms give the same solution (315 kha), IPOPT 61 iterations instead of 174. DEPARTURE (stated to the user): CAPRI takes the duals of its calibration solve, unique at the solver's basis; the least-norm choice stands in for that where the fit is degenerate. Test: test_emission_tax_in_supply_follows_capri

<a id="k59"></a>
### K59: Histosol fallowing never happened (found 21 October 2026)

The fallowed area F was on the upper land row only (crops + F <= land) while the mirrored lower row (land <= crops) left it out, so F <= 0 wherever the pair is tight - the arable and permanent rows always. CAPRI's Farm-to-Fork run fallows 2 -> 9% of the histosol area; capri-mod 0.

- **Effect:** Farm-to-Fork and Green Deal: histosol N2O and CO2, land use
- **In 9t:** yes
- **Status:** **fixed** 21 October 2026: F on both rows (crops + F = land; `_histosol_columns`). Same test as K60

<a id="k60"></a>
### K60: The grassland land row was not an equality (found 21 October 2026)

Under CAPRI's LandBalNoSlak_ the arable and permanent rows hold activities - land at the base use on both sides; the grassland row's upper side kept the land data's headroom (IE04 173 kha, NL13 6.5 kha): grass could grow onto it at no land cost, the base had no grass land rent (its upper row slack, the lower binding), and the calibration's multipliers were degenerate there (K58).

- **Effect:** grass and cattle responses in regions with headroom
- **In 9t:** –
- **Status:** **fixed** 21 October 2026: the upper row at the base use too (`_land_augment`). Test: test_land_rows_are_equalities_and_histosol_fallow_keeps_its_land

<a id="k61"></a>
### K61: PMP cross terms: structure not CAPRI's, and CAPRI's group curvature not at its size (found 21 October 2026)

CAPRI's QUADRA_ (with GRPLEVL_) has cross terms only through the crop groups' levels (CERE, CER2, OILS, OARA, FARA); permanent crops, vegetables, grass and animals have diagonal terms only. capri-mod's PMPCalibrator gave every other pair a uniform term (0.05 / (n - 1) x sqrt(Q_ii Q_jj)) and used PELA cross terms outside the groups (all 312 permanent-crop pairs in ES61).

- **Effect:** substitution between crop groups and the other activities
- **In 9t:** –
- **Status:** **structure fixed** 21 October 2026 (`PMPCalibrator.CROSS_TERMS = "capri"`): cross terms only between two crops of CAPRI's groups (OFOD mapped to FARA as CAPRI's OFAR), linear terms recalibrated so the base calibrates. tools/check/pmp_cross_term_check.py (CAPRI's decomposition experiment): six regions at +20% on the cereal prices, every group's response within 0.06 points across CAPRI's structure, the previous one and the diagonal only - with capri-mod's caps (|term| <= 0.05 sqrt(Q_ii Q_jj), rows at most half their diagonal) the cross terms are too small to matter. **CAPRI's own 2030 terms in hand** (21 October 2026, exported by the project lead: tools/gams/export_pmp_2030.gms, tools/build/build_pmp_2030.py, tools/build/build_pmp_capri_2030.py; docs/PMP_CAPRI_2030.md): `SupplyModule.pmp_source = "capri2030"` (run script `--pmp capri2030`) puts CAPRI's crop matrix (technology terms collapsed per crop, group terms on the groups' levels, at full size) into every region at the 2030 market year; the default since 22 October 2026 (the project lead's decision); capri-mod's own calibration with CAPRI's recipe as `--pmp recipe` (tools/build/build_pmp_recipe.py; Farm-to-Fork deviation 4.75 against 4.62 with CAPRI's terms and 5.30 with the elasticity calibration). Austria's crop supply elasticities with CAPRI's terms are close to CAPRI's own simulated ones (rapeseed 9.7 against 12.4, barley 3.0 against 3.4; elasticity calibration 2.6 and 0.9). Animals' herd terms, feed slopes and the land market's 2030 terms covered (21-22 October 2026, night), the intensity splits' curvature at 2030 too (22 October 2026, afternoon: tools/build/build_intensity_q_2030.py). The recipe (22 October 2026, afternoon) carries CAPRI's land-nest adjustment (p_landNestElasContrib, posterior land-type elasticities recomputed from CAPRI's land matrices) and 14 years of inflation at 2017 (inferred from CAPRI's CAPREG terms): within 5% of CAPRI's terms 80.5% at 2030 and 89.6% at 2017 (76.8% and 87.1% before); remaining differences in docs/PMP_CAPRI_2030.md

<a id="k62"></a>
### K62: Member states' milk price step: CAPRI's step weights tried and not kept (21 October 2026)

CAPRI's price forecast passes the weighted average of the last iterations' prices to the supply models (define_stepWeights.gms: 0.55 / 0.30 / 0.15). Applied to the member states' raw milk prices (option `milk_ms_step = "capri"`) in a full Green Deal 2030 run (r73), Spain's milk signal swung between +0.32 and -0.21 and its gap was still 0.34 at the 9th iteration (0.03 at the 6th with the adaptive step, r71): the weights average market prices that themselves swing with the herd, a cobweb they do not damp; the adaptive step halves its weight on every reversal. **Departure from CAPRI, kept**: the adaptive step (default `milk_ms_step = "adaptive"`). The remaining two-cycle of Portugal's milk price (r71, gap 0.005 / 0.03 alternating) is reported, not fixed

- **Effect:** iterations of the Green Deal run
- **In 9t:** –
- **Status:** **superseded**: since the K75 fix CAPRI's price forecast is the default for every price, member-state milk included (outer_loop.price_update "capri", 26 October 2026; r140, r142 converge); the separate milk option `milk_ms_step` was removed on 27 October 2026 (the adaptive step stays with price_update "adaptive")

<a id="k63"></a>
### K63: Ammonia options: costs per model head instead of per animal place, and poultry's costs per animal instead of per 1000 animals (found 21 October 2026, while adding Norway's pigs)

(1) CAPRI prices its ammonia options per place, places = activity level x DAYS / 365 in CAPRI's units (GHG_Mit_Cost_); `stock_factor` in ammonia_tech_model.csv is DAYS / 365 per CAPRI level unit. The model applied it per model head, while the N an option saves is per model head (manure N per head): where the model's heads differ from CAPRI's level units (capri_level_ratio: fattening pigs ~0.5, bulls ~0.4, heifers ~0.2, fattening sheep ~0.5, poultry 250-1000) the options cost ratio x CAPRI's per unit of N saved (DE11 fattening pigs: 294 thousand places from the model's heads against CAPRI's 604). (2) CAPRI's unit for hens and other poultry is 1000 animals; ammo_tech.gms multiplies the per-animal investment of housing and air purification (l. 153-157) and every extra input demand (l. 640-643) by 1000 for them; tools/build/build_ammonia_cost_curves.py did not, so poultry's housing and air-purification costs were 1000 times too low per CAPRI unit. For poultry the two errors largely cancelled (their options stayed at CAPRI's initial shares); for cattle other than cows and pigs (1) did not: at the 2030 baseline bulls' and heifers' shares were up to 0.37 off CAPRI's initial shares (DE94 bulls' covered storage 0 against 0.37)

- **Effect:** adoption of the ammonia options at base and under N targets (Farm-to-Fork, Green Deal)
- **In 9t:** yes
- **Status:** **fixed** 21 October 2026: `RegionalSupplyModel._manure_techs` divides stock_factor by the animal's capri_level_ratio (one place for the conic and NLP forms); the builder applies CAPRI's x 1000 (ammonia_technologies.csv and ammonia_tech_model.csv rebuilt: only HENS / POUF and LAYS / BROI rows change). At the 2030 baseline (FRH0, DE94, NL22, ITC4) every non-poultry share is within 0.04 of CAPRI's initial share (before: 0.37), poultry housing and air purification at theirs. Poultry's storage covers and spreading options left their initial shares at the baseline (up to 0.43, ITC4 broilers' covered storage, CAPRI 0). **Cause found and fixed** 22 October 2026 (afternoon): not the costs. CAPRI's simulation adds costsavings0 to each option's linear cost term (ammo_tech.gms l. 3366-3379: the marginal v_Miti.m of its calibration run with the shares held at the initial ones, set_miti_bounds.gms l. 160-176), so each option's marginal net cost at its initial share equals its marginal benefit there, and CONOPT, starting at the calibrated point, stays. capri-mod's NLP calibration nets the same residuals (CapriRegionalNLP.calibrate, dabat; checked: ITC4 residual 1.4e-9), but with the poultry options' small slopes against the N they keep, the base is a saddle along the options' joint direction (storage cover x spreading through the N reaching the field), and IPOPT's interior start left it. Now, as the conic form does (techs left out without an N row, re-solved without them when the row is slack): `RegionalSupplyModel.amm_fix_without_policy` holds the options at their base shares in a regional NLP solve without a policy incentive on N (no N-surplus row, no mineral cap, no emission tax) and re-solves with them held where the N-surplus row is slack. At the 2030 baseline every option in ITC4, DE94, FRH0, NL22 at its initial share (before: poultry up to 0.43 off, others up to 0.04). Under a policy incentive the options move as before. Tests: `test_ammonia_option_cost_is_per_place_of_the_models_heads`

<a id="k64"></a>
### K64: Market reported 'not converged' at a residual of about 1e-6 (21 October 2026)

The bilateral market stops at a largest relative excess-demand residual of 1e-7 (`_solve_bilateral`, tol); in the Farm-to-Fork and Green Deal scenarios its last rounds stay at 1e-6 to 3.5e-6 (TOBA, SUNF: tobacco and sunflower seed, thin markets) after 100 rounds (raised from 60), so the run summary says 'MARKET NOT CONVERGED: [scenario]' while the outer loop converges (prices and quantities move by less than its tolerance). A residual of 3.5e-6 of a market's volume does not change any reported figure at the precision reported

- **Effect:** the flag in the run summary
- **In 9t:** –
- **Status:** **fixed** 22 October 2026 (afternoon): not a thin market's slowness. Traced in a Farm-to-Fork run (tools: the bilateral trace by region): the whole residual sat in Norway's tobacco row - Norway's supply models returned 6.4e-6 kt of tobacco (the solver's interior on an activity without a base level), and Norway has no base production, so no trade flow could take it (S - flows = 6.4e-6 for ever). CAPRI has no variable for an activity without a level at the calibration point (v_actLevl only where p_technFact is set); `RegionalSupplyModel.absent_output_cleared` reports the solver's residue on such activities (|level| <= 1e-4) as zero. A bound row holding them at zero was tried first and dropped: it degenerated the fertiliser block of the NLP form (EL62 fell back to the conic form, eleven regions relaxed their mineral caps, the run took 82 minutes). Farm-to-Fork r86: the market converged in every scenario solve, no flag; 12 iterations, 32 minutes

<a id="k65"></a>
### K65: Cattle member splits and per-sex young-animal markets do not converge yet (22 October 2026)

CAPRI optimises its replacement heifers (HEIR) and its calf activities (CAMF, CAFF, CAMR, CAFR) on their own, and clears young animals per sex (INPANI_: male and female calves, young bulls and heifers). Both were built (split columns per CAPRI activity with bound rows and PMP block E' diag(q) E; per-sex balances; tools/build/build_cattle_intensity.py, build_young_animals.py, build_animal_pmp_capri_2030.py --splits), but in the Farm-to-Fork 2030 run the young-animal markets did not reach their tolerance (0.005) in 25 outer iterations: r89 diverged (male calves x 8, female -1); with the splits' response added to the price update (r90) the imbalance fell only from 0.052 to 0.033 in 6 iterations, the male-calf price creeping up 4% an iteration; a Broyden update of the price Jacobian (r91) made every good oscillate; an own-response scaling (r92) left the imbalance at 0.035-0.05. Cause: the price update predicts the supply response from the PMP terms alone (Q^-1), which ignores the constraints that bind (feed, land, N, the split members' bounds)

- **Effect:** the model's default leaves them off (`RegionalSupplyModel.use_cattle_member_splits = False`; pooled young-animal markets and the animals' herd terms of the intensity pairs, the validated state of r86 / r87); with them on, results are not usable
- **In 9t:** –
- **Status:** **open**, narrowed 23 October 2026 (night). The price update now takes each region's response from its solved NLP (`CapriRegionalNLP.response`: the implicit-function theorem on the KKT conditions, in the active rows' null space; `RegionalSupplyModel._yani_response`), on by default with the member splits. Checked: against finite differences on FRH0 the cattle goods' own responses agree within 1% (piglets within 20%); a price change reaches the regional objective as predicted. On 12 regions the markets reached 0.005 in 8 iterations (PMP terms: 0.016 after 8). The full Farm-to-Fork run (r96) still did not converge: the male calves' price rose to 6.1 x base and the female calves' fell below zero (-0.37) before the imbalance swung back up (0.03 -> 0.21). Under Farm-to-Fork the EU is short of male calves (fewer dairy births, fattening barely lower) and the calf activities hit their zero bounds, so the response nearly vanishes and the sexes' prices run apart. Next: compare the per-sex calf use and its flexibility with CAPRI (the calf activities' own PMP terms, CAPRI's per-sex young-animal prices in its Farm-to-Fork results, tools/gams/export_capmod_results.gms) before judging whether such prices are CAPRI's equilibrium or a defect here. Off by default. **Deferred, 23 October 2026**: CAPRI's own per-sex Farm-to-Fork results, needed to judge the prices, do not exist on the project lead's installation; it stays a DEPARTURE from CAPRI's setting (docs/DEPARTURES_FROM_CAPRI.md) until the divergence is understood from the model itself (the calf activities at their zero bounds).

<a id="k66"></a>
### K66: Farmland expands under the per-hectare N target more than in CAPRI (found 23 October 2026)

The Farm-to-Fork N target is per hectare of current farmland, as CAPRI's e_SURTOTHa (supply_model.gms l. 1463-1475 with e_MINFERT l. 1289: the surplus items divided by the land types ARAC, FRUN, GRAS), so an extra hectare dilutes the surplus and the land market supplies it. EU UAA +5.3% (r94) against CAPRI's +3% (JRC121368 sect. 5.1.1: set-aside 1.5, nutrients 0.8); in regions where the target binds at a very high price the expansion takes all forest and other land (BE33 +71%, N dual 2235 EUR/kg; BE32 dual 4.6e5, NL23 6.6e5). FRH0's set-aside 5 -> 708 kha is this: +243 kha of land, all set aside. JRC121368 capped nine regions at the EU average cut where its model was infeasible; the model caps the nine highest baseline surpluses and relaxes any region where its NLP fails, but BE32, BE33, BE35, NL23 are feasible here only through land conversion

- **Effect:** land use, regional N surplus and herds in the regions concerned; EU UAA
- **In 9t:** –
- **Status:** **open, waiting for CAPRI's scenario results** (the project lead's decision, 29 October 2026: kept open with its reference). Needed: CAPRI's Farm-to-Fork 2030 regional results for land use: per NUTS2 unit the land types (ARAC, GRAS, FORE, OLND, the land market's p_aLU / v_landTypes levels) and the land rents; to be exported with tools/gams/export_capmod_results.gms (run on a CAPRI installation where the scenario was solved); the project lead's installation has none of them so far. Before: **open**. CAPRI's regional Farm-to-Fork results do not exist on the project lead's installation (23 October 2026), so the comparison planned here cannot be made. Checked instead (r97): the expansion is broad, not from the capped or extreme regions (regions with N prices of 1-10 EUR/kg give +3.1 of the +6.0 points of the land types' farmland, regions above 100 EUR/kg 0.7); forest falls 16.7 Mha (about 10 to farmland, 7 to other land, through the cross terms of CAPRI's own 2030 land-type matrix); the land market is CAPRI's Trustee_land form with ARTIF fixed and the total-land row an inequality (both would make it expand less). Next: the share of the landscape-feature floor and of the N target, by runs without each (tools/run/run_f2f_2030.py --targets lndscpTarg=0 / surpRedu=0)

<a id="k67"></a>
### K67: Breeding options without CAPRI's maximum share (found 23 October 2026)

CAPRI caps every breeding option (GENET_YLD, GENET_EFF, GENET_REP) at MaxShare 0.002 unless %fixGenet_eff_to_iniValues% is off (envind/breeding.gms l. 65-77; only CAPRI's agora policy files set it off) and lowers it to the max calibration run's level where smaller (l. 375-379; that run holds 0.001999 for GENET_EFF everywhere). tools/build/build_genetics_effects.py used MaxShare 1, so under Farm-to-Fork higher ruminant efficiency covered 79% of non-dairy ruminants (JRC121368 Table 17: 9%)

- **Effect:** adoption of genet_eff and genet_yld
- **In 9t:** –
- **Status:** **fixed** 23 October 2026: column max_share in genetics_effects.csv, applied by the endotech setting fixGenetToIni (1 in star 3.0's and the JRC121368-era reference files, as CAPRI's default). Effect (r97, Farm-to-Fork 2030): higher ruminant efficiency 0.2% (was 78.7%), higher milk yield 0.0% (was 15.5%, Table 17 15%); mean deviation from JRC121368 4.97 (was 4.62), mostly the milk price (+25.2 against +20.9; CAPRI +1.5) and enteric methane (-10.6 against -11.9; CAPRI -14.6). JRC121368 Table 17's genomics shares came from an earlier CAPRI version without the cap; with the setting off (fixGenetToIni 0, as CAPRI's agora files) the earlier results return. Also found on the way: the builder read the cattle file's member-split rows for the heifers' eligible share (0.97 instead of 0.13); it now reads the intensity pair's row only (the delivered file was built before those rows existed, so no run was affected). Sub-items fixed 23 October 2026 (late): (F2) the options' PMP slope nets CAPRI's cost-saving drop between its ini and max calibration runs, max[floor c, c (relSubs1 - relSubs0) - (costsaving0 - costsaving1)] (breeding.gms l. 447-458, low_n_feed.gms l. 265-272, line_nitr.gms), the drop from CAPRI's runs per model head (column dsav of genetics_, lownfeed_ and supplement_effects.csv; tools/lib/_capri_costsavings.py; `RegionalSupplyModel.use_option_costsaving_drop`); the former registered deviation had its reasoning reversed (leaving the drop out counts the model's own curvature on top of the planned slope); (F3) CAPRI's cost floors (2 and 20 EUR) are per animal place, now converted per model head (stock factor / capri_level_ratio, as the ammonia options, K63); (F4) adoption of the animal options reported as share of the eligible herd in livestock units (CAPRI's LEVW; livestock_units.csv), baseline from the baseline run, the MaxShare ceiling shown (results['adoption_lu'], tools/check/compare_runs.py). Effect: see CHANGELOG 23 October 2026 (late), runs r99 / r100

<a id="k68"></a>
### K68: A bare SupplyModule.run did not reproduce the base (found and fixed 23 October 2026)

In DE11 it gave 71.3 kha of wheat against a base of 91.2. Cause: the land market charged CAPRI's calibration rents on the land columns (the land rows' dual at the base is the rent), but the activities' linear terms were calibrated without that rent. Until the proxy removals, a 1% shadow-price stand-in and recovered duals had hidden this. The NLP form recalibrates its linear terms at the base and absorbed the difference, so model runs reproduced the base; the plain path, without rations, did not. Fix: the activities' linear terms carry rent x land use, as in CAPRI's first-order conditions at the calibration point (prep_cal.gms, cal_land_nests.gms; RegionalSupplyModel._land_augment). The bare solve now reproduces the base: DE11, DE14, FRH0 and ITC4 are within 0.01 kha on every crop

- **Effect:** –
- **In 9t:** –
- **Status:** **fixed**. The NLP form's calibrated linear terms are pinned by the base, so model results should not change; the next reference run checks this

<a id="k69"></a>
### K69: Activities with no base level entered freely, and the Farm-to-Fork 2030 runs stopped converging (found and fixed 23 October 2026)

r103 and r105 stopped at 25 iterations, with the EU sugar price cycling with period three. The traced run r107 showed Estonia's sugar beet (no level in CAPRI or the base; an unsourced 500 t/ha yield) jumping from 0 to 171 kha. In r105, 88 zero-level activities entered, against 19 in r101. Cause: once the literature elasticities were removed, a zero-level activity without a CAPRI elasticity had only the inert curvature 1 and, with absent_activities_fixed = false, no bounds. Fix, CAPRI's rule that an activity without a level has no variable: absent_activities_fixed = true is now the default. Two inconsistencies that had made the NLP fail with it were fixed: (a) the crop-diversification index took the logarithm of fixed columns (NaN in 24 regions); (b) the permanent-grassland rule applied to a grassland of 3.5e-11 kha (EL62-64 infeasible); both now use the same threshold, ABSENT_LEVEL. The EE00 SUGB yield was set to 0. Reference run r110 (default settings): converged in 11 iterations (27 min), no conic fallbacks. Against r101, every EU aggregate is within 0.8 points

- **Effect:** Farm-to-Fork 2030
- **In 9t:** –
- **Status:** **fixed** (see K71 for the mineral caps)

<a id="k70"></a>
### K70: Data files that no builder reproduces as they are (found in the tools inventory, 23 October 2026; fixed 24 October)

Four cases: (1) `supply_elasticities_regional.csv`: it is CAPRI's PELA 2005 own-price slice (`sources/estnlp/pela_own_price.csv`) with CAPRI's upper-bound rule, cell for cell; new builder `tools/build/build_supply_elasticities_regional.py` (`--check`: reproduced). (2) The files patched in place by several builders: new driver `tools/build/build_patched_inputs.py` runs build_crop_economics_2017, build_eu_producer_prices, build_animal_yields, build_dairy_trade_params, build_demand_elas_capri, build_feed_byproducts, build_feed_demand_nonEU in that order (feed_demand_nonEU must follow feed_byproducts, which resets FENI/FPRI); `--check` on a copy reproduces yields.csv, producer_prices.csv, armington_params.csv and every other file the steps write (values within 1e-9). (3) `manure_n2o_tech.csv` rebuilt with build_manure_n2o: the old file lacked 29 AirPurCovHigh rows for pigs in 15 EU regions (BE10, CZ01, DE30, DE50, DE60, DK01-05, ES63, ES64, FI20, LT01, LT02) that ammonia_tech_model.csv offers; every other row equal; the Norway guard in build_norway_pigs is now empty. (4) `compare_qp_solvers.py` wrote to the repository root (fixed: capri_data/validation/). Not covered by any builder (see K72): 146 of armington_params.csv's 248 cells and the livestock rows of producer_prices.csv

- **Effect:** reproducibility of these inputs
- **In 9t:** –
- **Status:** **fixed** (the rest under K72)

<a id="k71"></a>
### K71: More regions needed the Green Deal mineral-fertiliser caps relaxed (found 23 October 2026; fixed 24 October)

r110 relaxed every cap to 1.1 x base in FI19, FI1C, BG32, BG33, BG34, BG41, BG42, HR03, HR04, LT01 and widened the duals in NL12. Cause, traced in BG33: the organic area target. CAPRI's organic_minfert_redu.gms caps each crop group's mineral N at baseline x (1 - the group's conversion); Bulgaria's permanent-crop target is 79.5 points (CAPRI's organic_targets.gdx, PECR), so PERM's cap falls from 10.4 to 2.1 kg N/ha, while its need net of own residues is about 7 kg/ha effective N and its manure prior is near zero (0.002 kg/ha, so the manure flow's bound, 1000 x the mode as CAPRI's prep_sim.gms, allows about 2 kg/ha). The group's need is out of reach whatever the duals. Relaxing PERM alone makes BG33 solve; no other group does. The same holds in CAPRI's own structure (same priors, bounds and targets); CAPRI's runs handle such cases with hand-listed exemptions (minfert_redu_by_crop.gms, p_checkSmallMine, PERM among them in IT31, EL24, PT18). Why r101 did not need it: with absent activities free (absent_activities_fixed false), zero-level permanent crops in the PERM group (CITR, OLIV, TABO in BG33) could enter with no need and enlarge the group's capped area. Fix: the blanket 1.1 x relaxation is gone (caps_relax_factor removed); after the widened duals, groups are exempted one at a time, those whose need is out of reach first (_nlp_cap_shortfall), at their baseline (fertiliser.exempt_cap_factor = 1.0, CAPRI's no-backsliding level), with CAPRI's duals first, and the set pruned to the smallest that solves. Single-region Farm-to-Fork tests: PERM in all BG and FI regions; PERM+ROOF in HR04 and LT01; PERM+PULS+ROOF in HR03 (before pruning); NL12 none

- **Effect:** mineral N on the exempted groups
- **In 9t:** –
- **Status:** **fixed**; full-run result: r111 (CHANGELOG 24 October)

<a id="k72"></a>
### K72: armington_params.csv: cells without a builder (found 24 October 2026, K70 check)

With every cell blanked, the builders refilled 102 of 248. The eta column (a generic demand elasticity, round numbers of unrecorded source for about 30 products) was removed on 24 October 2026 with the files that only it needed (eu_demand_elas_overrides.json, fao_demand_own_elas_eu.json, tools/build/build_demand_elas_capri.py): the market's demand is CAPRI's Armington balance (HCON + FEED + PROC + BIOF, each with CAPRI's function or fixed), so no generic elasticity is left (audit M2). The sigma and rho2 columns were removed the same day: the market reads CAPRI's p_rhoArm1/2 from armington_rho.csv, so they were unused. The file now holds eps only (EU market supply where CAPRI's EU p_elasSupp file has no value, PROXY_AUDIT S176 note); eps of about 30 products has no builder; also without a builder: the livestock rows of producer_prices.csv

- **Effect:** EU market supply (eps) where used
- **In 9t:** –
- **Status:** **fixed** 29 October 2026 (batch 5): the last inputs without a builder, the ten livestock rows of
  `producer_prices.csv` (DCOW 869.4, BCOW 844.05, BULL 1400, HFRS 900, CALV 300, PIGS 905, PIGF 844.72, LAYS 688.2, BROI
  748, OANI 8; origin not recorded), removed: no model code reads an animal's EU producer price (the supply models'
  livestock revenue is CAPRI's output value per head, `livestock_output_value_coef.csv`, and replaces price x yield
  for every animal; the other readers take crops only), to be confirmed by the batch's gate runs. ("The last inputs without a
  builder" held for the cells of armington_params.csv and producer_prices.csv only: a census of every file a run reads,
  K101, found 17 more.) Earlier steps: eta,
  sigma, rho2 removed 24 October 2026; eps and the file removed 29 October 2026. eps acted
  on no result: it was read only for the EU rows of the 28 products without CAPRI's EU p_elasSupp, and every one of
  them has its EU supply set afterwards in the same market step (PARI, SUGR, WINE, OLIV by CAPRI's market supply
  function, the measured Hessian; oils and cakes by crushing; the dairy products by the dairy block; BIOE, BIOD, DDGS
  by the biofuel block; FENI, FPRI by MaprFeed_) or has no EU production (PLMO, COFF, TEAS, COCO); a mini-EU run with
  eps doubled equals the run without, to the last digit, in every regional activity and price. Those products now get
  no own-price anticipation in the EU rows (MarketModule.supply_response); armington_params.csv, its loader and
  build_dairy_trade_params (which wrote only eps, for the regions without a dairy block, the four empty regions of
  K45) removed, build_feed_byproducts writes no eps. Left: the livestock rows of producer_prices.csv without a builder

<a id="k73"></a>
### K73: Market: differences from CAPRI that no register listed (CAPRI-claim audit, 24 October 2026)

Ten findings M1-M10 in docs/design/ARCHITECTURE_REFACTOR.md section 5.1 (table docs/design/audit/market_claims.csv). Largest likely: M1, consumer, processing and crushing-margin price changes formed on dom0 (world price x (1 + AVE)) instead of CAPRI's Arm1P0 / PPRI0 (Cpri_, ProcNQ_, ProcMargO_); M2, EU-average FAO_agg own-price elasticities replacing the non-EU p_ElasDem in every region; M3, non-EU feed demand without CAPRI's FeedNQ_ and energy balance. Smaller: EU feed bulks and raw milk fixed within a market solve (path only), Norway's feed rho above CAPRI's cap of 2.0, welfare reported in EUR million labelled billion, the crushing floor called ProcFudge_, dairy processing fixed, tariff changes on the exporter price only

- **Effect:** market prices and quantities in scenarios (M1-M3, M6, M9, M10); reporting (M7)
- **In 9t:** –
- **Status:** **fixed** (29 October 2026, batch 6 gate: every finding M1-M11 fixed and run). History: Fixed 24 October 2026: M1 and M8 (run r112), M2 (r113, the Armington balance), M11 raw milk cleared per region (r115, added to the audit), M6 (r117). Fixed 24 October 2026 (evening): M10 (tariff on price + transport per importer region), M7 label and base price; M5 implemented (raw milk per member state inside the market), run pending. M7's welfare report ported 27 October 2026 (docs/WELFARE.md; reporting only). M9 (dairy processing as CAPRI's ProcNQ_) fixed 28 October 2026 and accepted with the gate of batches 2 and 3 (r181). M3 ported 29 October 2026 (the project lead's decision of that day: arm/feed_conv.gms ported; CAPRI's FeedNQ_ and FeedBal_ in the market, market.noneu_feed_nq; batch 6), run pending. M4 (path only). M4 implemented 29 October 2026 (batch 6: CAPRI's feedBlk_ in the market, market.feed_bulk_in_market; the elasticities from the market supply Hessian's FEEDBLK rows), run pending
  Gate of batch 6 (29 October 2026): M3 and M4 run in Farm-to-Fork 2030 (r188: converged in 10 iterations; prices up to +0.9 points from r186, quantities within 0.3) and Green Deal 2030 (r189: converged under CAPRI's rule in 21 iterations; prices up to +0.4 points from r187, mean absolute deviation from JRC121368 8.63 against 8.65). Closed
  Batch 8: step F (Norway's raw milk inside the market, market.sup_milk_in_market; the baseline demand recalibration
  registered) and the claims table's 17 unsourced rows resolved (four removed as dead code, the rest registered as
  fallbacks, guards or numerical devices); step F's results with the batch-8 gate runs

<a id="k74"></a>
### K74: Supply: differences from CAPRI that no register listed (CAPRI-claim audit, 24 October 2026)

13 findings S1-S13 in docs/design/ARCHITECTURE_REFACTOR.md section 5.1b (table docs/design/audit/supply_claims.csv). Largest likely: S1, the animals' feed-cost change counted twice with feeding inside (net revenue and the NLP's feed purchases); S2, organic and mineral caps merged by min() where CAPRI's crop-specific mineral reduction overrides the small groups; S3-S4, the organic and pesticide other-input cost rules; S5, the fertiliser and inhibitor options' cost base and slopes

- **Effect:** livestock in every scenario (S1); Green Deal crop and fertiliser results (S2-S12)
- **In 9t:** –
- **Status:** **fixed** (closed with the batch-8 gate, 30 October 2026). History: fixed 24 October 2026: S1 (run r114). Implemented, not yet accepted (runs r116, r117 do not converge in 25 iterations, see K75): S3-S4 and the plant-protection / other-input part of S11 (CAPRI's regional input changes on every activity, the organic crops' fuel top-up, CAPRI's organic crop set; two CAPRI code errors corrected with parity switches, DEPARTURES_FROM_CAPRI; the other-input cost per ha was about 20% low, without its unit value). Fixed 24 October 2026 (evening; run pending): S5 (the options' cost on the N purchases, CAPRI's curvature with the saving term), S6 (need follows yield as fertned.gms, not sqrt), S7 (yield-dependent inputs, define_inputs.gms), S8 (the grassland rule's calibration dual), S9 (catch crops on the ecological set-aside row), S10 (idled histosols on the landscape floor; the diversification limit lowered under the floor). Fixed 27 October 2026 (branch supply-audit, run pending): S12 (the mineral N tax and soil N2O on CAPRI's MITERRA loss fractions). S13 (the elasticity calibration path) removed 28 October 2026; S12 and S13 accepted with batch 1 (runs r177, r178). Fixed 28 October 2026 (batch 2): S2 (CAPRI's small groups keep the mineral reduction's cap, replacing the organic one). The claims table brought up to date with S1-S13 (28 October 2026). S5's last part (28 October 2026): the inhibitor on manure's saving term added behind supply.fert_slope_with_saving, off as the mineral options' (K77 departure); its maximum share found in CAPRI (ghgMiti.gms l. 115-119). The PMP calibrator's elasticity cap and share term reach only 14 cells (set-aside below 50 m2 in Belgian and Dutch regions). Open: the pesticide yield-loss crop list (S11, jrc121368 rule only) **29 October 2026 (batch 8, K74 review):** S11 fixed: the pesticide yield loss on CAPRI's pesticideCrops (every crop activity but the idled histosols, conventional_io.gms l. 51-53) instead of an unsourced 23-crop list, the fodder crops and set-aside not reached (registered); the claims table's 19 remaining unsourced or unverifiable rows resolved: three fallbacks no unit reached removed (over-fertilisation factor, active technologies, the applied manure P/K ratio: now errors), the winter cover bound CAPRI's MaxShare (equal in every unit), the PESETA and yield-gap maps verified (CAPRI's own CEN fallback), the crop-diversity groups verified (OFOD = OFAR + ROOF one group, registered), the rest registered as guards, solver devices or reconciliations with their reasons. Closed with the batch-8 gate (30 October 2026: Farm-to-Fork r190 converged in 13 iterations, Green Deal r191 in 22; no non-optimal regional solve kept)

<a id="k75"></a>
### K75: The Farm-to-Fork runs with CAPRI's Green Deal input changes (S3/S4) did not converge: a warm-started NLP stuck at a worse point (24 October 2026)

Runs r116 (S3/S4) and r117 (S3/S4 + M6) stop at 25 iterations with Portugal's member-state milk gap at 0.0055 (tolerance 0.005). The trace (r117t) and a per-solve dump of Brittany (r117e, CAPRI_NLP_TRACE=FRH0) show the cause. At the 10th scenario iteration the warm start (IPOPT from the previous primal-dual point, small barrier) ended at a worse stationary point of Brittany's non-convex problem (per-head feeding): pigs, broilers and hens at their lower bounds, dairy cows 473 against 691 thousand, objective 9% worse, reported Solve_Succeeded. Every later warm start stayed there. A cold start solves each of those problems to the other optimum (final iteration: dairy cows 705, objective -6.394e7 against -5.858e7 kept); from ten starts the final problem has one optimum. The French and Portuguese milk loops restarted from the jump and Portugal's then drifted with the beef price. The S3/S4 input changes made the jump happen but are not its cause

- **Effect:** r116, r117 not usable as results
- **In 9t:** –
- **Status:** **open, narrowed (24 October 2026).** Done: CAPRI's structure, market.market_supply_nq = true and young_animals.in_market = true (the young-animal markets cleared inside the market with the products, through the market supply functions with young-animal rows and columns, measured once per baseline: 50 shocks, 49 min, cached). Found on the way: raw milk's ratio in the trade system is the pooled world ratio, not the dairy price the supply models see; through the Hessian's milk column it held the young-animal markets off balance (now taken at the models' price, MarketModule.NQ_PRICE_AS_SEEN). Run r123: the young-animal imbalance falls to 0.0004 by the 15th iteration (r119: stuck at 0.001-0.002 with the calf price rising every iteration) and the beef signal reaches 0.191 there (fixed point about 0.197-0.199); at the 25th iteration the results equal r119's within 0.1 point. Still not converged: Portugal's member-state milk gap stays at 0.0053-0.0068 (its signal and target falling together by about 0.003 an iteration), and from the 15th iteration the calf price creeps again (+0.001 to +0.006 an iteration, imbalance 0.0004 -> 0.0026) while a few regions move every iteration (BE32 calves, BE33 suckler cows, EL51). Diagnosed further (24 October 2026, evening): r124 (shocks at the final state) - Portugal's milk response is normal (+ dairy cows) and the EU calf response 5554 against the Hessian's 6169, so the market supply functions are accurate; r125 (regional herds in the history) - suckler cows fall linearly in FRK1, FRD1, IE04 and FRG0 (2-3 thousand head an iteration) at constant grassland; r126 (price_relaxation 1.0) - 'converged' in 13 iterations while still drifting (beef 18.8 against 19.8 at r123's 25th): a stopping rule on per-iteration changes, not a fix; r127 (the four drifting regions plus BE33, PT20, PT11 re-solved six times at the final prices) - identical to 3 decimals (PT11 suckler cows 42.220 -> 42.218): no solver creep. The drift is the outer loop's own slow mode (the anticipated responses against the young-animal and member-state milk prices), not the regional solves; next: the outer loop's update of those prices (M5's raw milk in the market solve is a candidate for Portugal's loop). 25 October 2026 (runs r129, r130; M5 on, the Hessian measured from the baseline's state, K76): the convergence tests are now recorded per iteration (outer_history[...]['conv']). From the 9th iteration every test passes except the member states' milk gap, 0.0052-0.0055 against 0.005, held by Portugal alone: each iteration its dairy-block price comes out 0.0053 below the price its models saw, the signal falls 0.0026, and the next block price again 0.0053 below. Portugal's delivered milk rises (0.905 -> 0.920 of base, iterations 9-25) while its milk price falls (1.434 -> 1.392): the Azores (PT20) add dairy cows (63.5 -> 68.6 thousand) against the falling milk price, the other Portuguese regions shed a few. With the EU's suckler cows falling about 12 thousand per iteration and the young-animal imbalance held at 0.0015-0.0017, this looks like the cattle sector's slow mode (calves scarce, dairy cows the calf supply) seen in Portugal's small dairy block, not a milk-price loop of its own. The mechanism, measured in r130 (iterations 14-25): the EU calf market stays short by 24-38 kt (net - reference, of about 22,500 kt), and the market raises the calf price by about 0.005 of base each iteration; the supply models' calf net balance then moves by -1 to +11 kt, where the Hessian's own response (6,168 kt per unit of price ratio, measured at the baseline) predicts about 30 kt. The realised response is 0-10% of the measured one (young cattle and replacement cows likewise), so each iteration the market clears a gap that the models do not close, and the calf price creeps with no end in 25 iterations; the imbalance itself (0.0015-0.0017) is inside its tolerance. CAPRI clears the same way with a fixed p_hessNQSupp, so a gain mismatch of this kind would show there too (not checked). Options, for the user's decision: (a) a secant correction of the young animals' own response from the observed responses (beyond CAPRI); (b) the Hessian measured again at the scenario's state (CAPRI measures it once per baseline); (c) accept, with Portugal's milk test (0.0052-0.0055) reported. 25 October 2026, option (b) tested (run r132, market.hessian_scenario_iter = 8; r131 discarded, the Hessian was not built, see CHANGELOG): the Hessian measured again at iteration 8 (62 min) changes the calves' own response by -10% (6,232 -> 5,626, as r124) and calves x beef from -1,278 to -3,040; the run is r130 again within 0.003 of the calf ratio (1.5903 against 1.5897 at the 25th iteration), the calf price creeps +0.004-0.005 an iteration from the 13th, Portugal's milk gap 0.0052-0.0053: not converged. (b) does not fix K75: the market's supply function is close to the models' response to a calf price shock, the realised response inside the loop is not. Lead, seen again in r132 (iterations 12-25): the EU's suckler cows (BCOW) fall 8,571 -> 8,417 thousand, about 12 thousand an iteration, and calf fattening (CALV) 18,958 -> 18,881 from the 15th, while the calf price rises 1.542 -> 1.590 and beef 0.1375 -> 0.1435: the cow that sells calves shrinks as calves become dearer; cause not yet known (a wrong-sign response or another term moving each iteration). Remaining choices for the user: (a), (c), or a diagnosis of the suckler-cow response first. 26 October 2026: (b) back off (market.hessian_scenario_iter = 0, CAPRI's); the user chose the diagnosis first (run r135 traces FRD1, FRK1, IE04), the comparison of CAPRI's price averaging (r136, r138) and CAPRI's stop rule recorded every iteration; a secant/Anderson update of the supply-market fixed point was tried after the fix (r143) and removed: no iterations saved (docs/design/ARCHITECTURE_REFACTOR.md 6.0b). Diagnosis (r135, 26 October 2026; FRD1's NLP problems of iterations 12 and 25 from the trace, re-solved with one part of the problem from iteration 12 at a time): prices, limits and the nutrient data move FRD1's suckler cows by less than 1 thousand head; the constraint matrix moves them by 36.3 of the 35.8 thousand head lost, through the fodder band rows alone (FGRA +23.4, FMAI +10.1, FOFA +2.4). In the NLP form CAPRI's fodder balance SUPBAL_ is the equality with the feed columns (FEDUSE_); the conic form's other side, the '_band' row, stayed in the problem with the animals' fodder per head from the ration state, i.e. the previous solve's feeding (heifers' maize 21.93 -> 22.22 t per head over iterations 12-25, rising every iteration). It binds (slack 0), so each iteration's feeding tightens the next iteration's fodder constraint: a lagged constraint that CAPRI does not have, and a slow mode of the loop of its own. Fix: supply.nlp_fodder_band_dropped = true (the band rows dropped in the NLP form; false restores them); the base is reproduced exactly either way (5-region check). The market supply Hessian's cache key carries the setting. Full Farm-to-Fork run with the fix (r139, 26 October 2026): **converged in 12 iterations** (r135: not in 25), the EU's suckler cows stable at the end (-0.2 to -0.6 thousand head per iteration, before -12 to -38), Portugal's milk gap 0.0018, one Dutch region at JRC121368's relaxed target (before five); mean deviation from JRC121368 over 20 indicators 4.44 (r135: 4.83), with beef price +20.6% (CAPRI +24), beef animals -20.5% (-18), beef production -14.8% (-14), sheep and goats -10.7% (-9.5), cereal production -15.5% (-15), UAA +3.1% (+3); further from CAPRI: pork price +18.0% (+43, was +23.5), poultry -12.0% (-16.5). CAPRI's own stop rule would still go on at the 12th iteration (14 rows above 0.05%: Irish potatoes 2.7%, Latvian oats 1.3%, French olives swinging at some iterations): open as K79. **Fixed** (r139); the price-step comparison on the fixed code is under way (r140 onward)

<a id="k76"></a>
### K76: The market supply Hessian's measurement left the baseline's regional models in another state (found and fixed 24 October 2026)

The price shocks of `_market_supply_hessian` warm-started each regional NLP from the previous shock's solution, and so did the final base re-solve that was to leave the models as they came. In DE11 it ended at another stationary point of the non-convex problem (12 kt off; the next baseline 2% less wheat); the measured terms came from drifted points too

- **Effect:** a scenario run right after a measured Hessian (a run with a cached Hessian re-runs no shocks: r122-r127 not affected in their scenario's start; the Hessian they read was measured with the chained warm starts)
- **In 9t:** yes
- **Status:** **fixed** 24 October 2026: the regional NLPs' state (_nlp_*) and the N-price loop's state restored before every shock and after the base re-solve (DE11 re-solve 0.0035 kt off, the next baseline the calibrated base); the cache key carries the measurement, so every Hessian is measured again. Found by test_mineral_fertiliser_cap_binds / test_cap_support_not_double_counted, which failed when the Hessian was measured inside an earlier test's run

<a id="k77"></a>
### K77: CAPRI's fertiliser-option curvature (S5) leaves the baseline's base shares (found 25 October 2026)

With CAPRI's pmpParSqr including the fertiliser-saving term (ghgMiti.gms l. 1016-1035; negative in 96 region-options, mostly precision farming with NMIN about 0.5) together with the options' cost on the N purchases (GHG_Mit_Cost_), the 2030 baseline leaves the initial shares: FR10 precision farming 0.44 (run r128: EU 9.6% at the baseline, 0 before). Either part alone keeps the base (FR10, DE11, PT11). In CAPRI's derivation the total cost (PMP term + the convex saving N0/(1+nmE m)) is stationary at both shares with a positive curvature at the initial share; in the NLP the saving runs through the fertilisation block (mineral, manure and residue flows), so the curvature there is not CAPRI's N0/(1+nmE m) and the base becomes a saddle

- **Effect:** Green Deal / Farm-to-Fork adoption of the fertiliser options
- **In 9t:** –
- **Status:** **open**: supply.fert_slope_with_saving off by default (the curvature without the saving term, as before); the cost on the purchases kept. Run r128 with both on: nitrification inhibitors 4.5% (r123 16.3%; JRC121368 Table 17 18%), precision farming 9.6 -> 25.0%

<a id="k78"></a>
### K78: Histosol fallowing under Farm-to-Fork far above JRC121368's figure (25 October 2026)

Run r129: 52.7% of the histosol area fallowed (r123: 21.7%; JRC121368 Table 17: 2% -> 9%). Since the S10 fix idled histosols count towards the landscape floor (CAPRI star 3.0's setaFallow includes iHisCr, iHisGr). The floor's dual is high: one-iteration landscape-only solves give 240-6,300 EUR/ha (DE94 239, NL13 490, FRK1 682, IE04 3,148, DE12 6,318), from CAPRI's own 2030 curvature of FALL + VSET (DE12: g 6,936 over a base of 10.8 kha, so about 640 EUR/ha per thousand ha more), against fallowing's CAPRI curvature of about 300-440 EUR/ha per unit share. Not a defect found yet: JRC121368 ran an earlier CAPRI version (whether its setaFallow held the idled histosols is not checked), and CAPRI's own Farm-to-Fork results with star 3.0 are not in hand. To check: the landscape floor (p_setAsideTarget x UAAR + SETF) and CAPRI's land-use options under it (prep_sim_luc.gms l. 599-607: forest's lower bound at 0.99 of its level when the floor is set)

- **28 October 2026, checked:** CAPRI star 3.0 counts the idled histosols in the floor (sets.gms l. 2265 setaFallow;
  supply_model.gms e_setaLandscape), with no histosol rule of their own in the Green Deal files (histomax is the AFOLU
  scenarios' switch only), so the model's rule is CAPRI's. The floor is CAPRI's formula (landscape.gms l. 54-57) on
  CAPRI's targets (landscape_targets.csv, same values). The histosol data reproduce CAPRI's: in CAPRI's maximum-mitigation
  run (scen_greendeal_2030, refpol_endotech_all_max; not a Green Deal targets run, it has no landscape floor) EU27 idles
  3,517 kha, against the model's maximum (MaxShare x histosol area on Green Deal 2030 land, r176) 3,532 kha, per member
  state within about 2% where CAPRI is at its maximum (DE 1,031 / 1,018, PL 950 / 970, NL 299 / 296, IE 296 / 296). The
  reference run idles none (res_2_1730greendeal_refdefaulta), as the model's calibration (IniShare 0). Still missing: a
  CAPRI star 3.0 run with the landscape floor (lndscpTarg > 0) to compare the share fallowed under it.
- **Effect:** Farm-to-Fork land use, histosol N2O and CO2, set-aside premiums
- **In 9t:** –
- **Status:** **open, waiting for CAPRI's scenario results** (the project lead's decision, 29 October 2026: kept open with its reference). Needed: CAPRI's Farm-to-Fork or Green Deal 2030 regional results with the landscape floor: per NUTS2 unit the histosol fallowing (the FALLOW technology's v_Miti levels) and the set-aside land; to be exported with tools/gams/export_capmod_results.gms (run on a CAPRI installation where the scenario was solved); the project lead's installation has none of them so far. Before: **open** (needs CAPRI's Green Deal or Farm-to-Fork result with the floor)

<a id="k79"></a>
### K79: Member-state production that keeps moving between iterations (26 October 2026)

CAPRI's stop rule, recorded every iteration since r135, flags rows that move by more than 0.05% between iterations in converged runs: Irish potatoes 1.2-2.7%, Dutch maize 1.5-2% (before the K75 fix), Latvian oats 1.3%, and French olives and table grapes jumping by 35-110% at some iterations. The model's own tests pass (they are on EU prices, quantities and price gaps), so these swings are invisible to them

- **Effect:** member-state production of a few crops; whether CAPRI-mod's runs would pass CAPRI's stop rule
- **In 9t:** –
- **Status:** **open**. Diagnosis of r161 (27 October 2026): (1) the rows still moving at the last iteration (Latvian 28 October 2026 (batch 1, r177): with the jump check (supply.nlp_jump_check 0.1) and S13 (the Swedish tomato cells held), Green Deal 2030 stops by CAPRI's rule after 18 iterations (r171: 30; the supply-audit run r174 without the jump check: not in 60). The recurring moves of r171 (Bulgarian maize and rapeseed, Hungarian pulses, 30% every few iterations; Swedish tomatoes up to 76%) do not appear; one single move left (Bulgarian oats, 85% at iteration 13). Which of the two removed which moves is not separated (the run did not record the jump check's action; recorded from batch 2: metadata nlp_jump_check, outer_history[...]["jump_check"]).
  oats 10.3, 5.1, 2.6, 1.1% at iterations 6-9; Portuguese potatoes, Romanian pulses) follow prices that converge
  geometrically under CAPRI's price forecast (the EU oats signal's steps 0.0036, 0.0020, 0.0010, 0.0004, 0.0002):
  slow convergence of the supply-market loop, not solver creep. The model's stop rule (prices within 0.5%) ends the
  loop before CAPRI's (production per member state within 0.05%; at r161's iteration 9, 14 rows above it, max 1.1%).
  (2) French olives and table grapes moved by 66% and 35% at iterations 4 and 5 only, back at iteration 6, and not in
  r160 (the same scenario): the four French olive regions' and two table grape regions' models respond smoothly to
  their price (sweep of +-0.6% in 0.05-point steps at base settings: largest step 0.01%), so not a kink of the regional
  model; cause not found (the region-solve warning added since r161 will show a failed solve if it recurs). CAPRI's stop
  rule made the default (the project lead's decision, 27 October 2026), with the model's inner balances settled as well;
  the next reference runs measure the iterations it needs. r163 (the same scenario and rule as r161, the Hessian skip
  and the K82 ammonia rebuild): the French jumps did not recur (largest change at iteration 4: 14.7%, r161 66%).
  r164 (Farm-to-Fork, CAPRI's rule): stopped by it after 12 iterations (two rows left, PT potatoes 0.93%, tomatoes
  0.36%). r165 (Green Deal 2030, CAPRI's rule): no stop by iteration 20 of the scenario (28 rows above 0.05%, the
  largest about 50%), stopped by hand before its two-hour limit. Default set back to the model's rule (the project
  lead's decision, 27 October 2026, DEPARTURES_FROM_CAPRI); r166 (the same scenario, the model's rule) prints CAPRI's
  verdict and its largest row at every iteration for the diagnosis. r168 (28 October 2026: Green Deal 2030, CAPRI's
  rule, its Hessian measured in the run (38 min), every region's levels recorded per iteration, tools/check/k79_trace.py):
  **converged under CAPRI's rule after 30 iterations** (0 rows above 0.05% at the last; 5,761 s with the Hessian, the
  scenario's 30 iterations about 53 min). r165 was stopped by hand at iteration 20, before its two-hour limit, not by a
  divergence: r168 too had 14 rows above 0.05% at iteration 20. EU indicators within 0.4 points of
  r166 (the model's rule, 9 iterations): oilseed price +7.1 (+6.8), fertiliser N2O -32.5 (-32.8), sheep and goats -7.7
  (-8.0). The large swings are single regions jumping between two states: BG010000 (maize -115, +128, -115 ... +131 kha,
  rapeseed +-55, broilers +-4,000 thousand head, iterations 3-10), HU230000 and HU330000 (other fodder +-45 to 70 kha,
  maize +-25 to 114, barley +-24, iterations 4-16), then Swedish tomatoes (39-76% at iterations 17-20), then a geometric
  tail. The mineral-cap exemptions (K71: kept for the rest of the scenario once needed) differ from r166's: more groups in
  BG020000, BG060000 (SOYA), DEF00000 (PERM), RO050000 (ROOF): the exemption set depends on the path. Default switched to
  CAPRI's rule (28 October 2026, the project lead's decision). Open: the two-state jumps (candidates: two local optima of
  the non-convex regional problem, as K75's FRH0, or an exemption switching), which cost iterations
  29 October 2026 (batch 2 and 3; the jump record of model._nlp_jump in outer_history[...]["jump_check"]): Green Deal
  2030 (r181) converged under CAPRI's rule in 37 iterations (r177, batch 1: 18), the EU indicators as r177's (largest
  price difference 0.17 points, tobacco). 1,655 regional checks in the scenario; 961 kept another start's solution,
  but only 23 lowered the objective by more than 1e-5 relative (the other 938: the same optimum within that, so the
  record's "switched" overstates how often the check acts). The 23 are almost all Hungary: HU230000 (gain about 5e-3,
  at iterations 2, 4, 6, 7, 32, 34: the warm start returns to the worse optimum and the check corrects it each time),
  HU210000 (1.7e-3), HU330000 (2e-4); EL210000 and RO070000 once or twice. The iteration-30 jump (HU pulses 52% in
  CAPRI's rows): HU230000 moved by 34 (relative); the standard start gave no lower objective, so the jump stayed; gone
  by iteration 32. Farm-to-Fork (r180): 12 iterations (r178: 13), 492 checks, none with a gain above 1e-5. Next, for
  the project lead's decision: switch (and count) only above a gain tolerance (a behaviour change: its own runs);
  compare HU230000's two optima (activities, feeding) to see what makes its warm start leave the better one
  29 October 2026, the project lead's decision: the check switches only where the other start gains more than
  supply.nlp_jump_gain = 1e-6 (relative; r181's gains: 938 at 1e-9 or less, one at 1.4e-7, 23 at 1.7e-5 and more), so
  the record's "switched" counts real switches; HU230000's two optima still to compare
  Gate of batch 4 (r183, Green Deal 2030 with the tolerance): converged under CAPRI's rule in 21 iterations (r181: 37);
  13 switches in the scenario, all with real gains (HU230000 at iterations 4, 7, 9, 10). At iteration 17 HU230000's
  solve from the previous point ended at its worse optimum (objective -5.0043e6 against -5.0301e6 at iteration 12,
  5e-3 relative), the standard start found no better one, and the loop stopped at iteration 21 with the region there:
  its maize 37 kha against r181's 148 (base 199), EU maize area -1.1% and the maize price +0.48 points against r181
  (other cereals +0.24, rye +0.18, soya +0.17); the aggregated EU indicators within 0.2 points. r181 ended at the better optimum because its iteration-34 check
  corrected it. So the end state still depends on the path where a region has two optima. Options for the project
  lead: keep, per region, the best objective found at (nearly) the same prices as a further start of the check; or
  compare HU230000's two optima first (still open)
  29 October 2026, HU230000's two optima compared (the project lead's option (b); every solve of the region traced in a
  repeat of r183, r184, which follows r183's path exactly): at the final prices the two optima differ by 5.1e-3 in
  the objective; the better one feeds the cattle concentrates and grows maize grain (168 kha) and sunflower, the worse
  one feeds no concentrates (cereals, protein feed 0) and twice the other fodder, with maize grain at 37 kha and more
  other fodder (54 -> 135 kha), rapeseed (25 -> 102) and soft wheat (113 -> 164); the non-convexity is the per-head
  feeding (herd x ration), CAPRI's own form. Why the run loses the better one: the warm start is built from the last
  solution moved by `inside_regulations` (the fertiliser flows above 0.95 of their regulation maximum pulled back to
  it: 44 values in HU230000) and started with the last solution's multipliers, an inconsistent primal-dual point; in 5
  of the 19 traced scenario solves it stopped at the 200-iteration cap (objective -3.3e6 instead of -5.03e6), and the cold
  restart from the same moved point (`prev`) ended at the worse optimum at iteration 17 (-5.0043e6 against -5.0300e6),
  where every later warm start stayed. Replayed from the recorded data, the warm start from the last solution itself
  (bounds clipped only) converged in all five (10-22 iterations), at iteration 17 to the better optimum (-5.02997e6);
  in two of the replays it ended at a slightly worse point than the run kept (iteration 4: -4.9974e6 against the
  standard start's -5.0202e6; iteration 8: 2e-4 relative). Proposed fix (for the project lead): the warm start from
  the last solution as it is, as CAPRI's CONOPT restarts from its last solution, the regulated flows moved only where
  they lie outside the support (not to 0.95 of it); `inside_regulations` kept for the cold starts
  29 October 2026, the project lead's decision: fix implemented (batch 5): the warm start from the last solution as it
  is (`inside_regulations(..., only_outside=True)`), the cold starts unchanged; replayed on HU230000's five failed warm
  starts, the fixed start moves no value and converges in 10-22 iterations (test
  `test_warm_start_from_the_last_solution_as_it_is`); the market supply Hessian's key changes with it. Results: the
  batch's gate runs
  Gate of batch 6 (r189, Green Deal 2030 with the warm-start fix of batch 5): converged under CAPRI's rule in 21
  iterations (r187: 17); after the first scenario iteration the check kept another start's solution 6 times (r187: 9),
  HU230000 once (iteration 4, the standard start). HU230000 ended at an objective 0.07% below r187's (-5.0317e6 against
  -5.0284e6, at slightly different prices) with another crop mix: rapeseed 97 kha against 24, soft wheat 154 against
  114, sunflower 51 against 115, maize 148 against 167. So the region still has near-equal optima and the end state
  depends on the path; the EU indicators of the two runs are within 0.4 points. Open

  **Gate 10 (31 October 2026, r196 Farm-to-Fork, r197 Green Deal against gate 9's r194, r195):** EU indicators within
  0.2 points; a few regions at another local optimum of their non-convex regional problem, the path changed by K80's
  tolerance (1e-10): Farm-to-Fork FR820000 wine 16.5 -> 50.7 kha (base 52.4; gate 8 and 9 had the 16.5 state), olives
  0.9 -> 16.7 (base 8.9), FR810000 olives 14.9 -> 5.4 (the jump check acted on FR810000 at iteration 2); Green Deal
  BG020000 oats 1.5 -> 23.1, other cereals 19.0 -> 52.9, sunflower 24.9 -> 46.9 (a region with mineral caps relaxed).
  Which state has the lower objective at the final prices is not measured (both runs' solves are optimal and the jump
  check did not act on FR820000 or BG020000)

<a id="k80"></a>
### K80: The same run repeated from a warm start differs by up to 3e-5 relative in small cereal activities (26 October 2026)

The 8-region baseline of test_pesticide_reduction_binds_and_is_a_noop_at_zero run twice in one model (the second solve warm-started from the first): DE23 rye 5.43015 vs 5.43000 kha (2.7e-5), DE23 durum wheat and DE21 rye 2-3e-5, oats 1.6-1.8e-5; the zero pesticide shock moves them by as much (up to 5.8e-5, DE11 rye). The test's comment recorded 1e-7 (DWHE +- 9e-7) at an earlier state; the cause of the increase is not diagnosed (the K75 fix, which removed the binding fodder band rows, is one candidate: rye, oats and durum wheat are small, nearly substitutable activities). Runs from the same start (the reference r145 rule) are not affected

- **Effect:** repeated solves and no-op checks at 1e-6; test tolerance set to 1e-4
- **In 9t:** –
- **Status:** **fixed** (30 October 2026, the project lead's decision; the gate's runs pending). Diagnosed with the
  8-region German baseline run twice in one model (every regional solve's IPOPT status recorded): all 16 solves were
  cold starts ending Solve_Succeeded (not IPOPT's acceptable stop, not the warm start), the two runs' objectives equal
  to 3e-11 to 1e-10 in every region, the levels up to 3.1e-5 apart (DE240000 rye). The problem is the same; its optimum
  is flat along the small, nearly substitutable crops, and IPOPT's stop at tol 1e-8 lands anywhere along it. With the
  acceptable tolerance at 1e-8 the same 3.1e-5; at tol 1e-10, 1.1e-6, with 5% more iterations. Mini-EU Farm-to-Fork
  run at 1e-10 against 1e-8: converged in 7 iterations both, no non-optimal solve, the same fallbacks, supply-model time
  152 s against 154 s, EU prices within 0.05 points. outer_loop.nlp_tol_final set to 1e-10; the organic and pesticide
  no-op tests back to 1e-5

<a id="k81"></a>
### K81: A plain regional solve after a shocked one kept the old price shock in the split and genetics columns (found 26 October 2026)

`_price_shock_now` is set by `_compute_net_revenues`, which runs only when a solve has a price or policy shock; a solve without one kept the previous solve's shock, and the cattle-split, dairy and genetics columns valued their products at it. Found by test_land_is_fixed_without_the_land_market once the stand-alone supply module ran CAPRI's form (FRB0, base after a +20% shock: up to 0.005 off, cold starts). In a run every solve after the first has a price signal; the first solve of a run (no signal) kept the last run's shock

- **Effect:** the first solve of each run after another run (cattle and genetics columns), stand-alone use
- **In 9t:** –
- **Status:** **fixed**: reset at every solve (`solve()`, with the other per-solve state); its own reference run checks the effect

<a id="k82"></a>
### K82: The market supply Hessian read from its cache differed from the measured one by an ulp (found 27 October 2026)

pandas' default CSV float parser returns 64% of the cached Hessian's terms one unit in the last place off (relative 1e-12). Through the outer loop a run reading the cache (r152) ended 1e-4 from the run that measured it (r150) and stopped one iteration earlier (9 against 10); r152 equalled r149 (also from the cache) to the last digit. The outer loop amplifies a 1e-12 perturbation to 1e-4: the stopping tests sit close to their tolerances (as K80's warm-start noise)

- **Effect:** results of runs reading a cached Hessian (1e-4), the iteration count
- **In 9t:** –
- **Status:** **fixed**: the cache is read with float_precision="round_trip" (e26234c); r154 (Green Deal 2030) and r155 (Farm-to-Fork) from the cache equal r151 and r150 to the last digit. All CSV inputs to be read exactly with one reader helper, and Parquet for model caches (planned, before the regional units)

<a id="k83"></a>
### K83: A one-region Farm-to-Fork run's market diverges in its second step (found 27 October 2026, test timing)

`model.run(regions=["DE11"], custom_scenario=farm_to_fork_scenario(), max_outer_iter=2)`: the market of the run, where DE11 alone stands for the EU, did not converge in either scenario step (100 steps each, largest relative residual 1.35e8 and 7.66e9, dairy products), ~550 s. The first scenario market solve started at 0.099 (POTA) and grew from the first step. With `max_outer_iter=1` the same solve converged in 27 steps. What differs between the two (both at the first scenario market solve, the baseline run inside the scenario has as many steps as the scenario): DE11's Farm-to-Fork supply at base prices (POTA 11.8 against 106.9 kt, base 133; OATS 15.4 against 25.2) and the market's own-price supply responses, measured once per calibration (EU row POTA, OATS, CORN at the 5.0 clip against 0.24-0.36). Full-EU runs not affected (the F2F and Green Deal references converge). Not yet known: why DE11's first scenario supply depends on the number of baseline steps (the CAPRI columns calibrated from the base duals enter from the second base solve on, a candidate). CAPRI solves its market simultaneously (CONOPT), where a steep response is not a fixed-point divergence.

- **Effect:** one-region scenario runs (tests, regional studies); the winter-cover test took 590 s
- **In 9t:** no
- **Status:** **open**, cause found and fix decided (30-31 October 2026). Reproduced (DE110000, Farm-to-Fork, two
  outer steps, 193 s): the market did not converge in either step (100 steps; largest relative residual 6.45 and
  1.76, potatoes), its log showing why: the EU market keeps the whole EU's demand while its supply is the solved
  units' alone (soya cake: EU production 16.8 kt against consumption 14,543 kt). For products the EU hardly trades no
  price within the market's bounds closes that gap: not a solver fault, a market the subset cannot balance (as K10).
  CAPRI switches whole countries off (%CountriesXX%) and keeps them in the market: a country off leaves RMSSUP
  (capmod/create_sim_ini_gdx.gms l. 73) and is supplied by CAPRI's market supply functions (ProdNQ_), as a non-EU
  region. Decision of the project lead (31 October 2026): CAPRI's rule, the units not in a run supplying the EU
  market through their member state's market supply function (their share of it, the model's departure where a
  subset cuts through a member state); the solved units supply their models' output
  The plan (31 October 2026, read in CAPRI's code and data): a country off in CAPRI gets both ProdNQ_ and FeedNQ_
  (arm/market_model.gms l. 1033: FeedNQ_ only for NOT RMSSUP). CAPRI's export elas_2_1730defaulta.csv has every EU
  member state's p_hessNQSupp at CAL (DE000000: 37 products, MILK and the young animals included) but no
  p_hessNQFeed or p_ElasFeed for them (in CAPRI's reference run every member state is RMSSUP, so their feed functions
  are never calibrated). So: the excluded share's supply through its member state's ProdNQ_; its feed demand at its
  base quantity (the model's departure: CAPRI would calibrate FeedNQ_ in its own run with the country off; no terms
  invented). The excluded share of a member state per product: its units outside the run over all its units, from the
  units' base output (0 in a full run, which therefore does not change). Steps: (1) a builder of the member states'
  ProdNQ_ terms for all products in model codes, with CAPRI's Data_CAL production; (2) the shares; (3) the market's
  EU supply (solved output + the excluded share's ProdNQ_), replacing the K16 fallback; (4) the base calibration and
  crushing base; (5) raw milk per member state; (6) feed bulks; (7) young animals; (8) the outer loop's member-state
  milk test. Checks: a full run unchanged exactly; a one-region run converging; the mini-EU run's prices nearer the
  full run's
  31 October 2026, steps 2, 3 and part of 5 built (the excluded units' base output through the bridge, their
  member states' ProdNQ_ in the market's supply after the measured Hessian, the base calibration and the dairy
  block's raw milk with them; the K16 refill of the whole EU's base production off where they are). DE110000 alone
  (two outer steps): the market converges in 19 and 16 steps (before: not in 100), Germany's milk gap 0.0002, the
  young-animal ratios 0.85-1.31, world prices within 0.3%; 63 s. tools/run/run_f2f_2030.py --regions now solves the
  subset on the whole data set (the model was built on the subset's data alone, so the projection had no data for
  the units outside it). Mini-EU Farm-to-Fork: converged in 5 iterations, 224 s (461 s). A correction to the plan's
  expectation: its EU prices moved further from the full run's, not nearer (cereals -0.9% against the full run's
  +11.2%, the mini run before +4.0%; milk +3.7 against +22.4, before +11.8): as in CAPRI, a policy applied in the
  supply models does not reach the countries switched off, so a subset run now simulates the policy in its own
  units only, the rest of the EU supplying through its market supply functions. A subset run is market-consistent
  but cannot stand in for the full run's prices under an EU-wide policy (nor could it before). Remaining: the
  excluded units' raw milk response (MILK's ProdNQ_), feed bulks, the outer loop's member-state milk test
  31 October 2026, **fixed** (the gate's runs pending): the excluded units' raw milk responds as their member state's
  ProdNQ_ of MILK inside the dairy block's clearing; their feed enters the member states' bulks at its base; the
  member-state milk test runs over the member states with units in the run. DE110000 alone, two outer steps: the
  market converges in 15 and 8 steps, the milk gap 0.0000, world prices within 0.03%, 68 s. Full test suite: 249
  passed; the 3 failures were two Norway tests written for the old rule (updated) and schema.json; updating them found
  the EU's raw milk counted twice with no EU unit in the run (fixed). tools/check/compare_runs.py notes a subset
  run's two coverages (prices and beef production: the EU market; herds, crops, environment: the run's units). The
  mini-EU regression run changes with it: its dev reference is to be renewed at the gate. Registered differences
  from CAPRI: a subset can cut through a member state (the part outside: its units' own base output); the excluded
  share's feed demand held at its base (no FeedNQ_ terms for EU member states in CAPRI's export); the member states'
  ProdNQ_ terms are CAPRI's 2030 reference calibration's (CAPRI may recalibrate them in a run with a country off, not
  verified)

<a id="k84"></a>
### K84: The landscape floor's fit ends on its last step (found 27 October 2026, test timing)

Where the set-aside floor cannot be held (land market off), `_fit_row` sets the row to the least value a linear program over the problem's linear rows reaches plus a margin, and widens the margin in steps (1e-3, 1e-2, 0.05, 0.1, 0.25, 0.5 of that value), each tried from two starts. In EL65 and ITH1 every step failed but the last (11 failed IPOPT solves, 60 and 106 s; shortfall 44.5 and 9.5 kha); FRM0's failed solves run to IPOPT's 3000 iterations (~580 s). The recorded shortfall is then mostly the last margin, not the least relaxation CAPRI's form can hold: the linear program leaves out the rows of CAPRI's form (feeding, fertilisation) that bind. Not seen in the reference runs (land market on).

- **Effect:** the landscape shortfall where the floor is fitted; run time
- **In 9t:** no
- **Status:** **fixed (CAPRI's form)**: the floor is no longer relaxed; as CAPRI (supply_model.gms e_setaLandscape is never widened by widen_bounds.gms), an unreachable floor keeps the solver's last point, recorded in nlp_fallback with the note that CAPRI's Green Deal runs have the land market on. EL250000 test 80 s -> 16 s (the project lead's decision, 27 October 2026)

<a id="k85"></a>
### K85: Input costs of animals a region does not have were NaN in its net revenues (found 27 October 2026, the first Farm-to-Fork run on CAPRI's units, r160)

The per-head animal columns of variable_costs.csv held values of unknown origin (written by no builder) and were emptied with the move to the units: an animal without CAPRI input cost in a region read NaN, the NaN reached the NLP's objective (for an activity fixed at 0, CAPRI keeps it out of the model), and IPOPT stopped with Invalid_Number_Detected in 16 regions, whose last point was kept.

- **Effect:** r160 (not used); no other run
- **In 9t:** no
- **Status:** **fixed**: an activity without CAPRI input cost and without base level costs 0 (its level is fixed at 0); one with a base level raises an error; the regional NLP refuses a non-finite matrix or vector. r161: all regional solves optimal

<a id="k89"></a>
### K89: Failing regional solves take most of IPOPT's time (found 29 October 2026)

The linear-solver benchmark (tools/check/linear_solver_bench.py: the mini-EU Farm-to-Fork run, every regional IPOPT
solve repeated with MA27; branch hsl-option) recorded 908 solves: the 860 that both solvers finished took 63.5 s of
IPOPT time with MUMPS, the 48 that failed with either solver took 260.9 s, 80% of the IPOPT time (45 failed with
both: MUMPS ended 34 as Infeasible_Problem_Detected and 11 at its iteration limit; 3 failed with MA27 only).
They are probably the tries of the fallbacks (JRC121368's relaxed N target, the mineral-cap exemptions of BG020000 and
HR000000, K71); which solves they are is not recorded.

- **Effect:** run time only
- **In 9t:** –
- **Status:** **fixed** (measured 30 October 2026, below); diagnosed 29 October 2026 (the project lead's decision: the cause first;
  tools/check/k89_trace.py, the mini-EU Farm-to-Fork run in one process: 905 solves, 345 s of IPOPT, 43 failed, 254 s).
  210 s are one episode in NL320000 at the scenario's first iteration: its solve at the tiered N target fails (warm
  start 3,000 iterations, cold start infeasible), then the mineral-cap exemption search (written for the Green Deal's
  caps, supply_module._capri_nlp_solve) exempts its crop groups one at a time, twice each: 30 cold solves, all
  infeasible or at the iteration limit; JRC121368's relaxed target (K57) then solves in 59 iterations and is kept, so
  every later solve of NL320000 succeeds. The caps are not what makes NL320000 infeasible, the N target is. The rest:
  the cap searches of BG020000 and HR000000 (the exemptions they need, found: PERM, ROOF; about 30 s) and a few failed
  starts of the jump check. In a full run of 221 units the NL320000 episode is the same single event, so its share of
  the run time is a few percent, not the mini run's 74% of IPOPT time (an estimate). Options: try JRC121368's relaxed
  target before the cap search where a tiered N target is in force (identical results where the cap search fails, as
  in NL320000); or a solve without the N-surplus row first to see which constraint makes the problem infeasible
  Left as it is for now (the project lead's decision, 29 October 2026), to be taken up again later
  29 October 2026 (commit acda673): on a failed solve under a tiered N target the problem is solved once without
  the N-surplus row; feasible there, the N target is the cause, and JRC121368's relaxed target is tried before any
  cap exemption (its own solve still searches exemptions where caps bind). Measured 30 October 2026 with
  tools/check/k89_trace.py on the same mini-EU Farm-to-Fork run with the code of that day (this fix and the others
  since the diagnosis, the warm start of batch 5 among them; converged in 7 iterations): 261 regional solves, 135 s of
  IPOPT (345 s in the diagnosis), 14 failed, 60 s (254 s); NL320000's episode 8.6 s (210 s), the part this fix
  addresses. The rest are
  the first mineral-cap exemption searches of BG020000 and HR000000 (43 s; their exemptions PERM and ROOF are needed
  and kept for the scenario, K71) and one or two failed starts of FI190000 and AT330000. **Fixed.**

## NLP check (tools/nlp_check), what it showed

- The check reproduces the conic model when given its own relations (objective within 1e-8 once K2 is accounted for).
- Fertiliser technologies: one regional share per technology (CAPRI) and one share per crop (the conic model's
  registered departure) give the same optimum in all five regions (1e-10): the departure costs nothing there.
- No multiple local optima: every start that converged found the same optimum (spread ≤ 1e-8).
- CAPRI's literal per-head feeding (bilinear) is hard for IPOPT: FRH0 and IE05 found no feasible point from any of five
  starts, not even from the conic solution; the total-feed form (same feasible set, convex) solves everywhere.
- After K1 and K2 the conic solution is CAPRI's exact optimum: objective within 1e-8–6e-7 of IPOPT on CAPRI's form
  (IE05 1e-5, Clarabel AlmostSolved), N prices equal to 0.01 EUR/kg, CAPRI's N balance met (violation ≤ 0.03 t N).
- Effect of K1 + K2 on the full runs: Farm-to-Fork gap 4.29 → 4.28, ammonia options' adoption toward CAPRI's (housing
  19.9 → 19.5%, CAPRI 12; covered storage 41.9 → 41.3%, CAPRI 34); Green Deal within 0.5 points; no other EU indicator
  moves more than 0.2 points. Regionally larger (DE94 pigs and broilers ~2%).
- Test suite: 92 passed, no warnings (K7).

<a id="k86"></a>
### K86: Ammonia housing and storage options without their farm-size cost curves in Denmark, Lithuania and Croatia (found 27 October 2026, builder reproduction audit)

tools/build/build_ammonia_cost_curves.py fits CAPRI's farm-size cost curves (ammo_tech.gms m_CostAmm) for the regions of
its manure data, keeping a member-state code only for a fixed list (MT, CY, LU, EE, LV, SI): the member states without
regional detail of an older CAPRI. DK000000, LT000000 and HR000000, regional units of CAPRI star 3.0 with all the inputs
(60 manure rows, 6 farm-size head rows, prices), get no curve, and build_ammonia_technologies.py then takes the curve's
terms as 0: e.g. air purification for fattening pigs and sows costs 0 in DK and LT (7.9 EUR in DE110000, 2.6 in
EE000000), low-emission housing for dairy cows 28.9 and 10.5 (112.2 in EE000000), and every curvature term (CostParSqr)
is 0 there. CAPRI computes the curves over all its regional units (ammo_tech.gms, rs). CZ010000 (Prague) also has no
curve, for another reason: the holdings per farm-size class (CAPRI's p_holdLSU, the heads per holding's denominator)
are missing for it and for CZ000000 in the exported data, so no farm-size class has a cost; its heads fall back to
the national ones (the builder's registered fallback). Whether CAPRI has holdings for CZ010000 in its own data: to check.

- **Effect:** the cost and curvature of the ammonia housing, storage and air-purification options in DK000000,
  LT000000, HR000000 (and CZ010000); every run with the ammonia options
- **In 9t:** not checked
- **Status:** **fixed** (27 October 2026, in dev since; Prague checked 29 October 2026): fixed in the builders (branch data-fixes): the cost curves, the AD option
  (build_ad_option.py, which had LU000000, not a unit, and missed HR000000) and the Nitrates Directive tables
  (build_nitrates_directive.py, the same list) take the regional units; the ammonia chain to be rebuilt
  (build_ammonia_cost_curves -> build_ammonia_technologies -> build_ad_option -> build_ammonia_tech_model ->
  build_manure_n2o, build_n_cascade) and rebuilt: DK000000, LT000000, HR000000 now have their curves (e.g. air
  purification for fattening pigs 7.62, 2.61, 2.93 EUR; curvature terms no longer 0). The AD option and the Nitrates
  Directive tables come out unchanged: Croatia is absent from CAPRI's AD base data (p_VSER) and from those tables'
  sources, so CAPRI has no AD option there either. The builder now lists the units left without a curve: CZ010000 and
  Norway's six (no ammonia options built for Norway, registered). Prague (29 October 2026): CAPRI's own holdings data
  (dat/scen/ghgtech/holdingsLSU.gdx, as exported to p_holdLSU.csv) has one row for CZ010000 (poultry, the largest class),
  so in CAPRI as well no heads per holding exist for its other animals (ammo_tech.gms l. 1355-1362, defined only where
  p_holdLSU is), m_CostAmm has no shares for them and v_alpha, v_beta stay 0: the option's own farm-size terms are 0
  and its CostParLin is the manure-storage term added on (l. 2120-2121; e.g. low-emission housing for dairy cows (DCOL) 5.36,
  the storage term). The model's file has the same values, so this is CAPRI's result, not a gap

<a id="k87"></a>
### K87: Builder outputs that do not follow from their builders (reproduction audit, 27 October 2026)

tools/check/reproduce_builders.py runs every builder on the committed inputs and compares what it writes with the
committed files. 117 invocations; most reproduce their files exactly. Found:

- `2017/supply/crop_cost_shares.csv` (the supply module's fertiliser cost share where CAPRI has no regional
  coefficient): rounded to 3 decimals (up to 2.9% relative for small shares); its builder also leaves out the eight
  member states that are one regional unit each (the old test "code does not end in 000000").
- `validation/greendeal_2030/capri_unit_values_max_2030.csv` (without the 34 TABO rows its extractor wrote): removed 30
  October 2026 with the max invocation, read by no code.
- Files written before the full-precision decision of 27 October and not rebuilt since: the market builders' outputs
  (bilateral flows, regions and quotas, biofuel, dairy, feed bulks, GL demand, processing, sugar, use components,
  EU member-state balance, fertiliser distribution priors, land-use change, CAP greening, cost savings) differ from
  their builders' output by 3e-10 to 5e-8 relative, five of them by up to 5e-6 (feed and biofuel use shares, dairy
  demand elasticities, feed by-product weights): the committed files' rounding.
- `recalibrate_trade_2017.py` writes a backup copy
  (`trade_flows_2021.csv.superseded_by_2017`) wherever it is absent, so in every clean checkout.
- Files several builders write in turn (`yields.csv`, `variable_costs.csv`, `capreg_producer_prices.csv`): a builder
  alone differs from the committed file where a later one overwrites its columns; to be checked as a chain
  (`--chain`), not done yet.

- **Effect:** crop_cost_shares: the fertiliser cost of crops without CAPRI's regional coefficient; the rest no model
  effect beyond the last digits
- **In 9t:** –
- **Status:** **fixed** (27 October 2026, branch data-fixes, with the reference runs of that push): the two builder
  fixes (crop cost shares over every unit; the two stray outputs dropped), every listed file rebuilt; the files
  downstream of the full-precision cost savings rebuilt too (genetics, low-N feed and supplement effects: dsav up to
  2e-4 relative, a difference of two calibration runs' savings; histosols 2e-6). Re-audit: every rebuilt builder
  reproduces its files exactly; the chain extract_all_from_data2 -> build_capri_base -> build_crop_economics_2017 ->
  build_shg_split -> build_animal_yields -> build_eu_producer_prices reproduces yields.csv, variable_costs.csv and
  capreg_producer_prices.csv. Not re-checked: the recipe PMP files (2e-9, used only with pmp_source = recipe)

<a id="k88"></a>
### K88: Builders that still round the values they write (found 27 October 2026)

The exact-I/O decision of 27 October (K82) has every CSV read parse floats exactly and every builder write full
precision. Reads are exact everywhere (capri_mod/tests/test_exact_io.py checks it statically; the last three inexact
reads, in build_nuts2024_reporting.py and compare_baseline_capri.py, fixed). But 20 builders still round values before
they write them: 72 calls, e.g. build_ammonia_technologies.py (costs and shares to 6 decimals), build_ad_option.py
(6-9), build_tariffs_2017.py, build_feed_byproducts.py, build_n_cascade.py, build_enteric_feed_factors.py (4-5),
build_biofuel_market.py and build_dairy_world_markets.py (3). The reproduction audit cannot see them (a builder that
rounds reproduces its own rounded file). Some may round keys or comparisons rather than outputs: to sort out per call.

- **Effect:** the last digits of these files (1e-6 and smaller relative for 6 decimals; up to 1e-3 for 3 decimals of
  small values)
- **In 9t:** –
- **Status:** **fixed** (28 October 2026). The roundings removed in the builders (every one rounded a written value,
  none a key or a comparison; the roundings of printed summaries moved into the prints); ROUNDING_ALLOWED empty. Every
  builder run in order on the committed sources (reproduce_builders.py --chain --keep; pushed with batch 1, reference
  runs r177, r178). Census on dev afterwards (each builder alone on the committed inputs, 314 outputs): 305
  byte-identical; 7 written by several builders in turn, reproduced by their last writer; 2 not reproduced because the
  build list ran a reader before its input's builder (ammonia_tech_model.csv read ad_option.csv, which read
  n_cascade_factors.csv, each built later in the list than its reader): the technology model's initial shares off by up to 1.6e-4
  relative, the AD option by 2.6e-11. The ammonia chain now runs in dependency order and was rebuilt (batch 2).

<a id="k90"></a>
### K90: The wheat market's world price is CAPRI's soft-wheat price, not its wheat product's (found 29 October 2026, making build_world_prices.py)

The model's wheat market SWHE is CAPRI's market product WHEA (capri_data/codes/model_commodities.csv, from
build_feed_bulks.COMMODITY), but its world price in world_prices.csv is FAO_agg's 'World'.'PMRK'.'SWHE'.'BAS', 171.93
EUR/t, as the file has held it since the earlier writer, not 'WHEA', 196.60. FAO_agg's WHEA price lies above both
its soft and durum wheat prices (171.93, 173.00), so it is not their average; which one CAPRI's market model starts
from for WHEA is not checked yet (arm/ data preparation).

- **Effect:** the level of the wheat market's base world price (`world_prices.csv`); the outer loop's price signal is
  its ratio to the base, so the level cancels there; where else the level enters the bilateral market is not traced.
  For comparison: CAPRI's 2017 market solution (market_base_1717) has a World PMRK of WHEA of 157.7 EUR/t, but its
  World rows are far from FAO_agg's for other products too (soya 102.7 against 325.7), so it is no check
- **In 9t:** not checked
- **Status:** **fixed** 29 October 2026 (batch 5; the project lead's "fix everything"): the wheat market takes CAPRI's
  WHEA world price (196.60 EUR/t), the price of the market product it is in CAPRI (no market of CAPRI's carries
  'SWHE'); effect measured in the batch's gate runs

<a id="k91"></a>
### K91: CAPRI's trend projection (captrd_2030.json) has no extractor (found 29 October 2026, the data pipeline)

capri_data/trajectories/captrd_2030.json, the alternative baseline trajectory (`--trajectory captrd`; the default is
CAPRI's 2030 reference, capri_ref_2030.json), holds CAPRI's CAPTRD trend factors extracted from a series slice
(its `_provenance`: "/tmp/series_slice.csv", per-activity medians of per-region cumulative ratios, band 0.2-5).
Corrected 29 October 2026 (registry migration): the extractor is in the repository, capri_mod/projection/captrd_import.py
`extract_trajectory` (it writes exactly the file's `_provenance` keys); missing are its input (the series slice of the
project lead's CAPTRD p_result export, not kept) and a builder that calls it. tools/build/build_trajectory_model_keys.py adds the model's activity and region
keys to the file in place (idempotent: rerun on its output, it writes the same file), so the file cannot be built from
blank; it was taken out of the pipeline's builder list (tools/check/reproduce_builders.py NOT_AUDITED). Beyond the
missing script, the step overwrites a BULL growth entry with BULF's, so whether the slice had a BULL factor of its own
cannot be told from the file.

- **Effect:** the `captrd` trajectory only (not the default runs)
- **In 9t:** not checked
- **Status:** **fixed** 29 October 2026 (batch 5): tools/build/build_captrd_trajectory.py builds the file from blank
  from CAPTRD's results of the base-2017 run (capri_reference/captrd_results/1770/series.csv.gz) with
  `extract_trajectory` and `build_trajectory_model_keys.add_model_keys`; it reproduces the earlier file's growth
  factors and all 442 entries keyed by the model's regions exactly (so the same source run); only CAPRI-keyed regional
  entries differ, where the NUTS-2016 model's keys step had overwritten them. captrd_import.py's docstring corrected

<a id="k92"></a>
### K92: Farm-to-Fork changes furthest from JRC121368, besides the milk price (K13) (found 29 October 2026, registry migration)

In the last Farm-to-Fork 2030 run whose indicators are tabulated (r145, README section 8 table; r161 in
`FITNESS_FOR_USE.json` within about 0.5 points), against JRC121368 (Figures 5 and 7, Table 15): pork price +18.0% (CAPRI
+43) while pigs fall as in CAPRI (-13.9%, -14.5); poultry price +15.1% (+18); oilseed price +14.4% (+11); cereal price
+10.6% (+8); vegetables and permanent crops +11.7% (+15); dairy cows -3.4% (-10); poultry -11.9% (-16.5); manure N2O
-18.2% (-3.2); ammonia -37.4% (-33); non-CO2 GHG -18.8% (-14.8). Close to CAPRI: beef animals, cereal, oilseed and
vegetable production. The comparison is not like for like (JRC121368 ran the 2020 CAPRI, base 2012; the model is star
3.0). The registry's earlier diagnoses (pork: EU exports absorb the supply cut at CAPRI's rho2; dairy: cows expanding
where the N target barely binds) were made on structures since replaced and are not re-checked.

- **Effect:** Farm-to-Fork meat and crop price levels, the dairy herd, poultry, manure N2O (README "Not sound for")
- **In 9t:** –
- **Status:** **open, waiting for CAPRI's scenario results** (the project lead's decision, 29 October 2026: kept open with its reference). Needed: CAPRI's Farm-to-Fork 2030 market and supply results behind the indicators: per member state and EU the prices (PPRI, ARM1P) of pork, poultry, cereals, oilseeds, vegetables and permanent crops, the herds (dairy cows, poultry), net trade of pork and poultry, and manure N2O and ammonia by source; to be exported with tools/gams/export_capmod_results.gms (run on a CAPRI installation where the scenario was solved); the project lead's installation has none of them so far. Before: **open**. The current reference run r182 (29 October 2026; tools/check/compare_runs.py --capri) gives
  the same picture: pork price +18.7% (CAPRI +43), milk +21.7% (+1.5, K13), poultry price +15.7% (+18), cereal +10.7%
  (+8), oilseed +14.4% (+11), vegetables and permanent crops +12.4% (+15); dairy cows -3.5% (-10), poultry -12.2%
  (-16.5); manure N2O -18.3% (-3.2), ammonia -37.7% (-33), GHG -18.9% (-14.8); mean absolute deviation over the 24
  indicators 4.44. Next, per indicator: pork through the EU pork trade response of the bilateral market, dairy
  through the regional N shadow prices against the change in cows; CAPRI's own Farm-to-Fork results would be the
  reference (K13)

<a id="k93"></a>
### K93: CAPRI mitigation options not built, and the documents disagree on which are in (found 29 October 2026, registry migration)

Not in the regional model: 3-NOP (built 29 October 2026), legume share (LegSh), tillage (ConsTill, NoTill), urea substitution (UreaSubst),
buffer strips, biodiversity options and biochar (`docs/MITIGATION_IN_SUPPLY.md`: "not built; their LEACHN_/RUNSURFN_
terms held at CAPRI's reference"); CAPRI's constraint on total ration fat (SupplementPerc_) is not carried. These are
recorded only inside the status texts of K50 and K51 (resolved table) and README's "Future (not scheduled)", not in
`docs/DEPARTURES_FROM_CAPRI.md`. On linseed the documents disagree: MITIGATION_IN_SUPPLY.md says it is in
(`build_supplement_effects.py`), README and `capri_regional_nlp.py`'s header list it as not yet in CAPRI's form.

- **Effect:** runs with an emission tax (3-NOP acts on enteric CH4); leaching and runoff where tillage or buffer strips
  would act (held at CAPRI's reference); size in the model not measured
- **In 9t:** –
- **Status:** **open**: registered as a departure (docs/DEPARTURES_FROM_CAPRI.md, 29 October 2026) and the linseed
  statements made to agree with the code (linseed and nitrate are in: columns of the regional model from
  `supplement_effects.csv`); building the options remains. Scoped 29 October 2026: CAPRI's Green Deal technology
  file (refpol_endotech_all_sup.gms, active_technologies.csv) switches on 3NOP, LegSh, ConsTill, NoTill and UreaSubst
  among those not built. 3NOP (envind/line_nitr.gms l. 58-61, 83-86, 124-143, 217-221): dairy cows in stables for
  305 of 365 days, 0.09% of dry matter, CH4ENT cut by 32.36 + 0.282 (dose - 70.5) - 0.915 (NDF - 32.9) - 3.08 (fat -
  4.2) %, the ration's NDF and fat shares from CAPRI's digestibility table p_digestPar (envind/def_digestibility.gms:
  NRC 2001 and INRA 2002 values written in CAPRI's code, then cleaned per region in digestibility.gms) over the
  activity's base ration; cost 175 EUR per kg of active substance; no cost saving. Without an emission price its
  share stays 0 (CAPRI's calibration), so it acts in the carbon-tax runs only. Needs p_digestPar as data (a CSV built
  from CAPRI's code) and the rations' dry matter. **3-NOP built 29 October 2026** (tools/build/build_digestibility_table.py: CAPRI's table to
  CSV; tools/lib/_capri_digest.py: digestibility.gms's steps; build_supplement_effects.py: 3NOP_Tot rows, CH4ENT -25%
  to -57% (median -35%), about EUR 95 per dairy cow and year; the accounts' combination of the supplements corrected so linseed and
  nitrate keep their overlap term with 3-NOP present); acts in the carbon-tax runs only. Remaining: LegSh, ConsTill,
  NoTill, UreaSubst, buffer strips, biodiversity options, biochar. **Where the rest would act** (checked 29 October 2026 in CAPRI's own Green Deal 2030 result,
  scen_greendeal_2030.txt): LegSh is adopted on 0.002% of the EU's other fodder (NL12 1.8%, every other region 0), 3-NOP
  at its 1e-6 floor, and UreaSubst, the tillage options, buffer strips and the biodiversity options carry no level at
  all (not active in that run); so none of them moves CAPRI's Green Deal or Farm-to-Fork result, and their port matters
  for the emission-tax runs (and scenarios that switch them on)

  **UreaSubst, scoped 29 October 2026 (port started):** CAPRI's form (envind/ammo_tech.gms l. 2353-2372, 3041-3107; supply/supply_model.gms GASTOTNETF_ l. 3366-3377, GWPCO2UREA_ l. 3966-3972, GHG_Mit_Cost_ l. 4945): one share m per region of the mineral N bought, 0 <= m <= MaxShare = p_fracUseFert(MS, Ureum) (LitRev_inputs), IniShare 0; cost per t N bought costParLin = (UVAG(NITF) - 289 x 60/28 x 1.019^(BAS - 2007) x (share urea + other)) / share other, case 3 calibration (relSubs0 0.2, relSubs1 1.2, pmpParSqr = (Subs1 - Subs0) / MaxShare, pmpParLin = Subs0 - costParLin); effects: the mineral N's NH3 loss x (1 - m x (EF_NH3 urea - EF_NH3 other)) (the model's cascade n_cascade.netf already takes these arguments) and CO2UREA = N bought x (IniShare - m) x 44/28 in the tax. Data: FracUseFert.csv written again by build_ammonia_tech_inputs.py (batch 8). Found on the way: the accounts' urea share (crop_co2_coef.csv, implied by CAPRI's 2017 CO2UREA / NMIN) differs from LitRev's p_fracUseFert, which CAPRI's simulation loads (ammoLitRev on; envind/ammo.gms l. 285-290): Czechia 0.116 against 0.016, Austria 0.032 against 0.014, Germany and Spain equal; which one CAPRI's 2030 runs use for CO2UREA is to be settled from its 2030 results (the Green Deal reference reports CO2UREA under 'UreaSubst' and 'CARB', meaning not yet established) before the port
  **Urea share settled 29 October 2026** from CAPRI's own Green Deal 2030 result (res_2_1730greendeal_refpol_endotech_all_ini,
  dataOut): for every country listed (EU27, UK, Turkey, the Balkans; Norway has no entry) CO2UREA booked under
  UreaSubst equals the mineral N bought (MINFER.NITF) x LitRev's p_fracUseFert(Ureum) (FracUseFert.csv) x 44/28 to
  six digits (CZ 7.306 kt = 290.57 x 0.016 x 44/28). CAPRI's simulation therefore uses LitRev's share, as
  envind/ammo.gms l. 285-290 loads it; the accounts' share (crop_co2_coef.csv, from CAPRI's 2017 CO2UREA / NMIN) is
  CAPREG's. The GROF.CO2UREA and CARB entries of the same result are another quantity (GROF = CARB x 44/12 in every
  country: carbon and its CO2), not the urea term. Consequence: the model's reported CO2_UREA (environmental_module,
  crop_co2_coef's urea_share) is CAPREG's base-year share, not CAPRI's 2030 simulation's (CZ 0.116 against 0.016);
  switched to FracUseFert the same day (tools/build/build_ghg_coefs_2017.py; reporting only: CO2 from urea is
  outside CAPRI's GGWP tax base; Norway stays at 0, its p_NO_FracUseFert not in hand). EU CO2 from urea changes
  with the next runs (e.g. Romania 0.342 -> 0.050, Croatia 0.337 -> 0.050, Poland 0.249 -> 0.345)
  **UreaSubst's incentives measured 31 October 2026** (before building it; scratchpad script, CAPRI's rules): CAPRI's
  calibration (case 3, or case 4 where the mineral N price is below the urea price, Bulgaria and Czechia) leaves a
  marginal cost at a zero share of Subs0 per t of N bought, 6.9 (Hungary) to 342 EUR (Italy), median about 58. The
  option's gains per unit share and t of N bought: the N it saves (the mineral N's NH3 loss falls, so more of the N
  bought reaches the crops: GASTOTNETF_ in fertDist, supply_model.gms l. 1143) worth 1.2 (Sweden) to 19 EUR (Italy) at
  the 2017 N price, below Subs0 in every member state (closest Hungary 4.0 against 6.9, Slovakia 4.1 against 17.2);
  CAPRI's GGWP tax gives none: with CAPRI's MITERRA fractions the N kept from volatilising raises the direct N2O (1.11%
  of the N left) by more than it cuts the indirect N2O of the NH3 (EF4 1%), so at 100 EUR/t CO2-eq the tax adds 0.05
  to 0.55 EUR per unit share; CO2 from urea is outside the GGWP (GWPCO2_ is CO2LIM only, GWPTOT_ l. 3980). So the
  option stays at 0 in the model's scenarios at base prices; it would move where the N bought is worth much more than
  its price (a binding mineral N cap: Hungary roughly from 560 EUR/t N above the price), under an NH3 price, or with a
  tax on CO2UREA (157 EUR per unit share and t N at 100 EUR/t CO2). Building it touches the fertilisation block's
  first-order conditions (the mineral N's efficiency becomes a function of the share)
  **UreaSubst parked 31 October 2026** (the project lead's decision): not built until a scenario with an NH3 price, a
  tax on CO2UREA or a binding mineral N cap where it could move is planned; CAPRI's form and this analysis are the
  starting point

<a id="k94"></a>
### K94: `capri_mod/data/reconcile_base.py` is an orphan, and README's re-basing note points at a removed concordance (found 29 October 2026, registry migration)

The module is imported only by its own test (`test_capri.py`, `null_check`); no builder or model path calls it.
README's re-basing paragraph says the concordance and the reconciliation "are now in hand" and names
`capri_data/shared/capri_regio_concordance.json`, removed on 27 October 2026 with the move to CAPRI's units. The
registry entry `base_reconciliation` records that its own test ran on share-allocated data, so turning raw regional
statistics into CAPRI's base was never tested.

- **Effect:** none on results; the documentation claims a capability the code does not use
- **In 9t:** –
- **Status:** **fixed** 29 October 2026 (batch 5): the module and its test removed (git history keeps them); README
  says re-basing is not available yet and is planned through the data pipeline (docs/design/CAPTRD_MOD.md)

<a id="k95"></a>
### K95: The "12/12 against CAPRI's PMRK" market-price validation is a solver-consistency check (found 29 October 2026, registry migration)

`test_market_module_reproduces_its_own_prices` compares the market's base solution with `world_prices.csv` itself; its
docstring says "Solver consistency, NOT price validation". The CHANGELOG validation table ("Market prices | CAPRI PMRK
| 12/12 within 15%"), README (section 8 and the world-production paragraph) and `FITNESS_FOR_USE.json`
(`market.prices`: validated) still present it as a validation against CAPRI. The test's comment speaks of soya
"corrected to 102.7"; since 29 October `world_prices.csv` holds FAO_agg's 325.67 (K90 on CAPRI's market rows).

- **Effect:** documentation only (an overstated validation claim)
- **In 9t:** –
- **Status:** **fixed** 29 October 2026 (batch 5): the claims reworded as solver consistency (CHANGELOG validation table,
  README sections 7 and 8, FITNESS `market.prices`), the test's comment corrected

<a id="k96"></a>
### K96: Documents and one constant still describe removed mechanisms (found 29 October 2026, registry migration)

- `capri_data/FITNESS_FOR_USE.json` (served by `capri_mod/fitness.py`, "other entries as of 2026-09-29"):
  `abatement_capri`, `abatement` describe post-solve modules retired in Sprint 9i; `market.prices` relies on the
  Armington premium removed on 20 October (K54) and the PMRK claim (K95); `market.eu_balance` on FAO's
  self-sufficiency (removed); `market.PARI` calls the EU base share-allocated (PARI is in CAPRI's bilateral data);
  `supply.gross_margin` names MREV where margins use TOOU.
- README: Saxony and Croatia regional detail from p_REGIO splits (removed on 27 October: DED00000 and HR000000 are
  single units); Iran's and Saudi Arabia's allocated shares (removed, K45); the feed check on IPCC Eq. 10.6 and
  calibrated monogastric targets (not in the code: the NLP's requirements are the base ration's supply); "no physical
  grass yield for Ireland" (CAPRI's GRAS output is taken for every unit; whether Ireland's units have their own rows or
  the national fallback is to be checked before the caveat is dropped).
- `docs/MITIGATION_IN_SUPPLY.md`: "columns of the regional QP" (removed 26 October); winter cover "not a choice" (the
  NLP chooses it, K51).
- Code: `supply_module.py` `UNVERIFIED_OUTPUT_UNITS`, read by nothing (one comment names it).
- The environmental module's HNV farmland indicator: hand-set weight 0.5 on legumes, and grass counted twice (the
  GRASSLAND land and GRAS among the "legumes"); reporting only (docs/design/PROXY_AUDIT.md).

- **Effect:** none on results; the fitness file is the machine-readable source of caveats, so stale entries mislead
- **In 9t:** –
- **Status:** **fixed** 29 October 2026 (batch 5): FITNESS entries brought up to date (the three abatement entries
  replaced by `mitigation` and `mitigation.at_carbon_price` with r182's adoption against JRC121368; market prices, EU
  balance, rice and gross margin rewritten; the Irish entry removed: Ireland's units carry their own CAPRI grass output,
  37.7 and 46.9 t fresh matter per ha, res_17IR GRAS.GRAS, while CAPRI's YILD item of grass equals MREV there); the
  README passages corrected (regional detail, world production, feed, the Irish item of "Not sound for");
  MITIGATION_IN_SUPPLY.md corrected (no QP; winter cover a choice); the dead constant removed; the HNV proxy removed
  (no CAPRI source; reporting only)

<a id="k97"></a>
### K97: NaN in the crop-diversification row during Green Deal solves (found 29 October 2026)

Every Green Deal 2030 run logs CasADi's "nlp_g failed: NaN detected for output g, at (row 66, col 0)": 168,690 times
in r183, 112,335 in r181, from the scenario's fourth iteration; Farm-to-Fork runs (r180, r182) log none. Row 66 is the
crop-diversification row (Shannon index of the annual crop groups, `cropDivGreening_`) in a region with all twelve
animals (HU230000's structure: 42 linear rows, 24 requirement rows, the permanent-grassland and ecological set-aside
rows); it takes the log of each group's area plus 1e-6 kha. IPOPT evaluates trial points within its bound relaxation
(1e-8 of the scaled variables), where a group sum can fall below -1e-6 kha and the log is undefined (a likely cause,
not confirmed); IPOPT then shortens the step. HU230000's traced solves replay without it, so the regions are not yet
identified. K69 removed the fixed-zero columns from the groups for the same symptom in the baseline.

- **Effect:** solver effort in the Green Deal: the solves that hit it were the jump check's cold starts, which ran to
  IPOPT's 3000 iterations or ended infeasible and were discarded (the warm solution kept), so the kept results were
  not affected
- **In 9t:** –
- **Status:** **fixed** 29 October 2026. Found with tools/check/k97_nan_regions.py on the Green Deal run r185 (the
  CasADi warnings per regional solve): LV000000, a cold start, 47,966 NaN warnings, 3000 iterations. A one-region
  Green Deal run of LV000000 caught the failing solve: the row is the crop-diversification row (cap_rows cropDiv), and
  at IPOPT's last point a one-column group (a column of base level about 166 kha, lower bound 0) sat at -6e-9 in the
  scaled column, within IPOPT's bound relaxation (1e-8), i.e. -1e-6 kha: the group plus the 1e-6 floor was zero and
  0 log 0 NaN. The floor under each group's log is now 1e-6 + 1e-7 x the sum of the group's column scales (max(|base
  level|, 1)), the relaxation over the group's columns x 10, the same in the base index H0 (supply_module, the
  spec's floors; capri_regional_nlp). The fixed columns as constants (as GAMS hands .fx variables to CONOPT) were
  tried first and did not remove it. LV000000's two-iteration Green Deal run: 41,636 NaN warnings before, none after;
  its supply-model time in the second iteration 10 s before, 3 s after; the indicators equal to 0.1 point. Test

<a id="k98"></a>
### K98: CAPRI's supply Hessian read as stored: half of the cross terms missed (found 29 October 2026)

CAPRI's calibration export (elas_2_1730defaulta.csv) stores each cross term of p_hessNQSupp once, under one of the two
products (USA: MAIZ's row carries WHEA, WHEA's row does not carry MAIZ); CAPRI's market model completes the matrix on
loading (arm/market1.gms l. 539-574: tiny terms deleted, products without ProdNQ_ deleted, missing terms from the
transpose). tools/build/build_eu_market_supply_nq.py (the EU's other vegetable oils and fish, market step D, 28
October 2026) read the products' stored rows only: 133 of the 817 terms CAPRI uses. The own terms were complete, so
CAPRI's own-price elasticities were reproduced and the builder's check passed; the cross terms of other oils to the
crops were missing (EU sum -10.7 kt per unit of price ratio against CAPRI's -116.4; fish: none of size). Found while
porting the non-EU market supply functions (K54-3), which need the full matrix.

- **Effect:** the EU's supply of other vegetable oils (about 2,490 kt per unit own term) in scenarios that move the
  crop prices; small
- **In 9t:** –
- **Status:** **fixed** 29 October 2026: tools/lib/_capri_nq.py completes the Hessian as CAPRI's market1.gms; both
  builders (the EU's other oils and fish, the non-EU market supply functions) use it; eu_market_supply_nq.csv rebuilt
  (817 terms; the 133 before unchanged); the non-EU builder checks the stored terms against CAPRI's p_elasSupp
  (23,647 terms, largest relative deviation 1e-14); run pending (batch-5 gate)

<a id="k99"></a>
### K99: A feed table without builder (feed_requirements.csv) as the fallback of the feed costs and bulks (found 29 October 2026, data declarations)

`capri_data/2017/feed/feed_requirements.csv` (9 animals x 11 feeds, one row per animal for every region) had no
builder; its records disagreed (DATA_SOURCING_REGISTRY "REAL_CAPRI ... fully real", MANIFEST "pigs/poultry synthetic",
a tools/gams note "one of the fully synthetic inputs"). It was read in two places, as the fallback where an animal has
no feed coefficient (livestock_feed_coef.csv, CAPRI's 2017 feed totals over the model's herds): the feed cost change of
the animals without a ration in the supply models (supply_module.py), and the feed bulks passed to the market
(model._set_feed_demand). The 24 cells without a coefficient are all region-animal pairs with no base herd (7 BROI, 9
LAYS, 4 HFRS, 3 PIGS, 1 BULL), so the fallback acted on herds of zero; with BROILER_BIRDS_PER_PLACE (4.35, read only
there).

- **Effect:** none expected in results (zero herds); an input of unrecorded origin kept as a required file
- **In 9t:** –
- **Status:** **fixed** 29 October 2026 (batch 6): the file, its loader and both fallbacks removed (no coefficient: no
  herd at base in CAPRI, so no feed); livestock_feed_coef.csv is now a required input; BROILER_BIRDS_PER_PLACE removed
  from model_parameters.csv; tests and run pending (batch-6 gate)

<a id="k100"></a>
### K100: A national nutrient table without builder (nutrient_coefs.csv) filled three crops' coefficients and fallow's mineral N (found 29 October 2026, data declarations)

`capri_data/2017/environment/nutrient_coefs.csv` holds one N, P2O5, K2O value per crop (no region; SWHE 125.9 kg N/ha)
and has no builder (MANIFEST's vintage summary still calls it synthetic; DATA_SOURCING_REGISTRY records it as replaced
by the regional CAPRI values). It is the base the regional values override:

1. supply models (`_region_nutrients`): CAPRI's regional NITF / PHOF / POTF (sources/capreg/capreg_nutrient_coefs.csv)
   cover every crop with area except OFOD (14.4 Mha, all 221 regions), SETA (7.5 Mha, 208 regions) and WINE (3.0 Mha,
   155 regions), which keep the national values: the extract is keyed by CAPRI's activities (OFAR, ROOF, FALL, TWIN),
   not mapped to the model's. The supply result's nutrient balance and the fertiliser instruments that scale the N
   column read them.
2. environmental accounts (`_base_mineral_rate`, the soil N2O pre-balance loop): CAPRI's regional mineral N (NMIN,
   nutrients_regional.csv) covers every crop but SETA, which takes the national 4.8 kg N/ha: about 38.7 kt of mineral
   N on 8.07 Mha of fallow and set-aside in the EU. CAPRI's 2017 results have no NMIN row for FALL, VSET or SETA (they
   have NITF, a requirement of about 4.3-4.8 kg/ha), so CAPRI spreads no mineral N there.

- **Effect:** mineral N on fallow about +39 kt (of about 9.5 Mt) in the N balance and the emissions; OFOD, SETA, WINE's
  nutrient coefficients national rather than regional in the supply models' nutrient balance
- **In 9t:** –
- **Status:** **fixed** 29 October 2026 (batch 6): tools/build/build_nutrient_coefs_regional.py writes CAPRI's NITF,
  PHOF, POTF on the model's crops (2017/supply/nutrient_coefs_regional.csv: level-weighted over the crop's CAPRI
  activities, the member state's for a crop the region does not grow; 6,517 rows), read by the supply models in place
  of the national table under the extract; the cells that change are exactly the three crops' (area-weighted N: OFOD
  70 -> 158, SETA 4.8 -> 0.47, WINE 70 -> 25 kg/ha; reported in the supply result's nutrient balance, which no result
  table reads). The environmental accounts take no mineral N where CAPRI has no NMIN (fallow, set-aside): EU mineral N
  about -39 kt. nutrient_coefs.csv and its loader removed. Tests and run pending (batch-6 gate)

<a id="k101"></a>
### K101: Model inputs without a builder (census of a run's reads, found 29 October 2026)

K72 closed the inputs without a builder it had found. A census of every file a Green Deal run reads (the run manifest
of a one-region run, lv_gd4, 164 files) against the outputs of the pipeline's builders (tools/pipeline/builders.json)
found 17 read files that no builder writes (settings/defaults.toml aside). Two were of unrecorded origin and are removed
(K99 feed_requirements.csv, K100 nutrient_coefs.csv); the others had a recorded CAPRI source but no code that turns it
into the file.

| File | Source | Status |
|---|---|---|
| policy/landscape_targets_ms.csv, organic_targets_ms.csv | CAPRI's pol_input/greendeal GDX (p_landscapeTargets, p_organicTargetMS, p_organicTargetUAA) | built: build_greendeal_targets.py (tools/lib/_gdx.py), same values (largest relative difference 4e-15: the files held 15 significant digits) |
| shared/eu_market_blocks.csv | CAPRI's aggregation/defaultA.agg section 4 (Norway's former capri-mod row removed 30 October 2026: Norway is its own market region since K56) | built: build_eu_market_blocks.py, byte-identical |
| policy/organic_yield_gap.csv | CAPRI's dat/pesticides/yield_effects_ppp.xlsx, sheet yld_gap | built: build_organic_yield_gap.py (the file held 3 decimals; at most 0.0005 points) |
| supply/yield_price_elasticity.csv | CAPRI's supply/yield_elas.gms with sets.gms CERE_COLS, OILS_COLS | built: build_yield_price_elasticity.py, byte-identical |
| supply/mineral_n_price.csv | CAPRI's res_17 national UVAG of NITF | built: build_mineral_n_price.py (the file held 2 decimals) |
| supply/pmp_own_price_elasticities.csv | CAPRI's PELA (estnlp results.gdx), latest year up to 2005 | built: build_pmp_own_price_elasticities.py, same values (1e-14); the year rule is the committed file's (116 pairs from before 2005; CAPRI's slope forecast reads 2004) |
| market/capri_oilseed_products_baseline.json | CAPRI's FAO_agg p_dataMarket | replaced: only the EU's three cake feed uses were read (the cake index's weights): market/eu_cake_feed_bas.csv, build_eu_cake_feed.py, same values; the JSON removed |
| supply/capri_own_price_elasticities.csv | CAPRI's p_ElasSupp 'CAL' of its 2020 supply-model calibration per member state (supply_elas_2_1720<MS>defaulta.txt and the REMAINI_NG zip) | built: build_capri_own_price_elasticities.py, same values (columns in the files' order of appearance); read by the elasticity-calibrated PMP only |
| sources/arm/capri_supply_elas_market_1717.csv, supply_elas_eu_all.json | CAPRI's elas1717defaulta.gdx p_elasSupp (gdxdump p_elasSupp.txt) | built: build_capri_supply_elas_market.py, both byte-identical as committed; then, at the project lead's decision (29 October 2026), the JSON replaced by 2017/market/supply_elas_eu.csv: the median over the model's 27 member states (was CAPRI's EU28, the UK included), every market commodity under the model's code (OLIV, PARI, SUGR, WINE now found; INPE dropped), full precision. Changes the EU rows' own-price anticipation: run pending (batch-6 gate) |
| sources/capreg/capreg_national_prices.csv | CAPRI's res_17 national MPRI | built: build_capreg_national_prices.py, same values; adds MAIZ, OAR1 and the model's CORN (the 17 regions without a regional maize price grow none), drops COTT and OFIB (copies of TEXT under old codes, read by nothing) |
| shared/model_parameters.csv | each row with its CAPRI or literature source | kept as the declared parameter table (the scalars CAPRI sets in its code); five rows checked against CAPRI's code, all as stated: p_OverFertMarkUp 0.1 and p_fertEffCor 1.1 (envind/ghgMiti.gms), p_trqSigmoidSlope 200 (arm/market_model.gms l. 339, the simulation's; trim_trqs.gms's 50 and 10 are the calibration's), p_elasHigh 4.5 (impose_upper_bound_on_elasticity.gms), p_rhoFeed FMIL 0.5 (arm/market1.gms l. 90) |
| shared/capri_member_state_codes.csv | CAPRI's sets.gms NUTS0 codes and the NUTS prefixes' aliases (BE, LU -> BL; IE -> IR; GR -> EL; GB -> UK) | kept as a declared code map, each row with its source: the aliases are a convention between NUTS and CAPRI, not in CAPRI's sets |

- **Effect:** reproducibility (no result changes from the builders added: the values are the files'; small rounding
  gains); K100's fallow mineral N
- **In 9t:** –
- **Status:** **fixed** (29 October 2026, batch 6 gate). Batch 6: eleven files built, one replaced, the member-state code map
  and the parameter table kept as declared; the EU supply elasticities rebuilt on the model's EU27 (the project lead's
  decision). Left: the census to be repeated on the gate runs' manifests (a full EU run
  reads files a one-region run may not)
  Census repeated on the gate runs' manifests (Farm-to-Fork r188, 162 files read; Green Deal r189, 167): every file
  read is written by a builder of tools/pipeline/builders.json but the two declared tables (the member-state code map,
  the parameter table) and settings/defaults.toml. Closed

<a id="k102"></a>
### K102: Data files that no run and no builder reads (census, found 29 October 2026)

The run manifests of a full Farm-to-Fork run (r186) and a one-region Green Deal run (lv_gd4) list every file the
model's main process reads; the pipeline's trace (tools/pipeline/builders.json) every file a builder reads. Under
capri_data/2017 and shared/, 46 files are in neither. By kind:

- read only under a setting that is off by default (kept): the EU trade blocks' market files (*_eu2.csv,
  market.eu_blocks), the cattle member splits' PMP files and per-sex young animals (K65), the 2017 tariff-rate quotas
  (the 2017 market year), the water module's irrigation, the NUTS 2024 reporting units, the 2017 trade flows;
- written in batch 6 and not yet run (the M3 files, the regional nutrient coefficients, the EU supply elasticities and
  cake weights): read by the batch-6 gate;
- read by nothing and written by no builder: crop_nutrient_export.csv, eu_mfn_tariffs.csv (listed in the loaders'
  file map only), min_share_mineral_fert.csv (K9's floor, superseded by the inner fertiliser distribution),
  nvz_p_soilTypes.csv: **removed 29 October 2026** (batch 6), with their register entries;
- written by an extractor and read by nothing: 17 symbols of CAPRI's ammonia data (tools/build/build_ammonia_tech_inputs.py
  writes every symbol of CAPRI's MITERRA and holdings files: ControlStrat_TS, CorrND, FracNVZNuts2(_full),
  FracToepHouse, FracToepStorage, FracUseFert, PercPeat, ScalarArray, costs/scalars, rCorrND, rLFManureBasis,
  rLFManureND, reducBio, the Nitrates Directive's min shares and obligations) and three of the mitigation inputs
  (p_ccEfa, p_tillageCover, p_winterCoverShare0; build_mitigation_inputs.py): CAPRI's data for parts not ported
  (the Nitrates Directive's NDtech is off in CAPRI's Green Deal runs; tillage, K93) or not needed;
- fao_market_baseline.json: read by a coverage test only (the market reads CAPRI's balances): to be settled with that
  test.

- **Effect:** none on results
- **In 9t:** –
- **Status:** **fixed** 29 October 2026 (batch 6): four orphans removed; the extractors write only what the model or a builder of its
  inputs reads (the project lead's decision, 29 October 2026): 13 ammonia symbols, the cost tables' scalars, three
  mitigation inputs and build_nitrates_directive with its inputs (nvz_p_nvzArea, nvz_p_slopeTypes) and outputs removed;
  p_holdLSU.csv and p_nvzShare_lu.csv given their builder (build_ammonia_tech_inputs with CAPRI's holdingsLSU and
  nvzShare_LU dumps, byte-identical). fao_market_baseline.json and the extended FAO_agg SUA (read only by a coverage
  test of an older market base) removed, the test now on CAPRI's FAO_agg balances (world_market_baseline.json).
  capri_data/sources: of 180 files no run or traced builder reads, 128 are named by no code at all and were removed
  (the project lead's decision, option 2, 29 October 2026: old parameter extractions of CAPRI's GAMS code, FAO 2021 /
  FAO_agg JSON / COCO extracts of the former market base, CAPRI data copies of parts not ported or handled otherwise:
  Norway's MITERRA mirror, anaerobic digestion base data, cost-saving runs, soil carbon, land-use transition, water,
  the IFS maps); kept as reference: the JRC121368 report text and published results, the NUTS correspondences; the
  others are named by a builder or extractor (their own outputs, or read in an untraced invocation). capri_data/archive/,
  DATA_CATALOG.json, SYMBOL_EXTRACTION_MAP.json and the unread extracts and reports listed under K103: removed 30
  October 2026, the project lead's decision, read by no code.
  **Removed 30 October 2026** at the project lead's request, read by no code: the JRC121368 report text, published
  results and scenario specification (jrc121368/), capri_trade_regions_2017.json, the NUTS workbooks
  NUTS_2010_-_NUTS_2013.xls, NUTS2013-NUTS2016__1_.xlsx, NUTS2021-NUTS2024.xlsx and NUTS2024-NUTS2027.xlsx (the NUTS
  tables remain in the project lead's uploads; the CSVs taken from them that code reads, nuts2013_2016.csv,
  nuts2021_2024.csv and nuts2024.csv, stay, written by tools/build/convert_sources_to_csv.py from git history), and the stand-alone
  extract_variable_costs.py with its notes (capri_star/capreg_extracts/; variable_costs.csv is written by
  build_crop_economics_2017.py). NUTS2021.xlsx is converted (nuts2016_2021.csv, read by build_nuts2024_reporting.py).
  The converter writes only what code reads: the miti_data_jul15 dump's four sets, three of the biofuel file's
  parameters (p_secgConv, p_oilEqu, p_density) and the NUTS 2021 classification and change sheets are not written; the
  unread second LitRevFertTech dump (sources/capri_dat/ghgtech, see K103) was removed with them.

### K103: Data files without a known origin or read by no code (data declarations, found 29 October 2026)

With every CSV declared and given its provenance (capri_data/schema/01_provenance.sql) the rule "every data file has
a known origin" finds nine files under capri_data/validation that no builder writes and no source folder or checked
note explains:

- read by no code (the static scan of schema.json and a grep): baseline_reproduction_2030.csv,
  capri_mitigation_shares_2030.csv, capri_pela_own_elasticities.csv, capri_ref_2030_levels.csv,
  elasticity_comparison.csv, greendeal_2030/capri_greendeal_effect.csv, price_structure_vs_capri_scenario.csv (this
  one is not a well-formed CSV: comment lines after the data; the validator reports it);
- read by checks and a test: capri_eu27_levels_2017_capreg.csv (tools/check/compare_baseline_capri.py),
  capri_eu27_levels_2030_ref.csv (the same, tools/check/compare_outlook_2030.py and test_capri.py); both arrived in
  the repository's first commit, without builder.

The check of the registry's notes (02_provenance_notes.sql) found three source extracts read by no code:
sources/capreg/capreg_nutrient_coefs.csv (build_nutrient_coefs_regional reads CAPRI's dumps directly),
capreg_manure_nutrients.csv and sources/capmod/capmod_world_prices_2017.csv (the world-price checks read
capmod_world_reference_2017.csv). sources/capri_dat/ghgtech/LitRevFertTech_p_litRevFertTechs.csv is a second, fuller
dump of the table that sources/ghgtech/LitRevFertTech_p_litRevFertTechs.csv holds (the one build_fert_side_effects
reads); no code names the first.

- **Effect:** none on results
- **In 9t:** –
- **Status:** **fixed** 29 October 2026 (the project lead's decision): the seven unread validation files and the
  three unread extracts removed (extract_all_from_data2, extract_remaining_nine and ingest_capmod_market no longer
  write them); the two reference files given a builder, tools/build/build_capri_eu27_levels.py (2030: dataOut EU27yr19
  LEVL of markmarket_greendeal_1730et_base_1717, reproduced exactly; 2017: the 26 CAPREG dumps summed, equal to the
  old file's four decimals, now at full precision). sources/capri_dat/ghgtech/LitRevFertTech_p_litRevFertTechs.csv
  (unread second dump) removed 30 October 2026 (K102); further builder outputs that no code reads remain to be settled (see the census in
  capri_data/schema/schema.json, read_by).
  **Removed 30 October 2026, the project lead's decision, read by no code** (an audit of the files read neither by the
  runs r190/r191 nor by a builder; each grepped again across code, tests, docs, schema and the pipeline trace), their
  writers stopped: sources/baseline_pmp/pmp_cnst_2030.csv and pmp_cnst_landtypes_2030.csv (build_pmp_2030),
  sources/baseline_pmp/simini_21730_data.csv (no writer; its reader build_pmp_recipe.calibration_point_2030, never
  called, removed too), sources/capmod/capmod_trade_flows_2017.csv.xz (ingest_capmod_market, which now writes only its
  uncommitted summary JSON), sources/capreg/capreg_cost_components.csv.xz (extract_all_from_data2),
  capreg_feed_use.csv, capreg_herds.csv, capreg_land.csv (extract_remaining_nine), sources/estnlp/gtap_armington.csv
  (ingest_pela_gtap, its GTAP part removed), validation/greendeal_2030/capri_marginal_terms_max_2030.csv.xz and
  capri_unit_values_max_2030.csv (extract_capri_marginal_terms: the max invocation removed from the pipeline trace
  and reproduce_builders), sources/world_price_provenance.csv (build_world_prices; its content summarised in the
  origin note of world_prices.csv, 02_provenance_notes.sql); the metadata DATA_CATALOG.json, SYMBOL_EXTRACTION_MAP.json,
  trajectories/TEMPLATE.json, validation/VALIDATION_SUMMARY.json, capreg_merge_report.json,
  capreg_yield_validation.json, coco_yield_merge_report.json, livestock_merge_report.json, documentation_answers.json,
  schema_coverage.json (tools/check/verify_schema.py --json writes it only where asked), greendeal_2030/summary.json
  and validation_result.json; and capri_data/archive/ (seven superseded files and its README). Kept:
  pipeline/captrd/sets/fixyield.csv (CAPTRD's FixYield, read once CAPTRD's Steps 2-3 are ported).

### K104: The payments report's area left fallow out of CAPRI's UAAR (found 29 October 2026, data declarations)

cap_payments.csv's BPS is CAPRI's premiums per ha of UAAR (UAAR PRME; tools/build/build_crop_economics_2017.py), and
CAPRI's UAAR holds the fallow land (SETA, FALL; base_areas' SETA column). The DirectPaymentsEngine
(capri_mod/policy/policy_module.py, compute_payments_by_region) multiplied it by arable + permanent + grassland only,
without FALLOW: AT110000 175.9 kha against CAPRI's 190.3. The EU total of the baseline payments was 46.9 bn EUR
(regression anchor 54.0 +- 6), 49.1 bn EUR with fallow.

- **Effect:** the policy report's payment totals only (the crop premiums in the margins come from crop_premium.csv
  and livestock_premium_coef.csv)
- **In 9t:** yes
- **Status:** **fixed** 29 October 2026: the area is the four land columns, CAPRI's UAAR

### K105: Numbers in the model's code to check, register or move to the settings (found 29 October 2026)

The census of the numbers held in the model's code (capri_data/schema/03_code_data.sql, classified in
04_code_data_status.sql; docs/design/PROXY_AUDIT.md) left five with an action; the project lead's decisions (29
October 2026):

- the manure-application limit (SupplyModule._manure_limit: 170 kg N/ha, or 1.001 x the base rate where higher): it
  built the manure_application row of the N-surplus scenarios (manure N <= limit x crop land), capri-mod's own, and
  the function returned None on any error (the manure terms then silently absent). The classification first said the
  limit was read nowhere; it was read. CAPRI's default runs have no such row: manure is tied to land by the crop
  nutrient balance (NUTNED_, fertDistExcr_, ManureNPK_, supply_model.gms l. 870-947 and 1095-1212) with manure trade,
  which the NLP form ports; the Nitrates Directive's cap is NDman (envind/envConstraints.gms l. 2876-2933), whose
  switch the Green Deal policy file sets only after an $exit. **Done** ("as CAPRI", the project lead's decision): the
  row, the limit and MANURE_LIMIT removed (the NLP form already dropped the row); _manure_per_head gives the manure
  per head and lets an error stop the solve. Found with it: the split columns (dairy, cattle, genetics) took their
  manure factor for NUTNED_ from the manure or N row, which exist only with an N target, so without one their manure
  did not reach the nutrient balance; the factor now comes from the tables (dmann_rel, d_mann_rel) in every run, which
  can move results of runs without an N target;
- capri_mod/data/validate_data.py _check_margins capped specialty-crop costs at 2 x the median, a cap the loader had
  dropped: **removed** (the check sees the model's costs; 12 pass, 0 warn);
- BilateralCommodity's export cap at 0.98 of the model's base supply (PROXY_AUDIT S192): a consequence of step F (the
  market calibrated to the supply models' baseline, where a region's base production can fall below CAPRI's recorded
  exports): **removed** with K106 (the market's base made CAPRI's production of the market year; exports scaled only
  where they exceed the base supply, which no cell does after the 30 October rebuild: 0 of 1,228 cells off by more than
  1e-4);
- PMPCalibrator.calibrate's 0.05 cap on PELA / p_pmpQuadPact cross terms of crops without CAPRI's terms (S065):
  **removed** with the path, its two inputs' loading and sources/estnlp/pela_cross_by_region.json (no longer written);
  such crops have diagonal rows, as in CAPRI's QUADRA_; default runs unchanged (with CAPRI's terms the path was
  skipped). Found with it: supply.pmp_cross_terms = "none" did not act on CAPRI's terms (the default ones); it does now;
- CAPRIModel._run_scenario's adaptive price step for Norway (1.25, 0.5, 0.1) now reads outer_loop.relax_step_up,
  relax_step_down and relax_floor (the same values): **done**.

- **Effect:** none on default results from the checks, the settings with equal values and the path the default skips;
  the split columns' manure in runs without an N target is a correction that can move results
- **In 9t:** yes
- **Status:** fixed (all five done 29-30 October 2026; the export cap with K106)

### K106: The market's base supply of crushed and biofuel products was not CAPRI's production of the market year (found 29 October 2026)

The market keeps CAPRI's bilateral flows of the market year and calibrates each region's domestic sales as its base
supply S0 minus those exports; an export cap at 0.98 of S0 (PROXY_AUDIT S192, not CAPRI's) bound in 42 commodity x region
cells at the 2017 base. In 34 of them CAPRI's own data were consistent (a region exporting 98-100% of its production,
Indonesia's coffee 99.99%) and only the cap changed CAPRI's flows; in 8, CAPRI's exports exceeded S0. In CAPRI's market
data all 8 are consistent: S0 did not come from them. 110 of 1,135 non-EU cells had S0 differing from CAPRI's production
(prod_kt of bilateral_regions_<year>.csv) by more than 1e-4, all from two blocks:

- crushing: crush and yields from FAO_agg's base period (p_dataMarket 'BAS', the raw data before CAPRI's market
  calibration), where CAPRI's calibration sets PRCY = Prod / Proc (clamped outside RMSSUP) and Prod = Proc x PRCY
  (arm/calibrate_market_data.gms l. 72-82, 1123-1130): Australia's soybean oil yield 0.1776 against CAPRI's 0.1937;
- biofuels and DDGS: the files held only CAPRI's 2030 reference (the builder hard-coded the year), so a 2017 market ran
  with 2030 output (Argentina's biodiesel 1,862 kt against 2,819 in 2017; New Zealand's DDGS 4.45 against 6.73), the EU
  rows included.

- **Effect:** the market's calibration at the 2017 base (oils, cakes, biofuels, DDGS; the 2017 market year's runs) and
  at 2030 (29 crushing cells above 5%); results move
- **In 9t:** yes
- **Status:** **fixed** 30 October 2026: crushing_parameters_<year>.csv from CAPRI's market data of the year (PROC,
  PRCY; p_ElasProc of the year's calibration); biofuel_feedstock/market/use_share_<year>.csv per market year
  (build_biofuel_market.py --year; CAPRI's "RW" aggregate of the 2017 data excluded; a non-positive feedstock cost is
  an error, no group dropped); the market reads the files of its market year (MarketModule._market_year). At the 2017
  base the cells with a gap above 1e-4 fell from 110 to 15, all from the UK: the new files map it to GBR, the bilateral
  market files still to ROW (the batch-7 rebuild on 32 regions). The 0.98 cap is removed: exports are scaled only where
  they exceed S0, which CAPRI's data no longer cause outside the rows set by the supply models (step F); such hits are
  logged in the run metadata and warned.

<a id="k107"></a>
### K107: The regional model's emission tax on mineral N took IPCC's factors while the accounts take CAPRI's MITERRA fractions (found 31 October 2026, UreaSubst scoping)

CAPRI taxes the soil N2O of the mineral N bought through its loss fractions: N2OSYN = N bought x emiLoss(NETF, N2O,
GasTot) and the mineral part of N2OAMM = N bought x (emiLoss(NETF, NH3) + emiLoss(NETF, NOx)) x EF4
(supply/supply_model.gms l. 3708, 3793). The accounts and the manure-trade terms moved to these fractions on 27
October 2026 (K74 S12, `_ef_mineral_n2o`), but the regional model's tax on the purchases (`AbatementBlock._nlp_tax_terms`,
the d and v terms) kept IPCC's EF1 (1%) and 10% x EF4. In DE11 the direct part is 1.067% against 1% and the indirect
0.039% against 0.1%; the sum differs by under 1% (1.107% against 1.1%); the nitrification inhibitor's side effects (N2OSYN, NH3SYN)
apply to the two parts separately, so its tax value takes the split as well (not measured).

- **Effect:** emission-tax runs only (the term is built only with a tax); the Farm-to-Fork and Green Deal runs have none
- **In 9t:** –
- **Status:** **fixed** 31 October 2026: `FertilisationBlock._mineral_n2o_parts` returns the two parts (MITERRA, IPCC's
  factors where CAPRI's fractions are missing, as before), used by `_ef_mineral_n2o` and by the tax terms; test
  `test_tax_on_mineral_n_takes_the_accounts_miterra_factors`

<a id="k108"></a>
### K108: Inputs from CAPRI's 2030 results in 2030 money in a model that works in 2017 money (found 31 October 2026, anaerobic digestion check)

The 2030 runs work in 2017 money: CAPRI's 2030 prices and premiums divided by CAPRI's general inflation 1.019^13 =
1.2772 (tools/build/build_price_trajectory_2030.py, capri_price_ratios_2030.csv), input costs at 2017 values. CAPRI's
own 2030 calibration and results are in its 2030 money: it inflates costs and mitigation parameters by p_infl^(2030 -
2017) (e.g. envind/ammo_tech.gms l. 3355-3358) and its PMP terms are calibrated on its 2030 prices (the recipe matches
CAPRI's terms only with p_infl since 2004, docs/PMP_CAPRI_2030.md). Found so far without deflation:

- CAPRI's crop PMP matrix (pmp_capri_2030.csv, the default pmp_source "capri2030"; supply_module.py capri_g, Q_ij = g_ij
  / sqrt(x_i x_j)) and the other 2030 terms of that source (animals' herd terms, intensity splits);
- anaerobic digestion: every money term x 1.019^13 (tools/build/build_ad_option.py INFL);
- the catch crops' cost (cover_crops.csv catc_cost_eur_ha = CATC TOIN of CAPRI's 2030 reference) and the winter-cover
  option built on it;
- the 2030 land rents (land_rents_2030.csv, D_AREA of CAPRI's 2030 reference);
- possibly the 2030 CAP ceilings (cap_ceilings_2030.csv) beside premiums in 2017 money (to check).

**Audit of the builders, 31 October 2026** (read-only; defaults pmp_source "capri2030", pmp_capri_parts crops, animals,
feed, land). In 2030 money and used by the 2030 runs, ranked by expected effect on the responses:
1. crop PMP matrix (build_pmp_capri_2030.py, supply_module.py capri_g);
2. animals' herd terms (build_animal_pmp_capri_2030.py; loaders put them into capri_g);
3. fertiliser prices of the fertilisation block (npk_region_2030.csv uvag_eur_t, CAPRI's 2030 UVAG: Austria's N
   1,110.5 EUR/t against 869.5 in 2017, ratio 1.2772; read by the NLP objective and the fertiliser options' NITF
   price), while the fertiliser allocation reads mineral_n_price.csv in 2017 money;
4. land market: the land types' quadratic terms (land_market_2030.csv, p_pmpQuadLandTypes) and the 2030 land rents
   (land_rents_2030.csv), also in the greening dual;
5. intensity splits' 2030 terms (q_*_capri2030 of the dairy, cattle and grass intensity files);
6. feed PMP slopes (feed_ration capri_slope_2030);
7. catch crops' cost and the winter-cover option's curve (CATC TOIN 2030);
8. anaerobic digestion (inflated on purpose, unlike the other ammonia options of the same file);
9. CAPRI's cost savings (capri_costsavings_2030.csv, dsav) in the genetics, low-N feed and supplement options, and
   genetic improvement's cost per unit (2030 UVAG of COMI).
Report-only: CAP budget ceilings (budget use) and the set-aside premiums of the labour table. In 2017 money (fine):
prices and premiums, histosols, 3-NOP cost, the ammonia options other than AD, the fertiliser options (miti_data_jul15
before CAPRI's inflation; their saving slope takes the 2030 NITF price, item 3), feed ration prices, young animals,
plant protection, mineral_n_price. Unsettled: welfare_base (market data of 2030 with INPE 1.2772; cancels in run
differences). The deflator for all items is 1.019^13 (CAPRI's 2030 terms carry p_infl since 2004, the model's prices
13 years from 2017).

Deflated already: histosol fallowing, the feed supplements (3-NOP), premiums and prices. The ammonia technologies are
in 2017 money (CAPRI inflates them; the model takes them before that step), consistent.

- **Effect (expected, not measured):** with curvature in 2030 money against prices in 2017 money, the crops' (and
  animals', where CAPRI's terms are used) price responses are 1/1.2772 of CAPRI's, about 22% weaker; an earlier check
  fits it (Austria's rapeseed elasticity 9.7 against CAPRI's 12.4, K61; 12.4 / 1.2772 = 9.7). The Farm-to-Fork and
  Green Deal results move
- **In 9t:** ?
- **Status:** **open**: audit of every input built from CAPRI's 2030 results under way (31 October 2026); fix after
  gate 10 (the project lead's decision: gate 10 runs as prepared, the money-year fix is gate 11): divide the 2030-money
  inputs by 1.019^13, the deflator the prices take
