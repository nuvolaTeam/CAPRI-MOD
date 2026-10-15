# Module coupling and commodity coverage — review

*October 2026. Facts below are read from the code and checked by running it.*

## Current state (October 2026)

**Nitrogen target as a plain constraint (capri-mod-proto).** CAPRI's inhibitor on manure, the last block decided
outside the regional solver at a given N price, is a decision of the conic model (exact, perspective cone); the
per-region N-price search is gone and the surplus target is a constraint as in CAPRI's NLP. Farm-to-Fork converged in
13 iterations, 353 s (gap 4.29); Green Deal 20 iterations, 584 s (docs/PROTOTYPE_NI_INSIDE.md).

**Parameters in one file (Sprint 9t).** `capri_data/shared/model_parameters.csv` (value, unit, kind, source) for
every constant of the economics and accounts; combined CAPRI regions' land supply summed over their land owners.
Farm-to-Fork gap 4.26.

**No synthetic data (Sprint 9s).** Crop premiums, costs, prices and yields are CAPRI's for every region; methane and
CO2 coefficients are CAPRI's (regional CH4MAN, CH4ENT, CO2LIM, urea shares); yield elasticities CAPRI's. Generators
and generic fallbacks removed (docs/SYNTHETIC_DATA_AUDIT.md); CAPRI's fixed activities and no other-oilseed market;
CAPRI's land market in every farmed region (Ireland added). Farm-to-Fork gap 4.27 (4.06 before Ireland's land market).

**Parallel regional solves; CAPRI's tariffs (Sprint 9r).** The regional supply models, independent at given market
prices, are solved across worker processes (one per core); results identical to one process. On 2 cores Farm-to-Fork
463 s, Green Deal 881 s (were 799 and 1537 s). The non-EU tariffs, drawn at random by the loader until now, are
CAPRI's total protection from its 2017 bilateral flows; indicators within 0.1 point.

**CAPRI's 2030 rations and fodder (Sprint 9q).** The projected baseline's rations, requirements and usable fodder per
ha are CAPRI's 2030 reference's; regional drift of the calibrated baseline 0.01% (median), 0.36% (90th percentile);
against CAPRI's reference activities 1.3%, production 1.1%.

**Projection layer: CAPRI's reference and baseline calibration (Sprint 9p).** The 2030 baseline is projected with
CAPRI's 2030 reference (levels, yields, land types per region) and calibrated as CAPMOD calibrates its supply models
(regional drift median 0.13%); against the reference: activities 2.6%, production 1.4%, use 1.7%. Open: fodder crops.

**Pigs, manure N2O and ammonia diagnosed; market speed (Sprint 9o).** The pig overshoot is Brittany and Lombardy
alone (rest of the EU −14.4%, CAPRI −14.5%); it, the manure N2O and the ammonia gaps follow the regional N prices,
which depend on which nine regions JRC121368's 36% relaxation covers (unnamed in the report; sensitivity gap 4.15).
Market solves ~40 steps instead of 60; Farm-to-Fork 747 s.

**Speed, reproducibility, milk price (Sprint 9n).** −21% time per outer iteration with unchanged behaviour; runs
now repeat exactly (fixed hash seed); the milk price gap re-checked and kept as a CAPRI version difference.

**Inhibitors on manure under the emission tax (Sprint 9m).** Every CAPRI option is now priced by the tax: at EUR
50/t inhibitors treat 34% of manure N; GHG −10.5%, manure N2O −15.9%, ammonia +1.9% (pollution swapping).

**Fertiliser options under the emission tax (Sprint 9l).** Under the tax the crops' mineral N is a variable of the
regional model without a nitrogen row, priced at its soil N2O; the options are adopted (inhibitors 15%, precision
farming 20% at EUR 50/t; GHG −9.5%, fertiliser N2O −13.3%).

**Manure and ammonia in every EU solve (Sprint 9k).** CAPRI's crop-need row (NUTNED_) and the manure trade columns
are in every EU regional solve, not only under a nitrogen target; the trade's cost is the pool price alone (CAPRI's
calibrated constants), and the pool clearing reads the price each region was solved at. Under the emission tax the
ammonia options are in the regional model priced by their N2O and NH3-borne emissions, and traded manure by the
mineral N it moves: EUR 50/t, GHG −8.0% (−6.8% before), manure N2O −10.3%, ammonia −0.9% (low-emission spreading
falls: its NH3 kept raises application N2O). Farm-to-Fork unchanged (gap 4.37), Green Deal within 0.8 points.

**Manure trade checked (Sprint 9j).** The base trade is CAPRI's 2030 reference per region (Belgium, Romania,
Ireland and others had been missing) and counts only in runs that trade manure: the Farm-to-Fork baseline, like
JRC121368's, keeps all manure in its region (gap 4.53 → 4.36). Green Deal: 1.1 Mt N traded against the base pattern,
importers no longer give up crops (docs/MANURE_MARKET.md).

**No post-solve modules left (Sprint 9i).** The post-solve feed module (IPCC requirement functions and a feed
balance after the solve) and the post-solve abatement layers (a net-revenue MACC, EcAMPA measures at full uptake,
CAPRI's portfolio applied after the solve) are retired with their data; CAPRI's emission tax (ghgTax) now acts
inside the supply models on each column's emissions per unit at the baseline solution (`ghg_tax.py`,
`carbon_tax_scenario`).

**All feed bulks and the residual feed markets (Sprint 9h).** CAPRI's five tradable feed bulks per member state
price the rations and split feed use into products; the residual feeds FENI (sugar by-products, manioc) and FPRI
(milling by-products) are traded markets with the EU's output from milling and sugar processing (`MaprFeed_`).
Baseline EU output and use exactly CAPRI's 2030; Farm-to-Fork gap 4.59 → 4.53 (docs/FEED_MARKETS.md).

**Feed options on, as star 3.0 (Sprint 9g).** Low-nitrogen feeding (`low_n_feed.gms`) and the linseed and nitrate
supplements (`line_nitr.gms`) are columns of the regional models with CAPRI's effects, maximum shares and calibration;
enteric CH4 follows the supplements. Farm-to-Fork: low-N feed on 42% of manure N (Table 17: 0%), linseed 0.8%, nitrate
0.2% (7%); gap 5.15 → 4.59. 3-NOP registered (CH4 only). docs/MITIGATION_IN_SUPPLY.md.

**Dairy block on, as star 3.0 (Sprint 9f).** CAPRI's dairy block is now part of the default market: nine dairy
products traded bilaterally, raw milk, fat and protein priced per member state, regional models paid their member
state's milk price. Baseline dairy within 3.6% of CAPRI's 2030 reference; Farm-to-Fork milk price +34% against +1.5%
(gap 5.15; +30% after Sprint 9g). JRC121368's Figure 7 checked (+1.2%): the JRC-era dairy block passed less of a milk
cut to the price than star 3.0's coefficients do - recorded as a version difference (docs/DAIRY_PROCESSING.md).

**Inner fertiliser model and `mineRedu` (Sprint 9e).** CAPRI's inner fertiliser distribution model (star 3.0
default) allocates each region's mineral, manure and residue N over CAPRI's crop groups on CAPRI's 2030 priors
(`results["fert_dist"]`); the Green Deal mineral fertiliser reduction (`mineRedu`: UAA-wide or by crop group with
CAPRI's exemptions) is a mineral-N row in the regional models, coupled to the fertiliser technologies. The
technologies now act on the crops' mineral rate (they had acted on the manure-covered need too, overstating their
saving ~40%); Farm-to-Fork gap 3.31 → 3.77, herds overshoot more (docs/FERTILISER_ALLOCATION.md). Every star 3.0
default of the scenario run is now in. Herd overshoot located (docs/COUPLING_SPRINTS.md, "Diagnosis after Sprint
9e"): the regional N price in the pig, dairy and sheep regions (Brittany €86/kg N); relaxing Brittany and Lombardy as
JRC121368's capped regions gives gap 3.47 but a pork price of +32%; CAPRI's regional Farm-to-Fork output is needed.

**Biofuel loop closed (Sprint 9d).** DDGS from the ethanol plants is a market commodity whose price enters the
plants' feedstock cost; the member states' feed bulks (FCER, FPRO) are split into products by CAPRI's CES
(`feedBlkPrice_`, `feedShareEqu_`, rho 6) and their price indices go to the rations, replacing the single EU cereal
and cake indices; non-EU DDGS feed demand from CAPRI's p_ElasFeed; non-fuel ethanol processing from `ProcNQ_`;
mandate shifts as `change_biof_mandate.gms` (docs/BIOFUEL_MARKET.md).

**Endogenous biofuel markets (Sprint 9c).** CAPRI's `BIOF_M` (star 3.0 GUI default) is the default: bio-ethanol and
bio-diesel are market commodities with CAPRI's supply (`SupplyBiof_`, on the processing margin) and demand
(`biofDemShare_`, mandate plus price against fossil fuel) per CAPRI market region, traded bilaterally; feedstock
use follows the biofuel output in every region (docs/BIOFUEL_MARKET.md). Remaining star 3.0 default then missing: the
inner fertilizer model (Sprint 9e).

**Scenario settings as star 3.0 (Sprint 9b).** Defaults are star 3.0's GUI defaults (manure trade on); each scenario
carries its own settings: the Green Deal group as star 3.0's files, Farm-to-Fork as JRC121368 (manure trade off,
tiered rule, genomics 0.2). Star 3.0 defaults then still missing: endogenous biofuel markets (BIOF_M, done in Sprint
9c) and the inner fertilizer model (docs/SCENARIO_SETTINGS.md).

**Scenario configurations (Sprint 9a).** Star 3.0's own surplus target (`surptot.gms`: every region's surplus per
hectare -50%) differs from JRC121368's tiered rule with its 36% cap; both are settings, and `run_f2f_2030.py --config
jrc121368|star3` sets the whole configuration (surplus rule, manure trade, genomics). The report's figures are
comparable with `jrc121368` only (gap 3.29); star 3.0's own Farm-to-Fork cuts the EU surplus by 46%. The pig overshoot
(-21% vs -14.5%) is Brittany and Lombardy, where without manure trade only animals carry the cut.

**CAPRI's bilateral market and the 2030 baseline (Sprint 8m).** The market is now CAPRI's: a price per region, two
Armington nests over CAPRI's bilateral flows of the run's year (2030 reference for the projection), transport costs,
tariffs and EU tariff-rate quotas; wheat with durum, olive oil and milled rice as traded products. The 2030 baseline
follows CAPRI's trend projection properly (model keys, livestock output per head, crop levels): median deviation
from star 3.0's 2030 reference 3.8% (was 9.5%). Farm-to-Fork gap 4.51 -> 3.30. Remaining market departures: raw milk
and other oilseeds as pooled markets (no CAPRI bilateral trade), dairy product prices without the dairy block,
global quotas, CAPRI's augmented-CES commitment terms.

**Star 3.0 as the reference (Sprint 6c).** Technology settings (`ghgTechMYld`, `ghgTechFEff`) are now scenario
configuration as in CAPRI, applied to baseline and scenario together; default star 3.0 (milk-yield genomics off).
The market's world base is CAPRI's FAO_agg for every region (sugar was cane, pork and eggs 40–50% too large); sugar
comes from beet at CAPRI's member-state yields with the beet price following sugar; the FATS and OFOD_M placeholders
and the beet world market are gone; rye and oats reach the other-cereals market; dairy products use CAPRI's yields.
Farm-to-Fork gap 4.36 → 4.51 (beef price +9% vs +24: the EU premium approximation in a world of CAPRI's size). New
like-for-like check against star 3.0's 2030 reference: median deviation 9.5% (activity levels), 9.4% (production).
Remaining market departures: the premium approximation (next sprint: CAPRI's bilateral market), durum, rice, other
oilseeds and olives without CAPRI world balances, the non-EU world and EU self-sufficiency at base-period values in
2030 runs.

**Manure trade.** CAPRI's Green Deal runs trade manure (`manureTradeNew` on); with the model's manure market (pools now
clearing, 10 iterations) the gap falls 6.13 → 5.23 and pigs match CAPRI (−13.7 vs −14.5). Off by default:
JRC121368's CAPRI had no manure trade (report sect. 4.3.4). EU instruments no longer apply to Norway.

**Items not yet modelled, first pass.** Inhibitors on manure now work with the technologies inside (they were
skipped there): F2F gap 6.41 → 5.70. Also in: fertiliser side effects, 2030 fodder values, CAPRI's regional
plant-protection costs, the coupled-support test (deviation 1.23 points), and CAPRI's Farm-to-Fork catch-crop
minimum (16% → 41% of the eligible area; gap 5.72). Sprint 7b: CAPRI's dairy split DCOL/DCOH (low-yield cows 50% → 51.8%, dairy cows −11.7%,
gap 5.73). GHG accounts: a unit bug had left soil N2O, liming and urea out of the total; soil N2O is
now by source (mineral, residues, histosols) as CAPRI; GHG total −20.4% (CAPRI −14.8), gap 5.81. Histosol fallowing
built, ~0 adoption (the model's land rents are a few EUR/ha). Manure N2O by stage with CAPRI's technology effects: −27.1% (CAPRI −3.2%), GHG total
−22.5%, gap 5.89 (5.81 with CAPRI's regional baseline surpluses). Open: manure inhibitors' adoption (CAPRI cost terms missing), dairy processing, crushing stage 4.

**Sprint 8 — CAPRI's land rules are the default.** The runaway regions under the land rules came from the model's
own grassland row (grass + arable fodder <= grassland + a fifth of arable land): held as an equality it pinned
arable fodder leys, so cattle had to stay and the N cut fell on poultry and pigs. With CAPRI's grassland balance the
land rules became the default. Follow-ups: regional tables for split and merged NUTS regions now come from their
CAPRI group (Finland's FI1B had carried all of Etelae-Suomi), and JRC121368's 36% rule for infeasible targets now
covers the Dutch manure-importing regions. Farm-to-Fork gap 4.70 (old default 5.81; with the manure market 4.77),
EU farmland +2.1% (CAPRI +3%), no land-market fallbacks. Open: Friesland at EUR 16,000/kg N (relaxed too: gap 4.58).
Sprint 7c: CAPRI's bull and heifer splits (BULL/BULH, HEIL/HEIH) per stall, with beef, manure, feed and young
animals; shifts are small (low-intensity bull stalls 33.6% -> 34.1%), gap 4.71. Manure N2O: CAPRI's loss cascade
and housing equation in, -28.8% -> -21.5% (CAPRI -3.2%), gap 4.64; the rest is the manure inhibitors' adoption.

**Sprint 7a — CAPRI's extensive and intensive grassland, default.** The model meets regional N cuts far less by idling
land (−2.9% instead of −7.5%); gap 6.71 → 6.33, N price median €6.1/kg. CAPRI's land rules now converge with it
(farmland +3.9%, CAPRI +3%) but stay off while Brittany and Lombardy remain extreme.

**Supply QP solver: Clarabel leading**, the built-in active-set chain as fallback and for comparison
(`qp_solver`); the two agree to 5e-5 on prices and 2e-5 on environmental totals (`tools/compare_qp_solvers.py`).

**Sprint 6a — CAPRI's 2030 prices in the baseline, default.** The 2030 baseline ran at 2017 prices and premiums;
it now takes CAPRI's 2030 reference unit values over CAPRI's input index (1.277) and CAPRI's 2030 premiums, in 2017
money (`capri_mod/projection/prices.py`). Gap 6.91 → 6.66; pork price +47% (CAPRI +43); poultry price +49% (+18).
Regional nitrogen prices are unchanged (median €10.5/kg N): the price level is not the cause of the nitrogen-price
failure. Next: nitrogen costs term by term against CAPRI's reference (`capri_marginal_terms_ini_2030.csv.xz`).

**Sprint 5 — CAPRI's pig activities, default** (docs/COUPLING_SPRINTS.md). Sows (`PIGS`) and fattening pigs
(`PIGF`) with CAPRI's coefficients, linked by a piglet market. Found and fixed: CAPRI's `MREV` is young-animal
sales for sows, raised calves and replacement heifers, so moving it with the meat price double-counted young
animals and under-moved suckler cows; meat, milk and egg prices now move revenue by quantity × price change,
product by product (`livestock_product_value_by_market_coef.csv`). Gap 6.75 → 6.91; beef animals −14.5% (CAPRI
−18), beef production −14.4% (−14). Sows and fatteners fall together (−29%): the pig gap is the level of regional
nitrogen prices, not the pig structure.

**Sprint 3 — CAPRI's land rules implemented, not default** (docs/COUPLING_SPRINTS.md). Three land-block defects
fixed: no-idle-land rows now hold at base use (the baseline settles); total land is conserved (land could vanish);
one land-supply mechanism where the land market solves. With CAPRI's rules the area farmed holds (+0.1%) but
nitrogen prices double to quadruple and pigs fall 40–43%, ruminants grow: grassland must stay grazed, so the cut
lands on monogastrics. Off by default until CAPRI's Farm-to-Fork results show what makes abatement cheap there.

**Feeding inside the supply models is now the default** (Sprint 4; docs/FEED_IN_SUPPLY.md): converged in 12
iterations, average gap 7.69 → 6.73. Channels examined while CAPRI's Farm-to-Fork results are sought: the
grassland split barely moves the gross balance, low-protein feeding is small (−3% pig excretion at most),
fertiliser options stop at CAPRI's over-fertilisation limit; the pig/sow split with a piglet market followed as
Sprint 5.

**Sprint 2 (in progress) — manure's value as fertiliser.** Manure replaces mineral N at CAPRI's marginal rate
under its endogenous availability (`endoManAvFact`, `fert/endoManAvail.gms`), from the reference run's own
per-region manure and mineral deliveries; the extra cut for crops at the minimum-mineral floor is gone (CAPRI's
`NUTNED_` is an equality with a free split of manure across crop groups, so floors bind only when manure grows).
Average gap 7.66 → 6.77. Found: the area farmed falls 14% (mostly idle land; CAPRI's farmland +3%) — idling land removes its
nitrogen from a balance capped per base hectare, at nitrogen prices of €9/kg (median) to over €21/kg (a quarter
of regions). With CAPRI's two land rules (no idle land, surplus per current hectare) the model swings to +13%
area farmed, sheep +52%, pigs −81%, unconverged: the regional targets cost the model far more than they cost
CAPRI. Next: the regional cuts' baseline (the 2023 CAPRI reference vs JRC121368's), a marginal-cost
decomposition in one high-price region, then the land rules (docs/COUPLING_SPRINTS.md). Decomposition done (Brittany):
technologies cover the first tenth of the cut, then herds and farmed land carry it at €9–22/kg N; pig, milk, beef and poultry
elasticities match CAPRI's and the targets add up to JRC121368's EU average (36%). CAPRI's own Farm-to-Fork run (surplus
constraint duals, regional herds) is needed to locate the difference. Legumes' removal now uses CAPRI's gross need (JRC96482:
fixation is 75% of soya's and pulses' need, and CAPRI's per-crop NITF is net of it): soya −66 → −33%; the egg premium gets
adaptive damping (it cycled). Average gap 7.69 (cereal, pork, poultry prices higher).

**Sprint 1 — gross nitrogen balance on CAPRI's definition** (`docs/COUPLING_SPRINTS.md`). Removal, crop residues
and fixation per crop from CAPRI's 2030 coefficients (`e_EXPPRD`, `e_CRESID`, `e_BIOFIX`); residue N displaces
mineral N at CAPRI's availability, arable residues pooled and credited by need, grassland and permanent crops
keeping their own (doc. eq. 5.10); manure-covered need spread by need, not per hectare (fallow had been credited
with average cover, so set-aside raised the reported surplus unseen by the constraint); fertiliser technologies
scale mineral N net of the manure and residue credits, organic land loses its mineral rate only
(`organic_minfert_redu.gms`); the N row takes each crop's own balance at the solve's yields and factors from the
same function as the accounts (target −35.8%, achieved −36.5%; before −27.6%). Outer loop: per-commodity
adaptive price damping (eggs cycled). EU balance items within 1–7 kg/ha of CAPRI's; regional correlation 0.92.
Farm-to-Fork: N₂O −39.4 (−40.4), beef animals −16.4 (−18), beef production −14.1 (−14), but dairy −14.8 (−10),
pigs −28.7 (−14.5), sheep −20 (−9.5), pork price +63.5 (+43); average gap 4.6 → 7.7. The old fit rested on two
errors that spared herds; the N target alone produces the overshoot, which points to Sprint 2 (crop-side
abatement: over-fertilisation, manure value under mineral caps).

**CAPRI's mitigation options on CAPRI's structure** (`docs/MITIGATION_IN_SUPPLY.md`). Read again from
CAPRI's code, three departures in the ammonia options and two in the fertiliser options were removed:

- ammonia: housing, storage, air purification and acidification are *alternatives* sharing one limit
  (`TotMit_`, NH3MAN), with CAPRI's combined pig/poultry options; the cost curvature follows CAPRI's
  calibration (relative subsidies, "VERSION B"), where the model had none for several options; losses
  cascade from house to storage to field. Adoption against Table 17: housing 66% → 19% (CAPRI 12%),
  covers 61% → 36% (34%), air purification 31% → 14% (10%); ammonia −34.9% (−33%);
- fertiliser: only the options CAPRI's Green Deal reference activates (precision farming, VRT_SRUC,
  timing, inhibitors - not the GAINS combinations the model had offered); costs per tonne of crop N
  need, as CAPRI's cost equation has them, not per hectare. Precision farming 1.5% → 9% (CAPRI 35%);
  VRT_SRUC is missing from the project's data.

**Livestock supply elasticities and young-animal markets** (`docs/YOUNG_ANIMALS.md`). Every livestock
activity had been calibrated to a hard-coded literature elasticity (dairy 0.15, bulls 0.18, pigs 0.20);
CAPRI's calibrated product elasticities (milk 0.47–0.58, beef 0.65–0.70, pork 0.57–0.72, poultry
0.71–0.79), already in the project, replace them. Calves, young cattle and replacement cows now clear
EU-wide markets at fixed net trade, as CAPRI's `yaniMarket_`, with coefficients per model head (the old
per-CAPRI-head coefficients gave EU base balances far from CAPRI's). Effect: pork price +21 → +32% (CAPRI
+43%), sheep −6 → −10.5% (−9.5%); beef production −5.5% (−14%) and pigs −22.5% (−14.5%) are now the
largest gaps. **Livestock curvature on the margin's basis**: margins had moved to CAPRI's total output
(TOOU) but the PMP curvature still used market revenue (MREV); for suckler cows (MREV €68 vs TOOU €620 per
head in Düsseldorf, the rest calves) this made them about nine times too responsive. Curvature now uses
TOOU, a commodity price moves only the market part of revenue (young animals move with their own
prices), and each cattle activity's elasticity weights its product's and its young animals' (CAPRI's
calibrated YCAM/YCAF/YBUL/YHEI/YCOW, 2020 file). Ireland was missing from the young-animal data (wrong
national code); fixed. Result: beef price +8.9 → +12.7%, beef production −5.5 → −7.6%, beef animals
−6.7 → −8.4%; average gap 4.55 → 4.31. Earlier regional diagnosis: where the nitrogen price stays below €1/kg (about a quarter of suckler
cows and calves) herds *grow* with prices (suckler cows +22%, pigs +10%), where it exceeds €20/kg they
collapse (suckler cows −65%, pigs −45%); CAPRI's results show neither extreme.

**Fertiliser options on CAPRI's own mitigation data** (`miti_data_jul15`, supplied by the project lead). The
Green Deal runs use `miti_data_jul15`; the model's table came from another set (`tdev`). Now from jul15:
VRT_SRUC (regional farm-size cost curves, NMIN 0.26) added; NITR_INH as CAPRI sets it — QEmitt = 0.9 × no
control (`ghgMiti.gms` l. 110), so NMIN 0.09 instead of 0.48, capped by over-fertilisation, maximum share
0.56–0.66 instead of 0.3; nitrification inhibitors on applied manure (target N2OMAN, NMAN 0.09, outside
`Tot_MitFert_`) now active (the routine looked up the wrong key and never ran). Adoption: precision farming and
VRT 9 → 22% (CAPRI 35%), inhibitors on mineral N 13 → 4%, on manure 31%. Average gap 4.31 → 4.46: the manure
option eases the nitrogen target, herds fall a little less. Also found: the current CAPRI code applies a
homogeneous 50% cut (`pol_input/greendeal/surptot.gms`, 2023); JRC121368's tiered rule is kept, since the
report is the validation reference; CAPRI divides the surplus by *current* farmland (`e_SURTOTHa`), the model by
base farmland (`surplus_per_current_ha`, off).

**Instrument decomposition.** The nitrogen-balance target alone gives dairy −8.7% and beef animals −11.2%,
as much as the full scenario (−8.3, −9.2): the cattle gap lies inside the nitrogen mechanism, not in how the
targets combine (JRC121368: "the GNB-reduction target dominates the simulated impacts on animal herds").
Calves barely move (−1.7%) while dairy cows fall 9% and suckler cows 29%: in CAPRI calves are outputs of
cows and inputs of rearing and fattening (`INPANI_`, young animals in `SUPBAL_`). Earlier herd-link tests
showed little effect; to be re-examined against CAPRI's young-animal block.

**CAPRI's over-fertilisation limit on fertiliser technologies** (`Tot_MitFert_`) is implemented with CAPRI's
regional factors (`docs/FEED_IN_SUPPLY.md`).

**Feeding inside the supply model, as CAPRI** (`docs/FEED_IN_SUPPLY.md`) — built and validated, behind
`use_feed_in_supply` (off): all 248 regions reproduce the base; cattle enteric methane follows the feed
mix and matches CAPRI's per-head levels within 3–6% (the fixed factors were ~30% too low; EU base
enteric 114 → 170 Mt CO₂-eq). Farm-to-Fork changes are unchanged, so the enteric gap is a cattle-number
gap. CAPRI
chooses each animal's feed in the same optimisation as herds, fodder, technologies and enteric
methane (which follows the feed mix); capri-mod solves rations in a separate model. The design
reformulates it as one convex conic problem per region (Clarabel). A systematic review of the
remaining structural departures (joint modules, activity and commodity detail) runs alongside.

The coupling gaps listed below have since been closed, except where noted:

- **Prices to livestock**, **feed demand from herds**, **oilseed crushing** (oil and
  cake markets, cake feed demand): done.
- **EU feed ration**: endogenous, on by default. **Fodder balance**: CAPRI's equality.
- **Land market**: CAPRI's land-type variables and land-market costs, on by default.
- **Ammonia**: CAPRI's emission factors per region, replacing a proxy.
- **EU market prices**: reported as producer prices with the Armington premium; a
  demand bug that cut tariff-protected demand at base is fixed.
- **Manure trade**: endogenous market available as an option, off by default
  (`docs/MANURE_MARKET.md`).
- **Nitrogen target as CAPRI applied it**: JRC121368's tiered rule, with the cut capped at
  the EU average (36%) in the nine highest-surplus regions, as the report states.
- **Manure trade**: JRC121368 ran without it ("all manure generated in a region has to be
  used within that region"), as the default here.
- **CAPRI's ammonia technologies inside supply: done, on by default.** Rebuilt from CAPRI's code and
  data (costs, initial and maximum shares matching CAPRI's runs, effects) and adopted under the
  nitrogen price as in CAPRI's Farm-to-Fork run; since October 2026 on CAPRI's groups, calibration and
  cascade (above): ammonia −34.9% (CAPRI −33%).
- **Still to do among CAPRI's technologies**: livestock-feed and genetics options (milk yield,
  ruminant efficiency, nitrate and 3-NOP additives), soil options (cover crops, peatland fallowing);
  sources mapped in `docs/MITIGATION_IN_SUPPLY.md`; all their CAPRI data files are now in the
  project. Feed additives (nitrate, 3-NOP, linseed) read: in CAPRI they are ration ingredients, so
  they go into the EU feed ration. Nitrate is added there (off until its methane and nitrogen
  effects are passed on); linseed and 3-NOP only cut methane, worthless without a carbon price. In the full Farm-to-Fork run nitrate barely
  enters the rations (no effect), so it stays off. *Superseded by Sprint 9g: linseed and nitrate as CAPRI's
  supply-model columns (they also supply nutrients), low-N feed likewise; 3-NOP registered.* Genetics: negligible in CAPRI's run (no line in the report's Table 18) - not
  pursued; the enteric-methane gap is a cattle-response gap. Diagnosis under way: the split between
  fertiliser (−38% vs CAPRI ~−40%) and manure (−10.5% vs ~−13%) is close, but pigs carry their share
  of the manure cut while poultry and cattle give way about half as much as in CAPRI. Lead: bulls and
  heifers carry implausible margins (about €5,000 per head) and nitrogen per head (118–197 kg), which
  protect them from the nitrogen target. Checked against CAPRI (Brittany): our bull head counts are
  far below CAPRI's activity levels (per-head figures inflated several-fold) and fattening costs omit
  young-animal purchases and much of the feed (margin 88% of revenue vs CAPRI 15–34%). Fixed (revenue
  and costs now CAPRI's total output and inputs / model heads); results barely move, since PMP responses
  depend on curvature, not margins. Mechanism found: in about half of the cattle regions the nitrogen
  target is met cheaply (nitrogen price €0.4–1/kg) and cattle there grow 3–5%, offsetting cuts elsewhere;
  where the target binds hard, dairy falls 10%, as in CAPRI. Targets there match CAPRI's, so the
  compliance is genuinely cheap; the expansion is the issue. Lead: rations price home-grown fodder at
  its base value, so maize-fed dairy is shielded from scarcer land (silage maize +7.8% under Farm-to-Fork);
  CAPRI values fodder at its balance shadow price.
- **Market solver**: market equilibrium now solved as a system of equations with a Newton-type
  method (SciPy `root`), as CAPRI does with CONOPT: markets clear to 10⁻¹³ instead of 1%.
- **Biofuels (crushing stage 4, October 2026)**: CAPRI's biofuel feedstock CES inside the market at
  fixed biofuel output (as CAPRI's scenarios without endogenous biofuel markets); the post-solve biofuel
  module is retired. Since Sprint 9c biofuel output, use and trade are endogenous too (`BIOF_M`, the star 3.0
  default; docs/BIOFUEL_MARKET.md).
- **Dairy processing (October 2026)**: CAPRI's DairyNQ_ / FatsProtBal_ block per member state inside the
  market; raw milk priced by its fat and protein; sheep and goat milk is raw milk; world dairy-product
  balances from CAPRI's FAO_agg. See `docs/DAIRY_PROCESSING.md` for its effect on the milk price.
- **Cattle genomics (October 2026)**: CAPRI's breeding options (higher milk yield, ruminant feed efficiency)
  inside the regional supply models with CAPRI's calibration; adoption follows the nitrogen price (efficiency
  33% vs Table 17's 9%, milk yield 3.3% vs 15%).
- **Dairy Stage 3 (October 2026)**: feed demand for dairy products from calves (FMIL) and CAPRI's cross-price
  food demand; the dairy block remains opt-in (raw milk +30% vs +1.5%).
- **Reported EU prices**: the EU price carried the Armington premium twice in the report (supply saw it
  once); fixed — every reported EU price change of a premium commodity was too high.

Current 2030 Farm-to-Fork results against CAPRI:

| 2030 Farm-to-Fork (JRC121368 targets) | capri-mod | CAPRI |
|---|---|---|
| Cereal / oilseed / vegetables-and-permanent-crops price | +10.5 / +16.7 / +16.3% | +8 / +11 / +15% |
| Beef / pork / poultry / milk price (EU producer prices) | +11.8 / +27.9 / +23.8 / +1.5% | +24 / +43 / +18 / +1.5% |
| Dairy cows / beef animals / pigs / poultry / sheep | −6.2 / −8.0 / −21.4 / −12.9 / −10.2% | −10 / −18 / −14.5 / −16.5 / −9.5% |
| Cereal / oilseed / vegetables-and-permanent-crops production | −14.9 / −16.6 / −11.6% | −15 / −15.5 / −12% |
| Nitrogen surplus / fertiliser N₂O | −38.5 / −37.8% | −33.5 / −40.4% |
| Enteric / manure CH₄ / non-CO₂ GHG | −8.2 / −14.2 / −10.8% | −14.6 / −12.2 / −14.8% |
| Ammonia | −34.4% | −33% |
| Beef production | −7.1% | −14% |

Default model (land market, feed ration and CAPRI's ammonia technologies on, manure market off); full EU, converged
in 7 iterations, about 8 minutes. Mean absolute deviation from CAPRI over the twenty
indicators above, ammonia excluded: 4.5 points over twenty indicators, 4.3 with ammonia included (5.5 before CAPRI's over-fertilisation limit; 4.51 before CAPRI's livestock elasticities and young-animal markets). Adoption of CAPRI's options against JRC121368 Table 17 (baseline → Farm-to-Fork, share of animal units weighted by excreted N or of crop area): low-emission housing 16 → 19% (CAPRI 12 → 12), covered storage 15 → 36% (14 → 34), air purification 0 → 14% (0 → 10), nitrification inhibitors 0 → 13% (0 → 18), precision farming 0 → 9% (0 → 35).

The sections below are the review as originally written.

## Summary

Two questions: are the modules coupled as tightly as they should be, and does
the model contain more product concepts than the 33 market-clearing
commodities? **Yes to both**, and the two are connected: most coupling gaps sit
exactly where a product concept exists in one module but has no market — or no
price — in another.

The model knows **34 crop and 11 animal activities, 11 feed items, 3 nutrients,
5 land types and the outputs of 5 processing chains** (sugar, three oilseeds,
milk). Only **33 commodities clear markets**. Several concepts are therefore
represented by a fixed coefficient, a proxy price, or a module that runs after
the solve instead of inside it. Three gaps matter most for the Farm-to-Fork
results:

1. **Market prices did not reach livestock** (fixed while writing this review).
   The market-to-farm price signal was keyed by market commodity (`PORK`,
   `MILK`), while farm margins look prices up by activity (`PIGS`, `DCOW`). No
   animal ever saw a meat, milk or egg price change; rye and oats never saw the
   cereal price. Under Farm-to-Fork the pork price rose 7% and pig farmers did
   not see it.
2. **Feed demand is not linked to herds.** The market module never refers to
   animals or feed. When the pig herd falls 16%, the market does not see the
   cereals and protein those pigs no longer eat. This very likely explains why
   cereal prices rise +13% here against CAPRI's +8%.
3. **Oilseed processing has no market.** Oils and meals are defined
   (`PROCESSING_OUTPUTS`) and soybean meal is the main protein feed, but neither
   oils nor meals clear a market; meal prices are proxied from bean prices.
   Protein-feed price changes, which drive pig and poultry costs, are therefore
   approximate, and oilseed prices miss the oil–meal value split.

## How the modules are coupled today

| From → to | What passes | Strength |
|---|---|---|
| Supply → market | regional outputs → 33 EU market quantities (the "bridge") | two-way, outer loop |
| Market → supply | relative price change per commodity | two-way, outer loop — **livestock disconnected until now** |
| Land market ↔ supply | land expansion vs land shadow price, per region | two-way, inside each iteration |
| Nitrogen target ↔ supply | balance price vs balance constraint, per region | two-way, inside each iteration |
| Environment → supply | each activity's nitrogen-balance coefficient | tight: the constraint uses the environmental module's own balance |
| Supply → environment | activity levels, realised yields, fertiliser factors | post-solve accounting (consistent with the constraint) |
| Feed requirements → supply | CAPRI's requirements per head in the rations | inside the supply models |
| Fodder balance | **none** (herds not tied to fodder area) | regional fodder use = production | **add** — before wiring the ration |
| Feed | rations chosen inside the supply models; bulks priced by the market | inside (the post-solve feed module retired, Sprint 9i) |
| Biofuel block | feedstock demand ↔ feedstock prices; biofuel supply, use, trade | **inside the market** (CAPRI Biof_ CES; SupplyBiof_, biofDem_, bilateral trade with `BIOF_M`) |
| Abatement ↔ supply | technology adoption, emission tax | inside the supply models (Sprint 9g/9i) |
| Supply → market (feed demand) | the supply models' feed bulks per member state | two-way (`feedShareEqu_`, `feedBlkPrice_`; Sprint 9d, 9h) |

## Product concepts and their status

| Concept | In the model as | Clears a market? |
|---|---|---|
| Cereals, oilseeds, sugar beet, potatoes, pulses, fruit and vegetables, wine, olives (20 crops) | activities mapped one-to-one to markets | yes |
| Rye, oats | activities | yes — in the other-cereals market (OCER + RYEM + OATS), October 2026 |
| Other crops (`OCRO`, `OIND`, `NURS`, `FLOW`, `TAGR`, `TOBA`, `COTT`, `OFIB`) | activities | no — exogenous prices |
| Fodder (`GRAS`, `MAIF`, `OFOD`) | activities and feed items | no market; non-tradable in CAPRI too, priced through the feed balance (the `OFOD_M` placeholder market was removed) |
| Milk → nine dairy products | CAPRI's dairy block (NQ, fat and protein balances) per member state | butter, SMP, cheese, whey on world markets; fresh products, cream, concentrated milk, WMP, casein clear in the EU; raw milk priced by fat and protein |
| Beef, pork, poultry, eggs, sheep and goat meat | animal outputs summed into markets | yes — prices did not reach farms until this turn |
| Sugar | sugar beet × CAPRI's member-state sugar per beet (PRCY × processed share); beet price follows sugar | yes (white sugar; beet has no market, as in CAPRI) |
| Oils (rapeseed, sunflower, soybean) | crushing inside the market | yes — RAPO, SUNO, SOYO markets |
| Meals (soybean, rapeseed, sunflower) | `PROCESSING_OUTPUTS`, feed items | **no** — price proxied (0.89 × soybean price) |
| Mineral fertiliser N | derived from crop need minus manure | no price formation (fixed unit cost) |
| Manure | regional supply, traded at fixed base shares | no — trade is not price-driven (CAPRI's is endogenous) |
| Land | regional land market with rents | regional, yes |
| Feed energy and protein | requirement table per head | no feed balance in the market |
| Biofuels | feedstock demand, biofuel supply, use and trade, DDGS market and feed, non-fuel processing (`BIOF_M`, default) | glycerine fixed at 600 EUR/t (as CAPRI); FPRI and fish meals in the FPRO bulk at reference prices |

## Simplification register

Project rule: **no fixed coefficients, proxy prices or post-solve modules unless
CAPRI does the same.** Every current exception, against what CAPRI does:

| Item | This model | CAPRI | Status |
|---|---|---|---|
| Protein-feed price | CAPRI's FPRO bulk price per member state (CES rho 6 over cakes, DDGS, pulses, oils, milling by-products; Sprint 9d) | oilseed-cake and DDGS markets | *done* |
| Feed-cereal price mix | CAPRI's FCER bulk price per member state (CES rho 6 over CAPRI's 2030 feed use; Sprint 9d) | `feedBlkPrice_` | *done* |
| Feed demand, non-EU | feed part responds to feed prices with CAPRI's `p_ElasFeed` (own and cross) | `p_ElasFeed` | *done* |
| Feed demand, EU | rations chosen inside the supply models; all five bulks (FCER, FPRO, FENE, FOTH, FMIL) per member state split into products (`feedShareEqu_`; Sprint 4, 9d, 9h) | same | *done* |
| Energy-rich feed price | FENE bulk index per member state; FENI and FPRI traded markets with EU output from `MaprFeed_` (Sprint 9h, docs/FEED_MARKETS.md) | same | *done* (MOLA, STAR at reference prices) |
| Manure trade | CAPRI's country pools, transport costs and regional export/import costs (`manureTradeNew`; default on, off in Farm-to-Fork as JRC121368) | same | *done*: base trade CAPRI's 2030 reference per region, only in runs with trade (Sprint 9j); trade columns and CAPRI's crop-need row (NUTNED_) in every EU solve, cost = pool price as CAPRI's calibrated constants (Sprint 9k) |
| Milk products | CAPRI's dairy processing with fat/protein balance (EU-common fat, protein and milk price ratios) | per member state | *done* (registered: EU-common ratios) |
| Sugar | CAPRI's member-state sugar per beet (2030 reference); beet price follows sugar | PRCY per member state; `set_prices.gms` | *done* |
| Olives, other oilseeds | olives reach the market as olive oil (CAPRI yields); other oilseeds a pooled market | CAPRI trades olive oil; other oilseeds not bilaterally | *done* for olives; other oilseeds registered |
| `FATS`, `OFOD_M` markets | removed (no supply, no use, invented data) | no such products | *done* |
| World market base | CAPRI's market results of the run's year (bilateral market); FAO_agg base for pooled markets | CAPRI market data | *done* (raw milk, other oilseeds pooled) |
| Trade structure | CAPRI's: market price per region, two Armington nests over CAPRI's bilateral flows, transport costs, tariffs, EU TRQs | same | *done* (Sprint 8m; registered: global quotas, commitment terms) |
| EU oil and cake supply | crush × yields, crush driven by the margin | crush × yields | *done* |
| EU tariffs | CAPRI's 2017 total protection on EU imports (`ImportP/(Fob+TCost)−1`) | same | *done* — levels barely affect results (constant wedge) |
| World prices | now CAPRI's base world prices (`FAO_agg` `PMRK`); five codes without an unambiguous counterpart kept | `FAO_agg` `PMRK` | *done* (5 codes to resolve) |
| Mineral-fertiliser substitution | linearised around the base | allocation inside the supply model | *equivalent at the margin*; revisit if large changes |
| Abatement technologies | endogenous in the supply models (ammonia, fertiliser, breeding, low-N feed, supplements, cover crops, histosols); CAPRI's emission tax inside them (Sprint 9i), ammonia options, manure trade (Sprint 9k) fertiliser options (Sprint 9l) and inhibitors on manure (Sprint 9m) priced by their emissions; post-solve reports retired | endogenous; `ghgTax` in the supply model | *done* (tax coefficients at the baseline solution: registered) |
| Feed module | retired (Sprint 9i): feeding inside the supply models | feed balance inside the supply model | *done* |
| Biofuel module | feedstock CES and endogenous biofuel markets in the market (`BIOF_M` default; off = fixed output) | same | *done* |
| Broiler birds per place | removed — feed per head now from CAPRI totals | — | *done* |
| Livestock manure and feed per head | CAPRI 2017 totals ÷ this model's herds | per-unit coefficients on CAPRI units | *equivalent* (totals match) |

## Findings, ranked by effect on results

**1. Price signal not reaching livestock — fixed.** An activity → market map
(`ACTIVITY_PRICE_SOURCE`) now carries each commodity's price change to the
activities that earn it. Base year untouched (no signal at base).

**2. Feed demand independent of herds — fixed.** Each feed cereal's EU demand
now has a feed part that follows total cereal feed (herds × feed table) at the
cereal's feed share from CAPRI's 2030 balance (wheat 43%, barley 69%, maize 81%,
other cereals 63%). Cereal price under Farm-to-Fork +13.8% → +10.2% (CAPRI +8%).
*Original finding:* In CAPRI,
feed demand is derived from animal numbers and rations; here it is a fixed part
of each commodity's demand curve. Effects: cereal and protein prices overshoot
when herds shrink; the herd–crop feedback loop (fewer animals → cheaper feed →
partial herd recovery) is missing. *Fix*: derive EU feed demand per commodity
from herd sizes × the feed table (already in the model) and make it the feed
component of market demand, calibrated so base demand is unchanged.

**3. No oilseed crushing.** *Fix*: add oil and meal markets with fixed
extraction rates (as for sugar) and a crushing margin, so oilseed prices follow
the joint value of oil and meal and meal prices are formed, not proxied.

**4. Side modules outside the loop.** The feed and biofuel modules run after the
solve and do not feed back. Once finding 2 is fixed, the feed module's balance
could become the feed-demand source. Abatement adoption could enter the supply
model as CAPRI's reference run does ("endotech").

**5. Missing market links for minor crops — fixed (October 2026).** Rye and oats produced output that
reached no market. *Fix*: aggregate them into the other-cereals market (as
CAPRI's market aggregates), calibrated at base.

**6. Fixed processing coefficients.** Milk products by fixed shares, sugar by a
fixed extraction rate. Adequate for most uses; CAPRI's dairy fat/protein
balance matters only for dairy-specific questions.

**7. Units and scales across module boundaries.** A recurring source of error:
revenues per head computed in one place from price × yield and in another from
CAPRI's market revenue; livestock "head" meaning places in one table and birds
in another. Each module boundary should carry an explicit unit, and tests should
check that the same quantity computed by two modules agrees.

## Recommended order

1. ~~**Feed demand from herds**~~ — done.
2. **Oilseed crushing** (finding 3) — completes protein-feed prices.
3. **Rye and oats into the other-cereals market** (finding 5) — small.
4. **Abatement into the supply model** (finding 4) — needed to mirror CAPRI's
   reference run with endogenous technologies.
5. A **boundary-consistency test suite** (finding 7) — now the priority for
   livestock: every per-head coefficient (feed, manure, revenue, costs) must use
   the same unit as the herd (census stock), not CAPRI's production units.
