-- Inputs under capri_data/2017/feed. Generated structure (types, NOT NULL, keys) from the files on 29 October 2026; units open where no
-- builder or CAPRI file states them (value_units).

-- file: capri_data/baselines/capri_greendeal_ref/1730/feed/feed_cereal_mix_2030.csv
CREATE TABLE feed_feed_cereal_mix_2030 (
    cereal VARCHAR NOT NULL,
    fedm_kt DOUBLE NOT NULL,
    PRIMARY KEY (cereal)
);
COMMENT ON TABLE feed_feed_cereal_mix_2030 IS 'CAPRI''s feed bulks in the market for the member states (arm/market_model.gms feedBlkPrice_, feedShareEqu_). (tools/build/build_feed_bulks.py)';
INSERT INTO value_units VALUES
  ('feed_feed_cereal_mix_2030', 'fedm_kt', NULL, 'open', 'feed_cereal_mix_2030.fedm_kt: unit to be established');

-- file: capri_data/baselines/capri_greendeal_ref/1730/feed/fodder_value_2030.csv
CREATE TABLE feed_fodder_value_2030 (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    fodder VARCHAR NOT NULL CHECK (fodder IN ('FGRA', 'FMAI', 'FOFA', 'FROO')),
    value_eur_t DOUBLE NOT NULL CHECK (value_eur_t > 0),
    uvag_capri_2030 DOUBLE NOT NULL CHECK (uvag_capri_2030 > 0),
    PRIMARY KEY (region, fodder)
);
COMMENT ON TABLE feed_fodder_value_2030 IS 'CAPRI''s 2030 unit value of the fed non-tradable fodders (UVAG, the dual of SUPBAL_ per t fed) as the fodder balance''s base dual, in 2017 money (KNOWN_ISSUES K161; tools/build/build_fodder_value_2030.py)';
INSERT INTO value_units VALUES
  ('feed_fodder_value_2030', 'value_eur_t', NULL, 'open', 'EUR of 2017 per t fed (CAPRI''s UVAG over its 2030 deflator; the builder; no unit code in the catalogue)'),
  ('feed_fodder_value_2030', 'uvag_capri_2030', NULL, 'open', 'CAPRI''s UVAG, EUR of 2030 per t fed (the builder; no unit code in the catalogue)');

-- file: capri_data/baselines/capri_greendeal_ref/1730/feed/milk_for_feeding_2030.csv
CREATE TABLE feed_milk_for_feeding_2030 (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    product VARCHAR NOT NULL CHECK (product IN ('COMF', 'SGMF')),
    feed VARCHAR NOT NULL CHECK (feed IN ('FCOM', 'FSGM')),
    animal VARCHAR NOT NULL CHECK (animal IN ('DCOW', 'BCOW', 'SHGM')),
    output_t_head DOUBLE NOT NULL CHECK (output_t_head > 0),
    value_eur_t DOUBLE NOT NULL CHECK (value_eur_t > 0),
    uvag_capri_2030 DOUBLE NOT NULL CHECK (uvag_capri_2030 > 0),
    PRIMARY KEY (region, product, animal)
);
COMMENT ON TABLE feed_milk_for_feeding_2030 IS 'CAPRI''s milk for feeding at its 2030 calibration point (COMF, SGMF: non-tradable outputs fed as FCOM, FSGM; SUPBAL_ with losses): the producing animals'' output per head and the milk''s value (UVAG, the balance''s dual) in 2017 money (KNOWN_ISSUES K189; tools/build/build_milk_for_feeding_2030.py)';
INSERT INTO value_units VALUES
  ('feed_milk_for_feeding_2030', 'output_t_head', NULL, 'open', 't of milk for feeding per head (CAPRI''s dataOut output per head over 1000; the builder; no unit code in the catalogue)'),
  ('feed_milk_for_feeding_2030', 'value_eur_t', NULL, 'open', 'EUR of 2017 per t (CAPRI''s UVAG over its 2030 deflator; the builder; no unit code in the catalogue)'),
  ('feed_milk_for_feeding_2030', 'uvag_capri_2030', NULL, 'open', 'CAPRI''s UVAG, EUR of 2030 per t (the builder; no unit code in the catalogue)');

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

-- file: capri_data/2017/feed/manure_output_params.csv
CREATE TABLE feed_manure_output_params (
    symbol VARCHAR NOT NULL CHECK (symbol IN ('p_NutContManureKgM3', 'p_addExcrPerkgMilk', 'p_carcassShare', 'p_startWgt', 'p_reqfcnlim', 'p_LUUnits', 'p_pigsReqHighWgt', 'p_pigsReqLowWgt')),
    key1 VARCHAR NOT NULL,                   -- CAPRI's first key (manure type ANTYP, manure row, CAPRI activity)
    key2 VARCHAR,                            -- CAPRI's second key (manure row MANN/MANP/MANK; DAYS/DAILY of p_reqfcnlim; the pig tables' item)
    key3 VARCHAR,                            -- p_reqfcnlim's bound (up, lo)
    value DOUBLE NOT NULL                    -- one row per symbol and key (key2, key3 empty where the symbol has fewer)
);
COMMENT ON TABLE feed_manure_output_params IS 'CAPRI''s literal parameters of its manure output functions, star 3.0: feed/feed_decl.gms''s p_NutContManureKgM3 (kg N, P2O5, K2O per m3 of cattle, swine and poultry manure), p_addExcrPerkgMilk (kg per kg of milk), p_carcassShare (carcass over live weight), p_startWgt (kg live weight at the start of fattening or raising), p_reqfcnlim (the requirement functions'' limits on days and daily gains, g per day), CAPRI''s p_LUUnits (livestock units per head, dat/policy/livestock_units.gms), and the fattened pigs'' requirements by weight class p_pigsReqHighWgt and p_pigsReqLowWgt (key1 the class, key2 the item: XDUF days, XALW kg live weight, CRPR kg crude protein, ...; dat/feed/porkreq.gms); read by capri_mod/feed/equations/req_or_man_fnc.py (feed/req_or_man_fnc.gms with %1 = man; tools/build/build_manure_output_params.py)';
INSERT INTO value_units VALUES ('feed_manure_output_params', 'value', NULL, 'open', 'the unit of its symbol (the comment)');

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
COMMENT ON TABLE feed_fodder_balance_2017 IS 'the regional balances of the non-tradable fodder (CAPRI supply_model.gms SUPBAL_): the crops producing it (one row each: grass FGRA from GRAE and GRAI since 7 November 2026), the usable fresh fodder per ha (base fodder use / base area) and its base value (CAPRI''s UVAG); built from feed_ration_2017.csv, base_areas.csv and animal_numbers.csv (tools/build/build_fodder_balance.py; fodder_balance_2017.json until 31 October 2026; capri_mod/data/nested_tables.py)';
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
