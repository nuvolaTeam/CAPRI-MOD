-- The extracts under capri_data/sources (CAPRI's files and outside sources the builders read), 29 October 2026. Structure (types, NOT NULL, keys) from the files; each table's origin in provenance (01_provenance.sql); units open where no builder or CAPRI file states them.

-- file: capri_data/sources/arm/capri_supply_elas_market_1717.csv
CREATE TABLE src_capri_supply_elas_market_1717 (
    region VARCHAR NOT NULL,
    prod VARCHAR NOT NULL,
    wrt VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, prod, wrt)
);
COMMENT ON TABLE src_capri_supply_elas_market_1717 IS 'Every record of CAPRI''s p_elasSupp(region, prod, wrt, ''CAL'') from elas1717defaulta.gdx (gdxdump p_elasSupp.txt): the supply elasticity of prod with respect to the price of wrt, per market region (countries and trade regions), 73528 rows (tools/build/build_capri_supply_elas_market.py).';
INSERT INTO value_units VALUES
  ('src_capri_supply_elas_market_1717', 'value', NULL, 'open', 'capri_supply_elas_market_1717.value: unit to be established');

-- file: capri_data/sources/arm/capri_supply_elas_young_1720.csv
CREATE TABLE src_capri_supply_elas_young_1720 (
    region VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, "item")
);
COMMENT ON TABLE src_capri_supply_elas_young_1720 IS 'CAPRI''s calibrated supply elasticities of young animals (YCAM, YCAF, YBUL, YHEI, YCOW, YPIG) per member state: p_ElasSupp(MS, item, item, ''CAL'') from results/arm/supply_elas_2_1720<MS>defaulta.gdx, the 2020 calibration (tools/build/build_young_animal_elasticities.py).';
INSERT INTO value_units VALUES
  ('src_capri_supply_elas_young_1720', 'value', NULL, 'open', 'capri_supply_elas_young_1720.value: unit to be established');

-- file: capri_data/sources/baseline_pmp/estnlp_vb.csv
CREATE TABLE src_estnlp_vb (
    region VARCHAR NOT NULL,
    group1 VARCHAR NOT NULL,
    group2 VARCHAR NOT NULL,
    "level" DOUBLE NOT NULL,
    PRIMARY KEY (region, group1, group2)
);
COMMENT ON TABLE src_estnlp_vb IS 'CAPRI''s econometric estimate VB.L(region, group1, group2) from dat/estnlp/results.gdx (around 2004), the crop-group terms CAPRI derives its PMP terms from; kept for the record and for checks (tools/build/build_pmp_2030.py).';
INSERT INTO value_units VALUES
  ('src_estnlp_vb', 'level', NULL, 'open', 'estnlp_vb.level: unit to be established');

-- file: capri_data/sources/baseline_pmp/estnlp_vd.csv
CREATE TABLE src_estnlp_vd (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    "level" DOUBLE NOT NULL,
    PRIMARY KEY (region, activity)
);
COMMENT ON TABLE src_estnlp_vd IS 'CAPRI''s econometric estimate VD.L(region, activity) from dat/estnlp/results.gdx (around 2004), the activity slopes CAPRI derives its PMP terms from; kept for the record and for checks (tools/build/build_pmp_2030.py).';
INSERT INTO value_units VALUES
  ('src_estnlp_vd', 'level', NULL, 'open', 'estnlp_vd.level: unit to be established');

-- file: capri_data/sources/baseline_pmp/intensity_q_capri2030.csv
CREATE TABLE src_intensity_q_capri2030 (
    model_region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (model_region, activity)
);
COMMENT ON TABLE src_intensity_q_capri2030 IS 'Per model region (a CAPRI regional unit) and activity of the intensity splits (DCOL/DCOH, BULL/BULH, HEIL/HEIH, GRAE/GRAI, ...): the curvature on the activity level, its technology block of CAPRI''s exported 2030 p_pmpQuadTechn collapsed, c = 1/(1'' Q^-1 1) (tools/build/build_intensity_q_2030.py).';
INSERT INTO value_units VALUES
  ('src_intensity_q_capri2030', 'value', NULL, 'open', 'intensity_q_capri2030.value: unit to be established');

-- file: capri_data/sources/baseline_pmp/intensity_q_recipe2017.csv
CREATE TABLE src_intensity_q_recipe2017 (
    model_region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (model_region, activity)
);
COMMENT ON TABLE src_intensity_q_recipe2017 IS 'Per model region (a CAPRI regional unit) and activity of the intensity splits: the curvature on the activity level, c = 1/(1'' Q^-1 1), from capri-mod''s own 2017 terms by CAPRI''s recipe (recipe_2017_quad_techn.csv); read for the set-aside split''s base-year weights (tools/build/build_intensity_q_2030.py).';
INSERT INTO value_units VALUES
  ('src_intensity_q_recipe2017', 'value', NULL, 'open', 'intensity_q_recipe2017.value: unit to be established');

-- file: capri_data/sources/baseline_pmp/intensity_q_recipe2030.csv
CREATE TABLE src_intensity_q_recipe2030 (
    model_region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (model_region, activity)
);
COMMENT ON TABLE src_intensity_q_recipe2030 IS 'Per model region (a CAPRI regional unit) and activity of the intensity splits: the curvature on the activity level, c = 1/(1'' Q^-1 1), from capri-mod''s own 2030 terms by CAPRI''s recipe (recipe_2030_quad_techn.csv) (tools/build/build_intensity_q_2030.py).';
INSERT INTO value_units VALUES
  ('src_intensity_q_recipe2030', 'value', NULL, 'open', 'intensity_q_recipe2030.value: unit to be established');

-- file: capri_data/sources/baseline_pmp/pmp_cnst_2030.csv
CREATE TABLE src_pmp_cnst_2030 (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    tech VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, activity, tech)
);
COMMENT ON TABLE src_pmp_cnst_2030 IS 'CAPRI''s linear PMP terms p_pmpCnst(region, activity, tech) of its 2030 baseline calibration, from the project lead''s gdxdump of output/results/baseline/pmppar_21730<CC>defaulta.gdx; CAPRI codes, unchanged (tools/build/build_pmp_2030.py).';
INSERT INTO value_units VALUES
  ('src_pmp_cnst_2030', 'value', NULL, 'open', 'pmp_cnst_2030.value: unit to be established');

-- file: capri_data/sources/baseline_pmp/pmp_cnst_landtypes_2030.csv
CREATE TABLE src_pmp_cnst_landtypes_2030 (
    region VARCHAR NOT NULL,
    landtype VARCHAR NOT NULL,
    "value" VARCHAR NOT NULL,
    PRIMARY KEY (region, landtype, "value")
);
COMMENT ON TABLE src_pmp_cnst_landtypes_2030 IS 'CAPRI''s linear land-supply terms p_pmpCnstLandTypes(region, landtype) of its 2030 baseline calibration, from pmppar_21730<CC>defaulta.gdx; the text exogenousLandSupply, CAPRI''s marker of an exogenous land type, is kept (tools/build/build_pmp_2030.py).';

-- file: capri_data/sources/baseline_pmp/pmp_feed_inp_coeff_2030.csv
CREATE TABLE src_pmp_feed_inp_coeff_2030 (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    tech VARCHAR NOT NULL,
    feed VARCHAR NOT NULL,
    coef VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, activity, tech, feed, coef)
);
COMMENT ON TABLE src_pmp_feed_inp_coeff_2030 IS 'CAPRI''s feed input coefficients of its 2030 baseline calibration per region, animal activity, tech and feed, with coef CNST or SLOP, from pmppar_21730<CC>defaulta.gdx; CAPRI codes, unchanged (tools/build/build_pmp_2030.py).';
INSERT INTO value_units VALUES
  ('src_pmp_feed_inp_coeff_2030', 'value', NULL, 'open', 'pmp_feed_inp_coeff_2030.value: unit to be established');

-- file: capri_data/sources/baseline_pmp/pmp_quad_landtypes_2030.csv
CREATE TABLE src_pmp_quad_landtypes_2030 (
    region VARCHAR NOT NULL,
    landtype1 VARCHAR NOT NULL,
    landtype2 VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, landtype1, landtype2)
);
COMMENT ON TABLE src_pmp_quad_landtypes_2030 IS 'CAPRI''s quadratic land-supply terms p_pmpQuadLandTypes(region, landtype1, landtype2) of its 2030 baseline calibration (land market, Trustee_land), from pmppar_21730<CC>defaulta.gdx (tools/build/build_pmp_2030.py).';
INSERT INTO value_units VALUES
  ('src_pmp_quad_landtypes_2030', 'value', NULL, 'open', 'pmp_quad_landtypes_2030.value: unit to be established');

-- file: capri_data/sources/baseline_pmp/pmp_quad_pact_2030.csv
CREATE TABLE src_pmp_quad_pact_2030 (
    region VARCHAR NOT NULL,
    group1 VARCHAR NOT NULL,
    group2 VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, group1, group2)
);
COMMENT ON TABLE src_pmp_quad_pact_2030 IS 'CAPRI''s quadratic PMP terms on crop-group levels p_pmpQuadPact(region, group1, group2) (CERE, CER2, OILS, OARA, FARA; stored for group1 <= group2 in CAPRI''s order) of its 2030 baseline calibration, from pmppar_21730<CC>defaulta.gdx (tools/build/build_pmp_2030.py).';
INSERT INTO value_units VALUES
  ('src_pmp_quad_pact_2030', 'value', NULL, 'open', 'pmp_quad_pact_2030.value: unit to be established');

-- file: capri_data/sources/baseline_pmp/pmp_quad_techn_2030.csv
CREATE TABLE src_pmp_quad_techn_2030 (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    tech1 VARCHAR NOT NULL,
    tech2 VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, activity, tech1, tech2)
);
COMMENT ON TABLE src_pmp_quad_techn_2030 IS 'CAPRI''s quadratic PMP terms p_pmpQuadTechn(region, activity, tech1, tech2) of its 2030 baseline calibration (crops T1/T2, animals T), from the project lead''s gdxdump of pmppar_21730<CC>defaulta.gdx (tools/build/build_pmp_2030.py).';
INSERT INTO value_units VALUES
  ('src_pmp_quad_techn_2030', 'value', NULL, 'open', 'pmp_quad_techn_2030.value: unit to be established');

-- file: capri_data/sources/baseline_pmp/recipe_2017_quad_pact.csv
CREATE TABLE src_recipe_2017_quad_pact (
    region VARCHAR NOT NULL,
    group1 VARCHAR NOT NULL,
    group2 VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, group1, group2)
);
COMMENT ON TABLE src_recipe_2017_quad_pact IS 'capri-mod''s own crop-group PMP terms for 2017 (region, group1, group2, value; the format of p_pmpQuadPact), computed with CAPRI''s recipe (supply/define_pmp_terms.gms, supply/pmp_terms/*) per CAPRI region (tools/build/build_pmp_recipe.py --year 2017).';
INSERT INTO value_units VALUES
  ('src_recipe_2017_quad_pact', 'value', NULL, 'open', 'recipe_2017_quad_pact.value: unit to be established');

-- file: capri_data/sources/baseline_pmp/recipe_2017_quad_techn.csv
CREATE TABLE src_recipe_2017_quad_techn (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    tech1 VARCHAR NOT NULL,
    tech2 VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, activity, tech1, tech2)
);
COMMENT ON TABLE src_recipe_2017_quad_techn IS 'capri-mod''s own activity PMP terms for 2017 (region, activity, tech1, tech2, value; the format of p_pmpQuadTechn), computed with CAPRI''s recipe (supply/define_pmp_terms.gms, supply/pmp_terms/*) per CAPRI region (tools/build/build_pmp_recipe.py --year 2017).';
INSERT INTO value_units VALUES
  ('src_recipe_2017_quad_techn', 'value', NULL, 'open', 'recipe_2017_quad_techn.value: unit to be established');

-- file: capri_data/sources/baseline_pmp/recipe_2030_quad_pact.csv
CREATE TABLE src_recipe_2030_quad_pact (
    region VARCHAR NOT NULL,
    group1 VARCHAR NOT NULL,
    group2 VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, group1, group2)
);
COMMENT ON TABLE src_recipe_2030_quad_pact IS 'capri-mod''s own crop-group PMP terms for 2030 (region, group1, group2, value; the format of p_pmpQuadPact), computed with CAPRI''s recipe (supply/define_pmp_terms.gms, supply/pmp_terms/*) per CAPRI region (tools/build/build_pmp_recipe.py --year 2030).';
INSERT INTO value_units VALUES
  ('src_recipe_2030_quad_pact', 'value', NULL, 'open', 'recipe_2030_quad_pact.value: unit to be established');

-- file: capri_data/sources/baseline_pmp/recipe_2030_quad_techn.csv
CREATE TABLE src_recipe_2030_quad_techn (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    tech1 VARCHAR NOT NULL,
    tech2 VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, activity, tech1, tech2)
);
COMMENT ON TABLE src_recipe_2030_quad_techn IS 'capri-mod''s own activity PMP terms for 2030 (region, activity, tech1, tech2, value; the format of p_pmpQuadTechn), computed with CAPRI''s recipe (supply/define_pmp_terms.gms, supply/pmp_terms/*) per CAPRI region (tools/build/build_pmp_recipe.py --year 2030).';
INSERT INTO value_units VALUES
  ('src_recipe_2030_quad_techn', 'value', NULL, 'open', 'recipe_2030_quad_techn.value: unit to be established');

-- file: capri_data/sources/baseline_pmp/simini_21730_data.csv
CREATE TABLE src_simini_21730_data (
    region VARCHAR NOT NULL,
    col VARCHAR NOT NULL,
    row VARCHAR NOT NULL,
    "year" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, col, row, "year")
);
COMMENT ON TABLE src_simini_21730_data IS 'CAPRI''s DATA(region, col, row, year) of sim_ini_21730.gdx, the start file of the 2030 baseline simulation, at year Y and BAS (682267 rows); no builder: tools/build/build_pmp_recipe.py, its reader, describes it as extracted from that file (provided by the project lead).';
INSERT INTO value_units VALUES
  ('src_simini_21730_data', 'value', NULL, 'open', 'simini_21730_data.value: unit to be established');

-- file: capri_data/sources/capmod/capmod_world_reference_2017.csv
CREATE TABLE src_capmod_world_reference_2017 (
    commodity VARCHAR NOT NULL,
    Fob DOUBLE NOT NULL,
    ImportP DOUBLE NOT NULL,
    ImportQ DOUBLE NOT NULL,
    PRIMARY KEY (commodity)
);
COMMENT ON TABLE src_capmod_world_reference_2017 IS 'Per CAPRI market commodity: Fob, ImportP and ImportQ (71 rows); no builder. Read by tools/check/validate_world_prices.py and report_world_price_divergence.py; the latter describes it as the (World, World) cell of capmod''s 2017 base result; how it was extracted is not documented.';
INSERT INTO value_units VALUES
  ('src_capmod_world_reference_2017', 'Fob', NULL, 'open', 'capmod_world_reference_2017.Fob: unit to be established'),
  ('src_capmod_world_reference_2017', 'ImportP', NULL, 'open', 'capmod_world_reference_2017.ImportP: unit to be established'),
  ('src_capmod_world_reference_2017', 'ImportQ', NULL, 'open', 'capmod_world_reference_2017.ImportQ: unit to be established');

-- file: capri_data/sources/capreg/capreg_activity_levels.csv
CREATE TABLE src_capreg_activity_levels (
    model_region VARCHAR NOT NULL,
    AGGT DOUBLE NOT NULL,
    ANNC DOUBLE NOT NULL,
    APPL DOUBLE NOT NULL,
    ARAC DOUBLE NOT NULL,
    ARTART DOUBLE NOT NULL,
    ARTCRP DOUBLE NOT NULL,
    ARTFOR DOUBLE NOT NULL,
    ARTGRS DOUBLE NOT NULL,
    ARTIF DOUBLE NOT NULL,
    ARTO DOUBLE NOT NULL,
    ARTRES DOUBLE NOT NULL,
    ARTWET DOUBLE NOT NULL,
    BARL DOUBLE NOT NULL,
    BEFM DOUBLE NOT NULL,
    BULF DOUBLE,
    BULH DOUBLE,
    BULL DOUBLE,
    CACR DOUBLE NOT NULL,
    CAFF DOUBLE NOT NULL,
    CAFR DOUBLE NOT NULL,
    CAMF DOUBLE,
    CAMR DOUBLE NOT NULL,
    CAT1 DOUBLE,
    CAT2 DOUBLE,
    CATA DOUBLE NOT NULL,
    CER2 DOUBLE NOT NULL,
    CERE DOUBLE NOT NULL,
    CITR DOUBLE,
    CORN DOUBLE,
    CROP DOUBLE NOT NULL,
    CRPART DOUBLE NOT NULL,
    CRPCRP DOUBLE NOT NULL,
    CRPFOR DOUBLE NOT NULL,
    CRPGRS DOUBLE NOT NULL,
    CRPRES DOUBLE NOT NULL,
    CRPWET DOUBLE NOT NULL,
    DCOH DOUBLE NOT NULL,
    DCOL DOUBLE NOT NULL,
    DCOW DOUBLE NOT NULL,
    DWHE DOUBLE,
    EAAB DOUBLE,
    EAAP DOUBLE,
    EXPD DOUBLE,
    FARA DOUBLE NOT NULL,
    FATS DOUBLE,
    FLEG DOUBLE,
    FLOW DOUBLE,
    FODD DOUBLE NOT NULL,
    FORART DOUBLE NOT NULL,
    FORCRP DOUBLE NOT NULL,
    FORE DOUBLE NOT NULL,
    FORFOR DOUBLE NOT NULL,
    FORGRS DOUBLE NOT NULL,
    FORRES DOUBLE NOT NULL,
    FORWET DOUBLE NOT NULL,
    FPEG DOUBLE,
    FRUI DOUBLE,
    FRUN DOUBLE NOT NULL,
    GRAS DOUBLE,
    GRSART DOUBLE NOT NULL,
    GRSCRP DOUBLE NOT NULL,
    GRSFOR DOUBLE NOT NULL,
    GRSGRS DOUBLE NOT NULL,
    GRSLND DOUBLE NOT NULL,
    GRSRES DOUBLE NOT NULL,
    GRSWET DOUBLE NOT NULL,
    HEIF DOUBLE,
    HEIH DOUBLE,
    HEIL DOUBLE,
    HEIR DOUBLE NOT NULL,
    HENS DOUBLE,
    INDU DOUBLE,
    INHA DOUBLE,
    INLW DOUBLE NOT NULL,
    MAIF DOUBLE,
    NURS DOUBLE,
    OANI DOUBLE,
    OAR1 DOUBLE NOT NULL,
    OARA DOUBLE NOT NULL,
    OATS DOUBLE,
    OCER DOUBLE NOT NULL,
    OCRO DOUBLE,
    OFAR DOUBLE NOT NULL,
    OFRU DOUBLE NOT NULL,
    OILS DOUBLE,
    OIND DOUBLE,
    OLIV DOUBLE,
    OOIL DOUBLE,
    OVEG DOUBLE NOT NULL,
    PARI DOUBLE,
    PERM DOUBLE NOT NULL,
    PIGF DOUBLE NOT NULL,
    PKPL DOUBLE NOT NULL,
    POTA DOUBLE,
    POUF DOUBLE,
    PROT DOUBLE,
    PULS DOUBLE NOT NULL,
    RAPE DOUBLE,
    RESART DOUBLE NOT NULL,
    RESCRP DOUBLE NOT NULL,
    RESFOR DOUBLE NOT NULL,
    RESGRS DOUBLE NOT NULL,
    RESLND DOUBLE NOT NULL,
    RESRES DOUBLE NOT NULL,
    RESWET DOUBLE NOT NULL,
    ROOF DOUBLE,
    RUMI DOUBLE NOT NULL,
    RYEM DOUBLE,
    SCOW DOUBLE NOT NULL,
    SETF DOUBLE NOT NULL,
    SHGF DOUBLE NOT NULL,
    SHGM DOUBLE NOT NULL,
    SOWS DOUBLE,
    SOYA DOUBLE,
    SUGB DOUBLE,
    SUNF DOUBLE,
    SWHE DOUBLE,
    TABO DOUBLE,
    TAGR DOUBLE,
    TEXT DOUBLE,
    TOBA DOUBLE,
    TOMA DOUBLE NOT NULL,
    TWIN DOUBLE,
    VEGE DOUBLE,
    VINY DOUBLE,
    VSET DOUBLE,
    WETART DOUBLE NOT NULL,
    WETCRP DOUBLE NOT NULL,
    WETFOR DOUBLE NOT NULL,
    WETGRS DOUBLE NOT NULL,
    WETLND DOUBLE NOT NULL,
    WETRES DOUBLE NOT NULL,
    WETWET DOUBLE NOT NULL,
    PRIMARY KEY (model_region)
);
COMMENT ON TABLE src_capreg_activity_levels IS 'CAPRI''s activity levels LEVL per regional unit (rows) and activity (columns), land categories excluded, from the CAPREG DATA2_<CC>.txt dumps, year column Y; MAIZ renamed CORN (tools/build/extract_remaining_nine.py).';
INSERT INTO value_units VALUES
  ('src_capreg_activity_levels', 'AGGT', NULL, 'open', 'capreg_activity_levels.AGGT: unit to be established'),
  ('src_capreg_activity_levels', 'ANNC', NULL, 'open', 'capreg_activity_levels.ANNC: unit to be established'),
  ('src_capreg_activity_levels', 'APPL', NULL, 'open', 'capreg_activity_levels.APPL: unit to be established'),
  ('src_capreg_activity_levels', 'ARAC', NULL, 'open', 'capreg_activity_levels.ARAC: unit to be established'),
  ('src_capreg_activity_levels', 'ARTART', NULL, 'open', 'capreg_activity_levels.ARTART: unit to be established'),
  ('src_capreg_activity_levels', 'ARTCRP', NULL, 'open', 'capreg_activity_levels.ARTCRP: unit to be established'),
  ('src_capreg_activity_levels', 'ARTFOR', NULL, 'open', 'capreg_activity_levels.ARTFOR: unit to be established'),
  ('src_capreg_activity_levels', 'ARTGRS', NULL, 'open', 'capreg_activity_levels.ARTGRS: unit to be established'),
  ('src_capreg_activity_levels', 'ARTIF', NULL, 'open', 'capreg_activity_levels.ARTIF: unit to be established'),
  ('src_capreg_activity_levels', 'ARTO', NULL, 'open', 'capreg_activity_levels.ARTO: unit to be established'),
  ('src_capreg_activity_levels', 'ARTRES', NULL, 'open', 'capreg_activity_levels.ARTRES: unit to be established'),
  ('src_capreg_activity_levels', 'ARTWET', NULL, 'open', 'capreg_activity_levels.ARTWET: unit to be established'),
  ('src_capreg_activity_levels', 'BARL', NULL, 'open', 'capreg_activity_levels.BARL: unit to be established'),
  ('src_capreg_activity_levels', 'BEFM', NULL, 'open', 'capreg_activity_levels.BEFM: unit to be established'),
  ('src_capreg_activity_levels', 'BULF', NULL, 'open', 'capreg_activity_levels.BULF: unit to be established'),
  ('src_capreg_activity_levels', 'BULH', NULL, 'open', 'capreg_activity_levels.BULH: unit to be established'),
  ('src_capreg_activity_levels', 'BULL', NULL, 'open', 'capreg_activity_levels.BULL: unit to be established'),
  ('src_capreg_activity_levels', 'CACR', NULL, 'open', 'capreg_activity_levels.CACR: unit to be established'),
  ('src_capreg_activity_levels', 'CAFF', NULL, 'open', 'capreg_activity_levels.CAFF: unit to be established'),
  ('src_capreg_activity_levels', 'CAFR', NULL, 'open', 'capreg_activity_levels.CAFR: unit to be established'),
  ('src_capreg_activity_levels', 'CAMF', NULL, 'open', 'capreg_activity_levels.CAMF: unit to be established'),
  ('src_capreg_activity_levels', 'CAMR', NULL, 'open', 'capreg_activity_levels.CAMR: unit to be established'),
  ('src_capreg_activity_levels', 'CAT1', NULL, 'open', 'capreg_activity_levels.CAT1: unit to be established'),
  ('src_capreg_activity_levels', 'CAT2', NULL, 'open', 'capreg_activity_levels.CAT2: unit to be established'),
  ('src_capreg_activity_levels', 'CATA', NULL, 'open', 'capreg_activity_levels.CATA: unit to be established'),
  ('src_capreg_activity_levels', 'CER2', NULL, 'open', 'capreg_activity_levels.CER2: unit to be established'),
  ('src_capreg_activity_levels', 'CERE', NULL, 'open', 'capreg_activity_levels.CERE: unit to be established'),
  ('src_capreg_activity_levels', 'CITR', NULL, 'open', 'capreg_activity_levels.CITR: unit to be established'),
  ('src_capreg_activity_levels', 'CORN', NULL, 'open', 'capreg_activity_levels.CORN: unit to be established'),
  ('src_capreg_activity_levels', 'CROP', NULL, 'open', 'capreg_activity_levels.CROP: unit to be established'),
  ('src_capreg_activity_levels', 'CRPART', NULL, 'open', 'capreg_activity_levels.CRPART: unit to be established'),
  ('src_capreg_activity_levels', 'CRPCRP', NULL, 'open', 'capreg_activity_levels.CRPCRP: unit to be established'),
  ('src_capreg_activity_levels', 'CRPFOR', NULL, 'open', 'capreg_activity_levels.CRPFOR: unit to be established'),
  ('src_capreg_activity_levels', 'CRPGRS', NULL, 'open', 'capreg_activity_levels.CRPGRS: unit to be established'),
  ('src_capreg_activity_levels', 'CRPRES', NULL, 'open', 'capreg_activity_levels.CRPRES: unit to be established'),
  ('src_capreg_activity_levels', 'CRPWET', NULL, 'open', 'capreg_activity_levels.CRPWET: unit to be established'),
  ('src_capreg_activity_levels', 'DCOH', NULL, 'open', 'capreg_activity_levels.DCOH: unit to be established'),
  ('src_capreg_activity_levels', 'DCOL', NULL, 'open', 'capreg_activity_levels.DCOL: unit to be established'),
  ('src_capreg_activity_levels', 'DCOW', NULL, 'open', 'capreg_activity_levels.DCOW: unit to be established'),
  ('src_capreg_activity_levels', 'DWHE', NULL, 'open', 'capreg_activity_levels.DWHE: unit to be established'),
  ('src_capreg_activity_levels', 'EAAB', NULL, 'open', 'capreg_activity_levels.EAAB: unit to be established'),
  ('src_capreg_activity_levels', 'EAAP', NULL, 'open', 'capreg_activity_levels.EAAP: unit to be established'),
  ('src_capreg_activity_levels', 'EXPD', NULL, 'open', 'capreg_activity_levels.EXPD: unit to be established'),
  ('src_capreg_activity_levels', 'FARA', NULL, 'open', 'capreg_activity_levels.FARA: unit to be established'),
  ('src_capreg_activity_levels', 'FATS', NULL, 'open', 'capreg_activity_levels.FATS: unit to be established'),
  ('src_capreg_activity_levels', 'FLEG', NULL, 'open', 'capreg_activity_levels.FLEG: unit to be established'),
  ('src_capreg_activity_levels', 'FLOW', NULL, 'open', 'capreg_activity_levels.FLOW: unit to be established'),
  ('src_capreg_activity_levels', 'FODD', NULL, 'open', 'capreg_activity_levels.FODD: unit to be established'),
  ('src_capreg_activity_levels', 'FORART', NULL, 'open', 'capreg_activity_levels.FORART: unit to be established'),
  ('src_capreg_activity_levels', 'FORCRP', NULL, 'open', 'capreg_activity_levels.FORCRP: unit to be established'),
  ('src_capreg_activity_levels', 'FORE', NULL, 'open', 'capreg_activity_levels.FORE: unit to be established'),
  ('src_capreg_activity_levels', 'FORFOR', NULL, 'open', 'capreg_activity_levels.FORFOR: unit to be established'),
  ('src_capreg_activity_levels', 'FORGRS', NULL, 'open', 'capreg_activity_levels.FORGRS: unit to be established'),
  ('src_capreg_activity_levels', 'FORRES', NULL, 'open', 'capreg_activity_levels.FORRES: unit to be established'),
  ('src_capreg_activity_levels', 'FORWET', NULL, 'open', 'capreg_activity_levels.FORWET: unit to be established'),
  ('src_capreg_activity_levels', 'FPEG', NULL, 'open', 'capreg_activity_levels.FPEG: unit to be established'),
  ('src_capreg_activity_levels', 'FRUI', NULL, 'open', 'capreg_activity_levels.FRUI: unit to be established'),
  ('src_capreg_activity_levels', 'FRUN', NULL, 'open', 'capreg_activity_levels.FRUN: unit to be established'),
  ('src_capreg_activity_levels', 'GRAS', NULL, 'open', 'capreg_activity_levels.GRAS: unit to be established'),
  ('src_capreg_activity_levels', 'GRSART', NULL, 'open', 'capreg_activity_levels.GRSART: unit to be established'),
  ('src_capreg_activity_levels', 'GRSCRP', NULL, 'open', 'capreg_activity_levels.GRSCRP: unit to be established'),
  ('src_capreg_activity_levels', 'GRSFOR', NULL, 'open', 'capreg_activity_levels.GRSFOR: unit to be established'),
  ('src_capreg_activity_levels', 'GRSGRS', NULL, 'open', 'capreg_activity_levels.GRSGRS: unit to be established'),
  ('src_capreg_activity_levels', 'GRSLND', NULL, 'open', 'capreg_activity_levels.GRSLND: unit to be established'),
  ('src_capreg_activity_levels', 'GRSRES', NULL, 'open', 'capreg_activity_levels.GRSRES: unit to be established'),
  ('src_capreg_activity_levels', 'GRSWET', NULL, 'open', 'capreg_activity_levels.GRSWET: unit to be established'),
  ('src_capreg_activity_levels', 'HEIF', NULL, 'open', 'capreg_activity_levels.HEIF: unit to be established'),
  ('src_capreg_activity_levels', 'HEIH', NULL, 'open', 'capreg_activity_levels.HEIH: unit to be established'),
  ('src_capreg_activity_levels', 'HEIL', NULL, 'open', 'capreg_activity_levels.HEIL: unit to be established'),
  ('src_capreg_activity_levels', 'HEIR', NULL, 'open', 'capreg_activity_levels.HEIR: unit to be established'),
  ('src_capreg_activity_levels', 'HENS', NULL, 'open', 'capreg_activity_levels.HENS: unit to be established'),
  ('src_capreg_activity_levels', 'INDU', NULL, 'open', 'capreg_activity_levels.INDU: unit to be established'),
  ('src_capreg_activity_levels', 'INHA', NULL, 'open', 'capreg_activity_levels.INHA: unit to be established'),
  ('src_capreg_activity_levels', 'INLW', NULL, 'open', 'capreg_activity_levels.INLW: unit to be established'),
  ('src_capreg_activity_levels', 'MAIF', NULL, 'open', 'capreg_activity_levels.MAIF: unit to be established'),
  ('src_capreg_activity_levels', 'NURS', NULL, 'open', 'capreg_activity_levels.NURS: unit to be established'),
  ('src_capreg_activity_levels', 'OANI', NULL, 'open', 'capreg_activity_levels.OANI: unit to be established'),
  ('src_capreg_activity_levels', 'OAR1', NULL, 'open', 'capreg_activity_levels.OAR1: unit to be established'),
  ('src_capreg_activity_levels', 'OARA', NULL, 'open', 'capreg_activity_levels.OARA: unit to be established'),
  ('src_capreg_activity_levels', 'OATS', NULL, 'open', 'capreg_activity_levels.OATS: unit to be established'),
  ('src_capreg_activity_levels', 'OCER', NULL, 'open', 'capreg_activity_levels.OCER: unit to be established'),
  ('src_capreg_activity_levels', 'OCRO', NULL, 'open', 'capreg_activity_levels.OCRO: unit to be established'),
  ('src_capreg_activity_levels', 'OFAR', NULL, 'open', 'capreg_activity_levels.OFAR: unit to be established'),
  ('src_capreg_activity_levels', 'OFRU', NULL, 'open', 'capreg_activity_levels.OFRU: unit to be established'),
  ('src_capreg_activity_levels', 'OILS', NULL, 'open', 'capreg_activity_levels.OILS: unit to be established'),
  ('src_capreg_activity_levels', 'OIND', NULL, 'open', 'capreg_activity_levels.OIND: unit to be established'),
  ('src_capreg_activity_levels', 'OLIV', NULL, 'open', 'capreg_activity_levels.OLIV: unit to be established'),
  ('src_capreg_activity_levels', 'OOIL', NULL, 'open', 'capreg_activity_levels.OOIL: unit to be established'),
  ('src_capreg_activity_levels', 'OVEG', NULL, 'open', 'capreg_activity_levels.OVEG: unit to be established'),
  ('src_capreg_activity_levels', 'PARI', NULL, 'open', 'capreg_activity_levels.PARI: unit to be established'),
  ('src_capreg_activity_levels', 'PERM', NULL, 'open', 'capreg_activity_levels.PERM: unit to be established'),
  ('src_capreg_activity_levels', 'PIGF', NULL, 'open', 'capreg_activity_levels.PIGF: unit to be established'),
  ('src_capreg_activity_levels', 'PKPL', NULL, 'open', 'capreg_activity_levels.PKPL: unit to be established'),
  ('src_capreg_activity_levels', 'POTA', NULL, 'open', 'capreg_activity_levels.POTA: unit to be established'),
  ('src_capreg_activity_levels', 'POUF', NULL, 'open', 'capreg_activity_levels.POUF: unit to be established'),
  ('src_capreg_activity_levels', 'PROT', NULL, 'open', 'capreg_activity_levels.PROT: unit to be established'),
  ('src_capreg_activity_levels', 'PULS', NULL, 'open', 'capreg_activity_levels.PULS: unit to be established'),
  ('src_capreg_activity_levels', 'RAPE', NULL, 'open', 'capreg_activity_levels.RAPE: unit to be established'),
  ('src_capreg_activity_levels', 'RESART', NULL, 'open', 'capreg_activity_levels.RESART: unit to be established'),
  ('src_capreg_activity_levels', 'RESCRP', NULL, 'open', 'capreg_activity_levels.RESCRP: unit to be established'),
  ('src_capreg_activity_levels', 'RESFOR', NULL, 'open', 'capreg_activity_levels.RESFOR: unit to be established'),
  ('src_capreg_activity_levels', 'RESGRS', NULL, 'open', 'capreg_activity_levels.RESGRS: unit to be established'),
  ('src_capreg_activity_levels', 'RESLND', NULL, 'open', 'capreg_activity_levels.RESLND: unit to be established'),
  ('src_capreg_activity_levels', 'RESRES', NULL, 'open', 'capreg_activity_levels.RESRES: unit to be established'),
  ('src_capreg_activity_levels', 'RESWET', NULL, 'open', 'capreg_activity_levels.RESWET: unit to be established'),
  ('src_capreg_activity_levels', 'ROOF', NULL, 'open', 'capreg_activity_levels.ROOF: unit to be established'),
  ('src_capreg_activity_levels', 'RUMI', NULL, 'open', 'capreg_activity_levels.RUMI: unit to be established'),
  ('src_capreg_activity_levels', 'RYEM', NULL, 'open', 'capreg_activity_levels.RYEM: unit to be established'),
  ('src_capreg_activity_levels', 'SCOW', NULL, 'open', 'capreg_activity_levels.SCOW: unit to be established'),
  ('src_capreg_activity_levels', 'SETF', NULL, 'open', 'capreg_activity_levels.SETF: unit to be established'),
  ('src_capreg_activity_levels', 'SHGF', NULL, 'open', 'capreg_activity_levels.SHGF: unit to be established'),
  ('src_capreg_activity_levels', 'SHGM', NULL, 'open', 'capreg_activity_levels.SHGM: unit to be established'),
  ('src_capreg_activity_levels', 'SOWS', NULL, 'open', 'capreg_activity_levels.SOWS: unit to be established'),
  ('src_capreg_activity_levels', 'SOYA', NULL, 'open', 'capreg_activity_levels.SOYA: unit to be established'),
  ('src_capreg_activity_levels', 'SUGB', NULL, 'open', 'capreg_activity_levels.SUGB: unit to be established'),
  ('src_capreg_activity_levels', 'SUNF', NULL, 'open', 'capreg_activity_levels.SUNF: unit to be established'),
  ('src_capreg_activity_levels', 'SWHE', NULL, 'open', 'capreg_activity_levels.SWHE: unit to be established'),
  ('src_capreg_activity_levels', 'TABO', NULL, 'open', 'capreg_activity_levels.TABO: unit to be established'),
  ('src_capreg_activity_levels', 'TAGR', NULL, 'open', 'capreg_activity_levels.TAGR: unit to be established'),
  ('src_capreg_activity_levels', 'TEXT', NULL, 'open', 'capreg_activity_levels.TEXT: unit to be established'),
  ('src_capreg_activity_levels', 'TOBA', NULL, 'open', 'capreg_activity_levels.TOBA: unit to be established'),
  ('src_capreg_activity_levels', 'TOMA', NULL, 'open', 'capreg_activity_levels.TOMA: unit to be established'),
  ('src_capreg_activity_levels', 'TWIN', NULL, 'open', 'capreg_activity_levels.TWIN: unit to be established'),
  ('src_capreg_activity_levels', 'VEGE', NULL, 'open', 'capreg_activity_levels.VEGE: unit to be established'),
  ('src_capreg_activity_levels', 'VINY', NULL, 'open', 'capreg_activity_levels.VINY: unit to be established'),
  ('src_capreg_activity_levels', 'VSET', NULL, 'open', 'capreg_activity_levels.VSET: unit to be established'),
  ('src_capreg_activity_levels', 'WETART', NULL, 'open', 'capreg_activity_levels.WETART: unit to be established'),
  ('src_capreg_activity_levels', 'WETCRP', NULL, 'open', 'capreg_activity_levels.WETCRP: unit to be established'),
  ('src_capreg_activity_levels', 'WETFOR', NULL, 'open', 'capreg_activity_levels.WETFOR: unit to be established'),
  ('src_capreg_activity_levels', 'WETGRS', NULL, 'open', 'capreg_activity_levels.WETGRS: unit to be established'),
  ('src_capreg_activity_levels', 'WETLND', NULL, 'open', 'capreg_activity_levels.WETLND: unit to be established'),
  ('src_capreg_activity_levels', 'WETRES', NULL, 'open', 'capreg_activity_levels.WETRES: unit to be established'),
  ('src_capreg_activity_levels', 'WETWET', NULL, 'open', 'capreg_activity_levels.WETWET: unit to be established');

-- file: capri_data/sources/capreg/capreg_cap_premium.csv
CREATE TABLE src_capreg_cap_premium (
    model_region VARCHAR NOT NULL,
    AGGT DOUBLE NOT NULL,
    ANNC DOUBLE,
    APPL DOUBLE,
    ARAC DOUBLE,
    BARL DOUBLE,
    BEFM DOUBLE,
    BULF DOUBLE,
    BULH DOUBLE,
    BULL DOUBLE,
    CACR DOUBLE,
    CAFF DOUBLE,
    CAFR DOUBLE,
    CAMF DOUBLE,
    CAMR DOUBLE,
    CATA DOUBLE,
    CERE DOUBLE,
    CITR DOUBLE,
    CORN DOUBLE,
    DCOH DOUBLE,
    DCOL DOUBLE,
    DCOW DOUBLE,
    DWHE DOUBLE,
    EAAG DOUBLE NOT NULL,
    FLOW DOUBLE,
    FODD DOUBLE,
    FRUN DOUBLE,
    GRAS DOUBLE,
    HEIF DOUBLE,
    HEIH DOUBLE,
    HEIL DOUBLE,
    HEIR DOUBLE,
    HENS DOUBLE,
    LABT DOUBLE,
    MAIF DOUBLE,
    MODU DOUBLE,
    NURS DOUBLE,
    OANI DOUBLE,
    OAR1 DOUBLE,
    OATS DOUBLE,
    OCER DOUBLE,
    OCRO DOUBLE,
    OFAR DOUBLE,
    OFRU DOUBLE,
    OILS DOUBLE,
    OIND DOUBLE,
    OLIV DOUBLE,
    OOIL DOUBLE,
    OVEG DOUBLE,
    PARI DOUBLE,
    PERM DOUBLE,
    PIGF DOUBLE,
    PKPL DOUBLE,
    POTA DOUBLE,
    POUF DOUBLE,
    PULS DOUBLE,
    RAPE DOUBLE,
    ROOF DOUBLE,
    RUMI DOUBLE,
    RYEM DOUBLE,
    SCOW DOUBLE,
    SETF DOUBLE,
    SHGF DOUBLE,
    SHGM DOUBLE,
    SOWS DOUBLE,
    SOYA DOUBLE,
    SUGB DOUBLE,
    SUNF DOUBLE,
    SWHE DOUBLE,
    TABO DOUBLE,
    TAGR DOUBLE,
    TEXT DOUBLE,
    TOBA DOUBLE,
    TOMA DOUBLE,
    TWIN DOUBLE,
    VSET DOUBLE,
    PRIMARY KEY (model_region)
);
COMMENT ON TABLE src_capreg_cap_premium IS 'CAPRI''s premium PRME per regional unit (rows) and activity (columns), per ha or per head, from the CAPREG DATA2_<CC>.txt dumps, year column Y; MAIZ renamed CORN (tools/build/extract_remaining_nine.py).';
INSERT INTO value_units VALUES
  ('src_capreg_cap_premium', 'AGGT', NULL, 'open', 'capreg_cap_premium.AGGT: unit to be established'),
  ('src_capreg_cap_premium', 'ANNC', NULL, 'open', 'capreg_cap_premium.ANNC: unit to be established'),
  ('src_capreg_cap_premium', 'APPL', NULL, 'open', 'capreg_cap_premium.APPL: unit to be established'),
  ('src_capreg_cap_premium', 'ARAC', NULL, 'open', 'capreg_cap_premium.ARAC: unit to be established'),
  ('src_capreg_cap_premium', 'BARL', NULL, 'open', 'capreg_cap_premium.BARL: unit to be established'),
  ('src_capreg_cap_premium', 'BEFM', NULL, 'open', 'capreg_cap_premium.BEFM: unit to be established'),
  ('src_capreg_cap_premium', 'BULF', NULL, 'open', 'capreg_cap_premium.BULF: unit to be established'),
  ('src_capreg_cap_premium', 'BULH', NULL, 'open', 'capreg_cap_premium.BULH: unit to be established'),
  ('src_capreg_cap_premium', 'BULL', NULL, 'open', 'capreg_cap_premium.BULL: unit to be established'),
  ('src_capreg_cap_premium', 'CACR', NULL, 'open', 'capreg_cap_premium.CACR: unit to be established'),
  ('src_capreg_cap_premium', 'CAFF', NULL, 'open', 'capreg_cap_premium.CAFF: unit to be established'),
  ('src_capreg_cap_premium', 'CAFR', NULL, 'open', 'capreg_cap_premium.CAFR: unit to be established'),
  ('src_capreg_cap_premium', 'CAMF', NULL, 'open', 'capreg_cap_premium.CAMF: unit to be established'),
  ('src_capreg_cap_premium', 'CAMR', NULL, 'open', 'capreg_cap_premium.CAMR: unit to be established'),
  ('src_capreg_cap_premium', 'CATA', NULL, 'open', 'capreg_cap_premium.CATA: unit to be established'),
  ('src_capreg_cap_premium', 'CERE', NULL, 'open', 'capreg_cap_premium.CERE: unit to be established'),
  ('src_capreg_cap_premium', 'CITR', NULL, 'open', 'capreg_cap_premium.CITR: unit to be established'),
  ('src_capreg_cap_premium', 'CORN', NULL, 'open', 'capreg_cap_premium.CORN: unit to be established'),
  ('src_capreg_cap_premium', 'DCOH', NULL, 'open', 'capreg_cap_premium.DCOH: unit to be established'),
  ('src_capreg_cap_premium', 'DCOL', NULL, 'open', 'capreg_cap_premium.DCOL: unit to be established'),
  ('src_capreg_cap_premium', 'DCOW', NULL, 'open', 'capreg_cap_premium.DCOW: unit to be established'),
  ('src_capreg_cap_premium', 'DWHE', NULL, 'open', 'capreg_cap_premium.DWHE: unit to be established'),
  ('src_capreg_cap_premium', 'EAAG', NULL, 'open', 'capreg_cap_premium.EAAG: unit to be established'),
  ('src_capreg_cap_premium', 'FLOW', NULL, 'open', 'capreg_cap_premium.FLOW: unit to be established'),
  ('src_capreg_cap_premium', 'FODD', NULL, 'open', 'capreg_cap_premium.FODD: unit to be established'),
  ('src_capreg_cap_premium', 'FRUN', NULL, 'open', 'capreg_cap_premium.FRUN: unit to be established'),
  ('src_capreg_cap_premium', 'GRAS', NULL, 'open', 'capreg_cap_premium.GRAS: unit to be established'),
  ('src_capreg_cap_premium', 'HEIF', NULL, 'open', 'capreg_cap_premium.HEIF: unit to be established'),
  ('src_capreg_cap_premium', 'HEIH', NULL, 'open', 'capreg_cap_premium.HEIH: unit to be established'),
  ('src_capreg_cap_premium', 'HEIL', NULL, 'open', 'capreg_cap_premium.HEIL: unit to be established'),
  ('src_capreg_cap_premium', 'HEIR', NULL, 'open', 'capreg_cap_premium.HEIR: unit to be established'),
  ('src_capreg_cap_premium', 'HENS', NULL, 'open', 'capreg_cap_premium.HENS: unit to be established'),
  ('src_capreg_cap_premium', 'LABT', NULL, 'open', 'capreg_cap_premium.LABT: unit to be established'),
  ('src_capreg_cap_premium', 'MAIF', NULL, 'open', 'capreg_cap_premium.MAIF: unit to be established'),
  ('src_capreg_cap_premium', 'MODU', NULL, 'open', 'capreg_cap_premium.MODU: unit to be established'),
  ('src_capreg_cap_premium', 'NURS', NULL, 'open', 'capreg_cap_premium.NURS: unit to be established'),
  ('src_capreg_cap_premium', 'OANI', NULL, 'open', 'capreg_cap_premium.OANI: unit to be established'),
  ('src_capreg_cap_premium', 'OAR1', NULL, 'open', 'capreg_cap_premium.OAR1: unit to be established'),
  ('src_capreg_cap_premium', 'OATS', NULL, 'open', 'capreg_cap_premium.OATS: unit to be established'),
  ('src_capreg_cap_premium', 'OCER', NULL, 'open', 'capreg_cap_premium.OCER: unit to be established'),
  ('src_capreg_cap_premium', 'OCRO', NULL, 'open', 'capreg_cap_premium.OCRO: unit to be established'),
  ('src_capreg_cap_premium', 'OFAR', NULL, 'open', 'capreg_cap_premium.OFAR: unit to be established'),
  ('src_capreg_cap_premium', 'OFRU', NULL, 'open', 'capreg_cap_premium.OFRU: unit to be established'),
  ('src_capreg_cap_premium', 'OILS', NULL, 'open', 'capreg_cap_premium.OILS: unit to be established'),
  ('src_capreg_cap_premium', 'OIND', NULL, 'open', 'capreg_cap_premium.OIND: unit to be established'),
  ('src_capreg_cap_premium', 'OLIV', NULL, 'open', 'capreg_cap_premium.OLIV: unit to be established'),
  ('src_capreg_cap_premium', 'OOIL', NULL, 'open', 'capreg_cap_premium.OOIL: unit to be established'),
  ('src_capreg_cap_premium', 'OVEG', NULL, 'open', 'capreg_cap_premium.OVEG: unit to be established'),
  ('src_capreg_cap_premium', 'PARI', NULL, 'open', 'capreg_cap_premium.PARI: unit to be established'),
  ('src_capreg_cap_premium', 'PERM', NULL, 'open', 'capreg_cap_premium.PERM: unit to be established'),
  ('src_capreg_cap_premium', 'PIGF', NULL, 'open', 'capreg_cap_premium.PIGF: unit to be established'),
  ('src_capreg_cap_premium', 'PKPL', NULL, 'open', 'capreg_cap_premium.PKPL: unit to be established'),
  ('src_capreg_cap_premium', 'POTA', NULL, 'open', 'capreg_cap_premium.POTA: unit to be established'),
  ('src_capreg_cap_premium', 'POUF', NULL, 'open', 'capreg_cap_premium.POUF: unit to be established'),
  ('src_capreg_cap_premium', 'PULS', NULL, 'open', 'capreg_cap_premium.PULS: unit to be established'),
  ('src_capreg_cap_premium', 'RAPE', NULL, 'open', 'capreg_cap_premium.RAPE: unit to be established'),
  ('src_capreg_cap_premium', 'ROOF', NULL, 'open', 'capreg_cap_premium.ROOF: unit to be established'),
  ('src_capreg_cap_premium', 'RUMI', NULL, 'open', 'capreg_cap_premium.RUMI: unit to be established'),
  ('src_capreg_cap_premium', 'RYEM', NULL, 'open', 'capreg_cap_premium.RYEM: unit to be established'),
  ('src_capreg_cap_premium', 'SCOW', NULL, 'open', 'capreg_cap_premium.SCOW: unit to be established'),
  ('src_capreg_cap_premium', 'SETF', NULL, 'open', 'capreg_cap_premium.SETF: unit to be established'),
  ('src_capreg_cap_premium', 'SHGF', NULL, 'open', 'capreg_cap_premium.SHGF: unit to be established'),
  ('src_capreg_cap_premium', 'SHGM', NULL, 'open', 'capreg_cap_premium.SHGM: unit to be established'),
  ('src_capreg_cap_premium', 'SOWS', NULL, 'open', 'capreg_cap_premium.SOWS: unit to be established'),
  ('src_capreg_cap_premium', 'SOYA', NULL, 'open', 'capreg_cap_premium.SOYA: unit to be established'),
  ('src_capreg_cap_premium', 'SUGB', NULL, 'open', 'capreg_cap_premium.SUGB: unit to be established'),
  ('src_capreg_cap_premium', 'SUNF', NULL, 'open', 'capreg_cap_premium.SUNF: unit to be established'),
  ('src_capreg_cap_premium', 'SWHE', NULL, 'open', 'capreg_cap_premium.SWHE: unit to be established'),
  ('src_capreg_cap_premium', 'TABO', NULL, 'open', 'capreg_cap_premium.TABO: unit to be established'),
  ('src_capreg_cap_premium', 'TAGR', NULL, 'open', 'capreg_cap_premium.TAGR: unit to be established'),
  ('src_capreg_cap_premium', 'TEXT', NULL, 'open', 'capreg_cap_premium.TEXT: unit to be established'),
  ('src_capreg_cap_premium', 'TOBA', NULL, 'open', 'capreg_cap_premium.TOBA: unit to be established'),
  ('src_capreg_cap_premium', 'TOMA', NULL, 'open', 'capreg_cap_premium.TOMA: unit to be established'),
  ('src_capreg_cap_premium', 'TWIN', NULL, 'open', 'capreg_cap_premium.TWIN: unit to be established'),
  ('src_capreg_cap_premium', 'VSET', NULL, 'open', 'capreg_cap_premium.VSET: unit to be established');

-- file: capri_data/sources/capreg/capreg_feed_use.csv
CREATE TABLE src_capreg_feed_use (
    model_region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (model_region, activity, "item")
);
COMMENT ON TABLE src_capreg_feed_use IS 'CAPRI''s feed use per regional unit, activity and feed item (FEED, FCER, FGRA, FMAI, FROO, FOFA, FPRO, FCOM, FMIL, FSGM, FSTR, FOTH), from the CAPREG DATA2_<CC>.txt dumps, year column Y (tools/build/extract_remaining_nine.py).';
INSERT INTO value_units VALUES
  ('src_capreg_feed_use', 'value', NULL, 'open', 'capreg_feed_use.value: unit to be established');

-- file: capri_data/sources/capreg/capreg_herds.csv
CREATE TABLE src_capreg_herds (
    model_region VARCHAR NOT NULL,
    BULF DOUBLE,
    BULH DOUBLE,
    BULL DOUBLE,
    CAFF DOUBLE NOT NULL,
    CAFR DOUBLE NOT NULL,
    CALV DOUBLE NOT NULL,
    CAMF DOUBLE,
    CAMR DOUBLE NOT NULL,
    CATA DOUBLE NOT NULL,
    DCOH DOUBLE NOT NULL,
    DCOL DOUBLE NOT NULL,
    DCOW DOUBLE NOT NULL,
    GOAT DOUBLE,
    HEIF DOUBLE,
    HEIH DOUBLE,
    HEIL DOUBLE,
    HEIR DOUBLE NOT NULL,
    HENS DOUBLE,
    PIGF DOUBLE NOT NULL,
    PIGS DOUBLE,
    POUF DOUBLE,
    POUL DOUBLE,
    SCOW DOUBLE NOT NULL,
    SHEP DOUBLE,
    SHGF DOUBLE NOT NULL,
    SHGM DOUBLE NOT NULL,
    SHGT DOUBLE NOT NULL,
    SOWS DOUBLE,
    PRIMARY KEY (model_region)
);
COMMENT ON TABLE src_capreg_herds IS 'CAPRI''s HERD per regional unit (rows) and animal activity (columns), from the CAPREG DATA2_<CC>.txt dumps, year column Y (tools/build/extract_remaining_nine.py).';
INSERT INTO value_units VALUES
  ('src_capreg_herds', 'BULF', NULL, 'open', 'capreg_herds.BULF: unit to be established'),
  ('src_capreg_herds', 'BULH', NULL, 'open', 'capreg_herds.BULH: unit to be established'),
  ('src_capreg_herds', 'BULL', NULL, 'open', 'capreg_herds.BULL: unit to be established'),
  ('src_capreg_herds', 'CAFF', NULL, 'open', 'capreg_herds.CAFF: unit to be established'),
  ('src_capreg_herds', 'CAFR', NULL, 'open', 'capreg_herds.CAFR: unit to be established'),
  ('src_capreg_herds', 'CALV', NULL, 'open', 'capreg_herds.CALV: unit to be established'),
  ('src_capreg_herds', 'CAMF', NULL, 'open', 'capreg_herds.CAMF: unit to be established'),
  ('src_capreg_herds', 'CAMR', NULL, 'open', 'capreg_herds.CAMR: unit to be established'),
  ('src_capreg_herds', 'CATA', NULL, 'open', 'capreg_herds.CATA: unit to be established'),
  ('src_capreg_herds', 'DCOH', NULL, 'open', 'capreg_herds.DCOH: unit to be established'),
  ('src_capreg_herds', 'DCOL', NULL, 'open', 'capreg_herds.DCOL: unit to be established'),
  ('src_capreg_herds', 'DCOW', NULL, 'open', 'capreg_herds.DCOW: unit to be established'),
  ('src_capreg_herds', 'GOAT', NULL, 'open', 'capreg_herds.GOAT: unit to be established'),
  ('src_capreg_herds', 'HEIF', NULL, 'open', 'capreg_herds.HEIF: unit to be established'),
  ('src_capreg_herds', 'HEIH', NULL, 'open', 'capreg_herds.HEIH: unit to be established'),
  ('src_capreg_herds', 'HEIL', NULL, 'open', 'capreg_herds.HEIL: unit to be established'),
  ('src_capreg_herds', 'HEIR', NULL, 'open', 'capreg_herds.HEIR: unit to be established'),
  ('src_capreg_herds', 'HENS', NULL, 'open', 'capreg_herds.HENS: unit to be established'),
  ('src_capreg_herds', 'PIGF', NULL, 'open', 'capreg_herds.PIGF: unit to be established'),
  ('src_capreg_herds', 'PIGS', NULL, 'open', 'capreg_herds.PIGS: unit to be established'),
  ('src_capreg_herds', 'POUF', NULL, 'open', 'capreg_herds.POUF: unit to be established'),
  ('src_capreg_herds', 'POUL', NULL, 'open', 'capreg_herds.POUL: unit to be established'),
  ('src_capreg_herds', 'SCOW', NULL, 'open', 'capreg_herds.SCOW: unit to be established'),
  ('src_capreg_herds', 'SHEP', NULL, 'open', 'capreg_herds.SHEP: unit to be established'),
  ('src_capreg_herds', 'SHGF', NULL, 'open', 'capreg_herds.SHGF: unit to be established'),
  ('src_capreg_herds', 'SHGM', NULL, 'open', 'capreg_herds.SHGM: unit to be established'),
  ('src_capreg_herds', 'SHGT', NULL, 'open', 'capreg_herds.SHGT: unit to be established'),
  ('src_capreg_herds', 'SOWS', NULL, 'open', 'capreg_herds.SOWS: unit to be established');

-- file: capri_data/sources/capreg/capreg_land.csv
CREATE TABLE src_capreg_land (
    model_region VARCHAR NOT NULL,
    ARAB DOUBLE NOT NULL,
    FALL DOUBLE NOT NULL,
    GRAE DOUBLE,
    GRAI DOUBLE,
    OLND DOUBLE NOT NULL,
    SETA DOUBLE,
    UAAR DOUBLE NOT NULL,
    PRIMARY KEY (model_region)
);
COMMENT ON TABLE src_capreg_land IS 'CAPRI''s LEVL of the land categories UAAR, ARAB, GRAE, GRAI, SETA, FALL, OLND per regional unit, from the CAPREG DATA2_<CC>.txt dumps, year column Y (tools/build/extract_remaining_nine.py).';
INSERT INTO value_units VALUES
  ('src_capreg_land', 'ARAB', NULL, 'open', 'capreg_land.ARAB: unit to be established'),
  ('src_capreg_land', 'FALL', NULL, 'open', 'capreg_land.FALL: unit to be established'),
  ('src_capreg_land', 'GRAE', NULL, 'open', 'capreg_land.GRAE: unit to be established'),
  ('src_capreg_land', 'GRAI', NULL, 'open', 'capreg_land.GRAI: unit to be established'),
  ('src_capreg_land', 'OLND', NULL, 'open', 'capreg_land.OLND: unit to be established'),
  ('src_capreg_land', 'SETA', NULL, 'open', 'capreg_land.SETA: unit to be established'),
  ('src_capreg_land', 'UAAR', NULL, 'open', 'capreg_land.UAAR: unit to be established');

-- file: capri_data/sources/capreg/capreg_national_prices.csv
CREATE TABLE src_capreg_national_prices (
    capri_country VARCHAR NOT NULL,
    AGGT DOUBLE NOT NULL,
    APPL DOUBLE NOT NULL,
    ARAB DOUBLE NOT NULL,
    BARL DOUBLE NOT NULL,
    BEFM DOUBLE NOT NULL,
    BULF DOUBLE NOT NULL,
    BULH DOUBLE NOT NULL,
    BULL DOUBLE NOT NULL,
    CACR DOUBLE NOT NULL,
    CAFF DOUBLE NOT NULL,
    CAFR DOUBLE NOT NULL,
    CAMF DOUBLE NOT NULL,
    CAMR DOUBLE NOT NULL,
    CATA DOUBLE NOT NULL,
    CERE DOUBLE NOT NULL,
    CITR DOUBLE,
    CORN DOUBLE,
    DCOH DOUBLE NOT NULL,
    DCOL DOUBLE NOT NULL,
    DCOW DOUBLE NOT NULL,
    DWHE DOUBLE,
    FLOW DOUBLE,
    FODD DOUBLE NOT NULL,
    GRAE DOUBLE,
    GRAI DOUBLE,
    GRAS DOUBLE,
    HEIF DOUBLE,
    HEIH DOUBLE,
    HEIL DOUBLE,
    HEIR DOUBLE NOT NULL,
    HENS DOUBLE NOT NULL,
    MAIF DOUBLE,
    MAIZ DOUBLE,
    NURS DOUBLE,
    OANI DOUBLE,
    OAR1 DOUBLE NOT NULL,
    OATS DOUBLE,
    OCER DOUBLE NOT NULL,
    OCRO DOUBLE NOT NULL,
    OFAR DOUBLE NOT NULL,
    OFOD DOUBLE NOT NULL,
    OFRU DOUBLE NOT NULL,
    OILS DOUBLE,
    OIND DOUBLE,
    OLIV DOUBLE,
    OOIL DOUBLE,
    OVEG DOUBLE NOT NULL,
    PARI DOUBLE,
    PERM DOUBLE NOT NULL,
    PIGF DOUBLE NOT NULL,
    PKPL DOUBLE NOT NULL,
    POTA DOUBLE NOT NULL,
    POUF DOUBLE NOT NULL,
    PULS DOUBLE NOT NULL,
    RAPE DOUBLE,
    ROOF DOUBLE,
    RUMI DOUBLE NOT NULL,
    RYEM DOUBLE,
    SCOW DOUBLE NOT NULL,
    SHGF DOUBLE NOT NULL,
    SHGM DOUBLE,
    SOWS DOUBLE NOT NULL,
    SOYA DOUBLE,
    SUGB DOUBLE,
    SUNF DOUBLE,
    SWHE DOUBLE,
    TABO DOUBLE,
    TAGR DOUBLE,
    TEXT DOUBLE,
    TOBA DOUBLE,
    TOMA DOUBLE NOT NULL,
    TWIN DOUBLE,
    UAAR DOUBLE NOT NULL,
    WINE DOUBLE,
    PRIMARY KEY (capri_country)
);
COMMENT ON TABLE src_capreg_national_prices IS 'CAPRI''s producer price MPRI of the national row <MS>000000 per country (two-letter code) and activity, from the 2017 dumps res_17<MS>.txt, column Y, under CAPRI''s code and also the model''s where it differs (CORN = MAIZ) (tools/build/build_capreg_national_prices.py).';
INSERT INTO value_units VALUES
  ('src_capreg_national_prices', 'AGGT', NULL, 'open', 'capreg_national_prices.AGGT: unit to be established'),
  ('src_capreg_national_prices', 'APPL', NULL, 'open', 'capreg_national_prices.APPL: unit to be established'),
  ('src_capreg_national_prices', 'ARAB', NULL, 'open', 'capreg_national_prices.ARAB: unit to be established'),
  ('src_capreg_national_prices', 'BARL', NULL, 'open', 'capreg_national_prices.BARL: unit to be established'),
  ('src_capreg_national_prices', 'BEFM', NULL, 'open', 'capreg_national_prices.BEFM: unit to be established'),
  ('src_capreg_national_prices', 'BULF', NULL, 'open', 'capreg_national_prices.BULF: unit to be established'),
  ('src_capreg_national_prices', 'BULH', NULL, 'open', 'capreg_national_prices.BULH: unit to be established'),
  ('src_capreg_national_prices', 'BULL', NULL, 'open', 'capreg_national_prices.BULL: unit to be established'),
  ('src_capreg_national_prices', 'CACR', NULL, 'open', 'capreg_national_prices.CACR: unit to be established'),
  ('src_capreg_national_prices', 'CAFF', NULL, 'open', 'capreg_national_prices.CAFF: unit to be established'),
  ('src_capreg_national_prices', 'CAFR', NULL, 'open', 'capreg_national_prices.CAFR: unit to be established'),
  ('src_capreg_national_prices', 'CAMF', NULL, 'open', 'capreg_national_prices.CAMF: unit to be established'),
  ('src_capreg_national_prices', 'CAMR', NULL, 'open', 'capreg_national_prices.CAMR: unit to be established'),
  ('src_capreg_national_prices', 'CATA', NULL, 'open', 'capreg_national_prices.CATA: unit to be established'),
  ('src_capreg_national_prices', 'CERE', NULL, 'open', 'capreg_national_prices.CERE: unit to be established'),
  ('src_capreg_national_prices', 'CITR', NULL, 'open', 'capreg_national_prices.CITR: unit to be established'),
  ('src_capreg_national_prices', 'CORN', NULL, 'open', 'capreg_national_prices.CORN: unit to be established'),
  ('src_capreg_national_prices', 'DCOH', NULL, 'open', 'capreg_national_prices.DCOH: unit to be established'),
  ('src_capreg_national_prices', 'DCOL', NULL, 'open', 'capreg_national_prices.DCOL: unit to be established'),
  ('src_capreg_national_prices', 'DCOW', NULL, 'open', 'capreg_national_prices.DCOW: unit to be established'),
  ('src_capreg_national_prices', 'DWHE', NULL, 'open', 'capreg_national_prices.DWHE: unit to be established'),
  ('src_capreg_national_prices', 'FLOW', NULL, 'open', 'capreg_national_prices.FLOW: unit to be established'),
  ('src_capreg_national_prices', 'FODD', NULL, 'open', 'capreg_national_prices.FODD: unit to be established'),
  ('src_capreg_national_prices', 'GRAE', NULL, 'open', 'capreg_national_prices.GRAE: unit to be established'),
  ('src_capreg_national_prices', 'GRAI', NULL, 'open', 'capreg_national_prices.GRAI: unit to be established'),
  ('src_capreg_national_prices', 'GRAS', NULL, 'open', 'capreg_national_prices.GRAS: unit to be established'),
  ('src_capreg_national_prices', 'HEIF', NULL, 'open', 'capreg_national_prices.HEIF: unit to be established'),
  ('src_capreg_national_prices', 'HEIH', NULL, 'open', 'capreg_national_prices.HEIH: unit to be established'),
  ('src_capreg_national_prices', 'HEIL', NULL, 'open', 'capreg_national_prices.HEIL: unit to be established'),
  ('src_capreg_national_prices', 'HEIR', NULL, 'open', 'capreg_national_prices.HEIR: unit to be established'),
  ('src_capreg_national_prices', 'HENS', NULL, 'open', 'capreg_national_prices.HENS: unit to be established'),
  ('src_capreg_national_prices', 'MAIF', NULL, 'open', 'capreg_national_prices.MAIF: unit to be established'),
  ('src_capreg_national_prices', 'MAIZ', NULL, 'open', 'capreg_national_prices.MAIZ: unit to be established'),
  ('src_capreg_national_prices', 'NURS', NULL, 'open', 'capreg_national_prices.NURS: unit to be established'),
  ('src_capreg_national_prices', 'OANI', NULL, 'open', 'capreg_national_prices.OANI: unit to be established'),
  ('src_capreg_national_prices', 'OAR1', NULL, 'open', 'capreg_national_prices.OAR1: unit to be established'),
  ('src_capreg_national_prices', 'OATS', NULL, 'open', 'capreg_national_prices.OATS: unit to be established'),
  ('src_capreg_national_prices', 'OCER', NULL, 'open', 'capreg_national_prices.OCER: unit to be established'),
  ('src_capreg_national_prices', 'OCRO', NULL, 'open', 'capreg_national_prices.OCRO: unit to be established'),
  ('src_capreg_national_prices', 'OFAR', NULL, 'open', 'capreg_national_prices.OFAR: unit to be established'),
  ('src_capreg_national_prices', 'OFOD', NULL, 'open', 'capreg_national_prices.OFOD: unit to be established'),
  ('src_capreg_national_prices', 'OFRU', NULL, 'open', 'capreg_national_prices.OFRU: unit to be established'),
  ('src_capreg_national_prices', 'OILS', NULL, 'open', 'capreg_national_prices.OILS: unit to be established'),
  ('src_capreg_national_prices', 'OIND', NULL, 'open', 'capreg_national_prices.OIND: unit to be established'),
  ('src_capreg_national_prices', 'OLIV', NULL, 'open', 'capreg_national_prices.OLIV: unit to be established'),
  ('src_capreg_national_prices', 'OOIL', NULL, 'open', 'capreg_national_prices.OOIL: unit to be established'),
  ('src_capreg_national_prices', 'OVEG', NULL, 'open', 'capreg_national_prices.OVEG: unit to be established'),
  ('src_capreg_national_prices', 'PARI', NULL, 'open', 'capreg_national_prices.PARI: unit to be established'),
  ('src_capreg_national_prices', 'PERM', NULL, 'open', 'capreg_national_prices.PERM: unit to be established'),
  ('src_capreg_national_prices', 'PIGF', NULL, 'open', 'capreg_national_prices.PIGF: unit to be established'),
  ('src_capreg_national_prices', 'PKPL', NULL, 'open', 'capreg_national_prices.PKPL: unit to be established'),
  ('src_capreg_national_prices', 'POTA', NULL, 'open', 'capreg_national_prices.POTA: unit to be established'),
  ('src_capreg_national_prices', 'POUF', NULL, 'open', 'capreg_national_prices.POUF: unit to be established'),
  ('src_capreg_national_prices', 'PULS', NULL, 'open', 'capreg_national_prices.PULS: unit to be established'),
  ('src_capreg_national_prices', 'RAPE', NULL, 'open', 'capreg_national_prices.RAPE: unit to be established'),
  ('src_capreg_national_prices', 'ROOF', NULL, 'open', 'capreg_national_prices.ROOF: unit to be established'),
  ('src_capreg_national_prices', 'RUMI', NULL, 'open', 'capreg_national_prices.RUMI: unit to be established'),
  ('src_capreg_national_prices', 'RYEM', NULL, 'open', 'capreg_national_prices.RYEM: unit to be established'),
  ('src_capreg_national_prices', 'SCOW', NULL, 'open', 'capreg_national_prices.SCOW: unit to be established'),
  ('src_capreg_national_prices', 'SHGF', NULL, 'open', 'capreg_national_prices.SHGF: unit to be established'),
  ('src_capreg_national_prices', 'SHGM', NULL, 'open', 'capreg_national_prices.SHGM: unit to be established'),
  ('src_capreg_national_prices', 'SOWS', NULL, 'open', 'capreg_national_prices.SOWS: unit to be established'),
  ('src_capreg_national_prices', 'SOYA', NULL, 'open', 'capreg_national_prices.SOYA: unit to be established'),
  ('src_capreg_national_prices', 'SUGB', NULL, 'open', 'capreg_national_prices.SUGB: unit to be established'),
  ('src_capreg_national_prices', 'SUNF', NULL, 'open', 'capreg_national_prices.SUNF: unit to be established'),
  ('src_capreg_national_prices', 'SWHE', NULL, 'open', 'capreg_national_prices.SWHE: unit to be established'),
  ('src_capreg_national_prices', 'TABO', NULL, 'open', 'capreg_national_prices.TABO: unit to be established'),
  ('src_capreg_national_prices', 'TAGR', NULL, 'open', 'capreg_national_prices.TAGR: unit to be established'),
  ('src_capreg_national_prices', 'TEXT', NULL, 'open', 'capreg_national_prices.TEXT: unit to be established'),
  ('src_capreg_national_prices', 'TOBA', NULL, 'open', 'capreg_national_prices.TOBA: unit to be established'),
  ('src_capreg_national_prices', 'TOMA', NULL, 'open', 'capreg_national_prices.TOMA: unit to be established'),
  ('src_capreg_national_prices', 'TWIN', NULL, 'open', 'capreg_national_prices.TWIN: unit to be established'),
  ('src_capreg_national_prices', 'UAAR', NULL, 'open', 'capreg_national_prices.UAAR: unit to be established'),
  ('src_capreg_national_prices', 'WINE', NULL, 'open', 'capreg_national_prices.WINE: unit to be established');

-- file: capri_data/sources/capreg/capreg_producer_prices.csv
CREATE TABLE src_capreg_producer_prices (
    model_region VARCHAR NOT NULL,
    AGGT DOUBLE NOT NULL,
    APPL DOUBLE NOT NULL,
    ARAB DOUBLE NOT NULL,
    BARL DOUBLE NOT NULL,
    BEFM DOUBLE NOT NULL,
    BULF DOUBLE,
    BULH DOUBLE,
    BULL DOUBLE,
    CACR DOUBLE NOT NULL,
    CAFF DOUBLE NOT NULL,
    CAFR DOUBLE NOT NULL,
    CAMF DOUBLE,
    CAMR DOUBLE NOT NULL,
    CATA DOUBLE NOT NULL,
    CERE DOUBLE NOT NULL,
    CITR DOUBLE,
    CORN DOUBLE,
    DCOH DOUBLE NOT NULL,
    DCOL DOUBLE NOT NULL,
    DCOW DOUBLE NOT NULL,
    DWHE DOUBLE,
    FLOW DOUBLE,
    FODD DOUBLE NOT NULL,
    GRAE DOUBLE,
    GRAI DOUBLE,
    GRAS DOUBLE,
    HEIF DOUBLE,
    HEIH DOUBLE,
    HEIL DOUBLE,
    HEIR DOUBLE NOT NULL,
    HENS DOUBLE,
    MAIF DOUBLE,
    NURS DOUBLE,
    OANI DOUBLE,
    OAR1 DOUBLE NOT NULL,
    OATS DOUBLE,
    OCER DOUBLE NOT NULL,
    OCRO DOUBLE NOT NULL,
    OFAR DOUBLE NOT NULL,
    OFRU DOUBLE NOT NULL,
    OILS DOUBLE,
    OIND DOUBLE,
    OLIV DOUBLE,
    OOIL DOUBLE,
    OVEG DOUBLE NOT NULL,
    PARI DOUBLE,
    PERM DOUBLE NOT NULL,
    PIGF DOUBLE NOT NULL,
    PKPL DOUBLE NOT NULL,
    POTA DOUBLE NOT NULL,
    POUF DOUBLE,
    PULS DOUBLE NOT NULL,
    RAPE DOUBLE,
    ROOF DOUBLE,
    RUMI DOUBLE NOT NULL,
    RYEM DOUBLE,
    SCOW DOUBLE NOT NULL,
    SHGF DOUBLE NOT NULL,
    SHGM DOUBLE,
    SOWS DOUBLE,
    SOYA DOUBLE,
    SUGB DOUBLE,
    SUNF DOUBLE,
    SWHE DOUBLE,
    TABO DOUBLE,
    TAGR DOUBLE,
    TEXT DOUBLE,
    TOBA DOUBLE,
    TOMA DOUBLE NOT NULL,
    TWIN DOUBLE,
    UAAR DOUBLE NOT NULL,
    WINE DOUBLE,
    OFOD DOUBLE NOT NULL,
    PRIMARY KEY (model_region)
);
COMMENT ON TABLE src_capreg_producer_prices IS 'Producer prices (EUR/t) per regional unit and activity: CAPRI''s MPRI extract (capreg_producer_prices_extract.csv) with the model-coded crop columns written for all regions and the animal columns DCOW, BULL, PIGF, OANI (MPRI) from CAPRI''s 2017 dumps (tools/build/build_crop_economics_2017.py).';
INSERT INTO value_units VALUES
  ('src_capreg_producer_prices', 'AGGT', NULL, 'open', 'capreg_producer_prices.AGGT: unit to be established'),
  ('src_capreg_producer_prices', 'APPL', NULL, 'open', 'capreg_producer_prices.APPL: unit to be established'),
  ('src_capreg_producer_prices', 'ARAB', NULL, 'open', 'capreg_producer_prices.ARAB: unit to be established'),
  ('src_capreg_producer_prices', 'BARL', NULL, 'open', 'capreg_producer_prices.BARL: unit to be established'),
  ('src_capreg_producer_prices', 'BEFM', NULL, 'open', 'capreg_producer_prices.BEFM: unit to be established'),
  ('src_capreg_producer_prices', 'BULF', NULL, 'open', 'capreg_producer_prices.BULF: unit to be established'),
  ('src_capreg_producer_prices', 'BULH', NULL, 'open', 'capreg_producer_prices.BULH: unit to be established'),
  ('src_capreg_producer_prices', 'BULL', NULL, 'open', 'capreg_producer_prices.BULL: unit to be established'),
  ('src_capreg_producer_prices', 'CACR', NULL, 'open', 'capreg_producer_prices.CACR: unit to be established'),
  ('src_capreg_producer_prices', 'CAFF', NULL, 'open', 'capreg_producer_prices.CAFF: unit to be established'),
  ('src_capreg_producer_prices', 'CAFR', NULL, 'open', 'capreg_producer_prices.CAFR: unit to be established'),
  ('src_capreg_producer_prices', 'CAMF', NULL, 'open', 'capreg_producer_prices.CAMF: unit to be established'),
  ('src_capreg_producer_prices', 'CAMR', NULL, 'open', 'capreg_producer_prices.CAMR: unit to be established'),
  ('src_capreg_producer_prices', 'CATA', NULL, 'open', 'capreg_producer_prices.CATA: unit to be established'),
  ('src_capreg_producer_prices', 'CERE', NULL, 'open', 'capreg_producer_prices.CERE: unit to be established'),
  ('src_capreg_producer_prices', 'CITR', NULL, 'open', 'capreg_producer_prices.CITR: unit to be established'),
  ('src_capreg_producer_prices', 'CORN', NULL, 'open', 'capreg_producer_prices.CORN: unit to be established'),
  ('src_capreg_producer_prices', 'DCOH', NULL, 'open', 'capreg_producer_prices.DCOH: unit to be established'),
  ('src_capreg_producer_prices', 'DCOL', NULL, 'open', 'capreg_producer_prices.DCOL: unit to be established'),
  ('src_capreg_producer_prices', 'DCOW', NULL, 'open', 'capreg_producer_prices.DCOW: unit to be established'),
  ('src_capreg_producer_prices', 'DWHE', NULL, 'open', 'capreg_producer_prices.DWHE: unit to be established'),
  ('src_capreg_producer_prices', 'FLOW', NULL, 'open', 'capreg_producer_prices.FLOW: unit to be established'),
  ('src_capreg_producer_prices', 'FODD', NULL, 'open', 'capreg_producer_prices.FODD: unit to be established'),
  ('src_capreg_producer_prices', 'GRAE', NULL, 'open', 'capreg_producer_prices.GRAE: unit to be established'),
  ('src_capreg_producer_prices', 'GRAI', NULL, 'open', 'capreg_producer_prices.GRAI: unit to be established'),
  ('src_capreg_producer_prices', 'GRAS', NULL, 'open', 'capreg_producer_prices.GRAS: unit to be established'),
  ('src_capreg_producer_prices', 'HEIF', NULL, 'open', 'capreg_producer_prices.HEIF: unit to be established'),
  ('src_capreg_producer_prices', 'HEIH', NULL, 'open', 'capreg_producer_prices.HEIH: unit to be established'),
  ('src_capreg_producer_prices', 'HEIL', NULL, 'open', 'capreg_producer_prices.HEIL: unit to be established'),
  ('src_capreg_producer_prices', 'HEIR', NULL, 'open', 'capreg_producer_prices.HEIR: unit to be established'),
  ('src_capreg_producer_prices', 'HENS', NULL, 'open', 'capreg_producer_prices.HENS: unit to be established'),
  ('src_capreg_producer_prices', 'MAIF', NULL, 'open', 'capreg_producer_prices.MAIF: unit to be established'),
  ('src_capreg_producer_prices', 'NURS', NULL, 'open', 'capreg_producer_prices.NURS: unit to be established'),
  ('src_capreg_producer_prices', 'OANI', NULL, 'open', 'capreg_producer_prices.OANI: unit to be established'),
  ('src_capreg_producer_prices', 'OAR1', NULL, 'open', 'capreg_producer_prices.OAR1: unit to be established'),
  ('src_capreg_producer_prices', 'OATS', NULL, 'open', 'capreg_producer_prices.OATS: unit to be established'),
  ('src_capreg_producer_prices', 'OCER', NULL, 'open', 'capreg_producer_prices.OCER: unit to be established'),
  ('src_capreg_producer_prices', 'OCRO', NULL, 'open', 'capreg_producer_prices.OCRO: unit to be established'),
  ('src_capreg_producer_prices', 'OFAR', NULL, 'open', 'capreg_producer_prices.OFAR: unit to be established'),
  ('src_capreg_producer_prices', 'OFRU', NULL, 'open', 'capreg_producer_prices.OFRU: unit to be established'),
  ('src_capreg_producer_prices', 'OILS', NULL, 'open', 'capreg_producer_prices.OILS: unit to be established'),
  ('src_capreg_producer_prices', 'OIND', NULL, 'open', 'capreg_producer_prices.OIND: unit to be established'),
  ('src_capreg_producer_prices', 'OLIV', NULL, 'open', 'capreg_producer_prices.OLIV: unit to be established'),
  ('src_capreg_producer_prices', 'OOIL', NULL, 'open', 'capreg_producer_prices.OOIL: unit to be established'),
  ('src_capreg_producer_prices', 'OVEG', NULL, 'open', 'capreg_producer_prices.OVEG: unit to be established'),
  ('src_capreg_producer_prices', 'PARI', NULL, 'open', 'capreg_producer_prices.PARI: unit to be established'),
  ('src_capreg_producer_prices', 'PERM', NULL, 'open', 'capreg_producer_prices.PERM: unit to be established'),
  ('src_capreg_producer_prices', 'PIGF', NULL, 'open', 'capreg_producer_prices.PIGF: unit to be established'),
  ('src_capreg_producer_prices', 'PKPL', NULL, 'open', 'capreg_producer_prices.PKPL: unit to be established'),
  ('src_capreg_producer_prices', 'POTA', NULL, 'open', 'capreg_producer_prices.POTA: unit to be established'),
  ('src_capreg_producer_prices', 'POUF', NULL, 'open', 'capreg_producer_prices.POUF: unit to be established'),
  ('src_capreg_producer_prices', 'PULS', NULL, 'open', 'capreg_producer_prices.PULS: unit to be established'),
  ('src_capreg_producer_prices', 'RAPE', NULL, 'open', 'capreg_producer_prices.RAPE: unit to be established'),
  ('src_capreg_producer_prices', 'ROOF', NULL, 'open', 'capreg_producer_prices.ROOF: unit to be established'),
  ('src_capreg_producer_prices', 'RUMI', NULL, 'open', 'capreg_producer_prices.RUMI: unit to be established'),
  ('src_capreg_producer_prices', 'RYEM', NULL, 'open', 'capreg_producer_prices.RYEM: unit to be established'),
  ('src_capreg_producer_prices', 'SCOW', NULL, 'open', 'capreg_producer_prices.SCOW: unit to be established'),
  ('src_capreg_producer_prices', 'SHGF', NULL, 'open', 'capreg_producer_prices.SHGF: unit to be established'),
  ('src_capreg_producer_prices', 'SHGM', NULL, 'open', 'capreg_producer_prices.SHGM: unit to be established'),
  ('src_capreg_producer_prices', 'SOWS', NULL, 'open', 'capreg_producer_prices.SOWS: unit to be established'),
  ('src_capreg_producer_prices', 'SOYA', NULL, 'open', 'capreg_producer_prices.SOYA: unit to be established'),
  ('src_capreg_producer_prices', 'SUGB', NULL, 'open', 'capreg_producer_prices.SUGB: unit to be established'),
  ('src_capreg_producer_prices', 'SUNF', NULL, 'open', 'capreg_producer_prices.SUNF: unit to be established'),
  ('src_capreg_producer_prices', 'SWHE', NULL, 'open', 'capreg_producer_prices.SWHE: unit to be established'),
  ('src_capreg_producer_prices', 'TABO', NULL, 'open', 'capreg_producer_prices.TABO: unit to be established'),
  ('src_capreg_producer_prices', 'TAGR', NULL, 'open', 'capreg_producer_prices.TAGR: unit to be established'),
  ('src_capreg_producer_prices', 'TEXT', NULL, 'open', 'capreg_producer_prices.TEXT: unit to be established'),
  ('src_capreg_producer_prices', 'TOBA', NULL, 'open', 'capreg_producer_prices.TOBA: unit to be established'),
  ('src_capreg_producer_prices', 'TOMA', NULL, 'open', 'capreg_producer_prices.TOMA: unit to be established'),
  ('src_capreg_producer_prices', 'TWIN', NULL, 'open', 'capreg_producer_prices.TWIN: unit to be established'),
  ('src_capreg_producer_prices', 'UAAR', NULL, 'open', 'capreg_producer_prices.UAAR: unit to be established'),
  ('src_capreg_producer_prices', 'WINE', NULL, 'open', 'capreg_producer_prices.WINE: unit to be established'),
  ('src_capreg_producer_prices', 'OFOD', NULL, 'open', 'capreg_producer_prices.OFOD: unit to be established');

-- file: capri_data/sources/capreg/capreg_producer_prices_extract.csv
CREATE TABLE src_capreg_producer_prices_extract (
    model_region VARCHAR NOT NULL,
    AGGT DOUBLE NOT NULL,
    APPL DOUBLE NOT NULL,
    ARAB DOUBLE NOT NULL,
    BARL DOUBLE NOT NULL,
    BEFM DOUBLE NOT NULL,
    BULF DOUBLE,
    BULH DOUBLE,
    BULL DOUBLE,
    CACR DOUBLE NOT NULL,
    CAFF DOUBLE NOT NULL,
    CAFR DOUBLE NOT NULL,
    CAMF DOUBLE,
    CAMR DOUBLE NOT NULL,
    CATA DOUBLE NOT NULL,
    CERE DOUBLE NOT NULL,
    CITR DOUBLE,
    CORN DOUBLE,
    DCOH DOUBLE NOT NULL,
    DCOL DOUBLE NOT NULL,
    DCOW DOUBLE NOT NULL,
    DWHE DOUBLE,
    FLOW DOUBLE,
    FODD DOUBLE NOT NULL,
    GRAE DOUBLE,
    GRAI DOUBLE,
    GRAS DOUBLE,
    HEIF DOUBLE,
    HEIH DOUBLE,
    HEIL DOUBLE,
    HEIR DOUBLE NOT NULL,
    HENS DOUBLE,
    MAIF DOUBLE,
    NURS DOUBLE,
    OANI DOUBLE,
    OAR1 DOUBLE NOT NULL,
    OATS DOUBLE,
    OCER DOUBLE NOT NULL,
    OCRO DOUBLE,
    OFAR DOUBLE NOT NULL,
    OFRU DOUBLE NOT NULL,
    OILS DOUBLE,
    OIND DOUBLE,
    OLIV DOUBLE,
    OOIL DOUBLE,
    OVEG DOUBLE NOT NULL,
    PARI DOUBLE,
    PERM DOUBLE NOT NULL,
    PIGF DOUBLE NOT NULL,
    PKPL DOUBLE NOT NULL,
    POTA DOUBLE,
    POUF DOUBLE,
    PULS DOUBLE NOT NULL,
    RAPE DOUBLE,
    ROOF DOUBLE,
    RUMI DOUBLE NOT NULL,
    RYEM DOUBLE,
    SCOW DOUBLE NOT NULL,
    SHGF DOUBLE NOT NULL,
    SHGM DOUBLE,
    SOWS DOUBLE,
    SOYA DOUBLE,
    SUGB DOUBLE,
    SUNF DOUBLE,
    SWHE DOUBLE,
    TABO DOUBLE,
    TAGR DOUBLE,
    TEXT DOUBLE,
    TOBA DOUBLE,
    TOMA DOUBLE NOT NULL,
    TWIN DOUBLE,
    UAAR DOUBLE NOT NULL,
    PRIMARY KEY (model_region)
);
COMMENT ON TABLE src_capreg_producer_prices_extract IS 'CAPRI''s regional producer price MPRI (EUR/t per the builder) per regional unit (rows) and activity (columns), from the CAPREG DATA2_<CC>.txt dumps; MAIZ renamed CORN (tools/build/extract_all_from_data2.py).';
INSERT INTO value_units VALUES
  ('src_capreg_producer_prices_extract', 'AGGT', NULL, 'open', 'capreg_producer_prices_extract.AGGT: unit to be established'),
  ('src_capreg_producer_prices_extract', 'APPL', NULL, 'open', 'capreg_producer_prices_extract.APPL: unit to be established'),
  ('src_capreg_producer_prices_extract', 'ARAB', NULL, 'open', 'capreg_producer_prices_extract.ARAB: unit to be established'),
  ('src_capreg_producer_prices_extract', 'BARL', NULL, 'open', 'capreg_producer_prices_extract.BARL: unit to be established'),
  ('src_capreg_producer_prices_extract', 'BEFM', NULL, 'open', 'capreg_producer_prices_extract.BEFM: unit to be established'),
  ('src_capreg_producer_prices_extract', 'BULF', NULL, 'open', 'capreg_producer_prices_extract.BULF: unit to be established'),
  ('src_capreg_producer_prices_extract', 'BULH', NULL, 'open', 'capreg_producer_prices_extract.BULH: unit to be established'),
  ('src_capreg_producer_prices_extract', 'BULL', NULL, 'open', 'capreg_producer_prices_extract.BULL: unit to be established'),
  ('src_capreg_producer_prices_extract', 'CACR', NULL, 'open', 'capreg_producer_prices_extract.CACR: unit to be established'),
  ('src_capreg_producer_prices_extract', 'CAFF', NULL, 'open', 'capreg_producer_prices_extract.CAFF: unit to be established'),
  ('src_capreg_producer_prices_extract', 'CAFR', NULL, 'open', 'capreg_producer_prices_extract.CAFR: unit to be established'),
  ('src_capreg_producer_prices_extract', 'CAMF', NULL, 'open', 'capreg_producer_prices_extract.CAMF: unit to be established'),
  ('src_capreg_producer_prices_extract', 'CAMR', NULL, 'open', 'capreg_producer_prices_extract.CAMR: unit to be established'),
  ('src_capreg_producer_prices_extract', 'CATA', NULL, 'open', 'capreg_producer_prices_extract.CATA: unit to be established'),
  ('src_capreg_producer_prices_extract', 'CERE', NULL, 'open', 'capreg_producer_prices_extract.CERE: unit to be established'),
  ('src_capreg_producer_prices_extract', 'CITR', NULL, 'open', 'capreg_producer_prices_extract.CITR: unit to be established'),
  ('src_capreg_producer_prices_extract', 'CORN', NULL, 'open', 'capreg_producer_prices_extract.CORN: unit to be established'),
  ('src_capreg_producer_prices_extract', 'DCOH', NULL, 'open', 'capreg_producer_prices_extract.DCOH: unit to be established'),
  ('src_capreg_producer_prices_extract', 'DCOL', NULL, 'open', 'capreg_producer_prices_extract.DCOL: unit to be established'),
  ('src_capreg_producer_prices_extract', 'DCOW', NULL, 'open', 'capreg_producer_prices_extract.DCOW: unit to be established'),
  ('src_capreg_producer_prices_extract', 'DWHE', NULL, 'open', 'capreg_producer_prices_extract.DWHE: unit to be established'),
  ('src_capreg_producer_prices_extract', 'FLOW', NULL, 'open', 'capreg_producer_prices_extract.FLOW: unit to be established'),
  ('src_capreg_producer_prices_extract', 'FODD', NULL, 'open', 'capreg_producer_prices_extract.FODD: unit to be established'),
  ('src_capreg_producer_prices_extract', 'GRAE', NULL, 'open', 'capreg_producer_prices_extract.GRAE: unit to be established'),
  ('src_capreg_producer_prices_extract', 'GRAI', NULL, 'open', 'capreg_producer_prices_extract.GRAI: unit to be established'),
  ('src_capreg_producer_prices_extract', 'GRAS', NULL, 'open', 'capreg_producer_prices_extract.GRAS: unit to be established'),
  ('src_capreg_producer_prices_extract', 'HEIF', NULL, 'open', 'capreg_producer_prices_extract.HEIF: unit to be established'),
  ('src_capreg_producer_prices_extract', 'HEIH', NULL, 'open', 'capreg_producer_prices_extract.HEIH: unit to be established'),
  ('src_capreg_producer_prices_extract', 'HEIL', NULL, 'open', 'capreg_producer_prices_extract.HEIL: unit to be established'),
  ('src_capreg_producer_prices_extract', 'HEIR', NULL, 'open', 'capreg_producer_prices_extract.HEIR: unit to be established'),
  ('src_capreg_producer_prices_extract', 'HENS', NULL, 'open', 'capreg_producer_prices_extract.HENS: unit to be established'),
  ('src_capreg_producer_prices_extract', 'MAIF', NULL, 'open', 'capreg_producer_prices_extract.MAIF: unit to be established'),
  ('src_capreg_producer_prices_extract', 'NURS', NULL, 'open', 'capreg_producer_prices_extract.NURS: unit to be established'),
  ('src_capreg_producer_prices_extract', 'OANI', NULL, 'open', 'capreg_producer_prices_extract.OANI: unit to be established'),
  ('src_capreg_producer_prices_extract', 'OAR1', NULL, 'open', 'capreg_producer_prices_extract.OAR1: unit to be established'),
  ('src_capreg_producer_prices_extract', 'OATS', NULL, 'open', 'capreg_producer_prices_extract.OATS: unit to be established'),
  ('src_capreg_producer_prices_extract', 'OCER', NULL, 'open', 'capreg_producer_prices_extract.OCER: unit to be established'),
  ('src_capreg_producer_prices_extract', 'OCRO', NULL, 'open', 'capreg_producer_prices_extract.OCRO: unit to be established'),
  ('src_capreg_producer_prices_extract', 'OFAR', NULL, 'open', 'capreg_producer_prices_extract.OFAR: unit to be established'),
  ('src_capreg_producer_prices_extract', 'OFRU', NULL, 'open', 'capreg_producer_prices_extract.OFRU: unit to be established'),
  ('src_capreg_producer_prices_extract', 'OILS', NULL, 'open', 'capreg_producer_prices_extract.OILS: unit to be established'),
  ('src_capreg_producer_prices_extract', 'OIND', NULL, 'open', 'capreg_producer_prices_extract.OIND: unit to be established'),
  ('src_capreg_producer_prices_extract', 'OLIV', NULL, 'open', 'capreg_producer_prices_extract.OLIV: unit to be established'),
  ('src_capreg_producer_prices_extract', 'OOIL', NULL, 'open', 'capreg_producer_prices_extract.OOIL: unit to be established'),
  ('src_capreg_producer_prices_extract', 'OVEG', NULL, 'open', 'capreg_producer_prices_extract.OVEG: unit to be established'),
  ('src_capreg_producer_prices_extract', 'PARI', NULL, 'open', 'capreg_producer_prices_extract.PARI: unit to be established'),
  ('src_capreg_producer_prices_extract', 'PERM', NULL, 'open', 'capreg_producer_prices_extract.PERM: unit to be established'),
  ('src_capreg_producer_prices_extract', 'PIGF', NULL, 'open', 'capreg_producer_prices_extract.PIGF: unit to be established'),
  ('src_capreg_producer_prices_extract', 'PKPL', NULL, 'open', 'capreg_producer_prices_extract.PKPL: unit to be established'),
  ('src_capreg_producer_prices_extract', 'POTA', NULL, 'open', 'capreg_producer_prices_extract.POTA: unit to be established'),
  ('src_capreg_producer_prices_extract', 'POUF', NULL, 'open', 'capreg_producer_prices_extract.POUF: unit to be established'),
  ('src_capreg_producer_prices_extract', 'PULS', NULL, 'open', 'capreg_producer_prices_extract.PULS: unit to be established'),
  ('src_capreg_producer_prices_extract', 'RAPE', NULL, 'open', 'capreg_producer_prices_extract.RAPE: unit to be established'),
  ('src_capreg_producer_prices_extract', 'ROOF', NULL, 'open', 'capreg_producer_prices_extract.ROOF: unit to be established'),
  ('src_capreg_producer_prices_extract', 'RUMI', NULL, 'open', 'capreg_producer_prices_extract.RUMI: unit to be established'),
  ('src_capreg_producer_prices_extract', 'RYEM', NULL, 'open', 'capreg_producer_prices_extract.RYEM: unit to be established'),
  ('src_capreg_producer_prices_extract', 'SCOW', NULL, 'open', 'capreg_producer_prices_extract.SCOW: unit to be established'),
  ('src_capreg_producer_prices_extract', 'SHGF', NULL, 'open', 'capreg_producer_prices_extract.SHGF: unit to be established'),
  ('src_capreg_producer_prices_extract', 'SHGM', NULL, 'open', 'capreg_producer_prices_extract.SHGM: unit to be established'),
  ('src_capreg_producer_prices_extract', 'SOWS', NULL, 'open', 'capreg_producer_prices_extract.SOWS: unit to be established'),
  ('src_capreg_producer_prices_extract', 'SOYA', NULL, 'open', 'capreg_producer_prices_extract.SOYA: unit to be established'),
  ('src_capreg_producer_prices_extract', 'SUGB', NULL, 'open', 'capreg_producer_prices_extract.SUGB: unit to be established'),
  ('src_capreg_producer_prices_extract', 'SUNF', NULL, 'open', 'capreg_producer_prices_extract.SUNF: unit to be established'),
  ('src_capreg_producer_prices_extract', 'SWHE', NULL, 'open', 'capreg_producer_prices_extract.SWHE: unit to be established'),
  ('src_capreg_producer_prices_extract', 'TABO', NULL, 'open', 'capreg_producer_prices_extract.TABO: unit to be established'),
  ('src_capreg_producer_prices_extract', 'TAGR', NULL, 'open', 'capreg_producer_prices_extract.TAGR: unit to be established'),
  ('src_capreg_producer_prices_extract', 'TEXT', NULL, 'open', 'capreg_producer_prices_extract.TEXT: unit to be established'),
  ('src_capreg_producer_prices_extract', 'TOBA', NULL, 'open', 'capreg_producer_prices_extract.TOBA: unit to be established'),
  ('src_capreg_producer_prices_extract', 'TOMA', NULL, 'open', 'capreg_producer_prices_extract.TOMA: unit to be established'),
  ('src_capreg_producer_prices_extract', 'TWIN', NULL, 'open', 'capreg_producer_prices_extract.TWIN: unit to be established'),
  ('src_capreg_producer_prices_extract', 'UAAR', NULL, 'open', 'capreg_producer_prices_extract.UAAR: unit to be established');

-- file: capri_data/sources/capreg/pmp_quad_landtypes_2017.csv
CREATE TABLE src_pmp_quad_landtypes_2017 (
    region VARCHAR NOT NULL,
    landtype1 VARCHAR NOT NULL,
    landtype2 VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, landtype1, landtype2)
);
COMMENT ON TABLE src_pmp_quad_landtypes_2017 IS 'CAPRI''s 2017 quadratic land-supply terms p_pmpQuadLandTypes(region, landtype1, landtype2), read by tools/build/build_pmp_recipe.py for its 2017 land-nest adjustment; no builder, the file it was taken from is not documented.';
INSERT INTO value_units VALUES
  ('src_pmp_quad_landtypes_2017', 'value', NULL, 'open', 'pmp_quad_landtypes_2017.value: unit to be established');

-- file: capri_data/sources/capreg/pmp_quad_pact.csv
CREATE TABLE src_pmp_quad_pact (
    model_region VARCHAR NOT NULL,
    group1 VARCHAR NOT NULL,
    group2 VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (model_region, group1, group2)
);
COMMENT ON TABLE src_pmp_quad_pact IS 'CAPRI''s 2017 crop-group PMP terms p_pmpQuadPact(region, group1, group2) per regional unit, from the quadPact_<CC>.txt dumps of pmppar_17*.gdx (tools/build/ingest_pmp_terms.py).';
INSERT INTO value_units VALUES
  ('src_pmp_quad_pact', 'value', NULL, 'open', 'pmp_quad_pact.value: unit to be established');

-- file: capri_data/sources/capreg/pmp_quad_techn.csv
CREATE TABLE src_pmp_quad_techn (
    model_region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (model_region, activity)
);
COMMENT ON TABLE src_pmp_quad_techn IS 'CAPRI''s 2017 own-activity PMP diagonal p_pmpQuadTechn(region, activity, T1, T1) (T.T for animals) per regional unit and activity, from the quadTechn_<CC>.txt dumps of pmppar_17*.gdx; MAIZ renamed CORN (tools/build/ingest_pmp_terms.py).';
INSERT INTO value_units VALUES
  ('src_pmp_quad_techn', 'value', NULL, 'open', 'pmp_quad_techn.value: unit to be established');

-- file: capri_data/sources/capri_baseline/capri_market_prices_1730.csv
CREATE TABLE src_capri_market_prices_1730 (
    region VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    product VARCHAR NOT NULL,
    point VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, "item", product, point)
);
COMMENT ON TABLE src_capri_market_prices_1730 IS 'CAPRI''s market prices PPRI and CPRI per region and product at the base point BAS (2017) and the 2030 calibration point CAL; no builder: per capri_data/DATA_DICTIONARY.md a gdxdump of results/baseline/data_market_1730defaulta.';
INSERT INTO value_units VALUES
  ('src_capri_market_prices_1730', 'value', NULL, 'open', 'capri_market_prices_1730.value: unit to be established');

-- file: capri_data/sources/capri_baseline/capri_uvag_store_1730.csv
CREATE TABLE src_capri_uvag_store_1730 (
    region VARCHAR NOT NULL,
    product VARCHAR NOT NULL,
    uvag_2030 DOUBLE NOT NULL,
    PRIMARY KEY (region, product)
);
COMMENT ON TABLE src_capri_uvag_store_1730 IS 'CAPRI''s calibrated 2030 unit values p_uvagStore per region and product (uvag_2030); no builder: per capri_data/DATA_DICTIONARY.md a gdxdump of results/baseline/data_uvag1730defaulta.';
INSERT INTO value_units VALUES
  ('src_capri_uvag_store_1730', 'uvag_2030', NULL, 'open', 'capri_uvag_store_1730.uvag_2030: unit to be established');

-- file: capri_data/sources/capri_dat/ghgtech/AD_basedata_p_B0.csv
CREATE TABLE src_ad_basedata_p_b0 (
    dim1 VARCHAR NOT NULL,
    dim2 VARCHAR NOT NULL,
    "level" DOUBLE NOT NULL,
    marginal DOUBLE NOT NULL,
    PRIMARY KEY (dim1, dim2)
);
COMMENT ON TABLE src_ad_basedata_p_b0 IS 'CAPRI''s p_B0 (m3 CH4 per kg VS, per docs/AD_SPEC.md) per region (EU000000) and animal group, level and marginal, from dat/scen/ghgtech/AD_basedata.gdx (loaded at envind/ad_data_and_cali.gms l. 239); no builder; read by tools/build/build_ad_option.py.';
INSERT INTO value_units VALUES
  ('src_ad_basedata_p_b0', 'level', NULL, 'open', 'AD_basedata_p_B0.level: unit to be established'),
  ('src_ad_basedata_p_b0', 'marginal', NULL, 'open', 'AD_basedata_p_B0.marginal: unit to be established');

-- file: capri_data/sources/capri_dat/ghgtech/AD_basedata_p_Heads.csv
CREATE TABLE src_ad_basedata_p_heads (
    dim1 VARCHAR NOT NULL,
    dim2 VARCHAR NOT NULL,
    dim3 VARCHAR NOT NULL,
    "level" DOUBLE NOT NULL,
    marginal DOUBLE NOT NULL,
    PRIMARY KEY (dim1, dim2, dim3)
);
COMMENT ON TABLE src_ad_basedata_p_heads IS 'CAPRI''s p_Heads, heads per region, AD animal activity and farm-size class (dim1-dim3), level and marginal, from dat/scen/ghgtech/AD_basedata.gdx (loaded at envind/ad_data_and_cali.gms l. 239); no builder; read by tools/build/build_ad_option.py.';
INSERT INTO value_units VALUES
  ('src_ad_basedata_p_heads', 'level', NULL, 'open', 'AD_basedata_p_Heads.level: unit to be established'),
  ('src_ad_basedata_p_heads', 'marginal', NULL, 'open', 'AD_basedata_p_Heads.marginal: unit to be established');

-- file: capri_data/sources/capri_dat/ghgtech/AD_basedata_p_HousShar.csv
CREATE TABLE src_ad_basedata_p_housshar (
    dim1 VARCHAR NOT NULL,
    dim2 VARCHAR NOT NULL,
    "level" DOUBLE NOT NULL,
    marginal DOUBLE NOT NULL,
    PRIMARY KEY (dim1, dim2)
);
COMMENT ON TABLE src_ad_basedata_p_housshar IS 'CAPRI''s p_HousShar, housing share per country and animal group (DAIRY, NDAIRY, ...), level and marginal, from dat/scen/ghgtech/AD_basedata.gdx (loaded at envind/ad_data_and_cali.gms l. 239); no builder; read by tools/build/build_ad_option.py.';
INSERT INTO value_units VALUES
  ('src_ad_basedata_p_housshar', 'level', NULL, 'open', 'AD_basedata_p_HousShar.level: unit to be established'),
  ('src_ad_basedata_p_housshar', 'marginal', NULL, 'open', 'AD_basedata_p_HousShar.marginal: unit to be established');

-- file: capri_data/sources/capri_dat/ghgtech/AD_basedata_p_MitiShar0.csv
CREATE TABLE src_ad_basedata_p_mitishar0 (
    dim1 VARCHAR NOT NULL,
    dim2 VARCHAR NOT NULL,
    "level" DOUBLE NOT NULL,
    marginal DOUBLE NOT NULL,
    PRIMARY KEY (dim1, dim2)
);
COMMENT ON TABLE src_ad_basedata_p_mitishar0 IS 'CAPRI''s p_MitiShar0, initial anaerobic digestion share per country and animal group, level and marginal, from dat/scen/ghgtech/AD_basedata.gdx (loaded at envind/ad_data_and_cali.gms l. 239); no builder; read by tools/build/build_ad_option.py.';
INSERT INTO value_units VALUES
  ('src_ad_basedata_p_mitishar0', 'level', NULL, 'open', 'AD_basedata_p_MitiShar0.level: unit to be established'),
  ('src_ad_basedata_p_mitishar0', 'marginal', NULL, 'open', 'AD_basedata_p_MitiShar0.marginal: unit to be established');

-- file: capri_data/sources/capri_dat/ghgtech/AD_basedata_p_SharLiq.csv
CREATE TABLE src_ad_basedata_p_sharliq (
    dim1 VARCHAR NOT NULL,
    dim2 VARCHAR NOT NULL,
    "level" DOUBLE NOT NULL,
    marginal DOUBLE NOT NULL,
    PRIMARY KEY (dim1, dim2)
);
COMMENT ON TABLE src_ad_basedata_p_sharliq IS 'CAPRI''s p_SharLiq, liquid manure share per country and animal group, level and marginal, from dat/scen/ghgtech/AD_basedata.gdx (loaded at envind/ad_data_and_cali.gms l. 239); no builder; read by tools/build/build_ad_option.py.';
INSERT INTO value_units VALUES
  ('src_ad_basedata_p_sharliq', 'level', NULL, 'open', 'AD_basedata_p_SharLiq.level: unit to be established'),
  ('src_ad_basedata_p_sharliq', 'marginal', NULL, 'open', 'AD_basedata_p_SharLiq.marginal: unit to be established');

-- file: capri_data/sources/capri_dat/ghgtech/AD_basedata_p_VSER.csv
CREATE TABLE src_ad_basedata_p_vser (
    dim1 VARCHAR NOT NULL,
    dim2 VARCHAR NOT NULL,
    "level" DOUBLE NOT NULL,
    marginal DOUBLE NOT NULL,
    PRIMARY KEY (dim1, dim2)
);
COMMENT ON TABLE src_ad_basedata_p_vser IS 'CAPRI''s p_VSER (kg VS per head and day, per docs/AD_SPEC.md) per country and AD animal activity, level and marginal, from dat/scen/ghgtech/AD_basedata.gdx (loaded at envind/ad_data_and_cali.gms l. 239); no builder; read by tools/build/build_ad_option.py.';
INSERT INTO value_units VALUES
  ('src_ad_basedata_p_vser', 'level', NULL, 'open', 'AD_basedata_p_VSER.level: unit to be established'),
  ('src_ad_basedata_p_vser', 'marginal', NULL, 'open', 'AD_basedata_p_VSER.marginal: unit to be established');

-- file: capri_data/sources/capri_dat/ghgtech/AD_basedata_p_sf.csv
CREATE TABLE src_ad_basedata_p_sf (
    dim1 VARCHAR NOT NULL,
    dim2 VARCHAR NOT NULL,
    "level" DOUBLE NOT NULL,
    marginal DOUBLE NOT NULL,
    PRIMARY KEY (dim1, dim2)
);
COMMENT ON TABLE src_ad_basedata_p_sf IS 'CAPRI''s p_sf, farm size (LSU per farm, per docs/AD_SPEC.md) per region and farm-size class, level and marginal, from dat/scen/ghgtech/AD_basedata.gdx (loaded at envind/ad_data_and_cali.gms l. 239); no builder; read by tools/build/build_ad_option.py.';
INSERT INTO value_units VALUES
  ('src_ad_basedata_p_sf', 'level', NULL, 'open', 'AD_basedata_p_sf.level: unit to be established'),
  ('src_ad_basedata_p_sf', 'marginal', NULL, 'open', 'AD_basedata_p_sf.marginal: unit to be established');

-- file: capri_data/sources/capri_dat/ghgtech/LitRevFertTech_p_litRevFertTechs.csv
CREATE TABLE src_capri_dat_litrevferttech_p_litrevferttechs (
    dim1 VARCHAR NOT NULL,
    dim2 VARCHAR NOT NULL,
    dim3 VARCHAR NOT NULL,
    dim4 VARCHAR NOT NULL,
    dim5 VARCHAR NOT NULL,
    "level" DOUBLE NOT NULL,
    marginal DOUBLE NOT NULL,
    PRIMARY KEY (dim1, dim2, dim3, dim4, dim5)
);
COMMENT ON TABLE src_capri_dat_litrevferttech_p_litrevferttechs IS 'CAPRI''s p_litRevFertTechs (dim1-dim5: region, technology, activity, manure system, emission item; level, marginal; 88530 rows), relative emission changes of fertiliser technologies; no builder, read by no code: a fuller dump of the table in sources/ghgtech (KNOWN_ISSUES K103).';
INSERT INTO value_units VALUES
  ('src_capri_dat_litrevferttech_p_litrevferttechs', 'level', NULL, 'open', 'LitRevFertTech_p_litRevFertTechs.level: unit to be established'),
  ('src_capri_dat_litrevferttech_p_litrevferttechs', 'marginal', NULL, 'open', 'LitRevFertTech_p_litRevFertTechs.marginal: unit to be established');

-- file: capri_data/sources/capri_dat/ghgtech/gains_ad_p_gainsdata.csv
CREATE TABLE src_gains_ad_p_gainsdata (
    dim1 VARCHAR NOT NULL,
    dim2 VARCHAR NOT NULL,
    dim3 VARCHAR NOT NULL,
    "level" DOUBLE NOT NULL,
    marginal DOUBLE NOT NULL,
    PRIMARY KEY (dim1, dim2, dim3)
);
COMMENT ON TABLE src_gains_ad_p_gainsdata IS 'CAPRI''s p_gainsdata (dim1-dim3: GAINS country, sector, item; level, marginal) from dat/scen/ghgtech/gains_ad.gdx (loaded at envind/ad_data_and_cali.gms l. 265); no builder; tools/build/build_ad_option.py reads its energy prices (EUR/kWh, per docs/AD_SPEC.md).';
INSERT INTO value_units VALUES
  ('src_gains_ad_p_gainsdata', 'level', NULL, 'open', 'gains_ad_p_gainsdata.level: unit to be established'),
  ('src_gains_ad_p_gainsdata', 'marginal', NULL, 'open', 'gains_ad_p_gainsdata.marginal: unit to be established');

-- file: capri_data/sources/capri_land_rents/land_rents_capri_2017.csv
CREATE TABLE src_land_rents_capri_2017 (
    capri_region VARCHAR NOT NULL,
    land_type VARCHAR NOT NULL,
    rent_eur_ha DOUBLE NOT NULL,
    levl_kha DOUBLE NOT NULL,
    PRIMARY KEY (capri_region, land_type)
);
COMMENT ON TABLE src_land_rents_capri_2017 IS 'Land rent (EUR/ha) and level (1000 ha) per CAPRI region and land type ARAC, FRUN, GRAS from CAPRI''s 2017 results (res_17<MS> dumps, D_AREA, column Y), non-positive rents replaced by CAPRI''s calibration rent (cal_land_nests.gms l. 204-226) (tools/build/build_land_rents.py --year 2017).';
INSERT INTO value_units VALUES
  ('src_land_rents_capri_2017', 'rent_eur_ha', NULL, 'open', 'land_rents_capri_2017.rent_eur_ha: unit to be established'),
  ('src_land_rents_capri_2017', 'levl_kha', NULL, 'open', 'land_rents_capri_2017.levl_kha: unit to be established');

-- file: capri_data/sources/capri_land_rents/land_rents_capri_2030.csv
CREATE TABLE src_land_rents_capri_2030 (
    capri_region VARCHAR NOT NULL,
    land_type VARCHAR NOT NULL,
    rent_eur_ha DOUBLE NOT NULL,
    levl_kha DOUBLE NOT NULL,
    PRIMARY KEY (capri_region, land_type)
);
COMMENT ON TABLE src_land_rents_capri_2030 IS 'Land rent (EUR/ha) and level (1000 ha) per CAPRI region and land type ARAC, FRUN, GRAS from CAPRI''s 2030 reference res_2_1730greendeal_refpol_endotech_all_inidefaulta (D_AREA), non-positive rents replaced by CAPRI''s calibration rent (cal_land_nests.gms l. 204-226) (tools/build/build_land_rents.py).';
INSERT INTO value_units VALUES
  ('src_land_rents_capri_2030', 'rent_eur_ha', NULL, 'open', 'land_rents_capri_2030.rent_eur_ha: unit to be established'),
  ('src_land_rents_capri_2030', 'levl_kha', NULL, 'open', 'land_rents_capri_2030.levl_kha: unit to be established');

-- file: capri_data/sources/capri_res/gd2030_endotech_ini_nbalance.csv
CREATE TABLE src_gd2030_endotech_ini_nbalance (
    region VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, "item")
);
COMMENT ON TABLE src_gd2030_endotech_ini_nbalance IS 'CAPRI''s regional N balance items (dataOut '''' . item . NITF . 2030, 1000 t N: MINFER, EXCRET, SURSOI, ...) plus UAAR LEVL (1000 ha) and N2OLEA, per region, from res_2_1730greendeal_refpol_endotech_all_inidefaulta (tools/build/extract_gd2030_nbalance.py).';
INSERT INTO value_units VALUES
  ('src_gd2030_endotech_ini_nbalance', 'value', NULL, 'open', 'gd2030_endotech_ini_nbalance.value: unit to be established');

-- file: capri_data/sources/capri_res/gd2030_endotech_ini_pbalance.csv
CREATE TABLE src_gd2030_endotech_ini_pbalance (
    region VARCHAR NOT NULL,
    col VARCHAR NOT NULL,
    row VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, col, row)
);
COMMENT ON TABLE src_gd2030_endotech_ini_pbalance IS 'CAPRI''s P2O5 balance items (1000 t P2O5) per region, per-crop LEVL, PRET, PCRD and per-animal LEVL, MANP, MANN, RUNANI (kg per head), from res_2_1730greendeal_refpol_endotech_all_inidefaulta (region, col, row, value); validation only (tools/build/build_p_balance.py).';
INSERT INTO value_units VALUES
  ('src_gd2030_endotech_ini_pbalance', 'value', NULL, 'open', 'gd2030_endotech_ini_pbalance.value: unit to be established');

-- file: capri_data/sources/capri_res/gd2030_ref_pbalance.csv
CREATE TABLE src_gd2030_ref_pbalance (
    region VARCHAR NOT NULL,
    col VARCHAR NOT NULL,
    row VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, col, row)
);
COMMENT ON TABLE src_gd2030_ref_pbalance IS 'CAPRI''s P2O5 balance items (1000 t P2O5) per region, UAAR LEVL and per-crop LEVL, PRET, PCRD, from the Green Deal 2030 reference res_2_1730greendeal_refdefaulta (region, col, row, value) (tools/build/build_p_balance.py).';
INSERT INTO value_units VALUES
  ('src_gd2030_ref_pbalance', 'value', NULL, 'open', 'gd2030_ref_pbalance.value: unit to be established');

-- file: capri_data/sources/capri_res/ref2030_welfare.csv
CREATE TABLE src_ref2030_welfare (
    region VARCHAR NOT NULL,
    col VARCHAR NOT NULL,
    row VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, col, row)
);
COMMENT ON TABLE src_ref2030_welfare IS 'CAPRI''s welfare items of the 2030 reference (region, col: WELFARE, CSSP, PROFITAGR, TARIFFREV, ...; row: product; value); no builder and no reader; per docs/WELFARE.md taken from scen_ref_2030.txt.';
INSERT INTO value_units VALUES
  ('src_ref2030_welfare', 'value', NULL, 'open', 'ref2030_welfare.value: unit to be established');

-- file: capri_data/sources/envind/anim_req_corr_2017.csv
CREATE TABLE src_anim_req_corr_2017 (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, activity, "item")
);
COMMENT ON TABLE src_anim_req_corr_2017 IS 'CAPRI''s requirement correction factors p_animReqCorrFac1(region, animal activity, ''T'', CRPR or ENNE) from the animReq_* dumps (animReq_SK.zip), used for the low-N feeding option (tools/build/build_lownfeed_effects.py).';
INSERT INTO value_units VALUES
  ('src_anim_req_corr_2017', 'value', NULL, 'open', 'anim_req_corr_2017.value: unit to be established');

-- file: capri_data/sources/envind/capri_digest_default_prd.csv
CREATE TABLE src_capri_digest_default_prd (
    "default" VARCHAR NOT NULL,
    feed VARCHAR NOT NULL,
    PRIMARY KEY ("default", feed)
);
COMMENT ON TABLE src_capri_digest_default_prd IS 'CAPRI''s set DEF_PRD: per row, a feed and the default product whose values fill the feed''s missing digestibility items, from envind/def_digestibility.gms (tools/build/build_digestibility_table.py).';

-- file: capri_data/sources/envind/capri_digestpar.csv
CREATE TABLE src_capri_digestpar (
    feed VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (feed, "item")
);
COMMENT ON TABLE src_capri_digestpar IS 'CAPRI''s feed composition p_digestPar(''EU'', ''DCOL'', feed, item) (items PAF, DM, CP, NDICP, ADICP, EE, NDF, ADF, LI, ASH, CAT), from the table in envind/def_digestibility.gms (tools/build/build_digestibility_table.py).';
INSERT INTO value_units VALUES
  ('src_capri_digestpar', 'value', NULL, 'open', 'capri_digestpar.value: unit to be established');

-- file: capri_data/sources/envind/res17_mann_crpr_expt.csv
CREATE TABLE src_res17_mann_crpr_expt (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, activity, "item")
);
COMMENT ON TABLE src_res17_mann_crpr_expt IS 'CAPRI''s LEVL, MANN and CRPR_EXPT per region and animal activity from the 2017 dumps res_17*.txt, column Y, used for the low-N feeding option (tools/build/build_lownfeed_effects.py).';
INSERT INTO value_units VALUES
  ('src_res17_mann_crpr_expt', 'value', NULL, 'open', 'res17_mann_crpr_expt.value: unit to be established');

-- file: capri_data/sources/environment/capri_manure_trade_2030.csv
CREATE TABLE src_capri_manure_trade_2030 (
    capri_region VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    kt_n DOUBLE NOT NULL,
    PRIMARY KEY (capri_region, "item")
);
COMMENT ON TABLE src_capri_manure_trade_2030 IS 'CAPRI''s manure N excretion EXCRET and net manure trade MTRADE (kt N, positive = net export) per CAPRI region, item NITF, from res_2_1730greendeal_refpol_endotech_all_inidefaulta (tools/build/build_manure_trade_base.py).';
INSERT INTO value_units VALUES
  ('src_capri_manure_trade_2030', 'kt_n', NULL, 'open', 'capri_manure_trade_2030.kt_n: unit to be established');

-- file: capri_data/sources/estnlp/gtap_armington.csv
CREATE TABLE src_gtap_armington (
    commodity VARCHAR NOT NULL,
    gtap_sector VARCHAR NOT NULL,
    esubd DOUBLE NOT NULL,
    esubm DOUBLE NOT NULL,
    PRIMARY KEY (commodity, gtap_sector)
);
COMMENT ON TABLE src_gtap_armington IS 'Per model commodity: its GTAP sector and the GTAP Armington elasticities esubd (imports vs domestic) and esubm (among imports), from CAPRI''s dat/arm/GTP57_134.gdx dumps, by a concordance declared in the builder (tools/build/ingest_pela_gtap.py).';
INSERT INTO value_units VALUES
  ('src_gtap_armington', 'esubd', NULL, 'open', 'gtap_armington.esubd: unit to be established'),
  ('src_gtap_armington', 'esubm', NULL, 'open', 'gtap_armington.esubm: unit to be established');

-- file: capri_data/sources/estnlp/pela_own_price.csv
CREATE TABLE src_pela_own_price (
    model_region VARCHAR NOT NULL,
    BARL DOUBLE,
    CORN DOUBLE,
    DWHE DOUBLE,
    MAIF DOUBLE,
    OATS DOUBLE,
    OCER DOUBLE,
    OFAR DOUBLE,
    POTA DOUBLE,
    PULS DOUBLE,
    RAPE DOUBLE,
    RYEM DOUBLE,
    SOYA DOUBLE,
    SUGB DOUBLE,
    SUNF DOUBLE,
    SWHE DOUBLE,
    PRIMARY KEY (model_region)
);
COMMENT ON TABLE src_pela_own_price IS 'CAPRI''s estimated own-price supply elasticities PELA(region, crop, crop, ''2005'') from dat/estnlp/results.gdx, per regional unit (rows) and crop (columns); MAIZ renamed CORN (tools/build/ingest_pela_gtap.py).';
INSERT INTO value_units VALUES
  ('src_pela_own_price', 'BARL', NULL, 'open', 'pela_own_price.BARL: unit to be established'),
  ('src_pela_own_price', 'CORN', NULL, 'open', 'pela_own_price.CORN: unit to be established'),
  ('src_pela_own_price', 'DWHE', NULL, 'open', 'pela_own_price.DWHE: unit to be established'),
  ('src_pela_own_price', 'MAIF', NULL, 'open', 'pela_own_price.MAIF: unit to be established'),
  ('src_pela_own_price', 'OATS', NULL, 'open', 'pela_own_price.OATS: unit to be established'),
  ('src_pela_own_price', 'OCER', NULL, 'open', 'pela_own_price.OCER: unit to be established'),
  ('src_pela_own_price', 'OFAR', NULL, 'open', 'pela_own_price.OFAR: unit to be established'),
  ('src_pela_own_price', 'POTA', NULL, 'open', 'pela_own_price.POTA: unit to be established'),
  ('src_pela_own_price', 'PULS', NULL, 'open', 'pela_own_price.PULS: unit to be established'),
  ('src_pela_own_price', 'RAPE', NULL, 'open', 'pela_own_price.RAPE: unit to be established'),
  ('src_pela_own_price', 'RYEM', NULL, 'open', 'pela_own_price.RYEM: unit to be established'),
  ('src_pela_own_price', 'SOYA', NULL, 'open', 'pela_own_price.SOYA: unit to be established'),
  ('src_pela_own_price', 'SUGB', NULL, 'open', 'pela_own_price.SUGB: unit to be established'),
  ('src_pela_own_price', 'SUNF', NULL, 'open', 'pela_own_price.SUNF: unit to be established'),
  ('src_pela_own_price', 'SWHE', NULL, 'open', 'pela_own_price.SWHE: unit to be established');

-- file: capri_data/sources/eurostat/aei_pr_gnb_nitrogen.csv
CREATE TABLE src_aei_pr_gnb_nitrogen (
    geo VARCHAR NOT NULL,
    indic_ag VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    "value" DOUBLE NOT NULL,
    flag VARCHAR
);
COMMENT ON TABLE src_aei_pr_gnb_nitrogen IS 'Eurostat gross nitrogen balance aei_pr_gnb per country, indicator, year (1985-2023), value and flag (tonnes and kg/ha, per capri_data/DATA_DICTIONARY.md); supplied by the project lead, no builder; read by tools/check/validate_gnb_eurostat.py.';
INSERT INTO value_units VALUES
  ('src_aei_pr_gnb_nitrogen', 'value', NULL, 'open', 'aei_pr_gnb_nitrogen.value: unit to be established');

-- file: capri_data/sources/eurostat/ef_lus_main_uaa_nuts2024.csv
CREATE TABLE src_ef_lus_main_uaa_nuts2024 (
    nuts VARCHAR NOT NULL,
    uaa_ha DOUBLE NOT NULL,
    "year" BIGINT NOT NULL,
    source VARCHAR NOT NULL,
    PRIMARY KEY (nuts, source)
);
COMMENT ON TABLE src_ef_lus_main_uaa_nuts2024 IS 'Utilised agricultural area (ha) per NUTS-2 region from Eurostat ef_lus_main (2023; the 2020 census where 2023 has no NUTS-2 data), with year and source text; written by tools/build/build_nuts2024_reporting.py (with --download or when the file is missing), which reads it.';
INSERT INTO value_units VALUES
  ('src_ef_lus_main_uaa_nuts2024', 'uaa_ha', NULL, 'open', 'ef_lus_main_uaa_nuts2024.uaa_ha: unit to be established'),
  ('src_ef_lus_main_uaa_nuts2024', 'year', NULL, 'open', 'ef_lus_main_uaa_nuts2024.year: unit to be established');

-- file: capri_data/sources/fao_2021/trade_flows_2021.csv
CREATE TABLE src_trade_flows_2021 (
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
    PRIMARY KEY (exporter, importer)
);
COMMENT ON TABLE src_trade_flows_2021 IS 'FAOSTAT 2021 bilateral trade (sources/fao_2021/README.md): one row per exporter and importer of 29 trade regions, one column per commodity; no builder; read only by tools/build/recalibrate_trade_2017.py as a comparison.';
INSERT INTO value_units VALUES
  ('src_trade_flows_2021', 'SWHE', NULL, 'open', 'trade_flows_2021.SWHE: unit to be established'),
  ('src_trade_flows_2021', 'DWHE', NULL, 'open', 'trade_flows_2021.DWHE: unit to be established'),
  ('src_trade_flows_2021', 'BARL', NULL, 'open', 'trade_flows_2021.BARL: unit to be established'),
  ('src_trade_flows_2021', 'CORN', NULL, 'open', 'trade_flows_2021.CORN: unit to be established'),
  ('src_trade_flows_2021', 'OCER', NULL, 'open', 'trade_flows_2021.OCER: unit to be established'),
  ('src_trade_flows_2021', 'RAPE', NULL, 'open', 'trade_flows_2021.RAPE: unit to be established'),
  ('src_trade_flows_2021', 'SUNF', NULL, 'open', 'trade_flows_2021.SUNF: unit to be established'),
  ('src_trade_flows_2021', 'SOYA', NULL, 'open', 'trade_flows_2021.SOYA: unit to be established'),
  ('src_trade_flows_2021', 'OOIL', NULL, 'open', 'trade_flows_2021.OOIL: unit to be established'),
  ('src_trade_flows_2021', 'SUGB', NULL, 'open', 'trade_flows_2021.SUGB: unit to be established'),
  ('src_trade_flows_2021', 'SUGR', NULL, 'open', 'trade_flows_2021.SUGR: unit to be established'),
  ('src_trade_flows_2021', 'POTA', NULL, 'open', 'trade_flows_2021.POTA: unit to be established'),
  ('src_trade_flows_2021', 'PULS', NULL, 'open', 'trade_flows_2021.PULS: unit to be established'),
  ('src_trade_flows_2021', 'TOMA', NULL, 'open', 'trade_flows_2021.TOMA: unit to be established'),
  ('src_trade_flows_2021', 'OVEG', NULL, 'open', 'trade_flows_2021.OVEG: unit to be established'),
  ('src_trade_flows_2021', 'APPL', NULL, 'open', 'trade_flows_2021.APPL: unit to be established'),
  ('src_trade_flows_2021', 'OFRU', NULL, 'open', 'trade_flows_2021.OFRU: unit to be established'),
  ('src_trade_flows_2021', 'CITR', NULL, 'open', 'trade_flows_2021.CITR: unit to be established'),
  ('src_trade_flows_2021', 'WINE', NULL, 'open', 'trade_flows_2021.WINE: unit to be established'),
  ('src_trade_flows_2021', 'OLIV', NULL, 'open', 'trade_flows_2021.OLIV: unit to be established'),
  ('src_trade_flows_2021', 'MILK', NULL, 'open', 'trade_flows_2021.MILK: unit to be established'),
  ('src_trade_flows_2021', 'BUTR', NULL, 'open', 'trade_flows_2021.BUTR: unit to be established'),
  ('src_trade_flows_2021', 'SKIM', NULL, 'open', 'trade_flows_2021.SKIM: unit to be established'),
  ('src_trade_flows_2021', 'CHES', NULL, 'open', 'trade_flows_2021.CHES: unit to be established'),
  ('src_trade_flows_2021', 'WHEY', NULL, 'open', 'trade_flows_2021.WHEY: unit to be established'),
  ('src_trade_flows_2021', 'BEEF', NULL, 'open', 'trade_flows_2021.BEEF: unit to be established'),
  ('src_trade_flows_2021', 'PORK', NULL, 'open', 'trade_flows_2021.PORK: unit to be established'),
  ('src_trade_flows_2021', 'POUL', NULL, 'open', 'trade_flows_2021.POUL: unit to be established'),
  ('src_trade_flows_2021', 'SHGM', NULL, 'open', 'trade_flows_2021.SHGM: unit to be established'),
  ('src_trade_flows_2021', 'EGGS', NULL, 'open', 'trade_flows_2021.EGGS: unit to be established'),
  ('src_trade_flows_2021', 'FATS', NULL, 'open', 'trade_flows_2021.FATS: unit to be established'),
  ('src_trade_flows_2021', 'OFOD_M', NULL, 'open', 'trade_flows_2021.OFOD_M: unit to be established');

-- file: capri_data/sources/fao_agg_2017/fao_agg_dairy_products_bas.csv
CREATE TABLE src_fao_agg_dairy_products_bas (
    region VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    product VARCHAR NOT NULL,
    tonnes DOUBLE NOT NULL,
    PRIMARY KEY (region, "item", product)
);
COMMENT ON TABLE src_fao_agg_dairy_products_bas IS 'CAPRI''s FAO_agg base-period balances (p_dataMarket, year BAS: MAPR, DOMM, IMPT, EXPT; tonnes) of the dairy products per CAPRI region, from fao_agg_17_datamarket.txt (tools/build/build_dairy_world_markets.py).';
INSERT INTO value_units VALUES
  ('src_fao_agg_dairy_products_bas', 'tonnes', NULL, 'open', 'fao_agg_dairy_products_bas.tonnes: unit to be established');

-- file: capri_data/sources/fao_agg_2017/fao_agg_market_balances_bas.csv
CREATE TABLE src_fao_agg_market_balances_bas (
    region VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    product VARCHAR NOT NULL,
    tonnes DOUBLE NOT NULL,
    PRIMARY KEY (region, "item", product)
);
COMMENT ON TABLE src_fao_agg_market_balances_bas IS 'CAPRI''s FAO_agg base-period balances (p_dataMarket, year BAS: MAPR, DOMM, IMPT, EXPT; tonnes) of the market products per CAPRI region, from fao_agg_17_datamarket.txt (tools/build/build_world_market_baseline.py).';
INSERT INTO value_units VALUES
  ('src_fao_agg_market_balances_bas', 'tonnes', NULL, 'open', 'fao_agg_market_balances_bas.tonnes: unit to be established');

-- file: capri_data/sources/ghgtech/LitRevFertTech_p_litRevFertTechs.csv
CREATE TABLE src_litrevferttech_p_litrevferttechs (
    region VARCHAR NOT NULL,
    technology VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    system VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, technology, activity, system, "item")
);
COMMENT ON TABLE src_litrevferttech_p_litrevferttechs IS 'CAPRI''s p_litRevFertTechs(region, technology, activity, system, item): relative change in emissions of a fertiliser technology, the records used, from the gdxdump of dat/scen/ghgtech/LitRevFertTech.gdx (the full dump beside it, LitRevFertTech_p_litRevFertTechs_all.csv); no builder; read by tools/build/build_fert_side_effects.py.';
INSERT INTO value_units VALUES
  ('src_litrevferttech_p_litrevferttechs', 'value', NULL, 'open', 'LitRevFertTech_p_litRevFertTechs.value: unit to be established');

-- file: capri_data/sources/ghgtech/LitRevFertTech_p_litRevFertTechs_no3.csv
CREATE TABLE src_litrevferttech_p_litrevferttechs_no3 (
    region VARCHAR NOT NULL,
    technology VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    system VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, technology, activity, system, "item")
);
COMMENT ON TABLE src_litrevferttech_p_litrevferttechs_no3 IS 'The nitrate leaching and runoff records (NO3...) of CAPRI''s p_litRevFertTechs(region, technology, activity, system, item), taken from the full dump LitRevFertTech_p_litRevFertTechs_all.csv (the gdxdump text converted by tools/build/convert_sources_to_csv.py) (tools/build/build_fert_side_effects.py).';
INSERT INTO value_units VALUES
  ('src_litrevferttech_p_litrevferttechs_no3', 'value', NULL, 'open', 'LitRevFertTech_p_litRevFertTechs_no3.value: unit to be established');

-- file: capri_data/sources/ghgtech/capri_costsavings_2030.csv
CREATE TABLE src_capri_costsavings_2030 (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    technology VARCHAR NOT NULL,
    target VARCHAR NOT NULL,
    run VARCHAR NOT NULL,
    "level" DOUBLE NOT NULL,
    marginal DOUBLE NOT NULL,
    PRIMARY KEY (region, activity, technology, target, run)
);
COMMENT ON TABLE src_capri_costsavings_2030 IS 'Level and marginal of CAPRI''s v_Miti per EU region, activity, mitigation technology and target, in the calibration runs ini and max (costsavings_ini/max_21730_jul15.gdx dumps, 2030); options other than NOC (tools/build/extract_capri_costsavings.py).';
INSERT INTO value_units VALUES
  ('src_capri_costsavings_2030', 'level', NULL, 'open', 'capri_costsavings_2030.level: unit to be established'),
  ('src_capri_costsavings_2030', 'marginal', NULL, 'open', 'capri_costsavings_2030.marginal: unit to be established');

-- file: capri_data/sources/market/bilateral_trq_dataout_2017.csv
CREATE TABLE src_bilateral_trq_dataout_2017 (
    exporter VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    product VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (exporter, "item", product)
);
COMMENT ON TABLE src_bilateral_trq_dataout_2017 IS 'CAPRI''s bilateral TRQ and price items (TrqNT, TAMFN, TSMFN, TaAppl, TsAppl, Fob, TCost, ImportQ) of the EU policy block ''EU'' as importer, per exporter and product, from market_base_1717 dataOut, 2017 (tools/build/build_bilateral_market.py).';
INSERT INTO value_units VALUES
  ('src_bilateral_trq_dataout_2017', 'value', NULL, 'open', 'bilateral_trq_dataout_2017.value: unit to be established');

-- file: capri_data/sources/market/bilateral_trq_dataout_2030.csv
CREATE TABLE src_bilateral_trq_dataout_2030 (
    exporter VARCHAR,
    "item" VARCHAR NOT NULL,
    product VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL
);
COMMENT ON TABLE src_bilateral_trq_dataout_2030 IS 'CAPRI''s bilateral TRQ and price items (TrqNT, TAMFN, TSMFN, TaAppl, TsAppl, Fob, TCost, ImportQ) of the EU policy block ''EU'' as importer, per exporter and product, from markmarket_greendeal_1730et_base_1717 dataOut, 2030 (tools/build/build_bilateral_market.py).';
INSERT INTO value_units VALUES
  ('src_bilateral_trq_dataout_2030', 'value', NULL, 'open', 'bilateral_trq_dataout_2030.value: unit to be established');

-- file: capri_data/sources/market/biofuel_proc_hessian_2030.csv
CREATE TABLE src_biofuel_proc_hessian_2030 (
    region VARCHAR NOT NULL,
    product VARCHAR NOT NULL,
    price_of VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, product, price_of)
);
COMMENT ON TABLE src_biofuel_proc_hessian_2030 IS 'CAPRI''s p_hessNQProc(region, product, price_of, ''CAL'') rows of the biofuels BIOE and BIOD, own and cross terms, per market region, from elas_2_1730defaulta (tools/build/build_biofuel_market.py).';
INSERT INTO value_units VALUES
  ('src_biofuel_proc_hessian_2030', 'value', NULL, 'open', 'biofuel_proc_hessian_2030.value: unit to be established');

-- file: capri_data/sources/market/biofuel_proc_hessian_2017.csv
CREATE TABLE src_biofuel_proc_hessian_2017 (
    region VARCHAR NOT NULL,
    product VARCHAR NOT NULL,
    price_of VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, product, price_of)
);
COMMENT ON TABLE src_biofuel_proc_hessian_2017 IS 'CAPRI''s p_hessNQProc(region, product, price_of, ''CAL'') rows of the biofuels BIOE and BIOD, own and cross terms, per market region, from elas_2_1717defaulta (tools/build/build_biofuel_market.py).';
INSERT INTO value_units VALUES
  ('src_biofuel_proc_hessian_2017', 'value', NULL, 'open', 'biofuel_proc_hessian_2017.value: unit to be established');

-- file: capri_data/sources/market/dairy_dataout_2030.csv
CREATE TABLE src_dairy_dataout_2030 (
    region VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    product VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, "item", product)
);
COMMENT ON TABLE src_dairy_dataout_2030 IS 'CAPRI''s dairy market items (PROD, PROC, GROF, HCOM, PPRI, FATS, PROT, ...) per member state and ''EU'' and dairy product, from markmarket_greendeal_1730et_base_1717 dataOut, 2030 (tools/build/build_dairy_processing.py).';
INSERT INTO value_units VALUES
  ('src_dairy_dataout_2030', 'value', NULL, 'open', 'dairy_dataout_2030.value: unit to be established');

-- file: capri_data/sources/market/dairy_elasticities_2030.csv
CREATE TABLE src_dairy_elasticities_2030 (
    param VARCHAR NOT NULL,
    ms VARCHAR NOT NULL,
    row VARCHAR NOT NULL,
    col VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (param, ms, row, col)
);
COMMENT ON TABLE src_dairy_elasticities_2030 IS 'CAPRI''s dairy parameters p_hessNQDairy, p_ElasDair and p_ElasDem (param, member state, row, col; CAL) between dairy products, from elas_2_1730defaulta (tools/build/build_dairy_processing.py).';
INSERT INTO value_units VALUES
  ('src_dairy_elasticities_2030', 'value', NULL, 'open', 'dairy_elasticities_2030.value: unit to be established');

-- file: capri_data/sources/market/dairy_world_dataout_2030.csv
CREATE TABLE src_dairy_world_dataout_2030 (
    region VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    product VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, "item", product)
);
COMMENT ON TABLE src_dairy_world_dataout_2030 IS 'CAPRI''s dairy market items (PROD, PROC, FATS, PROT, PPRI, HCON, FEED, Imports_noIntra, Exports_noIntra) per market region and dairy product, from markmarket_greendeal_1730et_base_1717 dataOut, 2030 (tools/build/build_dairy_world_blocks.py).';
INSERT INTO value_units VALUES
  ('src_dairy_world_dataout_2030', 'value', NULL, 'open', 'dairy_world_dataout_2030.value: unit to be established');

-- file: capri_data/sources/market/dairy_world_elasticities_2030.csv
CREATE TABLE src_dairy_world_elasticities_2030 (
    param VARCHAR NOT NULL,
    rms VARCHAR NOT NULL,
    row VARCHAR NOT NULL,
    col VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (param, rms, row, col)
);
COMMENT ON TABLE src_dairy_world_elasticities_2030 IS 'CAPRI''s p_hessNQDairy, p_ElasDem (between dairy products) and p_hessNQSupp (MILK own term) per market region, CAL, from elas_2_1730defaulta (param, rms, row, col, value) (tools/build/build_dairy_world_blocks.py).';
INSERT INTO value_units VALUES
  ('src_dairy_world_elasticities_2030', 'value', NULL, 'open', 'dairy_world_elasticities_2030.value: unit to be established');

-- file: capri_data/sources/market/feed_bulks_dataout_2030.csv
CREATE TABLE src_feed_bulks_dataout_2030 (
    region VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    product VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, "item", product)
);
COMMENT ON TABLE src_feed_bulks_dataout_2030 IS 'CAPRI''s FEED per EU member state and product, ARM1P of the EU trade block EU27yr19 and Norway, and Norway''s use items, from markmarket_greendeal_1730et_base_1717 dataOut, 2030 (tools/build/build_feed_bulks.py).';
INSERT INTO value_units VALUES
  ('src_feed_bulks_dataout_2030', 'value', NULL, 'open', 'feed_bulks_dataout_2030.value: unit to be established');

-- file: capri_data/sources/market/feed_demand_nonEU_elas_2030.csv
CREATE TABLE src_feed_demand_noneu_elas_2030 (
    rms VARCHAR NOT NULL,
    feed VARCHAR NOT NULL,
    price_of VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (rms, feed, price_of)
);
COMMENT ON TABLE src_feed_demand_noneu_elas_2030 IS 'CAPRI''s feed demand elasticities p_ElasFeed(rms, feed, price_of, ''CAL'') per behavioural market region, for the products the model trades, from elas_2_1730defaulta (tools/build/build_feed_demand_nonEU.py).';
INSERT INTO value_units VALUES
  ('src_feed_demand_noneu_elas_2030', 'value', NULL, 'open', 'feed_demand_nonEU_elas_2030.value: unit to be established');

-- file: capri_data/sources/market/feed_demand_nonEU_use_2030.csv
CREATE TABLE src_feed_demand_noneu_use_2030 (
    rms VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    product VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (rms, "item", product)
);
COMMENT ON TABLE src_feed_demand_noneu_use_2030 IS 'CAPRI''s uses HCON, FEED, PROC, BIOF per market region (EU member states included) and product at the 2030 calibration point CAL, from data_market_1730defaulta (tools/build/build_feed_demand_nonEU.py).';
INSERT INTO value_units VALUES
  ('src_feed_demand_noneu_use_2030', 'value', NULL, 'open', 'feed_demand_nonEU_use_2030.value: unit to be established');

-- file: capri_data/sources/market/processing_yields_dataout_2030.csv
CREATE TABLE src_processing_yields_dataout_2030 (
    ms VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    product VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (ms, "item", product)
);
COMMENT ON TABLE src_processing_yields_dataout_2030 IS 'CAPRI''s GROF of olives and paddy (OLIV, PARI) and MAPR of olive oil and milled rice (OLIO, RICE) per member state, from markmarket_greendeal_1730et_base_1717 dataOut, 2030 (tools/build/build_processing_yields.py).';
INSERT INTO value_units VALUES
  ('src_processing_yields_dataout_2030', 'value', NULL, 'open', 'processing_yields_dataout_2030.value: unit to be established');

-- file: capri_data/sources/market/sugar_processing_dataout_2030.csv
CREATE TABLE src_sugar_processing_dataout_2030 (
    ms VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    product VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (ms, "item", product)
);
COMMENT ON TABLE src_sugar_processing_dataout_2030 IS 'CAPRI''s sugar beet GROF and PRCM and white sugar MAPR and PRCY per member state, from markmarket_greendeal_1730et_base_1717 dataOut, 2030 (tools/build/build_sugar_processing.py).';
INSERT INTO value_units VALUES
  ('src_sugar_processing_dataout_2030', 'value', NULL, 'open', 'sugar_processing_dataout_2030.value: unit to be established');

-- file: capri_data/sources/nuts/nuts2013_2016.csv
CREATE TABLE src_nuts2013_2016 (
    code_2013 VARCHAR,
    code_2016 VARCHAR,
    country VARCHAR,
    level1 VARCHAR,
    level2 VARCHAR,
    level3 VARCHAR,
    change VARCHAR
);
COMMENT ON TABLE src_nuts2013_2016 IS 'Correspondence NUTS 2013 to NUTS 2016 (codes, names by level, change), from Eurostat''s workbook NUTS2013-NUTS2016__1_.xlsx (sheet ''NUTS2013-NUTS2016'', the rows with a code, columns B-H, text as written, CRLF line ends as committed before), written by tools/build/convert_sources_to_csv.py; read by tools/build/build_nuts2024_reporting.py.';

-- file: capri_data/sources/nuts/nuts2016_2021.csv
CREATE TABLE src_nuts2016_2021 (
    code_2016 VARCHAR,
    code_2021 VARCHAR,
    country VARCHAR,
    level1 VARCHAR,
    level2 VARCHAR,
    level3 VARCHAR,
    change_codes DOUBLE,
    change_comments VARCHAR
);
COMMENT ON TABLE src_nuts2016_2021 IS 'Correspondence NUTS 2016 to NUTS 2021 (codes, names by level, changes), from Eurostat''s workbook NUTS2021.xlsx (sheet ''Changes detailed NUTS 2016-2021'', the rows with a code, columns A-H, the text stripped of surrounding white space as committed before), written by tools/build/convert_sources_to_csv.py; read by tools/build/build_nuts2024_reporting.py.';
INSERT INTO value_units VALUES
  ('src_nuts2016_2021', 'change_codes', NULL, 'open', 'nuts2016_2021.change_codes: unit to be established');

-- file: capri_data/sources/nuts/nuts2021_2024.csv
CREATE TABLE src_nuts2021_2024 (
    country VARCHAR NOT NULL,
    code_2021 VARCHAR,
    code_2024 VARCHAR,
    level1 VARCHAR,
    level2 VARCHAR,
    level3 VARCHAR,
    change VARCHAR
);
COMMENT ON TABLE src_nuts2021_2024 IS 'Correspondence NUTS 2021 to NUTS 2024 (country, codes, names by level, change), from Eurostat''s workbook NUTS2021-NUTS2024.xlsx (sheet ''NUTS2021- NUTS2024'', the rows with a code, columns B-H, the text stripped of surrounding white space as committed before), written by tools/build/convert_sources_to_csv.py; read by tools/build/build_nuts2024_reporting.py.';

-- file: capri_data/sources/nuts/nuts2024.csv
CREATE TABLE src_nuts2024 (
    country VARCHAR NOT NULL,
    code VARCHAR NOT NULL,
    label VARCHAR NOT NULL,
    "level" BIGINT NOT NULL,
    PRIMARY KEY (country, code, label)
);
COMMENT ON TABLE src_nuts2024 IS 'NUTS 2024 codes with country, label and level, from Eurostat''s workbook NUTS2021-NUTS2024.xlsx (sheet ''NUTS2024'', the rows with a code, columns A-D, as committed before), written by tools/build/convert_sources_to_csv.py; read by capri_mod/tests/test_nuts_reporting.py.';
INSERT INTO value_units VALUES
  ('src_nuts2024', 'level', NULL, 'open', 'nuts2024.level: unit to be established');

-- file: capri_data/sources/unsourced/producer_prices_no_builder.csv
CREATE TABLE src_producer_prices_no_builder (
    activity VARCHAR NOT NULL,
    price DOUBLE NOT NULL,
    note VARCHAR NOT NULL,
    PRIMARY KEY (activity, note)
);
COMMENT ON TABLE src_producer_prices_no_builder IS 'EU producer price rows no builder computes (activity, price, note): one row, set-aside SETA at 0 by convention; hand-kept, read by tools/build/build_eu_producer_prices.py (KNOWN_ISSUES K72).';
INSERT INTO value_units VALUES
  ('src_producer_prices_no_builder', 'price', NULL, 'open', 'producer_prices_no_builder.price: unit to be established');

