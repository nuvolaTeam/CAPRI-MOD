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

-- file: capri_data/codes/capri/landTypesMrk.csv
CREATE TABLE capri_landtypesmrk (code VARCHAR PRIMARY KEY, text VARCHAR);
COMMENT ON TABLE capri_landtypesmrk IS 'CAPRI landTypesMrk: the land types of the land market (sets.gms)';

-- file: capri_data/codes/capri/FODCRP.csv
CREATE TABLE capri_fodcrp (code VARCHAR PRIMARY KEY, text VARCHAR);
COMMENT ON TABLE capri_fodcrp IS 'CAPRI FODCRP: the fodder crops (sets.gms)';

-- file: capri_data/codes/capri/landTypes_to_pact.csv
CREATE TABLE capri_landtypes_to_pact (land_type VARCHAR NOT NULL, pact VARCHAR NOT NULL, PRIMARY KEY (land_type, pact));
COMMENT ON TABLE capri_landtypes_to_pact IS 'CAPRI landTypes_to_pact: the land type of each production activity (sets.gms)';

-- file: capri_data/codes/capri/cropDivGrps_mCact.csv
CREATE TABLE capri_cropdivgrps_mcact ("group" VARCHAR NOT NULL, mcact VARCHAR NOT NULL, PRIMARY KEY ("group", mcact));
COMMENT ON TABLE capri_cropdivgrps_mcact IS 'CAPRI cropDivGrps_mCact: the crop-diversification group of each annual crop (sets.gms)';

-- file: capri_data/codes/capri/PSG_TO_A.csv
CREATE TABLE capri_psg_to_a (psgroup VARCHAR NOT NULL, pact VARCHAR NOT NULL, PRIMARY KEY (psgroup, pact));
COMMENT ON TABLE capri_psg_to_a IS 'CAPRI psg_to_a: the activities of each premium group (policy/policy_sets.gms; a scheme''s rate per group reaches them, policy.gms)';

-- file: capri_data/codes/capri/MAP_RR.csv
CREATE TABLE capri_map_rr (region VARCHAR NOT NULL, member VARCHAR NOT NULL, PRIMARY KEY (region, member));
COMMENT ON TABLE capri_map_rr IS 'CAPRI MAP_RR: the members of each region (aggregates, member states, NUTS 1 and NUTS 2; policy.gms re-aggregates the declared premiums along it)';

-- file: capri_data/codes/capri/R_RAGG.csv
CREATE TABLE capri_r_ragg (region VARCHAR NOT NULL, "aggregate" VARCHAR NOT NULL, PRIMARY KEY (region, "aggregate"));
COMMENT ON TABLE capri_r_ragg IS 'CAPRI R_RAGG: the regions each region belongs to, itself included (policy.gms breaks the premium declarations down along it)';

-- file: capri_data/codes/capri/NUTS0.csv
CREATE TABLE capri_nuts0 (code VARCHAR PRIMARY KEY, text VARCHAR);
COMMENT ON TABLE capri_nuts0 IS 'CAPRI NUTS0: the countries (extend_rd_baseline.gms runs the RD money by them)';

-- file: capri_data/codes/capri/SRNUTS2.csv
CREATE TABLE capri_srnuts2 (code VARCHAR PRIMARY KEY, text VARCHAR);
COMMENT ON TABLE capri_srnuts2 IS 'CAPRI SRNUTS2: the NUTS 2 regions of the supply side (rd_logic.gms)';

-- file: capri_data/codes/capri/SRNUTS2_EXT.csv
CREATE TABLE capri_srnuts2_ext (code VARCHAR PRIMARY KEY, text VARCHAR);
COMMENT ON TABLE capri_srnuts2_ext IS 'CAPRI SRNUTS2_EXT: the NUTS 2 regions with RD money, the urban ones without agriculture included (extend_rd_baseline.gms)';

-- file: capri_data/codes/capri/PSDPAY_RD.csv
CREATE TABLE capri_psdpay_rd (code VARCHAR PRIMARY KEY, text VARCHAR);
COMMENT ON TABLE capri_psdpay_rd IS 'CAPRI PSDPAY_RD: the rural development payment schemes (rd_logic.gms)';

-- file: capri_data/codes/capri/PSDPAY_AE.csv
CREATE TABLE capri_psdpay_ae (code VARCHAR PRIMARY KEY, text VARCHAR);
COMMENT ON TABLE capri_psdpay_ae IS 'CAPRI PSDPAY_AE: the agri-environment payment schemes (rd_logic.gms)';

-- file: capri_data/codes/capri/REGAGGP.csv
CREATE TABLE capri_regaggp (code VARCHAR PRIMARY KEY, text VARCHAR);
COMMENT ON TABLE capri_regaggp IS 'CAPRI REGAGGP: the EU aggregates with premium declarations (policy.gms)';

-- file: capri_data/codes/capri/REGEU1015.csv
CREATE TABLE capri_regeu1015 (code VARCHAR PRIMARY KEY, text VARCHAR);
COMMENT ON TABLE capri_regeu1015 IS 'CAPRI REGEU1015: the EU-10 and EU-15 aggregates (policy.gms takes a member state''s premium declarations from them first)';

-- file: capri_data/codes/capri/MSAGG.csv
CREATE TABLE capri_msagg (code VARCHAR PRIMARY KEY, text VARCHAR);
COMMENT ON TABLE capri_msagg IS 'CAPRI MSAGG: the member states (policy.gms)';

-- file: capri_data/codes/capri/NUTS1A.csv
CREATE TABLE capri_nuts1a (code VARCHAR PRIMARY KEY, text VARCHAR);
COMMENT ON TABLE capri_nuts1a IS 'CAPRI NUTS1A: the NUTS 1 regions, a member state or unit without one standing for it (policy.gms)';

-- file: capri_data/codes/capri/SRNUTS1.csv
CREATE TABLE capri_srnuts1 (code VARCHAR PRIMARY KEY, text VARCHAR);
COMMENT ON TABLE capri_srnuts1 IS 'CAPRI SRNUTS1: the NUTS 1 regions a member state''s declared premiums are re-aggregated from (policy.gms)';


-- file: capri_data/codes/model_activity_classes.csv
CREATE TABLE model_activity_classes (
    code VARCHAR PRIMARY KEY REFERENCES model_activities (code),
    land_type VARCHAR,                     -- ARAC, GRAS or FRUN for a crop, empty for an animal
    cropdiv_group VARCHAR,                 -- the crop-diversification group of an annual crop
    fodder INTEGER NOT NULL CHECK (fodder IN (0, 1)),
    fixed INTEGER NOT NULL CHECK (fixed IN (0, 1)),
    organic_target VARCHAR CHECK (organic_target IN ('arable_pp', 'permanent_pp', 'uaa_pp')),   -- empty: not an organic crop
    organic_yield_gap INTEGER NOT NULL CHECK (organic_yield_gap IN (0, 1)),
    pesticide INTEGER NOT NULL CHECK (pesticide IN (0, 1)),
    price_source VARCHAR,                  -- the market whose price an animal earns (a model_commodities code)
    share_term_arable INTEGER NOT NULL CHECK (share_term_arable IN (0, 1)),
    young_outputs VARCHAR,                 -- the young animals in the activity's outputs (CAPRI OYANI), ';'-separated
    technologies INTEGER NOT NULL CHECK (technologies IN (1, 2)),   -- CAPRI's LEVL technologies (T; T1 and T2 at 0.5 each)
    source VARCHAR NOT NULL
);
COMMENT ON TABLE model_activity_classes IS 'the model''s activity classes (refactor stage 3, N6): land type, crop-diversification group, fodder and fixed flags, the organic target group and yield gap, the pesticide yield loss, the price source, the PMP share term''s arable set, the young-animal outputs and the number of CAPRI technologies; a declared table, checked against CAPRI''s sets by build_code_lists (a row that differs names its departure)';

-- file: capri_data/codes/model_cattle_splits.csv
CREATE TABLE model_cattle_splits (
    split VARCHAR PRIMARY KEY,             -- the model's animal and split (BULL, HFRS:rep, CALV:male, ...)
    gains VARCHAR NOT NULL REFERENCES capri_maact (code),
    gives VARCHAR NOT NULL REFERENCES capri_maact (code),
    source VARCHAR NOT NULL
);
COMMENT ON TABLE model_cattle_splits IS 'CAPRI''s cattle activities inside the model''s animals (refactor stage 3, N6): per split the CAPRI activity that gains the stalls and the one that gives them up; a declared table, checked against CAPRI''s MAACT and SplitActs by build_code_lists';

-- file: capri_data/codes/model_price_follows.csv
CREATE TABLE model_price_follows (
    activity VARCHAR PRIMARY KEY REFERENCES model_activities (code),
    commodity VARCHAR NOT NULL,            -- the market commodity whose price the activity's follows
    eu_market INTEGER NOT NULL CHECK (eu_market IN (0, 1)),   -- 1: in the EU's markets' price step too
    source VARCHAR NOT NULL
);
COMMENT ON TABLE model_price_follows IS 'the activities whose price follows a market commodity''s (refactor stage 4: beet follows sugar, durum wheat the wheat market, Norway''s raw milk the MILK market); a declared table';

-- file: capri_data/codes/model_land_types.csv
CREATE TABLE model_land_types (
    code VARCHAR PRIMARY KEY REFERENCES capri_landtypesmrk (code),
    in_land_market INTEGER NOT NULL CHECK (in_land_market IN (0, 1)),
    source VARCHAR NOT NULL
);
COMMENT ON TABLE model_land_types IS 'the land types of the model''s land market, in its column order (refactor stage 3, N6)';

-- file: capri_data/codes/model_commodities.csv
CREATE TABLE model_commodities (
    code VARCHAR PRIMARY KEY,
    capri_code VARCHAR NOT NULL UNIQUE REFERENCES capri_xx (code),
    mapping_source VARCHAR NOT NULL
);
COMMENT ON TABLE model_commodities IS 'the model''s market commodities (capri_mod/data/definitions.py MARKET_COMMODITIES) and CAPRI''s products';

-- file: capri_data/codes/regional_units.csv
CREATE TABLE regional_units (
    region VARCHAR PRIMARY KEY REFERENCES capri_rall (code),
    capri_ms VARCHAR NOT NULL REFERENCES capri_rall (code),
    country VARCHAR NOT NULL CHECK (length(country) = 2)
);
COMMENT ON TABLE regional_units IS 'CAPRI''s regional units of its supply models (EU27, Norway, UK, Turkey, Western Balkans; a run selects the countries outside the EU, run.supply_countries_outside_eu): unit, its member state, country';

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

-- file: capri_data/codes/capri/RM.csv
CREATE TABLE capri_rm (code VARCHAR PRIMARY KEY REFERENCES capri_rall (code), text VARCHAR);
COMMENT ON TABLE capri_rm IS 'CAPRI RM: the market regions of the global market model, in CAPRI''s set order (sets.gms; the market''s move onto CAPRI''s regions, MARKET_REGIONS_INVENTORY.md stage 1)';

-- file: capri_data/codes/capri/RMTP.csv
CREATE TABLE capri_rmtp (code VARCHAR PRIMARY KEY REFERENCES capri_rall (code), text VARCHAR);
COMMENT ON TABLE capri_rmtp IS 'CAPRI RMTP: the trade-policy blocks of the market model (tariffs and TRQs), in CAPRI''s set order (sets.gms)';

-- file: capri_data/codes/capri/RM_TO_RMTP.csv
CREATE TABLE capri_rm_to_rmtp (
    rm VARCHAR PRIMARY KEY REFERENCES capri_rm (code),
    rmtp VARCHAR NOT NULL REFERENCES capri_rmtp (code)
);
COMMENT ON TABLE capri_rm_to_rmtp IS 'CAPRI RM_TO_RMTP: the trade-policy block of each market region (sets.gms)';

-- file: capri_data/codes/capri/RMEU_to_RM.csv
CREATE TABLE capri_rmeu_to_rm (rmeu VARCHAR PRIMARY KEY, rm VARCHAR NOT NULL REFERENCES capri_rm (code));
COMMENT ON TABLE capri_rmeu_to_rm IS 'CAPRI RMEU_to_RM: the EU''s market blocks and their market regions (sets.gms)';

-- file: capri_data/codes/capri/PERM_NGRP.csv
CREATE TABLE capri_perm_ngrp (code VARCHAR PRIMARY KEY, text VARCHAR);
COMMENT ON TABLE capri_perm_ngrp IS 'CAPRI PERM_NGRP: the permanent crop groups of the fertiliser distribution (supply/define_ngrp_sets.gms)';

-- file: capri_data/codes/capri/CACT_TO_NGRP.csv
CREATE TABLE capri_cact_to_ngrp (cact VARCHAR PRIMARY KEY, ngrp VARCHAR NOT NULL);
COMMENT ON TABLE capri_cact_to_ngrp IS 'CAPRI CACT_TO_NGRP: the nutrient group of each crop activity (supply/define_ngrp_sets.gms)';

-- file: capri_data/codes/capri/FEED_TRD.csv
CREATE TABLE capri_feed_trd (code VARCHAR PRIMARY KEY, text VARCHAR);
COMMENT ON TABLE capri_feed_trd IS 'CAPRI FEED_TRD: the traded feed bulks, in CAPRI''s set order (global/fromimpact/sets.gms)';

-- file: capri_data/codes/capri/MS_RU.csv
CREATE TABLE capri_ms_ru (
    ms VARCHAR NOT NULL REFERENCES capri_rall (code),
    ru VARCHAR NOT NULL REFERENCES capri_rall (code),
    PRIMARY KEY (ms, ru)
);
COMMENT ON TABLE capri_ms_ru IS 'CAPRI''s member states and their regional units (MAP_RR restricted to MS x RU)';

-- rule: an animal's price source is a market commodity of the model
SELECT code, price_source FROM model_activity_classes
WHERE price_source IS NOT NULL AND price_source NOT IN (SELECT code FROM model_commodities);

-- file: capri_data/codes/capri/COLS.csv
CREATE TABLE capri_cols (code VARCHAR PRIMARY KEY, text VARCHAR);
COMMENT ON TABLE capri_cols IS 'CAPRI COLS, the column items of its data and results arrays DATA and DATAOUT (sets.gms)';

-- file: capri_data/codes/capri/ROWS.csv
CREATE TABLE capri_rows (code VARCHAR PRIMARY KEY, text VARCHAR);
COMMENT ON TABLE capri_rows IS 'CAPRI ROWS, the row items of its data and results arrays DATA and DATAOUT (sets.gms)';

-- file: capri_data/codes/results_items.csv
CREATE TABLE results_items (
    block VARCHAR NOT NULL,
    item VARCHAR NOT NULL,
    item_dim VARCHAR NOT NULL CHECK (item_dim IN ('cols', 'rows')),
    capri_cols VARCHAR,
    capri_rows VARCHAR,
    applies_to VARCHAR,
    unit VARCHAR,
    capri_source VARCHAR,
    PRIMARY KEY (block, item)
);
COMMENT ON TABLE results_items IS 'The items of the long results table (capri_mod/io_results.py) and their CAPRI codes in DATAOUT''s cols and rows ("*": the model''s own coordinate translated, "act": the activity''s code in rows; applies_to: the activities or products the mapping holds for, empty for all; empty codes: no CAPRI item or not determined)';

-- rule: a results item's CAPRI codes are both given or both empty, are in CAPRI's COLS and ROWS ("*" apart), and cite
-- where CAPRI sets them
SELECT block, item, capri_cols, capri_rows FROM results_items
WHERE (capri_cols = '') <> (capri_rows = '')
   OR (capri_cols <> '' AND (capri_source IS NULL OR capri_source = ''))
   OR (capri_cols NOT IN ('', '*') AND capri_cols NOT IN (SELECT code FROM capri_cols))
   OR (capri_rows NOT IN ('', '*', 'act') AND capri_rows NOT IN (SELECT code FROM capri_rows));
