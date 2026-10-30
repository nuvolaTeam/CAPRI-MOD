-- CAPTRD-MOD's labour and policy inputs under capri_data/pipeline/captrd (labour_ageline.gms, captrd_policy.gms) and the
-- sugar quota extracts they come from (30 October 2026). Structure (types, NOT NULL, keys) from the files; units open where no
-- builder or CAPRI file states them.

-- file: capri_data/pipeline/captrd/dat/ageline.csv
CREATE TABLE ctrd_ageline (
    region VARCHAR NOT NULL,
    age BIGINT NOT NULL,
    "year" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, "year", age)
);
COMMENT ON TABLE ctrd_ageline IS 'CAPRI''s AGELINE(region, age, year): farm holders by age class in the farm structure surveys, NUTS 1 regions (dat/baseline/ageline.gdx, from the parquet mirror of CAPRI''s dat folder; the year label ageline kept as it is), read by baseline/labour_ageline.gms (captrd.gms l. 902) for the labour bounds (tools/build/build_captrd_dat.py --ageline)';
INSERT INTO value_units VALUES
  ('ctrd_ageline', 'value', NULL, 'open', 'ageline.value: unit to be established');

-- file: capri_data/pipeline/captrd/dat/p_minlabourperact.csv
CREATE TABLE ctrd_p_minlabourperact (
    act VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (act)
);
COMMENT ON TABLE ctrd_p_minlabourperact IS 'CAPRI''s p_minLabourPerAct(act): minimum labour per activity unit (h, 2008), transcribed from baseline/labour_ageline.gms (copy in capri_data/sources/capri_gams) by tools/build/build_captrd_dat.py';
INSERT INTO value_units VALUES
  ('ctrd_p_minlabourperact', 'value', NULL, 'open', 'p_minlabourperact.value: unit to be established');

-- file: capri_data/pipeline/captrd/dat/p_mquotadat.csv
CREATE TABLE ctrd_p_mquotadat (
    region VARCHAR NOT NULL,
    info VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, info, "year")
);
COMMENT ON TABLE ctrd_p_mquotadat IS 'CAPRI''s p_MQuotaDat(MS, info, year): milk quotas, deliveries and direct sales (DG AGRI), from dat/coco/milk_quota_dat.gms (copy in capri_data/sources/capri_dat), read by captrd/captrd_policy.gms (tools/build/build_captrd_dat.py)';
INSERT INTO value_units VALUES
  ('ctrd_p_mquotadat', 'value', NULL, 'open', 'p_mquotadat.value: unit to be established');

-- file: capri_data/pipeline/captrd/dat/p_mquotareg.csv
CREATE TABLE ctrd_p_mquotareg (
    region VARCHAR NOT NULL,
    info VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, info, "year")
);
COMMENT ON TABLE ctrd_p_mquotareg IS 'CAPRI''s PMQuotaReg(MS, QUTtot, year): total milk quotas 2004-2014 (1000 t), from pol_input/mquota_update.gms (copy in capri_data/sources/capri_gams), read by captrd/captrd_policy.gms (tools/build/build_captrd_dat.py)';
INSERT INTO value_units VALUES
  ('ctrd_p_mquotareg', 'value', 'U_1000t', 'capri', 'CAPRI''s quantity in 1000 t (builder docstring; sugar README)');

-- file: capri_data/pipeline/captrd/dat/p_ppsqcbuyback.csv
CREATE TABLE ctrd_p_ppsqcbuyback (
    region VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, "year")
);
COMMENT ON TABLE ctrd_p_ppsqcbuyback IS 'CAPRI''s p_PPSQCBuyBack(MSALL, year): sugar quota buy-back, from CAPRI''s input_load_sugar_quotas.gdx (capri_data/sources/capri_dat/sugar/p_PPSQCBuyBack.csv), read by captrd/captrd_policy.gms (tools/build/build_captrd_dat.py)';
INSERT INTO value_units VALUES
  ('ctrd_p_ppsqcbuyback', 'year', NULL, 'open', 'p_ppsqcbuyback.year: unit to be established'),
  ('ctrd_p_ppsqcbuyback', 'value', NULL, 'open', 'p_ppsqcbuyback.value: unit to be established');

-- file: capri_data/pipeline/captrd/dat/p_ppsqrenounce.csv
CREATE TABLE ctrd_p_ppsqrenounce (
    region VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, "year")
);
COMMENT ON TABLE ctrd_p_ppsqrenounce IS 'CAPRI''s p_PPSQRenounce(MSALL, year): renounced sugar quota, from CAPRI''s input_load_sugar_quotas.gdx (capri_data/sources/capri_dat/sugar/p_PPSQRenounce.csv), read by captrd/captrd_policy.gms (tools/build/build_captrd_dat.py)';
INSERT INTO value_units VALUES
  ('ctrd_p_ppsqrenounce', 'value', NULL, 'open', 'p_ppsqrenounce.value: unit to be established');

-- file: capri_data/pipeline/captrd/dat/p_smallprodshare.csv
CREATE TABLE ctrd_p_smallprodshare (
    "year" BIGINT NOT NULL,
    region VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, "year")
);
COMMENT ON TABLE ctrd_p_smallprodshare IS 'CAPRI''s p_smallProdShare(year, MS): small producers'' share outside compulsory set-aside, from dat/policy/smal_pshar.gms (copy in capri_data/sources/capri_dat), read by captrd/captrd_policy.gms (tools/build/build_captrd_dat.py)';
INSERT INTO value_units VALUES
  ('ctrd_p_smallprodshare', 'value', NULL, 'open', 'p_smallprodshare.value: unit to be established');

-- file: capri_data/pipeline/captrd/dat/p_squotas.csv
CREATE TABLE ctrd_p_squotas (
    region VARCHAR NOT NULL,
    quota VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, quota, "year")
);
COMMENT ON TABLE ctrd_p_squotas IS 'CAPRI''s p_SQuotas(MSALL, QUOTAS, year): sugar quotas (1000 t white sugar), from CAPRI''s input_load_sugar_quotas.gdx (capri_data/sources/capri_dat/sugar/p_SQuotas.csv), read by captrd/captrd_policy.gms (tools/build/build_captrd_dat.py)';
INSERT INTO value_units VALUES
  ('ctrd_p_squotas', 'value', 'U_1000t', 'capri', 'CAPRI''s quantity in 1000 t (builder docstring; sugar README)');

-- file: capri_data/pipeline/captrd/sets/grcu.csv
CREATE TABLE ctrd_grcu (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_grcu IS 'CAPRI''s global set GRCU (gams/sets.gms) as instantiated in sim_ini_21730 (capri_reference/sets/simini_21730), copied by tools/build/build_captrd_sets.py';

-- file: capri_data/pipeline/captrd/sets/map_rrt.csv
CREATE TABLE ctrd_map_rrt (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    d2 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1, d2)
);
COMMENT ON TABLE ctrd_map_rrt IS 'CAPRI''s global set MAP_RRT (gams/sets.gms) as instantiated in sim_ini_21730 (capri_reference/sets/simini_21730), copied by tools/build/build_captrd_sets.py';

-- file: capri_data/pipeline/captrd/sets/msall.csv
CREATE TABLE ctrd_msall (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_msall IS 'CAPRI''s global set MSALL (gams/sets.gms) as instantiated in sim_ini_21730 (capri_reference/sets/simini_21730), copied by tools/build/build_captrd_sets.py';

-- file: capri_data/pipeline/captrd/sets/nosugquotaaglinkversion.csv
CREATE TABLE ctrd_nosugquotaaglinkversion (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_nosugquotaaglinkversion IS 'CAPRI''s global set noSugQuotaAglinkVersion (gams/sets.gms) as instantiated in sim_ini_21730 (capri_reference/sets/simini_21730), copied by tools/build/build_captrd_sets.py';

-- file: capri_data/pipeline/captrd/sets/rset.csv
CREATE TABLE ctrd_rset (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_rset IS 'CAPRI''s global set RSET (gams/sets.gms) as instantiated in sim_ini_21730 (capri_reference/sets/simini_21730), copied by tools/build/build_captrd_sets.py';

-- file: capri_data/pipeline/captrd/sets/srnuts1.csv
CREATE TABLE ctrd_srnuts1 (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_srnuts1 IS 'CAPRI''s global set SRNUTS1 (gams/sets.gms) as instantiated in sim_ini_21730 (capri_reference/sets/simini_21730), copied by tools/build/build_captrd_sets.py';

-- file: capri_data/sources/capri_dat/sugar/p_PPSQCBuyBack.csv
CREATE TABLE src_capri_dat_sugar_p_ppsqcbuyback (
    region VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, "year")
);
COMMENT ON TABLE src_capri_dat_sugar_p_ppsqcbuyback IS 'CAPRI''s p_PPSQCBuyBack(MSALL, year) of input_load_sugar_quotas.gdx (sugar/load_quotas.gms), as the parquet mirror of CAPRI''s dat folder holds it, columns renamed (README in the folder); no builder';
INSERT INTO value_units VALUES
  ('src_capri_dat_sugar_p_ppsqcbuyback', 'year', NULL, 'open', 'p_PPSQCBuyBack.year: unit to be established'),
  ('src_capri_dat_sugar_p_ppsqcbuyback', 'value', NULL, 'open', 'p_PPSQCBuyBack.value: unit to be established');

-- file: capri_data/sources/capri_dat/sugar/p_PPSQRenounce.csv
CREATE TABLE src_capri_dat_sugar_p_ppsqrenounce (
    region VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, "year")
);
COMMENT ON TABLE src_capri_dat_sugar_p_ppsqrenounce IS 'CAPRI''s p_PPSQRenounce(MSALL, year) of input_load_sugar_quotas.gdx (sugar/load_quotas.gms), as the parquet mirror of CAPRI''s dat folder holds it, columns renamed (README in the folder); no builder';
INSERT INTO value_units VALUES
  ('src_capri_dat_sugar_p_ppsqrenounce', 'value', NULL, 'open', 'p_PPSQRenounce.value: unit to be established');

-- file: capri_data/sources/capri_dat/sugar/p_SQuotas.csv
CREATE TABLE src_capri_dat_sugar_p_squotas (
    region VARCHAR NOT NULL,
    quota VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, quota, "year")
);
COMMENT ON TABLE src_capri_dat_sugar_p_squotas IS 'CAPRI''s p_SQuotas(MSALL, QUOTAS, year) of input_load_sugar_quotas.gdx (sugar/load_quotas.gms; 1000 t white sugar), as the parquet mirror of CAPRI''s dat folder holds it, columns renamed (README in the folder); no builder';
INSERT INTO value_units VALUES
  ('src_capri_dat_sugar_p_squotas', 'value', 'U_1000t', 'capri', 'CAPRI''s quantity in 1000 t (builder docstring; sugar README)');

