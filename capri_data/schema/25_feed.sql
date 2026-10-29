-- Inputs under capri_data/2017/feed. Generated structure (types, NOT NULL, keys) from the files on 29 October 2026; units open where no
-- builder or CAPRI file states them (value_units).

-- file: capri_data/2017/feed/feed_cereal_mix_2030.csv
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
