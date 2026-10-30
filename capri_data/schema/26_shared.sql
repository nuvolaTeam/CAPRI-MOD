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

-- file: capri_data/shared/trade_regions.csv
CREATE TABLE shr_trade_regions (
    trade_region VARCHAR NOT NULL,
    capri_region VARCHAR,
    country VARCHAR,
    source VARCHAR NOT NULL,
    UNIQUE (trade_region, country)
);
COMMENT ON TABLE shr_trade_regions IS 'The market''s trade regions in their order (no builder: a declared table, a source per row): trade region, CAPRI''s region code in its market data (market region or trade block; ROW: none), the countries (two-letter codes; EU27: none, its countries are the member states of eu_market_blocks.csv). Read by capri_mod/data/definitions.py (TRADE_REGIONS, the non-EU supply-model regions) and tools/build/recalibrate_trade_2017.py (REGION_MAP).';

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

-- file: capri_data/shared/trade_flows_2017.csv
CREATE TABLE shr_trade_flows_2017 (
    exporter VARCHAR NOT NULL,
    importer VARCHAR NOT NULL,
    SWHE DOUBLE NOT NULL,
    DWHE DOUBLE NOT NULL,
    BARL DOUBLE NOT NULL,
    CORN DOUBLE NOT NULL,
    OCER DOUBLE NOT NULL,
    RAPE DOUBLE NOT NULL,
    SUNF DOUBLE NOT NULL,
    SOYA DOUBLE NOT NULL,
    OOIL DOUBLE NOT NULL,
    SUGB DOUBLE NOT NULL,
    SUGR DOUBLE NOT NULL,
    POTA DOUBLE NOT NULL,
    PULS DOUBLE NOT NULL,
    TOMA DOUBLE NOT NULL,
    OVEG DOUBLE NOT NULL,
    APPL DOUBLE NOT NULL,
    OFRU DOUBLE NOT NULL,
    CITR DOUBLE NOT NULL,
    WINE DOUBLE NOT NULL,
    OLIV DOUBLE NOT NULL,
    MILK DOUBLE NOT NULL,
    BUTR DOUBLE NOT NULL,
    SKIM DOUBLE NOT NULL,
    CHES DOUBLE NOT NULL,
    WHEY DOUBLE NOT NULL,
    BEEF DOUBLE NOT NULL,
    PORK DOUBLE NOT NULL,
    POUL DOUBLE NOT NULL,
    SHGM DOUBLE NOT NULL,
    EGGS DOUBLE NOT NULL,
    FATS DOUBLE NOT NULL,
    OFOD_M DOUBLE NOT NULL,
    SGMT DOUBLE NOT NULL,
    RAPO DOUBLE NOT NULL,
    SUNO DOUBLE NOT NULL,
    SOYO DOUBLE NOT NULL,
    RAPC DOUBLE NOT NULL,
    SUNC DOUBLE NOT NULL,
    SOYC DOUBLE NOT NULL,
    PRIMARY KEY (exporter, importer)
);
COMMENT ON TABLE shr_trade_flows_2017 IS 'Recalibrate the trade matrix from CAPRI''s 2017 capmod result. (tools/build/recalibrate_trade_2017.py)';
INSERT INTO value_units VALUES
  ('shr_trade_flows_2017', 'SWHE', NULL, 'open', 'trade_flows_2017.SWHE: unit to be established'),
  ('shr_trade_flows_2017', 'DWHE', NULL, 'open', 'trade_flows_2017.DWHE: unit to be established'),
  ('shr_trade_flows_2017', 'BARL', NULL, 'open', 'trade_flows_2017.BARL: unit to be established'),
  ('shr_trade_flows_2017', 'CORN', NULL, 'open', 'trade_flows_2017.CORN: unit to be established'),
  ('shr_trade_flows_2017', 'OCER', NULL, 'open', 'trade_flows_2017.OCER: unit to be established'),
  ('shr_trade_flows_2017', 'RAPE', NULL, 'open', 'trade_flows_2017.RAPE: unit to be established'),
  ('shr_trade_flows_2017', 'SUNF', NULL, 'open', 'trade_flows_2017.SUNF: unit to be established'),
  ('shr_trade_flows_2017', 'SOYA', NULL, 'open', 'trade_flows_2017.SOYA: unit to be established'),
  ('shr_trade_flows_2017', 'OOIL', NULL, 'open', 'trade_flows_2017.OOIL: unit to be established'),
  ('shr_trade_flows_2017', 'SUGB', NULL, 'open', 'trade_flows_2017.SUGB: unit to be established'),
  ('shr_trade_flows_2017', 'SUGR', NULL, 'open', 'trade_flows_2017.SUGR: unit to be established'),
  ('shr_trade_flows_2017', 'POTA', NULL, 'open', 'trade_flows_2017.POTA: unit to be established'),
  ('shr_trade_flows_2017', 'PULS', NULL, 'open', 'trade_flows_2017.PULS: unit to be established'),
  ('shr_trade_flows_2017', 'TOMA', NULL, 'open', 'trade_flows_2017.TOMA: unit to be established'),
  ('shr_trade_flows_2017', 'OVEG', NULL, 'open', 'trade_flows_2017.OVEG: unit to be established'),
  ('shr_trade_flows_2017', 'APPL', NULL, 'open', 'trade_flows_2017.APPL: unit to be established'),
  ('shr_trade_flows_2017', 'OFRU', NULL, 'open', 'trade_flows_2017.OFRU: unit to be established'),
  ('shr_trade_flows_2017', 'CITR', NULL, 'open', 'trade_flows_2017.CITR: unit to be established'),
  ('shr_trade_flows_2017', 'WINE', NULL, 'open', 'trade_flows_2017.WINE: unit to be established'),
  ('shr_trade_flows_2017', 'OLIV', NULL, 'open', 'trade_flows_2017.OLIV: unit to be established'),
  ('shr_trade_flows_2017', 'MILK', NULL, 'open', 'trade_flows_2017.MILK: unit to be established'),
  ('shr_trade_flows_2017', 'BUTR', NULL, 'open', 'trade_flows_2017.BUTR: unit to be established'),
  ('shr_trade_flows_2017', 'SKIM', NULL, 'open', 'trade_flows_2017.SKIM: unit to be established'),
  ('shr_trade_flows_2017', 'CHES', NULL, 'open', 'trade_flows_2017.CHES: unit to be established'),
  ('shr_trade_flows_2017', 'WHEY', NULL, 'open', 'trade_flows_2017.WHEY: unit to be established'),
  ('shr_trade_flows_2017', 'BEEF', NULL, 'open', 'trade_flows_2017.BEEF: unit to be established'),
  ('shr_trade_flows_2017', 'PORK', NULL, 'open', 'trade_flows_2017.PORK: unit to be established'),
  ('shr_trade_flows_2017', 'POUL', NULL, 'open', 'trade_flows_2017.POUL: unit to be established'),
  ('shr_trade_flows_2017', 'SHGM', NULL, 'open', 'trade_flows_2017.SHGM: unit to be established'),
  ('shr_trade_flows_2017', 'EGGS', NULL, 'open', 'trade_flows_2017.EGGS: unit to be established'),
  ('shr_trade_flows_2017', 'FATS', NULL, 'open', 'trade_flows_2017.FATS: unit to be established'),
  ('shr_trade_flows_2017', 'OFOD_M', NULL, 'open', 'trade_flows_2017.OFOD_M: unit to be established'),
  ('shr_trade_flows_2017', 'SGMT', NULL, 'open', 'trade_flows_2017.SGMT: unit to be established'),
  ('shr_trade_flows_2017', 'RAPO', NULL, 'open', 'trade_flows_2017.RAPO: unit to be established'),
  ('shr_trade_flows_2017', 'SUNO', NULL, 'open', 'trade_flows_2017.SUNO: unit to be established'),
  ('shr_trade_flows_2017', 'SOYO', NULL, 'open', 'trade_flows_2017.SOYO: unit to be established'),
  ('shr_trade_flows_2017', 'RAPC', NULL, 'open', 'trade_flows_2017.RAPC: unit to be established'),
  ('shr_trade_flows_2017', 'SUNC', NULL, 'open', 'trade_flows_2017.SUNC: unit to be established'),
  ('shr_trade_flows_2017', 'SOYC', NULL, 'open', 'trade_flows_2017.SOYC: unit to be established');
