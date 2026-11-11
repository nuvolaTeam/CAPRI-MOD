-- Inputs under capri_data/2017/feed. Generated structure (types, NOT NULL, keys) from the files on 29 October 2026; units open where no
-- builder or CAPRI file states them (value_units).

-- file: capri_data/baselines/capri_greendeal_ref/2017_2030/feed/feed_cereal_mix_2030.csv
CREATE TABLE feed_feed_cereal_mix_2030 (
    cereal VARCHAR NOT NULL,
    fedm_kt DOUBLE NOT NULL,
    PRIMARY KEY (cereal)
);
COMMENT ON TABLE feed_feed_cereal_mix_2030 IS 'CAPRI''s feed bulks in the market for the member states (arm/market_model.gms feedBlkPrice_, feedShareEqu_). (tools/build/build_feed_bulks.py)';
INSERT INTO value_units VALUES
  ('feed_feed_cereal_mix_2030', 'fedm_kt', NULL, 'open', 'feed_cereal_mix_2030.fedm_kt: unit to be established');

-- file: capri_data/2017/feed/livestock_feed_coef.csv
-- layout: wide, unnamed
CREATE TABLE feed_livestock_feed_coef (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal_bulk VARCHAR NOT NULL,             -- <model animal>_<cereals | protein | energy>
    value DOUBLE CHECK (value >= 0),
    PRIMARY KEY (region, animal_bulk)
);
COMMENT ON TABLE feed_livestock_feed_coef IS 'CAPRI''s purchased feed per model head by bulk: FCER (cereals), FPRO (protein), FENE (energy), LEVL x item over the model''s heads / 1000 (tools/build/build_livestock_output_coef.py)';
INSERT INTO value_units SELECT 'feed_livestock_feed_coef', c, NULL, 'open', 'CAPRI''s feed item per head / 1000 (t per head if the item is kg)' FROM (VALUES ('BCOW_cereals'), ('BROI_cereals'), ('BULL_cereals'), ('CALV_cereals'), ('DCOW_cereals'), ('HFRS_cereals'), ('LAYS_cereals'), ('PIGF_cereals'), ('PIGS_cereals'), ('SHGF_cereals'), ('SHGM_cereals'), ('BCOW_protein'), ('BROI_protein'), ('BULL_protein'), ('CALV_protein'), ('DCOW_protein'), ('HFRS_protein'), ('LAYS_protein'), ('PIGF_protein'), ('PIGS_protein'), ('SHGF_protein'), ('SHGM_protein'), ('BCOW_energy'), ('BROI_energy'), ('BULL_energy'), ('CALV_energy'), ('DCOW_energy'), ('HFRS_energy'), ('LAYS_energy'), ('PIGF_energy'), ('PIGS_energy'), ('SHGF_energy'), ('SHGM_energy')) x(c);

-- rule: the animal of each feed column is a model animal and its bulk one of the three
SELECT DISTINCT animal_bulk FROM feed_livestock_feed_coef
WHERE split_part(animal_bulk, '_', 1) NOT IN (SELECT code FROM model_activities WHERE kind = 'animal')
   OR split_part(animal_bulk, '_', 2) NOT IN ('cereals', 'protein', 'energy');

-- file: capri_data/2017/feed/feed_ration_2017.csv
CREATE TABLE feed_feed_ration_2017 (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    block VARCHAR NOT NULL CHECK (block IN ('ration', 'req', 'content', 'price', 'capri_slope', 'capri_slope_2030')),
    feed VARCHAR,
    nutrient VARCHAR,
    "value" DOUBLE NOT NULL,
    UNIQUE (region, animal, block, feed, nutrient),
    CHECK ((block = 'req') = (feed IS NULL)),
    CHECK ((block IN ('req', 'content')) = (nutrient IS NOT NULL))
);
COMMENT ON TABLE feed_feed_ration_2017 IS 'the EU feed rations per model region and animal from CAPRI''s 2017 regional results (res_17*, dataOut; per head = CAPRI total / the model''s herd): ration (kg per head and year, by feed), req (per head and year, by nutrient: ENNE energy units, CRPR kg, DMIN/DMAX kg dry matter), content (per kg fresh feed, by feed and nutrient), price (EUR/kg, by feed), capri_slope and capri_slope_2030 (CAPRI''s feed-PMP slopes of pmppar_17* and of the 2030 calibration pmppar_21730, by feed); tools/build/build_feed_ration.py; feed_ration_2017.json until 31 October 2026 (capri_mod/data/nested_tables.py)';
INSERT INTO value_units VALUES
  ('feed_feed_ration_2017', 'value', NULL, 'open', 'feed_ration_2017.value: the unit of its block (the comment)');

-- file: capri_data/2017/feed/fodder_balance_2017.csv
CREATE TABLE feed_fodder_balance_2017 (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    fodder VARCHAR NOT NULL CHECK (fodder IN ('FGRA', 'FMAI', 'FOFA', 'FROO')),
    crop VARCHAR NOT NULL REFERENCES model_activities (code),
    u_t_per_ha DOUBLE NOT NULL,
    value_eur_t DOUBLE NOT NULL,
    PRIMARY KEY (region, fodder, crop)
);
COMMENT ON TABLE feed_fodder_balance_2017 IS 'the regional balances of the non-tradable fodder (CAPRI supply_model.gms SUPBAL_): the crops producing it (one row each: grass FGRA from GRAE and GRAI since S2, 7 November 2026), the usable fresh fodder per ha (base fodder use / base area) and its base value (CAPRI''s UVAG); built from feed_ration_2017.csv, base_areas.csv and animal_numbers.csv (tools/build/build_fodder_balance.py; fodder_balance_2017.json until 31 October 2026; capri_mod/data/nested_tables.py)';
INSERT INTO value_units VALUES
  ('feed_fodder_balance_2017', 'u_t_per_ha', 'U_TonPerHa', 'builder', 'fodder_balance_2017.u_t_per_ha: t fresh fodder per ha (the builder)'),
  ('feed_fodder_balance_2017', 'value_eur_t', NULL, 'open', 'fodder_balance_2017.value_eur_t: EUR per t (the builder; no unit code in the catalogue)');

-- file: capri_data/2017/feed/fodder_balance_2017_use.csv
CREATE TABLE feed_fodder_balance_2017_use (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    fodder VARCHAR NOT NULL CHECK (fodder IN ('FGRA', 'FMAI', 'FOFA', 'FROO')),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    use_t_head DOUBLE NOT NULL,
    PRIMARY KEY (region, fodder, animal)
);
COMMENT ON TABLE feed_fodder_balance_2017_use IS 'the fodder each animal eats per head in a fodder balance (fodder_balance_2017.csv), from the base ration (tools/build/build_fodder_balance.py)';
INSERT INTO value_units VALUES
  ('feed_fodder_balance_2017_use', 'use_t_head', 'U_TonPerHd', 'builder', 'fodder_balance_2017_use.use_t_head: t per head (the builder)');
