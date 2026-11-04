-- Inputs under capri_data/shared. Generated structure (types, NOT NULL, keys) from the files on 29 October 2026; units open where no
-- builder or CAPRI file states them (value_units).

-- file: capri_data/shared/capri_member_state_codes.csv
CREATE TABLE shr_capri_member_state_codes (
    nuts_prefix VARCHAR NOT NULL,
    capri_ms VARCHAR NOT NULL,
    source VARCHAR NOT NULL,
    PRIMARY KEY (nuts_prefix, capri_ms, source)
);
COMMENT ON TABLE shr_capri_member_state_codes IS 'capri_member_state_codes (no builder: a declared table)';

-- rule: a regional unit's member state is one of CAPRI's member state codes (this table: XX000000,
-- or TUR for Turkey's units, sets.gms MAP_RR TUR.SET.R_TUR)
SELECT region, capri_ms FROM regional_units WHERE capri_ms NOT IN (SELECT capri_ms FROM shr_capri_member_state_codes);

-- file: capri_data/shared/capri_units_nuts2024.csv
CREATE TABLE shr_capri_units_nuts2024 (
    capri_unit VARCHAR NOT NULL,
    nuts2024 VARCHAR NOT NULL,
    "group" BIGINT NOT NULL,
    uaa_ha DOUBLE,
    weight DOUBLE NOT NULL,
    PRIMARY KEY (capri_unit, nuts2024)
);
COMMENT ON TABLE shr_capri_units_nuts2024 IS 'CAPRI''s regional units -> current NUTS-2 regions (NUTS 2024), with area weights, for reporting results on current (tools/build/build_nuts2024_reporting.py)';
INSERT INTO value_units VALUES
  ('shr_capri_units_nuts2024', 'group', NULL, 'open', 'capri_units_nuts2024.group: unit to be established'),
  ('shr_capri_units_nuts2024', 'uaa_ha', NULL, 'open', 'capri_units_nuts2024.uaa_ha: unit to be established'),
  ('shr_capri_units_nuts2024', 'weight', NULL, 'open', 'capri_units_nuts2024.weight: unit to be established');

-- file: capri_data/shared/eu_market_blocks.csv
CREATE TABLE shr_eu_market_blocks (
    ms VARCHAR NOT NULL,
    block VARCHAR NOT NULL,
    source VARCHAR NOT NULL,
    PRIMARY KEY (ms, block, source)
);
COMMENT ON TABLE shr_eu_market_blocks IS 'The EU''s trade blocks of CAPRI''s market (market step E, eu_blocks): member state -> block, from CAPRI''s region (tools/build/build_eu_market_blocks.py)';

-- file: capri_data/shared/model_parameters.csv
CREATE TABLE shr_model_parameters (
    name VARCHAR NOT NULL,
    "key" VARCHAR,
    "value" DOUBLE NOT NULL,
    unit VARCHAR NOT NULL,
    kind VARCHAR NOT NULL,
    source VARCHAR NOT NULL,
    used_in VARCHAR NOT NULL
);
COMMENT ON TABLE shr_model_parameters IS 'model_parameters (no builder: a declared table)';
INSERT INTO value_units VALUES
  ('shr_model_parameters', 'value', NULL, 'open', 'model_parameters.value: unit to be established');

-- file: capri_data/shared/rms.csv
CREATE TABLE shr_rms (
    rms VARCHAR NOT NULL,
    PRIMARY KEY (rms)
);
COMMENT ON TABLE shr_rms IS 'rms (no builder: a declared table)';

-- file: capri_data/shared/nuts_version_correspondence.csv
CREATE TABLE shr_nuts_version_correspondence (
    capri_code VARCHAR NOT NULL,
    nuts_code VARCHAR,
    UNIQUE (capri_code, nuts_code)
);
COMMENT ON TABLE shr_nuts_version_correspondence IS 'CAPRI''s 8-character region codes and their NUTS codes across coding-scheme versions, in order (a code can have several: IT110000 -> IT11 and ITC1; an empty nuts_code for a code without one), from CAPRI''s gams/compile_rdp_data/build_general_set_structure.gms, with 75 NUTS-2 pairs added in October 2026 (each verified by CAPRI''s total agricultural area against the model region''s base area and a second variable), NO090000 -> NO03 and PL500000 -> PL81 removed as unconfirmed, and FI190000 -> FI1C removed; read by tools/lib/_model_regions.py (with its CORR_FIXES, SPLITS_MERGES). nuts_version_correspondence.json until 31 October 2026, kept by hand (capri_mod/data/nested_tables.py)';

-- the flags of the code tables declared in 00_codes.sql (value_units exists from here)
INSERT INTO value_units VALUES
  ('model_activity_classes', 'fodder', NULL, 'open', 'a flag (1: a fodder crop)'),
  ('model_activity_classes', 'fixed', NULL, 'open', 'a flag (1: held at its base level)'),
  ('model_activity_classes', 'organic_yield_gap', NULL, 'open', 'a flag (1: the organic yield gap applies)'),
  ('model_price_follows', 'eu_market', NULL, 'open', 'a flag (1: in the EU markets'' price step)'),
  ('model_activity_classes', 'pesticide', NULL, 'open', 'a flag (1: the pesticide yield loss reaches the crop)'),
  ('model_activity_classes', 'share_term_arable', NULL, 'open', 'a flag (1: in the PMP share term''s arable denominator)'),
  ('model_land_types', 'in_land_market', NULL, 'open', 'a flag (1: a column of the land market)');
