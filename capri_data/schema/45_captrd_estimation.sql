-- CAPTRD's member-state estimation m_trendMS (captrd/equations.gms; capri_mod/pipeline/captrd/estimate_ms.py, 12 November 2026): the sets and parameters its equations use beyond those of 28_captrd_sets.sql and 29_captrd_more.sql.

-- file: capri_data/pipeline/captrd/sets/arbact.csv
CREATE TABLE ctrd_arbact (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_arbact IS 'CAPRI''s global set arbAct (crops on arable land; gams/sets.gms l. 2962): one member per row in d0, 40 members (e.g. SWHE, DWHE); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py, for the equations of captrd/equations.gms.';

-- file: capri_data/pipeline/captrd/sets/secod.csv
CREATE TABLE ctrd_secod (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_secod IS 'CAPRI''s global set SECOD (processed outputs linked to PRCM; gams/sets.gms l. 5135): one member per row in d0, 13 members (e.g. RICE, MOLA); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py, for the equations of captrd/equations.gms.';

-- file: capri_data/pipeline/captrd/sets/resimp.csv
CREATE TABLE ctrd_resimp (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_resimp IS 'CAPRI''s global set RESIMP (by-products of milling and processing (FPRI, FENI); gams/sets.gms l. 5323): one member per row in d0, 2 members (e.g. FPRI, FENI); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py, for the equations of captrd/equations.gms.';

-- file: capri_data/pipeline/captrd/sets/resimp_t_o.csv
CREATE TABLE ctrd_resimp_t_o (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_resimp_t_o IS 'CAPRI''s global mapping RESIMP_T_O (by-product of milling or processing to the product it comes from; gams/sets.gms l. 5325): one pair per row (d0, d1), 10 pairs (e.g. FPRI.SWHE, FPRI.DWHE); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py, for the equations of captrd/equations.gms.';

-- file: capri_data/pipeline/captrd/sets/mlkseco.csv
CREATE TABLE ctrd_mlkseco (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_mlkseco IS 'CAPRI''s global set MLKSECO (dairy products; gams/sets.gms l. 5078): one member per row in d0, 9 members (e.g. WHEP, CASE); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py, for the equations of captrd/equations.gms.';

-- file: capri_data/pipeline/captrd/sets/mlko.csv
CREATE TABLE ctrd_mlko (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_mlko IS 'CAPRI''s global set MLKO (raw milks as tradeable products (COMI, SGMI); gams/sets.gms l. 5072): one member per row in d0, 2 members (e.g. COMI, SGMI); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py, for the equations of captrd/equations.gms.';

-- file: capri_data/pipeline/captrd/sets/o_to_yani.csv
CREATE TABLE ctrd_o_to_yani (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_o_to_yani IS 'CAPRI''s global mapping O_TO_YANI (young animals produced to young animals used as inputs; gams/sets.gms l. 5331): one pair per row (d0, d1), 8 pairs (e.g. YCOW.ICOW, YBUL.IBUL); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py, for the equations of captrd/equations.gms.';

-- file: capri_data/pipeline/captrd/sets/rows_lab.csv
CREATE TABLE ctrd_rows_lab (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_rows_lab IS 'CAPTRD''s set ROWS_LAB (the labour rows; sets_captrd.gms l. 252-259): one member per row in d0, 6 members (e.g. LABO, LABN); transcribed by tools/build/build_captrd_sets.py, for the equations of captrd/equations.gms.';

-- file: capri_data/pipeline/captrd/sets/mlkcnt.csv
CREATE TABLE ctrd_mlkcnt (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_mlkcnt IS 'CAPTRD''s set MLKCNT (the milk components; sets_captrd.gms l. 330): one member per row in d0, 2 members (e.g. FATS, PROT); transcribed by tools/build/build_captrd_sets.py, for the equations of captrd/equations.gms.';

-- file: capri_data/pipeline/captrd/sets/lo_to_hi.csv
CREATE TABLE ctrd_lo_to_hi (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_lo_to_hi IS 'CAPTRD''s set LO_TO_HI (low-yield to high-yield variant of an activity; sets_captrd.gms l. 376): one pair per row (d0, d1), 4 pairs (e.g. GRAE.GRAI, BULL.BULH); transcribed by tools/build/build_captrd_sets.py, for the equations of captrd/equations.gms.';

-- file: capri_data/pipeline/captrd/sets/splitactslo.csv
CREATE TABLE ctrd_splitactslo (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_splitactslo IS 'CAPTRD''s set SplitActsLo (the low-yield variants of the split activities; sets_captrd.gms l. 377): one member per row in d0, 4 members (e.g. DCOL, BULL); transcribed by tools/build/build_captrd_sets.py, for the equations of captrd/equations.gms.';

-- file: capri_data/pipeline/captrd/sets/bulf.csv
CREATE TABLE ctrd_bulf (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_bulf IS 'CAPTRD''s set BULF (the male fattening activities of Dailyup_; sets_captrd.gms l. 341): one member per row in d0, 2 members (e.g. BULL, BULH); transcribed by tools/build/build_captrd_sets.py, for the equations of captrd/equations.gms.';

-- file: capri_data/pipeline/captrd/params/carcass_share.csv
CREATE TABLE ctrd_carcass_share (
    d0 VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_carcass_share IS 'CAPRI''s p_carcassShare(COLS): carcass weight over live weight of the fattening and breeding activities, CAPRI''s constants of feed/feed_decl.gms l. 211-226 (included by captrd.gms l. 370), as in sim_ini_21730 (the raw dataset, capri/results/simini/sim_ini_21730/p_carcassShare.parquet); used by FinalWgt_ and Dailyup_ (equations.gms l. 573-593); 13 rows (tools/build/build_captrd_estimation_params.py).';
INSERT INTO value_units VALUES
  ('ctrd_carcass_share', 'value', NULL, 'open', 'carcass over live weight, a ratio; no unit code for it');

-- file: capri_data/pipeline/captrd/params/start_wgt.csv
CREATE TABLE ctrd_start_wgt (
    d0 VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_start_wgt IS 'CAPRI''s p_startWgt(COLS): live weight at the start of the fattening or raising process, feed/feed_decl.gms l. 231-245, as in sim_ini_21730 (p_startWgt.parquet); used by FinalWgt_ (equations.gms l. 573-583); 12 rows (tools/build/build_captrd_estimation_params.py).';
INSERT INTO value_units VALUES
  ('ctrd_start_wgt', 'value', NULL, 'open', 'kg live weight per head (feed_decl.gms: live weight at start)');

-- file: capri_data/pipeline/captrd/params/ncnc_cont.csv
CREATE TABLE ctrd_ncnc_cont (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_ncnc_cont IS 'CAPRI''s p_NCNC_CONT(ROWS, NCNC): nutrient content per kg of a food product, the USDA contents mapped to CAPRI''s codes (captrd.gms l. 622-633, coco2.gms l. 255-262), as in sim_ini_21730 (p_NCNC_CONT.parquet); used by NUTBAL_ (equations.gms l. 740-746); 1118 rows (tools/build/build_captrd_estimation_params.py).';
INSERT INTO value_units VALUES
  ('ctrd_ncnc_cont', 'value', NULL, 'open', 'per kg of product, by nutrient (kcal, g, mg); no unit code for it');

-- file: capri_data/sources/raw/capri/results/simini/sim_ini_21730/captrd_estimation_params.parquet
CREATE TABLE src_captrd_estimation_params (
    symbol VARCHAR NOT NULL,
    d0 VARCHAR NOT NULL,
    d1 VARCHAR,
    "value" DOUBLE NOT NULL,
    UNIQUE (symbol, d0, d1)
);
COMMENT ON TABLE src_captrd_estimation_params IS 'CAPRI''s p_carcassShare, p_startWgt and p_NCNC_CONT as in sim_ini_21730 (the raw dataset nuvolaTeam/capri-mod-raw, capri/results/simini/sim_ini_21730/), the records tools/build/build_captrd_estimation_params.py uses, kept so it rebuilds without the raw files; d1 only for p_NCNC_CONT.';
INSERT INTO value_units VALUES
  ('src_captrd_estimation_params', 'value', NULL, 'open', 'by symbol: see ctrd_carcass_share, ctrd_start_wgt, ctrd_ncnc_cont');
