# Changelog

Recorded because the project's documentation had drifted in **both** directions:
claims of validation outlived their truth (the CAP policy layer was inert while
documented as validated), and claims of failure outlived their fix (the pulse
elasticity sign error and the DE60 non-convergence had both been resolved long
before anyone retired the note). Limitations should be re-measured, not
inherited.

Full provenance for every entry is in `capri_data/DATA_SOURCING_REGISTRY.json`.

---

## Validation status

| Component | Reference | Result |
|---|---|---|
| Market prices | CAPRI `PMRK` | 12/12 within 15% |
| 2030 projection | CAPRI 2030 reference run | correlation **+0.997**, total area within 2% |
| Carbon MACC | EcAMPA 2 (JRC 2016) | agrees at €50/t |
| Fertiliser | CAPRI `p_FertPerHa` | ~10% |
| Feed, monogastrics | CAPRI capreg reference | within ~5% |
| CAP budget | Real EU CAP | €54.0bn vs ~€55–58bn |
| Nitrogen balance | Eurostat gross N balance | median 54 vs ~45–50 kg N/ha |
| Water demand | Known EU irrigation geography | Mediterranean 79%, correct hotspots |
| Biofuel | Observed EU statistics | both within 10% |
| **Total cereal output** | **EU Agricultural Outlook 2017-2030 (DG AGRI/JRC)** | **297.2 Mt vs ~300 Mt — ratio 0.99** |
| **Farm-to-Fork scenarios** | Published CAPRI (JRC121368) | reported as a range; CAPRI's figure falls inside it for oilseeds |

---

## New capability

**Projection layer (`projection/`)** — versioned trajectory input with mandatory
provenance, weighted least-squares reconciliation, recursive loop, and baseline
drift reported separately from the policy increment. Driven by CAPRI's own
`captrd` baseline. Two correctness properties hold: a null trajectory reproduces
the comparative-static result **exactly**, and the projection reproduces CAPRI's
independent 2030 reference at +0.997.

This changes what the model *is*: it is no longer purely comparative-static, and
the README description was updated accordingly. Three caveats bound the claim —
validation covers a **single step** to 2030, not multi-period recursion; only
**perennial areas** are carried between periods, so herds are re-optimised each
period and livestock adjustment speed is overstated; and the trajectory is
**exogenous**, adopted rather than generated.

**Nitrogen intensity margin (`supply/intensity.py`)** — N per hectare is now a
decision variable with a Mitscherlich yield response, normalised so the base
year is reproduced exactly. Without it a nitrogen constraint could only cut
*area*, overstating the response roughly tenfold.

**Farm-to-Fork instruments** — all four CAPRI targets are now representable:
landscape elements (a fallow floor, as `landscape.gms` does it), organic area
share (I/O adjustment, as `organic_io.gms` does it), the tiered nutrient-surplus
rule, and the pesticide yield-loss channel.

**Base-year reconciliation (`data/reconcile_base.py`)** — reproduces CAPRI's
`coco`/`capreg` step: weighted least-squares projection onto accounting
identities, the same Highest Posterior Density family CAPRI uses. Reconciling
already-consistent data changes it by 9.09e-13 (machine precision), the gate that
catches a reconciler which rewrites rather than reconciles.

Tested against the three area vintages in `capri_data/archive/` — a Eurostat-derived
matrix (107,828 kha), COCO-reconciled (125,775), CAPRI final (144,719). It closes
**32%** of the distance. **That test is weaker than it first appears**: the
"Eurostat" file is already mapped to CAPRI activity codes, and 35% of its values
carry repeating decimals, so it is share-allocated rather than measured regional
data. It measures recovery of regional detail from allocated totals, *not* whether
raw Eurostat can be turned into CAPRI data — which remains untested. **The residual is definitional, not a
reconciliation failure**: GRAS alone is 18,393 kha of it (Eurostat 13,640 vs CAPRI
44,819 — different grassland definitions), OLIV 1,884 vs 4,808, and CORN runs the
other way because Eurostat's maize includes silage.

That splits a problem previously treated as one: **reconciliation** (making numbers
internally consistent) is now solved and ours; **concordance** (mapping external
statistical categories onto CAPRI activities) is separate and, on this evidence,
larger. Conflating them is why "just use Eurostat" looks easier than it is.

**Yield-price response** — yields now move with own price, as CAPRI's stage-one
decision does (*"updated depending on price changes against the baseline"*,
documentation ch. 5). Previously a price shock moved area only, a pure extensive
margin that understated supply response. `YIELD_PRICE_ELASTICITY = 0.15`, a
short-run literature value, exposed rather than buried. At an unchanged price the
factor is exactly 1.0, so base fidelity is untouched (0.47%, 248/248 converge).

**NUTS version correspondence** (`capri_data/shared/nuts_version_correspondence.json`)
— 184 CAPRI region codes mapped across NUTS scheme versions, extracted from
`build_general_set_structure.gms`. CAPRI's result files use *old numeric* codes
for member states that changed scheme (`IT110000` where NUTS-2016 says `ITC1`), so
every Italian validation lookup had been matching **zero** regions and silently
returning nothing. Spain was unaffected because its codes are numeric in both
schemes — which is why the gap survived until Italy was tried. Not in the
published documentation: the Annex Code Lists map items, not regions.

**Water demand (`water/`)** and **farm-income distribution (`income/`)**.

---

## Defects fixed

Every one was surfaced by an **external reference**, not by an internal
consistency check. That is the single most useful lesson in this log.

| Defect | Effect |
|---|---|
| **CAP support double-counted** | The calibrated net revenue already contained `cap_premium`, and the solve *added* the absolute payment on top — ~29% supply inflation in **every scenario ever run**. The same inflation sat in the baseline, so scenario-vs-baseline comparisons were measuring the double-count rather than the policy. Adders now pass as a delta, ending the double-counting |
| All policy instruments inert | Scenarios returned baseline numbers while reporting success — four separate causes |
| Nitrogen balance meaningless | Median −170,196 kg N/ha, from a grass fresh-matter artifact and a manure-N scale error |
| Permanent crops destroyed | Olives 78% error in every base solve; invisible to a fidelity measure that only checked annual crops |
| **Arable land bound cut the base year** | **Base fidelity 11.28% → 0.47%.** ARABLE land and crop areas disagreed in 54 of 248 regions by 9,960 kha (LT02 12.7x); the solver shed 9,976 kha, losing most cereals in those regions. Not solver noise — a data conflict, and fixable |
| Grain maize silently excluded | `MAIZ` (not an activity) listed instead of `CORN` in three modules — fertiliser group, pesticide target, abatement N₂O |
| **Grass unit fixed at source** | CAPRI reports grass yield as fresh matter in kg/ha; every other crop is t/ha. The raw value caused the same defect **five times** — 99.3% of nitrogen uptake, 99.9% of gross margin, 4.5 bn kt of grass output — each patched where it surfaced. Now converted once at load time, five patches removed, results identical. Exposed a sixth dependency: the fertiliser module's plausibility guard had been silently dropping grass *because* of the bug |
| **Livestock output was not a product** | `gross_output` used CAPRI's `YILD`, which for breeding and suckler activities measures offspring or liveweight, not a marketed product — one region reported 3.9 billion tonnes of pig. Now built from CAPRI's final-product items (milk, beef, pork, poultry, eggs, sheep and goat) for all 27 member states plus Norway; EU totals match real 2017 production within 0.94–1.08. Building it hit five traps, including a region pattern of mine that silently dropped every letter-coded region |
| **Ireland: no livestock, and placeholder land** | Herds were absent (CAPRI's two NUTS-2013 Irish regions don't map onto NUTS-2016's three), and adding them exposed that Irish crop areas, yields and costs were synthetic placeholders — maize, sunflower and sugar beet Ireland doesn't grow, on 15% of its real land. Rebuilt from CAPRI using a Eurostat table that lists Irish cattle under both region schemes, which fixes the split exactly. EU livestock output now equals CAPRI's EU27 total to the tonne. Irish grass yield is still a placeholder |
| **Base data rebuilt from CAPRI for every region** | It had been a template overwritten by CAPRI only where a code matched: ~3.5 Mha of placeholder crops, 100 of 248 regions with no CAPRI source (all of France, Greece, Sweden, much of Italy and Poland), and two whole categories missing — fodder on arable land (14.3 Mha) and fallow (5.5 Mha). Poland was counted twice (21 rows for 17 regions); Ceuta, Melilla and Brussels held 1.6 Mha of phantom farmland. Now one tool builds all 248 regions; every country within 0.93–1.03 of CAPRI's own agricultural area. EU wheat production 113.6 → 126.6 Mt (real ~130); grain maize 91.7 → 66.5 Mt (real ~65) |
| **Table olives mapped, grass yield resolved** | CAPRI separates olives for oil from table olives (307 kha); both are olive groves, so EU olive area now reads 5,010 kha against a real ~5,000. Separately, the model's grass yield had no verified basis against CAPRI — because CAPRI has none: its grass price is a dummy 1000 EUR/t and its grass "yield" equals revenue, so it is a value construct. The model's 4.64 t DM/ha median is plausible on its own terms |
| **Paddy rice added** | A documented CAPRI activity the model lacked: 427 kha EU-wide, concentrated in Lombardy, Piedmont and Andalucía. Now the 30th crop activity |
| **Livestock intensity margin** | CAPRI carries every dairy herd as a low- and a high-intensity variant (`DCOL`/`DCOH`) so it can extensify under a nutrient target instead of only shrinking. In the base year the split is mechanical — half the herd each, yields averaging to the one already used — so the value is the response channel. Bounds extracted per region (EU median 5.39 and 8.99 t milk/head); a nitrogen ceiling moves the dairy yield toward the low bound, carrying revenue and reported output with it. In `NL11` under a 100 kg N/ha ceiling the herd falls 1.6% while milk output falls 10.5%. Inert when no ceiling binds; base fidelity and all anchors unchanged |
| **Oilseed and permanent-crop overshoot documented** | Cereals land at 0.93× CAPRI but oilseeds and permanent crops at 1.40× and 1.39×. Six explanations tested and ruled out by measurement (yield channel, land pinning, price feedback, elasticities, uniform organic shock, catch crops). The residual is concentrated in vegetables (−9.3%), which CAPRI reports merged with permanent crops — so its reference cannot be split to check them. Recorded as a bounded limitation rather than left as an open question |
| **Rice given a market, and the last four activities mapped** | Paddy rice competed for land but had no market balance; CAPRI's own world price (411.42 EUR/t) and FAO data for 24 regions were already held, so `PARI` is now a market commodity — world rice balances at 386,384 kt with the real producers. The four activities left unmapped (other marketable crops, other industrial, nursery, flowers — 1,721 kha) are now activities in their own right. **The model's agricultural area now equals CAPRI's exactly: 166,690 kha, 100.0%.** The manifest caught the row-count changes from adding rice before anything absorbed them |
| **Five inputs were undeclared in both manifests** | `livestock_output_coef`, `livestock_revenue_coef`, `nutrients_regional`, `organic_yield_gap` and `capri_own_price_elasticities` were loaded and used but declared nowhere, so the validator's shape check skipped them — a truncated livestock coefficient file would have passed silently. Found while updating the README, whose claim that "every input is declared" turned out to be false. Now declared in both manifests with shapes; validator coverage 25 → 30 files, verified by truncating a file to 99 rows and confirming it is caught |
| **Wine's regional price was silently dropped** | The price file uses CAPRI's codes (`TWIN` for wine, `TEXT` for fibre, `OFAR` for fodder), so five crops fell back to the EU-wide price — the same silent-drop family as MAIZ/CORN. Wine was priced at 95.5 EUR/t against CAPRI's median 1,362, leaving it on a **negative margin** (Spain −712, Aquitaine −1,413 EUR/ha) where real margins are 2,000–6,000. Found by decomposing the permanent-crop group: olives (4.5 Mha) already matched CAPRI at −0.10%, and the contraction was wine alone. Fixed: wine −11.3% → −2.6%, permanent crops −4.1% → −1.7% area |
| **CAPRI's area/yield decomposition obtained** | The published report (user-supplied PDF; the online fetch truncated before the results) gives what every comparison here lacked: cereals area −4% and yields −11% for a −15% supply fall; vegetables and permanent crops **area stable at +0.1%** with the whole −12% coming from yields. Against this: our cereals are close (−13.9% production, −2.4% area), but our permanent crops lose 4.9% of area where CAPRI loses none. The open question is now why permanent-crop area moves at all. The annex also independently confirms the organic yield-gap table and PESETA region membership already wired in |
| **Organic target applied at double CAPRI's shock** | The 25% organic target was applied as if every hectare converted. CAPRI converts the *distance* to the target — `p_organicAreaTarget = 0.25 - 0.10` in its own code, a 15-point shock. Corrected: cereals now −13.8% against CAPRI's −15%, and our cereal *yield* effect is −11.6% against CAPRI's published −11%. The remaining overshoot (oilseeds 1.40×, permanents 1.44×) is now on the area side |
| **Yield shocks never reached reported output** | The pesticide yield loss and organic yield gap were applied to net revenue only, not to yields, so production was computed on unshocked yields. This **reverses** the long-standing "cereals under-respond" finding: CAPRI's −15% cereal figure decomposes into −11% yield and −4% area, and our *area* falls 5.9% — more than CAPRI's. We had been comparing our area against CAPRI's production, the fifth apples-to-oranges error in this project. Fixed, plus CAPRI's 0.45 double-counting factor (previously tested and rejected on the wrong metric): cereals now −13.5% against −15% |
| **Two "Validated" claims corrected by audit** | After two investigations found stale summary figures rather than live defects, the standing claims were re-checked. "Crop elasticities match CAPRI within ~10%" was false for annuals (barley 0.51×, rape 0.14×) — it had been measured against literature targets, not CAPRI's values. "N excretion matches CAPRI `MANN` within ~12%" is withdrawn rather than restated: it predates the poultry unit conversion and a re-measurement runs into the same unit ambiguity that has produced two false readings. What *is* verified is the absolute check — manure nitrogen 7.5 Mt against a real EU ~7 |
| **Scenario implementation verified against the published report** | JRC121368 fetched directly (it is public; no CAPRI installation needed). Every implemented channel matches its specification: −50% plant-protection expenditure, +50% other costs, 10% yield loss, and for organic zero fertiliser/pesticides, +100% other costs, FADN yield gaps. The 10% yield loss traces to Sánchez et al. (2019) — CAPRI's own reading of the literature, not a tunable parameter |
| **World production: 6.7% allocated, not 23.4%** | A figure quoted throughout this project was 3.5× too pessimistic — it predated the FAO_agg extension being counted against both real sources. 26 of 29 trade regions carry real data; of the rest, 5.9 points are `ROW` (a residual by construction), leaving Iran and Saudi Arabia at 0.8% combined. Also removed a seeded ±8% noise multiplier on the allocated regions: reproducible, but invented variation presented as data. All anchors unchanged |
| **A safety rail overrode policy constraints** | A post-solve clamp caps each activity at a multiple of its base; running after the optimisation, it pushed solutions off constraints the solver had satisfied. A 10% set-aside requirement was cut to 1.5× base (floor 56.2 kha → reported 24.7). Price shocks only arise from the second iteration, so single-iteration runs looked right while **every converged policy run quietly relaxed its land constraints** — EU-wide, set-aside delivered 9.9 Mha against 15.6 required. Constraints now win over the rail. It did *not* change the policy headline, so it was not the cause of the under-response |
| **CAPRI's own elasticities for all 26 countries** | Permanent crops, horticulture and livestock vary only 1.0–1.6× across member states (tomatoes 1.0×, pork 1.1×) — genuinely EU-wide constants. Annual crops vary by up to two orders of magnitude (barley 9.9×, rape 16×, other cereals 56×, sunflower 141×), so per-country targets are mandatory. Wheat is absent from the parameter entirely, and an earlier "CAPRI 2.00" for wheat in this project was an assumption of mine, not a CAPRI value |
| **Plant-protection costs from 2 countries, not 27** | Shares derived from Spain and Italy alone were understated ~3x (wheat 5.7% → 17.6%). The check is decisive: applied to the base year the old shares imply €3.6bn of EU pesticide spending against a real €11–12bn market; the new ones imply €10.8bn. Correcting it alone made scenarios *weaker* — a bigger share means banning half of it saves more — which exposed the missing other half below |
| **CAPRI's +50% other-cost shock was switched off** | `PESTICIDE_OTHER_COST_RISE` was zero, for a documented and sound reason: the model had no equivalent of CAPRI's `INPO` category, and using the plant-protection share instead cancels the saving exactly. That precondition changed once `OTHER_COST_SHARE` was derived from `INPO` across all 27 dumps; restored to CAPRI's 0.50. French wheat margin −13.6%, rape −31.6% at the 50% target |
| **Farm-to-Fork figures were a 30-region subset** | Every F2F number reported here had been computed on the first 30 regions in index order — all German and Austrian, containing almost no permanent crops. EU-wide over all 248 regions the model under-responds: cereals 0.44x of CAPRI, oilseeds 0.73x, permanent crops 0.40x, where the subset showed 1.22x, 1.25x and 0.72x. The claim "all three within ±25%" was false. Same failure as `max_outer_iter=1`: a convenience setting became a published result. Comparison now lives in `tools/run_policy_comparison.py`, EU-wide and converged by default |
| **Market module vectorised** | 2.3 million scalar pandas lookups per run, 137 of every 140 seconds. Vectorised with identical results (anchors unchanged, prices still 12/12): a converged 10-region run fell from 59s to 19s, and a full EU two-scenario comparison now takes 9 minutes — so there is no longer a reason to use a subset |
| **Organic yield gaps from CAPRI's own FADN data** | The flat 20% gap is replaced by CAPRI's estimates by macro-region and crop group (JRC Seville, SUPREMA project), which it loads from an external file rather than hard-coding: Southern Europe fruits 22.5% and olives 11.6%, Central Europe fruits 51.3% and cereals 42.9%. With this and the cost-channel fix, all three crop groups land within 25% of published CAPRI (cereals 1.22x, oilseeds 1.25x, permanents 0.72x, from 0.45x) |
| **Farm-to-Fork cost channels were wrong** | CAPRI's pesticide and organic scenarios raise the *other inputs* cost category by 50% and 100%; this model applied that rise to the plant-protection share, where it cancelled the expenditure saving exactly and left the cost channel a no-op. Organic used a flat 15% premium where CAPRI doubles other inputs and removes fertiliser and plant protection. Other inputs are 48% of cost for table grapes against 9% for wheat, so the shock should bite ~4x harder on permanents. Fixed from CAPRI's own cost structure across all 27 countries: oilseeds now match exactly (1.00x, was 0.87x), permanent crops 0.45x → 0.58x |
| **Permanent-crop policy gap localised** | Running the four Farm-to-Fork instruments separately shows no channel is missing — each is about a third as strong as CAPRI's on permanent crops. Points at three measurable parameters rather than a structural unknown |
| **Farm income was not a margin** | Livestock revenue came from `YILD` (not a marketed product for breeding and suckler activities), and `gross_margin` reported the PMP *calibration* terms rather than the margin — 55,531,046 against an actual 428,136 thousand EUR for one region. Also found: CAPRI's dummy grass price of exactly 1000 EUR/t (grass isn't traded) had been copied in, making grass the largest item in every regional margin. Income now responds: organic 25% costs −10.8% of income, the nutrient rule −5.3%, where all instruments previously read ~−0.1% |
| **Poultry counted in the wrong unit** | CAPRI reports poultry in million head, everything else in thousand; per-head coefficients understated poultry manure, feed and emissions a thousandfold. Converted at load |
| **Nitrogen balance had two errors that cancelled** | Manure was counted twice on the input side, and fodder crops were credited with ~double the nitrogen they remove (fresh-matter yields against a dry-matter coefficient). Together they produced a plausible-looking 54 kg N/ha. Mineral nitrogen now comes from CAPRI's own NMIN per region and crop: mineral 10.2 Mt (real ~10.8), manure 7.2 (real ~7), surplus 44.5 kg N/ha (real ~46) |
| **Poultry head counts in mixed units** *(found, not fixed)* | Most regions in CAPRI's million head, three (Lombardy, Campania, Helsinki) in thousands. Output unaffected; effect on nitrogen excretion and feed not yet measured |
| **Solve state leaked between runs** | The restore block *enumerated* fields; the list fell behind twice (`nutrient_coefs`, then `yields`). Altered values persisted into later solves, so results depended on what ran before them. Now snapshots every restorable attribute |
| Permanent-crop elasticities inverted | 10× *less* elastic than annuals, where CAPRI has them 2.47× *more* |
| Livestock yields unit-inconsistent | ~56 regions in tonnes, ~192 in kg; drove the MACC 2–3× too high |
| Consumption fabricated | A clamp invented supply where exports exceeded production |
| Set-aside mapped to the wrong instrument | Modelled as an arable cut; CAPRI uses a fallow floor |
| Market price test asserting stale values | Failed for the life of the project against deliberately-corrected data |
| Hard-coded 2017 paths | Re-basing would have silently fallen back to literature defaults |
| Organic target missing | Only a payment *rate* existed, not an area *target* |

---

## Farm-to-Fork comparison (JRC121368)

**Now a single estimate, not a range.** The plant-protection cost was derived
from CAPRI data (see below), which removed the reason for reporting bounds.

| | CAPRI-mod | CAPRI published (JRC121368) |
|---|---|---|
| Cereals | −18.5% | −15% |
| Oilseeds | −12.3% | −15% |
| Permanent / fruit & veg | −9.4% | −12% |

Oilseeds (1.07x) and permanent crops (0.86x) are close. **Cereals still
**All three land within ±25% of CAPRI, with errors in both directions** —
cereals 1.24x over, oilseeds 0.86x and permanent crops 0.78x under. Errors that
do not share a sign argue against a systematic bias.

A large part of the previously-reported cereals overshoot was **a measurement
error of mine, not a model defect**: every comparison had been run with
`max_outer_iter=1`, which executes one supply–market pass and so suppresses the
price feedback. When EU cereal supply falls, prices rise and cushion the area
response; CAPRI's published results include that, ours did not. Running to
convergence moved cereals from −22.6% to −18.5%, closing roughly half the gap.

A convenience setting chosen for speed while iterating became a published
result — the same class of mistake as the stale documentation found elsewhere
here: correct in its moment, wrong once the context changed.

**Fixed at the cause, not the symptom.** The old code printed the
non-convergence warning only when `verbose=True`, so every comparison — all run
with `verbose=False` — failed in silence. A non-converged run now always raises
a `RuntimeWarning` and records `metadata["outer_converged"] = False`, and
`test_unconverged_run_warns_and_is_recorded` pins both that it fires when it
should and stays quiet when it shouldn't.

**The pesticide cost is CAPRI-derived, not assumed.** Built as
`PESTOTAL (g a.i./ha, capreg) / 1000 x UVAB.PLAP (EUR/kg, coco)`. Two unit checks
were run rather than assumed: summing PESTOTAL x area over Spain gives 89,888 t
against a national quantity of 83,104 t (within 8%, fixing the unit as grams per
hectare), and `UVAB x NETF` reproduces `EAAB` exactly at EUR 1,110.7m — which is
Spain's real annual pesticide spend.

**Confirmed independently on a second country.** Both checks were re-run from
scratch on Italy and passed *better*: reconciliation within 2% (against Spain's
8%), and `UVAB x NETF` matching `EAAB` to the decimal (947.6 vs 947.59 m EUR).
Two countries agreeing on the unit interpretation is far stronger than one.

**Country variation is real**, which is why one country was not enough: Italian
costs run a median 1.15x Spanish, but from 0.95x for maize to ~1.7x for olives,
citrus and apples. Mediterranean permanent crops are where the two disagree most.
Shares are now the median across both countries.

---

## Known assumptions carrying weight

- **`PPP_COST_SHARE`** — now **CAPRI-derived** (from `PESTOTAL` x `UVAB.PLAP`,
  two member states, units verified independently in each), no longer assumed.
  The residual uncertainty is country coverage: ES and IT differ by a median
  1.15x, and by ~1.7x for Mediterranean permanent crops.
- **Permanent-crop elasticities** — CAPRI's *relative* structure (2.47× annuals),
  not its absolute levels, which are member-state market elasticities rather than
  regional PMP targets.
- **Organic yield gap 20%, cost premium 15%** — literature (Seufert 2012, Ponisio 2015).
- **Mitscherlich curvature k = 3.0** — agronomic literature; not tuned to fit CAPRI.

---

## Documentation coverage check

`tools/check_doc_coverage.py` asserts that every registry entry recorded as a new
capability or fixed bug is mentioned in a user-facing document. It exists because
the same failure recurred **five times**: the work went into the registry and the
README lagged, caught each time by a human asking rather than by anything
mechanical.

Its first tightened run found a real gap — the CAP double-counting bug, one of the
most significant defects in this log, was absent from both the README and the
CHANGELOG.

A first version was too loose to be useful: it matched substrings, so a
deliberately-undocumented probe entry *passed* because "deliberate" occurs inside
"deliberately". A checker that cannot fail is worse than none. It now matches on
word boundaries and requires either the full entry key, a file path the entry
names, or two distinctive words in the same document — and is verified to fail on
a probe.

## Regression anchors

`capri_data/validation/REGRESSION_ANCHORS.json` + `tools/check_regression.py`.

A machine-checkable snapshot of the numbers that **external references**
validated. It reports *which validation broke*, not merely that a number moved —
each anchor names the reference it was checked against, so a failure points at a
source you can go and re-read.

```bash
python tools/check_regression.py            # exit 1 on breach
python tools/check_regression.py --update   # accept an intended change
```

Eight cheap anchors run every time (regions, convergence, base fidelity, olive
fidelity, N surplus, world balance, price reproduction, CAP budget); two
expensive ones (MACC, projection correlation) are recorded but checked on demand.

Two design points worth keeping:

- **Olives have their own anchor.** The aggregate base-fidelity measure looks
  only at annual crops and did not see the permanent-crop collapse. An anchor
  that shares a blind spot with the bug it should catch is worthless.
- **`--update` is how an intended change is accepted, not how a failure is
  silenced.** Verified to exit 1 on a breach and 0 when clean, so it is usable
  in CI.

Run it before and after any base-year re-base — that is the situation this
exists for.

---

## Still open

- **Cereals sit 1.24x above CAPRI's published figure** (−18.5% against −15%),
  within the uncertainty of CAPRI's own numbers — JRC121368 states its production
  impacts are likely overestimated, which would widen the gap, not close it.
- **Pesticide cost shares rest on two member states** (ES, IT), whose costs differ
  by a median 1.15x and by ~1.7x for Mediterranean permanent crops. A third
  country would narrow that.
- Phase 2 (base-year update) not started; the base year remains 2017.
