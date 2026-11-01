-- The code lists: CAPRI's own sets and the model's codes mapped to them (tools/build/build_code_lists.py).
-- Declarations of the data batch (docs/design/DATA_SCHEMA_DUCKDB.md): tools/check/validate_data.py creates each table,
-- loads the CSV named by the "-- file:" line above it and enforces the types, keys, ranges and references declared here.
-- Files load in name order (00_ first), so later declarations can reference these tables.

-- file: capri_data/codes/capri/PACT.csv
CREATE TABLE capri_pact (code VARCHAR PRIMARY KEY, text VARCHAR);
COMMENT ON TABLE capri_pact IS 'CAPRI PACT, all production activities (sets.gms; CAPMOD restart file sim_ini_21730)';

-- file: capri_data/codes/capri/MPACT.csv
CREATE TABLE capri_mpact (code VARCHAR PRIMARY KEY REFERENCES capri_pact (code), text VARCHAR);
COMMENT ON TABLE capri_mpact IS 'CAPRI MPACT(PACT), production activities in the supply model';

-- file: capri_data/codes/capri/MCACT.csv
CREATE TABLE capri_mcact (code VARCHAR PRIMARY KEY REFERENCES capri_pact (code), text VARCHAR);
COMMENT ON TABLE capri_mcact IS 'CAPRI MCACT(PACT), crop activities in the supply model';

-- file: capri_data/codes/capri/MAACT.csv
CREATE TABLE capri_maact (code VARCHAR PRIMARY KEY REFERENCES capri_pact (code), text VARCHAR);
COMMENT ON TABLE capri_maact IS 'CAPRI MAACT(PACT), animal activities in the supply model';

-- file: capri_data/codes/capri/XX.csv
CREATE TABLE capri_xx (code VARCHAR PRIMARY KEY, text VARCHAR);
COMMENT ON TABLE capri_xx IS 'CAPRI XX, the market model''s products (arm/arm_sets.gms)';

-- file: capri_data/codes/capri/XX1.csv
CREATE TABLE capri_xx1 (code VARCHAR PRIMARY KEY, text VARCHAR);
COMMENT ON TABLE capri_xx1 IS 'CAPRI''s XX1: the market model''s products with the non-agricultural good, income, the land inputs and feed energy (arm/arm_sets.gms)';

-- file: capri_data/codes/capri/FEED_TO_O.csv
CREATE TABLE capri_feed_to_o (feed VARCHAR NOT NULL, row VARCHAR NOT NULL, PRIMARY KEY (feed, row));
COMMENT ON TABLE capri_feed_to_o IS 'CAPRI''s FEED_TO_O: the feed bulks and their products (sets.gms)';

-- file: capri_data/codes/capri/RALL.csv
CREATE TABLE capri_rall (code VARCHAR PRIMARY KEY, text VARCHAR);
COMMENT ON TABLE capri_rall IS 'CAPRI RALL, all regional units of the CAPRI system (sets.gms)';

-- file: capri_data/codes/model_activities.csv
CREATE TABLE model_activities (
    code VARCHAR PRIMARY KEY,
    kind VARCHAR NOT NULL CHECK (kind IN ('crop', 'animal')),
    capri_codes VARCHAR NOT NULL,          -- ';'-joined CAPRI PACT codes summed into the model's activity (rule below)
    capmod_codes VARCHAR NOT NULL,         -- the same with CAPRI's supply-model activities carrying PMP terms (GRAS: GRAE;GRAI)
    mapping_source VARCHAR NOT NULL
);
COMMENT ON TABLE model_activities IS 'the model''s activities (capri_mod/data/definitions.py CROPS, ANIMALS) and their CAPRI activities: a declared code list, a source per row (tools/lib/_model_codes.py reads it for the builders)';

-- file: capri_data/codes/model_commodities.csv
CREATE TABLE model_commodities (
    code VARCHAR PRIMARY KEY,
    capri_code VARCHAR NOT NULL UNIQUE REFERENCES capri_xx (code),
    mapping_source VARCHAR NOT NULL
);
COMMENT ON TABLE model_commodities IS 'the model''s market commodities (capri_mod/data/definitions.py MARKET_COMMODITIES) and CAPRI''s products';

-- file: capri_data/shared/regional_units.csv
CREATE TABLE regional_units (
    region VARCHAR PRIMARY KEY REFERENCES capri_rall (code),
    capri_ms VARCHAR NOT NULL REFERENCES capri_rall (code),
    country VARCHAR NOT NULL CHECK (length(country) = 2)
);
COMMENT ON TABLE regional_units IS 'CAPRI''s regional units the model runs on (27 October 2026): unit, its member state, country';

-- file: capri_data/codes/units.csv
CREATE TABLE units (
    code VARCHAR PRIMARY KEY,
    description VARCHAR NOT NULL,
    capri VARCHAR NOT NULL CHECK (capri IN ('yes', 'no'))   -- no: the model's own unit (model_units.csv)
);
COMMENT ON TABLE units IS 'the unit catalogue: CAPRI''s set capri_u (gams/CAPRIunits.gms) and the model''s own units (tools/build/build_unit_catalogue.py)';

-- The unit of each value, per table and item (a wide table's value column holds a different unit per column: t/ha for
-- a crop, t per head for milk). Filled by the declaration of each table (INSERT below its CREATE TABLE).
--   status  capri    the unit is stated by CAPRI (CAPRIunits.gms, CAPRIunits.gdx or CAPRI's documentation)
--           builder  stated by the table's builder from CAPRI's item it transforms; not found stated by CAPRI
--           open     not established (unit empty): the value is used as it is, its unit is to be checked
CREATE TABLE value_units (
    tbl VARCHAR NOT NULL,
    item VARCHAR NOT NULL,
    unit VARCHAR,
    status VARCHAR NOT NULL CHECK (status IN ('capri', 'builder', 'open')),
    basis VARCHAR NOT NULL,
    PRIMARY KEY (tbl, item),
    CHECK ((unit IS NULL) = (status = 'open'))
);

-- rule: every CAPRI code of a model activity is a CAPRI production activity
SELECT a.code, c.capri_code
FROM (SELECT code, unnest(string_split(capri_codes, ';')) AS capri_code FROM model_activities) c
JOIN model_activities a USING (code)
WHERE c.capri_code NOT IN (SELECT code FROM capri_pact);

-- rule: no CAPRI activity is summed into two model activities
SELECT capri_code, list(code) AS model_codes
FROM (SELECT code, unnest(string_split(capri_codes, ';')) AS capri_code FROM model_activities)
GROUP BY capri_code HAVING count(*) > 1;

-- rule: every CAPRI supply-model code of a model activity is a CAPRI production activity
SELECT code, capri_code
FROM (SELECT code, unnest(string_split(capmod_codes, ';')) AS capri_code FROM model_activities)
WHERE capri_code NOT IN (SELECT code FROM capri_pact);

-- rule: no CAPRI supply-model activity is summed into two model activities
SELECT capri_code, list(code) AS model_codes
FROM (SELECT code, unnest(string_split(capmod_codes, ';')) AS capri_code FROM model_activities)
GROUP BY capri_code HAVING count(*) > 1;

-- rule: a member state of the regional units is its own unit's member state code (ends in 000000)
SELECT region, capri_ms FROM regional_units WHERE capri_ms NOT LIKE '%000000';

-- file: capri_data/codes/capri/MS_RU.csv
CREATE TABLE capri_ms_ru (
    ms VARCHAR NOT NULL REFERENCES capri_rall (code),
    ru VARCHAR NOT NULL REFERENCES capri_rall (code),
    PRIMARY KEY (ms, ru)
);
COMMENT ON TABLE capri_ms_ru IS 'CAPRI''s member states and their regional units (MAP_RR restricted to MS x RU)';
