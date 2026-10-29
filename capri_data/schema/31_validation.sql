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

-- file: capri_data/validation/greendeal_2030/capri_unit_values_ini_2030.csv
CREATE TABLE val_capri_unit_values_ini_2030 (
    region VARCHAR NOT NULL,
    product VARCHAR NOT NULL,
    uvag DOUBLE NOT NULL,
    PRIMARY KEY (region, product)
);
COMMENT ON TABLE val_capri_unit_values_ini_2030 IS 'CAPRI''s 2030 unit values UVAG per region and product from the dataOut of res_2_1730greendeal_refpol_endotech_all_inidefaulta (tools/build/extract_capri_marginal_terms.py, tag ini).';
INSERT INTO value_units VALUES
  ('val_capri_unit_values_ini_2030', 'uvag', NULL, 'open', 'capri_unit_values_ini_2030.uvag: unit to be established');

-- file: capri_data/validation/greendeal_2030/capri_unit_values_max_2030.csv
CREATE TABLE val_capri_unit_values_max_2030 (
    region VARCHAR NOT NULL,
    product VARCHAR NOT NULL,
    uvag DOUBLE NOT NULL,
    PRIMARY KEY (region, product)
);
COMMENT ON TABLE val_capri_unit_values_max_2030 IS 'CAPRI''s 2030 unit values UVAG per region and product from the dataOut of res_2_1730greendeal_refpol_endotech_all_maxdefaulta (tools/build/extract_capri_marginal_terms.py, tag max).';
INSERT INTO value_units VALUES
  ('val_capri_unit_values_max_2030', 'uvag', NULL, 'open', 'capri_unit_values_max_2030.uvag: unit to be established');

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

