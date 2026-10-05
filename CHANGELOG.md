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
| **Fitness for use, in machine-readable form** | Every other data file records where an *input* came from; nothing recorded how far an *output* could be trusted except README prose. `FITNESS_FOR_USE.json` declares 19 outputs with a status (`validated`, `use_with_care`, `overstated`, `not_supported`), and `capri_mod/fitness.py` queries it with fallback from specific to general. An unrecorded key returns `unknown`, not `validated` — silence is not a clean bill of health. Writing it caught two stale README claims: farm income described as contaminated after being fixed, and permanent crops as under-responding when they now overshoot |
| **Why meat prices barely move: diagnosed** | Every region's price is the world price plus tariff, so an EU supply cut moves EU prices only as far as world prices. CAPRI gives each region its own producer price, with imports as imperfect substitutes (Armington). Design for adopting CAPRI's structure in `docs/ARMINGTON_MARKET.md` |
| **Ammonia: CAPRI's accounting replaces a proxy** | Ammonia was housing emissions plus a flat 10% for soils, so it could only follow herd numbers. It now uses CAPRI's own factors per region — the share of excreted nitrogen lost from housing, storage, spreading and grazing for each animal, and the share of mineral fertiliser nitrogen — so fertiliser cuts reduce ammonia too. Base totals within 6% of CAPRI's |
| **Surplus rule checked against CAPRI** | The model applies JRC121368's tiered nitrogen-surplus rule; the current CAPRI code applies a flat 50%. Applied mechanically, the tiered rule implies an EU cut of −37.5% and the flat one −50%, against the study's −33.5%, so the tiered rule (the study's) stays. It requires the densest regions to cut 76–88% of their surplus, which drives the pig overshoot |
| **Manure pool tested and set aside** | A national manure pool as in CAPRI clears, but only at prices of €58–98 per kg of N, because the regional nitrogen targets bite extremely hard in pig regions; outcomes were absurd, so it was reverted. Settling this needs CAPRI's own Farm-to-Fork scenario output |
| **Why pigs fall 22%: diagnosed** | Without the fodder equality, pig regions grew silage maize that was never fed, purely to absorb manure nitrogen — a loophole that had made pigs match CAPRI for the wrong reason. CAPRI's valve is manure trade through a national pool that must clear; that is the next module |
| **EU ration on by default; fodder balance as CAPRI's equality** | The feed ration is now on by default, as in CAPRI; Farm-to-Fork still runs in about 3 minutes, and the cereal price and production now match CAPRI's. The fodder balance enforces CAPRI's equality (production may not exceed use), so fodder areas follow herds. Open: pigs now fall 22% against CAPRI's 14.5% |
| **Land market on by default, as in CAPRI** | CAPRI's land-market terms are per hectare, the model's land in thousand hectares; with that factor the land-supply elasticities fall in CAPRI's range. The land market is now on by default, as CAPRI's is: two regions that had no feasible solution under Farm-to-Fork now solve properly, results move by about one point, and the full 2030 run takes about 3 minutes instead of 10–12 |
| **Licence changed to Apache-2.0** | The project is now licensed under the Apache License, Version 2.0 (previously MIT): `LICENSE` holds the full Apache 2.0 text, a `NOTICE` file carries the copyright line, and `pyproject.toml` declares `Apache-2.0` |
| **Land market: all regions, and the run-time result** | Split regions (Trento and others) now have land-market data too. With the land market on, the full 2030 Farm-to-Fork runs in about 2 minutes instead of 10–12, with no slow solves; results shift because land demands can be met by converting forest and other land. Default stays off until the land-use change is checked against CAPRI |
| **Land market (switch, off by default)** | Land-type areas are now variables in each regional problem when `use_land_market` is on, with CAPRI's land-market costs; the base is identical. In Epirus, Farm-to-Fork's fallow floor is now met by converting other land, without the slow solver path, and cereals are no longer wiped out |
| **CAPRI land-market data built** | CAPRI's land-market matrices for six land types (arable, grassland, permanent crops, forest, other land, artificial) and their base areas, for 202 regions, from the files supplied. Ready for land-use flexibility |
| **Why two regions are infeasible under Farm-to-Fork** | CAPRI's landscape floor applies to total agricultural area, but the model keeps each region's arable land fixed; in Trento and Epirus, almost all grassland, the floor exceeds all arable land. CAPRI makes land types variable and converts grassland or other land to arable, within its permanent-grassland rule. Design in `docs/LAND_USE_FLEXIBILITY.md` |
| **Run-time overhead removed, results identical** | Profiling showed most market time in single-cell pandas operations inside loops added this month, and much supply time in re-reading fixed data. Both rewritten with the same arithmetic on arrays and cached values; each change verified to give identical results (differences 0 and 6×10⁻¹⁵) |
| **Faster, exact regional solves** | Farm-to-Fork run time is dominated by regional solves falling back to a slow general solver. On feasible problems an exact least-distance solver now runs first: it matches the old fallback's result in 29 of 30 captured cases and finds a 3.5% better optimum in the 30th (where the old solver stopped short), in about 0.5 ms instead of 1 s. Two mountain regions turned out to be genuinely infeasible under Farm-to-Fork (landscape floor vs arable land) and are unchanged for now |
| **EU ration wired in (switch, off by default)** | The ration now feeds livestock feed costs, the fodder balance and EU feed demand when `use_ration` is on; the baseline is unchanged. Testing found that the 2030 projection did not pass the switch to its model (fixed) and that undamped rations made the outer loop oscillate (ration updates now damped like prices) |
| **Fodder balance: first Farm-to-Fork result** | With herds tied to fodder, ruminant herds fall more, toward CAPRI (dairy −8.8% vs −10%), and manure methane now matches CAPRI (−12.5% vs −12.2%). Fodder areas do not yet follow herds down, because the balance allows unused fodder; CAPRI's is an equality, which comes with the ration wiring |
| **Fodder balance in the supply model** | Herds are now tied to the fodder they eat, as in CAPRI: regional fodder use must be met by regional fodder production. It replaces an older roughage constraint that never bound (it allowed generous "buy-in"). The balance is exact at base and carries CAPRI's fodder value as its shadow price, so fodder area follows herds in both directions |
| **73 regions now get CAPRI's regional livestock data** | The NUTS correspondence did not map CAPRI's codes for all of France and several German, Bulgarian, Greek, Italian, Swedish, Norwegian and Polish regions, so they received national averages for revenue, manure and feed per head. Pairs were found by matching agricultural areas and confirmed on dairy herds (which caught one coincidental match in Italy and two others); all livestock coefficients and the ration data were rebuilt. Brittany's dairy manure, for instance, rises from 141 to 169 kg N per head |
| **Fodder balance designed** | CAPRI's fodder balance read (use = production net of on-farm losses) and its regional data located; the design (`docs/FODDER_BALANCE.md`) fits the calibrator's existing treatment of binding constraints. One data check remains: our base fodder areas are smaller than CAPRI's in some regions |
| **All CAPRI ration rules in; a missing fodder balance found** | The ration model now has all of CAPRI's share rules, including the data-driven fodder ones, and a fallback solver (no failures). Building it revealed that the supply model has no fodder balance: herds are not tied to the fodder they eat. That link comes before the ration is wired in |
| **CAPRI's feed-share rules in the ration model** | CAPRI's minimum and maximum feed shares turned out to be rules in its code rather than stored data; the fixed rules are now in the ration model. Dairy and bull rations now respond plausibly (cereals −2% instead of −52% to −77% for a 10% cereal-price rise); suckler cows and heifers wait for CAPRI's data-driven fibre rules |
| **CAPRI's feed-PMP terms adopted in the ration model** | CAPRI's calibrated ration slopes (`pmppar`, sign convention verified against base optimality) now drive the ration model; the base stays exact. Responses barely change, which shows the reconstruction was faithful and that CAPRI's restraint on cattle rations comes from its feed-share constraints — still to be obtained |
| **EU ration programme built (not yet wired)** | `capri_mod/feed/ration.py` implements CAPRI's feed PMP per region and animal; all 2,084 base rations are reproduced exactly. Without CAPRI's minimum and maximum feed shares, cattle rations react far too strongly to prices, so wiring waits for those bounds (`Chk_feeddataTOP*.gdx`) |
| **EU ration data built; impossible rice data removed** | `tools/build_feed_ration.py` builds base rations, nutrient requirements, contents and feed prices for every EU region and animal from CAPRI's 2017 results (235 regions, 2,084 entries, energy and protein closing exactly). `pari_activity.json` turned out to be an undeclared source extract no longer read at run time and was removed; La Rioja's rice (81 ha at an impossible 25.4 t/ha) was removed from the live tables |
| **EU tariffs set to CAPRI's** | EU tariffs now equal CAPRI's 2017 total protection on EU imports (ad valorem, specific duties and quota effects together). Several were far off — sheep meat 52% vs 0.1%, cheese 40% vs 6%, butter 82% vs 38%, whey 12% vs 66% — while beef was already close (65% vs 58%). The effect on Farm-to-Fork meat prices is tiny, which shows the meat-price gap comes from market structure, not tariff levels |
| **Loose ends closed** | Olive world price per tonne of olives from CAPRI's olive-oil price and EU oil yield (21.3%); whole milk powder mapped; other oilseeds confirmed to have no CAPRI world price; the sheep 'arbitrage' anomaly traced to a code collision (CAPRI's SHGM is the dairy-sheep activity), correcting an earlier explanation; German land rents now official Destatis 2016 values by federal state (mean €304/ha, was a uniform derived €172). The EU oilseed seed balances now use CAPRI's data (EU rapeseed crush within 1.3% of CAPRI's, was +10%), which also exposed and fixed a latent crushing bug: the EU base crush read a value that calibration later rescales |
| **Comparison with CAPRI: modules and coupling** | `docs/CAPRI_COMPARISON.md`: every capri-mod module against its CAPRI counterpart, a link-by-link coupling scorecard, the Farm-to-Fork validation read against it, and the remaining gaps in order of effect |
| **EU ration choice: design complete, data verified** | CAPRI's ration mechanism read in full: nutrient requirements per production day, feed PMP terms that make the observed ration optimal at base, assumed feed elasticities (cereals and fodder −10, protein −5, energy −0.5), requirements trimmed to the data at calibration, and links to mitigation options. The 2017 regional data close for all 4,518 region × animal cases (energy and protein to a median of 0.00%) |
| **Feed demand responds to feed prices outside the EU** | Non-EU feed demand for cereals and cakes now follows CAPRI's feed-price elasticities, own and cross. Under Farm-to-Fork the sunflower-cake price fall halves (−23% → −12%), the cereal price rise eases (+12.1% → +11.6%) and convergence returns to 7 iterations. The EU counterpart — CAPRI's ration choice in the supply models — is designed in `docs/FEED_RATION.md` |
| **Oilseed crushing (stage 3): cakes as feed, proxy removed** | Cake feed demand follows herds' protein-rich feed, and livestock protein-feed costs follow a cake price index weighted by CAPRI's EU feed use. The soybean-meal proxy price is gone. Under Farm-to-Fork cake prices fall as herds shrink; the size of the fall (sunflower cake −23%) shows that feed demand still lacks its own-price response, which is next |
| **Oilseed crushing (stage 2)** | Crushing runs inside the market in every region, as in CAPRI: crush responds to the crushing margin with CAPRI's calibrated response, oil and cake supply = crush × yields, crush is part of seed demand. Fixing the projection identity test also removed a pre-existing leak: the market's base tables are now restored at every baseline, so results no longer depend on a model's run history |
| **Six oil and cake markets added (crushing, stage 1)** | Rapeseed, sunflower and soybean oils and cakes are now market commodities (39 in total), with CAPRI's balances, world prices, trade, Armington, demand and tariff parameters; EU oil demand uses CAPRI's EU-specific elasticities. The base clears exactly at CAPRI's prices and all existing results are unchanged. EU supply is held at base until crushing (stage 2) makes it endogenous |
| **Trade table rebuilt on CAPRI's own trade partition** | The trade table double-counted EU trade (CAPRI reports the EU block under two codes), dropped eleven genuine trading regions as if they were reporting aggregates (including Uruguay–Paraguay, which supplies most EU soybean imports), merged another region into South Africa, and had no trade at all for sugar, wine, whey and sheep meat. CAPRI's trading regions were derived from its own numbers (they reproduce its world totals exactly for all 71 products) and the table rebuilt; EU imports now equal CAPRI's to the tonne (soybeans 14.6 Mt, was 26.4). Six oil and cake columns added for the crushing module |
| **World prices replaced with CAPRI's own** | The world price file differed from CAPRI's base-period world prices for most commodities, and its oilseed rows held cake prices (soybeans at a third of their value). Replaced from CAPRI's `FAO_agg` market data with an explicit code map; the reproduction anchor and test now read the file instead of hard-coding the old values. Base and Farm-to-Fork results unchanged (the model works on price ratios); correct levels are needed for crushing margins |
| **Oilseed crushing: base data from CAPRI's own market database** | Balances of the three seeds and their six oils and cakes for all 21 trade regions, from CAPRI's `FAO_agg` market data (base period); EU crush and yields derived (rapeseed 41.8% oil / 54.1% cake, sunflower 42.0 / 52.8, soybean 18.6 / 78.8). The crushing design now maps every coupling link the module creates |
| **Oilseed crushing designed** | CAPRI's crushing mechanism read from its market model (margin, crushing response, Leontief oil and cake output) and CAPRI's 2030 oil and cake balances identified; design in `docs/OILSEED_CRUSHING.md`. It will replace the soybean-meal proxy price. CAPRI's calibrated market elasticities (`results\arm\elas*.gdx`) requested |
| **Livestock unit audit: manure and feed per animal now match CAPRI** | Comparing EU totals per animal with CAPRI showed manure and feed per head had used CAPRI's per-unit values on census herds — bulls, heifers, calves and broilers carried 3–12× too little manure, pigs and sheep too much, nearly cancelling in the EU total. Rebuilt from CAPRI's 2017 totals as revenue already was. The nitrogen target now reaches beef and poultry: beef −10% (was −5%), poultry −8% (was −2%), manure methane −11.7% (CAPRI −12.2%). Simplification register added to the coupling review |
| **Feed demand follows herds** | Cereal feed demand in the market now follows herd sizes, at each cereal's feed share from CAPRI's 2030 balance — fewer animals, less feed demand. The cereal price rise under Farm-to-Fork falls from +13.8% to +10.2% (CAPRI +8%) and cereal production moves to 0.96× CAPRI |
| **Coupling review; prices now reach livestock** | A review of how the modules are coupled (`docs/MODULE_COUPLING_REVIEW.md`) found that market prices never reached livestock: the price signal was keyed by commodity and margins looked it up by activity. Fixed. The review also documents the open gaps — feed demand independent of herds (likely behind the cereal price overshoot), no oilseed crushing, side modules outside the loop |
| **Livestock respond to prices: pigs now match CAPRI** | Animals' price response was calibrated on an inflated revenue (price × yield, ~20× too high for pigs), damping every price and feed-cost change; it now uses CAPRI's market revenue per head, as the margins already did. A numerical floor that pinned poultry's curvature was relaxed. Feed costs now include soybean meal. Pigs −15.8% (CAPRI −14.5%), manure methane −10.6% (−12.2%). Livestock comparisons now use herd sizes (output is unverified for most animals) |
| **Fertiliser allocation, stage 2: fertiliser follows crop need** | Mineral fertiliser now covers what crops need beyond what manure supplies, with CAPRI's regional availability and its minimum-mineral floor (40% of an arable crop's need must be mineral) — so herds are a strong lever on the surplus where manure is saturated, a weak one where it is well used. Base year identical by construction, pinned by a new test. Fertiliser N₂O −32% (CAPRI −40%, was −28%); crops still match |
| **Fertiliser allocation, stage 1: manure trade** | CAPRI's fertiliser allocation read from its code and verified against its reference numbers; calibration data extracted (153 regions, 47 crops). Manure now moves between regions as in CAPRI (11% of EU manure N; Weser-Ems exports 31%), which brings regional surpluses closer to CAPRI's on every measure. Surplus anchor re-based with that evidence. Design for the remaining stages in `docs/FERTILISER_ALLOCATION.md` |
| **Organic land is fertiliser-free; poultry diagnosed** | Organic conversion now removes mineral nitrogen, not just its cost (CAPRI's `organic_minfert_redu.gms`): fertiliser N₂O −26% (CAPRI −40%). Poultry's non-response traced to its margin's unit chain, not the feed table, which matches CAPRI's per-bird figures |
| **Nitrogen balance aligned with CAPRI's reference run** | Using the full CAPRI 2030 reference results: the nitrogen target now starts from CAPRI's own baseline surplus per region, the balance no longer subtracts "animal products" (manure now counts in full), and deposition comes from CAPRI's regional values. Farm-to-Fork herds now nearly match CAPRI: dairy −9.3% (−10%), beef −12.8% (−14.5%), pigs −10.7% (−15.5%); methane and GHG move with them. Poultry, fertiliser N₂O and meat prices remain open |
| **Livestock fixes; gap narrowed down** | A post-solve "safety rail" overrode policy responses and corrupted shadow prices under the nitrogen target — skipped there now. Corrected the livestock-to-market codes (an earlier fix had used codes that don't exist here — beef came from bulls and calves only). Animal feed costs now follow cereal prices. EU herds still respond about half as much as CAPRI's; the cause is narrowed to the composition of the nitrogen balance, not prices |
| **CAPRI's fertiliser technologies; crops now match** | Fertiliser now falls as in CAPRI's code: efficiency technologies adopted under the nitrogen price, with CAPRI's own efficiency formula and cost terms, and no yield loss — replacing a yield-loss channel. A manure-application constraint (Nitrates Directive) stops regions keeping animals while abandoning fields. Farm-to-Fork 2030: cereals 0.97×, oilseeds 1.12×, vegetables and permanent crops 1.00× CAPRI. Remaining gap: herds respond about half as much as CAPRI's |
| **Nitrogen target: convergence, accounting and three bug fixes** | Farm-to-Fork now converges in 7–8 iterations (was not converging in 25): land and the nitrogen price are settled within each iteration. Fixed a fallback-solver crash, per-run resets that wiped other regions' land-market state, land expansion "diluting" the target (now a regional cap), and uptake accounted at base yields in both the constraint and the environmental report. N surplus −30.0% (CAPRI −33.5%), fertiliser N₂O −36.6% (−40.4%). Crops now carry too much of the adjustment: fertiliser falls through yield loss here, whereas CAPRI uses nitrogen mitigation technologies — the next change |
| **Environmental results restored; first Table 15 comparison** | Every run's environmental table had been empty: two bugs (an undefined name, a missing `@dataclass`) failed every region inside a loop that swallowed errors. Fixed and pinned by a test. Against CAPRI's Table 15: N surplus −29.8% (−33.5%), enteric methane −13.1% (−14.6%), GHG −12.4% (−14.8%); mineral fertiliser barely falls (N₂O −2% vs −40%) — next to reconnect |
| **Nitrogen target on the full balance; livestock reaches the market** | The nutrient target now binds the gross nitrogen balance, as JRC121368 specifies, instead of applied nitrogen — so manure counts and herds respond: Farm-to-Fork dairy −6.9% (CAPRI −10%), beef −12.7% (−14.5%), pigs −9.9% (−15.5%). And a broken bridge block, using activity codes that don't exist and arbitrary "market slot" factors, had kept meat markets disconnected from the herds in every scenario; meat prices now respond (pork +23% where supply falls 30%). EU meat prices still react far less than CAPRI's (pork +4% vs +43%) — recorded as the next market question |
| **CAPRI's Green Deal switchboard; Farm-to-Fork in 2030** | `greendeal_scenario()` mirrors `greendeal_scenarios.gms` — same settings, units and result names; unimplemented options refused. The projection now runs scenario objects, reusing each year's baseline. Run in 2030 as CAPRI does: farmland +3.6% (+3%), cereals 0.85× (0.77× on the 2017 base), oilseeds 1.04×, vegetables and permanent crops 1.14×. The 2030 scenario converges in exactly 25 iterations, the cap |
| **Organic yield gap in CAPRI's actual mode** | The organic gap was discounted by 0.45 whenever the pesticide instrument was active. CAPRI does that only in its endogenous-pesticide mode; the Farm-to-Fork study used an explicit 10% loss, in which the organic gap applies in full. Removed: wheat and barley yields now −11% as in CAPRI, cereals 0.67× → 0.77×. Oilseeds (1.09×) and vegetables and permanent crops (1.16×) now slightly overshoot — they had matched partly because of the discount; nothing re-tuned. Iteration cap 15 → 25 (this scenario converges in 16) |
| **Farm-to-Fork matches CAPRI's area split; five times faster** | 79% of scenario run time was a slow fallback solving 11 **infeasible** regional problems — mountain and island regions where the landscape floor cannot fit on their arable land — and returning constraint-violating answers the model used. The floor is now fitted exactly to what the land can hold and the unmet part reported (81.7 kha, 0.8%). All regions converge; a full comparison takes ~2 minutes instead of ~10. With a bracketed land update the scenario converges in 11 iterations: **farmland +3.7% (CAPRI +3%), cereal area −3.7% (−4%), oilseeds 0.97×, vegetables and permanent crops 0.97×**. Cereals 0.67× — now exposed as a weaker yield response |
| **Land rents from Eurostat; land market converges robustly** | Regional land rents now come from Eurostat (`apri_lrnt`, 2017): 209 of 248 regions published, Germany and Cyprus on a flagged fallback. The CAPRI accounts rents used before overstated land's value up to sevenfold in places (Slovakia 340 against 48 €/ha), suppressing the land response. With the steeper response, the land update oscillated in low-rent regions; a secant step now settles it in 3–4 iterations |
| **Faster solves; real shadow prices; land responds to rent** | A profile put half of run time in the nitrogen intensity routine and 11% in `_base_levels`; both rewritten with **zero difference** in results (binding-ceiling solves 3.8× faster). The reported shadow prices could only be non-zero for a violated constraint — now real duals, labelled per row, which withdraws an early finding that land never binds. Agricultural land now responds to the land rent (CAPRI's land market; elasticity 0.15 from its land-use nest, rents from its accounts), one solve per region per outer iteration, carried statelessly. Farm-to-Fork re-run against CAPRI's Figure 5 (farmland +3%, oilseed area −4%) pending. A remaining cost, solver cycling in 11 of 248 regions per scenario iteration, is diagnosed and recorded |
| **Sugar trade from CAPRI; source files checked; README counts gated** | Sugar now carries CAPRI's own extra-EU trade (imports 2,969 kt, exports 855 kt, from the bilateral 2030 reference), so its EU price can respond. Durum remains a documented gap: CAPRI trades wheat as one commodity, and the market's EU durum balance is near-even, so the first attempt made the premium so steep that Farm-to-Fork stopped converging — fixed by applying the traded-goods rule to the rebuilt flows; converges in 7. The source price tables and CAPRI's regional selection are now shape-checked (40/40 files, gzip included). The documentation gate checks README counts against the code — and caught a stale input count on its first run |
| **Trade check against CAPRI; abatement layers labelled** | Under Farm-to-Fork, EU cereal imports rise +40% (CAPRI +39%, durum excluded for lack of trade data) and exports fall −44% (CAPRI −38%), reported by a new `eu_gross_trade` from the market's own Armington clearing. CAPRI's mitigation portfolio is now the primary technological abatement (`abatement_capri`); the EcAMPA measures are kept as an independent literature comparison (`abatement`), with fitness-for-use entries for both |
| **Abatement from CAPRI's own mitigation portfolio** | Replaces reliance on a 10-row literature table with CAPRI's data: its technology table (20 options × 27 countries) and its full-potential run against the 2030 reference. The adoption rule is CAPRI's own and reproduces its calibration for all 245 options at zero price. At full potential, per source, on this model's emissions: enteric −10.8% (CAPRI −12.0%), manure methane −22.3% (−21.8%), manure N₂O −29.4% (−30.0%). Also corrected along the way: CAPRI's reductions had first been read per unit of an aggregate that grows 17%, overstating them twofold |
| **Oilseed seed quantities reach the market intact** | The bridge multiplied rapeseed and sunflower seed by the oil extraction yield (0.42) and handed the result to the seed market, so the market saw EU rapeseed at 7.4 Mt instead of ~19 (CAPRI's 2030 reference: 22.4). Found by comparing against CAPRI's own EU27 market balance, now stored as a validation reference — which also confirms the corrected EU balance (wheat self-sufficiency 1.27 against CAPRI's 1.31). Oilseeds under Farm-to-Fork 1.40× → 1.33× |
| **Pesticide target on conventional area only** | CAPRI treats the 50% pesticide cut as a total target: organic conversion already delivers part of it, and only the remainder falls on conventional land (`conventional_io.gms`). This model applied the full cut, the yield loss and the extra input costs to every hectare, double-counting wherever organic and pesticide instruments combine. Fixed: **vegetables and permanent crops 1.21× → 1.08×** CAPRI, oilseeds 1.48× → 1.40×. Run instrument by instrument, the landscape floor matches CAPRI's own attribution (cereal area −8.8% against −9%); the remaining oilseed excess sits in the pesticide cost channel |
| **Results no longer depend on a model's history** (run history dependence) | A run with a world price shock overwrote the market's base world prices and nothing restored them, so every later run on the same model inherited the shock — a baseline after a +20% wheat-price run gave DE11 wheat 111.2 instead of 91.2. This predates the current work. The market calibration also froze at an instance's first-ever solve. Now each run starts from the true base, each baseline recalibrates, and scenarios reuse their baseline's calibration. The null-trajectory projection test passes even after a deliberately shocked first run |
| **Consistent EU market; scenarios converge fast** | The market's EU production was the residual of a hard-coded world total (wheat 55.9 Mt against ~139), so EU consumption came out at 28.4 Mt of wheat. Now EU production is the model's own output and consumption keeps FAO's self-sufficiency — wheat 99.4 Mt; the baseline converges in 2 iterations instead of 11. The Armington premium now uses gross trade, applies only to traded goods (sugar beet was flipping between bounds every iteration), and the market anticipates the supply response. **Farm-to-Fork converges in 6 iterations; a full comparison takes ~10 min.** Cereals −15.0% against CAPRI's −15%. Also fixed: a world-price shock persisted into every later run on the same model |
| **Land conserved; CAPRI's own Green Deal targets** | The arable constraint left out set-aside and fodder, so a landscape floor grew set-aside out of nothing (DE40: +52 kha, cereals unchanged) and ~14 Mha of slack meant the constraint could never bind. Fixed, with one crop classification shared by the constraints and the land data — base fidelity improved 0.59% → 0.22%. CAPRI's per-member-state landscape and organic targets (from its own GDX files) replace flat 10% and 25%: organic conversion is burden-shared by member state and crop group. **Cereals −15.3% against CAPRI's −15%.** Diagnosing the remaining price overshoot found the market's EU base balance departs from FAO (wheat consumption 28.5 Mt vs 108.9) — recorded as the next fix |
| **EU prices now formed in an Armington market** | The oilseed and permanent-crop overshoot had a structural cause: every EU price was a fixed wedge on the world price, so the EU was a price-taker. The model held Armington parameters — CAPRI's own values — but they only split imports among supplier countries and never touched prices. And farmers responded to the world price, not the EU price. Under Farm-to-Fork, EU prices rose 1.6–3% against CAPRI's 8–15%. Fixed with an Armington premium from the standard first-order condition, with supply responding to the EU price; exactly 1 at base, all anchors unchanged. A cobweb oscillation followed and was damped. **Oilseeds 1.40× → 0.93×, vegetables and permanent crops 1.39× → 1.05×**, prices now +7.5–9.5%. Cereals fall to 0.65× with their price almost exactly CAPRI's — so the earlier cereal match was partly two errors cancelling. Rice also added to the supply-to-market bridge |
| **Three "Not sound for" items fixed** | **Wine**: only 11 of the "101 regions" actually grow wine; each now falls back to its country's own CAPRI price (Sicily 95.5 → 1,361.6 EUR/t) instead of the EU average. **Croatia**: split by crop from CAPRI's regional data instead of one cattle key, which had put 91% of the olives in continental Croatia — Adriatic olives now 18.0 kha, verified against CAPRI's national 18.6. **Saxony**: split by crop from the pre-2013 codes — maize in upland Chemnitz 7.1 → 0.9 kha, lowland Leipzig 2.4 → 7.8. National totals preserved exactly. Norway, Irish nitrogen, the overshoot, multi-period projections and economy-wide effects remain, each for a stated reason |
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
