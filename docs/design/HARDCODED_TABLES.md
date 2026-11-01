# Hard-coded code tables: inventory and plan

Project lead's rule, 30 October 2026: no hard-coded constants or parameters in any file, unless needed. Numbers are
already covered by the code-number census (capri_data/schema/03_code_data.sql, 04_code_data_status.sql). This note
covers the other kind: tables of codes written in Python (sets, lists and mappings of region, product, activity, feed
or technology codes). These should be data, read from CSV.

## Inventory (30 October 2026)

The inventory is a machine scan of the 254 Python files of capri_mod/ (tests excluded) and tools/build/. It takes
every tuple, list, set or dict literal with two or more code-like strings, and checks each against the CSVs of
capri_data/ and CAPRI's set dumps (capri_reference/sets/simini_21730). Only the rows named under "Checked by hand"
were verified by reading the code; the rest is the scan's result.

| Where | Tables | Mirror a CAPRI set (exact or superset match in its dumps) | Model crosswalks or classifications |
|---|---|---|---|
| capri_mod/ | 81 | 31 | 50 |
| tools/build/ | 212 in 81 files (3+ codes each; includes item and column selectors) | most | the model ↔ CAPRI crosswalks |

About 10 of capri_mod's tables are the master copy of a generated file: capri_data/codes/model_activities.csv,
model_commodities.csv and model_trade_regions.csv are written by tools/build/build_code_lists.py from the Python
literals, not the other way round.

Single codes compared in logic (`c == "MILK"` in a formula specific to milk) number 466 tests and 14
`startswith`/`endswith` tests over both trees. A code named in an equation that is about that code is legitimate. A
code used as a classifier (`startswith("NO")` meaning "outside the EU") is not.

### Duplicated tables (the first to fix)

- **Model animal → CAPRI activities:** 11 copies across the builders, at two levels of detail (18 or 19 pairs).
- **Model crop → CAPRI crop:** two pairs of identical copies:
  - build_capri_base `CROP_MAP` and build_cap_ceilings_2030 `CROPS`;
  - build_labour_setaside `CROPS` and build_pmp_capri_2030 `MODEL_TO_CAPRI`.
- **EU member states:**
  - 9 copies of the two-letter EU27 set;
  - 4 copies of the eight-character `EU_MS` set;
  - at least 6 variants of non-EU lists, which do not agree with each other.
- **Non-EU tests on Norway:** `"NO"` or `"NO000000"` tests in about 12 places in capri_mod.
- **Feed and dairy sets:**
  - tradable feed bulks (CAPRI's FEED_TRD): 3 copies;
  - dairy products (DAIRY_DEF): 5 copies;
  - dairy product → market code: 3 copies.
- **Other CAPRI sets and crop or land groups:**
  - MITERRA animal types: 3 copies;
  - oilseed crushing chains (PRCD): 3 copies;
  - permanent crops: 5 copies;
  - the land-type labels ARAC, GRAS, FRUN: 11 copies;
  - the nitrogen sources MINE, EXCR, CRES: about 10 copies.
- **Animal → product:** three copies, in two code domains (supply/capri_pmp.py, supply/supply_module.py, and the
  inverse in coupling/bridge.py).

### Checked by hand

- **coupling/bridge.py, `_sugar_per_beet`.** The EU ratio leaves out a literal list of non-EU member states. That list
  names ME000000 and CH000000, which are not CAPRI codes (CAPRI's Montenegro is MO000000). There is no effect on
  results today, because the sugar table has neither.
- **tools/build/build_trajectory_capri_ref.py.** A set named `EU27` holds Norway and not the United Kingdom: the
  model's supply countries, under a misleading name.

### Also reported by the scan, not yet checked

- supply/land.py `LTall` fixes the column order expected of the land-market matrix.
- definitions.py's FEED_ITEMS, GHG_TYPES, NUTRIENTS and LAND_TYPES may be read by no code.

## Done

On 30 October 2026 (branch region-decl):
- **Trade regions.** The code list capri_data/codes/model_trade_regions.csv is now the declared master, with
  a source per row: each trade region in order, and CAPRI's region code. build_code_lists wrote it from the
  REGION_MAP literal until then.
  - The model (definitions.ALL_TRADE_REGIONS, TRADE_REGION_OF_CAPRI) and the builders (REGION_MAP) read it.
  - The country lists of definitions.TRADE_REGIONS were read by no code and are gone.
- **EU trade blocks.** They are read from eu_market_blocks.csv, whose stale Norway row is removed.
- **Supply-model countries outside the EU** are derived from the data: the regional units outside the EU blocks
  (regional_units.csv), placed in their CAPRI market region (rms_to_rm.csv) (definitions.SUP_NONEU).
- **H1 in the model.** Every Norway test and non-EU list in capri_mod now goes through definitions.is_eu, SUP_NONEU
  or EU_MS_BLOCK. This covers model.py, coupling/bridge.py (including the sugar ratio's list), coupling/price_step.py,
  supply_module.py, projection/prices.py, policy_module.py and io_results.py.
  - Kept: capri_stop.py's NO000000 and captrd/prepare.py's NO000000 statement, because CAPRI's own code names
    Norway there.
- **Still to do in H1:** the builders' EU and non-EU lists.

## Plan (proposed; each stage a move that must reproduce the reference run, except where noted)

1. **H1, regions.** Replace every non-EU test and every EU member-state list, in the model and in the builders, by
   `definitions.EU_MS_BLOCK` and `SUP_NONEU`, or by the same CSVs for builders. bridge.py's list goes too.
2. **H2, crosswalks.** Make the code tables of capri_data/codes the master copy:
   - model ↔ CAPRI activities, products, dairy and crushing chains;
   - the model and every builder read them;
   - build_code_lists then checks the tables instead of writing them from the literals.
3. **H3, CAPRI's sets.** The tables that mirror a CAPRI set are read from that set. The run cannot read
   capri_reference (it is not committed), so a builder extracts the sets the model uses from CAPRI's instantiation
   into capri_data/shared/sets/, as tools/build/build_captrd_sets.py does for CAPTRD.
4. **H4, classifiers in logic.** A single code used as a classifier becomes a set read from data. A code named in an
   equation about that code stays.

The rule for new code: no new table of codes in Python. A set or mapping goes in a declared CSV, or is read from
CAPRI's sets.
