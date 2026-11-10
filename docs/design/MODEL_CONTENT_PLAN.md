# Model content plan: market regions, ports, non-EU supply units, S1/S2, step G, structural gaps

Drafted 2 November 2026 from the design notes on branch manifest-sql. Read-only:
nothing was run. This plan puts the upcoming model-content work in one place: the market on CAPRI's 45 market regions,
the ports onto those regions, the 29 supply units outside the EU, S1/S2 (with DEP-42), step G (G2b, G2d, G2f, G2g; G3
on standby) and the remaining structural gaps S3, S5, S6, S7, S9, S10, S11.

**Agreed order (the project lead's decisions, as given for this plan).** (1) Finish the refactor: stage 3 N6, stage 4
second half, stage 5. (2) Full scenario runs. (3) The market move to CAPRI's regions (RM, 45 market regions; RMTP, 42
policy blocks). (4) The ports onto those regions. (5) The 29 non-EU supply units. DEP-42 (OFOD as one
crop-diversification group) is kept until S1/S2 splits OFOD (decision of 2 November 2026). The notes do not place S1/S2,
step G's G2 stages or the structural gaps in this sequence, except as stated in each section.

**Decisions of 2 November 2026 (evening), the project lead.** The order above is kept; meanwhile the market move's data
preparation that touches no model code goes ahead (the sim_ini parameter extract to CSV, stage 1's region files). The
2017 market year is rebuilt on RM in stage 1; CAPRI's TARV tariffs replace tariffs.csv in stage 2; the young-animal
timing is fixed in stage 2 in the current market solve, and G2g later writes the same markets as G3's equations; the
Farm-to-Fork / Green Deal gates come after stages 1-4 and after stages 5-7. Items 1-3 of section 14 are decided.

This order is later than the notes': ARCHITECTURE_REFACTOR.md §3 ("Stage 3's gates") and MARKET_REGIONS_INVENTORY.md §7
put the market move right after refactor stage 3. The project lead's decision of 2 November 2026 (refactor through
stage 5, then the full scenario runs) comes after them; AR §3 is updated with this plan.

**Conventions.** "[I]" marks my own inference, not stated in the notes. "[own check]" marks a fact I checked in the
repository or in CAPRI's GAMS for this plan (git, file listing, grep, or a line read). Everything else is cited to a
note and section. Short names for the notes:

| Short | Path in the repository |
|---|---|
| MRI | docs/design/MARKET_REGIONS_INVENTORY.md |
| G3I | docs/design/G3_MARKET_INVENTORY.md |
| GR | docs/design/G_REVIEW_2026-11-01.md |
| MID | docs/design/MARKET_IPOPT_DESIGN.md |
| SND | docs/design/SUPPLY_NONEU_DESIGN.md |
| RUI | docs/design/REGIONAL_UNITS_INVENTORY.md |
| S12 | docs/design/S1_S2_DESIGN.md |
| SGP | docs/design/STRUCTURAL_GAPS_PLAN.md |
| AR | docs/design/ARCHITECTURE_REFACTOR.md |
| REG | docs/CAPRI_DEPARTURES_REGISTER.md |
| DFC | docs/DEPARTURES_FROM_CAPRI.md |
| KI | docs/KNOWN_ISSUES.md |
| N6 | docs/design/N6_CODE_TABLES.md (on branches n6-code-tables and n6-nurs only) |

CAPRI's GAMS source is cited as "gams/" (the project lead's CAPRI installation, not in the repository).

---

## 1. The market on CAPRI's 45 market regions

**What it is.** The market model moves from capri-mod's 28 regions (29 with `market.eu_blocks`) to CAPRI's 45 market
regions RM, with tariffs and quotas on CAPRI's 42 policy blocks RMTP and the 80 behavioural regions RMS mapped by
RMS_TO_RM (MRI intro, §1.1-1.2). In scope here, as listed: the 2017 market year on RM, the EU's quotas against MER
(DEP-41), CAPRI's tariff values (TARV) and the young-animal timing.

**CAPRI's form.** Sets RM, RMTP, RMS, RMS_TO_RM, RM_TO_RMTP in sim_ini_21730_1.gdx (MRI §1.1). EU_WEST and EU_EAST as
market blocks in gams/aggregation/defaultA.agg l. 5, 56 ff. [own check]. RMTP = RM minus ARG, BRA, URUPAR, A_EU_WEST,
A_EU_EAST, plus MER and EU (MRI §1.1). Bilateral TRQs per (RMTP, RMTP1) pair: trqSigmoidFunc_, gams/arm/market_model.gms
l. 3275 [own check]; import prices per pair: impPrice_ l. 2849 (G3I, Armington table).

**What exists.**
- The inventory: region-keyed files (MRI §2), code that depends on the region set (§3), result effects (§4), a staged
  plan (§5), decisions (§7).
- CAPRI's sets as CSV in capri_reference/sets/simini_21730/; capri_data/shared/rms_to_rm.csv equals sim_ini's
  RMS_TO_RM (MRI header).
- Extracts with the two EU regions for both years: capri_data/sources/market/bilateral_dataout_2017_eu2.csv.xz and
  _2030_eu2.csv.xz [own check]. The 2030 `_eu2` extract equals p_tradeFlows "CAL" over all 20,705 RM pairs (MRI §2.1).
- The `market.eu_blocks` option, with a blocks branch in every EU27-specific code path (MRI §3.3); default false
  (capri_mod/settings/defaults.toml l. 249 [own check]).
- The Western Balkans' food demand moved from ROW to WBA: done 1 November 2026 on k79-amm-resolve (MRI §7 item 5),
  gated in gate 14 (AR §3, "Stage 3's gates"); that branch is merged into manifest-sql [own check].
- DEP-40 kept with its note (MRI §7, 2 November; REG DEP-40).
- Not started: no shared/market_regions.csv, policy_blocks.csv or rm_to_rmtp.csv exists (stage 1's files) [own
  check]. I found no extract of sim_ini's parameters (as opposed to its sets) under capri_data or capri_reference, by
  file name [own check].

**Steps still to do** (MRI §5, with the decisions of MRI §7):
1. Stage 1 (move): CAPRI's region lists as data, built from sim_ini through a builder; one RM-to-model-region grouping
   step in recalibrate_trade_2017 used by about 20 builders; remove the orphan candidate shared/trade_flows_2017.csv.
2. Guard `definitions.is_eu` / `capri_ms` so a market code never passes through them (BEL, BGD, SKOR read as EU
   member states by their first two letters; MRI §1.2, §7 item 1).
3. Stage 2 (behaviour, DEP-3): the EU as A_EU_WEST + A_EU_EAST only; the single-EU branches deleted; feed-bulk prices
   per block (CAPRI's feedBlkPrice_, gams/arm/market_model.gms l. 951-962, cited in MRI §2.2); EU balances per block
   from member states; **the young-animal markets solved inside the market solve in this stage** (MRI §7 item 7).
4. Stage 3 (behaviour): ROW split into its 17 RM; codes renamed to CAPRI's RM codes (MRI §7 item 1); tests' region
   names updated (6 files, MRI §3).
5. "EU27" kept in the reports as the sum of A_EU_WEST and A_EU_EAST (MRI §7 item 2).
6. The 2030 market built from sim_ini, extracted to CSV; dataOut kept for cross-checks (MRI §7 item 4).
7. The 2017 market year rebuilt on RM from market_base_1717 (MRI §7, 2 November).
8. CAPRI's DATA(RM, "TARV", XX, "CAL") replaces the derived policy/tariffs.csv, after a documented comparison (MRI §7
   item 6). The stage for this is not stated in the notes.
9. DEP-41 (EU quotas against MER): fixed by the move, "where quotas sit on RMTP" (MRI §7 item 5; REG DEP-41). In the
   staged plan, MER is restored in stage 4, with the bilateral TRQs per RMTP pair (MRI §5). [I] So DEP-41 closes with
   the first port (section 2), not with stages 1-3.

**Dependencies.** The refactor first (agreed order). G3 and the ports come after the move (MRI §7 item 3). The 29
non-EU units come after it (MRI §7, 2 November). [I] Stage 2's young-animal fix overlaps G2g, which lifts the
young-animal markets into the market NLP (G3I, "Young animals"); the notes do not say whether stage 2 does it in the
current fixed-point solve or as part of G2g.

**How it is checked** (MRI §5): stage 1, every rebuilt file identical to today's (as tools/check/compare_rekeyed.py did
for the regional units); stage 2, an `eu_blocks = true` run on today's code reproduced exactly before branches are
deleted, then the market alone at CAPRI's 2030 CAL supply against DATA / p_tradeFlows "CAL" per RM, the market
Hessians measured per block (about 50 minutes per reference baseline, RUI §4), a mini-EU run; stage 3, the base
reproduces CAPRI's 2030 calibrated market for all 45 RM, a mini-EU run. The Farm-to-Fork / Green Deal gate per batch
as the project lead decides; suggested after stages 1-4 and again after 5-7 (MRI §5).

**Expected effect** (MRI §4). Renaming and regrouping: no change (§4.1). EU as two regions: Farm-to-Fork deviation
4.22 -> 4.65 when tried (§4.2 item 1, citing DFC). ROW split: at the base nothing should move; in scenarios 23 RMS
respond to their own RM's prices; the flows between ROW's members are 49,871 kt of 1,234,408 kt (4.0%) in the 2030
extract, and ROW takes 27% of capri-mod's inter-region imports (§4.2 item 2). Base data change for feed-bulk prices,
FPRI's world price and the EU blocks' balances (§4.2 item 8). Size: 20,705 product flows at CAL against 11,340 today
(§4.2 item 9). Effort, "an estimate only": stage 1 one to one and a half days, stage 2 one to two days plus the
Hessian measurements, stage 3 one to two days (MRI §5). Risks listed in MRI §5: solve convergence and run time at 45
regions before G3; DEP-5's [0.2, 5] factor on 17 new regions; region-keyed results breaking.

**Open decisions.** None of MRI §6's twelve questions is left open (MRI §7). Not stated in the notes: the stage of the
TARV switch and of the 2017 rebuild; how stage 2's young-animal fix relates to G2g.

**Decided 3 November 2026 (the project lead).**
- Checks. After each behaviour change: a mini-EU run compared with the previous one, with its mean absolute deviation
  from CAPRI, plus the tests of the changed parts and the generated-file checks; commits stay local. The full suite at
  the end of each block (market stages 2-3, the ports, the 29 non-EU units), then a push to dev. The Farm-to-Fork and
  Green Deal gates once, after S1/S2 (with DEP-42).
- FPRI's world price (build_world_prices, the export-weighted market price of CAPRI's 2017 exporters; FAO_agg has no
  World PMRK for FPRI): kept on the single-EU 2017 files until stage 3 (250.84 EUR/t); in stage 3, every CAPRI market
  region an exporter, the two EU blocks included and their trade with each other counted (244.57 EUR/t on today's
  regions, -2.5%; leaving out West-East trade would give 257.24, +2.6%). The single-EU files, and the renaming of the
  `_eu2` files to plain names, wait for stage 3 too.
- Tariffs (task 301, docs/design/TARV_COMPARISON.md): tariffs.csv stays in stage 2. CAPRI's TARV, TARS, bilateral
  TRQs and preferences come in with the ports (stages 4-7), as CAPRI's bilateral wedges on the import price, with
  CAPRI's Armington and producer prices as the reference price levels (AR 5.1, M1). This replaces the decision of
  2 November (TARV switch in stage 2).

**Sources.** MRI §§1-7; REG DEP-3, DEP-40, DEP-41; RUI §4; AR §3.

---

## 2. The ports onto CAPRI's regions: quotas, levies, entry prices, land and yield block

**What it is.** The policy and land equations of CAPRI's market that act in its 2030 data and that capri-mod lacks or
has in another form: bilateral TRQs for every importer, global (erga omnes) TRQs, flexible cereal levies, entry prices
of fruit and vegetables, and the market's land and yield block for the behavioural regions (G3I, "What CAPRI's 2030
data activate"; MRI §4.2 items 3-7).

**CAPRI's form** (gams/arm/market_model.gms, lines checked [own check]):
- bilateral TRQs: trqSigmoidFunc_ l. 3275, tarSpec_ l. 3292, tarAdval_ l. 3417; the fill from TradeFlowsAgg_ l. 3106
  (G3I);
- global TRQs: TRQImports_ l. 3142, tarSpecW_ l. 3399, tarAdValW_ l. 3475;
- flexible levies: FlexLevyNotCut_ l. 3236, FlexLevy_ l. 3258, prefTriggerPrice_ l. 3369; entry prices:
  EntryPriceDriver_ l. 3176, tarSpecIfEntryPrice_ l. 3204;
- land and yields: LandSupplyMNL_ l. 1737, Yield_ l. 1795, and LndSupplyEqualsDemand_, rentFromProdpriceLand_,
  LandAgrFromYld_, ScaleLandAgr_ (G3I, "Land (supremaMrk on)"); supremaMrk on by default
  (gams/capmod/set_global_variables.gms l. 386 [own check]). Yield_ is in the model whatever supremaMrk (GR Q4).

**What exists.**
- The check of which blocks CAPRI's 2030 data activate: flexible levies yes (30 entries), entry prices yes (EU and UK),
  global TRQs yes, non-EU bilateral TRQs yes (MED, MOR, NO000000, RUS, TUR at "CAL"), land and yields yes (45
  behavioural regions); intervention stocks and subsidised exports no (G3I).
- Counts from sim_ini: EU 81 bilateral quotas against 22 exporter blocks; 70 global quotas for 12 importers, of which
  CH, MED and TAW sit inside capri-mod's ROW today (MRI §4.2 items 4-5).
- The registered departures these ports remove: DEP-33 (no global TRQs), DEP-34 (EU's TRQs only), DEP-35 (TRQs summed
  per model exporter), DEP-36 (ad valorem tariff frozen at base FOB), DEP-41 (EU x MER quotas) (REG).
- G2a's TRQ sigmoid as a CasADi expression (trade_trq_function; MID §6 item 1). GR Q3.a11: G2a is reusable only for
  its CES and TRQ sub-expressions.

**Steps still to do** (MRI §5, stages 4-7):
1. Stage 4: bilateral TRQs per (RMTP, RMTP1) for every importer with quotas (EU, MED, MOR, NO000000, RUS, TUR), MER
   restored, fill = TradeFlowsAgg_, tarAdVal_ on the current price (DEP-34, -35, -36, -41).
2. Stage 5: global TRQs, TRQImports_, tarSpecW_, tarAdValW_ for the 12 importers (DEP-33).
3. Stage 6: flexible levies (p_flexLevy, MinBordP) and entry prices (p_entryPriceFac, TriggerP).
4. Stage 7: the market's land and yield block for the RMS without supply models.
GR's recommendations for this code: write tarSpec_ in levels with CAPRI's parameters and check its base value against
v_tarSpec (Q3.a8); split the specific and ad valorem parts and write tarAdval_ in CAPRI's form (Q3.a5); copy the
smoothing constants exactly (ncpcm in TRQImports_, tarSpec_, tarAdval_ with different constants; Q1.3).

**Dependencies.** The move, stages 1-3 (MRI §7 item 3). Stage 5 is possible only on RM, because CH, MED and TAW are
inside ROW today (MRI §4.4). [I] Stage 7 touches DEP-7 (non-EU supply with land rents held); MRI §4.4 lists DEP-7 as
unchanged by the move, so the relation is not stated in the notes. The notes do not say whether the ports are written
in the current fixed-point market code or directly as G3's defining equations.

**How it is checked** (MRI §5): stage 4, CAPRI's quota fills (p_trqBilat ImportsR) and import prices (p_impPrice
"CAL") per pair at the base, equation-level unit tests against market_model.gms l. 3275-3475, mini-EU run, F2F/GD gate
(batch 1-4); stage 5, base fills against p_trqGlobl; stage 6, base tariffs against p_flexLevy "CAL"; stage 7, base
against DATA(RMS, LEVL/YILD, "CAL"); mini-EU after each; F2F/GD gate (batch 5-7). GR Q5.2 Test C: test TRQs with fills
in [0.9, 1.05], where the slope-200 sigmoid is steep (only 3 of 67 quotas sit there at the 2030 base).

**Expected effect.** The EU's MER quotas are not binding at the 2030 base (imports 45%, 11%, 5%, 61% of the quotas;
REG DEP-41). CAPRI's EU beef erga omnes quota is 95% filled at the 2030 reference (GR Q3.a4, citing
KNOWN_ISSUES_REGISTRY_LOG.md l. 1137). DEP-36's error is proportional to (TaMFN - TaPref)/100 x the market price
change (GR Q3.a5). Otherwise not stated in the notes. Effort, "an estimate only": stage 4 two to three days, stage 5
about two, stage 6 one to two, stage 7 three to five; stages 1-7 together roughly 12-18 working days without gate runs
(MRI §5).

**Open decisions.** Not stated in the notes: whether the ports precede G3 or are written as G3's equations; the
treatment of the market's land-use-change estimation (luc_market, on with REPORTS_ENV; G3I findings), which is not
in this list.

**Sources.** MRI §4.2, §4.4, §5; G3I "What CAPRI's 2030 data activate", "Tariffs and TRQs", "Flexible levies and entry
prices", "Land (supremaMrk on)", "Yields"; GR Q1.3, Q3.a4-a8, Q5.2; REG DEP-33 to DEP-36, DEP-41.

---

## 3. The 29 supply units outside the EU (UK 11, Turkey 12, Western Balkans 6)

**What it is.** Regional supply models for the 29 units CAPRI's Green Deal 2030 run solves beyond the model's 221
(EU27 215, Norway 6): UKC00000 ... UKN00000, TR100000 ... TRC00000, AL, BA, CS, KO, MK, MO (SND §1; RUI §1). Their
market supply then comes from their supply models (RMSSUP), and DEP-7's "no supply models" part goes (REG DEP-7).

**CAPRI's form.** Per-country switches %CountriesNO000000% ... %CountriesTUR% (gams/capmod/define_regional_sets.gms
l. 40-77; SND §3, lines checked [own check]); CAPRI's rules for the units' missing data in SND §5 (winter cover,
tillage, organic soils, irrigation, labour, PMP terms, ammonia farm structure, AD, Turkey's prices, CEILVAL, each with
file and lines).

**What exists.**
- The data inventory of 77 builders with a verdict each (SND §2): 41 ready, 7 ready but for Turkey's code, 7 need
  their country list changed, 12 need data CAPRI's files lack for some units, 10 EU-only by nature.
- SND §3 order: step 1 (builders take the EU from eu_market_blocks.csv) done; step 2 (the setting
  `run.supply_countries_outside_eu`, default ["NO000000"], and the outside-EU test by `is_eu`) done.
- Step 3, part one (Turkey as TUR and the Western Balkans in the member-state code table): in manifest-sql (commit
  eeecdfe has an equivalent there) [own check].
- Step 3, part two (regional_units.csv with all 250 units): on branch noneu-step3, commit dfa8c54, not merged
  [own check]. Its message says every unit has CAPRI 2017 activity levels in the CAPREG dumps and that the core
  supply tables do not hold the 29 units yet. regional_units.csv has 221 data rows in manifest-sql and 250 on
  noneu-step3 [own check].
- CAPRI's rules for the missing data read (SND §5); their port not done.
- Decisions: the per-country setting (SND §3); mitigation aligned with CAPRI's Green Deal file when the 29 come in, for
  Norway too (SND §4); the producer-price fallback (SND §4); "as CAPRI" for the missing-data rules (SND §5).

**Steps still to do** (SND §3, "The order of the work"):
1. Finish step 3: merge build_regional_units on 250 units.
2. Step 4: the ready builders on the 250 units.
3. Step 5: the country lists of SND §2 (7 builders).
4. Step 6: port CAPRI's missing-data rules (SND §5), each with file and lines; numbers in CSVs with their source.
5. Step 7: the exact-reproduction check with the default setting.
6. Step 8: the market side, SUP_NONEU one-to-many for WBA (about 10 places; SND §3, "The market").
7. Step 9: the baseline of the 29 against CAPRI's 2030.
8. Step 10: an F2F/GD gate: the full F2F and GD runs after §5's Step G (the project lead, 4 November 2026).
Also from SND §2 and §4: build_histosol to stop skipping Norway (done 4 November 2026: every supply region, the endotech
setting fallowInAllRmssup), winter cover outside the EU
as CAPRI's Green Deal file, the dumps' folder for the eight non-EU CAPREG dumps in builders.json.

**Dependencies.** After the market move (MRI §7, 2 November; AR §3). [I] The move gives WBA, TUR and UK000000 as RM
with their RMS members, which is the structure step 8 needs; the notes do not state this link. The market supply
Hessian is measured again for a new region list (RUI §4).

**How it is checked.** Exact reproduction of a default run (Norway only) before and after the data rebuild (SND §3,
"The switch", step 7); the 29 units' baseline against CAPRI's 2030 (step 9); the F2F/GD gate (step 10).

**Expected effect.** Not stated in the notes.

**Open decisions.** None open in SND §4 (all three points decided or answered). Not stated in the notes: whether the
default of `run.supply_countries_outside_eu` changes to all countries of CAPRI's Green Deal run once the units are
built (CAPRI's run solves 250 units, SND §1) [I: a question I raise, not one in the notes]. SND §5 marks two points
as inferred: Turkey's and the Western Balkans' winter-cover initial share presumably 0, and their absent CAP premiums.
Beyond CAPRI, not taken now: measured data for some fallbacks (SND §5, last paragraph).

**Sources.** SND §§1-5; RUI §1, §5 item 6; REG DEP-7; git log noneu-step3.

---

## 4. S1/S2: CAPRI's crop technologies and split activities (and DEP-42)

**What it is.** S1: CAPRI's two technologies per crop (T1 high yield, T2 low yield) instead of one activity per crop.
S2: GRAE/GRAI, OFAR/ROOF and VSET/FALL as activities of their own instead of GRAS, OFOD and SETA (S12 §1, §5; SGP S1,
S2). Splitting OFOD into OFAR and ROOF also resolves DEP-42 (OFOD counted as one crop-diversification group).

**CAPRI's form.** Technologies: capmod.gms l. 247-249, intens/techf.gms l. 39-117 (factors), fert/fertned.gms
l. 206-207 and 314-335, PMP terms in supply/pmp_terms/ (S12 §1.1-1.2). Split activities: supply/define_ngrp_sets.gms,
supply_model.gms l. 1112, 1129, 1970, 2306, 2315-2321 (S12 §1.3). Crop-diversification groups: gams/sets.gms
l. 2995-3015: cropDivGrps(AnnualCrops) = YES, so OFAR and ROOF are groups of their own; CAPRI's line excluding OFAR is
commented out [own check].

**What exists.**
- The design and the decision (S12 §5, 1 November 2026): S1 option (c), one mix column z per crop (T1 = X/2 + z,
  T2 = X/2 - z, |z| <= X/2), CAPRI's quadratic blocks and linear terms carried over by the change of variables; S2 the
  three pairs as activities of their own. Nothing implemented (S12 status line).
- Data in hand: CAPRI's 2030 quadratic technology blocks (capri_data/sources/intermediate/baseline_pmp/pmp_quad_techn_2030.csv;
  S12 §3). Not yet extracted: the linear terms per technology (capri_sources/pmp2030/pmppar_21730<CC>defaulta.txt).
  Not in any export: the factors p_technFact (fixed rules in CAPRI's code). The split activities' levels are in
  CAPREG's 2017 results and the 2030 reference (S12 §3).
- DEP-42 registered on branches n6-code-tables and n6-nurs (REG row DEP-42 there; N6 "Findings" item 1, "Decisions"),
  not yet in manifest-sql's register [own check].

**Steps still to do** (S12 §5):
1. Data first: the linear PMP terms per technology from the PMP export; the factor table with its citations (the MANN
   factor also needs p_nitrBalance's deposition and mineralisation, S12 §3); CAPREG's 2017 levels of the split
   activities.
2. S1: the mix column per crop that CAPRI gives T1/T2 (EACT and CACT without grassland; ISET and VSET with levels only);
   the factors on outputs, inputs, plant protection and nutrient need through z; the set-aside obligation per
   technology; reports with T1 and T2 recovered and weighted as CAPRI's (sol_simy.gms l. 160, 373-389).
3. S2: GRAE and GRAI replacing GRAS and its grass_z column; OFAR and ROOF replacing OFOD's fixed shares (OFAR with
   T1/T2, the legume share's N fixation and CO2 option, its weight in the ecological set-aside); VSET and FALL replacing
   SETA (FALL without fertiliser, VSET in the set-aside limit); each with its PMP terms, nutrient groups and CAPRI's
   data.
4. Register S1 option (c) as a departure of form, not of model (S12 §5).
5. With OFAR and ROOF as activities, read the crop-diversification groups from CAPRI's set and remove DEP-42 (REG
   DEP-42 on n6-nurs: "kept until S1/S2 splits OFOD").

**Dependencies.** After refactor stages 3-5 (S12 §5; AR §3 "Order and scope"). The N6 code tables (N6) carry the
crop-diversification groups and the OFOD crosswalk (OFOD = OFAR + ROOF in capri_data/codes/model_activities.csv; N6
intro). [I] S10's no-till yield effect may act through the T1/T2 split in CAPRI (KI K93: "applied directly or through
the T1/T2 split, %NoYieldEffect%"). Position relative to the market move and the 29 units: not stated in the notes.

**How it is checked** (S12 §5; SGP S1): the base reproduced exactly; crop supply elasticities against CAPRI's own
(supply_elas files); the yield and N per ha responses at the F2F and GD gates.

**Expected effect.** Intensity responses (yield, N per ha) to prices and N targets; the crop groups' marginal N need
(SGP S1); grassland and fodder N need, set-aside premiums (SGP S2). What the collapse loses: the T1-against-T2
direction, curvature d - c (AT11 soft wheat 137.6; S12 §2). DEP-42: the model's largest group can be larger than
CAPRI's where both are grown, "not measured" (REG DEP-42 on n6-nurs). Effort: "the largest single item of the plan
after the refactor of the supply code" (S12 §4, an estimate).

**Open decisions.** None stated in the notes beyond those taken on 1 and 2 November 2026.

**Sources.** S12 §§1-5; SGP S1, S2; REG DEP-9 (manifest-sql) and DEP-42 (n6-nurs); N6 "Findings", "Decisions".

---

## 5. Step G: G2b, G2d, G2f, G2g, with G3 on standby

**What it is.** Every market block written once as a CasADi function, each block's inner solves lifted into one
system, then the whole market solved by IPOPT with exact derivatives (G3) in CAPRI's own form: a square system with
every quantity a variable (MID §2, §3.1, §6).

**CAPRI's form.** m_globMarket (gams/arm/market_model.gms l. 4243 [own check]) solved as DNLP with a dummy objective
(FlipFlop_ l. 3771; SOLVE at arm/simu_market.gms l. 107), bounds widened and re-solved at most twice, a sum of
infeasibilities up to 0.1 accepted in the last iteration (MID §1; GR Q2.1). 123 equations, listed with their status in
G3I.

**What exists.** G1 (trade systems' exact Jacobian, AR §6 step G); G2a (TRQ sigmoid, built 30 October), G2c (GL
demand, built 31 October), G2e (processing and crushing, built 31 October), with a mini-EU check of G2c and G2e
(MID §6). G3I (123 equations: 20 ported, 14 ported in another form, 3 departure, 15 to check, 59 not ported, 11 off,
1 replaced). The independent review GR. IPOPT 3.14.19 with SPRAL in OpenMP built, kept for G3's NLP (MID §9.1).
Step-g branch merged into manifest-sql [own check]. G3 on standby pending the review's points (MID §3).

**Steps still to do** (MID §6, §3.1 "Next"; each G2 stage written as defining equations from the start):
- **G2b** market supply and pooled commodities: non-EU supply functions and the EU's response through the measured
  Hessian. In G3 written as ProdNQ_ itself, with the PSE/AREP terms of MILK, the CRDO oil cost and the feed-bulk
  prices, l. 1546-1572 (G3I "Market supply"; GR Q6.1). Check that the Hessian terms act on the producer-price change
  net of additive support (GR Q3.a3, inferred there). The pooled commodities are DEP-31.
- **G2d** feed, with the feed-energy price (FeedBal_) lifted as an unknown, which removes the lag on the dairy price
  (MID §8; GR Q6.6).
- **G2f** dairy blocks lifted: DairyNQ_, ProcMargM_, FatsProtBal_, now a Newton solve inside the response (G3I
  "Dairy"). GR did not review it; implicit definitions need care (GR Q1.6).
- **G2g** biofuels (11 equations "to check", G3I "Biofuels"), young animals and raw milk lifted (yaniMarket_ l. 1579,
  rmsYaniMarket_ l. 1613 [own check]).
- Before G3: CAPRI's bounds per variable (MID §3.1 "Next"); GR's corrections to the design.

**Dependencies.** G2b rests on the coupling code that refactor stage 4 restructures (MID §6 item 3). G3 after the
market move (MRI §7 item 3). [I] After the move, G3 can be written on CAPRI's sets, which GR asks for validation
(Q5.2 Test A, Q6.5). Stage 2 of the move fixes the young-animal timing (section 1), which overlaps G2g.

**How it is checked.** Each G2 stage: the CasADi residual equals the NumPy residual at random points (relative 1e-10)
and the Jacobian equals finite differences (MID §6); GR adds stress-point tests (Q5.2 Test C) and tests in the
default configuration (`market.market_supply_nq` true; GR Q5.2). G3: MID §6 item 8 says equilibrium equal to the
default solve within `market.tol` and the same or fewer outer iterations; GR Q5.1 finds this compares capri-mod with
itself and recommends G3-R (regression, equations unchanged) plus G3-C (each CAPRI-form change validated against CAPRI)
and tolerances on CAPRI's scale (1e-5 scaled residual; GR Q5.3).

**Expected effect.** "None at convergence" for the solver change (AR §6 table, step G). GR Q5.1: every move toward
CAPRI's form (bound policy, lifted lags, removed floors, global TRQs) changes the equilibrium.

**Open decisions (G3, the project lead's).**
1. Bound policy: (i) CAPRI's policy reproduced (bounds as checks, widen and re-solve at most twice, CAPRI's thresholds)
   or (ii) an elastic least-infeasibility formulation (GR Q2.4 item 3).
2. Objective: ½‖z − z₀‖² was decided on 30 October (MID §7); GR recommends a zero objective with a squareness check
   (counts and structural rank, as check_square.gms) before every solve (GR Q2.4 items 1-2). z is undefined in the
   full-variable form (GR Q2.3).
3. Validation by reproducing CAPRI's market state (GR Q5.2 Test A: CAPRI's equations evaluated at CAPRI's levels on
   its native sets; sim_ini holds the calibrated 2030 state, MRI header).
4. Also raised by GR and not decided in the notes: fudge activation as CAPRI's (off, widen, activate) or always on
   (Q1.2); variables scaled as ratios to base (Q6.4); the set structure G3 targets in production and in validation
   (Q6.5); IPOPT options and the fixed-point solver kept as fallback (Q6.3). Beyond CAPRI, for decision: a
   deterministic least-infeasibility mode and a Dulmage–Mendelsohn check before each solve (GR "Beyond CAPRI").

**Sources.** MID §§1-9; G3I; GR Q1-Q6; AR §6; REG DEP-16, DEP-31 to DEP-40.

---

## 6. S3: the fertilisation block's scaling (kappa)

**What it is.** CAPRI applies its need multiplier to the need alone; capri-mod applied it to the need net of the
permanent crops' own residues (SGP S3).

**CAPRI's form.** Stated in SGP S3 without a GAMS line.

**What exists.** Diagnosis (31 October 2026): CAPRI's form fails where a permanent group's residues exceed its scaled
need, the grassland group; with manure trade on, 5 failures, all Romanian N, traced to Romania's mineral N (the
model's 2017 base about half of CAPRI's 2030, a vintage difference) (SGP S3). Decision (31 October 2026): CAPRI's form
wherever it leaves every permanent group a positive need, capri-mod's form only where not; checked at the base (base
reproduced, activities within 8e-6) (SGP S3). The setting name `need_multiplier` appears in capri_mod/fert/npk.py and
capri_mod/environmental/p_balance.py [own check]. REG DEP-10 records it.

**Steps still to do.** None stated in the notes. The change (commit 3c3db00, 31 October 2026) is in the code of gate
14 (commit 44861b3, 1 November 2026) [own check]; no note records its effect on the gate's results on its own.

**Dependencies, check, effect.** SGP §2 expected S3 might point at S1/S2; the diagnosis points at manure trade and
Romania's data vintage instead (SGP S3). Effect: the block's balance in permanent-crop regions; capri-mod's form had
changed the multiplier in every region (median 0.008 for N) (SGP S3).

**Open decisions.** None stated. [I] Whether Romania's mineral N vintage difference is to be addressed (it is the
remaining cause) is not raised in the notes.

**Sources.** SGP S3, §2; REG DEP-10.

---

## 7. S5: ammonia options held without an N incentive

**What it is.** Ammonia options held at their base shares in runs without an N incentive (DEP-15, KI K63; SGP S5).

**CAPRI's form.** The options are in the model with the base as a first-order point; for the manure-management options
CAPRI sets the quadratic PMP term to zero (ammo_tech.gms l. 3121) and calibrates the linear term (l. 3126-3133) (SGP
S5).

**What exists.** Curvature analysis at DE94: three negative directions; CAPRI's base is very probably a saddle too
(SGP S5). **Decision (31 October 2026): keep the hold (DEP-15); S5 closed** (SGP S5; REG DEP-15).

**Steps still to do.** None. Not yet checked: CAPRI's costParSqr values for DE94 against the model's slope (SGP S5).

**Open decisions.** None stated. Option (c), a calibrated quadratic term beyond CAPRI, was offered and not chosen (SGP
S5).

**Sources.** SGP S5; REG DEP-15; KI K63.

---

## 8. S6: the other regional NLP departures

**What it is.** DEP-10's list of 14 departures of the regional NLP form: need multipliers, fertiliser calibration in
RO21, RO22, RO31, RO41, RO42, ES62, HU11, the inner dual bound ±1000, the Shannon term +1e-6, ecoSetAside held, LUC
after the regional model, organic conversion per member state and crop class, Green Deal mineral caps exempted by
solving, manure of the split columns, relaxation kept for the scenario, warm start cut at 200 IPOPT iterations, and
others (REG DEP-10; SGP S6).

**CAPRI's form.** supply_model.gms (REG DEP-10); per item not stated in the plan.

**What exists.** Two items changed on 31 October 2026: the need multipliers narrowed (S3) and P and K manure trade as
CAPRI's MANP/MANK markets (S4) (REG DEP-10). No design note per item.

**Steps still to do.** "One at a time; each has its reason recorded" (SGP S6). Which items: as the project lead marks
them (SGP §2 item 4).

**How it is checked.** Per item (SGP S6). **Expected effect.** Regional; the seven calibration regions most (SGP S6).

**Open decisions.** Which DEP-10 items to take on, and in which order (SGP §2 item 4).

**Sources.** SGP S6; REG DEP-10; KI K50.

---

## 9. S7: market demand calibration

**What it is.** In the baseline run capri-mod recalibrates market demand to the supply models' supply every iteration
and scenarios inherit it frozen; the non-EU use factor is bounded to [0.2, 5] (REG DEP-5; SGP S7).

**CAPRI's form.** Market and supply models calibrated to the same baseline before the run (arm/market1.gms); during a
run only the market supply functions are recalibrated (simu_calibration_to_supply.gms) (DFC, row "the market's demand
at the baseline"; AR §6 step F).

**What exists.** The departure recorded on 29 October 2026 (step F; the code comment had called it CAPRI's) (DFC row;
AR §6 step F). No design note.

**Steps still to do.** DFC's removal condition: "supply models that reproduce CAPRI's 2030 market baseline quantities at
its prices, then the recalibration can be dropped and the baseline run checked against CAPRI's prices" (DFC row).

**Dependencies.** [I] The market move: MRI §5 lists DEP-5's [0.2, 5] factor acting on 17 new regions as a risk. [I]
The 29 units: their supply would come from supply models instead of fixed functions.

**How it is checked.** The baseline's market against CAPRI's reference market (SGP S7).

**Expected effect.** Prices, so the value of everything; small at base by construction (SGP S7).

**Open decisions.** Whether and when to take it on (SGP §2 item 4).

**Sources.** SGP S7; REG DEP-5; DFC (market demand row); MRI §5 risks.

---

## 10. S9: cattle member splits

**What it is.** CAPRI optimises replacement heifers (HEIR) and the calf activities on their own and clears young
animals per sex (INPANI_); capri-mod pools young-animal markets (REG DEP-4; KI K65; SGP S9).

**CAPRI's form.** INPANI_ per sex; HEIR and calf activities (REG DEP-4; KI K65).

**What exists.** Built as an option (`supply.use_cattle_member_splits`, default false); the price update takes each
region's response from its solved NLP; the full Farm-to-Fork run r96 did not converge (male calves' price 6.1 x base,
female below zero) (KI K65). **Deferred 23 October 2026**: CAPRI's per-sex Farm-to-Fork results, needed to judge the
prices, do not exist on the project lead's installation (KI K65).

**Steps still to do.** Find why the per-sex prices diverge (calf activities at their zero bounds); compare the per-sex
calf use and its flexibility with CAPRI (KI K65; DFC row `supply.use_cattle_member_splits`).

**Dependencies.** SGP §2 item 5: "S9 with K65". [I] G2g (young animals lifted into the market NLP) and the market
move's young-animal fix act on the same markets; the notes do not link them.

**How it is checked.** K65's test runs (SGP S9).

**Expected effect.** Cattle herds and their manure (SGP S9).

**Open decisions.** Whether to resume K65 without CAPRI's per-sex results (KI K65).

**Sources.** SGP S9; KI K65; REG DEP-4; DFC.

---

## 11. S10: mitigation options not built

**What it is.** CAPRI mitigation options not in the regional model (REG DEP-8; KI K93). SGP S10 names NoTill and LegSh
as the ones needed for F2F/GD.

**CAPRI's form.** The Green Deal technology list, pol_input/greendeal/refpol_endotech_all_ini.gms l. 216; no-till in
envind/tillage.gms l. 450-453 (yield), 562-563 (leaching), 580-583 (N2O) (KI K93, "The remaining options scoped").
Tillage options are zeroed outside the EU in the Green Deal file (SND §5).

**What exists.** 3-NOP built 29 October 2026; UreaSubst analysed and parked 31 October 2026 (the project lead's
decision) until a scenario where it could move; buffer strips, biodiversity options and biochar need nothing for F2F
and GD; conservation tillage none without a soil-carbon price (KI K93).

**Steps still to do.** NoTill and LegSh, "the two whose scenario response could be non-zero, small by the code's
terms, unmeasured" (KI K93). The Green Deal file's %NoYieldEffect% setting is "not checked" (KI K93).

**Dependencies.** [I] No-till's yield effect may act through CAPRI's T1/T2 split (KI K93), so it may depend on S1.

**How it is checked.** Their scenario response once built (SGP S10).

**Expected effect.** NoTill: yield, leaching, N2O, from small initial shares (Denmark 0.013); not measured (SGP S10; KI
K93).

**Open decisions.** Whether to build NoTill and LegSh; UreaSubst stays parked unless a scenario with an NH3 price, a
tax on CO2UREA or a binding mineral N cap is planned (KI K93).

**Sources.** SGP S10; KI K93; REG DEP-8; DFC (mitigation row); SND §5.

---

## 12. S11: quantities rebuilt from CAPRI's reported results

**What it is.** Where CAPRI reports nothing, capri-mod rebuilds its internal parameters: the 2030 feed slopes with
2017 weights (DEP-22), the MITERRA fractions, the digestibility table; per activity CAPRI's averages over T1/T2 (part
of S1) (SGP S11).

**CAPRI's form.** CAPRI's internal parameters (SGP S11); no GAMS lines given.

**What exists.** DEP-22 removed 6 November 2026: the 2030 feed slopes take CAPRI's 2030 weights from sim_ini_21730's DATA
at TRD (REG history; PMP_CAPRI_2030.md), so that export is not needed. No design note for the rest.

**Steps still to do.** Per item; "some close with more exports from the project lead's CAPRI" (SGP S11).

**Dependencies.** The T1/T2 averages close with S1 (SGP S11).

**How it is checked.** The rebuilt quantity against a CAPRI export, where one can be made (SGP S11).

**Expected effect.** "Small each, documented per builder" (SGP S11).

**Open decisions.** Which items to take and which CAPRI exports to request (not stated in the notes).

**Sources.** SGP S11; REG DEP-22.

---

## 12a. CAP instruments found missing in refactor stage 5 (added 3 November 2026)

Two scenario definitions could not be written as CAPRI's rules, because the model lacks the instruments; the project
lead decided (3 November 2026) to remove or keep them as they are and to schedule the ports here.

**P1. Obligatory set-aside.** CAPRI's SETA_ (supply/supply_model.gms l. 2219-2241): sum over the arable activities of
level x (1 - NONS) x r / (1 - r) = the obligatory set-aside activities (setaPact: ISET, GSET, TSET, NONF), r the
set-aside rate (DATA SETR), with the cost and income terms of supply/define_const_pmp_param.gms l. 44-76 when the
obligation binds at calibration. The model has the voluntary set-aside and fallow only (its SETA = VSET + FALL), so it
needs one obligatory set-aside activity (no output; CAPRI's costs and premium; first check that CAPRI's 2017 data
carry their coefficients, their levels being zero since 2008), the constraint and the PMP terms. Then
scen/set_aside/set_aside_10.gms (10% on GRCU) becomes a scenario folder again. SET_ASIDE_10PCT, which put a 10% floor
on all arable land counted on SETA, was removed (commit 3120071). Estimate: half a day to a day.
**Done 10 November 2026.** CAPRI's 2017 and 2030 data carry no coefficient of ISET, GSET, TSET or NONF other than HSTY
(sim_ini_21730 DATA; no TOIN, no premium, no level), so CAPRI's ISET, opened by prep_sim.gms l. 253 where a rate is
set, has nothing in the objective: the model substitutes it into the arable land balance (CAPRI's LandBalNoSlak_(ARAC)),
each rated activity's coefficient there + r / (1 - r) x (1 - NONS), the balance's base use unchanged, and reports
ISET (set_aside table, SupplyResult.iset). Same optimum as CAPRI's column (Claude's choice: no extra column without
terms). NONS is 0 (no NONS in CAPRI's 2030 data; the scenario sets it 0). Scenario folder set_aside_10:
set_aside_rates.csv (tools/build/build_set_aside_scenario.py from set_aside_10.gms and sets.gms: 10% on SWHE, DWHE,
RYEM, BARL, OATS, CORN, OCER, RAPE, SUNF, SOYA, PULS, MAIF in the 215 EU units). Mini-EU check: ISET = 0.1111 x the
rated crops' area in every unit (1,073 thousand ha), those crops -8.6%, voluntary set-aside and fallow -74, cereal
production -8.4%; no CAPRI run of the scenario to compare with.

**P2. Coupled support and the Pillar I envelope.** CAPRI's scenario without voluntary coupled support
(cap_after_2014 with voluntaryCoupledSupportFile = void.gms) sets the coupled premium types (PSDPAY_vcs*) to zero and
its premium module moves the envelope into the decoupled payment (cereal premiums +9 to +11% in CAPRI's pair). The
model holds Pillar I as one share of each premium (premium_scheme_shares_2030.csv, DPPIL1), so it needs CAPRI's
coupled-support part of each activity's premium per member state, and the ceiling logic that redistributes the freed
envelope. Part of a port of CAPRI's premium module, which would also allow other CAP experiments (other VCS levels,
BPS convergence). Until then tools/run/run_vcs_2030.py stays a supply-response validation test: it applies CAPRI's
own per-unit premium change of its pair of runs (capri_vcs_effect.csv) and compares the model's response with CAPRI's.

## 12b. CAPRI's source material as Parquet, outside git, for download (added 3 November 2026; beyond CAPRI)

**What it is.** The builders read CAPRI's material from capri_sources/ (and capri_reference/, merged into it on 4 November 2026), outside git (about 9 GB
raw: tools/lib/paths.py, docs/EXTERNAL_SOURCES.md): 114 of the 137 pipeline tasks, writing 233 of the 261 model-input
files, need it [own check, from the trace of 3 November 2026]. So the data can be rebuilt only where CAPRI's
installation is. The item converts that material to Parquet and publishes it as a versioned download, so a clean clone
can rebuild every model input. **Beyond CAPRI**: CAPRI needs its installation to rebuild its own data.

**Decided (the project lead, 3 November 2026).** The full Parquet set stays out of git and is available for download,
hosted on Hugging Face (as the dat mirror, hf_capri) as a gated dataset (each download approved by the project
lead); the item comes after the market move's stages 2-3; capri_data/sources kept, its extracts derived from the
pinned set (step 5); the converter written here (step 1).

**Measured** (3 November 2026, three of the largest files, every numeric record kept):

| CAPRI file | Records | Raw text | xz | Parquet (zstd) |
|---|---|---|---|---|
| markmarket_greendeal_1730et_base_1717.txt | 6.40 M | 388 MB | 42.0 MB | 38.4 MB |
| costsavings_ini_21730_jul15.csv | 7.48 M | 359 MB | 6.3 MB | 3.5 MB |
| res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv | 5.33 M | 330 MB | 34.7 MB | 31.9 MB |

**Steps** [I]:
1. One converter: a CAPRI listing (gdxdump text, CSV) or GDX to Parquet, one file per GAMS symbol, every record, Eps
   kept as a flag (as capri_reference's CSVs: value 0, eps 1), checked lossless against the original.
2. The full set published outside git, versioned; the repository keeps a manifest (file, SHA-256, size, version) and a
   download step that fetches the pinned version into capri_sources/ (tools/lib/paths.py unchanged for the builders).
3. CAPRI's GAMS source tree stays text (code: the builders read parameter statements from it,
   tools/build/convert_sources_to_csv.py).
4. The builders switched one by one to the Parquet files through one reader, each checked identical
   (tools/check/reproduce_builders.py; the rebuild from blank, tools/check/rebuild_from_blank.py).
5. capri_data/sources is kept (the project lead, 3 November 2026, revising the same day's decision to drop it): it
   holds the records each builder uses, extracted from the pinned version of the set only (the version recorded in
   each extract's provenance; the rebuild check refuses an extract of another version), so a clone rebuilds every
   model input from git alone, without access to the gated set (collaborators, CI), and CAPRI's changes show as diffs
   of the records the model uses. The everyday rebuild from blank runs from the extracts; the full rebuild from the
   downloaded set runs before each new version is published. The model's inputs stay CSV in git. Every file of
   capri_data/sources is Parquet (the project lead, 3 November 2026: an exception to the project's CSV rule for the
   builders' sources only), with a git text-conversion driver (.gitattributes) so that git diff shows a changed
   extract's rows as text; the data checks (capri_mod/data/validate_data.py) extended to the Parquet files.
6. Updating the set: CAPRI's new files (uploaded, or on the project lead's machine) -> the converter -> a version report
   kept in git (symbols, record counts, largest value changes against the previous version) -> the extracts rebuilt
   from it -> upload as a new tagged version of the gated dataset (a write token; the workspace's
   access to huggingface.co to be checked, else the upload runs on the project lead's side) -> the manifest pinned to
   it -> the inputs rebuilt from blank, reviewed, mini-EU and F2F/GD gates.
7. The update as one command, `python -m capri_mod.update_data` (stages 1-6 in order, stopping at the first failure,
   resumable; the upload only after an explicit approval; the Hugging Face token read from the environment or the
   local token file, never from the repository).
8. A Claude Code project skill, `.claude/skills/update-capri-data/SKILL.md`, which runs that command with the project
   lead, reviews the version report and the input diffs, and asks before the upload and any push (interactive
   `/update-capri-data`, or `claude -p` without the upload).

The Hugging Face side (the converter, the gated dataset under the account nuvolaTeam, its versions and uploads) is
Claude's work (the project lead, 3 November 2026). The dataset is nuvolaTeam/capri-mod-raw
(https://huggingface.co/datasets/nuvolaTeam/capri-mod-raw): licence GPL-3.0 (the project lead, 3 November 2026),
gated with manual approval, public listing, the card only (no data yet). Access from the workspace to huggingface.co with the project lead's
fine-grained token checked the same day; the token is kept outside the repository.

**Open decisions.** None stated (host, access, licence and timing decided 3 November 2026).

**Decided 4 November 2026 (the project lead).**
- capri_reference/ is gone from the repository: its folders are in capri_sources/reference/ (tools/lib/paths.py
  REFERENCE, capri_mod/external_paths.py; CAPRI_REFERENCE to put them elsewhere), its README in
  docs/EXTERNAL_SOURCES.md ("The reference folder"); it goes to the Hugging Face set with the rest of capri_sources.
- capri_data/sources/ is renamed by one rule, where each file comes from, at the Parquet conversion (step 2 of this
  section, after the market move), so each file is renamed once: `capri/dat/<CAPRI dat path>/<gams file>__<symbol>`,
  `capri/gams/<CAPRI gams path>/<gams file>__<symbol>`, `capri/results/<CAPRI run or file>/<content>_<year>` (capreg,
  capmod, sim_ini, estnlp included), `external/<provider>/<dataset>` (Eurostat, FAO, NUTS, literature); the file under
  unsourced/ given a source or a builder first. A move: every model input rebuilt identically.
- capri_data/sources/ keeps the extracts of external material (CAPRI's files, Eurostat, NUTS, literature) and the
  declared files: the ones pinned to the Hugging Face version. The files one builder writes for another (on 4 November
  2026 about 50 of its 109, e.g. baseline_pmp/intensity_q_*, recipe_*_quad_*, capreg/capreg_producer_prices.csv) leave
  git for a pipeline cache the pipeline rebuilds; a few may be kept deliberately where worth reviewing. Each of the 50
  classified one by one first (some are extracts made inside a builder, e.g. the PMP terms read from CAPRI's GDX).
  Done with the Parquet conversion of this section.
- The published set is converted from CAPRI's own files (the project lead's installation and exports), not from the
  JRC's Hugging Face mirror of `dat` (hf_capri), which is not a dependency (the project lead, 4 November 2026). The
  converter (step 1) therefore covers CAPRI's GDX files and the data parameters CAPRI writes in its `.gms` data files
  (e.g. p_PEATSH_def in dat/envind/lulucf_emissions_original_source.gms), one Parquet file per symbol;
  capri_sources/dat_local/ (the files the project lead supplied on 4 November 2026) is part of it.
- The model's inputs are organised by role, not by a year in the folder name (with the renaming above, so paths change
  once): capri_data/<base_year>/ holds the base year's data only; capri_data/baselines/capri_ref_2030/ everything taken
  from CAPRI's 2030 reference run (on 4 November 2026 spread over 40 of the 216 files of capri_data/2017/, e.g. the
  2030 PMP terms, market state, rents, N coefficients and CAP ceilings, over capri_data/trajectories/ and over
  capri_data/scenarios/capri_ref_2030/), a CAPTRD-MOD baseline as another package (baselines/captrd_2030/), the run
  choosing its baseline package; capri_data/scenarios/ the policy scenarios, and under scenarios/groups/ the data a
  scenario group shares, as CAPRI's pol_input files (the project lead, 4 November 2026: greendeal_group moves to
  scenarios/groups/greendeal/, held once, read by every Green Deal scenario). A move: each of the 40 files
  classified first (a _2030 file that is in fact a base-year input is put to the project lead, not moved blindly);
  loaders, builders, declarations and pipeline outputs follow; every model input rebuilt identically.

## 13. Summary

| Item | Depends on | Status | Open decisions | Main source |
|---|---|---|---|---|
| Market on 45 RM (stages 1-3, 2017 year, TARV, young-animal timing) | refactor finished; full scenario runs | inventory and decisions done; WBA fix done; **stage 1 done 3 November 2026** (MRI "Stage 1, done"); stages 2-3 built 3-4 November 2026 (stage 2: the two EU blocks, feed bulks per block; stage 3: ROW as CAPRI's 17 market regions, FPRI over the 45; tariffs.csv kept in stage 2, TARV with the ports) | stage of the TARV switch and 2017 rebuild; link of stage 2's young-animal fix with G2g; gate batching | MRI |
| Ports (stages 4-7: bilateral and global TRQs, DEP-41, levies, entry prices, land and yield block) | market move stages 1-3 | built 4 November 2026 in the current market code (stages 4-5 TRQs, stage 6 entry prices and flexible levies, CAPRI's market prices as the reference price levels, stage 7 the land market outside the EU); the full F2F with them converged on 5 November after K117 (13 iterations; mean deviation from CAPRI 4.59 against 4.18 at gate 16, the beef and poultry prices higher, not yet attributed); the GD gate not run; market time per solve 145-480 s against 15-38 s at gate 16 (open) | ports before G3 or as G3 equations; luc_market not in scope | MRI §5; G3I |
| 29 non-EU units | market move (MRI §7) | SND steps 1-9 done 4 November 2026 (step 9: the 2030 baseline per country within 0.7-5.1% of CAPRI's, weighted; the 9-country F2F did not converge, Serbia's feed energy price oscillating, to diagnose); step 10, the full F2F and GD runs, started 4 November | default country list after the build [I] | SND |
| S1/S2 (and DEP-42) | refactor stages 3-5; N6 | decided 1 Nov (S1 option c; S2 explicit); data and code not started; DEP-42 on n6 branches; **the project lead, 4 Nov: close the activity gap with CAPRI** (S2's splits; NECR held fixed as CAPRI's FACT, 251 kha in the EU's 2030; calves and heifers by sex with S9) | none stated | S12 |
| Step G (G2b, G2d, G2f, G2g; G3) | G2b on refactor stage 4; G3 after market move | G1, G2a, G2c, G2e built; G2b, G2d, G2f, G2g built 4 November 2026 on branch step-g2b (each equal to the former code at random points; merge after a mini-EU check and the suite); G3 on standby | G3: bound policy, objective with squareness check, validation on sim_ini; fudge activation; scaling | MID; GR; G3I |
| S3 | — | decided and implemented (narrowed form); base checked; in gate 14's code | none stated | SGP S3 |
| S5 | — | closed: hold kept (DEP-15) | none | SGP S5 |
| S6 | — | not started; per item | which DEP-10 items | SGP S6; REG DEP-10 |
| S7 | [I] market move; 29 units | not started | whether and when | SGP S7; DFC |
| S9 | K65 | deferred (no CAPRI per-sex results) | whether to resume | KI K65 |
| S10 | [I] S1 for no-till's yield | 3-NOP built; UreaSubst parked; NoTill, LegSh not built | whether to build NoTill and LegSh | KI K93 |
| S11 | S1 for T1/T2 averages | not started; per item | which items and exports | SGP S11 |
| P1 obligatory set-aside | done 10 November 2026 | CAPRI's SETA_ (supply/land.py _obligatory_set_aside), scenario set_aside_10 | — | §12a; supply_model.gms SETA_ |
| P2 coupled support, Pillar I envelope | — | not started | when; with the premium module's port | §12a |
| CAPRI's sources as Parquet, for download (beyond CAPRI) | — | decided 3 Nov: outside git, gated Hugging Face dataset, after market stages 2-3; sizes measured; not started | none | §12b |

## 14. Open decisions across all items

1. Decided 2 November 2026: the TARV switch in stage 2, the 2017 rebuild in stage 1.
2. Decided 2 November 2026: stage 2's young-animal fix in the current solve; G2g later.
3. Decided 2 November 2026: the F2F/GD gates after stages 1-4 and after stages 5-7.
4. Ports: written in the current market code (done 4 November 2026, stages 4-7).
5. Decided 5 November 2026: the market's land-use-change estimation (luc_market) is ported.
6. Decided 5 November 2026: the default `run.supply_countries_outside_eu` becomes CAPRI's full list, at the end of the
   work (too costly in run time now). Moved on 9 November 2026 (the project lead): after G3, before CAPTRD-MOD.
7. Decided 5 November 2026: G3's bound policy is CAPRI's reproduced; the least-infeasibility formulation an optional
   diagnostic mode (MID §7.2; BEYOND-13).
8. Decided 5 November 2026: G3's objective is zero, with a squareness and structural-rank check before every solve
   (MID §7.2).
9. Decided 5 November 2026: G3-R plus G3-C replace MID §6's acceptance test. Open: the CAPRI market dump for the
   external validation (GR Q5.2), to be agreed with the project lead.
10. Decided 5 November 2026: the fudge equations as CAPRI activates them; variables scaled as ratios to base (a
    registered departure); a Dulmage–Mendelsohn check (BEYOND-12). Open: the set structure in production and
    validation (GR Q6.5), with G3's design.
11. Decided 5 November 2026: S6 stays close to CAPRI; each DEP-10 item triaged, with questions to the project lead
    where CAPRI's form cannot be kept.
12. Decided 5 November 2026: S7, the baseline demand recalibration (DEP-5) is removed, soon.
13. Open (5 November 2026): K65 stays deferred unless CAPRI data help; to revisit after S1/S2 (heifers by sex).
14. Decided 5 November 2026: S10, NoTill and LegSh are ported.
15. Open (5 November 2026): S11's CAPRI exports, specified to the project lead (2030 feed per head per activity for
    DEP-22, p_Nemidat, p_digestPar after digestibility.gms; T1/T2 with S1).
16. Not raised in the notes [I]: the position of S1/S2, the G2 stages and S6-S11 relative to the market move and the
    29 units.
17. Decided 5 November 2026: P1 (obligatory set-aside) just before CAPTRD; P2 by porting CAPRI's premium module, scheduled
    with P1 before CAPTRD.
18. Decided 3 November 2026: §12b's Parquet download on Hugging Face, gated, after the market move's stages 2-3. Go-ahead confirmed 5 November 2026.
19. Decided 5 November 2026: the CAPRI 2040 mirror-standard (pesticide) extracts are kept as a future 2040 check for
    CAPTRD-MOD (capri_reference/), not as a benchmark until the shock inputs and CAPRI's scenario code are available.

## 15. Notes found out of date while drafting

- DEPARTURES_FROM_CAPRI.md (about line 357) says the market supply Hessian is not built per EU block; MRI §3.3 says the
  code builds it. STRUCTURAL_GAPS_PLAN S8 bases its effort estimate on the older statement. Not corrected here; to be
  checked against the code first.
- MARKET_REGIONS_INVENTORY.md line 9 said DEP-31 to DEP-40 were on the unmerged step-g; step-g is merged into
  manifest-sql. Corrected with this plan.
- STRUCTURAL_GAPS_PLAN S1 cited capmod.gms l. 246 for CAPRI's technology set; the set is at l. 247-249 (as S1_S2_DESIGN.md
  has it). Corrected with this plan.
- MARKET_IPOPT_DESIGN.md §7 still records the objective ½‖z − z₀‖² as decided and §6 item 8's acceptance test; G_REVIEW
  reopens both (Q2.4, Q5.1). Left as it is until the project lead decides G3's points.
- DEP-42 is in the register on the n6 branches only; it reaches manifest-sql when they are merged.
- NONEU_SUPPLY_REGIONS_SCOPING.md is a project document, not in the repository; this plan uses SUPPLY_NONEU_DESIGN.md.
- No CSV extract of sim_ini's parameters exists yet (only its sets); the move's stage 1 needs one (MRI §7 item 4).
