# Data declarations and checks in DuckDB (28 October 2026, the project lead's decision)

Decision: the CSV files stay the stored data. Each input's metadata (types, units, key, ranges, code lists, source) is
declared once, as DuckDB table definitions kept as `.sql` files in git, and the check loads the CSVs into those
declared tables, so the declaration is the enforcement. The pipeline stays with doit (`DATA_PIPELINE_DOIT.md`); the
check is one doit task after every rebuild and one test. This batch changes no data: a violation it finds is reported
and fixed as its own item.

## What exists today (inventory, 28 October 2026, batch-3 at fb60dc8)

401 CSV files under `capri_data` outside `archive/`: `sources/` 162 (CAPRI and other extracts), `2017/abatement` 68,
`2017/supply` 47, `2017/market` 42, `2017/environment` 30, `validation` 13, `2017/policy` 13, `pipeline` 10, `shared` 8,
`trajectories` 5, `2017/feed` 3.

Metadata stores, kept by hand, overlapping (the first inventory counted four; with the batch-4 removal of
armington_params.csv, 29 October 2026, the file turned out to be named in seven: the four below and `DATA_CATALOG.json`
(live, stored-not-applied and archived files, 44 live entries), `INPUT_MANIFEST.json` (93 inputs and the data held in
code) and `DATA_LOCATION_MAP.md` (where each input lives in CAPRI). `FITNESS_FOR_USE.json` (the outputs' fitness,
read by capri_mod/fitness.py), `SYMBOL_EXTRACTION_MAP.json` and `validation/schema_coverage.json` (a dated report)
describe the data too. All of them are to be checked when their content moves into the declarations):

| Store | Entries | Holds | Read by |
|---|---|---|---|
| `MANIFEST.json` | 143 | source, vintage, units, domain, status, shape | people; `DATA_DICTIONARY.md` says it lags the files in places |
| `DATA_SOURCING_REGISTRY.json` | 276 | per dataset its nature (REAL_CAPRI, SYNTHETIC_FALLBACK, ...), source, status, notes; also issue records that are not datasets (e.g. `paddy_rice_blocked`, `ireland_livestock_missing`) | people, audits |
| `INPUT_SCHEMA.json` | 54 inputs | concept, unit, dimension, modules, source (type, reference, vintage, confidence), known gaps | `tools/check/verify_schema.py` (coverage of real against fallback cells) |
| `DATA_DICTIONARY.md` | about 170 table rows | content, source, shape per file | people |

Matched to the files by name (so approximate): 167 of the 401 CSVs are described in at least one store, 234 in none.

Code lists: the regional units are data (`capri_data/shared/regional_units.csv`, 221 units with member state); the
crop and animal activities and the market commodities are lists in code (`capri_mod/data/definitions.py`: `CROPS`,
`ANIMALS`, `MARKET_COMMODITIES`), with aliases elsewhere (`capri_pmp.py` `ACTIVITY_ALIASES`).

## CAPRI's own practice

- `gams/sets.gms` declares the code lists: `RALL` (all regional units), `MPACT` / `MAACT` (production and animal
  activities), `ROWS` and `COLS` (the data cube's rows and columns), the market products. GAMS refuses a value whose key
  is not an element of the parameter's declared sets (domain checking): the guarantee the foreign keys below give.
- `gams/CAPRIunits.gms` (Witzke and Britz, 2009) assigns a unit to each `COLS` x `ROWS` cell (acronyms such as
  `U_1000ha`, `U_TonPerHa`, `U_EuPerHa`), "work in progress", meant to warn where an output holds numbers in cells
  without a unit.

Following CAPRI: the code lists are extracted from `sets.gms` and the units from `CAPRIunits.gms`, not written anew.
Beyond CAPRI (for the project lead to note): range checks, and enforcement at load instead of a warning.

## Layout

- `capri_data/schema/codes/*.csv`: code lists built from CAPRI's `sets.gms` by one builder (regional units, activities,
  data-cube rows, market products, with CAPRI's descriptions); `definitions.py` then reads them instead of holding lists.
- `capri_data/schema/units.csv`: the unit catalogue from `CAPRIunits.gms` (code, description); a unit CAPRI does not
  have is added with a flag saying so.
- `capri_data/schema/<folder>/<table>.sql`: one `CREATE TABLE` per CSV with column types, `NOT NULL`, `PRIMARY KEY`,
  `REFERENCES` to the code lists, `CHECK` ranges; `COMMENT ON COLUMN` holds the unit code, `COMMENT ON TABLE` the source,
  vintage and builder. Checked on DuckDB 2.0.0: duplicate keys, unknown codes, out-of-range values and non-numeric text
  are refused with the key or CSV line named; units stored as comments read back.
- `capri_data/schema/rules.sql`: the cross-table rules a constraint cannot express, as queries that must return no rows:
  every unit comment is in the catalogue; columns that are joined across tables carry the same unit; every CSV under
  `capri_data` has a declaration; every declared table is read by the model or by a declared builder.
- `tools/check/validate_data.py`: builds an in-memory database, runs the declarations, runs the rules and the same
  checks as queries first (so it lists every violation, not only the first a refused load reports), then loads.
- `capri_data/DATA_DICTIONARY.md` generated from the declarations.

## Points to settle while building

1. Wide tables (regions in rows, activities as columns). **Settled 29 October 2026**: the validator reads the file
   long. A `-- layout: wide` line declares the table as (key, item, value); the CSV's first column is the key, every
   other header an item, so the headers are checked against the code list by the item column's `REFERENCES` and every
   value by the value column's type and `CHECK`. `-- layout: unnamed` takes an empty first header (a pandas index
   written without a name) as the first declared column. A long table's value column holds a different unit per item
   (t/ha for a crop, t per head for milk), which `COMMENT ON COLUMN` cannot hold: the units are a table,
   `value_units (tbl, item, unit, status, basis)`, filled by each declaration, with a rule that every item has its
   unit and every unit is in the catalogue. `status` says how far the unit is established: `capri` (stated by CAPRI:
   `CAPRIunits.gms`, `CAPRIunits.gdx`, CAPRI's documentation), `builder` (stated by the builder from the CAPRI item it
   transforms, not found stated by CAPRI), `open` (not established; the unit is left empty). First declared
   (`10_supply_2017.sql`): base_areas, land_availability, animal_numbers, yields, variable_costs, producer_prices.
   Then `12_supply_pmp.sql` (29 October 2026): the PMP terms, CAPRI's 2030 and capri-mod's own with CAPRI's recipe
   (2017, 2030), crops and animals, and capri_level_ratio; rules: the crop terms symmetric with one level per activity,
   the territory groups' CAPRI regions in RALL and the same for a region's crops and animals, the animal terms' level
   ratio capri_level_ratio's. One open unit: the animals' x_capri holds CAPRI's level unit of each animal (1000 head,
   poultry million head), two units in one column. `13_supply_rents_elas.sql`: the land rents (2017, 2030), the
   own-price supply elasticities (PELA regional and raw, CAPRI's p_ElasSupp per member state; model unit U_Elasticity)
   and the mineral N price; three of them have no builder in the repository (pmp_own_price_elasticities,
   capri_own_price_elasticities, mineral_n_price: none is read by the default model). `20_market_2017.sql`: the
   market supply functions (ProdNQ_). `99_rules.sql`: every numeric column of a long table has a unit in the
   catalogue (information_schema; tables with per-item units are left to their own rules).
   The open units found, and settled where the data allow (29 October 2026): the yields of OCRO, OIND, NURS, FLOW are
   value units per ha (CAPRI measures these crops in value: MPRI an index near 1000, MREV = YILD / 1000 x MPRI; the
   model's own unit U_ValueUnitPerHa); HFRS's yield has no single unit (its CAPRI members' YILD measure meat and raised
   heifers; without effect on results: the animals' output is CAPRI's output coefficients, and of their yields only DCOW's is used, as a ratio); OANI's yield and cost stay open (per unit of
   an index level; OANI is held at 0); the livestock rows of the EU producer prices were removed (K72). `CAPRIunits.gms` assigns units to the market results (`yild` of a
   product t/ha, prices EUR/t), not to the supply data's per-activity items, and the old `CAPRIunits.gdx` gives the
   activities' LEVL units only (crops 1000 ha, animals 1000 heads, hens and poultry million heads, OANI an index).
2. `MANIFEST.json` and `INPUT_SCHEMA.json`: retired once their content is in the declarations; `verify_schema.py`'s
   coverage count moves onto the declarations.
3. `DATA_SOURCING_REGISTRY.json` (276 entries): the 37 that name a file give their provenance to the table comments.
   The other 239 are not data declarations but a log of the project's checks and decisions: 143 closed (fixed,
   implemented, retired), 59 with another status (validations, diagnoses, settings, "comparison pending"), 37 without
   a status. The project lead's decision (28 October 2026): they go to `KNOWN_ISSUES.md`. Each still-open item is
   checked against today's code and becomes a K item (or joins the K item it duplicates); the closed and historical
   entries are kept verbatim in an appendix of `KNOWN_ISSUES.md`, so nothing is lost and the K list stays current.
   Its `code_embedded_data` section (2 entries: constants in code) goes to the proxy audit's hardcoded-data list.
   **Done 29 October 2026:** the 201 log entries and the sections uploaded_star_files_assessment,
   capreg_extraction_outcome, _release_readiness and cattle_member_splits are verbatim in
   docs/KNOWN_ISSUES_REGISTRY_LOG.md (a file of its own, linked from KNOWN_ISSUES.md, because of its size), with the
   triage of the 71 entries not marked closed (new K92-K96; K91 corrected); code_embedded_data in
   docs/design/PROXY_AUDIT.md; the registry keeps its 74 dataset entries.
4. "No orphan rows": a row whose key is not in a code list (the foreign keys) and a table nothing reads (rule above).

## Order

1. Code lists and units from CAPRI's sources.
2. The 54 model inputs of `INPUT_SCHEMA.json`.
3. The builders' outputs and intermediates (the doit trace gives which builder writes each).
4. The extracts under `sources/`, each declared with its CAPRI symbol.

Each step: declarations, check, violations listed; the data unchanged.
