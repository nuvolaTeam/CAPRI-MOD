# Known issues and bugs (from October 2026)

Found by running the model, its tests and the NLP check (`tools/nlp_check`: the regional problems in CAPRI's original
form, solved with IPOPT). The tables give one line per issue; the details follow below, one section per issue: what
was found, where it acts, whether the tagged release 9t (`capri-mod-9t.zip`) carries it, and its status. 9t.1 is 9t
with every fix below except K5, which needs the prototype's model change.

The data sourcing registry's log of checks, fixes and decisions (201 entries, moved 29 October 2026) is in
[KNOWN_ISSUES_REGISTRY_LOG.md](KNOWN_ISSUES_REGISTRY_LOG.md), verbatim, with the triage of its open entries against
the code: they became K92-K96, joined K73, K80, K91, or were closed or historical.

## Open (30)

| # | Issue | Status |
|---|---|---|
| [K13](#k13) | Farm-to-Fork milk price | open: waiting for CAPRI's scenario results |
| [K29](#k29) | NL11 and NL13 meet the tiered N target only at corner solutions (Farm-to-Fork) | open: waiting for CAPRI's scenario results |
| [K47](#k47) | The cattle chain's equilibrium is sensitive to changes outside it | open |
| [K48](#k48) | Young-animal prices against CAPRI's own market run | open |
| [K65](#k65) | Cattle member splits and per-sex young-animal markets do not converge yet | open |
| [K66](#k66) | Farmland expands under the per-hectare N target more than in CAPRI | open: waiting for CAPRI's scenario results |
| [K78](#k78) | Histosol fallowing under Farm-to-Fork far above JRC121368's figure | open: waiting for CAPRI's scenario results |
| [K79](#k79) | Member-state production that keeps moving between iterations | open |
| [K92](#k92) | Farm-to-Fork changes furthest from JRC121368, besides the milk price | open: waiting for CAPRI's scenario results |
| [K93](#k93) | CAPRI mitigation options not built; documents disagree on which are in | open: no-till and legume share unmeasured; UreaSubst parked; the others not needed for Farm-to-Fork and the Green Deal |
| [K120](#k120) | S7 ("capri"): the market supply Hessian measured after the first supply solve had lost most of its response; the baseline calibration's stall rule stopped it uncorrected | fixed: 20 and 37 units, full EU Farm-to-Fork and Green Deal (7 November 2026); open in S7: the baseline calibration's first-round drift (9 November 2026: not the ecological set-aside row; the baseline's prices move up to 1.3% from CAPRI's calibration point; at the baseline's end the crop levels are within a median 0.22% of CAPRI's 2030 levels, 7 region pairs above 5%; 9 November 2026, night: most of the remaining gap was the projection rescaling CAPRI's own 2030 levels to the 2017 crop-to-land ratio, fixed) |
| [K121](#k121) | S2 step 1a: other fodder split into CAPRI's OFAR and ROOF; the fodder roots' feed (FROO) tied to their land for the first time | done on mini-EU (7 November 2026); the full runs and the suite to come |
| [K122](#k122) | S2 step 1b: set-aside split into CAPRI's VSET and FALL; the winter-cover option's potential counted set-aside CAPRI fills | done on mini-EU (7 November 2026); the full runs and the suite to come |
| [K123](#k123) | S2 step 1c: grassland split into CAPRI's GRAE and GRAI, the split column z and its late calibration removed; fodder roots' 2030 fodder trajectory was missing since 1a | done (8 November 2026): suite, mini-EU, full-EU Farm-to-Fork and Green Deal |
| [K124](#k124) | S1: CAPRI's two crop technologies T1 and T2 as one mix column per crop; five approximations registered | done (8 November 2026): mini-EU, full-EU Farm-to-Fork and Green Deal; CAPRI's setting the default |
| [K125](#k125) | S7, CAPRI's market calibration, the model's only form: the "supply" form and its setting removed; ten tests written for the old form adapted | done (9 November 2026); the scenario-shifter layer (S7 step 5) still to build |
| [K126](#k126) | The CasADi trade system left out the quota price offsets of a commodity with global quotas only (casein), in the optional exact-Jacobian and Newton-Krylov solves | fixed (9 November 2026); the default solve unaffected |
| [K127](#k127) | Under CAPRI's market calibration (S7) an emission tax leaves N manure trade at zero in a four-unit Belgian run where the former form traded 360 t | open (9 November 2026): cause not established |
| [K128](#k128) | Farm-to-Fork's meat prices against JRC121368: beef +29.5% against +24.0%, poultry +20.4% against +18.0%, pork +20.5% against +43.0%, with EU production close to CAPRI's | open (9 November 2026): the market's inputs checked against CAPRI's (base, demand elasticities, Armington, quotas), no departure found; needs CAPRI's own scenario run on the same version |
| [K129](#k129) | BG020000 under the Green Deal: the coupled iteration settles on one of two branches of the region's response (maize 169 or 16 thousand ha between two runs); each iteration's problem mostly has one solution the starts agree on | open (10 November 2026): the branch follows the market iteration's path; more starts per solve did not change it (tried and dropped) |
| [K130](#k130) | Catch crops' cost per ha is CAPRI's reported TOIN of CATC, not its cost coefficients; where CAPRI's Green Deal baseline has no catch crops (160 of 250 units), the calibration run's TOIN | open (9 November 2026): to read CAPRI's own cost data of the winter-cover technology |
| [K131](#k131) | Given CAPRI's own Green Deal supply, the market's EU prices follow CAPRI's within 0.3 points on average, but the dairy protein products rise 2-5 points more and butter 1 point less | open (12 November 2026): not yet traced |
| [K138](#k138) | CAPRI's new energy crops (NECR, 251 kha of the EU's 2030 crop area) are not a model activity | open (13 November 2026) |
| [K139](#k139) | PL340000 converts all its forest to farmland in the Green Deal 2030 run (crop area +45% against CAPRI's -2%) | open (13 November 2026) |
| [K140](#k140) | P2c, the rural development port: 286 of 20,098 effective RD premiums differ from CAPRI's 2030 reference (Praha's rates, Ile-de-France's inherited LFA cut, Sweden's technology-differentiated extensification measure) | open (13 November 2026); in the model's 2030 premiums since P2 step 2 |
| [K142](#k142) | P2c, the BPS key (the MTR port): Croatia's key not found in CAPRI's chain (a uniform IUV used); sim_ini's NA sheep rates of 2002 taken as absent; France's Corsica 5% below CAPRI's 2030 BPS rate | open (13 November 2026) |
| [K143](#k143) | A regional premium factor on animals compounded at every solve (livestock_premium_coef not restored) | fixed (13 November 2026) |
| [K144](#k144) | CAPRI bug: Norway's output payments (DPNOR6, DPNOR7) pay nothing in the simulation year (policy.gms l. 97 reads the yields at the year's column) | closed (13 November 2026): a CAPRI bug, kept as CAPRI computes it |
| [K145](#k145) | The 2030 premium of wine (WINE) was never set from CAPRI's 2030 TWIN: the model kept the 2017 premium in 2030 | fixed (13 November 2026) |
| [K146](#k146) | Switzerland's market supply responded to its market prices as if its producer prices carried no support per tonne (CAPRI's PPri_ adds PSEd): its price terms too large by PPRI0 / (PPRI0 - PSEd), soya 1.83 times | fixed (13 November 2026) |

## Resolved (115)

| # | Issue | Status |
|---|---|---|
| [K141](#k141) | CAPRI bug: CAPRI's BPS convergence takes the overshoot left after the 30% rule off the low units in million EUR per thousand ha, without the factor 1000 (implement_bps.gms l. 309) | closed (13 November 2026): a CAPRI bug, kept as CAPRI computes it (the project lead's decision) |
| [K136](#k136) | CAPRI's endogenous entitlement limit (def_endCut.gms: no area payment beyond the trend area) was not in the model; ported with CAPRI's 2030 ceilings computed from its CAP 2014-2020 tables | fixed (13 November 2026) |
| [K137](#k137) | The reported UAA left out the idled histosols (CAPRI's IHISGR, IHISCR stay in GRAS, ARAC and UAAR): the Green Deal's surplus per ha looked short of its target where the row met it | fixed (13 November 2026) |
| [K135](#k135) | The Green Deal targets reached the regions by their country, not through CAPRI's geo_to_ms maps: Portugal, which CAPRI maps to no target, took its GDX values; Luxembourg its own instead of Belgium's | fixed (13 November 2026) |
| [K134](#k134) | The activity bounds of one technology for crops with CAPRI's two (T1, T2) | fixed (13 November 2026) |
| [K133](#k133) | Fallow held under 10 x its level when the landscape floor needs more (CAPRI: 0.5 x UAAR per technology) | fixed (13 November 2026) |
| [K132](#k132) | The voluntary set-aside exempt from the absent-activity rule everywhere; it grew from zero where CAPRI's data have none | fixed (13 November 2026) |
| [K108](#k108) | Inputs from CAPRI's 2030 results in 2030 money in a model working in 2017 money | fixed (gate 11, 31 October 2026) |
| [K77](#k77) | CAPRI's fertiliser-option curvature (S5) leaves the baseline's base shares | decided (31 October 2026): the model's calibration kept, a deliberate departure (DEP-30) |
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
| [K110](#k110) | The market's Newton-Krylov solve did not converge on a real shock; its test had passed without one | fixed |
| [K111](#k111) | The set-aside report booked part of a set-aside increase as VSET where CAPRI has none | fixed; the split itself removed with K122 |
| [K112](#k112) | Histosols: regions without a JRC record took their country's share; Greek grassland had no N2O | fixed |
| [K113](#k113) | Croatia had no AD option: CAPRI's fallback_Balkan fills its VSER and housing share | fixed |
| [K114](#k114) | Norway lacked CAPRI's mirrored MITERRA data and Sweden's AD data: no housed liquid manure, no AD | fixed |
| [K115](#k115) | The 2030 set-aside followed CAPRI's VSET alone, not FALL + VSET: up to half or double CAPRI's per region | fixed |
| [K116](#k116) | The CAPRI-reference trajectory kept the trend projection's [0.2, 5] band, 1.0 threshold and missing zeros; OFOD grew as OFAR alone | fixed |
| [K117](#k117) | The full-EU market did not converge in Farm-to-Fork: the EU's sugar quotas switched on and off at every step | fixed |
| [K118](#k118) | The market supply Hessian's cache key did not cover the supply data: a data change could reuse a stale Hessian | fixed |
| [K119](#k119) | The CAPTRD trajectory took CAPRI's "Pigs total" aggregate for the model's PIGS (CAPRI's SOWS) since K116 | fixed |

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

- **Measured 11 November 2026 on CAPRI star 3.0's own Green Deal 2030 run** (the project lead's, against its reference; full-EU greendeal2030, damped manure pool prices; not the Farm-to-Fork of JRC121368): milk price +8.0% against CAPRI's +11.2% (an under-response, the opposite of the Farm-to-Fork overshoot).
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

- **Measured 11 November 2026 on CAPRI star 3.0's own Green Deal 2030 run** (the project lead's, against its reference; full-EU greendeal2030, damped manure pool prices; not the Farm-to-Fork of JRC121368): NL110000 and NL130000: voluntary set-aside +3.9% and -7.1% against CAPRI's -98% and -100%, sugar beet -17.0% and -6.7% against -2.0% and +1.9%.
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

`CAPRIModel.supply_form = "nlp"` (the default since 20 October 2026, see Status): feeding (REQSE_ equalities, FEDUSE_, QUADRF_), fodder balances as equalities, NUTNED_ for N, P2O5 and K2O per crop group with the inner fertiliser model's FOCs inside, mineral purchases priced at CAPRI's unit values, endogenous manure availability, CAP greening (permGras, ecoSetAside 5%, cropDiv Shannon), the N-surplus target with the purchases, the mineral caps and the organic area target as CAPRI's regulations, ammonia/fertiliser/inhibitor options with CAPRI's loss cascade, the emission tax; LUC transitions after each solve. Calibrated so the base is a first-order point. REGISTERED departures: (1) need multiplier per region and nutrient, on need net of the permanent crops' own residues (model base levels with CAPRI's 2030 coefficients; since 31 October 2026 only where CAPRI's form, the multiplier on the need alone, leaves a permanent group no need of its own: 5 Romanian N cases with manure trade, 10 without, STRUCTURAL_GAPS_PLAN S3); (2) CAPRI's fertiliser calibration (blanket priors, posterior at the model's base) where CAPRI's 2030 posterior admits no allocation at the model's base (RO21, RO22, RO31, RO41, RO42, ES62, HU11 in the 2017 baseline); (3) inner-model dual bound +-1000 instead of +-10 where a tiny crop group needs more (HU11; CAPRI's own workaround is v_fertDistPartialSlack); (4) P and K manure trade follows N trade in the region's proportions (removed 31 October 2026: CAPRI's MANP and MANK markets of their own, STRUCTURAL_GAPS_PLAN S4); (5) one need multiplier per region instead of per technology; (6) Shannon term + 1e-6 kha instead of 1e-10 (IPOPT's bound relaxation); (7) the ecological set-aside rule held at the base where the model's base data do not meet it; (8) LUC solved after the regional model (identical without a LULUCF price; its priors centred on CAPRI's 2030 solution, not CAPRI's observed transitions: S6 item 6, 9 November 2026, to be fixed with S13); (9) the conic form's manure-application limit and mineral-N allocation column dropped (not CAPRI's); (10) the group's organic conversion for CAPRI's organic caps is capri-mod's per member state and crop class (the shares of the organic I/O change), weighted by base area; (11) where the Green Deal's mineral caps leave a group's need unmet (IPOPT infeasible), the inner model's duals are widened to +-1000; if that is not enough, the groups concerned are exempted one at a time, those whose need is out of reach under their cap first, with their cap at the baseline mineral N per ha (CAPRI's p_checkSmallMine in minfert_redu_by_crop.gms; CAPRI lists its exempted region x group pairs by hand, capri-mod finds them by solving; K71); recorded as nlp_relaxed ("caps:PERM"); (12) the split columns' manure (dairy, cattle, genetics) reaches ManureNPK_ in the proportion of their manure per head to their animal's (since 9 November 2026 N, P2O5 and K2O at CAPRI's 2030 terms for the dairy and cattle splits, N for genetics: S6 item 6)

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
- **Status:** **fixed** 20 October 2026 (the user's decisions): (a) FARM_TO_FORK, FLAT_RATE_BPS, UKRAINE_SHOCK and the unused WORLD_PRICE_SHOCKS removed (CAPRI's Farm-to-Fork: `policy.greendeal.farm_to_fork_scenario()`); (b) `trq_volume_changes` acts on CAPRI's EU tariff-rate quotas in the bilateral market (1000 t per commodity, spread over the exporters' quotas by base volume, base fill kept at the base quotas; `MarketModule._apply_trq_volumes`), a commodity without a CAPRI quota raises an error; the TRQHandler with its hand-entered quotas removed; (c) a shocked run is a scenario against the unshocked baseline; (d) 0 read as given; (e) docstring corrected (the organic yield gap applies in full; CAPRI's 0.45 only with pest_disagg on); (f) a base year other than 2017 raises an error; 2 November 2026 (the project lead's decision): the base year is a parameter of the run, every reader of the model takes it from the run's inputs (folders and file names, the market year's default, the loader's file map), a base year without a data folder stops naming the years with data (capri_mod/tests/test_base_year.py: the 2017 data under the name 2018 load the same); the builders (tools/build) keep 2017; (g)-(k) fixed before; (l) CAPRI's gross phosphate balance (calc_nbalance.gms with PHOF, in P2O5) fills the P columns, and `organic_area` is the area the organic target converts (docs/P_BALANCE.md); (m) a trajectory `demand` factor other than 1 raises an error: the market's demand of a target year is CAPRI's market data of that year, and a demand factor alone has no consistent closure in the calibrated bilateral market (flows and supply fixed)

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
- **Status:** **open**, narrowed 23 October 2026 (night). The price update now takes each region's response from its solved NLP (`CapriRegionalNLP.response`: the implicit-function theorem on the KKT conditions, in the active rows' null space; `RegionalSupplyModel._yani_response`), on by default with the member splits. Checked: against finite differences on FRH0 the cattle goods' own responses agree within 1% (piglets within 20%); a price change reaches the regional objective as predicted. On 12 regions the markets reached 0.005 in 8 iterations (PMP terms: 0.016 after 8). The full Farm-to-Fork run (r96) still did not converge: the male calves' price rose to 6.1 x base and the female calves' fell below zero (-0.37) before the imbalance swung back up (0.03 -> 0.21). Under Farm-to-Fork the EU is short of male calves (fewer dairy births, fattening barely lower) and the calf activities hit their zero bounds, so the response nearly vanishes and the sexes' prices run apart. Next: compare the per-sex calf use and its flexibility with CAPRI (the calf activities' own PMP terms, CAPRI's per-sex young-animal prices in its Farm-to-Fork results, tools/gams/export_capmod_results.gms) before judging whether such prices are CAPRI's equilibrium or a defect here. Off by default. **Deferred, 23 October 2026**: CAPRI's own per-sex Farm-to-Fork results, needed to judge the prices, do not exist on the project lead's installation; it stays a DEPARTURE from CAPRI's setting (docs/DEPARTURES_FROM_CAPRI.md) until the divergence is understood from the model itself (the calf activities at their zero bounds). **13 November 2026**: the project lead agrees to bring the replacement heifers, the calves and the per-sex young-animal markets to CAPRI's setting where possible; scheduled after P2. Retried the same evening on CAPRI's own path, which did not exist when r89-r96 ran (22-23 October): since K75 (24 October) the young-animal markets clear inside the market model (yaniMarket_ with the market supply Hessian's young-animal rows, measured per good: the per-sex table holds CAPRI's seven goods YCAM, YCAF, YBUL, YHEI, YCOW, YPIG, YLAM), the outer loop passing the prices on as the products'. Mini-EU Farm-to-Fork with supply.use_cattle_member_splits (mini_k65_splits): converged in 14 iterations (7 with the pooled goods), young-animal imbalance 0.0033 (tolerance 0.005); EU_WEST female calves 1.55 x base, male 1.19 (pooled 1.34), young heifers 1.10, bulls 1.03; the Farm-to-Fork indicators within 0.4 point of the pooled run. Full-EU Farm-to-Fork (full_f2f_k65, 13 November 2026, evening; not saved): the market supply Hessian measured in 2,157 s (1,882 without the splits); CAPRI's stop rule on prices and quantities met from iteration 15 (largest change then 0.002%), the market balances within 5e-9, but the young-animal imbalance fell by a near-constant 2.9% per iteration (0.111 at the first scenario iteration, 0.022 at the 6th, 0.0096 at the 28th, 0.0051 at the 49th) and the run reached its 7,180 s limit in iteration 50, just above the tolerance. So the splits converge on the full EU, but about 35 iterations after the prices and quantities have settled (14 iterations without them). Next: which good and market lag (the young-animal detail per iteration on the mini-EU run), and why the market's clearing corrects only 3% of the imbalance per step (a price at its bound, or the market's young-animal response far above the supply models'). The default stays off.
Diagnosis on the mini-EU Farm-to-Fork with the splits (14 November 2026, night; the young-animal markets' state written per iteration, scratchpad k65_diag.py): converged in 14 iterations; the first scenario iteration opens gaps of 20-31% (EU_WEST male and female calves, the young heifers and bulls), closed to under 2% by the fifth; then the EU_EAST young bulls and heifers hold a gap of 1.3-3.1% for five iterations (young bulls -2.0, -2.4, -1.8, -1.6, -1.4%) while the market clears them at almost the prices the supply models saw (young bulls 0.9743 against 0.9747): at the seen young-animal prices the market's clearing (yaniMarket_ with the measured Hessian, recalibrated to the supply models' latest net supply) attributes the gap to the product prices' change through the Hessian's cross terms, and the supply models' response to those prices does not close it. To test next: the cross terms of the young-animal rows against the supply models' response between iterations, and a re-measured Hessian at a scenario iteration (market.hessian_scenario_iter; CAPRI's practice is a question for Bonn, bonn_notes_solver Q5). Tried 14 November 2026 (morning; the same mini-EU run with market.hessian_scenario_iter = 2): worse. The EU markets follow the first run to the third scenario iteration (calves 25.3% then 19.1% instead of 10.2%), then Norway's young-animal market, with its Hessian measured again at the scenario's state, moves away (the largest gap Norway's at every iteration from the fifth: young animals -93%, -272%, -236%, -196%, calves -176% to -180%); not converged after 14 iterations, stopped by the run's time limit at 4,800 s (the first run: 14 iterations, 656 s). So a scenario-state Hessian is not the way to close the EU_EAST gap; the cross terms remain to test.

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

Four cases: (1) `supply_elasticities_regional.csv`: it is CAPRI's PELA 2005 own-price slice (`sources/intermediate/estnlp/pela_own_price.csv`) with CAPRI's upper-bound rule, cell for cell; new builder `tools/build/build_supply_elasticities_regional.py` (`--check`: reproduced). (2) The files patched in place by several builders: new driver `tools/build/build_patched_inputs.py` runs build_crop_economics_2017, build_eu_producer_prices, build_animal_yields, build_dairy_trade_params, build_demand_elas_capri, build_feed_byproducts, build_feed_demand_nonEU in that order (feed_demand_nonEU must follow feed_byproducts, which resets FENI/FPRI); `--check` on a copy reproduces yields.csv, producer_prices.csv, armington_params.csv and every other file the steps write (values within 1e-9). (3) `manure_n2o_tech.csv` rebuilt with build_manure_n2o: the old file lacked 29 AirPurCovHigh rows for pigs in 15 EU regions (BE10, CZ01, DE30, DE50, DE60, DK01-05, ES63, ES64, FI20, LT01, LT02) that ammonia_tech_model.csv offers; every other row equal; the Norway guard in build_norway_pigs is now empty. (4) `compare_qp_solvers.py` wrote to the repository root (fixed: capri_data/validation/). Not covered by any builder (see K72): 146 of armington_params.csv's 248 cells and the livestock rows of producer_prices.csv

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
  **CAPRI's own 2030 reference checked, 31 October 2026** (res_2_1730greendeal_refpol_endotech_all_ini, dataOut SHARE
  of the fertiliser options; code reading). CAPRI's reference run is a ghgTechCali = ini run
  (pol_input/greendeal/refpol_endotech_all_ini.gms l. 29), and that setting fixes the ammonia, breeding, histosol,
  winter-cover and tillage options at their initial shares (supply/set_miti_bounds.gms l. 60-74, 101-115, 158-201,
  213-229, 236-253) but not the fertiliser options, which keep only their upper bound MaxShare (l. 41-42): in CAPRI's
  reference the fertiliser options are endogenous, as in the model's baseline. Their shares there:
  - precision farming at most 0.3% (PT200000; IT12, IT13 0.2%; every other region 0): CAPRI's base stays where the
    model's stays with fert_slope_with_saving off, and far from the model's with it on (r128: FR10 0.44, EU 9.6%);
  - fertiliser timing up to 85% (NL410000 0.855; RO020000 0.61, RO060000 0.58, ES130000 0.30, RO010000 0.23, RO070000
    0.20, ES120000 0.14; Montenegro and Albania too) and nitrification inhibitors up to 34% in the EU (PT300000 0.335,
    NL410000 0.109, IT330000 0.072, PT110000 0.062; Montenegro 0.52): CAPRI's reference leaves the initial share in a
    handful of regions, which the model's baseline does not (0 everywhere, the gate runs' adoption tables).
  So neither setting reproduces CAPRI's reference: with the saving term the base moves where CAPRI's does not (precision
  farming), without it the base stays where CAPRI's moves (timing and inhibitors in about ten EU regions). Next step:
  per option and region, CAPRI's reference share against the model's baseline with each setting, and CAPRI's own
  first-order condition at its reference (which of its terms makes timing move in NL41 and not precision farming in
  FR10).
  **Why the two differ (code reading, 31 October 2026).** CAPRI calibrates an option's linear term beta so that its
  first-order condition is zero at the initial share with the fertiliser saving valued by a notional formula, the
  member state's NITF price times nmE on N0 / (1 + nmE m) (envind/ghgMiti.gms l. 1016-1035 and the beta derivation
  above it); in its simulation the saving runs through its fertilisation block, so where the block's marginal value of N
  differs from that notional value the option can move off its initial share, the likely reason for CAPRI's reference
  moves (fertiliser timing in NL41, Romania; inhibitors in PT30; not verified on CAPRI's numbers). The model calibrates on the solved NLP's own reduced cost instead (CapriRegionalNLP
  calibration: an option's residual at its base share goes into its linear cost, dabat("fert", option); an option at
  zero with a positive reduced cost is left alone), which makes every base share exactly stationary: the baseline
  cannot move where CAPRI's does. Two ways to CAPRI's reference, for the project lead's decision: (a) CAPRI's beta
  with its notional saving (the baseline then moves as CAPRI's, by the model's own block, not CAPRI's); (b) CAPRI's
  2030 reference shares (dataOut SHARE of the ini run) as the model's base shares, calibrated stationary there as now,
  the same treatment as the other base data the 2030 baseline takes from that run. (b) reproduces CAPRI's reference
  state by construction; (a) reproduces CAPRI's mechanism with the model's fertilisation block.
  **Decision of the project lead, 31 October 2026:** the model's calibration is kept and registered as a deliberate
  departure up to CAPRI (CAPRI_DEPARTURES_REGISTER DEP-30). It meets the condition CAPRI's derivation states
  (envind/ghgMiti.gms l. 731: each initial share optimal) exactly, with the model's own value of N, where CAPRI's
  notional saving misses it in some regions; neither (a) CAPRI's notional formula, which carries that miss into the
  model's own regions, nor (b) CAPRI's reference shares as the base, which would tie the baseline to CAPRI's reference
  run. The saving term in the curvature stays off (DEP-2). The structural differences that move the regional value of N
  (activities and technologies, the fertilisation block's scaling, manure P and K trade, the open departures) are to be
  assessed and reduced for their own sake (plan to follow)


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
- **Measured 11 November 2026 on CAPRI star 3.0's own Green Deal 2030 run** (the project lead's, against its reference; full-EU greendeal2030, damped manure pool prices; not the Farm-to-Fork of JRC121368): histosols idled 1,647 thousand ha against CAPRI's 1,819 (IHISCR 481, IHISGR 1,339): no excess against star 3.0.
- **Effect:** Farm-to-Fork land use, histosol N2O and CO2, set-aside premiums
- **In 9t:** –
- **Status:** **open, waiting for CAPRI's scenario results** (the project lead's decision, 29 October 2026: kept open with its reference). Needed: CAPRI's Farm-to-Fork or Green Deal 2030 regional results with the landscape floor: per NUTS2 unit the histosol fallowing (the FALLOW technology's v_Miti levels) and the set-aside land; to be exported with tools/gams/export_capmod_results.gms (run on a CAPRI installation where the scenario was solved); the project lead's installation has none of them so far. Before: **open** (needs CAPRI's Green Deal or Farm-to-Fork result with the floor)

<a id="k79"></a>
### K79: Member-state production that keeps moving between iterations (26 October 2026)

CAPRI's stop rule, recorded every iteration since r135, flags rows that move by more than 0.05% between iterations in converged runs: Irish potatoes 1.2-2.7%, Dutch maize 1.5-2% (before the K75 fix), Latvian oats 1.3%, and French olives and table grapes jumping by 35-110% at some iterations. The model's own tests pass (they are on EU prices, quantities and price gaps), so these swings are invisible to them

- **Effect:** member-state production of a few crops; whether CAPRI-mod's runs would pass CAPRI's stop rule
- **In 9t:** –
- **Status:** **open**. Diagnosis of r161 (27 October 2026): (1) the rows still moving at the last iteration (Latvian 28 October 2026 (batch 1, r177): with the jump check (supply.nlp_jump_check 0.1) and S13 (the Swedish tomato cells held), Green Deal 2030 stops by CAPRI's rule after 18 iterations (r171: 30; the supply-audit run r174 without the jump check: not in 60). The recurring moves of r171 (Bulgarian maize and rapeseed, Hungarian pulses, 30% every few iterations; Swedish tomatoes up to 76%) do not appear; one single move left (Bulgarian oats, 85% at iteration 13). Which of the two removed which moves is not separated (the run did not record the jump check's action; recorded from batch 2: metadata nlp_jump_check, outer_history[...]["jump_check"]).
- **Multistart check (31 October 2026; F2F run r200 with CAPRI_NLP_DUMP, tools/check/k79_multistart.py):** each region's last regional problem solved from its own start and from the levels gates 9, 10 and 11 ended at. FR820000: every start reaches the same optimum (objectives equal to 5e-5): on one problem there is one optimum, so its wine switching between runs comes from the runs' different problems (prices, iterations), not from two optima. BG020000: the same optimum from three starts; from gate 9's levels IPOPT stops at its iteration limit (a failed start, not another optimum). LT000000: two local optima: from gate 10's levels the objective is lower by 11,353 (0.07%), with other fodder 56.6 -> 166.7, maize fodder 72.2 -> 57.0 and cereals lower (oats 140 -> 99, barley 145 -> 114); r200 and gate 11 ended at the higher one. So in at least one region the run's regional solution is not the best local optimum of its own problem. CAPRI's CONOPT is a local solver as well; whether CAPRI has the same two optima is not known. Possible remedies, each a departure: a second start from the previous iteration's or the base point's levels when a solve moves far, keeping the lower objective (beyond CAPRI); or none, recorded as a property of the non-convex regional problem.
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
  **Gate 11 (31 October 2026, r198 against r196):** FR820000 back in the gate-8/9 state (wine 15.0 kha, olives 0.9),
  LT000000's other fodder 56.6 kha (gate 10 166.9, base 232.8): the regions with two states switch with the PMP terms'
  change (K108). The diagnostic of the two states' objectives (tools/check/k79_multistart, draft) is the next step
  (STRUCTURAL_GAPS_PLAN S12)
  **Gate 12 (31 October 2026, r201 against r198; Farm-to-Fork only):** converged under CAPRI's rule in 23 iterations
  (r198: 12); the EU indicators within 1 point of r198 (beef price +0.9, beef animals -0.8, the rest within 0.5; mean
  deviation from JRC121368 over 20 indicators 4.15, r198 4.19). The extra iterations are a two-step cycle of FR820000's
  jump check: at every even iteration from 2 to 20 the region's solve ended at objective -4.63e6 (moves 0.14-0.17 against
  the last iteration's levels), the standard start found -6.21e6 and was kept; at the odd iterations the check did not
  act. CAPRI's row OLIV FR000000 moved by about 102% at every iteration from 3 to 21; the cycle ended at iteration 21,
  where CAPRI's late price-averaging weights start (capri_step_weights_late_from = 20). Which region carries the olive
  swing is not known (per-iteration crop levels are not recorded): FR820000's olives are 0.89 kha at the end in both
  gates, FR810000's 5.5 (r198 14.9). End states differ from r198 in FR820000 (suckler cows 2.7 thousand head, r198 19.9;
  cereals) and LT000000 (other fodder 161.5 kha, r198 56.6; the check moved it to the standard start's lower objective
  at iteration 1). Why the solve from the better point returns to the worse one every other iteration is not known; a
  traced run of FR820000 and FR810000 (CAPRI_NLP_TRACE) would show it
  31 October 2026, the project lead's decision: the next gate's Farm-to-Fork run is traced (diagnostics only, the
  results unchanged): CAPRI_NLP_DUMP=DIR CAPRI_NLP_TRACE=FR820000,FR810000 (every solve of the two regions: the
  previous point, the starts tried, the point kept) and diagnostics.record_regional_levels = true (every region's levels
  per iteration, tools/check/k79_trace.py, to find the region behind CAPRI's olive row); the K79 remedy is decided on
  what it shows
  **Gate 13 (1 November 2026, r202 Farm-to-Fork traced, against r201):** converged under CAPRI's rule in 28 iterations
  (r201: 23); EU indicators equal to r201 to 0.1 point (mean deviation from JRC121368 over 20 indicators 4.15 in both).
  The trace (CAPRI_NLP_TRACE=FR820000,FR810000; 66 solves per region) answers gate 12's question. In the scenario
  FR820000 alternates between two points of its regional problem (levels as a ratio to base):
  A: olives 0.10, wine 0.29, table grapes 0.13, paddy rice 0.82; objective about -4.63e6 (IPOPT: Solved_To_Acceptable
  from a warm start);
  B: olives 2.79, wine 0.915, table grapes 0.94, paddy rice 0.79; objective about -6.21e6 (Solve_Succeeded from the
  standard start), i.e. the better point of the same problem by about 1.58e6.
  At every odd scenario solve the warm start from A stays at A, the jump check's standard start finds B and B is kept. At
  every even solve the warm start from B stays at B (-6.206e6, Solve_Succeeded), and then the ammonia-fixed re-solve
  (capri_mod/supply/nlp.py, the "amm-fixed" block: the ammonia options fixed at base shares when the N-balance row is
  slack, started from the solution clipped to its bounds, kept whenever IPOPT reports success, with no comparison of
  objectives) walks from B back to A. The cycle ends at solve 63 (iteration 26), where the ammonia-fixed re-solve after
  the standard start also lands on A; from there the warm start stays at A and the jump check does not act, so the run
  stops with FR820000 at A, the worse point (olives 0.9 kha, wine 15.4 kha; base 8.9 and 52.4). Gates 8, 9, 11, 12
  ended near the same state (wine 15.0-16.5 kha, olives 0.9); gate 10's (wine 50.7, olives 16.7) was near B. FR810000 has no such switch: it moves by small
  alternating steps (paddy rice 1.4553 / 1.4554, wine 0.9984 / 0.9990) following FR820000.
  Not yet measured: the ammonia-fixed problem's own objective at B (with the options at base shares), i.e. whether B is
  feasible and better in the fixed problem too, or whether fixing the options really moves the optimum to A.
  Green Deal (r203 against gate 10's r197; gates 11 and 12 had no Green Deal run): converged under CAPRI's rule in 21
  iterations (r197: 17), no non-optimal solve kept; EU indicators within 1.6 points (ammonia -29.4% against -31.0%,
  milk price +7.5 against +8.9, manure N2O -10.8 against -12.1, beef price +11.2 against +12.4, the rest within 1
  point). Farm-to-Fork moved the same way over the same gates (r202 against r196: milk price -2.3 points, pork -1.3,
  poultry -1.1), in line with gate 11's K108 fix (smaller price rises), not checked further. The N-surplus row was
  slack at the end in two regions (BG020000, RO020000; r197: three)
  1 November 2026, the project lead's decision: option (c), CAPRI's way. The re-solve with the ammonia options at
  their base shares where the N-surplus row is slack is removed (no switch kept: gate 13's r202 is the reference run
  with it): CAPRI solves the regional model once, from the calibrated point. The options stay held at their base shares where
  there is no policy incentive on N at all (K63). To check at the next gate: FR820000's end state, and the ammonia
  options' adoption in the regions where the N-surplus row is slack (K63's saddle along the options' joint direction
  could let IPOPT move them off their base shares there). In r202's final state 213 regions had an N-surplus row
  (none a mineral cap) and it was slack (|dual| <= 1e-9) in four: FR100000, FR240000, FR810000, FR820000, the only
  regions where the re-solve could act at the end of that run; in the Green Deal's r203, two (BG020000, RO020000)
  **Gate 14 (2 November 2026; stage 3's first batch with the K79 branch: the ammonia-fixed re-solve removed, the
  Western Balkans' food demand in WBA):** Farm-to-Fork r204 (regional levels recorded, against gate 13's r202):
  converged under CAPRI's rule in 12 iterations (r202: 28), no non-optimal solve kept; EU indicators within 0.4 points
  of r202 (largest: fertiliser N2O -39.7% against -40.0, N surplus -32.2 against -32.5, beef price +23.7 against
  +24.0; mean deviation from JRC121368 over 20 indicators 4.18 against 4.15), adoption rates within 0.4 points (catch
  crops 40.9% against 41.3). Regional activities moved by more than 10% of base (and more than 1 kha or thousand head)
  in FR810000 and FR820000 only. FR820000 ends near gate 13's point B, the better local optimum: olives 24.7 kha, wine
  47.9, table grapes 1.2, paddy rice 7.4 (base 8.9, 52.4, 1.3, 9.3; r202 0.9, 16.0, 0.2, 9.0), its suckler cows and
  calves near base (20.0 and 104.3 thousand; r202 2.7 and 85.4). FR810000 moves with it: olives 30.2 kha (base 5.3,
  r202 5.5), wine 129.2 (145.9, 145.8), suckler cows 94.9 thousand (87.9, 56.2). Not checked against CAPRI's own
  regional results (none at hand): olives at 2.8 and 5.7 times base in eight years are large for a permanent crop.
  The N-surplus row is slack at the end in five regions (FR100000, FR240000, FR810000, FR820000 as in r202, and
  RO020000, where it bound in r202). The ammonia options move off their base shares in four of them (not FR100000): up
  in FR240000, FR820000 and RO020000 (broilers' and layers' covered storage and low-emission spreading, shares from
  about 0 to 0.1-0.55), down in FR810000 (pigs' and broilers' low-emission spreading to 0). Whether these moves are the
  options' value through the mineral N they save or K63's saddle along the options' joint direction is not determined
  (it needs the regional objective along that direction); the EU adoption rates of the ammonia options move by 0.1
  point at most.
  Green Deal r205 (against r203): baselines equal (largest regional difference 0); converged under CAPRI's rule in 18
  iterations (r203: 21), no non-optimal solve kept; EU indicators within 0.1 point of r203; N-surplus row slack at the
  end in BG020000 and RO020000 as in r203, their ammonia options as in r203 (no share moved by more than 0.05);
  FR820000 as in r203 (olives 8.6 kha, wine 52.1). One region ends at a different point: HU230000 (one of the regions
  with relaxed mineral caps, ROOF and duals, in both runs), rapeseed 24.6 kha against 97.6 (base 64.2), sunflower 115.1
  against 52.8 (78.6), barley 82.2 against 51.9 (35.4), soft wheat 108.6 against 145.5 (164.8); Hungary's rapeseed 250
  kha against 317 (base 344), the EU's within 0.1%. Which of the two points is the better one in HU230000's problem is
  not known (no trace); RO050000 and BG010000 move by less (other fodder, oats, soya and other cereals, 1.6-8.4 kha)


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

- **Measured 11 November 2026 on CAPRI star 3.0's own Green Deal 2030 run** (the project lead's, against its reference; full-EU greendeal2030, damped manure pool prices; not the Farm-to-Fork of JRC121368): pork +7.9% against +12.9, poultry +8.8 against +13.5, cereals (soft wheat) +5.5 against +8.9, oilseeds (rape) +6.2 against +8.2; fattening pigs -6.1% against -9.2, broilers -5.9 against -8.1, dairy cows -1.2 against -1.6.
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
  **The remaining options scoped, 31 October 2026** (code reading; CAPRI's 2030 reference res_2_1730greendeal_refpol_endotech_all_ini
  and its maximum-mitigation run scen_greendeal_2030.txt). Correction first: the statement above that LegSh, UreaSubst,
  the tillage options, buffer strips and the biodiversity options "carry no level" in CAPRI's Green Deal 2030 result,
  and so "none of them moves CAPRI's Green Deal or Farm-to-Fork result", was read from scen_greendeal_2030.txt, which
  is CAPRI's maximum-mitigation run (refpol_endotech_all_max, K38), not a Green Deal or Farm-to-Fork scenario; it is not
  evidence about those scenarios, and it is not even right for that run: conservation tillage carries SHARE 1 there in
  most regions (3,258 regional entries, median 1; ConsTill's initial shares in the 2030 reference are e.g. Denmark 0.107,
  NoTill 0.013). What the code says instead:
  - buffer strips, the biodiversity options and biochar are not in CAPRI's Green Deal technology lists
    (pol_input/greendeal/refpol_endotech_all_ini.gms l. 216: ghgTechActiveCarb LegSh, WinterCov, ConsTill, NoTill;
    biochar and rotGraz commented out; the landscape options off): nothing to port for the Farm-to-Fork and Green Deal
    runs;
  - conservation tillage (ConsTill): no yield effect (p_tillYldFrac 1 in every zone, envind/tillage.gms l. 454-456), a
    cost saving (costParLin 46 - 60 - 7 = -21 EUR/ha, l. 403) calibrated away at the initial share, its soil carbon
    (CO2SEQ) outside the GGWP tax base and its runoff effect commented out (l. 561-566): without a soil-carbon price it
    stays at its initial share, which the 2030 reference's yields and costs already contain;
  - no-till (NoTill): yield 0.9 of the regional mix in CAPRI's North and Center zones, 1 in the South (l. 450-453;
    applied directly or through the T1/T2 split, %NoYieldEffect%, l. 486-535, the Green Deal file's setting not
    checked), leaching of mineral and manure N up 24% and 38% (l. 562-563, active), N2O of mineral N up 12% (8% South,
    l. 580-583); so its share would respond to crop prices and to the GGWP tax (both against it) from small initial
    shares (Denmark 0.013); the effect on production and emissions is that small share's change times those factors,
    not measured;
  - legume share in temporary grassland (LegSh): MaxShare 1, its scenario response not measured (in the
    maximum-mitigation run 1.9e-5 of the EU's area);
  - urea substitution: the incentive analysis above does not depend on CAPRI's result files and stands; the sentence
    "CAPRI's own Green Deal result shows no adoption either" in the 31 October discussion came from the same
    maximum-mitigation run and is withdrawn.
  Status of the remaining options: buffer strips, biodiversity options and biochar need nothing for CAPRI's Green Deal
  and Farm-to-Fork runs; conservation tillage none without a soil-carbon price; no-till and LegSh are the two whose
  scenario response could be non-zero, small by the code's terms, unmeasured.

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
| 2017/supply/capri_supply_elas_market_1717.csv, supply_elas_eu_all.json | CAPRI's elas1717defaulta.gdx p_elasSupp (gdxdump p_elasSupp.txt) | built: build_capri_supply_elas_market.py, both byte-identical as committed; then, at the project lead's decision (29 October 2026), the JSON replaced by 2017/market/supply_elas_eu.csv: the median over the model's 27 member states (was CAPRI's EU28, the UK included), every market commodity under the model's code (OLIV, PARI, SUGR, WINE now found; INPE dropped), full precision. Changes the EU rows' own-price anticipation: run pending (batch-6 gate) |
| sources/intermediate/capreg/capreg_national_prices.csv | CAPRI's res_17 national MPRI | built: build_capreg_national_prices.py, same values; adds MAIZ, OAR1 and the model's CORN (the 17 regions without a regional maize price grow none), drops COTT and OFIB (copies of TEXT under old codes, read by nothing) |
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
  unread second LitRevFertTech dump (sources/raw/capri/dat/scen/ghgtech, see K103) was removed with them.

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
capreg_manure_nutrients.csv and sources/raw/capri/capmod/capmod_world_prices_2017.csv (the world-price checks read
capmod_world_reference_2017.csv). sources/raw/capri/dat/scen/ghgtech/LitRevFertTech_p_litRevFertTechs.csv is a second, fuller
dump of the table that sources/raw/capri/dat/scen/ghgtech/LitRevFertTech_p_litRevFertTechs.csv holds (the one build_fert_side_effects
reads); no code names the first.

- **Effect:** none on results
- **In 9t:** –
- **Status:** **fixed** 29 October 2026 (the project lead's decision): the seven unread validation files and the
  three unread extracts removed (extract_all_from_data2, extract_remaining_nine and ingest_capmod_market no longer
  write them); the two reference files given a builder, tools/build/build_capri_eu27_levels.py (2030: dataOut EU27yr19
  LEVL of markmarket_greendeal_1730et_base_1717, reproduced exactly; 2017: the 26 CAPREG dumps summed, equal to the
  old file's four decimals, now at full precision). sources/raw/capri/dat/scen/ghgtech/LitRevFertTech_p_litRevFertTechs.csv
  (unread second dump) removed 30 October 2026 (K102); further builder outputs that no code reads remain to be settled (see the census in
  capri_data/schema/schema.json, read_by).
  **Removed 30 October 2026, the project lead's decision, read by no code** (an audit of the files read neither by the
  runs r190/r191 nor by a builder; each grepped again across code, tests, docs, schema and the pipeline trace), their
  writers stopped: sources/intermediate/baseline_pmp/pmp_cnst_2030.csv and pmp_cnst_landtypes_2030.csv (build_pmp_2030),
  sources/intermediate/baseline_pmp/simini_21730_data.csv (no writer; its reader build_pmp_recipe.calibration_point_2030, never
  called, removed too), sources/raw/capri/capmod/capmod_trade_flows_2017.csv.xz (ingest_capmod_market, which now writes only its
  uncommitted summary JSON), sources/capreg/capreg_cost_components.csv.xz (extract_all_from_data2),
  capreg_feed_use.csv, capreg_herds.csv, capreg_land.csv (extract_remaining_nine), sources/intermediate/estnlp/gtap_armington.csv
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
  **removed** with the path, its two inputs' loading and sources/intermediate/estnlp/pela_cross_by_region.json (no longer written);
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
- **Status:** **fixed, gate 11 pending** (31 October 2026, branch money-year): tools/lib/_money.deflator(year) (the
  deflator of capri_price_ratios_<year>.csv, one value, 1.019^13 to 4e-16) divides every item of the audit's list in its
  builder (genetics: also CAPRI's floors of 20 and 2 EUR, in its simulation year's money; anaerobic digestion: CAPRI's
  inflation taken back out; the per-CAPRI-region land rents stay in CAPRI's money, the recipe's input); data rebuilt in
  the pipeline's order, every changed term exactly 1/1.277216 of before; tests 253 passed. Mini-EU Farm-to-Fork (20
  units) against the gate-10 reference: oilseed production -22.4% (-20.6), cereals -16.9 (-16.0), veg+perm -16.1
  (-15.5), ammonia -38.7 (-39.6), manure N2O -21.8 (-23.0), prices within 0.2 points (a subset run: its EU prices move
  little). Not changed: genet_eff's feed cost from the 2017 ration prices where CAPRI takes the simulation year's
  (a price-year question); the market's welfare base (to settle). The full Farm-to-Fork and Green Deal runs wait for the
  project lead's go (gate 11)
  **Gate 11, 31 October 2026** (r198 Farm-to-Fork, r199 Green Deal 2030 against gate 10's r196, r197): baselines equal
  (largest regional difference 0.006); supply responds more to prices, so the scenarios' price rises are smaller and the
  herds fall less: Farm-to-Fork milk +20.0% (+22.4), pork +19.5 (+20.9), poultry +16.3 (+17.4), cereals +10.7 (+11.2),
  pigs -12.8% (-13.5), ammonia -36.7 (-37.7), manure N2O -17.2 (-18.1), production totals within 0.1 points; Green
  Deal milk +8.0 (+8.9), cereals +5.7 (+6.4), ammonia -29.7 (-31.0), the rest within 0.3 points. Both converged (12 and
  20 iterations); the scenario iterations take about 1.5 times as long (a first Green Deal run stopped at its
  iteration 6, restarted with the Hessian from the cache)

### K109: The market base of the EU's two market regions: processed products split differently, dairy below CAPRI's (found 3 November 2026, market stage 3; recorded 4 November 2026)

tools/check/check_market_base.py (the market alone at CAPRI's 2030 calibrated state, the EU's and the supply-model
regions' supply held at base): every price and every one of the 20,705 bilateral flows is CAPRI's (largest relative
gap 5e-12), and so is the production of every non-EU region (largest 6e-6, Canada's DDGS). Production differs in
the EU's two market regions only (A_EU_WEST, A_EU_EAST):

- crushing (oils and cakes of rape, sunflower, soya): the EU total is CAPRI's, the split between the two regions is
  not (EU_EAST rape cake -122.8 kt, EU_WEST +122.8; sunflower oil -22.9 / +22.9): the crush of the member states is
  allocated to the two regions differently from CAPRI's market data;
- dairy: cheese -407 kt in EU_WEST (-4.6%) and -19 kt in EU_EAST (-3.9% for the EU), butter -0.4% and -0.5%, casein
  -31% in EU_EAST (6.1 against 8.9 kt; 2.8 kt) and -1.3% in EU_WEST: the dairy block's base output per member state,
  summed, is not CAPRI's market data of the two regions.

Not yet traced to the member-state data. Next: compare the member states' crush and dairy output of the base with
CAPRI's DATA per member state (sim_ini_21730), region by region.

- **12 November 2026:** the check now passes the EU's supply per member state, as a run does
  (MarketModule.capri_base_supply_rows); until then its two block rows gave the dairy block no member state's milk and
  Norway the base table's FAO milk. Prices (largest relative gap 9.4e-8) and flows (5.3e-7) are now CAPRI's in every
  region, Norway's dairy included (before: up to 17% and 2x). The production gaps above are unchanged (cheese -407 kt
  in EU_WEST, rape cake +-122.8 kt, casein -31% in EU_EAST): they do not come from the check's rows.

### K110: The market's Newton-Krylov solve did not converge on a real shock; its test had passed without one (found 4 November 2026, the ports block's full test suite)

test_market_nk.py (a 10% cut of EU beef and 5% of EU soft wheat, the Newton-Krylov solve against the default one)
stopped at its time limit in the full suite of the ports block. What was found:

- From 3 November 2026 (market stage 3, dae33d3) to 1cfcc2c the test had no shock: the EU supply rows named after an
  EU block were dropped, so the cut never reached the market (residual at the first step 3e-5) and the test passed in
  two steps. 1cfcc2c restored the rows; from there the Newton-Krylov solve crawled (residual 6.8e-2 to 1.4e-3 in 13
  steps and 231 evaluations, the Krylov solve never within its tolerance, the Newton step rejected by the line search
  and replaced by half the default step), with or without the land market (stage 7) and before the quotas (stages
  4-5): the same path at 1cfcc2c and at 78f3ed4.
- Cause: the market evaluation reads state the previous evaluation left (MarketEvalState: the dairy blocks' raw milk
  price that FeedBal_, the land markets and Norway's milk row use, and the other per-evaluation carriers). The default
  solve takes it lagged by one step, which settles with the prices; the Newton-Krylov solve's finite differences
  (steps of 1e-6) saw each evaluation start from a different state, so they were not derivatives of one function.
- Fix (capri_mod/market/market_nk.py): every evaluation of one Newton step starts from the same copy of that state;
  the state moves to the accepted point's between steps, as the quotas' rates do; where the prices already clear the
  markets and only the quotas' rates move, the next step is theirs (one evaluation), not a Newton step. The equations
  and the stopping rule are unchanged. On the test's shock: the Newton steps bring the residual below 1e-7 in 5 steps
  (51 evaluations); the whole solve stops after 17 steps and 234 evaluations (397 s) because the quotas' rates settle
  slowly, in the default solve as well (40 iterations, 100 evaluations, 295 s): the quota fixed point (bilateral.py
  trq_solve, updated between steps), not either solve, sets the length near the tolerance.

- The two solves then stop at the same prices to 6e-7 relative or better, except Switzerland's casein (9,344.64
  against 9,344.56 EUR/t, 8.4e-6): a market of about 1.8 kt (0.28 kt own sales, 1.08 kt imports, 0.20 kt exports),
  where the stopping rule (residual below 1e-7 of S0 + D0) leaves room for that gap. The test's bound became 1e-5 for
  every price and 1e-6 for all but five (it was 1e-6 for all, more than the stopping rule guarantees).

Status: fixed. Open, as a possible improvement: solving the quotas' sigmas inside each evaluation (CAPRI solves
trqSigmoidFunc_ with the rest of the market) would make the end of both solves shorter; not done. Decided on 4 November 2026
(docs/design/MARKET_IPOPT_DESIGN.md section 7.1): the Newton-Krylov solve stays optional with no further work; the
quotas and the raw milk price go inside the evaluation after the Farm-to-Fork and Green Deal runs, then G3.

5 November 2026: the default solve now takes the quotas' sigmas with the prices (market.trq_joint, K117); the Newton-
Krylov solve keeps them one step behind. Switzerland's casein then differs by 1.37e-5 between the two stops (the test's
bound 1e-5 failed in the suite; the next largest gap 1.1e-6, Swiss butter). Rerun at market.tol = 1e-9: the default
solve converged in 116 s; the Newton-Krylov solve reached its 300-step cap without converging (1,787 s); the casein gap
fell to 4.8e-6 and every other price was within 4e-7. So a stop-point gap in this thin market, not two equilibria; the
test's bound became 3e-5 for every price, 1e-6 for all but five as before. The Newton-Krylov solve is left as it is
(optional, no further work, as decided on 4 November).

### K111: The set-aside report books part of a set-aside increase as VSET where CAPRI has none (found 4 November 2026)

capri_mod/model.py _set_aside_table splits the model's SETA into CAPRI's VSET and FALL: VSET = s X0 + w (X - X0), s
CAPRI's VSET share at the calibration year, w the share of a common change CAPRI's PMP terms give VSET
(tools/build/build_labour_setaside.py). Where the unit has no PMP terms of its own for the two, w is its country's median,
else the EU median (0.655 in 2017). 60 of the 226 EU and UK units have no VSET in CAPRI in either year (the Bulgarian,
Cypriot and Czech units among them; share 0 in 2017 and 2030), yet w 0.645-0.662: a scenario that raises set-aside books
about two thirds of the increase as VSET, an activity these units do not have in CAPRI (an activity without a base level
stays at zero there). Reporting only (the set-aside's premiums and labour; the supply models solve SETA as one activity).
The units of Norway, Turkey and the Western Balkans, given a set-aside split on 4 November 2026 (they have FALL only),
follow the same rule.

CAPRI (checked 4 November 2026): supply/prep_cal.gms l. 103 sets p_technFact(region, activity, "LEVL") to 0 where the
activity's level is 0 at the calibration point, which takes it out of the region's model (aggreg.gms l. 25 sets its
level to 0); set_supply_bounds.gms l. 42-43 bound VSET only where its base level exceeds 1e-6. So VSET stays 0 there and
a set-aside change is FALL's. What counts is the level at the run's calibration point (the 2030 baseline in a 2030 run),
not "in either year" as first proposed.

Status: fixed (the project lead, 4 November 2026): _set_aside_table takes w = 0 where the VSET share at the run's
calibration year is 0. Reporting only (the set-aside split, its premiums and labour); supply results unchanged.

### K112: Histosols: regions without a JRC record took their country's share; Greek grassland had no N2O (found 4 November 2026)

tools/build/build_histosol.py compared with CAPRI's regional results (Green Deal 2030 ini run, N2OHIS of ARAB and GRAS,
kg N2O per ha; res_2_1730greendeal_refpol_endotech_all_inidefaulta): 145 of the 215 regions matched to 2e-6, 70 did not.
- 65 regions without a record in the JRC organic-soil table (p_OrgSoilOri) took their member state's shares (41 of them
  non-zero: DE72, DEB1-2, 16 Italian, BL22/24/31, FR61/62/82/83, PT20/30, RO05/07/08, AT21/22). CAPRI treats a missing
  record as zero for every NUTS 0 but the Western Balkans and Turkey (p_OrgSoilNoGap, envind/prep_lulucf_carbon.gms
  l. 250-266); its results are zero for all 65.
- Greece's 13 regions have a JRC cropland share and no grassland one. CAPRI's gases.gms (l. 676-686) gives every crop
  activity, GRAE and GRAI included (MCACT holds GRSACT), the cropland N2OHIS, overwritten by the grassland one only where
  that is non-zero: Greek grassland emits the cropland N2O per ha. The model had 0. CO2HIS and CH4HIS are per class in
  CAPRI (calc_lulucf_carbon.gms), and the grassland fallowing's MaxShare is the grassland share: both unchanged.

A reproduction error of capri-mod, not a registered departure. The fallowing terms are unchanged (the 65 regions have no
FALLOW calibration in CAPRI's cost savings).

- **Effect:** histosol N2O, CO2 and CH4 (emission reports; the GHG price terms where a tax is on)
- **Status:** **fixed** 4 November 2026: the region's JRC record only, a missing one zero; grassland without a share
  takes the cropland N2O per ha. After the fix every region matches CAPRI to 2e-6 (the three Greek regions without
  grassland in CAPRI's 2030 have no GRAS row there). Test: test_histosol_n2o_per_ha_as_capris_regional_results.
  Mini-EU Farm-to-Fork run (91f621c against 202acf5): supply and market identical; only EL140000's histosol N2O
  changes (baseline 16.7 -> 31.0, scenario 0.4 -> 14.7 kt CO2-eq), the one mini region concerned.

### K113: Croatia had no AD option: CAPRI's fallback_Balkan fills its VSER and housing share (found 4 November 2026)

tools/build/build_ad_option.py skipped a region without CAPRI's AD_basedata p_VSER. Croatia has none (nor p_HousShar,
p_MitiShar0), so it had no AD option. CAPRI fills p_VSER, p_HousShar and p_SharLiq of every region of fallback_Balkan's
first list, Croatia included, with the unweighted average over Romania, Bulgaria, Croatia and their NUTS 2 units having
a value (ad_data_and_cali.gms l. 353-365; sets.gms l. 8111-8119), and its Green Deal 2030 results report AD_AnCh for
HR000000 (about 5e-7, no initial share). Found while porting the same fallback for the Western Balkans and Turkey
(SUPPLY_NONEU step 6). A reproduction error of capri-mod.

- **Effect:** Croatia's AD option (manure CH4, its cost) in the scenarios; the baseline keeps the share at zero
- **Status:** **fixed** 4 November 2026: the fallback ported (fallback_balkan in build_ad_option.py; gams_text.set_pairs
  reads CAPRI's (a, b).(c, d) notation). Croatia and the six Western Balkan countries now have the option; Turkey's
  units not yet (their manure-system shares in n_cascade_factors give no housed liquid manure: to check against CAPRI).
  Test: test_ad_option_of_croatia_and_the_balkans_as_capri. Mini-EU Farm-to-Fork run (d80d7fd against 4cd6518):
  Croatia's results unchanged (the option stays at zero without an incentive on manure CH4).

### K114: Norway lacked CAPRI's mirrored MITERRA data and Sweden's AD data: no housed liquid manure, no AD (found 4 November 2026)

CAPRI loads Norway's MITERRA data from dat/miterra/mirror_non_changeable_parameters_norway.gdx and
mirror_miterra_inputs_norway.gdx and copies them to NO000000 (envind/ammo.gms l. 252-343: RCEmissions, ControlStrategies,
ReducControlStrategies, FracEmGrazing, ReducEmhouse, ReducEmStorage, FracEmHouse, FracEmStorage, FracEmAppl, EmFracFert,
FracUseFert, NN_CorrFertFactDeviation, bNumAniRAINS among them), and gives Norway Sweden's AD data (p_SharLiq,
p_HousShar, p_MitiShar0, p_VSER; ad_data_and_cali.gms l. 257-261). The model's ammonia inputs (converted from the base
files' dumps) had no Norwegian records but a few base-file ones, so Norway's units had no housed liquid manure (tsl 0,
tsg 1 in n_cascade_factors: every housing, storage and application factor 0), no AD option, and housing and storage
reductions from the base files where CAPRI uses the mirror. Norway is in every default run. Found while porting the AD
option outside the EU (SUPPLY_NONEU step 6). A reproduction error of capri-mod.

- **Effect:** Norway's manure N cascade (NH3, N2O, NOx, N2, run-off), its ammonia technologies and AD option, its urea
  share; EU, UK, Western Balkan and Turkish rows unchanged (checked file by file)
- **Status:** **fixed** 4 November 2026: the mirror symbols extracted (tools/build/extract_capri_dat.py) and applied by
  build_ammonia_tech_inputs (norway_mirror; the pairs read from ammo.gms), Sweden's AD data by build_ad_option (mirror).
  Norway's AD initial shares are CAPRI's 2030 AD_AnCh to 0.3% (DCOL 0.000209, BULL 0.000077, PIGF 0.000333 in all six
  units). The regional mirrors (rLFrest, rLFmanureBasis, rLFmanureND, rCorrND) hold the former NUTS 3 codes, none of the
  units, so CAPRI's assignment gives the units nothing, as here. Test: test_norway_miterra_mirror_and_ad_option_as_capri.
  Mini-EU Farm-to-Fork run (d80d7fd, with the winter cover outside the EU, against 4cd6518): NO080000's soil N2O
  106.9 -> 97.2 kt CO2-eq, P run-off 68.6 -> 156.3 t, urea CO2 0 -> 0.03 kt; supply, market and every other region
  unchanged to the solves' tolerance; the mean deviation from CAPRI (20 indicators) 7.81 as before.

### K115: The 2030 set-aside followed CAPRI's VSET alone, not FALL + VSET (found 4 November 2026)

The model's SETA is CAPRI's fallow FALL plus its voluntary set-aside VSET (CAPRI_TO_MODEL_ACTIVITY maps FALL to SETA;
the set-aside split, K111). tools/build/build_trajectory_capri_ref.py gave it the growth of CAPRI's own SETA row, which
is VSET alone (CAPREG 2017: IT400000 SETA = VSET = 10.70, FALL 7.22), and the EU median where a region has no VSET.
Against CAPRI's 2030 reference (res_2_1730greendeal_refpol_endotech_all_ini, FALL + VSET as
capri_data/validation/greendeal_2030/capri_marginal_terms_ini_2030.csv has them) the mini run's 2030 baseline had
PL12 55.6 kha against 103.9, IT40 9.7 against 19.9, PT18 43.8 against 25.9, BG02 28.6 against 18.3, HR 41.0 against
25.0, RO04 67.2 against 51.3, ES61 430.3 against 373.3. The EU-level check (BASELINE_REPRODUCTION) did not show it: the regions offset each other. Found
while preparing SUPPLY_NONEU step 9's comparison per region. A reproduction error of capri-mod.

- **Effect:** the 2030 baseline's set-aside and fallow per region, and through land use the other crops a little; the
  Green Deal landscape floor and the set-aside split rest on it
- **Status:** **fixed** 4 November 2026: SETA's levels in the trajectory are FALL + VSET in both years (as SHGT and CACR
  are sums); VSET is read and not written. 434 regional SETA factors change (191 regions had none and took the EU
  median). Test: test_set_aside_trajectory_is_fallow_plus_voluntary_set_aside.
  Mini-EU Farm-to-Fork run (02dcf2b against 0c80e21): the 2030 baseline's SETA against CAPRI's reference (kha) PL12
  55.6 -> 104.5 (CAPRI 103.9), IT40 9.7 -> 20.0 (19.9), RO04 67.2 -> 51.2 (51.3), HR 41.0 -> 25.6 (25.0), ES61
  430.3 -> 375.5 (373.3), EL14 7.1 -> 10.9 (10.9), PT18 43.8 -> 26.1 (25.9), BG02 28.6 -> 18.3 (18.3), IR01 8.1
  (8.1), FR24 80.0 (80.3); FI19, DED, NO08 and DE11 within 1%. 132 baseline activity levels move by more than 1% (the
  land the set-aside frees or takes); the mean deviation from CAPRI's 20 indicators 7.81 as before.
  Correction (4 November 2026, late): the first version of this entry listed EL14, PT18, BG02, IR01 and FR24 as still
  apart (CAPRI 7.2, 20.7, 14.3, 4.4, 85.7). Those CAPRI values came from another CAPRI file,
  markmarket_greendeal_1730et_base_1717.txt, not from the reference's ini levels that the trajectory and the
  validation file use; against the latter the ten regions are within 0.8%, HR 2.4%.
  Not changed: the CAPTRD trajectory (scenarios/captrd_2030, not the default) takes CAPTRD's own SETA row as it is
  (capri_mod/projection/captrd_import.py, no aggregation); whether CAPTRD's SETA is VSET too is to check before that
  trajectory is used.

<a id="k116"></a>
### K116: The CAPRI-reference trajectory did not reproduce CAPRI's 2030 levels (found 4 November 2026)

tools/build/build_trajectory_capri_ref.py writes the 2030 baseline's growth from CAPRI's own reference
(res_2_1730greendeal_refpol_endotech_all_ini over CAPRI's 2017 results), but it kept three rules of the trend
projection captrd_2030: every factor held in [0.2, 5], regional factors only where the 2017 level is >= 1.0, and a 2030
level the reference does not list treated as missing (the national or EU factor, about 1) where GAMS lists no zero.
And the model's OFOD (CAPRI's OFAR + ROOF) took OFAR's growth alone. The model's 2017 levels being CAPRI's, the
projection then missed CAPRI's 2030 reference in 96 of the EU's 3,587 crop cells with a regional factor by more than 1%
(139 kha in all): France's pulses at 0.2 against CAPRI's 0.112 (FR24 9.7 kha against 0.8), IT20 rape 13.5 against 22.7,
UK grain maize 5.6 kha against none. Outside the EU 247 crop cells (UK 123, Norway 58, Turkey 25, the Western
Balkans 41). Found from SUPPLY_NONEU step 9's UK maize (about 1 kha per region against 0). A
reproduction error of capri-mod.

- **Effect:** the 2030 baseline's levels of those cells, and through land the other crops a little; livestock factors
  outside the band too (SK suckler cows 0.083 against 0.2)
- **Status:** **fixed** in the data, 4 November 2026 (branch fix-open): level factors are CAPRI's ratio as it is, for any
  2017 level > 0; a level the reference does not list is 0 where it lists the region and the activity elsewhere (20
  cells of 2017 level >= 1: DE, ES and IE other oilseeds, PT durum wheat, DK and NL pulses, UK grain maize, FR tobacco, NL
  fallow); OFOD = OFAR + ROOF (levels, and the level-weighted yield). The EU fallback medians stay over the cells of
  2017 level >= 1.0 (3 change, by the zeros). The schema allows a zero level factor. 7,870 regional factors added, 193
  changed. Test: test_capri_reference_trajectory_reproduces_its_crop_levels (every crop cell of the trajectory equals
  CAPRI's 2030 reference level: the EU's 6,047, the 30 non-EU units' too).
- **Effect measured** 5 November 2026. Full Farm-to-Fork run full_k116c against r213 (the same code without K116):
  converged in 12 iterations (r213: 13); the baseline against CAPRI's 2030 reference (compare_baseline_capri.py): median
  deviation of activities 0.2% (0.4%), production 0.2% (0.5%), domestic use 0.4% (0.6%), relative prices 12.1% as before;
  mean absolute deviation from JRC121368 over 20 indicators 4.56 (4.59), every indicator within 0.4 points of r213; the
  scenario's voluntary set-aside 5,379 kha (5,757). Mini-EU: 6 iterations, deviation 7.82 (7.81).
- Yields likewise: the band held 18 regional yield factors, all above 5 (Poland's other crops OCRO: CAPRI's yield 11.6
  in 2017, 206.5 in 2030, 14 to 21-fold per region; Bosnia's apples 5.7-fold), now CAPRI's ratio as it is.
- **Not changed:** the trajectory's own check on the solved baseline (the PMP and the land reconciliation can still
  move levels) comes with the run.

<a id="k117"></a>
### K117: The full-EU market did not converge in Farm-to-Fork, the EU's sugar quotas switching (found 5 November 2026)

The Farm-to-Fork gate run of 4 November (r212, commit 02dcf2b) converged its baseline, but every scenario market solve
ran its 100 steps without converging, the largest residual on sugar (SUGR, 1.2-1.9%), 411-535 s per solve against 15-38
s in gate 16; the run could not finish within its time limit and was stopped after 3 iterations. A replay of the
first scenario solve from its saved state: the residual alternating between about 1.5% and 66% at every step, three of
the EU's sugar quotas (from AFR_REST 844 kt, India 10 kt, South Africa 274 kt) switching between sigma 0 and 1 in turn.
trq_solve set each quota's sigma to its fixed point at the flows of the step (a bisection on the sigmoid at fixed
market prices); with the out-of-quota tariff of 661 EUR/t, above the sugar price, the market's prices then moved so far
that the next step's fixed point was on the other side. CAPRI solves the quotas with the prices in one system
(trqSigmoidFunc_, TRQImports_ in m_globMarket) and has no such loop. Came in with the market move's quota stage (stages
4-5, 4 November), which gate 16 did not include; the mini-EU runs converged, more slowly (market time 50 s before stage
4, 120-330 s after).

- **Effect:** the full-EU scenario market did not converge; the runs could not finish
- **Status:** **fixed** 5 November 2026 (branch trq-relax): trq_solve takes the full step only until a quota's gap
  g = Sigmoid(fill) - sigma changes sign, then the regula falsi point of the bracket (Illinois variant), an end not
  revisited in 4 steps dropped (the prices move on with the market's steps); trq_gap, max |g| (CAPRI's trqSigmoidFunc_
  residual), counts in the solve's convergence test with the move. The equations are unchanged. Replay of the stuck solve:
  residual 1e-9 and quota gap 2e-7 at step 100 (tolerance 1e-7 for both). Mini-EU F2F against the same code without it
  (mini_k115): the same 6 iterations, market time 680 s against 1011 s, 77 values apart by more than 1e-6 relative
  (welfare TRQ rents, dairy block z, at most about 5e-6), the deviation from CAPRI 7.81 as before. Test:
  test_trq_fill_converges_when_the_market_responds_more_than_the_flow (full steps keep swinging, the search converges
  to 1e-10). Confirmed by the full Farm-to-Fork run r213 (5 November 2026): converged in 13 iterations, deviation from
  JRC121368 4.59 (gate 16: 4.18; the beef and poultry prices not yet attributed).
- **Market time:** most solves had still run to the 100-step cap because the quotas' sigmas settled one step behind
  the prices (diagnosed 5 November 2026: the residual meets the tolerance by step 70, the quota moves by step 100). The
  quota bracketing's cost per step was cut first by computing each trial on the quota's own cells (commit 3818bc5,
  identical results, market time about halved in the full run). **Then the sigmas solved with the prices** (5 November
  2026, `market.trq_joint = true`, the default; MARKET_IPOPT_DESIGN §7.1 step 2 for the quotas): inside each
  commodity's trade solve the active quotas' sigmoid arguments are unknowns beside the prices, and one Newton system
  meets the market balances and CAPRI's trqSigmoidFunc_ for every active bilateral and global quota
  (`BilateralSolveMixin._bilateral_inner_trq`; `BilateralCommodity.trq_arguments`, `trq_equation_gap`). The
  commodities are still linked by the outer fixed point (G3 solves the whole market as one system). Replay of the
  full-EU scenario solve that ran to the cap: 33 steps, 116 s, converged (quota gap 3.4e-8), against 100 steps, 228 s,
  not converged; prices equal within 4.3e-9 in log. Mini-EU Farm-to-Fork against mini_k116 (the same code with the
  lagged sigmas): the same 6 iterations with the same rows above 0.05% at each, data values apart by at most 5e-5
  relative (a Croatian grassland dual; DDGS net exports and the CASE price about 1e-5), deviation from JRC121368 7.82 in
  both; scenario market time 287 s against 712 s. Full Farm-to-Fork against full_k116c: the same 12 iterations and rows,
  prices within 6.4e-7 in log, deviation 4.56 in both; scenario market time 576 s against 2,421 s, the run 45 minutes
  against 89 (part of the difference is the machine's speed on the day). `market.trq_joint = false` keeps the lagged
  sigmas (trq_solve's bracketing). Tests: test_joint_trade_solve_meets_the_market_and_the_quota_equations,
  test_import_prices_at_trial_sigmas_equal_the_stored_offsets.

<a id="k118"></a>
### K118: The market supply Hessian's cache key did not cover the supply data (found 5 November 2026, with DEP-22)

The market supply Hessian is measured once per baseline and cached on disk (.cache/market_supply_hessian). Its key held the
supply code's fingerprint (since 30 October 2026), the baseline's totals and the supply settings, but not the data files. DEP-22
changes the 2030 feed slopes, i.e. the supply models' price response, without moving the baseline's totals: a run after it would
have taken the Hessian measured on the old slopes from the cache. Not seen in a run (the DEP-22 runs were the first with the
new data and measured anew); found while preparing them.

- **Effect:** none observed; a stale Hessian after any data change that leaves the baseline's totals unchanged was possible
- **Status:** **fixed** 5 November 2026: `capri_mod/coupling/hessian.py` supply_data_fingerprint, a hash of every CSV under the
  run's data folder but the market's, the validation references' and the schema's (path and content), is part of the key.
  Any change of those files means one new measurement (full EU about 45 minutes).

<a id="k119"></a>
### K119: The CAPTRD trajectory took CAPRI's "Pigs total" aggregate for the model's PIGS (found 6 November 2026)

`tools/check/reproduce_builders.py` (the data-layout move's rebuild check) found
`capri_data/scenarios/captrd_2030/regional.csv` different from what `tools/build/build_captrd_trajectory.py` wrote:
468 rows of PIGS (246 yields, 222 herds; e.g. AT21 yields 1.0117 committed against 1.1544 rebuilt, herds 0.9983
against 0.8482), deterministic and the same on dev before the move.

- **Cause:** K116 (9d7d251, 4 November 2026) changed the shared `tools/build/build_trajectory_model_keys.py` so that a
  factor under the model's own name is kept instead of its alias's (for the CAPRI-reference trajectory, OFOD = OFAR +
  ROOF), with BULL excepted. CAPTRD's series hold a PIGS key, and it is another item: CAPRI's "Pigs total" aggregate,
  (PIGF,SOWS).PIGS (reports/aggreg_sets.gms l. 101, 132), which CAPTRD computes after its estimation as LEVL = PIGF +
  SOWS + piglets produced and YILD = (pork in 1000 t + piglets in 1000 heads) / LEVL x 1000, units mixed
  (captrd/aggreg_and_report.gms l. 262-283; AT21 2017: LEVL 361.06, PROD 175.66, YILD 486.5). The model's PIGS is
  CAPRI's SOWS (codes/model_activities.csv: piglets per sow in yields.csv, sows in animal_numbers.csv). The aggregate's
  factor follows the herd mix, not the output per animal (AT21: +15% against +1-5% for SOWS and PIGF). An older part of
  the same error, not from K116: where SOWS had no factor, the region already took the aggregate's (yields DEA2, DEB1,
  FI20, SK03; herds 15 regions), and the EU fallback factors were the aggregate's (yields 1.006 against SOWS 1.0794,
  herds 0.9079 against 0.8367).
- **Effect:** runs on the CAPTRD trajectory (`--trajectory captrd`; `tools/run/run_vcs_2030.py`); the Farm-to-Fork and
  Green Deal runs on `capri_ref_2030` were not affected (that trajectory holds no PIGS key under CAPRI's name; rebuilt
  unchanged).
- **Status:** **fixed** 6 November 2026 (the project lead's decision: PIGS keyed to SOWS, as CAPRI): PIGS joins BULL as
  a model name that is CAPRI's name for another item (`CAPRI_OTHER` in the key builder): the alias replaces it in the
  regional and EU blocks, and where the alias has no factor the model name gets none (the region falls back to the EU
  factor, itself SOWS's). Rebuilt: the 468 rows equal the committed file; the EU PIGS factors now SOWS's; 19 regional
  entries that had the aggregate's factor dropped (4 yields, 15 herds). The VCS pair to be rerun on it.

<a id="k120"></a>
### K120: The market supply Hessian measured after the baseline's first supply solve had lost most of its response (found 6 November 2026, S7)

In CAPRI's coupling form (market.demand_calibration = "capri") the market supply Hessian was moved from the baseline's
end to the calibration point, measured right after the baseline's first supply solve (uncommitted S7 step, 6 November
2026, to stop the full-EU baseline's oscillation). With it the baseline converged in 3 iterations (37 units), but the
Farm-to-Fork scenario diverged from its second iteration in the 37- and the 20-unit runs (young-animal imbalance
0.10 -> 52 -> 117; Norway's whey and skimmed-milk-powder markets unsolved: 189,000 kt and 34,000 kt of supply against
92 kt and 56 kt of use). The same 20 units had converged in 6 iterations with the Hessian measured after the baseline.

- **Cause:** a regional model's calibration is complete only at its second solve. The dairy, cattle and genetics
  split columns (supply/nlp.py, the "_late" columns grass_z, dairy_z, cattle_z_, genet_z_, hist_) enter after the
  region's first solve, and a solve that finds them recalibrates the region at the prices it is given. The Hessian's
  price shocks each start from the state the first solve left (restored before every shock), so each shock's solve
  recalibrated its regions at the shocked price and cancelled the response. Measured: Dresden (DED00000) recalibrated
  in 46 of its shock solves; the 20 units' Hessian had a response for 19 of 35 prices, none for milk, meat, eggs, fruit,
  wine, olives or the young animals, and Germany's wheat 626 against 6,004 measured after the baseline. In the
  baseline, whose prices hardly move, the missing response mattered little; under the Farm-to-Fork shock the market
  saw almost no supply response for those products.
- **Effect:** the uncommitted S7 runs of 6 November 2026 (37 and 20 units); no committed run.
- **Status:** **fixed** (checked on 20 and 37 units and the full EU, below): in "capri", the baseline's regional models are solved once more
  at the reference prices before the measurement, so the measurement starts from calibrated models (CAPRI measures on
  its calibrated supply models, supply/calibrate_supply.gms). Dresden: no recalibration during the measurement, 30
  prices with a response, wheat 4,702 against 4,967 after the baseline; 20 units: all 35 prices respond (Germany's wheat
  5,683, milk 715). The loop goes on with the first iteration's own supply results. 20 units, Farm-to-Fork: converged in 6 iterations
  (540 s), the indicators within 0.2 points of the run with the Hessian measured after the baseline (mini_s7c1).
- **Found with it: the baseline calibration's stall rule.** SupplyModule.calibrate_to_base leaves a region whose
  drift a round does not reduce by 5% (projection.base_cal_stall_ratio). With the Hessian measured on calibrated models,
  the baseline's first round finds every region at its target (drift 0) and the next round sees the drift of the prices
  moved since (Dresden's pulses 4.2%, Ile-de-France's sugar beet 1.6%): read as a failed correction, every region was
  left and the baseline stopped uncorrected (20 units: baseline activities up to 1.5% from the earlier run). Fixed: a
  drift above projection.base_cal_tol after a round within it is corrected, not left (Dresden and Ile-de-France: 4.2%,
  0.6%, 0.3% over the rounds). A region whose drift stays below the tolerance stalls as before, so the supply mode's
  runs are unchanged where that case did not arise (checked: the mini-EU Farm-to-Fork run in the
  supply mode is identical to 962a907's, rtol 0). The residual drift after the four rounds (20 units): Hungary's
  set-aside 2.8% (25.3 against 26.0 kha; set-aside is held by its rules, the correction overshoots and stalls), Norway's
  bulls 1.6%, all others below 0.9%; the largest at the first round, Norway's bulls 12.3% (3.82 against 3.40 thousand
  heads), Italy's set-aside 7.7%. Before, the recalibration at the second solve absorbed these drifts.

- **Full-EU check (7 November 2026, commit b2b7422, local):** Farm-to-Fork converged in 12 iterations (baseline 8,
  3,932 s); its baseline prices are within a median 0.08% of the supply-mode run's (full_d22), none above 5%, and the
  indicators within 0.5 points (milk price +21.2% against +20.7%). Green Deal converged in 34 iterations (6,260 s; the
  supply-mode Green Deal runs took 18-21), on the same baseline as the Farm-to-Fork run (prices, production and use
  within 1e-5 relative). Its indicators are within 0.5 points of the supply-mode Green Deal run r211_gd_gate16 except
  the beef price (+13.5% against +11.2%) and the poultry price (+8.6% against +7.3%); that run is at an older commit
  (65cd4d8, 122 inputs differing), so the gap is not attributable to the coupling alone. The Green Deal's long tail is
  CAPRI's stop rule (rows above 0.05%), not the prices: the EU prices are unchanged to 0.01 points from iteration 16,
  while member-state minor and feed cereals (OATS, OCER, RYEM, FCER in Bulgaria, Hungary, Greece, Slovakia) move by
  0.1-2.9% between iterations, the pattern of [K79](#k79). Still open in S7: the baseline calibration's first-round drift
  (94% in the full EU, then 11.8% and 2.5%); located below (7 November 2026), not yet resolved.
- **The same-commit pair (7 November 2026):** Green Deal in "supply" at 803c4cf (b2b7422 and a documentation change;
  inputs identical, full_sup_gd): converged in 21 iterations (3,545 s, the Hessian from the cache), against 34 in
  "capri". The EU indicators agree within 0.3 points (beef price +13.4% against +13.5%, poultry +8.5% against +8.6%,
  cereals production -6.2% against -6.5%): the beef and poultry gaps against r211 come from the 125 commits between,
  not from the coupling form. The rows that keep CAPRI's stop rule going in the tail are the same in both forms
  (Bulgaria's other cereals, Greece's maize and feed bulks, Ireland's feed cereals in "supply"), so they are the
  model's under the Green Deal, not the new form's; "capri" takes 13 more iterations to bring them under 0.05%. Why it
  damps them more slowly is not measured (one candidate: its market supply Hessian is measured at the calibration point,
  "supply"'s at the baseline's solution). Subsets do not show the tail: 20 units 14 iterations, 47 units (every unit of
  BG, HU, EL, SK and the mini-EU's) 15, in "capri".
- **Farm-to-Fork, the same-commit pair (7 November 2026):** "supply" at 803c4cf (full_sup_f2f): scenario 12 iterations,
  baseline 2 (3,355 s); "capri" (full_s7): scenario 12, baseline 8 (3,932 s). The 24 indicators within 0.5 points (milk
  price +21.2% against +20.7%, cereal price +10.5% against +10.8%, beef +30.1% against +30.3%); the deviation from
  JRC121368 over 20 indicators 4.54 against 4.55; set-aside and labour equal to 0.1%.
- **The manure pools' price, CAPRI's (7 November 2026):** CAPRI sends its regional models the weighted average of the
  pools' clearing prices of the last steps (manuremarket/simu_manure_market.gms l. 214-226); capri-mod sent a damped step
  towards the new clearing prices. outer_loop.manure_pool_price_update: "capri" the default since 7 November 2026 (the
  project lead's decision), "damped" capri-mod's own. Mini-EU Green Deal 2030 in "capri": 23 iterations with CAPRI's
  price against 14 damped, indicators equal to 0.1 point, final pool gap 0.03% against 0.6%; "damped" reproduces the
  earlier run exactly (rtol 0). Full-EU Green Deal 2030 in "capri" (results store f802d7469075, commit 9598b3e):
  converged in 47 iterations, 6568 s, against 34 iterations, 6260 s, damped (9fce879f41b2, commit b2b7422; the two
  runs had different package versions, pandas 2.3.3 against 3.0.5, so the times are not a clean pair); the 24
  indicators of compare_runs.py within 0.2 point. With CAPRI's price the pools' gap stays between 1% and 12% after
  iteration 20 (damped: below 2.3% from iteration 14); the iterations where it rises (34, 39, 44) are those where the
  rows above CAPRI's 0.05% rise again (to 20, 17, 13). The rows most often among the five largest after iteration 14
  are Bulgaria's cereals (OCER, FCER, OATS), Greece's feed (FPRO, FCER) and Ireland's cereals with CAPRI's price;
  Hungary's cereals (OCER, BARL), Greece's maize and feed and Bulgaria's OCER damped. Whether the pools' price drives
  the relapses or only moves with them is not established.
- **The baseline calibration's first-round drift, located (7 November 2026):** a full-EU baseline with CAPRI_CAL_DEBUG
  (Green Deal settings, commit 9598b3e, stopped after the baseline's 8 iterations; the same calibration trace as the
  Green Deal run, 0.21%, 93.9%, 11.8%, 2.5%). Round 0 finds every region within 0.21% of its targets. Round 1, after
  the first market solve, has 37 regions above 5%: 19 of them at set-aside (SETA) and 12 at pulses (PULS), the two
  crops that count towards the greening ecological set-aside row (ecoSetAside: SETA at FALL's weight, PULS at its own;
  supply/policy.py). The largest: Aquitaine (FR610000) SETA 2.26 against 1.16 thousand ha (93.9%), Extremadura
  (ES430000) PULS 10.10 against 5.78 (74.9%), Mazowieckie (PL220000) SETA 6.06 against 5.06 (19.9%). The rounds do not
  settle them: at the fourth and last round ES430000 PULS 6.56 (13.6% above its target, after 5.40, 6.6% below, at the
  third) and FR610000 SETA 1.31 (13.0%); after it the rounds are used up and the remaining drift is not measured. My
  reading, not checked: where the ecological set-aside row binds, SETA and PULS substitute for each other along a
  linear row, so a small price change moves them far and the linear shift's correction overshoots. To check: the row's
  dual and activity in those regions at round 1. The gaps are small in area (the largest 4.3 thousand ha, ES430000 PULS), so the effect on the
  EU indicators is likely small (not measured). An earlier guess, Luxembourg's set-aside (the largest move in the
  [nlp] trace), was wrong: its level is below the 1-thousand-ha threshold of the drift measure.
- **Checked on 9 November 2026 (S7 and S2 in place, the full-EU Green Deal at 1b97161, its baseline ref_star3):**
  - **Not the ecological set-aside row.** I read CAPRI's equation (supply_model.gms l. 1937-1964): it has the same
    form as the model's row.
    - In CAPRI's own 2030 Green Deal levels (capri_marginal_terms_ini_2030), the row binds in Mazowieckie
      (PL220000): slack 0.
    - The row is slack in Aquitaine (FR610000), 24 thousand ha, and in Extremadura (ES430000), 162 thousand ha.
    - In the model's base the row is also slack there (base gap -58.6 and -160.8 thousand ha, catch crops
      included). So the 7 November reading (SETA and PULS substituting along a binding row) does not hold for
      the two largest cases.
    - Mazowieckie's base does not meet the rule by 0.59 thousand ha. There the rule is held at the base's value
      (REGISTERED).
  - **What moves the regions.** The baseline's market moves the EU prices from CAPRI's calibration point by up to
    1.3%:
    - beef -1.3%, sugar -0.9%, other cereals -0.6%, pulses +0.6% at the last iteration;
    - the EU's beef production is +1.2% and sugar +0.9% against CAPRI's (compare_baseline_capri.py).
    - A few regions answer that strongly. In Extremadura, a stand-alone probe (the model built outside the 2030
      projection, so its levels are not the run's) moves pulses 7.7 to 10.9 thousand ha (+41%) for the first
      iteration's price signal. With the pulses signal alone (+0.49%) the move is +15%. With the signal reversed
      it is -4%. The response is asymmetric, so some kink is involved; not identified.
    - CAPRI's own PMP term for Extremadura's pulses is flat: g = 65 EUR/ha per 100% change, CAPRI's H about
      11 per thousand ha (pmp_capri_2030).
  - **What is left at the baseline's end** (crop levels per region against CAPRI's 2030 Green Deal levels,
    activities of at least 1 thousand ha, 3,177 pairs):
    - median 0.22%; 95% within 1.5%; 7 pairs above 5%, 7 thousand ha in all;
    - the largest: Extremadura's pulses +25.7% (7.27 against 5.78 thousand ha), CZ040000 other fodder +18.5%
      (fodder is held by its balance and not shifted), IT910000 voluntary set-aside -12.5%.
    - The effect on the EU indicators is small. The open question is why the baseline's EU beef and sugar supply
      sit about 1% above CAPRI's at the calibration point. Not analysed further.

- **The baseline against CAPRI's Green Deal baseline (9 November 2026, night):** with the base point moved to CAPRI's
  Green Deal baseline res_2_1730greendeal_refdefaulta (the project lead's decision; docs/BASELINE_REPRODUCTION.md), the
  mini-EU baseline's crop levels were 228 thousand ha (of 25,505) from CAPRI's, almost all in a few regions and the
  same factor for every crop of a region: Denmark +4.1%, Croatia +2.3%, Portugal's PT18 +1.2%, Spain's ES61 +0.7%,
  Poland's PL12 +0.5%. Not a calibration drift: the projected data themselves were off by those factors. The
  projection's land reconciliation (capri_mod/projection/reconcile.py) rescaled each region's crop areas to its 2017
  ratio of cropped area to land, carried to the projected land; with CAPRI's own 2030 levels, which are one consistent
  solution, that moved them by the change of the ratio between 2017 and 2030, and the baseline calibration then
  reproduced the rescaled levels. Fixed: a trajectory of CAPRI's own results (capri_ref_*) is not rescaled (CAPRI
  simulates from CAPMOD's results as they are); a trend projection (CAPTRD) still is. The projected 2030 crop areas of
  the 20 units are then CAPRI's to round-off (before: 214 thousand ha off, 0.24% mean adjustment over 221 regions,
  4.4% the largest).

### K121: Other fodder split into CAPRI's OFAR and ROOF (S2 step 1a, 7 November 2026)

Until 7 November 2026 the model had one other-fodder activity, OFOD = CAPRI's OFAR (other fodder on arable land) +
ROOF (fodder root crops), one crop-diversification group (DEP-42) and one fodder balance (FOFA); CAPRI's fodder root
crops' feed FROO was in the rations but tied to no land. S2 step 1a (claude/s1_s2_implementation_plan.md, the project
lead's decisions of 1 and 7 November 2026) makes OFAR and ROOF the model's own activities, as CAPRI's:
- codes/model_activities.csv and model_activity_classes.csv (two crop-diversification groups, CAPRI's
  cropDivGrps_mCact; both in FODCRP, landTypes_to_pact ARAC and EPRD_TO_GRP FARA), definitions.CROPS;
- the fodder balances as CAPRI's SUPBAL_ of FODF: FOFA from OFAR and FROO from ROOF (tools/build/build_fodder_balance.py);
- the ecological set-aside row: OFAR at CAPRI's weight times the member state's legume share, ROOF not counted
  (supply/policy.py; before, OFOD at that weight scaled by OFAR's share of OFOD);
- the builders' mappings (base areas, fertiliser groups, N and P balances, irrigation, prices, trajectories: no OFOD
  composite left); the data rebuilt by the pipeline (doit) on the restored CAPRI sources: every changed file is
  identical outside OFOD/OFAR/ROOF (FOFA/FROO) rows and columns to 1e-9, and OFAR + ROOF equals the former OFOD to
  6e-14 (EU: OFAR 17,173, ROOF 174 thousand ha).
- ROOF has no CAPRI elasticity estimate in the sources (supply_elas, PELA, the PMP elasticities carry OFAR only), so its
  provenance is NO_CAPRI_VALUE in all 192 regions that grow it; it is not held at its level, because CAPRI's 2030 PMP
  terms cover it (pmp_capri_2030.csv), as in CAPRI. OFAR's curvature is unchanged (Q of OFAR = Q of the former OFOD,
  median ratio 1.0000001 over the mini-EU's units).

Mini-EU Farm-to-Fork (S7 form, 20 units; commit after f10a8dd, local): converged in 6 iterations, baseline 5, as the dev
run (mini_f2f_store_v2, commit d113d69, same environment); the 24 indicators within 0.9 point. The largest changes:
cereal production -17.7% against -16.8% (CAPRI -15.0), oilseed production -22.5% against -22.1%, fertiliser N2O
-38.5% against -38.2%; other fodder falls less (OFAR + ROOF -13.6% against OFOD -17.0%) and the cereal area more (-4.9%
against -4.0%). Why other fodder falls less is not measured: one candidate, not checked, is the feeding (FROO now costs
ROOF's land, so the rations may move from FROO to FOFA, which OFAR supplies).

Found with it, not caused by it: build_farm_size_noneu does not reproduce farm_size_noneu.csv after the container's
package change of 7 November 2026 (casadi 3.8.1 to 3.8.2): cells near zero of an estimate that is not unique (Turkey's
TR800000 sheep holdings 15-20 head 5e-50 against 845); the committed file kept, the builder's output not used.

### K122: Set-aside split into CAPRI's VSET and FALL (S2 step 1b, 7 November 2026)

Until 7 November 2026 the model had one set-aside activity, SETA = CAPRI's VSET (voluntary set-aside) + FALL (fallow),
with VSET's exemption from the calibration bounds, and the report split a SETA level into VSET and FALL by CAPRI's VSET
share at base and the share of a change CAPRI's PMP terms give VSET (K111). S2 step 1b makes VSET and FALL the model's
own activities, as CAPRI's:
- codes/model_activities.csv and model_activity_classes.csv (both CAPRI's crop-diversification group OSET,
  landTypes_to_pact ARAC), definitions.CROPS;
- the landscape floor on both (CAPRI's e_setaLandscape over setaFallow, supply_model.gms l. 2315-2321; its SETF the base
  VSET + FALL), the ecological set-aside row with each at its own weight (1 and 1);
- the calibration bounds: VSET exempt (set_supply_bounds.gms l. 42-43), FALL under the rule (0.1 to 10 times its level,
  at least + 100), as CAPRI; before, SETA was exempt as a whole;
- the BISS adder and the EU price rows (0) on both; the set-aside and labour reports from the two levels directly
  (set_aside_split.csv keeps CAPRI's premiums per ha only; its split columns and the PMP weights' helper removed);
- the builders' mappings (no SETA composite left; CAPRI's ISET, GSET and TSET, which have no area in its 2017 and 2030
  data, no longer mapped); the data rebuilt: every changed file identical outside the set-aside rows and columns to 1e-9,
  except the winter-cover option (below).

Found with it: the winter-cover option's maximal share (build_winter_cover_option.py) counted the set-aside area as open
to catch crops, because CAPRI's wintercovershare.gms gives VSET a filled share of 1 and the builder looked the share up
under the model's SETA, which CAPRI's file does not have (so 0). With VSET's own share the maximal share falls where
there is voluntary set-aside (AT110000 0.529 to 0.473); 660 cells of winter_cover_option.csv change.

Mini-EU Farm-to-Fork (20 units, against step 1a): converged in 6 iterations, baseline 5; the 24 indicators within 0.6
point (poultry -18.4% against -17.8%, manure N2O -22.3% against -21.9%). Set-aside and fallow 2,405 thousand ha against
2,418; VSET 1,032 against the reported split's 698, FALL 1,373 against 1,720 (now the models' choice under FALL's bounds);
labour -7.9% against -7.0% (VSET's and FALL's own labour coefficients). CAPRI's own split under Farm-to-Fork is not at
hand to compare.

### K123: Grassland split into CAPRI's GRAE and GRAI (S2 step 1c, 8 November 2026)

Until 8 November 2026 the model had one grassland activity, GRAS (CAPRI's GRAE + GRAI), and CAPRI's two activities
through a split column z (area moved from GRAI to GRAE, Sprint 7a: livestock._grass_intensity_column): z's N balance,
fodder and mineral-N coefficients the differences of the two activities (nitrogen.grass_intensity_delta, with GRAE's
and GRAI's mineral N taken as GRAS's in proportion to their need), PMP (q_GRAE + q_GRAI) z^2 / 2 from
grass_intensity.csv, and a linear term fitted to the duals of the region's first solve (a "late" column: part of the
mechanism behind K120's first-round drift). S2 step 1c makes GRAE and GRAI the model's own activities, as CAPRI's:
- codes/model_activities.csv and model_activity_classes.csv (land type GRAS; fodder through CAPRI's FEDACT_TO_FODDI,
  as FODCRP names their product GRAS; tools/build/build_code_lists.py checks it so), definitions.CROPS;
- each with CAPREG's own data: grass output (the GRAS item of each activity; DE110000 19.3 and 45.1 t fresh matter per
  ha, their mean the former GRAS's 32.2), costs, premiums, labour, mineral N (nutrients_regional: DE940000 GRAE below
  GRAI), N and P coefficients, CAPRI's own 2030 PMP terms and trajectories;
- the grassland row and the permGras rule over both; the grass fodder balance FGRA shared by their production (u per
  ha in proportion to each one's grass output, the sum exact at base; fodder_balance_2017.csv one row per producing
  activity); the histosol and luc accounts over both;
- removed: the split column, its state, its calibration from the duals, nitrogen.grass_intensity_delta and the
  grass_override machinery, the GHG tax's and the P accounts' z terms, build_grass_intensity.py and grass_intensity.csv,
  and intensity_q_2030's rows and file that only the grass and set-aside splits read (GRAE, GRAI, VSET, FALL, ROOF,
  OFAR; intensity_q_recipe2017.csv).
The data rebuilt: every changed file identical outside the grassland rows and columns to 1e-9; GRAE + GRAI equals the
former GRAS to 1e-11 (EU 40,426 thousand ha each, CAPREG's base split being 50:50).

Found with it, from step 1a: build_ration_trajectory_2030.py's 2017 pattern did not list ROOF, so the fodder roots had
no 2030 fodder trajectory (capri_ref_fodder_2030.csv without ROOF rows; their use per ha stayed at 2017 in the 1a and 1b
runs); fixed here.

Mini-EU Farm-to-Fork (20 units, against step 1b): converged in 6 iterations, baseline 5; the 24 indicators within 0.3
point (beef animals -21.0% against -21.3%). Grassland 8,059 thousand ha against 8,057; under Farm-to-Fork GRAE 4,022 to
5,232 (+30%), GRAI 4,033 to 2,827 (-30%). The baseline calibration's drift (K120) is the same as in 1b (0.02%,
25.8%, 2.0%, 0.65%, 0 against 0.02%, 25.9%, 2.1%, 0.65%, 0): removing the late grass column did not move it, consistent
with K120's finding that the drift is in set-aside and pulses. Against dev (0.05%, 12.3%, 3.6%, 2.8%, 0) the second round
is larger and the third and fourth smaller; 1a's trace equals dev's, so the change comes with 1b, the set-aside split
(VSET and FALL measured separately, FALL now under the bounds; not analysed further).

Full EU (S2 branch at 22dac48 against dev, 8 November 2026):
- Farm-to-Fork (run f3e741eaa428 against dev 9b026803124f): converged in 12 iterations, baseline 8, 1814 s; the 24
  indicators within 0.2 point; mean absolute deviation from JRC121368 4.53 against 4.56.
- Green Deal 2030, CAPRI's averaged manure pool price (full_gd_s2.pkl against dev f802d7469075): converged in 21
  iterations against 47, 5401 s against 6568; the indicators within 0.3 point except manure N2O (-11.6% against -10.8%);
  mean absolute deviation from CAPRI's figures 8.77 against 8.84. Set-aside under the landscape target: VSET 2,505 to
  6,702 thousand ha against 2,502 to 4,549, FALL 5,403 to 8,967 against 5,403 to 10,765 (the 1b split: VSET outside the
  bounds, FALL within them). Low nitrogen feed 59.3% of eligible LU against 54.3%. Not analysed further.
- Baseline levels against CAPRI's 2030 (compare_baseline_capri.py): GRAE +0.2%, GRAI +0.1%, OFAR -0.8%, ROOF +1.0%,
  FALL +0.6%, VSET -1.9%.
- Reporting error found with the Green Deal run: run_f2f_2030.py's histosol area (the denominator of "fallowing
  histosols") still summed a GRAS activity, so from 1c the grassland histosols were left out (1,823 thousand ha against
  3,665) and the share showed 84.7%; the idled area itself is unchanged (1,545 thousand ha against dev's 1,524), the
  share 42.1% against 42.8%. Fixed after the run, with the other scripts still on the old codes (run_vcs_2030.py,
  compare_baseline_capri.py, pmp_cross_term_check.py: GRAS, OFOD, SETA). The stored full_gd_s2.pkl keeps the wrong
  denominator.

### K124: CAPRI's crop technologies T1 and T2 as mix columns (S1, 8 November 2026)

Until 8 November 2026 the model had CAPRI's two technologies per crop (intens/techf.gms: T1 high yield, T2 low yield,
50-50 at the calibration point) only through the curvature of the optimal split: pmp_capri_2030.csv's crop term is the
Schur complement of CAPRI's 2x2 technology block (DEP-9). The area response followed CAPRI's terms; the change in average
yield, inputs and nutrient need from shifting between the technologies was not represented. S1 (docs/design/
S1_MIX_COLUMNS.md, capri_mod/supply/techn_mix.py) adds one column z per crop with both technologies, x_T1 = X/2 + z,
x_T2 = X/2 - z, -X/2 <= z <= X/2:
- PMP CAPRI's block in (X, z), exact (Q_XX, Q_Xz, Q_zz from p_pmpQuadTechn; X's curvature with z optimised out equals
  the collapsed term on all 5,417 blocks to 1.4e-13): pmp_capri_2030_mix.csv;
- per unit z, the differences T1 - T2 of CAPRI's technology factors (techn_mix_2030.csv): output and the fodder rows
  +0.4 x yield, the factored inputs (SEED, REPM, REPB, ELEC, EGAS, EFUL, ELUB +-0.25; INPO +-0.25 and PLAP +-0.4 on
  their current cost, with the Green Deal changes), the nutrient need (NUTNED_'s SQRT(1 + y)(1 + y): +0.590 x the
  crop's), the N balance and mineral N rows (the environmental accounts' unit balance at each technology's yield), the
  rural-development premiums by scheme (AE -0.5/+0.5, N2K -1/+1, SeExte; zero where the scheme pays nothing);
- z's linear term calibrated with the activities (not a free column), so the base is a first-order point at z = 0.
Columns in 4,626 region-crop pairs (FALL only where CAPRI has T2, 24 regions; the decision of 7 November 2026).
Setting supply.crop_technologies, CAPRI's (on) the default since 8 November 2026; off reproduces the collapsed form.

Checks:
- Off: the mini-EU run identical to S2 except the histosol reporting fix of K123.
- Baseline, on: z at EU level 3.1 thousand ha of 102,162 (OFAR 1.5), none at a bound; EU activities within 1e-4 of off.
- Mini-EU Farm-to-Fork, on: converged in 6 iterations; the indicators within 0.2 point of off.
- Full EU, on, against S2 (the market supply Hessian measured again: 1,466 s Farm-to-Fork, 1,524 s Green Deal):
  - Farm-to-Fork (run 7a797932c3b2 against f3e741eaa428): converged in 13 iterations against 12, 3,267 s; the indicators
    within 0.4 point; mean absolute deviation from JRC121368 4.46 against 4.49. z moves 671 thousand ha to T1 (of 97,463):
    SWHE 1.39% of its area (average yield +0.55%), BARL 1.33%, MAIF 0.76%, OATS 0.68%; 21 pairs at a bound.
  - Green Deal 2030 (run b7b38df49dae against full_gd_s2.pkl): converged in 28 iterations against 21, 4,209 s; the
    indicators within 0.1 point; mean absolute deviation from CAPRI's figures 8.78 against 8.77. z moves 78 thousand ha
    to T1 (SWHE 0.15%, SUNF 0.27%); 2 pairs at a bound. The histosol share 42.1% against 84.7% is K123's reporting fix
    (full_gd_s2.pkl keeps the wrong denominator), not S1.
  Why Farm-to-Fork moves more toward T1 than the Green Deal, and why the Green Deal needs 7 more iterations, is not
  analysed. The technology shares are not compared with CAPRI's scenario results (not in hand, as K13).

Registered approximations (not closed):
1. No emission-tax term on z (supply/ghg_tax.py's finite differences have no key per z); matters only in the GHG-tax
   scenario.
2. The yield-dependent input costs (_apply_yield_input_costs) are not differentiated by technology; z's input costs
   are CAPREG 2017's coefficients x the factors.
3. The fertiliser options (inhibitors, precision farming, timing) do not see z's need; z enters the need and the N rows.
4. The premium split uses CAPRI's 2030 reference shares by scheme (dataOut PRME) on the solve's premium.
5. Sugar beet's VCOF factor (sugar/techf.gms l. 103) is not carried (taken as without effect since the quotas ended;
   to be confirmed).
Open with it: whether CAPRI's endogenous yields act on the technologies' mean yield as here (S1_MIX_COLUMNS.md
section 6).

### K125: S7, CAPRI's market calibration, the model's only form (9 November 2026)

S7 (docs/design/S7_DEMAND_CALIBRATION.md) built CAPRI's calibration of the market (once per run at CAPRI's own 2030
market data; the baseline a market solution; only the supply side following the supply models each iteration, at
CAPRI's marketed over gross production, grofNEprod) as market.demand_calibration = "capri", beside the former form
"supply" (DEP-5: the demand recalibrated to the supply models' output in every baseline iteration, the baseline at the
reference prices). The agreed condition for removing "supply" (the full Farm-to-Fork run validating "capri") was met
on 7 November 2026 (K120: full-EU Farm-to-Fork and Green Deal converged; baseline prices within a median 0.08% of the
"supply" run's, none above 5%), and every validation run since used "capri", but the switch was not made until
8 November 2026 (an omission). Removed: the setting, the EU's and Norway's base alignment to the supply models
(_align_eu_base_balance, _align_sup_base, base_net_exports_eu), the baseline's return at the reference prices, the
Hessian "pending" after a baseline (sv.hessian_pending) and seen.eu_base_supply; DEP-5's main part to the register's
history, its raw milk world pool kept (DEP-5, to close with the non-EU dairy blocks).

Consequence: a baseline measures the market supply Hessian at its start (on calibrated models at the reference prices,
K120), because its own market uses it; the decision of 28 October 2026 (a baseline alone does not measure it, the
scenario on it does) belonged to the "supply" form, whose baseline did not solve the market. A full-EU baseline alone
now takes the measurement (about 25 minutes) unless the cache holds it.

The suite with "capri" the default: 10 failures, all tests written for the old form (the bridge's output unchanged by
the marketed share; the baseline's last round at the base; the base reproduced at the models' own supply; the Hessian
not measured by a baseline; Norway's market supply its run units' alone on a subset run), adapted to CAPRI's form; one
real defect found with them (K126). The tests' helper that fed one country per EU block its whole raw milk now gives
each member state CAPRI's marketed milk (the dairy blocks are per member state).

Open: the scenario-shifter layer (S7 step 5: CAPRI's DATA ChangeFactor / PercentageChange of prep_market.gms and the
supply side's shifters), which the course scenario ladder needs; not built.

### K126: The CasADi trade system without the global quotas' price offsets (found 9 November 2026)

capri_mod/market/trade_ad.import_price_matrices (p = A r + B, the CasADi trade system's import prices) added the
quotas' price offsets only for a commodity with bilateral tariff-rate quotas; BilateralCommodity.import_prices adds
them for bilateral or global quotas. Casein (CASE) has global quotas only, so its offset (up to 278 EUR/t at CAPRI's
calibration point, where the quota binds) was left out of the system. test_casadi_trade_residual_and_jacobian_match
passed until S7, so the offset was presumably zero at the "supply" form's base (not checked). Effect: only the optional
solves that use the CasADi system, market.exact_jacobian (off by default) and market.solver = "newton_krylov" (not the
default); the default solve, which every run with the default settings uses, takes BilateralCommodity's own residual. Fixed: the same condition as
import_prices.

### K127: No N manure trade under the emission tax in a four-unit Belgian run, under CAPRI's market calibration (found 9 November 2026)

test_manure_p_and_k_have_markets_of_their_own (BL210000-BL240000, manure trade on, baseline 3 iterations, then CAPRI's
emission tax at 100 EUR/t CO2-eq, 4 iterations) expected N trade to move under the tax. With S7 the only form it does
not: every unit's N exports and imports stay below 1e-6 t, in the baseline and under the tax, and the N, P and K pools
clear at every iteration (gaps 0.0000). On dev (the former "supply" form, 608ea0b) the same sequence trades 360 t
(BL210000 exports 174 t, BL220000 and BL240000 import 109 and 77 t). The regional models' response to the tax is
nearly the same in both forms (suckler cows -27%, maize, barley and grassland +-16-39%). The N pool's price at the end
of the tax run: -0.181 against -0.212 (the units of the pool price not checked here); the units' N export column costs -0.020 to -0.111 against
-0.051 to -0.142.

Possible reading, not established: a pool with trade costs also clears at zero trade when every unit's marginal value
of manure N lies within the cost band around the pool price, and the product prices differ between the forms
(CAPRI's baseline is a market solution away from the reference prices), so the tax run can end in the no-trade
equilibrium. To check: the units' marginal N values against the band, and the pools' price history (CAPRI's averaged
price, outer_loop.manure_pool_price_update = "capri") in both forms.

The test's tax part is test_manure_n_trade_moves_under_the_emission_tax, an expected failure until this is settled; its
base part passes (the base a first-order point at the calibration point's prices, P and K trade below 0.1 t).

<a id="k128"></a>
### K128: Farm-to-Fork's meat prices against JRC121368 (checked 9 November 2026)

The full-EU Farm-to-Fork at 1b97161 against JRC121368's combined scenario (EU27, % change from the 2030 baseline):
beef price +29.5 against +24.0, poultry price +20.4 against +18.0, pork price +20.5 against +43.0, with EU beef
production -13.7 against -14.0, the beef herd -19.2 against -18.0, poultry production -9.9 against -16.5. In the
model's EU market (both EU blocks): beef production -13.7%, human consumption -5.6%, net exports 667 -> 134 kt; poultry
-9.6%, -1.5%, 2,822 -> 1,676 kt; pork -13.4%, -1.8%, 3,845 -> 1,302 kt. With production close to CAPRI's the beef gap is
in the market's price formation, not in the supply. The Green Deal's beef and poultry prices moved from r211 (gate 16,
+11.2 and +7.3) to +13.4 and +8.8 (1b97161) with the market's ports to CAPRI's form of 4 November (quotas, entry prices
and levies, the non-EU land block) and S7, S1/S2, DEP-22; r211 is not reproducible (its commit 65cd4d8 is not in the
re-rooted history; the earliest commit, a715747, carries K117's quota failure and was stopped after 4 scenario
iterations).

Checked against CAPRI's own inputs (no departure found):
- The market alone at CAPRI's 2030 calibration point (tools/check/check_market_base.py): beef, pork, poultry and sheep
  meat production within 0.16%, prices within 0.21%, bilateral flows within 1.5% (median 2e-5), so every quota's fill
  at the base is CAPRI's.
- The GL food demand: the own-price elasticities at the calibration prices (finite differences on gl_demand_*.csv)
  against CAPRI's p_ElasDem "CAL" (elas_2_1730defaulta): beef, pork, sheep meat, cheese and poultry meat (POUM) in
  every behavioural region (80 for poultry) within 7e-5.
- The Armington substitution elasticities: armington_rho.csv equals CAPRI's p_rhoArm1 and p_rhoArm2 in sim_ini_21730
  (beef 3.5 and 7.1, pork 6.7 and 13.4, poultry 3.7 and 7.3, sheep meat 3.2 and 6.4).
- DEP-12 (no commitment terms in the second Armington nest) has no effect with CAPRI's default: p_arm2Commit is set only
  with modArmington = commitment (arm/modArmington.gms l. 436; default off, capmod/set_global_variables.gms l. 95).

Not settled: JRC121368 is another CAPRI version on another baseline, and its meat consumption and trade changes are not
in hand (the report's tables were not readable from its PDF here), so the gap cannot be split between the version and
the model. Next: CAPRI's own Farm-to-Fork or a market-only shock run on the same version (the course's release or
Bonn, VALIDATION_PLAN §1.3).

<a id="k129"></a>
### K129: BG020000 under the Green Deal: the run settles on one of two branches of the region's response (found 9 November 2026)

The mini-EU Green Deal 2030 at 65f8c65 (mini_gd_s6c) and with CAPRI's fertiliser priors' slack (s6d, mini_gd_s6d; the
slack does not act in BG020000, outside CAPRI's list) end BG020000 at very different crop mixes - maize 169 against 16
thousand ha, barley 14 against 84, other arable crops 80 against 16, pulses 7 against 37, voluntary set-aside 55
against 97. The full-EU Green Deal's response there is large as well (soft wheat -54%, maize -73%, sunflower -62%,
set-aside and fallow 18 -> 193 thousand ha); in the last iteration 13 of 221 EU regions end at IPOPT's acceptable
level, not optimal.

Investigation (9-10 November 2026, the region's solves traced with CAPRI_NLP_DUMP / CAPRI_NLP_TRACE and re-solved alone):
- the region's problem can have two local optima at some prices: in mini_gd_s6c's 19th scenario iteration the warm
  start ended at -1,861,922 and the restart from the previous point (the jump check, K79) at -1,906,423 on the same
  problem, and the run continued on that branch;
- but at most iterations the starts agree: in the mini-EU Green Deal at 1fc8088 with an extra check (10 November
  2026; every solve kept at the acceptable level also solved from the previous point, the standard start and the
  region's last optimal solution), the three starts reached the same objective in each of the last 16 scenario
  iterations (or failed), and the last problem re-solved from the last six iterates at a tight tolerance gives one
  solution, -1,859,343 (maize 15, barley 87, set-aside 99 thousand ha); the run's indicators were identical to one
  decimal without the check, which cost about 30% more time. The check was dropped;
- so the branch a run ends on follows the coupled iteration's path (the prices the market feeds back), not a solve
  that misses a better optimum of its own problem; the objectives of two runs' problems are not comparable (the
  first reading of 9 November, "a worse optimum kept, 2.4% from the best", compared two different problems).
CAPRI solves the same kind of problem with CONOPT, a local solver whose result also depends on its start; which
branch CAPRI's own Green Deal solution takes for the region is to be read from the project lead's CAPRI Green Deal
run, when its results are stored.

- **Measured 11 November 2026 on CAPRI star 3.0's own Green Deal 2030 run** (the project lead's, against its reference; full-EU greendeal2030, damped manure pool prices; not the Farm-to-Fork of JRC121368): beef +13.4% against +20.1, pork +7.9 against +12.9, poultry +8.8 against +13.5.
- **Effect:** the mini-EU Green Deal's cereal production -9.6% against -8.6% between the two runs, most of it this
  region; any run's BG020000 result, and comparisons between runs where the region changes branch
- **Status:** **open**: to compare with CAPRI's Green Deal result for the region; until then a run-to-run difference
  concentrated in such a region is not attributed to the change under test

### K130: Catch crops' cost per ha from CAPRI's reported TOIN (found 9 November 2026)

The winter-cover (catch crop) option's linear cost (tools/build/build_cover_crops.py, catc_cost_eur_ha; the cost curve
of tools/build/build_winter_cover_option.py scales with it) is CATC's input cost TOIN per ha as CAPRI reports it in its
2030 results, not CAPRI's cost coefficients of the winter-cover technology. CAPRI reports TOIN only where CATC has a
level. With the base point at CAPRI's Green Deal baseline (res_2_1730greendeal_refdefaulta), whose catch crops are far
fewer than its calibration run's (EU national rows 2.35 against 9.2 million ha), 160 of the 250 units have no catch
crop and so no TOIN in the baseline: they take the region's own TOIN in the calibration run
(res_2_1730greendeal_refpol_endotech_all_inidefaulta; column cost_source = calibration). Where both runs report it,
the two TOIN per ha differ by up to 25% (input mix at another adoption level).

- **Effect:** the Green Deal's and Farm-to-Fork's catch-crop requirement (e_minCoverCrops) in those units costs the
  calibration run's input bill per ha; mini-EU indicators within 0.4 point of the runs with the calibration run's base
- **Status:** **open**: to read CAPRI's own cost data of the winter-cover technology (the ghg technology tables of
  envind/cover_crops.gms) instead of the reported TOIN, for every unit

<a id="k131"></a>
### K131: Given CAPRI's Green Deal supply, the market's dairy protein products rise more than CAPRI's (found 12 November 2026)

tools/check/check_market_gd.py solves the market alone with CAPRI's own Green Deal 2030 supply-model results as its
supply side (member states' production and raw milk, feed bulks, the prices the supply models saw;
capri_data/validation/greendeal_2030/capri_gd_market_2030.csv). The EU's prices follow CAPRI's within 0.3 points of
price change on average (correlation 0.99; cereals, oilseeds, meats, eggs within about 0.4, beef -0.6); the other
producing regions within 0.17 on average. The dairy products do not: raw milk +12.4 / +11.4% in EU_WEST / EU_EAST
against CAPRI's producer price +11.3 / +10.6; skimmed milk powder +5.0 / +4.9 against +2.5 / +2.6, whey +6.1 / +5.2
against +1.5 / +2.6, casein, concentrated milk and whole milk powder 1-2 points above; butter 1 point below
(+7.3 / +9.7 against +8.3 / +10.8). Protein products above, fat products below: the dairy block's valuation of milk
protein against fat, or the feed use of whey and SMP (CAPRI's FEDM of whey -111 kt, SMP -30 kt in A_EU_WEST), not yet
traced.

Also seen in that check, not an issue of results: in the 534 cells of non-EU regions without production of a product
the market reports the region's base price (none moves), CAPRI's PMRK moves in 364 of them (Pakistan's rye +14.7%).
Whether those regions' consumer prices differ was not checked.

- **Effect:** EU dairy product prices in scenario runs
- **In 9t:** –
- **Status:** open


<a id="k132"></a>
### K132: The voluntary set-aside exempt from the absent-activity rule everywhere (found 13 November 2026)

CAPRI bounds VSET at 1e-6 .. 1e5 (1000 ha) only `$ (p_technFact x DATA VSET LEVL > 1e-6)` (set_supply_bounds.gms
l. 42-43); without a data level the activity has no variable. The model skipped VSET in the bounds loop in every
region, so where CAPRI's 2030 data have fallow only (PL, CZ, RO, SK, CY, MT) VSET could grow from zero: 0.013 kha in
the baseline, 363 kha in PL, 484 in RO, 255 in CZ and 112 in SK in the Green Deal 2030 run (runs/full_gd_buf.pkl),
where EU VSET rose +163% against CAPRI's +80% and FALL +65% against +91%. Fixed: CAPRI's condition
(`RegionalSupplyModel.VSET_DATA_MIN`); with a data level CAPRI's bounds, without one the absent rule.

- **Effect:** set-aside and fallow under area targets (Green Deal landscape features), the per-ha N constraints
- **In 9t:** –
- **Status:** fixed (13 November 2026); the Green Deal run with the fix to be compared again

<a id="k133"></a>
### K133: Fallow held under 10 x its level when a landscape floor needs more (found 13 November 2026)

With a landscape floor CAPRI lifts the fallow's upper bound to half the UAA per technology
(set_supply_bounds.gms l. 159-160, after the general 0.1x .. 10x rule; FALL has T1 and T2 at a LEVL factor of 0.5 in
all 236 regions of sim_ini_21730 that have fallow). The model kept the general rule, which K132's free VSET had
hidden. Once VSET followed CAPRI's rule, RO010000 (12 kha of fallow and no set-aside in CAPRI's 2030 data, a floor of
about 122 kha under the Green Deal's 8% target, more than 10 x its fallow) became infeasible in every scenario solve;
IPOPT's last point was kept, and Romania's market went on moving by up to 197% between steps until the run was
stopped. Fixed: `RegionalSupplyModel.FALL_FLOOR_UP_SHARE` x FALL's technologies (K134) x the UAA the floor is sized on.

- **Effect:** feasibility under the Green Deal landscape target where the data have little fallow and no set-aside
- **In 9t:** –
- **Status:** fixed (13 November 2026); the Green Deal 2030 run with K132 and K133 (runs/full_gd_fall.pkl) converged
  in 19 iterations with every regional solve optimal (RO010000 included); EU VSET +79.1% against CAPRI's +79.5% (before
  +162.8%), FALL +101% against +91%; the prices' and herds' gaps to CAPRI are unchanged

<a id="k134"></a>
### K134: The activity bounds of one technology for crops with two (found 13 November 2026)

CAPRI bounds each technology's level (set_supply_bounds.gms l. 26-27, 42-43, 159-160): every crop but grassland, OOIL,
OIND, NURS, FLOW and OCRO has T1 and T2 at half its level (p_technFact LEVL, the same in all regions of sim_ini_21730;
intens/techf.gms l. 64-75), so its level may reach max(10 x level, level + 200), not level + 100. The model applied
one technology's bounds to the crop: a crop below 22 kha could grow by 100 kha (BARL in PL340000 ended at that bound,
15 -> 155 kha, in the Green Deal 2030 run runs/full_gd_buf.pkl). Fixed: model_activity_classes.csv carries CAPRI's
number of technologies (checked by build_code_lists against p_technFact); the bounds are their sums. The mix columns'
per-technology bounds (T1 and T2 each within its own range) are not rows of the model (S1_MIX_COLUMNS.md).

- **Effect:** small crops' upper bound under large shocks
- **In 9t:** –
- **Status:** fixed (13 November 2026); in the run with K132 and K133 only (runs/full_gd_fall.pkl) BARL in PL340000 still
  ended at 10 x its level (155 kha), whose bound is now 215.5 kha

<a id="k135"></a>
### K135: The Green Deal targets of Portugal and Luxembourg not CAPRI's (found 13 November 2026)

CAPRI maps the target files' Eurostat codes to its member states with two sets, geo_to_ms_landscape
(pol_input/greendeal/load_landscape_targets.gms) and geo_to_ms (load_organic_targets.gms), and a region takes the sum
over the codes mapped to its member state (p_setAsideTarget(ms), p_organicAreaTarget(ms), p_organicAreaTargetCrops(ms,
ngrp)), then the member state's value by map_rr. Neither set maps LU or PT, although landscape_targets.gdx,
organic_targets.gdx and organic_targets_uaa.gdx hold values for both. So in CAPRI Luxembourg (BL400000) takes
Belgium's targets (BE -> BL000000), Portugal has neither a landscape nor an organic target, and neither do the regions
outside the EU. The model looked the targets up by the region's NUTS-0 country: Portugal took 3.08 landscape points
(PT200000's fallow 0.01 -> 2.94 kha, CAPRI 0.01 -> 0.01; CAPRI's Portuguese fallow and set-aside fall 22% and 21%) and
19.2 organic points of UAA, and Luxembourg its own values (the regions outside the EU take none of the Green Deal's
instruments in the model, SupplyModule.EU_POLICY_KEYS, so their lookup had no effect). An empty cell of a mapped code (Ireland's permanent crops, Malta's grassland) fell back
to the member state's UAA target, where CAPRI's sum gives 0. Fixed: CAPRI's two sets are data
(capri_data/scenarios/greendeal_group/greendeal_geo_to_ms.csv, parsed by build_greendeal_targets.py from the GMS
files) and `_capri_ms_targets` sums the codes mapped to the region's member state. That CAPRI leaves out Portugal and
Luxembourg looks like an omission in its sets rather than a choice (the GDX files carry their targets); the model
follows CAPRI's code.

- **Effect:** the Green Deal in Portugal and Luxembourg; Ireland's permanent crops and Malta's grassland under the
  organic target
- **In 9t:** –
- **Status:** fixed (13 November 2026)

<a id="k136"></a>
### K136: CAPRI's endogenous entitlement limit was not in the model (found 13 November 2026)

CAPRI's policy/def_endCut.gms (through scen/base_scenarios/CAP_2014_2020.gms, in the Green Deal reference and in the
scenario's base refpol_endotech_all_sup.gms alike) gives each region entitlements for the area payments (dp_bps,
Dpbps_SAPS, DpYOUNG, DpFIRHA, DpNATCO where the member state has a 2030 ceiling): Limit = the crops' trend levels
(DATA "trd"), Cut = the member state's ceiling CEILVAL x 1000 / its regions' Limit (EUR/ha). The supply model's
sumEntl_ and overShotEntl_ (supply_model.gms l. 1885-1892) and the objective's - overshoot x Cut (l. 4768) take the
payment away from every eligible hectare beyond the limit; entitlement trade (prem_entl_trade.gms) is off
(%entl_trade%, capmod/set_global_variables.gms l. 194). The dual's contribution D_sumEntl in CAPRI's dataOut is nonzero
in 85 regions and aggregates of the 2030 reference and in all 248 EU regions and aggregates of the Green Deal 2030
step, at about the payment per ha (NL -273, BL -231, DE -223, IR020000 -186.5 EUR/ha). The model pays every hectare
(fixed PRME per activity): its UAA grows +3.4% in the Green Deal (with the idled histosols, K137) against CAPRI's
+1.3%, which also eases the per-ha N-surplus target.

Ported (the project lead's choice, 13 November 2026: CAPRI's chain, not its results). tools/build/
build_cap14_entitlements.py takes CAPRI's tables (Annex II, the shares, the transfers, the coupled ceilings) from its
GAMS files and the trend levels from sim_ini_21730; capri_mod/supply/entitlements.py computes the 2030 ceilings as the
chain does, and the regional model has one overshoot column at the member state's cut and one row (the crop columns and
the idled histosols - overshoot <= the trend area). What the chain does, read in the code and confirmed by the
numbers:
  - no transfer from pillar 2 to pillar 1: its base, the pillar-2 ceilings of the years before the simulation year, is
    deleted by policy/del_policy.gms before the transfer file runs (CAP_2014_2020.gms l. 52 before l. 147);
  - 2030 is after the BPS years (2000-2029): def_policy.gms gives each scheme its last value, BPS from 2029 and the
    young-farmer, redistributive and natural-constraint payments from 2020, the last year of their tables. So in 2030
    the BPS ceiling is not reduced by those payments (France: cut 193.5 EUR/ha, 139.7 with the deduction);
  - the coupled ceilings are carried forward only from the base year 2017 (Poland's flax VCS of 2015 is not).
Checks (CAPRI's results, used as checks only): the 2030 ceilings of all 27 member states and 6 schemes equal the
reference dataOut's CEILVAL to 1e-12 million EUR; the cut equals the Green Deal step's D_sumEntl in 25 member states (EE
and UK, where CAPRI's area sits at the limit, have smaller duals). In a four-region Green Deal run the row binds with the
dual at the cut: IR020000 overshoot 83 kha, dual 186.55 (CAPRI -186.55); NL120000 52 kha, 272.64 (-272.64); PL340000
671 kha, 139.77 (-139.77, K139); FR210000 at the limit (dual 79.5; CAPRI's FR21 overshoots, -193.47).
The model keeps CAPRI's fixed premiums per activity otherwise (PRME): CAPRI's ceiling cuts of prmcut.gms (premiums scaled
down where a scheme's payments exceed its ceiling) are P2. NECR, which the model does not have (K138), is held at its
trend level.

- **Effect:** land expansion and the land market under shocks that raise land's value (the Green Deal); the base
  regions where the limit binds
- **In 9t:** –
- **Status:** fixed (13 November 2026). The full EU Green Deal run (runs/full_gd_k136.pkl, 19 iterations, every
  regional solve optimal): EU UAA +1.90% (K135 +3.36%, CAPRI +1.3%); the 35 activities' mean absolute gap to CAPRI's
  Green Deal step 3.6 points (K135 4.3), the producer prices' 2.7 (3.8). PL340000 (K139) unchanged. Since 13
  November (P2) only CAPRI's VCS and cotton schemes are taken out of the BPS ceiling (the CNDP are national money).
  The full EU Farm-to-Fork run with it (dev f5da6c7, 13 November 2026): converged in 14 iterations, 4,051 s, every
  regional solve optimal; the mean absolute deviation from JRC121368's 20 indicators 4.77 points (UAA +3.2%,
  JRC121368 +3%). Both runs are in the results store (ebc377a04811, 3c1dee09f16b)

<a id="k137"></a>
### K137: The reported UAA left out the idled histosols (found 13 November 2026)

The environmental table's arable land, grassland and uaa_total summed the crop activities only. The histosols the
regional model idles (CAPRI's IHISGR, IHISCR; capri-mod's histosol fallow columns) stay in their land type: in the
model's land rows (crops + idled area = the land type, CAPRI's LandBalNoSlak_) and in CAPRI's reporting (dataOut's
GRAS includes IHISGR, ARAC IHISCR, UAAR both; e_SURTOTHa divides by the land types). So the surplus per ha computed
from the table looked short of the Green Deal's -30% in 28 manure-heavy regions (IR020000 -26.8%, NL120000 -16.2%)
while the N-surplus row met it exactly: in IR020000 the row is surplus <= 0.7 x 176.36 kg N/ha x the land columns
(2674.8 kha), 330.2 kt N, the reported surplus, with 115 kha of idled histosol grassland in the land and not in the
table (checked by recording the row at the solution). The EU UAA of the Green Deal 2030 run grows +3.36% with the idled
histosols (1,721 kha; CAPRI 1,819 kha) against +2.30% without; CAPRI +1.3% (K136). Fixed: the idled area is counted in
the land type it belongs to (EnvironmentalModule, from the supply result's histosol_fallow).

- **Effect:** reporting: arable land, grassland and UAA, and every per-ha figure taken from them, wherever histosols
  are idled (the Green Deal, an emission tax)
- **In 9t:** –
- **Status:** fixed (13 November 2026)

<a id="k138"></a>
### K138: CAPRI's new energy crops (NECR) are not a model activity (found 13 November 2026)

CAPRI's crop activities (MCACT) include NECR, new energy crops (perennial biomass for energy). Its 2030 trend level is
251 kha in 108 EU regions (415 kha in 128 regions with the UK and the other regions outside the EU; sim_ini_21730
DATA "LEVL" "TRD"). The model has no NECR column, so that area does not
respond to prices or to the Green Deal. In the entitlement limit (K136) NECR is held at its trend level, which is the
same as leaving it out of both sides of sumEntl_.

- **Effect:** 251 kha of the EU's 2030 crop area (0.15% of the sum of CAPRI's EU crop activities) without a response
- **In 9t:** –
- **Status:** open: to be checked where the area sits in the model's land data, and added as an activity if it matters

<a id="k139"></a>
### K139: PL340000 converts all its forest to farmland in the Green Deal 2030 run (found 13 November 2026)

In the Green Deal 2030 runs PL340000's crop area grows +44.7% (full_gd_k135: 1,076 -> 1,557 kha), the largest
expansion of any region; CAPRI's falls 2% (1,075 -> 1,052 kha). In a four-region run with the entitlement limit (K136)
it still grows to 1,546 kha (overshoot 671 kha at the cut of 139.77 EUR/ha): the land market takes the whole forest
(FORE 614 -> 0 kha) into arable land (649 -> 790) and grassland (410 -> 939), and the land balances' duals are zero at
the solution. GRAE (205 -> 703 kha), BARL (16 -> 212) and FALL (24 -> 197) take the land; in CAPRI they barely move. (The land
market's quadratic is not unusual there: smallest eigenvalue 1.5e-4, the median of the 250 regions 1.4e-4, land_market_2030_regions.csv.)

- **Effect:** PL340000's land use and supply in the Green Deal; part of the EU's UAA gap (K136)
- **In 9t:** –
- **Status:** open: to be traced (the land market's transformation costs at the solution against CAPRI's 2030 LUC)

### K140: the rural development port's open differences from CAPRI's 2030 reference (found 13 November 2026)

capri_mod/policy/rd.py ports extend_rd_baseline.gms and rd_logic.gms (P2c). At the trend levels its 2030 RD
declarations equal sim_ini's (all 2,607 ceilings and 3,658 rates), its declared premiums CAPRI's 2030 reference PRMD at
21,673 of 21,733 unit x activity x scheme records, and, with the cut and the entitlement weights killed as
CAP_2014_2020.gms l. 77 does, the effective premiums PRME at 19,812 of 20,098 records within 1e-4. The 286 others:

- **Praha (CZ010000), 60 records:** in CAPRI's simulation Praha takes the Czech rates of the agri-environment schemes
  (PRMD 49.889 for AE1, the member state's), while rd_logic at the trend levels gives it its own (398.7, as sim_ini
  has them): consistent with Praha's levels being zero in DATA "Y" when the simulation's chain runs; not established.
- **Ile-de-France (FR100000), 26 records:** its LFA ceiling is negative in the data (-0.00015 million EUR), so it has no
  cut of its own; CAPRI pays it the member state's reported cut, 0.634, not France's own 0.984 (the cut factors
  persist across prmcut's calls: not ported yet).
- **Sweden's DPRD_SeExte, 184 records (1.6%):** its technology factors (T2 +1/3, T1 -1/3) enter the cut through the
  technology shares (prmcut's p_technFactMod), which the check leaves at 50/50.
- 16 records just above 1e-4 (BG030000's AE6: 4.2292 against 4.2296).

- **Effect:** since P2 step 2 (13 November 2026, tools/build/build_price_trajectory_2030.py: the 2030 premiums from
  the ports in place of CAPRI's reference rows) these points are in the model's 2030 premiums: Praha's crop premiums
  2 to 18 times CAPRI's (11.7 of Czechia's 3,893 thousand ha), Ile-de-France's about 3% above, Sweden's fallow 4-9%
  above; elsewhere the ported premiums are CAPRI's within 1% (crops) and 1.5% (the livestock ratios)
- **In 9t:** –
- **Status:** open (the technology shares come with the integration, step <= 10 on the solved levels)

### K142: P2c, the BPS key: three points left in the MTR port (found 13 November 2026)

capri_mod/policy/mtr.py ports CAPRI's 2004-2013 regime as CAP_2014_2020.gms evaluates it for the BPS key
(mtr_until2013.gms executed on sim_ini_21730's time series, calc_mtr_top.gms, calc_mtr.gms, the policyIUV pass). With
it the BPS rates of 2030 (bps.py) are CAPRI's reference at every unit of Belgium, Greece, Spain, Italy, Portugal and
Ireland (within 3e-5), and of the flat-rate member states (2e-8). Three points are open:

1. Croatia: no unit has MTR payments in the port (no declaration of an MTR scheme; DPMTR's 40 million EUR of 2013 has
   no payments to scale), so implement_bps.gms would give it no BPS ceiling; CAPRI's reference has one. Where CAPRI's
   key for Croatia comes from was not found. bps.py takes the entitlements as the key of a member state none of whose
   units has one (a uniform IUV): for Croatia, one unit, CAPRI's rate whatever the key (exact). A departure where it
   acts, flagged.
2. NA: agenda.gms l. 1225 writes the sheep premium of 2002 as NA in every EU region ("treated as a missing value",
   policy.gms l. 25), and sim_ini_21730 holds those records. Reading them as GAMS records (def_policy.gms carries NA
   to 2030; policy.gms drops it; the member states take EU015000's 16.8 EUR) puts Spain, Italy, Portugal and Greece
   1-5% off CAPRI's reference, correlated with the units' sheep payments; taking them as absent (each member state's
   last rate before them: 26.98 EUR in Spain, 26 in France and Italy, 23 in Portugal, 20 in Greece) gives the
   reference exactly. The port takes them as absent; how CAPRI's run loses them is not traced. CAPRI's results used
   to choose between two readings of its data, not to fit a value.
3. France: the mainland units within 0.6% of the reference, Corsica (FR830000, its own BPS region, so its rate is its
   key share of the French ceiling) 5% low: its key short by about 1 million EUR of 19.6. Not found: the coupling
   degree of 2030 is nil in CAPRI's chain (the loop stops at %endofMTR%; with 2020's degrees all member states move
   further off), the modification factors do not change a unit's total, the 2030 cut of DPFRMS improves the match.

- **Effect:** the BPS rates of Croatia (CAPRI's), of France's units (Corsica 5% low, the others within 0.6%)
- **In 9t:** -
- **Status:** open

### K141: CAPRI bug: CAPRI's BPS convergence takes the leftover overshoot off in the wrong unit (found 13 November 2026)

implement_bps.gms l. 309 recomputes the BPS region's overshoot after the 30% rule (million EUR: entitlements in 1000
ha x EUR/ha / 1000) and takes it off the units below target as p_bps_envelopeOvershoot / sum of their entitlements,
1000 ha: an EUR/ha change 1000 times too small. Where the 30% rule binds (BL, EL, France's rbps2, IT, PT, SI) the
envelope stays overshot by what the rule kept; the year's prmcut then cuts every unit's BPS to the member state's
ceiling by the same factor, so the total is right but the low units keep a larger share than the rule intends.
capri_mod/policy/bps.py keeps CAPRI's arithmetic (CAPRI's 2030 reference is computed with it); a test
(test_bps.py) fixes it.

- **Effect:** the BPS distribution within those member states' BPS regions, as in CAPRI
- **In 9t:** -
- **Status:** closed (13 November 2026): a CAPRI bug, kept as CAPRI computes it by the project lead's decision ("keep
  capri but sign it as capri bug"); correcting it (x 1000) would be a departure, not offered as a setting

<a id="k143"></a>
### K143: A regional premium factor on animals compounded at every solve (found and fixed 13 November 2026)

The supply model applies premium_factor_regional {region: {activity: factor}} for a solve: crops on cap_premium,
animals on livestock_premium_coef. The solve restores what it changed in its data (RegionalSupplyModel._solve_once,
_RESTORABLE) but not livestock_premium_coef, so an animal's premium was multiplied by its factor again at every later
solve of the same regional model. Found with P2's premium response (capri_mod/policy/premium_response.py): factors of
1.5-1.7 on Denmark's and Italy's pigs, poultry and calves (a livestock-unit scheme's fixed budget over fewer heads)
grew geometrically and the mini-EU Farm-to-Fork run diverged (step changes above 100% at step 20). Fixed:
livestock_premium_coef restored with the others; test_capri.py::test_regional_premium_factors_do_not_compound (fails
without the fix)

- **Effect:** every run with an animal premium factor different from 1 before 13 November 2026: the premium response's
  first runs (13 November, not kept), tools/run/run_vcs_2030.py's coupled-support experiment (the animals' coupled
  support removed by a factor below 1, compounded towards 0 over the outer iterations: the animals' response was
  overstated; "test done: MAD 1.23 points" in COUPLING_SPRINTS to be redone), and scenarios with Pillar II budget
  changes (none of the shipped scenarios has them). Farm-to-Fork and Green Deal runs without the premium response
  had no factor and are not affected
- **In 9t:** -
- **Status:** fixed

<a id="k144"></a>
### K144: CAPRI bug: Norway's output payments pay nothing in the simulation year (found 13 November 2026)

policy/norw_pol.gms declares Norway's price support per t of output (DPNOR6, amber box, and DPNOR7, blue box; APPTYPE
noPriceSup). policy.gms pays it per activity unit as the yield x 0.001 x the rate, with the yields of
p_dataCopy(rsNorw, pppact, o, %1), which l. 97 copies from DATA(rsNorw, pppact, o, %1): the year's own column
("2030"), while CAPMOD's DATA holds the simulation year at "Y" (l. 92-94 copy the EU's yields from "Y"). So the
weight is 0 and the output payments are not in the premiums: CAPRI's 2030 reference PRME of every Norwegian unit and
production activity equals the direct payments (DPNOR1-DPNOR5) alone (capri_mod/policy/norway.py, test_norway.py: 108
cells exact). With the yields at "Y" Norway's dairy cows would get about 40% more (NO020000: 1,798-2,032 against
1,277 EUR per head), bulls 2.5-3.3 times as much, fattening pigs 3.8 times.

- **Effect:** Norway's premiums per activity in the simulation year, as in CAPRI
- **In 9t:** -
- **Status:** closed (13 November 2026): a CAPRI bug, kept as CAPRI computes it by the project lead's decision ("for
  the moment keep capri and sign the fact, like you did with k141"); reading the yields at "Y" would be a departure,
  not offered as a setting

### K145: The 2030 premium of wine was left at 2017 (found and fixed 13 November 2026)

tools/build/build_price_trajectory_2030.py writes the 2030 premiums per model region from CAPRI's 2030 PRME by
activity; the model's crops that carry another CAPRI code took it from a map that held only CORN -> MAIZ. The model's
wine activity (WINE, CAPRI's TWIN) therefore had no 2030 value in capri_cap_premium_2030.csv, and
capri_mod/projection/prices.py, which keeps the 2017 premium where 2030 has none, left the 2017 premium in the 2030
baseline at the 155 model regions where CAPRI's 2030 reference has one (Anatoliki Makedonia, EL110000: 637.7 EUR/ha kept against CAPRI's 2030 536.4,
419.95 in 2017 money). The map is now read from codes/model_activities.csv (the crops with a single CAPRI code:
CORN -> MAIZ, WINE -> TWIN).

- **Effect:** the 2030 wine premium falls to CAPRI's (in 2017 money); wine's 2030 levels and the regions' premium
  totals move with it
- **In 9t:** -
- **Status:** fixed (13 November 2026)

### K146: Switzerland's supply terms without its support per tonne (found and fixed 13 November 2026)

CAPRI's producer price is the market price times the producer price margin plus the support per tonne (PPri_,
arm/market_model.gms l. 3046-3060: PSEi + PSEd + AREP x (1 - DECP), fixed in a simulation), so a market price change
moves the producer price by (PPRI0 - support) x (ratio - 1), not PPRI0 x (ratio - 1). CAPRI's 2030 market data
(data_market_1730defaulta.csv, Data_CAL) carry support only for Switzerland: PSEd on 25 items (soya 234 EUR/t of a
516 producer price, pulses 160 of 614, sugar 113 of 573, beef 1,056 of 9,822; land 1,116 EUR/ha).
tools/build/build_noneu_market_supply_nq.py stated that none of the non-EU regions had any and wrote every term as
h x PPRI0 / INPE, so Switzerland's supply terms in 22 product prices (528 terms) were too large by PPRI0 /
(PPRI0 - PSEd): soya x1.83, pulses x1.35, sugar x1.25, sunflower and rape x1.17, beef x1.12, sheep and goat meat
x1.11, cereals x1.05-1.11. The rents (rent = producer price + PSEd: the change form drops it), raw milk (the dairy
block's own price; "for MILK there is no PPRI_ equ", l. 1094) and FEDE were right. Found in G3.0 (the inventory
refresh, docs/design/G3_MARKET_INVENTORY.md). The builder now writes support_y and h_ratio = h x (PPRI0 - support) /
INPE; CAPRI's p_elasSupp is still reproduced at the producer price (1.35e-14).

- **Effect:** Switzerland's market supply responds less to its product prices, as in CAPRI
- **In 9t:** -
- **Status:** fixed (13 November 2026); test_market_layers.py
  test_switzerlands_supply_terms_take_its_support_per_tonne_off_the_producer_price
