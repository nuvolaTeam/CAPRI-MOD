-- The scenarios (capri_data/scenarios/<name>/, capri_mod/projection/scenario_io.py; the project lead's rule, 31 October
-- 2026: a scenario's settings and its reference data in separate files, in a scenario folder). settings.toml holds the
-- scenario's settings (name, source, vintage, base year, target years, notes, provenance); growth.csv and regional.csv
-- its projection factors, cumulative multipliers relative to the base year (capri_mod/projection/trajectory.py). Until
-- 31 October 2026 each scenario was one JSON file in capri_data/trajectories. The null scenario holds settings only.

-- file: capri_data/scenarios/capri_ref_2030/growth.csv
CREATE TABLE scn_capri_ref_2030_growth (
    block VARCHAR NOT NULL CHECK (block IN ('yields', 'demand', 'world_prices', 'herds', 'land')),
    "item" VARCHAR NOT NULL,
    "year" INTEGER NOT NULL,
    factor DOUBLE NOT NULL CHECK (factor >= 0),
    PRIMARY KEY (block, "item", "year")
);
COMMENT ON TABLE scn_capri_ref_2030_growth IS 'CAPRI''s 2030 reference as growth factors per block and activity: the per-activity median of the per-region ratios LEVL or YILD in res_2_1730greendeal_refpol_endotech_all_ini / CAPRI''s 2017 results, with the model''s activity aliases (tools/build/build_trajectory_capri_ref.py, build_trajectory_model_keys.py)';
INSERT INTO value_units VALUES
  ('scn_capri_ref_2030_growth', 'year', NULL, 'open', 'the target year (a calendar year, not a quantity)'),
  ('scn_capri_ref_2030_growth', 'factor', NULL, 'open', 'growth.factor: a ratio to the base year (the builder)');

-- file: capri_data/scenarios/capri_ref_2030/regional.csv
CREATE TABLE scn_capri_ref_2030_regional (
    block VARCHAR NOT NULL CHECK (block IN ('yields', 'demand', 'world_prices', 'herds', 'land')),
    region VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "year" INTEGER NOT NULL,
    factor DOUBLE NOT NULL CHECK (factor >= 0),
    PRIMARY KEY (block, region, "item", "year")
);
COMMENT ON TABLE scn_capri_ref_2030_regional IS 'CAPRI''s 2030 reference as per-region growth factors (regions keyed by CAPRI''s four-character codes and by the model''s regions; the factor where the 2017 value is > 0; 0 for a level the 2030 reference does not list, GAMS storing no zero) (tools/build/build_trajectory_capri_ref.py, build_trajectory_model_keys.py)';
INSERT INTO value_units VALUES
  ('scn_capri_ref_2030_regional', 'year', NULL, 'open', 'the target year (a calendar year, not a quantity)'),
  ('scn_capri_ref_2030_regional', 'factor', NULL, 'open', 'regional.factor: a ratio to the base year (the builder)');

-- file: capri_data/scenarios/captrd_2030/growth.csv
CREATE TABLE scn_captrd_2030_growth (
    block VARCHAR NOT NULL CHECK (block IN ('yields', 'demand', 'world_prices', 'herds', 'land')),
    "item" VARCHAR NOT NULL,
    "year" INTEGER NOT NULL,
    factor DOUBLE NOT NULL CHECK (factor > 0),
    PRIMARY KEY (block, "item", "year")
);
COMMENT ON TABLE scn_captrd_2030_growth IS 'CAPRI''s trend projection (CAPTRD results_1770, p_result series) as growth factors per block and activity: per-activity medians of the per-region cumulative ratios 2030 / 2017 of YILD and LEVL, with the model''s activity aliases (tools/build/build_captrd_trajectory.py)';
INSERT INTO value_units VALUES
  ('scn_captrd_2030_growth', 'year', NULL, 'open', 'the target year (a calendar year, not a quantity)'),
  ('scn_captrd_2030_growth', 'factor', NULL, 'open', 'growth.factor: a ratio to the base year (the builder)');

-- file: capri_data/scenarios/captrd_2030/regional.csv
CREATE TABLE scn_captrd_2030_regional (
    block VARCHAR NOT NULL CHECK (block IN ('yields', 'demand', 'world_prices', 'herds', 'land')),
    region VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "year" INTEGER NOT NULL,
    factor DOUBLE NOT NULL CHECK (factor > 0),
    PRIMARY KEY (block, region, "item", "year")
);
COMMENT ON TABLE scn_captrd_2030_regional IS 'CAPRI''s trend projection as per-region growth factors (where the base value is >= 1.0), keyed by CAPRI''s four-character codes and by the model''s regions (tools/build/build_captrd_trajectory.py)';
INSERT INTO value_units VALUES
  ('scn_captrd_2030_regional', 'year', NULL, 'open', 'the target year (a calendar year, not a quantity)'),
  ('scn_captrd_2030_regional', 'factor', NULL, 'open', 'regional.factor: a ratio to the base year (the builder)');
