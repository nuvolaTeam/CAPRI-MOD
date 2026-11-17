-- The comparison files under capri_data/validation (CAPRI's results and the model's against them), 29 October 2026. Structure from the files; units open.

-- file: capri_data/validation/capri_eu27_levels_2017_capreg.csv
CREATE TABLE val_capri_eu27_levels_2017_capreg (
    act VARCHAR NOT NULL,
    val DOUBLE NOT NULL,
    PRIMARY KEY (act)
);
COMMENT ON TABLE val_capri_eu27_levels_2017_capreg IS 'EU27 level per animal activity (BULF, HEIF, HEIR, PIGF, POUF, SOWS, HENS; 7 rows), read by tools/check/compare_baseline_capri.py for the growth 2017-2030; no builder, origin not documented (KNOWN_ISSUES K103).';
INSERT INTO value_units VALUES
  ('val_capri_eu27_levels_2017_capreg', 'val', NULL, 'open', 'capri_eu27_levels_2017_capreg.val: unit to be established');

-- file: capri_data/validation/capri_eu27_levels_2030_ref.csv
CREATE TABLE val_capri_eu27_levels_2030_ref (
    act VARCHAR NOT NULL,
    val DOUBLE NOT NULL,
    PRIMARY KEY (act)
);
COMMENT ON TABLE val_capri_eu27_levels_2030_ref IS 'CAPRI''s EU27 activity levels in 2030 (act, val; 1000 ha or 1000 heads); no builder: its reader tools/check/compare_baseline_capri.py describes it as EU27yr19 LEVL extracted from markmarket_greendeal_1730et_base_1717.';
INSERT INTO value_units VALUES
  ('val_capri_eu27_levels_2030_ref', 'val', NULL, 'open', 'capri_eu27_levels_2030_ref.val: unit to be established');

-- file: capri_data/validation/eu_outlook_2020_2030.csv
CREATE TABLE val_eu_outlook_2020_2030 (
    "table" DOUBLE NOT NULL,
    title VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "2016" VARCHAR NOT NULL,
    "2017" VARCHAR NOT NULL,
    "2018" VARCHAR NOT NULL,
    "2019" VARCHAR NOT NULL,
    "2020" VARCHAR NOT NULL,
    "2021" VARCHAR NOT NULL,
    "2022" VARCHAR NOT NULL,
    "2023" VARCHAR NOT NULL,
    "2024" VARCHAR NOT NULL,
    "2025" VARCHAR NOT NULL,
    "2026" VARCHAR NOT NULL,
    "2027" VARCHAR NOT NULL,
    "2028" VARCHAR NOT NULL,
    "2029" VARCHAR NOT NULL,
    "2030" VARCHAR NOT NULL,
    PRIMARY KEY (title, "item", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026", "2027", "2028", "2029", "2030")
);
COMMENT ON TABLE val_eu_outlook_2020_2030 IS 'DG AGRI''s EU agricultural outlook 2020-2030 (December 2020), annex tables 8.8-8.44: per table, title and item one value per year 2016-2030, extracted from the PDF (tools/build/build_eu_outlook_2030.py, not in the pipeline trace).';
INSERT INTO value_units VALUES
  ('val_eu_outlook_2020_2030', 'table', NULL, 'open', 'eu_outlook_2020_2030.table: unit to be established');

-- file: capri_data/validation/greendeal_2030/capri_unit_values_ref_2030.csv
CREATE TABLE val_capri_unit_values_ref_2030 (
    region VARCHAR NOT NULL,
    product VARCHAR NOT NULL,
    uvag DOUBLE NOT NULL,
    PRIMARY KEY (region, product)
);
COMMENT ON TABLE val_capri_unit_values_ref_2030 IS 'CAPRI''s 2030 unit values UVAG per region and product from the dataOut of res_2_1730greendeal_refdefaulta (CAPRI''s 2030 Green Deal baseline) (tools/build/extract_capri_marginal_terms.py, tag ini).';
INSERT INTO value_units VALUES
  ('val_capri_unit_values_ref_2030', 'uvag', NULL, 'open', 'capri_unit_values_ref_2030.uvag: unit to be established');

-- file: capri_data/validation/n_cascade_capri_gd2030.csv
CREATE TABLE val_n_cascade_capri_gd2030 (
    region VARCHAR NOT NULL,
    "key" VARCHAR,
    col VARCHAR NOT NULL,
    row VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL
);
COMMENT ON TABLE val_n_cascade_capri_gd2030 IS 'CAPRI''s per-head N losses (MANN, NH3/NOX/N2O at grazing, housing, application, GASANI, RUNANI), option shares and regional mineral-fertiliser rows, per region, key, col, row, from res_2_1730greendeal_refpol_endotech_all_inidefaulta (tools/build/build_n_cascade_validation.py, not in the trace).';
INSERT INTO value_units VALUES
  ('val_n_cascade_capri_gd2030', 'value', NULL, 'open', 'n_cascade_capri_gd2030.value: unit to be established');


-- file: capri_data/validation/farm_to_fork_2030/jrc121368_eu27.csv
CREATE TABLE val_jrc121368_eu27 (
    indicator VARCHAR NOT NULL,
    value_pct DOUBLE NOT NULL,
    kind VARCHAR NOT NULL CHECK (kind IN ('table', 'text', 'figure')),
    source VARCHAR NOT NULL,
    PRIMARY KEY (indicator)
);
COMMENT ON TABLE val_jrc121368_eu27 IS 'JRC121368 (Barreiro-Hurle et al. 2021, EUR 30317 EN), the F2F and BDS targets and CAP 2014-2020 scenario: EU27 % changes from the 2030 baseline of the indicators tools/check/compare_runs.py computes, each with its table, page or text; "figure" marks a reading measured on the report''s chart (kept by hand, 13 November 2026)';
INSERT INTO value_units VALUES
  ('val_jrc121368_eu27', 'value_pct', 'U_percent', 'capri', 'JRC121368: % change from the baseline in 2030');

-- The four CAPRI comparison tables kept xz-compressed until 14 November 2026 (outside the declarations then), plain CSV
-- since (the project lead: the inputs are CSV).

-- file: capri_data/validation/greendeal_2030/capri_marginal_terms_ref_2030.csv
CREATE TABLE val_capri_marginal_terms_ref_2030 (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, activity, "item")
);
COMMENT ON TABLE val_capri_marginal_terms_ref_2030 IS 'CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta) per region and activity: the marginal terms D_* and the items LEVL, MREV, TOOU, TOIN, MANN, PRME, ... of its dataOut (tools/build/extract_capri_marginal_terms.py, tag ref); read by the 2030 builders as CAPRI''s 2030 levels and premiums and by the checks.';
INSERT INTO value_units VALUES
  ('val_capri_marginal_terms_ref_2030', 'value', NULL, 'open', 'capri_marginal_terms_ref_2030.value: the unit of the item (CAPRI''s units per item)');

-- file: capri_data/validation/greendeal_2030/capri_gd_effect.csv
CREATE TABLE val_capri_gd_effect (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    ref DOUBLE,
    scen DOUBLE,
    pct_change DOUBLE,
    PRIMARY KEY (region, activity, "item")
);
COMMENT ON TABLE val_capri_gd_effect IS 'CAPRI''s Green Deal 2030 step against its reference, per region, activity and item: the reference and scenario values and the % change (tools/build/extract_capri_gd_pair.py); empty where one of the runs has no record.';
INSERT INTO value_units VALUES
  ('val_capri_gd_effect', 'ref', NULL, 'open', 'capri_gd_effect.ref: the unit of the item'),
  ('val_capri_gd_effect', 'scen', NULL, 'open', 'capri_gd_effect.scen: the unit of the item'),
  ('val_capri_gd_effect', 'pct_change', 'U_percent', 'builder', '% change from the reference');

-- file: capri_data/validation/greendeal_2030/capri_gd_market_2030.csv
CREATE TABLE val_capri_gd_market_2030 (
    region VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    commodity VARCHAR NOT NULL,
    ref DOUBLE,
    scen DOUBLE,
    PRIMARY KEY (region, "item", commodity)
);
COMMENT ON TABLE val_capri_gd_market_2030 IS 'CAPRI''s 2030 market of its Green Deal step and its reference, per market region, item and commodity (tools/build/extract_capri_gd_market.py).';
INSERT INTO value_units VALUES
  ('val_capri_gd_market_2030', 'ref', NULL, 'open', 'capri_gd_market_2030.ref: the unit of the item (kt, EUR/t)'),
  ('val_capri_gd_market_2030', 'scen', NULL, 'open', 'capri_gd_market_2030.scen: the unit of the item (kt, EUR/t)');

-- file: capri_data/validation/coupled_support_2030/capri_vcs_effect.csv
CREATE TABLE val_capri_vcs_effect (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    ref DOUBLE,
    novcs DOUBLE,
    pct_change DOUBLE,
    PRIMARY KEY (region, activity, "item")
);
COMMENT ON TABLE val_capri_vcs_effect IS 'CAPRI''s 2030 reference against its run without voluntary coupled support, per region, activity and item (tools/build/extract_capri_vcs_pair.py); empty where one of the runs has no record.';
INSERT INTO value_units VALUES
  ('val_capri_vcs_effect', 'ref', NULL, 'open', 'capri_vcs_effect.ref: the unit of the item'),
  ('val_capri_vcs_effect', 'novcs', NULL, 'open', 'capri_vcs_effect.novcs: the unit of the item'),
  ('val_capri_vcs_effect', 'pct_change', 'U_percent', 'builder', '% change from the reference');
