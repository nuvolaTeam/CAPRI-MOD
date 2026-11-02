# Refactor stage 3, N6: the supply's code tables as data (design, 2 November 2026)

N6 moves the code tables of the supply files (docs/design/STAGE3B_PLAN.md 2.4; HARDCODED_TABLES.md H2-H4) out of the
Python code. The project rule: no table of codes in Python; a set or mapping is a declared CSV with a source per row, or
is read from CAPRI's own sets. CAPRI's sets reach the model through capri_data/codes/capri/<SET>.csv, written by
tools/build/build_code_lists.py from CAPRI's instantiated sets (capri_reference/sets/simini_21730, 1,972 sets of the
endotech Green Deal 2030 run); nine are there today (FEED_TO_O, MAACT, MCACT, MPACT, MS_RU, PACT, RALL, XX, XX1). Model
codes and CAPRI codes are joined through capri_data/codes/model_activities.csv (capri_codes: WINE = TWIN, CORN = MAIZ,
OFOD = OFAR + ROOF, SETA = SETA + FALL).

Each move must leave the mini-EU run identical (1e-12), except where a finding below changes a table; those wait for
the project lead's decision.

## The tables, their source and what the comparison shows

| table (supply_module.py unless noted) | CAPRI source | comparison with the model's table | proposal |
|---|---|---|---|
| CROPDIV_GROUPS | set cropDivGrps_mCact (in the sim_ini sets) | equal for every annual crop, except the model's OFOD: CAPRI has OFAR and ROOF as two groups of their own, the model one group OFOD (its activity is their sum) | read from the set through the crosswalk; OFOD's group: **finding 1** |
| PERMANENT_LAND_CROPS | set landTypes_to_pact, land type FRUN: NURS, NECR, OLIV, APPL, OFRU, CITR, TAGR, TABO, TWIN | the model has WINE, OLIV, TABO, APPL, OFRU, CITR, TAGR: **NURS (nurseries) is on permanent land in CAPRI, on arable land in the model**; NECR is not a model activity; OCRO is on ARAC in both | read from the set through the crosswalk; NURS: **finding 2** |
| LAND_TYPES | set landTypesMrk: GRAS, FORE, ARTIF, OLND, ARAC, FRUN | the model's ARAC, GRAS, FRUN, FORE, OLND: the same without ARTIF (artificial land is not in the model's land market) | read from the set, ARTIF left out as a declared choice (one row with its reason), unless the project lead wants it in (a behaviour change) |
| FODDER_ACTS | set FODCRP: MAIF, ROOF, OFAR, GRAS, STRA (the comment cites sets.gms FODF) | the model's GRAS, MAIF, OFOD, ROOF: ROOF is not a model activity (it is inside OFOD), so it never matches; STRA (straw) is not an activity of the model | read from the set through the crosswalk (GRAS, MAIF, OFOD); the stray ROOF goes (no effect) |
| ORGANIC_CROPS, ORGANIC_CROP_TARGET, ORGANIC_YIELD_GAP_CROPS | organicCrops, ngrp_to_organicCrops, crops_to_ngrp, pact2yieldGap (pol_input/greendeal/load_organic_targets.gms, inputs/load_organic_yieldgap.gms) | **not among the sim_ini sets** (the run did not load the organic module's sets) | a declared CSV (capri_data/codes/organic_crops.csv: crop, target group, takes the yield gap, with the GAMS lines per row), or a builder reading the GAMS sources |
| PESTICIDE_AFFECTED | pesticideCrops = MCACT minus the idled histosols (conventional_io.gms l. 51-53) | the model's CROPS minus GRAS, MAIF, OFOD, SETA (the fodder crops and set-aside, which the rule's yields do not reach: registered in the code) | derived from MCACT through the crosswalk minus FODCRP and the set-aside codes, the exclusion as a declared rule |
| HISTOSOL_CLASSES | (crop, arable_land), (grass, grassland): the model's two classes of CAPRI's histosol options | not a CAPRI set but the model's naming of its two classes | a declared CSV (two rows, their source) |
| CATTLE_SPLIT_MEMBERS | set SplitActs (GRAE, GRAI, DCOL, DCOH, BULL, BULH, HEIL, HEIH) and the cattle member sets | to compare row by row (the model adds HFRS:rep, CALV:male/female/sex for its young-animal splits) | a declared CSV unless every row is in CAPRI's sets |
| FIXED_ACTIVITIES | OOIL, OIND, NURS, FLOW, OCRO, OANI | the model's classification (activities held at their level, K69) | a declared CSV with the reason |
| ACTIVITY_PRICE_SOURCE (and capri_pmp.LIVESTOCK_PRODUCT, coupling/bridge.py's inverse) | the animal -> product mapping, three copies | to check against CAPRI's MAACT -> product sets | one declared table read by the three |
| capri_pmp.py crosswalks (ARABLE_ACTIVITIES, LIVESTOCK_YOUNG, COUNTRY_ELAS_ALIASES, ACTIVITY_ALIASES) | partly CAPRI's sets, partly the model's | to check one by one | declared CSVs or the crosswalk |
| n_cascade.py HOUS_TECHS, STOR_TECHS, RUNH_TECHS, APPL_TECHS; n_leaching.py APPL | CAPRI's ammonia technology sets (MITERRA cascade) | to check against the sets of the run (mitiTech_map and the ammonia sets) | read from the sets |
| _MS_ALIAS ({"GR": "EL", "UK": "UK"}) | member-state code aliases | the model's normalisation of Eurostat and CAPRI country codes | a declared CSV |

## Findings for the project lead

1. **OFOD's crop-diversification group.** CAPRI's crop diversification (cropDivGreening_) counts other fodder on
   arable land (OFAR) and fodder root crops (ROOF) as two groups; the model counts its OFOD, their sum, as one. Where
   both are grown, the model's largest group can be larger than CAPRI's, so the rule can bind where CAPRI's does
   not (not measured). As CAPRI
   it would need OFOD split into its two members, which the model does not have; the alternative is to keep one group
   and register the departure.
2. **Nurseries (NURS) on arable land.** In CAPRI NURS is a permanent crop on FRUN land (landTypes_to_pact); in the model
   it is on arable land (PERMANENT_LAND_CROPS leaves it out). NURS is a fixed activity (held at its level), so the
   difference shifts its area between the arable and the permanent land balances and their rents: as CAPRI it would
   move to FRUN (a behaviour change, its own run; the land data are built with the model's
   set, tools/build/build_capri_base.py, so the builder would change with it).

Both are behaviour changes. Moving the tables as they are (with the two findings registered) keeps the runs identical;
correcting them follows as separate commits after the project lead's decision.

## Decisions (2 November 2026, the project lead)

- Step 1: the tables move as they are (runs identical), the two findings registered: DEP-42 (OFOD one
  crop-diversification group, kept until S1/S2 splits OFOD) and DEP-43 (NURS on arable land).
- Step 2: NURS goes to permanent-crop land as in CAPRI (its own commit and run, the land data's builder with it).
  Done 2 November 2026: the mini-EU run's differences are in the register (DEP-43); test suite 279 passed, 2 skipped.
