# Fitness for use

Which of the model's outputs can be relied on, which cannot, and the hazards in reading them. Read this before using a
number from the model. The same findings are in machine-readable form in `capri_data/FITNESS_FOR_USE.json`, queried
with `capri_mod/fitness.py`. The comparisons with CAPRI's runs (the Green Deal 2030 step and Farm-to-Fork 2030) are in
README2.md, §2.

> **The figures here are those of the runs each paragraph names.** Most predate the changes of late November 2026
> (the non-EU supply countries in the run, the default since 24 November; CAPRI's 2030 livestock outputs per head).
> They are to be refreshed from the next converged full-EU runs.

## The references

The model is checked against:

- CAPRI's 2030 Green Deal baseline, the levels the 2030 baseline is calibrated to;
- CAPRI's dump of its market model at its calibration point;
- the project lead's CAPRI runs of the Green Deal 2030 baseline and step (the same release, star 3.0);
- CAPRI's published Farm-to-Fork results (JRC121368, an older CAPRI);
- CAPRI's 2030 run without voluntary coupled support against its reference.

CAPRI's results are used to check, not to tune.

**The 2030 baseline against CAPRI's Green Deal baseline:** crop levels per regional unit within a median 0.22% of
CAPRI's (95% within 1.5%; 7 pairs above 5%, 7 thousand ha; `tools/check/compare_baseline_capri.py`).

**The projection layer against CAPRI's own 2030 baseline:** projecting to 2030 on the captrd trajectory reproduces
CAPRI's 2030 reference to a correlation of +0.993 on activity levels, total cropped area within 3%, and 20 of 23 crops
within 25% (the regression anchor, `capri_data/validation/REGRESSION_ANCHORS.json`).

## Sound for

- Base-year analysis and the comparative-static policy increment.
- **Area-based instruments**: set-aside and landscape elements, CAP payment rates (BISS, coupled support, Pillar II
  budgets). Magnitudes are of the right order against CAPRI.
- **The Green Deal 2030 step**, at the comparison settings (`capri_mod/settings/capri_comparison.toml`): EU activity
  changes within a mean 1.0 points of CAPRI's step, EU producer prices within 0.6 points, median ratio 0.97 (23
  November 2026; README2.md §2.2).
- **Nitrogen targets**: CAPRI's tiered surplus rule on the gross N balance inside the regional models; pesticide
  instruments (with plant-protection costs derived from all 27 member states); organic area targets (CAPRI's
  input/output adjustment with its FADN yield gaps).
- Emission-tax scenarios with CAPRI's mitigation options endogenous (CAPRI's ghgTax). No CAPRI tax result is in hand to
  compare with (docs/MITIGATION_IN_SUPPLY.md).
- Indicator layers: GHG, nutrient balances; irrigation water demand and farm income as reports outside the run
  (`capri_mod/water`, `capri_mod/income`).

## Not sound for

- **Price magnitudes under Farm-to-Fork.** Against JRC121368, cereal prices rise too far (+12.5% against +8.2%), the
  pork price far too little (+21% against +43%) and the milk price far too much (+22% against +1%). Directions and
  rankings are usable. JRC121368 is another CAPRI release with another baseline (README2.md §2.3).
- **The Green Deal's N-surplus dual**, the price of its nitrogen target: 0.856 of CAPRI's in the median unit (CAPRI's
  dual recovered from its results' marginal terms, `tools/build/extract_capri_marginal_terms.py`). The herds' response
  and the grassland split follow it.
- **A scenario's reported income**: still at the base unit margins. The solved ration, the fodder's scenario value and
  the mitigation options' costs are not in it yet; the port of CAPRI's income indicators (reports/calc_inc_indic.gms)
  is planned (`capri_mod/income`).
- **Results of a run that has not converged.** A run that stops at the iteration limit says so in
  `metadata["outer_converged"]`, to be checked before using its results.
- **Multi-period projections.** The projection is checked for a single step to 2030; the recursion runs but has no
  external check, and herds are re-optimised each period rather than carried.
- **Economy-wide effects** (labour, capital, GDP): outside the partial-equilibrium boundary, as in CAPRI.

## Reading hazards

**Run scenario comparisons to convergence.** `max_outer_iter=1` gives a single supply-market pass and suppresses the
price feedback, which overstates quantity responses: it moved the Farm-to-Fork cereal decline by 4 percentage points.
An unconverged run raises a `RuntimeWarning` and sets `metadata["outer_converged"] = False`; do not compare such a run
against external references.

**Filter near-zero base cells before reading percentage changes.** An activity with a base of 0.0 in the selected
regions produces meaningless percentages: a CAP scenario run on northern-European regions reported *pig fattening
+118%* on a base of zero, and an organic scenario showed cotton and olives at +1600%. Restrict to activities that exist
in the region set (a base threshold of about 50 kha works) before computing or reporting any percentage.

**Compare production with CAPRI's published production, not areas.**

## How the instruments behave

**Prices are formed in an Armington market.** EU and imported goods are imperfect substitutes, so when EU supply falls
the EU price must rise before consumers turn to imports, with CAPRI's own substitution elasticities. Farmers respond
to that EU price; it is what holds supply up under a policy shock. With EU prices tied rigidly to world prices instead,
Farm-to-Fork prices rose only 1.6-3% and oilseed and permanent-crop output fell about 40% further than CAPRI's. The
premium is exactly 1 in the base year.

**Agricultural land responds to the land rent**, through CAPRI's land market. When a policy makes land scarce, its
value rises and farmland expands by absorbing other land: the land types are variables of the regional model with
CAPRI's quadratic land terms (`p_pmpQuadLandTypes`) and calibration rents (`land_rents_2030`). A region without
land-market data keeps its land fixed, as CAPRI without the land market. A rent-elasticity expansion that stood in for
it (an elasticity of 0.15 and Eurostat rents) was a proxy and was removed (docs/dev/PROXY_AUDIT.md). Land expansion is
what closed the oilseed gap: with land fixed, a landscape floor took every hectare from crops, and oilseeds lost about
three times CAPRI's share of area.

**Where the landscape floor cannot fit, it is kept, as in CAPRI.** With the land market off, a floor sized on total
farmland may not fit on a region's arable land (Corsica, the Alps, Greek regions). CAPRI keeps the floor
(`e_setaLandscape`; its widen_bounds.gms never relaxes it) and carries on with the solver's last point; the model does
the same and records it in the run's `nlp_fallback`. CAPRI's Green Deal runs have the land market on, where grassland
can become arable land; the reference runs do too and meet every floor.

**Land is conserved.** Every activity on arable land, fodder and set-aside included, competes for it, so a landscape
floor displaces crops as it does in CAPRI rather than adding land.

**The nutrient target** binds the full gross nitrogen balance, manure included. Manure replaces mineral fertiliser
linearly with CAPRI's availability factors (docs/FERTILISER_ALLOCATION.md); fertiliser also falls through CAPRI's
efficiency technologies, adopted under the nitrogen shadow price; manure must be spread on land (Nitrates Directive).
Feed rations are chosen endogenously and feed demand follows herds; fodder must be grown where it is eaten (CAPRI's
fodder equality). Ammonia uses CAPRI's emission factors per region.

**The EU market balance is consistent.** The market is calibrated once per run at CAPRI's 2030 market data, as CAPRI's
prep_market: the baseline is a market solution there, EU production in the market is the supply models' output and EU
use follows CAPRI's Armington balance (food, feed, processing, biofuels, each with CAPRI's function). The market
anticipates the supply response through CAPRI's market supply functions (ProdNQ_, measured on the supply models), and
the loop ends on CAPRI's stop rule.

## The data behind the outputs

**World production and trade are CAPRI's market data.** The market runs on CAPRI's bilateral market (2017 and 2030
market data) for CAPRI's 45 market regions; no region is aggregated or allocated by a share. The base world prices are
CAPRI's FAO_agg world prices (`tools/build/build_world_prices.py`; the wheat market's is CAPRI's WHEA price). The
base-price test (`test_market_module_reproduces_its_own_prices`) checks that the market reproduces its own base
prices: solver consistency, not a validation against an independent price.

**Livestock `gross_output` is marketed product from CAPRI's own coefficients.** It is built from CAPRI's final-product
items (milk, beef, pork, poultry meat, eggs, sheep and goat meat and milk) by `tools/build/build_livestock_output_coef.py`;
EU totals match real 2017 production within 0.94-1.08 by product, equalling CAPRI's own EU27 total to the tonne.

**The regional base data are CAPRI's own, built by one tool** (`tools/build/build_capri_base.py`) for every regional
unit. Each country lands within 0.93-1.03 of CAPRI's own agricultural area, and the total equals it exactly: 166,690
kha. Every CAPRI crop activity with a recorded area is mapped, including paddy rice (`PARI`, 427 kha EU-wide), table
olives and CAPRI's four minor activities. Poultry head counts are CAPRI's, in million head, converted by the loader
(`capri_mod/data/loaders.py`). Each of the 250 units carries its CAPRI row (Saxony and Croatia are single units in
CAPRI, DED00000 and HR000000); where CAPRI has no regional value for a crop, the unit takes its member state's
(`tools/build/build_crop_economics_2017.py`).

**Farm income (`gross_margin`) is net revenue × activity levels**, with livestock revenue from CAPRI's own output value
per head (TOOU and `MREV`) rather than from `YILD`, which for breeding and suckler activities is not a marketed
product. The PMP terms are a calibration device and are excluded from the reported margin. In a scenario the net
revenues are still the base unit margins (above, *Not sound for*).

**Re-basing is not available yet.** The base year is CAPRI's (2017); a new base needs CAPRI's data steps (COCO,
CAPREG, the market database) ported or a newer CAPRI release, planned through the data pipeline
(`docs/dev/CAPTRD_MOD.md`).

## By module

| Module | Status | How validated |
|---|---|---|
| **Supply, crops** | CAPRI's own terms and levels | CAPRI's 2030 PMP terms; the 2030 baseline's crop levels within a median 0.22% of CAPRI's Green Deal baseline; Green Deal activity changes within a mean 1.0 points of CAPRI's step |
| **Supply, livestock** | CAPRI's run (direction and size) | Green Deal: suckler cows −27.8% against −28.8%, pigs −8.6% against −9.2%; Farm-to-Fork dairy cows −3% against JRC121368's −10% |
| **Policy, payments** | Validated | premiums match CAPRI's `PRME`; the EU budget computes to €54.2bn against the real ~€55-58bn |
| **Policy, scenario response** | Published CAPRI (JRC121368) | all four Farm-to-Fork instruments in CAPRI's own specification, EU-wide, converged: farmland +3.2% against +3%, cereals −16.3% against −15%, oilseeds −12.2% against −15.4%, vegetables and permanent crops −13.0% against −12% |
| **Policy, nitrogen instruments** | CAPRI's form | CAPRI's tiered N-balance target inside the regional models, met through CAPRI's fertiliser options, intensity variants and area |
| **Environment** | Validated | gross N balance on CAPRI's definition (`e_SURTOTHa`) against CAPRI's 2030 reference (EU, kg N/ha): removal 125 against 119, residues 57 against 55, fixation 10 against 8, deposition 11 against 11, mineral 63 against 57, manure 54 against 53; regional surplus correlation 0.92 over 235 regions. P2O5 balance (docs/P_BALANCE.md): regional surplus correlation 0.99 |
| **Feed** | CAPRI data | rations chosen inside the regional models against CAPRI's requirement rows (REQSE_) at CAPRI's base rations; the requirements equal the base rations' supply by construction, no independent check |
| **Market** | CAPRI's market model | at CAPRI's calibration point prices within 1.5e-4, trade flows within 1e-3; given CAPRI's own Green Deal supply and feed demand, EU price changes within a median 0.08 points of CAPRI's |
| **Biofuel** | CAPRI structure | the feedstock CES reproduces CAPRI's 2030 BiofFeedCost in every market region; the biofuel markets (`BIOF_M`) reproduce every region's 2030 output and use at reference prices |

## The machine-readable form

```python
from capri_mod.fitness import check, caveats

check("scenario.permanent_crops").status   # 'overstated'
check("supply.gross_margin").ok            # True
caveats(["scenario.oilseeds", "activities.WINE"])   # what to report alongside
```

Statuses are `validated`, `use_with_care`, `overstated`, `understated` and `not_supported`. Lookup falls back from the
specific to the general, and an unrecorded key returns `unknown`, which means no finding is recorded, *not* that the
output is validated. The JSON's figures are to be refreshed from a converged run.
