-- The core 2017 inputs of the supply model: crop areas, land, herds, yields, input costs, EU producer prices.
-- Each wide file (regions in rows, codes as columns) is declared long, (region, item, value): its headers are checked
-- against the code list by the item column's REFERENCES; the unit of each item is in value_units (00_codes.sql).

-- file: capri_data/2017/supply/base_areas.csv
-- layout: wide
CREATE TABLE base_areas (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    activity VARCHAR NOT NULL REFERENCES model_activities (code),
    value DOUBLE NOT NULL CHECK (value >= 0),
    PRIMARY KEY (region, activity)
);
COMMENT ON TABLE base_areas IS 'crop areas 2017 per regional unit: CAPRI''s LEVL summed over the crop''s CAPRI activities (tools/build/build_capri_base.py, res_17* dumps)';
INSERT INTO value_units SELECT 'base_areas', code, 'U_1000ha', 'capri', 'CAPRI''s LEVL of crop activities (CAPRIunits.gdx P_CAPRIunits: U_1000ha)'
FROM model_activities WHERE kind = 'crop';

-- file: capri_data/2017/supply/land_availability.csv
-- layout: wide
CREATE TABLE land_availability (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    land VARCHAR NOT NULL CHECK (land IN ('ARABLE', 'PERMANENT', 'GRASSLAND', 'FALLOW')),
    value DOUBLE NOT NULL CHECK (value >= 0),
    PRIMARY KEY (region, land)
);
COMMENT ON TABLE land_availability IS 'land by type 2017: sums of CAPRI''s crop LEVL (build_capri_base.py: PERMANENT the permanent crops, GRASSLAND GRAS, FALLOW SETA, ARABLE the rest)';
INSERT INTO value_units SELECT 'land_availability', l, 'U_1000ha', 'capri', 'sums of CAPRI''s crop LEVL (U_1000ha)'
FROM (VALUES ('ARABLE'), ('PERMANENT'), ('GRASSLAND'), ('FALLOW')) t(l);

-- file: capri_data/2017/supply/animal_numbers.csv
-- layout: wide, unnamed
CREATE TABLE animal_numbers (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    herd VARCHAR NOT NULL CHECK (herd IN ('DCOW', 'SCOW', 'COWS', 'BULL', 'HEIF', 'CALV', 'PIGS', 'PIGF', 'HENS', 'POUL',
                                          'SHGM', 'SHGF')),
    value DOUBLE NOT NULL CHECK (value >= 0),
    PRIMARY KEY (region, herd)
);
COMMENT ON TABLE animal_numbers IS 'herd sizes 2017: CAPRI''s HERD item (build_capri_base.py HERD_MAP; COWS = DCOW + SCOW; PIGS = CAPRI''s SOWS herd, PIGF = the PIGS census less the sows); the loader renames SCOW, HEIF, HENS, POUL (loaders.HERD_ALIASES)';
INSERT INTO value_units SELECT 'animal_numbers', h, 'U_1000hd', 'builder', 'CAPRI''s HERD item; CAPRI''s unit table gives these animals'' LEVL in U_1000hd, not their HERD'
FROM (VALUES ('DCOW'), ('SCOW'), ('COWS'), ('BULL'), ('HEIF'), ('CALV'), ('PIGS'), ('PIGF'), ('SHGM'), ('SHGF')) t(h);
INSERT INTO value_units SELECT 'animal_numbers', h, 'U_Miohd', 'builder', 'CAPRI''s HERD item of poultry, read as million heads by the loader (loaders.POULTRY_MILLION_HEAD); CAPRI''s unit table gives HENS and POUF LEVL in U_Miohd'
FROM (VALUES ('HENS'), ('POUL')) t(h);

-- file: capri_data/2017/supply/yields.csv
-- layout: wide
CREATE TABLE yields (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    activity VARCHAR NOT NULL REFERENCES model_activities (code),
    value DOUBLE NOT NULL CHECK (value >= 0),
    PRIMARY KEY (region, activity)
);
COMMENT ON TABLE yields IS 'yields 2017: crops CAPRI''s YILD / 1000 level-weighted over the crop''s CAPRI activities (build_crop_economics_2017.py), GRAS CAPRI''s fresh-matter YILD unscaled, animals CAPRI''s YILD / 1000 per model head (build_animal_yields.py)';
INSERT INTO value_units SELECT 'yields', code, 'U_TonPerHa', 'builder', 'CAPRI''s YILD / 1000 (build_crop_economics_2017.py: t/ha)'
FROM model_activities WHERE kind = 'crop' AND code NOT IN ('GRAS', 'OCRO', 'OIND', 'NURS', 'FLOW');
INSERT INTO value_units VALUES
  ('yields', 'GRAS', 'U_kgperha', 'builder', 'CAPRI''s YILD of GRAS unscaled, fresh matter (loaders: converted to dry matter with CAPRI''s DRMA)'),
  ('yields', 'OCRO', 'U_ValueUnitPerHa', 'builder', 'CAPRI''s YILD / 1000: a value-measured crop, CAPRI''s MPRI an index near 1000 and MREV = YILD / 1000 x MPRI as for every crop (checked in res_17NL: NL320000)'),
  ('yields', 'OIND', 'U_ValueUnitPerHa', 'builder', 'CAPRI''s YILD / 1000: a value-measured crop, CAPRI''s MPRI an index near 1000 and MREV = YILD / 1000 x MPRI as for every crop (checked in res_17NL: NL320000)'),
  ('yields', 'NURS', 'U_ValueUnitPerHa', 'builder', 'CAPRI''s YILD / 1000: a value-measured crop, CAPRI''s MPRI an index near 1000 and MREV = YILD / 1000 x MPRI as for every crop (checked in res_17NL: NL320000)'),
  ('yields', 'FLOW', 'U_ValueUnitPerHa', 'builder', 'CAPRI''s YILD / 1000: a value-measured crop, CAPRI''s MPRI an index near 1000 and MREV = YILD / 1000 x MPRI as for every crop (checked in res_17NL: NL320000)'),
  ('yields', 'DCOW', 'U_TonPerHd', 'builder', 'build_animal_yields.py: t of milk per dairy cow'),
  ('yields', 'LAYS', 'U_TonPerHd', 'builder', 'build_animal_yields.py: CAPRI''s output unit / 1000 per hen (eggs)'),
  ('yields', 'PIGS', 'U_HdPerHd', 'builder', 'build_animal_yields.py: piglets per sow'),
  ('yields', 'BCOW', 'U_TonPerHd', 'builder', 'build_animal_yields.py: CAPRI''s YILD / 1000 per model head'),
  ('yields', 'BULL', 'U_TonPerHd', 'builder', 'build_animal_yields.py: t of meat per model head'),
  ('yields', 'CALV', 'U_TonPerHd', 'builder', 'build_animal_yields.py: CAPRI''s YILD / 1000 per model head'),
  ('yields', 'PIGF', 'U_TonPerHd', 'builder', 'build_animal_yields.py: t of meat per model head'),
  ('yields', 'BROI', 'U_TonPerHd', 'builder', 'build_animal_yields.py: t of meat per model head'),
  ('yields', 'SHGM', 'U_TonPerHd', 'builder', 'build_animal_yields.py: t of milk per model head'),
  ('yields', 'SHGF', 'U_TonPerHd', 'builder', 'build_animal_yields.py: t of meat per model head'),
  ('yields', 'HFRS', NULL, 'open', 'build_animal_yields.py: CAPRI''s YILD / 1000 per model head, level-weighted over members whose YILD measures different outputs (HEIL, HEIH kg of meat per head; HEIR one raised heifer as 1000): no single unit; the model reads animal yields only for DCOW (its ratio to base scales milk), the animals'' output is CAPRI''s output coefficients'),
  ('yields', 'OANI', NULL, 'open', 'value-measured like the value crops (MPRI near 1000, MREV = YILD / 1000 x MPRI: res_17DE DE110000), per unit of OANI''s level, an index (U_1unit): no catalogue unit; OANI is held at 0 in every region');

-- file: capri_data/2017/supply/variable_costs.csv
-- layout: wide
CREATE TABLE variable_costs (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    activity VARCHAR NOT NULL REFERENCES model_activities (code),
    value DOUBLE CHECK (value >= 0),      -- empty: no cost written (BCOW, HFRS, CALV, PIGS, LAYS, BROI)
    PRIMARY KEY (region, activity)
);
COMMENT ON TABLE variable_costs IS 'input costs 2017: crops CAPRI''s TOIN level-weighted per ha (build_crop_economics_2017.py); DCOW, BULL, PIGF, OANI CAPRI''s TOIN per CAPRI level unit (build_capri_base.intensive_values); SHGM, SHGF tools/lib/_sheep_goat.costs';
INSERT INTO value_units SELECT 'variable_costs', code, 'U_EuPerHa', 'builder', 'CAPRI''s TOIN per ha (build_crop_economics_2017.py: EUR/ha)'
FROM model_activities WHERE kind = 'crop';
INSERT INTO value_units SELECT 'variable_costs', a, 'U_EuPerHd', 'builder', 'CAPRI''s TOIN per head of CAPRI''s activity level (not per model head: capri_level_ratio)'
FROM (VALUES ('DCOW'), ('BULL'), ('PIGF'), ('SHGM'), ('SHGF')) t(a);
INSERT INTO value_units VALUES
  ('variable_costs', 'OANI', NULL, 'open', 'CAPRI''s TOIN per unit of OANI''s level, an index (U_1unit)');
INSERT INTO value_units SELECT 'variable_costs', a, NULL, 'open', 'the column is empty: no cost is written for it'
FROM (VALUES ('BCOW'), ('HFRS'), ('CALV'), ('PIGS'), ('LAYS'), ('BROI')) t(a);

-- file: capri_data/2017/market/producer_prices.csv
-- layout: unnamed
CREATE TABLE producer_prices (
    activity VARCHAR PRIMARY KEY REFERENCES model_activities (code),
    price DOUBLE NOT NULL CHECK (price >= 0)
);
COMMENT ON TABLE producer_prices IS 'EU producer prices 2017 (build_eu_producer_prices.py): crops from CAPRI''s regional prices; SHGM, SHGF from tools/lib/_sheep_goat.eu_prices; SETA''s 0 from sources/unsourced/producer_prices_no_builder.csv';
INSERT INTO value_units SELECT 'producer_prices', code, 'U_EuPerTon', 'builder', 'revenue over production of CAPRI''s YILD x MPRI (build_crop_economics_2017.py: EUR/t)'
FROM model_activities WHERE kind = 'crop' AND code NOT IN ('GRAS', 'SETA', 'OCRO', 'OIND', 'NURS', 'FLOW');
INSERT INTO value_units VALUES
  ('producer_prices', 'GRAS', 'U_EuPerTon', 'builder', 'CAPRI''s MREV over the dry-matter yield (build_crop_economics_2017.py): EUR per t of dry matter'),
  ('producer_prices', 'SETA', 'U_EuPerTon', 'builder', '0 by convention (producer_prices_no_builder.csv)');
-- (OCRO, OIND, NURS, FLOW have no EU producer price row)
INSERT INTO value_units VALUES
  ('producer_prices', 'SHGM', NULL, 'open', 'CAPREG''s regional prices of the activity weighted by the herds (tools/lib/_sheep_goat.py); the product and unit are to be checked'),
  ('producer_prices', 'SHGF', NULL, 'open', 'CAPREG''s regional prices of the activity weighted by the herds (tools/lib/_sheep_goat.py); the product and unit are to be checked');
-- (the other animals' rows, of unrecorded origin and read by no model code, were removed on 29 October 2026, K72)

-- rule: every item of a table has its unit declared, and every declared unit's item is in its table
SELECT t.tbl, t.item, 'no unit declared' AS what FROM (
    SELECT DISTINCT 'base_areas' AS tbl, activity AS item FROM base_areas UNION ALL
    SELECT DISTINCT 'land_availability', land FROM land_availability UNION ALL
    SELECT DISTINCT 'animal_numbers', herd FROM animal_numbers UNION ALL
    SELECT DISTINCT 'yields', activity FROM yields UNION ALL
    SELECT DISTINCT 'variable_costs', activity FROM variable_costs UNION ALL
    SELECT 'producer_prices', activity FROM producer_prices) t
WHERE NOT EXISTS (SELECT 1 FROM value_units v WHERE v.tbl = t.tbl AND v.item = t.item)
UNION ALL
SELECT v.tbl, v.item, 'unit declared for an item not in the table' FROM value_units v
WHERE v.tbl IN ('base_areas', 'land_availability', 'animal_numbers', 'yields', 'variable_costs', 'producer_prices')
  AND NOT EXISTS (
    SELECT 1 FROM (
        SELECT 'base_areas' AS tbl, activity AS item FROM base_areas UNION ALL
        SELECT 'land_availability', land FROM land_availability UNION ALL
        SELECT 'animal_numbers', herd FROM animal_numbers UNION ALL
        SELECT 'yields', activity FROM yields UNION ALL
        SELECT 'variable_costs', activity FROM variable_costs UNION ALL
        SELECT 'producer_prices', activity FROM producer_prices) t
    WHERE t.tbl = v.tbl AND t.item = v.item);

-- rule: every declared unit is in the unit catalogue
SELECT tbl, item, unit FROM value_units WHERE unit IS NOT NULL AND unit NOT IN (SELECT code FROM units);

-- rule: every region of the core tables has its crop areas, land, herds, yields and costs (same regional units)
SELECT r.region, list(t.tbl) AS missing_in FROM regional_units r CROSS JOIN
    (VALUES ('base_areas'), ('land_availability'), ('animal_numbers'), ('yields'), ('variable_costs')) t(tbl)
WHERE NOT EXISTS (SELECT 1 FROM base_areas b WHERE t.tbl = 'base_areas' AND b.region = r.region)
  AND NOT EXISTS (SELECT 1 FROM land_availability b WHERE t.tbl = 'land_availability' AND b.region = r.region)
  AND NOT EXISTS (SELECT 1 FROM animal_numbers b WHERE t.tbl = 'animal_numbers' AND b.region = r.region)
  AND NOT EXISTS (SELECT 1 FROM yields b WHERE t.tbl = 'yields' AND b.region = r.region)
  AND NOT EXISTS (SELECT 1 FROM variable_costs b WHERE t.tbl = 'variable_costs' AND b.region = r.region)
GROUP BY r.region;
